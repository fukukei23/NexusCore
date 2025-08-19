
# === NexusCore/openenv\Lib\site-packages\httpcore\_models.py ===
from __future__ import annotations

import base64
import ssl
import typing
import urllib.parse

# Functions for typechecking...


ByteOrStr = typing.Union[bytes, str]
HeadersAsSequence = typing.Sequence[typing.Tuple[ByteOrStr, ByteOrStr]]
HeadersAsMapping = typing.Mapping[ByteOrStr, ByteOrStr]
HeaderTypes = typing.Union[HeadersAsSequence, HeadersAsMapping, None]

Extensions = typing.MutableMapping[str, typing.Any]


def enforce_bytes(value: bytes | str, *, name: str) -> bytes:
    """
    Any arguments that are ultimately represented as bytes can be specified
    either as bytes or as strings.

    However we enforce that any string arguments must only contain characters in
    the plain ASCII range. chr(0)...chr(127). If you need to use characters
    outside that range then be precise, and use a byte-wise argument.
    """
    if isinstance(value, str):
        try:
            return value.encode("ascii")
        except UnicodeEncodeError:
            raise TypeError(f"{name} strings may not include unicode characters.")
    elif isinstance(value, bytes):
        return value

    seen_type = type(value).__name__
    raise TypeError(f"{name} must be bytes or str, but got {seen_type}.")


def enforce_url(value: URL | bytes | str, *, name: str) -> URL:
    """
    Type check for URL parameters.
    """
    if isinstance(value, (bytes, str)):
        return URL(value)
    elif isinstance(value, URL):
        return value

    seen_type = type(value).__name__
    raise TypeError(f"{name} must be a URL, bytes, or str, but got {seen_type}.")


def enforce_headers(
    value: HeadersAsMapping | HeadersAsSequence | None = None, *, name: str
) -> list[tuple[bytes, bytes]]:
    """
    Convienence function that ensure all items in request or response headers
    are either bytes or strings in the plain ASCII range.
    """
    if value is None:
        return []
    elif isinstance(value, typing.Mapping):
        return [
            (
                enforce_bytes(k, name="header name"),
                enforce_bytes(v, name="header value"),
            )
            for k, v in value.items()
        ]
    elif isinstance(value, typing.Sequence):
        return [
            (
                enforce_bytes(k, name="header name"),
                enforce_bytes(v, name="header value"),
            )
            for k, v in value
        ]

    seen_type = type(value).__name__
    raise TypeError(
        f"{name} must be a mapping or sequence of two-tuples, but got {seen_type}."
    )


def enforce_stream(
    value: bytes | typing.Iterable[bytes] | typing.AsyncIterable[bytes] | None,
    *,
    name: str,
) -> typing.Iterable[bytes] | typing.AsyncIterable[bytes]:
    if value is None:
        return ByteStream(b"")
    elif isinstance(value, bytes):
        return ByteStream(value)
    return value


# * https://tools.ietf.org/html/rfc3986#section-3.2.3
# * https://url.spec.whatwg.org/#url-miscellaneous
# * https://url.spec.whatwg.org/#scheme-state
DEFAULT_PORTS = {
    b"ftp": 21,
    b"http": 80,
    b"https": 443,
    b"ws": 80,
    b"wss": 443,
}


def include_request_headers(
    headers: list[tuple[bytes, bytes]],
    *,
    url: "URL",
    content: None | bytes | typing.Iterable[bytes] | typing.AsyncIterable[bytes],
) -> list[tuple[bytes, bytes]]:
    headers_set = set(k.lower() for k, v in headers)

    if b"host" not in headers_set:
        default_port = DEFAULT_PORTS.get(url.scheme)
        if url.port is None or url.port == default_port:
            header_value = url.host
        else:
            header_value = b"%b:%d" % (url.host, url.port)
        headers = [(b"Host", header_value)] + headers

    if (
        content is not None
        and b"content-length" not in headers_set
        and b"transfer-encoding" not in headers_set
    ):
        if isinstance(content, bytes):
            content_length = str(len(content)).encode("ascii")
            headers += [(b"Content-Length", content_length)]
        else:
            headers += [(b"Transfer-Encoding", b"chunked")]  # pragma: nocover

    return headers


# Interfaces for byte streams...


class ByteStream:
    """
    A container for non-streaming content, and that supports both sync and async
    stream iteration.
    """

    def __init__(self, content: bytes) -> None:
        self._content = content

    def __iter__(self) -> typing.Iterator[bytes]:
        yield self._content

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield self._content

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} [{len(self._content)} bytes]>"


class Origin:
    def __init__(self, scheme: bytes, host: bytes, port: int) -> None:
        self.scheme = scheme
        self.host = host
        self.port = port

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, Origin)
            and self.scheme == other.scheme
            and self.host == other.host
            and self.port == other.port
        )

    def __str__(self) -> str:
        scheme = self.scheme.decode("ascii")
        host = self.host.decode("ascii")
        port = str(self.port)
        return f"{scheme}://{host}:{port}"


class URL:
    """
    Represents the URL against which an HTTP request may be made.

    The URL may either be specified as a plain string, for convienence:

    ```python
    url = httpcore.URL("https://www.example.com/")
    ```

    Or be constructed with explicitily pre-parsed components:

    ```python
    url = httpcore.URL(scheme=b'https', host=b'www.example.com', port=None, target=b'/')
    ```

    Using this second more explicit style allows integrations that are using
    `httpcore` to pass through URLs that have already been parsed in order to use
    libraries such as `rfc-3986` rather than relying on the stdlib. It also ensures
    that URL parsing is treated identically at both the networking level and at any
    higher layers of abstraction.

    The four components are important here, as they allow the URL to be precisely
    specified in a pre-parsed format. They also allow certain types of request to
    be created that could not otherwise be expressed.

    For example, an HTTP request to `http://www.example.com/` forwarded via a proxy
    at `http://localhost:8080`...

    ```python
    # Constructs an HTTP request with a complete URL as the target:
    # GET https://www.example.com/ HTTP/1.1
    url = httpcore.URL(
        scheme=b'http',
        host=b'localhost',
        port=8080,
        target=b'https://www.example.com/'
    )
    request = httpcore.Request(
        method="GET",
        url=url
    )
    ```

    Another example is constructing an `OPTIONS *` request...

    ```python
    # Constructs an 'OPTIONS *' HTTP request:
    # OPTIONS * HTTP/1.1
    url = httpcore.URL(scheme=b'https', host=b'www.example.com', target=b'*')
    request = httpcore.Request(method="OPTIONS", url=url)
    ```

    This kind of request is not possible to formulate with a URL string,
    because the `/` delimiter is always used to demark the target from the
    host/port portion of the URL.

    For convenience, string-like arguments may be specified either as strings or
    as bytes. However, once a request is being issue over-the-wire, the URL
    components are always ultimately required to be a bytewise representation.

    In order to avoid any ambiguity over character encodings, when strings are used
    as arguments, they must be strictly limited to the ASCII range `chr(0)`-`chr(127)`.
    If you require a bytewise representation that is outside this range you must
    handle the character encoding directly, and pass a bytes instance.
    """

    def __init__(
        self,
        url: bytes | str = "",
        *,
        scheme: bytes | str = b"",
        host: bytes | str = b"",
        port: int | None = None,
        target: bytes | str = b"",
    ) -> None:
        """
        Parameters:
            url: The complete URL as a string or bytes.
            scheme: The URL scheme as a string or bytes.
                Typically either `"http"` or `"https"`.
            host: The URL host as a string or bytes. Such as `"www.example.com"`.
            port: The port to connect to. Either an integer or `None`.
            target: The target of the HTTP request. Such as `"/items?search=red"`.
        """
        if url:
            parsed = urllib.parse.urlparse(enforce_bytes(url, name="url"))
            self.scheme = parsed.scheme
            self.host = parsed.hostname or b""
            self.port = parsed.port
            self.target = (parsed.path or b"/") + (
                b"?" + parsed.query if parsed.query else b""
            )
        else:
            self.scheme = enforce_bytes(scheme, name="scheme")
            self.host = enforce_bytes(host, name="host")
            self.port = port
            self.target = enforce_bytes(target, name="target")

    @property
    def origin(self) -> Origin:
        default_port = {
            b"http": 80,
            b"https": 443,
            b"ws": 80,
            b"wss": 443,
            b"socks5": 1080,
            b"socks5h": 1080,
        }[self.scheme]
        return Origin(
            scheme=self.scheme, host=self.host, port=self.port or default_port
        )

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, URL)
            and other.scheme == self.scheme
            and other.host == self.host
            and other.port == self.port
            and other.target == self.target
        )

    def __bytes__(self) -> bytes:
        if self.port is None:
            return b"%b://%b%b" % (self.scheme, self.host, self.target)
        return b"%b://%b:%d%b" % (self.scheme, self.host, self.port, self.target)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(scheme={self.scheme!r}, "
            f"host={self.host!r}, port={self.port!r}, target={self.target!r})"
        )


class Request:
    """
    An HTTP request.
    """

    def __init__(
        self,
        method: bytes | str,
        url: URL | bytes | str,
        *,
        headers: HeaderTypes = None,
        content: bytes
        | typing.Iterable[bytes]
        | typing.AsyncIterable[bytes]
        | None = None,
        extensions: Extensions | None = None,
    ) -> None:
        """
        Parameters:
            method: The HTTP request method, either as a string or bytes.
                For example: `GET`.
            url: The request URL, either as a `URL` instance, or as a string or bytes.
                For example: `"https://www.example.com".`
            headers: The HTTP request headers.
            content: The content of the request body.
            extensions: A dictionary of optional extra information included on
                the request. Possible keys include `"timeout"`, and `"trace"`.
        """
        self.method: bytes = enforce_bytes(method, name="method")
        self.url: URL = enforce_url(url, name="url")
        self.headers: list[tuple[bytes, bytes]] = enforce_headers(
            headers, name="headers"
        )
        self.stream: typing.Iterable[bytes] | typing.AsyncIterable[bytes] = (
            enforce_stream(content, name="content")
        )
        self.extensions = {} if extensions is None else extensions

        if "target" in self.extensions:
            self.url = URL(
                scheme=self.url.scheme,
                host=self.url.host,
                port=self.url.port,
                target=self.extensions["target"],
            )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} [{self.method!r}]>"


class Response:
    """
    An HTTP response.
    """

    def __init__(
        self,
        status: int,
        *,
        headers: HeaderTypes = None,
        content: bytes
        | typing.Iterable[bytes]
        | typing.AsyncIterable[bytes]
        | None = None,
        extensions: Extensions | None = None,
    ) -> None:
        """
        Parameters:
            status: The HTTP status code of the response. For example `200`.
            headers: The HTTP response headers.
            content: The content of the response body.
            extensions: A dictionary of optional extra information included on
                the responseself.Possible keys include `"http_version"`,
                `"reason_phrase"`, and `"network_stream"`.
        """
        self.status: int = status
        self.headers: list[tuple[bytes, bytes]] = enforce_headers(
            headers, name="headers"
        )
        self.stream: typing.Iterable[bytes] | typing.AsyncIterable[bytes] = (
            enforce_stream(content, name="content")
        )
        self.extensions = {} if extensions is None else extensions

        self._stream_consumed = False

    @property
    def content(self) -> bytes:
        if not hasattr(self, "_content"):
            if isinstance(self.stream, typing.Iterable):
                raise RuntimeError(
                    "Attempted to access 'response.content' on a streaming response. "
                    "Call 'response.read()' first."
                )
            else:
                raise RuntimeError(
                    "Attempted to access 'response.content' on a streaming response. "
                    "Call 'await response.aread()' first."
                )
        return self._content

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} [{self.status}]>"

    # Sync interface...

    def read(self) -> bytes:
        if not isinstance(self.stream, typing.Iterable):  # pragma: nocover
            raise RuntimeError(
                "Attempted to read an asynchronous response using 'response.read()'. "
                "You should use 'await response.aread()' instead."
            )
        if not hasattr(self, "_content"):
            self._content = b"".join([part for part in self.iter_stream()])
        return self._content

    def iter_stream(self) -> typing.Iterator[bytes]:
        if not isinstance(self.stream, typing.Iterable):  # pragma: nocover
            raise RuntimeError(
                "Attempted to stream an asynchronous response using 'for ... in "
                "response.iter_stream()'. "
                "You should use 'async for ... in response.aiter_stream()' instead."
            )
        if self._stream_consumed:
            raise RuntimeError(
                "Attempted to call 'for ... in response.iter_stream()' more than once."
            )
        self._stream_consumed = True
        for chunk in self.stream:
            yield chunk

    def close(self) -> None:
        if not isinstance(self.stream, typing.Iterable):  # pragma: nocover
            raise RuntimeError(
                "Attempted to close an asynchronous response using 'response.close()'. "
                "You should use 'await response.aclose()' instead."
            )
        if hasattr(self.stream, "close"):
            self.stream.close()

    # Async interface...

    async def aread(self) -> bytes:
        if not isinstance(self.stream, typing.AsyncIterable):  # pragma: nocover
            raise RuntimeError(
                "Attempted to read an synchronous response using "
                "'await response.aread()'. "
                "You should use 'response.read()' instead."
            )
        if not hasattr(self, "_content"):
            self._content = b"".join([part async for part in self.aiter_stream()])
        return self._content

    async def aiter_stream(self) -> typing.AsyncIterator[bytes]:
        if not isinstance(self.stream, typing.AsyncIterable):  # pragma: nocover
            raise RuntimeError(
                "Attempted to stream an synchronous response using 'async for ... in "
                "response.aiter_stream()'. "
                "You should use 'for ... in response.iter_stream()' instead."
            )
        if self._stream_consumed:
            raise RuntimeError(
                "Attempted to call 'async for ... in response.aiter_stream()' "
                "more than once."
            )
        self._stream_consumed = True
        async for chunk in self.stream:
            yield chunk

    async def aclose(self) -> None:
        if not isinstance(self.stream, typing.AsyncIterable):  # pragma: nocover
            raise RuntimeError(
                "Attempted to close a synchronous response using "
                "'await response.aclose()'. "
                "You should use 'response.close()' instead."
            )
        if hasattr(self.stream, "aclose"):
            await self.stream.aclose()


class Proxy:
    def __init__(
        self,
        url: URL | bytes | str,
        auth: tuple[bytes | str, bytes | str] | None = None,
        headers: HeadersAsMapping | HeadersAsSequence | None = None,
        ssl_context: ssl.SSLContext | None = None,
    ):
        self.url = enforce_url(url, name="url")
        self.headers = enforce_headers(headers, name="headers")
        self.ssl_context = ssl_context

        if auth is not None:
            username = enforce_bytes(auth[0], name="auth")
            password = enforce_bytes(auth[1], name="auth")
            userpass = username + b":" + password
            authorization = b"Basic " + base64.b64encode(userpass)
            self.auth: tuple[bytes, bytes] | None = (username, password)
            self.headers = [(b"Proxy-Authorization", authorization)] + self.headers
        else:
            self.auth = None

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\transform.py ===
"""Affine 2D transformation matrix class.

The Transform class implements various transformation matrix operations,
both on the matrix itself, as well as on 2D coordinates.

Transform instances are effectively immutable: all methods that operate on the
transformation itself always return a new instance. This has as the
interesting side effect that Transform instances are hashable, ie. they can be
used as dictionary keys.

This module exports the following symbols:

Transform
	this is the main class
Identity
	Transform instance set to the identity transformation
Offset
	Convenience function that returns a translating transformation
Scale
	Convenience function that returns a scaling transformation

The DecomposedTransform class implements a transformation with separate
translate, rotation, scale, skew, and transformation-center components.

:Example:

	>>> t = Transform(2, 0, 0, 3, 0, 0)
	>>> t.transformPoint((100, 100))
	(200, 300)
	>>> t = Scale(2, 3)
	>>> t.transformPoint((100, 100))
	(200, 300)
	>>> t.transformPoint((0, 0))
	(0, 0)
	>>> t = Offset(2, 3)
	>>> t.transformPoint((100, 100))
	(102, 103)
	>>> t.transformPoint((0, 0))
	(2, 3)
	>>> t2 = t.scale(0.5)
	>>> t2.transformPoint((100, 100))
	(52.0, 53.0)
	>>> import math
	>>> t3 = t2.rotate(math.pi / 2)
	>>> t3.transformPoint((0, 0))
	(2.0, 3.0)
	>>> t3.transformPoint((100, 100))
	(-48.0, 53.0)
	>>> t = Identity.scale(0.5).translate(100, 200).skew(0.1, 0.2)
	>>> t.transformPoints([(0, 0), (1, 1), (100, 100)])
	[(50.0, 100.0), (50.550167336042726, 100.60135501775433), (105.01673360427253, 160.13550177543362)]
	>>>
"""

from __future__ import annotations

import math
from typing import NamedTuple
from dataclasses import dataclass


__all__ = ["Transform", "Identity", "Offset", "Scale", "DecomposedTransform"]


_EPSILON = 1e-15
_ONE_EPSILON = 1 - _EPSILON
_MINUS_ONE_EPSILON = -1 + _EPSILON


def _normSinCos(v: float) -> float:
    if abs(v) < _EPSILON:
        v = 0
    elif v > _ONE_EPSILON:
        v = 1
    elif v < _MINUS_ONE_EPSILON:
        v = -1
    return v


class Transform(NamedTuple):
    """2x2 transformation matrix plus offset, a.k.a. Affine transform.
    Transform instances are immutable: all transforming methods, eg.
    rotate(), return a new Transform instance.

    :Example:

            >>> t = Transform()
            >>> t
            <Transform [1 0 0 1 0 0]>
            >>> t.scale(2)
            <Transform [2 0 0 2 0 0]>
            >>> t.scale(2.5, 5.5)
            <Transform [2.5 0 0 5.5 0 0]>
            >>>
            >>> t.scale(2, 3).transformPoint((100, 100))
            (200, 300)

    Transform's constructor takes six arguments, all of which are
    optional, and can be used as keyword arguments::

            >>> Transform(12)
            <Transform [12 0 0 1 0 0]>
            >>> Transform(dx=12)
            <Transform [1 0 0 1 12 0]>
            >>> Transform(yx=12)
            <Transform [1 0 12 1 0 0]>

    Transform instances also behave like sequences of length 6::

            >>> len(Identity)
            6
            >>> list(Identity)
            [1, 0, 0, 1, 0, 0]
            >>> tuple(Identity)
            (1, 0, 0, 1, 0, 0)

    Transform instances are comparable::

            >>> t1 = Identity.scale(2, 3).translate(4, 6)
            >>> t2 = Identity.translate(8, 18).scale(2, 3)
            >>> t1 == t2
            1

    But beware of floating point rounding errors::

            >>> t1 = Identity.scale(0.2, 0.3).translate(0.4, 0.6)
            >>> t2 = Identity.translate(0.08, 0.18).scale(0.2, 0.3)
            >>> t1
            <Transform [0.2 0 0 0.3 0.08 0.18]>
            >>> t2
            <Transform [0.2 0 0 0.3 0.08 0.18]>
            >>> t1 == t2
            0

    Transform instances are hashable, meaning you can use them as
    keys in dictionaries::

            >>> d = {Scale(12, 13): None}
            >>> d
            {<Transform [12 0 0 13 0 0]>: None}

    But again, beware of floating point rounding errors::

            >>> t1 = Identity.scale(0.2, 0.3).translate(0.4, 0.6)
            >>> t2 = Identity.translate(0.08, 0.18).scale(0.2, 0.3)
            >>> t1
            <Transform [0.2 0 0 0.3 0.08 0.18]>
            >>> t2
            <Transform [0.2 0 0 0.3 0.08 0.18]>
            >>> d = {t1: None}
            >>> d
            {<Transform [0.2 0 0 0.3 0.08 0.18]>: None}
            >>> d[t2]
            Traceback (most recent call last):
              File "<stdin>", line 1, in ?
            KeyError: <Transform [0.2 0 0 0.3 0.08 0.18]>
    """

    xx: float = 1
    xy: float = 0
    yx: float = 0
    yy: float = 1
    dx: float = 0
    dy: float = 0

    def transformPoint(self, p):
        """Transform a point.

        :Example:

                >>> t = Transform()
                >>> t = t.scale(2.5, 5.5)
                >>> t.transformPoint((100, 100))
                (250.0, 550.0)
        """
        (x, y) = p
        xx, xy, yx, yy, dx, dy = self
        return (xx * x + yx * y + dx, xy * x + yy * y + dy)

    def transformPoints(self, points):
        """Transform a list of points.

        :Example:

                >>> t = Scale(2, 3)
                >>> t.transformPoints([(0, 0), (0, 100), (100, 100), (100, 0)])
                [(0, 0), (0, 300), (200, 300), (200, 0)]
                >>>
        """
        xx, xy, yx, yy, dx, dy = self
        return [(xx * x + yx * y + dx, xy * x + yy * y + dy) for x, y in points]

    def transformVector(self, v):
        """Transform an (dx, dy) vector, treating translation as zero.

        :Example:

                >>> t = Transform(2, 0, 0, 2, 10, 20)
                >>> t.transformVector((3, -4))
                (6, -8)
                >>>
        """
        (dx, dy) = v
        xx, xy, yx, yy = self[:4]
        return (xx * dx + yx * dy, xy * dx + yy * dy)

    def transformVectors(self, vectors):
        """Transform a list of (dx, dy) vector, treating translation as zero.

        :Example:
                >>> t = Transform(2, 0, 0, 2, 10, 20)
                >>> t.transformVectors([(3, -4), (5, -6)])
                [(6, -8), (10, -12)]
                >>>
        """
        xx, xy, yx, yy = self[:4]
        return [(xx * dx + yx * dy, xy * dx + yy * dy) for dx, dy in vectors]

    def translate(self, x: float = 0, y: float = 0):
        """Return a new transformation, translated (offset) by x, y.

        :Example:
                >>> t = Transform()
                >>> t.translate(20, 30)
                <Transform [1 0 0 1 20 30]>
                >>>
        """
        return self.transform((1, 0, 0, 1, x, y))

    def scale(self, x: float = 1, y: float | None = None):
        """Return a new transformation, scaled by x, y. The 'y' argument
        may be None, which implies to use the x value for y as well.

        :Example:
                >>> t = Transform()
                >>> t.scale(5)
                <Transform [5 0 0 5 0 0]>
                >>> t.scale(5, 6)
                <Transform [5 0 0 6 0 0]>
                >>>
        """
        if y is None:
            y = x
        return self.transform((x, 0, 0, y, 0, 0))

    def rotate(self, angle: float):
        """Return a new transformation, rotated by 'angle' (radians).

        :Example:
                >>> import math
                >>> t = Transform()
                >>> t.rotate(math.pi / 2)
                <Transform [0 1 -1 0 0 0]>
                >>>
        """
        c = _normSinCos(math.cos(angle))
        s = _normSinCos(math.sin(angle))
        return self.transform((c, s, -s, c, 0, 0))

    def skew(self, x: float = 0, y: float = 0):
        """Return a new transformation, skewed by x and y.

        :Example:
                >>> import math
                >>> t = Transform()
                >>> t.skew(math.pi / 4)
                <Transform [1 0 1 1 0 0]>
                >>>
        """
        return self.transform((1, math.tan(y), math.tan(x), 1, 0, 0))

    def transform(self, other):
        """Return a new transformation, transformed by another
        transformation.

        :Example:
                >>> t = Transform(2, 0, 0, 3, 1, 6)
                >>> t.transform((4, 3, 2, 1, 5, 6))
                <Transform [8 9 4 3 11 24]>
                >>>
        """
        xx1, xy1, yx1, yy1, dx1, dy1 = other
        xx2, xy2, yx2, yy2, dx2, dy2 = self
        return self.__class__(
            xx1 * xx2 + xy1 * yx2,
            xx1 * xy2 + xy1 * yy2,
            yx1 * xx2 + yy1 * yx2,
            yx1 * xy2 + yy1 * yy2,
            xx2 * dx1 + yx2 * dy1 + dx2,
            xy2 * dx1 + yy2 * dy1 + dy2,
        )

    def reverseTransform(self, other):
        """Return a new transformation, which is the other transformation
        transformed by self. self.reverseTransform(other) is equivalent to
        other.transform(self).

        :Example:
                >>> t = Transform(2, 0, 0, 3, 1, 6)
                >>> t.reverseTransform((4, 3, 2, 1, 5, 6))
                <Transform [8 6 6 3 21 15]>
                >>> Transform(4, 3, 2, 1, 5, 6).transform((2, 0, 0, 3, 1, 6))
                <Transform [8 6 6 3 21 15]>
                >>>
        """
        xx1, xy1, yx1, yy1, dx1, dy1 = self
        xx2, xy2, yx2, yy2, dx2, dy2 = other
        return self.__class__(
            xx1 * xx2 + xy1 * yx2,
            xx1 * xy2 + xy1 * yy2,
            yx1 * xx2 + yy1 * yx2,
            yx1 * xy2 + yy1 * yy2,
            xx2 * dx1 + yx2 * dy1 + dx2,
            xy2 * dx1 + yy2 * dy1 + dy2,
        )

    def inverse(self):
        """Return the inverse transformation.

        :Example:
                >>> t = Identity.translate(2, 3).scale(4, 5)
                >>> t.transformPoint((10, 20))
                (42, 103)
                >>> it = t.inverse()
                >>> it.transformPoint((42, 103))
                (10.0, 20.0)
                >>>
        """
        if self == Identity:
            return self
        xx, xy, yx, yy, dx, dy = self
        det = xx * yy - yx * xy
        xx, xy, yx, yy = yy / det, -xy / det, -yx / det, xx / det
        dx, dy = -xx * dx - yx * dy, -xy * dx - yy * dy
        return self.__class__(xx, xy, yx, yy, dx, dy)

    def toPS(self) -> str:
        """Return a PostScript representation

        :Example:

                >>> t = Identity.scale(2, 3).translate(4, 5)
                >>> t.toPS()
                '[2 0 0 3 8 15]'
                >>>
        """
        return "[%s %s %s %s %s %s]" % self

    def toDecomposed(self) -> "DecomposedTransform":
        """Decompose into a DecomposedTransform."""
        return DecomposedTransform.fromTransform(self)

    def __bool__(self) -> bool:
        """Returns True if transform is not identity, False otherwise.

        :Example:

                >>> bool(Identity)
                False
                >>> bool(Transform())
                False
                >>> bool(Scale(1.))
                False
                >>> bool(Scale(2))
                True
                >>> bool(Offset())
                False
                >>> bool(Offset(0))
                False
                >>> bool(Offset(2))
                True
        """
        return self != Identity

    def __repr__(self) -> str:
        return "<%s [%g %g %g %g %g %g]>" % ((self.__class__.__name__,) + self)


Identity = Transform()


def Offset(x: float = 0, y: float = 0) -> Transform:
    """Return the identity transformation offset by x, y.

    :Example:
            >>> Offset(2, 3)
            <Transform [1 0 0 1 2 3]>
            >>>
    """
    return Transform(1, 0, 0, 1, x, y)


def Scale(x: float, y: float | None = None) -> Transform:
    """Return the identity transformation scaled by x, y. The 'y' argument
    may be None, which implies to use the x value for y as well.

    :Example:
            >>> Scale(2, 3)
            <Transform [2 0 0 3 0 0]>
            >>>
    """
    if y is None:
        y = x
    return Transform(x, 0, 0, y, 0, 0)


@dataclass
class DecomposedTransform:
    """The DecomposedTransform class implements a transformation with separate
    translate, rotation, scale, skew, and transformation-center components.
    """

    translateX: float = 0
    translateY: float = 0
    rotation: float = 0  # in degrees, counter-clockwise
    scaleX: float = 1
    scaleY: float = 1
    skewX: float = 0  # in degrees, clockwise
    skewY: float = 0  # in degrees, counter-clockwise
    tCenterX: float = 0
    tCenterY: float = 0

    def __bool__(self):
        return (
            self.translateX != 0
            or self.translateY != 0
            or self.rotation != 0
            or self.scaleX != 1
            or self.scaleY != 1
            or self.skewX != 0
            or self.skewY != 0
            or self.tCenterX != 0
            or self.tCenterY != 0
        )

    @classmethod
    def fromTransform(self, transform):
        """Return a DecomposedTransform() equivalent of this transformation.
        The returned solution always has skewY = 0, and angle in the (-180, 180].

        :Example:
                >>> DecomposedTransform.fromTransform(Transform(3, 0, 0, 2, 0, 0))
                DecomposedTransform(translateX=0, translateY=0, rotation=0.0, scaleX=3.0, scaleY=2.0, skewX=0.0, skewY=0.0, tCenterX=0, tCenterY=0)
                >>> DecomposedTransform.fromTransform(Transform(0, 0, 0, 1, 0, 0))
                DecomposedTransform(translateX=0, translateY=0, rotation=0.0, scaleX=0.0, scaleY=1.0, skewX=0.0, skewY=0.0, tCenterX=0, tCenterY=0)
                >>> DecomposedTransform.fromTransform(Transform(0, 0, 1, 1, 0, 0))
                DecomposedTransform(translateX=0, translateY=0, rotation=-45.0, scaleX=0.0, scaleY=1.4142135623730951, skewX=0.0, skewY=0.0, tCenterX=0, tCenterY=0)
        """
        # Adapted from an answer on
        # https://math.stackexchange.com/questions/13150/extracting-rotation-scale-values-from-2d-transformation-matrix

        a, b, c, d, x, y = transform

        sx = math.copysign(1, a)
        if sx < 0:
            a *= sx
            b *= sx

        delta = a * d - b * c

        rotation = 0
        scaleX = scaleY = 0
        skewX = 0

        # Apply the QR-like decomposition.
        if a != 0 or b != 0:
            r = math.sqrt(a * a + b * b)
            rotation = math.acos(a / r) if b >= 0 else -math.acos(a / r)
            scaleX, scaleY = (r, delta / r)
            skewX = math.atan((a * c + b * d) / (r * r))
        elif c != 0 or d != 0:
            s = math.sqrt(c * c + d * d)
            rotation = math.pi / 2 - (
                math.acos(-c / s) if d >= 0 else -math.acos(c / s)
            )
            scaleX, scaleY = (delta / s, s)
        else:
            # a = b = c = d = 0
            pass

        return DecomposedTransform(
            x,
            y,
            math.degrees(rotation),
            scaleX * sx,
            scaleY,
            math.degrees(skewX) * sx,
            0.0,
            0,
            0,
        )

    def toTransform(self) -> Transform:
        """Return the Transform() equivalent of this transformation.

        :Example:
                >>> DecomposedTransform(scaleX=2, scaleY=2).toTransform()
                <Transform [2 0 0 2 0 0]>
                >>>
        """
        t = Transform()
        t = t.translate(
            self.translateX + self.tCenterX, self.translateY + self.tCenterY
        )
        t = t.rotate(math.radians(self.rotation))
        t = t.scale(self.scaleX, self.scaleY)
        t = t.skew(math.radians(self.skewX), math.radians(self.skewY))
        t = t.translate(-self.tCenterX, -self.tCenterY)
        return t


if __name__ == "__main__":
    import sys
    import doctest

    sys.exit(doctest.testmod().failed)

# === NexusCore/openenv\Lib\site-packages\PIL\BmpImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# BMP file handler
#
# Windows (and OS/2) native bitmap storage format.
#
# history:
# 1995-09-01 fl   Created
# 1996-04-30 fl   Added save
# 1997-08-27 fl   Fixed save of 1-bit images
# 1998-03-06 fl   Load P images as L where possible
# 1998-07-03 fl   Load P images as 1 where possible
# 1998-12-29 fl   Handle small palettes
# 2002-12-30 fl   Fixed load of 1-bit palette images
# 2003-04-21 fl   Fixed load of 1-bit monochrome images
# 2003-04-23 fl   Added limited support for BI_BITFIELDS compression
#
# Copyright (c) 1997-2003 by Secret Labs AB
# Copyright (c) 1995-2003 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import os
from typing import IO, Any

from . import Image, ImageFile, ImagePalette
from ._binary import i16le as i16
from ._binary import i32le as i32
from ._binary import o8
from ._binary import o16le as o16
from ._binary import o32le as o32

#
# --------------------------------------------------------------------
# Read BMP file

BIT2MODE = {
    # bits => mode, rawmode
    1: ("P", "P;1"),
    4: ("P", "P;4"),
    8: ("P", "P"),
    16: ("RGB", "BGR;15"),
    24: ("RGB", "BGR"),
    32: ("RGB", "BGRX"),
}

USE_RAW_ALPHA = False


def _accept(prefix: bytes) -> bool:
    return prefix.startswith(b"BM")


def _dib_accept(prefix: bytes) -> bool:
    return i32(prefix) in [12, 40, 52, 56, 64, 108, 124]


# =============================================================================
# Image plugin for the Windows BMP format.
# =============================================================================
class BmpImageFile(ImageFile.ImageFile):
    """Image plugin for the Windows Bitmap format (BMP)"""

    # ------------------------------------------------------------- Description
    format_description = "Windows Bitmap"
    format = "BMP"

    # -------------------------------------------------- BMP Compression values
    COMPRESSIONS = {"RAW": 0, "RLE8": 1, "RLE4": 2, "BITFIELDS": 3, "JPEG": 4, "PNG": 5}
    for k, v in COMPRESSIONS.items():
        vars()[k] = v

    def _bitmap(self, header: int = 0, offset: int = 0) -> None:
        """Read relevant info about the BMP"""
        read, seek = self.fp.read, self.fp.seek
        if header:
            seek(header)
        # read bmp header size @offset 14 (this is part of the header size)
        file_info: dict[str, bool | int | tuple[int, ...]] = {
            "header_size": i32(read(4)),
            "direction": -1,
        }

        # -------------------- If requested, read header at a specific position
        # read the rest of the bmp header, without its size
        assert isinstance(file_info["header_size"], int)
        header_data = ImageFile._safe_read(self.fp, file_info["header_size"] - 4)

        # ------------------------------- Windows Bitmap v2, IBM OS/2 Bitmap v1
        # ----- This format has different offsets because of width/height types
        # 12: BITMAPCOREHEADER/OS21XBITMAPHEADER
        if file_info["header_size"] == 12:
            file_info["width"] = i16(header_data, 0)
            file_info["height"] = i16(header_data, 2)
            file_info["planes"] = i16(header_data, 4)
            file_info["bits"] = i16(header_data, 6)
            file_info["compression"] = self.COMPRESSIONS["RAW"]
            file_info["palette_padding"] = 3

        # --------------------------------------------- Windows Bitmap v3 to v5
        #  40: BITMAPINFOHEADER
        #  52: BITMAPV2HEADER
        #  56: BITMAPV3HEADER
        #  64: BITMAPCOREHEADER2/OS22XBITMAPHEADER
        # 108: BITMAPV4HEADER
        # 124: BITMAPV5HEADER
        elif file_info["header_size"] in (40, 52, 56, 64, 108, 124):
            file_info["y_flip"] = header_data[7] == 0xFF
            file_info["direction"] = 1 if file_info["y_flip"] else -1
            file_info["width"] = i32(header_data, 0)
            file_info["height"] = (
                i32(header_data, 4)
                if not file_info["y_flip"]
                else 2**32 - i32(header_data, 4)
            )
            file_info["planes"] = i16(header_data, 8)
            file_info["bits"] = i16(header_data, 10)
            file_info["compression"] = i32(header_data, 12)
            # byte size of pixel data
            file_info["data_size"] = i32(header_data, 16)
            file_info["pixels_per_meter"] = (
                i32(header_data, 20),
                i32(header_data, 24),
            )
            file_info["colors"] = i32(header_data, 28)
            file_info["palette_padding"] = 4
            assert isinstance(file_info["pixels_per_meter"], tuple)
            self.info["dpi"] = tuple(x / 39.3701 for x in file_info["pixels_per_meter"])
            if file_info["compression"] == self.COMPRESSIONS["BITFIELDS"]:
                masks = ["r_mask", "g_mask", "b_mask"]
                if len(header_data) >= 48:
                    if len(header_data) >= 52:
                        masks.append("a_mask")
                    else:
                        file_info["a_mask"] = 0x0
                    for idx, mask in enumerate(masks):
                        file_info[mask] = i32(header_data, 36 + idx * 4)
                else:
                    # 40 byte headers only have the three components in the
                    # bitfields masks, ref:
                    # https://msdn.microsoft.com/en-us/library/windows/desktop/dd183376(v=vs.85).aspx
                    # See also
                    # https://github.com/python-pillow/Pillow/issues/1293
                    # There is a 4th component in the RGBQuad, in the alpha
                    # location, but it is listed as a reserved component,
                    # and it is not generally an alpha channel
                    file_info["a_mask"] = 0x0
                    for mask in masks:
                        file_info[mask] = i32(read(4))
                assert isinstance(file_info["r_mask"], int)
                assert isinstance(file_info["g_mask"], int)
                assert isinstance(file_info["b_mask"], int)
                assert isinstance(file_info["a_mask"], int)
                file_info["rgb_mask"] = (
                    file_info["r_mask"],
                    file_info["g_mask"],
                    file_info["b_mask"],
                )
                file_info["rgba_mask"] = (
                    file_info["r_mask"],
                    file_info["g_mask"],
                    file_info["b_mask"],
                    file_info["a_mask"],
                )
        else:
            msg = f"Unsupported BMP header type ({file_info['header_size']})"
            raise OSError(msg)

        # ------------------ Special case : header is reported 40, which
        # ---------------------- is shorter than real size for bpp >= 16
        assert isinstance(file_info["width"], int)
        assert isinstance(file_info["height"], int)
        self._size = file_info["width"], file_info["height"]

        # ------- If color count was not found in the header, compute from bits
        assert isinstance(file_info["bits"], int)
        file_info["colors"] = (
            file_info["colors"]
            if file_info.get("colors", 0)
            else (1 << file_info["bits"])
        )
        assert isinstance(file_info["colors"], int)
        if offset == 14 + file_info["header_size"] and file_info["bits"] <= 8:
            offset += 4 * file_info["colors"]

        # ---------------------- Check bit depth for unusual unsupported values
        self._mode, raw_mode = BIT2MODE.get(file_info["bits"], ("", ""))
        if not self.mode:
            msg = f"Unsupported BMP pixel depth ({file_info['bits']})"
            raise OSError(msg)

        # ---------------- Process BMP with Bitfields compression (not palette)
        decoder_name = "raw"
        if file_info["compression"] == self.COMPRESSIONS["BITFIELDS"]:
            SUPPORTED: dict[int, list[tuple[int, ...]]] = {
                32: [
                    (0xFF0000, 0xFF00, 0xFF, 0x0),
                    (0xFF000000, 0xFF0000, 0xFF00, 0x0),
                    (0xFF000000, 0xFF00, 0xFF, 0x0),
                    (0xFF000000, 0xFF0000, 0xFF00, 0xFF),
                    (0xFF, 0xFF00, 0xFF0000, 0xFF000000),
                    (0xFF0000, 0xFF00, 0xFF, 0xFF000000),
                    (0xFF000000, 0xFF00, 0xFF, 0xFF0000),
                    (0x0, 0x0, 0x0, 0x0),
                ],
                24: [(0xFF0000, 0xFF00, 0xFF)],
                16: [(0xF800, 0x7E0, 0x1F), (0x7C00, 0x3E0, 0x1F)],
            }
            MASK_MODES = {
                (32, (0xFF0000, 0xFF00, 0xFF, 0x0)): "BGRX",
                (32, (0xFF000000, 0xFF0000, 0xFF00, 0x0)): "XBGR",
                (32, (0xFF000000, 0xFF00, 0xFF, 0x0)): "BGXR",
                (32, (0xFF000000, 0xFF0000, 0xFF00, 0xFF)): "ABGR",
                (32, (0xFF, 0xFF00, 0xFF0000, 0xFF000000)): "RGBA",
                (32, (0xFF0000, 0xFF00, 0xFF, 0xFF000000)): "BGRA",
                (32, (0xFF000000, 0xFF00, 0xFF, 0xFF0000)): "BGAR",
                (32, (0x0, 0x0, 0x0, 0x0)): "BGRA",
                (24, (0xFF0000, 0xFF00, 0xFF)): "BGR",
                (16, (0xF800, 0x7E0, 0x1F)): "BGR;16",
                (16, (0x7C00, 0x3E0, 0x1F)): "BGR;15",
            }
            if file_info["bits"] in SUPPORTED:
                if (
                    file_info["bits"] == 32
                    and file_info["rgba_mask"] in SUPPORTED[file_info["bits"]]
                ):
                    assert isinstance(file_info["rgba_mask"], tuple)
                    raw_mode = MASK_MODES[(file_info["bits"], file_info["rgba_mask"])]
                    self._mode = "RGBA" if "A" in raw_mode else self.mode
                elif (
                    file_info["bits"] in (24, 16)
                    and file_info["rgb_mask"] in SUPPORTED[file_info["bits"]]
                ):
                    assert isinstance(file_info["rgb_mask"], tuple)
                    raw_mode = MASK_MODES[(file_info["bits"], file_info["rgb_mask"])]
                else:
                    msg = "Unsupported BMP bitfields layout"
                    raise OSError(msg)
            else:
                msg = "Unsupported BMP bitfields layout"
                raise OSError(msg)
        elif file_info["compression"] == self.COMPRESSIONS["RAW"]:
            if file_info["bits"] == 32 and (
                header == 22 or USE_RAW_ALPHA  # 32-bit .cur offset
            ):
                raw_mode, self._mode = "BGRA", "RGBA"
        elif file_info["compression"] in (
            self.COMPRESSIONS["RLE8"],
            self.COMPRESSIONS["RLE4"],
        ):
            decoder_name = "bmp_rle"
        else:
            msg = f"Unsupported BMP compression ({file_info['compression']})"
            raise OSError(msg)

        # --------------- Once the header is processed, process the palette/LUT
        if self.mode == "P":  # Paletted for 1, 4 and 8 bit images
            # ---------------------------------------------------- 1-bit images
            if not (0 < file_info["colors"] <= 65536):
                msg = f"Unsupported BMP Palette size ({file_info['colors']})"
                raise OSError(msg)
            else:
                assert isinstance(file_info["palette_padding"], int)
                padding = file_info["palette_padding"]
                palette = read(padding * file_info["colors"])
                grayscale = True
                indices = (
                    (0, 255)
                    if file_info["colors"] == 2
                    else list(range(file_info["colors"]))
                )

                # ----------------- Check if grayscale and ignore palette if so
                for ind, val in enumerate(indices):
                    rgb = palette[ind * padding : ind * padding + 3]
                    if rgb != o8(val) * 3:
                        grayscale = False

                # ------- If all colors are gray, white or black, ditch palette
                if grayscale:
                    self._mode = "1" if file_info["colors"] == 2 else "L"
                    raw_mode = self.mode
                else:
                    self._mode = "P"
                    self.palette = ImagePalette.raw(
                        "BGRX" if padding == 4 else "BGR", palette
                    )

        # ---------------------------- Finally set the tile data for the plugin
        self.info["compression"] = file_info["compression"]
        args: list[Any] = [raw_mode]
        if decoder_name == "bmp_rle":
            args.append(file_info["compression"] == self.COMPRESSIONS["RLE4"])
        else:
            assert isinstance(file_info["width"], int)
            args.append(((file_info["width"] * file_info["bits"] + 31) >> 3) & (~3))
        args.append(file_info["direction"])
        self.tile = [
            ImageFile._Tile(
                decoder_name,
                (0, 0, file_info["width"], file_info["height"]),
                offset or self.fp.tell(),
                tuple(args),
            )
        ]

    def _open(self) -> None:
        """Open file, check magic number and read header"""
        # read 14 bytes: magic number, filesize, reserved, header final offset
        head_data = self.fp.read(14)
        # choke if the file does not have the required magic bytes
        if not _accept(head_data):
            msg = "Not a BMP file"
            raise SyntaxError(msg)
        # read the start position of the BMP image data (u32)
        offset = i32(head_data, 10)
        # load bitmap information (offset=raster info)
        self._bitmap(offset=offset)


class BmpRleDecoder(ImageFile.PyDecoder):
    _pulls_fd = True

    def decode(self, buffer: bytes | Image.SupportsArrayInterface) -> tuple[int, int]:
        assert self.fd is not None
        rle4 = self.args[1]
        data = bytearray()
        x = 0
        dest_length = self.state.xsize * self.state.ysize
        while len(data) < dest_length:
            pixels = self.fd.read(1)
            byte = self.fd.read(1)
            if not pixels or not byte:
                break
            num_pixels = pixels[0]
            if num_pixels:
                # encoded mode
                if x + num_pixels > self.state.xsize:
                    # Too much data for row
                    num_pixels = max(0, self.state.xsize - x)
                if rle4:
                    first_pixel = o8(byte[0] >> 4)
                    second_pixel = o8(byte[0] & 0x0F)
                    for index in range(num_pixels):
                        if index % 2 == 0:
                            data += first_pixel
                        else:
                            data += second_pixel
                else:
                    data += byte * num_pixels
                x += num_pixels
            else:
                if byte[0] == 0:
                    # end of line
                    while len(data) % self.state.xsize != 0:
                        data += b"\x00"
                    x = 0
                elif byte[0] == 1:
                    # end of bitmap
                    break
                elif byte[0] == 2:
                    # delta
                    bytes_read = self.fd.read(2)
                    if len(bytes_read) < 2:
                        break
                    right, up = self.fd.read(2)
                    data += b"\x00" * (right + up * self.state.xsize)
                    x = len(data) % self.state.xsize
                else:
                    # absolute mode
                    if rle4:
                        # 2 pixels per byte
                        byte_count = byte[0] // 2
                        bytes_read = self.fd.read(byte_count)
                        for byte_read in bytes_read:
                            data += o8(byte_read >> 4)
                            data += o8(byte_read & 0x0F)
                    else:
                        byte_count = byte[0]
                        bytes_read = self.fd.read(byte_count)
                        data += bytes_read
                    if len(bytes_read) < byte_count:
                        break
                    x += byte[0]

                    # align to 16-bit word boundary
                    if self.fd.tell() % 2 != 0:
                        self.fd.seek(1, os.SEEK_CUR)
        rawmode = "L" if self.mode == "L" else "P"
        self.set_as_raw(bytes(data), rawmode, (0, self.args[-1]))
        return -1, 0


# =============================================================================
# Image plugin for the DIB format (BMP alias)
# =============================================================================
class DibImageFile(BmpImageFile):
    format = "DIB"
    format_description = "Windows Bitmap"

    def _open(self) -> None:
        self._bitmap()


#
# --------------------------------------------------------------------
# Write BMP file


SAVE = {
    "1": ("1", 1, 2),
    "L": ("L", 8, 256),
    "P": ("P", 8, 256),
    "RGB": ("BGR", 24, 0),
    "RGBA": ("BGRA", 32, 0),
}


def _dib_save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    _save(im, fp, filename, False)


def _save(
    im: Image.Image, fp: IO[bytes], filename: str | bytes, bitmap_header: bool = True
) -> None:
    try:
        rawmode, bits, colors = SAVE[im.mode]
    except KeyError as e:
        msg = f"cannot write mode {im.mode} as BMP"
        raise OSError(msg) from e

    info = im.encoderinfo

    dpi = info.get("dpi", (96, 96))

    # 1 meter == 39.3701 inches
    ppm = tuple(int(x * 39.3701 + 0.5) for x in dpi)

    stride = ((im.size[0] * bits + 7) // 8 + 3) & (~3)
    header = 40  # or 64 for OS/2 version 2
    image = stride * im.size[1]

    if im.mode == "1":
        palette = b"".join(o8(i) * 4 for i in (0, 255))
    elif im.mode == "L":
        palette = b"".join(o8(i) * 4 for i in range(256))
    elif im.mode == "P":
        palette = im.im.getpalette("RGB", "BGRX")
        colors = len(palette) // 4
    else:
        palette = None

    # bitmap header
    if bitmap_header:
        offset = 14 + header + colors * 4
        file_size = offset + image
        if file_size > 2**32 - 1:
            msg = "File size is too large for the BMP format"
            raise ValueError(msg)
        fp.write(
            b"BM"  # file type (magic)
            + o32(file_size)  # file size
            + o32(0)  # reserved
            + o32(offset)  # image data offset
        )

    # bitmap info header
    fp.write(
        o32(header)  # info header size
        + o32(im.size[0])  # width
        + o32(im.size[1])  # height
        + o16(1)  # planes
        + o16(bits)  # depth
        + o32(0)  # compression (0=uncompressed)
        + o32(image)  # size of bitmap
        + o32(ppm[0])  # resolution
        + o32(ppm[1])  # resolution
        + o32(colors)  # colors used
        + o32(colors)  # colors important
    )

    fp.write(b"\0" * (header - 40))  # padding (for OS/2 format)

    if palette:
        fp.write(palette)

    ImageFile._save(
        im, fp, [ImageFile._Tile("raw", (0, 0) + im.size, 0, (rawmode, stride, -1))]
    )


#
# --------------------------------------------------------------------
# Registry


Image.register_open(BmpImageFile.format, BmpImageFile, _accept)
Image.register_save(BmpImageFile.format, _save)

Image.register_extension(BmpImageFile.format, ".bmp")

Image.register_mime(BmpImageFile.format, "image/bmp")

Image.register_decoder("bmp_rle", BmpRleDecoder)

Image.register_open(DibImageFile.format, DibImageFile, _dib_accept)
Image.register_save(DibImageFile.format, _dib_save)

Image.register_extension(DibImageFile.format, ".dib")

Image.register_mime(DibImageFile.format, "image/bmp")

# === NexusCore/openenv\Lib\site-packages\IPython\core\pylabtools.py ===
# -*- coding: utf-8 -*-
"""Pylab (matplotlib) support utilities."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from io import BytesIO
from binascii import b2a_base64
from functools import partial
import warnings

from IPython.core.display import _pngxy
from IPython.utils.decorators import flag_calls


# Matplotlib backend resolution functionality moved from IPython to Matplotlib
# in IPython 8.24 and Matplotlib 3.9.0. Need to keep `backends` and `backend2gui`
# here for earlier Matplotlib and for external backend libraries such as
# mplcairo that might rely upon it.
_deprecated_backends = {
    "tk": "TkAgg",
    "gtk": "GTKAgg",
    "gtk3": "GTK3Agg",
    "gtk4": "GTK4Agg",
    "wx": "WXAgg",
    "qt4": "Qt4Agg",
    "qt5": "Qt5Agg",
    "qt6": "QtAgg",
    "qt": "QtAgg",
    "osx": "MacOSX",
    "nbagg": "nbAgg",
    "webagg": "WebAgg",
    "notebook": "nbAgg",
    "agg": "agg",
    "svg": "svg",
    "pdf": "pdf",
    "ps": "ps",
    "inline": "module://matplotlib_inline.backend_inline",
    "ipympl": "module://ipympl.backend_nbagg",
    "widget": "module://ipympl.backend_nbagg",
}

# We also need a reverse backends2guis mapping that will properly choose which
# GUI support to activate based on the desired matplotlib backend.  For the
# most part it's just a reverse of the above dict, but we also need to add a
# few others that map to the same GUI manually:
_deprecated_backend2gui = dict(
    zip(_deprecated_backends.values(), _deprecated_backends.keys())
)
# In the reverse mapping, there are a few extra valid matplotlib backends that
# map to the same GUI support
_deprecated_backend2gui["GTK"] = _deprecated_backend2gui["GTKCairo"] = "gtk"
_deprecated_backend2gui["GTK3Cairo"] = "gtk3"
_deprecated_backend2gui["GTK4Cairo"] = "gtk4"
_deprecated_backend2gui["WX"] = "wx"
_deprecated_backend2gui["CocoaAgg"] = "osx"
# There needs to be a hysteresis here as the new QtAgg Matplotlib backend
# supports either Qt5 or Qt6 and the IPython qt event loop support Qt4, Qt5,
# and Qt6.
_deprecated_backend2gui["QtAgg"] = "qt"
_deprecated_backend2gui["Qt4Agg"] = "qt4"
_deprecated_backend2gui["Qt5Agg"] = "qt5"

# And some backends that don't need GUI integration
del _deprecated_backend2gui["nbAgg"]
del _deprecated_backend2gui["agg"]
del _deprecated_backend2gui["svg"]
del _deprecated_backend2gui["pdf"]
del _deprecated_backend2gui["ps"]
del _deprecated_backend2gui["module://matplotlib_inline.backend_inline"]
del _deprecated_backend2gui["module://ipympl.backend_nbagg"]


# Deprecated attributes backends and backend2gui mostly following PEP 562.
def __getattr__(name):
    if name in ("backends", "backend2gui"):
        warnings.warn(
            f"{name} is deprecated since IPython 8.24, backends are managed "
            "in matplotlib and can be externally registered.",
            DeprecationWarning,
        )
        return globals()[f"_deprecated_{name}"]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


#-----------------------------------------------------------------------------
# Matplotlib utilities
#-----------------------------------------------------------------------------


def getfigs(*fig_nums):
    """Get a list of matplotlib figures by figure numbers.

    If no arguments are given, all available figures are returned.  If the
    argument list contains references to invalid figures, a warning is printed
    but the function continues pasting further figures.

    Parameters
    ----------
    figs : tuple
        A tuple of ints giving the figure numbers of the figures to return.
    """
    from matplotlib._pylab_helpers import Gcf
    if not fig_nums:
        fig_managers = Gcf.get_all_fig_managers()
        return [fm.canvas.figure for fm in fig_managers]
    else:
        figs = []
        for num in fig_nums:
            f = Gcf.figs.get(num)
            if f is None:
                print('Warning: figure %s not available.' % num)
            else:
                figs.append(f.canvas.figure)
        return figs


def figsize(sizex, sizey):
    """Set the default figure size to be [sizex, sizey].

    This is just an easy to remember, convenience wrapper that sets::

      matplotlib.rcParams['figure.figsize'] = [sizex, sizey]
    """
    import matplotlib
    matplotlib.rcParams['figure.figsize'] = [sizex, sizey]


def print_figure(fig, fmt="png", bbox_inches="tight", base64=False, **kwargs):
    """Print a figure to an image, and return the resulting file data

    Returned data will be bytes unless ``fmt='svg'``,
    in which case it will be unicode.

    Any keyword args are passed to fig.canvas.print_figure,
    such as ``quality`` or ``bbox_inches``.

    If `base64` is True, return base64-encoded str instead of raw bytes
    for binary-encoded image formats

    .. versionadded:: 7.29
        base64 argument
    """
    # When there's an empty figure, we shouldn't return anything, otherwise we
    # get big blank areas in the qt console.
    if not fig.axes and not fig.lines:
        return

    dpi = fig.dpi
    if fmt == 'retina':
        dpi = dpi * 2
        fmt = 'png'

    # build keyword args
    kw = {
        "format":fmt,
        "facecolor":fig.get_facecolor(),
        "edgecolor":fig.get_edgecolor(),
        "dpi":dpi,
        "bbox_inches":bbox_inches,
    }
    # **kwargs get higher priority
    kw.update(kwargs)

    bytes_io = BytesIO()
    if fig.canvas is None:
        from matplotlib.backend_bases import FigureCanvasBase
        FigureCanvasBase(fig)

    fig.canvas.print_figure(bytes_io, **kw)
    data = bytes_io.getvalue()
    if fmt == 'svg':
        data = data.decode('utf-8')
    elif base64:
        data = b2a_base64(data, newline=False).decode("ascii")
    return data

def retina_figure(fig, base64=False, **kwargs):
    """format a figure as a pixel-doubled (retina) PNG

    If `base64` is True, return base64-encoded str instead of raw bytes
    for binary-encoded image formats

    .. versionadded:: 7.29
        base64 argument
    """
    pngdata = print_figure(fig, fmt="retina", base64=False, **kwargs)
    # Make sure that retina_figure acts just like print_figure and returns
    # None when the figure is empty.
    if pngdata is None:
        return
    w, h = _pngxy(pngdata)
    metadata = {"width": w//2, "height":h//2}
    if base64:
        pngdata = b2a_base64(pngdata, newline=False).decode("ascii")
    return pngdata, metadata


# We need a little factory function here to create the closure where
# safe_execfile can live.
def mpl_runner(safe_execfile):
    """Factory to return a matplotlib-enabled runner for %run.

    Parameters
    ----------
    safe_execfile : function
        This must be a function with the same interface as the
        :meth:`safe_execfile` method of IPython.

    Returns
    -------
    A function suitable for use as the ``runner`` argument of the %run magic
    function.
    """

    def mpl_execfile(fname,*where,**kw):
        """matplotlib-aware wrapper around safe_execfile.

        Its interface is identical to that of the :func:`execfile` builtin.

        This is ultimately a call to execfile(), but wrapped in safeties to
        properly handle interactive rendering."""

        import matplotlib
        import matplotlib.pyplot as plt

        # print('*** Matplotlib runner ***')  # dbg
        # turn off rendering until end of script
        with matplotlib.rc_context({"interactive": False}):
            safe_execfile(fname, *where, **kw)

        if matplotlib.is_interactive():
            plt.show()

        # make rendering call now, if the user tried to do it
        if plt.draw_if_interactive.called:
            plt.draw()
            plt.draw_if_interactive.called = False

        # re-draw everything that is stale
        try:
            da = plt.draw_all
        except AttributeError:
            pass
        else:
            da()

    return mpl_execfile


def _reshow_nbagg_figure(fig):
    """reshow an nbagg figure"""
    try:
        reshow = fig.canvas.manager.reshow
    except AttributeError as e:
        raise NotImplementedError() from e
    else:
        reshow()


def select_figure_formats(shell, formats, **kwargs):
    """Select figure formats for the inline backend.

    Parameters
    ----------
    shell : InteractiveShell
        The main IPython instance.
    formats : str or set
        One or a set of figure formats to enable: 'png', 'retina', 'jpeg', 'svg', 'pdf'.
    **kwargs : any
        Extra keyword arguments to be passed to fig.canvas.print_figure.
    """
    import matplotlib
    from matplotlib.figure import Figure

    svg_formatter = shell.display_formatter.formatters['image/svg+xml']
    png_formatter = shell.display_formatter.formatters['image/png']
    jpg_formatter = shell.display_formatter.formatters['image/jpeg']
    pdf_formatter = shell.display_formatter.formatters['application/pdf']

    if isinstance(formats, str):
        formats = {formats}
    # cast in case of list / tuple
    formats = set(formats)

    [ f.pop(Figure, None) for f in shell.display_formatter.formatters.values() ]
    mplbackend = matplotlib.get_backend().lower()
    if mplbackend in ("nbagg", "ipympl", "widget", "module://ipympl.backend_nbagg"):
        formatter = shell.display_formatter.ipython_display_formatter
        formatter.for_type(Figure, _reshow_nbagg_figure)

    supported = {'png', 'png2x', 'retina', 'jpg', 'jpeg', 'svg', 'pdf'}
    bad = formats.difference(supported)
    if bad:
        bs = "%s" % ','.join([repr(f) for f in bad])
        gs = "%s" % ','.join([repr(f) for f in supported])
        raise ValueError("supported formats are: %s not %s" % (gs, bs))

    if "png" in formats:
        png_formatter.for_type(
            Figure, partial(print_figure, fmt="png", base64=True, **kwargs)
        )
    if "retina" in formats or "png2x" in formats:
        png_formatter.for_type(Figure, partial(retina_figure, base64=True, **kwargs))
    if "jpg" in formats or "jpeg" in formats:
        jpg_formatter.for_type(
            Figure, partial(print_figure, fmt="jpg", base64=True, **kwargs)
        )
    if "svg" in formats:
        svg_formatter.for_type(Figure, partial(print_figure, fmt="svg", **kwargs))
    if "pdf" in formats:
        pdf_formatter.for_type(
            Figure, partial(print_figure, fmt="pdf", base64=True, **kwargs)
        )

#-----------------------------------------------------------------------------
# Code for initializing matplotlib and importing pylab
#-----------------------------------------------------------------------------


def find_gui_and_backend(gui=None, gui_select=None):
    """Given a gui string return the gui and mpl backend.

    Parameters
    ----------
    gui : str
        Can be one of ('tk','gtk','wx','qt','qt4','inline','agg').
    gui_select : str
        Can be one of ('tk','gtk','wx','qt','qt4','inline').
        This is any gui already selected by the shell.

    Returns
    -------
    A tuple of (gui, backend) where backend is one of ('TkAgg','GTKAgg',
    'WXAgg','Qt4Agg','module://matplotlib_inline.backend_inline','agg').
    """

    import matplotlib

    if _matplotlib_manages_backends():
        backend_registry = matplotlib.backends.registry.backend_registry

        # gui argument may be a gui event loop or may be a backend name.
        if gui in ("auto", None):
            backend = matplotlib.rcParamsOrig["backend"]
            backend, gui = backend_registry.resolve_backend(backend)
        else:
            gui = _convert_gui_to_matplotlib(gui)
            backend, gui = backend_registry.resolve_gui_or_backend(gui)

        gui = _convert_gui_from_matplotlib(gui)
        return gui, backend

    # Fallback to previous behaviour (Matplotlib < 3.9)
    mpl_version_info = getattr(matplotlib, "__version_info__", (0, 0))
    has_unified_qt_backend = mpl_version_info >= (3, 5)

    from IPython.core.pylabtools import backends

    backends_ = dict(backends)
    if not has_unified_qt_backend:
        backends_["qt"] = "qt5agg"

    if gui and gui != 'auto':
        # select backend based on requested gui
        backend = backends_[gui]
        if gui == 'agg':
            gui = None
    else:
        # We need to read the backend from the original data structure, *not*
        # from mpl.rcParams, since a prior invocation of %matplotlib may have
        # overwritten that.
        # WARNING: this assumes matplotlib 1.1 or newer!!
        backend = matplotlib.rcParamsOrig['backend']
        # In this case, we need to find what the appropriate gui selection call
        # should be for IPython, so we can activate inputhook accordingly
        from IPython.core.pylabtools import backend2gui
        gui = backend2gui.get(backend, None)

        # If we have already had a gui active, we need it and inline are the
        # ones allowed.
        if gui_select and gui != gui_select:
            gui = gui_select
            backend = backends_[gui]

    # Matplotlib before _matplotlib_manages_backends() can return "inline" for
    # no gui event loop rather than the None that IPython >= 8.24.0 expects.
    if gui == "inline":
        gui = None

    return gui, backend


def activate_matplotlib(backend):
    """Activate the given backend and set interactive to True."""

    import matplotlib
    matplotlib.interactive(True)

    # Matplotlib had a bug where even switch_backend could not force
    # the rcParam to update. This needs to be set *before* the module
    # magic of switch_backend().
    matplotlib.rcParams['backend'] = backend

    # Due to circular imports, pyplot may be only partially initialised
    # when this function runs.
    # So avoid needing matplotlib attribute-lookup to access pyplot.
    from matplotlib import pyplot as plt

    plt.switch_backend(backend)

    plt.show._needmain = False
    # We need to detect at runtime whether show() is called by the user.
    # For this, we wrap it into a decorator which adds a 'called' flag.
    plt.draw_if_interactive = flag_calls(plt.draw_if_interactive)


def import_pylab(user_ns, import_all=True):
    """Populate the namespace with pylab-related values.

    Imports matplotlib, pylab, numpy, and everything from pylab and numpy.

    Also imports a few names from IPython (figsize, display, getfigs)

    """

    # Import numpy as np/pyplot as plt are conventions we're trying to
    # somewhat standardize on.  Making them available to users by default
    # will greatly help this.
    s = ("import numpy\n"
          "import matplotlib\n"
          "from matplotlib import pylab, mlab, pyplot\n"
          "np = numpy\n"
          "plt = pyplot\n"
          )
    exec(s, user_ns)

    if import_all:
        s = ("from matplotlib.pylab import *\n"
             "from numpy import *\n")
        exec(s, user_ns)

    # IPython symbols to add
    user_ns['figsize'] = figsize
    from IPython.display import display
    # Add display and getfigs to the user's namespace
    user_ns['display'] = display
    user_ns['getfigs'] = getfigs


# Determine if Matplotlib manages backends only if needed, and cache result.
# Do not read this directly, instead use _matplotlib_manages_backends().
_matplotlib_manages_backends_value: bool | None = None


def _matplotlib_manages_backends() -> bool:
    """Return True if Matplotlib manages backends, False otherwise.

    If it returns True, the caller can be sure that
    matplotlib.backends.registry.backend_registry is available along with
    member functions resolve_gui_or_backend, resolve_backend, list_all, and
    list_gui_frameworks.

    This function can be removed as it will always return True when Python
    3.12, the latest version supported by Matplotlib < 3.9, reaches
    end-of-life in late 2028.
    """
    global _matplotlib_manages_backends_value
    if _matplotlib_manages_backends_value is None:
        try:
            from matplotlib.backends.registry import backend_registry

            _matplotlib_manages_backends_value = hasattr(
                backend_registry, "resolve_gui_or_backend"
            )
        except ImportError:
            _matplotlib_manages_backends_value = False

    return _matplotlib_manages_backends_value


def _list_matplotlib_backends_and_gui_loops() -> list[str]:
    """Return list of all Matplotlib backends and GUI event loops.

    This is the list returned by
        %matplotlib --list
    """
    if _matplotlib_manages_backends():
        from matplotlib.backends.registry import backend_registry

        ret = backend_registry.list_all() + [
            _convert_gui_from_matplotlib(gui)
            for gui in backend_registry.list_gui_frameworks()
        ]
    else:
        from IPython.core import pylabtools

        ret = list(pylabtools.backends.keys())

    return sorted(["auto"] + ret)


# Matplotlib and IPython do not always use the same gui framework name.
# Always use the appropriate one of these conversion functions when passing a
# gui framework name to/from Matplotlib.
def _convert_gui_to_matplotlib(gui: str | None) -> str | None:
    if gui and gui.lower() == "osx":
        return "macosx"
    return gui


def _convert_gui_from_matplotlib(gui: str | None) -> str | None:
    if gui and gui.lower() == "macosx":
        return "osx"
    return gui

# === NexusCore/openenv\Lib\site-packages\nltk\translate\stack_decoder.py ===
# Natural Language Toolkit: Stack decoder
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Tah Wei Hoon <hoon.tw@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A decoder that uses stacks to implement phrase-based translation.

In phrase-based translation, the source sentence is segmented into
phrases of one or more words, and translations for those phrases are
used to build the target sentence.

Hypothesis data structures are used to keep track of the source words
translated so far and the partial output. A hypothesis can be expanded
by selecting an untranslated phrase, looking up its translation in a
phrase table, and appending that translation to the partial output.
Translation is complete when a hypothesis covers all source words.

The search space is huge because the source sentence can be segmented
in different ways, the source phrases can be selected in any order,
and there could be multiple translations for the same source phrase in
the phrase table. To make decoding tractable, stacks are used to limit
the number of candidate hypotheses by doing histogram and/or threshold
pruning.

Hypotheses with the same number of words translated are placed in the
same stack. In histogram pruning, each stack has a size limit, and
the hypothesis with the lowest score is removed when the stack is full.
In threshold pruning, hypotheses that score below a certain threshold
of the best hypothesis in that stack are removed.

Hypothesis scoring can include various factors such as phrase
translation probability, language model probability, length of
translation, cost of remaining words to be translated, and so on.


References:
Philipp Koehn. 2010. Statistical Machine Translation.
Cambridge University Press, New York.
"""

import warnings
from collections import defaultdict
from math import log


class StackDecoder:
    """
    Phrase-based stack decoder for machine translation

    >>> from nltk.translate import PhraseTable
    >>> phrase_table = PhraseTable()
    >>> phrase_table.add(('niemand',), ('nobody',), log(0.8))
    >>> phrase_table.add(('niemand',), ('no', 'one'), log(0.2))
    >>> phrase_table.add(('erwartet',), ('expects',), log(0.8))
    >>> phrase_table.add(('erwartet',), ('expecting',), log(0.2))
    >>> phrase_table.add(('niemand', 'erwartet'), ('one', 'does', 'not', 'expect'), log(0.1))
    >>> phrase_table.add(('die', 'spanische', 'inquisition'), ('the', 'spanish', 'inquisition'), log(0.8))
    >>> phrase_table.add(('!',), ('!',), log(0.8))

    >>> #  nltk.model should be used here once it is implemented
    >>> from collections import defaultdict
    >>> language_prob = defaultdict(lambda: -999.0)
    >>> language_prob[('nobody',)] = log(0.5)
    >>> language_prob[('expects',)] = log(0.4)
    >>> language_prob[('the', 'spanish', 'inquisition')] = log(0.2)
    >>> language_prob[('!',)] = log(0.1)
    >>> language_model = type('',(object,),{'probability_change': lambda self, context, phrase: language_prob[phrase], 'probability': lambda self, phrase: language_prob[phrase]})()

    >>> stack_decoder = StackDecoder(phrase_table, language_model)

    >>> stack_decoder.translate(['niemand', 'erwartet', 'die', 'spanische', 'inquisition', '!'])
    ['nobody', 'expects', 'the', 'spanish', 'inquisition', '!']

    """

    def __init__(self, phrase_table, language_model):
        """
        :param phrase_table: Table of translations for source language
            phrases and the log probabilities for those translations.
        :type phrase_table: PhraseTable

        :param language_model: Target language model. Must define a
            ``probability_change`` method that calculates the change in
            log probability of a sentence, if a given string is appended
            to it.
            This interface is experimental and will likely be replaced
            with nltk.model once it is implemented.
        :type language_model: object
        """
        self.phrase_table = phrase_table
        self.language_model = language_model

        self.word_penalty = 0.0
        """
        float: Influences the translation length exponentially.
            If positive, shorter translations are preferred.
            If negative, longer translations are preferred.
            If zero, no penalty is applied.
        """

        self.beam_threshold = 0.0
        """
        float: Hypotheses that score below this factor of the best
            hypothesis in a stack are dropped from consideration.
            Value between 0.0 and 1.0.
        """

        self.stack_size = 100
        """
        int: Maximum number of hypotheses to consider in a stack.
            Higher values increase the likelihood of a good translation,
            but increases processing time.
        """

        self.__distortion_factor = 0.5
        self.__compute_log_distortion()

    @property
    def distortion_factor(self):
        """
        float: Amount of reordering of source phrases.
            Lower values favour monotone translation, suitable when
            word order is similar for both source and target languages.
            Value between 0.0 and 1.0. Default 0.5.
        """
        return self.__distortion_factor

    @distortion_factor.setter
    def distortion_factor(self, d):
        self.__distortion_factor = d
        self.__compute_log_distortion()

    def __compute_log_distortion(self):
        # cache log(distortion_factor) so we don't have to recompute it
        # when scoring hypotheses
        if self.__distortion_factor == 0.0:
            self.__log_distortion_factor = log(1e-9)  # 1e-9 is almost zero
        else:
            self.__log_distortion_factor = log(self.__distortion_factor)

    def translate(self, src_sentence):
        """
        :param src_sentence: Sentence to be translated
        :type src_sentence: list(str)

        :return: Translated sentence
        :rtype: list(str)
        """
        sentence = tuple(src_sentence)  # prevent accidental modification
        sentence_length = len(sentence)
        stacks = [
            _Stack(self.stack_size, self.beam_threshold)
            for _ in range(0, sentence_length + 1)
        ]
        empty_hypothesis = _Hypothesis()
        stacks[0].push(empty_hypothesis)

        all_phrases = self.find_all_src_phrases(sentence)
        future_score_table = self.compute_future_scores(sentence)
        for stack in stacks:
            for hypothesis in stack:
                possible_expansions = StackDecoder.valid_phrases(
                    all_phrases, hypothesis
                )
                for src_phrase_span in possible_expansions:
                    src_phrase = sentence[src_phrase_span[0] : src_phrase_span[1]]
                    for translation_option in self.phrase_table.translations_for(
                        src_phrase
                    ):
                        raw_score = self.expansion_score(
                            hypothesis, translation_option, src_phrase_span
                        )
                        new_hypothesis = _Hypothesis(
                            raw_score=raw_score,
                            src_phrase_span=src_phrase_span,
                            trg_phrase=translation_option.trg_phrase,
                            previous=hypothesis,
                        )
                        new_hypothesis.future_score = self.future_score(
                            new_hypothesis, future_score_table, sentence_length
                        )
                        total_words = new_hypothesis.total_translated_words()
                        stacks[total_words].push(new_hypothesis)

        if not stacks[sentence_length]:
            warnings.warn(
                "Unable to translate all words. "
                "The source sentence contains words not in "
                "the phrase table"
            )
            # Instead of returning empty output, perhaps a partial
            # translation could be returned
            return []

        best_hypothesis = stacks[sentence_length].best()
        return best_hypothesis.translation_so_far()

    def find_all_src_phrases(self, src_sentence):
        """
        Finds all subsequences in src_sentence that have a phrase
        translation in the translation table

        :type src_sentence: tuple(str)

        :return: Subsequences that have a phrase translation,
            represented as a table of lists of end positions.
            For example, if result[2] is [5, 6, 9], then there are
            three phrases starting from position 2 in ``src_sentence``,
            ending at positions 5, 6, and 9 exclusive. The list of
            ending positions are in ascending order.
        :rtype: list(list(int))
        """
        sentence_length = len(src_sentence)
        phrase_indices = [[] for _ in src_sentence]
        for start in range(0, sentence_length):
            for end in range(start + 1, sentence_length + 1):
                potential_phrase = src_sentence[start:end]
                if potential_phrase in self.phrase_table:
                    phrase_indices[start].append(end)
        return phrase_indices

    def compute_future_scores(self, src_sentence):
        """
        Determines the approximate scores for translating every
        subsequence in ``src_sentence``

        Future scores can be used a look-ahead to determine the
        difficulty of translating the remaining parts of a src_sentence.

        :type src_sentence: tuple(str)

        :return: Scores of subsequences referenced by their start and
            end positions. For example, result[2][5] is the score of the
            subsequence covering positions 2, 3, and 4.
        :rtype: dict(int: (dict(int): float))
        """
        scores = defaultdict(lambda: defaultdict(lambda: float("-inf")))
        for seq_length in range(1, len(src_sentence) + 1):
            for start in range(0, len(src_sentence) - seq_length + 1):
                end = start + seq_length
                phrase = src_sentence[start:end]
                if phrase in self.phrase_table:
                    score = self.phrase_table.translations_for(phrase)[
                        0
                    ].log_prob  # pick best (first) translation
                    # Warning: API of language_model is subject to change
                    score += self.language_model.probability(phrase)
                    scores[start][end] = score

                # check if a better score can be obtained by combining
                # two child subsequences
                for mid in range(start + 1, end):
                    combined_score = scores[start][mid] + scores[mid][end]
                    if combined_score > scores[start][end]:
                        scores[start][end] = combined_score
        return scores

    def future_score(self, hypothesis, future_score_table, sentence_length):
        """
        Determines the approximate score for translating the
        untranslated words in ``hypothesis``
        """
        score = 0.0
        for span in hypothesis.untranslated_spans(sentence_length):
            score += future_score_table[span[0]][span[1]]
        return score

    def expansion_score(self, hypothesis, translation_option, src_phrase_span):
        """
        Calculate the score of expanding ``hypothesis`` with
        ``translation_option``

        :param hypothesis: Hypothesis being expanded
        :type hypothesis: _Hypothesis

        :param translation_option: Information about the proposed expansion
        :type translation_option: PhraseTableEntry

        :param src_phrase_span: Word position span of the source phrase
        :type src_phrase_span: tuple(int, int)
        """
        score = hypothesis.raw_score
        score += translation_option.log_prob
        # The API of language_model is subject to change; it could accept
        # a string, a list of words, and/or some other type
        score += self.language_model.probability_change(
            hypothesis, translation_option.trg_phrase
        )
        score += self.distortion_score(hypothesis, src_phrase_span)
        score -= self.word_penalty * len(translation_option.trg_phrase)
        return score

    def distortion_score(self, hypothesis, next_src_phrase_span):
        if not hypothesis.src_phrase_span:
            return 0.0
        next_src_phrase_start = next_src_phrase_span[0]
        prev_src_phrase_end = hypothesis.src_phrase_span[1]
        distortion_distance = next_src_phrase_start - prev_src_phrase_end
        return abs(distortion_distance) * self.__log_distortion_factor

    @staticmethod
    def valid_phrases(all_phrases_from, hypothesis):
        """
        Extract phrases from ``all_phrases_from`` that contains words
        that have not been translated by ``hypothesis``

        :param all_phrases_from: Phrases represented by their spans, in
            the same format as the return value of
            ``find_all_src_phrases``
        :type all_phrases_from: list(list(int))

        :type hypothesis: _Hypothesis

        :return: A list of phrases, represented by their spans, that
            cover untranslated positions.
        :rtype: list(tuple(int, int))
        """
        untranslated_spans = hypothesis.untranslated_spans(len(all_phrases_from))
        valid_phrases = []
        for available_span in untranslated_spans:
            start = available_span[0]
            available_end = available_span[1]
            while start < available_end:
                for phrase_end in all_phrases_from[start]:
                    if phrase_end > available_end:
                        # Subsequent elements in all_phrases_from[start]
                        # will also be > available_end, since the
                        # elements are in ascending order
                        break
                    valid_phrases.append((start, phrase_end))
                start += 1
        return valid_phrases


class _Hypothesis:
    """
    Partial solution to a translation.

    Records the word positions of the phrase being translated, its
    translation, raw score, and the cost of the untranslated parts of
    the sentence. When the next phrase is selected to build upon the
    partial solution, a new _Hypothesis object is created, with a back
    pointer to the previous hypothesis.

    To find out which words have been translated so far, look at the
    ``src_phrase_span`` in the hypothesis chain. Similarly, the
    translation output can be found by traversing up the chain.
    """

    def __init__(
        self,
        raw_score=0.0,
        src_phrase_span=(),
        trg_phrase=(),
        previous=None,
        future_score=0.0,
    ):
        """
        :param raw_score: Likelihood of hypothesis so far.
            Higher is better. Does not account for untranslated words.
        :type raw_score: float

        :param src_phrase_span: Span of word positions covered by the
            source phrase in this hypothesis expansion. For example,
            (2, 5) means that the phrase is from the second word up to,
            but not including the fifth word in the source sentence.
        :type src_phrase_span: tuple(int)

        :param trg_phrase: Translation of the source phrase in this
            hypothesis expansion
        :type trg_phrase: tuple(str)

        :param previous: Previous hypothesis before expansion to this one
        :type previous: _Hypothesis

        :param future_score: Approximate score for translating the
            remaining words not covered by this hypothesis. Higher means
            that the remaining words are easier to translate.
        :type future_score: float
        """
        self.raw_score = raw_score
        self.src_phrase_span = src_phrase_span
        self.trg_phrase = trg_phrase
        self.previous = previous
        self.future_score = future_score

    def score(self):
        """
        Overall score of hypothesis after accounting for local and
        global features
        """
        return self.raw_score + self.future_score

    def untranslated_spans(self, sentence_length):
        """
        Starting from each untranslated word, find the longest
        continuous span of untranslated positions

        :param sentence_length: Length of source sentence being
            translated by the hypothesis
        :type sentence_length: int

        :rtype: list(tuple(int, int))
        """
        translated_positions = self.translated_positions()
        translated_positions.sort()
        translated_positions.append(sentence_length)  # add sentinel position

        untranslated_spans = []
        start = 0
        # each untranslated span must end in one of the translated_positions
        for end in translated_positions:
            if start < end:
                untranslated_spans.append((start, end))
            start = end + 1

        return untranslated_spans

    def translated_positions(self):
        """
        List of positions in the source sentence of words already
        translated. The list is not sorted.

        :rtype: list(int)
        """
        translated_positions = []
        current_hypothesis = self
        while current_hypothesis.previous is not None:
            translated_span = current_hypothesis.src_phrase_span
            translated_positions.extend(range(translated_span[0], translated_span[1]))
            current_hypothesis = current_hypothesis.previous
        return translated_positions

    def total_translated_words(self):
        return len(self.translated_positions())

    def translation_so_far(self):
        translation = []
        self.__build_translation(self, translation)
        return translation

    def __build_translation(self, hypothesis, output):
        if hypothesis.previous is None:
            return
        self.__build_translation(hypothesis.previous, output)
        output.extend(hypothesis.trg_phrase)


class _Stack:
    """
    Collection of _Hypothesis objects
    """

    def __init__(self, max_size=100, beam_threshold=0.0):
        """
        :param beam_threshold: Hypotheses that score less than this
            factor of the best hypothesis are discarded from the stack.
            Value must be between 0.0 and 1.0.
        :type beam_threshold: float
        """
        self.max_size = max_size
        self.items = []

        if beam_threshold == 0.0:
            self.__log_beam_threshold = float("-inf")
        else:
            self.__log_beam_threshold = log(beam_threshold)

    def push(self, hypothesis):
        """
        Add ``hypothesis`` to the stack.
        Removes lowest scoring hypothesis if the stack is full.
        After insertion, hypotheses that score less than
        ``beam_threshold`` times the score of the best hypothesis
        are removed.
        """
        self.items.append(hypothesis)
        self.items.sort(key=lambda h: h.score(), reverse=True)
        while len(self.items) > self.max_size:
            self.items.pop()
        self.threshold_prune()

    def threshold_prune(self):
        if not self.items:
            return
        #  log(score * beam_threshold) = log(score) + log(beam_threshold)
        threshold = self.items[0].score() + self.__log_beam_threshold
        for hypothesis in reversed(self.items):
            if hypothesis.score() < threshold:
                self.items.pop()
            else:
                break

    def best(self):
        """
        :return: Hypothesis with the highest score in the stack
        :rtype: _Hypothesis
        """
        if self.items:
            return self.items[0]
        return None

    def __iter__(self):
        return iter(self.items)

    def __contains__(self, hypothesis):
        return hypothesis in self.items

    def __bool__(self):
        return len(self.items) != 0

    __nonzero__ = __bool__

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_fields.py ===
"""Private logic related to fields (the `Field()` function and `FieldInfo` class), and arguments to `Annotated`."""

from __future__ import annotations as _annotations

import dataclasses
import warnings
from collections.abc import Mapping
from copy import copy
from functools import cache
from inspect import Parameter, ismethoddescriptor, signature
from re import Pattern
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from pydantic_core import PydanticUndefined
from typing_extensions import TypeIs, get_origin
from typing_inspection import typing_objects
from typing_inspection.introspection import AnnotationSource

from pydantic import PydanticDeprecatedSince211
from pydantic.errors import PydanticUserError

from . import _generics, _typing_extra
from ._config import ConfigWrapper
from ._docs_extraction import extract_docstrings_from_cls
from ._import_utils import import_cached_base_model, import_cached_field_info
from ._namespace_utils import NsResolver
from ._repr import Representation
from ._utils import can_be_positional

if TYPE_CHECKING:
    from annotated_types import BaseMetadata

    from ..fields import FieldInfo
    from ..main import BaseModel
    from ._dataclasses import PydanticDataclass, StandardDataclass
    from ._decorators import DecoratorInfos


class PydanticMetadata(Representation):
    """Base class for annotation markers like `Strict`."""

    __slots__ = ()


def pydantic_general_metadata(**metadata: Any) -> BaseMetadata:
    """Create a new `_PydanticGeneralMetadata` class with the given metadata.

    Args:
        **metadata: The metadata to add.

    Returns:
        The new `_PydanticGeneralMetadata` class.
    """
    return _general_metadata_cls()(metadata)  # type: ignore


@cache
def _general_metadata_cls() -> type[BaseMetadata]:
    """Do it this way to avoid importing `annotated_types` at import time."""
    from annotated_types import BaseMetadata

    class _PydanticGeneralMetadata(PydanticMetadata, BaseMetadata):
        """Pydantic general metadata like `max_digits`."""

        def __init__(self, metadata: Any):
            self.__dict__ = metadata

    return _PydanticGeneralMetadata  # type: ignore


def _update_fields_from_docstrings(cls: type[Any], fields: dict[str, FieldInfo], use_inspect: bool = False) -> None:
    fields_docs = extract_docstrings_from_cls(cls, use_inspect=use_inspect)
    for ann_name, field_info in fields.items():
        if field_info.description is None and ann_name in fields_docs:
            field_info.description = fields_docs[ann_name]


def collect_model_fields(  # noqa: C901
    cls: type[BaseModel],
    config_wrapper: ConfigWrapper,
    ns_resolver: NsResolver | None,
    *,
    typevars_map: Mapping[TypeVar, Any] | None = None,
) -> tuple[dict[str, FieldInfo], set[str]]:
    """Collect the fields and class variables names of a nascent Pydantic model.

    The fields collection process is *lenient*, meaning it won't error if string annotations
    fail to evaluate. If this happens, the original annotation (and assigned value, if any)
    is stored on the created `FieldInfo` instance.

    The `rebuild_model_fields()` should be called at a later point (e.g. when rebuilding the model),
    and will make use of these stored attributes.

    Args:
        cls: BaseModel or dataclass.
        config_wrapper: The config wrapper instance.
        ns_resolver: Namespace resolver to use when getting model annotations.
        typevars_map: A dictionary mapping type variables to their concrete types.

    Returns:
        A two-tuple containing model fields and class variables names.

    Raises:
        NameError:
            - If there is a conflict between a field name and protected namespaces.
            - If there is a field other than `root` in `RootModel`.
            - If a field shadows an attribute in the parent model.
    """
    BaseModel = import_cached_base_model()
    FieldInfo_ = import_cached_field_info()

    bases = cls.__bases__
    parent_fields_lookup: dict[str, FieldInfo] = {}
    for base in reversed(bases):
        if model_fields := getattr(base, '__pydantic_fields__', None):
            parent_fields_lookup.update(model_fields)

    type_hints = _typing_extra.get_model_type_hints(cls, ns_resolver=ns_resolver)

    # https://docs.python.org/3/howto/annotations.html#accessing-the-annotations-dict-of-an-object-in-python-3-9-and-older
    # annotations is only used for finding fields in parent classes
    annotations = cls.__dict__.get('__annotations__', {})
    fields: dict[str, FieldInfo] = {}

    class_vars: set[str] = set()
    for ann_name, (ann_type, evaluated) in type_hints.items():
        if ann_name == 'model_config':
            # We never want to treat `model_config` as a field
            # Note: we may need to change this logic if/when we introduce a `BareModel` class with no
            # protected namespaces (where `model_config` might be allowed as a field name)
            continue

        for protected_namespace in config_wrapper.protected_namespaces:
            ns_violation: bool = False
            if isinstance(protected_namespace, Pattern):
                ns_violation = protected_namespace.match(ann_name) is not None
            elif isinstance(protected_namespace, str):
                ns_violation = ann_name.startswith(protected_namespace)

            if ns_violation:
                for b in bases:
                    if hasattr(b, ann_name):
                        if not (issubclass(b, BaseModel) and ann_name in getattr(b, '__pydantic_fields__', {})):
                            raise NameError(
                                f'Field "{ann_name}" conflicts with member {getattr(b, ann_name)}'
                                f' of protected namespace "{protected_namespace}".'
                            )
                else:
                    valid_namespaces = ()
                    for pn in config_wrapper.protected_namespaces:
                        if isinstance(pn, Pattern):
                            if not pn.match(ann_name):
                                valid_namespaces += (f're.compile({pn.pattern})',)
                        else:
                            if not ann_name.startswith(pn):
                                valid_namespaces += (pn,)

                    warnings.warn(
                        f'Field "{ann_name}" in {cls.__name__} has conflict with protected namespace "{protected_namespace}".'
                        '\n\nYou may be able to resolve this warning by setting'
                        f" `model_config['protected_namespaces'] = {valid_namespaces}`.",
                        UserWarning,
                    )
        if _typing_extra.is_classvar_annotation(ann_type):
            class_vars.add(ann_name)
            continue

        assigned_value = getattr(cls, ann_name, PydanticUndefined)

        if not is_valid_field_name(ann_name):
            continue
        if cls.__pydantic_root_model__ and ann_name != 'root':
            raise NameError(
                f"Unexpected field with name {ann_name!r}; only 'root' is allowed as a field of a `RootModel`"
            )

        # when building a generic model with `MyModel[int]`, the generic_origin check makes sure we don't get
        # "... shadows an attribute" warnings
        generic_origin = getattr(cls, '__pydantic_generic_metadata__', {}).get('origin')
        for base in bases:
            dataclass_fields = {
                field.name for field in (dataclasses.fields(base) if dataclasses.is_dataclass(base) else ())
            }
            if hasattr(base, ann_name):
                if base is generic_origin:
                    # Don't warn when "shadowing" of attributes in parametrized generics
                    continue

                if ann_name in dataclass_fields:
                    # Don't warn when inheriting stdlib dataclasses whose fields are "shadowed" by defaults being set
                    # on the class instance.
                    continue

                if ann_name not in annotations:
                    # Don't warn when a field exists in a parent class but has not been defined in the current class
                    continue

                warnings.warn(
                    f'Field name "{ann_name}" in "{cls.__qualname__}" shadows an attribute in parent '
                    f'"{base.__qualname__}"',
                    UserWarning,
                )

        if assigned_value is PydanticUndefined:  # no assignment, just a plain annotation
            if ann_name in annotations or ann_name not in parent_fields_lookup:
                # field is either:
                # - present in the current model's annotations (and *not* from parent classes)
                # - not found on any base classes; this seems to be caused by fields bot getting
                #   generated due to models not being fully defined while initializing recursive models.
                #   Nothing stops us from just creating a `FieldInfo` for this type hint, so we do this.
                field_info = FieldInfo_.from_annotation(ann_type, _source=AnnotationSource.CLASS)
                if not evaluated:
                    field_info._complete = False
                    # Store the original annotation that should be used to rebuild
                    # the field info later:
                    field_info._original_annotation = ann_type
            else:
                # The field was present on one of the (possibly multiple) base classes
                # copy the field to make sure typevar substitutions don't cause issues with the base classes
                field_info = copy(parent_fields_lookup[ann_name])

        else:  # An assigned value is present (either the default value, or a `Field()` function)
            _warn_on_nested_alias_in_annotation(ann_type, ann_name)
            if isinstance(assigned_value, FieldInfo_) and ismethoddescriptor(assigned_value.default):
                # `assigned_value` was fetched using `getattr`, which triggers a call to `__get__`
                # for descriptors, so we do the same if the `= field(default=...)` form is used.
                # Note that we only do this for method descriptors for now, we might want to
                # extend this to any descriptor in the future (by simply checking for
                # `hasattr(assigned_value.default, '__get__')`).
                assigned_value.default = assigned_value.default.__get__(None, cls)

            # The `from_annotated_attribute()` call below mutates the assigned `Field()`, so make a copy:
            original_assignment = (
                assigned_value._copy() if not evaluated and isinstance(assigned_value, FieldInfo_) else assigned_value
            )

            field_info = FieldInfo_.from_annotated_attribute(ann_type, assigned_value, _source=AnnotationSource.CLASS)
            # Store the original annotation and assignment value that should be used to rebuild the field info later.
            # Note that the assignment is always stored as the annotation might contain a type var that is later
            #  parameterized with an unknown forward reference (and we'll need it to rebuild the field info):
            field_info._original_assignment = original_assignment
            if not evaluated:
                field_info._complete = False
                field_info._original_annotation = ann_type
            elif 'final' in field_info._qualifiers and not field_info.is_required():
                warnings.warn(
                    f'Annotation {ann_name!r} is marked as final and has a default value. Pydantic treats {ann_name!r} as a '
                    'class variable, but it will be considered as a normal field in V3 to be aligned with dataclasses. If you '
                    f'still want {ann_name!r} to be considered as a class variable, annotate it as: `ClassVar[<type>] = <default>.`',
                    category=PydanticDeprecatedSince211,
                    # Incorrect when `create_model` is used, but the chance that final with a default is used is low in that case:
                    stacklevel=4,
                )
                class_vars.add(ann_name)
                continue

            # attributes which are fields are removed from the class namespace:
            # 1. To match the behaviour of annotation-only fields
            # 2. To avoid false positives in the NameError check above
            try:
                delattr(cls, ann_name)
            except AttributeError:
                pass  # indicates the attribute was on a parent class

        # Use cls.__dict__['__pydantic_decorators__'] instead of cls.__pydantic_decorators__
        # to make sure the decorators have already been built for this exact class
        decorators: DecoratorInfos = cls.__dict__['__pydantic_decorators__']
        if ann_name in decorators.computed_fields:
            raise TypeError(
                f'Field {ann_name!r} of class {cls.__name__!r} overrides symbol of same name in a parent class. '
                'This override with a computed_field is incompatible.'
            )
        fields[ann_name] = field_info

    if typevars_map:
        for field in fields.values():
            if field._complete:
                field.apply_typevars_map(typevars_map)

    if config_wrapper.use_attribute_docstrings:
        _update_fields_from_docstrings(cls, fields)
    return fields, class_vars


def _warn_on_nested_alias_in_annotation(ann_type: type[Any], ann_name: str) -> None:
    FieldInfo = import_cached_field_info()

    args = getattr(ann_type, '__args__', None)
    if args:
        for anno_arg in args:
            if typing_objects.is_annotated(get_origin(anno_arg)):
                for anno_type_arg in _typing_extra.get_args(anno_arg):
                    if isinstance(anno_type_arg, FieldInfo) and anno_type_arg.alias is not None:
                        warnings.warn(
                            f'`alias` specification on field "{ann_name}" must be set on outermost annotation to take effect.',
                            UserWarning,
                        )
                        return


def rebuild_model_fields(
    cls: type[BaseModel],
    *,
    ns_resolver: NsResolver,
    typevars_map: Mapping[TypeVar, Any],
) -> dict[str, FieldInfo]:
    """Rebuild the (already present) model fields by trying to reevaluate annotations.

    This function should be called whenever a model with incomplete fields is encountered.

    Raises:
        NameError: If one of the annotations failed to evaluate.

    Note:
        This function *doesn't* mutate the model fields in place, as it can be called during
        schema generation, where you don't want to mutate other model's fields.
    """
    FieldInfo_ = import_cached_field_info()

    rebuilt_fields: dict[str, FieldInfo] = {}
    with ns_resolver.push(cls):
        for f_name, field_info in cls.__pydantic_fields__.items():
            if field_info._complete:
                rebuilt_fields[f_name] = field_info
            else:
                existing_desc = field_info.description
                ann = _typing_extra.eval_type(
                    field_info._original_annotation,
                    *ns_resolver.types_namespace,
                )
                ann = _generics.replace_types(ann, typevars_map)

                if (assign := field_info._original_assignment) is PydanticUndefined:
                    new_field = FieldInfo_.from_annotation(ann, _source=AnnotationSource.CLASS)
                else:
                    new_field = FieldInfo_.from_annotated_attribute(ann, assign, _source=AnnotationSource.CLASS)
                # The description might come from the docstring if `use_attribute_docstrings` was `True`:
                new_field.description = new_field.description if new_field.description is not None else existing_desc
                rebuilt_fields[f_name] = new_field

    return rebuilt_fields


def collect_dataclass_fields(
    cls: type[StandardDataclass],
    *,
    ns_resolver: NsResolver | None = None,
    typevars_map: dict[Any, Any] | None = None,
    config_wrapper: ConfigWrapper | None = None,
) -> dict[str, FieldInfo]:
    """Collect the fields of a dataclass.

    Args:
        cls: dataclass.
        ns_resolver: Namespace resolver to use when getting dataclass annotations.
            Defaults to an empty instance.
        typevars_map: A dictionary mapping type variables to their concrete types.
        config_wrapper: The config wrapper instance.

    Returns:
        The dataclass fields.
    """
    FieldInfo_ = import_cached_field_info()

    fields: dict[str, FieldInfo] = {}
    ns_resolver = ns_resolver or NsResolver()
    dataclass_fields = cls.__dataclass_fields__

    # The logic here is similar to `_typing_extra.get_cls_type_hints`,
    # although we do it manually as stdlib dataclasses already have annotations
    # collected in each class:
    for base in reversed(cls.__mro__):
        if not dataclasses.is_dataclass(base):
            continue

        with ns_resolver.push(base):
            for ann_name, dataclass_field in dataclass_fields.items():
                if ann_name not in base.__dict__.get('__annotations__', {}):
                    # `__dataclass_fields__`contains every field, even the ones from base classes.
                    # Only collect the ones defined on `base`.
                    continue

                globalns, localns = ns_resolver.types_namespace
                ann_type, evaluated = _typing_extra.try_eval_type(dataclass_field.type, globalns, localns)

                if _typing_extra.is_classvar_annotation(ann_type):
                    continue

                if (
                    not dataclass_field.init
                    and dataclass_field.default is dataclasses.MISSING
                    and dataclass_field.default_factory is dataclasses.MISSING
                ):
                    # TODO: We should probably do something with this so that validate_assignment behaves properly
                    #   Issue: https://github.com/pydantic/pydantic/issues/5470
                    continue

                if isinstance(dataclass_field.default, FieldInfo_):
                    if dataclass_field.default.init_var:
                        if dataclass_field.default.init is False:
                            raise PydanticUserError(
                                f'Dataclass field {ann_name} has init=False and init_var=True, but these are mutually exclusive.',
                                code='clashing-init-and-init-var',
                            )

                        # TODO: same note as above re validate_assignment
                        continue
                    field_info = FieldInfo_.from_annotated_attribute(
                        ann_type, dataclass_field.default, _source=AnnotationSource.DATACLASS
                    )
                    field_info._original_assignment = dataclass_field.default
                else:
                    field_info = FieldInfo_.from_annotated_attribute(
                        ann_type, dataclass_field, _source=AnnotationSource.DATACLASS
                    )
                    field_info._original_assignment = dataclass_field

                if not evaluated:
                    field_info._complete = False
                    field_info._original_annotation = ann_type

                fields[ann_name] = field_info

                if field_info.default is not PydanticUndefined and isinstance(
                    getattr(cls, ann_name, field_info), FieldInfo_
                ):
                    # We need this to fix the default when the "default" from __dataclass_fields__ is a pydantic.FieldInfo
                    setattr(cls, ann_name, field_info.default)

    if typevars_map:
        for field in fields.values():
            # We don't pass any ns, as `field.annotation`
            # was already evaluated. TODO: is this method relevant?
            # Can't we juste use `_generics.replace_types`?
            field.apply_typevars_map(typevars_map)

    if config_wrapper is not None and config_wrapper.use_attribute_docstrings:
        _update_fields_from_docstrings(
            cls,
            fields,
            # We can't rely on the (more reliable) frame inspection method
            # for stdlib dataclasses:
            use_inspect=not hasattr(cls, '__is_pydantic_dataclass__'),
        )

    return fields


def rebuild_dataclass_fields(
    cls: type[PydanticDataclass],
    *,
    config_wrapper: ConfigWrapper,
    ns_resolver: NsResolver,
    typevars_map: Mapping[TypeVar, Any],
) -> dict[str, FieldInfo]:
    """Rebuild the (already present) dataclass fields by trying to reevaluate annotations.

    This function should be called whenever a dataclass with incomplete fields is encountered.

    Raises:
        NameError: If one of the annotations failed to evaluate.

    Note:
        This function *doesn't* mutate the dataclass fields in place, as it can be called during
        schema generation, where you don't want to mutate other dataclass's fields.
    """
    FieldInfo_ = import_cached_field_info()

    rebuilt_fields: dict[str, FieldInfo] = {}
    with ns_resolver.push(cls):
        for f_name, field_info in cls.__pydantic_fields__.items():
            if field_info._complete:
                rebuilt_fields[f_name] = field_info
            else:
                existing_desc = field_info.description
                ann = _typing_extra.eval_type(
                    field_info._original_annotation,
                    *ns_resolver.types_namespace,
                )
                ann = _generics.replace_types(ann, typevars_map)
                new_field = FieldInfo_.from_annotated_attribute(
                    ann,
                    field_info._original_assignment,
                    _source=AnnotationSource.DATACLASS,
                )

                # The description might come from the docstring if `use_attribute_docstrings` was `True`:
                new_field.description = new_field.description if new_field.description is not None else existing_desc
                rebuilt_fields[f_name] = new_field

    return rebuilt_fields


def is_valid_field_name(name: str) -> bool:
    return not name.startswith('_')


def is_valid_privateattr_name(name: str) -> bool:
    return name.startswith('_') and not name.startswith('__')


def takes_validated_data_argument(
    default_factory: Callable[[], Any] | Callable[[dict[str, Any]], Any],
) -> TypeIs[Callable[[dict[str, Any]], Any]]:
    """Whether the provided default factory callable has a validated data parameter."""
    try:
        sig = signature(default_factory)
    except (ValueError, TypeError):
        # `inspect.signature` might not be able to infer a signature, e.g. with C objects.
        # In this case, we assume no data argument is present:
        return False

    parameters = list(sig.parameters.values())

    return len(parameters) == 1 and can_be_positional(parameters[0]) and parameters[0].default is Parameter.empty

# === NexusCore/openenv\Lib\site-packages\openai\resources\batches.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Literal

import httpx

from .. import _legacy_response
from ..types import batch_list_params, batch_create_params
from .._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from .._utils import maybe_transform, async_maybe_transform
from .._compat import cached_property
from .._resource import SyncAPIResource, AsyncAPIResource
from .._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ..pagination import SyncCursorPage, AsyncCursorPage
from ..types.batch import Batch
from .._base_client import AsyncPaginator, make_request_options
from ..types.shared_params.metadata import Metadata

__all__ = ["Batches", "AsyncBatches"]


class Batches(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> BatchesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return BatchesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> BatchesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return BatchesWithStreamingResponse(self)

    def create(
        self,
        *,
        completion_window: Literal["24h"],
        endpoint: Literal["/v1/responses", "/v1/chat/completions", "/v1/embeddings", "/v1/completions"],
        input_file_id: str,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Batch:
        """
        Creates and executes a batch from an uploaded file of requests

        Args:
          completion_window: The time frame within which the batch should be processed. Currently only `24h`
              is supported.

          endpoint: The endpoint to be used for all requests in the batch. Currently
              `/v1/responses`, `/v1/chat/completions`, `/v1/embeddings`, and `/v1/completions`
              are supported. Note that `/v1/embeddings` batches are also restricted to a
              maximum of 50,000 embedding inputs across all requests in the batch.

          input_file_id: The ID of an uploaded file that contains requests for the new batch.

              See [upload file](https://platform.openai.com/docs/api-reference/files/create)
              for how to upload a file.

              Your input file must be formatted as a
              [JSONL file](https://platform.openai.com/docs/api-reference/batch/request-input),
              and must be uploaded with the purpose `batch`. The file can contain up to 50,000
              requests, and can be up to 200 MB in size.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/batches",
            body=maybe_transform(
                {
                    "completion_window": completion_window,
                    "endpoint": endpoint,
                    "input_file_id": input_file_id,
                    "metadata": metadata,
                },
                batch_create_params.BatchCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Batch,
        )

    def retrieve(
        self,
        batch_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Batch:
        """
        Retrieves a batch.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not batch_id:
            raise ValueError(f"Expected a non-empty value for `batch_id` but received {batch_id!r}")
        return self._get(
            f"/batches/{batch_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Batch,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[Batch]:
        """List your organization's batches.

        Args:
          after: A cursor for use in pagination.

        `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get_api_list(
            "/batches",
            page=SyncCursorPage[Batch],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                    },
                    batch_list_params.BatchListParams,
                ),
            ),
            model=Batch,
        )

    def cancel(
        self,
        batch_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Batch:
        """Cancels an in-progress batch.

        The batch will be in status `cancelling` for up to
        10 minutes, before changing to `cancelled`, where it will have partial results
        (if any) available in the output file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not batch_id:
            raise ValueError(f"Expected a non-empty value for `batch_id` but received {batch_id!r}")
        return self._post(
            f"/batches/{batch_id}/cancel",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Batch,
        )


class AsyncBatches(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncBatchesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncBatchesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncBatchesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncBatchesWithStreamingResponse(self)

    async def create(
        self,
        *,
        completion_window: Literal["24h"],
        endpoint: Literal["/v1/responses", "/v1/chat/completions", "/v1/embeddings", "/v1/completions"],
        input_file_id: str,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Batch:
        """
        Creates and executes a batch from an uploaded file of requests

        Args:
          completion_window: The time frame within which the batch should be processed. Currently only `24h`
              is supported.

          endpoint: The endpoint to be used for all requests in the batch. Currently
              `/v1/responses`, `/v1/chat/completions`, `/v1/embeddings`, and `/v1/completions`
              are supported. Note that `/v1/embeddings` batches are also restricted to a
              maximum of 50,000 embedding inputs across all requests in the batch.

          input_file_id: The ID of an uploaded file that contains requests for the new batch.

              See [upload file](https://platform.openai.com/docs/api-reference/files/create)
              for how to upload a file.

              Your input file must be formatted as a
              [JSONL file](https://platform.openai.com/docs/api-reference/batch/request-input),
              and must be uploaded with the purpose `batch`. The file can contain up to 50,000
              requests, and can be up to 200 MB in size.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/batches",
            body=await async_maybe_transform(
                {
                    "completion_window": completion_window,
                    "endpoint": endpoint,
                    "input_file_id": input_file_id,
                    "metadata": metadata,
                },
                batch_create_params.BatchCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Batch,
        )

    async def retrieve(
        self,
        batch_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Batch:
        """
        Retrieves a batch.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not batch_id:
            raise ValueError(f"Expected a non-empty value for `batch_id` but received {batch_id!r}")
        return await self._get(
            f"/batches/{batch_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Batch,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[Batch, AsyncCursorPage[Batch]]:
        """List your organization's batches.

        Args:
          after: A cursor for use in pagination.

        `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get_api_list(
            "/batches",
            page=AsyncCursorPage[Batch],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                    },
                    batch_list_params.BatchListParams,
                ),
            ),
            model=Batch,
        )

    async def cancel(
        self,
        batch_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Batch:
        """Cancels an in-progress batch.

        The batch will be in status `cancelling` for up to
        10 minutes, before changing to `cancelled`, where it will have partial results
        (if any) available in the output file.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not batch_id:
            raise ValueError(f"Expected a non-empty value for `batch_id` but received {batch_id!r}")
        return await self._post(
            f"/batches/{batch_id}/cancel",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Batch,
        )


class BatchesWithRawResponse:
    def __init__(self, batches: Batches) -> None:
        self._batches = batches

        self.create = _legacy_response.to_raw_response_wrapper(
            batches.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            batches.retrieve,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            batches.list,
        )
        self.cancel = _legacy_response.to_raw_response_wrapper(
            batches.cancel,
        )


class AsyncBatchesWithRawResponse:
    def __init__(self, batches: AsyncBatches) -> None:
        self._batches = batches

        self.create = _legacy_response.async_to_raw_response_wrapper(
            batches.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            batches.retrieve,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            batches.list,
        )
        self.cancel = _legacy_response.async_to_raw_response_wrapper(
            batches.cancel,
        )


class BatchesWithStreamingResponse:
    def __init__(self, batches: Batches) -> None:
        self._batches = batches

        self.create = to_streamed_response_wrapper(
            batches.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            batches.retrieve,
        )
        self.list = to_streamed_response_wrapper(
            batches.list,
        )
        self.cancel = to_streamed_response_wrapper(
            batches.cancel,
        )


class AsyncBatchesWithStreamingResponse:
    def __init__(self, batches: AsyncBatches) -> None:
        self._batches = batches

        self.create = async_to_streamed_response_wrapper(
            batches.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            batches.retrieve,
        )
        self.list = async_to_streamed_response_wrapper(
            batches.list,
        )
        self.cancel = async_to_streamed_response_wrapper(
            batches.cancel,
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\options.py ===
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

import warnings
from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import List, Optional

from selenium.common.exceptions import InvalidArgumentException
from selenium.webdriver.common.proxy import Proxy


class PageLoadStrategy(str, Enum):
    """Enum of possible page load strategies.

    Selenium support following strategies:
        * normal (default) - waits for all resources to download
        * eager - DOM access is ready, but other resources like images may still be loading
        * none - does not block `WebDriver` at all

    Docs: https://www.selenium.dev/documentation/webdriver/drivers/options/#pageloadstrategy.
    """

    normal = "normal"
    eager = "eager"
    none = "none"


class _BaseOptionsDescriptor:
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls):
        if self.name == "enableBidi":
            # whether BiDi is or will be enabled
            value = obj._caps.get("webSocketUrl")
            return value is True or isinstance(value, str)
        if self.name == "webSocketUrl":
            # Return socket url or None if not created yet
            value = obj._caps.get(self.name)
            return None if not isinstance(value, str) else value
        if self.name in ("acceptInsecureCerts", "strictFileInteractability", "setWindowRect", "se:downloadsEnabled"):
            return obj._caps.get(self.name, False)
        return obj._caps.get(self.name)

    def __set__(self, obj, value):
        if self.name == "enableBidi":
            obj.set_capability("webSocketUrl", value)
        else:
            obj.set_capability(self.name, value)


class _PageLoadStrategyDescriptor:
    """Determines the point at which a navigation command is returned:
    https://w3c.github.io/webdriver/#dfn-table-of-page-load-strategies.

    :param strategy: the strategy corresponding to a document readiness state
    """

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls):
        return obj._caps.get(self.name)

    def __set__(self, obj, value):
        if value in ("normal", "eager", "none"):
            obj.set_capability(self.name, value)
        else:
            raise ValueError("Strategy can only be one of the following: normal, eager, none")


class _UnHandledPromptBehaviorDescriptor:
    """How the driver should respond when an alert is present and the:
    command sent is not handling the alert:
    https://w3c.github.io/webdriver/#dfn-table-of-page-load-strategies:

    :param behavior: behavior to use when an alert is encountered

    :returns: Values for implicit timeout, pageLoad timeout and script timeout if set (in milliseconds)
    """

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls):
        return obj._caps.get(self.name)

    def __set__(self, obj, value):
        if value in ("dismiss", "accept", "dismiss and notify", "accept and notify", "ignore"):
            obj.set_capability(self.name, value)
        else:
            raise ValueError(
                "Behavior can only be one of the following: dismiss, accept, dismiss and notify, "
                "accept and notify, ignore"
            )


class _TimeoutsDescriptor:
    """How long the driver should wait for actions to complete before:
    returning an error https://w3c.github.io/webdriver/#timeouts:

    :param timeouts: values in milliseconds for implicit wait, page load and script timeout

    :returns: Values for implicit timeout, pageLoad timeout and script timeout if set (in milliseconds)
    """

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls):
        return obj._caps.get(self.name)

    def __set__(self, obj, value):
        if all(x in ("implicit", "pageLoad", "script") for x in value.keys()):
            obj.set_capability(self.name, value)
        else:
            raise ValueError("Timeout keys can only be one of the following: implicit, pageLoad, script")


class _ProxyDescriptor:
    """:Returns: Proxy if set, otherwise None."""

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls):
        return obj._proxy

    def __set__(self, obj, value):
        if not isinstance(value, Proxy):
            raise InvalidArgumentException("Only Proxy objects can be passed in.")
        obj._proxy = value
        obj._caps[self.name] = value.to_capabilities()


class BaseOptions(metaclass=ABCMeta):
    """Base class for individual browser options."""

    browser_version = _BaseOptionsDescriptor("browserVersion")
    """Gets and Sets the version of the browser.

    Usage:
    ------
    - Get
        - `self.browser_version`
    - Set
        - `self.browser_version` = `value`

    Parameters:
    -----------
    `value`: `str`

    Returns:
    --------
    - Get
        - `str`
    - Set
        - `None`
    """

    platform_name = _BaseOptionsDescriptor("platformName")
    """Gets and Sets name of the platform.

    Usage:
    ------
    - Get
        - `self.platform_name`
    - Set
        - `self.platform_name` = `value`

    Parameters:
    -----------
    `value`: `str`

    Returns:
    --------
    - Get
        - `str`
    - Set
        - `None`
    """

    accept_insecure_certs = _BaseOptionsDescriptor("acceptInsecureCerts")
    """Gets and Set whether the session accepts insecure certificates.

    Usage:
    ------
    - Get
        - `self.accept_insecure_certs`
    - Set
        - `self.accept_insecure_certs` = `value`

    Parameters:
    -----------
    `value`: `bool`

    Returns:
    --------
    - Get
        - `bool`
    - Set
        - `None`
    """

    strict_file_interactability = _BaseOptionsDescriptor("strictFileInteractability")
    """Gets and Sets whether session is about file interactability.

    Usage:
    ------
    - Get
        - `self.strict_file_interactability`
    - Set
        - `self.strict_file_interactability` = `value`

    Parameters:
    -----------
    `value`: `bool`

    Returns:
    --------
    - Get
        - `bool`
    - Set
        - `None`
    """

    set_window_rect = _BaseOptionsDescriptor("setWindowRect")
    """Gets and Sets window size and position.

    Usage:
    ------
    - Get
        - `self.set_window_rect`
    - Set
        - `self.set_window_rect` = `value`

    Parameters:
    -----------
    `value`: `bool`

    Returns:
    --------
    - Get
        - `bool`
    - Set
        - `None`
    """

    enable_bidi = _BaseOptionsDescriptor("enableBidi")
    """Gets and Set whether the session has WebDriverBiDi enabled.

    Usage:
    ------
    - Get
        - `self.enable_bidi`
    - Set
        - `self.enable_bidi` = `value`

    Parameters:
    -----------
    `value`: `bool`

    Returns:
    --------
    - Get
        - `bool`
    - Set
        - `None`
    """

    page_load_strategy = _PageLoadStrategyDescriptor("pageLoadStrategy")
    """:Gets and Sets page load strategy, the default is "normal".

    Usage:
    ------
    - Get
        - `self.page_load_strategy`
    - Set
        - `self.page_load_strategy` = `value`

    Parameters:
    -----------
    `value`: `str`

    Returns:
    --------
    - Get
        - `str`
    - Set
        - `None`
    """

    unhandled_prompt_behavior = _UnHandledPromptBehaviorDescriptor("unhandledPromptBehavior")
    """:Gets and Sets unhandled prompt behavior, the default is "dismiss and
    notify".

    Usage:
    ------
    - Get
        - `self.unhandled_prompt_behavior`
    - Set
        - `self.unhandled_prompt_behavior` = `value`

    Parameters:
    -----------
    `value`: `str`

    Returns:
    --------
    - Get
        - `str`
    - Set
        - `None`
    """

    timeouts = _TimeoutsDescriptor("timeouts")
    """:Gets and Sets implicit timeout, pageLoad timeout and script timeout if
    set (in milliseconds)

    Usage:
    ------
    - Get
        - `self.timeouts`
    - Set
        - `self.timeouts` = `value`

    Parameters:
    -----------
    `value`: `dict`

    Returns:
    --------
    - Get
        - `dict`
    - Set
        - `None`
    """

    proxy = _ProxyDescriptor("proxy")
    """Sets and Gets Proxy.

    Usage:
    ------
    - Get
        - `self.proxy`
    - Set
        - `self.proxy` = `value`

    Parameters:
    -----------
    `value`: `Proxy`

    Returns:
    --------
    - Get
        - `Proxy`
    - Set
        - `None`
    """

    enable_downloads = _BaseOptionsDescriptor("se:downloadsEnabled")
    """Gets and Sets whether session can download files.

    Usage:
    ------
    - Get
        - `self.enable_downloads`
    - Set
        - `self.enable_downloads` = `value`

    Parameters:
    -----------
    `value`: `bool`

    Returns:
    --------
    - Get
        - `bool`
    - Set
        - `None`
    """

    web_socket_url = _BaseOptionsDescriptor("webSocketUrl")
    """Gets and Sets WebSocket URL.

    Usage:
    ------
    - Get
        - `self.web_socket_url`
    - Set
        - `self.web_socket_url` = `value`

    Parameters:
    -----------
    `value`: `str`

    Returns:
    --------
    - Get
        - `bool`
    - Set
        - `None`
    """

    def __init__(self) -> None:
        super().__init__()
        self._caps = self.default_capabilities
        self._proxy = None
        self.set_capability("pageLoadStrategy", PageLoadStrategy.normal)
        self.mobile_options = None
        self._ignore_local_proxy = False

    @property
    def capabilities(self):
        return self._caps

    def set_capability(self, name, value) -> None:
        """Sets a capability."""
        self._caps[name] = value

    def enable_mobile(
        self,
        android_package: Optional[str] = None,
        android_activity: Optional[str] = None,
        device_serial: Optional[str] = None,
    ) -> None:
        """Enables mobile browser use for browsers that support it.

        :Args:
            android_activity: The name of the android package to start
        """
        if not android_package:
            raise AttributeError("android_package must be passed in")
        self.mobile_options = {"androidPackage": android_package}
        if android_activity:
            self.mobile_options["androidActivity"] = android_activity
        if device_serial:
            self.mobile_options["androidDeviceSerial"] = device_serial

    @abstractmethod
    def to_capabilities(self):
        """Convert options into capabilities dictionary."""

    @property
    @abstractmethod
    def default_capabilities(self):
        """Return minimal capabilities necessary as a dictionary."""

    def ignore_local_proxy_environment_variables(self) -> None:
        """By calling this you will ignore HTTP_PROXY and HTTPS_PROXY from
        being picked up and used."""
        self._ignore_local_proxy = True


class ArgOptions(BaseOptions):
    BINARY_LOCATION_ERROR = "Binary Location Must be a String"
    # FedCM capability key
    FEDCM_CAPABILITY = "fedcm:accounts"

    def __init__(self) -> None:
        super().__init__()
        self._arguments: List[str] = []

    @property
    def arguments(self):
        """:Returns: A list of arguments needed for the browser."""
        return self._arguments

    def add_argument(self, argument: str) -> None:
        """Adds an argument to the list.

        :Args:
         - Sets the arguments
        """
        if argument:
            self._arguments.append(argument)
        else:
            raise ValueError("argument can not be null")

    def ignore_local_proxy_environment_variables(self) -> None:
        """By calling this you will ignore HTTP_PROXY and HTTPS_PROXY from
        being picked up and used."""
        warnings.warn(
            "using ignore_local_proxy_environment_variables in Options has been deprecated, "
            "instead, create a Proxy instance with ProxyType.DIRECT to ignore proxy settings, "
            "pass the proxy instance into a ClientConfig constructor, "
            "pass the client config instance into the Webdriver constructor",
            DeprecationWarning,
            stacklevel=2,
        )

        super().ignore_local_proxy_environment_variables()

    def to_capabilities(self):
        return self._caps

    @property
    def default_capabilities(self):
        return {}

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\bidi\cdp.py ===
# The MIT License(MIT)
#
# Copyright(c) 2018 Hyperion Gray
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files(the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and / or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# This code comes from https://github.com/HyperionGray/trio-chrome-devtools-protocol/tree/master/trio_cdp

# flake8: noqa

import contextvars
import importlib
import itertools
import json
import logging
import pathlib
from collections import defaultdict
from contextlib import asynccontextmanager
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from typing import AsyncGenerator
from typing import AsyncIterator
from typing import Generator
from typing import Type
from typing import TypeVar

import trio
from trio_websocket import ConnectionClosed as WsConnectionClosed
from trio_websocket import connect_websocket_url

logger = logging.getLogger("trio_cdp")
T = TypeVar("T")
MAX_WS_MESSAGE_SIZE = 2**24

devtools = None
version = None


def import_devtools(ver):
    """Attempt to load the current latest available devtools into the module
    cache for use later."""
    global devtools
    global version
    version = ver
    base = "selenium.webdriver.common.devtools.v"
    try:
        devtools = importlib.import_module(f"{base}{ver}")
        return devtools
    except ModuleNotFoundError:
        # Attempt to parse and load the 'most recent' devtools module. This is likely
        # because cdp has been updated but selenium python has not been released yet.
        devtools_path = pathlib.Path(__file__).parents[1].joinpath("devtools")
        versions = tuple(f.name for f in devtools_path.iterdir() if f.is_dir())
        latest = max(int(x[1:]) for x in versions)
        selenium_logger = logging.getLogger(__name__)
        selenium_logger.debug("Falling back to loading `devtools`: v%s", latest)
        devtools = importlib.import_module(f"{base}{latest}")
        return devtools


_connection_context: contextvars.ContextVar = contextvars.ContextVar("connection_context")
_session_context: contextvars.ContextVar = contextvars.ContextVar("session_context")


def get_connection_context(fn_name):
    """Look up the current connection.

    If there is no current connection, raise a ``RuntimeError`` with a
    helpful message.
    """
    try:
        return _connection_context.get()
    except LookupError:
        raise RuntimeError(f"{fn_name}() must be called in a connection context.")


def get_session_context(fn_name):
    """Look up the current session.

    If there is no current session, raise a ``RuntimeError`` with a
    helpful message.
    """
    try:
        return _session_context.get()
    except LookupError:
        raise RuntimeError(f"{fn_name}() must be called in a session context.")


@contextmanager
def connection_context(connection):
    """This context manager installs ``connection`` as the session context for
    the current Trio task."""
    token = _connection_context.set(connection)
    try:
        yield
    finally:
        _connection_context.reset(token)


@contextmanager
def session_context(session):
    """This context manager installs ``session`` as the session context for the
    current Trio task."""
    token = _session_context.set(session)
    try:
        yield
    finally:
        _session_context.reset(token)


def set_global_connection(connection):
    """Install ``connection`` in the root context so that it will become the
    default connection for all tasks.

    This is generally not recommended, except it may be necessary in
    certain use cases such as running inside Jupyter notebook.
    """
    global _connection_context
    _connection_context = contextvars.ContextVar("_connection_context", default=connection)


def set_global_session(session):
    """Install ``session`` in the root context so that it will become the
    default session for all tasks.

    This is generally not recommended, except it may be necessary in
    certain use cases such as running inside Jupyter notebook.
    """
    global _session_context
    _session_context = contextvars.ContextVar("_session_context", default=session)


class BrowserError(Exception):
    """This exception is raised when the browser's response to a command
    indicates that an error occurred."""

    def __init__(self, obj):
        self.code = obj.get("code")
        self.message = obj.get("message")
        self.detail = obj.get("data")

    def __str__(self):
        return f"BrowserError<code={self.code} message={self.message}> {self.detail}"


class CdpConnectionClosed(WsConnectionClosed):
    """Raised when a public method is called on a closed CDP connection."""

    def __init__(self, reason):
        """Constructor.

        :param reason:
        :type reason: wsproto.frame_protocol.CloseReason
        """
        self.reason = reason

    def __repr__(self):
        """Return representation."""
        return f"{self.__class__.__name__}<{self.reason}>"


class InternalError(Exception):
    """This exception is only raised when there is faulty logic in TrioCDP or
    the integration with PyCDP."""


@dataclass
class CmEventProxy:
    """A proxy object returned by :meth:`CdpBase.wait_for()``.

    After the context manager executes, this proxy object will have a
    value set that contains the returned event.
    """

    value: Any = None


class CdpBase:
    def __init__(self, ws, session_id, target_id):
        self.ws = ws
        self.session_id = session_id
        self.target_id = target_id
        self.channels = defaultdict(set)
        self.id_iter = itertools.count()
        self.inflight_cmd = {}
        self.inflight_result = {}

    async def execute(self, cmd: Generator[dict, T, Any]) -> T:
        """Execute a command on the server and wait for the result.

        :param cmd: any CDP command
        :returns: a CDP result
        """
        cmd_id = next(self.id_iter)
        cmd_event = trio.Event()
        self.inflight_cmd[cmd_id] = cmd, cmd_event
        request = next(cmd)
        request["id"] = cmd_id
        if self.session_id:
            request["sessionId"] = self.session_id
        request_str = json.dumps(request)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Sending CDP message: {cmd_id} {cmd_event}: {request_str}")
        try:
            await self.ws.send_message(request_str)
        except WsConnectionClosed as wcc:
            raise CdpConnectionClosed(wcc.reason) from None
        await cmd_event.wait()
        response = self.inflight_result.pop(cmd_id)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Received CDP message: {response}")
        if isinstance(response, Exception):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Exception raised by {cmd_event} message: {type(response).__name__}")
            raise response
        return response

    def listen(self, *event_types, buffer_size=10):
        """Return an async iterator that iterates over events matching the
        indicated types."""
        sender, receiver = trio.open_memory_channel(buffer_size)
        for event_type in event_types:
            self.channels[event_type].add(sender)
        return receiver

    @asynccontextmanager
    async def wait_for(self, event_type: Type[T], buffer_size=10) -> AsyncGenerator[CmEventProxy, None]:
        """Wait for an event of the given type and return it.

        This is an async context manager, so you should open it inside
        an async with block. The block will not exit until the indicated
        event is received.
        """
        sender: trio.MemorySendChannel
        receiver: trio.MemoryReceiveChannel
        sender, receiver = trio.open_memory_channel(buffer_size)
        self.channels[event_type].add(sender)
        proxy = CmEventProxy()
        yield proxy
        async with receiver:
            event = await receiver.receive()
        proxy.value = event

    def _handle_data(self, data):
        """Handle incoming WebSocket data.

        :param dict data: a JSON dictionary
        """
        if "id" in data:
            self._handle_cmd_response(data)
        else:
            self._handle_event(data)

    def _handle_cmd_response(self, data):
        """Handle a response to a command. This will set an event flag that
        will return control to the task that called the command.

        :param dict data: response as a JSON dictionary
        """
        cmd_id = data["id"]
        try:
            cmd, event = self.inflight_cmd.pop(cmd_id)
        except KeyError:
            logger.warning("Got a message with a command ID that does not exist: %s", data)
            return
        if "error" in data:
            # If the server reported an error, convert it to an exception and do
            # not process the response any further.
            self.inflight_result[cmd_id] = BrowserError(data["error"])
        else:
            # Otherwise, continue the generator to parse the JSON result
            # into a CDP object.
            try:
                _ = cmd.send(data["result"])
                raise InternalError("The command's generator function did not exit when expected!")
            except StopIteration as exit:
                return_ = exit.value
            self.inflight_result[cmd_id] = return_
        event.set()

    def _handle_event(self, data):
        """Handle an event.

        :param dict data: event as a JSON dictionary
        """
        global devtools
        event = devtools.util.parse_json_event(data)
        logger.debug("Received event: %s", event)
        to_remove = set()
        for sender in self.channels[type(event)]:
            try:
                sender.send_nowait(event)
            except trio.WouldBlock:
                logger.error('Unable to send event "%r" due to full channel %s', event, sender)
            except trio.BrokenResourceError:
                to_remove.add(sender)
        if to_remove:
            self.channels[type(event)] -= to_remove


class CdpSession(CdpBase):
    """Contains the state for a CDP session.

    Generally you should not instantiate this object yourself; you should call
    :meth:`CdpConnection.open_session`.
    """

    def __init__(self, ws, session_id, target_id):
        """Constructor.

        :param trio_websocket.WebSocketConnection ws:
        :param devtools.target.SessionID session_id:
        :param devtools.target.TargetID target_id:
        """
        super().__init__(ws, session_id, target_id)

        self._dom_enable_count = 0
        self._dom_enable_lock = trio.Lock()
        self._page_enable_count = 0
        self._page_enable_lock = trio.Lock()

    @asynccontextmanager
    async def dom_enable(self):
        """A context manager that executes ``dom.enable()`` when it enters and
        then calls ``dom.disable()``.

        This keeps track of concurrent callers and only disables DOM
        events when all callers have exited.
        """
        global devtools
        async with self._dom_enable_lock:
            self._dom_enable_count += 1
            if self._dom_enable_count == 1:
                await self.execute(devtools.dom.enable())

        yield

        async with self._dom_enable_lock:
            self._dom_enable_count -= 1
            if self._dom_enable_count == 0:
                await self.execute(devtools.dom.disable())

    @asynccontextmanager
    async def page_enable(self):
        """A context manager that executes ``page.enable()`` when it enters and
        then calls ``page.disable()`` when it exits.

        This keeps track of concurrent callers and only disables page
        events when all callers have exited.
        """
        global devtools
        async with self._page_enable_lock:
            self._page_enable_count += 1
            if self._page_enable_count == 1:
                await self.execute(devtools.page.enable())

        yield

        async with self._page_enable_lock:
            self._page_enable_count -= 1
            if self._page_enable_count == 0:
                await self.execute(devtools.page.disable())


class CdpConnection(CdpBase, trio.abc.AsyncResource):
    """Contains the connection state for a Chrome DevTools Protocol server.

    CDP can multiplex multiple "sessions" over a single connection. This
    class corresponds to the "root" session, i.e. the implicitly created
    session that has no session ID. This class is responsible for
    reading incoming WebSocket messages and forwarding them to the
    corresponding session, as well as handling messages targeted at the
    root session itself. You should generally call the
    :func:`open_cdp()` instead of instantiating this class directly.
    """

    def __init__(self, ws):
        """Constructor.

        :param trio_websocket.WebSocketConnection ws:
        """
        super().__init__(ws, session_id=None, target_id=None)
        self.sessions = {}

    async def aclose(self):
        """Close the underlying WebSocket connection.

        This will cause the reader task to gracefully exit when it tries
        to read the next message from the WebSocket. All of the public
        APIs (``execute()``, ``listen()``, etc.) will raise
        ``CdpConnectionClosed`` after the CDP connection is closed. It
        is safe to call this multiple times.
        """
        await self.ws.aclose()

    @asynccontextmanager
    async def open_session(self, target_id) -> AsyncIterator[CdpSession]:
        """This context manager opens a session and enables the "simple" style
        of calling CDP APIs.

        For example, inside a session context, you can call ``await
        dom.get_document()`` and it will execute on the current session
        automatically.
        """
        session = await self.connect_session(target_id)
        with session_context(session):
            yield session

    async def connect_session(self, target_id) -> "CdpSession":
        """Returns a new :class:`CdpSession` connected to the specified
        target."""
        global devtools
        session_id = await self.execute(devtools.target.attach_to_target(target_id, True))
        session = CdpSession(self.ws, session_id, target_id)
        self.sessions[session_id] = session
        return session

    async def _reader_task(self):
        """Runs in the background and handles incoming messages: dispatching
        responses to commands and events to listeners."""
        global devtools
        while True:
            try:
                message = await self.ws.get_message()
            except WsConnectionClosed:
                # If the WebSocket is closed, we don't want to throw an
                # exception from the reader task. Instead we will throw
                # exceptions from the public API methods, and we can quietly
                # exit the reader task here.
                break
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                raise BrowserError({"code": -32700, "message": "Client received invalid JSON", "data": message})
            logger.debug("Received message %r", data)
            if "sessionId" in data:
                session_id = devtools.target.SessionID(data["sessionId"])
                try:
                    session = self.sessions[session_id]
                except KeyError:
                    raise BrowserError(
                        {
                            "code": -32700,
                            "message": "Browser sent a message for an invalid session",
                            "data": f"{session_id!r}",
                        }
                    )
                session._handle_data(data)
            else:
                self._handle_data(data)

        for _, session in self.sessions.items():
            for _, senders in session.channels.items():
                for sender in senders:
                    sender.close()


@asynccontextmanager
async def open_cdp(url) -> AsyncIterator[CdpConnection]:
    """This async context manager opens a connection to the browser specified
    by ``url`` before entering the block, then closes the connection when the
    block exits.

    The context manager also sets the connection as the default
    connection for the current task, so that commands like ``await
    target.get_targets()`` will run on this connection automatically. If
    you want to use multiple connections concurrently, it is recommended
    to open each on in a separate task.
    """

    async with trio.open_nursery() as nursery:
        conn = await connect_cdp(nursery, url)
        try:
            with connection_context(conn):
                yield conn
        finally:
            await conn.aclose()


async def connect_cdp(nursery, url) -> CdpConnection:
    """Connect to the browser specified by ``url`` and spawn a background task
    in the specified nursery.

    The ``open_cdp()`` context manager is preferred in most situations.
    You should only use this function if you need to specify a custom
    nursery. This connection is not automatically closed! You can either
    use the connection object as a context manager (``async with
    conn:``) or else call ``await conn.aclose()`` on it when you are
    done with it. If ``set_context`` is True, then the returned
    connection will be installed as the default connection for the
    current task. This argument is for unusual use cases, such as
    running inside of a notebook.
    """
    ws = await connect_websocket_url(nursery, url, max_message_size=MAX_WS_MESSAGE_SIZE)
    cdp_conn = CdpConnection(ws)
    nursery.start_soon(cdp_conn._reader_task)
    return cdp_conn

# === NexusCore/openenv\Lib\site-packages\trio\_file_io.py ===
from __future__ import annotations

import io
from collections.abc import Callable, Iterable
from functools import partial
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    AnyStr,
    BinaryIO,
    Generic,
    TypeVar,
    Union,
    overload,
)

import trio

from ._util import async_wraps
from .abc import AsyncResource

if TYPE_CHECKING:
    from _typeshed import (
        OpenBinaryMode,
        OpenBinaryModeReading,
        OpenBinaryModeUpdating,
        OpenBinaryModeWriting,
        OpenTextMode,
        StrOrBytesPath,
    )
    from typing_extensions import Literal

    from ._sync import CapacityLimiter

# This list is also in the docs, make sure to keep them in sync
_FILE_SYNC_ATTRS: set[str] = {
    "closed",
    "encoding",
    "errors",
    "fileno",
    "isatty",
    "newlines",
    "readable",
    "seekable",
    "writable",
    # not defined in *IOBase:
    "buffer",
    "raw",
    "line_buffering",
    "closefd",
    "name",
    "mode",
    "getvalue",
    "getbuffer",
}

# This list is also in the docs, make sure to keep them in sync
_FILE_ASYNC_METHODS: set[str] = {
    "flush",
    "read",
    "read1",
    "readall",
    "readinto",
    "readline",
    "readlines",
    "seek",
    "tell",
    "truncate",
    "write",
    "writelines",
    # not defined in *IOBase:
    "readinto1",
    "peek",
}


FileT = TypeVar("FileT")
FileT_co = TypeVar("FileT_co", covariant=True)
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)
AnyStr_co = TypeVar("AnyStr_co", str, bytes, covariant=True)
AnyStr_contra = TypeVar("AnyStr_contra", str, bytes, contravariant=True)

# This is a little complicated. IO objects have a lot of methods, and which are available on
# different types varies wildly. We want to match the interface of whatever file we're wrapping.
# This pile of protocols each has one sync method/property, meaning they're going to be compatible
# with a file class that supports that method/property. The ones parameterized with AnyStr take
# either str or bytes depending.

# The wrapper is then a generic class, where the typevar is set to the type of the sync file we're
# wrapping. For generics, adding a type to self has a special meaning - properties/methods can be
# conditional - it's only valid to call them if the object you're accessing them on is compatible
# with that type hint. By using the protocols, the type checker will be checking to see if the
# wrapped type has that method, and only allow the methods that do to be called. We can then alter
# the signature however it needs to match runtime behaviour.
# More info: https://mypy.readthedocs.io/en/stable/more_types.html#advanced-uses-of-self-types
if TYPE_CHECKING:
    from typing_extensions import Buffer, Protocol

    # fmt: off

    class _HasClosed(Protocol):
        @property
        def closed(self) -> bool: ...

    class _HasEncoding(Protocol):
        @property
        def encoding(self) -> str: ...

    class _HasErrors(Protocol):
        @property
        def errors(self) -> str | None: ...

    class _HasFileNo(Protocol):
        def fileno(self) -> int: ...

    class _HasIsATTY(Protocol):
        def isatty(self) -> bool: ...

    class _HasNewlines(Protocol[T_co]):
        # Type varies here - documented to be None, tuple of strings, strings. Typeshed uses Any.
        @property
        def newlines(self) -> T_co: ...

    class _HasReadable(Protocol):
        def readable(self) -> bool: ...

    class _HasSeekable(Protocol):
        def seekable(self) -> bool: ...

    class _HasWritable(Protocol):
        def writable(self) -> bool: ...

    class _HasBuffer(Protocol):
        @property
        def buffer(self) -> BinaryIO: ...

    class _HasRaw(Protocol):
        @property
        def raw(self) -> io.RawIOBase: ...

    class _HasLineBuffering(Protocol):
        @property
        def line_buffering(self) -> bool: ...

    class _HasCloseFD(Protocol):
        @property
        def closefd(self) -> bool: ...

    class _HasName(Protocol):
        @property
        def name(self) -> str: ...

    class _HasMode(Protocol):
        @property
        def mode(self) -> str: ...

    class _CanGetValue(Protocol[AnyStr_co]):
        def getvalue(self) -> AnyStr_co: ...

    class _CanGetBuffer(Protocol):
        def getbuffer(self) -> memoryview: ...

    class _CanFlush(Protocol):
        def flush(self) -> None: ...

    class _CanRead(Protocol[AnyStr_co]):
        def read(self, size: int | None = ..., /) -> AnyStr_co: ...

    class _CanRead1(Protocol):
        def read1(self, size: int | None = ..., /) -> bytes: ...

    class _CanReadAll(Protocol[AnyStr_co]):
        def readall(self) -> AnyStr_co: ...

    class _CanReadInto(Protocol):
        def readinto(self, buf: Buffer, /) -> int | None: ...

    class _CanReadInto1(Protocol):
        def readinto1(self, buffer: Buffer, /) -> int: ...

    class _CanReadLine(Protocol[AnyStr_co]):
        def readline(self, size: int = ..., /) -> AnyStr_co: ...

    class _CanReadLines(Protocol[AnyStr]):
        def readlines(self, hint: int = ..., /) -> list[AnyStr]: ...

    class _CanSeek(Protocol):
        def seek(self, target: int, whence: int = 0, /) -> int: ...

    class _CanTell(Protocol):
        def tell(self) -> int: ...

    class _CanTruncate(Protocol):
        def truncate(self, size: int | None = ..., /) -> int: ...

    class _CanWrite(Protocol[T_contra]):
        def write(self, data: T_contra, /) -> int: ...

    class _CanWriteLines(Protocol[T_contra]):
        # The lines parameter varies for bytes/str, so use a typevar to make the async match.
        def writelines(self, lines: Iterable[T_contra], /) -> None: ...

    class _CanPeek(Protocol[AnyStr_co]):
        def peek(self, size: int = 0, /) -> AnyStr_co: ...

    class _CanDetach(Protocol[T_co]):
        # The T typevar will be the unbuffered/binary file this file wraps.
        def detach(self) -> T_co: ...

    class _CanClose(Protocol):
        def close(self) -> None: ...


# FileT needs to be covariant for the protocol trick to work - the real IO types are effectively a
# subtype of the protocols.
class AsyncIOWrapper(AsyncResource, Generic[FileT_co]):
    """A generic :class:`~io.IOBase` wrapper that implements the :term:`asynchronous
    file object` interface. Wrapped methods that could block are executed in
    :meth:`trio.to_thread.run_sync`.

    All properties and methods defined in :mod:`~io` are exposed by this
    wrapper, if they exist in the wrapped file object.
    """

    def __init__(self, file: FileT_co) -> None:
        self._wrapped = file

    @property
    def wrapped(self) -> FileT_co:
        """object: A reference to the wrapped file object"""

        return self._wrapped

    if not TYPE_CHECKING:

        def __getattr__(self, name: str) -> object:
            if name in _FILE_SYNC_ATTRS:
                return getattr(self._wrapped, name)
            if name in _FILE_ASYNC_METHODS:
                meth = getattr(self._wrapped, name)

                @async_wraps(self.__class__, self._wrapped.__class__, name)
                async def wrapper(
                    *args: Callable[..., T],
                    **kwargs: object | str | bool | CapacityLimiter | None,
                ) -> T:
                    func = partial(meth, *args, **kwargs)
                    return await trio.to_thread.run_sync(func)

                # cache the generated method
                setattr(self, name, wrapper)
                return wrapper

            raise AttributeError(name)

    def __dir__(self) -> Iterable[str]:
        attrs = set(super().__dir__())
        attrs.update(a for a in _FILE_SYNC_ATTRS if hasattr(self.wrapped, a))
        attrs.update(a for a in _FILE_ASYNC_METHODS if hasattr(self.wrapped, a))
        return attrs

    def __aiter__(self) -> AsyncIOWrapper[FileT_co]:
        return self

    async def __anext__(self: AsyncIOWrapper[_CanReadLine[AnyStr]]) -> AnyStr:
        line = await self.readline()
        if line:
            return line
        else:
            raise StopAsyncIteration

    async def detach(self: AsyncIOWrapper[_CanDetach[T]]) -> AsyncIOWrapper[T]:
        """Like :meth:`io.BufferedIOBase.detach`, but async.

        This also re-wraps the result in a new :term:`asynchronous file object`
        wrapper.

        """

        raw = await trio.to_thread.run_sync(self._wrapped.detach)
        return wrap_file(raw)

    async def aclose(self: AsyncIOWrapper[_CanClose]) -> None:
        """Like :meth:`io.IOBase.close`, but async.

        This is also shielded from cancellation; if a cancellation scope is
        cancelled, the wrapped file object will still be safely closed.

        """

        # ensure the underling file is closed during cancellation
        with trio.CancelScope(shield=True):
            await trio.to_thread.run_sync(self._wrapped.close)

        await trio.lowlevel.checkpoint_if_cancelled()

    if TYPE_CHECKING:
        # fmt: off
        # Based on typing.IO and io stubs.
        @property
        def closed(self: AsyncIOWrapper[_HasClosed]) -> bool: ...
        @property
        def encoding(self: AsyncIOWrapper[_HasEncoding]) -> str: ...
        @property
        def errors(self: AsyncIOWrapper[_HasErrors]) -> str | None: ...
        @property
        def newlines(self: AsyncIOWrapper[_HasNewlines[T]]) -> T: ...
        @property
        def buffer(self: AsyncIOWrapper[_HasBuffer]) -> BinaryIO: ...
        @property
        def raw(self: AsyncIOWrapper[_HasRaw]) -> io.RawIOBase: ...
        @property
        def line_buffering(self: AsyncIOWrapper[_HasLineBuffering]) -> int: ...
        @property
        def closefd(self: AsyncIOWrapper[_HasCloseFD]) -> bool: ...
        @property
        def name(self: AsyncIOWrapper[_HasName]) -> str: ...
        @property
        def mode(self: AsyncIOWrapper[_HasMode]) -> str: ...

        def fileno(self: AsyncIOWrapper[_HasFileNo]) -> int: ...
        def isatty(self: AsyncIOWrapper[_HasIsATTY]) -> bool: ...
        def readable(self: AsyncIOWrapper[_HasReadable]) -> bool: ...
        def seekable(self: AsyncIOWrapper[_HasSeekable]) -> bool: ...
        def writable(self: AsyncIOWrapper[_HasWritable]) -> bool: ...
        def getvalue(self: AsyncIOWrapper[_CanGetValue[AnyStr]]) -> AnyStr: ...
        def getbuffer(self: AsyncIOWrapper[_CanGetBuffer]) -> memoryview: ...
        async def flush(self: AsyncIOWrapper[_CanFlush]) -> None: ...
        async def read(self: AsyncIOWrapper[_CanRead[AnyStr]], size: int | None = -1, /) -> AnyStr: ...
        async def read1(self: AsyncIOWrapper[_CanRead1], size: int | None = -1, /) -> bytes: ...
        async def readall(self: AsyncIOWrapper[_CanReadAll[AnyStr]]) -> AnyStr: ...
        async def readinto(self: AsyncIOWrapper[_CanReadInto], buf: Buffer, /) -> int | None: ...
        async def readline(self: AsyncIOWrapper[_CanReadLine[AnyStr]], size: int = -1, /) -> AnyStr: ...
        async def readlines(self: AsyncIOWrapper[_CanReadLines[AnyStr]]) -> list[AnyStr]: ...
        async def seek(self: AsyncIOWrapper[_CanSeek], target: int, whence: int = 0, /) -> int: ...
        async def tell(self: AsyncIOWrapper[_CanTell]) -> int: ...
        async def truncate(self: AsyncIOWrapper[_CanTruncate], size: int | None = None, /) -> int: ...
        async def write(self: AsyncIOWrapper[_CanWrite[T]], data: T, /) -> int: ...
        async def writelines(self: AsyncIOWrapper[_CanWriteLines[T]], lines: Iterable[T], /) -> None: ...
        async def readinto1(self: AsyncIOWrapper[_CanReadInto1], buffer: Buffer, /) -> int: ...
        async def peek(self: AsyncIOWrapper[_CanPeek[AnyStr]], size: int = 0, /) -> AnyStr: ...


# Type hints are copied from builtin open.
_OpenFile = Union["StrOrBytesPath", int]
_Opener = Callable[[str, int], int]


@overload
async def open_file(
    file: _OpenFile,
    mode: OpenTextMode = "r",
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> AsyncIOWrapper[io.TextIOWrapper]: ...


@overload
async def open_file(
    file: _OpenFile,
    mode: OpenBinaryMode,
    buffering: Literal[0],
    encoding: None = None,
    errors: None = None,
    newline: None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> AsyncIOWrapper[io.FileIO]: ...


@overload
async def open_file(
    file: _OpenFile,
    mode: OpenBinaryModeUpdating,
    buffering: Literal[-1, 1] = -1,
    encoding: None = None,
    errors: None = None,
    newline: None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> AsyncIOWrapper[io.BufferedRandom]: ...


@overload
async def open_file(
    file: _OpenFile,
    mode: OpenBinaryModeWriting,
    buffering: Literal[-1, 1] = -1,
    encoding: None = None,
    errors: None = None,
    newline: None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> AsyncIOWrapper[io.BufferedWriter]: ...


@overload
async def open_file(
    file: _OpenFile,
    mode: OpenBinaryModeReading,
    buffering: Literal[-1, 1] = -1,
    encoding: None = None,
    errors: None = None,
    newline: None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> AsyncIOWrapper[io.BufferedReader]: ...


@overload
async def open_file(
    file: _OpenFile,
    mode: OpenBinaryMode,
    buffering: int,
    encoding: None = None,
    errors: None = None,
    newline: None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> AsyncIOWrapper[BinaryIO]: ...


@overload
async def open_file(  # type: ignore[explicit-any, misc]  # Any usage matches builtins.open().
    file: _OpenFile,
    mode: str,
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> AsyncIOWrapper[IO[Any]]: ...


async def open_file(
    file: _OpenFile,
    mode: str = "r",
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener: _Opener | None = None,
) -> AsyncIOWrapper[object]:
    """Asynchronous version of :func:`open`.

    Returns:
        An :term:`asynchronous file object`

    Example::

        async with await trio.open_file(filename) as f:
            async for line in f:
                pass

        assert f.closed

    See also:
      :func:`trio.Path.open`

    """
    file_ = wrap_file(
        await trio.to_thread.run_sync(
            io.open,
            file,
            mode,
            buffering,
            encoding,
            errors,
            newline,
            closefd,
            opener,
        ),
    )
    return file_


def wrap_file(file: FileT) -> AsyncIOWrapper[FileT]:
    """This wraps any file object in a wrapper that provides an asynchronous
    file object interface.

    Args:
        file: a :term:`file object`

    Returns:
        An :term:`asynchronous file object` that wraps ``file``

    Example::

        async_file = trio.wrap_file(StringIO('asdf'))

        assert await async_file.read() == 'asdf'

    """

    def has(attr: str) -> bool:
        return hasattr(file, attr) and callable(getattr(file, attr))

    if not (has("close") and (has("read") or has("write"))):
        raise TypeError(
            f"{file} does not implement required duck-file methods: "
            "close and (read or write)",
        )

    return AsyncIOWrapper(file)

# === NexusCore/openenv\Lib\site-packages\google\auth\_helpers.py ===
# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helper functions for commonly used utilities."""

import base64
import calendar
import datetime
from email.message import Message
import hashlib
import json
import logging
import sys
from typing import Any, Dict, Mapping, Optional, Union
import urllib

from google.auth import exceptions


# _BASE_LOGGER_NAME is the base logger for all google-based loggers.
_BASE_LOGGER_NAME = "google"

# _LOGGING_INITIALIZED ensures that base logger is only configured once
# (unless already configured by the end-user).
_LOGGING_INITIALIZED = False


# The smallest MDS cache used by this library stores tokens until 4 minutes from
# expiry.
REFRESH_THRESHOLD = datetime.timedelta(minutes=3, seconds=45)

# TODO(https://github.com/googleapis/google-auth-library-python/issues/1684): Audit and update the list below.
_SENSITIVE_FIELDS = {
    "accessToken",
    "access_token",
    "id_token",
    "client_id",
    "refresh_token",
    "client_secret",
}


def copy_docstring(source_class):
    """Decorator that copies a method's docstring from another class.

    Args:
        source_class (type): The class that has the documented method.

    Returns:
        Callable: A decorator that will copy the docstring of the same
            named method in the source class to the decorated method.
    """

    def decorator(method):
        """Decorator implementation.

        Args:
            method (Callable): The method to copy the docstring to.

        Returns:
            Callable: the same method passed in with an updated docstring.

        Raises:
            google.auth.exceptions.InvalidOperation: if the method already has a docstring.
        """
        if method.__doc__:
            raise exceptions.InvalidOperation("Method already has a docstring.")

        source_method = getattr(source_class, method.__name__)
        method.__doc__ = source_method.__doc__

        return method

    return decorator


def parse_content_type(header_value):
    """Parse a 'content-type' header value to get just the plain media-type (without parameters).

    This is done using the class Message from email.message as suggested in PEP 594
        (because the cgi is now deprecated and will be removed in python 3.13,
        see https://peps.python.org/pep-0594/#cgi).

    Args:
        header_value (str): The value of a 'content-type' header as a string.

    Returns:
        str: A string with just the lowercase media-type from the parsed 'content-type' header.
            If the provided content-type is not parsable, returns 'text/plain',
            the default value for textual files.
    """
    m = Message()
    m["content-type"] = header_value
    return (
        m.get_content_type()
    )  # Despite the name, actually returns just the media-type


def utcnow():
    """Returns the current UTC datetime.

    Returns:
        datetime: The current time in UTC.
    """
    # We used datetime.utcnow() before, since it's deprecated from python 3.12,
    # we are using datetime.now(timezone.utc) now. "utcnow()" is offset-native
    # (no timezone info), but "now()" is offset-aware (with timezone info).
    # This will cause datetime comparison problem. For backward compatibility,
    # we need to remove the timezone info.
    now = datetime.datetime.now(datetime.timezone.utc)
    now = now.replace(tzinfo=None)
    return now


def datetime_to_secs(value):
    """Convert a datetime object to the number of seconds since the UNIX epoch.

    Args:
        value (datetime): The datetime to convert.

    Returns:
        int: The number of seconds since the UNIX epoch.
    """
    return calendar.timegm(value.utctimetuple())


def to_bytes(value, encoding="utf-8"):
    """Converts a string value to bytes, if necessary.

    Args:
        value (Union[str, bytes]): The value to be converted.
        encoding (str): The encoding to use to convert unicode to bytes.
            Defaults to "utf-8".

    Returns:
        bytes: The original value converted to bytes (if unicode) or as
            passed in if it started out as bytes.

    Raises:
        google.auth.exceptions.InvalidValue: If the value could not be converted to bytes.
    """
    result = value.encode(encoding) if isinstance(value, str) else value
    if isinstance(result, bytes):
        return result
    else:
        raise exceptions.InvalidValue(
            "{0!r} could not be converted to bytes".format(value)
        )


def from_bytes(value):
    """Converts bytes to a string value, if necessary.

    Args:
        value (Union[str, bytes]): The value to be converted.

    Returns:
        str: The original value converted to unicode (if bytes) or as passed in
            if it started out as unicode.

    Raises:
        google.auth.exceptions.InvalidValue: If the value could not be converted to unicode.
    """
    result = value.decode("utf-8") if isinstance(value, bytes) else value
    if isinstance(result, str):
        return result
    else:
        raise exceptions.InvalidValue(
            "{0!r} could not be converted to unicode".format(value)
        )


def update_query(url, params, remove=None):
    """Updates a URL's query parameters.

    Replaces any current values if they are already present in the URL.

    Args:
        url (str): The URL to update.
        params (Mapping[str, str]): A mapping of query parameter
            keys to values.
        remove (Sequence[str]): Parameters to remove from the query string.

    Returns:
        str: The URL with updated query parameters.

    Examples:

        >>> url = 'http://example.com?a=1'
        >>> update_query(url, {'a': '2'})
        http://example.com?a=2
        >>> update_query(url, {'b': '3'})
        http://example.com?a=1&b=3
        >> update_query(url, {'b': '3'}, remove=['a'])
        http://example.com?b=3

    """
    if remove is None:
        remove = []

    # Split the URL into parts.
    parts = urllib.parse.urlparse(url)
    # Parse the query string.
    query_params = urllib.parse.parse_qs(parts.query)
    # Update the query parameters with the new parameters.
    query_params.update(params)
    # Remove any values specified in remove.
    query_params = {
        key: value for key, value in query_params.items() if key not in remove
    }
    # Re-encoded the query string.
    new_query = urllib.parse.urlencode(query_params, doseq=True)
    # Unsplit the url.
    new_parts = parts._replace(query=new_query)
    return urllib.parse.urlunparse(new_parts)


def scopes_to_string(scopes):
    """Converts scope value to a string suitable for sending to OAuth 2.0
    authorization servers.

    Args:
        scopes (Sequence[str]): The sequence of scopes to convert.

    Returns:
        str: The scopes formatted as a single string.
    """
    return " ".join(scopes)


def string_to_scopes(scopes):
    """Converts stringifed scopes value to a list.

    Args:
        scopes (Union[Sequence, str]): The string of space-separated scopes
            to convert.
    Returns:
        Sequence(str): The separated scopes.
    """
    if not scopes:
        return []

    return scopes.split(" ")


def padded_urlsafe_b64decode(value):
    """Decodes base64 strings lacking padding characters.

    Google infrastructure tends to omit the base64 padding characters.

    Args:
        value (Union[str, bytes]): The encoded value.

    Returns:
        bytes: The decoded value
    """
    b64string = to_bytes(value)
    padded = b64string + b"=" * (-len(b64string) % 4)
    return base64.urlsafe_b64decode(padded)


def unpadded_urlsafe_b64encode(value):
    """Encodes base64 strings removing any padding characters.

    `rfc 7515`_ defines Base64url to NOT include any padding
    characters, but the stdlib doesn't do that by default.

    _rfc7515: https://tools.ietf.org/html/rfc7515#page-6

    Args:
        value (Union[str|bytes]): The bytes-like value to encode

    Returns:
        Union[str|bytes]: The encoded value
    """
    return base64.urlsafe_b64encode(value).rstrip(b"=")


def is_python_3():
    """Check if the Python interpreter is Python 2 or 3.

    Returns:
        bool: True if the Python interpreter is Python 3 and False otherwise.
    """
    return sys.version_info > (3, 0)


def _hash_sensitive_info(data: Union[dict, list]) -> Union[dict, list, str]:
    """
    Hashes sensitive information within a dictionary.

    Args:
        data: The dictionary containing data to be processed.

    Returns:
        A new dictionary with sensitive values replaced by their SHA512 hashes.
        If the input is a list, returns a list with each element recursively processed.
        If the input is neither a dict nor a list, returns the type of the input as a string.

    """
    if isinstance(data, dict):
        hashed_data: Dict[Any, Union[Optional[str], dict, list]] = {}
        for key, value in data.items():
            if key in _SENSITIVE_FIELDS and not isinstance(value, (dict, list)):
                hashed_data[key] = _hash_value(value, key)
            elif isinstance(value, (dict, list)):
                hashed_data[key] = _hash_sensitive_info(value)
            else:
                hashed_data[key] = value
        return hashed_data
    elif isinstance(data, list):
        hashed_list = []
        for val in data:
            hashed_list.append(_hash_sensitive_info(val))
        return hashed_list
    else:
        # TODO(https://github.com/googleapis/google-auth-library-python/issues/1701):
        # Investigate and hash sensitive info before logging when the data type is
        # not a dict or a list.
        return str(type(data))


def _hash_value(value, field_name: str) -> Optional[str]:
    """Hashes a value and returns a formatted hash string."""
    if value is None:
        return None
    encoded_value = str(value).encode("utf-8")
    hash_object = hashlib.sha512()
    hash_object.update(encoded_value)
    hex_digest = hash_object.hexdigest()
    return f"hashed_{field_name}-{hex_digest}"


def _logger_configured(logger: logging.Logger) -> bool:
    """Determines whether `logger` has non-default configuration

    Args:
      logger: The logger to check.

    Returns:
      bool: Whether the logger has any non-default configuration.
    """
    return (
        logger.handlers != [] or logger.level != logging.NOTSET or not logger.propagate
    )


def is_logging_enabled(logger: logging.Logger) -> bool:
    """
    Checks if debug logging is enabled for the given logger.

    Args:
        logger: The logging.Logger instance to check.

    Returns:
        True if debug logging is enabled, False otherwise.
    """
    # NOTE: Log propagation to the root logger is disabled unless
    # the base logger i.e. logging.getLogger("google") is
    # explicitly configured by the end user. Ideally this
    # needs to happen in the client layer (already does for GAPICs).
    # However, this is implemented here to avoid logging
    # (if a root logger is configured) when a version of google-auth
    # which supports logging is used with:
    #  - an older version of a GAPIC which does not support logging.
    #  - Apiary client which does not support logging.
    global _LOGGING_INITIALIZED
    if not _LOGGING_INITIALIZED:
        base_logger = logging.getLogger(_BASE_LOGGER_NAME)
        if not _logger_configured(base_logger):
            base_logger.propagate = False
        _LOGGING_INITIALIZED = True

    return logger.isEnabledFor(logging.DEBUG)


def request_log(
    logger: logging.Logger,
    method: str,
    url: str,
    body: Optional[bytes],
    headers: Optional[Mapping[str, str]],
) -> None:
    """
    Logs an HTTP request at the DEBUG level if logging is enabled.

    Args:
        logger: The logging.Logger instance to use.
        method: The HTTP method (e.g., "GET", "POST").
        url: The URL of the request.
        body: The request body (can be None).
        headers: The request headers (can be None).
    """
    if is_logging_enabled(logger):
        content_type = (
            headers["Content-Type"] if headers and "Content-Type" in headers else ""
        )
        json_body = _parse_request_body(body, content_type=content_type)
        logged_body = _hash_sensitive_info(json_body)
        logger.debug(
            "Making request...",
            extra={
                "httpRequest": {
                    "method": method,
                    "url": url,
                    "body": logged_body,
                    "headers": headers,
                }
            },
        )


def _parse_request_body(body: Optional[bytes], content_type: str = "") -> Any:
    """
    Parses a request body, handling bytes and string types, and different content types.

    Args:
        body (Optional[bytes]): The request body.
        content_type (str): The content type of the request body, e.g., "application/json",
            "application/x-www-form-urlencoded", or "text/plain". If empty, attempts
            to parse as JSON.

    Returns:
        Parsed body (dict, str, or None).
        - JSON: Decodes if content_type is "application/json" or None (fallback).
        - URL-encoded: Parses if content_type is "application/x-www-form-urlencoded".
        - Plain text: Returns string if content_type is "text/plain".
        - None: Returns if body is None, UTF-8 decode fails, or content_type is unknown.
    """
    if body is None:
        return None
    try:
        body_str = body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        return None
    content_type = content_type.lower()
    if not content_type or "application/json" in content_type:
        try:
            return json.loads(body_str)
        except (json.JSONDecodeError, TypeError):
            return body_str
    if "application/x-www-form-urlencoded" in content_type:
        parsed_query = urllib.parse.parse_qs(body_str)
        result = {k: v[0] for k, v in parsed_query.items()}
        return result
    if "text/plain" in content_type:
        return body_str
    return None


def _parse_response(response: Any) -> Any:
    """
    Parses a response, attempting to decode JSON.

    Args:
        response: The response object to parse. This can be any type, but
            it is expected to have a `json()` method if it contains JSON.

    Returns:
        The parsed response. If the response contains valid JSON, the
        decoded JSON object (e.g., a dictionary or list) is returned.
        If the response does not have a `json()` method or if the JSON
        decoding fails, None is returned.
    """
    try:
        json_response = response.json()
        return json_response
    except Exception:
        # TODO(https://github.com/googleapis/google-auth-library-python/issues/1744):
        # Parse and return response payload as json based on different content types.
        return None


def _response_log_base(logger: logging.Logger, parsed_response: Any) -> None:
    """
    Logs a parsed HTTP response at the DEBUG level.

    This internal helper function takes a parsed response and logs it
    using the provided logger. It also applies a hashing function to
    potentially sensitive information before logging.

    Args:
        logger: The logging.Logger instance to use for logging.
        parsed_response: The parsed HTTP response object (e.g., a dictionary,
            list, or the original response if parsing failed).
    """

    logged_response = _hash_sensitive_info(parsed_response)
    logger.debug("Response received...", extra={"httpResponse": logged_response})


def response_log(logger: logging.Logger, response: Any) -> None:
    """
    Logs an HTTP response at the DEBUG level if logging is enabled.

    Args:
        logger: The logging.Logger instance to use.
        response: The HTTP response object to log.
    """
    if is_logging_enabled(logger):
        json_response = _parse_response(response)
        _response_log_base(logger, json_response)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\objective.py ===
"""
    pygments.lexers.objective
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for Objective-C family languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, using, this, words, \
    inherit, default
from pygments.token import Text, Keyword, Name, String, Operator, \
    Number, Punctuation, Literal, Comment, Whitespace

from pygments.lexers.c_cpp import CLexer, CppLexer

__all__ = ['ObjectiveCLexer', 'ObjectiveCppLexer', 'LogosLexer', 'SwiftLexer']


def objective(baselexer):
    """
    Generate a subclass of baselexer that accepts the Objective-C syntax
    extensions.
    """

    # Have to be careful not to accidentally match JavaDoc/Doxygen syntax here,
    # since that's quite common in ordinary C/C++ files.  It's OK to match
    # JavaDoc/Doxygen keywords that only apply to Objective-C, mind.
    #
    # The upshot of this is that we CANNOT match @class or @interface
    _oc_keywords = re.compile(r'@(?:end|implementation|protocol)')

    # Matches [ <ws>? identifier <ws> ( identifier <ws>? ] |  identifier? : )
    # (note the identifier is *optional* when there is a ':'!)
    _oc_message = re.compile(r'\[\s*[a-zA-Z_]\w*\s+'
                             r'(?:[a-zA-Z_]\w*\s*\]|'
                             r'(?:[a-zA-Z_]\w*)?:)')

    class GeneratedObjectiveCVariant(baselexer):
        """
        Implements Objective-C syntax on top of an existing C family lexer.
        """

        tokens = {
            'statements': [
                (r'@"', String, 'string'),
                (r'@(YES|NO)', Number),
                (r"@'(\\.|\\[0-7]{1,3}|\\x[a-fA-F0-9]{1,2}|[^\\\'\n])'", String.Char),
                (r'@(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d+[lL]?', Number.Float),
                (r'@(\d+\.\d*|\.\d+|\d+[fF])[fF]?', Number.Float),
                (r'@0x[0-9a-fA-F]+[Ll]?', Number.Hex),
                (r'@0[0-7]+[Ll]?', Number.Oct),
                (r'@\d+[Ll]?', Number.Integer),
                (r'@\(', Literal, 'literal_number'),
                (r'@\[', Literal, 'literal_array'),
                (r'@\{', Literal, 'literal_dictionary'),
                (words((
                    '@selector', '@private', '@protected', '@public', '@encode',
                    '@synchronized', '@try', '@throw', '@catch', '@finally',
                    '@end', '@property', '@synthesize', '__bridge', '__bridge_transfer',
                    '__autoreleasing', '__block', '__weak', '__strong', 'weak', 'strong',
                    'copy', 'retain', 'assign', 'unsafe_unretained', 'atomic', 'nonatomic',
                    'readonly', 'readwrite', 'setter', 'getter', 'typeof', 'in',
                    'out', 'inout', 'release', 'class', '@dynamic', '@optional',
                    '@required', '@autoreleasepool', '@import'), suffix=r'\b'),
                 Keyword),
                (words(('id', 'instancetype', 'Class', 'IMP', 'SEL', 'BOOL',
                        'IBOutlet', 'IBAction', 'unichar'), suffix=r'\b'),
                 Keyword.Type),
                (r'@(true|false|YES|NO)\n', Name.Builtin),
                (r'(YES|NO|nil|self|super)\b', Name.Builtin),
                # Carbon types
                (r'(Boolean|UInt8|SInt8|UInt16|SInt16|UInt32|SInt32)\b', Keyword.Type),
                # Carbon built-ins
                (r'(TRUE|FALSE)\b', Name.Builtin),
                (r'(@interface|@implementation)(\s+)', bygroups(Keyword, Text),
                 ('#pop', 'oc_classname')),
                (r'(@class|@protocol)(\s+)', bygroups(Keyword, Text),
                 ('#pop', 'oc_forward_classname')),
                # @ can also prefix other expressions like @{...} or @(...)
                (r'@', Punctuation),
                inherit,
            ],
            'oc_classname': [
                # interface definition that inherits
                (r'([a-zA-Z$_][\w$]*)(\s*:\s*)([a-zA-Z$_][\w$]*)?(\s*)(\{)',
                 bygroups(Name.Class, Text, Name.Class, Text, Punctuation),
                 ('#pop', 'oc_ivars')),
                (r'([a-zA-Z$_][\w$]*)(\s*:\s*)([a-zA-Z$_][\w$]*)?',
                 bygroups(Name.Class, Text, Name.Class), '#pop'),
                # interface definition for a category
                (r'([a-zA-Z$_][\w$]*)(\s*)(\([a-zA-Z$_][\w$]*\))(\s*)(\{)',
                 bygroups(Name.Class, Text, Name.Label, Text, Punctuation),
                 ('#pop', 'oc_ivars')),
                (r'([a-zA-Z$_][\w$]*)(\s*)(\([a-zA-Z$_][\w$]*\))',
                 bygroups(Name.Class, Text, Name.Label), '#pop'),
                # simple interface / implementation
                (r'([a-zA-Z$_][\w$]*)(\s*)(\{)',
                 bygroups(Name.Class, Text, Punctuation), ('#pop', 'oc_ivars')),
                (r'([a-zA-Z$_][\w$]*)', Name.Class, '#pop')
            ],
            'oc_forward_classname': [
                (r'([a-zA-Z$_][\w$]*)(\s*,\s*)',
                 bygroups(Name.Class, Text), 'oc_forward_classname'),
                (r'([a-zA-Z$_][\w$]*)(\s*;?)',
                 bygroups(Name.Class, Text), '#pop')
            ],
            'oc_ivars': [
                include('whitespace'),
                include('statements'),
                (';', Punctuation),
                (r'\{', Punctuation, '#push'),
                (r'\}', Punctuation, '#pop'),
            ],
            'root': [
                # methods
                (r'^([-+])(\s*)'                         # method marker
                 r'(\(.*?\))?(\s*)'                      # return type
                 r'([a-zA-Z$_][\w$]*:?)',        # begin of method name
                 bygroups(Punctuation, Text, using(this),
                          Text, Name.Function),
                 'method'),
                inherit,
            ],
            'method': [
                include('whitespace'),
                # TODO unsure if ellipses are allowed elsewhere, see
                # discussion in Issue 789
                (r',', Punctuation),
                (r'\.\.\.', Punctuation),
                (r'(\(.*?\))(\s*)([a-zA-Z$_][\w$]*)',
                 bygroups(using(this), Text, Name.Variable)),
                (r'[a-zA-Z$_][\w$]*:', Name.Function),
                (';', Punctuation, '#pop'),
                (r'\{', Punctuation, 'function'),
                default('#pop'),
            ],
            'literal_number': [
                (r'\(', Punctuation, 'literal_number_inner'),
                (r'\)', Literal, '#pop'),
                include('statement'),
            ],
            'literal_number_inner': [
                (r'\(', Punctuation, '#push'),
                (r'\)', Punctuation, '#pop'),
                include('statement'),
            ],
            'literal_array': [
                (r'\[', Punctuation, 'literal_array_inner'),
                (r'\]', Literal, '#pop'),
                include('statement'),
            ],
            'literal_array_inner': [
                (r'\[', Punctuation, '#push'),
                (r'\]', Punctuation, '#pop'),
                include('statement'),
            ],
            'literal_dictionary': [
                (r'\}', Literal, '#pop'),
                include('statement'),
            ],
        }

        def analyse_text(text):
            if _oc_keywords.search(text):
                return 1.0
            elif '@"' in text:  # strings
                return 0.8
            elif re.search('@[0-9]+', text):
                return 0.7
            elif _oc_message.search(text):
                return 0.8
            return 0

        def get_tokens_unprocessed(self, text, stack=('root',)):
            from pygments.lexers._cocoa_builtins import COCOA_INTERFACES, \
                COCOA_PROTOCOLS, COCOA_PRIMITIVES

            for index, token, value in \
                    baselexer.get_tokens_unprocessed(self, text, stack):
                if token is Name or token is Name.Class:
                    if value in COCOA_INTERFACES or value in COCOA_PROTOCOLS \
                       or value in COCOA_PRIMITIVES:
                        token = Name.Builtin.Pseudo

                yield index, token, value

    return GeneratedObjectiveCVariant


class ObjectiveCLexer(objective(CLexer)):
    """
    For Objective-C source code with preprocessor directives.
    """

    name = 'Objective-C'
    url = 'https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/ProgrammingWithObjectiveC/Introduction/Introduction.html'
    aliases = ['objective-c', 'objectivec', 'obj-c', 'objc']
    filenames = ['*.m', '*.h']
    mimetypes = ['text/x-objective-c']
    version_added = ''
    priority = 0.05    # Lower than C


class ObjectiveCppLexer(objective(CppLexer)):
    """
    For Objective-C++ source code with preprocessor directives.
    """

    name = 'Objective-C++'
    aliases = ['objective-c++', 'objectivec++', 'obj-c++', 'objc++']
    filenames = ['*.mm', '*.hh']
    mimetypes = ['text/x-objective-c++']
    version_added = ''
    priority = 0.05    # Lower than C++


class LogosLexer(ObjectiveCppLexer):
    """
    For Logos + Objective-C source code with preprocessor directives.
    """

    name = 'Logos'
    aliases = ['logos']
    filenames = ['*.x', '*.xi', '*.xm', '*.xmi']
    mimetypes = ['text/x-logos']
    version_added = '1.6'
    priority = 0.25

    tokens = {
        'statements': [
            (r'(%orig|%log)\b', Keyword),
            (r'(%c)\b(\()(\s*)([a-zA-Z$_][\w$]*)(\s*)(\))',
             bygroups(Keyword, Punctuation, Text, Name.Class, Text, Punctuation)),
            (r'(%init)\b(\()',
             bygroups(Keyword, Punctuation), 'logos_init_directive'),
            (r'(%init)(?=\s*;)', bygroups(Keyword)),
            (r'(%hook|%group)(\s+)([a-zA-Z$_][\w$]+)',
             bygroups(Keyword, Text, Name.Class), '#pop'),
            (r'(%subclass)(\s+)', bygroups(Keyword, Text),
             ('#pop', 'logos_classname')),
            inherit,
        ],
        'logos_init_directive': [
            (r'\s+', Text),
            (',', Punctuation, ('logos_init_directive', '#pop')),
            (r'([a-zA-Z$_][\w$]*)(\s*)(=)(\s*)([^);]*)',
             bygroups(Name.Class, Text, Punctuation, Text, Text)),
            (r'([a-zA-Z$_][\w$]*)', Name.Class),
            (r'\)', Punctuation, '#pop'),
        ],
        'logos_classname': [
            (r'([a-zA-Z$_][\w$]*)(\s*:\s*)([a-zA-Z$_][\w$]*)?',
             bygroups(Name.Class, Text, Name.Class), '#pop'),
            (r'([a-zA-Z$_][\w$]*)', Name.Class, '#pop')
        ],
        'root': [
            (r'(%subclass)(\s+)', bygroups(Keyword, Text),
             'logos_classname'),
            (r'(%hook|%group)(\s+)([a-zA-Z$_][\w$]+)',
             bygroups(Keyword, Text, Name.Class)),
            (r'(%config)(\s*\(\s*)(\w+)(\s*=)(.*?)(\)\s*)',
             bygroups(Keyword, Text, Name.Variable, Text, String, Text)),
            (r'(%ctor)(\s*)(\{)', bygroups(Keyword, Text, Punctuation),
             'function'),
            (r'(%new)(\s*)(\()(.*?)(\))',
             bygroups(Keyword, Text, Keyword, String, Keyword)),
            (r'(\s*)(%end)(\s*)', bygroups(Text, Keyword, Text)),
            inherit,
        ],
    }

    _logos_keywords = re.compile(r'%(?:hook|ctor|init|c\()')

    def analyse_text(text):
        if LogosLexer._logos_keywords.search(text):
            return 1.0
        return 0


class SwiftLexer(RegexLexer):
    """
    For Swift source.
    """
    name = 'Swift'
    url = 'https://www.swift.org/'
    filenames = ['*.swift']
    aliases = ['swift']
    mimetypes = ['text/x-swift']
    version_added = '2.0'

    tokens = {
        'root': [
            # Whitespace and Comments
            (r'\n', Text),
            (r'\s+', Whitespace),
            (r'//', Comment.Single, 'comment-single'),
            (r'/\*', Comment.Multiline, 'comment-multi'),
            (r'#(if|elseif|else|endif|available)\b', Comment.Preproc, 'preproc'),

            # Keywords
            include('keywords'),

            # Global Types
            (words((
                'Array', 'AutoreleasingUnsafeMutablePointer', 'BidirectionalReverseView',
                'Bit', 'Bool', 'CFunctionPointer', 'COpaquePointer', 'CVaListPointer',
                'Character', 'ClosedInterval', 'CollectionOfOne', 'ContiguousArray',
                'Dictionary', 'DictionaryGenerator', 'DictionaryIndex', 'Double',
                'EmptyCollection', 'EmptyGenerator', 'EnumerateGenerator',
                'EnumerateSequence', 'FilterCollectionView',
                'FilterCollectionViewIndex', 'FilterGenerator', 'FilterSequenceView',
                'Float', 'Float80', 'FloatingPointClassification', 'GeneratorOf',
                'GeneratorOfOne', 'GeneratorSequence', 'HalfOpenInterval', 'HeapBuffer',
                'HeapBufferStorage', 'ImplicitlyUnwrappedOptional', 'IndexingGenerator',
                'Int', 'Int16', 'Int32', 'Int64', 'Int8', 'LazyBidirectionalCollection',
                'LazyForwardCollection', 'LazyRandomAccessCollection',
                'LazySequence', 'MapCollectionView', 'MapSequenceGenerator',
                'MapSequenceView', 'MirrorDisposition', 'ObjectIdentifier', 'OnHeap',
                'Optional', 'PermutationGenerator', 'QuickLookObject',
                'RandomAccessReverseView', 'Range', 'RangeGenerator', 'RawByte', 'Repeat',
                'ReverseBidirectionalIndex', 'ReverseRandomAccessIndex', 'SequenceOf',
                'SinkOf', 'Slice', 'StaticString', 'StrideThrough', 'StrideThroughGenerator',
                'StrideTo', 'StrideToGenerator', 'String', 'UInt', 'UInt16', 'UInt32',
                'UInt64', 'UInt8', 'UTF16', 'UTF32', 'UTF8', 'UnicodeDecodingResult',
                'UnicodeScalar', 'Unmanaged', 'UnsafeBufferPointer',
                'UnsafeBufferPointerGenerator', 'UnsafeMutableBufferPointer',
                'UnsafeMutablePointer', 'UnsafePointer', 'Zip2', 'ZipGenerator2',
                # Protocols
                'AbsoluteValuable', 'AnyObject', 'ArrayLiteralConvertible',
                'BidirectionalIndexType', 'BitwiseOperationsType',
                'BooleanLiteralConvertible', 'BooleanType', 'CVarArgType',
                'CollectionType', 'Comparable', 'DebugPrintable',
                'DictionaryLiteralConvertible', 'Equatable',
                'ExtendedGraphemeClusterLiteralConvertible',
                'ExtensibleCollectionType', 'FloatLiteralConvertible',
                'FloatingPointType', 'ForwardIndexType', 'GeneratorType', 'Hashable',
                'IntegerArithmeticType', 'IntegerLiteralConvertible', 'IntegerType',
                'IntervalType', 'MirrorType', 'MutableCollectionType', 'MutableSliceable',
                'NilLiteralConvertible', 'OutputStreamType', 'Printable',
                'RandomAccessIndexType', 'RangeReplaceableCollectionType',
                'RawOptionSetType', 'RawRepresentable', 'Reflectable', 'SequenceType',
                'SignedIntegerType', 'SignedNumberType', 'SinkType', 'Sliceable',
                'Streamable', 'Strideable', 'StringInterpolationConvertible',
                'StringLiteralConvertible', 'UnicodeCodecType',
                'UnicodeScalarLiteralConvertible', 'UnsignedIntegerType',
                '_ArrayBufferType', '_BidirectionalIndexType', '_CocoaStringType',
                '_CollectionType', '_Comparable', '_ExtensibleCollectionType',
                '_ForwardIndexType', '_Incrementable', '_IntegerArithmeticType',
                '_IntegerType', '_ObjectiveCBridgeable', '_RandomAccessIndexType',
                '_RawOptionSetType', '_SequenceType', '_Sequence_Type',
                '_SignedIntegerType', '_SignedNumberType', '_Sliceable', '_Strideable',
                '_SwiftNSArrayRequiredOverridesType', '_SwiftNSArrayType',
                '_SwiftNSCopyingType', '_SwiftNSDictionaryRequiredOverridesType',
                '_SwiftNSDictionaryType', '_SwiftNSEnumeratorType',
                '_SwiftNSFastEnumerationType', '_SwiftNSStringRequiredOverridesType',
                '_SwiftNSStringType', '_UnsignedIntegerType',
                # Variables
                'C_ARGC', 'C_ARGV', 'Process',
                # Typealiases
                'Any', 'AnyClass', 'BooleanLiteralType', 'CBool', 'CChar', 'CChar16',
                'CChar32', 'CDouble', 'CFloat', 'CInt', 'CLong', 'CLongLong', 'CShort',
                'CSignedChar', 'CUnsignedInt', 'CUnsignedLong', 'CUnsignedShort',
                'CWideChar', 'ExtendedGraphemeClusterType', 'Float32', 'Float64',
                'FloatLiteralType', 'IntMax', 'IntegerLiteralType', 'StringLiteralType',
                'UIntMax', 'UWord', 'UnicodeScalarType', 'Void', 'Word',
                # Foundation/Cocoa
                'NSErrorPointer', 'NSObjectProtocol', 'Selector'), suffix=r'\b'),
             Name.Builtin),
            # Functions
            (words((
                'abs', 'advance', 'alignof', 'alignofValue', 'assert', 'assertionFailure',
                'contains', 'count', 'countElements', 'debugPrint', 'debugPrintln',
                'distance', 'dropFirst', 'dropLast', 'dump', 'enumerate', 'equal',
                'extend', 'fatalError', 'filter', 'find', 'first', 'getVaList', 'indices',
                'insert', 'isEmpty', 'join', 'last', 'lazy', 'lexicographicalCompare',
                'map', 'max', 'maxElement', 'min', 'minElement', 'numericCast', 'overlaps',
                'partition', 'precondition', 'preconditionFailure', 'prefix', 'print',
                'println', 'reduce', 'reflect', 'removeAll', 'removeAtIndex', 'removeLast',
                'removeRange', 'reverse', 'sizeof', 'sizeofValue', 'sort', 'sorted',
                'splice', 'split', 'startsWith', 'stride', 'strideof', 'strideofValue',
                'suffix', 'swap', 'toDebugString', 'toString', 'transcode',
                'underestimateCount', 'unsafeAddressOf', 'unsafeBitCast', 'unsafeDowncast',
                'withExtendedLifetime', 'withUnsafeMutablePointer',
                'withUnsafeMutablePointers', 'withUnsafePointer', 'withUnsafePointers',
                'withVaList'), suffix=r'\b'),
             Name.Builtin.Pseudo),

            # Implicit Block Variables
            (r'\$\d+', Name.Variable),

            # Binary Literal
            (r'0b[01_]+', Number.Bin),
            # Octal Literal
            (r'0o[0-7_]+', Number.Oct),
            # Hexadecimal Literal
            (r'0x[0-9a-fA-F_]+', Number.Hex),
            # Decimal Literal
            (r'[0-9][0-9_]*(\.[0-9_]+[eE][+\-]?[0-9_]+|'
             r'\.[0-9_]*|[eE][+\-]?[0-9_]+)', Number.Float),
            (r'[0-9][0-9_]*', Number.Integer),
            # String Literal
            (r'"""', String, 'string-multi'),
            (r'"', String, 'string'),

            # Operators and Punctuation
            (r'[(){}\[\].,:;=@#`?]|->|[<&?](?=\w)|(?<=\w)[>!?]', Punctuation),
            (r'[/=\-+!*%<>&|^?~]+', Operator),

            # Identifier
            (r'[a-zA-Z_]\w*', Name)
        ],
        'keywords': [
            (words((
                'as', 'async', 'await', 'break', 'case', 'catch', 'continue', 'default', 'defer',
                'do', 'else', 'fallthrough', 'for', 'guard', 'if', 'in', 'is',
                'repeat', 'return', '#selector', 'switch', 'throw', 'try',
                'where', 'while'), suffix=r'\b'),
             Keyword),
            (r'@availability\([^)]+\)', Keyword.Reserved),
            (words((
                'associativity', 'convenience', 'dynamic', 'didSet', 'final',
                'get', 'indirect', 'infix', 'inout', 'lazy', 'left', 'mutating',
                'none', 'nonmutating', 'optional', 'override', 'postfix',
                'precedence', 'prefix', 'Protocol', 'required', 'rethrows',
                'right', 'set', 'throws', 'Type', 'unowned', 'weak', 'willSet',
                '@availability', '@autoclosure', '@noreturn',
                '@NSApplicationMain', '@NSCopying', '@NSManaged', '@objc',
                '@UIApplicationMain', '@IBAction', '@IBDesignable',
                '@IBInspectable', '@IBOutlet'), suffix=r'\b'),
             Keyword.Reserved),
            (r'(as|dynamicType|false|is|nil|self|Self|super|true|__COLUMN__'
             r'|__FILE__|__FUNCTION__|__LINE__|_'
             r'|#(?:file|line|column|function))\b', Keyword.Constant),
            (r'import\b', Keyword.Declaration, 'module'),
            (r'(class|enum|extension|struct|protocol)(\s+)([a-zA-Z_]\w*)',
             bygroups(Keyword.Declaration, Whitespace, Name.Class)),
            (r'(func)(\s+)([a-zA-Z_]\w*)',
             bygroups(Keyword.Declaration, Whitespace, Name.Function)),
            (r'(var|let)(\s+)([a-zA-Z_]\w*)', bygroups(Keyword.Declaration,
             Whitespace, Name.Variable)),
            (words((
                'actor', 'associatedtype', 'class', 'deinit', 'enum', 'extension', 'func', 'import',
                'init', 'internal', 'let', 'operator', 'private', 'protocol', 'public',
                'static', 'struct', 'subscript', 'typealias', 'var'), suffix=r'\b'),
             Keyword.Declaration)
        ],
        'comment': [
            (r':param: [a-zA-Z_]\w*|:returns?:|(FIXME|MARK|TODO):',
             Comment.Special)
        ],

        # Nested
        'comment-single': [
            (r'\n', Whitespace, '#pop'),
            include('comment'),
            (r'[^\n]+', Comment.Single)
        ],
        'comment-multi': [
            include('comment'),
            (r'[^*/]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]+', Comment.Multiline)
        ],
        'module': [
            (r'\n', Whitespace, '#pop'),
            (r'[a-zA-Z_]\w*', Name.Class),
            include('root')
        ],
        'preproc': [
            (r'\n', Whitespace, '#pop'),
            include('keywords'),
            (r'[A-Za-z]\w*', Comment.Preproc),
            include('root')
        ],
        'string': [
            (r'"', String, '#pop'),
            include("string-common"),
        ],
        'string-multi': [
            (r'"""', String, '#pop'),
            include("string-common"),
        ],
        'string-common': [
            (r'\\\(', String.Interpol, 'string-intp'),
            (r"""\\['"\\nrt]|\\x[0-9a-fA-F]{2}|\\[0-7]{1,3}"""
             r"""|\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}""", String.Escape),
            (r'[^\\"]+', String),
            (r'\\', String)
        ],
        'string-intp': [
            (r'\(', String.Interpol, '#push'),
            (r'\)', String.Interpol, '#pop'),
            include('root')
        ]
    }

    def get_tokens_unprocessed(self, text):
        from pygments.lexers._cocoa_builtins import COCOA_INTERFACES, \
            COCOA_PROTOCOLS, COCOA_PRIMITIVES

        for index, token, value in \
                RegexLexer.get_tokens_unprocessed(self, text):
            if token is Name or token is Name.Class:
                if value in COCOA_INTERFACES or value in COCOA_PROTOCOLS \
                   or value in COCOA_PRIMITIVES:
                    token = Name.Builtin.Pseudo

            yield index, token, value

# === NexusCore/openenv\Lib\site-packages\google\auth\downscoped.py ===
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Downscoping with Credential Access Boundaries

This module provides the ability to downscope credentials using
`Downscoping with Credential Access Boundaries`_. This is useful to restrict the
Identity and Access Management (IAM) permissions that a short-lived credential
can use.

To downscope permissions of a source credential, a Credential Access Boundary
that specifies which resources the new credential can access, as well as
an upper bound on the permissions that are available on each resource, has to
be defined. A downscoped credential can then be instantiated using the source
credential and the Credential Access Boundary.

The common pattern of usage is to have a token broker with elevated access
generate these downscoped credentials from higher access source credentials and
pass the downscoped short-lived access tokens to a token consumer via some
secure authenticated channel for limited access to Google Cloud Storage
resources.

For example, a token broker can be set up on a server in a private network.
Various workloads (token consumers) in the same network will send authenticated
requests to that broker for downscoped tokens to access or modify specific google
cloud storage buckets.

The broker will instantiate downscoped credentials instances that can be used to
generate short lived downscoped access tokens that can be passed to the token
consumer. These downscoped access tokens can be injected by the consumer into
google.oauth2.Credentials and used to initialize a storage client instance to
access Google Cloud Storage resources with restricted access.

Note: Only Cloud Storage supports Credential Access Boundaries. Other Google
Cloud services do not support this feature.

.. _Downscoping with Credential Access Boundaries: https://cloud.google.com/iam/docs/downscoping-short-lived-credentials
"""

import datetime

from google.auth import _helpers
from google.auth import credentials
from google.auth import exceptions
from google.oauth2 import sts

# The maximum number of access boundary rules a Credential Access Boundary can
# contain.
_MAX_ACCESS_BOUNDARY_RULES_COUNT = 10
# The token exchange grant_type used for exchanging credentials.
_STS_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:token-exchange"
# The token exchange requested_token_type. This is always an access_token.
_STS_REQUESTED_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"
# The STS token URL used to exchanged a short lived access token for a downscoped one.
_STS_TOKEN_URL_PATTERN = "https://sts.{}/v1/token"
# The subject token type to use when exchanging a short lived access token for a
# downscoped token.
_STS_SUBJECT_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"


class CredentialAccessBoundary(object):
    """Defines a Credential Access Boundary which contains a list of access boundary
    rules. Each rule contains information on the resource that the rule applies to,
    the upper bound of the permissions that are available on that resource and an
    optional condition to further restrict permissions.
    """

    def __init__(self, rules=[]):
        """Instantiates a Credential Access Boundary. A Credential Access Boundary
        can contain up to 10 access boundary rules.

        Args:
            rules (Sequence[google.auth.downscoped.AccessBoundaryRule]): The list of
                access boundary rules limiting the access that a downscoped credential
                will have.
        Raises:
            InvalidType: If any of the rules are not a valid type.
            InvalidValue: If the provided rules exceed the maximum allowed.
        """
        self.rules = rules

    @property
    def rules(self):
        """Returns the list of access boundary rules defined on the Credential
        Access Boundary.

        Returns:
            Tuple[google.auth.downscoped.AccessBoundaryRule, ...]: The list of access
                boundary rules defined on the Credential Access Boundary. These are returned
                as an immutable tuple to prevent modification.
        """
        return tuple(self._rules)

    @rules.setter
    def rules(self, value):
        """Updates the current rules on the Credential Access Boundary. This will overwrite
        the existing set of rules.

        Args:
            value (Sequence[google.auth.downscoped.AccessBoundaryRule]): The list of
                access boundary rules limiting the access that a downscoped credential
                will have.
        Raises:
            InvalidType: If any of the rules are not a valid type.
            InvalidValue: If the provided rules exceed the maximum allowed.
        """
        if len(value) > _MAX_ACCESS_BOUNDARY_RULES_COUNT:
            raise exceptions.InvalidValue(
                "Credential access boundary rules can have a maximum of {} rules.".format(
                    _MAX_ACCESS_BOUNDARY_RULES_COUNT
                )
            )
        for access_boundary_rule in value:
            if not isinstance(access_boundary_rule, AccessBoundaryRule):
                raise exceptions.InvalidType(
                    "List of rules provided do not contain a valid 'google.auth.downscoped.AccessBoundaryRule'."
                )
        # Make a copy of the original list.
        self._rules = list(value)

    def add_rule(self, rule):
        """Adds a single access boundary rule to the existing rules.

        Args:
            rule (google.auth.downscoped.AccessBoundaryRule): The access boundary rule,
                limiting the access that a downscoped credential will have, to be added to
                the existing rules.
        Raises:
            InvalidType: If any of the rules are not a valid type.
            InvalidValue: If the provided rules exceed the maximum allowed.
        """
        if len(self.rules) == _MAX_ACCESS_BOUNDARY_RULES_COUNT:
            raise exceptions.InvalidValue(
                "Credential access boundary rules can have a maximum of {} rules.".format(
                    _MAX_ACCESS_BOUNDARY_RULES_COUNT
                )
            )
        if not isinstance(rule, AccessBoundaryRule):
            raise exceptions.InvalidType(
                "The provided rule does not contain a valid 'google.auth.downscoped.AccessBoundaryRule'."
            )
        self._rules.append(rule)

    def to_json(self):
        """Generates the dictionary representation of the Credential Access Boundary.
        This uses the format expected by the Security Token Service API as documented in
        `Defining a Credential Access Boundary`_.

        .. _Defining a Credential Access Boundary:
            https://cloud.google.com/iam/docs/downscoping-short-lived-credentials#define-boundary

        Returns:
            Mapping: Credential Access Boundary Rule represented in a dictionary object.
        """
        rules = []
        for access_boundary_rule in self.rules:
            rules.append(access_boundary_rule.to_json())

        return {"accessBoundary": {"accessBoundaryRules": rules}}


class AccessBoundaryRule(object):
    """Defines an access boundary rule which contains information on the resource that
    the rule applies to, the upper bound of the permissions that are available on that
    resource and an optional condition to further restrict permissions.
    """

    def __init__(
        self, available_resource, available_permissions, availability_condition=None
    ):
        """Instantiates a single access boundary rule.

        Args:
            available_resource (str): The full resource name of the Cloud Storage bucket
                that the rule applies to. Use the format
                "//storage.googleapis.com/projects/_/buckets/bucket-name".
            available_permissions (Sequence[str]): A list defining the upper bound that
                the downscoped token will have on the available permissions for the
                resource. Each value is the identifier for an IAM predefined role or
                custom role, with the prefix "inRole:". For example:
                "inRole:roles/storage.objectViewer".
                Only the permissions in these roles will be available.
            availability_condition (Optional[google.auth.downscoped.AvailabilityCondition]):
                Optional condition that restricts the availability of permissions to
                specific Cloud Storage objects.

        Raises:
            InvalidType: If any of the parameters are not of the expected types.
            InvalidValue: If any of the parameters are not of the expected values.
        """
        self.available_resource = available_resource
        self.available_permissions = available_permissions
        self.availability_condition = availability_condition

    @property
    def available_resource(self):
        """Returns the current available resource.

        Returns:
           str: The current available resource.
        """
        return self._available_resource

    @available_resource.setter
    def available_resource(self, value):
        """Updates the current available resource.

        Args:
            value (str): The updated value of the available resource.

        Raises:
            google.auth.exceptions.InvalidType: If the value is not a string.
        """
        if not isinstance(value, str):
            raise exceptions.InvalidType(
                "The provided available_resource is not a string."
            )
        self._available_resource = value

    @property
    def available_permissions(self):
        """Returns the current available permissions.

        Returns:
           Tuple[str, ...]: The current available permissions. These are returned
               as an immutable tuple to prevent modification.
        """
        return tuple(self._available_permissions)

    @available_permissions.setter
    def available_permissions(self, value):
        """Updates the current available permissions.

        Args:
            value (Sequence[str]): The updated value of the available permissions.

        Raises:
            InvalidType: If the value is not a list of strings.
            InvalidValue: If the value is not valid.
        """
        for available_permission in value:
            if not isinstance(available_permission, str):
                raise exceptions.InvalidType(
                    "Provided available_permissions are not a list of strings."
                )
            if available_permission.find("inRole:") != 0:
                raise exceptions.InvalidValue(
                    "available_permissions must be prefixed with 'inRole:'."
                )
        # Make a copy of the original list.
        self._available_permissions = list(value)

    @property
    def availability_condition(self):
        """Returns the current availability condition.

        Returns:
           Optional[google.auth.downscoped.AvailabilityCondition]: The current
               availability condition.
        """
        return self._availability_condition

    @availability_condition.setter
    def availability_condition(self, value):
        """Updates the current availability condition.

        Args:
            value (Optional[google.auth.downscoped.AvailabilityCondition]): The updated
                value of the availability condition.

        Raises:
            google.auth.exceptions.InvalidType: If the value is not of type google.auth.downscoped.AvailabilityCondition
                or None.
        """
        if not isinstance(value, AvailabilityCondition) and value is not None:
            raise exceptions.InvalidType(
                "The provided availability_condition is not a 'google.auth.downscoped.AvailabilityCondition' or None."
            )
        self._availability_condition = value

    def to_json(self):
        """Generates the dictionary representation of the access boundary rule.
        This uses the format expected by the Security Token Service API as documented in
        `Defining a Credential Access Boundary`_.

        .. _Defining a Credential Access Boundary:
            https://cloud.google.com/iam/docs/downscoping-short-lived-credentials#define-boundary

        Returns:
            Mapping: The access boundary rule represented in a dictionary object.
        """
        json = {
            "availablePermissions": list(self.available_permissions),
            "availableResource": self.available_resource,
        }
        if self.availability_condition:
            json["availabilityCondition"] = self.availability_condition.to_json()
        return json


class AvailabilityCondition(object):
    """An optional condition that can be used as part of a Credential Access Boundary
    to further restrict permissions."""

    def __init__(self, expression, title=None, description=None):
        """Instantiates an availability condition using the provided expression and
        optional title or description.

        Args:
            expression (str): A condition expression that specifies the Cloud Storage
                objects where permissions are available. For example, this expression
                makes permissions available for objects whose name starts with "customer-a":
                "resource.name.startsWith('projects/_/buckets/example-bucket/objects/customer-a')"
            title (Optional[str]): An optional short string that identifies the purpose of
                the condition.
            description (Optional[str]): Optional details about the purpose of the condition.

        Raises:
            InvalidType: If any of the parameters are not of the expected types.
            InvalidValue: If any of the parameters are not of the expected values.
        """
        self.expression = expression
        self.title = title
        self.description = description

    @property
    def expression(self):
        """Returns the current condition expression.

        Returns:
           str: The current conditon expression.
        """
        return self._expression

    @expression.setter
    def expression(self, value):
        """Updates the current condition expression.

        Args:
            value (str): The updated value of the condition expression.

        Raises:
            google.auth.exceptions.InvalidType: If the value is not of type string.
        """
        if not isinstance(value, str):
            raise exceptions.InvalidType("The provided expression is not a string.")
        self._expression = value

    @property
    def title(self):
        """Returns the current title.

        Returns:
           Optional[str]: The current title.
        """
        return self._title

    @title.setter
    def title(self, value):
        """Updates the current title.

        Args:
            value (Optional[str]): The updated value of the title.

        Raises:
            google.auth.exceptions.InvalidType: If the value is not of type string or None.
        """
        if not isinstance(value, str) and value is not None:
            raise exceptions.InvalidType("The provided title is not a string or None.")
        self._title = value

    @property
    def description(self):
        """Returns the current description.

        Returns:
           Optional[str]: The current description.
        """
        return self._description

    @description.setter
    def description(self, value):
        """Updates the current description.

        Args:
            value (Optional[str]): The updated value of the description.

        Raises:
            google.auth.exceptions.InvalidType: If the value is not of type string or None.
        """
        if not isinstance(value, str) and value is not None:
            raise exceptions.InvalidType(
                "The provided description is not a string or None."
            )
        self._description = value

    def to_json(self):
        """Generates the dictionary representation of the availability condition.
        This uses the format expected by the Security Token Service API as documented in
        `Defining a Credential Access Boundary`_.

        .. _Defining a Credential Access Boundary:
            https://cloud.google.com/iam/docs/downscoping-short-lived-credentials#define-boundary

        Returns:
            Mapping[str, str]: The availability condition represented in a dictionary
                object.
        """
        json = {"expression": self.expression}
        if self.title:
            json["title"] = self.title
        if self.description:
            json["description"] = self.description
        return json


class Credentials(credentials.CredentialsWithQuotaProject):
    """Defines a set of Google credentials that are downscoped from an existing set
    of Google OAuth2 credentials. This is useful to restrict the Identity and Access
    Management (IAM) permissions that a short-lived credential can use.
    The common pattern of usage is to have a token broker with elevated access
    generate these downscoped credentials from higher access source credentials and
    pass the downscoped short-lived access tokens to a token consumer via some
    secure authenticated channel for limited access to Google Cloud Storage
    resources.
    """

    def __init__(
        self,
        source_credentials,
        credential_access_boundary,
        quota_project_id=None,
        universe_domain=credentials.DEFAULT_UNIVERSE_DOMAIN,
    ):
        """Instantiates a downscoped credentials object using the provided source
        credentials and credential access boundary rules.
        To downscope permissions of a source credential, a Credential Access Boundary
        that specifies which resources the new credential can access, as well as an
        upper bound on the permissions that are available on each resource, has to be
        defined. A downscoped credential can then be instantiated using the source
        credential and the Credential Access Boundary.

        Args:
            source_credentials (google.auth.credentials.Credentials): The source credentials
                to be downscoped based on the provided Credential Access Boundary rules.
            credential_access_boundary (google.auth.downscoped.CredentialAccessBoundary):
                The Credential Access Boundary which contains a list of access boundary
                rules. Each rule contains information on the resource that the rule applies to,
                the upper bound of the permissions that are available on that resource and an
                optional condition to further restrict permissions.
            quota_project_id (Optional[str]): The optional quota project ID.
            universe_domain (Optional[str]): The universe domain value, default is googleapis.com
        Raises:
            google.auth.exceptions.RefreshError: If the source credentials
                return an error on token refresh.
            google.auth.exceptions.OAuthError: If the STS token exchange
                endpoint returned an error during downscoped token generation.
        """

        super(Credentials, self).__init__()
        self._source_credentials = source_credentials
        self._credential_access_boundary = credential_access_boundary
        self._quota_project_id = quota_project_id
        self._universe_domain = universe_domain or credentials.DEFAULT_UNIVERSE_DOMAIN
        self._sts_client = sts.Client(
            _STS_TOKEN_URL_PATTERN.format(self.universe_domain)
        )

    @_helpers.copy_docstring(credentials.Credentials)
    def refresh(self, request):
        # Generate an access token from the source credentials.
        self._source_credentials.refresh(request)
        now = _helpers.utcnow()
        # Exchange the access token for a downscoped access token.
        response_data = self._sts_client.exchange_token(
            request=request,
            grant_type=_STS_GRANT_TYPE,
            subject_token=self._source_credentials.token,
            subject_token_type=_STS_SUBJECT_TOKEN_TYPE,
            requested_token_type=_STS_REQUESTED_TOKEN_TYPE,
            additional_options=self._credential_access_boundary.to_json(),
        )
        self.token = response_data.get("access_token")
        # For downscoping CAB flow, the STS endpoint may not return the expiration
        # field for some flows. The generated downscoped token should always have
        # the same expiration time as the source credentials. When no expires_in
        # field is returned in the response, we can just get the expiration time
        # from the source credentials.
        if response_data.get("expires_in"):
            lifetime = datetime.timedelta(seconds=response_data.get("expires_in"))
            self.expiry = now + lifetime
        else:
            self.expiry = self._source_credentials.expiry

    @_helpers.copy_docstring(credentials.CredentialsWithQuotaProject)
    def with_quota_project(self, quota_project_id):
        return self.__class__(
            self._source_credentials,
            self._credential_access_boundary,
            quota_project_id=quota_project_id,
        )

# === NexusCore/openenv\Lib\site-packages\google\generativeai\responder.py ===
# -*- coding: utf-8 -*-
# Copyright 2023 Google LLC
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
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import inspect
import typing
from typing import Any, Callable, Union
from typing_extensions import TypedDict

import pydantic

from google.generativeai import protos

Type = protos.Type

TypeOptions = Union[int, str, Type]

_TYPE_TYPE: dict[TypeOptions, Type] = {
    Type.TYPE_UNSPECIFIED: Type.TYPE_UNSPECIFIED,
    0: Type.TYPE_UNSPECIFIED,
    "type_unspecified": Type.TYPE_UNSPECIFIED,
    "unspecified": Type.TYPE_UNSPECIFIED,
    Type.STRING: Type.STRING,
    1: Type.STRING,
    "type_string": Type.STRING,
    "string": Type.STRING,
    Type.NUMBER: Type.NUMBER,
    2: Type.NUMBER,
    "type_number": Type.NUMBER,
    "number": Type.NUMBER,
    Type.INTEGER: Type.INTEGER,
    3: Type.INTEGER,
    "type_integer": Type.INTEGER,
    "integer": Type.INTEGER,
    Type.BOOLEAN: Type.BOOLEAN,
    4: Type.INTEGER,
    "type_boolean": Type.BOOLEAN,
    "boolean": Type.BOOLEAN,
    Type.ARRAY: Type.ARRAY,
    5: Type.ARRAY,
    "type_array": Type.ARRAY,
    "array": Type.ARRAY,
    Type.OBJECT: Type.OBJECT,
    6: Type.OBJECT,
    "type_object": Type.OBJECT,
    "object": Type.OBJECT,
}


def to_type(x: TypeOptions) -> Type:
    if isinstance(x, str):
        x = x.lower()
    return _TYPE_TYPE[x]


def _generate_schema(
    f: Callable[..., Any],
    *,
    descriptions: Mapping[str, str] | None = None,
    required: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Generates the OpenAPI Schema for a python function.

    Args:
        f: The function to generate an OpenAPI Schema for.
        descriptions: Optional. A `{name: description}` mapping for annotating input
            arguments of the function with user-provided descriptions. It
            defaults to an empty dictionary (i.e. there will not be any
            description for any of the inputs).
        required: Optional. For the user to specify the set of required arguments in
            function calls to `f`. If unspecified, it will be automatically
            inferred from `f`.

    Returns:
        dict[str, Any]: The OpenAPI Schema for the function `f` in JSON format.
    """
    if descriptions is None:
        descriptions = {}
    if required is None:
        required = []
    defaults = dict(inspect.signature(f).parameters)
    fields_dict = {
        name: (
            # 1. We infer the argument type here: use Any rather than None so
            # it will not try to auto-infer the type based on the default value.
            (param.annotation if param.annotation != inspect.Parameter.empty else Any),
            pydantic.Field(
                # 2. We do not support default values for now.
                # default=(
                #     param.default if param.default != inspect.Parameter.empty
                #     else None
                # ),
                # 3. We support user-provided descriptions.
                description=descriptions.get(name, None),
            ),
        )
        for name, param in defaults.items()
        # We do not support *args or **kwargs
        if param.kind
        in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.POSITIONAL_ONLY,
        )
    }
    parameters = pydantic.create_model(f.__name__, **fields_dict).schema()
    # Postprocessing
    # 4. Suppress unnecessary title generation:
    #    * https://github.com/pydantic/pydantic/issues/1051
    #    * http://cl/586221780
    parameters.pop("title", None)
    for name, function_arg in parameters.get("properties", {}).items():
        function_arg.pop("title", None)
        annotation = defaults[name].annotation
        # 5. Nullable fields:
        #     * https://github.com/pydantic/pydantic/issues/1270
        #     * https://stackoverflow.com/a/58841311
        #     * https://github.com/pydantic/pydantic/discussions/4872
        if typing.get_origin(annotation) is typing.Union and type(None) in typing.get_args(
            annotation
        ):
            function_arg["nullable"] = True
    # 6. Annotate required fields.
    if required:
        # We use the user-provided "required" fields if specified.
        parameters["required"] = required
    else:
        # Otherwise we infer it from the function signature.
        parameters["required"] = [
            k
            for k in defaults
            if (
                defaults[k].default == inspect.Parameter.empty
                and defaults[k].kind
                in (
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                    inspect.Parameter.POSITIONAL_ONLY,
                )
            )
        ]
    schema = dict(name=f.__name__, description=f.__doc__, parameters=parameters)
    return schema


def _rename_schema_fields(schema: dict[str, Any]):
    if schema is None:
        return schema

    schema = schema.copy()

    type_ = schema.pop("type", None)
    if type_ is not None:
        schema["type_"] = type_
    type_ = schema.get("type_", None)
    if type_ is not None:
        schema["type_"] = to_type(type_)

    format_ = schema.pop("format", None)
    if format_ is not None:
        schema["format_"] = format_

    items = schema.pop("items", None)
    if items is not None:
        schema["items"] = _rename_schema_fields(items)

    properties = schema.pop("properties", None)
    if properties is not None:
        schema["properties"] = {k: _rename_schema_fields(v) for k, v in properties.items()}

    return schema


class FunctionDeclaration:
    def __init__(self, *, name: str, description: str, parameters: dict[str, Any] | None = None):
        """A  class wrapping a `protos.FunctionDeclaration`, describes a function for `genai.GenerativeModel`'s `tools`."""
        self._proto = protos.FunctionDeclaration(
            name=name, description=description, parameters=_rename_schema_fields(parameters)
        )

    @property
    def name(self) -> str:
        return self._proto.name

    @property
    def description(self) -> str:
        return self._proto.description

    @property
    def parameters(self) -> protos.Schema:
        return self._proto.parameters

    @classmethod
    def from_proto(cls, proto) -> FunctionDeclaration:
        self = cls(name="", description="", parameters={})
        self._proto = proto
        return self

    def to_proto(self) -> protos.FunctionDeclaration:
        return self._proto

    @staticmethod
    def from_function(function: Callable[..., Any], descriptions: dict[str, str] | None = None):
        """Builds a `CallableFunctionDeclaration` from a python function.

        The function should have type annotations.

        This method is able to generate the schema for arguments annotated with types:

        `AllowedTypes = float | int | str | list[AllowedTypes] | dict`

        This method does not yet build a schema for `TypedDict`, that would allow you to specify the dictionary
        contents. But you can build these manually.
        """

        if descriptions is None:
            descriptions = {}

        schema = _generate_schema(function, descriptions=descriptions)

        return CallableFunctionDeclaration(**schema, function=function)


StructType = dict[str, "ValueType"]
ValueType = Union[float, str, bool, StructType, list["ValueType"], None]


class CallableFunctionDeclaration(FunctionDeclaration):
    """An extension of `FunctionDeclaration` that can be built from a Python function, and is callable.

    Note: The Python function must have type annotations.
    """

    def __init__(
        self,
        *,
        name: str,
        description: str,
        parameters: dict[str, Any] | None = None,
        function: Callable[..., Any],
    ):
        super().__init__(name=name, description=description, parameters=parameters)
        self.function = function

    def __call__(self, fc: protos.FunctionCall) -> protos.FunctionResponse:
        result = self.function(**fc.args)
        if not isinstance(result, dict):
            result = {"result": result}
        return protos.FunctionResponse(name=fc.name, response=result)


FunctionDeclarationType = Union[
    FunctionDeclaration,
    protos.FunctionDeclaration,
    dict[str, Any],
    Callable[..., Any],
]


def _make_function_declaration(
    fun: FunctionDeclarationType,
) -> FunctionDeclaration | protos.FunctionDeclaration:
    if isinstance(fun, (FunctionDeclaration, protos.FunctionDeclaration)):
        return fun
    elif isinstance(fun, dict):
        if "function" in fun:
            return CallableFunctionDeclaration(**fun)
        else:
            return FunctionDeclaration(**fun)
    elif callable(fun):
        return CallableFunctionDeclaration.from_function(fun)
    else:
        raise TypeError(
            f"Invalid argument type: Expected an instance of `genai.FunctionDeclarationType`. Received type: {type(fun).__name__}.",
            fun,
        )


def _encode_fd(fd: FunctionDeclaration | protos.FunctionDeclaration) -> protos.FunctionDeclaration:
    if isinstance(fd, protos.FunctionDeclaration):
        return fd

    return fd.to_proto()


class Tool:
    """A wrapper for `protos.Tool`, Contains a collection of related `FunctionDeclaration` objects."""

    def __init__(self, function_declarations: Iterable[FunctionDeclarationType]):
        # The main path doesn't use this but is seems useful.
        self._function_declarations = [_make_function_declaration(f) for f in function_declarations]
        self._index = {}
        for fd in self._function_declarations:
            name = fd.name
            if name in self._index:
                raise ValueError("")
            self._index[fd.name] = fd

        self._proto = protos.Tool(
            function_declarations=[_encode_fd(fd) for fd in self._function_declarations]
        )

    @property
    def function_declarations(self) -> list[FunctionDeclaration | protos.FunctionDeclaration]:
        return self._function_declarations

    def __getitem__(
        self, name: str | protos.FunctionCall
    ) -> FunctionDeclaration | protos.FunctionDeclaration:
        if not isinstance(name, str):
            name = name.name

        return self._index[name]

    def __call__(self, fc: protos.FunctionCall) -> protos.FunctionResponse | None:
        declaration = self[fc]
        if not callable(declaration):
            return None

        return declaration(fc)

    def to_proto(self):
        return self._proto


class ToolDict(TypedDict):
    function_declarations: list[FunctionDeclarationType]


ToolType = Union[
    Tool, protos.Tool, ToolDict, Iterable[FunctionDeclarationType], FunctionDeclarationType
]


def _make_tool(tool: ToolType) -> Tool:
    if isinstance(tool, Tool):
        return tool
    elif isinstance(tool, protos.Tool):
        return Tool(function_declarations=tool.function_declarations)
    elif isinstance(tool, dict):
        if "function_declarations" in tool:
            return Tool(**tool)
        else:
            fd = tool
            return Tool(function_declarations=[protos.FunctionDeclaration(**fd)])
    elif isinstance(tool, Iterable):
        return Tool(function_declarations=tool)
    else:
        try:
            return Tool(function_declarations=[tool])
        except Exception as e:
            raise TypeError(
                f"Invalid argument type: Expected an instance of `genai.ToolType`. Received type: {type(tool).__name__}.",
                tool,
            ) from e


class FunctionLibrary:
    """A container for a set of `Tool` objects, manages lookup and execution of their functions."""

    def __init__(self, tools: Iterable[ToolType]):
        tools = _make_tools(tools)
        self._tools = list(tools)
        self._index = {}
        for tool in self._tools:
            for declaration in tool.function_declarations:
                name = declaration.name
                if name in self._index:
                    raise ValueError(
                        f"Invalid operation: A `FunctionDeclaration` named '{name}' is already defined. Each `FunctionDeclaration` must have a unique name."
                    )
                self._index[declaration.name] = declaration

    def __getitem__(
        self, name: str | protos.FunctionCall
    ) -> FunctionDeclaration | protos.FunctionDeclaration:
        if not isinstance(name, str):
            name = name.name

        return self._index[name]

    def __call__(self, fc: protos.FunctionCall) -> protos.Part | None:
        declaration = self[fc]
        if not callable(declaration):
            return None

        response = declaration(fc)
        return protos.Part(function_response=response)

    def to_proto(self):
        return [tool.to_proto() for tool in self._tools]


ToolsType = Union[Iterable[ToolType], ToolType]


def _make_tools(tools: ToolsType) -> list[Tool]:
    if isinstance(tools, Iterable) and not isinstance(tools, Mapping):
        tools = [_make_tool(t) for t in tools]
        if len(tools) > 1 and all(len(t.function_declarations) == 1 for t in tools):
            # flatten into a single tool.
            tools = [_make_tool([t.function_declarations[0] for t in tools])]
        return tools
    else:
        tool = tools
        return [_make_tool(tool)]


FunctionLibraryType = Union[FunctionLibrary, ToolsType]


def to_function_library(lib: FunctionLibraryType | None) -> FunctionLibrary | None:
    if lib is None:
        return lib
    elif isinstance(lib, FunctionLibrary):
        return lib
    else:
        return FunctionLibrary(tools=lib)


FunctionCallingMode = protos.FunctionCallingConfig.Mode

# fmt: off
_FUNCTION_CALLING_MODE = {
    1: FunctionCallingMode.AUTO,
    FunctionCallingMode.AUTO: FunctionCallingMode.AUTO,
    "mode_auto": FunctionCallingMode.AUTO,
    "auto": FunctionCallingMode.AUTO,

    2: FunctionCallingMode.ANY,
    FunctionCallingMode.ANY: FunctionCallingMode.ANY,
    "mode_any": FunctionCallingMode.ANY,
    "any": FunctionCallingMode.ANY,

    3: FunctionCallingMode.NONE,
    FunctionCallingMode.NONE: FunctionCallingMode.NONE,
    "mode_none": FunctionCallingMode.NONE,
    "none": FunctionCallingMode.NONE,
}
# fmt: on

FunctionCallingModeType = Union[FunctionCallingMode, str, int]


def to_function_calling_mode(x: FunctionCallingModeType) -> FunctionCallingMode:
    if isinstance(x, str):
        x = x.lower()
    return _FUNCTION_CALLING_MODE[x]


class FunctionCallingConfigDict(TypedDict):
    mode: FunctionCallingModeType
    allowed_function_names: list[str]


FunctionCallingConfigType = Union[
    FunctionCallingModeType, FunctionCallingConfigDict, protos.FunctionCallingConfig
]


def to_function_calling_config(obj: FunctionCallingConfigType) -> protos.FunctionCallingConfig:
    if isinstance(obj, protos.FunctionCallingConfig):
        return obj
    elif isinstance(obj, (FunctionCallingMode, str, int)):
        obj = {"mode": to_function_calling_mode(obj)}
    elif isinstance(obj, dict):
        obj = obj.copy()
        mode = obj.pop("mode")
        obj["mode"] = to_function_calling_mode(mode)
    else:
        raise TypeError(
            "Invalid argument type: Could not convert input to `protos.FunctionCallingConfig`."
            f" Received type: {type(obj).__name__}.",
            obj,
        )

    return protos.FunctionCallingConfig(obj)


class ToolConfigDict:
    function_calling_config: FunctionCallingConfigType


ToolConfigType = Union[ToolConfigDict, protos.ToolConfig]


def to_tool_config(obj: ToolConfigType) -> protos.ToolConfig:
    if isinstance(obj, protos.ToolConfig):
        return obj
    elif isinstance(obj, dict):
        fcc = obj.pop("function_calling_config")
        fcc = to_function_calling_config(fcc)
        obj["function_calling_config"] = fcc
        return protos.ToolConfig(**obj)
    else:
        raise TypeError(
            "Invalid argument type: Could not convert input to `protos.ToolConfig`. "
            f"Received type: {type(obj).__name__}.",
        )

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\services\model_service\async_client.py ===
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

from google.ai.generativelanguage_v1beta2 import gapic_version as package_version

try:
    OptionalRetry = Union[retries.AsyncRetry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.AsyncRetry, object, None]  # type: ignore

from google.ai.generativelanguage_v1beta2.services.model_service import pagers
from google.ai.generativelanguage_v1beta2.types import model, model_service

from .client import ModelServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, ModelServiceTransport
from .transports.grpc_asyncio import ModelServiceGrpcAsyncIOTransport


class ModelServiceAsyncClient:
    """Provides methods for getting metadata information about
    Generative Models.
    """

    _client: ModelServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = ModelServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = ModelServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = ModelServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = ModelServiceClient._DEFAULT_UNIVERSE

    model_path = staticmethod(ModelServiceClient.model_path)
    parse_model_path = staticmethod(ModelServiceClient.parse_model_path)
    common_billing_account_path = staticmethod(
        ModelServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        ModelServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(ModelServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(ModelServiceClient.parse_common_folder_path)
    common_organization_path = staticmethod(ModelServiceClient.common_organization_path)
    parse_common_organization_path = staticmethod(
        ModelServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(ModelServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        ModelServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(ModelServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        ModelServiceClient.parse_common_location_path
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
            ModelServiceAsyncClient: The constructed client.
        """
        return ModelServiceClient.from_service_account_info.__func__(ModelServiceAsyncClient, info, *args, **kwargs)  # type: ignore

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
            ModelServiceAsyncClient: The constructed client.
        """
        return ModelServiceClient.from_service_account_file.__func__(ModelServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

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
        return ModelServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> ModelServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            ModelServiceTransport: The transport used by the client instance.
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
        type(ModelServiceClient).get_transport_class, type(ModelServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, ModelServiceTransport, Callable[..., ModelServiceTransport]]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the model service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,ModelServiceTransport,Callable[..., ModelServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the ModelServiceTransport constructor.
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
        self._client = ModelServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def get_model(
        self,
        request: Optional[Union[model_service.GetModelRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> model.Model:
        r"""Gets information about a specific Model.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta2

            async def sample_get_model():
                # Create a client
                client = generativelanguage_v1beta2.ModelServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta2.GetModelRequest(
                    name="name_value",
                )

                # Make the request
                response = await client.get_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta2.types.GetModelRequest, dict]]):
                The request object. Request for getting information about
                a specific Model.
            name (:class:`str`):
                Required. The resource name of the model.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta2.types.Model:
                Information about a Generative
                Language Model.

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
        if not isinstance(request, model_service.GetModelRequest):
            request = model_service.GetModelRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.get_model
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

    async def list_models(
        self,
        request: Optional[Union[model_service.ListModelsRequest, dict]] = None,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListModelsAsyncPager:
        r"""Lists models available through the API.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta2

            async def sample_list_models():
                # Create a client
                client = generativelanguage_v1beta2.ModelServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta2.ListModelsRequest(
                )

                # Make the request
                page_result = client.list_models(request=request)

                # Handle the response
                async for response in page_result:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta2.types.ListModelsRequest, dict]]):
                The request object. Request for listing all Models.
            page_size (:class:`int`):
                The maximum number of ``Models`` to return (per page).

                The service may return fewer models. If unspecified, at
                most 50 models will be returned per page. This method
                returns at most 1000 models per page, even if you pass a
                larger page_size.

                This corresponds to the ``page_size`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            page_token (:class:`str`):
                A page token, received from a previous ``ListModels``
                call.

                Provide the ``page_token`` returned by one request as an
                argument to the next request to retrieve the next page.

                When paginating, all other parameters provided to
                ``ListModels`` must match the call that provided the
                page token.

                This corresponds to the ``page_token`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta2.services.model_service.pagers.ListModelsAsyncPager:
                Response from ListModel containing a paginated list of
                Models.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([page_size, page_token])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.ListModelsRequest):
            request = model_service.ListModelsRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if page_size is not None:
            request.page_size = page_size
        if page_token is not None:
            request.page_token = page_token

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.list_models
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
        response = pagers.ListModelsAsyncPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def __aenter__(self) -> "ModelServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("ModelServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\jedi\inference\compiled\subprocess\__init__.py ===
"""
Makes it possible to do the compiled analysis in a subprocess. This has two
goals:

1. Making it safer - Segfaults and RuntimeErrors as well as stdout/stderr can
   be ignored and dealt with.
2. Make it possible to handle different Python versions as well as virtualenvs.

The architecture here is briefly:
 - For each Jedi `Environment` there is a corresponding subprocess which
   operates within the target environment. If the subprocess dies it is replaced
   at this level.
 - `CompiledSubprocess` manages exactly one subprocess and handles communication
   from the parent side.
 - `Listener` runs within the subprocess, processing each request and yielding
   results.
 - `InterpreterEnvironment` provides an API which matches that of `Environment`,
   but runs functionality inline rather than within a subprocess. It is thus
   used both directly in places where a subprocess is unnecessary and/or
   undesirable and also within subprocesses themselves.
 - `InferenceStateSubprocess` (or `InferenceStateSameProcess`) provide high
   level access to functionality within the subprocess from within the parent.
   Each `InterpreterState` has an instance of one of these, provided by its
   environment.
"""

import collections
import os
import sys
import queue
import subprocess
import traceback
import weakref
from functools import partial
from threading import Thread
from typing import Dict, TYPE_CHECKING

from jedi._compatibility import pickle_dump, pickle_load
from jedi import debug
from jedi.cache import memoize_method
from jedi.inference.compiled.subprocess import functions
from jedi.inference.compiled.access import DirectObjectAccess, AccessPath, \
    SignatureParam
from jedi.api.exceptions import InternalError

if TYPE_CHECKING:
    from jedi.inference import InferenceState


_MAIN_PATH = os.path.join(os.path.dirname(__file__), '__main__.py')
PICKLE_PROTOCOL = 4


def _GeneralizedPopen(*args, **kwargs):
    if os.name == 'nt':
        try:
            # Was introduced in Python 3.7.
            CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW
        except AttributeError:
            CREATE_NO_WINDOW = 0x08000000
        kwargs['creationflags'] = CREATE_NO_WINDOW
    # The child process doesn't need file descriptors except 0, 1, 2.
    # This is unix only.
    kwargs['close_fds'] = 'posix' in sys.builtin_module_names

    return subprocess.Popen(*args, **kwargs)


def _enqueue_output(out, queue_):
    for line in iter(out.readline, b''):
        queue_.put(line)


def _add_stderr_to_debug(stderr_queue):
    while True:
        # Try to do some error reporting from the subprocess and print its
        # stderr contents.
        try:
            line = stderr_queue.get_nowait()
            line = line.decode('utf-8', 'replace')
            debug.warning('stderr output: %s' % line.rstrip('\n'))
        except queue.Empty:
            break


def _get_function(name):
    return getattr(functions, name)


def _cleanup_process(process, thread):
    try:
        process.kill()
        process.wait()
    except OSError:
        # Raised if the process is already killed.
        pass
    thread.join()
    for stream in [process.stdin, process.stdout, process.stderr]:
        try:
            stream.close()
        except OSError:
            # Raised if the stream is broken.
            pass


class _InferenceStateProcess:
    def __init__(self, inference_state: 'InferenceState') -> None:
        self._inference_state_weakref = weakref.ref(inference_state)
        self._handles: Dict[int, AccessHandle] = {}

    def get_or_create_access_handle(self, obj):
        id_ = id(obj)
        try:
            return self.get_access_handle(id_)
        except KeyError:
            access = DirectObjectAccess(self._inference_state_weakref(), obj)
            handle = AccessHandle(self, access, id_)
            self.set_access_handle(handle)
            return handle

    def get_access_handle(self, id_):
        return self._handles[id_]

    def set_access_handle(self, handle):
        self._handles[handle.id] = handle


class InferenceStateSameProcess(_InferenceStateProcess):
    """
    Basically just an easy access to functions.py. It has the same API
    as InferenceStateSubprocess and does the same thing without using a subprocess.
    This is necessary for the Interpreter process.
    """
    def __getattr__(self, name):
        return partial(_get_function(name), self._inference_state_weakref())


class InferenceStateSubprocess(_InferenceStateProcess):
    """
    API to functionality which will run in a subprocess.

    This mediates the interaction between an `InferenceState` and the actual
    execution of functionality running within a `CompiledSubprocess`. Available
    functions are defined in `.functions`, though should be accessed via
    attributes on this class of the same name.

    This class is responsible for indicating that the `InferenceState` within
    the subprocess can be removed once the corresponding instance in the parent
    goes away.
    """

    def __init__(
        self,
        inference_state: 'InferenceState',
        compiled_subprocess: 'CompiledSubprocess',
    ) -> None:
        super().__init__(inference_state)
        self._used = False
        self._compiled_subprocess = compiled_subprocess

        # Opaque id we'll pass to the subprocess to identify the context (an
        # `InferenceState`) which should be used for the request. This allows us
        # to make subsequent requests which operate on results from previous
        # ones, while keeping a single subprocess which can work with several
        # contexts in the parent process. Once it is no longer needed(i.e: when
        # this class goes away), we also use this id to indicate that the
        # subprocess can discard the context.
        #
        # Note: this id is deliberately coupled to this class (and not to
        # `InferenceState`) as this class manages access handle mappings which
        # must correspond to those in the subprocess. This approach also avoids
        # race conditions from successive `InferenceState`s with the same object
        # id (as observed while adding support for Python 3.13).
        #
        # This value does not need to be the `id()` of this instance, we merely
        # need to ensure that it enables the (visible) lifetime of the context
        # within the subprocess to match that of this class. We therefore also
        # depend on the semantics of `CompiledSubprocess.delete_inference_state`
        # for correctness.
        self._inference_state_id = id(self)

    def __getattr__(self, name):
        func = _get_function(name)

        def wrapper(*args, **kwargs):
            self._used = True

            result = self._compiled_subprocess.run(
                self._inference_state_id,
                func,
                args=args,
                kwargs=kwargs,
            )
            # IMO it should be possible to create a hook in pickle.load to
            # mess with the loaded objects. However it's extremely complicated
            # to work around this so just do it with this call. ~ dave
            return self._convert_access_handles(result)

        return wrapper

    def _convert_access_handles(self, obj):
        if isinstance(obj, SignatureParam):
            return SignatureParam(*self._convert_access_handles(tuple(obj)))
        elif isinstance(obj, tuple):
            return tuple(self._convert_access_handles(o) for o in obj)
        elif isinstance(obj, list):
            return [self._convert_access_handles(o) for o in obj]
        elif isinstance(obj, AccessHandle):
            try:
                # Rewrite the access handle to one we're already having.
                obj = self.get_access_handle(obj.id)
            except KeyError:
                obj.add_subprocess(self)
                self.set_access_handle(obj)
        elif isinstance(obj, AccessPath):
            return AccessPath(self._convert_access_handles(obj.accesses))
        return obj

    def __del__(self):
        if self._used and not self._compiled_subprocess.is_crashed:
            self._compiled_subprocess.delete_inference_state(self._inference_state_id)


class CompiledSubprocess:
    """
    A subprocess which runs inference within a target environment.

    This class manages the interface to a single instance of such a process as
    well as the lifecycle of the process itself. See `.__main__` and `Listener`
    for the implementation of the subprocess and details of the protocol.

    A single live instance of this is maintained by `jedi.api.environment.Environment`,
    so that typically a single subprocess is used at a time.
    """

    is_crashed = False

    def __init__(self, executable, env_vars=None):
        self._executable = executable
        self._env_vars = env_vars
        self._inference_state_deletion_queue = collections.deque()
        self._cleanup_callable = lambda: None

    def __repr__(self):
        pid = os.getpid()
        return '<%s _executable=%r, is_crashed=%r, pid=%r>' % (
            self.__class__.__name__,
            self._executable,
            self.is_crashed,
            pid,
        )

    @memoize_method
    def _get_process(self):
        debug.dbg('Start environment subprocess %s', self._executable)
        parso_path = sys.modules['parso'].__file__
        args = (
            self._executable,
            _MAIN_PATH,
            os.path.dirname(os.path.dirname(parso_path)),
            '.'.join(str(x) for x in sys.version_info[:3]),
        )
        process = _GeneralizedPopen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self._env_vars
        )
        self._stderr_queue = queue.Queue()
        self._stderr_thread = t = Thread(
            target=_enqueue_output,
            args=(process.stderr, self._stderr_queue)
        )
        t.daemon = True
        t.start()
        # Ensure the subprocess is properly cleaned up when the object
        # is garbage collected.
        self._cleanup_callable = weakref.finalize(self,
                                                  _cleanup_process,
                                                  process,
                                                  t)
        return process

    def run(self, inference_state_id, function, args=(), kwargs={}):
        # Delete old inference_states.
        while True:
            try:
                delete_id = self._inference_state_deletion_queue.pop()
            except IndexError:
                break
            else:
                self._send(delete_id, None)

        assert callable(function)
        return self._send(inference_state_id, function, args, kwargs)

    def get_sys_path(self):
        return self._send(None, functions.get_sys_path, (), {})

    def _kill(self):
        self.is_crashed = True
        self._cleanup_callable()

    def _send(self, inference_state_id, function, args=(), kwargs={}):
        if self.is_crashed:
            raise InternalError("The subprocess %s has crashed." % self._executable)

        data = inference_state_id, function, args, kwargs
        try:
            pickle_dump(data, self._get_process().stdin, PICKLE_PROTOCOL)
        except BrokenPipeError:
            self._kill()
            raise InternalError("The subprocess %s was killed. Maybe out of memory?"
                                % self._executable)

        try:
            is_exception, traceback, result = pickle_load(self._get_process().stdout)
        except EOFError as eof_error:
            try:
                stderr = self._get_process().stderr.read().decode('utf-8', 'replace')
            except Exception as exc:
                stderr = '<empty/not available (%r)>' % exc
            self._kill()
            _add_stderr_to_debug(self._stderr_queue)
            raise InternalError(
                "The subprocess %s has crashed (%r, stderr=%s)." % (
                    self._executable,
                    eof_error,
                    stderr,
                ))

        _add_stderr_to_debug(self._stderr_queue)

        if is_exception:
            # Replace the attribute error message with a the traceback. It's
            # way more informative.
            result.args = (traceback,)
            raise result
        return result

    def delete_inference_state(self, inference_state_id):
        """
        Indicate that an inference state (in the subprocess) is no longer
        needed.

        The state corresponding to the given id will become inaccessible and the
        id may safely be re-used to refer to a different context.

        Note: it is not guaranteed that the corresponding state will actually be
        deleted immediately.
        """
        # Warning: if changing the semantics of context deletion see the comment
        # in `InferenceStateSubprocess.__init__` regarding potential race
        # conditions.

        # Currently we are not deleting the related state instantly. They only
        # get deleted once the subprocess is used again. It would probably a
        # better solution to move all of this into a thread. However, the memory
        # usage of a single inference_state shouldn't be that high.
        self._inference_state_deletion_queue.append(inference_state_id)


class Listener:
    """
    Main loop for the subprocess which actually does the inference.

    This class runs within the target environment. It listens to instructions
    from the parent process, runs inference and returns the results.

    The subprocess has a long lifetime and is expected to process several
    requests, including for different `InferenceState` instances in the parent.
    See `CompiledSubprocess` for the parent half of the system.

    Communication is via pickled data sent serially over stdin and stdout.
    Stderr is read only if the child process crashes.

    The request protocol is a 4-tuple of:
     * inference_state_id | None: an opaque identifier of the parent's
       `InferenceState`. An `InferenceState` operating over an
       `InterpreterEnvironment` is created within this process for each of
       these, ensuring that each parent context has a corresponding context
       here. This allows context to be persisted between requests. Unless
       `None`, the local `InferenceState` will be passed to the given function
       as the first positional argument.
     * function | None: the function to run. This is expected to be a member of
       `.functions`. `None` indicates that the corresponding inference state is
       no longer needed and should be dropped.
     * args: positional arguments to the `function`. If any of these are
       `AccessHandle` instances they will be adapted to the local
       `InferenceState` before being passed.
     * kwargs: keyword arguments to the `function`. If any of these are
       `AccessHandle` instances they will be adapted to the local
       `InferenceState` before being passed.

    The result protocol is a 3-tuple of either:
     * (False, None, function result): if the function returns without error, or
     * (True, traceback, exception): if the function raises an exception
    """

    def __init__(self):
        self._inference_states = {}

    def _get_inference_state(self, function, inference_state_id):
        from jedi.inference import InferenceState

        try:
            inference_state = self._inference_states[inference_state_id]
        except KeyError:
            from jedi import InterpreterEnvironment
            inference_state = InferenceState(
                # The project is not actually needed. Nothing should need to
                # access it.
                project=None,
                environment=InterpreterEnvironment()
            )
            self._inference_states[inference_state_id] = inference_state
        return inference_state

    def _run(self, inference_state_id, function, args, kwargs):
        if inference_state_id is None:
            return function(*args, **kwargs)
        elif function is None:
            # Warning: if changing the semantics of context deletion see the comment
            # in `InferenceStateSubprocess.__init__` regarding potential race
            # conditions.
            del self._inference_states[inference_state_id]
        else:
            inference_state = self._get_inference_state(function, inference_state_id)

            # Exchange all handles
            args = list(args)
            for i, arg in enumerate(args):
                if isinstance(arg, AccessHandle):
                    args[i] = inference_state.compiled_subprocess.get_access_handle(arg.id)
            for key, value in kwargs.items():
                if isinstance(value, AccessHandle):
                    kwargs[key] = inference_state.compiled_subprocess.get_access_handle(value.id)

            return function(inference_state, *args, **kwargs)

    def listen(self):
        stdout = sys.stdout
        # Mute stdout. Nobody should actually be able to write to it,
        # because stdout is used for IPC.
        sys.stdout = open(os.devnull, 'w')
        stdin = sys.stdin
        stdout = stdout.buffer
        stdin = stdin.buffer

        while True:
            try:
                payload = pickle_load(stdin)
            except EOFError:
                # It looks like the parent process closed.
                # Don't make a big fuss here and just exit.
                exit(0)
            try:
                result = False, None, self._run(*payload)
            except Exception as e:
                result = True, traceback.format_exc(), e

            pickle_dump(result, stdout, PICKLE_PROTOCOL)


class AccessHandle:
    def __init__(
        self,
        subprocess: _InferenceStateProcess,
        access: DirectObjectAccess,
        id_: int,
    ) -> None:
        self.access = access
        self._subprocess = subprocess
        self.id = id_

    def add_subprocess(self, subprocess):
        self._subprocess = subprocess

    def __repr__(self):
        try:
            detail = self.access
        except AttributeError:
            detail = '#' + str(self.id)
        return '<%s of %s>' % (self.__class__.__name__, detail)

    def __getstate__(self):
        return self.id

    def __setstate__(self, state):
        self.id = state

    def __getattr__(self, name):
        if name in ('id', 'access') or name.startswith('_'):
            raise AttributeError("Something went wrong with unpickling")

        # print('getattr', name, file=sys.stderr)
        return partial(self._workaround, name)

    def _workaround(self, name, *args, **kwargs):
        """
        TODO Currently we're passing slice objects around. This should not
        happen. They are also the only unhashable objects that we're passing
        around.
        """
        if args and isinstance(args[0], slice):
            return self._subprocess.get_compiled_method_return(self.id, name, *args, **kwargs)
        return self._cached_results(name, *args, **kwargs)

    @memoize_method
    def _cached_results(self, name, *args, **kwargs):
        return self._subprocess.get_compiled_method_return(self.id, name, *args, **kwargs)

# === NexusCore/openenv\Lib\site-packages\matplotlib\patheffects.py ===
"""
Defines classes for path effects. The path effects are supported in `.Text`,
`.Line2D` and `.Patch`.

.. seealso::
   :ref:`patheffects_guide`
"""

from matplotlib.backend_bases import RendererBase
from matplotlib import colors as mcolors
from matplotlib import patches as mpatches
from matplotlib import transforms as mtransforms
from matplotlib.path import Path
import numpy as np


class AbstractPathEffect:
    """
    A base class for path effects.

    Subclasses should override the ``draw_path`` method to add effect
    functionality.
    """

    def __init__(self, offset=(0., 0.)):
        """
        Parameters
        ----------
        offset : (float, float), default: (0, 0)
            The (x, y) offset to apply to the path, measured in points.
        """
        self._offset = offset

    def _offset_transform(self, renderer):
        """Apply the offset to the given transform."""
        return mtransforms.Affine2D().translate(
            *map(renderer.points_to_pixels, self._offset))

    def _update_gc(self, gc, new_gc_dict):
        """
        Update the given GraphicsContext with the given dict of properties.

        The keys in the dictionary are used to identify the appropriate
        ``set_`` method on the *gc*.
        """
        new_gc_dict = new_gc_dict.copy()

        dashes = new_gc_dict.pop("dashes", None)
        if dashes:
            gc.set_dashes(**dashes)

        for k, v in new_gc_dict.items():
            set_method = getattr(gc, 'set_' + k, None)
            if not callable(set_method):
                raise AttributeError(f'Unknown property {k}')
            set_method(v)
        return gc

    def draw_path(self, renderer, gc, tpath, affine, rgbFace=None):
        """
        Derived should override this method. The arguments are the same
        as :meth:`matplotlib.backend_bases.RendererBase.draw_path`
        except the first argument is a renderer.
        """
        # Get the real renderer, not a PathEffectRenderer.
        if isinstance(renderer, PathEffectRenderer):
            renderer = renderer._renderer
        return renderer.draw_path(gc, tpath, affine, rgbFace)


class PathEffectRenderer(RendererBase):
    """
    Implements a Renderer which contains another renderer.

    This proxy then intercepts draw calls, calling the appropriate
    :class:`AbstractPathEffect` draw method.

    .. note::
        Not all methods have been overridden on this RendererBase subclass.
        It may be necessary to add further methods to extend the PathEffects
        capabilities further.
    """

    def __init__(self, path_effects, renderer):
        """
        Parameters
        ----------
        path_effects : iterable of :class:`AbstractPathEffect`
            The path effects which this renderer represents.
        renderer : `~matplotlib.backend_bases.RendererBase` subclass

        """
        self._path_effects = path_effects
        self._renderer = renderer

    def copy_with_path_effect(self, path_effects):
        return self.__class__(path_effects, self._renderer)

    def __getattribute__(self, name):
        if name in ['flipy', 'get_canvas_width_height', 'new_gc',
                    'points_to_pixels', '_text2path', 'height', 'width']:
            return getattr(self._renderer, name)
        else:
            return object.__getattribute__(self, name)

    def draw_path(self, gc, tpath, affine, rgbFace=None):
        for path_effect in self._path_effects:
            path_effect.draw_path(self._renderer, gc, tpath, affine,
                                  rgbFace)

    def draw_markers(
            self, gc, marker_path, marker_trans, path, *args, **kwargs):
        # We do a little shimmy so that all markers are drawn for each path
        # effect in turn. Essentially, we induce recursion (depth 1) which is
        # terminated once we have just a single path effect to work with.
        if len(self._path_effects) == 1:
            # Call the base path effect function - this uses the unoptimised
            # approach of calling "draw_path" multiple times.
            return super().draw_markers(gc, marker_path, marker_trans, path,
                                        *args, **kwargs)

        for path_effect in self._path_effects:
            renderer = self.copy_with_path_effect([path_effect])
            # Recursively call this method, only next time we will only have
            # one path effect.
            renderer.draw_markers(gc, marker_path, marker_trans, path,
                                  *args, **kwargs)

    def draw_path_collection(self, gc, master_transform, paths, *args,
                             **kwargs):
        # We do a little shimmy so that all paths are drawn for each path
        # effect in turn. Essentially, we induce recursion (depth 1) which is
        # terminated once we have just a single path effect to work with.
        if len(self._path_effects) == 1:
            # Call the base path effect function - this uses the unoptimised
            # approach of calling "draw_path" multiple times.
            return super().draw_path_collection(gc, master_transform, paths,
                                                *args, **kwargs)

        for path_effect in self._path_effects:
            renderer = self.copy_with_path_effect([path_effect])
            # Recursively call this method, only next time we will only have
            # one path effect.
            renderer.draw_path_collection(gc, master_transform, paths,
                                          *args, **kwargs)

    def open_group(self, s, gid=None):
        return self._renderer.open_group(s, gid)

    def close_group(self, s):
        return self._renderer.close_group(s)


class Normal(AbstractPathEffect):
    """
    The "identity" PathEffect.

    The Normal PathEffect's sole purpose is to draw the original artist with
    no special path effect.
    """


def _subclass_with_normal(effect_class):
    """
    Create a PathEffect class combining *effect_class* and a normal draw.
    """

    class withEffect(effect_class):
        def draw_path(self, renderer, gc, tpath, affine, rgbFace):
            super().draw_path(renderer, gc, tpath, affine, rgbFace)
            renderer.draw_path(gc, tpath, affine, rgbFace)

    withEffect.__name__ = f"with{effect_class.__name__}"
    withEffect.__qualname__ = f"with{effect_class.__name__}"
    withEffect.__doc__ = f"""
    A shortcut PathEffect for applying `.{effect_class.__name__}` and then
    drawing the original Artist.

    With this class you can use ::

        artist.set_path_effects([patheffects.with{effect_class.__name__}()])

    as a shortcut for ::

        artist.set_path_effects([patheffects.{effect_class.__name__}(),
                                 patheffects.Normal()])
    """
    # Docstring inheritance doesn't work for locally-defined subclasses.
    withEffect.draw_path.__doc__ = effect_class.draw_path.__doc__
    return withEffect


class Stroke(AbstractPathEffect):
    """A line based PathEffect which re-draws a stroke."""

    def __init__(self, offset=(0, 0), **kwargs):
        """
        The path will be stroked with its gc updated with the given
        keyword arguments, i.e., the keyword arguments should be valid
        gc parameter values.
        """
        super().__init__(offset)
        self._gc = kwargs

    def draw_path(self, renderer, gc, tpath, affine, rgbFace):
        """Draw the path with updated gc."""
        gc0 = renderer.new_gc()  # Don't modify gc, but a copy!
        gc0.copy_properties(gc)
        gc0 = self._update_gc(gc0, self._gc)
        renderer.draw_path(
            gc0, tpath, affine + self._offset_transform(renderer), rgbFace)
        gc0.restore()


withStroke = _subclass_with_normal(effect_class=Stroke)


class SimplePatchShadow(AbstractPathEffect):
    """A simple shadow via a filled patch."""

    def __init__(self, offset=(2, -2),
                 shadow_rgbFace=None, alpha=None,
                 rho=0.3, **kwargs):
        """
        Parameters
        ----------
        offset : (float, float), default: (2, -2)
            The (x, y) offset of the shadow in points.
        shadow_rgbFace : :mpltype:`color`
            The shadow color.
        alpha : float, default: 0.3
            The alpha transparency of the created shadow patch.
        rho : float, default: 0.3
            A scale factor to apply to the rgbFace color if *shadow_rgbFace*
            is not specified.
        **kwargs
            Extra keywords are stored and passed through to
            :meth:`AbstractPathEffect._update_gc`.

        """
        super().__init__(offset)

        if shadow_rgbFace is None:
            self._shadow_rgbFace = shadow_rgbFace
        else:
            self._shadow_rgbFace = mcolors.to_rgba(shadow_rgbFace)

        if alpha is None:
            alpha = 0.3

        self._alpha = alpha
        self._rho = rho

        #: The dictionary of keywords to update the graphics collection with.
        self._gc = kwargs

    def draw_path(self, renderer, gc, tpath, affine, rgbFace):
        """
        Overrides the standard draw_path to add the shadow offset and
        necessary color changes for the shadow.
        """
        gc0 = renderer.new_gc()  # Don't modify gc, but a copy!
        gc0.copy_properties(gc)

        if self._shadow_rgbFace is None:
            r, g, b = (rgbFace or (1., 1., 1.))[:3]
            # Scale the colors by a factor to improve the shadow effect.
            shadow_rgbFace = (r * self._rho, g * self._rho, b * self._rho)
        else:
            shadow_rgbFace = self._shadow_rgbFace

        gc0.set_foreground("none")
        gc0.set_alpha(self._alpha)
        gc0.set_linewidth(0)

        gc0 = self._update_gc(gc0, self._gc)
        renderer.draw_path(
            gc0, tpath, affine + self._offset_transform(renderer),
            shadow_rgbFace)
        gc0.restore()


withSimplePatchShadow = _subclass_with_normal(effect_class=SimplePatchShadow)


class SimpleLineShadow(AbstractPathEffect):
    """A simple shadow via a line."""

    def __init__(self, offset=(2, -2),
                 shadow_color='k', alpha=0.3, rho=0.3, **kwargs):
        """
        Parameters
        ----------
        offset : (float, float), default: (2, -2)
            The (x, y) offset to apply to the path, in points.
        shadow_color : :mpltype:`color`, default: 'black'
            The shadow color.
            A value of ``None`` takes the original artist's color
            with a scale factor of *rho*.
        alpha : float, default: 0.3
            The alpha transparency of the created shadow patch.
        rho : float, default: 0.3
            A scale factor to apply to the rgbFace color if *shadow_color*
            is ``None``.
        **kwargs
            Extra keywords are stored and passed through to
            :meth:`AbstractPathEffect._update_gc`.
        """
        super().__init__(offset)
        if shadow_color is None:
            self._shadow_color = shadow_color
        else:
            self._shadow_color = mcolors.to_rgba(shadow_color)
        self._alpha = alpha
        self._rho = rho
        #: The dictionary of keywords to update the graphics collection with.
        self._gc = kwargs

    def draw_path(self, renderer, gc, tpath, affine, rgbFace):
        """
        Overrides the standard draw_path to add the shadow offset and
        necessary color changes for the shadow.
        """
        gc0 = renderer.new_gc()  # Don't modify gc, but a copy!
        gc0.copy_properties(gc)

        if self._shadow_color is None:
            r, g, b = (gc0.get_foreground() or (1., 1., 1.))[:3]
            # Scale the colors by a factor to improve the shadow effect.
            shadow_rgbFace = (r * self._rho, g * self._rho, b * self._rho)
        else:
            shadow_rgbFace = self._shadow_color

        gc0.set_foreground(shadow_rgbFace)
        gc0.set_alpha(self._alpha)

        gc0 = self._update_gc(gc0, self._gc)
        renderer.draw_path(
            gc0, tpath, affine + self._offset_transform(renderer))
        gc0.restore()


class PathPatchEffect(AbstractPathEffect):
    """
    Draws a `.PathPatch` instance whose Path comes from the original
    PathEffect artist.
    """

    def __init__(self, offset=(0, 0), **kwargs):
        """
        Parameters
        ----------
        offset : (float, float), default: (0, 0)
            The (x, y) offset to apply to the path, in points.
        **kwargs
            All keyword arguments are passed through to the
            :class:`~matplotlib.patches.PathPatch` constructor. The
            properties which cannot be overridden are "path", "clip_box"
            "transform" and "clip_path".
        """
        super().__init__(offset=offset)
        self.patch = mpatches.PathPatch([], **kwargs)

    def draw_path(self, renderer, gc, tpath, affine, rgbFace):
        self.patch._path = tpath
        self.patch.set_transform(affine + self._offset_transform(renderer))
        self.patch.set_clip_box(gc.get_clip_rectangle())
        clip_path = gc.get_clip_path()
        if clip_path and self.patch.get_clip_path() is None:
            self.patch.set_clip_path(*clip_path)
        self.patch.draw(renderer)


class TickedStroke(AbstractPathEffect):
    """
    A line-based PathEffect which draws a path with a ticked style.

    This line style is frequently used to represent constraints in
    optimization.  The ticks may be used to indicate that one side
    of the line is invalid or to represent a closed boundary of a
    domain (i.e. a wall or the edge of a pipe).

    The spacing, length, and angle of ticks can be controlled.

    This line style is sometimes referred to as a hatched line.

    See also the :doc:`/gallery/misc/tickedstroke_demo` example.
    """

    def __init__(self, offset=(0, 0),
                 spacing=10.0, angle=45.0, length=np.sqrt(2),
                 **kwargs):
        """
        Parameters
        ----------
        offset : (float, float), default: (0, 0)
            The (x, y) offset to apply to the path, in points.
        spacing : float, default: 10.0
            The spacing between ticks in points.
        angle : float, default: 45.0
            The angle between the path and the tick in degrees.  The angle
            is measured as if you were an ant walking along the curve, with
            zero degrees pointing directly ahead, 90 to your left, -90
            to your right, and 180 behind you. To change side of the ticks,
            change sign of the angle.
        length : float, default: 1.414
            The length of the tick relative to spacing.
            Recommended length = 1.414 (sqrt(2)) when angle=45, length=1.0
            when angle=90 and length=2.0 when angle=60.
        **kwargs
            Extra keywords are stored and passed through to
            :meth:`AbstractPathEffect._update_gc`.

        Examples
        --------
        See :doc:`/gallery/misc/tickedstroke_demo`.
        """
        super().__init__(offset)

        self._spacing = spacing
        self._angle = angle
        self._length = length
        self._gc = kwargs

    def draw_path(self, renderer, gc, tpath, affine, rgbFace):
        """Draw the path with updated gc."""
        # Do not modify the input! Use copy instead.
        gc0 = renderer.new_gc()
        gc0.copy_properties(gc)

        gc0 = self._update_gc(gc0, self._gc)
        trans = affine + self._offset_transform(renderer)

        theta = -np.radians(self._angle)
        trans_matrix = np.array([[np.cos(theta), -np.sin(theta)],
                                 [np.sin(theta), np.cos(theta)]])

        # Convert spacing parameter to pixels.
        spacing_px = renderer.points_to_pixels(self._spacing)

        # Transform before evaluation because to_polygons works at resolution
        # of one -- assuming it is working in pixel space.
        transpath = affine.transform_path(tpath)

        # Evaluate path to straight line segments that can be used to
        # construct line ticks.
        polys = transpath.to_polygons(closed_only=False)

        for p in polys:
            x = p[:, 0]
            y = p[:, 1]

            # Can not interpolate points or draw line if only one point in
            # polyline.
            if x.size < 2:
                continue

            # Find distance between points on the line
            ds = np.hypot(x[1:] - x[:-1], y[1:] - y[:-1])

            # Build parametric coordinate along curve
            s = np.concatenate(([0.0], np.cumsum(ds)))
            s_total = s[-1]

            num = int(np.ceil(s_total / spacing_px)) - 1
            # Pick parameter values for ticks.
            s_tick = np.linspace(spacing_px/2, s_total - spacing_px/2, num)

            # Find points along the parameterized curve
            x_tick = np.interp(s_tick, s, x)
            y_tick = np.interp(s_tick, s, y)

            # Find unit vectors in local direction of curve
            delta_s = self._spacing * .001
            u = (np.interp(s_tick + delta_s, s, x) - x_tick) / delta_s
            v = (np.interp(s_tick + delta_s, s, y) - y_tick) / delta_s

            # Normalize slope into unit slope vector.
            n = np.hypot(u, v)
            mask = n == 0
            n[mask] = 1.0

            uv = np.array([u / n, v / n]).T
            uv[mask] = np.array([0, 0]).T

            # Rotate and scale unit vector into tick vector
            dxy = np.dot(uv, trans_matrix) * self._length * spacing_px

            # Build tick endpoints
            x_end = x_tick + dxy[:, 0]
            y_end = y_tick + dxy[:, 1]

            # Interleave ticks to form Path vertices
            xyt = np.empty((2 * num, 2), dtype=x_tick.dtype)
            xyt[0::2, 0] = x_tick
            xyt[1::2, 0] = x_end
            xyt[0::2, 1] = y_tick
            xyt[1::2, 1] = y_end

            # Build up vector of Path codes
            codes = np.tile([Path.MOVETO, Path.LINETO], num)

            # Construct and draw resulting path
            h = Path(xyt, codes)
            # Transform back to data space during render
            renderer.draw_path(gc0, h, affine.inverted() + trans, rgbFace)

        gc0.restore()


withTickedStroke = _subclass_with_normal(effect_class=TickedStroke)

# === NexusCore/openenv\Lib\site-packages\matplotlib\projections\geo.py ===
import numpy as np

import matplotlib as mpl
from matplotlib import _api
from matplotlib.axes import Axes
import matplotlib.axis as maxis
from matplotlib.patches import Circle
from matplotlib.path import Path
import matplotlib.spines as mspines
from matplotlib.ticker import (
    Formatter, NullLocator, FixedLocator, NullFormatter)
from matplotlib.transforms import Affine2D, BboxTransformTo, Transform


class GeoAxes(Axes):
    """An abstract base class for geographic projections."""

    class ThetaFormatter(Formatter):
        """
        Used to format the theta tick labels.  Converts the native
        unit of radians into degrees and adds a degree symbol.
        """
        def __init__(self, round_to=1.0):
            self._round_to = round_to

        def __call__(self, x, pos=None):
            degrees = round(np.rad2deg(x) / self._round_to) * self._round_to
            return f"{degrees:0.0f}\N{DEGREE SIGN}"

    RESOLUTION = 75

    def _init_axis(self):
        self.xaxis = maxis.XAxis(self, clear=False)
        self.yaxis = maxis.YAxis(self, clear=False)
        self.spines['geo'].register_axis(self.yaxis)

    def clear(self):
        # docstring inherited
        super().clear()

        self.set_longitude_grid(30)
        self.set_latitude_grid(15)
        self.set_longitude_grid_ends(75)
        self.xaxis.set_minor_locator(NullLocator())
        self.yaxis.set_minor_locator(NullLocator())
        self.xaxis.set_ticks_position('none')
        self.yaxis.set_ticks_position('none')
        self.yaxis.set_tick_params(label1On=True)
        # Why do we need to turn on yaxis tick labels, but
        # xaxis tick labels are already on?

        self.grid(mpl.rcParams['axes.grid'])

        Axes.set_xlim(self, -np.pi, np.pi)
        Axes.set_ylim(self, -np.pi / 2.0, np.pi / 2.0)

    def _set_lim_and_transforms(self):
        # A (possibly non-linear) projection on the (already scaled) data
        self.transProjection = self._get_core_transform(self.RESOLUTION)

        self.transAffine = self._get_affine_transform()

        self.transAxes = BboxTransformTo(self.bbox)

        # The complete data transformation stack -- from data all the
        # way to display coordinates
        self.transData = \
            self.transProjection + \
            self.transAffine + \
            self.transAxes

        # This is the transform for longitude ticks.
        self._xaxis_pretransform = \
            Affine2D() \
            .scale(1, self._longitude_cap * 2) \
            .translate(0, -self._longitude_cap)
        self._xaxis_transform = \
            self._xaxis_pretransform + \
            self.transData
        self._xaxis_text1_transform = \
            Affine2D().scale(1, 0) + \
            self.transData + \
            Affine2D().translate(0, 4)
        self._xaxis_text2_transform = \
            Affine2D().scale(1, 0) + \
            self.transData + \
            Affine2D().translate(0, -4)

        # This is the transform for latitude ticks.
        yaxis_stretch = Affine2D().scale(np.pi * 2, 1).translate(-np.pi, 0)
        yaxis_space = Affine2D().scale(1, 1.1)
        self._yaxis_transform = \
            yaxis_stretch + \
            self.transData
        yaxis_text_base = \
            yaxis_stretch + \
            self.transProjection + \
            (yaxis_space +
             self.transAffine +
             self.transAxes)
        self._yaxis_text1_transform = \
            yaxis_text_base + \
            Affine2D().translate(-8, 0)
        self._yaxis_text2_transform = \
            yaxis_text_base + \
            Affine2D().translate(8, 0)

    def _get_affine_transform(self):
        transform = self._get_core_transform(1)
        xscale, _ = transform.transform((np.pi, 0))
        _, yscale = transform.transform((0, np.pi/2))
        return Affine2D() \
            .scale(0.5 / xscale, 0.5 / yscale) \
            .translate(0.5, 0.5)

    def get_xaxis_transform(self, which='grid'):
        _api.check_in_list(['tick1', 'tick2', 'grid'], which=which)
        return self._xaxis_transform

    def get_xaxis_text1_transform(self, pad):
        return self._xaxis_text1_transform, 'bottom', 'center'

    def get_xaxis_text2_transform(self, pad):
        return self._xaxis_text2_transform, 'top', 'center'

    def get_yaxis_transform(self, which='grid'):
        _api.check_in_list(['tick1', 'tick2', 'grid'], which=which)
        return self._yaxis_transform

    def get_yaxis_text1_transform(self, pad):
        return self._yaxis_text1_transform, 'center', 'right'

    def get_yaxis_text2_transform(self, pad):
        return self._yaxis_text2_transform, 'center', 'left'

    def _gen_axes_patch(self):
        return Circle((0.5, 0.5), 0.5)

    def _gen_axes_spines(self):
        return {'geo': mspines.Spine.circular_spine(self, (0.5, 0.5), 0.5)}

    def set_yscale(self, *args, **kwargs):
        if args[0] != 'linear':
            raise NotImplementedError

    set_xscale = set_yscale

    def set_xlim(self, *args, **kwargs):
        """Not supported. Please consider using Cartopy."""
        raise TypeError("Changing axes limits of a geographic projection is "
                        "not supported.  Please consider using Cartopy.")

    set_ylim = set_xlim
    set_xbound = set_xlim
    set_ybound = set_ylim

    def invert_xaxis(self):
        """Not supported. Please consider using Cartopy."""
        raise TypeError("Changing axes limits of a geographic projection is "
                        "not supported.  Please consider using Cartopy.")

    invert_yaxis = invert_xaxis

    def format_coord(self, lon, lat):
        """Return a format string formatting the coordinate."""
        lon, lat = np.rad2deg([lon, lat])
        ns = 'N' if lat >= 0.0 else 'S'
        ew = 'E' if lon >= 0.0 else 'W'
        return ('%f\N{DEGREE SIGN}%s, %f\N{DEGREE SIGN}%s'
                % (abs(lat), ns, abs(lon), ew))

    def set_longitude_grid(self, degrees):
        """
        Set the number of degrees between each longitude grid.
        """
        # Skip -180 and 180, which are the fixed limits.
        grid = np.arange(-180 + degrees, 180, degrees)
        self.xaxis.set_major_locator(FixedLocator(np.deg2rad(grid)))
        self.xaxis.set_major_formatter(self.ThetaFormatter(degrees))

    def set_latitude_grid(self, degrees):
        """
        Set the number of degrees between each latitude grid.
        """
        # Skip -90 and 90, which are the fixed limits.
        grid = np.arange(-90 + degrees, 90, degrees)
        self.yaxis.set_major_locator(FixedLocator(np.deg2rad(grid)))
        self.yaxis.set_major_formatter(self.ThetaFormatter(degrees))

    def set_longitude_grid_ends(self, degrees):
        """
        Set the latitude(s) at which to stop drawing the longitude grids.
        """
        self._longitude_cap = np.deg2rad(degrees)
        self._xaxis_pretransform \
            .clear() \
            .scale(1.0, self._longitude_cap * 2.0) \
            .translate(0.0, -self._longitude_cap)

    def get_data_ratio(self):
        """Return the aspect ratio of the data itself."""
        return 1.0

    ### Interactive panning

    def can_zoom(self):
        """
        Return whether this Axes supports the zoom box button functionality.

        This Axes object does not support interactive zoom box.
        """
        return False

    def can_pan(self):
        """
        Return whether this Axes supports the pan/zoom button functionality.

        This Axes object does not support interactive pan/zoom.
        """
        return False

    def start_pan(self, x, y, button):
        pass

    def end_pan(self):
        pass

    def drag_pan(self, button, key, x, y):
        pass


class _GeoTransform(Transform):
    # Factoring out some common functionality.
    input_dims = output_dims = 2

    def __init__(self, resolution):
        """
        Create a new geographical transform.

        Resolution is the number of steps to interpolate between each input
        line segment to approximate its path in curved space.
        """
        super().__init__()
        self._resolution = resolution

    def __str__(self):
        return f"{type(self).__name__}({self._resolution})"

    def transform_path_non_affine(self, path):
        # docstring inherited
        ipath = path.interpolated(self._resolution)
        return Path(self.transform(ipath.vertices), ipath.codes)


class AitoffAxes(GeoAxes):
    name = 'aitoff'

    class AitoffTransform(_GeoTransform):
        """The base Aitoff transform."""

        def transform_non_affine(self, values):
            # docstring inherited
            longitude, latitude = values.T

            # Pre-compute some values
            half_long = longitude / 2.0
            cos_latitude = np.cos(latitude)

            alpha = np.arccos(cos_latitude * np.cos(half_long))
            sinc_alpha = np.sinc(alpha / np.pi)  # np.sinc is sin(pi*x)/(pi*x).

            x = (cos_latitude * np.sin(half_long)) / sinc_alpha
            y = np.sin(latitude) / sinc_alpha
            return np.column_stack([x, y])

        def inverted(self):
            # docstring inherited
            return AitoffAxes.InvertedAitoffTransform(self._resolution)

    class InvertedAitoffTransform(_GeoTransform):

        def transform_non_affine(self, values):
            # docstring inherited
            # MGDTODO: Math is hard ;(
            return np.full_like(values, np.nan)

        def inverted(self):
            # docstring inherited
            return AitoffAxes.AitoffTransform(self._resolution)

    def __init__(self, *args, **kwargs):
        self._longitude_cap = np.pi / 2.0
        super().__init__(*args, **kwargs)
        self.set_aspect(0.5, adjustable='box', anchor='C')
        self.clear()

    def _get_core_transform(self, resolution):
        return self.AitoffTransform(resolution)


class HammerAxes(GeoAxes):
    name = 'hammer'

    class HammerTransform(_GeoTransform):
        """The base Hammer transform."""

        def transform_non_affine(self, values):
            # docstring inherited
            longitude, latitude = values.T
            half_long = longitude / 2.0
            cos_latitude = np.cos(latitude)
            sqrt2 = np.sqrt(2.0)
            alpha = np.sqrt(1.0 + cos_latitude * np.cos(half_long))
            x = (2.0 * sqrt2) * (cos_latitude * np.sin(half_long)) / alpha
            y = (sqrt2 * np.sin(latitude)) / alpha
            return np.column_stack([x, y])

        def inverted(self):
            # docstring inherited
            return HammerAxes.InvertedHammerTransform(self._resolution)

    class InvertedHammerTransform(_GeoTransform):

        def transform_non_affine(self, values):
            # docstring inherited
            x, y = values.T
            z = np.sqrt(1 - (x / 4) ** 2 - (y / 2) ** 2)
            longitude = 2 * np.arctan((z * x) / (2 * (2 * z ** 2 - 1)))
            latitude = np.arcsin(y*z)
            return np.column_stack([longitude, latitude])

        def inverted(self):
            # docstring inherited
            return HammerAxes.HammerTransform(self._resolution)

    def __init__(self, *args, **kwargs):
        self._longitude_cap = np.pi / 2.0
        super().__init__(*args, **kwargs)
        self.set_aspect(0.5, adjustable='box', anchor='C')
        self.clear()

    def _get_core_transform(self, resolution):
        return self.HammerTransform(resolution)


class MollweideAxes(GeoAxes):
    name = 'mollweide'

    class MollweideTransform(_GeoTransform):
        """The base Mollweide transform."""

        def transform_non_affine(self, values):
            # docstring inherited
            def d(theta):
                delta = (-(theta + np.sin(theta) - pi_sin_l)
                         / (1 + np.cos(theta)))
                return delta, np.abs(delta) > 0.001

            longitude, latitude = values.T

            clat = np.pi/2 - np.abs(latitude)
            ihigh = clat < 0.087  # within 5 degrees of the poles
            ilow = ~ihigh
            aux = np.empty(latitude.shape, dtype=float)

            if ilow.any():  # Newton-Raphson iteration
                pi_sin_l = np.pi * np.sin(latitude[ilow])
                theta = 2.0 * latitude[ilow]
                delta, large_delta = d(theta)
                while np.any(large_delta):
                    theta[large_delta] += delta[large_delta]
                    delta, large_delta = d(theta)
                aux[ilow] = theta / 2

            if ihigh.any():  # Taylor series-based approx. solution
                e = clat[ihigh]
                d = 0.5 * (3 * np.pi * e**2) ** (1.0/3)
                aux[ihigh] = (np.pi/2 - d) * np.sign(latitude[ihigh])

            xy = np.empty(values.shape, dtype=float)
            xy[:, 0] = (2.0 * np.sqrt(2.0) / np.pi) * longitude * np.cos(aux)
            xy[:, 1] = np.sqrt(2.0) * np.sin(aux)

            return xy

        def inverted(self):
            # docstring inherited
            return MollweideAxes.InvertedMollweideTransform(self._resolution)

    class InvertedMollweideTransform(_GeoTransform):

        def transform_non_affine(self, values):
            # docstring inherited
            x, y = values.T
            # from Equations (7, 8) of
            # https://mathworld.wolfram.com/MollweideProjection.html
            theta = np.arcsin(y / np.sqrt(2))
            longitude = (np.pi / (2 * np.sqrt(2))) * x / np.cos(theta)
            latitude = np.arcsin((2 * theta + np.sin(2 * theta)) / np.pi)
            return np.column_stack([longitude, latitude])

        def inverted(self):
            # docstring inherited
            return MollweideAxes.MollweideTransform(self._resolution)

    def __init__(self, *args, **kwargs):
        self._longitude_cap = np.pi / 2.0
        super().__init__(*args, **kwargs)
        self.set_aspect(0.5, adjustable='box', anchor='C')
        self.clear()

    def _get_core_transform(self, resolution):
        return self.MollweideTransform(resolution)


class LambertAxes(GeoAxes):
    name = 'lambert'

    class LambertTransform(_GeoTransform):
        """The base Lambert transform."""

        def __init__(self, center_longitude, center_latitude, resolution):
            """
            Create a new Lambert transform.  Resolution is the number of steps
            to interpolate between each input line segment to approximate its
            path in curved Lambert space.
            """
            _GeoTransform.__init__(self, resolution)
            self._center_longitude = center_longitude
            self._center_latitude = center_latitude

        def transform_non_affine(self, values):
            # docstring inherited
            longitude, latitude = values.T
            clong = self._center_longitude
            clat = self._center_latitude
            cos_lat = np.cos(latitude)
            sin_lat = np.sin(latitude)
            diff_long = longitude - clong
            cos_diff_long = np.cos(diff_long)

            inner_k = np.maximum(  # Prevent divide-by-zero problems
                1 + np.sin(clat)*sin_lat + np.cos(clat)*cos_lat*cos_diff_long,
                1e-15)
            k = np.sqrt(2 / inner_k)
            x = k * cos_lat*np.sin(diff_long)
            y = k * (np.cos(clat)*sin_lat - np.sin(clat)*cos_lat*cos_diff_long)

            return np.column_stack([x, y])

        def inverted(self):
            # docstring inherited
            return LambertAxes.InvertedLambertTransform(
                self._center_longitude,
                self._center_latitude,
                self._resolution)

    class InvertedLambertTransform(_GeoTransform):

        def __init__(self, center_longitude, center_latitude, resolution):
            _GeoTransform.__init__(self, resolution)
            self._center_longitude = center_longitude
            self._center_latitude = center_latitude

        def transform_non_affine(self, values):
            # docstring inherited
            x, y = values.T
            clong = self._center_longitude
            clat = self._center_latitude
            p = np.maximum(np.hypot(x, y), 1e-9)
            c = 2 * np.arcsin(0.5 * p)
            sin_c = np.sin(c)
            cos_c = np.cos(c)

            latitude = np.arcsin(cos_c*np.sin(clat) +
                                 ((y*sin_c*np.cos(clat)) / p))
            longitude = clong + np.arctan(
                (x*sin_c) / (p*np.cos(clat)*cos_c - y*np.sin(clat)*sin_c))

            return np.column_stack([longitude, latitude])

        def inverted(self):
            # docstring inherited
            return LambertAxes.LambertTransform(
                self._center_longitude,
                self._center_latitude,
                self._resolution)

    def __init__(self, *args, center_longitude=0, center_latitude=0, **kwargs):
        self._longitude_cap = np.pi / 2
        self._center_longitude = center_longitude
        self._center_latitude = center_latitude
        super().__init__(*args, **kwargs)
        self.set_aspect('equal', adjustable='box', anchor='C')
        self.clear()

    def clear(self):
        # docstring inherited
        super().clear()
        self.yaxis.set_major_formatter(NullFormatter())

    def _get_core_transform(self, resolution):
        return self.LambertTransform(
            self._center_longitude,
            self._center_latitude,
            resolution)

    def _get_affine_transform(self):
        return Affine2D() \
            .scale(0.25) \
            .translate(0.5, 0.5)

# === NexusCore/openenv\Lib\site-packages\openai\resources\containers\containers.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List
from typing_extensions import Literal

import httpx

from ... import _legacy_response
from ...types import container_list_params, container_create_params
from ..._types import NOT_GIVEN, Body, Query, Headers, NoneType, NotGiven
from ..._utils import maybe_transform, async_maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from .files.files import (
    Files,
    AsyncFiles,
    FilesWithRawResponse,
    AsyncFilesWithRawResponse,
    FilesWithStreamingResponse,
    AsyncFilesWithStreamingResponse,
)
from ...pagination import SyncCursorPage, AsyncCursorPage
from ..._base_client import AsyncPaginator, make_request_options
from ...types.container_list_response import ContainerListResponse
from ...types.container_create_response import ContainerCreateResponse
from ...types.container_retrieve_response import ContainerRetrieveResponse

__all__ = ["Containers", "AsyncContainers"]


class Containers(SyncAPIResource):
    @cached_property
    def files(self) -> Files:
        return Files(self._client)

    @cached_property
    def with_raw_response(self) -> ContainersWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return ContainersWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> ContainersWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return ContainersWithStreamingResponse(self)

    def create(
        self,
        *,
        name: str,
        expires_after: container_create_params.ExpiresAfter | NotGiven = NOT_GIVEN,
        file_ids: List[str] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ContainerCreateResponse:
        """
        Create Container

        Args:
          name: Name of the container to create.

          expires_after: Container expiration time in seconds relative to the 'anchor' time.

          file_ids: IDs of files to copy to the container.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/containers",
            body=maybe_transform(
                {
                    "name": name,
                    "expires_after": expires_after,
                    "file_ids": file_ids,
                },
                container_create_params.ContainerCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ContainerCreateResponse,
        )

    def retrieve(
        self,
        container_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ContainerRetrieveResponse:
        """
        Retrieve Container

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not container_id:
            raise ValueError(f"Expected a non-empty value for `container_id` but received {container_id!r}")
        return self._get(
            f"/containers/{container_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ContainerRetrieveResponse,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[ContainerListResponse]:
        """List Containers

        Args:
          after: A cursor for use in pagination.

        `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get_api_list(
            "/containers",
            page=SyncCursorPage[ContainerListResponse],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                        "order": order,
                    },
                    container_list_params.ContainerListParams,
                ),
            ),
            model=ContainerListResponse,
        )

    def delete(
        self,
        container_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> None:
        """
        Delete Container

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not container_id:
            raise ValueError(f"Expected a non-empty value for `container_id` but received {container_id!r}")
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return self._delete(
            f"/containers/{container_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class AsyncContainers(AsyncAPIResource):
    @cached_property
    def files(self) -> AsyncFiles:
        return AsyncFiles(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncContainersWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncContainersWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncContainersWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncContainersWithStreamingResponse(self)

    async def create(
        self,
        *,
        name: str,
        expires_after: container_create_params.ExpiresAfter | NotGiven = NOT_GIVEN,
        file_ids: List[str] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ContainerCreateResponse:
        """
        Create Container

        Args:
          name: Name of the container to create.

          expires_after: Container expiration time in seconds relative to the 'anchor' time.

          file_ids: IDs of files to copy to the container.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/containers",
            body=await async_maybe_transform(
                {
                    "name": name,
                    "expires_after": expires_after,
                    "file_ids": file_ids,
                },
                container_create_params.ContainerCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ContainerCreateResponse,
        )

    async def retrieve(
        self,
        container_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ContainerRetrieveResponse:
        """
        Retrieve Container

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not container_id:
            raise ValueError(f"Expected a non-empty value for `container_id` but received {container_id!r}")
        return await self._get(
            f"/containers/{container_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ContainerRetrieveResponse,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[ContainerListResponse, AsyncCursorPage[ContainerListResponse]]:
        """List Containers

        Args:
          after: A cursor for use in pagination.

        `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get_api_list(
            "/containers",
            page=AsyncCursorPage[ContainerListResponse],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                        "order": order,
                    },
                    container_list_params.ContainerListParams,
                ),
            ),
            model=ContainerListResponse,
        )

    async def delete(
        self,
        container_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> None:
        """
        Delete Container

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not container_id:
            raise ValueError(f"Expected a non-empty value for `container_id` but received {container_id!r}")
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return await self._delete(
            f"/containers/{container_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )


class ContainersWithRawResponse:
    def __init__(self, containers: Containers) -> None:
        self._containers = containers

        self.create = _legacy_response.to_raw_response_wrapper(
            containers.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            containers.retrieve,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            containers.list,
        )
        self.delete = _legacy_response.to_raw_response_wrapper(
            containers.delete,
        )

    @cached_property
    def files(self) -> FilesWithRawResponse:
        return FilesWithRawResponse(self._containers.files)


class AsyncContainersWithRawResponse:
    def __init__(self, containers: AsyncContainers) -> None:
        self._containers = containers

        self.create = _legacy_response.async_to_raw_response_wrapper(
            containers.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            containers.retrieve,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            containers.list,
        )
        self.delete = _legacy_response.async_to_raw_response_wrapper(
            containers.delete,
        )

    @cached_property
    def files(self) -> AsyncFilesWithRawResponse:
        return AsyncFilesWithRawResponse(self._containers.files)


class ContainersWithStreamingResponse:
    def __init__(self, containers: Containers) -> None:
        self._containers = containers

        self.create = to_streamed_response_wrapper(
            containers.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            containers.retrieve,
        )
        self.list = to_streamed_response_wrapper(
            containers.list,
        )
        self.delete = to_streamed_response_wrapper(
            containers.delete,
        )

    @cached_property
    def files(self) -> FilesWithStreamingResponse:
        return FilesWithStreamingResponse(self._containers.files)


class AsyncContainersWithStreamingResponse:
    def __init__(self, containers: AsyncContainers) -> None:
        self._containers = containers

        self.create = async_to_streamed_response_wrapper(
            containers.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            containers.retrieve,
        )
        self.list = async_to_streamed_response_wrapper(
            containers.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            containers.delete,
        )

    @cached_property
    def files(self) -> AsyncFilesWithStreamingResponse:
        return AsyncFilesWithStreamingResponse(self._containers.files)

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\scintilla\find.py ===
# find.py - Find and Replace
from __future__ import annotations

import win32api
import win32con
import win32ui
from pywin.framework import scriptutils
from pywin.mfc import afxres, dialog

FOUND_NOTHING = 0
FOUND_NORMAL = 1
FOUND_LOOPED_BACK = 2
FOUND_NEXT_FILE = 3


class SearchParams:
    def __init__(self, other=None):
        if other is None:
            self.__dict__["findText"] = ""
            self.__dict__["replaceText"] = ""
            self.__dict__["matchCase"] = 0
            self.__dict__["matchWords"] = 0
            self.__dict__["acrossFiles"] = 0
            self.__dict__["remember"] = 1
            self.__dict__["sel"] = (-1, -1)
            self.__dict__["keepDialogOpen"] = 0
        else:
            self.__dict__.update(other.__dict__)

    # Helper so we can't misspell attributes :-)
    def __setattr__(self, attr, val):
        if not hasattr(self, attr):
            raise AttributeError(attr)
        self.__dict__[attr] = val


curDialog = None
lastSearch = defaultSearch = SearchParams()
searchHistory: list[str] = []


def ShowFindDialog():
    _ShowDialog(FindDialog)


def ShowReplaceDialog():
    _ShowDialog(ReplaceDialog)


def _ShowDialog(dlgClass):
    global curDialog
    if curDialog is not None:
        if curDialog.__class__ != dlgClass:
            curDialog.DestroyWindow()
            curDialog = None
        else:
            curDialog.SetFocus()
    if curDialog is None:
        curDialog = dlgClass()
        curDialog.CreateWindow()


def FindNext():
    params = SearchParams(lastSearch)
    params.sel = (-1, -1)
    if not params.findText:
        ShowFindDialog()
    else:
        return _FindIt(None, params)


def _GetControl(control=None):
    if control is None:
        control = scriptutils.GetActiveEditControl()
    return control


def _FindIt(control, searchParams):
    global lastSearch, defaultSearch
    control = _GetControl(control)
    if control is None:
        return FOUND_NOTHING

    # Move to the next char, so we find the next one.
    flags = 0
    if searchParams.matchWords:
        flags |= win32con.FR_WHOLEWORD
    if searchParams.matchCase:
        flags |= win32con.FR_MATCHCASE
    if searchParams.sel == (-1, -1):
        sel = control.GetSel()
        # If the position is the same as we found last time,
        # then we assume it is a "FindNext"
        if sel == lastSearch.sel:
            sel = sel[0] + 1, sel[0] + 1
    else:
        sel = searchParams.sel

    if sel[0] == sel[1]:
        sel = sel[0], control.GetTextLength()

    rc = FOUND_NOTHING
    # (Old edit control will fail here!)
    posFind, foundSel = control.FindText(flags, sel, searchParams.findText)
    lastSearch = SearchParams(searchParams)
    if posFind >= 0:
        rc = FOUND_NORMAL
        lineno = control.LineFromChar(posFind)
        control.SCIEnsureVisible(lineno)
        control.SetSel(foundSel)
        control.SetFocus()
        win32ui.SetStatusText(win32ui.LoadString(afxres.AFX_IDS_IDLEMESSAGE))
    if rc == FOUND_NOTHING and lastSearch.acrossFiles:
        # Loop around all documents.  First find this document.
        try:
            try:
                doc = control.GetDocument()
            except AttributeError:
                try:
                    doc = control.GetParent().GetDocument()
                except AttributeError:
                    print("Can't find a document for the control!")
                    doc = None
            if doc is not None:
                template = doc.GetDocTemplate()
                alldocs = template.GetDocumentList()
                mypos = lookpos = alldocs.index(doc)
                while 1:
                    lookpos = (lookpos + 1) % len(alldocs)
                    if lookpos == mypos:
                        break
                    view = alldocs[lookpos].GetFirstView()
                    posFind, foundSel = view.FindText(
                        flags, (0, view.GetTextLength()), searchParams.findText
                    )
                    if posFind >= 0:
                        nChars = foundSel[1] - foundSel[0]
                        lineNo = view.LineFromChar(posFind)  # zero based.
                        lineStart = view.LineIndex(lineNo)
                        colNo = posFind - lineStart  # zero based.
                        scriptutils.JumpToDocument(
                            alldocs[lookpos].GetPathName(),
                            lineNo + 1,
                            colNo + 1,
                            nChars,
                        )
                        rc = FOUND_NEXT_FILE
                        break
        except win32ui.error:
            pass
    if rc == FOUND_NOTHING:
        # Loop around this control - attempt to find from the start of the control.
        posFind, foundSel = control.FindText(
            flags, (0, sel[0] - 1), searchParams.findText
        )
        if posFind >= 0:
            control.SCIEnsureVisible(control.LineFromChar(foundSel[0]))
            control.SetSel(foundSel)
            control.SetFocus()
            win32ui.SetStatusText("Not found! Searching from the top of the file.")
            rc = FOUND_LOOPED_BACK
        else:
            lastSearch.sel = -1, -1
            win32ui.SetStatusText("Can not find '%s'" % searchParams.findText)

    if rc != FOUND_NOTHING:
        lastSearch.sel = foundSel

    if lastSearch.remember:
        defaultSearch = lastSearch

        # track search history
        try:
            ix = searchHistory.index(searchParams.findText)
        except ValueError:
            if len(searchHistory) > 50:
                searchHistory[50:] = []
        else:
            del searchHistory[ix]
        searchHistory.insert(0, searchParams.findText)

    return rc


def _ReplaceIt(control):
    control = _GetControl(control)
    statusText = "Can not find '%s'." % lastSearch.findText
    rc = FOUND_NOTHING
    if control is not None and lastSearch.sel != (-1, -1):
        control.ReplaceSel(lastSearch.replaceText)
        rc = FindNext()
        if rc != FOUND_NOTHING:
            statusText = win32ui.LoadString(afxres.AFX_IDS_IDLEMESSAGE)
    win32ui.SetStatusText(statusText)
    return rc


class FindReplaceDialog(dialog.Dialog):
    def __init__(self):
        dialog.Dialog.__init__(self, self._GetDialogTemplate())
        self.HookCommand(self.OnFindNext, 109)

    def OnInitDialog(self):
        self.editFindText = self.GetDlgItem(102)
        self.butMatchWords = self.GetDlgItem(105)
        self.butMatchCase = self.GetDlgItem(107)
        self.butKeepDialogOpen = self.GetDlgItem(115)
        self.butAcrossFiles = self.GetDlgItem(116)
        self.butRemember = self.GetDlgItem(117)

        self.editFindText.SetWindowText(defaultSearch.findText)
        control = _GetControl()
        # _GetControl only gets normal MDI windows; if the interactive
        # window is docked and no document open, we get None.
        if control:
            # If we have a selection, default to that.
            sel = control.GetSelText()
            if len(sel) != 0:
                self.editFindText.SetWindowText(sel)
                if defaultSearch.remember:
                    defaultSearch.findText = sel
        for hist in searchHistory:
            self.editFindText.AddString(hist)

        if hasattr(self.editFindText, "SetEditSel"):
            self.editFindText.SetEditSel(0, -1)
        else:
            self.editFindText.SetSel(0, -1)
        self.butMatchWords.SetCheck(defaultSearch.matchWords)
        self.butMatchCase.SetCheck(defaultSearch.matchCase)
        self.butKeepDialogOpen.SetCheck(defaultSearch.keepDialogOpen)
        self.butAcrossFiles.SetCheck(defaultSearch.acrossFiles)
        self.butRemember.SetCheck(defaultSearch.remember)
        return dialog.Dialog.OnInitDialog(self)

    def OnDestroy(self, msg):
        global curDialog
        curDialog = None
        return dialog.Dialog.OnDestroy(self, msg)

    def DoFindNext(self):
        params = SearchParams()
        params.findText = self.editFindText.GetWindowText()
        params.matchCase = self.butMatchCase.GetCheck()
        params.matchWords = self.butMatchWords.GetCheck()
        params.acrossFiles = self.butAcrossFiles.GetCheck()
        params.remember = self.butRemember.GetCheck()
        return _FindIt(None, params)

    def OnFindNext(self, id, code):
        if code != 0:  # BN_CLICKED
            # 3d controls (python.exe + start_pythonwin.pyw) send
            # other notification codes
            return 1  #
        if not self.editFindText.GetWindowText():
            win32api.MessageBeep()
            return 1
        if self.DoFindNext() != FOUND_NOTHING:
            if not self.butKeepDialogOpen.GetCheck():
                self.DestroyWindow()


class FindDialog(FindReplaceDialog):
    def _GetDialogTemplate(self):
        style = (
            win32con.DS_MODALFRAME
            | win32con.WS_POPUP
            | win32con.WS_VISIBLE
            | win32con.WS_CAPTION
            | win32con.WS_SYSMENU
            | win32con.DS_SETFONT
        )
        visible = win32con.WS_CHILD | win32con.WS_VISIBLE
        dt = [
            ["Find", (0, 2, 240, 75), style, None, (8, "MS Sans Serif")],
            ["Static", "Fi&nd What:", 101, (5, 8, 40, 10), visible],
            [
                "ComboBox",
                "",
                102,
                (50, 7, 120, 120),
                visible
                | win32con.WS_BORDER
                | win32con.WS_TABSTOP
                | win32con.WS_VSCROLL
                | win32con.CBS_DROPDOWN
                | win32con.CBS_AUTOHSCROLL,
            ],
            [
                "Button",
                "Match &whole word only",
                105,
                (5, 23, 100, 10),
                visible | win32con.BS_AUTOCHECKBOX | win32con.WS_TABSTOP,
            ],
            [
                "Button",
                "Match &case",
                107,
                (5, 33, 100, 10),
                visible | win32con.BS_AUTOCHECKBOX | win32con.WS_TABSTOP,
            ],
            [
                "Button",
                "Keep &dialog open",
                115,
                (5, 43, 100, 10),
                visible | win32con.BS_AUTOCHECKBOX | win32con.WS_TABSTOP,
            ],
            [
                "Button",
                "Across &open files",
                116,
                (5, 52, 100, 10),
                visible | win32con.BS_AUTOCHECKBOX | win32con.WS_TABSTOP,
            ],
            [
                "Button",
                "&Remember as default search",
                117,
                (5, 61, 150, 10),
                visible | win32con.BS_AUTOCHECKBOX | win32con.WS_TABSTOP,
            ],
            [
                "Button",
                "&Find Next",
                109,
                (185, 5, 50, 14),
                visible | win32con.BS_DEFPUSHBUTTON | win32con.WS_TABSTOP,
            ],
            [
                "Button",
                "Cancel",
                win32con.IDCANCEL,
                (185, 23, 50, 14),
                visible | win32con.WS_TABSTOP,
            ],
        ]
        return dt


class ReplaceDialog(FindReplaceDialog):
    def _GetDialogTemplate(self):
        style = (
            win32con.DS_MODALFRAME
            | win32con.WS_POPUP
            | win32con.WS_VISIBLE
            | win32con.WS_CAPTION
            | win32con.WS_SYSMENU
            | win32con.DS_SETFONT
        )
        visible = win32con.WS_CHILD | win32con.WS_VISIBLE
        dt = [
            ["Replace", (0, 2, 240, 95), style, 0, (8, "MS Sans Serif")],
            ["Static", "Fi&nd What:", 101, (5, 8, 40, 10), visible],
            [
                "ComboBox",
                "",
                102,
                (60, 7, 110, 120),
                visible
                | win32con.WS_BORDER
                | win32con.WS_TABSTOP
                | win32con.WS_VSCROLL
                | win32con.CBS_DROPDOWN
                | win32con.CBS_AUTOHSCROLL,
            ],
            ["Static", "Re&place with:", 103, (5, 25, 50, 10), visible],
            [
                "ComboBox",
                "",
                104,
                (60, 24, 110, 120),
                visible
                | win32con.WS_BORDER
                | win32con.WS_TABSTOP
                | win32con.WS_VSCROLL
                | win32con.CBS_DROPDOWN
                | win32con.CBS_AUTOHSCROLL,
            ],
            [
                "Button",
                "Match &whole word only",
                105,
                (5, 42, 100, 10),
                visible | win32con.BS_AUTOCHECKBOX | win32con.WS_TABSTOP,
            ],
            [
                "Button",
                "Match &case",
                107,
                (5, 52, 100, 10),
                visible | win32con.BS_AUTOCHECKBOX | win32con.WS_TABSTOP,
            ],
            [
                "Button",
                "Keep &dialog open",
                115,
                (5, 62, 100, 10),
                visible | win32con.BS_AUTOCHECKBOX | win32con.WS_TABSTOP,
            ],
            [
                "Button",
                "Across &open files",
                116,
                (5, 72, 100, 10),
                visible | win32con.BS_AUTOCHECKBOX | win32con.WS_TABSTOP,
            ],
            [
                "Button",
                "&Remember as default search",
                117,
                (5, 81, 150, 10),
                visible | win32con.BS_AUTOCHECKBOX | win32con.WS_TABSTOP,
            ],
            [
                "Button",
                "&Find Next",
                109,
                (185, 5, 50, 14),
                visible | win32con.BS_DEFPUSHBUTTON | win32con.WS_TABSTOP,
            ],
            [
                "Button",
                "&Replace",
                110,
                (185, 23, 50, 14),
                visible | win32con.WS_TABSTOP,
            ],
            [
                "Button",
                "Replace &All",
                111,
                (185, 41, 50, 14),
                visible | win32con.WS_TABSTOP,
            ],
            [
                "Button",
                "Cancel",
                win32con.IDCANCEL,
                (185, 59, 50, 14),
                visible | win32con.WS_TABSTOP,
            ],
        ]
        return dt

    def OnInitDialog(self):
        rc = FindReplaceDialog.OnInitDialog(self)
        self.HookCommand(self.OnReplace, 110)
        self.HookCommand(self.OnReplaceAll, 111)
        self.HookMessage(self.OnActivate, win32con.WM_ACTIVATE)
        self.editReplaceText = self.GetDlgItem(104)
        self.editReplaceText.SetWindowText(lastSearch.replaceText)
        if hasattr(self.editReplaceText, "SetEditSel"):
            self.editReplaceText.SetEditSel(0, -1)
        else:
            self.editReplaceText.SetSel(0, -1)
        self.butReplace = self.GetDlgItem(110)
        self.butReplaceAll = self.GetDlgItem(111)
        self.CheckButtonStates()
        return rc  # 0 when focus set

    def CheckButtonStates(self):
        # We can do a "Replace" or "Replace All" if the current selection
        # is the same as the search text.
        ft = self.editFindText.GetWindowText()
        control = _GetControl()
        # 		bCanReplace = len(ft)>0 and control.GetSelText() == ft
        bCanReplace = control is not None and lastSearch.sel == control.GetSel()
        self.butReplace.EnableWindow(bCanReplace)

    # 		self.butReplaceAll.EnableWindow(bCanReplace)

    def OnActivate(self, msg):
        wparam = msg[2]
        fActive = win32api.LOWORD(wparam)
        if fActive != win32con.WA_INACTIVE:
            self.CheckButtonStates()

    def OnFindNext(self, id, code):
        if code != 0:
            return 1
        self.DoFindNext()
        self.CheckButtonStates()

    def OnReplace(self, id, code):
        if code != 0:
            return 1
        lastSearch.replaceText = self.editReplaceText.GetWindowText()
        _ReplaceIt(None)

    def OnReplaceAll(self, id, code):
        if code != 0:
            return 1
        control = _GetControl(None)
        if control is not None:
            control.SetSel(0)
            num = 0
            if self.DoFindNext() == FOUND_NORMAL:
                num = 1
                lastSearch.replaceText = self.editReplaceText.GetWindowText()
                while _ReplaceIt(control) == FOUND_NORMAL:
                    num += 1

            win32ui.SetStatusText("Replaced %d occurrences" % num)
            if num > 0 and not self.butKeepDialogOpen.GetCheck():
                self.DestroyWindow()


if __name__ == "__main__":
    ShowFindDialog()