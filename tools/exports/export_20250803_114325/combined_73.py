
# === NexusCore/openenv\Lib\site-packages\numpy\fft\_pocketfft.py ===
"""
Discrete Fourier Transforms

Routines in this module:

fft(a, n=None, axis=-1, norm="backward")
ifft(a, n=None, axis=-1, norm="backward")
rfft(a, n=None, axis=-1, norm="backward")
irfft(a, n=None, axis=-1, norm="backward")
hfft(a, n=None, axis=-1, norm="backward")
ihfft(a, n=None, axis=-1, norm="backward")
fftn(a, s=None, axes=None, norm="backward")
ifftn(a, s=None, axes=None, norm="backward")
rfftn(a, s=None, axes=None, norm="backward")
irfftn(a, s=None, axes=None, norm="backward")
fft2(a, s=None, axes=(-2,-1), norm="backward")
ifft2(a, s=None, axes=(-2, -1), norm="backward")
rfft2(a, s=None, axes=(-2,-1), norm="backward")
irfft2(a, s=None, axes=(-2, -1), norm="backward")

i = inverse transform
r = transform of purely real data
h = Hermite transform
n = n-dimensional transform
2 = 2-dimensional transform
(Note: 2D routines are just nD routines with different default
behavior.)

"""
__all__ = ['fft', 'ifft', 'rfft', 'irfft', 'hfft', 'ihfft', 'rfftn',
           'irfftn', 'rfft2', 'irfft2', 'fft2', 'ifft2', 'fftn', 'ifftn']

import functools
import warnings

from numpy._core import (
    asarray,
    conjugate,
    empty_like,
    overrides,
    reciprocal,
    result_type,
    sqrt,
    take,
)
from numpy.lib.array_utils import normalize_axis_index

from . import _pocketfft_umath as pfu

array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy.fft')


# `inv_norm` is a float by which the result of the transform needs to be
# divided. This replaces the original, more intuitive 'fct` parameter to avoid
# divisions by zero (or alternatively additional checks) in the case of
# zero-length axes during its computation.
def _raw_fft(a, n, axis, is_real, is_forward, norm, out=None):
    if n < 1:
        raise ValueError(f"Invalid number of FFT data points ({n}) specified.")

    # Calculate the normalization factor, passing in the array dtype to
    # avoid precision loss in the possible sqrt or reciprocal.
    if not is_forward:
        norm = _swap_direction(norm)

    real_dtype = result_type(a.real.dtype, 1.0)
    if norm is None or norm == "backward":
        fct = 1
    elif norm == "ortho":
        fct = reciprocal(sqrt(n, dtype=real_dtype))
    elif norm == "forward":
        fct = reciprocal(n, dtype=real_dtype)
    else:
        raise ValueError(f'Invalid norm value {norm}; should be "backward",'
                         '"ortho" or "forward".')

    n_out = n
    if is_real:
        if is_forward:
            ufunc = pfu.rfft_n_even if n % 2 == 0 else pfu.rfft_n_odd
            n_out = n // 2 + 1
        else:
            ufunc = pfu.irfft
    else:
        ufunc = pfu.fft if is_forward else pfu.ifft

    axis = normalize_axis_index(axis, a.ndim)

    if out is None:
        if is_real and not is_forward:  # irfft, complex in, real output.
            out_dtype = real_dtype
        else:  # Others, complex output.
            out_dtype = result_type(a.dtype, 1j)
        out = empty_like(a, shape=a.shape[:axis] + (n_out,) + a.shape[axis + 1:],
                         dtype=out_dtype)
    elif ((shape := getattr(out, "shape", None)) is not None
          and (len(shape) != a.ndim or shape[axis] != n_out)):
        raise ValueError("output array has wrong shape.")

    return ufunc(a, fct, axes=[(axis,), (), (axis,)], out=out)


_SWAP_DIRECTION_MAP = {"backward": "forward", None: "forward",
                       "ortho": "ortho", "forward": "backward"}


def _swap_direction(norm):
    try:
        return _SWAP_DIRECTION_MAP[norm]
    except KeyError:
        raise ValueError(f'Invalid norm value {norm}; should be "backward", '
                         '"ortho" or "forward".') from None


def _fft_dispatcher(a, n=None, axis=None, norm=None, out=None):
    return (a, out)


@array_function_dispatch(_fft_dispatcher)
def fft(a, n=None, axis=-1, norm=None, out=None):
    """
    Compute the one-dimensional discrete Fourier Transform.

    This function computes the one-dimensional *n*-point discrete Fourier
    Transform (DFT) with the efficient Fast Fourier Transform (FFT)
    algorithm [CT].

    Parameters
    ----------
    a : array_like
        Input array, can be complex.
    n : int, optional
        Length of the transformed axis of the output.
        If `n` is smaller than the length of the input, the input is cropped.
        If it is larger, the input is padded with zeros.  If `n` is not given,
        the length of the input along the axis specified by `axis` is used.
    axis : int, optional
        Axis over which to compute the FFT.  If not given, the last axis is
        used.
    norm : {"backward", "ortho", "forward"}, optional
        Normalization mode (see `numpy.fft`). Default is "backward".
        Indicates which direction of the forward/backward pair of transforms
        is scaled and with what normalization factor.

        .. versionadded:: 1.20.0

            The "backward", "forward" values were added.
    out : complex ndarray, optional
        If provided, the result will be placed in this array. It should be
        of the appropriate shape and dtype.

        .. versionadded:: 2.0.0

    Returns
    -------
    out : complex ndarray
        The truncated or zero-padded input, transformed along the axis
        indicated by `axis`, or the last one if `axis` is not specified.

    Raises
    ------
    IndexError
        If `axis` is not a valid axis of `a`.

    See Also
    --------
    numpy.fft : for definition of the DFT and conventions used.
    ifft : The inverse of `fft`.
    fft2 : The two-dimensional FFT.
    fftn : The *n*-dimensional FFT.
    rfftn : The *n*-dimensional FFT of real input.
    fftfreq : Frequency bins for given FFT parameters.

    Notes
    -----
    FFT (Fast Fourier Transform) refers to a way the discrete Fourier
    Transform (DFT) can be calculated efficiently, by using symmetries in the
    calculated terms.  The symmetry is highest when `n` is a power of 2, and
    the transform is therefore most efficient for these sizes.

    The DFT is defined, with the conventions used in this implementation, in
    the documentation for the `numpy.fft` module.

    References
    ----------
    .. [CT] Cooley, James W., and John W. Tukey, 1965, "An algorithm for the
            machine calculation of complex Fourier series," *Math. Comput.*
            19: 297-301.

    Examples
    --------
    >>> import numpy as np
    >>> np.fft.fft(np.exp(2j * np.pi * np.arange(8) / 8))
    array([-2.33486982e-16+1.14423775e-17j,  8.00000000e+00-1.25557246e-15j,
            2.33486982e-16+2.33486982e-16j,  0.00000000e+00+1.22464680e-16j,
           -1.14423775e-17+2.33486982e-16j,  0.00000000e+00+5.20784380e-16j,
            1.14423775e-17+1.14423775e-17j,  0.00000000e+00+1.22464680e-16j])

    In this example, real input has an FFT which is Hermitian, i.e., symmetric
    in the real part and anti-symmetric in the imaginary part, as described in
    the `numpy.fft` documentation:

    >>> import matplotlib.pyplot as plt
    >>> t = np.arange(256)
    >>> sp = np.fft.fft(np.sin(t))
    >>> freq = np.fft.fftfreq(t.shape[-1])
    >>> _ = plt.plot(freq, sp.real, freq, sp.imag)
    >>> plt.show()

    """
    a = asarray(a)
    if n is None:
        n = a.shape[axis]
    output = _raw_fft(a, n, axis, False, True, norm, out)
    return output


@array_function_dispatch(_fft_dispatcher)
def ifft(a, n=None, axis=-1, norm=None, out=None):
    """
    Compute the one-dimensional inverse discrete Fourier Transform.

    This function computes the inverse of the one-dimensional *n*-point
    discrete Fourier transform computed by `fft`.  In other words,
    ``ifft(fft(a)) == a`` to within numerical accuracy.
    For a general description of the algorithm and definitions,
    see `numpy.fft`.

    The input should be ordered in the same way as is returned by `fft`,
    i.e.,

    * ``a[0]`` should contain the zero frequency term,
    * ``a[1:n//2]`` should contain the positive-frequency terms,
    * ``a[n//2 + 1:]`` should contain the negative-frequency terms, in
      increasing order starting from the most negative frequency.

    For an even number of input points, ``A[n//2]`` represents the sum of
    the values at the positive and negative Nyquist frequencies, as the two
    are aliased together. See `numpy.fft` for details.

    Parameters
    ----------
    a : array_like
        Input array, can be complex.
    n : int, optional
        Length of the transformed axis of the output.
        If `n` is smaller than the length of the input, the input is cropped.
        If it is larger, the input is padded with zeros.  If `n` is not given,
        the length of the input along the axis specified by `axis` is used.
        See notes about padding issues.
    axis : int, optional
        Axis over which to compute the inverse DFT.  If not given, the last
        axis is used.
    norm : {"backward", "ortho", "forward"}, optional
        Normalization mode (see `numpy.fft`). Default is "backward".
        Indicates which direction of the forward/backward pair of transforms
        is scaled and with what normalization factor.

        .. versionadded:: 1.20.0

            The "backward", "forward" values were added.

    out : complex ndarray, optional
        If provided, the result will be placed in this array. It should be
        of the appropriate shape and dtype.

        .. versionadded:: 2.0.0

    Returns
    -------
    out : complex ndarray
        The truncated or zero-padded input, transformed along the axis
        indicated by `axis`, or the last one if `axis` is not specified.

    Raises
    ------
    IndexError
        If `axis` is not a valid axis of `a`.

    See Also
    --------
    numpy.fft : An introduction, with definitions and general explanations.
    fft : The one-dimensional (forward) FFT, of which `ifft` is the inverse
    ifft2 : The two-dimensional inverse FFT.
    ifftn : The n-dimensional inverse FFT.

    Notes
    -----
    If the input parameter `n` is larger than the size of the input, the input
    is padded by appending zeros at the end.  Even though this is the common
    approach, it might lead to surprising results.  If a different padding is
    desired, it must be performed before calling `ifft`.

    Examples
    --------
    >>> import numpy as np
    >>> np.fft.ifft([0, 4, 0, 0])
    array([ 1.+0.j,  0.+1.j, -1.+0.j,  0.-1.j]) # may vary

    Create and plot a band-limited signal with random phases:

    >>> import matplotlib.pyplot as plt
    >>> t = np.arange(400)
    >>> n = np.zeros((400,), dtype=complex)
    >>> n[40:60] = np.exp(1j*np.random.uniform(0, 2*np.pi, (20,)))
    >>> s = np.fft.ifft(n)
    >>> plt.plot(t, s.real, label='real')
    [<matplotlib.lines.Line2D object at ...>]
    >>> plt.plot(t, s.imag, '--', label='imaginary')
    [<matplotlib.lines.Line2D object at ...>]
    >>> plt.legend()
    <matplotlib.legend.Legend object at ...>
    >>> plt.show()

    """
    a = asarray(a)
    if n is None:
        n = a.shape[axis]
    output = _raw_fft(a, n, axis, False, False, norm, out=out)
    return output


@array_function_dispatch(_fft_dispatcher)
def rfft(a, n=None, axis=-1, norm=None, out=None):
    """
    Compute the one-dimensional discrete Fourier Transform for real input.

    This function computes the one-dimensional *n*-point discrete Fourier
    Transform (DFT) of a real-valued array by means of an efficient algorithm
    called the Fast Fourier Transform (FFT).

    Parameters
    ----------
    a : array_like
        Input array
    n : int, optional
        Number of points along transformation axis in the input to use.
        If `n` is smaller than the length of the input, the input is cropped.
        If it is larger, the input is padded with zeros. If `n` is not given,
        the length of the input along the axis specified by `axis` is used.
    axis : int, optional
        Axis over which to compute the FFT. If not given, the last axis is
        used.
    norm : {"backward", "ortho", "forward"}, optional
        Normalization mode (see `numpy.fft`). Default is "backward".
        Indicates which direction of the forward/backward pair of transforms
        is scaled and with what normalization factor.

        .. versionadded:: 1.20.0

            The "backward", "forward" values were added.

    out : complex ndarray, optional
        If provided, the result will be placed in this array. It should be
        of the appropriate shape and dtype.

        .. versionadded:: 2.0.0

    Returns
    -------
    out : complex ndarray
        The truncated or zero-padded input, transformed along the axis
        indicated by `axis`, or the last one if `axis` is not specified.
        If `n` is even, the length of the transformed axis is ``(n/2)+1``.
        If `n` is odd, the length is ``(n+1)/2``.

    Raises
    ------
    IndexError
        If `axis` is not a valid axis of `a`.

    See Also
    --------
    numpy.fft : For definition of the DFT and conventions used.
    irfft : The inverse of `rfft`.
    fft : The one-dimensional FFT of general (complex) input.
    fftn : The *n*-dimensional FFT.
    rfftn : The *n*-dimensional FFT of real input.

    Notes
    -----
    When the DFT is computed for purely real input, the output is
    Hermitian-symmetric, i.e. the negative frequency terms are just the complex
    conjugates of the corresponding positive-frequency terms, and the
    negative-frequency terms are therefore redundant.  This function does not
    compute the negative frequency terms, and the length of the transformed
    axis of the output is therefore ``n//2 + 1``.

    When ``A = rfft(a)`` and fs is the sampling frequency, ``A[0]`` contains
    the zero-frequency term 0*fs, which is real due to Hermitian symmetry.

    If `n` is even, ``A[-1]`` contains the term representing both positive
    and negative Nyquist frequency (+fs/2 and -fs/2), and must also be purely
    real. If `n` is odd, there is no term at fs/2; ``A[-1]`` contains
    the largest positive frequency (fs/2*(n-1)/n), and is complex in the
    general case.

    If the input `a` contains an imaginary part, it is silently discarded.

    Examples
    --------
    >>> import numpy as np
    >>> np.fft.fft([0, 1, 0, 0])
    array([ 1.+0.j,  0.-1.j, -1.+0.j,  0.+1.j]) # may vary
    >>> np.fft.rfft([0, 1, 0, 0])
    array([ 1.+0.j,  0.-1.j, -1.+0.j]) # may vary

    Notice how the final element of the `fft` output is the complex conjugate
    of the second element, for real input. For `rfft`, this symmetry is
    exploited to compute only the non-negative frequency terms.

    """
    a = asarray(a)
    if n is None:
        n = a.shape[axis]
    output = _raw_fft(a, n, axis, True, True, norm, out=out)
    return output


@array_function_dispatch(_fft_dispatcher)
def irfft(a, n=None, axis=-1, norm=None, out=None):
    """
    Computes the inverse of `rfft`.

    This function computes the inverse of the one-dimensional *n*-point
    discrete Fourier Transform of real input computed by `rfft`.
    In other words, ``irfft(rfft(a), len(a)) == a`` to within numerical
    accuracy. (See Notes below for why ``len(a)`` is necessary here.)

    The input is expected to be in the form returned by `rfft`, i.e. the
    real zero-frequency term followed by the complex positive frequency terms
    in order of increasing frequency.  Since the discrete Fourier Transform of
    real input is Hermitian-symmetric, the negative frequency terms are taken
    to be the complex conjugates of the corresponding positive frequency terms.

    Parameters
    ----------
    a : array_like
        The input array.
    n : int, optional
        Length of the transformed axis of the output.
        For `n` output points, ``n//2+1`` input points are necessary.  If the
        input is longer than this, it is cropped.  If it is shorter than this,
        it is padded with zeros.  If `n` is not given, it is taken to be
        ``2*(m-1)`` where ``m`` is the length of the input along the axis
        specified by `axis`.
    axis : int, optional
        Axis over which to compute the inverse FFT. If not given, the last
        axis is used.
    norm : {"backward", "ortho", "forward"}, optional
        Normalization mode (see `numpy.fft`). Default is "backward".
        Indicates which direction of the forward/backward pair of transforms
        is scaled and with what normalization factor.

        .. versionadded:: 1.20.0

            The "backward", "forward" values were added.

    out : ndarray, optional
        If provided, the result will be placed in this array. It should be
        of the appropriate shape and dtype.

        .. versionadded:: 2.0.0

    Returns
    -------
    out : ndarray
        The truncated or zero-padded input, transformed along the axis
        indicated by `axis`, or the last one if `axis` is not specified.
        The length of the transformed axis is `n`, or, if `n` is not given,
        ``2*(m-1)`` where ``m`` is the length of the transformed axis of the
        input. To get an odd number of output points, `n` must be specified.

    Raises
    ------
    IndexError
        If `axis` is not a valid axis of `a`.

    See Also
    --------
    numpy.fft : For definition of the DFT and conventions used.
    rfft : The one-dimensional FFT of real input, of which `irfft` is inverse.
    fft : The one-dimensional FFT.
    irfft2 : The inverse of the two-dimensional FFT of real input.
    irfftn : The inverse of the *n*-dimensional FFT of real input.

    Notes
    -----
    Returns the real valued `n`-point inverse discrete Fourier transform
    of `a`, where `a` contains the non-negative frequency terms of a
    Hermitian-symmetric sequence. `n` is the length of the result, not the
    input.

    If you specify an `n` such that `a` must be zero-padded or truncated, the
    extra/removed values will be added/removed at high frequencies. One can
    thus resample a series to `m` points via Fourier interpolation by:
    ``a_resamp = irfft(rfft(a), m)``.

    The correct interpretation of the hermitian input depends on the length of
    the original data, as given by `n`. This is because each input shape could
    correspond to either an odd or even length signal. By default, `irfft`
    assumes an even output length which puts the last entry at the Nyquist
    frequency; aliasing with its symmetric counterpart. By Hermitian symmetry,
    the value is thus treated as purely real. To avoid losing information, the
    correct length of the real input **must** be given.

    Examples
    --------
    >>> import numpy as np
    >>> np.fft.ifft([1, -1j, -1, 1j])
    array([0.+0.j,  1.+0.j,  0.+0.j,  0.+0.j]) # may vary
    >>> np.fft.irfft([1, -1j, -1])
    array([0.,  1.,  0.,  0.])

    Notice how the last term in the input to the ordinary `ifft` is the
    complex conjugate of the second term, and the output has zero imaginary
    part everywhere.  When calling `irfft`, the negative frequencies are not
    specified, and the output array is purely real.

    """
    a = asarray(a)
    if n is None:
        n = (a.shape[axis] - 1) * 2
    output = _raw_fft(a, n, axis, True, False, norm, out=out)
    return output


@array_function_dispatch(_fft_dispatcher)
def hfft(a, n=None, axis=-1, norm=None, out=None):
    """
    Compute the FFT of a signal that has Hermitian symmetry, i.e., a real
    spectrum.

    Parameters
    ----------
    a : array_like
        The input array.
    n : int, optional
        Length of the transformed axis of the output. For `n` output
        points, ``n//2 + 1`` input points are necessary.  If the input is
        longer than this, it is cropped.  If it is shorter than this, it is
        padded with zeros.  If `n` is not given, it is taken to be ``2*(m-1)``
        where ``m`` is the length of the input along the axis specified by
        `axis`.
    axis : int, optional
        Axis over which to compute the FFT. If not given, the last
        axis is used.
    norm : {"backward", "ortho", "forward"}, optional
        Normalization mode (see `numpy.fft`). Default is "backward".
        Indicates which direction of the forward/backward pair of transforms
        is scaled and with what normalization factor.

        .. versionadded:: 1.20.0

            The "backward", "forward" values were added.

    out : ndarray, optional
        If provided, the result will be placed in this array. It should be
        of the appropriate shape and dtype.

        .. versionadded:: 2.0.0

    Returns
    -------
    out : ndarray
        The truncated or zero-padded input, transformed along the axis
        indicated by `axis`, or the last one if `axis` is not specified.
        The length of the transformed axis is `n`, or, if `n` is not given,
        ``2*m - 2`` where ``m`` is the length of the transformed axis of
        the input. To get an odd number of output points, `n` must be
        specified, for instance as ``2*m - 1`` in the typical case,

    Raises
    ------
    IndexError
        If `axis` is not a valid axis of `a`.

    See also
    --------
    rfft : Compute the one-dimensional FFT for real input.
    ihfft : The inverse of `hfft`.

    Notes
    -----
    `hfft`/`ihfft` are a pair analogous to `rfft`/`irfft`, but for the
    opposite case: here the signal has Hermitian symmetry in the time
    domain and is real in the frequency domain. So here it's `hfft` for
    which you must supply the length of the result if it is to be odd.

    * even: ``ihfft(hfft(a, 2*len(a) - 2)) == a``, within roundoff error,
    * odd: ``ihfft(hfft(a, 2*len(a) - 1)) == a``, within roundoff error.

    The correct interpretation of the hermitian input depends on the length of
    the original data, as given by `n`. This is because each input shape could
    correspond to either an odd or even length signal. By default, `hfft`
    assumes an even output length which puts the last entry at the Nyquist
    frequency; aliasing with its symmetric counterpart. By Hermitian symmetry,
    the value is thus treated as purely real. To avoid losing information, the
    shape of the full signal **must** be given.

    Examples
    --------
    >>> import numpy as np
    >>> signal = np.array([1, 2, 3, 4, 3, 2])
    >>> np.fft.fft(signal)
    array([15.+0.j,  -4.+0.j,   0.+0.j,  -1.-0.j,   0.+0.j,  -4.+0.j]) # may vary
    >>> np.fft.hfft(signal[:4]) # Input first half of signal
    array([15.,  -4.,   0.,  -1.,   0.,  -4.])
    >>> np.fft.hfft(signal, 6)  # Input entire signal and truncate
    array([15.,  -4.,   0.,  -1.,   0.,  -4.])


    >>> signal = np.array([[1, 1.j], [-1.j, 2]])
    >>> np.conj(signal.T) - signal   # check Hermitian symmetry
    array([[ 0.-0.j,  -0.+0.j], # may vary
           [ 0.+0.j,  0.-0.j]])
    >>> freq_spectrum = np.fft.hfft(signal)
    >>> freq_spectrum
    array([[ 1.,  1.],
           [ 2., -2.]])

    """
    a = asarray(a)
    if n is None:
        n = (a.shape[axis] - 1) * 2
    new_norm = _swap_direction(norm)
    output = irfft(conjugate(a), n, axis, norm=new_norm, out=None)
    return output


@array_function_dispatch(_fft_dispatcher)
def ihfft(a, n=None, axis=-1, norm=None, out=None):
    """
    Compute the inverse FFT of a signal that has Hermitian symmetry.

    Parameters
    ----------
    a : array_like
        Input array.
    n : int, optional
        Length of the inverse FFT, the number of points along
        transformation axis in the input to use.  If `n` is smaller than
        the length of the input, the input is cropped.  If it is larger,
        the input is padded with zeros. If `n` is not given, the length of
        the input along the axis specified by `axis` is used.
    axis : int, optional
        Axis over which to compute the inverse FFT. If not given, the last
        axis is used.
    norm : {"backward", "ortho", "forward"}, optional
        Normalization mode (see `numpy.fft`). Default is "backward".
        Indicates which direction of the forward/backward pair of transforms
        is scaled and with what normalization factor.

        .. versionadded:: 1.20.0

            The "backward", "forward" values were added.

    out : complex ndarray, optional
        If provided, the result will be placed in this array. It should be
        of the appropriate shape and dtype.

        .. versionadded:: 2.0.0

    Returns
    -------
    out : complex ndarray
        The truncated or zero-padded input, transformed along the axis
        indicated by `axis`, or the last one if `axis` is not specified.
        The length of the transformed axis is ``n//2 + 1``.

    See also
    --------
    hfft, irfft

    Notes
    -----
    `hfft`/`ihfft` are a pair analogous to `rfft`/`irfft`, but for the
    opposite case: here the signal has Hermitian symmetry in the time
    domain and is real in the frequency domain. So here it's `hfft` for
    which you must supply the length of the result if it is to be odd:

    * even: ``ihfft(hfft(a, 2*len(a) - 2)) == a``, within roundoff error,
    * odd: ``ihfft(hfft(a, 2*len(a) - 1)) == a``, within roundoff error.

    Examples
    --------
    >>> import numpy as np
    >>> spectrum = np.array([ 15, -4, 0, -1, 0, -4])
    >>> np.fft.ifft(spectrum)
    array([1.+0.j,  2.+0.j,  3.+0.j,  4.+0.j,  3.+0.j,  2.+0.j]) # may vary
    >>> np.fft.ihfft(spectrum)
    array([ 1.-0.j,  2.-0.j,  3.-0.j,  4.-0.j]) # may vary

    """
    a = asarray(a)
    if n is None:
        n = a.shape[axis]
    new_norm = _swap_direction(norm)
    out = rfft(a, n, axis, norm=new_norm, out=out)
    return conjugate(out, out=out)


def _cook_nd_args(a, s=None, axes=None, invreal=0):
    if s is None:
        shapeless = True
        if axes is None:
            s = list(a.shape)
        else:
            s = take(a.shape, axes)
    else:
        shapeless = False
    s = list(s)
    if axes is None:
        if not shapeless:
            msg = ("`axes` should not be `None` if `s` is not `None` "
                   "(Deprecated in NumPy 2.0). In a future version of NumPy, "
                   "this will raise an error and `s[i]` will correspond to "
                   "the size along the transformed axis specified by "
                   "`axes[i]`. To retain current behaviour, pass a sequence "
                   "[0, ..., k-1] to `axes` for an array of dimension k.")
            warnings.warn(msg, DeprecationWarning, stacklevel=3)
        axes = list(range(-len(s), 0))
    if len(s) != len(axes):
        raise ValueError("Shape and axes have different lengths.")
    if invreal and shapeless:
        s[-1] = (a.shape[axes[-1]] - 1) * 2
    if None in s:
        msg = ("Passing an array containing `None` values to `s` is "
               "deprecated in NumPy 2.0 and will raise an error in "
               "a future version of NumPy. To use the default behaviour "
               "of the corresponding 1-D transform, pass the value matching "
               "the default for its `n` parameter. To use the default "
               "behaviour for every axis, the `s` argument can be omitted.")
        warnings.warn(msg, DeprecationWarning, stacklevel=3)
    # use the whole input array along axis `i` if `s[i] == -1`
    s = [a.shape[_a] if _s == -1 else _s for _s, _a in zip(s, axes)]
    return s, axes


def _raw_fftnd(a, s=None, axes=None, function=fft, norm=None, out=None):
    a = asarray(a)
    s, axes = _cook_nd_args(a, s, axes)
    itl = list(range(len(axes)))
    itl.reverse()
    for ii in itl:
        a = function(a, n=s[ii], axis=axes[ii], norm=norm, out=out)
    return a


def _fftn_dispatcher(a, s=None, axes=None, norm=None, out=None):
    return (a, out)


@array_function_dispatch(_fftn_dispatcher)
def fftn(a, s=None, axes=None, norm=None, out=None):
    """
    Compute the N-dimensional discrete Fourier Transform.

    This function computes the *N*-dimensional discrete Fourier Transform over
    any number of axes in an *M*-dimensional array by means of the Fast Fourier
    Transform (FFT).

    Parameters
    ----------
    a : array_like
        Input array, can be complex.
    s : sequence of ints, optional
        Shape (length of each transformed axis) of the output
        (``s[0]`` refers to axis 0, ``s[1]`` to axis 1, etc.).
        This corresponds to ``n`` for ``fft(x, n)``.
        Along any axis, if the given shape is smaller than that of the input,
        the input is cropped. If it is larger, the input is padded with zeros.

        .. versionchanged:: 2.0

            If it is ``-1``, the whole input is used (no padding/trimming).

        If `s` is not given, the shape of the input along the axes specified
        by `axes` is used.

        .. deprecated:: 2.0

            If `s` is not ``None``, `axes` must not be ``None`` either.

        .. deprecated:: 2.0

            `s` must contain only ``int`` s, not ``None`` values. ``None``
            values currently mean that the default value for ``n`` is used
            in the corresponding 1-D transform, but this behaviour is
            deprecated.

    axes : sequence of ints, optional
        Axes over which to compute the FFT.  If not given, the last ``len(s)``
        axes are used, or all axes if `s` is also not specified.
        Repeated indices in `axes` means that the transform over that axis is
        performed multiple times.

        .. deprecated:: 2.0

            If `s` is specified, the corresponding `axes` to be transformed
            must be explicitly specified too.

    norm : {"backward", "ortho", "forward"}, optional
        Normalization mode (see `numpy.fft`). Default is "backward".
        Indicates which direction of the forward/backward pair of transforms
        is scaled and with what normalization factor.

        .. versionadded:: 1.20.0

            The "backward", "forward" values were added.

    out : complex ndarray, optional
        If provided, the result will be placed in this array. It should be
        of the appropriate shape and dtype for all axes (and hence is
        incompatible with passing in all but the trivial ``s``).

        .. versionadded:: 2.0.0

    Returns
    -------
    out : complex ndarray
        The truncated or zero-padded input, transformed along the axes
        indicated by `axes`, or by a combination of `s` and `a`,
        as explained in the parameters section above.

    Raises
    ------
    ValueError
        If `s` and `axes` have different length.
    IndexError
        If an element of `axes` is larger than than the number of axes of `a`.

    See Also
    --------
    numpy.fft : Overall view of discrete Fourier transforms, with definitions
        and conventions used.
    ifftn : The inverse of `fftn`, the inverse *n*-dimensional FFT.
    fft : The one-dimensional FFT, with definitions and conventions used.
    rfftn : The *n*-dimensional FFT of real input.
    fft2 : The two-dimensional FFT.
    fftshift : Shifts zero-frequency terms to centre of array

    Notes
    -----
    The output, analogously to `fft`, contains the term for zero frequency in
    the low-order corner of all axes, the positive frequency terms in the
    first half of all axes, the term for the Nyquist frequency in the middle
    of all axes and the negative frequency terms in the second half of all
    axes, in order of decreasingly negative frequency.

    See `numpy.fft` for details, definitions and conventions used.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.mgrid[:3, :3, :3][0]
    >>> np.fft.fftn(a, axes=(1, 2))
    array([[[ 0.+0.j,   0.+0.j,   0.+0.j], # may vary
            [ 0.+0.j,   0.+0.j,   0.+0.j],
            [ 0.+0.j,   0.+0.j,   0.+0.j]],
           [[ 9.+0.j,   0.+0.j,   0.+0.j],
            [ 0.+0.j,   0.+0.j,   0.+0.j],
            [ 0.+0.j,   0.+0.j,   0.+0.j]],
           [[18.+0.j,   0.+0.j,   0.+0.j],
            [ 0.+0.j,   0.+0.j,   0.+0.j],
            [ 0.+0.j,   0.+0.j,   0.+0.j]]])
    >>> np.fft.fftn(a, (2, 2), axes=(0, 1))
    array([[[ 2.+0.j,  2.+0.j,  2.+0.j], # may vary
            [ 0.+0.j,  0.+0.j,  0.+0.j]],
           [[-2.+0.j, -2.+0.j, -2.+0.j],
            [ 0.+0.j,  0.+0.j,  0.+0.j]]])

    >>> import matplotlib.pyplot as plt
    >>> [X, Y] = np.meshgrid(2 * np.pi * np.arange(200) / 12,
    ...                      2 * np.pi * np.arange(200) / 34)
    >>> S = np.sin(X) + np.cos(Y) + np.random.uniform(0, 1, X.shape)
    >>> FS = np.fft.fftn(S)
    >>> plt.imshow(np.log(np.abs(np.fft.fftshift(FS))**2))
    <matplotlib.image.AxesImage object at 0x...>
    >>> plt.show()

    """
    return _raw_fftnd(a, s, axes, fft, norm, out=out)


@array_function_dispatch(_fftn_dispatcher)
def ifftn(a, s=None, axes=None, norm=None, out=None):
    """
    Compute the N-dimensional inverse discrete Fourier Transform.

    This function computes the inverse of the N-dimensional discrete
    Fourier Transform over any number of axes in an M-dimensional array by
    means of the Fast Fourier Transform (FFT).  In other words,
    ``ifftn(fftn(a)) == a`` to within numerical accuracy.
    For a description of the definitions and conventions used, see `numpy.fft`.

    The input, analogously to `ifft`, should be ordered in the same way as is
    returned by `fftn`, i.e. it should have the term for zero frequency
    in all axes in the low-order corner, the positive frequency terms in the
    first half of all axes, the term for the Nyquist frequency in the middle
    of all axes and the negative frequency terms in the second half of all
    axes, in order of decreasingly negative frequency.

    Parameters
    ----------
    a : array_like
        Input array, can be complex.
    s : sequence of ints, optional
        Shape (length of each transformed axis) of the output
        (``s[0]`` refers to axis 0, ``s[1]`` to axis 1, etc.).
        This corresponds to ``n`` for ``ifft(x, n)``.
        Along any axis, if the given shape is smaller than that of the input,
        the input is cropped. If it is larger, the input is padded with zeros.

        .. versionchanged:: 2.0

            If it is ``-1``, the whole input is used (no padding/trimming).

        If `s` is not given, the shape of the input along the axes specified
        by `axes` is used. See notes for issue on `ifft` zero padding.

        .. deprecated:: 2.0

            If `s` is not ``None``, `axes` must not be ``None`` either.

        .. deprecated:: 2.0

            `s` must contain only ``int`` s, not ``None`` values. ``None``
            values currently mean that the default value for ``n`` is used
            in the corresponding 1-D transform, but this behaviour is
            deprecated.

    axes : sequence of ints, optional
        Axes over which to compute the IFFT.  If not given, the last ``len(s)``
        axes are used, or all axes if `s` is also not specified.
        Repeated indices in `axes` means that the inverse transform over that
        axis is performed multiple times.

        .. deprecated:: 2.0

            If `s` is specified, the corresponding `axes` to be transformed
            must be explicitly specified too.

    norm : {"backward", "ortho", "forward"}, optional
        Normalization mode (see `numpy.fft`). Default is "backward".
        Indicates which direction of the forward/backward pair of transforms
        is scaled and with what normalization factor.

        .. versionadded:: 1.20.0

            The "backward", "forward" values were added.

    out : complex ndarray, optional
        If provided, the result will be placed in this array. It should be
        of the appropriate shape and dtype for all axes (and hence is
        incompatible with passing in all but the trivial ``s``).

        .. versionadded:: 2.0.0

    Returns
    -------
    out : complex ndarray
        The truncated or zero-padded input, transformed along the axes
        indicated by `axes`, or by a combination of `s` or `a`,
        as explained in the parameters section above.

    Raises
    ------
    ValueError
        If `s` and `axes` have different length.
    IndexError
        If an element of `axes` is larger than than the number of axes of `a`.

    See Also
    --------
    numpy.fft : Overall view of discrete Fourier transforms, with definitions
         and conventions used.
    fftn : The forward *n*-dimensional FFT, of which `ifftn` is the inverse.
    ifft : The one-dimensional inverse FFT.
    ifft2 : The two-dimensional inverse FFT.
    ifftshift : Undoes `fftshift`, shifts zero-frequency terms to beginning
        of array.

    Notes
    -----
    See `numpy.fft` for definitions and conventions used.

    Zero-padding, analogously with `ifft`, is performed by appending zeros to
    the input along the specified dimension.  Although this is the common
    approach, it might lead to surprising results.  If another form of zero
    padding is desired, it must be performed before `ifftn` is called.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.eye(4)
    >>> np.fft.ifftn(np.fft.fftn(a, axes=(0,)), axes=(1,))
    array([[1.+0.j,  0.+0.j,  0.+0.j,  0.+0.j], # may vary
           [0.+0.j,  1.+0.j,  0.+0.j,  0.+0.j],
           [0.+0.j,  0.+0.j,  1.+0.j,  0.+0.j],
           [0.+0.j,  0.+0.j,  0.+0.j,  1.+0.j]])


    Create and plot an image with band-limited frequency content:

    >>> import matplotlib.pyplot as plt
    >>> n = np.zeros((200,200), dtype=complex)
    >>> n[60:80, 20:40] = np.exp(1j*np.random.uniform(0, 2*np.pi, (20, 20)))
    >>> im = np.fft.ifftn(n).real
    >>> plt.imshow(im)
    <matplotlib.image.AxesImage object at 0x...>
    >>> plt.show()

    """
    return _raw_fftnd(a, s, axes, ifft, norm, out=out)


@array_function_dispatch(_fftn_dispatcher)
def fft2(a, s=None, axes=(-2, -1), norm=None, out=None):
    """
    Compute the 2-dimensional discrete Fourier Transform.

    This function computes the *n*-dimensional discrete Fourier Transform
    over any axes in an *M*-dimensional array by means of the
    Fast Fourier Transform (FFT).  By default, the transform is computed over
    the last two axes of the input array, i.e., a 2-dimensional FFT.

    Parameters
    ----------
    a : array_like
        Input array, can be complex
    s : sequence of ints, optional
        Shape (length of each transformed axis) of the output
        (``s[0]`` refers to axis 0, ``s[1]`` to axis 1, etc.).
        This corresponds to ``n`` for ``fft(x, n)``.
        Along each axis, if the given shape is smaller than that of the input,
        the input is cropped. If it is larger, the input is padded with zeros.

        .. versionchanged:: 2.0

            If it is ``-1``, the whole input is used (no padding/trimming).

        If `s` is not given, the shape of the input along the axes specified
        by `axes` is used.

        .. deprecated:: 2.0

            If `s` is not ``None``, `axes` must not be ``None`` either.

        .. deprecated:: 2.0

            `s` must contain only ``int`` s, not ``None`` values. ``None``
            values currently mean that the default value for ``n`` is used
            in the corresponding 1-D transform, but this behaviour is
            deprecated.

    axes : sequence of ints, optional
        Axes over which to compute the FFT.  If not given, the last two
        axes are used.  A repeated index in `axes` means the transform over
        that axis is performed multiple times.  A one-element sequence means
        that a one-dimensional FFT is performed. Default: ``(-2, -1)``.

        .. deprecated:: 2.0

            If `s` is specified, the corresponding `axes` to be transformed
            must not be ``None``.

    norm : {"backward", "ortho", "forward"}, optional
        Normalization mode (see `numpy.fft`). Default is "backward".
        Indicates which direction of the forward/backward pair of transforms
        is scaled and with what normalization factor.

        .. versionadded:: 1.20.0

            The "backward", "forward" values were added.

    out : complex ndarray, optional
        If provided, the result will be placed in this array. It should be
        of the appropriate shape and dtype for all axes (and hence only the
        last axis can have ``s`` not equal to the shape at that axis).

        .. versionadded:: 2.0.0

    Returns
    -------
    out : complex ndarray
        The truncated or zero-padded input, transformed along the axes
        indicated by `axes`, or the last two axes if `axes` is not given.

    Raises
    ------
    ValueError
        If `s` and `axes` have different length, or `axes` not given and
        ``len(s) != 2``.
    IndexError
        If an element of `axes` is larger than than the number of axes of `a`.

    See Also
    --------
    numpy.fft : Overall view of discrete Fourier transforms, with definitions
         and conventions used.
    ifft2 : The inverse two-dimensional FFT.
    fft : The one-dimensional FFT.
    fftn : The *n*-dimensional FFT.
    fftshift : Shifts zero-frequency terms to the center of the array.
        For two-dimensional input, swaps first and third quadrants, and second
        and fourth quadrants.

    Notes
    -----
    `fft2` is just `fftn` with a different default for `axes`.

    The output, analogously to `fft`, contains the term for zero frequency in
    the low-order corner of the transformed axes, the positive frequency terms
    in the first half of these axes, the term for the Nyquist frequency in the
    middle of the axes and the negative frequency terms in the second half of
    the axes, in order of decreasingly negative frequency.

    See `fftn` for details and a plotting example, and `numpy.fft` for
    definitions and conventions used.


    Examples
    --------
    >>> import numpy as np
    >>> a = np.mgrid[:5, :5][0]
    >>> np.fft.fft2(a)
    array([[ 50.  +0.j        ,   0.  +0.j        ,   0.  +0.j        , # may vary
              0.  +0.j        ,   0.  +0.j        ],
           [-12.5+17.20477401j,   0.  +0.j        ,   0.  +0.j        ,
              0.  +0.j        ,   0.  +0.j        ],
           [-12.5 +4.0614962j ,   0.  +0.j        ,   0.  +0.j        ,
              0.  +0.j        ,   0.  +0.j        ],
           [-12.5 -4.0614962j ,   0.  +0.j        ,   0.  +0.j        ,
              0.  +0.j        ,   0.  +0.j        ],
           [-12.5-17.20477401j,   0.  +0.j        ,   0.  +0.j        ,
              0.  +0.j        ,   0.  +0.j        ]])

    """
    return _raw_fftnd(a, s, axes, fft, norm, out=out)


@array_function_dispatch(_fftn_dispatcher)
def ifft2(a, s=None, axes=(-2, -1), norm=None, out=None):
    """
    Compute the 2-dimensional inverse discrete Fourier Transform.

    This function computes the inverse of the 2-dimensional discrete Fourier
    Transform over any number of axes in an M-dimensional array by means of
    the Fast Fourier Transform (FFT).  In other words, ``ifft2(fft2(a)) == a``
    to within numerical accuracy.  By default, the inverse transform is
    computed over the last two axes of the input array.

    The input, analogously to `ifft`, should be ordered in the same way as is
    returned by `fft2`, i.e. it should have the term for zero frequency
    in the low-order corner of the two axes, the positive frequency terms in
    the first half of these axes, the term for the Nyquist frequency in the
    middle of the axes and the negative frequency terms in the second half of
    both axes, in order of decreasingly negative frequency.

    Parameters
    ----------
    a : array_like
        Input array, can be complex.
    s : sequence of ints, optional
        Shape (length of each axis) of the output (``s[0]`` refers to axis 0,
        ``s[1]`` to axis 1, etc.).  This corresponds to `n` for ``ifft(x, n)``.
        Along each axis, if the given shape is smaller than that of the input,
        the input is cropped. If it is larger, the input is padded with zeros.

        .. versionchanged:: 2.0

            If it is ``-1``, the whole input is used (no padding/trimming).

        If `s` is not given, the shape of the input along the axes specified
        by `axes` is used.  See notes for issue on `ifft` zero padding.

        .. deprecated:: 2.0

            If `s` is not ``None``, `axes` must not be ``None`` either.

        .. deprecated:: 2.0

            `s` must contain only ``int`` s, not ``None`` values. ``None``
            values currently mean that the default value for ``n`` is used
            in the corresponding 1-D transform, but this behaviour is
            deprecated.

    axes : sequence of ints, optional
        Axes over which to compute the FFT.  If not given, the last two
        axes are used.  A repeated index in `axes` means the transform over
        that axis is performed multiple times.  A one-element sequence means
        that a one-dimensional FFT is performed. Default: ``(-2, -1)``.

        .. deprecated:: 2.0

            If `s` is specified, the corresponding `axes` to be transformed
            must not be ``None``.

    norm : {"backward", "ortho", "forward"}, optional
        Normalization mode (see `numpy.fft`). Default is "backward".
        Indicates which direction of the forward/backward pair of transforms
        is scaled and with what normalization factor.

        .. versionadded:: 1.20.0

            The "backward", "forward" values were added.

    out : complex ndarray, optional
        If provided, the result will be placed in this array. It should be
        of the appropriate shape and dtype for all axes (and hence is
        incompatible with passing in all but the trivial ``s``).

        .. versionadded:: 2.0.0

    Returns
    -------
    out : complex ndarray
        The truncated or zero-padded input, transformed along the axes
        indicated by `axes`, or the last two axes if `axes` is not given.

    Raises
    ------
    ValueError
        If `s` and `axes` have different length, or `axes` not given and
        ``len(s) != 2``.
    IndexError
        If an element of `axes` is larger than than the number of axes of `a`.

    See Also
    --------
    numpy.fft : Overall view of discrete Fourier transforms, with definitions
         and conventions used.
    fft2 : The forward 2-dimensional FFT, of which `ifft2` is the inverse.
    ifftn : The inverse of the *n*-dimensional FFT.
    fft : The one-dimensional FFT.
    ifft : The one-dimensional inverse FFT.

    Notes
    -----
    `ifft2` is just `ifftn` with a different default for `axes`.

    See `ifftn` for details and a plotting example, and `numpy.fft` for
    definition and conventions used.

    Zero-padding, analogously with `ifft`, is performed by appending zeros to
    the input along the specified dimension.  Although this is the common
    approach, it might lead to surprising results.  If another form of zero
    padding is desired, it must be performed before `ifft2` is called.

    Examples
    --------
    >>> import numpy as np
    >>> a = 4 * np.eye(4)
    >>> np.fft.ifft2(a)
    array([[1.+0.j,  0.+0.j,  0.+0.j,  0.+0.j], # may vary
           [0.+0.j,  0.+0.j,  0.+0.j,  1.+0.j],
           [0.+0.j,  0.+0.j,  1.+0.j,  0.+0.j],
           [0.+0.j,  1.+0.j,  0.+0.j,  0.+0.j]])

    """
    return _raw_fftnd(a, s, axes, ifft, norm, out=None)


@array_function_dispatch(_fftn_dispatcher)
def rfftn(a, s=None, axes=None, norm=None, out=None):
    """
    Compute the N-dimensional discrete Fourier Transform for real input.

    This function computes the N-dimensional discrete Fourier Transform over
    any number of axes in an M-dimensional real array by means of the Fast
    Fourier Transform (FFT).  By default, all axes are transformed, with the
    real transform performed over the last axis, while the remaining
    transforms are complex.

    Parameters
    ----------
    a : array_like
        Input array, taken to be real.
    s : sequence of ints, optional
        Shape (length along each transformed axis) to use from the input.
        (``s[0]`` refers to axis 0, ``s[1]`` to axis 1, etc.).
        The final element of `s` corresponds to `n` for ``rfft(x, n)``, while
        for the remaining axes, it corresponds to `n` for ``fft(x, n)``.
        Along any axis, if the given shape is smaller than that of the input,
        the input is cropped. If it is larger, the input is padded with zeros.

        .. versionchanged:: 2.0

            If it is ``-1``, the whole input is used (no padding/trimming).

        If `s` is not given, the shape of the input along the axes specified
        by `axes` is used.

        .. deprecated:: 2.0

            If `s` is not ``None``, `axes` must not be ``None`` either.

        .. deprecated:: 2.0

            `s` must contain only ``int`` s, not ``None`` values. ``None``
            values currently mean that the default value for ``n`` is used
            in the corresponding 1-D transform, but this behaviour is
            deprecated.

    axes : sequence of ints, optional
        Axes over which to compute the FFT.  If not given, the last ``len(s)``
        axes are used, or all axes if `s` is also not specified.

        .. deprecated:: 2.0

            If `s` is specified, the corresponding `axes` to be transformed
            must be explicitly specified too.

    norm : {"backward", "ortho", "forward"}, optional
        Normalization mode (see `numpy.fft`). Default is "backward".
        Indicates which direction of the forward/backward pair of transforms
        is scaled and with what normalization factor.

        .. versionadded:: 1.20.0

            The "backward", "forward" values were added.

    out : complex ndarray, optional
        If provided, the result will be placed in this array. It should be
        of the appropriate shape and dtype for all axes (and hence is
        incompatible with passing in all but the trivial ``s``).

        .. versionadded:: 2.0.0

    Returns
    -------
    out : complex ndarray
        The truncated or zero-padded input, transformed along the axes
        indicated by `axes`, or by a combination of `s` and `a`,
        as explained in the parameters section above.
        The length of the last axis transformed will be ``s[-1]//2+1``,
        while the remaining transformed axes will have lengths according to
        `s`, or unchanged from the input.

    Raises
    ------
    ValueError
        If `s` and `axes` have different length.
    IndexError
        If an element of `axes` is larger than than the number of axes of `a`.

    See Also
    --------
    irfftn : The inverse of `rfftn`, i.e. the inverse of the n-dimensional FFT
         of real input.
    fft : The one-dimensional FFT, with definitions and conventions used.
    rfft : The one-dimensional FFT of real input.
    fftn : The n-dimensional FFT.
    rfft2 : The two-dimensional FFT of real input.

    Notes
    -----
    The transform for real input is performed over the last transformation
    axis, as by `rfft`, then the transform over the remaining axes is
    performed as by `fftn`.  The order of the output is as for `rfft` for the
    final transformation axis, and as for `fftn` for the remaining
    transformation axes.

    See `fft` for details, definitions and conventions used.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.ones((2, 2, 2))
    >>> np.fft.rfftn(a)
    array([[[8.+0.j,  0.+0.j], # may vary
            [0.+0.j,  0.+0.j]],
           [[0.+0.j,  0.+0.j],
            [0.+0.j,  0.+0.j]]])

    >>> np.fft.rfftn(a, axes=(2, 0))
    array([[[4.+0.j,  0.+0.j], # may vary
            [4.+0.j,  0.+0.j]],
           [[0.+0.j,  0.+0.j],
            [0.+0.j,  0.+0.j]]])

    """
    a = asarray(a)
    s, axes = _cook_nd_args(a, s, axes)
    a = rfft(a, s[-1], axes[-1], norm, out=out)
    for ii in range(len(axes) - 2, -1, -1):
        a = fft(a, s[ii], axes[ii], norm, out=out)
    return a


@array_function_dispatch(_fftn_dispatcher)
def rfft2(a, s=None, axes=(-2, -1), norm=None, out=None):
    """
    Compute the 2-dimensional FFT of a real array.

    Parameters
    ----------
    a : array
        Input array, taken to be real.
    s : sequence of ints, optional
        Shape of the FFT.

        .. versionchanged:: 2.0

            If it is ``-1``, the whole input is used (no padding/trimming).

        .. deprecated:: 2.0

            If `s` is not ``None``, `axes` must not be ``None`` either.

        .. deprecated:: 2.0

            `s` must contain only ``int`` s, not ``None`` values. ``None``
            values currently mean that the default value for ``n`` is used
            in the corresponding 1-D transform, but this behaviour is
            deprecated.

    axes : sequence of ints, optional
        Axes over which to compute the FFT. Default: ``(-2, -1)``.

        .. deprecated:: 2.0

            If `s` is specified, the corresponding `axes` to be transformed
            must not be ``None``.

    norm : {"backward", "ortho", "forward"}, optional
        Normalization mode (see `numpy.fft`). Default is "backward".
        Indicates which direction of the forward/backward pair of transforms
        is scaled and with what normalization factor.

        .. versionadded:: 1.20.0

            The "backward", "forward" values were added.

    out : complex ndarray, optional
        If provided, the result will be placed in this array. It should be
        of the appropriate shape and dtype for the last inverse transform.
        incompatible with passing in all but the trivial ``s``).

        .. versionadded:: 2.0.0

    Returns
    -------
    out : ndarray
        The result of the real 2-D FFT.

    See Also
    --------
    rfftn : Compute the N-dimensional discrete Fourier Transform for real
            input.

    Notes
    -----
    This is really just `rfftn` with different default behavior.
    For more details see `rfftn`.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.mgrid[:5, :5][0]
    >>> np.fft.rfft2(a)
    array([[ 50.  +0.j        ,   0.  +0.j        ,   0.  +0.j        ],
           [-12.5+17.20477401j,   0.  +0.j        ,   0.  +0.j        ],
           [-12.5 +4.0614962j ,   0.  +0.j        ,   0.  +0.j        ],
           [-12.5 -4.0614962j ,   0.  +0.j        ,   0.  +0.j        ],
           [-12.5-17.20477401j,   0.  +0.j        ,   0.  +0.j        ]])
    """
    return rfftn(a, s, axes, norm, out=out)


@array_function_dispatch(_fftn_dispatcher)
def irfftn(a, s=None, axes=None, norm=None, out=None):
    """
    Computes the inverse of `rfftn`.

    This function computes the inverse of the N-dimensional discrete
    Fourier Transform for real input over any number of axes in an
    M-dimensional array by means of the Fast Fourier Transform (FFT).  In
    other words, ``irfftn(rfftn(a), a.shape) == a`` to within numerical
    accuracy. (The ``a.shape`` is necessary like ``len(a)`` is for `irfft`,
    and for the same reason.)

    The input should be ordered in the same way as is returned by `rfftn`,
    i.e. as for `irfft` for the final transformation axis, and as for `ifftn`
    along all the other axes.

    Parameters
    ----------
    a : array_like
        Input array.
    s : sequence of ints, optional
        Shape (length of each transformed axis) of the output
        (``s[0]`` refers to axis 0, ``s[1]`` to axis 1, etc.). `s` is also the
        number of input points used along this axis, except for the last axis,
        where ``s[-1]//2+1`` points of the input are used.
        Along any axis, if the shape indicated by `s` is smaller than that of
        the input, the input is cropped.  If it is larger, the input is padded
        with zeros.

        .. versionchanged:: 2.0

            If it is ``-1``, the whole input is used (no padding/trimming).

        If `s` is not given, the shape of the input along the axes
        specified by axes is used. Except for the last axis which is taken to
        be ``2*(m-1)`` where ``m`` is the length of the input along that axis.

        .. deprecated:: 2.0

            If `s` is not ``None``, `axes` must not be ``None`` either.

        .. deprecated:: 2.0

            `s` must contain only ``int`` s, not ``None`` values. ``None``
            values currently mean that the default value for ``n`` is used
            in the corresponding 1-D transform, but this behaviour is
            deprecated.

    axes : sequence of ints, optional
        Axes over which to compute the inverse FFT. If not given, the last
        `len(s)` axes are used, or all axes if `s` is also not specified.
        Repeated indices in `axes` means that the inverse transform over that
        axis is performed multiple times.

        .. deprecated:: 2.0

            If `s` is specified, the corresponding `axes` to be transformed
            must be explicitly specified too.

    norm : {"backward", "ortho", "forward"}, optional
        Normalization mode (see `numpy.fft`). Default is "backward".
        Indicates which direction of the forward/backward pair of transforms
        is scaled and with what normalization factor.

        .. versionadded:: 1.20.0

            The "backward", "forward" values were added.

    out : ndarray, optional
        If provided, the result will be placed in this array. It should be
        of the appropriate shape and dtype for the last transformation.

        .. versionadded:: 2.0.0

    Returns
    -------
    out : ndarray
        The truncated or zero-padded input, transformed along the axes
        indicated by `axes`, or by a combination of `s` or `a`,
        as explained in the parameters section above.
        The length of each transformed axis is as given by the corresponding
        element of `s`, or the length of the input in every axis except for the
        last one if `s` is not given.  In the final transformed axis the length
        of the output when `s` is not given is ``2*(m-1)`` where ``m`` is the
        length of the final transformed axis of the input.  To get an odd
        number of output points in the final axis, `s` must be specified.

    Raises
    ------
    ValueError
        If `s` and `axes` have different length.
    IndexError
        If an element of `axes` is larger than than the number of axes of `a`.

    See Also
    --------
    rfftn : The forward n-dimensional FFT of real input,
            of which `ifftn` is the inverse.
    fft : The one-dimensional FFT, with definitions and conventions used.
    irfft : The inverse of the one-dimensional FFT of real input.
    irfft2 : The inverse of the two-dimensional FFT of real input.

    Notes
    -----
    See `fft` for definitions and conventions used.

    See `rfft` for definitions and conventions used for real input.

    The correct interpretation of the hermitian input depends on the shape of
    the original data, as given by `s`. This is because each input shape could
    correspond to either an odd or even length signal. By default, `irfftn`
    assumes an even output length which puts the last entry at the Nyquist
    frequency; aliasing with its symmetric counterpart. When performing the
    final complex to real transform, the last value is thus treated as purely
    real. To avoid losing information, the correct shape of the real input
    **must** be given.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.zeros((3, 2, 2))
    >>> a[0, 0, 0] = 3 * 2 * 2
    >>> np.fft.irfftn(a)
    array([[[1.,  1.],
            [1.,  1.]],
           [[1.,  1.],
            [1.,  1.]],
           [[1.,  1.],
            [1.,  1.]]])

    """
    a = asarray(a)
    s, axes = _cook_nd_args(a, s, axes, invreal=1)
    for ii in range(len(axes) - 1):
        a = ifft(a, s[ii], axes[ii], norm)
    a = irfft(a, s[-1], axes[-1], norm, out=out)
    return a


@array_function_dispatch(_fftn_dispatcher)
def irfft2(a, s=None, axes=(-2, -1), norm=None, out=None):
    """
    Computes the inverse of `rfft2`.

    Parameters
    ----------
    a : array_like
        The input array
    s : sequence of ints, optional
        Shape of the real output to the inverse FFT.

        .. versionchanged:: 2.0

            If it is ``-1``, the whole input is used (no padding/trimming).

        .. deprecated:: 2.0

            If `s` is not ``None``, `axes` must not be ``None`` either.

        .. deprecated:: 2.0

            `s` must contain only ``int`` s, not ``None`` values. ``None``
            values currently mean that the default value for ``n`` is used
            in the corresponding 1-D transform, but this behaviour is
            deprecated.

    axes : sequence of ints, optional
        The axes over which to compute the inverse fft.
        Default: ``(-2, -1)``, the last two axes.

        .. deprecated:: 2.0

            If `s` is specified, the corresponding `axes` to be transformed
            must not be ``None``.

    norm : {"backward", "ortho", "forward"}, optional
        Normalization mode (see `numpy.fft`). Default is "backward".
        Indicates which direction of the forward/backward pair of transforms
        is scaled and with what normalization factor.

        .. versionadded:: 1.20.0

            The "backward", "forward" values were added.

    out : ndarray, optional
        If provided, the result will be placed in this array. It should be
        of the appropriate shape and dtype for the last transformation.

        .. versionadded:: 2.0.0

    Returns
    -------
    out : ndarray
        The result of the inverse real 2-D FFT.

    See Also
    --------
    rfft2 : The forward two-dimensional FFT of real input,
            of which `irfft2` is the inverse.
    rfft : The one-dimensional FFT for real input.
    irfft : The inverse of the one-dimensional FFT of real input.
    irfftn : Compute the inverse of the N-dimensional FFT of real input.

    Notes
    -----
    This is really `irfftn` with different defaults.
    For more details see `irfftn`.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.mgrid[:5, :5][0]
    >>> A = np.fft.rfft2(a)
    >>> np.fft.irfft2(A, s=a.shape)
    array([[0., 0., 0., 0., 0.],
           [1., 1., 1., 1., 1.],
           [2., 2., 2., 2., 2.],
           [3., 3., 3., 3., 3.],
           [4., 4., 4., 4., 4.]])
    """
    return irfftn(a, s, axes, norm, out=None)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\bedrock\chat\invoke_handler.py ===
"""
TODO: DELETE FILE. Bedrock LLM is no longer used. Goto `litellm/llms/bedrock/chat/invoke_transformations/base_invoke_transformation.py`
"""

import copy
import json
import time
import types
import urllib.parse
import uuid
from functools import partial
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
    cast,
    get_args,
)

import httpx  # type: ignore

import litellm
from litellm import verbose_logger
from litellm.caching.caching import InMemoryCache
from litellm.litellm_core_utils.core_helpers import map_finish_reason
from litellm.litellm_core_utils.litellm_logging import Logging
from litellm.litellm_core_utils.logging_utils import track_llm_api_timing
from litellm.litellm_core_utils.prompt_templates.factory import (
    cohere_message_pt,
    construct_tool_use_system_prompt,
    contains_tag,
    custom_prompt,
    extract_between_tags,
    parse_xml_params,
    prompt_factory,
)
from litellm.llms.anthropic.chat.handler import (
    ModelResponseIterator as AnthropicModelResponseIterator,
)
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    _get_httpx_client,
    get_async_httpx_client,
)
from litellm.types.llms.bedrock import *
from litellm.types.llms.openai import (
    ChatCompletionRedactedThinkingBlock,
    ChatCompletionThinkingBlock,
    ChatCompletionToolCallChunk,
    ChatCompletionToolCallFunctionChunk,
    ChatCompletionUsageBlock,
)
from litellm.types.utils import ChatCompletionMessageToolCall, Choices, Delta
from litellm.types.utils import GenericStreamingChunk as GChunk
from litellm.types.utils import (
    ModelResponse,
    ModelResponseStream,
    StreamingChoices,
    Usage,
)
from litellm.utils import CustomStreamWrapper, get_secret

from ..base_aws_llm import BaseAWSLLM
from ..common_utils import BedrockError, ModelResponseIterator, get_bedrock_tool_name

_response_stream_shape_cache = None
bedrock_tool_name_mappings: InMemoryCache = InMemoryCache(
    max_size_in_memory=50, default_ttl=600
)
from litellm.llms.bedrock.chat.converse_transformation import AmazonConverseConfig

converse_config = AmazonConverseConfig()


class AmazonCohereChatConfig:
    """
    Reference - https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-cohere-command-r-plus.html
    """

    documents: Optional[List[Document]] = None
    search_queries_only: Optional[bool] = None
    preamble: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    p: Optional[float] = None
    k: Optional[float] = None
    prompt_truncation: Optional[str] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    seed: Optional[int] = None
    return_prompt: Optional[bool] = None
    stop_sequences: Optional[List[str]] = None
    raw_prompting: Optional[bool] = None

    def __init__(
        self,
        documents: Optional[List[Document]] = None,
        search_queries_only: Optional[bool] = None,
        preamble: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        p: Optional[float] = None,
        k: Optional[float] = None,
        prompt_truncation: Optional[str] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        seed: Optional[int] = None,
        return_prompt: Optional[bool] = None,
        stop_sequences: Optional[str] = None,
        raw_prompting: Optional[bool] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return {
            k: v
            for k, v in cls.__dict__.items()
            if not k.startswith("__")
            and not isinstance(
                v,
                (
                    types.FunctionType,
                    types.BuiltinFunctionType,
                    classmethod,
                    staticmethod,
                ),
            )
            and v is not None
        }

    def get_supported_openai_params(self) -> List[str]:
        return [
            "max_tokens",
            "max_completion_tokens",
            "stream",
            "stop",
            "temperature",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "seed",
            "stop",
            "tools",
            "tool_choice",
        ]

    def map_openai_params(
        self, non_default_params: dict, optional_params: dict
    ) -> dict:
        for param, value in non_default_params.items():
            if param == "max_tokens" or param == "max_completion_tokens":
                optional_params["max_tokens"] = value
            if param == "stream":
                optional_params["stream"] = value
            if param == "stop":
                if isinstance(value, str):
                    value = [value]
                optional_params["stop_sequences"] = value
            if param == "temperature":
                optional_params["temperature"] = value
            if param == "top_p":
                optional_params["p"] = value
            if param == "frequency_penalty":
                optional_params["frequency_penalty"] = value
            if param == "presence_penalty":
                optional_params["presence_penalty"] = value
            if "seed":
                optional_params["seed"] = value
        return optional_params


async def make_call(
    client: Optional[AsyncHTTPHandler],
    api_base: str,
    headers: dict,
    data: str,
    model: str,
    messages: list,
    logging_obj: Logging,
    fake_stream: bool = False,
    json_mode: Optional[bool] = False,
    bedrock_invoke_provider: Optional[litellm.BEDROCK_INVOKE_PROVIDERS_LITERAL] = None,
):
    try:
        if client is None:
            client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders.BEDROCK
            )  # Create a new client if none provided

        response = await client.post(
            api_base,
            headers=headers,
            data=data,
            stream=not fake_stream,
            logging_obj=logging_obj,
        )

        if response.status_code != 200:
            raise BedrockError(status_code=response.status_code, message=response.text)

        if fake_stream:
            model_response: (
                ModelResponse
            ) = litellm.AmazonConverseConfig()._transform_response(
                model=model,
                response=response,
                model_response=litellm.ModelResponse(),
                stream=True,
                logging_obj=logging_obj,
                optional_params={},
                api_key="",
                data=data,
                messages=messages,
                encoding=litellm.encoding,
            )  # type: ignore
            completion_stream: Any = MockResponseIterator(
                model_response=model_response, json_mode=json_mode
            )
        elif bedrock_invoke_provider == "anthropic":
            decoder: AWSEventStreamDecoder = AmazonAnthropicClaudeStreamDecoder(
                model=model,
                sync_stream=False,
                json_mode=json_mode,
            )
            completion_stream = decoder.aiter_bytes(
                response.aiter_bytes(chunk_size=1024)
            )
        elif bedrock_invoke_provider == "deepseek_r1":
            decoder = AmazonDeepSeekR1StreamDecoder(
                model=model,
                sync_stream=False,
            )
            completion_stream = decoder.aiter_bytes(
                response.aiter_bytes(chunk_size=1024)
            )
        else:
            decoder = AWSEventStreamDecoder(model=model)
            completion_stream = decoder.aiter_bytes(
                response.aiter_bytes(chunk_size=1024)
            )

        # LOGGING
        logging_obj.post_call(
            input=messages,
            api_key="",
            original_response="first stream response received",
            additional_args={"complete_input_dict": data},
        )

        return completion_stream
    except httpx.HTTPStatusError as err:
        error_code = err.response.status_code
        raise BedrockError(status_code=error_code, message=err.response.text)
    except httpx.TimeoutException:
        raise BedrockError(status_code=408, message="Timeout error occurred.")
    except Exception as e:
        raise BedrockError(status_code=500, message=str(e))


def make_sync_call(
    client: Optional[HTTPHandler],
    api_base: str,
    headers: dict,
    data: str,
    signed_json_body: Optional[bytes],
    model: str,
    messages: list,
    logging_obj: Logging,
    fake_stream: bool = False,
    json_mode: Optional[bool] = False,
    bedrock_invoke_provider: Optional[litellm.BEDROCK_INVOKE_PROVIDERS_LITERAL] = None,
):
    try:
        if client is None:
            client = _get_httpx_client(params={})

        response = client.post(
            api_base,
            headers=headers,
            data=signed_json_body if signed_json_body is not None else data,
            stream=not fake_stream,
            logging_obj=logging_obj,
        )

        if response.status_code != 200:
            raise BedrockError(status_code=response.status_code, message=response.text)

        if fake_stream:
            model_response: (
                ModelResponse
            ) = litellm.AmazonConverseConfig()._transform_response(
                model=model,
                response=response,
                model_response=litellm.ModelResponse(),
                stream=True,
                logging_obj=logging_obj,
                optional_params={},
                api_key="",
                data=data,
                messages=messages,
                encoding=litellm.encoding,
            )  # type: ignore
            completion_stream: Any = MockResponseIterator(
                model_response=model_response, json_mode=json_mode
            )
        elif bedrock_invoke_provider == "anthropic":
            decoder: AWSEventStreamDecoder = AmazonAnthropicClaudeStreamDecoder(
                model=model,
                sync_stream=True,
                json_mode=json_mode,
            )
            completion_stream = decoder.iter_bytes(response.iter_bytes(chunk_size=1024))
        elif bedrock_invoke_provider == "deepseek_r1":
            decoder = AmazonDeepSeekR1StreamDecoder(
                model=model,
                sync_stream=True,
            )
            completion_stream = decoder.iter_bytes(response.iter_bytes(chunk_size=1024))
        else:
            decoder = AWSEventStreamDecoder(model=model)
            completion_stream = decoder.iter_bytes(response.iter_bytes(chunk_size=1024))

        # LOGGING
        logging_obj.post_call(
            input=messages,
            api_key="",
            original_response="first stream response received",
            additional_args={"complete_input_dict": data},
        )

        return completion_stream
    except httpx.HTTPStatusError as err:
        error_code = err.response.status_code
        raise BedrockError(status_code=error_code, message=err.response.text)
    except httpx.TimeoutException:
        raise BedrockError(status_code=408, message="Timeout error occurred.")
    except Exception as e:
        raise BedrockError(status_code=500, message=str(e))


class BedrockLLM(BaseAWSLLM):
    """
    Example call

    ```
    curl --location --request POST 'https://bedrock-runtime.{aws_region_name}.amazonaws.com/model/{bedrock_model_name}/invoke' \
        --header 'Content-Type: application/json' \
        --header 'Accept: application/json' \
        --user "$AWS_ACCESS_KEY_ID":"$AWS_SECRET_ACCESS_KEY" \
        --aws-sigv4 "aws:amz:us-east-1:bedrock" \
        --data-raw '{
        "prompt": "Hi",
        "temperature": 0,
        "p": 0.9,
        "max_tokens": 4096
        }'
    ```
    """

    def __init__(self) -> None:
        super().__init__()

    def convert_messages_to_prompt(
        self, model, messages, provider, custom_prompt_dict
    ) -> Tuple[str, Optional[list]]:
        # handle anthropic prompts and amazon titan prompts
        prompt = ""
        chat_history: Optional[list] = None
        ## CUSTOM PROMPT
        if model in custom_prompt_dict:
            # check if the model has a registered custom prompt
            model_prompt_details = custom_prompt_dict[model]
            prompt = custom_prompt(
                role_dict=model_prompt_details["roles"],
                initial_prompt_value=model_prompt_details.get(
                    "initial_prompt_value", ""
                ),
                final_prompt_value=model_prompt_details.get("final_prompt_value", ""),
                messages=messages,
            )
            return prompt, None
        ## ELSE
        if provider == "anthropic" or provider == "amazon":
            prompt = prompt_factory(
                model=model, messages=messages, custom_llm_provider="bedrock"
            )
        elif provider == "mistral":
            prompt = prompt_factory(
                model=model, messages=messages, custom_llm_provider="bedrock"
            )
        elif provider == "meta" or provider == "llama":
            prompt = prompt_factory(
                model=model, messages=messages, custom_llm_provider="bedrock"
            )
        elif provider == "cohere":
            prompt, chat_history = cohere_message_pt(messages=messages)
        else:
            prompt = ""
            for message in messages:
                if "role" in message:
                    if message["role"] == "user":
                        prompt += f"{message['content']}"
                    else:
                        prompt += f"{message['content']}"
                else:
                    prompt += f"{message['content']}"
        return prompt, chat_history  # type: ignore

    def process_response(  # noqa: PLR0915
        self,
        model: str,
        response: httpx.Response,
        model_response: ModelResponse,
        stream: Optional[bool],
        logging_obj: Logging,
        optional_params: dict,
        api_key: str,
        data: Union[dict, str],
        messages: List,
        print_verbose,
        encoding,
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        provider = self.get_bedrock_invoke_provider(model)
        ## LOGGING
        logging_obj.post_call(
            input=messages,
            api_key=api_key,
            original_response=response.text,
            additional_args={"complete_input_dict": data},
        )
        print_verbose(f"raw model_response: {response.text}")

        ## RESPONSE OBJECT
        try:
            completion_response = response.json()
        except Exception:
            raise BedrockError(message=response.text, status_code=422)

        outputText: Optional[str] = None
        try:
            if provider == "cohere":
                if "text" in completion_response:
                    outputText = completion_response["text"]  # type: ignore
                elif "generations" in completion_response:
                    outputText = completion_response["generations"][0]["text"]
                    model_response.choices[0].finish_reason = map_finish_reason(
                        completion_response["generations"][0]["finish_reason"]
                    )
            elif provider == "anthropic":
                if model.startswith("anthropic.claude-3"):
                    json_schemas: dict = {}
                    _is_function_call = False
                    ## Handle Tool Calling
                    if "tools" in optional_params:
                        _is_function_call = True
                        for tool in optional_params["tools"]:
                            json_schemas[tool["function"]["name"]] = tool[
                                "function"
                            ].get("parameters", None)
                    outputText = completion_response.get("content")[0].get("text", None)
                    if outputText is not None and contains_tag(
                        "invoke", outputText
                    ):  # OUTPUT PARSE FUNCTION CALL
                        function_name = extract_between_tags("tool_name", outputText)[0]
                        function_arguments_str = extract_between_tags(
                            "invoke", outputText
                        )[0].strip()
                        function_arguments_str = (
                            f"<invoke>{function_arguments_str}</invoke>"
                        )
                        function_arguments = parse_xml_params(
                            function_arguments_str,
                            json_schema=json_schemas.get(
                                function_name, None
                            ),  # check if we have a json schema for this function name)
                        )
                        _message = litellm.Message(
                            tool_calls=[
                                {
                                    "id": f"call_{uuid.uuid4()}",
                                    "type": "function",
                                    "function": {
                                        "name": function_name,
                                        "arguments": json.dumps(function_arguments),
                                    },
                                }
                            ],
                            content=None,
                        )
                        model_response.choices[0].message = _message  # type: ignore
                        model_response._hidden_params[
                            "original_response"
                        ] = outputText  # allow user to access raw anthropic tool calling response
                    if (
                        _is_function_call is True
                        and stream is not None
                        and stream is True
                    ):
                        print_verbose(
                            "INSIDE BEDROCK STREAMING TOOL CALLING CONDITION BLOCK"
                        )
                        # return an iterator
                        streaming_model_response = ModelResponse(stream=True)
                        streaming_model_response.choices[0].finish_reason = getattr(
                            model_response.choices[0], "finish_reason", "stop"
                        )
                        # streaming_model_response.choices = [litellm.utils.StreamingChoices()]
                        streaming_choice = litellm.utils.StreamingChoices()
                        streaming_choice.index = model_response.choices[0].index
                        _tool_calls = []
                        print_verbose(
                            f"type of model_response.choices[0]: {type(model_response.choices[0])}"
                        )
                        print_verbose(
                            f"type of streaming_choice: {type(streaming_choice)}"
                        )
                        if isinstance(model_response.choices[0], litellm.Choices):
                            if getattr(
                                model_response.choices[0].message, "tool_calls", None
                            ) is not None and isinstance(
                                model_response.choices[0].message.tool_calls, list
                            ):
                                for tool_call in model_response.choices[
                                    0
                                ].message.tool_calls:
                                    _tool_call = {**tool_call.dict(), "index": 0}
                                    _tool_calls.append(_tool_call)
                            delta_obj = Delta(
                                content=getattr(
                                    model_response.choices[0].message, "content", None
                                ),
                                role=model_response.choices[0].message.role,
                                tool_calls=_tool_calls,
                            )
                            streaming_choice.delta = delta_obj
                            streaming_model_response.choices = [streaming_choice]
                            completion_stream = ModelResponseIterator(
                                model_response=streaming_model_response
                            )
                            print_verbose(
                                "Returns anthropic CustomStreamWrapper with 'cached_response' streaming object"
                            )
                            return litellm.CustomStreamWrapper(
                                completion_stream=completion_stream,
                                model=model,
                                custom_llm_provider="cached_response",
                                logging_obj=logging_obj,
                            )

                    model_response.choices[0].finish_reason = map_finish_reason(
                        completion_response.get("stop_reason", "")
                    )
                    _usage = litellm.Usage(
                        prompt_tokens=completion_response["usage"]["input_tokens"],
                        completion_tokens=completion_response["usage"]["output_tokens"],
                        total_tokens=completion_response["usage"]["input_tokens"]
                        + completion_response["usage"]["output_tokens"],
                    )
                    setattr(model_response, "usage", _usage)
                else:
                    outputText = completion_response["completion"]

                    model_response.choices[0].finish_reason = completion_response[
                        "stop_reason"
                    ]
            elif provider == "ai21":
                outputText = (
                    completion_response.get("completions")[0].get("data").get("text")
                )
            elif provider == "meta" or provider == "llama":
                outputText = completion_response["generation"]
            elif provider == "mistral":
                outputText = completion_response["outputs"][0]["text"]
                model_response.choices[0].finish_reason = completion_response[
                    "outputs"
                ][0]["stop_reason"]
            else:  # amazon titan
                outputText = completion_response.get("results")[0].get("outputText")
        except Exception as e:
            raise BedrockError(
                message="Error processing={}, Received error={}".format(
                    response.text, str(e)
                ),
                status_code=422,
            )

        try:
            if (
                outputText is not None
                and len(outputText) > 0
                and hasattr(model_response.choices[0], "message")
                and getattr(model_response.choices[0].message, "tool_calls", None)  # type: ignore
                is None
            ):
                model_response.choices[0].message.content = outputText  # type: ignore
            elif (
                hasattr(model_response.choices[0], "message")
                and getattr(model_response.choices[0].message, "tool_calls", None)  # type: ignore
                is not None
            ):
                pass
            else:
                raise Exception()
        except Exception as e:
            raise BedrockError(
                message="Error parsing received text={}.\nError-{}".format(
                    outputText, str(e)
                ),
                status_code=response.status_code,
            )

        if stream and provider == "ai21":
            streaming_model_response = ModelResponse(stream=True)
            streaming_model_response.choices[0].finish_reason = model_response.choices[  # type: ignore
                0
            ].finish_reason
            # streaming_model_response.choices = [litellm.utils.StreamingChoices()]
            streaming_choice = litellm.utils.StreamingChoices()
            streaming_choice.index = model_response.choices[0].index
            delta_obj = litellm.utils.Delta(
                content=getattr(model_response.choices[0].message, "content", None),  # type: ignore
                role=model_response.choices[0].message.role,  # type: ignore
            )
            streaming_choice.delta = delta_obj
            streaming_model_response.choices = [streaming_choice]
            mri = ModelResponseIterator(model_response=streaming_model_response)
            return CustomStreamWrapper(
                completion_stream=mri,
                model=model,
                custom_llm_provider="cached_response",
                logging_obj=logging_obj,
            )

        ## CALCULATING USAGE - bedrock returns usage in the headers
        bedrock_input_tokens = response.headers.get(
            "x-amzn-bedrock-input-token-count", None
        )
        bedrock_output_tokens = response.headers.get(
            "x-amzn-bedrock-output-token-count", None
        )

        prompt_tokens = int(
            bedrock_input_tokens or litellm.token_counter(messages=messages)
        )

        completion_tokens = int(
            bedrock_output_tokens
            or litellm.token_counter(
                text=model_response.choices[0].message.content,  # type: ignore
                count_response_tokens=True,
            )
        )

        model_response.created = int(time.time())
        model_response.model = model
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        setattr(model_response, "usage", usage)

        return model_response

    def encode_model_id(self, model_id: str) -> str:
        """
        Double encode the model ID to ensure it matches the expected double-encoded format.
        Args:
            model_id (str): The model ID to encode.
        Returns:
            str: The double-encoded model ID.
        """
        return urllib.parse.quote(model_id, safe="")

    def completion(  # noqa: PLR0915
        self,
        model: str,
        messages: list,
        api_base: Optional[str],
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding,
        logging_obj: Logging,
        optional_params: dict,
        acompletion: bool,
        timeout: Optional[Union[float, httpx.Timeout]],
        litellm_params=None,
        logger_fn=None,
        extra_headers: Optional[dict] = None,
        client: Optional[Union[AsyncHTTPHandler, HTTPHandler]] = None,
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            from botocore.credentials import Credentials
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")

        ## SETUP ##
        stream = optional_params.pop("stream", None)

        provider = self.get_bedrock_invoke_provider(model)
        modelId = self.get_bedrock_model_id(
            model=model,
            provider=provider,
            optional_params=optional_params,
        )

        ## CREDENTIALS ##
        # pop aws_secret_access_key, aws_access_key_id, aws_session_token, aws_region_name from kwargs, since completion calls fail with them
        aws_secret_access_key = optional_params.pop("aws_secret_access_key", None)
        aws_access_key_id = optional_params.pop("aws_access_key_id", None)
        aws_session_token = optional_params.pop("aws_session_token", None)
        aws_region_name = optional_params.pop("aws_region_name", None)
        aws_role_name = optional_params.pop("aws_role_name", None)
        aws_session_name = optional_params.pop("aws_session_name", None)
        aws_profile_name = optional_params.pop("aws_profile_name", None)
        aws_bedrock_runtime_endpoint = optional_params.pop(
            "aws_bedrock_runtime_endpoint", None
        )  # https://bedrock-runtime.{region_name}.amazonaws.com
        aws_web_identity_token = optional_params.pop("aws_web_identity_token", None)
        aws_sts_endpoint = optional_params.pop("aws_sts_endpoint", None)

        ### SET REGION NAME ###
        if aws_region_name is None:
            # check env #
            litellm_aws_region_name = get_secret("AWS_REGION_NAME", None)

            if litellm_aws_region_name is not None and isinstance(
                litellm_aws_region_name, str
            ):
                aws_region_name = litellm_aws_region_name

            standard_aws_region_name = get_secret("AWS_REGION", None)
            if standard_aws_region_name is not None and isinstance(
                standard_aws_region_name, str
            ):
                aws_region_name = standard_aws_region_name

            if aws_region_name is None:
                aws_region_name = "us-west-2"

        credentials: Credentials = self.get_credentials(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            aws_region_name=aws_region_name,
            aws_session_name=aws_session_name,
            aws_profile_name=aws_profile_name,
            aws_role_name=aws_role_name,
            aws_web_identity_token=aws_web_identity_token,
            aws_sts_endpoint=aws_sts_endpoint,
        )

        ### SET RUNTIME ENDPOINT ###
        endpoint_url, proxy_endpoint_url = self.get_runtime_endpoint(
            api_base=api_base,
            aws_bedrock_runtime_endpoint=aws_bedrock_runtime_endpoint,
            aws_region_name=aws_region_name,
        )

        if (stream is not None and stream is True) and provider != "ai21":
            endpoint_url = f"{endpoint_url}/model/{modelId}/invoke-with-response-stream"
            proxy_endpoint_url = (
                f"{proxy_endpoint_url}/model/{modelId}/invoke-with-response-stream"
            )
        else:
            endpoint_url = f"{endpoint_url}/model/{modelId}/invoke"
            proxy_endpoint_url = f"{proxy_endpoint_url}/model/{modelId}/invoke"

        sigv4 = SigV4Auth(credentials, "bedrock", aws_region_name)

        prompt, chat_history = self.convert_messages_to_prompt(
            model, messages, provider, custom_prompt_dict
        )
        inference_params = copy.deepcopy(optional_params)
        json_schemas: dict = {}
        if provider == "cohere":
            if model.startswith("cohere.command-r"):
                ## LOAD CONFIG
                config = litellm.AmazonCohereChatConfig().get_config()
                for k, v in config.items():
                    if (
                        k not in inference_params
                    ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                        inference_params[k] = v
                _data = {"message": prompt, **inference_params}
                if chat_history is not None:
                    _data["chat_history"] = chat_history
                data = json.dumps(_data)
            else:
                ## LOAD CONFIG
                config = litellm.AmazonCohereConfig.get_config()
                for k, v in config.items():
                    if (
                        k not in inference_params
                    ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                        inference_params[k] = v
                if stream is True:
                    inference_params[
                        "stream"
                    ] = True  # cohere requires stream = True in inference params
                data = json.dumps({"prompt": prompt, **inference_params})
        elif provider == "anthropic":
            if model.startswith("anthropic.claude-3"):
                # Separate system prompt from rest of message
                system_prompt_idx: list[int] = []
                system_messages: list[str] = []
                for idx, message in enumerate(messages):
                    if message["role"] == "system":
                        system_messages.append(message["content"])
                        system_prompt_idx.append(idx)
                if len(system_prompt_idx) > 0:
                    inference_params["system"] = "\n".join(system_messages)
                    messages = [
                        i for j, i in enumerate(messages) if j not in system_prompt_idx
                    ]
                # Format rest of message according to anthropic guidelines
                messages = prompt_factory(
                    model=model, messages=messages, custom_llm_provider="anthropic_xml"
                )  # type: ignore
                ## LOAD CONFIG
                config = litellm.AmazonAnthropicClaude3Config.get_config()
                for k, v in config.items():
                    if (
                        k not in inference_params
                    ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                        inference_params[k] = v
                ## Handle Tool Calling
                if "tools" in inference_params:
                    _is_function_call = True
                    for tool in inference_params["tools"]:
                        json_schemas[tool["function"]["name"]] = tool["function"].get(
                            "parameters", None
                        )
                    tool_calling_system_prompt = construct_tool_use_system_prompt(
                        tools=inference_params["tools"]
                    )
                    inference_params["system"] = (
                        inference_params.get("system", "\n")
                        + tool_calling_system_prompt
                    )  # add the anthropic tool calling prompt to the system prompt
                    inference_params.pop("tools")
                data = json.dumps({"messages": messages, **inference_params})
            else:
                ## LOAD CONFIG
                config = litellm.AmazonAnthropicConfig.get_config()
                for k, v in config.items():
                    if (
                        k not in inference_params
                    ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                        inference_params[k] = v
                data = json.dumps({"prompt": prompt, **inference_params})
        elif provider == "ai21":
            ## LOAD CONFIG
            config = litellm.AmazonAI21Config.get_config()
            for k, v in config.items():
                if (
                    k not in inference_params
                ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                    inference_params[k] = v

            data = json.dumps({"prompt": prompt, **inference_params})
        elif provider == "mistral":
            ## LOAD CONFIG
            config = litellm.AmazonMistralConfig.get_config()
            for k, v in config.items():
                if (
                    k not in inference_params
                ):  # completion(top_k=3) > amazon_config(top_k=3) <- allows for dynamic variables to be passed in
                    inference_params[k] = v

            data = json.dumps({"prompt": prompt, **inference_params})
        elif provider == "amazon":  # amazon titan
            ## LOAD CONFIG
            config = litellm.AmazonTitanConfig.get_config()
            for k, v in config.items():
                if (
                    k not in inference_params
                ):  # completion(top_k=3) > amazon_config(top_k=3) <- allows for dynamic variables to be passed in
                    inference_params[k] = v

            data = json.dumps(
                {
                    "inputText": prompt,
                    "textGenerationConfig": inference_params,
                }
            )
        elif provider == "meta" or provider == "llama":
            ## LOAD CONFIG
            config = litellm.AmazonLlamaConfig.get_config()
            for k, v in config.items():
                if (
                    k not in inference_params
                ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                    inference_params[k] = v
            data = json.dumps({"prompt": prompt, **inference_params})
        else:
            ## LOGGING
            logging_obj.pre_call(
                input=messages,
                api_key="",
                additional_args={
                    "complete_input_dict": inference_params,
                },
            )
            raise BedrockError(
                status_code=404,
                message="Bedrock Invoke HTTPX: Unknown provider={}, model={}. Try calling via converse route - `bedrock/converse/<model>`.".format(
                    provider, model
                ),
            )

        ## COMPLETION CALL

        headers = {"Content-Type": "application/json"}
        if extra_headers is not None:
            headers = {"Content-Type": "application/json", **extra_headers}
        request = AWSRequest(
            method="POST", url=endpoint_url, data=data, headers=headers
        )
        sigv4.add_auth(request)
        if (
            extra_headers is not None and "Authorization" in extra_headers
        ):  # prevent sigv4 from overwriting the auth header
            request.headers["Authorization"] = extra_headers["Authorization"]
        prepped = request.prepare()

        ## LOGGING
        logging_obj.pre_call(
            input=messages,
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": proxy_endpoint_url,
                "headers": prepped.headers,
            },
        )

        ### ROUTING (ASYNC, STREAMING, SYNC)
        if acompletion:
            if isinstance(client, HTTPHandler):
                client = None
            if stream is True and provider != "ai21":
                return self.async_streaming(
                    model=model,
                    messages=messages,
                    data=data,
                    api_base=proxy_endpoint_url,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    encoding=encoding,
                    logging_obj=logging_obj,
                    optional_params=optional_params,
                    stream=True,
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    headers=prepped.headers,
                    timeout=timeout,
                    client=client,
                )  # type: ignore
            ### ASYNC COMPLETION
            return self.async_completion(
                model=model,
                messages=messages,
                data=data,
                api_base=proxy_endpoint_url,
                model_response=model_response,
                print_verbose=print_verbose,
                encoding=encoding,
                logging_obj=logging_obj,
                optional_params=optional_params,
                stream=stream,  # type: ignore
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                headers=prepped.headers,
                timeout=timeout,
                client=client,
            )  # type: ignore

        if client is None or isinstance(client, AsyncHTTPHandler):
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    timeout = httpx.Timeout(timeout)
                _params["timeout"] = timeout
            self.client = _get_httpx_client(_params)  # type: ignore
        else:
            self.client = client
        if (stream is not None and stream is True) and provider != "ai21":
            response = self.client.post(
                url=proxy_endpoint_url,
                headers=prepped.headers,  # type: ignore
                data=data,
                stream=stream,
                logging_obj=logging_obj,
            )

            if response.status_code != 200:
                raise BedrockError(
                    status_code=response.status_code, message=str(response.read())
                )

            decoder = AWSEventStreamDecoder(model=model)

            completion_stream = decoder.iter_bytes(response.iter_bytes(chunk_size=1024))
            streaming_response = CustomStreamWrapper(
                completion_stream=completion_stream,
                model=model,
                custom_llm_provider="bedrock",
                logging_obj=logging_obj,
            )

            ## LOGGING
            logging_obj.post_call(
                input=messages,
                api_key="",
                original_response=streaming_response,
                additional_args={"complete_input_dict": data},
            )
            return streaming_response

        try:
            response = self.client.post(
                url=proxy_endpoint_url,
                headers=dict(prepped.headers),
                data=data,
                logging_obj=logging_obj,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise BedrockError(status_code=error_code, message=err.response.text)
        except httpx.TimeoutException:
            raise BedrockError(status_code=408, message="Timeout error occurred.")

        return self.process_response(
            model=model,
            response=response,
            model_response=model_response,
            stream=stream,
            logging_obj=logging_obj,
            optional_params=optional_params,
            api_key="",
            data=data,
            messages=messages,
            print_verbose=print_verbose,
            encoding=encoding,
        )

    async def async_completion(
        self,
        model: str,
        messages: list,
        api_base: str,
        model_response: ModelResponse,
        print_verbose: Callable,
        data: str,
        timeout: Optional[Union[float, httpx.Timeout]],
        encoding,
        logging_obj: Logging,
        stream,
        optional_params: dict,
        litellm_params=None,
        logger_fn=None,
        headers={},
        client: Optional[AsyncHTTPHandler] = None,
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        if client is None:
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    timeout = httpx.Timeout(timeout)
                _params["timeout"] = timeout
            client = get_async_httpx_client(params=_params, llm_provider=litellm.LlmProviders.BEDROCK)  # type: ignore
        else:
            client = client  # type: ignore

        try:
            response = await client.post(
                api_base,
                headers=headers,
                data=data,
                timeout=timeout,
                logging_obj=logging_obj,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise BedrockError(status_code=error_code, message=err.response.text)
        except httpx.TimeoutException:
            raise BedrockError(status_code=408, message="Timeout error occurred.")

        return self.process_response(
            model=model,
            response=response,
            model_response=model_response,
            stream=stream if isinstance(stream, bool) else False,
            logging_obj=logging_obj,
            api_key="",
            data=data,
            messages=messages,
            print_verbose=print_verbose,
            optional_params=optional_params,
            encoding=encoding,
        )

    @track_llm_api_timing()  # for streaming, we need to instrument the function calling the wrapper
    async def async_streaming(
        self,
        model: str,
        messages: list,
        api_base: str,
        model_response: ModelResponse,
        print_verbose: Callable,
        data: str,
        timeout: Optional[Union[float, httpx.Timeout]],
        encoding,
        logging_obj: Logging,
        stream,
        optional_params: dict,
        litellm_params=None,
        logger_fn=None,
        headers={},
        client: Optional[AsyncHTTPHandler] = None,
    ) -> CustomStreamWrapper:
        # The call is not made here; instead, we prepare the necessary objects for the stream.

        streaming_response = CustomStreamWrapper(
            completion_stream=None,
            make_call=partial(
                make_call,
                client=client,
                api_base=api_base,
                headers=headers,
                data=data,  # type: ignore
                model=model,
                messages=messages,
                logging_obj=logging_obj,
                fake_stream=True if "ai21" in api_base else False,
            ),
            model=model,
            custom_llm_provider="bedrock",
            logging_obj=logging_obj,
        )
        return streaming_response

    @staticmethod
    def _get_provider_from_model_path(
        model_path: str,
    ) -> Optional[litellm.BEDROCK_INVOKE_PROVIDERS_LITERAL]:
        """
        Helper function to get the provider from a model path with format: provider/model-name

        Args:
            model_path (str): The model path (e.g., 'llama/arn:aws:bedrock:us-east-1:086734376398:imported-model/r4c4kewx2s0n' or 'anthropic/model-name')

        Returns:
            Optional[str]: The provider name, or None if no valid provider found
        """
        parts = model_path.split("/")
        if len(parts) >= 1:
            provider = parts[0]
            if provider in get_args(litellm.BEDROCK_INVOKE_PROVIDERS_LITERAL):
                return cast(litellm.BEDROCK_INVOKE_PROVIDERS_LITERAL, provider)
        return None

    def get_bedrock_model_id(
        self,
        optional_params: dict,
        provider: Optional[litellm.BEDROCK_INVOKE_PROVIDERS_LITERAL],
        model: str,
    ) -> str:
        modelId = optional_params.pop("model_id", None)
        if modelId is not None:
            modelId = self.encode_model_id(model_id=modelId)
        else:
            modelId = model

        if provider == "llama" and "llama/" in modelId:
            modelId = self._get_model_id_for_llama_like_model(modelId)

        return modelId

    def _get_model_id_for_llama_like_model(
        self,
        model: str,
    ) -> str:
        """
        Remove `llama` from modelID since `llama` is simply a spec to follow for custom bedrock models
        """
        model_id = model.replace("llama/", "")
        return self.encode_model_id(model_id=model_id)


def get_response_stream_shape():
    global _response_stream_shape_cache
    if _response_stream_shape_cache is None:
        from botocore.loaders import Loader
        from botocore.model import ServiceModel

        loader = Loader()
        bedrock_service_dict = loader.load_service_model("bedrock-runtime", "service-2")
        bedrock_service_model = ServiceModel(bedrock_service_dict)
        _response_stream_shape_cache = bedrock_service_model.shape_for("ResponseStream")

    return _response_stream_shape_cache


class AWSEventStreamDecoder:
    def __init__(self, model: str) -> None:
        from botocore.parsers import EventStreamJSONParser

        self.model = model
        self.parser = EventStreamJSONParser()
        self.content_blocks: List[ContentBlockDeltaEvent] = []
        self.tool_calls_index: Optional[int] = None

    def check_empty_tool_call_args(self) -> bool:
        """
        Check if the tool call block so far has been an empty string
        """
        args = ""
        # if text content block -> skip
        if len(self.content_blocks) == 0:
            return False

        if (
            "toolUse" not in self.content_blocks[0]
        ):  # be explicit - only do this if tool use block, as this is to prevent json decoding errors
            return False

        for block in self.content_blocks:
            if "toolUse" in block:
                args += block["toolUse"]["input"]

        if len(args) == 0:
            return True
        return False

    def extract_reasoning_content_str(
        self, reasoning_content_block: BedrockConverseReasoningContentBlockDelta
    ) -> Optional[str]:
        if "text" in reasoning_content_block:
            return reasoning_content_block["text"]
        return None

    def translate_thinking_blocks(
        self, thinking_block: BedrockConverseReasoningContentBlockDelta
    ) -> Optional[
        List[Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]]
    ]:
        """
        Translate the thinking blocks to a string
        """

        thinking_blocks_list: List[
            Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]
        ] = []
        _thinking_block: Optional[
            Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]
        ] = None

        if "text" in thinking_block:
            _thinking_block = ChatCompletionThinkingBlock(type="thinking")
            _thinking_block["thinking"] = thinking_block["text"]
        elif "signature" in thinking_block:
            _thinking_block = ChatCompletionThinkingBlock(type="thinking")
            _thinking_block["signature"] = thinking_block["signature"]
            _thinking_block["thinking"] = ""  # consistent with anthropic response
        elif "redactedContent" in thinking_block:
            _thinking_block = ChatCompletionRedactedThinkingBlock(
                type="redacted_thinking", data=thinking_block["redactedContent"]
            )
        if _thinking_block is not None:
            thinking_blocks_list.append(_thinking_block)
        return thinking_blocks_list

    def converse_chunk_parser(self, chunk_data: dict) -> ModelResponseStream:
        try:
            verbose_logger.debug("\n\nRaw Chunk: {}\n\n".format(chunk_data))
            text = ""
            tool_use: Optional[ChatCompletionToolCallChunk] = None
            finish_reason = ""
            usage: Optional[Usage] = None
            provider_specific_fields: dict = {}
            reasoning_content: Optional[str] = None
            thinking_blocks: Optional[
                List[
                    Union[
                        ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock
                    ]
                ]
            ] = None

            index = int(chunk_data.get("contentBlockIndex", 0))
            if "start" in chunk_data:
                start_obj = ContentBlockStartEvent(**chunk_data["start"])
                self.content_blocks = []  # reset
                if start_obj is not None:
                    if "toolUse" in start_obj and start_obj["toolUse"] is not None:
                        ## check tool name was formatted by litellm
                        _response_tool_name = start_obj["toolUse"]["name"]
                        response_tool_name = get_bedrock_tool_name(
                            response_tool_name=_response_tool_name
                        )
                        self.tool_calls_index = (
                            0
                            if self.tool_calls_index is None
                            else self.tool_calls_index + 1
                        )
                        tool_use = {
                            "id": start_obj["toolUse"]["toolUseId"],
                            "type": "function",
                            "function": {
                                "name": response_tool_name,
                                "arguments": "",
                            },
                            "index": self.tool_calls_index,
                        }
                    elif (
                        "reasoningContent" in start_obj
                        and start_obj["reasoningContent"] is not None
                    ):  # redacted thinking can be in start object
                        thinking_blocks = self.translate_thinking_blocks(
                            start_obj["reasoningContent"]
                        )
                        provider_specific_fields = {
                            "reasoningContent": start_obj["reasoningContent"],
                        }
            elif "delta" in chunk_data:
                delta_obj = ContentBlockDeltaEvent(**chunk_data["delta"])
                self.content_blocks.append(delta_obj)
                if "text" in delta_obj:
                    text = delta_obj["text"]
                elif "toolUse" in delta_obj:
                    tool_use = {
                        "id": None,
                        "type": "function",
                        "function": {
                            "name": None,
                            "arguments": delta_obj["toolUse"]["input"],
                        },
                        "index": self.tool_calls_index
                        if self.tool_calls_index is not None
                        else index,
                    }
                elif "reasoningContent" in delta_obj:
                    provider_specific_fields = {
                        "reasoningContent": delta_obj["reasoningContent"],
                    }
                    reasoning_content = self.extract_reasoning_content_str(
                        delta_obj["reasoningContent"]
                    )
                    thinking_blocks = self.translate_thinking_blocks(
                        delta_obj["reasoningContent"]
                    )
                    if (
                        thinking_blocks
                        and len(thinking_blocks) > 0
                        and reasoning_content is None
                    ):
                        reasoning_content = ""  # set to non-empty string to ensure consistency with Anthropic
            elif (
                "contentBlockIndex" in chunk_data
            ):  # stop block, no 'start' or 'delta' object
                is_empty = self.check_empty_tool_call_args()
                if is_empty:
                    tool_use = {
                        "id": None,
                        "type": "function",
                        "function": {
                            "name": None,
                            "arguments": "{}",
                        },
                        "index": chunk_data["contentBlockIndex"],
                    }
            elif "stopReason" in chunk_data:
                finish_reason = map_finish_reason(chunk_data.get("stopReason", "stop"))
            elif "usage" in chunk_data:
                usage = converse_config._transform_usage(chunk_data.get("usage", {}))

            model_response_provider_specific_fields = {}
            if "trace" in chunk_data:
                trace = chunk_data.get("trace")
                model_response_provider_specific_fields["trace"] = trace
            response = ModelResponseStream(
                choices=[
                    StreamingChoices(
                        finish_reason=finish_reason,
                        index=index,
                        delta=Delta(
                            content=text,
                            role="assistant",
                            tool_calls=[tool_use] if tool_use else None,
                            provider_specific_fields=(
                                provider_specific_fields
                                if provider_specific_fields
                                else None
                            ),
                            thinking_blocks=thinking_blocks,
                            reasoning_content=reasoning_content,
                        ),
                    )
                ],
                usage=usage,
                provider_specific_fields=model_response_provider_specific_fields,
            )

            return response
        except Exception as e:
            raise Exception("Received streaming error - {}".format(str(e)))

    def _chunk_parser(
        self, chunk_data: dict
    ) -> Union[GChunk, ModelResponseStream, dict]:
        text = ""
        is_finished = False
        finish_reason = ""
        if "outputText" in chunk_data:
            text = chunk_data["outputText"]
        # ai21 mapping
        elif "ai21" in self.model:  # fake ai21 streaming
            text = chunk_data.get("completions")[0].get("data").get("text")  # type: ignore
            is_finished = True
            finish_reason = "stop"
        ######## /bedrock/converse mappings ###############
        elif (
            "contentBlockIndex" in chunk_data
            or "stopReason" in chunk_data
            or "metrics" in chunk_data
            or "trace" in chunk_data
        ):
            return self.converse_chunk_parser(chunk_data=chunk_data)
        ######### /bedrock/invoke nova mappings ###############
        elif "contentBlockDelta" in chunk_data:
            # when using /bedrock/invoke/nova, the chunk_data is nested under "contentBlockDelta"
            _chunk_data = chunk_data.get("contentBlockDelta", None)
            return self.converse_chunk_parser(chunk_data=_chunk_data)
        ######## bedrock.mistral mappings ###############
        elif "outputs" in chunk_data:
            if (
                len(chunk_data["outputs"]) == 1
                and chunk_data["outputs"][0].get("text", None) is not None
            ):
                text = chunk_data["outputs"][0]["text"]
            stop_reason = chunk_data.get("stop_reason", None)
            if stop_reason is not None:
                is_finished = True
                finish_reason = stop_reason
        ######## bedrock.cohere mappings ###############
        # meta mapping
        elif "generation" in chunk_data:
            text = chunk_data["generation"]  # bedrock.meta
        # cohere mapping
        elif "text" in chunk_data:
            text = chunk_data["text"]  # bedrock.cohere
        # cohere mapping for finish reason
        elif "finish_reason" in chunk_data:
            finish_reason = chunk_data["finish_reason"]
            is_finished = True
        elif chunk_data.get("completionReason", None):
            is_finished = True
            finish_reason = chunk_data["completionReason"]
        return GChunk(
            text=text,
            is_finished=is_finished,
            finish_reason=finish_reason,
            usage=None,
            index=0,
            tool_use=None,
        )

    def iter_bytes(
        self, iterator: Iterator[bytes]
    ) -> Iterator[Union[GChunk, ModelResponseStream, dict]]:
        """Given an iterator that yields lines, iterate over it & yield every event encountered"""
        from botocore.eventstream import EventStreamBuffer

        event_stream_buffer = EventStreamBuffer()
        for chunk in iterator:
            event_stream_buffer.add_data(chunk)
            for event in event_stream_buffer:
                message = self._parse_message_from_event(event)
                if message:
                    # sse_event = ServerSentEvent(data=message, event="completion")
                    _data = json.loads(message)
                    yield self._chunk_parser(chunk_data=_data)

    async def aiter_bytes(
        self, iterator: AsyncIterator[bytes]
    ) -> AsyncIterator[Union[GChunk, ModelResponseStream, dict]]:
        """Given an async iterator that yields lines, iterate over it & yield every event encountered"""
        from botocore.eventstream import EventStreamBuffer

        event_stream_buffer = EventStreamBuffer()
        async for chunk in iterator:
            event_stream_buffer.add_data(chunk)
            for event in event_stream_buffer:
                message = self._parse_message_from_event(event)
                if message:
                    _data = json.loads(message)
                    yield self._chunk_parser(chunk_data=_data)

    def _parse_message_from_event(self, event) -> Optional[str]:
        response_dict = event.to_response_dict()
        parsed_response = self.parser.parse(response_dict, get_response_stream_shape())

        if response_dict["status_code"] != 200:
            decoded_body = response_dict["body"].decode()
            if isinstance(decoded_body, dict):
                error_message = decoded_body.get("message")
            elif isinstance(decoded_body, str):
                error_message = decoded_body
            else:
                error_message = ""
            exception_status = response_dict["headers"].get(":exception-type")
            error_message = exception_status + " " + error_message
            raise BedrockError(
                status_code=response_dict["status_code"],
                message=(
                    json.dumps(error_message)
                    if isinstance(error_message, dict)
                    else error_message
                ),
            )
        if "chunk" in parsed_response:
            chunk = parsed_response.get("chunk")
            if not chunk:
                return None
            return chunk.get("bytes").decode()  # type: ignore[no-any-return]
        else:
            chunk = response_dict.get("body")
            if not chunk:
                return None

            return chunk.decode()  # type: ignore[no-any-return]


class AmazonAnthropicClaudeStreamDecoder(AWSEventStreamDecoder):
    def __init__(
        self,
        model: str,
        sync_stream: bool,
        json_mode: Optional[bool] = None,
    ) -> None:
        """
        Child class of AWSEventStreamDecoder that handles the streaming response from the Anthropic family of models

        The only difference between AWSEventStreamDecoder and AmazonAnthropicClaudeStreamDecoder is the `chunk_parser` method
        """
        super().__init__(model=model)
        self.anthropic_model_response_iterator = AnthropicModelResponseIterator(
            streaming_response=None,
            sync_stream=sync_stream,
            json_mode=json_mode,
        )

    def _chunk_parser(self, chunk_data: dict) -> ModelResponseStream:
        return self.anthropic_model_response_iterator.chunk_parser(chunk=chunk_data)


class AmazonDeepSeekR1StreamDecoder(AWSEventStreamDecoder):
    def __init__(
        self,
        model: str,
        sync_stream: bool,
    ) -> None:
        super().__init__(model=model)
        from litellm.llms.bedrock.chat.invoke_transformations.amazon_deepseek_transformation import (
            AmazonDeepseekR1ResponseIterator,
        )

        self.deepseek_model_response_iterator = AmazonDeepseekR1ResponseIterator(
            streaming_response=None,
            sync_stream=sync_stream,
        )

    def _chunk_parser(
        self, chunk_data: dict
    ) -> Union[GChunk, ModelResponseStream, dict]:
        return self.deepseek_model_response_iterator.chunk_parser(chunk=chunk_data)


class MockResponseIterator:  # for returning ai21 streaming responses
    def __init__(self, model_response, json_mode: Optional[bool] = False):
        self.model_response = model_response
        self.json_mode = json_mode
        self.is_done = False

    # Sync iterator
    def __iter__(self):
        return self

    def _handle_json_mode_chunk(
        self, text: str, tool_calls: Optional[List[ChatCompletionToolCallChunk]]
    ) -> Tuple[str, Optional[ChatCompletionToolCallChunk]]:
        """
        If JSON mode is enabled, convert the tool call to a message.

        Bedrock returns the JSON schema as part of the tool call
        OpenAI returns the JSON schema as part of the content, this handles placing it in the content

        Args:
            text: str
            tool_use: Optional[ChatCompletionToolCallChunk]
        Returns:
            Tuple[str, Optional[ChatCompletionToolCallChunk]]

            text: The text to use in the content
            tool_use: The ChatCompletionToolCallChunk to use in the chunk response
        """
        tool_use: Optional[ChatCompletionToolCallChunk] = None
        if self.json_mode is True and tool_calls is not None:
            message = litellm.AnthropicConfig()._convert_tool_response_to_message(
                tool_calls=tool_calls
            )
            if message is not None:
                text = message.content or ""
                tool_use = None
        elif tool_calls is not None and len(tool_calls) > 0:
            tool_use = tool_calls[0]
        return text, tool_use

    def _chunk_parser(self, chunk_data: ModelResponse) -> GChunk:
        try:
            chunk_usage: Usage = getattr(chunk_data, "usage")
            text = chunk_data.choices[0].message.content or ""  # type: ignore
            tool_use = None
            _model_response_tool_call = cast(
                Optional[List[ChatCompletionMessageToolCall]],
                cast(Choices, chunk_data.choices[0]).message.tool_calls,
            )
            if self.json_mode is True:
                text, tool_use = self._handle_json_mode_chunk(
                    text=text,
                    tool_calls=chunk_data.choices[0].message.tool_calls,  # type: ignore
                )
            elif _model_response_tool_call is not None:
                tool_use = ChatCompletionToolCallChunk(
                    id=_model_response_tool_call[0].id,
                    type="function",
                    function=ChatCompletionToolCallFunctionChunk(
                        name=_model_response_tool_call[0].function.name,
                        arguments=_model_response_tool_call[0].function.arguments,
                    ),
                    index=0,
                )
            processed_chunk = GChunk(
                text=text,
                tool_use=tool_use,
                is_finished=True,
                finish_reason=map_finish_reason(
                    finish_reason=chunk_data.choices[0].finish_reason or ""
                ),
                usage=ChatCompletionUsageBlock(
                    prompt_tokens=chunk_usage.prompt_tokens,
                    completion_tokens=chunk_usage.completion_tokens,
                    total_tokens=chunk_usage.total_tokens,
                ),
                index=0,
            )
            return processed_chunk
        except Exception as e:
            raise ValueError(f"Failed to decode chunk: {chunk_data}. Error: {e}")

    def __next__(self):
        if self.is_done:
            raise StopIteration
        self.is_done = True
        return self._chunk_parser(self.model_response)

    # Async iterator
    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.is_done:
            raise StopAsyncIteration
        self.is_done = True
        return self._chunk_parser(self.model_response)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\auth\auth_checks.py ===
# What is this?
## Common auth checks between jwt + key based auth
"""
Got Valid Token from Cache, DB
Run checks for:

1. If user can call model
2. If user is in budget
3. If end_user ('user' passed to /chat/completions, /embeddings endpoint) is in budget
"""
import asyncio
import re
import time
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union, cast

from fastapi import Request, status
from pydantic import BaseModel

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.caching.caching import DualCache
from litellm.caching.dual_cache import LimitedSizeOrderedDict
from litellm.constants import (
    DEFAULT_IN_MEMORY_TTL,
    DEFAULT_MANAGEMENT_OBJECT_IN_MEMORY_CACHE_TTL,
    DEFAULT_MAX_RECURSE_DEPTH,
)
from litellm.litellm_core_utils.get_llm_provider_logic import get_llm_provider
from litellm.proxy._types import (
    RBAC_ROLES,
    CallInfo,
    LiteLLM_EndUserTable,
    Litellm_EntityType,
    LiteLLM_JWTAuth,
    LiteLLM_ObjectPermissionTable,
    LiteLLM_OrganizationMembershipTable,
    LiteLLM_OrganizationTable,
    LiteLLM_TeamTable,
    LiteLLM_TeamTableCachedObj,
    LiteLLM_UserTable,
    LiteLLMRoutes,
    LitellmUserRoles,
    ProxyErrorTypes,
    ProxyException,
    RoleBasedPermissions,
    SpecialModelNames,
    UserAPIKeyAuth,
)
from litellm.proxy.auth.route_checks import RouteChecks
from litellm.proxy.route_llm_request import route_request
from litellm.proxy.utils import PrismaClient, ProxyLogging, log_db_metrics
from litellm.router import Router
from litellm.utils import get_utc_datetime

from .auth_checks_organization import organization_role_based_access_check
from .auth_utils import get_model_from_request

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    Span = Union[_Span, Any]
else:
    Span = Any


last_db_access_time = LimitedSizeOrderedDict(max_size=100)
db_cache_expiry = DEFAULT_IN_MEMORY_TTL  # refresh every 5s

all_routes = LiteLLMRoutes.openai_routes.value + LiteLLMRoutes.management_routes.value


async def common_checks(
    request_body: dict,
    team_object: Optional[LiteLLM_TeamTable],
    user_object: Optional[LiteLLM_UserTable],
    end_user_object: Optional[LiteLLM_EndUserTable],
    global_proxy_spend: Optional[float],
    general_settings: dict,
    route: str,
    llm_router: Optional[Router],
    proxy_logging_obj: ProxyLogging,
    valid_token: Optional[UserAPIKeyAuth],
    request: Request,
) -> bool:
    """
    Common checks across jwt + key-based auth.

    1. If team is blocked
    2. If team can call model
    3. If team is in budget
    4. If user passed in (JWT or key.user_id) - is in budget
    5. If end_user (either via JWT or 'user' passed to /chat/completions, /embeddings endpoint) is in budget
    6. [OPTIONAL] If 'enforce_end_user' enabled - did developer pass in 'user' param for openai endpoints
    7. [OPTIONAL] If 'litellm.max_budget' is set (>0), is proxy under budget
    8. [OPTIONAL] If guardrails modified - is request allowed to change this
    9. Check if request body is safe
    10. [OPTIONAL] Organization checks - is user_object.organization_id is set, run these checks
    11. [OPTIONAL] Vector store checks - is the object allowed to access the vector store
    """
    _model: Optional[Union[str, List[str]]] = get_model_from_request(
        request_body, route
    )

    # 1. If team is blocked
    if team_object is not None and team_object.blocked is True:
        raise Exception(
            f"Team={team_object.team_id} is blocked. Update via `/team/unblock` if your admin."
        )

    # 2. If team can call model
    if _model and team_object:
        if not can_team_access_model(
            model=_model,
            team_object=team_object,
            llm_router=llm_router,
            team_model_aliases=valid_token.team_model_aliases if valid_token else None,
        ):
            raise ProxyException(
                message=f"Team not allowed to access model. Team={team_object.team_id}, Model={_model}. Allowed team models = {team_object.models}",
                type=ProxyErrorTypes.team_model_access_denied,
                param="model",
                code=status.HTTP_401_UNAUTHORIZED,
            )

    ## 2.1 If user can call model (if personal key)
    if _model and team_object is None and user_object is not None:
        await can_user_call_model(
            model=_model,
            llm_router=llm_router,
            user_object=user_object,
        )

    # 3. If team is in budget
    await _team_max_budget_check(
        team_object=team_object,
        proxy_logging_obj=proxy_logging_obj,
        valid_token=valid_token,
    )

    # 4. If user is in budget
    ## 4.1 check personal budget, if personal key
    if (
        (team_object is None or team_object.team_id is None)
        and user_object is not None
        and user_object.max_budget is not None
    ):
        user_budget = user_object.max_budget
        if user_budget < user_object.spend:
            raise litellm.BudgetExceededError(
                current_cost=user_object.spend,
                max_budget=user_budget,
                message=f"ExceededBudget: User={user_object.user_id} over budget. Spend={user_object.spend}, Budget={user_budget}",
            )

    ## 4.2 check team member budget, if team key
    # 5. If end_user ('user' passed to /chat/completions, /embeddings endpoint) is in budget
    if end_user_object is not None and end_user_object.litellm_budget_table is not None:
        end_user_budget = end_user_object.litellm_budget_table.max_budget
        if end_user_budget is not None and end_user_object.spend > end_user_budget:
            raise litellm.BudgetExceededError(
                current_cost=end_user_object.spend,
                max_budget=end_user_budget,
                message=f"ExceededBudget: End User={end_user_object.user_id} over budget. Spend={end_user_object.spend}, Budget={end_user_budget}",
            )

    # 6. [OPTIONAL] If 'enforce_user_param' enabled - did developer pass in 'user' param for openai endpoints
    if (
        general_settings.get("enforce_user_param", None) is not None
        and general_settings["enforce_user_param"] is True
    ):
        if RouteChecks.is_llm_api_route(route=route) and "user" not in request_body:
            raise Exception(
                f"'user' param not passed in. 'enforce_user_param'={general_settings['enforce_user_param']}"
            )
    # 7. [OPTIONAL] If 'litellm.max_budget' is set (>0), is proxy under budget
    if (
        litellm.max_budget > 0
        and global_proxy_spend is not None
        # only run global budget checks for OpenAI routes
        # Reason - the Admin UI should continue working if the proxy crosses it's global budget
        and RouteChecks.is_llm_api_route(route=route)
        and route != "/v1/models"
        and route != "/models"
    ):
        if global_proxy_spend > litellm.max_budget:
            raise litellm.BudgetExceededError(
                current_cost=global_proxy_spend, max_budget=litellm.max_budget
            )

    _request_metadata: dict = request_body.get("metadata", {}) or {}
    if _request_metadata.get("guardrails"):
        # check if team allowed to modify guardrails
        from litellm.proxy.guardrails.guardrail_helpers import can_modify_guardrails

        can_modify: bool = can_modify_guardrails(team_object)
        if can_modify is False:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Your team does not have permission to modify guardrails."
                },
            )

    # 10 [OPTIONAL] Organization RBAC checks
    organization_role_based_access_check(
        user_object=user_object, route=route, request_body=request_body
    )

    token_team = getattr(valid_token, "team_id", None)
    token_type: Literal["ui", "api"] = (
        "ui" if token_team is not None and token_team == "litellm-dashboard" else "api"
    )
    _is_route_allowed = _is_allowed_route(
        route=route,
        token_type=token_type,
        user_obj=user_object,
        request=request,
        request_data=request_body,
        valid_token=valid_token,
    )

    # 11. [OPTIONAL] Vector store checks - is the object allowed to access the vector store
    await vector_store_access_check(
        request_body=request_body,
        team_object=team_object,
        valid_token=valid_token,
    )

    return True


def _is_ui_route(
    route: str,
    user_obj: Optional[LiteLLM_UserTable] = None,
) -> bool:
    """
    - Check if the route is a UI used route
    """
    # this token is only used for managing the ui
    allowed_routes = LiteLLMRoutes.ui_routes.value
    # check if the current route startswith any of the allowed routes
    if (
        route is not None
        and isinstance(route, str)
        and any(route.startswith(allowed_route) for allowed_route in allowed_routes)
    ):
        # Do something if the current route starts with any of the allowed routes
        return True
    elif any(
        RouteChecks._route_matches_pattern(route=route, pattern=allowed_route)
        for allowed_route in allowed_routes
    ):
        return True
    return False


def _get_user_role(
    user_obj: Optional[LiteLLM_UserTable],
) -> Optional[LitellmUserRoles]:
    if user_obj is None:
        return None

    _user = user_obj

    _user_role = _user.user_role
    try:
        role = LitellmUserRoles(_user_role)
    except ValueError:
        return LitellmUserRoles.INTERNAL_USER

    return role


def _is_api_route_allowed(
    route: str,
    request: Request,
    request_data: dict,
    valid_token: Optional[UserAPIKeyAuth],
    user_obj: Optional[LiteLLM_UserTable] = None,
) -> bool:
    """
    - Route b/w api token check and normal token check
    """
    _user_role = _get_user_role(user_obj=user_obj)

    if valid_token is None:
        raise Exception("Invalid proxy server token passed. valid_token=None.")

    # Check if Virtual Key is allowed to call the route - Applies to all Roles
    RouteChecks.is_virtual_key_allowed_to_call_route(
        route=route, valid_token=valid_token
    )

    if not _is_user_proxy_admin(user_obj=user_obj):  # if non-admin
        RouteChecks.non_proxy_admin_allowed_routes_check(
            user_obj=user_obj,
            _user_role=_user_role,
            route=route,
            request=request,
            request_data=request_data,
            valid_token=valid_token,
        )
    return True


def _is_user_proxy_admin(user_obj: Optional[LiteLLM_UserTable]):
    if user_obj is None:
        return False

    if (
        user_obj.user_role is not None
        and user_obj.user_role == LitellmUserRoles.PROXY_ADMIN.value
    ):
        return True

    if (
        user_obj.user_role is not None
        and user_obj.user_role == LitellmUserRoles.PROXY_ADMIN.value
    ):
        return True

    return False


def _is_allowed_route(
    route: str,
    token_type: Literal["ui", "api"],
    request: Request,
    request_data: dict,
    valid_token: Optional[UserAPIKeyAuth],
    user_obj: Optional[LiteLLM_UserTable] = None,
) -> bool:
    """
    - Route b/w ui token check and normal token check
    """

    if token_type == "ui" and _is_ui_route(route=route, user_obj=user_obj):
        return True
    else:
        return _is_api_route_allowed(
            route=route,
            request=request,
            request_data=request_data,
            valid_token=valid_token,
            user_obj=user_obj,
        )


def _allowed_routes_check(user_route: str, allowed_routes: list) -> bool:
    """
    Return if a user is allowed to access route. Helper function for `allowed_routes_check`.

    Parameters:
    - user_route: str - the route the user is trying to call
    - allowed_routes: List[str|LiteLLMRoutes] - the list of allowed routes for the user.
    """

    for allowed_route in allowed_routes:
        if (
            allowed_route in LiteLLMRoutes.__members__
            and user_route in LiteLLMRoutes[allowed_route].value
        ):
            return True
        elif allowed_route == user_route:
            return True
    return False


def allowed_routes_check(
    user_role: Literal[
        LitellmUserRoles.PROXY_ADMIN,
        LitellmUserRoles.TEAM,
        LitellmUserRoles.INTERNAL_USER,
    ],
    user_route: str,
    litellm_proxy_roles: LiteLLM_JWTAuth,
) -> bool:
    """
    Check if user -> not admin - allowed to access these routes
    """

    if user_role == LitellmUserRoles.PROXY_ADMIN:
        is_allowed = _allowed_routes_check(
            user_route=user_route,
            allowed_routes=litellm_proxy_roles.admin_allowed_routes,
        )
        return is_allowed

    elif user_role == LitellmUserRoles.TEAM:
        if litellm_proxy_roles.team_allowed_routes is None:
            """
            By default allow a team to call openai + info routes
            """
            is_allowed = _allowed_routes_check(
                user_route=user_route, allowed_routes=["openai_routes", "info_routes"]
            )
            return is_allowed
        elif litellm_proxy_roles.team_allowed_routes is not None:
            is_allowed = _allowed_routes_check(
                user_route=user_route,
                allowed_routes=litellm_proxy_roles.team_allowed_routes,
            )
            return is_allowed
    return False


def allowed_route_check_inside_route(
    user_api_key_dict: UserAPIKeyAuth,
    requested_user_id: Optional[str],
) -> bool:
    ret_val = True
    if (
        user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN
        and user_api_key_dict.user_role != LitellmUserRoles.PROXY_ADMIN_VIEW_ONLY
    ):
        ret_val = False
    if requested_user_id is not None and user_api_key_dict.user_id is not None:
        if user_api_key_dict.user_id == requested_user_id:
            ret_val = True
    return ret_val


def get_actual_routes(allowed_routes: list) -> list:
    actual_routes: list = []
    for route_name in allowed_routes:
        try:
            route_value = LiteLLMRoutes[route_name].value
            if isinstance(route_value, set):
                actual_routes.extend(list(route_value))
            else:
                actual_routes.extend(route_value)

        except KeyError:
            actual_routes.append(route_name)
    return actual_routes


@log_db_metrics
async def get_end_user_object(
    end_user_id: Optional[str],
    prisma_client: Optional[PrismaClient],
    user_api_key_cache: DualCache,
    parent_otel_span: Optional[Span] = None,
    proxy_logging_obj: Optional[ProxyLogging] = None,
) -> Optional[LiteLLM_EndUserTable]:
    """
    Returns end user object, if in db.

    Do a isolated check for end user in table vs. doing a combined key + team + user + end-user check, as key might come in frequently for different end-users. Larger call will slowdown query time. This way we get to cache the constant (key/team/user info) and only update based on the changing value (end-user).
    """
    if prisma_client is None:
        raise Exception("No db connected")

    if end_user_id is None:
        return None
    _key = "end_user_id:{}".format(end_user_id)

    def check_in_budget(end_user_obj: LiteLLM_EndUserTable):
        if end_user_obj.litellm_budget_table is None:
            return
        end_user_budget = end_user_obj.litellm_budget_table.max_budget
        if end_user_budget is not None and end_user_obj.spend > end_user_budget:
            raise litellm.BudgetExceededError(
                current_cost=end_user_obj.spend, max_budget=end_user_budget
            )

    # check if in cache
    cached_user_obj = await user_api_key_cache.async_get_cache(key=_key)
    if cached_user_obj is not None:
        if isinstance(cached_user_obj, dict):
            return_obj = LiteLLM_EndUserTable(**cached_user_obj)
            check_in_budget(end_user_obj=return_obj)
            return return_obj
        elif isinstance(cached_user_obj, LiteLLM_EndUserTable):
            return_obj = cached_user_obj
            check_in_budget(end_user_obj=return_obj)
            return return_obj
    # else, check db
    try:
        response = await prisma_client.db.litellm_endusertable.find_unique(
            where={"user_id": end_user_id},
            include={"litellm_budget_table": True},
        )

        if response is None:
            raise Exception

        # save the end-user object to cache
        await user_api_key_cache.async_set_cache(
            key="end_user_id:{}".format(end_user_id), value=response
        )

        _response = LiteLLM_EndUserTable(**response.dict())

        check_in_budget(end_user_obj=_response)

        return _response
    except Exception as e:  # if end-user not in db
        if isinstance(e, litellm.BudgetExceededError):
            raise e
        return None


def model_in_access_group(
    model: str, team_models: Optional[List[str]], llm_router: Optional[Router]
) -> bool:
    from collections import defaultdict

    if team_models is None:
        return True
    if model in team_models:
        return True

    access_groups: dict[str, list[str]] = defaultdict(list)
    if llm_router:
        access_groups = llm_router.get_model_access_groups(model_name=model)

    if len(access_groups) > 0:  # check if token contains any model access groups
        for idx, m in enumerate(
            team_models
        ):  # loop token models, if any of them are an access group add the access group
            if m in access_groups:
                return True

    # Filter out models that are access_groups
    filtered_models = [m for m in team_models if m not in access_groups]

    if model in filtered_models:
        return True

    return False


def _should_check_db(
    key: str, last_db_access_time: LimitedSizeOrderedDict, db_cache_expiry: int
) -> bool:
    """
    Prevent calling db repeatedly for items that don't exist in the db.
    """
    current_time = time.time()
    # if key doesn't exist in last_db_access_time -> check db
    if key not in last_db_access_time:
        return True
    elif (
        last_db_access_time[key][0] is not None
    ):  # check db for non-null values (for refresh operations)
        return True
    elif last_db_access_time[key][0] is None:
        if current_time - last_db_access_time[key] >= db_cache_expiry:
            return True
    return False


def _update_last_db_access_time(
    key: str, value: Optional[Any], last_db_access_time: LimitedSizeOrderedDict
):
    last_db_access_time[key] = (value, time.time())


def _get_role_based_permissions(
    rbac_role: RBAC_ROLES,
    general_settings: dict,
    key: Literal["models", "routes"],
) -> Optional[List[str]]:
    """
    Get the role based permissions from the general settings.
    """
    role_based_permissions = cast(
        Optional[List[RoleBasedPermissions]],
        general_settings.get("role_permissions", []),
    )
    if role_based_permissions is None:
        return None

    for role_based_permission in role_based_permissions:
        if role_based_permission.role == rbac_role:
            return getattr(role_based_permission, key)

    return None


def get_role_based_models(
    rbac_role: RBAC_ROLES,
    general_settings: dict,
) -> Optional[List[str]]:
    """
    Get the models allowed for a user role.

    Used by JWT Auth.
    """

    return _get_role_based_permissions(
        rbac_role=rbac_role,
        general_settings=general_settings,
        key="models",
    )


def get_role_based_routes(
    rbac_role: RBAC_ROLES,
    general_settings: dict,
) -> Optional[List[str]]:
    """
    Get the routes allowed for a user role.
    """

    return _get_role_based_permissions(
        rbac_role=rbac_role,
        general_settings=general_settings,
        key="routes",
    )


async def _get_fuzzy_user_object(
    prisma_client: PrismaClient,
    sso_user_id: Optional[str] = None,
    user_email: Optional[str] = None,
) -> Optional[LiteLLM_UserTable]:
    """
    Checks if sso user is in db.

    Called when user id match is not found in db.

    - Check if sso_user_id is user_id in db
    - Check if sso_user_id is sso_user_id in db
    - Check if user_email is user_email in db
    - If not, create new user with user_email and sso_user_id and user_id = sso_user_id
    """

    response = None
    if sso_user_id is not None:
        response = await prisma_client.db.litellm_usertable.find_unique(
            where={"sso_user_id": sso_user_id},
            include={"organization_memberships": True},
        )

    if response is None and user_email is not None:
        response = await prisma_client.db.litellm_usertable.find_first(
            where={"user_email": user_email},
            include={"organization_memberships": True},
        )

        if response is not None and sso_user_id is not None:  # update sso_user_id
            asyncio.create_task(  # background task to update user with sso id
                prisma_client.db.litellm_usertable.update(
                    where={"user_id": response.user_id},
                    data={"sso_user_id": sso_user_id},
                )
            )

    return response


@log_db_metrics
async def get_user_object(
    user_id: Optional[str],
    prisma_client: Optional[PrismaClient],
    user_api_key_cache: DualCache,
    user_id_upsert: bool,
    parent_otel_span: Optional[Span] = None,
    proxy_logging_obj: Optional[ProxyLogging] = None,
    sso_user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    check_db_only: Optional[bool] = None,
) -> Optional[LiteLLM_UserTable]:
    """
    - Check if user id in proxy User Table
    - if valid, return LiteLLM_UserTable object with defined limits
    - if not, then raise an error
    """

    if user_id is None:
        return None

    # check if in cache
    if not check_db_only:
        cached_user_obj = await user_api_key_cache.async_get_cache(key=user_id)
        if cached_user_obj is not None:
            if isinstance(cached_user_obj, dict):
                return LiteLLM_UserTable(**cached_user_obj)
            elif isinstance(cached_user_obj, LiteLLM_UserTable):
                return cached_user_obj
    # else, check db
    if prisma_client is None:
        raise Exception("No db connected")
    try:
        db_access_time_key = "user_id:{}".format(user_id)
        should_check_db = _should_check_db(
            key=db_access_time_key,
            last_db_access_time=last_db_access_time,
            db_cache_expiry=db_cache_expiry,
        )

        if should_check_db:
            response = await prisma_client.db.litellm_usertable.find_unique(
                where={"user_id": user_id}, include={"organization_memberships": True}
            )

            if response is None:
                response = await _get_fuzzy_user_object(
                    prisma_client=prisma_client,
                    sso_user_id=sso_user_id,
                    user_email=user_email,
                )

        else:
            response = None

        if response is None:
            if user_id_upsert:
                new_user_params: Dict[str, Any] = {
                    "user_id": user_id,
                }
                if litellm.default_internal_user_params is not None:
                    new_user_params.update(litellm.default_internal_user_params)

                response = await prisma_client.db.litellm_usertable.create(
                    data=new_user_params,
                    include={"organization_memberships": True},
                )
            else:
                raise Exception

        if (
            response.organization_memberships is not None
            and len(response.organization_memberships) > 0
        ):
            # dump each organization membership to type LiteLLM_OrganizationMembershipTable
            _dumped_memberships = [
                LiteLLM_OrganizationMembershipTable(**membership.model_dump())
                for membership in response.organization_memberships
                if membership is not None
            ]
            response.organization_memberships = _dumped_memberships

        _response = LiteLLM_UserTable(**dict(response))
        response_dict = _response.model_dump()

        # save the user object to cache
        await user_api_key_cache.async_set_cache(
            key=user_id,
            value=response_dict,
            ttl=DEFAULT_MANAGEMENT_OBJECT_IN_MEMORY_CACHE_TTL,
        )

        # save to db access time
        _update_last_db_access_time(
            key=db_access_time_key,
            value=response_dict,
            last_db_access_time=last_db_access_time,
        )

        return _response
    except Exception as e:  # if user not in db
        raise ValueError(
            f"User doesn't exist in db. 'user_id'={user_id}. Create user via `/user/new` call. Got error - {e}"
        )


async def _cache_management_object(
    key: str,
    value: BaseModel,
    user_api_key_cache: DualCache,
    proxy_logging_obj: Optional[ProxyLogging],
):
    await user_api_key_cache.async_set_cache(
        key=key, value=value, ttl=DEFAULT_MANAGEMENT_OBJECT_IN_MEMORY_CACHE_TTL
    )


async def _cache_team_object(
    team_id: str,
    team_table: LiteLLM_TeamTableCachedObj,
    user_api_key_cache: DualCache,
    proxy_logging_obj: Optional[ProxyLogging],
):
    key = "team_id:{}".format(team_id)

    ## CACHE REFRESH TIME!
    team_table.last_refreshed_at = time.time()

    await _cache_management_object(
        key=key,
        value=team_table,
        user_api_key_cache=user_api_key_cache,
        proxy_logging_obj=proxy_logging_obj,
    )


async def _cache_key_object(
    hashed_token: str,
    user_api_key_obj: UserAPIKeyAuth,
    user_api_key_cache: DualCache,
    proxy_logging_obj: Optional[ProxyLogging],
):
    key = hashed_token

    ## CACHE REFRESH TIME
    user_api_key_obj.last_refreshed_at = time.time()

    await _cache_management_object(
        key=key,
        value=user_api_key_obj,
        user_api_key_cache=user_api_key_cache,
        proxy_logging_obj=proxy_logging_obj,
    )


async def _delete_cache_key_object(
    hashed_token: str,
    user_api_key_cache: DualCache,
    proxy_logging_obj: Optional[ProxyLogging],
):
    key = hashed_token

    user_api_key_cache.delete_cache(key=key)

    ## UPDATE REDIS CACHE ##
    if proxy_logging_obj is not None:
        await proxy_logging_obj.internal_usage_cache.dual_cache.async_delete_cache(
            key=key
        )


@log_db_metrics
async def _get_team_db_check(
    team_id: str, prisma_client: PrismaClient, team_id_upsert: Optional[bool] = None
):
    response = await prisma_client.db.litellm_teamtable.find_unique(
        where={"team_id": team_id}
    )

    if response is None and team_id_upsert:
        response = await prisma_client.db.litellm_teamtable.create(
            data={"team_id": team_id}
        )

    return response


async def _get_team_object_from_db(team_id: str, prisma_client: PrismaClient):
    return await prisma_client.db.litellm_teamtable.find_unique(
        where={"team_id": team_id}
    )


async def _get_team_object_from_user_api_key_cache(
    team_id: str,
    prisma_client: PrismaClient,
    user_api_key_cache: DualCache,
    last_db_access_time: LimitedSizeOrderedDict,
    db_cache_expiry: int,
    proxy_logging_obj: Optional[ProxyLogging],
    key: str,
    team_id_upsert: Optional[bool] = None,
) -> LiteLLM_TeamTableCachedObj:
    db_access_time_key = key
    should_check_db = _should_check_db(
        key=db_access_time_key,
        last_db_access_time=last_db_access_time,
        db_cache_expiry=db_cache_expiry,
    )
    if should_check_db:
        response = await _get_team_db_check(
            team_id=team_id, prisma_client=prisma_client, team_id_upsert=team_id_upsert
        )
    else:
        response = None

    if response is None:
        raise Exception

    _response = LiteLLM_TeamTableCachedObj(**response.dict())
    # save the team object to cache
    await _cache_team_object(
        team_id=team_id,
        team_table=_response,
        user_api_key_cache=user_api_key_cache,
        proxy_logging_obj=proxy_logging_obj,
    )

    # save to db access time
    _update_last_db_access_time(
        key=db_access_time_key,
        value=_response,
        last_db_access_time=last_db_access_time,
    )

    return _response


async def _get_team_object_from_cache(
    key: str,
    proxy_logging_obj: Optional[ProxyLogging],
    user_api_key_cache: DualCache,
    parent_otel_span: Optional[Span],
) -> Optional[LiteLLM_TeamTableCachedObj]:
    cached_team_obj: Optional[LiteLLM_TeamTableCachedObj] = None

    ## CHECK REDIS CACHE ##
    if (
        proxy_logging_obj is not None
        and proxy_logging_obj.internal_usage_cache.dual_cache
    ):
        cached_team_obj = (
            await proxy_logging_obj.internal_usage_cache.dual_cache.async_get_cache(
                key=key, parent_otel_span=parent_otel_span
            )
        )

    if cached_team_obj is None:
        cached_team_obj = await user_api_key_cache.async_get_cache(key=key)

    if cached_team_obj is not None:
        if isinstance(cached_team_obj, dict):
            return LiteLLM_TeamTableCachedObj(**cached_team_obj)
        elif isinstance(cached_team_obj, LiteLLM_TeamTableCachedObj):
            return cached_team_obj

    return None


async def get_team_object(
    team_id: str,
    prisma_client: Optional[PrismaClient],
    user_api_key_cache: DualCache,
    parent_otel_span: Optional[Span] = None,
    proxy_logging_obj: Optional[ProxyLogging] = None,
    check_cache_only: Optional[bool] = None,
    check_db_only: Optional[bool] = None,
    team_id_upsert: Optional[bool] = None,
) -> LiteLLM_TeamTableCachedObj:
    """
    - Check if team id in proxy Team Table
    - if valid, return LiteLLM_TeamTable object with defined limits
    - if not, then raise an error

    Raises:
        - Exception: If team doesn't exist in db or cache
    """
    if prisma_client is None:
        raise Exception(
            "No DB Connected. See - https://docs.litellm.ai/docs/proxy/virtual_keys"
        )

    # check if in cache
    key = "team_id:{}".format(team_id)

    if not check_db_only:
        cached_team_obj = await _get_team_object_from_cache(
            key=key,
            proxy_logging_obj=proxy_logging_obj,
            user_api_key_cache=user_api_key_cache,
            parent_otel_span=parent_otel_span,
        )

        if cached_team_obj is not None:
            return cached_team_obj

        if check_cache_only:
            raise Exception(
                f"Team doesn't exist in cache + check_cache_only=True. Team={team_id}."
            )

    # else, check db
    try:
        return await _get_team_object_from_user_api_key_cache(
            team_id=team_id,
            prisma_client=prisma_client,
            user_api_key_cache=user_api_key_cache,
            proxy_logging_obj=proxy_logging_obj,
            last_db_access_time=last_db_access_time,
            db_cache_expiry=db_cache_expiry,
            key=key,
            team_id_upsert=team_id_upsert,
        )
    except Exception:
        raise Exception(
            f"Team doesn't exist in db. Team={team_id}. Create team via `/team/new` call."
        )


class ExperimentalUIJWTToken:
    @staticmethod
    def get_experimental_ui_login_jwt_auth_token(user_info: LiteLLM_UserTable) -> str:
        from datetime import timedelta

        from litellm.proxy.common_utils.encrypt_decrypt_utils import (
            encrypt_value_helper,
        )

        if user_info.user_role is None:
            raise Exception("User role is required for experimental UI login")

        # Calculate expiration time (10 minutes from now)
        expiration_time = get_utc_datetime() + timedelta(minutes=10)

        # Format the expiration time as ISO 8601 string
        expires = expiration_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+00:00"

        valid_token = UserAPIKeyAuth(
            token="ui-token",
            key_name="ui-token",
            key_alias="ui-token",
            max_budget=litellm.max_ui_session_budget,
            rpm_limit=100,  # allow user to have a conversation on test key pane of UI
            expires=expires,
            user_id=user_info.user_id,
            team_id="litellm-dashboard",
            models=user_info.models,
            max_parallel_requests=None,
            user_role=LitellmUserRoles(user_info.user_role),
        )

        return encrypt_value_helper(valid_token.model_dump_json(exclude_none=True))

    @staticmethod
    def get_key_object_from_ui_hash_key(
        hashed_token: str,
    ) -> Optional[UserAPIKeyAuth]:
        import json

        from litellm.proxy.auth.user_api_key_auth import UserAPIKeyAuth
        from litellm.proxy.common_utils.encrypt_decrypt_utils import (
            decrypt_value_helper,
        )

        decrypted_token = decrypt_value_helper(hashed_token, exception_type="debug")
        if decrypted_token is None:
            return None
        try:
            return UserAPIKeyAuth(**json.loads(decrypted_token))
        except Exception as e:
            raise Exception(
                f"Invalid hash key. Hash key={hashed_token}. Decrypted token={decrypted_token}. Error: {e}"
            )


@log_db_metrics
async def get_key_object(
    hashed_token: str,
    prisma_client: Optional[PrismaClient],
    user_api_key_cache: DualCache,
    parent_otel_span: Optional[Span] = None,
    proxy_logging_obj: Optional[ProxyLogging] = None,
    check_cache_only: Optional[bool] = None,
) -> UserAPIKeyAuth:
    """
    - Check if team id in proxy Team Table
    - if valid, return LiteLLM_TeamTable object with defined limits
    - if not, then raise an error
    """
    if prisma_client is None:
        raise Exception(
            "No DB Connected. See - https://docs.litellm.ai/docs/proxy/virtual_keys"
        )

    # check if in cache
    key = hashed_token

    cached_key_obj: Optional[UserAPIKeyAuth] = await user_api_key_cache.async_get_cache(
        key=key
    )

    if cached_key_obj is not None:
        if isinstance(cached_key_obj, dict):
            return UserAPIKeyAuth(**cached_key_obj)
        elif isinstance(cached_key_obj, UserAPIKeyAuth):
            return cached_key_obj

    if check_cache_only:
        raise Exception(
            f"Key doesn't exist in cache + check_cache_only=True. key={key}."
        )

    # else, check db
    _valid_token: Optional[BaseModel] = await prisma_client.get_data(
        token=hashed_token,
        table_name="combined_view",
        parent_otel_span=parent_otel_span,
        proxy_logging_obj=proxy_logging_obj,
    )

    if _valid_token is None:
        raise ProxyException(
            message="Authentication Error, Invalid proxy server token passed. key={}, not found in db. Create key via `/key/generate` call.".format(
                hashed_token
            ),
            type=ProxyErrorTypes.token_not_found_in_db,
            param="key",
            code=status.HTTP_401_UNAUTHORIZED,
        )

    _response = UserAPIKeyAuth(**_valid_token.model_dump(exclude_none=True))

    # save the key object to cache
    await _cache_key_object(
        hashed_token=hashed_token,
        user_api_key_obj=_response,
        user_api_key_cache=user_api_key_cache,
        proxy_logging_obj=proxy_logging_obj,
    )

    return _response


@log_db_metrics
async def get_org_object(
    org_id: str,
    prisma_client: Optional[PrismaClient],
    user_api_key_cache: DualCache,
    parent_otel_span: Optional[Span] = None,
    proxy_logging_obj: Optional[ProxyLogging] = None,
) -> Optional[LiteLLM_OrganizationTable]:
    """
    - Check if org id in proxy Org Table
    - if valid, return LiteLLM_OrganizationTable object
    - if not, then raise an error
    """
    if prisma_client is None:
        raise Exception(
            "No DB Connected. See - https://docs.litellm.ai/docs/proxy/virtual_keys"
        )

    # check if in cache
    cached_org_obj = user_api_key_cache.async_get_cache(key="org_id:{}".format(org_id))
    if cached_org_obj is not None:
        if isinstance(cached_org_obj, dict):
            return LiteLLM_OrganizationTable(**cached_org_obj)
        elif isinstance(cached_org_obj, LiteLLM_OrganizationTable):
            return cached_org_obj
    # else, check db
    try:
        response = await prisma_client.db.litellm_organizationtable.find_unique(
            where={"organization_id": org_id}
        )

        if response is None:
            raise Exception

        return response
    except Exception:
        raise Exception(
            f"Organization doesn't exist in db. Organization={org_id}. Create organization via `/organization/new` call."
        )


def _can_object_call_model(
    model: Union[str, List[str]],
    llm_router: Optional[Router],
    models: List[str],
    team_model_aliases: Optional[Dict[str, str]] = None,
    object_type: Literal["user", "team", "key", "org"] = "user",
    fallback_depth: int = 0,
) -> Literal[True]:
    """
    Checks if token can call a given model

    Args:
        - model: str
        - llm_router: Optional[Router]
        - models: List[str]
        - team_model_aliases: Optional[Dict[str, str]]
        - object_type: Literal["user", "team", "key", "org"]. We use the object type to raise the correct exception type

    Returns:
        - True: if token allowed to call model

    Raises:
        - Exception: If token not allowed to call model
    """
    if fallback_depth >= DEFAULT_MAX_RECURSE_DEPTH:
        raise Exception(
            "Unable to parse model, max fallback depth exceeded - received model: {}".format(
                model
            )
        )
    if isinstance(model, list):
        for m in model:
            _can_object_call_model(
                model=m,
                llm_router=llm_router,
                models=models,
                team_model_aliases=team_model_aliases,
                object_type=object_type,
                fallback_depth=fallback_depth + 1,
            )
        return True

    if model in litellm.model_alias_map:
        model = litellm.model_alias_map[model]

    ## check if model in allowed model names
    from collections import defaultdict

    access_groups: Dict[str, List[str]] = defaultdict(list)

    if llm_router:
        access_groups = llm_router.get_model_access_groups(model_name=model)
    if (
        len(access_groups) > 0 and llm_router is not None
    ):  # check if token contains any model access groups
        for idx, m in enumerate(
            models
        ):  # loop token models, if any of them are an access group add the access group
            if m in access_groups:
                return True

    # Filter out models that are access_groups
    filtered_models = [m for m in models if m not in access_groups]

    verbose_proxy_logger.debug(f"model: {model}; allowed_models: {filtered_models}")

    if _model_in_team_aliases(model=model, team_model_aliases=team_model_aliases):
        return True

    if _model_matches_any_wildcard_pattern_in_list(
        model=model, allowed_model_list=filtered_models
    ):
        return True

    all_model_access: bool = False

    if (len(filtered_models) == 0 and len(models) == 0) or "*" in filtered_models:
        all_model_access = True

    if SpecialModelNames.all_proxy_models.value in filtered_models:
        all_model_access = True

    if model is not None and model not in filtered_models and all_model_access is False:
        raise ProxyException(
            message=f"{object_type} not allowed to access model. This {object_type} can only access models={models}. Tried to access {model}",
            type=ProxyErrorTypes.get_model_access_error_type_for_object(
                object_type=object_type
            ),
            param="model",
            code=status.HTTP_401_UNAUTHORIZED,
        )

    verbose_proxy_logger.debug(
        f"filtered allowed_models: {filtered_models}; models: {models}"
    )
    return True


def _model_in_team_aliases(
    model: str, team_model_aliases: Optional[Dict[str, str]] = None
) -> bool:
    """
    Returns True if `model` being accessed is an alias of a team model

    - `model=gpt-4o`
    - `team_model_aliases={"gpt-4o": "gpt-4o-team-1"}`
        - returns True

    - `model=gp-4o`
    - `team_model_aliases={"o-3": "o3-preview"}`
        - returns False
    """
    if team_model_aliases:
        if model in team_model_aliases:
            return True
    return False


async def can_key_call_model(
    model: Union[str, List[str]],
    llm_model_list: Optional[list],
    valid_token: UserAPIKeyAuth,
    llm_router: Optional[litellm.Router],
) -> Literal[True]:
    """
    Checks if token can call a given model

    Returns:
        - True: if token allowed to call model

    Raises:
        - Exception: If token not allowed to call model
    """
    return _can_object_call_model(
        model=model,
        llm_router=llm_router,
        models=valid_token.models,
        team_model_aliases=valid_token.team_model_aliases,
        object_type="key",
    )


def can_org_access_model(
    model: str,
    org_object: Optional[LiteLLM_OrganizationTable],
    llm_router: Optional[Router],
    team_model_aliases: Optional[Dict[str, str]] = None,
) -> Literal[True]:
    """
    Returns True if the team can access a specific model.

    """
    return _can_object_call_model(
        model=model,
        llm_router=llm_router,
        models=org_object.models if org_object else [],
        team_model_aliases=team_model_aliases,
        object_type="org",
    )


def can_team_access_model(
    model: Union[str, List[str]],
    team_object: Optional[LiteLLM_TeamTable],
    llm_router: Optional[Router],
    team_model_aliases: Optional[Dict[str, str]] = None,
) -> Literal[True]:
    """
    Returns True if the team can access a specific model.

    """
    return _can_object_call_model(
        model=model,
        llm_router=llm_router,
        models=team_object.models if team_object else [],
        team_model_aliases=team_model_aliases,
        object_type="team",
    )


async def can_user_call_model(
    model: Union[str, List[str]],
    llm_router: Optional[Router],
    user_object: Optional[LiteLLM_UserTable],
) -> Literal[True]:
    if user_object is None:
        return True

    if SpecialModelNames.no_default_models.value in user_object.models:
        raise ProxyException(
            message=f"User not allowed to access model. No default model access, only team models allowed. Tried to access {model}",
            type=ProxyErrorTypes.key_model_access_denied,
            param="model",
            code=status.HTTP_401_UNAUTHORIZED,
        )

    return _can_object_call_model(
        model=model,
        llm_router=llm_router,
        models=user_object.models,
        object_type="user",
    )


async def is_valid_fallback_model(
    model: str,
    llm_router: Optional[Router],
    user_model: Optional[str],
) -> Literal[True]:
    """
    Try to route the fallback model request.

    Validate if it can't be routed.

    Help catch invalid fallback models.
    """
    await route_request(
        data={
            "model": model,
            "messages": [{"role": "user", "content": "Who was Alexander?"}],
        },
        llm_router=llm_router,
        user_model=user_model,
        route_type="acompletion",  # route type shouldn't affect the fallback model check
    )

    return True


async def _virtual_key_max_budget_check(
    valid_token: UserAPIKeyAuth,
    proxy_logging_obj: ProxyLogging,
    user_obj: Optional[LiteLLM_UserTable] = None,
):
    """
    Raises:
        BudgetExceededError if the token is over it's max budget.
        Triggers a budget alert if the token is over it's max budget.

    """
    if valid_token.spend is not None and valid_token.max_budget is not None:
        ####################################
        # collect information for alerting #
        ####################################

        user_email = None
        # Check if the token has any user id information
        if user_obj is not None:
            user_email = user_obj.user_email

        call_info = CallInfo(
            token=valid_token.token,
            spend=valid_token.spend,
            max_budget=valid_token.max_budget,
            user_id=valid_token.user_id,
            team_id=valid_token.team_id,
            user_email=user_email,
            key_alias=valid_token.key_alias,
            event_group=Litellm_EntityType.KEY,
        )
        asyncio.create_task(
            proxy_logging_obj.budget_alerts(
                type="token_budget",
                user_info=call_info,
            )
        )

        ####################################
        # collect information for alerting #
        ####################################

        if valid_token.spend >= valid_token.max_budget:
            raise litellm.BudgetExceededError(
                current_cost=valid_token.spend,
                max_budget=valid_token.max_budget,
            )


async def _virtual_key_soft_budget_check(
    valid_token: UserAPIKeyAuth,
    proxy_logging_obj: ProxyLogging,
):
    """
    Triggers a budget alert if the token is over it's soft budget.

    """

    if valid_token.soft_budget and valid_token.spend >= valid_token.soft_budget:
        verbose_proxy_logger.debug(
            "Crossed Soft Budget for token %s, spend %s, soft_budget %s",
            valid_token.token,
            valid_token.spend,
            valid_token.soft_budget,
        )
        call_info = CallInfo(
            token=valid_token.token,
            spend=valid_token.spend,
            max_budget=valid_token.max_budget,
            soft_budget=valid_token.soft_budget,
            user_id=valid_token.user_id,
            team_id=valid_token.team_id,
            team_alias=valid_token.team_alias,
            user_email=None,
            key_alias=valid_token.key_alias,
            event_group=Litellm_EntityType.KEY,
        )
        asyncio.create_task(
            proxy_logging_obj.budget_alerts(
                type="soft_budget",
                user_info=call_info,
            )
        )


async def _team_max_budget_check(
    team_object: Optional[LiteLLM_TeamTable],
    valid_token: Optional[UserAPIKeyAuth],
    proxy_logging_obj: ProxyLogging,
):
    """
    Check if the team is over it's max budget.

    Raises:
        BudgetExceededError if the team is over it's max budget.
        Triggers a budget alert if the team is over it's max budget.
    """
    if (
        team_object is not None
        and team_object.max_budget is not None
        and team_object.spend is not None
        and team_object.spend > team_object.max_budget
    ):
        if valid_token:
            call_info = CallInfo(
                token=valid_token.token,
                spend=team_object.spend,
                max_budget=team_object.max_budget,
                user_id=valid_token.user_id,
                team_id=valid_token.team_id,
                team_alias=valid_token.team_alias,
                event_group=Litellm_EntityType.TEAM,
            )
            asyncio.create_task(
                proxy_logging_obj.budget_alerts(
                    type="team_budget",
                    user_info=call_info,
                )
            )

        raise litellm.BudgetExceededError(
            current_cost=team_object.spend,
            max_budget=team_object.max_budget,
            message=f"Budget has been exceeded! Team={team_object.team_id} Current cost: {team_object.spend}, Max budget: {team_object.max_budget}",
        )


def is_model_allowed_by_pattern(model: str, allowed_model_pattern: str) -> bool:
    """
    Check if a model matches an allowed pattern.
    Handles exact matches and wildcard patterns.

    Args:
        model (str): The model to check (e.g., "bedrock/anthropic.claude-3-5-sonnet-20240620")
        allowed_model_pattern (str): The allowed pattern (e.g., "bedrock/*", "*", "openai/*")

    Returns:
        bool: True if model matches the pattern, False otherwise
    """
    if "*" in allowed_model_pattern:
        pattern = f"^{allowed_model_pattern.replace('*', '.*')}$"
        return bool(re.match(pattern, model))

    return False


def _model_matches_any_wildcard_pattern_in_list(
    model: str, allowed_model_list: list
) -> bool:
    """
    Returns True if a model matches any wildcard pattern in a list.

    eg.
    - model=`bedrock/us.amazon.nova-micro-v1:0`, allowed_models=`bedrock/*` returns True
    - model=`bedrock/us.amazon.nova-micro-v1:0`, allowed_models=`bedrock/us.*` returns True
    - model=`bedrockzzzz/us.amazon.nova-micro-v1:0`, allowed_models=`bedrock/*` returns False
    """

    if any(
        _is_wildcard_pattern(allowed_model_pattern)
        and is_model_allowed_by_pattern(
            model=model, allowed_model_pattern=allowed_model_pattern
        )
        for allowed_model_pattern in allowed_model_list
    ):
        return True

    if any(
        _is_wildcard_pattern(allowed_model_pattern)
        and _model_custom_llm_provider_matches_wildcard_pattern(
            model=model, allowed_model_pattern=allowed_model_pattern
        )
        for allowed_model_pattern in allowed_model_list
    ):
        return True

    return False


def _model_custom_llm_provider_matches_wildcard_pattern(
    model: str, allowed_model_pattern: str
) -> bool:
    """
    Returns True for this scenario:
    - `model=gpt-4o`
    - `allowed_model_pattern=openai/*`

    or
    - `model=claude-3-5-sonnet-20240620`
    - `allowed_model_pattern=anthropic/*`
    """
    try:
        model, custom_llm_provider, _, _ = get_llm_provider(model=model)
    except Exception:
        return False

    return is_model_allowed_by_pattern(
        model=f"{custom_llm_provider}/{model}",
        allowed_model_pattern=allowed_model_pattern,
    )


def _is_wildcard_pattern(allowed_model_pattern: str) -> bool:
    """
    Returns True if the pattern is a wildcard pattern.

    Checks if `*` is in the pattern.
    """
    return "*" in allowed_model_pattern


async def vector_store_access_check(
    request_body: dict,
    team_object: Optional[LiteLLM_TeamTable],
    valid_token: Optional[UserAPIKeyAuth],
):
    """
    Checks if the object (key, team, org) has access to the vector store.

    Raises ProxyException if the object (key, team, org) cannot access the specific vector store.
    """
    from litellm.proxy.proxy_server import prisma_client

    #########################################################
    # Get the vector store the user is trying to access
    #########################################################
    if prisma_client is None:
        verbose_proxy_logger.debug(
            "Prisma client not found, skipping vector store access check"
        )
        return True

    if litellm.vector_store_registry is None:
        verbose_proxy_logger.debug(
            "Vector store registry not found, skipping vector store access check"
        )
        return True

    vector_store_ids_to_run = litellm.vector_store_registry.get_vector_store_ids_to_run(
        non_default_params=request_body, tools=request_body.get("tools", None)
    )
    if vector_store_ids_to_run is None:
        verbose_proxy_logger.debug(
            "Vector store to run not found, skipping vector store access check"
        )
        return True

    #########################################################
    # Check if the object (key, team, org) has access to the vector store
    #########################################################
    # Check if the key can access the vector store
    if valid_token is not None and valid_token.object_permission_id is not None:
        key_object_permission = (
            await prisma_client.db.litellm_objectpermissiontable.find_unique(
                where={"object_permission_id": valid_token.object_permission_id},
            )
        )
        if key_object_permission is not None:
            _can_object_call_vector_stores(
                object_type="key",
                vector_store_ids_to_run=vector_store_ids_to_run,
                object_permissions=key_object_permission,
            )

    # Check if the team can access the vector store
    if team_object is not None and team_object.object_permission_id is not None:
        team_object_permission = (
            await prisma_client.db.litellm_objectpermissiontable.find_unique(
                where={"object_permission_id": team_object.object_permission_id},
            )
        )
        if team_object_permission is not None:
            _can_object_call_vector_stores(
                object_type="team",
                vector_store_ids_to_run=vector_store_ids_to_run,
                object_permissions=team_object_permission,
            )
    return True


def _can_object_call_vector_stores(
    object_type: Literal["key", "team", "org"],
    vector_store_ids_to_run: List[str],
    object_permissions: Optional[LiteLLM_ObjectPermissionTable],
):
    """
    Raises ProxyException if the object (key, team, org) cannot access the specific vector store.
    """
    if object_permissions is None:
        return True

    if object_permissions.vector_stores is None:
        return True

    # If length is 0, then the object has access to all vector stores.
    if len(object_permissions.vector_stores) == 0:
        return True

    for vector_store_id in vector_store_ids_to_run:
        if vector_store_id not in object_permissions.vector_stores:
            raise ProxyException(
                message=f"User not allowed to access vector store. Tried to access {vector_store_id}. Only allowed to access {object_permissions.vector_stores}",
                type=ProxyErrorTypes.get_vector_store_access_error_type_for_object(
                    object_type
                ),
                param="vector_store",
                code=status.HTTP_401_UNAUTHORIZED,
            )

    return True

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\woff2.py ===
from io import BytesIO
import sys
import array
import struct
from collections import OrderedDict
from fontTools.misc import sstruct
from fontTools.misc.arrayTools import calcIntBounds
from fontTools.misc.textTools import Tag, bytechr, byteord, bytesjoin, pad
from fontTools.ttLib import (
    TTFont,
    TTLibError,
    getTableModule,
    getTableClass,
    getSearchRange,
)
from fontTools.ttLib.sfnt import (
    SFNTReader,
    SFNTWriter,
    DirectoryEntry,
    WOFFFlavorData,
    sfntDirectoryFormat,
    sfntDirectorySize,
    SFNTDirectoryEntry,
    sfntDirectoryEntrySize,
    calcChecksum,
)
from fontTools.ttLib.tables import ttProgram, _g_l_y_f
import logging


log = logging.getLogger("fontTools.ttLib.woff2")

haveBrotli = False
try:
    try:
        import brotlicffi as brotli
    except ImportError:
        import brotli
    haveBrotli = True
except ImportError:
    pass


class WOFF2Reader(SFNTReader):
    flavor = "woff2"

    def __init__(self, file, checkChecksums=0, fontNumber=-1):
        if not haveBrotli:
            log.error(
                "The WOFF2 decoder requires the Brotli Python extension, available at: "
                "https://github.com/google/brotli"
            )
            raise ImportError("No module named brotli")

        self.file = file

        signature = Tag(self.file.read(4))
        if signature != b"wOF2":
            raise TTLibError("Not a WOFF2 font (bad signature)")

        self.file.seek(0)
        self.DirectoryEntry = WOFF2DirectoryEntry
        data = self.file.read(woff2DirectorySize)
        if len(data) != woff2DirectorySize:
            raise TTLibError("Not a WOFF2 font (not enough data)")
        sstruct.unpack(woff2DirectoryFormat, data, self)

        self.tables = OrderedDict()
        offset = 0
        for i in range(self.numTables):
            entry = self.DirectoryEntry()
            entry.fromFile(self.file)
            tag = Tag(entry.tag)
            self.tables[tag] = entry
            entry.offset = offset
            offset += entry.length

        totalUncompressedSize = offset
        compressedData = self.file.read(self.totalCompressedSize)
        decompressedData = brotli.decompress(compressedData)
        if len(decompressedData) != totalUncompressedSize:
            raise TTLibError(
                "unexpected size for decompressed font data: expected %d, found %d"
                % (totalUncompressedSize, len(decompressedData))
            )
        self.transformBuffer = BytesIO(decompressedData)

        self.file.seek(0, 2)
        if self.length != self.file.tell():
            raise TTLibError("reported 'length' doesn't match the actual file size")

        self.flavorData = WOFF2FlavorData(self)

        # make empty TTFont to store data while reconstructing tables
        self.ttFont = TTFont(recalcBBoxes=False, recalcTimestamp=False)

    def __getitem__(self, tag):
        """Fetch the raw table data. Reconstruct transformed tables."""
        entry = self.tables[Tag(tag)]
        if not hasattr(entry, "data"):
            if entry.transformed:
                entry.data = self.reconstructTable(tag)
            else:
                entry.data = entry.loadData(self.transformBuffer)
        return entry.data

    def reconstructTable(self, tag):
        """Reconstruct table named 'tag' from transformed data."""
        entry = self.tables[Tag(tag)]
        rawData = entry.loadData(self.transformBuffer)
        if tag == "glyf":
            # no need to pad glyph data when reconstructing
            padding = self.padding if hasattr(self, "padding") else None
            data = self._reconstructGlyf(rawData, padding)
        elif tag == "loca":
            data = self._reconstructLoca()
        elif tag == "hmtx":
            data = self._reconstructHmtx(rawData)
        else:
            raise TTLibError("transform for table '%s' is unknown" % tag)
        return data

    def _reconstructGlyf(self, data, padding=None):
        """Return recostructed glyf table data, and set the corresponding loca's
        locations. Optionally pad glyph offsets to the specified number of bytes.
        """
        self.ttFont["loca"] = WOFF2LocaTable()
        glyfTable = self.ttFont["glyf"] = WOFF2GlyfTable()
        glyfTable.reconstruct(data, self.ttFont)
        if padding:
            glyfTable.padding = padding
        data = glyfTable.compile(self.ttFont)
        return data

    def _reconstructLoca(self):
        """Return reconstructed loca table data."""
        if "loca" not in self.ttFont:
            # make sure glyf is reconstructed first
            self.tables["glyf"].data = self.reconstructTable("glyf")
        locaTable = self.ttFont["loca"]
        data = locaTable.compile(self.ttFont)
        if len(data) != self.tables["loca"].origLength:
            raise TTLibError(
                "reconstructed 'loca' table doesn't match original size: "
                "expected %d, found %d" % (self.tables["loca"].origLength, len(data))
            )
        return data

    def _reconstructHmtx(self, data):
        """Return reconstructed hmtx table data."""
        # Before reconstructing 'hmtx' table we need to parse other tables:
        # 'glyf' is required for reconstructing the sidebearings from the glyphs'
        # bounding box; 'hhea' is needed for the numberOfHMetrics field.
        if "glyf" in self.flavorData.transformedTables:
            # transformed 'glyf' table is self-contained, thus 'loca' not needed
            tableDependencies = ("maxp", "hhea", "glyf")
        else:
            # decompiling untransformed 'glyf' requires 'loca', which requires 'head'
            tableDependencies = ("maxp", "head", "hhea", "loca", "glyf")
        for tag in tableDependencies:
            self._decompileTable(tag)
        hmtxTable = self.ttFont["hmtx"] = WOFF2HmtxTable()
        hmtxTable.reconstruct(data, self.ttFont)
        data = hmtxTable.compile(self.ttFont)
        return data

    def _decompileTable(self, tag):
        """Decompile table data and store it inside self.ttFont."""
        data = self[tag]
        if self.ttFont.isLoaded(tag):
            return self.ttFont[tag]
        tableClass = getTableClass(tag)
        table = tableClass(tag)
        self.ttFont.tables[tag] = table
        table.decompile(data, self.ttFont)


class WOFF2Writer(SFNTWriter):
    flavor = "woff2"

    def __init__(
        self,
        file,
        numTables,
        sfntVersion="\000\001\000\000",
        flavor=None,
        flavorData=None,
    ):
        if not haveBrotli:
            log.error(
                "The WOFF2 encoder requires the Brotli Python extension, available at: "
                "https://github.com/google/brotli"
            )
            raise ImportError("No module named brotli")

        self.file = file
        self.numTables = numTables
        self.sfntVersion = Tag(sfntVersion)
        self.flavorData = WOFF2FlavorData(data=flavorData)

        self.directoryFormat = woff2DirectoryFormat
        self.directorySize = woff2DirectorySize
        self.DirectoryEntry = WOFF2DirectoryEntry

        self.signature = Tag("wOF2")

        self.nextTableOffset = 0
        self.transformBuffer = BytesIO()

        self.tables = OrderedDict()

        # make empty TTFont to store data while normalising and transforming tables
        self.ttFont = TTFont(recalcBBoxes=False, recalcTimestamp=False)

    def __setitem__(self, tag, data):
        """Associate new entry named 'tag' with raw table data."""
        if tag in self.tables:
            raise TTLibError("cannot rewrite '%s' table" % tag)
        if tag == "DSIG":
            # always drop DSIG table, since the encoding process can invalidate it
            self.numTables -= 1
            return

        entry = self.DirectoryEntry()
        entry.tag = Tag(tag)
        entry.flags = getKnownTagIndex(entry.tag)
        # WOFF2 table data are written to disk only on close(), after all tags
        # have been specified
        entry.data = data

        self.tables[tag] = entry

    def close(self):
        """All tags must have been specified. Now write the table data and directory."""
        if len(self.tables) != self.numTables:
            raise TTLibError(
                "wrong number of tables; expected %d, found %d"
                % (self.numTables, len(self.tables))
            )

        if self.sfntVersion in ("\x00\x01\x00\x00", "true"):
            isTrueType = True
        elif self.sfntVersion == "OTTO":
            isTrueType = False
        else:
            raise TTLibError("Not a TrueType or OpenType font (bad sfntVersion)")

        # The WOFF2 spec no longer requires the glyph offsets to be 4-byte aligned.
        # However, the reference WOFF2 implementation still fails to reconstruct
        # 'unpadded' glyf tables, therefore we need to 'normalise' them.
        # See:
        # https://github.com/khaledhosny/ots/issues/60
        # https://github.com/google/woff2/issues/15
        if (
            isTrueType
            and "glyf" in self.flavorData.transformedTables
            and "glyf" in self.tables
        ):
            self._normaliseGlyfAndLoca(padding=4)
        self._setHeadTransformFlag()

        # To pass the legacy OpenType Sanitiser currently included in browsers,
        # we must sort the table directory and data alphabetically by tag.
        # See:
        # https://github.com/google/woff2/pull/3
        # https://lists.w3.org/Archives/Public/public-webfonts-wg/2015Mar/0000.html
        #
        # 2023: We rely on this in _transformTables where we expect that
        # "loca" comes after "glyf" table.
        self.tables = OrderedDict(sorted(self.tables.items()))

        self.totalSfntSize = self._calcSFNTChecksumsLengthsAndOffsets()

        fontData = self._transformTables()
        compressedFont = brotli.compress(fontData, mode=brotli.MODE_FONT)

        self.totalCompressedSize = len(compressedFont)
        self.length = self._calcTotalSize()
        self.majorVersion, self.minorVersion = self._getVersion()
        self.reserved = 0

        directory = self._packTableDirectory()
        self.file.seek(0)
        self.file.write(pad(directory + compressedFont, size=4))
        self._writeFlavorData()

    def _normaliseGlyfAndLoca(self, padding=4):
        """Recompile glyf and loca tables, aligning glyph offsets to multiples of
        'padding' size. Update the head table's 'indexToLocFormat' accordingly while
        compiling loca.
        """
        if self.sfntVersion == "OTTO":
            return

        for tag in ("maxp", "head", "loca", "glyf", "fvar"):
            if tag in self.tables:
                self._decompileTable(tag)
        self.ttFont["glyf"].padding = padding
        for tag in ("glyf", "loca"):
            self._compileTable(tag)

    def _setHeadTransformFlag(self):
        """Set bit 11 of 'head' table flags to indicate that the font has undergone
        a lossless modifying transform. Re-compile head table data."""
        self._decompileTable("head")
        self.ttFont["head"].flags |= 1 << 11
        self._compileTable("head")

    def _decompileTable(self, tag):
        """Fetch table data, decompile it, and store it inside self.ttFont."""
        tag = Tag(tag)
        if tag not in self.tables:
            raise TTLibError("missing required table: %s" % tag)
        if self.ttFont.isLoaded(tag):
            return
        data = self.tables[tag].data
        if tag == "loca":
            tableClass = WOFF2LocaTable
        elif tag == "glyf":
            tableClass = WOFF2GlyfTable
        elif tag == "hmtx":
            tableClass = WOFF2HmtxTable
        else:
            tableClass = getTableClass(tag)
        table = tableClass(tag)
        self.ttFont.tables[tag] = table
        table.decompile(data, self.ttFont)

    def _compileTable(self, tag):
        """Compile table and store it in its 'data' attribute."""
        self.tables[tag].data = self.ttFont[tag].compile(self.ttFont)

    def _calcSFNTChecksumsLengthsAndOffsets(self):
        """Compute the 'original' SFNT checksums, lengths and offsets for checksum
        adjustment calculation. Return the total size of the uncompressed font.
        """
        offset = sfntDirectorySize + sfntDirectoryEntrySize * len(self.tables)
        for tag, entry in self.tables.items():
            data = entry.data
            entry.origOffset = offset
            entry.origLength = len(data)
            if tag == "head":
                entry.checkSum = calcChecksum(data[:8] + b"\0\0\0\0" + data[12:])
            else:
                entry.checkSum = calcChecksum(data)
            offset += (entry.origLength + 3) & ~3
        return offset

    def _transformTables(self):
        """Return transformed font data."""
        transformedTables = self.flavorData.transformedTables
        for tag, entry in self.tables.items():
            data = None
            if tag in transformedTables:
                data = self.transformTable(tag)
                if data is not None:
                    entry.transformed = True
            if data is None:
                if tag == "glyf":
                    # Currently we always sort table tags so
                    # 'loca' comes after 'glyf'.
                    transformedTables.discard("loca")
                # pass-through the table data without transformation
                data = entry.data
                entry.transformed = False
            entry.offset = self.nextTableOffset
            entry.saveData(self.transformBuffer, data)
            self.nextTableOffset += entry.length
        self.writeMasterChecksum()
        fontData = self.transformBuffer.getvalue()
        return fontData

    def transformTable(self, tag):
        """Return transformed table data, or None if some pre-conditions aren't
        met -- in which case, the non-transformed table data will be used.
        """
        if tag == "loca":
            data = b""
        elif tag == "glyf":
            for tag in ("maxp", "head", "loca", "glyf"):
                self._decompileTable(tag)
            glyfTable = self.ttFont["glyf"]
            data = glyfTable.transform(self.ttFont)
        elif tag == "hmtx":
            if "glyf" not in self.tables:
                return
            for tag in ("maxp", "head", "hhea", "loca", "glyf", "hmtx"):
                self._decompileTable(tag)
            hmtxTable = self.ttFont["hmtx"]
            data = hmtxTable.transform(self.ttFont)  # can be None
        else:
            raise TTLibError("Transform for table '%s' is unknown" % tag)
        return data

    def _calcMasterChecksum(self):
        """Calculate checkSumAdjustment."""
        tags = list(self.tables.keys())
        checksums = []
        for i in range(len(tags)):
            checksums.append(self.tables[tags[i]].checkSum)

        # Create a SFNT directory for checksum calculation purposes
        self.searchRange, self.entrySelector, self.rangeShift = getSearchRange(
            self.numTables, 16
        )
        directory = sstruct.pack(sfntDirectoryFormat, self)
        tables = sorted(self.tables.items())
        for tag, entry in tables:
            sfntEntry = SFNTDirectoryEntry()
            sfntEntry.tag = entry.tag
            sfntEntry.checkSum = entry.checkSum
            sfntEntry.offset = entry.origOffset
            sfntEntry.length = entry.origLength
            directory = directory + sfntEntry.toString()

        directory_end = sfntDirectorySize + len(self.tables) * sfntDirectoryEntrySize
        assert directory_end == len(directory)

        checksums.append(calcChecksum(directory))
        checksum = sum(checksums) & 0xFFFFFFFF
        # BiboAfba!
        checksumadjustment = (0xB1B0AFBA - checksum) & 0xFFFFFFFF
        return checksumadjustment

    def writeMasterChecksum(self):
        """Write checkSumAdjustment to the transformBuffer."""
        checksumadjustment = self._calcMasterChecksum()
        self.transformBuffer.seek(self.tables["head"].offset + 8)
        self.transformBuffer.write(struct.pack(">L", checksumadjustment))

    def _calcTotalSize(self):
        """Calculate total size of WOFF2 font, including any meta- and/or private data."""
        offset = self.directorySize
        for entry in self.tables.values():
            offset += len(entry.toString())
        offset += self.totalCompressedSize
        offset = (offset + 3) & ~3
        offset = self._calcFlavorDataOffsetsAndSize(offset)
        return offset

    def _calcFlavorDataOffsetsAndSize(self, start):
        """Calculate offsets and lengths for any meta- and/or private data."""
        offset = start
        data = self.flavorData
        if data.metaData:
            self.metaOrigLength = len(data.metaData)
            self.metaOffset = offset
            self.compressedMetaData = brotli.compress(
                data.metaData, mode=brotli.MODE_TEXT
            )
            self.metaLength = len(self.compressedMetaData)
            offset += self.metaLength
        else:
            self.metaOffset = self.metaLength = self.metaOrigLength = 0
            self.compressedMetaData = b""
        if data.privData:
            # make sure private data is padded to 4-byte boundary
            offset = (offset + 3) & ~3
            self.privOffset = offset
            self.privLength = len(data.privData)
            offset += self.privLength
        else:
            self.privOffset = self.privLength = 0
        return offset

    def _getVersion(self):
        """Return the WOFF2 font's (majorVersion, minorVersion) tuple."""
        data = self.flavorData
        if data.majorVersion is not None and data.minorVersion is not None:
            return data.majorVersion, data.minorVersion
        else:
            # if None, return 'fontRevision' from 'head' table
            if "head" in self.tables:
                return struct.unpack(">HH", self.tables["head"].data[4:8])
            else:
                return 0, 0

    def _packTableDirectory(self):
        """Return WOFF2 table directory data."""
        directory = sstruct.pack(self.directoryFormat, self)
        for entry in self.tables.values():
            directory = directory + entry.toString()
        return directory

    def _writeFlavorData(self):
        """Write metadata and/or private data using appropiate padding."""
        compressedMetaData = self.compressedMetaData
        privData = self.flavorData.privData
        if compressedMetaData and privData:
            compressedMetaData = pad(compressedMetaData, size=4)
        if compressedMetaData:
            self.file.seek(self.metaOffset)
            assert self.file.tell() == self.metaOffset
            self.file.write(compressedMetaData)
        if privData:
            self.file.seek(self.privOffset)
            assert self.file.tell() == self.privOffset
            self.file.write(privData)

    def reordersTables(self):
        return True


# -- woff2 directory helpers and cruft

woff2DirectoryFormat = """
		> # big endian
		signature:           4s   # "wOF2"
		sfntVersion:         4s
		length:              L    # total woff2 file size
		numTables:           H    # number of tables
		reserved:            H    # set to 0
		totalSfntSize:       L    # uncompressed size
		totalCompressedSize: L    # compressed size
		majorVersion:        H    # major version of WOFF file
		minorVersion:        H    # minor version of WOFF file
		metaOffset:          L    # offset to metadata block
		metaLength:          L    # length of compressed metadata
		metaOrigLength:      L    # length of uncompressed metadata
		privOffset:          L    # offset to private data block
		privLength:          L    # length of private data block
"""

woff2DirectorySize = sstruct.calcsize(woff2DirectoryFormat)

woff2KnownTags = (
    "cmap",
    "head",
    "hhea",
    "hmtx",
    "maxp",
    "name",
    "OS/2",
    "post",
    "cvt ",
    "fpgm",
    "glyf",
    "loca",
    "prep",
    "CFF ",
    "VORG",
    "EBDT",
    "EBLC",
    "gasp",
    "hdmx",
    "kern",
    "LTSH",
    "PCLT",
    "VDMX",
    "vhea",
    "vmtx",
    "BASE",
    "GDEF",
    "GPOS",
    "GSUB",
    "EBSC",
    "JSTF",
    "MATH",
    "CBDT",
    "CBLC",
    "COLR",
    "CPAL",
    "SVG ",
    "sbix",
    "acnt",
    "avar",
    "bdat",
    "bloc",
    "bsln",
    "cvar",
    "fdsc",
    "feat",
    "fmtx",
    "fvar",
    "gvar",
    "hsty",
    "just",
    "lcar",
    "mort",
    "morx",
    "opbd",
    "prop",
    "trak",
    "Zapf",
    "Silf",
    "Glat",
    "Gloc",
    "Feat",
    "Sill",
)

woff2FlagsFormat = """
		> # big endian
		flags: B  # table type and flags
"""

woff2FlagsSize = sstruct.calcsize(woff2FlagsFormat)

woff2UnknownTagFormat = """
		> # big endian
		tag: 4s  # 4-byte tag (optional)
"""

woff2UnknownTagSize = sstruct.calcsize(woff2UnknownTagFormat)

woff2UnknownTagIndex = 0x3F

woff2Base128MaxSize = 5
woff2DirectoryEntryMaxSize = (
    woff2FlagsSize + woff2UnknownTagSize + 2 * woff2Base128MaxSize
)

woff2TransformedTableTags = ("glyf", "loca")

woff2GlyfTableFormat = """
		> # big endian
		version:                  H  # = 0x0000
		optionFlags:              H  # Bit 0: we have overlapSimpleBitmap[], Bits 1-15: reserved
		numGlyphs:                H  # Number of glyphs
		indexFormat:              H  # Offset format for loca table
		nContourStreamSize:       L  # Size of nContour stream
		nPointsStreamSize:        L  # Size of nPoints stream
		flagStreamSize:           L  # Size of flag stream
		glyphStreamSize:          L  # Size of glyph stream
		compositeStreamSize:      L  # Size of composite stream
		bboxStreamSize:           L  # Comnined size of bboxBitmap and bboxStream
		instructionStreamSize:    L  # Size of instruction stream
"""

woff2GlyfTableFormatSize = sstruct.calcsize(woff2GlyfTableFormat)

bboxFormat = """
		>	# big endian
		xMin:				h
		yMin:				h
		xMax:				h
		yMax:				h
"""

woff2OverlapSimpleBitmapFlag = 0x0001


def getKnownTagIndex(tag):
    """Return index of 'tag' in woff2KnownTags list. Return 63 if not found."""
    for i in range(len(woff2KnownTags)):
        if tag == woff2KnownTags[i]:
            return i
    return woff2UnknownTagIndex


class WOFF2DirectoryEntry(DirectoryEntry):
    def fromFile(self, file):
        pos = file.tell()
        data = file.read(woff2DirectoryEntryMaxSize)
        left = self.fromString(data)
        consumed = len(data) - len(left)
        file.seek(pos + consumed)

    def fromString(self, data):
        if len(data) < 1:
            raise TTLibError("can't read table 'flags': not enough data")
        dummy, data = sstruct.unpack2(woff2FlagsFormat, data, self)
        if self.flags & 0x3F == 0x3F:
            # if bits [0..5] of the flags byte == 63, read a 4-byte arbitrary tag value
            if len(data) < woff2UnknownTagSize:
                raise TTLibError("can't read table 'tag': not enough data")
            dummy, data = sstruct.unpack2(woff2UnknownTagFormat, data, self)
        else:
            # otherwise, tag is derived from a fixed 'Known Tags' table
            self.tag = woff2KnownTags[self.flags & 0x3F]
        self.tag = Tag(self.tag)
        self.origLength, data = unpackBase128(data)
        self.length = self.origLength
        if self.transformed:
            self.length, data = unpackBase128(data)
            if self.tag == "loca" and self.length != 0:
                raise TTLibError("the transformLength of the 'loca' table must be 0")
        # return left over data
        return data

    def toString(self):
        data = bytechr(self.flags)
        if (self.flags & 0x3F) == 0x3F:
            data += struct.pack(">4s", self.tag.tobytes())
        data += packBase128(self.origLength)
        if self.transformed:
            data += packBase128(self.length)
        return data

    @property
    def transformVersion(self):
        """Return bits 6-7 of table entry's flags, which indicate the preprocessing
        transformation version number (between 0 and 3).
        """
        return self.flags >> 6

    @transformVersion.setter
    def transformVersion(self, value):
        assert 0 <= value <= 3
        self.flags |= value << 6

    @property
    def transformed(self):
        """Return True if the table has any transformation, else return False."""
        # For all tables in a font, except for 'glyf' and 'loca', the transformation
        # version 0 indicates the null transform (where the original table data is
        # passed directly to the Brotli compressor). For 'glyf' and 'loca' tables,
        # transformation version 3 indicates the null transform
        if self.tag in {"glyf", "loca"}:
            return self.transformVersion != 3
        else:
            return self.transformVersion != 0

    @transformed.setter
    def transformed(self, booleanValue):
        # here we assume that a non-null transform means version 0 for 'glyf' and
        # 'loca' and 1 for every other table (e.g. hmtx); but that may change as
        # new transformation formats are introduced in the future (if ever).
        if self.tag in {"glyf", "loca"}:
            self.transformVersion = 3 if not booleanValue else 0
        else:
            self.transformVersion = int(booleanValue)


class WOFF2LocaTable(getTableClass("loca")):
    """Same as parent class. The only difference is that it attempts to preserve
    the 'indexFormat' as encoded in the WOFF2 glyf table.
    """

    def __init__(self, tag=None):
        self.tableTag = Tag(tag or "loca")

    def compile(self, ttFont):
        try:
            max_location = max(self.locations)
        except AttributeError:
            self.set([])
            max_location = 0
        if "glyf" in ttFont and hasattr(ttFont["glyf"], "indexFormat"):
            # copile loca using the indexFormat specified in the WOFF2 glyf table
            indexFormat = ttFont["glyf"].indexFormat
            if indexFormat == 0:
                if max_location >= 0x20000:
                    raise TTLibError("indexFormat is 0 but local offsets > 0x20000")
                if not all(l % 2 == 0 for l in self.locations):
                    raise TTLibError(
                        "indexFormat is 0 but local offsets not multiples of 2"
                    )
                locations = array.array("H")
                for i in range(len(self.locations)):
                    locations.append(self.locations[i] // 2)
            else:
                locations = array.array("I", self.locations)
            if sys.byteorder != "big":
                locations.byteswap()
            data = locations.tobytes()
        else:
            # use the most compact indexFormat given the current glyph offsets
            data = super(WOFF2LocaTable, self).compile(ttFont)
        return data


class WOFF2GlyfTable(getTableClass("glyf")):
    """Decoder/Encoder for WOFF2 'glyf' table transform."""

    subStreams = (
        "nContourStream",
        "nPointsStream",
        "flagStream",
        "glyphStream",
        "compositeStream",
        "bboxStream",
        "instructionStream",
    )

    def __init__(self, tag=None):
        self.tableTag = Tag(tag or "glyf")

    def reconstruct(self, data, ttFont):
        """Decompile transformed 'glyf' data."""
        inputDataSize = len(data)

        if inputDataSize < woff2GlyfTableFormatSize:
            raise TTLibError("not enough 'glyf' data")
        dummy, data = sstruct.unpack2(woff2GlyfTableFormat, data, self)
        offset = woff2GlyfTableFormatSize

        for stream in self.subStreams:
            size = getattr(self, stream + "Size")
            setattr(self, stream, data[:size])
            data = data[size:]
            offset += size

        hasOverlapSimpleBitmap = self.optionFlags & woff2OverlapSimpleBitmapFlag
        self.overlapSimpleBitmap = None
        if hasOverlapSimpleBitmap:
            overlapSimpleBitmapSize = (self.numGlyphs + 7) >> 3
            self.overlapSimpleBitmap = array.array("B", data[:overlapSimpleBitmapSize])
            offset += overlapSimpleBitmapSize

        if offset != inputDataSize:
            raise TTLibError(
                "incorrect size of transformed 'glyf' table: expected %d, received %d bytes"
                % (offset, inputDataSize)
            )

        bboxBitmapSize = ((self.numGlyphs + 31) >> 5) << 2
        bboxBitmap = self.bboxStream[:bboxBitmapSize]
        self.bboxBitmap = array.array("B", bboxBitmap)
        self.bboxStream = self.bboxStream[bboxBitmapSize:]

        self.nContourStream = array.array("h", self.nContourStream)
        if sys.byteorder != "big":
            self.nContourStream.byteswap()
        assert len(self.nContourStream) == self.numGlyphs

        if "head" in ttFont:
            ttFont["head"].indexToLocFormat = self.indexFormat
        try:
            self.glyphOrder = ttFont.getGlyphOrder()
        except:
            self.glyphOrder = None
        if self.glyphOrder is None:
            self.glyphOrder = [".notdef"]
            self.glyphOrder.extend(["glyph%.5d" % i for i in range(1, self.numGlyphs)])
        else:
            if len(self.glyphOrder) != self.numGlyphs:
                raise TTLibError(
                    "incorrect glyphOrder: expected %d glyphs, found %d"
                    % (len(self.glyphOrder), self.numGlyphs)
                )

        glyphs = self.glyphs = {}
        for glyphID, glyphName in enumerate(self.glyphOrder):
            glyph = self._decodeGlyph(glyphID)
            glyphs[glyphName] = glyph

    def transform(self, ttFont):
        """Return transformed 'glyf' data"""
        self.numGlyphs = len(self.glyphs)
        assert len(self.glyphOrder) == self.numGlyphs
        if "maxp" in ttFont:
            ttFont["maxp"].numGlyphs = self.numGlyphs
        self.indexFormat = ttFont["head"].indexToLocFormat

        for stream in self.subStreams:
            setattr(self, stream, b"")
        bboxBitmapSize = ((self.numGlyphs + 31) >> 5) << 2
        self.bboxBitmap = array.array("B", [0] * bboxBitmapSize)

        self.overlapSimpleBitmap = array.array("B", [0] * ((self.numGlyphs + 7) >> 3))
        for glyphID in range(self.numGlyphs):
            try:
                self._encodeGlyph(glyphID)
            except NotImplementedError:
                return None
        hasOverlapSimpleBitmap = any(self.overlapSimpleBitmap)

        self.bboxStream = self.bboxBitmap.tobytes() + self.bboxStream
        for stream in self.subStreams:
            setattr(self, stream + "Size", len(getattr(self, stream)))
        self.version = 0
        self.optionFlags = 0
        if hasOverlapSimpleBitmap:
            self.optionFlags |= woff2OverlapSimpleBitmapFlag
        data = sstruct.pack(woff2GlyfTableFormat, self)
        data += bytesjoin([getattr(self, s) for s in self.subStreams])
        if hasOverlapSimpleBitmap:
            data += self.overlapSimpleBitmap.tobytes()
        return data

    def _decodeGlyph(self, glyphID):
        glyph = getTableModule("glyf").Glyph()
        glyph.numberOfContours = self.nContourStream[glyphID]
        if glyph.numberOfContours == 0:
            return glyph
        elif glyph.isComposite():
            self._decodeComponents(glyph)
        else:
            self._decodeCoordinates(glyph)
            self._decodeOverlapSimpleFlag(glyph, glyphID)
        self._decodeBBox(glyphID, glyph)
        return glyph

    def _decodeComponents(self, glyph):
        data = self.compositeStream
        glyph.components = []
        more = 1
        haveInstructions = 0
        while more:
            component = getTableModule("glyf").GlyphComponent()
            more, haveInstr, data = component.decompile(data, self)
            haveInstructions = haveInstructions | haveInstr
            glyph.components.append(component)
        self.compositeStream = data
        if haveInstructions:
            self._decodeInstructions(glyph)

    def _decodeCoordinates(self, glyph):
        data = self.nPointsStream
        endPtsOfContours = []
        endPoint = -1
        for i in range(glyph.numberOfContours):
            ptsOfContour, data = unpack255UShort(data)
            endPoint += ptsOfContour
            endPtsOfContours.append(endPoint)
        glyph.endPtsOfContours = endPtsOfContours
        self.nPointsStream = data
        self._decodeTriplets(glyph)
        self._decodeInstructions(glyph)

    def _decodeOverlapSimpleFlag(self, glyph, glyphID):
        if self.overlapSimpleBitmap is None or glyph.numberOfContours <= 0:
            return
        byte = glyphID >> 3
        bit = glyphID & 7
        if self.overlapSimpleBitmap[byte] & (0x80 >> bit):
            glyph.flags[0] |= _g_l_y_f.flagOverlapSimple

    def _decodeInstructions(self, glyph):
        glyphStream = self.glyphStream
        instructionStream = self.instructionStream
        instructionLength, glyphStream = unpack255UShort(glyphStream)
        glyph.program = ttProgram.Program()
        glyph.program.fromBytecode(instructionStream[:instructionLength])
        self.glyphStream = glyphStream
        self.instructionStream = instructionStream[instructionLength:]

    def _decodeBBox(self, glyphID, glyph):
        haveBBox = bool(self.bboxBitmap[glyphID >> 3] & (0x80 >> (glyphID & 7)))
        if glyph.isComposite() and not haveBBox:
            raise TTLibError("no bbox values for composite glyph %d" % glyphID)
        if haveBBox:
            dummy, self.bboxStream = sstruct.unpack2(bboxFormat, self.bboxStream, glyph)
        else:
            glyph.recalcBounds(self)

    def _decodeTriplets(self, glyph):
        def withSign(flag, baseval):
            assert 0 <= baseval and baseval < 65536, "integer overflow"
            return baseval if flag & 1 else -baseval

        nPoints = glyph.endPtsOfContours[-1] + 1
        flagSize = nPoints
        if flagSize > len(self.flagStream):
            raise TTLibError("not enough 'flagStream' data")
        flagsData = self.flagStream[:flagSize]
        self.flagStream = self.flagStream[flagSize:]
        flags = array.array("B", flagsData)

        triplets = array.array("B", self.glyphStream)
        nTriplets = len(triplets)
        assert nPoints <= nTriplets

        x = 0
        y = 0
        glyph.coordinates = getTableModule("glyf").GlyphCoordinates.zeros(nPoints)
        glyph.flags = array.array("B")
        tripletIndex = 0
        for i in range(nPoints):
            flag = flags[i]
            onCurve = not bool(flag >> 7)
            flag &= 0x7F
            if flag < 84:
                nBytes = 1
            elif flag < 120:
                nBytes = 2
            elif flag < 124:
                nBytes = 3
            else:
                nBytes = 4
            assert (tripletIndex + nBytes) <= nTriplets
            if flag < 10:
                dx = 0
                dy = withSign(flag, ((flag & 14) << 7) + triplets[tripletIndex])
            elif flag < 20:
                dx = withSign(flag, (((flag - 10) & 14) << 7) + triplets[tripletIndex])
                dy = 0
            elif flag < 84:
                b0 = flag - 20
                b1 = triplets[tripletIndex]
                dx = withSign(flag, 1 + (b0 & 0x30) + (b1 >> 4))
                dy = withSign(flag >> 1, 1 + ((b0 & 0x0C) << 2) + (b1 & 0x0F))
            elif flag < 120:
                b0 = flag - 84
                dx = withSign(flag, 1 + ((b0 // 12) << 8) + triplets[tripletIndex])
                dy = withSign(
                    flag >> 1, 1 + (((b0 % 12) >> 2) << 8) + triplets[tripletIndex + 1]
                )
            elif flag < 124:
                b2 = triplets[tripletIndex + 1]
                dx = withSign(flag, (triplets[tripletIndex] << 4) + (b2 >> 4))
                dy = withSign(
                    flag >> 1, ((b2 & 0x0F) << 8) + triplets[tripletIndex + 2]
                )
            else:
                dx = withSign(
                    flag, (triplets[tripletIndex] << 8) + triplets[tripletIndex + 1]
                )
                dy = withSign(
                    flag >> 1,
                    (triplets[tripletIndex + 2] << 8) + triplets[tripletIndex + 3],
                )
            tripletIndex += nBytes
            x += dx
            y += dy
            glyph.coordinates[i] = (x, y)
            glyph.flags.append(int(onCurve))
        bytesConsumed = tripletIndex
        self.glyphStream = self.glyphStream[bytesConsumed:]

    def _encodeGlyph(self, glyphID):
        glyphName = self.getGlyphName(glyphID)
        glyph = self[glyphName]
        self.nContourStream += struct.pack(">h", glyph.numberOfContours)
        if glyph.numberOfContours == 0:
            return
        elif glyph.isComposite():
            self._encodeComponents(glyph)
        else:
            self._encodeCoordinates(glyph)
            self._encodeOverlapSimpleFlag(glyph, glyphID)
        self._encodeBBox(glyphID, glyph)

    def _encodeComponents(self, glyph):
        lastcomponent = len(glyph.components) - 1
        more = 1
        haveInstructions = 0
        for i in range(len(glyph.components)):
            if i == lastcomponent:
                haveInstructions = hasattr(glyph, "program")
                more = 0
            component = glyph.components[i]
            self.compositeStream += component.compile(more, haveInstructions, self)
        if haveInstructions:
            self._encodeInstructions(glyph)

    def _encodeCoordinates(self, glyph):
        lastEndPoint = -1
        if _g_l_y_f.flagCubic in glyph.flags:
            raise NotImplementedError
        for endPoint in glyph.endPtsOfContours:
            ptsOfContour = endPoint - lastEndPoint
            self.nPointsStream += pack255UShort(ptsOfContour)
            lastEndPoint = endPoint
        self._encodeTriplets(glyph)
        self._encodeInstructions(glyph)

    def _encodeOverlapSimpleFlag(self, glyph, glyphID):
        if glyph.numberOfContours <= 0:
            return
        if glyph.flags[0] & _g_l_y_f.flagOverlapSimple:
            byte = glyphID >> 3
            bit = glyphID & 7
            self.overlapSimpleBitmap[byte] |= 0x80 >> bit

    def _encodeInstructions(self, glyph):
        instructions = glyph.program.getBytecode()
        self.glyphStream += pack255UShort(len(instructions))
        self.instructionStream += instructions

    def _encodeBBox(self, glyphID, glyph):
        assert glyph.numberOfContours != 0, "empty glyph has no bbox"
        if not glyph.isComposite():
            # for simple glyphs, compare the encoded bounding box info with the calculated
            # values, and if they match omit the bounding box info
            currentBBox = glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax
            calculatedBBox = calcIntBounds(glyph.coordinates)
            if currentBBox == calculatedBBox:
                return
        self.bboxBitmap[glyphID >> 3] |= 0x80 >> (glyphID & 7)
        self.bboxStream += sstruct.pack(bboxFormat, glyph)

    def _encodeTriplets(self, glyph):
        assert len(glyph.coordinates) == len(glyph.flags)
        coordinates = glyph.coordinates.copy()
        coordinates.absoluteToRelative()

        flags = array.array("B")
        triplets = array.array("B")
        for i in range(len(coordinates)):
            onCurve = glyph.flags[i] & _g_l_y_f.flagOnCurve
            x, y = coordinates[i]
            absX = abs(x)
            absY = abs(y)
            onCurveBit = 0 if onCurve else 128
            xSignBit = 0 if (x < 0) else 1
            ySignBit = 0 if (y < 0) else 1
            xySignBits = xSignBit + 2 * ySignBit

            if x == 0 and absY < 1280:
                flags.append(onCurveBit + ((absY & 0xF00) >> 7) + ySignBit)
                triplets.append(absY & 0xFF)
            elif y == 0 and absX < 1280:
                flags.append(onCurveBit + 10 + ((absX & 0xF00) >> 7) + xSignBit)
                triplets.append(absX & 0xFF)
            elif absX < 65 and absY < 65:
                flags.append(
                    onCurveBit
                    + 20
                    + ((absX - 1) & 0x30)
                    + (((absY - 1) & 0x30) >> 2)
                    + xySignBits
                )
                triplets.append((((absX - 1) & 0xF) << 4) | ((absY - 1) & 0xF))
            elif absX < 769 and absY < 769:
                flags.append(
                    onCurveBit
                    + 84
                    + 12 * (((absX - 1) & 0x300) >> 8)
                    + (((absY - 1) & 0x300) >> 6)
                    + xySignBits
                )
                triplets.append((absX - 1) & 0xFF)
                triplets.append((absY - 1) & 0xFF)
            elif absX < 4096 and absY < 4096:
                flags.append(onCurveBit + 120 + xySignBits)
                triplets.append(absX >> 4)
                triplets.append(((absX & 0xF) << 4) | (absY >> 8))
                triplets.append(absY & 0xFF)
            else:
                flags.append(onCurveBit + 124 + xySignBits)
                triplets.append(absX >> 8)
                triplets.append(absX & 0xFF)
                triplets.append(absY >> 8)
                triplets.append(absY & 0xFF)

        self.flagStream += flags.tobytes()
        self.glyphStream += triplets.tobytes()


class WOFF2HmtxTable(getTableClass("hmtx")):
    def __init__(self, tag=None):
        self.tableTag = Tag(tag or "hmtx")

    def reconstruct(self, data, ttFont):
        (flags,) = struct.unpack(">B", data[:1])
        data = data[1:]
        if flags & 0b11111100 != 0:
            raise TTLibError("Bits 2-7 of '%s' flags are reserved" % self.tableTag)

        # When bit 0 is _not_ set, the lsb[] array is present
        hasLsbArray = flags & 1 == 0
        # When bit 1 is _not_ set, the leftSideBearing[] array is present
        hasLeftSideBearingArray = flags & 2 == 0
        if hasLsbArray and hasLeftSideBearingArray:
            raise TTLibError(
                "either bits 0 or 1 (or both) must set in transformed '%s' flags"
                % self.tableTag
            )

        glyfTable = ttFont["glyf"]
        headerTable = ttFont["hhea"]
        glyphOrder = glyfTable.glyphOrder
        numGlyphs = len(glyphOrder)
        numberOfHMetrics = min(int(headerTable.numberOfHMetrics), numGlyphs)

        assert len(data) >= 2 * numberOfHMetrics
        advanceWidthArray = array.array("H", data[: 2 * numberOfHMetrics])
        if sys.byteorder != "big":
            advanceWidthArray.byteswap()
        data = data[2 * numberOfHMetrics :]

        if hasLsbArray:
            assert len(data) >= 2 * numberOfHMetrics
            lsbArray = array.array("h", data[: 2 * numberOfHMetrics])
            if sys.byteorder != "big":
                lsbArray.byteswap()
            data = data[2 * numberOfHMetrics :]
        else:
            # compute (proportional) glyphs' lsb from their xMin
            lsbArray = array.array("h")
            for i, glyphName in enumerate(glyphOrder):
                if i >= numberOfHMetrics:
                    break
                glyph = glyfTable[glyphName]
                xMin = getattr(glyph, "xMin", 0)
                lsbArray.append(xMin)

        numberOfSideBearings = numGlyphs - numberOfHMetrics
        if hasLeftSideBearingArray:
            assert len(data) >= 2 * numberOfSideBearings
            leftSideBearingArray = array.array("h", data[: 2 * numberOfSideBearings])
            if sys.byteorder != "big":
                leftSideBearingArray.byteswap()
            data = data[2 * numberOfSideBearings :]
        else:
            # compute (monospaced) glyphs' leftSideBearing from their xMin
            leftSideBearingArray = array.array("h")
            for i, glyphName in enumerate(glyphOrder):
                if i < numberOfHMetrics:
                    continue
                glyph = glyfTable[glyphName]
                xMin = getattr(glyph, "xMin", 0)
                leftSideBearingArray.append(xMin)

        if data:
            raise TTLibError("too much '%s' table data" % self.tableTag)

        self.metrics = {}
        for i in range(numberOfHMetrics):
            glyphName = glyphOrder[i]
            advanceWidth, lsb = advanceWidthArray[i], lsbArray[i]
            self.metrics[glyphName] = (advanceWidth, lsb)
        lastAdvance = advanceWidthArray[-1]
        for i in range(numberOfSideBearings):
            glyphName = glyphOrder[i + numberOfHMetrics]
            self.metrics[glyphName] = (lastAdvance, leftSideBearingArray[i])

    def transform(self, ttFont):
        glyphOrder = ttFont.getGlyphOrder()
        glyf = ttFont["glyf"]
        hhea = ttFont["hhea"]
        numberOfHMetrics = hhea.numberOfHMetrics

        # check if any of the proportional glyphs has left sidebearings that
        # differ from their xMin bounding box values.
        hasLsbArray = False
        for i in range(numberOfHMetrics):
            glyphName = glyphOrder[i]
            lsb = self.metrics[glyphName][1]
            if lsb != getattr(glyf[glyphName], "xMin", 0):
                hasLsbArray = True
                break

        # do the same for the monospaced glyphs (if any) at the end of hmtx table
        hasLeftSideBearingArray = False
        for i in range(numberOfHMetrics, len(glyphOrder)):
            glyphName = glyphOrder[i]
            lsb = self.metrics[glyphName][1]
            if lsb != getattr(glyf[glyphName], "xMin", 0):
                hasLeftSideBearingArray = True
                break

        # if we need to encode both sidebearings arrays, then no transformation is
        # applicable, and we must use the untransformed hmtx data
        if hasLsbArray and hasLeftSideBearingArray:
            return

        # set bit 0 and 1 when the respective arrays are _not_ present
        flags = 0
        if not hasLsbArray:
            flags |= 1 << 0
        if not hasLeftSideBearingArray:
            flags |= 1 << 1

        data = struct.pack(">B", flags)

        advanceWidthArray = array.array(
            "H",
            [
                self.metrics[glyphName][0]
                for i, glyphName in enumerate(glyphOrder)
                if i < numberOfHMetrics
            ],
        )
        if sys.byteorder != "big":
            advanceWidthArray.byteswap()
        data += advanceWidthArray.tobytes()

        if hasLsbArray:
            lsbArray = array.array(
                "h",
                [
                    self.metrics[glyphName][1]
                    for i, glyphName in enumerate(glyphOrder)
                    if i < numberOfHMetrics
                ],
            )
            if sys.byteorder != "big":
                lsbArray.byteswap()
            data += lsbArray.tobytes()

        if hasLeftSideBearingArray:
            leftSideBearingArray = array.array(
                "h",
                [
                    self.metrics[glyphOrder[i]][1]
                    for i in range(numberOfHMetrics, len(glyphOrder))
                ],
            )
            if sys.byteorder != "big":
                leftSideBearingArray.byteswap()
            data += leftSideBearingArray.tobytes()

        return data


class WOFF2FlavorData(WOFFFlavorData):
    Flavor = "woff2"

    def __init__(self, reader=None, data=None, transformedTables=None):
        """Data class that holds the WOFF2 header major/minor version, any
        metadata or private data (as bytes strings), and the set of
        table tags that have transformations applied (if reader is not None),
        or will have once the WOFF2 font is compiled.

        Args:
                reader: an SFNTReader (or subclass) object to read flavor data from.
                data: another WOFFFlavorData object to initialise data from.
                transformedTables: set of strings containing table tags to be transformed.

        Raises:
                ImportError if the brotli module is not installed.

        NOTE: The 'reader' argument, on the one hand, and the 'data' and
        'transformedTables' arguments, on the other hand, are mutually exclusive.
        """
        if not haveBrotli:
            raise ImportError("No module named brotli")

        if reader is not None:
            if data is not None:
                raise TypeError("'reader' and 'data' arguments are mutually exclusive")
            if transformedTables is not None:
                raise TypeError(
                    "'reader' and 'transformedTables' arguments are mutually exclusive"
                )

        if transformedTables is not None and (
            "glyf" in transformedTables
            and "loca" not in transformedTables
            or "loca" in transformedTables
            and "glyf" not in transformedTables
        ):
            raise ValueError("'glyf' and 'loca' must be transformed (or not) together")
        super(WOFF2FlavorData, self).__init__(reader=reader)
        if reader:
            transformedTables = [
                tag for tag, entry in reader.tables.items() if entry.transformed
            ]
        elif data:
            self.majorVersion = data.majorVersion
            self.majorVersion = data.minorVersion
            self.metaData = data.metaData
            self.privData = data.privData
            if transformedTables is None and hasattr(data, "transformedTables"):
                transformedTables = data.transformedTables

        if transformedTables is None:
            transformedTables = woff2TransformedTableTags

        self.transformedTables = set(transformedTables)

    def _decompress(self, rawData):
        return brotli.decompress(rawData)


def unpackBase128(data):
    r"""Read one to five bytes from UIntBase128-encoded input string, and return
    a tuple containing the decoded integer plus any leftover data.

    >>> unpackBase128(b'\x3f\x00\x00') == (63, b"\x00\x00")
    True
    >>> unpackBase128(b'\x8f\xff\xff\xff\x7f')[0] == 4294967295
    True
    >>> unpackBase128(b'\x80\x80\x3f')  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    TTLibError: UIntBase128 value must not start with leading zeros
    >>> unpackBase128(b'\x8f\xff\xff\xff\xff\x7f')[0]  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    TTLibError: UIntBase128-encoded sequence is longer than 5 bytes
    >>> unpackBase128(b'\x90\x80\x80\x80\x00')[0]  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    TTLibError: UIntBase128 value exceeds 2**32-1
    """
    if len(data) == 0:
        raise TTLibError("not enough data to unpack UIntBase128")
    result = 0
    if byteord(data[0]) == 0x80:
        # font must be rejected if UIntBase128 value starts with 0x80
        raise TTLibError("UIntBase128 value must not start with leading zeros")
    for i in range(woff2Base128MaxSize):
        if len(data) == 0:
            raise TTLibError("not enough data to unpack UIntBase128")
        code = byteord(data[0])
        data = data[1:]
        # if any of the top seven bits are set then we're about to overflow
        if result & 0xFE000000:
            raise TTLibError("UIntBase128 value exceeds 2**32-1")
        # set current value = old value times 128 bitwise-or (byte bitwise-and 127)
        result = (result << 7) | (code & 0x7F)
        # repeat until the most significant bit of byte is false
        if (code & 0x80) == 0:
            # return result plus left over data
            return result, data
    # make sure not to exceed the size bound
    raise TTLibError("UIntBase128-encoded sequence is longer than 5 bytes")


def base128Size(n):
    """Return the length in bytes of a UIntBase128-encoded sequence with value n.

    >>> base128Size(0)
    1
    >>> base128Size(24567)
    3
    >>> base128Size(2**32-1)
    5
    """
    assert n >= 0
    size = 1
    while n >= 128:
        size += 1
        n >>= 7
    return size


def packBase128(n):
    r"""Encode unsigned integer in range 0 to 2**32-1 (inclusive) to a string of
    bytes using UIntBase128 variable-length encoding. Produce the shortest possible
    encoding.

    >>> packBase128(63) == b"\x3f"
    True
    >>> packBase128(2**32-1) == b'\x8f\xff\xff\xff\x7f'
    True
    """
    if n < 0 or n >= 2**32:
        raise TTLibError("UIntBase128 format requires 0 <= integer <= 2**32-1")
    data = b""
    size = base128Size(n)
    for i in range(size):
        b = (n >> (7 * (size - i - 1))) & 0x7F
        if i < size - 1:
            b |= 0x80
        data += struct.pack("B", b)
    return data


def unpack255UShort(data):
    """Read one to three bytes from 255UInt16-encoded input string, and return a
    tuple containing the decoded integer plus any leftover data.

    >>> unpack255UShort(bytechr(252))[0]
    252

    Note that some numbers (e.g. 506) can have multiple encodings:
    >>> unpack255UShort(struct.pack("BB", 254, 0))[0]
    506
    >>> unpack255UShort(struct.pack("BB", 255, 253))[0]
    506
    >>> unpack255UShort(struct.pack("BBB", 253, 1, 250))[0]
    506
    """
    code = byteord(data[:1])
    data = data[1:]
    if code == 253:
        # read two more bytes as an unsigned short
        if len(data) < 2:
            raise TTLibError("not enough data to unpack 255UInt16")
        (result,) = struct.unpack(">H", data[:2])
        data = data[2:]
    elif code == 254:
        # read another byte, plus 253 * 2
        if len(data) == 0:
            raise TTLibError("not enough data to unpack 255UInt16")
        result = byteord(data[:1])
        result += 506
        data = data[1:]
    elif code == 255:
        # read another byte, plus 253
        if len(data) == 0:
            raise TTLibError("not enough data to unpack 255UInt16")
        result = byteord(data[:1])
        result += 253
        data = data[1:]
    else:
        # leave as is if lower than 253
        result = code
    # return result plus left over data
    return result, data


def pack255UShort(value):
    r"""Encode unsigned integer in range 0 to 65535 (inclusive) to a bytestring
    using 255UInt16 variable-length encoding.

    >>> pack255UShort(252) == b'\xfc'
    True
    >>> pack255UShort(506) == b'\xfe\x00'
    True
    >>> pack255UShort(762) == b'\xfd\x02\xfa'
    True
    """
    if value < 0 or value > 0xFFFF:
        raise TTLibError("255UInt16 format requires 0 <= integer <= 65535")
    if value < 253:
        return struct.pack(">B", value)
    elif value < 506:
        return struct.pack(">BB", 255, value - 253)
    elif value < 762:
        return struct.pack(">BB", 254, value - 506)
    else:
        return struct.pack(">BH", 253, value)


def compress(input_file, output_file, transform_tables=None):
    """Compress OpenType font to WOFF2.

    Args:
            input_file: a file path, file or file-like object (open in binary mode)
                    containing an OpenType font (either CFF- or TrueType-flavored).
            output_file: a file path, file or file-like object where to save the
                    compressed WOFF2 font.
            transform_tables: Optional[Iterable[str]]: a set of table tags for which
                    to enable preprocessing transformations. By default, only 'glyf'
                    and 'loca' tables are transformed. An empty set means disable all
                    transformations.
    """
    log.info("Processing %s => %s" % (input_file, output_file))

    font = TTFont(input_file, recalcBBoxes=False, recalcTimestamp=False)
    font.flavor = "woff2"

    if transform_tables is not None:
        font.flavorData = WOFF2FlavorData(
            data=font.flavorData, transformedTables=transform_tables
        )

    font.save(output_file, reorderTables=False)


def decompress(input_file, output_file):
    """Decompress WOFF2 font to OpenType font.

    Args:
            input_file: a file path, file or file-like object (open in binary mode)
                    containing a compressed WOFF2 font.
            output_file: a file path, file or file-like object where to save the
                    decompressed OpenType font.
    """
    log.info("Processing %s => %s" % (input_file, output_file))

    font = TTFont(input_file, recalcBBoxes=False, recalcTimestamp=False)
    font.flavor = None
    font.flavorData = None
    font.save(output_file, reorderTables=True)


def main(args=None):
    """Compress and decompress WOFF2 fonts"""
    import argparse
    from fontTools import configLogger
    from fontTools.ttx import makeOutputFileName

    class _HelpAction(argparse._HelpAction):
        def __call__(self, parser, namespace, values, option_string=None):
            subparsers_actions = [
                action
                for action in parser._actions
                if isinstance(action, argparse._SubParsersAction)
            ]
            for subparsers_action in subparsers_actions:
                for choice, subparser in subparsers_action.choices.items():
                    print(subparser.format_help())
            parser.exit()

    class _NoGlyfTransformAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            namespace.transform_tables.difference_update({"glyf", "loca"})

    class _HmtxTransformAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            namespace.transform_tables.add("hmtx")

    parser = argparse.ArgumentParser(
        prog="fonttools ttLib.woff2", description=main.__doc__, add_help=False
    )

    parser.add_argument(
        "-h", "--help", action=_HelpAction, help="show this help message and exit"
    )

    parser_group = parser.add_subparsers(title="sub-commands")
    parser_compress = parser_group.add_parser(
        "compress", description="Compress a TTF or OTF font to WOFF2"
    )
    parser_decompress = parser_group.add_parser(
        "decompress", description="Decompress a WOFF2 font to OTF"
    )

    for subparser in (parser_compress, parser_decompress):
        group = subparser.add_mutually_exclusive_group(required=False)
        group.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="print more messages to console",
        )
        group.add_argument(
            "-q",
            "--quiet",
            action="store_true",
            help="do not print messages to console",
        )

    parser_compress.add_argument(
        "input_file",
        metavar="INPUT",
        help="the input OpenType font (.ttf or .otf)",
    )
    parser_decompress.add_argument(
        "input_file",
        metavar="INPUT",
        help="the input WOFF2 font",
    )

    parser_compress.add_argument(
        "-o",
        "--output-file",
        metavar="OUTPUT",
        help="the output WOFF2 font",
    )
    parser_decompress.add_argument(
        "-o",
        "--output-file",
        metavar="OUTPUT",
        help="the output OpenType font",
    )

    transform_group = parser_compress.add_argument_group()
    transform_group.add_argument(
        "--no-glyf-transform",
        dest="transform_tables",
        nargs=0,
        action=_NoGlyfTransformAction,
        help="Do not transform glyf (and loca) tables",
    )
    transform_group.add_argument(
        "--hmtx-transform",
        dest="transform_tables",
        nargs=0,
        action=_HmtxTransformAction,
        help="Enable optional transformation for 'hmtx' table",
    )

    parser_compress.set_defaults(
        subcommand=compress,
        transform_tables={"glyf", "loca"},
    )
    parser_decompress.set_defaults(subcommand=decompress)

    options = vars(parser.parse_args(args))

    subcommand = options.pop("subcommand", None)
    if not subcommand:
        parser.print_help()
        return

    quiet = options.pop("quiet")
    verbose = options.pop("verbose")
    configLogger(
        level=("ERROR" if quiet else "DEBUG" if verbose else "INFO"),
    )

    if not options["output_file"]:
        if subcommand is compress:
            extension = ".woff2"
        elif subcommand is decompress:
            # choose .ttf/.otf file extension depending on sfntVersion
            with open(options["input_file"], "rb") as f:
                f.seek(4)  # skip 'wOF2' signature
                sfntVersion = f.read(4)
            assert len(sfntVersion) == 4, "not enough data"
            extension = ".otf" if sfntVersion == b"OTTO" else ".ttf"
        else:
            raise AssertionError(subcommand)
        options["output_file"] = makeOutputFileName(
            options["input_file"], outputDir=None, extension=extension
        )

    try:
        subcommand(**options)
    except TTLibError as e:
        parser.error(e)


if __name__ == "__main__":
    sys.exit(main())

# === NexusCore/openenv\Lib\site-packages\IPython\core\magics\execution.py ===
# -*- coding: utf-8 -*-
"""Implementation of execution-related magic functions."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.


import ast
import bdb
import builtins as builtin_mod
import copy
import cProfile as profile
import gc
import itertools
import math
import os
import pstats
import re
import shlex
import sys
import time
import timeit
from typing import Dict, Any
from ast import (
    Assign,
    Call,
    Expr,
    Load,
    Module,
    Name,
    NodeTransformer,
    Store,
    parse,
    unparse,
)
from io import StringIO
from logging import error
from pathlib import Path
from pdb import Restart
from textwrap import dedent, indent
from warnings import warn

from IPython.core import magic_arguments, oinspect, page
from IPython.core.displayhook import DisplayHook
from IPython.core.error import UsageError
from IPython.core.macro import Macro
from IPython.core.magic import (
    Magics,
    cell_magic,
    line_cell_magic,
    line_magic,
    magics_class,
    needs_local_scope,
    no_var_expand,
    on_off,
    output_can_be_silenced,
)
from IPython.testing.skipdoctest import skip_doctest
from IPython.utils.capture import capture_output
from IPython.utils.contexts import preserve_keys
from IPython.utils.ipstruct import Struct
from IPython.utils.module_paths import find_mod
from IPython.utils.path import get_py_filename, shellglob
from IPython.utils.timing import clock, clock2
from IPython.core.magics.ast_mod import ReplaceCodeTransformer

#-----------------------------------------------------------------------------
# Magic implementation classes
#-----------------------------------------------------------------------------


class TimeitResult:
    """
    Object returned by the timeit magic with info about the run.

    Contains the following attributes:

    loops: int
      number of loops done per measurement

    repeat: int
      number of times the measurement was repeated

    best: float
      best execution time / number

    all_runs : list[float]
      execution time of each run (in s)

    compile_time: float
      time of statement compilation (s)

    """
    def __init__(self, loops, repeat, best, worst, all_runs, compile_time, precision):
        self.loops = loops
        self.repeat = repeat
        self.best = best
        self.worst = worst
        self.all_runs = all_runs
        self.compile_time = compile_time
        self._precision = precision
        self.timings = [dt / self.loops for dt in all_runs]

    @property
    def average(self):
        return math.fsum(self.timings) / len(self.timings)

    @property
    def stdev(self):
        mean = self.average
        return (math.fsum([(x - mean) ** 2 for x in self.timings]) / len(self.timings)) ** 0.5

    def __str__(self):
        pm = '+-'
        if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding:
            try:
                "\xb1".encode(sys.stdout.encoding)
                pm = "\xb1"
            except:
                pass
        return "{mean} {pm} {std} per loop (mean {pm} std. dev. of {runs} run{run_plural}, {loops:,} loop{loop_plural} each)".format(
            pm=pm,
            runs=self.repeat,
            loops=self.loops,
            loop_plural="" if self.loops == 1 else "s",
            run_plural="" if self.repeat == 1 else "s",
            mean=_format_time(self.average, self._precision),
            std=_format_time(self.stdev, self._precision),
        )

    def _repr_pretty_(self, p , cycle):
        unic = self.__str__()
        p.text("<TimeitResult : " + unic + ">")


class TimeitTemplateFiller(ast.NodeTransformer):
    """Fill in the AST template for timing execution.

    This is quite closely tied to the template definition, which is in
    :meth:`ExecutionMagics.timeit`.
    """
    def __init__(self, ast_setup, ast_stmt):
        self.ast_setup = ast_setup
        self.ast_stmt = ast_stmt

    def visit_FunctionDef(self, node):
        "Fill in the setup statement"
        self.generic_visit(node)
        if node.name == "inner":
            node.body[:1] = self.ast_setup.body

        return node

    def visit_For(self, node):
        "Fill in the statement to be timed"
        if getattr(getattr(node.body[0], 'value', None), 'id', None) == 'stmt':
            node.body = self.ast_stmt.body
        return node


class Timer(timeit.Timer):
    """Timer class that explicitly uses self.inner

    which is an undocumented implementation detail of CPython,
    not shared by PyPy.
    """

    # Timer.timeit copied from CPython 3.4.2
    def timeit(self, number=timeit.default_number):
        """Time 'number' executions of the main statement.

        To be precise, this executes the setup statement once, and
        then returns the time it takes to execute the main statement
        a number of times, as a float measured in seconds.  The
        argument is the number of times through the loop, defaulting
        to one million.  The main statement, the setup statement and
        the timer function to be used are passed to the constructor.
        """
        it = itertools.repeat(None, number)
        gcold = gc.isenabled()
        gc.disable()
        try:
            timing = self.inner(it, self.timer)
        finally:
            if gcold:
                gc.enable()
        return timing


@magics_class
class ExecutionMagics(Magics):
    """Magics related to code execution, debugging, profiling, etc."""

    _transformers: Dict[str, Any] = {}

    def __init__(self, shell):
        super(ExecutionMagics, self).__init__(shell)
        # Default execution function used to actually run user code.
        self.default_runner = None

    @skip_doctest
    @no_var_expand
    @line_cell_magic
    def prun(self, parameter_s='', cell=None):
        """Run a statement through the python code profiler.

        **Usage, in line mode**::

          %prun [options] statement

        **Usage, in cell mode**::

          %%prun [options] [statement]
          code...
          code...

        In cell mode, the additional code lines are appended to the (possibly
        empty) statement in the first line.  Cell mode allows you to easily
        profile multiline blocks without having to put them in a separate
        function.

        The given statement (which doesn't require quote marks) is run via the
        python profiler in a manner similar to the profile.run() function.
        Namespaces are internally managed to work correctly; profile.run
        cannot be used in IPython because it makes certain assumptions about
        namespaces which do not hold under IPython.

        Options:

        -l <limit>
          you can place restrictions on what or how much of the
          profile gets printed. The limit value can be:

             * A string: only information for function names containing this string
               is printed.

             * An integer: only these many lines are printed.

             * A float (between 0 and 1): this fraction of the report is printed
               (for example, use a limit of 0.4 to see the topmost 40% only).

          You can combine several limits with repeated use of the option. For
          example, ``-l __init__ -l 5`` will print only the topmost 5 lines of
          information about class constructors.

        -r
          return the pstats.Stats object generated by the profiling. This
          object has all the information about the profile in it, and you can
          later use it for further analysis or in other functions.

        -s <key>
          sort profile by given key. You can provide more than one key
          by using the option several times: '-s key1 -s key2 -s key3...'. The
          default sorting key is 'time'.

          The following is copied verbatim from the profile documentation
          referenced below:

          When more than one key is provided, additional keys are used as
          secondary criteria when the there is equality in all keys selected
          before them.

          Abbreviations can be used for any key names, as long as the
          abbreviation is unambiguous.  The following are the keys currently
          defined:

          ============  =====================
          Valid Arg     Meaning
          ============  =====================
          "calls"       call count
          "cumulative"  cumulative time
          "file"        file name
          "module"      file name
          "pcalls"      primitive call count
          "line"        line number
          "name"        function name
          "nfl"         name/file/line
          "stdname"     standard name
          "time"        internal time
          ============  =====================

          Note that all sorts on statistics are in descending order (placing
          most time consuming items first), where as name, file, and line number
          searches are in ascending order (i.e., alphabetical). The subtle
          distinction between "nfl" and "stdname" is that the standard name is a
          sort of the name as printed, which means that the embedded line
          numbers get compared in an odd way.  For example, lines 3, 20, and 40
          would (if the file names were the same) appear in the string order
          "20" "3" and "40".  In contrast, "nfl" does a numeric compare of the
          line numbers.  In fact, sort_stats("nfl") is the same as
          sort_stats("name", "file", "line").

        -T <filename>
          save profile results as shown on screen to a text
          file. The profile is still shown on screen.

        -D <filename>
          save (via dump_stats) profile statistics to given
          filename. This data is in a format understood by the pstats module, and
          is generated by a call to the dump_stats() method of profile
          objects. The profile is still shown on screen.

        -q
          suppress output to the pager.  Best used with -T and/or -D above.

        If you want to run complete programs under the profiler's control, use
        ``%run -p [prof_opts] filename.py [args to program]`` where prof_opts
        contains profiler specific options as described here.

        You can read the complete documentation for the profile module with::

          In [1]: import profile; profile.help()

        .. versionchanged:: 7.3
            User variables are no longer expanded,
            the magic line is always left unmodified.

        """
        opts, arg_str = self.parse_options(parameter_s, 'D:l:rs:T:q',
                                           list_all=True, posix=False)
        if cell is not None:
            arg_str += '\n' + cell
        arg_str = self.shell.transform_cell(arg_str)
        return self._run_with_profiler(arg_str, opts, self.shell.user_ns)

    def _run_with_profiler(self, code, opts, namespace):
        """
        Run `code` with profiler.  Used by ``%prun`` and ``%run -p``.

        Parameters
        ----------
        code : str
            Code to be executed.
        opts : Struct
            Options parsed by `self.parse_options`.
        namespace : dict
            A dictionary for Python namespace (e.g., `self.shell.user_ns`).

        """

        # Fill default values for unspecified options:
        opts.merge(Struct(D=[''], l=[], s=['time'], T=['']))

        prof = profile.Profile()
        try:
            prof = prof.runctx(code, namespace, namespace)
            sys_exit = ''
        except SystemExit:
            sys_exit = """*** SystemExit exception caught in code being profiled."""

        stats = pstats.Stats(prof).strip_dirs().sort_stats(*opts.s)

        lims = opts.l
        if lims:
            lims = []  # rebuild lims with ints/floats/strings
            for lim in opts.l:
                try:
                    lims.append(int(lim))
                except ValueError:
                    try:
                        lims.append(float(lim))
                    except ValueError:
                        lims.append(lim)

        # Trap output.
        stdout_trap = StringIO()
        stats_stream = stats.stream
        try:
            stats.stream = stdout_trap
            stats.print_stats(*lims)
        finally:
            stats.stream = stats_stream

        output = stdout_trap.getvalue()
        output = output.rstrip()

        if 'q' not in opts:
            page.page(output)
        print(sys_exit, end=' ')

        dump_file = opts.D[0]
        text_file = opts.T[0]
        if dump_file:
            prof.dump_stats(dump_file)
            print(
                f"\n*** Profile stats marshalled to file {repr(dump_file)}.{sys_exit}"
            )
        if text_file:
            pfile = Path(text_file)
            pfile.touch(exist_ok=True)
            pfile.write_text(output, encoding="utf-8")

            print(
                f"\n*** Profile printout saved to text file {repr(text_file)}.{sys_exit}"
            )

        if 'r' in opts:
            return stats

        return None

    @line_magic
    def pdb(self, parameter_s=''):
        """Control the automatic calling of the pdb interactive debugger.

        Call as '%pdb on', '%pdb 1', '%pdb off' or '%pdb 0'. If called without
        argument it works as a toggle.

        When an exception is triggered, IPython can optionally call the
        interactive pdb debugger after the traceback printout. %pdb toggles
        this feature on and off.

        The initial state of this feature is set in your configuration
        file (the option is ``InteractiveShell.pdb``).

        If you want to just activate the debugger AFTER an exception has fired,
        without having to type '%pdb on' and rerunning your code, you can use
        the %debug magic."""

        par = parameter_s.strip().lower()

        if par:
            try:
                new_pdb = {'off':0,'0':0,'on':1,'1':1}[par]
            except KeyError:
                print ('Incorrect argument. Use on/1, off/0, '
                       'or nothing for a toggle.')
                return
        else:
            # toggle
            new_pdb = not self.shell.call_pdb

        # set on the shell
        self.shell.call_pdb = new_pdb
        print('Automatic pdb calling has been turned',on_off(new_pdb))

    @magic_arguments.magic_arguments()
    @magic_arguments.argument('--breakpoint', '-b', metavar='FILE:LINE',
        help="""
        Set break point at LINE in FILE.
        """
    )
    @magic_arguments.argument('statement', nargs='*',
        help="""
        Code to run in debugger.
        You can omit this in cell magic mode.
        """
    )
    @no_var_expand
    @line_cell_magic
    @needs_local_scope
    def debug(self, line="", cell=None, local_ns=None):
        """Activate the interactive debugger.

        This magic command support two ways of activating debugger.
        One is to activate debugger before executing code.  This way, you
        can set a break point, to step through the code from the point.
        You can use this mode by giving statements to execute and optionally
        a breakpoint.

        The other one is to activate debugger in post-mortem mode.  You can
        activate this mode simply running %debug without any argument.
        If an exception has just occurred, this lets you inspect its stack
        frames interactively.  Note that this will always work only on the last
        traceback that occurred, so you must call this quickly after an
        exception that you wish to inspect has fired, because if another one
        occurs, it clobbers the previous one.

        If you want IPython to automatically do this on every exception, see
        the %pdb magic for more details.

        .. versionchanged:: 7.3
            When running code, user variables are no longer expanded,
            the magic line is always left unmodified.

        """
        args = magic_arguments.parse_argstring(self.debug, line)

        if not (args.breakpoint or args.statement or cell):
            self._debug_post_mortem()
        elif not (args.breakpoint or cell):
            # If there is no breakpoints, the line is just code to execute
            self._debug_exec(line, None, local_ns)
        else:
            # Here we try to reconstruct the code from the output of
            # parse_argstring. This might not work if the code has spaces
            # For example this fails for `print("a b")`
            code = "\n".join(args.statement)
            if cell:
                code += "\n" + cell
            self._debug_exec(code, args.breakpoint, local_ns)

    def _debug_post_mortem(self):
        self.shell.debugger(force=True)

    def _debug_exec(self, code, breakpoint, local_ns=None):
        if breakpoint:
            (filename, bp_line) = breakpoint.rsplit(':', 1)
            bp_line = int(bp_line)
        else:
            (filename, bp_line) = (None, None)
        self._run_with_debugger(
            code, self.shell.user_ns, filename, bp_line, local_ns=local_ns
        )

    @line_magic
    def tb(self, s):
        """Print the last traceback.

        Optionally, specify an exception reporting mode, tuning the
        verbosity of the traceback. By default the currently-active exception
        mode is used. See %xmode for changing exception reporting modes.

        Valid modes: Plain, Context, Verbose, and Minimal.
        """
        interactive_tb = self.shell.InteractiveTB
        if s:
            # Switch exception reporting mode for this one call.
            # Ensure it is switched back.
            def xmode_switch_err(name):
                warn('Error changing %s exception modes.\n%s' %
                    (name,sys.exc_info()[1]))

            new_mode = s.strip().capitalize()
            original_mode = interactive_tb.mode
            try:
                try:
                    interactive_tb.set_mode(mode=new_mode)
                except Exception:
                    xmode_switch_err('user')
                else:
                    self.shell.showtraceback()
            finally:
                interactive_tb.set_mode(mode=original_mode)
        else:
            self.shell.showtraceback()

    @skip_doctest
    @line_magic
    def run(self, parameter_s='', runner=None,
                  file_finder=get_py_filename):
        """Run the named file inside IPython as a program.

        Usage::

          %run [-n -i -e -G]
               [( -t [-N<N>] | -d [-b<N>] | -p [profile options] )]
               ( -m mod | filename ) [args]

        The filename argument should be either a pure Python script (with
        extension ``.py``), or a file with custom IPython syntax (such as
        magics). If the latter, the file can be either a script with ``.ipy``
        extension, or a Jupyter notebook with ``.ipynb`` extension. When running
        a Jupyter notebook, the output from print statements and other
        displayed objects will appear in the terminal (even matplotlib figures
        will open, if a terminal-compliant backend is being used). Note that,
        at the system command line, the ``jupyter run`` command offers similar
        functionality for executing notebooks (albeit currently with some
        differences in supported options).

        Parameters after the filename are passed as command-line arguments to
        the program (put in sys.argv). Then, control returns to IPython's
        prompt.

        This is similar to running at a system prompt ``python file args``,
        but with the advantage of giving you IPython's tracebacks, and of
        loading all variables into your interactive namespace for further use
        (unless -p is used, see below).

        The file is executed in a namespace initially consisting only of
        ``__name__=='__main__'`` and sys.argv constructed as indicated. It thus
        sees its environment as if it were being run as a stand-alone program
        (except for sharing global objects such as previously imported
        modules). But after execution, the IPython interactive namespace gets
        updated with all variables defined in the program (except for ``__name__``
        and ``sys.argv``). This allows for very convenient loading of code for
        interactive work, while giving each program a 'clean sheet' to run in.

        Arguments are expanded using shell-like glob match.  Patterns
        '*', '?', '[seq]' and '[!seq]' can be used.  Additionally,
        tilde '~' will be expanded into user's home directory.  Unlike
        real shells, quotation does not suppress expansions.  Use
        *two* back slashes (e.g. ``\\\\*``) to suppress expansions.
        To completely disable these expansions, you can use -G flag.

        On Windows systems, the use of single quotes `'` when specifying
        a file is not supported. Use double quotes `"`.

        Options:

        -n
          __name__ is NOT set to '__main__', but to the running file's name
          without extension (as python does under import).  This allows running
          scripts and reloading the definitions in them without calling code
          protected by an ``if __name__ == "__main__"`` clause.

        -i
          run the file in IPython's namespace instead of an empty one. This
          is useful if you are experimenting with code written in a text editor
          which depends on variables defined interactively.

        -e
          ignore sys.exit() calls or SystemExit exceptions in the script
          being run.  This is particularly useful if IPython is being used to
          run unittests, which always exit with a sys.exit() call.  In such
          cases you are interested in the output of the test results, not in
          seeing a traceback of the unittest module.

        -t
          print timing information at the end of the run.  IPython will give
          you an estimated CPU time consumption for your script, which under
          Unix uses the resource module to avoid the wraparound problems of
          time.clock().  Under Unix, an estimate of time spent on system tasks
          is also given (for Windows platforms this is reported as 0.0).

          If -t is given, an additional ``-N<N>`` option can be given, where <N>
          must be an integer indicating how many times you want the script to
          run.  The final timing report will include total and per run results.

          For example (testing the script uniq_stable.py)::

              In [1]: run -t uniq_stable

              IPython CPU timings (estimated):
                User  :    0.19597 s.
                System:        0.0 s.

              In [2]: run -t -N5 uniq_stable

              IPython CPU timings (estimated):
              Total runs performed: 5
                Times :      Total       Per run
                User  :   0.910862 s,  0.1821724 s.
                System:        0.0 s,        0.0 s.

        -d
          run your program under the control of pdb, the Python debugger.
          This allows you to execute your program step by step, watch variables,
          etc.  Internally, what IPython does is similar to calling::

              pdb.run('execfile("YOURFILENAME")')

          with a breakpoint set on line 1 of your file.  You can change the line
          number for this automatic breakpoint to be <N> by using the -bN option
          (where N must be an integer). For example::

              %run -d -b40 myscript

          will set the first breakpoint at line 40 in myscript.py.  Note that
          the first breakpoint must be set on a line which actually does
          something (not a comment or docstring) for it to stop execution.

          Or you can specify a breakpoint in a different file::

              %run -d -b myotherfile.py:20 myscript

          When the pdb debugger starts, you will see a (Pdb) prompt.  You must
          first enter 'c' (without quotes) to start execution up to the first
          breakpoint.

          Entering 'help' gives information about the use of the debugger.  You
          can easily see pdb's full documentation with "import pdb;pdb.help()"
          at a prompt.

        -p
          run program under the control of the Python profiler module (which
          prints a detailed report of execution times, function calls, etc).

          You can pass other options after -p which affect the behavior of the
          profiler itself. See the docs for %prun for details.

          In this mode, the program's variables do NOT propagate back to the
          IPython interactive namespace (because they remain in the namespace
          where the profiler executes them).

          Internally this triggers a call to %prun, see its documentation for
          details on the options available specifically for profiling.

        There is one special usage for which the text above doesn't apply:
        if the filename ends with .ipy[nb], the file is run as ipython script,
        just as if the commands were written on IPython prompt.

        -m
          specify module name to load instead of script path. Similar to
          the -m option for the python interpreter. Use this option last if you
          want to combine with other %run options. Unlike the python interpreter
          only source modules are allowed no .pyc or .pyo files.
          For example::

              %run -m example

          will run the example module.

        -G
          disable shell-like glob expansion of arguments.

        """

        # Logic to handle issue #3664
        # Add '--' after '-m <module_name>' to ignore additional args passed to a module.
        if '-m' in parameter_s and '--' not in parameter_s:
            argv = shlex.split(parameter_s, posix=(os.name == 'posix'))
            for idx, arg in enumerate(argv):
                if arg and arg.startswith('-') and arg != '-':
                    if arg == '-m':
                        argv.insert(idx + 2, '--')
                        break
                else:
                    # Positional arg, break
                    break
            parameter_s = ' '.join(shlex.quote(arg) for arg in argv)

        # get arguments and set sys.argv for program to be run.
        opts, arg_lst = self.parse_options(parameter_s,
                                           'nidtN:b:pD:l:rs:T:em:G',
                                           mode='list', list_all=1)
        if "m" in opts:
            modulename = opts["m"][0]
            modpath = find_mod(modulename)
            if modpath is None:
                msg = '%r is not a valid modulename on sys.path'%modulename
                raise Exception(msg)
            arg_lst = [modpath] + arg_lst
        try:
            fpath = None # initialize to make sure fpath is in scope later
            fpath = arg_lst[0]
            filename = file_finder(fpath)
        except IndexError as e:
            msg = 'you must provide at least a filename.'
            raise Exception(msg) from e
        except IOError as e:
            try:
                msg = str(e)
            except UnicodeError:
                msg = e.message
            if os.name == 'nt' and re.match(r"^'.*'$",fpath):
                warn('For Windows, use double quotes to wrap a filename: %run "mypath\\myfile.py"')
            raise Exception(msg) from e
        except TypeError:
            if fpath in sys.meta_path:
                filename = ""
            else:
                raise

        if filename.lower().endswith(('.ipy', '.ipynb')):
            with preserve_keys(self.shell.user_ns, '__file__'):
                self.shell.user_ns['__file__'] = filename
                self.shell.safe_execfile_ipy(filename, raise_exceptions=True)
            return

        # Control the response to exit() calls made by the script being run
        exit_ignore = 'e' in opts

        # Make sure that the running script gets a proper sys.argv as if it
        # were run from a system shell.
        save_argv = sys.argv # save it for later restoring

        if 'G' in opts:
            args = arg_lst[1:]
        else:
            # tilde and glob expansion
            args = shellglob(map(os.path.expanduser,  arg_lst[1:]))

        sys.argv = [filename] + args  # put in the proper filename

        if 'n' in opts:
            name = Path(filename).stem
        else:
            name = '__main__'

        if 'i' in opts:
            # Run in user's interactive namespace
            prog_ns = self.shell.user_ns
            __name__save = self.shell.user_ns['__name__']
            prog_ns['__name__'] = name
            main_mod = self.shell.user_module

            # Since '%run foo' emulates 'python foo.py' at the cmd line, we must
            # set the __file__ global in the script's namespace
            # TK: Is this necessary in interactive mode?
            prog_ns['__file__'] = filename
        else:
            # Run in a fresh, empty namespace

            # The shell MUST hold a reference to prog_ns so after %run
            # exits, the python deletion mechanism doesn't zero it out
            # (leaving dangling references). See interactiveshell for details
            main_mod = self.shell.new_main_mod(filename, name)
            prog_ns = main_mod.__dict__

        # pickle fix.  See interactiveshell for an explanation.  But we need to
        # make sure that, if we overwrite __main__, we replace it at the end
        main_mod_name = prog_ns['__name__']

        if main_mod_name == '__main__':
            restore_main = sys.modules['__main__']
        else:
            restore_main = False

        # This needs to be undone at the end to prevent holding references to
        # every single object ever created.
        sys.modules[main_mod_name] = main_mod

        if 'p' in opts or 'd' in opts:
            if 'm' in opts:
                code = 'run_module(modulename, prog_ns)'
                code_ns = {
                    'run_module': self.shell.safe_run_module,
                    'prog_ns': prog_ns,
                    'modulename': modulename,
                }
            else:
                if 'd' in opts:
                    # allow exceptions to raise in debug mode
                    code = 'execfile(filename, prog_ns, raise_exceptions=True)'
                else:
                    code = 'execfile(filename, prog_ns)'
                code_ns = {
                    'execfile': self.shell.safe_execfile,
                    'prog_ns': prog_ns,
                    'filename': get_py_filename(filename),
                }

        try:
            stats = None
            if 'p' in opts:
                stats = self._run_with_profiler(code, opts, code_ns)
            else:
                if 'd' in opts:
                    bp_file, bp_line = parse_breakpoint(
                        opts.get('b', ['1'])[0], filename)
                    self._run_with_debugger(
                        code, code_ns, filename, bp_line, bp_file)
                else:
                    if 'm' in opts:
                        def run():
                            self.shell.safe_run_module(modulename, prog_ns)
                    else:
                        if runner is None:
                            runner = self.default_runner
                        if runner is None:
                            runner = self.shell.safe_execfile

                        def run():
                            runner(filename, prog_ns, prog_ns,
                                    exit_ignore=exit_ignore)

                    if 't' in opts:
                        # timed execution
                        try:
                            nruns = int(opts['N'][0])
                            if nruns < 1:
                                error('Number of runs must be >=1')
                                return
                        except (KeyError):
                            nruns = 1
                        self._run_with_timing(run, nruns)
                    else:
                        # regular execution
                        run()

            if 'i' in opts:
                self.shell.user_ns['__name__'] = __name__save
            else:
                # update IPython interactive namespace

                # Some forms of read errors on the file may mean the
                # __name__ key was never set; using pop we don't have to
                # worry about a possible KeyError.
                prog_ns.pop('__name__', None)

                with preserve_keys(self.shell.user_ns, '__file__'):
                    self.shell.user_ns.update(prog_ns)
        finally:
            # It's a bit of a mystery why, but __builtins__ can change from
            # being a module to becoming a dict missing some key data after
            # %run.  As best I can see, this is NOT something IPython is doing
            # at all, and similar problems have been reported before:
            # http://coding.derkeiler.com/Archive/Python/comp.lang.python/2004-10/0188.html
            # Since this seems to be done by the interpreter itself, the best
            # we can do is to at least restore __builtins__ for the user on
            # exit.
            self.shell.user_ns['__builtins__'] = builtin_mod

            # Ensure key global structures are restored
            sys.argv = save_argv
            if restore_main:
                sys.modules['__main__'] = restore_main
                if '__mp_main__' in sys.modules:
                    sys.modules['__mp_main__'] = restore_main
            else:
                # Remove from sys.modules the reference to main_mod we'd
                # added.  Otherwise it will trap references to objects
                # contained therein.
                del sys.modules[main_mod_name]

        return stats

    def _run_with_debugger(
        self, code, code_ns, filename=None, bp_line=None, bp_file=None, local_ns=None
    ):
        """
        Run `code` in debugger with a break point.

        Parameters
        ----------
        code : str
            Code to execute.
        code_ns : dict
            A namespace in which `code` is executed.
        filename : str
            `code` is ran as if it is in `filename`.
        bp_line : int, optional
            Line number of the break point.
        bp_file : str, optional
            Path to the file in which break point is specified.
            `filename` is used if not given.
        local_ns : dict, optional
            A local namespace in which `code` is executed.

        Raises
        ------
        UsageError
            If the break point given by `bp_line` is not valid.

        """
        deb = self.shell.InteractiveTB.pdb
        if not deb:
            self.shell.InteractiveTB.pdb = self.shell.InteractiveTB.debugger_cls()
            deb = self.shell.InteractiveTB.pdb

        # deb.checkline() fails if deb.curframe exists but is None; it can
        # handle it not existing. https://github.com/ipython/ipython/issues/10028
        if hasattr(deb, 'curframe'):
            del deb.curframe

        # reset Breakpoint state, which is moronically kept
        # in a class
        bdb.Breakpoint.next = 1
        bdb.Breakpoint.bplist = {}
        bdb.Breakpoint.bpbynumber = [None]
        deb.clear_all_breaks()
        if bp_line is not None:
            # Set an initial breakpoint to stop execution
            maxtries = 10
            bp_file = bp_file or filename
            checkline = deb.checkline(bp_file, bp_line)
            if not checkline:
                for bp in range(bp_line + 1, bp_line + maxtries + 1):
                    if deb.checkline(bp_file, bp):
                        break
                else:
                    msg = ("\nI failed to find a valid line to set "
                           "a breakpoint\n"
                           "after trying up to line: %s.\n"
                           "Please set a valid breakpoint manually "
                           "with the -b option." % bp)
                    raise UsageError(msg)
            # if we find a good linenumber, set the breakpoint
            deb.do_break('%s:%s' % (bp_file, bp_line))

        if filename:
            # Mimic Pdb._runscript(...)
            deb._wait_for_mainpyfile = True
            deb.mainpyfile = deb.canonic(filename)

        # Start file run
        print("NOTE: Enter 'c' at the %s prompt to continue execution." % deb.prompt)
        try:
            if filename:
                # save filename so it can be used by methods on the deb object
                deb._exec_filename = filename
            while True:
                try:
                    trace = sys.gettrace()
                    deb.run(code, code_ns, local_ns)
                except Restart:
                    print("Restarting")
                    if filename:
                        deb._wait_for_mainpyfile = True
                        deb.mainpyfile = deb.canonic(filename)
                    continue
                else:
                    break
                finally:
                    sys.settrace(trace)

            # Perform proper cleanup of the session in case if
            # it exited with "continue" and not "quit" command
            if hasattr(deb, "rcLines"):
                # Run this code defensively in case if custom debugger
                # class does not implement rcLines, which although public
                # is an implementation detail of `pdb.Pdb` and not part of
                # the more generic basic debugger framework (`bdb.Bdb`).
                deb.set_quit()
                deb.rcLines.extend(["q"])
                try:
                    deb.run("", code_ns, local_ns)
                except StopIteration:
                    # Stop iteration is raised on quit command
                    pass

        except Exception:
            etype, value, tb = sys.exc_info()
            # Skip three frames in the traceback: the %run one,
            # one inside bdb.py, and the command-line typed by the
            # user (run by exec in pdb itself).
            self.shell.InteractiveTB(etype, value, tb, tb_offset=3)

    @staticmethod
    def _run_with_timing(run, nruns):
        """
        Run function `run` and print timing information.

        Parameters
        ----------
        run : callable
            Any callable object which takes no argument.
        nruns : int
            Number of times to execute `run`.

        """
        twall0 = time.perf_counter()
        if nruns == 1:
            t0 = clock2()
            run()
            t1 = clock2()
            t_usr = t1[0] - t0[0]
            t_sys = t1[1] - t0[1]
            print("\nIPython CPU timings (estimated):")
            print("  User   : %10.2f s." % t_usr)
            print("  System : %10.2f s." % t_sys)
        else:
            runs = range(nruns)
            t0 = clock2()
            for nr in runs:
                run()
            t1 = clock2()
            t_usr = t1[0] - t0[0]
            t_sys = t1[1] - t0[1]
            print("\nIPython CPU timings (estimated):")
            print("Total runs performed:", nruns)
            print("  Times  : %10s   %10s" % ('Total', 'Per run'))
            print("  User   : %10.2f s, %10.2f s." % (t_usr, t_usr / nruns))
            print("  System : %10.2f s, %10.2f s." % (t_sys, t_sys / nruns))
        twall1 = time.perf_counter()
        print("Wall time: %10.2f s." % (twall1 - twall0))

    @skip_doctest
    @no_var_expand
    @line_cell_magic
    @needs_local_scope
    def timeit(self, line='', cell=None, local_ns=None):
        """Time execution of a Python statement or expression

        **Usage, in line mode**::

          %timeit [-n<N> -r<R> [-t|-c] -q -p<P> [-o|-v <V>]] statement

        **or in cell mode**::

          %%timeit [-n<N> -r<R> [-t|-c] -q -p<P> [-o|-v <V>]] setup_code
          code
          code...

        Time execution of a Python statement or expression using the timeit
        module.  This function can be used both as a line and cell magic:

        - In line mode you can time a single-line statement (though multiple
          ones can be chained with using semicolons).

        - In cell mode, the statement in the first line is used as setup code
          (executed but not timed) and the body of the cell is timed.  The cell
          body has access to any variables created in the setup code.

        Options:

        -n<N>
          Execute the given statement N times in a loop. If N is not
          provided, N is determined so as to get sufficient accuracy.

        -r<R>
          Number of repeats R, each consisting of N loops, and take the
          average result.
          Default: 7

        -t
          Use ``time.time`` to measure the time, which is the default on Unix.
          This function measures wall time.

        -c
          Use ``time.clock`` to measure the time, which is the default on
          Windows and measures wall time. On Unix, ``resource.getrusage`` is used
          instead and returns the CPU user time.

        -p<P>
          Use a precision of P digits to display the timing result.
          Default: 3

        -q
          Quiet, do not print result.

        -o
          Return a ``TimeitResult`` that can be stored in a variable to inspect
          the result in more details.

        -v <V>
          Like ``-o``, but save the ``TimeitResult`` directly to variable <V>.

        .. versionchanged:: 7.3
            User variables are no longer expanded,
            the magic line is always left unmodified.

        Examples
        --------
        ::

          In [1]: %timeit pass
          8.26 ns ± 0.12 ns per loop (mean ± std. dev. of 7 runs, 100000000 loops each)

          In [2]: u = None

          In [3]: %timeit u is None
          29.9 ns ± 0.643 ns per loop (mean ± std. dev. of 7 runs, 10000000 loops each)

          In [4]: %timeit -r 4 u == None

          In [5]: import time

          In [6]: %timeit -n1 time.sleep(2)

        The times reported by ``%timeit`` will be slightly higher than those
        reported by the timeit.py script when variables are accessed. This is
        due to the fact that ``%timeit`` executes the statement in the namespace
        of the shell, compared with timeit.py, which uses a single setup
        statement to import function or create variables. Generally, the bias
        does not matter as long as results from timeit.py are not mixed with
        those from ``%timeit``."""

        opts, stmt = self.parse_options(
            line, "n:r:tcp:qov:", posix=False, strict=False, preserve_non_opts=True
        )
        if stmt == "" and cell is None:
            return

        timefunc = timeit.default_timer
        number = int(getattr(opts, "n", 0))
        default_repeat = 7 if timeit.default_repeat < 7 else timeit.default_repeat
        repeat = int(getattr(opts, "r", default_repeat))
        precision = int(getattr(opts, "p", 3))
        quiet = "q" in opts
        return_result = "o" in opts
        save_result = "v" in opts
        if hasattr(opts, "t"):
            timefunc = time.time
        if hasattr(opts, "c"):
            timefunc = clock

        timer = Timer(timer=timefunc)
        # this code has tight coupling to the inner workings of timeit.Timer,
        # but is there a better way to achieve that the code stmt has access
        # to the shell namespace?
        transform  = self.shell.transform_cell

        if cell is None:
            # called as line magic
            ast_setup = self.shell.compile.ast_parse("pass")
            ast_stmt = self.shell.compile.ast_parse(transform(stmt))
        else:
            ast_setup = self.shell.compile.ast_parse(transform(stmt))
            ast_stmt = self.shell.compile.ast_parse(transform(cell))

        ast_setup = self.shell.transform_ast(ast_setup)
        ast_stmt = self.shell.transform_ast(ast_stmt)

        # Check that these compile to valid Python code *outside* the timer func
        # Invalid code may become valid when put inside the function & loop,
        # which messes up error messages.
        # https://github.com/ipython/ipython/issues/10636
        self.shell.compile(ast_setup, "<magic-timeit-setup>", "exec")
        self.shell.compile(ast_stmt, "<magic-timeit-stmt>", "exec")

        # This codestring is taken from timeit.template - we fill it in as an
        # AST, so that we can apply our AST transformations to the user code
        # without affecting the timing code.
        timeit_ast_template = ast.parse('def inner(_it, _timer):\n'
                                        '    setup\n'
                                        '    _t0 = _timer()\n'
                                        '    for _i in _it:\n'
                                        '        stmt\n'
                                        '    _t1 = _timer()\n'
                                        '    return _t1 - _t0\n')

        timeit_ast = TimeitTemplateFiller(ast_setup, ast_stmt).visit(timeit_ast_template)
        timeit_ast = ast.fix_missing_locations(timeit_ast)

        # Track compilation time so it can be reported if too long
        # Minimum time above which compilation time will be reported
        tc_min = 0.1

        t0 = clock()
        code = self.shell.compile(timeit_ast, "<magic-timeit>", "exec")
        tc = clock()-t0

        ns = {}
        glob = self.shell.user_ns
        # handles global vars with same name as local vars. We store them in conflict_globs.
        conflict_globs = {}
        if local_ns and cell is None:
            for var_name, var_val in glob.items():
                if var_name in local_ns:
                    conflict_globs[var_name] = var_val
            glob.update(local_ns)

        exec(code, glob, ns)
        timer.inner = ns["inner"]

        # This is used to check if there is a huge difference between the
        # best and worst timings.
        # Issue: https://github.com/ipython/ipython/issues/6471
        if number == 0:
            # determine number so that 0.2 <= total time < 2.0
            for index in range(0, 10):
                number = 10 ** index
                time_number = timer.timeit(number)
                if time_number >= 0.2:
                    break

        all_runs = timer.repeat(repeat, number)
        best = min(all_runs) / number
        worst = max(all_runs) / number
        timeit_result = TimeitResult(number, repeat, best, worst, all_runs, tc, precision)

        # Restore global vars from conflict_globs
        if conflict_globs:
            glob.update(conflict_globs)

        if not quiet:
            # Check best timing is greater than zero to avoid a
            # ZeroDivisionError.
            # In cases where the slowest timing is lesser than a microsecond
            # we assume that it does not really matter if the fastest
            # timing is 4 times faster than the slowest timing or not.
            if worst > 4 * best and best > 0 and worst > 1e-6:
                print("The slowest run took %0.2f times longer than the "
                      "fastest. This could mean that an intermediate result "
                      "is being cached." % (worst / best))

            print( timeit_result )

            if tc > tc_min:
                print("Compiler time: %.2f s" % tc)

        if save_result:
            self.shell.user_ns[opts.v] = timeit_result

        if return_result:
            return timeit_result

    @skip_doctest
    @no_var_expand
    @needs_local_scope
    @line_cell_magic
    @output_can_be_silenced
    def time(self, line="", cell=None, local_ns=None):
        """Time execution of a Python statement or expression.

        The CPU and wall clock times are printed, and the value of the
        expression (if any) is returned.  Note that under Win32, system time
        is always reported as 0, since it can not be measured.

        This function can be used both as a line and cell magic:

        - In line mode you can time a single-line statement (though multiple
          ones can be chained with using semicolons).

        - In cell mode, you can time the cell body (a directly
          following statement raises an error).

        This function provides very basic timing functionality. Use the timeit
        magic for more control over the measurement.

        .. versionchanged:: 7.3
            User variables are no longer expanded,
            the magic line is always left unmodified.

        .. versionchanged:: 8.3
            The time magic now correctly propagates system-exiting exceptions
            (such as ``KeyboardInterrupt`` invoked when interrupting execution)
            rather than just printing out the exception traceback.
            The non-system-exception will still be caught as before.

        Examples
        --------
        ::

          In [1]: %time 2**128
          CPU times: user 0.00 s, sys: 0.00 s, total: 0.00 s
          Wall time: 0.00
          Out[1]: 340282366920938463463374607431768211456L

          In [2]: n = 1000000

          In [3]: %time sum(range(n))
          CPU times: user 1.20 s, sys: 0.05 s, total: 1.25 s
          Wall time: 1.37
          Out[3]: 499999500000L

          In [4]: %time print('hello world')
          hello world
          CPU times: user 0.00 s, sys: 0.00 s, total: 0.00 s
          Wall time: 0.00

        .. note::
            The time needed by Python to compile the given expression will be
            reported if it is more than 0.1s.

            In the example below, the actual exponentiation is done by Python
            at compilation time, so while the expression can take a noticeable
            amount of time to compute, that time is purely due to the
            compilation::

                In [5]: %time 3**9999;
                CPU times: user 0.00 s, sys: 0.00 s, total: 0.00 s
                Wall time: 0.00 s

                In [6]: %time 3**999999;
                CPU times: user 0.00 s, sys: 0.00 s, total: 0.00 s
                Wall time: 0.00 s
                Compiler : 0.78 s
        """
        # fail immediately if the given expression can't be compiled

        if line and cell:
            raise UsageError("Can't use statement directly after '%%time'!")

        if cell:
            expr = self.shell.transform_cell(cell)
        else:
            expr = self.shell.transform_cell(line)

        # Minimum time above which parse time will be reported
        tp_min = 0.1

        t0 = clock()
        expr_ast = self.shell.compile.ast_parse(expr)
        tp = clock() - t0

        # Apply AST transformations
        expr_ast = self.shell.transform_ast(expr_ast)

        # Minimum time above which compilation time will be reported
        tc_min = 0.1

        expr_val = None
        if len(expr_ast.body) == 1 and isinstance(expr_ast.body[0], ast.Expr):
            mode = 'eval'
            source = '<timed eval>'
            expr_ast = ast.Expression(expr_ast.body[0].value)
        else:
            mode = 'exec'
            source = '<timed exec>'
            # multi-line %%time case
            if len(expr_ast.body) > 1 and isinstance(expr_ast.body[-1], ast.Expr):
                expr_val = expr_ast.body[-1]
                expr_ast = expr_ast.body[:-1]
                expr_ast = Module(expr_ast, [])
                expr_val = ast.Expression(expr_val.value)

        t0 = clock()
        code = self.shell.compile(expr_ast, source, mode)
        tc = clock() - t0

        # skew measurement as little as possible
        glob = self.shell.user_ns
        wtime = time.time
        # time execution
        wall_st = wtime()
        if mode == "eval":
            st = clock2()
            try:
                out = eval(code, glob, local_ns)
            except Exception:
                self.shell.showtraceback()
                return
            end = clock2()
        else:
            st = clock2()
            try:
                exec(code, glob, local_ns)
                out = None
                # multi-line %%time case
                if expr_val is not None:
                    code_2 = self.shell.compile(expr_val, source, 'eval')
                    out = eval(code_2, glob, local_ns)
            except Exception:
                self.shell.showtraceback()
                return
            end = clock2()

        wall_end = wtime()
        # Compute actual times and report
        wall_time = wall_end - wall_st
        cpu_user = end[0] - st[0]
        cpu_sys = end[1] - st[1]
        cpu_tot = cpu_user + cpu_sys
        # On windows cpu_sys is always zero, so only total is displayed
        if sys.platform != "win32":
            print(
                f"CPU times: user {_format_time(cpu_user)}, sys: {_format_time(cpu_sys)}, total: {_format_time(cpu_tot)}"
            )
        else:
            print(f"CPU times: total: {_format_time(cpu_tot)}")
        print(f"Wall time: {_format_time(wall_time)}")
        if tc > tc_min:
            print(f"Compiler : {_format_time(tc)}")
        if tp > tp_min:
            print(f"Parser   : {_format_time(tp)}")
        return out

    @skip_doctest
    @line_magic
    def macro(self, parameter_s=''):
        """Define a macro for future re-execution. It accepts ranges of history,
        filenames or string objects.

        Usage::

          %macro [options] name n1-n2 n3-n4 ... n5 .. n6 ...

        Options:

        -r
          Use 'raw' input.  By default, the 'processed' history is used,
          so that magics are loaded in their transformed version to valid
          Python.  If this option is given, the raw input as typed at the
          command line is used instead.

        -q
          Quiet macro definition.  By default, a tag line is printed
          to indicate the macro has been created, and then the contents of
          the macro are printed.  If this option is given, then no printout
          is produced once the macro is created.

        This will define a global variable called `name` which is a string
        made of joining the slices and lines you specify (n1,n2,... numbers
        above) from your input history into a single string. This variable
        acts like an automatic function which re-executes those lines as if
        you had typed them. You just type 'name' at the prompt and the code
        executes.

        The syntax for indicating input ranges is described in %history.

        Note: as a 'hidden' feature, you can also use traditional python slice
        notation, where N:M means numbers N through M-1.

        For example, if your history contains (print using %hist -n )::

          44: x=1
          45: y=3
          46: z=x+y
          47: print(x)
          48: a=5
          49: print('x',x,'y',y)

        you can create a macro with lines 44 through 47 (included) and line 49
        called my_macro with::

          In [55]: %macro my_macro 44-47 49

        Now, typing `my_macro` (without quotes) will re-execute all this code
        in one pass.

        You don't need to give the line-numbers in order, and any given line
        number can appear multiple times. You can assemble macros with any
        lines from your input history in any order.

        The macro is a simple object which holds its value in an attribute,
        but IPython's display system checks for macros and executes them as
        code instead of printing them when you type their name.

        You can view a macro's contents by explicitly printing it with::

          print(macro_name)

        """
        opts,args = self.parse_options(parameter_s,'rq',mode='list')
        if not args:   # List existing macros
            return sorted(k for k,v in self.shell.user_ns.items() if isinstance(v, Macro))
        if len(args) == 1:
            raise UsageError(
                "%macro insufficient args; usage '%macro name n1-n2 n3-4...")
        name, codefrom = args[0], " ".join(args[1:])

        # print('rng',ranges)  # dbg
        try:
            lines = self.shell.find_user_code(codefrom, 'r' in opts)
        except (ValueError, TypeError) as e:
            print(e.args[0])
            return
        macro = Macro(lines)
        self.shell.define_macro(name, macro)
        if "q" not in opts:
            print(
                "Macro `%s` created. To execute, type its name (without quotes)." % name
            )
            print("=== Macro contents: ===")
            print(macro, end=" ")

    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        "output",
        type=str,
        default="",
        nargs="?",
        help="""
        
        The name of the variable in which to store output.
        This is a ``utils.io.CapturedIO`` object with stdout/err attributes
        for the text of the captured output.

        CapturedOutput also has a ``show()`` method for displaying the output,
        and ``__call__`` as well, so you can use that to quickly display the
        output.

        If unspecified, captured output is discarded.
        """,
    )
    @magic_arguments.argument(
        "--no-stderr", action="store_true", help="""Don't capture stderr."""
    )
    @magic_arguments.argument(
        "--no-stdout", action="store_true", help="""Don't capture stdout."""
    )
    @magic_arguments.argument(
        "--no-display",
        action="store_true",
        help="""Don't capture IPython's rich display."""
    )
    @cell_magic
    def capture(self, line, cell):
        """run the cell, capturing stdout, stderr, and IPython's rich display() calls."""
        args = magic_arguments.parse_argstring(self.capture, line)
        out = not args.no_stdout
        err = not args.no_stderr
        disp = not args.no_display
        with capture_output(out, err, disp) as io:
            self.shell.run_cell(cell)
        if DisplayHook.semicolon_at_end_of_expression(cell):
            if args.output in self.shell.user_ns:
                del self.shell.user_ns[args.output]
        elif args.output:
            self.shell.user_ns[args.output] = io

    @skip_doctest
    @magic_arguments.magic_arguments()
    @magic_arguments.argument("name", type=str, default="default", nargs="?")
    @magic_arguments.argument(
        "--remove", action="store_true", help="remove the current transformer"
    )
    @magic_arguments.argument(
        "--list", action="store_true", help="list existing transformers name"
    )
    @magic_arguments.argument(
        "--list-all",
        action="store_true",
        help="list existing transformers name and code template",
    )
    @line_cell_magic
    def code_wrap(self, line, cell=None):
        """
        Simple magic to quickly define a code transformer for all IPython's future input.

        ``__code__`` and ``__ret__`` are special variable that represent the code to run
        and the value of the last expression of ``__code__`` respectively.

        Examples
        --------

        .. ipython::

            In [1]: %%code_wrap before_after
               ...: print('before')
               ...: __code__
               ...: print('after')
               ...: __ret__


            In [2]: 1
            before
            after
            Out[2]: 1

            In [3]: %code_wrap --list
            before_after

            In [4]: %code_wrap --list-all
            before_after :
                print('before')
                __code__
                print('after')
                __ret__

            In [5]: %code_wrap --remove before_after

        """
        args = magic_arguments.parse_argstring(self.code_wrap, line)

        if args.list:
            for name in self._transformers.keys():
                print(name)
            return
        if args.list_all:
            for name, _t in self._transformers.items():
                print(name, ":")
                print(indent(ast.unparse(_t.template), "    "))
            print()
            return

        to_remove = self._transformers.pop(args.name, None)
        if to_remove in self.shell.ast_transformers:
            self.shell.ast_transformers.remove(to_remove)
        if cell is None or args.remove:
            return

        _trs = ReplaceCodeTransformer(ast.parse(cell))

        self._transformers[args.name] = _trs
        self.shell.ast_transformers.append(_trs)


def parse_breakpoint(text, current_file):
    '''Returns (file, line) for file:line and (current_file, line) for line'''
    colon = text.find(':')
    if colon == -1:
        return current_file, int(text)
    else:
        return text[:colon], int(text[colon+1:])


def _format_time(timespan, precision=3):
    """Formats the timespan in a human readable form"""

    if timespan >= 60.0:
        # we have more than a minute, format that in a human readable form
        # Idea from http://snipplr.com/view/5713/
        parts = [("d", 60 * 60 * 24), ("h", 60 * 60), ("min", 60), ("s", 1)]
        time = []
        leftover = timespan
        for suffix, length in parts:
            value = int(leftover / length)
            if value > 0:
                leftover = leftover % length
                time.append("%s%s" % (str(value), suffix))
            if leftover < 1:
                break
        return " ".join(time)

    # Unfortunately characters outside of range(128) can cause problems in
    # certain terminals.
    # See bug: https://bugs.launchpad.net/ipython/+bug/348466
    # Try to prevent crashes by being more secure than it needs to
    # E.g. eclipse is able to print a µ, but has no sys.stdout.encoding set.
    units = ["s", "ms", "us", "ns"]  # the safe value
    if hasattr(sys.stdout, "encoding") and sys.stdout.encoding:
        try:
            "μ".encode(sys.stdout.encoding)
            units = ["s", "ms", "μs", "ns"]
        except:
            pass
    scaling = [1, 1e3, 1e6, 1e9]

    if timespan > 0.0:
        order = min(-int(math.floor(math.log10(timespan)) // 3), 3)
    else:
        order = 3
    return "%.*g %s" % (precision, timespan * scaling[order], units[order])

# === NexusCore/openenv\Lib\site-packages\numpy\polynomial\laguerre.py ===
"""
==================================================
Laguerre Series (:mod:`numpy.polynomial.laguerre`)
==================================================

This module provides a number of objects (mostly functions) useful for
dealing with Laguerre series, including a `Laguerre` class that
encapsulates the usual arithmetic operations.  (General information
on how this module represents and works with such polynomials is in the
docstring for its "parent" sub-package, `numpy.polynomial`).

Classes
-------
.. autosummary::
   :toctree: generated/

   Laguerre

Constants
---------
.. autosummary::
   :toctree: generated/

   lagdomain
   lagzero
   lagone
   lagx

Arithmetic
----------
.. autosummary::
   :toctree: generated/

   lagadd
   lagsub
   lagmulx
   lagmul
   lagdiv
   lagpow
   lagval
   lagval2d
   lagval3d
   laggrid2d
   laggrid3d

Calculus
--------
.. autosummary::
   :toctree: generated/

   lagder
   lagint

Misc Functions
--------------
.. autosummary::
   :toctree: generated/

   lagfromroots
   lagroots
   lagvander
   lagvander2d
   lagvander3d
   laggauss
   lagweight
   lagcompanion
   lagfit
   lagtrim
   lagline
   lag2poly
   poly2lag

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
    'lagzero', 'lagone', 'lagx', 'lagdomain', 'lagline', 'lagadd',
    'lagsub', 'lagmulx', 'lagmul', 'lagdiv', 'lagpow', 'lagval', 'lagder',
    'lagint', 'lag2poly', 'poly2lag', 'lagfromroots', 'lagvander',
    'lagfit', 'lagtrim', 'lagroots', 'Laguerre', 'lagval2d', 'lagval3d',
    'laggrid2d', 'laggrid3d', 'lagvander2d', 'lagvander3d', 'lagcompanion',
    'laggauss', 'lagweight']

lagtrim = pu.trimcoef


def poly2lag(pol):
    """
    poly2lag(pol)

    Convert a polynomial to a Laguerre series.

    Convert an array representing the coefficients of a polynomial (relative
    to the "standard" basis) ordered from lowest degree to highest, to an
    array of the coefficients of the equivalent Laguerre series, ordered
    from lowest to highest degree.

    Parameters
    ----------
    pol : array_like
        1-D array containing the polynomial coefficients

    Returns
    -------
    c : ndarray
        1-D array containing the coefficients of the equivalent Laguerre
        series.

    See Also
    --------
    lag2poly

    Notes
    -----
    The easy way to do conversions between polynomial basis sets
    is to use the convert method of a class instance.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial.laguerre import poly2lag
    >>> poly2lag(np.arange(4))
    array([ 23., -63.,  58., -18.])

    """
    [pol] = pu.as_series([pol])
    res = 0
    for p in pol[::-1]:
        res = lagadd(lagmulx(res), p)
    return res


def lag2poly(c):
    """
    Convert a Laguerre series to a polynomial.

    Convert an array representing the coefficients of a Laguerre series,
    ordered from lowest degree to highest, to an array of the coefficients
    of the equivalent polynomial (relative to the "standard" basis) ordered
    from lowest to highest degree.

    Parameters
    ----------
    c : array_like
        1-D array containing the Laguerre series coefficients, ordered
        from lowest order term to highest.

    Returns
    -------
    pol : ndarray
        1-D array containing the coefficients of the equivalent polynomial
        (relative to the "standard" basis) ordered from lowest order term
        to highest.

    See Also
    --------
    poly2lag

    Notes
    -----
    The easy way to do conversions between polynomial basis sets
    is to use the convert method of a class instance.

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lag2poly
    >>> lag2poly([ 23., -63.,  58., -18.])
    array([0., 1., 2., 3.])

    """
    from .polynomial import polyadd, polymulx, polysub

    [c] = pu.as_series([c])
    n = len(c)
    if n == 1:
        return c
    else:
        c0 = c[-2]
        c1 = c[-1]
        # i is the current degree of c1
        for i in range(n - 1, 1, -1):
            tmp = c0
            c0 = polysub(c[i - 2], (c1 * (i - 1)) / i)
            c1 = polyadd(tmp, polysub((2 * i - 1) * c1, polymulx(c1)) / i)
        return polyadd(c0, polysub(c1, polymulx(c1)))


#
# These are constant arrays are of integer type so as to be compatible
# with the widest range of other types, such as Decimal.
#

# Laguerre
lagdomain = np.array([0., 1.])

# Laguerre coefficients representing zero.
lagzero = np.array([0])

# Laguerre coefficients representing one.
lagone = np.array([1])

# Laguerre coefficients representing the identity x.
lagx = np.array([1, -1])


def lagline(off, scl):
    """
    Laguerre series whose graph is a straight line.

    Parameters
    ----------
    off, scl : scalars
        The specified line is given by ``off + scl*x``.

    Returns
    -------
    y : ndarray
        This module's representation of the Laguerre series for
        ``off + scl*x``.

    See Also
    --------
    numpy.polynomial.polynomial.polyline
    numpy.polynomial.chebyshev.chebline
    numpy.polynomial.legendre.legline
    numpy.polynomial.hermite.hermline
    numpy.polynomial.hermite_e.hermeline

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagline, lagval
    >>> lagval(0,lagline(3, 2))
    3.0
    >>> lagval(1,lagline(3, 2))
    5.0

    """
    if scl != 0:
        return np.array([off + scl, -scl])
    else:
        return np.array([off])


def lagfromroots(roots):
    """
    Generate a Laguerre series with given roots.

    The function returns the coefficients of the polynomial

    .. math:: p(x) = (x - r_0) * (x - r_1) * ... * (x - r_n),

    in Laguerre form, where the :math:`r_n` are the roots specified in `roots`.
    If a zero has multiplicity n, then it must appear in `roots` n times.
    For instance, if 2 is a root of multiplicity three and 3 is a root of
    multiplicity 2, then `roots` looks something like [2, 2, 2, 3, 3]. The
    roots can appear in any order.

    If the returned coefficients are `c`, then

    .. math:: p(x) = c_0 + c_1 * L_1(x) + ... +  c_n * L_n(x)

    The coefficient of the last term is not generally 1 for monic
    polynomials in Laguerre form.

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
    numpy.polynomial.chebyshev.chebfromroots
    numpy.polynomial.hermite.hermfromroots
    numpy.polynomial.hermite_e.hermefromroots

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagfromroots, lagval
    >>> coef = lagfromroots((-1, 0, 1))
    >>> lagval((-1, 0, 1), coef)
    array([0.,  0.,  0.])
    >>> coef = lagfromroots((-1j, 1j))
    >>> lagval((-1j, 1j), coef)
    array([0.+0.j, 0.+0.j])

    """
    return pu._fromroots(lagline, lagmul, roots)


def lagadd(c1, c2):
    """
    Add one Laguerre series to another.

    Returns the sum of two Laguerre series `c1` + `c2`.  The arguments
    are sequences of coefficients ordered from lowest order term to
    highest, i.e., [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Laguerre series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Array representing the Laguerre series of their sum.

    See Also
    --------
    lagsub, lagmulx, lagmul, lagdiv, lagpow

    Notes
    -----
    Unlike multiplication, division, etc., the sum of two Laguerre series
    is a Laguerre series (without having to "reproject" the result onto
    the basis set) so addition, just like that of "standard" polynomials,
    is simply "component-wise."

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagadd
    >>> lagadd([1, 2, 3], [1, 2, 3, 4])
    array([2.,  4.,  6.,  4.])

    """
    return pu._add(c1, c2)


def lagsub(c1, c2):
    """
    Subtract one Laguerre series from another.

    Returns the difference of two Laguerre series `c1` - `c2`.  The
    sequences of coefficients are from lowest order term to highest, i.e.,
    [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Laguerre series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Of Laguerre series coefficients representing their difference.

    See Also
    --------
    lagadd, lagmulx, lagmul, lagdiv, lagpow

    Notes
    -----
    Unlike multiplication, division, etc., the difference of two Laguerre
    series is a Laguerre series (without having to "reproject" the result
    onto the basis set) so subtraction, just like that of "standard"
    polynomials, is simply "component-wise."

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagsub
    >>> lagsub([1, 2, 3, 4], [1, 2, 3])
    array([0.,  0.,  0.,  4.])

    """
    return pu._sub(c1, c2)


def lagmulx(c):
    """Multiply a Laguerre series by x.

    Multiply the Laguerre series `c` by x, where x is the independent
    variable.


    Parameters
    ----------
    c : array_like
        1-D array of Laguerre series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Array representing the result of the multiplication.

    See Also
    --------
    lagadd, lagsub, lagmul, lagdiv, lagpow

    Notes
    -----
    The multiplication uses the recursion relationship for Laguerre
    polynomials in the form

    .. math::

        xP_i(x) = (-(i + 1)*P_{i + 1}(x) + (2i + 1)P_{i}(x) - iP_{i - 1}(x))

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagmulx
    >>> lagmulx([1, 2, 3])
    array([-1.,  -1.,  11.,  -9.])

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    # The zero series needs special treatment
    if len(c) == 1 and c[0] == 0:
        return c

    prd = np.empty(len(c) + 1, dtype=c.dtype)
    prd[0] = c[0]
    prd[1] = -c[0]
    for i in range(1, len(c)):
        prd[i + 1] = -c[i] * (i + 1)
        prd[i] += c[i] * (2 * i + 1)
        prd[i - 1] -= c[i] * i
    return prd


def lagmul(c1, c2):
    """
    Multiply one Laguerre series by another.

    Returns the product of two Laguerre series `c1` * `c2`.  The arguments
    are sequences of coefficients, from lowest order "term" to highest,
    e.g., [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Laguerre series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Of Laguerre series coefficients representing their product.

    See Also
    --------
    lagadd, lagsub, lagmulx, lagdiv, lagpow

    Notes
    -----
    In general, the (polynomial) product of two C-series results in terms
    that are not in the Laguerre polynomial basis set.  Thus, to express
    the product as a Laguerre series, it is necessary to "reproject" the
    product onto said basis set, which may produce "unintuitive" (but
    correct) results; see Examples section below.

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagmul
    >>> lagmul([1, 2, 3], [0, 1, 2])
    array([  8., -13.,  38., -51.,  36.])

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
            c0 = lagsub(c[-i] * xs, (c1 * (nd - 1)) / nd)
            c1 = lagadd(tmp, lagsub((2 * nd - 1) * c1, lagmulx(c1)) / nd)
    return lagadd(c0, lagsub(c1, lagmulx(c1)))


def lagdiv(c1, c2):
    """
    Divide one Laguerre series by another.

    Returns the quotient-with-remainder of two Laguerre series
    `c1` / `c2`.  The arguments are sequences of coefficients from lowest
    order "term" to highest, e.g., [1,2,3] represents the series
    ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Laguerre series coefficients ordered from low to
        high.

    Returns
    -------
    [quo, rem] : ndarrays
        Of Laguerre series coefficients representing the quotient and
        remainder.

    See Also
    --------
    lagadd, lagsub, lagmulx, lagmul, lagpow

    Notes
    -----
    In general, the (polynomial) division of one Laguerre series by another
    results in quotient and remainder terms that are not in the Laguerre
    polynomial basis set.  Thus, to express these results as a Laguerre
    series, it is necessary to "reproject" the results onto the Laguerre
    basis set, which may produce "unintuitive" (but correct) results; see
    Examples section below.

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagdiv
    >>> lagdiv([  8., -13.,  38., -51.,  36.], [0, 1, 2])
    (array([1., 2., 3.]), array([0.]))
    >>> lagdiv([  9., -12.,  38., -51.,  36.], [0, 1, 2])
    (array([1., 2., 3.]), array([1., 1.]))

    """
    return pu._div(lagmul, c1, c2)


def lagpow(c, pow, maxpower=16):
    """Raise a Laguerre series to a power.

    Returns the Laguerre series `c` raised to the power `pow`. The
    argument `c` is a sequence of coefficients ordered from low to high.
    i.e., [1,2,3] is the series  ``P_0 + 2*P_1 + 3*P_2.``

    Parameters
    ----------
    c : array_like
        1-D array of Laguerre series coefficients ordered from low to
        high.
    pow : integer
        Power to which the series will be raised
    maxpower : integer, optional
        Maximum power allowed. This is mainly to limit growth of the series
        to unmanageable size. Default is 16

    Returns
    -------
    coef : ndarray
        Laguerre series of power.

    See Also
    --------
    lagadd, lagsub, lagmulx, lagmul, lagdiv

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagpow
    >>> lagpow([1, 2, 3], 2)
    array([ 14., -16.,  56., -72.,  54.])

    """
    return pu._pow(lagmul, c, pow, maxpower)


def lagder(c, m=1, scl=1, axis=0):
    """
    Differentiate a Laguerre series.

    Returns the Laguerre series coefficients `c` differentiated `m` times
    along `axis`.  At each iteration the result is multiplied by `scl` (the
    scaling factor is for use in a linear change of variable). The argument
    `c` is an array of coefficients from low to high degree along each
    axis, e.g., [1,2,3] represents the series ``1*L_0 + 2*L_1 + 3*L_2``
    while [[1,2],[1,2]] represents ``1*L_0(x)*L_0(y) + 1*L_1(x)*L_0(y) +
    2*L_0(x)*L_1(y) + 2*L_1(x)*L_1(y)`` if axis=0 is ``x`` and axis=1 is
    ``y``.

    Parameters
    ----------
    c : array_like
        Array of Laguerre series coefficients. If `c` is multidimensional
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
        Laguerre series of the derivative.

    See Also
    --------
    lagint

    Notes
    -----
    In general, the result of differentiating a Laguerre series does not
    resemble the same operation on a power series. Thus the result of this
    function may be "unintuitive," albeit correct; see Examples section
    below.

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagder
    >>> lagder([ 1.,  1.,  1., -3.])
    array([1.,  2.,  3.])
    >>> lagder([ 1.,  0.,  0., -4.,  3.], m=2)
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
        c = c[:1] * 0
    else:
        for i in range(cnt):
            n = n - 1
            c *= scl
            der = np.empty((n,) + c.shape[1:], dtype=c.dtype)
            for j in range(n, 1, -1):
                der[j - 1] = -c[j]
                c[j - 1] += c[j]
            der[0] = -c[1]
            c = der
    c = np.moveaxis(c, 0, iaxis)
    return c


def lagint(c, m=1, k=[], lbnd=0, scl=1, axis=0):
    """
    Integrate a Laguerre series.

    Returns the Laguerre series coefficients `c` integrated `m` times from
    `lbnd` along `axis`. At each iteration the resulting series is
    **multiplied** by `scl` and an integration constant, `k`, is added.
    The scaling factor is for use in a linear change of variable.  ("Buyer
    beware": note that, depending on what one is doing, one may want `scl`
    to be the reciprocal of what one might expect; for more information,
    see the Notes section below.)  The argument `c` is an array of
    coefficients from low to high degree along each axis, e.g., [1,2,3]
    represents the series ``L_0 + 2*L_1 + 3*L_2`` while [[1,2],[1,2]]
    represents ``1*L_0(x)*L_0(y) + 1*L_1(x)*L_0(y) + 2*L_0(x)*L_1(y) +
    2*L_1(x)*L_1(y)`` if axis=0 is ``x`` and axis=1 is ``y``.


    Parameters
    ----------
    c : array_like
        Array of Laguerre series coefficients. If `c` is multidimensional
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
        Laguerre series coefficients of the integral.

    Raises
    ------
    ValueError
        If ``m < 0``, ``len(k) > m``, ``np.ndim(lbnd) != 0``, or
        ``np.ndim(scl) != 0``.

    See Also
    --------
    lagder

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
    >>> from numpy.polynomial.laguerre import lagint
    >>> lagint([1,2,3])
    array([ 1.,  1.,  1., -3.])
    >>> lagint([1,2,3], m=2)
    array([ 1.,  0.,  0., -4.,  3.])
    >>> lagint([1,2,3], k=1)
    array([ 2.,  1.,  1., -3.])
    >>> lagint([1,2,3], lbnd=-1)
    array([11.5,  1. ,  1. , -3. ])
    >>> lagint([1,2], m=2, k=[1,2], lbnd=-1)
    array([ 11.16666667,  -5.        ,  -3.        ,   2.        ]) # may vary

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
            tmp[0] = c[0]
            tmp[1] = -c[0]
            for j in range(1, n):
                tmp[j] += c[j]
                tmp[j + 1] = -c[j]
            tmp[0] += k[i] - lagval(lbnd, tmp)
            c = tmp
    c = np.moveaxis(c, 0, iaxis)
    return c


def lagval(x, c, tensor=True):
    """
    Evaluate a Laguerre series at points x.

    If `c` is of length ``n + 1``, this function returns the value:

    .. math:: p(x) = c_0 * L_0(x) + c_1 * L_1(x) + ... + c_n * L_n(x)

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
        themselves and with the elements of `c`.
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
    lagval2d, laggrid2d, lagval3d, laggrid3d

    Notes
    -----
    The evaluation uses Clenshaw recursion, aka synthetic division.

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagval
    >>> coef = [1, 2, 3]
    >>> lagval(1, coef)
    -0.5
    >>> lagval([[1, 2],[3, 4]], coef)
    array([[-0.5, -4. ],
           [-4.5, -2. ]])

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
            c0 = c[-i] - (c1 * (nd - 1)) / nd
            c1 = tmp + (c1 * ((2 * nd - 1) - x)) / nd
    return c0 + c1 * (1 - x)


def lagval2d(x, y, c):
    """
    Evaluate a 2-D Laguerre series at points (x, y).

    This function returns the values:

    .. math:: p(x,y) = \\sum_{i,j} c_{i,j} * L_i(x) * L_j(y)

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
    lagval, laggrid2d, lagval3d, laggrid3d

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagval2d
    >>> c = [[1, 2],[3, 4]]
    >>> lagval2d(1, 1, c)
    1.0
    """
    return pu._valnd(lagval, c, x, y)


def laggrid2d(x, y, c):
    """
    Evaluate a 2-D Laguerre series on the Cartesian product of x and y.

    This function returns the values:

    .. math:: p(a,b) = \\sum_{i,j} c_{i,j} * L_i(a) * L_j(b)

    where the points ``(a, b)`` consist of all pairs formed by taking
    `a` from `x` and `b` from `y`. The resulting points form a grid with
    `x` in the first dimension and `y` in the second.

    The parameters `x` and `y` are converted to arrays only if they are
    tuples or a lists, otherwise they are treated as a scalars. In either
    case, either `x` and `y` or their elements must support multiplication
    and addition both with themselves and with the elements of `c`.

    If `c` has fewer than two dimensions, ones are implicitly appended to
    its shape to make it 2-D. The shape of the result will be c.shape[2:] +
    x.shape + y.shape.

    Parameters
    ----------
    x, y : array_like, compatible objects
        The two dimensional series is evaluated at the points in the
        Cartesian product of `x` and `y`.  If `x` or `y` is a list or
        tuple, it is first converted to an ndarray, otherwise it is left
        unchanged and, if it isn't an ndarray, it is treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficient of the term of
        multi-degree i,j is contained in ``c[i,j]``. If `c` has dimension
        greater than two the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional Chebyshev series at points in the
        Cartesian product of `x` and `y`.

    See Also
    --------
    lagval, lagval2d, lagval3d, laggrid3d

    Examples
    --------
    >>> from numpy.polynomial.laguerre import laggrid2d
    >>> c = [[1, 2], [3, 4]]
    >>> laggrid2d([0, 1], [0, 1], c)
    array([[10.,  4.],
           [ 3.,  1.]])

    """
    return pu._gridnd(lagval, c, x, y)


def lagval3d(x, y, z, c):
    """
    Evaluate a 3-D Laguerre series at points (x, y, z).

    This function returns the values:

    .. math:: p(x,y,z) = \\sum_{i,j,k} c_{i,j,k} * L_i(x) * L_j(y) * L_k(z)

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
        ``(x, y, z)``, where `x`, `y`, and `z` must have the same shape.  If
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
    lagval, lagval2d, laggrid2d, laggrid3d

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagval3d
    >>> c = [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]
    >>> lagval3d(1, 1, 2, c)
    -1.0

    """
    return pu._valnd(lagval, c, x, y, z)


def laggrid3d(x, y, z, c):
    """
    Evaluate a 3-D Laguerre series on the Cartesian product of x, y, and z.

    This function returns the values:

    .. math:: p(a,b,c) = \\sum_{i,j,k} c_{i,j,k} * L_i(a) * L_j(b) * L_k(c)

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
    lagval, lagval2d, laggrid2d, lagval3d

    Examples
    --------
    >>> from numpy.polynomial.laguerre import laggrid3d
    >>> c = [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]
    >>> laggrid3d([0, 1], [0, 1], [2, 4], c)
    array([[[ -4., -44.],
            [ -2., -18.]],
           [[ -2., -14.],
            [ -1.,  -5.]]])

    """
    return pu._gridnd(lagval, c, x, y, z)


def lagvander(x, deg):
    """Pseudo-Vandermonde matrix of given degree.

    Returns the pseudo-Vandermonde matrix of degree `deg` and sample points
    `x`. The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., i] = L_i(x)

    where ``0 <= i <= deg``. The leading indices of `V` index the elements of
    `x` and the last index is the degree of the Laguerre polynomial.

    If `c` is a 1-D array of coefficients of length ``n + 1`` and `V` is the
    array ``V = lagvander(x, n)``, then ``np.dot(V, c)`` and
    ``lagval(x, c)`` are the same up to roundoff. This equivalence is
    useful both for least squares fitting and for the evaluation of a large
    number of Laguerre series of the same degree and sample points.

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
        corresponding Laguerre polynomial.  The dtype will be the same as
        the converted `x`.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial.laguerre import lagvander
    >>> x = np.array([0, 1, 2])
    >>> lagvander(x, 3)
    array([[ 1.        ,  1.        ,  1.        ,  1.        ],
           [ 1.        ,  0.        , -0.5       , -0.66666667],
           [ 1.        , -1.        , -1.        , -0.33333333]])

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
        v[1] = 1 - x
        for i in range(2, ideg + 1):
            v[i] = (v[i - 1] * (2 * i - 1 - x) - v[i - 2] * (i - 1)) / i
    return np.moveaxis(v, 0, -1)


def lagvander2d(x, y, deg):
    """Pseudo-Vandermonde matrix of given degrees.

    Returns the pseudo-Vandermonde matrix of degrees `deg` and sample
    points ``(x, y)``. The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., (deg[1] + 1)*i + j] = L_i(x) * L_j(y),

    where ``0 <= i <= deg[0]`` and ``0 <= j <= deg[1]``. The leading indices of
    `V` index the points ``(x, y)`` and the last index encodes the degrees of
    the Laguerre polynomials.

    If ``V = lagvander2d(x, y, [xdeg, ydeg])``, then the columns of `V`
    correspond to the elements of a 2-D coefficient array `c` of shape
    (xdeg + 1, ydeg + 1) in the order

    .. math:: c_{00}, c_{01}, c_{02} ... , c_{10}, c_{11}, c_{12} ...

    and ``np.dot(V, c.flat)`` and ``lagval2d(x, y, c)`` will be the same
    up to roundoff. This equivalence is useful both for least squares
    fitting and for the evaluation of a large number of 2-D Laguerre
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
    lagvander, lagvander3d, lagval2d, lagval3d

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial.laguerre import lagvander2d
    >>> x = np.array([0])
    >>> y = np.array([2])
    >>> lagvander2d(x, y, [2, 1])
    array([[ 1., -1.,  1., -1.,  1., -1.]])

    """
    return pu._vander_nd_flat((lagvander, lagvander), (x, y), deg)


def lagvander3d(x, y, z, deg):
    """Pseudo-Vandermonde matrix of given degrees.

    Returns the pseudo-Vandermonde matrix of degrees `deg` and sample
    points ``(x, y, z)``. If `l`, `m`, `n` are the given degrees in `x`, `y`, `z`,
    then The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., (m+1)(n+1)i + (n+1)j + k] = L_i(x)*L_j(y)*L_k(z),

    where ``0 <= i <= l``, ``0 <= j <= m``, and ``0 <= j <= n``.  The leading
    indices of `V` index the points ``(x, y, z)`` and the last index encodes
    the degrees of the Laguerre polynomials.

    If ``V = lagvander3d(x, y, z, [xdeg, ydeg, zdeg])``, then the columns
    of `V` correspond to the elements of a 3-D coefficient array `c` of
    shape (xdeg + 1, ydeg + 1, zdeg + 1) in the order

    .. math:: c_{000}, c_{001}, c_{002},... , c_{010}, c_{011}, c_{012},...

    and  ``np.dot(V, c.flat)`` and ``lagval3d(x, y, z, c)`` will be the
    same up to roundoff. This equivalence is useful both for least squares
    fitting and for the evaluation of a large number of 3-D Laguerre
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
    lagvander, lagvander3d, lagval2d, lagval3d

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial.laguerre import lagvander3d
    >>> x = np.array([0])
    >>> y = np.array([2])
    >>> z = np.array([0])
    >>> lagvander3d(x, y, z, [2, 1, 3])
    array([[ 1.,  1.,  1.,  1., -1., -1., -1., -1.,  1.,  1.,  1.,  1., -1.,
            -1., -1., -1.,  1.,  1.,  1.,  1., -1., -1., -1., -1.]])

    """
    return pu._vander_nd_flat((lagvander, lagvander, lagvander), (x, y, z), deg)


def lagfit(x, y, deg, rcond=None, full=False, w=None):
    """
    Least squares fit of Laguerre series to data.

    Return the coefficients of a Laguerre series of degree `deg` that is the
    least squares fit to the data values `y` given at points `x`. If `y` is
    1-D the returned coefficients will also be 1-D. If `y` is 2-D multiple
    fits are done, one for each column of `y`, and the resulting
    coefficients are stored in the corresponding columns of a 2-D return.
    The fitted polynomial(s) are in the form

    .. math::  p(x) = c_0 + c_1 * L_1(x) + ... + c_n * L_n(x),

    where ``n`` is `deg`.

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
        Laguerre coefficients ordered from low to high. If `y` was 2-D,
        the coefficients for the data in column *k*  of `y` are in column
        *k*.

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
        deficient. The warning is only raised if ``full == False``.  The
        warnings can be turned off by

        >>> import warnings
        >>> warnings.simplefilter('ignore', np.exceptions.RankWarning)

    See Also
    --------
    numpy.polynomial.polynomial.polyfit
    numpy.polynomial.legendre.legfit
    numpy.polynomial.chebyshev.chebfit
    numpy.polynomial.hermite.hermfit
    numpy.polynomial.hermite_e.hermefit
    lagval : Evaluates a Laguerre series.
    lagvander : pseudo Vandermonde matrix of Laguerre series.
    lagweight : Laguerre weight function.
    numpy.linalg.lstsq : Computes a least-squares fit from the matrix.
    scipy.interpolate.UnivariateSpline : Computes spline fits.

    Notes
    -----
    The solution is the coefficients of the Laguerre series ``p`` that
    minimizes the sum of the weighted squared errors

    .. math:: E = \\sum_j w_j^2 * |y_j - p(x_j)|^2,

    where the :math:`w_j` are the weights. This problem is solved by
    setting up as the (typically) overdetermined matrix equation

    .. math:: V(x) * c = w * y,

    where ``V`` is the weighted pseudo Vandermonde matrix of `x`, ``c`` are the
    coefficients to be solved for, `w` are the weights, and `y` are the
    observed values.  This equation is then solved using the singular value
    decomposition of ``V``.

    If some of the singular values of `V` are so small that they are
    neglected, then a `~exceptions.RankWarning` will be issued. This means that
    the coefficient values may be poorly determined. Using a lower order fit
    will usually get rid of the warning.  The `rcond` parameter can also be
    set to a value smaller than its default, but the resulting fit may be
    spurious and have large contributions from roundoff error.

    Fits using Laguerre series are probably most useful when the data can
    be approximated by ``sqrt(w(x)) * p(x)``, where ``w(x)`` is the Laguerre
    weight. In that case the weight ``sqrt(w(x[i]))`` should be used
    together with data values ``y[i]/sqrt(w(x[i]))``. The weight function is
    available as `lagweight`.

    References
    ----------
    .. [1] Wikipedia, "Curve fitting",
           https://en.wikipedia.org/wiki/Curve_fitting

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.polynomial.laguerre import lagfit, lagval
    >>> x = np.linspace(0, 10)
    >>> rng = np.random.default_rng()
    >>> err = rng.normal(scale=1./10, size=len(x))
    >>> y = lagval(x, [1, 2, 3]) + err
    >>> lagfit(x, y, 2)
    array([1.00578369, 1.99417356, 2.99827656]) # may vary

    """
    return pu._fit(lagvander, x, y, deg, rcond, full, w)


def lagcompanion(c):
    """
    Return the companion matrix of c.

    The usual companion matrix of the Laguerre polynomials is already
    symmetric when `c` is a basis Laguerre polynomial, so no scaling is
    applied.

    Parameters
    ----------
    c : array_like
        1-D array of Laguerre series coefficients ordered from low to high
        degree.

    Returns
    -------
    mat : ndarray
        Companion matrix of dimensions (deg, deg).

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagcompanion
    >>> lagcompanion([1, 2, 3])
    array([[ 1.        , -0.33333333],
           [-1.        ,  4.33333333]])

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    if len(c) < 2:
        raise ValueError('Series must have maximum degree of at least 1.')
    if len(c) == 2:
        return np.array([[1 + c[0] / c[1]]])

    n = len(c) - 1
    mat = np.zeros((n, n), dtype=c.dtype)
    top = mat.reshape(-1)[1::n + 1]
    mid = mat.reshape(-1)[0::n + 1]
    bot = mat.reshape(-1)[n::n + 1]
    top[...] = -np.arange(1, n)
    mid[...] = 2. * np.arange(n) + 1.
    bot[...] = top
    mat[:, -1] += (c[:-1] / c[-1]) * n
    return mat


def lagroots(c):
    """
    Compute the roots of a Laguerre series.

    Return the roots (a.k.a. "zeros") of the polynomial

    .. math:: p(x) = \\sum_i c[i] * L_i(x).

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
    numpy.polynomial.chebyshev.chebroots
    numpy.polynomial.hermite.hermroots
    numpy.polynomial.hermite_e.hermeroots

    Notes
    -----
    The root estimates are obtained as the eigenvalues of the companion
    matrix, Roots far from the origin of the complex plane may have large
    errors due to the numerical instability of the series for such
    values. Roots with multiplicity greater than 1 will also show larger
    errors as the value of the series near such points is relatively
    insensitive to errors in the roots. Isolated roots near the origin can
    be improved by a few iterations of Newton's method.

    The Laguerre series basis polynomials aren't powers of `x` so the
    results of this function may seem unintuitive.

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagroots, lagfromroots
    >>> coef = lagfromroots([0, 1, 2])
    >>> coef
    array([  2.,  -8.,  12.,  -6.])
    >>> lagroots(coef)
    array([-4.4408921e-16,  1.0000000e+00,  2.0000000e+00])

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    if len(c) <= 1:
        return np.array([], dtype=c.dtype)
    if len(c) == 2:
        return np.array([1 + c[0] / c[1]])

    # rotated companion matrix reduces error
    m = lagcompanion(c)[::-1, ::-1]
    r = la.eigvals(m)
    r.sort()
    return r


def laggauss(deg):
    """
    Gauss-Laguerre quadrature.

    Computes the sample points and weights for Gauss-Laguerre quadrature.
    These sample points and weights will correctly integrate polynomials of
    degree :math:`2*deg - 1` or less over the interval :math:`[0, \\inf]`
    with the weight function :math:`f(x) = \\exp(-x)`.

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
    The results have only been tested up to degree 100 higher degrees may
    be problematic. The weights are determined by using the fact that

    .. math:: w_k = c / (L'_n(x_k) * L_{n-1}(x_k))

    where :math:`c` is a constant independent of :math:`k` and :math:`x_k`
    is the k'th root of :math:`L_n`, and then scaling the results to get
    the right value when integrating 1.

    Examples
    --------
    >>> from numpy.polynomial.laguerre import laggauss
    >>> laggauss(2)
    (array([0.58578644, 3.41421356]), array([0.85355339, 0.14644661]))

    """
    ideg = pu._as_int(deg, "deg")
    if ideg <= 0:
        raise ValueError("deg must be a positive integer")

    # first approximation of roots. We use the fact that the companion
    # matrix is symmetric in this case in order to obtain better zeros.
    c = np.array([0] * deg + [1])
    m = lagcompanion(c)
    x = la.eigvalsh(m)

    # improve roots by one application of Newton
    dy = lagval(x, c)
    df = lagval(x, lagder(c))
    x -= dy / df

    # compute the weights. We scale the factor to avoid possible numerical
    # overflow.
    fm = lagval(x, c[1:])
    fm /= np.abs(fm).max()
    df /= np.abs(df).max()
    w = 1 / (fm * df)

    # scale w to get the right value, 1 in this case
    w /= w.sum()

    return x, w


def lagweight(x):
    """Weight function of the Laguerre polynomials.

    The weight function is :math:`exp(-x)` and the interval of integration
    is :math:`[0, \\inf]`. The Laguerre polynomials are orthogonal, but not
    normalized, with respect to this weight function.

    Parameters
    ----------
    x : array_like
       Values at which the weight function will be computed.

    Returns
    -------
    w : ndarray
       The weight function at `x`.

    Examples
    --------
    >>> from numpy.polynomial.laguerre import lagweight
    >>> x = np.array([0, 1, 2])
    >>> lagweight(x)
    array([1.        , 0.36787944, 0.13533528])

    """
    w = np.exp(-x)
    return w

#
# Laguerre series class
#

class Laguerre(ABCPolyBase):
    """A Laguerre series class.

    The Laguerre class provides the standard Python numerical methods
    '+', '-', '*', '//', '%', 'divmod', '**', and '()' as well as the
    attributes and methods listed below.

    Parameters
    ----------
    coef : array_like
        Laguerre coefficients in order of increasing degree, i.e,
        ``(1, 2, 3)`` gives ``1*L_0(x) + 2*L_1(X) + 3*L_2(x)``.
    domain : (2,) array_like, optional
        Domain to use. The interval ``[domain[0], domain[1]]`` is mapped
        to the interval ``[window[0], window[1]]`` by shifting and scaling.
        The default value is [0., 1.].
    window : (2,) array_like, optional
        Window, see `domain` for its use. The default value is [0., 1.].
    symbol : str, optional
        Symbol used to represent the independent variable in string
        representations of the polynomial expression, e.g. for printing.
        The symbol must be a valid Python identifier. Default value is 'x'.

        .. versionadded:: 1.24

    """
    # Virtual Functions
    _add = staticmethod(lagadd)
    _sub = staticmethod(lagsub)
    _mul = staticmethod(lagmul)
    _div = staticmethod(lagdiv)
    _pow = staticmethod(lagpow)
    _val = staticmethod(lagval)
    _int = staticmethod(lagint)
    _der = staticmethod(lagder)
    _fit = staticmethod(lagfit)
    _line = staticmethod(lagline)
    _roots = staticmethod(lagroots)
    _fromroots = staticmethod(lagfromroots)

    # Virtual properties
    domain = np.array(lagdomain)
    window = np.array(lagdomain)
    basis_name = 'L'