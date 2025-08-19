
# === NexusCore/tools\exports\export_20250803_114325\combined_94.py ===

# === NexusCore/openenv\Lib\site-packages\httpx\_models.py ===
from __future__ import annotations

import codecs
import datetime
import email.message
import json as jsonlib
import re
import typing
import urllib.request
from collections.abc import Mapping
from http.cookiejar import Cookie, CookieJar

from ._content import ByteStream, UnattachedStream, encode_request, encode_response
from ._decoders import (
    SUPPORTED_DECODERS,
    ByteChunker,
    ContentDecoder,
    IdentityDecoder,
    LineDecoder,
    MultiDecoder,
    TextChunker,
    TextDecoder,
)
from ._exceptions import (
    CookieConflict,
    HTTPStatusError,
    RequestNotRead,
    ResponseNotRead,
    StreamClosed,
    StreamConsumed,
    request_context,
)
from ._multipart import get_multipart_boundary_from_content_type
from ._status_codes import codes
from ._types import (
    AsyncByteStream,
    CookieTypes,
    HeaderTypes,
    QueryParamTypes,
    RequestContent,
    RequestData,
    RequestExtensions,
    RequestFiles,
    ResponseContent,
    ResponseExtensions,
    SyncByteStream,
)
from ._urls import URL
from ._utils import to_bytes_or_str, to_str

__all__ = ["Cookies", "Headers", "Request", "Response"]

SENSITIVE_HEADERS = {"authorization", "proxy-authorization"}


def _is_known_encoding(encoding: str) -> bool:
    """
    Return `True` if `encoding` is a known codec.
    """
    try:
        codecs.lookup(encoding)
    except LookupError:
        return False
    return True


def _normalize_header_key(key: str | bytes, encoding: str | None = None) -> bytes:
    """
    Coerce str/bytes into a strictly byte-wise HTTP header key.
    """
    return key if isinstance(key, bytes) else key.encode(encoding or "ascii")


def _normalize_header_value(value: str | bytes, encoding: str | None = None) -> bytes:
    """
    Coerce str/bytes into a strictly byte-wise HTTP header value.
    """
    if isinstance(value, bytes):
        return value
    if not isinstance(value, str):
        raise TypeError(f"Header value must be str or bytes, not {type(value)}")
    return value.encode(encoding or "ascii")


def _parse_content_type_charset(content_type: str) -> str | None:
    # We used to use `cgi.parse_header()` here, but `cgi` became a dead battery.
    # See: https://peps.python.org/pep-0594/#cgi
    msg = email.message.Message()
    msg["content-type"] = content_type
    return msg.get_content_charset(failobj=None)


def _parse_header_links(value: str) -> list[dict[str, str]]:
    """
    Returns a list of parsed link headers, for more info see:
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Link
    The generic syntax of those is:
    Link: < uri-reference >; param1=value1; param2="value2"
    So for instance:
    Link; '<http:/.../front.jpeg>; type="image/jpeg",<http://.../back.jpeg>;'
    would return
        [
            {"url": "http:/.../front.jpeg", "type": "image/jpeg"},
            {"url": "http://.../back.jpeg"},
        ]
    :param value: HTTP Link entity-header field
    :return: list of parsed link headers
    """
    links: list[dict[str, str]] = []
    replace_chars = " '\""
    value = value.strip(replace_chars)
    if not value:
        return links
    for val in re.split(", *<", value):
        try:
            url, params = val.split(";", 1)
        except ValueError:
            url, params = val, ""
        link = {"url": url.strip("<> '\"")}
        for param in params.split(";"):
            try:
                key, value = param.split("=")
            except ValueError:
                break
            link[key.strip(replace_chars)] = value.strip(replace_chars)
        links.append(link)
    return links


def _obfuscate_sensitive_headers(
    items: typing.Iterable[tuple[typing.AnyStr, typing.AnyStr]],
) -> typing.Iterator[tuple[typing.AnyStr, typing.AnyStr]]:
    for k, v in items:
        if to_str(k.lower()) in SENSITIVE_HEADERS:
            v = to_bytes_or_str("[secure]", match_type_of=v)
        yield k, v


class Headers(typing.MutableMapping[str, str]):
    """
    HTTP headers, as a case-insensitive multi-dict.
    """

    def __init__(
        self,
        headers: HeaderTypes | None = None,
        encoding: str | None = None,
    ) -> None:
        self._list = []  # type: typing.List[typing.Tuple[bytes, bytes, bytes]]

        if isinstance(headers, Headers):
            self._list = list(headers._list)
        elif isinstance(headers, Mapping):
            for k, v in headers.items():
                bytes_key = _normalize_header_key(k, encoding)
                bytes_value = _normalize_header_value(v, encoding)
                self._list.append((bytes_key, bytes_key.lower(), bytes_value))
        elif headers is not None:
            for k, v in headers:
                bytes_key = _normalize_header_key(k, encoding)
                bytes_value = _normalize_header_value(v, encoding)
                self._list.append((bytes_key, bytes_key.lower(), bytes_value))

        self._encoding = encoding

    @property
    def encoding(self) -> str:
        """
        Header encoding is mandated as ascii, but we allow fallbacks to utf-8
        or iso-8859-1.
        """
        if self._encoding is None:
            for encoding in ["ascii", "utf-8"]:
                for key, value in self.raw:
                    try:
                        key.decode(encoding)
                        value.decode(encoding)
                    except UnicodeDecodeError:
                        break
                else:
                    # The else block runs if 'break' did not occur, meaning
                    # all values fitted the encoding.
                    self._encoding = encoding
                    break
            else:
                # The ISO-8859-1 encoding covers all 256 code points in a byte,
                # so will never raise decode errors.
                self._encoding = "iso-8859-1"
        return self._encoding

    @encoding.setter
    def encoding(self, value: str) -> None:
        self._encoding = value

    @property
    def raw(self) -> list[tuple[bytes, bytes]]:
        """
        Returns a list of the raw header items, as byte pairs.
        """
        return [(raw_key, value) for raw_key, _, value in self._list]

    def keys(self) -> typing.KeysView[str]:
        return {key.decode(self.encoding): None for _, key, value in self._list}.keys()

    def values(self) -> typing.ValuesView[str]:
        values_dict: dict[str, str] = {}
        for _, key, value in self._list:
            str_key = key.decode(self.encoding)
            str_value = value.decode(self.encoding)
            if str_key in values_dict:
                values_dict[str_key] += f", {str_value}"
            else:
                values_dict[str_key] = str_value
        return values_dict.values()

    def items(self) -> typing.ItemsView[str, str]:
        """
        Return `(key, value)` items of headers. Concatenate headers
        into a single comma separated value when a key occurs multiple times.
        """
        values_dict: dict[str, str] = {}
        for _, key, value in self._list:
            str_key = key.decode(self.encoding)
            str_value = value.decode(self.encoding)
            if str_key in values_dict:
                values_dict[str_key] += f", {str_value}"
            else:
                values_dict[str_key] = str_value
        return values_dict.items()

    def multi_items(self) -> list[tuple[str, str]]:
        """
        Return a list of `(key, value)` pairs of headers. Allow multiple
        occurrences of the same key without concatenating into a single
        comma separated value.
        """
        return [
            (key.decode(self.encoding), value.decode(self.encoding))
            for _, key, value in self._list
        ]

    def get(self, key: str, default: typing.Any = None) -> typing.Any:
        """
        Return a header value. If multiple occurrences of the header occur
        then concatenate them together with commas.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def get_list(self, key: str, split_commas: bool = False) -> list[str]:
        """
        Return a list of all header values for a given key.
        If `split_commas=True` is passed, then any comma separated header
        values are split into multiple return strings.
        """
        get_header_key = key.lower().encode(self.encoding)

        values = [
            item_value.decode(self.encoding)
            for _, item_key, item_value in self._list
            if item_key.lower() == get_header_key
        ]

        if not split_commas:
            return values

        split_values = []
        for value in values:
            split_values.extend([item.strip() for item in value.split(",")])
        return split_values

    def update(self, headers: HeaderTypes | None = None) -> None:  # type: ignore
        headers = Headers(headers)
        for key in headers.keys():
            if key in self:
                self.pop(key)
        self._list.extend(headers._list)

    def copy(self) -> Headers:
        return Headers(self, encoding=self.encoding)

    def __getitem__(self, key: str) -> str:
        """
        Return a single header value.

        If there are multiple headers with the same key, then we concatenate
        them with commas. See: https://tools.ietf.org/html/rfc7230#section-3.2.2
        """
        normalized_key = key.lower().encode(self.encoding)

        items = [
            header_value.decode(self.encoding)
            for _, header_key, header_value in self._list
            if header_key == normalized_key
        ]

        if items:
            return ", ".join(items)

        raise KeyError(key)

    def __setitem__(self, key: str, value: str) -> None:
        """
        Set the header `key` to `value`, removing any duplicate entries.
        Retains insertion order.
        """
        set_key = key.encode(self._encoding or "utf-8")
        set_value = value.encode(self._encoding or "utf-8")
        lookup_key = set_key.lower()

        found_indexes = [
            idx
            for idx, (_, item_key, _) in enumerate(self._list)
            if item_key == lookup_key
        ]

        for idx in reversed(found_indexes[1:]):
            del self._list[idx]

        if found_indexes:
            idx = found_indexes[0]
            self._list[idx] = (set_key, lookup_key, set_value)
        else:
            self._list.append((set_key, lookup_key, set_value))

    def __delitem__(self, key: str) -> None:
        """
        Remove the header `key`.
        """
        del_key = key.lower().encode(self.encoding)

        pop_indexes = [
            idx
            for idx, (_, item_key, _) in enumerate(self._list)
            if item_key.lower() == del_key
        ]

        if not pop_indexes:
            raise KeyError(key)

        for idx in reversed(pop_indexes):
            del self._list[idx]

    def __contains__(self, key: typing.Any) -> bool:
        header_key = key.lower().encode(self.encoding)
        return header_key in [key for _, key, _ in self._list]

    def __iter__(self) -> typing.Iterator[typing.Any]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._list)

    def __eq__(self, other: typing.Any) -> bool:
        try:
            other_headers = Headers(other)
        except ValueError:
            return False

        self_list = [(key, value) for _, key, value in self._list]
        other_list = [(key, value) for _, key, value in other_headers._list]
        return sorted(self_list) == sorted(other_list)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__

        encoding_str = ""
        if self.encoding != "ascii":
            encoding_str = f", encoding={self.encoding!r}"

        as_list = list(_obfuscate_sensitive_headers(self.multi_items()))
        as_dict = dict(as_list)

        no_duplicate_keys = len(as_dict) == len(as_list)
        if no_duplicate_keys:
            return f"{class_name}({as_dict!r}{encoding_str})"
        return f"{class_name}({as_list!r}{encoding_str})"


class Request:
    def __init__(
        self,
        method: str,
        url: URL | str,
        *,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: typing.Any | None = None,
        stream: SyncByteStream | AsyncByteStream | None = None,
        extensions: RequestExtensions | None = None,
    ) -> None:
        self.method = method.upper()
        self.url = URL(url) if params is None else URL(url, params=params)
        self.headers = Headers(headers)
        self.extensions = {} if extensions is None else dict(extensions)

        if cookies:
            Cookies(cookies).set_cookie_header(self)

        if stream is None:
            content_type: str | None = self.headers.get("content-type")
            headers, stream = encode_request(
                content=content,
                data=data,
                files=files,
                json=json,
                boundary=get_multipart_boundary_from_content_type(
                    content_type=content_type.encode(self.headers.encoding)
                    if content_type
                    else None
                ),
            )
            self._prepare(headers)
            self.stream = stream
            # Load the request body, except for streaming content.
            if isinstance(stream, ByteStream):
                self.read()
        else:
            # There's an important distinction between `Request(content=...)`,
            # and `Request(stream=...)`.
            #
            # Using `content=...` implies automatically populated `Host` and content
            # headers, of either `Content-Length: ...` or `Transfer-Encoding: chunked`.
            #
            # Using `stream=...` will not automatically include *any*
            # auto-populated headers.
            #
            # As an end-user you don't really need `stream=...`. It's only
            # useful when:
            #
            # * Preserving the request stream when copying requests, eg for redirects.
            # * Creating request instances on the *server-side* of the transport API.
            self.stream = stream

    def _prepare(self, default_headers: dict[str, str]) -> None:
        for key, value in default_headers.items():
            # Ignore Transfer-Encoding if the Content-Length has been set explicitly.
            if key.lower() == "transfer-encoding" and "Content-Length" in self.headers:
                continue
            self.headers.setdefault(key, value)

        auto_headers: list[tuple[bytes, bytes]] = []

        has_host = "Host" in self.headers
        has_content_length = (
            "Content-Length" in self.headers or "Transfer-Encoding" in self.headers
        )

        if not has_host and self.url.host:
            auto_headers.append((b"Host", self.url.netloc))
        if not has_content_length and self.method in ("POST", "PUT", "PATCH"):
            auto_headers.append((b"Content-Length", b"0"))

        self.headers = Headers(auto_headers + self.headers.raw)

    @property
    def content(self) -> bytes:
        if not hasattr(self, "_content"):
            raise RequestNotRead()
        return self._content

    def read(self) -> bytes:
        """
        Read and return the request content.
        """
        if not hasattr(self, "_content"):
            assert isinstance(self.stream, typing.Iterable)
            self._content = b"".join(self.stream)
            if not isinstance(self.stream, ByteStream):
                # If a streaming request has been read entirely into memory, then
                # we can replace the stream with a raw bytes implementation,
                # to ensure that any non-replayable streams can still be used.
                self.stream = ByteStream(self._content)
        return self._content

    async def aread(self) -> bytes:
        """
        Read and return the request content.
        """
        if not hasattr(self, "_content"):
            assert isinstance(self.stream, typing.AsyncIterable)
            self._content = b"".join([part async for part in self.stream])
            if not isinstance(self.stream, ByteStream):
                # If a streaming request has been read entirely into memory, then
                # we can replace the stream with a raw bytes implementation,
                # to ensure that any non-replayable streams can still be used.
                self.stream = ByteStream(self._content)
        return self._content

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        url = str(self.url)
        return f"<{class_name}({self.method!r}, {url!r})>"

    def __getstate__(self) -> dict[str, typing.Any]:
        return {
            name: value
            for name, value in self.__dict__.items()
            if name not in ["extensions", "stream"]
        }

    def __setstate__(self, state: dict[str, typing.Any]) -> None:
        for name, value in state.items():
            setattr(self, name, value)
        self.extensions = {}
        self.stream = UnattachedStream()


class Response:
    def __init__(
        self,
        status_code: int,
        *,
        headers: HeaderTypes | None = None,
        content: ResponseContent | None = None,
        text: str | None = None,
        html: str | None = None,
        json: typing.Any = None,
        stream: SyncByteStream | AsyncByteStream | None = None,
        request: Request | None = None,
        extensions: ResponseExtensions | None = None,
        history: list[Response] | None = None,
        default_encoding: str | typing.Callable[[bytes], str] = "utf-8",
    ) -> None:
        self.status_code = status_code
        self.headers = Headers(headers)

        self._request: Request | None = request

        # When follow_redirects=False and a redirect is received,
        # the client will set `response.next_request`.
        self.next_request: Request | None = None

        self.extensions = {} if extensions is None else dict(extensions)
        self.history = [] if history is None else list(history)

        self.is_closed = False
        self.is_stream_consumed = False

        self.default_encoding = default_encoding

        if stream is None:
            headers, stream = encode_response(content, text, html, json)
            self._prepare(headers)
            self.stream = stream
            if isinstance(stream, ByteStream):
                # Load the response body, except for streaming content.
                self.read()
        else:
            # There's an important distinction between `Response(content=...)`,
            # and `Response(stream=...)`.
            #
            # Using `content=...` implies automatically populated content headers,
            # of either `Content-Length: ...` or `Transfer-Encoding: chunked`.
            #
            # Using `stream=...` will not automatically include any content headers.
            #
            # As an end-user you don't really need `stream=...`. It's only
            # useful when creating response instances having received a stream
            # from the transport API.
            self.stream = stream

        self._num_bytes_downloaded = 0

    def _prepare(self, default_headers: dict[str, str]) -> None:
        for key, value in default_headers.items():
            # Ignore Transfer-Encoding if the Content-Length has been set explicitly.
            if key.lower() == "transfer-encoding" and "content-length" in self.headers:
                continue
            self.headers.setdefault(key, value)

    @property
    def elapsed(self) -> datetime.timedelta:
        """
        Returns the time taken for the complete request/response
        cycle to complete.
        """
        if not hasattr(self, "_elapsed"):
            raise RuntimeError(
                "'.elapsed' may only be accessed after the response "
                "has been read or closed."
            )
        return self._elapsed

    @elapsed.setter
    def elapsed(self, elapsed: datetime.timedelta) -> None:
        self._elapsed = elapsed

    @property
    def request(self) -> Request:
        """
        Returns the request instance associated to the current response.
        """
        if self._request is None:
            raise RuntimeError(
                "The request instance has not been set on this response."
            )
        return self._request

    @request.setter
    def request(self, value: Request) -> None:
        self._request = value

    @property
    def http_version(self) -> str:
        try:
            http_version: bytes = self.extensions["http_version"]
        except KeyError:
            return "HTTP/1.1"
        else:
            return http_version.decode("ascii", errors="ignore")

    @property
    def reason_phrase(self) -> str:
        try:
            reason_phrase: bytes = self.extensions["reason_phrase"]
        except KeyError:
            return codes.get_reason_phrase(self.status_code)
        else:
            return reason_phrase.decode("ascii", errors="ignore")

    @property
    def url(self) -> URL:
        """
        Returns the URL for which the request was made.
        """
        return self.request.url

    @property
    def content(self) -> bytes:
        if not hasattr(self, "_content"):
            raise ResponseNotRead()
        return self._content

    @property
    def text(self) -> str:
        if not hasattr(self, "_text"):
            content = self.content
            if not content:
                self._text = ""
            else:
                decoder = TextDecoder(encoding=self.encoding or "utf-8")
                self._text = "".join([decoder.decode(self.content), decoder.flush()])
        return self._text

    @property
    def encoding(self) -> str | None:
        """
        Return an encoding to use for decoding the byte content into text.
        The priority for determining this is given by...

        * `.encoding = <>` has been set explicitly.
        * The encoding as specified by the charset parameter in the Content-Type header.
        * The encoding as determined by `default_encoding`, which may either be
          a string like "utf-8" indicating the encoding to use, or may be a callable
          which enables charset autodetection.
        """
        if not hasattr(self, "_encoding"):
            encoding = self.charset_encoding
            if encoding is None or not _is_known_encoding(encoding):
                if isinstance(self.default_encoding, str):
                    encoding = self.default_encoding
                elif hasattr(self, "_content"):
                    encoding = self.default_encoding(self._content)
            self._encoding = encoding or "utf-8"
        return self._encoding

    @encoding.setter
    def encoding(self, value: str) -> None:
        """
        Set the encoding to use for decoding the byte content into text.

        If the `text` attribute has been accessed, attempting to set the
        encoding will throw a ValueError.
        """
        if hasattr(self, "_text"):
            raise ValueError(
                "Setting encoding after `text` has been accessed is not allowed."
            )
        self._encoding = value

    @property
    def charset_encoding(self) -> str | None:
        """
        Return the encoding, as specified by the Content-Type header.
        """
        content_type = self.headers.get("Content-Type")
        if content_type is None:
            return None

        return _parse_content_type_charset(content_type)

    def _get_content_decoder(self) -> ContentDecoder:
        """
        Returns a decoder instance which can be used to decode the raw byte
        content, depending on the Content-Encoding used in the response.
        """
        if not hasattr(self, "_decoder"):
            decoders: list[ContentDecoder] = []
            values = self.headers.get_list("content-encoding", split_commas=True)
            for value in values:
                value = value.strip().lower()
                try:
                    decoder_cls = SUPPORTED_DECODERS[value]
                    decoders.append(decoder_cls())
                except KeyError:
                    continue

            if len(decoders) == 1:
                self._decoder = decoders[0]
            elif len(decoders) > 1:
                self._decoder = MultiDecoder(children=decoders)
            else:
                self._decoder = IdentityDecoder()

        return self._decoder

    @property
    def is_informational(self) -> bool:
        """
        A property which is `True` for 1xx status codes, `False` otherwise.
        """
        return codes.is_informational(self.status_code)

    @property
    def is_success(self) -> bool:
        """
        A property which is `True` for 2xx status codes, `False` otherwise.
        """
        return codes.is_success(self.status_code)

    @property
    def is_redirect(self) -> bool:
        """
        A property which is `True` for 3xx status codes, `False` otherwise.

        Note that not all responses with a 3xx status code indicate a URL redirect.

        Use `response.has_redirect_location` to determine responses with a properly
        formed URL redirection.
        """
        return codes.is_redirect(self.status_code)

    @property
    def is_client_error(self) -> bool:
        """
        A property which is `True` for 4xx status codes, `False` otherwise.
        """
        return codes.is_client_error(self.status_code)

    @property
    def is_server_error(self) -> bool:
        """
        A property which is `True` for 5xx status codes, `False` otherwise.
        """
        return codes.is_server_error(self.status_code)

    @property
    def is_error(self) -> bool:
        """
        A property which is `True` for 4xx and 5xx status codes, `False` otherwise.
        """
        return codes.is_error(self.status_code)

    @property
    def has_redirect_location(self) -> bool:
        """
        Returns True for 3xx responses with a properly formed URL redirection,
        `False` otherwise.
        """
        return (
            self.status_code
            in (
                # 301 (Cacheable redirect. Method may change to GET.)
                codes.MOVED_PERMANENTLY,
                # 302 (Uncacheable redirect. Method may change to GET.)
                codes.FOUND,
                # 303 (Client should make a GET or HEAD request.)
                codes.SEE_OTHER,
                # 307 (Equiv. 302, but retain method)
                codes.TEMPORARY_REDIRECT,
                # 308 (Equiv. 301, but retain method)
                codes.PERMANENT_REDIRECT,
            )
            and "Location" in self.headers
        )

    def raise_for_status(self) -> Response:
        """
        Raise the `HTTPStatusError` if one occurred.
        """
        request = self._request
        if request is None:
            raise RuntimeError(
                "Cannot call `raise_for_status` as the request "
                "instance has not been set on this response."
            )

        if self.is_success:
            return self

        if self.has_redirect_location:
            message = (
                "{error_type} '{0.status_code} {0.reason_phrase}' for url '{0.url}'\n"
                "Redirect location: '{0.headers[location]}'\n"
                "For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/{0.status_code}"
            )
        else:
            message = (
                "{error_type} '{0.status_code} {0.reason_phrase}' for url '{0.url}'\n"
                "For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/{0.status_code}"
            )

        status_class = self.status_code // 100
        error_types = {
            1: "Informational response",
            3: "Redirect response",
            4: "Client error",
            5: "Server error",
        }
        error_type = error_types.get(status_class, "Invalid status code")
        message = message.format(self, error_type=error_type)
        raise HTTPStatusError(message, request=request, response=self)

    def json(self, **kwargs: typing.Any) -> typing.Any:
        return jsonlib.loads(self.content, **kwargs)

    @property
    def cookies(self) -> Cookies:
        if not hasattr(self, "_cookies"):
            self._cookies = Cookies()
            self._cookies.extract_cookies(self)
        return self._cookies

    @property
    def links(self) -> dict[str | None, dict[str, str]]:
        """
        Returns the parsed header links of the response, if any
        """
        header = self.headers.get("link")
        if header is None:
            return {}

        return {
            (link.get("rel") or link.get("url")): link
            for link in _parse_header_links(header)
        }

    @property
    def num_bytes_downloaded(self) -> int:
        return self._num_bytes_downloaded

    def __repr__(self) -> str:
        return f"<Response [{self.status_code} {self.reason_phrase}]>"

    def __getstate__(self) -> dict[str, typing.Any]:
        return {
            name: value
            for name, value in self.__dict__.items()
            if name not in ["extensions", "stream", "is_closed", "_decoder"]
        }

    def __setstate__(self, state: dict[str, typing.Any]) -> None:
        for name, value in state.items():
            setattr(self, name, value)
        self.is_closed = True
        self.extensions = {}
        self.stream = UnattachedStream()

    def read(self) -> bytes:
        """
        Read and return the response content.
        """
        if not hasattr(self, "_content"):
            self._content = b"".join(self.iter_bytes())
        return self._content

    def iter_bytes(self, chunk_size: int | None = None) -> typing.Iterator[bytes]:
        """
        A byte-iterator over the decoded response content.
        This allows us to handle gzip, deflate, brotli, and zstd encoded responses.
        """
        if hasattr(self, "_content"):
            chunk_size = len(self._content) if chunk_size is None else chunk_size
            for i in range(0, len(self._content), max(chunk_size, 1)):
                yield self._content[i : i + chunk_size]
        else:
            decoder = self._get_content_decoder()
            chunker = ByteChunker(chunk_size=chunk_size)
            with request_context(request=self._request):
                for raw_bytes in self.iter_raw():
                    decoded = decoder.decode(raw_bytes)
                    for chunk in chunker.decode(decoded):
                        yield chunk
                decoded = decoder.flush()
                for chunk in chunker.decode(decoded):
                    yield chunk  # pragma: no cover
                for chunk in chunker.flush():
                    yield chunk

    def iter_text(self, chunk_size: int | None = None) -> typing.Iterator[str]:
        """
        A str-iterator over the decoded response content
        that handles both gzip, deflate, etc but also detects the content's
        string encoding.
        """
        decoder = TextDecoder(encoding=self.encoding or "utf-8")
        chunker = TextChunker(chunk_size=chunk_size)
        with request_context(request=self._request):
            for byte_content in self.iter_bytes():
                text_content = decoder.decode(byte_content)
                for chunk in chunker.decode(text_content):
                    yield chunk
            text_content = decoder.flush()
            for chunk in chunker.decode(text_content):
                yield chunk  # pragma: no cover
            for chunk in chunker.flush():
                yield chunk

    def iter_lines(self) -> typing.Iterator[str]:
        decoder = LineDecoder()
        with request_context(request=self._request):
            for text in self.iter_text():
                for line in decoder.decode(text):
                    yield line
            for line in decoder.flush():
                yield line

    def iter_raw(self, chunk_size: int | None = None) -> typing.Iterator[bytes]:
        """
        A byte-iterator over the raw response content.
        """
        if self.is_stream_consumed:
            raise StreamConsumed()
        if self.is_closed:
            raise StreamClosed()
        if not isinstance(self.stream, SyncByteStream):
            raise RuntimeError("Attempted to call a sync iterator on an async stream.")

        self.is_stream_consumed = True
        self._num_bytes_downloaded = 0
        chunker = ByteChunker(chunk_size=chunk_size)

        with request_context(request=self._request):
            for raw_stream_bytes in self.stream:
                self._num_bytes_downloaded += len(raw_stream_bytes)
                for chunk in chunker.decode(raw_stream_bytes):
                    yield chunk

        for chunk in chunker.flush():
            yield chunk

        self.close()

    def close(self) -> None:
        """
        Close the response and release the connection.
        Automatically called if the response body is read to completion.
        """
        if not isinstance(self.stream, SyncByteStream):
            raise RuntimeError("Attempted to call an sync close on an async stream.")

        if not self.is_closed:
            self.is_closed = True
            with request_context(request=self._request):
                self.stream.close()

    async def aread(self) -> bytes:
        """
        Read and return the response content.
        """
        if not hasattr(self, "_content"):
            self._content = b"".join([part async for part in self.aiter_bytes()])
        return self._content

    async def aiter_bytes(
        self, chunk_size: int | None = None
    ) -> typing.AsyncIterator[bytes]:
        """
        A byte-iterator over the decoded response content.
        This allows us to handle gzip, deflate, brotli, and zstd encoded responses.
        """
        if hasattr(self, "_content"):
            chunk_size = len(self._content) if chunk_size is None else chunk_size
            for i in range(0, len(self._content), max(chunk_size, 1)):
                yield self._content[i : i + chunk_size]
        else:
            decoder = self._get_content_decoder()
            chunker = ByteChunker(chunk_size=chunk_size)
            with request_context(request=self._request):
                async for raw_bytes in self.aiter_raw():
                    decoded = decoder.decode(raw_bytes)
                    for chunk in chunker.decode(decoded):
                        yield chunk
                decoded = decoder.flush()
                for chunk in chunker.decode(decoded):
                    yield chunk  # pragma: no cover
                for chunk in chunker.flush():
                    yield chunk

    async def aiter_text(
        self, chunk_size: int | None = None
    ) -> typing.AsyncIterator[str]:
        """
        A str-iterator over the decoded response content
        that handles both gzip, deflate, etc but also detects the content's
        string encoding.
        """
        decoder = TextDecoder(encoding=self.encoding or "utf-8")
        chunker = TextChunker(chunk_size=chunk_size)
        with request_context(request=self._request):
            async for byte_content in self.aiter_bytes():
                text_content = decoder.decode(byte_content)
                for chunk in chunker.decode(text_content):
                    yield chunk
            text_content = decoder.flush()
            for chunk in chunker.decode(text_content):
                yield chunk  # pragma: no cover
            for chunk in chunker.flush():
                yield chunk

    async def aiter_lines(self) -> typing.AsyncIterator[str]:
        decoder = LineDecoder()
        with request_context(request=self._request):
            async for text in self.aiter_text():
                for line in decoder.decode(text):
                    yield line
            for line in decoder.flush():
                yield line

    async def aiter_raw(
        self, chunk_size: int | None = None
    ) -> typing.AsyncIterator[bytes]:
        """
        A byte-iterator over the raw response content.
        """
        if self.is_stream_consumed:
            raise StreamConsumed()
        if self.is_closed:
            raise StreamClosed()
        if not isinstance(self.stream, AsyncByteStream):
            raise RuntimeError("Attempted to call an async iterator on an sync stream.")

        self.is_stream_consumed = True
        self._num_bytes_downloaded = 0
        chunker = ByteChunker(chunk_size=chunk_size)

        with request_context(request=self._request):
            async for raw_stream_bytes in self.stream:
                self._num_bytes_downloaded += len(raw_stream_bytes)
                for chunk in chunker.decode(raw_stream_bytes):
                    yield chunk

        for chunk in chunker.flush():
            yield chunk

        await self.aclose()

    async def aclose(self) -> None:
        """
        Close the response and release the connection.
        Automatically called if the response body is read to completion.
        """
        if not isinstance(self.stream, AsyncByteStream):
            raise RuntimeError("Attempted to call an async close on an sync stream.")

        if not self.is_closed:
            self.is_closed = True
            with request_context(request=self._request):
                await self.stream.aclose()


class Cookies(typing.MutableMapping[str, str]):
    """
    HTTP Cookies, as a mutable mapping.
    """

    def __init__(self, cookies: CookieTypes | None = None) -> None:
        if cookies is None or isinstance(cookies, dict):
            self.jar = CookieJar()
            if isinstance(cookies, dict):
                for key, value in cookies.items():
                    self.set(key, value)
        elif isinstance(cookies, list):
            self.jar = CookieJar()
            for key, value in cookies:
                self.set(key, value)
        elif isinstance(cookies, Cookies):
            self.jar = CookieJar()
            for cookie in cookies.jar:
                self.jar.set_cookie(cookie)
        else:
            self.jar = cookies

    def extract_cookies(self, response: Response) -> None:
        """
        Loads any cookies based on the response `Set-Cookie` headers.
        """
        urllib_response = self._CookieCompatResponse(response)
        urllib_request = self._CookieCompatRequest(response.request)

        self.jar.extract_cookies(urllib_response, urllib_request)  # type: ignore

    def set_cookie_header(self, request: Request) -> None:
        """
        Sets an appropriate 'Cookie:' HTTP header on the `Request`.
        """
        urllib_request = self._CookieCompatRequest(request)
        self.jar.add_cookie_header(urllib_request)

    def set(self, name: str, value: str, domain: str = "", path: str = "/") -> None:
        """
        Set a cookie value by name. May optionally include domain and path.
        """
        kwargs = {
            "version": 0,
            "name": name,
            "value": value,
            "port": None,
            "port_specified": False,
            "domain": domain,
            "domain_specified": bool(domain),
            "domain_initial_dot": domain.startswith("."),
            "path": path,
            "path_specified": bool(path),
            "secure": False,
            "expires": None,
            "discard": True,
            "comment": None,
            "comment_url": None,
            "rest": {"HttpOnly": None},
            "rfc2109": False,
        }
        cookie = Cookie(**kwargs)  # type: ignore
        self.jar.set_cookie(cookie)

    def get(  # type: ignore
        self,
        name: str,
        default: str | None = None,
        domain: str | None = None,
        path: str | None = None,
    ) -> str | None:
        """
        Get a cookie by name. May optionally include domain and path
        in order to specify exactly which cookie to retrieve.
        """
        value = None
        for cookie in self.jar:
            if cookie.name == name:
                if domain is None or cookie.domain == domain:
                    if path is None or cookie.path == path:
                        if value is not None:
                            message = f"Multiple cookies exist with name={name}"
                            raise CookieConflict(message)
                        value = cookie.value

        if value is None:
            return default
        return value

    def delete(
        self,
        name: str,
        domain: str | None = None,
        path: str | None = None,
    ) -> None:
        """
        Delete a cookie by name. May optionally include domain and path
        in order to specify exactly which cookie to delete.
        """
        if domain is not None and path is not None:
            return self.jar.clear(domain, path, name)

        remove = [
            cookie
            for cookie in self.jar
            if cookie.name == name
            and (domain is None or cookie.domain == domain)
            and (path is None or cookie.path == path)
        ]

        for cookie in remove:
            self.jar.clear(cookie.domain, cookie.path, cookie.name)

    def clear(self, domain: str | None = None, path: str | None = None) -> None:
        """
        Delete all cookies. Optionally include a domain and path in
        order to only delete a subset of all the cookies.
        """
        args = []
        if domain is not None:
            args.append(domain)
        if path is not None:
            assert domain is not None
            args.append(path)
        self.jar.clear(*args)

    def update(self, cookies: CookieTypes | None = None) -> None:  # type: ignore
        cookies = Cookies(cookies)
        for cookie in cookies.jar:
            self.jar.set_cookie(cookie)

    def __setitem__(self, name: str, value: str) -> None:
        return self.set(name, value)

    def __getitem__(self, name: str) -> str:
        value = self.get(name)
        if value is None:
            raise KeyError(name)
        return value

    def __delitem__(self, name: str) -> None:
        return self.delete(name)

    def __len__(self) -> int:
        return len(self.jar)

    def __iter__(self) -> typing.Iterator[str]:
        return (cookie.name for cookie in self.jar)

    def __bool__(self) -> bool:
        for _ in self.jar:
            return True
        return False

    def __repr__(self) -> str:
        cookies_repr = ", ".join(
            [
                f"<Cookie {cookie.name}={cookie.value} for {cookie.domain} />"
                for cookie in self.jar
            ]
        )

        return f"<Cookies[{cookies_repr}]>"

    class _CookieCompatRequest(urllib.request.Request):
        """
        Wraps a `Request` instance up in a compatibility interface suitable
        for use with `CookieJar` operations.
        """

        def __init__(self, request: Request) -> None:
            super().__init__(
                url=str(request.url),
                headers=dict(request.headers),
                method=request.method,
            )
            self.request = request

        def add_unredirected_header(self, key: str, value: str) -> None:
            super().add_unredirected_header(key, value)
            self.request.headers[key] = value

    class _CookieCompatResponse:
        """
        Wraps a `Request` instance up in a compatibility interface suitable
        for use with `CookieJar` operations.
        """

        def __init__(self, response: Response) -> None:
            self.response = response

        def info(self) -> email.message.Message:
            info = email.message.Message()
            for key, value in self.response.headers.multi_items():
                # Note that setting `info[key]` here is an "append" operation,
                # not a "replace" operation.
                # https://docs.python.org/3/library/email.compat32-message.html#email.message.Message.__setitem__
                info[key] = value
            return info

# === NexusCore/openenv\Lib\site-packages\google\protobuf\descriptor_pool.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Provides DescriptorPool to use as a container for proto2 descriptors.

The DescriptorPool is used in conjection with a DescriptorDatabase to maintain
a collection of protocol buffer descriptors for use when dynamically creating
message types at runtime.

For most applications protocol buffers should be used via modules generated by
the protocol buffer compiler tool. This should only be used when the type of
protocol buffers used in an application or library cannot be predetermined.

Below is a straightforward example on how to use this class::

  pool = DescriptorPool()
  file_descriptor_protos = [ ... ]
  for file_descriptor_proto in file_descriptor_protos:
    pool.Add(file_descriptor_proto)
  my_message_descriptor = pool.FindMessageTypeByName('some.package.MessageType')

The message descriptor can be used in conjunction with the message_factory
module in order to create a protocol buffer class that can be encoded and
decoded.

If you want to get a Python class for the specified proto, use the
helper functions inside google.protobuf.message_factory
directly instead of this class.
"""

__author__ = 'matthewtoia@google.com (Matt Toia)'

import collections
import warnings

from google.protobuf import descriptor
from google.protobuf import descriptor_database
from google.protobuf import text_encoding
from google.protobuf.internal import python_message

_USE_C_DESCRIPTORS = descriptor._USE_C_DESCRIPTORS  # pylint: disable=protected-access


def _Deprecated(func):
  """Mark functions as deprecated."""

  def NewFunc(*args, **kwargs):
    warnings.warn(
        'Call to deprecated function %s(). Note: Do add unlinked descriptors '
        'to descriptor_pool is wrong. Please use Add() or AddSerializedFile() '
        'instead. This function will be removed soon.' % func.__name__,
        category=DeprecationWarning)
    return func(*args, **kwargs)
  NewFunc.__name__ = func.__name__
  NewFunc.__doc__ = func.__doc__
  NewFunc.__dict__.update(func.__dict__)
  return NewFunc


def _NormalizeFullyQualifiedName(name):
  """Remove leading period from fully-qualified type name.

  Due to b/13860351 in descriptor_database.py, types in the root namespace are
  generated with a leading period. This function removes that prefix.

  Args:
    name (str): The fully-qualified symbol name.

  Returns:
    str: The normalized fully-qualified symbol name.
  """
  return name.lstrip('.')


def _OptionsOrNone(descriptor_proto):
  """Returns the value of the field `options`, or None if it is not set."""
  if descriptor_proto.HasField('options'):
    return descriptor_proto.options
  else:
    return None


def _IsMessageSetExtension(field):
  return (field.is_extension and
          field.containing_type.has_options and
          field.containing_type.GetOptions().message_set_wire_format and
          field.type == descriptor.FieldDescriptor.TYPE_MESSAGE and
          field.label == descriptor.FieldDescriptor.LABEL_OPTIONAL)


class DescriptorPool(object):
  """A collection of protobufs dynamically constructed by descriptor protos."""

  if _USE_C_DESCRIPTORS:

   def __new__(cls, descriptor_db=None):
     # pylint: disable=protected-access
     return descriptor._message.DescriptorPool(descriptor_db)

  def __init__(
      self, descriptor_db=None, use_deprecated_legacy_json_field_conflicts=False
  ):
    """Initializes a Pool of proto buffs.

    The descriptor_db argument to the constructor is provided to allow
    specialized file descriptor proto lookup code to be triggered on demand. An
    example would be an implementation which will read and compile a file
    specified in a call to FindFileByName() and not require the call to Add()
    at all. Results from this database will be cached internally here as well.

    Args:
      descriptor_db: A secondary source of file descriptors.
      use_deprecated_legacy_json_field_conflicts: Unused, for compatibility with
        C++.
    """

    self._internal_db = descriptor_database.DescriptorDatabase()
    self._descriptor_db = descriptor_db
    self._descriptors = {}
    self._enum_descriptors = {}
    self._service_descriptors = {}
    self._file_descriptors = {}
    self._toplevel_extensions = {}
    self._top_enum_values = {}
    # We store extensions in two two-level mappings: The first key is the
    # descriptor of the message being extended, the second key is the extension
    # full name or its tag number.
    self._extensions_by_name = collections.defaultdict(dict)
    self._extensions_by_number = collections.defaultdict(dict)

  def _CheckConflictRegister(self, desc, desc_name, file_name):
    """Check if the descriptor name conflicts with another of the same name.

    Args:
      desc: Descriptor of a message, enum, service, extension or enum value.
      desc_name (str): the full name of desc.
      file_name (str): The file name of descriptor.
    """
    for register, descriptor_type in [
        (self._descriptors, descriptor.Descriptor),
        (self._enum_descriptors, descriptor.EnumDescriptor),
        (self._service_descriptors, descriptor.ServiceDescriptor),
        (self._toplevel_extensions, descriptor.FieldDescriptor),
        (self._top_enum_values, descriptor.EnumValueDescriptor)]:
      if desc_name in register:
        old_desc = register[desc_name]
        if isinstance(old_desc, descriptor.EnumValueDescriptor):
          old_file = old_desc.type.file.name
        else:
          old_file = old_desc.file.name

        if not isinstance(desc, descriptor_type) or (
            old_file != file_name):
          error_msg = ('Conflict register for file "' + file_name +
                       '": ' + desc_name +
                       ' is already defined in file "' +
                       old_file + '". Please fix the conflict by adding '
                       'package name on the proto file, or use different '
                       'name for the duplication.')
          if isinstance(desc, descriptor.EnumValueDescriptor):
            error_msg += ('\nNote: enum values appear as '
                          'siblings of the enum type instead of '
                          'children of it.')

          raise TypeError(error_msg)

        return

  def Add(self, file_desc_proto):
    """Adds the FileDescriptorProto and its types to this pool.

    Args:
      file_desc_proto (FileDescriptorProto): The file descriptor to add.
    """

    self._internal_db.Add(file_desc_proto)

  def AddSerializedFile(self, serialized_file_desc_proto):
    """Adds the FileDescriptorProto and its types to this pool.

    Args:
      serialized_file_desc_proto (bytes): A bytes string, serialization of the
        :class:`FileDescriptorProto` to add.

    Returns:
      FileDescriptor: Descriptor for the added file.
    """

    # pylint: disable=g-import-not-at-top
    from google.protobuf import descriptor_pb2
    file_desc_proto = descriptor_pb2.FileDescriptorProto.FromString(
        serialized_file_desc_proto)
    file_desc = self._ConvertFileProtoToFileDescriptor(file_desc_proto)
    file_desc.serialized_pb = serialized_file_desc_proto
    return file_desc

  # Add Descriptor to descriptor pool is deprecated. Please use Add()
  # or AddSerializedFile() to add a FileDescriptorProto instead.
  @_Deprecated
  def AddDescriptor(self, desc):
    self._AddDescriptor(desc)

  # Never call this method. It is for internal usage only.
  def _AddDescriptor(self, desc):
    """Adds a Descriptor to the pool, non-recursively.

    If the Descriptor contains nested messages or enums, the caller must
    explicitly register them. This method also registers the FileDescriptor
    associated with the message.

    Args:
      desc: A Descriptor.
    """
    if not isinstance(desc, descriptor.Descriptor):
      raise TypeError('Expected instance of descriptor.Descriptor.')

    self._CheckConflictRegister(desc, desc.full_name, desc.file.name)

    self._descriptors[desc.full_name] = desc
    self._AddFileDescriptor(desc.file)

  # Never call this method. It is for internal usage only.
  def _AddEnumDescriptor(self, enum_desc):
    """Adds an EnumDescriptor to the pool.

    This method also registers the FileDescriptor associated with the enum.

    Args:
      enum_desc: An EnumDescriptor.
    """

    if not isinstance(enum_desc, descriptor.EnumDescriptor):
      raise TypeError('Expected instance of descriptor.EnumDescriptor.')

    file_name = enum_desc.file.name
    self._CheckConflictRegister(enum_desc, enum_desc.full_name, file_name)
    self._enum_descriptors[enum_desc.full_name] = enum_desc

    # Top enum values need to be indexed.
    # Count the number of dots to see whether the enum is toplevel or nested
    # in a message. We cannot use enum_desc.containing_type at this stage.
    if enum_desc.file.package:
      top_level = (enum_desc.full_name.count('.')
                   - enum_desc.file.package.count('.') == 1)
    else:
      top_level = enum_desc.full_name.count('.') == 0
    if top_level:
      file_name = enum_desc.file.name
      package = enum_desc.file.package
      for enum_value in enum_desc.values:
        full_name = _NormalizeFullyQualifiedName(
            '.'.join((package, enum_value.name)))
        self._CheckConflictRegister(enum_value, full_name, file_name)
        self._top_enum_values[full_name] = enum_value
    self._AddFileDescriptor(enum_desc.file)

  # Add ServiceDescriptor to descriptor pool is deprecated. Please use Add()
  # or AddSerializedFile() to add a FileDescriptorProto instead.
  @_Deprecated
  def AddServiceDescriptor(self, service_desc):
    self._AddServiceDescriptor(service_desc)

  # Never call this method. It is for internal usage only.
  def _AddServiceDescriptor(self, service_desc):
    """Adds a ServiceDescriptor to the pool.

    Args:
      service_desc: A ServiceDescriptor.
    """

    if not isinstance(service_desc, descriptor.ServiceDescriptor):
      raise TypeError('Expected instance of descriptor.ServiceDescriptor.')

    self._CheckConflictRegister(service_desc, service_desc.full_name,
                                service_desc.file.name)
    self._service_descriptors[service_desc.full_name] = service_desc

  # Add ExtensionDescriptor to descriptor pool is deprecated. Please use Add()
  # or AddSerializedFile() to add a FileDescriptorProto instead.
  @_Deprecated
  def AddExtensionDescriptor(self, extension):
    self._AddExtensionDescriptor(extension)

  # Never call this method. It is for internal usage only.
  def _AddExtensionDescriptor(self, extension):
    """Adds a FieldDescriptor describing an extension to the pool.

    Args:
      extension: A FieldDescriptor.

    Raises:
      AssertionError: when another extension with the same number extends the
        same message.
      TypeError: when the specified extension is not a
        descriptor.FieldDescriptor.
    """
    if not (isinstance(extension, descriptor.FieldDescriptor) and
            extension.is_extension):
      raise TypeError('Expected an extension descriptor.')

    if extension.extension_scope is None:
      self._CheckConflictRegister(
          extension, extension.full_name, extension.file.name)
      self._toplevel_extensions[extension.full_name] = extension

    try:
      existing_desc = self._extensions_by_number[
          extension.containing_type][extension.number]
    except KeyError:
      pass
    else:
      if extension is not existing_desc:
        raise AssertionError(
            'Extensions "%s" and "%s" both try to extend message type "%s" '
            'with field number %d.' %
            (extension.full_name, existing_desc.full_name,
             extension.containing_type.full_name, extension.number))

    self._extensions_by_number[extension.containing_type][
        extension.number] = extension
    self._extensions_by_name[extension.containing_type][
        extension.full_name] = extension

    # Also register MessageSet extensions with the type name.
    if _IsMessageSetExtension(extension):
      self._extensions_by_name[extension.containing_type][
          extension.message_type.full_name] = extension

    if hasattr(extension.containing_type, '_concrete_class'):
      python_message._AttachFieldHelpers(
          extension.containing_type._concrete_class, extension)

  @_Deprecated
  def AddFileDescriptor(self, file_desc):
    self._InternalAddFileDescriptor(file_desc)

  # Never call this method. It is for internal usage only.
  def _InternalAddFileDescriptor(self, file_desc):
    """Adds a FileDescriptor to the pool, non-recursively.

    If the FileDescriptor contains messages or enums, the caller must explicitly
    register them.

    Args:
      file_desc: A FileDescriptor.
    """

    self._AddFileDescriptor(file_desc)

  def _AddFileDescriptor(self, file_desc):
    """Adds a FileDescriptor to the pool, non-recursively.

    If the FileDescriptor contains messages or enums, the caller must explicitly
    register them.

    Args:
      file_desc: A FileDescriptor.
    """

    if not isinstance(file_desc, descriptor.FileDescriptor):
      raise TypeError('Expected instance of descriptor.FileDescriptor.')
    self._file_descriptors[file_desc.name] = file_desc

  def FindFileByName(self, file_name):
    """Gets a FileDescriptor by file name.

    Args:
      file_name (str): The path to the file to get a descriptor for.

    Returns:
      FileDescriptor: The descriptor for the named file.

    Raises:
      KeyError: if the file cannot be found in the pool.
    """

    try:
      return self._file_descriptors[file_name]
    except KeyError:
      pass

    try:
      file_proto = self._internal_db.FindFileByName(file_name)
    except KeyError as error:
      if self._descriptor_db:
        file_proto = self._descriptor_db.FindFileByName(file_name)
      else:
        raise error
    if not file_proto:
      raise KeyError('Cannot find a file named %s' % file_name)
    return self._ConvertFileProtoToFileDescriptor(file_proto)

  def FindFileContainingSymbol(self, symbol):
    """Gets the FileDescriptor for the file containing the specified symbol.

    Args:
      symbol (str): The name of the symbol to search for.

    Returns:
      FileDescriptor: Descriptor for the file that contains the specified
      symbol.

    Raises:
      KeyError: if the file cannot be found in the pool.
    """

    symbol = _NormalizeFullyQualifiedName(symbol)
    try:
      return self._InternalFindFileContainingSymbol(symbol)
    except KeyError:
      pass

    try:
      # Try fallback database. Build and find again if possible.
      self._FindFileContainingSymbolInDb(symbol)
      return self._InternalFindFileContainingSymbol(symbol)
    except KeyError:
      raise KeyError('Cannot find a file containing %s' % symbol)

  def _InternalFindFileContainingSymbol(self, symbol):
    """Gets the already built FileDescriptor containing the specified symbol.

    Args:
      symbol (str): The name of the symbol to search for.

    Returns:
      FileDescriptor: Descriptor for the file that contains the specified
      symbol.

    Raises:
      KeyError: if the file cannot be found in the pool.
    """
    try:
      return self._descriptors[symbol].file
    except KeyError:
      pass

    try:
      return self._enum_descriptors[symbol].file
    except KeyError:
      pass

    try:
      return self._service_descriptors[symbol].file
    except KeyError:
      pass

    try:
      return self._top_enum_values[symbol].type.file
    except KeyError:
      pass

    try:
      return self._toplevel_extensions[symbol].file
    except KeyError:
      pass

    # Try fields, enum values and nested extensions inside a message.
    top_name, _, sub_name = symbol.rpartition('.')
    try:
      message = self.FindMessageTypeByName(top_name)
      assert (sub_name in message.extensions_by_name or
              sub_name in message.fields_by_name or
              sub_name in message.enum_values_by_name)
      return message.file
    except (KeyError, AssertionError):
      raise KeyError('Cannot find a file containing %s' % symbol)

  def FindMessageTypeByName(self, full_name):
    """Loads the named descriptor from the pool.

    Args:
      full_name (str): The full name of the descriptor to load.

    Returns:
      Descriptor: The descriptor for the named type.

    Raises:
      KeyError: if the message cannot be found in the pool.
    """

    full_name = _NormalizeFullyQualifiedName(full_name)
    if full_name not in self._descriptors:
      self._FindFileContainingSymbolInDb(full_name)
    return self._descriptors[full_name]

  def FindEnumTypeByName(self, full_name):
    """Loads the named enum descriptor from the pool.

    Args:
      full_name (str): The full name of the enum descriptor to load.

    Returns:
      EnumDescriptor: The enum descriptor for the named type.

    Raises:
      KeyError: if the enum cannot be found in the pool.
    """

    full_name = _NormalizeFullyQualifiedName(full_name)
    if full_name not in self._enum_descriptors:
      self._FindFileContainingSymbolInDb(full_name)
    return self._enum_descriptors[full_name]

  def FindFieldByName(self, full_name):
    """Loads the named field descriptor from the pool.

    Args:
      full_name (str): The full name of the field descriptor to load.

    Returns:
      FieldDescriptor: The field descriptor for the named field.

    Raises:
      KeyError: if the field cannot be found in the pool.
    """
    full_name = _NormalizeFullyQualifiedName(full_name)
    message_name, _, field_name = full_name.rpartition('.')
    message_descriptor = self.FindMessageTypeByName(message_name)
    return message_descriptor.fields_by_name[field_name]

  def FindOneofByName(self, full_name):
    """Loads the named oneof descriptor from the pool.

    Args:
      full_name (str): The full name of the oneof descriptor to load.

    Returns:
      OneofDescriptor: The oneof descriptor for the named oneof.

    Raises:
      KeyError: if the oneof cannot be found in the pool.
    """
    full_name = _NormalizeFullyQualifiedName(full_name)
    message_name, _, oneof_name = full_name.rpartition('.')
    message_descriptor = self.FindMessageTypeByName(message_name)
    return message_descriptor.oneofs_by_name[oneof_name]

  def FindExtensionByName(self, full_name):
    """Loads the named extension descriptor from the pool.

    Args:
      full_name (str): The full name of the extension descriptor to load.

    Returns:
      FieldDescriptor: The field descriptor for the named extension.

    Raises:
      KeyError: if the extension cannot be found in the pool.
    """
    full_name = _NormalizeFullyQualifiedName(full_name)
    try:
      # The proto compiler does not give any link between the FileDescriptor
      # and top-level extensions unless the FileDescriptorProto is added to
      # the DescriptorDatabase, but this can impact memory usage.
      # So we registered these extensions by name explicitly.
      return self._toplevel_extensions[full_name]
    except KeyError:
      pass
    message_name, _, extension_name = full_name.rpartition('.')
    try:
      # Most extensions are nested inside a message.
      scope = self.FindMessageTypeByName(message_name)
    except KeyError:
      # Some extensions are defined at file scope.
      scope = self._FindFileContainingSymbolInDb(full_name)
    return scope.extensions_by_name[extension_name]

  def FindExtensionByNumber(self, message_descriptor, number):
    """Gets the extension of the specified message with the specified number.

    Extensions have to be registered to this pool by calling :func:`Add` or
    :func:`AddExtensionDescriptor`.

    Args:
      message_descriptor (Descriptor): descriptor of the extended message.
      number (int): Number of the extension field.

    Returns:
      FieldDescriptor: The descriptor for the extension.

    Raises:
      KeyError: when no extension with the given number is known for the
        specified message.
    """
    try:
      return self._extensions_by_number[message_descriptor][number]
    except KeyError:
      self._TryLoadExtensionFromDB(message_descriptor, number)
      return self._extensions_by_number[message_descriptor][number]

  def FindAllExtensions(self, message_descriptor):
    """Gets all the known extensions of a given message.

    Extensions have to be registered to this pool by build related
    :func:`Add` or :func:`AddExtensionDescriptor`.

    Args:
      message_descriptor (Descriptor): Descriptor of the extended message.

    Returns:
      list[FieldDescriptor]: Field descriptors describing the extensions.
    """
    # Fallback to descriptor db if FindAllExtensionNumbers is provided.
    if self._descriptor_db and hasattr(
        self._descriptor_db, 'FindAllExtensionNumbers'):
      full_name = message_descriptor.full_name
      all_numbers = self._descriptor_db.FindAllExtensionNumbers(full_name)
      for number in all_numbers:
        if number in self._extensions_by_number[message_descriptor]:
          continue
        self._TryLoadExtensionFromDB(message_descriptor, number)

    return list(self._extensions_by_number[message_descriptor].values())

  def _TryLoadExtensionFromDB(self, message_descriptor, number):
    """Try to Load extensions from descriptor db.

    Args:
      message_descriptor: descriptor of the extended message.
      number: the extension number that needs to be loaded.
    """
    if not self._descriptor_db:
      return
    # Only supported when FindFileContainingExtension is provided.
    if not hasattr(
        self._descriptor_db, 'FindFileContainingExtension'):
      return

    full_name = message_descriptor.full_name
    file_proto = self._descriptor_db.FindFileContainingExtension(
        full_name, number)

    if file_proto is None:
      return

    try:
      self._ConvertFileProtoToFileDescriptor(file_proto)
    except:
      warn_msg = ('Unable to load proto file %s for extension number %d.' %
                  (file_proto.name, number))
      warnings.warn(warn_msg, RuntimeWarning)

  def FindServiceByName(self, full_name):
    """Loads the named service descriptor from the pool.

    Args:
      full_name (str): The full name of the service descriptor to load.

    Returns:
      ServiceDescriptor: The service descriptor for the named service.

    Raises:
      KeyError: if the service cannot be found in the pool.
    """
    full_name = _NormalizeFullyQualifiedName(full_name)
    if full_name not in self._service_descriptors:
      self._FindFileContainingSymbolInDb(full_name)
    return self._service_descriptors[full_name]

  def FindMethodByName(self, full_name):
    """Loads the named service method descriptor from the pool.

    Args:
      full_name (str): The full name of the method descriptor to load.

    Returns:
      MethodDescriptor: The method descriptor for the service method.

    Raises:
      KeyError: if the method cannot be found in the pool.
    """
    full_name = _NormalizeFullyQualifiedName(full_name)
    service_name, _, method_name = full_name.rpartition('.')
    service_descriptor = self.FindServiceByName(service_name)
    return service_descriptor.methods_by_name[method_name]

  def _FindFileContainingSymbolInDb(self, symbol):
    """Finds the file in descriptor DB containing the specified symbol.

    Args:
      symbol (str): The name of the symbol to search for.

    Returns:
      FileDescriptor: The file that contains the specified symbol.

    Raises:
      KeyError: if the file cannot be found in the descriptor database.
    """
    try:
      file_proto = self._internal_db.FindFileContainingSymbol(symbol)
    except KeyError as error:
      if self._descriptor_db:
        file_proto = self._descriptor_db.FindFileContainingSymbol(symbol)
      else:
        raise error
    if not file_proto:
      raise KeyError('Cannot find a file containing %s' % symbol)
    return self._ConvertFileProtoToFileDescriptor(file_proto)

  def _ConvertFileProtoToFileDescriptor(self, file_proto):
    """Creates a FileDescriptor from a proto or returns a cached copy.

    This method also has the side effect of loading all the symbols found in
    the file into the appropriate dictionaries in the pool.

    Args:
      file_proto: The proto to convert.

    Returns:
      A FileDescriptor matching the passed in proto.
    """
    if file_proto.name not in self._file_descriptors:
      built_deps = list(self._GetDeps(file_proto.dependency))
      direct_deps = [self.FindFileByName(n) for n in file_proto.dependency]
      public_deps = [direct_deps[i] for i in file_proto.public_dependency]

      file_descriptor = descriptor.FileDescriptor(
          pool=self,
          name=file_proto.name,
          package=file_proto.package,
          syntax=file_proto.syntax,
          options=_OptionsOrNone(file_proto),
          serialized_pb=file_proto.SerializeToString(),
          dependencies=direct_deps,
          public_dependencies=public_deps,
          # pylint: disable=protected-access
          create_key=descriptor._internal_create_key)
      scope = {}

      # This loop extracts all the message and enum types from all the
      # dependencies of the file_proto. This is necessary to create the
      # scope of available message types when defining the passed in
      # file proto.
      for dependency in built_deps:
        scope.update(self._ExtractSymbols(
            dependency.message_types_by_name.values()))
        scope.update((_PrefixWithDot(enum.full_name), enum)
                     for enum in dependency.enum_types_by_name.values())

      for message_type in file_proto.message_type:
        message_desc = self._ConvertMessageDescriptor(
            message_type, file_proto.package, file_descriptor, scope,
            file_proto.syntax)
        file_descriptor.message_types_by_name[message_desc.name] = (
            message_desc)

      for enum_type in file_proto.enum_type:
        file_descriptor.enum_types_by_name[enum_type.name] = (
            self._ConvertEnumDescriptor(enum_type, file_proto.package,
                                        file_descriptor, None, scope, True))

      for index, extension_proto in enumerate(file_proto.extension):
        extension_desc = self._MakeFieldDescriptor(
            extension_proto, file_proto.package, index, file_descriptor,
            is_extension=True)
        extension_desc.containing_type = self._GetTypeFromScope(
            file_descriptor.package, extension_proto.extendee, scope)
        self._SetFieldType(extension_proto, extension_desc,
                           file_descriptor.package, scope)
        file_descriptor.extensions_by_name[extension_desc.name] = (
            extension_desc)

      for desc_proto in file_proto.message_type:
        self._SetAllFieldTypes(file_proto.package, desc_proto, scope)

      if file_proto.package:
        desc_proto_prefix = _PrefixWithDot(file_proto.package)
      else:
        desc_proto_prefix = ''

      for desc_proto in file_proto.message_type:
        desc = self._GetTypeFromScope(
            desc_proto_prefix, desc_proto.name, scope)
        file_descriptor.message_types_by_name[desc_proto.name] = desc

      for index, service_proto in enumerate(file_proto.service):
        file_descriptor.services_by_name[service_proto.name] = (
            self._MakeServiceDescriptor(service_proto, index, scope,
                                        file_proto.package, file_descriptor))

      self._file_descriptors[file_proto.name] = file_descriptor

    # Add extensions to the pool
    def AddExtensionForNested(message_type):
      for nested in message_type.nested_types:
        AddExtensionForNested(nested)
      for extension in message_type.extensions:
        self._AddExtensionDescriptor(extension)

    file_desc = self._file_descriptors[file_proto.name]
    for extension in file_desc.extensions_by_name.values():
      self._AddExtensionDescriptor(extension)
    for message_type in file_desc.message_types_by_name.values():
      AddExtensionForNested(message_type)

    return file_desc

  def _ConvertMessageDescriptor(self, desc_proto, package=None, file_desc=None,
                                scope=None, syntax=None):
    """Adds the proto to the pool in the specified package.

    Args:
      desc_proto: The descriptor_pb2.DescriptorProto protobuf message.
      package: The package the proto should be located in.
      file_desc: The file containing this message.
      scope: Dict mapping short and full symbols to message and enum types.
      syntax: string indicating syntax of the file ("proto2" or "proto3")

    Returns:
      The added descriptor.
    """

    if package:
      desc_name = '.'.join((package, desc_proto.name))
    else:
      desc_name = desc_proto.name

    if file_desc is None:
      file_name = None
    else:
      file_name = file_desc.name

    if scope is None:
      scope = {}

    nested = [
        self._ConvertMessageDescriptor(
            nested, desc_name, file_desc, scope, syntax)
        for nested in desc_proto.nested_type]
    enums = [
        self._ConvertEnumDescriptor(enum, desc_name, file_desc, None,
                                    scope, False)
        for enum in desc_proto.enum_type]
    fields = [self._MakeFieldDescriptor(field, desc_name, index, file_desc)
              for index, field in enumerate(desc_proto.field)]
    extensions = [
        self._MakeFieldDescriptor(extension, desc_name, index, file_desc,
                                  is_extension=True)
        for index, extension in enumerate(desc_proto.extension)]
    oneofs = [
        # pylint: disable=g-complex-comprehension
        descriptor.OneofDescriptor(
            desc.name,
            '.'.join((desc_name, desc.name)),
            index,
            None,
            [],
            _OptionsOrNone(desc),
            # pylint: disable=protected-access
            create_key=descriptor._internal_create_key)
        for index, desc in enumerate(desc_proto.oneof_decl)
    ]
    extension_ranges = [(r.start, r.end) for r in desc_proto.extension_range]
    if extension_ranges:
      is_extendable = True
    else:
      is_extendable = False
    desc = descriptor.Descriptor(
        name=desc_proto.name,
        full_name=desc_name,
        filename=file_name,
        containing_type=None,
        fields=fields,
        oneofs=oneofs,
        nested_types=nested,
        enum_types=enums,
        extensions=extensions,
        options=_OptionsOrNone(desc_proto),
        is_extendable=is_extendable,
        extension_ranges=extension_ranges,
        file=file_desc,
        serialized_start=None,
        serialized_end=None,
        syntax=syntax,
        is_map_entry=desc_proto.options.map_entry,
        # pylint: disable=protected-access
        create_key=descriptor._internal_create_key)
    for nested in desc.nested_types:
      nested.containing_type = desc
    for enum in desc.enum_types:
      enum.containing_type = desc
    for field_index, field_desc in enumerate(desc_proto.field):
      if field_desc.HasField('oneof_index'):
        oneof_index = field_desc.oneof_index
        oneofs[oneof_index].fields.append(fields[field_index])
        fields[field_index].containing_oneof = oneofs[oneof_index]

    scope[_PrefixWithDot(desc_name)] = desc
    self._CheckConflictRegister(desc, desc.full_name, desc.file.name)
    self._descriptors[desc_name] = desc
    return desc

  def _ConvertEnumDescriptor(self, enum_proto, package=None, file_desc=None,
                             containing_type=None, scope=None, top_level=False):
    """Make a protobuf EnumDescriptor given an EnumDescriptorProto protobuf.

    Args:
      enum_proto: The descriptor_pb2.EnumDescriptorProto protobuf message.
      package: Optional package name for the new message EnumDescriptor.
      file_desc: The file containing the enum descriptor.
      containing_type: The type containing this enum.
      scope: Scope containing available types.
      top_level: If True, the enum is a top level symbol. If False, the enum
          is defined inside a message.

    Returns:
      The added descriptor
    """

    if package:
      enum_name = '.'.join((package, enum_proto.name))
    else:
      enum_name = enum_proto.name

    if file_desc is None:
      file_name = None
    else:
      file_name = file_desc.name

    values = [self._MakeEnumValueDescriptor(value, index)
              for index, value in enumerate(enum_proto.value)]
    desc = descriptor.EnumDescriptor(name=enum_proto.name,
                                     full_name=enum_name,
                                     filename=file_name,
                                     file=file_desc,
                                     values=values,
                                     containing_type=containing_type,
                                     options=_OptionsOrNone(enum_proto),
                                     # pylint: disable=protected-access
                                     create_key=descriptor._internal_create_key)
    scope['.%s' % enum_name] = desc
    self._CheckConflictRegister(desc, desc.full_name, desc.file.name)
    self._enum_descriptors[enum_name] = desc

    # Add top level enum values.
    if top_level:
      for value in values:
        full_name = _NormalizeFullyQualifiedName(
            '.'.join((package, value.name)))
        self._CheckConflictRegister(value, full_name, file_name)
        self._top_enum_values[full_name] = value

    return desc

  def _MakeFieldDescriptor(self, field_proto, message_name, index,
                           file_desc, is_extension=False):
    """Creates a field descriptor from a FieldDescriptorProto.

    For message and enum type fields, this method will do a look up
    in the pool for the appropriate descriptor for that type. If it
    is unavailable, it will fall back to the _source function to
    create it. If this type is still unavailable, construction will
    fail.

    Args:
      field_proto: The proto describing the field.
      message_name: The name of the containing message.
      index: Index of the field
      file_desc: The file containing the field descriptor.
      is_extension: Indication that this field is for an extension.

    Returns:
      An initialized FieldDescriptor object
    """

    if message_name:
      full_name = '.'.join((message_name, field_proto.name))
    else:
      full_name = field_proto.name

    if field_proto.json_name:
      json_name = field_proto.json_name
    else:
      json_name = None

    return descriptor.FieldDescriptor(
        name=field_proto.name,
        full_name=full_name,
        index=index,
        number=field_proto.number,
        type=field_proto.type,
        cpp_type=None,
        message_type=None,
        enum_type=None,
        containing_type=None,
        label=field_proto.label,
        has_default_value=False,
        default_value=None,
        is_extension=is_extension,
        extension_scope=None,
        options=_OptionsOrNone(field_proto),
        json_name=json_name,
        file=file_desc,
        # pylint: disable=protected-access
        create_key=descriptor._internal_create_key)

  def _SetAllFieldTypes(self, package, desc_proto, scope):
    """Sets all the descriptor's fields's types.

    This method also sets the containing types on any extensions.

    Args:
      package: The current package of desc_proto.
      desc_proto: The message descriptor to update.
      scope: Enclosing scope of available types.
    """

    package = _PrefixWithDot(package)

    main_desc = self._GetTypeFromScope(package, desc_proto.name, scope)

    if package == '.':
      nested_package = _PrefixWithDot(desc_proto.name)
    else:
      nested_package = '.'.join([package, desc_proto.name])

    for field_proto, field_desc in zip(desc_proto.field, main_desc.fields):
      self._SetFieldType(field_proto, field_desc, nested_package, scope)

    for extension_proto, extension_desc in (
        zip(desc_proto.extension, main_desc.extensions)):
      extension_desc.containing_type = self._GetTypeFromScope(
          nested_package, extension_proto.extendee, scope)
      self._SetFieldType(extension_proto, extension_desc, nested_package, scope)

    for nested_type in desc_proto.nested_type:
      self._SetAllFieldTypes(nested_package, nested_type, scope)

  def _SetFieldType(self, field_proto, field_desc, package, scope):
    """Sets the field's type, cpp_type, message_type and enum_type.

    Args:
      field_proto: Data about the field in proto format.
      field_desc: The descriptor to modify.
      package: The package the field's container is in.
      scope: Enclosing scope of available types.
    """
    if field_proto.type_name:
      desc = self._GetTypeFromScope(package, field_proto.type_name, scope)
    else:
      desc = None

    if not field_proto.HasField('type'):
      if isinstance(desc, descriptor.Descriptor):
        field_proto.type = descriptor.FieldDescriptor.TYPE_MESSAGE
      else:
        field_proto.type = descriptor.FieldDescriptor.TYPE_ENUM

    field_desc.cpp_type = descriptor.FieldDescriptor.ProtoTypeToCppProtoType(
        field_proto.type)

    if (field_proto.type == descriptor.FieldDescriptor.TYPE_MESSAGE
        or field_proto.type == descriptor.FieldDescriptor.TYPE_GROUP):
      field_desc.message_type = desc

    if field_proto.type == descriptor.FieldDescriptor.TYPE_ENUM:
      field_desc.enum_type = desc

    if field_proto.label == descriptor.FieldDescriptor.LABEL_REPEATED:
      field_desc.has_default_value = False
      field_desc.default_value = []
    elif field_proto.HasField('default_value'):
      field_desc.has_default_value = True
      if (field_proto.type == descriptor.FieldDescriptor.TYPE_DOUBLE or
          field_proto.type == descriptor.FieldDescriptor.TYPE_FLOAT):
        field_desc.default_value = float(field_proto.default_value)
      elif field_proto.type == descriptor.FieldDescriptor.TYPE_STRING:
        field_desc.default_value = field_proto.default_value
      elif field_proto.type == descriptor.FieldDescriptor.TYPE_BOOL:
        field_desc.default_value = field_proto.default_value.lower() == 'true'
      elif field_proto.type == descriptor.FieldDescriptor.TYPE_ENUM:
        field_desc.default_value = field_desc.enum_type.values_by_name[
            field_proto.default_value].number
      elif field_proto.type == descriptor.FieldDescriptor.TYPE_BYTES:
        field_desc.default_value = text_encoding.CUnescape(
            field_proto.default_value)
      elif field_proto.type == descriptor.FieldDescriptor.TYPE_MESSAGE:
        field_desc.default_value = None
      else:
        # All other types are of the "int" type.
        field_desc.default_value = int(field_proto.default_value)
    else:
      field_desc.has_default_value = False
      if (field_proto.type == descriptor.FieldDescriptor.TYPE_DOUBLE or
          field_proto.type == descriptor.FieldDescriptor.TYPE_FLOAT):
        field_desc.default_value = 0.0
      elif field_proto.type == descriptor.FieldDescriptor.TYPE_STRING:
        field_desc.default_value = u''
      elif field_proto.type == descriptor.FieldDescriptor.TYPE_BOOL:
        field_desc.default_value = False
      elif field_proto.type == descriptor.FieldDescriptor.TYPE_ENUM:
        field_desc.default_value = field_desc.enum_type.values[0].number
      elif field_proto.type == descriptor.FieldDescriptor.TYPE_BYTES:
        field_desc.default_value = b''
      elif field_proto.type == descriptor.FieldDescriptor.TYPE_MESSAGE:
        field_desc.default_value = None
      elif field_proto.type == descriptor.FieldDescriptor.TYPE_GROUP:
        field_desc.default_value = None
      else:
        # All other types are of the "int" type.
        field_desc.default_value = 0

    field_desc.type = field_proto.type

  def _MakeEnumValueDescriptor(self, value_proto, index):
    """Creates a enum value descriptor object from a enum value proto.

    Args:
      value_proto: The proto describing the enum value.
      index: The index of the enum value.

    Returns:
      An initialized EnumValueDescriptor object.
    """

    return descriptor.EnumValueDescriptor(
        name=value_proto.name,
        index=index,
        number=value_proto.number,
        options=_OptionsOrNone(value_proto),
        type=None,
        # pylint: disable=protected-access
        create_key=descriptor._internal_create_key)

  def _MakeServiceDescriptor(self, service_proto, service_index, scope,
                             package, file_desc):
    """Make a protobuf ServiceDescriptor given a ServiceDescriptorProto.

    Args:
      service_proto: The descriptor_pb2.ServiceDescriptorProto protobuf message.
      service_index: The index of the service in the File.
      scope: Dict mapping short and full symbols to message and enum types.
      package: Optional package name for the new message EnumDescriptor.
      file_desc: The file containing the service descriptor.

    Returns:
      The added descriptor.
    """

    if package:
      service_name = '.'.join((package, service_proto.name))
    else:
      service_name = service_proto.name

    methods = [self._MakeMethodDescriptor(method_proto, service_name, package,
                                          scope, index)
               for index, method_proto in enumerate(service_proto.method)]
    desc = descriptor.ServiceDescriptor(
        name=service_proto.name,
        full_name=service_name,
        index=service_index,
        methods=methods,
        options=_OptionsOrNone(service_proto),
        file=file_desc,
        # pylint: disable=protected-access
        create_key=descriptor._internal_create_key)
    self._CheckConflictRegister(desc, desc.full_name, desc.file.name)
    self._service_descriptors[service_name] = desc
    return desc

  def _MakeMethodDescriptor(self, method_proto, service_name, package, scope,
                            index):
    """Creates a method descriptor from a MethodDescriptorProto.

    Args:
      method_proto: The proto describing the method.
      service_name: The name of the containing service.
      package: Optional package name to look up for types.
      scope: Scope containing available types.
      index: Index of the method in the service.

    Returns:
      An initialized MethodDescriptor object.
    """
    full_name = '.'.join((service_name, method_proto.name))
    input_type = self._GetTypeFromScope(
        package, method_proto.input_type, scope)
    output_type = self._GetTypeFromScope(
        package, method_proto.output_type, scope)
    return descriptor.MethodDescriptor(
        name=method_proto.name,
        full_name=full_name,
        index=index,
        containing_service=None,
        input_type=input_type,
        output_type=output_type,
        client_streaming=method_proto.client_streaming,
        server_streaming=method_proto.server_streaming,
        options=_OptionsOrNone(method_proto),
        # pylint: disable=protected-access
        create_key=descriptor._internal_create_key)

  def _ExtractSymbols(self, descriptors):
    """Pulls out all the symbols from descriptor protos.

    Args:
      descriptors: The messages to extract descriptors from.
    Yields:
      A two element tuple of the type name and descriptor object.
    """

    for desc in descriptors:
      yield (_PrefixWithDot(desc.full_name), desc)
      for symbol in self._ExtractSymbols(desc.nested_types):
        yield symbol
      for enum in desc.enum_types:
        yield (_PrefixWithDot(enum.full_name), enum)

  def _GetDeps(self, dependencies, visited=None):
    """Recursively finds dependencies for file protos.

    Args:
      dependencies: The names of the files being depended on.
      visited: The names of files already found.

    Yields:
      Each direct and indirect dependency.
    """

    visited = visited or set()
    for dependency in dependencies:
      if dependency not in visited:
        visited.add(dependency)
        dep_desc = self.FindFileByName(dependency)
        yield dep_desc
        public_files = [d.name for d in dep_desc.public_dependencies]
        yield from self._GetDeps(public_files, visited)

  def _GetTypeFromScope(self, package, type_name, scope):
    """Finds a given type name in the current scope.

    Args:
      package: The package the proto should be located in.
      type_name: The name of the type to be found in the scope.
      scope: Dict mapping short and full symbols to message and enum types.

    Returns:
      The descriptor for the requested type.
    """
    if type_name not in scope:
      components = _PrefixWithDot(package).split('.')
      while components:
        possible_match = '.'.join(components + [type_name])
        if possible_match in scope:
          type_name = possible_match
          break
        else:
          components.pop(-1)
    return scope[type_name]


def _PrefixWithDot(name):
  return name if name.startswith('.') else '.%s' % name


if _USE_C_DESCRIPTORS:
  # TODO: This pool could be constructed from Python code, when we
  # support a flag like 'use_cpp_generated_pool=True'.
  # pylint: disable=protected-access
  _DEFAULT = descriptor._message.default_pool
else:
  _DEFAULT = DescriptorPool()


def Default():
  return _DEFAULT

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\interpolatablePlot.py ===
from .interpolatableHelpers import *
from fontTools.ttLib import TTFont
from fontTools.ttLib.ttGlyphSet import LerpGlyphSet
from fontTools.pens.recordingPen import (
    RecordingPen,
    DecomposingRecordingPen,
    RecordingPointPen,
)
from fontTools.pens.boundsPen import ControlBoundsPen
from fontTools.pens.cairoPen import CairoPen
from fontTools.pens.pointPen import (
    SegmentToPointPen,
    PointToSegmentPen,
    ReverseContourPointPen,
)
from fontTools.varLib.interpolatableHelpers import (
    PerContourOrComponentPen,
    SimpleRecordingPointPen,
)
from itertools import cycle
from functools import wraps
from io import BytesIO
import cairo
import math
import os
import logging

log = logging.getLogger("fontTools.varLib.interpolatable")


class OverridingDict(dict):
    def __init__(self, parent_dict):
        self.parent_dict = parent_dict

    def __missing__(self, key):
        return self.parent_dict[key]


class InterpolatablePlot:
    width = 8.5 * 72
    height = 11 * 72
    pad = 0.1 * 72
    title_font_size = 24
    font_size = 16
    page_number = 1
    head_color = (0.3, 0.3, 0.3)
    label_color = (0.2, 0.2, 0.2)
    border_color = (0.9, 0.9, 0.9)
    border_width = 0.5
    fill_color = (0.8, 0.8, 0.8)
    stroke_color = (0.1, 0.1, 0.1)
    stroke_width = 1
    oncurve_node_color = (0, 0.8, 0, 0.7)
    oncurve_node_diameter = 6
    offcurve_node_color = (0, 0.5, 0, 0.7)
    offcurve_node_diameter = 4
    handle_color = (0, 0.5, 0, 0.7)
    handle_width = 0.5
    corrected_start_point_color = (0, 0.9, 0, 0.7)
    corrected_start_point_size = 7
    wrong_start_point_color = (1, 0, 0, 0.7)
    start_point_color = (0, 0, 1, 0.7)
    start_arrow_length = 9
    kink_point_size = 7
    kink_point_color = (1, 0, 1, 0.7)
    kink_circle_size = 15
    kink_circle_stroke_width = 1
    kink_circle_color = (1, 0, 1, 0.7)
    contour_colors = ((1, 0, 0), (0, 0, 1), (0, 1, 0), (1, 1, 0), (1, 0, 1), (0, 1, 1))
    contour_alpha = 0.5
    weight_issue_contour_color = (0, 0, 0, 0.4)
    no_issues_label = "Your font's good! Have a cupcake..."
    no_issues_label_color = (0, 0.5, 0)
    cupcake_color = (0.3, 0, 0.3)
    cupcake = r"""
                          ,@.
                        ,@.@@,.
                  ,@@,.@@@.  @.@@@,.
                ,@@. @@@.     @@. @@,.
        ,@@@.@,.@.              @.  @@@@,.@.@@,.
   ,@@.@.     @@.@@.            @,.    .@' @'  @@,
 ,@@. @.          .@@.@@@.  @@'                  @,
,@.  @@.                                          @,
@.     @,@@,.     ,                             .@@,
@,.       .@,@@,.         .@@,.  ,       .@@,  @, @,
@.                             .@. @ @@,.    ,      @
 @,.@@.     @,.      @@,.      @.           @,.    @'
  @@||@,.  @'@,.       @@,.  @@ @,.        @'@@,  @'
     \\@@@@'  @,.      @'@@@@'   @@,.   @@@' //@@@'
      |||||||| @@,.  @@' |||||||  |@@@|@||  ||
       \\\\\\\  ||@@@||  |||||||  |||||||  //
        |||||||  ||||||  ||||||   ||||||  ||
         \\\\\\  ||||||  ||||||  ||||||  //
          ||||||  |||||  |||||   |||||  ||
           \\\\\  |||||  |||||  |||||  //
            |||||  ||||  |||||  ||||  ||
             \\\\  ||||  ||||  ||||  //
              ||||||||||||||||||||||||
"""
    emoticon_color = (0, 0.3, 0.3)
    shrug = r"""\_(")_/"""
    underweight = r"""
 o
/|\
/ \
"""
    overweight = r"""
 o
/O\
/ \
"""
    yay = r""" \o/ """

    def __init__(self, out, glyphsets, names=None, **kwargs):
        self.out = out
        self.glyphsets = glyphsets
        self.names = names or [repr(g) for g in glyphsets]
        self.toc = {}

        for k, v in kwargs.items():
            if not hasattr(self, k):
                raise TypeError("Unknown keyword argument: %s" % k)
            setattr(self, k, v)

        self.panel_width = self.width / 2 - self.pad * 3
        self.panel_height = (
            self.height / 2 - self.pad * 6 - self.font_size * 2 - self.title_font_size
        )

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    def show_page(self):
        self.page_number += 1

    def add_title_page(
        self, files, *, show_tolerance=True, tolerance=None, kinkiness=None
    ):
        pad = self.pad
        width = self.width - 3 * self.pad
        height = self.height - 2 * self.pad
        x = y = pad

        self.draw_label(
            "Problem report for:",
            x=x,
            y=y,
            bold=True,
            width=width,
            font_size=self.title_font_size,
        )
        y += self.title_font_size

        import hashlib

        for file in files:
            base_file = os.path.basename(file)
            y += self.font_size + self.pad
            self.draw_label(base_file, x=x, y=y, bold=True, width=width)
            y += self.font_size + self.pad

            try:
                h = hashlib.sha1(open(file, "rb").read()).hexdigest()
                self.draw_label("sha1: %s" % h, x=x + pad, y=y, width=width)
                y += self.font_size
            except IsADirectoryError:
                pass

            if file.endswith(".ttf"):
                ttFont = TTFont(file)
                name = ttFont["name"] if "name" in ttFont else None
                if name:
                    for what, nameIDs in (
                        ("Family name", (21, 16, 1)),
                        ("Version", (5,)),
                    ):
                        n = name.getFirstDebugName(nameIDs)
                        if n is None:
                            continue
                        self.draw_label(
                            "%s: %s" % (what, n), x=x + pad, y=y, width=width
                        )
                        y += self.font_size + self.pad
            elif file.endswith((".glyphs", ".glyphspackage")):
                from glyphsLib import GSFont

                f = GSFont(file)
                for what, field in (
                    ("Family name", "familyName"),
                    ("VersionMajor", "versionMajor"),
                    ("VersionMinor", "_versionMinor"),
                ):
                    self.draw_label(
                        "%s: %s" % (what, getattr(f, field)),
                        x=x + pad,
                        y=y,
                        width=width,
                    )
                    y += self.font_size + self.pad

        self.draw_legend(
            show_tolerance=show_tolerance, tolerance=tolerance, kinkiness=kinkiness
        )
        self.show_page()

    def draw_legend(self, *, show_tolerance=True, tolerance=None, kinkiness=None):
        cr = cairo.Context(self.surface)

        x = self.pad
        y = self.height - self.pad - self.font_size * 2
        width = self.width - 2 * self.pad

        xx = x + self.pad * 2
        xxx = x + self.pad * 4

        if show_tolerance:
            self.draw_label(
                "Tolerance: badness; closer to zero the worse", x=xxx, y=y, width=width
            )
            y -= self.pad + self.font_size

        self.draw_label("Underweight contours", x=xxx, y=y, width=width)
        cr.rectangle(xx - self.pad * 0.7, y, 1.5 * self.pad, self.font_size)
        cr.set_source_rgb(*self.fill_color)
        cr.fill_preserve()
        if self.stroke_color:
            cr.set_source_rgb(*self.stroke_color)
            cr.set_line_width(self.stroke_width)
            cr.stroke_preserve()
        cr.set_source_rgba(*self.weight_issue_contour_color)
        cr.fill()
        y -= self.pad + self.font_size

        self.draw_label(
            "Colored contours: contours with the wrong order", x=xxx, y=y, width=width
        )
        cr.rectangle(xx - self.pad * 0.7, y, 1.5 * self.pad, self.font_size)
        if self.fill_color:
            cr.set_source_rgb(*self.fill_color)
            cr.fill_preserve()
        if self.stroke_color:
            cr.set_source_rgb(*self.stroke_color)
            cr.set_line_width(self.stroke_width)
            cr.stroke_preserve()
        cr.set_source_rgba(*self.contour_colors[0], self.contour_alpha)
        cr.fill()
        y -= self.pad + self.font_size

        self.draw_label("Kink artifact", x=xxx, y=y, width=width)
        self.draw_circle(
            cr,
            x=xx,
            y=y + self.font_size * 0.5,
            diameter=self.kink_circle_size,
            stroke_width=self.kink_circle_stroke_width,
            color=self.kink_circle_color,
        )
        y -= self.pad + self.font_size

        self.draw_label("Point causing kink in the contour", x=xxx, y=y, width=width)
        self.draw_dot(
            cr,
            x=xx,
            y=y + self.font_size * 0.5,
            diameter=self.kink_point_size,
            color=self.kink_point_color,
        )
        y -= self.pad + self.font_size

        self.draw_label("Suggested new contour start point", x=xxx, y=y, width=width)
        self.draw_dot(
            cr,
            x=xx,
            y=y + self.font_size * 0.5,
            diameter=self.corrected_start_point_size,
            color=self.corrected_start_point_color,
        )
        y -= self.pad + self.font_size

        self.draw_label(
            "Contour start point in contours with wrong direction",
            x=xxx,
            y=y,
            width=width,
        )
        self.draw_arrow(
            cr,
            x=xx - self.start_arrow_length * 0.3,
            y=y + self.font_size * 0.5,
            color=self.wrong_start_point_color,
        )
        y -= self.pad + self.font_size

        self.draw_label(
            "Contour start point when the first two points overlap",
            x=xxx,
            y=y,
            width=width,
        )
        self.draw_dot(
            cr,
            x=xx,
            y=y + self.font_size * 0.5,
            diameter=self.corrected_start_point_size,
            color=self.start_point_color,
        )
        y -= self.pad + self.font_size

        self.draw_label("Contour start point and direction", x=xxx, y=y, width=width)
        self.draw_arrow(
            cr,
            x=xx - self.start_arrow_length * 0.3,
            y=y + self.font_size * 0.5,
            color=self.start_point_color,
        )
        y -= self.pad + self.font_size

        self.draw_label("Legend:", x=x, y=y, width=width, bold=True)
        y -= self.pad + self.font_size

        if kinkiness is not None:
            self.draw_label(
                "Kink-reporting aggressiveness: %g" % kinkiness,
                x=xxx,
                y=y,
                width=width,
            )
            y -= self.pad + self.font_size

        if tolerance is not None:
            self.draw_label(
                "Error tolerance: %g" % tolerance,
                x=xxx,
                y=y,
                width=width,
            )
            y -= self.pad + self.font_size

        self.draw_label("Parameters:", x=x, y=y, width=width, bold=True)
        y -= self.pad + self.font_size

    def add_summary(self, problems):
        pad = self.pad
        width = self.width - 3 * self.pad
        height = self.height - 2 * self.pad
        x = y = pad

        self.draw_label(
            "Summary of problems",
            x=x,
            y=y,
            bold=True,
            width=width,
            font_size=self.title_font_size,
        )
        y += self.title_font_size

        glyphs_per_problem = defaultdict(set)
        for glyphname, problems in sorted(problems.items()):
            for problem in problems:
                glyphs_per_problem[problem["type"]].add(glyphname)

        if "nothing" in glyphs_per_problem:
            del glyphs_per_problem["nothing"]

        for problem_type in sorted(
            glyphs_per_problem, key=lambda x: InterpolatableProblem.severity[x]
        ):
            y += self.font_size
            self.draw_label(
                "%s: %d" % (problem_type, len(glyphs_per_problem[problem_type])),
                x=x,
                y=y,
                width=width,
                bold=True,
            )
            y += self.font_size

            for glyphname in sorted(glyphs_per_problem[problem_type]):
                if y + self.font_size > height:
                    self.show_page()
                    y = self.font_size + pad
                self.draw_label(glyphname, x=x + 2 * pad, y=y, width=width - 2 * pad)
                y += self.font_size

        self.show_page()

    def _add_listing(self, title, items):
        pad = self.pad
        width = self.width - 2 * self.pad
        height = self.height - 2 * self.pad
        x = y = pad

        self.draw_label(
            title, x=x, y=y, bold=True, width=width, font_size=self.title_font_size
        )
        y += self.title_font_size + self.pad

        last_glyphname = None
        for page_no, (glyphname, problems) in items:
            if glyphname == last_glyphname:
                continue
            last_glyphname = glyphname
            if y + self.font_size > height:
                self.show_page()
                y = self.font_size + pad
            self.draw_label(glyphname, x=x + 5 * pad, y=y, width=width - 2 * pad)
            self.draw_label(str(page_no), x=x, y=y, width=4 * pad, align=1)
            y += self.font_size

        self.show_page()

    def add_table_of_contents(self):
        self._add_listing("Table of contents", sorted(self.toc.items()))

    def add_index(self):
        self._add_listing("Index", sorted(self.toc.items(), key=lambda x: x[1][0]))

    def add_problems(self, problems, *, show_tolerance=True, show_page_number=True):
        for glyph, glyph_problems in problems.items():
            last_masters = None
            current_glyph_problems = []
            for p in glyph_problems:
                masters = (
                    p["master_idx"]
                    if "master_idx" in p
                    else (p["master_1_idx"], p["master_2_idx"])
                )
                if masters == last_masters:
                    current_glyph_problems.append(p)
                    continue
                # Flush
                if current_glyph_problems:
                    self.add_problem(
                        glyph,
                        current_glyph_problems,
                        show_tolerance=show_tolerance,
                        show_page_number=show_page_number,
                    )
                    self.show_page()
                    current_glyph_problems = []
                last_masters = masters
                current_glyph_problems.append(p)
            if current_glyph_problems:
                self.add_problem(
                    glyph,
                    current_glyph_problems,
                    show_tolerance=show_tolerance,
                    show_page_number=show_page_number,
                )
                self.show_page()

    def add_problem(
        self, glyphname, problems, *, show_tolerance=True, show_page_number=True
    ):
        if type(problems) not in (list, tuple):
            problems = [problems]

        self.toc[self.page_number] = (glyphname, problems)

        problem_type = problems[0]["type"]
        problem_types = set(problem["type"] for problem in problems)
        if not all(pt == problem_type for pt in problem_types):
            problem_type = ", ".join(sorted({problem["type"] for problem in problems}))

        log.info("Drawing %s: %s", glyphname, problem_type)

        master_keys = (
            ("master_idx",)
            if "master_idx" in problems[0]
            else ("master_1_idx", "master_2_idx")
        )
        master_indices = [problems[0][k] for k in master_keys]

        if problem_type == InterpolatableProblem.MISSING:
            sample_glyph = next(
                i for i, m in enumerate(self.glyphsets) if m[glyphname] is not None
            )
            master_indices.insert(0, sample_glyph)

        x = self.pad
        y = self.pad

        self.draw_label(
            "Glyph name: " + glyphname,
            x=x,
            y=y,
            color=self.head_color,
            align=0,
            bold=True,
            font_size=self.title_font_size,
        )
        tolerance = min(p.get("tolerance", 1) for p in problems)
        if tolerance < 1 and show_tolerance:
            self.draw_label(
                "tolerance: %.2f" % tolerance,
                x=x,
                y=y,
                width=self.width - 2 * self.pad,
                align=1,
                bold=True,
            )
        y += self.title_font_size + self.pad
        self.draw_label(
            "Problems: " + problem_type,
            x=x,
            y=y,
            width=self.width - 2 * self.pad,
            color=self.head_color,
            bold=True,
        )
        y += self.font_size + self.pad * 2

        scales = []
        for which, master_idx in enumerate(master_indices):
            glyphset = self.glyphsets[master_idx]
            name = self.names[master_idx]

            self.draw_label(
                name,
                x=x,
                y=y,
                color=self.label_color,
                width=self.panel_width,
                align=0.5,
            )
            y += self.font_size + self.pad

            if glyphset[glyphname] is not None:
                scales.append(
                    self.draw_glyph(glyphset, glyphname, problems, which, x=x, y=y)
                )
            else:
                self.draw_emoticon(self.shrug, x=x, y=y)
            y += self.panel_height + self.font_size + self.pad

        if any(
            pt
            in (
                InterpolatableProblem.NOTHING,
                InterpolatableProblem.WRONG_START_POINT,
                InterpolatableProblem.CONTOUR_ORDER,
                InterpolatableProblem.KINK,
                InterpolatableProblem.UNDERWEIGHT,
                InterpolatableProblem.OVERWEIGHT,
            )
            for pt in problem_types
        ):
            x = self.pad + self.panel_width + self.pad
            y = self.pad
            y += self.title_font_size + self.pad * 2
            y += self.font_size + self.pad

            glyphset1 = self.glyphsets[master_indices[0]]
            glyphset2 = self.glyphsets[master_indices[1]]

            # Draw the mid-way of the two masters

            self.draw_label(
                "midway interpolation",
                x=x,
                y=y,
                color=self.head_color,
                width=self.panel_width,
                align=0.5,
            )
            y += self.font_size + self.pad

            midway_glyphset = LerpGlyphSet(glyphset1, glyphset2)
            self.draw_glyph(
                midway_glyphset,
                glyphname,
                [{"type": "midway"}]
                + [
                    p
                    for p in problems
                    if p["type"]
                    in (
                        InterpolatableProblem.KINK,
                        InterpolatableProblem.UNDERWEIGHT,
                        InterpolatableProblem.OVERWEIGHT,
                    )
                ],
                None,
                x=x,
                y=y,
                scale=min(scales),
            )

            y += self.panel_height + self.font_size + self.pad

        if any(
            pt
            in (
                InterpolatableProblem.WRONG_START_POINT,
                InterpolatableProblem.CONTOUR_ORDER,
                InterpolatableProblem.KINK,
            )
            for pt in problem_types
        ):
            # Draw the proposed fix

            self.draw_label(
                "proposed fix",
                x=x,
                y=y,
                color=self.head_color,
                width=self.panel_width,
                align=0.5,
            )
            y += self.font_size + self.pad

            overriding1 = OverridingDict(glyphset1)
            overriding2 = OverridingDict(glyphset2)
            perContourPen1 = PerContourOrComponentPen(
                RecordingPen, glyphset=overriding1
            )
            perContourPen2 = PerContourOrComponentPen(
                RecordingPen, glyphset=overriding2
            )
            glyphset1[glyphname].draw(perContourPen1)
            glyphset2[glyphname].draw(perContourPen2)

            for problem in problems:
                if problem["type"] == InterpolatableProblem.CONTOUR_ORDER:
                    fixed_contours = [
                        perContourPen2.value[i] for i in problems[0]["value_2"]
                    ]
                    perContourPen2.value = fixed_contours

            for problem in problems:
                if problem["type"] == InterpolatableProblem.WRONG_START_POINT:
                    # Save the wrong contours
                    wrongContour1 = perContourPen1.value[problem["contour"]]
                    wrongContour2 = perContourPen2.value[problem["contour"]]

                    # Convert the wrong contours to point pens
                    points1 = RecordingPointPen()
                    converter = SegmentToPointPen(points1, False)
                    wrongContour1.replay(converter)
                    points2 = RecordingPointPen()
                    converter = SegmentToPointPen(points2, False)
                    wrongContour2.replay(converter)

                    proposed_start = problem["value_2"]

                    # See if we need reversing; fragile but worth a try
                    if problem["reversed"]:
                        new_points2 = RecordingPointPen()
                        reversedPen = ReverseContourPointPen(new_points2)
                        points2.replay(reversedPen)
                        points2 = new_points2
                        proposed_start = len(points2.value) - 2 - proposed_start

                    # Rotate points2 so that the first point is the same as in points1
                    beginPath = points2.value[:1]
                    endPath = points2.value[-1:]
                    pts = points2.value[1:-1]
                    pts = pts[proposed_start:] + pts[:proposed_start]
                    points2.value = beginPath + pts + endPath

                    # Convert the point pens back to segment pens
                    segment1 = RecordingPen()
                    converter = PointToSegmentPen(segment1, True)
                    points1.replay(converter)
                    segment2 = RecordingPen()
                    converter = PointToSegmentPen(segment2, True)
                    points2.replay(converter)

                    # Replace the wrong contours
                    wrongContour1.value = segment1.value
                    wrongContour2.value = segment2.value
                    perContourPen1.value[problem["contour"]] = wrongContour1
                    perContourPen2.value[problem["contour"]] = wrongContour2

            for problem in problems:
                # If we have a kink, try to fix it.
                if problem["type"] == InterpolatableProblem.KINK:
                    # Save the wrong contours
                    wrongContour1 = perContourPen1.value[problem["contour"]]
                    wrongContour2 = perContourPen2.value[problem["contour"]]

                    # Convert the wrong contours to point pens
                    points1 = RecordingPointPen()
                    converter = SegmentToPointPen(points1, False)
                    wrongContour1.replay(converter)
                    points2 = RecordingPointPen()
                    converter = SegmentToPointPen(points2, False)
                    wrongContour2.replay(converter)

                    i = problem["value"]

                    # Position points to be around the same ratio
                    # beginPath / endPath dance
                    j = i + 1
                    pt0 = points1.value[j][1][0]
                    pt1 = points2.value[j][1][0]
                    j_prev = (i - 1) % (len(points1.value) - 2) + 1
                    pt0_prev = points1.value[j_prev][1][0]
                    pt1_prev = points2.value[j_prev][1][0]
                    j_next = (i + 1) % (len(points1.value) - 2) + 1
                    pt0_next = points1.value[j_next][1][0]
                    pt1_next = points2.value[j_next][1][0]

                    pt0 = complex(*pt0)
                    pt1 = complex(*pt1)
                    pt0_prev = complex(*pt0_prev)
                    pt1_prev = complex(*pt1_prev)
                    pt0_next = complex(*pt0_next)
                    pt1_next = complex(*pt1_next)

                    # Find the ratio of the distance between the points
                    r0 = abs(pt0 - pt0_prev) / abs(pt0_next - pt0_prev)
                    r1 = abs(pt1 - pt1_prev) / abs(pt1_next - pt1_prev)
                    r_mid = (r0 + r1) / 2

                    pt0 = pt0_prev + r_mid * (pt0_next - pt0_prev)
                    pt1 = pt1_prev + r_mid * (pt1_next - pt1_prev)

                    points1.value[j] = (
                        points1.value[j][0],
                        (((pt0.real, pt0.imag),) + points1.value[j][1][1:]),
                        points1.value[j][2],
                    )
                    points2.value[j] = (
                        points2.value[j][0],
                        (((pt1.real, pt1.imag),) + points2.value[j][1][1:]),
                        points2.value[j][2],
                    )

                    # Convert the point pens back to segment pens
                    segment1 = RecordingPen()
                    converter = PointToSegmentPen(segment1, True)
                    points1.replay(converter)
                    segment2 = RecordingPen()
                    converter = PointToSegmentPen(segment2, True)
                    points2.replay(converter)

                    # Replace the wrong contours
                    wrongContour1.value = segment1.value
                    wrongContour2.value = segment2.value

            # Assemble
            fixed1 = RecordingPen()
            fixed2 = RecordingPen()
            for contour in perContourPen1.value:
                fixed1.value.extend(contour.value)
            for contour in perContourPen2.value:
                fixed2.value.extend(contour.value)
            fixed1.draw = fixed1.replay
            fixed2.draw = fixed2.replay

            overriding1[glyphname] = fixed1
            overriding2[glyphname] = fixed2

            try:
                midway_glyphset = LerpGlyphSet(overriding1, overriding2)
                self.draw_glyph(
                    midway_glyphset,
                    glyphname,
                    {"type": "fixed"},
                    None,
                    x=x,
                    y=y,
                    scale=min(scales),
                )
            except ValueError:
                self.draw_emoticon(self.shrug, x=x, y=y)
            y += self.panel_height + self.pad

        else:
            emoticon = self.shrug
            if InterpolatableProblem.UNDERWEIGHT in problem_types:
                emoticon = self.underweight
            elif InterpolatableProblem.OVERWEIGHT in problem_types:
                emoticon = self.overweight
            elif InterpolatableProblem.NOTHING in problem_types:
                emoticon = self.yay
            self.draw_emoticon(emoticon, x=x, y=y)

        if show_page_number:
            self.draw_label(
                str(self.page_number),
                x=0,
                y=self.height - self.font_size - self.pad,
                width=self.width,
                color=self.head_color,
                align=0.5,
            )

    def draw_label(
        self,
        label,
        *,
        x=0,
        y=0,
        color=(0, 0, 0),
        align=0,
        bold=False,
        width=None,
        height=None,
        font_size=None,
    ):
        if width is None:
            width = self.width
        if height is None:
            height = self.height
        if font_size is None:
            font_size = self.font_size
        cr = cairo.Context(self.surface)
        cr.select_font_face(
            "@cairo:",
            cairo.FONT_SLANT_NORMAL,
            cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL,
        )
        cr.set_font_size(font_size)
        font_extents = cr.font_extents()
        font_size = font_size * font_size / font_extents[2]
        cr.set_font_size(font_size)
        font_extents = cr.font_extents()

        cr.set_source_rgb(*color)

        extents = cr.text_extents(label)
        if extents.width > width:
            # Shrink
            font_size *= width / extents.width
            cr.set_font_size(font_size)
            font_extents = cr.font_extents()
            extents = cr.text_extents(label)

        # Center
        label_x = x + (width - extents.width) * align
        label_y = y + font_extents[0]
        cr.move_to(label_x, label_y)
        cr.show_text(label)

    def draw_glyph(self, glyphset, glyphname, problems, which, *, x=0, y=0, scale=None):
        if type(problems) not in (list, tuple):
            problems = [problems]

        midway = any(problem["type"] == "midway" for problem in problems)
        problem_type = problems[0]["type"]
        problem_types = set(problem["type"] for problem in problems)
        if not all(pt == problem_type for pt in problem_types):
            problem_type = "mixed"
        glyph = glyphset[glyphname]

        recording = RecordingPen()
        glyph.draw(recording)
        decomposedRecording = DecomposingRecordingPen(glyphset)
        glyph.draw(decomposedRecording)

        boundsPen = ControlBoundsPen(glyphset)
        decomposedRecording.replay(boundsPen)
        bounds = boundsPen.bounds
        if bounds is None:
            bounds = (0, 0, 0, 0)

        glyph_width = bounds[2] - bounds[0]
        glyph_height = bounds[3] - bounds[1]

        if glyph_width:
            if scale is None:
                scale = self.panel_width / glyph_width
            else:
                scale = min(scale, self.panel_height / glyph_height)
        if glyph_height:
            if scale is None:
                scale = self.panel_height / glyph_height
            else:
                scale = min(scale, self.panel_height / glyph_height)
        if scale is None:
            scale = 1

        cr = cairo.Context(self.surface)
        cr.translate(x, y)
        # Center
        cr.translate(
            (self.panel_width - glyph_width * scale) / 2,
            (self.panel_height - glyph_height * scale) / 2,
        )
        cr.scale(scale, -scale)
        cr.translate(-bounds[0], -bounds[3])

        if self.border_color:
            cr.set_source_rgb(*self.border_color)
            cr.rectangle(bounds[0], bounds[1], glyph_width, glyph_height)
            cr.set_line_width(self.border_width / scale)
            cr.stroke()

        if self.fill_color or self.stroke_color:
            pen = CairoPen(glyphset, cr)
            decomposedRecording.replay(pen)

            if self.fill_color and problem_type != InterpolatableProblem.OPEN_PATH:
                cr.set_source_rgb(*self.fill_color)
                cr.fill_preserve()

            if self.stroke_color:
                cr.set_source_rgb(*self.stroke_color)
                cr.set_line_width(self.stroke_width / scale)
                cr.stroke_preserve()

            cr.new_path()

        if (
            InterpolatableProblem.UNDERWEIGHT in problem_types
            or InterpolatableProblem.OVERWEIGHT in problem_types
        ):
            perContourPen = PerContourOrComponentPen(RecordingPen, glyphset=glyphset)
            recording.replay(perContourPen)
            for problem in problems:
                if problem["type"] in (
                    InterpolatableProblem.UNDERWEIGHT,
                    InterpolatableProblem.OVERWEIGHT,
                ):
                    contour = perContourPen.value[problem["contour"]]
                    contour.replay(CairoPen(glyphset, cr))
                    cr.set_source_rgba(*self.weight_issue_contour_color)
                    cr.fill()

        if any(
            t in problem_types
            for t in {
                InterpolatableProblem.NOTHING,
                InterpolatableProblem.NODE_COUNT,
                InterpolatableProblem.NODE_INCOMPATIBILITY,
            }
        ):
            cr.set_line_cap(cairo.LINE_CAP_ROUND)

            # Oncurve nodes
            for segment, args in decomposedRecording.value:
                if not args:
                    continue
                x, y = args[-1]
                cr.move_to(x, y)
                cr.line_to(x, y)
            cr.set_source_rgba(*self.oncurve_node_color)
            cr.set_line_width(self.oncurve_node_diameter / scale)
            cr.stroke()

            # Offcurve nodes
            for segment, args in decomposedRecording.value:
                if not args:
                    continue
                for x, y in args[:-1]:
                    cr.move_to(x, y)
                    cr.line_to(x, y)
            cr.set_source_rgba(*self.offcurve_node_color)
            cr.set_line_width(self.offcurve_node_diameter / scale)
            cr.stroke()

            # Handles
            for segment, args in decomposedRecording.value:
                if not args:
                    pass
                elif segment in ("moveTo", "lineTo"):
                    cr.move_to(*args[0])
                elif segment == "qCurveTo":
                    for x, y in args:
                        cr.line_to(x, y)
                    cr.new_sub_path()
                    cr.move_to(*args[-1])
                elif segment == "curveTo":
                    cr.line_to(*args[0])
                    cr.new_sub_path()
                    cr.move_to(*args[1])
                    cr.line_to(*args[2])
                    cr.new_sub_path()
                    cr.move_to(*args[-1])
                else:
                    continue

            cr.set_source_rgba(*self.handle_color)
            cr.set_line_width(self.handle_width / scale)
            cr.stroke()

        matching = None
        for problem in problems:
            if problem["type"] == InterpolatableProblem.CONTOUR_ORDER:
                matching = problem["value_2"]
                colors = cycle(self.contour_colors)
                perContourPen = PerContourOrComponentPen(
                    RecordingPen, glyphset=glyphset
                )
                recording.replay(perContourPen)
                for i, contour in enumerate(perContourPen.value):
                    if matching[i] == i:
                        continue
                    color = next(colors)
                    contour.replay(CairoPen(glyphset, cr))
                    cr.set_source_rgba(*color, self.contour_alpha)
                    cr.fill()

        for problem in problems:
            if problem["type"] in (
                InterpolatableProblem.NOTHING,
                InterpolatableProblem.WRONG_START_POINT,
            ):
                idx = problem.get("contour")

                # Draw suggested point
                if idx is not None and which == 1 and "value_2" in problem:
                    perContourPen = PerContourOrComponentPen(
                        RecordingPen, glyphset=glyphset
                    )
                    decomposedRecording.replay(perContourPen)
                    points = SimpleRecordingPointPen()
                    converter = SegmentToPointPen(points, False)
                    perContourPen.value[
                        idx if matching is None else matching[idx]
                    ].replay(converter)
                    targetPoint = points.value[problem["value_2"]][0]
                    cr.save()
                    cr.translate(*targetPoint)
                    cr.scale(1 / scale, 1 / scale)
                    self.draw_dot(
                        cr,
                        diameter=self.corrected_start_point_size,
                        color=self.corrected_start_point_color,
                    )
                    cr.restore()

                # Draw start-point arrow
                if which == 0 or not problem.get("reversed"):
                    color = self.start_point_color
                else:
                    color = self.wrong_start_point_color
                first_pt = None
                i = 0
                cr.save()
                for segment, args in decomposedRecording.value:
                    if segment == "moveTo":
                        first_pt = args[0]
                        continue
                    if first_pt is None:
                        continue
                    if segment == "closePath":
                        second_pt = first_pt
                    else:
                        second_pt = args[0]

                    if idx is None or i == idx:
                        cr.save()
                        first_pt = complex(*first_pt)
                        second_pt = complex(*second_pt)
                        length = abs(second_pt - first_pt)
                        cr.translate(first_pt.real, first_pt.imag)
                        if length:
                            # Draw arrowhead
                            cr.rotate(
                                math.atan2(
                                    second_pt.imag - first_pt.imag,
                                    second_pt.real - first_pt.real,
                                )
                            )
                            cr.scale(1 / scale, 1 / scale)
                            self.draw_arrow(cr, color=color)
                        else:
                            # Draw circle
                            cr.scale(1 / scale, 1 / scale)
                            self.draw_dot(
                                cr,
                                diameter=self.corrected_start_point_size,
                                color=color,
                            )
                        cr.restore()

                        if idx is not None:
                            break

                    first_pt = None
                    i += 1

                cr.restore()

            if problem["type"] == InterpolatableProblem.KINK:
                idx = problem.get("contour")
                perContourPen = PerContourOrComponentPen(
                    RecordingPen, glyphset=glyphset
                )
                decomposedRecording.replay(perContourPen)
                points = SimpleRecordingPointPen()
                converter = SegmentToPointPen(points, False)
                perContourPen.value[idx if matching is None else matching[idx]].replay(
                    converter
                )

                targetPoint = points.value[problem["value"]][0]
                cr.save()
                cr.translate(*targetPoint)
                cr.scale(1 / scale, 1 / scale)
                if midway:
                    self.draw_circle(
                        cr,
                        diameter=self.kink_circle_size,
                        stroke_width=self.kink_circle_stroke_width,
                        color=self.kink_circle_color,
                    )
                else:
                    self.draw_dot(
                        cr,
                        diameter=self.kink_point_size,
                        color=self.kink_point_color,
                    )
                cr.restore()

        return scale

    def draw_dot(self, cr, *, x=0, y=0, color=(0, 0, 0), diameter=10):
        cr.save()
        cr.set_line_width(diameter)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(x, y)
        cr.line_to(x, y)
        if len(color) == 3:
            color = color + (1,)
        cr.set_source_rgba(*color)
        cr.stroke()
        cr.restore()

    def draw_circle(
        self, cr, *, x=0, y=0, color=(0, 0, 0), diameter=10, stroke_width=1
    ):
        cr.save()
        cr.set_line_width(stroke_width)
        cr.set_line_cap(cairo.LINE_CAP_SQUARE)
        cr.arc(x, y, diameter / 2, 0, 2 * math.pi)
        if len(color) == 3:
            color = color + (1,)
        cr.set_source_rgba(*color)
        cr.stroke()
        cr.restore()

    def draw_arrow(self, cr, *, x=0, y=0, color=(0, 0, 0)):
        cr.save()
        if len(color) == 3:
            color = color + (1,)
        cr.set_source_rgba(*color)
        cr.translate(self.start_arrow_length + x, y)
        cr.move_to(0, 0)
        cr.line_to(
            -self.start_arrow_length,
            -self.start_arrow_length * 0.4,
        )
        cr.line_to(
            -self.start_arrow_length,
            self.start_arrow_length * 0.4,
        )
        cr.close_path()
        cr.fill()
        cr.restore()

    def draw_text(self, text, *, x=0, y=0, color=(0, 0, 0), width=None, height=None):
        if width is None:
            width = self.width
        if height is None:
            height = self.height

        text = text.splitlines()
        cr = cairo.Context(self.surface)
        cr.set_source_rgb(*color)
        cr.set_font_size(self.font_size)
        cr.select_font_face(
            "@cairo:monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL
        )
        text_width = 0
        text_height = 0
        font_extents = cr.font_extents()
        font_font_size = font_extents[2]
        font_ascent = font_extents[0]
        for line in text:
            extents = cr.text_extents(line)
            text_width = max(text_width, extents.x_advance)
            text_height += font_font_size
        if not text_width:
            return
        cr.translate(x, y)
        scale = min(width / text_width, height / text_height)
        # center
        cr.translate(
            (width - text_width * scale) / 2, (height - text_height * scale) / 2
        )
        cr.scale(scale, scale)

        cr.translate(0, font_ascent)
        for line in text:
            cr.move_to(0, 0)
            cr.show_text(line)
            cr.translate(0, font_font_size)

    def draw_cupcake(self):
        self.draw_label(
            self.no_issues_label,
            x=self.pad,
            y=self.pad,
            color=self.no_issues_label_color,
            width=self.width - 2 * self.pad,
            align=0.5,
            bold=True,
            font_size=self.title_font_size,
        )

        self.draw_text(
            self.cupcake,
            x=self.pad,
            y=self.pad + self.font_size,
            width=self.width - 2 * self.pad,
            height=self.height - 2 * self.pad - self.font_size,
            color=self.cupcake_color,
        )

    def draw_emoticon(self, emoticon, x=0, y=0):
        self.draw_text(
            emoticon,
            x=x,
            y=y,
            color=self.emoticon_color,
            width=self.panel_width,
            height=self.panel_height,
        )


class InterpolatablePostscriptLike(InterpolatablePlot):
    def __exit__(self, type, value, traceback):
        self.surface.finish()

    def show_page(self):
        super().show_page()
        self.surface.show_page()


class InterpolatablePS(InterpolatablePostscriptLike):
    def __enter__(self):
        self.surface = cairo.PSSurface(self.out, self.width, self.height)
        return self


class InterpolatablePDF(InterpolatablePostscriptLike):
    def __enter__(self):
        self.surface = cairo.PDFSurface(self.out, self.width, self.height)
        self.surface.set_metadata(
            cairo.PDF_METADATA_CREATOR, "fonttools varLib.interpolatable"
        )
        self.surface.set_metadata(cairo.PDF_METADATA_CREATE_DATE, "")
        return self


class InterpolatableSVG(InterpolatablePlot):
    def __enter__(self):
        self.sink = BytesIO()
        self.surface = cairo.SVGSurface(self.sink, self.width, self.height)
        return self

    def __exit__(self, type, value, traceback):
        if self.surface is not None:
            self.show_page()

    def show_page(self):
        super().show_page()
        self.surface.finish()
        self.out.append(self.sink.getvalue())
        self.sink = BytesIO()
        self.surface = cairo.SVGSurface(self.sink, self.width, self.height)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\auth\user_api_key_auth.py ===
"""
This file handles authentication for the LiteLLM Proxy.

it checks if the user passed a valid API Key to the LiteLLM Proxy

Returns a UserAPIKeyAuth object if the API key is valid

"""

import asyncio
import secrets
from datetime import datetime, timezone
from typing import List, Optional, Tuple, cast

import fastapi
from fastapi import HTTPException, Request, WebSocket, status
from fastapi.security.api_key import APIKeyHeader

import litellm
from litellm._logging import verbose_logger, verbose_proxy_logger
from litellm._service_logger import ServiceLogging
from litellm.caching import DualCache
from litellm.litellm_core_utils.dd_tracing import tracer
from litellm.proxy._types import *
from litellm.proxy.auth.auth_checks import (
    ExperimentalUIJWTToken,
    _cache_key_object,
    _get_user_role,
    _is_user_proxy_admin,
    _virtual_key_max_budget_check,
    _virtual_key_soft_budget_check,
    can_key_call_model,
    common_checks,
    get_end_user_object,
    get_key_object,
    get_team_object,
    get_user_object,
    is_valid_fallback_model,
)
from litellm.proxy.auth.auth_exception_handler import UserAPIKeyAuthExceptionHandler
from litellm.proxy.auth.auth_utils import (
    abbreviate_api_key,
    get_end_user_id_from_request_body,
    get_model_from_request,
    get_request_route,
    is_pass_through_provider_route,
    pre_db_read_auth_checks,
    route_in_additonal_public_routes,
    should_run_auth_on_pass_through_provider_route,
)
from litellm.proxy.auth.handle_jwt import JWTAuthManager, JWTHandler
from litellm.proxy.auth.oauth2_check import check_oauth2_token
from litellm.proxy.auth.oauth2_proxy_hook import handle_oauth2_proxy_request
from litellm.proxy.common_utils.http_parsing_utils import (
    _read_request_body,
    _safe_get_request_headers,
)
from litellm.proxy.utils import PrismaClient, ProxyLogging
from litellm.secret_managers.main import get_secret_bool
from litellm.types.services import ServiceTypes

try:
    from litellm_enterprise.proxy.auth.user_api_key_auth import (
        enterprise_custom_auth as _enterprise_custom_auth,
    )

    enterprise_custom_auth: Optional[Callable] = _enterprise_custom_auth
except ImportError as e:
    verbose_proxy_logger.debug(f"Error in enterprise custom auth: {e}")
    enterprise_custom_auth = None

user_api_key_service_logger_obj = ServiceLogging()  # used for tracking latency on OTEL

custom_litellm_key_header = APIKeyHeader(
    name=SpecialHeaders.custom_litellm_api_key.value,
    auto_error=False,
    description="Bearer token",
)
api_key_header = APIKeyHeader(
    name=SpecialHeaders.openai_authorization.value,
    auto_error=False,
    description="Bearer token",
)
azure_api_key_header = APIKeyHeader(
    name=SpecialHeaders.azure_authorization.value,
    auto_error=False,
    description="Some older versions of the openai Python package will send an API-Key header with just the API key ",
)
anthropic_api_key_header = APIKeyHeader(
    name=SpecialHeaders.anthropic_authorization.value,
    auto_error=False,
    description="If anthropic client used.",
)
google_ai_studio_api_key_header = APIKeyHeader(
    name=SpecialHeaders.google_ai_studio_authorization.value,
    auto_error=False,
    description="If google ai studio client used.",
)
azure_apim_header = APIKeyHeader(
    name=SpecialHeaders.azure_apim_authorization.value,
    auto_error=False,
    description="The default name of the subscription key header of Azure",
)


def _get_bearer_token_or_received_api_key(api_key: str) -> str:
    if api_key.startswith("Bearer "):  # ensure Bearer token passed in
        api_key = api_key.replace("Bearer ", "")  # extract the token
    elif api_key.startswith("Basic "):
        api_key = api_key.replace("Basic ", "")  # handle langfuse input
    elif api_key.startswith("bearer "):
        api_key = api_key.replace("bearer ", "")

    return api_key


def _get_bearer_token(
    api_key: str,
):
    if api_key.startswith("Bearer "):  # ensure Bearer token passed in
        api_key = api_key.replace("Bearer ", "")  # extract the token
    elif api_key.startswith("Basic "):
        api_key = api_key.replace("Basic ", "")  # handle langfuse input
    elif api_key.startswith("bearer "):
        api_key = api_key.replace("bearer ", "")
    else:
        api_key = ""
    return api_key


async def user_api_key_auth_websocket(websocket: WebSocket):
    # Accept the WebSocket connection

    request = Request(
        scope={
            "type": "http",
            "headers": [
                (k.lower().encode(), v.encode()) for k, v in websocket.headers.items()
            ],
        }
    )

    request._url = websocket.url

    query_params = websocket.query_params

    model = query_params.get("model")

    async def return_body():
        return_string = f'{{"model": "{model}"}}'
        # return string as bytes
        return return_string.encode()

    request.body = return_body  # type: ignore

    authorization = websocket.headers.get("authorization")
    # If no Authorization header, try the api-key header
    if not authorization:
        api_key = websocket.headers.get("api-key")
        if not api_key:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise HTTPException(status_code=403, detail="No API key provided")
    else:
        # Extract the API key from the Bearer token
        if not authorization.startswith("Bearer "):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise HTTPException(
                status_code=403, detail="Invalid Authorization header format"
            )

        api_key = authorization[len("Bearer ") :].strip()

    # Call user_api_key_auth with the extracted API key
    # Note: You'll need to modify this to work with WebSocket context if needed
    try:
        return await user_api_key_auth(request=request, api_key=f"Bearer {api_key}")
    except Exception as e:
        verbose_proxy_logger.exception(e)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(status_code=403, detail=str(e))


def update_valid_token_with_end_user_params(
    valid_token: UserAPIKeyAuth, end_user_params: dict
) -> UserAPIKeyAuth:
    valid_token.end_user_id = end_user_params.get("end_user_id")
    valid_token.end_user_tpm_limit = end_user_params.get("end_user_tpm_limit")
    valid_token.end_user_rpm_limit = end_user_params.get("end_user_rpm_limit")
    valid_token.allowed_model_region = end_user_params.get("allowed_model_region")
    return valid_token


async def get_global_proxy_spend(
    litellm_proxy_admin_name: str,
    user_api_key_cache: DualCache,
    prisma_client: Optional[PrismaClient],
    token: str,
    proxy_logging_obj: ProxyLogging,
) -> Optional[float]:
    global_proxy_spend = None
    if litellm.max_budget > 0:  # user set proxy max budget
        # check cache
        global_proxy_spend = await user_api_key_cache.async_get_cache(
            key="{}:spend".format(litellm_proxy_admin_name)
        )
        if global_proxy_spend is None and prisma_client is not None:
            # get from db
            sql_query = (
                """SELECT SUM(spend) as total_spend FROM "MonthlyGlobalSpend";"""
            )

            response = await prisma_client.db.query_raw(query=sql_query)

            global_proxy_spend = response[0]["total_spend"]

            await user_api_key_cache.async_set_cache(
                key="{}:spend".format(litellm_proxy_admin_name),
                value=global_proxy_spend,
            )
        if global_proxy_spend is not None:
            user_info = CallInfo(
                user_id=litellm_proxy_admin_name,
                max_budget=litellm.max_budget,
                spend=global_proxy_spend,
                token=token,
                event_group=Litellm_EntityType.PROXY,
            )
            asyncio.create_task(
                proxy_logging_obj.budget_alerts(
                    type="proxy_budget",
                    user_info=user_info,
                )
            )
    return global_proxy_spend


def get_rbac_role(jwt_handler: JWTHandler, scopes: List[str]) -> str:
    is_admin = jwt_handler.is_admin(scopes=scopes)
    if is_admin:
        return LitellmUserRoles.PROXY_ADMIN
    else:
        return LitellmUserRoles.TEAM


def get_api_key(
    custom_litellm_key_header: Optional[str],
    api_key: str,
    azure_api_key_header: Optional[str],
    anthropic_api_key_header: Optional[str],
    google_ai_studio_api_key_header: Optional[str],
    azure_apim_header: Optional[str],
    pass_through_endpoints: Optional[List[dict]],
    route: str,
    request: Request,
) -> Tuple[str, Optional[str]]:
    """
    Returns:
        Tuple[Optional[str], Optional[str]]: Tuple of the api_key and the passed_in_key
    """
    api_key = api_key
    passed_in_key: Optional[str] = None
    if isinstance(custom_litellm_key_header, str):
        passed_in_key = custom_litellm_key_header
        api_key = _get_bearer_token_or_received_api_key(custom_litellm_key_header)
    elif isinstance(api_key, str):
        passed_in_key = api_key
        api_key = _get_bearer_token(api_key=api_key)
    elif isinstance(azure_api_key_header, str):
        passed_in_key = azure_api_key_header
        api_key = azure_api_key_header
    elif isinstance(anthropic_api_key_header, str):
        passed_in_key = anthropic_api_key_header
        api_key = anthropic_api_key_header
    elif isinstance(google_ai_studio_api_key_header, str):
        passed_in_key = google_ai_studio_api_key_header
        api_key = google_ai_studio_api_key_header
    elif isinstance(azure_apim_header, str):
        passed_in_key = azure_apim_header
        api_key = azure_apim_header
    elif pass_through_endpoints is not None:
        for endpoint in pass_through_endpoints:
            if endpoint.get("path", "") == route:
                headers: Optional[dict] = endpoint.get("headers", None)
                if headers is not None:
                    header_key: str = headers.get("litellm_user_api_key", "")
                    if request.headers.get(key=header_key) is not None:
                        api_key = request.headers.get(key=header_key)
                        passed_in_key = api_key
    return api_key, passed_in_key


async def check_api_key_for_custom_headers_or_pass_through_endpoints(
    request: Request,
    route: str,
    pass_through_endpoints: Optional[List[dict]],
    api_key: str,
) -> Union[UserAPIKeyAuth, str]:
    is_mapped_pass_through_route: bool = False
    for mapped_route in LiteLLMRoutes.mapped_pass_through_routes.value:  # type: ignore
        if route.startswith(mapped_route):
            is_mapped_pass_through_route = True
    if is_mapped_pass_through_route:
        if request.headers.get("litellm_user_api_key") is not None:
            api_key = request.headers.get("litellm_user_api_key") or ""
    if pass_through_endpoints is not None:
        for endpoint in pass_through_endpoints:
            if isinstance(endpoint, dict) and endpoint.get("path", "") == route:
                ## IF AUTH DISABLED
                if endpoint.get("auth") is not True:
                    return UserAPIKeyAuth()
                ## IF AUTH ENABLED
                ### IF CUSTOM PARSER REQUIRED
                if (
                    endpoint.get("custom_auth_parser") is not None
                    and endpoint.get("custom_auth_parser") == "langfuse"
                ):
                    """
                    - langfuse returns {'Authorization': 'Basic YW55dGhpbmc6YW55dGhpbmc'}
                    - check the langfuse public key if it contains the litellm api key
                    """
                    import base64

                    api_key = api_key.replace("Basic ", "").strip()
                    decoded_bytes = base64.b64decode(api_key)
                    decoded_str = decoded_bytes.decode("utf-8")
                    api_key = decoded_str.split(":")[0]
                else:
                    headers = endpoint.get("headers", None)
                    if headers is not None:
                        header_key = headers.get("litellm_user_api_key", "")
                        if (
                            isinstance(request.headers, dict)
                            and request.headers.get(key=header_key) is not None  # type: ignore
                        ):
                            api_key = request.headers.get(key=header_key)  # type: ignore
    return api_key


async def _user_api_key_auth_builder(  # noqa: PLR0915
    request: Request,
    api_key: str,
    azure_api_key_header: str,
    anthropic_api_key_header: Optional[str],
    google_ai_studio_api_key_header: Optional[str],
    azure_apim_header: Optional[str],
    request_data: dict,
    custom_litellm_key_header: Optional[str] = None,
) -> UserAPIKeyAuth:
    from litellm.proxy.proxy_server import (
        general_settings,
        jwt_handler,
        litellm_proxy_admin_name,
        llm_model_list,
        llm_router,
        master_key,
        model_max_budget_limiter,
        open_telemetry_logger,
        prisma_client,
        proxy_logging_obj,
        user_api_key_cache,
        user_custom_auth,
    )

    parent_otel_span: Optional[Span] = None
    start_time = datetime.now()
    route: str = get_request_route(request=request)
    valid_token: Optional[UserAPIKeyAuth] = None
    custom_auth_api_key: bool = False

    try:
        # get the request body

        await pre_db_read_auth_checks(
            request_data=request_data,
            request=request,
            route=route,
        )
        pass_through_endpoints: Optional[List[dict]] = general_settings.get(
            "pass_through_endpoints", None
        )
        passed_in_key: Optional[str] = None
        ## CHECK IF X-LITELM-API-KEY IS PASSED IN - supercedes Authorization header
        api_key, passed_in_key = get_api_key(
            custom_litellm_key_header=custom_litellm_key_header,
            api_key=api_key,
            azure_api_key_header=azure_api_key_header,
            anthropic_api_key_header=anthropic_api_key_header,
            google_ai_studio_api_key_header=google_ai_studio_api_key_header,
            azure_apim_header=azure_apim_header,
            pass_through_endpoints=pass_through_endpoints,
            route=route,
            request=request,
        )
        # if user wants to pass LiteLLM_Master_Key as a custom header, example pass litellm keys as X-LiteLLM-Key: Bearer sk-1234
        custom_litellm_key_header_name = general_settings.get("litellm_key_header_name")
        if custom_litellm_key_header_name is not None:
            api_key = get_api_key_from_custom_header(
                request=request,
                custom_litellm_key_header_name=custom_litellm_key_header_name,
            )

        if open_telemetry_logger is not None:
            parent_otel_span = (
                open_telemetry_logger.create_litellm_proxy_request_started_span(
                    start_time=start_time,
                    headers=dict(request.headers),
                )
            )

        ### USER-DEFINED AUTH FUNCTION ###
        if enterprise_custom_auth is not None:
            response = await enterprise_custom_auth(
                request=request, api_key=api_key, user_custom_auth=user_custom_auth
            )
            if response is not None and isinstance(response, UserAPIKeyAuth):
                return UserAPIKeyAuth.model_validate(response)
            elif response is not None and isinstance(response, str):
                api_key = response
                custom_auth_api_key = True
        elif user_custom_auth is not None:
            response = await user_custom_auth(request=request, api_key=api_key)  # type: ignore
            return UserAPIKeyAuth.model_validate(response)

        ### LITELLM-DEFINED AUTH FUNCTION ###
        #### IF JWT ####
        """
        LiteLLM supports using JWTs.

        Enable this in proxy config, by setting
        ```
        general_settings:
            enable_jwt_auth: true
        ```
        """

        ######## Route Checks Before Reading DB / Cache for "token" ################
        if (
            route in LiteLLMRoutes.public_routes.value  # type: ignore
            or route_in_additonal_public_routes(current_route=route)
        ):
            # check if public endpoint
            return UserAPIKeyAuth(user_role=LitellmUserRoles.INTERNAL_USER_VIEW_ONLY)
        elif is_pass_through_provider_route(route=route):
            if should_run_auth_on_pass_through_provider_route(route=route) is False:
                return UserAPIKeyAuth(
                    user_role=LitellmUserRoles.INTERNAL_USER_VIEW_ONLY
                )

        ########## End of Route Checks Before Reading DB / Cache for "token" ########

        if general_settings.get("enable_oauth2_auth", False) is True:
            # return UserAPIKeyAuth object
            # helper to check if the api_key is a valid oauth2 token
            from litellm.proxy.proxy_server import premium_user

            if premium_user is not True:
                raise ValueError(
                    "Oauth2 token validation is only available for premium users"
                    + CommonProxyErrors.not_premium_user.value
                )

            return await check_oauth2_token(token=api_key)

        if general_settings.get("enable_oauth2_proxy_auth", False) is True:
            return await handle_oauth2_proxy_request(request=request)

        if general_settings.get("enable_jwt_auth", False) is True:
            from litellm.proxy.proxy_server import premium_user

            if premium_user is not True:
                raise ValueError(
                    f"JWT Auth is an enterprise only feature. {CommonProxyErrors.not_premium_user.value}"
                )
            is_jwt = jwt_handler.is_jwt(token=api_key)
            verbose_proxy_logger.debug("is_jwt: %s", is_jwt)
            if is_jwt:
                result = await JWTAuthManager.auth_builder(
                    request_data=request_data,
                    general_settings=general_settings,
                    api_key=api_key,
                    jwt_handler=jwt_handler,
                    route=route,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                    proxy_logging_obj=proxy_logging_obj,
                    parent_otel_span=parent_otel_span,
                )

                is_proxy_admin = result["is_proxy_admin"]
                team_id = result["team_id"]
                team_object = result["team_object"]
                user_id = result["user_id"]
                user_object = result["user_object"]
                end_user_id = result["end_user_id"]
                end_user_object = result["end_user_object"]
                org_id = result["org_id"]
                token = result["token"]

                global_proxy_spend = await get_global_proxy_spend(
                    litellm_proxy_admin_name=litellm_proxy_admin_name,
                    user_api_key_cache=user_api_key_cache,
                    prisma_client=prisma_client,
                    token=token,
                    proxy_logging_obj=proxy_logging_obj,
                )

                if is_proxy_admin:
                    return UserAPIKeyAuth(
                        user_role=LitellmUserRoles.PROXY_ADMIN,
                        parent_otel_span=parent_otel_span,
                    )

                valid_token = UserAPIKeyAuth(
                    api_key=None,
                    team_id=team_id,
                    team_tpm_limit=(
                        team_object.tpm_limit if team_object is not None else None
                    ),
                    team_rpm_limit=(
                        team_object.rpm_limit if team_object is not None else None
                    ),
                    team_models=team_object.models if team_object is not None else [],
                    user_role=(
                        LitellmUserRoles(user_object.user_role)
                        if user_object is not None and user_object.user_role is not None
                        else LitellmUserRoles.INTERNAL_USER
                    ),
                    user_id=user_id,
                    org_id=org_id,
                    parent_otel_span=parent_otel_span,
                    end_user_id=end_user_id,
                )
                # run through common checks
                _ = await common_checks(
                    request=request,
                    request_body=request_data,
                    team_object=team_object,
                    user_object=user_object,
                    end_user_object=end_user_object,
                    general_settings=general_settings,
                    global_proxy_spend=global_proxy_spend,
                    route=route,
                    llm_router=llm_router,
                    proxy_logging_obj=proxy_logging_obj,
                    valid_token=valid_token,
                )

                # return UserAPIKeyAuth object
                return cast(UserAPIKeyAuth, valid_token)

        #### ELSE ####
        ## CHECK PASS-THROUGH ENDPOINTS ##
        if not custom_auth_api_key:
            response = await check_api_key_for_custom_headers_or_pass_through_endpoints(
                request=request,
                route=route,
                pass_through_endpoints=pass_through_endpoints,
                api_key=api_key,
            )
            if isinstance(response, str):
                api_key = response
            elif isinstance(response, UserAPIKeyAuth):
                return response
        if master_key is None:
            if isinstance(api_key, str):
                return UserAPIKeyAuth(
                    api_key=api_key,
                    user_role=LitellmUserRoles.PROXY_ADMIN,
                    parent_otel_span=parent_otel_span,
                )
            else:
                return UserAPIKeyAuth(
                    user_role=LitellmUserRoles.PROXY_ADMIN,
                    parent_otel_span=parent_otel_span,
                )
        elif api_key is None:  # only require api key if master key is set
            raise Exception("No api key passed in.")
        elif api_key == "":
            # missing 'Bearer ' prefix
            raise Exception(
                f"Malformed API Key passed in. Ensure Key has `Bearer ` prefix. Passed in: {passed_in_key}"
            )

        if route == "/user/auth":
            if general_settings.get("allow_user_auth", False) is True:
                return UserAPIKeyAuth()
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="'allow_user_auth' not set or set to False",
                )

        ## Check END-USER OBJECT
        _end_user_object = None
        end_user_params = {}

        end_user_id = get_end_user_id_from_request_body(
            request_data, _safe_get_request_headers(request)
        )
        if end_user_id:
            try:
                end_user_params["end_user_id"] = end_user_id

                # get end-user object
                _end_user_object = await get_end_user_object(
                    end_user_id=end_user_id,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                    parent_otel_span=parent_otel_span,
                    proxy_logging_obj=proxy_logging_obj,
                )
                if _end_user_object is not None:
                    end_user_params["allowed_model_region"] = (
                        _end_user_object.allowed_model_region
                    )
                    if _end_user_object.litellm_budget_table is not None:
                        budget_info = _end_user_object.litellm_budget_table
                        if budget_info.tpm_limit is not None:
                            end_user_params["end_user_tpm_limit"] = (
                                budget_info.tpm_limit
                            )
                        if budget_info.rpm_limit is not None:
                            end_user_params["end_user_rpm_limit"] = (
                                budget_info.rpm_limit
                            )
                        if budget_info.max_budget is not None:
                            end_user_params["end_user_max_budget"] = (
                                budget_info.max_budget
                            )
            except Exception as e:
                if isinstance(e, litellm.BudgetExceededError):
                    raise e
                verbose_proxy_logger.debug(
                    "Unable to find user in db. Error - {}".format(str(e))
                )
                pass

        ### CHECK IF ADMIN ###
        # note: never string compare api keys, this is vulenerable to a time attack. Use secrets.compare_digest instead
        ### CHECK IF ADMIN ###
        # note: never string compare api keys, this is vulenerable to a time attack. Use secrets.compare_digest instead
        ## Check CACHE
        try:
            valid_token = await get_key_object(
                hashed_token=hash_token(api_key),
                prisma_client=prisma_client,
                user_api_key_cache=user_api_key_cache,
                parent_otel_span=parent_otel_span,
                proxy_logging_obj=proxy_logging_obj,
                check_cache_only=True,
            )
        except Exception:
            verbose_logger.debug("api key not found in cache.")
            valid_token = None

        ## Check UI Hash Key
        if valid_token is None and get_secret_bool("EXPERIMENTAL_UI_LOGIN"):
            valid_token = ExperimentalUIJWTToken.get_key_object_from_ui_hash_key(
                api_key
            )

        if (
            valid_token is not None
            and isinstance(valid_token, UserAPIKeyAuth)
            and valid_token.user_role == LitellmUserRoles.PROXY_ADMIN
        ):
            # update end-user params on valid token
            valid_token = update_valid_token_with_end_user_params(
                valid_token=valid_token, end_user_params=end_user_params
            )
            valid_token.parent_otel_span = parent_otel_span

            return valid_token

        if (
            valid_token is not None
            and isinstance(valid_token, UserAPIKeyAuth)
            and valid_token.team_id is not None
        ):
            ## UPDATE TEAM VALUES BASED ON CACHED TEAM OBJECT - allows `/team/update` values to work for cached token
            try:
                team_obj: LiteLLM_TeamTableCachedObj = await get_team_object(
                    team_id=valid_token.team_id,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                    parent_otel_span=parent_otel_span,
                    proxy_logging_obj=proxy_logging_obj,
                    check_cache_only=True,
                )

                if (
                    team_obj.last_refreshed_at is not None
                    and valid_token.last_refreshed_at is not None
                    and team_obj.last_refreshed_at > valid_token.last_refreshed_at
                ):
                    team_obj_dict = team_obj.__dict__

                    for k, v in team_obj_dict.items():
                        field_name = f"team_{k}"
                        if field_name in valid_token.__fields__:
                            setattr(valid_token, field_name, v)
            except Exception as e:
                verbose_logger.debug(
                    e
                )  # moving from .warning to .debug as it spams logs when team missing from cache.

        try:
            is_master_key_valid = secrets.compare_digest(api_key, master_key)  # type: ignore
        except Exception:
            is_master_key_valid = False

        ## VALIDATE MASTER KEY ##
        try:
            assert isinstance(master_key, str)
        except Exception:
            raise HTTPException(
                status_code=500,
                detail={
                    "Master key must be a valid string. Current type={}".format(
                        type(master_key)
                    )
                },
            )

        if is_master_key_valid:
            _user_api_key_obj = await _return_user_api_key_auth_obj(
                user_obj=None,
                user_role=LitellmUserRoles.PROXY_ADMIN,
                api_key=master_key,
                parent_otel_span=parent_otel_span,
                valid_token_dict={
                    **end_user_params,
                    "user_id": litellm_proxy_admin_name,
                },
                route=route,
                start_time=start_time,
            )
            asyncio.create_task(
                _cache_key_object(
                    hashed_token=hash_token(master_key),
                    user_api_key_obj=_user_api_key_obj,
                    user_api_key_cache=user_api_key_cache,
                    proxy_logging_obj=proxy_logging_obj,
                )
            )

            _user_api_key_obj = update_valid_token_with_end_user_params(
                valid_token=_user_api_key_obj, end_user_params=end_user_params
            )

            return _user_api_key_obj

        ## IF it's not a master key
        ## Route should not be in master_key_only_routes
        if route in LiteLLMRoutes.master_key_only_routes.value:  # type: ignore
            raise Exception(
                f"Tried to access route={route}, which is only for MASTER KEY"
            )

        ## Check DB

        if (
            prisma_client is None
        ):  # if both master key + user key submitted, and user key != master key, and no db connected, raise an error
            raise ProxyException(
                message="No connected db.",
                type=ProxyErrorTypes.no_db_connection,
                code=400,
                param=None,
            )

        ## check for cache hit (In-Memory Cache)
        _user_role = None

        if valid_token is None:
            if isinstance(
                api_key, str
            ):  # if generated token, make sure it starts with sk-.
                assert api_key.startswith(
                    "sk-"
                ), "LiteLLM Virtual Key expected. Received={}, expected to start with 'sk-'.".format(
                    api_key
                )  # prevent token hashes from being used
            else:
                verbose_logger.warning(
                    "litellm.proxy.proxy_server.user_api_key_auth(): Warning - Key is not a string. Got type={}".format(
                        type(api_key) if api_key is not None else "None"
                    )
                )
            abbreviated_api_key = abbreviate_api_key(api_key=api_key)
            if api_key.startswith("sk-"):
                api_key = hash_token(token=api_key)

            try:
                valid_token = await get_key_object(
                    hashed_token=api_key,
                    prisma_client=prisma_client,
                    user_api_key_cache=user_api_key_cache,
                    parent_otel_span=parent_otel_span,
                    proxy_logging_obj=proxy_logging_obj,
                )
            except ProxyException as e:
                if e.code == 401 or e.code == "401":
                    e.message = "Authentication Error, Invalid proxy server token passed. Received API Key = {}, Key Hash (Token) ={}. Unable to find token in cache or `LiteLLM_VerificationTokenTable`".format(
                        abbreviated_api_key, api_key
                    )
                raise e
            # update end-user params on valid token
            # These can change per request - it's important to update them here
            valid_token.end_user_id = end_user_params.get("end_user_id")
            valid_token.end_user_tpm_limit = end_user_params.get("end_user_tpm_limit")
            valid_token.end_user_rpm_limit = end_user_params.get("end_user_rpm_limit")
            valid_token.allowed_model_region = end_user_params.get(
                "allowed_model_region"
            )
            # update key budget with temp budget increase
            valid_token = _update_key_budget_with_temp_budget_increase(
                valid_token
            )  # updating it here, allows all downstream reporting / checks to use the updated budget

        user_obj: Optional[LiteLLM_UserTable] = None
        valid_token_dict: dict = {}
        if valid_token is not None:
            # Got Valid Token from Cache, DB
            # Run checks for
            # 1. If token can call model
            ## 1a. If token can call fallback models (if client-side fallbacks given)
            # 2. If user_id for this token is in budget
            # 3. If the user spend within their own team is within budget
            # 4. If 'user' passed to /chat/completions, /embeddings endpoint is in budget
            # 5. If token is expired
            # 6. If token spend is under Budget for the token
            # 7. If token spend per model is under budget per model
            # 8. If token spend is under team budget
            # 9. If team spend is under team budget

            ## base case ## key is disabled
            if valid_token.blocked is True:
                raise Exception(
                    "Key is blocked. Update via `/key/unblock` if you're admin."
                )
            config = valid_token.config

            if config != {}:
                model_list = config.get("model_list", [])
                new_model_list = model_list
                verbose_proxy_logger.debug(
                    f"\n new llm router model list {new_model_list}"
                )
            elif (
                isinstance(valid_token.models, list)
                and "all-team-models" in valid_token.models
            ):
                # Do not do any validation at this step
                # the validation will occur when checking the team has access to this model
                pass
            else:
                model = get_model_from_request(request_data, route)
                fallback_models = cast(
                    Optional[List[ALL_FALLBACK_MODEL_VALUES]],
                    request_data.get("fallbacks", None),
                )

                if model is not None:
                    await can_key_call_model(
                        model=model,
                        llm_model_list=llm_model_list,
                        valid_token=valid_token,
                        llm_router=llm_router,
                    )

                if fallback_models is not None:
                    for m in fallback_models:
                        await can_key_call_model(
                            model=m["model"] if isinstance(m, dict) else m,
                            llm_model_list=llm_model_list,
                            valid_token=valid_token,
                            llm_router=llm_router,
                        )
                        await is_valid_fallback_model(
                            model=m["model"] if isinstance(m, dict) else m,
                            llm_router=llm_router,
                            user_model=None,
                        )

            # Check 2. If user_id for this token is in budget - done in common_checks()
            if valid_token.user_id is not None:
                try:
                    user_obj = await get_user_object(
                        user_id=valid_token.user_id,
                        prisma_client=prisma_client,
                        user_api_key_cache=user_api_key_cache,
                        user_id_upsert=False,
                        parent_otel_span=parent_otel_span,
                        proxy_logging_obj=proxy_logging_obj,
                    )
                except Exception as e:
                    verbose_logger.debug(
                        "litellm.proxy.auth.user_api_key_auth.py::user_api_key_auth() - Unable to get user from db/cache. Setting user_obj to None. Exception received - {}".format(
                            str(e)
                        )
                    )
                    user_obj = None

            # Check 3. Check if user is in their team budget
            if valid_token.team_member_spend is not None:

                if prisma_client is not None:
                    _cache_key = f"{valid_token.team_id}_{valid_token.user_id}"

                    team_member_info = await user_api_key_cache.async_get_cache(
                        key=_cache_key
                    )
                    if team_member_info is None:
                        # read from DB
                        _user_id = valid_token.user_id
                        _team_id = valid_token.team_id

                        if _user_id is not None and _team_id is not None:
                            team_member_info = await prisma_client.db.litellm_teammembership.find_first(
                                where={
                                    "user_id": _user_id,
                                    "team_id": _team_id,
                                },  # type: ignore
                                include={"litellm_budget_table": True},
                            )
                            await user_api_key_cache.async_set_cache(
                                key=_cache_key,
                                value=team_member_info,
                                ttl=5,
                            )

                    if (
                        team_member_info is not None
                        and team_member_info.litellm_budget_table is not None
                    ):
                        team_member_budget = (
                            team_member_info.litellm_budget_table.max_budget
                        )
                        if team_member_budget is not None and team_member_budget > 0:
                            if valid_token.team_member_spend > team_member_budget:
                                raise litellm.BudgetExceededError(
                                    current_cost=valid_token.team_member_spend,
                                    max_budget=team_member_budget,
                                )

            # Check 3. If token is expired
            if valid_token.expires is not None:
                current_time = datetime.now(timezone.utc)
                if isinstance(valid_token.expires, datetime):
                    expiry_time = valid_token.expires
                else:
                    expiry_time = datetime.fromisoformat(valid_token.expires)
                if (
                    expiry_time.tzinfo is None
                    or expiry_time.tzinfo.utcoffset(expiry_time) is None
                ):
                    expiry_time = expiry_time.replace(tzinfo=timezone.utc)
                verbose_proxy_logger.debug(
                    f"Checking if token expired, expiry time {expiry_time} and current time {current_time}"
                )
                if expiry_time < current_time:
                    # Token exists but is expired.
                    raise ProxyException(
                        message=f"Authentication Error - Expired Key. Key Expiry time {expiry_time} and current time {current_time}",
                        type=ProxyErrorTypes.expired_key,
                        code=400,
                        param=api_key,
                    )

            # Check 4. Token Spend is under budget
            if route in LiteLLMRoutes.llm_api_routes.value:
                await _virtual_key_max_budget_check(
                    valid_token=valid_token,
                    proxy_logging_obj=proxy_logging_obj,
                    user_obj=user_obj,
                )

            # Check 5. Soft Budget Check
            await _virtual_key_soft_budget_check(
                valid_token=valid_token,
                proxy_logging_obj=proxy_logging_obj,
            )

            # Check 5. Token Model Spend is under Model budget
            max_budget_per_model = valid_token.model_max_budget
            current_model = request_data.get("model", None)

            if (
                max_budget_per_model is not None
                and isinstance(max_budget_per_model, dict)
                and len(max_budget_per_model) > 0
                and prisma_client is not None
                and current_model is not None
                and valid_token.token is not None
            ):
                ## GET THE SPEND FOR THIS MODEL
                await model_max_budget_limiter.is_key_within_model_budget(
                    user_api_key_dict=valid_token,
                    model=current_model,
                )

            # Check 6: Additional Common Checks across jwt + key auth
            if valid_token.team_id is not None:
                _team_obj: Optional[LiteLLM_TeamTable] = LiteLLM_TeamTable(
                    team_id=valid_token.team_id,
                    max_budget=valid_token.team_max_budget,
                    spend=valid_token.team_spend,
                    tpm_limit=valid_token.team_tpm_limit,
                    rpm_limit=valid_token.team_rpm_limit,
                    blocked=valid_token.team_blocked,
                    models=valid_token.team_models,
                    metadata=valid_token.team_metadata,
                )
            else:
                _team_obj = None

            user_api_key_cache.set_cache(
                key=valid_token.team_id, value=_team_obj
            )  # save team table in cache - used for tpm/rpm limiting - tpm_rpm_limiter.py

            global_proxy_spend = None
            if (
                litellm.max_budget > 0 and prisma_client is not None
            ):  # user set proxy max budget
                # check cache
                global_proxy_spend = await user_api_key_cache.async_get_cache(
                    key="{}:spend".format(litellm_proxy_admin_name)
                )
                if global_proxy_spend is None:
                    # get from db
                    sql_query = """SELECT SUM(spend) as total_spend FROM "MonthlyGlobalSpend";"""

                    response = await prisma_client.db.query_raw(query=sql_query)

                    global_proxy_spend = response[0]["total_spend"]
                    await user_api_key_cache.async_set_cache(
                        key="{}:spend".format(litellm_proxy_admin_name),
                        value=global_proxy_spend,
                    )

                if global_proxy_spend is not None:
                    call_info = CallInfo(
                        token=valid_token.token,
                        spend=global_proxy_spend,
                        max_budget=litellm.max_budget,
                        user_id=litellm_proxy_admin_name,
                        team_id=valid_token.team_id,
                        event_group=Litellm_EntityType.PROXY,
                    )
                    asyncio.create_task(
                        proxy_logging_obj.budget_alerts(
                            type="proxy_budget",
                            user_info=call_info,
                        )
                    )
            _ = await common_checks(
                request=request,
                request_body=request_data,
                team_object=_team_obj,
                user_object=user_obj,
                end_user_object=_end_user_object,
                general_settings=general_settings,
                global_proxy_spend=global_proxy_spend,
                route=route,
                llm_router=llm_router,
                proxy_logging_obj=proxy_logging_obj,
                valid_token=valid_token,
            )
            # Token passed all checks
            if valid_token is None:
                raise HTTPException(401, detail="Invalid API key")
            if valid_token.token is None:
                raise HTTPException(401, detail="Invalid API key, no token associated")
            api_key = valid_token.token

            # Add hashed token to cache
            asyncio.create_task(
                _cache_key_object(
                    hashed_token=api_key,
                    user_api_key_obj=valid_token,
                    user_api_key_cache=user_api_key_cache,
                    proxy_logging_obj=proxy_logging_obj,
                )
            )

            valid_token_dict = valid_token.model_dump(exclude_none=True)
            valid_token_dict.pop("token", None)

            if _end_user_object is not None:
                valid_token_dict.update(end_user_params)

        # check if token is from litellm-ui, litellm ui makes keys to allow users to login with sso. These keys can only be used for LiteLLM UI functions
        # sso/login, ui/login, /key functions and /user functions
        # this will never be allowed to call /chat/completions

        if valid_token is None:
            # No token was found when looking up in the DB
            raise Exception("Invalid proxy server token passed")
        if valid_token_dict is not None:
            return await _return_user_api_key_auth_obj(
                user_obj=user_obj,
                api_key=api_key,
                parent_otel_span=parent_otel_span,
                valid_token_dict=valid_token_dict,
                route=route,
                start_time=start_time,
            )
    except Exception as e:
        return await UserAPIKeyAuthExceptionHandler._handle_authentication_error(
            e=e,
            request=request,
            request_data=request_data,
            route=route,
            parent_otel_span=parent_otel_span,
            api_key=api_key,
        )


@tracer.wrap()
async def user_api_key_auth(
    request: Request,
    api_key: str = fastapi.Security(api_key_header),
    azure_api_key_header: str = fastapi.Security(azure_api_key_header),
    anthropic_api_key_header: Optional[str] = fastapi.Security(
        anthropic_api_key_header
    ),
    google_ai_studio_api_key_header: Optional[str] = fastapi.Security(
        google_ai_studio_api_key_header
    ),
    azure_apim_header: Optional[str] = fastapi.Security(azure_apim_header),
    custom_litellm_key_header: Optional[str] = fastapi.Security(
        custom_litellm_key_header
    ),
) -> UserAPIKeyAuth:
    """
    Parent function to authenticate user api key / jwt token.
    """

    request_data = await _read_request_body(request=request)
    route: str = get_request_route(request=request)

    user_api_key_auth_obj = await _user_api_key_auth_builder(
        request=request,
        api_key=api_key,
        azure_api_key_header=azure_api_key_header,
        anthropic_api_key_header=anthropic_api_key_header,
        google_ai_studio_api_key_header=google_ai_studio_api_key_header,
        azure_apim_header=azure_apim_header,
        request_data=request_data,
        custom_litellm_key_header=custom_litellm_key_header,
    )

    end_user_id = get_end_user_id_from_request_body(
        request_data, _safe_get_request_headers(request)
    )
    if end_user_id is not None:
        user_api_key_auth_obj.end_user_id = end_user_id

    user_api_key_auth_obj.request_route = route

    return user_api_key_auth_obj


async def _return_user_api_key_auth_obj(
    user_obj: Optional[LiteLLM_UserTable],
    api_key: str,
    parent_otel_span: Optional[Span],
    valid_token_dict: dict,
    route: str,
    start_time: datetime,
    user_role: Optional[LitellmUserRoles] = None,
) -> UserAPIKeyAuth:
    end_time = datetime.now()

    asyncio.create_task(
        user_api_key_service_logger_obj.async_service_success_hook(
            service=ServiceTypes.AUTH,
            call_type=route,
            start_time=start_time,
            end_time=end_time,
            duration=end_time.timestamp() - start_time.timestamp(),
            parent_otel_span=parent_otel_span,
        )
    )

    retrieved_user_role = (
        user_role or _get_user_role(user_obj=user_obj) or LitellmUserRoles.INTERNAL_USER
    )

    user_api_key_kwargs = {
        "api_key": api_key,
        "parent_otel_span": parent_otel_span,
        "user_role": retrieved_user_role,
        **valid_token_dict,
    }
    if user_obj is not None:
        user_api_key_kwargs.update(
            user_tpm_limit=user_obj.tpm_limit,
            user_rpm_limit=user_obj.rpm_limit,
            user_email=user_obj.user_email,
        )
    if user_obj is not None and _is_user_proxy_admin(user_obj=user_obj):
        user_api_key_kwargs.update(
            user_role=LitellmUserRoles.PROXY_ADMIN,
        )
        return UserAPIKeyAuth(**user_api_key_kwargs)
    else:
        return UserAPIKeyAuth(**user_api_key_kwargs)


def get_api_key_from_custom_header(
    request: Request, custom_litellm_key_header_name: str
) -> str:
    """
    Get API key from custom header

    Args:
        request (Request): Request object
        custom_litellm_key_header_name (str): Custom header name

    Returns:
        Optional[str]: API key
    """
    api_key: str = ""
    # use this as the virtual key passed to litellm proxy
    custom_litellm_key_header_name = custom_litellm_key_header_name.lower()
    _headers = {k.lower(): v for k, v in request.headers.items()}
    verbose_proxy_logger.debug(
        "searching for custom_litellm_key_header_name= %s, in headers=%s",
        custom_litellm_key_header_name,
        _headers,
    )
    custom_api_key = _headers.get(custom_litellm_key_header_name)
    if custom_api_key:
        api_key = _get_bearer_token(api_key=custom_api_key)
        verbose_proxy_logger.debug(
            "Found custom API key using header: {}, setting api_key={}".format(
                custom_litellm_key_header_name, api_key
            )
        )
    else:
        verbose_proxy_logger.exception(
            f"No LiteLLM Virtual Key pass. Please set header={custom_litellm_key_header_name}: Bearer <api_key>"
        )
    return api_key


def _get_temp_budget_increase(valid_token: UserAPIKeyAuth):
    valid_token_metadata = valid_token.metadata
    if (
        "temp_budget_increase" in valid_token_metadata
        and "temp_budget_expiry" in valid_token_metadata
    ):
        expiry = datetime.fromisoformat(valid_token_metadata["temp_budget_expiry"])
        if expiry > datetime.now():
            return valid_token_metadata["temp_budget_increase"]
    return None


def _update_key_budget_with_temp_budget_increase(
    valid_token: UserAPIKeyAuth,
) -> UserAPIKeyAuth:
    if valid_token.max_budget is None:
        return valid_token
    temp_budget_increase = _get_temp_budget_increase(valid_token) or 0.0
    valid_token.max_budget = valid_token.max_budget + temp_budget_increase
    return valid_token

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\text_service\client.py ===
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

from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1beta3.types import safety, text_service

from .transports.base import DEFAULT_CLIENT_INFO, TextServiceTransport
from .transports.grpc import TextServiceGrpcTransport
from .transports.grpc_asyncio import TextServiceGrpcAsyncIOTransport
from .transports.rest import TextServiceRestTransport


class TextServiceClientMeta(type):
    """Metaclass for the TextService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = OrderedDict()  # type: Dict[str, Type[TextServiceTransport]]
    _transport_registry["grpc"] = TextServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = TextServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = TextServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[TextServiceTransport]:
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


class TextServiceClient(metaclass=TextServiceClientMeta):
    """API for using Generative Language Models (GLMs) trained to
    generate text.
    Also known as Large Language Models (LLM)s, these generate text
    given an input prompt from the user.
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
            TextServiceClient: The constructed client.
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
            TextServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> TextServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            TextServiceTransport: The transport used by the client
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
            _default_universe = TextServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = TextServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = TextServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
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
        universe_domain = TextServiceClient._DEFAULT_UNIVERSE
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

        default_universe = TextServiceClient._DEFAULT_UNIVERSE
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
            or TextServiceClient._compare_universes(
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
            Union[str, TextServiceTransport, Callable[..., TextServiceTransport]]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the text service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,TextServiceTransport,Callable[..., TextServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the TextServiceTransport constructor.
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
        ) = TextServiceClient._read_environment_variables()
        self._client_cert_source = TextServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = TextServiceClient._get_universe_domain(
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
        transport_provided = isinstance(transport, TextServiceTransport)
        if transport_provided:
            # transport is a TextServiceTransport instance.
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
            self._transport = cast(TextServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = self._api_endpoint or TextServiceClient._get_api_endpoint(
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
                Type[TextServiceTransport], Callable[..., TextServiceTransport]
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., TextServiceTransport], transport)
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

    def generate_text(
        self,
        request: Optional[Union[text_service.GenerateTextRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[text_service.TextPrompt] = None,
        temperature: Optional[float] = None,
        candidate_count: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.GenerateTextResponse:
        r"""Generates a response from the model given an input
        message.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_generate_text():
                # Create a client
                client = generativelanguage_v1beta3.TextServiceClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta3.TextPrompt()
                prompt.text = "text_value"

                request = generativelanguage_v1beta3.GenerateTextRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = client.generate_text(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.GenerateTextRequest, dict]):
                The request object. Request to generate a text completion
                response from the model.
            model (str):
                Required. The name of the ``Model`` or ``TunedModel`` to
                use for generating the completion. Examples:
                models/text-bison-001
                tunedModels/sentence-translator-u3b7m

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (google.ai.generativelanguage_v1beta3.types.TextPrompt):
                Required. The free-form input text
                given to the model as a prompt.
                Given a prompt, the model will generate
                a TextCompletion response it predicts as
                the completion of the input text.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            temperature (float):
                Optional. Controls the randomness of the output. Note:
                The default value varies by model, see the
                ``Model.temperature`` attribute of the ``Model``
                returned the ``getModel`` function.

                Values can range from [0.0,1.0], inclusive. A value
                closer to 1.0 will produce responses that are more
                varied and creative, while a value closer to 0.0 will
                typically result in more straightforward responses from
                the model.

                This corresponds to the ``temperature`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            candidate_count (int):
                Optional. Number of generated responses to return.

                This value must be between [1, 8], inclusive. If unset,
                this will default to 1.

                This corresponds to the ``candidate_count`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            max_output_tokens (int):
                Optional. The maximum number of tokens to include in a
                candidate.

                If unset, this will default to output_token_limit
                specified in the ``Model`` specification.

                This corresponds to the ``max_output_tokens`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_p (float):
                Optional. The maximum cumulative probability of tokens
                to consider when sampling.

                The model uses combined Top-k and nucleus sampling.

                Tokens are sorted based on their assigned probabilities
                so that only the most likely tokens are considered.
                Top-k sampling directly limits the maximum number of
                tokens to consider, while Nucleus sampling limits number
                of tokens based on the cumulative probability.

                Note: The default value varies by model, see the
                ``Model.top_p`` attribute of the ``Model`` returned the
                ``getModel`` function.

                This corresponds to the ``top_p`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_k (int):
                Optional. The maximum number of tokens to consider when
                sampling.

                The model uses combined Top-k and nucleus sampling.

                Top-k sampling considers the set of ``top_k`` most
                probable tokens. Defaults to 40.

                Note: The default value varies by model, see the
                ``Model.top_k`` attribute of the ``Model`` returned the
                ``getModel`` function.

                This corresponds to the ``top_k`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.GenerateTextResponse:
                The response from the model,
                including candidate completions.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any(
            [
                model,
                prompt,
                temperature,
                candidate_count,
                max_output_tokens,
                top_p,
                top_k,
            ]
        )
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.GenerateTextRequest):
            request = text_service.GenerateTextRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if prompt is not None:
                request.prompt = prompt
            if temperature is not None:
                request.temperature = temperature
            if candidate_count is not None:
                request.candidate_count = candidate_count
            if max_output_tokens is not None:
                request.max_output_tokens = max_output_tokens
            if top_p is not None:
                request.top_p = top_p
            if top_k is not None:
                request.top_k = top_k

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.generate_text]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    def embed_text(
        self,
        request: Optional[Union[text_service.EmbedTextRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        text: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.EmbedTextResponse:
        r"""Generates an embedding from the model given an input
        message.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_embed_text():
                # Create a client
                client = generativelanguage_v1beta3.TextServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.EmbedTextRequest(
                    model="model_value",
                    text="text_value",
                )

                # Make the request
                response = client.embed_text(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.EmbedTextRequest, dict]):
                The request object. Request to get a text embedding from
                the model.
            model (str):
                Required. The model name to use with
                the format model=models/{model}.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            text (str):
                Required. The free-form input text
                that the model will turn into an
                embedding.

                This corresponds to the ``text`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.EmbedTextResponse:
                The response to a EmbedTextRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, text])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.EmbedTextRequest):
            request = text_service.EmbedTextRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if text is not None:
                request.text = text

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.embed_text]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    def batch_embed_text(
        self,
        request: Optional[Union[text_service.BatchEmbedTextRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        texts: Optional[MutableSequence[str]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.BatchEmbedTextResponse:
        r"""Generates multiple embeddings from the model given
        input text in a synchronous call.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_batch_embed_text():
                # Create a client
                client = generativelanguage_v1beta3.TextServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.BatchEmbedTextRequest(
                    model="model_value",
                    texts=['texts_value1', 'texts_value2'],
                )

                # Make the request
                response = client.batch_embed_text(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.BatchEmbedTextRequest, dict]):
                The request object. Batch request to get a text embedding
                from the model.
            model (str):
                Required. The name of the ``Model`` to use for
                generating the embedding. Examples:
                models/embedding-gecko-001

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            texts (MutableSequence[str]):
                Required. The free-form input texts
                that the model will turn into an
                embedding.  The current limit is 100
                texts, over which an error will be
                thrown.

                This corresponds to the ``texts`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.BatchEmbedTextResponse:
                The response to a EmbedTextRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, texts])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.BatchEmbedTextRequest):
            request = text_service.BatchEmbedTextRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if texts is not None:
                request.texts = texts

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.batch_embed_text]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    def count_text_tokens(
        self,
        request: Optional[Union[text_service.CountTextTokensRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[text_service.TextPrompt] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.CountTextTokensResponse:
        r"""Runs a model's tokenizer on a text and returns the
        token count.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            def sample_count_text_tokens():
                # Create a client
                client = generativelanguage_v1beta3.TextServiceClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta3.TextPrompt()
                prompt.text = "text_value"

                request = generativelanguage_v1beta3.CountTextTokensRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = client.count_text_tokens(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta3.types.CountTextTokensRequest, dict]):
                The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
            model (str):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (google.ai.generativelanguage_v1beta3.types.TextPrompt):
                Required. The free-form input text
                given to the model as a prompt.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.CountTextTokensResponse:
                A response from CountTextTokens.

                   It returns the model's token_count for the prompt.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, prompt])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.CountTextTokensRequest):
            request = text_service.CountTextTokensRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if prompt is not None:
                request.prompt = prompt

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.count_text_tokens]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    def __enter__(self) -> "TextServiceClient":
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


__all__ = ("TextServiceClient",)

# === NexusCore/openenv\Lib\site-packages\IPython\core\display.py ===
"""Top-level display functions for displaying object in different formats."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.


from binascii import b2a_base64, hexlify
import html
import json
import mimetypes
import os
import struct
import warnings
from copy import deepcopy
from os.path import splitext
from pathlib import Path, PurePath

from typing import Optional

from IPython.testing.skipdoctest import skip_doctest
from . import display_functions


__all__ = [
    "display_pretty",
    "display_html",
    "display_markdown",
    "display_svg",
    "display_png",
    "display_jpeg",
    "display_webp",
    "display_latex",
    "display_json",
    "display_javascript",
    "display_pdf",
    "DisplayObject",
    "TextDisplayObject",
    "Pretty",
    "HTML",
    "Markdown",
    "Math",
    "Latex",
    "SVG",
    "ProgressBar",
    "JSON",
    "GeoJSON",
    "Javascript",
    "Image",
    "Video",
]

#-----------------------------------------------------------------------------
# utility functions
#-----------------------------------------------------------------------------

def _safe_exists(path):
    """Check path, but don't let exceptions raise"""
    try:
        return os.path.exists(path)
    except Exception:
        return False


def _display_mimetype(mimetype, objs, raw=False, metadata=None):
    """internal implementation of all display_foo methods

    Parameters
    ----------
    mimetype : str
        The mimetype to be published (e.g. 'image/png')
    *objs : object
        The Python objects to display, or if raw=True raw text data to
        display.
    raw : bool
        Are the data objects raw data or Python objects that need to be
        formatted before display? [default: False]
    metadata : dict (optional)
        Metadata to be associated with the specific mimetype output.
    """
    if metadata:
        metadata = {mimetype: metadata}
    if raw:
        # turn list of pngdata into list of { 'image/png': pngdata }
        objs = [ {mimetype: obj} for obj in objs ]
    display_functions.display(*objs, raw=raw, metadata=metadata, include=[mimetype])

#-----------------------------------------------------------------------------
# Main functions
#-----------------------------------------------------------------------------


def display_pretty(*objs, **kwargs):
    """Display the pretty (default) representation of an object.

    Parameters
    ----------
    *objs : object
        The Python objects to display, or if raw=True raw text data to
        display.
    raw : bool
        Are the data objects raw data or Python objects that need to be
        formatted before display? [default: False]
    metadata : dict (optional)
        Metadata to be associated with the specific mimetype output.
    """
    _display_mimetype('text/plain', objs, **kwargs)


def display_html(*objs, **kwargs):
    """Display the HTML representation of an object.

    Note: If raw=False and the object does not have a HTML
    representation, no HTML will be shown.

    Parameters
    ----------
    *objs : object
        The Python objects to display, or if raw=True raw HTML data to
        display.
    raw : bool
        Are the data objects raw data or Python objects that need to be
        formatted before display? [default: False]
    metadata : dict (optional)
        Metadata to be associated with the specific mimetype output.
    """
    _display_mimetype('text/html', objs, **kwargs)


def display_markdown(*objs, **kwargs):
    """Displays the Markdown representation of an object.

    Parameters
    ----------
    *objs : object
        The Python objects to display, or if raw=True raw markdown data to
        display.
    raw : bool
        Are the data objects raw data or Python objects that need to be
        formatted before display? [default: False]
    metadata : dict (optional)
        Metadata to be associated with the specific mimetype output.
    """

    _display_mimetype('text/markdown', objs, **kwargs)


def display_svg(*objs, **kwargs):
    """Display the SVG representation of an object.

    Parameters
    ----------
    *objs : object
        The Python objects to display, or if raw=True raw svg data to
        display.
    raw : bool
        Are the data objects raw data or Python objects that need to be
        formatted before display? [default: False]
    metadata : dict (optional)
        Metadata to be associated with the specific mimetype output.
    """
    _display_mimetype('image/svg+xml', objs, **kwargs)


def display_png(*objs, **kwargs):
    """Display the PNG representation of an object.

    Parameters
    ----------
    *objs : object
        The Python objects to display, or if raw=True raw png data to
        display.
    raw : bool
        Are the data objects raw data or Python objects that need to be
        formatted before display? [default: False]
    metadata : dict (optional)
        Metadata to be associated with the specific mimetype output.
    """
    _display_mimetype('image/png', objs, **kwargs)


def display_jpeg(*objs, **kwargs):
    """Display the JPEG representation of an object.

    Parameters
    ----------
    *objs : object
        The Python objects to display, or if raw=True raw JPEG data to
        display.
    raw : bool
        Are the data objects raw data or Python objects that need to be
        formatted before display? [default: False]
    metadata : dict (optional)
        Metadata to be associated with the specific mimetype output.
    """
    _display_mimetype('image/jpeg', objs, **kwargs)


def display_webp(*objs, **kwargs):
    """Display the WEBP representation of an object.

    Parameters
    ----------
    *objs : object
        The Python objects to display, or if raw=True raw JPEG data to
        display.
    raw : bool
        Are the data objects raw data or Python objects that need to be
        formatted before display? [default: False]
    metadata : dict (optional)
        Metadata to be associated with the specific mimetype output.
    """
    _display_mimetype("image/webp", objs, **kwargs)


def display_latex(*objs, **kwargs):
    """Display the LaTeX representation of an object.

    Parameters
    ----------
    *objs : object
        The Python objects to display, or if raw=True raw latex data to
        display.
    raw : bool
        Are the data objects raw data or Python objects that need to be
        formatted before display? [default: False]
    metadata : dict (optional)
        Metadata to be associated with the specific mimetype output.
    """
    _display_mimetype('text/latex', objs, **kwargs)


def display_json(*objs, **kwargs):
    """Display the JSON representation of an object.

    Note that not many frontends support displaying JSON.

    Parameters
    ----------
    *objs : object
        The Python objects to display, or if raw=True raw json data to
        display.
    raw : bool
        Are the data objects raw data or Python objects that need to be
        formatted before display? [default: False]
    metadata : dict (optional)
        Metadata to be associated with the specific mimetype output.
    """
    _display_mimetype('application/json', objs, **kwargs)


def display_javascript(*objs, **kwargs):
    """Display the Javascript representation of an object.

    Parameters
    ----------
    *objs : object
        The Python objects to display, or if raw=True raw javascript data to
        display.
    raw : bool
        Are the data objects raw data or Python objects that need to be
        formatted before display? [default: False]
    metadata : dict (optional)
        Metadata to be associated with the specific mimetype output.
    """
    _display_mimetype('application/javascript', objs, **kwargs)


def display_pdf(*objs, **kwargs):
    """Display the PDF representation of an object.

    Parameters
    ----------
    *objs : object
        The Python objects to display, or if raw=True raw javascript data to
        display.
    raw : bool
        Are the data objects raw data or Python objects that need to be
        formatted before display? [default: False]
    metadata : dict (optional)
        Metadata to be associated with the specific mimetype output.
    """
    _display_mimetype('application/pdf', objs, **kwargs)


#-----------------------------------------------------------------------------
# Smart classes
#-----------------------------------------------------------------------------


class DisplayObject:
    """An object that wraps data to be displayed."""

    _read_flags = 'r'
    _show_mem_addr = False
    metadata = None

    def __init__(self, data=None, url=None, filename=None, metadata=None):
        """Create a display object given raw data.

        When this object is returned by an expression or passed to the
        display function, it will result in the data being displayed
        in the frontend. The MIME type of the data should match the
        subclasses used, so the Png subclass should be used for 'image/png'
        data. If the data is a URL, the data will first be downloaded
        and then displayed.

        Parameters
        ----------
        data : unicode, str or bytes
            The raw data or a URL or file to load the data from
        url : unicode
            A URL to download the data from.
        filename : unicode
            Path to a local file to load the data from.
        metadata : dict
            Dict of metadata associated to be the object when displayed
        """
        if isinstance(data, (Path, PurePath)):
            data = str(data)

        if data is not None and isinstance(data, str):
            if data.startswith('http') and url is None:
                url = data
                filename = None
                data = None
            elif _safe_exists(data) and filename is None:
                url = None
                filename = data
                data = None

        self.url = url
        self.filename = filename
        # because of @data.setter methods in
        # subclasses ensure url and filename are set
        # before assigning to self.data
        self.data = data

        if metadata is not None:
            self.metadata = metadata
        elif self.metadata is None:
            self.metadata = {}

        self.reload()
        self._check_data()

    def __repr__(self):
        if not self._show_mem_addr:
            cls = self.__class__
            r = "<%s.%s object>" % (cls.__module__, cls.__name__)
        else:
            r = super(DisplayObject, self).__repr__()
        return r

    def _check_data(self):
        """Override in subclasses if there's something to check."""
        pass

    def _data_and_metadata(self):
        """shortcut for returning metadata with shape information, if defined"""
        if self.metadata:
            return self.data, deepcopy(self.metadata)
        else:
            return self.data

    def reload(self):
        """Reload the raw data from file or URL."""
        if self.filename is not None:
            encoding = None if "b" in self._read_flags else "utf-8"
            with open(self.filename, self._read_flags, encoding=encoding) as f:
                self.data = f.read()
        elif self.url is not None:
            # Deferred import
            from urllib.request import urlopen
            response = urlopen(self.url)
            data = response.read()
            # extract encoding from header, if there is one:
            encoding = None
            if 'content-type' in response.headers:
                for sub in response.headers['content-type'].split(';'):
                    sub = sub.strip()
                    if sub.startswith('charset'):
                        encoding = sub.split('=')[-1].strip()
                        break
            if 'content-encoding' in response.headers:
                # TODO: do deflate?
                if 'gzip' in response.headers['content-encoding']:
                    import gzip
                    from io import BytesIO

                    # assume utf-8 if encoding is not specified
                    with gzip.open(
                        BytesIO(data), "rt", encoding=encoding or "utf-8"
                    ) as fp:
                        encoding = None
                        data = fp.read()

            # decode data, if an encoding was specified
            # We only touch self.data once since
            # subclasses such as SVG have @data.setter methods
            # that transform self.data into ... well svg.
            if encoding:
                self.data = data.decode(encoding, 'replace')
            else:
                self.data = data


class TextDisplayObject(DisplayObject):
    """Create a text display object given raw data.

    Parameters
    ----------
    data : str or unicode
        The raw data or a URL or file to load the data from.
    url : unicode
        A URL to download the data from.
    filename : unicode
        Path to a local file to load the data from.
    metadata : dict
        Dict of metadata associated to be the object when displayed
    """
    def _check_data(self):
        if self.data is not None and not isinstance(self.data, str):
            raise TypeError("%s expects text, not %r" % (self.__class__.__name__, self.data))

class Pretty(TextDisplayObject):

    def _repr_pretty_(self, pp, cycle):
        return pp.text(self.data)


class HTML(TextDisplayObject):

    def __init__(self, data=None, url=None, filename=None, metadata=None):
        def warn():
            if not data:
                return False

            #
            # Avoid calling lower() on the entire data, because it could be a
            # long string and we're only interested in its beginning and end.
            #
            prefix = data[:10].lower()
            suffix = data[-10:].lower()
            return prefix.startswith("<iframe ") and suffix.endswith("</iframe>")

        if warn():
            warnings.warn("Consider using IPython.display.IFrame instead")
        super(HTML, self).__init__(data=data, url=url, filename=filename, metadata=metadata)

    def _repr_html_(self):
        return self._data_and_metadata()

    def __html__(self):
        """
        This method exists to inform other HTML-using modules (e.g. Markupsafe,
        htmltag, etc) that this object is HTML and does not need things like
        special characters (<>&) escaped.
        """
        return self._repr_html_()


class Markdown(TextDisplayObject):

    def _repr_markdown_(self):
        return self._data_and_metadata()


class Math(TextDisplayObject):

    def _repr_latex_(self):
        s = r"$\displaystyle %s$" % self.data.strip('$')
        if self.metadata:
            return s, deepcopy(self.metadata)
        else:
            return s


class Latex(TextDisplayObject):

    def _repr_latex_(self):
        return self._data_and_metadata()


class SVG(DisplayObject):
    """Embed an SVG into the display.

    Note if you just want to view a svg image via a URL use `:class:Image` with
    a url=URL keyword argument.
    """

    _read_flags = 'rb'
    # wrap data in a property, which extracts the <svg> tag, discarding
    # document headers
    _data: Optional[str] = None

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, svg):
        if svg is None:
            self._data = None
            return
        # parse into dom object
        from xml.dom import minidom
        x = minidom.parseString(svg)
        # get svg tag (should be 1)
        found_svg = x.getElementsByTagName('svg')
        if found_svg:
            svg = found_svg[0].toxml()
        else:
            # fallback on the input, trust the user
            # but this is probably an error.
            pass
        if isinstance(svg, bytes):
            self._data = svg.decode(errors="replace")
        else:
            self._data = svg

    def _repr_svg_(self):
        return self._data_and_metadata()

class ProgressBar(DisplayObject):
    """Progressbar supports displaying a progressbar like element
    """
    def __init__(self, total):
        """Creates a new progressbar

        Parameters
        ----------
        total : int
            maximum size of the progressbar
        """
        self.total = total
        self._progress = 0
        self.html_width = '60ex'
        self.text_width = 60
        self._display_id = hexlify(os.urandom(8)).decode('ascii')

    def __repr__(self):
        fraction = self.progress / self.total
        filled = '=' * int(fraction * self.text_width)
        rest = ' ' * (self.text_width - len(filled))
        return '[{}{}] {}/{}'.format(
            filled, rest,
            self.progress, self.total,
        )

    def _repr_html_(self):
        return "<progress style='width:{}' max='{}' value='{}'></progress>".format(
            self.html_width, self.total, self.progress)

    def display(self):
        display_functions.display(self, display_id=self._display_id)

    def update(self):
        display_functions.display(self, display_id=self._display_id, update=True)

    @property
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value):
        self._progress = value
        self.update()

    def __iter__(self):
        self.display()
        self._progress = -1 # First iteration is 0
        return self

    def __next__(self):
        """Returns current value and increments display by one."""
        self.progress += 1
        if self.progress < self.total:
            return self.progress
        else:
            raise StopIteration()

class JSON(DisplayObject):
    """JSON expects a JSON-able dict or list

    not an already-serialized JSON string.

    Scalar types (None, number, string) are not allowed, only dict or list containers.
    """
    # wrap data in a property, which warns about passing already-serialized JSON
    _data = None
    def __init__(self, data=None, url=None, filename=None, expanded=False, metadata=None, root='root', **kwargs):
        """Create a JSON display object given raw data.

        Parameters
        ----------
        data : dict or list
            JSON data to display. Not an already-serialized JSON string.
            Scalar types (None, number, string) are not allowed, only dict
            or list containers.
        url : unicode
            A URL to download the data from.
        filename : unicode
            Path to a local file to load the data from.
        expanded : boolean
            Metadata to control whether a JSON display component is expanded.
        metadata : dict
            Specify extra metadata to attach to the json display object.
        root : str
            The name of the root element of the JSON tree
        """
        self.metadata = {
            'expanded': expanded,
            'root': root,
        }
        if metadata:
            self.metadata.update(metadata)
        if kwargs:
            self.metadata.update(kwargs)
        super(JSON, self).__init__(data=data, url=url, filename=filename)

    def _check_data(self):
        if self.data is not None and not isinstance(self.data, (dict, list)):
            raise TypeError("%s expects JSONable dict or list, not %r" % (self.__class__.__name__, self.data))

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        if isinstance(data, (Path, PurePath)):
            data = str(data)

        if isinstance(data, str):
            if self.filename is None and self.url is None:
                warnings.warn("JSON expects JSONable dict or list, not JSON strings")
            data = json.loads(data)
        self._data = data

    def _data_and_metadata(self):
        return self.data, self.metadata

    def _repr_json_(self):
        return self._data_and_metadata()


_css_t = """var link = document.createElement("link");
	link.rel = "stylesheet";
	link.type = "text/css";
	link.href = "%s";
	document.head.appendChild(link);
"""

_lib_t1 = """new Promise(function(resolve, reject) {
	var script = document.createElement("script");
	script.onload = resolve;
	script.onerror = reject;
	script.src = "%s";
	document.head.appendChild(script);
}).then(() => {
"""

_lib_t2 = """
});"""

class GeoJSON(JSON):
    """GeoJSON expects JSON-able dict

    not an already-serialized JSON string.

    Scalar types (None, number, string) are not allowed, only dict containers.
    """

    def __init__(self, *args, **kwargs):
        """Create a GeoJSON display object given raw data.

        Parameters
        ----------
        data : dict or list
            VegaLite data. Not an already-serialized JSON string.
            Scalar types (None, number, string) are not allowed, only dict
            or list containers.
        url_template : string
            Leaflet TileLayer URL template: http://leafletjs.com/reference.html#url-template
        layer_options : dict
            Leaflet TileLayer options: http://leafletjs.com/reference.html#tilelayer-options
        url : unicode
            A URL to download the data from.
        filename : unicode
            Path to a local file to load the data from.
        metadata : dict
            Specify extra metadata to attach to the json display object.

        Examples
        --------
        The following will display an interactive map of Mars with a point of
        interest on frontend that do support GeoJSON display.

            >>> from IPython.display import GeoJSON

            >>> GeoJSON(data={
            ...     "type": "Feature",
            ...     "geometry": {
            ...         "type": "Point",
            ...         "coordinates": [-81.327, 296.038]
            ...     }
            ... },
            ... url_template="http://s3-eu-west-1.amazonaws.com/whereonmars.cartodb.net/{basemap_id}/{z}/{x}/{y}.png",
            ... layer_options={
            ...     "basemap_id": "celestia_mars-shaded-16k_global",
            ...     "attribution" : "Celestia/praesepe",
            ...     "minZoom" : 0,
            ...     "maxZoom" : 18,
            ... })
            <IPython.core.display.GeoJSON object>

        In the terminal IPython, you will only see the text representation of
        the GeoJSON object.

        """

        super(GeoJSON, self).__init__(*args, **kwargs)


    def _ipython_display_(self):
        bundle = {
            'application/geo+json': self.data,
            'text/plain': '<IPython.display.GeoJSON object>'
        }
        metadata = {
            'application/geo+json': self.metadata
        }
        display_functions.display(bundle, metadata=metadata, raw=True)

class Javascript(TextDisplayObject):

    def __init__(self, data=None, url=None, filename=None, lib=None, css=None):
        """Create a Javascript display object given raw data.

        When this object is returned by an expression or passed to the
        display function, it will result in the data being displayed
        in the frontend. If the data is a URL, the data will first be
        downloaded and then displayed.

        In the Notebook, the containing element will be available as `element`,
        and jQuery will be available.  Content appended to `element` will be
        visible in the output area.

        Parameters
        ----------
        data : unicode, str or bytes
            The Javascript source code or a URL to download it from.
        url : unicode
            A URL to download the data from.
        filename : unicode
            Path to a local file to load the data from.
        lib : list or str
            A sequence of Javascript library URLs to load asynchronously before
            running the source code. The full URLs of the libraries should
            be given. A single Javascript library URL can also be given as a
            string.
        css : list or str
            A sequence of css files to load before running the source code.
            The full URLs of the css files should be given. A single css URL
            can also be given as a string.
        """
        if isinstance(lib, str):
            lib = [lib]
        elif lib is None:
            lib = []
        if isinstance(css, str):
            css = [css]
        elif css is None:
            css = []
        if not isinstance(lib, (list,tuple)):
            raise TypeError('expected sequence, got: %r' % lib)
        if not isinstance(css, (list,tuple)):
            raise TypeError('expected sequence, got: %r' % css)
        self.lib = lib
        self.css = css
        super(Javascript, self).__init__(data=data, url=url, filename=filename)

    def _repr_javascript_(self):
        r = ''
        for c in self.css:
            r += _css_t % c
        for l in self.lib:
            r += _lib_t1 % l
        r += self.data
        r += _lib_t2*len(self.lib)
        return r


# constants for identifying png/jpeg/gif/webp data
_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG = b"\xff\xd8"
_GIF1 = b"GIF87a"
_GIF2 = b"GIF89a"
_WEBP = b"WEBP"


def _pngxy(data):
    """read the (width, height) from a PNG header"""
    ihdr = data.index(b'IHDR')
    # next 8 bytes are width/height
    return struct.unpack('>ii', data[ihdr+4:ihdr+12])


def _jpegxy(data):
    """read the (width, height) from a JPEG header"""
    # adapted from http://www.64lines.com/jpeg-width-height

    idx = 4
    while True:
        block_size = struct.unpack('>H', data[idx:idx+2])[0]
        idx = idx + block_size
        if data[idx:idx+2] == b'\xFF\xC0':
            # found Start of Frame
            iSOF = idx
            break
        else:
            # read another block
            idx += 2

    h, w = struct.unpack('>HH', data[iSOF+5:iSOF+9])
    return w, h


def _gifxy(data):
    """read the (width, height) from a GIF header"""
    return struct.unpack('<HH', data[6:10])


def _webpxy(data):
    """read the (width, height) from a WEBP header"""
    if data[12:16] == b"VP8 ":
        width, height = struct.unpack("<HH", data[24:30])
        width = width & 0x3FFF
        height = height & 0x3FFF
        return (width, height)
    elif data[12:16] == b"VP8L":
        size_info = struct.unpack("<I", data[21:25])[0]
        width = 1 + ((size_info & 0x3F) << 8) | (size_info >> 24)
        height = 1 + (
            (((size_info >> 8) & 0xF) << 10)
            | (((size_info >> 14) & 0x3FC) << 2)
            | ((size_info >> 22) & 0x3)
        )
        return (width, height)
    else:
        raise ValueError("Not a valid WEBP header")


class Image(DisplayObject):

    _read_flags = "rb"
    _FMT_JPEG = "jpeg"
    _FMT_PNG = "png"
    _FMT_GIF = "gif"
    _FMT_WEBP = "webp"
    _ACCEPTABLE_EMBEDDINGS = [_FMT_JPEG, _FMT_PNG, _FMT_GIF, _FMT_WEBP]
    _MIMETYPES = {
        _FMT_PNG: "image/png",
        _FMT_JPEG: "image/jpeg",
        _FMT_GIF: "image/gif",
        _FMT_WEBP: "image/webp",
    }

    def __init__(
        self,
        data=None,
        url=None,
        filename=None,
        format=None,
        embed=None,
        width=None,
        height=None,
        retina=False,
        unconfined=False,
        metadata=None,
        alt=None,
    ):
        """Create a PNG/JPEG/GIF/WEBP image object given raw data.

        When this object is returned by an input cell or passed to the
        display function, it will result in the image being displayed
        in the frontend.

        Parameters
        ----------
        data : unicode, str or bytes
            The raw image data or a URL or filename to load the data from.
            This always results in embedded image data.

        url : unicode
            A URL to download the data from. If you specify `url=`,
            the image data will not be embedded unless you also specify `embed=True`.

        filename : unicode
            Path to a local file to load the data from.
            Images from a file are always embedded.

        format : unicode
            The format of the image data (png/jpeg/jpg/gif/webp). If a filename or URL is given
            for format will be inferred from the filename extension.

        embed : bool
            Should the image data be embedded using a data URI (True) or be
            loaded using an <img> tag. Set this to True if you want the image
            to be viewable later with no internet connection in the notebook.

            Default is `True`, unless the keyword argument `url` is set, then
            default value is `False`.

            Note that QtConsole is not able to display images if `embed` is set to `False`

        width : int
            Width in pixels to which to constrain the image in html

        height : int
            Height in pixels to which to constrain the image in html

        retina : bool
            Automatically set the width and height to half of the measured
            width and height.
            This only works for embedded images because it reads the width/height
            from image data.
            For non-embedded images, you can just set the desired display width
            and height directly.

        unconfined : bool
            Set unconfined=True to disable max-width confinement of the image.

        metadata : dict
            Specify extra metadata to attach to the image.

        alt : unicode
            Alternative text for the image, for use by screen readers.

        Examples
        --------
        embedded image data, works in qtconsole and notebook
        when passed positionally, the first arg can be any of raw image data,
        a URL, or a filename from which to load image data.
        The result is always embedding image data for inline images.

        >>> Image('https://www.google.fr/images/srpr/logo3w.png') # doctest: +SKIP
        <IPython.core.display.Image object>

        >>> Image('/path/to/image.jpg')
        <IPython.core.display.Image object>

        >>> Image(b'RAW_PNG_DATA...')
        <IPython.core.display.Image object>

        Specifying Image(url=...) does not embed the image data,
        it only generates ``<img>`` tag with a link to the source.
        This will not work in the qtconsole or offline.

        >>> Image(url='https://www.google.fr/images/srpr/logo3w.png')
        <IPython.core.display.Image object>

        """
        if isinstance(data, (Path, PurePath)):
            data = str(data)

        if filename is not None:
            ext = self._find_ext(filename)
        elif url is not None:
            ext = self._find_ext(url)
        elif data is None:
            raise ValueError("No image data found. Expecting filename, url, or data.")
        elif isinstance(data, str) and (
            data.startswith('http') or _safe_exists(data)
        ):
            ext = self._find_ext(data)
        else:
            ext = None

        if format is None:
            if ext is not None:
                if ext == u'jpg' or ext == u'jpeg':
                    format = self._FMT_JPEG
                elif ext == u'png':
                    format = self._FMT_PNG
                elif ext == u'gif':
                    format = self._FMT_GIF
                elif ext == "webp":
                    format = self._FMT_WEBP
                else:
                    format = ext.lower()
            elif isinstance(data, bytes):
                # infer image type from image data header,
                # only if format has not been specified.
                if data[:2] == _JPEG:
                    format = self._FMT_JPEG
                elif data[:8] == _PNG:
                    format = self._FMT_PNG
                elif data[8:12] == _WEBP:
                    format = self._FMT_WEBP
                elif data[:6] == _GIF1 or data[:6] == _GIF2:
                    format = self._FMT_GIF

        # failed to detect format, default png
        if format is None:
            format = self._FMT_PNG

        if format.lower() == 'jpg':
            # jpg->jpeg
            format = self._FMT_JPEG

        self.format = format.lower()
        self.embed = embed if embed is not None else (url is None)

        if self.embed and self.format not in self._ACCEPTABLE_EMBEDDINGS:
            raise ValueError("Cannot embed the '%s' image format" % (self.format))
        if self.embed:
            self._mimetype = self._MIMETYPES.get(self.format)

        self.width = width
        self.height = height
        self.retina = retina
        self.unconfined = unconfined
        self.alt = alt
        super(Image, self).__init__(data=data, url=url, filename=filename,
                metadata=metadata)

        if self.width is None and self.metadata.get('width', {}):
            self.width = metadata['width']

        if self.height is None and self.metadata.get('height', {}):
            self.height = metadata['height']

        if self.alt is None and self.metadata.get("alt", {}):
            self.alt = metadata["alt"]

        if retina:
            self._retina_shape()


    def _retina_shape(self):
        """load pixel-doubled width and height from image data"""
        if not self.embed:
            return
        if self.format == self._FMT_PNG:
            w, h = _pngxy(self.data)
        elif self.format == self._FMT_JPEG:
            w, h = _jpegxy(self.data)
        elif self.format == self._FMT_GIF:
            w, h = _gifxy(self.data)
        else:
            # retina only supports png
            return
        self.width = w // 2
        self.height = h // 2

    def reload(self):
        """Reload the raw data from file or URL."""
        if self.embed:
            super(Image,self).reload()
            if self.retina:
                self._retina_shape()

    def _repr_html_(self):
        if not self.embed:
            width = height = klass = alt = ""
            if self.width:
                width = ' width="%d"' % self.width
            if self.height:
                height = ' height="%d"' % self.height
            if self.unconfined:
                klass = ' class="unconfined"'
            if self.alt:
                alt = ' alt="%s"' % html.escape(self.alt)
            return '<img src="{url}"{width}{height}{klass}{alt}/>'.format(
                url=self.url,
                width=width,
                height=height,
                klass=klass,
                alt=alt,
            )

    def _repr_mimebundle_(self, include=None, exclude=None):
        """Return the image as a mimebundle

        Any new mimetype support should be implemented here.
        """
        if self.embed:
            mimetype = self._mimetype
            data, metadata = self._data_and_metadata(always_both=True)
            if metadata:
                metadata = {mimetype: metadata}
            return {mimetype: data}, metadata
        else:
            return {'text/html': self._repr_html_()}

    def _data_and_metadata(self, always_both=False):
        """shortcut for returning metadata with shape information, if defined"""
        try:
            b64_data = b2a_base64(self.data, newline=False).decode("ascii")
        except TypeError as e:
            raise FileNotFoundError(
                "No such file or directory: '%s'" % (self.data)) from e
        md = {}
        if self.metadata:
            md.update(self.metadata)
        if self.width:
            md['width'] = self.width
        if self.height:
            md['height'] = self.height
        if self.unconfined:
            md['unconfined'] = self.unconfined
        if self.alt:
            md["alt"] = self.alt
        if md or always_both:
            return b64_data, md
        else:
            return b64_data

    def _repr_png_(self):
        if self.embed and self.format == self._FMT_PNG:
            return self._data_and_metadata()

    def _repr_jpeg_(self):
        if self.embed and self.format == self._FMT_JPEG:
            return self._data_and_metadata()

    def _find_ext(self, s):
        base, ext = splitext(s)

        if not ext:
            return base

        # `splitext` includes leading period, so we skip it
        return ext[1:].lower()


class Video(DisplayObject):

    def __init__(self, data=None, url=None, filename=None, embed=False,
                 mimetype=None, width=None, height=None, html_attributes="controls"):
        """Create a video object given raw data or an URL.

        When this object is returned by an input cell or passed to the
        display function, it will result in the video being displayed
        in the frontend.

        Parameters
        ----------
        data : unicode, str or bytes
            The raw video data or a URL or filename to load the data from.
            Raw data will require passing ``embed=True``.

        url : unicode
            A URL for the video. If you specify ``url=``,
            the image data will not be embedded.

        filename : unicode
            Path to a local file containing the video.
            Will be interpreted as a local URL unless ``embed=True``.

        embed : bool
            Should the video be embedded using a data URI (True) or be
            loaded using a <video> tag (False).

            Since videos are large, embedding them should be avoided, if possible.
            You must confirm embedding as your intention by passing ``embed=True``.

            Local files can be displayed with URLs without embedding the content, via::

                Video('./video.mp4')

        mimetype : unicode
            Specify the mimetype for embedded videos.
            Default will be guessed from file extension, if available.

        width : int
            Width in pixels to which to constrain the video in HTML.
            If not supplied, defaults to the width of the video.

        height : int
            Height in pixels to which to constrain the video in html.
            If not supplied, defaults to the height of the video.

        html_attributes : str
            Attributes for the HTML ``<video>`` block.
            Default: ``"controls"`` to get video controls.
            Other examples: ``"controls muted"`` for muted video with controls,
            ``"loop autoplay"`` for looping autoplaying video without controls.

        Examples
        --------
        ::

            Video('https://archive.org/download/Sita_Sings_the_Blues/Sita_Sings_the_Blues_small.mp4')
            Video('path/to/video.mp4')
            Video('path/to/video.mp4', embed=True)
            Video('path/to/video.mp4', embed=True, html_attributes="controls muted autoplay")
            Video(b'raw-videodata', embed=True)
        """
        if isinstance(data, (Path, PurePath)):
            data = str(data)

        if url is None and isinstance(data, str) and data.startswith(('http:', 'https:')):
            url = data
            data = None
        elif data is not None and os.path.exists(data):
            filename = data
            data = None

        if data and not embed:
            msg = ''.join([
                "To embed videos, you must pass embed=True ",
                "(this may make your notebook files huge)\n",
                "Consider passing Video(url='...')",
            ])
            raise ValueError(msg)

        self.mimetype = mimetype
        self.embed = embed
        self.width = width
        self.height = height
        self.html_attributes = html_attributes
        super(Video, self).__init__(data=data, url=url, filename=filename)

    def _repr_html_(self):
        width = height = ''
        if self.width:
            width = ' width="%d"' % self.width
        if self.height:
            height = ' height="%d"' % self.height

        # External URLs and potentially local files are not embedded into the
        # notebook output.
        if not self.embed:
            url = self.url if self.url is not None else self.filename
            output = """<video src="{0}" {1} {2} {3}>
      Your browser does not support the <code>video</code> element.
    </video>""".format(url, self.html_attributes, width, height)
            return output

        # Embedded videos are base64-encoded.
        mimetype = self.mimetype
        if self.filename is not None:
            if not mimetype:
                mimetype, _ = mimetypes.guess_type(self.filename)

            with open(self.filename, 'rb') as f:
                video = f.read()
        else:
            video = self.data
        if isinstance(video, str):
            # unicode input is already b64-encoded
            b64_video = video
        else:
            b64_video = b2a_base64(video, newline=False).decode("ascii").rstrip()

        output = """<video {0} {1} {2}>
 <source src="data:{3};base64,{4}" type="{3}">
 Your browser does not support the video tag.
 </video>""".format(self.html_attributes, width, height, mimetype, b64_video)
        return output

    def reload(self):
        # TODO
        pass

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\text_service\client.py ===
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

from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.types import safety, text_service

from .transports.base import DEFAULT_CLIENT_INFO, TextServiceTransport
from .transports.grpc import TextServiceGrpcTransport
from .transports.grpc_asyncio import TextServiceGrpcAsyncIOTransport
from .transports.rest import TextServiceRestTransport


class TextServiceClientMeta(type):
    """Metaclass for the TextService client.

    This provides class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = OrderedDict()  # type: Dict[str, Type[TextServiceTransport]]
    _transport_registry["grpc"] = TextServiceGrpcTransport
    _transport_registry["grpc_asyncio"] = TextServiceGrpcAsyncIOTransport
    _transport_registry["rest"] = TextServiceRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[TextServiceTransport]:
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


class TextServiceClient(metaclass=TextServiceClientMeta):
    """API for using Generative Language Models (GLMs) trained to
    generate text.
    Also known as Large Language Models (LLM)s, these generate text
    given an input prompt from the user.
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
            TextServiceClient: The constructed client.
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
            TextServiceClient: The constructed client.
        """
        credentials = service_account.Credentials.from_service_account_file(filename)
        kwargs["credentials"] = credentials
        return cls(*args, **kwargs)

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> TextServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            TextServiceTransport: The transport used by the client
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
            _default_universe = TextServiceClient._DEFAULT_UNIVERSE
            if universe_domain != _default_universe:
                raise MutualTLSChannelError(
                    f"mTLS is not supported in any universe other than {_default_universe}."
                )
            api_endpoint = TextServiceClient.DEFAULT_MTLS_ENDPOINT
        else:
            api_endpoint = TextServiceClient._DEFAULT_ENDPOINT_TEMPLATE.format(
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
        universe_domain = TextServiceClient._DEFAULT_UNIVERSE
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

        default_universe = TextServiceClient._DEFAULT_UNIVERSE
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
            or TextServiceClient._compare_universes(
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
            Union[str, TextServiceTransport, Callable[..., TextServiceTransport]]
        ] = None,
        client_options: Optional[Union[client_options_lib.ClientOptions, dict]] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the text service client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,TextServiceTransport,Callable[..., TextServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the TextServiceTransport constructor.
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
        ) = TextServiceClient._read_environment_variables()
        self._client_cert_source = TextServiceClient._get_client_cert_source(
            self._client_options.client_cert_source, self._use_client_cert
        )
        self._universe_domain = TextServiceClient._get_universe_domain(
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
        transport_provided = isinstance(transport, TextServiceTransport)
        if transport_provided:
            # transport is a TextServiceTransport instance.
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
            self._transport = cast(TextServiceTransport, transport)
            self._api_endpoint = self._transport.host

        self._api_endpoint = self._api_endpoint or TextServiceClient._get_api_endpoint(
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
                Type[TextServiceTransport], Callable[..., TextServiceTransport]
            ] = (
                type(self).get_transport_class(transport)
                if isinstance(transport, str) or transport is None
                else cast(Callable[..., TextServiceTransport], transport)
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

    def generate_text(
        self,
        request: Optional[Union[text_service.GenerateTextRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[text_service.TextPrompt] = None,
        temperature: Optional[float] = None,
        candidate_count: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.GenerateTextResponse:
        r"""Generates a response from the model given an input
        message.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_generate_text():
                # Create a client
                client = generativelanguage_v1beta.TextServiceClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta.TextPrompt()
                prompt.text = "text_value"

                request = generativelanguage_v1beta.GenerateTextRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = client.generate_text(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.GenerateTextRequest, dict]):
                The request object. Request to generate a text completion
                response from the model.
            model (str):
                Required. The name of the ``Model`` or ``TunedModel`` to
                use for generating the completion. Examples:
                models/text-bison-001
                tunedModels/sentence-translator-u3b7m

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (google.ai.generativelanguage_v1beta.types.TextPrompt):
                Required. The free-form input text
                given to the model as a prompt.
                Given a prompt, the model will generate
                a TextCompletion response it predicts as
                the completion of the input text.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            temperature (float):
                Optional. Controls the randomness of the output. Note:
                The default value varies by model, see the
                ``Model.temperature`` attribute of the ``Model``
                returned the ``getModel`` function.

                Values can range from [0.0,1.0], inclusive. A value
                closer to 1.0 will produce responses that are more
                varied and creative, while a value closer to 0.0 will
                typically result in more straightforward responses from
                the model.

                This corresponds to the ``temperature`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            candidate_count (int):
                Optional. Number of generated responses to return.

                This value must be between [1, 8], inclusive. If unset,
                this will default to 1.

                This corresponds to the ``candidate_count`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            max_output_tokens (int):
                Optional. The maximum number of tokens to include in a
                candidate.

                If unset, this will default to output_token_limit
                specified in the ``Model`` specification.

                This corresponds to the ``max_output_tokens`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_p (float):
                Optional. The maximum cumulative probability of tokens
                to consider when sampling.

                The model uses combined Top-k and nucleus sampling.

                Tokens are sorted based on their assigned probabilities
                so that only the most likely tokens are considered.
                Top-k sampling directly limits the maximum number of
                tokens to consider, while Nucleus sampling limits number
                of tokens based on the cumulative probability.

                Note: The default value varies by model, see the
                ``Model.top_p`` attribute of the ``Model`` returned the
                ``getModel`` function.

                This corresponds to the ``top_p`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_k (int):
                Optional. The maximum number of tokens to consider when
                sampling.

                The model uses combined Top-k and nucleus sampling.

                Top-k sampling considers the set of ``top_k`` most
                probable tokens. Defaults to 40.

                Note: The default value varies by model, see the
                ``Model.top_k`` attribute of the ``Model`` returned the
                ``getModel`` function.

                This corresponds to the ``top_k`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.GenerateTextResponse:
                The response from the model,
                including candidate completions.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any(
            [
                model,
                prompt,
                temperature,
                candidate_count,
                max_output_tokens,
                top_p,
                top_k,
            ]
        )
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.GenerateTextRequest):
            request = text_service.GenerateTextRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if prompt is not None:
                request.prompt = prompt
            if temperature is not None:
                request.temperature = temperature
            if candidate_count is not None:
                request.candidate_count = candidate_count
            if max_output_tokens is not None:
                request.max_output_tokens = max_output_tokens
            if top_p is not None:
                request.top_p = top_p
            if top_k is not None:
                request.top_k = top_k

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.generate_text]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    def embed_text(
        self,
        request: Optional[Union[text_service.EmbedTextRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        text: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.EmbedTextResponse:
        r"""Generates an embedding from the model given an input
        message.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_embed_text():
                # Create a client
                client = generativelanguage_v1beta.TextServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.EmbedTextRequest(
                    model="model_value",
                )

                # Make the request
                response = client.embed_text(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.EmbedTextRequest, dict]):
                The request object. Request to get a text embedding from
                the model.
            model (str):
                Required. The model name to use with
                the format model=models/{model}.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            text (str):
                Optional. The free-form input text
                that the model will turn into an
                embedding.

                This corresponds to the ``text`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.EmbedTextResponse:
                The response to a EmbedTextRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, text])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.EmbedTextRequest):
            request = text_service.EmbedTextRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if text is not None:
                request.text = text

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.embed_text]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    def batch_embed_text(
        self,
        request: Optional[Union[text_service.BatchEmbedTextRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        texts: Optional[MutableSequence[str]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.BatchEmbedTextResponse:
        r"""Generates multiple embeddings from the model given
        input text in a synchronous call.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_batch_embed_text():
                # Create a client
                client = generativelanguage_v1beta.TextServiceClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.BatchEmbedTextRequest(
                    model="model_value",
                )

                # Make the request
                response = client.batch_embed_text(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.BatchEmbedTextRequest, dict]):
                The request object. Batch request to get a text embedding
                from the model.
            model (str):
                Required. The name of the ``Model`` to use for
                generating the embedding. Examples:
                models/embedding-gecko-001

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            texts (MutableSequence[str]):
                Optional. The free-form input texts
                that the model will turn into an
                embedding. The current limit is 100
                texts, over which an error will be
                thrown.

                This corresponds to the ``texts`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.BatchEmbedTextResponse:
                The response to a EmbedTextRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, texts])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.BatchEmbedTextRequest):
            request = text_service.BatchEmbedTextRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if texts is not None:
                request.texts = texts

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.batch_embed_text]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    def count_text_tokens(
        self,
        request: Optional[Union[text_service.CountTextTokensRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[text_service.TextPrompt] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.CountTextTokensResponse:
        r"""Runs a model's tokenizer on a text and returns the
        token count.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            def sample_count_text_tokens():
                # Create a client
                client = generativelanguage_v1beta.TextServiceClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta.TextPrompt()
                prompt.text = "text_value"

                request = generativelanguage_v1beta.CountTextTokensRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = client.count_text_tokens(request=request)

                # Handle the response
                print(response)

        Args:
            request (Union[google.ai.generativelanguage_v1beta.types.CountTextTokensRequest, dict]):
                The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
            model (str):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (google.ai.generativelanguage_v1beta.types.TextPrompt):
                Required. The free-form input text
                given to the model as a prompt.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.CountTextTokensResponse:
                A response from CountTextTokens.

                   It returns the model's token_count for the prompt.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, prompt])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.CountTextTokensRequest):
            request = text_service.CountTextTokensRequest(request)
            # If we have keyword arguments corresponding to fields on the
            # request, apply these.
            if model is not None:
                request.model = model
            if prompt is not None:
                request.prompt = prompt

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._transport._wrapped_methods[self._transport.count_text_tokens]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
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

    def __enter__(self) -> "TextServiceClient":
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


__all__ = ("TextServiceClient",)

# === NexusCore/openenv\Lib\site-packages\tornado\httputil.py ===
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""HTTP utility code shared by clients and servers.

This module also defines the `HTTPServerRequest` class which is exposed
via `tornado.web.RequestHandler.request`.
"""

import calendar
import collections.abc
import copy
import datetime
import email.utils
from functools import lru_cache
from http.client import responses
import http.cookies
import re
from ssl import SSLError
import time
import unicodedata
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from tornado.escape import native_str, parse_qs_bytes, utf8, to_unicode
from tornado.util import ObjectDict, unicode_type


# responses is unused in this file, but we re-export it to other files.
# Reference it so pyflakes doesn't complain.
responses

import typing
from typing import (
    Tuple,
    Iterable,
    List,
    Mapping,
    Iterator,
    Dict,
    Union,
    Optional,
    Awaitable,
    Generator,
    AnyStr,
)

if typing.TYPE_CHECKING:
    from typing import Deque  # noqa: F401
    from asyncio import Future  # noqa: F401
    import unittest  # noqa: F401

    # This can be done unconditionally in the base class of HTTPHeaders
    # after we drop support for Python 3.8.
    StrMutableMapping = collections.abc.MutableMapping[str, str]
else:
    StrMutableMapping = collections.abc.MutableMapping

# To be used with str.strip() and related methods.
HTTP_WHITESPACE = " \t"

# Roughly the inverse of RequestHandler._VALID_HEADER_CHARS, but permits
# chars greater than \xFF (which may appear after decoding utf8).
_FORBIDDEN_HEADER_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


class _ABNF:
    """Class that holds a subset of ABNF rules from RFC 9110 and friends.

    Class attributes are re.Pattern objects, with the same name as in the RFC
    (with hyphens changed to underscores). Currently contains only the subset
    we use (which is why this class is not public). Unfortunately the fields
    cannot be alphabetized as they are in the RFCs because of dependencies.
    """

    # RFC 3986 (URI)
    # The URI hostname ABNF is both complex (including detailed vaildation of IPv4 and IPv6
    # literals) and not strict enough (a lot of punctuation is allowed by the ABNF even though
    # it is not allowed by DNS). We simplify it by allowing square brackets and colons in any
    # position, not only for their use in IPv6 literals.
    uri_unreserved = re.compile(r"[A-Za-z0-9\-._~]")
    uri_sub_delims = re.compile(r"[!$&'()*+,;=]")
    uri_pct_encoded = re.compile(r"%[0-9A-Fa-f]{2}")
    uri_host = re.compile(
        rf"(?:[\[\]:]|{uri_unreserved.pattern}|{uri_sub_delims.pattern}|{uri_pct_encoded.pattern})*"
    )
    uri_port = re.compile(r"[0-9]*")

    # RFC 5234 (ABNF)
    VCHAR = re.compile(r"[\x21-\x7E]")

    # RFC 9110 (HTTP Semantics)
    obs_text = re.compile(r"[\x80-\xFF]")
    field_vchar = re.compile(rf"(?:{VCHAR.pattern}|{obs_text.pattern})")
    # Not exactly from the RFC to simplify and combine field-content and field-value.
    field_value = re.compile(
        rf"|"
        rf"{field_vchar.pattern}|"
        rf"{field_vchar.pattern}(?:{field_vchar.pattern}| |\t)*{field_vchar.pattern}"
    )
    tchar = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]")
    token = re.compile(rf"{tchar.pattern}+")
    field_name = token
    method = token
    host = re.compile(rf"(?:{uri_host.pattern})(?::{uri_port.pattern})?")

    # RFC 9112 (HTTP/1.1)
    HTTP_version = re.compile(r"HTTP/[0-9]\.[0-9]")
    reason_phrase = re.compile(rf"(?:[\t ]|{VCHAR.pattern}|{obs_text.pattern})+")
    # request_target delegates to the URI RFC 3986, which is complex and may be
    # too restrictive (for example, the WHATWG version of the URL spec allows non-ASCII
    # characters). Instead, we allow everything but control chars and whitespace.
    request_target = re.compile(rf"{field_vchar.pattern}+")
    request_line = re.compile(
        rf"({method.pattern}) ({request_target.pattern}) ({HTTP_version.pattern})"
    )
    status_code = re.compile(r"[0-9]{3}")
    status_line = re.compile(
        rf"({HTTP_version.pattern}) ({status_code.pattern}) ({reason_phrase.pattern})?"
    )


@lru_cache(1000)
def _normalize_header(name: str) -> str:
    """Map a header name to Http-Header-Case.

    >>> _normalize_header("coNtent-TYPE")
    'Content-Type'
    """
    return "-".join([w.capitalize() for w in name.split("-")])


class HTTPHeaders(StrMutableMapping):
    """A dictionary that maintains ``Http-Header-Case`` for all keys.

    Supports multiple values per key via a pair of new methods,
    `add()` and `get_list()`.  The regular dictionary interface
    returns a single value per key, with multiple values joined by a
    comma.

    >>> h = HTTPHeaders({"content-type": "text/html"})
    >>> list(h.keys())
    ['Content-Type']
    >>> h["Content-Type"]
    'text/html'

    >>> h.add("Set-Cookie", "A=B")
    >>> h.add("Set-Cookie", "C=D")
    >>> h["set-cookie"]
    'A=B,C=D'
    >>> h.get_list("set-cookie")
    ['A=B', 'C=D']

    >>> for (k,v) in sorted(h.get_all()):
    ...    print('%s: %s' % (k,v))
    ...
    Content-Type: text/html
    Set-Cookie: A=B
    Set-Cookie: C=D
    """

    @typing.overload
    def __init__(self, __arg: Mapping[str, List[str]]) -> None:
        pass

    @typing.overload  # noqa: F811
    def __init__(self, __arg: Mapping[str, str]) -> None:
        pass

    @typing.overload  # noqa: F811
    def __init__(self, *args: Tuple[str, str]) -> None:
        pass

    @typing.overload  # noqa: F811
    def __init__(self, **kwargs: str) -> None:
        pass

    def __init__(self, *args: typing.Any, **kwargs: str) -> None:  # noqa: F811
        self._dict = {}  # type: typing.Dict[str, str]
        self._as_list = {}  # type: typing.Dict[str, typing.List[str]]
        self._last_key = None  # type: Optional[str]
        if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], HTTPHeaders):
            # Copy constructor
            for k, v in args[0].get_all():
                self.add(k, v)
        else:
            # Dict-style initialization
            self.update(*args, **kwargs)

    # new public methods

    def add(self, name: str, value: str, *, _chars_are_bytes: bool = True) -> None:
        """Adds a new value for the given key."""
        if not _ABNF.field_name.fullmatch(name):
            raise HTTPInputError("Invalid header name %r" % name)
        if _chars_are_bytes:
            if not _ABNF.field_value.fullmatch(to_unicode(value)):
                # TODO: the fact we still support bytes here (contrary to type annotations)
                # and still test for it should probably be changed.
                raise HTTPInputError("Invalid header value %r" % value)
        else:
            if _FORBIDDEN_HEADER_CHARS_RE.search(value):
                raise HTTPInputError("Invalid header value %r" % value)
        norm_name = _normalize_header(name)
        self._last_key = norm_name
        if norm_name in self:
            self._dict[norm_name] = (
                native_str(self[norm_name]) + "," + native_str(value)
            )
            self._as_list[norm_name].append(value)
        else:
            self[norm_name] = value

    def get_list(self, name: str) -> List[str]:
        """Returns all values for the given header as a list."""
        norm_name = _normalize_header(name)
        return self._as_list.get(norm_name, [])

    def get_all(self) -> Iterable[Tuple[str, str]]:
        """Returns an iterable of all (name, value) pairs.

        If a header has multiple values, multiple pairs will be
        returned with the same name.
        """
        for name, values in self._as_list.items():
            for value in values:
                yield (name, value)

    def parse_line(self, line: str, *, _chars_are_bytes: bool = True) -> None:
        r"""Updates the dictionary with a single header line.

        >>> h = HTTPHeaders()
        >>> h.parse_line("Content-Type: text/html")
        >>> h.get('content-type')
        'text/html'
        >>> h.parse_line("Content-Length: 42\r\n")
        >>> h.get('content-type')
        'text/html'

        .. versionchanged:: 6.5
            Now supports lines with or without the trailing CRLF, making it possible
            to pass lines from AsyncHTTPClient's header_callback directly to this method.

        .. deprecated:: 6.5
           In Tornado 7.0, certain deprecated features of HTTP will become errors.
           Specifically, line folding and the use of LF (with CR) as a line separator
           will be removed.
        """
        if m := re.search(r"\r?\n$", line):
            # RFC 9112 section 2.2: a recipient MAY recognize a single LF as a line
            # terminator and ignore any preceding CR.
            # TODO(7.0): Remove this support for LF-only line endings.
            line = line[: m.start()]
        if not line:
            # Empty line, or the final CRLF of a header block.
            return
        if line[0] in HTTP_WHITESPACE:
            # continuation of a multi-line header
            # TODO(7.0): Remove support for line folding.
            if self._last_key is None:
                raise HTTPInputError("first header line cannot start with whitespace")
            new_part = " " + line.strip(HTTP_WHITESPACE)
            if _chars_are_bytes:
                if not _ABNF.field_value.fullmatch(new_part[1:]):
                    raise HTTPInputError("Invalid header continuation %r" % new_part)
            else:
                if _FORBIDDEN_HEADER_CHARS_RE.search(new_part):
                    raise HTTPInputError("Invalid header value %r" % new_part)
            self._as_list[self._last_key][-1] += new_part
            self._dict[self._last_key] += new_part
        else:
            try:
                name, value = line.split(":", 1)
            except ValueError:
                raise HTTPInputError("no colon in header line")
            self.add(
                name, value.strip(HTTP_WHITESPACE), _chars_are_bytes=_chars_are_bytes
            )

    @classmethod
    def parse(cls, headers: str, *, _chars_are_bytes: bool = True) -> "HTTPHeaders":
        """Returns a dictionary from HTTP header text.

        >>> h = HTTPHeaders.parse("Content-Type: text/html\\r\\nContent-Length: 42\\r\\n")
        >>> sorted(h.items())
        [('Content-Length', '42'), ('Content-Type', 'text/html')]

        .. versionchanged:: 5.1

           Raises `HTTPInputError` on malformed headers instead of a
           mix of `KeyError`, and `ValueError`.

        """
        # _chars_are_bytes is a hack. This method is used in two places, HTTP headers (in which
        # non-ascii characters are to be interpreted as latin-1) and multipart/form-data (in which
        # they are to be interpreted as utf-8). For historical reasons, this method handled this by
        # expecting both callers to decode the headers to strings before parsing them. This wasn't a
        # problem until we started doing stricter validation of the characters allowed in HTTP
        # headers (using ABNF rules defined in terms of byte values), which inadvertently started
        # disallowing non-latin1 characters in multipart/form-data filenames.
        #
        # This method should have accepted bytes and a desired encoding, but this change is being
        # introduced in a patch release that shouldn't change the API. Instead, the _chars_are_bytes
        # flag decides whether to use HTTP-style ABNF validation (treating the string as bytes
        # smuggled through the latin1 encoding) or to accept any non-control unicode characters
        # as required by multipart/form-data. This method will change to accept bytes in a future
        # release.
        h = cls()

        start = 0
        while True:
            lf = headers.find("\n", start)
            if lf == -1:
                h.parse_line(headers[start:], _chars_are_bytes=_chars_are_bytes)
                break
            line = headers[start : lf + 1]
            start = lf + 1
            h.parse_line(line, _chars_are_bytes=_chars_are_bytes)
        return h

    # MutableMapping abstract method implementations.

    def __setitem__(self, name: str, value: str) -> None:
        norm_name = _normalize_header(name)
        self._dict[norm_name] = value
        self._as_list[norm_name] = [value]

    def __getitem__(self, name: str) -> str:
        return self._dict[_normalize_header(name)]

    def __delitem__(self, name: str) -> None:
        norm_name = _normalize_header(name)
        del self._dict[norm_name]
        del self._as_list[norm_name]

    def __len__(self) -> int:
        return len(self._dict)

    def __iter__(self) -> Iterator[typing.Any]:
        return iter(self._dict)

    def copy(self) -> "HTTPHeaders":
        # defined in dict but not in MutableMapping.
        return HTTPHeaders(self)

    # Use our overridden copy method for the copy.copy module.
    # This makes shallow copies one level deeper, but preserves
    # the appearance that HTTPHeaders is a single container.
    __copy__ = copy

    def __str__(self) -> str:
        lines = []
        for name, value in self.get_all():
            lines.append(f"{name}: {value}\n")
        return "".join(lines)

    __unicode__ = __str__


class HTTPServerRequest:
    """A single HTTP request.

    All attributes are type `str` unless otherwise noted.

    .. attribute:: method

       HTTP request method, e.g. "GET" or "POST"

    .. attribute:: uri

       The requested uri.

    .. attribute:: path

       The path portion of `uri`

    .. attribute:: query

       The query portion of `uri`

    .. attribute:: version

       HTTP version specified in request, e.g. "HTTP/1.1"

    .. attribute:: headers

       `.HTTPHeaders` dictionary-like object for request headers.  Acts like
       a case-insensitive dictionary with additional methods for repeated
       headers.

    .. attribute:: body

       Request body, if present, as a byte string.

    .. attribute:: remote_ip

       Client's IP address as a string.  If ``HTTPServer.xheaders`` is set,
       will pass along the real IP address provided by a load balancer
       in the ``X-Real-Ip`` or ``X-Forwarded-For`` header.

    .. versionchanged:: 3.1
       The list format of ``X-Forwarded-For`` is now supported.

    .. attribute:: protocol

       The protocol used, either "http" or "https".  If ``HTTPServer.xheaders``
       is set, will pass along the protocol used by a load balancer if
       reported via an ``X-Scheme`` header.

    .. attribute:: host

       The requested hostname, usually taken from the ``Host`` header.

    .. attribute:: arguments

       GET/POST arguments are available in the arguments property, which
       maps arguments names to lists of values (to support multiple values
       for individual names). Names are of type `str`, while arguments
       are byte strings.  Note that this is different from
       `.RequestHandler.get_argument`, which returns argument values as
       unicode strings.

    .. attribute:: query_arguments

       Same format as ``arguments``, but contains only arguments extracted
       from the query string.

       .. versionadded:: 3.2

    .. attribute:: body_arguments

       Same format as ``arguments``, but contains only arguments extracted
       from the request body.

       .. versionadded:: 3.2

    .. attribute:: files

       File uploads are available in the files property, which maps file
       names to lists of `.HTTPFile`.

    .. attribute:: connection

       An HTTP request is attached to a single HTTP connection, which can
       be accessed through the "connection" attribute. Since connections
       are typically kept open in HTTP/1.1, multiple requests can be handled
       sequentially on a single connection.

    .. versionchanged:: 4.0
       Moved from ``tornado.httpserver.HTTPRequest``.
    """

    path = None  # type: str
    query = None  # type: str

    # HACK: Used for stream_request_body
    _body_future = None  # type: Future[None]

    def __init__(
        self,
        method: Optional[str] = None,
        uri: Optional[str] = None,
        version: str = "HTTP/1.0",
        headers: Optional[HTTPHeaders] = None,
        body: Optional[bytes] = None,
        # host: Optional[str] = None,
        files: Optional[Dict[str, List["HTTPFile"]]] = None,
        connection: Optional["HTTPConnection"] = None,
        start_line: Optional["RequestStartLine"] = None,
        server_connection: Optional[object] = None,
    ) -> None:
        if start_line is not None:
            method, uri, version = start_line
        self.method = method
        self.uri = uri
        self.version = version
        self.headers = headers or HTTPHeaders()
        self.body = body or b""

        # set remote IP and protocol
        context = getattr(connection, "context", None)
        self.remote_ip = getattr(context, "remote_ip", None)
        self.protocol = getattr(context, "protocol", "http")

        try:
            self.host = self.headers["Host"]
        except KeyError:
            if version == "HTTP/1.0":
                # HTTP/1.0 does not require the Host header.
                self.host = "127.0.0.1"
            else:
                raise HTTPInputError("Missing Host header")
        if not _ABNF.host.fullmatch(self.host):
            print(_ABNF.host.pattern)
            raise HTTPInputError("Invalid Host header: %r" % self.host)
        if "," in self.host:
            # https://www.rfc-editor.org/rfc/rfc9112.html#name-request-target
            # Server MUST respond with 400 Bad Request if multiple
            # Host headers are present.
            #
            # We test for the presence of a comma instead of the number of
            # headers received because a proxy may have converted
            # multiple headers into a single comma-separated value
            # (per RFC 9110 section 5.3).
            #
            # This is technically a departure from the RFC since the ABNF
            # does not forbid commas in the host header. However, since
            # commas are not allowed in DNS names, it is appropriate to
            # disallow them. (The same argument could be made for other special
            # characters, but commas are the most problematic since they could
            # be used to exploit differences between proxies when multiple headers
            # are supplied).
            raise HTTPInputError("Multiple host headers not allowed: %r" % self.host)
        self.host_name = split_host_and_port(self.host.lower())[0]
        self.files = files or {}
        self.connection = connection
        self.server_connection = server_connection
        self._start_time = time.time()
        self._finish_time = None

        if uri is not None:
            self.path, sep, self.query = uri.partition("?")
        self.arguments = parse_qs_bytes(self.query, keep_blank_values=True)
        self.query_arguments = copy.deepcopy(self.arguments)
        self.body_arguments = {}  # type: Dict[str, List[bytes]]

    @property
    def cookies(self) -> Dict[str, http.cookies.Morsel]:
        """A dictionary of ``http.cookies.Morsel`` objects."""
        if not hasattr(self, "_cookies"):
            self._cookies = (
                http.cookies.SimpleCookie()
            )  # type: http.cookies.SimpleCookie
            if "Cookie" in self.headers:
                try:
                    parsed = parse_cookie(self.headers["Cookie"])
                except Exception:
                    pass
                else:
                    for k, v in parsed.items():
                        try:
                            self._cookies[k] = v
                        except Exception:
                            # SimpleCookie imposes some restrictions on keys;
                            # parse_cookie does not. Discard any cookies
                            # with disallowed keys.
                            pass
        return self._cookies

    def full_url(self) -> str:
        """Reconstructs the full URL for this request."""
        return self.protocol + "://" + self.host + self.uri  # type: ignore[operator]

    def request_time(self) -> float:
        """Returns the amount of time it took for this request to execute."""
        if self._finish_time is None:
            return time.time() - self._start_time
        else:
            return self._finish_time - self._start_time

    def get_ssl_certificate(
        self, binary_form: bool = False
    ) -> Union[None, Dict, bytes]:
        """Returns the client's SSL certificate, if any.

        To use client certificates, the HTTPServer's
        `ssl.SSLContext.verify_mode` field must be set, e.g.::

            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain("foo.crt", "foo.key")
            ssl_ctx.load_verify_locations("cacerts.pem")
            ssl_ctx.verify_mode = ssl.CERT_REQUIRED
            server = HTTPServer(app, ssl_options=ssl_ctx)

        By default, the return value is a dictionary (or None, if no
        client certificate is present).  If ``binary_form`` is true, a
        DER-encoded form of the certificate is returned instead.  See
        SSLSocket.getpeercert() in the standard library for more
        details.
        http://docs.python.org/library/ssl.html#sslsocket-objects
        """
        try:
            if self.connection is None:
                return None
            # TODO: add a method to HTTPConnection for this so it can work with HTTP/2
            return self.connection.stream.socket.getpeercert(  # type: ignore
                binary_form=binary_form
            )
        except SSLError:
            return None

    def _parse_body(self) -> None:
        parse_body_arguments(
            self.headers.get("Content-Type", ""),
            self.body,
            self.body_arguments,
            self.files,
            self.headers,
        )

        for k, v in self.body_arguments.items():
            self.arguments.setdefault(k, []).extend(v)

    def __repr__(self) -> str:
        attrs = ("protocol", "host", "method", "uri", "version", "remote_ip")
        args = ", ".join([f"{n}={getattr(self, n)!r}" for n in attrs])
        return f"{self.__class__.__name__}({args})"


class HTTPInputError(Exception):
    """Exception class for malformed HTTP requests or responses
    from remote sources.

    .. versionadded:: 4.0
    """

    pass


class HTTPOutputError(Exception):
    """Exception class for errors in HTTP output.

    .. versionadded:: 4.0
    """

    pass


class HTTPServerConnectionDelegate:
    """Implement this interface to handle requests from `.HTTPServer`.

    .. versionadded:: 4.0
    """

    def start_request(
        self, server_conn: object, request_conn: "HTTPConnection"
    ) -> "HTTPMessageDelegate":
        """This method is called by the server when a new request has started.

        :arg server_conn: is an opaque object representing the long-lived
            (e.g. tcp-level) connection.
        :arg request_conn: is a `.HTTPConnection` object for a single
            request/response exchange.

        This method should return a `.HTTPMessageDelegate`.
        """
        raise NotImplementedError()

    def on_close(self, server_conn: object) -> None:
        """This method is called when a connection has been closed.

        :arg server_conn: is a server connection that has previously been
            passed to ``start_request``.
        """
        pass


class HTTPMessageDelegate:
    """Implement this interface to handle an HTTP request or response.

    .. versionadded:: 4.0
    """

    # TODO: genericize this class to avoid exposing the Union.
    def headers_received(
        self,
        start_line: Union["RequestStartLine", "ResponseStartLine"],
        headers: HTTPHeaders,
    ) -> Optional[Awaitable[None]]:
        """Called when the HTTP headers have been received and parsed.

        :arg start_line: a `.RequestStartLine` or `.ResponseStartLine`
            depending on whether this is a client or server message.
        :arg headers: a `.HTTPHeaders` instance.

        Some `.HTTPConnection` methods can only be called during
        ``headers_received``.

        May return a `.Future`; if it does the body will not be read
        until it is done.
        """
        pass

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        """Called when a chunk of data has been received.

        May return a `.Future` for flow control.
        """
        pass

    def finish(self) -> None:
        """Called after the last chunk of data has been received."""
        pass

    def on_connection_close(self) -> None:
        """Called if the connection is closed without finishing the request.

        If ``headers_received`` is called, either ``finish`` or
        ``on_connection_close`` will be called, but not both.
        """
        pass


class HTTPConnection:
    """Applications use this interface to write their responses.

    .. versionadded:: 4.0
    """

    def write_headers(
        self,
        start_line: Union["RequestStartLine", "ResponseStartLine"],
        headers: HTTPHeaders,
        chunk: Optional[bytes] = None,
    ) -> "Future[None]":
        """Write an HTTP header block.

        :arg start_line: a `.RequestStartLine` or `.ResponseStartLine`.
        :arg headers: a `.HTTPHeaders` instance.
        :arg chunk: the first (optional) chunk of data.  This is an optimization
            so that small responses can be written in the same call as their
            headers.

        The ``version`` field of ``start_line`` is ignored.

        Returns a future for flow control.

        .. versionchanged:: 6.0

           The ``callback`` argument was removed.
        """
        raise NotImplementedError()

    def write(self, chunk: bytes) -> "Future[None]":
        """Writes a chunk of body data.

        Returns a future for flow control.

        .. versionchanged:: 6.0

           The ``callback`` argument was removed.
        """
        raise NotImplementedError()

    def finish(self) -> None:
        """Indicates that the last body data has been written."""
        raise NotImplementedError()


def url_concat(
    url: str,
    args: Union[
        None, Dict[str, str], List[Tuple[str, str]], Tuple[Tuple[str, str], ...]
    ],
) -> str:
    """Concatenate url and arguments regardless of whether
    url has existing query parameters.

    ``args`` may be either a dictionary or a list of key-value pairs
    (the latter allows for multiple values with the same key.

    >>> url_concat("http://example.com/foo", dict(c="d"))
    'http://example.com/foo?c=d'
    >>> url_concat("http://example.com/foo?a=b", dict(c="d"))
    'http://example.com/foo?a=b&c=d'
    >>> url_concat("http://example.com/foo?a=b", [("c", "d"), ("c", "d2")])
    'http://example.com/foo?a=b&c=d&c=d2'
    """
    if args is None:
        return url
    parsed_url = urlparse(url)
    if isinstance(args, dict):
        parsed_query = parse_qsl(parsed_url.query, keep_blank_values=True)
        parsed_query.extend(args.items())
    elif isinstance(args, list) or isinstance(args, tuple):
        parsed_query = parse_qsl(parsed_url.query, keep_blank_values=True)
        parsed_query.extend(args)
    else:
        err = "'args' parameter should be dict, list or tuple. Not {0}".format(
            type(args)
        )
        raise TypeError(err)
    final_query = urlencode(parsed_query)
    url = urlunparse(
        (
            parsed_url[0],
            parsed_url[1],
            parsed_url[2],
            parsed_url[3],
            final_query,
            parsed_url[5],
        )
    )
    return url


class HTTPFile(ObjectDict):
    """Represents a file uploaded via a form.

    For backwards compatibility, its instance attributes are also
    accessible as dictionary keys.

    * ``filename``
    * ``body``
    * ``content_type``
    """

    filename: str
    body: bytes
    content_type: str


def _parse_request_range(
    range_header: str,
) -> Optional[Tuple[Optional[int], Optional[int]]]:
    """Parses a Range header.

    Returns either ``None`` or tuple ``(start, end)``.
    Note that while the HTTP headers use inclusive byte positions,
    this method returns indexes suitable for use in slices.

    >>> start, end = _parse_request_range("bytes=1-2")
    >>> start, end
    (1, 3)
    >>> [0, 1, 2, 3, 4][start:end]
    [1, 2]
    >>> _parse_request_range("bytes=6-")
    (6, None)
    >>> _parse_request_range("bytes=-6")
    (-6, None)
    >>> _parse_request_range("bytes=-0")
    (None, 0)
    >>> _parse_request_range("bytes=")
    (None, None)
    >>> _parse_request_range("foo=42")
    >>> _parse_request_range("bytes=1-2,6-10")

    Note: only supports one range (ex, ``bytes=1-2,6-10`` is not allowed).

    See [0] for the details of the range header.

    [0]: http://greenbytes.de/tech/webdav/draft-ietf-httpbis-p5-range-latest.html#byte.ranges
    """
    unit, _, value = range_header.partition("=")
    unit, value = unit.strip(), value.strip()
    if unit != "bytes":
        return None
    start_b, _, end_b = value.partition("-")
    try:
        start = _int_or_none(start_b)
        end = _int_or_none(end_b)
    except ValueError:
        return None
    if end is not None:
        if start is None:
            if end != 0:
                start = -end
                end = None
        else:
            end += 1
    return (start, end)


def _get_content_range(start: Optional[int], end: Optional[int], total: int) -> str:
    """Returns a suitable Content-Range header:

    >>> print(_get_content_range(None, 1, 4))
    bytes 0-0/4
    >>> print(_get_content_range(1, 3, 4))
    bytes 1-2/4
    >>> print(_get_content_range(None, None, 4))
    bytes 0-3/4
    """
    start = start or 0
    end = (end or total) - 1
    return f"bytes {start}-{end}/{total}"


def _int_or_none(val: str) -> Optional[int]:
    val = val.strip()
    if val == "":
        return None
    return int(val)


def parse_body_arguments(
    content_type: str,
    body: bytes,
    arguments: Dict[str, List[bytes]],
    files: Dict[str, List[HTTPFile]],
    headers: Optional[HTTPHeaders] = None,
) -> None:
    """Parses a form request body.

    Supports ``application/x-www-form-urlencoded`` and
    ``multipart/form-data``.  The ``content_type`` parameter should be
    a string and ``body`` should be a byte string.  The ``arguments``
    and ``files`` parameters are dictionaries that will be updated
    with the parsed contents.
    """
    if content_type.startswith("application/x-www-form-urlencoded"):
        if headers and "Content-Encoding" in headers:
            raise HTTPInputError(
                "Unsupported Content-Encoding: %s" % headers["Content-Encoding"]
            )
        try:
            # real charset decoding will happen in RequestHandler.decode_argument()
            uri_arguments = parse_qs_bytes(body, keep_blank_values=True)
        except Exception as e:
            raise HTTPInputError("Invalid x-www-form-urlencoded body: %s" % e) from e
        for name, values in uri_arguments.items():
            if values:
                arguments.setdefault(name, []).extend(values)
    elif content_type.startswith("multipart/form-data"):
        if headers and "Content-Encoding" in headers:
            raise HTTPInputError(
                "Unsupported Content-Encoding: %s" % headers["Content-Encoding"]
            )
        try:
            fields = content_type.split(";")
            for field in fields:
                k, sep, v = field.strip().partition("=")
                if k == "boundary" and v:
                    parse_multipart_form_data(utf8(v), body, arguments, files)
                    break
            else:
                raise HTTPInputError("multipart boundary not found")
        except Exception as e:
            raise HTTPInputError("Invalid multipart/form-data: %s" % e) from e


def parse_multipart_form_data(
    boundary: bytes,
    data: bytes,
    arguments: Dict[str, List[bytes]],
    files: Dict[str, List[HTTPFile]],
) -> None:
    """Parses a ``multipart/form-data`` body.

    The ``boundary`` and ``data`` parameters are both byte strings.
    The dictionaries given in the arguments and files parameters
    will be updated with the contents of the body.

    .. versionchanged:: 5.1

       Now recognizes non-ASCII filenames in RFC 2231/5987
       (``filename*=``) format.
    """
    # The standard allows for the boundary to be quoted in the header,
    # although it's rare (it happens at least for google app engine
    # xmpp).  I think we're also supposed to handle backslash-escapes
    # here but I'll save that until we see a client that uses them
    # in the wild.
    if boundary.startswith(b'"') and boundary.endswith(b'"'):
        boundary = boundary[1:-1]
    final_boundary_index = data.rfind(b"--" + boundary + b"--")
    if final_boundary_index == -1:
        raise HTTPInputError("Invalid multipart/form-data: no final boundary found")
    parts = data[:final_boundary_index].split(b"--" + boundary + b"\r\n")
    for part in parts:
        if not part:
            continue
        eoh = part.find(b"\r\n\r\n")
        if eoh == -1:
            raise HTTPInputError("multipart/form-data missing headers")
        headers = HTTPHeaders.parse(part[:eoh].decode("utf-8"), _chars_are_bytes=False)
        disp_header = headers.get("Content-Disposition", "")
        disposition, disp_params = _parse_header(disp_header)
        if disposition != "form-data" or not part.endswith(b"\r\n"):
            raise HTTPInputError("Invalid multipart/form-data")
        value = part[eoh + 4 : -2]
        if not disp_params.get("name"):
            raise HTTPInputError("multipart/form-data missing name")
        name = disp_params["name"]
        if disp_params.get("filename"):
            ctype = headers.get("Content-Type", "application/unknown")
            files.setdefault(name, []).append(
                HTTPFile(
                    filename=disp_params["filename"], body=value, content_type=ctype
                )
            )
        else:
            arguments.setdefault(name, []).append(value)


def format_timestamp(
    ts: Union[int, float, tuple, time.struct_time, datetime.datetime],
) -> str:
    """Formats a timestamp in the format used by HTTP.

    The argument may be a numeric timestamp as returned by `time.time`,
    a time tuple as returned by `time.gmtime`, or a `datetime.datetime`
    object. Naive `datetime.datetime` objects are assumed to represent
    UTC; aware objects are converted to UTC before formatting.

    >>> format_timestamp(1359312200)
    'Sun, 27 Jan 2013 18:43:20 GMT'
    """
    if isinstance(ts, (int, float)):
        time_num = ts
    elif isinstance(ts, (tuple, time.struct_time)):
        time_num = calendar.timegm(ts)
    elif isinstance(ts, datetime.datetime):
        time_num = calendar.timegm(ts.utctimetuple())
    else:
        raise TypeError("unknown timestamp type: %r" % ts)
    return email.utils.formatdate(time_num, usegmt=True)


class RequestStartLine(typing.NamedTuple):
    method: str
    path: str
    version: str


def parse_request_start_line(line: str) -> RequestStartLine:
    """Returns a (method, path, version) tuple for an HTTP 1.x request line.

    The response is a `typing.NamedTuple`.

    >>> parse_request_start_line("GET /foo HTTP/1.1")
    RequestStartLine(method='GET', path='/foo', version='HTTP/1.1')
    """
    match = _ABNF.request_line.fullmatch(line)
    if not match:
        # https://tools.ietf.org/html/rfc7230#section-3.1.1
        # invalid request-line SHOULD respond with a 400 (Bad Request)
        raise HTTPInputError("Malformed HTTP request line")
    r = RequestStartLine(match.group(1), match.group(2), match.group(3))
    if not r.version.startswith("HTTP/1"):
        # HTTP/2 and above doesn't use parse_request_start_line.
        # This could be folded into the regex but we don't want to deviate
        # from the ABNF in the RFCs.
        raise HTTPInputError("Unexpected HTTP version %r" % r.version)
    return r


class ResponseStartLine(typing.NamedTuple):
    version: str
    code: int
    reason: str


def parse_response_start_line(line: str) -> ResponseStartLine:
    """Returns a (version, code, reason) tuple for an HTTP 1.x response line.

    The response is a `typing.NamedTuple`.

    >>> parse_response_start_line("HTTP/1.1 200 OK")
    ResponseStartLine(version='HTTP/1.1', code=200, reason='OK')
    """
    match = _ABNF.status_line.fullmatch(line)
    if not match:
        raise HTTPInputError("Error parsing response start line")
    r = ResponseStartLine(match.group(1), int(match.group(2)), match.group(3))
    if not r.version.startswith("HTTP/1"):
        # HTTP/2 and above doesn't use parse_response_start_line.
        raise HTTPInputError("Unexpected HTTP version %r" % r.version)
    return r


# _parseparam and _parse_header are copied and modified from python2.7's cgi.py
# The original 2.7 version of this code did not correctly support some
# combinations of semicolons and double quotes.
# It has also been modified to support valueless parameters as seen in
# websocket extension negotiations, and to support non-ascii values in
# RFC 2231/5987 format.


def _parseparam(s: str) -> Generator[str, None, None]:
    while s[:1] == ";":
        s = s[1:]
        end = s.find(";")
        while end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2:
            end = s.find(";", end + 1)
        if end < 0:
            end = len(s)
        f = s[:end]
        yield f.strip()
        s = s[end:]


def _parse_header(line: str) -> Tuple[str, Dict[str, str]]:
    r"""Parse a Content-type like header.

    Return the main content-type and a dictionary of options.

    >>> d = "form-data; foo=\"b\\\\a\\\"r\"; file*=utf-8''T%C3%A4st"
    >>> ct, d = _parse_header(d)
    >>> ct
    'form-data'
    >>> d['file'] == r'T\u00e4st'.encode('ascii').decode('unicode_escape')
    True
    >>> d['foo']
    'b\\a"r'
    """
    parts = _parseparam(";" + line)
    key = next(parts)
    # decode_params treats first argument special, but we already stripped key
    params = [("Dummy", "value")]
    for p in parts:
        i = p.find("=")
        if i >= 0:
            name = p[:i].strip().lower()
            value = p[i + 1 :].strip()
            params.append((name, native_str(value)))
    decoded_params = email.utils.decode_params(params)
    decoded_params.pop(0)  # get rid of the dummy again
    pdict = {}
    for name, decoded_value in decoded_params:
        value = email.utils.collapse_rfc2231_value(decoded_value)
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        pdict[name] = value
    return key, pdict


def _encode_header(key: str, pdict: Dict[str, str]) -> str:
    """Inverse of _parse_header.

    >>> _encode_header('permessage-deflate',
    ...     {'client_max_window_bits': 15, 'client_no_context_takeover': None})
    'permessage-deflate; client_max_window_bits=15; client_no_context_takeover'
    """
    if not pdict:
        return key
    out = [key]
    # Sort the parameters just to make it easy to test.
    for k, v in sorted(pdict.items()):
        if v is None:
            out.append(k)
        else:
            # TODO: quote if necessary.
            out.append(f"{k}={v}")
    return "; ".join(out)


def encode_username_password(
    username: Union[str, bytes], password: Union[str, bytes]
) -> bytes:
    """Encodes a username/password pair in the format used by HTTP auth.

    The return value is a byte string in the form ``username:password``.

    .. versionadded:: 5.1
    """
    if isinstance(username, unicode_type):
        username = unicodedata.normalize("NFC", username)
    if isinstance(password, unicode_type):
        password = unicodedata.normalize("NFC", password)
    return utf8(username) + b":" + utf8(password)


def doctests():
    # type: () -> unittest.TestSuite
    import doctest

    return doctest.DocTestSuite()


_netloc_re = re.compile(r"^(.+):(\d+)$")


def split_host_and_port(netloc: str) -> Tuple[str, Optional[int]]:
    """Returns ``(host, port)`` tuple from ``netloc``.

    Returned ``port`` will be ``None`` if not present.

    .. versionadded:: 4.1
    """
    match = _netloc_re.match(netloc)
    if match:
        host = match.group(1)
        port = int(match.group(2))  # type: Optional[int]
    else:
        host = netloc
        port = None
    return (host, port)


def qs_to_qsl(qs: Dict[str, List[AnyStr]]) -> Iterable[Tuple[str, AnyStr]]:
    """Generator converting a result of ``parse_qs`` back to name-value pairs.

    .. versionadded:: 5.0
    """
    for k, vs in qs.items():
        for v in vs:
            yield (k, v)


_unquote_sub = re.compile(r"\\(?:([0-3][0-7][0-7])|(.))").sub


def _unquote_replace(m: re.Match) -> str:
    if m[1]:
        return chr(int(m[1], 8))
    else:
        return m[2]


def _unquote_cookie(s: str) -> str:
    """Handle double quotes and escaping in cookie values.

    This method is copied verbatim from the Python 3.13 standard
    library (http.cookies._unquote) so we don't have to depend on
    non-public interfaces.
    """
    # If there aren't any doublequotes,
    # then there can't be any special characters.  See RFC 2109.
    if s is None or len(s) < 2:
        return s
    if s[0] != '"' or s[-1] != '"':
        return s

    # We have to assume that we must decode this string.
    # Down to work.

    # Remove the "s
    s = s[1:-1]

    # Check for special sequences.  Examples:
    #    \012 --> \n
    #    \"   --> "
    #
    return _unquote_sub(_unquote_replace, s)


def parse_cookie(cookie: str) -> Dict[str, str]:
    """Parse a ``Cookie`` HTTP header into a dict of name/value pairs.

    This function attempts to mimic browser cookie parsing behavior;
    it specifically does not follow any of the cookie-related RFCs
    (because browsers don't either).

    The algorithm used is identical to that used by Django version 1.9.10.

    .. versionadded:: 4.4.2
    """
    cookiedict = {}
    for chunk in cookie.split(";"):
        if "=" in chunk:
            key, val = chunk.split("=", 1)
        else:
            # Assume an empty name per
            # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
            key, val = "", chunk
        key, val = key.strip(), val.strip()
        if key or val:
            # unquote using Python's algorithm.
            cookiedict[key] = _unquote_cookie(val)
    return cookiedict