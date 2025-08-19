
# === NexusCore/tools\exports\export_20250803_114325\combined_34.py ===

# === NexusCore/openenv\Lib\site-packages\matplotlib\colors.py ===
"""
A module for converting numbers or color arguments to *RGB* or *RGBA*.

*RGB* and *RGBA* are sequences of, respectively, 3 or 4 floats in the
range 0-1.

This module includes functions and classes for color specification conversions,
and for mapping numbers to colors in a 1-D array of colors called a colormap.

Mapping data onto colors using a colormap typically involves two steps: a data
array is first mapped onto the range 0-1 using a subclass of `Normalize`,
then this number is mapped to a color using a subclass of `Colormap`.  Two
subclasses of `Colormap` provided here:  `LinearSegmentedColormap`, which uses
piecewise-linear interpolation to define colormaps, and `ListedColormap`, which
makes a colormap from a list of colors.

.. seealso::

  :ref:`colormap-manipulation` for examples of how to
  make colormaps and

  :ref:`colormaps` for a list of built-in colormaps.

  :ref:`colormapnorms` for more details about data
  normalization

  More colormaps are available at palettable_.

The module also provides functions for checking whether an object can be
interpreted as a color (`is_color_like`), for converting such an object
to an RGBA tuple (`to_rgba`) or to an HTML-like hex string in the
"#rrggbb" format (`to_hex`), and a sequence of colors to an (n, 4)
RGBA array (`to_rgba_array`).  Caching is used for efficiency.

Colors that Matplotlib recognizes are listed at
:ref:`colors_def`.

.. _palettable: https://jiffyclub.github.io/palettable/
.. _xkcd color survey: https://xkcd.com/color/rgb/
"""

import base64
from collections.abc import Sized, Sequence, Mapping
import functools
import importlib
import inspect
import io
import itertools
from numbers import Real
import re

from PIL import Image
from PIL.PngImagePlugin import PngInfo

import matplotlib as mpl
import numpy as np
from matplotlib import _api, _cm, cbook, scale, _image
from ._color_data import BASE_COLORS, TABLEAU_COLORS, CSS4_COLORS, XKCD_COLORS


class _ColorMapping(dict):
    def __init__(self, mapping):
        super().__init__(mapping)
        self.cache = {}

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.cache.clear()

    def __delitem__(self, key):
        super().__delitem__(key)
        self.cache.clear()


_colors_full_map = {}
# Set by reverse priority order.
_colors_full_map.update(XKCD_COLORS)
_colors_full_map.update({k.replace('grey', 'gray'): v
                         for k, v in XKCD_COLORS.items()
                         if 'grey' in k})
_colors_full_map.update(CSS4_COLORS)
_colors_full_map.update(TABLEAU_COLORS)
_colors_full_map.update({k.replace('gray', 'grey'): v
                         for k, v in TABLEAU_COLORS.items()
                         if 'gray' in k})
_colors_full_map.update(BASE_COLORS)
_colors_full_map = _ColorMapping(_colors_full_map)

_REPR_PNG_SIZE = (512, 64)
_BIVAR_REPR_PNG_SIZE = 256


def get_named_colors_mapping():
    """Return the global mapping of names to named colors."""
    return _colors_full_map


class ColorSequenceRegistry(Mapping):
    r"""
    Container for sequences of colors that are known to Matplotlib by name.

    The universal registry instance is `matplotlib.color_sequences`. There
    should be no need for users to instantiate `.ColorSequenceRegistry`
    themselves.

    Read access uses a dict-like interface mapping names to lists of colors::

        import matplotlib as mpl
        colors = mpl.color_sequences['tab10']

    For a list of built in color sequences, see :doc:`/gallery/color/color_sequences`.
    The returned lists are copies, so that their modification does not change
    the global definition of the color sequence.

    Additional color sequences can be added via
    `.ColorSequenceRegistry.register`::

        mpl.color_sequences.register('rgb', ['r', 'g', 'b'])
    """

    _BUILTIN_COLOR_SEQUENCES = {
        'tab10': _cm._tab10_data,
        'tab20': _cm._tab20_data,
        'tab20b': _cm._tab20b_data,
        'tab20c': _cm._tab20c_data,
        'Pastel1': _cm._Pastel1_data,
        'Pastel2': _cm._Pastel2_data,
        'Paired': _cm._Paired_data,
        'Accent': _cm._Accent_data,
        'Dark2': _cm._Dark2_data,
        'Set1': _cm._Set1_data,
        'Set2': _cm._Set2_data,
        'Set3': _cm._Set3_data,
        'petroff10': _cm._petroff10_data,
    }

    def __init__(self):
        self._color_sequences = {**self._BUILTIN_COLOR_SEQUENCES}

    def __getitem__(self, item):
        try:
            return list(self._color_sequences[item])
        except KeyError:
            raise KeyError(f"{item!r} is not a known color sequence name")

    def __iter__(self):
        return iter(self._color_sequences)

    def __len__(self):
        return len(self._color_sequences)

    def __str__(self):
        return ('ColorSequenceRegistry; available colormaps:\n' +
                ', '.join(f"'{name}'" for name in self))

    def register(self, name, color_list):
        """
        Register a new color sequence.

        The color sequence registry stores a copy of the given *color_list*, so
        that future changes to the original list do not affect the registered
        color sequence. Think of this as the registry taking a snapshot
        of *color_list* at registration.

        Parameters
        ----------
        name : str
            The name for the color sequence.

        color_list : list of :mpltype:`color`
            An iterable returning valid Matplotlib colors when iterating over.
            Note however that the returned color sequence will always be a
            list regardless of the input type.

        """
        if name in self._BUILTIN_COLOR_SEQUENCES:
            raise ValueError(f"{name!r} is a reserved name for a builtin "
                             "color sequence")

        color_list = list(color_list)  # force copy and coerce type to list
        for color in color_list:
            try:
                to_rgba(color)
            except ValueError:
                raise ValueError(
                    f"{color!r} is not a valid color specification")

        self._color_sequences[name] = color_list

    def unregister(self, name):
        """
        Remove a sequence from the registry.

        You cannot remove built-in color sequences.

        If the name is not registered, returns with no error.
        """
        if name in self._BUILTIN_COLOR_SEQUENCES:
            raise ValueError(
                f"Cannot unregister builtin color sequence {name!r}")
        self._color_sequences.pop(name, None)


_color_sequences = ColorSequenceRegistry()


def _sanitize_extrema(ex):
    if ex is None:
        return ex
    try:
        ret = ex.item()
    except AttributeError:
        ret = float(ex)
    return ret

_nth_color_re = re.compile(r"\AC[0-9]+\Z")


def _is_nth_color(c):
    """Return whether *c* can be interpreted as an item in the color cycle."""
    return isinstance(c, str) and _nth_color_re.match(c)


def is_color_like(c):
    """Return whether *c* can be interpreted as an RGB(A) color."""
    # Special-case nth color syntax because it cannot be parsed during setup.
    if _is_nth_color(c):
        return True
    try:
        to_rgba(c)
    except (TypeError, ValueError):
        return False
    else:
        return True


def _has_alpha_channel(c):
    """Return whether *c* is a color with an alpha channel."""
    # 4-element sequences are interpreted as r, g, b, a
    return not isinstance(c, str) and len(c) == 4


def _check_color_like(**kwargs):
    """
    For each *key, value* pair in *kwargs*, check that *value* is color-like.
    """
    for k, v in kwargs.items():
        if not is_color_like(v):
            raise ValueError(
                f"{v!r} is not a valid value for {k}: supported inputs are "
                f"(r, g, b) and (r, g, b, a) 0-1 float tuples; "
                f"'#rrggbb', '#rrggbbaa', '#rgb', '#rgba' strings; "
                f"named color strings; "
                f"string reprs of 0-1 floats for grayscale values; "
                f"'C0', 'C1', ... strings for colors of the color cycle; "
                f"and pairs combining one of the above with an alpha value")


def same_color(c1, c2):
    """
    Return whether the colors *c1* and *c2* are the same.

    *c1*, *c2* can be single colors or lists/arrays of colors.
    """
    c1 = to_rgba_array(c1)
    c2 = to_rgba_array(c2)
    n1 = max(c1.shape[0], 1)  # 'none' results in shape (0, 4), but is 1-elem
    n2 = max(c2.shape[0], 1)  # 'none' results in shape (0, 4), but is 1-elem

    if n1 != n2:
        raise ValueError('Different number of elements passed.')
    # The following shape test is needed to correctly handle comparisons with
    # 'none', which results in a shape (0, 4) array and thus cannot be tested
    # via value comparison.
    return c1.shape == c2.shape and (c1 == c2).all()


def to_rgba(c, alpha=None):
    """
    Convert *c* to an RGBA color.

    Parameters
    ----------
    c : Matplotlib color or ``np.ma.masked``

    alpha : float, optional
        If *alpha* is given, force the alpha value of the returned RGBA tuple
        to *alpha*.

        If None, the alpha value from *c* is used. If *c* does not have an
        alpha channel, then alpha defaults to 1.

        *alpha* is ignored for the color value ``"none"`` (case-insensitive),
        which always maps to ``(0, 0, 0, 0)``.

    Returns
    -------
    tuple
        Tuple of floats ``(r, g, b, a)``, where each channel (red, green, blue,
        alpha) can assume values between 0 and 1.
    """
    if isinstance(c, tuple) and len(c) == 2:
        if alpha is None:
            c, alpha = c
        else:
            c = c[0]
    # Special-case nth color syntax because it should not be cached.
    if _is_nth_color(c):
        prop_cycler = mpl.rcParams['axes.prop_cycle']
        colors = prop_cycler.by_key().get('color', ['k'])
        c = colors[int(c[1:]) % len(colors)]
    try:
        rgba = _colors_full_map.cache[c, alpha]
    except (KeyError, TypeError):  # Not in cache, or unhashable.
        rgba = None
    if rgba is None:  # Suppress exception chaining of cache lookup failure.
        rgba = _to_rgba_no_colorcycle(c, alpha)
        try:
            _colors_full_map.cache[c, alpha] = rgba
        except TypeError:
            pass
    return rgba


def _to_rgba_no_colorcycle(c, alpha=None):
    """
    Convert *c* to an RGBA color, with no support for color-cycle syntax.

    If *alpha* is given, force the alpha value of the returned RGBA tuple
    to *alpha*. Otherwise, the alpha value from *c* is used, if it has alpha
    information, or defaults to 1.

    *alpha* is ignored for the color value ``"none"`` (case-insensitive),
    which always maps to ``(0, 0, 0, 0)``.
    """
    if alpha is not None and not 0 <= alpha <= 1:
        raise ValueError("'alpha' must be between 0 and 1, inclusive")
    orig_c = c
    if c is np.ma.masked:
        return (0., 0., 0., 0.)
    if isinstance(c, str):
        if c.lower() == "none":
            return (0., 0., 0., 0.)
        # Named color.
        try:
            # This may turn c into a non-string, so we check again below.
            c = _colors_full_map[c]
        except KeyError:
            if len(orig_c) != 1:
                try:
                    c = _colors_full_map[c.lower()]
                except KeyError:
                    pass
    if isinstance(c, str):
        # hex color in #rrggbb format.
        match = re.match(r"\A#[a-fA-F0-9]{6}\Z", c)
        if match:
            return (tuple(int(n, 16) / 255
                          for n in [c[1:3], c[3:5], c[5:7]])
                    + (alpha if alpha is not None else 1.,))
        # hex color in #rgb format, shorthand for #rrggbb.
        match = re.match(r"\A#[a-fA-F0-9]{3}\Z", c)
        if match:
            return (tuple(int(n, 16) / 255
                          for n in [c[1]*2, c[2]*2, c[3]*2])
                    + (alpha if alpha is not None else 1.,))
        # hex color with alpha in #rrggbbaa format.
        match = re.match(r"\A#[a-fA-F0-9]{8}\Z", c)
        if match:
            color = [int(n, 16) / 255
                     for n in [c[1:3], c[3:5], c[5:7], c[7:9]]]
            if alpha is not None:
                color[-1] = alpha
            return tuple(color)
        # hex color with alpha in #rgba format, shorthand for #rrggbbaa.
        match = re.match(r"\A#[a-fA-F0-9]{4}\Z", c)
        if match:
            color = [int(n, 16) / 255
                     for n in [c[1]*2, c[2]*2, c[3]*2, c[4]*2]]
            if alpha is not None:
                color[-1] = alpha
            return tuple(color)
        # string gray.
        try:
            c = float(c)
        except ValueError:
            pass
        else:
            if not (0 <= c <= 1):
                raise ValueError(
                    f"Invalid string grayscale value {orig_c!r}. "
                    f"Value must be within 0-1 range")
            return c, c, c, alpha if alpha is not None else 1.
        raise ValueError(f"Invalid RGBA argument: {orig_c!r}")
    # turn 2-D array into 1-D array
    if isinstance(c, np.ndarray):
        if c.ndim == 2 and c.shape[0] == 1:
            c = c.reshape(-1)
    # tuple color.
    if not np.iterable(c):
        raise ValueError(f"Invalid RGBA argument: {orig_c!r}")
    if len(c) not in [3, 4]:
        raise ValueError("RGBA sequence should have length 3 or 4")
    if not all(isinstance(x, Real) for x in c):
        # Checks that don't work: `map(float, ...)`, `np.array(..., float)` and
        # `np.array(...).astype(float)` would all convert "0.5" to 0.5.
        raise ValueError(f"Invalid RGBA argument: {orig_c!r}")
    # Return a tuple to prevent the cached value from being modified.
    c = tuple(map(float, c))
    if len(c) == 3 and alpha is None:
        alpha = 1
    if alpha is not None:
        c = c[:3] + (alpha,)
    if any(elem < 0 or elem > 1 for elem in c):
        raise ValueError("RGBA values should be within 0-1 range")
    return c


def to_rgba_array(c, alpha=None):
    """
    Convert *c* to a (n, 4) array of RGBA colors.

    Parameters
    ----------
    c : Matplotlib color or array of colors
        If *c* is a masked array, an `~numpy.ndarray` is returned with a
        (0, 0, 0, 0) row for each masked value or row in *c*.

    alpha : float or sequence of floats, optional
        If *alpha* is given, force the alpha value of the returned RGBA tuple
        to *alpha*.

        If None, the alpha value from *c* is used. If *c* does not have an
        alpha channel, then alpha defaults to 1.

        *alpha* is ignored for the color value ``"none"`` (case-insensitive),
        which always maps to ``(0, 0, 0, 0)``.

        If *alpha* is a sequence and *c* is a single color, *c* will be
        repeated to match the length of *alpha*.

    Returns
    -------
    array
        (n, 4) array of RGBA colors,  where each channel (red, green, blue,
        alpha) can assume values between 0 and 1.
    """
    if isinstance(c, tuple) and len(c) == 2 and isinstance(c[1], Real):
        if alpha is None:
            c, alpha = c
        else:
            c = c[0]
    # Special-case inputs that are already arrays, for performance.  (If the
    # array has the wrong kind or shape, raise the error during one-at-a-time
    # conversion.)
    if np.iterable(alpha):
        alpha = np.asarray(alpha).ravel()
    if (isinstance(c, np.ndarray) and c.dtype.kind in "if"
            and c.ndim == 2 and c.shape[1] in [3, 4]):
        mask = c.mask.any(axis=1) if np.ma.is_masked(c) else None
        c = np.ma.getdata(c)
        if np.iterable(alpha):
            if c.shape[0] == 1 and alpha.shape[0] > 1:
                c = np.tile(c, (alpha.shape[0], 1))
            elif c.shape[0] != alpha.shape[0]:
                raise ValueError("The number of colors must match the number"
                                 " of alpha values if there are more than one"
                                 " of each.")
        if c.shape[1] == 3:
            result = np.column_stack([c, np.zeros(len(c))])
            result[:, -1] = alpha if alpha is not None else 1.
        elif c.shape[1] == 4:
            result = c.copy()
            if alpha is not None:
                result[:, -1] = alpha
        if mask is not None:
            result[mask] = 0
        if np.any((result < 0) | (result > 1)):
            raise ValueError("RGBA values should be within 0-1 range")
        return result
    # Handle single values.
    # Note that this occurs *after* handling inputs that are already arrays, as
    # `to_rgba(c, alpha)` (below) is expensive for such inputs, due to the need
    # to format the array in the ValueError message(!).
    if cbook._str_lower_equal(c, "none"):
        return np.zeros((0, 4), float)
    try:
        if np.iterable(alpha):
            return np.array([to_rgba(c, a) for a in alpha], float)
        else:
            return np.array([to_rgba(c, alpha)], float)
    except TypeError:
        pass
    except ValueError as e:
        if e.args == ("'alpha' must be between 0 and 1, inclusive", ):
            # ValueError is from _to_rgba_no_colorcycle().
            raise e
    if isinstance(c, str):
        raise ValueError(f"{c!r} is not a valid color value.")

    if len(c) == 0:
        return np.zeros((0, 4), float)

    # Quick path if the whole sequence can be directly converted to a numpy
    # array in one shot.
    if isinstance(c, Sequence):
        lens = {len(cc) if isinstance(cc, (list, tuple)) else -1 for cc in c}
        if lens == {3}:
            rgba = np.column_stack([c, np.ones(len(c))])
        elif lens == {4}:
            rgba = np.array(c)
        else:
            rgba = np.array([to_rgba(cc) for cc in c])
    else:
        rgba = np.array([to_rgba(cc) for cc in c])

    if alpha is not None:
        rgba[:, 3] = alpha
        if isinstance(c, Sequence):
            # ensure that an explicit alpha does not overwrite full transparency
            # for "none"
            none_mask = [cbook._str_equal(cc, "none") for cc in c]
            rgba[:, 3][none_mask] = 0
    return rgba


def to_rgb(c):
    """Convert *c* to an RGB color, silently dropping the alpha channel."""
    return to_rgba(c)[:3]


def to_hex(c, keep_alpha=False):
    """
    Convert *c* to a hex color.

    Parameters
    ----------
    c : :ref:`color <colors_def>` or `numpy.ma.masked`

    keep_alpha : bool, default: False
      If False, use the ``#rrggbb`` format, otherwise use ``#rrggbbaa``.

    Returns
    -------
    str
      ``#rrggbb`` or ``#rrggbbaa`` hex color string
    """
    c = to_rgba(c)
    if not keep_alpha:
        c = c[:3]
    return "#" + "".join(format(round(val * 255), "02x") for val in c)


### Backwards-compatible color-conversion API


cnames = CSS4_COLORS
hexColorPattern = re.compile(r"\A#[a-fA-F0-9]{6}\Z")
rgb2hex = to_hex
hex2color = to_rgb


class ColorConverter:
    """
    A class only kept for backwards compatibility.

    Its functionality is entirely provided by module-level functions.
    """
    colors = _colors_full_map
    cache = _colors_full_map.cache
    to_rgb = staticmethod(to_rgb)
    to_rgba = staticmethod(to_rgba)
    to_rgba_array = staticmethod(to_rgba_array)


colorConverter = ColorConverter()


### End of backwards-compatible color-conversion API


def _create_lookup_table(N, data, gamma=1.0):
    r"""
    Create an *N* -element 1D lookup table.

    This assumes a mapping :math:`f : [0, 1] \rightarrow [0, 1]`. The returned
    data is an array of N values :math:`y = f(x)` where x is sampled from
    [0, 1].

    By default (*gamma* = 1) x is equidistantly sampled from [0, 1]. The
    *gamma* correction factor :math:`\gamma` distorts this equidistant
    sampling by :math:`x \rightarrow x^\gamma`.

    Parameters
    ----------
    N : int
        The number of elements of the created lookup table; at least 1.

    data : (M, 3) array-like or callable
        Defines the mapping :math:`f`.

        If a (M, 3) array-like, the rows define values (x, y0, y1).  The x
        values must start with x=0, end with x=1, and all x values be in
        increasing order.

        A value between :math:`x_i` and :math:`x_{i+1}` is mapped to the range
        :math:`y^1_{i-1} \ldots y^0_i` by linear interpolation.

        For the simple case of a y-continuous mapping, y0 and y1 are identical.

        The two values of y are to allow for discontinuous mapping functions.
        E.g. a sawtooth with a period of 0.2 and an amplitude of 1 would be::

            [(0, 1, 0), (0.2, 1, 0), (0.4, 1, 0), ..., [(1, 1, 0)]

        In the special case of ``N == 1``, by convention the returned value
        is y0 for x == 1.

        If *data* is a callable, it must accept and return numpy arrays::

           data(x : ndarray) -> ndarray

        and map values between 0 - 1 to 0 - 1.

    gamma : float
        Gamma correction factor for input distribution x of the mapping.

        See also https://en.wikipedia.org/wiki/Gamma_correction.

    Returns
    -------
    array
        The lookup table where ``lut[x * (N-1)]`` gives the closest value
        for values of x between 0 and 1.

    Notes
    -----
    This function is internally used for `.LinearSegmentedColormap`.
    """

    if callable(data):
        xind = np.linspace(0, 1, N) ** gamma
        lut = np.clip(np.array(data(xind), dtype=float), 0, 1)
        return lut

    try:
        adata = np.array(data)
    except Exception as err:
        raise TypeError("data must be convertible to an array") from err
    _api.check_shape((None, 3), data=adata)

    x = adata[:, 0]
    y0 = adata[:, 1]
    y1 = adata[:, 2]

    if x[0] != 0. or x[-1] != 1.0:
        raise ValueError(
            "data mapping points must start with x=0 and end with x=1")
    if (np.diff(x) < 0).any():
        raise ValueError("data mapping points must have x in increasing order")
    # begin generation of lookup table
    if N == 1:
        # convention: use the y = f(x=1) value for a 1-element lookup table
        lut = np.array(y0[-1])
    else:
        x = x * (N - 1)
        xind = (N - 1) * np.linspace(0, 1, N) ** gamma
        ind = np.searchsorted(x, xind)[1:-1]

        distance = (xind[1:-1] - x[ind - 1]) / (x[ind] - x[ind - 1])
        lut = np.concatenate([
            [y1[0]],
            distance * (y0[ind] - y1[ind - 1]) + y1[ind - 1],
            [y0[-1]],
        ])
    # ensure that the lut is confined to values between 0 and 1 by clipping it
    return np.clip(lut, 0.0, 1.0)


class Colormap:
    """
    Baseclass for all scalar to RGBA mappings.

    Typically, Colormap instances are used to convert data values (floats)
    from the interval ``[0, 1]`` to the RGBA color that the respective
    Colormap represents. For scaling of data into the ``[0, 1]`` interval see
    `matplotlib.colors.Normalize`. Subclasses of `matplotlib.cm.ScalarMappable`
    make heavy use of this ``data -> normalize -> map-to-color`` processing
    chain.
    """

    def __init__(self, name, N=256):
        """
        Parameters
        ----------
        name : str
            The name of the colormap.
        N : int
            The number of RGB quantization levels.
        """
        self.name = name
        self.N = int(N)  # ensure that N is always int
        self._rgba_bad = (0.0, 0.0, 0.0, 0.0)  # If bad, don't paint anything.
        self._rgba_under = None
        self._rgba_over = None
        self._i_under = self.N
        self._i_over = self.N + 1
        self._i_bad = self.N + 2
        self._isinit = False
        self.n_variates = 1
        #: When this colormap exists on a scalar mappable and colorbar_extend
        #: is not False, colorbar creation will pick up ``colorbar_extend`` as
        #: the default value for the ``extend`` keyword in the
        #: `matplotlib.colorbar.Colorbar` constructor.
        self.colorbar_extend = False

    def __call__(self, X, alpha=None, bytes=False):
        r"""
        Parameters
        ----------
        X : float or int or array-like
            The data value(s) to convert to RGBA.
            For floats, *X* should be in the interval ``[0.0, 1.0]`` to
            return the RGBA values ``X*100`` percent along the Colormap line.
            For integers, *X* should be in the interval ``[0, Colormap.N)`` to
            return RGBA values *indexed* from the Colormap with index ``X``.
        alpha : float or array-like or None
            Alpha must be a scalar between 0 and 1, a sequence of such
            floats with shape matching X, or None.
        bytes : bool, default: False
            If False (default), the returned RGBA values will be floats in the
            interval ``[0, 1]`` otherwise they will be `numpy.uint8`\s in the
            interval ``[0, 255]``.

        Returns
        -------
        Tuple of RGBA values if X is scalar, otherwise an array of
        RGBA values with a shape of ``X.shape + (4, )``.
        """
        rgba, mask = self._get_rgba_and_mask(X, alpha=alpha, bytes=bytes)
        if not np.iterable(X):
            rgba = tuple(rgba)
        return rgba

    def _get_rgba_and_mask(self, X, alpha=None, bytes=False):
        r"""
        Parameters
        ----------
        X : float or int or array-like
            The data value(s) to convert to RGBA.
            For floats, *X* should be in the interval ``[0.0, 1.0]`` to
            return the RGBA values ``X*100`` percent along the Colormap line.
            For integers, *X* should be in the interval ``[0, Colormap.N)`` to
            return RGBA values *indexed* from the Colormap with index ``X``.
        alpha : float or array-like or None
            Alpha must be a scalar between 0 and 1, a sequence of such
            floats with shape matching X, or None.
        bytes : bool, default: False
            If False (default), the returned RGBA values will be floats in the
            interval ``[0, 1]`` otherwise they will be `numpy.uint8`\s in the
            interval ``[0, 255]``.

        Returns
        -------
        colors : np.ndarray
            Array of RGBA values with a shape of ``X.shape + (4, )``.
        mask : np.ndarray
            Boolean array with True where the input is ``np.nan`` or masked.
        """
        if not self._isinit:
            self._init()

        xa = np.array(X, copy=True)
        if not xa.dtype.isnative:
            # Native byteorder is faster.
            xa = xa.byteswap().view(xa.dtype.newbyteorder())
        if xa.dtype.kind == "f":
            xa *= self.N
            # xa == 1 (== N after multiplication) is not out of range.
            xa[xa == self.N] = self.N - 1
        # Pre-compute the masks before casting to int (which can truncate
        # negative values to zero or wrap large floats to negative ints).
        mask_under = xa < 0
        mask_over = xa >= self.N
        # If input was masked, get the bad mask from it; else mask out nans.
        mask_bad = X.mask if np.ma.is_masked(X) else np.isnan(xa)
        with np.errstate(invalid="ignore"):
            # We need this cast for unsigned ints as well as floats
            xa = xa.astype(int)
        xa[mask_under] = self._i_under
        xa[mask_over] = self._i_over
        xa[mask_bad] = self._i_bad

        lut = self._lut
        if bytes:
            lut = (lut * 255).astype(np.uint8)

        rgba = lut.take(xa, axis=0, mode='clip')

        if alpha is not None:
            alpha = np.clip(alpha, 0, 1)
            if bytes:
                alpha *= 255  # Will be cast to uint8 upon assignment.
            if alpha.shape not in [(), xa.shape]:
                raise ValueError(
                    f"alpha is array-like but its shape {alpha.shape} does "
                    f"not match that of X {xa.shape}")
            rgba[..., -1] = alpha
            # If the "bad" color is all zeros, then ignore alpha input.
            if (lut[-1] == 0).all():
                rgba[mask_bad] = (0, 0, 0, 0)

        return rgba, mask_bad

    def __copy__(self):
        cls = self.__class__
        cmapobject = cls.__new__(cls)
        cmapobject.__dict__.update(self.__dict__)
        if self._isinit:
            cmapobject._lut = np.copy(self._lut)
        return cmapobject

    def __eq__(self, other):
        if (not isinstance(other, Colormap) or
                self.colorbar_extend != other.colorbar_extend):
            return False
        # To compare lookup tables the Colormaps have to be initialized
        if not self._isinit:
            self._init()
        if not other._isinit:
            other._init()
        return np.array_equal(self._lut, other._lut)

    def get_bad(self):
        """Get the color for masked values."""
        if not self._isinit:
            self._init()
        return np.array(self._lut[self._i_bad])

    def set_bad(self, color='k', alpha=None):
        """Set the color for masked values."""
        self._rgba_bad = to_rgba(color, alpha)
        if self._isinit:
            self._set_extremes()

    def get_under(self):
        """Get the color for low out-of-range values."""
        if not self._isinit:
            self._init()
        return np.array(self._lut[self._i_under])

    def set_under(self, color='k', alpha=None):
        """Set the color for low out-of-range values."""
        self._rgba_under = to_rgba(color, alpha)
        if self._isinit:
            self._set_extremes()

    def get_over(self):
        """Get the color for high out-of-range values."""
        if not self._isinit:
            self._init()
        return np.array(self._lut[self._i_over])

    def set_over(self, color='k', alpha=None):
        """Set the color for high out-of-range values."""
        self._rgba_over = to_rgba(color, alpha)
        if self._isinit:
            self._set_extremes()

    def set_extremes(self, *, bad=None, under=None, over=None):
        """
        Set the colors for masked (*bad*) values and, when ``norm.clip =
        False``, low (*under*) and high (*over*) out-of-range values.
        """
        if bad is not None:
            self.set_bad(bad)
        if under is not None:
            self.set_under(under)
        if over is not None:
            self.set_over(over)

    def with_extremes(self, *, bad=None, under=None, over=None):
        """
        Return a copy of the colormap, for which the colors for masked (*bad*)
        values and, when ``norm.clip = False``, low (*under*) and high (*over*)
        out-of-range values, have been set accordingly.
        """
        new_cm = self.copy()
        new_cm.set_extremes(bad=bad, under=under, over=over)
        return new_cm

    def _set_extremes(self):
        if self._rgba_under:
            self._lut[self._i_under] = self._rgba_under
        else:
            self._lut[self._i_under] = self._lut[0]
        if self._rgba_over:
            self._lut[self._i_over] = self._rgba_over
        else:
            self._lut[self._i_over] = self._lut[self.N - 1]
        self._lut[self._i_bad] = self._rgba_bad

    def _init(self):
        """Generate the lookup table, ``self._lut``."""
        raise NotImplementedError("Abstract class only")

    def is_gray(self):
        """Return whether the colormap is grayscale."""
        if not self._isinit:
            self._init()
        return (np.all(self._lut[:, 0] == self._lut[:, 1]) and
                np.all(self._lut[:, 0] == self._lut[:, 2]))

    def resampled(self, lutsize):
        """Return a new colormap with *lutsize* entries."""
        if hasattr(self, '_resample'):
            _api.warn_external(
                "The ability to resample a color map is now public API "
                f"However the class {type(self)} still only implements "
                "the previous private _resample method.  Please update "
                "your class."
            )
            return self._resample(lutsize)

        raise NotImplementedError()

    def reversed(self, name=None):
        """
        Return a reversed instance of the Colormap.

        .. note:: This function is not implemented for the base class.

        Parameters
        ----------
        name : str, optional
            The name for the reversed colormap. If None, the
            name is set to ``self.name + "_r"``.

        See Also
        --------
        LinearSegmentedColormap.reversed
        ListedColormap.reversed
        """
        raise NotImplementedError()

    def _repr_png_(self):
        """Generate a PNG representation of the Colormap."""
        X = np.tile(np.linspace(0, 1, _REPR_PNG_SIZE[0]),
                    (_REPR_PNG_SIZE[1], 1))
        pixels = self(X, bytes=True)
        png_bytes = io.BytesIO()
        title = self.name + ' colormap'
        author = f'Matplotlib v{mpl.__version__}, https://matplotlib.org'
        pnginfo = PngInfo()
        pnginfo.add_text('Title', title)
        pnginfo.add_text('Description', title)
        pnginfo.add_text('Author', author)
        pnginfo.add_text('Software', author)
        Image.fromarray(pixels).save(png_bytes, format='png', pnginfo=pnginfo)
        return png_bytes.getvalue()

    def _repr_html_(self):
        """Generate an HTML representation of the Colormap."""
        png_bytes = self._repr_png_()
        png_base64 = base64.b64encode(png_bytes).decode('ascii')
        def color_block(color):
            hex_color = to_hex(color, keep_alpha=True)
            return (f'<div title="{hex_color}" '
                    'style="display: inline-block; '
                    'width: 1em; height: 1em; '
                    'margin: 0; '
                    'vertical-align: middle; '
                    'border: 1px solid #555; '
                    f'background-color: {hex_color};"></div>')

        return ('<div style="vertical-align: middle;">'
                f'<strong>{self.name}</strong> '
                '</div>'
                '<div class="cmap"><img '
                f'alt="{self.name} colormap" '
                f'title="{self.name}" '
                'style="border: 1px solid #555;" '
                f'src="data:image/png;base64,{png_base64}"></div>'
                '<div style="vertical-align: middle; '
                f'max-width: {_REPR_PNG_SIZE[0]+2}px; '
                'display: flex; justify-content: space-between;">'
                '<div style="float: left;">'
                f'{color_block(self.get_under())} under'
                '</div>'
                '<div style="margin: 0 auto; display: inline-block;">'
                f'bad {color_block(self.get_bad())}'
                '</div>'
                '<div style="float: right;">'
                f'over {color_block(self.get_over())}'
                '</div>'
                '</div>')

    def copy(self):
        """Return a copy of the colormap."""
        return self.__copy__()


class LinearSegmentedColormap(Colormap):
    """
    Colormap objects based on lookup tables using linear segments.

    The lookup table is generated using linear interpolation for each
    primary color, with the 0-1 domain divided into any number of
    segments.
    """

    def __init__(self, name, segmentdata, N=256, gamma=1.0):
        """
        Create colormap from linear mapping segments

        segmentdata argument is a dictionary with a red, green and blue
        entries. Each entry should be a list of *x*, *y0*, *y1* tuples,
        forming rows in a table. Entries for alpha are optional.

        Example: suppose you want red to increase from 0 to 1 over
        the bottom half, green to do the same over the middle half,
        and blue over the top half.  Then you would use::

            cdict = {'red':   [(0.0,  0.0, 0.0),
                               (0.5,  1.0, 1.0),
                               (1.0,  1.0, 1.0)],

                     'green': [(0.0,  0.0, 0.0),
                               (0.25, 0.0, 0.0),
                               (0.75, 1.0, 1.0),
                               (1.0,  1.0, 1.0)],

                     'blue':  [(0.0,  0.0, 0.0),
                               (0.5,  0.0, 0.0),
                               (1.0,  1.0, 1.0)]}

        Each row in the table for a given color is a sequence of
        *x*, *y0*, *y1* tuples.  In each sequence, *x* must increase
        monotonically from 0 to 1.  For any input value *z* falling
        between *x[i]* and *x[i+1]*, the output value of a given color
        will be linearly interpolated between *y1[i]* and *y0[i+1]*::

            row i:   x  y0  y1
                           /
                          /
            row i+1: x  y0  y1

        Hence y0 in the first row and y1 in the last row are never used.

        See Also
        --------
        LinearSegmentedColormap.from_list
            Static method; factory function for generating a smoothly-varying
            LinearSegmentedColormap.
        """
        # True only if all colors in map are identical; needed for contouring.
        self.monochrome = False
        super().__init__(name, N)
        self._segmentdata = segmentdata
        self._gamma = gamma

    def _init(self):
        self._lut = np.ones((self.N + 3, 4), float)
        self._lut[:-3, 0] = _create_lookup_table(
            self.N, self._segmentdata['red'], self._gamma)
        self._lut[:-3, 1] = _create_lookup_table(
            self.N, self._segmentdata['green'], self._gamma)
        self._lut[:-3, 2] = _create_lookup_table(
            self.N, self._segmentdata['blue'], self._gamma)
        if 'alpha' in self._segmentdata:
            self._lut[:-3, 3] = _create_lookup_table(
                self.N, self._segmentdata['alpha'], 1)
        self._isinit = True
        self._set_extremes()

    def set_gamma(self, gamma):
        """Set a new gamma value and regenerate colormap."""
        self._gamma = gamma
        self._init()

    @staticmethod
    def from_list(name, colors, N=256, gamma=1.0):
        """
        Create a `LinearSegmentedColormap` from a list of colors.

        Parameters
        ----------
        name : str
            The name of the colormap.
        colors : list of :mpltype:`color` or list of (value, color)
            If only colors are given, they are equidistantly mapped from the
            range :math:`[0, 1]`; i.e. 0 maps to ``colors[0]`` and 1 maps to
            ``colors[-1]``.
            If (value, color) pairs are given, the mapping is from *value*
            to *color*. This can be used to divide the range unevenly.
        N : int
            The number of RGB quantization levels.
        gamma : float
        """
        if not np.iterable(colors):
            raise ValueError('colors must be iterable')

        if (isinstance(colors[0], Sized) and len(colors[0]) == 2
                and not isinstance(colors[0], str)):
            # List of value, color pairs
            vals, colors = zip(*colors)
        else:
            vals = np.linspace(0, 1, len(colors))

        r, g, b, a = to_rgba_array(colors).T
        cdict = {
            "red": np.column_stack([vals, r, r]),
            "green": np.column_stack([vals, g, g]),
            "blue": np.column_stack([vals, b, b]),
            "alpha": np.column_stack([vals, a, a]),
        }

        return LinearSegmentedColormap(name, cdict, N, gamma)

    def resampled(self, lutsize):
        """Return a new colormap with *lutsize* entries."""
        new_cmap = LinearSegmentedColormap(self.name, self._segmentdata,
                                           lutsize)
        new_cmap._rgba_over = self._rgba_over
        new_cmap._rgba_under = self._rgba_under
        new_cmap._rgba_bad = self._rgba_bad
        return new_cmap

    # Helper ensuring picklability of the reversed cmap.
    @staticmethod
    def _reverser(func, x):
        return func(1 - x)

    def reversed(self, name=None):
        """
        Return a reversed instance of the Colormap.

        Parameters
        ----------
        name : str, optional
            The name for the reversed colormap. If None, the
            name is set to ``self.name + "_r"``.

        Returns
        -------
        LinearSegmentedColormap
            The reversed colormap.
        """
        if name is None:
            name = self.name + "_r"

        # Using a partial object keeps the cmap picklable.
        data_r = {key: (functools.partial(self._reverser, data)
                        if callable(data) else
                        [(1.0 - x, y1, y0) for x, y0, y1 in reversed(data)])
                  for key, data in self._segmentdata.items()}

        new_cmap = LinearSegmentedColormap(name, data_r, self.N, self._gamma)
        # Reverse the over/under values too
        new_cmap._rgba_over = self._rgba_under
        new_cmap._rgba_under = self._rgba_over
        new_cmap._rgba_bad = self._rgba_bad
        return new_cmap


class ListedColormap(Colormap):
    """
    Colormap object generated from a list of colors.

    This may be most useful when indexing directly into a colormap,
    but it can also be used to generate special colormaps for ordinary
    mapping.

    Parameters
    ----------
    colors : list, array
        Sequence of Matplotlib color specifications (color names or RGB(A)
        values).
    name : str, optional
        String to identify the colormap.
    N : int, optional
        Number of entries in the map. The default is *None*, in which case
        there is one colormap entry for each element in the list of colors.
        If ::

            N < len(colors)

        the list will be truncated at *N*. If ::

            N > len(colors)

        the list will be extended by repetition.
    """
    def __init__(self, colors, name='from_list', N=None):
        self.monochrome = False  # Are all colors identical? (for contour.py)
        if N is None:
            self.colors = colors
            N = len(colors)
        else:
            if isinstance(colors, str):
                self.colors = [colors] * N
                self.monochrome = True
            elif np.iterable(colors):
                if len(colors) == 1:
                    self.monochrome = True
                self.colors = list(
                    itertools.islice(itertools.cycle(colors), N))
            else:
                try:
                    gray = float(colors)
                except TypeError:
                    pass
                else:
                    self.colors = [gray] * N
                self.monochrome = True
        super().__init__(name, N)

    def _init(self):
        self._lut = np.zeros((self.N + 3, 4), float)
        self._lut[:-3] = to_rgba_array(self.colors)
        self._isinit = True
        self._set_extremes()

    def resampled(self, lutsize):
        """Return a new colormap with *lutsize* entries."""
        colors = self(np.linspace(0, 1, lutsize))
        new_cmap = ListedColormap(colors, name=self.name)
        # Keep the over/under values too
        new_cmap._rgba_over = self._rgba_over
        new_cmap._rgba_under = self._rgba_under
        new_cmap._rgba_bad = self._rgba_bad
        return new_cmap

    def reversed(self, name=None):
        """
        Return a reversed instance of the Colormap.

        Parameters
        ----------
        name : str, optional
            The name for the reversed colormap. If None, the
            name is set to ``self.name + "_r"``.

        Returns
        -------
        ListedColormap
            A reversed instance of the colormap.
        """
        if name is None:
            name = self.name + "_r"

        colors_r = list(reversed(self.colors))
        new_cmap = ListedColormap(colors_r, name=name, N=self.N)
        # Reverse the over/under values too
        new_cmap._rgba_over = self._rgba_under
        new_cmap._rgba_under = self._rgba_over
        new_cmap._rgba_bad = self._rgba_bad
        return new_cmap


class MultivarColormap:
    """
    Class for holding multiple `~matplotlib.colors.Colormap` for use in a
    `~matplotlib.cm.ScalarMappable` object
    """
    def __init__(self, colormaps, combination_mode, name='multivariate colormap'):
        """
        Parameters
        ----------
        colormaps: list or tuple of `~matplotlib.colors.Colormap` objects
            The individual colormaps that are combined
        combination_mode: str, 'sRGB_add' or 'sRGB_sub'
            Describe how colormaps are combined in sRGB space

            - If 'sRGB_add' -> Mixing produces brighter colors
              `sRGB = sum(colors)`
            - If 'sRGB_sub' -> Mixing produces darker colors
              `sRGB = 1 - sum(1 - colors)`
        name : str, optional
            The name of the colormap family.
        """
        self.name = name

        if not np.iterable(colormaps) \
           or len(colormaps) == 1 \
           or isinstance(colormaps, str):
            raise ValueError("A MultivarColormap must have more than one colormap.")
        colormaps = list(colormaps)  # ensure cmaps is a list, i.e. not a tuple
        for i, cmap in enumerate(colormaps):
            if isinstance(cmap, str):
                colormaps[i] = mpl.colormaps[cmap]
            elif not isinstance(cmap, Colormap):
                raise ValueError("colormaps must be a list of objects that subclass"
                                 " Colormap or a name found in the colormap registry.")

        self._colormaps = colormaps
        _api.check_in_list(['sRGB_add', 'sRGB_sub'], combination_mode=combination_mode)
        self._combination_mode = combination_mode
        self.n_variates = len(colormaps)
        self._rgba_bad = (0.0, 0.0, 0.0, 0.0)  # If bad, don't paint anything.

    def __call__(self, X, alpha=None, bytes=False, clip=True):
        r"""
        Parameters
        ----------
        X : tuple (X0, X1, ...) of length equal to the number of colormaps
            X0, X1 ...:
            float or int, `~numpy.ndarray` or scalar
            The data value(s) to convert to RGBA.
            For floats, *Xi...* should be in the interval ``[0.0, 1.0]`` to
            return the RGBA values ``X*100`` percent along the Colormap line.
            For integers, *Xi...*  should be in the interval ``[0, self[i].N)`` to
            return RGBA values *indexed* from colormap [i] with index ``Xi``, where
            self[i] is colormap i.
        alpha : float or array-like or None
            Alpha must be a scalar between 0 and 1, a sequence of such
            floats with shape matching *Xi*, or None.
        bytes : bool, default: False
            If False (default), the returned RGBA values will be floats in the
            interval ``[0, 1]`` otherwise they will be `numpy.uint8`\s in the
            interval ``[0, 255]``.
        clip : bool, default: True
            If True, clip output to 0 to 1

        Returns
        -------
        Tuple of RGBA values if X[0] is scalar, otherwise an array of
        RGBA values with a shape of ``X.shape + (4, )``.
        """

        if len(X) != len(self):
            raise ValueError(
                f'For the selected colormap the data must have a first dimension '
                f'{len(self)}, not {len(X)}')
        rgba, mask_bad = self[0]._get_rgba_and_mask(X[0], bytes=False)
        for c, xx in zip(self[1:], X[1:]):
            sub_rgba, sub_mask_bad = c._get_rgba_and_mask(xx, bytes=False)
            rgba[..., :3] += sub_rgba[..., :3]  # add colors
            rgba[..., 3] *= sub_rgba[..., 3]  # multiply alpha
            mask_bad |= sub_mask_bad

        if self.combination_mode == 'sRGB_sub':
            rgba[..., :3] -= len(self) - 1

        rgba[mask_bad] = self.get_bad()

        if clip:
            rgba = np.clip(rgba, 0, 1)

        if alpha is not None:
            if clip:
                alpha = np.clip(alpha, 0, 1)
            if np.shape(alpha) not in [(), np.shape(X[0])]:
                raise ValueError(
                    f"alpha is array-like but its shape {np.shape(alpha)} does "
                    f"not match that of X[0] {np.shape(X[0])}")
            rgba[..., -1] *= alpha

        if bytes:
            if not clip:
                raise ValueError(
                    "clip cannot be false while bytes is true"
                    " as uint8 does not support values below 0"
                    " or above 255.")
            rgba = (rgba * 255).astype('uint8')

        if not np.iterable(X[0]):
            rgba = tuple(rgba)

        return rgba

    def copy(self):
        """Return a copy of the multivarcolormap."""
        return self.__copy__()

    def __copy__(self):
        cls = self.__class__
        cmapobject = cls.__new__(cls)
        cmapobject.__dict__.update(self.__dict__)
        cmapobject._colormaps = [cm.copy() for cm in self._colormaps]
        cmapobject._rgba_bad = np.copy(self._rgba_bad)
        return cmapobject

    def __eq__(self, other):
        if not isinstance(other, MultivarColormap):
            return False
        if len(self) != len(other):
            return False
        for c0, c1 in zip(self, other):
            if c0 != c1:
                return False
        if not all(self._rgba_bad == other._rgba_bad):
            return False
        if self.combination_mode != other.combination_mode:
            return False
        return True

    def __getitem__(self, item):
        return self._colormaps[item]

    def __iter__(self):
        for c in self._colormaps:
            yield c

    def __len__(self):
        return len(self._colormaps)

    def __str__(self):
        return self.name

    def get_bad(self):
        """Get the color for masked values."""
        return np.array(self._rgba_bad)

    def resampled(self, lutshape):
        """
        Return a new colormap with *lutshape* entries.

        Parameters
        ----------
        lutshape : tuple of (`int`, `None`)
            The tuple must have a length matching the number of variates.
            For each element in the tuple, if `int`, the corresponding colorbar
            is resampled, if `None`, the corresponding colorbar is not resampled.

        Returns
        -------
        MultivarColormap
        """

        if not np.iterable(lutshape) or len(lutshape) != len(self):
            raise ValueError(f"lutshape must be of length {len(self)}")
        new_cmap = self.copy()
        for i, s in enumerate(lutshape):
            if s is not None:
                new_cmap._colormaps[i] = self[i].resampled(s)
        return new_cmap

    def with_extremes(self, *, bad=None, under=None, over=None):
        """
        Return a copy of the `MultivarColormap` with modified out-of-range attributes.

        The *bad* keyword modifies the copied `MultivarColormap` while *under* and
        *over* modifies the attributes of the copied component colormaps.
        Note that *under* and *over* colors are subject to the mixing rules determined
        by the *combination_mode*.

        Parameters
        ----------
        bad: :mpltype:`color`, default: None
            If Matplotlib color, the bad value is set accordingly in the copy

        under tuple of :mpltype:`color`, default: None
            If tuple, the `under` value of each component is set with the values
            from the tuple.

        over tuple of :mpltype:`color`, default: None
            If tuple, the `over` value of each component is set with the values
            from the tuple.

        Returns
        -------
        MultivarColormap
            copy of self with attributes set

        """
        new_cm = self.copy()
        if bad is not None:
            new_cm._rgba_bad = to_rgba(bad)
        if under is not None:
            if not np.iterable(under) or len(under) != len(new_cm):
                raise ValueError("*under* must contain a color for each scalar colormap"
                                 f" i.e. be of length {len(new_cm)}.")
            else:
                for c, b in zip(new_cm, under):
                    c.set_under(b)
        if over is not None:
            if not np.iterable(over) or len(over) != len(new_cm):
                raise ValueError("*over* must contain a color for each scalar colormap"
                                 f" i.e. be of length {len(new_cm)}.")
            else:
                for c, b in zip(new_cm, over):
                    c.set_over(b)
        return new_cm

    @property
    def combination_mode(self):
        return self._combination_mode

    def _repr_png_(self):
        """Generate a PNG representation of the Colormap."""
        X = np.tile(np.linspace(0, 1, _REPR_PNG_SIZE[0]),
                                (_REPR_PNG_SIZE[1], 1))
        pixels = np.zeros((_REPR_PNG_SIZE[1]*len(self), _REPR_PNG_SIZE[0], 4),
                          dtype=np.uint8)
        for i, c in enumerate(self):
            pixels[i*_REPR_PNG_SIZE[1]:(i+1)*_REPR_PNG_SIZE[1], :] = c(X, bytes=True)
        png_bytes = io.BytesIO()
        title = self.name + ' multivariate colormap'
        author = f'Matplotlib v{mpl.__version__}, https://matplotlib.org'
        pnginfo = PngInfo()
        pnginfo.add_text('Title', title)
        pnginfo.add_text('Description', title)
        pnginfo.add_text('Author', author)
        pnginfo.add_text('Software', author)
        Image.fromarray(pixels).save(png_bytes, format='png', pnginfo=pnginfo)
        return png_bytes.getvalue()

    def _repr_html_(self):
        """Generate an HTML representation of the MultivarColormap."""
        return ''.join([c._repr_html_() for c in self._colormaps])


class BivarColormap:
    """
    Base class for all bivariate to RGBA mappings.

    Designed as a drop-in replacement for Colormap when using a 2D
    lookup table. To be used with `~matplotlib.cm.ScalarMappable`.
    """

    def __init__(self, N=256, M=256, shape='square', origin=(0, 0),
                 name='bivariate colormap'):
        """
        Parameters
        ----------
        N : int, default: 256
            The number of RGB quantization levels along the first axis.
        M : int, default: 256
            The number of RGB quantization levels along the second axis.
        shape : {'square', 'circle', 'ignore', 'circleignore'}

            - 'square' each variate is clipped to [0,1] independently
            - 'circle' the variates are clipped radially to the center
              of the colormap, and a circular mask is applied when the colormap
              is displayed
            - 'ignore' the variates are not clipped, but instead assigned the
              'outside' color
            - 'circleignore' a circular mask is applied, but the data is not
              clipped and instead assigned the 'outside' color

        origin : (float, float), default: (0,0)
            The relative origin of the colormap. Typically (0, 0), for colormaps
            that are linear on both axis, and (.5, .5) for circular colormaps.
            Used when getting 1D colormaps from 2D colormaps.
        name : str, optional
            The name of the colormap.
        """

        self.name = name
        self.N = int(N)  # ensure that N is always int
        self.M = int(M)
        _api.check_in_list(['square', 'circle', 'ignore', 'circleignore'], shape=shape)
        self._shape = shape
        self._rgba_bad = (0.0, 0.0, 0.0, 0.0)  # If bad, don't paint anything.
        self._rgba_outside = (1.0, 0.0, 1.0, 1.0)
        self._isinit = False
        self.n_variates = 2
        self._origin = (float(origin[0]), float(origin[1]))
        '''#: When this colormap exists on a scalar mappable and colorbar_extend
        #: is not False, colorbar creation will pick up ``colorbar_extend`` as
        #: the default value for the ``extend`` keyword in the
        #: `matplotlib.colorbar.Colorbar` constructor.
        self.colorbar_extend = False'''

    def __call__(self, X, alpha=None, bytes=False):
        r"""
        Parameters
        ----------
        X : tuple (X0, X1), X0 and X1: float or int or array-like
            The data value(s) to convert to RGBA.

            - For floats, *X* should be in the interval ``[0.0, 1.0]`` to
              return the RGBA values ``X*100`` percent along the Colormap.
            - For integers, *X* should be in the interval ``[0, Colormap.N)`` to
              return RGBA values *indexed* from the Colormap with index ``X``.

        alpha : float or array-like or None, default: None
            Alpha must be a scalar between 0 and 1, a sequence of such
            floats with shape matching X0, or None.
        bytes : bool, default: False
            If False (default), the returned RGBA values will be floats in the
            interval ``[0, 1]`` otherwise they will be `numpy.uint8`\s in the
            interval ``[0, 255]``.

        Returns
        -------
        Tuple of RGBA values if X is scalar, otherwise an array of
        RGBA values with a shape of ``X.shape + (4, )``.
        """

        if len(X) != 2:
            raise ValueError(
                f'For a `BivarColormap` the data must have a first dimension '
                f'2, not {len(X)}')

        if not self._isinit:
            self._init()

        X0 = np.ma.array(X[0], copy=True)
        X1 = np.ma.array(X[1], copy=True)
        # clip to shape of colormap, circle square, etc.
        self._clip((X0, X1))

        # Native byteorder is faster.
        if not X0.dtype.isnative:
            X0 = X0.byteswap().view(X0.dtype.newbyteorder())
        if not X1.dtype.isnative:
            X1 = X1.byteswap().view(X1.dtype.newbyteorder())

        if X0.dtype.kind == "f":
            X0 *= self.N
            # xa == 1 (== N after multiplication) is not out of range.
            X0[X0 == self.N] = self.N - 1

        if X1.dtype.kind == "f":
            X1 *= self.M
            # xa == 1 (== N after multiplication) is not out of range.
            X1[X1 == self.M] = self.M - 1

        # Pre-compute the masks before casting to int (which can truncate)
        mask_outside = (X0 < 0) | (X1 < 0) | (X0 >= self.N) | (X1 >= self.M)
        # If input was masked, get the bad mask from it; else mask out nans.
        mask_bad_0 = X0.mask if np.ma.is_masked(X0) else np.isnan(X0)
        mask_bad_1 = X1.mask if np.ma.is_masked(X1) else np.isnan(X1)
        mask_bad = mask_bad_0 | mask_bad_1

        with np.errstate(invalid="ignore"):
            # We need this cast for unsigned ints as well as floats
            X0 = X0.astype(int)
            X1 = X1.astype(int)

        # Set masked values to zero
        # The corresponding rgb values will be replaced later
        for X_part in [X0, X1]:
            X_part[mask_outside] = 0
            X_part[mask_bad] = 0

        rgba = self._lut[X0, X1]
        if np.isscalar(X[0]):
            rgba = np.copy(rgba)
        rgba[mask_outside] = self._rgba_outside
        rgba[mask_bad] = self._rgba_bad
        if bytes:
            rgba = (rgba * 255).astype(np.uint8)
        if alpha is not None:
            alpha = np.clip(alpha, 0, 1)
            if bytes:
                alpha *= 255  # Will be cast to uint8 upon assignment.
            if np.shape(alpha) not in [(), np.shape(X0)]:
                raise ValueError(
                    f"alpha is array-like but its shape {np.shape(alpha)} does "
                    f"not match that of X[0] {np.shape(X0)}")
            rgba[..., -1] = alpha
            # If the "bad" color is all zeros, then ignore alpha input.
            if (np.array(self._rgba_bad) == 0).all():
                rgba[mask_bad] = (0, 0, 0, 0)

        if not np.iterable(X[0]):
            rgba = tuple(rgba)
        return rgba

    @property
    def lut(self):
        """
        For external access to the lut, i.e. for displaying the cmap.
        For circular colormaps this returns a lut with a circular mask.

        Internal functions (such as to_rgb()) should use _lut
        which stores the lut without a circular mask
        A lut without the circular mask is needed in to_rgb() because the
        conversion from floats to ints results in some some pixel-requests
        just outside of the circular mask

        """
        if not self._isinit:
            self._init()
        lut = np.copy(self._lut)
        if self.shape == 'circle' or self.shape == 'circleignore':
            n = np.linspace(-1, 1, self.N)
            m = np.linspace(-1, 1, self.M)
            radii_sqr = (n**2)[:, np.newaxis] + (m**2)[np.newaxis, :]
            mask_outside = radii_sqr > 1
            lut[mask_outside, 3] = 0
        return lut

    def __copy__(self):
        cls = self.__class__
        cmapobject = cls.__new__(cls)
        cmapobject.__dict__.update(self.__dict__)

        cmapobject._rgba_outside = np.copy(self._rgba_outside)
        cmapobject._rgba_bad = np.copy(self._rgba_bad)
        cmapobject._shape = self.shape
        if self._isinit:
            cmapobject._lut = np.copy(self._lut)
        return cmapobject

    def __eq__(self, other):
        if not isinstance(other, BivarColormap):
            return False
        # To compare lookup tables the Colormaps have to be initialized
        if not self._isinit:
            self._init()
        if not other._isinit:
            other._init()
        if not np.array_equal(self._lut, other._lut):
            return False
        if not np.array_equal(self._rgba_bad, other._rgba_bad):
            return False
        if not np.array_equal(self._rgba_outside, other._rgba_outside):
            return False
        if self.shape != other.shape:
            return False
        return True

    def get_bad(self):
        """Get the color for masked values."""
        return self._rgba_bad

    def get_outside(self):
        """Get the color for out-of-range values."""
        return self._rgba_outside

    def resampled(self, lutshape, transposed=False):
        """
        Return a new colormap with *lutshape* entries.

        Note that this function does not move the origin.

        Parameters
        ----------
        lutshape : tuple of ints or None
            The tuple must be of length 2, and each entry is either an int or None.

            - If an int, the corresponding axis is resampled.
            - If negative the corresponding axis is resampled in reverse
            - If -1, the axis is inverted
            - If 1 or None, the corresponding axis is not resampled.

        transposed : bool, default: False
            if True, the axes are swapped after resampling

        Returns
        -------
        BivarColormap
        """

        if not np.iterable(lutshape) or len(lutshape) != 2:
            raise ValueError("lutshape must be of length 2")
        lutshape = [lutshape[0], lutshape[1]]
        if lutshape[0] is None or lutshape[0] == 1:
            lutshape[0] = self.N
        if lutshape[1] is None or lutshape[1] == 1:
            lutshape[1] = self.M

        inverted = [False, False]
        if lutshape[0] < 0:
            inverted[0] = True
            lutshape[0] = -lutshape[0]
            if lutshape[0] == 1:
                lutshape[0] = self.N
        if lutshape[1] < 0:
            inverted[1] = True
            lutshape[1] = -lutshape[1]
            if lutshape[1] == 1:
                lutshape[1] = self.M
        x_0, x_1 = np.mgrid[0:1:(lutshape[0] * 1j), 0:1:(lutshape[1] * 1j)]
        if inverted[0]:
            x_0 = x_0[::-1, :]
        if inverted[1]:
            x_1 = x_1[:, ::-1]

        # we need to use shape = 'square' while resampling the colormap.
        # if the colormap has shape = 'circle' we would otherwise get *outside* in the
        # resampled colormap
        shape_memory = self._shape
        self._shape = 'square'
        if transposed:
            new_lut = self((x_1, x_0))
            new_cmap = BivarColormapFromImage(new_lut, name=self.name,
                                              shape=shape_memory,
                                              origin=self.origin[::-1])
        else:
            new_lut = self((x_0, x_1))
            new_cmap = BivarColormapFromImage(new_lut, name=self.name,
                                              shape=shape_memory,
                                              origin=self.origin)
        self._shape = shape_memory

        new_cmap._rgba_bad = self._rgba_bad
        new_cmap._rgba_outside = self._rgba_outside
        return new_cmap

    def reversed(self, axis_0=True, axis_1=True):
        """
        Reverses both or one of the axis.
        """
        r_0 = -1 if axis_0 else 1
        r_1 = -1 if axis_1 else 1
        return self.resampled((r_0, r_1))

    def transposed(self):
        """
        Transposes the colormap by swapping the order of the axis
        """
        return self.resampled((None, None), transposed=True)

    def with_extremes(self, *, bad=None, outside=None, shape=None, origin=None):
        """
        Return a copy of the `BivarColormap` with modified attributes.

        Note that the *outside* color is only relevant if `shape` = 'ignore'
        or 'circleignore'.

        Parameters
        ----------
        bad : None or :mpltype:`color`
            If Matplotlib color, the *bad* value is set accordingly in the copy

        outside : None or :mpltype:`color`
            If Matplotlib color and shape is 'ignore' or 'circleignore', values
            *outside* the colormap are colored accordingly in the copy

        shape : {'square', 'circle', 'ignore', 'circleignore'}

            - If 'square' each variate is clipped to [0,1] independently
            - If 'circle' the variates are clipped radially to the center
              of the colormap, and a circular mask is applied when the colormap
              is displayed
            - If 'ignore' the variates are not clipped, but instead assigned the
              *outside* color
            - If 'circleignore' a circular mask is applied, but the data is not
              clipped and instead assigned the *outside* color

        origin : (float, float)
            The relative origin of the colormap. Typically (0, 0), for colormaps
            that are linear on both axis, and (.5, .5) for circular colormaps.
            Used when getting 1D colormaps from 2D colormaps.

        Returns
        -------
        BivarColormap
            copy of self with attributes set
        """
        new_cm = self.copy()
        if bad is not None:
            new_cm._rgba_bad = to_rgba(bad)
        if outside is not None:
            new_cm._rgba_outside = to_rgba(outside)
        if shape is not None:
            _api.check_in_list(['square', 'circle', 'ignore', 'circleignore'],
                               shape=shape)
            new_cm._shape = shape
        if origin is not None:
            new_cm._origin = (float(origin[0]), float(origin[1]))

        return new_cm

    def _init(self):
        """Generate the lookup table, ``self._lut``."""
        raise NotImplementedError("Abstract class only")

    @property
    def shape(self):
        return self._shape

    @property
    def origin(self):
        return self._origin

    def _clip(self, X):
        """
        For internal use when applying a BivarColormap to data.
        i.e. cm.ScalarMappable().to_rgba()
        Clips X[0] and X[1] according to 'self.shape'.
        X is modified in-place.

        Parameters
        ----------
        X: np.array
            array of floats or ints to be clipped
        shape : {'square', 'circle', 'ignore', 'circleignore'}

            - If 'square' each variate is clipped to [0,1] independently
            - If 'circle' the variates are clipped radially to the center
              of the colormap.
              It is assumed that a circular mask is applied when the colormap
              is displayed
            - If 'ignore' the variates are not clipped, but instead assigned the
              'outside' color
            - If 'circleignore' a circular mask is applied, but the data is not clipped
              and instead assigned the 'outside' color

        """
        if self.shape == 'square':
            for X_part, mx in zip(X, (self.N, self.M)):
                X_part[X_part < 0] = 0
                if X_part.dtype.kind == "f":
                    X_part[X_part > 1] = 1
                else:
                    X_part[X_part >= mx] = mx - 1

        elif self.shape == 'ignore':
            for X_part, mx in zip(X, (self.N, self.M)):
                X_part[X_part < 0] = -1
                if X_part.dtype.kind == "f":
                    X_part[X_part > 1] = -1
                else:
                    X_part[X_part >= mx] = -1

        elif self.shape == 'circle' or self.shape == 'circleignore':
            for X_part in X:
                if X_part.dtype.kind != "f":
                    raise NotImplementedError(
                        "Circular bivariate colormaps are only"
                        " implemented for use with with floats")
            radii_sqr = (X[0] - 0.5)**2 + (X[1] - 0.5)**2
            mask_outside = radii_sqr > 0.25
            if self.shape == 'circle':
                overextend = 2 * np.sqrt(radii_sqr[mask_outside])
                X[0][mask_outside] = (X[0][mask_outside] - 0.5) / overextend + 0.5
                X[1][mask_outside] = (X[1][mask_outside] - 0.5) / overextend + 0.5
            else:
                X[0][mask_outside] = -1
                X[1][mask_outside] = -1

    def __getitem__(self, item):
        """Creates and returns a colorbar along the selected axis"""
        if not self._isinit:
            self._init()
        if item == 0:
            origin_1_as_int = int(self._origin[1]*self.M)
            if origin_1_as_int > self.M-1:
                origin_1_as_int = self.M-1
            one_d_lut = self._lut[:, origin_1_as_int]
            new_cmap = ListedColormap(one_d_lut, name=f'{self.name}_0', N=self.N)

        elif item == 1:
            origin_0_as_int = int(self._origin[0]*self.N)
            if origin_0_as_int > self.N-1:
                origin_0_as_int = self.N-1
            one_d_lut = self._lut[origin_0_as_int, :]
            new_cmap = ListedColormap(one_d_lut, name=f'{self.name}_1', N=self.M)
        else:
            raise KeyError(f"only 0 or 1 are"
                           f" valid keys for BivarColormap, not {item!r}")
        new_cmap._rgba_bad = self._rgba_bad
        if self.shape in ['ignore', 'circleignore']:
            new_cmap.set_over(self._rgba_outside)
            new_cmap.set_under(self._rgba_outside)
        return new_cmap

    def _repr_png_(self):
        """Generate a PNG representation of the BivarColormap."""
        if not self._isinit:
            self._init()
        pixels = self.lut
        if pixels.shape[0] < _BIVAR_REPR_PNG_SIZE:
            pixels = np.repeat(pixels,
                               repeats=_BIVAR_REPR_PNG_SIZE//pixels.shape[0],
                               axis=0)[:256, :]
        if pixels.shape[1] < _BIVAR_REPR_PNG_SIZE:
            pixels = np.repeat(pixels,
                               repeats=_BIVAR_REPR_PNG_SIZE//pixels.shape[1],
                               axis=1)[:, :256]
        pixels = (pixels[::-1, :, :] * 255).astype(np.uint8)
        png_bytes = io.BytesIO()
        title = self.name + ' BivarColormap'
        author = f'Matplotlib v{mpl.__version__}, https://matplotlib.org'
        pnginfo = PngInfo()
        pnginfo.add_text('Title', title)
        pnginfo.add_text('Description', title)
        pnginfo.add_text('Author', author)
        pnginfo.add_text('Software', author)
        Image.fromarray(pixels).save(png_bytes, format='png', pnginfo=pnginfo)
        return png_bytes.getvalue()

    def _repr_html_(self):
        """Generate an HTML representation of the Colormap."""
        png_bytes = self._repr_png_()
        png_base64 = base64.b64encode(png_bytes).decode('ascii')
        def color_block(color):
            hex_color = to_hex(color, keep_alpha=True)
            return (f'<div title="{hex_color}" '
                    'style="display: inline-block; '
                    'width: 1em; height: 1em; '
                    'margin: 0; '
                    'vertical-align: middle; '
                    'border: 1px solid #555; '
                    f'background-color: {hex_color};"></div>')

        return ('<div style="vertical-align: middle;">'
                f'<strong>{self.name}</strong> '
                '</div>'
                '<div class="cmap"><img '
                f'alt="{self.name} BivarColormap" '
                f'title="{self.name}" '
                'style="border: 1px solid #555;" '
                f'src="data:image/png;base64,{png_base64}"></div>'
                '<div style="vertical-align: middle; '
                f'max-width: {_BIVAR_REPR_PNG_SIZE+2}px; '
                'display: flex; justify-content: space-between;">'
                '<div style="float: left;">'
                f'{color_block(self.get_outside())} outside'
                '</div>'
                '<div style="float: right;">'
                f'bad {color_block(self.get_bad())}'
                '</div></div>')

    def copy(self):
        """Return a copy of the colormap."""
        return self.__copy__()


class SegmentedBivarColormap(BivarColormap):
    """
    BivarColormap object generated by supersampling a regular grid.

    Parameters
    ----------
    patch : np.array
        Patch is required to have a shape (k, l, 3), and will get supersampled
        to a lut of shape (N, N, 4).
    N : int
        The number of RGB quantization levels along each axis.
    shape : {'square', 'circle', 'ignore', 'circleignore'}

        - If 'square' each variate is clipped to [0,1] independently
        - If 'circle' the variates are clipped radially to the center
          of the colormap, and a circular mask is applied when the colormap
          is displayed
        - If 'ignore' the variates are not clipped, but instead assigned the
          'outside' color
        - If 'circleignore' a circular mask is applied, but the data is not clipped

    origin : (float, float)
        The relative origin of the colormap. Typically (0, 0), for colormaps
        that are linear on both axis, and (.5, .5) for circular colormaps.
        Used when getting 1D colormaps from 2D colormaps.

    name : str, optional
        The name of the colormap.
    """

    def __init__(self, patch, N=256, shape='square', origin=(0, 0),
                 name='segmented bivariate colormap'):
        _api.check_shape((None, None, 3), patch=patch)
        self.patch = patch
        super().__init__(N, N, shape, origin, name=name)

    def _init(self):
        s = self.patch.shape
        _patch = np.empty((s[0], s[1], 4))
        _patch[:, :, :3] = self.patch
        _patch[:, :, 3] = 1
        transform = mpl.transforms.Affine2D().translate(-0.5, -0.5)\
                                .scale(self.N / (s[1] - 1), self.N / (s[0] - 1))
        self._lut = np.empty((self.N, self.N, 4))

        _image.resample(_patch, self._lut, transform, _image.BILINEAR,
                        resample=False, alpha=1)
        self._isinit = True


class BivarColormapFromImage(BivarColormap):
    """
    BivarColormap object generated by supersampling a regular grid.

    Parameters
    ----------
    lut : nparray of shape (N, M, 3) or (N, M, 4)
        The look-up-table
    shape: {'square', 'circle', 'ignore', 'circleignore'}

        - If 'square' each variate is clipped to [0,1] independently
        - If 'circle' the variates are clipped radially to the center
          of the colormap, and a circular mask is applied when the colormap
          is displayed
        - If 'ignore' the variates are not clipped, but instead assigned the
          'outside' color
        - If 'circleignore' a circular mask is applied, but the data is not clipped

    origin: (float, float)
        The relative origin of the colormap. Typically (0, 0), for colormaps
        that are linear on both axis, and (.5, .5) for circular colormaps.
        Used when getting 1D colormaps from 2D colormaps.
    name : str, optional
        The name of the colormap.

    """

    def __init__(self, lut, shape='square', origin=(0, 0), name='from image'):
        # We can allow for a PIL.Image as input in the following way, but importing
        # matplotlib.image.pil_to_array() results in a circular import
        # For now, this function only accepts numpy arrays.
        # i.e.:
        # if isinstance(Image, lut):
        #    lut = image.pil_to_array(lut)
        lut = np.array(lut, copy=True)
        if lut.ndim != 3 or lut.shape[2] not in (3, 4):
            raise ValueError("The lut must be an array of shape (n, m, 3) or (n, m, 4)",
                             " or a PIL.image encoded as RGB or RGBA")

        if lut.dtype == np.uint8:
            lut = lut.astype(np.float32)/255
        if lut.shape[2] == 3:
            new_lut = np.empty((lut.shape[0], lut.shape[1], 4), dtype=lut.dtype)
            new_lut[:, :, :3] = lut
            new_lut[:, :, 3] = 1.
            lut = new_lut
        self._lut = lut
        super().__init__(lut.shape[0], lut.shape[1], shape, origin, name=name)

    def _init(self):
        self._isinit = True


class Normalize:
    """
    A class which, when called, maps values within the interval
    ``[vmin, vmax]`` linearly to the interval ``[0.0, 1.0]``. The mapping of
    values outside ``[vmin, vmax]`` depends on *clip*.

    Examples
    --------
    ::

        x = [-2, -1, 0, 1, 2]

        norm = mpl.colors.Normalize(vmin=-1, vmax=1, clip=False)
        norm(x)  # [-0.5, 0., 0.5, 1., 1.5]
        norm = mpl.colors.Normalize(vmin=-1, vmax=1, clip=True)
        norm(x)  # [0., 0., 0.5, 1., 1.]

    See Also
    --------
    :ref:`colormapnorms`
    """

    def __init__(self, vmin=None, vmax=None, clip=False):
        """
        Parameters
        ----------
        vmin, vmax : float or None
            Values within the range ``[vmin, vmax]`` from the input data will be
            linearly mapped to ``[0, 1]``. If either *vmin* or *vmax* is not
            provided, they default to the minimum and maximum values of the input,
            respectively.

        clip : bool, default: False
            Determines the behavior for mapping values outside the range
            ``[vmin, vmax]``.

            If clipping is off, values outside the range ``[vmin, vmax]`` are
            also transformed, resulting in values outside ``[0, 1]``.  This
            behavior is usually desirable, as colormaps can mark these *under*
            and *over* values with specific colors.

            If clipping is on, values below *vmin* are mapped to 0 and values
            above *vmax* are mapped to 1. Such values become indistinguishable
            from regular boundary values, which may cause misinterpretation of
            the data.

        Notes
        -----
        If ``vmin == vmax``, input data will be mapped to 0.
        """
        self._vmin = _sanitize_extrema(vmin)
        self._vmax = _sanitize_extrema(vmax)
        self._clip = clip
        self._scale = None
        self.callbacks = cbook.CallbackRegistry(signals=["changed"])

    @property
    def vmin(self):
        return self._vmin

    @vmin.setter
    def vmin(self, value):
        value = _sanitize_extrema(value)
        if value != self._vmin:
            self._vmin = value
            self._changed()

    @property
    def vmax(self):
        return self._vmax

    @vmax.setter
    def vmax(self, value):
        value = _sanitize_extrema(value)
        if value != self._vmax:
            self._vmax = value
            self._changed()

    @property
    def clip(self):
        return self._clip

    @clip.setter
    def clip(self, value):
        if value != self._clip:
            self._clip = value
            self._changed()

    def _changed(self):
        """
        Call this whenever the norm is changed to notify all the
        callback listeners to the 'changed' signal.
        """
        self.callbacks.process('changed')

    @staticmethod
    def process_value(value):
        """
        Homogenize the input *value* for easy and efficient normalization.

        *value* can be a scalar or sequence.

        Parameters
        ----------
        value
            Data to normalize.

        Returns
        -------
        result : masked array
            Masked array with the same shape as *value*.
        is_scalar : bool
            Whether *value* is a scalar.

        Notes
        -----
        Float dtypes are preserved; integer types with two bytes or smaller are
        converted to np.float32, and larger types are converted to np.float64.
        Preserving float32 when possible, and using in-place operations,
        greatly improves speed for large arrays.
        """
        is_scalar = not np.iterable(value)
        if is_scalar:
            value = [value]
        dtype = np.min_scalar_type(value)
        if np.issubdtype(dtype, np.integer) or dtype.type is np.bool_:
            # bool_/int8/int16 -> float32; int32/int64 -> float64
            dtype = np.promote_types(dtype, np.float32)
        # ensure data passed in as an ndarray subclass are interpreted as
        # an ndarray. See issue #6622.
        mask = np.ma.getmask(value)
        data = np.asarray(value)
        result = np.ma.array(data, mask=mask, dtype=dtype, copy=True)
        return result, is_scalar

    def __call__(self, value, clip=None):
        """
        Normalize the data and return the normalized data.

        Parameters
        ----------
        value
            Data to normalize.
        clip : bool, optional
            See the description of the parameter *clip* in `.Normalize`.

            If ``None``, defaults to ``self.clip`` (which defaults to
            ``False``).

        Notes
        -----
        If not already initialized, ``self.vmin`` and ``self.vmax`` are
        initialized using ``self.autoscale_None(value)``.
        """
        if clip is None:
            clip = self.clip

        result, is_scalar = self.process_value(value)

        if self.vmin is None or self.vmax is None:
            self.autoscale_None(result)
        # Convert at least to float, without losing precision.
        (vmin,), _ = self.process_value(self.vmin)
        (vmax,), _ = self.process_value(self.vmax)
        if vmin == vmax:
            result.fill(0)  # Or should it be all masked?  Or 0.5?
        elif vmin > vmax:
            raise ValueError("minvalue must be less than or equal to maxvalue")
        else:
            if clip:
                mask = np.ma.getmask(result)
                result = np.ma.array(np.clip(result.filled(vmax), vmin, vmax),
                                     mask=mask)
            # ma division is very slow; we can take a shortcut
            resdat = result.data
            resdat -= vmin
            resdat /= (vmax - vmin)
            result = np.ma.array(resdat, mask=result.mask, copy=False)
        if is_scalar:
            result = result[0]
        return result

    def inverse(self, value):
        """
        Maps the normalized value (i.e., index in the colormap) back to image
        data value.

        Parameters
        ----------
        value
            Normalized value.
        """
        if not self.scaled():
            raise ValueError("Not invertible until both vmin and vmax are set")
        (vmin,), _ = self.process_value(self.vmin)
        (vmax,), _ = self.process_value(self.vmax)

        if np.iterable(value):
            val = np.ma.asarray(value)
            return vmin + val * (vmax - vmin)
        else:
            return vmin + value * (vmax - vmin)

    def autoscale(self, A):
        """Set *vmin*, *vmax* to min, max of *A*."""
        with self.callbacks.blocked():
            # Pause callbacks while we are updating so we only get
            # a single update signal at the end
            self.vmin = self.vmax = None
            self.autoscale_None(A)
        self._changed()

    def autoscale_None(self, A):
        """If *vmin* or *vmax* are not set, use the min/max of *A* to set them."""
        A = np.asanyarray(A)

        if isinstance(A, np.ma.MaskedArray):
            # we need to make the distinction between an array, False, np.bool_(False)
            if A.mask is False or not A.mask.shape:
                A = A.data

        if self.vmin is None and A.size:
            self.vmin = A.min()
        if self.vmax is None and A.size:
            self.vmax = A.max()

    def scaled(self):
        """Return whether *vmin* and *vmax* are both set."""
        return self.vmin is not None and self.vmax is not None


class TwoSlopeNorm(Normalize):
    def __init__(self, vcenter, vmin=None, vmax=None):
        """
        Normalize data with a set center.

        Useful when mapping data with an unequal rates of change around a
        conceptual center, e.g., data that range from -2 to 4, with 0 as
        the midpoint.

        Parameters
        ----------
        vcenter : float
            The data value that defines ``0.5`` in the normalization.
        vmin : float, optional
            The data value that defines ``0.0`` in the normalization.
            Defaults to the min value of the dataset.
        vmax : float, optional
            The data value that defines ``1.0`` in the normalization.
            Defaults to the max value of the dataset.

        Examples
        --------
        This maps data value -4000 to 0., 0 to 0.5, and +10000 to 1.0; data
        between is linearly interpolated::

            >>> import matplotlib.colors as mcolors
            >>> offset = mcolors.TwoSlopeNorm(vmin=-4000.,
            ...                               vcenter=0., vmax=10000)
            >>> data = [-4000., -2000., 0., 2500., 5000., 7500., 10000.]
            >>> offset(data)
            array([0., 0.25, 0.5, 0.625, 0.75, 0.875, 1.0])
        """

        super().__init__(vmin=vmin, vmax=vmax)
        self._vcenter = vcenter
        if vcenter is not None and vmax is not None and vcenter >= vmax:
            raise ValueError('vmin, vcenter, and vmax must be in '
                             'ascending order')
        if vcenter is not None and vmin is not None and vcenter <= vmin:
            raise ValueError('vmin, vcenter, and vmax must be in '
                             'ascending order')

    @property
    def vcenter(self):
        return self._vcenter

    @vcenter.setter
    def vcenter(self, value):
        if value != self._vcenter:
            self._vcenter = value
            self._changed()

    def autoscale_None(self, A):
        """
        Get vmin and vmax.

        If vcenter isn't in the range [vmin, vmax], either vmin or vmax
        is expanded so that vcenter lies in the middle of the modified range
        [vmin, vmax].
        """
        super().autoscale_None(A)
        if self.vmin >= self.vcenter:
            self.vmin = self.vcenter - (self.vmax - self.vcenter)
        if self.vmax <= self.vcenter:
            self.vmax = self.vcenter + (self.vcenter - self.vmin)

    def __call__(self, value, clip=None):
        """
        Map value to the interval [0, 1]. The *clip* argument is unused.
        """
        result, is_scalar = self.process_value(value)
        self.autoscale_None(result)  # sets self.vmin, self.vmax if None

        if not self.vmin <= self.vcenter <= self.vmax:
            raise ValueError("vmin, vcenter, vmax must increase monotonically")
        # note that we must extrapolate for tick locators:
        result = np.ma.masked_array(
            np.interp(result, [self.vmin, self.vcenter, self.vmax],
                      [0, 0.5, 1], left=-np.inf, right=np.inf),
            mask=np.ma.getmask(result))
        if is_scalar:
            result = np.atleast_1d(result)[0]
        return result

    def inverse(self, value):
        if not self.scaled():
            raise ValueError("Not invertible until both vmin and vmax are set")
        (vmin,), _ = self.process_value(self.vmin)
        (vmax,), _ = self.process_value(self.vmax)
        (vcenter,), _ = self.process_value(self.vcenter)
        result = np.interp(value, [0, 0.5, 1], [vmin, vcenter, vmax],
                           left=-np.inf, right=np.inf)
        return result


class CenteredNorm(Normalize):
    def __init__(self, vcenter=0, halfrange=None, clip=False):
        """
        Normalize symmetrical data around a center (0 by default).

        Unlike `TwoSlopeNorm`, `CenteredNorm` applies an equal rate of change
        around the center.

        Useful when mapping symmetrical data around a conceptual center
        e.g., data that range from -2 to 4, with 0 as the midpoint, and
        with equal rates of change around that midpoint.

        Parameters
        ----------
        vcenter : float, default: 0
            The data value that defines ``0.5`` in the normalization.
        halfrange : float, optional
            The range of data values that defines a range of ``0.5`` in the
            normalization, so that *vcenter* - *halfrange* is ``0.0`` and
            *vcenter* + *halfrange* is ``1.0`` in the normalization.
            Defaults to the largest absolute difference to *vcenter* for
            the values in the dataset.
        clip : bool, default: False
            Determines the behavior for mapping values outside the range
            ``[vmin, vmax]``.

            If clipping is off, values outside the range ``[vmin, vmax]`` are
            also transformed, resulting in values outside ``[0, 1]``.  This
            behavior is usually desirable, as colormaps can mark these *under*
            and *over* values with specific colors.

            If clipping is on, values below *vmin* are mapped to 0 and values
            above *vmax* are mapped to 1. Such values become indistinguishable
            from regular boundary values, which may cause misinterpretation of
            the data.

        Examples
        --------
        This maps data values -2 to 0.25, 0 to 0.5, and 4 to 1.0
        (assuming equal rates of change above and below 0.0):

            >>> import matplotlib.colors as mcolors
            >>> norm = mcolors.CenteredNorm(halfrange=4.0)
            >>> data = [-2., 0., 4.]
            >>> norm(data)
            array([0.25, 0.5 , 1.  ])
        """
        super().__init__(vmin=None, vmax=None, clip=clip)
        self._vcenter = vcenter
        # calling the halfrange setter to set vmin and vmax
        self.halfrange = halfrange

    def autoscale(self, A):
        """
        Set *halfrange* to ``max(abs(A-vcenter))``, then set *vmin* and *vmax*.
        """
        A = np.asanyarray(A)
        self.halfrange = max(self._vcenter-A.min(),
                             A.max()-self._vcenter)

    def autoscale_None(self, A):
        """Set *vmin* and *vmax*."""
        A = np.asanyarray(A)
        if self.halfrange is None and A.size:
            self.autoscale(A)

    @property
    def vmin(self):
        return self._vmin

    @vmin.setter
    def vmin(self, value):
        value = _sanitize_extrema(value)
        if value != self._vmin:
            self._vmin = value
            self._vmax = 2*self.vcenter - value
            self._changed()

    @property
    def vmax(self):
        return self._vmax

    @vmax.setter
    def vmax(self, value):
        value = _sanitize_extrema(value)
        if value != self._vmax:
            self._vmax = value
            self._vmin = 2*self.vcenter - value
            self._changed()

    @property
    def vcenter(self):
        return self._vcenter

    @vcenter.setter
    def vcenter(self, vcenter):
        if vcenter != self._vcenter:
            self._vcenter = vcenter
            # Trigger an update of the vmin/vmax values through the setter
            self.halfrange = self.halfrange
            self._changed()

    @property
    def halfrange(self):
        if self.vmin is None or self.vmax is None:
            return None
        return (self.vmax - self.vmin) / 2

    @halfrange.setter
    def halfrange(self, halfrange):
        if halfrange is None:
            self.vmin = None
            self.vmax = None
        else:
            self.vmin = self.vcenter - abs(halfrange)
            self.vmax = self.vcenter + abs(halfrange)


def make_norm_from_scale(scale_cls, base_norm_cls=None, *, init=None):
    """
    Decorator for building a `.Normalize` subclass from a `~.scale.ScaleBase`
    subclass.

    After ::

        @make_norm_from_scale(scale_cls)
        class norm_cls(Normalize):
            ...

    *norm_cls* is filled with methods so that normalization computations are
    forwarded to *scale_cls* (i.e., *scale_cls* is the scale that would be used
    for the colorbar of a mappable normalized with *norm_cls*).

    If *init* is not passed, then the constructor signature of *norm_cls*
    will be ``norm_cls(vmin=None, vmax=None, clip=False)``; these three
    parameters will be forwarded to the base class (``Normalize.__init__``),
    and a *scale_cls* object will be initialized with no arguments (other than
    a dummy axis).

    If the *scale_cls* constructor takes additional parameters, then *init*
    should be passed to `make_norm_from_scale`.  It is a callable which is
    *only* used for its signature.  First, this signature will become the
    signature of *norm_cls*.  Second, the *norm_cls* constructor will bind the
    parameters passed to it using this signature, extract the bound *vmin*,
    *vmax*, and *clip* values, pass those to ``Normalize.__init__``, and
    forward the remaining bound values (including any defaults defined by the
    signature) to the *scale_cls* constructor.
    """

    if base_norm_cls is None:
        return functools.partial(make_norm_from_scale, scale_cls, init=init)

    if isinstance(scale_cls, functools.partial):
        scale_args = scale_cls.args
        scale_kwargs_items = tuple(scale_cls.keywords.items())
        scale_cls = scale_cls.func
    else:
        scale_args = scale_kwargs_items = ()

    if init is None:
        def init(vmin=None, vmax=None, clip=False): pass

    return _make_norm_from_scale(
        scale_cls, scale_args, scale_kwargs_items,
        base_norm_cls, inspect.signature(init))


@functools.cache
def _make_norm_from_scale(
    scale_cls, scale_args, scale_kwargs_items,
    base_norm_cls, bound_init_signature,
):
    """
    Helper for `make_norm_from_scale`.

    This function is split out to enable caching (in particular so that
    different unpickles reuse the same class).  In order to do so,

    - ``functools.partial`` *scale_cls* is expanded into ``func, args, kwargs``
      to allow memoizing returned norms (partial instances always compare
      unequal, but we can check identity based on ``func, args, kwargs``;
    - *init* is replaced by *init_signature*, as signatures are picklable,
      unlike to arbitrary lambdas.
    """

    class Norm(base_norm_cls):
        def __reduce__(self):
            cls = type(self)
            # If the class is toplevel-accessible, it is possible to directly
            # pickle it "by name".  This is required to support norm classes
            # defined at a module's toplevel, as the inner base_norm_cls is
            # otherwise unpicklable (as it gets shadowed by the generated norm
            # class).  If either import or attribute access fails, fall back to
            # the general path.
            try:
                if cls is getattr(importlib.import_module(cls.__module__),
                                  cls.__qualname__):
                    return (_create_empty_object_of_class, (cls,), vars(self))
            except (ImportError, AttributeError):
                pass
            return (_picklable_norm_constructor,
                    (scale_cls, scale_args, scale_kwargs_items,
                     base_norm_cls, bound_init_signature),
                    vars(self))

        def __init__(self, *args, **kwargs):
            ba = bound_init_signature.bind(*args, **kwargs)
            ba.apply_defaults()
            super().__init__(
                **{k: ba.arguments.pop(k) for k in ["vmin", "vmax", "clip"]})
            self._scale = functools.partial(
                scale_cls, *scale_args, **dict(scale_kwargs_items))(
                    axis=None, **ba.arguments)
            self._trf = self._scale.get_transform()

        __init__.__signature__ = bound_init_signature.replace(parameters=[
            inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            *bound_init_signature.parameters.values()])

        def __call__(self, value, clip=None):
            value, is_scalar = self.process_value(value)
            if self.vmin is None or self.vmax is None:
                self.autoscale_None(value)
            if self.vmin > self.vmax:
                raise ValueError("vmin must be less or equal to vmax")
            if self.vmin == self.vmax:
                return np.full_like(value, 0)
            if clip is None:
                clip = self.clip
            if clip:
                value = np.clip(value, self.vmin, self.vmax)
            t_value = self._trf.transform(value).reshape(np.shape(value))
            t_vmin, t_vmax = self._trf.transform([self.vmin, self.vmax])
            if not np.isfinite([t_vmin, t_vmax]).all():
                raise ValueError("Invalid vmin or vmax")
            t_value -= t_vmin
            t_value /= (t_vmax - t_vmin)
            t_value = np.ma.masked_invalid(t_value, copy=False)
            return t_value[0] if is_scalar else t_value

        def inverse(self, value):
            if not self.scaled():
                raise ValueError("Not invertible until scaled")
            if self.vmin > self.vmax:
                raise ValueError("vmin must be less or equal to vmax")
            t_vmin, t_vmax = self._trf.transform([self.vmin, self.vmax])
            if not np.isfinite([t_vmin, t_vmax]).all():
                raise ValueError("Invalid vmin or vmax")
            value, is_scalar = self.process_value(value)
            rescaled = value * (t_vmax - t_vmin)
            rescaled += t_vmin
            value = (self._trf
                     .inverted()
                     .transform(rescaled)
                     .reshape(np.shape(value)))
            return value[0] if is_scalar else value

        def autoscale_None(self, A):
            # i.e. A[np.isfinite(...)], but also for non-array A's
            in_trf_domain = np.extract(np.isfinite(self._trf.transform(A)), A)
            if in_trf_domain.size == 0:
                in_trf_domain = np.ma.masked
            return super().autoscale_None(in_trf_domain)

    if base_norm_cls is Normalize:
        Norm.__name__ = f"{scale_cls.__name__}Norm"
        Norm.__qualname__ = f"{scale_cls.__qualname__}Norm"
    else:
        Norm.__name__ = base_norm_cls.__name__
        Norm.__qualname__ = base_norm_cls.__qualname__
    Norm.__module__ = base_norm_cls.__module__
    Norm.__doc__ = base_norm_cls.__doc__

    return Norm


def _create_empty_object_of_class(cls):
    return cls.__new__(cls)


def _picklable_norm_constructor(*args):
    return _create_empty_object_of_class(_make_norm_from_scale(*args))


@make_norm_from_scale(
    scale.FuncScale,
    init=lambda functions, vmin=None, vmax=None, clip=False: None)
class FuncNorm(Normalize):
    """
    Arbitrary normalization using functions for the forward and inverse.

    Parameters
    ----------
    functions : (callable, callable)
        two-tuple of the forward and inverse functions for the normalization.
        The forward function must be monotonic.

        Both functions must have the signature ::

           def forward(values: array-like) -> array-like

    vmin, vmax : float or None
        If *vmin* and/or *vmax* is not given, they are initialized from the
        minimum and maximum value, respectively, of the first input
        processed; i.e., ``__call__(A)`` calls ``autoscale_None(A)``.

    clip : bool, default: False
        Determines the behavior for mapping values outside the range
        ``[vmin, vmax]``.

        If clipping is off, values outside the range ``[vmin, vmax]`` are also
        transformed by the function, resulting in values outside ``[0, 1]``.
        This behavior is usually desirable, as colormaps can mark these *under*
        and *over* values with specific colors.

        If clipping is on, values below *vmin* are mapped to 0 and values above
        *vmax* are mapped to 1. Such values become indistinguishable from
        regular boundary values, which may cause misinterpretation of the data.
    """


LogNorm = make_norm_from_scale(
    functools.partial(scale.LogScale, nonpositive="mask"))(Normalize)
LogNorm.__name__ = LogNorm.__qualname__ = "LogNorm"
LogNorm.__doc__ = "Normalize a given value to the 0-1 range on a log scale."


@make_norm_from_scale(
    scale.SymmetricalLogScale,
    init=lambda linthresh, linscale=1., vmin=None, vmax=None, clip=False, *,
                base=10: None)
class SymLogNorm(Normalize):
    """
    The symmetrical logarithmic scale is logarithmic in both the
    positive and negative directions from the origin.

    Since the values close to zero tend toward infinity, there is a
    need to have a range around zero that is linear.  The parameter
    *linthresh* allows the user to specify the size of this range
    (-*linthresh*, *linthresh*).

    Parameters
    ----------
    linthresh : float
        The range within which the plot is linear (to avoid having the plot
        go to infinity around zero).
    linscale : float, default: 1
        This allows the linear range (-*linthresh* to *linthresh*) to be
        stretched relative to the logarithmic range. Its value is the
        number of decades to use for each half of the linear range. For
        example, when *linscale* == 1.0 (the default), the space used for
        the positive and negative halves of the linear range will be equal
        to one decade in the logarithmic range.
    base : float, default: 10
    """

    @property
    def linthresh(self):
        return self._scale.linthresh

    @linthresh.setter
    def linthresh(self, value):
        self._scale.linthresh = value


@make_norm_from_scale(
    scale.AsinhScale,
    init=lambda linear_width=1, vmin=None, vmax=None, clip=False: None)
class AsinhNorm(Normalize):
    """
    The inverse hyperbolic sine scale is approximately linear near
    the origin, but becomes logarithmic for larger positive
    or negative values. Unlike the `SymLogNorm`, the transition between
    these linear and logarithmic regions is smooth, which may reduce
    the risk of visual artifacts.

    .. note::

       This API is provisional and may be revised in the future
       based on early user feedback.

    Parameters
    ----------
    linear_width : float, default: 1
        The effective width of the linear region, beyond which
        the transformation becomes asymptotically logarithmic
    """

    @property
    def linear_width(self):
        return self._scale.linear_width

    @linear_width.setter
    def linear_width(self, value):
        self._scale.linear_width = value


class PowerNorm(Normalize):
    r"""
    Linearly map a given value to the 0-1 range and then apply
    a power-law normalization over that range.

    Parameters
    ----------
    gamma : float
        Power law exponent.
    vmin, vmax : float or None
        If *vmin* and/or *vmax* is not given, they are initialized from the
        minimum and maximum value, respectively, of the first input
        processed; i.e., ``__call__(A)`` calls ``autoscale_None(A)``.
    clip : bool, default: False
        Determines the behavior for mapping values outside the range
        ``[vmin, vmax]``.

        If clipping is off, values above *vmax* are transformed by the power
        function, resulting in values above 1, and values below *vmin* are linearly
        transformed resulting in values below 0. This behavior is usually desirable, as
        colormaps can mark these *under* and *over* values with specific colors.

        If clipping is on, values below *vmin* are mapped to 0 and values above
        *vmax* are mapped to 1. Such values become indistinguishable from
        regular boundary values, which may cause misinterpretation of the data.

    Notes
    -----
    The normalization formula is

    .. math::

        \left ( \frac{x - v_{min}}{v_{max}  - v_{min}} \right )^{\gamma}

    For input values below *vmin*, gamma is set to one.
    """
    def __init__(self, gamma, vmin=None, vmax=None, clip=False):
        super().__init__(vmin, vmax, clip)
        self.gamma = gamma

    def __call__(self, value, clip=None):
        if clip is None:
            clip = self.clip

        result, is_scalar = self.process_value(value)

        self.autoscale_None(result)
        gamma = self.gamma
        vmin, vmax = self.vmin, self.vmax
        if vmin > vmax:
            raise ValueError("minvalue must be less than or equal to maxvalue")
        elif vmin == vmax:
            result.fill(0)
        else:
            if clip:
                mask = np.ma.getmask(result)
                result = np.ma.array(np.clip(result.filled(vmax), vmin, vmax),
                                     mask=mask)
            resdat = result.data
            resdat -= vmin
            resdat /= (vmax - vmin)
            resdat[resdat > 0] = np.power(resdat[resdat > 0], gamma)

            result = np.ma.array(resdat, mask=result.mask, copy=False)
        if is_scalar:
            result = result[0]
        return result

    def inverse(self, value):
        if not self.scaled():
            raise ValueError("Not invertible until scaled")

        result, is_scalar = self.process_value(value)

        gamma = self.gamma
        vmin, vmax = self.vmin, self.vmax

        resdat = result.data
        resdat[resdat > 0] = np.power(resdat[resdat > 0], 1 / gamma)
        resdat *= (vmax - vmin)
        resdat += vmin

        result = np.ma.array(resdat, mask=result.mask, copy=False)
        if is_scalar:
            result = result[0]
        return result


class BoundaryNorm(Normalize):
    """
    Generate a colormap index based on discrete intervals.

    Unlike `Normalize` or `LogNorm`, `BoundaryNorm` maps values to integers
    instead of to the interval 0-1.
    """

    # Mapping to the 0-1 interval could have been done via piece-wise linear
    # interpolation, but using integers seems simpler, and reduces the number
    # of conversions back and forth between int and float.

    def __init__(self, boundaries, ncolors, clip=False, *, extend='neither'):
        """
        Parameters
        ----------
        boundaries : array-like
            Monotonically increasing sequence of at least 2 bin edges:  data
            falling in the n-th bin will be mapped to the n-th color.

        ncolors : int
            Number of colors in the colormap to be used.

        clip : bool, optional
            If clip is ``True``, out of range values are mapped to 0 if they
            are below ``boundaries[0]`` or mapped to ``ncolors - 1`` if they
            are above ``boundaries[-1]``.

            If clip is ``False``, out of range values are mapped to -1 if
            they are below ``boundaries[0]`` or mapped to *ncolors* if they are
            above ``boundaries[-1]``. These are then converted to valid indices
            by `Colormap.__call__`.

        extend : {'neither', 'both', 'min', 'max'}, default: 'neither'
            Extend the number of bins to include one or both of the
            regions beyond the boundaries.  For example, if ``extend``
            is 'min', then the color to which the region between the first
            pair of boundaries is mapped will be distinct from the first
            color in the colormap, and by default a
            `~matplotlib.colorbar.Colorbar` will be drawn with
            the triangle extension on the left or lower end.

        Notes
        -----
        If there are fewer bins (including extensions) than colors, then the
        color index is chosen by linearly interpolating the ``[0, nbins - 1]``
        range onto the ``[0, ncolors - 1]`` range, effectively skipping some
        colors in the middle of the colormap.
        """
        if clip and extend != 'neither':
            raise ValueError("'clip=True' is not compatible with 'extend'")
        super().__init__(vmin=boundaries[0], vmax=boundaries[-1], clip=clip)
        self.boundaries = np.asarray(boundaries)
        self.N = len(self.boundaries)
        if self.N < 2:
            raise ValueError("You must provide at least 2 boundaries "
                             f"(1 region) but you passed in {boundaries!r}")
        self.Ncmap = ncolors
        self.extend = extend

        self._scale = None  # don't use the default scale.

        self._n_regions = self.N - 1  # number of colors needed
        self._offset = 0
        if extend in ('min', 'both'):
            self._n_regions += 1
            self._offset = 1
        if extend in ('max', 'both'):
            self._n_regions += 1
        if self._n_regions > self.Ncmap:
            raise ValueError(f"There are {self._n_regions} color bins "
                             "including extensions, but ncolors = "
                             f"{ncolors}; ncolors must equal or exceed the "
                             "number of bins")

    def __call__(self, value, clip=None):
        """
        This method behaves similarly to `.Normalize.__call__`, except that it
        returns integers or arrays of int16.
        """
        if clip is None:
            clip = self.clip

        xx, is_scalar = self.process_value(value)
        mask = np.ma.getmaskarray(xx)
        # Fill masked values a value above the upper boundary
        xx = np.atleast_1d(xx.filled(self.vmax + 1))
        if clip:
            np.clip(xx, self.vmin, self.vmax, out=xx)
            max_col = self.Ncmap - 1
        else:
            max_col = self.Ncmap
        # this gives us the bins in the lookup table in the range
        # [0, _n_regions - 1]  (the offset is set in the init)
        iret = np.digitize(xx, self.boundaries) - 1 + self._offset
        # if we have more colors than regions, stretch the region
        # index computed above to full range of the color bins.  This
        # will make use of the full range (but skip some of the colors
        # in the middle) such that the first region is mapped to the
        # first color and the last region is mapped to the last color.
        if self.Ncmap > self._n_regions:
            if self._n_regions == 1:
                # special case the 1 region case, pick the middle color
                iret[iret == 0] = (self.Ncmap - 1) // 2
            else:
                # otherwise linearly remap the values from the region index
                # to the color index spaces
                iret = (self.Ncmap - 1) / (self._n_regions - 1) * iret
        # cast to 16bit integers in all cases
        iret = iret.astype(np.int16)
        iret[xx < self.vmin] = -1
        iret[xx >= self.vmax] = max_col
        ret = np.ma.array(iret, mask=mask)
        if is_scalar:
            ret = int(ret[0])  # assume python scalar
        return ret

    def inverse(self, value):
        """
        Raises
        ------
        ValueError
            BoundaryNorm is not invertible, so calling this method will always
            raise an error
        """
        raise ValueError("BoundaryNorm is not invertible")


class NoNorm(Normalize):
    """
    Dummy replacement for `Normalize`, for the case where we want to use
    indices directly in a `~matplotlib.cm.ScalarMappable`.
    """
    def __call__(self, value, clip=None):
        if np.iterable(value):
            return np.ma.array(value)
        return value

    def inverse(self, value):
        if np.iterable(value):
            return np.ma.array(value)
        return value


def rgb_to_hsv(arr):
    """
    Convert an array of float RGB values (in the range [0, 1]) to HSV values.

    Parameters
    ----------
    arr : (..., 3) array-like
       All values must be in the range [0, 1]

    Returns
    -------
    (..., 3) `~numpy.ndarray`
       Colors converted to HSV values in range [0, 1]
    """
    arr = np.asarray(arr)

    # check length of the last dimension, should be _some_ sort of rgb
    if arr.shape[-1] != 3:
        raise ValueError("Last dimension of input array must be 3; "
                         f"shape {arr.shape} was found.")

    in_shape = arr.shape
    arr = np.array(
        arr, copy=False,
        dtype=np.promote_types(arr.dtype, np.float32),  # Don't work on ints.
        ndmin=2,  # In case input was 1D.
    )

    out = np.zeros_like(arr)
    arr_max = arr.max(-1)
    # Check if input is in the expected range
    if np.any(arr_max > 1):
        raise ValueError(
            "Input array must be in the range [0, 1]. "
            f"Found a maximum value of {arr_max.max()}"
        )

    if arr.min() < 0:
        raise ValueError(
            "Input array must be in the range [0, 1]. "
            f"Found a minimum value of {arr.min()}"
        )

    ipos = arr_max > 0
    delta = np.ptp(arr, -1)
    s = np.zeros_like(delta)
    s[ipos] = delta[ipos] / arr_max[ipos]
    ipos = delta > 0
    # red is max
    idx = (arr[..., 0] == arr_max) & ipos
    out[idx, 0] = (arr[idx, 1] - arr[idx, 2]) / delta[idx]
    # green is max
    idx = (arr[..., 1] == arr_max) & ipos
    out[idx, 0] = 2. + (arr[idx, 2] - arr[idx, 0]) / delta[idx]
    # blue is max
    idx = (arr[..., 2] == arr_max) & ipos
    out[idx, 0] = 4. + (arr[idx, 0] - arr[idx, 1]) / delta[idx]

    out[..., 0] = (out[..., 0] / 6.0) % 1.0
    out[..., 1] = s
    out[..., 2] = arr_max

    return out.reshape(in_shape)


def hsv_to_rgb(hsv):
    """
    Convert HSV values to RGB.

    Parameters
    ----------
    hsv : (..., 3) array-like
       All values assumed to be in range [0, 1]

    Returns
    -------
    (..., 3) `~numpy.ndarray`
       Colors converted to RGB values in range [0, 1]
    """
    hsv = np.asarray(hsv)

    # check length of the last dimension, should be _some_ sort of rgb
    if hsv.shape[-1] != 3:
        raise ValueError("Last dimension of input array must be 3; "
                         f"shape {hsv.shape} was found.")

    in_shape = hsv.shape
    hsv = np.array(
        hsv, copy=False,
        dtype=np.promote_types(hsv.dtype, np.float32),  # Don't work on ints.
        ndmin=2,  # In case input was 1D.
    )

    h = hsv[..., 0]
    s = hsv[..., 1]
    v = hsv[..., 2]

    r = np.empty_like(h)
    g = np.empty_like(h)
    b = np.empty_like(h)

    i = (h * 6.0).astype(int)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))

    idx = i % 6 == 0
    r[idx] = v[idx]
    g[idx] = t[idx]
    b[idx] = p[idx]

    idx = i == 1
    r[idx] = q[idx]
    g[idx] = v[idx]
    b[idx] = p[idx]

    idx = i == 2
    r[idx] = p[idx]
    g[idx] = v[idx]
    b[idx] = t[idx]

    idx = i == 3
    r[idx] = p[idx]
    g[idx] = q[idx]
    b[idx] = v[idx]

    idx = i == 4
    r[idx] = t[idx]
    g[idx] = p[idx]
    b[idx] = v[idx]

    idx = i == 5
    r[idx] = v[idx]
    g[idx] = p[idx]
    b[idx] = q[idx]

    idx = s == 0
    r[idx] = v[idx]
    g[idx] = v[idx]
    b[idx] = v[idx]

    rgb = np.stack([r, g, b], axis=-1)

    return rgb.reshape(in_shape)


def _vector_magnitude(arr):
    # things that don't work here:
    #  * np.linalg.norm: drops mask from ma.array
    #  * np.sum: drops mask from ma.array unless entire vector is masked
    sum_sq = 0
    for i in range(arr.shape[-1]):
        sum_sq += arr[..., i, np.newaxis] ** 2
    return np.sqrt(sum_sq)


class LightSource:
    """
    Create a light source coming from the specified azimuth and elevation.
    Angles are in degrees, with the azimuth measured
    clockwise from north and elevation up from the zero plane of the surface.

    `shade` is used to produce "shaded" RGB values for a data array.
    `shade_rgb` can be used to combine an RGB image with an elevation map.
    `hillshade` produces an illumination map of a surface.
    """

    def __init__(self, azdeg=315, altdeg=45, hsv_min_val=0, hsv_max_val=1,
                 hsv_min_sat=1, hsv_max_sat=0):
        """
        Specify the azimuth (measured clockwise from south) and altitude
        (measured up from the plane of the surface) of the light source
        in degrees.

        Parameters
        ----------
        azdeg : float, default: 315 degrees (from the northwest)
            The azimuth (0-360, degrees clockwise from North) of the light
            source.
        altdeg : float, default: 45 degrees
            The altitude (0-90, degrees up from horizontal) of the light
            source.
        hsv_min_val : number, default: 0
            The minimum value ("v" in "hsv") that the *intensity* map can shift the
            output image to.
        hsv_max_val : number, default: 1
            The maximum value ("v" in "hsv") that the *intensity* map can shift the
            output image to.
        hsv_min_sat : number, default: 1
            The minimum saturation value that the *intensity* map can shift the output
            image to.
        hsv_max_sat : number, default: 0
            The maximum saturation value that the *intensity* map can shift the output
            image to.

        Notes
        -----
        For backwards compatibility, the parameters *hsv_min_val*,
        *hsv_max_val*, *hsv_min_sat*, and *hsv_max_sat* may be supplied at
        initialization as well.  However, these parameters will only be used if
        "blend_mode='hsv'" is passed into `shade` or `shade_rgb`.
        See the documentation for `blend_hsv` for more details.
        """
        self.azdeg = azdeg
        self.altdeg = altdeg
        self.hsv_min_val = hsv_min_val
        self.hsv_max_val = hsv_max_val
        self.hsv_min_sat = hsv_min_sat
        self.hsv_max_sat = hsv_max_sat

    @property
    def direction(self):
        """The unit vector direction towards the light source."""
        # Azimuth is in degrees clockwise from North. Convert to radians
        # counterclockwise from East (mathematical notation).
        az = np.radians(90 - self.azdeg)
        alt = np.radians(self.altdeg)
        return np.array([
            np.cos(az) * np.cos(alt),
            np.sin(az) * np.cos(alt),
            np.sin(alt)
        ])

    def hillshade(self, elevation, vert_exag=1, dx=1, dy=1, fraction=1.):
        """
        Calculate the illumination intensity for a surface using the defined
        azimuth and elevation for the light source.

        This computes the normal vectors for the surface, and then passes them
        on to `shade_normals`

        Parameters
        ----------
        elevation : 2D array-like
            The height values used to generate an illumination map
        vert_exag : number, optional
            The amount to exaggerate the elevation values by when calculating
            illumination. This can be used either to correct for differences in
            units between the x-y coordinate system and the elevation
            coordinate system (e.g. decimal degrees vs. meters) or to
            exaggerate or de-emphasize topographic effects.
        dx : number, optional
            The x-spacing (columns) of the input *elevation* grid.
        dy : number, optional
            The y-spacing (rows) of the input *elevation* grid.
        fraction : number, optional
            Increases or decreases the contrast of the hillshade.  Values
            greater than one will cause intermediate values to move closer to
            full illumination or shadow (and clipping any values that move
            beyond 0 or 1). Note that this is not visually or mathematically
            the same as vertical exaggeration.

        Returns
        -------
        `~numpy.ndarray`
            A 2D array of illumination values between 0-1, where 0 is
            completely in shadow and 1 is completely illuminated.
        """

        # Because most image and raster GIS data has the first row in the array
        # as the "top" of the image, dy is implicitly negative.  This is
        # consistent to what `imshow` assumes, as well.
        dy = -dy

        # compute the normal vectors from the partial derivatives
        e_dy, e_dx = np.gradient(vert_exag * elevation, dy, dx)

        # .view is to keep subclasses
        normal = np.empty(elevation.shape + (3,)).view(type(elevation))
        normal[..., 0] = -e_dx
        normal[..., 1] = -e_dy
        normal[..., 2] = 1
        normal /= _vector_magnitude(normal)

        return self.shade_normals(normal, fraction)

    def shade_normals(self, normals, fraction=1.):
        """
        Calculate the illumination intensity for the normal vectors of a
        surface using the defined azimuth and elevation for the light source.

        Imagine an artificial sun placed at infinity in some azimuth and
        elevation position illuminating our surface. The parts of the surface
        that slope toward the sun should brighten while those sides facing away
        should become darker.

        Parameters
        ----------
        fraction : number, optional
            Increases or decreases the contrast of the hillshade.  Values
            greater than one will cause intermediate values to move closer to
            full illumination or shadow (and clipping any values that move
            beyond 0 or 1). Note that this is not visually or mathematically
            the same as vertical exaggeration.

        Returns
        -------
        `~numpy.ndarray`
            A 2D array of illumination values between 0-1, where 0 is
            completely in shadow and 1 is completely illuminated.
        """

        intensity = normals.dot(self.direction)

        # Apply contrast stretch
        imin, imax = intensity.min(), intensity.max()
        intensity *= fraction

        # Rescale to 0-1, keeping range before contrast stretch
        # If constant slope, keep relative scaling (i.e. flat should be 0.5,
        # fully occluded 0, etc.)
        if (imax - imin) > 1e-6:
            # Strictly speaking, this is incorrect. Negative values should be
            # clipped to 0 because they're fully occluded. However, rescaling
            # in this manner is consistent with the previous implementation and
            # visually appears better than a "hard" clip.
            intensity -= imin
            intensity /= (imax - imin)
        intensity = np.clip(intensity, 0, 1)

        return intensity

    def shade(self, data, cmap, norm=None, blend_mode='overlay', vmin=None,
              vmax=None, vert_exag=1, dx=1, dy=1, fraction=1, **kwargs):
        """
        Combine colormapped data values with an illumination intensity map
        (a.k.a.  "hillshade") of the values.

        Parameters
        ----------
        data : 2D array-like
            The height values used to generate a shaded map.
        cmap : `~matplotlib.colors.Colormap`
            The colormap used to color the *data* array. Note that this must be
            a `~matplotlib.colors.Colormap` instance.  For example, rather than
            passing in ``cmap='gist_earth'``, use
            ``cmap=plt.get_cmap('gist_earth')`` instead.
        norm : `~matplotlib.colors.Normalize` instance, optional
            The normalization used to scale values before colormapping. If
            None, the input will be linearly scaled between its min and max.
        blend_mode : {'hsv', 'overlay', 'soft'} or callable, optional
            The type of blending used to combine the colormapped data
            values with the illumination intensity.  Default is
            "overlay".  Note that for most topographic surfaces,
            "overlay" or "soft" appear more visually realistic. If a
            user-defined function is supplied, it is expected to
            combine an (M, N, 3) RGB array of floats (ranging 0 to 1) with
            an (M, N, 1) hillshade array (also 0 to 1).  (Call signature
            ``func(rgb, illum, **kwargs)``) Additional kwargs supplied
            to this function will be passed on to the *blend_mode*
            function.
        vmin : float or None, optional
            The minimum value used in colormapping *data*. If *None* the
            minimum value in *data* is used. If *norm* is specified, then this
            argument will be ignored.
        vmax : float or None, optional
            The maximum value used in colormapping *data*. If *None* the
            maximum value in *data* is used. If *norm* is specified, then this
            argument will be ignored.
        vert_exag : number, optional
            The amount to exaggerate the elevation values by when calculating
            illumination. This can be used either to correct for differences in
            units between the x-y coordinate system and the elevation
            coordinate system (e.g. decimal degrees vs. meters) or to
            exaggerate or de-emphasize topography.
        dx : number, optional
            The x-spacing (columns) of the input *elevation* grid.
        dy : number, optional
            The y-spacing (rows) of the input *elevation* grid.
        fraction : number, optional
            Increases or decreases the contrast of the hillshade.  Values
            greater than one will cause intermediate values to move closer to
            full illumination or shadow (and clipping any values that move
            beyond 0 or 1). Note that this is not visually or mathematically
            the same as vertical exaggeration.
        **kwargs
            Additional kwargs are passed on to the *blend_mode* function.

        Returns
        -------
        `~numpy.ndarray`
            An (M, N, 4) array of floats ranging between 0-1.
        """
        if vmin is None:
            vmin = data.min()
        if vmax is None:
            vmax = data.max()
        if norm is None:
            norm = Normalize(vmin=vmin, vmax=vmax)

        rgb0 = cmap(norm(data))
        rgb1 = self.shade_rgb(rgb0, elevation=data, blend_mode=blend_mode,
                              vert_exag=vert_exag, dx=dx, dy=dy,
                              fraction=fraction, **kwargs)
        # Don't overwrite the alpha channel, if present.
        rgb0[..., :3] = rgb1[..., :3]
        return rgb0

    def shade_rgb(self, rgb, elevation, fraction=1., blend_mode='hsv',
                  vert_exag=1, dx=1, dy=1, **kwargs):
        """
        Use this light source to adjust the colors of the *rgb* input array to
        give the impression of a shaded relief map with the given *elevation*.

        Parameters
        ----------
        rgb : array-like
            An (M, N, 3) RGB array, assumed to be in the range of 0 to 1.
        elevation : array-like
            An (M, N) array of the height values used to generate a shaded map.
        fraction : number
            Increases or decreases the contrast of the hillshade.  Values
            greater than one will cause intermediate values to move closer to
            full illumination or shadow (and clipping any values that move
            beyond 0 or 1). Note that this is not visually or mathematically
            the same as vertical exaggeration.
        blend_mode : {'hsv', 'overlay', 'soft'} or callable, optional
            The type of blending used to combine the colormapped data values
            with the illumination intensity.  For backwards compatibility, this
            defaults to "hsv". Note that for most topographic surfaces,
            "overlay" or "soft" appear more visually realistic. If a
            user-defined function is supplied, it is expected to combine an
            (M, N, 3) RGB array of floats (ranging 0 to 1) with an (M, N, 1)
            hillshade array (also 0 to 1).  (Call signature
            ``func(rgb, illum, **kwargs)``)
            Additional kwargs supplied to this function will be passed on to
            the *blend_mode* function.
        vert_exag : number, optional
            The amount to exaggerate the elevation values by when calculating
            illumination. This can be used either to correct for differences in
            units between the x-y coordinate system and the elevation
            coordinate system (e.g. decimal degrees vs. meters) or to
            exaggerate or de-emphasize topography.
        dx : number, optional
            The x-spacing (columns) of the input *elevation* grid.
        dy : number, optional
            The y-spacing (rows) of the input *elevation* grid.
        **kwargs
            Additional kwargs are passed on to the *blend_mode* function.

        Returns
        -------
        `~numpy.ndarray`
            An (m, n, 3) array of floats ranging between 0-1.
        """
        # Calculate the "hillshade" intensity.
        intensity = self.hillshade(elevation, vert_exag, dx, dy, fraction)
        intensity = intensity[..., np.newaxis]

        # Blend the hillshade and rgb data using the specified mode
        lookup = {
                'hsv': self.blend_hsv,
                'soft': self.blend_soft_light,
                'overlay': self.blend_overlay,
                }
        if blend_mode in lookup:
            blend = lookup[blend_mode](rgb, intensity, **kwargs)
        else:
            try:
                blend = blend_mode(rgb, intensity, **kwargs)
            except TypeError as err:
                raise ValueError('"blend_mode" must be callable or one of '
                                 f'{lookup.keys}') from err

        # Only apply result where hillshade intensity isn't masked
        if np.ma.is_masked(intensity):
            mask = intensity.mask[..., 0]
            for i in range(3):
                blend[..., i][mask] = rgb[..., i][mask]

        return blend

    def blend_hsv(self, rgb, intensity, hsv_max_sat=None, hsv_max_val=None,
                  hsv_min_val=None, hsv_min_sat=None):
        """
        Take the input data array, convert to HSV values in the given colormap,
        then adjust those color values to give the impression of a shaded
        relief map with a specified light source.  RGBA values are returned,
        which can then be used to plot the shaded image with imshow.

        The color of the resulting image will be darkened by moving the (s, v)
        values (in HSV colorspace) toward (hsv_min_sat, hsv_min_val) in the
        shaded regions, or lightened by sliding (s, v) toward (hsv_max_sat,
        hsv_max_val) in regions that are illuminated.  The default extremes are
        chose so that completely shaded points are nearly black (s = 1, v = 0)
        and completely illuminated points are nearly white (s = 0, v = 1).

        Parameters
        ----------
        rgb : `~numpy.ndarray`
            An (M, N, 3) RGB array of floats ranging from 0 to 1 (color image).
        intensity : `~numpy.ndarray`
            An (M, N, 1) array of floats ranging from 0 to 1 (grayscale image).
        hsv_max_sat : number, optional
            The maximum saturation value that the *intensity* map can shift the output
            image to. If not provided, use the value provided upon initialization.
        hsv_min_sat : number, optional
            The minimum saturation value that the *intensity* map can shift the output
            image to. If not provided, use the value provided upon initialization.
        hsv_max_val : number, optional
            The maximum value ("v" in "hsv") that the *intensity* map can shift the
            output image to. If not provided, use the value provided upon
            initialization.
        hsv_min_val : number, optional
            The minimum value ("v" in "hsv") that the *intensity* map can shift the
            output image to. If not provided, use the value provided upon
            initialization.

        Returns
        -------
        `~numpy.ndarray`
            An (M, N, 3) RGB array representing the combined images.
        """
        # Backward compatibility...
        if hsv_max_sat is None:
            hsv_max_sat = self.hsv_max_sat
        if hsv_max_val is None:
            hsv_max_val = self.hsv_max_val
        if hsv_min_sat is None:
            hsv_min_sat = self.hsv_min_sat
        if hsv_min_val is None:
            hsv_min_val = self.hsv_min_val

        # Expects a 2D intensity array scaled between -1 to 1...
        intensity = intensity[..., 0]
        intensity = 2 * intensity - 1

        # Convert to rgb, then rgb to hsv
        hsv = rgb_to_hsv(rgb[:, :, 0:3])
        hue, sat, val = np.moveaxis(hsv, -1, 0)

        # Modify hsv values (in place) to simulate illumination.
        # putmask(A, mask, B) <=> A[mask] = B[mask]
        np.putmask(sat, (np.abs(sat) > 1.e-10) & (intensity > 0),
                   (1 - intensity) * sat + intensity * hsv_max_sat)
        np.putmask(sat, (np.abs(sat) > 1.e-10) & (intensity < 0),
                   (1 + intensity) * sat - intensity * hsv_min_sat)
        np.putmask(val, intensity > 0,
                   (1 - intensity) * val + intensity * hsv_max_val)
        np.putmask(val, intensity < 0,
                   (1 + intensity) * val - intensity * hsv_min_val)
        np.clip(hsv[:, :, 1:], 0, 1, out=hsv[:, :, 1:])

        # Convert modified hsv back to rgb.
        return hsv_to_rgb(hsv)

    def blend_soft_light(self, rgb, intensity):
        """
        Combine an RGB image with an intensity map using "soft light" blending,
        using the "pegtop" formula.

        Parameters
        ----------
        rgb : `~numpy.ndarray`
            An (M, N, 3) RGB array of floats ranging from 0 to 1 (color image).
        intensity : `~numpy.ndarray`
            An (M, N, 1) array of floats ranging from 0 to 1 (grayscale image).

        Returns
        -------
        `~numpy.ndarray`
            An (M, N, 3) RGB array representing the combined images.
        """
        return 2 * intensity * rgb + (1 - 2 * intensity) * rgb**2

    def blend_overlay(self, rgb, intensity):
        """
        Combine an RGB image with an intensity map using "overlay" blending.

        Parameters
        ----------
        rgb : `~numpy.ndarray`
            An (M, N, 3) RGB array of floats ranging from 0 to 1 (color image).
        intensity : `~numpy.ndarray`
            An (M, N, 1) array of floats ranging from 0 to 1 (grayscale image).

        Returns
        -------
        ndarray
            An (M, N, 3) RGB array representing the combined images.
        """
        low = 2 * intensity * rgb
        high = 1 - 2 * (1 - intensity) * (1 - rgb)
        return np.where(rgb <= 0.5, low, high)


def from_levels_and_colors(levels, colors, extend='neither'):
    """
    A helper routine to generate a cmap and a norm instance which
    behave similar to contourf's levels and colors arguments.

    Parameters
    ----------
    levels : sequence of numbers
        The quantization levels used to construct the `BoundaryNorm`.
        Value ``v`` is quantized to level ``i`` if ``lev[i] <= v < lev[i+1]``.
    colors : sequence of colors
        The fill color to use for each level. If *extend* is "neither" there
        must be ``n_level - 1`` colors. For an *extend* of "min" or "max" add
        one extra color, and for an *extend* of "both" add two colors.
    extend : {'neither', 'min', 'max', 'both'}, optional
        The behaviour when a value falls out of range of the given levels.
        See `~.Axes.contourf` for details.

    Returns
    -------
    cmap : `~matplotlib.colors.Colormap`
    norm : `~matplotlib.colors.Normalize`
    """
    slice_map = {
        'both': slice(1, -1),
        'min': slice(1, None),
        'max': slice(0, -1),
        'neither': slice(0, None),
    }
    _api.check_in_list(slice_map, extend=extend)
    color_slice = slice_map[extend]

    n_data_colors = len(levels) - 1
    n_expected = n_data_colors + color_slice.start - (color_slice.stop or 0)
    if len(colors) != n_expected:
        raise ValueError(
            f'With extend == {extend!r} and {len(levels)} levels, '
            f'expected {n_expected} colors, but got {len(colors)}')

    cmap = ListedColormap(colors[color_slice], N=n_data_colors)

    if extend in ['min', 'both']:
        cmap.set_under(colors[0])
    else:
        cmap.set_under('none')

    if extend in ['max', 'both']:
        cmap.set_over(colors[-1])
    else:
        cmap.set_over('none')

    cmap.colorbar_extend = extend

    norm = BoundaryNorm(levels, ncolors=n_data_colors)
    return cmap, norm

# === NexusCore/openenv\Lib\site-packages\pkg_resources\__init__.py ===
"""
Package resource API
--------------------

A resource is a logical file contained within a package, or a logical
subdirectory thereof.  The package resource API expects resource names
to have their path parts separated with ``/``, *not* whatever the local
path separator is.  Do not use os.path operations to manipulate resource
names being passed into the API.

The package resource API is designed to work with normal filesystem packages,
.egg files, and unpacked .egg files.  It can also work in a limited way with
.zip files and with custom PEP 302 loaders that support the ``get_data()``
method.

This module is deprecated. Users are directed to :mod:`importlib.resources`,
:mod:`importlib.metadata` and :pypi:`packaging` instead.
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 9):  # noqa: UP036 # Check for unsupported versions
    raise RuntimeError("Python 3.9 or later is required")

import _imp
import collections
import email.parser
import errno
import functools
import importlib
import importlib.abc
import importlib.machinery
import inspect
import io
import ntpath
import operator
import os
import pkgutil
import platform
import plistlib
import posixpath
import re
import stat
import tempfile
import textwrap
import time
import types
import warnings
import zipfile
import zipimport
from collections.abc import Iterable, Iterator, Mapping, MutableSequence
from pkgutil import get_importer
from typing import (
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Callable,
    Literal,
    NamedTuple,
    NoReturn,
    Protocol,
    TypeVar,
    Union,
    overload,
)

sys.path.extend(((vendor_path := os.path.join(os.path.dirname(os.path.dirname(__file__)), 'setuptools', '_vendor')) not in sys.path) * [vendor_path])  # fmt: skip
# workaround for #4476
sys.modules.pop('backports', None)

# capture these to bypass sandboxing
from os import open as os_open, utime  # isort: skip
from os.path import isdir, split  # isort: skip

try:
    from os import mkdir, rename, unlink

    WRITE_SUPPORT = True
except ImportError:
    # no write support, probably under GAE
    WRITE_SUPPORT = False

import packaging.markers
import packaging.requirements
import packaging.specifiers
import packaging.utils
import packaging.version
from jaraco.text import drop_comment, join_continuation, yield_lines
from platformdirs import user_cache_dir as _user_cache_dir

if TYPE_CHECKING:
    from _typeshed import BytesPath, StrOrBytesPath, StrPath
    from _typeshed.importlib import LoaderProtocol
    from typing_extensions import Self, TypeAlias

warnings.warn(
    "pkg_resources is deprecated as an API. "
    "See https://setuptools.pypa.io/en/latest/pkg_resources.html. "
    "The pkg_resources package is slated for removal as early as "
    "2025-11-30. Refrain from using this package or pin to "
    "Setuptools<81.",
    UserWarning,
    stacklevel=2,
)

_T = TypeVar("_T")
_DistributionT = TypeVar("_DistributionT", bound="Distribution")
# Type aliases
_NestedStr: TypeAlias = Union[str, Iterable[Union[str, Iterable["_NestedStr"]]]]
_StrictInstallerType: TypeAlias = Callable[["Requirement"], "_DistributionT"]
_InstallerType: TypeAlias = Callable[["Requirement"], Union["Distribution", None]]
_PkgReqType: TypeAlias = Union[str, "Requirement"]
_EPDistType: TypeAlias = Union["Distribution", _PkgReqType]
_MetadataType: TypeAlias = Union["IResourceProvider", None]
_ResolvedEntryPoint: TypeAlias = Any  # Can be any attribute in the module
_ResourceStream: TypeAlias = Any  # TODO / Incomplete: A readable file-like object
# Any object works, but let's indicate we expect something like a module (optionally has __loader__ or __file__)
_ModuleLike: TypeAlias = Union[object, types.ModuleType]
# Any: Should be _ModuleLike but we end up with issues where _ModuleLike doesn't have _ZipLoaderModule's __loader__
_ProviderFactoryType: TypeAlias = Callable[[Any], "IResourceProvider"]
_DistFinderType: TypeAlias = Callable[[_T, str, bool], Iterable["Distribution"]]
_NSHandlerType: TypeAlias = Callable[[_T, str, str, types.ModuleType], Union[str, None]]
_AdapterT = TypeVar(
    "_AdapterT", _DistFinderType[Any], _ProviderFactoryType, _NSHandlerType[Any]
)


class _ZipLoaderModule(Protocol):
    __loader__: zipimport.zipimporter


_PEP440_FALLBACK = re.compile(r"^v?(?P<safe>(?:[0-9]+!)?[0-9]+(?:\.[0-9]+)*)", re.I)


class PEP440Warning(RuntimeWarning):
    """
    Used when there is an issue with a version or specifier not complying with
    PEP 440.
    """


parse_version = packaging.version.Version

_state_vars: dict[str, str] = {}


def _declare_state(vartype: str, varname: str, initial_value: _T) -> _T:
    _state_vars[varname] = vartype
    return initial_value


def __getstate__() -> dict[str, Any]:
    state = {}
    g = globals()
    for k, v in _state_vars.items():
        state[k] = g['_sget_' + v](g[k])
    return state


def __setstate__(state: dict[str, Any]) -> dict[str, Any]:
    g = globals()
    for k, v in state.items():
        g['_sset_' + _state_vars[k]](k, g[k], v)
    return state


def _sget_dict(val):
    return val.copy()


def _sset_dict(key, ob, state) -> None:
    ob.clear()
    ob.update(state)


def _sget_object(val):
    return val.__getstate__()


def _sset_object(key, ob, state) -> None:
    ob.__setstate__(state)


_sget_none = _sset_none = lambda *args: None


def get_supported_platform():
    """Return this platform's maximum compatible version.

    distutils.util.get_platform() normally reports the minimum version
    of macOS that would be required to *use* extensions produced by
    distutils.  But what we want when checking compatibility is to know the
    version of macOS that we are *running*.  To allow usage of packages that
    explicitly require a newer version of macOS, we must also know the
    current version of the OS.

    If this condition occurs for any other platform with a version in its
    platform strings, this function should be extended accordingly.
    """
    plat = get_build_platform()
    m = macosVersionString.match(plat)
    if m is not None and sys.platform == "darwin":
        try:
            major_minor = '.'.join(_macos_vers()[:2])
            build = m.group(3)
            plat = f'macosx-{major_minor}-{build}'
        except ValueError:
            # not macOS
            pass
    return plat


__all__ = [
    # Basic resource access and distribution/entry point discovery
    'require',
    'run_script',
    'get_provider',
    'get_distribution',
    'load_entry_point',
    'get_entry_map',
    'get_entry_info',
    'iter_entry_points',
    'resource_string',
    'resource_stream',
    'resource_filename',
    'resource_listdir',
    'resource_exists',
    'resource_isdir',
    # Environmental control
    'declare_namespace',
    'working_set',
    'add_activation_listener',
    'find_distributions',
    'set_extraction_path',
    'cleanup_resources',
    'get_default_cache',
    # Primary implementation classes
    'Environment',
    'WorkingSet',
    'ResourceManager',
    'Distribution',
    'Requirement',
    'EntryPoint',
    # Exceptions
    'ResolutionError',
    'VersionConflict',
    'DistributionNotFound',
    'UnknownExtra',
    'ExtractionError',
    # Warnings
    'PEP440Warning',
    # Parsing functions and string utilities
    'parse_requirements',
    'parse_version',
    'safe_name',
    'safe_version',
    'get_platform',
    'compatible_platforms',
    'yield_lines',
    'split_sections',
    'safe_extra',
    'to_filename',
    'invalid_marker',
    'evaluate_marker',
    # filesystem utilities
    'ensure_directory',
    'normalize_path',
    # Distribution "precedence" constants
    'EGG_DIST',
    'BINARY_DIST',
    'SOURCE_DIST',
    'CHECKOUT_DIST',
    'DEVELOP_DIST',
    # "Provider" interfaces, implementations, and registration/lookup APIs
    'IMetadataProvider',
    'IResourceProvider',
    'FileMetadata',
    'PathMetadata',
    'EggMetadata',
    'EmptyProvider',
    'empty_provider',
    'NullProvider',
    'EggProvider',
    'DefaultProvider',
    'ZipProvider',
    'register_finder',
    'register_namespace_handler',
    'register_loader_type',
    'fixup_namespace_packages',
    'get_importer',
    # Warnings
    'PkgResourcesDeprecationWarning',
    # Deprecated/backward compatibility only
    'run_main',
    'AvailableDistributions',
]


class ResolutionError(Exception):
    """Abstract base for dependency resolution errors"""

    def __repr__(self) -> str:
        return self.__class__.__name__ + repr(self.args)


class VersionConflict(ResolutionError):
    """
    An already-installed version conflicts with the requested version.

    Should be initialized with the installed Distribution and the requested
    Requirement.
    """

    _template = "{self.dist} is installed but {self.req} is required"

    @property
    def dist(self) -> Distribution:
        return self.args[0]

    @property
    def req(self) -> Requirement:
        return self.args[1]

    def report(self):
        return self._template.format(**locals())

    def with_context(
        self, required_by: set[Distribution | str]
    ) -> Self | ContextualVersionConflict:
        """
        If required_by is non-empty, return a version of self that is a
        ContextualVersionConflict.
        """
        if not required_by:
            return self
        args = self.args + (required_by,)
        return ContextualVersionConflict(*args)


class ContextualVersionConflict(VersionConflict):
    """
    A VersionConflict that accepts a third parameter, the set of the
    requirements that required the installed Distribution.
    """

    _template = VersionConflict._template + ' by {self.required_by}'

    @property
    def required_by(self) -> set[str]:
        return self.args[2]


class DistributionNotFound(ResolutionError):
    """A requested distribution was not found"""

    _template = (
        "The '{self.req}' distribution was not found "
        "and is required by {self.requirers_str}"
    )

    @property
    def req(self) -> Requirement:
        return self.args[0]

    @property
    def requirers(self) -> set[str] | None:
        return self.args[1]

    @property
    def requirers_str(self):
        if not self.requirers:
            return 'the application'
        return ', '.join(self.requirers)

    def report(self):
        return self._template.format(**locals())

    def __str__(self) -> str:
        return self.report()


class UnknownExtra(ResolutionError):
    """Distribution doesn't have an "extra feature" of the given name"""


_provider_factories: dict[type[_ModuleLike], _ProviderFactoryType] = {}

PY_MAJOR = f'{sys.version_info.major}.{sys.version_info.minor}'
EGG_DIST = 3
BINARY_DIST = 2
SOURCE_DIST = 1
CHECKOUT_DIST = 0
DEVELOP_DIST = -1


def register_loader_type(
    loader_type: type[_ModuleLike], provider_factory: _ProviderFactoryType
) -> None:
    """Register `provider_factory` to make providers for `loader_type`

    `loader_type` is the type or class of a PEP 302 ``module.__loader__``,
    and `provider_factory` is a function that, passed a *module* object,
    returns an ``IResourceProvider`` for that module.
    """
    _provider_factories[loader_type] = provider_factory


@overload
def get_provider(moduleOrReq: str) -> IResourceProvider: ...
@overload
def get_provider(moduleOrReq: Requirement) -> Distribution: ...
def get_provider(moduleOrReq: str | Requirement) -> IResourceProvider | Distribution:
    """Return an IResourceProvider for the named module or requirement"""
    if isinstance(moduleOrReq, Requirement):
        return working_set.find(moduleOrReq) or require(str(moduleOrReq))[0]
    try:
        module = sys.modules[moduleOrReq]
    except KeyError:
        __import__(moduleOrReq)
        module = sys.modules[moduleOrReq]
    loader = getattr(module, '__loader__', None)
    return _find_adapter(_provider_factories, loader)(module)


@functools.cache
def _macos_vers():
    version = platform.mac_ver()[0]
    # fallback for MacPorts
    if version == '':
        plist = '/System/Library/CoreServices/SystemVersion.plist'
        if os.path.exists(plist):
            with open(plist, 'rb') as fh:
                plist_content = plistlib.load(fh)
            if 'ProductVersion' in plist_content:
                version = plist_content['ProductVersion']
    return version.split('.')


def _macos_arch(machine):
    return {'PowerPC': 'ppc', 'Power_Macintosh': 'ppc'}.get(machine, machine)


def get_build_platform():
    """Return this platform's string for platform-specific distributions"""
    from sysconfig import get_platform

    plat = get_platform()
    if sys.platform == "darwin" and not plat.startswith('macosx-'):
        try:
            version = _macos_vers()
            machine = _macos_arch(os.uname()[4].replace(" ", "_"))
            return f"macosx-{version[0]}.{version[1]}-{machine}"
        except ValueError:
            # if someone is running a non-Mac darwin system, this will fall
            # through to the default implementation
            pass
    return plat


macosVersionString = re.compile(r"macosx-(\d+)\.(\d+)-(.*)")
darwinVersionString = re.compile(r"darwin-(\d+)\.(\d+)\.(\d+)-(.*)")
# XXX backward compat
get_platform = get_build_platform


def compatible_platforms(provided: str | None, required: str | None) -> bool:
    """Can code for the `provided` platform run on the `required` platform?

    Returns true if either platform is ``None``, or the platforms are equal.

    XXX Needs compatibility checks for Linux and other unixy OSes.
    """
    if provided is None or required is None or provided == required:
        # easy case
        return True

    # macOS special cases
    reqMac = macosVersionString.match(required)
    if reqMac:
        provMac = macosVersionString.match(provided)

        # is this a Mac package?
        if not provMac:
            # this is backwards compatibility for packages built before
            # setuptools 0.6. All packages built after this point will
            # use the new macOS designation.
            provDarwin = darwinVersionString.match(provided)
            if provDarwin:
                dversion = int(provDarwin.group(1))
                macosversion = f"{reqMac.group(1)}.{reqMac.group(2)}"
                if (
                    dversion == 7
                    and macosversion >= "10.3"
                    or dversion == 8
                    and macosversion >= "10.4"
                ):
                    return True
            # egg isn't macOS or legacy darwin
            return False

        # are they the same major version and machine type?
        if provMac.group(1) != reqMac.group(1) or provMac.group(3) != reqMac.group(3):
            return False

        # is the required OS major update >= the provided one?
        if int(provMac.group(2)) > int(reqMac.group(2)):
            return False

        return True

    # XXX Linux and other platforms' special cases should go here
    return False


@overload
def get_distribution(dist: _DistributionT) -> _DistributionT: ...
@overload
def get_distribution(dist: _PkgReqType) -> Distribution: ...
def get_distribution(dist: Distribution | _PkgReqType) -> Distribution:
    """Return a current distribution object for a Requirement or string"""
    if isinstance(dist, str):
        dist = Requirement.parse(dist)
    if isinstance(dist, Requirement):
        dist = get_provider(dist)
    if not isinstance(dist, Distribution):
        raise TypeError("Expected str, Requirement, or Distribution", dist)
    return dist


def load_entry_point(dist: _EPDistType, group: str, name: str) -> _ResolvedEntryPoint:
    """Return `name` entry point of `group` for `dist` or raise ImportError"""
    return get_distribution(dist).load_entry_point(group, name)


@overload
def get_entry_map(
    dist: _EPDistType, group: None = None
) -> dict[str, dict[str, EntryPoint]]: ...
@overload
def get_entry_map(dist: _EPDistType, group: str) -> dict[str, EntryPoint]: ...
def get_entry_map(dist: _EPDistType, group: str | None = None):
    """Return the entry point map for `group`, or the full entry map"""
    return get_distribution(dist).get_entry_map(group)


def get_entry_info(dist: _EPDistType, group: str, name: str) -> EntryPoint | None:
    """Return the EntryPoint object for `group`+`name`, or ``None``"""
    return get_distribution(dist).get_entry_info(group, name)


class IMetadataProvider(Protocol):
    def has_metadata(self, name: str) -> bool:
        """Does the package's distribution contain the named metadata?"""
        ...

    def get_metadata(self, name: str) -> str:
        """The named metadata resource as a string"""
        ...

    def get_metadata_lines(self, name: str) -> Iterator[str]:
        """Yield named metadata resource as list of non-blank non-comment lines

        Leading and trailing whitespace is stripped from each line, and lines
        with ``#`` as the first non-blank character are omitted."""
        ...

    def metadata_isdir(self, name: str) -> bool:
        """Is the named metadata a directory?  (like ``os.path.isdir()``)"""
        ...

    def metadata_listdir(self, name: str) -> list[str]:
        """List of metadata names in the directory (like ``os.listdir()``)"""
        ...

    def run_script(self, script_name: str, namespace: dict[str, Any]) -> None:
        """Execute the named script in the supplied namespace dictionary"""
        ...


class IResourceProvider(IMetadataProvider, Protocol):
    """An object that provides access to package resources"""

    def get_resource_filename(
        self, manager: ResourceManager, resource_name: str
    ) -> str:
        """Return a true filesystem path for `resource_name`

        `manager` must be a ``ResourceManager``"""
        ...

    def get_resource_stream(
        self, manager: ResourceManager, resource_name: str
    ) -> _ResourceStream:
        """Return a readable file-like object for `resource_name`

        `manager` must be a ``ResourceManager``"""
        ...

    def get_resource_string(
        self, manager: ResourceManager, resource_name: str
    ) -> bytes:
        """Return the contents of `resource_name` as :obj:`bytes`

        `manager` must be a ``ResourceManager``"""
        ...

    def has_resource(self, resource_name: str) -> bool:
        """Does the package contain the named resource?"""
        ...

    def resource_isdir(self, resource_name: str) -> bool:
        """Is the named resource a directory?  (like ``os.path.isdir()``)"""
        ...

    def resource_listdir(self, resource_name: str) -> list[str]:
        """List of resource names in the directory (like ``os.listdir()``)"""
        ...


class WorkingSet:
    """A collection of active distributions on sys.path (or a similar list)"""

    def __init__(self, entries: Iterable[str] | None = None) -> None:
        """Create working set from list of path entries (default=sys.path)"""
        self.entries: list[str] = []
        self.entry_keys: dict[str | None, list[str]] = {}
        self.by_key: dict[str, Distribution] = {}
        self.normalized_to_canonical_keys: dict[str, str] = {}
        self.callbacks: list[Callable[[Distribution], object]] = []

        if entries is None:
            entries = sys.path

        for entry in entries:
            self.add_entry(entry)

    @classmethod
    def _build_master(cls):
        """
        Prepare the master working set.
        """
        ws = cls()
        try:
            from __main__ import __requires__
        except ImportError:
            # The main program does not list any requirements
            return ws

        # ensure the requirements are met
        try:
            ws.require(__requires__)
        except VersionConflict:
            return cls._build_from_requirements(__requires__)

        return ws

    @classmethod
    def _build_from_requirements(cls, req_spec):
        """
        Build a working set from a requirement spec. Rewrites sys.path.
        """
        # try it without defaults already on sys.path
        # by starting with an empty path
        ws = cls([])
        reqs = parse_requirements(req_spec)
        dists = ws.resolve(reqs, Environment())
        for dist in dists:
            ws.add(dist)

        # add any missing entries from sys.path
        for entry in sys.path:
            if entry not in ws.entries:
                ws.add_entry(entry)

        # then copy back to sys.path
        sys.path[:] = ws.entries
        return ws

    def add_entry(self, entry: str) -> None:
        """Add a path item to ``.entries``, finding any distributions on it

        ``find_distributions(entry, True)`` is used to find distributions
        corresponding to the path entry, and they are added.  `entry` is
        always appended to ``.entries``, even if it is already present.
        (This is because ``sys.path`` can contain the same value more than
        once, and the ``.entries`` of the ``sys.path`` WorkingSet should always
        equal ``sys.path``.)
        """
        self.entry_keys.setdefault(entry, [])
        self.entries.append(entry)
        for dist in find_distributions(entry, True):
            self.add(dist, entry, False)

    def __contains__(self, dist: Distribution) -> bool:
        """True if `dist` is the active distribution for its project"""
        return self.by_key.get(dist.key) == dist

    def find(self, req: Requirement) -> Distribution | None:
        """Find a distribution matching requirement `req`

        If there is an active distribution for the requested project, this
        returns it as long as it meets the version requirement specified by
        `req`.  But, if there is an active distribution for the project and it
        does *not* meet the `req` requirement, ``VersionConflict`` is raised.
        If there is no active distribution for the requested project, ``None``
        is returned.
        """
        dist: Distribution | None = None

        candidates = (
            req.key,
            self.normalized_to_canonical_keys.get(req.key),
            safe_name(req.key).replace(".", "-"),
        )

        for candidate in filter(None, candidates):
            dist = self.by_key.get(candidate)
            if dist:
                req.key = candidate
                break

        if dist is not None and dist not in req:
            # XXX add more info
            raise VersionConflict(dist, req)
        return dist

    def iter_entry_points(
        self, group: str, name: str | None = None
    ) -> Iterator[EntryPoint]:
        """Yield entry point objects from `group` matching `name`

        If `name` is None, yields all entry points in `group` from all
        distributions in the working set, otherwise only ones matching
        both `group` and `name` are yielded (in distribution order).
        """
        return (
            entry
            for dist in self
            for entry in dist.get_entry_map(group).values()
            if name is None or name == entry.name
        )

    def run_script(self, requires: str, script_name: str) -> None:
        """Locate distribution for `requires` and run `script_name` script"""
        ns = sys._getframe(1).f_globals
        name = ns['__name__']
        ns.clear()
        ns['__name__'] = name
        self.require(requires)[0].run_script(script_name, ns)

    def __iter__(self) -> Iterator[Distribution]:
        """Yield distributions for non-duplicate projects in the working set

        The yield order is the order in which the items' path entries were
        added to the working set.
        """
        seen = set()
        for item in self.entries:
            if item not in self.entry_keys:
                # workaround a cache issue
                continue

            for key in self.entry_keys[item]:
                if key not in seen:
                    seen.add(key)
                    yield self.by_key[key]

    def add(
        self,
        dist: Distribution,
        entry: str | None = None,
        insert: bool = True,
        replace: bool = False,
    ) -> None:
        """Add `dist` to working set, associated with `entry`

        If `entry` is unspecified, it defaults to the ``.location`` of `dist`.
        On exit from this routine, `entry` is added to the end of the working
        set's ``.entries`` (if it wasn't already present).

        `dist` is only added to the working set if it's for a project that
        doesn't already have a distribution in the set, unless `replace=True`.
        If it's added, any callbacks registered with the ``subscribe()`` method
        will be called.
        """
        if insert:
            dist.insert_on(self.entries, entry, replace=replace)

        if entry is None:
            entry = dist.location
        keys = self.entry_keys.setdefault(entry, [])
        keys2 = self.entry_keys.setdefault(dist.location, [])
        if not replace and dist.key in self.by_key:
            # ignore hidden distros
            return

        self.by_key[dist.key] = dist
        normalized_name = packaging.utils.canonicalize_name(dist.key)
        self.normalized_to_canonical_keys[normalized_name] = dist.key
        if dist.key not in keys:
            keys.append(dist.key)
        if dist.key not in keys2:
            keys2.append(dist.key)
        self._added_new(dist)

    @overload
    def resolve(
        self,
        requirements: Iterable[Requirement],
        env: Environment | None,
        installer: _StrictInstallerType[_DistributionT],
        replace_conflicting: bool = False,
        extras: tuple[str, ...] | None = None,
    ) -> list[_DistributionT]: ...
    @overload
    def resolve(
        self,
        requirements: Iterable[Requirement],
        env: Environment | None = None,
        *,
        installer: _StrictInstallerType[_DistributionT],
        replace_conflicting: bool = False,
        extras: tuple[str, ...] | None = None,
    ) -> list[_DistributionT]: ...
    @overload
    def resolve(
        self,
        requirements: Iterable[Requirement],
        env: Environment | None = None,
        installer: _InstallerType | None = None,
        replace_conflicting: bool = False,
        extras: tuple[str, ...] | None = None,
    ) -> list[Distribution]: ...
    def resolve(
        self,
        requirements: Iterable[Requirement],
        env: Environment | None = None,
        installer: _InstallerType | None | _StrictInstallerType[_DistributionT] = None,
        replace_conflicting: bool = False,
        extras: tuple[str, ...] | None = None,
    ) -> list[Distribution] | list[_DistributionT]:
        """List all distributions needed to (recursively) meet `requirements`

        `requirements` must be a sequence of ``Requirement`` objects.  `env`,
        if supplied, should be an ``Environment`` instance.  If
        not supplied, it defaults to all distributions available within any
        entry or distribution in the working set.  `installer`, if supplied,
        will be invoked with each requirement that cannot be met by an
        already-installed distribution; it should return a ``Distribution`` or
        ``None``.

        Unless `replace_conflicting=True`, raises a VersionConflict exception
        if
        any requirements are found on the path that have the correct name but
        the wrong version.  Otherwise, if an `installer` is supplied it will be
        invoked to obtain the correct version of the requirement and activate
        it.

        `extras` is a list of the extras to be used with these requirements.
        This is important because extra requirements may look like `my_req;
        extra = "my_extra"`, which would otherwise be interpreted as a purely
        optional requirement.  Instead, we want to be able to assert that these
        requirements are truly required.
        """

        # set up the stack
        requirements = list(requirements)[::-1]
        # set of processed requirements
        processed = set()
        # key -> dist
        best: dict[str, Distribution] = {}
        to_activate: list[Distribution] = []

        req_extras = _ReqExtras()

        # Mapping of requirement to set of distributions that required it;
        # useful for reporting info about conflicts.
        required_by = collections.defaultdict[Requirement, set[str]](set)

        while requirements:
            # process dependencies breadth-first
            req = requirements.pop(0)
            if req in processed:
                # Ignore cyclic or redundant dependencies
                continue

            if not req_extras.markers_pass(req, extras):
                continue

            dist = self._resolve_dist(
                req, best, replace_conflicting, env, installer, required_by, to_activate
            )

            # push the new requirements onto the stack
            new_requirements = dist.requires(req.extras)[::-1]
            requirements.extend(new_requirements)

            # Register the new requirements needed by req
            for new_requirement in new_requirements:
                required_by[new_requirement].add(req.project_name)
                req_extras[new_requirement] = req.extras

            processed.add(req)

        # return list of distros to activate
        return to_activate

    def _resolve_dist(
        self, req, best, replace_conflicting, env, installer, required_by, to_activate
    ) -> Distribution:
        dist = best.get(req.key)
        if dist is None:
            # Find the best distribution and add it to the map
            dist = self.by_key.get(req.key)
            if dist is None or (dist not in req and replace_conflicting):
                ws = self
                if env is None:
                    if dist is None:
                        env = Environment(self.entries)
                    else:
                        # Use an empty environment and workingset to avoid
                        # any further conflicts with the conflicting
                        # distribution
                        env = Environment([])
                        ws = WorkingSet([])
                dist = best[req.key] = env.best_match(
                    req, ws, installer, replace_conflicting=replace_conflicting
                )
                if dist is None:
                    requirers = required_by.get(req, None)
                    raise DistributionNotFound(req, requirers)
            to_activate.append(dist)
        if dist not in req:
            # Oops, the "best" so far conflicts with a dependency
            dependent_req = required_by[req]
            raise VersionConflict(dist, req).with_context(dependent_req)
        return dist

    @overload
    def find_plugins(
        self,
        plugin_env: Environment,
        full_env: Environment | None,
        installer: _StrictInstallerType[_DistributionT],
        fallback: bool = True,
    ) -> tuple[list[_DistributionT], dict[Distribution, Exception]]: ...
    @overload
    def find_plugins(
        self,
        plugin_env: Environment,
        full_env: Environment | None = None,
        *,
        installer: _StrictInstallerType[_DistributionT],
        fallback: bool = True,
    ) -> tuple[list[_DistributionT], dict[Distribution, Exception]]: ...
    @overload
    def find_plugins(
        self,
        plugin_env: Environment,
        full_env: Environment | None = None,
        installer: _InstallerType | None = None,
        fallback: bool = True,
    ) -> tuple[list[Distribution], dict[Distribution, Exception]]: ...
    def find_plugins(
        self,
        plugin_env: Environment,
        full_env: Environment | None = None,
        installer: _InstallerType | None | _StrictInstallerType[_DistributionT] = None,
        fallback: bool = True,
    ) -> tuple[
        list[Distribution] | list[_DistributionT],
        dict[Distribution, Exception],
    ]:
        """Find all activatable distributions in `plugin_env`

        Example usage::

            distributions, errors = working_set.find_plugins(
                Environment(plugin_dirlist)
            )
            # add plugins+libs to sys.path
            map(working_set.add, distributions)
            # display errors
            print('Could not load', errors)

        The `plugin_env` should be an ``Environment`` instance that contains
        only distributions that are in the project's "plugin directory" or
        directories. The `full_env`, if supplied, should be an ``Environment``
        contains all currently-available distributions.  If `full_env` is not
        supplied, one is created automatically from the ``WorkingSet`` this
        method is called on, which will typically mean that every directory on
        ``sys.path`` will be scanned for distributions.

        `installer` is a standard installer callback as used by the
        ``resolve()`` method. The `fallback` flag indicates whether we should
        attempt to resolve older versions of a plugin if the newest version
        cannot be resolved.

        This method returns a 2-tuple: (`distributions`, `error_info`), where
        `distributions` is a list of the distributions found in `plugin_env`
        that were loadable, along with any other distributions that are needed
        to resolve their dependencies.  `error_info` is a dictionary mapping
        unloadable plugin distributions to an exception instance describing the
        error that occurred. Usually this will be a ``DistributionNotFound`` or
        ``VersionConflict`` instance.
        """

        plugin_projects = list(plugin_env)
        # scan project names in alphabetic order
        plugin_projects.sort()

        error_info: dict[Distribution, Exception] = {}
        distributions: dict[Distribution, Exception | None] = {}

        if full_env is None:
            env = Environment(self.entries)
            env += plugin_env
        else:
            env = full_env + plugin_env

        shadow_set = self.__class__([])
        # put all our entries in shadow_set
        list(map(shadow_set.add, self))

        for project_name in plugin_projects:
            for dist in plugin_env[project_name]:
                req = [dist.as_requirement()]

                try:
                    resolvees = shadow_set.resolve(req, env, installer)

                except ResolutionError as v:
                    # save error info
                    error_info[dist] = v
                    if fallback:
                        # try the next older version of project
                        continue
                    else:
                        # give up on this project, keep going
                        break

                else:
                    list(map(shadow_set.add, resolvees))
                    distributions.update(dict.fromkeys(resolvees))

                    # success, no need to try any more versions of this project
                    break

        sorted_distributions = list(distributions)
        sorted_distributions.sort()

        return sorted_distributions, error_info

    def require(self, *requirements: _NestedStr) -> list[Distribution]:
        """Ensure that distributions matching `requirements` are activated

        `requirements` must be a string or a (possibly-nested) sequence
        thereof, specifying the distributions and versions required.  The
        return value is a sequence of the distributions that needed to be
        activated to fulfill the requirements; all relevant distributions are
        included, even if they were already activated in this working set.
        """
        needed = self.resolve(parse_requirements(requirements))

        for dist in needed:
            self.add(dist)

        return needed

    def subscribe(
        self, callback: Callable[[Distribution], object], existing: bool = True
    ) -> None:
        """Invoke `callback` for all distributions

        If `existing=True` (default),
        call on all existing ones, as well.
        """
        if callback in self.callbacks:
            return
        self.callbacks.append(callback)
        if not existing:
            return
        for dist in self:
            callback(dist)

    def _added_new(self, dist) -> None:
        for callback in self.callbacks:
            callback(dist)

    def __getstate__(
        self,
    ) -> tuple[
        list[str],
        dict[str | None, list[str]],
        dict[str, Distribution],
        dict[str, str],
        list[Callable[[Distribution], object]],
    ]:
        return (
            self.entries[:],
            self.entry_keys.copy(),
            self.by_key.copy(),
            self.normalized_to_canonical_keys.copy(),
            self.callbacks[:],
        )

    def __setstate__(self, e_k_b_n_c) -> None:
        entries, keys, by_key, normalized_to_canonical_keys, callbacks = e_k_b_n_c
        self.entries = entries[:]
        self.entry_keys = keys.copy()
        self.by_key = by_key.copy()
        self.normalized_to_canonical_keys = normalized_to_canonical_keys.copy()
        self.callbacks = callbacks[:]


class _ReqExtras(dict["Requirement", tuple[str, ...]]):
    """
    Map each requirement to the extras that demanded it.
    """

    def markers_pass(self, req: Requirement, extras: tuple[str, ...] | None = None):
        """
        Evaluate markers for req against each extra that
        demanded it.

        Return False if the req has a marker and fails
        evaluation. Otherwise, return True.
        """
        return not req.marker or any(
            req.marker.evaluate({'extra': extra})
            for extra in self.get(req, ()) + (extras or ("",))
        )


class Environment:
    """Searchable snapshot of distributions on a search path"""

    def __init__(
        self,
        search_path: Iterable[str] | None = None,
        platform: str | None = get_supported_platform(),
        python: str | None = PY_MAJOR,
    ) -> None:
        """Snapshot distributions available on a search path

        Any distributions found on `search_path` are added to the environment.
        `search_path` should be a sequence of ``sys.path`` items.  If not
        supplied, ``sys.path`` is used.

        `platform` is an optional string specifying the name of the platform
        that platform-specific distributions must be compatible with.  If
        unspecified, it defaults to the current platform.  `python` is an
        optional string naming the desired version of Python (e.g. ``'3.6'``);
        it defaults to the current version.

        You may explicitly set `platform` (and/or `python`) to ``None`` if you
        wish to map *all* distributions, not just those compatible with the
        running platform or Python version.
        """
        self._distmap: dict[str, list[Distribution]] = {}
        self.platform = platform
        self.python = python
        self.scan(search_path)

    def can_add(self, dist: Distribution) -> bool:
        """Is distribution `dist` acceptable for this environment?

        The distribution must match the platform and python version
        requirements specified when this environment was created, or False
        is returned.
        """
        py_compat = (
            self.python is None
            or dist.py_version is None
            or dist.py_version == self.python
        )
        return py_compat and compatible_platforms(dist.platform, self.platform)

    def remove(self, dist: Distribution) -> None:
        """Remove `dist` from the environment"""
        self._distmap[dist.key].remove(dist)

    def scan(self, search_path: Iterable[str] | None = None) -> None:
        """Scan `search_path` for distributions usable in this environment

        Any distributions found are added to the environment.
        `search_path` should be a sequence of ``sys.path`` items.  If not
        supplied, ``sys.path`` is used.  Only distributions conforming to
        the platform/python version defined at initialization are added.
        """
        if search_path is None:
            search_path = sys.path

        for item in search_path:
            for dist in find_distributions(item):
                self.add(dist)

    def __getitem__(self, project_name: str) -> list[Distribution]:
        """Return a newest-to-oldest list of distributions for `project_name`

        Uses case-insensitive `project_name` comparison, assuming all the
        project's distributions use their project's name converted to all
        lowercase as their key.

        """
        distribution_key = project_name.lower()
        return self._distmap.get(distribution_key, [])

    def add(self, dist: Distribution) -> None:
        """Add `dist` if we ``can_add()`` it and it has not already been added"""
        if self.can_add(dist) and dist.has_version():
            dists = self._distmap.setdefault(dist.key, [])
            if dist not in dists:
                dists.append(dist)
                dists.sort(key=operator.attrgetter('hashcmp'), reverse=True)

    @overload
    def best_match(
        self,
        req: Requirement,
        working_set: WorkingSet,
        installer: _StrictInstallerType[_DistributionT],
        replace_conflicting: bool = False,
    ) -> _DistributionT: ...
    @overload
    def best_match(
        self,
        req: Requirement,
        working_set: WorkingSet,
        installer: _InstallerType | None = None,
        replace_conflicting: bool = False,
    ) -> Distribution | None: ...
    def best_match(
        self,
        req: Requirement,
        working_set: WorkingSet,
        installer: _InstallerType | None | _StrictInstallerType[_DistributionT] = None,
        replace_conflicting: bool = False,
    ) -> Distribution | None:
        """Find distribution best matching `req` and usable on `working_set`

        This calls the ``find(req)`` method of the `working_set` to see if a
        suitable distribution is already active.  (This may raise
        ``VersionConflict`` if an unsuitable version of the project is already
        active in the specified `working_set`.)  If a suitable distribution
        isn't active, this method returns the newest distribution in the
        environment that meets the ``Requirement`` in `req`.  If no suitable
        distribution is found, and `installer` is supplied, then the result of
        calling the environment's ``obtain(req, installer)`` method will be
        returned.
        """
        try:
            dist = working_set.find(req)
        except VersionConflict:
            if not replace_conflicting:
                raise
            dist = None
        if dist is not None:
            return dist
        for dist in self[req.key]:
            if dist in req:
                return dist
        # try to download/install
        return self.obtain(req, installer)

    @overload
    def obtain(
        self,
        requirement: Requirement,
        installer: _StrictInstallerType[_DistributionT],
    ) -> _DistributionT: ...
    @overload
    def obtain(
        self,
        requirement: Requirement,
        installer: Callable[[Requirement], None] | None = None,
    ) -> None: ...
    @overload
    def obtain(
        self,
        requirement: Requirement,
        installer: _InstallerType | None = None,
    ) -> Distribution | None: ...
    def obtain(
        self,
        requirement: Requirement,
        installer: Callable[[Requirement], None]
        | _InstallerType
        | None
        | _StrictInstallerType[_DistributionT] = None,
    ) -> Distribution | None:
        """Obtain a distribution matching `requirement` (e.g. via download)

        Obtain a distro that matches requirement (e.g. via download).  In the
        base ``Environment`` class, this routine just returns
        ``installer(requirement)``, unless `installer` is None, in which case
        None is returned instead.  This method is a hook that allows subclasses
        to attempt other ways of obtaining a distribution before falling back
        to the `installer` argument."""
        return installer(requirement) if installer else None

    def __iter__(self) -> Iterator[str]:
        """Yield the unique project names of the available distributions"""
        for key in self._distmap.keys():
            if self[key]:
                yield key

    def __iadd__(self, other: Distribution | Environment) -> Self:
        """In-place addition of a distribution or environment"""
        if isinstance(other, Distribution):
            self.add(other)
        elif isinstance(other, Environment):
            for project in other:
                for dist in other[project]:
                    self.add(dist)
        else:
            raise TypeError(f"Can't add {other!r} to environment")
        return self

    def __add__(self, other: Distribution | Environment) -> Self:
        """Add an environment or distribution to an environment"""
        new = self.__class__([], platform=None, python=None)
        for env in self, other:
            new += env
        return new


# XXX backward compatibility
AvailableDistributions = Environment


class ExtractionError(RuntimeError):
    """An error occurred extracting a resource

    The following attributes are available from instances of this exception:

    manager
        The resource manager that raised this exception

    cache_path
        The base directory for resource extraction

    original_error
        The exception instance that caused extraction to fail
    """

    manager: ResourceManager
    cache_path: str
    original_error: BaseException | None


class ResourceManager:
    """Manage resource extraction and packages"""

    extraction_path: str | None = None

    def __init__(self) -> None:
        # acts like a set
        self.cached_files: dict[str, Literal[True]] = {}

    def resource_exists(
        self, package_or_requirement: _PkgReqType, resource_name: str
    ) -> bool:
        """Does the named resource exist?"""
        return get_provider(package_or_requirement).has_resource(resource_name)

    def resource_isdir(
        self, package_or_requirement: _PkgReqType, resource_name: str
    ) -> bool:
        """Is the named resource an existing directory?"""
        return get_provider(package_or_requirement).resource_isdir(resource_name)

    def resource_filename(
        self, package_or_requirement: _PkgReqType, resource_name: str
    ) -> str:
        """Return a true filesystem path for specified resource"""
        return get_provider(package_or_requirement).get_resource_filename(
            self, resource_name
        )

    def resource_stream(
        self, package_or_requirement: _PkgReqType, resource_name: str
    ) -> _ResourceStream:
        """Return a readable file-like object for specified resource"""
        return get_provider(package_or_requirement).get_resource_stream(
            self, resource_name
        )

    def resource_string(
        self, package_or_requirement: _PkgReqType, resource_name: str
    ) -> bytes:
        """Return specified resource as :obj:`bytes`"""
        return get_provider(package_or_requirement).get_resource_string(
            self, resource_name
        )

    def resource_listdir(
        self, package_or_requirement: _PkgReqType, resource_name: str
    ) -> list[str]:
        """List the contents of the named resource directory"""
        return get_provider(package_or_requirement).resource_listdir(resource_name)

    def extraction_error(self) -> NoReturn:
        """Give an error message for problems extracting file(s)"""

        old_exc = sys.exc_info()[1]
        cache_path = self.extraction_path or get_default_cache()

        tmpl = textwrap.dedent(
            """
            Can't extract file(s) to egg cache

            The following error occurred while trying to extract file(s)
            to the Python egg cache:

              {old_exc}

            The Python egg cache directory is currently set to:

              {cache_path}

            Perhaps your account does not have write access to this directory?
            You can change the cache directory by setting the PYTHON_EGG_CACHE
            environment variable to point to an accessible directory.
            """
        ).lstrip()
        err = ExtractionError(tmpl.format(**locals()))
        err.manager = self
        err.cache_path = cache_path
        err.original_error = old_exc
        raise err

    def get_cache_path(self, archive_name: str, names: Iterable[StrPath] = ()) -> str:
        """Return absolute location in cache for `archive_name` and `names`

        The parent directory of the resulting path will be created if it does
        not already exist.  `archive_name` should be the base filename of the
        enclosing egg (which may not be the name of the enclosing zipfile!),
        including its ".egg" extension.  `names`, if provided, should be a
        sequence of path name parts "under" the egg's extraction location.

        This method should only be called by resource providers that need to
        obtain an extraction location, and only for names they intend to
        extract, as it tracks the generated names for possible cleanup later.
        """
        extract_path = self.extraction_path or get_default_cache()
        target_path = os.path.join(extract_path, archive_name + '-tmp', *names)
        try:
            _bypass_ensure_directory(target_path)
        except Exception:
            self.extraction_error()

        self._warn_unsafe_extraction_path(extract_path)

        self.cached_files[target_path] = True
        return target_path

    @staticmethod
    def _warn_unsafe_extraction_path(path) -> None:
        """
        If the default extraction path is overridden and set to an insecure
        location, such as /tmp, it opens up an opportunity for an attacker to
        replace an extracted file with an unauthorized payload. Warn the user
        if a known insecure location is used.

        See Distribute #375 for more details.
        """
        if os.name == 'nt' and not path.startswith(os.environ['windir']):
            # On Windows, permissions are generally restrictive by default
            #  and temp directories are not writable by other users, so
            #  bypass the warning.
            return
        mode = os.stat(path).st_mode
        if mode & stat.S_IWOTH or mode & stat.S_IWGRP:
            msg = (
                "Extraction path is writable by group/others "
                "and vulnerable to attack when "
                "used with get_resource_filename ({path}). "
                "Consider a more secure "
                "location (set with .set_extraction_path or the "
                "PYTHON_EGG_CACHE environment variable)."
            ).format(**locals())
            warnings.warn(msg, UserWarning)

    def postprocess(self, tempname: StrOrBytesPath, filename: StrOrBytesPath) -> None:
        """Perform any platform-specific postprocessing of `tempname`

        This is where Mac header rewrites should be done; other platforms don't
        have anything special they should do.

        Resource providers should call this method ONLY after successfully
        extracting a compressed resource.  They must NOT call it on resources
        that are already in the filesystem.

        `tempname` is the current (temporary) name of the file, and `filename`
        is the name it will be renamed to by the caller after this routine
        returns.
        """

        if os.name == 'posix':
            # Make the resource executable
            mode = ((os.stat(tempname).st_mode) | 0o555) & 0o7777
            os.chmod(tempname, mode)

    def set_extraction_path(self, path: str) -> None:
        """Set the base path where resources will be extracted to, if needed.

        If you do not call this routine before any extractions take place, the
        path defaults to the return value of ``get_default_cache()``.  (Which
        is based on the ``PYTHON_EGG_CACHE`` environment variable, with various
        platform-specific fallbacks.  See that routine's documentation for more
        details.)

        Resources are extracted to subdirectories of this path based upon
        information given by the ``IResourceProvider``.  You may set this to a
        temporary directory, but then you must call ``cleanup_resources()`` to
        delete the extracted files when done.  There is no guarantee that
        ``cleanup_resources()`` will be able to remove all extracted files.

        (Note: you may not change the extraction path for a given resource
        manager once resources have been extracted, unless you first call
        ``cleanup_resources()``.)
        """
        if self.cached_files:
            raise ValueError("Can't change extraction path, files already extracted")

        self.extraction_path = path

    def cleanup_resources(self, force: bool = False) -> list[str]:
        """
        Delete all extracted resource files and directories, returning a list
        of the file and directory names that could not be successfully removed.
        This function does not have any concurrency protection, so it should
        generally only be called when the extraction path is a temporary
        directory exclusive to a single process.  This method is not
        automatically called; you must call it explicitly or register it as an
        ``atexit`` function if you wish to ensure cleanup of a temporary
        directory used for extractions.
        """
        # XXX
        return []


def get_default_cache() -> str:
    """
    Return the ``PYTHON_EGG_CACHE`` environment variable
    or a platform-relevant user cache dir for an app
    named "Python-Eggs".
    """
    return os.environ.get('PYTHON_EGG_CACHE') or _user_cache_dir(appname='Python-Eggs')


def safe_name(name: str) -> str:
    """Convert an arbitrary string to a standard distribution name

    Any runs of non-alphanumeric/. characters are replaced with a single '-'.
    """
    return re.sub('[^A-Za-z0-9.]+', '-', name)


def safe_version(version: str) -> str:
    """
    Convert an arbitrary string to a standard version string
    """
    try:
        # normalize the version
        return str(packaging.version.Version(version))
    except packaging.version.InvalidVersion:
        version = version.replace(' ', '.')
        return re.sub('[^A-Za-z0-9.]+', '-', version)


def _forgiving_version(version) -> str:
    """Fallback when ``safe_version`` is not safe enough
    >>> parse_version(_forgiving_version('0.23ubuntu1'))
    <Version('0.23.dev0+sanitized.ubuntu1')>
    >>> parse_version(_forgiving_version('0.23-'))
    <Version('0.23.dev0+sanitized')>
    >>> parse_version(_forgiving_version('0.-_'))
    <Version('0.dev0+sanitized')>
    >>> parse_version(_forgiving_version('42.+?1'))
    <Version('42.dev0+sanitized.1')>
    >>> parse_version(_forgiving_version('hello world'))
    <Version('0.dev0+sanitized.hello.world')>
    """
    version = version.replace(' ', '.')
    match = _PEP440_FALLBACK.search(version)
    if match:
        safe = match["safe"]
        rest = version[len(safe) :]
    else:
        safe = "0"
        rest = version
    local = f"sanitized.{_safe_segment(rest)}".strip(".")
    return f"{safe}.dev0+{local}"


def _safe_segment(segment):
    """Convert an arbitrary string into a safe segment"""
    segment = re.sub('[^A-Za-z0-9.]+', '-', segment)
    segment = re.sub('-[^A-Za-z0-9]+', '-', segment)
    return re.sub(r'\.[^A-Za-z0-9]+', '.', segment).strip(".-")


def safe_extra(extra: str) -> str:
    """Convert an arbitrary string to a standard 'extra' name

    Any runs of non-alphanumeric characters are replaced with a single '_',
    and the result is always lowercased.
    """
    return re.sub('[^A-Za-z0-9.-]+', '_', extra).lower()


def to_filename(name: str) -> str:
    """Convert a project or version name to its filename-escaped form

    Any '-' characters are currently replaced with '_'.
    """
    return name.replace('-', '_')


def invalid_marker(text: str) -> SyntaxError | Literal[False]:
    """
    Validate text as a PEP 508 environment marker; return an exception
    if invalid or False otherwise.
    """
    try:
        evaluate_marker(text)
    except SyntaxError as e:
        e.filename = None
        e.lineno = None
        return e
    return False


def evaluate_marker(text: str, extra: str | None = None) -> bool:
    """
    Evaluate a PEP 508 environment marker.
    Return a boolean indicating the marker result in this environment.
    Raise SyntaxError if marker is invalid.

    This implementation uses the 'pyparsing' module.
    """
    try:
        marker = packaging.markers.Marker(text)
        return marker.evaluate()
    except packaging.markers.InvalidMarker as e:
        raise SyntaxError(e) from e


class NullProvider:
    """Try to implement resources and metadata for arbitrary PEP 302 loaders"""

    egg_name: str | None = None
    egg_info: str | None = None
    loader: LoaderProtocol | None = None

    def __init__(self, module: _ModuleLike) -> None:
        self.loader = getattr(module, '__loader__', None)
        self.module_path = os.path.dirname(getattr(module, '__file__', ''))

    def get_resource_filename(
        self, manager: ResourceManager, resource_name: str
    ) -> str:
        return self._fn(self.module_path, resource_name)

    def get_resource_stream(
        self, manager: ResourceManager, resource_name: str
    ) -> BinaryIO:
        return io.BytesIO(self.get_resource_string(manager, resource_name))

    def get_resource_string(
        self, manager: ResourceManager, resource_name: str
    ) -> bytes:
        return self._get(self._fn(self.module_path, resource_name))

    def has_resource(self, resource_name: str) -> bool:
        return self._has(self._fn(self.module_path, resource_name))

    def _get_metadata_path(self, name):
        return self._fn(self.egg_info, name)

    def has_metadata(self, name: str) -> bool:
        if not self.egg_info:
            return False

        path = self._get_metadata_path(name)
        return self._has(path)

    def get_metadata(self, name: str) -> str:
        if not self.egg_info:
            return ""
        path = self._get_metadata_path(name)
        value = self._get(path)
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError as exc:
            # Include the path in the error message to simplify
            # troubleshooting, and without changing the exception type.
            exc.reason += f' in {name} file at path: {path}'
            raise

    def get_metadata_lines(self, name: str) -> Iterator[str]:
        return yield_lines(self.get_metadata(name))

    def resource_isdir(self, resource_name: str) -> bool:
        return self._isdir(self._fn(self.module_path, resource_name))

    def metadata_isdir(self, name: str) -> bool:
        return bool(self.egg_info and self._isdir(self._fn(self.egg_info, name)))

    def resource_listdir(self, resource_name: str) -> list[str]:
        return self._listdir(self._fn(self.module_path, resource_name))

    def metadata_listdir(self, name: str) -> list[str]:
        if self.egg_info:
            return self._listdir(self._fn(self.egg_info, name))
        return []

    def run_script(self, script_name: str, namespace: dict[str, Any]) -> None:
        script = 'scripts/' + script_name
        if not self.has_metadata(script):
            raise ResolutionError(
                "Script {script!r} not found in metadata at {self.egg_info!r}".format(
                    **locals()
                ),
            )

        script_text = self.get_metadata(script).replace('\r\n', '\n')
        script_text = script_text.replace('\r', '\n')
        script_filename = self._fn(self.egg_info, script)
        namespace['__file__'] = script_filename
        if os.path.exists(script_filename):
            source = _read_utf8_with_fallback(script_filename)
            code = compile(source, script_filename, 'exec')
            exec(code, namespace, namespace)
        else:
            from linecache import cache

            cache[script_filename] = (
                len(script_text),
                0,
                script_text.split('\n'),
                script_filename,
            )
            script_code = compile(script_text, script_filename, 'exec')
            exec(script_code, namespace, namespace)

    def _has(self, path) -> bool:
        raise NotImplementedError(
            "Can't perform this operation for unregistered loader type"
        )

    def _isdir(self, path) -> bool:
        raise NotImplementedError(
            "Can't perform this operation for unregistered loader type"
        )

    def _listdir(self, path) -> list[str]:
        raise NotImplementedError(
            "Can't perform this operation for unregistered loader type"
        )

    def _fn(self, base: str | None, resource_name: str):
        if base is None:
            raise TypeError(
                "`base` parameter in `_fn` is `None`. Either override this method or check the parameter first."
            )
        self._validate_resource_path(resource_name)
        if resource_name:
            return os.path.join(base, *resource_name.split('/'))
        return base

    @staticmethod
    def _validate_resource_path(path) -> None:
        """
        Validate the resource paths according to the docs.
        https://setuptools.pypa.io/en/latest/pkg_resources.html#basic-resource-access

        >>> warned = getfixture('recwarn')
        >>> warnings.simplefilter('always')
        >>> vrp = NullProvider._validate_resource_path
        >>> vrp('foo/bar.txt')
        >>> bool(warned)
        False
        >>> vrp('../foo/bar.txt')
        >>> bool(warned)
        True
        >>> warned.clear()
        >>> vrp('/foo/bar.txt')
        >>> bool(warned)
        True
        >>> vrp('foo/../../bar.txt')
        >>> bool(warned)
        True
        >>> warned.clear()
        >>> vrp('foo/f../bar.txt')
        >>> bool(warned)
        False

        Windows path separators are straight-up disallowed.
        >>> vrp(r'\\foo/bar.txt')
        Traceback (most recent call last):
        ...
        ValueError: Use of .. or absolute path in a resource path \
is not allowed.

        >>> vrp(r'C:\\foo/bar.txt')
        Traceback (most recent call last):
        ...
        ValueError: Use of .. or absolute path in a resource path \
is not allowed.

        Blank values are allowed

        >>> vrp('')
        >>> bool(warned)
        False

        Non-string values are not.

        >>> vrp(None)
        Traceback (most recent call last):
        ...
        AttributeError: ...
        """
        invalid = (
            os.path.pardir in path.split(posixpath.sep)
            or posixpath.isabs(path)
            or ntpath.isabs(path)
            or path.startswith("\\")
        )
        if not invalid:
            return

        msg = "Use of .. or absolute path in a resource path is not allowed."

        # Aggressively disallow Windows absolute paths
        if (path.startswith("\\") or ntpath.isabs(path)) and not posixpath.isabs(path):
            raise ValueError(msg)

        # for compatibility, warn; in future
        # raise ValueError(msg)
        issue_warning(
            msg[:-1] + " and will raise exceptions in a future release.",
            DeprecationWarning,
        )

    def _get(self, path) -> bytes:
        if hasattr(self.loader, 'get_data') and self.loader:
            # Already checked get_data exists
            return self.loader.get_data(path)  # type: ignore[attr-defined]
        raise NotImplementedError(
            "Can't perform this operation for loaders without 'get_data()'"
        )


register_loader_type(object, NullProvider)


def _parents(path):
    """
    yield all parents of path including path
    """
    last = None
    while path != last:
        yield path
        last = path
        path, _ = os.path.split(path)


class EggProvider(NullProvider):
    """Provider based on a virtual filesystem"""

    def __init__(self, module: _ModuleLike) -> None:
        super().__init__(module)
        self._setup_prefix()

    def _setup_prefix(self):
        # Assume that metadata may be nested inside a "basket"
        # of multiple eggs and use module_path instead of .archive.
        eggs = filter(_is_egg_path, _parents(self.module_path))
        egg = next(eggs, None)
        egg and self._set_egg(egg)

    def _set_egg(self, path: str) -> None:
        self.egg_name = os.path.basename(path)
        self.egg_info = os.path.join(path, 'EGG-INFO')
        self.egg_root = path


class DefaultProvider(EggProvider):
    """Provides access to package resources in the filesystem"""

    def _has(self, path) -> bool:
        return os.path.exists(path)

    def _isdir(self, path) -> bool:
        return os.path.isdir(path)

    def _listdir(self, path):
        return os.listdir(path)

    def get_resource_stream(
        self, manager: object, resource_name: str
    ) -> io.BufferedReader:
        return open(self._fn(self.module_path, resource_name), 'rb')

    def _get(self, path) -> bytes:
        with open(path, 'rb') as stream:
            return stream.read()

    @classmethod
    def _register(cls) -> None:
        loader_names = (
            'SourceFileLoader',
            'SourcelessFileLoader',
        )
        for name in loader_names:
            loader_cls = getattr(importlib.machinery, name, type(None))
            register_loader_type(loader_cls, cls)


DefaultProvider._register()


class EmptyProvider(NullProvider):
    """Provider that returns nothing for all requests"""

    # A special case, we don't want all Providers inheriting from NullProvider to have a potentially None module_path
    module_path: str | None = None  # type: ignore[assignment]

    _isdir = _has = lambda self, path: False

    def _get(self, path) -> bytes:
        return b''

    def _listdir(self, path):
        return []

    def __init__(self) -> None:
        pass


empty_provider = EmptyProvider()


class ZipManifests(dict[str, "MemoizedZipManifests.manifest_mod"]):
    """
    zip manifest builder
    """

    # `path` could be `StrPath | IO[bytes]` but that violates the LSP for `MemoizedZipManifests.load`
    @classmethod
    def build(cls, path: str) -> dict[str, zipfile.ZipInfo]:
        """
        Build a dictionary similar to the zipimport directory
        caches, except instead of tuples, store ZipInfo objects.

        Use a platform-specific path separator (os.sep) for the path keys
        for compatibility with pypy on Windows.
        """
        with zipfile.ZipFile(path) as zfile:
            items = (
                (
                    name.replace('/', os.sep),
                    zfile.getinfo(name),
                )
                for name in zfile.namelist()
            )
            return dict(items)

    load = build


class MemoizedZipManifests(ZipManifests):
    """
    Memoized zipfile manifests.
    """

    class manifest_mod(NamedTuple):
        manifest: dict[str, zipfile.ZipInfo]
        mtime: float

    def load(self, path: str) -> dict[str, zipfile.ZipInfo]:  # type: ignore[override] # ZipManifests.load is a classmethod
        """
        Load a manifest at path or return a suitable manifest already loaded.
        """
        path = os.path.normpath(path)
        mtime = os.stat(path).st_mtime

        if path not in self or self[path].mtime != mtime:
            manifest = self.build(path)
            self[path] = self.manifest_mod(manifest, mtime)

        return self[path].manifest


class ZipProvider(EggProvider):
    """Resource support for zips and eggs"""

    eagers: list[str] | None = None
    _zip_manifests = MemoizedZipManifests()
    # ZipProvider's loader should always be a zipimporter or equivalent
    loader: zipimport.zipimporter

    def __init__(self, module: _ZipLoaderModule) -> None:
        super().__init__(module)
        self.zip_pre = self.loader.archive + os.sep

    def _zipinfo_name(self, fspath):
        # Convert a virtual filename (full path to file) into a zipfile subpath
        # usable with the zipimport directory cache for our target archive
        fspath = fspath.rstrip(os.sep)
        if fspath == self.loader.archive:
            return ''
        if fspath.startswith(self.zip_pre):
            return fspath[len(self.zip_pre) :]
        raise AssertionError(f"{fspath} is not a subpath of {self.zip_pre}")

    def _parts(self, zip_path):
        # Convert a zipfile subpath into an egg-relative path part list.
        # pseudo-fs path
        fspath = self.zip_pre + zip_path
        if fspath.startswith(self.egg_root + os.sep):
            return fspath[len(self.egg_root) + 1 :].split(os.sep)
        raise AssertionError(f"{fspath} is not a subpath of {self.egg_root}")

    @property
    def zipinfo(self):
        return self._zip_manifests.load(self.loader.archive)

    def get_resource_filename(
        self, manager: ResourceManager, resource_name: str
    ) -> str:
        if not self.egg_name:
            raise NotImplementedError(
                "resource_filename() only supported for .egg, not .zip"
            )
        # no need to lock for extraction, since we use temp names
        zip_path = self._resource_to_zip(resource_name)
        eagers = self._get_eager_resources()
        if '/'.join(self._parts(zip_path)) in eagers:
            for name in eagers:
                self._extract_resource(manager, self._eager_to_zip(name))
        return self._extract_resource(manager, zip_path)

    @staticmethod
    def _get_date_and_size(zip_stat):
        size = zip_stat.file_size
        # ymdhms+wday, yday, dst
        date_time = zip_stat.date_time + (0, 0, -1)
        # 1980 offset already done
        timestamp = time.mktime(date_time)
        return timestamp, size

    # FIXME: 'ZipProvider._extract_resource' is too complex (12)
    def _extract_resource(self, manager: ResourceManager, zip_path) -> str:  # noqa: C901
        if zip_path in self._index():
            for name in self._index()[zip_path]:
                last = self._extract_resource(manager, os.path.join(zip_path, name))
            # return the extracted directory name
            return os.path.dirname(last)

        timestamp, _size = self._get_date_and_size(self.zipinfo[zip_path])

        if not WRITE_SUPPORT:
            raise OSError(
                '"os.rename" and "os.unlink" are not supported on this platform'
            )
        try:
            if not self.egg_name:
                raise OSError(
                    '"egg_name" is empty. This likely means no egg could be found from the "module_path".'
                )
            real_path = manager.get_cache_path(self.egg_name, self._parts(zip_path))

            if self._is_current(real_path, zip_path):
                return real_path

            outf, tmpnam = _mkstemp(
                ".$extract",
                dir=os.path.dirname(real_path),
            )
            os.write(outf, self.loader.get_data(zip_path))
            os.close(outf)
            utime(tmpnam, (timestamp, timestamp))
            manager.postprocess(tmpnam, real_path)

            try:
                rename(tmpnam, real_path)

            except OSError:
                if os.path.isfile(real_path):
                    if self._is_current(real_path, zip_path):
                        # the file became current since it was checked above,
                        #  so proceed.
                        return real_path
                    # Windows, del old file and retry
                    elif os.name == 'nt':
                        unlink(real_path)
                        rename(tmpnam, real_path)
                        return real_path
                raise

        except OSError:
            # report a user-friendly error
            manager.extraction_error()

        return real_path

    def _is_current(self, file_path, zip_path):
        """
        Return True if the file_path is current for this zip_path
        """
        timestamp, size = self._get_date_and_size(self.zipinfo[zip_path])
        if not os.path.isfile(file_path):
            return False
        stat = os.stat(file_path)
        if stat.st_size != size or stat.st_mtime != timestamp:
            return False
        # check that the contents match
        zip_contents = self.loader.get_data(zip_path)
        with open(file_path, 'rb') as f:
            file_contents = f.read()
        return zip_contents == file_contents

    def _get_eager_resources(self):
        if self.eagers is None:
            eagers = []
            for name in ('native_libs.txt', 'eager_resources.txt'):
                if self.has_metadata(name):
                    eagers.extend(self.get_metadata_lines(name))
            self.eagers = eagers
        return self.eagers

    def _index(self):
        try:
            return self._dirindex
        except AttributeError:
            ind = {}
            for path in self.zipinfo:
                parts = path.split(os.sep)
                while parts:
                    parent = os.sep.join(parts[:-1])
                    if parent in ind:
                        ind[parent].append(parts[-1])
                        break
                    else:
                        ind[parent] = [parts.pop()]
            self._dirindex = ind
            return ind

    def _has(self, fspath) -> bool:
        zip_path = self._zipinfo_name(fspath)
        return zip_path in self.zipinfo or zip_path in self._index()

    def _isdir(self, fspath) -> bool:
        return self._zipinfo_name(fspath) in self._index()

    def _listdir(self, fspath):
        return list(self._index().get(self._zipinfo_name(fspath), ()))

    def _eager_to_zip(self, resource_name: str):
        return self._zipinfo_name(self._fn(self.egg_root, resource_name))

    def _resource_to_zip(self, resource_name: str):
        return self._zipinfo_name(self._fn(self.module_path, resource_name))


register_loader_type(zipimport.zipimporter, ZipProvider)


class FileMetadata(EmptyProvider):
    """Metadata handler for standalone PKG-INFO files

    Usage::

        metadata = FileMetadata("/path/to/PKG-INFO")

    This provider rejects all data and metadata requests except for PKG-INFO,
    which is treated as existing, and will be the contents of the file at
    the provided location.
    """

    def __init__(self, path: StrPath) -> None:
        self.path = path

    def _get_metadata_path(self, name):
        return self.path

    def has_metadata(self, name: str) -> bool:
        return name == 'PKG-INFO' and os.path.isfile(self.path)

    def get_metadata(self, name: str) -> str:
        if name != 'PKG-INFO':
            raise KeyError("No metadata except PKG-INFO is available")

        with open(self.path, encoding='utf-8', errors="replace") as f:
            metadata = f.read()
        self._warn_on_replacement(metadata)
        return metadata

    def _warn_on_replacement(self, metadata) -> None:
        replacement_char = '�'
        if replacement_char in metadata:
            tmpl = "{self.path} could not be properly decoded in UTF-8"
            msg = tmpl.format(**locals())
            warnings.warn(msg)

    def get_metadata_lines(self, name: str) -> Iterator[str]:
        return yield_lines(self.get_metadata(name))


class PathMetadata(DefaultProvider):
    """Metadata provider for egg directories

    Usage::

        # Development eggs:

        egg_info = "/path/to/PackageName.egg-info"
        base_dir = os.path.dirname(egg_info)
        metadata = PathMetadata(base_dir, egg_info)
        dist_name = os.path.splitext(os.path.basename(egg_info))[0]
        dist = Distribution(basedir, project_name=dist_name, metadata=metadata)

        # Unpacked egg directories:

        egg_path = "/path/to/PackageName-ver-pyver-etc.egg"
        metadata = PathMetadata(egg_path, os.path.join(egg_path,'EGG-INFO'))
        dist = Distribution.from_filename(egg_path, metadata=metadata)
    """

    def __init__(self, path: str, egg_info: str) -> None:
        self.module_path = path
        self.egg_info = egg_info


class EggMetadata(ZipProvider):
    """Metadata provider for .egg files"""

    def __init__(self, importer: zipimport.zipimporter) -> None:
        """Create a metadata provider from a zipimporter"""

        self.zip_pre = importer.archive + os.sep
        self.loader = importer
        if importer.prefix:
            self.module_path = os.path.join(importer.archive, importer.prefix)
        else:
            self.module_path = importer.archive
        self._setup_prefix()


_distribution_finders: dict[type, _DistFinderType[Any]] = _declare_state(
    'dict', '_distribution_finders', {}
)


def register_finder(
    importer_type: type[_T], distribution_finder: _DistFinderType[_T]
) -> None:
    """Register `distribution_finder` to find distributions in sys.path items

    `importer_type` is the type or class of a PEP 302 "Importer" (sys.path item
    handler), and `distribution_finder` is a callable that, passed a path
    item and the importer instance, yields ``Distribution`` instances found on
    that path item.  See ``pkg_resources.find_on_path`` for an example."""
    _distribution_finders[importer_type] = distribution_finder


def find_distributions(path_item: str, only: bool = False) -> Iterable[Distribution]:
    """Yield distributions accessible via `path_item`"""
    importer = get_importer(path_item)
    finder = _find_adapter(_distribution_finders, importer)
    return finder(importer, path_item, only)


def find_eggs_in_zip(
    importer: zipimport.zipimporter, path_item: str, only: bool = False
) -> Iterator[Distribution]:
    """
    Find eggs in zip files; possibly multiple nested eggs.
    """
    if importer.archive.endswith('.whl'):
        # wheels are not supported with this finder
        # they don't have PKG-INFO metadata, and won't ever contain eggs
        return
    metadata = EggMetadata(importer)
    if metadata.has_metadata('PKG-INFO'):
        yield Distribution.from_filename(path_item, metadata=metadata)
    if only:
        # don't yield nested distros
        return
    for subitem in metadata.resource_listdir(''):
        if _is_egg_path(subitem):
            subpath = os.path.join(path_item, subitem)
            dists = find_eggs_in_zip(zipimport.zipimporter(subpath), subpath)
            yield from dists
        elif subitem.lower().endswith(('.dist-info', '.egg-info')):
            subpath = os.path.join(path_item, subitem)
            submeta = EggMetadata(zipimport.zipimporter(subpath))
            submeta.egg_info = subpath
            yield Distribution.from_location(path_item, subitem, submeta)


register_finder(zipimport.zipimporter, find_eggs_in_zip)


def find_nothing(
    importer: object | None, path_item: str | None, only: bool | None = False
):
    return ()


register_finder(object, find_nothing)


def find_on_path(importer: object | None, path_item, only=False):
    """Yield distributions accessible on a sys.path directory"""
    path_item = _normalize_cached(path_item)

    if _is_unpacked_egg(path_item):
        yield Distribution.from_filename(
            path_item,
            metadata=PathMetadata(path_item, os.path.join(path_item, 'EGG-INFO')),
        )
        return

    entries = (os.path.join(path_item, child) for child in safe_listdir(path_item))

    # scan for .egg and .egg-info in directory
    for entry in sorted(entries):
        fullpath = os.path.join(path_item, entry)
        factory = dist_factory(path_item, entry, only)
        yield from factory(fullpath)


def dist_factory(path_item, entry, only):
    """Return a dist_factory for the given entry."""
    lower = entry.lower()
    is_egg_info = lower.endswith('.egg-info')
    is_dist_info = lower.endswith('.dist-info') and os.path.isdir(
        os.path.join(path_item, entry)
    )
    is_meta = is_egg_info or is_dist_info
    return (
        distributions_from_metadata
        if is_meta
        else find_distributions
        if not only and _is_egg_path(entry)
        else resolve_egg_link
        if not only and lower.endswith('.egg-link')
        else NoDists()
    )


class NoDists:
    """
    >>> bool(NoDists())
    False

    >>> list(NoDists()('anything'))
    []
    """

    def __bool__(self) -> Literal[False]:
        return False

    def __call__(self, fullpath: object):
        return iter(())


def safe_listdir(path: StrOrBytesPath):
    """
    Attempt to list contents of path, but suppress some exceptions.
    """
    try:
        return os.listdir(path)
    except (PermissionError, NotADirectoryError):
        pass
    except OSError as e:
        # Ignore the directory if does not exist, not a directory or
        # permission denied
        if e.errno not in (errno.ENOTDIR, errno.EACCES, errno.ENOENT):
            raise
    return ()


def distributions_from_metadata(path: str):
    root = os.path.dirname(path)
    if os.path.isdir(path):
        if len(os.listdir(path)) == 0:
            # empty metadata dir; skip
            return
        metadata: _MetadataType = PathMetadata(root, path)
    else:
        metadata = FileMetadata(path)
    entry = os.path.basename(path)
    yield Distribution.from_location(
        root,
        entry,
        metadata,
        precedence=DEVELOP_DIST,
    )


def non_empty_lines(path):
    """
    Yield non-empty lines from file at path
    """
    for line in _read_utf8_with_fallback(path).splitlines():
        line = line.strip()
        if line:
            yield line


def resolve_egg_link(path):
    """
    Given a path to an .egg-link, resolve distributions
    present in the referenced path.
    """
    referenced_paths = non_empty_lines(path)
    resolved_paths = (
        os.path.join(os.path.dirname(path), ref) for ref in referenced_paths
    )
    dist_groups = map(find_distributions, resolved_paths)
    return next(dist_groups, ())


if hasattr(pkgutil, 'ImpImporter'):
    register_finder(pkgutil.ImpImporter, find_on_path)

register_finder(importlib.machinery.FileFinder, find_on_path)

_namespace_handlers: dict[type, _NSHandlerType[Any]] = _declare_state(
    'dict', '_namespace_handlers', {}
)
_namespace_packages: dict[str | None, list[str]] = _declare_state(
    'dict', '_namespace_packages', {}
)


def register_namespace_handler(
    importer_type: type[_T], namespace_handler: _NSHandlerType[_T]
) -> None:
    """Register `namespace_handler` to declare namespace packages

    `importer_type` is the type or class of a PEP 302 "Importer" (sys.path item
    handler), and `namespace_handler` is a callable like this::

        def namespace_handler(importer, path_entry, moduleName, module):
            # return a path_entry to use for child packages

    Namespace handlers are only called if the importer object has already
    agreed that it can handle the relevant path item, and they should only
    return a subpath if the module __path__ does not already contain an
    equivalent subpath.  For an example namespace handler, see
    ``pkg_resources.file_ns_handler``.
    """
    _namespace_handlers[importer_type] = namespace_handler


def _handle_ns(packageName, path_item):
    """Ensure that named package includes a subpath of path_item (if needed)"""

    importer = get_importer(path_item)
    if importer is None:
        return None

    # use find_spec (PEP 451) and fall-back to find_module (PEP 302)
    try:
        spec = importer.find_spec(packageName)
    except AttributeError:
        # capture warnings due to #1111
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            loader = importer.find_module(packageName)
    else:
        loader = spec.loader if spec else None

    if loader is None:
        return None
    module = sys.modules.get(packageName)
    if module is None:
        module = sys.modules[packageName] = types.ModuleType(packageName)
        module.__path__ = []
        _set_parent_ns(packageName)
    elif not hasattr(module, '__path__'):
        raise TypeError("Not a package:", packageName)
    handler = _find_adapter(_namespace_handlers, importer)
    subpath = handler(importer, path_item, packageName, module)
    if subpath is not None:
        path = module.__path__
        path.append(subpath)
        importlib.import_module(packageName)
        _rebuild_mod_path(path, packageName, module)
    return subpath


def _rebuild_mod_path(orig_path, package_name, module: types.ModuleType) -> None:
    """
    Rebuild module.__path__ ensuring that all entries are ordered
    corresponding to their sys.path order
    """
    sys_path = [_normalize_cached(p) for p in sys.path]

    def safe_sys_path_index(entry):
        """
        Workaround for #520 and #513.
        """
        try:
            return sys_path.index(entry)
        except ValueError:
            return float('inf')

    def position_in_sys_path(path):
        """
        Return the ordinal of the path based on its position in sys.path
        """
        path_parts = path.split(os.sep)
        module_parts = package_name.count('.') + 1
        parts = path_parts[:-module_parts]
        return safe_sys_path_index(_normalize_cached(os.sep.join(parts)))

    new_path = sorted(orig_path, key=position_in_sys_path)
    new_path = [_normalize_cached(p) for p in new_path]

    if isinstance(module.__path__, list):
        module.__path__[:] = new_path
    else:
        module.__path__ = new_path


def declare_namespace(packageName: str) -> None:
    """Declare that package 'packageName' is a namespace package"""

    msg = (
        f"Deprecated call to `pkg_resources.declare_namespace({packageName!r})`.\n"
        "Implementing implicit namespace packages (as specified in PEP 420) "
        "is preferred to `pkg_resources.declare_namespace`. "
        "See https://setuptools.pypa.io/en/latest/references/"
        "keywords.html#keyword-namespace-packages"
    )
    warnings.warn(msg, DeprecationWarning, stacklevel=2)

    _imp.acquire_lock()
    try:
        if packageName in _namespace_packages:
            return

        path: MutableSequence[str] = sys.path
        parent, _, _ = packageName.rpartition('.')

        if parent:
            declare_namespace(parent)
            if parent not in _namespace_packages:
                __import__(parent)
            try:
                path = sys.modules[parent].__path__
            except AttributeError as e:
                raise TypeError("Not a package:", parent) from e

        # Track what packages are namespaces, so when new path items are added,
        # they can be updated
        _namespace_packages.setdefault(parent or None, []).append(packageName)
        _namespace_packages.setdefault(packageName, [])

        for path_item in path:
            # Ensure all the parent's path items are reflected in the child,
            # if they apply
            _handle_ns(packageName, path_item)

    finally:
        _imp.release_lock()


def fixup_namespace_packages(path_item: str, parent: str | None = None) -> None:
    """Ensure that previously-declared namespace packages include path_item"""
    _imp.acquire_lock()
    try:
        for package in _namespace_packages.get(parent, ()):
            subpath = _handle_ns(package, path_item)
            if subpath:
                fixup_namespace_packages(subpath, package)
    finally:
        _imp.release_lock()


def file_ns_handler(
    importer: object,
    path_item: StrPath,
    packageName: str,
    module: types.ModuleType,
):
    """Compute an ns-package subpath for a filesystem or zipfile importer"""

    subpath = os.path.join(path_item, packageName.split('.')[-1])
    normalized = _normalize_cached(subpath)
    for item in module.__path__:
        if _normalize_cached(item) == normalized:
            break
    else:
        # Only return the path if it's not already there
        return subpath


if hasattr(pkgutil, 'ImpImporter'):
    register_namespace_handler(pkgutil.ImpImporter, file_ns_handler)

register_namespace_handler(zipimport.zipimporter, file_ns_handler)
register_namespace_handler(importlib.machinery.FileFinder, file_ns_handler)


def null_ns_handler(
    importer: object,
    path_item: str | None,
    packageName: str | None,
    module: _ModuleLike | None,
) -> None:
    return None


register_namespace_handler(object, null_ns_handler)


@overload
def normalize_path(filename: StrPath) -> str: ...
@overload
def normalize_path(filename: BytesPath) -> bytes: ...
def normalize_path(filename: StrOrBytesPath) -> str | bytes:
    """Normalize a file/dir name for comparison purposes"""
    return os.path.normcase(os.path.realpath(os.path.normpath(_cygwin_patch(filename))))


def _cygwin_patch(filename: StrOrBytesPath):  # pragma: nocover
    """
    Contrary to POSIX 2008, on Cygwin, getcwd (3) contains
    symlink components. Using
    os.path.abspath() works around this limitation. A fix in os.getcwd()
    would probably better, in Cygwin even more so, except
    that this seems to be by design...
    """
    return os.path.abspath(filename) if sys.platform == 'cygwin' else filename


if TYPE_CHECKING:
    # https://github.com/python/mypy/issues/16261
    # https://github.com/python/typeshed/issues/6347
    @overload
    def _normalize_cached(filename: StrPath) -> str: ...
    @overload
    def _normalize_cached(filename: BytesPath) -> bytes: ...
    def _normalize_cached(filename: StrOrBytesPath) -> str | bytes: ...

else:

    @functools.cache
    def _normalize_cached(filename):
        return normalize_path(filename)


def _is_egg_path(path):
    """
    Determine if given path appears to be an egg.
    """
    return _is_zip_egg(path) or _is_unpacked_egg(path)


def _is_zip_egg(path):
    return (
        path.lower().endswith('.egg')
        and os.path.isfile(path)
        and zipfile.is_zipfile(path)
    )


def _is_unpacked_egg(path):
    """
    Determine if given path appears to be an unpacked egg.
    """
    return path.lower().endswith('.egg') and os.path.isfile(
        os.path.join(path, 'EGG-INFO', 'PKG-INFO')
    )


def _set_parent_ns(packageName) -> None:
    parts = packageName.split('.')
    name = parts.pop()
    if parts:
        parent = '.'.join(parts)
        setattr(sys.modules[parent], name, sys.modules[packageName])


MODULE = re.compile(r"\w+(\.\w+)*$").match
EGG_NAME = re.compile(
    r"""
    (?P<name>[^-]+) (
        -(?P<ver>[^-]+) (
            -py(?P<pyver>[^-]+) (
                -(?P<plat>.+)
            )?
        )?
    )?
    """,
    re.VERBOSE | re.IGNORECASE,
).match


class EntryPoint:
    """Object representing an advertised importable object"""

    def __init__(
        self,
        name: str,
        module_name: str,
        attrs: Iterable[str] = (),
        extras: Iterable[str] = (),
        dist: Distribution | None = None,
    ) -> None:
        if not MODULE(module_name):
            raise ValueError("Invalid module name", module_name)
        self.name = name
        self.module_name = module_name
        self.attrs = tuple(attrs)
        self.extras = tuple(extras)
        self.dist = dist

    def __str__(self) -> str:
        s = f"{self.name} = {self.module_name}"
        if self.attrs:
            s += ':' + '.'.join(self.attrs)
        if self.extras:
            extras = ','.join(self.extras)
            s += f' [{extras}]'
        return s

    def __repr__(self) -> str:
        return f"EntryPoint.parse({str(self)!r})"

    @overload
    def load(
        self,
        require: Literal[True] = True,
        env: Environment | None = None,
        installer: _InstallerType | None = None,
    ) -> _ResolvedEntryPoint: ...
    @overload
    def load(
        self,
        require: Literal[False],
        *args: Any,
        **kwargs: Any,
    ) -> _ResolvedEntryPoint: ...
    def load(
        self,
        require: bool = True,
        *args: Environment | _InstallerType | None,
        **kwargs: Environment | _InstallerType | None,
    ) -> _ResolvedEntryPoint:
        """
        Require packages for this EntryPoint, then resolve it.
        """
        if not require or args or kwargs:
            warnings.warn(
                "Parameters to load are deprecated.  Call .resolve and "
                ".require separately.",
                PkgResourcesDeprecationWarning,
                stacklevel=2,
            )
        if require:
            # We could pass `env` and `installer` directly,
            # but keeping `*args` and `**kwargs` for backwards compatibility
            self.require(*args, **kwargs)  # type: ignore[arg-type]
        return self.resolve()

    def resolve(self) -> _ResolvedEntryPoint:
        """
        Resolve the entry point from its module and attrs.
        """
        module = __import__(self.module_name, fromlist=['__name__'], level=0)
        try:
            return functools.reduce(getattr, self.attrs, module)
        except AttributeError as exc:
            raise ImportError(str(exc)) from exc

    def require(
        self,
        env: Environment | None = None,
        installer: _InstallerType | None = None,
    ) -> None:
        if not self.dist:
            error_cls = UnknownExtra if self.extras else AttributeError
            raise error_cls("Can't require() without a distribution", self)

        # Get the requirements for this entry point with all its extras and
        # then resolve them. We have to pass `extras` along when resolving so
        # that the working set knows what extras we want. Otherwise, for
        # dist-info distributions, the working set will assume that the
        # requirements for that extra are purely optional and skip over them.
        reqs = self.dist.requires(self.extras)
        items = working_set.resolve(reqs, env, installer, extras=self.extras)
        list(map(working_set.add, items))

    pattern = re.compile(
        r'\s*'
        r'(?P<name>.+?)\s*'
        r'=\s*'
        r'(?P<module>[\w.]+)\s*'
        r'(:\s*(?P<attr>[\w.]+))?\s*'
        r'(?P<extras>\[.*\])?\s*$'
    )

    @classmethod
    def parse(cls, src: str, dist: Distribution | None = None) -> Self:
        """Parse a single entry point from string `src`

        Entry point syntax follows the form::

            name = some.module:some.attr [extra1, extra2]

        The entry name and module name are required, but the ``:attrs`` and
        ``[extras]`` parts are optional
        """
        m = cls.pattern.match(src)
        if not m:
            msg = "EntryPoint must be in 'name=module:attrs [extras]' format"
            raise ValueError(msg, src)
        res = m.groupdict()
        extras = cls._parse_extras(res['extras'])
        attrs = res['attr'].split('.') if res['attr'] else ()
        return cls(res['name'], res['module'], attrs, extras, dist)

    @classmethod
    def _parse_extras(cls, extras_spec):
        if not extras_spec:
            return ()
        req = Requirement.parse('x' + extras_spec)
        if req.specs:
            raise ValueError
        return req.extras

    @classmethod
    def parse_group(
        cls,
        group: str,
        lines: _NestedStr,
        dist: Distribution | None = None,
    ) -> dict[str, Self]:
        """Parse an entry point group"""
        if not MODULE(group):
            raise ValueError("Invalid group name", group)
        this: dict[str, Self] = {}
        for line in yield_lines(lines):
            ep = cls.parse(line, dist)
            if ep.name in this:
                raise ValueError("Duplicate entry point", group, ep.name)
            this[ep.name] = ep
        return this

    @classmethod
    def parse_map(
        cls,
        data: str | Iterable[str] | dict[str, str | Iterable[str]],
        dist: Distribution | None = None,
    ) -> dict[str, dict[str, Self]]:
        """Parse a map of entry point groups"""
        _data: Iterable[tuple[str | None, str | Iterable[str]]]
        if isinstance(data, dict):
            _data = data.items()
        else:
            _data = split_sections(data)
        maps: dict[str, dict[str, Self]] = {}
        for group, lines in _data:
            if group is None:
                if not lines:
                    continue
                raise ValueError("Entry points must be listed in groups")
            group = group.strip()
            if group in maps:
                raise ValueError("Duplicate group name", group)
            maps[group] = cls.parse_group(group, lines, dist)
        return maps


def _version_from_file(lines):
    """
    Given an iterable of lines from a Metadata file, return
    the value of the Version field, if present, or None otherwise.
    """

    def is_version_line(line):
        return line.lower().startswith('version:')

    version_lines = filter(is_version_line, lines)
    line = next(iter(version_lines), '')
    _, _, value = line.partition(':')
    return safe_version(value.strip()) or None


class Distribution:
    """Wrap an actual or potential sys.path entry w/metadata"""

    PKG_INFO = 'PKG-INFO'

    def __init__(
        self,
        location: str | None = None,
        metadata: _MetadataType = None,
        project_name: str | None = None,
        version: str | None = None,
        py_version: str | None = PY_MAJOR,
        platform: str | None = None,
        precedence: int = EGG_DIST,
    ) -> None:
        self.project_name = safe_name(project_name or 'Unknown')
        if version is not None:
            self._version = safe_version(version)
        self.py_version = py_version
        self.platform = platform
        self.location = location
        self.precedence = precedence
        self._provider = metadata or empty_provider

    @classmethod
    def from_location(
        cls,
        location: str,
        basename: StrPath,
        metadata: _MetadataType = None,
        **kw: int,  # We could set `precedence` explicitly, but keeping this as `**kw` for full backwards and subclassing compatibility
    ) -> Distribution:
        project_name, version, py_version, platform = [None] * 4
        basename, ext = os.path.splitext(basename)
        if ext.lower() in _distributionImpl:
            cls = _distributionImpl[ext.lower()]

            match = EGG_NAME(basename)
            if match:
                project_name, version, py_version, platform = match.group(
                    'name', 'ver', 'pyver', 'plat'
                )
        return cls(
            location,
            metadata,
            project_name=project_name,
            version=version,
            py_version=py_version,
            platform=platform,
            **kw,
        )._reload_version()

    def _reload_version(self):
        return self

    @property
    def hashcmp(self):
        return (
            self._forgiving_parsed_version,
            self.precedence,
            self.key,
            self.location,
            self.py_version or '',
            self.platform or '',
        )

    def __hash__(self) -> int:
        return hash(self.hashcmp)

    def __lt__(self, other: Distribution) -> bool:
        return self.hashcmp < other.hashcmp

    def __le__(self, other: Distribution) -> bool:
        return self.hashcmp <= other.hashcmp

    def __gt__(self, other: Distribution) -> bool:
        return self.hashcmp > other.hashcmp

    def __ge__(self, other: Distribution) -> bool:
        return self.hashcmp >= other.hashcmp

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            # It's not a Distribution, so they are not equal
            return False
        return self.hashcmp == other.hashcmp

    def __ne__(self, other: object) -> bool:
        return not self == other

    # These properties have to be lazy so that we don't have to load any
    # metadata until/unless it's actually needed.  (i.e., some distributions
    # may not know their name or version without loading PKG-INFO)

    @property
    def key(self):
        try:
            return self._key
        except AttributeError:
            self._key = key = self.project_name.lower()
            return key

    @property
    def parsed_version(self):
        if not hasattr(self, "_parsed_version"):
            try:
                self._parsed_version = parse_version(self.version)
            except packaging.version.InvalidVersion as ex:
                info = f"(package: {self.project_name})"
                if hasattr(ex, "add_note"):
                    ex.add_note(info)  # PEP 678
                    raise
                raise packaging.version.InvalidVersion(f"{str(ex)} {info}") from None

        return self._parsed_version

    @property
    def _forgiving_parsed_version(self):
        try:
            return self.parsed_version
        except packaging.version.InvalidVersion as ex:
            self._parsed_version = parse_version(_forgiving_version(self.version))

            notes = "\n".join(getattr(ex, "__notes__", []))  # PEP 678
            msg = f"""!!\n\n
            *************************************************************************
            {str(ex)}\n{notes}

            This is a long overdue deprecation.
            For the time being, `pkg_resources` will use `{self._parsed_version}`
            as a replacement to avoid breaking existing environments,
            but no future compatibility is guaranteed.

            If you maintain package {self.project_name} you should implement
            the relevant changes to adequate the project to PEP 440 immediately.
            *************************************************************************
            \n\n!!
            """
            warnings.warn(msg, DeprecationWarning)

            return self._parsed_version

    @property
    def version(self):
        try:
            return self._version
        except AttributeError as e:
            version = self._get_version()
            if version is None:
                path = self._get_metadata_path_for_display(self.PKG_INFO)
                msg = f"Missing 'Version:' header and/or {self.PKG_INFO} file at path: {path}"
                raise ValueError(msg, self) from e

            return version

    @property
    def _dep_map(self):
        """
        A map of extra to its list of (direct) requirements
        for this distribution, including the null extra.
        """
        try:
            return self.__dep_map
        except AttributeError:
            self.__dep_map = self._filter_extras(self._build_dep_map())
        return self.__dep_map

    @staticmethod
    def _filter_extras(
        dm: dict[str | None, list[Requirement]],
    ) -> dict[str | None, list[Requirement]]:
        """
        Given a mapping of extras to dependencies, strip off
        environment markers and filter out any dependencies
        not matching the markers.
        """
        for extra in list(filter(None, dm)):
            new_extra: str | None = extra
            reqs = dm.pop(extra)
            new_extra, _, marker = extra.partition(':')
            fails_marker = marker and (
                invalid_marker(marker) or not evaluate_marker(marker)
            )
            if fails_marker:
                reqs = []
            new_extra = safe_extra(new_extra) or None

            dm.setdefault(new_extra, []).extend(reqs)
        return dm

    def _build_dep_map(self):
        dm = {}
        for name in 'requires.txt', 'depends.txt':
            for extra, reqs in split_sections(self._get_metadata(name)):
                dm.setdefault(extra, []).extend(parse_requirements(reqs))
        return dm

    def requires(self, extras: Iterable[str] = ()) -> list[Requirement]:
        """List of Requirements needed for this distro if `extras` are used"""
        dm = self._dep_map
        deps: list[Requirement] = []
        deps.extend(dm.get(None, ()))
        for ext in extras:
            try:
                deps.extend(dm[safe_extra(ext)])
            except KeyError as e:
                raise UnknownExtra(f"{self} has no such extra feature {ext!r}") from e
        return deps

    def _get_metadata_path_for_display(self, name):
        """
        Return the path to the given metadata file, if available.
        """
        try:
            # We need to access _get_metadata_path() on the provider object
            # directly rather than through this class's __getattr__()
            # since _get_metadata_path() is marked private.
            path = self._provider._get_metadata_path(name)

        # Handle exceptions e.g. in case the distribution's metadata
        # provider doesn't support _get_metadata_path().
        except Exception:
            return '[could not detect]'

        return path

    def _get_metadata(self, name):
        if self.has_metadata(name):
            yield from self.get_metadata_lines(name)

    def _get_version(self):
        lines = self._get_metadata(self.PKG_INFO)
        return _version_from_file(lines)

    def activate(self, path: list[str] | None = None, replace: bool = False) -> None:
        """Ensure distribution is importable on `path` (default=sys.path)"""
        if path is None:
            path = sys.path
        self.insert_on(path, replace=replace)
        if path is sys.path and self.location is not None:
            fixup_namespace_packages(self.location)
            for pkg in self._get_metadata('namespace_packages.txt'):
                if pkg in sys.modules:
                    declare_namespace(pkg)

    def egg_name(self):
        """Return what this distribution's standard .egg filename should be"""
        filename = f"{to_filename(self.project_name)}-{to_filename(self.version)}-py{self.py_version or PY_MAJOR}"

        if self.platform:
            filename += '-' + self.platform
        return filename

    def __repr__(self) -> str:
        if self.location:
            return f"{self} ({self.location})"
        else:
            return str(self)

    def __str__(self) -> str:
        try:
            version = getattr(self, 'version', None)
        except ValueError:
            version = None
        version = version or "[unknown version]"
        return f"{self.project_name} {version}"

    def __getattr__(self, attr: str):
        """Delegate all unrecognized public attributes to .metadata provider"""
        if attr.startswith('_'):
            raise AttributeError(attr)
        return getattr(self._provider, attr)

    def __dir__(self):
        return list(
            set(super().__dir__())
            | set(attr for attr in self._provider.__dir__() if not attr.startswith('_'))
        )

    @classmethod
    def from_filename(
        cls,
        filename: StrPath,
        metadata: _MetadataType = None,
        **kw: int,  # We could set `precedence` explicitly, but keeping this as `**kw` for full backwards and subclassing compatibility
    ) -> Distribution:
        return cls.from_location(
            _normalize_cached(filename), os.path.basename(filename), metadata, **kw
        )

    def as_requirement(self):
        """Return a ``Requirement`` that matches this distribution exactly"""
        if isinstance(self.parsed_version, packaging.version.Version):
            spec = f"{self.project_name}=={self.parsed_version}"
        else:
            spec = f"{self.project_name}==={self.parsed_version}"

        return Requirement.parse(spec)

    def load_entry_point(self, group: str, name: str) -> _ResolvedEntryPoint:
        """Return the `name` entry point of `group` or raise ImportError"""
        ep = self.get_entry_info(group, name)
        if ep is None:
            raise ImportError(f"Entry point {(group, name)!r} not found")
        return ep.load()

    @overload
    def get_entry_map(self, group: None = None) -> dict[str, dict[str, EntryPoint]]: ...
    @overload
    def get_entry_map(self, group: str) -> dict[str, EntryPoint]: ...
    def get_entry_map(self, group: str | None = None):
        """Return the entry point map for `group`, or the full entry map"""
        if not hasattr(self, "_ep_map"):
            self._ep_map = EntryPoint.parse_map(
                self._get_metadata('entry_points.txt'), self
            )
        if group is not None:
            return self._ep_map.get(group, {})
        return self._ep_map

    def get_entry_info(self, group: str, name: str) -> EntryPoint | None:
        """Return the EntryPoint object for `group`+`name`, or ``None``"""
        return self.get_entry_map(group).get(name)

    # FIXME: 'Distribution.insert_on' is too complex (13)
    def insert_on(  # noqa: C901
        self,
        path: list[str],
        loc=None,
        replace: bool = False,
    ) -> None:
        """Ensure self.location is on path

        If replace=False (default):
            - If location is already in path anywhere, do nothing.
            - Else:
              - If it's an egg and its parent directory is on path,
                insert just ahead of the parent.
              - Else: add to the end of path.
        If replace=True:
            - If location is already on path anywhere (not eggs)
              or higher priority than its parent (eggs)
              do nothing.
            - Else:
              - If it's an egg and its parent directory is on path,
                insert just ahead of the parent,
                removing any lower-priority entries.
              - Else: add it to the front of path.
        """

        loc = loc or self.location
        if not loc:
            return

        nloc = _normalize_cached(loc)
        bdir = os.path.dirname(nloc)
        npath = [(p and _normalize_cached(p) or p) for p in path]

        for p, item in enumerate(npath):
            if item == nloc:
                if replace:
                    break
                else:
                    # don't modify path (even removing duplicates) if
                    # found and not replace
                    return
            elif item == bdir and self.precedence == EGG_DIST:
                # if it's an .egg, give it precedence over its directory
                # UNLESS it's already been added to sys.path and replace=False
                if (not replace) and nloc in npath[p:]:
                    return
                if path is sys.path:
                    self.check_version_conflict()
                path.insert(p, loc)
                npath.insert(p, nloc)
                break
        else:
            if path is sys.path:
                self.check_version_conflict()
            if replace:
                path.insert(0, loc)
            else:
                path.append(loc)
            return

        # p is the spot where we found or inserted loc; now remove duplicates
        while True:
            try:
                np = npath.index(nloc, p + 1)
            except ValueError:
                break
            else:
                del npath[np], path[np]
                # ha!
                p = np

        return

    def check_version_conflict(self):
        if self.key == 'setuptools':
            # ignore the inevitable setuptools self-conflicts  :(
            return

        nsp = dict.fromkeys(self._get_metadata('namespace_packages.txt'))
        loc = normalize_path(self.location)
        for modname in self._get_metadata('top_level.txt'):
            if (
                modname not in sys.modules
                or modname in nsp
                or modname in _namespace_packages
            ):
                continue
            if modname in ('pkg_resources', 'setuptools', 'site'):
                continue
            fn = getattr(sys.modules[modname], '__file__', None)
            if fn and (
                normalize_path(fn).startswith(loc) or fn.startswith(self.location)
            ):
                continue
            issue_warning(
                f"Module {modname} was already imported from {fn}, "
                f"but {self.location} is being added to sys.path",
            )

    def has_version(self) -> bool:
        try:
            self.version
        except ValueError:
            issue_warning("Unbuilt egg for " + repr(self))
            return False
        except SystemError:
            # TODO: remove this except clause when python/cpython#103632 is fixed.
            return False
        return True

    def clone(self, **kw: str | int | IResourceProvider | None) -> Self:
        """Copy this distribution, substituting in any changed keyword args"""
        names = 'project_name version py_version platform location precedence'
        for attr in names.split():
            kw.setdefault(attr, getattr(self, attr, None))
        kw.setdefault('metadata', self._provider)
        # Unsafely unpacking. But keeping **kw for backwards and subclassing compatibility
        return self.__class__(**kw)  # type:ignore[arg-type]

    @property
    def extras(self):
        return [dep for dep in self._dep_map if dep]


class EggInfoDistribution(Distribution):
    def _reload_version(self):
        """
        Packages installed by distutils (e.g. numpy or scipy),
        which uses an old safe_version, and so
        their version numbers can get mangled when
        converted to filenames (e.g., 1.11.0.dev0+2329eae to
        1.11.0.dev0_2329eae). These distributions will not be
        parsed properly
        downstream by Distribution and safe_version, so
        take an extra step and try to get the version number from
        the metadata file itself instead of the filename.
        """
        md_version = self._get_version()
        if md_version:
            self._version = md_version
        return self


class DistInfoDistribution(Distribution):
    """
    Wrap an actual or potential sys.path entry
    w/metadata, .dist-info style.
    """

    PKG_INFO = 'METADATA'
    EQEQ = re.compile(r"([\(,])\s*(\d.*?)\s*([,\)])")

    @property
    def _parsed_pkg_info(self):
        """Parse and cache metadata"""
        try:
            return self._pkg_info
        except AttributeError:
            metadata = self.get_metadata(self.PKG_INFO)
            self._pkg_info = email.parser.Parser().parsestr(metadata)
            return self._pkg_info

    @property
    def _dep_map(self):
        try:
            return self.__dep_map
        except AttributeError:
            self.__dep_map = self._compute_dependencies()
            return self.__dep_map

    def _compute_dependencies(self) -> dict[str | None, list[Requirement]]:
        """Recompute this distribution's dependencies."""
        self.__dep_map: dict[str | None, list[Requirement]] = {None: []}

        reqs: list[Requirement] = []
        # Including any condition expressions
        for req in self._parsed_pkg_info.get_all('Requires-Dist') or []:
            reqs.extend(parse_requirements(req))

        def reqs_for_extra(extra):
            for req in reqs:
                if not req.marker or req.marker.evaluate({'extra': extra}):
                    yield req

        common = types.MappingProxyType(dict.fromkeys(reqs_for_extra(None)))
        self.__dep_map[None].extend(common)

        for extra in self._parsed_pkg_info.get_all('Provides-Extra') or []:
            s_extra = safe_extra(extra.strip())
            self.__dep_map[s_extra] = [
                r for r in reqs_for_extra(extra) if r not in common
            ]

        return self.__dep_map


_distributionImpl = {
    '.egg': Distribution,
    '.egg-info': EggInfoDistribution,
    '.dist-info': DistInfoDistribution,
}


def issue_warning(*args, **kw):
    level = 1
    g = globals()
    try:
        # find the first stack frame that is *not* code in
        # the pkg_resources module, to use for the warning
        while sys._getframe(level).f_globals is g:
            level += 1
    except ValueError:
        pass
    warnings.warn(stacklevel=level + 1, *args, **kw)


def parse_requirements(strs: _NestedStr) -> map[Requirement]:
    """
    Yield ``Requirement`` objects for each specification in `strs`.

    `strs` must be a string, or a (possibly-nested) iterable thereof.
    """
    return map(Requirement, join_continuation(map(drop_comment, yield_lines(strs))))


class RequirementParseError(packaging.requirements.InvalidRequirement):
    "Compatibility wrapper for InvalidRequirement"


class Requirement(packaging.requirements.Requirement):
    # prefer variable length tuple to set (as found in
    # packaging.requirements.Requirement)
    extras: tuple[str, ...]  # type: ignore[assignment]

    def __init__(self, requirement_string: str) -> None:
        """DO NOT CALL THIS UNDOCUMENTED METHOD; use Requirement.parse()!"""
        super().__init__(requirement_string)
        self.unsafe_name = self.name
        project_name = safe_name(self.name)
        self.project_name, self.key = project_name, project_name.lower()
        self.specs = [(spec.operator, spec.version) for spec in self.specifier]
        self.extras = tuple(map(safe_extra, self.extras))
        self.hashCmp = (
            self.key,
            self.url,
            self.specifier,
            frozenset(self.extras),
            str(self.marker) if self.marker else None,
        )
        self.__hash = hash(self.hashCmp)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Requirement) and self.hashCmp == other.hashCmp

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __contains__(
        self, item: Distribution | packaging.specifiers.UnparsedVersion
    ) -> bool:
        if isinstance(item, Distribution):
            if item.key != self.key:
                return False

            version = item.version
        else:
            version = item

        # Allow prereleases always in order to match the previous behavior of
        # this method. In the future this should be smarter and follow PEP 440
        # more accurately.
        return self.specifier.contains(
            version,
            prereleases=True,
        )

    def __hash__(self) -> int:
        return self.__hash

    def __repr__(self) -> str:
        return f"Requirement.parse({str(self)!r})"

    @staticmethod
    def parse(s: str | Iterable[str]) -> Requirement:
        (req,) = parse_requirements(s)
        return req


def _always_object(classes):
    """
    Ensure object appears in the mro even
    for old-style classes.
    """
    if object not in classes:
        return classes + (object,)
    return classes


def _find_adapter(registry: Mapping[type, _AdapterT], ob: object) -> _AdapterT:
    """Return an adapter factory for `ob` from `registry`"""
    types = _always_object(inspect.getmro(getattr(ob, '__class__', type(ob))))
    for t in types:
        if t in registry:
            return registry[t]
    # _find_adapter would previously return None, and immediately be called.
    # So we're raising a TypeError to keep backward compatibility if anyone depended on that behaviour.
    raise TypeError(f"Could not find adapter for {registry} and {ob}")


def ensure_directory(path: StrOrBytesPath) -> None:
    """Ensure that the parent directory of `path` exists"""
    dirname = os.path.dirname(path)
    os.makedirs(dirname, exist_ok=True)


def _bypass_ensure_directory(path) -> None:
    """Sandbox-bypassing version of ensure_directory()"""
    if not WRITE_SUPPORT:
        raise OSError('"os.mkdir" not supported on this platform.')
    dirname, filename = split(path)
    if dirname and filename and not isdir(dirname):
        _bypass_ensure_directory(dirname)
        try:
            mkdir(dirname, 0o755)
        except FileExistsError:
            pass


def split_sections(s: _NestedStr) -> Iterator[tuple[str | None, list[str]]]:
    """Split a string or iterable thereof into (section, content) pairs

    Each ``section`` is a stripped version of the section header ("[section]")
    and each ``content`` is a list of stripped lines excluding blank lines and
    comment-only lines.  If there are any such lines before the first section
    header, they're returned in a first ``section`` of ``None``.
    """
    section = None
    content: list[str] = []
    for line in yield_lines(s):
        if line.startswith("["):
            if line.endswith("]"):
                if section or content:
                    yield section, content
                section = line[1:-1].strip()
                content = []
            else:
                raise ValueError("Invalid section heading", line)
        else:
            content.append(line)

    # wrap up last segment
    yield section, content


def _mkstemp(*args, **kw):
    old_open = os.open
    try:
        # temporarily bypass sandboxing
        os.open = os_open
        return tempfile.mkstemp(*args, **kw)
    finally:
        # and then put it back
        os.open = old_open


# Silence the PEP440Warning by default, so that end users don't get hit by it
# randomly just because they use pkg_resources. We want to append the rule
# because we want earlier uses of filterwarnings to take precedence over this
# one.
warnings.filterwarnings("ignore", category=PEP440Warning, append=True)


class PkgResourcesDeprecationWarning(Warning):
    """
    Base class for warning about deprecations in ``pkg_resources``

    This class is not derived from ``DeprecationWarning``, and as such is
    visible by default.
    """


# Ported from ``setuptools`` to avoid introducing an import inter-dependency:
_LOCALE_ENCODING = "locale" if sys.version_info >= (3, 10) else None


# This must go before calls to `_call_aside`. See https://github.com/pypa/setuptools/pull/4422
def _read_utf8_with_fallback(file: str, fallback_encoding=_LOCALE_ENCODING) -> str:
    """See setuptools.unicode_utils._read_utf8_with_fallback"""
    try:
        with open(file, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:  # pragma: no cover
        msg = f"""\
        ********************************************************************************
        `encoding="utf-8"` fails with {file!r}, trying `encoding={fallback_encoding!r}`.

        This fallback behaviour is considered **deprecated** and future versions of
        `setuptools/pkg_resources` may not implement it.

        Please encode {file!r} with "utf-8" to ensure future builds will succeed.

        If this file was produced by `setuptools` itself, cleaning up the cached files
        and re-building/re-installing the package with a newer version of `setuptools`
        (e.g. by updating `build-system.requires` in its `pyproject.toml`)
        might solve the problem.
        ********************************************************************************
        """
        # TODO: Add a deadline?
        #       See comment in setuptools.unicode_utils._Utf8EncodingNeeded
        warnings.warn(msg, PkgResourcesDeprecationWarning, stacklevel=2)
        with open(file, "r", encoding=fallback_encoding) as f:
            return f.read()


# from jaraco.functools 1.3
def _call_aside(f, *args, **kwargs):
    f(*args, **kwargs)
    return f


@_call_aside
def _initialize(g=globals()) -> None:
    "Set up global resource manager (deliberately not state-saved)"
    manager = ResourceManager()
    g['_manager'] = manager
    g.update(
        (name, getattr(manager, name))
        for name in dir(manager)
        if not name.startswith('_')
    )


@_call_aside
def _initialize_master_working_set() -> None:
    """
    Prepare the master working set and make the ``require()``
    API available.

    This function has explicit effects on the global state
    of pkg_resources. It is intended to be invoked once at
    the initialization of this module.

    Invocation by other packages is unsupported and done
    at their own risk.
    """
    working_set = _declare_state('object', 'working_set', WorkingSet._build_master())

    require = working_set.require
    iter_entry_points = working_set.iter_entry_points
    add_activation_listener = working_set.subscribe
    run_script = working_set.run_script
    # backward compatibility
    run_main = run_script
    # Activate all distributions already on sys.path with replace=False and
    # ensure that all distributions added to the working set in the future
    # (e.g. by calling ``require()``) will get activated as well,
    # with higher priority (replace=True).
    tuple(dist.activate(replace=False) for dist in working_set)
    add_activation_listener(
        lambda dist: dist.activate(replace=True),
        existing=False,
    )
    working_set.entries = []
    # match order
    list(map(working_set.add_entry, sys.path))
    globals().update(locals())


if TYPE_CHECKING:
    # All of these are set by the @_call_aside methods above
    __resource_manager = ResourceManager()  # Won't exist at runtime
    resource_exists = __resource_manager.resource_exists
    resource_isdir = __resource_manager.resource_isdir
    resource_filename = __resource_manager.resource_filename
    resource_stream = __resource_manager.resource_stream
    resource_string = __resource_manager.resource_string
    resource_listdir = __resource_manager.resource_listdir
    set_extraction_path = __resource_manager.set_extraction_path
    cleanup_resources = __resource_manager.cleanup_resources

    working_set = WorkingSet()
    require = working_set.require
    iter_entry_points = working_set.iter_entry_points
    add_activation_listener = working_set.subscribe
    run_script = working_set.run_script
    run_main = run_script

# === NexusCore/openenv\Lib\site-packages\fontTools\cffLib\__init__.py ===
"""cffLib: read/write Adobe CFF fonts

OpenType fonts with PostScript outlines embed a completely independent
font file in Adobe's *Compact Font Format*. So dealing with OpenType fonts
requires also dealing with CFF. This module allows you to read and write
fonts written in the CFF format.

In 2016, OpenType 1.8 introduced the `CFF2 <https://docs.microsoft.com/en-us/typography/opentype/spec/cff2>`_
format which, along with other changes, extended the CFF format to deal with
the demands of variable fonts. This module parses both original CFF and CFF2.

"""

from fontTools.misc import sstruct
from fontTools.misc import psCharStrings
from fontTools.misc.arrayTools import unionRect, intRect
from fontTools.misc.textTools import (
    bytechr,
    byteord,
    bytesjoin,
    tobytes,
    tostr,
    safeEval,
)
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.otBase import OTTableWriter
from fontTools.ttLib.tables.otBase import OTTableReader
from fontTools.ttLib.tables import otTables as ot
from io import BytesIO
import struct
import logging
import re

# mute cffLib debug messages when running ttx in verbose mode
DEBUG = logging.DEBUG - 1
log = logging.getLogger(__name__)

cffHeaderFormat = """
	major:   B
	minor:   B
	hdrSize: B
"""

maxStackLimit = 513
# maxstack operator has been deprecated. max stack is now always 513.


class CFFFontSet(object):
    """A CFF font "file" can contain more than one font, although this is
    extremely rare (and not allowed within OpenType fonts).

    This class is the entry point for parsing a CFF table. To actually
    manipulate the data inside the CFF font, you will want to access the
    ``CFFFontSet``'s :class:`TopDict` object. To do this, a ``CFFFontSet``
    object can either be treated as a dictionary (with appropriate
    ``keys()`` and ``values()`` methods) mapping font names to :class:`TopDict`
    objects, or as a list.

    .. code:: python

            from fontTools import ttLib
            tt = ttLib.TTFont("Tests/cffLib/data/LinLibertine_RBI.otf")
            tt["CFF "].cff
            # <fontTools.cffLib.CFFFontSet object at 0x101e24c90>
            tt["CFF "].cff[0] # Here's your actual font data
            # <fontTools.cffLib.TopDict object at 0x1020f1fd0>

    """

    def decompile(self, file, otFont, isCFF2=None):
        """Parse a binary CFF file into an internal representation. ``file``
        should be a file handle object. ``otFont`` is the top-level
        :py:class:`fontTools.ttLib.ttFont.TTFont` object containing this CFF file.

        If ``isCFF2`` is passed and set to ``True`` or ``False``, then the
        library makes an assertion that the CFF header is of the appropriate
        version.
        """

        self.otFont = otFont
        sstruct.unpack(cffHeaderFormat, file.read(3), self)
        if isCFF2 is not None:
            # called from ttLib: assert 'major' as read from file matches the
            # expected version
            expected_major = 2 if isCFF2 else 1
            if self.major != expected_major:
                raise ValueError(
                    "Invalid CFF 'major' version: expected %d, found %d"
                    % (expected_major, self.major)
                )
        else:
            # use 'major' version from file to determine if isCFF2
            assert self.major in (1, 2), "Unknown CFF format"
            isCFF2 = self.major == 2
        if not isCFF2:
            self.offSize = struct.unpack("B", file.read(1))[0]
            file.seek(self.hdrSize)
            self.fontNames = list(tostr(s) for s in Index(file, isCFF2=isCFF2))
            self.topDictIndex = TopDictIndex(file, isCFF2=isCFF2)
            self.strings = IndexedStrings(file)
        else:  # isCFF2
            self.topDictSize = struct.unpack(">H", file.read(2))[0]
            file.seek(self.hdrSize)
            self.fontNames = ["CFF2Font"]
            cff2GetGlyphOrder = otFont.getGlyphOrder
            # in CFF2, offsetSize is the size of the TopDict data.
            self.topDictIndex = TopDictIndex(
                file, cff2GetGlyphOrder, self.topDictSize, isCFF2=isCFF2
            )
            self.strings = None
        self.GlobalSubrs = GlobalSubrsIndex(file, isCFF2=isCFF2)
        self.topDictIndex.strings = self.strings
        self.topDictIndex.GlobalSubrs = self.GlobalSubrs

    def __len__(self):
        return len(self.fontNames)

    def keys(self):
        return list(self.fontNames)

    def values(self):
        return self.topDictIndex

    def __getitem__(self, nameOrIndex):
        """Return TopDict instance identified by name (str) or index (int
        or any object that implements `__index__`).
        """
        if hasattr(nameOrIndex, "__index__"):
            index = nameOrIndex.__index__()
        elif isinstance(nameOrIndex, str):
            name = nameOrIndex
            try:
                index = self.fontNames.index(name)
            except ValueError:
                raise KeyError(nameOrIndex)
        else:
            raise TypeError(nameOrIndex)
        return self.topDictIndex[index]

    def compile(self, file, otFont, isCFF2=None):
        """Write the object back into binary representation onto the given file.
        ``file`` should be a file handle object. ``otFont`` is the top-level
        :py:class:`fontTools.ttLib.ttFont.TTFont` object containing this CFF file.

        If ``isCFF2`` is passed and set to ``True`` or ``False``, then the
        library makes an assertion that the CFF header is of the appropriate
        version.
        """
        self.otFont = otFont
        if isCFF2 is not None:
            # called from ttLib: assert 'major' value matches expected version
            expected_major = 2 if isCFF2 else 1
            if self.major != expected_major:
                raise ValueError(
                    "Invalid CFF 'major' version: expected %d, found %d"
                    % (expected_major, self.major)
                )
        else:
            # use current 'major' value to determine output format
            assert self.major in (1, 2), "Unknown CFF format"
            isCFF2 = self.major == 2

        if otFont.recalcBBoxes and not isCFF2:
            for topDict in self.topDictIndex:
                topDict.recalcFontBBox()

        if not isCFF2:
            strings = IndexedStrings()
        else:
            strings = None
        writer = CFFWriter(isCFF2)
        topCompiler = self.topDictIndex.getCompiler(strings, self, isCFF2=isCFF2)
        if isCFF2:
            self.hdrSize = 5
            writer.add(sstruct.pack(cffHeaderFormat, self))
            # Note: topDictSize will most likely change in CFFWriter.toFile().
            self.topDictSize = topCompiler.getDataLength()
            writer.add(struct.pack(">H", self.topDictSize))
        else:
            self.hdrSize = 4
            self.offSize = 4  # will most likely change in CFFWriter.toFile().
            writer.add(sstruct.pack(cffHeaderFormat, self))
            writer.add(struct.pack("B", self.offSize))
        if not isCFF2:
            fontNames = Index()
            for name in self.fontNames:
                fontNames.append(name)
            writer.add(fontNames.getCompiler(strings, self, isCFF2=isCFF2))
        writer.add(topCompiler)
        if not isCFF2:
            writer.add(strings.getCompiler())
        writer.add(self.GlobalSubrs.getCompiler(strings, self, isCFF2=isCFF2))

        for topDict in self.topDictIndex:
            if not hasattr(topDict, "charset") or topDict.charset is None:
                charset = otFont.getGlyphOrder()
                topDict.charset = charset
        children = topCompiler.getChildren(strings)
        for child in children:
            writer.add(child)

        writer.toFile(file)

    def toXML(self, xmlWriter):
        """Write the object into XML representation onto the given
        :class:`fontTools.misc.xmlWriter.XMLWriter`.

        .. code:: python

                writer = xmlWriter.XMLWriter(sys.stdout)
                tt["CFF "].cff.toXML(writer)

        """

        xmlWriter.simpletag("major", value=self.major)
        xmlWriter.newline()
        xmlWriter.simpletag("minor", value=self.minor)
        xmlWriter.newline()
        for fontName in self.fontNames:
            xmlWriter.begintag("CFFFont", name=tostr(fontName))
            xmlWriter.newline()
            font = self[fontName]
            font.toXML(xmlWriter)
            xmlWriter.endtag("CFFFont")
            xmlWriter.newline()
        xmlWriter.newline()
        xmlWriter.begintag("GlobalSubrs")
        xmlWriter.newline()
        self.GlobalSubrs.toXML(xmlWriter)
        xmlWriter.endtag("GlobalSubrs")
        xmlWriter.newline()

    def fromXML(self, name, attrs, content, otFont=None):
        """Reads data from the XML element into the ``CFFFontSet`` object."""
        self.otFont = otFont

        # set defaults. These will be replaced if there are entries for them
        # in the XML file.
        if not hasattr(self, "major"):
            self.major = 1
        if not hasattr(self, "minor"):
            self.minor = 0

        if name == "CFFFont":
            if self.major == 1:
                if not hasattr(self, "offSize"):
                    # this will be recalculated when the cff is compiled.
                    self.offSize = 4
                if not hasattr(self, "hdrSize"):
                    self.hdrSize = 4
                if not hasattr(self, "GlobalSubrs"):
                    self.GlobalSubrs = GlobalSubrsIndex()
                if not hasattr(self, "fontNames"):
                    self.fontNames = []
                    self.topDictIndex = TopDictIndex()
                fontName = attrs["name"]
                self.fontNames.append(fontName)
                topDict = TopDict(GlobalSubrs=self.GlobalSubrs)
                topDict.charset = None  # gets filled in later
            elif self.major == 2:
                if not hasattr(self, "hdrSize"):
                    self.hdrSize = 5
                if not hasattr(self, "GlobalSubrs"):
                    self.GlobalSubrs = GlobalSubrsIndex()
                if not hasattr(self, "fontNames"):
                    self.fontNames = ["CFF2Font"]
                cff2GetGlyphOrder = self.otFont.getGlyphOrder
                topDict = TopDict(
                    GlobalSubrs=self.GlobalSubrs, cff2GetGlyphOrder=cff2GetGlyphOrder
                )
                self.topDictIndex = TopDictIndex(None, cff2GetGlyphOrder)
            self.topDictIndex.append(topDict)
            for element in content:
                if isinstance(element, str):
                    continue
                name, attrs, content = element
                topDict.fromXML(name, attrs, content)

            if hasattr(topDict, "VarStore") and topDict.FDArray[0].vstore is None:
                fdArray = topDict.FDArray
                for fontDict in fdArray:
                    if hasattr(fontDict, "Private"):
                        fontDict.Private.vstore = topDict.VarStore

        elif name == "GlobalSubrs":
            subrCharStringClass = psCharStrings.T2CharString
            if not hasattr(self, "GlobalSubrs"):
                self.GlobalSubrs = GlobalSubrsIndex()
            for element in content:
                if isinstance(element, str):
                    continue
                name, attrs, content = element
                subr = subrCharStringClass()
                subr.fromXML(name, attrs, content)
                self.GlobalSubrs.append(subr)
        elif name == "major":
            self.major = int(attrs["value"])
        elif name == "minor":
            self.minor = int(attrs["value"])

    def convertCFFToCFF2(self, otFont):
        from .CFFToCFF2 import _convertCFFToCFF2

        _convertCFFToCFF2(self, otFont)

    def convertCFF2ToCFF(self, otFont):
        from .CFF2ToCFF import _convertCFF2ToCFF

        _convertCFF2ToCFF(self, otFont)

    def desubroutinize(self):
        from .transforms import desubroutinize

        desubroutinize(self)

    def remove_hints(self):
        from .transforms import remove_hints

        remove_hints(self)

    def remove_unused_subroutines(self):
        from .transforms import remove_unused_subroutines

        remove_unused_subroutines(self)


class CFFWriter(object):
    """Helper class for serializing CFF data to binary. Used by
    :meth:`CFFFontSet.compile`."""

    def __init__(self, isCFF2):
        self.data = []
        self.isCFF2 = isCFF2

    def add(self, table):
        self.data.append(table)

    def toFile(self, file):
        lastPosList = None
        count = 1
        while True:
            log.log(DEBUG, "CFFWriter.toFile() iteration: %d", count)
            count = count + 1
            pos = 0
            posList = [pos]
            for item in self.data:
                if hasattr(item, "getDataLength"):
                    endPos = pos + item.getDataLength()
                    if isinstance(item, TopDictIndexCompiler) and item.isCFF2:
                        self.topDictSize = item.getDataLength()
                else:
                    endPos = pos + len(item)
                if hasattr(item, "setPos"):
                    item.setPos(pos, endPos)
                pos = endPos
                posList.append(pos)
            if posList == lastPosList:
                break
            lastPosList = posList
        log.log(DEBUG, "CFFWriter.toFile() writing to file.")
        begin = file.tell()
        if self.isCFF2:
            self.data[1] = struct.pack(">H", self.topDictSize)
        else:
            self.offSize = calcOffSize(lastPosList[-1])
            self.data[1] = struct.pack("B", self.offSize)
        posList = [0]
        for item in self.data:
            if hasattr(item, "toFile"):
                item.toFile(file)
            else:
                file.write(item)
            posList.append(file.tell() - begin)
        assert posList == lastPosList


def calcOffSize(largestOffset):
    if largestOffset < 0x100:
        offSize = 1
    elif largestOffset < 0x10000:
        offSize = 2
    elif largestOffset < 0x1000000:
        offSize = 3
    else:
        offSize = 4
    return offSize


class IndexCompiler(object):
    """Base class for writing CFF `INDEX data <https://docs.microsoft.com/en-us/typography/opentype/spec/cff2#5-index-data>`_
    to binary."""

    def __init__(self, items, strings, parent, isCFF2=None):
        if isCFF2 is None and hasattr(parent, "isCFF2"):
            isCFF2 = parent.isCFF2
            assert isCFF2 is not None
        self.isCFF2 = isCFF2
        self.items = self.getItems(items, strings)
        self.parent = parent

    def getItems(self, items, strings):
        return items

    def getOffsets(self):
        # An empty INDEX contains only the count field.
        if self.items:
            pos = 1
            offsets = [pos]
            for item in self.items:
                if hasattr(item, "getDataLength"):
                    pos = pos + item.getDataLength()
                else:
                    pos = pos + len(item)
                offsets.append(pos)
        else:
            offsets = []
        return offsets

    def getDataLength(self):
        if self.isCFF2:
            countSize = 4
        else:
            countSize = 2

        if self.items:
            lastOffset = self.getOffsets()[-1]
            offSize = calcOffSize(lastOffset)
            dataLength = (
                countSize
                + 1  # count
                + (len(self.items) + 1) * offSize  # offSize
                + lastOffset  # the offsets
                - 1  # size of object data
            )
        else:
            # count. For empty INDEX tables, this is the only entry.
            dataLength = countSize

        return dataLength

    def toFile(self, file):
        offsets = self.getOffsets()
        if self.isCFF2:
            writeCard32(file, len(self.items))
        else:
            writeCard16(file, len(self.items))
        # An empty INDEX contains only the count field.
        if self.items:
            offSize = calcOffSize(offsets[-1])
            writeCard8(file, offSize)
            offSize = -offSize
            pack = struct.pack
            for offset in offsets:
                binOffset = pack(">l", offset)[offSize:]
                assert len(binOffset) == -offSize
                file.write(binOffset)
            for item in self.items:
                if hasattr(item, "toFile"):
                    item.toFile(file)
                else:
                    data = tobytes(item, encoding="latin1")
                    file.write(data)


class IndexedStringsCompiler(IndexCompiler):
    def getItems(self, items, strings):
        return items.strings


class TopDictIndexCompiler(IndexCompiler):
    """Helper class for writing the TopDict to binary."""

    def getItems(self, items, strings):
        out = []
        for item in items:
            out.append(item.getCompiler(strings, self))
        return out

    def getChildren(self, strings):
        children = []
        for topDict in self.items:
            children.extend(topDict.getChildren(strings))
        return children

    def getOffsets(self):
        if self.isCFF2:
            offsets = [0, self.items[0].getDataLength()]
            return offsets
        else:
            return super(TopDictIndexCompiler, self).getOffsets()

    def getDataLength(self):
        if self.isCFF2:
            dataLength = self.items[0].getDataLength()
            return dataLength
        else:
            return super(TopDictIndexCompiler, self).getDataLength()

    def toFile(self, file):
        if self.isCFF2:
            self.items[0].toFile(file)
        else:
            super(TopDictIndexCompiler, self).toFile(file)


class FDArrayIndexCompiler(IndexCompiler):
    """Helper class for writing the
    `Font DICT INDEX <https://docs.microsoft.com/en-us/typography/opentype/spec/cff2#10-font-dict-index-font-dicts-and-fdselect>`_
    to binary."""

    def getItems(self, items, strings):
        out = []
        for item in items:
            out.append(item.getCompiler(strings, self))
        return out

    def getChildren(self, strings):
        children = []
        for fontDict in self.items:
            children.extend(fontDict.getChildren(strings))
        return children

    def toFile(self, file):
        offsets = self.getOffsets()
        if self.isCFF2:
            writeCard32(file, len(self.items))
        else:
            writeCard16(file, len(self.items))
        offSize = calcOffSize(offsets[-1])
        writeCard8(file, offSize)
        offSize = -offSize
        pack = struct.pack
        for offset in offsets:
            binOffset = pack(">l", offset)[offSize:]
            assert len(binOffset) == -offSize
            file.write(binOffset)
        for item in self.items:
            if hasattr(item, "toFile"):
                item.toFile(file)
            else:
                file.write(item)

    def setPos(self, pos, endPos):
        self.parent.rawDict["FDArray"] = pos


class GlobalSubrsCompiler(IndexCompiler):
    """Helper class for writing the `global subroutine INDEX <https://docs.microsoft.com/en-us/typography/opentype/spec/cff2#9-local-and-global-subr-indexes>`_
    to binary."""

    def getItems(self, items, strings):
        out = []
        for cs in items:
            cs.compile(self.isCFF2)
            out.append(cs.bytecode)
        return out


class SubrsCompiler(GlobalSubrsCompiler):
    """Helper class for writing the `local subroutine INDEX <https://docs.microsoft.com/en-us/typography/opentype/spec/cff2#9-local-and-global-subr-indexes>`_
    to binary."""

    def setPos(self, pos, endPos):
        offset = pos - self.parent.pos
        self.parent.rawDict["Subrs"] = offset


class CharStringsCompiler(GlobalSubrsCompiler):
    """Helper class for writing the `CharStrings INDEX <https://docs.microsoft.com/en-us/typography/opentype/spec/cff2#9-local-and-global-subr-indexes>`_
    to binary."""

    def getItems(self, items, strings):
        out = []
        for cs in items:
            cs.compile(self.isCFF2)
            out.append(cs.bytecode)
        return out

    def setPos(self, pos, endPos):
        self.parent.rawDict["CharStrings"] = pos


class Index(object):
    """This class represents what the CFF spec calls an INDEX (an array of
    variable-sized objects). `Index` items can be addressed and set using
    Python list indexing."""

    compilerClass = IndexCompiler

    def __init__(self, file=None, isCFF2=None):
        self.items = []
        self.offsets = offsets = []
        name = self.__class__.__name__
        if file is None:
            return
        self._isCFF2 = isCFF2
        log.log(DEBUG, "loading %s at %s", name, file.tell())
        self.file = file
        if isCFF2:
            count = readCard32(file)
        else:
            count = readCard16(file)
        if count == 0:
            return
        self.items = [None] * count
        offSize = readCard8(file)
        log.log(DEBUG, "    index count: %s offSize: %s", count, offSize)
        assert offSize <= 4, "offSize too large: %s" % offSize
        pad = b"\0" * (4 - offSize)
        for index in range(count + 1):
            chunk = file.read(offSize)
            chunk = pad + chunk
            (offset,) = struct.unpack(">L", chunk)
            offsets.append(int(offset))
        self.offsetBase = file.tell() - 1
        file.seek(self.offsetBase + offsets[-1])  # pretend we've read the whole lot
        log.log(DEBUG, "    end of %s at %s", name, file.tell())

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        item = self.items[index]
        if item is not None:
            return item
        offset = self.offsets[index] + self.offsetBase
        size = self.offsets[index + 1] - self.offsets[index]
        file = self.file
        file.seek(offset)
        data = file.read(size)
        assert len(data) == size
        item = self.produceItem(index, data, file, offset)
        self.items[index] = item
        return item

    def __setitem__(self, index, item):
        self.items[index] = item

    def produceItem(self, index, data, file, offset):
        return data

    def append(self, item):
        """Add an item to an INDEX."""
        self.items.append(item)

    def getCompiler(self, strings, parent, isCFF2=None):
        return self.compilerClass(self, strings, parent, isCFF2=isCFF2)

    def clear(self):
        """Empty the INDEX."""
        del self.items[:]


class GlobalSubrsIndex(Index):
    """This index contains all the global subroutines in the font. A global
    subroutine is a set of ``CharString`` data which is accessible to any
    glyph in the font, and are used to store repeated instructions - for
    example, components may be encoded as global subroutines, but so could
    hinting instructions.

    Remember that when interpreting a ``callgsubr`` instruction (or indeed
    a ``callsubr`` instruction) that you will need to add the "subroutine
    number bias" to number given:

    .. code:: python

            tt = ttLib.TTFont("Almendra-Bold.otf")
            u = tt["CFF "].cff[0].CharStrings["udieresis"]
            u.decompile()

            u.toXML(XMLWriter(sys.stdout))
            # <some stuff>
            # -64 callgsubr <-- Subroutine which implements the dieresis mark
            # <other stuff>

            tt["CFF "].cff[0].GlobalSubrs[-64] # <-- WRONG
            # <T2CharString (bytecode) at 103451d10>

            tt["CFF "].cff[0].GlobalSubrs[-64 + 107] # <-- RIGHT
            # <T2CharString (source) at 103451390>

    ("The bias applied depends on the number of subrs (gsubrs). If the number of
    subrs (gsubrs) is less than 1240, the bias is 107. Otherwise if it is less
    than 33900, it is 1131; otherwise it is 32768.",
    `Subroutine Operators <https://docs.microsoft.com/en-us/typography/opentype/otspec180/cff2charstr#section4.4>`)
    """

    compilerClass = GlobalSubrsCompiler
    subrClass = psCharStrings.T2CharString
    charStringClass = psCharStrings.T2CharString

    def __init__(
        self,
        file=None,
        globalSubrs=None,
        private=None,
        fdSelect=None,
        fdArray=None,
        isCFF2=None,
    ):
        super(GlobalSubrsIndex, self).__init__(file, isCFF2=isCFF2)
        self.globalSubrs = globalSubrs
        self.private = private
        if fdSelect:
            self.fdSelect = fdSelect
        if fdArray:
            self.fdArray = fdArray

    def produceItem(self, index, data, file, offset):
        if self.private is not None:
            private = self.private
        elif hasattr(self, "fdArray") and self.fdArray is not None:
            if hasattr(self, "fdSelect") and self.fdSelect is not None:
                fdIndex = self.fdSelect[index]
            else:
                fdIndex = 0
            private = self.fdArray[fdIndex].Private
        else:
            private = None
        return self.subrClass(data, private=private, globalSubrs=self.globalSubrs)

    def toXML(self, xmlWriter):
        """Write the subroutines index into XML representation onto the given
        :class:`fontTools.misc.xmlWriter.XMLWriter`.

        .. code:: python

                writer = xmlWriter.XMLWriter(sys.stdout)
                tt["CFF "].cff[0].GlobalSubrs.toXML(writer)

        """
        xmlWriter.comment(
            "The 'index' attribute is only for humans; " "it is ignored when parsed."
        )
        xmlWriter.newline()
        for i in range(len(self)):
            subr = self[i]
            if subr.needsDecompilation():
                xmlWriter.begintag("CharString", index=i, raw=1)
            else:
                xmlWriter.begintag("CharString", index=i)
            xmlWriter.newline()
            subr.toXML(xmlWriter)
            xmlWriter.endtag("CharString")
            xmlWriter.newline()

    def fromXML(self, name, attrs, content):
        if name != "CharString":
            return
        subr = self.subrClass()
        subr.fromXML(name, attrs, content)
        self.append(subr)

    def getItemAndSelector(self, index):
        sel = None
        if hasattr(self, "fdSelect"):
            sel = self.fdSelect[index]
        return self[index], sel


class SubrsIndex(GlobalSubrsIndex):
    """This index contains a glyph's local subroutines. A local subroutine is a
    private set of ``CharString`` data which is accessible only to the glyph to
    which the index is attached."""

    compilerClass = SubrsCompiler


class TopDictIndex(Index):
    """This index represents the array of ``TopDict`` structures in the font
    (again, usually only one entry is present). Hence the following calls are
    equivalent:

    .. code:: python

            tt["CFF "].cff[0]
            # <fontTools.cffLib.TopDict object at 0x102ed6e50>
            tt["CFF "].cff.topDictIndex[0]
            # <fontTools.cffLib.TopDict object at 0x102ed6e50>

    """

    compilerClass = TopDictIndexCompiler

    def __init__(self, file=None, cff2GetGlyphOrder=None, topSize=0, isCFF2=None):
        self.cff2GetGlyphOrder = cff2GetGlyphOrder
        if file is not None and isCFF2:
            self._isCFF2 = isCFF2
            self.items = []
            name = self.__class__.__name__
            log.log(DEBUG, "loading %s at %s", name, file.tell())
            self.file = file
            count = 1
            self.items = [None] * count
            self.offsets = [0, topSize]
            self.offsetBase = file.tell()
            # pretend we've read the whole lot
            file.seek(self.offsetBase + topSize)
            log.log(DEBUG, "    end of %s at %s", name, file.tell())
        else:
            super(TopDictIndex, self).__init__(file, isCFF2=isCFF2)

    def produceItem(self, index, data, file, offset):
        top = TopDict(
            self.strings,
            file,
            offset,
            self.GlobalSubrs,
            self.cff2GetGlyphOrder,
            isCFF2=self._isCFF2,
        )
        top.decompile(data)
        return top

    def toXML(self, xmlWriter):
        for i in range(len(self)):
            xmlWriter.begintag("FontDict", index=i)
            xmlWriter.newline()
            self[i].toXML(xmlWriter)
            xmlWriter.endtag("FontDict")
            xmlWriter.newline()


class FDArrayIndex(Index):
    compilerClass = FDArrayIndexCompiler

    def toXML(self, xmlWriter):
        for i in range(len(self)):
            xmlWriter.begintag("FontDict", index=i)
            xmlWriter.newline()
            self[i].toXML(xmlWriter)
            xmlWriter.endtag("FontDict")
            xmlWriter.newline()

    def produceItem(self, index, data, file, offset):
        fontDict = FontDict(
            self.strings,
            file,
            offset,
            self.GlobalSubrs,
            isCFF2=self._isCFF2,
            vstore=self.vstore,
        )
        fontDict.decompile(data)
        return fontDict

    def fromXML(self, name, attrs, content):
        if name != "FontDict":
            return
        fontDict = FontDict()
        for element in content:
            if isinstance(element, str):
                continue
            name, attrs, content = element
            fontDict.fromXML(name, attrs, content)
        self.append(fontDict)


class VarStoreData(object):
    def __init__(self, file=None, otVarStore=None):
        self.file = file
        self.data = None
        self.otVarStore = otVarStore
        self.font = TTFont()  # dummy font for the decompile function.

    def decompile(self):
        if self.file:
            # read data in from file. Assume position is correct.
            length = readCard16(self.file)
            # https://github.com/fonttools/fonttools/issues/3673
            if length == 65535:
                self.data = self.file.read()
            else:
                self.data = self.file.read(length)
            globalState = {}
            reader = OTTableReader(self.data, globalState)
            self.otVarStore = ot.VarStore()
            self.otVarStore.decompile(reader, self.font)
            self.data = None
        return self

    def compile(self):
        writer = OTTableWriter()
        self.otVarStore.compile(writer, self.font)
        # Note that this omits the initial Card16 length from the CFF2
        # VarStore data block
        self.data = writer.getAllData()

    def writeXML(self, xmlWriter, name):
        self.otVarStore.toXML(xmlWriter, self.font)

    def xmlRead(self, name, attrs, content, parent):
        self.otVarStore = ot.VarStore()
        for element in content:
            if isinstance(element, tuple):
                name, attrs, content = element
                self.otVarStore.fromXML(name, attrs, content, self.font)
            else:
                pass
        return None

    def __len__(self):
        return len(self.data)

    def getNumRegions(self, vsIndex):
        if vsIndex is None:
            vsIndex = 0
        varData = self.otVarStore.VarData[vsIndex]
        numRegions = varData.VarRegionCount
        return numRegions


class FDSelect(object):
    def __init__(self, file=None, numGlyphs=None, format=None):
        if file:
            # read data in from file
            self.format = readCard8(file)
            if self.format == 0:
                from array import array

                self.gidArray = array("B", file.read(numGlyphs)).tolist()
            elif self.format == 3:
                gidArray = [None] * numGlyphs
                nRanges = readCard16(file)
                fd = None
                prev = None
                for i in range(nRanges):
                    first = readCard16(file)
                    if prev is not None:
                        for glyphID in range(prev, first):
                            gidArray[glyphID] = fd
                    prev = first
                    fd = readCard8(file)
                if prev is not None:
                    first = readCard16(file)
                    for glyphID in range(prev, first):
                        gidArray[glyphID] = fd
                self.gidArray = gidArray
            elif self.format == 4:
                gidArray = [None] * numGlyphs
                nRanges = readCard32(file)
                fd = None
                prev = None
                for i in range(nRanges):
                    first = readCard32(file)
                    if prev is not None:
                        for glyphID in range(prev, first):
                            gidArray[glyphID] = fd
                    prev = first
                    fd = readCard16(file)
                if prev is not None:
                    first = readCard32(file)
                    for glyphID in range(prev, first):
                        gidArray[glyphID] = fd
                self.gidArray = gidArray
            else:
                assert False, "unsupported FDSelect format: %s" % format
        else:
            # reading from XML. Make empty gidArray, and leave format as passed in.
            # format is None will result in the smallest representation being used.
            self.format = format
            self.gidArray = []

    def __len__(self):
        return len(self.gidArray)

    def __getitem__(self, index):
        return self.gidArray[index]

    def __setitem__(self, index, fdSelectValue):
        self.gidArray[index] = fdSelectValue

    def append(self, fdSelectValue):
        self.gidArray.append(fdSelectValue)


class CharStrings(object):
    """The ``CharStrings`` in the font represent the instructions for drawing
    each glyph. This object presents a dictionary interface to the font's
    CharStrings, indexed by glyph name:

    .. code:: python

            tt["CFF "].cff[0].CharStrings["a"]
            # <T2CharString (bytecode) at 103451e90>

    See :class:`fontTools.misc.psCharStrings.T1CharString` and
    :class:`fontTools.misc.psCharStrings.T2CharString` for how to decompile,
    compile and interpret the glyph drawing instructions in the returned objects.

    """

    def __init__(
        self,
        file,
        charset,
        globalSubrs,
        private,
        fdSelect,
        fdArray,
        isCFF2=None,
        varStore=None,
    ):
        self.globalSubrs = globalSubrs
        self.varStore = varStore
        if file is not None:
            self.charStringsIndex = SubrsIndex(
                file, globalSubrs, private, fdSelect, fdArray, isCFF2=isCFF2
            )
            self.charStrings = charStrings = {}
            for i in range(len(charset)):
                charStrings[charset[i]] = i
            # read from OTF file: charStrings.values() are indices into
            # charStringsIndex.
            self.charStringsAreIndexed = 1
        else:
            self.charStrings = {}
            # read from ttx file: charStrings.values() are actual charstrings
            self.charStringsAreIndexed = 0
            self.private = private
            if fdSelect is not None:
                self.fdSelect = fdSelect
            if fdArray is not None:
                self.fdArray = fdArray

    def keys(self):
        return list(self.charStrings.keys())

    def values(self):
        if self.charStringsAreIndexed:
            return self.charStringsIndex
        else:
            return list(self.charStrings.values())

    def has_key(self, name):
        return name in self.charStrings

    __contains__ = has_key

    def __len__(self):
        return len(self.charStrings)

    def __getitem__(self, name):
        charString = self.charStrings[name]
        if self.charStringsAreIndexed:
            charString = self.charStringsIndex[charString]
        return charString

    def __setitem__(self, name, charString):
        if self.charStringsAreIndexed:
            index = self.charStrings[name]
            self.charStringsIndex[index] = charString
        else:
            self.charStrings[name] = charString

    def getItemAndSelector(self, name):
        if self.charStringsAreIndexed:
            index = self.charStrings[name]
            return self.charStringsIndex.getItemAndSelector(index)
        else:
            if hasattr(self, "fdArray"):
                if hasattr(self, "fdSelect"):
                    sel = self.charStrings[name].fdSelectIndex
                else:
                    sel = 0
            else:
                sel = None
            return self.charStrings[name], sel

    def toXML(self, xmlWriter):
        names = sorted(self.keys())
        for name in names:
            charStr, fdSelectIndex = self.getItemAndSelector(name)
            if charStr.needsDecompilation():
                raw = [("raw", 1)]
            else:
                raw = []
            if fdSelectIndex is None:
                xmlWriter.begintag("CharString", [("name", name)] + raw)
            else:
                xmlWriter.begintag(
                    "CharString",
                    [("name", name), ("fdSelectIndex", fdSelectIndex)] + raw,
                )
            xmlWriter.newline()
            charStr.toXML(xmlWriter)
            xmlWriter.endtag("CharString")
            xmlWriter.newline()

    def fromXML(self, name, attrs, content):
        for element in content:
            if isinstance(element, str):
                continue
            name, attrs, content = element
            if name != "CharString":
                continue
            fdID = -1
            if hasattr(self, "fdArray"):
                try:
                    fdID = safeEval(attrs["fdSelectIndex"])
                except KeyError:
                    fdID = 0
                private = self.fdArray[fdID].Private
            else:
                private = self.private

            glyphName = attrs["name"]
            charStringClass = psCharStrings.T2CharString
            charString = charStringClass(private=private, globalSubrs=self.globalSubrs)
            charString.fromXML(name, attrs, content)
            if fdID >= 0:
                charString.fdSelectIndex = fdID
            self[glyphName] = charString


def readCard8(file):
    return byteord(file.read(1))


def readCard16(file):
    (value,) = struct.unpack(">H", file.read(2))
    return value


def readCard32(file):
    (value,) = struct.unpack(">L", file.read(4))
    return value


def writeCard8(file, value):
    file.write(bytechr(value))


def writeCard16(file, value):
    file.write(struct.pack(">H", value))


def writeCard32(file, value):
    file.write(struct.pack(">L", value))


def packCard8(value):
    return bytechr(value)


def packCard16(value):
    return struct.pack(">H", value)


def packCard32(value):
    return struct.pack(">L", value)


def buildOperatorDict(table):
    d = {}
    for op, name, arg, default, conv in table:
        d[op] = (name, arg)
    return d


def buildOpcodeDict(table):
    d = {}
    for op, name, arg, default, conv in table:
        if isinstance(op, tuple):
            op = bytechr(op[0]) + bytechr(op[1])
        else:
            op = bytechr(op)
        d[name] = (op, arg)
    return d


def buildOrder(table):
    l = []
    for op, name, arg, default, conv in table:
        l.append(name)
    return l


def buildDefaults(table):
    d = {}
    for op, name, arg, default, conv in table:
        if default is not None:
            d[name] = default
    return d


def buildConverters(table):
    d = {}
    for op, name, arg, default, conv in table:
        d[name] = conv
    return d


class SimpleConverter(object):
    def read(self, parent, value):
        if not hasattr(parent, "file"):
            return self._read(parent, value)
        file = parent.file
        pos = file.tell()
        try:
            return self._read(parent, value)
        finally:
            file.seek(pos)

    def _read(self, parent, value):
        return value

    def write(self, parent, value):
        return value

    def xmlWrite(self, xmlWriter, name, value):
        xmlWriter.simpletag(name, value=value)
        xmlWriter.newline()

    def xmlRead(self, name, attrs, content, parent):
        return attrs["value"]


class ASCIIConverter(SimpleConverter):
    def _read(self, parent, value):
        return tostr(value, encoding="ascii")

    def write(self, parent, value):
        return tobytes(value, encoding="ascii")

    def xmlWrite(self, xmlWriter, name, value):
        xmlWriter.simpletag(name, value=tostr(value, encoding="ascii"))
        xmlWriter.newline()

    def xmlRead(self, name, attrs, content, parent):
        return tobytes(attrs["value"], encoding=("ascii"))


class Latin1Converter(SimpleConverter):
    def _read(self, parent, value):
        return tostr(value, encoding="latin1")

    def write(self, parent, value):
        return tobytes(value, encoding="latin1")

    def xmlWrite(self, xmlWriter, name, value):
        value = tostr(value, encoding="latin1")
        if name in ["Notice", "Copyright"]:
            value = re.sub(r"[\r\n]\s+", " ", value)
        xmlWriter.simpletag(name, value=value)
        xmlWriter.newline()

    def xmlRead(self, name, attrs, content, parent):
        return tobytes(attrs["value"], encoding=("latin1"))


def parseNum(s):
    try:
        value = int(s)
    except:
        value = float(s)
    return value


def parseBlendList(s):
    valueList = []
    for element in s:
        if isinstance(element, str):
            continue
        name, attrs, content = element
        blendList = attrs["value"].split()
        blendList = [eval(val) for val in blendList]
        valueList.append(blendList)
    if len(valueList) == 1:
        valueList = valueList[0]
    return valueList


class NumberConverter(SimpleConverter):
    def xmlWrite(self, xmlWriter, name, value):
        if isinstance(value, list):
            xmlWriter.begintag(name)
            xmlWriter.newline()
            xmlWriter.indent()
            blendValue = " ".join([str(val) for val in value])
            xmlWriter.simpletag(kBlendDictOpName, value=blendValue)
            xmlWriter.newline()
            xmlWriter.dedent()
            xmlWriter.endtag(name)
            xmlWriter.newline()
        else:
            xmlWriter.simpletag(name, value=value)
            xmlWriter.newline()

    def xmlRead(self, name, attrs, content, parent):
        valueString = attrs.get("value", None)
        if valueString is None:
            value = parseBlendList(content)
        else:
            value = parseNum(attrs["value"])
        return value


class ArrayConverter(SimpleConverter):
    def xmlWrite(self, xmlWriter, name, value):
        if value and isinstance(value[0], list):
            xmlWriter.begintag(name)
            xmlWriter.newline()
            xmlWriter.indent()
            for valueList in value:
                blendValue = " ".join([str(val) for val in valueList])
                xmlWriter.simpletag(kBlendDictOpName, value=blendValue)
                xmlWriter.newline()
            xmlWriter.dedent()
            xmlWriter.endtag(name)
            xmlWriter.newline()
        else:
            value = " ".join([str(val) for val in value])
            xmlWriter.simpletag(name, value=value)
            xmlWriter.newline()

    def xmlRead(self, name, attrs, content, parent):
        valueString = attrs.get("value", None)
        if valueString is None:
            valueList = parseBlendList(content)
        else:
            values = valueString.split()
            valueList = [parseNum(value) for value in values]
        return valueList


class TableConverter(SimpleConverter):
    def xmlWrite(self, xmlWriter, name, value):
        xmlWriter.begintag(name)
        xmlWriter.newline()
        value.toXML(xmlWriter)
        xmlWriter.endtag(name)
        xmlWriter.newline()

    def xmlRead(self, name, attrs, content, parent):
        ob = self.getClass()()
        for element in content:
            if isinstance(element, str):
                continue
            name, attrs, content = element
            ob.fromXML(name, attrs, content)
        return ob


class PrivateDictConverter(TableConverter):
    def getClass(self):
        return PrivateDict

    def _read(self, parent, value):
        size, offset = value
        file = parent.file
        isCFF2 = parent._isCFF2
        try:
            vstore = parent.vstore
        except AttributeError:
            vstore = None
        priv = PrivateDict(parent.strings, file, offset, isCFF2=isCFF2, vstore=vstore)
        file.seek(offset)
        data = file.read(size)
        assert len(data) == size
        priv.decompile(data)
        return priv

    def write(self, parent, value):
        return (0, 0)  # dummy value


class SubrsConverter(TableConverter):
    def getClass(self):
        return SubrsIndex

    def _read(self, parent, value):
        file = parent.file
        isCFF2 = parent._isCFF2
        file.seek(parent.offset + value)  # Offset(self)
        return SubrsIndex(file, isCFF2=isCFF2)

    def write(self, parent, value):
        return 0  # dummy value


class CharStringsConverter(TableConverter):
    def _read(self, parent, value):
        file = parent.file
        isCFF2 = parent._isCFF2
        charset = parent.charset
        varStore = getattr(parent, "VarStore", None)
        globalSubrs = parent.GlobalSubrs
        if hasattr(parent, "FDArray"):
            fdArray = parent.FDArray
            if hasattr(parent, "FDSelect"):
                fdSelect = parent.FDSelect
            else:
                fdSelect = None
            private = None
        else:
            fdSelect, fdArray = None, None
            private = parent.Private
        file.seek(value)  # Offset(0)
        charStrings = CharStrings(
            file,
            charset,
            globalSubrs,
            private,
            fdSelect,
            fdArray,
            isCFF2=isCFF2,
            varStore=varStore,
        )
        return charStrings

    def write(self, parent, value):
        return 0  # dummy value

    def xmlRead(self, name, attrs, content, parent):
        if hasattr(parent, "FDArray"):
            # if it is a CID-keyed font, then the private Dict is extracted from the
            # parent.FDArray
            fdArray = parent.FDArray
            if hasattr(parent, "FDSelect"):
                fdSelect = parent.FDSelect
            else:
                fdSelect = None
            private = None
        else:
            # if it is a name-keyed font, then the private dict is in the top dict,
            # and
            # there is no fdArray.
            private, fdSelect, fdArray = parent.Private, None, None
        charStrings = CharStrings(
            None,
            None,
            parent.GlobalSubrs,
            private,
            fdSelect,
            fdArray,
            varStore=getattr(parent, "VarStore", None),
        )
        charStrings.fromXML(name, attrs, content)
        return charStrings


class CharsetConverter(SimpleConverter):
    def _read(self, parent, value):
        isCID = hasattr(parent, "ROS")
        if value > 2:
            numGlyphs = parent.numGlyphs
            file = parent.file
            file.seek(value)
            log.log(DEBUG, "loading charset at %s", value)
            format = readCard8(file)
            if format == 0:
                charset = parseCharset0(numGlyphs, file, parent.strings, isCID)
            elif format == 1 or format == 2:
                charset = parseCharset(numGlyphs, file, parent.strings, isCID, format)
            else:
                raise NotImplementedError
            assert len(charset) == numGlyphs
            log.log(DEBUG, "    charset end at %s", file.tell())
            # make sure glyph names are unique
            allNames = {}
            newCharset = []
            for glyphName in charset:
                if glyphName in allNames:
                    # make up a new glyphName that's unique
                    n = allNames[glyphName]
                    names = set(allNames) | set(charset)
                    while (glyphName + "." + str(n)) in names:
                        n += 1
                    allNames[glyphName] = n + 1
                    glyphName = glyphName + "." + str(n)
                allNames[glyphName] = 1
                newCharset.append(glyphName)
            charset = newCharset
        else:  # offset == 0 -> no charset data.
            if isCID or "CharStrings" not in parent.rawDict:
                # We get here only when processing fontDicts from the FDArray of
                # CFF-CID fonts. Only the real topDict references the charset.
                assert value == 0
                charset = None
            elif value == 0:
                charset = cffISOAdobeStrings
            elif value == 1:
                charset = cffIExpertStrings
            elif value == 2:
                charset = cffExpertSubsetStrings
        if charset and (len(charset) != parent.numGlyphs):
            charset = charset[: parent.numGlyphs]
        return charset

    def write(self, parent, value):
        return 0  # dummy value

    def xmlWrite(self, xmlWriter, name, value):
        # XXX only write charset when not in OT/TTX context, where we
        # dump charset as a separate "GlyphOrder" table.
        # # xmlWriter.simpletag("charset")
        xmlWriter.comment("charset is dumped separately as the 'GlyphOrder' element")
        xmlWriter.newline()

    def xmlRead(self, name, attrs, content, parent):
        pass


class CharsetCompiler(object):
    def __init__(self, strings, charset, parent):
        assert charset[0] == ".notdef"
        isCID = hasattr(parent.dictObj, "ROS")
        data0 = packCharset0(charset, isCID, strings)
        data = packCharset(charset, isCID, strings)
        if len(data) < len(data0):
            self.data = data
        else:
            self.data = data0
        self.parent = parent

    def setPos(self, pos, endPos):
        self.parent.rawDict["charset"] = pos

    def getDataLength(self):
        return len(self.data)

    def toFile(self, file):
        file.write(self.data)


def getStdCharSet(charset):
    # check to see if we can use a predefined charset value.
    predefinedCharSetVal = None
    predefinedCharSets = [
        (cffISOAdobeStringCount, cffISOAdobeStrings, 0),
        (cffExpertStringCount, cffIExpertStrings, 1),
        (cffExpertSubsetStringCount, cffExpertSubsetStrings, 2),
    ]
    lcs = len(charset)
    for cnt, pcs, csv in predefinedCharSets:
        if predefinedCharSetVal is not None:
            break
        if lcs > cnt:
            continue
        predefinedCharSetVal = csv
        for i in range(lcs):
            if charset[i] != pcs[i]:
                predefinedCharSetVal = None
                break
    return predefinedCharSetVal


def getCIDfromName(name, strings):
    return int(name[3:])


def getSIDfromName(name, strings):
    return strings.getSID(name)


def packCharset0(charset, isCID, strings):
    fmt = 0
    data = [packCard8(fmt)]
    if isCID:
        getNameID = getCIDfromName
    else:
        getNameID = getSIDfromName

    for name in charset[1:]:
        data.append(packCard16(getNameID(name, strings)))
    return bytesjoin(data)


def packCharset(charset, isCID, strings):
    fmt = 1
    ranges = []
    first = None
    end = 0
    if isCID:
        getNameID = getCIDfromName
    else:
        getNameID = getSIDfromName

    for name in charset[1:]:
        SID = getNameID(name, strings)
        if first is None:
            first = SID
        elif end + 1 != SID:
            nLeft = end - first
            if nLeft > 255:
                fmt = 2
            ranges.append((first, nLeft))
            first = SID
        end = SID
    if end:
        nLeft = end - first
        if nLeft > 255:
            fmt = 2
        ranges.append((first, nLeft))

    data = [packCard8(fmt)]
    if fmt == 1:
        nLeftFunc = packCard8
    else:
        nLeftFunc = packCard16
    for first, nLeft in ranges:
        data.append(packCard16(first) + nLeftFunc(nLeft))
    return bytesjoin(data)


def parseCharset0(numGlyphs, file, strings, isCID):
    charset = [".notdef"]
    if isCID:
        for i in range(numGlyphs - 1):
            CID = readCard16(file)
            charset.append("cid" + str(CID).zfill(5))
    else:
        for i in range(numGlyphs - 1):
            SID = readCard16(file)
            charset.append(strings[SID])
    return charset


def parseCharset(numGlyphs, file, strings, isCID, fmt):
    charset = [".notdef"]
    count = 1
    if fmt == 1:
        nLeftFunc = readCard8
    else:
        nLeftFunc = readCard16
    while count < numGlyphs:
        first = readCard16(file)
        nLeft = nLeftFunc(file)
        if isCID:
            for CID in range(first, first + nLeft + 1):
                charset.append("cid" + str(CID).zfill(5))
        else:
            for SID in range(first, first + nLeft + 1):
                charset.append(strings[SID])
        count = count + nLeft + 1
    return charset


class EncodingCompiler(object):
    def __init__(self, strings, encoding, parent):
        assert not isinstance(encoding, str)
        data0 = packEncoding0(parent.dictObj.charset, encoding, parent.strings)
        data1 = packEncoding1(parent.dictObj.charset, encoding, parent.strings)
        if len(data0) < len(data1):
            self.data = data0
        else:
            self.data = data1
        self.parent = parent

    def setPos(self, pos, endPos):
        self.parent.rawDict["Encoding"] = pos

    def getDataLength(self):
        return len(self.data)

    def toFile(self, file):
        file.write(self.data)


class EncodingConverter(SimpleConverter):
    def _read(self, parent, value):
        if value == 0:
            return "StandardEncoding"
        elif value == 1:
            return "ExpertEncoding"
        # custom encoding at offset `value`
        assert value > 1
        file = parent.file
        file.seek(value)
        log.log(DEBUG, "loading Encoding at %s", value)
        fmt = readCard8(file)
        haveSupplement = bool(fmt & 0x80)
        fmt = fmt & 0x7F

        if fmt == 0:
            encoding = parseEncoding0(parent.charset, file)
        elif fmt == 1:
            encoding = parseEncoding1(parent.charset, file)
        else:
            raise ValueError(f"Unknown Encoding format: {fmt}")

        if haveSupplement:
            parseEncodingSupplement(file, encoding, parent.strings)

        return encoding

    def write(self, parent, value):
        if value == "StandardEncoding":
            return 0
        elif value == "ExpertEncoding":
            return 1
        return 0  # dummy value

    def xmlWrite(self, xmlWriter, name, value):
        if value in ("StandardEncoding", "ExpertEncoding"):
            xmlWriter.simpletag(name, name=value)
            xmlWriter.newline()
            return
        xmlWriter.begintag(name)
        xmlWriter.newline()
        for code in range(len(value)):
            glyphName = value[code]
            if glyphName != ".notdef":
                xmlWriter.simpletag("map", code=hex(code), name=glyphName)
                xmlWriter.newline()
        xmlWriter.endtag(name)
        xmlWriter.newline()

    def xmlRead(self, name, attrs, content, parent):
        if "name" in attrs:
            return attrs["name"]
        encoding = [".notdef"] * 256
        for element in content:
            if isinstance(element, str):
                continue
            name, attrs, content = element
            code = safeEval(attrs["code"])
            glyphName = attrs["name"]
            encoding[code] = glyphName
        return encoding


def readSID(file):
    """Read a String ID (SID) — 2-byte unsigned integer."""
    data = file.read(2)
    if len(data) != 2:
        raise EOFError("Unexpected end of file while reading SID")
    return struct.unpack(">H", data)[0]  # big-endian uint16


def parseEncodingSupplement(file, encoding, strings):
    """
    Parse the CFF Encoding supplement data:
      - nSups: number of supplementary mappings
      - each mapping: (code, SID) pair
    and apply them to the `encoding` list in place.
    """
    nSups = readCard8(file)
    for _ in range(nSups):
        code = readCard8(file)
        sid = readSID(file)
        name = strings[sid]
        encoding[code] = name


def parseEncoding0(charset, file):
    """
    Format 0: simple list of codes.
    After reading the base table, optionally parse the supplement.
    """
    nCodes = readCard8(file)
    encoding = [".notdef"] * 256
    for glyphID in range(1, nCodes + 1):
        code = readCard8(file)
        if code != 0:
            encoding[code] = charset[glyphID]

    return encoding


def parseEncoding1(charset, file):
    """
    Format 1: range-based encoding.
    After reading the base ranges, optionally parse the supplement.
    """
    nRanges = readCard8(file)
    encoding = [".notdef"] * 256
    glyphID = 1
    for _ in range(nRanges):
        code = readCard8(file)
        nLeft = readCard8(file)
        for _ in range(nLeft + 1):
            encoding[code] = charset[glyphID]
            code += 1
            glyphID += 1

    return encoding


def packEncoding0(charset, encoding, strings):
    fmt = 0
    m = {}
    for code in range(len(encoding)):
        name = encoding[code]
        if name != ".notdef":
            m[name] = code
    codes = []
    for name in charset[1:]:
        code = m.get(name)
        codes.append(code)

    while codes and codes[-1] is None:
        codes.pop()

    data = [packCard8(fmt), packCard8(len(codes))]
    for code in codes:
        if code is None:
            code = 0
        data.append(packCard8(code))
    return bytesjoin(data)


def packEncoding1(charset, encoding, strings):
    fmt = 1
    m = {}
    for code in range(len(encoding)):
        name = encoding[code]
        if name != ".notdef":
            m[name] = code
    ranges = []
    first = None
    end = 0
    for name in charset[1:]:
        code = m.get(name, -1)
        if first is None:
            first = code
        elif end + 1 != code:
            nLeft = end - first
            ranges.append((first, nLeft))
            first = code
        end = code
    nLeft = end - first
    ranges.append((first, nLeft))

    # remove unencoded glyphs at the end.
    while ranges and ranges[-1][0] == -1:
        ranges.pop()

    data = [packCard8(fmt), packCard8(len(ranges))]
    for first, nLeft in ranges:
        if first == -1:  # unencoded
            first = 0
        data.append(packCard8(first) + packCard8(nLeft))
    return bytesjoin(data)


class FDArrayConverter(TableConverter):
    def _read(self, parent, value):
        try:
            vstore = parent.VarStore
        except AttributeError:
            vstore = None
        file = parent.file
        isCFF2 = parent._isCFF2
        file.seek(value)
        fdArray = FDArrayIndex(file, isCFF2=isCFF2)
        fdArray.vstore = vstore
        fdArray.strings = parent.strings
        fdArray.GlobalSubrs = parent.GlobalSubrs
        return fdArray

    def write(self, parent, value):
        return 0  # dummy value

    def xmlRead(self, name, attrs, content, parent):
        fdArray = FDArrayIndex()
        for element in content:
            if isinstance(element, str):
                continue
            name, attrs, content = element
            fdArray.fromXML(name, attrs, content)
        return fdArray


class FDSelectConverter(SimpleConverter):
    def _read(self, parent, value):
        file = parent.file
        file.seek(value)
        fdSelect = FDSelect(file, parent.numGlyphs)
        return fdSelect

    def write(self, parent, value):
        return 0  # dummy value

    # The FDSelect glyph data is written out to XML in the charstring keys,
    # so we write out only the format selector
    def xmlWrite(self, xmlWriter, name, value):
        xmlWriter.simpletag(name, [("format", value.format)])
        xmlWriter.newline()

    def xmlRead(self, name, attrs, content, parent):
        fmt = safeEval(attrs["format"])
        file = None
        numGlyphs = None
        fdSelect = FDSelect(file, numGlyphs, fmt)
        return fdSelect


class VarStoreConverter(SimpleConverter):
    def _read(self, parent, value):
        file = parent.file
        file.seek(value)
        varStore = VarStoreData(file)
        varStore.decompile()
        return varStore

    def write(self, parent, value):
        return 0  # dummy value

    def xmlWrite(self, xmlWriter, name, value):
        value.writeXML(xmlWriter, name)

    def xmlRead(self, name, attrs, content, parent):
        varStore = VarStoreData()
        varStore.xmlRead(name, attrs, content, parent)
        return varStore


def packFDSelect0(fdSelectArray):
    fmt = 0
    data = [packCard8(fmt)]
    for index in fdSelectArray:
        data.append(packCard8(index))
    return bytesjoin(data)


def packFDSelect3(fdSelectArray):
    fmt = 3
    fdRanges = []
    lenArray = len(fdSelectArray)
    lastFDIndex = -1
    for i in range(lenArray):
        fdIndex = fdSelectArray[i]
        if lastFDIndex != fdIndex:
            fdRanges.append([i, fdIndex])
            lastFDIndex = fdIndex
    sentinelGID = i + 1

    data = [packCard8(fmt)]
    data.append(packCard16(len(fdRanges)))
    for fdRange in fdRanges:
        data.append(packCard16(fdRange[0]))
        data.append(packCard8(fdRange[1]))
    data.append(packCard16(sentinelGID))
    return bytesjoin(data)


def packFDSelect4(fdSelectArray):
    fmt = 4
    fdRanges = []
    lenArray = len(fdSelectArray)
    lastFDIndex = -1
    for i in range(lenArray):
        fdIndex = fdSelectArray[i]
        if lastFDIndex != fdIndex:
            fdRanges.append([i, fdIndex])
            lastFDIndex = fdIndex
    sentinelGID = i + 1

    data = [packCard8(fmt)]
    data.append(packCard32(len(fdRanges)))
    for fdRange in fdRanges:
        data.append(packCard32(fdRange[0]))
        data.append(packCard16(fdRange[1]))
    data.append(packCard32(sentinelGID))
    return bytesjoin(data)


class FDSelectCompiler(object):
    def __init__(self, fdSelect, parent):
        fmt = fdSelect.format
        fdSelectArray = fdSelect.gidArray
        if fmt == 0:
            self.data = packFDSelect0(fdSelectArray)
        elif fmt == 3:
            self.data = packFDSelect3(fdSelectArray)
        elif fmt == 4:
            self.data = packFDSelect4(fdSelectArray)
        else:
            # choose smaller of the two formats
            data0 = packFDSelect0(fdSelectArray)
            data3 = packFDSelect3(fdSelectArray)
            if len(data0) < len(data3):
                self.data = data0
                fdSelect.format = 0
            else:
                self.data = data3
                fdSelect.format = 3

        self.parent = parent

    def setPos(self, pos, endPos):
        self.parent.rawDict["FDSelect"] = pos

    def getDataLength(self):
        return len(self.data)

    def toFile(self, file):
        file.write(self.data)


class VarStoreCompiler(object):
    def __init__(self, varStoreData, parent):
        self.parent = parent
        if not varStoreData.data:
            varStoreData.compile()
        varStoreDataLen = min(0xFFFF, len(varStoreData.data))
        data = [packCard16(varStoreDataLen), varStoreData.data]
        self.data = bytesjoin(data)

    def setPos(self, pos, endPos):
        self.parent.rawDict["VarStore"] = pos

    def getDataLength(self):
        return len(self.data)

    def toFile(self, file):
        file.write(self.data)


class ROSConverter(SimpleConverter):
    def xmlWrite(self, xmlWriter, name, value):
        registry, order, supplement = value
        xmlWriter.simpletag(
            name,
            [
                ("Registry", tostr(registry)),
                ("Order", tostr(order)),
                ("Supplement", supplement),
            ],
        )
        xmlWriter.newline()

    def xmlRead(self, name, attrs, content, parent):
        return (attrs["Registry"], attrs["Order"], safeEval(attrs["Supplement"]))


topDictOperators = [
    # 	opcode		name			argument type	default	converter
    (25, "maxstack", "number", None, None),
    ((12, 30), "ROS", ("SID", "SID", "number"), None, ROSConverter()),
    ((12, 20), "SyntheticBase", "number", None, None),
    (0, "version", "SID", None, None),
    (1, "Notice", "SID", None, Latin1Converter()),
    ((12, 0), "Copyright", "SID", None, Latin1Converter()),
    (2, "FullName", "SID", None, Latin1Converter()),
    ((12, 38), "FontName", "SID", None, Latin1Converter()),
    (3, "FamilyName", "SID", None, Latin1Converter()),
    (4, "Weight", "SID", None, None),
    ((12, 1), "isFixedPitch", "number", 0, None),
    ((12, 2), "ItalicAngle", "number", 0, None),
    ((12, 3), "UnderlinePosition", "number", -100, None),
    ((12, 4), "UnderlineThickness", "number", 50, None),
    ((12, 5), "PaintType", "number", 0, None),
    ((12, 6), "CharstringType", "number", 2, None),
    ((12, 7), "FontMatrix", "array", [0.001, 0, 0, 0.001, 0, 0], None),
    (13, "UniqueID", "number", None, None),
    (5, "FontBBox", "array", [0, 0, 0, 0], None),
    ((12, 8), "StrokeWidth", "number", 0, None),
    (14, "XUID", "array", None, None),
    ((12, 21), "PostScript", "SID", None, None),
    ((12, 22), "BaseFontName", "SID", None, None),
    ((12, 23), "BaseFontBlend", "delta", None, None),
    ((12, 31), "CIDFontVersion", "number", 0, None),
    ((12, 32), "CIDFontRevision", "number", 0, None),
    ((12, 33), "CIDFontType", "number", 0, None),
    ((12, 34), "CIDCount", "number", 8720, None),
    (15, "charset", "number", None, CharsetConverter()),
    ((12, 35), "UIDBase", "number", None, None),
    (16, "Encoding", "number", 0, EncodingConverter()),
    (18, "Private", ("number", "number"), None, PrivateDictConverter()),
    ((12, 37), "FDSelect", "number", None, FDSelectConverter()),
    ((12, 36), "FDArray", "number", None, FDArrayConverter()),
    (17, "CharStrings", "number", None, CharStringsConverter()),
    (24, "VarStore", "number", None, VarStoreConverter()),
]

topDictOperators2 = [
    # 	opcode		name			argument type	default	converter
    (25, "maxstack", "number", None, None),
    ((12, 7), "FontMatrix", "array", [0.001, 0, 0, 0.001, 0, 0], None),
    ((12, 37), "FDSelect", "number", None, FDSelectConverter()),
    ((12, 36), "FDArray", "number", None, FDArrayConverter()),
    (17, "CharStrings", "number", None, CharStringsConverter()),
    (24, "VarStore", "number", None, VarStoreConverter()),
]

# Note! FDSelect and FDArray must both preceed CharStrings in the output XML build order,
# in order for the font to compile back from xml.

kBlendDictOpName = "blend"
blendOp = 23

privateDictOperators = [
    # 	opcode		name			argument type	default	converter
    (22, "vsindex", "number", None, None),
    (
        blendOp,
        kBlendDictOpName,
        "blendList",
        None,
        None,
    ),  # This is for reading to/from XML: it not written to CFF.
    (6, "BlueValues", "delta", None, None),
    (7, "OtherBlues", "delta", None, None),
    (8, "FamilyBlues", "delta", None, None),
    (9, "FamilyOtherBlues", "delta", None, None),
    ((12, 9), "BlueScale", "number", 0.039625, None),
    ((12, 10), "BlueShift", "number", 7, None),
    ((12, 11), "BlueFuzz", "number", 1, None),
    (10, "StdHW", "number", None, None),
    (11, "StdVW", "number", None, None),
    ((12, 12), "StemSnapH", "delta", None, None),
    ((12, 13), "StemSnapV", "delta", None, None),
    ((12, 14), "ForceBold", "number", 0, None),
    ((12, 15), "ForceBoldThreshold", "number", None, None),  # deprecated
    ((12, 16), "lenIV", "number", None, None),  # deprecated
    ((12, 17), "LanguageGroup", "number", 0, None),
    ((12, 18), "ExpansionFactor", "number", 0.06, None),
    ((12, 19), "initialRandomSeed", "number", 0, None),
    (20, "defaultWidthX", "number", 0, None),
    (21, "nominalWidthX", "number", 0, None),
    (19, "Subrs", "number", None, SubrsConverter()),
]

privateDictOperators2 = [
    # 	opcode		name			argument type	default	converter
    (22, "vsindex", "number", None, None),
    (
        blendOp,
        kBlendDictOpName,
        "blendList",
        None,
        None,
    ),  # This is for reading to/from XML: it not written to CFF.
    (6, "BlueValues", "delta", None, None),
    (7, "OtherBlues", "delta", None, None),
    (8, "FamilyBlues", "delta", None, None),
    (9, "FamilyOtherBlues", "delta", None, None),
    ((12, 9), "BlueScale", "number", 0.039625, None),
    ((12, 10), "BlueShift", "number", 7, None),
    ((12, 11), "BlueFuzz", "number", 1, None),
    (10, "StdHW", "number", None, None),
    (11, "StdVW", "number", None, None),
    ((12, 12), "StemSnapH", "delta", None, None),
    ((12, 13), "StemSnapV", "delta", None, None),
    ((12, 17), "LanguageGroup", "number", 0, None),
    ((12, 18), "ExpansionFactor", "number", 0.06, None),
    (19, "Subrs", "number", None, SubrsConverter()),
]


def addConverters(table):
    for i in range(len(table)):
        op, name, arg, default, conv = table[i]
        if conv is not None:
            continue
        if arg in ("delta", "array"):
            conv = ArrayConverter()
        elif arg == "number":
            conv = NumberConverter()
        elif arg == "SID":
            conv = ASCIIConverter()
        elif arg == "blendList":
            conv = None
        else:
            assert False
        table[i] = op, name, arg, default, conv


addConverters(privateDictOperators)
addConverters(topDictOperators)


class TopDictDecompiler(psCharStrings.DictDecompiler):
    operators = buildOperatorDict(topDictOperators)


class PrivateDictDecompiler(psCharStrings.DictDecompiler):
    operators = buildOperatorDict(privateDictOperators)


class DictCompiler(object):
    maxBlendStack = 0

    def __init__(self, dictObj, strings, parent, isCFF2=None):
        if strings:
            assert isinstance(strings, IndexedStrings)
        if isCFF2 is None and hasattr(parent, "isCFF2"):
            isCFF2 = parent.isCFF2
            assert isCFF2 is not None
        self.isCFF2 = isCFF2
        self.dictObj = dictObj
        self.strings = strings
        self.parent = parent
        rawDict = {}
        for name in dictObj.order:
            value = getattr(dictObj, name, None)
            if value is None:
                continue
            conv = dictObj.converters[name]
            value = conv.write(dictObj, value)
            if value == dictObj.defaults.get(name):
                continue
            rawDict[name] = value
        self.rawDict = rawDict

    def setPos(self, pos, endPos):
        pass

    def getDataLength(self):
        return len(self.compile("getDataLength"))

    def compile(self, reason):
        log.log(DEBUG, "-- compiling %s for %s", self.__class__.__name__, reason)
        rawDict = self.rawDict
        data = []
        for name in self.dictObj.order:
            value = rawDict.get(name)
            if value is None:
                continue
            op, argType = self.opcodes[name]
            if isinstance(argType, tuple):
                l = len(argType)
                assert len(value) == l, "value doesn't match arg type"
                for i in range(l):
                    arg = argType[i]
                    v = value[i]
                    arghandler = getattr(self, "arg_" + arg)
                    data.append(arghandler(v))
            else:
                arghandler = getattr(self, "arg_" + argType)
                data.append(arghandler(value))
            data.append(op)
        data = bytesjoin(data)
        return data

    def toFile(self, file):
        data = self.compile("toFile")
        file.write(data)

    def arg_number(self, num):
        if isinstance(num, list):
            data = [encodeNumber(val) for val in num]
            data.append(encodeNumber(1))
            data.append(bytechr(blendOp))
            datum = bytesjoin(data)
        else:
            datum = encodeNumber(num)
        return datum

    def arg_SID(self, s):
        return psCharStrings.encodeIntCFF(self.strings.getSID(s))

    def arg_array(self, value):
        data = []
        for num in value:
            data.append(self.arg_number(num))
        return bytesjoin(data)

    def arg_delta(self, value):
        if not value:
            return b""
        val0 = value[0]
        if isinstance(val0, list):
            data = self.arg_delta_blend(value)
        else:
            out = []
            last = 0
            for v in value:
                out.append(v - last)
                last = v
            data = []
            for num in out:
                data.append(encodeNumber(num))
        return bytesjoin(data)

    def arg_delta_blend(self, value):
        """A delta list with blend lists has to be *all* blend lists.

        The value is a list is arranged as follows::

                [
                        [V0, d0..dn]
                        [V1, d0..dn]
                        ...
                        [Vm, d0..dn]
                ]

        ``V`` is the absolute coordinate value from the default font, and ``d0-dn``
        are the delta values from the *n* regions. Each ``V`` is an absolute
        coordinate from the default font.

        We want to return a list::

                [
                        [v0, v1..vm]
                        [d0..dn]
                        ...
                        [d0..dn]
                        numBlends
                        blendOp
                ]

        where each ``v`` is relative to the previous default font value.
        """
        numMasters = len(value[0])
        numBlends = len(value)
        numStack = (numBlends * numMasters) + 1
        if numStack > self.maxBlendStack:
            # Figure out the max number of value we can blend
            # and divide this list up into chunks of that size.

            numBlendValues = int((self.maxBlendStack - 1) / numMasters)
            out = []
            while True:
                numVal = min(len(value), numBlendValues)
                if numVal == 0:
                    break
                valList = value[0:numVal]
                out1 = self.arg_delta_blend(valList)
                out.extend(out1)
                value = value[numVal:]
        else:
            firstList = [0] * numBlends
            deltaList = [None] * numBlends
            i = 0
            prevVal = 0
            while i < numBlends:
                # For PrivateDict BlueValues, the default font
                # values are absolute, not relative.
                # Must convert these back to relative coordinates
                # before writing to CFF2.
                defaultValue = value[i][0]
                firstList[i] = defaultValue - prevVal
                prevVal = defaultValue
                deltaList[i] = value[i][1:]
                i += 1

            relValueList = firstList
            for blendList in deltaList:
                relValueList.extend(blendList)
            out = [encodeNumber(val) for val in relValueList]
            out.append(encodeNumber(numBlends))
            out.append(bytechr(blendOp))
        return out


def encodeNumber(num):
    if isinstance(num, float):
        return psCharStrings.encodeFloat(num)
    else:
        return psCharStrings.encodeIntCFF(num)


class TopDictCompiler(DictCompiler):
    opcodes = buildOpcodeDict(topDictOperators)

    def getChildren(self, strings):
        isCFF2 = self.isCFF2
        children = []
        if self.dictObj.cff2GetGlyphOrder is None:
            if hasattr(self.dictObj, "charset") and self.dictObj.charset:
                if hasattr(self.dictObj, "ROS"):  # aka isCID
                    charsetCode = None
                else:
                    charsetCode = getStdCharSet(self.dictObj.charset)
                if charsetCode is None:
                    children.append(
                        CharsetCompiler(strings, self.dictObj.charset, self)
                    )
                else:
                    self.rawDict["charset"] = charsetCode
            if hasattr(self.dictObj, "Encoding") and self.dictObj.Encoding:
                encoding = self.dictObj.Encoding
                if not isinstance(encoding, str):
                    children.append(EncodingCompiler(strings, encoding, self))
        else:
            if hasattr(self.dictObj, "VarStore"):
                varStoreData = self.dictObj.VarStore
                varStoreComp = VarStoreCompiler(varStoreData, self)
                children.append(varStoreComp)
        if hasattr(self.dictObj, "FDSelect"):
            # I have not yet supported merging a ttx CFF-CID font, as there are
            # interesting issues about merging the FDArrays. Here I assume that
            # either the font was read from XML, and the FDSelect indices are all
            # in the charstring data, or the FDSelect array is already fully defined.
            fdSelect = self.dictObj.FDSelect
            # probably read in from XML; assume fdIndex in CharString data
            if len(fdSelect) == 0:
                charStrings = self.dictObj.CharStrings
                for name in self.dictObj.charset:
                    fdSelect.append(charStrings[name].fdSelectIndex)
            fdSelectComp = FDSelectCompiler(fdSelect, self)
            children.append(fdSelectComp)
        if hasattr(self.dictObj, "CharStrings"):
            items = []
            charStrings = self.dictObj.CharStrings
            for name in self.dictObj.charset:
                items.append(charStrings[name])
            charStringsComp = CharStringsCompiler(items, strings, self, isCFF2=isCFF2)
            children.append(charStringsComp)
        if hasattr(self.dictObj, "FDArray"):
            # I have not yet supported merging a ttx CFF-CID font, as there are
            # interesting issues about merging the FDArrays. Here I assume that the
            # FDArray info is correct and complete.
            fdArrayIndexComp = self.dictObj.FDArray.getCompiler(strings, self)
            children.append(fdArrayIndexComp)
            children.extend(fdArrayIndexComp.getChildren(strings))
        if hasattr(self.dictObj, "Private"):
            privComp = self.dictObj.Private.getCompiler(strings, self)
            children.append(privComp)
            children.extend(privComp.getChildren(strings))
        return children


class FontDictCompiler(DictCompiler):
    opcodes = buildOpcodeDict(topDictOperators)

    def __init__(self, dictObj, strings, parent, isCFF2=None):
        super(FontDictCompiler, self).__init__(dictObj, strings, parent, isCFF2=isCFF2)
        #
        # We now take some effort to detect if there were any key/value pairs
        # supplied that were ignored in the FontDict context, and issue a warning
        # for those cases.
        #
        ignoredNames = []
        dictObj = self.dictObj
        for name in sorted(set(dictObj.converters) - set(dictObj.order)):
            if name in dictObj.rawDict:
                # The font was directly read from binary. In this
                # case, we want to report *all* "useless" key/value
                # pairs that are in the font, not just the ones that
                # are different from the default.
                ignoredNames.append(name)
            else:
                # The font was probably read from a TTX file. We only
                # warn about keys whos value is not the default. The
                # ones that have the default value will not be written
                # to binary anyway.
                default = dictObj.defaults.get(name)
                if default is not None:
                    conv = dictObj.converters[name]
                    default = conv.read(dictObj, default)
                if getattr(dictObj, name, None) != default:
                    ignoredNames.append(name)
        if ignoredNames:
            log.warning(
                "Some CFF FDArray/FontDict keys were ignored upon compile: "
                + " ".join(sorted(ignoredNames))
            )

    def getChildren(self, strings):
        children = []
        if hasattr(self.dictObj, "Private"):
            privComp = self.dictObj.Private.getCompiler(strings, self)
            children.append(privComp)
            children.extend(privComp.getChildren(strings))
        return children


class PrivateDictCompiler(DictCompiler):
    maxBlendStack = maxStackLimit
    opcodes = buildOpcodeDict(privateDictOperators)

    def setPos(self, pos, endPos):
        size = endPos - pos
        self.parent.rawDict["Private"] = size, pos
        self.pos = pos

    def getChildren(self, strings):
        children = []
        if hasattr(self.dictObj, "Subrs"):
            children.append(self.dictObj.Subrs.getCompiler(strings, self))
        return children


class BaseDict(object):
    def __init__(self, strings=None, file=None, offset=None, isCFF2=None):
        assert (isCFF2 is None) == (file is None)
        self.rawDict = {}
        self.skipNames = []
        self.strings = strings
        if file is None:
            return
        self._isCFF2 = isCFF2
        self.file = file
        if offset is not None:
            log.log(DEBUG, "loading %s at %s", self.__class__.__name__, offset)
            self.offset = offset

    def decompile(self, data):
        log.log(DEBUG, "    length %s is %d", self.__class__.__name__, len(data))
        dec = self.decompilerClass(self.strings, self)
        dec.decompile(data)
        self.rawDict = dec.getDict()
        self.postDecompile()

    def postDecompile(self):
        pass

    def getCompiler(self, strings, parent, isCFF2=None):
        return self.compilerClass(self, strings, parent, isCFF2=isCFF2)

    def __getattr__(self, name):
        if name[:2] == name[-2:] == "__":
            # to make deepcopy() and pickle.load() work, we need to signal with
            # AttributeError that dunder methods like '__deepcopy__' or '__getstate__'
            # aren't implemented. For more details, see:
            # https://github.com/fonttools/fonttools/pull/1488
            raise AttributeError(name)
        value = self.rawDict.get(name, None)
        if value is None:
            value = self.defaults.get(name)
        if value is None:
            raise AttributeError(name)
        conv = self.converters[name]
        value = conv.read(self, value)
        setattr(self, name, value)
        return value

    def toXML(self, xmlWriter):
        for name in self.order:
            if name in self.skipNames:
                continue
            value = getattr(self, name, None)
            # XXX For "charset" we never skip calling xmlWrite even if the
            # value is None, so we always write the following XML comment:
            #
            # <!-- charset is dumped separately as the 'GlyphOrder' element -->
            #
            # Charset is None when 'CFF ' table is imported from XML into an
            # empty TTFont(). By writing this comment all the time, we obtain
            # the same XML output whether roundtripping XML-to-XML or
            # dumping binary-to-XML
            if value is None and name != "charset":
                continue
            conv = self.converters[name]
            conv.xmlWrite(xmlWriter, name, value)
        ignoredNames = set(self.rawDict) - set(self.order)
        if ignoredNames:
            xmlWriter.comment(
                "some keys were ignored: %s" % " ".join(sorted(ignoredNames))
            )
            xmlWriter.newline()

    def fromXML(self, name, attrs, content):
        conv = self.converters[name]
        value = conv.xmlRead(name, attrs, content, self)
        setattr(self, name, value)


class TopDict(BaseDict):
    """The ``TopDict`` represents the top-level dictionary holding font
    information. CFF2 tables contain a restricted set of top-level entries
    as described `here <https://docs.microsoft.com/en-us/typography/opentype/spec/cff2#7-top-dict-data>`_,
    but CFF tables may contain a wider range of information. This information
    can be accessed through attributes or through the dictionary returned
    through the ``rawDict`` property:

    .. code:: python

            font = tt["CFF "].cff[0]
            font.FamilyName
            # 'Linux Libertine O'
            font.rawDict["FamilyName"]
            # 'Linux Libertine O'

    More information is available in the CFF file's private dictionary, accessed
    via the ``Private`` property:

    .. code:: python

            tt["CFF "].cff[0].Private.BlueValues
            # [-15, 0, 515, 515, 666, 666]

    """

    defaults = buildDefaults(topDictOperators)
    converters = buildConverters(topDictOperators)
    compilerClass = TopDictCompiler
    order = buildOrder(topDictOperators)
    decompilerClass = TopDictDecompiler

    def __init__(
        self,
        strings=None,
        file=None,
        offset=None,
        GlobalSubrs=None,
        cff2GetGlyphOrder=None,
        isCFF2=None,
    ):
        super(TopDict, self).__init__(strings, file, offset, isCFF2=isCFF2)
        self.cff2GetGlyphOrder = cff2GetGlyphOrder
        self.GlobalSubrs = GlobalSubrs
        if isCFF2:
            self.defaults = buildDefaults(topDictOperators2)
            self.charset = cff2GetGlyphOrder()
            self.order = buildOrder(topDictOperators2)
        else:
            self.defaults = buildDefaults(topDictOperators)
            self.order = buildOrder(topDictOperators)

    def getGlyphOrder(self):
        """Returns a list of glyph names in the CFF font."""
        return self.charset

    def postDecompile(self):
        offset = self.rawDict.get("CharStrings")
        if offset is None:
            return
        # get the number of glyphs beforehand.
        self.file.seek(offset)
        if self._isCFF2:
            self.numGlyphs = readCard32(self.file)
        else:
            self.numGlyphs = readCard16(self.file)

    def toXML(self, xmlWriter):
        if hasattr(self, "CharStrings"):
            self.decompileAllCharStrings()
        if hasattr(self, "ROS"):
            self.skipNames = ["Encoding"]
        if not hasattr(self, "ROS") or not hasattr(self, "CharStrings"):
            # these values have default values, but I only want them to show up
            # in CID fonts.
            self.skipNames = [
                "CIDFontVersion",
                "CIDFontRevision",
                "CIDFontType",
                "CIDCount",
            ]
        BaseDict.toXML(self, xmlWriter)

    def decompileAllCharStrings(self):
        # Make sure that all the Private Dicts have been instantiated.
        for i, charString in enumerate(self.CharStrings.values()):
            try:
                charString.decompile()
            except:
                log.error("Error in charstring %s", i)
                raise

    def recalcFontBBox(self):
        fontBBox = None
        for charString in self.CharStrings.values():
            bounds = charString.calcBounds(self.CharStrings)
            if bounds is not None:
                if fontBBox is not None:
                    fontBBox = unionRect(fontBBox, bounds)
                else:
                    fontBBox = bounds

        if fontBBox is None:
            self.FontBBox = self.defaults["FontBBox"][:]
        else:
            self.FontBBox = list(intRect(fontBBox))


class FontDict(BaseDict):
    #
    # Since fonttools used to pass a lot of fields that are not relevant in the FDArray
    # FontDict, there are 'ttx' files in the wild that contain all these. These got in
    # the ttx files because fonttools writes explicit values for all the TopDict default
    # values. These are not actually illegal in the context of an FDArray FontDict - you
    # can legally, per spec, put any arbitrary key/value pair in a FontDict - but are
    # useless since current major company CFF interpreters ignore anything but the set
    # listed in this file. So, we just silently skip them. An exception is Weight: this
    # is not used by any interpreter, but some foundries have asked that this be
    # supported in FDArray FontDicts just to preserve information about the design when
    # the font is being inspected.
    #
    # On top of that, there are fonts out there that contain such useless FontDict values.
    #
    # By subclassing TopDict, we *allow* all key/values from TopDict, both when reading
    # from binary or when reading from XML, but by overriding `order` with a limited
    # list of names, we ensure that only the useful names ever get exported to XML and
    # ever get compiled into the binary font.
    #
    # We override compilerClass so we can warn about "useless" key/value pairs, either
    # from the original binary font or from TTX input.
    #
    # See:
    # - https://github.com/fonttools/fonttools/issues/740
    # - https://github.com/fonttools/fonttools/issues/601
    # - https://github.com/adobe-type-tools/afdko/issues/137
    #
    defaults = {}
    converters = buildConverters(topDictOperators)
    compilerClass = FontDictCompiler
    orderCFF = ["FontName", "FontMatrix", "Weight", "Private"]
    orderCFF2 = ["Private"]
    decompilerClass = TopDictDecompiler

    def __init__(
        self,
        strings=None,
        file=None,
        offset=None,
        GlobalSubrs=None,
        isCFF2=None,
        vstore=None,
    ):
        super(FontDict, self).__init__(strings, file, offset, isCFF2=isCFF2)
        self.vstore = vstore
        self.setCFF2(isCFF2)

    def setCFF2(self, isCFF2):
        # isCFF2 may be None.
        if isCFF2:
            self.order = self.orderCFF2
            self._isCFF2 = True
        else:
            self.order = self.orderCFF
            self._isCFF2 = False


class PrivateDict(BaseDict):
    defaults = buildDefaults(privateDictOperators)
    converters = buildConverters(privateDictOperators)
    order = buildOrder(privateDictOperators)
    decompilerClass = PrivateDictDecompiler
    compilerClass = PrivateDictCompiler

    def __init__(self, strings=None, file=None, offset=None, isCFF2=None, vstore=None):
        super(PrivateDict, self).__init__(strings, file, offset, isCFF2=isCFF2)
        self.vstore = vstore
        if isCFF2:
            self.defaults = buildDefaults(privateDictOperators2)
            self.order = buildOrder(privateDictOperators2)
            # Provide dummy values. This avoids needing to provide
            # an isCFF2 state in a lot of places.
            self.nominalWidthX = self.defaultWidthX = None
            self._isCFF2 = True
        else:
            self.defaults = buildDefaults(privateDictOperators)
            self.order = buildOrder(privateDictOperators)
            self._isCFF2 = False

    @property
    def in_cff2(self):
        return self._isCFF2

    def getNumRegions(self, vi=None):  # called from misc/psCharStrings.py
        # if getNumRegions is being called, we can assume that VarStore exists.
        if vi is None:
            if hasattr(self, "vsindex"):
                vi = self.vsindex
            else:
                vi = 0
        numRegions = self.vstore.getNumRegions(vi)
        return numRegions


class IndexedStrings(object):
    """SID -> string mapping."""

    def __init__(self, file=None):
        if file is None:
            strings = []
        else:
            strings = [tostr(s, encoding="latin1") for s in Index(file, isCFF2=False)]
        self.strings = strings

    def getCompiler(self):
        return IndexedStringsCompiler(self, None, self, isCFF2=False)

    def __len__(self):
        return len(self.strings)

    def __getitem__(self, SID):
        if SID < cffStandardStringCount:
            return cffStandardStrings[SID]
        else:
            return self.strings[SID - cffStandardStringCount]

    def getSID(self, s):
        if not hasattr(self, "stringMapping"):
            self.buildStringMapping()
        s = tostr(s, encoding="latin1")
        if s in cffStandardStringMapping:
            SID = cffStandardStringMapping[s]
        elif s in self.stringMapping:
            SID = self.stringMapping[s]
        else:
            SID = len(self.strings) + cffStandardStringCount
            self.strings.append(s)
            self.stringMapping[s] = SID
        return SID

    def getStrings(self):
        return self.strings

    def buildStringMapping(self):
        self.stringMapping = {}
        for index in range(len(self.strings)):
            self.stringMapping[self.strings[index]] = index + cffStandardStringCount


# The 391 Standard Strings as used in the CFF format.
# from Adobe Technical None #5176, version 1.0, 18 March 1998

cffStandardStrings = [
    ".notdef",
    "space",
    "exclam",
    "quotedbl",
    "numbersign",
    "dollar",
    "percent",
    "ampersand",
    "quoteright",
    "parenleft",
    "parenright",
    "asterisk",
    "plus",
    "comma",
    "hyphen",
    "period",
    "slash",
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "colon",
    "semicolon",
    "less",
    "equal",
    "greater",
    "question",
    "at",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "bracketleft",
    "backslash",
    "bracketright",
    "asciicircum",
    "underscore",
    "quoteleft",
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z",
    "braceleft",
    "bar",
    "braceright",
    "asciitilde",
    "exclamdown",
    "cent",
    "sterling",
    "fraction",
    "yen",
    "florin",
    "section",
    "currency",
    "quotesingle",
    "quotedblleft",
    "guillemotleft",
    "guilsinglleft",
    "guilsinglright",
    "fi",
    "fl",
    "endash",
    "dagger",
    "daggerdbl",
    "periodcentered",
    "paragraph",
    "bullet",
    "quotesinglbase",
    "quotedblbase",
    "quotedblright",
    "guillemotright",
    "ellipsis",
    "perthousand",
    "questiondown",
    "grave",
    "acute",
    "circumflex",
    "tilde",
    "macron",
    "breve",
    "dotaccent",
    "dieresis",
    "ring",
    "cedilla",
    "hungarumlaut",
    "ogonek",
    "caron",
    "emdash",
    "AE",
    "ordfeminine",
    "Lslash",
    "Oslash",
    "OE",
    "ordmasculine",
    "ae",
    "dotlessi",
    "lslash",
    "oslash",
    "oe",
    "germandbls",
    "onesuperior",
    "logicalnot",
    "mu",
    "trademark",
    "Eth",
    "onehalf",
    "plusminus",
    "Thorn",
    "onequarter",
    "divide",
    "brokenbar",
    "degree",
    "thorn",
    "threequarters",
    "twosuperior",
    "registered",
    "minus",
    "eth",
    "multiply",
    "threesuperior",
    "copyright",
    "Aacute",
    "Acircumflex",
    "Adieresis",
    "Agrave",
    "Aring",
    "Atilde",
    "Ccedilla",
    "Eacute",
    "Ecircumflex",
    "Edieresis",
    "Egrave",
    "Iacute",
    "Icircumflex",
    "Idieresis",
    "Igrave",
    "Ntilde",
    "Oacute",
    "Ocircumflex",
    "Odieresis",
    "Ograve",
    "Otilde",
    "Scaron",
    "Uacute",
    "Ucircumflex",
    "Udieresis",
    "Ugrave",
    "Yacute",
    "Ydieresis",
    "Zcaron",
    "aacute",
    "acircumflex",
    "adieresis",
    "agrave",
    "aring",
    "atilde",
    "ccedilla",
    "eacute",
    "ecircumflex",
    "edieresis",
    "egrave",
    "iacute",
    "icircumflex",
    "idieresis",
    "igrave",
    "ntilde",
    "oacute",
    "ocircumflex",
    "odieresis",
    "ograve",
    "otilde",
    "scaron",
    "uacute",
    "ucircumflex",
    "udieresis",
    "ugrave",
    "yacute",
    "ydieresis",
    "zcaron",
    "exclamsmall",
    "Hungarumlautsmall",
    "dollaroldstyle",
    "dollarsuperior",
    "ampersandsmall",
    "Acutesmall",
    "parenleftsuperior",
    "parenrightsuperior",
    "twodotenleader",
    "onedotenleader",
    "zerooldstyle",
    "oneoldstyle",
    "twooldstyle",
    "threeoldstyle",
    "fouroldstyle",
    "fiveoldstyle",
    "sixoldstyle",
    "sevenoldstyle",
    "eightoldstyle",
    "nineoldstyle",
    "commasuperior",
    "threequartersemdash",
    "periodsuperior",
    "questionsmall",
    "asuperior",
    "bsuperior",
    "centsuperior",
    "dsuperior",
    "esuperior",
    "isuperior",
    "lsuperior",
    "msuperior",
    "nsuperior",
    "osuperior",
    "rsuperior",
    "ssuperior",
    "tsuperior",
    "ff",
    "ffi",
    "ffl",
    "parenleftinferior",
    "parenrightinferior",
    "Circumflexsmall",
    "hyphensuperior",
    "Gravesmall",
    "Asmall",
    "Bsmall",
    "Csmall",
    "Dsmall",
    "Esmall",
    "Fsmall",
    "Gsmall",
    "Hsmall",
    "Ismall",
    "Jsmall",
    "Ksmall",
    "Lsmall",
    "Msmall",
    "Nsmall",
    "Osmall",
    "Psmall",
    "Qsmall",
    "Rsmall",
    "Ssmall",
    "Tsmall",
    "Usmall",
    "Vsmall",
    "Wsmall",
    "Xsmall",
    "Ysmall",
    "Zsmall",
    "colonmonetary",
    "onefitted",
    "rupiah",
    "Tildesmall",
    "exclamdownsmall",
    "centoldstyle",
    "Lslashsmall",
    "Scaronsmall",
    "Zcaronsmall",
    "Dieresissmall",
    "Brevesmall",
    "Caronsmall",
    "Dotaccentsmall",
    "Macronsmall",
    "figuredash",
    "hypheninferior",
    "Ogoneksmall",
    "Ringsmall",
    "Cedillasmall",
    "questiondownsmall",
    "oneeighth",
    "threeeighths",
    "fiveeighths",
    "seveneighths",
    "onethird",
    "twothirds",
    "zerosuperior",
    "foursuperior",
    "fivesuperior",
    "sixsuperior",
    "sevensuperior",
    "eightsuperior",
    "ninesuperior",
    "zeroinferior",
    "oneinferior",
    "twoinferior",
    "threeinferior",
    "fourinferior",
    "fiveinferior",
    "sixinferior",
    "seveninferior",
    "eightinferior",
    "nineinferior",
    "centinferior",
    "dollarinferior",
    "periodinferior",
    "commainferior",
    "Agravesmall",
    "Aacutesmall",
    "Acircumflexsmall",
    "Atildesmall",
    "Adieresissmall",
    "Aringsmall",
    "AEsmall",
    "Ccedillasmall",
    "Egravesmall",
    "Eacutesmall",
    "Ecircumflexsmall",
    "Edieresissmall",
    "Igravesmall",
    "Iacutesmall",
    "Icircumflexsmall",
    "Idieresissmall",
    "Ethsmall",
    "Ntildesmall",
    "Ogravesmall",
    "Oacutesmall",
    "Ocircumflexsmall",
    "Otildesmall",
    "Odieresissmall",
    "OEsmall",
    "Oslashsmall",
    "Ugravesmall",
    "Uacutesmall",
    "Ucircumflexsmall",
    "Udieresissmall",
    "Yacutesmall",
    "Thornsmall",
    "Ydieresissmall",
    "001.000",
    "001.001",
    "001.002",
    "001.003",
    "Black",
    "Bold",
    "Book",
    "Light",
    "Medium",
    "Regular",
    "Roman",
    "Semibold",
]

cffStandardStringCount = 391
assert len(cffStandardStrings) == cffStandardStringCount
# build reverse mapping
cffStandardStringMapping = {}
for _i in range(cffStandardStringCount):
    cffStandardStringMapping[cffStandardStrings[_i]] = _i

cffISOAdobeStrings = [
    ".notdef",
    "space",
    "exclam",
    "quotedbl",
    "numbersign",
    "dollar",
    "percent",
    "ampersand",
    "quoteright",
    "parenleft",
    "parenright",
    "asterisk",
    "plus",
    "comma",
    "hyphen",
    "period",
    "slash",
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "colon",
    "semicolon",
    "less",
    "equal",
    "greater",
    "question",
    "at",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "bracketleft",
    "backslash",
    "bracketright",
    "asciicircum",
    "underscore",
    "quoteleft",
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z",
    "braceleft",
    "bar",
    "braceright",
    "asciitilde",
    "exclamdown",
    "cent",
    "sterling",
    "fraction",
    "yen",
    "florin",
    "section",
    "currency",
    "quotesingle",
    "quotedblleft",
    "guillemotleft",
    "guilsinglleft",
    "guilsinglright",
    "fi",
    "fl",
    "endash",
    "dagger",
    "daggerdbl",
    "periodcentered",
    "paragraph",
    "bullet",
    "quotesinglbase",
    "quotedblbase",
    "quotedblright",
    "guillemotright",
    "ellipsis",
    "perthousand",
    "questiondown",
    "grave",
    "acute",
    "circumflex",
    "tilde",
    "macron",
    "breve",
    "dotaccent",
    "dieresis",
    "ring",
    "cedilla",
    "hungarumlaut",
    "ogonek",
    "caron",
    "emdash",
    "AE",
    "ordfeminine",
    "Lslash",
    "Oslash",
    "OE",
    "ordmasculine",
    "ae",
    "dotlessi",
    "lslash",
    "oslash",
    "oe",
    "germandbls",
    "onesuperior",
    "logicalnot",
    "mu",
    "trademark",
    "Eth",
    "onehalf",
    "plusminus",
    "Thorn",
    "onequarter",
    "divide",
    "brokenbar",
    "degree",
    "thorn",
    "threequarters",
    "twosuperior",
    "registered",
    "minus",
    "eth",
    "multiply",
    "threesuperior",
    "copyright",
    "Aacute",
    "Acircumflex",
    "Adieresis",
    "Agrave",
    "Aring",
    "Atilde",
    "Ccedilla",
    "Eacute",
    "Ecircumflex",
    "Edieresis",
    "Egrave",
    "Iacute",
    "Icircumflex",
    "Idieresis",
    "Igrave",
    "Ntilde",
    "Oacute",
    "Ocircumflex",
    "Odieresis",
    "Ograve",
    "Otilde",
    "Scaron",
    "Uacute",
    "Ucircumflex",
    "Udieresis",
    "Ugrave",
    "Yacute",
    "Ydieresis",
    "Zcaron",
    "aacute",
    "acircumflex",
    "adieresis",
    "agrave",
    "aring",
    "atilde",
    "ccedilla",
    "eacute",
    "ecircumflex",
    "edieresis",
    "egrave",
    "iacute",
    "icircumflex",
    "idieresis",
    "igrave",
    "ntilde",
    "oacute",
    "ocircumflex",
    "odieresis",
    "ograve",
    "otilde",
    "scaron",
    "uacute",
    "ucircumflex",
    "udieresis",
    "ugrave",
    "yacute",
    "ydieresis",
    "zcaron",
]

cffISOAdobeStringCount = 229
assert len(cffISOAdobeStrings) == cffISOAdobeStringCount

cffIExpertStrings = [
    ".notdef",
    "space",
    "exclamsmall",
    "Hungarumlautsmall",
    "dollaroldstyle",
    "dollarsuperior",
    "ampersandsmall",
    "Acutesmall",
    "parenleftsuperior",
    "parenrightsuperior",
    "twodotenleader",
    "onedotenleader",
    "comma",
    "hyphen",
    "period",
    "fraction",
    "zerooldstyle",
    "oneoldstyle",
    "twooldstyle",
    "threeoldstyle",
    "fouroldstyle",
    "fiveoldstyle",
    "sixoldstyle",
    "sevenoldstyle",
    "eightoldstyle",
    "nineoldstyle",
    "colon",
    "semicolon",
    "commasuperior",
    "threequartersemdash",
    "periodsuperior",
    "questionsmall",
    "asuperior",
    "bsuperior",
    "centsuperior",
    "dsuperior",
    "esuperior",
    "isuperior",
    "lsuperior",
    "msuperior",
    "nsuperior",
    "osuperior",
    "rsuperior",
    "ssuperior",
    "tsuperior",
    "ff",
    "fi",
    "fl",
    "ffi",
    "ffl",
    "parenleftinferior",
    "parenrightinferior",
    "Circumflexsmall",
    "hyphensuperior",
    "Gravesmall",
    "Asmall",
    "Bsmall",
    "Csmall",
    "Dsmall",
    "Esmall",
    "Fsmall",
    "Gsmall",
    "Hsmall",
    "Ismall",
    "Jsmall",
    "Ksmall",
    "Lsmall",
    "Msmall",
    "Nsmall",
    "Osmall",
    "Psmall",
    "Qsmall",
    "Rsmall",
    "Ssmall",
    "Tsmall",
    "Usmall",
    "Vsmall",
    "Wsmall",
    "Xsmall",
    "Ysmall",
    "Zsmall",
    "colonmonetary",
    "onefitted",
    "rupiah",
    "Tildesmall",
    "exclamdownsmall",
    "centoldstyle",
    "Lslashsmall",
    "Scaronsmall",
    "Zcaronsmall",
    "Dieresissmall",
    "Brevesmall",
    "Caronsmall",
    "Dotaccentsmall",
    "Macronsmall",
    "figuredash",
    "hypheninferior",
    "Ogoneksmall",
    "Ringsmall",
    "Cedillasmall",
    "onequarter",
    "onehalf",
    "threequarters",
    "questiondownsmall",
    "oneeighth",
    "threeeighths",
    "fiveeighths",
    "seveneighths",
    "onethird",
    "twothirds",
    "zerosuperior",
    "onesuperior",
    "twosuperior",
    "threesuperior",
    "foursuperior",
    "fivesuperior",
    "sixsuperior",
    "sevensuperior",
    "eightsuperior",
    "ninesuperior",
    "zeroinferior",
    "oneinferior",
    "twoinferior",
    "threeinferior",
    "fourinferior",
    "fiveinferior",
    "sixinferior",
    "seveninferior",
    "eightinferior",
    "nineinferior",
    "centinferior",
    "dollarinferior",
    "periodinferior",
    "commainferior",
    "Agravesmall",
    "Aacutesmall",
    "Acircumflexsmall",
    "Atildesmall",
    "Adieresissmall",
    "Aringsmall",
    "AEsmall",
    "Ccedillasmall",
    "Egravesmall",
    "Eacutesmall",
    "Ecircumflexsmall",
    "Edieresissmall",
    "Igravesmall",
    "Iacutesmall",
    "Icircumflexsmall",
    "Idieresissmall",
    "Ethsmall",
    "Ntildesmall",
    "Ogravesmall",
    "Oacutesmall",
    "Ocircumflexsmall",
    "Otildesmall",
    "Odieresissmall",
    "OEsmall",
    "Oslashsmall",
    "Ugravesmall",
    "Uacutesmall",
    "Ucircumflexsmall",
    "Udieresissmall",
    "Yacutesmall",
    "Thornsmall",
    "Ydieresissmall",
]

cffExpertStringCount = 166
assert len(cffIExpertStrings) == cffExpertStringCount

cffExpertSubsetStrings = [
    ".notdef",
    "space",
    "dollaroldstyle",
    "dollarsuperior",
    "parenleftsuperior",
    "parenrightsuperior",
    "twodotenleader",
    "onedotenleader",
    "comma",
    "hyphen",
    "period",
    "fraction",
    "zerooldstyle",
    "oneoldstyle",
    "twooldstyle",
    "threeoldstyle",
    "fouroldstyle",
    "fiveoldstyle",
    "sixoldstyle",
    "sevenoldstyle",
    "eightoldstyle",
    "nineoldstyle",
    "colon",
    "semicolon",
    "commasuperior",
    "threequartersemdash",
    "periodsuperior",
    "asuperior",
    "bsuperior",
    "centsuperior",
    "dsuperior",
    "esuperior",
    "isuperior",
    "lsuperior",
    "msuperior",
    "nsuperior",
    "osuperior",
    "rsuperior",
    "ssuperior",
    "tsuperior",
    "ff",
    "fi",
    "fl",
    "ffi",
    "ffl",
    "parenleftinferior",
    "parenrightinferior",
    "hyphensuperior",
    "colonmonetary",
    "onefitted",
    "rupiah",
    "centoldstyle",
    "figuredash",
    "hypheninferior",
    "onequarter",
    "onehalf",
    "threequarters",
    "oneeighth",
    "threeeighths",
    "fiveeighths",
    "seveneighths",
    "onethird",
    "twothirds",
    "zerosuperior",
    "onesuperior",
    "twosuperior",
    "threesuperior",
    "foursuperior",
    "fivesuperior",
    "sixsuperior",
    "sevensuperior",
    "eightsuperior",
    "ninesuperior",
    "zeroinferior",
    "oneinferior",
    "twoinferior",
    "threeinferior",
    "fourinferior",
    "fiveinferior",
    "sixinferior",
    "seveninferior",
    "eightinferior",
    "nineinferior",
    "centinferior",
    "dollarinferior",
    "periodinferior",
    "commainferior",
]

cffExpertSubsetStringCount = 87
assert len(cffExpertSubsetStrings) == cffExpertSubsetStringCount