
# === NexusCore/openenv\Lib\site-packages\httpx\_utils.py ===
from __future__ import annotations

import ipaddress
import os
import re
import typing
from urllib.request import getproxies

from ._types import PrimitiveData

if typing.TYPE_CHECKING:  # pragma: no cover
    from ._urls import URL


def primitive_value_to_str(value: PrimitiveData) -> str:
    """
    Coerce a primitive data type into a string value.

    Note that we prefer JSON-style 'true'/'false' for boolean values here.
    """
    if value is True:
        return "true"
    elif value is False:
        return "false"
    elif value is None:
        return ""
    return str(value)


def get_environment_proxies() -> dict[str, str | None]:
    """Gets proxy information from the environment"""

    # urllib.request.getproxies() falls back on System
    # Registry and Config for proxies on Windows and macOS.
    # We don't want to propagate non-HTTP proxies into
    # our configuration such as 'TRAVIS_APT_PROXY'.
    proxy_info = getproxies()
    mounts: dict[str, str | None] = {}

    for scheme in ("http", "https", "all"):
        if proxy_info.get(scheme):
            hostname = proxy_info[scheme]
            mounts[f"{scheme}://"] = (
                hostname if "://" in hostname else f"http://{hostname}"
            )

    no_proxy_hosts = [host.strip() for host in proxy_info.get("no", "").split(",")]
    for hostname in no_proxy_hosts:
        # See https://curl.haxx.se/libcurl/c/CURLOPT_NOPROXY.html for details
        # on how names in `NO_PROXY` are handled.
        if hostname == "*":
            # If NO_PROXY=* is used or if "*" occurs as any one of the comma
            # separated hostnames, then we should just bypass any information
            # from HTTP_PROXY, HTTPS_PROXY, ALL_PROXY, and always ignore
            # proxies.
            return {}
        elif hostname:
            # NO_PROXY=.google.com is marked as "all://*.google.com,
            #   which disables "www.google.com" but not "google.com"
            # NO_PROXY=google.com is marked as "all://*google.com,
            #   which disables "www.google.com" and "google.com".
            #   (But not "wwwgoogle.com")
            # NO_PROXY can include domains, IPv6, IPv4 addresses and "localhost"
            #   NO_PROXY=example.com,::1,localhost,192.168.0.0/16
            if "://" in hostname:
                mounts[hostname] = None
            elif is_ipv4_hostname(hostname):
                mounts[f"all://{hostname}"] = None
            elif is_ipv6_hostname(hostname):
                mounts[f"all://[{hostname}]"] = None
            elif hostname.lower() == "localhost":
                mounts[f"all://{hostname}"] = None
            else:
                mounts[f"all://*{hostname}"] = None

    return mounts


def to_bytes(value: str | bytes, encoding: str = "utf-8") -> bytes:
    return value.encode(encoding) if isinstance(value, str) else value


def to_str(value: str | bytes, encoding: str = "utf-8") -> str:
    return value if isinstance(value, str) else value.decode(encoding)


def to_bytes_or_str(value: str, match_type_of: typing.AnyStr) -> typing.AnyStr:
    return value if isinstance(match_type_of, str) else value.encode()


def unquote(value: str) -> str:
    return value[1:-1] if value[0] == value[-1] == '"' else value


def peek_filelike_length(stream: typing.Any) -> int | None:
    """
    Given a file-like stream object, return its length in number of bytes
    without reading it into memory.
    """
    try:
        # Is it an actual file?
        fd = stream.fileno()
        # Yup, seems to be an actual file.
        length = os.fstat(fd).st_size
    except (AttributeError, OSError):
        # No... Maybe it's something that supports random access, like `io.BytesIO`?
        try:
            # Assuming so, go to end of stream to figure out its length,
            # then put it back in place.
            offset = stream.tell()
            length = stream.seek(0, os.SEEK_END)
            stream.seek(offset)
        except (AttributeError, OSError):
            # Not even that? Sorry, we're doomed...
            return None

    return length


class URLPattern:
    """
    A utility class currently used for making lookups against proxy keys...

    # Wildcard matching...
    >>> pattern = URLPattern("all://")
    >>> pattern.matches(httpx.URL("http://example.com"))
    True

    # Witch scheme matching...
    >>> pattern = URLPattern("https://")
    >>> pattern.matches(httpx.URL("https://example.com"))
    True
    >>> pattern.matches(httpx.URL("http://example.com"))
    False

    # With domain matching...
    >>> pattern = URLPattern("https://example.com")
    >>> pattern.matches(httpx.URL("https://example.com"))
    True
    >>> pattern.matches(httpx.URL("http://example.com"))
    False
    >>> pattern.matches(httpx.URL("https://other.com"))
    False

    # Wildcard scheme, with domain matching...
    >>> pattern = URLPattern("all://example.com")
    >>> pattern.matches(httpx.URL("https://example.com"))
    True
    >>> pattern.matches(httpx.URL("http://example.com"))
    True
    >>> pattern.matches(httpx.URL("https://other.com"))
    False

    # With port matching...
    >>> pattern = URLPattern("https://example.com:1234")
    >>> pattern.matches(httpx.URL("https://example.com:1234"))
    True
    >>> pattern.matches(httpx.URL("https://example.com"))
    False
    """

    def __init__(self, pattern: str) -> None:
        from ._urls import URL

        if pattern and ":" not in pattern:
            raise ValueError(
                f"Proxy keys should use proper URL forms rather "
                f"than plain scheme strings. "
                f'Instead of "{pattern}", use "{pattern}://"'
            )

        url = URL(pattern)
        self.pattern = pattern
        self.scheme = "" if url.scheme == "all" else url.scheme
        self.host = "" if url.host == "*" else url.host
        self.port = url.port
        if not url.host or url.host == "*":
            self.host_regex: typing.Pattern[str] | None = None
        elif url.host.startswith("*."):
            # *.example.com should match "www.example.com", but not "example.com"
            domain = re.escape(url.host[2:])
            self.host_regex = re.compile(f"^.+\\.{domain}$")
        elif url.host.startswith("*"):
            # *example.com should match "www.example.com" and "example.com"
            domain = re.escape(url.host[1:])
            self.host_regex = re.compile(f"^(.+\\.)?{domain}$")
        else:
            # example.com should match "example.com" but not "www.example.com"
            domain = re.escape(url.host)
            self.host_regex = re.compile(f"^{domain}$")

    def matches(self, other: URL) -> bool:
        if self.scheme and self.scheme != other.scheme:
            return False
        if (
            self.host
            and self.host_regex is not None
            and not self.host_regex.match(other.host)
        ):
            return False
        if self.port is not None and self.port != other.port:
            return False
        return True

    @property
    def priority(self) -> tuple[int, int, int]:
        """
        The priority allows URLPattern instances to be sortable, so that
        we can match from most specific to least specific.
        """
        # URLs with a port should take priority over URLs without a port.
        port_priority = 0 if self.port is not None else 1
        # Longer hostnames should match first.
        host_priority = -len(self.host)
        # Longer schemes should match first.
        scheme_priority = -len(self.scheme)
        return (port_priority, host_priority, scheme_priority)

    def __hash__(self) -> int:
        return hash(self.pattern)

    def __lt__(self, other: URLPattern) -> bool:
        return self.priority < other.priority

    def __eq__(self, other: typing.Any) -> bool:
        return isinstance(other, URLPattern) and self.pattern == other.pattern


def is_ipv4_hostname(hostname: str) -> bool:
    try:
        ipaddress.IPv4Address(hostname.split("/")[0])
    except Exception:
        return False
    return True


def is_ipv6_hostname(hostname: str) -> bool:
    try:
        ipaddress.IPv6Address(hostname.split("/")[0])
    except Exception:
        return False
    return True

# === NexusCore/openenv\Lib\site-packages\PIL\JpegPresets.py ===
"""
JPEG quality settings equivalent to the Photoshop settings.
Can be used when saving JPEG files.

The following presets are available by default:
``web_low``, ``web_medium``, ``web_high``, ``web_very_high``, ``web_maximum``,
``low``, ``medium``, ``high``, ``maximum``.
More presets can be added to the :py:data:`presets` dict if needed.

To apply the preset, specify::

  quality="preset_name"

To apply only the quantization table::

  qtables="preset_name"

To apply only the subsampling setting::

  subsampling="preset_name"

Example::

  im.save("image_name.jpg", quality="web_high")

Subsampling
-----------

Subsampling is the practice of encoding images by implementing less resolution
for chroma information than for luma information.
(ref.: https://en.wikipedia.org/wiki/Chroma_subsampling)

Possible subsampling values are 0, 1 and 2 that correspond to 4:4:4, 4:2:2 and
4:2:0.

You can get the subsampling of a JPEG with the
:func:`.JpegImagePlugin.get_sampling` function.

In JPEG compressed data a JPEG marker is used instead of an EXIF tag.
(ref.: https://exiv2.org/tags.html)


Quantization tables
-------------------

They are values use by the DCT (Discrete cosine transform) to remove
*unnecessary* information from the image (the lossy part of the compression).
(ref.: https://en.wikipedia.org/wiki/Quantization_matrix#Quantization_matrices,
https://en.wikipedia.org/wiki/JPEG#Quantization)

You can get the quantization tables of a JPEG with::

  im.quantization

This will return a dict with a number of lists. You can pass this dict
directly as the qtables argument when saving a JPEG.

The quantization table format in presets is a list with sublists. These formats
are interchangeable.

Libjpeg ref.:
https://web.archive.org/web/20120328125543/http://www.jpegcameras.com/libjpeg/libjpeg-3.html

"""

from __future__ import annotations

# fmt: off
presets = {
            'web_low':      {'subsampling':  2,  # "4:2:0"
                             'quantization': [
                               [20, 16, 25, 39, 50, 46, 62, 68,
                                16, 18, 23, 38, 38, 53, 65, 68,
                                25, 23, 31, 38, 53, 65, 68, 68,
                                39, 38, 38, 53, 65, 68, 68, 68,
                                50, 38, 53, 65, 68, 68, 68, 68,
                                46, 53, 65, 68, 68, 68, 68, 68,
                                62, 65, 68, 68, 68, 68, 68, 68,
                                68, 68, 68, 68, 68, 68, 68, 68],
                               [21, 25, 32, 38, 54, 68, 68, 68,
                                25, 28, 24, 38, 54, 68, 68, 68,
                                32, 24, 32, 43, 66, 68, 68, 68,
                                38, 38, 43, 53, 68, 68, 68, 68,
                                54, 54, 66, 68, 68, 68, 68, 68,
                                68, 68, 68, 68, 68, 68, 68, 68,
                                68, 68, 68, 68, 68, 68, 68, 68,
                                68, 68, 68, 68, 68, 68, 68, 68]
                              ]},
            'web_medium':   {'subsampling':  2,  # "4:2:0"
                             'quantization': [
                               [16, 11, 11, 16, 23, 27, 31, 30,
                                11, 12, 12, 15, 20, 23, 23, 30,
                                11, 12, 13, 16, 23, 26, 35, 47,
                                16, 15, 16, 23, 26, 37, 47, 64,
                                23, 20, 23, 26, 39, 51, 64, 64,
                                27, 23, 26, 37, 51, 64, 64, 64,
                                31, 23, 35, 47, 64, 64, 64, 64,
                                30, 30, 47, 64, 64, 64, 64, 64],
                               [17, 15, 17, 21, 20, 26, 38, 48,
                                15, 19, 18, 17, 20, 26, 35, 43,
                                17, 18, 20, 22, 26, 30, 46, 53,
                                21, 17, 22, 28, 30, 39, 53, 64,
                                20, 20, 26, 30, 39, 48, 64, 64,
                                26, 26, 30, 39, 48, 63, 64, 64,
                                38, 35, 46, 53, 64, 64, 64, 64,
                                48, 43, 53, 64, 64, 64, 64, 64]
                             ]},
            'web_high':     {'subsampling':  0,  # "4:4:4"
                             'quantization': [
                               [6,   4,  4,  6,  9, 11, 12, 16,
                                4,   5,  5,  6,  8, 10, 12, 12,
                                4,   5,  5,  6, 10, 12, 14, 19,
                                6,   6,  6, 11, 12, 15, 19, 28,
                                9,   8, 10, 12, 16, 20, 27, 31,
                                11, 10, 12, 15, 20, 27, 31, 31,
                                12, 12, 14, 19, 27, 31, 31, 31,
                                16, 12, 19, 28, 31, 31, 31, 31],
                               [7,   7, 13, 24, 26, 31, 31, 31,
                                7,  12, 16, 21, 31, 31, 31, 31,
                                13, 16, 17, 31, 31, 31, 31, 31,
                                24, 21, 31, 31, 31, 31, 31, 31,
                                26, 31, 31, 31, 31, 31, 31, 31,
                                31, 31, 31, 31, 31, 31, 31, 31,
                                31, 31, 31, 31, 31, 31, 31, 31,
                                31, 31, 31, 31, 31, 31, 31, 31]
                             ]},
            'web_very_high': {'subsampling':  0,  # "4:4:4"
                              'quantization': [
                               [2,   2,  2,  2,  3,  4,  5,  6,
                                2,   2,  2,  2,  3,  4,  5,  6,
                                2,   2,  2,  2,  4,  5,  7,  9,
                                2,   2,  2,  4,  5,  7,  9, 12,
                                3,   3,  4,  5,  8, 10, 12, 12,
                                4,   4,  5,  7, 10, 12, 12, 12,
                                5,   5,  7,  9, 12, 12, 12, 12,
                                6,   6,  9, 12, 12, 12, 12, 12],
                               [3,   3,  5,  9, 13, 15, 15, 15,
                                3,   4,  6, 11, 14, 12, 12, 12,
                                5,   6,  9, 14, 12, 12, 12, 12,
                                9,  11, 14, 12, 12, 12, 12, 12,
                                13, 14, 12, 12, 12, 12, 12, 12,
                                15, 12, 12, 12, 12, 12, 12, 12,
                                15, 12, 12, 12, 12, 12, 12, 12,
                                15, 12, 12, 12, 12, 12, 12, 12]
                              ]},
            'web_maximum':  {'subsampling':  0,  # "4:4:4"
                             'quantization': [
                                [1,  1,  1,  1,  1,  1,  1,  1,
                                 1,  1,  1,  1,  1,  1,  1,  1,
                                 1,  1,  1,  1,  1,  1,  1,  2,
                                 1,  1,  1,  1,  1,  1,  2,  2,
                                 1,  1,  1,  1,  1,  2,  2,  3,
                                 1,  1,  1,  1,  2,  2,  3,  3,
                                 1,  1,  1,  2,  2,  3,  3,  3,
                                 1,  1,  2,  2,  3,  3,  3,  3],
                                [1,  1,  1,  2,  2,  3,  3,  3,
                                 1,  1,  1,  2,  3,  3,  3,  3,
                                 1,  1,  1,  3,  3,  3,  3,  3,
                                 2,  2,  3,  3,  3,  3,  3,  3,
                                 2,  3,  3,  3,  3,  3,  3,  3,
                                 3,  3,  3,  3,  3,  3,  3,  3,
                                 3,  3,  3,  3,  3,  3,  3,  3,
                                 3,  3,  3,  3,  3,  3,  3,  3]
                             ]},
            'low':          {'subsampling':  2,  # "4:2:0"
                             'quantization': [
                               [18, 14, 14, 21, 30, 35, 34, 17,
                                14, 16, 16, 19, 26, 23, 12, 12,
                                14, 16, 17, 21, 23, 12, 12, 12,
                                21, 19, 21, 23, 12, 12, 12, 12,
                                30, 26, 23, 12, 12, 12, 12, 12,
                                35, 23, 12, 12, 12, 12, 12, 12,
                                34, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12],
                               [20, 19, 22, 27, 20, 20, 17, 17,
                                19, 25, 23, 14, 14, 12, 12, 12,
                                22, 23, 14, 14, 12, 12, 12, 12,
                                27, 14, 14, 12, 12, 12, 12, 12,
                                20, 14, 12, 12, 12, 12, 12, 12,
                                20, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12]
                             ]},
            'medium':       {'subsampling':  2,  # "4:2:0"
                             'quantization': [
                               [12,  8,  8, 12, 17, 21, 24, 17,
                                8,   9,  9, 11, 15, 19, 12, 12,
                                8,   9, 10, 12, 19, 12, 12, 12,
                                12, 11, 12, 21, 12, 12, 12, 12,
                                17, 15, 19, 12, 12, 12, 12, 12,
                                21, 19, 12, 12, 12, 12, 12, 12,
                                24, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12],
                               [13, 11, 13, 16, 20, 20, 17, 17,
                                11, 14, 14, 14, 14, 12, 12, 12,
                                13, 14, 14, 14, 12, 12, 12, 12,
                                16, 14, 14, 12, 12, 12, 12, 12,
                                20, 14, 12, 12, 12, 12, 12, 12,
                                20, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12]
                             ]},
            'high':         {'subsampling':  0,  # "4:4:4"
                             'quantization': [
                               [6,   4,  4,  6,  9, 11, 12, 16,
                                4,   5,  5,  6,  8, 10, 12, 12,
                                4,   5,  5,  6, 10, 12, 12, 12,
                                6,   6,  6, 11, 12, 12, 12, 12,
                                9,   8, 10, 12, 12, 12, 12, 12,
                                11, 10, 12, 12, 12, 12, 12, 12,
                                12, 12, 12, 12, 12, 12, 12, 12,
                                16, 12, 12, 12, 12, 12, 12, 12],
                               [7,   7, 13, 24, 20, 20, 17, 17,
                                7,  12, 16, 14, 14, 12, 12, 12,
                                13, 16, 14, 14, 12, 12, 12, 12,
                                24, 14, 14, 12, 12, 12, 12, 12,
                                20, 14, 12, 12, 12, 12, 12, 12,
                                20, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12]
                             ]},
            'maximum':      {'subsampling':  0,  # "4:4:4"
                             'quantization': [
                               [2,   2,  2,  2,  3,  4,  5,  6,
                                2,   2,  2,  2,  3,  4,  5,  6,
                                2,   2,  2,  2,  4,  5,  7,  9,
                                2,   2,  2,  4,  5,  7,  9, 12,
                                3,   3,  4,  5,  8, 10, 12, 12,
                                4,   4,  5,  7, 10, 12, 12, 12,
                                5,   5,  7,  9, 12, 12, 12, 12,
                                6,   6,  9, 12, 12, 12, 12, 12],
                               [3,   3,  5,  9, 13, 15, 15, 15,
                                3,   4,  6, 10, 14, 12, 12, 12,
                                5,   6,  9, 14, 12, 12, 12, 12,
                                9,  10, 14, 12, 12, 12, 12, 12,
                                13, 14, 12, 12, 12, 12, 12, 12,
                                15, 12, 12, 12, 12, 12, 12, 12,
                                15, 12, 12, 12, 12, 12, 12, 12,
                                15, 12, 12, 12, 12, 12, 12, 12]
                             ]},
}
# fmt: on

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\symfont.py ===
from fontTools.pens.basePen import BasePen
from functools import partial
from itertools import count
import sympy as sp
import sys

n = 3  # Max Bezier degree; 3 for cubic, 2 for quadratic

t, x, y = sp.symbols("t x y", real=True)
c = sp.symbols("c", real=False)  # Complex representation instead of x/y

X = tuple(sp.symbols("x:%d" % (n + 1), real=True))
Y = tuple(sp.symbols("y:%d" % (n + 1), real=True))
P = tuple(zip(*(sp.symbols("p:%d[%s]" % (n + 1, w), real=True) for w in "01")))
C = tuple(sp.symbols("c:%d" % (n + 1), real=False))

# Cubic Bernstein basis functions
BinomialCoefficient = [(1, 0)]
for i in range(1, n + 1):
    last = BinomialCoefficient[-1]
    this = tuple(last[j - 1] + last[j] for j in range(len(last))) + (0,)
    BinomialCoefficient.append(this)
BinomialCoefficient = tuple(tuple(item[:-1]) for item in BinomialCoefficient)
del last, this

BernsteinPolynomial = tuple(
    tuple(c * t**i * (1 - t) ** (n - i) for i, c in enumerate(coeffs))
    for n, coeffs in enumerate(BinomialCoefficient)
)

BezierCurve = tuple(
    tuple(
        sum(P[i][j] * bernstein for i, bernstein in enumerate(bernsteins))
        for j in range(2)
    )
    for n, bernsteins in enumerate(BernsteinPolynomial)
)
BezierCurveC = tuple(
    sum(C[i] * bernstein for i, bernstein in enumerate(bernsteins))
    for n, bernsteins in enumerate(BernsteinPolynomial)
)


def green(f, curveXY):
    f = -sp.integrate(sp.sympify(f), y)
    f = f.subs({x: curveXY[0], y: curveXY[1]})
    f = sp.integrate(f * sp.diff(curveXY[0], t), (t, 0, 1))
    return f


class _BezierFuncsLazy(dict):
    def __init__(self, symfunc):
        self._symfunc = symfunc
        self._bezfuncs = {}

    def __missing__(self, i):
        args = ["p%d" % d for d in range(i + 1)]
        f = green(self._symfunc, BezierCurve[i])
        f = sp.gcd_terms(f.collect(sum(P, ())))  # Optimize
        return sp.lambdify(args, f)


class GreenPen(BasePen):
    _BezierFuncs = {}

    @classmethod
    def _getGreenBezierFuncs(celf, func):
        funcstr = str(func)
        if not funcstr in celf._BezierFuncs:
            celf._BezierFuncs[funcstr] = _BezierFuncsLazy(func)
        return celf._BezierFuncs[funcstr]

    def __init__(self, func, glyphset=None):
        BasePen.__init__(self, glyphset)
        self._funcs = self._getGreenBezierFuncs(func)
        self.value = 0

    def _moveTo(self, p0):
        self._startPoint = p0

    def _closePath(self):
        p0 = self._getCurrentPoint()
        if p0 != self._startPoint:
            self._lineTo(self._startPoint)

    def _endPath(self):
        p0 = self._getCurrentPoint()
        if p0 != self._startPoint:
            # Green theorem is not defined on open contours.
            raise NotImplementedError

    def _lineTo(self, p1):
        p0 = self._getCurrentPoint()
        self.value += self._funcs[1](p0, p1)

    def _qCurveToOne(self, p1, p2):
        p0 = self._getCurrentPoint()
        self.value += self._funcs[2](p0, p1, p2)

    def _curveToOne(self, p1, p2, p3):
        p0 = self._getCurrentPoint()
        self.value += self._funcs[3](p0, p1, p2, p3)


# Sample pens.
# Do not use this in real code.
# Use fontTools.pens.momentsPen.MomentsPen instead.
AreaPen = partial(GreenPen, func=1)
MomentXPen = partial(GreenPen, func=x)
MomentYPen = partial(GreenPen, func=y)
MomentXXPen = partial(GreenPen, func=x * x)
MomentYYPen = partial(GreenPen, func=y * y)
MomentXYPen = partial(GreenPen, func=x * y)


def printGreenPen(penName, funcs, file=sys.stdout, docstring=None):
    if docstring is not None:
        print('"""%s"""' % docstring)

    print(
        """from fontTools.pens.basePen import BasePen, OpenContourError
try:
	import cython
except (AttributeError, ImportError):
	# if cython not installed, use mock module with no-op decorators and types
	from fontTools.misc import cython
COMPILED = cython.compiled


__all__ = ["%s"]

class %s(BasePen):

	def __init__(self, glyphset=None):
		BasePen.__init__(self, glyphset)
"""
        % (penName, penName),
        file=file,
    )
    for name, f in funcs:
        print("		self.%s = 0" % name, file=file)
    print(
        """
	def _moveTo(self, p0):
		self._startPoint = p0

	def _closePath(self):
		p0 = self._getCurrentPoint()
		if p0 != self._startPoint:
			self._lineTo(self._startPoint)

	def _endPath(self):
		p0 = self._getCurrentPoint()
		if p0 != self._startPoint:
			raise OpenContourError(
							"Glyph statistics is not defined on open contours."
			)
""",
        end="",
        file=file,
    )

    for n in (1, 2, 3):
        subs = {P[i][j]: [X, Y][j][i] for i in range(n + 1) for j in range(2)}
        greens = [green(f, BezierCurve[n]) for name, f in funcs]
        greens = [sp.gcd_terms(f.collect(sum(P, ()))) for f in greens]  # Optimize
        greens = [f.subs(subs) for f in greens]  # Convert to p to x/y
        defs, exprs = sp.cse(
            greens,
            optimizations="basic",
            symbols=(sp.Symbol("r%d" % i) for i in count()),
        )

        print()
        for name, value in defs:
            print("	@cython.locals(%s=cython.double)" % name, file=file)
        if n == 1:
            print(
                """\
	@cython.locals(x0=cython.double, y0=cython.double)
	@cython.locals(x1=cython.double, y1=cython.double)
	def _lineTo(self, p1):
		x0,y0 = self._getCurrentPoint()
		x1,y1 = p1
""",
                file=file,
            )
        elif n == 2:
            print(
                """\
	@cython.locals(x0=cython.double, y0=cython.double)
	@cython.locals(x1=cython.double, y1=cython.double)
	@cython.locals(x2=cython.double, y2=cython.double)
	def _qCurveToOne(self, p1, p2):
		x0,y0 = self._getCurrentPoint()
		x1,y1 = p1
		x2,y2 = p2
""",
                file=file,
            )
        elif n == 3:
            print(
                """\
	@cython.locals(x0=cython.double, y0=cython.double)
	@cython.locals(x1=cython.double, y1=cython.double)
	@cython.locals(x2=cython.double, y2=cython.double)
	@cython.locals(x3=cython.double, y3=cython.double)
	def _curveToOne(self, p1, p2, p3):
		x0,y0 = self._getCurrentPoint()
		x1,y1 = p1
		x2,y2 = p2
		x3,y3 = p3
""",
                file=file,
            )
        for name, value in defs:
            print("		%s = %s" % (name, value), file=file)

        print(file=file)
        for name, value in zip([f[0] for f in funcs], exprs):
            print("		self.%s += %s" % (name, value), file=file)

    print(
        """
if __name__ == '__main__':
	from fontTools.misc.symfont import x, y, printGreenPen
	printGreenPen('%s', ["""
        % penName,
        file=file,
    )
    for name, f in funcs:
        print("		      ('%s', %s)," % (name, str(f)), file=file)
    print("		     ])", file=file)


if __name__ == "__main__":
    import sys

    if sys.argv[1:]:
        penName = sys.argv[1]
        funcs = [(name, eval(f)) for name, f in zip(sys.argv[2::2], sys.argv[3::2])]
        printGreenPen(penName, funcs, file=sys.stdout)

# === NexusCore/openenv\Lib\site-packages\jupyter_client\provisioning\local_provisioner.py ===
"""Kernel Provisioner Classes"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import os
import signal
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..connect import KernelConnectionInfo, LocalPortCache
from ..launcher import launch_kernel
from ..localinterfaces import is_local_ip, local_ips
from .provisioner_base import KernelProvisionerBase


class LocalProvisioner(KernelProvisionerBase):  # type:ignore[misc]
    """
    :class:`LocalProvisioner` is a concrete class of ABC :py:class:`KernelProvisionerBase`
    and is the out-of-box default implementation used when no kernel provisioner is
    specified in the kernel specification (``kernel.json``).  It provides functional
    parity to existing applications by launching the kernel locally and using
    :class:`subprocess.Popen` to manage its lifecycle.

    This class is intended to be subclassed for customizing local kernel environments
    and serve as a reference implementation for other custom provisioners.
    """

    process = None
    _exit_future = None
    pid = None
    pgid = None
    ip = None
    ports_cached = False

    @property
    def has_process(self) -> bool:
        return self.process is not None

    async def poll(self) -> Optional[int]:
        """Poll the provisioner."""
        ret = 0
        if self.process:
            ret = self.process.poll()  # type:ignore[unreachable]
        return ret

    async def wait(self) -> Optional[int]:
        """Wait for the provisioner process."""
        ret = 0
        if self.process:
            # Use busy loop at 100ms intervals, polling until the process is
            # not alive.  If we find the process is no longer alive, complete
            # its cleanup via the blocking wait().  Callers are responsible for
            # issuing calls to wait() using a timeout (see kill()).
            while await self.poll() is None:  # type:ignore[unreachable]
                await asyncio.sleep(0.1)

            # Process is no longer alive, wait and clear
            ret = self.process.wait()
            # Make sure all the fds get closed.
            for attr in ["stdout", "stderr", "stdin"]:
                fid = getattr(self.process, attr)
                if fid:
                    fid.close()
            self.process = None  # allow has_process to now return False
        return ret

    async def send_signal(self, signum: int) -> None:
        """Sends a signal to the process group of the kernel (this
        usually includes the kernel and any subprocesses spawned by
        the kernel).

        Note that since only SIGTERM is supported on Windows, we will
        check if the desired signal is for interrupt and apply the
        applicable code on Windows in that case.
        """
        if self.process:
            if signum == signal.SIGINT and sys.platform == "win32":  # type:ignore[unreachable]
                from ..win_interrupt import send_interrupt

                send_interrupt(self.process.win32_interrupt_event)
                return

            # Prefer process-group over process
            if self.pgid and hasattr(os, "killpg"):
                try:
                    os.killpg(self.pgid, signum)
                    return
                except OSError:
                    pass  # We'll retry sending the signal to only the process below

            # If we're here, send the signal to the process and let caller handle exceptions
            self.process.send_signal(signum)
            return

    async def kill(self, restart: bool = False) -> None:
        """Kill the provisioner and optionally restart."""
        if self.process:
            if hasattr(signal, "SIGKILL"):  # type:ignore[unreachable]
                # If available, give preference to signalling the process-group over `kill()`.
                try:
                    await self.send_signal(signal.SIGKILL)
                    return
                except OSError:
                    pass
            try:
                self.process.kill()
            except OSError as e:
                LocalProvisioner._tolerate_no_process(e)

    async def terminate(self, restart: bool = False) -> None:
        """Terminate the provisioner and optionally restart."""
        if self.process:
            if hasattr(signal, "SIGTERM"):  # type:ignore[unreachable]
                # If available, give preference to signalling the process group over `terminate()`.
                try:
                    await self.send_signal(signal.SIGTERM)
                    return
                except OSError:
                    pass
            try:
                self.process.terminate()
            except OSError as e:
                LocalProvisioner._tolerate_no_process(e)

    @staticmethod
    def _tolerate_no_process(os_error: OSError) -> None:
        # In Windows, we will get an Access Denied error if the process
        # has already terminated. Ignore it.
        if sys.platform == "win32":
            if os_error.winerror != 5:
                raise
        # On Unix, we may get an ESRCH error (or ProcessLookupError instance) if
        # the process has already terminated. Ignore it.
        else:
            from errno import ESRCH

            if not isinstance(os_error, ProcessLookupError) or os_error.errno != ESRCH:
                raise

    async def cleanup(self, restart: bool = False) -> None:
        """Clean up the resources used by the provisioner and optionally restart."""
        if self.ports_cached and not restart:
            # provisioner is about to be destroyed, return cached ports
            lpc = LocalPortCache.instance()
            ports = (
                self.connection_info["shell_port"],
                self.connection_info["iopub_port"],
                self.connection_info["stdin_port"],
                self.connection_info["hb_port"],
                self.connection_info["control_port"],
            )
            for port in ports:
                if TYPE_CHECKING:
                    assert isinstance(port, int)
                lpc.return_port(port)

    async def pre_launch(self, **kwargs: Any) -> Dict[str, Any]:
        """Perform any steps in preparation for kernel process launch.

        This includes applying additional substitutions to the kernel launch command and env.
        It also includes preparation of launch parameters.

        Returns the updated kwargs.
        """

        # This should be considered temporary until a better division of labor can be defined.
        km = self.parent
        if km:
            if km.transport == "tcp" and not is_local_ip(km.ip):
                msg = (
                    "Can only launch a kernel on a local interface. "
                    f"This one is not: {km.ip}."
                    "Make sure that the '*_address' attributes are "
                    "configured properly. "
                    f"Currently valid addresses are: {local_ips()}"
                )
                raise RuntimeError(msg)
            # build the Popen cmd
            extra_arguments = kwargs.pop("extra_arguments", [])

            # write connection file / get default ports
            # TODO - change when handshake pattern is adopted
            if km.cache_ports and not self.ports_cached:
                lpc = LocalPortCache.instance()
                km.shell_port = lpc.find_available_port(km.ip)
                km.iopub_port = lpc.find_available_port(km.ip)
                km.stdin_port = lpc.find_available_port(km.ip)
                km.hb_port = lpc.find_available_port(km.ip)
                km.control_port = lpc.find_available_port(km.ip)
                self.ports_cached = True
            if "env" in kwargs:
                jupyter_session = kwargs["env"].get("JPY_SESSION_NAME", "")
                km.write_connection_file(jupyter_session=jupyter_session)
            else:
                km.write_connection_file()
            self.connection_info = km.get_connection_info()

            kernel_cmd = km.format_kernel_cmd(
                extra_arguments=extra_arguments
            )  # This needs to remain here for b/c
        else:
            extra_arguments = kwargs.pop("extra_arguments", [])
            kernel_cmd = self.kernel_spec.argv + extra_arguments

        return await super().pre_launch(cmd=kernel_cmd, **kwargs)

    async def launch_kernel(self, cmd: List[str], **kwargs: Any) -> KernelConnectionInfo:
        """Launch a kernel with a command."""
        scrubbed_kwargs = LocalProvisioner._scrub_kwargs(kwargs)
        self.process = launch_kernel(cmd, **scrubbed_kwargs)
        pgid = None
        if hasattr(os, "getpgid"):
            try:
                pgid = os.getpgid(self.process.pid)
            except OSError:
                pass

        self.pid = self.process.pid
        self.pgid = pgid
        return self.connection_info

    @staticmethod
    def _scrub_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Remove any keyword arguments that Popen does not tolerate."""
        keywords_to_scrub: List[str] = ["extra_arguments", "kernel_id"]
        scrubbed_kwargs = kwargs.copy()
        for kw in keywords_to_scrub:
            scrubbed_kwargs.pop(kw, None)
        return scrubbed_kwargs

    async def get_provisioner_info(self) -> Dict:
        """Captures the base information necessary for persistence relative to this instance."""
        provisioner_info = await super().get_provisioner_info()
        provisioner_info.update({"pid": self.pid, "pgid": self.pgid, "ip": self.ip})
        return provisioner_info

    async def load_provisioner_info(self, provisioner_info: Dict) -> None:
        """Loads the base information necessary for persistence relative to this instance."""
        await super().load_provisioner_info(provisioner_info)
        self.pid = provisioner_info["pid"]
        self.pgid = provisioner_info["pgid"]
        self.ip = provisioner_info["ip"]

# === NexusCore/openenv\Lib\site-packages\matplotlib\sphinxext\mathmpl.py ===
r"""
A role and directive to display mathtext in Sphinx
==================================================

The ``mathmpl`` Sphinx extension creates a mathtext image in Matplotlib and
shows it in html output. Thus, it is a true and faithful representation of what
you will see if you pass a given LaTeX string to Matplotlib (see
:ref:`mathtext`).

.. warning::
    In most cases, you will likely want to use one of `Sphinx's builtin Math
    extensions
    <https://www.sphinx-doc.org/en/master/usage/extensions/math.html>`__
    instead of this one. The builtin Sphinx math directive uses MathJax to
    render mathematical expressions, and addresses accessibility concerns that
    ``mathmpl`` doesn't address.

Mathtext may be included in two ways:

1. Inline, using the role::

     This text uses inline math: :mathmpl:`\alpha > \beta`.

   which produces:

     This text uses inline math: :mathmpl:`\alpha > \beta`.

2. Standalone, using the directive::

     Here is some standalone math:

     .. mathmpl::

         \alpha > \beta

   which produces:

     Here is some standalone math:

     .. mathmpl::

         \alpha > \beta

Options
-------

The ``mathmpl`` role and directive both support the following options:

fontset : str, default: 'cm'
    The font set to use when displaying math. See :rc:`mathtext.fontset`.

fontsize : float
    The font size, in points. Defaults to the value from the extension
    configuration option defined below.

Configuration options
---------------------

The mathtext extension has the following configuration options:

mathmpl_fontsize : float, default: 10.0
    Default font size, in points.

mathmpl_srcset : list of str, default: []
    Additional image sizes to generate when embedding in HTML, to support
    `responsive resolution images
    <https://developer.mozilla.org/en-US/docs/Learn/HTML/Multimedia_and_embedding/Responsive_images>`__.
    The list should contain additional x-descriptors (``'1.5x'``, ``'2x'``,
    etc.) to generate (1x is the default and always included.)

"""

import hashlib
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import Directive, directives
import sphinx
from sphinx.errors import ConfigError, ExtensionError

import matplotlib as mpl
from matplotlib import _api, mathtext
from matplotlib.rcsetup import validate_float_or_None


# Define LaTeX math node:
class latex_math(nodes.General, nodes.Element):
    pass


def fontset_choice(arg):
    return directives.choice(arg, mathtext.MathTextParser._font_type_mapping)


def math_role(role, rawtext, text, lineno, inliner,
              options={}, content=[]):
    i = rawtext.find('`')
    latex = rawtext[i+1:-1]
    node = latex_math(rawtext)
    node['latex'] = latex
    node['fontset'] = options.get('fontset', 'cm')
    node['fontsize'] = options.get('fontsize',
                                   setup.app.config.mathmpl_fontsize)
    return [node], []
math_role.options = {'fontset': fontset_choice,
                     'fontsize': validate_float_or_None}


class MathDirective(Directive):
    """
    The ``.. mathmpl::`` directive, as documented in the module's docstring.
    """
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {'fontset': fontset_choice,
                   'fontsize': validate_float_or_None}

    def run(self):
        latex = ''.join(self.content)
        node = latex_math(self.block_text)
        node['latex'] = latex
        node['fontset'] = self.options.get('fontset', 'cm')
        node['fontsize'] = self.options.get('fontsize',
                                            setup.app.config.mathmpl_fontsize)
        return [node]


# This uses mathtext to render the expression
def latex2png(latex, filename, fontset='cm', fontsize=10, dpi=100):
    with mpl.rc_context({'mathtext.fontset': fontset, 'font.size': fontsize}):
        try:
            depth = mathtext.math_to_image(
                f"${latex}$", filename, dpi=dpi, format="png")
        except Exception:
            _api.warn_external(f"Could not render math expression {latex}")
            depth = 0
    return depth


# LaTeX to HTML translation stuff:
def latex2html(node, source):
    inline = isinstance(node.parent, nodes.TextElement)
    latex = node['latex']
    fontset = node['fontset']
    fontsize = node['fontsize']
    name = 'math-{}'.format(
        hashlib.sha256(
            f'{latex}{fontset}{fontsize}'.encode(),
            usedforsecurity=False,
        ).hexdigest()[-10:])

    destdir = Path(setup.app.builder.outdir, '_images', 'mathmpl')
    destdir.mkdir(parents=True, exist_ok=True)

    dest = destdir / f'{name}.png'
    depth = latex2png(latex, dest, fontset, fontsize=fontsize)

    srcset = []
    for size in setup.app.config.mathmpl_srcset:
        filename = f'{name}-{size.replace(".", "_")}.png'
        latex2png(latex, destdir / filename, fontset, fontsize=fontsize,
                  dpi=100 * float(size[:-1]))
        srcset.append(
            f'{setup.app.builder.imgpath}/mathmpl/{filename} {size}')
    if srcset:
        srcset = (f'srcset="{setup.app.builder.imgpath}/mathmpl/{name}.png, ' +
                  ', '.join(srcset) + '" ')

    if inline:
        cls = ''
    else:
        cls = 'class="center" '
    if inline and depth != 0:
        style = 'style="position: relative; bottom: -%dpx"' % (depth + 1)
    else:
        style = ''

    return (f'<img src="{setup.app.builder.imgpath}/mathmpl/{name}.png"'
            f' {srcset}{cls}{style}/>')


def _config_inited(app, config):
    # Check for srcset hidpi images
    for i, size in enumerate(app.config.mathmpl_srcset):
        if size[-1] == 'x':  # "2x" = "2.0"
            try:
                float(size[:-1])
            except ValueError:
                raise ConfigError(
                    f'Invalid value for mathmpl_srcset parameter: {size!r}. '
                    'Must be a list of strings with the multiplicative '
                    'factor followed by an "x".  e.g. ["2.0x", "1.5x"]')
        else:
            raise ConfigError(
                f'Invalid value for mathmpl_srcset parameter: {size!r}. '
                'Must be a list of strings with the multiplicative '
                'factor followed by an "x".  e.g. ["2.0x", "1.5x"]')


def setup(app):
    setup.app = app
    app.add_config_value('mathmpl_fontsize', 10.0, True)
    app.add_config_value('mathmpl_srcset', [], True)
    try:
        app.connect('config-inited', _config_inited)  # Sphinx 1.8+
    except ExtensionError:
        app.connect('env-updated', lambda app, env: _config_inited(app, None))

    # Add visit/depart methods to HTML-Translator:
    def visit_latex_math_html(self, node):
        source = self.document.attributes['source']
        self.body.append(latex2html(node, source))

    def depart_latex_math_html(self, node):
        pass

    # Add visit/depart methods to LaTeX-Translator:
    def visit_latex_math_latex(self, node):
        inline = isinstance(node.parent, nodes.TextElement)
        if inline:
            self.body.append('$%s$' % node['latex'])
        else:
            self.body.extend(['\\begin{equation}',
                              node['latex'],
                              '\\end{equation}'])

    def depart_latex_math_latex(self, node):
        pass

    app.add_node(latex_math,
                 html=(visit_latex_math_html, depart_latex_math_html),
                 latex=(visit_latex_math_latex, depart_latex_math_latex))
    app.add_role('mathmpl', math_role)
    app.add_directive('mathmpl', MathDirective)
    if sphinx.version_info < (1, 8):
        app.add_role('math', math_role)
        app.add_directive('math', MathDirective)

    metadata = {'parallel_read_safe': True, 'parallel_write_safe': True}
    return metadata

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\dialogs\status.py ===
# No cancel button.

import threading
import time

import win32api
import win32con
import win32ui
from pywin.mfc import dialog
from pywin.mfc.thread import WinThread


def MakeProgressDlgTemplate(caption, staticText=""):
    style = (
        win32con.DS_MODALFRAME
        | win32con.WS_POPUP
        | win32con.WS_VISIBLE
        | win32con.WS_CAPTION
        | win32con.WS_SYSMENU
        | win32con.DS_SETFONT
    )
    cs = win32con.WS_CHILD | win32con.WS_VISIBLE

    w = 215
    h = 36  # With button
    h = 40

    dlg = [
        [caption, (0, 0, w, h), style, None, (8, "MS Sans Serif")],
    ]

    s = win32con.WS_TABSTOP | cs

    dlg.append([130, staticText, 1000, (7, 7, w - 7, h - 32), cs | win32con.SS_LEFT])

    #    dlg.append([128,
    # 		"Cancel",
    # 		win32con.IDCANCEL,
    # 		(w - 60, h - 18, 50, 14), s | win32con.BS_PUSHBUTTON])

    return dlg


class CStatusProgressDialog(dialog.Dialog):
    def __init__(self, title, msg="", maxticks=100, tickincr=1):
        self.initMsg = msg
        templ = MakeProgressDlgTemplate(title, msg)
        dialog.Dialog.__init__(self, templ)
        self.maxticks = maxticks
        self.tickincr = tickincr
        self.pbar = None

    def OnInitDialog(self):
        rc = dialog.Dialog.OnInitDialog(self)
        self.static = self.GetDlgItem(1000)
        self.pbar = win32ui.CreateProgressCtrl()
        self.pbar.CreateWindow(
            win32con.WS_CHILD | win32con.WS_VISIBLE, (10, 30, 310, 44), self, 1001
        )
        self.pbar.SetRange(0, self.maxticks)
        self.pbar.SetStep(self.tickincr)
        self.progress = 0
        self.pincr = 5
        return rc

    def Close(self):
        self.EndDialog(0)

    def SetMaxTicks(self, maxticks):
        if self.pbar is not None:
            self.pbar.SetRange(0, maxticks)

    def Tick(self):
        if self.pbar is not None:
            self.pbar.StepIt()

    def SetTitle(self, text):
        self.SetWindowText(text)

    def SetText(self, text):
        self.SetDlgItemText(1000, text)

    def Set(self, pos, max=None):
        if self.pbar is not None:
            self.pbar.SetPos(pos)
            if max is not None:
                self.pbar.SetRange(0, max)


# a progress dialog created in a new thread - especially suitable for
# console apps with no message loop.
MYWM_SETTITLE = win32con.WM_USER + 10
MYWM_SETMSG = win32con.WM_USER + 11
MYWM_TICK = win32con.WM_USER + 12
MYWM_SETMAXTICKS = win32con.WM_USER + 13
MYWM_SET = win32con.WM_USER + 14


class CThreadedStatusProcessDialog(CStatusProgressDialog):
    def __init__(self, title, msg="", maxticks=100, tickincr=1):
        self.title = title
        self.msg = msg
        self.threadid = win32api.GetCurrentThreadId()
        CStatusProgressDialog.__init__(self, title, msg, maxticks, tickincr)

    def OnInitDialog(self):
        rc = CStatusProgressDialog.OnInitDialog(self)
        self.HookMessage(self.OnTitle, MYWM_SETTITLE)
        self.HookMessage(self.OnMsg, MYWM_SETMSG)
        self.HookMessage(self.OnTick, MYWM_TICK)
        self.HookMessage(self.OnMaxTicks, MYWM_SETMAXTICKS)
        self.HookMessage(self.OnSet, MYWM_SET)
        return rc

    def _Send(self, msg):
        try:
            self.PostMessage(msg)
        except win32ui.error:
            # the user closed the window - but this does not cancel the
            # process - so just ignore it.
            pass

    def OnTitle(self, msg):
        CStatusProgressDialog.SetTitle(self, self.title)

    def OnMsg(self, msg):
        CStatusProgressDialog.SetText(self, self.msg)

    def OnTick(self, msg):
        CStatusProgressDialog.Tick(self)

    def OnMaxTicks(self, msg):
        CStatusProgressDialog.SetMaxTicks(self, self.maxticks)

    def OnSet(self, msg):
        CStatusProgressDialog.Set(self, self.pos, self.max)

    def Close(self):
        assert self.threadid, "No thread!"
        win32api.PostThreadMessage(self.threadid, win32con.WM_QUIT, 0, 0)

    def SetMaxTicks(self, maxticks):
        self.maxticks = maxticks
        self._Send(MYWM_SETMAXTICKS)

    def SetTitle(self, title):
        self.title = title
        self._Send(MYWM_SETTITLE)

    def SetText(self, text):
        self.msg = text
        self._Send(MYWM_SETMSG)

    def Tick(self):
        self._Send(MYWM_TICK)

    def Set(self, pos, max=None):
        self.pos = pos
        self.max = max
        self._Send(MYWM_SET)


class ProgressThread(WinThread):
    def __init__(self, title, msg="", maxticks=100, tickincr=1):
        self.title = title
        self.msg = msg
        self.maxticks = maxticks
        self.tickincr = tickincr
        self.dialog = None
        WinThread.__init__(self)
        self.createdEvent = threading.Event()

    def InitInstance(self):
        self.dialog = CThreadedStatusProcessDialog(
            self.title, self.msg, self.maxticks, self.tickincr
        )
        self.dialog.CreateWindow()
        try:
            self.dialog.SetForegroundWindow()
        except win32ui.error:
            pass
        self.createdEvent.set()
        return WinThread.InitInstance(self)

    def ExitInstance(self):
        return 0


def StatusProgressDialog(title, msg="", maxticks=100, parent=None):
    d = CStatusProgressDialog(title, msg, maxticks)
    d.CreateWindow(parent)
    return d


def ThreadedStatusProgressDialog(title, msg="", maxticks=100):
    t = ProgressThread(title, msg, maxticks)
    t.CreateThread()
    # Need to run a basic "PumpWaitingMessages" loop just incase we are
    # running inside Pythonwin.
    # Basic timeout incase things go terribly wrong.  Ideally we should use
    # win32event.MsgWaitForMultipleObjects(), but we use a threading module
    # event - so use a dumb strategy
    end_time = time.time() + 10
    while time.time() < end_time:
        if t.createdEvent.isSet():
            break
        win32ui.PumpWaitingMessages()
        time.sleep(0.1)
    return t.dialog


def demo():
    d = StatusProgressDialog("A Demo", "Doing something...")
    import win32api

    for i in range(100):
        if i == 50:
            d.SetText("Getting there...")
        if i == 90:
            d.SetText("Nearly done...")
        win32api.Sleep(20)
        d.Tick()
    d.Close()


def thread_demo():
    d = ThreadedStatusProgressDialog("A threaded demo", "Doing something")
    import win32api

    for i in range(100):
        if i == 50:
            d.SetText("Getting there...")
        if i == 90:
            d.SetText("Nearly done...")
        win32api.Sleep(20)
        d.Tick()
    d.Close()


if __name__ == "__main__":
    thread_demo()
    # demo()

# === NexusCore/openenv\Lib\site-packages\trio\_core\_tests\test_thread_cache.py ===
from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager
from queue import Queue
from typing import TYPE_CHECKING, NoReturn

import pytest

from .. import _thread_cache
from .._thread_cache import ThreadCache, start_thread_soon
from .tutil import gc_collect_harder, slow

if TYPE_CHECKING:
    from collections.abc import Iterator

    from outcome import Outcome


def test_thread_cache_basics() -> None:
    q: Queue[Outcome[object]] = Queue()

    def fn() -> NoReturn:
        raise RuntimeError("hi")

    def deliver(outcome: Outcome[object]) -> None:
        q.put(outcome)

    start_thread_soon(fn, deliver)

    outcome = q.get()
    with pytest.raises(RuntimeError, match="hi"):
        outcome.unwrap()


def test_thread_cache_deref() -> None:
    res = [False]

    class del_me:
        def __call__(self) -> int:
            return 42

        def __del__(self) -> None:
            res[0] = True

    q: Queue[Outcome[int]] = Queue()

    def deliver(outcome: Outcome[int]) -> None:
        q.put(outcome)

    start_thread_soon(del_me(), deliver)
    outcome = q.get()
    assert outcome.unwrap() == 42

    gc_collect_harder()
    assert res[0]


@slow
def test_spawning_new_thread_from_deliver_reuses_starting_thread() -> None:
    # We know that no-one else is using the thread cache, so if we keep
    # submitting new jobs the instant the previous one is finished, we should
    # keep getting the same thread over and over. This tests both that the
    # thread cache is LIFO, and that threads can be assigned new work *before*
    # deliver exits.

    # Make sure there are a few threads running, so if we weren't LIFO then we
    # could grab the wrong one.
    q: Queue[Outcome[object]] = Queue()
    COUNT = 5
    for _ in range(COUNT):
        start_thread_soon(lambda: time.sleep(1), lambda result: q.put(result))
    for _ in range(COUNT):
        q.get().unwrap()

    seen_threads = set()
    done = threading.Event()

    def deliver(n: int, _: object) -> None:
        print(n)
        seen_threads.add(threading.current_thread())
        if n == 0:
            done.set()
        else:
            start_thread_soon(lambda: None, lambda _: deliver(n - 1, _))

    start_thread_soon(lambda: None, lambda _: deliver(5, _))

    done.wait()

    assert len(seen_threads) == 1


@slow
def test_idle_threads_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    # Temporarily set the idle timeout to something tiny, to speed up the
    # test. (But non-zero, so that the worker loop will at least yield the
    # CPU.)
    monkeypatch.setattr(_thread_cache, "IDLE_TIMEOUT", 0.0001)

    q: Queue[threading.Thread] = Queue()
    start_thread_soon(lambda: None, lambda _: q.put(threading.current_thread()))
    seen_thread = q.get()
    # Since the idle timeout is 0, after sleeping for 1 second, the thread
    # should have exited
    time.sleep(1)
    assert not seen_thread.is_alive()


@contextmanager
def _join_started_threads() -> Iterator[None]:
    before = frozenset(threading.enumerate())
    try:
        yield
    finally:
        for thread in threading.enumerate():
            if thread not in before:
                thread.join(timeout=1.0)
                assert not thread.is_alive()


def test_race_between_idle_exit_and_job_assignment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # This is a lock where the first few times you try to acquire it with a
    # timeout, it waits until the lock is available and then pretends to time
    # out. Using this in our thread cache implementation causes the following
    # sequence:
    #
    # 1. start_thread_soon grabs the worker thread, assigns it a job, and
    #    releases its lock.
    # 2. The worker thread wakes up (because the lock has been released), but
    #    the JankyLock lies to it and tells it that the lock timed out. So the
    #    worker thread tries to exit.
    # 3. The worker thread checks for the race between exiting and being
    #    assigned a job, and discovers that it *is* in the process of being
    #    assigned a job, so it loops around and tries to acquire the lock
    #    again.
    # 4. Eventually the JankyLock admits that the lock is available, and
    #    everything proceeds as normal.

    class JankyLock:
        def __init__(self) -> None:
            self._lock = threading.Lock()
            self._counter = 3

        def acquire(self, timeout: int = -1) -> bool:
            got_it = self._lock.acquire(timeout=timeout)
            if timeout == -1:
                return True
            elif got_it:
                if self._counter > 0:
                    self._counter -= 1
                    self._lock.release()
                    return False
                return True
            else:
                return False

        def release(self) -> None:
            self._lock.release()

    monkeypatch.setattr(_thread_cache, "Lock", JankyLock)

    with _join_started_threads():
        tc = ThreadCache()
        done = threading.Event()
        tc.start_thread_soon(lambda: None, lambda _: done.set())
        done.wait()
        # Let's kill the thread we started, so it doesn't hang around until the
        # test suite finishes. Doesn't really do any harm, but it can be confusing
        # to see it in debug output.
        monkeypatch.setattr(_thread_cache, "IDLE_TIMEOUT", 0.0001)
        tc.start_thread_soon(lambda: None, lambda _: None)


def test_raise_in_deliver(capfd: pytest.CaptureFixture[str]) -> None:
    seen_threads = set()

    def track_threads() -> None:
        seen_threads.add(threading.current_thread())

    def deliver(_: object) -> NoReturn:
        done.set()
        raise RuntimeError("don't do this")

    done = threading.Event()
    start_thread_soon(track_threads, deliver)
    done.wait()
    done = threading.Event()
    start_thread_soon(track_threads, lambda _: done.set())
    done.wait()
    assert len(seen_threads) == 1
    err = capfd.readouterr().err
    assert "don't do this" in err
    assert "delivering result" in err


@pytest.mark.skipif(not hasattr(os, "fork"), reason="os.fork isn't supported")
def test_clear_thread_cache_after_fork() -> None:
    assert hasattr(os, "fork")

    def foo() -> None:
        pass

    # ensure the thread cache exists
    done = threading.Event()
    start_thread_soon(foo, lambda _: done.set())
    done.wait()

    child_pid = os.fork()

    # try using it
    done = threading.Event()
    start_thread_soon(foo, lambda _: done.set())
    done.wait()

    if child_pid != 0:
        # if this test fails, this will hang, triggering a timeout.
        os.waitpid(child_pid, 0)
    else:
        # this is necessary because os._exit doesn't unwind the stack,
        # so coverage doesn't get to automatically stop and save
        # coverage information.
        try:
            import coverage

            cov = coverage.Coverage.current()
            # the following pragmas are necessary because if coverage:
            #  - isn't running, then it can't record the branch not
            #    taken
            #  - isn't installed, then it can't record the ImportError

            if cov:  # pragma: no branch
                cov.stop()
                cov.save()
        except ImportError:  # pragma: no cover
            pass

        os._exit(0)  # pragma: no cover  # coverage was stopped above.

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\ansi.py ===
import re
import sys
from contextlib import suppress
from typing import Iterable, NamedTuple, Optional

from .color import Color
from .style import Style
from .text import Text

re_ansi = re.compile(
    r"""
(?:\x1b[0-?])|
(?:\x1b\](.*?)\x1b\\)|
(?:\x1b([(@-Z\\-_]|\[[0-?]*[ -/]*[@-~]))
""",
    re.VERBOSE,
)


class _AnsiToken(NamedTuple):
    """Result of ansi tokenized string."""

    plain: str = ""
    sgr: Optional[str] = ""
    osc: Optional[str] = ""


def _ansi_tokenize(ansi_text: str) -> Iterable[_AnsiToken]:
    """Tokenize a string in to plain text and ANSI codes.

    Args:
        ansi_text (str): A String containing ANSI codes.

    Yields:
        AnsiToken: A named tuple of (plain, sgr, osc)
    """

    position = 0
    sgr: Optional[str]
    osc: Optional[str]
    for match in re_ansi.finditer(ansi_text):
        start, end = match.span(0)
        osc, sgr = match.groups()
        if start > position:
            yield _AnsiToken(ansi_text[position:start])
        if sgr:
            if sgr == "(":
                position = end + 1
                continue
            if sgr.endswith("m"):
                yield _AnsiToken("", sgr[1:-1], osc)
        else:
            yield _AnsiToken("", sgr, osc)
        position = end
    if position < len(ansi_text):
        yield _AnsiToken(ansi_text[position:])


SGR_STYLE_MAP = {
    1: "bold",
    2: "dim",
    3: "italic",
    4: "underline",
    5: "blink",
    6: "blink2",
    7: "reverse",
    8: "conceal",
    9: "strike",
    21: "underline2",
    22: "not dim not bold",
    23: "not italic",
    24: "not underline",
    25: "not blink",
    26: "not blink2",
    27: "not reverse",
    28: "not conceal",
    29: "not strike",
    30: "color(0)",
    31: "color(1)",
    32: "color(2)",
    33: "color(3)",
    34: "color(4)",
    35: "color(5)",
    36: "color(6)",
    37: "color(7)",
    39: "default",
    40: "on color(0)",
    41: "on color(1)",
    42: "on color(2)",
    43: "on color(3)",
    44: "on color(4)",
    45: "on color(5)",
    46: "on color(6)",
    47: "on color(7)",
    49: "on default",
    51: "frame",
    52: "encircle",
    53: "overline",
    54: "not frame not encircle",
    55: "not overline",
    90: "color(8)",
    91: "color(9)",
    92: "color(10)",
    93: "color(11)",
    94: "color(12)",
    95: "color(13)",
    96: "color(14)",
    97: "color(15)",
    100: "on color(8)",
    101: "on color(9)",
    102: "on color(10)",
    103: "on color(11)",
    104: "on color(12)",
    105: "on color(13)",
    106: "on color(14)",
    107: "on color(15)",
}


class AnsiDecoder:
    """Translate ANSI code in to styled Text."""

    def __init__(self) -> None:
        self.style = Style.null()

    def decode(self, terminal_text: str) -> Iterable[Text]:
        """Decode ANSI codes in an iterable of lines.

        Args:
            lines (Iterable[str]): An iterable of lines of terminal output.

        Yields:
            Text: Marked up Text.
        """
        for line in terminal_text.splitlines():
            yield self.decode_line(line)

    def decode_line(self, line: str) -> Text:
        """Decode a line containing ansi codes.

        Args:
            line (str): A line of terminal output.

        Returns:
            Text: A Text instance marked up according to ansi codes.
        """
        from_ansi = Color.from_ansi
        from_rgb = Color.from_rgb
        _Style = Style
        text = Text()
        append = text.append
        line = line.rsplit("\r", 1)[-1]
        for plain_text, sgr, osc in _ansi_tokenize(line):
            if plain_text:
                append(plain_text, self.style or None)
            elif osc is not None:
                if osc.startswith("8;"):
                    _params, semicolon, link = osc[2:].partition(";")
                    if semicolon:
                        self.style = self.style.update_link(link or None)
            elif sgr is not None:
                # Translate in to semi-colon separated codes
                # Ignore invalid codes, because we want to be lenient
                codes = [
                    min(255, int(_code) if _code else 0)
                    for _code in sgr.split(";")
                    if _code.isdigit() or _code == ""
                ]
                iter_codes = iter(codes)
                for code in iter_codes:
                    if code == 0:
                        # reset
                        self.style = _Style.null()
                    elif code in SGR_STYLE_MAP:
                        # styles
                        self.style += _Style.parse(SGR_STYLE_MAP[code])
                    elif code == 38:
                        #  Foreground
                        with suppress(StopIteration):
                            color_type = next(iter_codes)
                            if color_type == 5:
                                self.style += _Style.from_color(
                                    from_ansi(next(iter_codes))
                                )
                            elif color_type == 2:
                                self.style += _Style.from_color(
                                    from_rgb(
                                        next(iter_codes),
                                        next(iter_codes),
                                        next(iter_codes),
                                    )
                                )
                    elif code == 48:
                        # Background
                        with suppress(StopIteration):
                            color_type = next(iter_codes)
                            if color_type == 5:
                                self.style += _Style.from_color(
                                    None, from_ansi(next(iter_codes))
                                )
                            elif color_type == 2:
                                self.style += _Style.from_color(
                                    None,
                                    from_rgb(
                                        next(iter_codes),
                                        next(iter_codes),
                                        next(iter_codes),
                                    ),
                                )

        return text


if sys.platform != "win32" and __name__ == "__main__":  # pragma: no cover
    import io
    import os
    import pty
    import sys

    decoder = AnsiDecoder()

    stdout = io.BytesIO()

    def read(fd: int) -> bytes:
        data = os.read(fd, 1024)
        stdout.write(data)
        return data

    pty.spawn(sys.argv[1:], read)

    from .console import Console

    console = Console(record=True)

    stdout_result = stdout.getvalue().decode("utf-8")
    print(stdout_result)

    for line in decoder.decode(stdout_result):
        console.print(line)

    console.save_html("stdout.html")

# === NexusCore/openenv\Lib\site-packages\rich\ansi.py ===
import re
import sys
from contextlib import suppress
from typing import Iterable, NamedTuple, Optional

from .color import Color
from .style import Style
from .text import Text

re_ansi = re.compile(
    r"""
(?:\x1b[0-?])|
(?:\x1b\](.*?)\x1b\\)|
(?:\x1b([(@-Z\\-_]|\[[0-?]*[ -/]*[@-~]))
""",
    re.VERBOSE,
)


class _AnsiToken(NamedTuple):
    """Result of ansi tokenized string."""

    plain: str = ""
    sgr: Optional[str] = ""
    osc: Optional[str] = ""


def _ansi_tokenize(ansi_text: str) -> Iterable[_AnsiToken]:
    """Tokenize a string in to plain text and ANSI codes.

    Args:
        ansi_text (str): A String containing ANSI codes.

    Yields:
        AnsiToken: A named tuple of (plain, sgr, osc)
    """

    position = 0
    sgr: Optional[str]
    osc: Optional[str]
    for match in re_ansi.finditer(ansi_text):
        start, end = match.span(0)
        osc, sgr = match.groups()
        if start > position:
            yield _AnsiToken(ansi_text[position:start])
        if sgr:
            if sgr == "(":
                position = end + 1
                continue
            if sgr.endswith("m"):
                yield _AnsiToken("", sgr[1:-1], osc)
        else:
            yield _AnsiToken("", sgr, osc)
        position = end
    if position < len(ansi_text):
        yield _AnsiToken(ansi_text[position:])


SGR_STYLE_MAP = {
    1: "bold",
    2: "dim",
    3: "italic",
    4: "underline",
    5: "blink",
    6: "blink2",
    7: "reverse",
    8: "conceal",
    9: "strike",
    21: "underline2",
    22: "not dim not bold",
    23: "not italic",
    24: "not underline",
    25: "not blink",
    26: "not blink2",
    27: "not reverse",
    28: "not conceal",
    29: "not strike",
    30: "color(0)",
    31: "color(1)",
    32: "color(2)",
    33: "color(3)",
    34: "color(4)",
    35: "color(5)",
    36: "color(6)",
    37: "color(7)",
    39: "default",
    40: "on color(0)",
    41: "on color(1)",
    42: "on color(2)",
    43: "on color(3)",
    44: "on color(4)",
    45: "on color(5)",
    46: "on color(6)",
    47: "on color(7)",
    49: "on default",
    51: "frame",
    52: "encircle",
    53: "overline",
    54: "not frame not encircle",
    55: "not overline",
    90: "color(8)",
    91: "color(9)",
    92: "color(10)",
    93: "color(11)",
    94: "color(12)",
    95: "color(13)",
    96: "color(14)",
    97: "color(15)",
    100: "on color(8)",
    101: "on color(9)",
    102: "on color(10)",
    103: "on color(11)",
    104: "on color(12)",
    105: "on color(13)",
    106: "on color(14)",
    107: "on color(15)",
}


class AnsiDecoder:
    """Translate ANSI code in to styled Text."""

    def __init__(self) -> None:
        self.style = Style.null()

    def decode(self, terminal_text: str) -> Iterable[Text]:
        """Decode ANSI codes in an iterable of lines.

        Args:
            lines (Iterable[str]): An iterable of lines of terminal output.

        Yields:
            Text: Marked up Text.
        """
        for line in terminal_text.splitlines():
            yield self.decode_line(line)

    def decode_line(self, line: str) -> Text:
        """Decode a line containing ansi codes.

        Args:
            line (str): A line of terminal output.

        Returns:
            Text: A Text instance marked up according to ansi codes.
        """
        from_ansi = Color.from_ansi
        from_rgb = Color.from_rgb
        _Style = Style
        text = Text()
        append = text.append
        line = line.rsplit("\r", 1)[-1]
        for plain_text, sgr, osc in _ansi_tokenize(line):
            if plain_text:
                append(plain_text, self.style or None)
            elif osc is not None:
                if osc.startswith("8;"):
                    _params, semicolon, link = osc[2:].partition(";")
                    if semicolon:
                        self.style = self.style.update_link(link or None)
            elif sgr is not None:
                # Translate in to semi-colon separated codes
                # Ignore invalid codes, because we want to be lenient
                codes = [
                    min(255, int(_code) if _code else 0)
                    for _code in sgr.split(";")
                    if _code.isdigit() or _code == ""
                ]
                iter_codes = iter(codes)
                for code in iter_codes:
                    if code == 0:
                        # reset
                        self.style = _Style.null()
                    elif code in SGR_STYLE_MAP:
                        # styles
                        self.style += _Style.parse(SGR_STYLE_MAP[code])
                    elif code == 38:
                        #  Foreground
                        with suppress(StopIteration):
                            color_type = next(iter_codes)
                            if color_type == 5:
                                self.style += _Style.from_color(
                                    from_ansi(next(iter_codes))
                                )
                            elif color_type == 2:
                                self.style += _Style.from_color(
                                    from_rgb(
                                        next(iter_codes),
                                        next(iter_codes),
                                        next(iter_codes),
                                    )
                                )
                    elif code == 48:
                        # Background
                        with suppress(StopIteration):
                            color_type = next(iter_codes)
                            if color_type == 5:
                                self.style += _Style.from_color(
                                    None, from_ansi(next(iter_codes))
                                )
                            elif color_type == 2:
                                self.style += _Style.from_color(
                                    None,
                                    from_rgb(
                                        next(iter_codes),
                                        next(iter_codes),
                                        next(iter_codes),
                                    ),
                                )

        return text


if sys.platform != "win32" and __name__ == "__main__":  # pragma: no cover
    import io
    import os
    import pty
    import sys

    decoder = AnsiDecoder()

    stdout = io.BytesIO()

    def read(fd: int) -> bytes:
        data = os.read(fd, 1024)
        stdout.write(data)
        return data

    pty.spawn(sys.argv[1:], read)

    from .console import Console

    console = Console(record=True)

    stdout_result = stdout.getvalue().decode("utf-8")
    print(stdout_result)

    for line in decoder.decode(stdout_result):
        console.print(line)

    console.save_html("stdout.html")

# === NexusCore/openenv\Lib\site-packages\fontTools\pens\filterPen.py ===
from __future__ import annotations

from fontTools.pens.basePen import AbstractPen, DecomposingPen
from fontTools.pens.pointPen import AbstractPointPen, DecomposingPointPen
from fontTools.pens.recordingPen import RecordingPen


class _PassThruComponentsMixin(object):
    def addComponent(self, glyphName, transformation, **kwargs):
        self._outPen.addComponent(glyphName, transformation, **kwargs)


class FilterPen(_PassThruComponentsMixin, AbstractPen):
    """Base class for pens that apply some transformation to the coordinates
    they receive and pass them to another pen.

    You can override any of its methods. The default implementation does
    nothing, but passes the commands unmodified to the other pen.

    >>> from fontTools.pens.recordingPen import RecordingPen
    >>> rec = RecordingPen()
    >>> pen = FilterPen(rec)
    >>> v = iter(rec.value)

    >>> pen.moveTo((0, 0))
    >>> next(v)
    ('moveTo', ((0, 0),))

    >>> pen.lineTo((1, 1))
    >>> next(v)
    ('lineTo', ((1, 1),))

    >>> pen.curveTo((2, 2), (3, 3), (4, 4))
    >>> next(v)
    ('curveTo', ((2, 2), (3, 3), (4, 4)))

    >>> pen.qCurveTo((5, 5), (6, 6), (7, 7), (8, 8))
    >>> next(v)
    ('qCurveTo', ((5, 5), (6, 6), (7, 7), (8, 8)))

    >>> pen.closePath()
    >>> next(v)
    ('closePath', ())

    >>> pen.moveTo((9, 9))
    >>> next(v)
    ('moveTo', ((9, 9),))

    >>> pen.endPath()
    >>> next(v)
    ('endPath', ())

    >>> pen.addComponent('foo', (1, 0, 0, 1, 0, 0))
    >>> next(v)
    ('addComponent', ('foo', (1, 0, 0, 1, 0, 0)))
    """

    def __init__(self, outPen):
        self._outPen = outPen
        self.current_pt = None

    def moveTo(self, pt):
        self._outPen.moveTo(pt)
        self.current_pt = pt

    def lineTo(self, pt):
        self._outPen.lineTo(pt)
        self.current_pt = pt

    def curveTo(self, *points):
        self._outPen.curveTo(*points)
        self.current_pt = points[-1]

    def qCurveTo(self, *points):
        self._outPen.qCurveTo(*points)
        self.current_pt = points[-1]

    def closePath(self):
        self._outPen.closePath()
        self.current_pt = None

    def endPath(self):
        self._outPen.endPath()
        self.current_pt = None


class ContourFilterPen(_PassThruComponentsMixin, RecordingPen):
    """A "buffered" filter pen that accumulates contour data, passes
    it through a ``filterContour`` method when the contour is closed or ended,
    and finally draws the result with the output pen.

    Components are passed through unchanged.
    """

    def __init__(self, outPen):
        super(ContourFilterPen, self).__init__()
        self._outPen = outPen

    def closePath(self):
        super(ContourFilterPen, self).closePath()
        self._flushContour()

    def endPath(self):
        super(ContourFilterPen, self).endPath()
        self._flushContour()

    def _flushContour(self):
        result = self.filterContour(self.value)
        if result is not None:
            self.value = result
        self.replay(self._outPen)
        self.value = []

    def filterContour(self, contour):
        """Subclasses must override this to perform the filtering.

        The contour is a list of pen (operator, operands) tuples.
        Operators are strings corresponding to the AbstractPen methods:
        "moveTo", "lineTo", "curveTo", "qCurveTo", "closePath" and
        "endPath". The operands are the positional arguments that are
        passed to each method.

        If the method doesn't return a value (i.e. returns None), it's
        assumed that the argument was modified in-place.
        Otherwise, the return value is drawn with the output pen.
        """
        return  # or return contour


class FilterPointPen(_PassThruComponentsMixin, AbstractPointPen):
    """Baseclass for point pens that apply some transformation to the
    coordinates they receive and pass them to another point pen.

    You can override any of its methods. The default implementation does
    nothing, but passes the commands unmodified to the other pen.

    >>> from fontTools.pens.recordingPen import RecordingPointPen
    >>> rec = RecordingPointPen()
    >>> pen = FilterPointPen(rec)
    >>> v = iter(rec.value)
    >>> pen.beginPath(identifier="abc")
    >>> next(v)
    ('beginPath', (), {'identifier': 'abc'})
    >>> pen.addPoint((1, 2), "line", False)
    >>> next(v)
    ('addPoint', ((1, 2), 'line', False, None), {})
    >>> pen.addComponent("a", (2, 0, 0, 2, 10, -10), identifier="0001")
    >>> next(v)
    ('addComponent', ('a', (2, 0, 0, 2, 10, -10)), {'identifier': '0001'})
    >>> pen.endPath()
    >>> next(v)
    ('endPath', (), {})
    """

    def __init__(self, outPen):
        self._outPen = outPen

    def beginPath(self, **kwargs):
        self._outPen.beginPath(**kwargs)

    def endPath(self):
        self._outPen.endPath()

    def addPoint(self, pt, segmentType=None, smooth=False, name=None, **kwargs):
        self._outPen.addPoint(pt, segmentType, smooth, name, **kwargs)


class _DecomposingFilterPenMixin:
    """Mixin class that decomposes components as regular contours.

    Shared by both DecomposingFilterPen and DecomposingFilterPointPen.

    Takes two required parameters, another (segment or point) pen 'outPen' to draw
    with, and a 'glyphSet' dict of drawable glyph objects to draw components from.

    The 'skipMissingComponents' and 'reverseFlipped' optional arguments work the
    same as in the DecomposingPen/DecomposingPointPen. Both are False by default.

    In addition, the decomposing filter pens also take the following two options:

    'include' is an optional set of component base glyph names to consider for
    decomposition; the default include=None means decompose all components no matter
    the base glyph name).

    'decomposeNested' (bool) controls whether to recurse decomposition into nested
    components of components (this only matters when 'include' was also provided);
    if False, only decompose top-level components included in the set, but not
    also their children.
    """

    # raises MissingComponentError if base glyph is not found in glyphSet
    skipMissingComponents = False

    def __init__(
        self,
        outPen,
        glyphSet,
        skipMissingComponents=None,
        reverseFlipped=False,
        include: set[str] | None = None,
        decomposeNested: bool = True,
    ):
        super().__init__(
            outPen=outPen,
            glyphSet=glyphSet,
            skipMissingComponents=skipMissingComponents,
            reverseFlipped=reverseFlipped,
        )
        self.include = include
        self.decomposeNested = decomposeNested

    def addComponent(self, baseGlyphName, transformation, **kwargs):
        # only decompose the component if it's included in the set
        if self.include is None or baseGlyphName in self.include:
            # if we're decomposing nested components, temporarily set include to None
            include_bak = self.include
            if self.decomposeNested and self.include:
                self.include = None
            try:
                super().addComponent(baseGlyphName, transformation, **kwargs)
            finally:
                if self.include != include_bak:
                    self.include = include_bak
        else:
            _PassThruComponentsMixin.addComponent(
                self, baseGlyphName, transformation, **kwargs
            )


class DecomposingFilterPen(_DecomposingFilterPenMixin, DecomposingPen, FilterPen):
    """Filter pen that draws components as regular contours."""

    pass


class DecomposingFilterPointPen(
    _DecomposingFilterPenMixin, DecomposingPointPen, FilterPointPen
):
    """Filter point pen that draws components as regular contours."""

    pass

# === NexusCore/openenv\Lib\site-packages\httpcore\_backends\sync.py ===
from __future__ import annotations

import functools
import socket
import ssl
import sys
import typing

from .._exceptions import (
    ConnectError,
    ConnectTimeout,
    ExceptionMapping,
    ReadError,
    ReadTimeout,
    WriteError,
    WriteTimeout,
    map_exceptions,
)
from .._utils import is_socket_readable
from .base import SOCKET_OPTION, NetworkBackend, NetworkStream


class TLSinTLSStream(NetworkStream):  # pragma: no cover
    """
    Because the standard `SSLContext.wrap_socket` method does
    not work for `SSLSocket` objects, we need this class
    to implement TLS stream using an underlying `SSLObject`
    instance in order to support TLS on top of TLS.
    """

    # Defined in RFC 8449
    TLS_RECORD_SIZE = 16384

    def __init__(
        self,
        sock: socket.socket,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ):
        self._sock = sock
        self._incoming = ssl.MemoryBIO()
        self._outgoing = ssl.MemoryBIO()

        self.ssl_obj = ssl_context.wrap_bio(
            incoming=self._incoming,
            outgoing=self._outgoing,
            server_hostname=server_hostname,
        )

        self._sock.settimeout(timeout)
        self._perform_io(self.ssl_obj.do_handshake)

    def _perform_io(
        self,
        func: typing.Callable[..., typing.Any],
    ) -> typing.Any:
        ret = None

        while True:
            errno = None
            try:
                ret = func()
            except (ssl.SSLWantReadError, ssl.SSLWantWriteError) as e:
                errno = e.errno

            self._sock.sendall(self._outgoing.read())

            if errno == ssl.SSL_ERROR_WANT_READ:
                buf = self._sock.recv(self.TLS_RECORD_SIZE)

                if buf:
                    self._incoming.write(buf)
                else:
                    self._incoming.write_eof()
            if errno is None:
                return ret

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        exc_map: ExceptionMapping = {socket.timeout: ReadTimeout, OSError: ReadError}
        with map_exceptions(exc_map):
            self._sock.settimeout(timeout)
            return typing.cast(
                bytes, self._perform_io(functools.partial(self.ssl_obj.read, max_bytes))
            )

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        exc_map: ExceptionMapping = {socket.timeout: WriteTimeout, OSError: WriteError}
        with map_exceptions(exc_map):
            self._sock.settimeout(timeout)
            while buffer:
                nsent = self._perform_io(functools.partial(self.ssl_obj.write, buffer))
                buffer = buffer[nsent:]

    def close(self) -> None:
        self._sock.close()

    def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> NetworkStream:
        raise NotImplementedError()

    def get_extra_info(self, info: str) -> typing.Any:
        if info == "ssl_object":
            return self.ssl_obj
        if info == "client_addr":
            return self._sock.getsockname()
        if info == "server_addr":
            return self._sock.getpeername()
        if info == "socket":
            return self._sock
        if info == "is_readable":
            return is_socket_readable(self._sock)
        return None


class SyncStream(NetworkStream):
    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        exc_map: ExceptionMapping = {socket.timeout: ReadTimeout, OSError: ReadError}
        with map_exceptions(exc_map):
            self._sock.settimeout(timeout)
            return self._sock.recv(max_bytes)

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        if not buffer:
            return

        exc_map: ExceptionMapping = {socket.timeout: WriteTimeout, OSError: WriteError}
        with map_exceptions(exc_map):
            while buffer:
                self._sock.settimeout(timeout)
                n = self._sock.send(buffer)
                buffer = buffer[n:]

    def close(self) -> None:
        self._sock.close()

    def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> NetworkStream:
        exc_map: ExceptionMapping = {
            socket.timeout: ConnectTimeout,
            OSError: ConnectError,
        }
        with map_exceptions(exc_map):
            try:
                if isinstance(self._sock, ssl.SSLSocket):  # pragma: no cover
                    # If the underlying socket has already been upgraded
                    # to the TLS layer (i.e. is an instance of SSLSocket),
                    # we need some additional smarts to support TLS-in-TLS.
                    return TLSinTLSStream(
                        self._sock, ssl_context, server_hostname, timeout
                    )
                else:
                    self._sock.settimeout(timeout)
                    sock = ssl_context.wrap_socket(
                        self._sock, server_hostname=server_hostname
                    )
            except Exception as exc:  # pragma: nocover
                self.close()
                raise exc
        return SyncStream(sock)

    def get_extra_info(self, info: str) -> typing.Any:
        if info == "ssl_object" and isinstance(self._sock, ssl.SSLSocket):
            return self._sock._sslobj  # type: ignore
        if info == "client_addr":
            return self._sock.getsockname()
        if info == "server_addr":
            return self._sock.getpeername()
        if info == "socket":
            return self._sock
        if info == "is_readable":
            return is_socket_readable(self._sock)
        return None


class SyncBackend(NetworkBackend):
    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> NetworkStream:
        # Note that we automatically include `TCP_NODELAY`
        # in addition to any other custom socket options.
        if socket_options is None:
            socket_options = []  # pragma: no cover
        address = (host, port)
        source_address = None if local_address is None else (local_address, 0)
        exc_map: ExceptionMapping = {
            socket.timeout: ConnectTimeout,
            OSError: ConnectError,
        }

        with map_exceptions(exc_map):
            sock = socket.create_connection(
                address,
                timeout,
                source_address=source_address,
            )
            for option in socket_options:
                sock.setsockopt(*option)  # pragma: no cover
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return SyncStream(sock)

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> NetworkStream:  # pragma: nocover
        if sys.platform == "win32":
            raise RuntimeError(
                "Attempted to connect to a UNIX socket on a Windows system."
            )
        if socket_options is None:
            socket_options = []

        exc_map: ExceptionMapping = {
            socket.timeout: ConnectTimeout,
            OSError: ConnectError,
        }
        with map_exceptions(exc_map):
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            for option in socket_options:
                sock.setsockopt(*option)
            sock.settimeout(timeout)
            sock.connect(path)
        return SyncStream(sock)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\ansi.py ===
import re
import sys
from contextlib import suppress
from typing import Iterable, NamedTuple, Optional

from .color import Color
from .style import Style
from .text import Text

re_ansi = re.compile(
    r"""
(?:\x1b[0-?])|
(?:\x1b\](.*?)\x1b\\)|
(?:\x1b([(@-Z\\-_]|\[[0-?]*[ -/]*[@-~]))
""",
    re.VERBOSE,
)


class _AnsiToken(NamedTuple):
    """Result of ansi tokenized string."""

    plain: str = ""
    sgr: Optional[str] = ""
    osc: Optional[str] = ""


def _ansi_tokenize(ansi_text: str) -> Iterable[_AnsiToken]:
    """Tokenize a string in to plain text and ANSI codes.

    Args:
        ansi_text (str): A String containing ANSI codes.

    Yields:
        AnsiToken: A named tuple of (plain, sgr, osc)
    """

    position = 0
    sgr: Optional[str]
    osc: Optional[str]
    for match in re_ansi.finditer(ansi_text):
        start, end = match.span(0)
        osc, sgr = match.groups()
        if start > position:
            yield _AnsiToken(ansi_text[position:start])
        if sgr:
            if sgr == "(":
                position = end + 1
                continue
            if sgr.endswith("m"):
                yield _AnsiToken("", sgr[1:-1], osc)
        else:
            yield _AnsiToken("", sgr, osc)
        position = end
    if position < len(ansi_text):
        yield _AnsiToken(ansi_text[position:])


SGR_STYLE_MAP = {
    1: "bold",
    2: "dim",
    3: "italic",
    4: "underline",
    5: "blink",
    6: "blink2",
    7: "reverse",
    8: "conceal",
    9: "strike",
    21: "underline2",
    22: "not dim not bold",
    23: "not italic",
    24: "not underline",
    25: "not blink",
    26: "not blink2",
    27: "not reverse",
    28: "not conceal",
    29: "not strike",
    30: "color(0)",
    31: "color(1)",
    32: "color(2)",
    33: "color(3)",
    34: "color(4)",
    35: "color(5)",
    36: "color(6)",
    37: "color(7)",
    39: "default",
    40: "on color(0)",
    41: "on color(1)",
    42: "on color(2)",
    43: "on color(3)",
    44: "on color(4)",
    45: "on color(5)",
    46: "on color(6)",
    47: "on color(7)",
    49: "on default",
    51: "frame",
    52: "encircle",
    53: "overline",
    54: "not frame not encircle",
    55: "not overline",
    90: "color(8)",
    91: "color(9)",
    92: "color(10)",
    93: "color(11)",
    94: "color(12)",
    95: "color(13)",
    96: "color(14)",
    97: "color(15)",
    100: "on color(8)",
    101: "on color(9)",
    102: "on color(10)",
    103: "on color(11)",
    104: "on color(12)",
    105: "on color(13)",
    106: "on color(14)",
    107: "on color(15)",
}


class AnsiDecoder:
    """Translate ANSI code in to styled Text."""

    def __init__(self) -> None:
        self.style = Style.null()

    def decode(self, terminal_text: str) -> Iterable[Text]:
        """Decode ANSI codes in an iterable of lines.

        Args:
            lines (Iterable[str]): An iterable of lines of terminal output.

        Yields:
            Text: Marked up Text.
        """
        for line in terminal_text.splitlines():
            yield self.decode_line(line)

    def decode_line(self, line: str) -> Text:
        """Decode a line containing ansi codes.

        Args:
            line (str): A line of terminal output.

        Returns:
            Text: A Text instance marked up according to ansi codes.
        """
        from_ansi = Color.from_ansi
        from_rgb = Color.from_rgb
        _Style = Style
        text = Text()
        append = text.append
        line = line.rsplit("\r", 1)[-1]
        for plain_text, sgr, osc in _ansi_tokenize(line):
            if plain_text:
                append(plain_text, self.style or None)
            elif osc is not None:
                if osc.startswith("8;"):
                    _params, semicolon, link = osc[2:].partition(";")
                    if semicolon:
                        self.style = self.style.update_link(link or None)
            elif sgr is not None:
                # Translate in to semi-colon separated codes
                # Ignore invalid codes, because we want to be lenient
                codes = [
                    min(255, int(_code) if _code else 0)
                    for _code in sgr.split(";")
                    if _code.isdigit() or _code == ""
                ]
                iter_codes = iter(codes)
                for code in iter_codes:
                    if code == 0:
                        # reset
                        self.style = _Style.null()
                    elif code in SGR_STYLE_MAP:
                        # styles
                        self.style += _Style.parse(SGR_STYLE_MAP[code])
                    elif code == 38:
                        #  Foreground
                        with suppress(StopIteration):
                            color_type = next(iter_codes)
                            if color_type == 5:
                                self.style += _Style.from_color(
                                    from_ansi(next(iter_codes))
                                )
                            elif color_type == 2:
                                self.style += _Style.from_color(
                                    from_rgb(
                                        next(iter_codes),
                                        next(iter_codes),
                                        next(iter_codes),
                                    )
                                )
                    elif code == 48:
                        # Background
                        with suppress(StopIteration):
                            color_type = next(iter_codes)
                            if color_type == 5:
                                self.style += _Style.from_color(
                                    None, from_ansi(next(iter_codes))
                                )
                            elif color_type == 2:
                                self.style += _Style.from_color(
                                    None,
                                    from_rgb(
                                        next(iter_codes),
                                        next(iter_codes),
                                        next(iter_codes),
                                    ),
                                )

        return text


if sys.platform != "win32" and __name__ == "__main__":  # pragma: no cover
    import io
    import os
    import pty
    import sys

    decoder = AnsiDecoder()

    stdout = io.BytesIO()

    def read(fd: int) -> bytes:
        data = os.read(fd, 1024)
        stdout.write(data)
        return data

    pty.spawn(sys.argv[1:], read)

    from .console import Console

    console = Console(record=True)

    stdout_result = stdout.getvalue().decode("utf-8")
    print(stdout_result)

    for line in decoder.decode(stdout_result):
        console.print(line)

    console.save_html("stdout.html")

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\lean.py ===
"""
    pygments.lexers.lean
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for the Lean theorem prover.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, words, include
from pygments.token import Comment, Operator, Keyword, Name, String, \
    Number, Generic, Whitespace

__all__ = ['Lean3Lexer', 'Lean4Lexer']

class Lean3Lexer(RegexLexer):
    """
    For the Lean 3 theorem prover.
    """
    name = 'Lean'
    url = 'https://leanprover-community.github.io/lean3'
    aliases = ['lean', 'lean3']
    filenames = ['*.lean']
    mimetypes = ['text/x-lean', 'text/x-lean3']
    version_added = '2.0'

    # from https://github.com/leanprover/vscode-lean/blob/1589ca3a65e394b3789409707febbd2d166c9344/syntaxes/lean.json#L186C20-L186C217
    _name_segment = (
        "(?![λΠΣ])[_a-zA-Zα-ωΑ-Ωϊ-ϻἀ-῾℀-⅏𝒜-𝖟]"
        "(?:(?![λΠΣ])[_a-zA-Zα-ωΑ-Ωϊ-ϻἀ-῾℀-⅏𝒜-𝖟0-9'ⁿ-₉ₐ-ₜᵢ-ᵪ])*")
    _name = _name_segment + r"(\." + _name_segment + r")*"

    tokens = {
        'expression': [
            (r'\s+', Whitespace),
            (r'/--', String.Doc, 'docstring'),
            (r'/-', Comment, 'comment'),
            (r'--.*?$', Comment.Single),
            (words((
                    'forall', 'fun', 'Pi', 'from', 'have', 'show', 'assume', 'suffices',
                    'let', 'if', 'else', 'then', 'in', 'with', 'calc', 'match',
                    'do'
                ), prefix=r'\b', suffix=r'\b'), Keyword),
            (words(('sorry', 'admit'), prefix=r'\b', suffix=r'\b'), Generic.Error),
            (words(('Sort', 'Prop', 'Type'), prefix=r'\b', suffix=r'\b'), Keyword.Type),
            (words((
                '(', ')', ':', '{', '}', '[', ']', '⟨', '⟩', '‹', '›', '⦃', '⦄', ':=', ',',
            )), Operator),
            (_name, Name),
            (r'``?' + _name, String.Symbol),
            (r'0x[A-Za-z0-9]+', Number.Integer),
            (r'0b[01]+', Number.Integer),
            (r'\d+', Number.Integer),
            (r'"', String.Double, 'string'),
            (r"'(?:(\\[\\\"'nt])|(\\x[0-9a-fA-F]{2})|(\\u[0-9a-fA-F]{4})|.)'", String.Char),
            (r'[~?][a-z][\w\']*:', Name.Variable),
            (r'\S', Name.Builtin.Pseudo),
        ],
        'root': [
            (words((
                'import', 'renaming', 'hiding',
                'namespace',
                'local',
                'private', 'protected', 'section',
                'include', 'omit', 'section',
                'protected', 'export',
                'open',
                'attribute',
            ), prefix=r'\b', suffix=r'\b'), Keyword.Namespace),
            (words((
                'lemma', 'theorem', 'def', 'definition', 'example',
                'axiom', 'axioms', 'constant', 'constants',
                'universe', 'universes',
                'inductive', 'coinductive', 'structure', 'extends',
                'class', 'instance',
                'abbreviation',

                'noncomputable theory',

                'noncomputable', 'mutual', 'meta',

                'attribute',

                'parameter', 'parameters',
                'variable', 'variables',

                'reserve', 'precedence',
                'postfix', 'prefix', 'notation', 'infix', 'infixl', 'infixr',

                'begin', 'by', 'end',

                'set_option',
                'run_cmd',
            ), prefix=r'\b', suffix=r'\b'), Keyword.Declaration),
            (r'@\[', Keyword.Declaration, 'attribute'),
            (words((
                '#eval', '#check', '#reduce', '#exit',
                '#print', '#help',
            ), suffix=r'\b'), Keyword),
            include('expression')
        ],
        'attribute': [
            (r'\]', Keyword.Declaration, '#pop'),
            include('expression'),
        ],
        'comment': [
            (r'[^/-]+', Comment.Multiline),
            (r'/-', Comment.Multiline, '#push'),
            (r'-/', Comment.Multiline, '#pop'),
            (r'[/-]', Comment.Multiline)
        ],
        'docstring': [
            (r'[^/-]+', String.Doc),
            (r'-/', String.Doc, '#pop'),
            (r'[/-]', String.Doc)
        ],
        'string': [
            (r'[^\\"]+', String.Double),
            (r"(?:(\\[\\\"'nt])|(\\x[0-9a-fA-F]{2})|(\\u[0-9a-fA-F]{4}))", String.Escape),
            ('"', String.Double, '#pop'),
        ],
    }

    def analyse_text(text):
        if re.search(r'^import [a-z]', text, re.MULTILINE):
            return 0.1


LeanLexer = Lean3Lexer


class Lean4Lexer(RegexLexer):
    """
    For the Lean 4 theorem prover.
    """
    
    name = 'Lean4'
    url = 'https://github.com/leanprover/lean4'
    aliases = ['lean4']
    filenames = ['*.lean']
    mimetypes = ['text/x-lean4']
    version_added = '2.18'

    # same as Lean3Lexer, with `!` and `?` allowed
    _name_segment = (
        "(?![λΠΣ])[_a-zA-Zα-ωΑ-Ωϊ-ϻἀ-῾℀-⅏𝒜-𝖟]"
        "(?:(?![λΠΣ])[_a-zA-Zα-ωΑ-Ωϊ-ϻἀ-῾℀-⅏𝒜-𝖟0-9'ⁿ-₉ₐ-ₜᵢ-ᵪ!?])*")
    _name = _name_segment + r"(\." + _name_segment + r")*"

    keywords1 = (
        'import', 'unif_hint',
        'renaming', 'inline', 'hiding', 'lemma', 'variable',
        'theorem', 'axiom', 'inductive', 'structure', 'universe', 'alias',
        '#help',  'precedence', 'postfix', 'prefix',
        'infix', 'infixl', 'infixr', 'notation', '#eval',
        '#check', '#reduce', '#exit', 'end', 'private', 'using', 'namespace',
        'instance', 'section', 'protected',
        'export', 'set_option', 'extends', 'open', 'example',
        '#print', 'opaque',
        'def', 'macro', 'elab', 'syntax', 'macro_rules', '#reduce', 'where',
        'abbrev', 'noncomputable', 'class', 'attribute', '#synth', 'mutual',
        'scoped', 'local',
    )

    keywords2 = (
        'forall', 'fun', 'obtain', 'from', 'have', 'show', 'assume',
        'let', 'if', 'else', 'then', 'by', 'in', 'with',
        'calc', 'match', 'nomatch', 'do', 'at',
    )

    keywords3 = (
        # Sorts
        'Type', 'Prop', 'Sort',
    )

    operators = (
        '!=', '#', '&', '&&', '*', '+', '-', '/', '@', '!',
        '-.', '->', '.', '..', '...', '::', ':>', ';', ';;', '<',
        '<-', '=', '==', '>', '_', '|', '||', '~', '=>', '<=', '>=',
        '/\\', '\\/', '∀', 'Π', 'λ', '↔', '∧', '∨', '≠', '≤', '≥',
        '¬', '⁻¹', '⬝', '▸', '→', '∃', '≈', '×', '⌞',
        '⌟', '≡', '⟨', '⟩', "↦",
    )

    punctuation = ('(', ')', ':', '{', '}', '[', ']', '⦃', '⦄',
                   ':=', ',')

    tokens = {
        'expression': [
            (r'\s+', Whitespace),
            (r'/--', String.Doc, 'docstring'),
            (r'/-', Comment, 'comment'),
            (r'--.*$', Comment.Single),
            (words(keywords3, prefix=r'\b', suffix=r'\b'), Keyword.Type),
            (words(('sorry', 'admit'), prefix=r'\b', suffix=r'\b'), Generic.Error),
            (words(operators), Name.Builtin.Pseudo),
            (words(punctuation), Operator),
            (_name_segment, Name),
            (r'``?' + _name, String.Symbol),
            (r'(?<=\.)\d+', Number),
            (r'(\d+\.\d*)([eE][+-]?[0-9]+)?', Number.Float),
            (r'\d+', Number.Integer),
            (r'"', String.Double, 'string'),
            (r'[~?][a-z][\w\']*:', Name.Variable),
            (r'\S', Name.Builtin.Pseudo),
        ],
        'root': [
            (words(keywords1, prefix=r'\b', suffix=r'\b'), Keyword.Namespace),
            (words(keywords2, prefix=r'\b', suffix=r'\b'), Keyword),
            (r'@\[', Keyword.Declaration, 'attribute'),
            include('expression')
        ],
        'attribute': [
            (r'\]', Keyword.Declaration, '#pop'),
            include('expression'),
        ],
        'comment': [
            # Multiline Comments
            (r'[^/-]+', Comment.Multiline),
            (r'/-', Comment.Multiline, '#push'),
            (r'-/', Comment.Multiline, '#pop'),
            (r'[/-]', Comment.Multiline)
        ],
        'docstring': [
            (r'[^/-]+', String.Doc),
            (r'-/', String.Doc, '#pop'),
            (r'[/-]', String.Doc)
        ],
        'string': [
            (r'[^\\"]+', String.Double),
            (r'\\[n"\\\n]', String.Escape),
            ('"', String.Double, '#pop'),
        ],
    }

    def analyse_text(text):
        if re.search(r'^import [A-Z]', text, re.MULTILINE):
            return 0.1

# === NexusCore/openenv\Lib\site-packages\trio\_core\_asyncgens.py ===
from __future__ import annotations

import logging
import sys
import warnings
import weakref
from typing import TYPE_CHECKING, NoReturn, TypeVar

import attrs

from .. import _core
from .._util import name_asyncgen
from . import _run

# Used to log exceptions in async generator finalizers
ASYNCGEN_LOGGER = logging.getLogger("trio.async_generator_errors")

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import AsyncGeneratorType

    from typing_extensions import ParamSpec

    _P = ParamSpec("_P")

    _WEAK_ASYNC_GEN_SET = weakref.WeakSet[AsyncGeneratorType[object, NoReturn]]
    _ASYNC_GEN_SET = set[AsyncGeneratorType[object, NoReturn]]
else:
    _WEAK_ASYNC_GEN_SET = weakref.WeakSet
    _ASYNC_GEN_SET = set

_R = TypeVar("_R")


@_core.disable_ki_protection
def _call_without_ki_protection(
    f: Callable[_P, _R],
    /,
    *args: _P.args,
    **kwargs: _P.kwargs,
) -> _R:
    return f(*args, **kwargs)


@attrs.define(eq=False)
class AsyncGenerators:
    # Async generators are added to this set when first iterated. Any
    # left after the main task exits will be closed before trio.run()
    # returns.  During most of the run, this is a WeakSet so GC works.
    # During shutdown, when we're finalizing all the remaining
    # asyncgens after the system nursery has been closed, it's a
    # regular set so we don't have to deal with GC firing at
    # unexpected times.
    alive: _WEAK_ASYNC_GEN_SET | _ASYNC_GEN_SET = attrs.Factory(_WEAK_ASYNC_GEN_SET)
    # The ids of foreign async generators are added to this set when first
    # iterated. Usually it is not safe to refer to ids like this, but because
    # we're using a finalizer we can ensure ids in this set do not outlive
    # their async generator.
    foreign: set[int] = attrs.Factory(set)

    # This collects async generators that get garbage collected during
    # the one-tick window between the system nursery closing and the
    # init task starting end-of-run asyncgen finalization.
    trailing_needs_finalize: _ASYNC_GEN_SET = attrs.Factory(_ASYNC_GEN_SET)

    prev_hooks: sys._asyncgen_hooks = attrs.field(init=False)

    def install_hooks(self, runner: _run.Runner) -> None:
        def firstiter(agen: AsyncGeneratorType[object, NoReturn]) -> None:
            if hasattr(_run.GLOBAL_RUN_CONTEXT, "task"):
                self.alive.add(agen)
            else:
                # An async generator first iterated outside of a Trio
                # task doesn't belong to Trio. Probably we're in guest
                # mode and the async generator belongs to our host.
                # A strong set of ids is one of the only good places to
                # remember this fact, at least until
                # https://github.com/python/cpython/issues/85093 is implemented.
                self.foreign.add(id(agen))
                if self.prev_hooks.firstiter is not None:
                    self.prev_hooks.firstiter(agen)

        def finalize_in_trio_context(
            agen: AsyncGeneratorType[object, NoReturn],
            agen_name: str,
        ) -> None:
            try:
                runner.spawn_system_task(
                    self._finalize_one,
                    agen,
                    agen_name,
                    name=f"close asyncgen {agen_name} (abandoned)",
                )
            except RuntimeError:
                # There is a one-tick window where the system nursery
                # is closed but the init task hasn't yet made
                # self.asyncgens a strong set to disable GC. We seem to
                # have hit it.
                self.trailing_needs_finalize.add(agen)

        @_core.enable_ki_protection
        def finalizer(agen: AsyncGeneratorType[object, NoReturn]) -> None:
            try:
                self.foreign.remove(id(agen))
            except KeyError:
                is_ours = True
            else:
                is_ours = False

            agen_name = name_asyncgen(agen)
            if is_ours:
                runner.entry_queue.run_sync_soon(
                    finalize_in_trio_context,
                    agen,
                    agen_name,
                )

                # Do this last, because it might raise an exception
                # depending on the user's warnings filter. (That
                # exception will be printed to the terminal and
                # ignored, since we're running in GC context.)
                warnings.warn(
                    f"Async generator {agen_name!r} was garbage collected before it "
                    "had been exhausted. Surround its use in 'async with "
                    "aclosing(...):' to ensure that it gets cleaned up as soon as "
                    "you're done using it.",
                    ResourceWarning,
                    stacklevel=2,
                    source=agen,
                )
            else:
                # Not ours -> forward to the host loop's async generator finalizer
                finalizer = self.prev_hooks.finalizer
                if finalizer is not None:
                    _call_without_ki_protection(finalizer, agen)
                else:
                    # Host has no finalizer.  Reimplement the default
                    # Python behavior with no hooks installed: throw in
                    # GeneratorExit, step once, raise RuntimeError if
                    # it doesn't exit.
                    closer = agen.aclose()
                    try:
                        # If the next thing is a yield, this will raise RuntimeError
                        # which we allow to propagate
                        _call_without_ki_protection(closer.send, None)
                    except StopIteration:
                        pass
                    else:
                        # If the next thing is an await, we get here. Give a nicer
                        # error than the default "async generator ignored GeneratorExit"
                        raise RuntimeError(
                            f"Non-Trio async generator {agen_name!r} awaited something "
                            "during finalization; install a finalization hook to "
                            "support this, or wrap it in 'async with aclosing(...):'",
                        )

        self.prev_hooks = sys.get_asyncgen_hooks()
        sys.set_asyncgen_hooks(firstiter=firstiter, finalizer=finalizer)  # type: ignore[arg-type]  # Finalizer doesn't use AsyncGeneratorType

    async def finalize_remaining(self, runner: _run.Runner) -> None:
        # This is called from init after shutting down the system nursery.
        # The only tasks running at this point are init and
        # the run_sync_soon task, and since the system nursery is closed,
        # there's no way for user code to spawn more.
        assert _core.current_task() is runner.init_task
        assert len(runner.tasks) == 2

        # To make async generator finalization easier to reason
        # about, we'll shut down asyncgen garbage collection by turning
        # the alive WeakSet into a regular set.
        self.alive = set(self.alive)

        # Process all pending run_sync_soon callbacks, in case one of
        # them was an asyncgen finalizer that snuck in under the wire.
        runner.entry_queue.run_sync_soon(runner.reschedule, runner.init_task)
        await _core.wait_task_rescheduled(
            lambda _: _core.Abort.FAILED,  # pragma: no cover
        )
        self.alive.update(self.trailing_needs_finalize)
        self.trailing_needs_finalize.clear()

        # None of the still-living tasks use async generators, so
        # every async generator must be suspended at a yield point --
        # there's no one to be doing the iteration. That's good,
        # because aclose() only works on an asyncgen that's suspended
        # at a yield point.  (If it's suspended at an event loop trap,
        # because someone is in the middle of iterating it, then you
        # get a RuntimeError on 3.8+, and a nasty surprise on earlier
        # versions due to https://bugs.python.org/issue32526.)
        #
        # However, once we start aclose() of one async generator, it
        # might start fetching the next value from another, thus
        # preventing us from closing that other (at least until
        # aclose() of the first one is complete).  This constraint
        # effectively requires us to finalize the remaining asyncgens
        # in arbitrary order, rather than doing all of them at the
        # same time. On 3.8+ we could defer any generator with
        # ag_running=True to a later batch, but that only catches
        # the case where our aclose() starts after the user's
        # asend()/etc. If our aclose() starts first, then the
        # user's asend()/etc will raise RuntimeError, since they're
        # probably not checking ag_running.
        #
        # It might be possible to allow some parallelized cleanup if
        # we can determine that a certain set of asyncgens have no
        # interdependencies, using gc.get_referents() and such.
        # But just doing one at a time will typically work well enough
        # (since each aclose() executes in a cancelled scope) and
        # is much easier to reason about.

        # It's possible that that cleanup code will itself create
        # more async generators, so we iterate repeatedly until
        # all are gone.
        while self.alive:
            batch = self.alive
            self.alive = _ASYNC_GEN_SET()
            for agen in batch:
                await self._finalize_one(agen, name_asyncgen(agen))

    def close(self) -> None:
        sys.set_asyncgen_hooks(*self.prev_hooks)

    async def _finalize_one(
        self,
        agen: AsyncGeneratorType[object, NoReturn],
        name: object,
    ) -> None:
        try:
            # This shield ensures that finalize_asyncgen never exits
            # with an exception, not even a Cancelled. The inside
            # is cancelled so there's no deadlock risk.
            with _core.CancelScope(shield=True) as cancel_scope:
                cancel_scope.cancel()
                await agen.aclose()
        except BaseException:
            ASYNCGEN_LOGGER.exception(
                "Exception ignored during finalization of async generator %r -- "
                "surround your use of the generator in 'async with aclosing(...):' "
                "to raise exceptions like this in the context where they're generated",
                name,
            )

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_repl.py ===
from __future__ import annotations

import subprocess
import sys
from typing import Protocol

import pytest

import trio._repl


class RawInput(Protocol):
    def __call__(self, prompt: str = "") -> str: ...


def build_raw_input(cmds: list[str]) -> RawInput:
    """
    Pass in a list of strings.
    Returns a callable that returns each string, each time its called
    When there are not more strings to return, raise EOFError
    """
    cmds_iter = iter(cmds)
    prompts = []

    def _raw_helper(prompt: str = "") -> str:
        prompts.append(prompt)
        try:
            return next(cmds_iter)
        except StopIteration:
            raise EOFError from None

    return _raw_helper


def test_build_raw_input() -> None:
    """Quick test of our helper function."""
    raw_input = build_raw_input(["cmd1"])
    assert raw_input() == "cmd1"
    with pytest.raises(EOFError):
        raw_input()


# In 3.10 or later, types.FunctionType (used internally) will automatically
# attach __builtins__ to the function objects. However we need to explicitly
# include it for 3.9 support
def build_locals() -> dict[str, object]:
    return {"__builtins__": __builtins__}


async def test_basic_interaction(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Run some basic commands through the interpreter while capturing stdout.
    Ensure that the interpreted prints the expected results.
    """
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            # evaluate simple expression and recall the value
            "x = 1",
            "print(f'{x=}')",
            # Literal gets printed
            "'hello'",
            # define and call sync function
            "def func():",
            "  print(x + 1)",
            "",
            "func()",
            # define and call async function
            "async def afunc():",
            "  return 4",
            "",
            "await afunc()",
            # import works
            "import sys",
            "sys.stdout.write('hello stdout\\n')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, _err = capsys.readouterr()
    assert out.splitlines() == ["x=1", "'hello'", "2", "4", "hello stdout", "13"]


async def test_system_exits_quit_interpreter(monkeypatch: pytest.MonkeyPatch) -> None:
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            "raise SystemExit",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    with pytest.raises(SystemExit):
        await trio._repl.run_repl(console)


async def test_KI_interrupts(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            "import signal, trio, trio.lowlevel",
            "async def f():",
            "  trio.lowlevel.spawn_system_task("
            "    trio.to_thread.run_sync,"
            "    signal.raise_signal, signal.SIGINT,"
            "  )",  # just awaiting this kills the test runner?!
            "  await trio.sleep_forever()",
            "  print('should not see this')",
            "",
            "await f()",
            "print('AFTER KeyboardInterrupt')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, err = capsys.readouterr()
    assert "KeyboardInterrupt" in err
    assert "should" not in out
    assert "AFTER KeyboardInterrupt" in out


async def test_system_exits_in_exc_group(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            "import sys",
            "if sys.version_info < (3, 11):",
            "  from exceptiongroup import BaseExceptionGroup",
            "",
            "raise BaseExceptionGroup('', [RuntimeError(), SystemExit()])",
            "print('AFTER BaseExceptionGroup')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, _err = capsys.readouterr()
    # assert that raise SystemExit in an exception group
    # doesn't quit
    assert "AFTER BaseExceptionGroup" in out


async def test_system_exits_in_nested_exc_group(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            "import sys",
            "if sys.version_info < (3, 11):",
            "  from exceptiongroup import BaseExceptionGroup",
            "",
            "raise BaseExceptionGroup(",
            "  '', [BaseExceptionGroup('', [RuntimeError(), SystemExit()])])",
            "print('AFTER BaseExceptionGroup')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, _err = capsys.readouterr()
    # assert that raise SystemExit in an exception group
    # doesn't quit
    assert "AFTER BaseExceptionGroup" in out


async def test_base_exception_captured(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            # The statement after raise should still get executed
            "raise BaseException",
            "print('AFTER BaseException')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, err = capsys.readouterr()
    assert "_threads.py" not in err
    assert "_repl.py" not in err
    assert "AFTER BaseException" in out


async def test_exc_group_captured(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            # The statement after raise should still get executed
            "raise ExceptionGroup('', [KeyError()])",
            "print('AFTER ExceptionGroup')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, _err = capsys.readouterr()
    assert "AFTER ExceptionGroup" in out


async def test_base_exception_capture_from_coroutine(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            "async def async_func_raises_base_exception():",
            "  raise BaseException",
            "",
            # This will raise, but the statement after should still
            # be executed
            "await async_func_raises_base_exception()",
            "print('AFTER BaseException')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, err = capsys.readouterr()
    assert "_threads.py" not in err
    assert "_repl.py" not in err
    assert "AFTER BaseException" in out


def test_main_entrypoint() -> None:
    """
    Basic smoke test when running via the package __main__ entrypoint.
    """
    repl = subprocess.run([sys.executable, "-m", "trio"], input=b"exit()")
    assert repl.returncode == 0

# === NexusCore/evaluation\evalplus\evalplus\perf\select_pe_tasks.py ===
"""Analyze the variance of PE and their time cost.
Filter those with high variance and low time cost.
"""

import json
import math
from datetime import datetime
from typing import List

import numpy as np
from rich.console import Console
from rich.syntax import Syntax
from termcolor import colored

from evalplus.perf.config import MIN_REQUIRED_NUM_INSTRUCTION


def cv(time_costs: List[float]) -> float:
    """
    We use Coefficient of Variation (CV) to as the variance of PE.
    CV = 100 * standard deviation / mean
    """
    if len(time_costs) == 0:
        raise ValueError("time_costs is empty.")
    return 100 * np.std(time_costs) / np.mean(time_costs)


def filter_by_profile_size(task2profile: dict, threshold: int = 10):
    to_remove = []
    for task_id, profile in task2profile.items():
        if (
            profile is None
            or len(profile) < threshold
            or any(None in p for p in profile)
        ):
            print(colored(f"⚠️ {task_id} skipped: #profile < {threshold}", "red"))
            to_remove.append(task_id)
    for task_id in to_remove:
        del task2profile[task_id]
    return task2profile


def filter_by_compute_cost(
    task2profile: dict, thresh: float = MIN_REQUIRED_NUM_INSTRUCTION
):
    """Filter out tasks that can be solved using less than threshold #instruction."""
    to_remove = []
    for task_id, profile in task2profile.items():
        if (
            min(np.mean(p) for p in profile) < thresh
        ):  # filter if some solution is too fast
            print(
                colored(
                    f"⚠️ {task_id} skipped: some solution is faster than {thresh} #instruction",
                    "red",
                )
            )
            to_remove.append(task_id)
    for task_id in to_remove:
        del task2profile[task_id]
    return task2profile


def filter_by_cv(task2profile: dict, thresh: float, percentile: int = 95):
    to_remove = []
    for task_id, profile in task2profile.items():
        mean_var = np.percentile([cv(p) for p in profile], percentile)
        if mean_var > thresh:
            print(
                colored(
                    f"⚠️ {task_id} skipped: P{percentile} CV = {mean_var:.1f}% > {thresh}%",
                    "red",
                )
            )
            to_remove.append(task_id)
    for task_id in to_remove:
        del task2profile[task_id]
    return task2profile


# smaller time, larger threshold
def thresh_fn(base_thresh, x, weight=0.002):
    return base_thresh + math.sqrt(weight / x)


def adaptive_seg1d(arr1d, base_thresh=0.10):
    # sort from large to small
    arr1d = np.sort(arr1d)[::-1]
    # relative distance
    relative_distance = -np.diff(arr1d) / arr1d[:-1]

    splitter_idx = []
    for i, rel in enumerate(relative_distance):
        if rel > thresh_fn(base_thresh, arr1d[i], weight=MIN_REQUIRED_NUM_INSTRUCTION):
            splitter_idx.append(i + 1)

    # [9, 8, 7, |-> 3, 2 1]
    # splitter_idx points to the slowest in each cluster
    return np.split(arr1d, splitter_idx)


def filter_by_clustering(task2profile: dict, base_threshold=0.2, min_clusters=3):
    to_remove = []
    for task_id, profile in task2profile.items():
        if len(adaptive_seg1d(np.mean(profile, axis=1), base_threshold)) < min_clusters:
            print(
                colored(
                    f"⚠️ {task_id} skipped: #Cluster = 0 with {base_threshold=}%",
                    "red",
                )
            )
            to_remove.append(task_id)
    for task_id in to_remove:
        del task2profile[task_id]
    return task2profile


def brief_list_repr(lst, head_count=4, tail_count=4):
    if len(lst) <= head_count + tail_count:
        return f"{lst}"
    else:
        head = ", ".join(str(x) for x in lst[:head_count])
        tail = ", ".join(str(x) for x in lst[-tail_count:])
        return f"[{head}, ..., {tail}]"


def script(
    profiled_solutions: str,
    output_dataset: str = f"evalperf-{datetime.now():%Y%m%d}.jsonl",
    debug_tasks: List[str] = [],
    min_clusters=4,
):
    assert profiled_solutions.endswith(".jsonl")
    assert output_dataset.endswith(".jsonl")

    # read jsonl
    with open(profiled_solutions, "r") as f:
        profiled_solutions = [json.loads(l) for l in f if l.strip()]

    console = Console()

    task2profile = {d["task_id"]: d["counter_profile"] for d in profiled_solutions}
    print(f"Loaded {len(task2profile)} tasks.")

    # * Criteria 1: Profile cannot be empty
    task2profile = filter_by_profile_size(task2profile)
    print(f"{len(task2profile)} tasks with profile.")

    # * Criteria 2: Solutions should run more than MIN_SLOWEST_INSTRUCTION_COUNT
    task2profile = filter_by_compute_cost(task2profile)
    print(
        f"{len(task2profile)} tasks with slowest mean time > {MIN_REQUIRED_NUM_INSTRUCTION}s."
    )

    # * Criteria 3: P99-CV should be less than 5%
    final_thresh = 5
    percentile = 99
    task2profile = filter_by_cv(
        task2profile, thresh=final_thresh, percentile=percentile
    )
    print(f"{len(task2profile)} tasks with CV <= {final_thresh}%.")

    # * Criteria 4: Cluster should be more than 1
    task2profile = filter_by_clustering(
        task2profile, base_threshold=0.2, min_clusters=min_clusters
    )
    print(f"{len(task2profile)} tasks with #Cluster >= {min_clusters}.")

    # export dataset
    task2solution = {d["task_id"]: d for d in profiled_solutions}
    # each item is {"task_id": "xxx", "solutions": [...], "percentile": [...]}
    export_dataset = []
    total_clusters = 0
    for task_id, profile in task2profile.items():
        print(colored(f"-========== {task_id} ==========-", "green"))
        if task_id in debug_tasks:
            print(colored(f"Debugging {task_id}", "red"))
        mean_runtime = [np.mean(p) for p in profile]
        clusters = adaptive_seg1d(mean_runtime)  # descend
        print(colored(f"#seg = {len(clusters)}", "green"))

        accumulative_ratio = []
        ref_idx = []
        for i, cluster in enumerate(clusters):
            prior_ar = 0 if i == 0 else accumulative_ratio[-1]
            ratio = 100 * len(cluster) / len(mean_runtime)
            acc_ratio = prior_ar + ratio
            brief_list_str = brief_list_repr([round(1000 * v) for v in cluster])
            print(
                f"#{i} |{len(cluster):<3}| ({acc_ratio:<4.1f}) @cv {cv(cluster):.1f}: {brief_list_str}"
            )
            accumulative_ratio.append(acc_ratio)
            ref_idx.append(np.where(mean_runtime == cluster[0])[0][0])

            if task_id in debug_tasks:
                # print solutions
                solution_text = task2solution[task_id]["solutions"][ref_idx[-1]]
                # remove empty lines
                solution_text = "\n".join(
                    line for line in solution_text.split("\n") if line.strip()
                )
                console.print(Syntax(solution_text, "python"))
                print(colored("-" * 32, "green"))

        total_clusters += len(clusters)

        # add reference solution and check consistency
        for i in range(len(ref_idx)):
            if i == 0:
                continue
            # prior runtime must be larger than current
            assert mean_runtime[ref_idx[i - 1]] > mean_runtime[ref_idx[i]]

        reference = [task2solution[task_id]["solutions"][idx] for idx in ref_idx]

        assert len(reference) == len(clusters)
        assert len(accumulative_ratio) == len(reference)
        item = {
            "task_id": task_id,
            "reference": reference,
            "pe_input": task2solution[task_id]["pe_input"],
            "scores": accumulative_ratio,
        }
        export_dataset.append(item)

    print(f"Total clusters: {total_clusters}")

    with open(output_dataset, "w") as f:
        for item in export_dataset:
            f.write(json.dumps(item) + "\n")


def main():
    from fire import Fire

    Fire(script)


if __name__ == "__main__":
    main()

# === NexusCore/myenv\Lib\site-packages\pip\_internal\cli\base_command.py ===
"""Base Command class, and related routines"""

import logging
import logging.config
import optparse
import os
import sys
import traceback
from optparse import Values
from typing import List, Optional, Tuple

from pip._vendor.rich import reconfigure
from pip._vendor.rich import traceback as rich_traceback

from pip._internal.cli import cmdoptions
from pip._internal.cli.command_context import CommandContextMixIn
from pip._internal.cli.parser import ConfigOptionParser, UpdatingDefaultsHelpFormatter
from pip._internal.cli.status_codes import (
    ERROR,
    PREVIOUS_BUILD_DIR_ERROR,
    UNKNOWN_ERROR,
    VIRTUALENV_NOT_FOUND,
)
from pip._internal.exceptions import (
    BadCommand,
    CommandError,
    DiagnosticPipError,
    InstallationError,
    NetworkConnectionError,
    PreviousBuildDirError,
)
from pip._internal.utils.deprecation import deprecated
from pip._internal.utils.filesystem import check_path_owner
from pip._internal.utils.logging import BrokenStdoutLoggingError, setup_logging
from pip._internal.utils.misc import get_prog, normalize_path
from pip._internal.utils.temp_dir import TempDirectoryTypeRegistry as TempDirRegistry
from pip._internal.utils.temp_dir import global_tempdir_manager, tempdir_registry
from pip._internal.utils.virtualenv import running_under_virtualenv

__all__ = ["Command"]

logger = logging.getLogger(__name__)


class Command(CommandContextMixIn):
    usage: str = ""
    ignore_require_venv: bool = False

    def __init__(self, name: str, summary: str, isolated: bool = False) -> None:
        super().__init__()

        self.name = name
        self.summary = summary
        self.parser = ConfigOptionParser(
            usage=self.usage,
            prog=f"{get_prog()} {name}",
            formatter=UpdatingDefaultsHelpFormatter(),
            add_help_option=False,
            name=name,
            description=self.__doc__,
            isolated=isolated,
        )

        self.tempdir_registry: Optional[TempDirRegistry] = None

        # Commands should add options to this option group
        optgroup_name = f"{self.name.capitalize()} Options"
        self.cmd_opts = optparse.OptionGroup(self.parser, optgroup_name)

        # Add the general options
        gen_opts = cmdoptions.make_option_group(
            cmdoptions.general_group,
            self.parser,
        )
        self.parser.add_option_group(gen_opts)

        self.add_options()

    def add_options(self) -> None:
        pass

    def handle_pip_version_check(self, options: Values) -> None:
        """
        This is a no-op so that commands by default do not do the pip version
        check.
        """
        # Make sure we do the pip version check if the index_group options
        # are present.
        assert not hasattr(options, "no_index")

    def run(self, options: Values, args: List[str]) -> int:
        raise NotImplementedError

    def _run_wrapper(self, level_number: int, options: Values, args: List[str]) -> int:
        def _inner_run() -> int:
            try:
                return self.run(options, args)
            finally:
                self.handle_pip_version_check(options)

        if options.debug_mode:
            rich_traceback.install(show_locals=True)
            return _inner_run()

        try:
            status = _inner_run()
            assert isinstance(status, int)
            return status
        except DiagnosticPipError as exc:
            logger.error("%s", exc, extra={"rich": True})
            logger.debug("Exception information:", exc_info=True)

            return ERROR
        except PreviousBuildDirError as exc:
            logger.critical(str(exc))
            logger.debug("Exception information:", exc_info=True)

            return PREVIOUS_BUILD_DIR_ERROR
        except (
            InstallationError,
            BadCommand,
            NetworkConnectionError,
        ) as exc:
            logger.critical(str(exc))
            logger.debug("Exception information:", exc_info=True)

            return ERROR
        except CommandError as exc:
            logger.critical("%s", exc)
            logger.debug("Exception information:", exc_info=True)

            return ERROR
        except BrokenStdoutLoggingError:
            # Bypass our logger and write any remaining messages to
            # stderr because stdout no longer works.
            print("ERROR: Pipe to stdout was broken", file=sys.stderr)
            if level_number <= logging.DEBUG:
                traceback.print_exc(file=sys.stderr)

            return ERROR
        except KeyboardInterrupt:
            logger.critical("Operation cancelled by user")
            logger.debug("Exception information:", exc_info=True)

            return ERROR
        except BaseException:
            logger.critical("Exception:", exc_info=True)

            return UNKNOWN_ERROR

    def parse_args(self, args: List[str]) -> Tuple[Values, List[str]]:
        # factored out for testability
        return self.parser.parse_args(args)

    def main(self, args: List[str]) -> int:
        try:
            with self.main_context():
                return self._main(args)
        finally:
            logging.shutdown()

    def _main(self, args: List[str]) -> int:
        # We must initialize this before the tempdir manager, otherwise the
        # configuration would not be accessible by the time we clean up the
        # tempdir manager.
        self.tempdir_registry = self.enter_context(tempdir_registry())
        # Intentionally set as early as possible so globally-managed temporary
        # directories are available to the rest of the code.
        self.enter_context(global_tempdir_manager())

        options, args = self.parse_args(args)

        # Set verbosity so that it can be used elsewhere.
        self.verbosity = options.verbose - options.quiet

        reconfigure(no_color=options.no_color)
        level_number = setup_logging(
            verbosity=self.verbosity,
            no_color=options.no_color,
            user_log_file=options.log,
        )

        always_enabled_features = set(options.features_enabled) & set(
            cmdoptions.ALWAYS_ENABLED_FEATURES
        )
        if always_enabled_features:
            logger.warning(
                "The following features are always enabled: %s. ",
                ", ".join(sorted(always_enabled_features)),
            )

        # Make sure that the --python argument isn't specified after the
        # subcommand. We can tell, because if --python was specified,
        # we should only reach this point if we're running in the created
        # subprocess, which has the _PIP_RUNNING_IN_SUBPROCESS environment
        # variable set.
        if options.python and "_PIP_RUNNING_IN_SUBPROCESS" not in os.environ:
            logger.critical(
                "The --python option must be placed before the pip subcommand name"
            )
            sys.exit(ERROR)

        # TODO: Try to get these passing down from the command?
        #       without resorting to os.environ to hold these.
        #       This also affects isolated builds and it should.

        if options.no_input:
            os.environ["PIP_NO_INPUT"] = "1"

        if options.exists_action:
            os.environ["PIP_EXISTS_ACTION"] = " ".join(options.exists_action)

        if options.require_venv and not self.ignore_require_venv:
            # If a venv is required check if it can really be found
            if not running_under_virtualenv():
                logger.critical("Could not find an activated virtualenv (required).")
                sys.exit(VIRTUALENV_NOT_FOUND)

        if options.cache_dir:
            options.cache_dir = normalize_path(options.cache_dir)
            if not check_path_owner(options.cache_dir):
                logger.warning(
                    "The directory '%s' or its parent directory is not owned "
                    "or is not writable by the current user. The cache "
                    "has been disabled. Check the permissions and owner of "
                    "that directory. If executing pip with sudo, you should "
                    "use sudo's -H flag.",
                    options.cache_dir,
                )
                options.cache_dir = None

        if options.no_python_version_warning:
            deprecated(
                reason="--no-python-version-warning is deprecated.",
                replacement="to remove the flag as it's a no-op",
                gone_in="25.1",
                issue=13154,
            )

        return self._run_wrapper(level_number, options, args)

# === NexusCore/openenv\Lib\site-packages\httpx\_content.py ===
from __future__ import annotations

import inspect
import warnings
from json import dumps as json_dumps
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Iterable,
    Iterator,
    Mapping,
)
from urllib.parse import urlencode

from ._exceptions import StreamClosed, StreamConsumed
from ._multipart import MultipartStream
from ._types import (
    AsyncByteStream,
    RequestContent,
    RequestData,
    RequestFiles,
    ResponseContent,
    SyncByteStream,
)
from ._utils import peek_filelike_length, primitive_value_to_str

__all__ = ["ByteStream"]


class ByteStream(AsyncByteStream, SyncByteStream):
    def __init__(self, stream: bytes) -> None:
        self._stream = stream

    def __iter__(self) -> Iterator[bytes]:
        yield self._stream

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self._stream


class IteratorByteStream(SyncByteStream):
    CHUNK_SIZE = 65_536

    def __init__(self, stream: Iterable[bytes]) -> None:
        self._stream = stream
        self._is_stream_consumed = False
        self._is_generator = inspect.isgenerator(stream)

    def __iter__(self) -> Iterator[bytes]:
        if self._is_stream_consumed and self._is_generator:
            raise StreamConsumed()

        self._is_stream_consumed = True
        if hasattr(self._stream, "read"):
            # File-like interfaces should use 'read' directly.
            chunk = self._stream.read(self.CHUNK_SIZE)
            while chunk:
                yield chunk
                chunk = self._stream.read(self.CHUNK_SIZE)
        else:
            # Otherwise iterate.
            for part in self._stream:
                yield part


class AsyncIteratorByteStream(AsyncByteStream):
    CHUNK_SIZE = 65_536

    def __init__(self, stream: AsyncIterable[bytes]) -> None:
        self._stream = stream
        self._is_stream_consumed = False
        self._is_generator = inspect.isasyncgen(stream)

    async def __aiter__(self) -> AsyncIterator[bytes]:
        if self._is_stream_consumed and self._is_generator:
            raise StreamConsumed()

        self._is_stream_consumed = True
        if hasattr(self._stream, "aread"):
            # File-like interfaces should use 'aread' directly.
            chunk = await self._stream.aread(self.CHUNK_SIZE)
            while chunk:
                yield chunk
                chunk = await self._stream.aread(self.CHUNK_SIZE)
        else:
            # Otherwise iterate.
            async for part in self._stream:
                yield part


class UnattachedStream(AsyncByteStream, SyncByteStream):
    """
    If a request or response is serialized using pickle, then it is no longer
    attached to a stream for I/O purposes. Any stream operations should result
    in `httpx.StreamClosed`.
    """

    def __iter__(self) -> Iterator[bytes]:
        raise StreamClosed()

    async def __aiter__(self) -> AsyncIterator[bytes]:
        raise StreamClosed()
        yield b""  # pragma: no cover


def encode_content(
    content: str | bytes | Iterable[bytes] | AsyncIterable[bytes],
) -> tuple[dict[str, str], SyncByteStream | AsyncByteStream]:
    if isinstance(content, (bytes, str)):
        body = content.encode("utf-8") if isinstance(content, str) else content
        content_length = len(body)
        headers = {"Content-Length": str(content_length)} if body else {}
        return headers, ByteStream(body)

    elif isinstance(content, Iterable) and not isinstance(content, dict):
        # `not isinstance(content, dict)` is a bit oddly specific, but it
        # catches a case that's easy for users to make in error, and would
        # otherwise pass through here, like any other bytes-iterable,
        # because `dict` happens to be iterable. See issue #2491.
        content_length_or_none = peek_filelike_length(content)

        if content_length_or_none is None:
            headers = {"Transfer-Encoding": "chunked"}
        else:
            headers = {"Content-Length": str(content_length_or_none)}
        return headers, IteratorByteStream(content)  # type: ignore

    elif isinstance(content, AsyncIterable):
        headers = {"Transfer-Encoding": "chunked"}
        return headers, AsyncIteratorByteStream(content)

    raise TypeError(f"Unexpected type for 'content', {type(content)!r}")


def encode_urlencoded_data(
    data: RequestData,
) -> tuple[dict[str, str], ByteStream]:
    plain_data = []
    for key, value in data.items():
        if isinstance(value, (list, tuple)):
            plain_data.extend([(key, primitive_value_to_str(item)) for item in value])
        else:
            plain_data.append((key, primitive_value_to_str(value)))
    body = urlencode(plain_data, doseq=True).encode("utf-8")
    content_length = str(len(body))
    content_type = "application/x-www-form-urlencoded"
    headers = {"Content-Length": content_length, "Content-Type": content_type}
    return headers, ByteStream(body)


def encode_multipart_data(
    data: RequestData, files: RequestFiles, boundary: bytes | None
) -> tuple[dict[str, str], MultipartStream]:
    multipart = MultipartStream(data=data, files=files, boundary=boundary)
    headers = multipart.get_headers()
    return headers, multipart


def encode_text(text: str) -> tuple[dict[str, str], ByteStream]:
    body = text.encode("utf-8")
    content_length = str(len(body))
    content_type = "text/plain; charset=utf-8"
    headers = {"Content-Length": content_length, "Content-Type": content_type}
    return headers, ByteStream(body)


def encode_html(html: str) -> tuple[dict[str, str], ByteStream]:
    body = html.encode("utf-8")
    content_length = str(len(body))
    content_type = "text/html; charset=utf-8"
    headers = {"Content-Length": content_length, "Content-Type": content_type}
    return headers, ByteStream(body)


def encode_json(json: Any) -> tuple[dict[str, str], ByteStream]:
    body = json_dumps(
        json, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    content_length = str(len(body))
    content_type = "application/json"
    headers = {"Content-Length": content_length, "Content-Type": content_type}
    return headers, ByteStream(body)


def encode_request(
    content: RequestContent | None = None,
    data: RequestData | None = None,
    files: RequestFiles | None = None,
    json: Any | None = None,
    boundary: bytes | None = None,
) -> tuple[dict[str, str], SyncByteStream | AsyncByteStream]:
    """
    Handles encoding the given `content`, `data`, `files`, and `json`,
    returning a two-tuple of (<headers>, <stream>).
    """
    if data is not None and not isinstance(data, Mapping):
        # We prefer to separate `content=<bytes|str|byte iterator|bytes aiterator>`
        # for raw request content, and `data=<form data>` for url encoded or
        # multipart form content.
        #
        # However for compat with requests, we *do* still support
        # `data=<bytes...>` usages. We deal with that case here, treating it
        # as if `content=<...>` had been supplied instead.
        message = "Use 'content=<...>' to upload raw bytes/text content."
        warnings.warn(message, DeprecationWarning, stacklevel=2)
        return encode_content(data)

    if content is not None:
        return encode_content(content)
    elif files:
        return encode_multipart_data(data or {}, files, boundary)
    elif data:
        return encode_urlencoded_data(data)
    elif json is not None:
        return encode_json(json)

    return {}, ByteStream(b"")


def encode_response(
    content: ResponseContent | None = None,
    text: str | None = None,
    html: str | None = None,
    json: Any | None = None,
) -> tuple[dict[str, str], SyncByteStream | AsyncByteStream]:
    """
    Handles encoding the given `content`, returning a two-tuple of
    (<headers>, <stream>).
    """
    if content is not None:
        return encode_content(content)
    elif text is not None:
        return encode_text(text)
    elif html is not None:
        return encode_html(html)
    elif json is not None:
        return encode_json(json)

    return {}, ByteStream(b"")

# === NexusCore/openenv\Lib\site-packages\typer\_completion_shared.py ===
import os
import re
import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

import click

try:
    import shellingham
except ImportError:  # pragma: no cover
    shellingham = None


class Shells(str, Enum):
    bash = "bash"
    zsh = "zsh"
    fish = "fish"
    powershell = "powershell"
    pwsh = "pwsh"


COMPLETION_SCRIPT_BASH = """
%(complete_func)s() {
    local IFS=$'\n'
    COMPREPLY=( $( env COMP_WORDS="${COMP_WORDS[*]}" \\
                   COMP_CWORD=$COMP_CWORD \\
                   %(autocomplete_var)s=complete_bash $1 ) )
    return 0
}

complete -o default -F %(complete_func)s %(prog_name)s
"""

COMPLETION_SCRIPT_ZSH = """
#compdef %(prog_name)s

%(complete_func)s() {
  eval $(env _TYPER_COMPLETE_ARGS="${words[1,$CURRENT]}" %(autocomplete_var)s=complete_zsh %(prog_name)s)
}

compdef %(complete_func)s %(prog_name)s
"""

COMPLETION_SCRIPT_FISH = 'complete --command %(prog_name)s --no-files --arguments "(env %(autocomplete_var)s=complete_fish _TYPER_COMPLETE_FISH_ACTION=get-args _TYPER_COMPLETE_ARGS=(commandline -cp) %(prog_name)s)" --condition "env %(autocomplete_var)s=complete_fish _TYPER_COMPLETE_FISH_ACTION=is-args _TYPER_COMPLETE_ARGS=(commandline -cp) %(prog_name)s"'

COMPLETION_SCRIPT_POWER_SHELL = """
Import-Module PSReadLine
Set-PSReadLineKeyHandler -Chord Tab -Function MenuComplete
$scriptblock = {
    param($wordToComplete, $commandAst, $cursorPosition)
    $Env:%(autocomplete_var)s = "complete_powershell"
    $Env:_TYPER_COMPLETE_ARGS = $commandAst.ToString()
    $Env:_TYPER_COMPLETE_WORD_TO_COMPLETE = $wordToComplete
    %(prog_name)s | ForEach-Object {
        $commandArray = $_ -Split ":::"
        $command = $commandArray[0]
        $helpString = $commandArray[1]
        [System.Management.Automation.CompletionResult]::new(
            $command, $command, 'ParameterValue', $helpString)
    }
    $Env:%(autocomplete_var)s = ""
    $Env:_TYPER_COMPLETE_ARGS = ""
    $Env:_TYPER_COMPLETE_WORD_TO_COMPLETE = ""
}
Register-ArgumentCompleter -Native -CommandName %(prog_name)s -ScriptBlock $scriptblock
"""

_completion_scripts = {
    "bash": COMPLETION_SCRIPT_BASH,
    "zsh": COMPLETION_SCRIPT_ZSH,
    "fish": COMPLETION_SCRIPT_FISH,
    "powershell": COMPLETION_SCRIPT_POWER_SHELL,
    "pwsh": COMPLETION_SCRIPT_POWER_SHELL,
}

# TODO: Probably refactor this, copied from Click 7.x
_invalid_ident_char_re = re.compile(r"[^a-zA-Z0-9_]")


def get_completion_script(*, prog_name: str, complete_var: str, shell: str) -> str:
    cf_name = _invalid_ident_char_re.sub("", prog_name.replace("-", "_"))
    script = _completion_scripts.get(shell)
    if script is None:
        click.echo(f"Shell {shell} not supported.", err=True)
        raise click.exceptions.Exit(1)
    return (
        script
        % {
            "complete_func": f"_{cf_name}_completion",
            "prog_name": prog_name,
            "autocomplete_var": complete_var,
        }
    ).strip()


def install_bash(*, prog_name: str, complete_var: str, shell: str) -> Path:
    # Ref: https://github.com/scop/bash-completion#faq
    # It seems bash-completion is the official completion system for bash:
    # Ref: https://www.gnu.org/software/bash/manual/html_node/A-Programmable-Completion-Example.html
    # But installing in the locations from the docs doesn't seem to have effect
    completion_path = Path.home() / ".bash_completions" / f"{prog_name}.sh"
    rc_path = Path.home() / ".bashrc"
    rc_path.parent.mkdir(parents=True, exist_ok=True)
    rc_content = ""
    if rc_path.is_file():
        rc_content = rc_path.read_text()
    completion_init_lines = [f"source '{completion_path}'"]
    for line in completion_init_lines:
        if line not in rc_content:  # pragma: no cover
            rc_content += f"\n{line}"
    rc_content += "\n"
    rc_path.write_text(rc_content)
    # Install completion
    completion_path.parent.mkdir(parents=True, exist_ok=True)
    script_content = get_completion_script(
        prog_name=prog_name, complete_var=complete_var, shell=shell
    )
    completion_path.write_text(script_content)
    return completion_path


def install_zsh(*, prog_name: str, complete_var: str, shell: str) -> Path:
    # Setup Zsh and load ~/.zfunc
    zshrc_path = Path.home() / ".zshrc"
    zshrc_path.parent.mkdir(parents=True, exist_ok=True)
    zshrc_content = ""
    if zshrc_path.is_file():
        zshrc_content = zshrc_path.read_text()
    completion_line = "fpath+=~/.zfunc; autoload -Uz compinit; compinit"
    if completion_line not in zshrc_content:
        zshrc_content += f"\n{completion_line}\n"
    style_line = "zstyle ':completion:*' menu select"
    # TODO: consider setting the style only for the current program
    # style_line = f"zstyle ':completion:*:*:{prog_name}:*' menu select"
    # Install zstyle completion config only if the user doesn't have a customization
    if "zstyle" not in zshrc_content:
        zshrc_content += f"\n{style_line}\n"
    zshrc_content = f"{zshrc_content.strip()}\n"
    zshrc_path.write_text(zshrc_content)
    # Install completion under ~/.zfunc/
    path_obj = Path.home() / f".zfunc/_{prog_name}"
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    script_content = get_completion_script(
        prog_name=prog_name, complete_var=complete_var, shell=shell
    )
    path_obj.write_text(script_content)
    return path_obj


def install_fish(*, prog_name: str, complete_var: str, shell: str) -> Path:
    path_obj = Path.home() / f".config/fish/completions/{prog_name}.fish"
    parent_dir: Path = path_obj.parent
    parent_dir.mkdir(parents=True, exist_ok=True)
    script_content = get_completion_script(
        prog_name=prog_name, complete_var=complete_var, shell=shell
    )
    path_obj.write_text(f"{script_content}\n")
    return path_obj


def install_powershell(*, prog_name: str, complete_var: str, shell: str) -> Path:
    subprocess.run(
        [
            shell,
            "-Command",
            "Set-ExecutionPolicy",
            "Unrestricted",
            "-Scope",
            "CurrentUser",
        ]
    )
    result = subprocess.run(
        [shell, "-NoProfile", "-Command", "echo", "$profile"],
        check=True,
        stdout=subprocess.PIPE,
    )
    if result.returncode != 0:  # pragma: no cover
        click.echo("Couldn't get PowerShell user profile", err=True)
        raise click.exceptions.Exit(result.returncode)
    path_str = ""
    if isinstance(result.stdout, str):  # pragma: no cover
        path_str = result.stdout
    if isinstance(result.stdout, bytes):
        try:
            # PowerShell would be predominant in Windows
            path_str = result.stdout.decode("windows-1252")
        except UnicodeDecodeError:  # pragma: no cover
            try:
                path_str = result.stdout.decode("utf8")
            except UnicodeDecodeError:
                click.echo("Couldn't decode the path automatically", err=True)
                raise
    path_obj = Path(path_str.strip())
    parent_dir: Path = path_obj.parent
    parent_dir.mkdir(parents=True, exist_ok=True)
    script_content = get_completion_script(
        prog_name=prog_name, complete_var=complete_var, shell=shell
    )
    with path_obj.open(mode="a") as f:
        f.write(f"{script_content}\n")
    return path_obj


def install(
    shell: Optional[str] = None,
    prog_name: Optional[str] = None,
    complete_var: Optional[str] = None,
) -> Tuple[str, Path]:
    prog_name = prog_name or click.get_current_context().find_root().info_name
    assert prog_name
    if complete_var is None:
        complete_var = "_{}_COMPLETE".format(prog_name.replace("-", "_").upper())
    test_disable_detection = os.getenv("_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION")
    if shell is None and shellingham is not None and not test_disable_detection:
        shell, _ = shellingham.detect_shell()
    if shell == "bash":
        installed_path = install_bash(
            prog_name=prog_name, complete_var=complete_var, shell=shell
        )
        return shell, installed_path
    elif shell == "zsh":
        installed_path = install_zsh(
            prog_name=prog_name, complete_var=complete_var, shell=shell
        )
        return shell, installed_path
    elif shell == "fish":
        installed_path = install_fish(
            prog_name=prog_name, complete_var=complete_var, shell=shell
        )
        return shell, installed_path
    elif shell in {"powershell", "pwsh"}:
        installed_path = install_powershell(
            prog_name=prog_name, complete_var=complete_var, shell=shell
        )
        return shell, installed_path
    else:
        click.echo(f"Shell {shell} is not supported.")
        raise click.exceptions.Exit(1)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\cli\base_command.py ===
"""Base Command class, and related routines"""

import logging
import logging.config
import optparse
import os
import sys
import traceback
from optparse import Values
from typing import List, Optional, Tuple

from pip._vendor.rich import reconfigure
from pip._vendor.rich import traceback as rich_traceback

from pip._internal.cli import cmdoptions
from pip._internal.cli.command_context import CommandContextMixIn
from pip._internal.cli.parser import ConfigOptionParser, UpdatingDefaultsHelpFormatter
from pip._internal.cli.status_codes import (
    ERROR,
    PREVIOUS_BUILD_DIR_ERROR,
    UNKNOWN_ERROR,
    VIRTUALENV_NOT_FOUND,
)
from pip._internal.exceptions import (
    BadCommand,
    CommandError,
    DiagnosticPipError,
    InstallationError,
    NetworkConnectionError,
    PreviousBuildDirError,
)
from pip._internal.utils.deprecation import deprecated
from pip._internal.utils.filesystem import check_path_owner
from pip._internal.utils.logging import BrokenStdoutLoggingError, setup_logging
from pip._internal.utils.misc import get_prog, normalize_path
from pip._internal.utils.temp_dir import TempDirectoryTypeRegistry as TempDirRegistry
from pip._internal.utils.temp_dir import global_tempdir_manager, tempdir_registry
from pip._internal.utils.virtualenv import running_under_virtualenv

__all__ = ["Command"]

logger = logging.getLogger(__name__)


class Command(CommandContextMixIn):
    usage: str = ""
    ignore_require_venv: bool = False

    def __init__(self, name: str, summary: str, isolated: bool = False) -> None:
        super().__init__()

        self.name = name
        self.summary = summary
        self.parser = ConfigOptionParser(
            usage=self.usage,
            prog=f"{get_prog()} {name}",
            formatter=UpdatingDefaultsHelpFormatter(),
            add_help_option=False,
            name=name,
            description=self.__doc__,
            isolated=isolated,
        )

        self.tempdir_registry: Optional[TempDirRegistry] = None

        # Commands should add options to this option group
        optgroup_name = f"{self.name.capitalize()} Options"
        self.cmd_opts = optparse.OptionGroup(self.parser, optgroup_name)

        # Add the general options
        gen_opts = cmdoptions.make_option_group(
            cmdoptions.general_group,
            self.parser,
        )
        self.parser.add_option_group(gen_opts)

        self.add_options()

    def add_options(self) -> None:
        pass

    def handle_pip_version_check(self, options: Values) -> None:
        """
        This is a no-op so that commands by default do not do the pip version
        check.
        """
        # Make sure we do the pip version check if the index_group options
        # are present.
        assert not hasattr(options, "no_index")

    def run(self, options: Values, args: List[str]) -> int:
        raise NotImplementedError

    def _run_wrapper(self, level_number: int, options: Values, args: List[str]) -> int:
        def _inner_run() -> int:
            try:
                return self.run(options, args)
            finally:
                self.handle_pip_version_check(options)

        if options.debug_mode:
            rich_traceback.install(show_locals=True)
            return _inner_run()

        try:
            status = _inner_run()
            assert isinstance(status, int)
            return status
        except DiagnosticPipError as exc:
            logger.error("%s", exc, extra={"rich": True})
            logger.debug("Exception information:", exc_info=True)

            return ERROR
        except PreviousBuildDirError as exc:
            logger.critical(str(exc))
            logger.debug("Exception information:", exc_info=True)

            return PREVIOUS_BUILD_DIR_ERROR
        except (
            InstallationError,
            BadCommand,
            NetworkConnectionError,
        ) as exc:
            logger.critical(str(exc))
            logger.debug("Exception information:", exc_info=True)

            return ERROR
        except CommandError as exc:
            logger.critical("%s", exc)
            logger.debug("Exception information:", exc_info=True)

            return ERROR
        except BrokenStdoutLoggingError:
            # Bypass our logger and write any remaining messages to
            # stderr because stdout no longer works.
            print("ERROR: Pipe to stdout was broken", file=sys.stderr)
            if level_number <= logging.DEBUG:
                traceback.print_exc(file=sys.stderr)

            return ERROR
        except KeyboardInterrupt:
            logger.critical("Operation cancelled by user")
            logger.debug("Exception information:", exc_info=True)

            return ERROR
        except BaseException:
            logger.critical("Exception:", exc_info=True)

            return UNKNOWN_ERROR

    def parse_args(self, args: List[str]) -> Tuple[Values, List[str]]:
        # factored out for testability
        return self.parser.parse_args(args)

    def main(self, args: List[str]) -> int:
        try:
            with self.main_context():
                return self._main(args)
        finally:
            logging.shutdown()

    def _main(self, args: List[str]) -> int:
        # We must initialize this before the tempdir manager, otherwise the
        # configuration would not be accessible by the time we clean up the
        # tempdir manager.
        self.tempdir_registry = self.enter_context(tempdir_registry())
        # Intentionally set as early as possible so globally-managed temporary
        # directories are available to the rest of the code.
        self.enter_context(global_tempdir_manager())

        options, args = self.parse_args(args)

        # Set verbosity so that it can be used elsewhere.
        self.verbosity = options.verbose - options.quiet

        reconfigure(no_color=options.no_color)
        level_number = setup_logging(
            verbosity=self.verbosity,
            no_color=options.no_color,
            user_log_file=options.log,
        )

        always_enabled_features = set(options.features_enabled) & set(
            cmdoptions.ALWAYS_ENABLED_FEATURES
        )
        if always_enabled_features:
            logger.warning(
                "The following features are always enabled: %s. ",
                ", ".join(sorted(always_enabled_features)),
            )

        # Make sure that the --python argument isn't specified after the
        # subcommand. We can tell, because if --python was specified,
        # we should only reach this point if we're running in the created
        # subprocess, which has the _PIP_RUNNING_IN_SUBPROCESS environment
        # variable set.
        if options.python and "_PIP_RUNNING_IN_SUBPROCESS" not in os.environ:
            logger.critical(
                "The --python option must be placed before the pip subcommand name"
            )
            sys.exit(ERROR)

        # TODO: Try to get these passing down from the command?
        #       without resorting to os.environ to hold these.
        #       This also affects isolated builds and it should.

        if options.no_input:
            os.environ["PIP_NO_INPUT"] = "1"

        if options.exists_action:
            os.environ["PIP_EXISTS_ACTION"] = " ".join(options.exists_action)

        if options.require_venv and not self.ignore_require_venv:
            # If a venv is required check if it can really be found
            if not running_under_virtualenv():
                logger.critical("Could not find an activated virtualenv (required).")
                sys.exit(VIRTUALENV_NOT_FOUND)

        if options.cache_dir:
            options.cache_dir = normalize_path(options.cache_dir)
            if not check_path_owner(options.cache_dir):
                logger.warning(
                    "The directory '%s' or its parent directory is not owned "
                    "or is not writable by the current user. The cache "
                    "has been disabled. Check the permissions and owner of "
                    "that directory. If executing pip with sudo, you should "
                    "use sudo's -H flag.",
                    options.cache_dir,
                )
                options.cache_dir = None

        if options.no_python_version_warning:
            deprecated(
                reason="--no-python-version-warning is deprecated.",
                replacement="to remove the flag as it's a no-op",
                gone_in="25.1",
                issue=13154,
            )

        return self._run_wrapper(level_number, options, args)

# === NexusCore/openenv\Lib\site-packages\win32comext\axscript\test\testHost.py ===
import sys
import unittest

import pythoncom
import win32com.server.policy
import win32com.test.util
from win32com.axscript import axscript
from win32com.axscript.server import axsite
from win32com.client.dynamic import Dispatch
from win32com.server import connect, util

verbose = "-v" in sys.argv


class MySite(axsite.AXSite):
    def __init__(self, *args):
        self.exception_seen = None
        axsite.AXSite.__init__(self, *args)

    def OnScriptError(self, error):
        self.exception_seen = exc = error.GetExceptionInfo()
        context, line, char = error.GetSourcePosition()
        if not verbose:
            return
        print(" >Exception:", exc[1])
        try:
            st = error.GetSourceLineText()
        except pythoncom.com_error:
            st = None
        if st is None:
            st = ""
        text = st + "\n" + (" " * (char - 1)) + "^" + "\n" + exc[2]
        for line in text.splitlines():
            print("  >" + line)


class MyCollection(util.Collection):
    def _NewEnum(self):
        return util.Collection._NewEnum(self)


class Test:
    _public_methods_ = ["echo", "fail"]
    _public_attrs_ = ["collection"]

    def __init__(self):
        self.verbose = verbose
        self.collection = util.wrap(MyCollection([1, "Two", 3]))
        self.last = ""
        self.fail_called = 0

    #    self._connect_server_ = TestConnectServer(self)

    def echo(self, *args):
        self.last = "".join([str(s) for s in args])
        if self.verbose:
            for arg in args:
                print(arg, end=" ")
            print()

    def fail(self, *args):
        print("**** fail() called ***")
        for arg in args:
            print(arg, end=" ")
        print()
        self.fail_called = 1


#    self._connect_server_.Broadcast(last)


#### Connections currently won't work, as there is no way for the engine to
#### know what events we support.  We need typeinfo support.

IID_ITestEvents = pythoncom.MakeIID("{8EB72F90-0D44-11d1-9C4B-00AA00125A98}")


class TestConnectServer(connect.ConnectableServer):
    _connect_interfaces_ = [IID_ITestEvents]

    # The single public method that the client can call on us
    # (ie, as a normal COM server, this exposes just this single method.
    def __init__(self, object):
        self.object = object

    def Broadcast(self, arg):
        # Simply broadcast a notification.
        self._BroadcastNotify(self.NotifyDoneIt, (arg,))

    def NotifyDoneIt(self, interface, arg):
        interface.Invoke(1000, 0, pythoncom.DISPATCH_METHOD, 1, arg)


VBScript = """\
prop = "Property Value"

sub hello(arg1)
   test.echo arg1
end sub

sub testcollection
   if test.collection.Item(0) <> 1 then
     test.fail("Index 0 was wrong")
   end if
   if test.collection.Item(1) <> "Two" then
     test.fail("Index 1 was wrong")
   end if
   if test.collection.Item(2) <> 3 then
     test.fail("Index 2 was wrong")
   end if
   num = 0
   for each item in test.collection
     num = num + 1
   next
   if num <> 3 then
     test.fail("Collection didn't have 3 items")
   end if
end sub
"""
PyScript = """\
# A unicode \xa9omment.
prop = "Property Value"
def hello(arg1):
   test.echo(arg1)

def testcollection():
#   test.collection[1] = "New one"
   got = []
   for item in test.collection:
     got.append(item)
   if got != [1, "Two", 3]:
     test.fail("Didn't get the collection")
   pass
"""

ErrScript = """\
bad code for everyone!
"""

state_map = {
    axscript.SCRIPTSTATE_UNINITIALIZED: "SCRIPTSTATE_UNINITIALIZED",
    axscript.SCRIPTSTATE_INITIALIZED: "SCRIPTSTATE_INITIALIZED",
    axscript.SCRIPTSTATE_STARTED: "SCRIPTSTATE_STARTED",
    axscript.SCRIPTSTATE_CONNECTED: "SCRIPTSTATE_CONNECTED",
    axscript.SCRIPTSTATE_DISCONNECTED: "SCRIPTSTATE_DISCONNECTED",
    axscript.SCRIPTSTATE_CLOSED: "SCRIPTSTATE_CLOSED",
}


def _CheckEngineState(engine, name, state):
    got = engine.engine.eScript.GetScriptState()
    if got != state:
        got_name = state_map.get(got, str(got))
        state_name = state_map.get(state, str(state))
        raise RuntimeError(
            f"Warning - engine {name} has state {got_name}, but expected {state_name}"
        )


class EngineTester(win32com.test.util.TestCase):
    def _TestEngine(self, engineName, code, expected_exc=None):
        echoer = Test()
        model = {
            "test": util.wrap(echoer),
        }
        site = MySite(model)
        engine = site._AddEngine(engineName)
        try:
            _CheckEngineState(site, engineName, axscript.SCRIPTSTATE_INITIALIZED)
            engine.AddCode(code)
            engine.Start()
            _CheckEngineState(site, engineName, axscript.SCRIPTSTATE_STARTED)
            self.assertTrue(not echoer.fail_called, "Fail should not have been called")
            # Now call into the scripts IDispatch
            ob = Dispatch(engine.GetScriptDispatch())
            try:
                ob.hello("Goober")
                self.assertTrue(
                    expected_exc is None,
                    f"Expected {expected_exc!r}, but no exception seen",
                )
            except pythoncom.com_error:
                if expected_exc is None:
                    self.fail(
                        f"Unexpected failure from script code: {site.exception_seen}"
                    )
                if expected_exc not in site.exception_seen[2]:
                    self.fail(
                        f"Could not find {expected_exc!r} in {site.exception_seen[2]!r}"
                    )
                return
            self.assertEqual(echoer.last, "Goober")

            self.assertEqual(str(ob.prop), "Property Value")
            ob.testcollection()
            self.assertTrue(not echoer.fail_called, "Fail should not have been called")

            # Now make sure my engines can evaluate stuff.
            result = engine.eParse.ParseScriptText(
                "1+1", None, None, None, 0, 0, axscript.SCRIPTTEXT_ISEXPRESSION
            )
            self.assertEqual(result, 2)
            # re-initialize to make sure it transitions back to initialized again.
            engine.SetScriptState(axscript.SCRIPTSTATE_INITIALIZED)
            _CheckEngineState(site, engineName, axscript.SCRIPTSTATE_INITIALIZED)
            engine.Start()
            _CheckEngineState(site, engineName, axscript.SCRIPTSTATE_STARTED)

            # Transition back to initialized, then through connected too.
            engine.SetScriptState(axscript.SCRIPTSTATE_INITIALIZED)
            _CheckEngineState(site, engineName, axscript.SCRIPTSTATE_INITIALIZED)
            engine.SetScriptState(axscript.SCRIPTSTATE_CONNECTED)
            _CheckEngineState(site, engineName, axscript.SCRIPTSTATE_CONNECTED)
            engine.SetScriptState(axscript.SCRIPTSTATE_INITIALIZED)
            _CheckEngineState(site, engineName, axscript.SCRIPTSTATE_INITIALIZED)

            engine.SetScriptState(axscript.SCRIPTSTATE_CONNECTED)
            _CheckEngineState(site, engineName, axscript.SCRIPTSTATE_CONNECTED)
            engine.SetScriptState(axscript.SCRIPTSTATE_DISCONNECTED)
            _CheckEngineState(site, engineName, axscript.SCRIPTSTATE_DISCONNECTED)
        finally:
            engine.Close()
            engine = None
            site = None

    def testVB(self):
        self._TestEngine("VBScript", VBScript)

    def testPython(self):
        self._TestEngine("Python", PyScript)

    def testPythonUnicodeError(self):
        self._TestEngine("Python", PyScript)

    def testVBExceptions(self):
        self.assertRaises(pythoncom.com_error, self._TestEngine, "VBScript", ErrScript)


if __name__ == "__main__":
    unittest.main()

# === NexusCore/openenv\Lib\site-packages\outcome\_impl.py ===
from __future__ import annotations

import abc
from typing import (
    TYPE_CHECKING,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generator,
    Generic,
    NoReturn,
    TypeVar,
    Union,
    overload,
)

import attr

from ._util import AlreadyUsedError, remove_tb_frames

if TYPE_CHECKING:
    from typing_extensions import ParamSpec, final
    ArgsT = ParamSpec("ArgsT")
else:

    def final(func):
        return func


__all__ = ['Error', 'Outcome', 'Maybe', 'Value', 'acapture', 'capture']

ValueT = TypeVar("ValueT", covariant=True)
ResultT = TypeVar("ResultT")


@overload
def capture(
        # NoReturn = raises exception, so we should get an error.
        sync_fn: Callable[ArgsT, NoReturn],
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
) -> Error:
    ...


@overload
def capture(
        sync_fn: Callable[ArgsT, ResultT],
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
) -> Value[ResultT] | Error:
    ...


def capture(
        sync_fn: Callable[ArgsT, ResultT],
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
) -> Value[ResultT] | Error:
    """Run ``sync_fn(*args, **kwargs)`` and capture the result.

    Returns:
      Either a :class:`Value` or :class:`Error` as appropriate.

    """
    try:
        return Value(sync_fn(*args, **kwargs))
    except BaseException as exc:
        exc = remove_tb_frames(exc, 1)
        return Error(exc)


@overload
async def acapture(
        async_fn: Callable[ArgsT, Awaitable[NoReturn]],
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
) -> Error:
    ...


@overload
async def acapture(
        async_fn: Callable[ArgsT, Awaitable[ResultT]],
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
) -> Value[ResultT] | Error:
    ...


async def acapture(
        async_fn: Callable[ArgsT, Awaitable[ResultT]],
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
) -> Value[ResultT] | Error:
    """Run ``await async_fn(*args, **kwargs)`` and capture the result.

    Returns:
      Either a :class:`Value` or :class:`Error` as appropriate.

    """
    try:
        return Value(await async_fn(*args, **kwargs))
    except BaseException as exc:
        exc = remove_tb_frames(exc, 1)
        return Error(exc)


@attr.s(repr=False, init=False, slots=True)
class Outcome(abc.ABC, Generic[ValueT]):
    """An abstract class representing the result of a Python computation.

    This class has two concrete subclasses: :class:`Value` representing a
    value, and :class:`Error` representing an exception.

    In addition to the methods described below, comparison operators on
    :class:`Value` and :class:`Error` objects (``==``, ``<``, etc.) check that
    the other object is also a :class:`Value` or :class:`Error` object
    respectively, and then compare the contained objects.

    :class:`Outcome` objects are hashable if the contained objects are
    hashable.

    """
    _unwrapped: bool = attr.ib(default=False, eq=False, init=False)

    def _set_unwrapped(self) -> None:
        if self._unwrapped:
            raise AlreadyUsedError
        object.__setattr__(self, '_unwrapped', True)

    @abc.abstractmethod
    def unwrap(self) -> ValueT:
        """Return or raise the contained value or exception.

        These two lines of code are equivalent::

           x = fn(*args)
           x = outcome.capture(fn, *args).unwrap()

        """

    @abc.abstractmethod
    def send(self, gen: Generator[ResultT, ValueT, object]) -> ResultT:
        """Send or throw the contained value or exception into the given
        generator object.

        Args:
          gen: A generator object supporting ``.send()`` and ``.throw()``
              methods.

        """

    @abc.abstractmethod
    async def asend(self, agen: AsyncGenerator[ResultT, ValueT]) -> ResultT:
        """Send or throw the contained value or exception into the given async
        generator object.

        Args:
          agen: An async generator object supporting ``.asend()`` and
              ``.athrow()`` methods.

        """


@final
@attr.s(frozen=True, repr=False, slots=True)
class Value(Outcome[ValueT], Generic[ValueT]):
    """Concrete :class:`Outcome` subclass representing a regular value.

    """

    value: ValueT = attr.ib()
    """The contained value."""

    def __repr__(self) -> str:
        return f'Value({self.value!r})'

    def unwrap(self) -> ValueT:
        self._set_unwrapped()
        return self.value

    def send(self, gen: Generator[ResultT, ValueT, object]) -> ResultT:
        self._set_unwrapped()
        return gen.send(self.value)

    async def asend(self, agen: AsyncGenerator[ResultT, ValueT]) -> ResultT:
        self._set_unwrapped()
        return await agen.asend(self.value)


@final
@attr.s(frozen=True, repr=False, slots=True)
class Error(Outcome[NoReturn]):
    """Concrete :class:`Outcome` subclass representing a raised exception.

    """

    error: BaseException = attr.ib(
        validator=attr.validators.instance_of(BaseException)
    )
    """The contained exception object."""

    def __repr__(self) -> str:
        return f'Error({self.error!r})'

    def unwrap(self) -> NoReturn:
        self._set_unwrapped()
        # Tracebacks show the 'raise' line below out of context, so let's give
        # this variable a name that makes sense out of context.
        captured_error = self.error
        try:
            raise captured_error
        finally:
            # We want to avoid creating a reference cycle here. Python does
            # collect cycles just fine, so it wouldn't be the end of the world
            # if we did create a cycle, but the cyclic garbage collector adds
            # latency to Python programs, and the more cycles you create, the
            # more often it runs, so it's nicer to avoid creating them in the
            # first place. For more details see:
            #
            #    https://github.com/python-trio/trio/issues/1770
            #
            # In particuar, by deleting this local variables from the 'unwrap'
            # methods frame, we avoid the 'captured_error' object's
            # __traceback__ from indirectly referencing 'captured_error'.
            del captured_error, self

    def send(self, gen: Generator[ResultT, NoReturn, object]) -> ResultT:
        self._set_unwrapped()
        return gen.throw(self.error)

    async def asend(self, agen: AsyncGenerator[ResultT, NoReturn]) -> ResultT:
        self._set_unwrapped()
        return await agen.athrow(self.error)


# A convenience alias to a union of both results, allowing exhaustiveness checking.
Maybe = Union[Value[ValueT], Error]

# === NexusCore/openenv\Lib\site-packages\starlette\staticfiles.py ===
from __future__ import annotations

import importlib.util
import os
import stat
import typing
from email.utils import parsedate

import anyio
import anyio.to_thread

from starlette._utils import get_route_path
from starlette.datastructures import URL, Headers
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse, RedirectResponse, Response
from starlette.types import Receive, Scope, Send

PathLike = typing.Union[str, "os.PathLike[str]"]


class NotModifiedResponse(Response):
    NOT_MODIFIED_HEADERS = (
        "cache-control",
        "content-location",
        "date",
        "etag",
        "expires",
        "vary",
    )

    def __init__(self, headers: Headers):
        super().__init__(
            status_code=304,
            headers={
                name: value
                for name, value in headers.items()
                if name in self.NOT_MODIFIED_HEADERS
            },
        )


class StaticFiles:
    def __init__(
        self,
        *,
        directory: PathLike | None = None,
        packages: list[str | tuple[str, str]] | None = None,
        html: bool = False,
        check_dir: bool = True,
        follow_symlink: bool = False,
    ) -> None:
        self.directory = directory
        self.packages = packages
        self.all_directories = self.get_directories(directory, packages)
        self.html = html
        self.config_checked = False
        self.follow_symlink = follow_symlink
        if check_dir and directory is not None and not os.path.isdir(directory):
            raise RuntimeError(f"Directory '{directory}' does not exist")

    def get_directories(
        self,
        directory: PathLike | None = None,
        packages: list[str | tuple[str, str]] | None = None,
    ) -> list[PathLike]:
        """
        Given `directory` and `packages` arguments, return a list of all the
        directories that should be used for serving static files from.
        """
        directories = []
        if directory is not None:
            directories.append(directory)

        for package in packages or []:
            if isinstance(package, tuple):
                package, statics_dir = package
            else:
                statics_dir = "statics"
            spec = importlib.util.find_spec(package)
            assert spec is not None, f"Package {package!r} could not be found."
            assert spec.origin is not None, f"Package {package!r} could not be found."
            package_directory = os.path.normpath(
                os.path.join(spec.origin, "..", statics_dir)
            )
            assert os.path.isdir(
                package_directory
            ), f"Directory '{statics_dir!r}' in package {package!r} could not be found."
            directories.append(package_directory)

        return directories

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        The ASGI entry point.
        """
        assert scope["type"] == "http"

        if not self.config_checked:
            await self.check_config()
            self.config_checked = True

        path = self.get_path(scope)
        response = await self.get_response(path, scope)
        await response(scope, receive, send)

    def get_path(self, scope: Scope) -> str:
        """
        Given the ASGI scope, return the `path` string to serve up,
        with OS specific path separators, and any '..', '.' components removed.
        """
        route_path = get_route_path(scope)
        return os.path.normpath(os.path.join(*route_path.split("/")))  # noqa: E501

    async def get_response(self, path: str, scope: Scope) -> Response:
        """
        Returns an HTTP response, given the incoming path, method and request headers.
        """
        if scope["method"] not in ("GET", "HEAD"):
            raise HTTPException(status_code=405)

        try:
            full_path, stat_result = await anyio.to_thread.run_sync(
                self.lookup_path, path
            )
        except PermissionError:
            raise HTTPException(status_code=401)
        except OSError:
            raise

        if stat_result and stat.S_ISREG(stat_result.st_mode):
            # We have a static file to serve.
            return self.file_response(full_path, stat_result, scope)

        elif stat_result and stat.S_ISDIR(stat_result.st_mode) and self.html:
            # We're in HTML mode, and have got a directory URL.
            # Check if we have 'index.html' file to serve.
            index_path = os.path.join(path, "index.html")
            full_path, stat_result = await anyio.to_thread.run_sync(
                self.lookup_path, index_path
            )
            if stat_result is not None and stat.S_ISREG(stat_result.st_mode):
                if not scope["path"].endswith("/"):
                    # Directory URLs should redirect to always end in "/".
                    url = URL(scope=scope)
                    url = url.replace(path=url.path + "/")
                    return RedirectResponse(url=url)
                return self.file_response(full_path, stat_result, scope)

        if self.html:
            # Check for '404.html' if we're in HTML mode.
            full_path, stat_result = await anyio.to_thread.run_sync(
                self.lookup_path, "404.html"
            )
            if stat_result and stat.S_ISREG(stat_result.st_mode):
                return FileResponse(full_path, stat_result=stat_result, status_code=404)
        raise HTTPException(status_code=404)

    def lookup_path(self, path: str) -> tuple[str, os.stat_result | None]:
        for directory in self.all_directories:
            joined_path = os.path.join(directory, path)
            if self.follow_symlink:
                full_path = os.path.abspath(joined_path)
            else:
                full_path = os.path.realpath(joined_path)
            directory = os.path.realpath(directory)
            if os.path.commonpath([full_path, directory]) != directory:
                # Don't allow misbehaving clients to break out of the static files
                # directory.
                continue
            try:
                return full_path, os.stat(full_path)
            except (FileNotFoundError, NotADirectoryError):
                continue
        return "", None

    def file_response(
        self,
        full_path: PathLike,
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        request_headers = Headers(scope=scope)

        response = FileResponse(
            full_path, status_code=status_code, stat_result=stat_result
        )
        if self.is_not_modified(response.headers, request_headers):
            return NotModifiedResponse(response.headers)
        return response

    async def check_config(self) -> None:
        """
        Perform a one-off configuration check that StaticFiles is actually
        pointed at a directory, so that we can raise loud errors rather than
        just returning 404 responses.
        """
        if self.directory is None:
            return

        try:
            stat_result = await anyio.to_thread.run_sync(os.stat, self.directory)
        except FileNotFoundError:
            raise RuntimeError(
                f"StaticFiles directory '{self.directory}' does not exist."
            )
        if not (stat.S_ISDIR(stat_result.st_mode) or stat.S_ISLNK(stat_result.st_mode)):
            raise RuntimeError(
                f"StaticFiles path '{self.directory}' is not a directory."
            )

    def is_not_modified(
        self, response_headers: Headers, request_headers: Headers
    ) -> bool:
        """
        Given the request and response headers, return `True` if an HTTP
        "Not Modified" response could be returned instead.
        """
        try:
            if_none_match = request_headers["if-none-match"]
            etag = response_headers["etag"]
            if etag in [tag.strip(" W/") for tag in if_none_match.split(",")]:
                return True
        except KeyError:
            pass

        try:
            if_modified_since = parsedate(request_headers["if-modified-since"])
            last_modified = parsedate(response_headers["last-modified"])
            if (
                if_modified_since is not None
                and last_modified is not None
                and if_modified_since >= last_modified
            ):
                return True
        except KeyError:
            pass

        return False

# === NexusCore/openenv\Lib\site-packages\_distutils_hack\__init__.py ===
# don't import any costly modules
import os
import sys

report_url = (
    "https://github.com/pypa/setuptools/issues/new?template=distutils-deprecation.yml"
)


def warn_distutils_present():
    if 'distutils' not in sys.modules:
        return
    import warnings

    warnings.warn(
        "Distutils was imported before Setuptools, but importing Setuptools "
        "also replaces the `distutils` module in `sys.modules`. This may lead "
        "to undesirable behaviors or errors. To avoid these issues, avoid "
        "using distutils directly, ensure that setuptools is installed in the "
        "traditional way (e.g. not an editable install), and/or make sure "
        "that setuptools is always imported before distutils."
    )


def clear_distutils():
    if 'distutils' not in sys.modules:
        return
    import warnings

    warnings.warn(
        "Setuptools is replacing distutils. Support for replacing "
        "an already imported distutils is deprecated. In the future, "
        "this condition will fail. "
        f"Register concerns at {report_url}"
    )
    mods = [
        name
        for name in sys.modules
        if name == "distutils" or name.startswith("distutils.")
    ]
    for name in mods:
        del sys.modules[name]


def enabled():
    """
    Allow selection of distutils by environment variable.
    """
    which = os.environ.get('SETUPTOOLS_USE_DISTUTILS', 'local')
    if which == 'stdlib':
        import warnings

        warnings.warn(
            "Reliance on distutils from stdlib is deprecated. Users "
            "must rely on setuptools to provide the distutils module. "
            "Avoid importing distutils or import setuptools first, "
            "and avoid setting SETUPTOOLS_USE_DISTUTILS=stdlib. "
            f"Register concerns at {report_url}"
        )
    return which == 'local'


def ensure_local_distutils():
    import importlib

    clear_distutils()

    # With the DistutilsMetaFinder in place,
    # perform an import to cause distutils to be
    # loaded from setuptools._distutils. Ref #2906.
    with shim():
        importlib.import_module('distutils')

    # check that submodules load as expected
    core = importlib.import_module('distutils.core')
    assert '_distutils' in core.__file__, core.__file__
    assert 'setuptools._distutils.log' not in sys.modules


def do_override():
    """
    Ensure that the local copy of distutils is preferred over stdlib.

    See https://github.com/pypa/setuptools/issues/417#issuecomment-392298401
    for more motivation.
    """
    if enabled():
        warn_distutils_present()
        ensure_local_distutils()


class _TrivialRe:
    def __init__(self, *patterns) -> None:
        self._patterns = patterns

    def match(self, string):
        return all(pat in string for pat in self._patterns)


class DistutilsMetaFinder:
    def find_spec(self, fullname, path, target=None):
        # optimization: only consider top level modules and those
        # found in the CPython test suite.
        if path is not None and not fullname.startswith('test.'):
            return None

        method_name = 'spec_for_{fullname}'.format(**locals())
        method = getattr(self, method_name, lambda: None)
        return method()

    def spec_for_distutils(self):
        if self.is_cpython():
            return None

        import importlib
        import importlib.abc
        import importlib.util

        try:
            mod = importlib.import_module('setuptools._distutils')
        except Exception:
            # There are a couple of cases where setuptools._distutils
            # may not be present:
            # - An older Setuptools without a local distutils is
            #   taking precedence. Ref #2957.
            # - Path manipulation during sitecustomize removes
            #   setuptools from the path but only after the hook
            #   has been loaded. Ref #2980.
            # In either case, fall back to stdlib behavior.
            return None

        class DistutilsLoader(importlib.abc.Loader):
            def create_module(self, spec):
                mod.__name__ = 'distutils'
                return mod

            def exec_module(self, module):
                pass

        return importlib.util.spec_from_loader(
            'distutils', DistutilsLoader(), origin=mod.__file__
        )

    @staticmethod
    def is_cpython():
        """
        Suppress supplying distutils for CPython (build and tests).
        Ref #2965 and #3007.
        """
        return os.path.isfile('pybuilddir.txt')

    def spec_for_pip(self):
        """
        Ensure stdlib distutils when running under pip.
        See pypa/pip#8761 for rationale.
        """
        if sys.version_info >= (3, 12) or self.pip_imported_during_build():
            return
        clear_distutils()
        self.spec_for_distutils = lambda: None

    @classmethod
    def pip_imported_during_build(cls):
        """
        Detect if pip is being imported in a build script. Ref #2355.
        """
        import traceback

        return any(
            cls.frame_file_is_setup(frame) for frame, line in traceback.walk_stack(None)
        )

    @staticmethod
    def frame_file_is_setup(frame):
        """
        Return True if the indicated frame suggests a setup.py file.
        """
        # some frames may not have __file__ (#2940)
        return frame.f_globals.get('__file__', '').endswith('setup.py')

    def spec_for_sensitive_tests(self):
        """
        Ensure stdlib distutils when running select tests under CPython.

        python/cpython#91169
        """
        clear_distutils()
        self.spec_for_distutils = lambda: None

    sensitive_tests = (
        [
            'test.test_distutils',
            'test.test_peg_generator',
            'test.test_importlib',
        ]
        if sys.version_info < (3, 10)
        else [
            'test.test_distutils',
        ]
    )


for name in DistutilsMetaFinder.sensitive_tests:
    setattr(
        DistutilsMetaFinder,
        f'spec_for_{name}',
        DistutilsMetaFinder.spec_for_sensitive_tests,
    )


DISTUTILS_FINDER = DistutilsMetaFinder()


def add_shim():
    DISTUTILS_FINDER in sys.meta_path or insert_shim()


class shim:
    def __enter__(self) -> None:
        insert_shim()

    def __exit__(self, exc: object, value: object, tb: object) -> None:
        _remove_shim()


def insert_shim():
    sys.meta_path.insert(0, DISTUTILS_FINDER)


def _remove_shim():
    try:
        sys.meta_path.remove(DISTUTILS_FINDER)
    except ValueError:
        pass


if sys.version_info < (3, 12):
    # DistutilsMetaFinder can only be disabled in Python < 3.12 (PEP 632)
    remove_shim = _remove_shim

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\permission_service\transports\base.py ===
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
import abc
from typing import Awaitable, Callable, Dict, Optional, Sequence, Union

import google.api_core
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.oauth2 import service_account  # type: ignore
from google.protobuf import empty_pb2  # type: ignore

from google.ai.generativelanguage_v1beta3 import gapic_version as package_version
from google.ai.generativelanguage_v1beta3.types import permission as gag_permission
from google.ai.generativelanguage_v1beta3.types import permission
from google.ai.generativelanguage_v1beta3.types import permission_service

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


class PermissionServiceTransport(abc.ABC):
    """Abstract transport class for PermissionService."""

    AUTH_SCOPES = ()

    DEFAULT_HOST: str = "generativelanguage.googleapis.com"

    def __init__(
        self,
        *,
        host: str = DEFAULT_HOST,
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'generativelanguage.googleapis.com').
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A list of scopes.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
        """

        scopes_kwargs = {"scopes": scopes, "default_scopes": self.AUTH_SCOPES}

        # Save the scopes.
        self._scopes = scopes

        # If no credentials are provided, then determine the appropriate
        # defaults.
        if credentials and credentials_file:
            raise core_exceptions.DuplicateCredentialArgs(
                "'credentials_file' and 'credentials' are mutually exclusive"
            )

        if credentials_file is not None:
            credentials, _ = google.auth.load_credentials_from_file(
                credentials_file, **scopes_kwargs, quota_project_id=quota_project_id
            )
        elif credentials is None:
            credentials, _ = google.auth.default(
                **scopes_kwargs, quota_project_id=quota_project_id
            )
            # Don't apply audience if the credentials file passed from user.
            if hasattr(credentials, "with_gdch_audience"):
                credentials = credentials.with_gdch_audience(
                    api_audience if api_audience else host
                )

        # If the credentials are service account credentials, then always try to use self signed JWT.
        if (
            always_use_jwt_access
            and isinstance(credentials, service_account.Credentials)
            and hasattr(service_account.Credentials, "with_always_use_jwt_access")
        ):
            credentials = credentials.with_always_use_jwt_access(True)

        # Save the credentials.
        self._credentials = credentials

        # Save the hostname. Default to port 443 (HTTPS) if none is specified.
        if ":" not in host:
            host += ":443"
        self._host = host

    @property
    def host(self):
        return self._host

    def _prep_wrapped_messages(self, client_info):
        # Precompute the wrapped methods.
        self._wrapped_methods = {
            self.create_permission: gapic_v1.method.wrap_method(
                self.create_permission,
                default_timeout=None,
                client_info=client_info,
            ),
            self.get_permission: gapic_v1.method.wrap_method(
                self.get_permission,
                default_timeout=None,
                client_info=client_info,
            ),
            self.list_permissions: gapic_v1.method.wrap_method(
                self.list_permissions,
                default_timeout=None,
                client_info=client_info,
            ),
            self.update_permission: gapic_v1.method.wrap_method(
                self.update_permission,
                default_timeout=None,
                client_info=client_info,
            ),
            self.delete_permission: gapic_v1.method.wrap_method(
                self.delete_permission,
                default_timeout=None,
                client_info=client_info,
            ),
            self.transfer_ownership: gapic_v1.method.wrap_method(
                self.transfer_ownership,
                default_timeout=None,
                client_info=client_info,
            ),
        }

    def close(self):
        """Closes resources associated with the transport.

        .. warning::
             Only call this method if the transport is NOT shared
             with other clients - this may cause errors in other clients!
        """
        raise NotImplementedError()

    @property
    def create_permission(
        self,
    ) -> Callable[
        [permission_service.CreatePermissionRequest],
        Union[gag_permission.Permission, Awaitable[gag_permission.Permission]],
    ]:
        raise NotImplementedError()

    @property
    def get_permission(
        self,
    ) -> Callable[
        [permission_service.GetPermissionRequest],
        Union[permission.Permission, Awaitable[permission.Permission]],
    ]:
        raise NotImplementedError()

    @property
    def list_permissions(
        self,
    ) -> Callable[
        [permission_service.ListPermissionsRequest],
        Union[
            permission_service.ListPermissionsResponse,
            Awaitable[permission_service.ListPermissionsResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def update_permission(
        self,
    ) -> Callable[
        [permission_service.UpdatePermissionRequest],
        Union[gag_permission.Permission, Awaitable[gag_permission.Permission]],
    ]:
        raise NotImplementedError()

    @property
    def delete_permission(
        self,
    ) -> Callable[
        [permission_service.DeletePermissionRequest],
        Union[empty_pb2.Empty, Awaitable[empty_pb2.Empty]],
    ]:
        raise NotImplementedError()

    @property
    def transfer_ownership(
        self,
    ) -> Callable[
        [permission_service.TransferOwnershipRequest],
        Union[
            permission_service.TransferOwnershipResponse,
            Awaitable[permission_service.TransferOwnershipResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def kind(self) -> str:
        raise NotImplementedError()


__all__ = ("PermissionServiceTransport",)

# === NexusCore/openenv\Lib\site-packages\google\api_core\retry\retry_unary_async.py ===
# Copyright 2020 Google LLC
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

"""Helpers for retrying coroutine functions with exponential back-off.

The :class:`AsyncRetry` decorator shares most functionality and behavior with
:class:`Retry`, but supports coroutine functions. Please refer to description
of :class:`Retry` for more details.

By default, this decorator will retry transient
API errors (see :func:`if_transient_error`). For example:

.. code-block:: python

    @retry_async.AsyncRetry()
    async def call_flaky_rpc():
        return await client.flaky_rpc()

    # Will retry flaky_rpc() if it raises transient API errors.
    result = await call_flaky_rpc()

You can pass a custom predicate to retry on different exceptions, such as
waiting for an eventually consistent item to be available:

.. code-block:: python

    @retry_async.AsyncRetry(predicate=retry_async.if_exception_type(exceptions.NotFound))
    async def check_if_exists():
        return await client.does_thing_exist()

    is_available = await check_if_exists()

Some client library methods apply retry automatically. These methods can accept
a ``retry`` parameter that allows you to configure the behavior:

.. code-block:: python

    my_retry = retry_async.AsyncRetry(timeout=60)
    result = await client.some_method(retry=my_retry)

"""

from __future__ import annotations

import asyncio
import time
import functools
from typing import (
    Awaitable,
    Any,
    Callable,
    Iterable,
    TypeVar,
    TYPE_CHECKING,
)

from google.api_core.retry.retry_base import _BaseRetry
from google.api_core.retry.retry_base import _retry_error_helper
from google.api_core.retry.retry_base import exponential_sleep_generator
from google.api_core.retry.retry_base import build_retry_error
from google.api_core.retry.retry_base import RetryFailureReason

# for backwards compatibility, expose helpers in this module
from google.api_core.retry.retry_base import if_exception_type  # noqa
from google.api_core.retry.retry_base import if_transient_error  # noqa

if TYPE_CHECKING:
    import sys

    if sys.version_info >= (3, 10):
        from typing import ParamSpec
    else:
        from typing_extensions import ParamSpec

    _P = ParamSpec("_P")  # target function call parameters
    _R = TypeVar("_R")  # target function returned value

_DEFAULT_INITIAL_DELAY = 1.0  # seconds
_DEFAULT_MAXIMUM_DELAY = 60.0  # seconds
_DEFAULT_DELAY_MULTIPLIER = 2.0
_DEFAULT_DEADLINE = 60.0 * 2.0  # seconds
_DEFAULT_TIMEOUT = 60.0 * 2.0  # seconds


async def retry_target(
    target: Callable[[], Awaitable[_R]],
    predicate: Callable[[Exception], bool],
    sleep_generator: Iterable[float],
    timeout: float | None = None,
    on_error: Callable[[Exception], None] | None = None,
    exception_factory: Callable[
        [list[Exception], RetryFailureReason, float | None],
        tuple[Exception, Exception | None],
    ] = build_retry_error,
    **kwargs,
):
    """Await a coroutine and retry if it fails.

    This is the lowest-level retry helper. Generally, you'll use the
    higher-level retry helper :class:`Retry`.

    Args:
        target(Callable[[], Any]): The function to call and retry. This must be a
            nullary function - apply arguments with `functools.partial`.
        predicate (Callable[Exception]): A callable used to determine if an
            exception raised by the target should be considered retryable.
            It should return True to retry or False otherwise.
        sleep_generator (Iterable[float]): An infinite iterator that determines
            how long to sleep between retries.
        timeout (Optional[float]): How long to keep retrying the target, in seconds.
            Note: timeout is only checked before initiating a retry, so the target may
            run past the timeout value as long as it is healthy.
        on_error (Optional[Callable[Exception]]): If given, the on_error
            callback will be called with each retryable exception raised by the
            target. Any error raised by this function will *not* be caught.
        exception_factory: A function that is called when the retryable reaches
            a terminal failure state, used to construct an exception to be raised.
            It takes a list of all exceptions encountered, a retry.RetryFailureReason
            enum indicating the failure cause, and the original timeout value
            as arguments. It should return a tuple of the exception to be raised,
            along with the cause exception if any. The default implementation will raise
            a RetryError on timeout, or the last exception encountered otherwise.
        deadline (float): DEPRECATED use ``timeout`` instead. For backward
            compatibility, if set it will override the ``timeout`` parameter.

    Returns:
        Any: the return value of the target function.

    Raises:
        ValueError: If the sleep generator stops yielding values.
        Exception: a custom exception specified by the exception_factory if provided.
            If no exception_factory is provided:
                google.api_core.RetryError: If the timeout is exceeded while retrying.
                Exception: If the target raises an error that isn't retryable.
    """

    timeout = kwargs.get("deadline", timeout)

    deadline = time.monotonic() + timeout if timeout is not None else None
    error_list: list[Exception] = []
    sleep_iter = iter(sleep_generator)

    # continue trying until an attempt completes, or a terminal exception is raised in _retry_error_helper
    # TODO: support max_attempts argument: https://github.com/googleapis/python-api-core/issues/535
    while True:
        try:
            return await target()
        # pylint: disable=broad-except
        # This function explicitly must deal with broad exceptions.
        except Exception as exc:
            # defer to shared logic for handling errors
            next_sleep = _retry_error_helper(
                exc,
                deadline,
                sleep_iter,
                error_list,
                predicate,
                on_error,
                exception_factory,
                timeout,
            )
            # if exception not raised, sleep before next attempt
            await asyncio.sleep(next_sleep)


class AsyncRetry(_BaseRetry):
    """Exponential retry decorator for async coroutines.

    This class is a decorator used to add exponential back-off retry behavior
    to an RPC call.

    Although the default behavior is to retry transient API errors, a
    different predicate can be provided to retry other exceptions.

    Args:
        predicate (Callable[Exception]): A callable that should return ``True``
            if the given exception is retryable.
        initial (float): The minimum amount of time to delay in seconds. This
            must be greater than 0.
        maximum (float): The maximum amount of time to delay in seconds.
        multiplier (float): The multiplier applied to the delay.
        timeout (Optional[float]): How long to keep retrying in seconds.
            Note: timeout is only checked before initiating a retry, so the target may
            run past the timeout value as long as it is healthy.
        on_error (Optional[Callable[Exception]]): A function to call while processing
            a retryable exception. Any error raised by this function will
            *not* be caught.
        deadline (float): DEPRECATED use ``timeout`` instead. If set it will
        override ``timeout`` parameter.
    """

    def __call__(
        self,
        func: Callable[..., Awaitable[_R]],
        on_error: Callable[[Exception], Any] | None = None,
    ) -> Callable[_P, Awaitable[_R]]:
        """Wrap a callable with retry behavior.

        Args:
            func (Callable): The callable or stream to add retry behavior to.
            on_error (Optional[Callable[Exception]]): If given, the
                on_error callback will be called with each retryable exception
                raised by the wrapped function. Any error raised by this
                function will *not* be caught. If on_error was specified in the
                constructor, this value will be ignored.

        Returns:
            Callable: A callable that will invoke ``func`` with retry
                behavior.
        """
        if self._on_error is not None:
            on_error = self._on_error

        @functools.wraps(func)
        async def retry_wrapped_func(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            """A wrapper that calls target function with retry."""
            sleep_generator = exponential_sleep_generator(
                self._initial, self._maximum, multiplier=self._multiplier
            )
            return await retry_target(
                functools.partial(func, *args, **kwargs),
                predicate=self._predicate,
                sleep_generator=sleep_generator,
                timeout=self._timeout,
                on_error=on_error,
            )

        return retry_wrapped_func

# === NexusCore/openenv\Lib\site-packages\grpc\aio\_server.py ===
# Copyright 2019 The gRPC Authors
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
"""Server-side implementation of gRPC Asyncio Python."""

from concurrent.futures import Executor
from typing import Any, Dict, Optional, Sequence

import grpc
from grpc import _common
from grpc import _compression
from grpc._cython import cygrpc

from . import _base_server
from ._interceptor import ServerInterceptor
from ._typing import ChannelArgumentType


def _augment_channel_arguments(
    base_options: ChannelArgumentType, compression: Optional[grpc.Compression]
):
    compression_option = _compression.create_channel_option(compression)
    return tuple(base_options) + compression_option


class Server(_base_server.Server):
    """Serves RPCs."""

    def __init__(
        self,
        thread_pool: Optional[Executor],
        generic_handlers: Optional[Sequence[grpc.GenericRpcHandler]],
        interceptors: Optional[Sequence[Any]],
        options: ChannelArgumentType,
        maximum_concurrent_rpcs: Optional[int],
        compression: Optional[grpc.Compression],
    ):
        self._loop = cygrpc.get_working_loop()
        if interceptors:
            invalid_interceptors = [
                interceptor
                for interceptor in interceptors
                if not isinstance(interceptor, ServerInterceptor)
            ]
            if invalid_interceptors:
                raise ValueError(
                    "Interceptor must be ServerInterceptor, the "
                    f"following are invalid: {invalid_interceptors}"
                )
        self._server = cygrpc.AioServer(
            self._loop,
            thread_pool,
            generic_handlers,
            interceptors,
            _augment_channel_arguments(options, compression),
            maximum_concurrent_rpcs,
        )

    def add_generic_rpc_handlers(
        self, generic_rpc_handlers: Sequence[grpc.GenericRpcHandler]
    ) -> None:
        """Registers GenericRpcHandlers with this Server.

        This method is only safe to call before the server is started.

        Args:
          generic_rpc_handlers: A sequence of GenericRpcHandlers that will be
          used to service RPCs.
        """
        self._server.add_generic_rpc_handlers(generic_rpc_handlers)

    def add_registered_method_handlers(
        self,
        service_name: str,
        method_handlers: Dict[str, grpc.RpcMethodHandler],
    ) -> None:
        # TODO(xuanwn): Implement this for AsyncIO.
        pass

    def add_insecure_port(self, address: str) -> int:
        """Opens an insecure port for accepting RPCs.

        This method may only be called before starting the server.

        Args:
          address: The address for which to open a port. If the port is 0,
            or not specified in the address, then the gRPC runtime will choose a port.

        Returns:
          An integer port on which the server will accept RPC requests.
        """
        return _common.validate_port_binding_result(
            address, self._server.add_insecure_port(_common.encode(address))
        )

    def add_secure_port(
        self, address: str, server_credentials: grpc.ServerCredentials
    ) -> int:
        """Opens a secure port for accepting RPCs.

        This method may only be called before starting the server.

        Args:
          address: The address for which to open a port.
            if the port is 0, or not specified in the address, then the gRPC
            runtime will choose a port.
          server_credentials: A ServerCredentials object.

        Returns:
          An integer port on which the server will accept RPC requests.
        """
        return _common.validate_port_binding_result(
            address,
            self._server.add_secure_port(
                _common.encode(address), server_credentials
            ),
        )

    async def start(self) -> None:
        """Starts this Server.

        This method may only be called once. (i.e. it is not idempotent).
        """
        await self._server.start()

    async def stop(self, grace: Optional[float]) -> None:
        """Stops this Server.

        This method immediately stops the server from servicing new RPCs in
        all cases.

        If a grace period is specified, this method waits until all active
        RPCs are finished or until the grace period is reached. RPCs that haven't
        been terminated within the grace period are aborted.
        If a grace period is not specified (by passing None for grace), all
        existing RPCs are aborted immediately and this method blocks until
        the last RPC handler terminates.

        This method is idempotent and may be called at any time. Passing a
        smaller grace value in a subsequent call will have the effect of
        stopping the Server sooner (passing None will have the effect of
        stopping the server immediately). Passing a larger grace value in a
        subsequent call will not have the effect of stopping the server later
        (i.e. the most restrictive grace value is used).

        Args:
          grace: A duration of time in seconds or None.
        """
        await self._server.shutdown(grace)

    async def wait_for_termination(
        self, timeout: Optional[float] = None
    ) -> bool:
        """Block current coroutine until the server stops.

        This is an EXPERIMENTAL API.

        The wait will not consume computational resources during blocking, and
        it will block until one of the two following conditions are met:

        1) The server is stopped or terminated;
        2) A timeout occurs if timeout is not `None`.

        The timeout argument works in the same way as `threading.Event.wait()`.
        https://docs.python.org/3/library/threading.html#threading.Event.wait

        Args:
          timeout: A floating point number specifying a timeout for the
            operation in seconds.

        Returns:
          A bool indicates if the operation times out.
        """
        return await self._server.wait_for_termination(timeout)

    def __del__(self):
        """Schedules a graceful shutdown in current event loop.

        The Cython AioServer doesn't hold a ref-count to this class. It should
        be safe to slightly extend the underlying Cython object's life span.
        """
        if hasattr(self, "_server"):
            if self._server.is_running():
                cygrpc.schedule_coro_threadsafe(
                    self._server.shutdown(None),
                    self._loop,
                )


def server(
    migration_thread_pool: Optional[Executor] = None,
    handlers: Optional[Sequence[grpc.GenericRpcHandler]] = None,
    interceptors: Optional[Sequence[Any]] = None,
    options: Optional[ChannelArgumentType] = None,
    maximum_concurrent_rpcs: Optional[int] = None,
    compression: Optional[grpc.Compression] = None,
):
    """Creates a Server with which RPCs can be serviced.

    Args:
      migration_thread_pool: A futures.ThreadPoolExecutor to be used by the
        Server to execute non-AsyncIO RPC handlers for migration purpose.
      handlers: An optional list of GenericRpcHandlers used for executing RPCs.
        More handlers may be added by calling add_generic_rpc_handlers any time
        before the server is started.
      interceptors: An optional list of ServerInterceptor objects that observe
        and optionally manipulate the incoming RPCs before handing them over to
        handlers. The interceptors are given control in the order they are
        specified. This is an EXPERIMENTAL API.
      options: An optional list of key-value pairs (:term:`channel_arguments` in gRPC runtime)
        to configure the channel.
      maximum_concurrent_rpcs: The maximum number of concurrent RPCs this server
        will service before returning RESOURCE_EXHAUSTED status, or None to
        indicate no limit.
      compression: An element of grpc.compression, e.g.
        grpc.compression.Gzip. This compression algorithm will be used for the
        lifetime of the server unless overridden by set_compression.

    Returns:
      A Server object.
    """
    return Server(
        migration_thread_pool,
        () if handlers is None else handlers,
        () if interceptors is None else interceptors,
        () if options is None else options,
        maximum_concurrent_rpcs,
        compression,
    )

# === NexusCore/openenv\Lib\site-packages\openai\types\responses\response.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Union, Optional
from typing_extensions import Literal, TypeAlias

from .tool import Tool
from ..._models import BaseModel
from .response_error import ResponseError
from .response_usage import ResponseUsage
from .response_prompt import ResponsePrompt
from .response_status import ResponseStatus
from ..shared.metadata import Metadata
from ..shared.reasoning import Reasoning
from .tool_choice_types import ToolChoiceTypes
from .response_input_item import ResponseInputItem
from .tool_choice_options import ToolChoiceOptions
from .response_output_item import ResponseOutputItem
from .response_text_config import ResponseTextConfig
from .tool_choice_function import ToolChoiceFunction
from ..shared.responses_model import ResponsesModel

__all__ = ["Response", "IncompleteDetails", "ToolChoice"]


class IncompleteDetails(BaseModel):
    reason: Optional[Literal["max_output_tokens", "content_filter"]] = None
    """The reason why the response is incomplete."""


ToolChoice: TypeAlias = Union[ToolChoiceOptions, ToolChoiceTypes, ToolChoiceFunction]


class Response(BaseModel):
    id: str
    """Unique identifier for this Response."""

    created_at: float
    """Unix timestamp (in seconds) of when this Response was created."""

    error: Optional[ResponseError] = None
    """An error object returned when the model fails to generate a Response."""

    incomplete_details: Optional[IncompleteDetails] = None
    """Details about why the response is incomplete."""

    instructions: Union[str, List[ResponseInputItem], None] = None
    """A system (or developer) message inserted into the model's context.

    When using along with `previous_response_id`, the instructions from a previous
    response will not be carried over to the next response. This makes it simple to
    swap out system (or developer) messages in new responses.
    """

    metadata: Optional[Metadata] = None
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    model: ResponsesModel
    """Model ID used to generate the response, like `gpt-4o` or `o3`.

    OpenAI offers a wide range of models with different capabilities, performance
    characteristics, and price points. Refer to the
    [model guide](https://platform.openai.com/docs/models) to browse and compare
    available models.
    """

    object: Literal["response"]
    """The object type of this resource - always set to `response`."""

    output: List[ResponseOutputItem]
    """An array of content items generated by the model.

    - The length and order of items in the `output` array is dependent on the
      model's response.
    - Rather than accessing the first item in the `output` array and assuming it's
      an `assistant` message with the content generated by the model, you might
      consider using the `output_text` property where supported in SDKs.
    """

    parallel_tool_calls: bool
    """Whether to allow the model to run tool calls in parallel."""

    temperature: Optional[float] = None
    """What sampling temperature to use, between 0 and 2.

    Higher values like 0.8 will make the output more random, while lower values like
    0.2 will make it more focused and deterministic. We generally recommend altering
    this or `top_p` but not both.
    """

    tool_choice: ToolChoice
    """
    How the model should select which tool (or tools) to use when generating a
    response. See the `tools` parameter to see how to specify which tools the model
    can call.
    """

    tools: List[Tool]
    """An array of tools the model may call while generating a response.

    You can specify which tool to use by setting the `tool_choice` parameter.

    The two categories of tools you can provide the model are:

    - **Built-in tools**: Tools that are provided by OpenAI that extend the model's
      capabilities, like
      [web search](https://platform.openai.com/docs/guides/tools-web-search) or
      [file search](https://platform.openai.com/docs/guides/tools-file-search).
      Learn more about
      [built-in tools](https://platform.openai.com/docs/guides/tools).
    - **Function calls (custom tools)**: Functions that are defined by you, enabling
      the model to call your own code. Learn more about
      [function calling](https://platform.openai.com/docs/guides/function-calling).
    """

    top_p: Optional[float] = None
    """
    An alternative to sampling with temperature, called nucleus sampling, where the
    model considers the results of the tokens with top_p probability mass. So 0.1
    means only the tokens comprising the top 10% probability mass are considered.

    We generally recommend altering this or `temperature` but not both.
    """

    background: Optional[bool] = None
    """Whether to run the model response in the background.

    [Learn more](https://platform.openai.com/docs/guides/background).
    """

    max_output_tokens: Optional[int] = None
    """
    An upper bound for the number of tokens that can be generated for a response,
    including visible output tokens and
    [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).
    """

    previous_response_id: Optional[str] = None
    """The unique ID of the previous response to the model.

    Use this to create multi-turn conversations. Learn more about
    [conversation state](https://platform.openai.com/docs/guides/conversation-state).
    """

    prompt: Optional[ResponsePrompt] = None
    """Reference to a prompt template and its variables.

    [Learn more](https://platform.openai.com/docs/guides/text?api-mode=responses#reusable-prompts).
    """

    reasoning: Optional[Reasoning] = None
    """**o-series models only**

    Configuration options for
    [reasoning models](https://platform.openai.com/docs/guides/reasoning).
    """

    service_tier: Optional[Literal["auto", "default", "flex", "scale"]] = None
    """Specifies the latency tier to use for processing the request.

    This parameter is relevant for customers subscribed to the scale tier service:

    - If set to 'auto', and the Project is Scale tier enabled, the system will
      utilize scale tier credits until they are exhausted.
    - If set to 'auto', and the Project is not Scale tier enabled, the request will
      be processed using the default service tier with a lower uptime SLA and no
      latency guarantee.
    - If set to 'default', the request will be processed using the default service
      tier with a lower uptime SLA and no latency guarantee.
    - If set to 'flex', the request will be processed with the Flex Processing
      service tier.
      [Learn more](https://platform.openai.com/docs/guides/flex-processing).
    - When not set, the default behavior is 'auto'.

    When this parameter is set, the response body will include the `service_tier`
    utilized.
    """

    status: Optional[ResponseStatus] = None
    """The status of the response generation.

    One of `completed`, `failed`, `in_progress`, `cancelled`, `queued`, or
    `incomplete`.
    """

    text: Optional[ResponseTextConfig] = None
    """Configuration options for a text response from the model.

    Can be plain text or structured JSON data. Learn more:

    - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
    - [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
    """

    truncation: Optional[Literal["auto", "disabled"]] = None
    """The truncation strategy to use for the model response.

    - `auto`: If the context of this response and previous ones exceeds the model's
      context window size, the model will truncate the response to fit the context
      window by dropping input items in the middle of the conversation.
    - `disabled` (default): If a model response will exceed the context window size
      for a model, the request will fail with a 400 error.
    """

    usage: Optional[ResponseUsage] = None
    """
    Represents token usage details including input tokens, output tokens, a
    breakdown of output tokens, and the total tokens used.
    """

    user: Optional[str] = None
    """A stable identifier for your end-users.

    Used to boost cache hit rates by better bucketing similar requests and to help
    OpenAI detect and prevent abuse.
    [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).
    """

    @property
    def output_text(self) -> str:
        """Convenience property that aggregates all `output_text` items from the `output`
        list.

        If no `output_text` content blocks exist, then an empty string is returned.
        """
        texts: List[str] = []
        for output in self.output:
            if output.type == "message":
                for content in output.content:
                    if content.type == "output_text":
                        texts.append(content.text)

        return "".join(texts)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\shortcuts\utils.py ===
from __future__ import annotations

from asyncio.events import AbstractEventLoop
from typing import TYPE_CHECKING, Any, TextIO

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app_or_none, get_app_session
from prompt_toolkit.application.run_in_terminal import run_in_terminal
from prompt_toolkit.formatted_text import (
    FormattedText,
    StyleAndTextTuples,
    to_formatted_text,
)
from prompt_toolkit.input import DummyInput
from prompt_toolkit.layout import Layout
from prompt_toolkit.output import ColorDepth, Output
from prompt_toolkit.output.defaults import create_output
from prompt_toolkit.renderer import (
    print_formatted_text as renderer_print_formatted_text,
)
from prompt_toolkit.styles import (
    BaseStyle,
    StyleTransformation,
    default_pygments_style,
    default_ui_style,
    merge_styles,
)

if TYPE_CHECKING:
    from prompt_toolkit.layout.containers import AnyContainer

__all__ = [
    "print_formatted_text",
    "print_container",
    "clear",
    "set_title",
    "clear_title",
]


def print_formatted_text(
    *values: Any,
    sep: str = " ",
    end: str = "\n",
    file: TextIO | None = None,
    flush: bool = False,
    style: BaseStyle | None = None,
    output: Output | None = None,
    color_depth: ColorDepth | None = None,
    style_transformation: StyleTransformation | None = None,
    include_default_pygments_style: bool = True,
) -> None:
    """
    ::

        print_formatted_text(*values, sep=' ', end='\\n', file=None, flush=False, style=None, output=None)

    Print text to stdout. This is supposed to be compatible with Python's print
    function, but supports printing of formatted text. You can pass a
    :class:`~prompt_toolkit.formatted_text.FormattedText`,
    :class:`~prompt_toolkit.formatted_text.HTML` or
    :class:`~prompt_toolkit.formatted_text.ANSI` object to print formatted
    text.

    * Print HTML as follows::

        print_formatted_text(HTML('<i>Some italic text</i> <ansired>This is red!</ansired>'))

        style = Style.from_dict({
            'hello': '#ff0066',
            'world': '#884444 italic',
        })
        print_formatted_text(HTML('<hello>Hello</hello> <world>world</world>!'), style=style)

    * Print a list of (style_str, text) tuples in the given style to the
      output.  E.g.::

        style = Style.from_dict({
            'hello': '#ff0066',
            'world': '#884444 italic',
        })
        fragments = FormattedText([
            ('class:hello', 'Hello'),
            ('class:world', 'World'),
        ])
        print_formatted_text(fragments, style=style)

    If you want to print a list of Pygments tokens, wrap it in
    :class:`~prompt_toolkit.formatted_text.PygmentsTokens` to do the
    conversion.

    If a prompt_toolkit `Application` is currently running, this will always
    print above the application or prompt (similar to `patch_stdout`). So,
    `print_formatted_text` will erase the current application, print the text,
    and render the application again.

    :param values: Any kind of printable object, or formatted string.
    :param sep: String inserted between values, default a space.
    :param end: String appended after the last value, default a newline.
    :param style: :class:`.Style` instance for the color scheme.
    :param include_default_pygments_style: `bool`. Include the default Pygments
        style when set to `True` (the default).
    """
    assert not (output and file)

    # Create Output object.
    if output is None:
        if file:
            output = create_output(stdout=file)
        else:
            output = get_app_session().output

    assert isinstance(output, Output)

    # Get color depth.
    color_depth = color_depth or output.get_default_color_depth()

    # Merges values.
    def to_text(val: Any) -> StyleAndTextTuples:
        # Normal lists which are not instances of `FormattedText` are
        # considered plain text.
        if isinstance(val, list) and not isinstance(val, FormattedText):
            return to_formatted_text(f"{val}")
        return to_formatted_text(val, auto_convert=True)

    fragments = []
    for i, value in enumerate(values):
        fragments.extend(to_text(value))

        if sep and i != len(values) - 1:
            fragments.extend(to_text(sep))

    fragments.extend(to_text(end))

    # Print output.
    def render() -> None:
        assert isinstance(output, Output)

        renderer_print_formatted_text(
            output,
            fragments,
            _create_merged_style(
                style, include_default_pygments_style=include_default_pygments_style
            ),
            color_depth=color_depth,
            style_transformation=style_transformation,
        )

        # Flush the output stream.
        if flush:
            output.flush()

    # If an application is running, print above the app. This does not require
    # `patch_stdout`.
    loop: AbstractEventLoop | None = None

    app = get_app_or_none()
    if app is not None:
        loop = app.loop

    if loop is not None:
        loop.call_soon_threadsafe(lambda: run_in_terminal(render))
    else:
        render()


def print_container(
    container: AnyContainer,
    file: TextIO | None = None,
    style: BaseStyle | None = None,
    include_default_pygments_style: bool = True,
) -> None:
    """
    Print any layout to the output in a non-interactive way.

    Example usage::

        from prompt_toolkit.widgets import Frame, TextArea
        print_container(
            Frame(TextArea(text='Hello world!')))
    """
    if file:
        output = create_output(stdout=file)
    else:
        output = get_app_session().output

    app: Application[None] = Application(
        layout=Layout(container=container),
        output=output,
        # `DummyInput` will cause the application to terminate immediately.
        input=DummyInput(),
        style=_create_merged_style(
            style, include_default_pygments_style=include_default_pygments_style
        ),
    )
    try:
        app.run(in_thread=True)
    except EOFError:
        pass


def _create_merged_style(
    style: BaseStyle | None, include_default_pygments_style: bool
) -> BaseStyle:
    """
    Merge user defined style with built-in style.
    """
    styles = [default_ui_style()]
    if include_default_pygments_style:
        styles.append(default_pygments_style())
    if style:
        styles.append(style)

    return merge_styles(styles)


def clear() -> None:
    """
    Clear the screen.
    """
    output = get_app_session().output
    output.erase_screen()
    output.cursor_goto(0, 0)
    output.flush()


def set_title(text: str) -> None:
    """
    Set the terminal title.
    """
    output = get_app_session().output
    output.set_title(text)


def clear_title() -> None:
    """
    Erase the current title.
    """
    set_title("")

# === NexusCore/openenv\Lib\site-packages\win32com\server\dispatcher.py ===
"""Dispatcher

Please see policy.py for a discussion on dispatchers and policies
"""

from __future__ import annotations

import traceback
from typing import NoReturn

import pythoncom
import win32api
import win32com
from win32com.server.exception import IsCOMServerException
from win32com.util import IIDToInterfaceName


class DispatcherBase:
    """The base class for all Dispatchers.

    This dispatcher supports wrapping all operations in exception handlers,
    and all the necessary delegation to the policy.

    This base class supports the printing of "unexpected" exceptions.  Note, however,
    that exactly where the output of print goes may not be useful!  A derived class may
    provide additional semantics for this.
    """

    def __init__(self, policyClass, object):
        self.policy = policyClass(object)
        # The logger we should dump to.  If None, we should send to the
        # default location (typically 'print')
        self.logger = getattr(win32com, "logger", None)

    def _CreateInstance_(self, clsid, reqIID):
        try:
            self.policy._CreateInstance_(clsid, reqIID)
            return pythoncom.WrapObject(self, reqIID)
        except:
            self._HandleException_()

    def _QueryInterface_(self, iid):
        try:
            return self.policy._QueryInterface_(iid)
        except:
            self._HandleException_()

    def _Invoke_(self, dispid, lcid, wFlags, args):
        try:
            return self.policy._Invoke_(dispid, lcid, wFlags, args)
        except:
            self._HandleException_()

    def _GetIDsOfNames_(self, names, lcid):
        try:
            return self.policy._GetIDsOfNames_(names, lcid)
        except:
            self._HandleException_()

    def _GetTypeInfo_(self, index, lcid):
        try:
            return self.policy._GetTypeInfo_(index, lcid)
        except:
            self._HandleException_()

    def _GetTypeInfoCount_(self):
        try:
            return self.policy._GetTypeInfoCount_()
        except:
            self._HandleException_()

    def _GetDispID_(self, name, fdex):
        try:
            return self.policy._GetDispID_(name, fdex)
        except:
            self._HandleException_()

    def _InvokeEx_(self, dispid, lcid, wFlags, args, kwargs, serviceProvider):
        try:
            return self.policy._InvokeEx_(
                dispid, lcid, wFlags, args, kwargs, serviceProvider
            )
        except:
            self._HandleException_()

    def _DeleteMemberByName_(self, name, fdex):
        try:
            return self.policy._DeleteMemberByName_(name, fdex)
        except:
            self._HandleException_()

    def _DeleteMemberByDispID_(self, id):
        try:
            return self.policy._DeleteMemberByDispID_(id)
        except:
            self._HandleException_()

    def _GetMemberProperties_(self, id, fdex):
        try:
            return self.policy._GetMemberProperties_(id, fdex)
        except:
            self._HandleException_()

    def _GetMemberName_(self, dispid):
        try:
            return self.policy._GetMemberName_(dispid)
        except:
            self._HandleException_()

    def _GetNextDispID_(self, fdex, flags):
        try:
            return self.policy._GetNextDispID_(fdex, flags)
        except:
            self._HandleException_()

    def _GetNameSpaceParent_(self):
        try:
            return self.policy._GetNameSpaceParent_()
        except:
            self._HandleException_()

    def _HandleException_(self) -> NoReturn:
        """Called whenever an exception is raised.

        Default behaviour is to print the exception.
        """
        # If not a COM exception, print it for the developer.
        if not IsCOMServerException():
            if self.logger is not None:
                self.logger.exception("pythoncom server error")
            else:
                traceback.print_exc()
        # But still raise it for the framework.
        raise

    def _trace_(self, *args):
        if self.logger is not None:
            record = " ".join(map(str, args))
            self.logger.debug(record)
        else:
            for arg in args[:-1]:
                print(arg, end=" ")
            print(args[-1])


class DispatcherTrace(DispatcherBase):
    """A dispatcher, which causes a 'print' line for each COM function called."""

    def _QueryInterface_(self, iid):
        rc = DispatcherBase._QueryInterface_(self, iid)
        if not rc:
            self._trace_(
                "in {!r}._QueryInterface_ with unsupported IID {} ({})".format(
                    self.policy._obj_, IIDToInterfaceName(iid), iid
                )
            )
        return rc

    def _GetIDsOfNames_(self, names, lcid):
        self._trace_("in _GetIDsOfNames_ with '%s' and '%d'\n" % (names, lcid))
        return DispatcherBase._GetIDsOfNames_(self, names, lcid)

    def _GetTypeInfo_(self, index, lcid):
        self._trace_("in _GetTypeInfo_ with index=%d, lcid=%d\n" % (index, lcid))
        return DispatcherBase._GetTypeInfo_(self, index, lcid)

    def _GetTypeInfoCount_(self):
        self._trace_("in _GetTypeInfoCount_\n")
        return DispatcherBase._GetTypeInfoCount_(self)

    def _Invoke_(self, dispid, lcid, wFlags, args):
        self._trace_("in _Invoke_ with", dispid, lcid, wFlags, args)
        return DispatcherBase._Invoke_(self, dispid, lcid, wFlags, args)

    def _GetDispID_(self, name, fdex):
        self._trace_("in _GetDispID_ with", name, fdex)
        return DispatcherBase._GetDispID_(self, name, fdex)

    def _InvokeEx_(self, dispid, lcid, wFlags, args, kwargs, serviceProvider):
        self._trace_(
            "in {!r}._InvokeEx_-{}{!r} [{:x},{},{!r}]".format(
                self.policy._obj_, dispid, args, wFlags, lcid, serviceProvider
            )
        )
        return DispatcherBase._InvokeEx_(
            self, dispid, lcid, wFlags, args, kwargs, serviceProvider
        )

    def _DeleteMemberByName_(self, name, fdex):
        self._trace_("in _DeleteMemberByName_ with", name, fdex)
        return DispatcherBase._DeleteMemberByName_(self, name, fdex)

    def _DeleteMemberByDispID_(self, id):
        self._trace_("in _DeleteMemberByDispID_ with", id)
        return DispatcherBase._DeleteMemberByDispID_(self, id)

    def _GetMemberProperties_(self, id, fdex):
        self._trace_("in _GetMemberProperties_ with", id, fdex)
        return DispatcherBase._GetMemberProperties_(self, id, fdex)

    def _GetMemberName_(self, dispid):
        self._trace_("in _GetMemberName_ with", dispid)
        return DispatcherBase._GetMemberName_(self, dispid)

    def _GetNextDispID_(self, fdex, flags):
        self._trace_("in _GetNextDispID_ with", fdex, flags)
        return DispatcherBase._GetNextDispID_(self, fdex, flags)

    def _GetNameSpaceParent_(self):
        self._trace_("in _GetNameSpaceParent_")
        return DispatcherBase._GetNameSpaceParent_(self)


class DispatcherWin32trace(DispatcherTrace):
    """A tracing dispatcher that sends its output to the win32trace remote collector."""

    def __init__(self, policyClass, object):
        DispatcherTrace.__init__(self, policyClass, object)
        if self.logger is None:
            # If we have no logger, setup our output.
            import win32traceutil  # Sets up everything.
        self._trace_(f"Object with win32trace dispatcher created (object={object!r})")


class DispatcherOutputDebugString(DispatcherTrace):
    """A tracing dispatcher that sends its output to win32api.OutputDebugString"""

    def _trace_(self, *args):
        for arg in args[:-1]:
            win32api.OutputDebugString(str(arg) + " ")
        win32api.OutputDebugString(str(args[-1]) + "\n")


try:
    import win32trace  # nopycln: import # Check for win32traceutil w/o importing it

    DefaultDebugDispatcher: type[DispatcherTrace] = DispatcherWin32trace
except ImportError:  # no win32trace module - just use a print based one.
    DefaultDebugDispatcher = DispatcherTrace

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\plot.py ===
"""Visualize DesignSpaceDocument and resulting VariationModel."""

from fontTools.varLib.models import VariationModel, supportScalar
from fontTools.designspaceLib import DesignSpaceDocument
from matplotlib import pyplot
from mpl_toolkits.mplot3d import axes3d
from itertools import cycle
import math
import logging
import sys

log = logging.getLogger(__name__)


def stops(support, count=10):
    a, b, c = support

    return (
        [a + (b - a) * i / count for i in range(count)]
        + [b + (c - b) * i / count for i in range(count)]
        + [c]
    )


def _plotLocationsDots(locations, axes, subplot, **kwargs):
    for loc, color in zip(locations, cycle(pyplot.cm.Set1.colors)):
        if len(axes) == 1:
            subplot.plot([loc.get(axes[0], 0)], [1.0], "o", color=color, **kwargs)
        elif len(axes) == 2:
            subplot.plot(
                [loc.get(axes[0], 0)],
                [loc.get(axes[1], 0)],
                [1.0],
                "o",
                color=color,
                **kwargs,
            )
        else:
            raise AssertionError(len(axes))


def plotLocations(locations, fig, names=None, **kwargs):
    n = len(locations)
    cols = math.ceil(n**0.5)
    rows = math.ceil(n / cols)

    if names is None:
        names = [None] * len(locations)

    model = VariationModel(locations)
    names = [names[model.reverseMapping[i]] for i in range(len(names))]

    axes = sorted(locations[0].keys())
    if len(axes) == 1:
        _plotLocations2D(model, axes[0], fig, cols, rows, names=names, **kwargs)
    elif len(axes) == 2:
        _plotLocations3D(model, axes, fig, cols, rows, names=names, **kwargs)
    else:
        raise ValueError("Only 1 or 2 axes are supported")


def _plotLocations2D(model, axis, fig, cols, rows, names, **kwargs):
    subplot = fig.add_subplot(111)
    for i, (support, color, name) in enumerate(
        zip(model.supports, cycle(pyplot.cm.Set1.colors), cycle(names))
    ):
        if name is not None:
            subplot.set_title(name)
        subplot.set_xlabel(axis)
        pyplot.xlim(-1.0, +1.0)

        Xs = support.get(axis, (-1.0, 0.0, +1.0))
        X, Y = [], []
        for x in stops(Xs):
            y = supportScalar({axis: x}, support)
            X.append(x)
            Y.append(y)
        subplot.plot(X, Y, color=color, **kwargs)

        _plotLocationsDots(model.locations, [axis], subplot)


def _plotLocations3D(model, axes, fig, rows, cols, names, **kwargs):
    ax1, ax2 = axes

    axis3D = fig.add_subplot(111, projection="3d")
    for i, (support, color, name) in enumerate(
        zip(model.supports, cycle(pyplot.cm.Set1.colors), cycle(names))
    ):
        if name is not None:
            axis3D.set_title(name)
        axis3D.set_xlabel(ax1)
        axis3D.set_ylabel(ax2)
        pyplot.xlim(-1.0, +1.0)
        pyplot.ylim(-1.0, +1.0)

        Xs = support.get(ax1, (-1.0, 0.0, +1.0))
        Ys = support.get(ax2, (-1.0, 0.0, +1.0))
        for x in stops(Xs):
            X, Y, Z = [], [], []
            for y in Ys:
                z = supportScalar({ax1: x, ax2: y}, support)
                X.append(x)
                Y.append(y)
                Z.append(z)
            axis3D.plot(X, Y, Z, color=color, **kwargs)
        for y in stops(Ys):
            X, Y, Z = [], [], []
            for x in Xs:
                z = supportScalar({ax1: x, ax2: y}, support)
                X.append(x)
                Y.append(y)
                Z.append(z)
            axis3D.plot(X, Y, Z, color=color, **kwargs)

        _plotLocationsDots(model.locations, [ax1, ax2], axis3D)


def plotDocument(doc, fig, **kwargs):
    doc.normalize()
    locations = [s.location for s in doc.sources]
    names = [s.name for s in doc.sources]
    plotLocations(locations, fig, names, **kwargs)


def _plotModelFromMasters2D(model, masterValues, fig, **kwargs):
    assert len(model.axisOrder) == 1
    axis = model.axisOrder[0]

    axis_min = min(loc.get(axis, 0) for loc in model.locations)
    axis_max = max(loc.get(axis, 0) for loc in model.locations)

    import numpy as np

    X = np.arange(axis_min, axis_max, (axis_max - axis_min) / 100)
    Y = []

    for x in X:
        loc = {axis: x}
        v = model.interpolateFromMasters(loc, masterValues)
        Y.append(v)

    subplot = fig.add_subplot(111)
    subplot.plot(X, Y, "-", **kwargs)


def _plotModelFromMasters3D(model, masterValues, fig, **kwargs):
    assert len(model.axisOrder) == 2
    axis1, axis2 = model.axisOrder[0], model.axisOrder[1]

    axis1_min = min(loc.get(axis1, 0) for loc in model.locations)
    axis1_max = max(loc.get(axis1, 0) for loc in model.locations)
    axis2_min = min(loc.get(axis2, 0) for loc in model.locations)
    axis2_max = max(loc.get(axis2, 0) for loc in model.locations)

    import numpy as np

    X = np.arange(axis1_min, axis1_max, (axis1_max - axis1_min) / 100)
    Y = np.arange(axis2_min, axis2_max, (axis2_max - axis2_min) / 100)
    X, Y = np.meshgrid(X, Y)
    Z = []

    for row_x, row_y in zip(X, Y):
        z_row = []
        Z.append(z_row)
        for x, y in zip(row_x, row_y):
            loc = {axis1: x, axis2: y}
            v = model.interpolateFromMasters(loc, masterValues)
            z_row.append(v)
    Z = np.array(Z)

    axis3D = fig.add_subplot(111, projection="3d")
    axis3D.plot_surface(X, Y, Z, **kwargs)


def plotModelFromMasters(model, masterValues, fig, **kwargs):
    """Plot a variation model and set of master values corresponding
    to the locations to the model into a pyplot figure.  Variation
    model must have axisOrder of size 1 or 2."""
    if len(model.axisOrder) == 1:
        _plotModelFromMasters2D(model, masterValues, fig, **kwargs)
    elif len(model.axisOrder) == 2:
        _plotModelFromMasters3D(model, masterValues, fig, **kwargs)
    else:
        raise ValueError("Only 1 or 2 axes are supported")


def main(args=None):
    from fontTools import configLogger

    if args is None:
        args = sys.argv[1:]

    # configure the library logger (for >= WARNING)
    configLogger()
    # comment this out to enable debug messages from logger
    # log.setLevel(logging.DEBUG)

    if len(args) < 1:
        print("usage: fonttools varLib.plot source.designspace", file=sys.stderr)
        print("  or")
        print("usage: fonttools varLib.plot location1 location2 ...", file=sys.stderr)
        print("  or")
        print(
            "usage: fonttools varLib.plot location1=value1 location2=value2 ...",
            file=sys.stderr,
        )
        sys.exit(1)

    fig = pyplot.figure()
    fig.set_tight_layout(True)

    if len(args) == 1 and args[0].endswith(".designspace"):
        doc = DesignSpaceDocument()
        doc.read(args[0])
        plotDocument(doc, fig)
    else:
        axes = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
        if "=" not in args[0]:
            locs = [dict(zip(axes, (float(v) for v in s.split(",")))) for s in args]
            plotLocations(locs, fig)
        else:
            locations = []
            masterValues = []
            for arg in args:
                loc, v = arg.split("=")
                locations.append(dict(zip(axes, (float(v) for v in loc.split(",")))))
                masterValues.append(float(v))
            model = VariationModel(locations, axes[: len(locations[0])])
            plotModelFromMasters(model, masterValues, fig)

    pyplot.show()


if __name__ == "__main__":
    import sys

    sys.exit(main())

# === NexusCore/openenv\Lib\site-packages\nltk\lm\api.py ===
# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2024 NLTK Project
# Authors: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Language Model Interface."""

import random
import warnings
from abc import ABCMeta, abstractmethod
from bisect import bisect
from itertools import accumulate

from nltk.lm.counter import NgramCounter
from nltk.lm.util import log_base2
from nltk.lm.vocabulary import Vocabulary


class Smoothing(metaclass=ABCMeta):
    """Ngram Smoothing Interface

    Implements Chen & Goodman 1995's idea that all smoothing algorithms have
    certain features in common. This should ideally allow smoothing algorithms to
    work both with Backoff and Interpolation.
    """

    def __init__(self, vocabulary, counter):
        """
        :param vocabulary: The Ngram vocabulary object.
        :type vocabulary: nltk.lm.vocab.Vocabulary
        :param counter: The counts of the vocabulary items.
        :type counter: nltk.lm.counter.NgramCounter
        """
        self.vocab = vocabulary
        self.counts = counter

    @abstractmethod
    def unigram_score(self, word):
        raise NotImplementedError()

    @abstractmethod
    def alpha_gamma(self, word, context):
        raise NotImplementedError()


def _mean(items):
    """Return average (aka mean) for sequence of items."""
    return sum(items) / len(items)


def _random_generator(seed_or_generator):
    if isinstance(seed_or_generator, random.Random):
        return seed_or_generator
    return random.Random(seed_or_generator)


def _weighted_choice(population, weights, random_generator=None):
    """Like random.choice, but with weights.

    Heavily inspired by python 3.6 `random.choices`.
    """
    if not population:
        raise ValueError("Can't choose from empty population")
    if len(population) != len(weights):
        raise ValueError("The number of weights does not match the population")
    cum_weights = list(accumulate(weights))
    total = cum_weights[-1]
    threshold = random_generator.random()
    return population[bisect(cum_weights, total * threshold)]


class LanguageModel(metaclass=ABCMeta):
    """ABC for Language Models.

    Cannot be directly instantiated itself.

    """

    def __init__(self, order, vocabulary=None, counter=None):
        """Creates new LanguageModel.

        :param vocabulary: If provided, this vocabulary will be used instead
            of creating a new one when training.
        :type vocabulary: `nltk.lm.Vocabulary` or None
        :param counter: If provided, use this object to count ngrams.
        :type counter: `nltk.lm.NgramCounter` or None
        :param ngrams_fn: If given, defines how sentences in training text are turned to ngram
            sequences.
        :type ngrams_fn: function or None
        :param pad_fn: If given, defines how sentences in training text are padded.
        :type pad_fn: function or None
        """
        self.order = order
        if vocabulary and not isinstance(vocabulary, Vocabulary):
            warnings.warn(
                f"The `vocabulary` argument passed to {self.__class__.__name__!r} "
                "must be an instance of `nltk.lm.Vocabulary`.",
                stacklevel=3,
            )
        self.vocab = Vocabulary() if vocabulary is None else vocabulary
        self.counts = NgramCounter() if counter is None else counter

    def fit(self, text, vocabulary_text=None):
        """Trains the model on a text.

        :param text: Training text as a sequence of sentences.

        """
        if not self.vocab:
            if vocabulary_text is None:
                raise ValueError(
                    "Cannot fit without a vocabulary or text to create it from."
                )
            self.vocab.update(vocabulary_text)
        self.counts.update(self.vocab.lookup(sent) for sent in text)

    def score(self, word, context=None):
        """Masks out of vocab (OOV) words and computes their model score.

        For model-specific logic of calculating scores, see the `unmasked_score`
        method.
        """
        return self.unmasked_score(
            self.vocab.lookup(word), self.vocab.lookup(context) if context else None
        )

    @abstractmethod
    def unmasked_score(self, word, context=None):
        """Score a word given some optional context.

        Concrete models are expected to provide an implementation.
        Note that this method does not mask its arguments with the OOV label.
        Use the `score` method for that.

        :param str word: Word for which we want the score
        :param tuple(str) context: Context the word is in.
            If `None`, compute unigram score.
        :param context: tuple(str) or None
        :rtype: float
        """
        raise NotImplementedError()

    def logscore(self, word, context=None):
        """Evaluate the log score of this word in this context.

        The arguments are the same as for `score` and `unmasked_score`.

        """
        return log_base2(self.score(word, context))

    def context_counts(self, context):
        """Helper method for retrieving counts for a given context.

        Assumes context has been checked and oov words in it masked.
        :type context: tuple(str) or None

        """
        return (
            self.counts[len(context) + 1][context] if context else self.counts.unigrams
        )

    def entropy(self, text_ngrams):
        """Calculate cross-entropy of model for given evaluation text.

        This implementation is based on the Shannon-McMillan-Breiman theorem,
        as used and referenced by Dan Jurafsky and Jordan Boyd-Graber.

        :param Iterable(tuple(str)) text_ngrams: A sequence of ngram tuples.
        :rtype: float

        """
        return -1 * _mean(
            [self.logscore(ngram[-1], ngram[:-1]) for ngram in text_ngrams]
        )

    def perplexity(self, text_ngrams):
        """Calculates the perplexity of the given text.

        This is simply 2 ** cross-entropy for the text, so the arguments are the same.

        """
        return pow(2.0, self.entropy(text_ngrams))

    def generate(self, num_words=1, text_seed=None, random_seed=None):
        """Generate words from the model.

        :param int num_words: How many words to generate. By default 1.
        :param text_seed: Generation can be conditioned on preceding context.
        :param random_seed: A random seed or an instance of `random.Random`. If provided,
            makes the random sampling part of generation reproducible.
        :return: One (str) word or a list of words generated from model.

        Examples:

        >>> from nltk.lm import MLE
        >>> lm = MLE(2)
        >>> lm.fit([[("a", "b"), ("b", "c")]], vocabulary_text=['a', 'b', 'c'])
        >>> lm.fit([[("a",), ("b",), ("c",)]])
        >>> lm.generate(random_seed=3)
        'a'
        >>> lm.generate(text_seed=['a'])
        'b'

        """
        text_seed = [] if text_seed is None else list(text_seed)
        random_generator = _random_generator(random_seed)
        # This is the base recursion case.
        if num_words == 1:
            context = (
                text_seed[-self.order + 1 :]
                if len(text_seed) >= self.order
                else text_seed
            )
            samples = self.context_counts(self.vocab.lookup(context))
            while context and not samples:
                context = context[1:] if len(context) > 1 else []
                samples = self.context_counts(self.vocab.lookup(context))
            # Sorting samples achieves two things:
            # - reproducible randomness when sampling
            # - turns Mapping into Sequence which `_weighted_choice` expects
            samples = sorted(samples)
            return _weighted_choice(
                samples,
                tuple(self.score(w, context) for w in samples),
                random_generator,
            )
        # We build up text one word at a time using the preceding context.
        generated = []
        for _ in range(num_words):
            generated.append(
                self.generate(
                    num_words=1,
                    text_seed=text_seed + generated,
                    random_seed=random_generator,
                )
            )
        return generated

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_dataclasses.py ===
"""Private logic for creating pydantic dataclasses."""

from __future__ import annotations as _annotations

import dataclasses
import typing
import warnings
from functools import partial, wraps
from typing import Any, ClassVar

from pydantic_core import (
    ArgsKwargs,
    SchemaSerializer,
    SchemaValidator,
    core_schema,
)
from typing_extensions import TypeGuard

from ..errors import PydanticUndefinedAnnotation
from ..plugin._schema_validator import PluggableSchemaValidator, create_schema_validator
from ..warnings import PydanticDeprecatedSince20
from . import _config, _decorators
from ._fields import collect_dataclass_fields
from ._generate_schema import GenerateSchema, InvalidSchemaError
from ._generics import get_standard_typevars_map
from ._mock_val_ser import set_dataclass_mocks
from ._namespace_utils import NsResolver
from ._signature import generate_pydantic_signature
from ._utils import LazyClassAttribute

if typing.TYPE_CHECKING:
    from _typeshed import DataclassInstance as StandardDataclass

    from ..config import ConfigDict
    from ..fields import FieldInfo

    class PydanticDataclass(StandardDataclass, typing.Protocol):
        """A protocol containing attributes only available once a class has been decorated as a Pydantic dataclass.

        Attributes:
            __pydantic_config__: Pydantic-specific configuration settings for the dataclass.
            __pydantic_complete__: Whether dataclass building is completed, or if there are still undefined fields.
            __pydantic_core_schema__: The pydantic-core schema used to build the SchemaValidator and SchemaSerializer.
            __pydantic_decorators__: Metadata containing the decorators defined on the dataclass.
            __pydantic_fields__: Metadata about the fields defined on the dataclass.
            __pydantic_serializer__: The pydantic-core SchemaSerializer used to dump instances of the dataclass.
            __pydantic_validator__: The pydantic-core SchemaValidator used to validate instances of the dataclass.
        """

        __pydantic_config__: ClassVar[ConfigDict]
        __pydantic_complete__: ClassVar[bool]
        __pydantic_core_schema__: ClassVar[core_schema.CoreSchema]
        __pydantic_decorators__: ClassVar[_decorators.DecoratorInfos]
        __pydantic_fields__: ClassVar[dict[str, FieldInfo]]
        __pydantic_serializer__: ClassVar[SchemaSerializer]
        __pydantic_validator__: ClassVar[SchemaValidator | PluggableSchemaValidator]

        @classmethod
        def __pydantic_fields_complete__(cls) -> bool: ...

else:
    # See PyCharm issues https://youtrack.jetbrains.com/issue/PY-21915
    # and https://youtrack.jetbrains.com/issue/PY-51428
    DeprecationWarning = PydanticDeprecatedSince20


def set_dataclass_fields(
    cls: type[StandardDataclass],
    ns_resolver: NsResolver | None = None,
    config_wrapper: _config.ConfigWrapper | None = None,
) -> None:
    """Collect and set `cls.__pydantic_fields__`.

    Args:
        cls: The class.
        ns_resolver: Namespace resolver to use when getting dataclass annotations.
        config_wrapper: The config wrapper instance, defaults to `None`.
    """
    typevars_map = get_standard_typevars_map(cls)
    fields = collect_dataclass_fields(
        cls, ns_resolver=ns_resolver, typevars_map=typevars_map, config_wrapper=config_wrapper
    )

    cls.__pydantic_fields__ = fields  # type: ignore


def complete_dataclass(
    cls: type[Any],
    config_wrapper: _config.ConfigWrapper,
    *,
    raise_errors: bool = True,
    ns_resolver: NsResolver | None = None,
    _force_build: bool = False,
) -> bool:
    """Finish building a pydantic dataclass.

    This logic is called on a class which has already been wrapped in `dataclasses.dataclass()`.

    This is somewhat analogous to `pydantic._internal._model_construction.complete_model_class`.

    Args:
        cls: The class.
        config_wrapper: The config wrapper instance.
        raise_errors: Whether to raise errors, defaults to `True`.
        ns_resolver: The namespace resolver instance to use when collecting dataclass fields
            and during schema building.
        _force_build: Whether to force building the dataclass, no matter if
            [`defer_build`][pydantic.config.ConfigDict.defer_build] is set.

    Returns:
        `True` if building a pydantic dataclass is successfully completed, `False` otherwise.

    Raises:
        PydanticUndefinedAnnotation: If `raise_error` is `True` and there is an undefined annotations.
    """
    original_init = cls.__init__

    # dataclass.__init__ must be defined here so its `__qualname__` can be changed since functions can't be copied,
    # and so that the mock validator is used if building was deferred:
    def __init__(__dataclass_self__: PydanticDataclass, *args: Any, **kwargs: Any) -> None:
        __tracebackhide__ = True
        s = __dataclass_self__
        s.__pydantic_validator__.validate_python(ArgsKwargs(args, kwargs), self_instance=s)

    __init__.__qualname__ = f'{cls.__qualname__}.__init__'

    cls.__init__ = __init__  # type: ignore
    cls.__pydantic_config__ = config_wrapper.config_dict  # type: ignore

    set_dataclass_fields(cls, ns_resolver, config_wrapper=config_wrapper)

    if not _force_build and config_wrapper.defer_build:
        set_dataclass_mocks(cls)
        return False

    if hasattr(cls, '__post_init_post_parse__'):
        warnings.warn(
            'Support for `__post_init_post_parse__` has been dropped, the method will not be called', DeprecationWarning
        )

    typevars_map = get_standard_typevars_map(cls)
    gen_schema = GenerateSchema(
        config_wrapper,
        ns_resolver=ns_resolver,
        typevars_map=typevars_map,
    )

    # set __signature__ attr only for the class, but not for its instances
    # (because instances can define `__call__`, and `inspect.signature` shouldn't
    # use the `__signature__` attribute and instead generate from `__call__`).
    cls.__signature__ = LazyClassAttribute(
        '__signature__',
        partial(
            generate_pydantic_signature,
            # It's important that we reference the `original_init` here,
            # as it is the one synthesized by the stdlib `dataclass` module:
            init=original_init,
            fields=cls.__pydantic_fields__,  # type: ignore
            validate_by_name=config_wrapper.validate_by_name,
            extra=config_wrapper.extra,
            is_dataclass=True,
        ),
    )

    try:
        schema = gen_schema.generate_schema(cls)
    except PydanticUndefinedAnnotation as e:
        if raise_errors:
            raise
        set_dataclass_mocks(cls, f'`{e.name}`')
        return False

    core_config = config_wrapper.core_config(title=cls.__name__)

    try:
        schema = gen_schema.clean_schema(schema)
    except InvalidSchemaError:
        set_dataclass_mocks(cls)
        return False

    # We are about to set all the remaining required properties expected for this cast;
    # __pydantic_decorators__ and __pydantic_fields__ should already be set
    cls = typing.cast('type[PydanticDataclass]', cls)
    # debug(schema)

    cls.__pydantic_core_schema__ = schema
    cls.__pydantic_validator__ = validator = create_schema_validator(
        schema, cls, cls.__module__, cls.__qualname__, 'dataclass', core_config, config_wrapper.plugin_settings
    )
    cls.__pydantic_serializer__ = SchemaSerializer(schema, core_config)

    if config_wrapper.validate_assignment:

        @wraps(cls.__setattr__)
        def validated_setattr(instance: Any, field: str, value: str, /) -> None:
            validator.validate_assignment(instance, field, value)

        cls.__setattr__ = validated_setattr.__get__(None, cls)  # type: ignore

    cls.__pydantic_complete__ = True
    return True


def is_builtin_dataclass(_cls: type[Any]) -> TypeGuard[type[StandardDataclass]]:
    """Returns True if a class is a stdlib dataclass and *not* a pydantic dataclass.

    We check that
    - `_cls` is a dataclass
    - `_cls` does not inherit from a processed pydantic dataclass (and thus have a `__pydantic_validator__`)
    - `_cls` does not have any annotations that are not dataclass fields
    e.g.
    ```python
    import dataclasses

    import pydantic.dataclasses

    @dataclasses.dataclass
    class A:
        x: int

    @pydantic.dataclasses.dataclass
    class B(A):
        y: int
    ```
    In this case, when we first check `B`, we make an extra check and look at the annotations ('y'),
    which won't be a superset of all the dataclass fields (only the stdlib fields i.e. 'x')

    Args:
        cls: The class.

    Returns:
        `True` if the class is a stdlib dataclass, `False` otherwise.
    """
    return (
        dataclasses.is_dataclass(_cls)
        and not hasattr(_cls, '__pydantic_validator__')
        and set(_cls.__dataclass_fields__).issuperset(set(getattr(_cls, '__annotations__', {})))
    )

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\command\install_lib.py ===
"""distutils.command.install_lib

Implements the Distutils 'install_lib' command
(install all Python modules)."""

from __future__ import annotations

import importlib.util
import os
import sys
from typing import Any, ClassVar

from ..core import Command
from ..errors import DistutilsOptionError

# Extension for Python source files.
PYTHON_SOURCE_EXTENSION = ".py"


class install_lib(Command):
    description = "install all Python modules (extensions and pure Python)"

    # The byte-compilation options are a tad confusing.  Here are the
    # possible scenarios:
    #   1) no compilation at all (--no-compile --no-optimize)
    #   2) compile .pyc only (--compile --no-optimize; default)
    #   3) compile .pyc and "opt-1" .pyc (--compile --optimize)
    #   4) compile "opt-1" .pyc only (--no-compile --optimize)
    #   5) compile .pyc and "opt-2" .pyc (--compile --optimize-more)
    #   6) compile "opt-2" .pyc only (--no-compile --optimize-more)
    #
    # The UI for this is two options, 'compile' and 'optimize'.
    # 'compile' is strictly boolean, and only decides whether to
    # generate .pyc files.  'optimize' is three-way (0, 1, or 2), and
    # decides both whether to generate .pyc files and what level of
    # optimization to use.

    user_options = [
        ('install-dir=', 'd', "directory to install to"),
        ('build-dir=', 'b', "build directory (where to install from)"),
        ('force', 'f', "force installation (overwrite existing files)"),
        ('compile', 'c', "compile .py to .pyc [default]"),
        ('no-compile', None, "don't compile .py files"),
        (
            'optimize=',
            'O',
            "also compile with optimization: -O1 for \"python -O\", "
            "-O2 for \"python -OO\", and -O0 to disable [default: -O0]",
        ),
        ('skip-build', None, "skip the build steps"),
    ]

    boolean_options: ClassVar[list[str]] = ['force', 'compile', 'skip-build']
    negative_opt: ClassVar[dict[str, str]] = {'no-compile': 'compile'}

    def initialize_options(self):
        # let the 'install' command dictate our installation directory
        self.install_dir = None
        self.build_dir = None
        self.force = False
        self.compile = None
        self.optimize = None
        self.skip_build = None

    def finalize_options(self) -> None:
        # Get all the information we need to install pure Python modules
        # from the umbrella 'install' command -- build (source) directory,
        # install (target) directory, and whether to compile .py files.
        self.set_undefined_options(
            'install',
            ('build_lib', 'build_dir'),
            ('install_lib', 'install_dir'),
            ('force', 'force'),
            ('compile', 'compile'),
            ('optimize', 'optimize'),
            ('skip_build', 'skip_build'),
        )

        if self.compile is None:
            self.compile = True
        if self.optimize is None:
            self.optimize = False

        if not isinstance(self.optimize, int):
            try:
                self.optimize = int(self.optimize)
            except ValueError:
                pass
            if self.optimize not in (0, 1, 2):
                raise DistutilsOptionError("optimize must be 0, 1, or 2")

    def run(self) -> None:
        # Make sure we have built everything we need first
        self.build()

        # Install everything: simply dump the entire contents of the build
        # directory to the installation directory (that's the beauty of
        # having a build directory!)
        outfiles = self.install()

        # (Optionally) compile .py to .pyc
        if outfiles is not None and self.distribution.has_pure_modules():
            self.byte_compile(outfiles)

    # -- Top-level worker functions ------------------------------------
    # (called from 'run()')

    def build(self) -> None:
        if not self.skip_build:
            if self.distribution.has_pure_modules():
                self.run_command('build_py')
            if self.distribution.has_ext_modules():
                self.run_command('build_ext')

    # Any: https://typing.readthedocs.io/en/latest/guides/writing_stubs.html#the-any-trick
    def install(self) -> list[str] | Any:
        if os.path.isdir(self.build_dir):
            outfiles = self.copy_tree(self.build_dir, self.install_dir)
        else:
            self.warn(
                f"'{self.build_dir}' does not exist -- no Python modules to install"
            )
            return
        return outfiles

    def byte_compile(self, files) -> None:
        if sys.dont_write_bytecode:
            self.warn('byte-compiling is disabled, skipping.')
            return

        from ..util import byte_compile

        # Get the "--root" directory supplied to the "install" command,
        # and use it as a prefix to strip off the purported filename
        # encoded in bytecode files.  This is far from complete, but it
        # should at least generate usable bytecode in RPM distributions.
        install_root = self.get_finalized_command('install').root

        if self.compile:
            byte_compile(
                files,
                optimize=0,
                force=self.force,
                prefix=install_root,
                dry_run=self.dry_run,
            )
        if self.optimize > 0:
            byte_compile(
                files,
                optimize=self.optimize,
                force=self.force,
                prefix=install_root,
                verbose=self.verbose,
                dry_run=self.dry_run,
            )

    # -- Utility methods -----------------------------------------------

    def _mutate_outputs(self, has_any, build_cmd, cmd_option, output_dir):
        if not has_any:
            return []

        build_cmd = self.get_finalized_command(build_cmd)
        build_files = build_cmd.get_outputs()
        build_dir = getattr(build_cmd, cmd_option)

        prefix_len = len(build_dir) + len(os.sep)
        outputs = [os.path.join(output_dir, file[prefix_len:]) for file in build_files]

        return outputs

    def _bytecode_filenames(self, py_filenames):
        bytecode_files = []
        for py_file in py_filenames:
            # Since build_py handles package data installation, the
            # list of outputs can contain more than just .py files.
            # Make sure we only report bytecode for the .py files.
            ext = os.path.splitext(os.path.normcase(py_file))[1]
            if ext != PYTHON_SOURCE_EXTENSION:
                continue
            if self.compile:
                bytecode_files.append(
                    importlib.util.cache_from_source(py_file, optimization='')
                )
            if self.optimize > 0:
                bytecode_files.append(
                    importlib.util.cache_from_source(
                        py_file, optimization=self.optimize
                    )
                )

        return bytecode_files

    # -- External interface --------------------------------------------
    # (called by outsiders)

    def get_outputs(self):
        """Return the list of files that would be installed if this command
        were actually run.  Not affected by the "dry-run" flag or whether
        modules have actually been built yet.
        """
        pure_outputs = self._mutate_outputs(
            self.distribution.has_pure_modules(),
            'build_py',
            'build_lib',
            self.install_dir,
        )
        if self.compile:
            bytecode_outputs = self._bytecode_filenames(pure_outputs)
        else:
            bytecode_outputs = []

        ext_outputs = self._mutate_outputs(
            self.distribution.has_ext_modules(),
            'build_ext',
            'build_lib',
            self.install_dir,
        )

        return pure_outputs + bytecode_outputs + ext_outputs

    def get_inputs(self):
        """Get the list of files that are input to this command, ie. the
        files that get installed as they are named in the build tree.
        The files in this list correspond one-to-one to the output
        filenames returned by 'get_outputs()'.
        """
        inputs = []

        if self.distribution.has_pure_modules():
            build_py = self.get_finalized_command('build_py')
            inputs.extend(build_py.get_outputs())

        if self.distribution.has_ext_modules():
            build_ext = self.get_finalized_command('build_ext')
            inputs.extend(build_ext.get_outputs())

        return inputs

# === NexusCore/openenv\Lib\site-packages\win32comext\axdebug\debugger.py ===
import os
import sys

import pythoncom
from win32com.axdebug import adb, axdebug, codecontainer, documents, expressions
from win32com.axdebug.util import _wrap

currentDebugger = None


class ModuleTreeNode:
    """Helper class for building a module tree"""

    def __init__(self, module):
        modName = module.__name__
        self.moduleName = modName
        self.module = module
        self.realNode = None
        self.cont = codecontainer.SourceModuleContainer(module)

    def __repr__(self):
        return f"<ModuleTreeNode wrapping {self.module}>"

    def Attach(self, parentRealNode):
        self.realNode.Attach(parentRealNode)

    def Close(self):
        self.module = None
        self.cont = None
        self.realNode = None


def BuildModule(module, built_nodes, rootNode, create_node_fn, create_node_args):
    if module:
        keep = module.__name__
        keep = keep and (built_nodes.get(module) is None)
        if keep and hasattr(module, "__file__"):
            keep = os.path.splitext(module.__file__)[1].lower() not in [
                ".pyd",
                ".dll",
            ]
    # keep = keep and module.__name__=='__main__'
    if module and keep:
        # print("keeping", module.__name__)
        node = ModuleTreeNode(module)
        built_nodes[module] = node
        realNode = create_node_fn(*(node,) + create_node_args)
        node.realNode = realNode

        # Split into parent nodes.
        parts = module.__name__.split(".")
        if parts[-1][:8] == "__init__":
            parts = parts[:-1]
        parent = ".".join(parts[:-1])
        parentNode = rootNode
        if parent:
            parentModule = sys.modules[parent]
            BuildModule(
                parentModule, built_nodes, rootNode, create_node_fn, create_node_args
            )
            if parentModule in built_nodes:
                parentNode = built_nodes[parentModule].realNode
        node.Attach(parentNode)


def RefreshAllModules(builtItems, rootNode, create_node, create_node_args):
    for module in sys.modules.values():
        BuildModule(module, builtItems, rootNode, create_node, create_node_args)


# realNode = pdm.CreateDebugDocumentHelper(None) # DebugDocumentHelper node?
# app.CreateApplicationNode() # doc provider node.


class CodeContainerProvider(documents.CodeContainerProvider):
    def __init__(self, axdebugger):
        self.axdebugger = axdebugger
        documents.CodeContainerProvider.__init__(self)
        self.currentNumModules = len(sys.modules)
        self.nodes = {}
        self.axdebugger.RefreshAllModules(self.nodes, self)

    def FromFileName(self, fname):
        # It appears we can't add modules during a debug session!
        # if self.currentNumModules != len(sys.modules):
        #     self.axdebugger.RefreshAllModules(self.nodes, self)
        #     self.currentNumModules = len(sys.modules)
        # for key in self.ccsAndNodes:
        #     print("File:", key)
        return documents.CodeContainerProvider.FromFileName(self, fname)

    def Close(self):
        documents.CodeContainerProvider.Close(self)
        self.axdebugger = None
        print(f"Closing {len(self.nodes)} nodes")
        for node in self.nodes.values():
            node.Close()
        self.nodes = {}


class OriginalInterfaceMaker:
    def MakeInterfaces(self, pdm):
        app = self.pdm.CreateApplication()
        self.cookie = pdm.AddApplication(app)
        root = app.GetRootNode()
        return app, root

    def CloseInterfaces(self, pdm):
        pdm.RemoveApplication(self.cookie)


class SimpleHostStyleInterfaceMaker:
    def MakeInterfaces(self, pdm):
        app = pdm.GetDefaultApplication()
        root = app.GetRootNode()
        return app, root

    def CloseInterfaces(self, pdm):
        pass


class AXDebugger:
    def __init__(self, interfaceMaker=None, processName=None):
        if processName is None:
            processName = "Python Process"
        if interfaceMaker is None:
            interfaceMaker = SimpleHostStyleInterfaceMaker()

        self.pydebugger = adb.Debugger()

        self.pdm = pythoncom.CoCreateInstance(
            axdebug.CLSID_ProcessDebugManager,
            None,
            pythoncom.CLSCTX_ALL,
            axdebug.IID_IProcessDebugManager,
        )

        self.app, self.root = interfaceMaker.MakeInterfaces(self.pdm)
        self.app.SetName(processName)
        self.interfaceMaker = interfaceMaker

        expressionProvider = _wrap(
            expressions.ProvideExpressionContexts(),
            axdebug.IID_IProvideExpressionContexts,
        )
        self.expressionCookie = self.app.AddGlobalExpressionContextProvider(
            expressionProvider
        )

        contProvider = CodeContainerProvider(self)
        self.pydebugger.AttachApp(self.app, contProvider)

    def Break(self):
        # Get the frame we start debugging from - this is the frame 1 level up
        try:
            1 + ""
        except:
            frame = sys.exc_info()[2].tb_frame.f_back

        # Get/create the debugger, and tell it to break.
        self.app.StartDebugSession()
        # self.app.CauseBreak()

        self.pydebugger.SetupAXDebugging(None, frame)
        self.pydebugger.set_trace()

    def Close(self):
        self.pydebugger.ResetAXDebugging()
        self.interfaceMaker.CloseInterfaces(self.pdm)
        self.pydebugger.CloseApp()
        self.app.RemoveGlobalExpressionContextProvider(self.expressionCookie)
        self.expressionCookie = None

        self.pdm = None
        self.app = None
        self.pydebugger = None
        self.root = None

    def RefreshAllModules(self, nodes, containerProvider):
        RefreshAllModules(
            nodes, self.root, self.CreateApplicationNode, (containerProvider,)
        )

    def CreateApplicationNode(self, node, containerProvider):
        realNode = self.app.CreateApplicationNode()

        document = documents.DebugDocumentText(node.cont)
        document = _wrap(document, axdebug.IID_IDebugDocument)

        node.cont.debugDocument = document

        provider = documents.DebugDocumentProvider(document)
        provider = _wrap(provider, axdebug.IID_IDebugDocumentProvider)
        realNode.SetDocumentProvider(provider)

        containerProvider.AddCodeContainer(node.cont, realNode)
        return realNode


def _GetCurrentDebugger():
    global currentDebugger
    if currentDebugger is None:
        currentDebugger = AXDebugger()
    return currentDebugger


def Break():
    _GetCurrentDebugger().Break()


brk = Break
set_trace = Break


def dosomethingelse():
    a = 2
    b = "Hi there"


def dosomething():
    a = 1
    b = 2
    dosomethingelse()


def test():
    Break()
    input("Waiting...")
    dosomething()
    print("Done")


if __name__ == "__main__":
    print("About to test the debugging interfaces!")
    test()
    print(
        f" {pythoncom._GetInterfaceCount()}/{pythoncom._GetGatewayCount()} com objects still alive"
    )

# === NexusCore/openenv\Lib\site-packages\PIL\PSDraw.py ===
#
# The Python Imaging Library
# $Id$
#
# Simple PostScript graphics interface
#
# History:
# 1996-04-20 fl   Created
# 1999-01-10 fl   Added gsave/grestore to image method
# 2005-05-04 fl   Fixed floating point issue in image (from Eric Etheridge)
#
# Copyright (c) 1997-2005 by Secret Labs AB.  All rights reserved.
# Copyright (c) 1996 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import sys
from typing import IO

from . import EpsImagePlugin

TYPE_CHECKING = False


##
# Simple PostScript graphics interface.


class PSDraw:
    """
    Sets up printing to the given file. If ``fp`` is omitted,
    ``sys.stdout.buffer`` is assumed.
    """

    def __init__(self, fp: IO[bytes] | None = None) -> None:
        if not fp:
            fp = sys.stdout.buffer
        self.fp = fp

    def begin_document(self, id: str | None = None) -> None:
        """Set up printing of a document. (Write PostScript DSC header.)"""
        # FIXME: incomplete
        self.fp.write(
            b"%!PS-Adobe-3.0\n"
            b"save\n"
            b"/showpage { } def\n"
            b"%%EndComments\n"
            b"%%BeginDocument\n"
        )
        # self.fp.write(ERROR_PS)  # debugging!
        self.fp.write(EDROFF_PS)
        self.fp.write(VDI_PS)
        self.fp.write(b"%%EndProlog\n")
        self.isofont: dict[bytes, int] = {}

    def end_document(self) -> None:
        """Ends printing. (Write PostScript DSC footer.)"""
        self.fp.write(b"%%EndDocument\nrestore showpage\n%%End\n")
        if hasattr(self.fp, "flush"):
            self.fp.flush()

    def setfont(self, font: str, size: int) -> None:
        """
        Selects which font to use.

        :param font: A PostScript font name
        :param size: Size in points.
        """
        font_bytes = bytes(font, "UTF-8")
        if font_bytes not in self.isofont:
            # reencode font
            self.fp.write(
                b"/PSDraw-%s ISOLatin1Encoding /%s E\n" % (font_bytes, font_bytes)
            )
            self.isofont[font_bytes] = 1
        # rough
        self.fp.write(b"/F0 %d /PSDraw-%s F\n" % (size, font_bytes))

    def line(self, xy0: tuple[int, int], xy1: tuple[int, int]) -> None:
        """
        Draws a line between the two points. Coordinates are given in
        PostScript point coordinates (72 points per inch, (0, 0) is the lower
        left corner of the page).
        """
        self.fp.write(b"%d %d %d %d Vl\n" % (*xy0, *xy1))

    def rectangle(self, box: tuple[int, int, int, int]) -> None:
        """
        Draws a rectangle.

        :param box: A tuple of four integers, specifying left, bottom, width and
           height.
        """
        self.fp.write(b"%d %d M 0 %d %d Vr\n" % box)

    def text(self, xy: tuple[int, int], text: str) -> None:
        """
        Draws text at the given position. You must use
        :py:meth:`~PIL.PSDraw.PSDraw.setfont` before calling this method.
        """
        text_bytes = bytes(text, "UTF-8")
        text_bytes = b"\\(".join(text_bytes.split(b"("))
        text_bytes = b"\\)".join(text_bytes.split(b")"))
        self.fp.write(b"%d %d M (%s) S\n" % (xy + (text_bytes,)))

    if TYPE_CHECKING:
        from . import Image

    def image(
        self, box: tuple[int, int, int, int], im: Image.Image, dpi: int | None = None
    ) -> None:
        """Draw a PIL image, centered in the given box."""
        # default resolution depends on mode
        if not dpi:
            if im.mode == "1":
                dpi = 200  # fax
            else:
                dpi = 100  # grayscale
        # image size (on paper)
        x = im.size[0] * 72 / dpi
        y = im.size[1] * 72 / dpi
        # max allowed size
        xmax = float(box[2] - box[0])
        ymax = float(box[3] - box[1])
        if x > xmax:
            y = y * xmax / x
            x = xmax
        if y > ymax:
            x = x * ymax / y
            y = ymax
        dx = (xmax - x) / 2 + box[0]
        dy = (ymax - y) / 2 + box[1]
        self.fp.write(b"gsave\n%f %f translate\n" % (dx, dy))
        if (x, y) != im.size:
            # EpsImagePlugin._save prints the image at (0,0,xsize,ysize)
            sx = x / im.size[0]
            sy = y / im.size[1]
            self.fp.write(b"%f %f scale\n" % (sx, sy))
        EpsImagePlugin._save(im, self.fp, "", 0)
        self.fp.write(b"\ngrestore\n")


# --------------------------------------------------------------------
# PostScript driver

#
# EDROFF.PS -- PostScript driver for Edroff 2
#
# History:
# 94-01-25 fl: created (edroff 2.04)
#
# Copyright (c) Fredrik Lundh 1994.
#


EDROFF_PS = b"""\
/S { show } bind def
/P { moveto show } bind def
/M { moveto } bind def
/X { 0 rmoveto } bind def
/Y { 0 exch rmoveto } bind def
/E {    findfont
        dup maxlength dict begin
        {
                1 index /FID ne { def } { pop pop } ifelse
        } forall
        /Encoding exch def
        dup /FontName exch def
        currentdict end definefont pop
} bind def
/F {    findfont exch scalefont dup setfont
        [ exch /setfont cvx ] cvx bind def
} bind def
"""

#
# VDI.PS -- PostScript driver for VDI meta commands
#
# History:
# 94-01-25 fl: created (edroff 2.04)
#
# Copyright (c) Fredrik Lundh 1994.
#

VDI_PS = b"""\
/Vm { moveto } bind def
/Va { newpath arcn stroke } bind def
/Vl { moveto lineto stroke } bind def
/Vc { newpath 0 360 arc closepath } bind def
/Vr {   exch dup 0 rlineto
        exch dup 0 exch rlineto
        exch neg 0 rlineto
        0 exch neg rlineto
        setgray fill } bind def
/Tm matrix def
/Ve {   Tm currentmatrix pop
        translate scale newpath 0 0 .5 0 360 arc closepath
        Tm setmatrix
} bind def
/Vf { currentgray exch setgray fill setgray } bind def
"""

#
# ERROR.PS -- Error handler
#
# History:
# 89-11-21 fl: created (pslist 1.10)
#

ERROR_PS = b"""\
/landscape false def
/errorBUF 200 string def
/errorNL { currentpoint 10 sub exch pop 72 exch moveto } def
errordict begin /handleerror {
    initmatrix /Courier findfont 10 scalefont setfont
    newpath 72 720 moveto $error begin /newerror false def
    (PostScript Error) show errorNL errorNL
    (Error: ) show
        /errorname load errorBUF cvs show errorNL errorNL
    (Command: ) show
        /command load dup type /stringtype ne { errorBUF cvs } if show
        errorNL errorNL
    (VMstatus: ) show
        vmstatus errorBUF cvs show ( bytes available, ) show
        errorBUF cvs show ( bytes used at level ) show
        errorBUF cvs show errorNL errorNL
    (Operand stargck: ) show errorNL /ostargck load {
        dup type /stringtype ne { errorBUF cvs } if 72 0 rmoveto show errorNL
    } forall errorNL
    (Execution stargck: ) show errorNL /estargck load {
        dup type /stringtype ne { errorBUF cvs } if 72 0 rmoveto show errorNL
    } forall
    end showpage
} def end
"""

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc5990.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# Use of the RSA-KEM Key Transport Algorithm in the CMS
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc5990.txt
#

from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import univ

from pyasn1_modules import rfc5280

MAX = float('inf')

def _OID(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))
    return univ.ObjectIdentifier(output)


# Imports from RFC 5280

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier


# Useful types and definitions

class NullParms(univ.Null):
    pass


# Object identifier arcs

is18033_2 = _OID(1, 0, 18033, 2)

nistAlgorithm = _OID(2, 16, 840, 1, 101, 3, 4)

pkcs_1 = _OID(1, 2, 840, 113549, 1, 1)

x9_44 = _OID(1, 3, 133, 16, 840, 9, 44)

x9_44_components = _OID(x9_44, 1)


# Types for algorithm identifiers

class Camellia_KeyWrappingScheme(AlgorithmIdentifier):
    pass

class DataEncapsulationMechanism(AlgorithmIdentifier):
    pass

class KDF2_HashFunction(AlgorithmIdentifier):
    pass

class KDF3_HashFunction(AlgorithmIdentifier):
    pass

class KeyDerivationFunction(AlgorithmIdentifier):
    pass

class KeyEncapsulationMechanism(AlgorithmIdentifier):
    pass

class X9_SymmetricKeyWrappingScheme(AlgorithmIdentifier):
    pass


# RSA-KEM Key Transport Algorithm

id_rsa_kem = _OID(1, 2, 840, 113549, 1, 9, 16, 3, 14)


class GenericHybridParameters(univ.Sequence):
    pass

GenericHybridParameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('kem', KeyEncapsulationMechanism()),
    namedtype.NamedType('dem', DataEncapsulationMechanism())
)


rsa_kem = AlgorithmIdentifier()
rsa_kem['algorithm'] = id_rsa_kem
rsa_kem['parameters'] = GenericHybridParameters()


# KEM-RSA Key Encapsulation Mechanism

id_kem_rsa = _OID(is18033_2, 2, 4)


class KeyLength(univ.Integer):
    pass

KeyLength.subtypeSpec = constraint.ValueRangeConstraint(1, MAX)


class RsaKemParameters(univ.Sequence):
    pass

RsaKemParameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('keyDerivationFunction', KeyDerivationFunction()),
    namedtype.NamedType('keyLength', KeyLength())
)


kem_rsa = AlgorithmIdentifier()
kem_rsa['algorithm'] = id_kem_rsa
kem_rsa['parameters'] = RsaKemParameters()


# Key Derivation Functions

id_kdf_kdf2 = _OID(x9_44_components, 1)

id_kdf_kdf3 = _OID(x9_44_components, 2)


kdf2 = AlgorithmIdentifier()
kdf2['algorithm'] = id_kdf_kdf2
kdf2['parameters'] = KDF2_HashFunction()

kdf3 = AlgorithmIdentifier()
kdf3['algorithm'] = id_kdf_kdf3
kdf3['parameters'] = KDF3_HashFunction()


# Hash Functions

id_sha1 = _OID(1, 3, 14, 3, 2, 26)

id_sha224 = _OID(2, 16, 840, 1, 101, 3, 4, 2, 4)

id_sha256 = _OID(2, 16, 840, 1, 101, 3, 4, 2, 1)

id_sha384 = _OID(2, 16, 840, 1, 101, 3, 4, 2, 2)

id_sha512 = _OID(2, 16, 840, 1, 101, 3, 4, 2, 3)


sha1 = AlgorithmIdentifier()
sha1['algorithm'] = id_sha1
sha1['parameters'] = univ.Null("")

sha224 = AlgorithmIdentifier()
sha224['algorithm'] = id_sha224
sha224['parameters'] = univ.Null("")

sha256 = AlgorithmIdentifier()
sha256['algorithm'] = id_sha256
sha256['parameters'] = univ.Null("")

sha384 = AlgorithmIdentifier()
sha384['algorithm'] = id_sha384
sha384['parameters'] = univ.Null("")

sha512 = AlgorithmIdentifier()
sha512['algorithm'] = id_sha512
sha512['parameters'] = univ.Null("")


# Symmetric Key-Wrapping Schemes

id_aes128_Wrap = _OID(nistAlgorithm, 1, 5)

id_aes192_Wrap = _OID(nistAlgorithm, 1, 25)

id_aes256_Wrap = _OID(nistAlgorithm, 1, 45)

id_alg_CMS3DESwrap = _OID(1, 2, 840, 113549, 1, 9, 16, 3, 6)

id_camellia128_Wrap = _OID(1, 2, 392, 200011, 61, 1, 1, 3, 2)

id_camellia192_Wrap = _OID(1, 2, 392, 200011, 61, 1, 1, 3, 3)

id_camellia256_Wrap = _OID(1, 2, 392, 200011, 61, 1, 1, 3, 4)


aes128_Wrap = AlgorithmIdentifier()
aes128_Wrap['algorithm'] = id_aes128_Wrap
# aes128_Wrap['parameters'] are absent

aes192_Wrap = AlgorithmIdentifier()
aes192_Wrap['algorithm'] = id_aes128_Wrap
# aes192_Wrap['parameters'] are absent

aes256_Wrap = AlgorithmIdentifier()
aes256_Wrap['algorithm'] = id_sha256
# aes256_Wrap['parameters'] are absent

tdes_Wrap = AlgorithmIdentifier()
tdes_Wrap['algorithm'] = id_alg_CMS3DESwrap
tdes_Wrap['parameters'] = univ.Null("")

camellia128_Wrap = AlgorithmIdentifier()
camellia128_Wrap['algorithm'] = id_camellia128_Wrap
# camellia128_Wrap['parameters'] are absent

camellia192_Wrap = AlgorithmIdentifier()
camellia192_Wrap['algorithm'] = id_camellia192_Wrap
# camellia192_Wrap['parameters'] are absent

camellia256_Wrap = AlgorithmIdentifier()
camellia256_Wrap['algorithm'] = id_camellia256_Wrap
# camellia256_Wrap['parameters'] are absent


# Update the Algorithm Identifier map in rfc5280.py.
# Note that the ones that must not have parameters are not added to the map.

_algorithmIdentifierMapUpdate = {
    id_rsa_kem: GenericHybridParameters(),
    id_kem_rsa: RsaKemParameters(),
    id_kdf_kdf2: KDF2_HashFunction(),
    id_kdf_kdf3: KDF3_HashFunction(),
    id_sha1: univ.Null(),
    id_sha224: univ.Null(),
    id_sha256: univ.Null(),
    id_sha384: univ.Null(),
    id_sha512: univ.Null(),
    id_alg_CMS3DESwrap: univ.Null(),
}

rfc5280.algorithmIdentifierMap.update(_algorithmIdentifierMapUpdate)

# === NexusCore/openenv\Lib\site-packages\starlette\templating.py ===
from __future__ import annotations

import typing
import warnings
from os import PathLike

from starlette.background import BackgroundTask
from starlette.datastructures import URL
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.types import Receive, Scope, Send

try:
    import jinja2

    # @contextfunction was renamed to @pass_context in Jinja 3.0, and was removed in 3.1
    # hence we try to get pass_context (most installs will be >=3.1)
    # and fall back to contextfunction,
    # adding a type ignore for mypy to let us access an attribute that may not exist
    if hasattr(jinja2, "pass_context"):
        pass_context = jinja2.pass_context
    else:  # pragma: nocover
        pass_context = jinja2.contextfunction  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: nocover
    jinja2 = None  # type: ignore[assignment]


class _TemplateResponse(HTMLResponse):
    def __init__(
        self,
        template: typing.Any,
        context: dict[str, typing.Any],
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ):
        self.template = template
        self.context = context
        content = template.render(context)
        super().__init__(content, status_code, headers, media_type, background)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = self.context.get("request", {})
        extensions = request.get("extensions", {})
        if "http.response.debug" in extensions:
            await send(
                {
                    "type": "http.response.debug",
                    "info": {
                        "template": self.template,
                        "context": self.context,
                    },
                }
            )
        await super().__call__(scope, receive, send)


class Jinja2Templates:
    """
    templates = Jinja2Templates("templates")

    return templates.TemplateResponse("index.html", {"request": request})
    """

    @typing.overload
    def __init__(
        self,
        directory: str
        | PathLike[typing.AnyStr]
        | typing.Sequence[str | PathLike[typing.AnyStr]],
        *,
        context_processors: list[typing.Callable[[Request], dict[str, typing.Any]]]
        | None = None,
        **env_options: typing.Any,
    ) -> None:
        ...

    @typing.overload
    def __init__(
        self,
        *,
        env: jinja2.Environment,
        context_processors: list[typing.Callable[[Request], dict[str, typing.Any]]]
        | None = None,
    ) -> None:
        ...

    def __init__(
        self,
        directory: str
        | PathLike[typing.AnyStr]
        | typing.Sequence[str | PathLike[typing.AnyStr]]
        | None = None,
        *,
        context_processors: list[typing.Callable[[Request], dict[str, typing.Any]]]
        | None = None,
        env: jinja2.Environment | None = None,
        **env_options: typing.Any,
    ) -> None:
        if env_options:
            warnings.warn(
                "Extra environment options are deprecated. Use a preconfigured jinja2.Environment instead.",  # noqa: E501
                DeprecationWarning,
            )
        assert jinja2 is not None, "jinja2 must be installed to use Jinja2Templates"
        assert directory or env, "either 'directory' or 'env' arguments must be passed"
        self.context_processors = context_processors or []
        if directory is not None:
            self.env = self._create_env(directory, **env_options)
        elif env is not None:
            self.env = env

        self._setup_env_defaults(self.env)

    def _create_env(
        self,
        directory: str
        | PathLike[typing.AnyStr]
        | typing.Sequence[str | PathLike[typing.AnyStr]],
        **env_options: typing.Any,
    ) -> jinja2.Environment:
        loader = jinja2.FileSystemLoader(directory)
        env_options.setdefault("loader", loader)
        env_options.setdefault("autoescape", True)

        return jinja2.Environment(**env_options)

    def _setup_env_defaults(self, env: jinja2.Environment) -> None:
        @pass_context
        def url_for(
            context: dict[str, typing.Any],
            name: str,
            /,
            **path_params: typing.Any,
        ) -> URL:
            request: Request = context["request"]
            return request.url_for(name, **path_params)

        env.globals.setdefault("url_for", url_for)

    def get_template(self, name: str) -> jinja2.Template:
        return self.env.get_template(name)

    @typing.overload
    def TemplateResponse(
        self,
        request: Request,
        name: str,
        context: dict[str, typing.Any] | None = None,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> _TemplateResponse:
        ...

    @typing.overload
    def TemplateResponse(
        self,
        name: str,
        context: dict[str, typing.Any] | None = None,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> _TemplateResponse:
        # Deprecated usage
        ...

    def TemplateResponse(
        self, *args: typing.Any, **kwargs: typing.Any
    ) -> _TemplateResponse:
        if args:
            if isinstance(
                args[0], str
            ):  # the first argument is template name (old style)
                warnings.warn(
                    "The `name` is not the first parameter anymore. "
                    "The first parameter should be the `Request` instance.\n"
                    'Replace `TemplateResponse(name, {"request": request})` by `TemplateResponse(request, name)`.',  # noqa: E501
                    DeprecationWarning,
                )

                name = args[0]
                context = args[1] if len(args) > 1 else kwargs.get("context", {})
                status_code = (
                    args[2] if len(args) > 2 else kwargs.get("status_code", 200)
                )
                headers = args[2] if len(args) > 2 else kwargs.get("headers")
                media_type = args[3] if len(args) > 3 else kwargs.get("media_type")
                background = args[4] if len(args) > 4 else kwargs.get("background")

                if "request" not in context:
                    raise ValueError('context must include a "request" key')
                request = context["request"]
            else:  # the first argument is a request instance (new style)
                request = args[0]
                name = args[1] if len(args) > 1 else kwargs["name"]
                context = args[2] if len(args) > 2 else kwargs.get("context", {})
                status_code = (
                    args[3] if len(args) > 3 else kwargs.get("status_code", 200)
                )
                headers = args[4] if len(args) > 4 else kwargs.get("headers")
                media_type = args[5] if len(args) > 5 else kwargs.get("media_type")
                background = args[6] if len(args) > 6 else kwargs.get("background")
        else:  # all arguments are kwargs
            if "request" not in kwargs:
                warnings.warn(
                    "The `TemplateResponse` now requires the `request` argument.\n"
                    'Replace `TemplateResponse(name, {"context": context})` by `TemplateResponse(request, name)`.',  # noqa: E501
                    DeprecationWarning,
                )
                if "request" not in kwargs.get("context", {}):
                    raise ValueError('context must include a "request" key')

            context = kwargs.get("context", {})
            request = kwargs.get("request", context.get("request"))
            name = typing.cast(str, kwargs["name"])
            status_code = kwargs.get("status_code", 200)
            headers = kwargs.get("headers")
            media_type = kwargs.get("media_type")
            background = kwargs.get("background")

        context.setdefault("request", request)
        for context_processor in self.context_processors:
            context.update(context_processor(request))

        template = self.get_template(name)
        return _TemplateResponse(
            template,
            context,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_timeout.py ===
from _pydev_bundle._pydev_saved_modules import ThreadingEvent, ThreadingLock, threading_current_thread
from _pydevd_bundle.pydevd_daemon_thread import PyDBDaemonThread
from _pydevd_bundle.pydevd_constants import thread_get_ident, IS_CPYTHON, NULL
import ctypes
import time
from _pydev_bundle import pydev_log
import weakref
from _pydevd_bundle.pydevd_utils import is_current_thread_main_thread
from _pydevd_bundle import pydevd_utils

_DEBUG = False  # Default should be False as this can be very verbose.


class _TimeoutThread(PyDBDaemonThread):
    """
    The idea in this class is that it should be usually stopped waiting
    for the next event to be called (paused in a threading.Event.wait).

    When a new handle is added it sets the event so that it processes the handles and
    then keeps on waiting as needed again.

    This is done so that it's a bit more optimized than creating many Timer threads.
    """

    def __init__(self, py_db):
        PyDBDaemonThread.__init__(self, py_db)
        self._event = ThreadingEvent()
        self._handles = []

        # We could probably do things valid without this lock so that it's possible to add
        # handles while processing, but the implementation would also be harder to follow,
        # so, for now, we're either processing or adding handles, not both at the same time.
        self._lock = ThreadingLock()

    def _on_run(self):
        wait_time = None
        while not self._kill_received:
            if _DEBUG:
                if wait_time is None:
                    pydev_log.critical("pydevd_timeout: Wait until a new handle is added.")
                else:
                    pydev_log.critical("pydevd_timeout: Next wait time: %s.", wait_time)
            self._event.wait(wait_time)

            if self._kill_received:
                self._handles = []
                return

            wait_time = self.process_handles()

    def process_handles(self):
        """
        :return int:
            Returns the time we should be waiting for to process the next event properly.
        """
        with self._lock:
            if _DEBUG:
                pydev_log.critical("pydevd_timeout: Processing handles")
            self._event.clear()
            handles = self._handles
            new_handles = self._handles = []

            # Do all the processing based on this time (we want to consider snapshots
            # of processing time -- anything not processed now may be processed at the
            # next snapshot).
            curtime = time.time()

            min_handle_timeout = None

            for handle in handles:
                if curtime < handle.abs_timeout and not handle.disposed:
                    # It still didn't time out.
                    if _DEBUG:
                        pydev_log.critical("pydevd_timeout: Handle NOT processed: %s", handle)
                    new_handles.append(handle)
                    if min_handle_timeout is None:
                        min_handle_timeout = handle.abs_timeout

                    elif handle.abs_timeout < min_handle_timeout:
                        min_handle_timeout = handle.abs_timeout

                else:
                    if _DEBUG:
                        pydev_log.critical("pydevd_timeout: Handle processed: %s", handle)
                    # Timed out (or disposed), so, let's execute it (should be no-op if disposed).
                    handle.exec_on_timeout()

            if min_handle_timeout is None:
                return None
            else:
                timeout = min_handle_timeout - curtime
                if timeout <= 0:
                    pydev_log.critical("pydevd_timeout: Expected timeout to be > 0. Found: %s", timeout)

                return timeout

    def do_kill_pydev_thread(self):
        PyDBDaemonThread.do_kill_pydev_thread(self)
        with self._lock:
            self._event.set()

    def add_on_timeout_handle(self, handle):
        with self._lock:
            self._handles.append(handle)
            self._event.set()


class _OnTimeoutHandle(object):
    def __init__(self, tracker, abs_timeout, on_timeout, kwargs):
        self._str = "_OnTimeoutHandle(%s)" % (on_timeout,)

        self._tracker = weakref.ref(tracker)
        self.abs_timeout = abs_timeout
        self.on_timeout = on_timeout
        if kwargs is None:
            kwargs = {}
        self.kwargs = kwargs
        self.disposed = False

    def exec_on_timeout(self):
        # Note: lock should already be obtained when executing this function.
        kwargs = self.kwargs
        on_timeout = self.on_timeout

        if not self.disposed:
            self.disposed = True
            self.kwargs = None
            self.on_timeout = None

            try:
                if _DEBUG:
                    pydev_log.critical("pydevd_timeout: Calling on timeout: %s with kwargs: %s", on_timeout, kwargs)

                on_timeout(**kwargs)
            except Exception:
                pydev_log.exception("pydevd_timeout: Exception on callback timeout.")

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        tracker = self._tracker()

        if tracker is None:
            lock = NULL
        else:
            lock = tracker._lock

        with lock:
            self.disposed = True
            self.kwargs = None
            self.on_timeout = None

    def __str__(self):
        return self._str

    __repr__ = __str__


class TimeoutTracker(object):
    """
    This is a helper class to track the timeout of something.
    """

    def __init__(self, py_db):
        self._thread = None
        self._lock = ThreadingLock()
        self._py_db = weakref.ref(py_db)

    def call_on_timeout(self, timeout, on_timeout, kwargs=None):
        """
        This can be called regularly to always execute the given function after a given timeout:

        call_on_timeout(py_db, 10, on_timeout)


        Or as a context manager to stop the method from being called if it finishes before the timeout
        elapses:

        with call_on_timeout(py_db, 10, on_timeout):
            ...

        Note: the callback will be called from a PyDBDaemonThread.
        """
        with self._lock:
            if self._thread is None:
                if _DEBUG:
                    pydev_log.critical("pydevd_timeout: Created _TimeoutThread.")

                self._thread = _TimeoutThread(self._py_db())
                self._thread.start()

            curtime = time.time()
            handle = _OnTimeoutHandle(self, curtime + timeout, on_timeout, kwargs)
            if _DEBUG:
                pydev_log.critical("pydevd_timeout: Added handle: %s.", handle)
            self._thread.add_on_timeout_handle(handle)
            return handle


def create_interrupt_this_thread_callback():
    """
    The idea here is returning a callback that when called will generate a KeyboardInterrupt
    in the thread that called this function.

    If this is the main thread, this means that it'll emulate a Ctrl+C (which may stop I/O
    and sleep operations).

    For other threads, this will call PyThreadState_SetAsyncExc to raise
    a KeyboardInterrupt before the next instruction (so, it won't really interrupt I/O or
    sleep operations).

    :return callable:
        Returns a callback that will interrupt the current thread (this may be called
        from an auxiliary thread).
    """
    tid = thread_get_ident()

    if is_current_thread_main_thread():
        main_thread = threading_current_thread()

        def raise_on_this_thread():
            pydev_log.debug("Callback to interrupt main thread.")
            pydevd_utils.interrupt_main_thread(main_thread)

    else:
        # Note: this works in the sense that it can stop some cpu-intensive slow operation,
        # but we can't really interrupt the thread out of some sleep or I/O operation
        # (this will only be raised when Python is about to execute the next instruction).
        def raise_on_this_thread():
            if IS_CPYTHON:
                pydev_log.debug("Interrupt thread: %s", tid)
                ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(KeyboardInterrupt))
            else:
                pydev_log.debug("It is only possible to interrupt non-main threads in CPython.")

    return raise_on_this_thread

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\computer.py ===
import inspect
import json

from .ai.ai import Ai
from .browser.browser import Browser
from .calendar.calendar import Calendar
from .clipboard.clipboard import Clipboard
from .contacts.contacts import Contacts
from .display.display import Display
from .docs.docs import Docs
from .files.files import Files
from .keyboard.keyboard import Keyboard
from .mail.mail import Mail
from .mouse.mouse import Mouse
from .os.os import Os
from .skills.skills import Skills
from .sms.sms import SMS
from .terminal.terminal import Terminal
from .vision.vision import Vision


class Computer:
    def __init__(self, interpreter):
        self.interpreter = interpreter

        self.terminal = Terminal(self)

        self.offline = False
        self.verbose = False
        self.debug = False

        self.mouse = Mouse(self)
        self.keyboard = Keyboard(self)
        self.display = Display(self)
        self.clipboard = Clipboard(self)
        self.mail = Mail(self)
        self.sms = SMS(self)
        self.calendar = Calendar(self)
        self.contacts = Contacts(self)
        self.browser = Browser(self)
        self.os = Os(self)
        self.vision = Vision(self)
        self.skills = Skills(self)
        self.docs = Docs(self)
        self.ai = Ai(self)
        self.files = Files(self)

        self.emit_images = True
        self.api_base = "https://api.openinterpreter.com/v0"
        self.save_skills = True

        self.import_computer_api = False  # Defaults to false
        self._has_imported_computer_api = False  # Because we only want to do this once

        self.import_skills = False
        self._has_imported_skills = False
        self.max_output = (
            self.interpreter.max_output
        )  # Should mirror interpreter.max_output

        computer_tools = "\n".join(
            self._get_all_computer_tools_signature_and_description()
        )

        self.system_message = f"""

# THE COMPUTER API

A python `computer` module is ALREADY IMPORTED, and can be used for many tasks:

```python
{computer_tools}
```

Do not import the computer module, or any of its sub-modules. They are already imported.

    """.strip()

    # Shortcut for computer.terminal.languages
    @property
    def languages(self):
        return self.terminal.languages

    @languages.setter
    def languages(self, value):
        self.terminal.languages = value

    def _get_all_computer_tools_list(self):
        return [
            self.mouse,
            self.keyboard,
            self.display,
            self.clipboard,
            self.mail,
            self.sms,
            self.calendar,
            self.contacts,
            self.browser,
            self.os,
            self.vision,
            self.skills,
            self.docs,
            self.ai,
            self.files,
        ]

    def _get_all_computer_tools_signature_and_description(self):
        """
        This function returns a list of all the computer tools that are available with their signature and description from the function docstrings.
        for example:
        computer.browser.search(query) # Searches the web for the specified query and returns the results.
        computer.calendar.create_event(title: str, start_date: datetime.datetime, end_date: datetime.datetime, location: str = "", notes: str = "", calendar: str = None) -> str # Creates a new calendar event in the default calendar with the given parameters using AppleScript.
        """
        tools = self._get_all_computer_tools_list()
        tools_signature_and_description = []
        for tool in tools:
            tool_info = self._extract_tool_info(tool)
            for method in tool_info["methods"]:
                # Format as tool_signature # tool_description
                formatted_info = f"{method['signature']} # {method['description']}"
                tools_signature_and_description.append(formatted_info)
        return tools_signature_and_description

    def _extract_tool_info(self, tool):
        """
        Helper function to extract the signature and description of a tool's methods.
        """
        tool_info = {"signature": tool.__class__.__name__, "methods": []}
        if tool.__class__.__name__ == "Browser":
            methods = []
            for name in dir(tool):
                if "driver" in name:
                    continue  # Skip methods containing 'driver' in their name
                attr = getattr(tool, name)
                if (
                    callable(attr)
                    and not name.startswith("_")
                    and not hasattr(attr, "__wrapped__")
                    and not isinstance(attr, property)
                ):
                    # Construct the method signature manually
                    param_str = ", ".join(
                        param
                        for param in attr.__code__.co_varnames[
                            : attr.__code__.co_argcount
                        ]
                    )
                    full_signature = f"computer.{tool.__class__.__name__.lower()}.{name}({param_str})"
                    # Get the method description
                    method_description = attr.__doc__ or ""
                    # Append the method details
                    tool_info["methods"].append(
                        {
                            "signature": full_signature,
                            "description": method_description.strip(),
                        }
                    )
            return tool_info

        for name, method in inspect.getmembers(tool, predicate=inspect.ismethod):
            # Check if the method should be ignored based on its decorator
            if not name.startswith("_") and not hasattr(method, "__wrapped__"):
                # Get the method signature
                method_signature = inspect.signature(method)
                # Construct the signature string without *args and **kwargs
                param_str = ", ".join(
                    f"{param.name}"
                    if param.default == param.empty
                    else f"{param.name}={param.default!r}"
                    for param in method_signature.parameters.values()
                    if param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD)
                )
                full_signature = (
                    f"computer.{tool.__class__.__name__.lower()}.{name}({param_str})"
                )
                # Get the method description
                method_description = method.__doc__ or ""
                # Append the method details
                tool_info["methods"].append(
                    {
                        "signature": full_signature,
                        "description": method_description.strip(),
                    }
                )
        return tool_info

    def run(self, *args, **kwargs):
        """
        Shortcut for computer.terminal.run
        """
        return self.terminal.run(*args, **kwargs)

    def exec(self, code):
        """
        Shortcut for computer.terminal.run("shell", code)
        It has hallucinated this.
        """
        return self.terminal.run("shell", code)

    def stop(self):
        """
        Shortcut for computer.terminal.stop
        """
        return self.terminal.stop()

    def terminate(self):
        """
        Shortcut for computer.terminal.terminate
        """
        return self.terminal.terminate()

    def screenshot(self, *args, **kwargs):
        """
        Shortcut for computer.display.screenshot
        """
        return self.display.screenshot(*args, **kwargs)

    def view(self, *args, **kwargs):
        """
        Shortcut for computer.display.screenshot
        """
        return self.display.screenshot(*args, **kwargs)

    def to_dict(self):
        def json_serializable(obj):
            try:
                json.dumps(obj)
                return True
            except:
                return False

        return {k: v for k, v in self.__dict__.items() if json_serializable(v)}

    def load_dict(self, data_dict):
        for key, value in data_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)

# === NexusCore/openenv\Lib\site-packages\matplotlib\style\core.py ===
"""
Core functions and attributes for the matplotlib style library:

``use``
    Select style sheet to override the current matplotlib settings.
``context``
    Context manager to use a style sheet temporarily.
``available``
    List available style sheets.
``library``
    A dictionary of style names and matplotlib settings.
"""

import contextlib
import importlib.resources
import logging
import os
from pathlib import Path
import warnings

import matplotlib as mpl
from matplotlib import _api, _docstring, _rc_params_in_file, rcParamsDefault

_log = logging.getLogger(__name__)

__all__ = ['use', 'context', 'available', 'library', 'reload_library']


BASE_LIBRARY_PATH = os.path.join(mpl.get_data_path(), 'stylelib')
# Users may want multiple library paths, so store a list of paths.
USER_LIBRARY_PATHS = [os.path.join(mpl.get_configdir(), 'stylelib')]
STYLE_EXTENSION = 'mplstyle'
# A list of rcParams that should not be applied from styles
STYLE_BLACKLIST = {
    'interactive', 'backend', 'webagg.port', 'webagg.address',
    'webagg.port_retries', 'webagg.open_in_browser', 'backend_fallback',
    'toolbar', 'timezone', 'figure.max_open_warning',
    'figure.raise_window', 'savefig.directory', 'tk.window_focus',
    'docstring.hardcopy', 'date.epoch'}


@_docstring.Substitution(
    "\n".join(map("- {}".format, sorted(STYLE_BLACKLIST, key=str.lower)))
)
def use(style):
    """
    Use Matplotlib style settings from a style specification.

    The style name of 'default' is reserved for reverting back to
    the default style settings.

    .. note::

       This updates the `.rcParams` with the settings from the style.
       `.rcParams` not defined in the style are kept.

    Parameters
    ----------
    style : str, dict, Path or list

        A style specification. Valid options are:

        str
            - One of the style names in `.style.available` (a builtin style or
              a style installed in the user library path).

            - A dotted name of the form "package.style_name"; in that case,
              "package" should be an importable Python package name, e.g. at
              ``/path/to/package/__init__.py``; the loaded style file is
              ``/path/to/package/style_name.mplstyle``.  (Style files in
              subpackages are likewise supported.)

            - The path or URL to a style file, which gets loaded by
              `.rc_params_from_file`.

        dict
            A mapping of key/value pairs for `matplotlib.rcParams`.

        Path
            The path to a style file, which gets loaded by
            `.rc_params_from_file`.

        list
            A list of style specifiers (str, Path or dict), which are applied
            from first to last in the list.

    Notes
    -----
    The following `.rcParams` are not related to style and will be ignored if
    found in a style specification:

    %s
    """
    if isinstance(style, (str, Path)) or hasattr(style, 'keys'):
        # If name is a single str, Path or dict, make it a single element list.
        styles = [style]
    else:
        styles = style

    style_alias = {'mpl20': 'default', 'mpl15': 'classic'}

    for style in styles:
        if isinstance(style, str):
            style = style_alias.get(style, style)
            if style == "default":
                # Deprecation warnings were already handled when creating
                # rcParamsDefault, no need to reemit them here.
                with _api.suppress_matplotlib_deprecation_warning():
                    # don't trigger RcParams.__getitem__('backend')
                    style = {k: rcParamsDefault[k] for k in rcParamsDefault
                             if k not in STYLE_BLACKLIST}
            elif style in library:
                style = library[style]
            elif "." in style:
                pkg, _, name = style.rpartition(".")
                try:
                    path = importlib.resources.files(pkg) / f"{name}.{STYLE_EXTENSION}"
                    style = _rc_params_in_file(path)
                except (ModuleNotFoundError, OSError, TypeError) as exc:
                    # There is an ambiguity whether a dotted name refers to a
                    # package.style_name or to a dotted file path.  Currently,
                    # we silently try the first form and then the second one;
                    # in the future, we may consider forcing file paths to
                    # either use Path objects or be prepended with "./" and use
                    # the slash as marker for file paths.
                    pass
        if isinstance(style, (str, Path)):
            try:
                style = _rc_params_in_file(style)
            except OSError as err:
                raise OSError(
                    f"{style!r} is not a valid package style, path of style "
                    f"file, URL of style file, or library style name (library "
                    f"styles are listed in `style.available`)") from err
        filtered = {}
        for k in style:  # don't trigger RcParams.__getitem__('backend')
            if k in STYLE_BLACKLIST:
                _api.warn_external(
                    f"Style includes a parameter, {k!r}, that is not "
                    f"related to style.  Ignoring this parameter.")
            else:
                filtered[k] = style[k]
        mpl.rcParams.update(filtered)


@contextlib.contextmanager
def context(style, after_reset=False):
    """
    Context manager for using style settings temporarily.

    Parameters
    ----------
    style : str, dict, Path or list
        A style specification. Valid options are:

        str
            - One of the style names in `.style.available` (a builtin style or
              a style installed in the user library path).

            - A dotted name of the form "package.style_name"; in that case,
              "package" should be an importable Python package name, e.g. at
              ``/path/to/package/__init__.py``; the loaded style file is
              ``/path/to/package/style_name.mplstyle``.  (Style files in
              subpackages are likewise supported.)

            - The path or URL to a style file, which gets loaded by
              `.rc_params_from_file`.
        dict
            A mapping of key/value pairs for `matplotlib.rcParams`.

        Path
            The path to a style file, which gets loaded by
            `.rc_params_from_file`.

        list
            A list of style specifiers (str, Path or dict), which are applied
            from first to last in the list.

    after_reset : bool
        If True, apply style after resetting settings to their defaults;
        otherwise, apply style on top of the current settings.
    """
    with mpl.rc_context():
        if after_reset:
            mpl.rcdefaults()
        use(style)
        yield


def update_user_library(library):
    """Update style library with user-defined rc files."""
    for stylelib_path in map(os.path.expanduser, USER_LIBRARY_PATHS):
        styles = read_style_directory(stylelib_path)
        update_nested_dict(library, styles)
    return library


def read_style_directory(style_dir):
    """Return dictionary of styles defined in *style_dir*."""
    styles = dict()
    for path in Path(style_dir).glob(f"*.{STYLE_EXTENSION}"):
        with warnings.catch_warnings(record=True) as warns:
            styles[path.stem] = _rc_params_in_file(path)
        for w in warns:
            _log.warning('In %s: %s', path, w.message)
    return styles


def update_nested_dict(main_dict, new_dict):
    """
    Update nested dict (only level of nesting) with new values.

    Unlike `dict.update`, this assumes that the values of the parent dict are
    dicts (or dict-like), so you shouldn't replace the nested dict if it
    already exists. Instead you should update the sub-dict.
    """
    # update named styles specified by user
    for name, rc_dict in new_dict.items():
        main_dict.setdefault(name, {}).update(rc_dict)
    return main_dict


# Load style library
# ==================
_base_library = read_style_directory(BASE_LIBRARY_PATH)
library = {}
available = []


def reload_library():
    """Reload the style library."""
    library.clear()
    library.update(update_user_library(_base_library))
    available[:] = sorted(library.keys())


reload_library()

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\bracket_parse.py ===
# Natural Language Toolkit: Penn Treebank Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
Corpus reader for corpora that consist of parenthesis-delineated parse trees.
"""

import sys

from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *
from nltk.tag import map_tag
from nltk.tree import Tree

# we use [^\s()]+ instead of \S+? to avoid matching ()
SORTTAGWRD = re.compile(r"\((\d+) ([^\s()]+) ([^\s()]+)\)")
TAGWORD = re.compile(r"\(([^\s()]+) ([^\s()]+)\)")
WORD = re.compile(r"\([^\s()]+ ([^\s()]+)\)")
EMPTY_BRACKETS = re.compile(r"\s*\(\s*\(")


class BracketParseCorpusReader(SyntaxCorpusReader):
    """
    Reader for corpora that consist of parenthesis-delineated parse trees,
    like those found in the "combined" section of the Penn Treebank,
    e.g. "(S (NP (DT the) (JJ little) (NN dog)) (VP (VBD barked)))".

    """

    def __init__(
        self,
        root,
        fileids,
        comment_char=None,
        detect_blocks="unindented_paren",
        encoding="utf8",
        tagset=None,
    ):
        """
        :param root: The root directory for this corpus.
        :param fileids: A list or regexp specifying the fileids in this corpus.
        :param comment_char: The character which can appear at the start of
            a line to indicate that the rest of the line is a comment.
        :param detect_blocks: The method that is used to find blocks
            in the corpus; can be 'unindented_paren' (every unindented
            parenthesis starts a new parse) or 'sexpr' (brackets are
            matched).
        :param tagset: The name of the tagset used by this corpus, to be used
            for normalizing or converting the POS tags returned by the
            ``tagged_...()`` methods.
        """
        SyntaxCorpusReader.__init__(self, root, fileids, encoding)
        self._comment_char = comment_char
        self._detect_blocks = detect_blocks
        self._tagset = tagset

    def _read_block(self, stream):
        if self._detect_blocks == "sexpr":
            return read_sexpr_block(stream, comment_char=self._comment_char)
        elif self._detect_blocks == "blankline":
            return read_blankline_block(stream)
        elif self._detect_blocks == "unindented_paren":
            # Tokens start with unindented left parens.
            toks = read_regexp_block(stream, start_re=r"^\(")
            # Strip any comments out of the tokens.
            if self._comment_char:
                toks = [
                    re.sub("(?m)^%s.*" % re.escape(self._comment_char), "", tok)
                    for tok in toks
                ]
            return toks
        else:
            assert 0, "bad block type"

    def _normalize(self, t):
        # Replace leaves of the form (!), (,), with (! !), (, ,)
        t = re.sub(r"\((.)\)", r"(\1 \1)", t)
        # Replace leaves of the form (tag word root) with (tag word)
        t = re.sub(r"\(([^\s()]+) ([^\s()]+) [^\s()]+\)", r"(\1 \2)", t)
        return t

    def _parse(self, t):
        try:
            tree = Tree.fromstring(self._normalize(t))
            # If there's an empty node at the top, strip it off
            if tree.label() == "" and len(tree) == 1:
                return tree[0]
            else:
                return tree

        except ValueError as e:
            sys.stderr.write("Bad tree detected; trying to recover...\n")
            # Try to recover, if we can:
            if e.args == ("mismatched parens",):
                for n in range(1, 5):
                    try:
                        v = Tree(self._normalize(t + ")" * n))
                        sys.stderr.write(
                            "  Recovered by adding %d close " "paren(s)\n" % n
                        )
                        return v
                    except ValueError:
                        pass
            # Try something else:
            sys.stderr.write("  Recovered by returning a flat parse.\n")
            # sys.stderr.write(' '.join(t.split())+'\n')
            return Tree("S", self._tag(t))

    def _tag(self, t, tagset=None):
        tagged_sent = [(w, p) for (p, w) in TAGWORD.findall(self._normalize(t))]
        if tagset and tagset != self._tagset:
            tagged_sent = [
                (w, map_tag(self._tagset, tagset, p)) for (w, p) in tagged_sent
            ]
        return tagged_sent

    def _word(self, t):
        return WORD.findall(self._normalize(t))


class CategorizedBracketParseCorpusReader(
    CategorizedCorpusReader, BracketParseCorpusReader
):
    """
    A reader for parsed corpora whose documents are
    divided into categories based on their file identifiers.
    @author: Nathan Schneider <nschneid@cs.cmu.edu>
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the corpus reader.  Categorization arguments
        (C{cat_pattern}, C{cat_map}, and C{cat_file}) are passed to
        the L{CategorizedCorpusReader constructor
        <CategorizedCorpusReader.__init__>}.  The remaining arguments
        are passed to the L{BracketParseCorpusReader constructor
        <BracketParseCorpusReader.__init__>}.
        """
        CategorizedCorpusReader.__init__(self, kwargs)
        BracketParseCorpusReader.__init__(self, *args, **kwargs)

    def tagged_words(self, fileids=None, categories=None, tagset=None):
        return super().tagged_words(self._resolve(fileids, categories), tagset)

    def tagged_sents(self, fileids=None, categories=None, tagset=None):
        return super().tagged_sents(self._resolve(fileids, categories), tagset)

    def tagged_paras(self, fileids=None, categories=None, tagset=None):
        return super().tagged_paras(self._resolve(fileids, categories), tagset)

    def parsed_words(self, fileids=None, categories=None):
        return super().parsed_words(self._resolve(fileids, categories))

    def parsed_sents(self, fileids=None, categories=None):
        return super().parsed_sents(self._resolve(fileids, categories))

    def parsed_paras(self, fileids=None, categories=None):
        return super().parsed_paras(self._resolve(fileids, categories))


class AlpinoCorpusReader(BracketParseCorpusReader):
    """
    Reader for the Alpino Dutch Treebank.
    This corpus has a lexical breakdown structure embedded, as read by `_parse`
    Unfortunately this puts punctuation and some other words out of the sentence
    order in the xml element tree. This is no good for `tag_` and `word_`
    `_tag` and `_word` will be overridden to use a non-default new parameter 'ordered'
    to the overridden _normalize function. The _parse function can then remain
    untouched.
    """

    def __init__(self, root, encoding="ISO-8859-1", tagset=None):
        BracketParseCorpusReader.__init__(
            self,
            root,
            r"alpino\.xml",
            detect_blocks="blankline",
            encoding=encoding,
            tagset=tagset,
        )

    def _normalize(self, t, ordered=False):
        """Normalize the xml sentence element in t.
        The sentence elements <alpino_ds>, although embedded in a few overall
        xml elements, are separated by blank lines. That's how the reader can
        deliver them one at a time.
        Each sentence has a few category subnodes that are of no use to us.
        The remaining word nodes may or may not appear in the proper order.
        Each word node has attributes, among which:
        - begin : the position of the word in the sentence
        - pos   : Part of Speech: the Tag
        - word  : the actual word
        The return value is a string with all xml elementes replaced by
        clauses: either a cat clause with nested clauses, or a word clause.
        The order of the bracket clauses closely follows the xml.
        If ordered == True, the word clauses include an order sequence number.
        If ordered == False, the word clauses only have pos and word parts.
        """
        if t[:10] != "<alpino_ds":
            return ""
        # convert XML to sexpr notation
        t = re.sub(r'  <node .*? cat="(\w+)".*>', r"(\1", t)
        if ordered:
            t = re.sub(
                r'  <node. *?begin="(\d+)".*? pos="(\w+)".*? word="([^"]+)".*?/>',
                r"(\1 \2 \3)",
                t,
            )
        else:
            t = re.sub(r'  <node .*?pos="(\w+)".*? word="([^"]+)".*?/>', r"(\1 \2)", t)
        t = re.sub(r"  </node>", r")", t)
        t = re.sub(r"<sentence>.*</sentence>", r"", t)
        t = re.sub(r"</?alpino_ds.*>", r"", t)
        return t

    def _tag(self, t, tagset=None):
        tagged_sent = [
            (int(o), w, p)
            for (o, p, w) in SORTTAGWRD.findall(self._normalize(t, ordered=True))
        ]
        tagged_sent.sort()
        if tagset and tagset != self._tagset:
            tagged_sent = [
                (w, map_tag(self._tagset, tagset, p)) for (o, w, p) in tagged_sent
            ]
        else:
            tagged_sent = [(w, p) for (o, w, p) in tagged_sent]
        return tagged_sent

    def _word(self, t):
        """Return a correctly ordered list if words"""
        tagged_sent = self._tag(t)
        return [w for (w, p) in tagged_sent]