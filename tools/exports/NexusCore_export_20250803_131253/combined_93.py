
# === NexusCore/tools\exports\export_20250803_114325\combined_81.py ===

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\lib\unique_fn.py ===
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
"""Function for de-duping results."""
from __future__ import annotations

from typing import Sequence
from google.generativeai.notebook.lib import llmfn_output_row


def unique_fn(
    rows: Sequence[llmfn_output_row.LLMFnOutputRowView],
) -> Sequence[int]:
    """Returns a list of indices with duplicates removed.

    E.g. if rows has results ["hello", "hello", "world"], the return value would
    be [0, 2], indicating that the results at index 1 is a duplicate and should be
    removed.

    Args:
      rows: The input rows

    Returns:
      A sequence of indices indicating which entries have unique results.
    """
    indices: list[int] = []
    seen_entries = set()
    for idx, row in enumerate(rows):
        value = row.result_value()
        if value in seen_entries:
            continue

        seen_entries.add(value)
        indices.append(idx)

    return indices

# === NexusCore/openenv\Lib\site-packages\aiohttp\client_reqrep.py ===
import asyncio
import codecs
import contextlib
import functools
import io
import re
import sys
import traceback
import warnings
from collections.abc import Mapping
from hashlib import md5, sha1, sha256
from http.cookies import Morsel, SimpleCookie
from types import MappingProxyType, TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    Union,
)

import attr
from multidict import CIMultiDict, CIMultiDictProxy, MultiDict, MultiDictProxy
from yarl import URL

from . import hdrs, helpers, http, multipart, payload
from ._cookie_helpers import (
    parse_cookie_header,
    parse_set_cookie_headers,
    preserve_morsel_with_coded_value,
)
from .abc import AbstractStreamWriter
from .client_exceptions import (
    ClientConnectionError,
    ClientOSError,
    ClientResponseError,
    ContentTypeError,
    InvalidURL,
    ServerFingerprintMismatch,
)
from .compression_utils import HAS_BROTLI
from .formdata import FormData
from .helpers import (
    _SENTINEL,
    BaseTimerContext,
    BasicAuth,
    HeadersMixin,
    TimerNoop,
    basicauth_from_netrc,
    netrc_from_env,
    noop,
    reify,
    set_exception,
    set_result,
)
from .http import (
    SERVER_SOFTWARE,
    HttpVersion,
    HttpVersion10,
    HttpVersion11,
    StreamWriter,
)
from .streams import StreamReader
from .typedefs import (
    DEFAULT_JSON_DECODER,
    JSONDecoder,
    LooseCookies,
    LooseHeaders,
    Query,
    RawHeaders,
)

if TYPE_CHECKING:
    import ssl
    from ssl import SSLContext
else:
    try:
        import ssl
        from ssl import SSLContext
    except ImportError:  # pragma: no cover
        ssl = None  # type: ignore[assignment]
        SSLContext = object  # type: ignore[misc,assignment]


__all__ = ("ClientRequest", "ClientResponse", "RequestInfo", "Fingerprint")


if TYPE_CHECKING:
    from .client import ClientSession
    from .connector import Connection
    from .tracing import Trace


_CONNECTION_CLOSED_EXCEPTION = ClientConnectionError("Connection closed")
_CONTAINS_CONTROL_CHAR_RE = re.compile(r"[^-!#$%&'*+.^_`|~0-9a-zA-Z]")
json_re = re.compile(r"^application/(?:[\w.+-]+?\+)?json")


def _gen_default_accept_encoding() -> str:
    return "gzip, deflate, br" if HAS_BROTLI else "gzip, deflate"


@attr.s(auto_attribs=True, frozen=True, slots=True)
class ContentDisposition:
    type: Optional[str]
    parameters: "MappingProxyType[str, str]"
    filename: Optional[str]


class _RequestInfo(NamedTuple):
    url: URL
    method: str
    headers: "CIMultiDictProxy[str]"
    real_url: URL


class RequestInfo(_RequestInfo):

    def __new__(
        cls,
        url: URL,
        method: str,
        headers: "CIMultiDictProxy[str]",
        real_url: URL = _SENTINEL,  # type: ignore[assignment]
    ) -> "RequestInfo":
        """Create a new RequestInfo instance.

        For backwards compatibility, the real_url parameter is optional.
        """
        return tuple.__new__(
            cls, (url, method, headers, url if real_url is _SENTINEL else real_url)
        )


class Fingerprint:
    HASHFUNC_BY_DIGESTLEN = {
        16: md5,
        20: sha1,
        32: sha256,
    }

    def __init__(self, fingerprint: bytes) -> None:
        digestlen = len(fingerprint)
        hashfunc = self.HASHFUNC_BY_DIGESTLEN.get(digestlen)
        if not hashfunc:
            raise ValueError("fingerprint has invalid length")
        elif hashfunc is md5 or hashfunc is sha1:
            raise ValueError("md5 and sha1 are insecure and not supported. Use sha256.")
        self._hashfunc = hashfunc
        self._fingerprint = fingerprint

    @property
    def fingerprint(self) -> bytes:
        return self._fingerprint

    def check(self, transport: asyncio.Transport) -> None:
        if not transport.get_extra_info("sslcontext"):
            return
        sslobj = transport.get_extra_info("ssl_object")
        cert = sslobj.getpeercert(binary_form=True)
        got = self._hashfunc(cert).digest()
        if got != self._fingerprint:
            host, port, *_ = transport.get_extra_info("peername")
            raise ServerFingerprintMismatch(self._fingerprint, got, host, port)


if ssl is not None:
    SSL_ALLOWED_TYPES = (ssl.SSLContext, bool, Fingerprint, type(None))
else:  # pragma: no cover
    SSL_ALLOWED_TYPES = (bool, type(None))


def _merge_ssl_params(
    ssl: Union["SSLContext", bool, Fingerprint],
    verify_ssl: Optional[bool],
    ssl_context: Optional["SSLContext"],
    fingerprint: Optional[bytes],
) -> Union["SSLContext", bool, Fingerprint]:
    if ssl is None:
        ssl = True  # Double check for backwards compatibility
    if verify_ssl is not None and not verify_ssl:
        warnings.warn(
            "verify_ssl is deprecated, use ssl=False instead",
            DeprecationWarning,
            stacklevel=3,
        )
        if ssl is not True:
            raise ValueError(
                "verify_ssl, ssl_context, fingerprint and ssl "
                "parameters are mutually exclusive"
            )
        else:
            ssl = False
    if ssl_context is not None:
        warnings.warn(
            "ssl_context is deprecated, use ssl=context instead",
            DeprecationWarning,
            stacklevel=3,
        )
        if ssl is not True:
            raise ValueError(
                "verify_ssl, ssl_context, fingerprint and ssl "
                "parameters are mutually exclusive"
            )
        else:
            ssl = ssl_context
    if fingerprint is not None:
        warnings.warn(
            "fingerprint is deprecated, use ssl=Fingerprint(fingerprint) instead",
            DeprecationWarning,
            stacklevel=3,
        )
        if ssl is not True:
            raise ValueError(
                "verify_ssl, ssl_context, fingerprint and ssl "
                "parameters are mutually exclusive"
            )
        else:
            ssl = Fingerprint(fingerprint)
    if not isinstance(ssl, SSL_ALLOWED_TYPES):
        raise TypeError(
            "ssl should be SSLContext, bool, Fingerprint or None, "
            "got {!r} instead.".format(ssl)
        )
    return ssl


_SSL_SCHEMES = frozenset(("https", "wss"))


# ConnectionKey is a NamedTuple because it is used as a key in a dict
# and a set in the connector. Since a NamedTuple is a tuple it uses
# the fast native tuple __hash__ and __eq__ implementation in CPython.
class ConnectionKey(NamedTuple):
    # the key should contain an information about used proxy / TLS
    # to prevent reusing wrong connections from a pool
    host: str
    port: Optional[int]
    is_ssl: bool
    ssl: Union[SSLContext, bool, Fingerprint]
    proxy: Optional[URL]
    proxy_auth: Optional[BasicAuth]
    proxy_headers_hash: Optional[int]  # hash(CIMultiDict)


def _is_expected_content_type(
    response_content_type: str, expected_content_type: str
) -> bool:
    if expected_content_type == "application/json":
        return json_re.match(response_content_type) is not None
    return expected_content_type in response_content_type


def _warn_if_unclosed_payload(payload: payload.Payload, stacklevel: int = 2) -> None:
    """Warn if the payload is not closed.

    Callers must check that the body is a Payload before calling this method.

    Args:
        payload: The payload to check
        stacklevel: Stack level for the warning (default 2 for direct callers)
    """
    if not payload.autoclose and not payload.consumed:
        warnings.warn(
            "The previous request body contains unclosed resources. "
            "Use await request.update_body() instead of setting request.body "
            "directly to properly close resources and avoid leaks.",
            ResourceWarning,
            stacklevel=stacklevel,
        )


class ClientResponse(HeadersMixin):

    # Some of these attributes are None when created,
    # but will be set by the start() method.
    # As the end user will likely never see the None values, we cheat the types below.
    # from the Status-Line of the response
    version: Optional[HttpVersion] = None  # HTTP-Version
    status: int = None  # type: ignore[assignment] # Status-Code
    reason: Optional[str] = None  # Reason-Phrase

    content: StreamReader = None  # type: ignore[assignment] # Payload stream
    _body: Optional[bytes] = None
    _headers: CIMultiDictProxy[str] = None  # type: ignore[assignment]
    _history: Tuple["ClientResponse", ...] = ()
    _raw_headers: RawHeaders = None  # type: ignore[assignment]

    _connection: Optional["Connection"] = None  # current connection
    _cookies: Optional[SimpleCookie] = None
    _raw_cookie_headers: Optional[Tuple[str, ...]] = None
    _continue: Optional["asyncio.Future[bool]"] = None
    _source_traceback: Optional[traceback.StackSummary] = None
    _session: Optional["ClientSession"] = None
    # set up by ClientRequest after ClientResponse object creation
    # post-init stage allows to not change ctor signature
    _closed = True  # to allow __del__ for non-initialized properly response
    _released = False
    _in_context = False

    _resolve_charset: Callable[["ClientResponse", bytes], str] = lambda *_: "utf-8"

    __writer: Optional["asyncio.Task[None]"] = None

    def __init__(
        self,
        method: str,
        url: URL,
        *,
        writer: "Optional[asyncio.Task[None]]",
        continue100: Optional["asyncio.Future[bool]"],
        timer: BaseTimerContext,
        request_info: RequestInfo,
        traces: List["Trace"],
        loop: asyncio.AbstractEventLoop,
        session: "ClientSession",
    ) -> None:
        # URL forbids subclasses, so a simple type check is enough.
        assert type(url) is URL

        self.method = method

        self._real_url = url
        self._url = url.with_fragment(None) if url.raw_fragment else url
        if writer is not None:
            self._writer = writer
        if continue100 is not None:
            self._continue = continue100
        self._request_info = request_info
        self._timer = timer if timer is not None else TimerNoop()
        self._cache: Dict[str, Any] = {}
        self._traces = traces
        self._loop = loop
        # Save reference to _resolve_charset, so that get_encoding() will still
        # work after the response has finished reading the body.
        # TODO: Fix session=None in tests (see ClientRequest.__init__).
        if session is not None:
            # store a reference to session #1985
            self._session = session
            self._resolve_charset = session._resolve_charset
        if loop.get_debug():
            self._source_traceback = traceback.extract_stack(sys._getframe(1))

    def __reset_writer(self, _: object = None) -> None:
        self.__writer = None

    @property
    def _writer(self) -> Optional["asyncio.Task[None]"]:
        """The writer task for streaming data.

        _writer is only provided for backwards compatibility
        for subclasses that may need to access it.
        """
        return self.__writer

    @_writer.setter
    def _writer(self, writer: Optional["asyncio.Task[None]"]) -> None:
        """Set the writer task for streaming data."""
        if self.__writer is not None:
            self.__writer.remove_done_callback(self.__reset_writer)
        self.__writer = writer
        if writer is None:
            return
        if writer.done():
            # The writer is already done, so we can clear it immediately.
            self.__writer = None
        else:
            writer.add_done_callback(self.__reset_writer)

    @property
    def cookies(self) -> SimpleCookie:
        if self._cookies is None:
            if self._raw_cookie_headers is not None:
                # Parse cookies for response.cookies (SimpleCookie for backward compatibility)
                cookies = SimpleCookie()
                # Use parse_set_cookie_headers for more lenient parsing that handles
                # malformed cookies better than SimpleCookie.load
                cookies.update(parse_set_cookie_headers(self._raw_cookie_headers))
                self._cookies = cookies
            else:
                self._cookies = SimpleCookie()
        return self._cookies

    @cookies.setter
    def cookies(self, cookies: SimpleCookie) -> None:
        self._cookies = cookies
        # Generate raw cookie headers from the SimpleCookie
        if cookies:
            self._raw_cookie_headers = tuple(
                morsel.OutputString() for morsel in cookies.values()
            )
        else:
            self._raw_cookie_headers = None

    @reify
    def url(self) -> URL:
        return self._url

    @reify
    def url_obj(self) -> URL:
        warnings.warn("Deprecated, use .url #1654", DeprecationWarning, stacklevel=2)
        return self._url

    @reify
    def real_url(self) -> URL:
        return self._real_url

    @reify
    def host(self) -> str:
        assert self._url.host is not None
        return self._url.host

    @reify
    def headers(self) -> "CIMultiDictProxy[str]":
        return self._headers

    @reify
    def raw_headers(self) -> RawHeaders:
        return self._raw_headers

    @reify
    def request_info(self) -> RequestInfo:
        return self._request_info

    @reify
    def content_disposition(self) -> Optional[ContentDisposition]:
        raw = self._headers.get(hdrs.CONTENT_DISPOSITION)
        if raw is None:
            return None
        disposition_type, params_dct = multipart.parse_content_disposition(raw)
        params = MappingProxyType(params_dct)
        filename = multipart.content_disposition_filename(params)
        return ContentDisposition(disposition_type, params, filename)

    def __del__(self, _warnings: Any = warnings) -> None:
        if self._closed:
            return

        if self._connection is not None:
            self._connection.release()
            self._cleanup_writer()

            if self._loop.get_debug():
                kwargs = {"source": self}
                _warnings.warn(f"Unclosed response {self!r}", ResourceWarning, **kwargs)
                context = {"client_response": self, "message": "Unclosed response"}
                if self._source_traceback:
                    context["source_traceback"] = self._source_traceback
                self._loop.call_exception_handler(context)

    def __repr__(self) -> str:
        out = io.StringIO()
        ascii_encodable_url = str(self.url)
        if self.reason:
            ascii_encodable_reason = self.reason.encode(
                "ascii", "backslashreplace"
            ).decode("ascii")
        else:
            ascii_encodable_reason = "None"
        print(
            "<ClientResponse({}) [{} {}]>".format(
                ascii_encodable_url, self.status, ascii_encodable_reason
            ),
            file=out,
        )
        print(self.headers, file=out)
        return out.getvalue()

    @property
    def connection(self) -> Optional["Connection"]:
        return self._connection

    @reify
    def history(self) -> Tuple["ClientResponse", ...]:
        """A sequence of of responses, if redirects occurred."""
        return self._history

    @reify
    def links(self) -> "MultiDictProxy[MultiDictProxy[Union[str, URL]]]":
        links_str = ", ".join(self.headers.getall("link", []))

        if not links_str:
            return MultiDictProxy(MultiDict())

        links: MultiDict[MultiDictProxy[Union[str, URL]]] = MultiDict()

        for val in re.split(r",(?=\s*<)", links_str):
            match = re.match(r"\s*<(.*)>(.*)", val)
            if match is None:  # pragma: no cover
                # the check exists to suppress mypy error
                continue
            url, params_str = match.groups()
            params = params_str.split(";")[1:]

            link: MultiDict[Union[str, URL]] = MultiDict()

            for param in params:
                match = re.match(r"^\s*(\S*)\s*=\s*(['\"]?)(.*?)(\2)\s*$", param, re.M)
                if match is None:  # pragma: no cover
                    # the check exists to suppress mypy error
                    continue
                key, _, value, _ = match.groups()

                link.add(key, value)

            key = link.get("rel", url)

            link.add("url", self.url.join(URL(url)))

            links.add(str(key), MultiDictProxy(link))

        return MultiDictProxy(links)

    async def start(self, connection: "Connection") -> "ClientResponse":
        """Start response processing."""
        self._closed = False
        self._protocol = connection.protocol
        self._connection = connection

        with self._timer:
            while True:
                # read response
                try:
                    protocol = self._protocol
                    message, payload = await protocol.read()  # type: ignore[union-attr]
                except http.HttpProcessingError as exc:
                    raise ClientResponseError(
                        self.request_info,
                        self.history,
                        status=exc.code,
                        message=exc.message,
                        headers=exc.headers,
                    ) from exc

                if message.code < 100 or message.code > 199 or message.code == 101:
                    break

                if self._continue is not None:
                    set_result(self._continue, True)
                    self._continue = None

        # payload eof handler
        payload.on_eof(self._response_eof)

        # response status
        self.version = message.version
        self.status = message.code
        self.reason = message.reason

        # headers
        self._headers = message.headers  # type is CIMultiDictProxy
        self._raw_headers = message.raw_headers  # type is Tuple[bytes, bytes]

        # payload
        self.content = payload

        # cookies
        if cookie_hdrs := self.headers.getall(hdrs.SET_COOKIE, ()):
            # Store raw cookie headers for CookieJar
            self._raw_cookie_headers = tuple(cookie_hdrs)
        return self

    def _response_eof(self) -> None:
        if self._closed:
            return

        # protocol could be None because connection could be detached
        protocol = self._connection and self._connection.protocol
        if protocol is not None and protocol.upgraded:
            return

        self._closed = True
        self._cleanup_writer()
        self._release_connection()

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        if not self._released:
            self._notify_content()

        self._closed = True
        if self._loop is None or self._loop.is_closed():
            return

        self._cleanup_writer()
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def release(self) -> Any:
        if not self._released:
            self._notify_content()

        self._closed = True

        self._cleanup_writer()
        self._release_connection()
        return noop()

    @property
    def ok(self) -> bool:
        """Returns ``True`` if ``status`` is less than ``400``, ``False`` if not.

        This is **not** a check for ``200 OK`` but a check that the response
        status is under 400.
        """
        return 400 > self.status

    def raise_for_status(self) -> None:
        if not self.ok:
            # reason should always be not None for a started response
            assert self.reason is not None

            # If we're in a context we can rely on __aexit__() to release as the
            # exception propagates.
            if not self._in_context:
                self.release()

            raise ClientResponseError(
                self.request_info,
                self.history,
                status=self.status,
                message=self.reason,
                headers=self.headers,
            )

    def _release_connection(self) -> None:
        if self._connection is not None:
            if self.__writer is None:
                self._connection.release()
                self._connection = None
            else:
                self.__writer.add_done_callback(lambda f: self._release_connection())

    async def _wait_released(self) -> None:
        if self.__writer is not None:
            try:
                await self.__writer
            except asyncio.CancelledError:
                if (
                    sys.version_info >= (3, 11)
                    and (task := asyncio.current_task())
                    and task.cancelling()
                ):
                    raise
        self._release_connection()

    def _cleanup_writer(self) -> None:
        if self.__writer is not None:
            self.__writer.cancel()
        self._session = None

    def _notify_content(self) -> None:
        content = self.content
        if content and content.exception() is None:
            set_exception(content, _CONNECTION_CLOSED_EXCEPTION)
        self._released = True

    async def wait_for_close(self) -> None:
        if self.__writer is not None:
            try:
                await self.__writer
            except asyncio.CancelledError:
                if (
                    sys.version_info >= (3, 11)
                    and (task := asyncio.current_task())
                    and task.cancelling()
                ):
                    raise
        self.release()

    async def read(self) -> bytes:
        """Read response payload."""
        if self._body is None:
            try:
                self._body = await self.content.read()
                for trace in self._traces:
                    await trace.send_response_chunk_received(
                        self.method, self.url, self._body
                    )
            except BaseException:
                self.close()
                raise
        elif self._released:  # Response explicitly released
            raise ClientConnectionError("Connection closed")

        protocol = self._connection and self._connection.protocol
        if protocol is None or not protocol.upgraded:
            await self._wait_released()  # Underlying connection released
        return self._body

    def get_encoding(self) -> str:
        ctype = self.headers.get(hdrs.CONTENT_TYPE, "").lower()
        mimetype = helpers.parse_mimetype(ctype)

        encoding = mimetype.parameters.get("charset")
        if encoding:
            with contextlib.suppress(LookupError, ValueError):
                return codecs.lookup(encoding).name

        if mimetype.type == "application" and (
            mimetype.subtype == "json" or mimetype.subtype == "rdap"
        ):
            # RFC 7159 states that the default encoding is UTF-8.
            # RFC 7483 defines application/rdap+json
            return "utf-8"

        if self._body is None:
            raise RuntimeError(
                "Cannot compute fallback encoding of a not yet read body"
            )

        return self._resolve_charset(self, self._body)

    async def text(self, encoding: Optional[str] = None, errors: str = "strict") -> str:
        """Read response payload and decode."""
        if self._body is None:
            await self.read()

        if encoding is None:
            encoding = self.get_encoding()

        return self._body.decode(encoding, errors=errors)  # type: ignore[union-attr]

    async def json(
        self,
        *,
        encoding: Optional[str] = None,
        loads: JSONDecoder = DEFAULT_JSON_DECODER,
        content_type: Optional[str] = "application/json",
    ) -> Any:
        """Read and decodes JSON response."""
        if self._body is None:
            await self.read()

        if content_type:
            ctype = self.headers.get(hdrs.CONTENT_TYPE, "").lower()
            if not _is_expected_content_type(ctype, content_type):
                raise ContentTypeError(
                    self.request_info,
                    self.history,
                    status=self.status,
                    message=(
                        "Attempt to decode JSON with unexpected mimetype: %s" % ctype
                    ),
                    headers=self.headers,
                )

        stripped = self._body.strip()  # type: ignore[union-attr]
        if not stripped:
            return None

        if encoding is None:
            encoding = self.get_encoding()

        return loads(stripped.decode(encoding))

    async def __aenter__(self) -> "ClientResponse":
        self._in_context = True
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self._in_context = False
        # similar to _RequestContextManager, we do not need to check
        # for exceptions, response object can close connection
        # if state is broken
        self.release()
        await self.wait_for_close()


class ClientRequest:
    GET_METHODS = {
        hdrs.METH_GET,
        hdrs.METH_HEAD,
        hdrs.METH_OPTIONS,
        hdrs.METH_TRACE,
    }
    POST_METHODS = {hdrs.METH_PATCH, hdrs.METH_POST, hdrs.METH_PUT}
    ALL_METHODS = GET_METHODS.union(POST_METHODS).union({hdrs.METH_DELETE})

    DEFAULT_HEADERS = {
        hdrs.ACCEPT: "*/*",
        hdrs.ACCEPT_ENCODING: _gen_default_accept_encoding(),
    }

    # Type of body depends on PAYLOAD_REGISTRY, which is dynamic.
    _body: Union[None, payload.Payload] = None
    auth = None
    response = None

    __writer: Optional["asyncio.Task[None]"] = None  # async task for streaming data

    # These class defaults help create_autospec() work correctly.
    # If autospec is improved in future, maybe these can be removed.
    url = URL()
    method = "GET"

    _continue = None  # waiter future for '100 Continue' response

    _skip_auto_headers: Optional["CIMultiDict[None]"] = None

    # N.B.
    # Adding __del__ method with self._writer closing doesn't make sense
    # because _writer is instance method, thus it keeps a reference to self.
    # Until writer has finished finalizer will not be called.

    def __init__(
        self,
        method: str,
        url: URL,
        *,
        params: Query = None,
        headers: Optional[LooseHeaders] = None,
        skip_auto_headers: Optional[Iterable[str]] = None,
        data: Any = None,
        cookies: Optional[LooseCookies] = None,
        auth: Optional[BasicAuth] = None,
        version: http.HttpVersion = http.HttpVersion11,
        compress: Union[str, bool, None] = None,
        chunked: Optional[bool] = None,
        expect100: bool = False,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        response_class: Optional[Type["ClientResponse"]] = None,
        proxy: Optional[URL] = None,
        proxy_auth: Optional[BasicAuth] = None,
        timer: Optional[BaseTimerContext] = None,
        session: Optional["ClientSession"] = None,
        ssl: Union[SSLContext, bool, Fingerprint] = True,
        proxy_headers: Optional[LooseHeaders] = None,
        traces: Optional[List["Trace"]] = None,
        trust_env: bool = False,
        server_hostname: Optional[str] = None,
    ):
        if loop is None:
            loop = asyncio.get_event_loop()
        if match := _CONTAINS_CONTROL_CHAR_RE.search(method):
            raise ValueError(
                f"Method cannot contain non-token characters {method!r} "
                f"(found at least {match.group()!r})"
            )
        # URL forbids subclasses, so a simple type check is enough.
        assert type(url) is URL, url
        if proxy is not None:
            assert type(proxy) is URL, proxy
        # FIXME: session is None in tests only, need to fix tests
        # assert session is not None
        if TYPE_CHECKING:
            assert session is not None
        self._session = session
        if params:
            url = url.extend_query(params)
        self.original_url = url
        self.url = url.with_fragment(None) if url.raw_fragment else url
        self.method = method.upper()
        self.chunked = chunked
        self.compress = compress
        self.loop = loop
        self.length = None
        if response_class is None:
            real_response_class = ClientResponse
        else:
            real_response_class = response_class
        self.response_class: Type[ClientResponse] = real_response_class
        self._timer = timer if timer is not None else TimerNoop()
        self._ssl = ssl if ssl is not None else True
        self.server_hostname = server_hostname

        if loop.get_debug():
            self._source_traceback = traceback.extract_stack(sys._getframe(1))

        self.update_version(version)
        self.update_host(url)
        self.update_headers(headers)
        self.update_auto_headers(skip_auto_headers)
        self.update_cookies(cookies)
        self.update_content_encoding(data)
        self.update_auth(auth, trust_env)
        self.update_proxy(proxy, proxy_auth, proxy_headers)

        self.update_body_from_data(data)
        if data is not None or self.method not in self.GET_METHODS:
            self.update_transfer_encoding()
        self.update_expect_continue(expect100)
        self._traces = [] if traces is None else traces

    def __reset_writer(self, _: object = None) -> None:
        self.__writer = None

    def _get_content_length(self) -> Optional[int]:
        """Extract and validate Content-Length header value.

        Returns parsed Content-Length value or None if not set.
        Raises ValueError if header exists but cannot be parsed as an integer.
        """
        if hdrs.CONTENT_LENGTH not in self.headers:
            return None

        content_length_hdr = self.headers[hdrs.CONTENT_LENGTH]
        try:
            return int(content_length_hdr)
        except ValueError:
            raise ValueError(
                f"Invalid Content-Length header: {content_length_hdr}"
            ) from None

    @property
    def skip_auto_headers(self) -> CIMultiDict[None]:
        return self._skip_auto_headers or CIMultiDict()

    @property
    def _writer(self) -> Optional["asyncio.Task[None]"]:
        return self.__writer

    @_writer.setter
    def _writer(self, writer: "asyncio.Task[None]") -> None:
        if self.__writer is not None:
            self.__writer.remove_done_callback(self.__reset_writer)
        self.__writer = writer
        writer.add_done_callback(self.__reset_writer)

    def is_ssl(self) -> bool:
        return self.url.scheme in _SSL_SCHEMES

    @property
    def ssl(self) -> Union["SSLContext", bool, Fingerprint]:
        return self._ssl

    @property
    def connection_key(self) -> ConnectionKey:
        if proxy_headers := self.proxy_headers:
            h: Optional[int] = hash(tuple(proxy_headers.items()))
        else:
            h = None
        url = self.url
        return tuple.__new__(
            ConnectionKey,
            (
                url.raw_host or "",
                url.port,
                url.scheme in _SSL_SCHEMES,
                self._ssl,
                self.proxy,
                self.proxy_auth,
                h,
            ),
        )

    @property
    def host(self) -> str:
        ret = self.url.raw_host
        assert ret is not None
        return ret

    @property
    def port(self) -> Optional[int]:
        return self.url.port

    @property
    def body(self) -> Union[payload.Payload, Literal[b""]]:
        """Request body."""
        # empty body is represented as bytes for backwards compatibility
        return self._body or b""

    @body.setter
    def body(self, value: Any) -> None:
        """Set request body with warning for non-autoclose payloads.

        WARNING: This setter must be called from within an event loop and is not
        thread-safe. Setting body outside of an event loop may raise RuntimeError
        when closing file-based payloads.

        DEPRECATED: Direct assignment to body is deprecated and will be removed
        in a future version. Use await update_body() instead for proper resource
        management.
        """
        # Close existing payload if present
        if self._body is not None:
            # Warn if the payload needs manual closing
            # stacklevel=3: user code -> body setter -> _warn_if_unclosed_payload
            _warn_if_unclosed_payload(self._body, stacklevel=3)
            # NOTE: In the future, when we remove sync close support,
            # this setter will need to be removed and only the async
            # update_body() method will be available. For now, we call
            # _close() for backwards compatibility.
            self._body._close()
        self._update_body(value)

    @property
    def request_info(self) -> RequestInfo:
        headers: CIMultiDictProxy[str] = CIMultiDictProxy(self.headers)
        # These are created on every request, so we use a NamedTuple
        # for performance reasons. We don't use the RequestInfo.__new__
        # method because it has a different signature which is provided
        # for backwards compatibility only.
        return tuple.__new__(
            RequestInfo, (self.url, self.method, headers, self.original_url)
        )

    @property
    def session(self) -> "ClientSession":
        """Return the ClientSession instance.

        This property provides access to the ClientSession that initiated
        this request, allowing middleware to make additional requests
        using the same session.
        """
        return self._session

    def update_host(self, url: URL) -> None:
        """Update destination host, port and connection type (ssl)."""
        # get host/port
        if not url.raw_host:
            raise InvalidURL(url)

        # basic auth info
        if url.raw_user or url.raw_password:
            self.auth = helpers.BasicAuth(url.user or "", url.password or "")

    def update_version(self, version: Union[http.HttpVersion, str]) -> None:
        """Convert request version to two elements tuple.

        parser HTTP version '1.1' => (1, 1)
        """
        if isinstance(version, str):
            v = [part.strip() for part in version.split(".", 1)]
            try:
                version = http.HttpVersion(int(v[0]), int(v[1]))
            except ValueError:
                raise ValueError(
                    f"Can not parse http version number: {version}"
                ) from None
        self.version = version

    def update_headers(self, headers: Optional[LooseHeaders]) -> None:
        """Update request headers."""
        self.headers: CIMultiDict[str] = CIMultiDict()

        # Build the host header
        host = self.url.host_port_subcomponent

        # host_port_subcomponent is None when the URL is a relative URL.
        # but we know we do not have a relative URL here.
        assert host is not None
        self.headers[hdrs.HOST] = host

        if not headers:
            return

        if isinstance(headers, (dict, MultiDictProxy, MultiDict)):
            headers = headers.items()

        for key, value in headers:  # type: ignore[misc]
            # A special case for Host header
            if key in hdrs.HOST_ALL:
                self.headers[key] = value
            else:
                self.headers.add(key, value)

    def update_auto_headers(self, skip_auto_headers: Optional[Iterable[str]]) -> None:
        if skip_auto_headers is not None:
            self._skip_auto_headers = CIMultiDict(
                (hdr, None) for hdr in sorted(skip_auto_headers)
            )
            used_headers = self.headers.copy()
            used_headers.extend(self._skip_auto_headers)  # type: ignore[arg-type]
        else:
            # Fast path when there are no headers to skip
            # which is the most common case.
            used_headers = self.headers

        for hdr, val in self.DEFAULT_HEADERS.items():
            if hdr not in used_headers:
                self.headers[hdr] = val

        if hdrs.USER_AGENT not in used_headers:
            self.headers[hdrs.USER_AGENT] = SERVER_SOFTWARE

    def update_cookies(self, cookies: Optional[LooseCookies]) -> None:
        """Update request cookies header."""
        if not cookies:
            return

        c = SimpleCookie()
        if hdrs.COOKIE in self.headers:
            # parse_cookie_header for RFC 6265 compliant Cookie header parsing
            c.update(parse_cookie_header(self.headers.get(hdrs.COOKIE, "")))
            del self.headers[hdrs.COOKIE]

        if isinstance(cookies, Mapping):
            iter_cookies = cookies.items()
        else:
            iter_cookies = cookies  # type: ignore[assignment]
        for name, value in iter_cookies:
            if isinstance(value, Morsel):
                # Use helper to preserve coded_value exactly as sent by server
                c[name] = preserve_morsel_with_coded_value(value)
            else:
                c[name] = value  # type: ignore[assignment]

        self.headers[hdrs.COOKIE] = c.output(header="", sep=";").strip()

    def update_content_encoding(self, data: Any) -> None:
        """Set request content encoding."""
        if not data:
            # Don't compress an empty body.
            self.compress = None
            return

        if self.headers.get(hdrs.CONTENT_ENCODING):
            if self.compress:
                raise ValueError(
                    "compress can not be set if Content-Encoding header is set"
                )
        elif self.compress:
            if not isinstance(self.compress, str):
                self.compress = "deflate"
            self.headers[hdrs.CONTENT_ENCODING] = self.compress
            self.chunked = True  # enable chunked, no need to deal with length

    def update_transfer_encoding(self) -> None:
        """Analyze transfer-encoding header."""
        te = self.headers.get(hdrs.TRANSFER_ENCODING, "").lower()

        if "chunked" in te:
            if self.chunked:
                raise ValueError(
                    "chunked can not be set "
                    'if "Transfer-Encoding: chunked" header is set'
                )

        elif self.chunked:
            if hdrs.CONTENT_LENGTH in self.headers:
                raise ValueError(
                    "chunked can not be set if Content-Length header is set"
                )

            self.headers[hdrs.TRANSFER_ENCODING] = "chunked"

    def update_auth(self, auth: Optional[BasicAuth], trust_env: bool = False) -> None:
        """Set basic auth."""
        if auth is None:
            auth = self.auth
        if auth is None and trust_env and self.url.host is not None:
            netrc_obj = netrc_from_env()
            with contextlib.suppress(LookupError):
                auth = basicauth_from_netrc(netrc_obj, self.url.host)
        if auth is None:
            return

        if not isinstance(auth, helpers.BasicAuth):
            raise TypeError("BasicAuth() tuple is required instead")

        self.headers[hdrs.AUTHORIZATION] = auth.encode()

    def update_body_from_data(self, body: Any, _stacklevel: int = 3) -> None:
        """Update request body from data."""
        if self._body is not None:
            _warn_if_unclosed_payload(self._body, stacklevel=_stacklevel)

        if body is None:
            self._body = None
            # Set Content-Length to 0 when body is None for methods that expect a body
            if (
                self.method not in self.GET_METHODS
                and not self.chunked
                and hdrs.CONTENT_LENGTH not in self.headers
            ):
                self.headers[hdrs.CONTENT_LENGTH] = "0"
            return

        # FormData
        maybe_payload = body() if isinstance(body, FormData) else body

        try:
            body_payload = payload.PAYLOAD_REGISTRY.get(maybe_payload, disposition=None)
        except payload.LookupError:
            body_payload = FormData(maybe_payload)()  # type: ignore[arg-type]

        self._body = body_payload
        # enable chunked encoding if needed
        if not self.chunked and hdrs.CONTENT_LENGTH not in self.headers:
            if (size := body_payload.size) is not None:
                self.headers[hdrs.CONTENT_LENGTH] = str(size)
            else:
                self.chunked = True

        # copy payload headers
        assert body_payload.headers
        headers = self.headers
        skip_headers = self._skip_auto_headers
        for key, value in body_payload.headers.items():
            if key in headers or (skip_headers is not None and key in skip_headers):
                continue
            headers[key] = value

    def _update_body(self, body: Any) -> None:
        """Update request body after its already been set."""
        # Remove existing Content-Length header since body is changing
        if hdrs.CONTENT_LENGTH in self.headers:
            del self.headers[hdrs.CONTENT_LENGTH]

        # Remove existing Transfer-Encoding header to avoid conflicts
        if self.chunked and hdrs.TRANSFER_ENCODING in self.headers:
            del self.headers[hdrs.TRANSFER_ENCODING]

        # Now update the body using the existing method
        # Called from _update_body, add 1 to stacklevel from caller
        self.update_body_from_data(body, _stacklevel=4)

        # Update transfer encoding headers if needed (same logic as __init__)
        if body is not None or self.method not in self.GET_METHODS:
            self.update_transfer_encoding()

    async def update_body(self, body: Any) -> None:
        """
        Update request body and close previous payload if needed.

        This method safely updates the request body by first closing any existing
        payload to prevent resource leaks, then setting the new body.

        IMPORTANT: Always use this method instead of setting request.body directly.
        Direct assignment to request.body will leak resources if the previous body
        contains file handles, streams, or other resources that need cleanup.

        Args:
            body: The new body content. Can be:
                - bytes/bytearray: Raw binary data
                - str: Text data (will be encoded using charset from Content-Type)
                - FormData: Form data that will be encoded as multipart/form-data
                - Payload: A pre-configured payload object
                - AsyncIterable: An async iterable of bytes chunks
                - File-like object: Will be read and sent as binary data
                - None: Clears the body

        Usage:
            # CORRECT: Use update_body
            await request.update_body(b"new request data")

            # WRONG: Don't set body directly
            # request.body = b"new request data"  # This will leak resources!

            # Update with form data
            form_data = FormData()
            form_data.add_field('field', 'value')
            await request.update_body(form_data)

            # Clear body
            await request.update_body(None)

        Note:
            This method is async because it may need to close file handles or
            other resources associated with the previous payload. Always await
            this method to ensure proper cleanup.

        Warning:
            Setting request.body directly is highly discouraged and can lead to:
            - Resource leaks (unclosed file handles, streams)
            - Memory leaks (unreleased buffers)
            - Unexpected behavior with streaming payloads

            It is not recommended to change the payload type in middleware. If the
            body was already set (e.g., as bytes), it's best to keep the same type
            rather than converting it (e.g., to str) as this may result in unexpected
            behavior.

        See Also:
            - update_body_from_data: Synchronous body update without cleanup
            - body property: Direct body access (STRONGLY DISCOURAGED)

        """
        # Close existing payload if it exists and needs closing
        if self._body is not None:
            await self._body.close()
        self._update_body(body)

    def update_expect_continue(self, expect: bool = False) -> None:
        if expect:
            self.headers[hdrs.EXPECT] = "100-continue"
        elif (
            hdrs.EXPECT in self.headers
            and self.headers[hdrs.EXPECT].lower() == "100-continue"
        ):
            expect = True

        if expect:
            self._continue = self.loop.create_future()

    def update_proxy(
        self,
        proxy: Optional[URL],
        proxy_auth: Optional[BasicAuth],
        proxy_headers: Optional[LooseHeaders],
    ) -> None:
        self.proxy = proxy
        if proxy is None:
            self.proxy_auth = None
            self.proxy_headers = None
            return

        if proxy_auth and not isinstance(proxy_auth, helpers.BasicAuth):
            raise ValueError("proxy_auth must be None or BasicAuth() tuple")
        self.proxy_auth = proxy_auth

        if proxy_headers is not None and not isinstance(
            proxy_headers, (MultiDict, MultiDictProxy)
        ):
            proxy_headers = CIMultiDict(proxy_headers)
        self.proxy_headers = proxy_headers

    async def write_bytes(
        self,
        writer: AbstractStreamWriter,
        conn: "Connection",
        content_length: Optional[int],
    ) -> None:
        """
        Write the request body to the connection stream.

        This method handles writing different types of request bodies:
        1. Payload objects (using their specialized write_with_length method)
        2. Bytes/bytearray objects
        3. Iterable body content

        Args:
            writer: The stream writer to write the body to
            conn: The connection being used for this request
            content_length: Optional maximum number of bytes to write from the body
                            (None means write the entire body)

        The method properly handles:
        - Waiting for 100-Continue responses if required
        - Content length constraints for chunked encoding
        - Error handling for network issues, cancellation, and other exceptions
        - Signaling EOF and timeout management

        Raises:
            ClientOSError: When there's an OS-level error writing the body
            ClientConnectionError: When there's a general connection error
            asyncio.CancelledError: When the operation is cancelled

        """
        # 100 response
        if self._continue is not None:
            # Force headers to be sent before waiting for 100-continue
            writer.send_headers()
            await writer.drain()
            await self._continue

        protocol = conn.protocol
        assert protocol is not None
        try:
            # This should be a rare case but the
            # self._body can be set to None while
            # the task is being started or we wait above
            # for the 100-continue response.
            # The more likely case is we have an empty
            # payload, but 100-continue is still expected.
            if self._body is not None:
                await self._body.write_with_length(writer, content_length)
        except OSError as underlying_exc:
            reraised_exc = underlying_exc

            # Distinguish between timeout and other OS errors for better error reporting
            exc_is_not_timeout = underlying_exc.errno is not None or not isinstance(
                underlying_exc, asyncio.TimeoutError
            )
            if exc_is_not_timeout:
                reraised_exc = ClientOSError(
                    underlying_exc.errno,
                    f"Can not write request body for {self.url !s}",
                )

            set_exception(protocol, reraised_exc, underlying_exc)
        except asyncio.CancelledError:
            # Body hasn't been fully sent, so connection can't be reused
            conn.close()
            raise
        except Exception as underlying_exc:
            set_exception(
                protocol,
                ClientConnectionError(
                    "Failed to send bytes into the underlying connection "
                    f"{conn !s}: {underlying_exc!r}",
                ),
                underlying_exc,
            )
        else:
            # Successfully wrote the body, signal EOF and start response timeout
            await writer.write_eof()
            protocol.start_timeout()

    async def send(self, conn: "Connection") -> "ClientResponse":
        # Specify request target:
        # - CONNECT request must send authority form URI
        # - not CONNECT proxy must send absolute form URI
        # - most common is origin form URI
        if self.method == hdrs.METH_CONNECT:
            connect_host = self.url.host_subcomponent
            assert connect_host is not None
            path = f"{connect_host}:{self.url.port}"
        elif self.proxy and not self.is_ssl():
            path = str(self.url)
        else:
            path = self.url.raw_path_qs

        protocol = conn.protocol
        assert protocol is not None
        writer = StreamWriter(
            protocol,
            self.loop,
            on_chunk_sent=(
                functools.partial(self._on_chunk_request_sent, self.method, self.url)
                if self._traces
                else None
            ),
            on_headers_sent=(
                functools.partial(self._on_headers_request_sent, self.method, self.url)
                if self._traces
                else None
            ),
        )

        if self.compress:
            writer.enable_compression(self.compress)  # type: ignore[arg-type]

        if self.chunked is not None:
            writer.enable_chunking()

        # set default content-type
        if (
            self.method in self.POST_METHODS
            and (
                self._skip_auto_headers is None
                or hdrs.CONTENT_TYPE not in self._skip_auto_headers
            )
            and hdrs.CONTENT_TYPE not in self.headers
        ):
            self.headers[hdrs.CONTENT_TYPE] = "application/octet-stream"

        v = self.version
        if hdrs.CONNECTION not in self.headers:
            if conn._connector.force_close:
                if v == HttpVersion11:
                    self.headers[hdrs.CONNECTION] = "close"
            elif v == HttpVersion10:
                self.headers[hdrs.CONNECTION] = "keep-alive"

        # status + headers
        status_line = f"{self.method} {path} HTTP/{v.major}.{v.minor}"

        # Buffer headers for potential coalescing with body
        await writer.write_headers(status_line, self.headers)

        task: Optional["asyncio.Task[None]"]
        if self._body or self._continue is not None or protocol.writing_paused:
            coro = self.write_bytes(writer, conn, self._get_content_length())
            if sys.version_info >= (3, 12):
                # Optimization for Python 3.12, try to write
                # bytes immediately to avoid having to schedule
                # the task on the event loop.
                task = asyncio.Task(coro, loop=self.loop, eager_start=True)
            else:
                task = self.loop.create_task(coro)
            if task.done():
                task = None
            else:
                self._writer = task
        else:
            # We have nothing to write because
            # - there is no body
            # - the protocol does not have writing paused
            # - we are not waiting for a 100-continue response
            protocol.start_timeout()
            writer.set_eof()
            task = None
        response_class = self.response_class
        assert response_class is not None
        self.response = response_class(
            self.method,
            self.original_url,
            writer=task,
            continue100=self._continue,
            timer=self._timer,
            request_info=self.request_info,
            traces=self._traces,
            loop=self.loop,
            session=self._session,
        )
        return self.response

    async def close(self) -> None:
        if self.__writer is not None:
            try:
                await self.__writer
            except asyncio.CancelledError:
                if (
                    sys.version_info >= (3, 11)
                    and (task := asyncio.current_task())
                    and task.cancelling()
                ):
                    raise

    def terminate(self) -> None:
        if self.__writer is not None:
            if not self.loop.is_closed():
                self.__writer.cancel()
            self.__writer.remove_done_callback(self.__reset_writer)
            self.__writer = None

    async def _on_chunk_request_sent(self, method: str, url: URL, chunk: bytes) -> None:
        for trace in self._traces:
            await trace.send_request_chunk_sent(method, url, chunk)

    async def _on_headers_request_sent(
        self, method: str, url: URL, headers: "CIMultiDict[str]"
    ) -> None:
        for trace in self._traces:
            await trace.send_request_headers(method, url, headers)

# === NexusCore/openenv\Lib\site-packages\grpc\_server.py ===
# Copyright 2016 gRPC authors.
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
"""Service-side implementation of gRPC Python."""

from __future__ import annotations

import abc
import collections
from concurrent import futures
import contextvars
import enum
import logging
import threading
import time
import traceback
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

import grpc  # pytype: disable=pyi-error
from grpc import _common  # pytype: disable=pyi-error
from grpc import _compression  # pytype: disable=pyi-error
from grpc import _interceptor  # pytype: disable=pyi-error
from grpc import _observability  # pytype: disable=pyi-error
from grpc._cython import cygrpc
from grpc._typing import ArityAgnosticMethodHandler
from grpc._typing import ChannelArgumentType
from grpc._typing import DeserializingFunction
from grpc._typing import MetadataType
from grpc._typing import NullaryCallbackType
from grpc._typing import ResponseType
from grpc._typing import SerializingFunction
from grpc._typing import ServerCallbackTag
from grpc._typing import ServerTagCallbackType

_LOGGER = logging.getLogger(__name__)

_SHUTDOWN_TAG = "shutdown"
_REQUEST_CALL_TAG = "request_call"

_RECEIVE_CLOSE_ON_SERVER_TOKEN = "receive_close_on_server"
_SEND_INITIAL_METADATA_TOKEN = "send_initial_metadata"
_RECEIVE_MESSAGE_TOKEN = "receive_message"
_SEND_MESSAGE_TOKEN = "send_message"
_SEND_INITIAL_METADATA_AND_SEND_MESSAGE_TOKEN = (
    "send_initial_metadata * send_message"
)
_SEND_STATUS_FROM_SERVER_TOKEN = "send_status_from_server"
_SEND_INITIAL_METADATA_AND_SEND_STATUS_FROM_SERVER_TOKEN = (
    "send_initial_metadata * send_status_from_server"
)

_OPEN = "open"
_CLOSED = "closed"
_CANCELLED = "cancelled"

_EMPTY_FLAGS = 0

_DEALLOCATED_SERVER_CHECK_PERIOD_S = 1.0
_INF_TIMEOUT = 1e9


def _serialized_request(request_event: cygrpc.BaseEvent) -> bytes:
    return request_event.batch_operations[0].message()


def _application_code(code: grpc.StatusCode) -> cygrpc.StatusCode:
    cygrpc_code = _common.STATUS_CODE_TO_CYGRPC_STATUS_CODE.get(code)
    return cygrpc.StatusCode.unknown if cygrpc_code is None else cygrpc_code


def _completion_code(state: _RPCState) -> cygrpc.StatusCode:
    if state.code is None:
        return cygrpc.StatusCode.ok
    else:
        return _application_code(state.code)


def _abortion_code(
    state: _RPCState, code: cygrpc.StatusCode
) -> cygrpc.StatusCode:
    if state.code is None:
        return code
    else:
        return _application_code(state.code)


def _details(state: _RPCState) -> bytes:
    return b"" if state.details is None else state.details


class _HandlerCallDetails(
    collections.namedtuple(
        "_HandlerCallDetails",
        (
            "method",
            "invocation_metadata",
        ),
    ),
    grpc.HandlerCallDetails,
):
    pass


class _Method(abc.ABC):
    @abc.abstractmethod
    def name(self) -> Optional[str]:
        raise NotImplementedError()

    @abc.abstractmethod
    def handler(
        self, handler_call_details: _HandlerCallDetails
    ) -> Optional[grpc.RpcMethodHandler]:
        raise NotImplementedError()


class _RegisteredMethod(_Method):
    def __init__(
        self,
        name: str,
        registered_handler: Optional[grpc.RpcMethodHandler],
    ):
        self._name = name
        self._registered_handler = registered_handler

    def name(self) -> Optional[str]:
        return self._name

    def handler(
        self, handler_call_details: _HandlerCallDetails
    ) -> Optional[grpc.RpcMethodHandler]:
        return self._registered_handler


class _GenericMethod(_Method):
    def __init__(
        self,
        generic_handlers: List[grpc.GenericRpcHandler],
    ):
        self._generic_handlers = generic_handlers

    def name(self) -> Optional[str]:
        return None

    def handler(
        self, handler_call_details: _HandlerCallDetails
    ) -> Optional[grpc.RpcMethodHandler]:
        # If the same method have both generic and registered handler,
        # registered handler will take precedence.
        for generic_handler in self._generic_handlers:
            method_handler = generic_handler.service(handler_call_details)
            if method_handler is not None:
                return method_handler
        return None


class _RPCState(object):
    context: contextvars.Context
    condition: threading.Condition
    due = Set[str]
    request: Any
    client: str
    initial_metadata_allowed: bool
    compression_algorithm: Optional[grpc.Compression]
    disable_next_compression: bool
    trailing_metadata: Optional[MetadataType]
    code: Optional[grpc.StatusCode]
    details: Optional[bytes]
    statused: bool
    rpc_errors: List[Exception]
    callbacks: Optional[List[NullaryCallbackType]]
    aborted: bool

    def __init__(self):
        self.context = contextvars.Context()
        self.condition = threading.Condition()
        self.due = set()
        self.request = None
        self.client = _OPEN
        self.initial_metadata_allowed = True
        self.compression_algorithm = None
        self.disable_next_compression = False
        self.trailing_metadata = None
        self.code = None
        self.details = None
        self.statused = False
        self.rpc_errors = []
        self.callbacks = []
        self.aborted = False


def _raise_rpc_error(state: _RPCState) -> None:
    rpc_error = grpc.RpcError()
    state.rpc_errors.append(rpc_error)
    raise rpc_error


def _possibly_finish_call(
    state: _RPCState, token: str
) -> ServerTagCallbackType:
    state.due.remove(token)
    if not _is_rpc_state_active(state) and not state.due:
        callbacks = state.callbacks
        state.callbacks = None
        return state, callbacks
    else:
        return None, ()


def _send_status_from_server(state: _RPCState, token: str) -> ServerCallbackTag:
    def send_status_from_server(unused_send_status_from_server_event):
        with state.condition:
            return _possibly_finish_call(state, token)

    return send_status_from_server


def _get_initial_metadata(
    state: _RPCState, metadata: Optional[MetadataType]
) -> Optional[MetadataType]:
    with state.condition:
        if state.compression_algorithm:
            compression_metadata = (
                _compression.compression_algorithm_to_metadata(
                    state.compression_algorithm
                ),
            )
            if metadata is None:
                return compression_metadata
            else:
                return compression_metadata + tuple(metadata)
        else:
            return metadata


def _get_initial_metadata_operation(
    state: _RPCState, metadata: Optional[MetadataType]
) -> cygrpc.Operation:
    operation = cygrpc.SendInitialMetadataOperation(
        _get_initial_metadata(state, metadata), _EMPTY_FLAGS
    )
    return operation


def _abort(
    state: _RPCState, call: cygrpc.Call, code: cygrpc.StatusCode, details: bytes
) -> None:
    if state.client is not _CANCELLED:
        effective_code = _abortion_code(state, code)
        effective_details = details if state.details is None else state.details
        if state.initial_metadata_allowed:
            operations = (
                _get_initial_metadata_operation(state, None),
                cygrpc.SendStatusFromServerOperation(
                    state.trailing_metadata,
                    effective_code,
                    effective_details,
                    _EMPTY_FLAGS,
                ),
            )
            token = _SEND_INITIAL_METADATA_AND_SEND_STATUS_FROM_SERVER_TOKEN
        else:
            operations = (
                cygrpc.SendStatusFromServerOperation(
                    state.trailing_metadata,
                    effective_code,
                    effective_details,
                    _EMPTY_FLAGS,
                ),
            )
            token = _SEND_STATUS_FROM_SERVER_TOKEN
        call.start_server_batch(
            operations, _send_status_from_server(state, token)
        )
        state.statused = True
        state.due.add(token)


def _receive_close_on_server(state: _RPCState) -> ServerCallbackTag:
    def receive_close_on_server(receive_close_on_server_event):
        with state.condition:
            if receive_close_on_server_event.batch_operations[0].cancelled():
                state.client = _CANCELLED
            elif state.client is _OPEN:
                state.client = _CLOSED
            state.condition.notify_all()
            return _possibly_finish_call(state, _RECEIVE_CLOSE_ON_SERVER_TOKEN)

    return receive_close_on_server


def _receive_message(
    state: _RPCState,
    call: cygrpc.Call,
    request_deserializer: Optional[DeserializingFunction],
) -> ServerCallbackTag:
    def receive_message(receive_message_event):
        serialized_request = _serialized_request(receive_message_event)
        if serialized_request is None:
            with state.condition:
                if state.client is _OPEN:
                    state.client = _CLOSED
                state.condition.notify_all()
                return _possibly_finish_call(state, _RECEIVE_MESSAGE_TOKEN)
        else:
            request = _common.deserialize(
                serialized_request, request_deserializer
            )
            with state.condition:
                if request is None:
                    _abort(
                        state,
                        call,
                        cygrpc.StatusCode.internal,
                        b"Exception deserializing request!",
                    )
                else:
                    state.request = request
                state.condition.notify_all()
                return _possibly_finish_call(state, _RECEIVE_MESSAGE_TOKEN)

    return receive_message


def _send_initial_metadata(state: _RPCState) -> ServerCallbackTag:
    def send_initial_metadata(unused_send_initial_metadata_event):
        with state.condition:
            return _possibly_finish_call(state, _SEND_INITIAL_METADATA_TOKEN)

    return send_initial_metadata


def _send_message(state: _RPCState, token: str) -> ServerCallbackTag:
    def send_message(unused_send_message_event):
        with state.condition:
            state.condition.notify_all()
            return _possibly_finish_call(state, token)

    return send_message


class _Context(grpc.ServicerContext):
    _rpc_event: cygrpc.BaseEvent
    _state: _RPCState
    request_deserializer: Optional[DeserializingFunction]

    def __init__(
        self,
        rpc_event: cygrpc.BaseEvent,
        state: _RPCState,
        request_deserializer: Optional[DeserializingFunction],
    ):
        self._rpc_event = rpc_event
        self._state = state
        self._request_deserializer = request_deserializer

    def is_active(self) -> bool:
        with self._state.condition:
            return _is_rpc_state_active(self._state)

    def time_remaining(self) -> float:
        return max(self._rpc_event.call_details.deadline - time.time(), 0)

    def cancel(self) -> None:
        self._rpc_event.call.cancel()

    def add_callback(self, callback: NullaryCallbackType) -> bool:
        with self._state.condition:
            if self._state.callbacks is None:
                return False
            else:
                self._state.callbacks.append(callback)
                return True

    def disable_next_message_compression(self) -> None:
        with self._state.condition:
            self._state.disable_next_compression = True

    def invocation_metadata(self) -> Optional[MetadataType]:
        return self._rpc_event.invocation_metadata

    def peer(self) -> str:
        return _common.decode(self._rpc_event.call.peer())

    def peer_identities(self) -> Optional[Sequence[bytes]]:
        return cygrpc.peer_identities(self._rpc_event.call)

    def peer_identity_key(self) -> Optional[str]:
        id_key = cygrpc.peer_identity_key(self._rpc_event.call)
        return id_key if id_key is None else _common.decode(id_key)

    def auth_context(self) -> Mapping[str, Sequence[bytes]]:
        auth_context = cygrpc.auth_context(self._rpc_event.call)
        auth_context_dict = {} if auth_context is None else auth_context
        return {
            _common.decode(key): value
            for key, value in auth_context_dict.items()
        }

    def set_compression(self, compression: grpc.Compression) -> None:
        with self._state.condition:
            self._state.compression_algorithm = compression

    def send_initial_metadata(self, initial_metadata: MetadataType) -> None:
        with self._state.condition:
            if self._state.client is _CANCELLED:
                _raise_rpc_error(self._state)
            else:
                if self._state.initial_metadata_allowed:
                    operation = _get_initial_metadata_operation(
                        self._state, initial_metadata
                    )
                    self._rpc_event.call.start_server_batch(
                        (operation,), _send_initial_metadata(self._state)
                    )
                    self._state.initial_metadata_allowed = False
                    self._state.due.add(_SEND_INITIAL_METADATA_TOKEN)
                else:
                    raise ValueError("Initial metadata no longer allowed!")

    def set_trailing_metadata(self, trailing_metadata: MetadataType) -> None:
        with self._state.condition:
            self._state.trailing_metadata = trailing_metadata

    def trailing_metadata(self) -> Optional[MetadataType]:
        return self._state.trailing_metadata

    def abort(self, code: grpc.StatusCode, details: str) -> None:
        # treat OK like other invalid arguments: fail the RPC
        if code == grpc.StatusCode.OK:
            _LOGGER.error(
                "abort() called with StatusCode.OK; returning UNKNOWN"
            )
            code = grpc.StatusCode.UNKNOWN
            details = ""
        with self._state.condition:
            self._state.code = code
            self._state.details = _common.encode(details)
            self._state.aborted = True
            raise Exception()

    def abort_with_status(self, status: grpc.Status) -> None:
        self._state.trailing_metadata = status.trailing_metadata
        self.abort(status.code, status.details)

    def set_code(self, code: grpc.StatusCode) -> None:
        with self._state.condition:
            self._state.code = code

    def code(self) -> grpc.StatusCode:
        return self._state.code

    def set_details(self, details: str) -> None:
        with self._state.condition:
            self._state.details = _common.encode(details)

    def details(self) -> bytes:
        return self._state.details

    def _finalize_state(self) -> None:
        pass


class _RequestIterator(object):
    _state: _RPCState
    _call: cygrpc.Call
    _request_deserializer: Optional[DeserializingFunction]

    def __init__(
        self,
        state: _RPCState,
        call: cygrpc.Call,
        request_deserializer: Optional[DeserializingFunction],
    ):
        self._state = state
        self._call = call
        self._request_deserializer = request_deserializer

    def _raise_or_start_receive_message(self) -> None:
        if self._state.client is _CANCELLED:
            _raise_rpc_error(self._state)
        elif not _is_rpc_state_active(self._state):
            raise StopIteration()
        else:
            self._call.start_server_batch(
                (cygrpc.ReceiveMessageOperation(_EMPTY_FLAGS),),
                _receive_message(
                    self._state, self._call, self._request_deserializer
                ),
            )
            self._state.due.add(_RECEIVE_MESSAGE_TOKEN)

    def _look_for_request(self) -> Any:
        if self._state.client is _CANCELLED:
            _raise_rpc_error(self._state)
        elif (
            self._state.request is None
            and _RECEIVE_MESSAGE_TOKEN not in self._state.due
        ):
            raise StopIteration()
        else:
            request = self._state.request
            self._state.request = None
            return request

        raise AssertionError()  # should never run

    def _next(self) -> Any:
        with self._state.condition:
            self._raise_or_start_receive_message()
            while True:
                self._state.condition.wait()
                request = self._look_for_request()
                if request is not None:
                    return request

    def __iter__(self) -> _RequestIterator:
        return self

    def __next__(self) -> Any:
        return self._next()

    def next(self) -> Any:
        return self._next()


def _unary_request(
    rpc_event: cygrpc.BaseEvent,
    state: _RPCState,
    request_deserializer: Optional[DeserializingFunction],
) -> Callable[[], Any]:
    def unary_request():
        with state.condition:
            if not _is_rpc_state_active(state):
                return None
            else:
                rpc_event.call.start_server_batch(
                    (cygrpc.ReceiveMessageOperation(_EMPTY_FLAGS),),
                    _receive_message(
                        state, rpc_event.call, request_deserializer
                    ),
                )
                state.due.add(_RECEIVE_MESSAGE_TOKEN)
                while True:
                    state.condition.wait()
                    if state.request is None:
                        if state.client is _CLOSED:
                            details = '"{}" requires exactly one request message.'.format(
                                rpc_event.call_details.method
                            )
                            _abort(
                                state,
                                rpc_event.call,
                                cygrpc.StatusCode.unimplemented,
                                _common.encode(details),
                            )
                            return None
                        elif state.client is _CANCELLED:
                            return None
                    else:
                        request = state.request
                        state.request = None
                        return request

    return unary_request


def _call_behavior(
    rpc_event: cygrpc.BaseEvent,
    state: _RPCState,
    behavior: ArityAgnosticMethodHandler,
    argument: Any,
    request_deserializer: Optional[DeserializingFunction],
    send_response_callback: Optional[Callable[[ResponseType], None]] = None,
) -> Tuple[Union[ResponseType, Iterator[ResponseType]], bool]:
    from grpc import _create_servicer_context  # pytype: disable=pyi-error

    with _create_servicer_context(
        rpc_event, state, request_deserializer
    ) as context:
        try:
            response_or_iterator = None
            if send_response_callback is not None:
                response_or_iterator = behavior(
                    argument, context, send_response_callback
                )
            else:
                response_or_iterator = behavior(argument, context)
            return response_or_iterator, True
        except Exception as exception:  # pylint: disable=broad-except
            with state.condition:
                if state.aborted:
                    _abort(
                        state,
                        rpc_event.call,
                        cygrpc.StatusCode.unknown,
                        b"RPC Aborted",
                    )
                elif exception not in state.rpc_errors:
                    try:
                        details = "Exception calling application: {}".format(
                            exception
                        )
                    except Exception:  # pylint: disable=broad-except
                        details = (
                            "Calling application raised unprintable Exception!"
                        )
                        _LOGGER.exception(
                            traceback.format_exception(
                                type(exception),
                                exception,
                                exception.__traceback__,
                            )
                        )
                        traceback.print_exc()
                    _LOGGER.exception(details)
                    _abort(
                        state,
                        rpc_event.call,
                        cygrpc.StatusCode.unknown,
                        _common.encode(details),
                    )
            return None, False


def _take_response_from_response_iterator(
    rpc_event: cygrpc.BaseEvent,
    state: _RPCState,
    response_iterator: Iterator[ResponseType],
) -> Tuple[ResponseType, bool]:
    try:
        return next(response_iterator), True
    except StopIteration:
        return None, True
    except Exception as exception:  # pylint: disable=broad-except
        with state.condition:
            if state.aborted:
                _abort(
                    state,
                    rpc_event.call,
                    cygrpc.StatusCode.unknown,
                    b"RPC Aborted",
                )
            elif exception not in state.rpc_errors:
                details = "Exception iterating responses: {}".format(exception)
                _LOGGER.exception(details)
                _abort(
                    state,
                    rpc_event.call,
                    cygrpc.StatusCode.unknown,
                    _common.encode(details),
                )
        return None, False


def _serialize_response(
    rpc_event: cygrpc.BaseEvent,
    state: _RPCState,
    response: Any,
    response_serializer: Optional[SerializingFunction],
) -> Optional[bytes]:
    serialized_response = _common.serialize(response, response_serializer)
    if serialized_response is None:
        with state.condition:
            _abort(
                state,
                rpc_event.call,
                cygrpc.StatusCode.internal,
                b"Failed to serialize response!",
            )
        return None
    else:
        return serialized_response


def _get_send_message_op_flags_from_state(
    state: _RPCState,
) -> Union[int, cygrpc.WriteFlag]:
    if state.disable_next_compression:
        return cygrpc.WriteFlag.no_compress
    else:
        return _EMPTY_FLAGS


def _reset_per_message_state(state: _RPCState) -> None:
    with state.condition:
        state.disable_next_compression = False


def _send_response(
    rpc_event: cygrpc.BaseEvent, state: _RPCState, serialized_response: bytes
) -> bool:
    with state.condition:
        if not _is_rpc_state_active(state):
            return False
        else:
            if state.initial_metadata_allowed:
                operations = (
                    _get_initial_metadata_operation(state, None),
                    cygrpc.SendMessageOperation(
                        serialized_response,
                        _get_send_message_op_flags_from_state(state),
                    ),
                )
                state.initial_metadata_allowed = False
                token = _SEND_INITIAL_METADATA_AND_SEND_MESSAGE_TOKEN
            else:
                operations = (
                    cygrpc.SendMessageOperation(
                        serialized_response,
                        _get_send_message_op_flags_from_state(state),
                    ),
                )
                token = _SEND_MESSAGE_TOKEN
            rpc_event.call.start_server_batch(
                operations, _send_message(state, token)
            )
            state.due.add(token)
            _reset_per_message_state(state)
            while True:
                state.condition.wait()
                if token not in state.due:
                    return _is_rpc_state_active(state)


def _status(
    rpc_event: cygrpc.BaseEvent,
    state: _RPCState,
    serialized_response: Optional[bytes],
) -> None:
    with state.condition:
        if state.client is not _CANCELLED:
            code = _completion_code(state)
            details = _details(state)
            operations = [
                cygrpc.SendStatusFromServerOperation(
                    state.trailing_metadata, code, details, _EMPTY_FLAGS
                ),
            ]
            if state.initial_metadata_allowed:
                operations.append(_get_initial_metadata_operation(state, None))
            if serialized_response is not None:
                operations.append(
                    cygrpc.SendMessageOperation(
                        serialized_response,
                        _get_send_message_op_flags_from_state(state),
                    )
                )
            rpc_event.call.start_server_batch(
                operations,
                _send_status_from_server(state, _SEND_STATUS_FROM_SERVER_TOKEN),
            )
            state.statused = True
            _reset_per_message_state(state)
            state.due.add(_SEND_STATUS_FROM_SERVER_TOKEN)


def _unary_response_in_pool(
    rpc_event: cygrpc.BaseEvent,
    state: _RPCState,
    behavior: ArityAgnosticMethodHandler,
    argument_thunk: Callable[[], Any],
    request_deserializer: Optional[SerializingFunction],
    response_serializer: Optional[SerializingFunction],
) -> None:
    cygrpc.install_context_from_request_call_event(rpc_event)

    try:
        argument = argument_thunk()
        if argument is not None:
            response, proceed = _call_behavior(
                rpc_event, state, behavior, argument, request_deserializer
            )
            if proceed:
                serialized_response = _serialize_response(
                    rpc_event, state, response, response_serializer
                )
                if serialized_response is not None:
                    _status(rpc_event, state, serialized_response)
    except Exception:  # pylint: disable=broad-except
        traceback.print_exc()
    finally:
        cygrpc.uninstall_context()


def _stream_response_in_pool(
    rpc_event: cygrpc.BaseEvent,
    state: _RPCState,
    behavior: ArityAgnosticMethodHandler,
    argument_thunk: Callable[[], Any],
    request_deserializer: Optional[DeserializingFunction],
    response_serializer: Optional[SerializingFunction],
) -> None:
    cygrpc.install_context_from_request_call_event(rpc_event)

    def send_response(response: Any) -> None:
        if response is None:
            _status(rpc_event, state, None)
        else:
            serialized_response = _serialize_response(
                rpc_event, state, response, response_serializer
            )
            if serialized_response is not None:
                _send_response(rpc_event, state, serialized_response)

    try:
        argument = argument_thunk()
        if argument is not None:
            if (
                hasattr(behavior, "experimental_non_blocking")
                and behavior.experimental_non_blocking
            ):
                _call_behavior(
                    rpc_event,
                    state,
                    behavior,
                    argument,
                    request_deserializer,
                    send_response_callback=send_response,
                )
            else:
                response_iterator, proceed = _call_behavior(
                    rpc_event, state, behavior, argument, request_deserializer
                )
                if proceed:
                    _send_message_callback_to_blocking_iterator_adapter(
                        rpc_event, state, send_response, response_iterator
                    )
    except Exception:  # pylint: disable=broad-except
        traceback.print_exc()
    finally:
        cygrpc.uninstall_context()


def _is_rpc_state_active(state: _RPCState) -> bool:
    return state.client is not _CANCELLED and not state.statused


def _send_message_callback_to_blocking_iterator_adapter(
    rpc_event: cygrpc.BaseEvent,
    state: _RPCState,
    send_response_callback: Callable[[ResponseType], None],
    response_iterator: Iterator[ResponseType],
) -> None:
    while True:
        response, proceed = _take_response_from_response_iterator(
            rpc_event, state, response_iterator
        )
        if proceed:
            send_response_callback(response)
            if not _is_rpc_state_active(state):
                break
        else:
            break


def _select_thread_pool_for_behavior(
    behavior: ArityAgnosticMethodHandler,
    default_thread_pool: futures.ThreadPoolExecutor,
) -> futures.ThreadPoolExecutor:
    if hasattr(behavior, "experimental_thread_pool") and isinstance(
        behavior.experimental_thread_pool, futures.ThreadPoolExecutor
    ):
        return behavior.experimental_thread_pool
    else:
        return default_thread_pool


def _handle_unary_unary(
    rpc_event: cygrpc.BaseEvent,
    state: _RPCState,
    method_handler: grpc.RpcMethodHandler,
    default_thread_pool: futures.ThreadPoolExecutor,
) -> futures.Future:
    unary_request = _unary_request(
        rpc_event, state, method_handler.request_deserializer
    )
    thread_pool = _select_thread_pool_for_behavior(
        method_handler.unary_unary, default_thread_pool
    )
    return thread_pool.submit(
        state.context.run,
        _unary_response_in_pool,
        rpc_event,
        state,
        method_handler.unary_unary,
        unary_request,
        method_handler.request_deserializer,
        method_handler.response_serializer,
    )


def _handle_unary_stream(
    rpc_event: cygrpc.BaseEvent,
    state: _RPCState,
    method_handler: grpc.RpcMethodHandler,
    default_thread_pool: futures.ThreadPoolExecutor,
) -> futures.Future:
    unary_request = _unary_request(
        rpc_event, state, method_handler.request_deserializer
    )
    thread_pool = _select_thread_pool_for_behavior(
        method_handler.unary_stream, default_thread_pool
    )
    return thread_pool.submit(
        state.context.run,
        _stream_response_in_pool,
        rpc_event,
        state,
        method_handler.unary_stream,
        unary_request,
        method_handler.request_deserializer,
        method_handler.response_serializer,
    )


def _handle_stream_unary(
    rpc_event: cygrpc.BaseEvent,
    state: _RPCState,
    method_handler: grpc.RpcMethodHandler,
    default_thread_pool: futures.ThreadPoolExecutor,
) -> futures.Future:
    request_iterator = _RequestIterator(
        state, rpc_event.call, method_handler.request_deserializer
    )
    thread_pool = _select_thread_pool_for_behavior(
        method_handler.stream_unary, default_thread_pool
    )
    return thread_pool.submit(
        state.context.run,
        _unary_response_in_pool,
        rpc_event,
        state,
        method_handler.stream_unary,
        lambda: request_iterator,
        method_handler.request_deserializer,
        method_handler.response_serializer,
    )


def _handle_stream_stream(
    rpc_event: cygrpc.BaseEvent,
    state: _RPCState,
    method_handler: grpc.RpcMethodHandler,
    default_thread_pool: futures.ThreadPoolExecutor,
) -> futures.Future:
    request_iterator = _RequestIterator(
        state, rpc_event.call, method_handler.request_deserializer
    )
    thread_pool = _select_thread_pool_for_behavior(
        method_handler.stream_stream, default_thread_pool
    )
    return thread_pool.submit(
        state.context.run,
        _stream_response_in_pool,
        rpc_event,
        state,
        method_handler.stream_stream,
        lambda: request_iterator,
        method_handler.request_deserializer,
        method_handler.response_serializer,
    )


def _find_method_handler(
    rpc_event: cygrpc.BaseEvent,
    state: _RPCState,
    method_with_handler: _Method,
    interceptor_pipeline: Optional[_interceptor._ServicePipeline],
) -> Optional[grpc.RpcMethodHandler]:
    def query_handlers(
        handler_call_details: _HandlerCallDetails,
    ) -> Optional[grpc.RpcMethodHandler]:
        return method_with_handler.handler(handler_call_details)

    method_name = method_with_handler.name()
    if not method_name:
        method_name = _common.decode(rpc_event.call_details.method)

    handler_call_details = _HandlerCallDetails(
        method_name,
        rpc_event.invocation_metadata,
    )

    if interceptor_pipeline is not None:
        return state.context.run(
            interceptor_pipeline.execute, query_handlers, handler_call_details
        )
    else:
        return state.context.run(query_handlers, handler_call_details)


def _reject_rpc(
    rpc_event: cygrpc.BaseEvent,
    rpc_state: _RPCState,
    status: cygrpc.StatusCode,
    details: bytes,
):
    operations = (
        _get_initial_metadata_operation(rpc_state, None),
        cygrpc.ReceiveCloseOnServerOperation(_EMPTY_FLAGS),
        cygrpc.SendStatusFromServerOperation(
            None, status, details, _EMPTY_FLAGS
        ),
    )
    rpc_event.call.start_server_batch(
        operations,
        lambda ignored_event: (
            rpc_state,
            (),
        ),
    )


def _handle_with_method_handler(
    rpc_event: cygrpc.BaseEvent,
    state: _RPCState,
    method_handler: grpc.RpcMethodHandler,
    thread_pool: futures.ThreadPoolExecutor,
) -> futures.Future:
    with state.condition:
        rpc_event.call.start_server_batch(
            (cygrpc.ReceiveCloseOnServerOperation(_EMPTY_FLAGS),),
            _receive_close_on_server(state),
        )
        state.due.add(_RECEIVE_CLOSE_ON_SERVER_TOKEN)
        if method_handler.request_streaming:
            if method_handler.response_streaming:
                return _handle_stream_stream(
                    rpc_event, state, method_handler, thread_pool
                )
            else:
                return _handle_stream_unary(
                    rpc_event, state, method_handler, thread_pool
                )
        else:
            if method_handler.response_streaming:
                return _handle_unary_stream(
                    rpc_event, state, method_handler, thread_pool
                )
            else:
                return _handle_unary_unary(
                    rpc_event, state, method_handler, thread_pool
                )


def _handle_call(
    rpc_event: cygrpc.BaseEvent,
    method_with_handler: _Method,
    interceptor_pipeline: Optional[_interceptor._ServicePipeline],
    thread_pool: futures.ThreadPoolExecutor,
    concurrency_exceeded: bool,
) -> Tuple[Optional[_RPCState], Optional[futures.Future]]:
    """Handles RPC based on provided handlers.

      When receiving a call event from Core, registered method will have its
    name as tag, we pass the tag as registered_method_name to this method,
    then we can find the handler in registered_method_handlers based on
    the method name.

      For call event with unregistered method, the method name will be included
    in rpc_event.call_details.method and we need to query the generics handlers
    to find the actual handler.
    """
    if not rpc_event.success:
        return None, None
    if rpc_event.call_details.method or method_with_handler.name():
        rpc_state = _RPCState()
        try:
            method_handler = _find_method_handler(
                rpc_event,
                rpc_state,
                method_with_handler,
                interceptor_pipeline,
            )
        except Exception as exception:  # pylint: disable=broad-except
            details = "Exception servicing handler: {}".format(exception)
            _LOGGER.exception(details)
            _reject_rpc(
                rpc_event,
                rpc_state,
                cygrpc.StatusCode.unknown,
                b"Error in service handler!",
            )
            return rpc_state, None
        if method_handler is None:
            _reject_rpc(
                rpc_event,
                rpc_state,
                cygrpc.StatusCode.unimplemented,
                b"Method not found!",
            )
            return rpc_state, None
        elif concurrency_exceeded:
            _reject_rpc(
                rpc_event,
                rpc_state,
                cygrpc.StatusCode.resource_exhausted,
                b"Concurrent RPC limit exceeded!",
            )
            return rpc_state, None
        else:
            return (
                rpc_state,
                _handle_with_method_handler(
                    rpc_event, rpc_state, method_handler, thread_pool
                ),
            )
    else:
        return None, None


@enum.unique
class _ServerStage(enum.Enum):
    STOPPED = "stopped"
    STARTED = "started"
    GRACE = "grace"


class _ServerState(object):
    lock: threading.RLock
    completion_queue: cygrpc.CompletionQueue
    server: cygrpc.Server
    generic_handlers: List[grpc.GenericRpcHandler]
    registered_method_handlers: Dict[str, grpc.RpcMethodHandler]
    interceptor_pipeline: Optional[_interceptor._ServicePipeline]
    thread_pool: futures.ThreadPoolExecutor
    stage: _ServerStage
    termination_event: threading.Event
    shutdown_events: List[threading.Event]
    maximum_concurrent_rpcs: Optional[int]
    active_rpc_count: int
    rpc_states: Set[_RPCState]
    due: Set[str]
    server_deallocated: bool

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        completion_queue: cygrpc.CompletionQueue,
        server: cygrpc.Server,
        generic_handlers: Sequence[grpc.GenericRpcHandler],
        interceptor_pipeline: Optional[_interceptor._ServicePipeline],
        thread_pool: futures.ThreadPoolExecutor,
        maximum_concurrent_rpcs: Optional[int],
    ):
        self.lock = threading.RLock()
        self.completion_queue = completion_queue
        self.server = server
        self.generic_handlers = list(generic_handlers)
        self.interceptor_pipeline = interceptor_pipeline
        self.thread_pool = thread_pool
        self.stage = _ServerStage.STOPPED
        self.termination_event = threading.Event()
        self.shutdown_events = [self.termination_event]
        self.maximum_concurrent_rpcs = maximum_concurrent_rpcs
        self.active_rpc_count = 0
        self.registered_method_handlers = {}

        # TODO(https://github.com/grpc/grpc/issues/6597): eliminate these fields.
        self.rpc_states = set()
        self.due = set()

        # A "volatile" flag to interrupt the daemon serving thread
        self.server_deallocated = False


def _add_generic_handlers(
    state: _ServerState, generic_handlers: Iterable[grpc.GenericRpcHandler]
) -> None:
    with state.lock:
        state.generic_handlers.extend(generic_handlers)


def _add_registered_method_handlers(
    state: _ServerState, method_handlers: Dict[str, grpc.RpcMethodHandler]
) -> None:
    with state.lock:
        state.registered_method_handlers.update(method_handlers)


def _add_insecure_port(state: _ServerState, address: bytes) -> int:
    with state.lock:
        return state.server.add_http2_port(address)


def _add_secure_port(
    state: _ServerState,
    address: bytes,
    server_credentials: grpc.ServerCredentials,
) -> int:
    with state.lock:
        return state.server.add_http2_port(
            address, server_credentials._credentials
        )


def _request_call(state: _ServerState) -> None:
    state.server.request_call(
        state.completion_queue, state.completion_queue, _REQUEST_CALL_TAG
    )
    state.due.add(_REQUEST_CALL_TAG)


def _request_registered_call(state: _ServerState, method: str) -> None:
    registered_call_tag = method
    state.server.request_registered_call(
        state.completion_queue,
        state.completion_queue,
        method,
        registered_call_tag,
    )
    state.due.add(registered_call_tag)


# TODO(https://github.com/grpc/grpc/issues/6597): delete this function.
def _stop_serving(state: _ServerState) -> bool:
    if not state.rpc_states and not state.due:
        state.server.destroy()
        for shutdown_event in state.shutdown_events:
            shutdown_event.set()
        state.stage = _ServerStage.STOPPED
        return True
    else:
        return False


def _on_call_completed(state: _ServerState) -> None:
    with state.lock:
        state.active_rpc_count -= 1


# pylint: disable=too-many-branches
def _process_event_and_continue(
    state: _ServerState, event: cygrpc.BaseEvent
) -> bool:
    should_continue = True
    if event.tag is _SHUTDOWN_TAG:
        with state.lock:
            state.due.remove(_SHUTDOWN_TAG)
            if _stop_serving(state):
                should_continue = False
    elif (
        event.tag is _REQUEST_CALL_TAG
        or event.tag in state.registered_method_handlers.keys()
    ):
        registered_method_name = None
        if event.tag in state.registered_method_handlers.keys():
            registered_method_name = event.tag
            method_with_handler = _RegisteredMethod(
                registered_method_name,
                state.registered_method_handlers.get(
                    registered_method_name, None
                ),
            )
        else:
            method_with_handler = _GenericMethod(
                state.generic_handlers,
            )
        with state.lock:
            state.due.remove(event.tag)
            concurrency_exceeded = (
                state.maximum_concurrent_rpcs is not None
                and state.active_rpc_count >= state.maximum_concurrent_rpcs
            )
            rpc_state, rpc_future = _handle_call(
                event,
                method_with_handler,
                state.interceptor_pipeline,
                state.thread_pool,
                concurrency_exceeded,
            )
            if rpc_state is not None:
                state.rpc_states.add(rpc_state)
            if rpc_future is not None:
                state.active_rpc_count += 1
                rpc_future.add_done_callback(
                    lambda unused_future: _on_call_completed(state)
                )
            if state.stage is _ServerStage.STARTED:
                if (
                    registered_method_name
                    in state.registered_method_handlers.keys()
                ):
                    _request_registered_call(state, registered_method_name)
                else:
                    _request_call(state)
            elif _stop_serving(state):
                should_continue = False
    else:
        rpc_state, callbacks = event.tag(event)
        for callback in callbacks:
            try:
                callback()
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Exception calling callback!")
        if rpc_state is not None:
            with state.lock:
                state.rpc_states.remove(rpc_state)
                if _stop_serving(state):
                    should_continue = False
    return should_continue


def _serve(state: _ServerState) -> None:
    while True:
        timeout = time.time() + _DEALLOCATED_SERVER_CHECK_PERIOD_S
        event = state.completion_queue.poll(timeout)
        if state.server_deallocated:
            _begin_shutdown_once(state)
        if event.completion_type != cygrpc.CompletionType.queue_timeout:
            if not _process_event_and_continue(state, event):
                return
        # We want to force the deletion of the previous event
        # ~before~ we poll again; if the event has a reference
        # to a shutdown Call object, this can induce spinlock.
        event = None


def _begin_shutdown_once(state: _ServerState) -> None:
    with state.lock:
        if state.stage is _ServerStage.STARTED:
            state.server.shutdown(state.completion_queue, _SHUTDOWN_TAG)
            state.stage = _ServerStage.GRACE
            state.due.add(_SHUTDOWN_TAG)


def _stop(state: _ServerState, grace: Optional[float]) -> threading.Event:
    with state.lock:
        if state.stage is _ServerStage.STOPPED:
            shutdown_event = threading.Event()
            shutdown_event.set()
            return shutdown_event
        else:
            _begin_shutdown_once(state)
            shutdown_event = threading.Event()
            state.shutdown_events.append(shutdown_event)
            if grace is None:
                state.server.cancel_all_calls()
            else:

                def cancel_all_calls_after_grace():
                    shutdown_event.wait(timeout=grace)
                    with state.lock:
                        state.server.cancel_all_calls()

                thread = threading.Thread(target=cancel_all_calls_after_grace)
                thread.start()
                return shutdown_event
    shutdown_event.wait()
    return shutdown_event


def _start(state: _ServerState) -> None:
    with state.lock:
        if state.stage is not _ServerStage.STOPPED:
            raise ValueError("Cannot start already-started server!")
        state.server.start()
        state.stage = _ServerStage.STARTED
        # Request a call for each registered method so we can handle any of them.
        for method in state.registered_method_handlers.keys():
            _request_registered_call(state, method)
        # Also request a call for non-registered method.
        _request_call(state)
        thread = threading.Thread(target=_serve, args=(state,))
        thread.daemon = True
        thread.start()


def _validate_generic_rpc_handlers(
    generic_rpc_handlers: Iterable[grpc.GenericRpcHandler],
) -> None:
    for generic_rpc_handler in generic_rpc_handlers:
        service_attribute = getattr(generic_rpc_handler, "service", None)
        if service_attribute is None:
            raise AttributeError(
                '"{}" must conform to grpc.GenericRpcHandler type but does '
                'not have "service" method!'.format(generic_rpc_handler)
            )


def _augment_options(
    base_options: Sequence[ChannelArgumentType],
    compression: Optional[grpc.Compression],
    xds: bool,
) -> Sequence[ChannelArgumentType]:
    compression_option = _compression.create_channel_option(compression)
    maybe_server_call_tracer_factory_option = (
        _observability.create_server_call_tracer_factory_option(xds)
    )
    return (
        tuple(base_options)
        + compression_option
        + maybe_server_call_tracer_factory_option
    )


class _Server(grpc.Server):
    _state: _ServerState

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        thread_pool: futures.ThreadPoolExecutor,
        generic_handlers: Sequence[grpc.GenericRpcHandler],
        interceptors: Sequence[grpc.ServerInterceptor],
        options: Sequence[ChannelArgumentType],
        maximum_concurrent_rpcs: Optional[int],
        compression: Optional[grpc.Compression],
        xds: bool,
    ):
        completion_queue = cygrpc.CompletionQueue()
        server = cygrpc.Server(_augment_options(options, compression, xds), xds)
        server.register_completion_queue(completion_queue)
        self._state = _ServerState(
            completion_queue,
            server,
            generic_handlers,
            _interceptor.service_pipeline(interceptors),
            thread_pool,
            maximum_concurrent_rpcs,
        )
        self._cy_server = server

    def add_generic_rpc_handlers(
        self, generic_rpc_handlers: Iterable[grpc.GenericRpcHandler]
    ) -> None:
        _validate_generic_rpc_handlers(generic_rpc_handlers)
        _add_generic_handlers(self._state, generic_rpc_handlers)

    def add_registered_method_handlers(
        self,
        service_name: str,
        method_handlers: Dict[str, grpc.RpcMethodHandler],
    ) -> None:
        # Can't register method once server started.
        with self._state.lock:
            if self._state.stage is _ServerStage.STARTED:
                return

        # TODO(xuanwn): We should validate method_handlers first.
        method_to_handlers = {
            _common.fully_qualified_method(service_name, method): method_handler
            for method, method_handler in method_handlers.items()
        }
        for fully_qualified_method in method_to_handlers.keys():
            self._cy_server.register_method(fully_qualified_method)
        _add_registered_method_handlers(self._state, method_to_handlers)

    def add_insecure_port(self, address: str) -> int:
        return _common.validate_port_binding_result(
            address, _add_insecure_port(self._state, _common.encode(address))
        )

    def add_secure_port(
        self, address: str, server_credentials: grpc.ServerCredentials
    ) -> int:
        return _common.validate_port_binding_result(
            address,
            _add_secure_port(
                self._state, _common.encode(address), server_credentials
            ),
        )

    def start(self) -> None:
        _start(self._state)

    def wait_for_termination(self, timeout: Optional[float] = None) -> bool:
        # NOTE(https://bugs.python.org/issue35935)
        # Remove this workaround once threading.Event.wait() is working with
        # CTRL+C across platforms.
        return _common.wait(
            self._state.termination_event.wait,
            self._state.termination_event.is_set,
            timeout=timeout,
        )

    def stop(self, grace: Optional[float]) -> threading.Event:
        return _stop(self._state, grace)

    def __del__(self):
        if hasattr(self, "_state"):
            # We can not grab a lock in __del__(), so set a flag to signal the
            # serving daemon thread (if it exists) to initiate shutdown.
            self._state.server_deallocated = True


def create_server(
    thread_pool: futures.ThreadPoolExecutor,
    generic_rpc_handlers: Sequence[grpc.GenericRpcHandler],
    interceptors: Sequence[grpc.ServerInterceptor],
    options: Sequence[ChannelArgumentType],
    maximum_concurrent_rpcs: Optional[int],
    compression: Optional[grpc.Compression],
    xds: bool,
) -> _Server:
    _validate_generic_rpc_handlers(generic_rpc_handlers)
    return _Server(
        thread_pool,
        generic_rpc_handlers,
        interceptors,
        options,
        maximum_concurrent_rpcs,
        compression,
        xds,
    )

# === NexusCore/openenv\Lib\site-packages\nltk\data.py ===
# Natural Language Toolkit: Utility functions
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# Author: ekaf (Restricting and switching pickles)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Functions to find and load NLTK resource files, such as corpora,
grammars, and saved processing objects.  Resource files are identified
using URLs, such as ``nltk:corpora/abc/rural.txt`` or
``https://raw.githubusercontent.com/nltk/nltk/develop/nltk/test/toy.cfg``.
The following URL protocols are supported:

  - ``file:path``: Specifies the file whose path is *path*.
    Both relative and absolute paths may be used.

  - ``https://host/path``: Specifies the file stored on the web
    server *host* at path *path*.

  - ``nltk:path``: Specifies the file stored in the NLTK data
    package at *path*.  NLTK will search for these files in the
    directories specified by ``nltk.data.path``.

If no protocol is specified, then the default protocol ``nltk:`` will
be used.

This module provides to functions that can be used to access a
resource file, given its URL: ``load()`` loads a given resource, and
adds it to a resource cache; and ``retrieve()`` copies a given resource
to a local file.
"""

import codecs
import functools
import os
import pickle
import re
import sys
import textwrap
import zipfile
from abc import ABCMeta, abstractmethod
from gzip import WRITE as GZ_WRITE
from gzip import GzipFile
from io import BytesIO, TextIOWrapper
from urllib.request import url2pathname, urlopen

try:
    from zlib import Z_SYNC_FLUSH as FLUSH
except ImportError:
    from zlib import Z_FINISH as FLUSH

from nltk import grammar, sem
from nltk.internals import deprecated

textwrap_indent = functools.partial(textwrap.indent, prefix="  ")

######################################################################
# Search Path
######################################################################

path = []
"""A list of directories where the NLTK data package might reside.
   These directories will be checked in order when looking for a
   resource in the data package.  Note that this allows users to
   substitute in their own versions of resources, if they have them
   (e.g., in their home directory under ~/nltk_data)."""

# User-specified locations:
_paths_from_env = os.environ.get("NLTK_DATA", "").split(os.pathsep)
path += [d for d in _paths_from_env if d]
if "APPENGINE_RUNTIME" not in os.environ and os.path.expanduser("~/") != "~/":
    path.append(os.path.expanduser("~/nltk_data"))

if sys.platform.startswith("win"):
    # Common locations on Windows:
    path += [
        os.path.join(sys.prefix, "nltk_data"),
        os.path.join(sys.prefix, "share", "nltk_data"),
        os.path.join(sys.prefix, "lib", "nltk_data"),
        os.path.join(os.environ.get("APPDATA", "C:\\"), "nltk_data"),
        r"C:\nltk_data",
        r"D:\nltk_data",
        r"E:\nltk_data",
    ]
else:
    # Common locations on UNIX & OS X:
    path += [
        os.path.join(sys.prefix, "nltk_data"),
        os.path.join(sys.prefix, "share", "nltk_data"),
        os.path.join(sys.prefix, "lib", "nltk_data"),
        "/usr/share/nltk_data",
        "/usr/local/share/nltk_data",
        "/usr/lib/nltk_data",
        "/usr/local/lib/nltk_data",
    ]


######################################################################
# Util Functions
######################################################################


def gzip_open_unicode(
    filename,
    mode="rb",
    compresslevel=9,
    encoding="utf-8",
    fileobj=None,
    errors=None,
    newline=None,
):
    if fileobj is None:
        fileobj = GzipFile(filename, mode, compresslevel, fileobj)
    return TextIOWrapper(fileobj, encoding, errors, newline)


def split_resource_url(resource_url):
    """
    Splits a resource url into "<protocol>:<path>".

    >>> windows = sys.platform.startswith('win')
    >>> split_resource_url('nltk:home/nltk')
    ('nltk', 'home/nltk')
    >>> split_resource_url('nltk:/home/nltk')
    ('nltk', '/home/nltk')
    >>> split_resource_url('file:/home/nltk')
    ('file', '/home/nltk')
    >>> split_resource_url('file:///home/nltk')
    ('file', '/home/nltk')
    >>> split_resource_url('file:///C:/home/nltk')
    ('file', '/C:/home/nltk')
    """
    protocol, path_ = resource_url.split(":", 1)
    if protocol == "nltk":
        pass
    elif protocol == "file":
        if path_.startswith("/"):
            path_ = "/" + path_.lstrip("/")
    else:
        path_ = re.sub(r"^/{0,2}", "", path_)
    return protocol, path_


def normalize_resource_url(resource_url):
    r"""
    Normalizes a resource url

    >>> windows = sys.platform.startswith('win')
    >>> os.path.normpath(split_resource_url(normalize_resource_url('file:grammar.fcfg'))[1]) == \
    ... ('\\' if windows else '') + os.path.abspath(os.path.join(os.curdir, 'grammar.fcfg'))
    True
    >>> not windows or normalize_resource_url('file:C:/dir/file') == 'file:///C:/dir/file'
    True
    >>> not windows or normalize_resource_url('file:C:\\dir\\file') == 'file:///C:/dir/file'
    True
    >>> not windows or normalize_resource_url('file:C:\\dir/file') == 'file:///C:/dir/file'
    True
    >>> not windows or normalize_resource_url('file://C:/dir/file') == 'file:///C:/dir/file'
    True
    >>> not windows or normalize_resource_url('file:////C:/dir/file') == 'file:///C:/dir/file'
    True
    >>> not windows or normalize_resource_url('nltk:C:/dir/file') == 'file:///C:/dir/file'
    True
    >>> not windows or normalize_resource_url('nltk:C:\\dir\\file') == 'file:///C:/dir/file'
    True
    >>> windows or normalize_resource_url('file:/dir/file/toy.cfg') == 'file:///dir/file/toy.cfg'
    True
    >>> normalize_resource_url('nltk:home/nltk')
    'nltk:home/nltk'
    >>> windows or normalize_resource_url('nltk:/home/nltk') == 'file:///home/nltk'
    True
    >>> normalize_resource_url('https://example.com/dir/file')
    'https://example.com/dir/file'
    >>> normalize_resource_url('dir/file')
    'nltk:dir/file'
    """
    try:
        protocol, name = split_resource_url(resource_url)
    except ValueError:
        # the resource url has no protocol, use the nltk protocol by default
        protocol = "nltk"
        name = resource_url
    # use file protocol if the path is an absolute path
    if protocol == "nltk" and os.path.isabs(name):
        protocol = "file://"
        name = normalize_resource_name(name, False, None)
    elif protocol == "file":
        protocol = "file://"
        # name is absolute
        name = normalize_resource_name(name, False, None)
    elif protocol == "nltk":
        protocol = "nltk:"
        name = normalize_resource_name(name, True)
    else:
        # handled by urllib
        protocol += "://"
    return "".join([protocol, name])


def normalize_resource_name(resource_name, allow_relative=True, relative_path=None):
    """
    :type resource_name: str or unicode
    :param resource_name: The name of the resource to search for.
        Resource names are posix-style relative path names, such as
        ``corpora/brown``.  Directory names will automatically
        be converted to a platform-appropriate path separator.
        Directory trailing slashes are preserved

    >>> windows = sys.platform.startswith('win')
    >>> normalize_resource_name('.', True)
    './'
    >>> normalize_resource_name('./', True)
    './'
    >>> windows or normalize_resource_name('dir/file', False, '/') == '/dir/file'
    True
    >>> not windows or normalize_resource_name('C:/file', False, '/') == '/C:/file'
    True
    >>> windows or normalize_resource_name('/dir/file', False, '/') == '/dir/file'
    True
    >>> windows or normalize_resource_name('../dir/file', False, '/') == '/dir/file'
    True
    >>> not windows or normalize_resource_name('/dir/file', True, '/') == 'dir/file'
    True
    >>> windows or normalize_resource_name('/dir/file', True, '/') == '/dir/file'
    True
    """
    is_dir = bool(re.search(r"[\\/.]$", resource_name)) or resource_name.endswith(
        os.path.sep
    )
    if sys.platform.startswith("win"):
        resource_name = resource_name.lstrip("/")
    else:
        resource_name = re.sub(r"^/+", "/", resource_name)
    if allow_relative:
        resource_name = os.path.normpath(resource_name)
    else:
        if relative_path is None:
            relative_path = os.curdir
        resource_name = os.path.abspath(os.path.join(relative_path, resource_name))
    resource_name = resource_name.replace("\\", "/").replace(os.path.sep, "/")
    if sys.platform.startswith("win") and os.path.isabs(resource_name):
        resource_name = "/" + resource_name
    if is_dir and not resource_name.endswith("/"):
        resource_name += "/"
    return resource_name


######################################################################
# Path Pointers
######################################################################


class PathPointer(metaclass=ABCMeta):
    """
    An abstract base class for 'path pointers,' used by NLTK's data
    package to identify specific paths.  Two subclasses exist:
    ``FileSystemPathPointer`` identifies a file that can be accessed
    directly via a given absolute path.  ``ZipFilePathPointer``
    identifies a file contained within a zipfile, that can be accessed
    by reading that zipfile.
    """

    @abstractmethod
    def open(self, encoding=None):
        """
        Return a seekable read-only stream that can be used to read
        the contents of the file identified by this path pointer.

        :raise IOError: If the path specified by this pointer does
            not contain a readable file.
        """

    @abstractmethod
    def file_size(self):
        """
        Return the size of the file pointed to by this path pointer,
        in bytes.

        :raise IOError: If the path specified by this pointer does
            not contain a readable file.
        """

    @abstractmethod
    def join(self, fileid):
        """
        Return a new path pointer formed by starting at the path
        identified by this pointer, and then following the relative
        path given by ``fileid``.  The path components of ``fileid``
        should be separated by forward slashes, regardless of
        the underlying file system's path separator character.
        """


class FileSystemPathPointer(PathPointer, str):
    """
    A path pointer that identifies a file which can be accessed
    directly via a given absolute path.
    """

    def __init__(self, _path):
        """
        Create a new path pointer for the given absolute path.

        :raise IOError: If the given path does not exist.
        """

        _path = os.path.abspath(_path)
        if not os.path.exists(_path):
            raise OSError("No such file or directory: %r" % _path)
        self._path = _path

        # There's no need to call str.__init__(), since it's a no-op;
        # str does all of its setup work in __new__.

    @property
    def path(self):
        """The absolute path identified by this path pointer."""
        return self._path

    def open(self, encoding=None):
        stream = open(self._path, "rb")
        if encoding is not None:
            stream = SeekableUnicodeStreamReader(stream, encoding)
        return stream

    def file_size(self):
        return os.stat(self._path).st_size

    def join(self, fileid):
        _path = os.path.join(self._path, fileid)
        return FileSystemPathPointer(_path)

    def __repr__(self):
        return "FileSystemPathPointer(%r)" % self._path

    def __str__(self):
        return self._path


@deprecated("Use gzip.GzipFile instead as it also uses a buffer.")
class BufferedGzipFile(GzipFile):
    """A ``GzipFile`` subclass for compatibility with older nltk releases.

    Use ``GzipFile`` directly as it also buffers in all supported
    Python versions.
    """

    def __init__(
        self, filename=None, mode=None, compresslevel=9, fileobj=None, **kwargs
    ):
        """Return a buffered gzip file object."""
        GzipFile.__init__(self, filename, mode, compresslevel, fileobj)

    def write(self, data):
        # This is identical to GzipFile.write but does not return
        # the bytes written to retain compatibility.
        super().write(data)


class GzipFileSystemPathPointer(FileSystemPathPointer):
    """
    A subclass of ``FileSystemPathPointer`` that identifies a gzip-compressed
    file located at a given absolute path.  ``GzipFileSystemPathPointer`` is
    appropriate for loading large gzip-compressed pickle objects efficiently.
    """

    def open(self, encoding=None):
        stream = GzipFile(self._path, "rb")
        if encoding:
            stream = SeekableUnicodeStreamReader(stream, encoding)
        return stream


class ZipFilePathPointer(PathPointer):
    """
    A path pointer that identifies a file contained within a zipfile,
    which can be accessed by reading that zipfile.
    """

    def __init__(self, zipfile, entry=""):
        """
        Create a new path pointer pointing at the specified entry
        in the given zipfile.

        :raise IOError: If the given zipfile does not exist, or if it
        does not contain the specified entry.
        """
        if isinstance(zipfile, str):
            zipfile = OpenOnDemandZipFile(os.path.abspath(zipfile))

        # Check that the entry exists:
        if entry:
            # Normalize the entry string, it should be relative:
            entry = normalize_resource_name(entry, True, "/").lstrip("/")

            try:
                zipfile.getinfo(entry)
            except Exception as e:
                # Sometimes directories aren't explicitly listed in
                # the zip file.  So if `entry` is a directory name,
                # then check if the zipfile contains any files that
                # are under the given directory.
                if entry.endswith("/") and [
                    n for n in zipfile.namelist() if n.startswith(entry)
                ]:
                    pass  # zipfile contains a file in that directory.
                else:
                    # Otherwise, complain.
                    raise OSError(
                        f"Zipfile {zipfile.filename!r} does not contain {entry!r}"
                    ) from e
        self._zipfile = zipfile
        self._entry = entry

    @property
    def zipfile(self):
        """
        The zipfile.ZipFile object used to access the zip file
        containing the entry identified by this path pointer.
        """
        return self._zipfile

    @property
    def entry(self):
        """
        The name of the file within zipfile that this path
        pointer points to.
        """
        return self._entry

    def open(self, encoding=None):
        data = self._zipfile.read(self._entry)
        stream = BytesIO(data)
        if self._entry.endswith(".gz"):
            stream = GzipFile(self._entry, fileobj=stream)
        elif encoding is not None:
            stream = SeekableUnicodeStreamReader(stream, encoding)
        return stream

    def file_size(self):
        return self._zipfile.getinfo(self._entry).file_size

    def join(self, fileid):
        entry = f"{self._entry}/{fileid}"
        return ZipFilePathPointer(self._zipfile, entry)

    def __repr__(self):
        return f"ZipFilePathPointer({self._zipfile.filename!r}, {self._entry!r})"

    def __str__(self):
        return os.path.normpath(os.path.join(self._zipfile.filename, self._entry))


######################################################################
# Access Functions
######################################################################

# Don't use a weak dictionary, because in the common case this
# causes a lot more reloading that necessary.
_resource_cache = {}
"""A dictionary used to cache resources so that they won't
   need to be loaded more than once."""


def find(resource_name, paths=None):
    """
    Find the given resource by searching through the directories and
    zip files in paths, where a None or empty string specifies an absolute path.
    Returns a corresponding path name.  If the given resource is not
    found, raise a ``LookupError``, whose message gives a pointer to
    the installation instructions for the NLTK downloader.

    Zip File Handling:

      - If ``resource_name`` contains a component with a ``.zip``
        extension, then it is assumed to be a zipfile; and the
        remaining path components are used to look inside the zipfile.

      - If any element of ``nltk.data.path`` has a ``.zip`` extension,
        then it is assumed to be a zipfile.

      - If a given resource name that does not contain any zipfile
        component is not found initially, then ``find()`` will make a
        second attempt to find that resource, by replacing each
        component *p* in the path with *p.zip/p*.  For example, this
        allows ``find()`` to map the resource name
        ``corpora/chat80/cities.pl`` to a zip file path pointer to
        ``corpora/chat80.zip/chat80/cities.pl``.

      - When using ``find()`` to locate a directory contained in a
        zipfile, the resource name must end with the forward slash
        character.  Otherwise, ``find()`` will not locate the
        directory.

    :type resource_name: str or unicode
    :param resource_name: The name of the resource to search for.
        Resource names are posix-style relative path names, such as
        ``corpora/brown``.  Directory names will be
        automatically converted to a platform-appropriate path separator.
    :rtype: str
    """
    resource_name = normalize_resource_name(resource_name, True)

    # Resolve default paths at runtime in-case the user overrides
    # nltk.data.path
    if paths is None:
        paths = path

    # Check if the resource name includes a zipfile name
    m = re.match(r"(.*\.zip)/?(.*)$|", resource_name)
    zipfile, zipentry = m.groups()

    # Check each item in our path
    for path_ in paths:
        # Is the path item a zipfile?
        if path_ and (os.path.isfile(path_) and path_.endswith(".zip")):
            try:
                return ZipFilePathPointer(path_, resource_name)
            except OSError:
                # resource not in zipfile
                continue

        # Is the path item a directory or is resource_name an absolute path?
        elif not path_ or os.path.isdir(path_):
            if zipfile is None:
                p = os.path.join(path_, url2pathname(resource_name))
                if os.path.exists(p):
                    if p.endswith(".gz"):
                        return GzipFileSystemPathPointer(p)
                    else:
                        return FileSystemPathPointer(p)
            else:
                p = os.path.join(path_, url2pathname(zipfile))
                if os.path.exists(p):
                    try:
                        return ZipFilePathPointer(p, zipentry)
                    except OSError:
                        # resource not in zipfile
                        continue

    # Fallback: if the path doesn't include a zip file, then try
    # again, assuming that one of the path components is inside a
    # zipfile of the same name.
    if zipfile is None:
        pieces = resource_name.split("/")
        for i in range(len(pieces)):
            modified_name = "/".join(pieces[:i] + [pieces[i] + ".zip"] + pieces[i:])
            try:
                return find(modified_name, paths)
            except LookupError:
                pass

    # Identify the package (i.e. the .zip file) to download.
    resource_zipname = resource_name.split("/")[1]
    if resource_zipname.endswith(".zip"):
        resource_zipname = resource_zipname.rpartition(".")[0]
    # Display a friendly error message if the resource wasn't found:
    msg = str(
        "Resource \33[93m{resource}\033[0m not found.\n"
        "Please use the NLTK Downloader to obtain the resource:\n\n"
        "\33[31m"  # To display red text in terminal.
        ">>> import nltk\n"
        ">>> nltk.download('{resource}')\n"
        "\033[0m"
    ).format(resource=resource_zipname)
    msg = textwrap_indent(msg)

    msg += "\n  For more information see: https://www.nltk.org/data.html\n"

    msg += "\n  Attempted to load \33[93m{resource_name}\033[0m\n".format(
        resource_name=resource_name
    )

    msg += "\n  Searched in:" + "".join("\n    - %r" % d for d in paths)
    sep = "*" * 70
    resource_not_found = f"\n{sep}\n{msg}\n{sep}\n"
    raise LookupError(resource_not_found)


def retrieve(resource_url, filename=None, verbose=True):
    """
    Copy the given resource to a local file.  If no filename is
    specified, then use the URL's filename.  If there is already a
    file named ``filename``, then raise a ``ValueError``.

    :type resource_url: str
    :param resource_url: A URL specifying where the resource should be
        loaded from.  The default protocol is "nltk:", which searches
        for the file in the the NLTK data package.
    """
    resource_url = normalize_resource_url(resource_url)
    if filename is None:
        if resource_url.startswith("file:"):
            filename = os.path.split(resource_url)[-1]
        else:
            filename = re.sub(r"(^\w+:)?.*/", "", resource_url)
    if os.path.exists(filename):
        filename = os.path.abspath(filename)
        raise ValueError("File %r already exists!" % filename)

    if verbose:
        print(f"Retrieving {resource_url!r}, saving to {filename!r}")

    # Open the input & output streams.
    infile = _open(resource_url)

    # Copy infile -> outfile, using 64k blocks.
    with open(filename, "wb") as outfile:
        while True:
            s = infile.read(1024 * 64)  # 64k blocks.
            outfile.write(s)
            if not s:
                break

    infile.close()


#: A dictionary describing the formats that are supported by NLTK's
#: load() method.  Keys are format names, and values are format
#: descriptions.
FORMATS = {
    "pickle": "A serialized python object, stored using the pickle module.",
    "json": "A serialized python object, stored using the json module.",
    "yaml": "A serialized python object, stored using the yaml module.",
    "cfg": "A context free grammar.",
    "pcfg": "A probabilistic CFG.",
    "fcfg": "A feature CFG.",
    "fol": "A list of first order logic expressions, parsed with "
    "nltk.sem.logic.Expression.fromstring.",
    "logic": "A list of first order logic expressions, parsed with "
    "nltk.sem.logic.LogicParser.  Requires an additional logic_parser "
    "parameter",
    "val": "A semantic valuation, parsed by nltk.sem.Valuation.fromstring.",
    "raw": "The raw (byte string) contents of a file.",
    "text": "The raw (unicode string) contents of a file. ",
}

#: A dictionary mapping from file extensions to format names, used
#: by load() when format="auto" to decide the format for a
#: given resource url.
AUTO_FORMATS = {
    "pickle": "pickle",
    "json": "json",
    "yaml": "yaml",
    "cfg": "cfg",
    "pcfg": "pcfg",
    "fcfg": "fcfg",
    "fol": "fol",
    "logic": "logic",
    "val": "val",
    "txt": "text",
    "text": "text",
}


def restricted_pickle_load(string):
    """
    Prevents any class or function from loading.
    """
    from nltk.app.wordnet_app import RestrictedUnpickler

    return RestrictedUnpickler(BytesIO(string)).load()


def switch_punkt(lang="english"):
    """
    Return a pickle-free Punkt tokenizer instead of loading a pickle.

    >>> import nltk
    >>> tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    >>> print(tokenizer.tokenize("Hello! How are you?"))
    ['Hello!', 'How are you?']
    """
    from nltk.tokenize import PunktTokenizer as tok

    return tok(lang)


def switch_chunker(fmt="multiclass"):
    """
    Return a pickle-free Named Entity Chunker instead of loading a pickle.

    >>> import nltk
    >>> from nltk.corpus import treebank
    >>> from pprint import pprint
    >>> chunker = nltk.data.load('chunkers/maxent_ne_chunker/PY3/english_ace_multiclass.pickle')
    >>> pprint(chunker.parse(treebank.tagged_sents()[2][8:14])) # doctest: +NORMALIZE_WHITESPACE
    Tree('S', [('chairman', 'NN'), ('of', 'IN'), Tree('ORGANIZATION', [('Consolidated', 'NNP'), ('Gold', 'NNP'), ('Fields', 'NNP')]), ('PLC', 'NNP')])

    """
    from nltk.chunk import ne_chunker

    return ne_chunker(fmt)


def switch_t_tagger():
    """
    Return a pickle-free Treebank Pos Tagger instead of loading a pickle.

    >>> import nltk
    >>> from nltk.tokenize import word_tokenize
    >>> tagger = nltk.data.load('taggers/maxent_treebank_pos_tagger/PY3/english.pickle')
    >>> print(tagger.tag(word_tokenize("Hello, how are you?")))
    [('Hello', 'NNP'), (',', ','), ('how', 'WRB'), ('are', 'VBP'), ('you', 'PRP'), ('?', '.')]

    """
    from nltk.classify.maxent import maxent_pos_tagger

    return maxent_pos_tagger()


def switch_p_tagger(lang):
    """
    Return a pickle-free Averaged Perceptron Tagger instead of loading a pickle.

    >>> import nltk
    >>> from nltk.tokenize import word_tokenize
    >>> tagger = nltk.data.load('taggers/averaged_perceptron_tagger/averaged_perceptron_tagger.pickle')
    >>> print(tagger.tag(word_tokenize("Hello, how are you?")))
    [('Hello', 'NNP'), (',', ','), ('how', 'WRB'), ('are', 'VBP'), ('you', 'PRP'), ('?', '.')]

    """
    from nltk.tag import _get_tagger

    if lang == "ru":
        lang = "rus"
    else:
        lang = None
    return _get_tagger(lang)


def load(
    resource_url,
    format="auto",
    cache=True,
    verbose=False,
    logic_parser=None,
    fstruct_reader=None,
    encoding=None,
):
    """
    Load a given resource from the NLTK data package.  The following
    resource formats are currently supported:

      - ``pickle``
      - ``json``
      - ``yaml``
      - ``cfg`` (context free grammars)
      - ``pcfg`` (probabilistic CFGs)
      - ``fcfg`` (feature-based CFGs)
      - ``fol`` (formulas of First Order Logic)
      - ``logic`` (Logical formulas to be parsed by the given logic_parser)
      - ``val`` (valuation of First Order Logic model)
      - ``text`` (the file contents as a unicode string)
      - ``raw`` (the raw file contents as a byte string)

    If no format is specified, ``load()`` will attempt to determine a
    format based on the resource name's file extension.  If that
    fails, ``load()`` will raise a ``ValueError`` exception.

    For all text formats (everything except ``pickle``, ``json``, ``yaml`` and ``raw``),
    it tries to decode the raw contents using UTF-8, and if that doesn't
    work, it tries with ISO-8859-1 (Latin-1), unless the ``encoding``
    is specified.

    :type resource_url: str
    :param resource_url: A URL specifying where the resource should be
        loaded from.  The default protocol is "nltk:", which searches
        for the file in the the NLTK data package.
    :type cache: bool
    :param cache: If true, add this resource to a cache.  If load()
        finds a resource in its cache, then it will return it from the
        cache rather than loading it.
    :type verbose: bool
    :param verbose: If true, print a message when loading a resource.
        Messages are not displayed when a resource is retrieved from
        the cache.
    :type logic_parser: LogicParser
    :param logic_parser: The parser that will be used to parse logical
        expressions.
    :type fstruct_reader: FeatStructReader
    :param fstruct_reader: The parser that will be used to parse the
        feature structure of an fcfg.
    :type encoding: str
    :param encoding: the encoding of the input; only used for text formats.
    """
    resource_url = normalize_resource_url(resource_url)

    # Determine the format of the resource.
    if format == "auto":
        resource_url_parts = resource_url.split(".")
        ext = resource_url_parts[-1]
        if ext == "gz":
            ext = resource_url_parts[-2]
        format = AUTO_FORMATS.get(ext)
        if format is None:
            raise ValueError(
                "Could not determine format for %s based "
                'on its file\nextension; use the "format" '
                "argument to specify the format explicitly." % resource_url
            )

    if format not in FORMATS:
        raise ValueError(f"Unknown format type: {format}!")

    # If we've cached the resource, then just return it.
    if cache:
        resource_val = _resource_cache.get((resource_url, format))
        if resource_val is not None:
            if verbose:
                print(f"<<Using cached copy of {resource_url}>>")
            return resource_val

    protocol, path_ = split_resource_url(resource_url)

    if path_[-7:] == ".pickle":
        if verbose:
            print(f"<<Loading pickle-free alternative to {resource_url}>>")
        fil = os.path.split(path_[:-7])[-1]
        if path_.startswith("tokenizers/punkt"):
            return switch_punkt(fil)
        elif path_.startswith("chunkers/maxent_ne_chunker"):
            return switch_chunker(fil.split("_")[-1])
        elif path_.startswith("taggers/maxent_treebank_pos_tagger"):
            return switch_t_tagger()
        elif path_.startswith("taggers/averaged_perceptron_tagger"):
            return switch_p_tagger(fil.split("_")[-1])

    # Let the user know what's going on.
    if verbose:
        print(f"<<Loading {resource_url}>>")

    # Load the resource.
    opened_resource = _open(resource_url)

    if format == "raw":
        resource_val = opened_resource.read()
    elif format == "pickle":
        resource_val = restricted_pickle_load(opened_resource.read())
    elif format == "json":
        import json

        from nltk.jsontags import json_tags

        resource_val = json.load(opened_resource)
        tag = None
        if len(resource_val) != 1:
            tag = next(resource_val.keys())
        if tag not in json_tags:
            raise ValueError("Unknown json tag.")
    elif format == "yaml":
        import yaml

        resource_val = yaml.safe_load(opened_resource)
    else:
        # The resource is a text format.
        binary_data = opened_resource.read()
        if encoding is not None:
            string_data = binary_data.decode(encoding)
        else:
            try:
                string_data = binary_data.decode("utf-8")
            except UnicodeDecodeError:
                string_data = binary_data.decode("latin-1")
        if format == "text":
            resource_val = string_data
        elif format == "cfg":
            resource_val = grammar.CFG.fromstring(string_data, encoding=encoding)
        elif format == "pcfg":
            resource_val = grammar.PCFG.fromstring(string_data, encoding=encoding)
        elif format == "fcfg":
            resource_val = grammar.FeatureGrammar.fromstring(
                string_data,
                logic_parser=logic_parser,
                fstruct_reader=fstruct_reader,
                encoding=encoding,
            )
        elif format == "fol":
            resource_val = sem.read_logic(
                string_data,
                logic_parser=sem.logic.LogicParser(),
                encoding=encoding,
            )
        elif format == "logic":
            resource_val = sem.read_logic(
                string_data, logic_parser=logic_parser, encoding=encoding
            )
        elif format == "val":
            resource_val = sem.read_valuation(string_data, encoding=encoding)
        else:
            raise AssertionError(
                "Internal NLTK error: Format %s isn't "
                "handled by nltk.data.load()" % (format,)
            )

    opened_resource.close()

    # If requested, add it to the cache.
    if cache:
        try:
            _resource_cache[(resource_url, format)] = resource_val
            # TODO: add this line
            # print('<<Caching a copy of %s>>' % (resource_url,))
        except TypeError:
            # We can't create weak references to some object types, like
            # strings and tuples.  For now, just don't cache them.
            pass

    return resource_val


def show_cfg(resource_url, escape="##"):
    """
    Write out a grammar file, ignoring escaped and empty lines.

    :type resource_url: str
    :param resource_url: A URL specifying where the resource should be
        loaded from.  The default protocol is "nltk:", which searches
        for the file in the the NLTK data package.
    :type escape: str
    :param escape: Prepended string that signals lines to be ignored
    """
    resource_url = normalize_resource_url(resource_url)
    resource_val = load(resource_url, format="text", cache=False)
    lines = resource_val.splitlines()
    for l in lines:
        if l.startswith(escape):
            continue
        if re.match("^$", l):
            continue
        print(l)


def clear_cache():
    """
    Remove all objects from the resource cache.
    :see: load()
    """
    _resource_cache.clear()


def _open(resource_url):
    """
    Helper function that returns an open file object for a resource,
    given its resource URL.  If the given resource URL uses the "nltk:"
    protocol, or uses no protocol, then use ``nltk.data.find`` to find
    its path, and open it with the given mode; if the resource URL
    uses the 'file' protocol, then open the file with the given mode;
    otherwise, delegate to ``urllib2.urlopen``.

    :type resource_url: str
    :param resource_url: A URL specifying where the resource should be
        loaded from.  The default protocol is "nltk:", which searches
        for the file in the the NLTK data package.
    """
    resource_url = normalize_resource_url(resource_url)
    protocol, path_ = split_resource_url(resource_url)

    if protocol is None or protocol.lower() == "nltk":
        return find(path_, path + [""]).open()
    elif protocol.lower() == "file":
        # urllib might not use mode='rb', so handle this one ourselves:
        return find(path_, [""]).open()
    else:
        return urlopen(resource_url)


######################################################################
# Lazy Resource Loader
######################################################################


class LazyLoader:

    def __init__(self, _path):
        self._path = _path

    def __load(self):
        resource = load(self._path)
        # This is where the magic happens!  Transform ourselves into
        # the object by modifying our own __dict__ and __class__ to
        # match that of `resource`.
        self.__dict__ = resource.__dict__
        self.__class__ = resource.__class__

    def __getattr__(self, attr):
        self.__load()
        # This looks circular, but its not, since __load() changes our
        # __class__ to something new:
        return getattr(self, attr)

    def __repr__(self):
        self.__load()
        # This looks circular, but its not, since __load() changes our
        # __class__ to something new:
        return repr(self)


######################################################################
# Open-On-Demand ZipFile
######################################################################


class OpenOnDemandZipFile(zipfile.ZipFile):
    """
    A subclass of ``zipfile.ZipFile`` that closes its file pointer
    whenever it is not using it; and re-opens it when it needs to read
    data from the zipfile.  This is useful for reducing the number of
    open file handles when many zip files are being accessed at once.
    ``OpenOnDemandZipFile`` must be constructed from a filename, not a
    file-like object (to allow re-opening).  ``OpenOnDemandZipFile`` is
    read-only (i.e. ``write()`` and ``writestr()`` are disabled.
    """

    def __init__(self, filename):
        if not isinstance(filename, str):
            raise TypeError("ReopenableZipFile filename must be a string")
        zipfile.ZipFile.__init__(self, filename)
        assert self.filename == filename
        self.close()
        # After closing a ZipFile object, the _fileRefCnt needs to be cleared
        # for Python2and3 compatible code.
        self._fileRefCnt = 0

    def read(self, name):
        assert self.fp is None
        self.fp = open(self.filename, "rb")
        value = zipfile.ZipFile.read(self, name)
        # Ensure that _fileRefCnt needs to be set for Python2and3 compatible code.
        # Since we only opened one file here, we add 1.
        self._fileRefCnt += 1
        self.close()
        return value

    def write(self, *args, **kwargs):
        """:raise NotImplementedError: OpenOnDemandZipfile is read-only"""
        raise NotImplementedError("OpenOnDemandZipfile is read-only")

    def writestr(self, *args, **kwargs):
        """:raise NotImplementedError: OpenOnDemandZipfile is read-only"""
        raise NotImplementedError("OpenOnDemandZipfile is read-only")

    def __repr__(self):
        return repr("OpenOnDemandZipFile(%r)" % self.filename)


######################################################################
# Seekable Unicode Stream Reader
######################################################################


class SeekableUnicodeStreamReader:
    """
    A stream reader that automatically encodes the source byte stream
    into unicode (like ``codecs.StreamReader``); but still supports the
    ``seek()`` and ``tell()`` operations correctly.  This is in contrast
    to ``codecs.StreamReader``, which provide *broken* ``seek()`` and
    ``tell()`` methods.

    This class was motivated by ``StreamBackedCorpusView``, which
    makes extensive use of ``seek()`` and ``tell()``, and needs to be
    able to handle unicode-encoded files.

    Note: this class requires stateless decoders.  To my knowledge,
    this shouldn't cause a problem with any of python's builtin
    unicode encodings.
    """

    DEBUG = True  # : If true, then perform extra sanity checks.

    def __init__(self, stream, encoding, errors="strict"):
        # Rewind the stream to its beginning.
        stream.seek(0)

        self.stream = stream
        """The underlying stream."""

        self.encoding = encoding
        """The name of the encoding that should be used to encode the
           underlying stream."""

        self.errors = errors
        """The error mode that should be used when decoding data from
           the underlying stream.  Can be 'strict', 'ignore', or
           'replace'."""

        self.decode = codecs.getdecoder(encoding)
        """The function that is used to decode byte strings into
           unicode strings."""

        self.bytebuffer = b""
        """A buffer to use bytes that have been read but have not yet
           been decoded.  This is only used when the final bytes from
           a read do not form a complete encoding for a character."""

        self.linebuffer = None
        """A buffer used by ``readline()`` to hold characters that have
           been read, but have not yet been returned by ``read()`` or
           ``readline()``.  This buffer consists of a list of unicode
           strings, where each string corresponds to a single line.
           The final element of the list may or may not be a complete
           line.  Note that the existence of a linebuffer makes the
           ``tell()`` operation more complex, because it must backtrack
           to the beginning of the buffer to determine the correct
           file position in the underlying byte stream."""

        self._rewind_checkpoint = 0
        """The file position at which the most recent read on the
           underlying stream began.  This is used, together with
           ``_rewind_numchars``, to backtrack to the beginning of
           ``linebuffer`` (which is required by ``tell()``)."""

        self._rewind_numchars = None
        """The number of characters that have been returned since the
           read that started at ``_rewind_checkpoint``.  This is used,
           together with ``_rewind_checkpoint``, to backtrack to the
           beginning of ``linebuffer`` (which is required by ``tell()``)."""

        self._bom = self._check_bom()
        """The length of the byte order marker at the beginning of
           the stream (or None for no byte order marker)."""

    # /////////////////////////////////////////////////////////////////
    # Read methods
    # /////////////////////////////////////////////////////////////////

    def read(self, size=None):
        """
        Read up to ``size`` bytes, decode them using this reader's
        encoding, and return the resulting unicode string.

        :param size: The maximum number of bytes to read.  If not
            specified, then read as many bytes as possible.
        :type size: int
        :rtype: unicode
        """
        chars = self._read(size)

        # If linebuffer is not empty, then include it in the result
        if self.linebuffer:
            chars = "".join(self.linebuffer) + chars
            self.linebuffer = None
            self._rewind_numchars = None

        return chars

    def discard_line(self):
        if self.linebuffer and len(self.linebuffer) > 1:
            line = self.linebuffer.pop(0)
            self._rewind_numchars += len(line)
        else:
            self.stream.readline()

    def readline(self, size=None):
        """
        Read a line of text, decode it using this reader's encoding,
        and return the resulting unicode string.

        :param size: The maximum number of bytes to read.  If no
            newline is encountered before ``size`` bytes have been read,
            then the returned value may not be a complete line of text.
        :type size: int
        """
        # If we have a non-empty linebuffer, then return the first
        # line from it.  (Note that the last element of linebuffer may
        # not be a complete line; so let _read() deal with it.)
        if self.linebuffer and len(self.linebuffer) > 1:
            line = self.linebuffer.pop(0)
            self._rewind_numchars += len(line)
            return line

        readsize = size or 72
        chars = ""

        # If there's a remaining incomplete line in the buffer, add it.
        if self.linebuffer:
            chars += self.linebuffer.pop()
            self.linebuffer = None

        while True:
            startpos = self.stream.tell() - len(self.bytebuffer)
            new_chars = self._read(readsize)

            # If we're at a '\r', then read one extra character, since
            # it might be a '\n', to get the proper line ending.
            if new_chars and new_chars.endswith("\r"):
                new_chars += self._read(1)

            chars += new_chars
            lines = chars.splitlines(True)
            if len(lines) > 1:
                line = lines[0]
                self.linebuffer = lines[1:]
                self._rewind_numchars = len(new_chars) - (len(chars) - len(line))
                self._rewind_checkpoint = startpos
                break
            elif len(lines) == 1:
                line0withend = lines[0]
                line0withoutend = lines[0].splitlines(False)[0]
                if line0withend != line0withoutend:  # complete line
                    line = line0withend
                    break

            if not new_chars or size is not None:
                line = chars
                break

            # Read successively larger blocks of text.
            if readsize < 8000:
                readsize *= 2

        return line

    def readlines(self, sizehint=None, keepends=True):
        """
        Read this file's contents, decode them using this reader's
        encoding, and return it as a list of unicode lines.

        :rtype: list(unicode)
        :param sizehint: Ignored.
        :param keepends: If false, then strip newlines.
        """
        return self.read().splitlines(keepends)

    def next(self):
        """Return the next decoded line from the underlying stream."""
        line = self.readline()
        if line:
            return line
        else:
            raise StopIteration

    def __next__(self):
        return self.next()

    def __iter__(self):
        """Return self"""
        return self

    def __del__(self):
        # let garbage collector deal with still opened streams
        if not self.closed:
            self.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def xreadlines(self):
        """Return self"""
        return self

    # /////////////////////////////////////////////////////////////////
    # Pass-through methods & properties
    # /////////////////////////////////////////////////////////////////

    @property
    def closed(self):
        """True if the underlying stream is closed."""
        return self.stream.closed

    @property
    def name(self):
        """The name of the underlying stream."""
        return self.stream.name

    @property
    def mode(self):
        """The mode of the underlying stream."""
        return self.stream.mode

    def close(self):
        """
        Close the underlying stream.
        """
        self.stream.close()

    # /////////////////////////////////////////////////////////////////
    # Seek and tell
    # /////////////////////////////////////////////////////////////////

    def seek(self, offset, whence=0):
        """
        Move the stream to a new file position.  If the reader is
        maintaining any buffers, then they will be cleared.

        :param offset: A byte count offset.
        :param whence: If 0, then the offset is from the start of the file
            (offset should be positive), if 1, then the offset is from the
            current position (offset may be positive or negative); and if 2,
            then the offset is from the end of the file (offset should
            typically be negative).
        """
        if whence == 1:
            raise ValueError(
                "Relative seek is not supported for "
                "SeekableUnicodeStreamReader -- consider "
                "using char_seek_forward() instead."
            )
        self.stream.seek(offset, whence)
        self.linebuffer = None
        self.bytebuffer = b""
        self._rewind_numchars = None
        self._rewind_checkpoint = self.stream.tell()

    def char_seek_forward(self, offset):
        """
        Move the read pointer forward by ``offset`` characters.
        """
        if offset < 0:
            raise ValueError("Negative offsets are not supported")
        # Clear all buffers.
        self.seek(self.tell())
        # Perform the seek operation.
        self._char_seek_forward(offset)

    def _char_seek_forward(self, offset, est_bytes=None):
        """
        Move the file position forward by ``offset`` characters,
        ignoring all buffers.

        :param est_bytes: A hint, giving an estimate of the number of
            bytes that will be needed to move forward by ``offset`` chars.
            Defaults to ``offset``.
        """
        if est_bytes is None:
            est_bytes = offset
        bytes = b""

        while True:
            # Read in a block of bytes.
            newbytes = self.stream.read(est_bytes - len(bytes))
            bytes += newbytes

            # Decode the bytes to characters.
            chars, bytes_decoded = self._incr_decode(bytes)

            # If we got the right number of characters, then seek
            # backwards over any truncated characters, and return.
            if len(chars) == offset:
                self.stream.seek(-len(bytes) + bytes_decoded, 1)
                return

            # If we went too far, then we can back-up until we get it
            # right, using the bytes we've already read.
            if len(chars) > offset:
                while len(chars) > offset:
                    # Assume at least one byte/char.
                    est_bytes += offset - len(chars)
                    chars, bytes_decoded = self._incr_decode(bytes[:est_bytes])
                self.stream.seek(-len(bytes) + bytes_decoded, 1)
                return

            # Otherwise, we haven't read enough bytes yet; loop again.
            est_bytes += offset - len(chars)

    def tell(self):
        """
        Return the current file position on the underlying byte
        stream.  If this reader is maintaining any buffers, then the
        returned file position will be the position of the beginning
        of those buffers.
        """
        # If nothing's buffered, then just return our current filepos:
        if self.linebuffer is None:
            return self.stream.tell() - len(self.bytebuffer)

        # Otherwise, we'll need to backtrack the filepos until we
        # reach the beginning of the buffer.

        # Store our original file position, so we can return here.
        orig_filepos = self.stream.tell()

        # Calculate an estimate of where we think the newline is.
        bytes_read = (orig_filepos - len(self.bytebuffer)) - self._rewind_checkpoint
        buf_size = sum(len(line) for line in self.linebuffer)
        est_bytes = int(
            bytes_read * self._rewind_numchars / (self._rewind_numchars + buf_size)
        )

        self.stream.seek(self._rewind_checkpoint)
        self._char_seek_forward(self._rewind_numchars, est_bytes)
        filepos = self.stream.tell()

        # Sanity check
        if self.DEBUG:
            self.stream.seek(filepos)
            check1 = self._incr_decode(self.stream.read(50))[0]
            check2 = "".join(self.linebuffer)
            assert check1.startswith(check2) or check2.startswith(check1)

        # Return to our original filepos (so we don't have to throw
        # out our buffer.)
        self.stream.seek(orig_filepos)

        # Return the calculated filepos
        return filepos

    # /////////////////////////////////////////////////////////////////
    # Helper methods
    # /////////////////////////////////////////////////////////////////

    def _read(self, size=None):
        """
        Read up to ``size`` bytes from the underlying stream, decode
        them using this reader's encoding, and return the resulting
        unicode string.  ``linebuffer`` is not included in the result.
        """
        if size == 0:
            return ""

        # Skip past the byte order marker, if present.
        if self._bom and self.stream.tell() == 0:
            self.stream.read(self._bom)

        # Read the requested number of bytes.
        if size is None:
            new_bytes = self.stream.read()
        else:
            new_bytes = self.stream.read(size)
        bytes = self.bytebuffer + new_bytes

        # Decode the bytes into unicode characters
        chars, bytes_decoded = self._incr_decode(bytes)

        # If we got bytes but couldn't decode any, then read further.
        if (size is not None) and (not chars) and (len(new_bytes) > 0):
            while not chars:
                new_bytes = self.stream.read(1)
                if not new_bytes:
                    break  # end of file.
                bytes += new_bytes
                chars, bytes_decoded = self._incr_decode(bytes)

        # Record any bytes we didn't consume.
        self.bytebuffer = bytes[bytes_decoded:]

        # Return the result
        return chars

    def _incr_decode(self, bytes):
        """
        Decode the given byte string into a unicode string, using this
        reader's encoding.  If an exception is encountered that
        appears to be caused by a truncation error, then just decode
        the byte string without the bytes that cause the trunctaion
        error.

        Return a tuple ``(chars, num_consumed)``, where ``chars`` is
        the decoded unicode string, and ``num_consumed`` is the
        number of bytes that were consumed.
        """
        while True:
            try:
                return self.decode(bytes, "strict")
            except UnicodeDecodeError as exc:
                # If the exception occurs at the end of the string,
                # then assume that it's a truncation error.
                if exc.end == len(bytes):
                    return self.decode(bytes[: exc.start], self.errors)

                # Otherwise, if we're being strict, then raise it.
                elif self.errors == "strict":
                    raise

                # If we're not strict, then re-process it with our
                # errors setting.  This *may* raise an exception.
                else:
                    return self.decode(bytes, self.errors)

    _BOM_TABLE = {
        "utf8": [(codecs.BOM_UTF8, None)],
        "utf16": [(codecs.BOM_UTF16_LE, "utf16-le"), (codecs.BOM_UTF16_BE, "utf16-be")],
        "utf16le": [(codecs.BOM_UTF16_LE, None)],
        "utf16be": [(codecs.BOM_UTF16_BE, None)],
        "utf32": [(codecs.BOM_UTF32_LE, "utf32-le"), (codecs.BOM_UTF32_BE, "utf32-be")],
        "utf32le": [(codecs.BOM_UTF32_LE, None)],
        "utf32be": [(codecs.BOM_UTF32_BE, None)],
    }

    def _check_bom(self):
        # Normalize our encoding name
        enc = re.sub("[ -]", "", self.encoding.lower())

        # Look up our encoding in the BOM table.
        bom_info = self._BOM_TABLE.get(enc)

        if bom_info:
            # Read a prefix, to check against the BOM(s)
            bytes = self.stream.read(16)
            self.stream.seek(0)

            # Check for each possible BOM.
            for bom, new_encoding in bom_info:
                if bytes.startswith(bom):
                    if new_encoding:
                        self.encoding = new_encoding
                    return len(bom)

        return None


__all__ = [
    "path",
    "PathPointer",
    "FileSystemPathPointer",
    "BufferedGzipFile",
    "GzipFileSystemPathPointer",
    "GzipFileSystemPathPointer",
    "find",
    "retrieve",
    "FORMATS",
    "AUTO_FORMATS",
    "load",
    "show_cfg",
    "clear_cache",
    "LazyLoader",
    "OpenOnDemandZipFile",
    "GzipFileSystemPathPointer",
    "SeekableUnicodeStreamReader",
]

# === NexusCore/openenv\Lib\site-packages\tqdm\std.py ===
"""
Customisable progressbar decorator for iterators.
Includes a default `range` iterator printing to `stderr`.

Usage:
>>> from tqdm import trange, tqdm
>>> for i in trange(10):
...     ...
"""
import sys
from collections import OrderedDict, defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from numbers import Number
from time import time
from warnings import warn
from weakref import WeakSet

from ._monitor import TMonitor
from .utils import (
    CallbackIOWrapper, Comparable, DisableOnWriteError, FormatReplace, SimpleTextIOWrapper,
    _is_ascii, _screen_shape_wrapper, _supports_unicode, _term_move_up, disp_len, disp_trim,
    envwrap)

__author__ = "https://github.com/tqdm/tqdm#contributions"
__all__ = ['tqdm', 'trange',
           'TqdmTypeError', 'TqdmKeyError', 'TqdmWarning',
           'TqdmExperimentalWarning', 'TqdmDeprecationWarning',
           'TqdmMonitorWarning']


class TqdmTypeError(TypeError):
    pass


class TqdmKeyError(KeyError):
    pass


class TqdmWarning(Warning):
    """base class for all tqdm warnings.

    Used for non-external-code-breaking errors, such as garbled printing.
    """
    def __init__(self, msg, fp_write=None, *a, **k):
        if fp_write is not None:
            fp_write("\n" + self.__class__.__name__ + ": " + str(msg).rstrip() + '\n')
        else:
            super().__init__(msg, *a, **k)


class TqdmExperimentalWarning(TqdmWarning, FutureWarning):
    """beta feature, unstable API and behaviour"""
    pass


class TqdmDeprecationWarning(TqdmWarning, DeprecationWarning):
    # not suppressed if raised
    pass


class TqdmMonitorWarning(TqdmWarning, RuntimeWarning):
    """tqdm monitor errors which do not affect external functionality"""
    pass


def TRLock(*args, **kwargs):
    """threading RLock"""
    try:
        from threading import RLock
        return RLock(*args, **kwargs)
    except (ImportError, OSError):  # pragma: no cover
        pass


class TqdmDefaultWriteLock(object):
    """
    Provide a default write lock for thread and multiprocessing safety.
    Works only on platforms supporting `fork` (so Windows is excluded).
    You must initialise a `tqdm` or `TqdmDefaultWriteLock` instance
    before forking in order for the write lock to work.
    On Windows, you need to supply the lock from the parent to the children as
    an argument to joblib or the parallelism lib you use.
    """
    # global thread lock so no setup required for multithreading.
    # NB: Do not create multiprocessing lock as it sets the multiprocessing
    # context, disallowing `spawn()`/`forkserver()`
    th_lock = TRLock()

    def __init__(self):
        # Create global parallelism locks to avoid racing issues with parallel
        # bars works only if fork available (Linux/MacOSX, but not Windows)
        cls = type(self)
        root_lock = cls.th_lock
        if root_lock is not None:
            root_lock.acquire()
        cls.create_mp_lock()
        self.locks = [lk for lk in [cls.mp_lock, cls.th_lock] if lk is not None]
        if root_lock is not None:
            root_lock.release()

    def acquire(self, *a, **k):
        for lock in self.locks:
            lock.acquire(*a, **k)

    def release(self):
        for lock in self.locks[::-1]:  # Release in inverse order of acquisition
            lock.release()

    def __enter__(self):
        self.acquire()

    def __exit__(self, *exc):
        self.release()

    @classmethod
    def create_mp_lock(cls):
        if not hasattr(cls, 'mp_lock'):
            try:
                from multiprocessing import RLock
                cls.mp_lock = RLock()
            except (ImportError, OSError):  # pragma: no cover
                cls.mp_lock = None

    @classmethod
    def create_th_lock(cls):
        assert hasattr(cls, 'th_lock')
        warn("create_th_lock not needed anymore", TqdmDeprecationWarning, stacklevel=2)


class Bar(object):
    """
    `str.format`-able bar with format specifiers: `[width][type]`

    - `width`
      + unspecified (default): use `self.default_len`
      + `int >= 0`: overrides `self.default_len`
      + `int < 0`: subtract from `self.default_len`
    - `type`
      + `a`: ascii (`charset=self.ASCII` override)
      + `u`: unicode (`charset=self.UTF` override)
      + `b`: blank (`charset="  "` override)
    """
    ASCII = " 123456789#"
    UTF = u" " + u''.join(map(chr, range(0x258F, 0x2587, -1)))
    BLANK = "  "
    COLOUR_RESET = '\x1b[0m'
    COLOUR_RGB = '\x1b[38;2;%d;%d;%dm'
    COLOURS = {'BLACK': '\x1b[30m', 'RED': '\x1b[31m', 'GREEN': '\x1b[32m',
               'YELLOW': '\x1b[33m', 'BLUE': '\x1b[34m', 'MAGENTA': '\x1b[35m',
               'CYAN': '\x1b[36m', 'WHITE': '\x1b[37m'}

    def __init__(self, frac, default_len=10, charset=UTF, colour=None):
        if not 0 <= frac <= 1:
            warn("clamping frac to range [0, 1]", TqdmWarning, stacklevel=2)
            frac = max(0, min(1, frac))
        assert default_len > 0
        self.frac = frac
        self.default_len = default_len
        self.charset = charset
        self.colour = colour

    @property
    def colour(self):
        return self._colour

    @colour.setter
    def colour(self, value):
        if not value:
            self._colour = None
            return
        try:
            if value.upper() in self.COLOURS:
                self._colour = self.COLOURS[value.upper()]
            elif value[0] == '#' and len(value) == 7:
                self._colour = self.COLOUR_RGB % tuple(
                    int(i, 16) for i in (value[1:3], value[3:5], value[5:7]))
            else:
                raise KeyError
        except (KeyError, AttributeError):
            warn("Unknown colour (%s); valid choices: [hex (#00ff00), %s]" % (
                 value, ", ".join(self.COLOURS)),
                 TqdmWarning, stacklevel=2)
            self._colour = None

    def __format__(self, format_spec):
        if format_spec:
            _type = format_spec[-1].lower()
            try:
                charset = {'a': self.ASCII, 'u': self.UTF, 'b': self.BLANK}[_type]
            except KeyError:
                charset = self.charset
            else:
                format_spec = format_spec[:-1]
            if format_spec:
                N_BARS = int(format_spec)
                if N_BARS < 0:
                    N_BARS += self.default_len
            else:
                N_BARS = self.default_len
        else:
            charset = self.charset
            N_BARS = self.default_len

        nsyms = len(charset) - 1
        bar_length, frac_bar_length = divmod(int(self.frac * N_BARS * nsyms), nsyms)

        res = charset[-1] * bar_length
        if bar_length < N_BARS:  # whitespace padding
            res = res + charset[frac_bar_length] + charset[0] * (N_BARS - bar_length - 1)
        return self.colour + res + self.COLOUR_RESET if self.colour else res


class EMA(object):
    """
    Exponential moving average: smoothing to give progressively lower
    weights to older values.

    Parameters
    ----------
    smoothing  : float, optional
        Smoothing factor in range [0, 1], [default: 0.3].
        Increase to give more weight to recent values.
        Ranges from 0 (yields old value) to 1 (yields new value).
    """
    def __init__(self, smoothing=0.3):
        self.alpha = smoothing
        self.last = 0
        self.calls = 0

    def __call__(self, x=None):
        """
        Parameters
        ----------
        x  : float
            New value to include in EMA.
        """
        beta = 1 - self.alpha
        if x is not None:
            self.last = self.alpha * x + beta * self.last
            self.calls += 1
        return self.last / (1 - beta ** self.calls) if self.calls else self.last


class tqdm(Comparable):
    """
    Decorate an iterable object, returning an iterator which acts exactly
    like the original iterable, but prints a dynamically updating
    progressbar every time a value is requested.

    Parameters
    ----------
    iterable  : iterable, optional
        Iterable to decorate with a progressbar.
        Leave blank to manually manage the updates.
    desc  : str, optional
        Prefix for the progressbar.
    total  : int or float, optional
        The number of expected iterations. If unspecified,
        len(iterable) is used if possible. If float("inf") or as a last
        resort, only basic progress statistics are displayed
        (no ETA, no progressbar).
        If `gui` is True and this parameter needs subsequent updating,
        specify an initial arbitrary large positive number,
        e.g. 9e9.
    leave  : bool, optional
        If [default: True], keeps all traces of the progressbar
        upon termination of iteration.
        If `None`, will leave only if `position` is `0`.
    file  : `io.TextIOWrapper` or `io.StringIO`, optional
        Specifies where to output the progress messages
        (default: sys.stderr). Uses `file.write(str)` and `file.flush()`
        methods.  For encoding, see `write_bytes`.
    ncols  : int, optional
        The width of the entire output message. If specified,
        dynamically resizes the progressbar to stay within this bound.
        If unspecified, attempts to use environment width. The
        fallback is a meter width of 10 and no limit for the counter and
        statistics. If 0, will not print any meter (only stats).
    mininterval  : float, optional
        Minimum progress display update interval [default: 0.1] seconds.
    maxinterval  : float, optional
        Maximum progress display update interval [default: 10] seconds.
        Automatically adjusts `miniters` to correspond to `mininterval`
        after long display update lag. Only works if `dynamic_miniters`
        or monitor thread is enabled.
    miniters  : int or float, optional
        Minimum progress display update interval, in iterations.
        If 0 and `dynamic_miniters`, will automatically adjust to equal
        `mininterval` (more CPU efficient, good for tight loops).
        If > 0, will skip display of specified number of iterations.
        Tweak this and `mininterval` to get very efficient loops.
        If your progress is erratic with both fast and slow iterations
        (network, skipping items, etc) you should set miniters=1.
    ascii  : bool or str, optional
        If unspecified or False, use unicode (smooth blocks) to fill
        the meter. The fallback is to use ASCII characters " 123456789#".
    disable  : bool, optional
        Whether to disable the entire progressbar wrapper
        [default: False]. If set to None, disable on non-TTY.
    unit  : str, optional
        String that will be used to define the unit of each iteration
        [default: it].
    unit_scale  : bool or int or float, optional
        If 1 or True, the number of iterations will be reduced/scaled
        automatically and a metric prefix following the
        International System of Units standard will be added
        (kilo, mega, etc.) [default: False]. If any other non-zero
        number, will scale `total` and `n`.
    dynamic_ncols  : bool, optional
        If set, constantly alters `ncols` and `nrows` to the
        environment (allowing for window resizes) [default: False].
    smoothing  : float, optional
        Exponential moving average smoothing factor for speed estimates
        (ignored in GUI mode). Ranges from 0 (average speed) to 1
        (current/instantaneous speed) [default: 0.3].
    bar_format  : str, optional
        Specify a custom bar string formatting. May impact performance.
        [default: '{l_bar}{bar}{r_bar}'], where
        l_bar='{desc}: {percentage:3.0f}%|' and
        r_bar='| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, '
            '{rate_fmt}{postfix}]'
        Possible vars: l_bar, bar, r_bar, n, n_fmt, total, total_fmt,
            percentage, elapsed, elapsed_s, ncols, nrows, desc, unit,
            rate, rate_fmt, rate_noinv, rate_noinv_fmt,
            rate_inv, rate_inv_fmt, postfix, unit_divisor,
            remaining, remaining_s, eta.
        Note that a trailing ": " is automatically removed after {desc}
        if the latter is empty.
    initial  : int or float, optional
        The initial counter value. Useful when restarting a progress
        bar [default: 0]. If using float, consider specifying `{n:.3f}`
        or similar in `bar_format`, or specifying `unit_scale`.
    position  : int, optional
        Specify the line offset to print this bar (starting from 0)
        Automatic if unspecified.
        Useful to manage multiple bars at once (eg, from threads).
    postfix  : dict or *, optional
        Specify additional stats to display at the end of the bar.
        Calls `set_postfix(**postfix)` if possible (dict).
    unit_divisor  : float, optional
        [default: 1000], ignored unless `unit_scale` is True.
    write_bytes  : bool, optional
        Whether to write bytes. If (default: False) will write unicode.
    lock_args  : tuple, optional
        Passed to `refresh` for intermediate output
        (initialisation, iterating, and updating).
    nrows  : int, optional
        The screen height. If specified, hides nested bars outside this
        bound. If unspecified, attempts to use environment height.
        The fallback is 20.
    colour  : str, optional
        Bar colour (e.g. 'green', '#00ff00').
    delay  : float, optional
        Don't display until [default: 0] seconds have elapsed.
    gui  : bool, optional
        WARNING: internal parameter - do not use.
        Use tqdm.gui.tqdm(...) instead. If set, will attempt to use
        matplotlib animations for a graphical output [default: False].

    Returns
    -------
    out  : decorated iterator.
    """

    monitor_interval = 10  # set to 0 to disable the thread
    monitor = None
    _instances = WeakSet()

    @staticmethod
    def format_sizeof(num, suffix='', divisor=1000):
        """
        Formats a number (greater than unity) with SI Order of Magnitude
        prefixes.

        Parameters
        ----------
        num  : float
            Number ( >= 1) to format.
        suffix  : str, optional
            Post-postfix [default: ''].
        divisor  : float, optional
            Divisor between prefixes [default: 1000].

        Returns
        -------
        out  : str
            Number with Order of Magnitude SI unit postfix.
        """
        for unit in ['', 'k', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(num) < 999.5:
                if abs(num) < 99.95:
                    if abs(num) < 9.995:
                        return f'{num:1.2f}{unit}{suffix}'
                    return f'{num:2.1f}{unit}{suffix}'
                return f'{num:3.0f}{unit}{suffix}'
            num /= divisor
        return f'{num:3.1f}Y{suffix}'

    @staticmethod
    def format_interval(t):
        """
        Formats a number of seconds as a clock time, [H:]MM:SS

        Parameters
        ----------
        t  : int
            Number of seconds.

        Returns
        -------
        out  : str
            [H:]MM:SS
        """
        mins, s = divmod(int(t), 60)
        h, m = divmod(mins, 60)
        return f'{h:d}:{m:02d}:{s:02d}' if h else f'{m:02d}:{s:02d}'

    @staticmethod
    def format_num(n):
        """
        Intelligent scientific notation (.3g).

        Parameters
        ----------
        n  : int or float or Numeric
            A Number.

        Returns
        -------
        out  : str
            Formatted number.
        """
        f = f'{n:.3g}'.replace('e+0', 'e+').replace('e-0', 'e-')
        n = str(n)
        return f if len(f) < len(n) else n

    @staticmethod
    def status_printer(file):
        """
        Manage the printing and in-place updating of a line of characters.
        Note that if the string is longer than a line, then in-place
        updating may not work (it will print a new line at each refresh).
        """
        fp = file
        fp_flush = getattr(fp, 'flush', lambda: None)  # pragma: no cover
        if fp in (sys.stderr, sys.stdout):
            getattr(sys.stderr, 'flush', lambda: None)()
            getattr(sys.stdout, 'flush', lambda: None)()

        def fp_write(s):
            fp.write(str(s))
            fp_flush()

        last_len = [0]

        def print_status(s):
            len_s = disp_len(s)
            fp_write('\r' + s + (' ' * max(last_len[0] - len_s, 0)))
            last_len[0] = len_s

        return print_status

    @staticmethod
    def format_meter(n, total, elapsed, ncols=None, prefix='', ascii=False, unit='it',
                     unit_scale=False, rate=None, bar_format=None, postfix=None,
                     unit_divisor=1000, initial=0, colour=None, **extra_kwargs):
        """
        Return a string-based progress bar given some parameters

        Parameters
        ----------
        n  : int or float
            Number of finished iterations.
        total  : int or float
            The expected total number of iterations. If meaningless (None),
            only basic progress statistics are displayed (no ETA).
        elapsed  : float
            Number of seconds passed since start.
        ncols  : int, optional
            The width of the entire output message. If specified,
            dynamically resizes `{bar}` to stay within this bound
            [default: None]. If `0`, will not print any bar (only stats).
            The fallback is `{bar:10}`.
        prefix  : str, optional
            Prefix message (included in total width) [default: ''].
            Use as {desc} in bar_format string.
        ascii  : bool, optional or str, optional
            If not set, use unicode (smooth blocks) to fill the meter
            [default: False]. The fallback is to use ASCII characters
            " 123456789#".
        unit  : str, optional
            The iteration unit [default: 'it'].
        unit_scale  : bool or int or float, optional
            If 1 or True, the number of iterations will be printed with an
            appropriate SI metric prefix (k = 10^3, M = 10^6, etc.)
            [default: False]. If any other non-zero number, will scale
            `total` and `n`.
        rate  : float, optional
            Manual override for iteration rate.
            If [default: None], uses n/elapsed.
        bar_format  : str, optional
            Specify a custom bar string formatting. May impact performance.
            [default: '{l_bar}{bar}{r_bar}'], where
            l_bar='{desc}: {percentage:3.0f}%|' and
            r_bar='| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, '
              '{rate_fmt}{postfix}]'
            Possible vars: l_bar, bar, r_bar, n, n_fmt, total, total_fmt,
              percentage, elapsed, elapsed_s, ncols, nrows, desc, unit,
              rate, rate_fmt, rate_noinv, rate_noinv_fmt,
              rate_inv, rate_inv_fmt, postfix, unit_divisor,
              remaining, remaining_s, eta.
            Note that a trailing ": " is automatically removed after {desc}
            if the latter is empty.
        postfix  : *, optional
            Similar to `prefix`, but placed at the end
            (e.g. for additional stats).
            Note: postfix is usually a string (not a dict) for this method,
            and will if possible be set to postfix = ', ' + postfix.
            However other types are supported (#382).
        unit_divisor  : float, optional
            [default: 1000], ignored unless `unit_scale` is True.
        initial  : int or float, optional
            The initial counter value [default: 0].
        colour  : str, optional
            Bar colour (e.g. 'green', '#00ff00').

        Returns
        -------
        out  : Formatted meter and stats, ready to display.
        """

        # sanity check: total
        if total and n >= (total + 0.5):  # allow float imprecision (#849)
            total = None

        # apply custom scale if necessary
        if unit_scale and unit_scale not in (True, 1):
            if total:
                total *= unit_scale
            n *= unit_scale
            if rate:
                rate *= unit_scale  # by default rate = self.avg_dn / self.avg_dt
            unit_scale = False

        elapsed_str = tqdm.format_interval(elapsed)

        # if unspecified, attempt to use rate = average speed
        # (we allow manual override since predicting time is an arcane art)
        if rate is None and elapsed:
            rate = (n - initial) / elapsed
        inv_rate = 1 / rate if rate else None
        format_sizeof = tqdm.format_sizeof
        rate_noinv_fmt = ((format_sizeof(rate) if unit_scale else f'{rate:5.2f}')
                          if rate else '?') + unit + '/s'
        rate_inv_fmt = (
            (format_sizeof(inv_rate) if unit_scale else f'{inv_rate:5.2f}')
            if inv_rate else '?') + 's/' + unit
        rate_fmt = rate_inv_fmt if inv_rate and inv_rate > 1 else rate_noinv_fmt

        if unit_scale:
            n_fmt = format_sizeof(n, divisor=unit_divisor)
            total_fmt = format_sizeof(total, divisor=unit_divisor) if total is not None else '?'
        else:
            n_fmt = str(n)
            total_fmt = str(total) if total is not None else '?'

        try:
            postfix = ', ' + postfix if postfix else ''
        except TypeError:
            pass

        remaining = (total - n) / rate if rate and total else 0
        remaining_str = tqdm.format_interval(remaining) if rate else '?'
        try:
            eta_dt = (datetime.now() + timedelta(seconds=remaining)
                      if rate and total else datetime.fromtimestamp(0, timezone.utc))
        except OverflowError:
            eta_dt = datetime.max

        # format the stats displayed to the left and right sides of the bar
        if prefix:
            # old prefix setup work around
            bool_prefix_colon_already = (prefix[-2:] == ": ")
            l_bar = prefix if bool_prefix_colon_already else prefix + ": "
        else:
            l_bar = ''

        r_bar = f'| {n_fmt}/{total_fmt} [{elapsed_str}<{remaining_str}, {rate_fmt}{postfix}]'

        # Custom bar formatting
        # Populate a dict with all available progress indicators
        format_dict = {
            # slight extension of self.format_dict
            'n': n, 'n_fmt': n_fmt, 'total': total, 'total_fmt': total_fmt,
            'elapsed': elapsed_str, 'elapsed_s': elapsed,
            'ncols': ncols, 'desc': prefix or '', 'unit': unit,
            'rate': inv_rate if inv_rate and inv_rate > 1 else rate,
            'rate_fmt': rate_fmt, 'rate_noinv': rate,
            'rate_noinv_fmt': rate_noinv_fmt, 'rate_inv': inv_rate,
            'rate_inv_fmt': rate_inv_fmt,
            'postfix': postfix, 'unit_divisor': unit_divisor,
            'colour': colour,
            # plus more useful definitions
            'remaining': remaining_str, 'remaining_s': remaining,
            'l_bar': l_bar, 'r_bar': r_bar, 'eta': eta_dt,
            **extra_kwargs}

        # total is known: we can predict some stats
        if total:
            # fractional and percentage progress
            frac = n / total
            percentage = frac * 100

            l_bar += f'{percentage:3.0f}%|'

            if ncols == 0:
                return l_bar[:-1] + r_bar[1:]

            format_dict.update(l_bar=l_bar)
            if bar_format:
                format_dict.update(percentage=percentage)

                # auto-remove colon for empty `{desc}`
                if not prefix:
                    bar_format = bar_format.replace("{desc}: ", '')
            else:
                bar_format = "{l_bar}{bar}{r_bar}"

            full_bar = FormatReplace()
            nobar = bar_format.format(bar=full_bar, **format_dict)
            if not full_bar.format_called:
                return nobar  # no `{bar}`; nothing else to do

            # Formatting progress bar space available for bar's display
            full_bar = Bar(frac,
                           max(1, ncols - disp_len(nobar)) if ncols else 10,
                           charset=Bar.ASCII if ascii is True else ascii or Bar.UTF,
                           colour=colour)
            if not _is_ascii(full_bar.charset) and _is_ascii(bar_format):
                bar_format = str(bar_format)
            res = bar_format.format(bar=full_bar, **format_dict)
            return disp_trim(res, ncols) if ncols else res

        elif bar_format:
            # user-specified bar_format but no total
            l_bar += '|'
            format_dict.update(l_bar=l_bar, percentage=0)
            full_bar = FormatReplace()
            nobar = bar_format.format(bar=full_bar, **format_dict)
            if not full_bar.format_called:
                return nobar
            full_bar = Bar(0,
                           max(1, ncols - disp_len(nobar)) if ncols else 10,
                           charset=Bar.BLANK, colour=colour)
            res = bar_format.format(bar=full_bar, **format_dict)
            return disp_trim(res, ncols) if ncols else res
        else:
            # no total: no progressbar, ETA, just progress stats
            return (f'{(prefix + ": ") if prefix else ""}'
                    f'{n_fmt}{unit} [{elapsed_str}, {rate_fmt}{postfix}]')

    def __new__(cls, *_, **__):
        instance = object.__new__(cls)
        with cls.get_lock():  # also constructs lock if non-existent
            cls._instances.add(instance)
            # create monitoring thread
            if cls.monitor_interval and (cls.monitor is None
                                         or not cls.monitor.report()):
                try:
                    cls.monitor = TMonitor(cls, cls.monitor_interval)
                except Exception as e:  # pragma: nocover
                    warn("tqdm:disabling monitor support"
                         " (monitor_interval = 0) due to:\n" + str(e),
                         TqdmMonitorWarning, stacklevel=2)
                    cls.monitor_interval = 0
        return instance

    @classmethod
    def _get_free_pos(cls, instance=None):
        """Skips specified instance."""
        positions = {abs(inst.pos) for inst in cls._instances
                     if inst is not instance and hasattr(inst, "pos")}
        return min(set(range(len(positions) + 1)).difference(positions))

    @classmethod
    def _decr_instances(cls, instance):
        """
        Remove from list and reposition another unfixed bar
        to fill the new gap.

        This means that by default (where all nested bars are unfixed),
        order is not maintained but screen flicker/blank space is minimised.
        (tqdm<=4.44.1 moved ALL subsequent unfixed bars up.)
        """
        with cls._lock:
            try:
                cls._instances.remove(instance)
            except KeyError:
                # if not instance.gui:  # pragma: no cover
                #     raise
                pass  # py2: maybe magically removed already
            # else:
            if not instance.gui:
                last = (instance.nrows or 20) - 1
                # find unfixed (`pos >= 0`) overflow (`pos >= nrows - 1`)
                instances = list(filter(
                    lambda i: hasattr(i, "pos") and last <= i.pos,
                    cls._instances))
                # set first found to current `pos`
                if instances:
                    inst = min(instances, key=lambda i: i.pos)
                    inst.clear(nolock=True)
                    inst.pos = abs(instance.pos)

    @classmethod
    def write(cls, s, file=None, end="\n", nolock=False):
        """Print a message via tqdm (without overlap with bars)."""
        fp = file if file is not None else sys.stdout
        with cls.external_write_mode(file=file, nolock=nolock):
            # Write the message
            fp.write(s)
            fp.write(end)

    @classmethod
    @contextmanager
    def external_write_mode(cls, file=None, nolock=False):
        """
        Disable tqdm within context and refresh tqdm when exits.
        Useful when writing to standard output stream
        """
        fp = file if file is not None else sys.stdout

        try:
            if not nolock:
                cls.get_lock().acquire()
            # Clear all bars
            inst_cleared = []
            for inst in getattr(cls, '_instances', []):
                # Clear instance if in the target output file
                # or if write output + tqdm output are both either
                # sys.stdout or sys.stderr (because both are mixed in terminal)
                if hasattr(inst, "start_t") and (inst.fp == fp or all(
                        f in (sys.stdout, sys.stderr) for f in (fp, inst.fp))):
                    inst.clear(nolock=True)
                    inst_cleared.append(inst)
            yield
            # Force refresh display of bars we cleared
            for inst in inst_cleared:
                inst.refresh(nolock=True)
        finally:
            if not nolock:
                cls._lock.release()

    @classmethod
    def set_lock(cls, lock):
        """Set the global lock."""
        cls._lock = lock

    @classmethod
    def get_lock(cls):
        """Get the global lock. Construct it if it does not exist."""
        if not hasattr(cls, '_lock'):
            cls._lock = TqdmDefaultWriteLock()
        return cls._lock

    @classmethod
    def pandas(cls, **tqdm_kwargs):
        """
        Registers the current `tqdm` class with
            pandas.core.
            ( frame.DataFrame
            | series.Series
            | groupby.(generic.)DataFrameGroupBy
            | groupby.(generic.)SeriesGroupBy
            ).progress_apply

        A new instance will be created every time `progress_apply` is called,
        and each instance will automatically `close()` upon completion.

        Parameters
        ----------
        tqdm_kwargs  : arguments for the tqdm instance

        Examples
        --------
        >>> import pandas as pd
        >>> import numpy as np
        >>> from tqdm import tqdm
        >>> from tqdm.gui import tqdm as tqdm_gui
        >>>
        >>> df = pd.DataFrame(np.random.randint(0, 100, (100000, 6)))
        >>> tqdm.pandas(ncols=50)  # can use tqdm_gui, optional kwargs, etc
        >>> # Now you can use `progress_apply` instead of `apply`
        >>> df.groupby(0).progress_apply(lambda x: x**2)

        References
        ----------
        <https://stackoverflow.com/questions/18603270/\
        progress-indicator-during-pandas-operations-python>
        """
        from warnings import catch_warnings, simplefilter

        from pandas.core.frame import DataFrame
        from pandas.core.series import Series
        try:
            with catch_warnings():
                simplefilter("ignore", category=FutureWarning)
                from pandas import Panel
        except ImportError:  # pandas>=1.2.0
            Panel = None
        Rolling, Expanding = None, None
        try:  # pandas>=1.0.0
            from pandas.core.window.rolling import _Rolling_and_Expanding
        except ImportError:
            try:  # pandas>=0.18.0
                from pandas.core.window import _Rolling_and_Expanding
            except ImportError:  # pandas>=1.2.0
                try:  # pandas>=1.2.0
                    from pandas.core.window.expanding import Expanding
                    from pandas.core.window.rolling import Rolling
                    _Rolling_and_Expanding = Rolling, Expanding
                except ImportError:  # pragma: no cover
                    _Rolling_and_Expanding = None
        try:  # pandas>=0.25.0
            from pandas.core.groupby.generic import SeriesGroupBy  # , NDFrameGroupBy
            from pandas.core.groupby.generic import DataFrameGroupBy
        except ImportError:  # pragma: no cover
            try:  # pandas>=0.23.0
                from pandas.core.groupby.groupby import DataFrameGroupBy, SeriesGroupBy
            except ImportError:
                from pandas.core.groupby import DataFrameGroupBy, SeriesGroupBy
        try:  # pandas>=0.23.0
            from pandas.core.groupby.groupby import GroupBy
        except ImportError:  # pragma: no cover
            from pandas.core.groupby import GroupBy

        try:  # pandas>=0.23.0
            from pandas.core.groupby.groupby import PanelGroupBy
        except ImportError:
            try:
                from pandas.core.groupby import PanelGroupBy
            except ImportError:  # pandas>=0.25.0
                PanelGroupBy = None

        tqdm_kwargs = tqdm_kwargs.copy()
        deprecated_t = [tqdm_kwargs.pop('deprecated_t', None)]

        def inner_generator(df_function='apply'):
            def inner(df, func, *args, **kwargs):
                """
                Parameters
                ----------
                df  : (DataFrame|Series)[GroupBy]
                    Data (may be grouped).
                func  : function
                    To be applied on the (grouped) data.
                **kwargs  : optional
                    Transmitted to `df.apply()`.
                """

                # Precompute total iterations
                total = tqdm_kwargs.pop("total", getattr(df, 'ngroups', None))
                if total is None:  # not grouped
                    if df_function == 'applymap':
                        total = df.size
                    elif isinstance(df, Series):
                        total = len(df)
                    elif (_Rolling_and_Expanding is None or
                          not isinstance(df, _Rolling_and_Expanding)):
                        # DataFrame or Panel
                        axis = kwargs.get('axis', 0)
                        if axis == 'index':
                            axis = 0
                        elif axis == 'columns':
                            axis = 1
                        # when axis=0, total is shape[axis1]
                        total = df.size // df.shape[axis]

                # Init bar
                if deprecated_t[0] is not None:
                    t = deprecated_t[0]
                    deprecated_t[0] = None
                else:
                    t = cls(total=total, **tqdm_kwargs)

                if len(args) > 0:
                    # *args intentionally not supported (see #244, #299)
                    TqdmDeprecationWarning(
                        "Except func, normal arguments are intentionally" +
                        " not supported by" +
                        " `(DataFrame|Series|GroupBy).progress_apply`." +
                        " Use keyword arguments instead.",
                        fp_write=getattr(t.fp, 'write', sys.stderr.write))

                try:  # pandas>=1.3.0
                    from pandas.core.common import is_builtin_func
                except ImportError:
                    is_builtin_func = df._is_builtin_func
                try:
                    func = is_builtin_func(func)
                except TypeError:
                    pass

                # Define bar updating wrapper
                def wrapper(*args, **kwargs):
                    # update tbar correctly
                    # it seems `pandas apply` calls `func` twice
                    # on the first column/row to decide whether it can
                    # take a fast or slow code path; so stop when t.total==t.n
                    t.update(n=1 if not t.total or t.n < t.total else 0)
                    return func(*args, **kwargs)

                # Apply the provided function (in **kwargs)
                # on the df using our wrapper (which provides bar updating)
                try:
                    return getattr(df, df_function)(wrapper, **kwargs)
                finally:
                    t.close()

            return inner

        # Monkeypatch pandas to provide easy methods
        # Enable custom tqdm progress in pandas!
        Series.progress_apply = inner_generator()
        SeriesGroupBy.progress_apply = inner_generator()
        Series.progress_map = inner_generator('map')
        SeriesGroupBy.progress_map = inner_generator('map')

        DataFrame.progress_apply = inner_generator()
        DataFrameGroupBy.progress_apply = inner_generator()
        DataFrame.progress_applymap = inner_generator('applymap')
        DataFrame.progress_map = inner_generator('map')
        DataFrameGroupBy.progress_map = inner_generator('map')

        if Panel is not None:
            Panel.progress_apply = inner_generator()
        if PanelGroupBy is not None:
            PanelGroupBy.progress_apply = inner_generator()

        GroupBy.progress_apply = inner_generator()
        GroupBy.progress_aggregate = inner_generator('aggregate')
        GroupBy.progress_transform = inner_generator('transform')

        if Rolling is not None and Expanding is not None:
            Rolling.progress_apply = inner_generator()
            Expanding.progress_apply = inner_generator()
        elif _Rolling_and_Expanding is not None:
            _Rolling_and_Expanding.progress_apply = inner_generator()

    # override defaults via env vars
    @envwrap("TQDM_", is_method=True, types={'total': float, 'ncols': int, 'miniters': float,
                                             'position': int, 'nrows': int})
    def __init__(self, iterable=None, desc=None, total=None, leave=True, file=None,
                 ncols=None, mininterval=0.1, maxinterval=10.0, miniters=None,
                 ascii=None, disable=False, unit='it', unit_scale=False,
                 dynamic_ncols=False, smoothing=0.3, bar_format=None, initial=0,
                 position=None, postfix=None, unit_divisor=1000, write_bytes=False,
                 lock_args=None, nrows=None, colour=None, delay=0.0, gui=False,
                 **kwargs):
        """see tqdm.tqdm for arguments"""
        if file is None:
            file = sys.stderr

        if write_bytes:
            # Despite coercing unicode into bytes, py2 sys.std* streams
            # should have bytes written to them.
            file = SimpleTextIOWrapper(
                file, encoding=getattr(file, 'encoding', None) or 'utf-8')

        file = DisableOnWriteError(file, tqdm_instance=self)

        if disable is None and hasattr(file, "isatty") and not file.isatty():
            disable = True

        if total is None and iterable is not None:
            try:
                total = len(iterable)
            except (TypeError, AttributeError):
                total = None
        if total == float("inf"):
            # Infinite iterations, behave same as unknown
            total = None

        if disable:
            self.iterable = iterable
            self.disable = disable
            with self._lock:
                self.pos = self._get_free_pos(self)
                self._instances.remove(self)
            self.n = initial
            self.total = total
            self.leave = leave
            return

        if kwargs:
            self.disable = True
            with self._lock:
                self.pos = self._get_free_pos(self)
                self._instances.remove(self)
            raise (
                TqdmDeprecationWarning(
                    "`nested` is deprecated and automated.\n"
                    "Use `position` instead for manual control.\n",
                    fp_write=getattr(file, 'write', sys.stderr.write))
                if "nested" in kwargs else
                TqdmKeyError("Unknown argument(s): " + str(kwargs)))

        # Preprocess the arguments
        if (
            (ncols is None or nrows is None) and (file in (sys.stderr, sys.stdout))
        ) or dynamic_ncols:  # pragma: no cover
            if dynamic_ncols:
                dynamic_ncols = _screen_shape_wrapper()
                if dynamic_ncols:
                    ncols, nrows = dynamic_ncols(file)
            else:
                _dynamic_ncols = _screen_shape_wrapper()
                if _dynamic_ncols:
                    _ncols, _nrows = _dynamic_ncols(file)
                    if ncols is None:
                        ncols = _ncols
                    if nrows is None:
                        nrows = _nrows

        if miniters is None:
            miniters = 0
            dynamic_miniters = True
        else:
            dynamic_miniters = False

        if mininterval is None:
            mininterval = 0

        if maxinterval is None:
            maxinterval = 0

        if ascii is None:
            ascii = not _supports_unicode(file)

        if bar_format and ascii is not True and not _is_ascii(ascii):
            # Convert bar format into unicode since terminal uses unicode
            bar_format = str(bar_format)

        if smoothing is None:
            smoothing = 0

        # Store the arguments
        self.iterable = iterable
        self.desc = desc or ''
        self.total = total
        self.leave = leave
        self.fp = file
        self.ncols = ncols
        self.nrows = nrows
        self.mininterval = mininterval
        self.maxinterval = maxinterval
        self.miniters = miniters
        self.dynamic_miniters = dynamic_miniters
        self.ascii = ascii
        self.disable = disable
        self.unit = unit
        self.unit_scale = unit_scale
        self.unit_divisor = unit_divisor
        self.initial = initial
        self.lock_args = lock_args
        self.delay = delay
        self.gui = gui
        self.dynamic_ncols = dynamic_ncols
        self.smoothing = smoothing
        self._ema_dn = EMA(smoothing)
        self._ema_dt = EMA(smoothing)
        self._ema_miniters = EMA(smoothing)
        self.bar_format = bar_format
        self.postfix = None
        self.colour = colour
        self._time = time
        if postfix:
            try:
                self.set_postfix(refresh=False, **postfix)
            except TypeError:
                self.postfix = postfix

        # Init the iterations counters
        self.last_print_n = initial
        self.n = initial

        # if nested, at initial sp() call we replace '\r' by '\n' to
        # not overwrite the outer progress bar
        with self._lock:
            # mark fixed positions as negative
            self.pos = self._get_free_pos(self) if position is None else -position

        if not gui:
            # Initialize the screen printer
            self.sp = self.status_printer(self.fp)
            if delay <= 0:
                self.refresh(lock_args=self.lock_args)

        # Init the time counter
        self.last_print_t = self._time()
        # NB: Avoid race conditions by setting start_t at the very end of init
        self.start_t = self.last_print_t

    def __bool__(self):
        if self.total is not None:
            return self.total > 0
        if self.iterable is None:
            raise TypeError('bool() undefined when iterable == total == None')
        return bool(self.iterable)

    def __len__(self):
        return (
            self.total if self.iterable is None
            else self.iterable.shape[0] if hasattr(self.iterable, "shape")
            else len(self.iterable) if hasattr(self.iterable, "__len__")
            else self.iterable.__length_hint__() if hasattr(self.iterable, "__length_hint__")
            else getattr(self, "total", None))

    def __reversed__(self):
        try:
            orig = self.iterable
        except AttributeError:
            raise TypeError("'tqdm' object is not reversible")
        else:
            self.iterable = reversed(self.iterable)
            return self.__iter__()
        finally:
            self.iterable = orig

    def __contains__(self, item):
        contains = getattr(self.iterable, '__contains__', None)
        return contains(item) if contains is not None else item in self.__iter__()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.close()
        except AttributeError:
            # maybe eager thread cleanup upon external error
            if (exc_type, exc_value, traceback) == (None, None, None):
                raise
            warn("AttributeError ignored", TqdmWarning, stacklevel=2)

    def __del__(self):
        self.close()

    def __str__(self):
        return self.format_meter(**self.format_dict)

    @property
    def _comparable(self):
        return abs(getattr(self, "pos", 1 << 31))

    def __hash__(self):
        return id(self)

    def __iter__(self):
        """Backward-compatibility to use: for x in tqdm(iterable)"""

        # Inlining instance variables as locals (speed optimisation)
        iterable = self.iterable

        # If the bar is disabled, then just walk the iterable
        # (note: keep this check outside the loop for performance)
        if self.disable:
            for obj in iterable:
                yield obj
            return

        mininterval = self.mininterval
        last_print_t = self.last_print_t
        last_print_n = self.last_print_n
        min_start_t = self.start_t + self.delay
        n = self.n
        time = self._time

        try:
            for obj in iterable:
                yield obj
                # Update and possibly print the progressbar.
                # Note: does not call self.update(1) for speed optimisation.
                n += 1

                if n - last_print_n >= self.miniters:
                    cur_t = time()
                    dt = cur_t - last_print_t
                    if dt >= mininterval and cur_t >= min_start_t:
                        self.update(n - last_print_n)
                        last_print_n = self.last_print_n
                        last_print_t = self.last_print_t
        finally:
            self.n = n
            self.close()

    def update(self, n=1):
        """
        Manually update the progress bar, useful for streams
        such as reading files.
        E.g.:
        >>> t = tqdm(total=filesize) # Initialise
        >>> for current_buffer in stream:
        ...    ...
        ...    t.update(len(current_buffer))
        >>> t.close()
        The last line is highly recommended, but possibly not necessary if
        `t.update()` will be called in such a way that `filesize` will be
        exactly reached and printed.

        Parameters
        ----------
        n  : int or float, optional
            Increment to add to the internal counter of iterations
            [default: 1]. If using float, consider specifying `{n:.3f}`
            or similar in `bar_format`, or specifying `unit_scale`.

        Returns
        -------
        out  : bool or None
            True if a `display()` was triggered.
        """
        if self.disable:
            return

        if n < 0:
            self.last_print_n += n  # for auto-refresh logic to work
        self.n += n

        # check counter first to reduce calls to time()
        if self.n - self.last_print_n >= self.miniters:
            cur_t = self._time()
            dt = cur_t - self.last_print_t
            if dt >= self.mininterval and cur_t >= self.start_t + self.delay:
                cur_t = self._time()
                dn = self.n - self.last_print_n  # >= n
                if self.smoothing and dt and dn:
                    # EMA (not just overall average)
                    self._ema_dn(dn)
                    self._ema_dt(dt)
                self.refresh(lock_args=self.lock_args)
                if self.dynamic_miniters:
                    # If no `miniters` was specified, adjust automatically to the
                    # maximum iteration rate seen so far between two prints.
                    # e.g.: After running `tqdm.update(5)`, subsequent
                    # calls to `tqdm.update()` will only cause an update after
                    # at least 5 more iterations.
                    if self.maxinterval and dt >= self.maxinterval:
                        self.miniters = dn * (self.mininterval or self.maxinterval) / dt
                    elif self.smoothing:
                        # EMA miniters update
                        self.miniters = self._ema_miniters(
                            dn * (self.mininterval / dt if self.mininterval and dt
                                  else 1))
                    else:
                        # max iters between two prints
                        self.miniters = max(self.miniters, dn)

                # Store old values for next call
                self.last_print_n = self.n
                self.last_print_t = cur_t
                return True

    def close(self):
        """Cleanup and (if leave=False) close the progressbar."""
        if self.disable:
            return

        # Prevent multiple closures
        self.disable = True

        # decrement instance pos and remove from internal set
        pos = abs(self.pos)
        self._decr_instances(self)

        if self.last_print_t < self.start_t + self.delay:
            # haven't ever displayed; nothing to clear
            return

        # GUI mode
        if getattr(self, 'sp', None) is None:
            return

        # annoyingly, _supports_unicode isn't good enough
        def fp_write(s):
            self.fp.write(str(s))

        try:
            fp_write('')
        except ValueError as e:
            if 'closed' in str(e):
                return
            raise  # pragma: no cover

        leave = pos == 0 if self.leave is None else self.leave

        with self._lock:
            if leave:
                # stats for overall rate (no weighted average)
                self._ema_dt = lambda: None
                self.display(pos=0)
                fp_write('\n')
            else:
                # clear previous display
                if self.display(msg='', pos=pos) and not pos:
                    fp_write('\r')

    def clear(self, nolock=False):
        """Clear current bar display."""
        if self.disable:
            return

        if not nolock:
            self._lock.acquire()
        pos = abs(self.pos)
        if pos < (self.nrows or 20):
            self.moveto(pos)
            self.sp('')
            self.fp.write('\r')  # place cursor back at the beginning of line
            self.moveto(-pos)
        if not nolock:
            self._lock.release()

    def refresh(self, nolock=False, lock_args=None):
        """
        Force refresh the display of this bar.

        Parameters
        ----------
        nolock  : bool, optional
            If `True`, does not lock.
            If [default: `False`]: calls `acquire()` on internal lock.
        lock_args  : tuple, optional
            Passed to internal lock's `acquire()`.
            If specified, will only `display()` if `acquire()` returns `True`.
        """
        if self.disable:
            return

        if not nolock:
            if lock_args:
                if not self._lock.acquire(*lock_args):
                    return False
            else:
                self._lock.acquire()
        self.display()
        if not nolock:
            self._lock.release()
        return True

    def unpause(self):
        """Restart tqdm timer from last print time."""
        if self.disable:
            return
        cur_t = self._time()
        self.start_t += cur_t - self.last_print_t
        self.last_print_t = cur_t

    def reset(self, total=None):
        """
        Resets to 0 iterations for repeated use.

        Consider combining with `leave=True`.

        Parameters
        ----------
        total  : int or float, optional. Total to use for the new bar.
        """
        self.n = 0
        if total is not None:
            self.total = total
        if self.disable:
            return
        self.last_print_n = 0
        self.last_print_t = self.start_t = self._time()
        self._ema_dn = EMA(self.smoothing)
        self._ema_dt = EMA(self.smoothing)
        self._ema_miniters = EMA(self.smoothing)
        self.refresh()

    def set_description(self, desc=None, refresh=True):
        """
        Set/modify description of the progress bar.

        Parameters
        ----------
        desc  : str, optional
        refresh  : bool, optional
            Forces refresh [default: True].
        """
        self.desc = desc + ': ' if desc else ''
        if refresh:
            self.refresh()

    def set_description_str(self, desc=None, refresh=True):
        """Set/modify description without ': ' appended."""
        self.desc = desc or ''
        if refresh:
            self.refresh()

    def set_postfix(self, ordered_dict=None, refresh=True, **kwargs):
        """
        Set/modify postfix (additional stats)
        with automatic formatting based on datatype.

        Parameters
        ----------
        ordered_dict  : dict or OrderedDict, optional
        refresh  : bool, optional
            Forces refresh [default: True].
        kwargs  : dict, optional
        """
        # Sort in alphabetical order to be more deterministic
        postfix = OrderedDict([] if ordered_dict is None else ordered_dict)
        for key in sorted(kwargs.keys()):
            postfix[key] = kwargs[key]
        # Preprocess stats according to datatype
        for key in postfix.keys():
            # Number: limit the length of the string
            if isinstance(postfix[key], Number):
                postfix[key] = self.format_num(postfix[key])
            # Else for any other type, try to get the string conversion
            elif not isinstance(postfix[key], str):
                postfix[key] = str(postfix[key])
            # Else if it's a string, don't need to preprocess anything
        # Stitch together to get the final postfix
        self.postfix = ', '.join(key + '=' + postfix[key].strip()
                                 for key in postfix.keys())
        if refresh:
            self.refresh()

    def set_postfix_str(self, s='', refresh=True):
        """
        Postfix without dictionary expansion, similar to prefix handling.
        """
        self.postfix = str(s)
        if refresh:
            self.refresh()

    def moveto(self, n):
        # TODO: private method
        self.fp.write('\n' * n + _term_move_up() * -n)
        getattr(self.fp, 'flush', lambda: None)()

    @property
    def format_dict(self):
        """Public API for read-only member access."""
        if self.disable and not hasattr(self, 'unit'):
            return defaultdict(lambda: None, {
                'n': self.n, 'total': self.total, 'elapsed': 0, 'unit': 'it'})
        if self.dynamic_ncols:
            self.ncols, self.nrows = self.dynamic_ncols(self.fp)
        return {
            'n': self.n, 'total': self.total,
            'elapsed': self._time() - self.start_t if hasattr(self, 'start_t') else 0,
            'ncols': self.ncols, 'nrows': self.nrows, 'prefix': self.desc,
            'ascii': self.ascii, 'unit': self.unit, 'unit_scale': self.unit_scale,
            'rate': self._ema_dn() / self._ema_dt() if self._ema_dt() else None,
            'bar_format': self.bar_format, 'postfix': self.postfix,
            'unit_divisor': self.unit_divisor, 'initial': self.initial,
            'colour': self.colour}

    def display(self, msg=None, pos=None):
        """
        Use `self.sp` to display `msg` in the specified `pos`.

        Consider overloading this function when inheriting to use e.g.:
        `self.some_frontend(**self.format_dict)` instead of `self.sp`.

        Parameters
        ----------
        msg  : str, optional. What to display (default: `repr(self)`).
        pos  : int, optional. Position to `moveto`
          (default: `abs(self.pos)`).
        """
        if pos is None:
            pos = abs(self.pos)

        nrows = self.nrows or 20
        if pos >= nrows - 1:
            if pos >= nrows:
                return False
            if msg or msg is None:  # override at `nrows - 1`
                msg = " ... (more hidden) ..."

        if not hasattr(self, "sp"):
            raise TqdmDeprecationWarning(
                "Please use `tqdm.gui.tqdm(...)`"
                " instead of `tqdm(..., gui=True)`\n",
                fp_write=getattr(self.fp, 'write', sys.stderr.write))

        if pos:
            self.moveto(pos)
        self.sp(self.__str__() if msg is None else msg)
        if pos:
            self.moveto(-pos)
        return True

    @classmethod
    @contextmanager
    def wrapattr(cls, stream, method, total=None, bytes=True, **tqdm_kwargs):
        """
        stream  : file-like object.
        method  : str, "read" or "write". The result of `read()` and
            the first argument of `write()` should have a `len()`.

        >>> with tqdm.wrapattr(file_obj, "read", total=file_obj.size) as fobj:
        ...     while True:
        ...         chunk = fobj.read(chunk_size)
        ...         if not chunk:
        ...             break
        """
        with cls(total=total, **tqdm_kwargs) as t:
            if bytes:
                t.unit = "B"
                t.unit_scale = True
                t.unit_divisor = 1024
            yield CallbackIOWrapper(t.update, stream, method)


def trange(*args, **kwargs):
    """Shortcut for tqdm(range(*args), **kwargs)."""
    return tqdm(range(*args), **kwargs)

# === NexusCore/openenv\Lib\site-packages\tornado\test\httpserver_test.py ===
from tornado import gen, netutil
from tornado.escape import (
    json_decode,
    json_encode,
    utf8,
    _unicode,
    recursive_unicode,
    native_str,
)
from tornado.http1connection import HTTP1Connection
from tornado.httpclient import HTTPError
from tornado.httpserver import HTTPServer
from tornado.httputil import (
    HTTPHeaders,
    HTTPMessageDelegate,
    HTTPServerConnectionDelegate,
    ResponseStartLine,
)
from tornado.iostream import IOStream
from tornado.locks import Event
from tornado.log import gen_log, app_log
from tornado.simple_httpclient import SimpleAsyncHTTPClient
from tornado.testing import (
    AsyncHTTPTestCase,
    AsyncHTTPSTestCase,
    AsyncTestCase,
    ExpectLog,
    gen_test,
)
from tornado.test.util import abstract_base_test
from tornado.web import Application, RequestHandler, stream_request_body

from contextlib import closing, contextmanager
import datetime
import gzip
import logging
import os
import shutil
import socket
import ssl
import sys
import tempfile
import textwrap
import unittest
import urllib.parse
import uuid
from io import BytesIO

import typing

if typing.TYPE_CHECKING:
    from typing import Dict, List  # noqa: F401


async def read_stream_body(stream):
    """Reads an HTTP response from `stream` and returns a tuple of its
    start_line, headers and body."""
    chunks = []

    class Delegate(HTTPMessageDelegate):
        def headers_received(self, start_line, headers):
            self.headers = headers
            self.start_line = start_line

        def data_received(self, chunk):
            chunks.append(chunk)

        def finish(self):
            conn.detach()  # type: ignore

    conn = HTTP1Connection(stream, True)
    delegate = Delegate()
    await conn.read_response(delegate)
    return delegate.start_line, delegate.headers, b"".join(chunks)


class HandlerBaseTestCase(AsyncHTTPTestCase):
    Handler = None

    def get_app(self):
        return Application([("/", self.__class__.Handler)])

    def fetch_json(self, *args, **kwargs):
        response = self.fetch(*args, **kwargs)
        response.rethrow()
        return json_decode(response.body)


class HelloWorldRequestHandler(RequestHandler):
    def initialize(self, protocol="http"):
        self.expected_protocol = protocol

    def get(self):
        if self.request.protocol != self.expected_protocol:
            raise Exception("unexpected protocol")
        self.finish("Hello world")

    def post(self):
        self.finish("Got %d bytes in POST" % len(self.request.body))


class SSLTest(AsyncHTTPSTestCase):
    def get_app(self):
        return Application([("/", HelloWorldRequestHandler, dict(protocol="https"))])

    def get_ssl_options(self):
        return dict(
            ssl_version=ssl.PROTOCOL_TLS_SERVER,
            **AsyncHTTPSTestCase.default_ssl_options(),
        )

    def test_ssl(self):
        response = self.fetch("/")
        self.assertEqual(response.body, b"Hello world")

    def test_large_post(self):
        response = self.fetch("/", method="POST", body="A" * 5000)
        self.assertEqual(response.body, b"Got 5000 bytes in POST")

    def test_non_ssl_request(self):
        # Make sure the server closes the connection when it gets a non-ssl
        # connection, rather than waiting for a timeout or otherwise
        # misbehaving.
        with ExpectLog(gen_log, "(SSL Error|uncaught exception)"):
            with ExpectLog(gen_log, "Uncaught exception", required=False):
                with self.assertRaises((IOError, HTTPError)):  # type: ignore
                    self.fetch(
                        self.get_url("/").replace("https:", "http:"),
                        request_timeout=3600,
                        connect_timeout=3600,
                        raise_error=True,
                    )

    def test_error_logging(self):
        # No stack traces are logged for SSL errors.
        with ExpectLog(gen_log, "SSL Error") as expect_log:
            with self.assertRaises((IOError, HTTPError)):  # type: ignore
                self.fetch(
                    self.get_url("/").replace("https:", "http:"), raise_error=True
                )
        self.assertFalse(expect_log.logged_stack)


class BadSSLOptionsTest(unittest.TestCase):
    def test_missing_arguments(self):
        application = Application()
        self.assertRaises(
            KeyError,
            HTTPServer,
            application,
            ssl_options={"keyfile": "/__missing__.crt"},
        )

    def test_missing_key(self):
        """A missing SSL key should cause an immediate exception."""

        application = Application()
        module_dir = os.path.dirname(__file__)
        existing_certificate = os.path.join(module_dir, "test.crt")
        existing_key = os.path.join(module_dir, "test.key")

        self.assertRaises(
            (ValueError, IOError),
            HTTPServer,
            application,
            ssl_options={"certfile": "/__mising__.crt"},
        )
        self.assertRaises(
            (ValueError, IOError),
            HTTPServer,
            application,
            ssl_options={
                "certfile": existing_certificate,
                "keyfile": "/__missing__.key",
            },
        )

        # This actually works because both files exist
        HTTPServer(
            application,
            ssl_options={"certfile": existing_certificate, "keyfile": existing_key},
        )


class MultipartTestHandler(RequestHandler):
    def post(self):
        self.finish(
            {
                "header": self.request.headers["X-Header-Encoding-Test"],
                "argument": self.get_argument("argument"),
                "filename": self.request.files["files"][0].filename,
                "filebody": _unicode(self.request.files["files"][0]["body"]),
            }
        )


# This test is also called from wsgi_test
class HTTPConnectionTest(AsyncHTTPTestCase):
    def get_handlers(self):
        return [
            ("/multipart", MultipartTestHandler),
            ("/hello", HelloWorldRequestHandler),
        ]

    def get_app(self):
        return Application(self.get_handlers())

    def raw_fetch(self, headers, body, newline=b"\r\n"):
        with closing(IOStream(socket.socket())) as stream:
            self.io_loop.run_sync(
                lambda: stream.connect(("127.0.0.1", self.get_http_port()))
            )
            stream.write(
                newline.join(headers + [utf8("Content-Length: %d" % len(body))])
                + newline
                + newline
                + body
            )
            start_line, headers, body = self.io_loop.run_sync(
                lambda: read_stream_body(stream)
            )
            return body

    def test_multipart_form(self):
        # Encodings here are tricky:  Headers are latin1, bodies can be
        # anything (we use utf8 by default).
        response = self.raw_fetch(
            [
                b"POST /multipart HTTP/1.0",
                b"Content-Type: multipart/form-data; boundary=1234567890",
                b"X-Header-encoding-test: \xe9",
            ],
            b"\r\n".join(
                [
                    b"Content-Disposition: form-data; name=argument",
                    b"",
                    "\u00e1".encode(),
                    b"--1234567890",
                    'Content-Disposition: form-data; name="files"; filename="\u00f3"'.encode(),
                    b"",
                    "\u00fa".encode(),
                    b"--1234567890--",
                    b"",
                ]
            ),
        )
        data = json_decode(response)
        self.assertEqual("\u00e9", data["header"])
        self.assertEqual("\u00e1", data["argument"])
        self.assertEqual("\u00f3", data["filename"])
        self.assertEqual("\u00fa", data["filebody"])

    def test_newlines(self):
        # We support both CRLF and bare LF as line separators.
        for newline in (b"\r\n", b"\n"):
            response = self.raw_fetch([b"GET /hello HTTP/1.0"], b"", newline=newline)
            self.assertEqual(response, b"Hello world")

    @gen_test
    def test_100_continue(self):
        # Run through a 100-continue interaction by hand:
        # When given Expect: 100-continue, we get a 100 response after the
        # headers, and then the real response after the body.
        stream = IOStream(socket.socket())
        yield stream.connect(("127.0.0.1", self.get_http_port()))
        yield stream.write(
            b"\r\n".join(
                [
                    b"POST /hello HTTP/1.1",
                    b"Host: 127.0.0.1",
                    b"Content-Length: 1024",
                    b"Expect: 100-continue",
                    b"Connection: close",
                    b"\r\n",
                ]
            )
        )
        data = yield stream.read_until(b"\r\n\r\n")
        self.assertTrue(data.startswith(b"HTTP/1.1 100 "), data)
        stream.write(b"a" * 1024)
        first_line = yield stream.read_until(b"\r\n")
        self.assertTrue(first_line.startswith(b"HTTP/1.1 200"), first_line)
        header_data = yield stream.read_until(b"\r\n\r\n")
        headers = HTTPHeaders.parse(native_str(header_data.decode("latin1")))
        body = yield stream.read_bytes(int(headers["Content-Length"]))
        self.assertEqual(body, b"Got 1024 bytes in POST")
        stream.close()


class EchoHandler(RequestHandler):
    def get(self):
        self.write(recursive_unicode(self.request.arguments))

    def post(self):
        self.write(recursive_unicode(self.request.arguments))


class TypeCheckHandler(RequestHandler):
    def prepare(self):
        self.errors = {}  # type: Dict[str, str]
        fields = [
            ("method", str),
            ("uri", str),
            ("version", str),
            ("remote_ip", str),
            ("protocol", str),
            ("host", str),
            ("path", str),
            ("query", str),
        ]
        for field, expected_type in fields:
            self.check_type(field, getattr(self.request, field), expected_type)

        self.check_type("header_key", list(self.request.headers.keys())[0], str)
        self.check_type("header_value", list(self.request.headers.values())[0], str)

        self.check_type("cookie_key", list(self.request.cookies.keys())[0], str)
        self.check_type(
            "cookie_value", list(self.request.cookies.values())[0].value, str
        )
        # secure cookies

        self.check_type("arg_key", list(self.request.arguments.keys())[0], str)
        self.check_type("arg_value", list(self.request.arguments.values())[0][0], bytes)

    def post(self):
        self.check_type("body", self.request.body, bytes)
        self.write(self.errors)

    def get(self):
        self.write(self.errors)

    def check_type(self, name, obj, expected_type):
        actual_type = type(obj)
        if expected_type != actual_type:
            self.errors[name] = f"expected {expected_type}, got {actual_type}"


class PostEchoHandler(RequestHandler):
    def post(self, *path_args):
        self.write(dict(echo=self.get_argument("data")))


class PostEchoGBKHandler(PostEchoHandler):
    def decode_argument(self, value, name=None):
        try:
            return value.decode("gbk")
        except Exception:
            raise HTTPError(400, "invalid gbk bytes: %r" % value)


class HTTPServerTest(AsyncHTTPTestCase):
    def get_app(self):
        return Application(
            [
                ("/echo", EchoHandler),
                ("/typecheck", TypeCheckHandler),
                ("//doubleslash", EchoHandler),
                ("/post_utf8", PostEchoHandler),
                ("/post_gbk", PostEchoGBKHandler),
            ]
        )

    def test_query_string_encoding(self):
        response = self.fetch("/echo?foo=%C3%A9")
        data = json_decode(response.body)
        self.assertEqual(data, {"foo": ["\u00e9"]})

    def test_empty_query_string(self):
        response = self.fetch("/echo?foo=&foo=")
        data = json_decode(response.body)
        self.assertEqual(data, {"foo": ["", ""]})

    def test_empty_post_parameters(self):
        response = self.fetch("/echo", method="POST", body="foo=&bar=")
        data = json_decode(response.body)
        self.assertEqual(data, {"foo": [""], "bar": [""]})

    def test_types(self):
        headers = {"Cookie": "foo=bar"}
        response = self.fetch("/typecheck?foo=bar", headers=headers)
        data = json_decode(response.body)
        self.assertEqual(data, {})

        response = self.fetch(
            "/typecheck", method="POST", body="foo=bar", headers=headers
        )
        data = json_decode(response.body)
        self.assertEqual(data, {})

    def test_double_slash(self):
        # urlparse.urlsplit (which tornado.httpserver used to use
        # incorrectly) would parse paths beginning with "//" as
        # protocol-relative urls.
        response = self.fetch("//doubleslash")
        self.assertEqual(200, response.code)
        self.assertEqual(json_decode(response.body), {})

    def test_post_encodings(self):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        uni_text = "chinese: \u5f20\u4e09"
        for enc in ("utf8", "gbk"):
            for quote in (True, False):
                with self.subTest(enc=enc, quote=quote):
                    bin_text = uni_text.encode(enc)
                    if quote:
                        bin_text = urllib.parse.quote(bin_text).encode("ascii")
                    response = self.fetch(
                        "/post_" + enc,
                        method="POST",
                        headers=headers,
                        body=(b"data=" + bin_text),
                    )
                    self.assertEqual(json_decode(response.body), {"echo": uni_text})


class HTTPServerRawTest(AsyncHTTPTestCase):
    def get_app(self):
        return Application([("/echo", EchoHandler)])

    def setUp(self):
        super().setUp()
        self.stream = IOStream(socket.socket())
        self.io_loop.run_sync(
            lambda: self.stream.connect(("127.0.0.1", self.get_http_port()))
        )

    def tearDown(self):
        self.stream.close()
        super().tearDown()

    def test_empty_request(self):
        self.stream.close()
        self.io_loop.add_timeout(datetime.timedelta(seconds=0.001), self.stop)
        self.wait()

    def test_malformed_first_line_response(self):
        with ExpectLog(gen_log, ".*Malformed HTTP request line", level=logging.INFO):
            self.stream.write(b"asdf\r\n\r\n")
            start_line, headers, response = self.io_loop.run_sync(
                lambda: read_stream_body(self.stream)
            )
            self.assertEqual("HTTP/1.1", start_line.version)
            self.assertEqual(400, start_line.code)
            self.assertEqual("Bad Request", start_line.reason)

    def test_malformed_first_line_log(self):
        with ExpectLog(gen_log, ".*Malformed HTTP request line", level=logging.INFO):
            self.stream.write(b"asdf\r\n\r\n")
            # TODO: need an async version of ExpectLog so we don't need
            # hard-coded timeouts here.
            self.io_loop.add_timeout(datetime.timedelta(seconds=0.05), self.stop)
            self.wait()

    def test_malformed_headers(self):
        with ExpectLog(
            gen_log,
            ".*Malformed HTTP message.*no colon in header line",
            level=logging.INFO,
        ):
            self.stream.write(b"GET / HTTP/1.0\r\nasdf\r\n\r\n")
            self.io_loop.add_timeout(datetime.timedelta(seconds=0.05), self.stop)
            self.wait()

    def test_chunked_request_body(self):
        # Chunked requests are not widely supported and we don't have a way
        # to generate them in AsyncHTTPClient, but HTTPServer will read them.
        self.stream.write(
            b"""\
POST /echo HTTP/1.1
Host: 127.0.0.1
Transfer-Encoding: chunked
Content-Type: application/x-www-form-urlencoded

4
foo=
3
bar
0

""".replace(
                b"\n", b"\r\n"
            )
        )
        start_line, headers, response = self.io_loop.run_sync(
            lambda: read_stream_body(self.stream)
        )
        self.assertEqual(json_decode(response), {"foo": ["bar"]})

    def test_chunked_request_uppercase(self):
        # As per RFC 2616 section 3.6, "Transfer-Encoding" header's value is
        # case-insensitive.
        self.stream.write(
            b"""\
POST /echo HTTP/1.1
Host: 127.0.0.1
Transfer-Encoding: Chunked
Content-Type: application/x-www-form-urlencoded

4
foo=
3
bar
0

""".replace(
                b"\n", b"\r\n"
            )
        )
        start_line, headers, response = self.io_loop.run_sync(
            lambda: read_stream_body(self.stream)
        )
        self.assertEqual(json_decode(response), {"foo": ["bar"]})

    def test_chunked_request_body_invalid_size(self):
        # Only hex digits are allowed in chunk sizes. Python's int() function
        # also accepts underscores, so make sure we reject them here.
        self.stream.write(
            b"""\
POST /echo HTTP/1.1
Host: 127.0.0.1
Transfer-Encoding: chunked

1_a
1234567890abcdef1234567890
0

""".replace(
                b"\n", b"\r\n"
            )
        )
        with ExpectLog(gen_log, ".*invalid chunk size", level=logging.INFO):
            start_line, headers, response = self.io_loop.run_sync(
                lambda: read_stream_body(self.stream)
            )
        self.assertEqual(400, start_line.code)

    def test_chunked_request_body_duplicate_header(self):
        # Repeated Transfer-Encoding headers should be an error (and not confuse
        # the chunked-encoding detection to mess up framing).
        self.stream.write(
            b"""\
POST /echo HTTP/1.1
Host: 127.0.0.1
Transfer-Encoding: chunked
Transfer-encoding: chunked

2
ok
0

"""
        )
        with ExpectLog(
            gen_log,
            ".*Unsupported Transfer-Encoding chunked,chunked",
            level=logging.INFO,
        ):
            start_line, headers, response = self.io_loop.run_sync(
                lambda: read_stream_body(self.stream)
            )
        self.assertEqual(400, start_line.code)

    def test_chunked_request_body_unsupported_transfer_encoding(self):
        # We don't support transfer-encodings other than chunked.
        self.stream.write(
            b"""\
POST /echo HTTP/1.1
Host: 127.0.0.1
Transfer-Encoding: gzip, chunked

2
ok
0

"""
        )
        with ExpectLog(
            gen_log, ".*Unsupported Transfer-Encoding gzip, chunked", level=logging.INFO
        ):
            start_line, headers, response = self.io_loop.run_sync(
                lambda: read_stream_body(self.stream)
            )
        self.assertEqual(400, start_line.code)

    def test_chunked_request_body_transfer_encoding_and_content_length(self):
        # Transfer-encoding and content-length are mutually exclusive
        self.stream.write(
            b"""\
POST /echo HTTP/1.1
Host: 127.0.0.1
Transfer-Encoding: chunked
Content-Length: 2

2
ok
0

"""
        )
        with ExpectLog(
            gen_log,
            ".*Message with both Transfer-Encoding and Content-Length",
            level=logging.INFO,
        ):
            start_line, headers, response = self.io_loop.run_sync(
                lambda: read_stream_body(self.stream)
            )
        self.assertEqual(400, start_line.code)

    @gen_test
    def test_invalid_content_length(self):
        # HTTP only allows decimal digits in content-length. Make sure we don't
        # accept anything else, with special attention to things accepted by the
        # python int() function (leading plus signs and internal underscores).
        test_cases = [
            ("alphabetic", "foo"),
            ("leading plus", "+10"),
            ("internal underscore", "1_0"),
        ]
        for name, value in test_cases:
            with self.subTest(name=name), closing(IOStream(socket.socket())) as stream:
                with ExpectLog(
                    gen_log,
                    ".*Only integer Content-Length is allowed",
                    level=logging.INFO,
                ):
                    yield stream.connect(("127.0.0.1", self.get_http_port()))
                    stream.write(
                        utf8(
                            textwrap.dedent(
                                f"""\
                            POST /echo HTTP/1.1
                            Host: 127.0.0.1
                            Content-Length: {value}
                            Connection: close

                            1234567890
                            """
                            ).replace("\n", "\r\n")
                        )
                    )
                    yield stream.read_until_close()

    @gen_test
    def test_invalid_methods(self):
        # RFC 9110 distinguishes between syntactically invalid methods and those that are
        # valid but unknown. The former must give a 400 status code, while the latter should
        # give a 405.
        test_cases = [
            ("FOO", 405, None),
            ("FOO,BAR", 400, ".*Malformed HTTP request line"),
        ]
        for method, code, log_msg in test_cases:
            if log_msg is not None:
                expect_log = ExpectLog(gen_log, log_msg, level=logging.INFO)
            else:

                @contextmanager
                def noop_context():
                    yield

                expect_log = noop_context()  # type: ignore
            with (
                self.subTest(method=method),
                closing(IOStream(socket.socket())) as stream,
                expect_log,
            ):
                yield stream.connect(("127.0.0.1", self.get_http_port()))
                stream.write(utf8(f"{method} /echo HTTP/1.1\r\nHost:127.0.0.1\r\n\r\n"))
                resp = yield stream.read_until(b"\r\n\r\n")
                self.assertTrue(
                    resp.startswith(b"HTTP/1.1 %d" % code),
                    f"expected status code {code} in {resp!r}",
                )


class XHeaderTest(HandlerBaseTestCase):
    class Handler(RequestHandler):
        def get(self):
            self.set_header("request-version", self.request.version)
            self.write(
                dict(
                    remote_ip=self.request.remote_ip,
                    remote_protocol=self.request.protocol,
                )
            )

    def get_httpserver_options(self):
        return dict(xheaders=True, trusted_downstream=["5.5.5.5"])

    def test_ip_headers(self):
        self.assertEqual(self.fetch_json("/")["remote_ip"], "127.0.0.1")

        valid_ipv4 = {"X-Real-IP": "4.4.4.4"}
        self.assertEqual(
            self.fetch_json("/", headers=valid_ipv4)["remote_ip"], "4.4.4.4"
        )

        valid_ipv4_list = {"X-Forwarded-For": "127.0.0.1, 4.4.4.4"}
        self.assertEqual(
            self.fetch_json("/", headers=valid_ipv4_list)["remote_ip"], "4.4.4.4"
        )

        valid_ipv6 = {"X-Real-IP": "2620:0:1cfe:face:b00c::3"}
        self.assertEqual(
            self.fetch_json("/", headers=valid_ipv6)["remote_ip"],
            "2620:0:1cfe:face:b00c::3",
        )

        valid_ipv6_list = {"X-Forwarded-For": "::1, 2620:0:1cfe:face:b00c::3"}
        self.assertEqual(
            self.fetch_json("/", headers=valid_ipv6_list)["remote_ip"],
            "2620:0:1cfe:face:b00c::3",
        )

        invalid_chars = {"X-Real-IP": "4.4.4.4<script>"}
        self.assertEqual(
            self.fetch_json("/", headers=invalid_chars)["remote_ip"], "127.0.0.1"
        )

        invalid_chars_list = {"X-Forwarded-For": "4.4.4.4, 5.5.5.5<script>"}
        self.assertEqual(
            self.fetch_json("/", headers=invalid_chars_list)["remote_ip"], "127.0.0.1"
        )

        invalid_host = {"X-Real-IP": "www.google.com"}
        self.assertEqual(
            self.fetch_json("/", headers=invalid_host)["remote_ip"], "127.0.0.1"
        )

    def test_trusted_downstream(self):
        valid_ipv4_list = {"X-Forwarded-For": "127.0.0.1, 4.4.4.4, 5.5.5.5"}
        resp = self.fetch("/", headers=valid_ipv4_list)
        if resp.headers["request-version"].startswith("HTTP/2"):
            # This is a hack - there's nothing that fundamentally requires http/1
            # here but tornado_http2 doesn't support it yet.
            self.skipTest("requires HTTP/1.x")
        result = json_decode(resp.body)
        self.assertEqual(result["remote_ip"], "4.4.4.4")

    def test_scheme_headers(self):
        self.assertEqual(self.fetch_json("/")["remote_protocol"], "http")

        https_scheme = {"X-Scheme": "https"}
        self.assertEqual(
            self.fetch_json("/", headers=https_scheme)["remote_protocol"], "https"
        )

        https_forwarded = {"X-Forwarded-Proto": "https"}
        self.assertEqual(
            self.fetch_json("/", headers=https_forwarded)["remote_protocol"], "https"
        )

        https_multi_forwarded = {"X-Forwarded-Proto": "https , http"}
        self.assertEqual(
            self.fetch_json("/", headers=https_multi_forwarded)["remote_protocol"],
            "http",
        )

        http_multi_forwarded = {"X-Forwarded-Proto": "http,https"}
        self.assertEqual(
            self.fetch_json("/", headers=http_multi_forwarded)["remote_protocol"],
            "https",
        )

        bad_forwarded = {"X-Forwarded-Proto": "unknown"}
        self.assertEqual(
            self.fetch_json("/", headers=bad_forwarded)["remote_protocol"], "http"
        )


class SSLXHeaderTest(AsyncHTTPSTestCase, HandlerBaseTestCase):
    def get_app(self):
        return Application([("/", XHeaderTest.Handler)])

    def get_httpserver_options(self):
        output = super().get_httpserver_options()
        output["xheaders"] = True
        return output

    def test_request_without_xprotocol(self):
        self.assertEqual(self.fetch_json("/")["remote_protocol"], "https")

        http_scheme = {"X-Scheme": "http"}
        self.assertEqual(
            self.fetch_json("/", headers=http_scheme)["remote_protocol"], "http"
        )

        bad_scheme = {"X-Scheme": "unknown"}
        self.assertEqual(
            self.fetch_json("/", headers=bad_scheme)["remote_protocol"], "https"
        )


class ManualProtocolTest(HandlerBaseTestCase):
    class Handler(RequestHandler):
        def get(self):
            self.write(dict(protocol=self.request.protocol))

    def get_httpserver_options(self):
        return dict(protocol="https")

    def test_manual_protocol(self):
        self.assertEqual(self.fetch_json("/")["protocol"], "https")


@abstract_base_test
class UnixSocketTest(AsyncTestCase):
    """HTTPServers can listen on Unix sockets too.

    Why would you want to do this?  Nginx can proxy to backends listening
    on unix sockets, for one thing (and managing a namespace for unix
    sockets can be easier than managing a bunch of TCP port numbers).

    Unfortunately, there's no way to specify a unix socket in a url for
    an HTTP client, so we have to test this by hand.
    """

    address = ""

    def setUp(self):
        super().setUp()
        app = Application([("/hello", HelloWorldRequestHandler)])
        self.server = HTTPServer(app)
        self.server.add_socket(netutil.bind_unix_socket(self.address))

    def tearDown(self):
        self.io_loop.run_sync(self.server.close_all_connections)
        self.server.stop()
        super().tearDown()

    @gen_test
    def test_unix_socket(self):
        with closing(IOStream(socket.socket(socket.AF_UNIX))) as stream:
            stream.connect(self.address)
            stream.write(b"GET /hello HTTP/1.0\r\n\r\n")
            response = yield stream.read_until(b"\r\n")
            self.assertEqual(response, b"HTTP/1.1 200 OK\r\n")
            header_data = yield stream.read_until(b"\r\n\r\n")
            headers = HTTPHeaders.parse(header_data.decode("latin1"))
            body = yield stream.read_bytes(int(headers["Content-Length"]))
            self.assertEqual(body, b"Hello world")

    @gen_test
    def test_unix_socket_bad_request(self):
        # Unix sockets don't have remote addresses so they just return an
        # empty string.
        with ExpectLog(gen_log, "Malformed HTTP message from", level=logging.INFO):
            with closing(IOStream(socket.socket(socket.AF_UNIX))) as stream:
                stream.connect(self.address)
                stream.write(b"garbage\r\n\r\n")
                response = yield stream.read_until_close()
        self.assertEqual(response, b"HTTP/1.1 400 Bad Request\r\n\r\n")


@unittest.skipIf(
    not hasattr(socket, "AF_UNIX") or sys.platform == "cygwin",
    "unix sockets not supported on this platform",
)
class UnixSocketTestFile(UnixSocketTest):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.address = os.path.join(self.tmpdir, "test.sock")
        super().setUp()

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.tmpdir)


@unittest.skipIf(
    not (hasattr(socket, "AF_UNIX") and sys.platform.startswith("linux")),
    "abstract namespace unix sockets not supported on this platform",
)
class UnixSocketTestAbstract(UnixSocketTest):
    def setUp(self):
        self.address = "\0" + uuid.uuid4().hex
        super().setUp()


class KeepAliveTest(AsyncHTTPTestCase):
    """Tests various scenarios for HTTP 1.1 keep-alive support.

    These tests don't use AsyncHTTPClient because we want to control
    connection reuse and closing.
    """

    def get_app(self):
        class HelloHandler(RequestHandler):
            def get(self):
                self.finish("Hello world")

            def post(self):
                self.finish("Hello world")

        class LargeHandler(RequestHandler):
            def get(self):
                # 512KB should be bigger than the socket buffers so it will
                # be written out in chunks.
                self.write("".join(chr(i % 256) * 1024 for i in range(512)))

        class TransferEncodingChunkedHandler(RequestHandler):
            @gen.coroutine
            def head(self):
                self.write("Hello world")
                yield self.flush()

        class FinishOnCloseHandler(RequestHandler):
            def initialize(self, cleanup_event):
                self.cleanup_event = cleanup_event

            @gen.coroutine
            def get(self):
                self.flush()
                yield self.cleanup_event.wait()

            def on_connection_close(self):
                # This is not very realistic, but finishing the request
                # from the close callback has the right timing to mimic
                # some errors seen in the wild.
                self.finish("closed")

        self.cleanup_event = Event()
        return Application(
            [
                ("/", HelloHandler),
                ("/large", LargeHandler),
                ("/chunked", TransferEncodingChunkedHandler),
                (
                    "/finish_on_close",
                    FinishOnCloseHandler,
                    dict(cleanup_event=self.cleanup_event),
                ),
            ]
        )

    def setUp(self):
        super().setUp()
        self.http_version = b"HTTP/1.1"

    def tearDown(self):
        # We just closed the client side of the socket; let the IOLoop run
        # once to make sure the server side got the message.
        self.io_loop.add_timeout(datetime.timedelta(seconds=0.001), self.stop)
        self.wait()

        if hasattr(self, "stream"):
            self.stream.close()
        super().tearDown()

    # The next few methods are a crude manual http client
    @gen.coroutine
    def connect(self):
        self.stream = IOStream(socket.socket())
        yield self.stream.connect(("127.0.0.1", self.get_http_port()))

    @gen.coroutine
    def read_headers(self):
        first_line = yield self.stream.read_until(b"\r\n")
        self.assertTrue(first_line.startswith(b"HTTP/1.1 200"), first_line)
        header_bytes = yield self.stream.read_until(b"\r\n\r\n")
        headers = HTTPHeaders.parse(header_bytes.decode("latin1"))
        raise gen.Return(headers)

    @gen.coroutine
    def read_response(self):
        self.headers = yield self.read_headers()
        body = yield self.stream.read_bytes(int(self.headers["Content-Length"]))
        self.assertEqual(b"Hello world", body)

    def close(self):
        self.stream.close()
        del self.stream

    @gen_test
    def test_two_requests(self):
        yield self.connect()
        self.stream.write(b"GET / HTTP/1.1\r\nHost:127.0.0.1\r\n\r\n")
        yield self.read_response()
        self.stream.write(b"GET / HTTP/1.1\r\nHost:127.0.0.1\r\n\r\n")
        yield self.read_response()
        self.close()

    @gen_test
    def test_request_close(self):
        yield self.connect()
        self.stream.write(
            b"GET / HTTP/1.1\r\nHost:127.0.0.1\r\nConnection: close\r\n\r\n"
        )
        yield self.read_response()
        data = yield self.stream.read_until_close()
        self.assertTrue(not data)
        self.assertEqual(self.headers["Connection"], "close")
        self.close()

    # keepalive is supported for http 1.0 too, but it's opt-in
    @gen_test
    def test_http10(self):
        self.http_version = b"HTTP/1.0"
        yield self.connect()
        self.stream.write(b"GET / HTTP/1.0\r\n\r\n")
        yield self.read_response()
        data = yield self.stream.read_until_close()
        self.assertFalse(data)
        self.assertNotIn("Connection", self.headers)
        self.close()

    @gen_test
    def test_http10_keepalive(self):
        self.http_version = b"HTTP/1.0"
        yield self.connect()
        self.stream.write(b"GET / HTTP/1.0\r\nConnection: keep-alive\r\n\r\n")
        yield self.read_response()
        self.assertEqual(self.headers["Connection"], "Keep-Alive")
        self.stream.write(b"GET / HTTP/1.0\r\nConnection: keep-alive\r\n\r\n")
        yield self.read_response()
        self.assertEqual(self.headers["Connection"], "Keep-Alive")
        self.close()

    @gen_test
    def test_http10_keepalive_extra_crlf(self):
        self.http_version = b"HTTP/1.0"
        yield self.connect()
        self.stream.write(b"GET / HTTP/1.0\r\nConnection: keep-alive\r\n\r\n\r\n")
        yield self.read_response()
        self.assertEqual(self.headers["Connection"], "Keep-Alive")
        self.stream.write(b"GET / HTTP/1.0\r\nConnection: keep-alive\r\n\r\n")
        yield self.read_response()
        self.assertEqual(self.headers["Connection"], "Keep-Alive")
        self.close()

    @gen_test
    def test_pipelined_requests(self):
        yield self.connect()
        self.stream.write(
            b"GET / HTTP/1.1\r\nHost:127.0.0.1\r\n\r\nGET / HTTP/1.1\r\nHost:127.0.0.1\r\n\r\n"
        )
        yield self.read_response()
        yield self.read_response()
        self.close()

    @gen_test
    def test_pipelined_cancel(self):
        yield self.connect()
        self.stream.write(
            b"GET / HTTP/1.1\r\nHost:127.0.0.1\r\n\r\nGET / HTTP/1.1\r\nHost:127.0.0.1\r\n\r\n"
        )
        # only read once
        yield self.read_response()
        self.close()

    @gen_test
    def test_cancel_during_download(self):
        yield self.connect()
        self.stream.write(b"GET /large HTTP/1.1\r\nHost:127.0.0.1\r\n\r\n")
        yield self.read_headers()
        yield self.stream.read_bytes(1024)
        self.close()

    @gen_test
    def test_finish_while_closed(self):
        yield self.connect()
        self.stream.write(b"GET /finish_on_close HTTP/1.1\r\nHost:127.0.0.1\r\n\r\n")
        yield self.read_headers()
        self.close()
        # Let the hanging coroutine clean up after itself
        self.cleanup_event.set()

    @gen_test
    def test_keepalive_chunked(self):
        self.http_version = b"HTTP/1.0"
        yield self.connect()
        self.stream.write(
            b"POST / HTTP/1.0\r\n"
            b"Connection: keep-alive\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"\r\n"
            b"0\r\n"
            b"\r\n"
        )
        yield self.read_response()
        self.assertEqual(self.headers["Connection"], "Keep-Alive")
        self.stream.write(b"GET / HTTP/1.0\r\nConnection: keep-alive\r\n\r\n")
        yield self.read_response()
        self.assertEqual(self.headers["Connection"], "Keep-Alive")
        self.close()

    @gen_test
    def test_keepalive_chunked_head_no_body(self):
        yield self.connect()
        self.stream.write(b"HEAD /chunked HTTP/1.1\r\nHost:127.0.0.1\r\n\r\n")
        yield self.read_headers()

        self.stream.write(b"HEAD /chunked HTTP/1.1\r\nHost:127.0.0.1\r\n\r\n")
        yield self.read_headers()
        self.close()


class GzipBaseTest(AsyncHTTPTestCase):
    def get_app(self):
        return Application([("/", EchoHandler)])

    def post_gzip(self, body):
        bytesio = BytesIO()
        gzip_file = gzip.GzipFile(mode="w", fileobj=bytesio)
        gzip_file.write(utf8(body))
        gzip_file.close()
        compressed_body = bytesio.getvalue()
        return self.fetch(
            "/",
            method="POST",
            body=compressed_body,
            headers={"Content-Encoding": "gzip"},
        )

    def test_uncompressed(self):
        response = self.fetch("/", method="POST", body="foo=bar")
        self.assertEqual(json_decode(response.body), {"foo": ["bar"]})


class GzipTest(GzipBaseTest, AsyncHTTPTestCase):
    def get_httpserver_options(self):
        return dict(decompress_request=True)

    def test_gzip(self):
        response = self.post_gzip("foo=bar")
        self.assertEqual(json_decode(response.body), {"foo": ["bar"]})

    def test_gzip_case_insensitive(self):
        # https://datatracker.ietf.org/doc/html/rfc7231#section-3.1.2.1
        bytesio = BytesIO()
        gzip_file = gzip.GzipFile(mode="w", fileobj=bytesio)
        gzip_file.write(utf8("foo=bar"))
        gzip_file.close()
        compressed_body = bytesio.getvalue()
        response = self.fetch(
            "/",
            method="POST",
            body=compressed_body,
            headers={"Content-Encoding": "GZIP"},
        )
        self.assertEqual(json_decode(response.body), {"foo": ["bar"]})


class GzipUnsupportedTest(GzipBaseTest, AsyncHTTPTestCase):
    def test_gzip_unsupported(self):
        # Gzip support is opt-in; without it the server fails to parse
        # the body (but parsing form bodies is currently just a log message,
        # not a fatal error).
        with ExpectLog(gen_log, ".*Unsupported Content-Encoding"):
            response = self.post_gzip("foo=bar")
        self.assertEqual(response.code, 400)


class StreamingChunkSizeTest(AsyncHTTPTestCase):
    # 50 characters long, and repetitive so it can be compressed.
    BODY = b"01234567890123456789012345678901234567890123456789"
    CHUNK_SIZE = 16

    def get_http_client(self):
        # body_producer doesn't work on curl_httpclient, so override the
        # configured AsyncHTTPClient implementation.
        return SimpleAsyncHTTPClient()

    def get_httpserver_options(self):
        return dict(chunk_size=self.CHUNK_SIZE, decompress_request=True)

    class MessageDelegate(HTTPMessageDelegate):
        def __init__(self, connection):
            self.connection = connection

        def headers_received(self, start_line, headers):
            self.chunk_lengths = []  # type: List[int]

        def data_received(self, chunk):
            self.chunk_lengths.append(len(chunk))

        def finish(self):
            response_body = utf8(json_encode(self.chunk_lengths))
            self.connection.write_headers(
                ResponseStartLine("HTTP/1.1", 200, "OK"),
                HTTPHeaders({"Content-Length": str(len(response_body))}),
            )
            self.connection.write(response_body)
            self.connection.finish()

    def get_app(self):
        class App(HTTPServerConnectionDelegate):
            def start_request(self, server_conn, request_conn):
                return StreamingChunkSizeTest.MessageDelegate(request_conn)

        return App()

    def fetch_chunk_sizes(self, **kwargs):
        response = self.fetch("/", method="POST", **kwargs)
        response.rethrow()
        chunks = json_decode(response.body)
        self.assertEqual(len(self.BODY), sum(chunks))
        for chunk_size in chunks:
            self.assertLessEqual(
                chunk_size, self.CHUNK_SIZE, "oversized chunk: " + str(chunks)
            )
            self.assertGreater(chunk_size, 0, "empty chunk: " + str(chunks))
        return chunks

    def compress(self, body):
        bytesio = BytesIO()
        gzfile = gzip.GzipFile(mode="w", fileobj=bytesio)
        gzfile.write(body)
        gzfile.close()
        compressed = bytesio.getvalue()
        if len(compressed) >= len(body):
            raise Exception("body did not shrink when compressed")
        return compressed

    def test_regular_body(self):
        chunks = self.fetch_chunk_sizes(body=self.BODY)
        # Without compression we know exactly what to expect.
        self.assertEqual([16, 16, 16, 2], chunks)

    def test_compressed_body(self):
        self.fetch_chunk_sizes(
            body=self.compress(self.BODY), headers={"Content-Encoding": "gzip"}
        )
        # Compression creates irregular boundaries so the assertions
        # in fetch_chunk_sizes are as specific as we can get.

    def test_chunked_body(self):
        def body_producer(write):
            write(self.BODY[:20])
            write(self.BODY[20:])

        chunks = self.fetch_chunk_sizes(body_producer=body_producer)
        # HTTP chunk boundaries translate to application-visible breaks
        self.assertEqual([16, 4, 16, 14], chunks)

    def test_chunked_compressed(self):
        compressed = self.compress(self.BODY)
        self.assertGreater(len(compressed), 20)

        def body_producer(write):
            write(compressed[:20])
            write(compressed[20:])

        self.fetch_chunk_sizes(
            body_producer=body_producer, headers={"Content-Encoding": "gzip"}
        )


class InvalidOutputContentLengthTest(AsyncHTTPTestCase):
    class MessageDelegate(HTTPMessageDelegate):
        def __init__(self, connection):
            self.connection = connection

        def headers_received(self, start_line, headers):
            content_lengths = {
                "normal": "10",
                "alphabetic": "foo",
                "leading plus": "+10",
                "underscore": "1_0",
            }
            self.connection.write_headers(
                ResponseStartLine("HTTP/1.1", 200, "OK"),
                HTTPHeaders({"Content-Length": content_lengths[headers["x-test"]]}),
            )
            self.connection.write(b"1234567890")
            self.connection.finish()

    def get_app(self):
        class App(HTTPServerConnectionDelegate):
            def start_request(self, server_conn, request_conn):
                return InvalidOutputContentLengthTest.MessageDelegate(request_conn)

        return App()

    def test_invalid_output_content_length(self):
        with self.subTest("normal"):
            response = self.fetch("/", method="GET", headers={"x-test": "normal"})
            response.rethrow()
            self.assertEqual(response.body, b"1234567890")
        for test in ["alphabetic", "leading plus", "underscore"]:
            with self.subTest(test):
                # This log matching could be tighter but I think I'm already
                # over-testing here.
                with ExpectLog(app_log, "Uncaught exception"):
                    with self.assertRaises(HTTPError):
                        self.fetch("/", method="GET", headers={"x-test": test})


class MaxHeaderSizeTest(AsyncHTTPTestCase):
    def get_app(self):
        return Application([("/", HelloWorldRequestHandler)])

    def get_httpserver_options(self):
        return dict(max_header_size=1024)

    def test_small_headers(self):
        response = self.fetch("/", headers={"X-Filler": "a" * 100})
        response.rethrow()
        self.assertEqual(response.body, b"Hello world")

    def test_large_headers(self):
        with ExpectLog(gen_log, "Unsatisfiable read", required=False):
            try:
                self.fetch("/", headers={"X-Filler": "a" * 1000}, raise_error=True)
                self.fail("did not raise expected exception")
            except HTTPError as e:
                # 431 is "Request Header Fields Too Large", defined in RFC
                # 6585. However, many implementations just close the
                # connection in this case, resulting in a missing response.
                if e.response is not None:
                    self.assertIn(e.response.code, (431, 599))


class IdleTimeoutTest(AsyncHTTPTestCase):
    def get_app(self):
        return Application([("/", HelloWorldRequestHandler)])

    def get_httpserver_options(self):
        return dict(idle_connection_timeout=0.1)

    def setUp(self):
        super().setUp()
        self.streams = []  # type: List[IOStream]

    def tearDown(self):
        super().tearDown()
        for stream in self.streams:
            stream.close()

    @gen.coroutine
    def connect(self):
        stream = IOStream(socket.socket())
        yield stream.connect(("127.0.0.1", self.get_http_port()))
        self.streams.append(stream)
        raise gen.Return(stream)

    @gen_test
    def test_unused_connection(self):
        stream = yield self.connect()
        event = Event()
        stream.set_close_callback(event.set)
        yield event.wait()

    @gen_test
    def test_idle_after_use(self):
        stream = yield self.connect()
        event = Event()
        stream.set_close_callback(event.set)

        # Use the connection twice to make sure keep-alives are working
        for i in range(2):
            stream.write(b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
            yield stream.read_until(b"\r\n\r\n")
            data = yield stream.read_bytes(11)
            self.assertEqual(data, b"Hello world")

        # Now let the timeout trigger and close the connection.
        yield event.wait()


class BodyLimitsTest(AsyncHTTPTestCase):
    def get_app(self):
        class BufferedHandler(RequestHandler):
            def put(self):
                self.write(str(len(self.request.body)))

        @stream_request_body
        class StreamingHandler(RequestHandler):
            def initialize(self):
                self.bytes_read = 0

            def prepare(self):
                conn = typing.cast(HTTP1Connection, self.request.connection)
                if "expected_size" in self.request.arguments:
                    conn.set_max_body_size(int(self.get_argument("expected_size")))
                if "body_timeout" in self.request.arguments:
                    conn.set_body_timeout(float(self.get_argument("body_timeout")))

            def data_received(self, data):
                self.bytes_read += len(data)

            def put(self):
                self.write(str(self.bytes_read))

        return Application(
            [("/buffered", BufferedHandler), ("/streaming", StreamingHandler)]
        )

    def get_httpserver_options(self):
        return dict(body_timeout=3600, max_body_size=4096)

    def get_http_client(self):
        # body_producer doesn't work on curl_httpclient, so override the
        # configured AsyncHTTPClient implementation.
        return SimpleAsyncHTTPClient()

    def test_small_body(self):
        response = self.fetch("/buffered", method="PUT", body=b"a" * 4096)
        self.assertEqual(response.body, b"4096")
        response = self.fetch("/streaming", method="PUT", body=b"a" * 4096)
        self.assertEqual(response.body, b"4096")

    def test_large_body_buffered(self):
        with ExpectLog(gen_log, ".*Content-Length too long", level=logging.INFO):
            response = self.fetch("/buffered", method="PUT", body=b"a" * 10240)
        self.assertEqual(response.code, 400)

    @unittest.skipIf(os.name == "nt", "flaky on windows")
    def test_large_body_buffered_chunked(self):
        # This test is flaky on windows for unknown reasons.
        with ExpectLog(gen_log, ".*chunked body too large", level=logging.INFO):
            response = self.fetch(
                "/buffered",
                method="PUT",
                body_producer=lambda write: write(b"a" * 10240),
            )
        self.assertEqual(response.code, 400)

    def test_large_body_streaming(self):
        with ExpectLog(gen_log, ".*Content-Length too long", level=logging.INFO):
            response = self.fetch("/streaming", method="PUT", body=b"a" * 10240)
        self.assertEqual(response.code, 400)

    @unittest.skipIf(os.name == "nt", "flaky on windows")
    def test_large_body_streaming_chunked(self):
        with ExpectLog(gen_log, ".*chunked body too large", level=logging.INFO):
            response = self.fetch(
                "/streaming",
                method="PUT",
                body_producer=lambda write: write(b"a" * 10240),
            )
        self.assertEqual(response.code, 400)

    def test_large_body_streaming_override(self):
        response = self.fetch(
            "/streaming?expected_size=10240", method="PUT", body=b"a" * 10240
        )
        self.assertEqual(response.body, b"10240")

    def test_large_body_streaming_chunked_override(self):
        response = self.fetch(
            "/streaming?expected_size=10240",
            method="PUT",
            body_producer=lambda write: write(b"a" * 10240),
        )
        self.assertEqual(response.body, b"10240")

    @gen_test
    def test_timeout(self):
        stream = IOStream(socket.socket())
        try:
            yield stream.connect(("127.0.0.1", self.get_http_port()))
            # Use a raw stream because AsyncHTTPClient won't let us read a
            # response without finishing a body.
            stream.write(
                b"PUT /streaming?body_timeout=0.1 HTTP/1.0\r\n"
                b"Content-Length: 42\r\n\r\n"
            )
            with ExpectLog(gen_log, "Timeout reading body", level=logging.INFO):
                response = yield stream.read_until_close()
            self.assertEqual(response, b"")
        finally:
            stream.close()

    @gen_test
    def test_body_size_override_reset(self):
        # The max_body_size override is reset between requests.
        stream = IOStream(socket.socket())
        try:
            yield stream.connect(("127.0.0.1", self.get_http_port()))
            # Use a raw stream so we can make sure it's all on one connection.
            stream.write(
                b"PUT /streaming?expected_size=10240 HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Content-Length: 10240\r\n\r\n"
            )
            stream.write(b"a" * 10240)
            start_line, headers, response = yield read_stream_body(stream)
            self.assertEqual(response, b"10240")
            # Without the ?expected_size parameter, we get the old default value
            stream.write(
                b"PUT /streaming HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Content-Length: 10240\r\n\r\n"
            )
            with ExpectLog(gen_log, ".*Content-Length too long", level=logging.INFO):
                data = yield stream.read_until_close()
            self.assertEqual(data, b"HTTP/1.1 400 Bad Request\r\n\r\n")
        finally:
            stream.close()


class LegacyInterfaceTest(AsyncHTTPTestCase):
    def get_app(self):
        # The old request_callback interface does not implement the
        # delegate interface, and writes its response via request.write
        # instead of request.connection.write_headers.
        def handle_request(request):
            self.http1 = request.version.startswith("HTTP/1.")
            if not self.http1:
                # This test will be skipped if we're using HTTP/2,
                # so just close it out cleanly using the modern interface.
                request.connection.write_headers(
                    ResponseStartLine("", 200, "OK"), HTTPHeaders()
                )
                request.connection.finish()
                return
            message = b"Hello world"
            request.connection.write(
                utf8("HTTP/1.1 200 OK\r\n" "Content-Length: %d\r\n\r\n" % len(message))
            )
            request.connection.write(message)
            request.connection.finish()

        return handle_request

    def test_legacy_interface(self):
        response = self.fetch("/")
        if not self.http1:
            self.skipTest("requires HTTP/1.x")
        self.assertEqual(response.body, b"Hello world")

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\model_service\client.py ===
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
import os
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
    cast,
)
import warnings

from google.api_core import client_options as client_options_lib
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.exceptions import MutualTLSChannelError  # type: ignore
from google.auth.transport import mtls  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta import gapic_version as package_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore

from google.api_core import operation  # type: ignore
from google.api_core import operation_async  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import field_mask_pb2  # type: ignore
from google.protobuf import timestamp_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.services.model_service import pagers
from google.ai.generativelanguage_v1beta.types import tuned_model as gag_tuned_model
from google.ai.generativelanguage_v1beta.types import model, model_service
from google.ai.generativelanguage_v1beta.types import tuned_model

from .transports.base import DEFAULT_CLIENT_INFO, ModelServiceTransport
from .transports.grpc import ModelServiceGrpcTransport
from .transports.grpc_asyncio import ModelServiceGrpcAsyncIOTransport
from .transports.rest import ModelServiceRestTransport


class ModelServiceClientMeta(type):
    """Metaclass for the ModelService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = OrderedDict()  # type: Dict[str, Type[ModelServiceTransport]]
    _transport_registry["grpc"] = ModelServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = ModelServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = ModelServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[ModelServiceTransport]:
        """Returns an appropriate transport class.

        Args:
            label: The name of the desired transport. If none is
                provided, then the first transport in the registry is used.

        Returns:
            The transport class to use.
        """
        # If a specific transport is requested, return that one.
        if label:
            return cls._transport_registry[label]

        # No transport is requested; return the default (that is, the first one
        # in the dictionary).
        return next(iter(cls._transport_registry.values()))


class ModelServiceClient(metaclass=ModelServiceClientMeta):
    """Provides methods for getting metadata information about
    Generative Models.
    """

    @staticmethod
    def _get_default_mtls_endpoint(api_endpoint):
        """Converts api endpoint to mTLS endpoint.

        Convert "*.sandbox.googleapis.com" and "*.googleapis.com" to
        "*.mtls.sandbox.googleapis.com" and "*.mtls.googleapis.com" respectively.
        Args:
            api_endpoint (Optional[str]): the api endpoint to convert.
        Returns:
            str: converted mTLS api endpoint.
        """
        if not api_endpoint:
            return api_endpoint

        mtls_endpoint_re = re.compile(
            r"(?P<name>[^.]+)(?P<mtls>\.mtls)?(?P<sandbox>\.sandbox)?(?P<googledomain>\.googleapis\.com)?"
        )

        m = mtls_endpoint_re.match(api_endpoint)
        name, mtls, sandbox, googledomain = m.groups()
        if mtls or not googledomain:
            return api_endpoint

        if sandbox:
            return api_endpoint.replace(
                "sandbox.googleapis.com", "mtls.sandbox.googleapis.com"
            )

        return api_endpoint.replace(".googleapis.com", ".mtls.googleapis.com")

    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = "generativelanguage.googleapis.com"
    DEFAULT_MTLS_ENDPOINT = _get_default_mtls_endpoint.__func__(  # type: ignore
        DEFAULT_ENDPOINT
    )

    _DEFAULT_ENDPOINT_TEMPLATE = "generativelanguage.{UNIVERSE_DOMAIN}"
    _DEFAULT_UNIVERSE = "googleapis.com"

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            ModelServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_info(info)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

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
            ModelServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> ModelServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            ModelServiceTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def model_path(
        model: str,
    ) -> str:
        """Returns a fully-qualified model string."""
        return "models/{model}".format(
            model=model,
        )

    @staticmethod
    def parse_model_path(path: str) -> Dict[str, str]:
        """Parses a model path into its component segments."""
        m = re.match(r"^models/(?P<model>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def tuned_model_path(
        tuned_model: str,
    ) -> str:
        """Returns a fully-qualified tuned_model string."""
        return "tunedModels/{tuned_model}".format(
            tuned_model=tuned_model,
        )

    @staticmethod
    def parse_tuned_model_path(path: str) -> Dict[str, str]:
        """Parses a tuned_model path into its component segments."""
        m = re.match(r"^tunedModels/(?P<tuned_model>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_billing_account_path(
        billing_account: str,
    ) -> str:
        """Returns a fully-qualified billing_account string."""
        return "billingAccounts/{billing_account}".format(
            billing_account=billing_account,
        )

    @staticmethod
    def parse_common_billing_account_path(path: str) -> Dict[str, str]:
        """Parse a billing_account path into its component segments."""
        m = re.match(r"^billingAccounts/(?P<billing_account>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_folder_path(
        folder: str,
    ) -> str:
        """Returns a fully-qualified folder string."""
        return "folders/{folder}".format(
            folder=folder,
        )

    @staticmethod
    def parse_common_folder_path(path: str) -> Dict[str, str]:
        """Parse a folder path into its component segments."""
        m = re.match(r"^folders/(?P<folder>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_organization_path(
        organization: str,
    ) -> str:
        """Returns a fully-qualified organization string."""
        return "organizations/{organization}".format(
            organization=organization,
        )

    @staticmethod
    def parse_common_organization_path(path: str) -> Dict[str, str]:
        """Parse a organization path into its component segments."""
        m = re.match(r"^organizations/(?P<organization>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_project_path(
        project: str,
    ) -> str:
        """Returns a fully-qualified project string."""
        return "projects/{project}".format(
            project=project,
        )

    @staticmethod
    def parse_common_project_path(path: str) -> Dict[str, str]:
        """Parse a project path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_location_path(
        project: str,
        location: str,
    ) -> str:
        """Returns a fully-qualified location string."""
        return "projects/{project}/locations/{location}".format(
            project=project,
            location=location,
        )

    @staticmethod
    def parse_common_location_path(path: str) -> Dict[str, str]:
        """Parse a location path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)/locations/(?P<location>.+?)$", path)
        return m.groupdict() if m else {}

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[client_options_lib.ClientOptions] = None
    ):
        """Deprecated. Return the API endpoint and client cert source for mutual TLS.

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

        warnings.warn(
            "get_mtls_endpoint_and_cert_source is deprecated. Use the api_endpoint property instead.",
            DeprecationWarning,
        )
        if client_options is None:
            client_options = client_options_lib.ClientOptions()
        use_client_cert = os.getenv("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )

        # Figure out the client cert source to use.
        client_cert_source = None
        if use_client_cert == "true":
            if client_options.client_cert_source:
                client_cert_source = client_options.client_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()

        # Figure out which api endpoint to use.
        if client_options.api_endpoint is not None:
            api_endpoint = client_options.api_endpoint
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            api_endpoint = cls.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = cls.DEFAULT_ENDPOINT

        return api_endpoint, client_cert_source

    @staticmethod
    def _read_environment_variables():
        """Returns the environment variables used by the client.

        Returns:
            Tuple[bool, str, str]: returns the GOOGLE_API_USE_CLIENT_CERTIFICATE,
            GOOGLE_API_USE_MTLS_ENDPOINT, and GOOGLE_CLOUD_UNIVERSE_DOMAIN environment variables.

        Raises:
            ValueError: If GOOGLE_API_USE_CLIENT_CERTIFICATE is not
                any of ["true", "false"].
            google.auth.exceptions.MutualTLSChannelError: If GOOGLE_API_USE_MTLS_ENDPOINT
                is not any of ["auto", "never", "always"].
        """
        use_client_cert = os.getenv(
            "GOOGLE_API_USE_CLIENT_CERTIFICATE", "false"
        ).lower()
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto").lower()
        universe_domain_env = os.getenv("GOOGLE_CLOUD_UNIVERSE_DOMAIN")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )
        return use_client_cert == "true", use_mtls_endpoint, universe_domain_env

    @staticmethod
    def _get_client_cert_source(provided_cert_source, use_cert_flag):
        """Return the client cert source to be used by the client.

        Args:
            provided_cert_source (bytes): The client certificate source provided.
            use_cert_flag (bool): A flag indicating whether to use the client certificate.

        Returns:
            bytes or None: The client cert source to be used by the client.
        """
        client_cert_source = None
        if use_cert_flag:
            if provided_cert_source:
                client_cert_source = provided_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()
        return client_cert_source

    @staticmethod
    def _get_api_endpoint(
        api_override, client_cert_source, universe_domain, use_mtls_endpoint
    ):
        """Return the API endpoint used by the client.

        Args:
            api_override (str): The API endpoint override. If specified, this is always
                the return value of this function and the other arguments are not used.
            client_cert_source (bytes): The client certificate source used by the client.
            universe_domain (str): The universe domain used by the client.
            use_mtls_endpoint (str): How to use the mTLS endpoint, which depends also on the other parameters.
                Possible values are "always", "auto", or "never".

        Returns:
            str: The API endpoint to be used by the client.
        """
        if api_override is not None:
            api_endpoint = api_override
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            _default_universe = ModelServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = ModelServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = ModelServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
                UNIVERSE_DOMAIN=universe_domain
            )
        return api_endpoint

    @staticmethod
    def _get_universe_domain(
        client_universe_domain: Optional[str], universe_domain_env: Optional[str]
    ) -> str:
        """Return the universe domain used by the client.

        Args:
            client_universe_domain (Optional[str]): The universe domain configured via the client options.
            universe_domain_env (Optional[str]): The universe domain configured via the "GOOGLE_CLOUD_UNIVERSE_DOMAIN" environment variable.

        Returns:
            str: The universe domain to be used by the client.

        Raises:
            ValueError: If the universe domain is an empty string.
        """
        universe_domain = ModelServiceClient._DEFAULT_UNIVERSE
        if client_universe_domain is not None:
            universe_domain = client_universe_domain
        elif universe_domain_env is not None:
            universe_domain = universe_domain_env
        if len(universe_domain.strip()) == 0:
            raise ValueError("Universe Domain cannot be an empty string.")
        return universe_domain

    @staticmethod
    def _compare_universes(
        client_universe: str, credentials: ga_credentials.Credentials
    ) -> bool:
        """Returns True iff the universe domains used by the client and credentials match.

        Args:
            client_universe (str): The universe domain configured via the client options.
            credentials (ga_credentials.Credentials): The credentials being used in the client.

        Returns:
            bool: True iff client_universe matches the universe in credentials.

        Raises:
            ValueError: when client_universe does not match the universe in credentials.
        """

        default_universe = ModelServiceClient._DEFAULT_UNIVERSE
        credentials_universe = getattr(credentials, "universe_domain", default_universe)

        if client_universe != credentials_universe:
            raise ValueError(
                "The configured universe domain "
                f"({client_universe}) does not match the universe domain "
                f"found in the credentials ({credentials_universe}). "
                "If you haven't configured the universe domain explicitly, "
                f"`{default_universe}` is the default."
            )
        return True

    def _validate_universe_domain(self):
        """Validates client's and credentials' universe domains are consistent.

        Returns:
            bool: True iff the configured universe domain is valid.

        Raises:
            ValueError: If the configured universe domain is not valid.
        """
        self._is_universe_domain_valid = (
            self._is_universe_domain_valid
            or ModelServiceClient._compare_universes(
                self.universe_domain, self.transport._credentials
            )
        )
        return self._is_universe_domain_valid

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used by the client instance.
        """
        return self._universe_domain

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, ModelServiceTransport, Callable[..., ModelServiceTransport]]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the model service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,ModelServiceTransport,Callable[..., ModelServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
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
                default "googleapis.com" universe. Note that the ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client_options = client_options
        if isinstance(self._client_options, dict):
            self._client_options = client_options_lib.from_dict(self._client_options)
        if self._client_options is None:
            self._client_options = client_options_lib.ClientOptions()
        self._client_options = cast(
            client_options_lib.ClientOptions, self._client_options
        )

        universe_domain_opt = getattr(self._client_options, "universe_domain", None)

        (
            self._use_client_cert,
            self._use_mtls_endpoint,
            self._universe_domain_env,
        ) = ModelServiceClient._read_environment_variables()
        self._client_cert_source = ModelServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = ModelServiceClient._get_universe_domain(
            universe_domain_opt, self._universe_domain_env
        )
        self._api_endpoint = None  # updated below, depending on `transport`

        # Initialize the universe domain validation.
        self._is_universe_domain_valid = False

        api_key_value = getattr(self._client_options, "api_key", None)
        if api_key_value and credentials:
            raise ValueError(
                "client_options.api_key and credentials are mutually exclusive"
            )

        # Save or instantiate the transport.
        # Ordinarily, we provide the transport, but allowing a custom transport
        # instance provides an extensibility point for unusual situations.
        transport_provided = isinstance(transport, ModelServiceTransport)
        if transport_provided:
            # transport is a ModelServiceTransport instance.
            if credentials or self._client_options.credentials_file or api_key_value:
                raise ValueError(
                    "When providing a transport instance, "
                    "provide its credentials directly."
                )
            if self._client_options.scopes:
                raise ValueError(
                    "When providing a transport instance, provide its scopes "
                    "directly."
                )
            self._transport = cast(ModelServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = self._api_endpoint or ModelServiceClient._get_api_endpoint(
            self._client_options.api_endpoint,
            self._client_cert_source,
            self._universe_domain,
            self._use_mtls_endpoint,
        )

        if not transport_provided:
            import google.auth._default  # type: ignore

            if api_key_value and hasattr(
                google.auth._default, "get_api_key_credentials"
            ):
                credentials = google.auth._default.get_api_key_credentials(
                    api_key_value
                )

            transport_init: Union[
                Type[ModelServiceTransport], Callable[..., ModelServiceTransport]
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., ModelServiceTransport], transport)
            )
            # initialize with the provided callable or the passed in class
            self._transport = transport_init(
                credentials=credentials,
                credentials_file=self._client_options.credentials_file,
                host=self._api_endpoint,
                scopes=self._client_options.scopes,
                client_cert_source_for_mtls=self._client_cert_source,
                quota_project_id=self._client_options.quota_project_id,
                client_info=client_info,
                always_use_jwt_access=True,
                api_audience=self._client_options.api_audience,
            )

    def get_model(
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
            from google.ai import generativelanguage_v1beta

            def sample_get_model():
                # Create a client
                client = generativelanguage_v1beta.ModelServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetModelRequest(
                    name="name_value",
                )

                # Make the request
                response = client.get_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.GetModelRequest, dict]):
                The request object. Request for getting information about
                a specific Model.
            name (str):
                Required. The resource name of the model.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.Model:
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
        rpc = self._transport._wrapped_methods[self._transport.get_model]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def list_models(
        self,
        request: Optional[Union[model_service.ListModelsRequest, dict]] = None,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListModelsPager:
        r"""Lists models available through the API.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_list_models():
                # Create a client
                client = generativelanguage_v1beta.ModelServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListModelsRequest(
                )

                # Make the request
                page_result = client.list_models(request=request)

                # Handle the response
                for response in page_result:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.ListModelsRequest, dict]):
                The request object. Request for listing all Models.
            page_size (int):
                The maximum number of ``Models`` to return (per page).

                The service may return fewer models. If unspecified, at
                most 50 models will be returned per page. This method
                returns at most 1000 models per page, even if you pass a
                larger page_size.

                This corresponds to the ``page_size`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            page_token (str):
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
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.model_service.pagers.ListModelsPager:
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
        rpc = self._transport._wrapped_methods[self._transport.list_models]

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__iter__` convenience method.
        response = pagers.ListModelsPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def get_tuned_model(
        self,
        request: Optional[Union[model_service.GetTunedModelRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> tuned_model.TunedModel:
        r"""Gets information about a specific TunedModel.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_get_tuned_model():
                # Create a client
                client = generativelanguage_v1beta.ModelServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetTunedModelRequest(
                    name="name_value",
                )

                # Make the request
                response = client.get_tuned_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.GetTunedModelRequest, dict]):
                The request object. Request for getting information about
                a specific Model.
            name (str):
                Required. The resource name of the model.

                Format: ``tunedModels/my-model-id``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.TunedModel:
                A fine-tuned model created using
                ModelService.CreateTunedModel.

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
        if not isinstance(request, model_service.GetTunedModelRequest):
            request = model_service.GetTunedModelRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.get_tuned_model]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def list_tuned_models(
        self,
        request: Optional[Union[model_service.ListTunedModelsRequest, dict]] = None,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListTunedModelsPager:
        r"""Lists tuned models owned by the user.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_list_tuned_models():
                # Create a client
                client = generativelanguage_v1beta.ModelServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListTunedModelsRequest(
                )

                # Make the request
                page_result = client.list_tuned_models(request=request)

                # Handle the response
                for response in page_result:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.ListTunedModelsRequest, dict]):
                The request object. Request for listing TunedModels.
            page_size (int):
                Optional. The maximum number of ``TunedModels`` to
                return (per page). The service may return fewer tuned
                models.

                If unspecified, at most 10 tuned models will be
                returned. This method returns at most 1000 models per
                page, even if you pass a larger page_size.

                This corresponds to the ``page_size`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            page_token (str):
                Optional. A page token, received from a previous
                ``ListTunedModels`` call.

                Provide the ``page_token`` returned by one request as an
                argument to the next request to retrieve the next page.

                When paginating, all other parameters provided to
                ``ListTunedModels`` must match the call that provided
                the page token.

                This corresponds to the ``page_token`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.model_service.pagers.ListTunedModelsPager:
                Response from ListTunedModels containing a paginated
                list of Models.

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
        if not isinstance(request, model_service.ListTunedModelsRequest):
            request = model_service.ListTunedModelsRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if page_size is not None:
                request.page_size = page_size
            if page_token is not None:
                request.page_token = page_token

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.list_tuned_models]

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__iter__` convenience method.
        response = pagers.ListTunedModelsPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def create_tuned_model(
        self,
        request: Optional[Union[model_service.CreateTunedModelRequest, dict]] = None,
        *,
        tuned_model: Optional[gag_tuned_model.TunedModel] = None,
        tuned_model_id: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operation.Operation:
        r"""Creates a tuned model. Intermediate tuning progress (if any) is
        accessed through the [google.longrunning.Operations] service.

        Status and results can be accessed through the Operations
        service. Example: GET
        /v1/tunedModels/az2mb0bpw6i/operations/000-111-222

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_create_tuned_model():
                # Create a client
                client = generativelanguage_v1beta.ModelServiceClient()

                # Initialize request argument(s)
                tuned_model = generativelanguage_v1beta.TunedModel()
                tuned_model.tuning_task.training_data.examples.examples.text_input = "text_input_value"
                tuned_model.tuning_task.training_data.examples.examples.output = "output_value"

                request = generativelanguage_v1beta.CreateTunedModelRequest(
                    tuned_model=tuned_model,
                )

                # Make the request
                operation = client.create_tuned_model(request=request)

                print("Waiting for operation to complete...")

                response = operation.result()

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.CreateTunedModelRequest, dict]):
                The request object. Request to create a TunedModel.
            tuned_model (google.ai.generativelanguage_v1beta.types.TunedModel):
                Required. The tuned model to create.
                This corresponds to the ``tuned_model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            tuned_model_id (str):
                Optional. The unique id for the tuned model if
                specified. This value should be up to 40 characters, the
                first character must be a letter, the last could be a
                letter or a number. The id must match the regular
                expression: `a-z <[a-z0-9-]{0,38}[a-z0-9]>`__?.

                This corresponds to the ``tuned_model_id`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.api_core.operation.Operation:
                An object representing a long-running operation.

                The result type for the operation will be
                :class:`google.ai.generativelanguage_v1beta.types.TunedModel`
                A fine-tuned model created using
                ModelService.CreateTunedModel.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([tuned_model, tuned_model_id])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.CreateTunedModelRequest):
            request = model_service.CreateTunedModelRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if tuned_model is not None:
                request.tuned_model = tuned_model
            if tuned_model_id is not None:
                request.tuned_model_id = tuned_model_id

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.create_tuned_model]

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Wrap the response in an operation future.
        response = operation.from_gapic(
            response,
            self._transport.operations_client,
            gag_tuned_model.TunedModel,
            metadata_type=model_service.CreateTunedModelMetadata,
        )

        # Done; return the response.
        return response

    def update_tuned_model(
        self,
        request: Optional[Union[model_service.UpdateTunedModelRequest, dict]] = None,
        *,
        tuned_model: Optional[gag_tuned_model.TunedModel] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_tuned_model.TunedModel:
        r"""Updates a tuned model.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_update_tuned_model():
                # Create a client
                client = generativelanguage_v1beta.ModelServiceClient()

                # Initialize request argument(s)
                tuned_model = generativelanguage_v1beta.TunedModel()
                tuned_model.tuning_task.training_data.examples.examples.text_input = "text_input_value"
                tuned_model.tuning_task.training_data.examples.examples.output = "output_value"

                request = generativelanguage_v1beta.UpdateTunedModelRequest(
                    tuned_model=tuned_model,
                )

                # Make the request
                response = client.update_tuned_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.UpdateTunedModelRequest, dict]):
                The request object. Request to update a TunedModel.
            tuned_model (google.ai.generativelanguage_v1beta.types.TunedModel):
                Required. The tuned model to update.
                This corresponds to the ``tuned_model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (google.protobuf.field_mask_pb2.FieldMask):
                Required. The list of fields to
                update.

                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.TunedModel:
                A fine-tuned model created using
                ModelService.CreateTunedModel.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([tuned_model, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.UpdateTunedModelRequest):
            request = model_service.UpdateTunedModelRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if tuned_model is not None:
                request.tuned_model = tuned_model
            if update_mask is not None:
                request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.update_tuned_model]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("tuned_model.name", request.tuned_model.name),)
            ),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def delete_tuned_model(
        self,
        request: Optional[Union[model_service.DeleteTunedModelRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes a tuned model.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_delete_tuned_model():
                # Create a client
                client = generativelanguage_v1beta.ModelServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.DeleteTunedModelRequest(
                    name="name_value",
                )

                # Make the request
                client.delete_tuned_model(request=request)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.DeleteTunedModelRequest, dict]):
                The request object. Request to delete a TunedModel.
            name (str):
                Required. The resource name of the model. Format:
                ``tunedModels/my-model-id``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
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
        if not isinstance(request, model_service.DeleteTunedModelRequest):
            request = model_service.DeleteTunedModelRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.delete_tuned_model]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    def __enter__(self) -> "ModelServiceClient":
        return self

    def __exit__(self, type, value, traceback):
        """Releases underlying transport's resources.

        .. warning::
            ONLY use as a context manager if the transport is NOT shared
            with other clients! Exiting the with block will CLOSE the transport
            and may cause errors in other clients!
        """
        self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("ModelServiceClient",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\model_service\client.py ===
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
import os
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
    cast,
)
import warnings

from google.api_core import client_options as client_options_lib
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.exceptions import MutualTLSChannelError  # type: ignore
from google.auth.transport import mtls  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta3 import gapic_version as package_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore

from google.api_core import operation  # type: ignore
from google.api_core import operation_async  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import field_mask_pb2  # type: ignore
from google.protobuf import timestamp_pb2  # type: ignore

from google.ai.generativelanguage_v1beta3.services.model_service import pagers
from google.ai.generativelanguage_v1beta3.types import tuned_model as gag_tuned_model
from google.ai.generativelanguage_v1beta3.types import model, model_service
from google.ai.generativelanguage_v1beta3.types import tuned_model

from .transports.base import DEFAULT_CLIENT_INFO, ModelServiceTransport
from .transports.grpc import ModelServiceGrpcTransport
from .transports.grpc_asyncio import ModelServiceGrpcAsyncIOTransport
from .transports.rest import ModelServiceRestTransport


class ModelServiceClientMeta(type):
    """Metaclass for the ModelService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = OrderedDict()  # type: Dict[str, Type[ModelServiceTransport]]
    _transport_registry["grpc"] = ModelServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = ModelServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = ModelServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[ModelServiceTransport]:
        """Returns an appropriate transport class.

        Args:
            label: The name of the desired transport. If none is
                provided, then the first transport in the registry is used.

        Returns:
            The transport class to use.
        """
        # If a specific transport is requested, return that one.
        if label:
            return cls._transport_registry[label]

        # No transport is requested; return the default (that is, the first one
        # in the dictionary).
        return next(iter(cls._transport_registry.values()))


class ModelServiceClient(metaclass=ModelServiceClientMeta):
    """Provides methods for getting metadata information about
    Generative Models.
    """

    @staticmethod
    def _get_default_mtls_endpoint(api_endpoint):
        """Converts api endpoint to mTLS endpoint.

        Convert "*.sandbox.googleapis.com" and "*.googleapis.com" to
        "*.mtls.sandbox.googleapis.com" and "*.mtls.googleapis.com" respectively.
        Args:
            api_endpoint (Optional[str]): the api endpoint to convert.
        Returns:
            str: converted mTLS api endpoint.
        """
        if not api_endpoint:
            return api_endpoint

        mtls_endpoint_re = re.compile(
            r"(?P<name>[^.]+)(?P<mtls>\.mtls)?(?P<sandbox>\.sandbox)?(?P<googledomain>\.googleapis\.com)?"
        )

        m = mtls_endpoint_re.match(api_endpoint)
        name, mtls, sandbox, googledomain = m.groups()
        if mtls or not googledomain:
            return api_endpoint

        if sandbox:
            return api_endpoint.replace(
                "sandbox.googleapis.com", "mtls.sandbox.googleapis.com"
            )

        return api_endpoint.replace(".googleapis.com", ".mtls.googleapis.com")

    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = "generativelanguage.googleapis.com"
    DEFAULT_MTLS_ENDPOINT = _get_default_mtls_endpoint.__func__(  # type: ignore
        DEFAULT_ENDPOINT
    )

    _DEFAULT_ENDPOINT_TEMPLATE = "generativelanguage.{UNIVERSE_DOMAIN}"
    _DEFAULT_UNIVERSE = "googleapis.com"

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            ModelServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_info(info)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

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
            ModelServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> ModelServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            ModelServiceTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def model_path(
        model: str,
    ) -> str:
        """Returns a fully-qualified model string."""
        return "models/{model}".format(
            model=model,
        )

    @staticmethod
    def parse_model_path(path: str) -> Dict[str, str]:
        """Parses a model path into its component segments."""
        m = re.match(r"^models/(?P<model>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def tuned_model_path(
        tuned_model: str,
    ) -> str:
        """Returns a fully-qualified tuned_model string."""
        return "tunedModels/{tuned_model}".format(
            tuned_model=tuned_model,
        )

    @staticmethod
    def parse_tuned_model_path(path: str) -> Dict[str, str]:
        """Parses a tuned_model path into its component segments."""
        m = re.match(r"^tunedModels/(?P<tuned_model>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_billing_account_path(
        billing_account: str,
    ) -> str:
        """Returns a fully-qualified billing_account string."""
        return "billingAccounts/{billing_account}".format(
            billing_account=billing_account,
        )

    @staticmethod
    def parse_common_billing_account_path(path: str) -> Dict[str, str]:
        """Parse a billing_account path into its component segments."""
        m = re.match(r"^billingAccounts/(?P<billing_account>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_folder_path(
        folder: str,
    ) -> str:
        """Returns a fully-qualified folder string."""
        return "folders/{folder}".format(
            folder=folder,
        )

    @staticmethod
    def parse_common_folder_path(path: str) -> Dict[str, str]:
        """Parse a folder path into its component segments."""
        m = re.match(r"^folders/(?P<folder>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_organization_path(
        organization: str,
    ) -> str:
        """Returns a fully-qualified organization string."""
        return "organizations/{organization}".format(
            organization=organization,
        )

    @staticmethod
    def parse_common_organization_path(path: str) -> Dict[str, str]:
        """Parse a organization path into its component segments."""
        m = re.match(r"^organizations/(?P<organization>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_project_path(
        project: str,
    ) -> str:
        """Returns a fully-qualified project string."""
        return "projects/{project}".format(
            project=project,
        )

    @staticmethod
    def parse_common_project_path(path: str) -> Dict[str, str]:
        """Parse a project path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_location_path(
        project: str,
        location: str,
    ) -> str:
        """Returns a fully-qualified location string."""
        return "projects/{project}/locations/{location}".format(
            project=project,
            location=location,
        )

    @staticmethod
    def parse_common_location_path(path: str) -> Dict[str, str]:
        """Parse a location path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)/locations/(?P<location>.+?)$", path)
        return m.groupdict() if m else {}

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[client_options_lib.ClientOptions] = None
    ):
        """Deprecated. Return the API endpoint and client cert source for mutual TLS.

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

        warnings.warn(
            "get_mtls_endpoint_and_cert_source is deprecated. Use the api_endpoint property instead.",
            DeprecationWarning,
        )
        if client_options is None:
            client_options = client_options_lib.ClientOptions()
        use_client_cert = os.getenv("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )

        # Figure out the client cert source to use.
        client_cert_source = None
        if use_client_cert == "true":
            if client_options.client_cert_source:
                client_cert_source = client_options.client_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()

        # Figure out which api endpoint to use.
        if client_options.api_endpoint is not None:
            api_endpoint = client_options.api_endpoint
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            api_endpoint = cls.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = cls.DEFAULT_ENDPOINT

        return api_endpoint, client_cert_source

    @staticmethod
    def _read_environment_variables():
        """Returns the environment variables used by the client.

        Returns:
            Tuple[bool, str, str]: returns the GOOGLE_API_USE_CLIENT_CERTIFICATE,
            GOOGLE_API_USE_MTLS_ENDPOINT, and GOOGLE_CLOUD_UNIVERSE_DOMAIN environment variables.

        Raises:
            ValueError: If GOOGLE_API_USE_CLIENT_CERTIFICATE is not
                any of ["true", "false"].
            google.auth.exceptions.MutualTLSChannelError: If GOOGLE_API_USE_MTLS_ENDPOINT
                is not any of ["auto", "never", "always"].
        """
        use_client_cert = os.getenv(
            "GOOGLE_API_USE_CLIENT_CERTIFICATE", "false"
        ).lower()
        use_mtls_endpoint = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto").lower()
        universe_domain_env = os.getenv("GOOGLE_CLOUD_UNIVERSE_DOMAIN")
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        if use_mtls_endpoint not in ("auto", "never", "always"):
            raise MutualTLSChannelError(
                "Environment variable `GOOGLE_API_USE_MTLS_ENDPOINT` must be `never`, `auto` or `always`"
            )
        return use_client_cert == "true", use_mtls_endpoint, universe_domain_env

    @staticmethod
    def _get_client_cert_source(provided_cert_source, use_cert_flag):
        """Return the client cert source to be used by the client.

        Args:
            provided_cert_source (bytes): The client certificate source provided.
            use_cert_flag (bool): A flag indicating whether to use the client certificate.

        Returns:
            bytes or None: The client cert source to be used by the client.
        """
        client_cert_source = None
        if use_cert_flag:
            if provided_cert_source:
                client_cert_source = provided_cert_source
            elif mtls.has_default_client_cert_source():
                client_cert_source = mtls.default_client_cert_source()
        return client_cert_source

    @staticmethod
    def _get_api_endpoint(
        api_override, client_cert_source, universe_domain, use_mtls_endpoint
    ):
        """Return the API endpoint used by the client.

        Args:
            api_override (str): The API endpoint override. If specified, this is always
                the return value of this function and the other arguments are not used.
            client_cert_source (bytes): The client certificate source used by the client.
            universe_domain (str): The universe domain used by the client.
            use_mtls_endpoint (str): How to use the mTLS endpoint, which depends also on the other parameters.
                Possible values are "always", "auto", or "never".

        Returns:
            str: The API endpoint to be used by the client.
        """
        if api_override is not None:
            api_endpoint = api_override
        elif use_mtls_endpoint == "always" or (
            use_mtls_endpoint == "auto" and client_cert_source
        ):
            _default_universe = ModelServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = ModelServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = ModelServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
                UNIVERSE_DOMAIN=universe_domain
            )
        return api_endpoint

    @staticmethod
    def _get_universe_domain(
        client_universe_domain: Optional[str], universe_domain_env: Optional[str]
    ) -> str:
        """Return the universe domain used by the client.

        Args:
            client_universe_domain (Optional[str]): The universe domain configured via the client options.
            universe_domain_env (Optional[str]): The universe domain configured via the "GOOGLE_CLOUD_UNIVERSE_DOMAIN" environment variable.

        Returns:
            str: The universe domain to be used by the client.

        Raises:
            ValueError: If the universe domain is an empty string.
        """
        universe_domain = ModelServiceClient._DEFAULT_UNIVERSE
        if client_universe_domain is not None:
            universe_domain = client_universe_domain
        elif universe_domain_env is not None:
            universe_domain = universe_domain_env
        if len(universe_domain.strip()) == 0:
            raise ValueError("Universe Domain cannot be an empty string.")
        return universe_domain

    @staticmethod
    def _compare_universes(
        client_universe: str, credentials: ga_credentials.Credentials
    ) -> bool:
        """Returns True iff the universe domains used by the client and credentials match.

        Args:
            client_universe (str): The universe domain configured via the client options.
            credentials (ga_credentials.Credentials): The credentials being used in the client.

        Returns:
            bool: True iff client_universe matches the universe in credentials.

        Raises:
            ValueError: when client_universe does not match the universe in credentials.
        """

        default_universe = ModelServiceClient._DEFAULT_UNIVERSE
        credentials_universe = getattr(credentials, "universe_domain", default_universe)

        if client_universe != credentials_universe:
            raise ValueError(
                "The configured universe domain "
                f"({client_universe}) does not match the universe domain "
                f"found in the credentials ({credentials_universe}). "
                "If you haven't configured the universe domain explicitly, "
                f"`{default_universe}` is the default."
            )
        return True

    def _validate_universe_domain(self):
        """Validates client's and credentials' universe domains are consistent.

        Returns:
            bool: True iff the configured universe domain is valid.

        Raises:
            ValueError: If the configured universe domain is not valid.
        """
        self._is_universe_domain_valid = (
            self._is_universe_domain_valid
            or ModelServiceClient._compare_universes(
                self.universe_domain, self.transport._credentials
            )
        )
        return self._is_universe_domain_valid

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used by the client instance.
        """
        return self._universe_domain

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, ModelServiceTransport, Callable[..., ModelServiceTransport]]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the model service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,ModelServiceTransport,Callable[..., ModelServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
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
                default "googleapis.com" universe. Note that the ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client_options = client_options
        if isinstance(self._client_options, dict):
            self._client_options = client_options_lib.from_dict(self._client_options)
        if self._client_options is None:
            self._client_options = client_options_lib.ClientOptions()
        self._client_options = cast(
            client_options_lib.ClientOptions, self._client_options
        )

        universe_domain_opt = getattr(self._client_options, "universe_domain", None)

        (
            self._use_client_cert,
            self._use_mtls_endpoint,
            self._universe_domain_env,
        ) = ModelServiceClient._read_environment_variables()
        self._client_cert_source = ModelServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = ModelServiceClient._get_universe_domain(
            universe_domain_opt, self._universe_domain_env
        )
        self._api_endpoint = None  # updated below, depending on `transport`

        # Initialize the universe domain validation.
        self._is_universe_domain_valid = False

        api_key_value = getattr(self._client_options, "api_key", None)
        if api_key_value and credentials:
            raise ValueError(
                "client_options.api_key and credentials are mutually exclusive"
            )

        # Save or instantiate the transport.
        # Ordinarily, we provide the transport, but allowing a custom transport
        # instance provides an extensibility point for unusual situations.
        transport_provided = isinstance(transport, ModelServiceTransport)
        if transport_provided:
            # transport is a ModelServiceTransport instance.
            if credentials or self._client_options.credentials_file or api_key_value:
                raise ValueError(
                    "When providing a transport instance, "
                    "provide its credentials directly."
                )
            if self._client_options.scopes:
                raise ValueError(
                    "When providing a transport instance, provide its scopes "
                    "directly."
                )
            self._transport = cast(ModelServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = self._api_endpoint or ModelServiceClient._get_api_endpoint(
            self._client_options.api_endpoint,
            self._client_cert_source,
            self._universe_domain,
            self._use_mtls_endpoint,
        )

        if not transport_provided:
            import google.auth._default  # type: ignore

            if api_key_value and hasattr(
                google.auth._default, "get_api_key_credentials"
            ):
                credentials = google.auth._default.get_api_key_credentials(
                    api_key_value
                )

            transport_init: Union[
                Type[ModelServiceTransport], Callable[..., ModelServiceTransport]
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., ModelServiceTransport], transport)
            )
            # initialize with the provided callable or the passed in class
            self._transport = transport_init(
                credentials=credentials,
                credentials_file=self._client_options.credentials_file,
                host=self._api_endpoint,
                scopes=self._client_options.scopes,
                client_cert_source_for_mtls=self._client_cert_source,
                quota_project_id=self._client_options.quota_project_id,
                client_info=client_info,
                always_use_jwt_access=True,
                api_audience=self._client_options.api_audience,
            )

    def get_model(
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
            from google.ai import generativelanguage_v1beta3

            def sample_get_model():
                # Create a client
                client = generativelanguage_v1beta3.ModelServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.GetModelRequest(
                    name="name_value",
                )

                # Make the request
                response = client.get_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.GetModelRequest, dict]):
                The request object. Request for getting information about
                a specific Model.
            name (str):
                Required. The resource name of the model.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.Model:
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
        rpc = self._transport._wrapped_methods[self._transport.get_model]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def list_models(
        self,
        request: Optional[Union[model_service.ListModelsRequest, dict]] = None,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListModelsPager:
        r"""Lists models available through the API.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_list_models():
                # Create a client
                client = generativelanguage_v1beta3.ModelServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.ListModelsRequest(
                )

                # Make the request
                page_result = client.list_models(request=request)

                # Handle the response
                for response in page_result:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.ListModelsRequest, dict]):
                The request object. Request for listing all Models.
            page_size (int):
                The maximum number of ``Models`` to return (per page).

                The service may return fewer models. If unspecified, at
                most 50 models will be returned per page. This method
                returns at most 1000 models per page, even if you pass a
                larger page_size.

                This corresponds to the ``page_size`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            page_token (str):
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
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.services.model_service.pagers.ListModelsPager:
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
        rpc = self._transport._wrapped_methods[self._transport.list_models]

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__iter__` convenience method.
        response = pagers.ListModelsPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def get_tuned_model(
        self,
        request: Optional[Union[model_service.GetTunedModelRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> tuned_model.TunedModel:
        r"""Gets information about a specific TunedModel.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_get_tuned_model():
                # Create a client
                client = generativelanguage_v1beta3.ModelServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.GetTunedModelRequest(
                    name="name_value",
                )

                # Make the request
                response = client.get_tuned_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.GetTunedModelRequest, dict]):
                The request object. Request for getting information about
                a specific Model.
            name (str):
                Required. The resource name of the model.

                Format: ``tunedModels/my-model-id``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.TunedModel:
                A fine-tuned model created using
                ModelService.CreateTunedModel.

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
        if not isinstance(request, model_service.GetTunedModelRequest):
            request = model_service.GetTunedModelRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.get_tuned_model]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def list_tuned_models(
        self,
        request: Optional[Union[model_service.ListTunedModelsRequest, dict]] = None,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListTunedModelsPager:
        r"""Lists tuned models owned by the user.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_list_tuned_models():
                # Create a client
                client = generativelanguage_v1beta3.ModelServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.ListTunedModelsRequest(
                )

                # Make the request
                page_result = client.list_tuned_models(request=request)

                # Handle the response
                for response in page_result:
                    print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.ListTunedModelsRequest, dict]):
                The request object. Request for listing TunedModels.
            page_size (int):
                Optional. The maximum number of ``TunedModels`` to
                return (per page). The service may return fewer tuned
                models.

                If unspecified, at most 10 tuned models will be
                returned. This method returns at most 1000 models per
                page, even if you pass a larger page_size.

                This corresponds to the ``page_size`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            page_token (str):
                Optional. A page token, received from a previous
                ``ListTunedModels`` call.

                Provide the ``page_token`` returned by one request as an
                argument to the next request to retrieve the next page.

                When paginating, all other parameters provided to
                ``ListTunedModels`` must match the call that provided
                the page token.

                This corresponds to the ``page_token`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.services.model_service.pagers.ListTunedModelsPager:
                Response from ListTunedModels containing a paginated
                list of Models.

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
        if not isinstance(request, model_service.ListTunedModelsRequest):
            request = model_service.ListTunedModelsRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if page_size is not None:
                request.page_size = page_size
            if page_token is not None:
                request.page_token = page_token

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.list_tuned_models]

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__iter__` convenience method.
        response = pagers.ListTunedModelsPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def create_tuned_model(
        self,
        request: Optional[Union[model_service.CreateTunedModelRequest, dict]] = None,
        *,
        tuned_model: Optional[gag_tuned_model.TunedModel] = None,
        tuned_model_id: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operation.Operation:
        r"""Creates a tuned model. Intermediate tuning progress (if any) is
        accessed through the [google.longrunning.Operations] service.

        Status and results can be accessed through the Operations
        service. Example: GET
        /v1/tunedModels/az2mb0bpw6i/operations/000-111-222

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_create_tuned_model():
                # Create a client
                client = generativelanguage_v1beta3.ModelServiceClient()

                # Initialize request argument(s)
                tuned_model = generativelanguage_v1beta3.TunedModel()
                tuned_model.tuning_task.training_data.examples.examples.text_input = "text_input_value"
                tuned_model.tuning_task.training_data.examples.examples.output = "output_value"

                request = generativelanguage_v1beta3.CreateTunedModelRequest(
                    tuned_model=tuned_model,
                )

                # Make the request
                operation = client.create_tuned_model(request=request)

                print("Waiting for operation to complete...")

                response = operation.result()

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.CreateTunedModelRequest, dict]):
                The request object. Request to create a TunedModel.
            tuned_model (google.ai.generativelanguage_v1beta3.types.TunedModel):
                Required. The tuned model to create.
                This corresponds to the ``tuned_model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            tuned_model_id (str):
                Optional. The unique id for the tuned model if
                specified. This value should be up to 40 characters, the
                first character must be a letter, the last could be a
                letter or a number. The id must match the regular
                expression: `a-z <[a-z0-9-]{0,38}[a-z0-9]>`__?.

                This corresponds to the ``tuned_model_id`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.api_core.operation.Operation:
                An object representing a long-running operation.

                The result type for the operation will be
                :class:`google.ai.generativelanguage_v1beta3.types.TunedModel`
                A fine-tuned model created using
                ModelService.CreateTunedModel.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([tuned_model, tuned_model_id])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.CreateTunedModelRequest):
            request = model_service.CreateTunedModelRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if tuned_model is not None:
                request.tuned_model = tuned_model
            if tuned_model_id is not None:
                request.tuned_model_id = tuned_model_id

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.create_tuned_model]

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Wrap the response in an operation future.
        response = operation.from_gapic(
            response,
            self._transport.operations_client,
            gag_tuned_model.TunedModel,
            metadata_type=model_service.CreateTunedModelMetadata,
        )

        # Done; return the response.
        return response

    def update_tuned_model(
        self,
        request: Optional[Union[model_service.UpdateTunedModelRequest, dict]] = None,
        *,
        tuned_model: Optional[gag_tuned_model.TunedModel] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_tuned_model.TunedModel:
        r"""Updates a tuned model.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_update_tuned_model():
                # Create a client
                client = generativelanguage_v1beta3.ModelServiceClient()

                # Initialize request argument(s)
                tuned_model = generativelanguage_v1beta3.TunedModel()
                tuned_model.tuning_task.training_data.examples.examples.text_input = "text_input_value"
                tuned_model.tuning_task.training_data.examples.examples.output = "output_value"

                request = generativelanguage_v1beta3.UpdateTunedModelRequest(
                    tuned_model=tuned_model,
                )

                # Make the request
                response = client.update_tuned_model(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.UpdateTunedModelRequest, dict]):
                The request object. Request to update a TunedModel.
            tuned_model (google.ai.generativelanguage_v1beta3.types.TunedModel):
                Required. The tuned model to update.
                This corresponds to the ``tuned_model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (google.protobuf.field_mask_pb2.FieldMask):
                Required. The list of fields to
                update.

                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.TunedModel:
                A fine-tuned model created using
                ModelService.CreateTunedModel.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([tuned_model, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, model_service.UpdateTunedModelRequest):
            request = model_service.UpdateTunedModelRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if tuned_model is not None:
                request.tuned_model = tuned_model
            if update_mask is not None:
                request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.update_tuned_model]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("tuned_model.name", request.tuned_model.name),)
            ),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        response = rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    def delete_tuned_model(
        self,
        request: Optional[Union[model_service.DeleteTunedModelRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes a tuned model.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_delete_tuned_model():
                # Create a client
                client = generativelanguage_v1beta3.ModelServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.DeleteTunedModelRequest(
                    name="name_value",
                )

                # Make the request
                client.delete_tuned_model(request=request)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.DeleteTunedModelRequest, dict]):
                The request object. Request to delete a TunedModel.
            name (str):
                Required. The resource name of the model. Format:
                ``tunedModels/my-model-id``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
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
        if not isinstance(request, model_service.DeleteTunedModelRequest):
            request = model_service.DeleteTunedModelRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if name is not None:
                request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.delete_tuned_model]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._validate_universe_domain()

        # Send the request.
        rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    def __enter__(self) -> "ModelServiceClient":
        return self

    def __exit__(self, type, value, traceback):
        """Releases underlying transport's resources.

        .. warning::
            ONLY use as a context manager if the transport is NOT shared
            with other clients! Exiting the with block will CLOSE the transport
            and may cause errors in other clients!
        """
        self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("ModelServiceClient",)