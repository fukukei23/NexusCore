
# === NexusCore/openenv\Lib\site-packages\PIL\TiffImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# TIFF file handling
#
# TIFF is a flexible, if somewhat aged, image file format originally
# defined by Aldus.  Although TIFF supports a wide variety of pixel
# layouts and compression methods, the name doesn't really stand for
# "thousands of incompatible file formats," it just feels that way.
#
# To read TIFF data from a stream, the stream must be seekable.  For
# progressive decoding, make sure to use TIFF files where the tag
# directory is placed first in the file.
#
# History:
# 1995-09-01 fl   Created
# 1996-05-04 fl   Handle JPEGTABLES tag
# 1996-05-18 fl   Fixed COLORMAP support
# 1997-01-05 fl   Fixed PREDICTOR support
# 1997-08-27 fl   Added support for rational tags (from Perry Stoll)
# 1998-01-10 fl   Fixed seek/tell (from Jan Blom)
# 1998-07-15 fl   Use private names for internal variables
# 1999-06-13 fl   Rewritten for PIL 1.0 (1.0)
# 2000-10-11 fl   Additional fixes for Python 2.0 (1.1)
# 2001-04-17 fl   Fixed rewind support (seek to frame 0) (1.2)
# 2001-05-12 fl   Added write support for more tags (from Greg Couch) (1.3)
# 2001-12-18 fl   Added workaround for broken Matrox library
# 2002-01-18 fl   Don't mess up if photometric tag is missing (D. Alan Stewart)
# 2003-05-19 fl   Check FILLORDER tag
# 2003-09-26 fl   Added RGBa support
# 2004-02-24 fl   Added DPI support; fixed rational write support
# 2005-02-07 fl   Added workaround for broken Corel Draw 10 files
# 2006-01-09 fl   Added support for float/double tags (from Russell Nelson)
#
# Copyright (c) 1997-2006 by Secret Labs AB.  All rights reserved.
# Copyright (c) 1995-1997 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import io
import itertools
import logging
import math
import os
import struct
import warnings
from collections.abc import Iterator, MutableMapping
from fractions import Fraction
from numbers import Number, Rational
from typing import IO, Any, Callable, NoReturn, cast

from . import ExifTags, Image, ImageFile, ImageOps, ImagePalette, TiffTags
from ._binary import i16be as i16
from ._binary import i32be as i32
from ._binary import o8
from ._deprecate import deprecate
from ._typing import StrOrBytesPath
from ._util import DeferredError, is_path
from .TiffTags import TYPES

TYPE_CHECKING = False
if TYPE_CHECKING:
    from ._typing import Buffer, IntegralLike

logger = logging.getLogger(__name__)

# Set these to true to force use of libtiff for reading or writing.
READ_LIBTIFF = False
WRITE_LIBTIFF = False
STRIP_SIZE = 65536

II = b"II"  # little-endian (Intel style)
MM = b"MM"  # big-endian (Motorola style)

#
# --------------------------------------------------------------------
# Read TIFF files

# a few tag names, just to make the code below a bit more readable
OSUBFILETYPE = 255
IMAGEWIDTH = 256
IMAGELENGTH = 257
BITSPERSAMPLE = 258
COMPRESSION = 259
PHOTOMETRIC_INTERPRETATION = 262
FILLORDER = 266
IMAGEDESCRIPTION = 270
STRIPOFFSETS = 273
SAMPLESPERPIXEL = 277
ROWSPERSTRIP = 278
STRIPBYTECOUNTS = 279
X_RESOLUTION = 282
Y_RESOLUTION = 283
PLANAR_CONFIGURATION = 284
RESOLUTION_UNIT = 296
TRANSFERFUNCTION = 301
SOFTWARE = 305
DATE_TIME = 306
ARTIST = 315
PREDICTOR = 317
COLORMAP = 320
TILEWIDTH = 322
TILELENGTH = 323
TILEOFFSETS = 324
TILEBYTECOUNTS = 325
SUBIFD = 330
EXTRASAMPLES = 338
SAMPLEFORMAT = 339
JPEGTABLES = 347
YCBCRSUBSAMPLING = 530
REFERENCEBLACKWHITE = 532
COPYRIGHT = 33432
IPTC_NAA_CHUNK = 33723  # newsphoto properties
PHOTOSHOP_CHUNK = 34377  # photoshop properties
ICCPROFILE = 34675
EXIFIFD = 34665
XMP = 700
JPEGQUALITY = 65537  # pseudo-tag by libtiff

# https://github.com/imagej/ImageJA/blob/master/src/main/java/ij/io/TiffDecoder.java
IMAGEJ_META_DATA_BYTE_COUNTS = 50838
IMAGEJ_META_DATA = 50839

COMPRESSION_INFO = {
    # Compression => pil compression name
    1: "raw",
    2: "tiff_ccitt",
    3: "group3",
    4: "group4",
    5: "tiff_lzw",
    6: "tiff_jpeg",  # obsolete
    7: "jpeg",
    8: "tiff_adobe_deflate",
    32771: "tiff_raw_16",  # 16-bit padding
    32773: "packbits",
    32809: "tiff_thunderscan",
    32946: "tiff_deflate",
    34676: "tiff_sgilog",
    34677: "tiff_sgilog24",
    34925: "lzma",
    50000: "zstd",
    50001: "webp",
}

COMPRESSION_INFO_REV = {v: k for k, v in COMPRESSION_INFO.items()}

OPEN_INFO = {
    # (ByteOrder, PhotoInterpretation, SampleFormat, FillOrder, BitsPerSample,
    #  ExtraSamples) => mode, rawmode
    (II, 0, (1,), 1, (1,), ()): ("1", "1;I"),
    (MM, 0, (1,), 1, (1,), ()): ("1", "1;I"),
    (II, 0, (1,), 2, (1,), ()): ("1", "1;IR"),
    (MM, 0, (1,), 2, (1,), ()): ("1", "1;IR"),
    (II, 1, (1,), 1, (1,), ()): ("1", "1"),
    (MM, 1, (1,), 1, (1,), ()): ("1", "1"),
    (II, 1, (1,), 2, (1,), ()): ("1", "1;R"),
    (MM, 1, (1,), 2, (1,), ()): ("1", "1;R"),
    (II, 0, (1,), 1, (2,), ()): ("L", "L;2I"),
    (MM, 0, (1,), 1, (2,), ()): ("L", "L;2I"),
    (II, 0, (1,), 2, (2,), ()): ("L", "L;2IR"),
    (MM, 0, (1,), 2, (2,), ()): ("L", "L;2IR"),
    (II, 1, (1,), 1, (2,), ()): ("L", "L;2"),
    (MM, 1, (1,), 1, (2,), ()): ("L", "L;2"),
    (II, 1, (1,), 2, (2,), ()): ("L", "L;2R"),
    (MM, 1, (1,), 2, (2,), ()): ("L", "L;2R"),
    (II, 0, (1,), 1, (4,), ()): ("L", "L;4I"),
    (MM, 0, (1,), 1, (4,), ()): ("L", "L;4I"),
    (II, 0, (1,), 2, (4,), ()): ("L", "L;4IR"),
    (MM, 0, (1,), 2, (4,), ()): ("L", "L;4IR"),
    (II, 1, (1,), 1, (4,), ()): ("L", "L;4"),
    (MM, 1, (1,), 1, (4,), ()): ("L", "L;4"),
    (II, 1, (1,), 2, (4,), ()): ("L", "L;4R"),
    (MM, 1, (1,), 2, (4,), ()): ("L", "L;4R"),
    (II, 0, (1,), 1, (8,), ()): ("L", "L;I"),
    (MM, 0, (1,), 1, (8,), ()): ("L", "L;I"),
    (II, 0, (1,), 2, (8,), ()): ("L", "L;IR"),
    (MM, 0, (1,), 2, (8,), ()): ("L", "L;IR"),
    (II, 1, (1,), 1, (8,), ()): ("L", "L"),
    (MM, 1, (1,), 1, (8,), ()): ("L", "L"),
    (II, 1, (2,), 1, (8,), ()): ("L", "L"),
    (MM, 1, (2,), 1, (8,), ()): ("L", "L"),
    (II, 1, (1,), 2, (8,), ()): ("L", "L;R"),
    (MM, 1, (1,), 2, (8,), ()): ("L", "L;R"),
    (II, 1, (1,), 1, (12,), ()): ("I;16", "I;12"),
    (II, 0, (1,), 1, (16,), ()): ("I;16", "I;16"),
    (II, 1, (1,), 1, (16,), ()): ("I;16", "I;16"),
    (MM, 1, (1,), 1, (16,), ()): ("I;16B", "I;16B"),
    (II, 1, (1,), 2, (16,), ()): ("I;16", "I;16R"),
    (II, 1, (2,), 1, (16,), ()): ("I", "I;16S"),
    (MM, 1, (2,), 1, (16,), ()): ("I", "I;16BS"),
    (II, 0, (3,), 1, (32,), ()): ("F", "F;32F"),
    (MM, 0, (3,), 1, (32,), ()): ("F", "F;32BF"),
    (II, 1, (1,), 1, (32,), ()): ("I", "I;32N"),
    (II, 1, (2,), 1, (32,), ()): ("I", "I;32S"),
    (MM, 1, (2,), 1, (32,), ()): ("I", "I;32BS"),
    (II, 1, (3,), 1, (32,), ()): ("F", "F;32F"),
    (MM, 1, (3,), 1, (32,), ()): ("F", "F;32BF"),
    (II, 1, (1,), 1, (8, 8), (2,)): ("LA", "LA"),
    (MM, 1, (1,), 1, (8, 8), (2,)): ("LA", "LA"),
    (II, 2, (1,), 1, (8, 8, 8), ()): ("RGB", "RGB"),
    (MM, 2, (1,), 1, (8, 8, 8), ()): ("RGB", "RGB"),
    (II, 2, (1,), 2, (8, 8, 8), ()): ("RGB", "RGB;R"),
    (MM, 2, (1,), 2, (8, 8, 8), ()): ("RGB", "RGB;R"),
    (II, 2, (1,), 1, (8, 8, 8, 8), ()): ("RGBA", "RGBA"),  # missing ExtraSamples
    (MM, 2, (1,), 1, (8, 8, 8, 8), ()): ("RGBA", "RGBA"),  # missing ExtraSamples
    (II, 2, (1,), 1, (8, 8, 8, 8), (0,)): ("RGB", "RGBX"),
    (MM, 2, (1,), 1, (8, 8, 8, 8), (0,)): ("RGB", "RGBX"),
    (II, 2, (1,), 1, (8, 8, 8, 8, 8), (0, 0)): ("RGB", "RGBXX"),
    (MM, 2, (1,), 1, (8, 8, 8, 8, 8), (0, 0)): ("RGB", "RGBXX"),
    (II, 2, (1,), 1, (8, 8, 8, 8, 8, 8), (0, 0, 0)): ("RGB", "RGBXXX"),
    (MM, 2, (1,), 1, (8, 8, 8, 8, 8, 8), (0, 0, 0)): ("RGB", "RGBXXX"),
    (II, 2, (1,), 1, (8, 8, 8, 8), (1,)): ("RGBA", "RGBa"),
    (MM, 2, (1,), 1, (8, 8, 8, 8), (1,)): ("RGBA", "RGBa"),
    (II, 2, (1,), 1, (8, 8, 8, 8, 8), (1, 0)): ("RGBA", "RGBaX"),
    (MM, 2, (1,), 1, (8, 8, 8, 8, 8), (1, 0)): ("RGBA", "RGBaX"),
    (II, 2, (1,), 1, (8, 8, 8, 8, 8, 8), (1, 0, 0)): ("RGBA", "RGBaXX"),
    (MM, 2, (1,), 1, (8, 8, 8, 8, 8, 8), (1, 0, 0)): ("RGBA", "RGBaXX"),
    (II, 2, (1,), 1, (8, 8, 8, 8), (2,)): ("RGBA", "RGBA"),
    (MM, 2, (1,), 1, (8, 8, 8, 8), (2,)): ("RGBA", "RGBA"),
    (II, 2, (1,), 1, (8, 8, 8, 8, 8), (2, 0)): ("RGBA", "RGBAX"),
    (MM, 2, (1,), 1, (8, 8, 8, 8, 8), (2, 0)): ("RGBA", "RGBAX"),
    (II, 2, (1,), 1, (8, 8, 8, 8, 8, 8), (2, 0, 0)): ("RGBA", "RGBAXX"),
    (MM, 2, (1,), 1, (8, 8, 8, 8, 8, 8), (2, 0, 0)): ("RGBA", "RGBAXX"),
    (II, 2, (1,), 1, (8, 8, 8, 8), (999,)): ("RGBA", "RGBA"),  # Corel Draw 10
    (MM, 2, (1,), 1, (8, 8, 8, 8), (999,)): ("RGBA", "RGBA"),  # Corel Draw 10
    (II, 2, (1,), 1, (16, 16, 16), ()): ("RGB", "RGB;16L"),
    (MM, 2, (1,), 1, (16, 16, 16), ()): ("RGB", "RGB;16B"),
    (II, 2, (1,), 1, (16, 16, 16, 16), ()): ("RGBA", "RGBA;16L"),
    (MM, 2, (1,), 1, (16, 16, 16, 16), ()): ("RGBA", "RGBA;16B"),
    (II, 2, (1,), 1, (16, 16, 16, 16), (0,)): ("RGB", "RGBX;16L"),
    (MM, 2, (1,), 1, (16, 16, 16, 16), (0,)): ("RGB", "RGBX;16B"),
    (II, 2, (1,), 1, (16, 16, 16, 16), (1,)): ("RGBA", "RGBa;16L"),
    (MM, 2, (1,), 1, (16, 16, 16, 16), (1,)): ("RGBA", "RGBa;16B"),
    (II, 2, (1,), 1, (16, 16, 16, 16), (2,)): ("RGBA", "RGBA;16L"),
    (MM, 2, (1,), 1, (16, 16, 16, 16), (2,)): ("RGBA", "RGBA;16B"),
    (II, 3, (1,), 1, (1,), ()): ("P", "P;1"),
    (MM, 3, (1,), 1, (1,), ()): ("P", "P;1"),
    (II, 3, (1,), 2, (1,), ()): ("P", "P;1R"),
    (MM, 3, (1,), 2, (1,), ()): ("P", "P;1R"),
    (II, 3, (1,), 1, (2,), ()): ("P", "P;2"),
    (MM, 3, (1,), 1, (2,), ()): ("P", "P;2"),
    (II, 3, (1,), 2, (2,), ()): ("P", "P;2R"),
    (MM, 3, (1,), 2, (2,), ()): ("P", "P;2R"),
    (II, 3, (1,), 1, (4,), ()): ("P", "P;4"),
    (MM, 3, (1,), 1, (4,), ()): ("P", "P;4"),
    (II, 3, (1,), 2, (4,), ()): ("P", "P;4R"),
    (MM, 3, (1,), 2, (4,), ()): ("P", "P;4R"),
    (II, 3, (1,), 1, (8,), ()): ("P", "P"),
    (MM, 3, (1,), 1, (8,), ()): ("P", "P"),
    (II, 3, (1,), 1, (8, 8), (0,)): ("P", "PX"),
    (II, 3, (1,), 1, (8, 8), (2,)): ("PA", "PA"),
    (MM, 3, (1,), 1, (8, 8), (2,)): ("PA", "PA"),
    (II, 3, (1,), 2, (8,), ()): ("P", "P;R"),
    (MM, 3, (1,), 2, (8,), ()): ("P", "P;R"),
    (II, 5, (1,), 1, (8, 8, 8, 8), ()): ("CMYK", "CMYK"),
    (MM, 5, (1,), 1, (8, 8, 8, 8), ()): ("CMYK", "CMYK"),
    (II, 5, (1,), 1, (8, 8, 8, 8, 8), (0,)): ("CMYK", "CMYKX"),
    (MM, 5, (1,), 1, (8, 8, 8, 8, 8), (0,)): ("CMYK", "CMYKX"),
    (II, 5, (1,), 1, (8, 8, 8, 8, 8, 8), (0, 0)): ("CMYK", "CMYKXX"),
    (MM, 5, (1,), 1, (8, 8, 8, 8, 8, 8), (0, 0)): ("CMYK", "CMYKXX"),
    (II, 5, (1,), 1, (16, 16, 16, 16), ()): ("CMYK", "CMYK;16L"),
    (MM, 5, (1,), 1, (16, 16, 16, 16), ()): ("CMYK", "CMYK;16B"),
    (II, 6, (1,), 1, (8,), ()): ("L", "L"),
    (MM, 6, (1,), 1, (8,), ()): ("L", "L"),
    # JPEG compressed images handled by LibTiff and auto-converted to RGBX
    # Minimal Baseline TIFF requires YCbCr images to have 3 SamplesPerPixel
    (II, 6, (1,), 1, (8, 8, 8), ()): ("RGB", "RGBX"),
    (MM, 6, (1,), 1, (8, 8, 8), ()): ("RGB", "RGBX"),
    (II, 8, (1,), 1, (8, 8, 8), ()): ("LAB", "LAB"),
    (MM, 8, (1,), 1, (8, 8, 8), ()): ("LAB", "LAB"),
}

MAX_SAMPLESPERPIXEL = max(len(key_tp[4]) for key_tp in OPEN_INFO)

PREFIXES = [
    b"MM\x00\x2a",  # Valid TIFF header with big-endian byte order
    b"II\x2a\x00",  # Valid TIFF header with little-endian byte order
    b"MM\x2a\x00",  # Invalid TIFF header, assume big-endian
    b"II\x00\x2a",  # Invalid TIFF header, assume little-endian
    b"MM\x00\x2b",  # BigTIFF with big-endian byte order
    b"II\x2b\x00",  # BigTIFF with little-endian byte order
]

if not getattr(Image.core, "libtiff_support_custom_tags", True):
    deprecate("Support for LibTIFF earlier than version 4", 12)


def _accept(prefix: bytes) -> bool:
    return prefix.startswith(tuple(PREFIXES))


def _limit_rational(
    val: float | Fraction | IFDRational, max_val: int
) -> tuple[IntegralLike, IntegralLike]:
    inv = abs(val) > 1
    n_d = IFDRational(1 / val if inv else val).limit_rational(max_val)
    return n_d[::-1] if inv else n_d


def _limit_signed_rational(
    val: IFDRational, max_val: int, min_val: int
) -> tuple[IntegralLike, IntegralLike]:
    frac = Fraction(val)
    n_d: tuple[IntegralLike, IntegralLike] = frac.numerator, frac.denominator

    if min(float(i) for i in n_d) < min_val:
        n_d = _limit_rational(val, abs(min_val))

    n_d_float = tuple(float(i) for i in n_d)
    if max(n_d_float) > max_val:
        n_d = _limit_rational(n_d_float[0] / n_d_float[1], max_val)

    return n_d


##
# Wrapper for TIFF IFDs.

_load_dispatch = {}
_write_dispatch = {}


def _delegate(op: str) -> Any:
    def delegate(
        self: IFDRational, *args: tuple[float, ...]
    ) -> bool | float | Fraction:
        return getattr(self._val, op)(*args)

    return delegate


class IFDRational(Rational):
    """Implements a rational class where 0/0 is a legal value to match
    the in the wild use of exif rationals.

    e.g., DigitalZoomRatio - 0.00/0.00  indicates that no digital zoom was used
    """

    """ If the denominator is 0, store this as a float('nan'), otherwise store
    as a fractions.Fraction(). Delegate as appropriate

    """

    __slots__ = ("_numerator", "_denominator", "_val")

    def __init__(
        self, value: float | Fraction | IFDRational, denominator: int = 1
    ) -> None:
        """
        :param value: either an integer numerator, a
        float/rational/other number, or an IFDRational
        :param denominator: Optional integer denominator
        """
        self._val: Fraction | float
        if isinstance(value, IFDRational):
            self._numerator = value.numerator
            self._denominator = value.denominator
            self._val = value._val
            return

        if isinstance(value, Fraction):
            self._numerator = value.numerator
            self._denominator = value.denominator
        else:
            if TYPE_CHECKING:
                self._numerator = cast(IntegralLike, value)
            else:
                self._numerator = value
            self._denominator = denominator

        if denominator == 0:
            self._val = float("nan")
        elif denominator == 1:
            self._val = Fraction(value)
        elif int(value) == value:
            self._val = Fraction(int(value), denominator)
        else:
            self._val = Fraction(value / denominator)

    @property
    def numerator(self) -> IntegralLike:
        return self._numerator

    @property
    def denominator(self) -> int:
        return self._denominator

    def limit_rational(self, max_denominator: int) -> tuple[IntegralLike, int]:
        """

        :param max_denominator: Integer, the maximum denominator value
        :returns: Tuple of (numerator, denominator)
        """

        if self.denominator == 0:
            return self.numerator, self.denominator

        assert isinstance(self._val, Fraction)
        f = self._val.limit_denominator(max_denominator)
        return f.numerator, f.denominator

    def __repr__(self) -> str:
        return str(float(self._val))

    def __hash__(self) -> int:  # type: ignore[override]
        return self._val.__hash__()

    def __eq__(self, other: object) -> bool:
        val = self._val
        if isinstance(other, IFDRational):
            other = other._val
        if isinstance(other, float):
            val = float(val)
        return val == other

    def __getstate__(self) -> list[float | Fraction | IntegralLike]:
        return [self._val, self._numerator, self._denominator]

    def __setstate__(self, state: list[float | Fraction | IntegralLike]) -> None:
        IFDRational.__init__(self, 0)
        _val, _numerator, _denominator = state
        assert isinstance(_val, (float, Fraction))
        self._val = _val
        if TYPE_CHECKING:
            self._numerator = cast(IntegralLike, _numerator)
        else:
            self._numerator = _numerator
        assert isinstance(_denominator, int)
        self._denominator = _denominator

    """ a = ['add','radd', 'sub', 'rsub', 'mul', 'rmul',
             'truediv', 'rtruediv', 'floordiv', 'rfloordiv',
             'mod','rmod', 'pow','rpow', 'pos', 'neg',
             'abs', 'trunc', 'lt', 'gt', 'le', 'ge', 'bool',
             'ceil', 'floor', 'round']
        print("\n".join("__%s__ = _delegate('__%s__')" % (s,s) for s in a))
        """

    __add__ = _delegate("__add__")
    __radd__ = _delegate("__radd__")
    __sub__ = _delegate("__sub__")
    __rsub__ = _delegate("__rsub__")
    __mul__ = _delegate("__mul__")
    __rmul__ = _delegate("__rmul__")
    __truediv__ = _delegate("__truediv__")
    __rtruediv__ = _delegate("__rtruediv__")
    __floordiv__ = _delegate("__floordiv__")
    __rfloordiv__ = _delegate("__rfloordiv__")
    __mod__ = _delegate("__mod__")
    __rmod__ = _delegate("__rmod__")
    __pow__ = _delegate("__pow__")
    __rpow__ = _delegate("__rpow__")
    __pos__ = _delegate("__pos__")
    __neg__ = _delegate("__neg__")
    __abs__ = _delegate("__abs__")
    __trunc__ = _delegate("__trunc__")
    __lt__ = _delegate("__lt__")
    __gt__ = _delegate("__gt__")
    __le__ = _delegate("__le__")
    __ge__ = _delegate("__ge__")
    __bool__ = _delegate("__bool__")
    __ceil__ = _delegate("__ceil__")
    __floor__ = _delegate("__floor__")
    __round__ = _delegate("__round__")
    # Python >= 3.11
    if hasattr(Fraction, "__int__"):
        __int__ = _delegate("__int__")


_LoaderFunc = Callable[["ImageFileDirectory_v2", bytes, bool], Any]


def _register_loader(idx: int, size: int) -> Callable[[_LoaderFunc], _LoaderFunc]:
    def decorator(func: _LoaderFunc) -> _LoaderFunc:
        from .TiffTags import TYPES

        if func.__name__.startswith("load_"):
            TYPES[idx] = func.__name__[5:].replace("_", " ")
        _load_dispatch[idx] = size, func  # noqa: F821
        return func

    return decorator


def _register_writer(idx: int) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        _write_dispatch[idx] = func  # noqa: F821
        return func

    return decorator


def _register_basic(idx_fmt_name: tuple[int, str, str]) -> None:
    from .TiffTags import TYPES

    idx, fmt, name = idx_fmt_name
    TYPES[idx] = name
    size = struct.calcsize(f"={fmt}")

    def basic_handler(
        self: ImageFileDirectory_v2, data: bytes, legacy_api: bool = True
    ) -> tuple[Any, ...]:
        return self._unpack(f"{len(data) // size}{fmt}", data)

    _load_dispatch[idx] = size, basic_handler  # noqa: F821
    _write_dispatch[idx] = lambda self, *values: (  # noqa: F821
        b"".join(self._pack(fmt, value) for value in values)
    )


if TYPE_CHECKING:
    _IFDv2Base = MutableMapping[int, Any]
else:
    _IFDv2Base = MutableMapping


class ImageFileDirectory_v2(_IFDv2Base):
    """This class represents a TIFF tag directory.  To speed things up, we
    don't decode tags unless they're asked for.

    Exposes a dictionary interface of the tags in the directory::

        ifd = ImageFileDirectory_v2()
        ifd[key] = 'Some Data'
        ifd.tagtype[key] = TiffTags.ASCII
        print(ifd[key])
        'Some Data'

    Individual values are returned as the strings or numbers, sequences are
    returned as tuples of the values.

    The tiff metadata type of each item is stored in a dictionary of
    tag types in
    :attr:`~PIL.TiffImagePlugin.ImageFileDirectory_v2.tagtype`. The types
    are read from a tiff file, guessed from the type added, or added
    manually.

    Data Structures:

        * ``self.tagtype = {}``

          * Key: numerical TIFF tag number
          * Value: integer corresponding to the data type from
            :py:data:`.TiffTags.TYPES`

          .. versionadded:: 3.0.0

    'Internal' data structures:

        * ``self._tags_v2 = {}``

          * Key: numerical TIFF tag number
          * Value: decoded data, as tuple for multiple values

        * ``self._tagdata = {}``

          * Key: numerical TIFF tag number
          * Value: undecoded byte string from file

        * ``self._tags_v1 = {}``

          * Key: numerical TIFF tag number
          * Value: decoded data in the v1 format

    Tags will be found in the private attributes ``self._tagdata``, and in
    ``self._tags_v2`` once decoded.

    ``self.legacy_api`` is a value for internal use, and shouldn't be changed
    from outside code. In cooperation with
    :py:class:`~PIL.TiffImagePlugin.ImageFileDirectory_v1`, if ``legacy_api``
    is true, then decoded tags will be populated into both ``_tags_v1`` and
    ``_tags_v2``. ``_tags_v2`` will be used if this IFD is used in the TIFF
    save routine. Tags should be read from ``_tags_v1`` if
    ``legacy_api == true``.

    """

    _load_dispatch: dict[int, tuple[int, _LoaderFunc]] = {}
    _write_dispatch: dict[int, Callable[..., Any]] = {}

    def __init__(
        self,
        ifh: bytes = b"II\x2a\x00\x00\x00\x00\x00",
        prefix: bytes | None = None,
        group: int | None = None,
    ) -> None:
        """Initialize an ImageFileDirectory.

        To construct an ImageFileDirectory from a real file, pass the 8-byte
        magic header to the constructor.  To only set the endianness, pass it
        as the 'prefix' keyword argument.

        :param ifh: One of the accepted magic headers (cf. PREFIXES); also sets
              endianness.
        :param prefix: Override the endianness of the file.
        """
        if not _accept(ifh):
            msg = f"not a TIFF file (header {repr(ifh)} not valid)"
            raise SyntaxError(msg)
        self._prefix = prefix if prefix is not None else ifh[:2]
        if self._prefix == MM:
            self._endian = ">"
        elif self._prefix == II:
            self._endian = "<"
        else:
            msg = "not a TIFF IFD"
            raise SyntaxError(msg)
        self._bigtiff = ifh[2] == 43
        self.group = group
        self.tagtype: dict[int, int] = {}
        """ Dictionary of tag types """
        self.reset()
        self.next = (
            self._unpack("Q", ifh[8:])[0]
            if self._bigtiff
            else self._unpack("L", ifh[4:])[0]
        )
        self._legacy_api = False

    prefix = property(lambda self: self._prefix)
    offset = property(lambda self: self._offset)

    @property
    def legacy_api(self) -> bool:
        return self._legacy_api

    @legacy_api.setter
    def legacy_api(self, value: bool) -> NoReturn:
        msg = "Not allowing setting of legacy api"
        raise Exception(msg)

    def reset(self) -> None:
        self._tags_v1: dict[int, Any] = {}  # will remain empty if legacy_api is false
        self._tags_v2: dict[int, Any] = {}  # main tag storage
        self._tagdata: dict[int, bytes] = {}
        self.tagtype = {}  # added 2008-06-05 by Florian Hoech
        self._next = None
        self._offset: int | None = None

    def __str__(self) -> str:
        return str(dict(self))

    def named(self) -> dict[str, Any]:
        """
        :returns: dict of name|key: value

        Returns the complete tag dictionary, with named tags where possible.
        """
        return {
            TiffTags.lookup(code, self.group).name: value
            for code, value in self.items()
        }

    def __len__(self) -> int:
        return len(set(self._tagdata) | set(self._tags_v2))

    def __getitem__(self, tag: int) -> Any:
        if tag not in self._tags_v2:  # unpack on the fly
            data = self._tagdata[tag]
            typ = self.tagtype[tag]
            size, handler = self._load_dispatch[typ]
            self[tag] = handler(self, data, self.legacy_api)  # check type
        val = self._tags_v2[tag]
        if self.legacy_api and not isinstance(val, (tuple, bytes)):
            val = (val,)
        return val

    def __contains__(self, tag: object) -> bool:
        return tag in self._tags_v2 or tag in self._tagdata

    def __setitem__(self, tag: int, value: Any) -> None:
        self._setitem(tag, value, self.legacy_api)

    def _setitem(self, tag: int, value: Any, legacy_api: bool) -> None:
        basetypes = (Number, bytes, str)

        info = TiffTags.lookup(tag, self.group)
        values = [value] if isinstance(value, basetypes) else value

        if tag not in self.tagtype:
            if info.type:
                self.tagtype[tag] = info.type
            else:
                self.tagtype[tag] = TiffTags.UNDEFINED
                if all(isinstance(v, IFDRational) for v in values):
                    for v in values:
                        assert isinstance(v, IFDRational)
                        if v < 0:
                            self.tagtype[tag] = TiffTags.SIGNED_RATIONAL
                            break
                    else:
                        self.tagtype[tag] = TiffTags.RATIONAL
                elif all(isinstance(v, int) for v in values):
                    short = True
                    signed_short = True
                    long = True
                    for v in values:
                        assert isinstance(v, int)
                        if short and not (0 <= v < 2**16):
                            short = False
                        if signed_short and not (-(2**15) < v < 2**15):
                            signed_short = False
                        if long and v < 0:
                            long = False
                    if short:
                        self.tagtype[tag] = TiffTags.SHORT
                    elif signed_short:
                        self.tagtype[tag] = TiffTags.SIGNED_SHORT
                    elif long:
                        self.tagtype[tag] = TiffTags.LONG
                    else:
                        self.tagtype[tag] = TiffTags.SIGNED_LONG
                elif all(isinstance(v, float) for v in values):
                    self.tagtype[tag] = TiffTags.DOUBLE
                elif all(isinstance(v, str) for v in values):
                    self.tagtype[tag] = TiffTags.ASCII
                elif all(isinstance(v, bytes) for v in values):
                    self.tagtype[tag] = TiffTags.BYTE

        if self.tagtype[tag] == TiffTags.UNDEFINED:
            values = [
                v.encode("ascii", "replace") if isinstance(v, str) else v
                for v in values
            ]
        elif self.tagtype[tag] == TiffTags.RATIONAL:
            values = [float(v) if isinstance(v, int) else v for v in values]

        is_ifd = self.tagtype[tag] == TiffTags.LONG and isinstance(values, dict)
        if not is_ifd:
            values = tuple(
                info.cvt_enum(value) if isinstance(value, str) else value
                for value in values
            )

        dest = self._tags_v1 if legacy_api else self._tags_v2

        # Three branches:
        # Spec'd length == 1, Actual length 1, store as element
        # Spec'd length == 1, Actual > 1, Warn and truncate. Formerly barfed.
        # No Spec, Actual length 1, Formerly (<4.2) returned a 1 element tuple.
        # Don't mess with the legacy api, since it's frozen.
        if not is_ifd and (
            (info.length == 1)
            or self.tagtype[tag] == TiffTags.BYTE
            or (info.length is None and len(values) == 1 and not legacy_api)
        ):
            # Don't mess with the legacy api, since it's frozen.
            if legacy_api and self.tagtype[tag] in [
                TiffTags.RATIONAL,
                TiffTags.SIGNED_RATIONAL,
            ]:  # rationals
                values = (values,)
            try:
                (dest[tag],) = values
            except ValueError:
                # We've got a builtin tag with 1 expected entry
                warnings.warn(
                    f"Metadata Warning, tag {tag} had too many entries: "
                    f"{len(values)}, expected 1"
                )
                dest[tag] = values[0]

        else:
            # Spec'd length > 1 or undefined
            # Unspec'd, and length > 1
            dest[tag] = values

    def __delitem__(self, tag: int) -> None:
        self._tags_v2.pop(tag, None)
        self._tags_v1.pop(tag, None)
        self._tagdata.pop(tag, None)

    def __iter__(self) -> Iterator[int]:
        return iter(set(self._tagdata) | set(self._tags_v2))

    def _unpack(self, fmt: str, data: bytes) -> tuple[Any, ...]:
        return struct.unpack(self._endian + fmt, data)

    def _pack(self, fmt: str, *values: Any) -> bytes:
        return struct.pack(self._endian + fmt, *values)

    list(
        map(
            _register_basic,
            [
                (TiffTags.SHORT, "H", "short"),
                (TiffTags.LONG, "L", "long"),
                (TiffTags.SIGNED_BYTE, "b", "signed byte"),
                (TiffTags.SIGNED_SHORT, "h", "signed short"),
                (TiffTags.SIGNED_LONG, "l", "signed long"),
                (TiffTags.FLOAT, "f", "float"),
                (TiffTags.DOUBLE, "d", "double"),
                (TiffTags.IFD, "L", "long"),
                (TiffTags.LONG8, "Q", "long8"),
            ],
        )
    )

    @_register_loader(1, 1)  # Basic type, except for the legacy API.
    def load_byte(self, data: bytes, legacy_api: bool = True) -> bytes:
        return data

    @_register_writer(1)  # Basic type, except for the legacy API.
    def write_byte(self, data: bytes | int | IFDRational) -> bytes:
        if isinstance(data, IFDRational):
            data = int(data)
        if isinstance(data, int):
            data = bytes((data,))
        return data

    @_register_loader(2, 1)
    def load_string(self, data: bytes, legacy_api: bool = True) -> str:
        if data.endswith(b"\0"):
            data = data[:-1]
        return data.decode("latin-1", "replace")

    @_register_writer(2)
    def write_string(self, value: str | bytes | int) -> bytes:
        # remerge of https://github.com/python-pillow/Pillow/pull/1416
        if isinstance(value, int):
            value = str(value)
        if not isinstance(value, bytes):
            value = value.encode("ascii", "replace")
        return value + b"\0"

    @_register_loader(5, 8)
    def load_rational(
        self, data: bytes, legacy_api: bool = True
    ) -> tuple[tuple[int, int] | IFDRational, ...]:
        vals = self._unpack(f"{len(data) // 4}L", data)

        def combine(a: int, b: int) -> tuple[int, int] | IFDRational:
            return (a, b) if legacy_api else IFDRational(a, b)

        return tuple(combine(num, denom) for num, denom in zip(vals[::2], vals[1::2]))

    @_register_writer(5)
    def write_rational(self, *values: IFDRational) -> bytes:
        return b"".join(
            self._pack("2L", *_limit_rational(frac, 2**32 - 1)) for frac in values
        )

    @_register_loader(7, 1)
    def load_undefined(self, data: bytes, legacy_api: bool = True) -> bytes:
        return data

    @_register_writer(7)
    def write_undefined(self, value: bytes | int | IFDRational) -> bytes:
        if isinstance(value, IFDRational):
            value = int(value)
        if isinstance(value, int):
            value = str(value).encode("ascii", "replace")
        return value

    @_register_loader(10, 8)
    def load_signed_rational(
        self, data: bytes, legacy_api: bool = True
    ) -> tuple[tuple[int, int] | IFDRational, ...]:
        vals = self._unpack(f"{len(data) // 4}l", data)

        def combine(a: int, b: int) -> tuple[int, int] | IFDRational:
            return (a, b) if legacy_api else IFDRational(a, b)

        return tuple(combine(num, denom) for num, denom in zip(vals[::2], vals[1::2]))

    @_register_writer(10)
    def write_signed_rational(self, *values: IFDRational) -> bytes:
        return b"".join(
            self._pack("2l", *_limit_signed_rational(frac, 2**31 - 1, -(2**31)))
            for frac in values
        )

    def _ensure_read(self, fp: IO[bytes], size: int) -> bytes:
        ret = fp.read(size)
        if len(ret) != size:
            msg = (
                "Corrupt EXIF data.  "
                f"Expecting to read {size} bytes but only got {len(ret)}. "
            )
            raise OSError(msg)
        return ret

    def load(self, fp: IO[bytes]) -> None:
        self.reset()
        self._offset = fp.tell()

        try:
            tag_count = (
                self._unpack("Q", self._ensure_read(fp, 8))
                if self._bigtiff
                else self._unpack("H", self._ensure_read(fp, 2))
            )[0]
            for i in range(tag_count):
                tag, typ, count, data = (
                    self._unpack("HHQ8s", self._ensure_read(fp, 20))
                    if self._bigtiff
                    else self._unpack("HHL4s", self._ensure_read(fp, 12))
                )

                tagname = TiffTags.lookup(tag, self.group).name
                typname = TYPES.get(typ, "unknown")
                msg = f"tag: {tagname} ({tag}) - type: {typname} ({typ})"

                try:
                    unit_size, handler = self._load_dispatch[typ]
                except KeyError:
                    logger.debug("%s - unsupported type %s", msg, typ)
                    continue  # ignore unsupported type
                size = count * unit_size
                if size > (8 if self._bigtiff else 4):
                    here = fp.tell()
                    (offset,) = self._unpack("Q" if self._bigtiff else "L", data)
                    msg += f" Tag Location: {here} - Data Location: {offset}"
                    fp.seek(offset)
                    data = ImageFile._safe_read(fp, size)
                    fp.seek(here)
                else:
                    data = data[:size]

                if len(data) != size:
                    warnings.warn(
                        "Possibly corrupt EXIF data.  "
                        f"Expecting to read {size} bytes but only got {len(data)}."
                        f" Skipping tag {tag}"
                    )
                    logger.debug(msg)
                    continue

                if not data:
                    logger.debug(msg)
                    continue

                self._tagdata[tag] = data
                self.tagtype[tag] = typ

                msg += " - value: "
                msg += f"<table: {size} bytes>" if size > 32 else repr(data)

                logger.debug(msg)

            (self.next,) = (
                self._unpack("Q", self._ensure_read(fp, 8))
                if self._bigtiff
                else self._unpack("L", self._ensure_read(fp, 4))
            )
        except OSError as msg:
            warnings.warn(str(msg))
            return

    def _get_ifh(self) -> bytes:
        ifh = self._prefix + self._pack("H", 43 if self._bigtiff else 42)
        if self._bigtiff:
            ifh += self._pack("HH", 8, 0)
        ifh += self._pack("Q", 16) if self._bigtiff else self._pack("L", 8)

        return ifh

    def tobytes(self, offset: int = 0) -> bytes:
        # FIXME What about tagdata?
        result = self._pack("Q" if self._bigtiff else "H", len(self._tags_v2))

        entries: list[tuple[int, int, int, bytes, bytes]] = []

        fmt = "Q" if self._bigtiff else "L"
        fmt_size = 8 if self._bigtiff else 4
        offset += (
            len(result) + len(self._tags_v2) * (20 if self._bigtiff else 12) + fmt_size
        )
        stripoffsets = None

        # pass 1: convert tags to binary format
        # always write tags in ascending order
        for tag, value in sorted(self._tags_v2.items()):
            if tag == STRIPOFFSETS:
                stripoffsets = len(entries)
            typ = self.tagtype[tag]
            logger.debug("Tag %s, Type: %s, Value: %s", tag, typ, repr(value))
            is_ifd = typ == TiffTags.LONG and isinstance(value, dict)
            if is_ifd:
                ifd = ImageFileDirectory_v2(self._get_ifh(), group=tag)
                values = self._tags_v2[tag]
                for ifd_tag, ifd_value in values.items():
                    ifd[ifd_tag] = ifd_value
                data = ifd.tobytes(offset)
            else:
                values = value if isinstance(value, tuple) else (value,)
                data = self._write_dispatch[typ](self, *values)

            tagname = TiffTags.lookup(tag, self.group).name
            typname = "ifd" if is_ifd else TYPES.get(typ, "unknown")
            msg = f"save: {tagname} ({tag}) - type: {typname} ({typ}) - value: "
            msg += f"<table: {len(data)} bytes>" if len(data) >= 16 else str(values)
            logger.debug(msg)

            # count is sum of lengths for string and arbitrary data
            if is_ifd:
                count = 1
            elif typ in [TiffTags.BYTE, TiffTags.ASCII, TiffTags.UNDEFINED]:
                count = len(data)
            else:
                count = len(values)
            # figure out if data fits into the entry
            if len(data) <= fmt_size:
                entries.append((tag, typ, count, data.ljust(fmt_size, b"\0"), b""))
            else:
                entries.append((tag, typ, count, self._pack(fmt, offset), data))
                offset += (len(data) + 1) // 2 * 2  # pad to word

        # update strip offset data to point beyond auxiliary data
        if stripoffsets is not None:
            tag, typ, count, value, data = entries[stripoffsets]
            if data:
                size, handler = self._load_dispatch[typ]
                values = [val + offset for val in handler(self, data, self.legacy_api)]
                data = self._write_dispatch[typ](self, *values)
            else:
                value = self._pack(fmt, self._unpack(fmt, value)[0] + offset)
            entries[stripoffsets] = tag, typ, count, value, data

        # pass 2: write entries to file
        for tag, typ, count, value, data in entries:
            logger.debug("%s %s %s %s %s", tag, typ, count, repr(value), repr(data))
            result += self._pack(
                "HHQ8s" if self._bigtiff else "HHL4s", tag, typ, count, value
            )

        # -- overwrite here for multi-page --
        result += self._pack(fmt, 0)  # end of entries

        # pass 3: write auxiliary data to file
        for tag, typ, count, value, data in entries:
            result += data
            if len(data) & 1:
                result += b"\0"

        return result

    def save(self, fp: IO[bytes]) -> int:
        if fp.tell() == 0:  # skip TIFF header on subsequent pages
            fp.write(self._get_ifh())

        offset = fp.tell()
        result = self.tobytes(offset)
        fp.write(result)
        return offset + len(result)


ImageFileDirectory_v2._load_dispatch = _load_dispatch
ImageFileDirectory_v2._write_dispatch = _write_dispatch
for idx, name in TYPES.items():
    name = name.replace(" ", "_")
    setattr(ImageFileDirectory_v2, f"load_{name}", _load_dispatch[idx][1])
    setattr(ImageFileDirectory_v2, f"write_{name}", _write_dispatch[idx])
del _load_dispatch, _write_dispatch, idx, name


# Legacy ImageFileDirectory support.
class ImageFileDirectory_v1(ImageFileDirectory_v2):
    """This class represents the **legacy** interface to a TIFF tag directory.

    Exposes a dictionary interface of the tags in the directory::

        ifd = ImageFileDirectory_v1()
        ifd[key] = 'Some Data'
        ifd.tagtype[key] = TiffTags.ASCII
        print(ifd[key])
        ('Some Data',)

    Also contains a dictionary of tag types as read from the tiff image file,
    :attr:`~PIL.TiffImagePlugin.ImageFileDirectory_v1.tagtype`.

    Values are returned as a tuple.

    ..  deprecated:: 3.0.0
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._legacy_api = True

    tags = property(lambda self: self._tags_v1)
    tagdata = property(lambda self: self._tagdata)

    # defined in ImageFileDirectory_v2
    tagtype: dict[int, int]
    """Dictionary of tag types"""

    @classmethod
    def from_v2(cls, original: ImageFileDirectory_v2) -> ImageFileDirectory_v1:
        """Returns an
        :py:class:`~PIL.TiffImagePlugin.ImageFileDirectory_v1`
        instance with the same data as is contained in the original
        :py:class:`~PIL.TiffImagePlugin.ImageFileDirectory_v2`
        instance.

        :returns: :py:class:`~PIL.TiffImagePlugin.ImageFileDirectory_v1`

        """

        ifd = cls(prefix=original.prefix)
        ifd._tagdata = original._tagdata
        ifd.tagtype = original.tagtype
        ifd.next = original.next  # an indicator for multipage tiffs
        return ifd

    def to_v2(self) -> ImageFileDirectory_v2:
        """Returns an
        :py:class:`~PIL.TiffImagePlugin.ImageFileDirectory_v2`
        instance with the same data as is contained in the original
        :py:class:`~PIL.TiffImagePlugin.ImageFileDirectory_v1`
        instance.

        :returns: :py:class:`~PIL.TiffImagePlugin.ImageFileDirectory_v2`

        """

        ifd = ImageFileDirectory_v2(prefix=self.prefix)
        ifd._tagdata = dict(self._tagdata)
        ifd.tagtype = dict(self.tagtype)
        ifd._tags_v2 = dict(self._tags_v2)
        return ifd

    def __contains__(self, tag: object) -> bool:
        return tag in self._tags_v1 or tag in self._tagdata

    def __len__(self) -> int:
        return len(set(self._tagdata) | set(self._tags_v1))

    def __iter__(self) -> Iterator[int]:
        return iter(set(self._tagdata) | set(self._tags_v1))

    def __setitem__(self, tag: int, value: Any) -> None:
        for legacy_api in (False, True):
            self._setitem(tag, value, legacy_api)

    def __getitem__(self, tag: int) -> Any:
        if tag not in self._tags_v1:  # unpack on the fly
            data = self._tagdata[tag]
            typ = self.tagtype[tag]
            size, handler = self._load_dispatch[typ]
            for legacy in (False, True):
                self._setitem(tag, handler(self, data, legacy), legacy)
        val = self._tags_v1[tag]
        if not isinstance(val, (tuple, bytes)):
            val = (val,)
        return val


# undone -- switch this pointer
ImageFileDirectory = ImageFileDirectory_v1


##
# Image plugin for TIFF files.


class TiffImageFile(ImageFile.ImageFile):
    format = "TIFF"
    format_description = "Adobe TIFF"
    _close_exclusive_fp_after_loading = False

    def __init__(
        self,
        fp: StrOrBytesPath | IO[bytes],
        filename: str | bytes | None = None,
    ) -> None:
        self.tag_v2: ImageFileDirectory_v2
        """ Image file directory (tag dictionary) """

        self.tag: ImageFileDirectory_v1
        """ Legacy tag entries """

        super().__init__(fp, filename)

    def _open(self) -> None:
        """Open the first image in a TIFF file"""

        # Header
        ifh = self.fp.read(8)
        if ifh[2] == 43:
            ifh += self.fp.read(8)

        self.tag_v2 = ImageFileDirectory_v2(ifh)

        # setup frame pointers
        self.__first = self.__next = self.tag_v2.next
        self.__frame = -1
        self._fp = self.fp
        self._frame_pos: list[int] = []
        self._n_frames: int | None = None

        logger.debug("*** TiffImageFile._open ***")
        logger.debug("- __first: %s", self.__first)
        logger.debug("- ifh: %s", repr(ifh))  # Use repr to avoid str(bytes)

        # and load the first frame
        self._seek(0)

    @property
    def n_frames(self) -> int:
        current_n_frames = self._n_frames
        if current_n_frames is None:
            current = self.tell()
            self._seek(len(self._frame_pos))
            while self._n_frames is None:
                self._seek(self.tell() + 1)
            self.seek(current)
        assert self._n_frames is not None
        return self._n_frames

    def seek(self, frame: int) -> None:
        """Select a given frame as current image"""
        if not self._seek_check(frame):
            return
        self._seek(frame)
        if self._im is not None and (
            self.im.size != self._tile_size or self.im.mode != self.mode
        ):
            # The core image will no longer be used
            self._im = None

    def _seek(self, frame: int) -> None:
        if isinstance(self._fp, DeferredError):
            raise self._fp.ex
        self.fp = self._fp

        while len(self._frame_pos) <= frame:
            if not self.__next:
                msg = "no more images in TIFF file"
                raise EOFError(msg)
            logger.debug(
                "Seeking to frame %s, on frame %s, __next %s, location: %s",
                frame,
                self.__frame,
                self.__next,
                self.fp.tell(),
            )
            if self.__next >= 2**63:
                msg = "Unable to seek to frame"
                raise ValueError(msg)
            self.fp.seek(self.__next)
            self._frame_pos.append(self.__next)
            logger.debug("Loading tags, location: %s", self.fp.tell())
            self.tag_v2.load(self.fp)
            if self.tag_v2.next in self._frame_pos:
                # This IFD has already been processed
                # Declare this to be the end of the image
                self.__next = 0
            else:
                self.__next = self.tag_v2.next
            if self.__next == 0:
                self._n_frames = frame + 1
            if len(self._frame_pos) == 1:
                self.is_animated = self.__next != 0
            self.__frame += 1
        self.fp.seek(self._frame_pos[frame])
        self.tag_v2.load(self.fp)
        if XMP in self.tag_v2:
            self.info["xmp"] = self.tag_v2[XMP]
        elif "xmp" in self.info:
            del self.info["xmp"]
        self._reload_exif()
        # fill the legacy tag/ifd entries
        self.tag = self.ifd = ImageFileDirectory_v1.from_v2(self.tag_v2)
        self.__frame = frame
        self._setup()

    def tell(self) -> int:
        """Return the current frame number"""
        return self.__frame

    def get_photoshop_blocks(self) -> dict[int, dict[str, bytes]]:
        """
        Returns a dictionary of Photoshop "Image Resource Blocks".
        The keys are the image resource ID. For more information, see
        https://www.adobe.com/devnet-apps/photoshop/fileformatashtml/#50577409_pgfId-1037727

        :returns: Photoshop "Image Resource Blocks" in a dictionary.
        """
        blocks = {}
        val = self.tag_v2.get(ExifTags.Base.ImageResources)
        if val:
            while val.startswith(b"8BIM"):
                id = i16(val[4:6])
                n = math.ceil((val[6] + 1) / 2) * 2
                size = i32(val[6 + n : 10 + n])
                data = val[10 + n : 10 + n + size]
                blocks[id] = {"data": data}

                val = val[math.ceil((10 + n + size) / 2) * 2 :]
        return blocks

    def load(self) -> Image.core.PixelAccess | None:
        if self.tile and self.use_load_libtiff:
            return self._load_libtiff()
        return super().load()

    def load_prepare(self) -> None:
        if self._im is None:
            Image._decompression_bomb_check(self._tile_size)
            self.im = Image.core.new(self.mode, self._tile_size)
        ImageFile.ImageFile.load_prepare(self)

    def load_end(self) -> None:
        # allow closing if we're on the first frame, there's no next
        # This is the ImageFile.load path only, libtiff specific below.
        if not self.is_animated:
            self._close_exclusive_fp_after_loading = True

            # load IFD data from fp before it is closed
            exif = self.getexif()
            for key in TiffTags.TAGS_V2_GROUPS:
                if key not in exif:
                    continue
                exif.get_ifd(key)

        ImageOps.exif_transpose(self, in_place=True)
        if ExifTags.Base.Orientation in self.tag_v2:
            del self.tag_v2[ExifTags.Base.Orientation]

    def _load_libtiff(self) -> Image.core.PixelAccess | None:
        """Overload method triggered when we detect a compressed tiff
        Calls out to libtiff"""

        Image.Image.load(self)

        self.load_prepare()

        if not len(self.tile) == 1:
            msg = "Not exactly one tile"
            raise OSError(msg)

        # (self._compression, (extents tuple),
        #   0, (rawmode, self._compression, fp))
        extents = self.tile[0][1]
        args = self.tile[0][3]

        # To be nice on memory footprint, if there's a
        # file descriptor, use that instead of reading
        # into a string in python.
        try:
            fp = hasattr(self.fp, "fileno") and self.fp.fileno()
            # flush the file descriptor, prevents error on pypy 2.4+
            # should also eliminate the need for fp.tell
            # in _seek
            if hasattr(self.fp, "flush"):
                self.fp.flush()
        except OSError:
            # io.BytesIO have a fileno, but returns an OSError if
            # it doesn't use a file descriptor.
            fp = False

        if fp:
            assert isinstance(args, tuple)
            args_list = list(args)
            args_list[2] = fp
            args = tuple(args_list)

        decoder = Image._getdecoder(self.mode, "libtiff", args, self.decoderconfig)
        try:
            decoder.setimage(self.im, extents)
        except ValueError as e:
            msg = "Couldn't set the image"
            raise OSError(msg) from e

        close_self_fp = self._exclusive_fp and not self.is_animated
        if hasattr(self.fp, "getvalue"):
            # We've got a stringio like thing passed in. Yay for all in memory.
            # The decoder needs the entire file in one shot, so there's not
            # a lot we can do here other than give it the entire file.
            # unless we could do something like get the address of the
            # underlying string for stringio.
            #
            # Rearranging for supporting byteio items, since they have a fileno
            # that returns an OSError if there's no underlying fp. Easier to
            # deal with here by reordering.
            logger.debug("have getvalue. just sending in a string from getvalue")
            n, err = decoder.decode(self.fp.getvalue())
        elif fp:
            # we've got a actual file on disk, pass in the fp.
            logger.debug("have fileno, calling fileno version of the decoder.")
            if not close_self_fp:
                self.fp.seek(0)
            # Save and restore the file position, because libtiff will move it
            # outside of the Python runtime, and that will confuse
            # io.BufferedReader and possible others.
            # NOTE: This must use os.lseek(), and not fp.tell()/fp.seek(),
            # because the buffer read head already may not equal the actual
            # file position, and fp.seek() may just adjust it's internal
            # pointer and not actually seek the OS file handle.
            pos = os.lseek(fp, 0, os.SEEK_CUR)
            # 4 bytes, otherwise the trace might error out
            n, err = decoder.decode(b"fpfp")
            os.lseek(fp, pos, os.SEEK_SET)
        else:
            # we have something else.
            logger.debug("don't have fileno or getvalue. just reading")
            self.fp.seek(0)
            # UNDONE -- so much for that buffer size thing.
            n, err = decoder.decode(self.fp.read())

        self.tile = []
        self.readonly = 0

        self.load_end()

        if close_self_fp:
            self.fp.close()
            self.fp = None  # might be shared

        if err < 0:
            msg = f"decoder error {err}"
            raise OSError(msg)

        return Image.Image.load(self)

    def _setup(self) -> None:
        """Setup this image object based on current tags"""

        if 0xBC01 in self.tag_v2:
            msg = "Windows Media Photo files not yet supported"
            raise OSError(msg)

        # extract relevant tags
        self._compression = COMPRESSION_INFO[self.tag_v2.get(COMPRESSION, 1)]
        self._planar_configuration = self.tag_v2.get(PLANAR_CONFIGURATION, 1)

        # photometric is a required tag, but not everyone is reading
        # the specification
        photo = self.tag_v2.get(PHOTOMETRIC_INTERPRETATION, 0)

        # old style jpeg compression images most certainly are YCbCr
        if self._compression == "tiff_jpeg":
            photo = 6

        fillorder = self.tag_v2.get(FILLORDER, 1)

        logger.debug("*** Summary ***")
        logger.debug("- compression: %s", self._compression)
        logger.debug("- photometric_interpretation: %s", photo)
        logger.debug("- planar_configuration: %s", self._planar_configuration)
        logger.debug("- fill_order: %s", fillorder)
        logger.debug("- YCbCr subsampling: %s", self.tag_v2.get(YCBCRSUBSAMPLING))

        # size
        try:
            xsize = self.tag_v2[IMAGEWIDTH]
            ysize = self.tag_v2[IMAGELENGTH]
        except KeyError as e:
            msg = "Missing dimensions"
            raise TypeError(msg) from e
        if not isinstance(xsize, int) or not isinstance(ysize, int):
            msg = "Invalid dimensions"
            raise ValueError(msg)
        self._tile_size = xsize, ysize
        orientation = self.tag_v2.get(ExifTags.Base.Orientation)
        if orientation in (5, 6, 7, 8):
            self._size = ysize, xsize
        else:
            self._size = xsize, ysize

        logger.debug("- size: %s", self.size)

        sample_format = self.tag_v2.get(SAMPLEFORMAT, (1,))
        if len(sample_format) > 1 and max(sample_format) == min(sample_format) == 1:
            # SAMPLEFORMAT is properly per band, so an RGB image will
            # be (1,1,1).  But, we don't support per band pixel types,
            # and anything more than one band is a uint8. So, just
            # take the first element. Revisit this if adding support
            # for more exotic images.
            sample_format = (1,)

        bps_tuple = self.tag_v2.get(BITSPERSAMPLE, (1,))
        extra_tuple = self.tag_v2.get(EXTRASAMPLES, ())
        if photo in (2, 6, 8):  # RGB, YCbCr, LAB
            bps_count = 3
        elif photo == 5:  # CMYK
            bps_count = 4
        else:
            bps_count = 1
        bps_count += len(extra_tuple)
        bps_actual_count = len(bps_tuple)
        samples_per_pixel = self.tag_v2.get(
            SAMPLESPERPIXEL,
            3 if self._compression == "tiff_jpeg" and photo in (2, 6) else 1,
        )

        if samples_per_pixel > MAX_SAMPLESPERPIXEL:
            # DOS check, samples_per_pixel can be a Long, and we extend the tuple below
            logger.error(
                "More samples per pixel than can be decoded: %s", samples_per_pixel
            )
            msg = "Invalid value for samples per pixel"
            raise SyntaxError(msg)

        if samples_per_pixel < bps_actual_count:
            # If a file has more values in bps_tuple than expected,
            # remove the excess.
            bps_tuple = bps_tuple[:samples_per_pixel]
        elif samples_per_pixel > bps_actual_count and bps_actual_count == 1:
            # If a file has only one value in bps_tuple, when it should have more,
            # presume it is the same number of bits for all of the samples.
            bps_tuple = bps_tuple * samples_per_pixel

        if len(bps_tuple) != samples_per_pixel:
            msg = "unknown data organization"
            raise SyntaxError(msg)

        # mode: check photometric interpretation and bits per pixel
        key = (
            self.tag_v2.prefix,
            photo,
            sample_format,
            fillorder,
            bps_tuple,
            extra_tuple,
        )
        logger.debug("format key: %s", key)
        try:
            self._mode, rawmode = OPEN_INFO[key]
        except KeyError as e:
            logger.debug("- unsupported format")
            msg = "unknown pixel mode"
            raise SyntaxError(msg) from e

        logger.debug("- raw mode: %s", rawmode)
        logger.debug("- pil mode: %s", self.mode)

        self.info["compression"] = self._compression

        xres = self.tag_v2.get(X_RESOLUTION, 1)
        yres = self.tag_v2.get(Y_RESOLUTION, 1)

        if xres and yres:
            resunit = self.tag_v2.get(RESOLUTION_UNIT)
            if resunit == 2:  # dots per inch
                self.info["dpi"] = (xres, yres)
            elif resunit == 3:  # dots per centimeter. convert to dpi
                self.info["dpi"] = (xres * 2.54, yres * 2.54)
            elif resunit is None:  # used to default to 1, but now 2)
                self.info["dpi"] = (xres, yres)
                # For backward compatibility,
                # we also preserve the old behavior
                self.info["resolution"] = xres, yres
            else:  # No absolute unit of measurement
                self.info["resolution"] = xres, yres

        # build tile descriptors
        x = y = layer = 0
        self.tile = []
        self.use_load_libtiff = READ_LIBTIFF or self._compression != "raw"
        if self.use_load_libtiff:
            # Decoder expects entire file as one tile.
            # There's a buffer size limit in load (64k)
            # so large g4 images will fail if we use that
            # function.
            #
            # Setup the one tile for the whole image, then
            # use the _load_libtiff function.

            # libtiff handles the fillmode for us, so 1;IR should
            # actually be 1;I. Including the R double reverses the
            # bits, so stripes of the image are reversed.  See
            # https://github.com/python-pillow/Pillow/issues/279
            if fillorder == 2:
                # Replace fillorder with fillorder=1
                key = key[:3] + (1,) + key[4:]
                logger.debug("format key: %s", key)
                # this should always work, since all the
                # fillorder==2 modes have a corresponding
                # fillorder=1 mode
                self._mode, rawmode = OPEN_INFO[key]
            # YCbCr images with new jpeg compression with pixels in one plane
            # unpacked straight into RGB values
            if (
                photo == 6
                and self._compression == "jpeg"
                and self._planar_configuration == 1
            ):
                rawmode = "RGB"
            # libtiff always returns the bytes in native order.
            # we're expecting image byte order. So, if the rawmode
            # contains I;16, we need to convert from native to image
            # byte order.
            elif rawmode == "I;16":
                rawmode = "I;16N"
            elif rawmode.endswith((";16B", ";16L")):
                rawmode = rawmode[:-1] + "N"

            # Offset in the tile tuple is 0, we go from 0,0 to
            # w,h, and we only do this once -- eds
            a = (rawmode, self._compression, False, self.tag_v2.offset)
            self.tile.append(ImageFile._Tile("libtiff", (0, 0, xsize, ysize), 0, a))

        elif STRIPOFFSETS in self.tag_v2 or TILEOFFSETS in self.tag_v2:
            # striped image
            if STRIPOFFSETS in self.tag_v2:
                offsets = self.tag_v2[STRIPOFFSETS]
                h = self.tag_v2.get(ROWSPERSTRIP, ysize)
                w = xsize
            else:
                # tiled image
                offsets = self.tag_v2[TILEOFFSETS]
                tilewidth = self.tag_v2.get(TILEWIDTH)
                h = self.tag_v2.get(TILELENGTH)
                if not isinstance(tilewidth, int) or not isinstance(h, int):
                    msg = "Invalid tile dimensions"
                    raise ValueError(msg)
                w = tilewidth

            if w == xsize and h == ysize and self._planar_configuration != 2:
                # Every tile covers the image. Only use the last offset
                offsets = offsets[-1:]

            for offset in offsets:
                if x + w > xsize:
                    stride = w * sum(bps_tuple) / 8  # bytes per line
                else:
                    stride = 0

                tile_rawmode = rawmode
                if self._planar_configuration == 2:
                    # each band on it's own layer
                    tile_rawmode = rawmode[layer]
                    # adjust stride width accordingly
                    stride /= bps_count

                args = (tile_rawmode, int(stride), 1)
                self.tile.append(
                    ImageFile._Tile(
                        self._compression,
                        (x, y, min(x + w, xsize), min(y + h, ysize)),
                        offset,
                        args,
                    )
                )
                x += w
                if x >= xsize:
                    x, y = 0, y + h
                    if y >= ysize:
                        y = 0
                        layer += 1
        else:
            logger.debug("- unsupported data organization")
            msg = "unknown data organization"
            raise SyntaxError(msg)

        # Fix up info.
        if ICCPROFILE in self.tag_v2:
            self.info["icc_profile"] = self.tag_v2[ICCPROFILE]

        # fixup palette descriptor

        if self.mode in ["P", "PA"]:
            palette = [o8(b // 256) for b in self.tag_v2[COLORMAP]]
            self.palette = ImagePalette.raw("RGB;L", b"".join(palette))


#
# --------------------------------------------------------------------
# Write TIFF files

# little endian is default except for image modes with
# explicit big endian byte-order

SAVE_INFO = {
    # mode => rawmode, byteorder, photometrics,
    #           sampleformat, bitspersample, extra
    "1": ("1", II, 1, 1, (1,), None),
    "L": ("L", II, 1, 1, (8,), None),
    "LA": ("LA", II, 1, 1, (8, 8), 2),
    "P": ("P", II, 3, 1, (8,), None),
    "PA": ("PA", II, 3, 1, (8, 8), 2),
    "I": ("I;32S", II, 1, 2, (32,), None),
    "I;16": ("I;16", II, 1, 1, (16,), None),
    "I;16S": ("I;16S", II, 1, 2, (16,), None),
    "F": ("F;32F", II, 1, 3, (32,), None),
    "RGB": ("RGB", II, 2, 1, (8, 8, 8), None),
    "RGBX": ("RGBX", II, 2, 1, (8, 8, 8, 8), 0),
    "RGBA": ("RGBA", II, 2, 1, (8, 8, 8, 8), 2),
    "CMYK": ("CMYK", II, 5, 1, (8, 8, 8, 8), None),
    "YCbCr": ("YCbCr", II, 6, 1, (8, 8, 8), None),
    "LAB": ("LAB", II, 8, 1, (8, 8, 8), None),
    "I;32BS": ("I;32BS", MM, 1, 2, (32,), None),
    "I;16B": ("I;16B", MM, 1, 1, (16,), None),
    "I;16BS": ("I;16BS", MM, 1, 2, (16,), None),
    "F;32BF": ("F;32BF", MM, 1, 3, (32,), None),
}


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    try:
        rawmode, prefix, photo, format, bits, extra = SAVE_INFO[im.mode]
    except KeyError as e:
        msg = f"cannot write mode {im.mode} as TIFF"
        raise OSError(msg) from e

    encoderinfo = im.encoderinfo
    encoderconfig = im.encoderconfig

    ifd = ImageFileDirectory_v2(prefix=prefix)
    if encoderinfo.get("big_tiff"):
        ifd._bigtiff = True

    try:
        compression = encoderinfo["compression"]
    except KeyError:
        compression = im.info.get("compression")
        if isinstance(compression, int):
            # compression value may be from BMP. Ignore it
            compression = None
    if compression is None:
        compression = "raw"
    elif compression == "tiff_jpeg":
        # OJPEG is obsolete, so use new-style JPEG compression instead
        compression = "jpeg"
    elif compression == "tiff_deflate":
        compression = "tiff_adobe_deflate"

    libtiff = WRITE_LIBTIFF or compression != "raw"

    # required for color libtiff images
    ifd[PLANAR_CONFIGURATION] = 1

    ifd[IMAGEWIDTH] = im.size[0]
    ifd[IMAGELENGTH] = im.size[1]

    # write any arbitrary tags passed in as an ImageFileDirectory
    if "tiffinfo" in encoderinfo:
        info = encoderinfo["tiffinfo"]
    elif "exif" in encoderinfo:
        info = encoderinfo["exif"]
        if isinstance(info, bytes):
            exif = Image.Exif()
            exif.load(info)
            info = exif
    else:
        info = {}
    logger.debug("Tiffinfo Keys: %s", list(info))
    if isinstance(info, ImageFileDirectory_v1):
        info = info.to_v2()
    for key in info:
        if isinstance(info, Image.Exif) and key in TiffTags.TAGS_V2_GROUPS:
            ifd[key] = info.get_ifd(key)
        else:
            ifd[key] = info.get(key)
        try:
            ifd.tagtype[key] = info.tagtype[key]
        except Exception:
            pass  # might not be an IFD. Might not have populated type

    legacy_ifd = {}
    if hasattr(im, "tag"):
        legacy_ifd = im.tag.to_v2()

    supplied_tags = {**legacy_ifd, **getattr(im, "tag_v2", {})}
    for tag in (
        # IFD offset that may not be correct in the saved image
        EXIFIFD,
        # Determined by the image format and should not be copied from legacy_ifd.
        SAMPLEFORMAT,
    ):
        if tag in supplied_tags:
            del supplied_tags[tag]

    # additions written by Greg Couch, gregc@cgl.ucsf.edu
    # inspired by image-sig posting from Kevin Cazabon, kcazabon@home.com
    if hasattr(im, "tag_v2"):
        # preserve tags from original TIFF image file
        for key in (
            RESOLUTION_UNIT,
            X_RESOLUTION,
            Y_RESOLUTION,
            IPTC_NAA_CHUNK,
            PHOTOSHOP_CHUNK,
            XMP,
        ):
            if key in im.tag_v2:
                if key == IPTC_NAA_CHUNK and im.tag_v2.tagtype[key] not in (
                    TiffTags.BYTE,
                    TiffTags.UNDEFINED,
                ):
                    del supplied_tags[key]
                else:
                    ifd[key] = im.tag_v2[key]
                    ifd.tagtype[key] = im.tag_v2.tagtype[key]

    # preserve ICC profile (should also work when saving other formats
    # which support profiles as TIFF) -- 2008-06-06 Florian Hoech
    icc = encoderinfo.get("icc_profile", im.info.get("icc_profile"))
    if icc:
        ifd[ICCPROFILE] = icc

    for key, name in [
        (IMAGEDESCRIPTION, "description"),
        (X_RESOLUTION, "resolution"),
        (Y_RESOLUTION, "resolution"),
        (X_RESOLUTION, "x_resolution"),
        (Y_RESOLUTION, "y_resolution"),
        (RESOLUTION_UNIT, "resolution_unit"),
        (SOFTWARE, "software"),
        (DATE_TIME, "date_time"),
        (ARTIST, "artist"),
        (COPYRIGHT, "copyright"),
    ]:
        if name in encoderinfo:
            ifd[key] = encoderinfo[name]

    dpi = encoderinfo.get("dpi")
    if dpi:
        ifd[RESOLUTION_UNIT] = 2
        ifd[X_RESOLUTION] = dpi[0]
        ifd[Y_RESOLUTION] = dpi[1]

    if bits != (1,):
        ifd[BITSPERSAMPLE] = bits
        if len(bits) != 1:
            ifd[SAMPLESPERPIXEL] = len(bits)
    if extra is not None:
        ifd[EXTRASAMPLES] = extra
    if format != 1:
        ifd[SAMPLEFORMAT] = format

    if PHOTOMETRIC_INTERPRETATION not in ifd:
        ifd[PHOTOMETRIC_INTERPRETATION] = photo
    elif im.mode in ("1", "L") and ifd[PHOTOMETRIC_INTERPRETATION] == 0:
        if im.mode == "1":
            inverted_im = im.copy()
            px = inverted_im.load()
            if px is not None:
                for y in range(inverted_im.height):
                    for x in range(inverted_im.width):
                        px[x, y] = 0 if px[x, y] == 255 else 255
                im = inverted_im
        else:
            im = ImageOps.invert(im)

    if im.mode in ["P", "PA"]:
        lut = im.im.getpalette("RGB", "RGB;L")
        colormap = []
        colors = len(lut) // 3
        for i in range(3):
            colormap += [v * 256 for v in lut[colors * i : colors * (i + 1)]]
            colormap += [0] * (256 - colors)
        ifd[COLORMAP] = colormap
    # data orientation
    w, h = ifd[IMAGEWIDTH], ifd[IMAGELENGTH]
    stride = len(bits) * ((w * bits[0] + 7) // 8)
    if ROWSPERSTRIP not in ifd:
        # aim for given strip size (64 KB by default) when using libtiff writer
        if libtiff:
            im_strip_size = encoderinfo.get("strip_size", STRIP_SIZE)
            rows_per_strip = 1 if stride == 0 else min(im_strip_size // stride, h)
            # JPEG encoder expects multiple of 8 rows
            if compression == "jpeg":
                rows_per_strip = min(((rows_per_strip + 7) // 8) * 8, h)
        else:
            rows_per_strip = h
        if rows_per_strip == 0:
            rows_per_strip = 1
        ifd[ROWSPERSTRIP] = rows_per_strip
    strip_byte_counts = 1 if stride == 0 else stride * ifd[ROWSPERSTRIP]
    strips_per_image = (h + ifd[ROWSPERSTRIP] - 1) // ifd[ROWSPERSTRIP]
    if strip_byte_counts >= 2**16:
        ifd.tagtype[STRIPBYTECOUNTS] = TiffTags.LONG
    ifd[STRIPBYTECOUNTS] = (strip_byte_counts,) * (strips_per_image - 1) + (
        stride * h - strip_byte_counts * (strips_per_image - 1),
    )
    ifd[STRIPOFFSETS] = tuple(
        range(0, strip_byte_counts * strips_per_image, strip_byte_counts)
    )  # this is adjusted by IFD writer
    # no compression by default:
    ifd[COMPRESSION] = COMPRESSION_INFO_REV.get(compression, 1)

    if im.mode == "YCbCr":
        for tag, default_value in {
            YCBCRSUBSAMPLING: (1, 1),
            REFERENCEBLACKWHITE: (0, 255, 128, 255, 128, 255),
        }.items():
            ifd.setdefault(tag, default_value)

    blocklist = [TILEWIDTH, TILELENGTH, TILEOFFSETS, TILEBYTECOUNTS]
    if libtiff:
        if "quality" in encoderinfo:
            quality = encoderinfo["quality"]
            if not isinstance(quality, int) or quality < 0 or quality > 100:
                msg = "Invalid quality setting"
                raise ValueError(msg)
            if compression != "jpeg":
                msg = "quality setting only supported for 'jpeg' compression"
                raise ValueError(msg)
            ifd[JPEGQUALITY] = quality

        logger.debug("Saving using libtiff encoder")
        logger.debug("Items: %s", sorted(ifd.items()))
        _fp = 0
        if hasattr(fp, "fileno"):
            try:
                fp.seek(0)
                _fp = fp.fileno()
            except io.UnsupportedOperation:
                pass

        # optional types for non core tags
        types = {}
        # STRIPOFFSETS and STRIPBYTECOUNTS are added by the library
        # based on the data in the strip.
        # OSUBFILETYPE is deprecated.
        # The other tags expect arrays with a certain length (fixed or depending on
        # BITSPERSAMPLE, etc), passing arrays with a different length will result in
        # segfaults. Block these tags until we add extra validation.
        # SUBIFD may also cause a segfault.
        blocklist += [
            OSUBFILETYPE,
            REFERENCEBLACKWHITE,
            STRIPBYTECOUNTS,
            STRIPOFFSETS,
            TRANSFERFUNCTION,
            SUBIFD,
        ]

        # bits per sample is a single short in the tiff directory, not a list.
        atts: dict[int, Any] = {BITSPERSAMPLE: bits[0]}
        # Merge the ones that we have with (optional) more bits from
        # the original file, e.g x,y resolution so that we can
        # save(load('')) == original file.
        for tag, value in itertools.chain(ifd.items(), supplied_tags.items()):
            # Libtiff can only process certain core items without adding
            # them to the custom dictionary.
            # Custom items are supported for int, float, unicode, string and byte
            # values. Other types and tuples require a tagtype.
            if tag not in TiffTags.LIBTIFF_CORE:
                if not getattr(Image.core, "libtiff_support_custom_tags", False):
                    continue

                if tag in TiffTags.TAGS_V2_GROUPS:
                    types[tag] = TiffTags.LONG8
                elif tag in ifd.tagtype:
                    types[tag] = ifd.tagtype[tag]
                elif not (isinstance(value, (int, float, str, bytes))):
                    continue
                else:
                    type = TiffTags.lookup(tag).type
                    if type:
                        types[tag] = type
            if tag not in atts and tag not in blocklist:
                if isinstance(value, str):
                    atts[tag] = value.encode("ascii", "replace") + b"\0"
                elif isinstance(value, IFDRational):
                    atts[tag] = float(value)
                else:
                    atts[tag] = value

        if SAMPLEFORMAT in atts and len(atts[SAMPLEFORMAT]) == 1:
            atts[SAMPLEFORMAT] = atts[SAMPLEFORMAT][0]

        logger.debug("Converted items: %s", sorted(atts.items()))

        # libtiff always expects the bytes in native order.
        # we're storing image byte order. So, if the rawmode
        # contains I;16, we need to convert from native to image
        # byte order.
        if im.mode in ("I;16B", "I;16"):
            rawmode = "I;16N"

        # Pass tags as sorted list so that the tags are set in a fixed order.
        # This is required by libtiff for some tags. For example, the JPEGQUALITY
        # pseudo tag requires that the COMPRESS tag was already set.
        tags = list(atts.items())
        tags.sort()
        a = (rawmode, compression, _fp, filename, tags, types)
        encoder = Image._getencoder(im.mode, "libtiff", a, encoderconfig)
        encoder.setimage(im.im, (0, 0) + im.size)
        while True:
            errcode, data = encoder.encode(ImageFile.MAXBLOCK)[1:]
            if not _fp:
                fp.write(data)
            if errcode:
                break
        if errcode < 0:
            msg = f"encoder error {errcode} when writing image file"
            raise OSError(msg)

    else:
        for tag in blocklist:
            del ifd[tag]
        offset = ifd.save(fp)

        ImageFile._save(
            im,
            fp,
            [ImageFile._Tile("raw", (0, 0) + im.size, offset, (rawmode, stride, 1))],
        )

    # -- helper for multi-page save --
    if "_debug_multipage" in encoderinfo:
        # just to access o32 and o16 (using correct byte order)
        setattr(im, "_debug_multipage", ifd)


class AppendingTiffWriter(io.BytesIO):
    fieldSizes = [
        0,  # None
        1,  # byte
        1,  # ascii
        2,  # short
        4,  # long
        8,  # rational
        1,  # sbyte
        1,  # undefined
        2,  # sshort
        4,  # slong
        8,  # srational
        4,  # float
        8,  # double
        4,  # ifd
        2,  # unicode
        4,  # complex
        8,  # long8
    ]

    Tags = {
        273,  # StripOffsets
        288,  # FreeOffsets
        324,  # TileOffsets
        519,  # JPEGQTables
        520,  # JPEGDCTables
        521,  # JPEGACTables
    }

    def __init__(self, fn: StrOrBytesPath | IO[bytes], new: bool = False) -> None:
        self.f: IO[bytes]
        if is_path(fn):
            self.name = fn
            self.close_fp = True
            try:
                self.f = open(fn, "w+b" if new else "r+b")
            except OSError:
                self.f = open(fn, "w+b")
        else:
            self.f = cast(IO[bytes], fn)
            self.close_fp = False
        self.beginning = self.f.tell()
        self.setup()

    def setup(self) -> None:
        # Reset everything.
        self.f.seek(self.beginning, os.SEEK_SET)

        self.whereToWriteNewIFDOffset: int | None = None
        self.offsetOfNewPage = 0

        self.IIMM = iimm = self.f.read(4)
        self._bigtiff = b"\x2b" in iimm
        if not iimm:
            # empty file - first page
            self.isFirst = True
            return

        self.isFirst = False
        if iimm not in PREFIXES:
            msg = "Invalid TIFF file header"
            raise RuntimeError(msg)

        self.setEndian("<" if iimm.startswith(II) else ">")

        if self._bigtiff:
            self.f.seek(4, os.SEEK_CUR)
        self.skipIFDs()
        self.goToEnd()

    def finalize(self) -> None:
        if self.isFirst:
            return

        # fix offsets
        self.f.seek(self.offsetOfNewPage)

        iimm = self.f.read(4)
        if not iimm:
            # Make it easy to finish a frame without committing to a new one.
            return

        if iimm != self.IIMM:
            msg = "IIMM of new page doesn't match IIMM of first page"
            raise RuntimeError(msg)

        if self._bigtiff:
            self.f.seek(4, os.SEEK_CUR)
        ifd_offset = self._read(8 if self._bigtiff else 4)
        ifd_offset += self.offsetOfNewPage
        assert self.whereToWriteNewIFDOffset is not None
        self.f.seek(self.whereToWriteNewIFDOffset)
        self._write(ifd_offset, 8 if self._bigtiff else 4)
        self.f.seek(ifd_offset)
        self.fixIFD()

    def newFrame(self) -> None:
        # Call this to finish a frame.
        self.finalize()
        self.setup()

    def __enter__(self) -> AppendingTiffWriter:
        return self

    def __exit__(self, *args: object) -> None:
        if self.close_fp:
            self.close()

    def tell(self) -> int:
        return self.f.tell() - self.offsetOfNewPage

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        """
        :param offset: Distance to seek.
        :param whence: Whether the distance is relative to the start,
                       end or current position.
        :returns: The resulting position, relative to the start.
        """
        if whence == os.SEEK_SET:
            offset += self.offsetOfNewPage

        self.f.seek(offset, whence)
        return self.tell()

    def goToEnd(self) -> None:
        self.f.seek(0, os.SEEK_END)
        pos = self.f.tell()

        # pad to 16 byte boundary
        pad_bytes = 16 - pos % 16
        if 0 < pad_bytes < 16:
            self.f.write(bytes(pad_bytes))
        self.offsetOfNewPage = self.f.tell()

    def setEndian(self, endian: str) -> None:
        self.endian = endian
        self.longFmt = f"{self.endian}L"
        self.shortFmt = f"{self.endian}H"
        self.tagFormat = f"{self.endian}HH" + ("Q" if self._bigtiff else "L")

    def skipIFDs(self) -> None:
        while True:
            ifd_offset = self._read(8 if self._bigtiff else 4)
            if ifd_offset == 0:
                self.whereToWriteNewIFDOffset = self.f.tell() - (
                    8 if self._bigtiff else 4
                )
                break

            self.f.seek(ifd_offset)
            num_tags = self._read(8 if self._bigtiff else 2)
            self.f.seek(num_tags * (20 if self._bigtiff else 12), os.SEEK_CUR)

    def write(self, data: Buffer, /) -> int:
        return self.f.write(data)

    def _fmt(self, field_size: int) -> str:
        try:
            return {2: "H", 4: "L", 8: "Q"}[field_size]
        except KeyError:
            msg = "offset is not supported"
            raise RuntimeError(msg)

    def _read(self, field_size: int) -> int:
        (value,) = struct.unpack(
            self.endian + self._fmt(field_size), self.f.read(field_size)
        )
        return value

    def readShort(self) -> int:
        return self._read(2)

    def readLong(self) -> int:
        return self._read(4)

    @staticmethod
    def _verify_bytes_written(bytes_written: int | None, expected: int) -> None:
        if bytes_written is not None and bytes_written != expected:
            msg = f"wrote only {bytes_written} bytes but wanted {expected}"
            raise RuntimeError(msg)

    def _rewriteLast(
        self, value: int, field_size: int, new_field_size: int = 0
    ) -> None:
        self.f.seek(-field_size, os.SEEK_CUR)
        if not new_field_size:
            new_field_size = field_size
        bytes_written = self.f.write(
            struct.pack(self.endian + self._fmt(new_field_size), value)
        )
        self._verify_bytes_written(bytes_written, new_field_size)

    def rewriteLastShortToLong(self, value: int) -> None:
        self._rewriteLast(value, 2, 4)

    def rewriteLastShort(self, value: int) -> None:
        return self._rewriteLast(value, 2)

    def rewriteLastLong(self, value: int) -> None:
        return self._rewriteLast(value, 4)

    def _write(self, value: int, field_size: int) -> None:
        bytes_written = self.f.write(
            struct.pack(self.endian + self._fmt(field_size), value)
        )
        self._verify_bytes_written(bytes_written, field_size)

    def writeShort(self, value: int) -> None:
        self._write(value, 2)

    def writeLong(self, value: int) -> None:
        self._write(value, 4)

    def close(self) -> None:
        self.finalize()
        if self.close_fp:
            self.f.close()

    def fixIFD(self) -> None:
        num_tags = self._read(8 if self._bigtiff else 2)

        for i in range(num_tags):
            tag, field_type, count = struct.unpack(
                self.tagFormat, self.f.read(12 if self._bigtiff else 8)
            )

            field_size = self.fieldSizes[field_type]
            total_size = field_size * count
            fmt_size = 8 if self._bigtiff else 4
            is_local = total_size <= fmt_size
            if not is_local:
                offset = self._read(fmt_size) + self.offsetOfNewPage
                self._rewriteLast(offset, fmt_size)

            if tag in self.Tags:
                cur_pos = self.f.tell()

                logger.debug(
                    "fixIFD: %s (%d) - type: %s (%d) - type size: %d - count: %d",
                    TiffTags.lookup(tag).name,
                    tag,
                    TYPES.get(field_type, "unknown"),
                    field_type,
                    field_size,
                    count,
                )

                if is_local:
                    self._fixOffsets(count, field_size)
                    self.f.seek(cur_pos + fmt_size)
                else:
                    self.f.seek(offset)
                    self._fixOffsets(count, field_size)
                    self.f.seek(cur_pos)

            elif is_local:
                # skip the locally stored value that is not an offset
                self.f.seek(fmt_size, os.SEEK_CUR)

    def _fixOffsets(self, count: int, field_size: int) -> None:
        for i in range(count):
            offset = self._read(field_size)
            offset += self.offsetOfNewPage

            new_field_size = 0
            if self._bigtiff and field_size in (2, 4) and offset >= 2**32:
                # offset is now too large - we must convert long to long8
                new_field_size = 8
            elif field_size == 2 and offset >= 2**16:
                # offset is now too large - we must convert short to long
                new_field_size = 4
            if new_field_size:
                if count != 1:
                    msg = "not implemented"
                    raise RuntimeError(msg)  # XXX TODO

                # simple case - the offset is just one and therefore it is
                # local (not referenced with another offset)
                self._rewriteLast(offset, field_size, new_field_size)
                # Move back past the new offset, past 'count', and before 'field_type'
                rewind = -new_field_size - 4 - 2
                self.f.seek(rewind, os.SEEK_CUR)
                self.writeShort(new_field_size)  # rewrite the type
                self.f.seek(2 - rewind, os.SEEK_CUR)
            else:
                self._rewriteLast(offset, field_size)

    def fixOffsets(
        self, count: int, isShort: bool = False, isLong: bool = False
    ) -> None:
        if isShort:
            field_size = 2
        elif isLong:
            field_size = 4
        else:
            field_size = 0
        return self._fixOffsets(count, field_size)


def _save_all(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    append_images = list(im.encoderinfo.get("append_images", []))
    if not hasattr(im, "n_frames") and not append_images:
        return _save(im, fp, filename)

    cur_idx = im.tell()
    try:
        with AppendingTiffWriter(fp) as tf:
            for ims in [im] + append_images:
                if not hasattr(ims, "encoderinfo"):
                    ims.encoderinfo = {}
                if not hasattr(ims, "encoderconfig"):
                    ims.encoderconfig = ()
                nfr = getattr(ims, "n_frames", 1)

                for idx in range(nfr):
                    ims.seek(idx)
                    ims.load()
                    _save(ims, tf, filename)
                    tf.newFrame()
    finally:
        im.seek(cur_idx)


#
# --------------------------------------------------------------------
# Register

Image.register_open(TiffImageFile.format, TiffImageFile, _accept)
Image.register_save(TiffImageFile.format, _save)
Image.register_save_all(TiffImageFile.format, _save_all)

Image.register_extensions(TiffImageFile.format, [".tif", ".tiff"])

Image.register_mime(TiffImageFile.format, "image/tiff")

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\exception_mapping_utils.py ===
import json
import traceback
from typing import Any, Optional

import httpx

import litellm
from litellm._logging import verbose_logger

from ..exceptions import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    BadRequestError,
    ContentPolicyViolationError,
    ContextWindowExceededError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
    UnprocessableEntityError,
)


class ExceptionCheckers:
    """
    Helper class for checking various error conditions in exception strings.
    """
    
    @staticmethod
    def is_error_str_rate_limit(error_str: str) -> bool:
        """
        Check if an error string indicates a rate limit error.
        
        Args:
            error_str: The error string to check
            
        Returns:
            True if the error indicates a rate limit, False otherwise
        """
        if not isinstance(error_str, str):
            return False
            
        return "429" in error_str or "rate limit" in error_str.lower()


def get_error_message(error_obj) -> Optional[str]:
    """
    OpenAI Returns Error message that is nested, this extract the message

    Example:
    {
        'request': "<Request('POST', 'https://api.openai.com/v1/chat/completions')>",
        'message': "Error code: 400 - {\'error\': {\'message\': \"Invalid 'temperature': decimal above maximum value. Expected a value <= 2, but got 200 instead.\", 'type': 'invalid_request_error', 'param': 'temperature', 'code': 'decimal_above_max_value'}}",
        'body': {
            'message': "Invalid 'temperature': decimal above maximum value. Expected a value <= 2, but got 200 instead.",
            'type': 'invalid_request_error',
            'param': 'temperature',
            'code': 'decimal_above_max_value'
        },
        'code': 'decimal_above_max_value',
        'param': 'temperature',
        'type': 'invalid_request_error',
        'response': "<Response [400 Bad Request]>",
        'status_code': 400,
        'request_id': 'req_f287898caa6364cd42bc01355f74dd2a'
    }
    """
    try:
        # First, try to access the message directly from the 'body' key
        if error_obj is None:
            return None

        if hasattr(error_obj, "body"):
            _error_obj_body = getattr(error_obj, "body")
            if isinstance(_error_obj_body, dict):
                return _error_obj_body.get("message")

        # If all else fails, return None
        return None
    except Exception:
        return None


####### EXCEPTION MAPPING ################
def _get_response_headers(original_exception: Exception) -> Optional[httpx.Headers]:
    """
    Extract and return the response headers from an exception, if present.

    Used for accurate retry logic.
    """
    _response_headers: Optional[httpx.Headers] = None
    try:
        _response_headers = getattr(original_exception, "headers", None)
        error_response = getattr(original_exception, "response", None)
        if not _response_headers and error_response:
            _response_headers = getattr(error_response, "headers", None)
        if not _response_headers:
            _response_headers = getattr(
                original_exception, "litellm_response_headers", None
            )
    except Exception:
        return None

    return _response_headers


import re


def extract_and_raise_litellm_exception(
    response: Optional[Any],
    error_str: str,
    model: str,
    custom_llm_provider: str,
):
    """
    Covers scenario where litellm sdk calling proxy.

    Enables raising the special errors raised by litellm, eg. ContextWindowExceededError.

    Relevant Issue: https://github.com/BerriAI/litellm/issues/7259
    """
    pattern = r"litellm\.\w+Error"

    # Search for the exception in the error string
    match = re.search(pattern, error_str)

    # Extract the exception if found
    if match:
        exception_name = match.group(0)
        exception_name = exception_name.strip().replace("litellm.", "")
        raised_exception_obj = getattr(litellm, exception_name, None)
        if raised_exception_obj:
            raise raised_exception_obj(
                message=error_str,
                llm_provider=custom_llm_provider,
                model=model,
                response=response,
            )


def exception_type(  # type: ignore  # noqa: PLR0915
    model,
    original_exception,
    custom_llm_provider,
    completion_kwargs={},
    extra_kwargs={},
):
    """Maps an LLM Provider Exception to OpenAI Exception Format"""
    if any(
        isinstance(original_exception, exc_type)
        for exc_type in litellm.LITELLM_EXCEPTION_TYPES
    ):
        return original_exception
    exception_mapping_worked = False
    exception_provider = custom_llm_provider
    if litellm.suppress_debug_info is False:
        print()  # noqa
        print(  # noqa
            "\033[1;31mGive Feedback / Get Help: https://github.com/BerriAI/litellm/issues/new\033[0m"  # noqa
        )  # noqa
        print(  # noqa
            "LiteLLM.Info: If you need to debug this error, use `litellm._turn_on_debug()'."  # noqa
        )  # noqa
        print()  # noqa

    litellm_response_headers = _get_response_headers(
        original_exception=original_exception
    )
    try:
        error_str = str(original_exception)
        if model:
            if hasattr(original_exception, "message"):
                error_str = str(original_exception.message)
            if isinstance(original_exception, BaseException):
                exception_type = type(original_exception).__name__
            else:
                exception_type = ""

            ################################################################################
            # Common Extra information needed for all providers
            # We pass num retries, api_base, vertex_deployment etc to the exception here
            ################################################################################
            extra_information = ""
            try:
                _api_base = litellm.get_api_base(
                    model=model, optional_params=extra_kwargs
                )
                messages = litellm.get_first_chars_messages(kwargs=completion_kwargs)
                _vertex_project = extra_kwargs.get("vertex_project")
                _vertex_location = extra_kwargs.get("vertex_location")
                _metadata = extra_kwargs.get("metadata", {}) or {}
                _model_group = _metadata.get("model_group")
                _deployment = _metadata.get("deployment")
                extra_information = f"\nModel: {model}"

                if (
                    isinstance(custom_llm_provider, str)
                    and len(custom_llm_provider) > 0
                ):
                    exception_provider = (
                        custom_llm_provider[0].upper()
                        + custom_llm_provider[1:]
                        + "Exception"
                    )

                if _api_base:
                    extra_information += f"\nAPI Base: `{_api_base}`"
                if (
                    messages
                    and len(messages) > 0
                    and litellm.redact_messages_in_exceptions is False
                ):
                    extra_information += f"\nMessages: `{messages}`"

                if _model_group is not None:
                    extra_information += f"\nmodel_group: `{_model_group}`\n"
                if _deployment is not None:
                    extra_information += f"\ndeployment: `{_deployment}`\n"
                if _vertex_project is not None:
                    extra_information += f"\nvertex_project: `{_vertex_project}`\n"
                if _vertex_location is not None:
                    extra_information += f"\nvertex_location: `{_vertex_location}`\n"

                # on litellm proxy add key name + team to exceptions
                extra_information = _add_key_name_and_team_to_alert(
                    request_info=extra_information, metadata=_metadata
                )
            except Exception:
                # DO NOT LET this Block raising the original exception
                pass

            ################################################################################
            # End of Common Extra information Needed for all providers
            ################################################################################

            ################################################################################
            #################### Start of Provider Exception mapping ####################
            ################################################################################

            if (
                "Request Timeout Error" in error_str
                or "Request timed out" in error_str
                or "Timed out generating response" in error_str
                or "The read operation timed out" in error_str
            ):
                exception_mapping_worked = True

                raise Timeout(
                    message=f"APITimeoutError - Request timed out. Error_str: {error_str}",
                    model=model,
                    llm_provider=custom_llm_provider,
                    litellm_debug_info=extra_information,
                )

            if (
                custom_llm_provider == "litellm_proxy"
            ):  # handle special case where calling litellm proxy + exception str contains error message
                extract_and_raise_litellm_exception(
                    response=getattr(original_exception, "response", None),
                    error_str=error_str,
                    model=model,
                    custom_llm_provider=custom_llm_provider,
                )
            if (
                custom_llm_provider == "openai"
                or custom_llm_provider == "text-completion-openai"
                or custom_llm_provider == "custom_openai"
                or custom_llm_provider in litellm.openai_compatible_providers
            ):
                # custom_llm_provider is openai, make it OpenAI
                message = get_error_message(error_obj=original_exception)
                if message is None:
                    if hasattr(original_exception, "message"):
                        message = original_exception.message
                    else:
                        message = str(original_exception)

                if message is not None and isinstance(
                    message, str
                ):  # done to prevent user-confusion. Relevant issue - https://github.com/BerriAI/litellm/issues/1414
                    message = message.replace("OPENAI", custom_llm_provider.upper())
                    message = message.replace(
                        "openai.OpenAIError",
                        "{}.{}Error".format(custom_llm_provider, custom_llm_provider),
                    )
                if custom_llm_provider == "openai":
                    exception_provider = "OpenAI" + "Exception"
                else:
                    exception_provider = (
                        custom_llm_provider[0].upper()
                        + custom_llm_provider[1:]
                        + "Exception"
                    )

                if ExceptionCheckers.is_error_str_rate_limit(error_str):
                    exception_mapping_worked = True
                    raise RateLimitError(
                        message=f"RateLimitError: {exception_provider} - {message}",
                        model=model,
                        llm_provider=custom_llm_provider,
                        response=getattr(original_exception, "response", None),
                    )
                elif (
                    "This model's maximum context length is" in error_str
                    or "string too long. Expected a string with maximum length"
                    in error_str
                    or "model's maximum context limit" in error_str
                    or "is longer than the model's context length" in error_str
                ):
                    exception_mapping_worked = True
                    raise ContextWindowExceededError(
                        message=f"ContextWindowExceededError: {exception_provider} - {message}",
                        llm_provider=custom_llm_provider,
                        model=model,
                        response=getattr(original_exception, "response", None),
                        litellm_debug_info=extra_information,
                    )
                elif (
                    "invalid_request_error" in error_str
                    and "model_not_found" in error_str
                ):
                    exception_mapping_worked = True
                    raise NotFoundError(
                        message=f"{exception_provider} - {message}",
                        llm_provider=custom_llm_provider,
                        model=model,
                        response=getattr(original_exception, "response", None),
                        litellm_debug_info=extra_information,
                    )
                elif "A timeout occurred" in error_str:
                    exception_mapping_worked = True
                    raise Timeout(
                        message=f"{exception_provider} - {message}",
                        model=model,
                        llm_provider=custom_llm_provider,
                        litellm_debug_info=extra_information,
                    )
                elif (
                    (
                        "invalid_request_error" in error_str
                        and "content_policy_violation" in error_str
                    )
                    or (
                        "Invalid prompt" in error_str
                        and "violating our usage policy" in error_str
                    )
                    or (
                        "request was rejected as a result of the safety system"
                        in error_str.lower()
                    )
                ):
                    exception_mapping_worked = True
                    raise ContentPolicyViolationError(
                        message=f"ContentPolicyViolationError: {exception_provider} - {message}",
                        llm_provider=custom_llm_provider,
                        model=model,
                        response=getattr(original_exception, "response", None),
                        litellm_debug_info=extra_information,
                    )
                elif (
                    "invalid_request_error" in error_str
                    and "Incorrect API key provided" not in error_str
                ):
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"{exception_provider} - {message}",
                        llm_provider=custom_llm_provider,
                        model=model,
                        response=getattr(original_exception, "response", None),
                        litellm_debug_info=extra_information,
                        body=getattr(original_exception, "body", None),
                    )
                elif (
                    "Web server is returning an unknown error" in error_str
                    or "The server had an error processing your request." in error_str
                ):
                    exception_mapping_worked = True
                    raise litellm.InternalServerError(
                        message=f"{exception_provider} - {message}",
                        model=model,
                        llm_provider=custom_llm_provider,
                    )
                elif "Request too large" in error_str:
                    exception_mapping_worked = True
                    raise RateLimitError(
                        message=f"RateLimitError: {exception_provider} - {message}",
                        model=model,
                        llm_provider=custom_llm_provider,
                        response=getattr(original_exception, "response", None),
                        litellm_debug_info=extra_information,
                    )
                elif (
                    "The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable"
                    in error_str
                ):
                    exception_mapping_worked = True
                    raise AuthenticationError(
                        message=f"AuthenticationError: {exception_provider} - {message}",
                        llm_provider=custom_llm_provider,
                        model=model,
                        response=getattr(original_exception, "response", None),
                        litellm_debug_info=extra_information,
                    )
                elif "Mistral API raised a streaming error" in error_str:
                    exception_mapping_worked = True
                    _request = httpx.Request(
                        method="POST", url="https://api.openai.com/v1"
                    )
                    raise APIError(
                        status_code=500,
                        message=f"{exception_provider} - {message}",
                        llm_provider=custom_llm_provider,
                        model=model,
                        request=_request,
                        litellm_debug_info=extra_information,
                    )
                elif hasattr(original_exception, "status_code"):
                    exception_mapping_worked = True
                    if original_exception.status_code == 400:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"{exception_provider} - {message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 401:
                        exception_mapping_worked = True
                        raise AuthenticationError(
                            message=f"AuthenticationError: {exception_provider} - {message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 404:
                        exception_mapping_worked = True
                        raise NotFoundError(
                            message=f"NotFoundError: {exception_provider} - {message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 408:
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"Timeout Error: {exception_provider} - {message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 422:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"{exception_provider} - {message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                            body=getattr(original_exception, "body", None),
                        )
                    elif original_exception.status_code == 429:
                        exception_mapping_worked = True
                        raise RateLimitError(
                            message=f"RateLimitError: {exception_provider} - {message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 500:
                        exception_mapping_worked = True
                        raise InternalServerError(
                            message=f"InternalServerError: {exception_provider} - {message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 503:
                        exception_mapping_worked = True
                        raise ServiceUnavailableError(
                            message=f"ServiceUnavailableError: {exception_provider} - {message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 504:  # gateway timeout error
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"Timeout Error: {exception_provider} - {message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            litellm_debug_info=extra_information,
                            exception_status_code=original_exception.status_code,
                        )
                    else:
                        exception_mapping_worked = True
                        raise APIError(
                            status_code=original_exception.status_code,
                            message=f"APIError: {exception_provider} - {message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                            request=getattr(original_exception, "request", None),
                            litellm_debug_info=extra_information,
                        )
                else:
                    # if no status code then it is an APIConnectionError: https://github.com/openai/openai-python#handling-errors
                    # exception_mapping_worked = True
                    raise APIConnectionError(
                        message=f"APIConnectionError: {exception_provider} - {message}",
                        llm_provider=custom_llm_provider,
                        model=model,
                        litellm_debug_info=extra_information,
                        request=httpx.Request(
                            method="POST", url="https://api.openai.com/v1/"
                        ),
                    )
            elif (
                custom_llm_provider == "anthropic"
                or custom_llm_provider == "anthropic_text"
            ):  # one of the anthropics
                if "prompt is too long" in error_str or "prompt: length" in error_str:
                    exception_mapping_worked = True
                    raise ContextWindowExceededError(
                        message="AnthropicError - {}".format(error_str),
                        model=model,
                        llm_provider="anthropic",
                    )
                elif "overloaded_error" in error_str:
                    exception_mapping_worked = True
                    raise InternalServerError(
                        message="AnthropicError - {}".format(error_str),
                        model=model,
                        llm_provider="anthropic",
                    )
                if "Invalid API Key" in error_str:
                    exception_mapping_worked = True
                    raise AuthenticationError(
                        message="AnthropicError - {}".format(error_str),
                        model=model,
                        llm_provider="anthropic",
                    )
                if "content filtering policy" in error_str:
                    exception_mapping_worked = True
                    raise ContentPolicyViolationError(
                        message="AnthropicError - {}".format(error_str),
                        model=model,
                        llm_provider="anthropic",
                    )
                if "Client error '400 Bad Request'" in error_str:
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message="AnthropicError - {}".format(error_str),
                        model=model,
                        llm_provider="anthropic",
                    )
                if hasattr(original_exception, "status_code"):
                    verbose_logger.debug(
                        f"status_code: {original_exception.status_code}"
                    )
                    if original_exception.status_code == 401:
                        exception_mapping_worked = True
                        raise AuthenticationError(
                            message=f"AnthropicException - {error_str}",
                            llm_provider="anthropic",
                            model=model,
                        )
                    elif (
                        original_exception.status_code == 400
                        or original_exception.status_code == 413
                    ):
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"AnthropicException - {error_str}",
                            model=model,
                            llm_provider="anthropic",
                        )
                    elif original_exception.status_code == 404:
                        exception_mapping_worked = True
                        raise NotFoundError(
                            message=f"AnthropicException - {error_str}",
                            model=model,
                            llm_provider="anthropic",
                        )
                    elif original_exception.status_code == 408:
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"AnthropicException - {error_str}",
                            model=model,
                            llm_provider="anthropic",
                        )
                    elif original_exception.status_code == 429:
                        exception_mapping_worked = True
                        raise RateLimitError(
                            message=f"AnthropicException - {error_str}",
                            llm_provider="anthropic",
                            model=model,
                        )
                    elif (
                        original_exception.status_code == 500
                        or original_exception.status_code == 529
                    ):
                        exception_mapping_worked = True
                        raise litellm.InternalServerError(
                            message=f"AnthropicException - {error_str}. Handle with `litellm.InternalServerError`.",
                            llm_provider="anthropic",
                            model=model,
                        )
                    elif original_exception.status_code == 503:
                        exception_mapping_worked = True
                        raise litellm.ServiceUnavailableError(
                            message=f"AnthropicException - {error_str}. Handle with `litellm.ServiceUnavailableError`.",
                            llm_provider="anthropic",
                            model=model,
                        )
            elif custom_llm_provider == "replicate":
                if "Incorrect authentication token" in error_str:
                    exception_mapping_worked = True
                    raise AuthenticationError(
                        message=f"ReplicateException - {error_str}",
                        llm_provider="replicate",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                elif "input is too long" in error_str:
                    exception_mapping_worked = True
                    raise ContextWindowExceededError(
                        message=f"ReplicateException - {error_str}",
                        model=model,
                        llm_provider="replicate",
                        response=getattr(original_exception, "response", None),
                    )
                elif exception_type == "ModelError":
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"ReplicateException - {error_str}",
                        model=model,
                        llm_provider="replicate",
                        response=getattr(original_exception, "response", None),
                    )
                elif "Request was throttled" in error_str:
                    exception_mapping_worked = True
                    raise RateLimitError(
                        message=f"ReplicateException - {error_str}",
                        llm_provider="replicate",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                elif hasattr(original_exception, "status_code"):
                    if original_exception.status_code == 401:
                        exception_mapping_worked = True
                        raise AuthenticationError(
                            message=f"ReplicateException - {original_exception.message}",
                            llm_provider="replicate",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif (
                        original_exception.status_code == 400
                        or original_exception.status_code == 413
                    ):
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"ReplicateException - {original_exception.message}",
                            model=model,
                            llm_provider="replicate",
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 422:
                        exception_mapping_worked = True
                        raise UnprocessableEntityError(
                            message=f"ReplicateException - {original_exception.message}",
                            model=model,
                            llm_provider="replicate",
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 408:
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"ReplicateException - {original_exception.message}",
                            model=model,
                            llm_provider="replicate",
                        )
                    elif original_exception.status_code == 422:
                        exception_mapping_worked = True
                        raise UnprocessableEntityError(
                            message=f"ReplicateException - {original_exception.message}",
                            llm_provider="replicate",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 429:
                        exception_mapping_worked = True
                        raise RateLimitError(
                            message=f"ReplicateException - {original_exception.message}",
                            llm_provider="replicate",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 500:
                        exception_mapping_worked = True
                        raise ServiceUnavailableError(
                            message=f"ReplicateException - {original_exception.message}",
                            llm_provider="replicate",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                exception_mapping_worked = True
                raise APIError(
                    status_code=500,
                    message=f"ReplicateException - {str(original_exception)}",
                    llm_provider="replicate",
                    model=model,
                    request=httpx.Request(
                        method="POST",
                        url="https://api.replicate.com/v1/deployments",
                    ),
                )
            elif custom_llm_provider in litellm._openai_like_providers:
                if "authorization denied for" in error_str:
                    exception_mapping_worked = True

                    # Predibase returns the raw API Key in the response - this block ensures it's not returned in the exception
                    if (
                        error_str is not None
                        and isinstance(error_str, str)
                        and "bearer" in error_str.lower()
                    ):
                        # only keep the first 10 chars after the occurnence of "bearer"
                        _bearer_token_start_index = error_str.lower().find("bearer")
                        error_str = error_str[: _bearer_token_start_index + 14]
                        error_str += "XXXXXXX" + '"'

                    raise AuthenticationError(
                        message=f"{custom_llm_provider}Exception: Authentication Error - {error_str}",
                        llm_provider=custom_llm_provider,
                        model=model,
                        response=getattr(original_exception, "response", None),
                        litellm_debug_info=extra_information,
                    )
                elif "model's maximum context limit" in error_str:
                    exception_mapping_worked = True
                    raise ContextWindowExceededError(
                        message=f"{custom_llm_provider}Exception: Context Window Error - {error_str}",
                        model=model,
                        llm_provider=custom_llm_provider,
                    )
                elif "token_quota_reached" in error_str:
                    exception_mapping_worked = True
                    raise RateLimitError(
                        message=f"{custom_llm_provider}Exception: Rate Limit Errror - {error_str}",
                        llm_provider=custom_llm_provider,
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                elif (
                    "The server received an invalid response from an upstream server."
                    in error_str
                ):
                    exception_mapping_worked = True
                    raise litellm.InternalServerError(
                        message=f"{custom_llm_provider}Exception - {original_exception.message}",
                        llm_provider=custom_llm_provider,
                        model=model,
                    )
                elif "model_no_support_for_function" in error_str:
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"{custom_llm_provider}Exception - Use 'watsonx_text' route instead. IBM WatsonX does not support `/text/chat` endpoint. - {error_str}",
                        llm_provider=custom_llm_provider,
                        model=model,
                    )
                elif hasattr(original_exception, "status_code"):
                    if original_exception.status_code == 500:
                        exception_mapping_worked = True
                        raise litellm.InternalServerError(
                            message=f"{custom_llm_provider}Exception - {original_exception.message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                        )
                    elif (
                        original_exception.status_code == 401
                        or original_exception.status_code == 403
                    ):
                        exception_mapping_worked = True
                        raise AuthenticationError(
                            message=f"{custom_llm_provider}Exception - {original_exception.message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                        )
                    elif original_exception.status_code == 400:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"{custom_llm_provider}Exception - {original_exception.message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                        )
                    elif original_exception.status_code == 404:
                        exception_mapping_worked = True
                        raise NotFoundError(
                            message=f"{custom_llm_provider}Exception - {original_exception.message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                        )
                    elif original_exception.status_code == 408:
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"{custom_llm_provider}Exception - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            litellm_debug_info=extra_information,
                        )
                    elif (
                        original_exception.status_code == 422
                        or original_exception.status_code == 424
                    ):
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"{custom_llm_provider}Exception - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 429:
                        exception_mapping_worked = True
                        raise RateLimitError(
                            message=f"{custom_llm_provider}Exception - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 503:
                        exception_mapping_worked = True
                        raise ServiceUnavailableError(
                            message=f"{custom_llm_provider}Exception - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 504:  # gateway timeout error
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"{custom_llm_provider}Exception - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            litellm_debug_info=extra_information,
                            exception_status_code=original_exception.status_code,
                        )
            elif custom_llm_provider == "bedrock":
                if (
                    "too many tokens" in error_str
                    or "expected maxLength:" in error_str
                    or "Input is too long" in error_str
                    or "prompt is too long" in error_str
                    or "prompt: length: 1.." in error_str
                    or "Too many input tokens" in error_str
                ):
                    exception_mapping_worked = True
                    raise ContextWindowExceededError(
                        message=f"BedrockException: Context Window Error - {error_str}",
                        model=model,
                        llm_provider="bedrock",
                    )
                elif (
                    "Conversation blocks and tool result blocks cannot be provided in the same turn."
                    in error_str
                ):
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"BedrockException - {error_str}\n. Enable 'litellm.modify_params=True' (for PROXY do: `litellm_settings::modify_params: True`) to insert a dummy assistant message and fix this error.",
                        model=model,
                        llm_provider="bedrock",
                        response=getattr(original_exception, "response", None),
                    )
                elif "Malformed input request" in error_str:
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"BedrockException - {error_str}",
                        model=model,
                        llm_provider="bedrock",
                        response=getattr(original_exception, "response", None),
                    )
                elif "A conversation must start with a user message." in error_str:
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"BedrockException - {error_str}\n. Pass in default user message via `completion(..,user_continue_message=)` or enable `litellm.modify_params=True`.\nFor Proxy: do via `litellm_settings::modify_params: True` or user_continue_message under `litellm_params`",
                        model=model,
                        llm_provider="bedrock",
                        response=getattr(original_exception, "response", None),
                    )
                elif (
                    "Unable to locate credentials" in error_str
                    or "The security token included in the request is invalid"
                    in error_str
                ):
                    exception_mapping_worked = True
                    raise AuthenticationError(
                        message=f"BedrockException Invalid Authentication - {error_str}",
                        model=model,
                        llm_provider="bedrock",
                        response=getattr(original_exception, "response", None),
                    )
                elif "AccessDeniedException" in error_str:
                    exception_mapping_worked = True
                    raise PermissionDeniedError(
                        message=f"BedrockException PermissionDeniedError - {error_str}",
                        model=model,
                        llm_provider="bedrock",
                        response=getattr(original_exception, "response", None),
                    )
                elif (
                    "throttlingException" in error_str
                    or "ThrottlingException" in error_str
                ):
                    exception_mapping_worked = True
                    raise RateLimitError(
                        message=f"BedrockException: Rate Limit Error - {error_str}",
                        model=model,
                        llm_provider="bedrock",
                        response=getattr(original_exception, "response", None),
                    )
                elif (
                    "Connect timeout on endpoint URL" in error_str
                    or "timed out" in error_str
                ):
                    exception_mapping_worked = True
                    raise Timeout(
                        message=f"BedrockException: Timeout Error - {error_str}",
                        model=model,
                        llm_provider="bedrock",
                    )
                elif "Could not process image" in error_str:
                    exception_mapping_worked = True
                    raise litellm.InternalServerError(
                        message=f"BedrockException - {error_str}",
                        model=model,
                        llm_provider="bedrock",
                    )
                elif hasattr(original_exception, "status_code"):
                    if original_exception.status_code == 500:
                        exception_mapping_worked = True
                        raise ServiceUnavailableError(
                            message=f"BedrockException - {original_exception.message}",
                            llm_provider="bedrock",
                            model=model,
                            response=httpx.Response(
                                status_code=500,
                                request=httpx.Request(
                                    method="POST", url="https://api.openai.com/v1/"
                                ),
                            ),
                        )
                    elif original_exception.status_code == 401:
                        exception_mapping_worked = True
                        raise AuthenticationError(
                            message=f"BedrockException - {original_exception.message}",
                            llm_provider="bedrock",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 400:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"BedrockException - {original_exception.message}",
                            llm_provider="bedrock",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 404:
                        exception_mapping_worked = True
                        raise NotFoundError(
                            message=f"BedrockException - {original_exception.message}",
                            llm_provider="bedrock",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 408:
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"BedrockException - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 422:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"BedrockException - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 429:
                        exception_mapping_worked = True
                        raise RateLimitError(
                            message=f"BedrockException - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 503:
                        exception_mapping_worked = True
                        raise ServiceUnavailableError(
                            message=f"BedrockException - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 504:  # gateway timeout error
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"BedrockException - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            litellm_debug_info=extra_information,
                            exception_status_code=original_exception.status_code,
                        )
            elif (
                custom_llm_provider == "sagemaker"
                or custom_llm_provider == "sagemaker_chat"
            ):
                if "Unable to locate credentials" in error_str:
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"litellm.BadRequestError: SagemakerException - {error_str}",
                        model=model,
                        llm_provider="sagemaker",
                        response=getattr(original_exception, "response", None),
                    )
                elif (
                    "Input validation error: `best_of` must be > 0 and <= 2"
                    in error_str
                ):
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message="SagemakerException - the value of 'n' must be > 0 and <= 2 for sagemaker endpoints",
                        model=model,
                        llm_provider="sagemaker",
                        response=getattr(original_exception, "response", None),
                    )
                elif (
                    "`inputs` tokens + `max_new_tokens` must be <=" in error_str
                    or "instance type with more CPU capacity or memory" in error_str
                ):
                    exception_mapping_worked = True
                    raise ContextWindowExceededError(
                        message=f"SagemakerException - {error_str}",
                        model=model,
                        llm_provider="sagemaker",
                        response=getattr(original_exception, "response", None),
                    )
                elif hasattr(original_exception, "status_code"):
                    if original_exception.status_code == 500:
                        exception_mapping_worked = True
                        raise ServiceUnavailableError(
                            message=f"SagemakerException - {original_exception.message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                            response=httpx.Response(
                                status_code=500,
                                request=httpx.Request(
                                    method="POST", url="https://api.openai.com/v1/"
                                ),
                            ),
                        )
                    elif original_exception.status_code == 401:
                        exception_mapping_worked = True
                        raise AuthenticationError(
                            message=f"SagemakerException - {original_exception.message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 400:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"SagemakerException - {original_exception.message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 404:
                        exception_mapping_worked = True
                        raise NotFoundError(
                            message=f"SagemakerException - {original_exception.message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 408:
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"SagemakerException - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            litellm_debug_info=extra_information,
                        )
                    elif (
                        original_exception.status_code == 422
                        or original_exception.status_code == 424
                    ):
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"SagemakerException - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 429:
                        exception_mapping_worked = True
                        raise RateLimitError(
                            message=f"SagemakerException - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 503:
                        exception_mapping_worked = True
                        raise ServiceUnavailableError(
                            message=f"SagemakerException - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 504:  # gateway timeout error
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"SagemakerException - {original_exception.message}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            litellm_debug_info=extra_information,
                            exception_status_code=original_exception.status_code,
                        )
            elif (
                custom_llm_provider == "vertex_ai"
                or custom_llm_provider == "vertex_ai_beta"
                or custom_llm_provider == "gemini"
            ):
                if (
                    "Vertex AI API has not been used in project" in error_str
                    or "Unable to find your project" in error_str
                ):
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"litellm.BadRequestError: VertexAIException - {error_str}",
                        model=model,
                        llm_provider="vertex_ai",
                        response=httpx.Response(
                            status_code=400,
                            request=httpx.Request(
                                method="POST",
                                url=" https://cloud.google.com/vertex-ai/",
                            ),
                        ),
                        litellm_debug_info=extra_information,
                    )
                if "400 Request payload size exceeds" in error_str:
                    exception_mapping_worked = True
                    raise ContextWindowExceededError(
                        message=f"VertexException - {error_str}",
                        model=model,
                        llm_provider=custom_llm_provider,
                    )
                elif (
                    "None Unknown Error." in error_str
                    or "Content has no parts." in error_str
                ):
                    exception_mapping_worked = True
                    raise litellm.InternalServerError(
                        message=f"litellm.InternalServerError: VertexAIException - {error_str}",
                        model=model,
                        llm_provider="vertex_ai",
                        response=httpx.Response(
                            status_code=500,
                            content=str(original_exception),
                            request=httpx.Request(method="completion", url="https://github.com/BerriAI/litellm"),  # type: ignore
                        ),
                        litellm_debug_info=extra_information,
                    )
                elif "API key not valid." in error_str:
                    exception_mapping_worked = True
                    raise AuthenticationError(
                        message=f"{custom_llm_provider}Exception - {error_str}",
                        model=model,
                        llm_provider=custom_llm_provider,
                        litellm_debug_info=extra_information,
                    )
                elif "403" in error_str:
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"VertexAIException BadRequestError - {error_str}",
                        model=model,
                        llm_provider="vertex_ai",
                        response=httpx.Response(
                            status_code=403,
                            request=httpx.Request(
                                method="POST",
                                url=" https://cloud.google.com/vertex-ai/",
                            ),
                        ),
                        litellm_debug_info=extra_information,
                    )
                elif (
                    "The response was blocked." in error_str
                    or "Output blocked by content filtering policy"
                    in error_str  # anthropic on vertex ai
                ):
                    exception_mapping_worked = True
                    raise ContentPolicyViolationError(
                        message=f"VertexAIException ContentPolicyViolationError - {error_str}",
                        model=model,
                        llm_provider="vertex_ai",
                        litellm_debug_info=extra_information,
                        response=httpx.Response(
                            status_code=400,
                            request=httpx.Request(
                                method="POST",
                                url=" https://cloud.google.com/vertex-ai/",
                            ),
                        ),
                    )
                elif (
                    "429 Quota exceeded" in error_str
                    or "Quota exceeded for" in error_str
                    or "IndexError: list index out of range" in error_str
                    or "429 Unable to submit request because the service is temporarily out of capacity."
                    in error_str
                ):
                    exception_mapping_worked = True
                    raise RateLimitError(
                        message=f"litellm.RateLimitError: VertexAIException - {error_str}",
                        model=model,
                        llm_provider="vertex_ai",
                        litellm_debug_info=extra_information,
                        response=httpx.Response(
                            status_code=429,
                            request=httpx.Request(
                                method="POST",
                                url=" https://cloud.google.com/vertex-ai/",
                            ),
                        ),
                    )
                elif (
                    "500 Internal Server Error" in error_str
                    or "The model is overloaded." in error_str
                ):
                    exception_mapping_worked = True
                    raise litellm.InternalServerError(
                        message=f"litellm.InternalServerError: VertexAIException - {error_str}",
                        model=model,
                        llm_provider="vertex_ai",
                        litellm_debug_info=extra_information,
                    )
                if hasattr(original_exception, "status_code"):
                    if original_exception.status_code == 400:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"VertexAIException BadRequestError - {error_str}",
                            model=model,
                            llm_provider="vertex_ai",
                            litellm_debug_info=extra_information,
                            response=httpx.Response(
                                status_code=400,
                                request=httpx.Request(
                                    method="POST",
                                    url="https://cloud.google.com/vertex-ai/",
                                ),
                            ),
                        )
                    if original_exception.status_code == 401:
                        exception_mapping_worked = True
                        raise AuthenticationError(
                            message=f"VertexAIException - {original_exception.message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                        )
                    if original_exception.status_code == 404:
                        exception_mapping_worked = True
                        raise NotFoundError(
                            message=f"VertexAIException - {original_exception.message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                        )
                    if original_exception.status_code == 408:
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"VertexAIException - {original_exception.message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                        )

                    if original_exception.status_code == 429:
                        exception_mapping_worked = True
                        raise RateLimitError(
                            message=f"litellm.RateLimitError: VertexAIException - {error_str}",
                            model=model,
                            llm_provider="vertex_ai",
                            litellm_debug_info=extra_information,
                            response=httpx.Response(
                                status_code=429,
                                request=httpx.Request(
                                    method="POST",
                                    url=" https://cloud.google.com/vertex-ai/",
                                ),
                            ),
                        )
                    if original_exception.status_code == 500:
                        exception_mapping_worked = True
                        raise litellm.InternalServerError(
                            message=f"VertexAIException InternalServerError - {error_str}",
                            model=model,
                            llm_provider="vertex_ai",
                            litellm_debug_info=extra_information,
                            response=httpx.Response(
                                status_code=500,
                                content=str(original_exception),
                                request=httpx.Request(method="completion", url="https://github.com/BerriAI/litellm"),  # type: ignore
                            ),
                        )
                    if original_exception.status_code == 503:
                        exception_mapping_worked = True
                        raise ServiceUnavailableError(
                            message=f"VertexAIException - {original_exception.message}",
                            llm_provider=custom_llm_provider,
                            model=model,
                        )
            elif custom_llm_provider == "palm" or custom_llm_provider == "gemini":
                if "503 Getting metadata" in error_str:
                    # auth errors look like this
                    # 503 Getting metadata from plugin failed with error: Reauthentication is needed. Please run `gcloud auth application-default login` to reauthenticate.
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message="GeminiException - Invalid api key",
                        model=model,
                        llm_provider="palm",
                        response=getattr(original_exception, "response", None),
                    )
                if (
                    "504 Deadline expired before operation could complete." in error_str
                    or "504 Deadline Exceeded" in error_str
                ):
                    exception_mapping_worked = True
                    raise Timeout(
                        message=f"GeminiException - {original_exception.message}",
                        model=model,
                        llm_provider="palm",
                        exception_status_code=original_exception.status_code,
                    )
                if "400 Request payload size exceeds" in error_str:
                    exception_mapping_worked = True
                    raise ContextWindowExceededError(
                        message=f"GeminiException - {error_str}",
                        model=model,
                        llm_provider="palm",
                        response=getattr(original_exception, "response", None),
                    )
                if (
                    "500 An internal error has occurred." in error_str
                    or "list index out of range" in error_str
                ):
                    exception_mapping_worked = True
                    raise APIError(
                        status_code=getattr(original_exception, "status_code", 500),
                        message=f"GeminiException - {original_exception.message}",
                        llm_provider="palm",
                        model=model,
                        request=httpx.Response(
                            status_code=429,
                            request=httpx.Request(
                                method="POST",
                                url=" https://cloud.google.com/vertex-ai/",
                            ),
                        ),
                    )
                if hasattr(original_exception, "status_code"):
                    if original_exception.status_code == 400:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"GeminiException - {error_str}",
                            model=model,
                            llm_provider="palm",
                            response=getattr(original_exception, "response", None),
                        )
                # Dailed: Error occurred: 400 Request payload size exceeds the limit: 20000 bytes
            elif custom_llm_provider == "cloudflare":
                if "Authentication error" in error_str:
                    exception_mapping_worked = True
                    raise AuthenticationError(
                        message=f"Cloudflare Exception - {original_exception.message}",
                        llm_provider="cloudflare",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                if "must have required property" in error_str:
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"Cloudflare Exception - {original_exception.message}",
                        llm_provider="cloudflare",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
            elif (
                custom_llm_provider == "cohere" or custom_llm_provider == "cohere_chat"
            ):  # Cohere
                if (
                    "invalid api token" in error_str
                    or "No API key provided." in error_str
                ):
                    exception_mapping_worked = True
                    raise AuthenticationError(
                        message=f"CohereException - {original_exception.message}",
                        llm_provider="cohere",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                elif "too many tokens" in error_str:
                    exception_mapping_worked = True
                    raise ContextWindowExceededError(
                        message=f"CohereException - {original_exception.message}",
                        model=model,
                        llm_provider="cohere",
                        response=getattr(original_exception, "response", None),
                    )
                elif hasattr(original_exception, "status_code"):
                    if (
                        original_exception.status_code == 400
                        or original_exception.status_code == 498
                    ):
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"CohereException - {original_exception.message}",
                            llm_provider="cohere",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 408:
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"CohereException - {original_exception.message}",
                            llm_provider="cohere",
                            model=model,
                        )
                    elif original_exception.status_code == 500:
                        exception_mapping_worked = True
                        raise ServiceUnavailableError(
                            message=f"CohereException - {original_exception.message}",
                            llm_provider="cohere",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                elif (
                    "CohereConnectionError" in exception_type
                ):  # cohere seems to fire these errors when we load test it (1k+ messages / min)
                    exception_mapping_worked = True
                    raise RateLimitError(
                        message=f"CohereException - {original_exception.message}",
                        llm_provider="cohere",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                elif "invalid type:" in error_str:
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"CohereException - {original_exception.message}",
                        llm_provider="cohere",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                elif "Unexpected server error" in error_str:
                    exception_mapping_worked = True
                    raise ServiceUnavailableError(
                        message=f"CohereException - {original_exception.message}",
                        llm_provider="cohere",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                else:
                    if hasattr(original_exception, "status_code"):
                        exception_mapping_worked = True
                        raise APIError(
                            status_code=original_exception.status_code,
                            message=f"CohereException - {original_exception.message}",
                            llm_provider="cohere",
                            model=model,
                            request=original_exception.request,
                        )
                    raise original_exception
            elif custom_llm_provider == "huggingface":
                if "length limit exceeded" in error_str:
                    exception_mapping_worked = True
                    raise ContextWindowExceededError(
                        message=error_str,
                        model=model,
                        llm_provider="huggingface",
                        response=getattr(original_exception, "response", None),
                    )
                elif "A valid user token is required" in error_str:
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=error_str,
                        llm_provider="huggingface",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                elif "Rate limit reached" in error_str:
                    exception_mapping_worked = True
                    raise RateLimitError(
                        message=error_str,
                        llm_provider="huggingface",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                if hasattr(original_exception, "status_code"):
                    if original_exception.status_code == 401:
                        exception_mapping_worked = True
                        raise AuthenticationError(
                            message=f"HuggingfaceException - {original_exception.message}",
                            llm_provider="huggingface",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 400:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"HuggingfaceException - {original_exception.message}",
                            model=model,
                            llm_provider="huggingface",
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 408:
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"HuggingfaceException - {original_exception.message}",
                            model=model,
                            llm_provider="huggingface",
                        )
                    elif original_exception.status_code == 429:
                        exception_mapping_worked = True
                        raise RateLimitError(
                            message=f"HuggingfaceException - {original_exception.message}",
                            llm_provider="huggingface",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 503:
                        exception_mapping_worked = True
                        raise ServiceUnavailableError(
                            message=f"HuggingfaceException - {original_exception.message}",
                            llm_provider="huggingface",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    else:
                        exception_mapping_worked = True
                        raise APIError(
                            status_code=original_exception.status_code,
                            message=f"HuggingfaceException - {original_exception.message}",
                            llm_provider="huggingface",
                            model=model,
                            request=original_exception.request,
                        )
            elif custom_llm_provider == "ai21":
                if hasattr(original_exception, "message"):
                    if "Prompt has too many tokens" in original_exception.message:
                        exception_mapping_worked = True
                        raise ContextWindowExceededError(
                            message=f"AI21Exception - {original_exception.message}",
                            model=model,
                            llm_provider="ai21",
                            response=getattr(original_exception, "response", None),
                        )
                    if "Bad or missing API token." in original_exception.message:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"AI21Exception - {original_exception.message}",
                            model=model,
                            llm_provider="ai21",
                            response=getattr(original_exception, "response", None),
                        )
                if hasattr(original_exception, "status_code"):
                    if original_exception.status_code == 401:
                        exception_mapping_worked = True
                        raise AuthenticationError(
                            message=f"AI21Exception - {original_exception.message}",
                            llm_provider="ai21",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 408:
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"AI21Exception - {original_exception.message}",
                            model=model,
                            llm_provider="ai21",
                        )
                    if original_exception.status_code == 422:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"AI21Exception - {original_exception.message}",
                            model=model,
                            llm_provider="ai21",
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 429:
                        exception_mapping_worked = True
                        raise RateLimitError(
                            message=f"AI21Exception - {original_exception.message}",
                            llm_provider="ai21",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    else:
                        exception_mapping_worked = True
                        raise APIError(
                            status_code=original_exception.status_code,
                            message=f"AI21Exception - {original_exception.message}",
                            llm_provider="ai21",
                            model=model,
                            request=original_exception.request,
                        )
            elif custom_llm_provider == "nlp_cloud":
                if "detail" in error_str:
                    if "Input text length should not exceed" in error_str:
                        exception_mapping_worked = True
                        raise ContextWindowExceededError(
                            message=f"NLPCloudException - {error_str}",
                            model=model,
                            llm_provider="nlp_cloud",
                            response=getattr(original_exception, "response", None),
                        )
                    elif "value is not a valid" in error_str:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"NLPCloudException - {error_str}",
                            model=model,
                            llm_provider="nlp_cloud",
                            response=getattr(original_exception, "response", None),
                        )
                    else:
                        exception_mapping_worked = True
                        raise APIError(
                            status_code=500,
                            message=f"NLPCloudException - {error_str}",
                            model=model,
                            llm_provider="nlp_cloud",
                            request=original_exception.request,
                        )
                if hasattr(
                    original_exception, "status_code"
                ):  # https://docs.nlpcloud.com/?shell#errors
                    if (
                        original_exception.status_code == 400
                        or original_exception.status_code == 406
                        or original_exception.status_code == 413
                        or original_exception.status_code == 422
                    ):
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"NLPCloudException - {original_exception.message}",
                            llm_provider="nlp_cloud",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif (
                        original_exception.status_code == 401
                        or original_exception.status_code == 403
                    ):
                        exception_mapping_worked = True
                        raise AuthenticationError(
                            message=f"NLPCloudException - {original_exception.message}",
                            llm_provider="nlp_cloud",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif (
                        original_exception.status_code == 522
                        or original_exception.status_code == 524
                    ):
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"NLPCloudException - {original_exception.message}",
                            model=model,
                            llm_provider="nlp_cloud",
                        )
                    elif (
                        original_exception.status_code == 429
                        or original_exception.status_code == 402
                    ):
                        exception_mapping_worked = True
                        raise RateLimitError(
                            message=f"NLPCloudException - {original_exception.message}",
                            llm_provider="nlp_cloud",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif (
                        original_exception.status_code == 500
                        or original_exception.status_code == 503
                    ):
                        exception_mapping_worked = True
                        raise APIError(
                            status_code=original_exception.status_code,
                            message=f"NLPCloudException - {original_exception.message}",
                            llm_provider="nlp_cloud",
                            model=model,
                            request=original_exception.request,
                        )
                    elif (
                        original_exception.status_code == 504
                        or original_exception.status_code == 520
                    ):
                        exception_mapping_worked = True
                        raise ServiceUnavailableError(
                            message=f"NLPCloudException - {original_exception.message}",
                            model=model,
                            llm_provider="nlp_cloud",
                            response=getattr(original_exception, "response", None),
                        )
                    else:
                        exception_mapping_worked = True
                        raise APIError(
                            status_code=original_exception.status_code,
                            message=f"NLPCloudException - {original_exception.message}",
                            llm_provider="nlp_cloud",
                            model=model,
                            request=original_exception.request,
                        )
            elif custom_llm_provider == "together_ai":
                try:
                    error_response = json.loads(error_str)
                except Exception:
                    error_response = {"error": error_str}
                if (
                    "error" in error_response
                    and "`inputs` tokens + `max_new_tokens` must be <="
                    in error_response["error"]
                ):
                    exception_mapping_worked = True
                    raise ContextWindowExceededError(
                        message=f"TogetherAIException - {error_response['error']}",
                        model=model,
                        llm_provider="together_ai",
                        response=getattr(original_exception, "response", None),
                    )
                elif (
                    "error" in error_response
                    and "invalid private key" in error_response["error"]
                ):
                    exception_mapping_worked = True
                    raise AuthenticationError(
                        message=f"TogetherAIException - {error_response['error']}",
                        llm_provider="together_ai",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                elif (
                    "error" in error_response
                    and "INVALID_ARGUMENT" in error_response["error"]
                ):
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"TogetherAIException - {error_response['error']}",
                        model=model,
                        llm_provider="together_ai",
                        response=getattr(original_exception, "response", None),
                    )
                elif "A timeout occurred" in error_str:
                    exception_mapping_worked = True
                    raise Timeout(
                        message=f"TogetherAIException - {error_str}",
                        model=model,
                        llm_provider="together_ai",
                    )
                elif (
                    "error" in error_response
                    and "API key doesn't match expected format."
                    in error_response["error"]
                ):
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"TogetherAIException - {error_response['error']}",
                        model=model,
                        llm_provider="together_ai",
                        response=getattr(original_exception, "response", None),
                    )
                elif (
                    "error_type" in error_response
                    and error_response["error_type"] == "validation"
                ):
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"TogetherAIException - {error_response['error']}",
                        model=model,
                        llm_provider="together_ai",
                        response=getattr(original_exception, "response", None),
                    )
                if hasattr(original_exception, "status_code"):
                    if original_exception.status_code == 408:
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"TogetherAIException - {original_exception.message}",
                            model=model,
                            llm_provider="together_ai",
                        )
                    elif original_exception.status_code == 422:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"TogetherAIException - {error_response['error']}",
                            model=model,
                            llm_provider="together_ai",
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 429:
                        exception_mapping_worked = True
                        raise RateLimitError(
                            message=f"TogetherAIException - {original_exception.message}",
                            llm_provider="together_ai",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 524:
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"TogetherAIException - {original_exception.message}",
                            llm_provider="together_ai",
                            model=model,
                        )
                else:
                    exception_mapping_worked = True
                    raise APIError(
                        status_code=original_exception.status_code,
                        message=f"TogetherAIException - {original_exception.message}",
                        llm_provider="together_ai",
                        model=model,
                        request=original_exception.request,
                    )
            elif custom_llm_provider == "aleph_alpha":
                if (
                    "This is longer than the model's maximum context length"
                    in error_str
                ):
                    exception_mapping_worked = True
                    raise ContextWindowExceededError(
                        message=f"AlephAlphaException - {original_exception.message}",
                        llm_provider="aleph_alpha",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                elif "InvalidToken" in error_str or "No token provided" in error_str:
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"AlephAlphaException - {original_exception.message}",
                        llm_provider="aleph_alpha",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                elif hasattr(original_exception, "status_code"):
                    verbose_logger.debug(
                        f"status code: {original_exception.status_code}"
                    )
                    if original_exception.status_code == 401:
                        exception_mapping_worked = True
                        raise AuthenticationError(
                            message=f"AlephAlphaException - {original_exception.message}",
                            llm_provider="aleph_alpha",
                            model=model,
                        )
                    elif original_exception.status_code == 400:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"AlephAlphaException - {original_exception.message}",
                            llm_provider="aleph_alpha",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 429:
                        exception_mapping_worked = True
                        raise RateLimitError(
                            message=f"AlephAlphaException - {original_exception.message}",
                            llm_provider="aleph_alpha",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 500:
                        exception_mapping_worked = True
                        raise ServiceUnavailableError(
                            message=f"AlephAlphaException - {original_exception.message}",
                            llm_provider="aleph_alpha",
                            model=model,
                            response=getattr(original_exception, "response", None),
                        )
                    raise original_exception
                raise original_exception
            elif (
                custom_llm_provider == "ollama" or custom_llm_provider == "ollama_chat"
            ):
                if isinstance(original_exception, dict):
                    error_str = original_exception.get("error", "")
                else:
                    error_str = str(original_exception)
                if "no such file or directory" in error_str:
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"OllamaException: Invalid Model/Model not loaded - {original_exception}",
                        model=model,
                        llm_provider="ollama",
                        response=getattr(original_exception, "response", None),
                    )
                elif "Failed to establish a new connection" in error_str:
                    exception_mapping_worked = True
                    raise ServiceUnavailableError(
                        message=f"OllamaException: {original_exception}",
                        llm_provider="ollama",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                elif "Invalid response object from API" in error_str:
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"OllamaException: {original_exception}",
                        llm_provider="ollama",
                        model=model,
                        response=getattr(original_exception, "response", None),
                    )
                elif "Read timed out" in error_str:
                    exception_mapping_worked = True
                    raise Timeout(
                        message=f"OllamaException: {original_exception}",
                        llm_provider="ollama",
                        model=model,
                    )
            elif custom_llm_provider == "vllm":
                if hasattr(original_exception, "status_code"):
                    if original_exception.status_code == 0:
                        exception_mapping_worked = True
                        raise APIConnectionError(
                            message=f"VLLMException - {original_exception.message}",
                            llm_provider="vllm",
                            model=model,
                            request=original_exception.request,
                        )
            elif custom_llm_provider == "azure" or custom_llm_provider == "azure_text":
                message = get_error_message(error_obj=original_exception)
                if message is None:
                    if hasattr(original_exception, "message"):
                        message = original_exception.message
                    else:
                        message = str(original_exception)

                if "Internal server error" in error_str:
                    exception_mapping_worked = True
                    raise litellm.InternalServerError(
                        message=f"AzureException Internal server error - {message}",
                        llm_provider="azure",
                        model=model,
                        litellm_debug_info=extra_information,
                        response=getattr(original_exception, "response", None),
                    )
                elif "This model's maximum context length is" in error_str:
                    exception_mapping_worked = True
                    raise ContextWindowExceededError(
                        message=f"AzureException ContextWindowExceededError - {message}",
                        llm_provider="azure",
                        model=model,
                        litellm_debug_info=extra_information,
                        response=getattr(original_exception, "response", None),
                    )
                elif "DeploymentNotFound" in error_str:
                    exception_mapping_worked = True
                    raise NotFoundError(
                        message=f"AzureException NotFoundError - {message}",
                        llm_provider="azure",
                        model=model,
                        litellm_debug_info=extra_information,
                        response=getattr(original_exception, "response", None),
                    )
                elif (
                    (
                        "invalid_request_error" in error_str
                        and "content_policy_violation" in error_str
                    )
                    or (
                        "The response was filtered due to the prompt triggering Azure OpenAI's content management"
                        in error_str
                    )
                    or "Your task failed as a result of our safety system" in error_str
                    or "The model produced invalid content" in error_str
                    or "content_filter_policy" in error_str
                ):
                    exception_mapping_worked = True
                    raise ContentPolicyViolationError(
                        message=f"litellm.ContentPolicyViolationError: AzureException - {message}",
                        llm_provider="azure",
                        model=model,
                        litellm_debug_info=extra_information,
                        response=getattr(original_exception, "response", None),
                    )
                elif "invalid_request_error" in error_str:
                    exception_mapping_worked = True
                    raise BadRequestError(
                        message=f"AzureException BadRequestError - {message}",
                        llm_provider="azure",
                        model=model,
                        litellm_debug_info=extra_information,
                        response=getattr(original_exception, "response", None),
                        body=getattr(original_exception, "body", None),
                    )
                elif (
                    "The api_key client option must be set either by passing api_key to the client or by setting"
                    in error_str
                ):
                    exception_mapping_worked = True
                    raise AuthenticationError(
                        message=f"{exception_provider} AuthenticationError - {message}",
                        llm_provider=custom_llm_provider,
                        model=model,
                        litellm_debug_info=extra_information,
                        response=getattr(original_exception, "response", None),
                    )
                elif "Connection error" in error_str:
                    exception_mapping_worked = True
                    raise APIConnectionError(
                        message=f"{exception_provider} APIConnectionError - {message}",
                        llm_provider=custom_llm_provider,
                        model=model,
                        litellm_debug_info=extra_information,
                    )
                elif hasattr(original_exception, "status_code"):
                    exception_mapping_worked = True
                    if original_exception.status_code == 400:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"AzureException - {message}",
                            llm_provider="azure",
                            model=model,
                            litellm_debug_info=extra_information,
                            response=getattr(original_exception, "response", None),
                            body=getattr(original_exception, "body", None),
                        )
                    elif original_exception.status_code == 401:
                        exception_mapping_worked = True
                        raise AuthenticationError(
                            message=f"AzureException AuthenticationError - {message}",
                            llm_provider="azure",
                            model=model,
                            litellm_debug_info=extra_information,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 408:
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"AzureException Timeout - {message}",
                            model=model,
                            litellm_debug_info=extra_information,
                            llm_provider="azure",
                        )
                    elif original_exception.status_code == 422:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"AzureException BadRequestError - {message}",
                            model=model,
                            llm_provider="azure",
                            litellm_debug_info=extra_information,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 429:
                        exception_mapping_worked = True
                        raise RateLimitError(
                            message=f"AzureException RateLimitError - {message}",
                            model=model,
                            llm_provider="azure",
                            litellm_debug_info=extra_information,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 503:
                        exception_mapping_worked = True
                        raise ServiceUnavailableError(
                            message=f"AzureException ServiceUnavailableError - {message}",
                            model=model,
                            llm_provider="azure",
                            litellm_debug_info=extra_information,
                            response=getattr(original_exception, "response", None),
                        )
                    elif original_exception.status_code == 504:  # gateway timeout error
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"AzureException Timeout - {message}",
                            model=model,
                            litellm_debug_info=extra_information,
                            llm_provider="azure",
                            exception_status_code=original_exception.status_code,
                        )
                    else:
                        exception_mapping_worked = True
                        raise APIError(
                            status_code=original_exception.status_code,
                            message=f"AzureException APIError - {message}",
                            llm_provider="azure",
                            litellm_debug_info=extra_information,
                            model=model,
                            request=httpx.Request(
                                method="POST", url="https://openai.com/"
                            ),
                        )
                else:
                    # if no status code then it is an APIConnectionError: https://github.com/openai/openai-python#handling-errors
                    raise APIConnectionError(
                        message=f"{exception_provider} APIConnectionError - {message}\n{traceback.format_exc()}",
                        llm_provider="azure",
                        model=model,
                        litellm_debug_info=extra_information,
                        request=httpx.Request(method="POST", url="https://openai.com/"),
                    )
            if custom_llm_provider == "openrouter":
                if hasattr(original_exception, "status_code"):
                    exception_mapping_worked = True
                    if original_exception.status_code == 400:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"{exception_provider} - {error_str}",
                            llm_provider=custom_llm_provider,
                            model=model,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 401:
                        exception_mapping_worked = True
                        raise AuthenticationError(
                            message=f"AuthenticationError: {exception_provider} - {error_str}",
                            llm_provider=custom_llm_provider,
                            model=model,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 404:
                        exception_mapping_worked = True
                        raise NotFoundError(
                            message=f"NotFoundError: {exception_provider} - {error_str}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 408:
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"Timeout Error: {exception_provider} - {error_str}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 422:
                        exception_mapping_worked = True
                        raise BadRequestError(
                            message=f"BadRequestError: {exception_provider} - {error_str}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 429:
                        exception_mapping_worked = True
                        raise RateLimitError(
                            message=f"RateLimitError: {exception_provider} - {error_str}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 503:
                        exception_mapping_worked = True
                        raise ServiceUnavailableError(
                            message=f"ServiceUnavailableError: {exception_provider} - {error_str}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            response=getattr(original_exception, "response", None),
                            litellm_debug_info=extra_information,
                        )
                    elif original_exception.status_code == 504:  # gateway timeout error
                        exception_mapping_worked = True
                        raise Timeout(
                            message=f"Timeout Error: {exception_provider} - {error_str}",
                            model=model,
                            llm_provider=custom_llm_provider,
                            litellm_debug_info=extra_information,
                            exception_status_code=original_exception.status_code,
                        )
                    else:
                        exception_mapping_worked = True
                        raise APIError(
                            status_code=original_exception.status_code,
                            message=f"APIError: {exception_provider} - {error_str}",
                            llm_provider=custom_llm_provider,
                            model=model,
                            request=original_exception.request,
                            litellm_debug_info=extra_information,
                        )
                else:
                    # if no status code then it is an APIConnectionError: https://github.com/openai/openai-python#handling-errors
                    raise APIConnectionError(
                        message=f"APIConnectionError: {exception_provider} - {error_str}",
                        llm_provider=custom_llm_provider,
                        model=model,
                        litellm_debug_info=extra_information,
                        request=httpx.Request(
                            method="POST", url="https://api.openai.com/v1/"
                        ),
                    )
        if (
            "BadRequestError.__init__() missing 1 required positional argument: 'param'"
            in str(original_exception)
        ):  # deal with edge-case invalid request error bug in openai-python sdk
            exception_mapping_worked = True
            raise BadRequestError(
                message=f"{exception_provider} BadRequestError : This can happen due to missing AZURE_API_VERSION: {str(original_exception)}",
                model=model,
                llm_provider=custom_llm_provider,
                response=getattr(original_exception, "response", None),
            )
        else:  # ensure generic errors always return APIConnectionError=
            """
            For unmapped exceptions - raise the exception with traceback - https://github.com/BerriAI/litellm/issues/4201
            """
            exception_mapping_worked = True
            if hasattr(original_exception, "request"):
                raise APIConnectionError(
                    message="{} - {}".format(exception_provider, error_str),
                    llm_provider=custom_llm_provider,
                    model=model,
                    request=original_exception.request,
                )
            else:
                raise APIConnectionError(
                    message="{}\n{}".format(
                        str(original_exception), traceback.format_exc()
                    ),
                    llm_provider=custom_llm_provider,
                    model=model,
                    request=httpx.Request(
                        method="POST", url="https://api.openai.com/v1/"
                    ),  # stub the request
                )
    except Exception as e:
        # LOGGING
        exception_logging(
            logger_fn=None,
            additional_args={
                "exception_mapping_worked": exception_mapping_worked,
                "original_exception": original_exception,
            },
            exception=e,
        )

        # don't let an error with mapping interrupt the user from receiving an error from the llm api calls
        if exception_mapping_worked:
            setattr(e, "litellm_response_headers", litellm_response_headers)
            raise e
        else:
            for error_type in litellm.LITELLM_EXCEPTION_TYPES:
                if isinstance(e, error_type):
                    setattr(e, "litellm_response_headers", litellm_response_headers)
                    raise e  # it's already mapped
            raised_exc = APIConnectionError(
                message="{}\n{}".format(original_exception, traceback.format_exc()),
                llm_provider="",
                model="",
            )
            setattr(raised_exc, "litellm_response_headers", litellm_response_headers)
            raise raised_exc


####### LOGGING ###################


def exception_logging(
    additional_args={},
    logger_fn=None,
    exception=None,
):
    try:
        model_call_details = {}
        if exception:
            model_call_details["exception"] = exception
        model_call_details["additional_args"] = additional_args
        # User Logging -> if you pass in a custom logging function or want to use sentry breadcrumbs
        verbose_logger.debug(
            f"Logging Details: logger_fn - {logger_fn} | callable(logger_fn) - {callable(logger_fn)}"
        )
        if logger_fn and callable(logger_fn):
            try:
                logger_fn(
                    model_call_details
                )  # Expectation: any logger function passed in by the user should accept a dict object
            except Exception:
                verbose_logger.debug(
                    f"LiteLLM.LoggingError: [Non-Blocking] Exception occurred while logging {traceback.format_exc()}"
                )
    except Exception:
        verbose_logger.debug(
            f"LiteLLM.LoggingError: [Non-Blocking] Exception occurred while logging {traceback.format_exc()}"
        )
        pass


def _add_key_name_and_team_to_alert(request_info: str, metadata: dict) -> str:
    """
    Internal helper function for litellm proxy
    Add the Key Name + Team Name to the error
    Only gets added if the metadata contains the user_api_key_alias and user_api_key_team_alias

    [Non-Blocking helper function]
    """
    try:
        _api_key_name = metadata.get("user_api_key_alias", None)
        _user_api_key_team_alias = metadata.get("user_api_key_team_alias", None)
        if _api_key_name is not None:
            request_info = (
                f"\n\nKey Name: `{_api_key_name}`\nTeam: `{_user_api_key_team_alias}`"
                + request_info
            )

        return request_info
    except Exception:
        return request_info

# === NexusCore/openenv\Lib\site-packages\openai\lib\_old_api.py ===
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from typing_extensions import override

from .._utils import LazyProxy
from .._exceptions import OpenAIError

INSTRUCTIONS = """

You tried to access openai.{symbol}, but this is no longer supported in openai>=1.0.0 - see the README at https://github.com/openai/openai-python for the API.

You can run `openai migrate` to automatically upgrade your codebase to use the 1.0.0 interface. 

Alternatively, you can pin your installation to the old version, e.g. `pip install openai==0.28`

A detailed migration guide is available here: https://github.com/openai/openai-python/discussions/742
"""


class APIRemovedInV1(OpenAIError):
    def __init__(self, *, symbol: str) -> None:
        super().__init__(INSTRUCTIONS.format(symbol=symbol))


class APIRemovedInV1Proxy(LazyProxy[Any]):
    def __init__(self, *, symbol: str) -> None:
        super().__init__()
        self._symbol = symbol

    @override
    def __load__(self) -> Any:
        # return the proxy until it is eventually called so that
        # we don't break people that are just checking the attributes
        # of a module
        return self

    def __call__(self, *_args: Any, **_kwargs: Any) -> Any:
        raise APIRemovedInV1(symbol=self._symbol)


SYMBOLS = [
    "Edit",
    "File",
    "Audio",
    "Image",
    "Model",
    "Engine",
    "Customer",
    "FineTune",
    "Embedding",
    "Completion",
    "Deployment",
    "Moderation",
    "ErrorObject",
    "FineTuningJob",
    "ChatCompletion",
]

# we explicitly tell type checkers that nothing is exported
# from this file so that when we re-export the old symbols
# in `openai/__init__.py` they aren't added to the auto-complete
# suggestions given by editors
if TYPE_CHECKING:
    __all__: list[str] = []
else:
    __all__ = SYMBOLS


__locals = locals()
for symbol in SYMBOLS:
    __locals[symbol] = APIRemovedInV1Proxy(symbol=symbol)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\retriever_service\async_client.py ===
# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from collections import OrderedDict
import functools
import re
from typing import (
    Callable,
    Dict,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry_async as retries
from google.api_core.client_options import ClientOptions
from google.auth import credentials as ga_credentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta import gapic_version as package_version

try:
    OptionalRetry = Union[retries.AsyncRetry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.AsyncRetry, object, None]  # type: ignore

from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import field_mask_pb2  # type: ignore
from google.protobuf import timestamp_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.services.retriever_service import pagers
from google.ai.generativelanguage_v1beta.types import retriever, retriever_service

from .client import RetrieverServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, RetrieverServiceTransport
from .transports.grpc_asyncio import RetrieverServiceGrpcAsyncIOTransport


class RetrieverServiceAsyncClient:
    """An API for semantic search over a corpus of user uploaded
    content.
    """

    _client: RetrieverServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = RetrieverServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = RetrieverServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = RetrieverServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = RetrieverServiceClient._DEFAULT_UNIVERSE

    chunk_path = staticmethod(RetrieverServiceClient.chunk_path)
    parse_chunk_path = staticmethod(RetrieverServiceClient.parse_chunk_path)
    corpus_path = staticmethod(RetrieverServiceClient.corpus_path)
    parse_corpus_path = staticmethod(RetrieverServiceClient.parse_corpus_path)
    document_path = staticmethod(RetrieverServiceClient.document_path)
    parse_document_path = staticmethod(RetrieverServiceClient.parse_document_path)
    common_billing_account_path = staticmethod(
        RetrieverServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        RetrieverServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(RetrieverServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(
        RetrieverServiceClient.parse_common_folder_path
    )
    common_organization_path = staticmethod(
        RetrieverServiceClient.common_organization_path
    )
    parse_common_organization_path = staticmethod(
        RetrieverServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(RetrieverServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        RetrieverServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(RetrieverServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        RetrieverServiceClient.parse_common_location_path
    )

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            RetrieverServiceAsyncClient: The constructed client.
        """
        return RetrieverServiceClient.from_service_account_info.__func__(RetrieverServiceAsyncClient, info, *args, **kwargs)  # type: ignore

    @classmethod
    def from_service_account_file(cls, filename: str, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            file.

        Args:
            filename (str): The path to the service account private key json
                file.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            RetrieverServiceAsyncClient: The constructed client.
        """
        return RetrieverServiceClient.from_service_account_file.__func__(RetrieverServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

    from_service_account_json = from_service_account_file

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[ClientOptions] = None
    ):
        """Return the API endpoint and client cert source for mutual TLS.

        The client cert source is determined in the following order:
        (1) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is not "true", the
        client cert source is None.
        (2) if `client_options.client_cert_source` is provided, use the provided one; if the
        default client cert source exists, use the default one; otherwise the client cert
        source is None.

        The API endpoint is determined in the following order:
        (1) if `client_options.api_endpoint` if provided, use the provided one.
        (2) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is "always", use the
        default mTLS endpoint; if the environment variable is "never", use the default API
        endpoint; otherwise if client cert source exists, use the default mTLS endpoint, otherwise
        use the default API endpoint.

        More details can be found at https://google.aip.dev/auth/4114.

        Args:
            client_options (google.api_core.client_options.ClientOptions): Custom options for the
                client. Only the `api_endpoint` and `client_cert_source` properties may be used
                in this method.

        Returns:
            Tuple[str, Callable[[], Tuple[bytes, bytes]]]: returns the API endpoint and the
                client cert source to use.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If any errors happen.
        """
        return RetrieverServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> RetrieverServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            RetrieverServiceTransport: The transport used by the client instance.
        """
        return self._client.transport

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._client._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used
                by the client instance.
        """
        return self._client._universe_domain

    get_transport_class = functools.partial(
        type(RetrieverServiceClient).get_transport_class, type(RetrieverServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[
                str, RetrieverServiceTransport, Callable[..., RetrieverServiceTransport]
            ]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the retriever service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,RetrieverServiceTransport,Callable[..., RetrieverServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the RetrieverServiceTransport constructor.
                If set to None, a transport is chosen automatically.
            client_options (Optional[Union[google.api_core.client_options.ClientOptions, dict]]):
                Custom options for the client.

                1. The ``api_endpoint`` property can be used to override the
                default endpoint provided by the client when ``transport`` is
                not explicitly provided. Only if this property is not set and
                ``transport`` was not explicitly provided, the endpoint is
                determined by the GOOGLE_API_USE_MTLS_ENDPOINT environment
                variable, which have one of the following values:
                "always" (always use the default mTLS endpoint), "never" (always
                use the default regular endpoint) and "auto" (auto-switch to the
                default mTLS endpoint if client certificate is present; this is
                the default value).

                2. If the GOOGLE_API_USE_CLIENT_CERTIFICATE environment variable
                is "true", then the ``client_cert_source`` property can be used
                to provide a client certificate for mTLS transport. If
                not provided, the default SSL client certificate will be used if
                present. If GOOGLE_API_USE_CLIENT_CERTIFICATE is "false" or not
                set, no client certificate will be used.

                3. The ``universe_domain`` property can be used to override the
                default "googleapis.com" universe. Note that ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client = RetrieverServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def create_corpus(
        self,
        request: Optional[Union[retriever_service.CreateCorpusRequest, dict]] = None,
        *,
        corpus: Optional[retriever.Corpus] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Corpus:
        r"""Creates an empty ``Corpus``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_create_corpus():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.CreateCorpusRequest(
                )

                # Make the request
                response = await client.create_corpus(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.CreateCorpusRequest, dict]]):
                The request object. Request to create a ``Corpus``.
            corpus (:class:`google.ai.generativelanguage_v1beta.types.Corpus`):
                Required. The ``Corpus`` to create.
                This corresponds to the ``corpus`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Corpus:
                A Corpus is a collection of Documents.
                   A project can create up to 5 corpora.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([corpus])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.CreateCorpusRequest):
            request = retriever_service.CreateCorpusRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if corpus is not None:
            request.corpus = corpus

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.create_corpus
        ]

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def get_corpus(
        self,
        request: Optional[Union[retriever_service.GetCorpusRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Corpus:
        r"""Gets information about a specific ``Corpus``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_get_corpus():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetCorpusRequest(
                    name="name_value",
                )

                # Make the request
                response = await client.get_corpus(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.GetCorpusRequest, dict]]):
                The request object. Request for getting information about a specific
                ``Corpus``.
            name (:class:`str`):
                Required. The name of the ``Corpus``. Example:
                ``corpora/my-corpus-123``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Corpus:
                A Corpus is a collection of Documents.
                   A project can create up to 5 corpora.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([name])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.GetCorpusRequest):
            request = retriever_service.GetCorpusRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.get_corpus
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def update_corpus(
        self,
        request: Optional[Union[retriever_service.UpdateCorpusRequest, dict]] = None,
        *,
        corpus: Optional[retriever.Corpus] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Corpus:
        r"""Updates a ``Corpus``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_update_corpus():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.UpdateCorpusRequest(
                )

                # Make the request
                response = await client.update_corpus(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.UpdateCorpusRequest, dict]]):
                The request object. Request to update a ``Corpus``.
            corpus (:class:`google.ai.generativelanguage_v1beta.types.Corpus`):
                Required. The ``Corpus`` to update.
                This corresponds to the ``corpus`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (:class:`google.protobuf.field_mask_pb2.FieldMask`):
                Required. The list of fields to update. Currently, this
                only supports updating ``display_name``.

                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Corpus:
                A Corpus is a collection of Documents.
                   A project can create up to 5 corpora.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([corpus, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.UpdateCorpusRequest):
            request = retriever_service.UpdateCorpusRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if corpus is not None:
            request.corpus = corpus
        if update_mask is not None:
            request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.update_corpus
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("corpus.name", request.corpus.name),)
            ),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def delete_corpus(
        self,
        request: Optional[Union[retriever_service.DeleteCorpusRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes a ``Corpus``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_delete_corpus():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.DeleteCorpusRequest(
                    name="name_value",
                )

                # Make the request
                await client.delete_corpus(request=request)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.DeleteCorpusRequest, dict]]):
                The request object. Request to delete a ``Corpus``.
            name (:class:`str`):
                Required. The resource name of the ``Corpus``. Example:
                ``corpora/my-corpus-123``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([name])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.DeleteCorpusRequest):
            request = retriever_service.DeleteCorpusRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.delete_corpus
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    async def list_corpora(
        self,
        request: Optional[Union[retriever_service.ListCorporaRequest, dict]] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListCorporaAsyncPager:
        r"""Lists all ``Corpora`` owned by the user.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_list_corpora():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListCorporaRequest(
                )

                # Make the request
                page_result = client.list_corpora(request=request)

                # Handle the response
                async for response in page_result:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.ListCorporaRequest, dict]]):
                The request object. Request for listing ``Corpora``.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.retriever_service.pagers.ListCorporaAsyncPager:
                Response from ListCorpora containing a paginated list of Corpora.
                   The results are sorted by ascending
                   corpus.create_time.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.ListCorporaRequest):
            request = retriever_service.ListCorporaRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.list_corpora
        ]

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__aiter__` convenience method.
        response = pagers.ListCorporaAsyncPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def query_corpus(
        self,
        request: Optional[Union[retriever_service.QueryCorpusRequest, dict]] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever_service.QueryCorpusResponse:
        r"""Performs semantic search over a ``Corpus``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_query_corpus():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.QueryCorpusRequest(
                    name="name_value",
                    query="query_value",
                )

                # Make the request
                response = await client.query_corpus(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.QueryCorpusRequest, dict]]):
                The request object. Request for querying a ``Corpus``.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.QueryCorpusResponse:
                Response from QueryCorpus containing a list of relevant
                chunks.

        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.QueryCorpusRequest):
            request = retriever_service.QueryCorpusRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.query_corpus
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def create_document(
        self,
        request: Optional[Union[retriever_service.CreateDocumentRequest, dict]] = None,
        *,
        parent: Optional[str] = None,
        document: Optional[retriever.Document] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Document:
        r"""Creates an empty ``Document``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_create_document():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.CreateDocumentRequest(
                    parent="parent_value",
                )

                # Make the request
                response = await client.create_document(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.CreateDocumentRequest, dict]]):
                The request object. Request to create a ``Document``.
            parent (:class:`str`):
                Required. The name of the ``Corpus`` where this
                ``Document`` will be created. Example:
                ``corpora/my-corpus-123``

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            document (:class:`google.ai.generativelanguage_v1beta.types.Document`):
                Required. The ``Document`` to create.
                This corresponds to the ``document`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Document:
                A Document is a collection of Chunks.
                   A Corpus can have a maximum of 10,000 Documents.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([parent, document])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.CreateDocumentRequest):
            request = retriever_service.CreateDocumentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if parent is not None:
            request.parent = parent
        if document is not None:
            request.document = document

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.create_document
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def get_document(
        self,
        request: Optional[Union[retriever_service.GetDocumentRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Document:
        r"""Gets information about a specific ``Document``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_get_document():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetDocumentRequest(
                    name="name_value",
                )

                # Make the request
                response = await client.get_document(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.GetDocumentRequest, dict]]):
                The request object. Request for getting information about a specific
                ``Document``.
            name (:class:`str`):
                Required. The name of the ``Document`` to retrieve.
                Example: ``corpora/my-corpus-123/documents/the-doc-abc``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Document:
                A Document is a collection of Chunks.
                   A Corpus can have a maximum of 10,000 Documents.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([name])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.GetDocumentRequest):
            request = retriever_service.GetDocumentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.get_document
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def update_document(
        self,
        request: Optional[Union[retriever_service.UpdateDocumentRequest, dict]] = None,
        *,
        document: Optional[retriever.Document] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Document:
        r"""Updates a ``Document``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_update_document():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.UpdateDocumentRequest(
                )

                # Make the request
                response = await client.update_document(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.UpdateDocumentRequest, dict]]):
                The request object. Request to update a ``Document``.
            document (:class:`google.ai.generativelanguage_v1beta.types.Document`):
                Required. The ``Document`` to update.
                This corresponds to the ``document`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (:class:`google.protobuf.field_mask_pb2.FieldMask`):
                Required. The list of fields to update. Currently, this
                only supports updating ``display_name`` and
                ``custom_metadata``.

                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Document:
                A Document is a collection of Chunks.
                   A Corpus can have a maximum of 10,000 Documents.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([document, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.UpdateDocumentRequest):
            request = retriever_service.UpdateDocumentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if document is not None:
            request.document = document
        if update_mask is not None:
            request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.update_document
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("document.name", request.document.name),)
            ),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def delete_document(
        self,
        request: Optional[Union[retriever_service.DeleteDocumentRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes a ``Document``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_delete_document():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.DeleteDocumentRequest(
                    name="name_value",
                )

                # Make the request
                await client.delete_document(request=request)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.DeleteDocumentRequest, dict]]):
                The request object. Request to delete a ``Document``.
            name (:class:`str`):
                Required. The resource name of the ``Document`` to
                delete. Example:
                ``corpora/my-corpus-123/documents/the-doc-abc``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([name])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.DeleteDocumentRequest):
            request = retriever_service.DeleteDocumentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.delete_document
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    async def list_documents(
        self,
        request: Optional[Union[retriever_service.ListDocumentsRequest, dict]] = None,
        *,
        parent: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListDocumentsAsyncPager:
        r"""Lists all ``Document``\ s in a ``Corpus``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_list_documents():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListDocumentsRequest(
                    parent="parent_value",
                )

                # Make the request
                page_result = client.list_documents(request=request)

                # Handle the response
                async for response in page_result:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.ListDocumentsRequest, dict]]):
                The request object. Request for listing ``Document``\ s.
            parent (:class:`str`):
                Required. The name of the ``Corpus`` containing
                ``Document``\ s. Example: ``corpora/my-corpus-123``

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.retriever_service.pagers.ListDocumentsAsyncPager:
                Response from ListDocuments containing a paginated list of Documents.
                   The Documents are sorted by ascending
                   document.create_time.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([parent])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.ListDocumentsRequest):
            request = retriever_service.ListDocumentsRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if parent is not None:
            request.parent = parent

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.list_documents
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__aiter__` convenience method.
        response = pagers.ListDocumentsAsyncPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def query_document(
        self,
        request: Optional[Union[retriever_service.QueryDocumentRequest, dict]] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever_service.QueryDocumentResponse:
        r"""Performs semantic search over a ``Document``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_query_document():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.QueryDocumentRequest(
                    name="name_value",
                    query="query_value",
                )

                # Make the request
                response = await client.query_document(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.QueryDocumentRequest, dict]]):
                The request object. Request for querying a ``Document``.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.QueryDocumentResponse:
                Response from QueryDocument containing a list of
                relevant chunks.

        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.QueryDocumentRequest):
            request = retriever_service.QueryDocumentRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.query_document
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def create_chunk(
        self,
        request: Optional[Union[retriever_service.CreateChunkRequest, dict]] = None,
        *,
        parent: Optional[str] = None,
        chunk: Optional[retriever.Chunk] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Chunk:
        r"""Creates a ``Chunk``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_create_chunk():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                chunk = generativelanguage_v1beta.Chunk()
                chunk.data.string_value = "string_value_value"

                request = generativelanguage_v1beta.CreateChunkRequest(
                    parent="parent_value",
                    chunk=chunk,
                )

                # Make the request
                response = await client.create_chunk(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.CreateChunkRequest, dict]]):
                The request object. Request to create a ``Chunk``.
            parent (:class:`str`):
                Required. The name of the ``Document`` where this
                ``Chunk`` will be created. Example:
                ``corpora/my-corpus-123/documents/the-doc-abc``

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            chunk (:class:`google.ai.generativelanguage_v1beta.types.Chunk`):
                Required. The ``Chunk`` to create.
                This corresponds to the ``chunk`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Chunk:
                A Chunk is a subpart of a Document that is treated as an independent unit
                   for the purposes of vector representation and
                   storage. A Corpus can have a maximum of 1 million
                   Chunks.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([parent, chunk])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.CreateChunkRequest):
            request = retriever_service.CreateChunkRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if parent is not None:
            request.parent = parent
        if chunk is not None:
            request.chunk = chunk

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.create_chunk
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def batch_create_chunks(
        self,
        request: Optional[
            Union[retriever_service.BatchCreateChunksRequest, dict]
        ] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever_service.BatchCreateChunksResponse:
        r"""Batch create ``Chunk``\ s.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_batch_create_chunks():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                requests = generativelanguage_v1beta.CreateChunkRequest()
                requests.parent = "parent_value"
                requests.chunk.data.string_value = "string_value_value"

                request = generativelanguage_v1beta.BatchCreateChunksRequest(
                    requests=requests,
                )

                # Make the request
                response = await client.batch_create_chunks(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.BatchCreateChunksRequest, dict]]):
                The request object. Request to batch create ``Chunk``\ s.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.BatchCreateChunksResponse:
                Response from BatchCreateChunks containing a list of
                created Chunks.

        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.BatchCreateChunksRequest):
            request = retriever_service.BatchCreateChunksRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.batch_create_chunks
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def get_chunk(
        self,
        request: Optional[Union[retriever_service.GetChunkRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Chunk:
        r"""Gets information about a specific ``Chunk``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_get_chunk():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetChunkRequest(
                    name="name_value",
                )

                # Make the request
                response = await client.get_chunk(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.GetChunkRequest, dict]]):
                The request object. Request for getting information about a specific
                ``Chunk``.
            name (:class:`str`):
                Required. The name of the ``Chunk`` to retrieve.
                Example:
                ``corpora/my-corpus-123/documents/the-doc-abc/chunks/some-chunk``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Chunk:
                A Chunk is a subpart of a Document that is treated as an independent unit
                   for the purposes of vector representation and
                   storage. A Corpus can have a maximum of 1 million
                   Chunks.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([name])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.GetChunkRequest):
            request = retriever_service.GetChunkRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.get_chunk
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def update_chunk(
        self,
        request: Optional[Union[retriever_service.UpdateChunkRequest, dict]] = None,
        *,
        chunk: Optional[retriever.Chunk] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever.Chunk:
        r"""Updates a ``Chunk``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_update_chunk():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                chunk = generativelanguage_v1beta.Chunk()
                chunk.data.string_value = "string_value_value"

                request = generativelanguage_v1beta.UpdateChunkRequest(
                    chunk=chunk,
                )

                # Make the request
                response = await client.update_chunk(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.UpdateChunkRequest, dict]]):
                The request object. Request to update a ``Chunk``.
            chunk (:class:`google.ai.generativelanguage_v1beta.types.Chunk`):
                Required. The ``Chunk`` to update.
                This corresponds to the ``chunk`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (:class:`google.protobuf.field_mask_pb2.FieldMask`):
                Required. The list of fields to update. Currently, this
                only supports updating ``custom_metadata`` and ``data``.

                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Chunk:
                A Chunk is a subpart of a Document that is treated as an independent unit
                   for the purposes of vector representation and
                   storage. A Corpus can have a maximum of 1 million
                   Chunks.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([chunk, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.UpdateChunkRequest):
            request = retriever_service.UpdateChunkRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if chunk is not None:
            request.chunk = chunk
        if update_mask is not None:
            request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.update_chunk
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("chunk.name", request.chunk.name),)
            ),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def batch_update_chunks(
        self,
        request: Optional[
            Union[retriever_service.BatchUpdateChunksRequest, dict]
        ] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> retriever_service.BatchUpdateChunksResponse:
        r"""Batch update ``Chunk``\ s.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_batch_update_chunks():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                requests = generativelanguage_v1beta.UpdateChunkRequest()
                requests.chunk.data.string_value = "string_value_value"

                request = generativelanguage_v1beta.BatchUpdateChunksRequest(
                    requests=requests,
                )

                # Make the request
                response = await client.batch_update_chunks(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.BatchUpdateChunksRequest, dict]]):
                The request object. Request to batch update ``Chunk``\ s.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.BatchUpdateChunksResponse:
                Response from BatchUpdateChunks containing a list of
                updated Chunks.

        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.BatchUpdateChunksRequest):
            request = retriever_service.BatchUpdateChunksRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.batch_update_chunks
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def delete_chunk(
        self,
        request: Optional[Union[retriever_service.DeleteChunkRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes a ``Chunk``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_delete_chunk():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.DeleteChunkRequest(
                    name="name_value",
                )

                # Make the request
                await client.delete_chunk(request=request)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.DeleteChunkRequest, dict]]):
                The request object. Request to delete a ``Chunk``.
            name (:class:`str`):
                Required. The resource name of the ``Chunk`` to delete.
                Example:
                ``corpora/my-corpus-123/documents/the-doc-abc/chunks/some-chunk``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([name])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.DeleteChunkRequest):
            request = retriever_service.DeleteChunkRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.delete_chunk
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    async def batch_delete_chunks(
        self,
        request: Optional[
            Union[retriever_service.BatchDeleteChunksRequest, dict]
        ] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Batch delete ``Chunk``\ s.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_batch_delete_chunks():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                requests = generativelanguage_v1beta.DeleteChunkRequest()
                requests.name = "name_value"

                request = generativelanguage_v1beta.BatchDeleteChunksRequest(
                    requests=requests,
                )

                # Make the request
                await client.batch_delete_chunks(request=request)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.BatchDeleteChunksRequest, dict]]):
                The request object. Request to batch delete ``Chunk``\ s.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.BatchDeleteChunksRequest):
            request = retriever_service.BatchDeleteChunksRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.batch_delete_chunks
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    async def list_chunks(
        self,
        request: Optional[Union[retriever_service.ListChunksRequest, dict]] = None,
        *,
        parent: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListChunksAsyncPager:
        r"""Lists all ``Chunk``\ s in a ``Document``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_list_chunks():
                # Create a client
                client = generativelanguage_v1beta.RetrieverServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListChunksRequest(
                    parent="parent_value",
                )

                # Make the request
                page_result = client.list_chunks(request=request)

                # Handle the response
                async for response in page_result:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.ListChunksRequest, dict]]):
                The request object. Request for listing ``Chunk``\ s.
            parent (:class:`str`):
                Required. The name of the ``Document`` containing
                ``Chunk``\ s. Example:
                ``corpora/my-corpus-123/documents/the-doc-abc``

                This corresponds to the ``parent`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.retriever_service.pagers.ListChunksAsyncPager:
                Response from ListChunks containing a paginated list of Chunks.
                   The Chunks are sorted by ascending chunk.create_time.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([parent])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, retriever_service.ListChunksRequest):
            request = retriever_service.ListChunksRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if parent is not None:
            request.parent = parent

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.list_chunks
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("parent", request.parent),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__aiter__` convenience method.
        response = pagers.ListChunksAsyncPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def __aenter__(self) -> "RetrieverServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("RetrieverServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\_g_l_y_f.py ===
"""_g_l_y_f.py -- Converter classes for the 'glyf' table."""

from collections import namedtuple
from fontTools.misc import sstruct
from fontTools import ttLib
from fontTools import version
from fontTools.misc.transform import DecomposedTransform
from fontTools.misc.textTools import tostr, safeEval, pad
from fontTools.misc.arrayTools import updateBounds, pointInRect
from fontTools.misc.bezierTools import calcQuadraticBounds
from fontTools.misc.fixedTools import (
    fixedToFloat as fi2fl,
    floatToFixed as fl2fi,
    floatToFixedToStr as fl2str,
    strToFixedToFloat as str2fl,
)
from fontTools.misc.roundTools import noRound, otRound
from fontTools.misc.vector import Vector
from numbers import Number
from . import DefaultTable
from . import ttProgram
import sys
import struct
import array
import logging
import math
import os
from fontTools.misc import xmlWriter
from fontTools.misc.filenames import userNameToFileName
from fontTools.misc.loggingTools import deprecateFunction
from enum import IntFlag
from functools import partial
from types import SimpleNamespace
from typing import Set

log = logging.getLogger(__name__)

# We compute the version the same as is computed in ttlib/__init__
# so that we can write 'ttLibVersion' attribute of the glyf TTX files
# when glyf is written to separate files.
version = ".".join(version.split(".")[:2])

#
# The Apple and MS rasterizers behave differently for
# scaled composite components: one does scale first and then translate
# and the other does it vice versa. MS defined some flags to indicate
# the difference, but it seems nobody actually _sets_ those flags.
#
# Funny thing: Apple seems to _only_ do their thing in the
# WE_HAVE_A_SCALE (eg. Chicago) case, and not when it's WE_HAVE_AN_X_AND_Y_SCALE
# (eg. Charcoal)...
#
SCALE_COMPONENT_OFFSET_DEFAULT = 0  # 0 == MS, 1 == Apple


class table__g_l_y_f(DefaultTable.DefaultTable):
    """Glyph Data table

    This class represents the `glyf <https://docs.microsoft.com/en-us/typography/opentype/spec/glyf>`_
    table, which contains outlines for glyphs in TrueType format. In many cases,
    it is easier to access and manipulate glyph outlines through the ``GlyphSet``
    object returned from :py:meth:`fontTools.ttLib.ttFont.getGlyphSet`::

                    >> from fontTools.pens.boundsPen import BoundsPen
                    >> glyphset = font.getGlyphSet()
                    >> bp = BoundsPen(glyphset)
                    >> glyphset["A"].draw(bp)
                    >> bp.bounds
                    (19, 0, 633, 716)

    However, this class can be used for low-level access to the ``glyf`` table data.
    Objects of this class support dictionary-like access, mapping glyph names to
    :py:class:`Glyph` objects::

                    >> glyf = font["glyf"]
                    >> len(glyf["Aacute"].components)
                    2

    Note that when adding glyphs to the font via low-level access to the ``glyf``
    table, the new glyphs must also be added to the ``hmtx``/``vmtx`` table::

                    >> font["glyf"]["divisionslash"] = Glyph()
                    >> font["hmtx"]["divisionslash"] = (640, 0)

    """

    dependencies = ["fvar"]

    # this attribute controls the amount of padding applied to glyph data upon compile.
    # Glyph lenghts are aligned to multiples of the specified value.
    # Allowed values are (0, 1, 2, 4). '0' means no padding; '1' (default) also means
    # no padding, except for when padding would allow to use short loca offsets.
    padding = 1

    def decompile(self, data, ttFont):
        self.axisTags = (
            [axis.axisTag for axis in ttFont["fvar"].axes] if "fvar" in ttFont else []
        )
        loca = ttFont["loca"]
        pos = int(loca[0])
        nextPos = 0
        noname = 0
        self.glyphs = {}
        self.glyphOrder = glyphOrder = ttFont.getGlyphOrder()
        self._reverseGlyphOrder = {}
        for i in range(0, len(loca) - 1):
            try:
                glyphName = glyphOrder[i]
            except IndexError:
                noname = noname + 1
                glyphName = "ttxautoglyph%s" % i
            nextPos = int(loca[i + 1])
            glyphdata = data[pos:nextPos]
            if len(glyphdata) != (nextPos - pos):
                raise ttLib.TTLibError("not enough 'glyf' table data")
            glyph = Glyph(glyphdata)
            self.glyphs[glyphName] = glyph
            pos = nextPos
        if len(data) - nextPos >= 4:
            log.warning(
                "too much 'glyf' table data: expected %d, received %d bytes",
                nextPos,
                len(data),
            )
        if noname:
            log.warning("%s glyphs have no name", noname)
        if ttFont.lazy is False:  # Be lazy for None and True
            self.ensureDecompiled()

    def ensureDecompiled(self, recurse=False):
        # The recurse argument is unused, but part of the signature of
        # ensureDecompiled across the library.
        for glyph in self.glyphs.values():
            glyph.expand(self)

    def compile(self, ttFont):
        optimizeSpeed = ttFont.cfg[ttLib.OPTIMIZE_FONT_SPEED]

        self.axisTags = (
            [axis.axisTag for axis in ttFont["fvar"].axes] if "fvar" in ttFont else []
        )
        if not hasattr(self, "glyphOrder"):
            self.glyphOrder = ttFont.getGlyphOrder()
        padding = self.padding
        assert padding in (0, 1, 2, 4)
        locations = []
        currentLocation = 0
        dataList = []
        recalcBBoxes = ttFont.recalcBBoxes
        boundsDone = set()
        for glyphName in self.glyphOrder:
            glyph = self.glyphs[glyphName]
            glyphData = glyph.compile(
                self,
                recalcBBoxes,
                boundsDone=boundsDone,
                optimizeSize=not optimizeSpeed,
            )
            if padding > 1:
                glyphData = pad(glyphData, size=padding)
            locations.append(currentLocation)
            currentLocation = currentLocation + len(glyphData)
            dataList.append(glyphData)
        locations.append(currentLocation)

        if padding == 1 and currentLocation < 0x20000:
            # See if we can pad any odd-lengthed glyphs to allow loca
            # table to use the short offsets.
            indices = [
                i for i, glyphData in enumerate(dataList) if len(glyphData) % 2 == 1
            ]
            if indices and currentLocation + len(indices) < 0x20000:
                # It fits.  Do it.
                for i in indices:
                    dataList[i] += b"\0"
                currentLocation = 0
                for i, glyphData in enumerate(dataList):
                    locations[i] = currentLocation
                    currentLocation += len(glyphData)
                locations[len(dataList)] = currentLocation

        data = b"".join(dataList)
        if "loca" in ttFont:
            ttFont["loca"].set(locations)
        if "maxp" in ttFont:
            ttFont["maxp"].numGlyphs = len(self.glyphs)
        if not data:
            # As a special case when all glyph in the font are empty, add a zero byte
            # to the table, so that OTS doesn’t reject it, and to make the table work
            # on Windows as well.
            # See https://github.com/khaledhosny/ots/issues/52
            data = b"\0"
        return data

    def toXML(self, writer, ttFont, splitGlyphs=False):
        notice = (
            "The xMin, yMin, xMax and yMax values\n"
            "will be recalculated by the compiler."
        )
        glyphNames = ttFont.getGlyphNames()
        if not splitGlyphs:
            writer.newline()
            writer.comment(notice)
            writer.newline()
            writer.newline()
        numGlyphs = len(glyphNames)
        if splitGlyphs:
            path, ext = os.path.splitext(writer.file.name)
            existingGlyphFiles = set()
        for glyphName in glyphNames:
            glyph = self.get(glyphName)
            if glyph is None:
                log.warning("glyph '%s' does not exist in glyf table", glyphName)
                continue
            if glyph.numberOfContours:
                if splitGlyphs:
                    glyphPath = userNameToFileName(
                        tostr(glyphName, "utf-8"),
                        existingGlyphFiles,
                        prefix=path + ".",
                        suffix=ext,
                    )
                    existingGlyphFiles.add(glyphPath.lower())
                    glyphWriter = xmlWriter.XMLWriter(
                        glyphPath,
                        idlefunc=writer.idlefunc,
                        newlinestr=writer.newlinestr,
                    )
                    glyphWriter.begintag("ttFont", ttLibVersion=version)
                    glyphWriter.newline()
                    glyphWriter.begintag("glyf")
                    glyphWriter.newline()
                    glyphWriter.comment(notice)
                    glyphWriter.newline()
                    writer.simpletag("TTGlyph", src=os.path.basename(glyphPath))
                else:
                    glyphWriter = writer
                glyphWriter.begintag(
                    "TTGlyph",
                    [
                        ("name", glyphName),
                        ("xMin", glyph.xMin),
                        ("yMin", glyph.yMin),
                        ("xMax", glyph.xMax),
                        ("yMax", glyph.yMax),
                    ],
                )
                glyphWriter.newline()
                glyph.toXML(glyphWriter, ttFont)
                glyphWriter.endtag("TTGlyph")
                glyphWriter.newline()
                if splitGlyphs:
                    glyphWriter.endtag("glyf")
                    glyphWriter.newline()
                    glyphWriter.endtag("ttFont")
                    glyphWriter.newline()
                    glyphWriter.close()
            else:
                writer.simpletag("TTGlyph", name=glyphName)
                writer.comment("contains no outline data")
                if not splitGlyphs:
                    writer.newline()
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name != "TTGlyph":
            return
        if not hasattr(self, "glyphs"):
            self.glyphs = {}
        if not hasattr(self, "glyphOrder"):
            self.glyphOrder = ttFont.getGlyphOrder()
        glyphName = attrs["name"]
        log.debug("unpacking glyph '%s'", glyphName)
        glyph = Glyph()
        for attr in ["xMin", "yMin", "xMax", "yMax"]:
            setattr(glyph, attr, safeEval(attrs.get(attr, "0")))
        self.glyphs[glyphName] = glyph
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            glyph.fromXML(name, attrs, content, ttFont)
        if not ttFont.recalcBBoxes:
            glyph.compact(self, 0)

    def setGlyphOrder(self, glyphOrder):
        """Sets the glyph order

        Args:
                glyphOrder ([str]): List of glyph names in order.
        """
        self.glyphOrder = glyphOrder
        self._reverseGlyphOrder = {}

    def getGlyphName(self, glyphID):
        """Returns the name for the glyph with the given ID.

        Raises a ``KeyError`` if the glyph name is not found in the font.
        """
        return self.glyphOrder[glyphID]

    def _buildReverseGlyphOrderDict(self):
        self._reverseGlyphOrder = d = {}
        for glyphID, glyphName in enumerate(self.glyphOrder):
            d[glyphName] = glyphID

    def getGlyphID(self, glyphName):
        """Returns the ID of the glyph with the given name.

        Raises a ``ValueError`` if the glyph is not found in the font.
        """
        glyphOrder = self.glyphOrder
        id = getattr(self, "_reverseGlyphOrder", {}).get(glyphName)
        if id is None or id >= len(glyphOrder) or glyphOrder[id] != glyphName:
            self._buildReverseGlyphOrderDict()
            id = self._reverseGlyphOrder.get(glyphName)
        if id is None:
            raise ValueError(glyphName)
        return id

    def removeHinting(self):
        """Removes TrueType hints from all glyphs in the glyphset.

        See :py:meth:`Glyph.removeHinting`.
        """
        for glyph in self.glyphs.values():
            glyph.removeHinting()

    def keys(self):
        return self.glyphs.keys()

    def has_key(self, glyphName):
        return glyphName in self.glyphs

    __contains__ = has_key

    def get(self, glyphName, default=None):
        glyph = self.glyphs.get(glyphName, default)
        if glyph is not None:
            glyph.expand(self)
        return glyph

    def __getitem__(self, glyphName):
        glyph = self.glyphs[glyphName]
        glyph.expand(self)
        return glyph

    def __setitem__(self, glyphName, glyph):
        self.glyphs[glyphName] = glyph
        if glyphName not in self.glyphOrder:
            self.glyphOrder.append(glyphName)

    def __delitem__(self, glyphName):
        del self.glyphs[glyphName]
        self.glyphOrder.remove(glyphName)

    def __len__(self):
        assert len(self.glyphOrder) == len(self.glyphs)
        return len(self.glyphs)

    def _getPhantomPoints(self, glyphName, hMetrics, vMetrics=None):
        """Compute the four "phantom points" for the given glyph from its bounding box
        and the horizontal and vertical advance widths and sidebearings stored in the
        ttFont's "hmtx" and "vmtx" tables.

        'hMetrics' should be ttFont['hmtx'].metrics.

        'vMetrics' should be ttFont['vmtx'].metrics if there is "vmtx" or None otherwise.
        If there is no vMetrics passed in, vertical phantom points are set to the zero coordinate.

        https://docs.microsoft.com/en-us/typography/opentype/spec/tt_instructing_glyphs#phantoms
        """
        glyph = self[glyphName]
        if not hasattr(glyph, "xMin"):
            glyph.recalcBounds(self)

        horizontalAdvanceWidth, leftSideBearing = hMetrics[glyphName]
        leftSideX = glyph.xMin - leftSideBearing
        rightSideX = leftSideX + horizontalAdvanceWidth

        if vMetrics:
            verticalAdvanceWidth, topSideBearing = vMetrics[glyphName]
            topSideY = topSideBearing + glyph.yMax
            bottomSideY = topSideY - verticalAdvanceWidth
        else:
            bottomSideY = topSideY = 0

        return [
            (leftSideX, 0),
            (rightSideX, 0),
            (0, topSideY),
            (0, bottomSideY),
        ]

    def _getCoordinatesAndControls(
        self, glyphName, hMetrics, vMetrics=None, *, round=otRound
    ):
        """Return glyph coordinates and controls as expected by "gvar" table.

        The coordinates includes four "phantom points" for the glyph metrics,
        as mandated by the "gvar" spec.

        The glyph controls is a namedtuple with the following attributes:
                - numberOfContours: -1 for composite glyphs.
                - endPts: list of indices of end points for each contour in simple
                glyphs, or component indices in composite glyphs (used for IUP
                optimization).
                - flags: array of contour point flags for simple glyphs (None for
                composite glyphs).
                - components: list of base glyph names (str) for each component in
                composite glyphs (None for simple glyphs).

        The "hMetrics" and vMetrics are used to compute the "phantom points" (see
        the "_getPhantomPoints" method).

        Return None if the requested glyphName is not present.
        """
        glyph = self.get(glyphName)
        if glyph is None:
            return None
        if glyph.isComposite():
            coords = GlyphCoordinates(
                [(getattr(c, "x", 0), getattr(c, "y", 0)) for c in glyph.components]
            )
            controls = _GlyphControls(
                numberOfContours=glyph.numberOfContours,
                endPts=list(range(len(glyph.components))),
                flags=None,
                components=[
                    (c.glyphName, getattr(c, "transform", None))
                    for c in glyph.components
                ],
            )
        else:
            coords, endPts, flags = glyph.getCoordinates(self)
            coords = coords.copy()
            controls = _GlyphControls(
                numberOfContours=glyph.numberOfContours,
                endPts=endPts,
                flags=flags,
                components=None,
            )
        # Add phantom points for (left, right, top, bottom) positions.
        phantomPoints = self._getPhantomPoints(glyphName, hMetrics, vMetrics)
        coords.extend(phantomPoints)
        coords.toInt(round=round)
        return coords, controls

    def _setCoordinates(self, glyphName, coord, hMetrics, vMetrics=None):
        """Set coordinates and metrics for the given glyph.

        "coord" is an array of GlyphCoordinates which must include the "phantom
        points" as the last four coordinates.

        Both the horizontal/vertical advances and left/top sidebearings in "hmtx"
        and "vmtx" tables (if any) are updated from four phantom points and
        the glyph's bounding boxes.

        The "hMetrics" and vMetrics are used to propagate "phantom points"
        into "hmtx" and "vmtx" tables if desired.  (see the "_getPhantomPoints"
        method).
        """
        glyph = self[glyphName]

        # Handle phantom points for (left, right, top, bottom) positions.
        assert len(coord) >= 4
        leftSideX = coord[-4][0]
        rightSideX = coord[-3][0]
        topSideY = coord[-2][1]
        bottomSideY = coord[-1][1]

        coord = coord[:-4]

        if glyph.isComposite():
            assert len(coord) == len(glyph.components)
            for p, comp in zip(coord, glyph.components):
                if hasattr(comp, "x"):
                    comp.x, comp.y = p
        elif glyph.numberOfContours == 0:
            assert len(coord) == 0
        else:
            assert len(coord) == len(glyph.coordinates)
            glyph.coordinates = GlyphCoordinates(coord)

        glyph.recalcBounds(self, boundsDone=set())

        horizontalAdvanceWidth = otRound(rightSideX - leftSideX)
        if horizontalAdvanceWidth < 0:
            # unlikely, but it can happen, see:
            # https://github.com/fonttools/fonttools/pull/1198
            horizontalAdvanceWidth = 0
        leftSideBearing = otRound(glyph.xMin - leftSideX)
        hMetrics[glyphName] = horizontalAdvanceWidth, leftSideBearing

        if vMetrics is not None:
            verticalAdvanceWidth = otRound(topSideY - bottomSideY)
            if verticalAdvanceWidth < 0:  # unlikely but do the same as horizontal
                verticalAdvanceWidth = 0
            topSideBearing = otRound(topSideY - glyph.yMax)
            vMetrics[glyphName] = verticalAdvanceWidth, topSideBearing

    # Deprecated

    def _synthesizeVMetrics(self, glyphName, ttFont, defaultVerticalOrigin):
        """This method is wrong and deprecated.
        For rationale see:
        https://github.com/fonttools/fonttools/pull/2266/files#r613569473
        """
        vMetrics = getattr(ttFont.get("vmtx"), "metrics", None)
        if vMetrics is None:
            verticalAdvanceWidth = ttFont["head"].unitsPerEm
            topSideY = getattr(ttFont.get("hhea"), "ascent", None)
            if topSideY is None:
                if defaultVerticalOrigin is not None:
                    topSideY = defaultVerticalOrigin
                else:
                    topSideY = verticalAdvanceWidth
            glyph = self[glyphName]
            glyph.recalcBounds(self)
            topSideBearing = otRound(topSideY - glyph.yMax)
            vMetrics = {glyphName: (verticalAdvanceWidth, topSideBearing)}
        return vMetrics

    @deprecateFunction("use '_getPhantomPoints' instead", category=DeprecationWarning)
    def getPhantomPoints(self, glyphName, ttFont, defaultVerticalOrigin=None):
        """Old public name for self._getPhantomPoints().
        See: https://github.com/fonttools/fonttools/pull/2266"""
        hMetrics = ttFont["hmtx"].metrics
        vMetrics = self._synthesizeVMetrics(glyphName, ttFont, defaultVerticalOrigin)
        return self._getPhantomPoints(glyphName, hMetrics, vMetrics)

    @deprecateFunction(
        "use '_getCoordinatesAndControls' instead", category=DeprecationWarning
    )
    def getCoordinatesAndControls(self, glyphName, ttFont, defaultVerticalOrigin=None):
        """Old public name for self._getCoordinatesAndControls().
        See: https://github.com/fonttools/fonttools/pull/2266"""
        hMetrics = ttFont["hmtx"].metrics
        vMetrics = self._synthesizeVMetrics(glyphName, ttFont, defaultVerticalOrigin)
        return self._getCoordinatesAndControls(glyphName, hMetrics, vMetrics)

    @deprecateFunction("use '_setCoordinates' instead", category=DeprecationWarning)
    def setCoordinates(self, glyphName, ttFont):
        """Old public name for self._setCoordinates().
        See: https://github.com/fonttools/fonttools/pull/2266"""
        hMetrics = ttFont["hmtx"].metrics
        vMetrics = getattr(ttFont.get("vmtx"), "metrics", None)
        self._setCoordinates(glyphName, hMetrics, vMetrics)


_GlyphControls = namedtuple(
    "_GlyphControls", "numberOfContours endPts flags components"
)


glyphHeaderFormat = """
		>	# big endian
		numberOfContours:	h
		xMin:				h
		yMin:				h
		xMax:				h
		yMax:				h
"""

# flags
flagOnCurve = 0x01
flagXShort = 0x02
flagYShort = 0x04
flagRepeat = 0x08
flagXsame = 0x10
flagYsame = 0x20
flagOverlapSimple = 0x40
flagCubic = 0x80

# These flags are kept for XML output after decompiling the coordinates
keepFlags = flagOnCurve + flagOverlapSimple + flagCubic

_flagSignBytes = {
    0: 2,
    flagXsame: 0,
    flagXShort | flagXsame: +1,
    flagXShort: -1,
    flagYsame: 0,
    flagYShort | flagYsame: +1,
    flagYShort: -1,
}


def flagBest(x, y, onCurve):
    """For a given x,y delta pair, returns the flag that packs this pair
    most efficiently, as well as the number of byte cost of such flag."""

    flag = flagOnCurve if onCurve else 0
    cost = 0
    # do x
    if x == 0:
        flag = flag | flagXsame
    elif -255 <= x <= 255:
        flag = flag | flagXShort
        if x > 0:
            flag = flag | flagXsame
        cost += 1
    else:
        cost += 2
    # do y
    if y == 0:
        flag = flag | flagYsame
    elif -255 <= y <= 255:
        flag = flag | flagYShort
        if y > 0:
            flag = flag | flagYsame
        cost += 1
    else:
        cost += 2
    return flag, cost


def flagFits(newFlag, oldFlag, mask):
    newBytes = _flagSignBytes[newFlag & mask]
    oldBytes = _flagSignBytes[oldFlag & mask]
    return newBytes == oldBytes or abs(newBytes) > abs(oldBytes)


def flagSupports(newFlag, oldFlag):
    return (
        (oldFlag & flagOnCurve) == (newFlag & flagOnCurve)
        and flagFits(newFlag, oldFlag, flagXsame | flagXShort)
        and flagFits(newFlag, oldFlag, flagYsame | flagYShort)
    )


def flagEncodeCoord(flag, mask, coord, coordBytes):
    byteCount = _flagSignBytes[flag & mask]
    if byteCount == 1:
        coordBytes.append(coord)
    elif byteCount == -1:
        coordBytes.append(-coord)
    elif byteCount == 2:
        coordBytes.extend(struct.pack(">h", coord))


def flagEncodeCoords(flag, x, y, xBytes, yBytes):
    flagEncodeCoord(flag, flagXsame | flagXShort, x, xBytes)
    flagEncodeCoord(flag, flagYsame | flagYShort, y, yBytes)


ARG_1_AND_2_ARE_WORDS = 0x0001  # if set args are words otherwise they are bytes
ARGS_ARE_XY_VALUES = 0x0002  # if set args are xy values, otherwise they are points
ROUND_XY_TO_GRID = 0x0004  # for the xy values if above is true
WE_HAVE_A_SCALE = 0x0008  # Sx = Sy, otherwise scale == 1.0
NON_OVERLAPPING = 0x0010  # set to same value for all components (obsolete!)
MORE_COMPONENTS = 0x0020  # indicates at least one more glyph after this one
WE_HAVE_AN_X_AND_Y_SCALE = 0x0040  # Sx, Sy
WE_HAVE_A_TWO_BY_TWO = 0x0080  # t00, t01, t10, t11
WE_HAVE_INSTRUCTIONS = 0x0100  # instructions follow
USE_MY_METRICS = 0x0200  # apply these metrics to parent glyph
OVERLAP_COMPOUND = 0x0400  # used by Apple in GX fonts
SCALED_COMPONENT_OFFSET = 0x0800  # composite designed to have the component offset scaled (designed for Apple)
UNSCALED_COMPONENT_OFFSET = 0x1000  # composite designed not to have the component offset scaled (designed for MS)


CompositeMaxpValues = namedtuple(
    "CompositeMaxpValues", ["nPoints", "nContours", "maxComponentDepth"]
)


class Glyph(object):
    """This class represents an individual TrueType glyph.

    TrueType glyph objects come in two flavours: simple and composite. Simple
    glyph objects contain contours, represented via the ``.coordinates``,
    ``.flags``, ``.numberOfContours``, and ``.endPtsOfContours`` attributes;
    composite glyphs contain components, available through the ``.components``
    attributes.

    Because the ``.coordinates`` attribute (and other simple glyph attributes mentioned
    above) is only set on simple glyphs and the ``.components`` attribute is only
    set on composite glyphs, it is necessary to use the :py:meth:`isComposite`
    method to test whether a glyph is simple or composite before attempting to
    access its data.

    For a composite glyph, the components can also be accessed via array-like access::

            >> assert(font["glyf"]["Aacute"].isComposite())
            >> font["glyf"]["Aacute"][0]
            <fontTools.ttLib.tables._g_l_y_f.GlyphComponent at 0x1027b2ee0>

    """

    def __init__(self, data=b""):
        if not data:
            # empty char
            self.numberOfContours = 0
            return
        self.data = data

    def compact(self, glyfTable, recalcBBoxes=True):
        data = self.compile(glyfTable, recalcBBoxes)
        self.__dict__.clear()
        self.data = data

    def expand(self, glyfTable):
        if not hasattr(self, "data"):
            # already unpacked
            return
        if not self.data:
            # empty char
            del self.data
            self.numberOfContours = 0
            return
        dummy, data = sstruct.unpack2(glyphHeaderFormat, self.data, self)
        del self.data
        # Some fonts (eg. Neirizi.ttf) have a 0 for numberOfContours in
        # some glyphs; decompileCoordinates assumes that there's at least
        # one, so short-circuit here.
        if self.numberOfContours == 0:
            return
        if self.isComposite():
            self.decompileComponents(data, glyfTable)
        else:
            self.decompileCoordinates(data)

    def compile(
        self, glyfTable, recalcBBoxes=True, *, boundsDone=None, optimizeSize=True
    ):
        if hasattr(self, "data"):
            if recalcBBoxes:
                # must unpack glyph in order to recalculate bounding box
                self.expand(glyfTable)
            else:
                return self.data
        if self.numberOfContours == 0:
            return b""

        if recalcBBoxes:
            self.recalcBounds(glyfTable, boundsDone=boundsDone)

        data = sstruct.pack(glyphHeaderFormat, self)
        if self.isComposite():
            data = data + self.compileComponents(glyfTable)
        else:
            data = data + self.compileCoordinates(optimizeSize=optimizeSize)
        return data

    def toXML(self, writer, ttFont):
        if self.isComposite():
            for compo in self.components:
                compo.toXML(writer, ttFont)
            haveInstructions = hasattr(self, "program")
        else:
            last = 0
            for i in range(self.numberOfContours):
                writer.begintag("contour")
                writer.newline()
                for j in range(last, self.endPtsOfContours[i] + 1):
                    attrs = [
                        ("x", self.coordinates[j][0]),
                        ("y", self.coordinates[j][1]),
                        ("on", self.flags[j] & flagOnCurve),
                    ]
                    if self.flags[j] & flagOverlapSimple:
                        # Apple's rasterizer uses flagOverlapSimple in the first contour/first pt to flag glyphs that contain overlapping contours
                        attrs.append(("overlap", 1))
                    if self.flags[j] & flagCubic:
                        attrs.append(("cubic", 1))
                    writer.simpletag("pt", attrs)
                    writer.newline()
                last = self.endPtsOfContours[i] + 1
                writer.endtag("contour")
                writer.newline()
            haveInstructions = self.numberOfContours > 0
        if haveInstructions:
            if self.program:
                writer.begintag("instructions")
                writer.newline()
                self.program.toXML(writer, ttFont)
                writer.endtag("instructions")
            else:
                writer.simpletag("instructions")
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "contour":
            if self.numberOfContours < 0:
                raise ttLib.TTLibError("can't mix composites and contours in glyph")
            self.numberOfContours = self.numberOfContours + 1
            coordinates = GlyphCoordinates()
            flags = bytearray()
            for element in content:
                if not isinstance(element, tuple):
                    continue
                name, attrs, content = element
                if name != "pt":
                    continue  # ignore anything but "pt"
                coordinates.append((safeEval(attrs["x"]), safeEval(attrs["y"])))
                flag = bool(safeEval(attrs["on"]))
                if "overlap" in attrs and bool(safeEval(attrs["overlap"])):
                    flag |= flagOverlapSimple
                if "cubic" in attrs and bool(safeEval(attrs["cubic"])):
                    flag |= flagCubic
                flags.append(flag)
            if not hasattr(self, "coordinates"):
                self.coordinates = coordinates
                self.flags = flags
                self.endPtsOfContours = [len(coordinates) - 1]
            else:
                self.coordinates.extend(coordinates)
                self.flags.extend(flags)
                self.endPtsOfContours.append(len(self.coordinates) - 1)
        elif name == "component":
            if self.numberOfContours > 0:
                raise ttLib.TTLibError("can't mix composites and contours in glyph")
            self.numberOfContours = -1
            if not hasattr(self, "components"):
                self.components = []
            component = GlyphComponent()
            self.components.append(component)
            component.fromXML(name, attrs, content, ttFont)
        elif name == "instructions":
            self.program = ttProgram.Program()
            for element in content:
                if not isinstance(element, tuple):
                    continue
                name, attrs, content = element
                self.program.fromXML(name, attrs, content, ttFont)

    def getCompositeMaxpValues(self, glyfTable, maxComponentDepth=1):
        assert self.isComposite()
        nContours = 0
        nPoints = 0
        initialMaxComponentDepth = maxComponentDepth
        for compo in self.components:
            baseGlyph = glyfTable[compo.glyphName]
            if baseGlyph.numberOfContours == 0:
                continue
            elif baseGlyph.numberOfContours > 0:
                nP, nC = baseGlyph.getMaxpValues()
            else:
                nP, nC, componentDepth = baseGlyph.getCompositeMaxpValues(
                    glyfTable, initialMaxComponentDepth + 1
                )
                maxComponentDepth = max(maxComponentDepth, componentDepth)
            nPoints = nPoints + nP
            nContours = nContours + nC
        return CompositeMaxpValues(nPoints, nContours, maxComponentDepth)

    def getMaxpValues(self):
        assert self.numberOfContours > 0
        return len(self.coordinates), len(self.endPtsOfContours)

    def decompileComponents(self, data, glyfTable):
        self.components = []
        more = 1
        haveInstructions = 0
        while more:
            component = GlyphComponent()
            more, haveInstr, data = component.decompile(data, glyfTable)
            haveInstructions = haveInstructions | haveInstr
            self.components.append(component)
        if haveInstructions:
            (numInstructions,) = struct.unpack(">h", data[:2])
            data = data[2:]
            self.program = ttProgram.Program()
            self.program.fromBytecode(data[:numInstructions])
            data = data[numInstructions:]
            if len(data) >= 4:
                log.warning(
                    "too much glyph data at the end of composite glyph: %d excess bytes",
                    len(data),
                )

    def decompileCoordinates(self, data):
        endPtsOfContours = array.array("H")
        endPtsOfContours.frombytes(data[: 2 * self.numberOfContours])
        if sys.byteorder != "big":
            endPtsOfContours.byteswap()
        self.endPtsOfContours = endPtsOfContours.tolist()

        pos = 2 * self.numberOfContours
        (instructionLength,) = struct.unpack(">h", data[pos : pos + 2])
        self.program = ttProgram.Program()
        self.program.fromBytecode(data[pos + 2 : pos + 2 + instructionLength])
        pos += 2 + instructionLength
        nCoordinates = self.endPtsOfContours[-1] + 1
        flags, xCoordinates, yCoordinates = self.decompileCoordinatesRaw(
            nCoordinates, data, pos
        )

        # fill in repetitions and apply signs
        self.coordinates = coordinates = GlyphCoordinates.zeros(nCoordinates)
        xIndex = 0
        yIndex = 0
        for i in range(nCoordinates):
            flag = flags[i]
            # x coordinate
            if flag & flagXShort:
                if flag & flagXsame:
                    x = xCoordinates[xIndex]
                else:
                    x = -xCoordinates[xIndex]
                xIndex = xIndex + 1
            elif flag & flagXsame:
                x = 0
            else:
                x = xCoordinates[xIndex]
                xIndex = xIndex + 1
            # y coordinate
            if flag & flagYShort:
                if flag & flagYsame:
                    y = yCoordinates[yIndex]
                else:
                    y = -yCoordinates[yIndex]
                yIndex = yIndex + 1
            elif flag & flagYsame:
                y = 0
            else:
                y = yCoordinates[yIndex]
                yIndex = yIndex + 1
            coordinates[i] = (x, y)
        assert xIndex == len(xCoordinates)
        assert yIndex == len(yCoordinates)
        coordinates.relativeToAbsolute()
        # discard all flags except "keepFlags"
        for i in range(len(flags)):
            flags[i] &= keepFlags
        self.flags = flags

    def decompileCoordinatesRaw(self, nCoordinates, data, pos=0):
        # unpack flags and prepare unpacking of coordinates
        flags = bytearray(nCoordinates)
        # Warning: deep Python trickery going on. We use the struct module to unpack
        # the coordinates. We build a format string based on the flags, so we can
        # unpack the coordinates in one struct.unpack() call.
        xFormat = ">"  # big endian
        yFormat = ">"  # big endian
        j = 0
        while True:
            flag = data[pos]
            pos += 1
            repeat = 1
            if flag & flagRepeat:
                repeat = data[pos] + 1
                pos += 1
            for k in range(repeat):
                if flag & flagXShort:
                    xFormat = xFormat + "B"
                elif not (flag & flagXsame):
                    xFormat = xFormat + "h"
                if flag & flagYShort:
                    yFormat = yFormat + "B"
                elif not (flag & flagYsame):
                    yFormat = yFormat + "h"
                flags[j] = flag
                j = j + 1
            if j >= nCoordinates:
                break
        assert j == nCoordinates, "bad glyph flags"
        # unpack raw coordinates, krrrrrr-tching!
        xDataLen = struct.calcsize(xFormat)
        yDataLen = struct.calcsize(yFormat)
        if len(data) - pos - (xDataLen + yDataLen) >= 4:
            log.warning(
                "too much glyph data: %d excess bytes",
                len(data) - pos - (xDataLen + yDataLen),
            )
        xCoordinates = struct.unpack(xFormat, data[pos : pos + xDataLen])
        yCoordinates = struct.unpack(
            yFormat, data[pos + xDataLen : pos + xDataLen + yDataLen]
        )
        return flags, xCoordinates, yCoordinates

    def compileComponents(self, glyfTable):
        data = b""
        lastcomponent = len(self.components) - 1
        more = 1
        haveInstructions = 0
        for i in range(len(self.components)):
            if i == lastcomponent:
                haveInstructions = hasattr(self, "program")
                more = 0
            compo = self.components[i]
            data = data + compo.compile(more, haveInstructions, glyfTable)
        if haveInstructions:
            instructions = self.program.getBytecode()
            data = data + struct.pack(">h", len(instructions)) + instructions
        return data

    def compileCoordinates(self, *, optimizeSize=True):
        assert len(self.coordinates) == len(self.flags)
        data = []
        endPtsOfContours = array.array("H", self.endPtsOfContours)
        if sys.byteorder != "big":
            endPtsOfContours.byteswap()
        data.append(endPtsOfContours.tobytes())
        instructions = self.program.getBytecode()
        data.append(struct.pack(">h", len(instructions)))
        data.append(instructions)

        deltas = self.coordinates.copy()
        deltas.toInt()
        deltas.absoluteToRelative()

        if optimizeSize:
            # TODO(behdad): Add a configuration option for this?
            deltas = self.compileDeltasGreedy(self.flags, deltas)
            # deltas = self.compileDeltasOptimal(self.flags, deltas)
        else:
            deltas = self.compileDeltasForSpeed(self.flags, deltas)

        data.extend(deltas)
        return b"".join(data)

    def compileDeltasGreedy(self, flags, deltas):
        # Implements greedy algorithm for packing coordinate deltas:
        # uses shortest representation one coordinate at a time.
        compressedFlags = bytearray()
        compressedXs = bytearray()
        compressedYs = bytearray()
        lastflag = None
        repeat = 0
        for flag, (x, y) in zip(flags, deltas):
            # Oh, the horrors of TrueType
            # do x
            if x == 0:
                flag = flag | flagXsame
            elif -255 <= x <= 255:
                flag = flag | flagXShort
                if x > 0:
                    flag = flag | flagXsame
                else:
                    x = -x
                compressedXs.append(x)
            else:
                compressedXs.extend(struct.pack(">h", x))
            # do y
            if y == 0:
                flag = flag | flagYsame
            elif -255 <= y <= 255:
                flag = flag | flagYShort
                if y > 0:
                    flag = flag | flagYsame
                else:
                    y = -y
                compressedYs.append(y)
            else:
                compressedYs.extend(struct.pack(">h", y))
            # handle repeating flags
            if flag == lastflag and repeat != 255:
                repeat = repeat + 1
                if repeat == 1:
                    compressedFlags.append(flag)
                else:
                    compressedFlags[-2] = flag | flagRepeat
                    compressedFlags[-1] = repeat
            else:
                repeat = 0
                compressedFlags.append(flag)
            lastflag = flag
        return (compressedFlags, compressedXs, compressedYs)

    def compileDeltasOptimal(self, flags, deltas):
        # Implements optimal, dynaic-programming, algorithm for packing coordinate
        # deltas.  The savings are negligible :(.
        candidates = []
        bestTuple = None
        bestCost = 0
        repeat = 0
        for flag, (x, y) in zip(flags, deltas):
            # Oh, the horrors of TrueType
            flag, coordBytes = flagBest(x, y, flag)
            bestCost += 1 + coordBytes
            newCandidates = [
                (bestCost, bestTuple, flag, coordBytes),
                (bestCost + 1, bestTuple, (flag | flagRepeat), coordBytes),
            ]
            for lastCost, lastTuple, lastFlag, coordBytes in candidates:
                if (
                    lastCost + coordBytes <= bestCost + 1
                    and (lastFlag & flagRepeat)
                    and (lastFlag < 0xFF00)
                    and flagSupports(lastFlag, flag)
                ):
                    if (lastFlag & 0xFF) == (
                        flag | flagRepeat
                    ) and lastCost == bestCost + 1:
                        continue
                    newCandidates.append(
                        (lastCost + coordBytes, lastTuple, lastFlag + 256, coordBytes)
                    )
            candidates = newCandidates
            bestTuple = min(candidates, key=lambda t: t[0])
            bestCost = bestTuple[0]

        flags = []
        while bestTuple:
            cost, bestTuple, flag, coordBytes = bestTuple
            flags.append(flag)
        flags.reverse()

        compressedFlags = bytearray()
        compressedXs = bytearray()
        compressedYs = bytearray()
        coords = iter(deltas)
        ff = []
        for flag in flags:
            repeatCount, flag = flag >> 8, flag & 0xFF
            compressedFlags.append(flag)
            if flag & flagRepeat:
                assert repeatCount > 0
                compressedFlags.append(repeatCount)
            else:
                assert repeatCount == 0
            for i in range(1 + repeatCount):
                x, y = next(coords)
                flagEncodeCoords(flag, x, y, compressedXs, compressedYs)
                ff.append(flag)
        try:
            next(coords)
            raise Exception("internal error")
        except StopIteration:
            pass

        return (compressedFlags, compressedXs, compressedYs)

    def compileDeltasForSpeed(self, flags, deltas):
        # uses widest representation needed, for all deltas.
        compressedFlags = bytearray()
        compressedXs = bytearray()
        compressedYs = bytearray()

        # Compute the necessary width for each axis
        xs = [d[0] for d in deltas]
        ys = [d[1] for d in deltas]
        minX, minY, maxX, maxY = min(xs), min(ys), max(xs), max(ys)
        xZero = minX == 0 and maxX == 0
        yZero = minY == 0 and maxY == 0
        xShort = -255 <= minX <= maxX <= 255
        yShort = -255 <= minY <= maxY <= 255

        lastflag = None
        repeat = 0
        for flag, (x, y) in zip(flags, deltas):
            # Oh, the horrors of TrueType
            # do x
            if xZero:
                flag = flag | flagXsame
            elif xShort:
                flag = flag | flagXShort
                if x > 0:
                    flag = flag | flagXsame
                else:
                    x = -x
                compressedXs.append(x)
            else:
                compressedXs.extend(struct.pack(">h", x))
            # do y
            if yZero:
                flag = flag | flagYsame
            elif yShort:
                flag = flag | flagYShort
                if y > 0:
                    flag = flag | flagYsame
                else:
                    y = -y
                compressedYs.append(y)
            else:
                compressedYs.extend(struct.pack(">h", y))
            # handle repeating flags
            if flag == lastflag and repeat != 255:
                repeat = repeat + 1
                if repeat == 1:
                    compressedFlags.append(flag)
                else:
                    compressedFlags[-2] = flag | flagRepeat
                    compressedFlags[-1] = repeat
            else:
                repeat = 0
                compressedFlags.append(flag)
            lastflag = flag
        return (compressedFlags, compressedXs, compressedYs)

    def recalcBounds(self, glyfTable, *, boundsDone=None):
        """Recalculates the bounds of the glyph.

        Each glyph object stores its bounding box in the
        ``xMin``/``yMin``/``xMax``/``yMax`` attributes. These bounds must be
        recomputed when the ``coordinates`` change. The ``table__g_l_y_f`` bounds
        must be provided to resolve component bounds.
        """
        if self.isComposite() and self.tryRecalcBoundsComposite(
            glyfTable, boundsDone=boundsDone
        ):
            return
        try:
            coords, endPts, flags = self.getCoordinates(glyfTable, round=otRound)
            self.xMin, self.yMin, self.xMax, self.yMax = coords.calcIntBounds()
        except NotImplementedError:
            pass

    def tryRecalcBoundsComposite(self, glyfTable, *, boundsDone=None):
        """Try recalculating the bounds of a composite glyph that has
        certain constrained properties. Namely, none of the components
        have a transform other than an integer translate, and none
        uses the anchor points.

        Each glyph object stores its bounding box in the
        ``xMin``/``yMin``/``xMax``/``yMax`` attributes. These bounds must be
        recomputed when the ``coordinates`` change. The ``table__g_l_y_f`` bounds
        must be provided to resolve component bounds.

        Return True if bounds were calculated, False otherwise.
        """
        for compo in self.components:
            if not compo._hasOnlyIntegerTranslate():
                return False

        # All components are untransformed and have an integer x/y translate
        bounds = None
        for compo in self.components:
            glyphName = compo.glyphName
            g = glyfTable[glyphName]

            if boundsDone is None or glyphName not in boundsDone:
                g.recalcBounds(glyfTable, boundsDone=boundsDone)
                if boundsDone is not None:
                    boundsDone.add(glyphName)
            # empty components shouldn't update the bounds of the parent glyph
            if g.yMin == g.yMax and g.xMin == g.xMax:
                continue

            x, y = compo.x, compo.y
            bounds = updateBounds(bounds, (g.xMin + x, g.yMin + y))
            bounds = updateBounds(bounds, (g.xMax + x, g.yMax + y))

        if bounds is None:
            bounds = (0, 0, 0, 0)
        self.xMin, self.yMin, self.xMax, self.yMax = bounds
        return True

    def isComposite(self):
        """Test whether a glyph has components"""
        if hasattr(self, "data"):
            return struct.unpack(">h", self.data[:2])[0] == -1 if self.data else False
        else:
            return self.numberOfContours == -1

    def getCoordinates(self, glyfTable, *, round=noRound):
        """Return the coordinates, end points and flags

        This method returns three values: A :py:class:`GlyphCoordinates` object,
        a list of the indexes of the final points of each contour (allowing you
        to split up the coordinates list into contours) and a list of flags.

        On simple glyphs, this method returns information from the glyph's own
        contours; on composite glyphs, it "flattens" all components recursively
        to return a list of coordinates representing all the components involved
        in the glyph.

        To interpret the flags for each point, see the "Simple Glyph Flags"
        section of the `glyf table specification <https://docs.microsoft.com/en-us/typography/opentype/spec/glyf#simple-glyph-description>`.
        """

        if self.numberOfContours > 0:
            return self.coordinates, self.endPtsOfContours, self.flags
        elif self.isComposite():
            # it's a composite
            allCoords = GlyphCoordinates()
            allFlags = bytearray()
            allEndPts = []
            for compo in self.components:
                g = glyfTable[compo.glyphName]
                try:
                    coordinates, endPts, flags = g.getCoordinates(
                        glyfTable, round=round
                    )
                except RecursionError:
                    raise ttLib.TTLibError(
                        "glyph '%s' contains a recursive component reference"
                        % compo.glyphName
                    )
                coordinates = GlyphCoordinates(coordinates)
                # if asked to round e.g. while computing bboxes, it's important we
                # do it immediately before a component transform is applied to a
                # simple glyph's coordinates in case these might still contain floats;
                # however, if the referenced component glyph is another composite, we
                # must not round here but only at the end, after all the nested
                # transforms have been applied, or else rounding errors will compound.
                if round is not noRound and g.numberOfContours > 0:
                    coordinates.toInt(round=round)
                if hasattr(compo, "firstPt"):
                    # component uses two reference points: we apply the transform _before_
                    # computing the offset between the points
                    if hasattr(compo, "transform"):
                        coordinates.transform(compo.transform)
                    x1, y1 = allCoords[compo.firstPt]
                    x2, y2 = coordinates[compo.secondPt]
                    move = x1 - x2, y1 - y2
                    coordinates.translate(move)
                else:
                    # component uses XY offsets
                    move = compo.x, compo.y
                    if not hasattr(compo, "transform"):
                        coordinates.translate(move)
                    else:
                        apple_way = compo.flags & SCALED_COMPONENT_OFFSET
                        ms_way = compo.flags & UNSCALED_COMPONENT_OFFSET
                        assert not (apple_way and ms_way)
                        if not (apple_way or ms_way):
                            scale_component_offset = (
                                SCALE_COMPONENT_OFFSET_DEFAULT  # see top of this file
                            )
                        else:
                            scale_component_offset = apple_way
                        if scale_component_offset:
                            # the Apple way: first move, then scale (ie. scale the component offset)
                            coordinates.translate(move)
                            coordinates.transform(compo.transform)
                        else:
                            # the MS way: first scale, then move
                            coordinates.transform(compo.transform)
                            coordinates.translate(move)
                offset = len(allCoords)
                allEndPts.extend(e + offset for e in endPts)
                allCoords.extend(coordinates)
                allFlags.extend(flags)
            return allCoords, allEndPts, allFlags
        else:
            return GlyphCoordinates(), [], bytearray()

    def getComponentNames(self, glyfTable):
        """Returns a list of names of component glyphs used in this glyph

        This method can be used on simple glyphs (in which case it returns an
        empty list) or composite glyphs.
        """
        if not hasattr(self, "data"):
            if self.isComposite():
                return [c.glyphName for c in self.components]
            else:
                return []

        # Extract components without expanding glyph

        if not self.data or struct.unpack(">h", self.data[:2])[0] >= 0:
            return []  # Not composite

        data = self.data
        i = 10
        components = []
        more = 1
        while more:
            flags, glyphID = struct.unpack(">HH", data[i : i + 4])
            i += 4
            flags = int(flags)
            components.append(glyfTable.getGlyphName(int(glyphID)))

            if flags & ARG_1_AND_2_ARE_WORDS:
                i += 4
            else:
                i += 2
            if flags & WE_HAVE_A_SCALE:
                i += 2
            elif flags & WE_HAVE_AN_X_AND_Y_SCALE:
                i += 4
            elif flags & WE_HAVE_A_TWO_BY_TWO:
                i += 8
            more = flags & MORE_COMPONENTS

        return components

    def trim(self, remove_hinting=False):
        """Remove padding and, if requested, hinting, from a glyph.
        This works on both expanded and compacted glyphs, without
        expanding it."""
        if not hasattr(self, "data"):
            if remove_hinting:
                if self.isComposite():
                    if hasattr(self, "program"):
                        del self.program
                else:
                    self.program = ttProgram.Program()
                    self.program.fromBytecode([])
            # No padding to trim.
            return
        if not self.data:
            return
        numContours = struct.unpack(">h", self.data[:2])[0]
        data = bytearray(self.data)
        i = 10
        if numContours >= 0:
            i += 2 * numContours  # endPtsOfContours
            nCoordinates = ((data[i - 2] << 8) | data[i - 1]) + 1
            instructionLen = (data[i] << 8) | data[i + 1]
            if remove_hinting:
                # Zero instruction length
                data[i] = data[i + 1] = 0
                i += 2
                if instructionLen:
                    # Splice it out
                    data = data[:i] + data[i + instructionLen :]
                instructionLen = 0
            else:
                i += 2 + instructionLen

            coordBytes = 0
            j = 0
            while True:
                flag = data[i]
                i = i + 1
                repeat = 1
                if flag & flagRepeat:
                    repeat = data[i] + 1
                    i = i + 1
                xBytes = yBytes = 0
                if flag & flagXShort:
                    xBytes = 1
                elif not (flag & flagXsame):
                    xBytes = 2
                if flag & flagYShort:
                    yBytes = 1
                elif not (flag & flagYsame):
                    yBytes = 2
                coordBytes += (xBytes + yBytes) * repeat
                j += repeat
                if j >= nCoordinates:
                    break
            assert j == nCoordinates, "bad glyph flags"
            i += coordBytes
            # Remove padding
            data = data[:i]
        elif self.isComposite():
            more = 1
            we_have_instructions = False
            while more:
                flags = (data[i] << 8) | data[i + 1]
                if remove_hinting:
                    flags &= ~WE_HAVE_INSTRUCTIONS
                if flags & WE_HAVE_INSTRUCTIONS:
                    we_have_instructions = True
                data[i + 0] = flags >> 8
                data[i + 1] = flags & 0xFF
                i += 4
                flags = int(flags)

                if flags & ARG_1_AND_2_ARE_WORDS:
                    i += 4
                else:
                    i += 2
                if flags & WE_HAVE_A_SCALE:
                    i += 2
                elif flags & WE_HAVE_AN_X_AND_Y_SCALE:
                    i += 4
                elif flags & WE_HAVE_A_TWO_BY_TWO:
                    i += 8
                more = flags & MORE_COMPONENTS
            if we_have_instructions:
                instructionLen = (data[i] << 8) | data[i + 1]
                i += 2 + instructionLen
            # Remove padding
            data = data[:i]

        self.data = data

    def removeHinting(self):
        """Removes TrueType hinting instructions from the glyph."""
        self.trim(remove_hinting=True)

    def draw(self, pen, glyfTable, offset=0):
        """Draws the glyph using the supplied pen object.

        Arguments:
                pen: An object conforming to the pen protocol.
                glyfTable: A :py:class:`table__g_l_y_f` object, to resolve components.
                offset (int): A horizontal offset. If provided, all coordinates are
                        translated by this offset.
        """

        if self.isComposite():
            for component in self.components:
                glyphName, transform = component.getComponentInfo()
                pen.addComponent(glyphName, transform)
            return

        self.expand(glyfTable)
        coordinates, endPts, flags = self.getCoordinates(glyfTable)
        if offset:
            coordinates = coordinates.copy()
            coordinates.translate((offset, 0))
        start = 0
        maybeInt = lambda v: int(v) if v == int(v) else v
        for end in endPts:
            end = end + 1
            contour = coordinates[start:end]
            cFlags = [flagOnCurve & f for f in flags[start:end]]
            cuFlags = [flagCubic & f for f in flags[start:end]]
            start = end
            if 1 not in cFlags:
                assert all(cuFlags) or not any(cuFlags)
                cubic = all(cuFlags)
                if cubic:
                    count = len(contour)
                    assert count % 2 == 0, "Odd number of cubic off-curves undefined"
                    l = contour[-1]
                    f = contour[0]
                    p0 = (maybeInt((l[0] + f[0]) * 0.5), maybeInt((l[1] + f[1]) * 0.5))
                    pen.moveTo(p0)
                    for i in range(0, count, 2):
                        p1 = contour[i]
                        p2 = contour[i + 1]
                        p4 = contour[i + 2 if i + 2 < count else 0]
                        p3 = (
                            maybeInt((p2[0] + p4[0]) * 0.5),
                            maybeInt((p2[1] + p4[1]) * 0.5),
                        )
                        pen.curveTo(p1, p2, p3)
                else:
                    # There is not a single on-curve point on the curve,
                    # use pen.qCurveTo's special case by specifying None
                    # as the on-curve point.
                    contour.append(None)
                    pen.qCurveTo(*contour)
            else:
                # Shuffle the points so that the contour is guaranteed
                # to *end* in an on-curve point, which we'll use for
                # the moveTo.
                firstOnCurve = cFlags.index(1) + 1
                contour = contour[firstOnCurve:] + contour[:firstOnCurve]
                cFlags = cFlags[firstOnCurve:] + cFlags[:firstOnCurve]
                cuFlags = cuFlags[firstOnCurve:] + cuFlags[:firstOnCurve]
                pen.moveTo(contour[-1])
                while contour:
                    nextOnCurve = cFlags.index(1) + 1
                    if nextOnCurve == 1:
                        # Skip a final lineTo(), as it is implied by
                        # pen.closePath()
                        if len(contour) > 1:
                            pen.lineTo(contour[0])
                    else:
                        cubicFlags = [f for f in cuFlags[: nextOnCurve - 1]]
                        assert all(cubicFlags) or not any(cubicFlags)
                        cubic = any(cubicFlags)
                        if cubic:
                            assert all(
                                cubicFlags
                            ), "Mixed cubic and quadratic segment undefined"

                            count = nextOnCurve
                            assert (
                                count >= 3
                            ), "At least two cubic off-curve points required"
                            assert (
                                count - 1
                            ) % 2 == 0, "Odd number of cubic off-curves undefined"
                            for i in range(0, count - 3, 2):
                                p1 = contour[i]
                                p2 = contour[i + 1]
                                p4 = contour[i + 2]
                                p3 = (
                                    maybeInt((p2[0] + p4[0]) * 0.5),
                                    maybeInt((p2[1] + p4[1]) * 0.5),
                                )
                                lastOnCurve = p3
                                pen.curveTo(p1, p2, p3)
                            pen.curveTo(*contour[count - 3 : count])
                        else:
                            pen.qCurveTo(*contour[:nextOnCurve])
                    contour = contour[nextOnCurve:]
                    cFlags = cFlags[nextOnCurve:]
                    cuFlags = cuFlags[nextOnCurve:]
            pen.closePath()

    def drawPoints(self, pen, glyfTable, offset=0):
        """Draw the glyph using the supplied pointPen. As opposed to Glyph.draw(),
        this will not change the point indices.
        """

        if self.isComposite():
            for component in self.components:
                glyphName, transform = component.getComponentInfo()
                pen.addComponent(glyphName, transform)
            return

        coordinates, endPts, flags = self.getCoordinates(glyfTable)
        if offset:
            coordinates = coordinates.copy()
            coordinates.translate((offset, 0))
        start = 0
        for end in endPts:
            end = end + 1
            contour = coordinates[start:end]
            cFlags = flags[start:end]
            start = end
            pen.beginPath()
            # Start with the appropriate segment type based on the final segment

            if cFlags[-1] & flagOnCurve:
                segmentType = "line"
            elif cFlags[-1] & flagCubic:
                segmentType = "curve"
            else:
                segmentType = "qcurve"
            for i, pt in enumerate(contour):
                if cFlags[i] & flagOnCurve:
                    pen.addPoint(pt, segmentType=segmentType)
                    segmentType = "line"
                else:
                    pen.addPoint(pt)
                    segmentType = "curve" if cFlags[i] & flagCubic else "qcurve"
            pen.endPath()

    def __eq__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        result = self.__eq__(other)
        return result if result is NotImplemented else not result


# Vector.__round__ uses the built-in (Banker's) `round` but we want
# to use otRound below
_roundv = partial(Vector.__round__, round=otRound)


def _is_mid_point(p0: tuple, p1: tuple, p2: tuple) -> bool:
    # True if p1 is in the middle of p0 and p2, either before or after rounding
    p0 = Vector(p0)
    p1 = Vector(p1)
    p2 = Vector(p2)
    return ((p0 + p2) * 0.5).isclose(p1) or _roundv(p0) + _roundv(p2) == _roundv(p1) * 2


def dropImpliedOnCurvePoints(*interpolatable_glyphs: Glyph) -> Set[int]:
    """Drop impliable on-curve points from the (simple) glyph or glyphs.

    In TrueType glyf outlines, on-curve points can be implied when they are located at
    the midpoint of the line connecting two consecutive off-curve points.

    If more than one glyphs are passed, these are assumed to be interpolatable masters
    of the same glyph impliable, and thus only the on-curve points that are impliable
    for all of them will actually be implied.
    Composite glyphs or empty glyphs are skipped, only simple glyphs with 1 or more
    contours are considered.
    The input glyph(s) is/are modified in-place.

    Args:
        interpolatable_glyphs: The glyph or glyphs to modify in-place.

    Returns:
        The set of point indices that were dropped if any.

    Raises:
        ValueError if simple glyphs are not in fact interpolatable because they have
        different point flags or number of contours.

    Reference:
    https://developer.apple.com/fonts/TrueType-Reference-Manual/RM01/Chap1.html
    """
    staticAttributes = SimpleNamespace(
        numberOfContours=None, flags=None, endPtsOfContours=None
    )
    drop = None
    simple_glyphs = []
    for i, glyph in enumerate(interpolatable_glyphs):
        if glyph.numberOfContours < 1:
            # ignore composite or empty glyphs
            continue

        for attr in staticAttributes.__dict__:
            expected = getattr(staticAttributes, attr)
            found = getattr(glyph, attr)
            if expected is None:
                setattr(staticAttributes, attr, found)
            elif expected != found:
                raise ValueError(
                    f"Incompatible {attr} for glyph at master index {i}: "
                    f"expected {expected}, found {found}"
                )

        may_drop = set()
        start = 0
        coords = glyph.coordinates
        flags = staticAttributes.flags
        endPtsOfContours = staticAttributes.endPtsOfContours
        for last in endPtsOfContours:
            for i in range(start, last + 1):
                if not (flags[i] & flagOnCurve):
                    continue
                prv = i - 1 if i > start else last
                nxt = i + 1 if i < last else start
                if (flags[prv] & flagOnCurve) or flags[prv] != flags[nxt]:
                    continue
                # we may drop the ith on-curve if halfway between previous/next off-curves
                if not _is_mid_point(coords[prv], coords[i], coords[nxt]):
                    continue

                may_drop.add(i)
            start = last + 1
        # we only want to drop if ALL interpolatable glyphs have the same implied oncurves
        if drop is None:
            drop = may_drop
        else:
            drop.intersection_update(may_drop)

        simple_glyphs.append(glyph)

    if drop:
        # Do the actual dropping
        flags = staticAttributes.flags
        assert flags is not None
        newFlags = array.array(
            "B", (flags[i] for i in range(len(flags)) if i not in drop)
        )

        endPts = staticAttributes.endPtsOfContours
        assert endPts is not None
        newEndPts = []
        i = 0
        delta = 0
        for d in sorted(drop):
            while d > endPts[i]:
                newEndPts.append(endPts[i] - delta)
                i += 1
            delta += 1
        while i < len(endPts):
            newEndPts.append(endPts[i] - delta)
            i += 1

        for glyph in simple_glyphs:
            coords = glyph.coordinates
            glyph.coordinates = GlyphCoordinates(
                coords[i] for i in range(len(coords)) if i not in drop
            )
            glyph.flags = newFlags
            glyph.endPtsOfContours = newEndPts

    return drop if drop is not None else set()


class GlyphComponent(object):
    """Represents a component within a composite glyph.

    The component is represented internally with four attributes: ``glyphName``,
    ``x``, ``y`` and ``transform``. If there is no "two-by-two" matrix (i.e
    no scaling, reflection, or rotation; only translation), the ``transform``
    attribute is not present.
    """

    # The above documentation is not *completely* true, but is *true enough* because
    # the rare firstPt/lastPt attributes are not totally supported and nobody seems to
    # mind - see below.

    def __init__(self):
        pass

    def getComponentInfo(self):
        """Return information about the component

        This method returns a tuple of two values: the glyph name of the component's
        base glyph, and a transformation matrix. As opposed to accessing the attributes
        directly, ``getComponentInfo`` always returns a six-element tuple of the
        component's transformation matrix, even when the two-by-two ``.transform``
        matrix is not present.
        """
        # XXX Ignoring self.firstPt & self.lastpt for now: I need to implement
        # something equivalent in fontTools.objects.glyph (I'd rather not
        # convert it to an absolute offset, since it is valuable information).
        # This method will now raise "AttributeError: x" on glyphs that use
        # this TT feature.
        if hasattr(self, "transform"):
            [[xx, xy], [yx, yy]] = self.transform
            trans = (xx, xy, yx, yy, self.x, self.y)
        else:
            trans = (1, 0, 0, 1, self.x, self.y)
        return self.glyphName, trans

    def decompile(self, data, glyfTable):
        flags, glyphID = struct.unpack(">HH", data[:4])
        self.flags = int(flags)
        glyphID = int(glyphID)
        self.glyphName = glyfTable.getGlyphName(int(glyphID))
        data = data[4:]

        if self.flags & ARG_1_AND_2_ARE_WORDS:
            if self.flags & ARGS_ARE_XY_VALUES:
                self.x, self.y = struct.unpack(">hh", data[:4])
            else:
                x, y = struct.unpack(">HH", data[:4])
                self.firstPt, self.secondPt = int(x), int(y)
            data = data[4:]
        else:
            if self.flags & ARGS_ARE_XY_VALUES:
                self.x, self.y = struct.unpack(">bb", data[:2])
            else:
                x, y = struct.unpack(">BB", data[:2])
                self.firstPt, self.secondPt = int(x), int(y)
            data = data[2:]

        if self.flags & WE_HAVE_A_SCALE:
            (scale,) = struct.unpack(">h", data[:2])
            self.transform = [
                [fi2fl(scale, 14), 0],
                [0, fi2fl(scale, 14)],
            ]  # fixed 2.14
            data = data[2:]
        elif self.flags & WE_HAVE_AN_X_AND_Y_SCALE:
            xscale, yscale = struct.unpack(">hh", data[:4])
            self.transform = [
                [fi2fl(xscale, 14), 0],
                [0, fi2fl(yscale, 14)],
            ]  # fixed 2.14
            data = data[4:]
        elif self.flags & WE_HAVE_A_TWO_BY_TWO:
            (xscale, scale01, scale10, yscale) = struct.unpack(">hhhh", data[:8])
            self.transform = [
                [fi2fl(xscale, 14), fi2fl(scale01, 14)],
                [fi2fl(scale10, 14), fi2fl(yscale, 14)],
            ]  # fixed 2.14
            data = data[8:]
        more = self.flags & MORE_COMPONENTS
        haveInstructions = self.flags & WE_HAVE_INSTRUCTIONS
        self.flags = self.flags & (
            ROUND_XY_TO_GRID
            | USE_MY_METRICS
            | SCALED_COMPONENT_OFFSET
            | UNSCALED_COMPONENT_OFFSET
            | NON_OVERLAPPING
            | OVERLAP_COMPOUND
        )
        return more, haveInstructions, data

    def compile(self, more, haveInstructions, glyfTable):
        data = b""

        # reset all flags we will calculate ourselves
        flags = self.flags & (
            ROUND_XY_TO_GRID
            | USE_MY_METRICS
            | SCALED_COMPONENT_OFFSET
            | UNSCALED_COMPONENT_OFFSET
            | NON_OVERLAPPING
            | OVERLAP_COMPOUND
        )
        if more:
            flags = flags | MORE_COMPONENTS
        if haveInstructions:
            flags = flags | WE_HAVE_INSTRUCTIONS

        if hasattr(self, "firstPt"):
            if (0 <= self.firstPt <= 255) and (0 <= self.secondPt <= 255):
                data = data + struct.pack(">BB", self.firstPt, self.secondPt)
            else:
                data = data + struct.pack(">HH", self.firstPt, self.secondPt)
                flags = flags | ARG_1_AND_2_ARE_WORDS
        else:
            x = otRound(self.x)
            y = otRound(self.y)
            flags = flags | ARGS_ARE_XY_VALUES
            if (-128 <= x <= 127) and (-128 <= y <= 127):
                data = data + struct.pack(">bb", x, y)
            else:
                data = data + struct.pack(">hh", x, y)
                flags = flags | ARG_1_AND_2_ARE_WORDS

        if hasattr(self, "transform"):
            transform = [[fl2fi(x, 14) for x in row] for row in self.transform]
            if transform[0][1] or transform[1][0]:
                flags = flags | WE_HAVE_A_TWO_BY_TWO
                data = data + struct.pack(
                    ">hhhh",
                    transform[0][0],
                    transform[0][1],
                    transform[1][0],
                    transform[1][1],
                )
            elif transform[0][0] != transform[1][1]:
                flags = flags | WE_HAVE_AN_X_AND_Y_SCALE
                data = data + struct.pack(">hh", transform[0][0], transform[1][1])
            else:
                flags = flags | WE_HAVE_A_SCALE
                data = data + struct.pack(">h", transform[0][0])

        glyphID = glyfTable.getGlyphID(self.glyphName)
        return struct.pack(">HH", flags, glyphID) + data

    def toXML(self, writer, ttFont):
        attrs = [("glyphName", self.glyphName)]
        if not hasattr(self, "firstPt"):
            attrs = attrs + [("x", self.x), ("y", self.y)]
        else:
            attrs = attrs + [("firstPt", self.firstPt), ("secondPt", self.secondPt)]

        if hasattr(self, "transform"):
            transform = self.transform
            if transform[0][1] or transform[1][0]:
                attrs = attrs + [
                    ("scalex", fl2str(transform[0][0], 14)),
                    ("scale01", fl2str(transform[0][1], 14)),
                    ("scale10", fl2str(transform[1][0], 14)),
                    ("scaley", fl2str(transform[1][1], 14)),
                ]
            elif transform[0][0] != transform[1][1]:
                attrs = attrs + [
                    ("scalex", fl2str(transform[0][0], 14)),
                    ("scaley", fl2str(transform[1][1], 14)),
                ]
            else:
                attrs = attrs + [("scale", fl2str(transform[0][0], 14))]
        attrs = attrs + [("flags", hex(self.flags))]
        writer.simpletag("component", attrs)
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        self.glyphName = attrs["glyphName"]
        if "firstPt" in attrs:
            self.firstPt = safeEval(attrs["firstPt"])
            self.secondPt = safeEval(attrs["secondPt"])
        else:
            self.x = safeEval(attrs["x"])
            self.y = safeEval(attrs["y"])
        if "scale01" in attrs:
            scalex = str2fl(attrs["scalex"], 14)
            scale01 = str2fl(attrs["scale01"], 14)
            scale10 = str2fl(attrs["scale10"], 14)
            scaley = str2fl(attrs["scaley"], 14)
            self.transform = [[scalex, scale01], [scale10, scaley]]
        elif "scalex" in attrs:
            scalex = str2fl(attrs["scalex"], 14)
            scaley = str2fl(attrs["scaley"], 14)
            self.transform = [[scalex, 0], [0, scaley]]
        elif "scale" in attrs:
            scale = str2fl(attrs["scale"], 14)
            self.transform = [[scale, 0], [0, scale]]
        self.flags = safeEval(attrs["flags"])

    def __eq__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        result = self.__eq__(other)
        return result if result is NotImplemented else not result

    def _hasOnlyIntegerTranslate(self):
        """Return True if it's a 'simple' component.

        That is, it has no anchor points and no transform other than integer translate.
        """
        return (
            not hasattr(self, "firstPt")
            and not hasattr(self, "transform")
            and float(self.x).is_integer()
            and float(self.y).is_integer()
        )


class GlyphCoordinates(object):
    """A list of glyph coordinates.

    Unlike an ordinary list, this is a numpy-like matrix object which supports
    matrix addition, scalar multiplication and other operations described below.
    """

    def __init__(self, iterable=[]):
        self._a = array.array("d")
        self.extend(iterable)

    @property
    def array(self):
        """Returns the underlying array of coordinates"""
        return self._a

    @staticmethod
    def zeros(count):
        """Creates a new ``GlyphCoordinates`` object with all coordinates set to (0,0)"""
        g = GlyphCoordinates()
        g._a.frombytes(bytes(count * 2 * g._a.itemsize))
        return g

    def copy(self):
        """Creates a new ``GlyphCoordinates`` object which is a copy of the current one."""
        c = GlyphCoordinates()
        c._a.extend(self._a)
        return c

    def __len__(self):
        """Returns the number of coordinates in the array."""
        return len(self._a) // 2

    def __getitem__(self, k):
        """Returns a two element tuple (x,y)"""
        a = self._a
        if isinstance(k, slice):
            indices = range(*k.indices(len(self)))
            # Instead of calling ourselves recursively, duplicate code; faster
            ret = []
            for k in indices:
                x = a[2 * k]
                y = a[2 * k + 1]
                ret.append(
                    (int(x) if x.is_integer() else x, int(y) if y.is_integer() else y)
                )
            return ret
        x = a[2 * k]
        y = a[2 * k + 1]
        return (int(x) if x.is_integer() else x, int(y) if y.is_integer() else y)

    def __setitem__(self, k, v):
        """Sets a point's coordinates to a two element tuple (x,y)"""
        if isinstance(k, slice):
            indices = range(*k.indices(len(self)))
            # XXX This only works if len(v) == len(indices)
            for j, i in enumerate(indices):
                self[i] = v[j]
            return
        self._a[2 * k], self._a[2 * k + 1] = v

    def __delitem__(self, i):
        """Removes a point from the list"""
        i = (2 * i) % len(self._a)
        del self._a[i]
        del self._a[i]

    def __repr__(self):
        return "GlyphCoordinates([" + ",".join(str(c) for c in self) + "])"

    def append(self, p):
        self._a.extend(tuple(p))

    def extend(self, iterable):
        for p in iterable:
            self._a.extend(p)

    def toInt(self, *, round=otRound):
        if round is noRound:
            return
        a = self._a
        for i in range(len(a)):
            a[i] = round(a[i])

    def calcBounds(self):
        a = self._a
        if not a:
            return 0, 0, 0, 0
        xs = a[0::2]
        ys = a[1::2]
        return min(xs), min(ys), max(xs), max(ys)

    def calcIntBounds(self, round=otRound):
        return tuple(round(v) for v in self.calcBounds())

    def relativeToAbsolute(self):
        a = self._a
        x, y = 0, 0
        for i in range(0, len(a), 2):
            a[i] = x = a[i] + x
            a[i + 1] = y = a[i + 1] + y

    def absoluteToRelative(self):
        a = self._a
        x, y = 0, 0
        for i in range(0, len(a), 2):
            nx = a[i]
            ny = a[i + 1]
            a[i] = nx - x
            a[i + 1] = ny - y
            x = nx
            y = ny

    def translate(self, p):
        """
        >>> GlyphCoordinates([(1,2)]).translate((.5,0))
        """
        x, y = p
        if x == 0 and y == 0:
            return
        a = self._a
        for i in range(0, len(a), 2):
            a[i] += x
            a[i + 1] += y

    def scale(self, p):
        """
        >>> GlyphCoordinates([(1,2)]).scale((.5,0))
        """
        x, y = p
        if x == 1 and y == 1:
            return
        a = self._a
        for i in range(0, len(a), 2):
            a[i] *= x
            a[i + 1] *= y

    def transform(self, t):
        """
        >>> GlyphCoordinates([(1,2)]).transform(((.5,0),(.2,.5)))
        """
        a = self._a
        for i in range(0, len(a), 2):
            x = a[i]
            y = a[i + 1]
            px = x * t[0][0] + y * t[1][0]
            py = x * t[0][1] + y * t[1][1]
            a[i] = px
            a[i + 1] = py

    def __eq__(self, other):
        """
        >>> g = GlyphCoordinates([(1,2)])
        >>> g2 = GlyphCoordinates([(1.0,2)])
        >>> g3 = GlyphCoordinates([(1.5,2)])
        >>> g == g2
        True
        >>> g == g3
        False
        >>> g2 == g3
        False
        """
        if type(self) != type(other):
            return NotImplemented
        return self._a == other._a

    def __ne__(self, other):
        """
        >>> g = GlyphCoordinates([(1,2)])
        >>> g2 = GlyphCoordinates([(1.0,2)])
        >>> g3 = GlyphCoordinates([(1.5,2)])
        >>> g != g2
        False
        >>> g != g3
        True
        >>> g2 != g3
        True
        """
        result = self.__eq__(other)
        return result if result is NotImplemented else not result

    # Math operations

    def __pos__(self):
        """
        >>> g = GlyphCoordinates([(1,2)])
        >>> g
        GlyphCoordinates([(1, 2)])
        >>> g2 = +g
        >>> g2
        GlyphCoordinates([(1, 2)])
        >>> g2.translate((1,0))
        >>> g2
        GlyphCoordinates([(2, 2)])
        >>> g
        GlyphCoordinates([(1, 2)])
        """
        return self.copy()

    def __neg__(self):
        """
        >>> g = GlyphCoordinates([(1,2)])
        >>> g
        GlyphCoordinates([(1, 2)])
        >>> g2 = -g
        >>> g2
        GlyphCoordinates([(-1, -2)])
        >>> g
        GlyphCoordinates([(1, 2)])
        """
        r = self.copy()
        a = r._a
        for i in range(len(a)):
            a[i] = -a[i]
        return r

    def __round__(self, *, round=otRound):
        r = self.copy()
        r.toInt(round=round)
        return r

    def __add__(self, other):
        return self.copy().__iadd__(other)

    def __sub__(self, other):
        return self.copy().__isub__(other)

    def __mul__(self, other):
        return self.copy().__imul__(other)

    def __truediv__(self, other):
        return self.copy().__itruediv__(other)

    __radd__ = __add__
    __rmul__ = __mul__

    def __rsub__(self, other):
        return other + (-self)

    def __iadd__(self, other):
        """
        >>> g = GlyphCoordinates([(1,2)])
        >>> g += (.5,0)
        >>> g
        GlyphCoordinates([(1.5, 2)])
        >>> g2 = GlyphCoordinates([(3,4)])
        >>> g += g2
        >>> g
        GlyphCoordinates([(4.5, 6)])
        """
        if isinstance(other, tuple):
            assert len(other) == 2
            self.translate(other)
            return self
        if isinstance(other, GlyphCoordinates):
            other = other._a
            a = self._a
            assert len(a) == len(other)
            for i in range(len(a)):
                a[i] += other[i]
            return self
        return NotImplemented

    def __isub__(self, other):
        """
        >>> g = GlyphCoordinates([(1,2)])
        >>> g -= (.5,0)
        >>> g
        GlyphCoordinates([(0.5, 2)])
        >>> g2 = GlyphCoordinates([(3,4)])
        >>> g -= g2
        >>> g
        GlyphCoordinates([(-2.5, -2)])
        """
        if isinstance(other, tuple):
            assert len(other) == 2
            self.translate((-other[0], -other[1]))
            return self
        if isinstance(other, GlyphCoordinates):
            other = other._a
            a = self._a
            assert len(a) == len(other)
            for i in range(len(a)):
                a[i] -= other[i]
            return self
        return NotImplemented

    def __imul__(self, other):
        """
        >>> g = GlyphCoordinates([(1,2)])
        >>> g *= (2,.5)
        >>> g *= 2
        >>> g
        GlyphCoordinates([(4, 2)])
        >>> g = GlyphCoordinates([(1,2)])
        >>> g *= 2
        >>> g
        GlyphCoordinates([(2, 4)])
        """
        if isinstance(other, tuple):
            assert len(other) == 2
            self.scale(other)
            return self
        if isinstance(other, Number):
            if other == 1:
                return self
            a = self._a
            for i in range(len(a)):
                a[i] *= other
            return self
        return NotImplemented

    def __itruediv__(self, other):
        """
        >>> g = GlyphCoordinates([(1,3)])
        >>> g /= (.5,1.5)
        >>> g /= 2
        >>> g
        GlyphCoordinates([(1, 1)])
        """
        if isinstance(other, Number):
            other = (other, other)
        if isinstance(other, tuple):
            if other == (1, 1):
                return self
            assert len(other) == 2
            self.scale((1.0 / other[0], 1.0 / other[1]))
            return self
        return NotImplemented

    def __bool__(self):
        """
        >>> g = GlyphCoordinates([])
        >>> bool(g)
        False
        >>> g = GlyphCoordinates([(0,0), (0.,0)])
        >>> bool(g)
        True
        >>> g = GlyphCoordinates([(0,0), (1,0)])
        >>> bool(g)
        True
        >>> g = GlyphCoordinates([(0,.5), (0,0)])
        >>> bool(g)
        True
        """
        return bool(self._a)

    __nonzero__ = __bool__


if __name__ == "__main__":
    import doctest, sys

    sys.exit(doctest.testmod().failed)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\storage.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Storage (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import browser
from . import network
from . import page


class SerializedStorageKey(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SerializedStorageKey:
        return cls(json)

    def __repr__(self):
        return 'SerializedStorageKey({})'.format(super().__repr__())


class StorageType(enum.Enum):
    '''
    Enum of possible storage types.
    '''
    COOKIES = "cookies"
    FILE_SYSTEMS = "file_systems"
    INDEXEDDB = "indexeddb"
    LOCAL_STORAGE = "local_storage"
    SHADER_CACHE = "shader_cache"
    WEBSQL = "websql"
    SERVICE_WORKERS = "service_workers"
    CACHE_STORAGE = "cache_storage"
    INTEREST_GROUPS = "interest_groups"
    SHARED_STORAGE = "shared_storage"
    STORAGE_BUCKETS = "storage_buckets"
    ALL_ = "all"
    OTHER = "other"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class UsageForType:
    '''
    Usage for a storage type.
    '''
    #: Name of storage type.
    storage_type: StorageType

    #: Storage usage (bytes).
    usage: float

    def to_json(self):
        json = dict()
        json['storageType'] = self.storage_type.to_json()
        json['usage'] = self.usage
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            storage_type=StorageType.from_json(json['storageType']),
            usage=float(json['usage']),
        )


@dataclass
class TrustTokens:
    '''
    Pair of issuer origin and number of available (signed, but not used) Trust
    Tokens from that issuer.
    '''
    issuer_origin: str

    count: float

    def to_json(self):
        json = dict()
        json['issuerOrigin'] = self.issuer_origin
        json['count'] = self.count
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            issuer_origin=str(json['issuerOrigin']),
            count=float(json['count']),
        )


class InterestGroupAuctionId(str):
    '''
    Protected audience interest group auction identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> InterestGroupAuctionId:
        return cls(json)

    def __repr__(self):
        return 'InterestGroupAuctionId({})'.format(super().__repr__())


class InterestGroupAccessType(enum.Enum):
    '''
    Enum of interest group access types.
    '''
    JOIN = "join"
    LEAVE = "leave"
    UPDATE = "update"
    LOADED = "loaded"
    BID = "bid"
    WIN = "win"
    ADDITIONAL_BID = "additionalBid"
    ADDITIONAL_BID_WIN = "additionalBidWin"
    TOP_LEVEL_BID = "topLevelBid"
    TOP_LEVEL_ADDITIONAL_BID = "topLevelAdditionalBid"
    CLEAR = "clear"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class InterestGroupAuctionEventType(enum.Enum):
    '''
    Enum of auction events.
    '''
    STARTED = "started"
    CONFIG_RESOLVED = "configResolved"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class InterestGroupAuctionFetchType(enum.Enum):
    '''
    Enum of network fetches auctions can do.
    '''
    BIDDER_JS = "bidderJs"
    BIDDER_WASM = "bidderWasm"
    SELLER_JS = "sellerJs"
    BIDDER_TRUSTED_SIGNALS = "bidderTrustedSignals"
    SELLER_TRUSTED_SIGNALS = "sellerTrustedSignals"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SharedStorageAccessScope(enum.Enum):
    '''
    Enum of shared storage access scopes.
    '''
    WINDOW = "window"
    SHARED_STORAGE_WORKLET = "sharedStorageWorklet"
    PROTECTED_AUDIENCE_WORKLET = "protectedAudienceWorklet"
    HEADER = "header"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SharedStorageAccessMethod(enum.Enum):
    '''
    Enum of shared storage access methods.
    '''
    ADD_MODULE = "addModule"
    CREATE_WORKLET = "createWorklet"
    SELECT_URL = "selectURL"
    RUN = "run"
    BATCH_UPDATE = "batchUpdate"
    SET_ = "set"
    APPEND = "append"
    DELETE = "delete"
    CLEAR = "clear"
    GET = "get"
    KEYS = "keys"
    VALUES = "values"
    ENTRIES = "entries"
    LENGTH = "length"
    REMAINING_BUDGET = "remainingBudget"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class SharedStorageEntry:
    '''
    Struct for a single key-value pair in an origin's shared storage.
    '''
    key: str

    value: str

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            value=str(json['value']),
        )


@dataclass
class SharedStorageMetadata:
    '''
    Details for an origin's shared storage.
    '''
    #: Time when the origin's shared storage was last created.
    creation_time: network.TimeSinceEpoch

    #: Number of key-value pairs stored in origin's shared storage.
    length: int

    #: Current amount of bits of entropy remaining in the navigation budget.
    remaining_budget: float

    #: Total number of bytes stored as key-value pairs in origin's shared
    #: storage.
    bytes_used: int

    def to_json(self):
        json = dict()
        json['creationTime'] = self.creation_time.to_json()
        json['length'] = self.length
        json['remainingBudget'] = self.remaining_budget
        json['bytesUsed'] = self.bytes_used
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            creation_time=network.TimeSinceEpoch.from_json(json['creationTime']),
            length=int(json['length']),
            remaining_budget=float(json['remainingBudget']),
            bytes_used=int(json['bytesUsed']),
        )


@dataclass
class SharedStoragePrivateAggregationConfig:
    '''
    Represents a dictionary object passed in as privateAggregationConfig to
    run or selectURL.
    '''
    #: Configures the maximum size allowed for filtering IDs.
    filtering_id_max_bytes: int

    #: The chosen aggregation service deployment.
    aggregation_coordinator_origin: typing.Optional[str] = None

    #: The context ID provided.
    context_id: typing.Optional[str] = None

    #: The limit on the number of contributions in the final report.
    max_contributions: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        json['filteringIdMaxBytes'] = self.filtering_id_max_bytes
        if self.aggregation_coordinator_origin is not None:
            json['aggregationCoordinatorOrigin'] = self.aggregation_coordinator_origin
        if self.context_id is not None:
            json['contextId'] = self.context_id
        if self.max_contributions is not None:
            json['maxContributions'] = self.max_contributions
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            filtering_id_max_bytes=int(json['filteringIdMaxBytes']),
            aggregation_coordinator_origin=str(json['aggregationCoordinatorOrigin']) if 'aggregationCoordinatorOrigin' in json else None,
            context_id=str(json['contextId']) if 'contextId' in json else None,
            max_contributions=int(json['maxContributions']) if 'maxContributions' in json else None,
        )


@dataclass
class SharedStorageReportingMetadata:
    '''
    Pair of reporting metadata details for a candidate URL for ``selectURL()``.
    '''
    event_type: str

    reporting_url: str

    def to_json(self):
        json = dict()
        json['eventType'] = self.event_type
        json['reportingUrl'] = self.reporting_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            event_type=str(json['eventType']),
            reporting_url=str(json['reportingUrl']),
        )


@dataclass
class SharedStorageUrlWithMetadata:
    '''
    Bundles a candidate URL with its reporting metadata.
    '''
    #: Spec of candidate URL.
    url: str

    #: Any associated reporting metadata.
    reporting_metadata: typing.List[SharedStorageReportingMetadata]

    def to_json(self):
        json = dict()
        json['url'] = self.url
        json['reportingMetadata'] = [i.to_json() for i in self.reporting_metadata]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            url=str(json['url']),
            reporting_metadata=[SharedStorageReportingMetadata.from_json(i) for i in json['reportingMetadata']],
        )


@dataclass
class SharedStorageAccessParams:
    '''
    Bundles the parameters for shared storage access events whose
    presence/absence can vary according to SharedStorageAccessType.
    '''
    #: Spec of the module script URL.
    #: Present only for SharedStorageAccessMethods: addModule and
    #: createWorklet.
    script_source_url: typing.Optional[str] = None

    #: String denoting "context-origin", "script-origin", or a custom
    #: origin to be used as the worklet's data origin.
    #: Present only for SharedStorageAccessMethod: createWorklet.
    data_origin: typing.Optional[str] = None

    #: Name of the registered operation to be run.
    #: Present only for SharedStorageAccessMethods: run and selectURL.
    operation_name: typing.Optional[str] = None

    #: Whether or not to keep the worket alive for future run or selectURL
    #: calls.
    #: Present only for SharedStorageAccessMethods: run and selectURL.
    keep_alive: typing.Optional[bool] = None

    #: Configures the private aggregation options.
    #: Present only for SharedStorageAccessMethods: run and selectURL.
    private_aggregation_config: typing.Optional[SharedStoragePrivateAggregationConfig] = None

    #: The operation's serialized data in bytes (converted to a string).
    #: Present only for SharedStorageAccessMethods: run and selectURL.
    #: TODO(crbug.com/401011862): Consider updating this parameter to binary.
    serialized_data: typing.Optional[str] = None

    #: Array of candidate URLs' specs, along with any associated metadata.
    #: Present only for SharedStorageAccessMethod: selectURL.
    urls_with_metadata: typing.Optional[typing.List[SharedStorageUrlWithMetadata]] = None

    #: Spec of the URN:UUID generated for a selectURL call.
    #: Present only for SharedStorageAccessMethod: selectURL.
    urn_uuid: typing.Optional[str] = None

    #: Key for a specific entry in an origin's shared storage.
    #: Present only for SharedStorageAccessMethods: set, append, delete, and
    #: get.
    key: typing.Optional[str] = None

    #: Value for a specific entry in an origin's shared storage.
    #: Present only for SharedStorageAccessMethods: set and append.
    value: typing.Optional[str] = None

    #: Whether or not to set an entry for a key if that key is already present.
    #: Present only for SharedStorageAccessMethod: set.
    ignore_if_present: typing.Optional[bool] = None

    #: If the method is called on a worklet, or as part of
    #: a worklet script, it will have an ID for the associated worklet.
    #: Present only for SharedStorageAccessMethods: addModule, createWorklet,
    #: run, selectURL, and any other SharedStorageAccessMethod when the
    #: SharedStorageAccessScope is worklet.
    worklet_id: typing.Optional[str] = None

    #: Name of the lock to be acquired, if present.
    #: Optionally present only for SharedStorageAccessMethods: batchUpdate,
    #: set, append, delete, and clear.
    with_lock: typing.Optional[str] = None

    #: If the method has been called as part of a batchUpdate, then this
    #: number identifies the batch to which it belongs.
    #: Optionally present only for SharedStorageAccessMethods:
    #: batchUpdate (required), set, append, delete, and clear.
    batch_update_id: typing.Optional[str] = None

    #: Number of modifier methods sent in batch.
    #: Present only for SharedStorageAccessMethod: batchUpdate.
    batch_size: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        if self.script_source_url is not None:
            json['scriptSourceUrl'] = self.script_source_url
        if self.data_origin is not None:
            json['dataOrigin'] = self.data_origin
        if self.operation_name is not None:
            json['operationName'] = self.operation_name
        if self.keep_alive is not None:
            json['keepAlive'] = self.keep_alive
        if self.private_aggregation_config is not None:
            json['privateAggregationConfig'] = self.private_aggregation_config.to_json()
        if self.serialized_data is not None:
            json['serializedData'] = self.serialized_data
        if self.urls_with_metadata is not None:
            json['urlsWithMetadata'] = [i.to_json() for i in self.urls_with_metadata]
        if self.urn_uuid is not None:
            json['urnUuid'] = self.urn_uuid
        if self.key is not None:
            json['key'] = self.key
        if self.value is not None:
            json['value'] = self.value
        if self.ignore_if_present is not None:
            json['ignoreIfPresent'] = self.ignore_if_present
        if self.worklet_id is not None:
            json['workletId'] = self.worklet_id
        if self.with_lock is not None:
            json['withLock'] = self.with_lock
        if self.batch_update_id is not None:
            json['batchUpdateId'] = self.batch_update_id
        if self.batch_size is not None:
            json['batchSize'] = self.batch_size
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_source_url=str(json['scriptSourceUrl']) if 'scriptSourceUrl' in json else None,
            data_origin=str(json['dataOrigin']) if 'dataOrigin' in json else None,
            operation_name=str(json['operationName']) if 'operationName' in json else None,
            keep_alive=bool(json['keepAlive']) if 'keepAlive' in json else None,
            private_aggregation_config=SharedStoragePrivateAggregationConfig.from_json(json['privateAggregationConfig']) if 'privateAggregationConfig' in json else None,
            serialized_data=str(json['serializedData']) if 'serializedData' in json else None,
            urls_with_metadata=[SharedStorageUrlWithMetadata.from_json(i) for i in json['urlsWithMetadata']] if 'urlsWithMetadata' in json else None,
            urn_uuid=str(json['urnUuid']) if 'urnUuid' in json else None,
            key=str(json['key']) if 'key' in json else None,
            value=str(json['value']) if 'value' in json else None,
            ignore_if_present=bool(json['ignoreIfPresent']) if 'ignoreIfPresent' in json else None,
            worklet_id=str(json['workletId']) if 'workletId' in json else None,
            with_lock=str(json['withLock']) if 'withLock' in json else None,
            batch_update_id=str(json['batchUpdateId']) if 'batchUpdateId' in json else None,
            batch_size=int(json['batchSize']) if 'batchSize' in json else None,
        )


class StorageBucketsDurability(enum.Enum):
    RELAXED = "relaxed"
    STRICT = "strict"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class StorageBucket:
    storage_key: SerializedStorageKey

    #: If not specified, it is the default bucket of the storageKey.
    name: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['storageKey'] = self.storage_key.to_json()
        if self.name is not None:
            json['name'] = self.name
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            storage_key=SerializedStorageKey.from_json(json['storageKey']),
            name=str(json['name']) if 'name' in json else None,
        )


@dataclass
class StorageBucketInfo:
    bucket: StorageBucket

    id_: str

    expiration: network.TimeSinceEpoch

    #: Storage quota (bytes).
    quota: float

    persistent: bool

    durability: StorageBucketsDurability

    def to_json(self):
        json = dict()
        json['bucket'] = self.bucket.to_json()
        json['id'] = self.id_
        json['expiration'] = self.expiration.to_json()
        json['quota'] = self.quota
        json['persistent'] = self.persistent
        json['durability'] = self.durability.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            bucket=StorageBucket.from_json(json['bucket']),
            id_=str(json['id']),
            expiration=network.TimeSinceEpoch.from_json(json['expiration']),
            quota=float(json['quota']),
            persistent=bool(json['persistent']),
            durability=StorageBucketsDurability.from_json(json['durability']),
        )


class AttributionReportingSourceType(enum.Enum):
    NAVIGATION = "navigation"
    EVENT = "event"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class UnsignedInt64AsBase10(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> UnsignedInt64AsBase10:
        return cls(json)

    def __repr__(self):
        return 'UnsignedInt64AsBase10({})'.format(super().__repr__())


class UnsignedInt128AsBase16(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> UnsignedInt128AsBase16:
        return cls(json)

    def __repr__(self):
        return 'UnsignedInt128AsBase16({})'.format(super().__repr__())


class SignedInt64AsBase10(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SignedInt64AsBase10:
        return cls(json)

    def __repr__(self):
        return 'SignedInt64AsBase10({})'.format(super().__repr__())


@dataclass
class AttributionReportingFilterDataEntry:
    key: str

    values: typing.List[str]

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['values'] = [i for i in self.values]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            values=[str(i) for i in json['values']],
        )


@dataclass
class AttributionReportingFilterConfig:
    filter_values: typing.List[AttributionReportingFilterDataEntry]

    #: duration in seconds
    lookback_window: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        json['filterValues'] = [i.to_json() for i in self.filter_values]
        if self.lookback_window is not None:
            json['lookbackWindow'] = self.lookback_window
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            filter_values=[AttributionReportingFilterDataEntry.from_json(i) for i in json['filterValues']],
            lookback_window=int(json['lookbackWindow']) if 'lookbackWindow' in json else None,
        )


@dataclass
class AttributionReportingFilterPair:
    filters: typing.List[AttributionReportingFilterConfig]

    not_filters: typing.List[AttributionReportingFilterConfig]

    def to_json(self):
        json = dict()
        json['filters'] = [i.to_json() for i in self.filters]
        json['notFilters'] = [i.to_json() for i in self.not_filters]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            filters=[AttributionReportingFilterConfig.from_json(i) for i in json['filters']],
            not_filters=[AttributionReportingFilterConfig.from_json(i) for i in json['notFilters']],
        )


@dataclass
class AttributionReportingAggregationKeysEntry:
    key: str

    value: UnsignedInt128AsBase16

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['value'] = self.value.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            value=UnsignedInt128AsBase16.from_json(json['value']),
        )


@dataclass
class AttributionReportingEventReportWindows:
    #: duration in seconds
    start: int

    #: duration in seconds
    ends: typing.List[int]

    def to_json(self):
        json = dict()
        json['start'] = self.start
        json['ends'] = [i for i in self.ends]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            start=int(json['start']),
            ends=[int(i) for i in json['ends']],
        )


@dataclass
class AttributionReportingTriggerSpec:
    #: number instead of integer because not all uint32 can be represented by
    #: int
    trigger_data: typing.List[float]

    event_report_windows: AttributionReportingEventReportWindows

    def to_json(self):
        json = dict()
        json['triggerData'] = [i for i in self.trigger_data]
        json['eventReportWindows'] = self.event_report_windows.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            trigger_data=[float(i) for i in json['triggerData']],
            event_report_windows=AttributionReportingEventReportWindows.from_json(json['eventReportWindows']),
        )


class AttributionReportingTriggerDataMatching(enum.Enum):
    EXACT = "exact"
    MODULUS = "modulus"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AttributionReportingAggregatableDebugReportingData:
    key_piece: UnsignedInt128AsBase16

    #: number instead of integer because not all uint32 can be represented by
    #: int
    value: float

    types: typing.List[str]

    def to_json(self):
        json = dict()
        json['keyPiece'] = self.key_piece.to_json()
        json['value'] = self.value
        json['types'] = [i for i in self.types]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key_piece=UnsignedInt128AsBase16.from_json(json['keyPiece']),
            value=float(json['value']),
            types=[str(i) for i in json['types']],
        )


@dataclass
class AttributionReportingAggregatableDebugReportingConfig:
    key_piece: UnsignedInt128AsBase16

    debug_data: typing.List[AttributionReportingAggregatableDebugReportingData]

    #: number instead of integer because not all uint32 can be represented by
    #: int, only present for source registrations
    budget: typing.Optional[float] = None

    aggregation_coordinator_origin: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['keyPiece'] = self.key_piece.to_json()
        json['debugData'] = [i.to_json() for i in self.debug_data]
        if self.budget is not None:
            json['budget'] = self.budget
        if self.aggregation_coordinator_origin is not None:
            json['aggregationCoordinatorOrigin'] = self.aggregation_coordinator_origin
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key_piece=UnsignedInt128AsBase16.from_json(json['keyPiece']),
            debug_data=[AttributionReportingAggregatableDebugReportingData.from_json(i) for i in json['debugData']],
            budget=float(json['budget']) if 'budget' in json else None,
            aggregation_coordinator_origin=str(json['aggregationCoordinatorOrigin']) if 'aggregationCoordinatorOrigin' in json else None,
        )


@dataclass
class AttributionScopesData:
    values: typing.List[str]

    #: number instead of integer because not all uint32 can be represented by
    #: int
    limit: float

    max_event_states: float

    def to_json(self):
        json = dict()
        json['values'] = [i for i in self.values]
        json['limit'] = self.limit
        json['maxEventStates'] = self.max_event_states
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            values=[str(i) for i in json['values']],
            limit=float(json['limit']),
            max_event_states=float(json['maxEventStates']),
        )


@dataclass
class AttributionReportingNamedBudgetDef:
    name: str

    budget: int

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['budget'] = self.budget
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            budget=int(json['budget']),
        )


@dataclass
class AttributionReportingSourceRegistration:
    time: network.TimeSinceEpoch

    #: duration in seconds
    expiry: int

    trigger_specs: typing.List[AttributionReportingTriggerSpec]

    #: duration in seconds
    aggregatable_report_window: int

    type_: AttributionReportingSourceType

    source_origin: str

    reporting_origin: str

    destination_sites: typing.List[str]

    event_id: UnsignedInt64AsBase10

    priority: SignedInt64AsBase10

    filter_data: typing.List[AttributionReportingFilterDataEntry]

    aggregation_keys: typing.List[AttributionReportingAggregationKeysEntry]

    trigger_data_matching: AttributionReportingTriggerDataMatching

    destination_limit_priority: SignedInt64AsBase10

    aggregatable_debug_reporting_config: AttributionReportingAggregatableDebugReportingConfig

    max_event_level_reports: int

    named_budgets: typing.List[AttributionReportingNamedBudgetDef]

    debug_reporting: bool

    event_level_epsilon: float

    debug_key: typing.Optional[UnsignedInt64AsBase10] = None

    scopes_data: typing.Optional[AttributionScopesData] = None

    def to_json(self):
        json = dict()
        json['time'] = self.time.to_json()
        json['expiry'] = self.expiry
        json['triggerSpecs'] = [i.to_json() for i in self.trigger_specs]
        json['aggregatableReportWindow'] = self.aggregatable_report_window
        json['type'] = self.type_.to_json()
        json['sourceOrigin'] = self.source_origin
        json['reportingOrigin'] = self.reporting_origin
        json['destinationSites'] = [i for i in self.destination_sites]
        json['eventId'] = self.event_id.to_json()
        json['priority'] = self.priority.to_json()
        json['filterData'] = [i.to_json() for i in self.filter_data]
        json['aggregationKeys'] = [i.to_json() for i in self.aggregation_keys]
        json['triggerDataMatching'] = self.trigger_data_matching.to_json()
        json['destinationLimitPriority'] = self.destination_limit_priority.to_json()
        json['aggregatableDebugReportingConfig'] = self.aggregatable_debug_reporting_config.to_json()
        json['maxEventLevelReports'] = self.max_event_level_reports
        json['namedBudgets'] = [i.to_json() for i in self.named_budgets]
        json['debugReporting'] = self.debug_reporting
        json['eventLevelEpsilon'] = self.event_level_epsilon
        if self.debug_key is not None:
            json['debugKey'] = self.debug_key.to_json()
        if self.scopes_data is not None:
            json['scopesData'] = self.scopes_data.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            time=network.TimeSinceEpoch.from_json(json['time']),
            expiry=int(json['expiry']),
            trigger_specs=[AttributionReportingTriggerSpec.from_json(i) for i in json['triggerSpecs']],
            aggregatable_report_window=int(json['aggregatableReportWindow']),
            type_=AttributionReportingSourceType.from_json(json['type']),
            source_origin=str(json['sourceOrigin']),
            reporting_origin=str(json['reportingOrigin']),
            destination_sites=[str(i) for i in json['destinationSites']],
            event_id=UnsignedInt64AsBase10.from_json(json['eventId']),
            priority=SignedInt64AsBase10.from_json(json['priority']),
            filter_data=[AttributionReportingFilterDataEntry.from_json(i) for i in json['filterData']],
            aggregation_keys=[AttributionReportingAggregationKeysEntry.from_json(i) for i in json['aggregationKeys']],
            trigger_data_matching=AttributionReportingTriggerDataMatching.from_json(json['triggerDataMatching']),
            destination_limit_priority=SignedInt64AsBase10.from_json(json['destinationLimitPriority']),
            aggregatable_debug_reporting_config=AttributionReportingAggregatableDebugReportingConfig.from_json(json['aggregatableDebugReportingConfig']),
            max_event_level_reports=int(json['maxEventLevelReports']),
            named_budgets=[AttributionReportingNamedBudgetDef.from_json(i) for i in json['namedBudgets']],
            debug_reporting=bool(json['debugReporting']),
            event_level_epsilon=float(json['eventLevelEpsilon']),
            debug_key=UnsignedInt64AsBase10.from_json(json['debugKey']) if 'debugKey' in json else None,
            scopes_data=AttributionScopesData.from_json(json['scopesData']) if 'scopesData' in json else None,
        )


class AttributionReportingSourceRegistrationResult(enum.Enum):
    SUCCESS = "success"
    INTERNAL_ERROR = "internalError"
    INSUFFICIENT_SOURCE_CAPACITY = "insufficientSourceCapacity"
    INSUFFICIENT_UNIQUE_DESTINATION_CAPACITY = "insufficientUniqueDestinationCapacity"
    EXCESSIVE_REPORTING_ORIGINS = "excessiveReportingOrigins"
    PROHIBITED_BY_BROWSER_POLICY = "prohibitedByBrowserPolicy"
    SUCCESS_NOISED = "successNoised"
    DESTINATION_REPORTING_LIMIT_REACHED = "destinationReportingLimitReached"
    DESTINATION_GLOBAL_LIMIT_REACHED = "destinationGlobalLimitReached"
    DESTINATION_BOTH_LIMITS_REACHED = "destinationBothLimitsReached"
    REPORTING_ORIGINS_PER_SITE_LIMIT_REACHED = "reportingOriginsPerSiteLimitReached"
    EXCEEDS_MAX_CHANNEL_CAPACITY = "exceedsMaxChannelCapacity"
    EXCEEDS_MAX_SCOPES_CHANNEL_CAPACITY = "exceedsMaxScopesChannelCapacity"
    EXCEEDS_MAX_TRIGGER_STATE_CARDINALITY = "exceedsMaxTriggerStateCardinality"
    EXCEEDS_MAX_EVENT_STATES_LIMIT = "exceedsMaxEventStatesLimit"
    DESTINATION_PER_DAY_REPORTING_LIMIT_REACHED = "destinationPerDayReportingLimitReached"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AttributionReportingSourceRegistrationTimeConfig(enum.Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class AttributionReportingAggregatableValueDictEntry:
    key: str

    #: number instead of integer because not all uint32 can be represented by
    #: int
    value: float

    filtering_id: UnsignedInt64AsBase10

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['value'] = self.value
        json['filteringId'] = self.filtering_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=str(json['key']),
            value=float(json['value']),
            filtering_id=UnsignedInt64AsBase10.from_json(json['filteringId']),
        )


@dataclass
class AttributionReportingAggregatableValueEntry:
    values: typing.List[AttributionReportingAggregatableValueDictEntry]

    filters: AttributionReportingFilterPair

    def to_json(self):
        json = dict()
        json['values'] = [i.to_json() for i in self.values]
        json['filters'] = self.filters.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            values=[AttributionReportingAggregatableValueDictEntry.from_json(i) for i in json['values']],
            filters=AttributionReportingFilterPair.from_json(json['filters']),
        )


@dataclass
class AttributionReportingEventTriggerData:
    data: UnsignedInt64AsBase10

    priority: SignedInt64AsBase10

    filters: AttributionReportingFilterPair

    dedup_key: typing.Optional[UnsignedInt64AsBase10] = None

    def to_json(self):
        json = dict()
        json['data'] = self.data.to_json()
        json['priority'] = self.priority.to_json()
        json['filters'] = self.filters.to_json()
        if self.dedup_key is not None:
            json['dedupKey'] = self.dedup_key.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            data=UnsignedInt64AsBase10.from_json(json['data']),
            priority=SignedInt64AsBase10.from_json(json['priority']),
            filters=AttributionReportingFilterPair.from_json(json['filters']),
            dedup_key=UnsignedInt64AsBase10.from_json(json['dedupKey']) if 'dedupKey' in json else None,
        )


@dataclass
class AttributionReportingAggregatableTriggerData:
    key_piece: UnsignedInt128AsBase16

    source_keys: typing.List[str]

    filters: AttributionReportingFilterPair

    def to_json(self):
        json = dict()
        json['keyPiece'] = self.key_piece.to_json()
        json['sourceKeys'] = [i for i in self.source_keys]
        json['filters'] = self.filters.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key_piece=UnsignedInt128AsBase16.from_json(json['keyPiece']),
            source_keys=[str(i) for i in json['sourceKeys']],
            filters=AttributionReportingFilterPair.from_json(json['filters']),
        )


@dataclass
class AttributionReportingAggregatableDedupKey:
    filters: AttributionReportingFilterPair

    dedup_key: typing.Optional[UnsignedInt64AsBase10] = None

    def to_json(self):
        json = dict()
        json['filters'] = self.filters.to_json()
        if self.dedup_key is not None:
            json['dedupKey'] = self.dedup_key.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            filters=AttributionReportingFilterPair.from_json(json['filters']),
            dedup_key=UnsignedInt64AsBase10.from_json(json['dedupKey']) if 'dedupKey' in json else None,
        )


@dataclass
class AttributionReportingNamedBudgetCandidate:
    filters: AttributionReportingFilterPair

    name: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['filters'] = self.filters.to_json()
        if self.name is not None:
            json['name'] = self.name
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            filters=AttributionReportingFilterPair.from_json(json['filters']),
            name=str(json['name']) if 'name' in json else None,
        )


@dataclass
class AttributionReportingTriggerRegistration:
    filters: AttributionReportingFilterPair

    aggregatable_dedup_keys: typing.List[AttributionReportingAggregatableDedupKey]

    event_trigger_data: typing.List[AttributionReportingEventTriggerData]

    aggregatable_trigger_data: typing.List[AttributionReportingAggregatableTriggerData]

    aggregatable_values: typing.List[AttributionReportingAggregatableValueEntry]

    aggregatable_filtering_id_max_bytes: int

    debug_reporting: bool

    source_registration_time_config: AttributionReportingSourceRegistrationTimeConfig

    aggregatable_debug_reporting_config: AttributionReportingAggregatableDebugReportingConfig

    scopes: typing.List[str]

    named_budgets: typing.List[AttributionReportingNamedBudgetCandidate]

    debug_key: typing.Optional[UnsignedInt64AsBase10] = None

    aggregation_coordinator_origin: typing.Optional[str] = None

    trigger_context_id: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['filters'] = self.filters.to_json()
        json['aggregatableDedupKeys'] = [i.to_json() for i in self.aggregatable_dedup_keys]
        json['eventTriggerData'] = [i.to_json() for i in self.event_trigger_data]
        json['aggregatableTriggerData'] = [i.to_json() for i in self.aggregatable_trigger_data]
        json['aggregatableValues'] = [i.to_json() for i in self.aggregatable_values]
        json['aggregatableFilteringIdMaxBytes'] = self.aggregatable_filtering_id_max_bytes
        json['debugReporting'] = self.debug_reporting
        json['sourceRegistrationTimeConfig'] = self.source_registration_time_config.to_json()
        json['aggregatableDebugReportingConfig'] = self.aggregatable_debug_reporting_config.to_json()
        json['scopes'] = [i for i in self.scopes]
        json['namedBudgets'] = [i.to_json() for i in self.named_budgets]
        if self.debug_key is not None:
            json['debugKey'] = self.debug_key.to_json()
        if self.aggregation_coordinator_origin is not None:
            json['aggregationCoordinatorOrigin'] = self.aggregation_coordinator_origin
        if self.trigger_context_id is not None:
            json['triggerContextId'] = self.trigger_context_id
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            filters=AttributionReportingFilterPair.from_json(json['filters']),
            aggregatable_dedup_keys=[AttributionReportingAggregatableDedupKey.from_json(i) for i in json['aggregatableDedupKeys']],
            event_trigger_data=[AttributionReportingEventTriggerData.from_json(i) for i in json['eventTriggerData']],
            aggregatable_trigger_data=[AttributionReportingAggregatableTriggerData.from_json(i) for i in json['aggregatableTriggerData']],
            aggregatable_values=[AttributionReportingAggregatableValueEntry.from_json(i) for i in json['aggregatableValues']],
            aggregatable_filtering_id_max_bytes=int(json['aggregatableFilteringIdMaxBytes']),
            debug_reporting=bool(json['debugReporting']),
            source_registration_time_config=AttributionReportingSourceRegistrationTimeConfig.from_json(json['sourceRegistrationTimeConfig']),
            aggregatable_debug_reporting_config=AttributionReportingAggregatableDebugReportingConfig.from_json(json['aggregatableDebugReportingConfig']),
            scopes=[str(i) for i in json['scopes']],
            named_budgets=[AttributionReportingNamedBudgetCandidate.from_json(i) for i in json['namedBudgets']],
            debug_key=UnsignedInt64AsBase10.from_json(json['debugKey']) if 'debugKey' in json else None,
            aggregation_coordinator_origin=str(json['aggregationCoordinatorOrigin']) if 'aggregationCoordinatorOrigin' in json else None,
            trigger_context_id=str(json['triggerContextId']) if 'triggerContextId' in json else None,
        )


class AttributionReportingEventLevelResult(enum.Enum):
    SUCCESS = "success"
    SUCCESS_DROPPED_LOWER_PRIORITY = "successDroppedLowerPriority"
    INTERNAL_ERROR = "internalError"
    NO_CAPACITY_FOR_ATTRIBUTION_DESTINATION = "noCapacityForAttributionDestination"
    NO_MATCHING_SOURCES = "noMatchingSources"
    DEDUPLICATED = "deduplicated"
    EXCESSIVE_ATTRIBUTIONS = "excessiveAttributions"
    PRIORITY_TOO_LOW = "priorityTooLow"
    NEVER_ATTRIBUTED_SOURCE = "neverAttributedSource"
    EXCESSIVE_REPORTING_ORIGINS = "excessiveReportingOrigins"
    NO_MATCHING_SOURCE_FILTER_DATA = "noMatchingSourceFilterData"
    PROHIBITED_BY_BROWSER_POLICY = "prohibitedByBrowserPolicy"
    NO_MATCHING_CONFIGURATIONS = "noMatchingConfigurations"
    EXCESSIVE_REPORTS = "excessiveReports"
    FALSELY_ATTRIBUTED_SOURCE = "falselyAttributedSource"
    REPORT_WINDOW_PASSED = "reportWindowPassed"
    NOT_REGISTERED = "notRegistered"
    REPORT_WINDOW_NOT_STARTED = "reportWindowNotStarted"
    NO_MATCHING_TRIGGER_DATA = "noMatchingTriggerData"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AttributionReportingAggregatableResult(enum.Enum):
    SUCCESS = "success"
    INTERNAL_ERROR = "internalError"
    NO_CAPACITY_FOR_ATTRIBUTION_DESTINATION = "noCapacityForAttributionDestination"
    NO_MATCHING_SOURCES = "noMatchingSources"
    EXCESSIVE_ATTRIBUTIONS = "excessiveAttributions"
    EXCESSIVE_REPORTING_ORIGINS = "excessiveReportingOrigins"
    NO_HISTOGRAMS = "noHistograms"
    INSUFFICIENT_BUDGET = "insufficientBudget"
    INSUFFICIENT_NAMED_BUDGET = "insufficientNamedBudget"
    NO_MATCHING_SOURCE_FILTER_DATA = "noMatchingSourceFilterData"
    NOT_REGISTERED = "notRegistered"
    PROHIBITED_BY_BROWSER_POLICY = "prohibitedByBrowserPolicy"
    DEDUPLICATED = "deduplicated"
    REPORT_WINDOW_PASSED = "reportWindowPassed"
    EXCESSIVE_REPORTS = "excessiveReports"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class RelatedWebsiteSet:
    '''
    A single Related Website Set object.
    '''
    #: The primary site of this set, along with the ccTLDs if there is any.
    primary_sites: typing.List[str]

    #: The associated sites of this set, along with the ccTLDs if there is any.
    associated_sites: typing.List[str]

    #: The service sites of this set, along with the ccTLDs if there is any.
    service_sites: typing.List[str]

    def to_json(self):
        json = dict()
        json['primarySites'] = [i for i in self.primary_sites]
        json['associatedSites'] = [i for i in self.associated_sites]
        json['serviceSites'] = [i for i in self.service_sites]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            primary_sites=[str(i) for i in json['primarySites']],
            associated_sites=[str(i) for i in json['associatedSites']],
            service_sites=[str(i) for i in json['serviceSites']],
        )


def get_storage_key_for_frame(
        frame_id: page.FrameId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SerializedStorageKey]:
    '''
    Returns a storage key given a frame id.

    :param frame_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['frameId'] = frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getStorageKeyForFrame',
        'params': params,
    }
    json = yield cmd_dict
    return SerializedStorageKey.from_json(json['storageKey'])


def clear_data_for_origin(
        origin: str,
        storage_types: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears storage for origin.

    :param origin: Security origin.
    :param storage_types: Comma separated list of StorageType to clear.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    params['storageTypes'] = storage_types
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearDataForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def clear_data_for_storage_key(
        storage_key: str,
        storage_types: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears storage for storage key.

    :param storage_key: Storage key.
    :param storage_types: Comma separated list of StorageType to clear.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    params['storageTypes'] = storage_types
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearDataForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def get_cookies(
        browser_context_id: typing.Optional[browser.BrowserContextID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[network.Cookie]]:
    '''
    Returns all browser cookies.

    :param browser_context_id: *(Optional)* Browser context to use when called on the browser endpoint.
    :returns: Array of cookie objects.
    '''
    params: T_JSON_DICT = dict()
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getCookies',
        'params': params,
    }
    json = yield cmd_dict
    return [network.Cookie.from_json(i) for i in json['cookies']]


def set_cookies(
        cookies: typing.List[network.CookieParam],
        browser_context_id: typing.Optional[browser.BrowserContextID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets given cookies.

    :param cookies: Cookies to be set.
    :param browser_context_id: *(Optional)* Browser context to use when called on the browser endpoint.
    '''
    params: T_JSON_DICT = dict()
    params['cookies'] = [i.to_json() for i in cookies]
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setCookies',
        'params': params,
    }
    json = yield cmd_dict


def clear_cookies(
        browser_context_id: typing.Optional[browser.BrowserContextID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears cookies.

    :param browser_context_id: *(Optional)* Browser context to use when called on the browser endpoint.
    '''
    params: T_JSON_DICT = dict()
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearCookies',
        'params': params,
    }
    json = yield cmd_dict


def get_usage_and_quota(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[float, float, bool, typing.List[UsageForType]]]:
    '''
    Returns usage and quota in bytes.

    :param origin: Security origin.
    :returns: A tuple with the following items:

        0. **usage** - Storage usage (bytes).
        1. **quota** - Storage quota (bytes).
        2. **overrideActive** - Whether or not the origin has an active storage quota override
        3. **usageBreakdown** - Storage usage per type (bytes).
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getUsageAndQuota',
        'params': params,
    }
    json = yield cmd_dict
    return (
        float(json['usage']),
        float(json['quota']),
        bool(json['overrideActive']),
        [UsageForType.from_json(i) for i in json['usageBreakdown']]
    )


def override_quota_for_origin(
        origin: str,
        quota_size: typing.Optional[float] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Override quota for the specified origin

    **EXPERIMENTAL**

    :param origin: Security origin.
    :param quota_size: *(Optional)* The quota size (in bytes) to override the original quota with. If this is called multiple times, the overridden quota will be equal to the quotaSize provided in the final call. If this is called without specifying a quotaSize, the quota will be reset to the default value for the specified origin. If this is called multiple times with different origins, the override will be maintained for each origin until it is disabled (called without a quotaSize).
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    if quota_size is not None:
        params['quotaSize'] = quota_size
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.overrideQuotaForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def track_cache_storage_for_origin(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Registers origin to be notified when an update occurs to its cache storage list.

    :param origin: Security origin.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.trackCacheStorageForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def track_cache_storage_for_storage_key(
        storage_key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Registers storage key to be notified when an update occurs to its cache storage list.

    :param storage_key: Storage key.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.trackCacheStorageForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def track_indexed_db_for_origin(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Registers origin to be notified when an update occurs to its IndexedDB.

    :param origin: Security origin.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.trackIndexedDBForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def track_indexed_db_for_storage_key(
        storage_key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Registers storage key to be notified when an update occurs to its IndexedDB.

    :param storage_key: Storage key.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.trackIndexedDBForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def untrack_cache_storage_for_origin(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Unregisters origin from receiving notifications for cache storage.

    :param origin: Security origin.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.untrackCacheStorageForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def untrack_cache_storage_for_storage_key(
        storage_key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Unregisters storage key from receiving notifications for cache storage.

    :param storage_key: Storage key.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.untrackCacheStorageForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def untrack_indexed_db_for_origin(
        origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Unregisters origin from receiving notifications for IndexedDB.

    :param origin: Security origin.
    '''
    params: T_JSON_DICT = dict()
    params['origin'] = origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.untrackIndexedDBForOrigin',
        'params': params,
    }
    json = yield cmd_dict


def untrack_indexed_db_for_storage_key(
        storage_key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Unregisters storage key from receiving notifications for IndexedDB.

    :param storage_key: Storage key.
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.untrackIndexedDBForStorageKey',
        'params': params,
    }
    json = yield cmd_dict


def get_trust_tokens() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[TrustTokens]]:
    '''
    Returns the number of stored Trust Tokens per issuer for the
    current browsing context.

    **EXPERIMENTAL**

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getTrustTokens',
    }
    json = yield cmd_dict
    return [TrustTokens.from_json(i) for i in json['tokens']]


def clear_trust_tokens(
        issuer_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Removes all Trust Tokens issued by the provided issuerOrigin.
    Leaves other stored data, including the issuer's Redemption Records, intact.

    **EXPERIMENTAL**

    :param issuer_origin:
    :returns: True if any tokens were deleted, false otherwise.
    '''
    params: T_JSON_DICT = dict()
    params['issuerOrigin'] = issuer_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearTrustTokens',
        'params': params,
    }
    json = yield cmd_dict
    return bool(json['didDeleteTokens'])


def get_interest_group_details(
        owner_origin: str,
        name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,dict]:
    '''
    Gets details for a named interest group.

    **EXPERIMENTAL**

    :param owner_origin:
    :param name:
    :returns: This largely corresponds to: https://wicg.github.io/turtledove/#dictdef-generatebidinterestgroup but has absolute expirationTime instead of relative lifetimeMs and also adds joiningOrigin.
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    params['name'] = name
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getInterestGroupDetails',
        'params': params,
    }
    json = yield cmd_dict
    return dict(json['details'])


def set_interest_group_tracking(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables/Disables issuing of interestGroupAccessed events.

    **EXPERIMENTAL**

    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setInterestGroupTracking',
        'params': params,
    }
    json = yield cmd_dict


def set_interest_group_auction_tracking(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables/Disables issuing of interestGroupAuctionEventOccurred and
    interestGroupAuctionNetworkRequestCreated.

    **EXPERIMENTAL**

    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setInterestGroupAuctionTracking',
        'params': params,
    }
    json = yield cmd_dict


def get_shared_storage_metadata(
        owner_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SharedStorageMetadata]:
    '''
    Gets metadata for an origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getSharedStorageMetadata',
        'params': params,
    }
    json = yield cmd_dict
    return SharedStorageMetadata.from_json(json['metadata'])


def get_shared_storage_entries(
        owner_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[SharedStorageEntry]]:
    '''
    Gets the entries in an given origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getSharedStorageEntries',
        'params': params,
    }
    json = yield cmd_dict
    return [SharedStorageEntry.from_json(i) for i in json['entries']]


def set_shared_storage_entry(
        owner_origin: str,
        key: str,
        value: str,
        ignore_if_present: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets entry with ``key`` and ``value`` for a given origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    :param key:
    :param value:
    :param ignore_if_present: *(Optional)* If ```ignoreIfPresent```` is included and true, then only sets the entry if ````key``` doesn't already exist.
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    params['key'] = key
    params['value'] = value
    if ignore_if_present is not None:
        params['ignoreIfPresent'] = ignore_if_present
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setSharedStorageEntry',
        'params': params,
    }
    json = yield cmd_dict


def delete_shared_storage_entry(
        owner_origin: str,
        key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes entry for ``key`` (if it exists) for a given origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    :param key:
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    params['key'] = key
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.deleteSharedStorageEntry',
        'params': params,
    }
    json = yield cmd_dict


def clear_shared_storage_entries(
        owner_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears all entries for a given origin's shared storage.

    **EXPERIMENTAL**

    :param owner_origin:
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.clearSharedStorageEntries',
        'params': params,
    }
    json = yield cmd_dict


def reset_shared_storage_budget(
        owner_origin: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Resets the budget for ``ownerOrigin`` by clearing all budget withdrawals.

    **EXPERIMENTAL**

    :param owner_origin:
    '''
    params: T_JSON_DICT = dict()
    params['ownerOrigin'] = owner_origin
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.resetSharedStorageBudget',
        'params': params,
    }
    json = yield cmd_dict


def set_shared_storage_tracking(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables/disables issuing of sharedStorageAccessed events.

    **EXPERIMENTAL**

    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setSharedStorageTracking',
        'params': params,
    }
    json = yield cmd_dict


def set_storage_bucket_tracking(
        storage_key: str,
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set tracking for a storage key's buckets.

    **EXPERIMENTAL**

    :param storage_key:
    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['storageKey'] = storage_key
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setStorageBucketTracking',
        'params': params,
    }
    json = yield cmd_dict


def delete_storage_bucket(
        bucket: StorageBucket
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes the Storage Bucket with the given storage key and bucket name.

    **EXPERIMENTAL**

    :param bucket:
    '''
    params: T_JSON_DICT = dict()
    params['bucket'] = bucket.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.deleteStorageBucket',
        'params': params,
    }
    json = yield cmd_dict


def run_bounce_tracking_mitigations() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Deletes state for sites identified as potential bounce trackers, immediately.

    **EXPERIMENTAL**

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.runBounceTrackingMitigations',
    }
    json = yield cmd_dict
    return [str(i) for i in json['deletedSites']]


def set_attribution_reporting_local_testing_mode(
        enabled: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    https://wicg.github.io/attribution-reporting-api/

    **EXPERIMENTAL**

    :param enabled: If enabled, noise is suppressed and reports are sent immediately.
    '''
    params: T_JSON_DICT = dict()
    params['enabled'] = enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setAttributionReportingLocalTestingMode',
        'params': params,
    }
    json = yield cmd_dict


def set_attribution_reporting_tracking(
        enable: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables/disables issuing of Attribution Reporting events.

    **EXPERIMENTAL**

    :param enable:
    '''
    params: T_JSON_DICT = dict()
    params['enable'] = enable
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setAttributionReportingTracking',
        'params': params,
    }
    json = yield cmd_dict


def send_pending_attribution_reports() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,int]:
    '''
    Sends all pending Attribution Reports immediately, regardless of their
    scheduled report time.

    **EXPERIMENTAL**

    :returns: The number of reports that were sent.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.sendPendingAttributionReports',
    }
    json = yield cmd_dict
    return int(json['numSent'])


def get_related_website_sets() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[RelatedWebsiteSet]]:
    '''
    Returns the effective Related Website Sets in use by this profile for the browser
    session. The effective Related Website Sets will not change during a browser session.

    **EXPERIMENTAL**

    :returns: 
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getRelatedWebsiteSets',
    }
    json = yield cmd_dict
    return [RelatedWebsiteSet.from_json(i) for i in json['sets']]


def get_affected_urls_for_third_party_cookie_metadata(
        first_party_url: str,
        third_party_urls: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Returns the list of URLs from a page and its embedded resources that match
    existing grace period URL pattern rules.
    https://developers.google.com/privacy-sandbox/cookies/temporary-exceptions/grace-period

    **EXPERIMENTAL**

    :param first_party_url: The URL of the page currently being visited.
    :param third_party_urls: The list of embedded resource URLs from the page.
    :returns: Array of matching URLs. If there is a primary pattern match for the first- party URL, only the first-party URL is returned in the array.
    '''
    params: T_JSON_DICT = dict()
    params['firstPartyUrl'] = first_party_url
    params['thirdPartyUrls'] = [i for i in third_party_urls]
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.getAffectedUrlsForThirdPartyCookieMetadata',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['matchedUrls']]


def set_protected_audience_k_anonymity(
        owner: str,
        name: str,
        hashes: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param owner:
    :param name:
    :param hashes:
    '''
    params: T_JSON_DICT = dict()
    params['owner'] = owner
    params['name'] = name
    params['hashes'] = [i for i in hashes]
    cmd_dict: T_JSON_DICT = {
        'method': 'Storage.setProtectedAudienceKAnonymity',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Storage.cacheStorageContentUpdated')
@dataclass
class CacheStorageContentUpdated:
    '''
    A cache's contents have been modified.
    '''
    #: Origin to update.
    origin: str
    #: Storage key to update.
    storage_key: str
    #: Storage bucket to update.
    bucket_id: str
    #: Name of cache in origin.
    cache_name: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CacheStorageContentUpdated:
        return cls(
            origin=str(json['origin']),
            storage_key=str(json['storageKey']),
            bucket_id=str(json['bucketId']),
            cache_name=str(json['cacheName'])
        )


@event_class('Storage.cacheStorageListUpdated')
@dataclass
class CacheStorageListUpdated:
    '''
    A cache has been added/deleted.
    '''
    #: Origin to update.
    origin: str
    #: Storage key to update.
    storage_key: str
    #: Storage bucket to update.
    bucket_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> CacheStorageListUpdated:
        return cls(
            origin=str(json['origin']),
            storage_key=str(json['storageKey']),
            bucket_id=str(json['bucketId'])
        )


@event_class('Storage.indexedDBContentUpdated')
@dataclass
class IndexedDBContentUpdated:
    '''
    The origin's IndexedDB object store has been modified.
    '''
    #: Origin to update.
    origin: str
    #: Storage key to update.
    storage_key: str
    #: Storage bucket to update.
    bucket_id: str
    #: Database to update.
    database_name: str
    #: ObjectStore to update.
    object_store_name: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> IndexedDBContentUpdated:
        return cls(
            origin=str(json['origin']),
            storage_key=str(json['storageKey']),
            bucket_id=str(json['bucketId']),
            database_name=str(json['databaseName']),
            object_store_name=str(json['objectStoreName'])
        )


@event_class('Storage.indexedDBListUpdated')
@dataclass
class IndexedDBListUpdated:
    '''
    The origin's IndexedDB database list has been modified.
    '''
    #: Origin to update.
    origin: str
    #: Storage key to update.
    storage_key: str
    #: Storage bucket to update.
    bucket_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> IndexedDBListUpdated:
        return cls(
            origin=str(json['origin']),
            storage_key=str(json['storageKey']),
            bucket_id=str(json['bucketId'])
        )


@event_class('Storage.interestGroupAccessed')
@dataclass
class InterestGroupAccessed:
    '''
    One of the interest groups was accessed. Note that these events are global
    to all targets sharing an interest group store.
    '''
    access_time: network.TimeSinceEpoch
    type_: InterestGroupAccessType
    owner_origin: str
    name: str
    #: For topLevelBid/topLevelAdditionalBid, and when appropriate,
    #: win and additionalBidWin
    component_seller_origin: typing.Optional[str]
    #: For bid or somethingBid event, if done locally and not on a server.
    bid: typing.Optional[float]
    bid_currency: typing.Optional[str]
    #: For non-global events --- links to interestGroupAuctionEvent
    unique_auction_id: typing.Optional[InterestGroupAuctionId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InterestGroupAccessed:
        return cls(
            access_time=network.TimeSinceEpoch.from_json(json['accessTime']),
            type_=InterestGroupAccessType.from_json(json['type']),
            owner_origin=str(json['ownerOrigin']),
            name=str(json['name']),
            component_seller_origin=str(json['componentSellerOrigin']) if 'componentSellerOrigin' in json else None,
            bid=float(json['bid']) if 'bid' in json else None,
            bid_currency=str(json['bidCurrency']) if 'bidCurrency' in json else None,
            unique_auction_id=InterestGroupAuctionId.from_json(json['uniqueAuctionId']) if 'uniqueAuctionId' in json else None
        )


@event_class('Storage.interestGroupAuctionEventOccurred')
@dataclass
class InterestGroupAuctionEventOccurred:
    '''
    An auction involving interest groups is taking place. These events are
    target-specific.
    '''
    event_time: network.TimeSinceEpoch
    type_: InterestGroupAuctionEventType
    unique_auction_id: InterestGroupAuctionId
    #: Set for child auctions.
    parent_auction_id: typing.Optional[InterestGroupAuctionId]
    #: Set for started and configResolved
    auction_config: typing.Optional[dict]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InterestGroupAuctionEventOccurred:
        return cls(
            event_time=network.TimeSinceEpoch.from_json(json['eventTime']),
            type_=InterestGroupAuctionEventType.from_json(json['type']),
            unique_auction_id=InterestGroupAuctionId.from_json(json['uniqueAuctionId']),
            parent_auction_id=InterestGroupAuctionId.from_json(json['parentAuctionId']) if 'parentAuctionId' in json else None,
            auction_config=dict(json['auctionConfig']) if 'auctionConfig' in json else None
        )


@event_class('Storage.interestGroupAuctionNetworkRequestCreated')
@dataclass
class InterestGroupAuctionNetworkRequestCreated:
    '''
    Specifies which auctions a particular network fetch may be related to, and
    in what role. Note that it is not ordered with respect to
    Network.requestWillBeSent (but will happen before loadingFinished
    loadingFailed).
    '''
    type_: InterestGroupAuctionFetchType
    request_id: network.RequestId
    #: This is the set of the auctions using the worklet that issued this
    #: request.  In the case of trusted signals, it's possible that only some of
    #: them actually care about the keys being queried.
    auctions: typing.List[InterestGroupAuctionId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> InterestGroupAuctionNetworkRequestCreated:
        return cls(
            type_=InterestGroupAuctionFetchType.from_json(json['type']),
            request_id=network.RequestId.from_json(json['requestId']),
            auctions=[InterestGroupAuctionId.from_json(i) for i in json['auctions']]
        )


@event_class('Storage.sharedStorageAccessed')
@dataclass
class SharedStorageAccessed:
    '''
    Shared storage was accessed by the associated page.
    The following parameters are included in all events.
    '''
    #: Time of the access.
    access_time: network.TimeSinceEpoch
    #: Enum value indicating the access scope.
    scope: SharedStorageAccessScope
    #: Enum value indicating the Shared Storage API method invoked.
    method: SharedStorageAccessMethod
    #: DevTools Frame Token for the primary frame tree's root.
    main_frame_id: page.FrameId
    #: Serialization of the origin owning the Shared Storage data.
    owner_origin: str
    #: Serialization of the site owning the Shared Storage data.
    owner_site: str
    #: The sub-parameters wrapped by ``params`` are all optional and their
    #: presence/absence depends on ``type``.
    params: SharedStorageAccessParams

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> SharedStorageAccessed:
        return cls(
            access_time=network.TimeSinceEpoch.from_json(json['accessTime']),
            scope=SharedStorageAccessScope.from_json(json['scope']),
            method=SharedStorageAccessMethod.from_json(json['method']),
            main_frame_id=page.FrameId.from_json(json['mainFrameId']),
            owner_origin=str(json['ownerOrigin']),
            owner_site=str(json['ownerSite']),
            params=SharedStorageAccessParams.from_json(json['params'])
        )


@event_class('Storage.storageBucketCreatedOrUpdated')
@dataclass
class StorageBucketCreatedOrUpdated:
    bucket_info: StorageBucketInfo

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> StorageBucketCreatedOrUpdated:
        return cls(
            bucket_info=StorageBucketInfo.from_json(json['bucketInfo'])
        )


@event_class('Storage.storageBucketDeleted')
@dataclass
class StorageBucketDeleted:
    bucket_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> StorageBucketDeleted:
        return cls(
            bucket_id=str(json['bucketId'])
        )


@event_class('Storage.attributionReportingSourceRegistered')
@dataclass
class AttributionReportingSourceRegistered:
    '''
    **EXPERIMENTAL**


    '''
    registration: AttributionReportingSourceRegistration
    result: AttributionReportingSourceRegistrationResult

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AttributionReportingSourceRegistered:
        return cls(
            registration=AttributionReportingSourceRegistration.from_json(json['registration']),
            result=AttributionReportingSourceRegistrationResult.from_json(json['result'])
        )


@event_class('Storage.attributionReportingTriggerRegistered')
@dataclass
class AttributionReportingTriggerRegistered:
    '''
    **EXPERIMENTAL**


    '''
    registration: AttributionReportingTriggerRegistration
    event_level: AttributionReportingEventLevelResult
    aggregatable: AttributionReportingAggregatableResult

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AttributionReportingTriggerRegistered:
        return cls(
            registration=AttributionReportingTriggerRegistration.from_json(json['registration']),
            event_level=AttributionReportingEventLevelResult.from_json(json['eventLevel']),
            aggregatable=AttributionReportingAggregatableResult.from_json(json['aggregatable'])
        )