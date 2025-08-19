
# === NexusCore/tools\exports\export_20250803_114325\combined_75.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\polynomial\hermite_e.py ===
"""
===================================================================
HermiteE Series, "Probabilists" (:mod:`numpy.polynomial.hermite_e`)
===================================================================

This module provides a number of objects (mostly functions) useful for
dealing with Hermite_e series, including a `HermiteE` class that
encapsulates the usual arithmetic operations.  (General information
on how this module represents and works with such polynomials is in the
docstring for its "parent" sub-package, `numpy.polynomial`).

Classes
-------
.. autosummary::
   :toctree: generated/

   HermiteE

Constants
---------
.. autosummary::
   :toctree: generated/

   hermedomain
   hermezero
   hermeone
   hermex

Arithmetic
----------
.. autosummary::
   :toctree: generated/

   hermeadd
   hermesub
   hermemulx
   hermemul
   hermediv
   hermepow
   hermeval
   hermeval2d
   hermeval3d
   hermegrid2d
   hermegrid3d

Calculus
--------
.. autosummary::
   :toctree: generated/

   hermeder
   hermeint

Misc Functions
--------------
.. autosummary::
   :toctree: generated/

   hermefromroots
   hermeroots
   hermevander
   hermevander2d
   hermevander3d
   hermegauss
   hermeweight
   hermecompanion
   hermefit
   hermetrim
   hermeline
   herme2poly
   poly2herme

See also
--------
`numpy.polynomial`

"""
import numpy as np
import numpy.linalg as la
from numpy.lib.array_utils import normalize_axis_index

from . import polyutils as pu
from ._polybase import ABCPolyBase

__all__ = [
    'hermezero', 'hermeone', 'hermex', 'hermedomain', 'hermeline',
    'hermeadd', 'hermesub', 'hermemulx', 'hermemul', 'hermediv',
    'hermepow', 'hermeval', 'hermeder', 'hermeint', 'herme2poly',
    'poly2herme', 'hermefromroots', 'hermevander', 'hermefit', 'hermetrim',
    'hermeroots', 'HermiteE', 'hermeval2d', 'hermeval3d', 'hermegrid2d',
    'hermegrid3d', 'hermevander2d', 'hermevander3d', 'hermecompanion',
    'hermegauss', 'hermeweight']

hermetrim = pu.trimcoef


def poly2herme(pol):
    """
    poly2herme(pol)

    Convert a polynomial to a Hermite series.

    Convert an array representing the coefficients of a polynomial (relative
    to the "standard" basis) ordered from lowest degree to highest, to an
    array of the coefficients of the equivalent Hermite series, ordered
    from lowest to highest degree.

    Parameters
    ----------
    pol : array_like
        1-D array containing the polynomial coefficients

    Returns
    -------
    c : ndarray
        1-D array containing the coefficients of the equivalent Hermite
        series.

    See Also
    --------
    herme2poly

    Notes
    -----
    The easy way to do conversions between polynomial basis sets
    is to use the convert method of a class instance.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial.hermite_e import poly2herme
    >>> poly2herme(np.arange(4))
    array([  2.,  10.,   2.,   3.])

    """
    [pol] = pu.as_series([pol])
    deg = len(pol) - 1
    res = 0
    for i in range(deg, -1, -1):
        res = hermeadd(hermemulx(res), pol[i])
    return res


def herme2poly(c):
    """
    Convert a Hermite series to a polynomial.

    Convert an array representing the coefficients of a Hermite series,
    ordered from lowest degree to highest, to an array of the coefficients
    of the equivalent polynomial (relative to the "standard" basis) ordered
    from lowest to highest degree.

    Parameters
    ----------
    c : array_like
        1-D array containing the Hermite series coefficients, ordered
        from lowest order term to highest.

    Returns
    -------
    pol : ndarray
        1-D array containing the coefficients of the equivalent polynomial
        (relative to the "standard" basis) ordered from lowest order term
        to highest.

    See Also
    --------
    poly2herme

    Notes
    -----
    The easy way to do conversions between polynomial basis sets
    is to use the convert method of a class instance.

    Examples
    --------
    >>> from numpy.polynomial.hermite_e import herme2poly
    >>> herme2poly([  2.,  10.,   2.,   3.])
    array([0.,  1.,  2.,  3.])

    """
    from .polynomial import polyadd, polymulx, polysub

    [c] = pu.as_series([c])
    n = len(c)
    if n == 1:
        return c
    if n == 2:
        return c
    else:
        c0 = c[-2]
        c1 = c[-1]
        # i is the current degree of c1
        for i in range(n - 1, 1, -1):
            tmp = c0
            c0 = polysub(c[i - 2], c1 * (i - 1))
            c1 = polyadd(tmp, polymulx(c1))
        return polyadd(c0, polymulx(c1))


#
# These are constant arrays are of integer type so as to be compatible
# with the widest range of other types, such as Decimal.
#

# Hermite
hermedomain = np.array([-1., 1.])

# Hermite coefficients representing zero.
hermezero = np.array([0])

# Hermite coefficients representing one.
hermeone = np.array([1])

# Hermite coefficients representing the identity x.
hermex = np.array([0, 1])


def hermeline(off, scl):
    """
    Hermite series whose graph is a straight line.

    Parameters
    ----------
    off, scl : scalars
        The specified line is given by ``off + scl*x``.

    Returns
    -------
    y : ndarray
        This module's representation of the Hermite series for
        ``off + scl*x``.

    See Also
    --------
    numpy.polynomial.polynomial.polyline
    numpy.polynomial.chebyshev.chebline
    numpy.polynomial.legendre.legline
    numpy.polynomial.laguerre.lagline
    numpy.polynomial.hermite.hermline

    Examples
    --------
    >>> from numpy.polynomial.hermite_e import hermeline
    >>> from numpy.polynomial.hermite_e import hermeline, hermeval
    >>> hermeval(0,hermeline(3, 2))
    3.0
    >>> hermeval(1,hermeline(3, 2))
    5.0

    """
    if scl != 0:
        return np.array([off, scl])
    else:
        return np.array([off])


def hermefromroots(roots):
    """
    Generate a HermiteE series with given roots.

    The function returns the coefficients of the polynomial

    .. math:: p(x) = (x - r_0) * (x - r_1) * ... * (x - r_n),

    in HermiteE form, where the :math:`r_n` are the roots specified in `roots`.
    If a zero has multiplicity n, then it must appear in `roots` n times.
    For instance, if 2 is a root of multiplicity three and 3 is a root of
    multiplicity 2, then `roots` looks something like [2, 2, 2, 3, 3]. The
    roots can appear in any order.

    If the returned coefficients are `c`, then

    .. math:: p(x) = c_0 + c_1 * He_1(x) + ... +  c_n * He_n(x)

    The coefficient of the last term is not generally 1 for monic
    polynomials in HermiteE form.

    Parameters
    ----------
    roots : array_like
        Sequence containing the roots.

    Returns
    -------
    out : ndarray
        1-D array of coefficients.  If all roots are real then `out` is a
        real array, if some of the roots are complex, then `out` is complex
        even if all the coefficients in the result are real (see Examples
        below).

    See Also
    --------
    numpy.polynomial.polynomial.polyfromroots
    numpy.polynomial.legendre.legfromroots
    numpy.polynomial.laguerre.lagfromroots
    numpy.polynomial.hermite.hermfromroots
    numpy.polynomial.chebyshev.chebfromroots

    Examples
    --------
    >>> from numpy.polynomial.hermite_e import hermefromroots, hermeval
    >>> coef = hermefromroots((-1, 0, 1))
    >>> hermeval((-1, 0, 1), coef)
    array([0., 0., 0.])
    >>> coef = hermefromroots((-1j, 1j))
    >>> hermeval((-1j, 1j), coef)
    array([0.+0.j, 0.+0.j])

    """
    return pu._fromroots(hermeline, hermemul, roots)


def hermeadd(c1, c2):
    """
    Add one Hermite series to another.

    Returns the sum of two Hermite series `c1` + `c2`.  The arguments
    are sequences of coefficients ordered from lowest order term to
    highest, i.e., [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Array representing the Hermite series of their sum.

    See Also
    --------
    hermesub, hermemulx, hermemul, hermediv, hermepow

    Notes
    -----
    Unlike multiplication, division, etc., the sum of two Hermite series
    is a Hermite series (without having to "reproject" the result onto
    the basis set) so addition, just like that of "standard" polynomials,
    is simply "component-wise."

    Examples
    --------
    >>> from numpy.polynomial.hermite_e import hermeadd
    >>> hermeadd([1, 2, 3], [1, 2, 3, 4])
    array([2.,  4.,  6.,  4.])

    """
    return pu._add(c1, c2)


def hermesub(c1, c2):
    """
    Subtract one Hermite series from another.

    Returns the difference of two Hermite series `c1` - `c2`.  The
    sequences of coefficients are from lowest order term to highest, i.e.,
    [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Of Hermite series coefficients representing their difference.

    See Also
    --------
    hermeadd, hermemulx, hermemul, hermediv, hermepow

    Notes
    -----
    Unlike multiplication, division, etc., the difference of two Hermite
    series is a Hermite series (without having to "reproject" the result
    onto the basis set) so subtraction, just like that of "standard"
    polynomials, is simply "component-wise."

    Examples
    --------
    >>> from numpy.polynomial.hermite_e import hermesub
    >>> hermesub([1, 2, 3, 4], [1, 2, 3])
    array([0., 0., 0., 4.])

    """
    return pu._sub(c1, c2)


def hermemulx(c):
    """Multiply a Hermite series by x.

    Multiply the Hermite series `c` by x, where x is the independent
    variable.


    Parameters
    ----------
    c : array_like
        1-D array of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Array representing the result of the multiplication.

    See Also
    --------
    hermeadd, hermesub, hermemul, hermediv, hermepow

    Notes
    -----
    The multiplication uses the recursion relationship for Hermite
    polynomials in the form

    .. math::

        xP_i(x) = (P_{i + 1}(x) + iP_{i - 1}(x)))

    Examples
    --------
    >>> from numpy.polynomial.hermite_e import hermemulx
    >>> hermemulx([1, 2, 3])
    array([2.,  7.,  2.,  3.])

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    # The zero series needs special treatment
    if len(c) == 1 and c[0] == 0:
        return c

    prd = np.empty(len(c) + 1, dtype=c.dtype)
    prd[0] = c[0] * 0
    prd[1] = c[0]
    for i in range(1, len(c)):
        prd[i + 1] = c[i]
        prd[i - 1] += c[i] * i
    return prd


def hermemul(c1, c2):
    """
    Multiply one Hermite series by another.

    Returns the product of two Hermite series `c1` * `c2`.  The arguments
    are sequences of coefficients, from lowest order "term" to highest,
    e.g., [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Of Hermite series coefficients representing their product.

    See Also
    --------
    hermeadd, hermesub, hermemulx, hermediv, hermepow

    Notes
    -----
    In general, the (polynomial) product of two C-series results in terms
    that are not in the Hermite polynomial basis set.  Thus, to express
    the product as a Hermite series, it is necessary to "reproject" the
    product onto said basis set, which may produce "unintuitive" (but
    correct) results; see Examples section below.

    Examples
    --------
    >>> from numpy.polynomial.hermite_e import hermemul
    >>> hermemul([1, 2, 3], [0, 1, 2])
    array([14.,  15.,  28.,   7.,   6.])

    """
    # s1, s2 are trimmed copies
    [c1, c2] = pu.as_series([c1, c2])

    if len(c1) > len(c2):
        c = c2
        xs = c1
    else:
        c = c1
        xs = c2

    if len(c) == 1:
        c0 = c[0] * xs
        c1 = 0
    elif len(c) == 2:
        c0 = c[0] * xs
        c1 = c[1] * xs
    else:
        nd = len(c)
        c0 = c[-2] * xs
        c1 = c[-1] * xs
        for i in range(3, len(c) + 1):
            tmp = c0
            nd = nd - 1
            c0 = hermesub(c[-i] * xs, c1 * (nd - 1))
            c1 = hermeadd(tmp, hermemulx(c1))
    return hermeadd(c0, hermemulx(c1))


def hermediv(c1, c2):
    """
    Divide one Hermite series by another.

    Returns the quotient-with-remainder of two Hermite series
    `c1` / `c2`.  The arguments are sequences of coefficients from lowest
    order "term" to highest, e.g., [1,2,3] represents the series
    ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    [quo, rem] : ndarrays
        Of Hermite series coefficients representing the quotient and
        remainder.

    See Also
    --------
    hermeadd, hermesub, hermemulx, hermemul, hermepow

    Notes
    -----
    In general, the (polynomial) division of one Hermite series by another
    results in quotient and remainder terms that are not in the Hermite
    polynomial basis set.  Thus, to express these results as a Hermite
    series, it is necessary to "reproject" the results onto the Hermite
    basis set, which may produce "unintuitive" (but correct) results; see
    Examples section below.

    Examples
    --------
    >>> from numpy.polynomial.hermite_e import hermediv
    >>> hermediv([ 14.,  15.,  28.,   7.,   6.], [0, 1, 2])
    (array([1., 2., 3.]), array([0.]))
    >>> hermediv([ 15.,  17.,  28.,   7.,   6.], [0, 1, 2])
    (array([1., 2., 3.]), array([1., 2.]))

    """
    return pu._div(hermemul, c1, c2)


def hermepow(c, pow, maxpower=16):
    """Raise a Hermite series to a power.

    Returns the Hermite series `c` raised to the power `pow`. The
    argument `c` is a sequence of coefficients ordered from low to high.
    i.e., [1,2,3] is the series  ``P_0 + 2*P_1 + 3*P_2.``

    Parameters
    ----------
    c : array_like
        1-D array of Hermite series coefficients ordered from low to
        high.
    pow : integer
        Power to which the series will be raised
    maxpower : integer, optional
        Maximum power allowed. This is mainly to limit growth of the series
        to unmanageable size. Default is 16

    Returns
    -------
    coef : ndarray
        Hermite series of power.

    See Also
    --------
    hermeadd, hermesub, hermemulx, hermemul, hermediv

    Examples
    --------
    >>> from numpy.polynomial.hermite_e import hermepow
    >>> hermepow([1, 2, 3], 2)
    array([23.,  28.,  46.,  12.,   9.])

    """
    return pu._pow(hermemul, c, pow, maxpower)


def hermeder(c, m=1, scl=1, axis=0):
    """
    Differentiate a Hermite_e series.

    Returns the series coefficients `c` differentiated `m` times along
    `axis`.  At each iteration the result is multiplied by `scl` (the
    scaling factor is for use in a linear change of variable). The argument
    `c` is an array of coefficients from low to high degree along each
    axis, e.g., [1,2,3] represents the series ``1*He_0 + 2*He_1 + 3*He_2``
    while [[1,2],[1,2]] represents ``1*He_0(x)*He_0(y) + 1*He_1(x)*He_0(y)
    + 2*He_0(x)*He_1(y) + 2*He_1(x)*He_1(y)`` if axis=0 is ``x`` and axis=1
    is ``y``.

    Parameters
    ----------
    c : array_like
        Array of Hermite_e series coefficients. If `c` is multidimensional
        the different axis correspond to different variables with the
        degree in each axis given by the corresponding index.
    m : int, optional
        Number of derivatives taken, must be non-negative. (Default: 1)
    scl : scalar, optional
        Each differentiation is multiplied by `scl`.  The end result is
        multiplication by ``scl**m``.  This is for use in a linear change of
        variable. (Default: 1)
    axis : int, optional
        Axis over which the derivative is taken. (Default: 0).

    Returns
    -------
    der : ndarray
        Hermite series of the derivative.

    See Also
    --------
    hermeint

    Notes
    -----
    In general, the result of differentiating a Hermite series does not
    resemble the same operation on a power series. Thus the result of this
    function may be "unintuitive," albeit correct; see Examples section
    below.

    Examples
    --------
    >>> from numpy.polynomial.hermite_e import hermeder
    >>> hermeder([ 1.,  1.,  1.,  1.])
    array([1.,  2.,  3.])
    >>> hermeder([-0.25,  1.,  1./2.,  1./3.,  1./4 ], m=2)
    array([1.,  2.,  3.])

    """
    c = np.array(c, ndmin=1, copy=True)
    if c.dtype.char in '?bBhHiIlLqQpP':
        c = c.astype(np.double)
    cnt = pu._as_int(m, "the order of derivation")
    iaxis = pu._as_int(axis, "the axis")
    if cnt < 0:
        raise ValueError("The order of derivation must be non-negative")
    iaxis = normalize_axis_index(iaxis, c.ndim)

    if cnt == 0:
        return c

    c = np.moveaxis(c, iaxis, 0)
    n = len(c)
    if cnt >= n:
        return c[:1] * 0
    else:
        for i in range(cnt):
            n = n - 1
            c *= scl
            der = np.empty((n,) + c.shape[1:], dtype=c.dtype)
            for j in range(n, 0, -1):
                der[j - 1] = j * c[j]
            c = der
    c = np.moveaxis(c, 0, iaxis)
    return c


def hermeint(c, m=1, k=[], lbnd=0, scl=1, axis=0):
    """
    Integrate a Hermite_e series.

    Returns the Hermite_e series coefficients `c` integrated `m` times from
    `lbnd` along `axis`. At each iteration the resulting series is
    **multiplied** by `scl` and an integration constant, `k`, is added.
    The scaling factor is for use in a linear change of variable.  ("Buyer
    beware": note that, depending on what one is doing, one may want `scl`
    to be the reciprocal of what one might expect; for more information,
    see the Notes section below.)  The argument `c` is an array of
    coefficients from low to high degree along each axis, e.g., [1,2,3]
    represents the series ``H_0 + 2*H_1 + 3*H_2`` while [[1,2],[1,2]]
    represents ``1*H_0(x)*H_0(y) + 1*H_1(x)*H_0(y) + 2*H_0(x)*H_1(y) +
    2*H_1(x)*H_1(y)`` if axis=0 is ``x`` and axis=1 is ``y``.

    Parameters
    ----------
    c : array_like
        Array of Hermite_e series coefficients. If c is multidimensional
        the different axis correspond to different variables with the
        degree in each axis given by the corresponding index.
    m : int, optional
        Order of integration, must be positive. (Default: 1)
    k : {[], list, scalar}, optional
        Integration constant(s).  The value of the first integral at
        ``lbnd`` is the first value in the list, the value of the second
        integral at ``lbnd`` is the second value, etc.  If ``k == []`` (the
        default), all constants are set to zero.  If ``m == 1``, a single
        scalar can be given instead of a list.
    lbnd : scalar, optional
        The lower bound of the integral. (Default: 0)
    scl : scalar, optional
        Following each integration the result is *multiplied* by `scl`
        before the integration constant is added. (Default: 1)
    axis : int, optional
        Axis over which the integral is taken. (Default: 0).

    Returns
    -------
    S : ndarray
        Hermite_e series coefficients of the integral.

    Raises
    ------
    ValueError
        If ``m < 0``, ``len(k) > m``, ``np.ndim(lbnd) != 0``, or
        ``np.ndim(scl) != 0``.

    See Also
    --------
    hermeder

    Notes
    -----
    Note that the result of each integration is *multiplied* by `scl`.
    Why is this important to note?  Say one is making a linear change of
    variable :math:`u = ax + b` in an integral relative to `x`.  Then
    :math:`dx = du/a`, so one will need to set `scl` equal to
    :math:`1/a` - perhaps not what one would have first thought.

    Also note that, in general, the result of integrating a C-series needs
    to be "reprojected" onto the C-series basis set.  Thus, typically,
    the result of this function is "unintuitive," albeit correct; see
    Examples section below.

    Examples
    --------
    >>> from numpy.polynomial.hermite_e import hermeint
    >>> hermeint([1, 2, 3]) # integrate once, value 0 at 0.
    array([1., 1., 1., 1.])
    >>> hermeint([1, 2, 3], m=2) # integrate twice, value & deriv 0 at 0
    array([-0.25      ,  1.        ,  0.5       ,  0.33333333,  0.25      ]) # may vary
    >>> hermeint([1, 2, 3], k=1) # integrate once, value 1 at 0.
    array([2., 1., 1., 1.])
    >>> hermeint([1, 2, 3], lbnd=-1) # integrate once, value 0 at -1
    array([-1.,  1.,  1.,  1.])
    >>> hermeint([1, 2, 3], m=2, k=[1, 2], lbnd=-1)
    array([ 1.83333333,  0.        ,  0.5       ,  0.33333333,  0.25      ]) # may vary

    """
    c = np.array(c, ndmin=1, copy=True)
    if c.dtype.char in '?bBhHiIlLqQpP':
        c = c.astype(np.double)
    if not np.iterable(k):
        k = [k]
    cnt = pu._as_int(m, "the order of integration")
    iaxis = pu._as_int(axis, "the axis")
    if cnt < 0:
        raise ValueError("The order of integration must be non-negative")
    if len(k) > cnt:
        raise ValueError("Too many integration constants")
    if np.ndim(lbnd) != 0:
        raise ValueError("lbnd must be a scalar.")
    if np.ndim(scl) != 0:
        raise ValueError("scl must be a scalar.")
    iaxis = normalize_axis_index(iaxis, c.ndim)

    if cnt == 0:
        return c

    c = np.moveaxis(c, iaxis, 0)
    k = list(k) + [0] * (cnt - len(k))
    for i in range(cnt):
        n = len(c)
        c *= scl
        if n == 1 and np.all(c[0] == 0):
            c[0] += k[i]
        else:
            tmp = np.empty((n + 1,) + c.shape[1:], dtype=c.dtype)
            tmp[0] = c[0] * 0
            tmp[1] = c[0]
            for j in range(1, n):
                tmp[j + 1] = c[j] / (j + 1)
            tmp[0] += k[i] - hermeval(lbnd, tmp)
            c = tmp
    c = np.moveaxis(c, 0, iaxis)
    return c


def hermeval(x, c, tensor=True):
    """
    Evaluate an HermiteE series at points x.

    If `c` is of length ``n + 1``, this function returns the value:

    .. math:: p(x) = c_0 * He_0(x) + c_1 * He_1(x) + ... + c_n * He_n(x)

    The parameter `x` is converted to an array only if it is a tuple or a
    list, otherwise it is treated as a scalar. In either case, either `x`
    or its elements must support multiplication and addition both with
    themselves and with the elements of `c`.

    If `c` is a 1-D array, then ``p(x)`` will have the same shape as `x`.  If
    `c` is multidimensional, then the shape of the result depends on the
    value of `tensor`. If `tensor` is true the shape will be c.shape[1:] +
    x.shape. If `tensor` is false the shape will be c.shape[1:]. Note that
    scalars have shape (,).

    Trailing zeros in the coefficients will be used in the evaluation, so
    they should be avoided if efficiency is a concern.

    Parameters
    ----------
    x : array_like, compatible object
        If `x` is a list or tuple, it is converted to an ndarray, otherwise
        it is left unchanged and treated as a scalar. In either case, `x`
        or its elements must support addition and multiplication with
        with themselves and with the elements of `c`.
    c : array_like
        Array of coefficients ordered so that the coefficients for terms of
        degree n are contained in c[n]. If `c` is multidimensional the
        remaining indices enumerate multiple polynomials. In the two
        dimensional case the coefficients may be thought of as stored in
        the columns of `c`.
    tensor : boolean, optional
        If True, the shape of the coefficient array is extended with ones
        on the right, one for each dimension of `x`. Scalars have dimension 0
        for this action. The result is that every column of coefficients in
        `c` is evaluated for every element of `x`. If False, `x` is broadcast
        over the columns of `c` for the evaluation.  This keyword is useful
        when `c` is multidimensional. The default value is True.

    Returns
    -------
    values : ndarray, algebra_like
        The shape of the return value is described above.

    See Also
    --------
    hermeval2d, hermegrid2d, hermeval3d, hermegrid3d

    Notes
    -----
    The evaluation uses Clenshaw recursion, aka synthetic division.

    Examples
    --------
    >>> from numpy.polynomial.hermite_e import hermeval
    >>> coef = [1,2,3]
    >>> hermeval(1, coef)
    3.0
    >>> hermeval([[1,2],[3,4]], coef)
    array([[ 3., 14.],
           [31., 54.]])

    """
    c = np.array(c, ndmin=1, copy=None)
    if c.dtype.char in '?bBhHiIlLqQpP':
        c = c.astype(np.double)
    if isinstance(x, (tuple, list)):
        x = np.asarray(x)
    if isinstance(x, np.ndarray) and tensor:
        c = c.reshape(c.shape + (1,) * x.ndim)

    if len(c) == 1:
        c0 = c[0]
        c1 = 0
    elif len(c) == 2:
        c0 = c[0]
        c1 = c[1]
    else:
        nd = len(c)
        c0 = c[-2]
        c1 = c[-1]
        for i in range(3, len(c) + 1):
            tmp = c0
            nd = nd - 1
            c0 = c[-i] - c1 * (nd - 1)
            c1 = tmp + c1 * x
    return c0 + c1 * x


def hermeval2d(x, y, c):
    """
    Evaluate a 2-D HermiteE series at points (x, y).

    This function returns the values:

    .. math:: p(x,y) = \\sum_{i,j} c_{i,j} * He_i(x) * He_j(y)

    The parameters `x` and `y` are converted to arrays only if they are
    tuples or a lists, otherwise they are treated as a scalars and they
    must have the same shape after conversion. In either case, either `x`
    and `y` or their elements must support multiplication and addition both
    with themselves and with the elements of `c`.

    If `c` is a 1-D array a one is implicitly appended to its shape to make
    it 2-D. The shape of the result will be c.shape[2:] + x.shape.

    Parameters
    ----------
    x, y : array_like, compatible objects
        The two dimensional series is evaluated at the points ``(x, y)``,
        where `x` and `y` must have the same shape. If `x` or `y` is a list
        or tuple, it is first converted to an ndarray, otherwise it is left
        unchanged and if it isn't an ndarray it is treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficient of the term
        of multi-degree i,j is contained in ``c[i,j]``. If `c` has
        dimension greater than two the remaining indices enumerate multiple
        sets of coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional polynomial at points formed with
        pairs of corresponding values from `x` and `y`.

    See Also
    --------
    hermeval, hermegrid2d, hermeval3d, hermegrid3d
    """
    return pu._valnd(hermeval, c, x, y)


def hermegrid2d(x, y, c):
    """
    Evaluate a 2-D HermiteE series on the Cartesian product of x and y.

    This function returns the values:

    .. math:: p(a,b) = \\sum_{i,j} c_{i,j} * H_i(a) * H_j(b)

    where the points ``(a, b)`` consist of all pairs formed by taking
    `a` from `x` and `b` from `y`. The resulting points form a grid with
    `x` in the first dimension and `y` in the second.

    The parameters `x` and `y` are converted to arrays only if they are
    tuples or a lists, otherwise they are treated as a scalars. In either
    case, either `x` and `y` or their elements must support multiplication
    and addition both with themselves and with the elements of `c`.

    If `c` has fewer than two dimensions, ones are implicitly appended to
    its shape to make it 2-D. The shape of the result will be c.shape[2:] +
    x.shape.

    Parameters
    ----------
    x, y : array_like, compatible objects
        The two dimensional series is evaluated at the points in the
        Cartesian product of `x` and `y`.  If `x` or `y` is a list or
        tuple, it is first converted to an ndarray, otherwise it is left
        unchanged and, if it isn't an ndarray, it is treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficients for terms of
        degree i,j are contained in ``c[i,j]``. If `c` has dimension
        greater than two the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional polynomial at points in the Cartesian
        product of `x` and `y`.

    See Also
    --------
    hermeval, hermeval2d, hermeval3d, hermegrid3d
    """
    return pu._gridnd(hermeval, c, x, y)


def hermeval3d(x, y, z, c):
    """
    Evaluate a 3-D Hermite_e series at points (x, y, z).

    This function returns the values:

    .. math:: p(x,y,z) = \\sum_{i,j,k} c_{i,j,k} * He_i(x) * He_j(y) * He_k(z)

    The parameters `x`, `y`, and `z` are converted to arrays only if
    they are tuples or a lists, otherwise they are treated as a scalars and
    they must have the same shape after conversion. In either case, either
    `x`, `y`, and `z` or their elements must support multiplication and
    addition both with themselves and with the elements of `c`.

    If `c` has fewer than 3 dimensions, ones are implicitly appended to its
    shape to make it 3-D. The shape of the result will be c.shape[3:] +
    x.shape.

    Parameters
    ----------
    x, y, z : array_like, compatible object
        The three dimensional series is evaluated at the points
        `(x, y, z)`, where `x`, `y`, and `z` must have the same shape.  If
        any of `x`, `y`, or `z` is a list or tuple, it is first converted
        to an ndarray, otherwise it is left unchanged and if it isn't an
        ndarray it is  treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficient of the term of
        multi-degree i,j,k is contained in ``c[i,j,k]``. If `c` has dimension
        greater than 3 the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the multidimensional polynomial on points formed with
        triples of corresponding values from `x`, `y`, and `z`.

    See Also
    --------
    hermeval, hermeval2d, hermegrid2d, hermegrid3d
    """
    return pu._valnd(hermeval, c, x, y, z)


def hermegrid3d(x, y, z, c):
    """
    Evaluate a 3-D HermiteE series on the Cartesian product of x, y, and z.

    This function returns the values:

    .. math:: p(a,b,c) = \\sum_{i,j,k} c_{i,j,k} * He_i(a) * He_j(b) * He_k(c)

    where the points ``(a, b, c)`` consist of all triples formed by taking
    `a` from `x`, `b` from `y`, and `c` from `z`. The resulting points form
    a grid with `x` in the first dimension, `y` in the second, and `z` in
    the third.

    The parameters `x`, `y`, and `z` are converted to arrays only if they
    are tuples or a lists, otherwise they are treated as a scalars. In
    either case, either `x`, `y`, and `z` or their elements must support
    multiplication and addition both with themselves and with the elements
    of `c`.

    If `c` has fewer than three dimensions, ones are implicitly appended to
    its shape to make it 3-D. The shape of the result will be c.shape[3:] +
    x.shape + y.shape + z.shape.

    Parameters
    ----------
    x, y, z : array_like, compatible objects
        The three dimensional series is evaluated at the points in the
        Cartesian product of `x`, `y`, and `z`.  If `x`, `y`, or `z` is a
        list or tuple, it is first converted to an ndarray, otherwise it is
        left unchanged and, if it isn't an ndarray, it is treated as a
        scalar.
    c : array_like
        Array of coefficients ordered so that the coefficients for terms of
        degree i,j are contained in ``c[i,j]``. If `c` has dimension
        greater than two the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional polynomial at points in the Cartesian
        product of `x` and `y`.

    See Also
    --------
    hermeval, hermeval2d, hermegrid2d, hermeval3d
    """
    return pu._gridnd(hermeval, c, x, y, z)


def hermevander(x, deg):
    """Pseudo-Vandermonde matrix of given degree.

    Returns the pseudo-Vandermonde matrix of degree `deg` and sample points
    `x`. The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., i] = He_i(x),

    where ``0 <= i <= deg``. The leading indices of `V` index the elements of
    `x` and the last index is the degree of the HermiteE polynomial.

    If `c` is a 1-D array of coefficients of length ``n + 1`` and `V` is the
    array ``V = hermevander(x, n)``, then ``np.dot(V, c)`` and
    ``hermeval(x, c)`` are the same up to roundoff. This equivalence is
    useful both for least squares fitting and for the evaluation of a large
    number of HermiteE series of the same degree and sample points.

    Parameters
    ----------
    x : array_like
        Array of points. The dtype is converted to float64 or complex128
        depending on whether any of the elements are complex. If `x` is
        scalar it is converted to a 1-D array.
    deg : int
        Degree of the resulting matrix.

    Returns
    -------
    vander : ndarray
        The pseudo-Vandermonde matrix. The shape of the returned matrix is
        ``x.shape + (deg + 1,)``, where The last index is the degree of the
        corresponding HermiteE polynomial.  The dtype will be the same as
        the converted `x`.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial.hermite_e import hermevander
    >>> x = np.array([-1, 0, 1])
    >>> hermevander(x, 3)
    array([[ 1., -1.,  0.,  2.],
           [ 1.,  0., -1., -0.],
           [ 1.,  1.,  0., -2.]])

    """
    ideg = pu._as_int(deg, "deg")
    if ideg < 0:
        raise ValueError("deg must be non-negative")

    x = np.array(x, copy=None, ndmin=1) + 0.0
    dims = (ideg + 1,) + x.shape
    dtyp = x.dtype
    v = np.empty(dims, dtype=dtyp)
    v[0] = x * 0 + 1
    if ideg > 0:
        v[1] = x
        for i in range(2, ideg + 1):
            v[i] = (v[i - 1] * x - v[i - 2] * (i - 1))
    return np.moveaxis(v, 0, -1)


def hermevander2d(x, y, deg):
    """Pseudo-Vandermonde matrix of given degrees.

    Returns the pseudo-Vandermonde matrix of degrees `deg` and sample
    points ``(x, y)``. The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., (deg[1] + 1)*i + j] = He_i(x) * He_j(y),

    where ``0 <= i <= deg[0]`` and ``0 <= j <= deg[1]``. The leading indices of
    `V` index the points ``(x, y)`` and the last index encodes the degrees of
    the HermiteE polynomials.

    If ``V = hermevander2d(x, y, [xdeg, ydeg])``, then the columns of `V`
    correspond to the elements of a 2-D coefficient array `c` of shape
    (xdeg + 1, ydeg + 1) in the order

    .. math:: c_{00}, c_{01}, c_{02} ... , c_{10}, c_{11}, c_{12} ...

    and ``np.dot(V, c.flat)`` and ``hermeval2d(x, y, c)`` will be the same
    up to roundoff. This equivalence is useful both for least squares
    fitting and for the evaluation of a large number of 2-D HermiteE
    series of the same degrees and sample points.

    Parameters
    ----------
    x, y : array_like
        Arrays of point coordinates, all of the same shape. The dtypes
        will be converted to either float64 or complex128 depending on
        whether any of the elements are complex. Scalars are converted to
        1-D arrays.
    deg : list of ints
        List of maximum degrees of the form [x_deg, y_deg].

    Returns
    -------
    vander2d : ndarray
        The shape of the returned matrix is ``x.shape + (order,)``, where
        :math:`order = (deg[0]+1)*(deg[1]+1)`.  The dtype will be the same
        as the converted `x` and `y`.

    See Also
    --------
    hermevander, hermevander3d, hermeval2d, hermeval3d
    """
    return pu._vander_nd_flat((hermevander, hermevander), (x, y), deg)


def hermevander3d(x, y, z, deg):
    """Pseudo-Vandermonde matrix of given degrees.

    Returns the pseudo-Vandermonde matrix of degrees `deg` and sample
    points ``(x, y, z)``. If `l`, `m`, `n` are the given degrees in `x`, `y`, `z`,
    then Hehe pseudo-Vandermonde matrix is defined by

    .. math:: V[..., (m+1)(n+1)i + (n+1)j + k] = He_i(x)*He_j(y)*He_k(z),

    where ``0 <= i <= l``, ``0 <= j <= m``, and ``0 <= j <= n``.  The leading
    indices of `V` index the points ``(x, y, z)`` and the last index encodes
    the degrees of the HermiteE polynomials.

    If ``V = hermevander3d(x, y, z, [xdeg, ydeg, zdeg])``, then the columns
    of `V` correspond to the elements of a 3-D coefficient array `c` of
    shape (xdeg + 1, ydeg + 1, zdeg + 1) in the order

    .. math:: c_{000}, c_{001}, c_{002},... , c_{010}, c_{011}, c_{012},...

    and  ``np.dot(V, c.flat)`` and ``hermeval3d(x, y, z, c)`` will be the
    same up to roundoff. This equivalence is useful both for least squares
    fitting and for the evaluation of a large number of 3-D HermiteE
    series of the same degrees and sample points.

    Parameters
    ----------
    x, y, z : array_like
        Arrays of point coordinates, all of the same shape. The dtypes will
        be converted to either float64 or complex128 depending on whether
        any of the elements are complex. Scalars are converted to 1-D
        arrays.
    deg : list of ints
        List of maximum degrees of the form [x_deg, y_deg, z_deg].

    Returns
    -------
    vander3d : ndarray
        The shape of the returned matrix is ``x.shape + (order,)``, where
        :math:`order = (deg[0]+1)*(deg[1]+1)*(deg[2]+1)`.  The dtype will
        be the same as the converted `x`, `y`, and `z`.

    See Also
    --------
    hermevander, hermevander3d, hermeval2d, hermeval3d
    """
    return pu._vander_nd_flat((hermevander, hermevander, hermevander), (x, y, z), deg)


def hermefit(x, y, deg, rcond=None, full=False, w=None):
    """
    Least squares fit of Hermite series to data.

    Return the coefficients of a HermiteE series of degree `deg` that is
    the least squares fit to the data values `y` given at points `x`. If
    `y` is 1-D the returned coefficients will also be 1-D. If `y` is 2-D
    multiple fits are done, one for each column of `y`, and the resulting
    coefficients are stored in the corresponding columns of a 2-D return.
    The fitted polynomial(s) are in the form

    .. math::  p(x) = c_0 + c_1 * He_1(x) + ... + c_n * He_n(x),

    where `n` is `deg`.

    Parameters
    ----------
    x : array_like, shape (M,)
        x-coordinates of the M sample points ``(x[i], y[i])``.
    y : array_like, shape (M,) or (M, K)
        y-coordinates of the sample points. Several data sets of sample
        points sharing the same x-coordinates can be fitted at once by
        passing in a 2D-array that contains one dataset per column.
    deg : int or 1-D array_like
        Degree(s) of the fitting polynomials. If `deg` is a single integer
        all terms up to and including the `deg`'th term are included in the
        fit. For NumPy versions >= 1.11.0 a list of integers specifying the
        degrees of the terms to include may be used instead.
    rcond : float, optional
        Relative condition number of the fit. Singular values smaller than
        this relative to the largest singular value will be ignored. The
        default value is len(x)*eps, where eps is the relative precision of
        the float type, about 2e-16 in most cases.
    full : bool, optional
        Switch determining nature of return value. When it is False (the
        default) just the coefficients are returned, when True diagnostic
        information from the singular value decomposition is also returned.
    w : array_like, shape (`M`,), optional
        Weights. If not None, the weight ``w[i]`` applies to the unsquared
        residual ``y[i] - y_hat[i]`` at ``x[i]``. Ideally the weights are
        chosen so that the errors of the products ``w[i]*y[i]`` all have the
        same variance.  When using inverse-variance weighting, use
        ``w[i] = 1/sigma(y[i])``.  The default value is None.

    Returns
    -------
    coef : ndarray, shape (M,) or (M, K)
        Hermite coefficients ordered from low to high. If `y` was 2-D,
        the coefficients for the data in column k  of `y` are in column
        `k`.

    [residuals, rank, singular_values, rcond] : list
        These values are only returned if ``full == True``

        - residuals -- sum of squared residuals of the least squares fit
        - rank -- the numerical rank of the scaled Vandermonde matrix
        - singular_values -- singular values of the scaled Vandermonde matrix
        - rcond -- value of `rcond`.

        For more details, see `numpy.linalg.lstsq`.

    Warns
    -----
    RankWarning
        The rank of the coefficient matrix in the least-squares fit is
        deficient. The warning is only raised if ``full = False``.  The
        warnings can be turned off by

        >>> import warnings
        >>> warnings.simplefilter('ignore', np.exceptions.RankWarning)

    See Also
    --------
    numpy.polynomial.chebyshev.chebfit
    numpy.polynomial.legendre.legfit
    numpy.polynomial.polynomial.polyfit
    numpy.polynomial.hermite.hermfit
    numpy.polynomial.laguerre.lagfit
    hermeval : Evaluates a Hermite series.
    hermevander : pseudo Vandermonde matrix of Hermite series.
    hermeweight : HermiteE weight function.
    numpy.linalg.lstsq : Computes a least-squares fit from the matrix.
    scipy.interpolate.UnivariateSpline : Computes spline fits.

    Notes
    -----
    The solution is the coefficients of the HermiteE series `p` that
    minimizes the sum of the weighted squared errors

    .. math:: E = \\sum_j w_j^2 * |y_j - p(x_j)|^2,

    where the :math:`w_j` are the weights. This problem is solved by
    setting up the (typically) overdetermined matrix equation

    .. math:: V(x) * c = w * y,

    where `V` is the pseudo Vandermonde matrix of `x`, the elements of `c`
    are the coefficients to be solved for, and the elements of `y` are the
    observed values.  This equation is then solved using the singular value
    decomposition of `V`.

    If some of the singular values of `V` are so small that they are
    neglected, then a `~exceptions.RankWarning` will be issued. This means that
    the coefficient values may be poorly determined. Using a lower order fit
    will usually get rid of the warning.  The `rcond` parameter can also be
    set to a value smaller than its default, but the resulting fit may be
    spurious and have large contributions from roundoff error.

    Fits using HermiteE series are probably most useful when the data can
    be approximated by ``sqrt(w(x)) * p(x)``, where ``w(x)`` is the HermiteE
    weight. In that case the weight ``sqrt(w(x[i]))`` should be used
    together with data values ``y[i]/sqrt(w(x[i]))``. The weight function is
    available as `hermeweight`.

    References
    ----------
    .. [1] Wikipedia, "Curve fitting",
           https://en.wikipedia.org/wiki/Curve_fitting

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial.hermite_e import hermefit, hermeval
    >>> x = np.linspace(-10, 10)
    >>> rng = np.random.default_rng()
    >>> err = rng.normal(scale=1./10, size=len(x))
    >>> y = hermeval(x, [1, 2, 3]) + err
    >>> hermefit(x, y, 2)
    array([1.02284196, 2.00032805, 2.99978457]) # may vary

    """
    return pu._fit(hermevander, x, y, deg, rcond, full, w)


def hermecompanion(c):
    """
    Return the scaled companion matrix of c.

    The basis polynomials are scaled so that the companion matrix is
    symmetric when `c` is an HermiteE basis polynomial. This provides
    better eigenvalue estimates than the unscaled case and for basis
    polynomials the eigenvalues are guaranteed to be real if
    `numpy.linalg.eigvalsh` is used to obtain them.

    Parameters
    ----------
    c : array_like
        1-D array of HermiteE series coefficients ordered from low to high
        degree.

    Returns
    -------
    mat : ndarray
        Scaled companion matrix of dimensions (deg, deg).
    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    if len(c) < 2:
        raise ValueError('Series must have maximum degree of at least 1.')
    if len(c) == 2:
        return np.array([[-c[0] / c[1]]])

    n = len(c) - 1
    mat = np.zeros((n, n), dtype=c.dtype)
    scl = np.hstack((1., 1. / np.sqrt(np.arange(n - 1, 0, -1))))
    scl = np.multiply.accumulate(scl)[::-1]
    top = mat.reshape(-1)[1::n + 1]
    bot = mat.reshape(-1)[n::n + 1]
    top[...] = np.sqrt(np.arange(1, n))
    bot[...] = top
    mat[:, -1] -= scl * c[:-1] / c[-1]
    return mat


def hermeroots(c):
    """
    Compute the roots of a HermiteE series.

    Return the roots (a.k.a. "zeros") of the polynomial

    .. math:: p(x) = \\sum_i c[i] * He_i(x).

    Parameters
    ----------
    c : 1-D array_like
        1-D array of coefficients.

    Returns
    -------
    out : ndarray
        Array of the roots of the series. If all the roots are real,
        then `out` is also real, otherwise it is complex.

    See Also
    --------
    numpy.polynomial.polynomial.polyroots
    numpy.polynomial.legendre.legroots
    numpy.polynomial.laguerre.lagroots
    numpy.polynomial.hermite.hermroots
    numpy.polynomial.chebyshev.chebroots

    Notes
    -----
    The root estimates are obtained as the eigenvalues of the companion
    matrix, Roots far from the origin of the complex plane may have large
    errors due to the numerical instability of the series for such
    values. Roots with multiplicity greater than 1 will also show larger
    errors as the value of the series near such points is relatively
    insensitive to errors in the roots. Isolated roots near the origin can
    be improved by a few iterations of Newton's method.

    The HermiteE series basis polynomials aren't powers of `x` so the
    results of this function may seem unintuitive.

    Examples
    --------
    >>> from numpy.polynomial.hermite_e import hermeroots, hermefromroots
    >>> coef = hermefromroots([-1, 0, 1])
    >>> coef
    array([0., 2., 0., 1.])
    >>> hermeroots(coef)
    array([-1.,  0.,  1.]) # may vary

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    if len(c) <= 1:
        return np.array([], dtype=c.dtype)
    if len(c) == 2:
        return np.array([-c[0] / c[1]])

    # rotated companion matrix reduces error
    m = hermecompanion(c)[::-1, ::-1]
    r = la.eigvals(m)
    r.sort()
    return r


def _normed_hermite_e_n(x, n):
    """
    Evaluate a normalized HermiteE polynomial.

    Compute the value of the normalized HermiteE polynomial of degree ``n``
    at the points ``x``.


    Parameters
    ----------
    x : ndarray of double.
        Points at which to evaluate the function
    n : int
        Degree of the normalized HermiteE function to be evaluated.

    Returns
    -------
    values : ndarray
        The shape of the return value is described above.

    Notes
    -----
    This function is needed for finding the Gauss points and integration
    weights for high degrees. The values of the standard HermiteE functions
    overflow when n >= 207.

    """
    if n == 0:
        return np.full(x.shape, 1 / np.sqrt(np.sqrt(2 * np.pi)))

    c0 = 0.
    c1 = 1. / np.sqrt(np.sqrt(2 * np.pi))
    nd = float(n)
    for i in range(n - 1):
        tmp = c0
        c0 = -c1 * np.sqrt((nd - 1.) / nd)
        c1 = tmp + c1 * x * np.sqrt(1. / nd)
        nd = nd - 1.0
    return c0 + c1 * x


def hermegauss(deg):
    """
    Gauss-HermiteE quadrature.

    Computes the sample points and weights for Gauss-HermiteE quadrature.
    These sample points and weights will correctly integrate polynomials of
    degree :math:`2*deg - 1` or less over the interval :math:`[-\\inf, \\inf]`
    with the weight function :math:`f(x) = \\exp(-x^2/2)`.

    Parameters
    ----------
    deg : int
        Number of sample points and weights. It must be >= 1.

    Returns
    -------
    x : ndarray
        1-D ndarray containing the sample points.
    y : ndarray
        1-D ndarray containing the weights.

    Notes
    -----
    The results have only been tested up to degree 100, higher degrees may
    be problematic. The weights are determined by using the fact that

    .. math:: w_k = c / (He'_n(x_k) * He_{n-1}(x_k))

    where :math:`c` is a constant independent of :math:`k` and :math:`x_k`
    is the k'th root of :math:`He_n`, and then scaling the results to get
    the right value when integrating 1.

    """
    ideg = pu._as_int(deg, "deg")
    if ideg <= 0:
        raise ValueError("deg must be a positive integer")

    # first approximation of roots. We use the fact that the companion
    # matrix is symmetric in this case in order to obtain better zeros.
    c = np.array([0] * deg + [1])
    m = hermecompanion(c)
    x = la.eigvalsh(m)

    # improve roots by one application of Newton
    dy = _normed_hermite_e_n(x, ideg)
    df = _normed_hermite_e_n(x, ideg - 1) * np.sqrt(ideg)
    x -= dy / df

    # compute the weights. We scale the factor to avoid possible numerical
    # overflow.
    fm = _normed_hermite_e_n(x, ideg - 1)
    fm /= np.abs(fm).max()
    w = 1 / (fm * fm)

    # for Hermite_e we can also symmetrize
    w = (w + w[::-1]) / 2
    x = (x - x[::-1]) / 2

    # scale w to get the right value
    w *= np.sqrt(2 * np.pi) / w.sum()

    return x, w


def hermeweight(x):
    """Weight function of the Hermite_e polynomials.

    The weight function is :math:`\\exp(-x^2/2)` and the interval of
    integration is :math:`[-\\inf, \\inf]`. the HermiteE polynomials are
    orthogonal, but not normalized, with respect to this weight function.

    Parameters
    ----------
    x : array_like
       Values at which the weight function will be computed.

    Returns
    -------
    w : ndarray
       The weight function at `x`.
    """
    w = np.exp(-.5 * x**2)
    return w


#
# HermiteE series class
#

class HermiteE(ABCPolyBase):
    """An HermiteE series class.

    The HermiteE class provides the standard Python numerical methods
    '+', '-', '*', '//', '%', 'divmod', '**', and '()' as well as the
    attributes and methods listed below.

    Parameters
    ----------
    coef : array_like
        HermiteE coefficients in order of increasing degree, i.e,
        ``(1, 2, 3)`` gives ``1*He_0(x) + 2*He_1(X) + 3*He_2(x)``.
    domain : (2,) array_like, optional
        Domain to use. The interval ``[domain[0], domain[1]]`` is mapped
        to the interval ``[window[0], window[1]]`` by shifting and scaling.
        The default value is [-1., 1.].
    window : (2,) array_like, optional
        Window, see `domain` for its use. The default value is [-1., 1.].
    symbol : str, optional
        Symbol used to represent the independent variable in string
        representations of the polynomial expression, e.g. for printing.
        The symbol must be a valid Python identifier. Default value is 'x'.

        .. versionadded:: 1.24

    """
    # Virtual Functions
    _add = staticmethod(hermeadd)
    _sub = staticmethod(hermesub)
    _mul = staticmethod(hermemul)
    _div = staticmethod(hermediv)
    _pow = staticmethod(hermepow)
    _val = staticmethod(hermeval)
    _int = staticmethod(hermeint)
    _der = staticmethod(hermeder)
    _fit = staticmethod(hermefit)
    _line = staticmethod(hermeline)
    _roots = staticmethod(hermeroots)
    _fromroots = staticmethod(hermefromroots)

    # Virtual properties
    domain = np.array(hermedomain)
    window = np.array(hermedomain)
    basis_name = 'He'

# === NexusCore/openenv\Lib\site-packages\git\repo\base.py ===
# Copyright (C) 2008, 2009 Michael Trier (mtrier@gmail.com) and contributors
#
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

from __future__ import annotations

__all__ = ["Repo"]

import gc
import logging
import os
import os.path as osp
from pathlib import Path
import re
import shlex
import sys
import warnings

import gitdb
from gitdb.db.loose import LooseObjectDB
from gitdb.exc import BadObject

from git.cmd import Git, handle_process_output
from git.compat import defenc, safe_decode
from git.config import GitConfigParser
from git.db import GitCmdObjectDB
from git.exc import (
    GitCommandError,
    InvalidGitRepositoryError,
    NoSuchPathError,
)
from git.index import IndexFile
from git.objects import Submodule, RootModule, Commit
from git.refs import HEAD, Head, Reference, TagReference
from git.remote import Remote, add_progress, to_progress_instance
from git.util import (
    Actor,
    cygpath,
    expand_path,
    finalize_process,
    hex_to_bin,
    remove_password_if_present,
)

from .fun import (
    find_submodule_git_dir,
    find_worktree_git_dir,
    is_git_dir,
    rev_parse,
    touch,
)

# typing ------------------------------------------------------

from git.types import (
    CallableProgress,
    Commit_ish,
    Lit_config_levels,
    PathLike,
    TBD,
    Tree_ish,
    assert_never,
)
from typing import (
    Any,
    BinaryIO,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    TYPE_CHECKING,
    TextIO,
    Tuple,
    Type,
    Union,
    cast,
)

from git.types import ConfigLevels_Tup, TypedDict

if TYPE_CHECKING:
    from git.objects import Tree
    from git.objects.submodule.base import UpdateProgress
    from git.refs.symbolic import SymbolicReference
    from git.remote import RemoteProgress
    from git.util import IterableList

# -----------------------------------------------------------

_logger = logging.getLogger(__name__)


class BlameEntry(NamedTuple):
    commit: Dict[str, Commit]
    linenos: range
    orig_path: Optional[str]
    orig_linenos: range


class Repo:
    """Represents a git repository and allows you to query references, create commit
    information, generate diffs, create and clone repositories, and query the log.

    The following attributes are worth using:

    * :attr:`working_dir` is the working directory of the git command, which is the
      working tree directory if available or the ``.git`` directory in case of bare
      repositories.

    * :attr:`working_tree_dir` is the working tree directory, but will return ``None``
      if we are a bare repository.

    * :attr:`git_dir` is the ``.git`` repository directory, which is always set.
    """

    DAEMON_EXPORT_FILE = "git-daemon-export-ok"

    # Must exist, or  __del__  will fail in case we raise on `__init__()`.
    git = cast("Git", None)

    working_dir: PathLike
    """The working directory of the git command."""

    _working_tree_dir: Optional[PathLike] = None

    git_dir: PathLike
    """The ``.git`` repository directory."""

    _common_dir: PathLike = ""

    # Precompiled regex
    re_whitespace = re.compile(r"\s+")
    re_hexsha_only = re.compile(r"^[0-9A-Fa-f]{40}$")
    re_hexsha_shortened = re.compile(r"^[0-9A-Fa-f]{4,40}$")
    re_envvars = re.compile(r"(\$(\{\s?)?[a-zA-Z_]\w*(\}\s?)?|%\s?[a-zA-Z_]\w*\s?%)")
    re_author_committer_start = re.compile(r"^(author|committer)")
    re_tab_full_line = re.compile(r"^\t(.*)$")

    unsafe_git_clone_options = [
        # Executes arbitrary commands:
        "--upload-pack",
        "-u",
        # Can override configuration variables that execute arbitrary commands:
        "--config",
        "-c",
    ]
    """Options to :manpage:`git-clone(1)` that allow arbitrary commands to be executed.

    The ``--upload-pack``/``-u`` option allows users to execute arbitrary commands
    directly:
    https://git-scm.com/docs/git-clone#Documentation/git-clone.txt---upload-packltupload-packgt

    The ``--config``/``-c`` option allows users to override configuration variables like
    ``protocol.allow`` and ``core.gitProxy`` to execute arbitrary commands:
    https://git-scm.com/docs/git-clone#Documentation/git-clone.txt---configltkeygtltvaluegt
    """

    # Invariants
    config_level: ConfigLevels_Tup = ("system", "user", "global", "repository")
    """Represents the configuration level of a configuration file."""

    # Subclass configuration
    GitCommandWrapperType = Git
    """Subclasses may easily bring in their own custom types by placing a constructor or
    type here."""

    def __init__(
        self,
        path: Optional[PathLike] = None,
        odbt: Type[LooseObjectDB] = GitCmdObjectDB,
        search_parent_directories: bool = False,
        expand_vars: bool = True,
    ) -> None:
        R"""Create a new :class:`Repo` instance.

        :param path:
            The path to either the worktree directory or the .git directory itself::

                repo = Repo("/Users/mtrier/Development/git-python")
                repo = Repo("/Users/mtrier/Development/git-python.git")
                repo = Repo("~/Development/git-python.git")
                repo = Repo("$REPOSITORIES/Development/git-python.git")
                repo = Repo(R"C:\Users\mtrier\Development\git-python\.git")

            - In *Cygwin*, `path` may be a ``cygdrive/...`` prefixed path.
            - If `path` is ``None`` or an empty string, :envvar:`GIT_DIR` is used. If
              that environment variable is absent or empty, the current directory is
              used.

        :param odbt:
            Object DataBase type - a type which is constructed by providing the
            directory containing the database objects, i.e. ``.git/objects``. It will be
            used to access all object data.

        :param search_parent_directories:
            If ``True``, all parent directories will be searched for a valid repo as
            well.

            Please note that this was the default behaviour in older versions of
            GitPython, which is considered a bug though.

        :raise git.exc.InvalidGitRepositoryError:

        :raise git.exc.NoSuchPathError:

        :return:
            :class:`Repo`
        """

        epath = path or os.getenv("GIT_DIR")
        if not epath:
            epath = os.getcwd()
        if Git.is_cygwin():
            # Given how the tests are written, this seems more likely to catch Cygwin
            # git used from Windows than Windows git used from Cygwin. Therefore
            # changing to Cygwin-style paths is the relevant operation.
            epath = cygpath(str(epath))

        epath = epath or path or os.getcwd()
        if not isinstance(epath, str):
            epath = str(epath)
        if expand_vars and re.search(self.re_envvars, epath):
            warnings.warn(
                "The use of environment variables in paths is deprecated"
                + "\nfor security reasons and may be removed in the future!!",
                stacklevel=1,
            )
        epath = expand_path(epath, expand_vars)
        if epath is not None:
            if not os.path.exists(epath):
                raise NoSuchPathError(epath)

        # Walk up the path to find the `.git` dir.
        curpath = epath
        git_dir = None
        while curpath:
            # ABOUT osp.NORMPATH
            # It's important to normalize the paths, as submodules will otherwise
            # initialize their repo instances with paths that depend on path-portions
            # that will not exist after being removed. It's just cleaner.
            if is_git_dir(curpath):
                git_dir = curpath
                # from man git-config : core.worktree
                # Set the path to the root of the working tree. If GIT_COMMON_DIR
                # environment variable is set, core.worktree is ignored and not used for
                # determining the root of working tree. This can be overridden by the
                # GIT_WORK_TREE environment variable. The value can be an absolute path
                # or relative to the path to the .git directory, which is either
                # specified by GIT_DIR, or automatically discovered. If GIT_DIR is
                # specified but none of GIT_WORK_TREE and core.worktree is specified,
                # the current working directory is regarded as the top level of your
                # working tree.
                self._working_tree_dir = os.path.dirname(git_dir)
                if os.environ.get("GIT_COMMON_DIR") is None:
                    gitconf = self._config_reader("repository", git_dir)
                    if gitconf.has_option("core", "worktree"):
                        self._working_tree_dir = gitconf.get("core", "worktree")
                if "GIT_WORK_TREE" in os.environ:
                    self._working_tree_dir = os.getenv("GIT_WORK_TREE")
                break

            dotgit = osp.join(curpath, ".git")
            sm_gitpath = find_submodule_git_dir(dotgit)
            if sm_gitpath is not None:
                git_dir = osp.normpath(sm_gitpath)

            sm_gitpath = find_submodule_git_dir(dotgit)
            if sm_gitpath is None:
                sm_gitpath = find_worktree_git_dir(dotgit)

            if sm_gitpath is not None:
                git_dir = expand_path(sm_gitpath, expand_vars)
                self._working_tree_dir = curpath
                break

            if not search_parent_directories:
                break
            curpath, tail = osp.split(curpath)
            if not tail:
                break
        # END while curpath

        if git_dir is None:
            raise InvalidGitRepositoryError(epath)
        self.git_dir = git_dir

        self._bare = False
        try:
            self._bare = self.config_reader("repository").getboolean("core", "bare")
        except Exception:
            # Let's not assume the option exists, although it should.
            pass

        try:
            common_dir = (Path(self.git_dir) / "commondir").read_text().splitlines()[0].strip()
            self._common_dir = osp.join(self.git_dir, common_dir)
        except OSError:
            self._common_dir = ""

        # Adjust the working directory in case we are actually bare - we didn't know
        # that in the first place.
        if self._bare:
            self._working_tree_dir = None
        # END working dir handling

        self.working_dir: PathLike = self._working_tree_dir or self.common_dir
        self.git = self.GitCommandWrapperType(self.working_dir)

        # Special handling, in special times.
        rootpath = osp.join(self.common_dir, "objects")
        if issubclass(odbt, GitCmdObjectDB):
            self.odb = odbt(rootpath, self.git)
        else:
            self.odb = odbt(rootpath)

    def __enter__(self) -> "Repo":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def close(self) -> None:
        if self.git:
            self.git.clear_cache()
            # Tempfiles objects on Windows are holding references to open files until
            # they are collected by the garbage collector, thus preventing deletion.
            # TODO: Find these references and ensure they are closed and deleted
            # synchronously rather than forcing a gc collection.
            if sys.platform == "win32":
                gc.collect()
            gitdb.util.mman.collect()
            if sys.platform == "win32":
                gc.collect()

    def __eq__(self, rhs: object) -> bool:
        if isinstance(rhs, Repo):
            return self.git_dir == rhs.git_dir
        return False

    def __ne__(self, rhs: object) -> bool:
        return not self.__eq__(rhs)

    def __hash__(self) -> int:
        return hash(self.git_dir)

    # Description property
    def _get_description(self) -> str:
        filename = osp.join(self.git_dir, "description")
        with open(filename, "rb") as fp:
            return fp.read().rstrip().decode(defenc)

    def _set_description(self, descr: str) -> None:
        filename = osp.join(self.git_dir, "description")
        with open(filename, "wb") as fp:
            fp.write((descr + "\n").encode(defenc))

    description = property(_get_description, _set_description, doc="the project's description")
    del _get_description
    del _set_description

    @property
    def working_tree_dir(self) -> Optional[PathLike]:
        """
        :return:
            The working tree directory of our git repository.
            If this is a bare repository, ``None`` is returned.
        """
        return self._working_tree_dir

    @property
    def common_dir(self) -> PathLike:
        """
        :return:
            The git dir that holds everything except possibly HEAD, FETCH_HEAD,
            ORIG_HEAD, COMMIT_EDITMSG, index, and logs/.
        """
        return self._common_dir or self.git_dir

    @property
    def bare(self) -> bool:
        """:return: ``True`` if the repository is bare"""
        return self._bare

    @property
    def heads(self) -> "IterableList[Head]":
        """A list of :class:`~git.refs.head.Head` objects representing the branch heads
        in this repo.

        :return:
            ``git.IterableList(Head, ...)``
        """
        return Head.list_items(self)

    @property
    def branches(self) -> "IterableList[Head]":
        """Alias for heads.
        A list of :class:`~git.refs.head.Head` objects representing the branch heads
        in this repo.

        :return:
            ``git.IterableList(Head, ...)``
        """
        return self.heads

    @property
    def references(self) -> "IterableList[Reference]":
        """A list of :class:`~git.refs.reference.Reference` objects representing tags,
        heads and remote references.

        :return:
            ``git.IterableList(Reference, ...)``
        """
        return Reference.list_items(self)

    @property
    def refs(self) -> "IterableList[Reference]":
        """Alias for references.
        A list of :class:`~git.refs.reference.Reference` objects representing tags,
        heads and remote references.

        :return:
            ``git.IterableList(Reference, ...)``
        """
        return self.references

    @property
    def index(self) -> "IndexFile":
        """
        :return:
            A :class:`~git.index.base.IndexFile` representing this repository's index.

        :note:
            This property can be expensive, as the returned
            :class:`~git.index.base.IndexFile` will be reinitialized.
            It is recommended to reuse the object.
        """
        return IndexFile(self)

    @property
    def head(self) -> "HEAD":
        """
        :return:
            :class:`~git.refs.head.HEAD` object pointing to the current head reference
        """
        return HEAD(self, "HEAD")

    @property
    def remotes(self) -> "IterableList[Remote]":
        """A list of :class:`~git.remote.Remote` objects allowing to access and
        manipulate remotes.

        :return:
            ``git.IterableList(Remote, ...)``
        """
        return Remote.list_items(self)

    def remote(self, name: str = "origin") -> "Remote":
        """:return: The remote with the specified name

        :raise ValueError:
            If no remote with such a name exists.
        """
        r = Remote(self, name)
        if not r.exists():
            raise ValueError("Remote named '%s' didn't exist" % name)
        return r

    # { Submodules

    @property
    def submodules(self) -> "IterableList[Submodule]":
        """
        :return:
            git.IterableList(Submodule, ...) of direct submodules available from the
            current head
        """
        return Submodule.list_items(self)

    def submodule(self, name: str) -> "Submodule":
        """:return: The submodule with the given name

        :raise ValueError:
            If no such submodule exists.
        """
        try:
            return self.submodules[name]
        except IndexError as e:
            raise ValueError("Didn't find submodule named %r" % name) from e
        # END exception handling

    def create_submodule(self, *args: Any, **kwargs: Any) -> Submodule:
        """Create a new submodule.

        :note:
            For a description of the applicable parameters, see the documentation of
            :meth:`Submodule.add <git.objects.submodule.base.Submodule.add>`.

        :return:
            The created submodule.
        """
        return Submodule.add(self, *args, **kwargs)

    def iter_submodules(self, *args: Any, **kwargs: Any) -> Iterator[Submodule]:
        """An iterator yielding Submodule instances.

        See the `~git.objects.util.Traversable` interface for a description of `args`
        and `kwargs`.

        :return:
            Iterator
        """
        return RootModule(self).traverse(*args, **kwargs)

    def submodule_update(self, *args: Any, **kwargs: Any) -> Iterator[Submodule]:
        """Update the submodules, keeping the repository consistent as it will
        take the previous state into consideration.

        :note:
            For more information, please see the documentation of
            :meth:`RootModule.update <git.objects.submodule.root.RootModule.update>`.
        """
        return RootModule(self).update(*args, **kwargs)

    # }END submodules

    @property
    def tags(self) -> "IterableList[TagReference]":
        """A list of :class:`~git.refs.tag.TagReference` objects that are available in
        this repo.

        :return:
            ``git.IterableList(TagReference, ...)``
        """
        return TagReference.list_items(self)

    def tag(self, path: PathLike) -> TagReference:
        """
        :return:
            :class:`~git.refs.tag.TagReference` object, reference pointing to a
            :class:`~git.objects.commit.Commit` or tag

        :param path:
            Path to the tag reference, e.g. ``0.1.5`` or ``tags/0.1.5``.
        """
        full_path = self._to_full_tag_path(path)
        return TagReference(self, full_path)

    @staticmethod
    def _to_full_tag_path(path: PathLike) -> str:
        path_str = str(path)
        if path_str.startswith(TagReference._common_path_default + "/"):
            return path_str
        if path_str.startswith(TagReference._common_default + "/"):
            return Reference._common_path_default + "/" + path_str
        else:
            return TagReference._common_path_default + "/" + path_str

    def create_head(
        self,
        path: PathLike,
        commit: Union["SymbolicReference", "str"] = "HEAD",
        force: bool = False,
        logmsg: Optional[str] = None,
    ) -> "Head":
        """Create a new head within the repository.

        :note:
            For more documentation, please see the
            :meth:`Head.create <git.refs.head.Head.create>` method.

        :return:
            Newly created :class:`~git.refs.head.Head` Reference.
        """
        return Head.create(self, path, commit, logmsg, force)

    def delete_head(self, *heads: "Union[str, Head]", **kwargs: Any) -> None:
        """Delete the given heads.

        :param kwargs:
            Additional keyword arguments to be passed to :manpage:`git-branch(1)`.
        """
        return Head.delete(self, *heads, **kwargs)

    def create_tag(
        self,
        path: PathLike,
        ref: Union[str, "SymbolicReference"] = "HEAD",
        message: Optional[str] = None,
        force: bool = False,
        **kwargs: Any,
    ) -> TagReference:
        """Create a new tag reference.

        :note:
            For more documentation, please see the
            :meth:`TagReference.create <git.refs.tag.TagReference.create>` method.

        :return:
            :class:`~git.refs.tag.TagReference` object
        """
        return TagReference.create(self, path, ref, message, force, **kwargs)

    def delete_tag(self, *tags: TagReference) -> None:
        """Delete the given tag references."""
        return TagReference.delete(self, *tags)

    def create_remote(self, name: str, url: str, **kwargs: Any) -> Remote:
        """Create a new remote.

        For more information, please see the documentation of the
        :meth:`Remote.create <git.remote.Remote.create>` method.

        :return:
            :class:`~git.remote.Remote` reference
        """
        return Remote.create(self, name, url, **kwargs)

    def delete_remote(self, remote: "Remote") -> str:
        """Delete the given remote."""
        return Remote.remove(self, remote)

    def _get_config_path(self, config_level: Lit_config_levels, git_dir: Optional[PathLike] = None) -> str:
        if git_dir is None:
            git_dir = self.git_dir
        # We do not support an absolute path of the gitconfig on Windows.
        # Use the global config instead.
        if sys.platform == "win32" and config_level == "system":
            config_level = "global"

        if config_level == "system":
            return "/etc/gitconfig"
        elif config_level == "user":
            config_home = os.environ.get("XDG_CONFIG_HOME") or osp.join(os.environ.get("HOME", "~"), ".config")
            return osp.normpath(osp.expanduser(osp.join(config_home, "git", "config")))
        elif config_level == "global":
            return osp.normpath(osp.expanduser("~/.gitconfig"))
        elif config_level == "repository":
            repo_dir = self._common_dir or git_dir
            if not repo_dir:
                raise NotADirectoryError
            else:
                return osp.normpath(osp.join(repo_dir, "config"))
        else:
            assert_never(  # type: ignore[unreachable]
                config_level,
                ValueError(f"Invalid configuration level: {config_level!r}"),
            )

    def config_reader(
        self,
        config_level: Optional[Lit_config_levels] = None,
    ) -> GitConfigParser:
        """
        :return:
            :class:`~git.config.GitConfigParser` allowing to read the full git
            configuration, but not to write it.

            The configuration will include values from the system, user and repository
            configuration files.

        :param config_level:
            For possible values, see the :meth:`config_writer` method. If ``None``, all
            applicable levels will be used. Specify a level in case you know which file
            you wish to read to prevent reading multiple files.

        :note:
            On Windows, system configuration cannot currently be read as the path is
            unknown, instead the global path will be used.
        """
        return self._config_reader(config_level=config_level)

    def _config_reader(
        self,
        config_level: Optional[Lit_config_levels] = None,
        git_dir: Optional[PathLike] = None,
    ) -> GitConfigParser:
        if config_level is None:
            files = [
                self._get_config_path(cast(Lit_config_levels, f), git_dir)
                for f in self.config_level
                if cast(Lit_config_levels, f)
            ]
        else:
            files = [self._get_config_path(config_level, git_dir)]
        return GitConfigParser(files, read_only=True, repo=self)

    def config_writer(self, config_level: Lit_config_levels = "repository") -> GitConfigParser:
        """
        :return:
            A :class:`~git.config.GitConfigParser` allowing to write values of the
            specified configuration file level. Config writers should be retrieved, used
            to change the configuration, and written right away as they will lock the
            configuration file in question and prevent other's to write it.

        :param config_level:
            One of the following values:

            * ``"system"`` = system wide configuration file
            * ``"global"`` = user level configuration file
            * ``"`repository"`` = configuration file for this repository only
        """
        return GitConfigParser(self._get_config_path(config_level), read_only=False, repo=self, merge_includes=False)

    def commit(self, rev: Union[str, Commit_ish, None] = None) -> Commit:
        """The :class:`~git.objects.commit.Commit` object for the specified revision.

        :param rev:
            Revision specifier, see :manpage:`git-rev-parse(1)` for viable options.

        :return:
            :class:`~git.objects.commit.Commit`
        """
        if rev is None:
            return self.head.commit
        return self.rev_parse(str(rev) + "^0")

    def iter_trees(self, *args: Any, **kwargs: Any) -> Iterator["Tree"]:
        """:return: Iterator yielding :class:`~git.objects.tree.Tree` objects

        :note:
            Accepts all arguments known to the :meth:`iter_commits` method.
        """
        return (c.tree for c in self.iter_commits(*args, **kwargs))

    def tree(self, rev: Union[Tree_ish, str, None] = None) -> "Tree":
        """The :class:`~git.objects.tree.Tree` object for the given tree-ish revision.

        Examples::

              repo.tree(repo.heads[0])

        :param rev:
            A revision pointing to a Treeish (being a commit or tree).

        :return:
            :class:`~git.objects.tree.Tree`

        :note:
            If you need a non-root level tree, find it by iterating the root tree.
            Otherwise it cannot know about its path relative to the repository root and
            subsequent operations might have unexpected results.
        """
        if rev is None:
            return self.head.commit.tree
        return self.rev_parse(str(rev) + "^{tree}")

    def iter_commits(
        self,
        rev: Union[str, Commit, "SymbolicReference", None] = None,
        paths: Union[PathLike, Sequence[PathLike]] = "",
        **kwargs: Any,
    ) -> Iterator[Commit]:
        """An iterator of :class:`~git.objects.commit.Commit` objects representing the
        history of a given ref/commit.

        :param rev:
            Revision specifier, see :manpage:`git-rev-parse(1)` for viable options.
            If ``None``, the active branch will be used.

        :param paths:
            An optional path or a list of paths. If set, only commits that include the
            path or paths will be returned.

        :param kwargs:
            Arguments to be passed to :manpage:`git-rev-list(1)`.
            Common ones are ``max_count`` and ``skip``.

        :note:
            To receive only commits between two named revisions, use the
            ``"revA...revB"`` revision specifier.

        :return:
            Iterator of :class:`~git.objects.commit.Commit` objects
        """
        if rev is None:
            rev = self.head.commit

        return Commit.iter_items(self, rev, paths, **kwargs)

    def merge_base(self, *rev: TBD, **kwargs: Any) -> List[Commit]:
        R"""Find the closest common ancestor for the given revision
        (:class:`~git.objects.commit.Commit`\s, :class:`~git.refs.tag.Tag`\s,
        :class:`~git.refs.reference.Reference`\s, etc.).

        :param rev:
            At least two revs to find the common ancestor for.

        :param kwargs:
            Additional arguments to be passed to the ``repo.git.merge_base()`` command
            which does all the work.

        :return:
            A list of :class:`~git.objects.commit.Commit` objects. If ``--all`` was
            not passed as a keyword argument, the list will have at max one
            :class:`~git.objects.commit.Commit`, or is empty if no common merge base
            exists.

        :raise ValueError:
            If fewer than two revisions are provided.
        """
        if len(rev) < 2:
            raise ValueError("Please specify at least two revs, got only %i" % len(rev))
        # END handle input

        res: List[Commit] = []
        try:
            lines: List[str] = self.git.merge_base(*rev, **kwargs).splitlines()
        except GitCommandError as err:
            if err.status == 128:
                raise
            # END handle invalid rev
            # Status code 1 is returned if there is no merge-base.
            # (See: https://github.com/git/git/blob/v2.44.0/builtin/merge-base.c#L19)
            return res
        # END exception handling

        for line in lines:
            res.append(self.commit(line))
        # END for each merge-base

        return res

    def is_ancestor(self, ancestor_rev: Commit, rev: Commit) -> bool:
        """Check if a commit is an ancestor of another.

        :param ancestor_rev:
            Rev which should be an ancestor.

        :param rev:
            Rev to test against `ancestor_rev`.

        :return:
            ``True`` if `ancestor_rev` is an ancestor to `rev`.
        """
        try:
            self.git.merge_base(ancestor_rev, rev, is_ancestor=True)
        except GitCommandError as err:
            if err.status == 1:
                return False
            raise
        return True

    def is_valid_object(self, sha: str, object_type: Union[str, None] = None) -> bool:
        try:
            complete_sha = self.odb.partial_to_complete_sha_hex(sha)
            object_info = self.odb.info(complete_sha)
            if object_type:
                if object_info.type == object_type.encode():
                    return True
                else:
                    _logger.debug(
                        "Commit hash points to an object of type '%s'. Requested were objects of type '%s'",
                        object_info.type.decode(),
                        object_type,
                    )
                    return False
            else:
                return True
        except BadObject:
            _logger.debug("Commit hash is invalid.")
            return False

    def _get_daemon_export(self) -> bool:
        if self.git_dir:
            filename = osp.join(self.git_dir, self.DAEMON_EXPORT_FILE)
        return osp.exists(filename)

    def _set_daemon_export(self, value: object) -> None:
        if self.git_dir:
            filename = osp.join(self.git_dir, self.DAEMON_EXPORT_FILE)
        fileexists = osp.exists(filename)
        if value and not fileexists:
            touch(filename)
        elif not value and fileexists:
            os.unlink(filename)

    daemon_export = property(
        _get_daemon_export,
        _set_daemon_export,
        doc="If True, git-daemon may export this repository",
    )
    del _get_daemon_export
    del _set_daemon_export

    def _get_alternates(self) -> List[str]:
        """The list of alternates for this repo from which objects can be retrieved.

        :return:
            List of strings being pathnames of alternates
        """
        if self.git_dir:
            alternates_path = osp.join(self.git_dir, "objects", "info", "alternates")

        if osp.exists(alternates_path):
            with open(alternates_path, "rb") as f:
                alts = f.read().decode(defenc)
            return alts.strip().splitlines()
        return []

    def _set_alternates(self, alts: List[str]) -> None:
        """Set the alternates.

        :param alts:
            The array of string paths representing the alternates at which git should
            look for objects, i.e. ``/home/user/repo/.git/objects``.

        :raise git.exc.NoSuchPathError:

        :note:
            The method does not check for the existence of the paths in `alts`, as the
            caller is responsible.
        """
        alternates_path = osp.join(self.common_dir, "objects", "info", "alternates")
        if not alts:
            if osp.isfile(alternates_path):
                os.remove(alternates_path)
        else:
            with open(alternates_path, "wb") as f:
                f.write("\n".join(alts).encode(defenc))

    alternates = property(
        _get_alternates,
        _set_alternates,
        doc="Retrieve a list of alternates paths or set a list paths to be used as alternates",
    )

    def is_dirty(
        self,
        index: bool = True,
        working_tree: bool = True,
        untracked_files: bool = False,
        submodules: bool = True,
        path: Optional[PathLike] = None,
    ) -> bool:
        """
        :return:
            ``True`` if the repository is considered dirty. By default it will react
            like a :manpage:`git-status(1)` without untracked files, hence it is dirty
            if the index or the working copy have changes.
        """
        if self._bare:
            # Bare repositories with no associated working directory are
            # always considered to be clean.
            return False

        # Start from the one which is fastest to evaluate.
        default_args = ["--abbrev=40", "--full-index", "--raw"]
        if not submodules:
            default_args.append("--ignore-submodules")
        if path:
            default_args.extend(["--", str(path)])
        if index:
            # diff index against HEAD.
            if osp.isfile(self.index.path) and len(self.git.diff("--cached", *default_args)):
                return True
        # END index handling
        if working_tree:
            # diff index against working tree.
            if len(self.git.diff(*default_args)):
                return True
        # END working tree handling
        if untracked_files:
            if len(self._get_untracked_files(path, ignore_submodules=not submodules)):
                return True
        # END untracked files
        return False

    @property
    def untracked_files(self) -> List[str]:
        """
        :return:
            list(str,...)

            Files currently untracked as they have not been staged yet. Paths are
            relative to the current working directory of the git command.

        :note:
            Ignored files will not appear here, i.e. files mentioned in ``.gitignore``.

        :note:
            This property is expensive, as no cache is involved. To process the result,
            please consider caching it yourself.
        """
        return self._get_untracked_files()

    def _get_untracked_files(self, *args: Any, **kwargs: Any) -> List[str]:
        # Make sure we get all files, not only untracked directories.
        proc = self.git.status(*args, porcelain=True, untracked_files=True, as_process=True, **kwargs)
        # Untracked files prefix in porcelain mode
        prefix = "?? "
        untracked_files = []
        for line in proc.stdout:
            line = line.decode(defenc)
            if not line.startswith(prefix):
                continue
            filename = line[len(prefix) :].rstrip("\n")
            # Special characters are escaped
            if filename[0] == filename[-1] == '"':
                filename = filename[1:-1]
                # WHATEVER ... it's a mess, but works for me
                filename = filename.encode("ascii").decode("unicode_escape").encode("latin1").decode(defenc)
            untracked_files.append(filename)
        finalize_process(proc)
        return untracked_files

    def ignored(self, *paths: PathLike) -> List[str]:
        """Checks if paths are ignored via ``.gitignore``.

        This does so using the :manpage:`git-check-ignore(1)` method.

        :param paths:
            List of paths to check whether they are ignored or not.

        :return:
            Subset of those paths which are ignored
        """
        try:
            proc: str = self.git.check_ignore(*paths)
        except GitCommandError as err:
            if err.status == 1:
                # If return code is 1, this means none of the items in *paths are
                # ignored by Git, so return an empty list.
                return []
            else:
                # Raise the exception on all other return codes.
                raise

        return proc.replace("\\\\", "\\").replace('"', "").split("\n")

    @property
    def active_branch(self) -> Head:
        """The name of the currently active branch.

        :raise TypeError:
            If HEAD is detached.

        :return:
            :class:`~git.refs.head.Head` to the active branch
        """
        # reveal_type(self.head.reference)  # => Reference
        return self.head.reference

    def blame_incremental(self, rev: str | HEAD | None, file: str, **kwargs: Any) -> Iterator["BlameEntry"]:
        """Iterator for blame information for the given file at the given revision.

        Unlike :meth:`blame`, this does not return the actual file's contents, only a
        stream of :class:`BlameEntry` tuples.

        :param rev:
            Revision specifier. If ``None``, the blame will include all the latest
            uncommitted changes. Otherwise, anything successfully parsed by
            :manpage:`git-rev-parse(1)` is a valid option.

        :return:
            Lazy iterator of :class:`BlameEntry` tuples, where the commit indicates the
            commit to blame for the line, and range indicates a span of line numbers in
            the resulting file.

        If you combine all line number ranges outputted by this command, you should get
        a continuous range spanning all line numbers in the file.
        """

        data: bytes = self.git.blame(rev, "--", file, p=True, incremental=True, stdout_as_string=False, **kwargs)
        commits: Dict[bytes, Commit] = {}

        stream = (line for line in data.split(b"\n") if line)
        while True:
            try:
                # When exhausted, causes a StopIteration, terminating this function.
                line = next(stream)
            except StopIteration:
                return
            split_line = line.split()
            hexsha, orig_lineno_b, lineno_b, num_lines_b = split_line
            lineno = int(lineno_b)
            num_lines = int(num_lines_b)
            orig_lineno = int(orig_lineno_b)
            if hexsha not in commits:
                # Now read the next few lines and build up a dict of properties for this
                # commit.
                props: Dict[bytes, bytes] = {}
                while True:
                    try:
                        line = next(stream)
                    except StopIteration:
                        return
                    if line == b"boundary":
                        # "boundary" indicates a root commit and occurs instead of the
                        # "previous" tag.
                        continue

                    tag, value = line.split(b" ", 1)
                    props[tag] = value
                    if tag == b"filename":
                        # "filename" formally terminates the entry for --incremental.
                        orig_filename = value
                        break

                c = Commit(
                    self,
                    hex_to_bin(hexsha),
                    author=Actor(
                        safe_decode(props[b"author"]),
                        safe_decode(props[b"author-mail"].lstrip(b"<").rstrip(b">")),
                    ),
                    authored_date=int(props[b"author-time"]),
                    committer=Actor(
                        safe_decode(props[b"committer"]),
                        safe_decode(props[b"committer-mail"].lstrip(b"<").rstrip(b">")),
                    ),
                    committed_date=int(props[b"committer-time"]),
                )
                commits[hexsha] = c
            else:
                # Discard all lines until we find "filename" which is guaranteed to be
                # the last line.
                while True:
                    try:
                        # Will fail if we reach the EOF unexpectedly.
                        line = next(stream)
                    except StopIteration:
                        return
                    tag, value = line.split(b" ", 1)
                    if tag == b"filename":
                        orig_filename = value
                        break

            yield BlameEntry(
                commits[hexsha],
                range(lineno, lineno + num_lines),
                safe_decode(orig_filename),
                range(orig_lineno, orig_lineno + num_lines),
            )

    def blame(
        self,
        rev: Union[str, HEAD, None],
        file: str,
        incremental: bool = False,
        rev_opts: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[List[Commit | List[str | bytes] | None]] | Iterator[BlameEntry] | None:
        """The blame information for the given file at the given revision.

        :param rev:
            Revision specifier. If ``None``, the blame will include all the latest
            uncommitted changes. Otherwise, anything successfully parsed by
            :manpage:`git-rev-parse(1)` is a valid option.

        :return:
            list: [git.Commit, list: [<line>]]

            A list of lists associating a :class:`~git.objects.commit.Commit` object
            with a list of lines that changed within the given commit. The
            :class:`~git.objects.commit.Commit` objects will be given in order of
            appearance.
        """
        if incremental:
            return self.blame_incremental(rev, file, **kwargs)
        rev_opts = rev_opts or []
        data: bytes = self.git.blame(rev, *rev_opts, "--", file, p=True, stdout_as_string=False, **kwargs)
        commits: Dict[str, Commit] = {}
        blames: List[List[Commit | List[str | bytes] | None]] = []

        class InfoTD(TypedDict, total=False):
            sha: str
            id: str
            filename: str
            summary: str
            author: str
            author_email: str
            author_date: int
            committer: str
            committer_email: str
            committer_date: int

        info: InfoTD = {}

        keepends = True
        for line_bytes in data.splitlines(keepends):
            try:
                line_str = line_bytes.rstrip().decode(defenc)
            except UnicodeDecodeError:
                firstpart = ""
                parts = []
                is_binary = True
            else:
                # As we don't have an idea when the binary data ends, as it could
                # contain multiple newlines in the process. So we rely on being able to
                # decode to tell us what it is. This can absolutely fail even on text
                # files, but even if it does, we should be fine treating it as binary
                # instead.
                parts = self.re_whitespace.split(line_str, 1)
                firstpart = parts[0]
                is_binary = False
            # END handle decode of line

            if self.re_hexsha_only.search(firstpart):
                # handles
                # 634396b2f541a9f2d58b00be1a07f0c358b999b3 1 1 7        - indicates blame-data start
                # 634396b2f541a9f2d58b00be1a07f0c358b999b3 2 2          - indicates
                # another line of blame with the same data
                digits = parts[-1].split(" ")
                if len(digits) == 3:
                    info = {"id": firstpart}
                    blames.append([None, []])
                elif info["id"] != firstpart:
                    info = {"id": firstpart}
                    blames.append([commits.get(firstpart), []])
                # END blame data initialization
            else:
                m = self.re_author_committer_start.search(firstpart)
                if m:
                    # handles:
                    # author Tom Preston-Werner
                    # author-mail <tom@mojombo.com>
                    # author-time 1192271832
                    # author-tz -0700
                    # committer Tom Preston-Werner
                    # committer-mail <tom@mojombo.com>
                    # committer-time 1192271832
                    # committer-tz -0700  - IGNORED BY US
                    role = m.group(0)
                    if role == "author":
                        if firstpart.endswith("-mail"):
                            info["author_email"] = parts[-1]
                        elif firstpart.endswith("-time"):
                            info["author_date"] = int(parts[-1])
                        elif role == firstpart:
                            info["author"] = parts[-1]
                    elif role == "committer":
                        if firstpart.endswith("-mail"):
                            info["committer_email"] = parts[-1]
                        elif firstpart.endswith("-time"):
                            info["committer_date"] = int(parts[-1])
                        elif role == firstpart:
                            info["committer"] = parts[-1]
                    # END distinguish mail,time,name
                else:
                    # handle
                    # filename lib/grit.rb
                    # summary add Blob
                    # <and rest>
                    if firstpart.startswith("filename"):
                        info["filename"] = parts[-1]
                    elif firstpart.startswith("summary"):
                        info["summary"] = parts[-1]
                    elif firstpart == "":
                        if info:
                            sha = info["id"]
                            c = commits.get(sha)
                            if c is None:
                                c = Commit(
                                    self,
                                    hex_to_bin(sha),
                                    author=Actor._from_string(f"{info['author']} {info['author_email']}"),
                                    authored_date=info["author_date"],
                                    committer=Actor._from_string(f"{info['committer']} {info['committer_email']}"),
                                    committed_date=info["committer_date"],
                                )
                                commits[sha] = c
                            blames[-1][0] = c
                            # END if commit objects needs initial creation

                            if blames[-1][1] is not None:
                                line: str | bytes
                                if not is_binary:
                                    if line_str and line_str[0] == "\t":
                                        line_str = line_str[1:]
                                    line = line_str
                                else:
                                    line = line_bytes
                                    # NOTE: We are actually parsing lines out of binary
                                    # data, which can lead to the binary being split up
                                    # along the newline separator. We will append this
                                    # to the blame we are currently looking at, even
                                    # though it should be concatenated with the last
                                    # line we have seen.
                                blames[-1][1].append(line)

                            info = {"id": sha}
                        # END if we collected commit info
                    # END distinguish filename,summary,rest
                # END distinguish author|committer vs filename,summary,rest
            # END distinguish hexsha vs other information
        return blames

    @classmethod
    def init(
        cls,
        path: Union[PathLike, None] = None,
        mkdir: bool = True,
        odbt: Type[GitCmdObjectDB] = GitCmdObjectDB,
        expand_vars: bool = True,
        **kwargs: Any,
    ) -> "Repo":
        """Initialize a git repository at the given path if specified.

        :param path:
            The full path to the repo (traditionally ends with ``/<name>.git``). Or
            ``None``, in which case the repository will be created in the current
            working directory.

        :param mkdir:
            If specified, will create the repository directory if it doesn't already
            exist. Creates the directory with a mode=0755.
            Only effective if a path is explicitly given.

        :param odbt:
            Object DataBase type - a type which is constructed by providing the
            directory containing the database objects, i.e. ``.git/objects``. It will be
            used to access all object data.

        :param expand_vars:
            If specified, environment variables will not be escaped. This can lead to
            information disclosure, allowing attackers to access the contents of
            environment variables.

        :param kwargs:
            Keyword arguments serving as additional options to the
            :manpage:`git-init(1)` command.

        :return:
            :class:`Repo` (the newly created repo)
        """
        if path:
            path = expand_path(path, expand_vars)
        if mkdir and path and not osp.exists(path):
            os.makedirs(path, 0o755)

        # git command automatically chdir into the directory
        git = cls.GitCommandWrapperType(path)
        git.init(**kwargs)
        return cls(path, odbt=odbt)

    @classmethod
    def _clone(
        cls,
        git: "Git",
        url: PathLike,
        path: PathLike,
        odb_default_type: Type[GitCmdObjectDB],
        progress: Union["RemoteProgress", "UpdateProgress", Callable[..., "RemoteProgress"], None] = None,
        multi_options: Optional[List[str]] = None,
        allow_unsafe_protocols: bool = False,
        allow_unsafe_options: bool = False,
        **kwargs: Any,
    ) -> "Repo":
        odbt = kwargs.pop("odbt", odb_default_type)

        # When pathlib.Path or other class-based path is passed
        if not isinstance(path, str):
            path = str(path)

        ## A bug win cygwin's Git, when `--bare` or `--separate-git-dir`
        #  it prepends the cwd or(?) the `url` into the `path, so::
        #        git clone --bare  /cygwin/d/foo.git  C:\\Work
        #  becomes::
        #        git clone --bare  /cygwin/d/foo.git  /cygwin/d/C:\\Work
        #
        clone_path = Git.polish_url(path) if Git.is_cygwin() and "bare" in kwargs else path
        sep_dir = kwargs.get("separate_git_dir")
        if sep_dir:
            kwargs["separate_git_dir"] = Git.polish_url(sep_dir)
        multi = None
        if multi_options:
            multi = shlex.split(" ".join(multi_options))

        if not allow_unsafe_protocols:
            Git.check_unsafe_protocols(str(url))
        if not allow_unsafe_options:
            Git.check_unsafe_options(options=list(kwargs.keys()), unsafe_options=cls.unsafe_git_clone_options)
        if not allow_unsafe_options and multi_options:
            Git.check_unsafe_options(options=multi_options, unsafe_options=cls.unsafe_git_clone_options)

        proc = git.clone(
            multi,
            "--",
            Git.polish_url(str(url)),
            clone_path,
            with_extended_output=True,
            as_process=True,
            v=True,
            universal_newlines=True,
            **add_progress(kwargs, git, progress),
        )
        if progress:
            handle_process_output(
                proc,
                None,
                to_progress_instance(progress).new_message_handler(),
                finalize_process,
                decode_streams=False,
            )
        else:
            (stdout, stderr) = proc.communicate()
            cmdline = getattr(proc, "args", "")
            cmdline = remove_password_if_present(cmdline)

            _logger.debug("Cmd(%s)'s unused stdout: %s", cmdline, stdout)
            finalize_process(proc, stderr=stderr)

        # Our git command could have a different working dir than our actual
        # environment, hence we prepend its working dir if required.
        if not osp.isabs(path):
            path = osp.join(git._working_dir, path) if git._working_dir is not None else path

        repo = cls(path, odbt=odbt)

        # Retain env values that were passed to _clone().
        repo.git.update_environment(**git.environment())

        # Adjust remotes - there may be operating systems which use backslashes, These
        # might be given as initial paths, but when handling the config file that
        # contains the remote from which we were clones, git stops liking it as it will
        # escape the backslashes. Hence we undo the escaping just to be sure.
        if repo.remotes:
            with repo.remotes[0].config_writer as writer:
                writer.set_value("url", Git.polish_url(repo.remotes[0].url))
        # END handle remote repo
        return repo

    def clone(
        self,
        path: PathLike,
        progress: Optional[CallableProgress] = None,
        multi_options: Optional[List[str]] = None,
        allow_unsafe_protocols: bool = False,
        allow_unsafe_options: bool = False,
        **kwargs: Any,
    ) -> "Repo":
        """Create a clone from this repository.

        :param path:
            The full path of the new repo (traditionally ends with ``./<name>.git``).

        :param progress:
            See :meth:`Remote.push <git.remote.Remote.push>`.

        :param multi_options:
            A list of :manpage:`git-clone(1)` options that can be provided multiple
            times.

            One option per list item which is passed exactly as specified to clone.
            For example::

                [
                    "--config core.filemode=false",
                    "--config core.ignorecase",
                    "--recurse-submodule=repo1_path",
                    "--recurse-submodule=repo2_path",
                ]

        :param allow_unsafe_protocols:
            Allow unsafe protocols to be used, like ``ext``.

        :param allow_unsafe_options:
            Allow unsafe options to be used, like ``--upload-pack``.

        :param kwargs:
            * ``odbt`` = ObjectDatabase Type, allowing to determine the object database
              implementation used by the returned :class:`Repo` instance.
            * All remaining keyword arguments are given to the :manpage:`git-clone(1)`
              command.

        :return:
            :class:`Repo` (the newly cloned repo)
        """
        return self._clone(
            self.git,
            self.common_dir,
            path,
            type(self.odb),
            progress,
            multi_options,
            allow_unsafe_protocols=allow_unsafe_protocols,
            allow_unsafe_options=allow_unsafe_options,
            **kwargs,
        )

    @classmethod
    def clone_from(
        cls,
        url: PathLike,
        to_path: PathLike,
        progress: CallableProgress = None,
        env: Optional[Mapping[str, str]] = None,
        multi_options: Optional[List[str]] = None,
        allow_unsafe_protocols: bool = False,
        allow_unsafe_options: bool = False,
        **kwargs: Any,
    ) -> "Repo":
        """Create a clone from the given URL.

        :param url:
            Valid git url, see: https://git-scm.com/docs/git-clone#URLS

        :param to_path:
            Path to which the repository should be cloned to.

        :param progress:
            See :meth:`Remote.push <git.remote.Remote.push>`.

        :param env:
            Optional dictionary containing the desired environment variables.

            Note: Provided variables will be used to update the execution environment
            for ``git``. If some variable is not specified in `env` and is defined in
            :attr:`os.environ`, value from :attr:`os.environ` will be used. If you want
            to unset some variable, consider providing empty string as its value.

        :param multi_options:
            See the :meth:`clone` method.

        :param allow_unsafe_protocols:
            Allow unsafe protocols to be used, like ``ext``.

        :param allow_unsafe_options:
            Allow unsafe options to be used, like ``--upload-pack``.

        :param kwargs:
            See the :meth:`clone` method.

        :return:
            :class:`Repo` instance pointing to the cloned directory.
        """
        git = cls.GitCommandWrapperType(os.getcwd())
        if env is not None:
            git.update_environment(**env)
        return cls._clone(
            git,
            url,
            to_path,
            GitCmdObjectDB,
            progress,
            multi_options,
            allow_unsafe_protocols=allow_unsafe_protocols,
            allow_unsafe_options=allow_unsafe_options,
            **kwargs,
        )

    def archive(
        self,
        ostream: Union[TextIO, BinaryIO],
        treeish: Optional[str] = None,
        prefix: Optional[str] = None,
        **kwargs: Any,
    ) -> Repo:
        """Archive the tree at the given revision.

        :param ostream:
            File-compatible stream object to which the archive will be written as bytes.

        :param treeish:
            The treeish name/id, defaults to active branch.

        :param prefix:
            The optional prefix to prepend to each filename in the archive.

        :param kwargs:
            Additional arguments passed to :manpage:`git-archive(1)`:

            * Use the ``format`` argument to define the kind of format. Use specialized
              ostreams to write any format supported by Python.
            * You may specify the special ``path`` keyword, which may either be a
              repository-relative path to a directory or file to place into the archive,
              or a list or tuple of multiple paths.

        :raise git.exc.GitCommandError:
            If something went wrong.

        :return:
            self
        """
        if treeish is None:
            treeish = self.head.commit
        if prefix and "prefix" not in kwargs:
            kwargs["prefix"] = prefix
        kwargs["output_stream"] = ostream
        path = kwargs.pop("path", [])
        path = cast(Union[PathLike, List[PathLike], Tuple[PathLike, ...]], path)
        if not isinstance(path, (tuple, list)):
            path = [path]
        # END ensure paths is list (or tuple)
        self.git.archive("--", treeish, *path, **kwargs)
        return self

    def has_separate_working_tree(self) -> bool:
        """
        :return:
            True if our :attr:`git_dir` is not at the root of our
            :attr:`working_tree_dir`, but a ``.git`` file with a platform-agnostic
            symbolic link. Our :attr:`git_dir` will be wherever the ``.git`` file points
            to.

        :note:
            Bare repositories will always return ``False`` here.
        """
        if self.bare:
            return False
        if self.working_tree_dir:
            return osp.isfile(osp.join(self.working_tree_dir, ".git"))
        else:
            return False  # Or raise Error?

    rev_parse = rev_parse

    def __repr__(self) -> str:
        clazz = self.__class__
        return "<%s.%s %r>" % (clazz.__module__, clazz.__name__, self.git_dir)

    def currently_rebasing_on(self) -> Commit | None:
        """
        :return:
            The commit which is currently being replayed while rebasing.

            ``None`` if we are not currently rebasing.
        """
        if self.git_dir:
            rebase_head_file = osp.join(self.git_dir, "REBASE_HEAD")
        if not osp.isfile(rebase_head_file):
            return None
        with open(rebase_head_file, "rt") as f:
            content = f.readline().strip()
        return self.commit(content)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\remote\webdriver.py ===
# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""The WebDriver implementation."""

import base64
import contextlib
import copy
import os
import pkgutil
import tempfile
import types
import warnings
import zipfile
from abc import ABCMeta
from base64 import b64decode, urlsafe_b64encode
from contextlib import asynccontextmanager, contextmanager
from importlib import import_module
from typing import Any, Dict, List, Optional, Type, Union

from selenium.common.exceptions import (
    InvalidArgumentException,
    JavascriptException,
    NoSuchCookieException,
    NoSuchElementException,
    WebDriverException,
)
from selenium.webdriver.common.bidi.browser import Browser
from selenium.webdriver.common.bidi.browsing_context import BrowsingContext
from selenium.webdriver.common.bidi.network import Network
from selenium.webdriver.common.bidi.script import Script
from selenium.webdriver.common.bidi.session import Session
from selenium.webdriver.common.bidi.storage import Storage
from selenium.webdriver.common.bidi.webextension import WebExtension
from selenium.webdriver.common.by import By
from selenium.webdriver.common.options import ArgOptions, BaseOptions
from selenium.webdriver.common.print_page_options import PrintOptions
from selenium.webdriver.common.timeouts import Timeouts
from selenium.webdriver.common.virtual_authenticator import (
    Credential,
    VirtualAuthenticatorOptions,
    required_virtual_authenticator,
)
from selenium.webdriver.support.relative_locator import RelativeBy

from ..common.fedcm.dialog import Dialog
from .bidi_connection import BidiConnection
from .client_config import ClientConfig
from .command import Command
from .errorhandler import ErrorHandler
from .fedcm import FedCM
from .file_detector import FileDetector, LocalFileDetector
from .locator_converter import LocatorConverter
from .mobile import Mobile
from .remote_connection import RemoteConnection
from .script_key import ScriptKey
from .shadowroot import ShadowRoot
from .switch_to import SwitchTo
from .webelement import WebElement
from .websocket_connection import WebSocketConnection

cdp = None
devtools = None


def import_cdp():
    global cdp
    if not cdp:
        cdp = import_module("selenium.webdriver.common.bidi.cdp")


def _create_caps(caps):
    """Makes a W3C alwaysMatch capabilities object.

    Filters out capability names that are not in the W3C spec. Spec-compliant
    drivers will reject requests containing unknown capability names.

    Moves the Firefox profile, if present, from the old location to the new Firefox
    options object.

    Parameters:
    -----------
    caps : dict
        - A dictionary of capabilities requested by the caller.
    """
    caps = copy.deepcopy(caps)
    always_match = {}
    for k, v in caps.items():
        always_match[k] = v
    return {"capabilities": {"firstMatch": [{}], "alwaysMatch": always_match}}


def get_remote_connection(
    capabilities: dict,
    command_executor: Union[str, RemoteConnection],
    keep_alive: bool,
    ignore_local_proxy: bool,
    client_config: Optional[ClientConfig] = None,
) -> RemoteConnection:
    if isinstance(command_executor, str):
        client_config = client_config or ClientConfig(remote_server_addr=command_executor)
        client_config.remote_server_addr = command_executor
        command_executor = RemoteConnection(client_config=client_config)
    from selenium.webdriver.chrome.remote_connection import ChromeRemoteConnection
    from selenium.webdriver.edge.remote_connection import EdgeRemoteConnection
    from selenium.webdriver.firefox.remote_connection import FirefoxRemoteConnection
    from selenium.webdriver.safari.remote_connection import SafariRemoteConnection

    candidates = [ChromeRemoteConnection, EdgeRemoteConnection, SafariRemoteConnection, FirefoxRemoteConnection]
    handler = next((c for c in candidates if c.browser_name == capabilities.get("browserName")), RemoteConnection)

    return handler(
        remote_server_addr=command_executor,
        keep_alive=keep_alive,
        ignore_proxy=ignore_local_proxy,
        client_config=client_config,
    )


def create_matches(options: List[BaseOptions]) -> Dict:
    capabilities = {"capabilities": {}}
    opts = []
    for opt in options:
        opts.append(opt.to_capabilities())
    opts_size = len(opts)
    samesies = {}

    # Can not use bitwise operations on the dicts or lists due to
    # https://bugs.python.org/issue38210
    for i in range(opts_size):
        min_index = i
        if i + 1 < opts_size:
            first_keys = opts[min_index].keys()

            for kys in first_keys:
                if kys in opts[i + 1].keys():
                    if opts[min_index][kys] == opts[i + 1][kys]:
                        samesies.update({kys: opts[min_index][kys]})

    always = {}
    for k, v in samesies.items():
        always[k] = v

    for i in opts:
        for k in always:
            del i[k]

    capabilities["capabilities"]["alwaysMatch"] = always
    capabilities["capabilities"]["firstMatch"] = opts

    return capabilities


class BaseWebDriver(metaclass=ABCMeta):
    """Abstract Base Class for all Webdriver subtypes.

    ABC's allow custom implementations of Webdriver to be registered so
    that isinstance type checks will succeed.
    """


class WebDriver(BaseWebDriver):
    """Controls a browser by sending commands to a remote server. This server
    is expected to be running the WebDriver wire protocol as defined at
    https://www.selenium.dev/documentation/legacy/json_wire_protocol/.

    Attributes:
    -----------
    session_id - String ID of the browser session started and controlled by this WebDriver.
    capabilities - Dictionary of effective capabilities of this browser session as returned
        by the remote server. See https://www.selenium.dev/documentation/legacy/desired_capabilities/
    command_executor : str or remote_connection.RemoteConnection object used to execute commands.
    error_handler - errorhandler.ErrorHandler object used to handle errors.
    """

    _web_element_cls = WebElement
    _shadowroot_cls = ShadowRoot

    def __init__(
        self,
        command_executor: Union[str, RemoteConnection] = "http://127.0.0.1:4444",
        keep_alive: bool = True,
        file_detector: Optional[FileDetector] = None,
        options: Optional[Union[BaseOptions, List[BaseOptions]]] = None,
        locator_converter: Optional[LocatorConverter] = None,
        web_element_cls: Optional[type] = None,
        client_config: Optional[ClientConfig] = None,
    ) -> None:
        """Create a new driver that will issue commands using the wire
        protocol.

        Parameters:
        -----------
        command_executor : str or remote_connection.RemoteConnection
            - Either a string representing the URL of the remote server or a custom
            remote_connection.RemoteConnection object. Defaults to 'http://127.0.0.1:4444/wd/hub'.
        keep_alive : bool (Deprecated)
            - Whether to configure remote_connection.RemoteConnection to use HTTP keep-alive. Defaults to True.
        file_detector : object or None
            - Pass a custom file detector object during instantiation. If None, the default
                LocalFileDetector() will be used.
        options : options.Options
            - Instance of a driver options.Options class.
        locator_converter : object or None
            - Custom locator converter to use. Defaults to None.
        web_element_cls : class
            - Custom class to use for web elements. Defaults to WebElement.
        client_config : object or None
            - Custom client configuration to use. Defaults to None.
        """

        if options is None:
            raise TypeError(
                "missing 1 required keyword-only argument: 'options' (instance of driver `options.Options` class)"
            )
        elif isinstance(options, list):
            capabilities = create_matches(options)
            _ignore_local_proxy = False
        else:
            capabilities = options.to_capabilities()
            _ignore_local_proxy = options._ignore_local_proxy
        self.command_executor = command_executor
        if isinstance(self.command_executor, (str, bytes)):
            self.command_executor = get_remote_connection(
                capabilities,
                command_executor=command_executor,
                keep_alive=keep_alive,
                ignore_local_proxy=_ignore_local_proxy,
                client_config=client_config,
            )
        self._is_remote = True
        self.session_id = None
        self.caps = {}
        self.pinned_scripts = {}
        self.error_handler = ErrorHandler()
        self._switch_to = SwitchTo(self)
        self._mobile = Mobile(self)
        self.file_detector = file_detector or LocalFileDetector()
        self.locator_converter = locator_converter or LocatorConverter()
        self._web_element_cls = web_element_cls or self._web_element_cls
        self._authenticator_id = None
        self.start_client()
        self.start_session(capabilities)
        self._fedcm = FedCM(self)

        self._websocket_connection = None
        self._script = None
        self._network = None
        self._browser = None
        self._bidi_session = None
        self._browsing_context = None
        self._storage = None
        self._webextension = None

    def __repr__(self):
        return f'<{type(self).__module__}.{type(self).__name__} (session="{self.session_id}")>'

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[types.TracebackType],
    ):
        self.quit()

    @contextmanager
    def file_detector_context(self, file_detector_class, *args, **kwargs):
        """Overrides the current file detector (if necessary) in limited
        context. Ensures the original file detector is set afterwards.

        Parameters:
        -----------
        file_detector_class : object
            - Class of the desired file detector. If the class is different
            from the current file_detector, then the class is instantiated with args and kwargs
            and used as a file detector during the duration of the context manager.
        args : tuple
            - Optional arguments that get passed to the file detector class during instantiation.
        kwargs : dict
            - Keyword arguments, passed the same way as args.

        Example:
        --------
        >>> with webdriver.file_detector_context(UselessFileDetector):
        >>>    someinput.send_keys('/etc/hosts')
        """
        last_detector = None
        if not isinstance(self.file_detector, file_detector_class):
            last_detector = self.file_detector
            self.file_detector = file_detector_class(*args, **kwargs)
        try:
            yield
        finally:
            if last_detector:
                self.file_detector = last_detector

    @property
    def mobile(self) -> Mobile:
        return self._mobile

    @property
    def name(self) -> str:
        """Returns the name of the underlying browser for this instance.

        Example:
        --------
        >>> name = driver.name
        """
        if "browserName" in self.caps:
            return self.caps["browserName"]
        raise KeyError("browserName not specified in session capabilities")

    def start_client(self):
        """Called before starting a new session.

        This method may be overridden to define custom startup behavior.
        """
        pass

    def stop_client(self):
        """Called after executing a quit command.

        This method may be overridden to define custom shutdown
        behavior.
        """
        pass

    def start_session(self, capabilities: dict) -> None:
        """Creates a new session with the desired capabilities.

        Parameters:
        -----------
        capabilities : dict
            - A capabilities dict to start the session with.
        """

        caps = _create_caps(capabilities)
        try:
            response = self.execute(Command.NEW_SESSION, caps)["value"]
            self.session_id = response.get("sessionId")
            self.caps = response.get("capabilities")
        except Exception:
            if hasattr(self, "service") and self.service is not None:
                self.service.stop()
            raise

    def _wrap_value(self, value):
        if isinstance(value, dict):
            converted = {}
            for key, val in value.items():
                converted[key] = self._wrap_value(val)
            return converted
        if isinstance(value, self._web_element_cls):
            return {"element-6066-11e4-a52e-4f735466cecf": value.id}
        if isinstance(value, self._shadowroot_cls):
            return {"shadow-6066-11e4-a52e-4f735466cecf": value.id}
        if isinstance(value, list):
            return list(self._wrap_value(item) for item in value)
        return value

    def create_web_element(self, element_id: str) -> WebElement:
        """Creates a web element with the specified `element_id`."""
        return self._web_element_cls(self, element_id)

    def _unwrap_value(self, value):
        if isinstance(value, dict):
            if "element-6066-11e4-a52e-4f735466cecf" in value:
                return self.create_web_element(value["element-6066-11e4-a52e-4f735466cecf"])
            if "shadow-6066-11e4-a52e-4f735466cecf" in value:
                return self._shadowroot_cls(self, value["shadow-6066-11e4-a52e-4f735466cecf"])
            for key, val in value.items():
                value[key] = self._unwrap_value(val)
            return value
        if isinstance(value, list):
            return list(self._unwrap_value(item) for item in value)
        return value

    def execute_cdp_cmd(self, cmd: str, cmd_args: dict):
        """Execute Chrome Devtools Protocol command and get returned result The
        command and command args should follow chrome devtools protocol
        domains/commands, refer to link
        https://chromedevtools.github.io/devtools-protocol/

        Parameters:
        -----------
        cmd : str,
            - Command name

        cmd_args : dict
            - Command args
            - Empty dict {} if there is no command args

        Returns:
        --------
            A dict, empty dict {} if there is no result to return.
                - To getResponseBody: {'base64Encoded': False, 'body': 'response body string'}

        Example:
        --------
        >>> driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": requestId})

        """
        return self.execute("executeCdpCommand", {"cmd": cmd, "params": cmd_args})["value"]

    def execute(self, driver_command: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Sends a command to be executed by a command.CommandExecutor.

        Parameters:
        -----------
        driver_command : str
            - The name of the command to execute as a string.

        params : dict
            - A dictionary of named Parameters to send with the command.

        Returns:
        --------
          dict - The command's JSON response loaded into a dictionary object.
        """
        params = self._wrap_value(params)

        if self.session_id:
            if not params:
                params = {"sessionId": self.session_id}
            elif "sessionId" not in params:
                params["sessionId"] = self.session_id

        response = self.command_executor.execute(driver_command, params)
        if response:
            self.error_handler.check_response(response)
            response["value"] = self._unwrap_value(response.get("value", None))
            return response
        # If the server doesn't send a response, assume the command was
        # a success
        return {"success": 0, "value": None, "sessionId": self.session_id}

    def get(self, url: str) -> None:
        """Navigate the browser to the specified URL in the current window or
        tab.

        The method does not return until the page is fully loaded (i.e. the
        onload event has fired).

        Parameters:
        -----------
        url : str
            - The URL to be opened by the browser.
            - Must include the protocol (e.g., http://, https://).

        Example:
        --------
        >>> driver = webdriver.Chrome()
        >>> driver.get("https://example.com")
        """
        self.execute(Command.GET, {"url": url})

    @property
    def title(self) -> str:
        """Returns the title of the current page.

        Example:
        --------
        >>> element = driver.find_element(By.ID, "foo")
        >>> print(element.title())
        """
        return self.execute(Command.GET_TITLE).get("value", "")

    def pin_script(self, script: str, script_key=None) -> ScriptKey:
        """Store common javascript scripts to be executed later by a unique
        hashable ID.

        Example:
        --------
        >>> script = "return document.getElementById('foo').value"
        """
        script_key_instance = ScriptKey(script_key)
        self.pinned_scripts[script_key_instance.id] = script
        return script_key_instance

    def unpin(self, script_key: ScriptKey) -> None:
        """Remove a pinned script from storage.

        Example:
        --------
        >>> driver.unpin(script_key)
        """
        try:
            self.pinned_scripts.pop(script_key.id)
        except KeyError:
            raise KeyError(f"No script with key: {script_key} existed in {self.pinned_scripts}") from None

    def get_pinned_scripts(self) -> List[str]:
        """Return a list of all pinned scripts.

        Example:
        --------
        >>> pinned_scripts = driver.get_pinned_scripts()
        """
        return list(self.pinned_scripts)

    def execute_script(self, script: str, *args):
        """Synchronously Executes JavaScript in the current window/frame.

        Parameters:
        -----------
        script : str
            - The javascript to execute.

        *args : tuple
            - Any applicable arguments for your JavaScript.

        Example:
        --------
        >>> input_id = "username"
        >>> input_value = "test_user"
        >>> driver.execute_script("document.getElementById(arguments[0]).value = arguments[1];", input_id, input_value)
        """
        if isinstance(script, ScriptKey):
            try:
                script = self.pinned_scripts[script.id]
            except KeyError:
                raise JavascriptException("Pinned script could not be found")

        converted_args = list(args)
        command = Command.W3C_EXECUTE_SCRIPT

        return self.execute(command, {"script": script, "args": converted_args})["value"]

    def execute_async_script(self, script: str, *args):
        """Asynchronously Executes JavaScript in the current window/frame.

        Parameters:
        -----------
        script : str
            - The javascript to execute.

        *args : tuple
            - Any applicable arguments for your JavaScript.

        Example:
        --------
        >>> script = "var callback = arguments[arguments.length - 1]; "
        ...     "window.setTimeout(function(){ callback('timeout') }, 3000);"
        >>> driver.execute_async_script(script)
        """
        converted_args = list(args)
        command = Command.W3C_EXECUTE_SCRIPT_ASYNC

        return self.execute(command, {"script": script, "args": converted_args})["value"]

    @property
    def current_url(self) -> str:
        """Gets the URL of the current page.

        Example:
        --------
        >>> print(driver.current_url)
        """
        return self.execute(Command.GET_CURRENT_URL)["value"]

    @property
    def page_source(self) -> str:
        """Gets the source of the current page.

        Example:
        --------
        >>> print(driver.page_source)
        """
        return self.execute(Command.GET_PAGE_SOURCE)["value"]

    def close(self) -> None:
        """Closes the current window.

        Example:
        --------
        >>> driver.close()
        """
        self.execute(Command.CLOSE)

    def quit(self) -> None:
        """Quits the driver and closes every associated window.

        Example:
        --------
        >>> driver.quit()
        """
        try:
            self.execute(Command.QUIT)
        finally:
            self.stop_client()
            self.command_executor.close()

    @property
    def current_window_handle(self) -> str:
        """Returns the handle of the current window.

        Example:
        --------
        >>> print(driver.current_window_handle)
        """
        return self.execute(Command.W3C_GET_CURRENT_WINDOW_HANDLE)["value"]

    @property
    def window_handles(self) -> List[str]:
        """Returns the handles of all windows within the current session.

        Example:
        --------
        >>> print(driver.window_handles)
        """
        return self.execute(Command.W3C_GET_WINDOW_HANDLES)["value"]

    def maximize_window(self) -> None:
        """Maximizes the current window that webdriver is using.

        Example:
        --------
        >>> driver.maximize_window()
        """
        command = Command.W3C_MAXIMIZE_WINDOW
        self.execute(command, None)

    def fullscreen_window(self) -> None:
        """Invokes the window manager-specific 'full screen' operation.

        Example:
        --------
        >>> driver.fullscreen_window()
        """
        self.execute(Command.FULLSCREEN_WINDOW)

    def minimize_window(self) -> None:
        """Invokes the window manager-specific 'minimize' operation."""
        self.execute(Command.MINIMIZE_WINDOW)

    def print_page(self, print_options: Optional[PrintOptions] = None) -> str:
        """Takes PDF of the current page.

        The driver makes a best effort to return a PDF based on the
        provided Parameters.

        Example:
        --------
        >>> driver.print_page()
        """
        options = {}
        if print_options:
            options = print_options.to_dict()

        return self.execute(Command.PRINT_PAGE, options)["value"]

    @property
    def switch_to(self) -> SwitchTo:
        """Return an object containing all options to switch focus into.

        Returns:
        --------
        SwitchTo: an object containing all options to switch focus into.

        Examples:
        --------
        >>> element = driver.switch_to.active_element
        >>> alert = driver.switch_to.alert
        >>> driver.switch_to.default_content()
        >>> driver.switch_to.frame("frame_name")
        >>> driver.switch_to.frame(1)
        >>> driver.switch_to.frame(driver.find_elements(By.TAG_NAME, "iframe")[0])
        >>> driver.switch_to.parent_frame()
        >>> driver.switch_to.window("main")
        """
        return self._switch_to

    # Navigation
    def back(self) -> None:
        """Goes one step backward in the browser history.

        Example:
        --------
        >>> driver.back()
        """
        self.execute(Command.GO_BACK)

    def forward(self) -> None:
        """Goes one step forward in the browser history.

        Example:
        --------
        >>> driver.forward()
        """
        self.execute(Command.GO_FORWARD)

    def refresh(self) -> None:
        """Refreshes the current page.

        Example:
        --------
        >>> driver.refresh()
        """
        self.execute(Command.REFRESH)

    # Options
    def get_cookies(self) -> List[dict]:
        """Returns a set of dictionaries, corresponding to cookies visible in
        the current session.

        Returns:
        --------
        cookies:List[dict] : A list of dictionaries, corresponding to cookies visible in the current

        Example:
        --------
        >>> cookies = driver.get_cookies()
        """
        return self.execute(Command.GET_ALL_COOKIES)["value"]

    def get_cookie(self, name) -> Optional[Dict]:
        """Get a single cookie by name. Raises ValueError if the name is empty
        or whitespace. Returns the cookie if found, None if not.

        Example:
        --------
        >>> cookie = driver.get_cookie("my_cookie")
        """
        if not name or name.isspace():
            raise ValueError("Cookie name cannot be empty")

        with contextlib.suppress(NoSuchCookieException):
            return self.execute(Command.GET_COOKIE, {"name": name})["value"]

        return None

    def delete_cookie(self, name) -> None:
        """Deletes a single cookie with the given name. Raises ValueError if
        the name is empty or whitespace.

        Example:
        --------
        >>> driver.delete_cookie("my_cookie")
        """

        # firefox deletes all cookies when "" is passed as name
        if not name or name.isspace():
            raise ValueError("Cookie name cannot be empty")

        self.execute(Command.DELETE_COOKIE, {"name": name})

    def delete_all_cookies(self) -> None:
        """Delete all cookies in the scope of the session.

        Example:
        --------
        >>> driver.delete_all_cookies()
        """
        self.execute(Command.DELETE_ALL_COOKIES)

    def add_cookie(self, cookie_dict) -> None:
        """Adds a cookie to your current session.

        Parameters:
        -----------
        cookie_dict : dict
            - A dictionary object, with required keys - "name" and "value";
            - Optional keys - "path", "domain", "secure", "httpOnly", "expiry", "sameSite"

        Examples:
        --------
        >>> driver.add_cookie({"name": "foo", "value": "bar"})
        >>> driver.add_cookie({"name": "foo", "value": "bar", "path": "/"})
        >>> driver.add_cookie({"name": "foo", "value": "bar", "path": "/", "secure": True})
        >>> driver.add_cookie({"name": "foo", "value": "bar", "sameSite": "Strict"})
        """
        if "sameSite" in cookie_dict:
            assert cookie_dict["sameSite"] in ["Strict", "Lax", "None"]
            self.execute(Command.ADD_COOKIE, {"cookie": cookie_dict})
        else:
            self.execute(Command.ADD_COOKIE, {"cookie": cookie_dict})

    # Timeouts
    def implicitly_wait(self, time_to_wait: float) -> None:
        """Sets a sticky timeout to implicitly wait for an element to be found,
        or a command to complete. This method only needs to be called one time
        per session. To set the timeout for calls to execute_async_script, see
        set_script_timeout.

        Parameters:
        -----------
        time_to_wait : float
            - Amount of time to wait (in seconds)

        Example:
        --------
        >>> driver.implicitly_wait(30)
        """
        self.execute(Command.SET_TIMEOUTS, {"implicit": int(float(time_to_wait) * 1000)})

    def set_script_timeout(self, time_to_wait: float) -> None:
        """Set the amount of time that the script should wait during an
        execute_async_script call before throwing an error.

        Parameters:
        -----------
        time_to_wait : float
            - The amount of time to wait (in seconds)

        Example:
        --------
        >>> driver.set_script_timeout(30)
        """
        self.execute(Command.SET_TIMEOUTS, {"script": int(float(time_to_wait) * 1000)})

    def set_page_load_timeout(self, time_to_wait: float) -> None:
        """Set the amount of time to wait for a page load to complete before
        throwing an error.

        Parameters:
        -----------
        time_to_wait : float
             - The amount of time to wait (in seconds)

        Example:
        --------
        >>> driver.set_page_load_timeout(30)
        """
        try:
            self.execute(Command.SET_TIMEOUTS, {"pageLoad": int(float(time_to_wait) * 1000)})
        except WebDriverException:
            self.execute(Command.SET_TIMEOUTS, {"ms": float(time_to_wait) * 1000, "type": "page load"})

    @property
    def timeouts(self) -> Timeouts:
        """Get all the timeouts that have been set on the current session.

        Returns:
        --------
        Timeouts: A named tuple with the following fields:
            - implicit_wait: The time to wait for elements to be found.
            - page_load: The time to wait for a page to load.
            - script: The time to wait for scripts to execute.

        Example:
        --------
        >>> driver.timeouts
        """
        timeouts = self.execute(Command.GET_TIMEOUTS)["value"]
        timeouts["implicit_wait"] = timeouts.pop("implicit") / 1000
        timeouts["page_load"] = timeouts.pop("pageLoad") / 1000
        timeouts["script"] = timeouts.pop("script") / 1000
        return Timeouts(**timeouts)

    @timeouts.setter
    def timeouts(self, timeouts) -> None:
        """Set all timeouts for the session. This will override any previously
        set timeouts.

        Example:
        --------
        >>> my_timeouts = Timeouts()
        >>> my_timeouts.implicit_wait = 10
        >>> driver.timeouts = my_timeouts
        """
        _ = self.execute(Command.SET_TIMEOUTS, timeouts._to_json())["value"]

    def find_element(self, by=By.ID, value: Optional[str] = None) -> WebElement:
        """Find an element given a By strategy and locator.

        Parameters:
        -----------
        by : selenium.webdriver.common.by.By
            The locating strategy to use. Default is `By.ID`. Supported values include:
            - By.ID: Locate by element ID.
            - By.NAME: Locate by the `name` attribute.
            - By.XPATH: Locate by an XPath expression.
            - By.CSS_SELECTOR: Locate by a CSS selector.
            - By.CLASS_NAME: Locate by the `class` attribute.
            - By.TAG_NAME: Locate by the tag name (e.g., "input", "button").
            - By.LINK_TEXT: Locate a link element by its exact text.
            - By.PARTIAL_LINK_TEXT: Locate a link element by partial text match.
            - RelativeBy: Locate elements relative to a specified root element.

        Example:
        --------
        element = driver.find_element(By.ID, 'foo')

        Returns:
        -------
        WebElement
            The first matching `WebElement` found on the page.
        """
        by, value = self.locator_converter.convert(by, value)

        if isinstance(by, RelativeBy):
            elements = self.find_elements(by=by, value=value)
            if not elements:
                raise NoSuchElementException(f"Cannot locate relative element with: {by.root}")
            return elements[0]

        return self.execute(Command.FIND_ELEMENT, {"using": by, "value": value})["value"]

    def find_elements(self, by=By.ID, value: Optional[str] = None) -> List[WebElement]:
        """Find elements given a By strategy and locator.

        Parameters:
        -----------
        by : selenium.webdriver.common.by.By
            The locating strategy to use. Default is `By.ID`. Supported values include:
            - By.ID: Locate by element ID.
            - By.NAME: Locate by the `name` attribute.
            - By.XPATH: Locate by an XPath expression.
            - By.CSS_SELECTOR: Locate by a CSS selector.
            - By.CLASS_NAME: Locate by the `class` attribute.
            - By.TAG_NAME: Locate by the tag name (e.g., "input", "button").
            - By.LINK_TEXT: Locate a link element by its exact text.
            - By.PARTIAL_LINK_TEXT: Locate a link element by partial text match.
            - RelativeBy: Locate elements relative to a specified root element.

        Example:
        --------
        element = driver.find_elements(By.ID, 'foo')

        Returns:
        -------
        List[WebElement]
            list of `WebElements` matching locator strategy found on the page.
        """
        by, value = self.locator_converter.convert(by, value)

        if isinstance(by, RelativeBy):
            _pkg = ".".join(__name__.split(".")[:-1])
            raw_function = pkgutil.get_data(_pkg, "findElements.js").decode("utf8")
            find_element_js = f"/* findElements */return ({raw_function}).apply(null, arguments);"
            return self.execute_script(find_element_js, by.to_dict())

        # Return empty list if driver returns null
        # See https://github.com/SeleniumHQ/selenium/issues/4555
        return self.execute(Command.FIND_ELEMENTS, {"using": by, "value": value})["value"] or []

    @property
    def capabilities(self) -> dict:
        """Returns the drivers current capabilities being used.

        Example:
        --------
        >>> print(driver.capabilities)
        """
        return self.caps

    def get_screenshot_as_file(self, filename) -> bool:
        """Saves a screenshot of the current window to a PNG image file.
        Returns False if there is any IOError, else returns True. Use full
        paths in your filename.

        Parameters:
        -----------
        filename : str
            - The full path you wish to save your screenshot to. This
            - should end with a `.png` extension.

        Example:
        --------
        >>> driver.get_screenshot_as_file("/Screenshots/foo.png")
        """
        if not str(filename).lower().endswith(".png"):
            warnings.warn(
                "name used for saved screenshot does not match file type. It should end with a `.png` extension",
                UserWarning,
                stacklevel=2,
            )
        png = self.get_screenshot_as_png()
        try:
            with open(filename, "wb") as f:
                f.write(png)
        except OSError:
            return False
        finally:
            del png
        return True

    def save_screenshot(self, filename) -> bool:
        """Saves a screenshot of the current window to a PNG image file.
        Returns False if there is any IOError, else returns True. Use full
        paths in your filename.

        Parameters:
        -----------
        filename : str
            - The full path you wish to save your screenshot to. This
            - should end with a `.png` extension.

        Example:
        --------
        >>> driver.save_screenshot("/Screenshots/foo.png")
        """
        return self.get_screenshot_as_file(filename)

    def get_screenshot_as_png(self) -> bytes:
        """Gets the screenshot of the current window as a binary data.

        Example:
        --------
        >>> driver.get_screenshot_as_png()
        """
        return b64decode(self.get_screenshot_as_base64().encode("ascii"))

    def get_screenshot_as_base64(self) -> str:
        """Gets the screenshot of the current window as a base64 encoded string
        which is useful in embedded images in HTML.

        Example:
        --------
        >>> driver.get_screenshot_as_base64()
        """
        return self.execute(Command.SCREENSHOT)["value"]

    def set_window_size(self, width, height, windowHandle: str = "current") -> None:
        """Sets the width and height of the current window. (window.resizeTo)

        Parameters:
        -----------
        width : int
            - the width in pixels to set the window to

        height : int
            - the height in pixels to set the window to

        Example:
        --------
        >>> driver.set_window_size(800, 600)
        """
        self._check_if_window_handle_is_current(windowHandle)
        self.set_window_rect(width=int(width), height=int(height))

    def get_window_size(self, windowHandle: str = "current") -> dict:
        """Gets the width and height of the current window.

        Example:
        --------
        >>> driver.get_window_size()
        """

        self._check_if_window_handle_is_current(windowHandle)
        size = self.get_window_rect()

        if size.get("value", None):
            size = size["value"]

        return {k: size[k] for k in ("width", "height")}

    def set_window_position(self, x: float, y: float, windowHandle: str = "current") -> dict:
        """Sets the x,y position of the current window. (window.moveTo)

        Parameters:
        ---------
        x : float
            - The x-coordinate in pixels to set the window position

        y : float
            - The y-coordinate in pixels to set the window position

        Example:
        --------
        >>> driver.set_window_position(0, 0)
        """
        self._check_if_window_handle_is_current(windowHandle)
        return self.set_window_rect(x=int(x), y=int(y))

    def get_window_position(self, windowHandle="current") -> dict:
        """Gets the x,y position of the current window.

        Example:
        --------
        >>> driver.get_window_position()
        """

        self._check_if_window_handle_is_current(windowHandle)
        position = self.get_window_rect()

        return {k: position[k] for k in ("x", "y")}

    def _check_if_window_handle_is_current(self, windowHandle: str) -> None:
        """Warns if the window handle is not equal to `current`."""
        if windowHandle != "current":
            warnings.warn("Only 'current' window is supported for W3C compatible browsers.", stacklevel=2)

    def get_window_rect(self) -> dict:
        """Gets the x, y coordinates of the window as well as height and width
        of the current window.

        Example:
        --------
        >>> driver.get_window_rect()
        """
        return self.execute(Command.GET_WINDOW_RECT)["value"]

    def set_window_rect(self, x=None, y=None, width=None, height=None) -> dict:
        """Sets the x, y coordinates of the window as well as height and width
        of the current window. This method is only supported for W3C compatible
        browsers; other browsers should use `set_window_position` and
        `set_window_size`.

        Example:
        --------
        >>> driver.set_window_rect(x=10, y=10)
        >>> driver.set_window_rect(width=100, height=200)
        >>> driver.set_window_rect(x=10, y=10, width=100, height=200)
        """

        if (x is None and y is None) and (not height and not width):
            raise InvalidArgumentException("x and y or height and width need values")

        return self.execute(Command.SET_WINDOW_RECT, {"x": x, "y": y, "width": width, "height": height})["value"]

    @property
    def file_detector(self) -> FileDetector:
        return self._file_detector

    @file_detector.setter
    def file_detector(self, detector) -> None:
        """Set the file detector to be used when sending keyboard input. By
        default, this is set to a file detector that does nothing.

        - see FileDetector
        - see LocalFileDetector
        - see UselessFileDetector

        Parameters:
        -----------
        detector : Any
            - The detector to use. Must not be None.
        """
        if not detector:
            raise WebDriverException("You may not set a file detector that is null")
        if not isinstance(detector, FileDetector):
            raise WebDriverException("Detector has to be instance of FileDetector")
        self._file_detector = detector

    @property
    def orientation(self):
        """Gets the current orientation of the device.

        Example:
        --------
        >>> orientation = driver.orientation
        """
        return self.execute(Command.GET_SCREEN_ORIENTATION)["value"]

    @orientation.setter
    def orientation(self, value) -> None:
        """Sets the current orientation of the device.

        Parameters:
        -----------
        value : str
            - orientation to set it to.

        Example:
        --------
        >>> driver.orientation = "landscape"
        """
        allowed_values = ["LANDSCAPE", "PORTRAIT"]
        if value.upper() in allowed_values:
            self.execute(Command.SET_SCREEN_ORIENTATION, {"orientation": value})
        else:
            raise WebDriverException("You can only set the orientation to 'LANDSCAPE' and 'PORTRAIT'")

    def start_devtools(self):
        global devtools
        if self._websocket_connection:
            return devtools, self._websocket_connection
        else:
            global cdp
            import_cdp()

            if not devtools:
                if self.caps.get("se:cdp"):
                    ws_url = self.caps.get("se:cdp")
                    version = self.caps.get("se:cdpVersion").split(".")[0]
                else:
                    version, ws_url = self._get_cdp_details()

                if not ws_url:
                    raise WebDriverException("Unable to find url to connect to from capabilities")

                devtools = cdp.import_devtools(version)
                if self.caps["browserName"].lower() == "firefox":
                    raise RuntimeError("CDP support for Firefox has been removed. Please switch to WebDriver BiDi.")
            self._websocket_connection = WebSocketConnection(ws_url)
            targets = self._websocket_connection.execute(devtools.target.get_targets())
            target_id = targets[0].target_id
            session = self._websocket_connection.execute(devtools.target.attach_to_target(target_id, True))
            self._websocket_connection.session_id = session
            return devtools, self._websocket_connection

    @asynccontextmanager
    async def bidi_connection(self):
        global cdp
        import_cdp()
        if self.caps.get("se:cdp"):
            ws_url = self.caps.get("se:cdp")
            version = self.caps.get("se:cdpVersion").split(".")[0]
        else:
            version, ws_url = self._get_cdp_details()

        if not ws_url:
            raise WebDriverException("Unable to find url to connect to from capabilities")

        devtools = cdp.import_devtools(version)
        async with cdp.open_cdp(ws_url) as conn:
            targets = await conn.execute(devtools.target.get_targets())
            target_id = targets[0].target_id
            async with conn.open_session(target_id) as session:
                yield BidiConnection(session, cdp, devtools)

    @property
    def script(self):
        if not self._websocket_connection:
            self._start_bidi()

        if not self._script:
            self._script = Script(self._websocket_connection)

        return self._script

    def _start_bidi(self):
        if self.caps.get("webSocketUrl"):
            ws_url = self.caps.get("webSocketUrl")
        else:
            raise WebDriverException("Unable to find url to connect to from capabilities")

        self._websocket_connection = WebSocketConnection(ws_url)

    @property
    def network(self):
        if not self._websocket_connection:
            self._start_bidi()

        if not hasattr(self, "_network") or self._network is None:
            self._network = Network(self._websocket_connection)

        return self._network

    @property
    def browser(self):
        """Returns a browser module object for BiDi browser commands.

        Returns:
        --------
        Browser: an object containing access to BiDi browser commands.

        Examples:
        ---------
        >>> user_context = driver.browser.create_user_context()
        >>> user_contexts = driver.browser.get_user_contexts()
        >>> client_windows = driver.browser.get_client_windows()
        >>> driver.browser.remove_user_context(user_context)
        """
        if not self._websocket_connection:
            self._start_bidi()

        if self._browser is None:
            self._browser = Browser(self._websocket_connection)

        return self._browser

    @property
    def _session(self):
        """
        Returns the BiDi session object for the current WebDriver session.
        """
        if not self._websocket_connection:
            self._start_bidi()

        if self._bidi_session is None:
            self._bidi_session = Session(self._websocket_connection)

        return self._bidi_session

    @property
    def browsing_context(self):
        """Returns a browsing context module object for BiDi browsing context commands.

        Returns:
        --------
        BrowsingContext: an object containing access to BiDi browsing context commands.

        Examples:
        ---------
        >>> context_id = driver.browsing_context.create(type="tab")
        >>> driver.browsing_context.navigate(context=context_id, url="https://www.selenium.dev")
        >>> driver.browsing_context.capture_screenshot(context=context_id)
        >>> driver.browsing_context.close(context_id)
        """
        if not self._websocket_connection:
            self._start_bidi()

        if self._browsing_context is None:
            self._browsing_context = BrowsingContext(self._websocket_connection)

        return self._browsing_context

    @property
    def storage(self):
        """Returns a storage module object for BiDi storage commands.

        Returns:
        --------
        Storage: an object containing access to BiDi storage commands.

        Examples:
        ---------
        >>> cookie_filter = CookieFilter(name="example")
        >>> result = driver.storage.get_cookies(filter=cookie_filter)
        >>> driver.storage.set_cookie(cookie=PartialCookie(
                "name", BytesValue(BytesValue.TYPE_STRING, "value"), "domain")
            )
        >>> driver.storage.delete_cookies(filter=CookieFilter(name="example"))
        """
        if not self._websocket_connection:
            self._start_bidi()

        if self._storage is None:
            self._storage = Storage(self._websocket_connection)

        return self._storage

    @property
    def webextension(self):
        """Returns a webextension module object for BiDi webextension commands.

        Returns:
        --------
        WebExtension: an object containing access to BiDi webextension commands.

        Examples:
        ---------
        >>> extension_path = "/path/to/extension"
        >>> extension_result = driver.webextension.install(path=extension_path)
        >>> driver.webextension.uninstall(extension_result)
        """
        if not self._websocket_connection:
            self._start_bidi()

        if self._webextension is None:
            self._webextension = WebExtension(self._websocket_connection)

        return self._webextension

    def _get_cdp_details(self):
        import json

        import urllib3

        http = urllib3.PoolManager()
        if self.caps.get("browserName") == "chrome":
            debugger_address = self.caps.get("goog:chromeOptions").get("debuggerAddress")
        elif self.caps.get("browserName") == "MicrosoftEdge":
            debugger_address = self.caps.get("ms:edgeOptions").get("debuggerAddress")

        res = http.request("GET", f"http://{debugger_address}/json/version")
        data = json.loads(res.data)

        browser_version = data.get("Browser")
        websocket_url = data.get("webSocketDebuggerUrl")

        import re

        version = re.search(r".*/(\d+)\.", browser_version).group(1)

        return version, websocket_url

    # Virtual Authenticator Methods
    def add_virtual_authenticator(self, options: VirtualAuthenticatorOptions) -> None:
        """Adds a virtual authenticator with the given options.

        Example:
        --------
        >>> from selenium.webdriver.common.virtual_authenticator import VirtualAuthenticatorOptions
        >>> options = VirtualAuthenticatorOptions(protocol="u2f", transport="usb", device_id="myDevice123")
        >>> driver.add_virtual_authenticator(options)
        """
        self._authenticator_id = self.execute(Command.ADD_VIRTUAL_AUTHENTICATOR, options.to_dict())["value"]

    @property
    def virtual_authenticator_id(self) -> str:
        """Returns the id of the virtual authenticator.

        Example:
        --------
        >>> print(driver.virtual_authenticator_id)
        """
        return self._authenticator_id

    @required_virtual_authenticator
    def remove_virtual_authenticator(self) -> None:
        """Removes a previously added virtual authenticator.

        The authenticator is no longer valid after removal, so no
        methods may be called.

        Example:
        --------
        >>> driver.remove_virtual_authenticator()
        """
        self.execute(Command.REMOVE_VIRTUAL_AUTHENTICATOR, {"authenticatorId": self._authenticator_id})
        self._authenticator_id = None

    @required_virtual_authenticator
    def add_credential(self, credential: Credential) -> None:
        """Injects a credential into the authenticator.

        Example:
        --------
        >>> from selenium.webdriver.common.credential import Credential
        >>> credential = Credential(id="user@example.com", password="aPassword")
        >>> driver.add_credential(credential)
        """
        self.execute(Command.ADD_CREDENTIAL, {**credential.to_dict(), "authenticatorId": self._authenticator_id})

    @required_virtual_authenticator
    def get_credentials(self) -> List[Credential]:
        """Returns the list of credentials owned by the authenticator.

        Example:
        --------
        >>> credentials = driver.get_credentials()
        """
        credential_data = self.execute(Command.GET_CREDENTIALS, {"authenticatorId": self._authenticator_id})
        return [Credential.from_dict(credential) for credential in credential_data["value"]]

    @required_virtual_authenticator
    def remove_credential(self, credential_id: Union[str, bytearray]) -> None:
        """Removes a credential from the authenticator.

        Example:
        --------
        >>> credential_id = "user@example.com"
        >>> driver.remove_credential(credential_id)
        """
        # Check if the credential is bytearray converted to b64 string
        if isinstance(credential_id, bytearray):
            credential_id = urlsafe_b64encode(credential_id).decode()

        self.execute(
            Command.REMOVE_CREDENTIAL, {"credentialId": credential_id, "authenticatorId": self._authenticator_id}
        )

    @required_virtual_authenticator
    def remove_all_credentials(self) -> None:
        """Removes all credentials from the authenticator.

        Example:
        --------
        >>> driver.remove_all_credentials()
        """
        self.execute(Command.REMOVE_ALL_CREDENTIALS, {"authenticatorId": self._authenticator_id})

    @required_virtual_authenticator
    def set_user_verified(self, verified: bool) -> None:
        """Sets whether the authenticator will simulate success or fail on user
        verification.

        Parameters:
        -----------
        verified: True if the authenticator will pass user verification, False otherwise.

        Example:
        --------
        >>> driver.set_user_verified(True)
        """
        self.execute(Command.SET_USER_VERIFIED, {"authenticatorId": self._authenticator_id, "isUserVerified": verified})

    def get_downloadable_files(self) -> list:
        """Retrieves the downloadable files as a list of file names.

        Example:
        --------
        >>> files = driver.get_downloadable_files()
        """
        if "se:downloadsEnabled" not in self.capabilities:
            raise WebDriverException("You must enable downloads in order to work with downloadable files.")

        return self.execute(Command.GET_DOWNLOADABLE_FILES)["value"]["names"]

    def download_file(self, file_name: str, target_directory: str) -> None:
        """Downloads a file with the specified file name to the target
        directory.

        Parameters:
        -----------
        file_name : str
            - The name of the file to download.

        target_directory : str
            - The path to the directory to save the downloaded file.

        Example:
        --------
        >>> driver.download_file("example.zip", "/path/to/directory")
        """
        if "se:downloadsEnabled" not in self.capabilities:
            raise WebDriverException("You must enable downloads in order to work with downloadable files.")

        if not os.path.exists(target_directory):
            os.makedirs(target_directory)

        contents = self.execute(Command.DOWNLOAD_FILE, {"name": file_name})["value"]["contents"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_file = os.path.join(tmp_dir, file_name + ".zip")
            with open(zip_file, "wb") as file:
                file.write(base64.b64decode(contents))

            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(target_directory)

    def delete_downloadable_files(self) -> None:
        """Deletes all downloadable files.

        Example:
        --------
        >>> driver.delete_downloadable_files()
        """
        if "se:downloadsEnabled" not in self.capabilities:
            raise WebDriverException("You must enable downloads in order to work with downloadable files.")

        self.execute(Command.DELETE_DOWNLOADABLE_FILES)

    @property
    def fedcm(self) -> FedCM:
        """Returns the Federated Credential Management (FedCM) dialog object
        for interaction.

        Returns:
        -------
        FedCM: an object providing access to all Federated Credential Management (FedCM) dialog commands.

        Examples:
        --------
        >>> title = driver.fedcm.title
        >>> subtitle = driver.fedcm.subtitle
        >>> dialog_type = driver.fedcm.dialog_type
        >>> accounts = driver.fedcm.account_list
        >>> driver.fedcm.select_account(0)
        >>> driver.fedcm.accept()
        >>> driver.fedcm.dismiss()
        >>> driver.fedcm.enable_delay()
        >>> driver.fedcm.disable_delay()
        >>> driver.fedcm.reset_cooldown()
        """
        return self._fedcm

    @property
    def supports_fedcm(self) -> bool:
        """Returns whether the browser supports FedCM capabilities.

        Example:
        --------
        >>> print(driver.supports_fedcm)
        """
        return self.capabilities.get(ArgOptions.FEDCM_CAPABILITY, False)

    def _require_fedcm_support(self):
        """Raises an exception if FedCM is not supported."""
        if not self.supports_fedcm:
            raise WebDriverException(
                "This browser does not support Federated Credential Management. "
                "Please ensure you're using a supported browser."
            )

    @property
    def dialog(self):
        """Returns the FedCM dialog object for interaction.

        Example:
        --------
        >>> dialog = driver.dialog
        """
        self._require_fedcm_support()
        return Dialog(self)

    def fedcm_dialog(self, timeout=5, poll_frequency=0.5, ignored_exceptions=None):
        """Waits for and returns the FedCM dialog.

        Parameters:
        -----------
        timeout : int
            - How long to wait for the dialog

        poll_frequency : floatHow
            - Frequently to poll

        ignored_exceptions : Any
            - Exceptions to ignore while waiting

        Returns:
        -------
            The FedCM dialog object if found

        Raises:
        -------
            TimeoutException if dialog doesn't appear
            WebDriverException if FedCM not supported
        """
        from selenium.common.exceptions import NoAlertPresentException
        from selenium.webdriver.support.wait import WebDriverWait

        self._require_fedcm_support()

        if ignored_exceptions is None:
            ignored_exceptions = (NoAlertPresentException,)

        def _check_fedcm():
            try:
                dialog = Dialog(self)
                return dialog if dialog.type else None
            except NoAlertPresentException:
                return None

        wait = WebDriverWait(self, timeout, poll_frequency=poll_frequency, ignored_exceptions=ignored_exceptions)
        return wait.until(lambda _: _check_fedcm())

# === NexusCore/openenv\Lib\site-packages\git\objects\submodule\base.py ===
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

__all__ = ["Submodule", "UpdateProgress"]

import gc
from io import BytesIO
import logging
import os
import os.path as osp
import stat
import sys
import uuid

import git
from git.cmd import Git
from git.compat import defenc
from git.config import GitConfigParser, SectionConstraint, cp
from git.exc import (
    BadName,
    InvalidGitRepositoryError,
    NoSuchPathError,
    RepositoryDirtyError,
)
from git.objects.base import IndexObject, Object
from git.objects.util import TraversableIterableObj
from git.util import (
    IterableList,
    RemoteProgress,
    join_path_native,
    rmtree,
    to_native_path_linux,
    unbare_repo,
)

from .util import (
    SubmoduleConfigParser,
    find_first_remote_branch,
    mkhead,
    sm_name,
    sm_section,
)

# typing ----------------------------------------------------------------------

from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    Mapping,
    Sequence,
    TYPE_CHECKING,
    Union,
    cast,
)

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

from git.types import Commit_ish, PathLike, TBD

if TYPE_CHECKING:
    from git.index import IndexFile
    from git.objects.commit import Commit
    from git.refs import Head
    from git.repo import Repo

# -----------------------------------------------------------------------------

_logger = logging.getLogger(__name__)


class UpdateProgress(RemoteProgress):
    """Class providing detailed progress information to the caller who should
    derive from it and implement the
    :meth:`update(...) <git.util.RemoteProgress.update>` message."""

    CLONE, FETCH, UPDWKTREE = [1 << x for x in range(RemoteProgress._num_op_codes, RemoteProgress._num_op_codes + 3)]
    _num_op_codes: int = RemoteProgress._num_op_codes + 3

    __slots__ = ()


BEGIN = UpdateProgress.BEGIN
END = UpdateProgress.END
CLONE = UpdateProgress.CLONE
FETCH = UpdateProgress.FETCH
UPDWKTREE = UpdateProgress.UPDWKTREE


# IndexObject comes via the util module. It's a 'hacky' fix thanks to Python's import
# mechanism, which causes plenty of trouble if the only reason for packages and modules
# is refactoring - subpackages shouldn't depend on parent packages.
class Submodule(IndexObject, TraversableIterableObj):
    """Implements access to a git submodule. They are special in that their sha
    represents a commit in the submodule's repository which is to be checked out
    at the path of this instance.

    The submodule type does not have a string type associated with it, as it exists
    solely as a marker in the tree and index.

    All methods work in bare and non-bare repositories.
    """

    _id_attribute_ = "name"
    k_modules_file = ".gitmodules"
    k_head_option = "branch"
    k_head_default = "master"
    k_default_mode = stat.S_IFDIR | stat.S_IFLNK
    """Submodule flags. Submodules are directories with link-status."""

    type: Literal["submodule"] = "submodule"  # type: ignore[assignment]
    """This is a bogus type string for base class compatibility."""

    __slots__ = ("_parent_commit", "_url", "_branch_path", "_name", "__weakref__")

    _cache_attrs = ("path", "_url", "_branch_path")

    def __init__(
        self,
        repo: "Repo",
        binsha: bytes,
        mode: Union[int, None] = None,
        path: Union[PathLike, None] = None,
        name: Union[str, None] = None,
        parent_commit: Union["Commit", None] = None,
        url: Union[str, None] = None,
        branch_path: Union[PathLike, None] = None,
    ) -> None:
        """Initialize this instance with its attributes.

        We only document the parameters that differ from
        :class:`~git.objects.base.IndexObject`.

        :param repo:
            Our parent repository.

        :param binsha:
            Binary sha referring to a commit in the remote repository.
            See the `url` parameter.

        :param parent_commit:
            The :class:`~git.objects.commit.Commit` whose tree is supposed to contain
            the ``.gitmodules`` blob, or ``None`` to always point to the most recent
            commit. See :meth:`set_parent_commit` for details.

        :param url:
            The URL to the remote repository which is the submodule.

        :param branch_path:
            Full repository-relative path to ref to checkout when cloning the remote
            repository.
        """
        super().__init__(repo, binsha, mode, path)
        self.size = 0
        self._parent_commit = parent_commit
        if url is not None:
            self._url = url
        if branch_path is not None:
            self._branch_path = branch_path
        if name is not None:
            self._name = name

    def _set_cache_(self, attr: str) -> None:
        if attr in ("path", "_url", "_branch_path"):
            reader: SectionConstraint = self.config_reader()
            # Default submodule values.
            try:
                self.path = reader.get("path")
            except cp.NoSectionError as e:
                if self.repo.working_tree_dir is not None:
                    raise ValueError(
                        "This submodule instance does not exist anymore in '%s' file"
                        % osp.join(self.repo.working_tree_dir, ".gitmodules")
                    ) from e

            self._url = reader.get("url")
            # GitPython extension values - optional.
            self._branch_path = reader.get_value(self.k_head_option, git.Head.to_full_path(self.k_head_default))
        elif attr == "_name":
            raise AttributeError("Cannot retrieve the name of a submodule if it was not set initially")
        else:
            super()._set_cache_(attr)
        # END handle attribute name

    @classmethod
    def _get_intermediate_items(cls, item: "Submodule") -> IterableList["Submodule"]:
        """:return: All the submodules of our module repository"""
        try:
            return cls.list_items(item.module())
        except InvalidGitRepositoryError:
            return IterableList("")
        # END handle intermediate items

    @classmethod
    def _need_gitfile_submodules(cls, git: Git) -> bool:
        return git.version_info[:3] >= (1, 7, 5)

    def __eq__(self, other: Any) -> bool:
        """Compare with another submodule."""
        # We may only compare by name as this should be the ID they are hashed with.
        # Otherwise this type wouldn't be hashable.
        # return self.path == other.path and self.url == other.url and super().__eq__(other)
        return self._name == other._name

    def __ne__(self, other: object) -> bool:
        """Compare with another submodule for inequality."""
        return not (self == other)

    def __hash__(self) -> int:
        """Hash this instance using its logical id, not the sha."""
        return hash(self._name)

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return "git.%s(name=%s, path=%s, url=%s, branch_path=%s)" % (
            type(self).__name__,
            self._name,
            self.path,
            self.url,
            self.branch_path,
        )

    @classmethod
    def _config_parser(
        cls, repo: "Repo", parent_commit: Union["Commit", None], read_only: bool
    ) -> SubmoduleConfigParser:
        """
        :return:
            Config parser constrained to our submodule in read or write mode

        :raise IOError:
            If the ``.gitmodules`` file cannot be found, either locally or in the
            repository at the given parent commit. Otherwise the exception would be
            delayed until the first access of the config parser.
        """
        parent_matches_head = True
        if parent_commit is not None:
            try:
                parent_matches_head = repo.head.commit == parent_commit
            except ValueError:
                # We are most likely in an empty repository, so the HEAD doesn't point
                # to a valid ref.
                pass
        # END handle parent_commit
        fp_module: Union[str, BytesIO]
        if not repo.bare and parent_matches_head and repo.working_tree_dir:
            fp_module = osp.join(repo.working_tree_dir, cls.k_modules_file)
        else:
            assert parent_commit is not None, "need valid parent_commit in bare repositories"
            try:
                fp_module = cls._sio_modules(parent_commit)
            except KeyError as e:
                raise IOError(
                    "Could not find %s file in the tree of parent commit %s" % (cls.k_modules_file, parent_commit)
                ) from e
            # END handle exceptions
        # END handle non-bare working tree

        if not read_only and (repo.bare or not parent_matches_head):
            raise ValueError("Cannot write blobs of 'historical' submodule configurations")
        # END handle writes of historical submodules

        return SubmoduleConfigParser(fp_module, read_only=read_only)

    def _clear_cache(self) -> None:
        """Clear the possibly changed values."""
        for name in self._cache_attrs:
            try:
                delattr(self, name)
            except AttributeError:
                pass
            # END try attr deletion
        # END for each name to delete

    @classmethod
    def _sio_modules(cls, parent_commit: "Commit") -> BytesIO:
        """
        :return:
            Configuration file as :class:`~io.BytesIO` - we only access it through the
            respective blob's data
        """
        sio = BytesIO(parent_commit.tree[cls.k_modules_file].data_stream.read())
        sio.name = cls.k_modules_file
        return sio

    def _config_parser_constrained(self, read_only: bool) -> SectionConstraint:
        """:return: Config parser constrained to our submodule in read or write mode"""
        try:
            pc = self.parent_commit
        except ValueError:
            pc = None
        # END handle empty parent repository
        parser = self._config_parser(self.repo, pc, read_only)
        parser.set_submodule(self)
        return SectionConstraint(parser, sm_section(self.name))

    @classmethod
    def _module_abspath(cls, parent_repo: "Repo", path: PathLike, name: str) -> PathLike:
        if cls._need_gitfile_submodules(parent_repo.git):
            return osp.join(parent_repo.git_dir, "modules", name)
        if parent_repo.working_tree_dir:
            return osp.join(parent_repo.working_tree_dir, path)
        raise NotADirectoryError()

    @classmethod
    def _clone_repo(
        cls,
        repo: "Repo",
        url: str,
        path: PathLike,
        name: str,
        allow_unsafe_options: bool = False,
        allow_unsafe_protocols: bool = False,
        **kwargs: Any,
    ) -> "Repo":
        """
        :return:
            :class:`~git.repo.base.Repo` instance of newly cloned repository.

        :param repo:
            Our parent repository.

        :param url:
            URL to clone from.

        :param path:
            Repository-relative path to the submodule checkout location.

        :param name:
            Canonical name of the submodule.

        :param allow_unsafe_protocols:
            Allow unsafe protocols to be used, like ``ext``.

        :param allow_unsafe_options:
            Allow unsafe options to be used, like ``--upload-pack``.

        :param kwargs:
            Additional arguments given to :manpage:`git-clone(1)`.
        """
        module_abspath = cls._module_abspath(repo, path, name)
        module_checkout_path = module_abspath
        if cls._need_gitfile_submodules(repo.git):
            kwargs["separate_git_dir"] = module_abspath
            module_abspath_dir = osp.dirname(module_abspath)
            if not osp.isdir(module_abspath_dir):
                os.makedirs(module_abspath_dir)
            module_checkout_path = osp.join(str(repo.working_tree_dir), path)

        clone = git.Repo.clone_from(
            url,
            module_checkout_path,
            allow_unsafe_options=allow_unsafe_options,
            allow_unsafe_protocols=allow_unsafe_protocols,
            **kwargs,
        )
        if cls._need_gitfile_submodules(repo.git):
            cls._write_git_file_and_module_config(module_checkout_path, module_abspath)

        return clone

    @classmethod
    def _to_relative_path(cls, parent_repo: "Repo", path: PathLike) -> PathLike:
        """:return: A path guaranteed to be relative to the given parent repository

        :raise ValueError:
            If path is not contained in the parent repository's working tree.
        """
        path = to_native_path_linux(path)
        if path.endswith("/"):
            path = path[:-1]
        # END handle trailing slash

        if osp.isabs(path) and parent_repo.working_tree_dir:
            working_tree_linux = to_native_path_linux(parent_repo.working_tree_dir)
            if not path.startswith(working_tree_linux):
                raise ValueError(
                    "Submodule checkout path '%s' needs to be within the parents repository at '%s'"
                    % (working_tree_linux, path)
                )
            path = path[len(working_tree_linux.rstrip("/")) + 1 :]
            if not path:
                raise ValueError("Absolute submodule path '%s' didn't yield a valid relative path" % path)
            # END verify converted relative path makes sense
        # END convert to a relative path

        return path

    @classmethod
    def _write_git_file_and_module_config(cls, working_tree_dir: PathLike, module_abspath: PathLike) -> None:
        """Write a ``.git`` file containing a (preferably) relative path to the actual
        git module repository.

        It is an error if the `module_abspath` cannot be made into a relative path,
        relative to the `working_tree_dir`.

        :note:
            This will overwrite existing files!

        :note:
            As we rewrite both the git file as well as the module configuration, we
            might fail on the configuration and will not roll back changes done to the
            git file. This should be a non-issue, but may easily be fixed if it becomes
            one.

        :param working_tree_dir:
            Directory to write the ``.git`` file into.

        :param module_abspath:
            Absolute path to the bare repository.
        """
        git_file = osp.join(working_tree_dir, ".git")
        rela_path = osp.relpath(module_abspath, start=working_tree_dir)
        if sys.platform == "win32" and osp.isfile(git_file):
            os.remove(git_file)
        with open(git_file, "wb") as fp:
            fp.write(("gitdir: %s" % rela_path).encode(defenc))

        with GitConfigParser(osp.join(module_abspath, "config"), read_only=False, merge_includes=False) as writer:
            writer.set_value(
                "core",
                "worktree",
                to_native_path_linux(osp.relpath(working_tree_dir, start=module_abspath)),
            )

    # { Edit Interface

    @classmethod
    def add(
        cls,
        repo: "Repo",
        name: str,
        path: PathLike,
        url: Union[str, None] = None,
        branch: Union[str, None] = None,
        no_checkout: bool = False,
        depth: Union[int, None] = None,
        env: Union[Mapping[str, str], None] = None,
        clone_multi_options: Union[Sequence[TBD], None] = None,
        allow_unsafe_options: bool = False,
        allow_unsafe_protocols: bool = False,
    ) -> "Submodule":
        """Add a new submodule to the given repository. This will alter the index as
        well as the ``.gitmodules`` file, but will not create a new commit. If the
        submodule already exists, no matter if the configuration differs from the one
        provided, the existing submodule will be returned.

        :param repo:
            Repository instance which should receive the submodule.

        :param name:
            The name/identifier for the submodule.

        :param path:
            Repository-relative or absolute path at which the submodule should be
            located.
            It will be created as required during the repository initialization.

        :param url:
            ``git clone ...``-compatible URL. See :manpage:`git-clone(1)` for more
            information. If ``None``, the repository is assumed to exist, and the URL of
            the first remote is taken instead. This is useful if you want to make an
            existing repository a submodule of another one.

        :param branch:
            Name of branch at which the submodule should (later) be checked out. The
            given branch must exist in the remote repository, and will be checked out
            locally as a tracking branch.
            It will only be written into the configuration if it not ``None``, which is
            when the checked out branch will be the one the remote HEAD pointed to.
            The result you get in these situation is somewhat fuzzy, and it is
            recommended to specify at least ``master`` here.
            Examples are ``master`` or ``feature/new``.

        :param no_checkout:
            If ``True``, and if the repository has to be cloned manually, no checkout
            will be performed.

        :param depth:
            Create a shallow clone with a history truncated to the specified number of
            commits.

        :param env:
            Optional dictionary containing the desired environment variables.

            Note: Provided variables will be used to update the execution environment
            for ``git``. If some variable is not specified in `env` and is defined in
            attr:`os.environ`, the value from attr:`os.environ` will be used. If you
            want to unset some variable, consider providing an empty string as its
            value.

        :param clone_multi_options:
            A list of clone options. Please see
            :meth:`Repo.clone <git.repo.base.Repo.clone>` for details.

        :param allow_unsafe_protocols:
            Allow unsafe protocols to be used, like ``ext``.

        :param allow_unsafe_options:
            Allow unsafe options to be used, like ``--upload-pack``.

        :return:
            The newly created :class:`Submodule` instance.

        :note:
            Works atomically, such that no change will be done if, for example, the
            repository update fails.
        """
        if repo.bare:
            raise InvalidGitRepositoryError("Cannot add submodules to bare repositories")
        # END handle bare repos

        path = cls._to_relative_path(repo, path)

        # Ensure we never put backslashes into the URL, as might happen on Windows.
        if url is not None:
            url = to_native_path_linux(url)
        # END ensure URL correctness

        # INSTANTIATE INTERMEDIATE SM
        sm = cls(
            repo,
            cls.NULL_BIN_SHA,
            cls.k_default_mode,
            path,
            name,
            url="invalid-temporary",
        )
        if sm.exists():
            # Reretrieve submodule from tree.
            try:
                sm = repo.head.commit.tree[str(path)]
                sm._name = name
                return sm
            except KeyError:
                # Could only be in index.
                index = repo.index
                entry = index.entries[index.entry_key(path, 0)]
                sm.binsha = entry.binsha
                return sm
            # END handle exceptions
        # END handle existing

        # fake-repo - we only need the functionality on the branch instance.
        br = git.Head(repo, git.Head.to_full_path(str(branch) or cls.k_head_default))
        has_module = sm.module_exists()
        branch_is_default = branch is None
        if has_module and url is not None:
            if url not in [r.url for r in sm.module().remotes]:
                raise ValueError(
                    "Specified URL '%s' does not match any remote url of the repository at '%s'" % (url, sm.abspath)
                )
            # END check url
        # END verify urls match

        mrepo: Union[Repo, None] = None

        if url is None:
            if not has_module:
                raise ValueError("A URL was not given and a repository did not exist at %s" % path)
            # END check url
            mrepo = sm.module()
            # assert isinstance(mrepo, git.Repo)
            urls = [r.url for r in mrepo.remotes]
            if not urls:
                raise ValueError("Didn't find any remote url in repository at %s" % sm.abspath)
            # END verify we have url
            url = urls[0]
        else:
            # Clone new repo.
            kwargs: Dict[str, Union[bool, int, str, Sequence[TBD]]] = {"n": no_checkout}
            if not branch_is_default:
                kwargs["b"] = br.name
            # END setup checkout-branch

            if depth:
                if isinstance(depth, int):
                    kwargs["depth"] = depth
                else:
                    raise ValueError("depth should be an integer")
            if clone_multi_options:
                kwargs["multi_options"] = clone_multi_options

            # _clone_repo(cls, repo, url, path, name, **kwargs):
            mrepo = cls._clone_repo(
                repo,
                url,
                path,
                name,
                env=env,
                allow_unsafe_options=allow_unsafe_options,
                allow_unsafe_protocols=allow_unsafe_protocols,
                **kwargs,
            )
        # END verify url

        ## See #525 for ensuring git URLs in config-files are valid under Windows.
        url = Git.polish_url(url)

        # It's important to add the URL to the parent config, to let `git submodule` know.
        # Otherwise there is a '-' character in front of the submodule listing:
        #  a38efa84daef914e4de58d1905a500d8d14aaf45 mymodule (v0.9.0-1-ga38efa8)
        # -a38efa84daef914e4de58d1905a500d8d14aaf45 submodules/intermediate/one
        writer: Union[GitConfigParser, SectionConstraint]

        with sm.repo.config_writer() as writer:
            writer.set_value(sm_section(name), "url", url)

        # Update configuration and index.
        index = sm.repo.index
        with sm.config_writer(index=index, write=False) as writer:
            writer.set_value("url", url)
            writer.set_value("path", path)

            sm._url = url
            if not branch_is_default:
                # Store full path.
                writer.set_value(cls.k_head_option, br.path)
                sm._branch_path = br.path

        # We deliberately assume that our head matches our index!
        if mrepo:
            sm.binsha = mrepo.head.commit.binsha
        index.add([sm], write=True)

        return sm

    def update(
        self,
        recursive: bool = False,
        init: bool = True,
        to_latest_revision: bool = False,
        progress: Union["UpdateProgress", None] = None,
        dry_run: bool = False,
        force: bool = False,
        keep_going: bool = False,
        env: Union[Mapping[str, str], None] = None,
        clone_multi_options: Union[Sequence[TBD], None] = None,
        allow_unsafe_options: bool = False,
        allow_unsafe_protocols: bool = False,
    ) -> "Submodule":
        """Update the repository of this submodule to point to the checkout we point at
        with the binsha of this instance.

        :param recursive:
            If ``True``, we will operate recursively and update child modules as well.

        :param init:
            If ``True``, the module repository will be cloned into place if necessary.

        :param to_latest_revision:
            If ``True``, the submodule's sha will be ignored during checkout. Instead,
            the remote will be fetched, and the local tracking branch updated. This only
            works if we have a local tracking branch, which is the case if the remote
            repository had a master branch, or if the ``branch`` option was specified
            for this submodule and the branch existed remotely.

        :param progress:
            :class:`UpdateProgress` instance, or ``None`` if no progress should be
            shown.

        :param dry_run:
            If ``True``, the operation will only be simulated, but not performed.
            All performed operations are read-only.

        :param force:
            If ``True``, we may reset heads even if the repository in question is dirty.
            Additionally we will be allowed to set a tracking branch which is ahead of
            its remote branch back into the past or the location of the remote branch.
            This will essentially 'forget' commits.

            If ``False``, local tracking branches that are in the future of their
            respective remote branches will simply not be moved.

        :param keep_going:
            If ``True``, we will ignore but log all errors, and keep going recursively.
            Unless `dry_run` is set as well, `keep_going` could cause
            subsequent/inherited errors you wouldn't see otherwise.
            In conjunction with `dry_run`, it can be useful to anticipate all errors
            when updating submodules.

        :param env:
            Optional dictionary containing the desired environment variables.

            Note: Provided variables will be used to update the execution environment
            for ``git``. If some variable is not specified in `env` and is defined in
            attr:`os.environ`, value from attr:`os.environ` will be used.

            If you want to unset some variable, consider providing the empty string as
            its value.

        :param clone_multi_options:
            List of :manpage:`git-clone(1)` options.
            Please see :meth:`Repo.clone <git.repo.base.Repo.clone>` for details.
            They only take effect with the `init` option.

        :param allow_unsafe_protocols:
            Allow unsafe protocols to be used, like ``ext``.

        :param allow_unsafe_options:
            Allow unsafe options to be used, like ``--upload-pack``.

        :note:
            Does nothing in bare repositories.

        :note:
            This method is definitely not atomic if `recursive` is ``True``.

        :return:
            self
        """
        if self.repo.bare:
            return self
        # END pass in bare mode

        if progress is None:
            progress = UpdateProgress()
        # END handle progress
        prefix = ""
        if dry_run:
            prefix = "DRY-RUN: "
        # END handle prefix

        # To keep things plausible in dry-run mode.
        if dry_run:
            mrepo = None
        # END init mrepo

        try:
            # ENSURE REPO IS PRESENT AND UP-TO-DATE
            #######################################
            try:
                mrepo = self.module()
                rmts = mrepo.remotes
                len_rmts = len(rmts)
                for i, remote in enumerate(rmts):
                    op = FETCH
                    if i == 0:
                        op |= BEGIN
                    # END handle start

                    progress.update(
                        op,
                        i,
                        len_rmts,
                        prefix + "Fetching remote %s of submodule %r" % (remote, self.name),
                    )
                    # ===============================
                    if not dry_run:
                        remote.fetch(progress=progress)
                    # END handle dry-run
                    # ===============================
                    if i == len_rmts - 1:
                        op |= END
                    # END handle end
                    progress.update(
                        op,
                        i,
                        len_rmts,
                        prefix + "Done fetching remote of submodule %r" % self.name,
                    )
                # END fetch new data
            except InvalidGitRepositoryError:
                mrepo = None
                if not init:
                    return self
                # END early abort if init is not allowed

                # There is no git-repository yet - but delete empty paths.
                checkout_module_abspath = self.abspath
                if not dry_run and osp.isdir(checkout_module_abspath):
                    try:
                        os.rmdir(checkout_module_abspath)
                    except OSError as e:
                        raise OSError(
                            "Module directory at %r does already exist and is non-empty" % checkout_module_abspath
                        ) from e
                    # END handle OSError
                # END handle directory removal

                # Don't check it out at first - nonetheless it will create a local
                # branch according to the remote-HEAD if possible.
                progress.update(
                    BEGIN | CLONE,
                    0,
                    1,
                    prefix
                    + "Cloning url '%s' to '%s' in submodule %r" % (self.url, checkout_module_abspath, self.name),
                )
                if not dry_run:
                    mrepo = self._clone_repo(
                        self.repo,
                        self.url,
                        self.path,
                        self.name,
                        n=True,
                        env=env,
                        multi_options=clone_multi_options,
                        allow_unsafe_options=allow_unsafe_options,
                        allow_unsafe_protocols=allow_unsafe_protocols,
                    )
                # END handle dry-run
                progress.update(
                    END | CLONE,
                    0,
                    1,
                    prefix + "Done cloning to %s" % checkout_module_abspath,
                )

                if not dry_run:
                    # See whether we have a valid branch to check out.
                    try:
                        mrepo = cast("Repo", mrepo)
                        # Find a remote which has our branch - we try to be flexible.
                        remote_branch = find_first_remote_branch(mrepo.remotes, self.branch_name)
                        local_branch = mkhead(mrepo, self.branch_path)

                        # Have a valid branch, but no checkout - make sure we can figure
                        # that out by marking the commit with a null_sha.
                        local_branch.set_object(Object(mrepo, self.NULL_BIN_SHA))
                        # END initial checkout + branch creation

                        # Make sure HEAD is not detached.
                        mrepo.head.set_reference(
                            local_branch,
                            logmsg="submodule: attaching head to %s" % local_branch,
                        )
                        mrepo.head.reference.set_tracking_branch(remote_branch)
                    except (IndexError, InvalidGitRepositoryError):
                        _logger.warning("Failed to checkout tracking branch %s", self.branch_path)
                    # END handle tracking branch

                    # NOTE: Have to write the repo config file as well, otherwise the
                    # default implementation will be offended and not update the
                    # repository. Maybe this is a good way to ensure it doesn't get into
                    # our way, but we want to stay backwards compatible too... It's so
                    # redundant!
                    with self.repo.config_writer() as writer:
                        writer.set_value(sm_section(self.name), "url", self.url)
                # END handle dry_run
            # END handle initialization

            # DETERMINE SHAS TO CHECK OUT
            #############################
            binsha = self.binsha
            hexsha = self.hexsha
            if mrepo is not None:
                # mrepo is only set if we are not in dry-run mode or if the module
                # existed.
                is_detached = mrepo.head.is_detached
            # END handle dry_run

            if mrepo is not None and to_latest_revision:
                msg_base = "Cannot update to latest revision in repository at %r as " % mrepo.working_dir
                if not is_detached:
                    rref = mrepo.head.reference.tracking_branch()
                    if rref is not None:
                        rcommit = rref.commit
                        binsha = rcommit.binsha
                        hexsha = rcommit.hexsha
                    else:
                        _logger.error(
                            "%s a tracking branch was not set for local branch '%s'",
                            msg_base,
                            mrepo.head.reference,
                        )
                    # END handle remote ref
                else:
                    _logger.error("%s there was no local tracking branch", msg_base)
                # END handle detached head
            # END handle to_latest_revision option

            # Update the working tree.
            # Handles dry_run.
            if mrepo is not None and mrepo.head.commit.binsha != binsha:
                # We must ensure that our destination sha (the one to point to) is in
                # the future of our current head. Otherwise, we will reset changes that
                # might have been done on the submodule, but were not yet pushed. We
                # also handle the case that history has been rewritten, leaving no
                # merge-base. In that case we behave conservatively, protecting possible
                # changes the user had done.
                may_reset = True
                if mrepo.head.commit.binsha != self.NULL_BIN_SHA:
                    base_commit = mrepo.merge_base(mrepo.head.commit, hexsha)
                    if len(base_commit) == 0 or (base_commit[0] is not None and base_commit[0].hexsha == hexsha):
                        if force:
                            msg = "Will force checkout or reset on local branch that is possibly in the future of"
                            msg += " the commit it will be checked out to, effectively 'forgetting' new commits"
                            _logger.debug(msg)
                        else:
                            msg = "Skipping %s on branch '%s' of submodule repo '%s' as it contains un-pushed commits"
                            msg %= (
                                is_detached and "checkout" or "reset",
                                mrepo.head,
                                mrepo,
                            )
                            _logger.info(msg)
                            may_reset = False
                        # END handle force
                    # END handle if we are in the future

                    if may_reset and not force and mrepo.is_dirty(index=True, working_tree=True, untracked_files=True):
                        raise RepositoryDirtyError(mrepo, "Cannot reset a dirty repository")
                    # END handle force and dirty state
                # END handle empty repo

                # END verify future/past
                progress.update(
                    BEGIN | UPDWKTREE,
                    0,
                    1,
                    prefix
                    + "Updating working tree at %s for submodule %r to revision %s" % (self.path, self.name, hexsha),
                )

                if not dry_run and may_reset:
                    if is_detached:
                        # NOTE: For now we force. The user is not supposed to change
                        # detached submodules anyway. Maybe at some point this becomes
                        # an option, to properly handle user modifications - see below
                        # for future options regarding rebase and merge.
                        mrepo.git.checkout(hexsha, force=force)
                    else:
                        mrepo.head.reset(hexsha, index=True, working_tree=True)
                    # END handle checkout
                # If we may reset/checkout.
                progress.update(
                    END | UPDWKTREE,
                    0,
                    1,
                    prefix + "Done updating working tree for submodule %r" % self.name,
                )
            # END update to new commit only if needed
        except Exception as err:
            if not keep_going:
                raise
            _logger.error(str(err))
        # END handle keep_going

        # HANDLE RECURSION
        ##################
        if recursive:
            # In dry_run mode, the module might not exist.
            if mrepo is not None:
                for submodule in self.iter_items(self.module()):
                    submodule.update(
                        recursive,
                        init,
                        to_latest_revision,
                        progress=progress,
                        dry_run=dry_run,
                        force=force,
                        keep_going=keep_going,
                    )
                # END handle recursive update
            # END handle dry run
        # END for each submodule

        return self

    @unbare_repo
    def move(self, module_path: PathLike, configuration: bool = True, module: bool = True) -> "Submodule":
        """Move the submodule to a another module path. This involves physically moving
        the repository at our current path, changing the configuration, as well as
        adjusting our index entry accordingly.

        :param module_path:
            The path to which to move our module in the parent repository's working
            tree, given as repository-relative or absolute path. Intermediate
            directories will be created accordingly. If the path already exists, it must
            be empty. Trailing (back)slashes are removed automatically.

        :param configuration:
            If ``True``, the configuration will be adjusted to let the submodule point
            to the given path.

        :param module:
            If ``True``, the repository managed by this submodule will be moved as well.
            If ``False``, we don't move the submodule's checkout, which may leave the
            parent repository in an inconsistent state.

        :return:
            self

        :raise ValueError:
            If the module path existed and was not empty, or was a file.

        :note:
            Currently the method is not atomic, and it could leave the repository in an
            inconsistent state if a sub-step fails for some reason.
        """
        if module + configuration < 1:
            raise ValueError("You must specify to move at least the module or the configuration of the submodule")
        # END handle input

        module_checkout_path = self._to_relative_path(self.repo, module_path)

        # VERIFY DESTINATION
        if module_checkout_path == self.path:
            return self
        # END handle no change

        module_checkout_abspath = join_path_native(str(self.repo.working_tree_dir), module_checkout_path)
        if osp.isfile(module_checkout_abspath):
            raise ValueError("Cannot move repository onto a file: %s" % module_checkout_abspath)
        # END handle target files

        index = self.repo.index
        tekey = index.entry_key(module_checkout_path, 0)
        # if the target item already exists, fail
        if configuration and tekey in index.entries:
            raise ValueError("Index entry for target path did already exist")
        # END handle index key already there

        # Remove existing destination.
        if module:
            if osp.exists(module_checkout_abspath):
                if len(os.listdir(module_checkout_abspath)):
                    raise ValueError("Destination module directory was not empty")
                # END handle non-emptiness

                if osp.islink(module_checkout_abspath):
                    os.remove(module_checkout_abspath)
                else:
                    os.rmdir(module_checkout_abspath)
                # END handle link
            else:
                # Recreate parent directories.
                # NOTE: renames() does that now.
                pass
            # END handle existence
        # END handle module

        # Move the module into place if possible.
        cur_path = self.abspath
        renamed_module = False
        if module and osp.exists(cur_path):
            os.renames(cur_path, module_checkout_abspath)
            renamed_module = True

            if osp.isfile(osp.join(module_checkout_abspath, ".git")):
                module_abspath = self._module_abspath(self.repo, self.path, self.name)
                self._write_git_file_and_module_config(module_checkout_abspath, module_abspath)
            # END handle git file rewrite
        # END move physical module

        # Rename the index entry - we have to manipulate the index directly as git-mv
        # cannot be used on submodules... yeah.
        previous_sm_path = self.path
        try:
            if configuration:
                try:
                    ekey = index.entry_key(self.path, 0)
                    entry = index.entries[ekey]
                    del index.entries[ekey]
                    nentry = git.IndexEntry(entry[:3] + (module_checkout_path,) + entry[4:])
                    index.entries[tekey] = nentry
                except KeyError as e:
                    raise InvalidGitRepositoryError("Submodule's entry at %r did not exist" % (self.path)) from e
                # END handle submodule doesn't exist

                # Update configuration.
                with self.config_writer(index=index) as writer:  # Auto-write.
                    writer.set_value("path", module_checkout_path)
                    self.path = module_checkout_path
            # END handle configuration flag
        except Exception:
            if renamed_module:
                os.renames(module_checkout_abspath, cur_path)
            # END undo module renaming
            raise
        # END handle undo rename

        # Auto-rename submodule if its name was 'default', that is, the checkout
        # directory.
        if previous_sm_path == self.name:
            self.rename(module_checkout_path)

        return self

    @unbare_repo
    def remove(
        self,
        module: bool = True,
        force: bool = False,
        configuration: bool = True,
        dry_run: bool = False,
    ) -> "Submodule":
        """Remove this submodule from the repository. This will remove our entry
        from the ``.gitmodules`` file and the entry in the ``.git/config`` file.

        :param module:
            If ``True``, the checked out module we point to will be deleted as well. If
            that module is currently on a commit outside any branch in the remote, or if
            it is ahead of its tracking branch, or if there are modified or untracked
            files in its working tree, then the removal will fail. In case the removal
            of the repository fails for these reasons, the submodule status will not
            have been altered.

            If this submodule has child modules of its own, these will be deleted prior
            to touching the direct submodule.

        :param force:
            Enforces the deletion of the module even though it contains modifications.
            This basically enforces a brute-force file system based deletion.

        :param configuration:
            If ``True``, the submodule is deleted from the configuration, otherwise it
            isn't. Although this should be enabled most of the time, this flag enables
            you to safely delete the repository of your submodule.

        :param dry_run:
            If ``True``, we will not actually do anything, but throw the errors we would
            usually throw.

        :return:
            self

        :note:
            Doesn't work in bare repositories.

        :note:
            Doesn't work atomically, as failure to remove any part of the submodule will
            leave an inconsistent state.

        :raise git.exc.InvalidGitRepositoryError:
            Thrown if the repository cannot be deleted.

        :raise OSError:
            If directories or files could not be removed.
        """
        if not (module or configuration):
            raise ValueError("Need to specify to delete at least the module, or the configuration")
        # END handle parameters

        # Recursively remove children of this submodule.
        nc = 0
        for csm in self.children():
            nc += 1
            csm.remove(module, force, configuration, dry_run)
            del csm

        if configuration and not dry_run and nc > 0:
            # Ensure we don't leave the parent repository in a dirty state, and commit
            # our changes. It's important for recursive, unforced, deletions to work as
            # expected.
            self.module().index.commit("Removed at least one of child-modules of '%s'" % self.name)
        # END handle recursion

        # DELETE REPOSITORY WORKING TREE
        ################################
        if module and self.module_exists():
            mod = self.module()
            git_dir = mod.git_dir
            if force:
                # Take the fast lane and just delete everything in our module path.
                # TODO: If we run into permission problems, we have a highly
                # inconsistent state. Delete the .git folders last, start with the
                # submodules first.
                mp = self.abspath
                method: Union[None, Callable[[PathLike], None]] = None
                if osp.islink(mp):
                    method = os.remove
                elif osp.isdir(mp):
                    method = rmtree
                elif osp.exists(mp):
                    raise AssertionError("Cannot forcibly delete repository as it was neither a link, nor a directory")
                # END handle brutal deletion
                if not dry_run:
                    assert method
                    method(mp)
                # END apply deletion method
            else:
                # Verify we may delete our module.
                if mod.is_dirty(index=True, working_tree=True, untracked_files=True):
                    raise InvalidGitRepositoryError(
                        "Cannot delete module at %s with any modifications, unless force is specified"
                        % mod.working_tree_dir
                    )
                # END check for dirt

                # Figure out whether we have new commits compared to the remotes.
                # NOTE: If the user pulled all the time, the remote heads might not have
                # been updated, so commits coming from the remote look as if they come
                # from us. But we stay strictly read-only and don't fetch beforehand.
                for remote in mod.remotes:
                    num_branches_with_new_commits = 0
                    rrefs = remote.refs
                    for rref in rrefs:
                        num_branches_with_new_commits += len(mod.git.cherry(rref)) != 0
                    # END for each remote ref
                    # Not a single remote branch contained all our commits.
                    if len(rrefs) and num_branches_with_new_commits == len(rrefs):
                        raise InvalidGitRepositoryError(
                            "Cannot delete module at %s as there are new commits" % mod.working_tree_dir
                        )
                    # END handle new commits
                    # We have to manually delete some references to allow resources to
                    # be cleaned up immediately when we are done with them, because
                    # Python's scoping is no more granular than the whole function (loop
                    # bodies are not scopes). When the objects stay alive longer, they
                    # can keep handles open. On Windows, this is a problem.
                    if len(rrefs):
                        del rref  # skipcq: PYL-W0631
                    # END handle remotes
                    del rrefs
                    del remote
                # END for each remote

                # Finally delete our own submodule.
                if not dry_run:
                    self._clear_cache()
                    wtd = mod.working_tree_dir
                    del mod  # Release file-handles (Windows).
                    gc.collect()
                    rmtree(str(wtd))
                # END delete tree if possible
            # END handle force

            if not dry_run and osp.isdir(git_dir):
                self._clear_cache()
                rmtree(git_dir)
            # END handle separate bare repository
        # END handle module deletion

        # Void our data so as not to delay invalid access.
        if not dry_run:
            self._clear_cache()

        # DELETE CONFIGURATION
        ######################
        if configuration and not dry_run:
            # First the index-entry.
            parent_index = self.repo.index
            try:
                del parent_index.entries[parent_index.entry_key(self.path, 0)]
            except KeyError:
                pass
            # END delete entry
            parent_index.write()

            # Now git config - we need the config intact, otherwise we can't query
            # information anymore.

            with self.repo.config_writer() as gcp_writer:
                gcp_writer.remove_section(sm_section(self.name))

            with self.config_writer() as sc_writer:
                sc_writer.remove_section()
        # END delete configuration

        return self

    def set_parent_commit(self, commit: Union[Commit_ish, str, None], check: bool = True) -> "Submodule":
        """Set this instance to use the given commit whose tree is supposed to
        contain the ``.gitmodules`` blob.

        :param commit:
            Commit-ish reference pointing at the root tree, or ``None`` to always point
            to the most recent commit.

        :param check:
            If ``True``, relatively expensive checks will be performed to verify
            validity of the submodule.

        :raise ValueError:
            If the commit's tree didn't contain the ``.gitmodules`` blob.

        :raise ValueError:
            If the parent commit didn't store this submodule under the current path.

        :return:
            self
        """
        if commit is None:
            self._parent_commit = None
            return self
        # END handle None
        pcommit = self.repo.commit(commit)
        pctree = pcommit.tree
        if self.k_modules_file not in pctree:
            raise ValueError("Tree of commit %s did not contain the %s file" % (commit, self.k_modules_file))
        # END handle exceptions

        prev_pc = self._parent_commit
        self._parent_commit = pcommit

        if check:
            parser = self._config_parser(self.repo, self._parent_commit, read_only=True)
            if not parser.has_section(sm_section(self.name)):
                self._parent_commit = prev_pc
                raise ValueError("Submodule at path %r did not exist in parent commit %s" % (self.path, commit))
            # END handle submodule did not exist
        # END handle checking mode

        # Update our sha, it could have changed.
        # If check is False, we might see a parent-commit that doesn't even contain the
        # submodule anymore. in that case, mark our sha as being NULL.
        try:
            self.binsha = pctree[str(self.path)].binsha
        except KeyError:
            self.binsha = self.NULL_BIN_SHA

        self._clear_cache()
        return self

    @unbare_repo
    def config_writer(
        self, index: Union["IndexFile", None] = None, write: bool = True
    ) -> SectionConstraint["SubmoduleConfigParser"]:
        """
        :return:
            A config writer instance allowing you to read and write the data belonging
            to this submodule into the ``.gitmodules`` file.

        :param index:
            If not ``None``, an :class:`~git.index.base.IndexFile` instance which should
            be written. Defaults to the index of the :class:`Submodule`'s parent
            repository.

        :param write:
            If ``True``, the index will be written each time a configuration value changes.

        :note:
            The parameters allow for a more efficient writing of the index, as you can
            pass in a modified index on your own, prevent automatic writing, and write
            yourself once the whole operation is complete.

        :raise ValueError:
            If trying to get a writer on a parent_commit which does not match the
            current head commit.

        :raise IOError:
            If the ``.gitmodules`` file/blob could not be read.
        """
        writer = self._config_parser_constrained(read_only=False)
        if index is not None:
            writer.config._index = index
        writer.config._auto_write = write
        return writer

    @unbare_repo
    def rename(self, new_name: str) -> "Submodule":
        """Rename this submodule.

        :note:
            This method takes care of renaming the submodule in various places, such as:

            * ``$parent_git_dir / config``
            * ``$working_tree_dir / .gitmodules``
            * (git >= v1.8.0: move submodule repository to new name)

        As ``.gitmodules`` will be changed, you would need to make a commit afterwards.
        The changed ``.gitmodules`` file will already be added to the index.

        :return:
            This :class:`Submodule` instance
        """
        if self.name == new_name:
            return self

        # .git/config
        with self.repo.config_writer() as pw:
            # As we ourselves didn't write anything about submodules into the parent
            # .git/config, we will not require it to exist, and just ignore missing
            # entries.
            if pw.has_section(sm_section(self.name)):
                pw.rename_section(sm_section(self.name), sm_section(new_name))

        # .gitmodules
        with self.config_writer(write=True).config as cw:
            cw.rename_section(sm_section(self.name), sm_section(new_name))

        self._name = new_name

        # .git/modules
        mod = self.module()
        if mod.has_separate_working_tree():
            destination_module_abspath = self._module_abspath(self.repo, self.path, new_name)
            source_dir = mod.git_dir
            # Let's be sure the submodule name is not so obviously tied to a directory.
            if str(destination_module_abspath).startswith(str(mod.git_dir)):
                tmp_dir = self._module_abspath(self.repo, self.path, str(uuid.uuid4()))
                os.renames(source_dir, tmp_dir)
                source_dir = tmp_dir
            # END handle self-containment
            os.renames(source_dir, destination_module_abspath)
            if mod.working_tree_dir:
                self._write_git_file_and_module_config(mod.working_tree_dir, destination_module_abspath)
        # END move separate git repository

        return self

    # } END edit interface

    # { Query Interface

    @unbare_repo
    def module(self) -> "Repo":
        """
        :return:
            :class:`~git.repo.base.Repo` instance initialized from the repository at our
            submodule path

        :raise git.exc.InvalidGitRepositoryError:
            If a repository was not available.
            This could also mean that it was not yet initialized.
        """
        module_checkout_abspath = self.abspath
        try:
            repo = git.Repo(module_checkout_abspath)
            if repo != self.repo:
                return repo
            # END handle repo uninitialized
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            raise InvalidGitRepositoryError("No valid repository at %s" % module_checkout_abspath) from e
        else:
            raise InvalidGitRepositoryError("Repository at %r was not yet checked out" % module_checkout_abspath)
        # END handle exceptions

    def module_exists(self) -> bool:
        """
        :return:
            ``True`` if our module exists and is a valid git repository.
            See the :meth:`module` method.
        """
        try:
            self.module()
            return True
        except Exception:
            return False
        # END handle exception

    def exists(self) -> bool:
        """
        :return:
            ``True`` if the submodule exists, ``False`` otherwise.
            Please note that a submodule may exist (in the ``.gitmodules`` file) even
            though its module doesn't exist on disk.
        """
        # Keep attributes for later, and restore them if we have no valid data.
        # This way we do not actually alter the state of the object.
        loc = locals()
        for attr in self._cache_attrs:
            try:
                if hasattr(self, attr):
                    loc[attr] = getattr(self, attr)
                # END if we have the attribute cache
            except (cp.NoSectionError, ValueError):
                # On PY3, this can happen apparently... don't know why this doesn't
                # happen on PY2.
                pass
        # END for each attr
        self._clear_cache()

        try:
            try:
                self.path  # noqa: B018
                return True
            except Exception:
                return False
            # END handle exceptions
        finally:
            for attr in self._cache_attrs:
                if attr in loc:
                    setattr(self, attr, loc[attr])
                # END if we have a cache
            # END reapply each attribute
        # END handle object state consistency

    @property
    def branch(self) -> "Head":
        """
        :return:
            The branch instance that we are to checkout

        :raise git.exc.InvalidGitRepositoryError:
            If our module is not yet checked out.
        """
        return mkhead(self.module(), self._branch_path)

    @property
    def branch_path(self) -> PathLike:
        """
        :return:
            Full repository-relative path as string to the branch we would checkout from
            the remote and track
        """
        return self._branch_path

    @property
    def branch_name(self) -> str:
        """
        :return:
            The name of the branch, which is the shortest possible branch name
        """
        # Use an instance method, for this we create a temporary Head instance which
        # uses a repository that is available at least (it makes no difference).
        return git.Head(self.repo, self._branch_path).name

    @property
    def url(self) -> str:
        """:return: The url to the repository our submodule's repository refers to"""
        return self._url

    @property
    def parent_commit(self) -> "Commit":
        """
        :return:
            :class:`~git.objects.commit.Commit` instance with the tree containing the
            ``.gitmodules`` file

        :note:
            Will always point to the current head's commit if it was not set explicitly.
        """
        if self._parent_commit is None:
            return self.repo.commit()
        return self._parent_commit

    @property
    def name(self) -> str:
        """
        :return:
            The name of this submodule. It is used to identify it within the
            ``.gitmodules`` file.

        :note:
            By default, this is the name is the path at which to find the submodule, but
            in GitPython it should be a unique identifier similar to the identifiers
            used for remotes, which allows to change the path of the submodule easily.
        """
        return self._name

    def config_reader(self) -> SectionConstraint[SubmoduleConfigParser]:
        """
        :return:
            ConfigReader instance which allows you to query the configuration values of
            this submodule, as provided by the ``.gitmodules`` file.

        :note:
            The config reader will actually read the data directly from the repository
            and thus does not need nor care about your working tree.

        :note:
            Should be cached by the caller and only kept as long as needed.

        :raise IOError:
            If the ``.gitmodules`` file/blob could not be read.
        """
        return self._config_parser_constrained(read_only=True)

    def children(self) -> IterableList["Submodule"]:
        """
        :return:
            IterableList(Submodule, ...) An iterable list of :class:`Submodule`
            instances which are children of this submodule or 0 if the submodule is not
            checked out.
        """
        return self._get_intermediate_items(self)

    # } END query interface

    # { Iterable Interface

    @classmethod
    def iter_items(
        cls,
        repo: "Repo",
        parent_commit: Union[Commit_ish, str] = "HEAD",
        *args: Any,
        **kwargs: Any,
    ) -> Iterator["Submodule"]:
        """
        :return:
            Iterator yielding :class:`Submodule` instances available in the given
            repository
        """
        try:
            pc = repo.commit(parent_commit)  # Parent commit instance
            parser = cls._config_parser(repo, pc, read_only=True)
        except (IOError, BadName):
            return
        # END handle empty iterator

        for sms in parser.sections():
            n = sm_name(sms)
            p = parser.get(sms, "path")
            u = parser.get(sms, "url")
            b = cls.k_head_default
            if parser.has_option(sms, cls.k_head_option):
                b = str(parser.get(sms, cls.k_head_option))
            # END handle optional information

            # Get the binsha.
            index = repo.index
            try:
                rt = pc.tree  # Root tree
                sm = rt[p]
            except KeyError:
                # Try the index, maybe it was just added.
                try:
                    entry = index.entries[index.entry_key(p, 0)]
                    sm = Submodule(repo, entry.binsha, entry.mode, entry.path)
                except KeyError:
                    # The submodule doesn't exist, probably it wasn't removed from the
                    # .gitmodules file.
                    continue
                # END handle keyerror
            # END handle critical error

            # Make sure we are looking at a submodule object.
            if type(sm) is not git.objects.submodule.base.Submodule:
                continue

            # Fill in remaining info - saves time as it doesn't have to be parsed again.
            sm._name = n
            if pc != repo.commit():
                sm._parent_commit = pc
            # END set only if not most recent!
            sm._branch_path = git.Head.to_full_path(b)
            sm._url = u

            yield sm
        # END for each section

    # } END iterable interface

# === NexusCore/openenv\Lib\site-packages\nltk\classify\maxent.py ===
# Natural Language Toolkit: Maximum Entropy Classifiers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Dmitry Chichkov <dchichkov@gmail.com> (TypedMaxentFeatureEncoding)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A classifier model based on maximum entropy modeling framework.  This
framework considers all of the probability distributions that are
empirically consistent with the training data; and chooses the
distribution with the highest entropy.  A probability distribution is
"empirically consistent" with a set of training data if its estimated
frequency with which a class and a feature vector value co-occur is
equal to the actual frequency in the data.

Terminology: 'feature'
======================
The term *feature* is usually used to refer to some property of an
unlabeled token.  For example, when performing word sense
disambiguation, we might define a ``'prevword'`` feature whose value is
the word preceding the target word.  However, in the context of
maxent modeling, the term *feature* is typically used to refer to a
property of a "labeled" token.  In order to prevent confusion, we
will introduce two distinct terms to disambiguate these two different
concepts:

  - An "input-feature" is a property of an unlabeled token.
  - A "joint-feature" is a property of a labeled token.

In the rest of the ``nltk.classify`` module, the term "features" is
used to refer to what we will call "input-features" in this module.

In literature that describes and discusses maximum entropy models,
input-features are typically called "contexts", and joint-features
are simply referred to as "features".

Converting Input-Features to Joint-Features
-------------------------------------------
In maximum entropy models, joint-features are required to have numeric
values.  Typically, each input-feature ``input_feat`` is mapped to a
set of joint-features of the form:

|   joint_feat(token, label) = { 1 if input_feat(token) == feat_val
|                              {      and label == some_label
|                              {
|                              { 0 otherwise

For all values of ``feat_val`` and ``some_label``.  This mapping is
performed by classes that implement the ``MaxentFeatureEncodingI``
interface.
"""
try:
    import numpy
except ImportError:
    pass

import os
import tempfile
from collections import defaultdict

from nltk.classify.api import ClassifierI
from nltk.classify.megam import call_megam, parse_megam_weights, write_megam_file
from nltk.classify.tadm import call_tadm, parse_tadm_weights, write_tadm_file
from nltk.classify.util import CutoffChecker, accuracy, log_likelihood
from nltk.data import gzip_open_unicode
from nltk.probability import DictionaryProbDist
from nltk.util import OrderedDict

__docformat__ = "epytext en"

######################################################################
# { Classifier Model
######################################################################


class MaxentClassifier(ClassifierI):
    """
    A maximum entropy classifier (also known as a "conditional
    exponential classifier").  This classifier is parameterized by a
    set of "weights", which are used to combine the joint-features
    that are generated from a featureset by an "encoding".  In
    particular, the encoding maps each ``(featureset, label)`` pair to
    a vector.  The probability of each label is then computed using
    the following equation::

                                dotprod(weights, encode(fs,label))
      prob(fs|label) = ---------------------------------------------------
                       sum(dotprod(weights, encode(fs,l)) for l in labels)

    Where ``dotprod`` is the dot product::

      dotprod(a,b) = sum(x*y for (x,y) in zip(a,b))
    """

    def __init__(self, encoding, weights, logarithmic=True):
        """
        Construct a new maxent classifier model.  Typically, new
        classifier models are created using the ``train()`` method.

        :type encoding: MaxentFeatureEncodingI
        :param encoding: An encoding that is used to convert the
            featuresets that are given to the ``classify`` method into
            joint-feature vectors, which are used by the maxent
            classifier model.

        :type weights: list of float
        :param weights:  The feature weight vector for this classifier.

        :type logarithmic: bool
        :param logarithmic: If false, then use non-logarithmic weights.
        """
        self._encoding = encoding
        self._weights = weights
        self._logarithmic = logarithmic
        # self._logarithmic = False
        assert encoding.length() == len(weights)

    def labels(self):
        return self._encoding.labels()

    def set_weights(self, new_weights):
        """
        Set the feature weight vector for this classifier.
        :param new_weights: The new feature weight vector.
        :type new_weights: list of float
        """
        self._weights = new_weights
        assert self._encoding.length() == len(new_weights)

    def weights(self):
        """
        :return: The feature weight vector for this classifier.
        :rtype: list of float
        """
        return self._weights

    def classify(self, featureset):
        return self.prob_classify(featureset).max()

    def prob_classify(self, featureset):
        prob_dict = {}
        for label in self._encoding.labels():
            feature_vector = self._encoding.encode(featureset, label)

            if self._logarithmic:
                total = 0.0
                for f_id, f_val in feature_vector:
                    total += self._weights[f_id] * f_val
                prob_dict[label] = total

            else:
                prod = 1.0
                for f_id, f_val in feature_vector:
                    prod *= self._weights[f_id] ** f_val
                prob_dict[label] = prod

        # Normalize the dictionary to give a probability distribution
        return DictionaryProbDist(prob_dict, log=self._logarithmic, normalize=True)

    def explain(self, featureset, columns=4):
        """
        Print a table showing the effect of each of the features in
        the given feature set, and how they combine to determine the
        probabilities of each label for that featureset.
        """
        descr_width = 50
        TEMPLATE = "  %-" + str(descr_width - 2) + "s%s%8.3f"

        pdist = self.prob_classify(featureset)
        labels = sorted(pdist.samples(), key=pdist.prob, reverse=True)
        labels = labels[:columns]
        print(
            "  Feature".ljust(descr_width)
            + "".join("%8s" % (("%s" % l)[:7]) for l in labels)
        )
        print("  " + "-" * (descr_width - 2 + 8 * len(labels)))
        sums = defaultdict(int)
        for i, label in enumerate(labels):
            feature_vector = self._encoding.encode(featureset, label)
            feature_vector.sort(
                key=lambda fid__: abs(self._weights[fid__[0]]), reverse=True
            )
            for f_id, f_val in feature_vector:
                if self._logarithmic:
                    score = self._weights[f_id] * f_val
                else:
                    score = self._weights[f_id] ** f_val
                descr = self._encoding.describe(f_id)
                descr = descr.split(" and label is ")[0]  # hack
                descr += " (%s)" % f_val  # hack
                if len(descr) > 47:
                    descr = descr[:44] + "..."
                print(TEMPLATE % (descr, i * 8 * " ", score))
                sums[label] += score
        print("  " + "-" * (descr_width - 1 + 8 * len(labels)))
        print(
            "  TOTAL:".ljust(descr_width) + "".join("%8.3f" % sums[l] for l in labels)
        )
        print(
            "  PROBS:".ljust(descr_width)
            + "".join("%8.3f" % pdist.prob(l) for l in labels)
        )

    def most_informative_features(self, n=10):
        """
        Generates the ranked list of informative features from most to least.
        """
        if hasattr(self, "_most_informative_features"):
            return self._most_informative_features[:n]
        else:
            self._most_informative_features = sorted(
                list(range(len(self._weights))),
                key=lambda fid: abs(self._weights[fid]),
                reverse=True,
            )
            return self._most_informative_features[:n]

    def show_most_informative_features(self, n=10, show="all"):
        """
        :param show: all, neg, or pos (for negative-only or positive-only)
        :type show: str
        :param n: The no. of top features
        :type n: int
        """
        # Use None the full list of ranked features.
        fids = self.most_informative_features(None)
        if show == "pos":
            fids = [fid for fid in fids if self._weights[fid] > 0]
        elif show == "neg":
            fids = [fid for fid in fids if self._weights[fid] < 0]
        for fid in fids[:n]:
            print(f"{self._weights[fid]:8.3f} {self._encoding.describe(fid)}")

    def __repr__(self):
        return "<ConditionalExponentialClassifier: %d labels, %d features>" % (
            len(self._encoding.labels()),
            self._encoding.length(),
        )

    #: A list of the algorithm names that are accepted for the
    #: ``train()`` method's ``algorithm`` parameter.
    ALGORITHMS = ["GIS", "IIS", "MEGAM", "TADM"]

    @classmethod
    def train(
        cls,
        train_toks,
        algorithm=None,
        trace=3,
        encoding=None,
        labels=None,
        gaussian_prior_sigma=0,
        **cutoffs,
    ):
        """
        Train a new maxent classifier based on the given corpus of
        training samples.  This classifier will have its weights
        chosen to maximize entropy while remaining empirically
        consistent with the training corpus.

        :rtype: MaxentClassifier
        :return: The new maxent classifier

        :type train_toks: list
        :param train_toks: Training data, represented as a list of
            pairs, the first member of which is a featureset,
            and the second of which is a classification label.

        :type algorithm: str
        :param algorithm: A case-insensitive string, specifying which
            algorithm should be used to train the classifier.  The
            following algorithms are currently available.

            - Iterative Scaling Methods: Generalized Iterative Scaling (``'GIS'``),
              Improved Iterative Scaling (``'IIS'``)
            - External Libraries (requiring megam):
              LM-BFGS algorithm, with training performed by Megam (``'megam'``)

            The default algorithm is ``'IIS'``.

        :type trace: int
        :param trace: The level of diagnostic tracing output to produce.
            Higher values produce more verbose output.
        :type encoding: MaxentFeatureEncodingI
        :param encoding: A feature encoding, used to convert featuresets
            into feature vectors.  If none is specified, then a
            ``BinaryMaxentFeatureEncoding`` will be built based on the
            features that are attested in the training corpus.
        :type labels: list(str)
        :param labels: The set of possible labels.  If none is given, then
            the set of all labels attested in the training data will be
            used instead.
        :param gaussian_prior_sigma: The sigma value for a gaussian
            prior on model weights.  Currently, this is supported by
            ``megam``. For other algorithms, its value is ignored.
        :param cutoffs: Arguments specifying various conditions under
            which the training should be halted.  (Some of the cutoff
            conditions are not supported by some algorithms.)

            - ``max_iter=v``: Terminate after ``v`` iterations.
            - ``min_ll=v``: Terminate after the negative average
              log-likelihood drops under ``v``.
            - ``min_lldelta=v``: Terminate if a single iteration improves
              log likelihood by less than ``v``.
        """
        if algorithm is None:
            algorithm = "iis"
        for key in cutoffs:
            if key not in (
                "max_iter",
                "min_ll",
                "min_lldelta",
                "max_acc",
                "min_accdelta",
                "count_cutoff",
                "norm",
                "explicit",
                "bernoulli",
            ):
                raise TypeError("Unexpected keyword arg %r" % key)
        algorithm = algorithm.lower()
        if algorithm == "iis":
            return train_maxent_classifier_with_iis(
                train_toks, trace, encoding, labels, **cutoffs
            )
        elif algorithm == "gis":
            return train_maxent_classifier_with_gis(
                train_toks, trace, encoding, labels, **cutoffs
            )
        elif algorithm == "megam":
            return train_maxent_classifier_with_megam(
                train_toks, trace, encoding, labels, gaussian_prior_sigma, **cutoffs
            )
        elif algorithm == "tadm":
            kwargs = cutoffs
            kwargs["trace"] = trace
            kwargs["encoding"] = encoding
            kwargs["labels"] = labels
            kwargs["gaussian_prior_sigma"] = gaussian_prior_sigma
            return TadmMaxentClassifier.train(train_toks, **kwargs)
        else:
            raise ValueError("Unknown algorithm %s" % algorithm)


#: Alias for MaxentClassifier.
ConditionalExponentialClassifier = MaxentClassifier


######################################################################
# { Feature Encodings
######################################################################


class MaxentFeatureEncodingI:
    """
    A mapping that converts a set of input-feature values to a vector
    of joint-feature values, given a label.  This conversion is
    necessary to translate featuresets into a format that can be used
    by maximum entropy models.

    The set of joint-features used by a given encoding is fixed, and
    each index in the generated joint-feature vectors corresponds to a
    single joint-feature.  The length of the generated joint-feature
    vectors is therefore constant (for a given encoding).

    Because the joint-feature vectors generated by
    ``MaxentFeatureEncodingI`` are typically very sparse, they are
    represented as a list of ``(index, value)`` tuples, specifying the
    value of each non-zero joint-feature.

    Feature encodings are generally created using the ``train()``
    method, which generates an appropriate encoding based on the
    input-feature values and labels that are present in a given
    corpus.
    """

    def encode(self, featureset, label):
        """
        Given a (featureset, label) pair, return the corresponding
        vector of joint-feature values.  This vector is represented as
        a list of ``(index, value)`` tuples, specifying the value of
        each non-zero joint-feature.

        :type featureset: dict
        :rtype: list(tuple(int, int))
        """
        raise NotImplementedError()

    def length(self):
        """
        :return: The size of the fixed-length joint-feature vectors
            that are generated by this encoding.
        :rtype: int
        """
        raise NotImplementedError()

    def labels(self):
        """
        :return: A list of the \"known labels\" -- i.e., all labels
            ``l`` such that ``self.encode(fs,l)`` can be a nonzero
            joint-feature vector for some value of ``fs``.
        :rtype: list
        """
        raise NotImplementedError()

    def describe(self, fid):
        """
        :return: A string describing the value of the joint-feature
            whose index in the generated feature vectors is ``fid``.
        :rtype: str
        """
        raise NotImplementedError()

    def train(cls, train_toks):
        """
        Construct and return new feature encoding, based on a given
        training corpus ``train_toks``.

        :type train_toks: list(tuple(dict, str))
        :param train_toks: Training data, represented as a list of
            pairs, the first member of which is a feature dictionary,
            and the second of which is a classification label.
        """
        raise NotImplementedError()


class FunctionBackedMaxentFeatureEncoding(MaxentFeatureEncodingI):
    """
    A feature encoding that calls a user-supplied function to map a
    given featureset/label pair to a sparse joint-feature vector.
    """

    def __init__(self, func, length, labels):
        """
        Construct a new feature encoding based on the given function.

        :type func: (callable)
        :param func: A function that takes two arguments, a featureset
             and a label, and returns the sparse joint feature vector
             that encodes them::

                 func(featureset, label) -> feature_vector

             This sparse joint feature vector (``feature_vector``) is a
             list of ``(index,value)`` tuples.

        :type length: int
        :param length: The size of the fixed-length joint-feature
            vectors that are generated by this encoding.

        :type labels: list
        :param labels: A list of the \"known labels\" for this
            encoding -- i.e., all labels ``l`` such that
            ``self.encode(fs,l)`` can be a nonzero joint-feature vector
            for some value of ``fs``.
        """
        self._length = length
        self._func = func
        self._labels = labels

    def encode(self, featureset, label):
        return self._func(featureset, label)

    def length(self):
        return self._length

    def labels(self):
        return self._labels

    def describe(self, fid):
        return "no description available"


class BinaryMaxentFeatureEncoding(MaxentFeatureEncodingI):
    """
    A feature encoding that generates vectors containing a binary
    joint-features of the form:

    |  joint_feat(fs, l) = { 1 if (fs[fname] == fval) and (l == label)
    |                      {
    |                      { 0 otherwise

    Where ``fname`` is the name of an input-feature, ``fval`` is a value
    for that input-feature, and ``label`` is a label.

    Typically, these features are constructed based on a training
    corpus, using the ``train()`` method.  This method will create one
    feature for each combination of ``fname``, ``fval``, and ``label``
    that occurs at least once in the training corpus.

    The ``unseen_features`` parameter can be used to add "unseen-value
    features", which are used whenever an input feature has a value
    that was not encountered in the training corpus.  These features
    have the form:

    |  joint_feat(fs, l) = { 1 if is_unseen(fname, fs[fname])
    |                      {      and l == label
    |                      {
    |                      { 0 otherwise

    Where ``is_unseen(fname, fval)`` is true if the encoding does not
    contain any joint features that are true when ``fs[fname]==fval``.

    The ``alwayson_features`` parameter can be used to add "always-on
    features", which have the form::

    |  joint_feat(fs, l) = { 1 if (l == label)
    |                      {
    |                      { 0 otherwise

    These always-on features allow the maxent model to directly model
    the prior probabilities of each label.
    """

    def __init__(self, labels, mapping, unseen_features=False, alwayson_features=False):
        """
        :param labels: A list of the \"known labels\" for this encoding.

        :param mapping: A dictionary mapping from ``(fname,fval,label)``
            tuples to corresponding joint-feature indexes.  These
            indexes must be the set of integers from 0...len(mapping).
            If ``mapping[fname,fval,label]=id``, then
            ``self.encode(..., fname:fval, ..., label)[id]`` is 1;
            otherwise, it is 0.

        :param unseen_features: If true, then include unseen value
           features in the generated joint-feature vectors.

        :param alwayson_features: If true, then include always-on
           features in the generated joint-feature vectors.
        """
        if set(mapping.values()) != set(range(len(mapping))):
            raise ValueError(
                "Mapping values must be exactly the "
                "set of integers from 0...len(mapping)"
            )

        self._labels = list(labels)
        """A list of attested labels."""

        self._mapping = mapping
        """dict mapping from (fname,fval,label) -> fid"""

        self._length = len(mapping)
        """The length of generated joint feature vectors."""

        self._alwayson = None
        """dict mapping from label -> fid"""

        self._unseen = None
        """dict mapping from fname -> fid"""

        if alwayson_features:
            self._alwayson = {
                label: i + self._length for (i, label) in enumerate(labels)
            }
            self._length += len(self._alwayson)

        if unseen_features:
            fnames = {fname for (fname, fval, label) in mapping}
            self._unseen = {fname: i + self._length for (i, fname) in enumerate(fnames)}
            self._length += len(fnames)

    def encode(self, featureset, label):
        # Inherit docs.
        encoding = []

        # Convert input-features to joint-features:
        for fname, fval in featureset.items():
            # Known feature name & value:
            if (fname, fval, label) in self._mapping:
                encoding.append((self._mapping[fname, fval, label], 1))

            # Otherwise, we might want to fire an "unseen-value feature".
            elif self._unseen:
                # Have we seen this fname/fval combination with any label?
                for label2 in self._labels:
                    if (fname, fval, label2) in self._mapping:
                        break  # we've seen this fname/fval combo
                # We haven't -- fire the unseen-value feature
                else:
                    if fname in self._unseen:
                        encoding.append((self._unseen[fname], 1))

        # Add always-on features:
        if self._alwayson and label in self._alwayson:
            encoding.append((self._alwayson[label], 1))

        return encoding

    def describe(self, f_id):
        # Inherit docs.
        if not isinstance(f_id, int):
            raise TypeError("describe() expected an int")
        try:
            self._inv_mapping
        except AttributeError:
            self._inv_mapping = [-1] * len(self._mapping)
            for info, i in self._mapping.items():
                self._inv_mapping[i] = info

        if f_id < len(self._mapping):
            (fname, fval, label) = self._inv_mapping[f_id]
            return f"{fname}=={fval!r} and label is {label!r}"
        elif self._alwayson and f_id in self._alwayson.values():
            for label, f_id2 in self._alwayson.items():
                if f_id == f_id2:
                    return "label is %r" % label
        elif self._unseen and f_id in self._unseen.values():
            for fname, f_id2 in self._unseen.items():
                if f_id == f_id2:
                    return "%s is unseen" % fname
        else:
            raise ValueError("Bad feature id")

    def labels(self):
        # Inherit docs.
        return self._labels

    def length(self):
        # Inherit docs.
        return self._length

    @classmethod
    def train(cls, train_toks, count_cutoff=0, labels=None, **options):
        """
        Construct and return new feature encoding, based on a given
        training corpus ``train_toks``.  See the class description
        ``BinaryMaxentFeatureEncoding`` for a description of the
        joint-features that will be included in this encoding.

        :type train_toks: list(tuple(dict, str))
        :param train_toks: Training data, represented as a list of
            pairs, the first member of which is a feature dictionary,
            and the second of which is a classification label.

        :type count_cutoff: int
        :param count_cutoff: A cutoff value that is used to discard
            rare joint-features.  If a joint-feature's value is 1
            fewer than ``count_cutoff`` times in the training corpus,
            then that joint-feature is not included in the generated
            encoding.

        :type labels: list
        :param labels: A list of labels that should be used by the
            classifier.  If not specified, then the set of labels
            attested in ``train_toks`` will be used.

        :param options: Extra parameters for the constructor, such as
            ``unseen_features`` and ``alwayson_features``.
        """
        mapping = {}  # maps (fname, fval, label) -> fid
        seen_labels = set()  # The set of labels we've encountered
        count = defaultdict(int)  # maps (fname, fval) -> count

        for tok, label in train_toks:
            if labels and label not in labels:
                raise ValueError("Unexpected label %s" % label)
            seen_labels.add(label)

            # Record each of the features.
            for fname, fval in tok.items():
                # If a count cutoff is given, then only add a joint
                # feature once the corresponding (fname, fval, label)
                # tuple exceeds that cutoff.
                count[fname, fval] += 1
                if count[fname, fval] >= count_cutoff:
                    if (fname, fval, label) not in mapping:
                        mapping[fname, fval, label] = len(mapping)

        if labels is None:
            labels = seen_labels
        return cls(labels, mapping, **options)


class GISEncoding(BinaryMaxentFeatureEncoding):
    """
    A binary feature encoding which adds one new joint-feature to the
    joint-features defined by ``BinaryMaxentFeatureEncoding``: a
    correction feature, whose value is chosen to ensure that the
    sparse vector always sums to a constant non-negative number.  This
    new feature is used to ensure two preconditions for the GIS
    training algorithm:

      - At least one feature vector index must be nonzero for every
        token.
      - The feature vector must sum to a constant non-negative number
        for every token.
    """

    def __init__(
        self, labels, mapping, unseen_features=False, alwayson_features=False, C=None
    ):
        """
        :param C: The correction constant.  The value of the correction
            feature is based on this value.  In particular, its value is
            ``C - sum([v for (f,v) in encoding])``.
        :seealso: ``BinaryMaxentFeatureEncoding.__init__``
        """
        BinaryMaxentFeatureEncoding.__init__(
            self, labels, mapping, unseen_features, alwayson_features
        )
        if C is None:
            C = len({fname for (fname, fval, label) in mapping}) + 1
        self._C = C

    @property
    def C(self):
        """The non-negative constant that all encoded feature vectors
        will sum to."""
        return self._C

    def encode(self, featureset, label):
        # Get the basic encoding.
        encoding = BinaryMaxentFeatureEncoding.encode(self, featureset, label)
        base_length = BinaryMaxentFeatureEncoding.length(self)

        # Add a correction feature.
        total = sum(v for (f, v) in encoding)
        if total >= self._C:
            raise ValueError("Correction feature is not high enough!")
        encoding.append((base_length, self._C - total))

        # Return the result
        return encoding

    def length(self):
        return BinaryMaxentFeatureEncoding.length(self) + 1

    def describe(self, f_id):
        if f_id == BinaryMaxentFeatureEncoding.length(self):
            return "Correction feature (%s)" % self._C
        else:
            return BinaryMaxentFeatureEncoding.describe(self, f_id)


class TadmEventMaxentFeatureEncoding(BinaryMaxentFeatureEncoding):
    def __init__(self, labels, mapping, unseen_features=False, alwayson_features=False):
        self._mapping = OrderedDict(mapping)
        self._label_mapping = OrderedDict()
        BinaryMaxentFeatureEncoding.__init__(
            self, labels, self._mapping, unseen_features, alwayson_features
        )

    def encode(self, featureset, label):
        encoding = []
        for feature, value in featureset.items():
            if (feature, label) not in self._mapping:
                self._mapping[(feature, label)] = len(self._mapping)
            if value not in self._label_mapping:
                if not isinstance(value, int):
                    self._label_mapping[value] = len(self._label_mapping)
                else:
                    self._label_mapping[value] = value
            encoding.append(
                (self._mapping[(feature, label)], self._label_mapping[value])
            )
        return encoding

    def labels(self):
        return self._labels

    def describe(self, fid):
        for feature, label in self._mapping:
            if self._mapping[(feature, label)] == fid:
                return (feature, label)

    def length(self):
        return len(self._mapping)

    @classmethod
    def train(cls, train_toks, count_cutoff=0, labels=None, **options):
        mapping = OrderedDict()
        if not labels:
            labels = []

        # This gets read twice, so compute the values in case it's lazy.
        train_toks = list(train_toks)

        for featureset, label in train_toks:
            if label not in labels:
                labels.append(label)

        for featureset, label in train_toks:
            for label in labels:
                for feature in featureset:
                    if (feature, label) not in mapping:
                        mapping[(feature, label)] = len(mapping)

        return cls(labels, mapping, **options)


class TypedMaxentFeatureEncoding(MaxentFeatureEncodingI):
    """
    A feature encoding that generates vectors containing integer,
    float and binary joint-features of the form:

    Binary (for string and boolean features):

    |  joint_feat(fs, l) = { 1 if (fs[fname] == fval) and (l == label)
    |                      {
    |                      { 0 otherwise

    Value (for integer and float features):

    |  joint_feat(fs, l) = { fval if     (fs[fname] == type(fval))
    |                      {         and (l == label)
    |                      {
    |                      { not encoded otherwise

    Where ``fname`` is the name of an input-feature, ``fval`` is a value
    for that input-feature, and ``label`` is a label.

    Typically, these features are constructed based on a training
    corpus, using the ``train()`` method.

    For string and boolean features [type(fval) not in (int, float)]
    this method will create one feature for each combination of
    ``fname``, ``fval``, and ``label`` that occurs at least once in the
    training corpus.

    For integer and float features [type(fval) in (int, float)] this
    method will create one feature for each combination of ``fname``
    and ``label`` that occurs at least once in the training corpus.

    For binary features the ``unseen_features`` parameter can be used
    to add "unseen-value features", which are used whenever an input
    feature has a value that was not encountered in the training
    corpus.  These features have the form:

    |  joint_feat(fs, l) = { 1 if is_unseen(fname, fs[fname])
    |                      {      and l == label
    |                      {
    |                      { 0 otherwise

    Where ``is_unseen(fname, fval)`` is true if the encoding does not
    contain any joint features that are true when ``fs[fname]==fval``.

    The ``alwayson_features`` parameter can be used to add "always-on
    features", which have the form:

    |  joint_feat(fs, l) = { 1 if (l == label)
    |                      {
    |                      { 0 otherwise

    These always-on features allow the maxent model to directly model
    the prior probabilities of each label.
    """

    def __init__(self, labels, mapping, unseen_features=False, alwayson_features=False):
        """
        :param labels: A list of the \"known labels\" for this encoding.

        :param mapping: A dictionary mapping from ``(fname,fval,label)``
            tuples to corresponding joint-feature indexes.  These
            indexes must be the set of integers from 0...len(mapping).
            If ``mapping[fname,fval,label]=id``, then
            ``self.encode({..., fname:fval, ...``, label)[id]} is 1;
            otherwise, it is 0.

        :param unseen_features: If true, then include unseen value
           features in the generated joint-feature vectors.

        :param alwayson_features: If true, then include always-on
           features in the generated joint-feature vectors.
        """
        if set(mapping.values()) != set(range(len(mapping))):
            raise ValueError(
                "Mapping values must be exactly the "
                "set of integers from 0...len(mapping)"
            )

        self._labels = list(labels)
        """A list of attested labels."""

        self._mapping = mapping
        """dict mapping from (fname,fval,label) -> fid"""

        self._length = len(mapping)
        """The length of generated joint feature vectors."""

        self._alwayson = None
        """dict mapping from label -> fid"""

        self._unseen = None
        """dict mapping from fname -> fid"""

        if alwayson_features:
            self._alwayson = {
                label: i + self._length for (i, label) in enumerate(labels)
            }
            self._length += len(self._alwayson)

        if unseen_features:
            fnames = {fname for (fname, fval, label) in mapping}
            self._unseen = {fname: i + self._length for (i, fname) in enumerate(fnames)}
            self._length += len(fnames)

    def encode(self, featureset, label):
        # Inherit docs.
        encoding = []

        # Convert input-features to joint-features:
        for fname, fval in featureset.items():
            if isinstance(fval, (int, float)):
                # Known feature name & value:
                if (fname, type(fval), label) in self._mapping:
                    encoding.append((self._mapping[fname, type(fval), label], fval))
            else:
                # Known feature name & value:
                if (fname, fval, label) in self._mapping:
                    encoding.append((self._mapping[fname, fval, label], 1))

                # Otherwise, we might want to fire an "unseen-value feature".
                elif self._unseen:
                    # Have we seen this fname/fval combination with any label?
                    for label2 in self._labels:
                        if (fname, fval, label2) in self._mapping:
                            break  # we've seen this fname/fval combo
                    # We haven't -- fire the unseen-value feature
                    else:
                        if fname in self._unseen:
                            encoding.append((self._unseen[fname], 1))

        # Add always-on features:
        if self._alwayson and label in self._alwayson:
            encoding.append((self._alwayson[label], 1))

        return encoding

    def describe(self, f_id):
        # Inherit docs.
        if not isinstance(f_id, int):
            raise TypeError("describe() expected an int")
        try:
            self._inv_mapping
        except AttributeError:
            self._inv_mapping = [-1] * len(self._mapping)
            for info, i in self._mapping.items():
                self._inv_mapping[i] = info

        if f_id < len(self._mapping):
            (fname, fval, label) = self._inv_mapping[f_id]
            return f"{fname}=={fval!r} and label is {label!r}"
        elif self._alwayson and f_id in self._alwayson.values():
            for label, f_id2 in self._alwayson.items():
                if f_id == f_id2:
                    return "label is %r" % label
        elif self._unseen and f_id in self._unseen.values():
            for fname, f_id2 in self._unseen.items():
                if f_id == f_id2:
                    return "%s is unseen" % fname
        else:
            raise ValueError("Bad feature id")

    def labels(self):
        # Inherit docs.
        return self._labels

    def length(self):
        # Inherit docs.
        return self._length

    @classmethod
    def train(cls, train_toks, count_cutoff=0, labels=None, **options):
        """
        Construct and return new feature encoding, based on a given
        training corpus ``train_toks``.  See the class description
        ``TypedMaxentFeatureEncoding`` for a description of the
        joint-features that will be included in this encoding.

        Note: recognized feature values types are (int, float), over
        types are interpreted as regular binary features.

        :type train_toks: list(tuple(dict, str))
        :param train_toks: Training data, represented as a list of
            pairs, the first member of which is a feature dictionary,
            and the second of which is a classification label.

        :type count_cutoff: int
        :param count_cutoff: A cutoff value that is used to discard
            rare joint-features.  If a joint-feature's value is 1
            fewer than ``count_cutoff`` times in the training corpus,
            then that joint-feature is not included in the generated
            encoding.

        :type labels: list
        :param labels: A list of labels that should be used by the
            classifier.  If not specified, then the set of labels
            attested in ``train_toks`` will be used.

        :param options: Extra parameters for the constructor, such as
            ``unseen_features`` and ``alwayson_features``.
        """
        mapping = {}  # maps (fname, fval, label) -> fid
        seen_labels = set()  # The set of labels we've encountered
        count = defaultdict(int)  # maps (fname, fval) -> count

        for tok, label in train_toks:
            if labels and label not in labels:
                raise ValueError("Unexpected label %s" % label)
            seen_labels.add(label)

            # Record each of the features.
            for fname, fval in tok.items():
                if type(fval) in (int, float):
                    fval = type(fval)
                # If a count cutoff is given, then only add a joint
                # feature once the corresponding (fname, fval, label)
                # tuple exceeds that cutoff.
                count[fname, fval] += 1
                if count[fname, fval] >= count_cutoff:
                    if (fname, fval, label) not in mapping:
                        mapping[fname, fval, label] = len(mapping)

        if labels is None:
            labels = seen_labels
        return cls(labels, mapping, **options)


######################################################################
# { Classifier Trainer: Generalized Iterative Scaling
######################################################################


def train_maxent_classifier_with_gis(
    train_toks, trace=3, encoding=None, labels=None, **cutoffs
):
    """
    Train a new ``ConditionalExponentialClassifier``, using the given
    training samples, using the Generalized Iterative Scaling
    algorithm.  This ``ConditionalExponentialClassifier`` will encode
    the model that maximizes entropy from all the models that are
    empirically consistent with ``train_toks``.

    :see: ``train_maxent_classifier()`` for parameter descriptions.
    """
    cutoffs.setdefault("max_iter", 100)
    cutoffchecker = CutoffChecker(cutoffs)

    # Construct an encoding from the training data.
    if encoding is None:
        encoding = GISEncoding.train(train_toks, labels=labels)

    if not hasattr(encoding, "C"):
        raise TypeError(
            "The GIS algorithm requires an encoding that "
            "defines C (e.g., GISEncoding)."
        )

    # Cinv is the inverse of the sum of each joint feature vector.
    # This controls the learning rate: higher Cinv (or lower C) gives
    # faster learning.
    Cinv = 1.0 / encoding.C

    # Count how many times each feature occurs in the training data.
    empirical_fcount = calculate_empirical_fcount(train_toks, encoding)

    # Check for any features that are not attested in train_toks.
    unattested = set(numpy.nonzero(empirical_fcount == 0)[0])

    # Build the classifier.  Start with weight=0 for each attested
    # feature, and weight=-infinity for each unattested feature.
    weights = numpy.zeros(len(empirical_fcount), "d")
    for fid in unattested:
        weights[fid] = numpy.NINF
    classifier = ConditionalExponentialClassifier(encoding, weights)

    # Take the log of the empirical fcount.
    log_empirical_fcount = numpy.log2(empirical_fcount)
    del empirical_fcount

    if trace > 0:
        print("  ==> Training (%d iterations)" % cutoffs["max_iter"])
    if trace > 2:
        print()
        print("      Iteration    Log Likelihood    Accuracy")
        print("      ---------------------------------------")

    # Train the classifier.
    try:
        while True:
            if trace > 2:
                ll = cutoffchecker.ll or log_likelihood(classifier, train_toks)
                acc = cutoffchecker.acc or accuracy(classifier, train_toks)
                iternum = cutoffchecker.iter
                print("     %9d    %14.5f    %9.3f" % (iternum, ll, acc))

            # Use the model to estimate the number of times each
            # feature should occur in the training data.
            estimated_fcount = calculate_estimated_fcount(
                classifier, train_toks, encoding
            )

            # Take the log of estimated fcount (avoid taking log(0).)
            for fid in unattested:
                estimated_fcount[fid] += 1
            log_estimated_fcount = numpy.log2(estimated_fcount)
            del estimated_fcount

            # Update the classifier weights
            weights = classifier.weights()
            weights += (log_empirical_fcount - log_estimated_fcount) * Cinv
            classifier.set_weights(weights)

            # Check the log-likelihood & accuracy cutoffs.
            if cutoffchecker.check(classifier, train_toks):
                break

    except KeyboardInterrupt:
        print("      Training stopped: keyboard interrupt")
    except:
        raise

    if trace > 2:
        ll = log_likelihood(classifier, train_toks)
        acc = accuracy(classifier, train_toks)
        print(f"         Final    {ll:14.5f}    {acc:9.3f}")

    # Return the classifier.
    return classifier


def calculate_empirical_fcount(train_toks, encoding):
    fcount = numpy.zeros(encoding.length(), "d")

    for tok, label in train_toks:
        for index, val in encoding.encode(tok, label):
            fcount[index] += val

    return fcount


def calculate_estimated_fcount(classifier, train_toks, encoding):
    fcount = numpy.zeros(encoding.length(), "d")

    for tok, label in train_toks:
        pdist = classifier.prob_classify(tok)
        for label in pdist.samples():
            prob = pdist.prob(label)
            for fid, fval in encoding.encode(tok, label):
                fcount[fid] += prob * fval

    return fcount


######################################################################
# { Classifier Trainer: Improved Iterative Scaling
######################################################################


def train_maxent_classifier_with_iis(
    train_toks, trace=3, encoding=None, labels=None, **cutoffs
):
    """
    Train a new ``ConditionalExponentialClassifier``, using the given
    training samples, using the Improved Iterative Scaling algorithm.
    This ``ConditionalExponentialClassifier`` will encode the model
    that maximizes entropy from all the models that are empirically
    consistent with ``train_toks``.

    :see: ``train_maxent_classifier()`` for parameter descriptions.
    """
    cutoffs.setdefault("max_iter", 100)
    cutoffchecker = CutoffChecker(cutoffs)

    # Construct an encoding from the training data.
    if encoding is None:
        encoding = BinaryMaxentFeatureEncoding.train(train_toks, labels=labels)

    # Count how many times each feature occurs in the training data.
    empirical_ffreq = calculate_empirical_fcount(train_toks, encoding) / len(train_toks)

    # Find the nf map, and related variables nfarray and nfident.
    # nf is the sum of the features for a given labeled text.
    # nfmap compresses this sparse set of values to a dense list.
    # nfarray performs the reverse operation.  nfident is
    # nfarray multiplied by an identity matrix.
    nfmap = calculate_nfmap(train_toks, encoding)
    nfarray = numpy.array(sorted(nfmap, key=nfmap.__getitem__), "d")
    nftranspose = numpy.reshape(nfarray, (len(nfarray), 1))

    # Check for any features that are not attested in train_toks.
    unattested = set(numpy.nonzero(empirical_ffreq == 0)[0])

    # Build the classifier.  Start with weight=0 for each attested
    # feature, and weight=-infinity for each unattested feature.
    weights = numpy.zeros(len(empirical_ffreq), "d")
    for fid in unattested:
        weights[fid] = numpy.NINF
    classifier = ConditionalExponentialClassifier(encoding, weights)

    if trace > 0:
        print("  ==> Training (%d iterations)" % cutoffs["max_iter"])
    if trace > 2:
        print()
        print("      Iteration    Log Likelihood    Accuracy")
        print("      ---------------------------------------")

    # Train the classifier.
    try:
        while True:
            if trace > 2:
                ll = cutoffchecker.ll or log_likelihood(classifier, train_toks)
                acc = cutoffchecker.acc or accuracy(classifier, train_toks)
                iternum = cutoffchecker.iter
                print("     %9d    %14.5f    %9.3f" % (iternum, ll, acc))

            # Calculate the deltas for this iteration, using Newton's method.
            deltas = calculate_deltas(
                train_toks,
                classifier,
                unattested,
                empirical_ffreq,
                nfmap,
                nfarray,
                nftranspose,
                encoding,
            )

            # Use the deltas to update our weights.
            weights = classifier.weights()
            weights += deltas
            classifier.set_weights(weights)

            # Check the log-likelihood & accuracy cutoffs.
            if cutoffchecker.check(classifier, train_toks):
                break

    except KeyboardInterrupt:
        print("      Training stopped: keyboard interrupt")
    except:
        raise

    if trace > 2:
        ll = log_likelihood(classifier, train_toks)
        acc = accuracy(classifier, train_toks)
        print(f"         Final    {ll:14.5f}    {acc:9.3f}")

    # Return the classifier.
    return classifier


def calculate_nfmap(train_toks, encoding):
    """
    Construct a map that can be used to compress ``nf`` (which is
    typically sparse).

    *nf(feature_vector)* is the sum of the feature values for
    *feature_vector*.

    This represents the number of features that are active for a
    given labeled text.  This method finds all values of *nf(t)*
    that are attested for at least one token in the given list of
    training tokens; and constructs a dictionary mapping these
    attested values to a continuous range *0...N*.  For example,
    if the only values of *nf()* that were attested were 3, 5, and
    7, then ``_nfmap`` might return the dictionary ``{3:0, 5:1, 7:2}``.

    :return: A map that can be used to compress ``nf`` to a dense
        vector.
    :rtype: dict(int -> int)
    """
    # Map from nf to indices.  This allows us to use smaller arrays.
    nfset = set()
    for tok, _ in train_toks:
        for label in encoding.labels():
            nfset.add(sum(val for (id, val) in encoding.encode(tok, label)))
    return {nf: i for (i, nf) in enumerate(nfset)}


def calculate_deltas(
    train_toks,
    classifier,
    unattested,
    ffreq_empirical,
    nfmap,
    nfarray,
    nftranspose,
    encoding,
):
    r"""
    Calculate the update values for the classifier weights for
    this iteration of IIS.  These update weights are the value of
    ``delta`` that solves the equation::

      ffreq_empirical[i]
             =
      SUM[fs,l] (classifier.prob_classify(fs).prob(l) *
                 feature_vector(fs,l)[i] *
                 exp(delta[i] * nf(feature_vector(fs,l))))

    Where:
        - *(fs,l)* is a (featureset, label) tuple from ``train_toks``
        - *feature_vector(fs,l)* = ``encoding.encode(fs,l)``
        - *nf(vector)* = ``sum([val for (id,val) in vector])``

    This method uses Newton's method to solve this equation for
    *delta[i]*.  In particular, it starts with a guess of
    ``delta[i]`` = 1; and iteratively updates ``delta`` with:

    | delta[i] -= (ffreq_empirical[i] - sum1[i])/(-sum2[i])

    until convergence, where *sum1* and *sum2* are defined as:

    |    sum1[i](delta) = SUM[fs,l] f[i](fs,l,delta)
    |    sum2[i](delta) = SUM[fs,l] (f[i](fs,l,delta).nf(feature_vector(fs,l)))
    |    f[i](fs,l,delta) = (classifier.prob_classify(fs).prob(l) .
    |                        feature_vector(fs,l)[i] .
    |                        exp(delta[i] . nf(feature_vector(fs,l))))

    Note that *sum1* and *sum2* depend on ``delta``; so they need
    to be re-computed each iteration.

    The variables ``nfmap``, ``nfarray``, and ``nftranspose`` are
    used to generate a dense encoding for *nf(ltext)*.  This
    allows ``_deltas`` to calculate *sum1* and *sum2* using
    matrices, which yields a significant performance improvement.

    :param train_toks: The set of training tokens.
    :type train_toks: list(tuple(dict, str))
    :param classifier: The current classifier.
    :type classifier: ClassifierI
    :param ffreq_empirical: An array containing the empirical
        frequency for each feature.  The *i*\ th element of this
        array is the empirical frequency for feature *i*.
    :type ffreq_empirical: sequence of float
    :param unattested: An array that is 1 for features that are
        not attested in the training data; and 0 for features that
        are attested.  In other words, ``unattested[i]==0`` iff
        ``ffreq_empirical[i]==0``.
    :type unattested: sequence of int
    :param nfmap: A map that can be used to compress ``nf`` to a dense
        vector.
    :type nfmap: dict(int -> int)
    :param nfarray: An array that can be used to uncompress ``nf``
        from a dense vector.
    :type nfarray: array(float)
    :param nftranspose: The transpose of ``nfarray``
    :type nftranspose: array(float)
    """
    # These parameters control when we decide that we've
    # converged.  It probably should be possible to set these
    # manually, via keyword arguments to train.
    NEWTON_CONVERGE = 1e-12
    MAX_NEWTON = 300

    deltas = numpy.ones(encoding.length(), "d")

    # Precompute the A matrix:
    # A[nf][id] = sum ( p(fs) * p(label|fs) * f(fs,label) )
    # over all label,fs s.t. num_features[label,fs]=nf
    A = numpy.zeros((len(nfmap), encoding.length()), "d")

    for tok, label in train_toks:
        dist = classifier.prob_classify(tok)

        for label in encoding.labels():
            # Generate the feature vector
            feature_vector = encoding.encode(tok, label)
            # Find the number of active features
            nf = sum(val for (id, val) in feature_vector)
            # Update the A matrix
            for id, val in feature_vector:
                A[nfmap[nf], id] += dist.prob(label) * val
    A /= len(train_toks)

    # Iteratively solve for delta.  Use the following variables:
    #   - nf_delta[x][y] = nfarray[x] * delta[y]
    #   - exp_nf_delta[x][y] = exp(nf[x] * delta[y])
    #   - nf_exp_nf_delta[x][y] = nf[x] * exp(nf[x] * delta[y])
    #   - sum1[i][nf] = sum p(fs)p(label|fs)f[i](label,fs)
    #                       exp(delta[i]nf)
    #   - sum2[i][nf] = sum p(fs)p(label|fs)f[i](label,fs)
    #                       nf exp(delta[i]nf)
    for rangenum in range(MAX_NEWTON):
        nf_delta = numpy.outer(nfarray, deltas)
        exp_nf_delta = 2**nf_delta
        nf_exp_nf_delta = nftranspose * exp_nf_delta
        sum1 = numpy.sum(exp_nf_delta * A, axis=0)
        sum2 = numpy.sum(nf_exp_nf_delta * A, axis=0)

        # Avoid division by zero.
        for fid in unattested:
            sum2[fid] += 1

        # Update the deltas.
        deltas -= (ffreq_empirical - sum1) / -sum2

        # We can stop once we converge.
        n_error = numpy.sum(abs(ffreq_empirical - sum1)) / numpy.sum(abs(deltas))
        if n_error < NEWTON_CONVERGE:
            return deltas

    return deltas


######################################################################
# { Classifier Trainer: megam
######################################################################


# [xx] possible extension: add support for using implicit file format;
# this would need to put requirements on what encoding is used.  But
# we may need this for other maxent classifier trainers that require
# implicit formats anyway.
def train_maxent_classifier_with_megam(
    train_toks, trace=3, encoding=None, labels=None, gaussian_prior_sigma=0, **kwargs
):
    """
    Train a new ``ConditionalExponentialClassifier``, using the given
    training samples, using the external ``megam`` library.  This
    ``ConditionalExponentialClassifier`` will encode the model that
    maximizes entropy from all the models that are empirically
    consistent with ``train_toks``.

    :see: ``train_maxent_classifier()`` for parameter descriptions.
    :see: ``nltk.classify.megam``
    """

    explicit = True
    bernoulli = True
    if "explicit" in kwargs:
        explicit = kwargs["explicit"]
    if "bernoulli" in kwargs:
        bernoulli = kwargs["bernoulli"]

    # Construct an encoding from the training data.
    if encoding is None:
        # Count cutoff can also be controlled by megam with the -minfc
        # option. Not sure where the best place for it is.
        count_cutoff = kwargs.get("count_cutoff", 0)
        encoding = BinaryMaxentFeatureEncoding.train(
            train_toks, count_cutoff, labels=labels, alwayson_features=True
        )
    elif labels is not None:
        raise ValueError("Specify encoding or labels, not both")

    # Write a training file for megam.
    try:
        fd, trainfile_name = tempfile.mkstemp(prefix="nltk-")
        with open(trainfile_name, "w") as trainfile:
            write_megam_file(
                train_toks, encoding, trainfile, explicit=explicit, bernoulli=bernoulli
            )
        os.close(fd)
    except (OSError, ValueError) as e:
        raise ValueError("Error while creating megam training file: %s" % e) from e

    # Run megam on the training file.
    options = []
    options += ["-nobias", "-repeat", "10"]
    if explicit:
        options += ["-explicit"]
    if not bernoulli:
        options += ["-fvals"]
    if gaussian_prior_sigma:
        # Lambda is just the precision of the Gaussian prior, i.e. it's the
        # inverse variance, so the parameter conversion is 1.0/sigma**2.
        # See https://users.umiacs.umd.edu/~hal/docs/daume04cg-bfgs.pdf
        inv_variance = 1.0 / gaussian_prior_sigma**2
    else:
        inv_variance = 0
    options += ["-lambda", "%.2f" % inv_variance, "-tune"]
    if trace < 3:
        options += ["-quiet"]
    if "max_iter" in kwargs:
        options += ["-maxi", "%s" % kwargs["max_iter"]]
    if "ll_delta" in kwargs:
        # [xx] this is actually a perplexity delta, not a log
        # likelihood delta
        options += ["-dpp", "%s" % abs(kwargs["ll_delta"])]
    if hasattr(encoding, "cost"):
        options += ["-multilabel"]  # each possible la
    options += ["multiclass", trainfile_name]
    stdout = call_megam(options)
    # print('./megam_i686.opt ', ' '.join(options))
    # Delete the training file
    try:
        os.remove(trainfile_name)
    except OSError as e:
        print(f"Warning: unable to delete {trainfile_name}: {e}")

    # Parse the generated weight vector.
    weights = parse_megam_weights(stdout, encoding.length(), explicit)

    # Convert from base-e to base-2 weights.
    weights *= numpy.log2(numpy.e)

    # Build the classifier
    return MaxentClassifier(encoding, weights)


######################################################################
# { Classifier Trainer: tadm
######################################################################


class TadmMaxentClassifier(MaxentClassifier):
    @classmethod
    def train(cls, train_toks, **kwargs):
        algorithm = kwargs.get("algorithm", "tao_lmvm")
        trace = kwargs.get("trace", 3)
        encoding = kwargs.get("encoding", None)
        labels = kwargs.get("labels", None)
        sigma = kwargs.get("gaussian_prior_sigma", 0)
        count_cutoff = kwargs.get("count_cutoff", 0)
        max_iter = kwargs.get("max_iter")
        ll_delta = kwargs.get("min_lldelta")

        # Construct an encoding from the training data.
        if not encoding:
            encoding = TadmEventMaxentFeatureEncoding.train(
                train_toks, count_cutoff, labels=labels
            )

        trainfile_fd, trainfile_name = tempfile.mkstemp(
            prefix="nltk-tadm-events-", suffix=".gz"
        )
        weightfile_fd, weightfile_name = tempfile.mkstemp(prefix="nltk-tadm-weights-")

        trainfile = gzip_open_unicode(trainfile_name, "w")
        write_tadm_file(train_toks, encoding, trainfile)
        trainfile.close()

        options = []
        options.extend(["-monitor"])
        options.extend(["-method", algorithm])
        if sigma:
            options.extend(["-l2", "%.6f" % sigma**2])
        if max_iter:
            options.extend(["-max_it", "%d" % max_iter])
        if ll_delta:
            options.extend(["-fatol", "%.6f" % abs(ll_delta)])
        options.extend(["-events_in", trainfile_name])
        options.extend(["-params_out", weightfile_name])
        if trace < 3:
            options.extend(["2>&1"])
        else:
            options.extend(["-summary"])

        call_tadm(options)

        with open(weightfile_name) as weightfile:
            weights = parse_tadm_weights(weightfile)

        os.remove(trainfile_name)
        os.remove(weightfile_name)

        # Convert from base-e to base-2 weights.
        weights *= numpy.log2(numpy.e)

        # Build the classifier
        return cls(encoding, weights)


######################################################################
# Load/Save Classifier Parameters as Tab-files
######################################################################


def load_maxent_params(tab_dir):
    import numpy

    from nltk.tabdata import MaxentDecoder

    mdec = MaxentDecoder()

    with open(f"{tab_dir}/weights.txt") as f:
        wgt = numpy.array(list(map(numpy.float64, mdec.txt2list(f))))

    with open(f"{tab_dir}/mapping.tab") as f:
        mpg = mdec.tupkey2dict(f)

    with open(f"{tab_dir}/labels.txt") as f:
        lab = mdec.txt2list(f)

    with open(f"{tab_dir}/alwayson.tab") as f:
        aon = mdec.tab2ivdict(f)

    return wgt, mpg, lab, aon


def save_maxent_params(wgt, mpg, lab, aon, tab_dir="/tmp"):

    from os import mkdir
    from os.path import isdir

    from nltk.tabdata import MaxentEncoder

    menc = MaxentEncoder()
    if not isdir(tab_dir):
        mkdir(tab_dir)

    print(f"Saving Maxent parameters in {tab_dir}")

    with open(f"{tab_dir}/weights.txt", "w") as f:
        f.write(f"{menc.list2txt(map(repr, wgt.tolist()))}")
    with open(f"{tab_dir}/mapping.tab", "w") as f:
        f.write(f"{menc.tupdict2tab(mpg)}")
    with open(f"{tab_dir}/labels.txt", "w") as f:
        f.write(f"{menc.list2txt(lab)}")
    with open(f"{tab_dir}/alwayson.tab", "w") as f:
        f.write(f"{menc.ivdict2tab(aon)}")


def maxent_pos_tagger():
    from nltk.data import find
    from nltk.tag.sequential import ClassifierBasedPOSTagger

    tab_dir = find("taggers/maxent_treebank_pos_tagger_tab/english")
    wgt, mpg, lab, aon = load_maxent_params(tab_dir)
    mc = MaxentClassifier(
        BinaryMaxentFeatureEncoding(lab, mpg, alwayson_features=aon), wgt
    )
    return ClassifierBasedPOSTagger(classifier=mc)


######################################################################
# { Demo
######################################################################
def demo():
    from nltk.classify.util import names_demo

    classifier = names_demo(MaxentClassifier.train)


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\numpy\f2py\rules.py ===
"""

Rules for building C/API module with f2py2e.

Here is a skeleton of a new wrapper function (13Dec2001):

wrapper_function(args)
  declarations
  get_python_arguments, say, `a' and `b'

  get_a_from_python
  if (successful) {

    get_b_from_python
    if (successful) {

      callfortran
      if (successful) {

        put_a_to_python
        if (successful) {

          put_b_to_python
          if (successful) {

            buildvalue = ...

          }

        }

      }

    }
    cleanup_b

  }
  cleanup_a

  return buildvalue

Copyright 1999 -- 2011 Pearu Peterson all rights reserved.
Copyright 2011 -- present NumPy Developers.
Permission to use, modify, and distribute this software is given under the
terms of the NumPy License.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
"""
import copy
import os
import sys
import time
from pathlib import Path

# __version__.version is now the same as the NumPy version
from . import (
    __version__,
    capi_maps,
    cfuncs,
    common_rules,
    f90mod_rules,
    func2subr,
    use_rules,
)
from .auxfuncs import (
    applyrules,
    debugcapi,
    dictappend,
    errmess,
    gentitle,
    getargs2,
    hascallstatement,
    hasexternals,
    hasinitvalue,
    hasnote,
    hasresultnote,
    isarray,
    isarrayofstrings,
    isattr_value,
    ischaracter,
    ischaracter_or_characterarray,
    ischaracterarray,
    iscomplex,
    iscomplexarray,
    iscomplexfunction,
    iscomplexfunction_warn,
    isdummyroutine,
    isexternal,
    isfunction,
    isfunction_wrap,
    isint1,
    isint1array,
    isintent_aux,
    isintent_c,
    isintent_callback,
    isintent_copy,
    isintent_hide,
    isintent_inout,
    isintent_nothide,
    isintent_out,
    isintent_overwrite,
    islogical,
    islong_complex,
    islong_double,
    islong_doublefunction,
    islong_long,
    islong_longfunction,
    ismoduleroutine,
    isoptional,
    isrequired,
    isscalar,
    issigned_long_longarray,
    isstring,
    isstringarray,
    isstringfunction,
    issubroutine,
    issubroutine_wrap,
    isthreadsafe,
    isunsigned,
    isunsigned_char,
    isunsigned_chararray,
    isunsigned_long_long,
    isunsigned_long_longarray,
    isunsigned_short,
    isunsigned_shortarray,
    l_and,
    l_not,
    l_or,
    outmess,
    replace,
    requiresf90wrapper,
    stripcomma,
)

f2py_version = __version__.version
numpy_version = __version__.version

options = {}
sepdict = {}
# for k in ['need_cfuncs']: sepdict[k]=','
for k in ['decl',
          'frompyobj',
          'cleanupfrompyobj',
          'topyarr', 'method',
          'pyobjfrom', 'closepyobjfrom',
          'freemem',
          'userincludes',
          'includes0', 'includes', 'typedefs', 'typedefs_generated',
          'cppmacros', 'cfuncs', 'callbacks',
          'latexdoc',
          'restdoc',
          'routine_defs', 'externroutines',
          'initf2pywraphooks',
          'commonhooks', 'initcommonhooks',
          'f90modhooks', 'initf90modhooks']:
    sepdict[k] = '\n'

#################### Rules for C/API module #################

generationtime = int(os.environ.get('SOURCE_DATE_EPOCH', time.time()))
module_rules = {
    'modulebody': """\
/* File: #modulename#module.c
 * This file is auto-generated with f2py (version:#f2py_version#).
 * f2py is a Fortran to Python Interface Generator (FPIG), Second Edition,
 * written by Pearu Peterson <pearu@cens.ioc.ee>.
 * Generation date: """ + time.asctime(time.gmtime(generationtime)) + """
 * Do not edit this file directly unless you know what you are doing!!!
 */

#ifdef __cplusplus
extern \"C\" {
#endif

#ifndef PY_SSIZE_T_CLEAN
#define PY_SSIZE_T_CLEAN
#endif /* PY_SSIZE_T_CLEAN */

/* Unconditionally included */
#include <Python.h>
#include <numpy/npy_os.h>

""" + gentitle("See f2py2e/cfuncs.py: includes") + """
#includes#
#includes0#

""" + gentitle("See f2py2e/rules.py: mod_rules['modulebody']") + """
static PyObject *#modulename#_error;
static PyObject *#modulename#_module;

""" + gentitle("See f2py2e/cfuncs.py: typedefs") + """
#typedefs#

""" + gentitle("See f2py2e/cfuncs.py: typedefs_generated") + """
#typedefs_generated#

""" + gentitle("See f2py2e/cfuncs.py: cppmacros") + """
#cppmacros#

""" + gentitle("See f2py2e/cfuncs.py: cfuncs") + """
#cfuncs#

""" + gentitle("See f2py2e/cfuncs.py: userincludes") + """
#userincludes#

""" + gentitle("See f2py2e/capi_rules.py: usercode") + """
#usercode#

/* See f2py2e/rules.py */
#externroutines#

""" + gentitle("See f2py2e/capi_rules.py: usercode1") + """
#usercode1#

""" + gentitle("See f2py2e/cb_rules.py: buildcallback") + """
#callbacks#

""" + gentitle("See f2py2e/rules.py: buildapi") + """
#body#

""" + gentitle("See f2py2e/f90mod_rules.py: buildhooks") + """
#f90modhooks#

""" + gentitle("See f2py2e/rules.py: module_rules['modulebody']") + """

""" + gentitle("See f2py2e/common_rules.py: buildhooks") + """
#commonhooks#

""" + gentitle("See f2py2e/rules.py") + """

static FortranDataDef f2py_routine_defs[] = {
#routine_defs#
    {NULL}
};

static PyMethodDef f2py_module_methods[] = {
#pymethoddef#
    {NULL,NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "#modulename#",
    NULL,
    -1,
    f2py_module_methods,
    NULL,
    NULL,
    NULL,
    NULL
};

PyMODINIT_FUNC PyInit_#modulename#(void) {
    int i;
    PyObject *m,*d, *s, *tmp;
    m = #modulename#_module = PyModule_Create(&moduledef);
    Py_SET_TYPE(&PyFortran_Type, &PyType_Type);
    import_array();
    if (PyErr_Occurred())
        {PyErr_SetString(PyExc_ImportError, \"can't initialize module #modulename# (failed to import numpy)\"); return m;}
    d = PyModule_GetDict(m);
    s = PyUnicode_FromString(\"#f2py_version#\");
    PyDict_SetItemString(d, \"__version__\", s);
    Py_DECREF(s);
    s = PyUnicode_FromString(
        \"This module '#modulename#' is auto-generated with f2py (version:#f2py_version#).\\nFunctions:\\n\"\n#docs#\".\");
    PyDict_SetItemString(d, \"__doc__\", s);
    Py_DECREF(s);
    s = PyUnicode_FromString(\"""" + numpy_version + """\");
    PyDict_SetItemString(d, \"__f2py_numpy_version__\", s);
    Py_DECREF(s);
    #modulename#_error = PyErr_NewException (\"#modulename#.error\", NULL, NULL);
    /*
     * Store the error object inside the dict, so that it could get deallocated.
     * (in practice, this is a module, so it likely will not and cannot.)
     */
    PyDict_SetItemString(d, \"_#modulename#_error\", #modulename#_error);
    Py_DECREF(#modulename#_error);
    for(i=0;f2py_routine_defs[i].name!=NULL;i++) {
        tmp = PyFortranObject_NewAsAttr(&f2py_routine_defs[i]);
        PyDict_SetItemString(d, f2py_routine_defs[i].name, tmp);
        Py_DECREF(tmp);
    }
#initf2pywraphooks#
#initf90modhooks#
#initcommonhooks#
#interface_usercode#

#if Py_GIL_DISABLED
    // signal whether this module supports running with the GIL disabled
    PyUnstable_Module_SetGIL(m , #gil_used#);
#endif

#ifdef F2PY_REPORT_ATEXIT
    if (! PyErr_Occurred())
        on_exit(f2py_report_on_exit,(void*)\"#modulename#\");
#endif

    if (PyType_Ready(&PyFortran_Type) < 0) {
        return NULL;
    }

    return m;
}
#ifdef __cplusplus
}
#endif
""",
    'separatorsfor': {'latexdoc': '\n\n',
                      'restdoc': '\n\n'},
    'latexdoc': ['\\section{Module \\texttt{#texmodulename#}}\n',
                 '#modnote#\n',
                 '#latexdoc#'],
    'restdoc': ['Module #modulename#\n' + '=' * 80,
                '\n#restdoc#']
}

defmod_rules = [
    {'body': '/*eof body*/',
     'method': '/*eof method*/',
     'externroutines': '/*eof externroutines*/',
     'routine_defs': '/*eof routine_defs*/',
     'initf90modhooks': '/*eof initf90modhooks*/',
     'initf2pywraphooks': '/*eof initf2pywraphooks*/',
     'initcommonhooks': '/*eof initcommonhooks*/',
     'latexdoc': '',
     'restdoc': '',
     'modnote': {hasnote: '#note#', l_not(hasnote): ''},
     }
]

routine_rules = {
    'separatorsfor': sepdict,
    'body': """
#begintitle#
static char doc_#apiname#[] = \"\\\n#docreturn##name#(#docsignatureshort#)\\n\\nWrapper for ``#name#``.\\\n\\n#docstrsigns#\";
/* #declfortranroutine# */
static PyObject *#apiname#(const PyObject *capi_self,
                           PyObject *capi_args,
                           PyObject *capi_keywds,
                           #functype# (*f2py_func)(#callprotoargument#)) {
    PyObject * volatile capi_buildvalue = NULL;
    volatile int f2py_success = 1;
#decl#
    static char *capi_kwlist[] = {#kwlist##kwlistopt##kwlistxa#NULL};
#usercode#
#routdebugenter#
#ifdef F2PY_REPORT_ATEXIT
f2py_start_clock();
#endif
    if (!PyArg_ParseTupleAndKeywords(capi_args,capi_keywds,\\
        \"#argformat#|#keyformat##xaformat#:#pyname#\",\\
        capi_kwlist#args_capi##keys_capi##keys_xa#))\n        return NULL;
#frompyobj#
/*end of frompyobj*/
#ifdef F2PY_REPORT_ATEXIT
f2py_start_call_clock();
#endif
#callfortranroutine#
if (PyErr_Occurred())
  f2py_success = 0;
#ifdef F2PY_REPORT_ATEXIT
f2py_stop_call_clock();
#endif
/*end of callfortranroutine*/
        if (f2py_success) {
#pyobjfrom#
/*end of pyobjfrom*/
        CFUNCSMESS(\"Building return value.\\n\");
        capi_buildvalue = Py_BuildValue(\"#returnformat#\"#return#);
/*closepyobjfrom*/
#closepyobjfrom#
        } /*if (f2py_success) after callfortranroutine*/
/*cleanupfrompyobj*/
#cleanupfrompyobj#
    if (capi_buildvalue == NULL) {
#routdebugfailure#
    } else {
#routdebugleave#
    }
    CFUNCSMESS(\"Freeing memory.\\n\");
#freemem#
#ifdef F2PY_REPORT_ATEXIT
f2py_stop_clock();
#endif
    return capi_buildvalue;
}
#endtitle#
""",
    'routine_defs': '#routine_def#',
    'initf2pywraphooks': '#initf2pywraphook#',
    'externroutines': '#declfortranroutine#',
    'doc': '#docreturn##name#(#docsignature#)',
    'docshort': '#docreturn##name#(#docsignatureshort#)',
    'docs': '"    #docreturn##name#(#docsignature#)\\n"\n',
    'need': ['arrayobject.h', 'CFUNCSMESS', 'MINMAX'],
    'cppmacros': {debugcapi: '#define DEBUGCFUNCS'},
    'latexdoc': ['\\subsection{Wrapper function \\texttt{#texname#}}\n',
                 """
\\noindent{{}\\verb@#docreturn##name#@{}}\\texttt{(#latexdocsignatureshort#)}
#routnote#

#latexdocstrsigns#
"""],
    'restdoc': ['Wrapped function ``#name#``\n' + '-' * 80,

                ]
}

################## Rules for C/API function ##############

rout_rules = [
    {  # Init
        'separatorsfor': {'callfortranroutine': '\n', 'routdebugenter': '\n', 'decl': '\n',
                          'routdebugleave': '\n', 'routdebugfailure': '\n',
                          'setjmpbuf': ' || ',
                          'docstrreq': '\n', 'docstropt': '\n', 'docstrout': '\n',
                          'docstrcbs': '\n', 'docstrsigns': '\\n"\n"',
                          'latexdocstrsigns': '\n',
                          'latexdocstrreq': '\n', 'latexdocstropt': '\n',
                          'latexdocstrout': '\n', 'latexdocstrcbs': '\n',
                          },
        'kwlist': '', 'kwlistopt': '', 'callfortran': '', 'callfortranappend': '',
        'docsign': '', 'docsignopt': '', 'decl': '/*decl*/',
        'freemem': '/*freemem*/',
        'docsignshort': '', 'docsignoptshort': '',
        'docstrsigns': '', 'latexdocstrsigns': '',
        'docstrreq': '\\nParameters\\n----------',
        'docstropt': '\\nOther Parameters\\n----------------',
        'docstrout': '\\nReturns\\n-------',
        'docstrcbs': '\\nNotes\\n-----\\nCall-back functions::\\n',
        'latexdocstrreq': '\\noindent Required arguments:',
        'latexdocstropt': '\\noindent Optional arguments:',
        'latexdocstrout': '\\noindent Return objects:',
        'latexdocstrcbs': '\\noindent Call-back functions:',
        'args_capi': '', 'keys_capi': '', 'functype': '',
        'frompyobj': '/*frompyobj*/',
        # this list will be reversed
        'cleanupfrompyobj': ['/*end of cleanupfrompyobj*/'],
        'pyobjfrom': '/*pyobjfrom*/',
        # this list will be reversed
        'closepyobjfrom': ['/*end of closepyobjfrom*/'],
        'topyarr': '/*topyarr*/', 'routdebugleave': '/*routdebugleave*/',
        'routdebugenter': '/*routdebugenter*/',
        'routdebugfailure': '/*routdebugfailure*/',
        'callfortranroutine': '/*callfortranroutine*/',
        'argformat': '', 'keyformat': '', 'need_cfuncs': '',
        'docreturn': '', 'return': '', 'returnformat': '', 'rformat': '',
        'kwlistxa': '', 'keys_xa': '', 'xaformat': '', 'docsignxa': '', 'docsignxashort': '',
        'initf2pywraphook': '',
        'routnote': {hasnote: '--- #note#', l_not(hasnote): ''},
    }, {
        'apiname': 'f2py_rout_#modulename#_#name#',
        'pyname': '#modulename#.#name#',
        'decl': '',
        '_check': l_not(ismoduleroutine)
    }, {
        'apiname': 'f2py_rout_#modulename#_#f90modulename#_#name#',
        'pyname': '#modulename#.#f90modulename#.#name#',
        'decl': '',
        '_check': ismoduleroutine
    }, {  # Subroutine
        'functype': 'void',
        'declfortranroutine': {l_and(l_not(l_or(ismoduleroutine, isintent_c)), l_not(isdummyroutine)): 'extern void #F_FUNC#(#fortranname#,#FORTRANNAME#)(#callprotoargument#);',
                               l_and(l_not(ismoduleroutine), isintent_c, l_not(isdummyroutine)): 'extern void #fortranname#(#callprotoargument#);',
                               ismoduleroutine: '',
                               isdummyroutine: ''
                               },
        'routine_def': {
            l_not(l_or(ismoduleroutine, isintent_c, isdummyroutine)):
            '    {\"#name#\",-1,{{-1}},0,0,(char *)'
            '  #F_FUNC#(#fortranname#,#FORTRANNAME#),'
            '  (f2py_init_func)#apiname#,doc_#apiname#},',
            l_and(l_not(ismoduleroutine), isintent_c, l_not(isdummyroutine)):
            '    {\"#name#\",-1,{{-1}},0,0,(char *)#fortranname#,'
            '  (f2py_init_func)#apiname#,doc_#apiname#},',
            l_and(l_not(ismoduleroutine), isdummyroutine):
            '    {\"#name#\",-1,{{-1}},0,0,NULL,'
            '  (f2py_init_func)#apiname#,doc_#apiname#},',
        },
        'need': {l_and(l_not(l_or(ismoduleroutine, isintent_c)), l_not(isdummyroutine)): 'F_FUNC'},
        'callfortranroutine': [
            {debugcapi: [
                """    fprintf(stderr,\"debug-capi:Fortran subroutine `#fortranname#(#callfortran#)\'\\n\");"""]},
            {hasexternals: """\
        if (#setjmpbuf#) {
            f2py_success = 0;
        } else {"""},
            {isthreadsafe: '            Py_BEGIN_ALLOW_THREADS'},
            {hascallstatement: '''                #callstatement#;
                /*(*f2py_func)(#callfortran#);*/'''},
            {l_not(l_or(hascallstatement, isdummyroutine))
                   : '                (*f2py_func)(#callfortran#);'},
            {isthreadsafe: '            Py_END_ALLOW_THREADS'},
            {hasexternals: """        }"""}
        ],
        '_check': l_and(issubroutine, l_not(issubroutine_wrap)),
    }, {  # Wrapped function
        'functype': 'void',
        'declfortranroutine': {l_not(l_or(ismoduleroutine, isdummyroutine)): 'extern void #F_WRAPPEDFUNC#(#name_lower#,#NAME#)(#callprotoargument#);',
                               isdummyroutine: '',
                               },

        'routine_def': {
            l_not(l_or(ismoduleroutine, isdummyroutine)):
            '    {\"#name#\",-1,{{-1}},0,0,(char *)'
            '  #F_WRAPPEDFUNC#(#name_lower#,#NAME#),'
            '  (f2py_init_func)#apiname#,doc_#apiname#},',
            isdummyroutine:
            '    {\"#name#\",-1,{{-1}},0,0,NULL,'
            '  (f2py_init_func)#apiname#,doc_#apiname#},',
        },
        'initf2pywraphook': {l_not(l_or(ismoduleroutine, isdummyroutine)): '''
    {
      extern #ctype# #F_FUNC#(#name_lower#,#NAME#)(void);
      PyObject* o = PyDict_GetItemString(d,"#name#");
      tmp = F2PyCapsule_FromVoidPtr((void*)#F_WRAPPEDFUNC#(#name_lower#,#NAME#),NULL);
      PyObject_SetAttrString(o,"_cpointer", tmp);
      Py_DECREF(tmp);
      s = PyUnicode_FromString("#name#");
      PyObject_SetAttrString(o,"__name__", s);
      Py_DECREF(s);
    }
    '''},
        'need': {l_not(l_or(ismoduleroutine, isdummyroutine)): ['F_WRAPPEDFUNC', 'F_FUNC']},
        'callfortranroutine': [
            {debugcapi: [
                """    fprintf(stderr,\"debug-capi:Fortran subroutine `f2pywrap#name_lower#(#callfortran#)\'\\n\");"""]},
            {hasexternals: """\
    if (#setjmpbuf#) {
        f2py_success = 0;
    } else {"""},
            {isthreadsafe: '    Py_BEGIN_ALLOW_THREADS'},
            {l_not(l_or(hascallstatement, isdummyroutine))
                   : '    (*f2py_func)(#callfortran#);'},
            {hascallstatement:
                '    #callstatement#;\n    /*(*f2py_func)(#callfortran#);*/'},
            {isthreadsafe: '    Py_END_ALLOW_THREADS'},
            {hasexternals: '    }'}
        ],
        '_check': isfunction_wrap,
    }, {  # Wrapped subroutine
        'functype': 'void',
        'declfortranroutine': {l_not(l_or(ismoduleroutine, isdummyroutine)): 'extern void #F_WRAPPEDFUNC#(#name_lower#,#NAME#)(#callprotoargument#);',
                               isdummyroutine: '',
                               },

        'routine_def': {
            l_not(l_or(ismoduleroutine, isdummyroutine)):
            '    {\"#name#\",-1,{{-1}},0,0,(char *)'
            '  #F_WRAPPEDFUNC#(#name_lower#,#NAME#),'
            '  (f2py_init_func)#apiname#,doc_#apiname#},',
            isdummyroutine:
            '    {\"#name#\",-1,{{-1}},0,0,NULL,'
            '  (f2py_init_func)#apiname#,doc_#apiname#},',
        },
        'initf2pywraphook': {l_not(l_or(ismoduleroutine, isdummyroutine)): '''
    {
      extern void #F_FUNC#(#name_lower#,#NAME#)(void);
      PyObject* o = PyDict_GetItemString(d,"#name#");
      tmp = F2PyCapsule_FromVoidPtr((void*)#F_FUNC#(#name_lower#,#NAME#),NULL);
      PyObject_SetAttrString(o,"_cpointer", tmp);
      Py_DECREF(tmp);
      s = PyUnicode_FromString("#name#");
      PyObject_SetAttrString(o,"__name__", s);
      Py_DECREF(s);
    }
    '''},
        'need': {l_not(l_or(ismoduleroutine, isdummyroutine)): ['F_WRAPPEDFUNC', 'F_FUNC']},
        'callfortranroutine': [
            {debugcapi: [
                """    fprintf(stderr,\"debug-capi:Fortran subroutine `f2pywrap#name_lower#(#callfortran#)\'\\n\");"""]},
            {hasexternals: """\
    if (#setjmpbuf#) {
        f2py_success = 0;
    } else {"""},
            {isthreadsafe: '    Py_BEGIN_ALLOW_THREADS'},
            {l_not(l_or(hascallstatement, isdummyroutine))
                   : '    (*f2py_func)(#callfortran#);'},
            {hascallstatement:
                '    #callstatement#;\n    /*(*f2py_func)(#callfortran#);*/'},
            {isthreadsafe: '    Py_END_ALLOW_THREADS'},
            {hasexternals: '    }'}
        ],
        '_check': issubroutine_wrap,
    }, {  # Function
        'functype': '#ctype#',
        'docreturn': {l_not(isintent_hide): '#rname#,'},
        'docstrout': '#pydocsignout#',
        'latexdocstrout': ['\\item[]{{}\\verb@#pydocsignout#@{}}',
                           {hasresultnote: '--- #resultnote#'}],
        'callfortranroutine': [{l_and(debugcapi, isstringfunction): """\
#ifdef USESCOMPAQFORTRAN
    fprintf(stderr,\"debug-capi:Fortran function #ctype# #fortranname#(#callcompaqfortran#)\\n\");
#else
    fprintf(stderr,\"debug-capi:Fortran function #ctype# #fortranname#(#callfortran#)\\n\");
#endif
"""},
                               {l_and(debugcapi, l_not(isstringfunction)): """\
    fprintf(stderr,\"debug-capi:Fortran function #ctype# #fortranname#(#callfortran#)\\n\");
"""}
                               ],
        '_check': l_and(isfunction, l_not(isfunction_wrap))
    }, {  # Scalar function
        'declfortranroutine': {l_and(l_not(l_or(ismoduleroutine, isintent_c)), l_not(isdummyroutine)): 'extern #ctype# #F_FUNC#(#fortranname#,#FORTRANNAME#)(#callprotoargument#);',
                               l_and(l_not(ismoduleroutine), isintent_c, l_not(isdummyroutine)): 'extern #ctype# #fortranname#(#callprotoargument#);',
                               isdummyroutine: ''
                               },
        'routine_def': {
            l_and(l_not(l_or(ismoduleroutine, isintent_c)),
                  l_not(isdummyroutine)):
            ('    {\"#name#\",-1,{{-1}},0,0,(char *)'
             '  #F_FUNC#(#fortranname#,#FORTRANNAME#),'
             '  (f2py_init_func)#apiname#,doc_#apiname#},'),
            l_and(l_not(ismoduleroutine), isintent_c, l_not(isdummyroutine)):
            ('    {\"#name#\",-1,{{-1}},0,0,(char *)#fortranname#,'
             '  (f2py_init_func)#apiname#,doc_#apiname#},'),
            isdummyroutine:
            '    {\"#name#\",-1,{{-1}},0,0,NULL,'
            '(f2py_init_func)#apiname#,doc_#apiname#},',
        },
        'decl': [{iscomplexfunction_warn: '    #ctype# #name#_return_value={0,0};',
                  l_not(iscomplexfunction): '    #ctype# #name#_return_value=0;'},
                 {iscomplexfunction:
                  '    PyObject *#name#_return_value_capi = Py_None;'}
                 ],
        'callfortranroutine': [
            {hasexternals: """\
    if (#setjmpbuf#) {
        f2py_success = 0;
    } else {"""},
            {isthreadsafe: '    Py_BEGIN_ALLOW_THREADS'},
            {hascallstatement: '''    #callstatement#;
/*    #name#_return_value = (*f2py_func)(#callfortran#);*/
'''},
            {l_not(l_or(hascallstatement, isdummyroutine))
                   : '    #name#_return_value = (*f2py_func)(#callfortran#);'},
            {isthreadsafe: '    Py_END_ALLOW_THREADS'},
            {hasexternals: '    }'},
            {l_and(debugcapi, iscomplexfunction)
                   : '    fprintf(stderr,"#routdebugshowvalue#\\n",#name#_return_value.r,#name#_return_value.i);'},
            {l_and(debugcapi, l_not(iscomplexfunction)): '    fprintf(stderr,"#routdebugshowvalue#\\n",#name#_return_value);'}],
        'pyobjfrom': {iscomplexfunction: '    #name#_return_value_capi = pyobj_from_#ctype#1(#name#_return_value);'},
        'need': [{l_not(isdummyroutine): 'F_FUNC'},
                 {iscomplexfunction: 'pyobj_from_#ctype#1'},
                 {islong_longfunction: 'long_long'},
                 {islong_doublefunction: 'long_double'}],
        'returnformat': {l_not(isintent_hide): '#rformat#'},
        'return': {iscomplexfunction: ',#name#_return_value_capi',
                   l_not(l_or(iscomplexfunction, isintent_hide)): ',#name#_return_value'},
        '_check': l_and(isfunction, l_not(isstringfunction), l_not(isfunction_wrap))
    }, {  # String function # in use for --no-wrap
        'declfortranroutine': 'extern void #F_FUNC#(#fortranname#,#FORTRANNAME#)(#callprotoargument#);',
        'routine_def': {l_not(l_or(ismoduleroutine, isintent_c)):
                        '    {\"#name#\",-1,{{-1}},0,0,(char *)#F_FUNC#(#fortranname#,#FORTRANNAME#),(f2py_init_func)#apiname#,doc_#apiname#},',
                        l_and(l_not(ismoduleroutine), isintent_c):
                        '    {\"#name#\",-1,{{-1}},0,0,(char *)#fortranname#,(f2py_init_func)#apiname#,doc_#apiname#},'
                        },
        'decl': ['    #ctype# #name#_return_value = NULL;',
                 '    int #name#_return_value_len = 0;'],
        'callfortran': '#name#_return_value,#name#_return_value_len,',
        'callfortranroutine': ['    #name#_return_value_len = #rlength#;',
                               '    if ((#name#_return_value = (string)malloc(#name#_return_value_len+1) == NULL) {',
                               '        PyErr_SetString(PyExc_MemoryError, \"out of memory\");',
                               '        f2py_success = 0;',
                               '    } else {',
                               "        (#name#_return_value)[#name#_return_value_len] = '\\0';",
                               '    }',
                               '    if (f2py_success) {',
                               {hasexternals: """\
        if (#setjmpbuf#) {
            f2py_success = 0;
        } else {"""},
                               {isthreadsafe: '        Py_BEGIN_ALLOW_THREADS'},
                              """\
#ifdef USESCOMPAQFORTRAN
        (*f2py_func)(#callcompaqfortran#);
#else
        (*f2py_func)(#callfortran#);
#endif
""",
                               {isthreadsafe: '        Py_END_ALLOW_THREADS'},
                               {hasexternals: '        }'},
                               {debugcapi:
                                  '        fprintf(stderr,"#routdebugshowvalue#\\n",#name#_return_value_len,#name#_return_value);'},
                               '    } /* if (f2py_success) after (string)malloc */',
                              ],
        'returnformat': '#rformat#',
        'return': ',#name#_return_value',
        'freemem': '    STRINGFREE(#name#_return_value);',
        'need': ['F_FUNC', '#ctype#', 'STRINGFREE'],
        '_check': l_and(isstringfunction, l_not(isfunction_wrap))  # ???obsolete
    },
    {  # Debugging
        'routdebugenter': '    fprintf(stderr,"debug-capi:Python C/API function #modulename#.#name#(#docsignature#)\\n");',
        'routdebugleave': '    fprintf(stderr,"debug-capi:Python C/API function #modulename#.#name#: successful.\\n");',
        'routdebugfailure': '    fprintf(stderr,"debug-capi:Python C/API function #modulename#.#name#: failure.\\n");',
        '_check': debugcapi
    }
]

################ Rules for arguments ##################

typedef_need_dict = {islong_long: 'long_long',
                     islong_double: 'long_double',
                     islong_complex: 'complex_long_double',
                     isunsigned_char: 'unsigned_char',
                     isunsigned_short: 'unsigned_short',
                     isunsigned: 'unsigned',
                     isunsigned_long_long: 'unsigned_long_long',
                     isunsigned_chararray: 'unsigned_char',
                     isunsigned_shortarray: 'unsigned_short',
                     isunsigned_long_longarray: 'unsigned_long_long',
                     issigned_long_longarray: 'long_long',
                     isint1: 'signed_char',
                     ischaracter_or_characterarray: 'character',
                     }

aux_rules = [
    {
        'separatorsfor': sepdict
    },
    {  # Common
        'frompyobj': ['    /* Processing auxiliary variable #varname# */',
                      {debugcapi: '    fprintf(stderr,"#vardebuginfo#\\n");'}, ],
        'cleanupfrompyobj': '    /* End of cleaning variable #varname# */',
        'need': typedef_need_dict,
    },
    # Scalars (not complex)
    {  # Common
        'decl': '    #ctype# #varname# = 0;',
        'need': {hasinitvalue: 'math.h'},
        'frompyobj': {hasinitvalue: '    #varname# = #init#;'},
        '_check': l_and(isscalar, l_not(iscomplex)),
    },
    {
        'return': ',#varname#',
        'docstrout': '#pydocsignout#',
        'docreturn': '#outvarname#,',
        'returnformat': '#varrformat#',
        '_check': l_and(isscalar, l_not(iscomplex), isintent_out),
    },
    # Complex scalars
    {  # Common
        'decl': '    #ctype# #varname#;',
        'frompyobj': {hasinitvalue: '    #varname#.r = #init.r#, #varname#.i = #init.i#;'},
        '_check': iscomplex
    },
    # String
    {  # Common
        'decl': ['    #ctype# #varname# = NULL;',
                 '    int slen(#varname#);',
                 ],
        'need': ['len..'],
        '_check': isstring
    },
    # Array
    {  # Common
        'decl': ['    #ctype# *#varname# = NULL;',
                 '    npy_intp #varname#_Dims[#rank#] = {#rank*[-1]#};',
                 '    const int #varname#_Rank = #rank#;',
                 ],
        'need': ['len..', {hasinitvalue: 'forcomb'}, {hasinitvalue: 'CFUNCSMESS'}],
        '_check': isarray
    },
    # Scalararray
    {  # Common
        '_check': l_and(isarray, l_not(iscomplexarray))
    }, {  # Not hidden
        '_check': l_and(isarray, l_not(iscomplexarray), isintent_nothide)
    },
    # Integer*1 array
    {'need': '#ctype#',
     '_check': isint1array,
     '_depend': ''
     },
    # Integer*-1 array
    {'need': '#ctype#',
     '_check': l_or(isunsigned_chararray, isunsigned_char),
     '_depend': ''
     },
    # Integer*-2 array
    {'need': '#ctype#',
     '_check': isunsigned_shortarray,
     '_depend': ''
     },
    # Integer*-8 array
    {'need': '#ctype#',
     '_check': isunsigned_long_longarray,
     '_depend': ''
     },
    # Complexarray
    {'need': '#ctype#',
     '_check': iscomplexarray,
     '_depend': ''
     },
    # Stringarray
    {
        'callfortranappend': {isarrayofstrings: 'flen(#varname#),'},
        'need': 'string',
        '_check': isstringarray
    }
]

arg_rules = [
    {
        'separatorsfor': sepdict
    },
    {  # Common
        'frompyobj': ['    /* Processing variable #varname# */',
                      {debugcapi: '    fprintf(stderr,"#vardebuginfo#\\n");'}, ],
        'cleanupfrompyobj': '    /* End of cleaning variable #varname# */',
        '_depend': '',
        'need': typedef_need_dict,
    },
    # Doc signatures
    {
        'docstropt': {l_and(isoptional, isintent_nothide): '#pydocsign#'},
        'docstrreq': {l_and(isrequired, isintent_nothide): '#pydocsign#'},
        'docstrout': {isintent_out: '#pydocsignout#'},
        'latexdocstropt': {l_and(isoptional, isintent_nothide): ['\\item[]{{}\\verb@#pydocsign#@{}}',
                                                                 {hasnote: '--- #note#'}]},
        'latexdocstrreq': {l_and(isrequired, isintent_nothide): ['\\item[]{{}\\verb@#pydocsign#@{}}',
                                                                 {hasnote: '--- #note#'}]},
        'latexdocstrout': {isintent_out: ['\\item[]{{}\\verb@#pydocsignout#@{}}',
                                          {l_and(hasnote, isintent_hide): '--- #note#',
                                           l_and(hasnote, isintent_nothide): '--- See above.'}]},
        'depend': ''
    },
    # Required/Optional arguments
    {
        'kwlist': '"#varname#",',
        'docsign': '#varname#,',
        '_check': l_and(isintent_nothide, l_not(isoptional))
    },
    {
        'kwlistopt': '"#varname#",',
        'docsignopt': '#varname#=#showinit#,',
        'docsignoptshort': '#varname#,',
        '_check': l_and(isintent_nothide, isoptional)
    },
    # Docstring/BuildValue
    {
        'docreturn': '#outvarname#,',
        'returnformat': '#varrformat#',
        '_check': isintent_out
    },
    # Externals (call-back functions)
    {  # Common
        'docsignxa': {isintent_nothide: '#varname#_extra_args=(),'},
        'docsignxashort': {isintent_nothide: '#varname#_extra_args,'},
        'docstropt': {isintent_nothide: '#varname#_extra_args : input tuple, optional\\n    Default: ()'},
        'docstrcbs': '#cbdocstr#',
        'latexdocstrcbs': '\\item[] #cblatexdocstr#',
        'latexdocstropt': {isintent_nothide: '\\item[]{{}\\verb@#varname#_extra_args := () input tuple@{}} --- Extra arguments for call-back function {{}\\verb@#varname#@{}}.'},
        'decl': ['    #cbname#_t #varname#_cb = { Py_None, NULL, 0 };',
                 '    #cbname#_t *#varname#_cb_ptr = &#varname#_cb;',
                 '    PyTupleObject *#varname#_xa_capi = NULL;',
                 {l_not(isintent_callback):
                  '    #cbname#_typedef #varname#_cptr;'}
                 ],
        'kwlistxa': {isintent_nothide: '"#varname#_extra_args",'},
        'argformat': {isrequired: 'O'},
        'keyformat': {isoptional: 'O'},
        'xaformat': {isintent_nothide: 'O!'},
        'args_capi': {isrequired: ',&#varname#_cb.capi'},
        'keys_capi': {isoptional: ',&#varname#_cb.capi'},
        'keys_xa': ',&PyTuple_Type,&#varname#_xa_capi',
        'setjmpbuf': '(setjmp(#varname#_cb.jmpbuf))',
        'callfortran': {l_not(isintent_callback): '#varname#_cptr,'},
        'need': ['#cbname#', 'setjmp.h'],
        '_check': isexternal
    },
    {
        'frompyobj': [{l_not(isintent_callback): """\
if(F2PyCapsule_Check(#varname#_cb.capi)) {
  #varname#_cptr = F2PyCapsule_AsVoidPtr(#varname#_cb.capi);
} else {
  #varname#_cptr = #cbname#;
}
"""}, {isintent_callback: """\
if (#varname#_cb.capi==Py_None) {
  #varname#_cb.capi = PyObject_GetAttrString(#modulename#_module,\"#varname#\");
  if (#varname#_cb.capi) {
    if (#varname#_xa_capi==NULL) {
      if (PyObject_HasAttrString(#modulename#_module,\"#varname#_extra_args\")) {
        PyObject* capi_tmp = PyObject_GetAttrString(#modulename#_module,\"#varname#_extra_args\");
        if (capi_tmp) {
          #varname#_xa_capi = (PyTupleObject *)PySequence_Tuple(capi_tmp);
          Py_DECREF(capi_tmp);
        }
        else {
          #varname#_xa_capi = (PyTupleObject *)Py_BuildValue(\"()\");
        }
        if (#varname#_xa_capi==NULL) {
          PyErr_SetString(#modulename#_error,\"Failed to convert #modulename#.#varname#_extra_args to tuple.\\n\");
          return NULL;
        }
      }
    }
  }
  if (#varname#_cb.capi==NULL) {
    PyErr_SetString(#modulename#_error,\"Callback #varname# not defined (as an argument or module #modulename# attribute).\\n\");
    return NULL;
  }
}
"""},
            """\
    if (create_cb_arglist(#varname#_cb.capi,#varname#_xa_capi,#maxnofargs#,#nofoptargs#,&#varname#_cb.nofargs,&#varname#_cb.args_capi,\"failed in processing argument list for call-back #varname#.\")) {
""",
            {debugcapi: ["""\
        fprintf(stderr,\"debug-capi:Assuming %d arguments; at most #maxnofargs#(-#nofoptargs#) is expected.\\n\",#varname#_cb.nofargs);
        CFUNCSMESSPY(\"for #varname#=\",#varname#_cb.capi);""",
                         {l_not(isintent_callback): """        fprintf(stderr,\"#vardebugshowvalue# (call-back in C).\\n\",#cbname#);"""}]},
            """\
        CFUNCSMESS(\"Saving callback variables for `#varname#`.\\n\");
        #varname#_cb_ptr = swap_active_#cbname#(#varname#_cb_ptr);""",
        ],
        'cleanupfrompyobj':
        """\
        CFUNCSMESS(\"Restoring callback variables for `#varname#`.\\n\");
        #varname#_cb_ptr = swap_active_#cbname#(#varname#_cb_ptr);
        Py_DECREF(#varname#_cb.args_capi);
    }""",
        'need': ['SWAP', 'create_cb_arglist'],
        '_check': isexternal,
        '_depend': ''
    },
    # Scalars (not complex)
    {  # Common
        'decl': '    #ctype# #varname# = 0;',
        'pyobjfrom': {debugcapi: '    fprintf(stderr,"#vardebugshowvalue#\\n",#varname#);'},
        'callfortran': {l_or(isintent_c, isattr_value): '#varname#,', l_not(l_or(isintent_c, isattr_value)): '&#varname#,'},
        'return': {isintent_out: ',#varname#'},
        '_check': l_and(isscalar, l_not(iscomplex))
    }, {
        'need': {hasinitvalue: 'math.h'},
        '_check': l_and(isscalar, l_not(iscomplex)),
    }, {  # Not hidden
        'decl': '    PyObject *#varname#_capi = Py_None;',
        'argformat': {isrequired: 'O'},
        'keyformat': {isoptional: 'O'},
        'args_capi': {isrequired: ',&#varname#_capi'},
        'keys_capi': {isoptional: ',&#varname#_capi'},
        'pyobjfrom': {isintent_inout: """\
    f2py_success = try_pyarr_from_#ctype#(#varname#_capi,&#varname#);
    if (f2py_success) {"""},
        'closepyobjfrom': {isintent_inout: "    } /*if (f2py_success) of #varname# pyobjfrom*/"},
        'need': {isintent_inout: 'try_pyarr_from_#ctype#'},
        '_check': l_and(isscalar, l_not(iscomplex), l_not(isstring),
                        isintent_nothide)
    }, {
        'frompyobj': [
            # hasinitvalue...
            #   if pyobj is None:
            #     varname = init
            #   else
            #     from_pyobj(varname)
            #
            # isoptional and noinitvalue...
            #   if pyobj is not None:
            #     from_pyobj(varname)
            #   else:
            #     varname is uninitialized
            #
            # ...
            #   from_pyobj(varname)
            #
            {hasinitvalue: '    if (#varname#_capi == Py_None) #varname# = #init#; else',
             '_depend': ''},
            {l_and(isoptional, l_not(hasinitvalue)): '    if (#varname#_capi != Py_None)',
             '_depend': ''},
            {l_not(islogical): '''\
        f2py_success = #ctype#_from_pyobj(&#varname#,#varname#_capi,"#pyname#() #nth# (#varname#) can\'t be converted to #ctype#");
    if (f2py_success) {'''},
            {islogical: '''\
        #varname# = (#ctype#)PyObject_IsTrue(#varname#_capi);
        f2py_success = 1;
    if (f2py_success) {'''},
        ],
        'cleanupfrompyobj': '    } /*if (f2py_success) of #varname#*/',
        'need': {l_not(islogical): '#ctype#_from_pyobj'},
        '_check': l_and(isscalar, l_not(iscomplex), isintent_nothide),
        '_depend': ''
    }, {  # Hidden
        'frompyobj': {hasinitvalue: '    #varname# = #init#;'},
        'need': typedef_need_dict,
        '_check': l_and(isscalar, l_not(iscomplex), isintent_hide),
        '_depend': ''
    }, {  # Common
        'frompyobj': {debugcapi: '    fprintf(stderr,"#vardebugshowvalue#\\n",#varname#);'},
        '_check': l_and(isscalar, l_not(iscomplex)),
        '_depend': ''
    },
    # Complex scalars
    {  # Common
        'decl': '    #ctype# #varname#;',
        'callfortran': {isintent_c: '#varname#,', l_not(isintent_c): '&#varname#,'},
        'pyobjfrom': {debugcapi: '    fprintf(stderr,"#vardebugshowvalue#\\n",#varname#.r,#varname#.i);'},
        'return': {isintent_out: ',#varname#_capi'},
        '_check': iscomplex
    }, {  # Not hidden
        'decl': '    PyObject *#varname#_capi = Py_None;',
        'argformat': {isrequired: 'O'},
        'keyformat': {isoptional: 'O'},
        'args_capi': {isrequired: ',&#varname#_capi'},
        'keys_capi': {isoptional: ',&#varname#_capi'},
        'need': {isintent_inout: 'try_pyarr_from_#ctype#'},
        'pyobjfrom': {isintent_inout: """\
        f2py_success = try_pyarr_from_#ctype#(#varname#_capi,&#varname#);
        if (f2py_success) {"""},
        'closepyobjfrom': {isintent_inout: "        } /*if (f2py_success) of #varname# pyobjfrom*/"},
        '_check': l_and(iscomplex, isintent_nothide)
    }, {
        'frompyobj': [{hasinitvalue: '    if (#varname#_capi==Py_None) {#varname#.r = #init.r#, #varname#.i = #init.i#;} else'},
                      {l_and(isoptional, l_not(hasinitvalue))
                             : '    if (#varname#_capi != Py_None)'},
                      '        f2py_success = #ctype#_from_pyobj(&#varname#,#varname#_capi,"#pyname#() #nth# (#varname#) can\'t be converted to #ctype#");'
                      '\n    if (f2py_success) {'],
        'cleanupfrompyobj': '    }  /*if (f2py_success) of #varname# frompyobj*/',
        'need': ['#ctype#_from_pyobj'],
        '_check': l_and(iscomplex, isintent_nothide),
        '_depend': ''
    }, {  # Hidden
        'decl': {isintent_out: '    PyObject *#varname#_capi = Py_None;'},
        '_check': l_and(iscomplex, isintent_hide)
    }, {
        'frompyobj': {hasinitvalue: '    #varname#.r = #init.r#, #varname#.i = #init.i#;'},
        '_check': l_and(iscomplex, isintent_hide),
        '_depend': ''
    }, {  # Common
        'pyobjfrom': {isintent_out: '    #varname#_capi = pyobj_from_#ctype#1(#varname#);'},
        'need': ['pyobj_from_#ctype#1'],
        '_check': iscomplex
    }, {
        'frompyobj': {debugcapi: '    fprintf(stderr,"#vardebugshowvalue#\\n",#varname#.r,#varname#.i);'},
        '_check': iscomplex,
        '_depend': ''
    },
    # String
    {  # Common
        'decl': ['    #ctype# #varname# = NULL;',
                 '    int slen(#varname#);',
                 '    PyObject *#varname#_capi = Py_None;'],
        'callfortran': '#varname#,',
        'callfortranappend': 'slen(#varname#),',
        'pyobjfrom': [
            {debugcapi:
             '    fprintf(stderr,'
             '"#vardebugshowvalue#\\n",slen(#varname#),#varname#);'},
            # The trailing null value for Fortran is blank.
            {l_and(isintent_out, l_not(isintent_c)):
             "        STRINGPADN(#varname#, slen(#varname#), ' ', '\\0');"},
        ],
        'return': {isintent_out: ',#varname#'},
        'need': ['len..',
                 {l_and(isintent_out, l_not(isintent_c)): 'STRINGPADN'}],
        '_check': isstring
    }, {  # Common
        'frompyobj': [
            """\
    slen(#varname#) = #elsize#;
    f2py_success = #ctype#_from_pyobj(&#varname#,&slen(#varname#),#init#,"""
"""#varname#_capi,\"#ctype#_from_pyobj failed in converting #nth#"""
"""`#varname#\' of #pyname# to C #ctype#\");
    if (f2py_success) {""",
            # The trailing null value for Fortran is blank.
            {l_not(isintent_c):
             "        STRINGPADN(#varname#, slen(#varname#), '\\0', ' ');"},
        ],
        'cleanupfrompyobj': """\
        STRINGFREE(#varname#);
    }  /*if (f2py_success) of #varname#*/""",
        'need': ['#ctype#_from_pyobj', 'len..', 'STRINGFREE',
                 {l_not(isintent_c): 'STRINGPADN'}],
        '_check': isstring,
        '_depend': ''
    }, {  # Not hidden
        'argformat': {isrequired: 'O'},
        'keyformat': {isoptional: 'O'},
        'args_capi': {isrequired: ',&#varname#_capi'},
        'keys_capi': {isoptional: ',&#varname#_capi'},
        'pyobjfrom': [
            {l_and(isintent_inout, l_not(isintent_c)):
             "        STRINGPADN(#varname#, slen(#varname#), ' ', '\\0');"},
            {isintent_inout: '''\
    f2py_success = try_pyarr_from_#ctype#(#varname#_capi, #varname#,
                                          slen(#varname#));
    if (f2py_success) {'''}],
        'closepyobjfrom': {isintent_inout: '    } /*if (f2py_success) of #varname# pyobjfrom*/'},
        'need': {isintent_inout: 'try_pyarr_from_#ctype#',
                 l_and(isintent_inout, l_not(isintent_c)): 'STRINGPADN'},
        '_check': l_and(isstring, isintent_nothide)
    }, {  # Hidden
        '_check': l_and(isstring, isintent_hide)
    }, {
        'frompyobj': {debugcapi: '    fprintf(stderr,"#vardebugshowvalue#\\n",slen(#varname#),#varname#);'},
        '_check': isstring,
        '_depend': ''
    },
    # Array
    {  # Common
        'decl': ['    #ctype# *#varname# = NULL;',
                 '    npy_intp #varname#_Dims[#rank#] = {#rank*[-1]#};',
                 '    const int #varname#_Rank = #rank#;',
                 '    PyArrayObject *capi_#varname#_as_array = NULL;',
                 '    int capi_#varname#_intent = 0;',
                 {isstringarray: '    int slen(#varname#) = 0;'},
                 ],
        'callfortran': '#varname#,',
        'callfortranappend': {isstringarray: 'slen(#varname#),'},
        'return': {isintent_out: ',capi_#varname#_as_array'},
        'need': 'len..',
        '_check': isarray
    }, {  # intent(overwrite) array
        'decl': '    int capi_overwrite_#varname# = 1;',
        'kwlistxa': '"overwrite_#varname#",',
        'xaformat': 'i',
        'keys_xa': ',&capi_overwrite_#varname#',
        'docsignxa': 'overwrite_#varname#=1,',
        'docsignxashort': 'overwrite_#varname#,',
        'docstropt': 'overwrite_#varname# : input int, optional\\n    Default: 1',
        '_check': l_and(isarray, isintent_overwrite),
    }, {
        'frompyobj': '    capi_#varname#_intent |= (capi_overwrite_#varname#?0:F2PY_INTENT_COPY);',
        '_check': l_and(isarray, isintent_overwrite),
        '_depend': '',
    },
    {  # intent(copy) array
        'decl': '    int capi_overwrite_#varname# = 0;',
        'kwlistxa': '"overwrite_#varname#",',
        'xaformat': 'i',
        'keys_xa': ',&capi_overwrite_#varname#',
        'docsignxa': 'overwrite_#varname#=0,',
        'docsignxashort': 'overwrite_#varname#,',
        'docstropt': 'overwrite_#varname# : input int, optional\\n    Default: 0',
        '_check': l_and(isarray, isintent_copy),
    }, {
        'frompyobj': '    capi_#varname#_intent |= (capi_overwrite_#varname#?0:F2PY_INTENT_COPY);',
        '_check': l_and(isarray, isintent_copy),
        '_depend': '',
    }, {
        'need': [{hasinitvalue: 'forcomb'}, {hasinitvalue: 'CFUNCSMESS'}],
        '_check': isarray,
        '_depend': ''
    }, {  # Not hidden
        'decl': '    PyObject *#varname#_capi = Py_None;',
        'argformat': {isrequired: 'O'},
        'keyformat': {isoptional: 'O'},
        'args_capi': {isrequired: ',&#varname#_capi'},
        'keys_capi': {isoptional: ',&#varname#_capi'},
        '_check': l_and(isarray, isintent_nothide)
    }, {
        'frompyobj': [
            '    #setdims#;',
            '    capi_#varname#_intent |= #intent#;',
            ('    const char capi_errmess[] = "#modulename#.#pyname#:'
             ' failed to create array from the #nth# `#varname#`";'),
            {isintent_hide:
             '    capi_#varname#_as_array = ndarray_from_pyobj('
             '  #atype#,#elsize#,#varname#_Dims,#varname#_Rank,'
             '  capi_#varname#_intent,Py_None,capi_errmess);'},
            {isintent_nothide:
             '    capi_#varname#_as_array = ndarray_from_pyobj('
             '  #atype#,#elsize#,#varname#_Dims,#varname#_Rank,'
             '  capi_#varname#_intent,#varname#_capi,capi_errmess);'},
            """\
    if (capi_#varname#_as_array == NULL) {
        PyObject* capi_err = PyErr_Occurred();
        if (capi_err == NULL) {
            capi_err = #modulename#_error;
            PyErr_SetString(capi_err, capi_errmess);
        }
    } else {
        #varname# = (#ctype# *)(PyArray_DATA(capi_#varname#_as_array));
""",
            {isstringarray:
             '    slen(#varname#) = f2py_itemsize(#varname#);'},
            {hasinitvalue: [
                {isintent_nothide:
                 '    if (#varname#_capi == Py_None) {'},
                {isintent_hide: '    {'},
                {iscomplexarray: '        #ctype# capi_c;'},
                """\
        int *_i,capi_i=0;
        CFUNCSMESS(\"#name#: Initializing #varname#=#init#\\n\");
        struct ForcombCache cache;
        if (initforcomb(&cache, PyArray_DIMS(capi_#varname#_as_array),
                        PyArray_NDIM(capi_#varname#_as_array),1)) {
            while ((_i = nextforcomb(&cache)))
                #varname#[capi_i++] = #init#; /* fortran way */
        } else {
            PyObject *exc, *val, *tb;
            PyErr_Fetch(&exc, &val, &tb);
            PyErr_SetString(exc ? exc : #modulename#_error,
                \"Initialization of #nth# #varname# failed (initforcomb).\");
            npy_PyErr_ChainExceptionsCause(exc, val, tb);
            f2py_success = 0;
        }
    }
    if (f2py_success) {"""]},
                      ],
        'cleanupfrompyobj': [  # note that this list will be reversed
            '    }  '
            '/* if (capi_#varname#_as_array == NULL) ... else of #varname# */',
            {l_not(l_or(isintent_out, isintent_hide)): """\
    if((PyObject *)capi_#varname#_as_array!=#varname#_capi) {
        Py_XDECREF(capi_#varname#_as_array); }"""},
            {l_and(isintent_hide, l_not(isintent_out))
                   : """        Py_XDECREF(capi_#varname#_as_array);"""},
            {hasinitvalue: '    }  /*if (f2py_success) of #varname# init*/'},
        ],
        '_check': isarray,
        '_depend': ''
    },
    # Scalararray
    {  # Common
        '_check': l_and(isarray, l_not(iscomplexarray))
    }, {  # Not hidden
        '_check': l_and(isarray, l_not(iscomplexarray), isintent_nothide)
    },
    # Integer*1 array
    {'need': '#ctype#',
     '_check': isint1array,
     '_depend': ''
     },
    # Integer*-1 array
    {'need': '#ctype#',
     '_check': isunsigned_chararray,
     '_depend': ''
     },
    # Integer*-2 array
    {'need': '#ctype#',
     '_check': isunsigned_shortarray,
     '_depend': ''
     },
    # Integer*-8 array
    {'need': '#ctype#',
     '_check': isunsigned_long_longarray,
     '_depend': ''
     },
    # Complexarray
    {'need': '#ctype#',
     '_check': iscomplexarray,
     '_depend': ''
     },
    # Character
    {
        'need': 'string',
        '_check': ischaracter,
    },
    # Character array
    {
        'need': 'string',
        '_check': ischaracterarray,
    },
    # Stringarray
    {
        'callfortranappend': {isarrayofstrings: 'flen(#varname#),'},
        'need': 'string',
        '_check': isstringarray
    }
]

################# Rules for checking ###############

check_rules = [
    {
        'frompyobj': {debugcapi: '    fprintf(stderr,\"debug-capi:Checking `#check#\'\\n\");'},
        'need': 'len..'
    }, {
        'frompyobj': '    CHECKSCALAR(#check#,\"#check#\",\"#nth# #varname#\",\"#varshowvalue#\",#varname#) {',
        'cleanupfrompyobj': '    } /*CHECKSCALAR(#check#)*/',
        'need': 'CHECKSCALAR',
        '_check': l_and(isscalar, l_not(iscomplex)),
        '_break': ''
    }, {
        'frompyobj': '    CHECKSTRING(#check#,\"#check#\",\"#nth# #varname#\",\"#varshowvalue#\",#varname#) {',
        'cleanupfrompyobj': '    } /*CHECKSTRING(#check#)*/',
        'need': 'CHECKSTRING',
        '_check': isstring,
        '_break': ''
    }, {
        'need': 'CHECKARRAY',
        'frompyobj': '    CHECKARRAY(#check#,\"#check#\",\"#nth# #varname#\") {',
        'cleanupfrompyobj': '    } /*CHECKARRAY(#check#)*/',
        '_check': isarray,
        '_break': ''
    }, {
        'need': 'CHECKGENERIC',
        'frompyobj': '    CHECKGENERIC(#check#,\"#check#\",\"#nth# #varname#\") {',
        'cleanupfrompyobj': '    } /*CHECKGENERIC(#check#)*/',
    }
]

########## Applying the rules. No need to modify what follows #############

#################### Build C/API module #######################


def buildmodule(m, um):
    """
    Return
    """
    outmess(f"    Building module \"{m['name']}\"...\n")
    ret = {}
    mod_rules = defmod_rules[:]
    vrd = capi_maps.modsign2map(m)
    rd = dictappend({'f2py_version': f2py_version}, vrd)
    funcwrappers = []
    funcwrappers2 = []  # F90 codes
    for n in m['interfaced']:
        nb = None
        for bi in m['body']:
            if bi['block'] not in ['interface', 'abstract interface']:
                errmess('buildmodule: Expected interface block. Skipping.\n')
                continue
            for b in bi['body']:
                if b['name'] == n:
                    nb = b
                    break

        if not nb:
            print(
                f'buildmodule: Could not find the body of interfaced routine "{n}". Skipping.\n', file=sys.stderr)
            continue
        nb_list = [nb]
        if 'entry' in nb:
            for k, a in nb['entry'].items():
                nb1 = copy.deepcopy(nb)
                del nb1['entry']
                nb1['name'] = k
                nb1['args'] = a
                nb_list.append(nb1)
        for nb in nb_list:
            # requiresf90wrapper must be called before buildapi as it
            # rewrites assumed shape arrays as automatic arrays.
            isf90 = requiresf90wrapper(nb)
            # options is in scope here
            if options['emptygen']:
                b_path = options['buildpath']
                m_name = vrd['modulename']
                outmess('    Generating possibly empty wrappers"\n')
                Path(f"{b_path}/{vrd['coutput']}").touch()
                if isf90:
                    # f77 + f90 wrappers
                    outmess(f'    Maybe empty "{m_name}-f2pywrappers2.f90"\n')
                    Path(f'{b_path}/{m_name}-f2pywrappers2.f90').touch()
                    outmess(f'    Maybe empty "{m_name}-f2pywrappers.f"\n')
                    Path(f'{b_path}/{m_name}-f2pywrappers.f').touch()
                else:
                    # only f77 wrappers
                    outmess(f'    Maybe empty "{m_name}-f2pywrappers.f"\n')
                    Path(f'{b_path}/{m_name}-f2pywrappers.f').touch()
            api, wrap = buildapi(nb)
            if wrap:
                if isf90:
                    funcwrappers2.append(wrap)
                else:
                    funcwrappers.append(wrap)
            ar = applyrules(api, vrd)
            rd = dictappend(rd, ar)

    # Construct COMMON block support
    cr, wrap = common_rules.buildhooks(m)
    if wrap:
        funcwrappers.append(wrap)
    ar = applyrules(cr, vrd)
    rd = dictappend(rd, ar)

    # Construct F90 module support
    mr, wrap = f90mod_rules.buildhooks(m)
    if wrap:
        funcwrappers2.append(wrap)
    ar = applyrules(mr, vrd)
    rd = dictappend(rd, ar)

    for u in um:
        ar = use_rules.buildusevars(u, m['use'][u['name']])
        rd = dictappend(rd, ar)

    needs = cfuncs.get_needs()
    # Add mapped definitions
    needs['typedefs'] += [cvar for cvar in capi_maps.f2cmap_mapped  #
                          if cvar in typedef_need_dict.values()]
    code = {}
    for n in needs.keys():
        code[n] = []
        for k in needs[n]:
            c = ''
            if k in cfuncs.includes0:
                c = cfuncs.includes0[k]
            elif k in cfuncs.includes:
                c = cfuncs.includes[k]
            elif k in cfuncs.userincludes:
                c = cfuncs.userincludes[k]
            elif k in cfuncs.typedefs:
                c = cfuncs.typedefs[k]
            elif k in cfuncs.typedefs_generated:
                c = cfuncs.typedefs_generated[k]
            elif k in cfuncs.cppmacros:
                c = cfuncs.cppmacros[k]
            elif k in cfuncs.cfuncs:
                c = cfuncs.cfuncs[k]
            elif k in cfuncs.callbacks:
                c = cfuncs.callbacks[k]
            elif k in cfuncs.f90modhooks:
                c = cfuncs.f90modhooks[k]
            elif k in cfuncs.commonhooks:
                c = cfuncs.commonhooks[k]
            else:
                errmess(f'buildmodule: unknown need {repr(k)}.\n')
                continue
            code[n].append(c)
    mod_rules.append(code)
    for r in mod_rules:
        if ('_check' in r and r['_check'](m)) or ('_check' not in r):
            ar = applyrules(r, vrd, m)
            rd = dictappend(rd, ar)
    ar = applyrules(module_rules, rd)

    fn = os.path.join(options['buildpath'], vrd['coutput'])
    ret['csrc'] = fn
    with open(fn, 'w') as f:
        f.write(ar['modulebody'].replace('\t', 2 * ' '))
    outmess(f"    Wrote C/API module \"{m['name']}\" to file \"{fn}\"\n")

    if options['dorestdoc']:
        fn = os.path.join(
            options['buildpath'], vrd['modulename'] + 'module.rest')
        with open(fn, 'w') as f:
            f.write('.. -*- rest -*-\n')
            f.write('\n'.join(ar['restdoc']))
        outmess('    ReST Documentation is saved to file "%s/%smodule.rest"\n' %
                (options['buildpath'], vrd['modulename']))
    if options['dolatexdoc']:
        fn = os.path.join(
            options['buildpath'], vrd['modulename'] + 'module.tex')
        ret['ltx'] = fn
        with open(fn, 'w') as f:
            f.write(
                f'% This file is auto-generated with f2py (version:{f2py_version})\n')
            if 'shortlatex' not in options:
                f.write(
                    '\\documentclass{article}\n\\usepackage{a4wide}\n\\begin{document}\n\\tableofcontents\n\n')
                f.write('\n'.join(ar['latexdoc']))
            if 'shortlatex' not in options:
                f.write('\\end{document}')
        outmess('    Documentation is saved to file "%s/%smodule.tex"\n' %
                (options['buildpath'], vrd['modulename']))
    if funcwrappers:
        wn = os.path.join(options['buildpath'], vrd['f2py_wrapper_output'])
        ret['fsrc'] = wn
        with open(wn, 'w') as f:
            f.write('C     -*- fortran -*-\n')
            f.write(
                f'C     This file is autogenerated with f2py (version:{f2py_version})\n')
            f.write(
                'C     It contains Fortran 77 wrappers to fortran functions.\n')
            lines = []
            for l in ('\n\n'.join(funcwrappers) + '\n').split('\n'):
                if 0 <= l.find('!') < 66:
                    # don't split comment lines
                    lines.append(l + '\n')
                elif l and l[0] == ' ':
                    while len(l) >= 66:
                        lines.append(l[:66] + '\n     &')
                        l = l[66:]
                    lines.append(l + '\n')
                else:
                    lines.append(l + '\n')
            lines = ''.join(lines).replace('\n     &\n', '\n')
            f.write(lines)
        outmess(f'    Fortran 77 wrappers are saved to "{wn}\"\n')
    if funcwrappers2:
        wn = os.path.join(
            options['buildpath'], f"{vrd['modulename']}-f2pywrappers2.f90")
        ret['fsrc'] = wn
        with open(wn, 'w') as f:
            f.write('!     -*- f90 -*-\n')
            f.write(
                f'!     This file is autogenerated with f2py (version:{f2py_version})\n')
            f.write(
                '!     It contains Fortran 90 wrappers to fortran functions.\n')
            lines = []
            for l in ('\n\n'.join(funcwrappers2) + '\n').split('\n'):
                if 0 <= l.find('!') < 72:
                    # don't split comment lines
                    lines.append(l + '\n')
                elif len(l) > 72 and l[0] == ' ':
                    lines.append(l[:72] + '&\n     &')
                    l = l[72:]
                    while len(l) > 66:
                        lines.append(l[:66] + '&\n     &')
                        l = l[66:]
                    lines.append(l + '\n')
                else:
                    lines.append(l + '\n')
            lines = ''.join(lines).replace('\n     &\n', '\n')
            f.write(lines)
        outmess(f'    Fortran 90 wrappers are saved to "{wn}\"\n')
    return ret

################## Build C/API function #############


stnd = {1: 'st', 2: 'nd', 3: 'rd', 4: 'th', 5: 'th',
        6: 'th', 7: 'th', 8: 'th', 9: 'th', 0: 'th'}


def buildapi(rout):
    rout, wrap = func2subr.assubr(rout)
    args, depargs = getargs2(rout)
    capi_maps.depargs = depargs
    var = rout['vars']

    if ismoduleroutine(rout):
        outmess('            Constructing wrapper function "%s.%s"...\n' %
                (rout['modulename'], rout['name']))
    else:
        outmess(f"        Constructing wrapper function \"{rout['name']}\"...\n")
    # Routine
    vrd = capi_maps.routsign2map(rout)
    rd = dictappend({}, vrd)
    for r in rout_rules:
        if ('_check' in r and r['_check'](rout)) or ('_check' not in r):
            ar = applyrules(r, vrd, rout)
            rd = dictappend(rd, ar)

    # Args
    nth, nthk = 0, 0
    savevrd = {}
    for a in args:
        vrd = capi_maps.sign2map(a, var[a])
        if isintent_aux(var[a]):
            _rules = aux_rules
        else:
            _rules = arg_rules
            if not isintent_hide(var[a]):
                if not isoptional(var[a]):
                    nth = nth + 1
                    vrd['nth'] = repr(nth) + stnd[nth % 10] + ' argument'
                else:
                    nthk = nthk + 1
                    vrd['nth'] = repr(nthk) + stnd[nthk % 10] + ' keyword'
            else:
                vrd['nth'] = 'hidden'
        savevrd[a] = vrd
        for r in _rules:
            if '_depend' in r:
                continue
            if ('_check' in r and r['_check'](var[a])) or ('_check' not in r):
                ar = applyrules(r, vrd, var[a])
                rd = dictappend(rd, ar)
                if '_break' in r:
                    break
    for a in depargs:
        if isintent_aux(var[a]):
            _rules = aux_rules
        else:
            _rules = arg_rules
        vrd = savevrd[a]
        for r in _rules:
            if '_depend' not in r:
                continue
            if ('_check' in r and r['_check'](var[a])) or ('_check' not in r):
                ar = applyrules(r, vrd, var[a])
                rd = dictappend(rd, ar)
                if '_break' in r:
                    break
        if 'check' in var[a]:
            for c in var[a]['check']:
                vrd['check'] = c
                ar = applyrules(check_rules, vrd, var[a])
                rd = dictappend(rd, ar)
    if isinstance(rd['cleanupfrompyobj'], list):
        rd['cleanupfrompyobj'].reverse()
    if isinstance(rd['closepyobjfrom'], list):
        rd['closepyobjfrom'].reverse()
    rd['docsignature'] = stripcomma(replace('#docsign##docsignopt##docsignxa#',
                                            {'docsign': rd['docsign'],
                                             'docsignopt': rd['docsignopt'],
                                             'docsignxa': rd['docsignxa']}))
    optargs = stripcomma(replace('#docsignopt##docsignxa#',
                                 {'docsignxa': rd['docsignxashort'],
                                  'docsignopt': rd['docsignoptshort']}
                                 ))
    if optargs == '':
        rd['docsignatureshort'] = stripcomma(
            replace('#docsign#', {'docsign': rd['docsign']}))
    else:
        rd['docsignatureshort'] = replace('#docsign#[#docsignopt#]',
                                          {'docsign': rd['docsign'],
                                           'docsignopt': optargs,
                                           })
    rd['latexdocsignatureshort'] = rd['docsignatureshort'].replace('_', '\\_')
    rd['latexdocsignatureshort'] = rd[
        'latexdocsignatureshort'].replace(',', ', ')
    cfs = stripcomma(replace('#callfortran##callfortranappend#', {
                     'callfortran': rd['callfortran'], 'callfortranappend': rd['callfortranappend']}))
    if len(rd['callfortranappend']) > 1:
        rd['callcompaqfortran'] = stripcomma(replace('#callfortran# 0,#callfortranappend#', {
                                             'callfortran': rd['callfortran'], 'callfortranappend': rd['callfortranappend']}))
    else:
        rd['callcompaqfortran'] = cfs
    rd['callfortran'] = cfs
    if isinstance(rd['docreturn'], list):
        rd['docreturn'] = stripcomma(
            replace('#docreturn#', {'docreturn': rd['docreturn']})) + ' = '
    rd['docstrsigns'] = []
    rd['latexdocstrsigns'] = []
    for k in ['docstrreq', 'docstropt', 'docstrout', 'docstrcbs']:
        if k in rd and isinstance(rd[k], list):
            rd['docstrsigns'] = rd['docstrsigns'] + rd[k]
        k = 'latex' + k
        if k in rd and isinstance(rd[k], list):
            rd['latexdocstrsigns'] = rd['latexdocstrsigns'] + rd[k][0:1] +\
                ['\\begin{description}'] + rd[k][1:] +\
                ['\\end{description}']

    ar = applyrules(routine_rules, rd)
    if ismoduleroutine(rout):
        outmess(f"              {ar['docshort']}\n")
    else:
        outmess(f"          {ar['docshort']}\n")
    return ar, wrap


#################### EOF rules.py #######################

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\application\application.py ===
from __future__ import annotations

import asyncio
import contextvars
import os
import re
import signal
import sys
import threading
import time
from asyncio import (
    AbstractEventLoop,
    Future,
    Task,
    ensure_future,
    get_running_loop,
    sleep,
)
from contextlib import ExitStack, contextmanager
from subprocess import Popen
from traceback import format_tb
from typing import (
    Any,
    Callable,
    Coroutine,
    Generator,
    Generic,
    Hashable,
    Iterable,
    Iterator,
    TypeVar,
    cast,
    overload,
)

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.cache import SimpleCache
from prompt_toolkit.clipboard import Clipboard, InMemoryClipboard
from prompt_toolkit.cursor_shapes import AnyCursorShapeConfig, to_cursor_shape_config
from prompt_toolkit.data_structures import Size
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.eventloop import (
    InputHook,
    get_traceback_from_context,
    new_eventloop_with_inputhook,
    run_in_executor_with_context,
)
from prompt_toolkit.eventloop.utils import call_soon_threadsafe
from prompt_toolkit.filters import Condition, Filter, FilterOrBool, to_filter
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.input.base import Input
from prompt_toolkit.input.typeahead import get_typeahead, store_typeahead
from prompt_toolkit.key_binding.bindings.page_navigation import (
    load_page_navigation_bindings,
)
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.key_binding.emacs_state import EmacsState
from prompt_toolkit.key_binding.key_bindings import (
    Binding,
    ConditionalKeyBindings,
    GlobalOnlyKeyBindings,
    KeyBindings,
    KeyBindingsBase,
    KeysTuple,
    merge_key_bindings,
)
from prompt_toolkit.key_binding.key_processor import KeyPressEvent, KeyProcessor
from prompt_toolkit.key_binding.vi_state import ViState
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import Container, Window
from prompt_toolkit.layout.controls import BufferControl, UIControl
from prompt_toolkit.layout.dummy import create_dummy_layout
from prompt_toolkit.layout.layout import Layout, walk
from prompt_toolkit.output import ColorDepth, Output
from prompt_toolkit.renderer import Renderer, print_formatted_text
from prompt_toolkit.search import SearchState
from prompt_toolkit.styles import (
    BaseStyle,
    DummyStyle,
    DummyStyleTransformation,
    DynamicStyle,
    StyleTransformation,
    default_pygments_style,
    default_ui_style,
    merge_styles,
)
from prompt_toolkit.utils import Event, in_main_thread

from .current import get_app_session, set_app
from .run_in_terminal import in_terminal, run_in_terminal

__all__ = [
    "Application",
]


E = KeyPressEvent
_AppResult = TypeVar("_AppResult")
ApplicationEventHandler = Callable[["Application[_AppResult]"], None]

_SIGWINCH = getattr(signal, "SIGWINCH", None)
_SIGTSTP = getattr(signal, "SIGTSTP", None)


class Application(Generic[_AppResult]):
    """
    The main Application class!
    This glues everything together.

    :param layout: A :class:`~prompt_toolkit.layout.Layout` instance.
    :param key_bindings:
        :class:`~prompt_toolkit.key_binding.KeyBindingsBase` instance for
        the key bindings.
    :param clipboard: :class:`~prompt_toolkit.clipboard.Clipboard` to use.
    :param full_screen: When True, run the application on the alternate screen buffer.
    :param color_depth: Any :class:`~.ColorDepth` value, a callable that
        returns a :class:`~.ColorDepth` or `None` for default.
    :param erase_when_done: (bool) Clear the application output when it finishes.
    :param reverse_vi_search_direction: Normally, in Vi mode, a '/' searches
        forward and a '?' searches backward. In Readline mode, this is usually
        reversed.
    :param min_redraw_interval: Number of seconds to wait between redraws. Use
        this for applications where `invalidate` is called a lot. This could cause
        a lot of terminal output, which some terminals are not able to process.

        `None` means that every `invalidate` will be scheduled right away
        (which is usually fine).

        When one `invalidate` is called, but a scheduled redraw of a previous
        `invalidate` call has not been executed yet, nothing will happen in any
        case.

    :param max_render_postpone_time: When there is high CPU (a lot of other
        scheduled calls), postpone the rendering max x seconds.  '0' means:
        don't postpone. '.5' means: try to draw at least twice a second.

    :param refresh_interval: Automatically invalidate the UI every so many
        seconds. When `None` (the default), only invalidate when `invalidate`
        has been called.

    :param terminal_size_polling_interval: Poll the terminal size every so many
        seconds. Useful if the applications runs in a thread other then then
        main thread where SIGWINCH can't be handled, or on Windows.

    Filters:

    :param mouse_support: (:class:`~prompt_toolkit.filters.Filter` or
        boolean). When True, enable mouse support.
    :param paste_mode: :class:`~prompt_toolkit.filters.Filter` or boolean.
    :param editing_mode: :class:`~prompt_toolkit.enums.EditingMode`.

    :param enable_page_navigation_bindings: When `True`, enable the page
        navigation key bindings. These include both Emacs and Vi bindings like
        page-up, page-down and so on to scroll through pages. Mostly useful for
        creating an editor or other full screen applications. Probably, you
        don't want this for the implementation of a REPL. By default, this is
        enabled if `full_screen` is set.

    Callbacks (all of these should accept an
    :class:`~prompt_toolkit.application.Application` object as input.)

    :param on_reset: Called during reset.
    :param on_invalidate: Called when the UI has been invalidated.
    :param before_render: Called right before rendering.
    :param after_render: Called right after rendering.

    I/O:
    (Note that the preferred way to change the input/output is by creating an
    `AppSession` with the required input/output objects. If you need multiple
    applications running at the same time, you have to create a separate
    `AppSession` using a `with create_app_session():` block.

    :param input: :class:`~prompt_toolkit.input.Input` instance.
    :param output: :class:`~prompt_toolkit.output.Output` instance. (Probably
                   Vt100_Output or Win32Output.)

    Usage:

        app = Application(...)
        app.run()

        # Or
        await app.run_async()
    """

    def __init__(
        self,
        layout: Layout | None = None,
        style: BaseStyle | None = None,
        include_default_pygments_style: FilterOrBool = True,
        style_transformation: StyleTransformation | None = None,
        key_bindings: KeyBindingsBase | None = None,
        clipboard: Clipboard | None = None,
        full_screen: bool = False,
        color_depth: (ColorDepth | Callable[[], ColorDepth | None] | None) = None,
        mouse_support: FilterOrBool = False,
        enable_page_navigation_bindings: None
        | (FilterOrBool) = None,  # Can be None, True or False.
        paste_mode: FilterOrBool = False,
        editing_mode: EditingMode = EditingMode.EMACS,
        erase_when_done: bool = False,
        reverse_vi_search_direction: FilterOrBool = False,
        min_redraw_interval: float | int | None = None,
        max_render_postpone_time: float | int | None = 0.01,
        refresh_interval: float | None = None,
        terminal_size_polling_interval: float | None = 0.5,
        cursor: AnyCursorShapeConfig = None,
        on_reset: ApplicationEventHandler[_AppResult] | None = None,
        on_invalidate: ApplicationEventHandler[_AppResult] | None = None,
        before_render: ApplicationEventHandler[_AppResult] | None = None,
        after_render: ApplicationEventHandler[_AppResult] | None = None,
        # I/O.
        input: Input | None = None,
        output: Output | None = None,
    ) -> None:
        # If `enable_page_navigation_bindings` is not specified, enable it in
        # case of full screen applications only. This can be overridden by the user.
        if enable_page_navigation_bindings is None:
            enable_page_navigation_bindings = Condition(lambda: self.full_screen)

        paste_mode = to_filter(paste_mode)
        mouse_support = to_filter(mouse_support)
        reverse_vi_search_direction = to_filter(reverse_vi_search_direction)
        enable_page_navigation_bindings = to_filter(enable_page_navigation_bindings)
        include_default_pygments_style = to_filter(include_default_pygments_style)

        if layout is None:
            layout = create_dummy_layout()

        if style_transformation is None:
            style_transformation = DummyStyleTransformation()

        self.style = style
        self.style_transformation = style_transformation

        # Key bindings.
        self.key_bindings = key_bindings
        self._default_bindings = load_key_bindings()
        self._page_navigation_bindings = load_page_navigation_bindings()

        self.layout = layout
        self.clipboard = clipboard or InMemoryClipboard()
        self.full_screen: bool = full_screen
        self._color_depth = color_depth
        self.mouse_support = mouse_support

        self.paste_mode = paste_mode
        self.editing_mode = editing_mode
        self.erase_when_done = erase_when_done
        self.reverse_vi_search_direction = reverse_vi_search_direction
        self.enable_page_navigation_bindings = enable_page_navigation_bindings
        self.min_redraw_interval = min_redraw_interval
        self.max_render_postpone_time = max_render_postpone_time
        self.refresh_interval = refresh_interval
        self.terminal_size_polling_interval = terminal_size_polling_interval

        self.cursor = to_cursor_shape_config(cursor)

        # Events.
        self.on_invalidate = Event(self, on_invalidate)
        self.on_reset = Event(self, on_reset)
        self.before_render = Event(self, before_render)
        self.after_render = Event(self, after_render)

        # I/O.
        session = get_app_session()
        self.output = output or session.output
        self.input = input or session.input

        # List of 'extra' functions to execute before a Application.run.
        self.pre_run_callables: list[Callable[[], None]] = []

        self._is_running = False
        self.future: Future[_AppResult] | None = None
        self.loop: AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self.context: contextvars.Context | None = None

        #: Quoted insert. This flag is set if we go into quoted insert mode.
        self.quoted_insert = False

        #: Vi state. (For Vi key bindings.)
        self.vi_state = ViState()
        self.emacs_state = EmacsState()

        #: When to flush the input (For flushing escape keys.) This is important
        #: on terminals that use vt100 input. We can't distinguish the escape
        #: key from for instance the left-arrow key, if we don't know what follows
        #: after "\x1b". This little timer will consider "\x1b" to be escape if
        #: nothing did follow in this time span.
        #: This seems to work like the `ttimeoutlen` option in Vim.
        self.ttimeoutlen = 0.5  # Seconds.

        #: Like Vim's `timeoutlen` option. This can be `None` or a float.  For
        #: instance, suppose that we have a key binding AB and a second key
        #: binding A. If the uses presses A and then waits, we don't handle
        #: this binding yet (unless it was marked 'eager'), because we don't
        #: know what will follow. This timeout is the maximum amount of time
        #: that we wait until we call the handlers anyway. Pass `None` to
        #: disable this timeout.
        self.timeoutlen = 1.0

        #: The `Renderer` instance.
        # Make sure that the same stdout is used, when a custom renderer has been passed.
        self._merged_style = self._create_merged_style(include_default_pygments_style)

        self.renderer = Renderer(
            self._merged_style,
            self.output,
            full_screen=full_screen,
            mouse_support=mouse_support,
            cpr_not_supported_callback=self.cpr_not_supported_callback,
        )

        #: Render counter. This one is increased every time the UI is rendered.
        #: It can be used as a key for caching certain information during one
        #: rendering.
        self.render_counter = 0

        # Invalidate flag. When 'True', a repaint has been scheduled.
        self._invalidated = False
        self._invalidate_events: list[
            Event[object]
        ] = []  # Collection of 'invalidate' Event objects.
        self._last_redraw_time = 0.0  # Unix timestamp of last redraw. Used when
        # `min_redraw_interval` is given.

        #: The `InputProcessor` instance.
        self.key_processor = KeyProcessor(_CombinedRegistry(self))

        # If `run_in_terminal` was called. This will point to a `Future` what will be
        # set at the point when the previous run finishes.
        self._running_in_terminal = False
        self._running_in_terminal_f: Future[None] | None = None

        # Trigger initialize callback.
        self.reset()

    def _create_merged_style(self, include_default_pygments_style: Filter) -> BaseStyle:
        """
        Create a `Style` object that merges the default UI style, the default
        pygments style, and the custom user style.
        """
        dummy_style = DummyStyle()
        pygments_style = default_pygments_style()

        @DynamicStyle
        def conditional_pygments_style() -> BaseStyle:
            if include_default_pygments_style():
                return pygments_style
            else:
                return dummy_style

        return merge_styles(
            [
                default_ui_style(),
                conditional_pygments_style,
                DynamicStyle(lambda: self.style),
            ]
        )

    @property
    def color_depth(self) -> ColorDepth:
        """
        The active :class:`.ColorDepth`.

        The current value is determined as follows:

        - If a color depth was given explicitly to this application, use that
          value.
        - Otherwise, fall back to the color depth that is reported by the
          :class:`.Output` implementation. If the :class:`.Output` class was
          created using `output.defaults.create_output`, then this value is
          coming from the $PROMPT_TOOLKIT_COLOR_DEPTH environment variable.
        """
        depth = self._color_depth

        if callable(depth):
            depth = depth()

        if depth is None:
            depth = self.output.get_default_color_depth()

        return depth

    @property
    def current_buffer(self) -> Buffer:
        """
        The currently focused :class:`~.Buffer`.

        (This returns a dummy :class:`.Buffer` when none of the actual buffers
        has the focus. In this case, it's really not practical to check for
        `None` values or catch exceptions every time.)
        """
        return self.layout.current_buffer or Buffer(
            name="dummy-buffer"
        )  # Dummy buffer.

    @property
    def current_search_state(self) -> SearchState:
        """
        Return the current :class:`.SearchState`. (The one for the focused
        :class:`.BufferControl`.)
        """
        ui_control = self.layout.current_control
        if isinstance(ui_control, BufferControl):
            return ui_control.search_state
        else:
            return SearchState()  # Dummy search state.  (Don't return None!)

    def reset(self) -> None:
        """
        Reset everything, for reading the next input.
        """
        # Notice that we don't reset the buffers. (This happens just before
        # returning, and when we have multiple buffers, we clearly want the
        # content in the other buffers to remain unchanged between several
        # calls of `run`. (And the same is true for the focus stack.)

        self.exit_style = ""

        self._background_tasks: set[Task[None]] = set()

        self.renderer.reset()
        self.key_processor.reset()
        self.layout.reset()
        self.vi_state.reset()
        self.emacs_state.reset()

        # Trigger reset event.
        self.on_reset.fire()

        # Make sure that we have a 'focusable' widget focused.
        # (The `Layout` class can't determine this.)
        layout = self.layout

        if not layout.current_control.is_focusable():
            for w in layout.find_all_windows():
                if w.content.is_focusable():
                    layout.current_window = w
                    break

    def invalidate(self) -> None:
        """
        Thread safe way of sending a repaint trigger to the input event loop.
        """
        if not self._is_running:
            # Don't schedule a redraw if we're not running.
            # Otherwise, `get_running_loop()` in `call_soon_threadsafe` can fail.
            # See: https://github.com/dbcli/mycli/issues/797
            return

        # `invalidate()` called if we don't have a loop yet (not running?), or
        # after the event loop was closed.
        if self.loop is None or self.loop.is_closed():
            return

        # Never schedule a second redraw, when a previous one has not yet been
        # executed. (This should protect against other threads calling
        # 'invalidate' many times, resulting in 100% CPU.)
        if self._invalidated:
            return
        else:
            self._invalidated = True

        # Trigger event.
        self.loop.call_soon_threadsafe(self.on_invalidate.fire)

        def redraw() -> None:
            self._invalidated = False
            self._redraw()

        def schedule_redraw() -> None:
            call_soon_threadsafe(
                redraw, max_postpone_time=self.max_render_postpone_time, loop=self.loop
            )

        if self.min_redraw_interval:
            # When a minimum redraw interval is set, wait minimum this amount
            # of time between redraws.
            diff = time.time() - self._last_redraw_time
            if diff < self.min_redraw_interval:

                async def redraw_in_future() -> None:
                    await sleep(cast(float, self.min_redraw_interval) - diff)
                    schedule_redraw()

                self.loop.call_soon_threadsafe(
                    lambda: self.create_background_task(redraw_in_future())
                )
            else:
                schedule_redraw()
        else:
            schedule_redraw()

    @property
    def invalidated(self) -> bool:
        "True when a redraw operation has been scheduled."
        return self._invalidated

    def _redraw(self, render_as_done: bool = False) -> None:
        """
        Render the command line again. (Not thread safe!) (From other threads,
        or if unsure, use :meth:`.Application.invalidate`.)

        :param render_as_done: make sure to put the cursor after the UI.
        """

        def run_in_context() -> None:
            # Only draw when no sub application was started.
            if self._is_running and not self._running_in_terminal:
                if self.min_redraw_interval:
                    self._last_redraw_time = time.time()

                # Render
                self.render_counter += 1
                self.before_render.fire()

                if render_as_done:
                    if self.erase_when_done:
                        self.renderer.erase()
                    else:
                        # Draw in 'done' state and reset renderer.
                        self.renderer.render(self, self.layout, is_done=render_as_done)
                else:
                    self.renderer.render(self, self.layout)

                self.layout.update_parents_relations()

                # Fire render event.
                self.after_render.fire()

                self._update_invalidate_events()

        # NOTE: We want to make sure this Application is the active one. The
        #       invalidate function is often called from a context where this
        #       application is not the active one. (Like the
        #       `PromptSession._auto_refresh_context`).
        #       We copy the context in case the context was already active, to
        #       prevent RuntimeErrors. (The rendering is not supposed to change
        #       any context variables.)
        if self.context is not None:
            self.context.copy().run(run_in_context)

    def _start_auto_refresh_task(self) -> None:
        """
        Start a while/true loop in the background for automatic invalidation of
        the UI.
        """
        if self.refresh_interval is not None and self.refresh_interval != 0:

            async def auto_refresh(refresh_interval: float) -> None:
                while True:
                    await sleep(refresh_interval)
                    self.invalidate()

            self.create_background_task(auto_refresh(self.refresh_interval))

    def _update_invalidate_events(self) -> None:
        """
        Make sure to attach 'invalidate' handlers to all invalidate events in
        the UI.
        """
        # Remove all the original event handlers. (Components can be removed
        # from the UI.)
        for ev in self._invalidate_events:
            ev -= self._invalidate_handler

        # Gather all new events.
        # (All controls are able to invalidate themselves.)
        def gather_events() -> Iterable[Event[object]]:
            for c in self.layout.find_all_controls():
                yield from c.get_invalidate_events()

        self._invalidate_events = list(gather_events())

        for ev in self._invalidate_events:
            ev += self._invalidate_handler

    def _invalidate_handler(self, sender: object) -> None:
        """
        Handler for invalidate events coming from UIControls.

        (This handles the difference in signature between event handler and
        `self.invalidate`. It also needs to be a method -not a nested
        function-, so that we can remove it again .)
        """
        self.invalidate()

    def _on_resize(self) -> None:
        """
        When the window size changes, we erase the current output and request
        again the cursor position. When the CPR answer arrives, the output is
        drawn again.
        """
        # Erase, request position (when cursor is at the start position)
        # and redraw again. -- The order is important.
        self.renderer.erase(leave_alternate_screen=False)
        self._request_absolute_cursor_position()
        self._redraw()

    def _pre_run(self, pre_run: Callable[[], None] | None = None) -> None:
        """
        Called during `run`.

        `self.future` should be set to the new future at the point where this
        is called in order to avoid data races. `pre_run` can be used to set a
        `threading.Event` to synchronize with UI termination code, running in
        another thread that would call `Application.exit`. (See the progress
        bar code for an example.)
        """
        if pre_run:
            pre_run()

        # Process registered "pre_run_callables" and clear list.
        for c in self.pre_run_callables:
            c()
        del self.pre_run_callables[:]

    async def run_async(
        self,
        pre_run: Callable[[], None] | None = None,
        set_exception_handler: bool = True,
        handle_sigint: bool = True,
        slow_callback_duration: float = 0.5,
    ) -> _AppResult:
        """
        Run the prompt_toolkit :class:`~prompt_toolkit.application.Application`
        until :meth:`~prompt_toolkit.application.Application.exit` has been
        called. Return the value that was passed to
        :meth:`~prompt_toolkit.application.Application.exit`.

        This is the main entry point for a prompt_toolkit
        :class:`~prompt_toolkit.application.Application` and usually the only
        place where the event loop is actually running.

        :param pre_run: Optional callable, which is called right after the
            "reset" of the application.
        :param set_exception_handler: When set, in case of an exception, go out
            of the alternate screen and hide the application, display the
            exception, and wait for the user to press ENTER.
        :param handle_sigint: Handle SIGINT signal if possible. This will call
            the `<sigint>` key binding when a SIGINT is received. (This only
            works in the main thread.)
        :param slow_callback_duration: Display warnings if code scheduled in
            the asyncio event loop takes more time than this. The asyncio
            default of `0.1` is sometimes not sufficient on a slow system,
            because exceptionally, the drawing of the app, which happens in the
            event loop, can take a bit longer from time to time.
        """
        assert not self._is_running, "Application is already running."

        if not in_main_thread() or sys.platform == "win32":
            # Handling signals in other threads is not supported.
            # Also on Windows, `add_signal_handler(signal.SIGINT, ...)` raises
            # `NotImplementedError`.
            # See: https://github.com/prompt-toolkit/python-prompt-toolkit/issues/1553
            handle_sigint = False

        async def _run_async(f: asyncio.Future[_AppResult]) -> _AppResult:
            context = contextvars.copy_context()
            self.context = context

            # Counter for cancelling 'flush' timeouts. Every time when a key is
            # pressed, we start a 'flush' timer for flushing our escape key. But
            # when any subsequent input is received, a new timer is started and
            # the current timer will be ignored.
            flush_task: asyncio.Task[None] | None = None

            # Reset.
            # (`self.future` needs to be set when `pre_run` is called.)
            self.reset()
            self._pre_run(pre_run)

            # Feed type ahead input first.
            self.key_processor.feed_multiple(get_typeahead(self.input))
            self.key_processor.process_keys()

            def read_from_input() -> None:
                nonlocal flush_task

                # Ignore when we aren't running anymore. This callback will
                # removed from the loop next time. (It could be that it was
                # still in the 'tasks' list of the loop.)
                # Except: if we need to process incoming CPRs.
                if not self._is_running and not self.renderer.waiting_for_cpr:
                    return

                # Get keys from the input object.
                keys = self.input.read_keys()

                # Feed to key processor.
                self.key_processor.feed_multiple(keys)
                self.key_processor.process_keys()

                # Quit when the input stream was closed.
                if self.input.closed:
                    if not f.done():
                        f.set_exception(EOFError)
                else:
                    # Automatically flush keys.
                    if flush_task:
                        flush_task.cancel()
                    flush_task = self.create_background_task(auto_flush_input())

            def read_from_input_in_context() -> None:
                # Ensure that key bindings callbacks are always executed in the
                # current context. This is important when key bindings are
                # accessing contextvars. (These callbacks are currently being
                # called from a different context. Underneath,
                # `loop.add_reader` is used to register the stdin FD.)
                # (We copy the context to avoid a `RuntimeError` in case the
                # context is already active.)
                context.copy().run(read_from_input)

            async def auto_flush_input() -> None:
                # Flush input after timeout.
                # (Used for flushing the enter key.)
                # This sleep can be cancelled, in that case we won't flush yet.
                await sleep(self.ttimeoutlen)
                flush_input()

            def flush_input() -> None:
                if not self.is_done:
                    # Get keys, and feed to key processor.
                    keys = self.input.flush_keys()
                    self.key_processor.feed_multiple(keys)
                    self.key_processor.process_keys()

                    if self.input.closed:
                        f.set_exception(EOFError)

            # Enter raw mode, attach input and attach WINCH event handler.
            with self.input.raw_mode(), self.input.attach(
                read_from_input_in_context
            ), attach_winch_signal_handler(self._on_resize):
                # Draw UI.
                self._request_absolute_cursor_position()
                self._redraw()
                self._start_auto_refresh_task()

                self.create_background_task(self._poll_output_size())

                # Wait for UI to finish.
                try:
                    result = await f
                finally:
                    # In any case, when the application finishes.
                    # (Successful, or because of an error.)
                    try:
                        self._redraw(render_as_done=True)
                    finally:
                        # _redraw has a good chance to fail if it calls widgets
                        # with bad code. Make sure to reset the renderer
                        # anyway.
                        self.renderer.reset()

                        # Unset `is_running`, this ensures that possibly
                        # scheduled draws won't paint during the following
                        # yield.
                        self._is_running = False

                        # Detach event handlers for invalidate events.
                        # (Important when a UIControl is embedded in multiple
                        # applications, like ptterm in pymux. An invalidate
                        # should not trigger a repaint in terminated
                        # applications.)
                        for ev in self._invalidate_events:
                            ev -= self._invalidate_handler
                        self._invalidate_events = []

                        # Wait for CPR responses.
                        if self.output.responds_to_cpr:
                            await self.renderer.wait_for_cpr_responses()

                        # Wait for the run-in-terminals to terminate.
                        previous_run_in_terminal_f = self._running_in_terminal_f

                        if previous_run_in_terminal_f:
                            await previous_run_in_terminal_f

                        # Store unprocessed input as typeahead for next time.
                        store_typeahead(self.input, self.key_processor.empty_queue())

                return result

        @contextmanager
        def set_loop() -> Iterator[AbstractEventLoop]:
            loop = get_running_loop()
            self.loop = loop
            self._loop_thread = threading.current_thread()

            try:
                yield loop
            finally:
                self.loop = None
                self._loop_thread = None

        @contextmanager
        def set_is_running() -> Iterator[None]:
            self._is_running = True
            try:
                yield
            finally:
                self._is_running = False

        @contextmanager
        def set_handle_sigint(loop: AbstractEventLoop) -> Iterator[None]:
            if handle_sigint:
                with _restore_sigint_from_ctypes():
                    # save sigint handlers (python and os level)
                    # See: https://github.com/prompt-toolkit/python-prompt-toolkit/issues/1576
                    loop.add_signal_handler(
                        signal.SIGINT,
                        lambda *_: loop.call_soon_threadsafe(
                            self.key_processor.send_sigint
                        ),
                    )
                    try:
                        yield
                    finally:
                        loop.remove_signal_handler(signal.SIGINT)
            else:
                yield

        @contextmanager
        def set_exception_handler_ctx(loop: AbstractEventLoop) -> Iterator[None]:
            if set_exception_handler:
                previous_exc_handler = loop.get_exception_handler()
                loop.set_exception_handler(self._handle_exception)
                try:
                    yield
                finally:
                    loop.set_exception_handler(previous_exc_handler)

            else:
                yield

        @contextmanager
        def set_callback_duration(loop: AbstractEventLoop) -> Iterator[None]:
            # Set slow_callback_duration.
            original_slow_callback_duration = loop.slow_callback_duration
            loop.slow_callback_duration = slow_callback_duration
            try:
                yield
            finally:
                # Reset slow_callback_duration.
                loop.slow_callback_duration = original_slow_callback_duration

        @contextmanager
        def create_future(
            loop: AbstractEventLoop,
        ) -> Iterator[asyncio.Future[_AppResult]]:
            f = loop.create_future()
            self.future = f  # XXX: make sure to set this before calling '_redraw'.

            try:
                yield f
            finally:
                # Also remove the Future again. (This brings the
                # application back to its initial state, where it also
                # doesn't have a Future.)
                self.future = None

        with ExitStack() as stack:
            stack.enter_context(set_is_running())

            # Make sure to set `_invalidated` to `False` to begin with,
            # otherwise we're not going to paint anything. This can happen if
            # this application had run before on a different event loop, and a
            # paint was scheduled using `call_soon_threadsafe` with
            # `max_postpone_time`.
            self._invalidated = False

            loop = stack.enter_context(set_loop())

            stack.enter_context(set_handle_sigint(loop))
            stack.enter_context(set_exception_handler_ctx(loop))
            stack.enter_context(set_callback_duration(loop))
            stack.enter_context(set_app(self))
            stack.enter_context(self._enable_breakpointhook())

            f = stack.enter_context(create_future(loop))

            try:
                return await _run_async(f)
            finally:
                # Wait for the background tasks to be done. This needs to
                # go in the finally! If `_run_async` raises
                # `KeyboardInterrupt`, we still want to wait for the
                # background tasks.
                await self.cancel_and_wait_for_background_tasks()

        # The `ExitStack` above is defined in typeshed in a way that it can
        # swallow exceptions. Without next line, mypy would think that there's
        # a possibility we don't return here. See:
        # https://github.com/python/mypy/issues/7726
        assert False, "unreachable"

    def run(
        self,
        pre_run: Callable[[], None] | None = None,
        set_exception_handler: bool = True,
        handle_sigint: bool = True,
        in_thread: bool = False,
        inputhook: InputHook | None = None,
    ) -> _AppResult:
        """
        A blocking 'run' call that waits until the UI is finished.

        This will run the application in a fresh asyncio event loop.

        :param pre_run: Optional callable, which is called right after the
            "reset" of the application.
        :param set_exception_handler: When set, in case of an exception, go out
            of the alternate screen and hide the application, display the
            exception, and wait for the user to press ENTER.
        :param in_thread: When true, run the application in a background
            thread, and block the current thread until the application
            terminates. This is useful if we need to be sure the application
            won't use the current event loop (asyncio does not support nested
            event loops). A new event loop will be created in this background
            thread, and that loop will also be closed when the background
            thread terminates. When this is used, it's especially important to
            make sure that all asyncio background tasks are managed through
            `get_appp().create_background_task()`, so that unfinished tasks are
            properly cancelled before the event loop is closed. This is used
            for instance in ptpython.
        :param handle_sigint: Handle SIGINT signal. Call the key binding for
            `Keys.SIGINT`. (This only works in the main thread.)
        """
        if in_thread:
            result: _AppResult
            exception: BaseException | None = None

            def run_in_thread() -> None:
                nonlocal result, exception
                try:
                    result = self.run(
                        pre_run=pre_run,
                        set_exception_handler=set_exception_handler,
                        # Signal handling only works in the main thread.
                        handle_sigint=False,
                        inputhook=inputhook,
                    )
                except BaseException as e:
                    exception = e

            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()

            if exception is not None:
                raise exception
            return result

        coro = self.run_async(
            pre_run=pre_run,
            set_exception_handler=set_exception_handler,
            handle_sigint=handle_sigint,
        )

        def _called_from_ipython() -> bool:
            try:
                return (
                    sys.modules["IPython"].version_info < (8, 18, 0, "")
                    and "IPython/terminal/interactiveshell.py"
                    in sys._getframe(3).f_code.co_filename
                )
            except BaseException:
                return False

        if inputhook is not None:
            # Create new event loop with given input hook and run the app.
            # In Python 3.12, we can use asyncio.run(loop_factory=...)
            # For now, use `run_until_complete()`.
            loop = new_eventloop_with_inputhook(inputhook)
            result = loop.run_until_complete(coro)
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
            return result

        elif _called_from_ipython():
            # workaround to make input hooks work for IPython until
            # https://github.com/ipython/ipython/pull/14241 is merged.
            # IPython was setting the input hook by installing an event loop
            # previously.
            try:
                # See whether a loop was installed already. If so, use that.
                # That's required for the input hooks to work, they are
                # installed using `set_event_loop`.
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No loop installed. Run like usual.
                return asyncio.run(coro)
            else:
                # Use existing loop.
                return loop.run_until_complete(coro)

        else:
            # No loop installed. Run like usual.
            return asyncio.run(coro)

    def _handle_exception(
        self, loop: AbstractEventLoop, context: dict[str, Any]
    ) -> None:
        """
        Handler for event loop exceptions.
        This will print the exception, using run_in_terminal.
        """
        # For Python 2: we have to get traceback at this point, because
        # we're still in the 'except:' block of the event loop where the
        # traceback is still available. Moving this code in the
        # 'print_exception' coroutine will loose the exception.
        tb = get_traceback_from_context(context)
        formatted_tb = "".join(format_tb(tb))

        async def in_term() -> None:
            async with in_terminal():
                # Print output. Similar to 'loop.default_exception_handler',
                # but don't use logger. (This works better on Python 2.)
                print("\nUnhandled exception in event loop:")
                print(formatted_tb)
                print("Exception {}".format(context.get("exception")))

                await _do_wait_for_enter("Press ENTER to continue...")

        ensure_future(in_term())

    @contextmanager
    def _enable_breakpointhook(self) -> Generator[None, None, None]:
        """
        Install our custom breakpointhook for the duration of this context
        manager. (We will only install the hook if no other custom hook was
        set.)
        """
        if sys.breakpointhook == sys.__breakpointhook__:
            sys.breakpointhook = self._breakpointhook

            try:
                yield
            finally:
                sys.breakpointhook = sys.__breakpointhook__
        else:
            yield

    def _breakpointhook(self, *a: object, **kw: object) -> None:
        """
        Breakpointhook which uses PDB, but ensures that the application is
        hidden and input echoing is restored during each debugger dispatch.

        This can be called from any thread. In any case, the application's
        event loop will be blocked while the PDB input is displayed. The event
        will continue after leaving the debugger.
        """
        app = self
        # Inline import on purpose. We don't want to import pdb, if not needed.
        import pdb
        from types import FrameType

        TraceDispatch = Callable[[FrameType, str, Any], Any]

        @contextmanager
        def hide_app_from_eventloop_thread() -> Generator[None, None, None]:
            """Stop application if `__breakpointhook__` is called from within
            the App's event loop."""
            # Hide application.
            app.renderer.erase()

            # Detach input and dispatch to debugger.
            with app.input.detach():
                with app.input.cooked_mode():
                    yield

            # Note: we don't render the application again here, because
            # there's a good chance that there's a breakpoint on the next
            # line. This paint/erase cycle would move the PDB prompt back
            # to the middle of the screen.

        @contextmanager
        def hide_app_from_other_thread() -> Generator[None, None, None]:
            """Stop application if `__breakpointhook__` is called from a
            thread other than the App's event loop."""
            ready = threading.Event()
            done = threading.Event()

            async def in_loop() -> None:
                # from .run_in_terminal import in_terminal
                # async with in_terminal():
                #     ready.set()
                #     await asyncio.get_running_loop().run_in_executor(None, done.wait)
                #     return

                # Hide application.
                app.renderer.erase()

                # Detach input and dispatch to debugger.
                with app.input.detach():
                    with app.input.cooked_mode():
                        ready.set()
                        # Here we block the App's event loop thread until the
                        # debugger resumes. We could have used `with
                        # run_in_terminal.in_terminal():` like the commented
                        # code above, but it seems to work better if we
                        # completely stop the main event loop while debugging.
                        done.wait()

            self.create_background_task(in_loop())
            ready.wait()
            try:
                yield
            finally:
                done.set()

        class CustomPdb(pdb.Pdb):
            def trace_dispatch(
                self, frame: FrameType, event: str, arg: Any
            ) -> TraceDispatch:
                if app._loop_thread is None:
                    return super().trace_dispatch(frame, event, arg)

                if app._loop_thread == threading.current_thread():
                    with hide_app_from_eventloop_thread():
                        return super().trace_dispatch(frame, event, arg)

                with hide_app_from_other_thread():
                    return super().trace_dispatch(frame, event, arg)

        frame = sys._getframe().f_back
        CustomPdb(stdout=sys.__stdout__).set_trace(frame)

    def create_background_task(
        self, coroutine: Coroutine[Any, Any, None]
    ) -> asyncio.Task[None]:
        """
        Start a background task (coroutine) for the running application. When
        the `Application` terminates, unfinished background tasks will be
        cancelled.

        Given that we still support Python versions before 3.11, we can't use
        task groups (and exception groups), because of that, these background
        tasks are not allowed to raise exceptions. If they do, we'll call the
        default exception handler from the event loop.

        If at some point, we have Python 3.11 as the minimum supported Python
        version, then we can use a `TaskGroup` (with the lifetime of
        `Application.run_async()`, and run run the background tasks in there.

        This is not threadsafe.
        """
        loop = self.loop or get_running_loop()
        task: asyncio.Task[None] = loop.create_task(coroutine)
        self._background_tasks.add(task)

        task.add_done_callback(self._on_background_task_done)
        return task

    def _on_background_task_done(self, task: asyncio.Task[None]) -> None:
        """
        Called when a background task completes. Remove it from
        `_background_tasks`, and handle exceptions if any.
        """
        self._background_tasks.discard(task)

        if task.cancelled():
            return

        exc = task.exception()
        if exc is not None:
            get_running_loop().call_exception_handler(
                {
                    "message": f"prompt_toolkit.Application background task {task!r} "
                    "raised an unexpected exception.",
                    "exception": exc,
                    "task": task,
                }
            )

    async def cancel_and_wait_for_background_tasks(self) -> None:
        """
        Cancel all background tasks, and wait for the cancellation to complete.
        If any of the background tasks raised an exception, this will also
        propagate the exception.

        (If we had nurseries like Trio, this would be the `__aexit__` of a
        nursery.)
        """
        for task in self._background_tasks:
            task.cancel()

        # Wait until the cancellation of the background tasks completes.
        # `asyncio.wait()` does not propagate exceptions raised within any of
        # these tasks, which is what we want. Otherwise, we can't distinguish
        # between a `CancelledError` raised in this task because it got
        # cancelled, and a `CancelledError` raised on this `await` checkpoint,
        # because *we* got cancelled during the teardown of the application.
        # (If we get cancelled here, then it's important to not suppress the
        # `CancelledError`, and have it propagate.)
        # NOTE: Currently, if we get cancelled at this point then we can't wait
        #       for the cancellation to complete (in the future, we should be
        #       using anyio or Python's 3.11 TaskGroup.)
        #       Also, if we had exception groups, we could propagate an
        #       `ExceptionGroup` if something went wrong here. Right now, we
        #       don't propagate exceptions, but have them printed in
        #       `_on_background_task_done`.
        if len(self._background_tasks) > 0:
            await asyncio.wait(
                self._background_tasks, timeout=None, return_when=asyncio.ALL_COMPLETED
            )

    async def _poll_output_size(self) -> None:
        """
        Coroutine for polling the terminal dimensions.

        Useful for situations where `attach_winch_signal_handler` is not sufficient:
        - If we are not running in the main thread.
        - On Windows.
        """
        size: Size | None = None
        interval = self.terminal_size_polling_interval

        if interval is None:
            return

        while True:
            await asyncio.sleep(interval)
            new_size = self.output.get_size()

            if size is not None and new_size != size:
                self._on_resize()
            size = new_size

    def cpr_not_supported_callback(self) -> None:
        """
        Called when we don't receive the cursor position response in time.
        """
        if not self.output.responds_to_cpr:
            return  # We know about this already.

        def in_terminal() -> None:
            self.output.write(
                "WARNING: your terminal doesn't support cursor position requests (CPR).\r\n"
            )
            self.output.flush()

        run_in_terminal(in_terminal)

    @overload
    def exit(self) -> None:
        "Exit without arguments."

    @overload
    def exit(self, *, result: _AppResult, style: str = "") -> None:
        "Exit with `_AppResult`."

    @overload
    def exit(
        self, *, exception: BaseException | type[BaseException], style: str = ""
    ) -> None:
        "Exit with exception."

    def exit(
        self,
        result: _AppResult | None = None,
        exception: BaseException | type[BaseException] | None = None,
        style: str = "",
    ) -> None:
        """
        Exit application.

        .. note::

            If `Application.exit` is called before `Application.run()` is
            called, then the `Application` won't exit (because the
            `Application.future` doesn't correspond to the current run). Use a
            `pre_run` hook and an event to synchronize the closing if there's a
            chance this can happen.

        :param result: Set this result for the application.
        :param exception: Set this exception as the result for an application. For
            a prompt, this is often `EOFError` or `KeyboardInterrupt`.
        :param style: Apply this style on the whole content when quitting,
            often this is 'class:exiting' for a prompt. (Used when
            `erase_when_done` is not set.)
        """
        assert result is None or exception is None

        if self.future is None:
            raise Exception("Application is not running. Application.exit() failed.")

        if self.future.done():
            raise Exception("Return value already set. Application.exit() failed.")

        self.exit_style = style

        if exception is not None:
            self.future.set_exception(exception)
        else:
            self.future.set_result(cast(_AppResult, result))

    def _request_absolute_cursor_position(self) -> None:
        """
        Send CPR request.
        """
        # Note: only do this if the input queue is not empty, and a return
        # value has not been set. Otherwise, we won't be able to read the
        # response anyway.
        if not self.key_processor.input_queue and not self.is_done:
            self.renderer.request_absolute_cursor_position()

    async def run_system_command(
        self,
        command: str,
        wait_for_enter: bool = True,
        display_before_text: AnyFormattedText = "",
        wait_text: str = "Press ENTER to continue...",
    ) -> None:
        """
        Run system command (While hiding the prompt. When finished, all the
        output will scroll above the prompt.)

        :param command: Shell command to be executed.
        :param wait_for_enter: FWait for the user to press enter, when the
            command is finished.
        :param display_before_text: If given, text to be displayed before the
            command executes.
        :return: A `Future` object.
        """
        async with in_terminal():
            # Try to use the same input/output file descriptors as the one,
            # used to run this application.
            try:
                input_fd = self.input.fileno()
            except AttributeError:
                input_fd = sys.stdin.fileno()
            try:
                output_fd = self.output.fileno()
            except AttributeError:
                output_fd = sys.stdout.fileno()

            # Run sub process.
            def run_command() -> None:
                self.print_text(display_before_text)
                p = Popen(command, shell=True, stdin=input_fd, stdout=output_fd)
                p.wait()

            await run_in_executor_with_context(run_command)

            # Wait for the user to press enter.
            if wait_for_enter:
                await _do_wait_for_enter(wait_text)

    def suspend_to_background(self, suspend_group: bool = True) -> None:
        """
        (Not thread safe -- to be called from inside the key bindings.)
        Suspend process.

        :param suspend_group: When true, suspend the whole process group.
            (This is the default, and probably what you want.)
        """
        # Only suspend when the operating system supports it.
        # (Not on Windows.)
        if _SIGTSTP is not None:

            def run() -> None:
                signal = cast(int, _SIGTSTP)
                # Send `SIGTSTP` to own process.
                # This will cause it to suspend.

                # Usually we want the whole process group to be suspended. This
                # handles the case when input is piped from another process.
                if suspend_group:
                    os.kill(0, signal)
                else:
                    os.kill(os.getpid(), signal)

            run_in_terminal(run)

    def print_text(
        self, text: AnyFormattedText, style: BaseStyle | None = None
    ) -> None:
        """
        Print a list of (style_str, text) tuples to the output.
        (When the UI is running, this method has to be called through
        `run_in_terminal`, otherwise it will destroy the UI.)

        :param text: List of ``(style_str, text)`` tuples.
        :param style: Style class to use. Defaults to the active style in the CLI.
        """
        print_formatted_text(
            output=self.output,
            formatted_text=text,
            style=style or self._merged_style,
            color_depth=self.color_depth,
            style_transformation=self.style_transformation,
        )

    @property
    def is_running(self) -> bool:
        "`True` when the application is currently active/running."
        return self._is_running

    @property
    def is_done(self) -> bool:
        if self.future:
            return self.future.done()
        return False

    def get_used_style_strings(self) -> list[str]:
        """
        Return a list of used style strings. This is helpful for debugging, and
        for writing a new `Style`.
        """
        attrs_for_style = self.renderer._attrs_for_style

        if attrs_for_style:
            return sorted(
                re.sub(r"\s+", " ", style_str).strip()
                for style_str in attrs_for_style.keys()
            )

        return []


class _CombinedRegistry(KeyBindingsBase):
    """
    The `KeyBindings` of key bindings for a `Application`.
    This merges the global key bindings with the one of the current user
    control.
    """

    def __init__(self, app: Application[_AppResult]) -> None:
        self.app = app
        self._cache: SimpleCache[
            tuple[Window, frozenset[UIControl]], KeyBindingsBase
        ] = SimpleCache()

    @property
    def _version(self) -> Hashable:
        """Not needed - this object is not going to be wrapped in another
        KeyBindings object."""
        raise NotImplementedError

    @property
    def bindings(self) -> list[Binding]:
        """Not needed - this object is not going to be wrapped in another
        KeyBindings object."""
        raise NotImplementedError

    def _create_key_bindings(
        self, current_window: Window, other_controls: list[UIControl]
    ) -> KeyBindingsBase:
        """
        Create a `KeyBindings` object that merges the `KeyBindings` from the
        `UIControl` with all the parent controls and the global key bindings.
        """
        key_bindings = []
        collected_containers = set()

        # Collect key bindings from currently focused control and all parent
        # controls. Don't include key bindings of container parent controls.
        container: Container = current_window
        while True:
            collected_containers.add(container)
            kb = container.get_key_bindings()
            if kb is not None:
                key_bindings.append(kb)

            if container.is_modal():
                break

            parent = self.app.layout.get_parent(container)
            if parent is None:
                break
            else:
                container = parent

        # Include global bindings (starting at the top-model container).
        for c in walk(container):
            if c not in collected_containers:
                kb = c.get_key_bindings()
                if kb is not None:
                    key_bindings.append(GlobalOnlyKeyBindings(kb))

        # Add App key bindings
        if self.app.key_bindings:
            key_bindings.append(self.app.key_bindings)

        # Add mouse bindings.
        key_bindings.append(
            ConditionalKeyBindings(
                self.app._page_navigation_bindings,
                self.app.enable_page_navigation_bindings,
            )
        )
        key_bindings.append(self.app._default_bindings)

        # Reverse this list. The current control's key bindings should come
        # last. They need priority.
        key_bindings = key_bindings[::-1]

        return merge_key_bindings(key_bindings)

    @property
    def _key_bindings(self) -> KeyBindingsBase:
        current_window = self.app.layout.current_window
        other_controls = list(self.app.layout.find_all_controls())
        key = current_window, frozenset(other_controls)

        return self._cache.get(
            key, lambda: self._create_key_bindings(current_window, other_controls)
        )

    def get_bindings_for_keys(self, keys: KeysTuple) -> list[Binding]:
        return self._key_bindings.get_bindings_for_keys(keys)

    def get_bindings_starting_with_keys(self, keys: KeysTuple) -> list[Binding]:
        return self._key_bindings.get_bindings_starting_with_keys(keys)


async def _do_wait_for_enter(wait_text: AnyFormattedText) -> None:
    """
    Create a sub application to wait for the enter key press.
    This has two advantages over using 'input'/'raw_input':
    - This will share the same input/output I/O.
    - This doesn't block the event loop.
    """
    from prompt_toolkit.shortcuts import PromptSession

    key_bindings = KeyBindings()

    @key_bindings.add("enter")
    def _ok(event: E) -> None:
        event.app.exit()

    @key_bindings.add(Keys.Any)
    def _ignore(event: E) -> None:
        "Disallow typing."
        pass

    session: PromptSession[None] = PromptSession(
        message=wait_text, key_bindings=key_bindings
    )
    try:
        await session.app.run_async()
    except KeyboardInterrupt:
        pass  # Control-c pressed. Don't propagate this error.


@contextmanager
def attach_winch_signal_handler(
    handler: Callable[[], None],
) -> Generator[None, None, None]:
    """
    Attach the given callback as a WINCH signal handler within the context
    manager. Restore the original signal handler when done.

    The `Application.run` method will register SIGWINCH, so that it will
    properly repaint when the terminal window resizes. However, using
    `run_in_terminal`, we can temporarily send an application to the
    background, and run an other app in between, which will then overwrite the
    SIGWINCH. This is why it's important to restore the handler when the app
    terminates.
    """
    # The tricky part here is that signals are registered in the Unix event
    # loop with a wakeup fd, but another application could have registered
    # signals using signal.signal directly. For now, the implementation is
    # hard-coded for the `asyncio.unix_events._UnixSelectorEventLoop`.

    # No WINCH? Then don't do anything.
    sigwinch = getattr(signal, "SIGWINCH", None)
    if sigwinch is None or not in_main_thread():
        yield
        return

    # Keep track of the previous handler.
    # (Only UnixSelectorEventloop has `_signal_handlers`.)
    loop = get_running_loop()
    previous_winch_handler = getattr(loop, "_signal_handlers", {}).get(sigwinch)

    try:
        loop.add_signal_handler(sigwinch, handler)
        yield
    finally:
        # Restore the previous signal handler.
        loop.remove_signal_handler(sigwinch)
        if previous_winch_handler is not None:
            loop.add_signal_handler(
                sigwinch,
                previous_winch_handler._callback,
                *previous_winch_handler._args,
            )


@contextmanager
def _restore_sigint_from_ctypes() -> Generator[None, None, None]:
    # The following functions are part of the stable ABI since python 3.2
    # See: https://docs.python.org/3/c-api/sys.html#c.PyOS_getsig
    # Inline import: these are not available on Pypy.
    try:
        from ctypes import c_int, c_void_p, pythonapi
    except ImportError:
        # Any of the above imports don't exist? Don't do anything here.
        yield
        return

    # PyOS_sighandler_t PyOS_getsig(int i)
    pythonapi.PyOS_getsig.restype = c_void_p
    pythonapi.PyOS_getsig.argtypes = (c_int,)

    # PyOS_sighandler_t PyOS_setsig(int i, PyOS_sighandler_t h)
    pythonapi.PyOS_setsig.restype = c_void_p
    pythonapi.PyOS_setsig.argtypes = (
        c_int,
        c_void_p,
    )

    sigint = signal.getsignal(signal.SIGINT)
    sigint_os = pythonapi.PyOS_getsig(signal.SIGINT)

    try:
        yield
    finally:
        if sigint is not None:
            signal.signal(signal.SIGINT, sigint)
        pythonapi.PyOS_setsig(signal.SIGINT, sigint_os)