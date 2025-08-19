
# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_network.py ===
# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import base64
import inspect
import json
import json as json_utils
import mimetypes
import re
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    TypedDict,
    Union,
    cast,
)
from urllib import parse

from playwright._impl._api_structures import (
    ClientCertificate,
    Headers,
    HeadersArray,
    RemoteAddr,
    RequestSizes,
    ResourceTiming,
    SecurityDetails,
)
from playwright._impl._connection import (
    ChannelOwner,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._errors import Error
from playwright._impl._event_context_manager import EventContextManagerImpl
from playwright._impl._helper import (
    URLMatch,
    WebSocketRouteHandlerCallback,
    async_readfile,
    locals_to_params,
    url_matches,
)
from playwright._impl._str_utils import escape_regex_flags
from playwright._impl._waiter import Waiter

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._browser_context import BrowserContext
    from playwright._impl._fetch import APIResponse
    from playwright._impl._frame import Frame
    from playwright._impl._page import Page


class FallbackOverrideParameters(TypedDict, total=False):
    url: Optional[str]
    method: Optional[str]
    headers: Optional[Dict[str, str]]
    postData: Optional[Union[str, bytes]]


class SerializedFallbackOverrides:
    def __init__(self) -> None:
        self.url: Optional[str] = None
        self.method: Optional[str] = None
        self.headers: Optional[Dict[str, str]] = None
        self.post_data_buffer: Optional[bytes] = None


def serialize_headers(headers: Dict[str, str]) -> HeadersArray:
    return [
        {"name": name, "value": value}
        for name, value in headers.items()
        if value is not None
    ]


async def to_client_certificates_protocol(
    clientCertificates: Optional[List[ClientCertificate]],
) -> Optional[List[Dict[str, str]]]:
    if not clientCertificates:
        return None
    out = []
    for clientCertificate in clientCertificates:
        out_record = {
            "origin": clientCertificate["origin"],
        }
        if passphrase := clientCertificate.get("passphrase"):
            out_record["passphrase"] = passphrase
        if pfx := clientCertificate.get("pfx"):
            out_record["pfx"] = base64.b64encode(pfx).decode()
        if pfx_path := clientCertificate.get("pfxPath"):
            out_record["pfx"] = base64.b64encode(
                await async_readfile(pfx_path)
            ).decode()
        if cert := clientCertificate.get("cert"):
            out_record["cert"] = base64.b64encode(cert).decode()
        if cert_path := clientCertificate.get("certPath"):
            out_record["cert"] = base64.b64encode(
                await async_readfile(cert_path)
            ).decode()
        if key := clientCertificate.get("key"):
            out_record["key"] = base64.b64encode(key).decode()
        if key_path := clientCertificate.get("keyPath"):
            out_record["key"] = base64.b64encode(
                await async_readfile(key_path)
            ).decode()
        out.append(out_record)
    return out


class Request(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._channel.mark_as_internal_type()
        self._redirected_from: Optional["Request"] = from_nullable_channel(
            initializer.get("redirectedFrom")
        )
        self._redirected_to: Optional["Request"] = None
        if self._redirected_from:
            self._redirected_from._redirected_to = self
        self._failure_text: Optional[str] = None
        self._timing: ResourceTiming = {
            "startTime": 0,
            "domainLookupStart": -1,
            "domainLookupEnd": -1,
            "connectStart": -1,
            "secureConnectionStart": -1,
            "connectEnd": -1,
            "requestStart": -1,
            "responseStart": -1,
            "responseEnd": -1,
        }
        self._provisional_headers = RawHeaders(self._initializer["headers"])
        self._all_headers_future: Optional[asyncio.Future[RawHeaders]] = None
        self._fallback_overrides: SerializedFallbackOverrides = (
            SerializedFallbackOverrides()
        )

    def __repr__(self) -> str:
        return f"<Request url={self.url!r} method={self.method!r}>"

    def _apply_fallback_overrides(self, overrides: FallbackOverrideParameters) -> None:
        self._fallback_overrides.url = overrides.get(
            "url", self._fallback_overrides.url
        )
        self._fallback_overrides.method = overrides.get(
            "method", self._fallback_overrides.method
        )
        self._fallback_overrides.headers = overrides.get(
            "headers", self._fallback_overrides.headers
        )
        post_data = overrides.get("postData")
        if isinstance(post_data, str):
            self._fallback_overrides.post_data_buffer = post_data.encode()
        elif isinstance(post_data, bytes):
            self._fallback_overrides.post_data_buffer = post_data
        elif post_data is not None:
            self._fallback_overrides.post_data_buffer = json.dumps(post_data).encode()

    @property
    def url(self) -> str:
        return cast(str, self._fallback_overrides.url or self._initializer["url"])

    @property
    def resource_type(self) -> str:
        return self._initializer["resourceType"]

    @property
    def method(self) -> str:
        return cast(str, self._fallback_overrides.method or self._initializer["method"])

    async def sizes(self) -> RequestSizes:
        response = await self.response()
        if not response:
            raise Error("Unable to fetch sizes for failed request")
        return await response._channel.send("sizes")

    @property
    def post_data(self) -> Optional[str]:
        data = self._fallback_overrides.post_data_buffer
        if data:
            return data.decode()
        base64_post_data = self._initializer.get("postData")
        if base64_post_data is not None:
            return base64.b64decode(base64_post_data).decode()
        return None

    @property
    def post_data_json(self) -> Optional[Any]:
        post_data = self.post_data
        if not post_data:
            return None
        content_type = self.headers["content-type"]
        if "application/x-www-form-urlencoded" in content_type:
            return dict(parse.parse_qsl(post_data))
        try:
            return json.loads(post_data)
        except Exception:
            raise Error(f"POST data is not a valid JSON object: {post_data}")

    @property
    def post_data_buffer(self) -> Optional[bytes]:
        if self._fallback_overrides.post_data_buffer:
            return self._fallback_overrides.post_data_buffer
        if self._initializer.get("postData"):
            return base64.b64decode(self._initializer["postData"])
        return None

    async def response(self) -> Optional["Response"]:
        return from_nullable_channel(await self._channel.send("response"))

    @property
    def frame(self) -> "Frame":
        if not self._initializer.get("frame"):
            raise Error("Service Worker requests do not have an associated frame.")
        frame = cast("Frame", from_channel(self._initializer["frame"]))
        if not frame._page:
            raise Error(
                "\n".join(
                    [
                        "Frame for this navigation request is not available, because the request",
                        "was issued before the frame is created. You can check whether the request",
                        "is a navigation request by calling isNavigationRequest() method.",
                    ]
                )
            )
        return frame

    def is_navigation_request(self) -> bool:
        return self._initializer["isNavigationRequest"]

    @property
    def redirected_from(self) -> Optional["Request"]:
        return self._redirected_from

    @property
    def redirected_to(self) -> Optional["Request"]:
        return self._redirected_to

    @property
    def failure(self) -> Optional[str]:
        return self._failure_text

    @property
    def timing(self) -> ResourceTiming:
        return self._timing

    def _set_response_end_timing(self, response_end_timing: float) -> None:
        self._timing["responseEnd"] = response_end_timing
        if self._timing["responseStart"] == -1:
            self._timing["responseStart"] = response_end_timing

    @property
    def headers(self) -> Headers:
        override = self._fallback_overrides.headers
        if override:
            return RawHeaders._from_headers_dict_lossy(override).headers()
        return self._provisional_headers.headers()

    async def all_headers(self) -> Headers:
        return (await self._actual_headers()).headers()

    async def headers_array(self) -> HeadersArray:
        return (await self._actual_headers()).headers_array()

    async def header_value(self, name: str) -> Optional[str]:
        return (await self._actual_headers()).get(name)

    async def _actual_headers(self) -> "RawHeaders":
        override = self._fallback_overrides.headers
        if override:
            return RawHeaders(serialize_headers(override))
        if not self._all_headers_future:
            self._all_headers_future = asyncio.Future()
            headers = await self._channel.send("rawRequestHeaders")
            self._all_headers_future.set_result(RawHeaders(headers))
        return await self._all_headers_future

    def _target_closed_future(self) -> asyncio.Future:
        frame = cast(
            Optional["Frame"], from_nullable_channel(self._initializer.get("frame"))
        )
        if not frame:
            return asyncio.Future()
        page = frame._page
        if not page:
            return asyncio.Future()
        return page._closed_or_crashed_future

    def _safe_page(self) -> "Optional[Page]":
        frame = from_nullable_channel(self._initializer.get("frame"))
        if not frame:
            return None
        return cast("Frame", frame)._page


class Route(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._channel.mark_as_internal_type()
        self._handling_future: Optional[asyncio.Future["bool"]] = None
        self._context: "BrowserContext" = cast("BrowserContext", None)
        self._did_throw = False

    def _start_handling(self) -> "asyncio.Future[bool]":
        self._handling_future = asyncio.Future()
        return self._handling_future

    def _report_handled(self, done: bool) -> None:
        chain = self._handling_future
        assert chain
        self._handling_future = None
        chain.set_result(done)

    def _check_not_handled(self) -> None:
        if not self._handling_future:
            raise Error("Route is already handled!")

    def __repr__(self) -> str:
        return f"<Route request={self.request}>"

    @property
    def request(self) -> Request:
        return from_channel(self._initializer["request"])

    async def abort(self, errorCode: str = None) -> None:
        await self._handle_route(
            lambda: self._race_with_page_close(
                self._channel.send(
                    "abort",
                    {
                        "errorCode": errorCode,
                    },
                )
            )
        )

    async def fulfill(
        self,
        status: int = None,
        headers: Dict[str, str] = None,
        body: Union[str, bytes] = None,
        json: Any = None,
        path: Union[str, Path] = None,
        contentType: str = None,
        response: "APIResponse" = None,
    ) -> None:
        await self._handle_route(
            lambda: self._inner_fulfill(
                status, headers, body, json, path, contentType, response
            )
        )

    async def _inner_fulfill(
        self,
        status: int = None,
        headers: Dict[str, str] = None,
        body: Union[str, bytes] = None,
        json: Any = None,
        path: Union[str, Path] = None,
        contentType: str = None,
        response: "APIResponse" = None,
    ) -> None:
        params = locals_to_params(locals())

        if json is not None:
            if body is not None:
                raise Error("Can specify either body or json parameters")
            body = json_utils.dumps(json)

        if response:
            del params["response"]
            params["status"] = (
                params["status"] if params.get("status") else response.status
            )
            params["headers"] = (
                params["headers"] if params.get("headers") else response.headers
            )
            from playwright._impl._fetch import APIResponse

            if body is None and path is None and isinstance(response, APIResponse):
                if response._request._connection is self._connection:
                    params["fetchResponseUid"] = response._fetch_uid
                else:
                    body = await response.body()

        length = 0
        if isinstance(body, str):
            params["body"] = body
            params["isBase64"] = False
            length = len(body.encode())
        elif isinstance(body, bytes):
            params["body"] = base64.b64encode(body).decode()
            params["isBase64"] = True
            length = len(body)
        elif path:
            del params["path"]
            file_content = Path(path).read_bytes()
            params["body"] = base64.b64encode(file_content).decode()
            params["isBase64"] = True
            length = len(file_content)

        headers = {k.lower(): str(v) for k, v in params.get("headers", {}).items()}
        if params.get("contentType"):
            headers["content-type"] = params["contentType"]
        elif json:
            headers["content-type"] = "application/json"
        elif path:
            headers["content-type"] = (
                mimetypes.guess_type(str(Path(path)))[0] or "application/octet-stream"
            )
        if length and "content-length" not in headers:
            headers["content-length"] = str(length)
        params["headers"] = serialize_headers(headers)

        await self._race_with_page_close(self._channel.send("fulfill", params))

    async def _handle_route(self, callback: Callable) -> None:
        self._check_not_handled()
        try:
            await callback()
            self._report_handled(True)
        except Exception as e:
            self._did_throw = True
            raise e

    async def fetch(
        self,
        url: str = None,
        method: str = None,
        headers: Dict[str, str] = None,
        postData: Union[Any, str, bytes] = None,
        maxRedirects: int = None,
        maxRetries: int = None,
        timeout: float = None,
    ) -> "APIResponse":
        return await self._connection.wrap_api_call(
            lambda: self._context.request._inner_fetch(
                self.request,
                url,
                method,
                headers,
                postData,
                maxRedirects=maxRedirects,
                maxRetries=maxRetries,
                timeout=timeout,
            )
        )

    async def fallback(
        self,
        url: str = None,
        method: str = None,
        headers: Dict[str, str] = None,
        postData: Union[Any, str, bytes] = None,
    ) -> None:
        overrides = cast(FallbackOverrideParameters, locals_to_params(locals()))
        self._check_not_handled()
        self.request._apply_fallback_overrides(overrides)
        self._report_handled(False)

    async def continue_(
        self,
        url: str = None,
        method: str = None,
        headers: Dict[str, str] = None,
        postData: Union[Any, str, bytes] = None,
    ) -> None:
        overrides = cast(FallbackOverrideParameters, locals_to_params(locals()))

        async def _inner() -> None:
            self.request._apply_fallback_overrides(overrides)
            await self._inner_continue(False)

        return await self._handle_route(_inner)

    async def _inner_continue(self, is_fallback: bool = False) -> None:
        options = self.request._fallback_overrides
        await self._race_with_page_close(
            self._channel.send(
                "continue",
                {
                    "url": options.url,
                    "method": options.method,
                    "headers": (
                        serialize_headers(options.headers) if options.headers else None
                    ),
                    "postData": (
                        base64.b64encode(options.post_data_buffer).decode()
                        if options.post_data_buffer is not None
                        else None
                    ),
                    "isFallback": is_fallback,
                },
            )
        )

    async def _redirected_navigation_request(self, url: str) -> None:
        await self._handle_route(
            lambda: self._race_with_page_close(
                self._channel.send("redirectNavigationRequest", {"url": url})
            )
        )

    async def _race_with_page_close(self, future: Coroutine) -> None:
        fut = asyncio.create_task(future)
        # Rewrite the user's stack to the new task which runs in the background.
        setattr(
            fut,
            "__pw_stack__",
            getattr(asyncio.current_task(self._loop), "__pw_stack__", inspect.stack()),
        )
        target_closed_future = self.request._target_closed_future()
        await asyncio.wait(
            [fut, target_closed_future],
            return_when=asyncio.FIRST_COMPLETED,
        )
        if fut.done() and fut.exception():
            raise cast(BaseException, fut.exception())
        if target_closed_future.done():
            await asyncio.gather(fut, return_exceptions=True)


def _create_task_and_ignore_exception(
    loop: asyncio.AbstractEventLoop, coro: Coroutine
) -> None:
    async def _ignore_exception() -> None:
        try:
            await coro
        except Exception:
            pass

    loop.create_task(_ignore_exception())


class ServerWebSocketRoute:
    def __init__(self, ws: "WebSocketRoute"):
        self._ws = ws

    def on_message(self, handler: Callable[[Union[str, bytes]], Any]) -> None:
        self._ws._on_server_message = handler

    def on_close(self, handler: Callable[[Optional[int], Optional[str]], Any]) -> None:
        self._ws._on_server_close = handler

    def connect_to_server(self) -> None:
        raise NotImplementedError(
            "connectToServer must be called on the page-side WebSocketRoute"
        )

    @property
    def url(self) -> str:
        return self._ws._initializer["url"]

    def close(self, code: int = None, reason: str = None) -> None:
        _create_task_and_ignore_exception(
            self._ws._loop,
            self._ws._channel.send(
                "closeServer",
                {
                    "code": code,
                    "reason": reason,
                    "wasClean": True,
                },
            ),
        )

    def send(self, message: Union[str, bytes]) -> None:
        if isinstance(message, str):
            _create_task_and_ignore_exception(
                self._ws._loop,
                self._ws._channel.send(
                    "sendToServer", {"message": message, "isBase64": False}
                ),
            )
        else:
            _create_task_and_ignore_exception(
                self._ws._loop,
                self._ws._channel.send(
                    "sendToServer",
                    {"message": base64.b64encode(message).decode(), "isBase64": True},
                ),
            )


class WebSocketRoute(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._channel.mark_as_internal_type()
        self._on_page_message: Optional[Callable[[Union[str, bytes]], Any]] = None
        self._on_page_close: Optional[Callable[[Optional[int], Optional[str]], Any]] = (
            None
        )
        self._on_server_message: Optional[Callable[[Union[str, bytes]], Any]] = None
        self._on_server_close: Optional[
            Callable[[Optional[int], Optional[str]], Any]
        ] = None
        self._server = ServerWebSocketRoute(self)
        self._connected = False

        self._channel.on("messageFromPage", self._channel_message_from_page)
        self._channel.on("messageFromServer", self._channel_message_from_server)
        self._channel.on("closePage", self._channel_close_page)
        self._channel.on("closeServer", self._channel_close_server)

    def _channel_message_from_page(self, event: Dict) -> None:
        if self._on_page_message:
            self._on_page_message(
                base64.b64decode(event["message"])
                if event["isBase64"]
                else event["message"]
            )
        elif self._connected:
            _create_task_and_ignore_exception(
                self._loop, self._channel.send("sendToServer", event)
            )

    def _channel_message_from_server(self, event: Dict) -> None:
        if self._on_server_message:
            self._on_server_message(
                base64.b64decode(event["message"])
                if event["isBase64"]
                else event["message"]
            )
        else:
            _create_task_and_ignore_exception(
                self._loop, self._channel.send("sendToPage", event)
            )

    def _channel_close_page(self, event: Dict) -> None:
        if self._on_page_close:
            self._on_page_close(event["code"], event["reason"])
        else:
            _create_task_and_ignore_exception(
                self._loop, self._channel.send("closeServer", event)
            )

    def _channel_close_server(self, event: Dict) -> None:
        if self._on_server_close:
            self._on_server_close(event["code"], event["reason"])
        else:
            _create_task_and_ignore_exception(
                self._loop, self._channel.send("closePage", event)
            )

    @property
    def url(self) -> str:
        return self._initializer["url"]

    async def close(self, code: int = None, reason: str = None) -> None:
        try:
            await self._channel.send(
                "closePage", {"code": code, "reason": reason, "wasClean": True}
            )
        except Exception:
            pass

    def connect_to_server(self) -> "WebSocketRoute":
        if self._connected:
            raise Error("Already connected to the server")
        self._connected = True
        asyncio.create_task(self._channel.send("connect"))
        return cast("WebSocketRoute", self._server)

    def send(self, message: Union[str, bytes]) -> None:
        if isinstance(message, str):
            _create_task_and_ignore_exception(
                self._loop,
                self._channel.send(
                    "sendToPage", {"message": message, "isBase64": False}
                ),
            )
        else:
            _create_task_and_ignore_exception(
                self._loop,
                self._channel.send(
                    "sendToPage",
                    {
                        "message": base64.b64encode(message).decode(),
                        "isBase64": True,
                    },
                ),
            )

    def on_message(self, handler: Callable[[Union[str, bytes]], Any]) -> None:
        self._on_page_message = handler

    def on_close(self, handler: Callable[[Optional[int], Optional[str]], Any]) -> None:
        self._on_page_close = handler

    async def _after_handle(self) -> None:
        if self._connected:
            return
        # Ensure that websocket is "open" and can send messages without an actual server connection.
        await self._channel.send("ensureOpened")


class WebSocketRouteHandler:
    def __init__(
        self,
        base_url: Optional[str],
        url: URLMatch,
        handler: WebSocketRouteHandlerCallback,
    ):
        self._base_url = base_url
        self.url = url
        self.handler = handler

    @staticmethod
    def prepare_interception_patterns(
        handlers: List["WebSocketRouteHandler"],
    ) -> List[dict]:
        patterns = []
        all_urls = False
        for handler in handlers:
            if isinstance(handler.url, str):
                patterns.append({"glob": handler.url})
            elif isinstance(handler.url, re.Pattern):
                patterns.append(
                    {
                        "regexSource": handler.url.pattern,
                        "regexFlags": escape_regex_flags(handler.url),
                    }
                )
            else:
                all_urls = True

        if all_urls:
            return [{"glob": "**/*"}]
        return patterns

    def matches(self, ws_url: str) -> bool:
        return url_matches(self._base_url, ws_url, self.url, True)

    async def handle(self, websocket_route: "WebSocketRoute") -> None:
        coro_or_future = self.handler(websocket_route)
        if asyncio.iscoroutine(coro_or_future):
            await coro_or_future
        await websocket_route._after_handle()


class Response(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._channel.mark_as_internal_type()
        self._request: Request = from_channel(self._initializer["request"])
        timing = self._initializer["timing"]
        self._request._timing["startTime"] = timing["startTime"]
        self._request._timing["domainLookupStart"] = timing["domainLookupStart"]
        self._request._timing["domainLookupEnd"] = timing["domainLookupEnd"]
        self._request._timing["connectStart"] = timing["connectStart"]
        self._request._timing["secureConnectionStart"] = timing["secureConnectionStart"]
        self._request._timing["connectEnd"] = timing["connectEnd"]
        self._request._timing["requestStart"] = timing["requestStart"]
        self._request._timing["responseStart"] = timing["responseStart"]
        self._provisional_headers = RawHeaders(
            cast(HeadersArray, self._initializer["headers"])
        )
        self._raw_headers_future: Optional[asyncio.Future[RawHeaders]] = None
        self._finished_future: asyncio.Future[bool] = asyncio.Future()

    def __repr__(self) -> str:
        return f"<Response url={self.url!r} request={self.request}>"

    @property
    def url(self) -> str:
        return self._initializer["url"]

    @property
    def ok(self) -> bool:
        # Status 0 is for file:// URLs
        return self._initializer["status"] == 0 or (
            self._initializer["status"] >= 200 and self._initializer["status"] <= 299
        )

    @property
    def status(self) -> int:
        return self._initializer["status"]

    @property
    def status_text(self) -> str:
        return self._initializer["statusText"]

    @property
    def headers(self) -> Headers:
        return self._provisional_headers.headers()

    @property
    def from_service_worker(self) -> bool:
        return self._initializer["fromServiceWorker"]

    async def all_headers(self) -> Headers:
        return (await self._actual_headers()).headers()

    async def headers_array(self) -> HeadersArray:
        return (await self._actual_headers()).headers_array()

    async def header_value(self, name: str) -> Optional[str]:
        return (await self._actual_headers()).get(name)

    async def header_values(self, name: str) -> List[str]:
        return (await self._actual_headers()).get_all(name)

    async def _actual_headers(self) -> "RawHeaders":
        if not self._raw_headers_future:
            self._raw_headers_future = asyncio.Future()
            headers = cast(HeadersArray, await self._channel.send("rawResponseHeaders"))
            self._raw_headers_future.set_result(RawHeaders(headers))
        return await self._raw_headers_future

    async def server_addr(self) -> Optional[RemoteAddr]:
        return await self._channel.send("serverAddr")

    async def security_details(self) -> Optional[SecurityDetails]:
        return await self._channel.send("securityDetails")

    async def finished(self) -> None:
        async def on_finished() -> None:
            await self._request._target_closed_future()
            raise Error("Target closed")

        on_finished_task = asyncio.create_task(on_finished())
        await asyncio.wait(
            cast(
                List[Union[asyncio.Task, asyncio.Future]],
                [self._finished_future, on_finished_task],
            ),
            return_when=asyncio.FIRST_COMPLETED,
        )
        if on_finished_task.done():
            await on_finished_task

    async def body(self) -> bytes:
        binary = await self._channel.send("body")
        return base64.b64decode(binary)

    async def text(self) -> str:
        content = await self.body()
        return content.decode()

    async def json(self) -> Any:
        return json.loads(await self.text())

    @property
    def request(self) -> Request:
        return self._request

    @property
    def frame(self) -> "Frame":
        return self._request.frame


class WebSocket(ChannelOwner):
    Events = SimpleNamespace(
        Close="close",
        FrameReceived="framereceived",
        FrameSent="framesent",
        Error="socketerror",
    )

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._is_closed = False
        self._page = cast("Page", parent)
        self._channel.on(
            "frameSent",
            lambda params: self._on_frame_sent(params["opcode"], params["data"]),
        )
        self._channel.on(
            "frameReceived",
            lambda params: self._on_frame_received(params["opcode"], params["data"]),
        )
        self._channel.on(
            "socketError",
            lambda params: self.emit(WebSocket.Events.Error, params["error"]),
        )
        self._channel.on("close", lambda params: self._on_close())

    def __repr__(self) -> str:
        return f"<WebSocket url={self.url!r}>"

    @property
    def url(self) -> str:
        return self._initializer["url"]

    def expect_event(
        self,
        event: str,
        predicate: Callable = None,
        timeout: float = None,
    ) -> EventContextManagerImpl:
        if timeout is None:
            timeout = cast(Any, self._parent)._timeout_settings.timeout()
        waiter = Waiter(self, f"web_socket.expect_event({event})")
        waiter.reject_on_timeout(
            cast(float, timeout),
            f'Timeout {timeout}ms exceeded while waiting for event "{event}"',
        )
        if event != WebSocket.Events.Close:
            waiter.reject_on_event(self, WebSocket.Events.Close, Error("Socket closed"))
        if event != WebSocket.Events.Error:
            waiter.reject_on_event(self, WebSocket.Events.Error, Error("Socket error"))
        waiter.reject_on_event(
            self._page, "close", lambda: self._page._close_error_with_reason()
        )
        waiter.wait_for_event(self, event, predicate)
        return EventContextManagerImpl(waiter.result())

    async def wait_for_event(
        self, event: str, predicate: Callable = None, timeout: float = None
    ) -> Any:
        async with self.expect_event(event, predicate, timeout) as event_info:
            pass
        return await event_info

    def _on_frame_sent(self, opcode: int, data: str) -> None:
        if opcode == 2:
            self.emit(WebSocket.Events.FrameSent, base64.b64decode(data))
        elif opcode == 1:
            self.emit(WebSocket.Events.FrameSent, data)

    def _on_frame_received(self, opcode: int, data: str) -> None:
        if opcode == 2:
            self.emit(WebSocket.Events.FrameReceived, base64.b64decode(data))
        elif opcode == 1:
            self.emit(WebSocket.Events.FrameReceived, data)

    def is_closed(self) -> bool:
        return self._is_closed

    def _on_close(self) -> None:
        self._is_closed = True
        self.emit(WebSocket.Events.Close, self)


class RawHeaders:
    def __init__(self, headers: HeadersArray) -> None:
        self._headers_array = headers
        self._headers_map: Dict[str, Dict[str, bool]] = defaultdict(dict)
        for header in headers:
            self._headers_map[header["name"].lower()][header["value"]] = True

    @staticmethod
    def _from_headers_dict_lossy(headers: Dict[str, str]) -> "RawHeaders":
        return RawHeaders(serialize_headers(headers))

    def get(self, name: str) -> Optional[str]:
        values = self.get_all(name)
        if not values:
            return None
        separator = "\n" if name.lower() == "set-cookie" else ", "
        return separator.join(values)

    def get_all(self, name: str) -> List[str]:
        return list(self._headers_map[name.lower()].keys())

    def headers(self) -> Dict[str, str]:
        result = {}
        for name in self._headers_map.keys():
            result[name] = cast(str, self.get(name))
        return result

    def headers_array(self) -> HeadersArray:
        return self._headers_array

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\openai_files_endpoints\files_endpoints.py ===
######################################################################

#                          /v1/files Endpoints

# Equivalent of https://platform.openai.com/docs/api-reference/files
######################################################################

import asyncio
import traceback
from typing import Optional, cast, get_args

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)

import litellm
from litellm import CreateFileRequest, get_secret_str
from litellm._logging import verbose_proxy_logger
from litellm.llms.base_llm.files.transformation import BaseFileEndpoints
from litellm.proxy._types import *
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.common_request_processing import ProxyBaseLLMRequestProcessing
from litellm.proxy.common_utils.openai_endpoint_utils import (
    get_custom_llm_provider_from_request_body,
)
from litellm.proxy.utils import ProxyLogging, is_known_model
from litellm.router import Router
from litellm.types.llms.openai import (
    CREATE_FILE_REQUESTS_PURPOSE,
    OpenAIFileObject,
    OpenAIFilesPurpose,
)

from .common_utils import _is_base64_encoded_unified_file_id

router = APIRouter()

files_config = None


def set_files_config(config):
    global files_config
    if config is None:
        return

    if not isinstance(config, list):
        raise ValueError("invalid files config, expected a list is not a list")

    for element in config:
        if isinstance(element, dict):
            for key, value in element.items():
                if isinstance(value, str) and value.startswith("os.environ/"):
                    element[key] = get_secret_str(value)

    files_config = config


def get_files_provider_config(
    custom_llm_provider: str,
):
    global files_config
    if custom_llm_provider == "vertex_ai":
        return None
    if files_config is None:
        raise ValueError("files_settings is not set, set it on your config.yaml file.")
    for setting in files_config:
        if setting.get("custom_llm_provider") == custom_llm_provider:
            return setting
    return None


def get_first_json_object(file_content_bytes: bytes) -> Optional[dict]:
    try:
        # Decode the bytes to a string and split into lines
        file_content = file_content_bytes.decode("utf-8")
        first_line = file_content.splitlines()[0].strip()

        # Parse the JSON object from the first line
        json_object = json.loads(first_line)
        return json_object
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def get_model_from_json_obj(json_object: dict) -> Optional[str]:
    body = json_object.get("body", {}) or {}
    model = body.get("model")

    return model


async def _deprecated_loadbalanced_create_file(
    llm_router: Optional[Router],
    router_model: str,
    _create_file_request: CreateFileRequest,
) -> OpenAIFileObject:
    if llm_router is None:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "LLM Router not initialized. Ensure models added to proxy."
            },
        )

    response = await llm_router.acreate_file(model=router_model, **_create_file_request)
    return response


async def route_create_file(
    llm_router: Optional[Router],
    _create_file_request: CreateFileRequest,
    purpose: OpenAIFilesPurpose,
    proxy_logging_obj: ProxyLogging,
    user_api_key_dict: UserAPIKeyAuth,
    target_model_names_list: List[str],
    is_router_model: bool,
    router_model: Optional[str],
    custom_llm_provider: str,
) -> OpenAIFileObject:
    if (
        litellm.enable_loadbalancing_on_batch_endpoints is True
        and is_router_model
        and router_model is not None
    ):
        response = await _deprecated_loadbalanced_create_file(
            llm_router=llm_router,
            router_model=router_model,
            _create_file_request=_create_file_request,
        )
    elif target_model_names_list:
        managed_files_obj = proxy_logging_obj.get_proxy_hook("managed_files")
        if managed_files_obj is None:
            raise ProxyException(
                message="Managed files hook not found",
                type="None",
                param="None",
                code=500,
            )
        if llm_router is None:
            raise ProxyException(
                message="LLM Router not found",
                type="None",
                param="None",
                code=500,
            )
        if not isinstance(managed_files_obj, BaseFileEndpoints):
            raise ProxyException(
                message="Managed files hook is not a BaseFileEndpoints",
                type="None",
                param="None",
                code=500,
            )
        response = await managed_files_obj.acreate_file(
            llm_router=llm_router,
            create_file_request=_create_file_request,
            target_model_names_list=target_model_names_list,
            litellm_parent_otel_span=user_api_key_dict.parent_otel_span,
            user_api_key_dict=user_api_key_dict,
        )
    else:
        # get configs for custom_llm_provider
        llm_provider_config = get_files_provider_config(
            custom_llm_provider=custom_llm_provider
        )
        if llm_provider_config is not None:
            # add llm_provider_config to data
            _create_file_request.update(llm_provider_config)
        _create_file_request.pop("custom_llm_provider", None)  # type: ignore
        # for now use custom_llm_provider=="openai" -> this will change as LiteLLM adds more providers for acreate_batch
        response = await litellm.acreate_file(**_create_file_request, custom_llm_provider=custom_llm_provider)  # type: ignore

    return response


@router.post(
    "/{provider}/v1/files",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
@router.post(
    "/v1/files",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
@router.post(
    "/files",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
async def create_file(
    request: Request,
    fastapi_response: Response,
    purpose: str = Form(...),
    target_model_names: str = Form(default=""),
    provider: Optional[str] = None,
    custom_llm_provider: str = Form(default="openai"),
    file: UploadFile = File(...),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Upload a file that can be used across - Assistants API, Batch API 
    This is the equivalent of POST https://api.openai.com/v1/files

    Supports Identical Params as: https://platform.openai.com/docs/api-reference/files/create

    Example Curl
    ```
    curl http://localhost:4000/v1/files \
        -H "Authorization: Bearer sk-1234" \
        -F purpose="batch" \
        -F file="@mydata.jsonl"

    ```
    """
    from litellm.proxy.proxy_server import (
        add_litellm_data_to_request,
        general_settings,
        llm_router,
        proxy_config,
        proxy_logging_obj,
        version,
    )

    data: Dict = {}
    try:
        # Use orjson to parse JSON data, orjson speeds up requests significantly
        # Read the file content
        file_content = await file.read()
        custom_llm_provider = (
            provider
            or await get_custom_llm_provider_from_request_body(request=request)
            or "openai"
        )

        target_model_names_list = (
            target_model_names.split(",") if target_model_names else []
        )
        target_model_names_list = [model.strip() for model in target_model_names_list]
        # Prepare the data for forwarding

        # Replace with:
        valid_purposes = get_args(OpenAIFilesPurpose)
        if purpose not in valid_purposes:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Invalid purpose: {purpose}. Must be one of: {valid_purposes}",
                },
            )
        # Cast purpose to OpenAIFilesPurpose type
        purpose = cast(OpenAIFilesPurpose, purpose)

        data = {}

        # Include original request and headers in the data
        data = await add_litellm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        # Prepare the file data according to FileTypes
        file_data = (file.filename, file_content, file.content_type)

        ## check if model is a loadbalanced model
        router_model: Optional[str] = None
        is_router_model = False
        if litellm.enable_loadbalancing_on_batch_endpoints is True:
            json_obj = get_first_json_object(file_content_bytes=file_content)
            if json_obj:
                router_model = get_model_from_json_obj(json_object=json_obj)
                is_router_model = is_known_model(
                    model=router_model, llm_router=llm_router
                )

        _create_file_request = CreateFileRequest(
            file=file_data, purpose=cast(CREATE_FILE_REQUESTS_PURPOSE, purpose), **data
        )

        response = await route_create_file(
            llm_router=llm_router,
            _create_file_request=_create_file_request,
            purpose=purpose,
            proxy_logging_obj=proxy_logging_obj,
            user_api_key_dict=user_api_key_dict,
            target_model_names_list=target_model_names_list,
            is_router_model=is_router_model,
            router_model=router_model,
            custom_llm_provider=custom_llm_provider,
        )

        if response is None:
            raise HTTPException(
                status_code=500,
                detail={"error": "Failed to create file. Please try again."},
            )
        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                litellm_call_id=data.get("litellm_call_id", ""), status="success"
            )
        )

        ## POST CALL HOOKS ###
        _response = await proxy_logging_obj.post_call_success_hook(
            data=data, user_api_key_dict=user_api_key_dict, response=response
        )
        if _response is not None and isinstance(_response, OpenAIFileObject):
            response = _response

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
            )
        )
        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.create_file(): Exception occured - {}".format(
                str(e)
            )
        )
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", 500),
            )


@router.get(
    "/{provider}/v1/files/{file_id:path}/content",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
@router.get(
    "/v1/files/{file_id:path}/content",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
@router.get(
    "/files/{file_id:path}/content",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
async def get_file_content(
    request: Request,
    fastapi_response: Response,
    file_id: str,
    provider: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Returns information about a specific file. that can be used across - Assistants API, Batch API 
    This is the equivalent of GET https://api.openai.com/v1/files/{file_id}/content

    Supports Identical Params as: https://platform.openai.com/docs/api-reference/files/retrieve-contents

    Example Curl
    ```
    curl http://localhost:4000/v1/files/file-abc123/content \
        -H "Authorization: Bearer sk-1234"

    ```
    """
    from litellm.proxy.proxy_server import (
        general_settings,
        llm_router,
        proxy_config,
        proxy_logging_obj,
        version,
    )

    data: Dict = {"file_id": file_id}
    try:
        # Include original request and headers in the data
        base_llm_response_processor = ProxyBaseLLMRequestProcessing(data=data)
        (
            data,
            litellm_logging_obj,
        ) = await base_llm_response_processor.common_processing_pre_call_logic(
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_logging_obj=proxy_logging_obj,
            proxy_config=proxy_config,
            route_type="afile_content",
        )

        custom_llm_provider = (
            provider
            or await get_custom_llm_provider_from_request_body(request=request)
            or "openai"
        )

        ## check if file_id is a litellm managed file
        is_base64_unified_file_id = _is_base64_encoded_unified_file_id(file_id)
        if is_base64_unified_file_id:
            managed_files_obj = proxy_logging_obj.get_proxy_hook("managed_files")
            if managed_files_obj is None:
                raise ProxyException(
                    message="Managed files hook not found",
                    type="None",
                    param="None",
                    code=500,
                )
            if llm_router is None:
                raise ProxyException(
                    message="LLM Router not found",
                    type="None",
                    param="None",
                    code=500,
                )
            if not isinstance(managed_files_obj, BaseFileEndpoints):
                raise ProxyException(
                    message="Managed files hook is not a BaseFileEndpoints",
                    type="None",
                    param="None",
                    code=500,
                )
            model = cast(Optional[str], data.get("model"))
            if model:
                response = await llm_router.afile_content(
                    **{
                        "model": model,
                        "file_id": file_id,
                        **data,
                    }
                )  # type: ignore

            else:
                response = await managed_files_obj.afile_content(
                    **{
                        "file_id": file_id,
                        "litellm_parent_otel_span": user_api_key_dict.parent_otel_span,
                        "llm_router": llm_router,
                        **data,
                    }
                )
        else:
            response = await litellm.afile_content(
                **{
                    "custom_llm_provider": custom_llm_provider,
                    "file_id": file_id,
                    **data,
                }  # type: ignore
            )

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                litellm_call_id=data.get("litellm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
            )
        )
        httpx_response: Optional[httpx.Response] = getattr(response, "response", None)
        if httpx_response is None:
            raise ValueError(
                f"Invalid response - response.response is None - got {response}"
            )

        return Response(
            content=httpx_response.content,
            status_code=httpx_response.status_code,
            headers=httpx_response.headers,
        )

    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.exception(
            "litellm.proxy.proxy_server.retrieve_file_content(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", 500),
            )


@router.get(
    "/{provider}/v1/files/{file_id:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
@router.get(
    "/v1/files/{file_id:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
@router.get(
    "/files/{file_id:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
async def get_file(
    request: Request,
    fastapi_response: Response,
    file_id: str,
    provider: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Returns information about a specific file. that can be used across - Assistants API, Batch API 
    This is the equivalent of GET https://api.openai.com/v1/files/{file_id}

    Supports Identical Params as: https://platform.openai.com/docs/api-reference/files/retrieve

    Example Curl
    ```
    curl http://localhost:4000/v1/files/file-abc123 \
        -H "Authorization: Bearer sk-1234"

    ```
    """
    from litellm.proxy.proxy_server import (
        add_litellm_data_to_request,
        general_settings,
        proxy_config,
        proxy_logging_obj,
        version,
    )

    data: Dict = {}
    try:
        custom_llm_provider = (
            provider
            or await get_custom_llm_provider_from_request_body(request=request)
            or "openai"
        )
        # Include original request and headers in the data
        data = await add_litellm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        ## check if file_id is a litellm managed file
        is_base64_unified_file_id = _is_base64_encoded_unified_file_id(file_id)

        if is_base64_unified_file_id:
            managed_files_obj = proxy_logging_obj.get_proxy_hook("managed_files")
            if managed_files_obj is None:
                raise ProxyException(
                    message="Managed files hook not found",
                    type="None",
                    param="None",
                    code=500,
                )
            if not isinstance(managed_files_obj, BaseFileEndpoints):
                raise ProxyException(
                    message="Managed files hook is not a BaseFileEndpoints",
                    type="None",
                    param="None",
                    code=500,
                )
            response = await managed_files_obj.afile_retrieve(
                file_id=file_id,
                litellm_parent_otel_span=user_api_key_dict.parent_otel_span,
            )
        else:
            response = await litellm.afile_retrieve(
                custom_llm_provider=custom_llm_provider, file_id=file_id, **data  # type: ignore
            )

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                litellm_call_id=data.get("litellm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
            )
        )
        return response

    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.error(
            "litellm.proxy.proxy_server.retrieve_file(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", 500),
            )


@router.delete(
    "/{provider}/v1/files/{file_id:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
@router.delete(
    "/v1/files/{file_id:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
@router.delete(
    "/files/{file_id:path}",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
async def delete_file(
    request: Request,
    fastapi_response: Response,
    file_id: str,
    provider: Optional[str] = None,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Deletes a specified file. that can be used across - Assistants API, Batch API 
    This is the equivalent of DELETE https://api.openai.com/v1/files/{file_id}

    Supports Identical Params as: https://platform.openai.com/docs/api-reference/files/delete

    Example Curl
    ```
    curl http://localhost:4000/v1/files/file-abc123 \
    -X DELETE \
    -H "Authorization: Bearer $OPENAI_API_KEY"

    ```
    """
    from litellm.proxy.proxy_server import (
        add_litellm_data_to_request,
        general_settings,
        llm_router,
        proxy_config,
        proxy_logging_obj,
        version,
    )

    data: Dict = {}
    try:
        custom_llm_provider = (
            provider
            or await get_custom_llm_provider_from_request_body(request=request)
            or "openai"
        )
        # Include original request and headers in the data
        data = await add_litellm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        ## check if file_id is a litellm managed file
        is_base64_unified_file_id = _is_base64_encoded_unified_file_id(file_id)

        if is_base64_unified_file_id:
            managed_files_obj = proxy_logging_obj.get_proxy_hook("managed_files")
            if managed_files_obj is None:
                raise ProxyException(
                    message="Managed files hook not found",
                    type="None",
                    param="None",
                    code=500,
                )
            if llm_router is None:
                raise ProxyException(
                    message="LLM Router not found",
                    type="None",
                    param="None",
                    code=500,
                )
            if not isinstance(managed_files_obj, BaseFileEndpoints):
                raise ProxyException(
                    message="Managed files hook is not a BaseFileEndpoints",
                    type="None",
                    param="None",
                    code=500,
                )
            response = await managed_files_obj.afile_delete(
                file_id=file_id,
                litellm_parent_otel_span=user_api_key_dict.parent_otel_span,
                llm_router=llm_router,
                **data,
            )
        else:
            response = await litellm.afile_delete(
                custom_llm_provider=custom_llm_provider, file_id=file_id, **data  # type: ignore
            )

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                litellm_call_id=data.get("litellm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
            )
        )
        return response

    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.error(
            "litellm.proxy.proxy_server.retrieve_file(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", 500),
            )


@router.get(
    "/{provider}/v1/files",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
@router.get(
    "/v1/files",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
@router.get(
    "/files",
    dependencies=[Depends(user_api_key_auth)],
    tags=["files"],
)
async def list_files(
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    provider: Optional[str] = None,
    target_model_names: Optional[str] = None,
    purpose: Optional[str] = None,
):
    """
    Returns information about a specific file. that can be used across - Assistants API, Batch API 
    This is the equivalent of GET https://api.openai.com/v1/files/

    Supports Identical Params as: https://platform.openai.com/docs/api-reference/files/list

    Example Curl
    ```
    curl http://localhost:4000/v1/files\
        -H "Authorization: Bearer sk-1234"

    ```
    """
    from litellm.proxy.proxy_server import (
        general_settings,
        llm_router,
        proxy_config,
        proxy_logging_obj,
        version,
    )

    data: Dict = {}
    try:
        # Include original request and headers in the data
        base_llm_response_processor = ProxyBaseLLMRequestProcessing(data=data)
        (
            data,
            litellm_logging_obj,
        ) = await base_llm_response_processor.common_processing_pre_call_logic(
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_logging_obj=proxy_logging_obj,
            proxy_config=proxy_config,
            route_type=CallTypes.alist_fine_tuning_jobs.value,
        )

        response: Optional[Any] = None
        if target_model_names and isinstance(target_model_names, str):
            target_model_names_list = target_model_names.split(",")
            if len(target_model_names_list) != 1:
                raise HTTPException(
                    status_code=400,
                    detail="target_model_names on list files must be a list of one model name. Example: ['gpt-4o']",
                )
            ## Use router to list fine-tuning jobs for that model
            if llm_router is None:
                raise HTTPException(
                    status_code=500,
                    detail="LLM Router not initialized. Ensure models added to proxy.",
                )
            data["model"] = target_model_names_list[0]
            response = await llm_router.afile_list(
                **data,
            )
        else:
            custom_llm_provider = (
                provider
                or await get_custom_llm_provider_from_request_body(request=request)
                or "openai"
            )

            response = await litellm.afile_list(
                custom_llm_provider=custom_llm_provider, purpose=purpose, **data  # type: ignore
            )

        if response is None:
            raise HTTPException(
                status_code=500,
                detail="Either 'provider' or 'target_model_names' must be provided e.g. `?target_model_names=gpt-4o`",
            )

        ## POST CALL HOOKS ###
        _response = await proxy_logging_obj.post_call_success_hook(
            data=data, user_api_key_dict=user_api_key_dict, response=response
        )
        if _response is not None and isinstance(_response, OpenAIFileObject):
            response = _response

        ### ALERTING ###
        asyncio.create_task(
            proxy_logging_obj.update_request_status(
                litellm_call_id=data.get("litellm_call_id", ""), status="success"
            )
        )

        ### RESPONSE HEADERS ###
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        model_id = hidden_params.get("model_id", None) or ""
        cache_key = hidden_params.get("cache_key", None) or ""
        api_base = hidden_params.get("api_base", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
            )
        )
        return response

    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.error(
            "litellm.proxy.proxy_server.list_files(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e.detail)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", 500),
            )

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\formatters\html.py ===
"""
    pygments.formatters.html
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for HTML output.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import functools
import os
import sys
import os.path
from io import StringIO

from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.token import Token, Text, STANDARD_TYPES
from pip._vendor.pygments.util import get_bool_opt, get_int_opt, get_list_opt

try:
    import ctags
except ImportError:
    ctags = None

__all__ = ['HtmlFormatter']


_escape_html_table = {
    ord('&'): '&amp;',
    ord('<'): '&lt;',
    ord('>'): '&gt;',
    ord('"'): '&quot;',
    ord("'"): '&#39;',
}


def escape_html(text, table=_escape_html_table):
    """Escape &, <, > as well as single and double quotes for HTML."""
    return text.translate(table)


def webify(color):
    if color.startswith('calc') or color.startswith('var'):
        return color
    else:
        return '#' + color


def _get_ttype_class(ttype):
    fname = STANDARD_TYPES.get(ttype)
    if fname:
        return fname
    aname = ''
    while fname is None:
        aname = '-' + ttype[-1] + aname
        ttype = ttype.parent
        fname = STANDARD_TYPES.get(ttype)
    return fname + aname


CSSFILE_TEMPLATE = '''\
/*
generated by Pygments <https://pygments.org/>
Copyright 2006-2024 by the Pygments team.
Licensed under the BSD license, see LICENSE for details.
*/
%(styledefs)s
'''

DOC_HEADER = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
   "http://www.w3.org/TR/html4/strict.dtd">
<!--
generated by Pygments <https://pygments.org/>
Copyright 2006-2024 by the Pygments team.
Licensed under the BSD license, see LICENSE for details.
-->
<html>
<head>
  <title>%(title)s</title>
  <meta http-equiv="content-type" content="text/html; charset=%(encoding)s">
  <style type="text/css">
''' + CSSFILE_TEMPLATE + '''
  </style>
</head>
<body>
<h2>%(title)s</h2>

'''

DOC_HEADER_EXTERNALCSS = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
   "http://www.w3.org/TR/html4/strict.dtd">

<html>
<head>
  <title>%(title)s</title>
  <meta http-equiv="content-type" content="text/html; charset=%(encoding)s">
  <link rel="stylesheet" href="%(cssfile)s" type="text/css">
</head>
<body>
<h2>%(title)s</h2>

'''

DOC_FOOTER = '''\
</body>
</html>
'''


class HtmlFormatter(Formatter):
    r"""
    Format tokens as HTML 4 ``<span>`` tags. By default, the content is enclosed
    in a ``<pre>`` tag, itself wrapped in a ``<div>`` tag (but see the `nowrap` option).
    The ``<div>``'s CSS class can be set by the `cssclass` option.

    If the `linenos` option is set to ``"table"``, the ``<pre>`` is
    additionally wrapped inside a ``<table>`` which has one row and two
    cells: one containing the line numbers and one containing the code.
    Example:

    .. sourcecode:: html

        <div class="highlight" >
        <table><tr>
          <td class="linenos" title="click to toggle"
            onclick="with (this.firstChild.style)
                     { display = (display == '') ? 'none' : '' }">
            <pre>1
            2</pre>
          </td>
          <td class="code">
            <pre><span class="Ke">def </span><span class="NaFu">foo</span>(bar):
              <span class="Ke">pass</span>
            </pre>
          </td>
        </tr></table></div>

    (whitespace added to improve clarity).

    A list of lines can be specified using the `hl_lines` option to make these
    lines highlighted (as of Pygments 0.11).

    With the `full` option, a complete HTML 4 document is output, including
    the style definitions inside a ``<style>`` tag, or in a separate file if
    the `cssfile` option is given.

    When `tagsfile` is set to the path of a ctags index file, it is used to
    generate hyperlinks from names to their definition.  You must enable
    `lineanchors` and run ctags with the `-n` option for this to work.  The
    `python-ctags` module from PyPI must be installed to use this feature;
    otherwise a `RuntimeError` will be raised.

    The `get_style_defs(arg='')` method of a `HtmlFormatter` returns a string
    containing CSS rules for the CSS classes used by the formatter. The
    argument `arg` can be used to specify additional CSS selectors that
    are prepended to the classes. A call `fmter.get_style_defs('td .code')`
    would result in the following CSS classes:

    .. sourcecode:: css

        td .code .kw { font-weight: bold; color: #00FF00 }
        td .code .cm { color: #999999 }
        ...

    If you have Pygments 0.6 or higher, you can also pass a list or tuple to the
    `get_style_defs()` method to request multiple prefixes for the tokens:

    .. sourcecode:: python

        formatter.get_style_defs(['div.syntax pre', 'pre.syntax'])

    The output would then look like this:

    .. sourcecode:: css

        div.syntax pre .kw,
        pre.syntax .kw { font-weight: bold; color: #00FF00 }
        div.syntax pre .cm,
        pre.syntax .cm { color: #999999 }
        ...

    Additional options accepted:

    `nowrap`
        If set to ``True``, don't add a ``<pre>`` and a ``<div>`` tag
        around the tokens. This disables most other options (default: ``False``).

    `full`
        Tells the formatter to output a "full" document, i.e. a complete
        self-contained document (default: ``False``).

    `title`
        If `full` is true, the title that should be used to caption the
        document (default: ``''``).

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``). This option has no effect if the `cssfile`
        and `noclobber_cssfile` option are given and the file specified in
        `cssfile` exists.

    `noclasses`
        If set to true, token ``<span>`` tags (as well as line number elements)
        will not use CSS classes, but inline styles. This is not recommended
        for larger pieces of code since it increases output size by quite a bit
        (default: ``False``).

    `classprefix`
        Since the token types use relatively short class names, they may clash
        with some of your own class names. In this case you can use the
        `classprefix` option to give a string to prepend to all Pygments-generated
        CSS class names for token types.
        Note that this option also affects the output of `get_style_defs()`.

    `cssclass`
        CSS class for the wrapping ``<div>`` tag (default: ``'highlight'``).
        If you set this option, the default selector for `get_style_defs()`
        will be this class.

        .. versionadded:: 0.9
           If you select the ``'table'`` line numbers, the wrapping table will
           have a CSS class of this string plus ``'table'``, the default is
           accordingly ``'highlighttable'``.

    `cssstyles`
        Inline CSS styles for the wrapping ``<div>`` tag (default: ``''``).

    `prestyles`
        Inline CSS styles for the ``<pre>`` tag (default: ``''``).

        .. versionadded:: 0.11

    `cssfile`
        If the `full` option is true and this option is given, it must be the
        name of an external file. If the filename does not include an absolute
        path, the file's path will be assumed to be relative to the main output
        file's path, if the latter can be found. The stylesheet is then written
        to this file instead of the HTML file.

        .. versionadded:: 0.6

    `noclobber_cssfile`
        If `cssfile` is given and the specified file exists, the css file will
        not be overwritten. This allows the use of the `full` option in
        combination with a user specified css file. Default is ``False``.

        .. versionadded:: 1.1

    `linenos`
        If set to ``'table'``, output line numbers as a table with two cells,
        one containing the line numbers, the other the whole code.  This is
        copy-and-paste-friendly, but may cause alignment problems with some
        browsers or fonts.  If set to ``'inline'``, the line numbers will be
        integrated in the ``<pre>`` tag that contains the code (that setting
        is *new in Pygments 0.8*).

        For compatibility with Pygments 0.7 and earlier, every true value
        except ``'inline'`` means the same as ``'table'`` (in particular, that
        means also ``True``).

        The default value is ``False``, which means no line numbers at all.

        **Note:** with the default ("table") line number mechanism, the line
        numbers and code can have different line heights in Internet Explorer
        unless you give the enclosing ``<pre>`` tags an explicit ``line-height``
        CSS property (you get the default line spacing with ``line-height:
        125%``).

    `hl_lines`
        Specify a list of lines to be highlighted. The line numbers are always
        relative to the input (i.e. the first line is line 1) and are
        independent of `linenostart`.

        .. versionadded:: 0.11

    `linenostart`
        The line number for the first line (default: ``1``).

    `linenostep`
        If set to a number n > 1, only every nth line number is printed.

    `linenospecial`
        If set to a number n > 0, every nth line number is given the CSS
        class ``"special"`` (default: ``0``).

    `nobackground`
        If set to ``True``, the formatter won't output the background color
        for the wrapping element (this automatically defaults to ``False``
        when there is no wrapping element [eg: no argument for the
        `get_syntax_defs` method given]) (default: ``False``).

        .. versionadded:: 0.6

    `lineseparator`
        This string is output between lines of code. It defaults to ``"\n"``,
        which is enough to break a line inside ``<pre>`` tags, but you can
        e.g. set it to ``"<br>"`` to get HTML line breaks.

        .. versionadded:: 0.7

    `lineanchors`
        If set to a nonempty string, e.g. ``foo``, the formatter will wrap each
        output line in an anchor tag with an ``id`` (and `name`) of ``foo-linenumber``.
        This allows easy linking to certain lines.

        .. versionadded:: 0.9

    `linespans`
        If set to a nonempty string, e.g. ``foo``, the formatter will wrap each
        output line in a span tag with an ``id`` of ``foo-linenumber``.
        This allows easy access to lines via javascript.

        .. versionadded:: 1.6

    `anchorlinenos`
        If set to `True`, will wrap line numbers in <a> tags. Used in
        combination with `linenos` and `lineanchors`.

    `tagsfile`
        If set to the path of a ctags file, wrap names in anchor tags that
        link to their definitions. `lineanchors` should be used, and the
        tags file should specify line numbers (see the `-n` option to ctags).
        The tags file is assumed to be encoded in UTF-8.

        .. versionadded:: 1.6

    `tagurlformat`
        A string formatting pattern used to generate links to ctags definitions.
        Available variables are `%(path)s`, `%(fname)s` and `%(fext)s`.
        Defaults to an empty string, resulting in just `#prefix-number` links.

        .. versionadded:: 1.6

    `filename`
        A string used to generate a filename when rendering ``<pre>`` blocks,
        for example if displaying source code. If `linenos` is set to
        ``'table'`` then the filename will be rendered in an initial row
        containing a single `<th>` which spans both columns.

        .. versionadded:: 2.1

    `wrapcode`
        Wrap the code inside ``<pre>`` blocks using ``<code>``, as recommended
        by the HTML5 specification.

        .. versionadded:: 2.4

    `debug_token_types`
        Add ``title`` attributes to all token ``<span>`` tags that show the
        name of the token.

        .. versionadded:: 2.10


    **Subclassing the HTML formatter**

    .. versionadded:: 0.7

    The HTML formatter is now built in a way that allows easy subclassing, thus
    customizing the output HTML code. The `format()` method calls
    `self._format_lines()` which returns a generator that yields tuples of ``(1,
    line)``, where the ``1`` indicates that the ``line`` is a line of the
    formatted source code.

    If the `nowrap` option is set, the generator is the iterated over and the
    resulting HTML is output.

    Otherwise, `format()` calls `self.wrap()`, which wraps the generator with
    other generators. These may add some HTML code to the one generated by
    `_format_lines()`, either by modifying the lines generated by the latter,
    then yielding them again with ``(1, line)``, and/or by yielding other HTML
    code before or after the lines, with ``(0, html)``. The distinction between
    source lines and other code makes it possible to wrap the generator multiple
    times.

    The default `wrap()` implementation adds a ``<div>`` and a ``<pre>`` tag.

    A custom `HtmlFormatter` subclass could look like this:

    .. sourcecode:: python

        class CodeHtmlFormatter(HtmlFormatter):

            def wrap(self, source, *, include_div):
                return self._wrap_code(source)

            def _wrap_code(self, source):
                yield 0, '<code>'
                for i, t in source:
                    if i == 1:
                        # it's a line of formatted code
                        t += '<br>'
                    yield i, t
                yield 0, '</code>'

    This results in wrapping the formatted lines with a ``<code>`` tag, where the
    source lines are broken using ``<br>`` tags.

    After calling `wrap()`, the `format()` method also adds the "line numbers"
    and/or "full document" wrappers if the respective options are set. Then, all
    HTML yielded by the wrapped generator is output.
    """

    name = 'HTML'
    aliases = ['html']
    filenames = ['*.html', '*.htm']

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.title = self._decodeifneeded(self.title)
        self.nowrap = get_bool_opt(options, 'nowrap', False)
        self.noclasses = get_bool_opt(options, 'noclasses', False)
        self.classprefix = options.get('classprefix', '')
        self.cssclass = self._decodeifneeded(options.get('cssclass', 'highlight'))
        self.cssstyles = self._decodeifneeded(options.get('cssstyles', ''))
        self.prestyles = self._decodeifneeded(options.get('prestyles', ''))
        self.cssfile = self._decodeifneeded(options.get('cssfile', ''))
        self.noclobber_cssfile = get_bool_opt(options, 'noclobber_cssfile', False)
        self.tagsfile = self._decodeifneeded(options.get('tagsfile', ''))
        self.tagurlformat = self._decodeifneeded(options.get('tagurlformat', ''))
        self.filename = self._decodeifneeded(options.get('filename', ''))
        self.wrapcode = get_bool_opt(options, 'wrapcode', False)
        self.span_element_openers = {}
        self.debug_token_types = get_bool_opt(options, 'debug_token_types', False)

        if self.tagsfile:
            if not ctags:
                raise RuntimeError('The "ctags" package must to be installed '
                                   'to be able to use the "tagsfile" feature.')
            self._ctags = ctags.CTags(self.tagsfile)

        linenos = options.get('linenos', False)
        if linenos == 'inline':
            self.linenos = 2
        elif linenos:
            # compatibility with <= 0.7
            self.linenos = 1
        else:
            self.linenos = 0
        self.linenostart = abs(get_int_opt(options, 'linenostart', 1))
        self.linenostep = abs(get_int_opt(options, 'linenostep', 1))
        self.linenospecial = abs(get_int_opt(options, 'linenospecial', 0))
        self.nobackground = get_bool_opt(options, 'nobackground', False)
        self.lineseparator = options.get('lineseparator', '\n')
        self.lineanchors = options.get('lineanchors', '')
        self.linespans = options.get('linespans', '')
        self.anchorlinenos = get_bool_opt(options, 'anchorlinenos', False)
        self.hl_lines = set()
        for lineno in get_list_opt(options, 'hl_lines', []):
            try:
                self.hl_lines.add(int(lineno))
            except ValueError:
                pass

        self._create_stylesheet()

    def _get_css_class(self, ttype):
        """Return the css class of this token type prefixed with
        the classprefix option."""
        ttypeclass = _get_ttype_class(ttype)
        if ttypeclass:
            return self.classprefix + ttypeclass
        return ''

    def _get_css_classes(self, ttype):
        """Return the CSS classes of this token type prefixed with the classprefix option."""
        cls = self._get_css_class(ttype)
        while ttype not in STANDARD_TYPES:
            ttype = ttype.parent
            cls = self._get_css_class(ttype) + ' ' + cls
        return cls or ''

    def _get_css_inline_styles(self, ttype):
        """Return the inline CSS styles for this token type."""
        cclass = self.ttype2class.get(ttype)
        while cclass is None:
            ttype = ttype.parent
            cclass = self.ttype2class.get(ttype)
        return cclass or ''

    def _create_stylesheet(self):
        t2c = self.ttype2class = {Token: ''}
        c2s = self.class2style = {}
        for ttype, ndef in self.style:
            name = self._get_css_class(ttype)
            style = ''
            if ndef['color']:
                style += 'color: {}; '.format(webify(ndef['color']))
            if ndef['bold']:
                style += 'font-weight: bold; '
            if ndef['italic']:
                style += 'font-style: italic; '
            if ndef['underline']:
                style += 'text-decoration: underline; '
            if ndef['bgcolor']:
                style += 'background-color: {}; '.format(webify(ndef['bgcolor']))
            if ndef['border']:
                style += 'border: 1px solid {}; '.format(webify(ndef['border']))
            if style:
                t2c[ttype] = name
                # save len(ttype) to enable ordering the styles by
                # hierarchy (necessary for CSS cascading rules!)
                c2s[name] = (style[:-2], ttype, len(ttype))

    def get_style_defs(self, arg=None):
        """
        Return CSS style definitions for the classes produced by the current
        highlighting style. ``arg`` can be a string or list of selectors to
        insert before the token type classes.
        """
        style_lines = []

        style_lines.extend(self.get_linenos_style_defs())
        style_lines.extend(self.get_background_style_defs(arg))
        style_lines.extend(self.get_token_style_defs(arg))

        return '\n'.join(style_lines)

    def get_token_style_defs(self, arg=None):
        prefix = self.get_css_prefix(arg)

        styles = [
            (level, ttype, cls, style)
            for cls, (style, ttype, level) in self.class2style.items()
            if cls and style
        ]
        styles.sort()

        lines = [
            f'{prefix(cls)} {{ {style} }} /* {repr(ttype)[6:]} */'
            for (level, ttype, cls, style) in styles
        ]

        return lines

    def get_background_style_defs(self, arg=None):
        prefix = self.get_css_prefix(arg)
        bg_color = self.style.background_color
        hl_color = self.style.highlight_color

        lines = []

        if arg and not self.nobackground and bg_color is not None:
            text_style = ''
            if Text in self.ttype2class:
                text_style = ' ' + self.class2style[self.ttype2class[Text]][0]
            lines.insert(
                0, '{}{{ background: {};{} }}'.format(
                    prefix(''), bg_color, text_style
                )
            )
        if hl_color is not None:
            lines.insert(
                0, '{} {{ background-color: {} }}'.format(prefix('hll'), hl_color)
            )

        return lines

    def get_linenos_style_defs(self):
        lines = [
            f'pre {{ {self._pre_style} }}',
            f'td.linenos .normal {{ {self._linenos_style} }}',
            f'span.linenos {{ {self._linenos_style} }}',
            f'td.linenos .special {{ {self._linenos_special_style} }}',
            f'span.linenos.special {{ {self._linenos_special_style} }}',
        ]

        return lines

    def get_css_prefix(self, arg):
        if arg is None:
            arg = ('cssclass' in self.options and '.'+self.cssclass or '')
        if isinstance(arg, str):
            args = [arg]
        else:
            args = list(arg)

        def prefix(cls):
            if cls:
                cls = '.' + cls
            tmp = []
            for arg in args:
                tmp.append((arg and arg + ' ' or '') + cls)
            return ', '.join(tmp)

        return prefix

    @property
    def _pre_style(self):
        return 'line-height: 125%;'

    @property
    def _linenos_style(self):
        color = self.style.line_number_color
        background_color = self.style.line_number_background_color
        return f'color: {color}; background-color: {background_color}; padding-left: 5px; padding-right: 5px;'

    @property
    def _linenos_special_style(self):
        color = self.style.line_number_special_color
        background_color = self.style.line_number_special_background_color
        return f'color: {color}; background-color: {background_color}; padding-left: 5px; padding-right: 5px;'

    def _decodeifneeded(self, value):
        if isinstance(value, bytes):
            if self.encoding:
                return value.decode(self.encoding)
            return value.decode()
        return value

    def _wrap_full(self, inner, outfile):
        if self.cssfile:
            if os.path.isabs(self.cssfile):
                # it's an absolute filename
                cssfilename = self.cssfile
            else:
                try:
                    filename = outfile.name
                    if not filename or filename[0] == '<':
                        # pseudo files, e.g. name == '<fdopen>'
                        raise AttributeError
                    cssfilename = os.path.join(os.path.dirname(filename),
                                               self.cssfile)
                except AttributeError:
                    print('Note: Cannot determine output file name, '
                          'using current directory as base for the CSS file name',
                          file=sys.stderr)
                    cssfilename = self.cssfile
            # write CSS file only if noclobber_cssfile isn't given as an option.
            try:
                if not os.path.exists(cssfilename) or not self.noclobber_cssfile:
                    with open(cssfilename, "w", encoding="utf-8") as cf:
                        cf.write(CSSFILE_TEMPLATE %
                                 {'styledefs': self.get_style_defs('body')})
            except OSError as err:
                err.strerror = 'Error writing CSS file: ' + err.strerror
                raise

            yield 0, (DOC_HEADER_EXTERNALCSS %
                      dict(title=self.title,
                           cssfile=self.cssfile,
                           encoding=self.encoding))
        else:
            yield 0, (DOC_HEADER %
                      dict(title=self.title,
                           styledefs=self.get_style_defs('body'),
                           encoding=self.encoding))

        yield from inner
        yield 0, DOC_FOOTER

    def _wrap_tablelinenos(self, inner):
        dummyoutfile = StringIO()
        lncount = 0
        for t, line in inner:
            if t:
                lncount += 1
            dummyoutfile.write(line)

        fl = self.linenostart
        mw = len(str(lncount + fl - 1))
        sp = self.linenospecial
        st = self.linenostep
        anchor_name = self.lineanchors or self.linespans
        aln = self.anchorlinenos
        nocls = self.noclasses

        lines = []

        for i in range(fl, fl+lncount):
            print_line = i % st == 0
            special_line = sp and i % sp == 0

            if print_line:
                line = '%*d' % (mw, i)
                if aln:
                    line = '<a href="#%s-%d">%s</a>' % (anchor_name, i, line)
            else:
                line = ' ' * mw

            if nocls:
                if special_line:
                    style = f' style="{self._linenos_special_style}"'
                else:
                    style = f' style="{self._linenos_style}"'
            else:
                if special_line:
                    style = ' class="special"'
                else:
                    style = ' class="normal"'

            if style:
                line = f'<span{style}>{line}</span>'

            lines.append(line)

        ls = '\n'.join(lines)

        # If a filename was specified, we can't put it into the code table as it
        # would misalign the line numbers. Hence we emit a separate row for it.
        filename_tr = ""
        if self.filename:
            filename_tr = (
                '<tr><th colspan="2" class="filename">'
                '<span class="filename">' + self.filename + '</span>'
                '</th></tr>')

        # in case you wonder about the seemingly redundant <div> here: since the
        # content in the other cell also is wrapped in a div, some browsers in
        # some configurations seem to mess up the formatting...
        yield 0, (f'<table class="{self.cssclass}table">' + filename_tr +
            '<tr><td class="linenos"><div class="linenodiv"><pre>' +
            ls + '</pre></div></td><td class="code">')
        yield 0, '<div>'
        yield 0, dummyoutfile.getvalue()
        yield 0, '</div>'
        yield 0, '</td></tr></table>'


    def _wrap_inlinelinenos(self, inner):
        # need a list of lines since we need the width of a single number :(
        inner_lines = list(inner)
        sp = self.linenospecial
        st = self.linenostep
        num = self.linenostart
        mw = len(str(len(inner_lines) + num - 1))
        anchor_name = self.lineanchors or self.linespans
        aln = self.anchorlinenos
        nocls = self.noclasses

        for _, inner_line in inner_lines:
            print_line = num % st == 0
            special_line = sp and num % sp == 0

            if print_line:
                line = '%*d' % (mw, num)
            else:
                line = ' ' * mw

            if nocls:
                if special_line:
                    style = f' style="{self._linenos_special_style}"'
                else:
                    style = f' style="{self._linenos_style}"'
            else:
                if special_line:
                    style = ' class="linenos special"'
                else:
                    style = ' class="linenos"'

            if style:
                linenos = f'<span{style}>{line}</span>'
            else:
                linenos = line

            if aln:
                yield 1, ('<a href="#%s-%d">%s</a>' % (anchor_name, num, linenos) +
                          inner_line)
            else:
                yield 1, linenos + inner_line
            num += 1

    def _wrap_lineanchors(self, inner):
        s = self.lineanchors
        # subtract 1 since we have to increment i *before* yielding
        i = self.linenostart - 1
        for t, line in inner:
            if t:
                i += 1
                href = "" if self.linenos else ' href="#%s-%d"' % (s, i)
                yield 1, '<a id="%s-%d" name="%s-%d"%s></a>' % (s, i, s, i, href) + line
            else:
                yield 0, line

    def _wrap_linespans(self, inner):
        s = self.linespans
        i = self.linenostart - 1
        for t, line in inner:
            if t:
                i += 1
                yield 1, '<span id="%s-%d">%s</span>' % (s, i, line)
            else:
                yield 0, line

    def _wrap_div(self, inner):
        style = []
        if (self.noclasses and not self.nobackground and
                self.style.background_color is not None):
            style.append(f'background: {self.style.background_color}')
        if self.cssstyles:
            style.append(self.cssstyles)
        style = '; '.join(style)

        yield 0, ('<div' + (self.cssclass and f' class="{self.cssclass}"') +
                  (style and (f' style="{style}"')) + '>')
        yield from inner
        yield 0, '</div>\n'

    def _wrap_pre(self, inner):
        style = []
        if self.prestyles:
            style.append(self.prestyles)
        if self.noclasses:
            style.append(self._pre_style)
        style = '; '.join(style)

        if self.filename and self.linenos != 1:
            yield 0, ('<span class="filename">' + self.filename + '</span>')

        # the empty span here is to keep leading empty lines from being
        # ignored by HTML parsers
        yield 0, ('<pre' + (style and f' style="{style}"') + '><span></span>')
        yield from inner
        yield 0, '</pre>'

    def _wrap_code(self, inner):
        yield 0, '<code>'
        yield from inner
        yield 0, '</code>'

    @functools.lru_cache(maxsize=100)
    def _translate_parts(self, value):
        """HTML-escape a value and split it by newlines."""
        return value.translate(_escape_html_table).split('\n')

    def _format_lines(self, tokensource):
        """
        Just format the tokens, without any wrapping tags.
        Yield individual lines.
        """
        nocls = self.noclasses
        lsep = self.lineseparator
        tagsfile = self.tagsfile

        lspan = ''
        line = []
        for ttype, value in tokensource:
            try:
                cspan = self.span_element_openers[ttype]
            except KeyError:
                title = ' title="{}"'.format('.'.join(ttype)) if self.debug_token_types else ''
                if nocls:
                    css_style = self._get_css_inline_styles(ttype)
                    if css_style:
                        css_style = self.class2style[css_style][0]
                        cspan = f'<span style="{css_style}"{title}>'
                    else:
                        cspan = ''
                else:
                    css_class = self._get_css_classes(ttype)
                    if css_class:
                        cspan = f'<span class="{css_class}"{title}>'
                    else:
                        cspan = ''
                self.span_element_openers[ttype] = cspan

            parts = self._translate_parts(value)

            if tagsfile and ttype in Token.Name:
                filename, linenumber = self._lookup_ctag(value)
                if linenumber:
                    base, filename = os.path.split(filename)
                    if base:
                        base += '/'
                    filename, extension = os.path.splitext(filename)
                    url = self.tagurlformat % {'path': base, 'fname': filename,
                                               'fext': extension}
                    parts[0] = "<a href=\"%s#%s-%d\">%s" % \
                        (url, self.lineanchors, linenumber, parts[0])
                    parts[-1] = parts[-1] + "</a>"

            # for all but the last line
            for part in parts[:-1]:
                if line:
                    # Also check for part being non-empty, so we avoid creating
                    # empty <span> tags
                    if lspan != cspan and part:
                        line.extend(((lspan and '</span>'), cspan, part,
                                     (cspan and '</span>'), lsep))
                    else:  # both are the same, or the current part was empty
                        line.extend((part, (lspan and '</span>'), lsep))
                    yield 1, ''.join(line)
                    line = []
                elif part:
                    yield 1, ''.join((cspan, part, (cspan and '</span>'), lsep))
                else:
                    yield 1, lsep
            # for the last line
            if line and parts[-1]:
                if lspan != cspan:
                    line.extend(((lspan and '</span>'), cspan, parts[-1]))
                    lspan = cspan
                else:
                    line.append(parts[-1])
            elif parts[-1]:
                line = [cspan, parts[-1]]
                lspan = cspan
            # else we neither have to open a new span nor set lspan

        if line:
            line.extend(((lspan and '</span>'), lsep))
            yield 1, ''.join(line)

    def _lookup_ctag(self, token):
        entry = ctags.TagEntry()
        if self._ctags.find(entry, token.encode(), 0):
            return entry['file'].decode(), entry['lineNumber']
        else:
            return None, None

    def _highlight_lines(self, tokensource):
        """
        Highlighted the lines specified in the `hl_lines` option by
        post-processing the token stream coming from `_format_lines`.
        """
        hls = self.hl_lines

        for i, (t, value) in enumerate(tokensource):
            if t != 1:
                yield t, value
            if i + 1 in hls:  # i + 1 because Python indexes start at 0
                if self.noclasses:
                    style = ''
                    if self.style.highlight_color is not None:
                        style = (f' style="background-color: {self.style.highlight_color}"')
                    yield 1, f'<span{style}>{value}</span>'
                else:
                    yield 1, f'<span class="hll">{value}</span>'
            else:
                yield 1, value

    def wrap(self, source):
        """
        Wrap the ``source``, which is a generator yielding
        individual lines, in custom generators. See docstring
        for `format`. Can be overridden.
        """

        output = source
        if self.wrapcode:
            output = self._wrap_code(output)

        output = self._wrap_pre(output)

        return output

    def format_unencoded(self, tokensource, outfile):
        """
        The formatting process uses several nested generators; which of
        them are used is determined by the user's options.

        Each generator should take at least one argument, ``inner``,
        and wrap the pieces of text generated by this.

        Always yield 2-tuples: (code, text). If "code" is 1, the text
        is part of the original tokensource being highlighted, if it's
        0, the text is some piece of wrapping. This makes it possible to
        use several different wrappers that process the original source
        linewise, e.g. line number generators.
        """
        source = self._format_lines(tokensource)

        # As a special case, we wrap line numbers before line highlighting
        # so the line numbers get wrapped in the highlighting tag.
        if not self.nowrap and self.linenos == 2:
            source = self._wrap_inlinelinenos(source)

        if self.hl_lines:
            source = self._highlight_lines(source)

        if not self.nowrap:
            if self.lineanchors:
                source = self._wrap_lineanchors(source)
            if self.linespans:
                source = self._wrap_linespans(source)
            source = self.wrap(source)
            if self.linenos == 1:
                source = self._wrap_tablelinenos(source)
            source = self._wrap_div(source)
            if self.full:
                source = self._wrap_full(source, outfile)

        for t, piece in source:
            outfile.write(piece)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\formatters\html.py ===
"""
    pygments.formatters.html
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for HTML output.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import functools
import os
import sys
import os.path
from io import StringIO

from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.token import Token, Text, STANDARD_TYPES
from pip._vendor.pygments.util import get_bool_opt, get_int_opt, get_list_opt

try:
    import ctags
except ImportError:
    ctags = None

__all__ = ['HtmlFormatter']


_escape_html_table = {
    ord('&'): '&amp;',
    ord('<'): '&lt;',
    ord('>'): '&gt;',
    ord('"'): '&quot;',
    ord("'"): '&#39;',
}


def escape_html(text, table=_escape_html_table):
    """Escape &, <, > as well as single and double quotes for HTML."""
    return text.translate(table)


def webify(color):
    if color.startswith('calc') or color.startswith('var'):
        return color
    else:
        return '#' + color


def _get_ttype_class(ttype):
    fname = STANDARD_TYPES.get(ttype)
    if fname:
        return fname
    aname = ''
    while fname is None:
        aname = '-' + ttype[-1] + aname
        ttype = ttype.parent
        fname = STANDARD_TYPES.get(ttype)
    return fname + aname


CSSFILE_TEMPLATE = '''\
/*
generated by Pygments <https://pygments.org/>
Copyright 2006-2024 by the Pygments team.
Licensed under the BSD license, see LICENSE for details.
*/
%(styledefs)s
'''

DOC_HEADER = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
   "http://www.w3.org/TR/html4/strict.dtd">
<!--
generated by Pygments <https://pygments.org/>
Copyright 2006-2024 by the Pygments team.
Licensed under the BSD license, see LICENSE for details.
-->
<html>
<head>
  <title>%(title)s</title>
  <meta http-equiv="content-type" content="text/html; charset=%(encoding)s">
  <style type="text/css">
''' + CSSFILE_TEMPLATE + '''
  </style>
</head>
<body>
<h2>%(title)s</h2>

'''

DOC_HEADER_EXTERNALCSS = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
   "http://www.w3.org/TR/html4/strict.dtd">

<html>
<head>
  <title>%(title)s</title>
  <meta http-equiv="content-type" content="text/html; charset=%(encoding)s">
  <link rel="stylesheet" href="%(cssfile)s" type="text/css">
</head>
<body>
<h2>%(title)s</h2>

'''

DOC_FOOTER = '''\
</body>
</html>
'''


class HtmlFormatter(Formatter):
    r"""
    Format tokens as HTML 4 ``<span>`` tags. By default, the content is enclosed
    in a ``<pre>`` tag, itself wrapped in a ``<div>`` tag (but see the `nowrap` option).
    The ``<div>``'s CSS class can be set by the `cssclass` option.

    If the `linenos` option is set to ``"table"``, the ``<pre>`` is
    additionally wrapped inside a ``<table>`` which has one row and two
    cells: one containing the line numbers and one containing the code.
    Example:

    .. sourcecode:: html

        <div class="highlight" >
        <table><tr>
          <td class="linenos" title="click to toggle"
            onclick="with (this.firstChild.style)
                     { display = (display == '') ? 'none' : '' }">
            <pre>1
            2</pre>
          </td>
          <td class="code">
            <pre><span class="Ke">def </span><span class="NaFu">foo</span>(bar):
              <span class="Ke">pass</span>
            </pre>
          </td>
        </tr></table></div>

    (whitespace added to improve clarity).

    A list of lines can be specified using the `hl_lines` option to make these
    lines highlighted (as of Pygments 0.11).

    With the `full` option, a complete HTML 4 document is output, including
    the style definitions inside a ``<style>`` tag, or in a separate file if
    the `cssfile` option is given.

    When `tagsfile` is set to the path of a ctags index file, it is used to
    generate hyperlinks from names to their definition.  You must enable
    `lineanchors` and run ctags with the `-n` option for this to work.  The
    `python-ctags` module from PyPI must be installed to use this feature;
    otherwise a `RuntimeError` will be raised.

    The `get_style_defs(arg='')` method of a `HtmlFormatter` returns a string
    containing CSS rules for the CSS classes used by the formatter. The
    argument `arg` can be used to specify additional CSS selectors that
    are prepended to the classes. A call `fmter.get_style_defs('td .code')`
    would result in the following CSS classes:

    .. sourcecode:: css

        td .code .kw { font-weight: bold; color: #00FF00 }
        td .code .cm { color: #999999 }
        ...

    If you have Pygments 0.6 or higher, you can also pass a list or tuple to the
    `get_style_defs()` method to request multiple prefixes for the tokens:

    .. sourcecode:: python

        formatter.get_style_defs(['div.syntax pre', 'pre.syntax'])

    The output would then look like this:

    .. sourcecode:: css

        div.syntax pre .kw,
        pre.syntax .kw { font-weight: bold; color: #00FF00 }
        div.syntax pre .cm,
        pre.syntax .cm { color: #999999 }
        ...

    Additional options accepted:

    `nowrap`
        If set to ``True``, don't add a ``<pre>`` and a ``<div>`` tag
        around the tokens. This disables most other options (default: ``False``).

    `full`
        Tells the formatter to output a "full" document, i.e. a complete
        self-contained document (default: ``False``).

    `title`
        If `full` is true, the title that should be used to caption the
        document (default: ``''``).

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``). This option has no effect if the `cssfile`
        and `noclobber_cssfile` option are given and the file specified in
        `cssfile` exists.

    `noclasses`
        If set to true, token ``<span>`` tags (as well as line number elements)
        will not use CSS classes, but inline styles. This is not recommended
        for larger pieces of code since it increases output size by quite a bit
        (default: ``False``).

    `classprefix`
        Since the token types use relatively short class names, they may clash
        with some of your own class names. In this case you can use the
        `classprefix` option to give a string to prepend to all Pygments-generated
        CSS class names for token types.
        Note that this option also affects the output of `get_style_defs()`.

    `cssclass`
        CSS class for the wrapping ``<div>`` tag (default: ``'highlight'``).
        If you set this option, the default selector for `get_style_defs()`
        will be this class.

        .. versionadded:: 0.9
           If you select the ``'table'`` line numbers, the wrapping table will
           have a CSS class of this string plus ``'table'``, the default is
           accordingly ``'highlighttable'``.

    `cssstyles`
        Inline CSS styles for the wrapping ``<div>`` tag (default: ``''``).

    `prestyles`
        Inline CSS styles for the ``<pre>`` tag (default: ``''``).

        .. versionadded:: 0.11

    `cssfile`
        If the `full` option is true and this option is given, it must be the
        name of an external file. If the filename does not include an absolute
        path, the file's path will be assumed to be relative to the main output
        file's path, if the latter can be found. The stylesheet is then written
        to this file instead of the HTML file.

        .. versionadded:: 0.6

    `noclobber_cssfile`
        If `cssfile` is given and the specified file exists, the css file will
        not be overwritten. This allows the use of the `full` option in
        combination with a user specified css file. Default is ``False``.

        .. versionadded:: 1.1

    `linenos`
        If set to ``'table'``, output line numbers as a table with two cells,
        one containing the line numbers, the other the whole code.  This is
        copy-and-paste-friendly, but may cause alignment problems with some
        browsers or fonts.  If set to ``'inline'``, the line numbers will be
        integrated in the ``<pre>`` tag that contains the code (that setting
        is *new in Pygments 0.8*).

        For compatibility with Pygments 0.7 and earlier, every true value
        except ``'inline'`` means the same as ``'table'`` (in particular, that
        means also ``True``).

        The default value is ``False``, which means no line numbers at all.

        **Note:** with the default ("table") line number mechanism, the line
        numbers and code can have different line heights in Internet Explorer
        unless you give the enclosing ``<pre>`` tags an explicit ``line-height``
        CSS property (you get the default line spacing with ``line-height:
        125%``).

    `hl_lines`
        Specify a list of lines to be highlighted. The line numbers are always
        relative to the input (i.e. the first line is line 1) and are
        independent of `linenostart`.

        .. versionadded:: 0.11

    `linenostart`
        The line number for the first line (default: ``1``).

    `linenostep`
        If set to a number n > 1, only every nth line number is printed.

    `linenospecial`
        If set to a number n > 0, every nth line number is given the CSS
        class ``"special"`` (default: ``0``).

    `nobackground`
        If set to ``True``, the formatter won't output the background color
        for the wrapping element (this automatically defaults to ``False``
        when there is no wrapping element [eg: no argument for the
        `get_syntax_defs` method given]) (default: ``False``).

        .. versionadded:: 0.6

    `lineseparator`
        This string is output between lines of code. It defaults to ``"\n"``,
        which is enough to break a line inside ``<pre>`` tags, but you can
        e.g. set it to ``"<br>"`` to get HTML line breaks.

        .. versionadded:: 0.7

    `lineanchors`
        If set to a nonempty string, e.g. ``foo``, the formatter will wrap each
        output line in an anchor tag with an ``id`` (and `name`) of ``foo-linenumber``.
        This allows easy linking to certain lines.

        .. versionadded:: 0.9

    `linespans`
        If set to a nonempty string, e.g. ``foo``, the formatter will wrap each
        output line in a span tag with an ``id`` of ``foo-linenumber``.
        This allows easy access to lines via javascript.

        .. versionadded:: 1.6

    `anchorlinenos`
        If set to `True`, will wrap line numbers in <a> tags. Used in
        combination with `linenos` and `lineanchors`.

    `tagsfile`
        If set to the path of a ctags file, wrap names in anchor tags that
        link to their definitions. `lineanchors` should be used, and the
        tags file should specify line numbers (see the `-n` option to ctags).
        The tags file is assumed to be encoded in UTF-8.

        .. versionadded:: 1.6

    `tagurlformat`
        A string formatting pattern used to generate links to ctags definitions.
        Available variables are `%(path)s`, `%(fname)s` and `%(fext)s`.
        Defaults to an empty string, resulting in just `#prefix-number` links.

        .. versionadded:: 1.6

    `filename`
        A string used to generate a filename when rendering ``<pre>`` blocks,
        for example if displaying source code. If `linenos` is set to
        ``'table'`` then the filename will be rendered in an initial row
        containing a single `<th>` which spans both columns.

        .. versionadded:: 2.1

    `wrapcode`
        Wrap the code inside ``<pre>`` blocks using ``<code>``, as recommended
        by the HTML5 specification.

        .. versionadded:: 2.4

    `debug_token_types`
        Add ``title`` attributes to all token ``<span>`` tags that show the
        name of the token.

        .. versionadded:: 2.10


    **Subclassing the HTML formatter**

    .. versionadded:: 0.7

    The HTML formatter is now built in a way that allows easy subclassing, thus
    customizing the output HTML code. The `format()` method calls
    `self._format_lines()` which returns a generator that yields tuples of ``(1,
    line)``, where the ``1`` indicates that the ``line`` is a line of the
    formatted source code.

    If the `nowrap` option is set, the generator is the iterated over and the
    resulting HTML is output.

    Otherwise, `format()` calls `self.wrap()`, which wraps the generator with
    other generators. These may add some HTML code to the one generated by
    `_format_lines()`, either by modifying the lines generated by the latter,
    then yielding them again with ``(1, line)``, and/or by yielding other HTML
    code before or after the lines, with ``(0, html)``. The distinction between
    source lines and other code makes it possible to wrap the generator multiple
    times.

    The default `wrap()` implementation adds a ``<div>`` and a ``<pre>`` tag.

    A custom `HtmlFormatter` subclass could look like this:

    .. sourcecode:: python

        class CodeHtmlFormatter(HtmlFormatter):

            def wrap(self, source, *, include_div):
                return self._wrap_code(source)

            def _wrap_code(self, source):
                yield 0, '<code>'
                for i, t in source:
                    if i == 1:
                        # it's a line of formatted code
                        t += '<br>'
                    yield i, t
                yield 0, '</code>'

    This results in wrapping the formatted lines with a ``<code>`` tag, where the
    source lines are broken using ``<br>`` tags.

    After calling `wrap()`, the `format()` method also adds the "line numbers"
    and/or "full document" wrappers if the respective options are set. Then, all
    HTML yielded by the wrapped generator is output.
    """

    name = 'HTML'
    aliases = ['html']
    filenames = ['*.html', '*.htm']

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.title = self._decodeifneeded(self.title)
        self.nowrap = get_bool_opt(options, 'nowrap', False)
        self.noclasses = get_bool_opt(options, 'noclasses', False)
        self.classprefix = options.get('classprefix', '')
        self.cssclass = self._decodeifneeded(options.get('cssclass', 'highlight'))
        self.cssstyles = self._decodeifneeded(options.get('cssstyles', ''))
        self.prestyles = self._decodeifneeded(options.get('prestyles', ''))
        self.cssfile = self._decodeifneeded(options.get('cssfile', ''))
        self.noclobber_cssfile = get_bool_opt(options, 'noclobber_cssfile', False)
        self.tagsfile = self._decodeifneeded(options.get('tagsfile', ''))
        self.tagurlformat = self._decodeifneeded(options.get('tagurlformat', ''))
        self.filename = self._decodeifneeded(options.get('filename', ''))
        self.wrapcode = get_bool_opt(options, 'wrapcode', False)
        self.span_element_openers = {}
        self.debug_token_types = get_bool_opt(options, 'debug_token_types', False)

        if self.tagsfile:
            if not ctags:
                raise RuntimeError('The "ctags" package must to be installed '
                                   'to be able to use the "tagsfile" feature.')
            self._ctags = ctags.CTags(self.tagsfile)

        linenos = options.get('linenos', False)
        if linenos == 'inline':
            self.linenos = 2
        elif linenos:
            # compatibility with <= 0.7
            self.linenos = 1
        else:
            self.linenos = 0
        self.linenostart = abs(get_int_opt(options, 'linenostart', 1))
        self.linenostep = abs(get_int_opt(options, 'linenostep', 1))
        self.linenospecial = abs(get_int_opt(options, 'linenospecial', 0))
        self.nobackground = get_bool_opt(options, 'nobackground', False)
        self.lineseparator = options.get('lineseparator', '\n')
        self.lineanchors = options.get('lineanchors', '')
        self.linespans = options.get('linespans', '')
        self.anchorlinenos = get_bool_opt(options, 'anchorlinenos', False)
        self.hl_lines = set()
        for lineno in get_list_opt(options, 'hl_lines', []):
            try:
                self.hl_lines.add(int(lineno))
            except ValueError:
                pass

        self._create_stylesheet()

    def _get_css_class(self, ttype):
        """Return the css class of this token type prefixed with
        the classprefix option."""
        ttypeclass = _get_ttype_class(ttype)
        if ttypeclass:
            return self.classprefix + ttypeclass
        return ''

    def _get_css_classes(self, ttype):
        """Return the CSS classes of this token type prefixed with the classprefix option."""
        cls = self._get_css_class(ttype)
        while ttype not in STANDARD_TYPES:
            ttype = ttype.parent
            cls = self._get_css_class(ttype) + ' ' + cls
        return cls or ''

    def _get_css_inline_styles(self, ttype):
        """Return the inline CSS styles for this token type."""
        cclass = self.ttype2class.get(ttype)
        while cclass is None:
            ttype = ttype.parent
            cclass = self.ttype2class.get(ttype)
        return cclass or ''

    def _create_stylesheet(self):
        t2c = self.ttype2class = {Token: ''}
        c2s = self.class2style = {}
        for ttype, ndef in self.style:
            name = self._get_css_class(ttype)
            style = ''
            if ndef['color']:
                style += 'color: {}; '.format(webify(ndef['color']))
            if ndef['bold']:
                style += 'font-weight: bold; '
            if ndef['italic']:
                style += 'font-style: italic; '
            if ndef['underline']:
                style += 'text-decoration: underline; '
            if ndef['bgcolor']:
                style += 'background-color: {}; '.format(webify(ndef['bgcolor']))
            if ndef['border']:
                style += 'border: 1px solid {}; '.format(webify(ndef['border']))
            if style:
                t2c[ttype] = name
                # save len(ttype) to enable ordering the styles by
                # hierarchy (necessary for CSS cascading rules!)
                c2s[name] = (style[:-2], ttype, len(ttype))

    def get_style_defs(self, arg=None):
        """
        Return CSS style definitions for the classes produced by the current
        highlighting style. ``arg`` can be a string or list of selectors to
        insert before the token type classes.
        """
        style_lines = []

        style_lines.extend(self.get_linenos_style_defs())
        style_lines.extend(self.get_background_style_defs(arg))
        style_lines.extend(self.get_token_style_defs(arg))

        return '\n'.join(style_lines)

    def get_token_style_defs(self, arg=None):
        prefix = self.get_css_prefix(arg)

        styles = [
            (level, ttype, cls, style)
            for cls, (style, ttype, level) in self.class2style.items()
            if cls and style
        ]
        styles.sort()

        lines = [
            f'{prefix(cls)} {{ {style} }} /* {repr(ttype)[6:]} */'
            for (level, ttype, cls, style) in styles
        ]

        return lines

    def get_background_style_defs(self, arg=None):
        prefix = self.get_css_prefix(arg)
        bg_color = self.style.background_color
        hl_color = self.style.highlight_color

        lines = []

        if arg and not self.nobackground and bg_color is not None:
            text_style = ''
            if Text in self.ttype2class:
                text_style = ' ' + self.class2style[self.ttype2class[Text]][0]
            lines.insert(
                0, '{}{{ background: {};{} }}'.format(
                    prefix(''), bg_color, text_style
                )
            )
        if hl_color is not None:
            lines.insert(
                0, '{} {{ background-color: {} }}'.format(prefix('hll'), hl_color)
            )

        return lines

    def get_linenos_style_defs(self):
        lines = [
            f'pre {{ {self._pre_style} }}',
            f'td.linenos .normal {{ {self._linenos_style} }}',
            f'span.linenos {{ {self._linenos_style} }}',
            f'td.linenos .special {{ {self._linenos_special_style} }}',
            f'span.linenos.special {{ {self._linenos_special_style} }}',
        ]

        return lines

    def get_css_prefix(self, arg):
        if arg is None:
            arg = ('cssclass' in self.options and '.'+self.cssclass or '')
        if isinstance(arg, str):
            args = [arg]
        else:
            args = list(arg)

        def prefix(cls):
            if cls:
                cls = '.' + cls
            tmp = []
            for arg in args:
                tmp.append((arg and arg + ' ' or '') + cls)
            return ', '.join(tmp)

        return prefix

    @property
    def _pre_style(self):
        return 'line-height: 125%;'

    @property
    def _linenos_style(self):
        color = self.style.line_number_color
        background_color = self.style.line_number_background_color
        return f'color: {color}; background-color: {background_color}; padding-left: 5px; padding-right: 5px;'

    @property
    def _linenos_special_style(self):
        color = self.style.line_number_special_color
        background_color = self.style.line_number_special_background_color
        return f'color: {color}; background-color: {background_color}; padding-left: 5px; padding-right: 5px;'

    def _decodeifneeded(self, value):
        if isinstance(value, bytes):
            if self.encoding:
                return value.decode(self.encoding)
            return value.decode()
        return value

    def _wrap_full(self, inner, outfile):
        if self.cssfile:
            if os.path.isabs(self.cssfile):
                # it's an absolute filename
                cssfilename = self.cssfile
            else:
                try:
                    filename = outfile.name
                    if not filename or filename[0] == '<':
                        # pseudo files, e.g. name == '<fdopen>'
                        raise AttributeError
                    cssfilename = os.path.join(os.path.dirname(filename),
                                               self.cssfile)
                except AttributeError:
                    print('Note: Cannot determine output file name, '
                          'using current directory as base for the CSS file name',
                          file=sys.stderr)
                    cssfilename = self.cssfile
            # write CSS file only if noclobber_cssfile isn't given as an option.
            try:
                if not os.path.exists(cssfilename) or not self.noclobber_cssfile:
                    with open(cssfilename, "w", encoding="utf-8") as cf:
                        cf.write(CSSFILE_TEMPLATE %
                                 {'styledefs': self.get_style_defs('body')})
            except OSError as err:
                err.strerror = 'Error writing CSS file: ' + err.strerror
                raise

            yield 0, (DOC_HEADER_EXTERNALCSS %
                      dict(title=self.title,
                           cssfile=self.cssfile,
                           encoding=self.encoding))
        else:
            yield 0, (DOC_HEADER %
                      dict(title=self.title,
                           styledefs=self.get_style_defs('body'),
                           encoding=self.encoding))

        yield from inner
        yield 0, DOC_FOOTER

    def _wrap_tablelinenos(self, inner):
        dummyoutfile = StringIO()
        lncount = 0
        for t, line in inner:
            if t:
                lncount += 1
            dummyoutfile.write(line)

        fl = self.linenostart
        mw = len(str(lncount + fl - 1))
        sp = self.linenospecial
        st = self.linenostep
        anchor_name = self.lineanchors or self.linespans
        aln = self.anchorlinenos
        nocls = self.noclasses

        lines = []

        for i in range(fl, fl+lncount):
            print_line = i % st == 0
            special_line = sp and i % sp == 0

            if print_line:
                line = '%*d' % (mw, i)
                if aln:
                    line = '<a href="#%s-%d">%s</a>' % (anchor_name, i, line)
            else:
                line = ' ' * mw

            if nocls:
                if special_line:
                    style = f' style="{self._linenos_special_style}"'
                else:
                    style = f' style="{self._linenos_style}"'
            else:
                if special_line:
                    style = ' class="special"'
                else:
                    style = ' class="normal"'

            if style:
                line = f'<span{style}>{line}</span>'

            lines.append(line)

        ls = '\n'.join(lines)

        # If a filename was specified, we can't put it into the code table as it
        # would misalign the line numbers. Hence we emit a separate row for it.
        filename_tr = ""
        if self.filename:
            filename_tr = (
                '<tr><th colspan="2" class="filename">'
                '<span class="filename">' + self.filename + '</span>'
                '</th></tr>')

        # in case you wonder about the seemingly redundant <div> here: since the
        # content in the other cell also is wrapped in a div, some browsers in
        # some configurations seem to mess up the formatting...
        yield 0, (f'<table class="{self.cssclass}table">' + filename_tr +
            '<tr><td class="linenos"><div class="linenodiv"><pre>' +
            ls + '</pre></div></td><td class="code">')
        yield 0, '<div>'
        yield 0, dummyoutfile.getvalue()
        yield 0, '</div>'
        yield 0, '</td></tr></table>'


    def _wrap_inlinelinenos(self, inner):
        # need a list of lines since we need the width of a single number :(
        inner_lines = list(inner)
        sp = self.linenospecial
        st = self.linenostep
        num = self.linenostart
        mw = len(str(len(inner_lines) + num - 1))
        anchor_name = self.lineanchors or self.linespans
        aln = self.anchorlinenos
        nocls = self.noclasses

        for _, inner_line in inner_lines:
            print_line = num % st == 0
            special_line = sp and num % sp == 0

            if print_line:
                line = '%*d' % (mw, num)
            else:
                line = ' ' * mw

            if nocls:
                if special_line:
                    style = f' style="{self._linenos_special_style}"'
                else:
                    style = f' style="{self._linenos_style}"'
            else:
                if special_line:
                    style = ' class="linenos special"'
                else:
                    style = ' class="linenos"'

            if style:
                linenos = f'<span{style}>{line}</span>'
            else:
                linenos = line

            if aln:
                yield 1, ('<a href="#%s-%d">%s</a>' % (anchor_name, num, linenos) +
                          inner_line)
            else:
                yield 1, linenos + inner_line
            num += 1

    def _wrap_lineanchors(self, inner):
        s = self.lineanchors
        # subtract 1 since we have to increment i *before* yielding
        i = self.linenostart - 1
        for t, line in inner:
            if t:
                i += 1
                href = "" if self.linenos else ' href="#%s-%d"' % (s, i)
                yield 1, '<a id="%s-%d" name="%s-%d"%s></a>' % (s, i, s, i, href) + line
            else:
                yield 0, line

    def _wrap_linespans(self, inner):
        s = self.linespans
        i = self.linenostart - 1
        for t, line in inner:
            if t:
                i += 1
                yield 1, '<span id="%s-%d">%s</span>' % (s, i, line)
            else:
                yield 0, line

    def _wrap_div(self, inner):
        style = []
        if (self.noclasses and not self.nobackground and
                self.style.background_color is not None):
            style.append(f'background: {self.style.background_color}')
        if self.cssstyles:
            style.append(self.cssstyles)
        style = '; '.join(style)

        yield 0, ('<div' + (self.cssclass and f' class="{self.cssclass}"') +
                  (style and (f' style="{style}"')) + '>')
        yield from inner
        yield 0, '</div>\n'

    def _wrap_pre(self, inner):
        style = []
        if self.prestyles:
            style.append(self.prestyles)
        if self.noclasses:
            style.append(self._pre_style)
        style = '; '.join(style)

        if self.filename and self.linenos != 1:
            yield 0, ('<span class="filename">' + self.filename + '</span>')

        # the empty span here is to keep leading empty lines from being
        # ignored by HTML parsers
        yield 0, ('<pre' + (style and f' style="{style}"') + '><span></span>')
        yield from inner
        yield 0, '</pre>'

    def _wrap_code(self, inner):
        yield 0, '<code>'
        yield from inner
        yield 0, '</code>'

    @functools.lru_cache(maxsize=100)
    def _translate_parts(self, value):
        """HTML-escape a value and split it by newlines."""
        return value.translate(_escape_html_table).split('\n')

    def _format_lines(self, tokensource):
        """
        Just format the tokens, without any wrapping tags.
        Yield individual lines.
        """
        nocls = self.noclasses
        lsep = self.lineseparator
        tagsfile = self.tagsfile

        lspan = ''
        line = []
        for ttype, value in tokensource:
            try:
                cspan = self.span_element_openers[ttype]
            except KeyError:
                title = ' title="{}"'.format('.'.join(ttype)) if self.debug_token_types else ''
                if nocls:
                    css_style = self._get_css_inline_styles(ttype)
                    if css_style:
                        css_style = self.class2style[css_style][0]
                        cspan = f'<span style="{css_style}"{title}>'
                    else:
                        cspan = ''
                else:
                    css_class = self._get_css_classes(ttype)
                    if css_class:
                        cspan = f'<span class="{css_class}"{title}>'
                    else:
                        cspan = ''
                self.span_element_openers[ttype] = cspan

            parts = self._translate_parts(value)

            if tagsfile and ttype in Token.Name:
                filename, linenumber = self._lookup_ctag(value)
                if linenumber:
                    base, filename = os.path.split(filename)
                    if base:
                        base += '/'
                    filename, extension = os.path.splitext(filename)
                    url = self.tagurlformat % {'path': base, 'fname': filename,
                                               'fext': extension}
                    parts[0] = "<a href=\"%s#%s-%d\">%s" % \
                        (url, self.lineanchors, linenumber, parts[0])
                    parts[-1] = parts[-1] + "</a>"

            # for all but the last line
            for part in parts[:-1]:
                if line:
                    # Also check for part being non-empty, so we avoid creating
                    # empty <span> tags
                    if lspan != cspan and part:
                        line.extend(((lspan and '</span>'), cspan, part,
                                     (cspan and '</span>'), lsep))
                    else:  # both are the same, or the current part was empty
                        line.extend((part, (lspan and '</span>'), lsep))
                    yield 1, ''.join(line)
                    line = []
                elif part:
                    yield 1, ''.join((cspan, part, (cspan and '</span>'), lsep))
                else:
                    yield 1, lsep
            # for the last line
            if line and parts[-1]:
                if lspan != cspan:
                    line.extend(((lspan and '</span>'), cspan, parts[-1]))
                    lspan = cspan
                else:
                    line.append(parts[-1])
            elif parts[-1]:
                line = [cspan, parts[-1]]
                lspan = cspan
            # else we neither have to open a new span nor set lspan

        if line:
            line.extend(((lspan and '</span>'), lsep))
            yield 1, ''.join(line)

    def _lookup_ctag(self, token):
        entry = ctags.TagEntry()
        if self._ctags.find(entry, token.encode(), 0):
            return entry['file'].decode(), entry['lineNumber']
        else:
            return None, None

    def _highlight_lines(self, tokensource):
        """
        Highlighted the lines specified in the `hl_lines` option by
        post-processing the token stream coming from `_format_lines`.
        """
        hls = self.hl_lines

        for i, (t, value) in enumerate(tokensource):
            if t != 1:
                yield t, value
            if i + 1 in hls:  # i + 1 because Python indexes start at 0
                if self.noclasses:
                    style = ''
                    if self.style.highlight_color is not None:
                        style = (f' style="background-color: {self.style.highlight_color}"')
                    yield 1, f'<span{style}>{value}</span>'
                else:
                    yield 1, f'<span class="hll">{value}</span>'
            else:
                yield 1, value

    def wrap(self, source):
        """
        Wrap the ``source``, which is a generator yielding
        individual lines, in custom generators. See docstring
        for `format`. Can be overridden.
        """

        output = source
        if self.wrapcode:
            output = self._wrap_code(output)

        output = self._wrap_pre(output)

        return output

    def format_unencoded(self, tokensource, outfile):
        """
        The formatting process uses several nested generators; which of
        them are used is determined by the user's options.

        Each generator should take at least one argument, ``inner``,
        and wrap the pieces of text generated by this.

        Always yield 2-tuples: (code, text). If "code" is 1, the text
        is part of the original tokensource being highlighted, if it's
        0, the text is some piece of wrapping. This makes it possible to
        use several different wrappers that process the original source
        linewise, e.g. line number generators.
        """
        source = self._format_lines(tokensource)

        # As a special case, we wrap line numbers before line highlighting
        # so the line numbers get wrapped in the highlighting tag.
        if not self.nowrap and self.linenos == 2:
            source = self._wrap_inlinelinenos(source)

        if self.hl_lines:
            source = self._highlight_lines(source)

        if not self.nowrap:
            if self.lineanchors:
                source = self._wrap_lineanchors(source)
            if self.linespans:
                source = self._wrap_linespans(source)
            source = self.wrap(source)
            if self.linenos == 1:
                source = self._wrap_tablelinenos(source)
            source = self._wrap_div(source)
            if self.full:
                source = self._wrap_full(source, outfile)

        for t, piece in source:
            outfile.write(piece)

# === NexusCore/openenv\Lib\site-packages\tornado\ioloop.py ===
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

"""An I/O event loop for non-blocking sockets.

In Tornado 6.0, `.IOLoop` is a wrapper around the `asyncio` event loop, with a
slightly different interface. The `.IOLoop` interface is now provided primarily
for backwards compatibility; new code should generally use the `asyncio` event
loop interface directly. The `IOLoop.current` class method provides the
`IOLoop` instance corresponding to the running `asyncio` event loop.

"""

import asyncio
import concurrent.futures
import datetime
import functools
import numbers
import os
import sys
import time
import math
import random
import warnings
from inspect import isawaitable

from tornado.concurrent import (
    Future,
    is_future,
    chain_future,
    future_set_exc_info,
    future_add_done_callback,
)
from tornado.log import app_log
from tornado.util import Configurable, TimeoutError, import_object

import typing
from typing import Union, Any, Type, Optional, Callable, TypeVar, Tuple, Awaitable

if typing.TYPE_CHECKING:
    from typing import Dict, List, Set, TypedDict  # noqa: F401

    from typing_extensions import Protocol
else:
    Protocol = object


class _Selectable(Protocol):
    def fileno(self) -> int:
        pass

    def close(self) -> None:
        pass


_T = TypeVar("_T")
_S = TypeVar("_S", bound=_Selectable)


class IOLoop(Configurable):
    """An I/O event loop.

    As of Tornado 6.0, `IOLoop` is a wrapper around the `asyncio` event loop.

    Example usage for a simple TCP server:

    .. testcode::

        import asyncio
        import errno
        import functools
        import socket

        import tornado
        from tornado.iostream import IOStream

        async def handle_connection(connection, address):
            stream = IOStream(connection)
            message = await stream.read_until_close()
            print("message from client:", message.decode().strip())

        def connection_ready(sock, fd, events):
            while True:
                try:
                    connection, address = sock.accept()
                except BlockingIOError:
                    return
                connection.setblocking(0)
                io_loop = tornado.ioloop.IOLoop.current()
                io_loop.spawn_callback(handle_connection, connection, address)

        async def main():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setblocking(0)
            sock.bind(("", 8888))
            sock.listen(128)

            io_loop = tornado.ioloop.IOLoop.current()
            callback = functools.partial(connection_ready, sock)
            io_loop.add_handler(sock.fileno(), callback, io_loop.READ)
            await asyncio.Event().wait()

        if __name__ == "__main__":
            asyncio.run(main())

    Most applications should not attempt to construct an `IOLoop` directly,
    and instead initialize the `asyncio` event loop and use `IOLoop.current()`.
    In some cases, such as in test frameworks when initializing an `IOLoop`
    to be run in a secondary thread, it may be appropriate to construct
    an `IOLoop` with ``IOLoop(make_current=False)``.

    In general, an `IOLoop` cannot survive a fork or be shared across processes
    in any way. When multiple processes are being used, each process should
    create its own `IOLoop`, which also implies that any objects which depend on
    the `IOLoop` (such as `.AsyncHTTPClient`) must also be created in the child
    processes. As a guideline, anything that starts processes (including the
    `tornado.process` and `multiprocessing` modules) should do so as early as
    possible, ideally the first thing the application does after loading its
    configuration, and *before* any calls to `.IOLoop.start` or `asyncio.run`.

    .. versionchanged:: 4.2
       Added the ``make_current`` keyword argument to the `IOLoop`
       constructor.

    .. versionchanged:: 5.0

       Uses the `asyncio` event loop by default. The ``IOLoop.configure`` method
       cannot be used on Python 3 except to redundantly specify the `asyncio`
       event loop.

    .. versionchanged:: 6.3
       ``make_current=True`` is now the default when creating an IOLoop -
       previously the default was to make the event loop current if there wasn't
       already a current one.
    """

    # These constants were originally based on constants from the epoll module.
    NONE = 0
    READ = 0x001
    WRITE = 0x004
    ERROR = 0x018

    # In Python 3, _ioloop_for_asyncio maps from asyncio loops to IOLoops.
    _ioloop_for_asyncio = dict()  # type: Dict[asyncio.AbstractEventLoop, IOLoop]

    # Maintain a set of all pending tasks to follow the warning in the docs
    # of asyncio.create_tasks:
    # https://docs.python.org/3.11/library/asyncio-task.html#asyncio.create_task
    # This ensures that all pending tasks have a strong reference so they
    # will not be garbage collected before they are finished.
    # (Thus avoiding "task was destroyed but it is pending" warnings)
    # An analogous change has been proposed in cpython for 3.13:
    # https://github.com/python/cpython/issues/91887
    # If that change is accepted, this can eventually be removed.
    # If it is not, we will consider the rationale and may remove this.
    _pending_tasks = set()  # type: Set[Future]

    @classmethod
    def configure(
        cls, impl: "Union[None, str, Type[Configurable]]", **kwargs: Any
    ) -> None:
        from tornado.platform.asyncio import BaseAsyncIOLoop

        if isinstance(impl, str):
            impl = import_object(impl)
        if isinstance(impl, type) and not issubclass(impl, BaseAsyncIOLoop):
            raise RuntimeError("only AsyncIOLoop is allowed when asyncio is available")
        super().configure(impl, **kwargs)

    @staticmethod
    def instance() -> "IOLoop":
        """Deprecated alias for `IOLoop.current()`.

        .. versionchanged:: 5.0

           Previously, this method returned a global singleton
           `IOLoop`, in contrast with the per-thread `IOLoop` returned
           by `current()`. In nearly all cases the two were the same
           (when they differed, it was generally used from non-Tornado
           threads to communicate back to the main thread's `IOLoop`).
           This distinction is not present in `asyncio`, so in order
           to facilitate integration with that package `instance()`
           was changed to be an alias to `current()`. Applications
           using the cross-thread communications aspect of
           `instance()` should instead set their own global variable
           to point to the `IOLoop` they want to use.

        .. deprecated:: 5.0
        """
        return IOLoop.current()

    def install(self) -> None:
        """Deprecated alias for `make_current()`.

        .. versionchanged:: 5.0

           Previously, this method would set this `IOLoop` as the
           global singleton used by `IOLoop.instance()`. Now that
           `instance()` is an alias for `current()`, `install()`
           is an alias for `make_current()`.

        .. deprecated:: 5.0
        """
        self.make_current()

    @staticmethod
    def clear_instance() -> None:
        """Deprecated alias for `clear_current()`.

        .. versionchanged:: 5.0

           Previously, this method would clear the `IOLoop` used as
           the global singleton by `IOLoop.instance()`. Now that
           `instance()` is an alias for `current()`,
           `clear_instance()` is an alias for `clear_current()`.

        .. deprecated:: 5.0

        """
        IOLoop.clear_current()

    @typing.overload
    @staticmethod
    def current() -> "IOLoop":
        pass

    @typing.overload
    @staticmethod
    def current(instance: bool = True) -> Optional["IOLoop"]:  # noqa: F811
        pass

    @staticmethod
    def current(instance: bool = True) -> Optional["IOLoop"]:  # noqa: F811
        """Returns the current thread's `IOLoop`.

        If an `IOLoop` is currently running or has been marked as
        current by `make_current`, returns that instance.  If there is
        no current `IOLoop` and ``instance`` is true, creates one.

        .. versionchanged:: 4.1
           Added ``instance`` argument to control the fallback to
           `IOLoop.instance()`.
        .. versionchanged:: 5.0
           On Python 3, control of the current `IOLoop` is delegated
           to `asyncio`, with this and other methods as pass-through accessors.
           The ``instance`` argument now controls whether an `IOLoop`
           is created automatically when there is none, instead of
           whether we fall back to `IOLoop.instance()` (which is now
           an alias for this method). ``instance=False`` is deprecated,
           since even if we do not create an `IOLoop`, this method
           may initialize the asyncio loop.

        .. deprecated:: 6.2
           It is deprecated to call ``IOLoop.current()`` when no `asyncio`
           event loop is running.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            if not instance:
                return None
            # Create a new asyncio event loop for this thread.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            return IOLoop._ioloop_for_asyncio[loop]
        except KeyError:
            if instance:
                from tornado.platform.asyncio import AsyncIOMainLoop

                current = AsyncIOMainLoop()  # type: Optional[IOLoop]
            else:
                current = None
        return current

    def make_current(self) -> None:
        """Makes this the `IOLoop` for the current thread.

        An `IOLoop` automatically becomes current for its thread
        when it is started, but it is sometimes useful to call
        `make_current` explicitly before starting the `IOLoop`,
        so that code run at startup time can find the right
        instance.

        .. versionchanged:: 4.1
           An `IOLoop` created while there is no current `IOLoop`
           will automatically become current.

        .. versionchanged:: 5.0
           This method also sets the current `asyncio` event loop.

        .. deprecated:: 6.2
           Setting and clearing the current event loop through Tornado is
           deprecated. Use ``asyncio.set_event_loop`` instead if you need this.
        """
        warnings.warn(
            "make_current is deprecated; start the event loop first",
            DeprecationWarning,
            stacklevel=2,
        )
        self._make_current()

    def _make_current(self) -> None:
        # The asyncio event loops override this method.
        raise NotImplementedError()

    @staticmethod
    def clear_current() -> None:
        """Clears the `IOLoop` for the current thread.

        Intended primarily for use by test frameworks in between tests.

        .. versionchanged:: 5.0
           This method also clears the current `asyncio` event loop.
        .. deprecated:: 6.2
        """
        warnings.warn(
            "clear_current is deprecated",
            DeprecationWarning,
            stacklevel=2,
        )
        IOLoop._clear_current()

    @staticmethod
    def _clear_current() -> None:
        old = IOLoop.current(instance=False)
        if old is not None:
            old._clear_current_hook()

    def _clear_current_hook(self) -> None:
        """Instance method called when an IOLoop ceases to be current.

        May be overridden by subclasses as a counterpart to make_current.
        """
        pass

    @classmethod
    def configurable_base(cls) -> Type[Configurable]:
        return IOLoop

    @classmethod
    def configurable_default(cls) -> Type[Configurable]:
        from tornado.platform.asyncio import AsyncIOLoop

        return AsyncIOLoop

    def initialize(self, make_current: bool = True) -> None:
        if make_current:
            self._make_current()

    def close(self, all_fds: bool = False) -> None:
        """Closes the `IOLoop`, freeing any resources used.

        If ``all_fds`` is true, all file descriptors registered on the
        IOLoop will be closed (not just the ones created by the
        `IOLoop` itself).

        Many applications will only use a single `IOLoop` that runs for the
        entire lifetime of the process.  In that case closing the `IOLoop`
        is not necessary since everything will be cleaned up when the
        process exits.  `IOLoop.close` is provided mainly for scenarios
        such as unit tests, which create and destroy a large number of
        ``IOLoops``.

        An `IOLoop` must be completely stopped before it can be closed.  This
        means that `IOLoop.stop()` must be called *and* `IOLoop.start()` must
        be allowed to return before attempting to call `IOLoop.close()`.
        Therefore the call to `close` will usually appear just after
        the call to `start` rather than near the call to `stop`.

        .. versionchanged:: 3.1
           If the `IOLoop` implementation supports non-integer objects
           for "file descriptors", those objects will have their
           ``close`` method when ``all_fds`` is true.
        """
        raise NotImplementedError()

    @typing.overload
    def add_handler(
        self, fd: int, handler: Callable[[int, int], None], events: int
    ) -> None:
        pass

    @typing.overload  # noqa: F811
    def add_handler(
        self, fd: _S, handler: Callable[[_S, int], None], events: int
    ) -> None:
        pass

    def add_handler(  # noqa: F811
        self, fd: Union[int, _Selectable], handler: Callable[..., None], events: int
    ) -> None:
        """Registers the given handler to receive the given events for ``fd``.

        The ``fd`` argument may either be an integer file descriptor or
        a file-like object with a ``fileno()`` and ``close()`` method.

        The ``events`` argument is a bitwise or of the constants
        ``IOLoop.READ``, ``IOLoop.WRITE``, and ``IOLoop.ERROR``.

        When an event occurs, ``handler(fd, events)`` will be run.

        .. versionchanged:: 4.0
           Added the ability to pass file-like objects in addition to
           raw file descriptors.
        """
        raise NotImplementedError()

    def update_handler(self, fd: Union[int, _Selectable], events: int) -> None:
        """Changes the events we listen for ``fd``.

        .. versionchanged:: 4.0
           Added the ability to pass file-like objects in addition to
           raw file descriptors.
        """
        raise NotImplementedError()

    def remove_handler(self, fd: Union[int, _Selectable]) -> None:
        """Stop listening for events on ``fd``.

        .. versionchanged:: 4.0
           Added the ability to pass file-like objects in addition to
           raw file descriptors.
        """
        raise NotImplementedError()

    def start(self) -> None:
        """Starts the I/O loop.

        The loop will run until one of the callbacks calls `stop()`, which
        will make the loop stop after the current event iteration completes.
        """
        raise NotImplementedError()

    def stop(self) -> None:
        """Stop the I/O loop.

        If the event loop is not currently running, the next call to `start()`
        will return immediately.

        Note that even after `stop` has been called, the `IOLoop` is not
        completely stopped until `IOLoop.start` has also returned.
        Some work that was scheduled before the call to `stop` may still
        be run before the `IOLoop` shuts down.
        """
        raise NotImplementedError()

    def run_sync(self, func: Callable, timeout: Optional[float] = None) -> Any:
        """Starts the `IOLoop`, runs the given function, and stops the loop.

        The function must return either an awaitable object or
        ``None``. If the function returns an awaitable object, the
        `IOLoop` will run until the awaitable is resolved (and
        `run_sync()` will return the awaitable's result). If it raises
        an exception, the `IOLoop` will stop and the exception will be
        re-raised to the caller.

        The keyword-only argument ``timeout`` may be used to set
        a maximum duration for the function.  If the timeout expires,
        a `asyncio.TimeoutError` is raised.

        This method is useful to allow asynchronous calls in a
        ``main()`` function::

            async def main():
                # do stuff...

            if __name__ == '__main__':
                IOLoop.current().run_sync(main)

        .. versionchanged:: 4.3
           Returning a non-``None``, non-awaitable value is now an error.

        .. versionchanged:: 5.0
           If a timeout occurs, the ``func`` coroutine will be cancelled.

        .. versionchanged:: 6.2
           ``tornado.util.TimeoutError`` is now an alias to ``asyncio.TimeoutError``.
        """
        if typing.TYPE_CHECKING:
            FutureCell = TypedDict(  # noqa: F841
                "FutureCell", {"future": Optional[Future], "timeout_called": bool}
            )
        future_cell = {"future": None, "timeout_called": False}  # type: FutureCell

        def run() -> None:
            try:
                result = func()
                if result is not None:
                    from tornado.gen import convert_yielded

                    result = convert_yielded(result)
            except Exception:
                fut = Future()  # type: Future[Any]
                future_cell["future"] = fut
                future_set_exc_info(fut, sys.exc_info())
            else:
                if is_future(result):
                    future_cell["future"] = result
                else:
                    fut = Future()
                    future_cell["future"] = fut
                    fut.set_result(result)
            assert future_cell["future"] is not None
            self.add_future(future_cell["future"], lambda future: self.stop())

        self.add_callback(run)
        if timeout is not None:

            def timeout_callback() -> None:
                # signal that timeout is triggered
                future_cell["timeout_called"] = True
                # If we can cancel the future, do so and wait on it. If not,
                # Just stop the loop and return with the task still pending.
                # (If we neither cancel nor wait for the task, a warning
                # will be logged).
                assert future_cell["future"] is not None
                if not future_cell["future"].cancel():
                    self.stop()

            timeout_handle = self.add_timeout(self.time() + timeout, timeout_callback)
        self.start()
        if timeout is not None:
            self.remove_timeout(timeout_handle)
        assert future_cell["future"] is not None
        if future_cell["future"].cancelled() or not future_cell["future"].done():
            if future_cell["timeout_called"]:
                raise TimeoutError("Operation timed out after %s seconds" % timeout)
            else:
                # timeout not called; maybe stop() was called explicitly
                # or some other cancellation
                raise RuntimeError("Event loop stopped before Future completed.")
        return future_cell["future"].result()

    def time(self) -> float:
        """Returns the current time according to the `IOLoop`'s clock.

        The return value is a floating-point number relative to an
        unspecified time in the past.

        Historically, the IOLoop could be customized to use e.g.
        `time.monotonic` instead of `time.time`, but this is not
        currently supported and so this method is equivalent to
        `time.time`.

        """
        return time.time()

    def add_timeout(
        self,
        deadline: Union[float, datetime.timedelta],
        callback: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> object:
        """Runs the ``callback`` at the time ``deadline`` from the I/O loop.

        Returns an opaque handle that may be passed to
        `remove_timeout` to cancel.

        ``deadline`` may be a number denoting a time (on the same
        scale as `IOLoop.time`, normally `time.time`), or a
        `datetime.timedelta` object for a deadline relative to the
        current time.  Since Tornado 4.0, `call_later` is a more
        convenient alternative for the relative case since it does not
        require a timedelta object.

        Note that it is not safe to call `add_timeout` from other threads.
        Instead, you must use `add_callback` to transfer control to the
        `IOLoop`'s thread, and then call `add_timeout` from there.

        Subclasses of IOLoop must implement either `add_timeout` or
        `call_at`; the default implementations of each will call
        the other.  `call_at` is usually easier to implement, but
        subclasses that wish to maintain compatibility with Tornado
        versions prior to 4.0 must use `add_timeout` instead.

        .. versionchanged:: 4.0
           Now passes through ``*args`` and ``**kwargs`` to the callback.
        """
        if isinstance(deadline, numbers.Real):
            return self.call_at(deadline, callback, *args, **kwargs)
        elif isinstance(deadline, datetime.timedelta):
            return self.call_at(
                self.time() + deadline.total_seconds(), callback, *args, **kwargs
            )
        else:
            raise TypeError("Unsupported deadline %r" % deadline)

    def call_later(
        self, delay: float, callback: Callable, *args: Any, **kwargs: Any
    ) -> object:
        """Runs the ``callback`` after ``delay`` seconds have passed.

        Returns an opaque handle that may be passed to `remove_timeout`
        to cancel.  Note that unlike the `asyncio` method of the same
        name, the returned object does not have a ``cancel()`` method.

        See `add_timeout` for comments on thread-safety and subclassing.

        .. versionadded:: 4.0
        """
        return self.call_at(self.time() + delay, callback, *args, **kwargs)

    def call_at(
        self, when: float, callback: Callable, *args: Any, **kwargs: Any
    ) -> object:
        """Runs the ``callback`` at the absolute time designated by ``when``.

        ``when`` must be a number using the same reference point as
        `IOLoop.time`.

        Returns an opaque handle that may be passed to `remove_timeout`
        to cancel.  Note that unlike the `asyncio` method of the same
        name, the returned object does not have a ``cancel()`` method.

        See `add_timeout` for comments on thread-safety and subclassing.

        .. versionadded:: 4.0
        """
        return self.add_timeout(when, callback, *args, **kwargs)

    def remove_timeout(self, timeout: object) -> None:
        """Cancels a pending timeout.

        The argument is a handle as returned by `add_timeout`.  It is
        safe to call `remove_timeout` even if the callback has already
        been run.
        """
        raise NotImplementedError()

    def add_callback(self, callback: Callable, *args: Any, **kwargs: Any) -> None:
        """Calls the given callback on the next I/O loop iteration.

        It is safe to call this method from any thread at any time,
        except from a signal handler.  Note that this is the **only**
        method in `IOLoop` that makes this thread-safety guarantee; all
        other interaction with the `IOLoop` must be done from that
        `IOLoop`'s thread.  `add_callback()` may be used to transfer
        control from other threads to the `IOLoop`'s thread.
        """
        raise NotImplementedError()

    def add_callback_from_signal(
        self, callback: Callable, *args: Any, **kwargs: Any
    ) -> None:
        """Calls the given callback on the next I/O loop iteration.

        Intended to be afe for use from a Python signal handler; should not be
        used otherwise.

        .. deprecated:: 6.4
           Use ``asyncio.AbstractEventLoop.add_signal_handler`` instead.
           This method is suspected to have been broken since Tornado 5.0 and
           will be removed in version 7.0.
        """
        raise NotImplementedError()

    def spawn_callback(self, callback: Callable, *args: Any, **kwargs: Any) -> None:
        """Calls the given callback on the next IOLoop iteration.

        As of Tornado 6.0, this method is equivalent to `add_callback`.

        .. versionadded:: 4.0
        """
        self.add_callback(callback, *args, **kwargs)

    def add_future(
        self,
        future: "Union[Future[_T], concurrent.futures.Future[_T]]",
        callback: Callable[["Future[_T]"], None],
    ) -> None:
        """Schedules a callback on the ``IOLoop`` when the given
        `.Future` is finished.

        The callback is invoked with one argument, the
        `.Future`.

        This method only accepts `.Future` objects and not other
        awaitables (unlike most of Tornado where the two are
        interchangeable).
        """
        if isinstance(future, Future):
            # Note that we specifically do not want the inline behavior of
            # tornado.concurrent.future_add_done_callback. We always want
            # this callback scheduled on the next IOLoop iteration (which
            # asyncio.Future always does).
            #
            # Wrap the callback in self._run_callback so we control
            # the error logging (i.e. it goes to tornado.log.app_log
            # instead of asyncio's log).
            future.add_done_callback(
                lambda f: self._run_callback(functools.partial(callback, f))
            )
        else:
            assert is_future(future)
            # For concurrent futures, we use self.add_callback, so
            # it's fine if future_add_done_callback inlines that call.
            future_add_done_callback(future, lambda f: self.add_callback(callback, f))

    def run_in_executor(
        self,
        executor: Optional[concurrent.futures.Executor],
        func: Callable[..., _T],
        *args: Any,
    ) -> "Future[_T]":
        """Runs a function in a ``concurrent.futures.Executor``. If
        ``executor`` is ``None``, the IO loop's default executor will be used.

        Use `functools.partial` to pass keyword arguments to ``func``.

        .. versionadded:: 5.0
        """
        if executor is None:
            if not hasattr(self, "_executor"):
                from tornado.process import cpu_count

                self._executor = concurrent.futures.ThreadPoolExecutor(
                    max_workers=(cpu_count() * 5)
                )  # type: concurrent.futures.Executor
            executor = self._executor
        c_future = executor.submit(func, *args)
        # Concurrent Futures are not usable with await. Wrap this in a
        # Tornado Future instead, using self.add_future for thread-safety.
        t_future = Future()  # type: Future[_T]
        self.add_future(c_future, lambda f: chain_future(f, t_future))
        return t_future

    def set_default_executor(self, executor: concurrent.futures.Executor) -> None:
        """Sets the default executor to use with :meth:`run_in_executor`.

        .. versionadded:: 5.0
        """
        self._executor = executor

    def _run_callback(self, callback: Callable[[], Any]) -> None:
        """Runs a callback with error handling.

        .. versionchanged:: 6.0

           CancelledErrors are no longer logged.
        """
        try:
            ret = callback()
            if ret is not None:
                from tornado import gen

                # Functions that return Futures typically swallow all
                # exceptions and store them in the Future.  If a Future
                # makes it out to the IOLoop, ensure its exception (if any)
                # gets logged too.
                try:
                    ret = gen.convert_yielded(ret)
                except gen.BadYieldError:
                    # It's not unusual for add_callback to be used with
                    # methods returning a non-None and non-yieldable
                    # result, which should just be ignored.
                    pass
                else:
                    self.add_future(ret, self._discard_future_result)
        except asyncio.CancelledError:
            pass
        except Exception:
            app_log.error("Exception in callback %r", callback, exc_info=True)

    def _discard_future_result(self, future: Future) -> None:
        """Avoid unhandled-exception warnings from spawned coroutines."""
        future.result()

    def split_fd(
        self, fd: Union[int, _Selectable]
    ) -> Tuple[int, Union[int, _Selectable]]:
        # """Returns an (fd, obj) pair from an ``fd`` parameter.

        # We accept both raw file descriptors and file-like objects as
        # input to `add_handler` and related methods.  When a file-like
        # object is passed, we must retain the object itself so we can
        # close it correctly when the `IOLoop` shuts down, but the
        # poller interfaces favor file descriptors (they will accept
        # file-like objects and call ``fileno()`` for you, but they
        # always return the descriptor itself).

        # This method is provided for use by `IOLoop` subclasses and should
        # not generally be used by application code.

        # .. versionadded:: 4.0
        # """
        if isinstance(fd, int):
            return fd, fd
        return fd.fileno(), fd

    def close_fd(self, fd: Union[int, _Selectable]) -> None:
        # """Utility method to close an ``fd``.

        # If ``fd`` is a file-like object, we close it directly; otherwise
        # we use `os.close`.

        # This method is provided for use by `IOLoop` subclasses (in
        # implementations of ``IOLoop.close(all_fds=True)`` and should
        # not generally be used by application code.

        # .. versionadded:: 4.0
        # """
        try:
            if isinstance(fd, int):
                os.close(fd)
            else:
                fd.close()
        except OSError:
            pass

    def _register_task(self, f: Future) -> None:
        self._pending_tasks.add(f)

    def _unregister_task(self, f: Future) -> None:
        self._pending_tasks.discard(f)


class _Timeout:
    """An IOLoop timeout, a UNIX timestamp and a callback"""

    # Reduce memory overhead when there are lots of pending callbacks
    __slots__ = ["deadline", "callback", "tdeadline"]

    def __init__(
        self, deadline: float, callback: Callable[[], None], io_loop: IOLoop
    ) -> None:
        if not isinstance(deadline, numbers.Real):
            raise TypeError("Unsupported deadline %r" % deadline)
        self.deadline = deadline
        self.callback = callback
        self.tdeadline = (
            deadline,
            next(io_loop._timeout_counter),
        )  # type: Tuple[float, int]

    # Comparison methods to sort by deadline, with object id as a tiebreaker
    # to guarantee a consistent ordering.  The heapq module uses __le__
    # in python2.5, and __lt__ in 2.6+ (sort() and most other comparisons
    # use __lt__).
    def __lt__(self, other: "_Timeout") -> bool:
        return self.tdeadline < other.tdeadline

    def __le__(self, other: "_Timeout") -> bool:
        return self.tdeadline <= other.tdeadline


class PeriodicCallback:
    """Schedules the given callback to be called periodically.

    The callback is called every ``callback_time`` milliseconds when
    ``callback_time`` is a float. Note that the timeout is given in
    milliseconds, while most other time-related functions in Tornado use
    seconds. ``callback_time`` may alternatively be given as a
    `datetime.timedelta` object.

    If ``jitter`` is specified, each callback time will be randomly selected
    within a window of ``jitter * callback_time`` milliseconds.
    Jitter can be used to reduce alignment of events with similar periods.
    A jitter of 0.1 means allowing a 10% variation in callback time.
    The window is centered on ``callback_time`` so the total number of calls
    within a given interval should not be significantly affected by adding
    jitter.

    If the callback runs for longer than ``callback_time`` milliseconds,
    subsequent invocations will be skipped to get back on schedule.

    `start` must be called after the `PeriodicCallback` is created.

    .. versionchanged:: 5.0
       The ``io_loop`` argument (deprecated since version 4.1) has been removed.

    .. versionchanged:: 5.1
       The ``jitter`` argument is added.

    .. versionchanged:: 6.2
       If the ``callback`` argument is a coroutine, and a callback runs for
       longer than ``callback_time``, subsequent invocations will be skipped.
       Previously this was only true for regular functions, not coroutines,
       which were "fire-and-forget" for `PeriodicCallback`.

       The ``callback_time`` argument now accepts `datetime.timedelta` objects,
       in addition to the previous numeric milliseconds.
    """

    def __init__(
        self,
        callback: Callable[[], Optional[Awaitable]],
        callback_time: Union[datetime.timedelta, float],
        jitter: float = 0,
    ) -> None:
        self.callback = callback
        if isinstance(callback_time, datetime.timedelta):
            self.callback_time = callback_time / datetime.timedelta(milliseconds=1)
        else:
            if callback_time <= 0:
                raise ValueError("Periodic callback must have a positive callback_time")
            self.callback_time = callback_time
        self.jitter = jitter
        self._running = False
        self._timeout = None  # type: object

    def start(self) -> None:
        """Starts the timer."""
        # Looking up the IOLoop here allows to first instantiate the
        # PeriodicCallback in another thread, then start it using
        # IOLoop.add_callback().
        self.io_loop = IOLoop.current()
        self._running = True
        self._next_timeout = self.io_loop.time()
        self._schedule_next()

    def stop(self) -> None:
        """Stops the timer."""
        self._running = False
        if self._timeout is not None:
            self.io_loop.remove_timeout(self._timeout)
            self._timeout = None

    def is_running(self) -> bool:
        """Returns ``True`` if this `.PeriodicCallback` has been started.

        .. versionadded:: 4.1
        """
        return self._running

    async def _run(self) -> None:
        if not self._running:
            return
        try:
            val = self.callback()
            if val is not None and isawaitable(val):
                await val
        except Exception:
            app_log.error("Exception in callback %r", self.callback, exc_info=True)
        finally:
            self._schedule_next()

    def _schedule_next(self) -> None:
        if self._running:
            self._update_next(self.io_loop.time())
            self._timeout = self.io_loop.add_timeout(self._next_timeout, self._run)

    def _update_next(self, current_time: float) -> None:
        callback_time_sec = self.callback_time / 1000.0
        if self.jitter:
            # apply jitter fraction
            callback_time_sec *= 1 + (self.jitter * (random.random() - 0.5))
        if self._next_timeout <= current_time:
            # The period should be measured from the start of one call
            # to the start of the next. If one call takes too long,
            # skip cycles to get back to a multiple of the original
            # schedule.
            self._next_timeout += (
                math.floor((current_time - self._next_timeout) / callback_time_sec) + 1
            ) * callback_time_sec
        else:
            # If the clock moved backwards, ensure we advance the next
            # timeout instead of recomputing the same value again.
            # This may result in long gaps between callbacks if the
            # clock jumps backwards by a lot, but the far more common
            # scenario is a small NTP adjustment that should just be
            # ignored.
            #
            # Note that on some systems if time.time() runs slower
            # than time.monotonic() (most common on windows), we
            # effectively experience a small backwards time jump on
            # every iteration because PeriodicCallback uses
            # time.time() while asyncio schedules callbacks using
            # time.monotonic().
            # https://github.com/tornadoweb/tornado/issues/2333
            self._next_timeout += callback_time_sec

# === NexusCore/openenv\Lib\site-packages\psutil\_common.py ===
# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common objects shared by __init__.py and _ps*.py modules."""

# Note: this module is imported by setup.py so it should not import
# psutil or third-party modules.

from __future__ import division
from __future__ import print_function

import collections
import contextlib
import errno
import functools
import os
import socket
import stat
import sys
import threading
import warnings
from collections import namedtuple
from socket import AF_INET
from socket import SOCK_DGRAM
from socket import SOCK_STREAM


try:
    from socket import AF_INET6
except ImportError:
    AF_INET6 = None
try:
    from socket import AF_UNIX
except ImportError:
    AF_UNIX = None


# can't take it from _common.py as this script is imported by setup.py
PY3 = sys.version_info[0] >= 3
if PY3:
    import enum
else:
    enum = None


PSUTIL_DEBUG = bool(os.getenv('PSUTIL_DEBUG'))
_DEFAULT = object()

# fmt: off
__all__ = [
    # OS constants
    'FREEBSD', 'BSD', 'LINUX', 'NETBSD', 'OPENBSD', 'MACOS', 'OSX', 'POSIX',
    'SUNOS', 'WINDOWS',
    # connection constants
    'CONN_CLOSE', 'CONN_CLOSE_WAIT', 'CONN_CLOSING', 'CONN_ESTABLISHED',
    'CONN_FIN_WAIT1', 'CONN_FIN_WAIT2', 'CONN_LAST_ACK', 'CONN_LISTEN',
    'CONN_NONE', 'CONN_SYN_RECV', 'CONN_SYN_SENT', 'CONN_TIME_WAIT',
    # net constants
    'NIC_DUPLEX_FULL', 'NIC_DUPLEX_HALF', 'NIC_DUPLEX_UNKNOWN',
    # process status constants
    'STATUS_DEAD', 'STATUS_DISK_SLEEP', 'STATUS_IDLE', 'STATUS_LOCKED',
    'STATUS_RUNNING', 'STATUS_SLEEPING', 'STATUS_STOPPED', 'STATUS_SUSPENDED',
    'STATUS_TRACING_STOP', 'STATUS_WAITING', 'STATUS_WAKE_KILL',
    'STATUS_WAKING', 'STATUS_ZOMBIE', 'STATUS_PARKED',
    # other constants
    'ENCODING', 'ENCODING_ERRS', 'AF_INET6',
    # named tuples
    'pconn', 'pcputimes', 'pctxsw', 'pgids', 'pio', 'pionice', 'popenfile',
    'pthread', 'puids', 'sconn', 'scpustats', 'sdiskio', 'sdiskpart',
    'sdiskusage', 'snetio', 'snicaddr', 'snicstats', 'sswap', 'suser',
    # utility functions
    'conn_tmap', 'deprecated_method', 'isfile_strict', 'memoize',
    'parse_environ_block', 'path_exists_strict', 'usage_percent',
    'supports_ipv6', 'sockfam_to_enum', 'socktype_to_enum', "wrap_numbers",
    'open_text', 'open_binary', 'cat', 'bcat',
    'bytes2human', 'conn_to_ntuple', 'debug',
    # shell utils
    'hilite', 'term_supports_colors', 'print_color',
]
# fmt: on


# ===================================================================
# --- OS constants
# ===================================================================


POSIX = os.name == "posix"
WINDOWS = os.name == "nt"
LINUX = sys.platform.startswith("linux")
MACOS = sys.platform.startswith("darwin")
OSX = MACOS  # deprecated alias
FREEBSD = sys.platform.startswith(("freebsd", "midnightbsd"))
OPENBSD = sys.platform.startswith("openbsd")
NETBSD = sys.platform.startswith("netbsd")
BSD = FREEBSD or OPENBSD or NETBSD
SUNOS = sys.platform.startswith(("sunos", "solaris"))
AIX = sys.platform.startswith("aix")


# ===================================================================
# --- API constants
# ===================================================================


# Process.status()
STATUS_RUNNING = "running"
STATUS_SLEEPING = "sleeping"
STATUS_DISK_SLEEP = "disk-sleep"
STATUS_STOPPED = "stopped"
STATUS_TRACING_STOP = "tracing-stop"
STATUS_ZOMBIE = "zombie"
STATUS_DEAD = "dead"
STATUS_WAKE_KILL = "wake-kill"
STATUS_WAKING = "waking"
STATUS_IDLE = "idle"  # Linux, macOS, FreeBSD
STATUS_LOCKED = "locked"  # FreeBSD
STATUS_WAITING = "waiting"  # FreeBSD
STATUS_SUSPENDED = "suspended"  # NetBSD
STATUS_PARKED = "parked"  # Linux

# Process.connections() and psutil.net_connections()
CONN_ESTABLISHED = "ESTABLISHED"
CONN_SYN_SENT = "SYN_SENT"
CONN_SYN_RECV = "SYN_RECV"
CONN_FIN_WAIT1 = "FIN_WAIT1"
CONN_FIN_WAIT2 = "FIN_WAIT2"
CONN_TIME_WAIT = "TIME_WAIT"
CONN_CLOSE = "CLOSE"
CONN_CLOSE_WAIT = "CLOSE_WAIT"
CONN_LAST_ACK = "LAST_ACK"
CONN_LISTEN = "LISTEN"
CONN_CLOSING = "CLOSING"
CONN_NONE = "NONE"

# net_if_stats()
if enum is None:
    NIC_DUPLEX_FULL = 2
    NIC_DUPLEX_HALF = 1
    NIC_DUPLEX_UNKNOWN = 0
else:

    class NicDuplex(enum.IntEnum):
        NIC_DUPLEX_FULL = 2
        NIC_DUPLEX_HALF = 1
        NIC_DUPLEX_UNKNOWN = 0

    globals().update(NicDuplex.__members__)

# sensors_battery()
if enum is None:
    POWER_TIME_UNKNOWN = -1
    POWER_TIME_UNLIMITED = -2
else:

    class BatteryTime(enum.IntEnum):
        POWER_TIME_UNKNOWN = -1
        POWER_TIME_UNLIMITED = -2

    globals().update(BatteryTime.__members__)

# --- others

ENCODING = sys.getfilesystemencoding()
if not PY3:
    ENCODING_ERRS = "replace"
else:
    try:
        ENCODING_ERRS = sys.getfilesystemencodeerrors()  # py 3.6
    except AttributeError:
        ENCODING_ERRS = "surrogateescape" if POSIX else "replace"


# ===================================================================
# --- namedtuples
# ===================================================================

# --- for system functions

# fmt: off
# psutil.swap_memory()
sswap = namedtuple('sswap', ['total', 'used', 'free', 'percent', 'sin',
                             'sout'])
# psutil.disk_usage()
sdiskusage = namedtuple('sdiskusage', ['total', 'used', 'free', 'percent'])
# psutil.disk_io_counters()
sdiskio = namedtuple('sdiskio', ['read_count', 'write_count',
                                 'read_bytes', 'write_bytes',
                                 'read_time', 'write_time'])
# psutil.disk_partitions()
sdiskpart = namedtuple('sdiskpart', ['device', 'mountpoint', 'fstype', 'opts',
                                     'maxfile', 'maxpath'])
# psutil.net_io_counters()
snetio = namedtuple('snetio', ['bytes_sent', 'bytes_recv',
                               'packets_sent', 'packets_recv',
                               'errin', 'errout',
                               'dropin', 'dropout'])
# psutil.users()
suser = namedtuple('suser', ['name', 'terminal', 'host', 'started', 'pid'])
# psutil.net_connections()
sconn = namedtuple('sconn', ['fd', 'family', 'type', 'laddr', 'raddr',
                             'status', 'pid'])
# psutil.net_if_addrs()
snicaddr = namedtuple('snicaddr',
                      ['family', 'address', 'netmask', 'broadcast', 'ptp'])
# psutil.net_if_stats()
snicstats = namedtuple('snicstats',
                       ['isup', 'duplex', 'speed', 'mtu', 'flags'])
# psutil.cpu_stats()
scpustats = namedtuple(
    'scpustats', ['ctx_switches', 'interrupts', 'soft_interrupts', 'syscalls'])
# psutil.cpu_freq()
scpufreq = namedtuple('scpufreq', ['current', 'min', 'max'])
# psutil.sensors_temperatures()
shwtemp = namedtuple(
    'shwtemp', ['label', 'current', 'high', 'critical'])
# psutil.sensors_battery()
sbattery = namedtuple('sbattery', ['percent', 'secsleft', 'power_plugged'])
# psutil.sensors_fans()
sfan = namedtuple('sfan', ['label', 'current'])
# fmt: on

# --- for Process methods

# psutil.Process.cpu_times()
pcputimes = namedtuple(
    'pcputimes', ['user', 'system', 'children_user', 'children_system']
)
# psutil.Process.open_files()
popenfile = namedtuple('popenfile', ['path', 'fd'])
# psutil.Process.threads()
pthread = namedtuple('pthread', ['id', 'user_time', 'system_time'])
# psutil.Process.uids()
puids = namedtuple('puids', ['real', 'effective', 'saved'])
# psutil.Process.gids()
pgids = namedtuple('pgids', ['real', 'effective', 'saved'])
# psutil.Process.io_counters()
pio = namedtuple(
    'pio', ['read_count', 'write_count', 'read_bytes', 'write_bytes']
)
# psutil.Process.ionice()
pionice = namedtuple('pionice', ['ioclass', 'value'])
# psutil.Process.ctx_switches()
pctxsw = namedtuple('pctxsw', ['voluntary', 'involuntary'])
# psutil.Process.connections()
pconn = namedtuple(
    'pconn', ['fd', 'family', 'type', 'laddr', 'raddr', 'status']
)

# psutil.connections() and psutil.Process.connections()
addr = namedtuple('addr', ['ip', 'port'])


# ===================================================================
# --- Process.connections() 'kind' parameter mapping
# ===================================================================


conn_tmap = {
    "all": ([AF_INET, AF_INET6, AF_UNIX], [SOCK_STREAM, SOCK_DGRAM]),
    "tcp": ([AF_INET, AF_INET6], [SOCK_STREAM]),
    "tcp4": ([AF_INET], [SOCK_STREAM]),
    "udp": ([AF_INET, AF_INET6], [SOCK_DGRAM]),
    "udp4": ([AF_INET], [SOCK_DGRAM]),
    "inet": ([AF_INET, AF_INET6], [SOCK_STREAM, SOCK_DGRAM]),
    "inet4": ([AF_INET], [SOCK_STREAM, SOCK_DGRAM]),
    "inet6": ([AF_INET6], [SOCK_STREAM, SOCK_DGRAM]),
}

if AF_INET6 is not None:
    conn_tmap.update({
        "tcp6": ([AF_INET6], [SOCK_STREAM]),
        "udp6": ([AF_INET6], [SOCK_DGRAM]),
    })

if AF_UNIX is not None:
    conn_tmap.update({"unix": ([AF_UNIX], [SOCK_STREAM, SOCK_DGRAM])})


# =====================================================================
# --- Exceptions
# =====================================================================


class Error(Exception):
    """Base exception class. All other psutil exceptions inherit
    from this one.
    """

    __module__ = 'psutil'

    def _infodict(self, attrs):
        info = collections.OrderedDict()
        for name in attrs:
            value = getattr(self, name, None)
            if value:  # noqa
                info[name] = value
            elif name == "pid" and value == 0:
                info[name] = value
        return info

    def __str__(self):
        # invoked on `raise Error`
        info = self._infodict(("pid", "ppid", "name"))
        if info:
            details = "(%s)" % ", ".join(
                ["%s=%r" % (k, v) for k, v in info.items()]
            )
        else:
            details = None
        return " ".join([x for x in (getattr(self, "msg", ""), details) if x])

    def __repr__(self):
        # invoked on `repr(Error)`
        info = self._infodict(("pid", "ppid", "name", "seconds", "msg"))
        details = ", ".join(["%s=%r" % (k, v) for k, v in info.items()])
        return "psutil.%s(%s)" % (self.__class__.__name__, details)


class NoSuchProcess(Error):
    """Exception raised when a process with a certain PID doesn't
    or no longer exists.
    """

    __module__ = 'psutil'

    def __init__(self, pid, name=None, msg=None):
        Error.__init__(self)
        self.pid = pid
        self.name = name
        self.msg = msg or "process no longer exists"


class ZombieProcess(NoSuchProcess):
    """Exception raised when querying a zombie process. This is
    raised on macOS, BSD and Solaris only, and not always: depending
    on the query the OS may be able to succeed anyway.
    On Linux all zombie processes are querable (hence this is never
    raised). Windows doesn't have zombie processes.
    """

    __module__ = 'psutil'

    def __init__(self, pid, name=None, ppid=None, msg=None):
        NoSuchProcess.__init__(self, pid, name, msg)
        self.ppid = ppid
        self.msg = msg or "PID still exists but it's a zombie"


class AccessDenied(Error):
    """Exception raised when permission to perform an action is denied."""

    __module__ = 'psutil'

    def __init__(self, pid=None, name=None, msg=None):
        Error.__init__(self)
        self.pid = pid
        self.name = name
        self.msg = msg or ""


class TimeoutExpired(Error):
    """Raised on Process.wait(timeout) if timeout expires and process
    is still alive.
    """

    __module__ = 'psutil'

    def __init__(self, seconds, pid=None, name=None):
        Error.__init__(self)
        self.seconds = seconds
        self.pid = pid
        self.name = name
        self.msg = "timeout after %s seconds" % seconds


# ===================================================================
# --- utils
# ===================================================================


# This should be in _compat.py rather than here, but does not work well
# with setup.py importing this module via a sys.path trick.
if PY3:
    if isinstance(__builtins__, dict):  # cpython
        exec_ = __builtins__["exec"]
    else:  # pypy
        exec_ = getattr(__builtins__, "exec")  # noqa

    exec_("""def raise_from(value, from_value):
    try:
        raise value from from_value
    finally:
        value = None
    """)
else:

    def raise_from(value, from_value):
        raise value


def usage_percent(used, total, round_=None):
    """Calculate percentage usage of 'used' against 'total'."""
    try:
        ret = (float(used) / total) * 100
    except ZeroDivisionError:
        return 0.0
    else:
        if round_ is not None:
            ret = round(ret, round_)
        return ret


def memoize(fun):
    """A simple memoize decorator for functions supporting (hashable)
    positional arguments.
    It also provides a cache_clear() function for clearing the cache:

    >>> @memoize
    ... def foo()
    ...     return 1
        ...
    >>> foo()
    1
    >>> foo.cache_clear()
    >>>

    It supports:
     - functions
     - classes (acts as a @singleton)
     - staticmethods
     - classmethods

    It does NOT support:
     - methods
    """

    @functools.wraps(fun)
    def wrapper(*args, **kwargs):
        key = (args, frozenset(sorted(kwargs.items())))
        try:
            return cache[key]
        except KeyError:
            try:
                ret = cache[key] = fun(*args, **kwargs)
            except Exception as err:  # noqa: BLE001
                raise raise_from(err, None)
            return ret

    def cache_clear():
        """Clear cache."""
        cache.clear()

    cache = {}
    wrapper.cache_clear = cache_clear
    return wrapper


def memoize_when_activated(fun):
    """A memoize decorator which is disabled by default. It can be
    activated and deactivated on request.
    For efficiency reasons it can be used only against class methods
    accepting no arguments.

    >>> class Foo:
    ...     @memoize
    ...     def foo()
    ...         print(1)
    ...
    >>> f = Foo()
    >>> # deactivated (default)
    >>> foo()
    1
    >>> foo()
    1
    >>>
    >>> # activated
    >>> foo.cache_activate(self)
    >>> foo()
    1
    >>> foo()
    >>> foo()
    >>>
    """

    @functools.wraps(fun)
    def wrapper(self):
        try:
            # case 1: we previously entered oneshot() ctx
            ret = self._cache[fun]
        except AttributeError:
            # case 2: we never entered oneshot() ctx
            try:
                return fun(self)
            except Exception as err:  # noqa: BLE001
                raise raise_from(err, None)
        except KeyError:
            # case 3: we entered oneshot() ctx but there's no cache
            # for this entry yet
            try:
                ret = fun(self)
            except Exception as err:  # noqa: BLE001
                raise raise_from(err, None)
            try:
                self._cache[fun] = ret
            except AttributeError:
                # multi-threading race condition, see:
                # https://github.com/giampaolo/psutil/issues/1948
                pass
        return ret

    def cache_activate(proc):
        """Activate cache. Expects a Process instance. Cache will be
        stored as a "_cache" instance attribute.
        """
        proc._cache = {}

    def cache_deactivate(proc):
        """Deactivate and clear cache."""
        try:
            del proc._cache
        except AttributeError:
            pass

    wrapper.cache_activate = cache_activate
    wrapper.cache_deactivate = cache_deactivate
    return wrapper


def isfile_strict(path):
    """Same as os.path.isfile() but does not swallow EACCES / EPERM
    exceptions, see:
    http://mail.python.org/pipermail/python-dev/2012-June/120787.html.
    """
    try:
        st = os.stat(path)
    except OSError as err:
        if err.errno in (errno.EPERM, errno.EACCES):
            raise
        return False
    else:
        return stat.S_ISREG(st.st_mode)


def path_exists_strict(path):
    """Same as os.path.exists() but does not swallow EACCES / EPERM
    exceptions. See:
    http://mail.python.org/pipermail/python-dev/2012-June/120787.html.
    """
    try:
        os.stat(path)
    except OSError as err:
        if err.errno in (errno.EPERM, errno.EACCES):
            raise
        return False
    else:
        return True


@memoize
def supports_ipv6():
    """Return True if IPv6 is supported on this platform."""
    if not socket.has_ipv6 or AF_INET6 is None:
        return False
    try:
        sock = socket.socket(AF_INET6, socket.SOCK_STREAM)
        with contextlib.closing(sock):
            sock.bind(("::1", 0))
        return True
    except socket.error:
        return False


def parse_environ_block(data):
    """Parse a C environ block of environment variables into a dictionary."""
    # The block is usually raw data from the target process.  It might contain
    # trailing garbage and lines that do not look like assignments.
    ret = {}
    pos = 0

    # localize global variable to speed up access.
    WINDOWS_ = WINDOWS
    while True:
        next_pos = data.find("\0", pos)
        # nul byte at the beginning or double nul byte means finish
        if next_pos <= pos:
            break
        # there might not be an equals sign
        equal_pos = data.find("=", pos, next_pos)
        if equal_pos > pos:
            key = data[pos:equal_pos]
            value = data[equal_pos + 1 : next_pos]
            # Windows expects environment variables to be uppercase only
            if WINDOWS_:
                key = key.upper()
            ret[key] = value
        pos = next_pos + 1

    return ret


def sockfam_to_enum(num):
    """Convert a numeric socket family value to an IntEnum member.
    If it's not a known member, return the numeric value itself.
    """
    if enum is None:
        return num
    else:  # pragma: no cover
        try:
            return socket.AddressFamily(num)
        except ValueError:
            return num


def socktype_to_enum(num):
    """Convert a numeric socket type value to an IntEnum member.
    If it's not a known member, return the numeric value itself.
    """
    if enum is None:
        return num
    else:  # pragma: no cover
        try:
            return socket.SocketKind(num)
        except ValueError:
            return num


def conn_to_ntuple(fd, fam, type_, laddr, raddr, status, status_map, pid=None):
    """Convert a raw connection tuple to a proper ntuple."""
    if fam in (socket.AF_INET, AF_INET6):
        if laddr:
            laddr = addr(*laddr)
        if raddr:
            raddr = addr(*raddr)
    if type_ == socket.SOCK_STREAM and fam in (AF_INET, AF_INET6):
        status = status_map.get(status, CONN_NONE)
    else:
        status = CONN_NONE  # ignore whatever C returned to us
    fam = sockfam_to_enum(fam)
    type_ = socktype_to_enum(type_)
    if pid is None:
        return pconn(fd, fam, type_, laddr, raddr, status)
    else:
        return sconn(fd, fam, type_, laddr, raddr, status, pid)


def deprecated_method(replacement):
    """A decorator which can be used to mark a method as deprecated
    'replcement' is the method name which will be called instead.
    """

    def outer(fun):
        msg = "%s() is deprecated and will be removed; use %s() instead" % (
            fun.__name__,
            replacement,
        )
        if fun.__doc__ is None:
            fun.__doc__ = msg

        @functools.wraps(fun)
        def inner(self, *args, **kwargs):
            warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
            return getattr(self, replacement)(*args, **kwargs)

        return inner

    return outer


class _WrapNumbers:
    """Watches numbers so that they don't overflow and wrap
    (reset to zero).
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.cache = {}
        self.reminders = {}
        self.reminder_keys = {}

    def _add_dict(self, input_dict, name):
        assert name not in self.cache
        assert name not in self.reminders
        assert name not in self.reminder_keys
        self.cache[name] = input_dict
        self.reminders[name] = collections.defaultdict(int)
        self.reminder_keys[name] = collections.defaultdict(set)

    def _remove_dead_reminders(self, input_dict, name):
        """In case the number of keys changed between calls (e.g. a
        disk disappears) this removes the entry from self.reminders.
        """
        old_dict = self.cache[name]
        gone_keys = set(old_dict.keys()) - set(input_dict.keys())
        for gone_key in gone_keys:
            for remkey in self.reminder_keys[name][gone_key]:
                del self.reminders[name][remkey]
            del self.reminder_keys[name][gone_key]

    def run(self, input_dict, name):
        """Cache dict and sum numbers which overflow and wrap.
        Return an updated copy of `input_dict`.
        """
        if name not in self.cache:
            # This was the first call.
            self._add_dict(input_dict, name)
            return input_dict

        self._remove_dead_reminders(input_dict, name)

        old_dict = self.cache[name]
        new_dict = {}
        for key in input_dict:
            input_tuple = input_dict[key]
            try:
                old_tuple = old_dict[key]
            except KeyError:
                # The input dict has a new key (e.g. a new disk or NIC)
                # which didn't exist in the previous call.
                new_dict[key] = input_tuple
                continue

            bits = []
            for i in range(len(input_tuple)):
                input_value = input_tuple[i]
                old_value = old_tuple[i]
                remkey = (key, i)
                if input_value < old_value:
                    # it wrapped!
                    self.reminders[name][remkey] += old_value
                    self.reminder_keys[name][key].add(remkey)
                bits.append(input_value + self.reminders[name][remkey])

            new_dict[key] = tuple(bits)

        self.cache[name] = input_dict
        return new_dict

    def cache_clear(self, name=None):
        """Clear the internal cache, optionally only for function 'name'."""
        with self.lock:
            if name is None:
                self.cache.clear()
                self.reminders.clear()
                self.reminder_keys.clear()
            else:
                self.cache.pop(name, None)
                self.reminders.pop(name, None)
                self.reminder_keys.pop(name, None)

    def cache_info(self):
        """Return internal cache dicts as a tuple of 3 elements."""
        with self.lock:
            return (self.cache, self.reminders, self.reminder_keys)


def wrap_numbers(input_dict, name):
    """Given an `input_dict` and a function `name`, adjust the numbers
    which "wrap" (restart from zero) across different calls by adding
    "old value" to "new value" and return an updated dict.
    """
    with _wn.lock:
        return _wn.run(input_dict, name)


_wn = _WrapNumbers()
wrap_numbers.cache_clear = _wn.cache_clear
wrap_numbers.cache_info = _wn.cache_info


# The read buffer size for open() builtin. This (also) dictates how
# much data we read(2) when iterating over file lines as in:
#   >>> with open(file) as f:
#   ...    for line in f:
#   ...        ...
# Default per-line buffer size for binary files is 1K. For text files
# is 8K. We use a bigger buffer (32K) in order to have more consistent
# results when reading /proc pseudo files on Linux, see:
# https://github.com/giampaolo/psutil/issues/2050
# On Python 2 this also speeds up the reading of big files:
# (namely /proc/{pid}/smaps and /proc/net/*):
# https://github.com/giampaolo/psutil/issues/708
FILE_READ_BUFFER_SIZE = 32 * 1024


def open_binary(fname):
    return open(fname, "rb", buffering=FILE_READ_BUFFER_SIZE)


def open_text(fname):
    """On Python 3 opens a file in text mode by using fs encoding and
    a proper en/decoding errors handler.
    On Python 2 this is just an alias for open(name, 'rt').
    """
    if not PY3:
        return open(fname, buffering=FILE_READ_BUFFER_SIZE)

    # See:
    # https://github.com/giampaolo/psutil/issues/675
    # https://github.com/giampaolo/psutil/pull/733
    fobj = open(
        fname,
        buffering=FILE_READ_BUFFER_SIZE,
        encoding=ENCODING,
        errors=ENCODING_ERRS,
    )
    try:
        # Dictates per-line read(2) buffer size. Defaults is 8k. See:
        # https://github.com/giampaolo/psutil/issues/2050#issuecomment-1013387546
        fobj._CHUNK_SIZE = FILE_READ_BUFFER_SIZE
    except AttributeError:
        pass
    except Exception:
        fobj.close()
        raise

    return fobj


def cat(fname, fallback=_DEFAULT, _open=open_text):
    """Read entire file content and return it as a string. File is
    opened in text mode. If specified, `fallback` is the value
    returned in case of error, either if the file does not exist or
    it can't be read().
    """
    if fallback is _DEFAULT:
        with _open(fname) as f:
            return f.read()
    else:
        try:
            with _open(fname) as f:
                return f.read()
        except (IOError, OSError):
            return fallback


def bcat(fname, fallback=_DEFAULT):
    """Same as above but opens file in binary mode."""
    return cat(fname, fallback=fallback, _open=open_binary)


def bytes2human(n, format="%(value).1f%(symbol)s"):
    """Used by various scripts. See: http://goo.gl/zeJZl.

    >>> bytes2human(10000)
    '9.8K'
    >>> bytes2human(100001221)
    '95.4M'
    """
    symbols = ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i + 1) * 10
    for symbol in reversed(symbols[1:]):
        if abs(n) >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return format % locals()
    return format % dict(symbol=symbols[0], value=n)


def get_procfs_path():
    """Return updated psutil.PROCFS_PATH constant."""
    return sys.modules['psutil'].PROCFS_PATH


if PY3:

    def decode(s):
        return s.decode(encoding=ENCODING, errors=ENCODING_ERRS)

else:

    def decode(s):
        return s


# =====================================================================
# --- shell utils
# =====================================================================


@memoize
def term_supports_colors(file=sys.stdout):  # pragma: no cover
    if os.name == 'nt':
        return True
    try:
        import curses

        assert file.isatty()
        curses.setupterm()
        assert curses.tigetnum("colors") > 0
    except Exception:  # noqa: BLE001
        return False
    else:
        return True


def hilite(s, color=None, bold=False):  # pragma: no cover
    """Return an highlighted version of 'string'."""
    if not term_supports_colors():
        return s
    attr = []
    colors = dict(
        blue='34',
        brown='33',
        darkgrey='30',
        green='32',
        grey='37',
        lightblue='36',
        red='91',
        violet='35',
        yellow='93',
    )
    colors[None] = '29'
    try:
        color = colors[color]
    except KeyError:
        raise ValueError(
            "invalid color %r; choose between %s" % (list(colors.keys()))
        )
    attr.append(color)
    if bold:
        attr.append('1')
    return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), s)


def print_color(
    s, color=None, bold=False, file=sys.stdout
):  # pragma: no cover
    """Print a colorized version of string."""
    if not term_supports_colors():
        print(s, file=file)  # NOQA
    elif POSIX:
        print(hilite(s, color, bold), file=file)  # NOQA
    else:
        import ctypes

        DEFAULT_COLOR = 7
        GetStdHandle = ctypes.windll.Kernel32.GetStdHandle
        SetConsoleTextAttribute = (
            ctypes.windll.Kernel32.SetConsoleTextAttribute
        )

        colors = dict(green=2, red=4, brown=6, yellow=6)
        colors[None] = DEFAULT_COLOR
        try:
            color = colors[color]
        except KeyError:
            raise ValueError(
                "invalid color %r; choose between %r"
                % (color, list(colors.keys()))
            )
        if bold and color <= 7:
            color += 8

        handle_id = -12 if file is sys.stderr else -11
        GetStdHandle.restype = ctypes.c_ulong
        handle = GetStdHandle(handle_id)
        SetConsoleTextAttribute(handle, color)
        try:
            print(s, file=file)  # NOQA
        finally:
            SetConsoleTextAttribute(handle, DEFAULT_COLOR)


def debug(msg):
    """If PSUTIL_DEBUG env var is set, print a debug message to stderr."""
    if PSUTIL_DEBUG:
        import inspect

        fname, lineno, _, lines, index = inspect.getframeinfo(
            inspect.currentframe().f_back
        )
        if isinstance(msg, Exception):
            if isinstance(msg, (OSError, IOError, EnvironmentError)):
                # ...because str(exc) may contain info about the file name
                msg = "ignoring %s" % msg
            else:
                msg = "ignoring %r" % msg
        print(  # noqa
            "psutil-debug [%s:%s]> %s" % (fname, lineno, msg), file=sys.stderr
        )

# === NexusCore/openenv\Lib\site-packages\nltk\tree\tree.py ===
# Natural Language Toolkit: Text Trees
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
#         Peter Ljunglöf <peter.ljunglof@gu.se>
#         Nathan Bodenstab <bodenstab@cslu.ogi.edu> (tree transforms)
#         Eric Kafe <kafe.eric@gmail.com> (Tree.fromlist())
#         Mohaned mashaly<mohaned.mashaly12@gmail.com> (Deprecating methods)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Class for representing hierarchical language structures, such as
syntax trees and morphological trees.
"""

import re

from nltk.grammar import Nonterminal, Production
from nltk.internals import deprecated

######################################################################
## Trees
######################################################################


class Tree(list):
    r"""
    A Tree represents a hierarchical grouping of leaves and subtrees.
    For example, each constituent in a syntax tree is represented by a single Tree.

    A tree's children are encoded as a list of leaves and subtrees,
    where a leaf is a basic (non-tree) value; and a subtree is a
    nested Tree.

        >>> from nltk.tree import Tree
        >>> print(Tree(1, [2, Tree(3, [4]), 5]))
        (1 2 (3 4) 5)
        >>> vp = Tree('VP', [Tree('V', ['saw']),
        ...                  Tree('NP', ['him'])])
        >>> s = Tree('S', [Tree('NP', ['I']), vp])
        >>> print(s)
        (S (NP I) (VP (V saw) (NP him)))
        >>> print(s[1])
        (VP (V saw) (NP him))
        >>> print(s[1,1])
        (NP him)
        >>> t = Tree.fromstring("(S (NP I) (VP (V saw) (NP him)))")
        >>> s == t
        True
        >>> t[1][1].set_label('X')
        >>> t[1][1].label()
        'X'
        >>> print(t)
        (S (NP I) (VP (V saw) (X him)))
        >>> t[0], t[1,1] = t[1,1], t[0]
        >>> print(t)
        (S (X him) (VP (V saw) (NP I)))

    The length of a tree is the number of children it has.

        >>> len(t)
        2

    The set_label() and label() methods allow individual constituents
    to be labeled.  For example, syntax trees use this label to specify
    phrase tags, such as "NP" and "VP".

    Several Tree methods use "tree positions" to specify
    children or descendants of a tree.  Tree positions are defined as
    follows:

      - The tree position *i* specifies a Tree's *i*\ th child.
      - The tree position ``()`` specifies the Tree itself.
      - If *p* is the tree position of descendant *d*, then
        *p+i* specifies the *i*\ th child of *d*.

    I.e., every tree position is either a single index *i*,
    specifying ``tree[i]``; or a sequence *i1, i2, ..., iN*,
    specifying ``tree[i1][i2]...[iN]``.

    Construct a new tree.  This constructor can be called in one
    of two ways:

    - ``Tree(label, children)`` constructs a new tree with the
        specified label and list of children.

    - ``Tree.fromstring(s)`` constructs a new tree by parsing the string ``s``.
    """

    def __init__(self, node, children=None):
        if children is None:
            raise TypeError(
                "%s: Expected a node value and child list " % type(self).__name__
            )
        elif isinstance(children, str):
            raise TypeError(
                "%s() argument 2 should be a list, not a "
                "string" % type(self).__name__
            )
        else:
            list.__init__(self, children)
            self._label = node

    # ////////////////////////////////////////////////////////////
    # Comparison operators
    # ////////////////////////////////////////////////////////////

    def __eq__(self, other):
        return self.__class__ is other.__class__ and (self._label, list(self)) == (
            other._label,
            list(other),
        )

    def __lt__(self, other):
        if not isinstance(other, Tree):
            # raise_unorderable_types("<", self, other)
            # Sometimes children can be pure strings,
            # so we need to be able to compare with non-trees:
            return self.__class__.__name__ < other.__class__.__name__
        elif self.__class__ is other.__class__:
            return (self._label, list(self)) < (other._label, list(other))
        else:
            return self.__class__.__name__ < other.__class__.__name__

    # @total_ordering doesn't work here, since the class inherits from a builtin class
    __ne__ = lambda self, other: not self == other
    __gt__ = lambda self, other: not (self < other or self == other)
    __le__ = lambda self, other: self < other or self == other
    __ge__ = lambda self, other: not self < other

    # ////////////////////////////////////////////////////////////
    # Disabled list operations
    # ////////////////////////////////////////////////////////////

    def __mul__(self, v):
        raise TypeError("Tree does not support multiplication")

    def __rmul__(self, v):
        raise TypeError("Tree does not support multiplication")

    def __add__(self, v):
        raise TypeError("Tree does not support addition")

    def __radd__(self, v):
        raise TypeError("Tree does not support addition")

    # ////////////////////////////////////////////////////////////
    # Indexing (with support for tree positions)
    # ////////////////////////////////////////////////////////////

    def __getitem__(self, index):
        if isinstance(index, (int, slice)):
            return list.__getitem__(self, index)
        elif isinstance(index, (list, tuple)):
            if len(index) == 0:
                return self
            elif len(index) == 1:
                return self[index[0]]
            else:
                return self[index[0]][index[1:]]
        else:
            raise TypeError(
                "%s indices must be integers, not %s"
                % (type(self).__name__, type(index).__name__)
            )

    def __setitem__(self, index, value):
        if isinstance(index, (int, slice)):
            return list.__setitem__(self, index, value)
        elif isinstance(index, (list, tuple)):
            if len(index) == 0:
                raise IndexError("The tree position () may not be " "assigned to.")
            elif len(index) == 1:
                self[index[0]] = value
            else:
                self[index[0]][index[1:]] = value
        else:
            raise TypeError(
                "%s indices must be integers, not %s"
                % (type(self).__name__, type(index).__name__)
            )

    def __delitem__(self, index):
        if isinstance(index, (int, slice)):
            return list.__delitem__(self, index)
        elif isinstance(index, (list, tuple)):
            if len(index) == 0:
                raise IndexError("The tree position () may not be deleted.")
            elif len(index) == 1:
                del self[index[0]]
            else:
                del self[index[0]][index[1:]]
        else:
            raise TypeError(
                "%s indices must be integers, not %s"
                % (type(self).__name__, type(index).__name__)
            )

    # ////////////////////////////////////////////////////////////
    # Basic tree operations
    # ////////////////////////////////////////////////////////////
    @deprecated("Use label() instead")
    def _get_node(self):
        """Outdated method to access the node value; use the label() method instead."""

    @deprecated("Use set_label() instead")
    def _set_node(self, value):
        """Outdated method to set the node value; use the set_label() method instead."""

    node = property(_get_node, _set_node)

    def label(self):
        """
        Return the node label of the tree.

            >>> t = Tree.fromstring('(S (NP (D the) (N dog)) (VP (V chased) (NP (D the) (N cat))))')
            >>> t.label()
            'S'

        :return: the node label (typically a string)
        :rtype: any
        """
        return self._label

    def set_label(self, label):
        """
        Set the node label of the tree.

            >>> t = Tree.fromstring("(S (NP (D the) (N dog)) (VP (V chased) (NP (D the) (N cat))))")
            >>> t.set_label("T")
            >>> print(t)
            (T (NP (D the) (N dog)) (VP (V chased) (NP (D the) (N cat))))

        :param label: the node label (typically a string)
        :type label: any
        """
        self._label = label

    def leaves(self):
        """
        Return the leaves of the tree.

            >>> t = Tree.fromstring("(S (NP (D the) (N dog)) (VP (V chased) (NP (D the) (N cat))))")
            >>> t.leaves()
            ['the', 'dog', 'chased', 'the', 'cat']

        :return: a list containing this tree's leaves.
            The order reflects the order of the
            leaves in the tree's hierarchical structure.
        :rtype: list
        """
        leaves = []
        for child in self:
            if isinstance(child, Tree):
                leaves.extend(child.leaves())
            else:
                leaves.append(child)
        return leaves

    def flatten(self):
        """
        Return a flat version of the tree, with all non-root non-terminals removed.

            >>> t = Tree.fromstring("(S (NP (D the) (N dog)) (VP (V chased) (NP (D the) (N cat))))")
            >>> print(t.flatten())
            (S the dog chased the cat)

        :return: a tree consisting of this tree's root connected directly to
            its leaves, omitting all intervening non-terminal nodes.
        :rtype: Tree
        """
        return Tree(self.label(), self.leaves())

    def height(self):
        """
        Return the height of the tree.

            >>> t = Tree.fromstring("(S (NP (D the) (N dog)) (VP (V chased) (NP (D the) (N cat))))")
            >>> t.height()
            5
            >>> print(t[0,0])
            (D the)
            >>> t[0,0].height()
            2

        :return: The height of this tree.  The height of a tree
            containing no children is 1; the height of a tree
            containing only leaves is 2; and the height of any other
            tree is one plus the maximum of its children's
            heights.
        :rtype: int
        """
        max_child_height = 0
        for child in self:
            if isinstance(child, Tree):
                max_child_height = max(max_child_height, child.height())
            else:
                max_child_height = max(max_child_height, 1)
        return 1 + max_child_height

    def treepositions(self, order="preorder"):
        """
            >>> t = Tree.fromstring("(S (NP (D the) (N dog)) (VP (V chased) (NP (D the) (N cat))))")
            >>> t.treepositions() # doctest: +ELLIPSIS
            [(), (0,), (0, 0), (0, 0, 0), (0, 1), (0, 1, 0), (1,), (1, 0), (1, 0, 0), ...]
            >>> for pos in t.treepositions('leaves'):
            ...     t[pos] = t[pos][::-1].upper()
            >>> print(t)
            (S (NP (D EHT) (N GOD)) (VP (V DESAHC) (NP (D EHT) (N TAC))))

        :param order: One of: ``preorder``, ``postorder``, ``bothorder``,
            ``leaves``.
        """
        positions = []
        if order in ("preorder", "bothorder"):
            positions.append(())
        for i, child in enumerate(self):
            if isinstance(child, Tree):
                childpos = child.treepositions(order)
                positions.extend((i,) + p for p in childpos)
            else:
                positions.append((i,))
        if order in ("postorder", "bothorder"):
            positions.append(())
        return positions

    def subtrees(self, filter=None):
        """
        Generate all the subtrees of this tree, optionally restricted
        to trees matching the filter function.

            >>> t = Tree.fromstring("(S (NP (D the) (N dog)) (VP (V chased) (NP (D the) (N cat))))")
            >>> for s in t.subtrees(lambda t: t.height() == 2):
            ...     print(s)
            (D the)
            (N dog)
            (V chased)
            (D the)
            (N cat)

        :type filter: function
        :param filter: the function to filter all local trees
        """
        if not filter or filter(self):
            yield self
        for child in self:
            if isinstance(child, Tree):
                yield from child.subtrees(filter)

    def productions(self):
        """
        Generate the productions that correspond to the non-terminal nodes of the tree.
        For each subtree of the form (P: C1 C2 ... Cn) this produces a production of the
        form P -> C1 C2 ... Cn.

            >>> t = Tree.fromstring("(S (NP (D the) (N dog)) (VP (V chased) (NP (D the) (N cat))))")
            >>> t.productions() # doctest: +NORMALIZE_WHITESPACE
            [S -> NP VP, NP -> D N, D -> 'the', N -> 'dog', VP -> V NP, V -> 'chased',
            NP -> D N, D -> 'the', N -> 'cat']

        :rtype: list(Production)
        """

        if not isinstance(self._label, str):
            raise TypeError(
                "Productions can only be generated from trees having node labels that are strings"
            )

        prods = [Production(Nonterminal(self._label), _child_names(self))]
        for child in self:
            if isinstance(child, Tree):
                prods += child.productions()
        return prods

    def pos(self):
        """
        Return a sequence of pos-tagged words extracted from the tree.

            >>> t = Tree.fromstring("(S (NP (D the) (N dog)) (VP (V chased) (NP (D the) (N cat))))")
            >>> t.pos()
            [('the', 'D'), ('dog', 'N'), ('chased', 'V'), ('the', 'D'), ('cat', 'N')]

        :return: a list of tuples containing leaves and pre-terminals (part-of-speech tags).
            The order reflects the order of the leaves in the tree's hierarchical structure.
        :rtype: list(tuple)
        """
        pos = []
        for child in self:
            if isinstance(child, Tree):
                pos.extend(child.pos())
            else:
                pos.append((child, self._label))
        return pos

    def leaf_treeposition(self, index):
        """
        :return: The tree position of the ``index``-th leaf in this
            tree.  I.e., if ``tp=self.leaf_treeposition(i)``, then
            ``self[tp]==self.leaves()[i]``.

        :raise IndexError: If this tree contains fewer than ``index+1``
            leaves, or if ``index<0``.
        """
        if index < 0:
            raise IndexError("index must be non-negative")

        stack = [(self, ())]
        while stack:
            value, treepos = stack.pop()
            if not isinstance(value, Tree):
                if index == 0:
                    return treepos
                else:
                    index -= 1
            else:
                for i in range(len(value) - 1, -1, -1):
                    stack.append((value[i], treepos + (i,)))

        raise IndexError("index must be less than or equal to len(self)")

    def treeposition_spanning_leaves(self, start, end):
        """
        :return: The tree position of the lowest descendant of this
            tree that dominates ``self.leaves()[start:end]``.
        :raise ValueError: if ``end <= start``
        """
        if end <= start:
            raise ValueError("end must be greater than start")
        # Find the tree positions of the start & end leaves, and
        # take the longest common subsequence.
        start_treepos = self.leaf_treeposition(start)
        end_treepos = self.leaf_treeposition(end - 1)
        # Find the first index where they mismatch:
        for i in range(len(start_treepos)):
            if i == len(end_treepos) or start_treepos[i] != end_treepos[i]:
                return start_treepos[:i]
        return start_treepos

    # ////////////////////////////////////////////////////////////
    # Transforms
    # ////////////////////////////////////////////////////////////

    def chomsky_normal_form(
        self,
        factor="right",
        horzMarkov=None,
        vertMarkov=0,
        childChar="|",
        parentChar="^",
    ):
        """
        This method can modify a tree in three ways:

          1. Convert a tree into its Chomsky Normal Form (CNF)
             equivalent -- Every subtree has either two non-terminals
             or one terminal as its children.  This process requires
             the creation of more"artificial" non-terminal nodes.
          2. Markov (vertical) smoothing of children in new artificial
             nodes
          3. Horizontal (parent) annotation of nodes

        :param factor: Right or left factoring method (default = "right")
        :type  factor: str = [left|right]
        :param horzMarkov: Markov order for sibling smoothing in artificial nodes (None (default) = include all siblings)
        :type  horzMarkov: int | None
        :param vertMarkov: Markov order for parent smoothing (0 (default) = no vertical annotation)
        :type  vertMarkov: int | None
        :param childChar: A string used in construction of the artificial nodes, separating the head of the
                          original subtree from the child nodes that have yet to be expanded (default = "|")
        :type  childChar: str
        :param parentChar: A string used to separate the node representation from its vertical annotation
        :type  parentChar: str
        """
        from nltk.tree.transforms import chomsky_normal_form

        chomsky_normal_form(self, factor, horzMarkov, vertMarkov, childChar, parentChar)

    def un_chomsky_normal_form(
        self, expandUnary=True, childChar="|", parentChar="^", unaryChar="+"
    ):
        """
        This method modifies the tree in three ways:

          1. Transforms a tree in Chomsky Normal Form back to its
             original structure (branching greater than two)
          2. Removes any parent annotation (if it exists)
          3. (optional) expands unary subtrees (if previously
             collapsed with collapseUnary(...) )

        :param expandUnary: Flag to expand unary or not (default = True)
        :type  expandUnary: bool
        :param childChar: A string separating the head node from its children in an artificial node (default = "|")
        :type  childChar: str
        :param parentChar: A string separating the node label from its parent annotation (default = "^")
        :type  parentChar: str
        :param unaryChar: A string joining two non-terminals in a unary production (default = "+")
        :type  unaryChar: str
        """
        from nltk.tree.transforms import un_chomsky_normal_form

        un_chomsky_normal_form(self, expandUnary, childChar, parentChar, unaryChar)

    def collapse_unary(self, collapsePOS=False, collapseRoot=False, joinChar="+"):
        """
        Collapse subtrees with a single child (ie. unary productions)
        into a new non-terminal (Tree node) joined by 'joinChar'.
        This is useful when working with algorithms that do not allow
        unary productions, and completely removing the unary productions
        would require loss of useful information.  The Tree is modified
        directly (since it is passed by reference) and no value is returned.

        :param collapsePOS: 'False' (default) will not collapse the parent of leaf nodes (ie.
                            Part-of-Speech tags) since they are always unary productions
        :type  collapsePOS: bool
        :param collapseRoot: 'False' (default) will not modify the root production
                             if it is unary.  For the Penn WSJ treebank corpus, this corresponds
                             to the TOP -> productions.
        :type collapseRoot: bool
        :param joinChar: A string used to connect collapsed node values (default = "+")
        :type  joinChar: str
        """
        from nltk.tree.transforms import collapse_unary

        collapse_unary(self, collapsePOS, collapseRoot, joinChar)

    # ////////////////////////////////////////////////////////////
    # Convert, copy
    # ////////////////////////////////////////////////////////////

    @classmethod
    def convert(cls, tree):
        """
        Convert a tree between different subtypes of Tree.  ``cls`` determines
        which class will be used to encode the new tree.

        :type tree: Tree
        :param tree: The tree that should be converted.
        :return: The new Tree.
        """
        if isinstance(tree, Tree):
            children = [cls.convert(child) for child in tree]
            return cls(tree._label, children)
        else:
            return tree

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memo):
        return self.copy(deep=True)

    def copy(self, deep=False):
        if not deep:
            return type(self)(self._label, self)
        else:
            return type(self).convert(self)

    def _frozen_class(self):
        from nltk.tree.immutable import ImmutableTree

        return ImmutableTree

    def freeze(self, leaf_freezer=None):
        frozen_class = self._frozen_class()
        if leaf_freezer is None:
            newcopy = frozen_class.convert(self)
        else:
            newcopy = self.copy(deep=True)
            for pos in newcopy.treepositions("leaves"):
                newcopy[pos] = leaf_freezer(newcopy[pos])
            newcopy = frozen_class.convert(newcopy)
        hash(newcopy)  # Make sure the leaves are hashable.
        return newcopy

    # ////////////////////////////////////////////////////////////
    # Parsing
    # ////////////////////////////////////////////////////////////

    @classmethod
    def fromstring(
        cls,
        s,
        brackets="()",
        read_node=None,
        read_leaf=None,
        node_pattern=None,
        leaf_pattern=None,
        remove_empty_top_bracketing=False,
    ):
        """
        Read a bracketed tree string and return the resulting tree.
        Trees are represented as nested brackettings, such as::

          (S (NP (NNP John)) (VP (V runs)))

        :type s: str
        :param s: The string to read

        :type brackets: str (length=2)
        :param brackets: The bracket characters used to mark the
            beginning and end of trees and subtrees.

        :type read_node: function
        :type read_leaf: function
        :param read_node, read_leaf: If specified, these functions
            are applied to the substrings of ``s`` corresponding to
            nodes and leaves (respectively) to obtain the values for
            those nodes and leaves.  They should have the following
            signature:

               read_node(str) -> value

            For example, these functions could be used to process nodes
            and leaves whose values should be some type other than
            string (such as ``FeatStruct``).
            Note that by default, node strings and leaf strings are
            delimited by whitespace and brackets; to override this
            default, use the ``node_pattern`` and ``leaf_pattern``
            arguments.

        :type node_pattern: str
        :type leaf_pattern: str
        :param node_pattern, leaf_pattern: Regular expression patterns
            used to find node and leaf substrings in ``s``.  By
            default, both nodes patterns are defined to match any
            sequence of non-whitespace non-bracket characters.

        :type remove_empty_top_bracketing: bool
        :param remove_empty_top_bracketing: If the resulting tree has
            an empty node label, and is length one, then return its
            single child instead.  This is useful for treebank trees,
            which sometimes contain an extra level of bracketing.

        :return: A tree corresponding to the string representation ``s``.
            If this class method is called using a subclass of Tree,
            then it will return a tree of that type.
        :rtype: Tree
        """
        if not isinstance(brackets, str) or len(brackets) != 2:
            raise TypeError("brackets must be a length-2 string")
        if re.search(r"\s", brackets):
            raise TypeError("whitespace brackets not allowed")
        # Construct a regexp that will tokenize the string.
        open_b, close_b = brackets
        open_pattern, close_pattern = (re.escape(open_b), re.escape(close_b))
        if node_pattern is None:
            node_pattern = rf"[^\s{open_pattern}{close_pattern}]+"
        if leaf_pattern is None:
            leaf_pattern = rf"[^\s{open_pattern}{close_pattern}]+"
        token_re = re.compile(
            r"%s\s*(%s)?|%s|(%s)"
            % (open_pattern, node_pattern, close_pattern, leaf_pattern)
        )
        # Walk through each token, updating a stack of trees.
        stack = [(None, [])]  # list of (node, children) tuples
        for match in token_re.finditer(s):
            token = match.group()
            # Beginning of a tree/subtree
            if token[0] == open_b:
                if len(stack) == 1 and len(stack[0][1]) > 0:
                    cls._parse_error(s, match, "end-of-string")
                label = token[1:].lstrip()
                if read_node is not None:
                    label = read_node(label)
                stack.append((label, []))
            # End of a tree/subtree
            elif token == close_b:
                if len(stack) == 1:
                    if len(stack[0][1]) == 0:
                        cls._parse_error(s, match, open_b)
                    else:
                        cls._parse_error(s, match, "end-of-string")
                label, children = stack.pop()
                stack[-1][1].append(cls(label, children))
            # Leaf node
            else:
                if len(stack) == 1:
                    cls._parse_error(s, match, open_b)
                if read_leaf is not None:
                    token = read_leaf(token)
                stack[-1][1].append(token)

        # check that we got exactly one complete tree.
        if len(stack) > 1:
            cls._parse_error(s, "end-of-string", close_b)
        elif len(stack[0][1]) == 0:
            cls._parse_error(s, "end-of-string", open_b)
        else:
            assert stack[0][0] is None
            assert len(stack[0][1]) == 1
        tree = stack[0][1][0]

        # If the tree has an extra level with node='', then get rid of
        # it.  E.g.: "((S (NP ...) (VP ...)))"
        if remove_empty_top_bracketing and tree._label == "" and len(tree) == 1:
            tree = tree[0]
        # return the tree.
        return tree

    @classmethod
    def _parse_error(cls, s, match, expecting):
        """
        Display a friendly error message when parsing a tree string fails.
        :param s: The string we're parsing.
        :param match: regexp match of the problem token.
        :param expecting: what we expected to see instead.
        """
        # Construct a basic error message
        if match == "end-of-string":
            pos, token = len(s), "end-of-string"
        else:
            pos, token = match.start(), match.group()
        msg = "%s.read(): expected %r but got %r\n%sat index %d." % (
            cls.__name__,
            expecting,
            token,
            " " * 12,
            pos,
        )
        # Add a display showing the error token itsels:
        s = s.replace("\n", " ").replace("\t", " ")
        offset = pos
        if len(s) > pos + 10:
            s = s[: pos + 10] + "..."
        if pos > 10:
            s = "..." + s[pos - 10 :]
            offset = 13
        msg += '\n{}"{}"\n{}^'.format(" " * 16, s, " " * (17 + offset))
        raise ValueError(msg)

    @classmethod
    def fromlist(cls, l):
        """
        :type l: list
        :param l: a tree represented as nested lists

        :return: A tree corresponding to the list representation ``l``.
        :rtype: Tree

        Convert nested lists to a NLTK Tree
        """
        if type(l) == list and len(l) > 0:
            label = repr(l[0])
            if len(l) > 1:
                return Tree(label, [cls.fromlist(child) for child in l[1:]])
            else:
                return label

    # ////////////////////////////////////////////////////////////
    # Visualization & String Representation
    # ////////////////////////////////////////////////////////////

    def draw(self):
        """
        Open a new window containing a graphical diagram of this tree.
        """
        from nltk.draw.tree import draw_trees

        draw_trees(self)

    def pretty_print(self, sentence=None, highlight=(), stream=None, **kwargs):
        """
        Pretty-print this tree as ASCII or Unicode art.
        For explanation of the arguments, see the documentation for
        `nltk.tree.prettyprinter.TreePrettyPrinter`.
        """
        from nltk.tree.prettyprinter import TreePrettyPrinter

        print(TreePrettyPrinter(self, sentence, highlight).text(**kwargs), file=stream)

    def __repr__(self):
        childstr = ", ".join(repr(c) for c in self)
        return "{}({}, [{}])".format(
            type(self).__name__,
            repr(self._label),
            childstr,
        )

    def _repr_svg_(self):
        from svgling import draw_tree

        return draw_tree(self)._repr_svg_()

    def __str__(self):
        return self.pformat()

    def pprint(self, **kwargs):
        """
        Print a string representation of this Tree to 'stream'
        """

        if "stream" in kwargs:
            stream = kwargs["stream"]
            del kwargs["stream"]
        else:
            stream = None
        print(self.pformat(**kwargs), file=stream)

    def pformat(self, margin=70, indent=0, nodesep="", parens="()", quotes=False):
        """
        :return: A pretty-printed string representation of this tree.
        :rtype: str
        :param margin: The right margin at which to do line-wrapping.
        :type margin: int
        :param indent: The indentation level at which printing
            begins.  This number is used to decide how far to indent
            subsequent lines.
        :type indent: int
        :param nodesep: A string that is used to separate the node
            from the children.  E.g., the default value ``':'`` gives
            trees like ``(S: (NP: I) (VP: (V: saw) (NP: it)))``.
        """

        # Try writing it on one line.
        s = self._pformat_flat(nodesep, parens, quotes)
        if len(s) + indent < margin:
            return s

        # If it doesn't fit on one line, then write it on multi-lines.
        if isinstance(self._label, str):
            s = f"{parens[0]}{self._label}{nodesep}"
        else:
            s = f"{parens[0]}{repr(self._label)}{nodesep}"
        for child in self:
            if isinstance(child, Tree):
                s += (
                    "\n"
                    + " " * (indent + 2)
                    + child.pformat(margin, indent + 2, nodesep, parens, quotes)
                )
            elif isinstance(child, tuple):
                s += "\n" + " " * (indent + 2) + "/".join(child)
            elif isinstance(child, str) and not quotes:
                s += "\n" + " " * (indent + 2) + "%s" % child
            else:
                s += "\n" + " " * (indent + 2) + repr(child)
        return s + parens[1]

    def pformat_latex_qtree(self):
        r"""
        Returns a representation of the tree compatible with the
        LaTeX qtree package. This consists of the string ``\Tree``
        followed by the tree represented in bracketed notation.

        For example, the following result was generated from a parse tree of
        the sentence ``The announcement astounded us``::

          \Tree [.I'' [.N'' [.D The ] [.N' [.N announcement ] ] ]
              [.I' [.V'' [.V' [.V astounded ] [.N'' [.N' [.N us ] ] ] ] ] ] ]

        See https://www.ling.upenn.edu/advice/latex.html for the LaTeX
        style file for the qtree package.

        :return: A latex qtree representation of this tree.
        :rtype: str
        """
        reserved_chars = re.compile(r"([#\$%&~_\{\}])")

        pformat = self.pformat(indent=6, nodesep="", parens=("[.", " ]"))
        return r"\Tree " + re.sub(reserved_chars, r"\\\1", pformat)

    def _pformat_flat(self, nodesep, parens, quotes):
        childstrs = []
        for child in self:
            if isinstance(child, Tree):
                childstrs.append(child._pformat_flat(nodesep, parens, quotes))
            elif isinstance(child, tuple):
                childstrs.append("/".join(child))
            elif isinstance(child, str) and not quotes:
                childstrs.append("%s" % child)
            else:
                childstrs.append(repr(child))
        if isinstance(self._label, str):
            return "{}{}{} {}{}".format(
                parens[0],
                self._label,
                nodesep,
                " ".join(childstrs),
                parens[1],
            )
        else:
            return "{}{}{} {}{}".format(
                parens[0],
                repr(self._label),
                nodesep,
                " ".join(childstrs),
                parens[1],
            )


def _child_names(tree):
    names = []
    for child in tree:
        if isinstance(child, Tree):
            names.append(Nonterminal(child._label))
        else:
            names.append(child)
    return names


######################################################################
## Demonstration
######################################################################


def demo():
    """
    A demonstration showing how Trees and Trees can be
    used.  This demonstration creates a Tree, and loads a
    Tree from the Treebank corpus,
    and shows the results of calling several of their methods.
    """

    from nltk import ProbabilisticTree, Tree

    # Demonstrate tree parsing.
    s = "(S (NP (DT the) (NN cat)) (VP (VBD ate) (NP (DT a) (NN cookie))))"
    t = Tree.fromstring(s)
    print("Convert bracketed string into tree:")
    print(t)
    print(t.__repr__())

    print("Display tree properties:")
    print(t.label())  # tree's constituent type
    print(t[0])  # tree's first child
    print(t[1])  # tree's second child
    print(t.height())
    print(t.leaves())
    print(t[1])
    print(t[1, 1])
    print(t[1, 1, 0])

    # Demonstrate tree modification.
    the_cat = t[0]
    the_cat.insert(1, Tree.fromstring("(JJ big)"))
    print("Tree modification:")
    print(t)
    t[1, 1, 1] = Tree.fromstring("(NN cake)")
    print(t)
    print()

    # Tree transforms
    print("Collapse unary:")
    t.collapse_unary()
    print(t)
    print("Chomsky normal form:")
    t.chomsky_normal_form()
    print(t)
    print()

    # Demonstrate probabilistic trees.
    pt = ProbabilisticTree("x", ["y", "z"], prob=0.5)
    print("Probabilistic Tree:")
    print(pt)
    print()

    # Demonstrate parsing of treebank output format.
    t = Tree.fromstring(t.pformat())
    print("Convert tree to bracketed string and back again:")
    print(t)
    print()

    # Demonstrate LaTeX output
    print("LaTeX output:")
    print(t.pformat_latex_qtree())
    print()

    # Demonstrate Productions
    print("Production output:")
    print(t.productions())
    print()

    # Demonstrate tree nodes containing objects other than strings
    t.set_label(("test", 3))
    print(t)


__all__ = [
    "Tree",
]

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_file_utils.py ===
r"""
This module provides utilities to get the absolute filenames so that we can be sure that:
    - The case of a file will match the actual file in the filesystem (otherwise breakpoints won't be hit).
    - Providing means for the user to make path conversions when doing a remote debugging session in
      one machine and debugging in another.

To do that, the PATHS_FROM_ECLIPSE_TO_PYTHON constant must be filled with the appropriate paths.

@note:
    in this context, the server is where your python process is running
    and the client is where eclipse is running.

E.g.:
    If the server (your python process) has the structure
        /user/projects/my_project/src/package/module1.py

    and the client has:
        c:\my_project\src\package\module1.py

    the PATHS_FROM_ECLIPSE_TO_PYTHON would have to be:
        PATHS_FROM_ECLIPSE_TO_PYTHON = [(r'c:\my_project\src', r'/user/projects/my_project/src')]

    alternatively, this can be set with an environment variable from the command line:
       set PATHS_FROM_ECLIPSE_TO_PYTHON=[['c:\my_project\src','/user/projects/my_project/src']]

@note: DEBUG_CLIENT_SERVER_TRANSLATION can be set to True to debug the result of those translations

@note: the case of the paths is important! Note that this can be tricky to get right when one machine
uses a case-independent filesystem and the other uses a case-dependent filesystem (if the system being
debugged is case-independent, 'normcase()' should be used on the paths defined in PATHS_FROM_ECLIPSE_TO_PYTHON).

@note: all the paths with breakpoints must be translated (otherwise they won't be found in the server)

@note: to enable remote debugging in the target machine (pydev extensions in the eclipse installation)
    import pydevd;pydevd.settrace(host, stdoutToServer, stderrToServer, port, suspend)

    see parameter docs on pydevd.py

@note: for doing a remote debugging session, all the pydevd_ files must be on the server accessible
    through the PYTHONPATH (and the PATHS_FROM_ECLIPSE_TO_PYTHON only needs to be set on the target
    machine for the paths that'll actually have breakpoints).
"""

from _pydev_bundle import pydev_log
from _pydevd_bundle.pydevd_constants import DebugInfoHolder, IS_WINDOWS, IS_JYTHON, DISABLE_FILE_VALIDATION, is_true_in_env, IS_MAC
from _pydev_bundle._pydev_filesystem_encoding import getfilesystemencoding
from _pydevd_bundle.pydevd_comm_constants import file_system_encoding, filesystem_encoding_is_utf8
from _pydev_bundle.pydev_log import error_once

import json
import os.path
import sys
import itertools
import ntpath
from functools import partial

_nt_os_normcase = ntpath.normcase
os_path_basename = os.path.basename
os_path_exists = os.path.exists
join = os.path.join

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError  # noqa

try:
    os_path_real_path = os.path.realpath  # @UndefinedVariable
except:
    # jython does not support os.path.realpath
    # realpath is a no-op on systems without islink support
    os_path_real_path = os.path.abspath


def _get_library_dir():
    library_dir = None
    try:
        import sysconfig

        library_dir = sysconfig.get_path("purelib")
    except ImportError:
        pass  # i.e.: Only 2.7 onwards

    if library_dir is None or not os_path_exists(library_dir):
        for path in sys.path:
            if os_path_exists(path) and os.path.basename(path) == "site-packages":
                library_dir = path
                break

    if library_dir is None or not os_path_exists(library_dir):
        library_dir = os.path.dirname(os.__file__)

    return library_dir


# Note: we can't call sysconfig.get_path from _apply_func_and_normalize_case (it deadlocks on Python 2.7) so, we
# need to get the library dir during module loading.
_library_dir = _get_library_dir()

# defined as a list of tuples where the 1st element of the tuple is the path in the client machine
# and the 2nd element is the path in the server machine.
# see module docstring for more details.
try:
    PATHS_FROM_ECLIPSE_TO_PYTHON = json.loads(os.environ.get("PATHS_FROM_ECLIPSE_TO_PYTHON", "[]"))
except Exception:
    pydev_log.critical("Error loading PATHS_FROM_ECLIPSE_TO_PYTHON from environment variable.")
    pydev_log.exception()
    PATHS_FROM_ECLIPSE_TO_PYTHON = []
else:
    if not isinstance(PATHS_FROM_ECLIPSE_TO_PYTHON, list):
        pydev_log.critical("Expected PATHS_FROM_ECLIPSE_TO_PYTHON loaded from environment variable to be a list.")
        PATHS_FROM_ECLIPSE_TO_PYTHON = []
    else:
        # Converting json lists to tuple
        PATHS_FROM_ECLIPSE_TO_PYTHON = [tuple(x) for x in PATHS_FROM_ECLIPSE_TO_PYTHON]

# example:
# PATHS_FROM_ECLIPSE_TO_PYTHON = [
#  (r'd:\temp\temp_workspace_2\test_python\src\yyy\yyy',
#   r'd:\temp\temp_workspace_2\test_python\src\hhh\xxx')
# ]

convert_to_long_pathname = lambda filename: filename
convert_to_short_pathname = lambda filename: filename
get_path_with_real_case = lambda filename: filename

# Note that we have a cache for previous list dirs... the only case where this may be an
# issue is if the user actually changes the case of an existing file on while
# the debugger is executing (as this seems very unlikely and the cache can save a
# reasonable time -- especially on mapped drives -- it seems nice to have it).
_listdir_cache = {}

# May be changed during tests.
os_listdir = os.listdir


def _resolve_listing(resolved, iter_parts_lowercase, cache=_listdir_cache):
    while True:  # Note: while True to make iterative and not recursive
        try:
            resolve_lowercase = next(iter_parts_lowercase)  # must be lowercase already
        except StopIteration:
            return resolved

        resolved_lower = resolved.lower()

        resolved_joined = cache.get((resolved_lower, resolve_lowercase))
        if resolved_joined is None:
            dir_contents = cache.get(resolved_lower)
            if dir_contents is None:
                dir_contents = cache[resolved_lower] = os_listdir(resolved)

            for filename in dir_contents:
                if filename.lower() == resolve_lowercase:
                    resolved_joined = os.path.join(resolved, filename)
                    cache[(resolved_lower, resolve_lowercase)] = resolved_joined
                    break
            else:
                raise FileNotFoundError("Unable to find: %s in %s. Dir Contents: %s" % (resolve_lowercase, resolved, dir_contents))

        resolved = resolved_joined


def _resolve_listing_parts(resolved, parts_in_lowercase, filename):
    try:
        if parts_in_lowercase == [""]:
            return resolved
        return _resolve_listing(resolved, iter(parts_in_lowercase))
    except FileNotFoundError:
        _listdir_cache.clear()
        # Retry once after clearing the cache we have.
        try:
            return _resolve_listing(resolved, iter(parts_in_lowercase))
        except FileNotFoundError:
            if os_path_exists(filename):
                # This is really strange, ask the user to report as error.
                pydev_log.critical(
                    "pydev debugger: critical: unable to get real case for file. Details:\n"
                    "filename: %s\ndrive: %s\nparts: %s\n"
                    "(please create a ticket in the tracker to address this).",
                    filename,
                    resolved,
                    parts_in_lowercase,
                )
                pydev_log.exception()
            # Don't fail, just return the original file passed.
            return filename
    except OSError:
        # Something as: PermissionError (listdir may fail).
        # See: https://github.com/microsoft/debugpy/issues/1154
        # Don't fail nor log unless the trace level is at least info. Just return the original file passed.
        if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 1:
            pydev_log.info(
                "pydev debugger: OSError: Unable to get real case for file. Details:\n" "filename: %s\ndrive: %s\nparts: %s\n",
                filename,
                resolved,
                parts_in_lowercase,
            )
            pydev_log.exception()
        return filename


if sys.platform == "win32":
    try:
        import ctypes
        from ctypes.wintypes import MAX_PATH, LPCWSTR, LPWSTR, DWORD

        GetLongPathName = ctypes.windll.kernel32.GetLongPathNameW  # noqa
        GetLongPathName.argtypes = [LPCWSTR, LPWSTR, DWORD]
        GetLongPathName.restype = DWORD

        GetShortPathName = ctypes.windll.kernel32.GetShortPathNameW  # noqa
        GetShortPathName.argtypes = [LPCWSTR, LPWSTR, DWORD]
        GetShortPathName.restype = DWORD

        def _convert_to_long_pathname(filename):
            buf = ctypes.create_unicode_buffer(MAX_PATH)

            rv = GetLongPathName(filename, buf, MAX_PATH)
            if rv != 0 and rv <= MAX_PATH:
                filename = buf.value

            return filename

        def _convert_to_short_pathname(filename):
            buf = ctypes.create_unicode_buffer(MAX_PATH)

            rv = GetShortPathName(filename, buf, MAX_PATH)
            if rv != 0 and rv <= MAX_PATH:
                filename = buf.value

            return filename

        def _get_path_with_real_case(filename):
            # Note: this previously made:
            # convert_to_long_pathname(convert_to_short_pathname(filename))
            # but this is no longer done because we can't rely on getting the shortname
            # consistently (there are settings to disable it on Windows).
            # So, using approach which resolves by listing the dir.

            if "~" in filename:
                filename = convert_to_long_pathname(filename)

            if filename.startswith("<") or not os_path_exists(filename):
                return filename  # Not much we can do.

            drive, parts = os.path.splitdrive(os.path.normpath(filename))
            drive = drive.upper()
            while parts.startswith(os.path.sep):
                parts = parts[1:]
                drive += os.path.sep
            parts = parts.lower().split(os.path.sep)
            return _resolve_listing_parts(drive, parts, filename)

        # Check that it actually works
        _get_path_with_real_case(__file__)
    except:
        # Something didn't quite work out, leave no-op conversions in place.
        if DebugInfoHolder.DEBUG_TRACE_LEVEL > 2:
            pydev_log.exception()
    else:
        convert_to_long_pathname = _convert_to_long_pathname
        convert_to_short_pathname = _convert_to_short_pathname
        get_path_with_real_case = _get_path_with_real_case

elif IS_JYTHON and IS_WINDOWS:

    def get_path_with_real_case(filename):
        if filename.startswith("<"):
            return filename

        from java.io import File  # noqa

        f = File(filename)
        ret = f.getCanonicalPath()
        return ret

elif IS_MAC:

    def get_path_with_real_case(filename):
        if filename.startswith("<") or not os_path_exists(filename):
            return filename  # Not much we can do.

        parts = filename.lower().split("/")

        found = ""
        while parts and parts[0] == "":
            found += "/"
            parts = parts[1:]

        return _resolve_listing_parts(found, parts, filename)


if IS_JYTHON:

    def _normcase_windows(filename):
        return filename.lower()

else:

    def _normcase_windows(filename):
        # `normcase` doesn't lower case on Python 2 for non-English locale, so we should do it manually.
        if "~" in filename:
            filename = convert_to_long_pathname(filename)

        filename = _nt_os_normcase(filename)
        return filename.lower()


def _normcase_linux(filename):
    return filename  # no-op


_filename_normalization = os.environ.get("PYDEVD_FILENAME_NORMALIZATION", "").lower()
if _filename_normalization == "lower":
    # Note: this is mostly for testing (forcing to always lower-case all contents
    # internally -- used to mimick Windows normalization on Linux).

    def _normcase_lower(filename):
        return filename.lower()

    _default_normcase = _normcase_lower

elif _filename_normalization == "none":
    # Disable any filename normalization may be an option on Windows if the
    # user is having issues under some circumstances.
    _default_normcase = _normcase_linux

elif IS_WINDOWS:
    _default_normcase = _normcase_windows

elif IS_MAC:

    def _normcase_lower(filename):
        return filename.lower()

    _default_normcase = _normcase_lower

else:
    _default_normcase = _normcase_linux


def normcase(s, NORMCASE_CACHE={}):
    try:
        return NORMCASE_CACHE[s]
    except:
        normalized = NORMCASE_CACHE[s] = _default_normcase(s)
        return normalized


_ide_os = "WINDOWS" if IS_WINDOWS else "UNIX"

_normcase_from_client = normcase


def normcase_from_client(s):
    return _normcase_from_client(s)


DEBUG_CLIENT_SERVER_TRANSLATION = os.environ.get("DEBUG_PYDEVD_PATHS_TRANSLATION", "False").lower() in ("1", "true")


def set_ide_os(os):
    """
    We need to set the IDE os because the host where the code is running may be
    actually different from the client (and the point is that we want the proper
    paths to translate from the client to the server).

    :param os:
        'UNIX' or 'WINDOWS'
    """
    global _ide_os
    global _normcase_from_client
    prev = _ide_os
    if os == "WIN":  # Apparently PyCharm uses 'WIN' (https://github.com/fabioz/PyDev.Debugger/issues/116)
        os = "WINDOWS"

    assert os in ("WINDOWS", "UNIX")

    if DEBUG_CLIENT_SERVER_TRANSLATION:
        print("pydev debugger: client OS: %s" % (os,))

    _normcase_from_client = normcase
    if os == "WINDOWS":
        # Client in Windows and server in Unix, we need to normalize the case.
        if not IS_WINDOWS:
            _normcase_from_client = _normcase_windows

    else:
        # Client in Unix and server in Windows, we can't normalize the case.
        if IS_WINDOWS:
            _normcase_from_client = _normcase_linux

    if prev != os:
        _ide_os = os
        # We need to (re)setup how the client <-> server translation works to provide proper separators.
        setup_client_server_paths(_last_client_server_paths_set)


# Caches filled as requested during the debug session.
NORM_PATHS_CONTAINER = {}
NORM_PATHS_AND_BASE_CONTAINER = {}


def canonical_normalized_path(filename):
    """
    This returns a filename that is canonical and it's meant to be used internally
    to store information on breakpoints and see if there's any hit on it.

    Note that this version is only internal as it may not match the case and
    may have symlinks resolved (and thus may not match what the user expects
    in the editor).
    """
    return get_abs_path_real_path_and_base_from_file(filename)[1]


def absolute_path(filename):
    """
    Provides a version of the filename that's absolute (and NOT normalized).
    """
    return get_abs_path_real_path_and_base_from_file(filename)[0]


def basename(filename):
    """
    Provides the basename for a file.
    """
    return get_abs_path_real_path_and_base_from_file(filename)[2]


# Returns tuple of absolute path and real path for given filename
def _abs_and_canonical_path(filename, NORM_PATHS_CONTAINER=NORM_PATHS_CONTAINER):
    try:
        return NORM_PATHS_CONTAINER[filename]
    except:
        if filename.__class__ != str:
            raise AssertionError("Paths passed to _abs_and_canonical_path must be str. Found: %s (%s)" % (filename, type(filename)))
        if os is None:  # Interpreter shutdown
            return filename, filename

        os_path = os.path
        if os_path is None:  # Interpreter shutdown
            return filename, filename

        os_path_abspath = os_path.abspath
        os_path_isabs = os_path.isabs

        if os_path_abspath is None or os_path_isabs is None or os_path_real_path is None:  # Interpreter shutdown
            return filename, filename

        isabs = os_path_isabs(filename)

        if _global_resolve_symlinks:
            os_path_abspath = os_path_real_path

        normalize = False
        abs_path = _apply_func_and_normalize_case(filename, os_path_abspath, isabs, normalize)

        normalize = True
        real_path = _apply_func_and_normalize_case(filename, os_path_real_path, isabs, normalize)

        # cache it for fast access later
        NORM_PATHS_CONTAINER[filename] = abs_path, real_path
        return abs_path, real_path


def _get_relative_filename_abs_path(filename, func, os_path_exists=os_path_exists):
    # If we have a relative path and the file does not exist when made absolute, try to
    # resolve it based on the sys.path entries.
    for p in sys.path:
        r = func(os.path.join(p, filename))
        if os_path_exists(r):
            return r

    # We couldn't find the real file for the relative path. Resolve it as if it was in
    # a library (so that it's considered a library file and not a project file).
    r = func(os.path.join(_library_dir, filename))
    return r


def _apply_func_and_normalize_case(filename, func, isabs, normalize_case, os_path_exists=os_path_exists, join=join):
    if filename.startswith("<"):
        # Not really a file, rather a synthetic name like <string> or <ipython-...>;
        # shouldn't be normalized.
        return filename

    r = func(filename)

    if not isabs:
        if not os_path_exists(r):
            r = _get_relative_filename_abs_path(filename, func)

    ind = r.find(".zip")
    if ind == -1:
        ind = r.find(".egg")
    if ind != -1:
        ind += 4
        zip_path = r[:ind]
        inner_path = r[ind:]
        if inner_path.startswith("!"):
            # Note (fabioz): although I can replicate this by creating a file ending as
            # .zip! or .egg!, I don't really know what's the real-world case for this
            # (still kept as it was added by @jetbrains, but it should probably be reviewed
            # later on).
            # Note 2: it goes hand-in-hand with 'exists'.
            inner_path = inner_path[1:]
            zip_path = zip_path + "!"

        if inner_path.startswith("/") or inner_path.startswith("\\"):
            inner_path = inner_path[1:]
        if inner_path:
            if normalize_case:
                r = join(normcase(zip_path), inner_path)
            else:
                r = join(zip_path, inner_path)
            return r

    if normalize_case:
        r = normcase(r)
    return r


_ZIP_SEARCH_CACHE = {}
_NOT_FOUND_SENTINEL = object()


def exists(filename):
    if os_path_exists(filename):
        return True

    if not os.path.isabs(filename):
        filename = _get_relative_filename_abs_path(filename, os.path.abspath)
        if os_path_exists(filename):
            return True

    ind = filename.find(".zip")
    if ind == -1:
        ind = filename.find(".egg")

    if ind != -1:
        ind += 4
        zip_path = filename[:ind]
        inner_path = filename[ind:]
        if inner_path.startswith("!"):
            # Note (fabioz): although I can replicate this by creating a file ending as
            # .zip! or .egg!, I don't really know what's the real-world case for this
            # (still kept as it was added by @jetbrains, but it should probably be reviewed
            # later on).
            # Note 2: it goes hand-in-hand with '_apply_func_and_normalize_case'.
            inner_path = inner_path[1:]
            zip_path = zip_path + "!"

        zip_file_obj = _ZIP_SEARCH_CACHE.get(zip_path, _NOT_FOUND_SENTINEL)
        if zip_file_obj is None:
            return False
        elif zip_file_obj is _NOT_FOUND_SENTINEL:
            try:
                import zipfile

                zip_file_obj = zipfile.ZipFile(zip_path, "r")
                _ZIP_SEARCH_CACHE[zip_path] = zip_file_obj
            except:
                _ZIP_SEARCH_CACHE[zip_path] = _NOT_FOUND_SENTINEL
                return False

        try:
            if inner_path.startswith("/") or inner_path.startswith("\\"):
                inner_path = inner_path[1:]

            _info = zip_file_obj.getinfo(inner_path.replace("\\", "/"))

            return join(zip_path, inner_path)
        except KeyError:
            return False

    else:
        pydev_log.debug("os.path.exists(%r) returned False.", filename)

    return False


try:
    report = pydev_log.critical
    if DISABLE_FILE_VALIDATION:
        report = pydev_log.debug

    try:
        code = os_path_real_path.func_code
    except AttributeError:
        code = os_path_real_path.__code__

    if code.co_filename.startswith("<frozen"):
        # See: https://github.com/fabioz/PyDev.Debugger/issues/213
        report("Debugger warning: It seems that frozen modules are being used, which may")
        report("make the debugger miss breakpoints. Please pass -Xfrozen_modules=off")
        report("to python to disable frozen modules.")
        report("Note: Debugging will proceed. Set PYDEVD_DISABLE_FILE_VALIDATION=1 to disable this validation.")

    elif not os.path.isabs(code.co_filename):
        report("Debugger warning: The os.path.realpath.__code__.co_filename (%s)", code.co_filename)
        report("is not absolute, which may make the debugger miss breakpoints.")
        report("Note: Debugging will proceed. Set PYDEVD_DISABLE_FILE_VALIDATION=1 to disable this validation.")

    elif not exists(code.co_filename):  # Note: checks for files inside .zip containers.
        report("Debugger warning: It seems the debugger cannot find os.path.realpath.__code__.co_filename (%s).", code.co_filename)
        report("This may make the debugger miss breakpoints in the standard library.")
        report("Note: Debugging will proceed. Set PYDEVD_DISABLE_FILE_VALIDATION=1 to disable this validation.")
except:
    # Don't fail if there's something not correct here -- but at least print it to the user so that we can correct that
    pydev_log.exception()

# Note: as these functions may be rebound, users should always import
# pydevd_file_utils and then use:
#
# pydevd_file_utils.map_file_to_client
# pydevd_file_utils.map_file_to_server
#
# instead of importing any of those names to a given scope.


def _path_to_expected_str(filename):
    if isinstance(filename, bytes):
        filename = filename.decode(file_system_encoding)

    return filename


def _original_file_to_client(filename, cache={}):
    try:
        return cache[filename]
    except KeyError:
        translated = _path_to_expected_str(get_path_with_real_case(absolute_path(filename)))
        cache[filename] = (translated, False)
    return cache[filename]


def _original_map_file_to_server(filename):
    # By default just mapping to the server does nothing if there are no mappings (usually
    # afterwards the debugger must do canonical_normalized_path to get a normalized version).
    return filename


map_file_to_client = _original_file_to_client
map_file_to_server = _original_map_file_to_server


def _fix_path(path, sep, add_end_sep=False):
    if add_end_sep:
        if not path.endswith("/") and not path.endswith("\\"):
            path += "/"
    else:
        if path.endswith("/") or path.endswith("\\"):
            path = path[:-1]

    if sep != "/":
        path = path.replace("/", sep)

    if path.startswith("."):
        # We need the full path if this relative because all comparisons below
        # check if the path is substring of another
        path = os.path.realpath(path)

    return path


_last_client_server_paths_set = []

_source_reference_to_frame_id = {}
_source_reference_to_server_filename = {}
_line_cache_source_reference_to_server_filename = {}
_client_filename_in_utf8_to_source_reference = {}
_next_source_reference = partial(next, itertools.count(1))


def get_client_filename_source_reference(client_filename):
    return _client_filename_in_utf8_to_source_reference.get(client_filename, 0)


def get_server_filename_from_source_reference(source_reference):
    return _source_reference_to_server_filename.get(source_reference, "")


def create_source_reference_for_linecache(server_filename):
    source_reference = _next_source_reference()
    pydev_log.debug("Created linecache id source reference: %s for server filename: %s", source_reference, server_filename)
    _line_cache_source_reference_to_server_filename[source_reference] = server_filename
    return source_reference


def get_source_reference_filename_from_linecache(source_reference):
    return _line_cache_source_reference_to_server_filename.get(source_reference)


def create_source_reference_for_frame_id(frame_id, original_filename):
    source_reference = _next_source_reference()
    pydev_log.debug("Created frame id source reference: %s for frame id: %s (%s)", source_reference, frame_id, original_filename)
    _source_reference_to_frame_id[source_reference] = frame_id
    return source_reference


def get_frame_id_from_source_reference(source_reference):
    return _source_reference_to_frame_id.get(source_reference)


_global_resolve_symlinks = is_true_in_env("PYDEVD_RESOLVE_SYMLINKS")


def set_resolve_symlinks(resolve_symlinks):
    global _global_resolve_symlinks
    _global_resolve_symlinks = resolve_symlinks


def setup_client_server_paths(paths):
    """paths is the same format as PATHS_FROM_ECLIPSE_TO_PYTHON"""

    global map_file_to_client
    global map_file_to_server
    global _last_client_server_paths_set
    global _next_source_reference

    _last_client_server_paths_set = paths[:]

    _source_reference_to_server_filename.clear()
    _client_filename_in_utf8_to_source_reference.clear()
    _next_source_reference = partial(next, itertools.count(1))

    # Work on the client and server slashes.
    python_sep = "\\" if IS_WINDOWS else "/"
    eclipse_sep = "\\" if _ide_os == "WINDOWS" else "/"

    norm_filename_to_server_container = {}
    norm_filename_to_client_container = {}

    initial_paths = []
    initial_paths_with_end_sep = []

    paths_from_eclipse_to_python = []
    paths_from_eclipse_to_python_with_end_sep = []

    # Apply normcase to the existing paths to follow the os preferences.

    for i, (path0, path1) in enumerate(paths):
        force_only_slash = path0.endswith(("/", "\\")) and path1.endswith(("/", "\\"))

        if not force_only_slash:
            path0 = _fix_path(path0, eclipse_sep, False)
            path1 = _fix_path(path1, python_sep, False)
            initial_paths.append((path0, path1))
            paths_from_eclipse_to_python.append((_normcase_from_client(path0), normcase(path1)))

        # Now, make a version with a slash in the end.
        path0 = _fix_path(path0, eclipse_sep, True)
        path1 = _fix_path(path1, python_sep, True)
        initial_paths_with_end_sep.append((path0, path1))
        paths_from_eclipse_to_python_with_end_sep.append((_normcase_from_client(path0), normcase(path1)))

    if DEBUG_CLIENT_SERVER_TRANSLATION:
        pydev_log.critical(
            "pydev debugger: paths_from_eclipse_to_python %s",
            ", ".join(
                [
                    '"%s=>%s"' % (x[0], x[1])
                    for x in paths_from_eclipse_to_python
                ]
            ),
        )
    # Fix things so that we always match the versions with a slash in the end first.
    initial_paths = initial_paths_with_end_sep + initial_paths
    paths_from_eclipse_to_python = paths_from_eclipse_to_python_with_end_sep + paths_from_eclipse_to_python

    if not paths_from_eclipse_to_python:
        # no translation step needed (just inline the calls)
        map_file_to_client = _original_file_to_client
        map_file_to_server = _original_map_file_to_server
        return

    # only setup translation functions if absolutely needed!
    def _map_file_to_server(filename, cache=norm_filename_to_server_container):
        # Eclipse will send the passed filename to be translated to the python process
        # So, this would be 'NormFileFromEclipseToPython'
        try:
            return cache[filename]
        except KeyError:
            if eclipse_sep != python_sep:
                # Make sure that the separators are what we expect from the IDE.
                filename = filename.replace(python_sep, eclipse_sep)

            # used to translate a path from the client to the debug server
            translated = filename
            translated_normalized = _normcase_from_client(filename)
            for eclipse_prefix, server_prefix in paths_from_eclipse_to_python:
                if translated_normalized.startswith(eclipse_prefix):
                    found_translation = True
                    if DEBUG_CLIENT_SERVER_TRANSLATION:
                        pydev_log.critical("pydev debugger: replacing to server: %s", filename)
                    translated = server_prefix + filename[len(eclipse_prefix) :]
                    if DEBUG_CLIENT_SERVER_TRANSLATION:
                        pydev_log.critical("pydev debugger: sent to server: %s - matched prefix: %s", translated, eclipse_prefix)
                    break
            else:
                found_translation = False

            # Note that when going to the server, we do the replace first and only later do the norm file.
            if eclipse_sep != python_sep:
                translated = translated.replace(eclipse_sep, python_sep)

            if found_translation:
                # Note: we don't normalize it here, this must be done as a separate
                # step by the caller.
                translated = absolute_path(translated)
            else:
                if not os_path_exists(translated):
                    if not translated.startswith("<"):
                        # This is a configuration error, so, write it always so
                        # that the user can fix it.
                        error_once(
                            'pydev debugger: unable to find translation for: "%s" in [%s] (please revise your path mappings).\n',
                            filename,
                            ", ".join(['"%s"' % (x[0],) for x in paths_from_eclipse_to_python]),
                        )
                else:
                    # It's possible that we had some round trip (say, we sent /usr/lib and received
                    # it back, so, having no translation is ok too).

                    # Note: we don't normalize it here, this must be done as a separate
                    # step by the caller.
                    translated = absolute_path(translated)

            cache[filename] = translated
            return translated

    def _map_file_to_client(filename, cache=norm_filename_to_client_container):
        # The result of this method will be passed to eclipse
        # So, this would be 'NormFileFromPythonToEclipse'
        try:
            return cache[filename]
        except KeyError:
            abs_path = absolute_path(filename)
            translated_proper_case = get_path_with_real_case(abs_path)
            translated_normalized = normcase(abs_path)

            path_mapping_applied = False

            if translated_normalized.lower() != translated_proper_case.lower():
                if DEBUG_CLIENT_SERVER_TRANSLATION:
                    pydev_log.critical(
                        "pydev debugger: translated_normalized changed path (from: %s to %s)", translated_proper_case, translated_normalized
                    )

            for i, (eclipse_prefix, python_prefix) in enumerate(paths_from_eclipse_to_python):
                if translated_normalized.startswith(python_prefix):
                    if DEBUG_CLIENT_SERVER_TRANSLATION:
                        pydev_log.critical("pydev debugger: replacing to client: %s", translated_normalized)

                    # Note: use the non-normalized version.
                    eclipse_prefix = initial_paths[i][0]
                    translated = eclipse_prefix + translated_proper_case[len(python_prefix) :]
                    if DEBUG_CLIENT_SERVER_TRANSLATION:
                        pydev_log.critical("pydev debugger: sent to client: %s - matched prefix: %s", translated, python_prefix)
                    path_mapping_applied = True
                    break
            else:
                if DEBUG_CLIENT_SERVER_TRANSLATION:
                    pydev_log.critical(
                        "pydev debugger: to client: unable to find matching prefix for: %s in %s",
                        translated_normalized,
                        [x[1] for x in paths_from_eclipse_to_python],
                    )
                translated = translated_proper_case

            if eclipse_sep != python_sep:
                translated = translated.replace(python_sep, eclipse_sep)

            translated = _path_to_expected_str(translated)

            # The resulting path is not in the python process, so, we cannot do a normalize the path here,
            # only at the beginning of this method.
            cache[filename] = (translated, path_mapping_applied)

            if translated not in _client_filename_in_utf8_to_source_reference:
                if path_mapping_applied:
                    source_reference = 0
                else:
                    source_reference = _next_source_reference()
                    pydev_log.debug("Created source reference: %s for untranslated path: %s", source_reference, filename)

                _client_filename_in_utf8_to_source_reference[translated] = source_reference
                _source_reference_to_server_filename[source_reference] = filename

            return (translated, path_mapping_applied)

    map_file_to_server = _map_file_to_server
    map_file_to_client = _map_file_to_client


setup_client_server_paths(PATHS_FROM_ECLIPSE_TO_PYTHON)


# For given file f returns tuple of its absolute path, real path and base name
def get_abs_path_real_path_and_base_from_file(filename, NORM_PATHS_AND_BASE_CONTAINER=NORM_PATHS_AND_BASE_CONTAINER):
    try:
        return NORM_PATHS_AND_BASE_CONTAINER[filename]
    except:
        f = filename
        if not f:
            # i.e.: it's possible that the user compiled code with an empty string (consider
            # it as <string> in this case).
            f = "<string>"

        if f.startswith("<"):
            return f, normcase(f), f

        if _abs_and_canonical_path is None:  # Interpreter shutdown
            i = max(f.rfind("/"), f.rfind("\\"))
            return (f, f, f[i + 1 :])

        if f is not None:
            if f.endswith(".pyc"):
                f = f[:-1]
            elif f.endswith("$py.class"):
                f = f[: -len("$py.class")] + ".py"

        abs_path, canonical_normalized_filename = _abs_and_canonical_path(f)

        try:
            base = os_path_basename(canonical_normalized_filename)
        except AttributeError:
            # Error during shutdown.
            i = max(f.rfind("/"), f.rfind("\\"))
            base = f[i + 1 :]
        ret = abs_path, canonical_normalized_filename, base
        NORM_PATHS_AND_BASE_CONTAINER[filename] = ret
        return ret


def get_abs_path_real_path_and_base_from_frame(frame, NORM_PATHS_AND_BASE_CONTAINER=NORM_PATHS_AND_BASE_CONTAINER):
    try:
        return NORM_PATHS_AND_BASE_CONTAINER[frame.f_code.co_filename]
    except:
        # This one is just internal (so, does not need any kind of client-server translation)
        f = frame.f_code.co_filename

        if f is not None and f.startswith(("build/bdist.", "build\\bdist.")):
            # files from eggs in Python 2.7 have paths like build/bdist.linux-x86_64/egg/<path-inside-egg>
            f = frame.f_globals["__file__"]

        if get_abs_path_real_path_and_base_from_file is None:
            # Interpreter shutdown
            if not f:
                # i.e.: it's possible that the user compiled code with an empty string (consider
                # it as <string> in this case).
                f = "<string>"
            i = max(f.rfind("/"), f.rfind("\\"))
            return f, f, f[i + 1 :]

        ret = get_abs_path_real_path_and_base_from_file(f)
        # Also cache based on the frame.f_code.co_filename (if we had it inside build/bdist it can make a difference).
        NORM_PATHS_AND_BASE_CONTAINER[frame.f_code.co_filename] = ret
        return ret


def get_fullname(mod_name):
    import pkgutil

    try:
        loader = pkgutil.get_loader(mod_name)
    except:
        return None
    if loader is not None:
        for attr in ("get_filename", "_get_filename"):
            meth = getattr(loader, attr, None)
            if meth is not None:
                return meth(mod_name)
    return None


def get_package_dir(mod_name):
    for path in sys.path:
        mod_path = join(path, mod_name.replace(".", "/"))
        if os.path.isdir(mod_path):
            return mod_path
    return None

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\sql.py ===
#!~/.wine/drive_c/Python25/python.exe
# -*- coding: utf-8 -*-

# Copyright (c) 2009-2014, Mario Vilas
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice,this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
SQL database storage support.

@group Crash reporting:
    CrashDAO
"""

__revision__ = "$Id$"

__all__ = ["CrashDAO"]

import sqlite3
import datetime
import warnings

from sqlalchemy import create_engine, Column, ForeignKey, Sequence
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.interfaces import PoolListener
from sqlalchemy.orm import sessionmaker, deferred
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.types import Integer, BigInteger, Boolean, DateTime, String, LargeBinary, Enum, VARCHAR
from sqlalchemy.sql.expression import asc, desc

from crash import Crash, Marshaller, pickle, HIGHEST_PROTOCOL
from textio import CrashDump
import win32

# ------------------------------------------------------------------------------

try:
    from decorator import decorator
except ImportError:
    import functools

    def decorator(w):
        """
        The C{decorator} module was not found. You can install it from:
        U{http://pypi.python.org/pypi/decorator/}
        """

        def d(fn):
            @functools.wraps(fn)
            def x(*argv, **argd):
                return w(fn, *argv, **argd)

            return x

        return d

# ------------------------------------------------------------------------------


@compiles(String, "mysql")
@compiles(VARCHAR, "mysql")
def _compile_varchar_mysql(element, compiler, **kw):
    """MySQL hack to avoid the "VARCHAR requires a length" error."""
    if not element.length or element.length == "max":
        return "TEXT"
    else:
        return compiler.visit_VARCHAR(element, **kw)


# ------------------------------------------------------------------------------


class _SQLitePatch(PoolListener):
    """
    Used internally by L{BaseDAO}.

    After connecting to an SQLite database, ensure that the foreign keys
    support is enabled. If not, abort the connection.

    @see: U{http://sqlite.org/foreignkeys.html}
    """

    def connect(dbapi_connection, connection_record):
        """
        Called once by SQLAlchemy for each new SQLite DB-API connection.

        Here is where we issue some PRAGMA statements to configure how we're
        going to access the SQLite database.

        @param dbapi_connection:
            A newly connected raw SQLite DB-API connection.

        @param connection_record:
            Unused by this method.
        """
        try:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys = ON;")
                cursor.execute("PRAGMA foreign_keys;")
                if cursor.fetchone()[0] != 1:
                    raise Exception()
            finally:
                cursor.close()
        except Exception:
            dbapi_connection.close()
            raise sqlite3.Error()


# ------------------------------------------------------------------------------


class BaseDTO(object):
    """
    Customized declarative base for SQLAlchemy.
    """

    __table_args__ = {
        # Don't use MyISAM in MySQL. It doesn't support ON DELETE CASCADE.
        "mysql_engine": "InnoDB",
        # Don't use BlitzDB in Drizzle. It doesn't support foreign keys.
        "drizzle_engine": "InnoDB",
        # Collate to UTF-8.
        "mysql_charset": "utf8",
    }


BaseDTO = declarative_base(cls=BaseDTO)

# ------------------------------------------------------------------------------

# TODO: if using mssql, check it's at least SQL Server 2005
#       (LIMIT and OFFSET support is required).
# TODO: if using mysql, check it's at least MySQL 5.0.3
#       (nested transactions are required).
# TODO: maybe in mysql check the tables are not myisam?
# TODO: maybe create the database if it doesn't exist?
# TODO: maybe add a method to compact the database?
#       http://stackoverflow.com/questions/1875885
#       http://www.sqlite.org/lang_vacuum.html
#       http://dev.mysql.com/doc/refman/5.1/en/optimize-table.html
#       http://msdn.microsoft.com/en-us/library/ms174459(v=sql.90).aspx


class BaseDAO(object):
    """
    Data Access Object base class.

    @type _url: sqlalchemy.url.URL
    @ivar _url: Database connection URL.

    @type _dialect: str
    @ivar _dialect: SQL dialect currently being used.

    @type _driver: str
    @ivar _driver: Name of the database driver currently being used.
        To get the actual Python module use L{_url}.get_driver() instead.

    @type _session: sqlalchemy.orm.Session
    @ivar _session: Database session object.

    @type _new_session: class
    @cvar _new_session: Custom configured Session class used to create the
        L{_session} instance variable.

    @type _echo: bool
    @cvar _echo: Set to C{True} to print all SQL queries to standard output.
    """

    _echo = False

    _new_session = sessionmaker(autoflush=True, autocommit=True, expire_on_commit=True, weak_identity_map=True)

    def __init__(self, url, creator=None):
        """
        Connect to the database using the given connection URL.

        The current implementation uses SQLAlchemy and so it will support
        whatever database said module supports.

        @type  url: str
        @param url:
            URL that specifies the database to connect to.

            Some examples:
             - Opening an SQLite file:
               C{dao = CrashDAO("sqlite:///C:\\some\\path\\database.sqlite")}
             - Connecting to a locally installed SQL Express database:
               C{dao = CrashDAO("mssql://.\\SQLEXPRESS/Crashes?trusted_connection=yes")}
             - Connecting to a MySQL database running locally, using the
               C{oursql} library, authenticating as the "winappdbg" user with
               no password:
               C{dao = CrashDAO("mysql+oursql://winappdbg@localhost/Crashes")}
             - Connecting to a Postgres database running locally,
               authenticating with user and password:
               C{dao = CrashDAO("postgresql://winappdbg:winappdbg@localhost/Crashes")}

            For more information see the C{SQLAlchemy} documentation online:
            U{http://docs.sqlalchemy.org/en/latest/core/engines.html}

            Note that in all dialects except for SQLite the database
            must already exist. The tables schema, however, is created
            automatically when connecting for the first time.

            To create the database in MSSQL, you can use the
            U{SQLCMD<http://msdn.microsoft.com/en-us/library/ms180944.aspx>}
            command::
                sqlcmd -Q "CREATE DATABASE Crashes"

            In MySQL you can use something like the following::
                mysql -u root -e "CREATE DATABASE Crashes;"

            And in Postgres::
                createdb Crashes -h localhost -U winappdbg -p winappdbg -O winappdbg

            Some small changes to the schema may be tolerated (for example,
            increasing the maximum length of string columns, or adding new
            columns with default values). Of course, it's best to test it
            first before making changes in a live database. This all depends
            very much on the SQLAlchemy version you're using, but it's best
            to use the latest version always.

        @type  creator: callable
        @param creator: (Optional) Callback function that creates the SQL
            database connection.

            Normally it's not necessary to use this argument. However in some
            odd cases you may need to customize the database connection.
        """

        # Parse the connection URL.
        parsed_url = URL(url)
        schema = parsed_url.drivername
        if "+" in schema:
            dialect, driver = schema.split("+")
        else:
            dialect, driver = schema, "base"
        dialect = dialect.strip().lower()
        driver = driver.strip()

        # Prepare the database engine arguments.
        arguments = {"echo": self._echo}
        if dialect == "sqlite":
            arguments["module"] = sqlite3.dbapi2
            arguments["listeners"] = [_SQLitePatch()]
        if creator is not None:
            arguments["creator"] = creator

        # Load the database engine.
        engine = create_engine(url, **arguments)

        # Create a new session.
        session = self._new_session(bind=engine)

        # Create the required tables if they don't exist.
        BaseDTO.metadata.create_all(engine)
        # TODO: create a dialect specific index on the "signature" column.

        # Set the instance properties.
        self._url = parsed_url
        self._driver = driver
        self._dialect = dialect
        self._session = session

    def _transactional(self, method, *argv, **argd):
        """
        Begins a transaction and calls the given DAO method.

        If the method executes successfully the transaction is commited.

        If the method fails, the transaction is rolled back.

        @type  method: callable
        @param method: Bound method of this class or one of its subclasses.
            The first argument will always be C{self}.

        @return: The return value of the method call.

        @raise Exception: Any exception raised by the method.
        """
        self._session.begin(subtransactions=True)
        try:
            result = method(self, *argv, **argd)
            self._session.commit()
            return result
        except:
            self._session.rollback()
            raise


# ------------------------------------------------------------------------------


@decorator
def Transactional(fn, self, *argv, **argd):
    """
    Decorator that wraps DAO methods to handle transactions automatically.

    It may only work with subclasses of L{BaseDAO}.
    """
    return self._transactional(fn, *argv, **argd)


# ==============================================================================


# Generates all possible memory access flags.
def _gen_valid_access_flags():
    f = []
    for a1 in ("---", "R--", "RW-", "RC-", "--X", "R-X", "RWX", "RCX", "???"):
        for a2 in ("G", "-"):
            for a3 in ("N", "-"):
                for a4 in ("W", "-"):
                    f.append("%s %s%s%s" % (a1, a2, a3, a4))
    return tuple(f)


_valid_access_flags = _gen_valid_access_flags()

# Enumerated types for the memory table.
n_MEM_ACCESS_ENUM = {"name": "MEM_ACCESS_ENUM"}
n_MEM_ALLOC_ACCESS_ENUM = {"name": "MEM_ALLOC_ACCESS_ENUM"}
MEM_ACCESS_ENUM = Enum(*_valid_access_flags, **n_MEM_ACCESS_ENUM)
MEM_ALLOC_ACCESS_ENUM = Enum(*_valid_access_flags, **n_MEM_ALLOC_ACCESS_ENUM)
MEM_STATE_ENUM = Enum("Reserved", "Commited", "Free", "Unknown", name="MEM_STATE_ENUM")
MEM_TYPE_ENUM = Enum("Image", "Mapped", "Private", "Unknown", name="MEM_TYPE_ENUM")

# Cleanup the namespace.
del _gen_valid_access_flags
del _valid_access_flags
del n_MEM_ACCESS_ENUM
del n_MEM_ALLOC_ACCESS_ENUM

# ------------------------------------------------------------------------------


class MemoryDTO(BaseDTO):
    """
    Database mapping for memory dumps.
    """

    # Declare the table mapping.
    __tablename__ = "memory"
    id = Column(Integer, Sequence(__tablename__ + "_seq"), primary_key=True, autoincrement=True)
    crash_id = Column(Integer, ForeignKey("crashes.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    address = Column(BigInteger, nullable=False, index=True)
    size = Column(BigInteger, nullable=False)
    state = Column(MEM_STATE_ENUM, nullable=False)
    access = Column(MEM_ACCESS_ENUM)
    type = Column(MEM_TYPE_ENUM)
    alloc_base = Column(BigInteger)
    alloc_access = Column(MEM_ALLOC_ACCESS_ENUM)
    filename = Column(String)
    content = deferred(Column(LargeBinary))

    def __init__(self, crash_id, mbi):
        """
        Process a L{win32.MemoryBasicInformation} object for database storage.
        """

        # Crash ID.
        self.crash_id = crash_id

        # Address.
        self.address = mbi.BaseAddress

        # Size.
        self.size = mbi.RegionSize

        # State (free or allocated).
        if mbi.State == win32.MEM_RESERVE:
            self.state = "Reserved"
        elif mbi.State == win32.MEM_COMMIT:
            self.state = "Commited"
        elif mbi.State == win32.MEM_FREE:
            self.state = "Free"
        else:
            self.state = "Unknown"

        # Page protection bits (R/W/X/G).
        if mbi.State != win32.MEM_COMMIT:
            self.access = None
        else:
            self.access = self._to_access(mbi.Protect)

        # Type (file mapping, executable image, or private memory).
        if mbi.Type == win32.MEM_IMAGE:
            self.type = "Image"
        elif mbi.Type == win32.MEM_MAPPED:
            self.type = "Mapped"
        elif mbi.Type == win32.MEM_PRIVATE:
            self.type = "Private"
        elif mbi.Type == 0:
            self.type = None
        else:
            self.type = "Unknown"

        # Allocation info.
        self.alloc_base = mbi.AllocationBase
        if not mbi.AllocationProtect:
            self.alloc_access = None
        else:
            self.alloc_access = self._to_access(mbi.AllocationProtect)

        # Filename (for memory mappings).
        try:
            self.filename = mbi.filename
        except AttributeError:
            self.filename = None

        # Memory contents.
        try:
            self.content = mbi.content
        except AttributeError:
            self.content = None

    def _to_access(self, protect):
        if protect & win32.PAGE_NOACCESS:
            access = "--- "
        elif protect & win32.PAGE_READONLY:
            access = "R-- "
        elif protect & win32.PAGE_READWRITE:
            access = "RW- "
        elif protect & win32.PAGE_WRITECOPY:
            access = "RC- "
        elif protect & win32.PAGE_EXECUTE:
            access = "--X "
        elif protect & win32.PAGE_EXECUTE_READ:
            access = "R-X "
        elif protect & win32.PAGE_EXECUTE_READWRITE:
            access = "RWX "
        elif protect & win32.PAGE_EXECUTE_WRITECOPY:
            access = "RCX "
        else:
            access = "??? "
        if protect & win32.PAGE_GUARD:
            access += "G"
        else:
            access += "-"
        if protect & win32.PAGE_NOCACHE:
            access += "N"
        else:
            access += "-"
        if protect & win32.PAGE_WRITECOMBINE:
            access += "W"
        else:
            access += "-"
        return access

    def toMBI(self, getMemoryDump=False):
        """
        Returns a L{win32.MemoryBasicInformation} object using the data
        retrieved from the database.

        @type  getMemoryDump: bool
        @param getMemoryDump: (Optional) If C{True} retrieve the memory dump.
            Defaults to C{False} since this may be a costly operation.

        @rtype:  L{win32.MemoryBasicInformation}
        @return: Memory block information.
        """
        mbi = win32.MemoryBasicInformation()
        mbi.BaseAddress = self.address
        mbi.RegionSize = self.size
        mbi.State = self._parse_state(self.state)
        mbi.Protect = self._parse_access(self.access)
        mbi.Type = self._parse_type(self.type)
        if self.alloc_base is not None:
            mbi.AllocationBase = self.alloc_base
        else:
            mbi.AllocationBase = mbi.BaseAddress
        if self.alloc_access is not None:
            mbi.AllocationProtect = self._parse_access(self.alloc_access)
        else:
            mbi.AllocationProtect = mbi.Protect
        if self.filename is not None:
            mbi.filename = self.filename
        if getMemoryDump and self.content is not None:
            mbi.content = self.content
        return mbi

    @staticmethod
    def _parse_state(state):
        if state:
            if state == "Reserved":
                return win32.MEM_RESERVE
            if state == "Commited":
                return win32.MEM_COMMIT
            if state == "Free":
                return win32.MEM_FREE
        return 0

    @staticmethod
    def _parse_type(type):
        if type:
            if type == "Image":
                return win32.MEM_IMAGE
            if type == "Mapped":
                return win32.MEM_MAPPED
            if type == "Private":
                return win32.MEM_PRIVATE
            return -1
        return 0

    @staticmethod
    def _parse_access(access):
        if not access:
            return 0
        perm = access[:3]
        if perm == "R--":
            protect = win32.PAGE_READONLY
        elif perm == "RW-":
            protect = win32.PAGE_READWRITE
        elif perm == "RC-":
            protect = win32.PAGE_WRITECOPY
        elif perm == "--X":
            protect = win32.PAGE_EXECUTE
        elif perm == "R-X":
            protect = win32.PAGE_EXECUTE_READ
        elif perm == "RWX":
            protect = win32.PAGE_EXECUTE_READWRITE
        elif perm == "RCX":
            protect = win32.PAGE_EXECUTE_WRITECOPY
        else:
            protect = win32.PAGE_NOACCESS
        if access[5] == "G":
            protect = protect | win32.PAGE_GUARD
        if access[6] == "N":
            protect = protect | win32.PAGE_NOCACHE
        if access[7] == "W":
            protect = protect | win32.PAGE_WRITECOMBINE
        return protect


# ------------------------------------------------------------------------------


class CrashDTO(BaseDTO):
    """
    Database mapping for crash dumps.
    """

    # Table name.
    __tablename__ = "crashes"

    # Primary key.
    id = Column(Integer, Sequence(__tablename__ + "_seq"), primary_key=True, autoincrement=True)

    # Timestamp.
    timestamp = Column(DateTime, nullable=False, index=True)

    # Exploitability test.
    exploitable = Column(Integer, nullable=False)
    exploitability_rule = Column(String(32), nullable=False)
    exploitability_rating = Column(String(32), nullable=False)
    exploitability_desc = Column(String, nullable=False)

    # Platform description.
    os = Column(String(32), nullable=False)
    arch = Column(String(16), nullable=False)
    bits = Column(Integer, nullable=False)  # Integer(4) is deprecated :(

    # Event description.
    event = Column(String, nullable=False)
    pid = Column(Integer, nullable=False)
    tid = Column(Integer, nullable=False)
    pc = Column(BigInteger, nullable=False)
    sp = Column(BigInteger, nullable=False)
    fp = Column(BigInteger, nullable=False)
    pc_label = Column(String, nullable=False)

    # Exception description.
    exception = Column(String(64))
    exception_text = Column(String(64))
    exception_address = Column(BigInteger)
    exception_label = Column(String)
    first_chance = Column(Boolean)
    fault_type = Column(Integer)
    fault_address = Column(BigInteger)
    fault_label = Column(String)
    fault_disasm = Column(String)
    stack_trace = Column(String)

    # Environment description.
    command_line = Column(String)
    environment = Column(String)

    # Debug strings.
    debug_string = Column(String)

    # Notes.
    notes = Column(String)

    # Heuristic signature.
    signature = Column(String, nullable=False)

    # Pickled Crash object, minus the memory dump.
    data = deferred(Column(LargeBinary, nullable=False))

    def __init__(self, crash):
        """
        @type  crash: Crash
        @param crash: L{Crash} object to store into the database.
        """

        # Timestamp and signature.
        self.timestamp = datetime.datetime.fromtimestamp(crash.timeStamp)
        self.signature = pickle.dumps(crash.signature, protocol=0)

        # Marshalled Crash object, minus the memory dump.
        # This code is *not* thread safe!
        memoryMap = crash.memoryMap
        try:
            crash.memoryMap = None
            self.data = buffer(Marshaller.dumps(crash))
        finally:
            crash.memoryMap = memoryMap

        # Exploitability test.
        self.exploitability_rating, self.exploitability_rule, self.exploitability_desc = crash.isExploitable()

        # Exploitability test as an integer result (for sorting).
        self.exploitable = [
            "Not an exception",
            "Not exploitable",
            "Not likely exploitable",
            "Unknown",
            "Probably exploitable",
            "Exploitable",
        ].index(self.exploitability_rating)

        # Platform description.
        self.os = crash.os
        self.arch = crash.arch
        self.bits = crash.bits

        # Event description.
        self.event = crash.eventName
        self.pid = crash.pid
        self.tid = crash.tid
        self.pc = crash.pc
        self.sp = crash.sp
        self.fp = crash.fp
        self.pc_label = crash.labelPC

        # Exception description.
        self.exception = crash.exceptionName
        self.exception_text = crash.exceptionDescription
        self.exception_address = crash.exceptionAddress
        self.exception_label = crash.exceptionLabel
        self.first_chance = crash.firstChance
        self.fault_type = crash.faultType
        self.fault_address = crash.faultAddress
        self.fault_label = crash.faultLabel
        self.fault_disasm = CrashDump.dump_code(crash.faultDisasm, crash.pc)
        self.stack_trace = CrashDump.dump_stack_trace_with_labels(crash.stackTracePretty)

        # Command line.
        self.command_line = crash.commandLine

        # Environment.
        if crash.environment:
            envList = crash.environment.items()
            envList.sort()
            environment = ""
            for envKey, envVal in envList:
                # Must concatenate here instead of using a substitution,
                # so strings can be automatically promoted to Unicode.
                environment += envKey + "=" + envVal + "\n"
            if environment:
                self.environment = environment

        # Debug string.
        self.debug_string = crash.debugString

        # Notes.
        self.notes = crash.notesReport()

    def toCrash(self, getMemoryDump=False):
        """
        Returns a L{Crash} object using the data retrieved from the database.

        @type  getMemoryDump: bool
        @param getMemoryDump: If C{True} retrieve the memory dump.
            Defaults to C{False} since this may be a costly operation.

        @rtype:  L{Crash}
        @return: Crash object.
        """
        crash = Marshaller.loads(str(self.data))
        if not isinstance(crash, Crash):
            raise TypeError("Expected Crash instance, got %s instead" % type(crash))
        crash._rowid = self.id
        if not crash.memoryMap:
            memory = getattr(self, "memory", [])
            if memory:
                crash.memoryMap = [dto.toMBI(getMemoryDump) for dto in memory]
        return crash


# ==============================================================================

# TODO: add a method to modify already stored crash dumps.


class CrashDAO(BaseDAO):
    """
    Data Access Object to read, write and search for L{Crash} objects in a
    database.
    """

    @Transactional
    def add(self, crash, allow_duplicates=True):
        """
        Add a new crash dump to the database, optionally filtering them by
        signature to avoid duplicates.

        @type  crash: L{Crash}
        @param crash: Crash object.

        @type  allow_duplicates: bool
        @param allow_duplicates: (Optional)
            C{True} to always add the new crash dump.
            C{False} to only add the crash dump if no other crash with the
            same signature is found in the database.

            Sometimes, your fuzzer turns out to be I{too} good. Then you find
            youself browsing through gigabytes of crash dumps, only to find
            a handful of actual bugs in them. This simple heuristic filter
            saves you the trouble by discarding crashes that seem to be similar
            to another one you've already found.
        """

        # Filter out duplicated crashes, if requested.
        if not allow_duplicates:
            signature = pickle.dumps(crash.signature, protocol=0)
            if self._session.query(CrashDTO.id).filter_by(signature=signature).count() > 0:
                return

        # Fill out a new row for the crashes table.
        crash_id = self.__add_crash(crash)

        # Fill out new rows for the memory dump.
        self.__add_memory(crash_id, crash.memoryMap)

        # On success set the row ID for the Crash object.
        # WARNING: In nested calls, make sure to delete
        # this property before a session rollback!
        crash._rowid = crash_id

    # Store the Crash object into the crashes table.
    def __add_crash(self, crash):
        session = self._session
        r_crash = None
        try:
            # Fill out a new row for the crashes table.
            r_crash = CrashDTO(crash)
            session.add(r_crash)

            # Flush and get the new row ID.
            session.flush()
            crash_id = r_crash.id

        finally:
            try:
                # Make the ORM forget the CrashDTO object.
                if r_crash is not None:
                    session.expire(r_crash)

            finally:
                # Delete the last reference to the CrashDTO
                # object, so the Python garbage collector claims it.
                del r_crash

        # Return the row ID.
        return crash_id

    # Store the memory dump into the memory table.
    def __add_memory(self, crash_id, memoryMap):
        session = self._session
        if memoryMap:
            for mbi in memoryMap:
                r_mem = MemoryDTO(crash_id, mbi)
                session.add(r_mem)
                session.flush()

    @Transactional
    def find(self, signature=None, order=0, since=None, until=None, offset=None, limit=None):
        """
        Retrieve all crash dumps in the database, optionally filtering them by
        signature and timestamp, and/or sorting them by timestamp.

        Results can be paged to avoid consuming too much memory if the database
        is large.

        @see: L{find_by_example}

        @type  signature: object
        @param signature: (Optional) Return only through crashes matching
            this signature. See L{Crash.signature} for more details.

        @type  order: int
        @param order: (Optional) Sort by timestamp.
            If C{== 0}, results are not sorted.
            If C{> 0}, results are sorted from older to newer.
            If C{< 0}, results are sorted from newer to older.

        @type  since: datetime
        @param since: (Optional) Return only the crashes after and
            including this date and time.

        @type  until: datetime
        @param until: (Optional) Return only the crashes before this date
            and time, not including it.

        @type  offset: int
        @param offset: (Optional) Skip the first I{offset} results.

        @type  limit: int
        @param limit: (Optional) Return at most I{limit} results.

        @rtype:  list(L{Crash})
        @return: List of Crash objects.
        """

        # Validate the parameters.
        if since and until and since > until:
            warnings.warn("CrashDAO.find() got the 'since' and 'until'" " arguments reversed, corrected automatically.")
            since, until = until, since
        if limit is not None and not limit:
            warnings.warn("CrashDAO.find() was set a limit of 0 results," " returning without executing a query.")
            return []

        # Build the SQL query.
        query = self._session.query(CrashDTO)
        if signature is not None:
            sig_pickled = pickle.dumps(signature, protocol=0)
            query = query.filter(CrashDTO.signature == sig_pickled)
        if since:
            query = query.filter(CrashDTO.timestamp >= since)
        if until:
            query = query.filter(CrashDTO.timestamp < until)
        if order:
            if order > 0:
                query = query.order_by(asc(CrashDTO.timestamp))
            else:
                query = query.order_by(desc(CrashDTO.timestamp))
        else:
            # Default ordering is by row ID, to get consistent results.
            # Also some database engines require ordering when using offsets.
            query = query.order_by(asc(CrashDTO.id))
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        # Execute the SQL query and convert the results.
        try:
            return [dto.toCrash() for dto in query.all()]
        except NoResultFound:
            return []

    @Transactional
    def find_by_example(self, crash, offset=None, limit=None):
        """
        Find all crash dumps that have common properties with the crash dump
        provided.

        Results can be paged to avoid consuming too much memory if the database
        is large.

        @see: L{find}

        @type  crash: L{Crash}
        @param crash: Crash object to compare with. Fields set to C{None} are
            ignored, all other fields but the signature are used in the
            comparison.

            To search for signature instead use the L{find} method.

        @type  offset: int
        @param offset: (Optional) Skip the first I{offset} results.

        @type  limit: int
        @param limit: (Optional) Return at most I{limit} results.

        @rtype:  list(L{Crash})
        @return: List of similar crash dumps found.
        """

        # Validate the parameters.
        if limit is not None and not limit:
            warnings.warn("CrashDAO.find_by_example() was set a limit of 0" " results, returning without executing a query.")
            return []

        # Build the query.
        query = self._session.query(CrashDTO)

        # Order by row ID to get consistent results.
        # Also some database engines require ordering when using offsets.
        query = query.asc(CrashDTO.id)

        # Build a CrashDTO from the Crash object.
        dto = CrashDTO(crash)

        # Filter all the fields in the crashes table that are present in the
        # CrashDTO object and not set to None, except for the row ID.
        for name, column in compat.iteritems(CrashDTO.__dict__):
            if not name.startswith("__") and name not in ("id", "signature", "data"):
                if isinstance(column, Column):
                    value = getattr(dto, name, None)
                    if value is not None:
                        query = query.filter(column == value)

        # Page the query.
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        # Execute the SQL query and convert the results.
        try:
            return [dto.toCrash() for dto in query.all()]
        except NoResultFound:
            return []

    @Transactional
    def count(self, signature=None):
        """
        Counts how many crash dumps have been stored in this database.
        Optionally filters the count by heuristic signature.

        @type  signature: object
        @param signature: (Optional) Count only the crashes that match
            this signature. See L{Crash.signature} for more details.

        @rtype:  int
        @return: Count of crash dumps stored in this database.
        """
        query = self._session.query(CrashDTO.id)
        if signature:
            sig_pickled = pickle.dumps(signature, protocol=0)
            query = query.filter_by(signature=sig_pickled)
        return query.count()

    @Transactional
    def delete(self, crash):
        """
        Remove the given crash dump from the database.

        @type  crash: L{Crash}
        @param crash: Crash dump to remove.
        """
        query = self._session.query(CrashDTO).filter_by(id=crash._rowid)
        query.delete(synchronize_session=False)
        del crash._rowid

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\litellm_pre_call_utils.py ===
import asyncio
import copy
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from fastapi import Request
from starlette.datastructures import Headers

import litellm
from litellm._logging import verbose_logger, verbose_proxy_logger
from litellm._service_logger import ServiceLogging
from litellm.litellm_core_utils.safe_json_loads import safe_json_loads
from litellm.proxy._types import (
    AddTeamCallback,
    CommonProxyErrors,
    LitellmDataForBackendLLMCall,
    SpecialHeaders,
    TeamCallbackMetadata,
    UserAPIKeyAuth,
)
from litellm.proxy.auth.route_checks import RouteChecks
from litellm.router import Router
from litellm.types.llms.anthropic import ANTHROPIC_API_HEADERS
from litellm.types.services import ServiceTypes
from litellm.types.utils import (
    ProviderSpecificHeader,
    StandardLoggingUserAPIKeyMetadata,
    SupportedCacheControls,
)

service_logger_obj = ServiceLogging()  # used for tracking latency on OTEL


if TYPE_CHECKING:
    from litellm.proxy.proxy_server import ProxyConfig as _ProxyConfig

    ProxyConfig = _ProxyConfig
else:
    ProxyConfig = Any


def parse_cache_control(cache_control):
    cache_dict = {}
    directives = cache_control.split(", ")

    for directive in directives:
        if "=" in directive:
            key, value = directive.split("=")
            cache_dict[key] = value
        else:
            cache_dict[directive] = True

    return cache_dict


def _get_metadata_variable_name(request: Request) -> str:
    """
    Helper to return what the "metadata" field should be called in the request data

    For all /thread or /assistant endpoints we need to call this "litellm_metadata"

    For ALL other endpoints we call this "metadata
    """
    if RouteChecks._is_assistants_api_request(request):
        return "litellm_metadata"

    LITELLM_METADATA_ROUTES = [
        "batches",
        "/v1/messages",
        "responses",
        "files",
    ]

    if any(
        [
            litellm_metadata_route in request.url.path
            for litellm_metadata_route in LITELLM_METADATA_ROUTES
        ]
    ):
        return "litellm_metadata"
    else:
        return "metadata"


def safe_add_api_version_from_query_params(data: dict, request: Request):
    try:
        if hasattr(request, "query_params"):
            query_params = dict(request.query_params)
            if "api-version" in query_params:
                data["api_version"] = query_params["api-version"]
    except KeyError:
        pass
    except Exception as e:
        verbose_logger.exception(
            "error checking api version in query params: %s", str(e)
        )


def convert_key_logging_metadata_to_callback(
    data: AddTeamCallback, team_callback_settings_obj: Optional[TeamCallbackMetadata]
) -> TeamCallbackMetadata:
    if team_callback_settings_obj is None:
        team_callback_settings_obj = TeamCallbackMetadata()
    if data.callback_type == "success":
        if team_callback_settings_obj.success_callback is None:
            team_callback_settings_obj.success_callback = []

        if data.callback_name not in team_callback_settings_obj.success_callback:
            team_callback_settings_obj.success_callback.append(data.callback_name)
    elif data.callback_type == "failure":
        if team_callback_settings_obj.failure_callback is None:
            team_callback_settings_obj.failure_callback = []

        if data.callback_name not in team_callback_settings_obj.failure_callback:
            team_callback_settings_obj.failure_callback.append(data.callback_name)
    elif (
        not data.callback_type or data.callback_type == "success_and_failure"
    ):  # assume 'success_and_failure' = litellm.callbacks
        if team_callback_settings_obj.success_callback is None:
            team_callback_settings_obj.success_callback = []
        if team_callback_settings_obj.failure_callback is None:
            team_callback_settings_obj.failure_callback = []
        if team_callback_settings_obj.callbacks is None:
            team_callback_settings_obj.callbacks = []

        if data.callback_name not in team_callback_settings_obj.success_callback:
            team_callback_settings_obj.success_callback.append(data.callback_name)

        if data.callback_name not in team_callback_settings_obj.failure_callback:
            team_callback_settings_obj.failure_callback.append(data.callback_name)

        if data.callback_name not in team_callback_settings_obj.callbacks:
            team_callback_settings_obj.callbacks.append(data.callback_name)

    for var, value in data.callback_vars.items():
        if team_callback_settings_obj.callback_vars is None:
            team_callback_settings_obj.callback_vars = {}
        team_callback_settings_obj.callback_vars[var] = str(
            litellm.utils.get_secret(value, default_value=value) or value
        )

    return team_callback_settings_obj


def _get_dynamic_logging_metadata(
    user_api_key_dict: UserAPIKeyAuth, proxy_config: ProxyConfig
) -> Optional[TeamCallbackMetadata]:
    callback_settings_obj: Optional[TeamCallbackMetadata] = None
    if (
        user_api_key_dict.metadata is not None
        and "logging" in user_api_key_dict.metadata
    ):
        for item in user_api_key_dict.metadata["logging"]:
            callback_settings_obj = convert_key_logging_metadata_to_callback(
                data=AddTeamCallback(**item),
                team_callback_settings_obj=callback_settings_obj,
            )
    elif (
        user_api_key_dict.team_metadata is not None
        and "callback_settings" in user_api_key_dict.team_metadata
    ):
        """
        callback_settings = {
            {
            'callback_vars': {'langfuse_public_key': 'pk', 'langfuse_secret_key': 'sk_'},
            'failure_callback': [],
            'success_callback': ['langfuse', 'langfuse']
        }
        }
        """
        team_metadata = user_api_key_dict.team_metadata
        callback_settings = team_metadata.get("callback_settings", None) or {}
        callback_settings_obj = TeamCallbackMetadata(**callback_settings)
        verbose_proxy_logger.debug(
            "Team callback settings activated: %s", callback_settings_obj
        )
    elif user_api_key_dict.team_id is not None:
        callback_settings_obj = (
            LiteLLMProxyRequestSetup.add_team_based_callbacks_from_config(
                team_id=user_api_key_dict.team_id, proxy_config=proxy_config
            )
        )
    return callback_settings_obj


def clean_headers(
    headers: Headers, litellm_key_header_name: Optional[str] = None
) -> dict:
    """
    Removes litellm api key from headers
    """
    special_headers = [v.value.lower() for v in SpecialHeaders._member_map_.values()]
    special_headers = special_headers
    if litellm_key_header_name is not None:
        special_headers.append(litellm_key_header_name.lower())
    clean_headers = {}

    for header, value in headers.items():
        if header.lower() not in special_headers:
            clean_headers[header] = value
    return clean_headers


class LiteLLMProxyRequestSetup:
    @staticmethod
    def _get_timeout_from_request(headers: dict) -> Optional[float]:
        """
        Workaround for client request from Vercel's AI SDK.

        Allow's user to set a timeout in the request headers.

        Example:

        ```js
        const openaiProvider = createOpenAI({
            baseURL: liteLLM.baseURL,
            apiKey: liteLLM.apiKey,
            compatibility: "compatible",
            headers: {
                "x-litellm-timeout": "90"
            },
        });
        ```
        """
        timeout_header = headers.get("x-litellm-timeout", None)
        if timeout_header is not None:
            return float(timeout_header)
        return None

    @staticmethod
    def _get_forwardable_headers(
        headers: Union[Headers, dict],
    ):
        """
        Get the headers that should be forwarded to the LLM Provider.

        Looks for any `x-` headers and sends them to the LLM Provider.
        """
        forwarded_headers = {}
        for header, value in headers.items():
            if header.lower().startswith("x-") and not header.lower().startswith(
                "x-stainless"
            ):  # causes openai sdk to fail
                forwarded_headers[header] = value

        return forwarded_headers

    @staticmethod
    def _get_case_insensitive_header(headers: dict, key: str) -> Optional[str]:
        """
        Get a case-insensitive header from the headers dictionary.
        """
        for header, value in headers.items():
            if header.lower() == key.lower():
                return value
        return None

    @staticmethod
    def get_user_from_headers(
        headers: dict, general_settings: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Get the user from the specified header if `general_settings.user_header_name` is set.
        """
        if general_settings is None:
            return None

        header_name = general_settings.get("user_header_name")
        if header_name is None or header_name == "":
            return None

        if not isinstance(header_name, str):
            raise TypeError(
                f"Expected user_header_name to be a str but got {type(header_name)}"
            )

        user = LiteLLMProxyRequestSetup._get_case_insensitive_header(
            headers, header_name
        )
        if user is not None:
            verbose_logger.info(f'found user "{user}" in header "{header_name}"')

        return user

    @staticmethod
    def get_openai_org_id_from_headers(
        headers: dict, general_settings: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Get the OpenAI Org ID from the headers.
        """
        if (
            general_settings is not None
            and general_settings.get("forward_openai_org_id") is not True
        ):
            return None
        for header, value in headers.items():
            if header.lower() == "openai-organization":
                verbose_logger.info(f"found openai org id: {value}, sending to llm")
                return value
        return None

    @staticmethod
    def add_headers_to_llm_call(
        headers: dict, user_api_key_dict: UserAPIKeyAuth
    ) -> dict:
        """
        Add headers to the LLM call

        - Checks request headers for forwardable headers
        - Checks if user information should be added to the headers
        """

        returned_headers = LiteLLMProxyRequestSetup._get_forwardable_headers(headers)

        if litellm.add_user_information_to_llm_headers is True:
            litellm_logging_metadata_headers = (
                LiteLLMProxyRequestSetup.get_sanitized_user_information_from_key(
                    user_api_key_dict=user_api_key_dict
                )
            )
            for k, v in litellm_logging_metadata_headers.items():
                if v is not None:
                    returned_headers["x-litellm-{}".format(k)] = v

        return returned_headers

    @staticmethod
    def add_litellm_data_for_backend_llm_call(
        *,
        headers: dict,
        user_api_key_dict: UserAPIKeyAuth,
        general_settings: Optional[Dict[str, Any]] = None,
    ) -> LitellmDataForBackendLLMCall:
        """
        - Adds user from headers
        - Adds forwardable headers
        - Adds org id
        """
        data = LitellmDataForBackendLLMCall()

        if (
            general_settings
            and general_settings.get("forward_client_headers_to_llm_api") is True
        ):
            _headers = LiteLLMProxyRequestSetup.add_headers_to_llm_call(
                headers, user_api_key_dict
            )
            if _headers != {}:
                data["headers"] = _headers
        _organization = LiteLLMProxyRequestSetup.get_openai_org_id_from_headers(
            headers, general_settings
        )
        if _organization is not None:
            data["organization"] = _organization

        timeout = LiteLLMProxyRequestSetup._get_timeout_from_request(headers)
        if timeout is not None:
            data["timeout"] = timeout

        return data

    @staticmethod
    def get_sanitized_user_information_from_key(
        user_api_key_dict: UserAPIKeyAuth,
    ) -> StandardLoggingUserAPIKeyMetadata:
        user_api_key_logged_metadata = StandardLoggingUserAPIKeyMetadata(
            user_api_key_hash=user_api_key_dict.api_key,  # just the hashed token
            user_api_key_alias=user_api_key_dict.key_alias,
            user_api_key_team_id=user_api_key_dict.team_id,
            user_api_key_user_id=user_api_key_dict.user_id,
            user_api_key_org_id=user_api_key_dict.org_id,
            user_api_key_team_alias=user_api_key_dict.team_alias,
            user_api_key_end_user_id=user_api_key_dict.end_user_id,
            user_api_key_user_email=user_api_key_dict.user_email,
            user_api_key_request_route=user_api_key_dict.request_route,
        )
        return user_api_key_logged_metadata

    @staticmethod
    def add_key_level_controls(
        key_metadata: dict, data: dict, _metadata_variable_name: str
    ):
        if "cache" in key_metadata:
            data["cache"] = {}
            if isinstance(key_metadata["cache"], dict):
                for k, v in key_metadata["cache"].items():
                    if k in SupportedCacheControls:
                        data["cache"][k] = v

        ## KEY-LEVEL SPEND LOGS / TAGS
        if "tags" in key_metadata and key_metadata["tags"] is not None:
            data[_metadata_variable_name]["tags"] = (
                LiteLLMProxyRequestSetup._merge_tags(
                    request_tags=data[_metadata_variable_name].get("tags"),
                    tags_to_add=key_metadata["tags"],
                )
            )
        if "spend_logs_metadata" in key_metadata and isinstance(
            key_metadata["spend_logs_metadata"], dict
        ):
            if "spend_logs_metadata" in data[_metadata_variable_name] and isinstance(
                data[_metadata_variable_name]["spend_logs_metadata"], dict
            ):
                for key, value in key_metadata["spend_logs_metadata"].items():
                    if (
                        key not in data[_metadata_variable_name]["spend_logs_metadata"]
                    ):  # don't override k-v pair sent by request (user request)
                        data[_metadata_variable_name]["spend_logs_metadata"][
                            key
                        ] = value
            else:
                data[_metadata_variable_name]["spend_logs_metadata"] = key_metadata[
                    "spend_logs_metadata"
                ]

        ## KEY-LEVEL DISABLE FALLBACKS
        if "disable_fallbacks" in key_metadata and isinstance(
            key_metadata["disable_fallbacks"], bool
        ):
            data["disable_fallbacks"] = key_metadata["disable_fallbacks"]
        return data

    @staticmethod
    def _merge_tags(request_tags: Optional[list], tags_to_add: Optional[list]) -> list:
        """
        Helper function to merge two lists of tags, ensuring no duplicates.

        Args:
            request_tags (Optional[list]): List of tags from the original request
            tags_to_add (Optional[list]): List of tags to add

        Returns:
            list: Combined list of unique tags
        """
        final_tags = []

        if request_tags and isinstance(request_tags, list):
            final_tags.extend(request_tags)

        if tags_to_add and isinstance(tags_to_add, list):
            for tag in tags_to_add:
                if tag not in final_tags:
                    final_tags.append(tag)

        return final_tags

    @staticmethod
    def add_team_based_callbacks_from_config(
        team_id: str,
        proxy_config: ProxyConfig,
    ) -> Optional[TeamCallbackMetadata]:
        """
        Add team-based callbacks from the config
        """
        team_config = proxy_config.load_team_config(team_id=team_id)
        if len(team_config.keys()) == 0:
            return None

        callback_vars_dict = {**team_config.get("callback_vars", team_config)}
        callback_vars_dict.pop("team_id", None)
        callback_vars_dict.pop("success_callback", None)
        callback_vars_dict.pop("failure_callback", None)

        return TeamCallbackMetadata(
            success_callback=team_config.get("success_callback", None),
            failure_callback=team_config.get("failure_callback", None),
            callback_vars=callback_vars_dict,
        )

    @staticmethod
    def add_request_tag_to_metadata(
        llm_router: Optional[Router],
        headers: dict,
        data: dict,
    ) -> Optional[List[str]]:
        tags = None

        # Check request headers for tags
        if "x-litellm-tags" in headers:
            if isinstance(headers["x-litellm-tags"], str):
                _tags = headers["x-litellm-tags"].split(",")
                tags = [tag.strip() for tag in _tags]
            elif isinstance(headers["x-litellm-tags"], list):
                tags = headers["x-litellm-tags"]
        # Check request body for tags
        if "tags" in data and isinstance(data["tags"], list):
            tags = data["tags"]

        return tags


async def add_litellm_data_to_request(  # noqa: PLR0915
    data: dict,
    request: Request,
    user_api_key_dict: UserAPIKeyAuth,
    proxy_config: ProxyConfig,
    general_settings: Optional[Dict[str, Any]] = None,
    version: Optional[str] = None,
):
    """
    Adds LiteLLM-specific data to the request.

    Args:
        data (dict): The data dictionary to be modified.
        request (Request): The incoming request.
        user_api_key_dict (UserAPIKeyAuth): The user API key dictionary.
        general_settings (Optional[Dict[str, Any]], optional): General settings. Defaults to None.
        version (Optional[str], optional): Version. Defaults to None.

    Returns:
        dict: The modified data dictionary.

    """

    from litellm.proxy.proxy_server import llm_router, premium_user

    safe_add_api_version_from_query_params(data, request)

    _headers = clean_headers(
        request.headers,
        litellm_key_header_name=(
            general_settings.get("litellm_key_header_name")
            if general_settings is not None
            else None
        ),
    )

    data.update(
        LiteLLMProxyRequestSetup.add_litellm_data_for_backend_llm_call(
            headers=_headers,
            user_api_key_dict=user_api_key_dict,
            general_settings=general_settings,
        )
    )

    # Parse user info from headers
    user = LiteLLMProxyRequestSetup.get_user_from_headers(_headers, general_settings)
    if user is not None:
        if user_api_key_dict.end_user_id is None:
            user_api_key_dict.end_user_id = user
        if "user" not in data:
            data["user"] = user

    # Include original request and headers in the data
    data["proxy_server_request"] = {
        "url": str(request.url),
        "method": request.method,
        "headers": _headers,
        "body": copy.copy(data),  # use copy instead of deepcopy
    }

    ## Dynamic api version (Azure OpenAI endpoints) ##
    try:
        query_params = request.query_params
        # Convert query parameters to a dictionary (optional)
        query_dict = dict(query_params)
    except KeyError:
        query_dict = {}

    ## check for api version in query params
    dynamic_api_version: Optional[str] = query_dict.get("api-version")

    if dynamic_api_version is not None:  # only pass, if set
        data["api_version"] = dynamic_api_version

    ## Forward any LLM API Provider specific headers in extra_headers
    add_provider_specific_headers_to_request(data=data, headers=_headers)

    ## Cache Controls
    headers = request.headers
    verbose_proxy_logger.debug("Request Headers: %s", headers)
    cache_control_header = headers.get("Cache-Control", None)
    if cache_control_header:
        cache_dict = parse_cache_control(cache_control_header)
        data["ttl"] = cache_dict.get("s-maxage")

    verbose_proxy_logger.debug("receiving data: %s", data)

    _metadata_variable_name = _get_metadata_variable_name(request)

    if data.get(_metadata_variable_name, None) is None:
        data[_metadata_variable_name] = {}

    # Parse metadata if it's a string (e.g., from multipart/form-data)
    if "metadata" in data and data["metadata"] is not None:
        if isinstance(data["metadata"], str):
            data["metadata"] = safe_json_loads(data["metadata"])
            if not isinstance(data["metadata"], dict):
                verbose_proxy_logger.warning(
                    f"Failed to parse 'metadata' as JSON dict. Received value: {data['metadata']}"
                )
        data[_metadata_variable_name]["requester_metadata"] = copy.deepcopy(
            data["metadata"]
        )

    user_api_key_logged_metadata = (
        LiteLLMProxyRequestSetup.get_sanitized_user_information_from_key(
            user_api_key_dict=user_api_key_dict
        )
    )
    data[_metadata_variable_name].update(user_api_key_logged_metadata)
    data[_metadata_variable_name][
        "user_api_key"
    ] = (
        user_api_key_dict.api_key
    )  # this is just the hashed token. [TODO]: replace variable name in repo.

    data[_metadata_variable_name]["user_api_end_user_max_budget"] = getattr(
        user_api_key_dict, "end_user_max_budget", None
    )

    data[_metadata_variable_name]["litellm_api_version"] = version

    if general_settings is not None:
        data[_metadata_variable_name]["global_max_parallel_requests"] = (
            general_settings.get("global_max_parallel_requests", None)
        )

    ### KEY-LEVEL Controls
    key_metadata = user_api_key_dict.metadata
    data = LiteLLMProxyRequestSetup.add_key_level_controls(
        key_metadata=key_metadata,
        data=data,
        _metadata_variable_name=_metadata_variable_name,
    )
    ## TEAM-LEVEL SPEND LOGS/TAGS
    team_metadata = user_api_key_dict.team_metadata or {}
    if "tags" in team_metadata and team_metadata["tags"] is not None:
        data[_metadata_variable_name]["tags"] = LiteLLMProxyRequestSetup._merge_tags(
            request_tags=data[_metadata_variable_name].get("tags"),
            tags_to_add=team_metadata["tags"],
        )
    if "spend_logs_metadata" in team_metadata and isinstance(
        team_metadata["spend_logs_metadata"], dict
    ):
        if "spend_logs_metadata" in data[_metadata_variable_name] and isinstance(
            data[_metadata_variable_name]["spend_logs_metadata"], dict
        ):
            for key, value in team_metadata["spend_logs_metadata"].items():
                if (
                    key not in data[_metadata_variable_name]["spend_logs_metadata"]
                ):  # don't override k-v pair sent by request (user request)
                    data[_metadata_variable_name]["spend_logs_metadata"][key] = value
        else:
            data[_metadata_variable_name]["spend_logs_metadata"] = team_metadata[
                "spend_logs_metadata"
            ]

    # Team spend, budget - used by prometheus.py
    data[_metadata_variable_name][
        "user_api_key_team_max_budget"
    ] = user_api_key_dict.team_max_budget
    data[_metadata_variable_name][
        "user_api_key_team_spend"
    ] = user_api_key_dict.team_spend
    data[_metadata_variable_name][
        "user_api_key_request_route"
    ] = user_api_key_dict.request_route

    # API Key spend, budget - used by prometheus.py
    data[_metadata_variable_name]["user_api_key_spend"] = user_api_key_dict.spend
    data[_metadata_variable_name][
        "user_api_key_max_budget"
    ] = user_api_key_dict.max_budget
    data[_metadata_variable_name][
        "user_api_key_model_max_budget"
    ] = user_api_key_dict.model_max_budget

    data[_metadata_variable_name]["user_api_key_metadata"] = user_api_key_dict.metadata
    _headers = dict(request.headers)
    _headers.pop(
        "authorization", None
    )  # do not store the original `sk-..` api key in the db
    data[_metadata_variable_name]["headers"] = _headers
    data[_metadata_variable_name]["endpoint"] = str(request.url)

    # OTEL Controls / Tracing
    # Add the OTEL Parent Trace before sending it LiteLLM
    data[_metadata_variable_name][
        "litellm_parent_otel_span"
    ] = user_api_key_dict.parent_otel_span
    _add_otel_traceparent_to_data(data, request=request)

    ### END-USER SPECIFIC PARAMS ###
    if user_api_key_dict.allowed_model_region is not None:
        data["allowed_model_region"] = user_api_key_dict.allowed_model_region
    start_time = time.time()
    ## [Enterprise Only]
    # Add User-IP Address
    requester_ip_address = ""
    if premium_user is True:
        # Only set the IP Address for Enterprise Users

        # logic for tracking IP Address
        if (
            general_settings is not None
            and general_settings.get("use_x_forwarded_for") is True
            and request is not None
            and hasattr(request, "headers")
            and "x-forwarded-for" in request.headers
        ):
            requester_ip_address = request.headers["x-forwarded-for"]
        elif (
            request is not None
            and hasattr(request, "client")
            and hasattr(request.client, "host")
            and request.client is not None
        ):
            requester_ip_address = request.client.host
    data[_metadata_variable_name]["requester_ip_address"] = requester_ip_address

    # Check if using tag based routing
    tags = LiteLLMProxyRequestSetup.add_request_tag_to_metadata(
        llm_router=llm_router,
        headers=dict(request.headers),
        data=data,
    )

    if tags is not None:
        data[_metadata_variable_name]["tags"] = tags

    # Team Callbacks controls
    callback_settings_obj = _get_dynamic_logging_metadata(
        user_api_key_dict=user_api_key_dict, proxy_config=proxy_config
    )
    if callback_settings_obj is not None:
        data["success_callback"] = callback_settings_obj.success_callback
        data["failure_callback"] = callback_settings_obj.failure_callback

        if callback_settings_obj.callback_vars is not None:
            # unpack callback_vars in data
            for k, v in callback_settings_obj.callback_vars.items():
                data[k] = v

    # Guardrails
    move_guardrails_to_metadata(
        data=data,
        _metadata_variable_name=_metadata_variable_name,
        user_api_key_dict=user_api_key_dict,
    )

    # Team Model Aliases
    _update_model_if_team_alias_exists(
        data=data,
        user_api_key_dict=user_api_key_dict,
    )

    verbose_proxy_logger.debug(
        "[PROXY] returned data from litellm_pre_call_utils: %s", data
    )

    ## ENFORCED PARAMS CHECK
    # loop through each enforced param
    # example enforced_params ['user', 'metadata', 'metadata.generation_name']
    _enforced_params_check(
        request_body=data,
        general_settings=general_settings,
        user_api_key_dict=user_api_key_dict,
        premium_user=premium_user,
    )

    end_time = time.time()
    asyncio.create_task(
        service_logger_obj.async_service_success_hook(
            service=ServiceTypes.PROXY_PRE_CALL,
            duration=end_time - start_time,
            call_type="add_litellm_data_to_request",
            start_time=start_time,
            end_time=end_time,
            parent_otel_span=user_api_key_dict.parent_otel_span,
        )
    )

    return data


def _update_model_if_team_alias_exists(
    data: dict,
    user_api_key_dict: UserAPIKeyAuth,
) -> None:
    """
    Update the model if the team alias exists

    If a alias map has been set on a team, then we want to make the request with the model the team alias is pointing to

    eg.
        - user calls `gpt-4o`
        - team.model_alias_map = {
            "gpt-4o": "gpt-4o-team-1"
        }
        - requested_model = "gpt-4o-team-1"
    """
    _model = data.get("model")
    if (
        _model
        and user_api_key_dict.team_model_aliases
        and _model in user_api_key_dict.team_model_aliases
    ):
        data["model"] = user_api_key_dict.team_model_aliases[_model]
    return


def _get_enforced_params(
    general_settings: Optional[dict], user_api_key_dict: UserAPIKeyAuth
) -> Optional[list]:
    enforced_params: Optional[list] = None
    if general_settings is not None:
        enforced_params = general_settings.get("enforced_params")
        if (
            "service_account_settings" in general_settings
            and check_if_token_is_service_account(user_api_key_dict) is True
        ):
            service_account_settings = general_settings["service_account_settings"]
            if "enforced_params" in service_account_settings:
                if enforced_params is None:
                    enforced_params = []
                enforced_params.extend(service_account_settings["enforced_params"])
    if user_api_key_dict.metadata.get("enforced_params", None) is not None:
        if enforced_params is None:
            enforced_params = []
        enforced_params.extend(user_api_key_dict.metadata["enforced_params"])
    return enforced_params


def check_if_token_is_service_account(valid_token: UserAPIKeyAuth) -> bool:
    """
    Checks if the token is a service account

    Returns:
        bool: True if token is a service account

    """
    if valid_token.metadata:
        if "service_account_id" in valid_token.metadata:
            return True
    return False


def _enforced_params_check(
    request_body: dict,
    general_settings: Optional[dict],
    user_api_key_dict: UserAPIKeyAuth,
    premium_user: bool,
) -> bool:
    """
    If enforced params are set, check if the request body contains the enforced params.
    """
    enforced_params: Optional[list] = _get_enforced_params(
        general_settings=general_settings, user_api_key_dict=user_api_key_dict
    )
    if enforced_params is None:
        return True
    if enforced_params is not None and premium_user is not True:
        raise ValueError(
            f"Enforced Params is an Enterprise feature. Enforced Params: {enforced_params}. {CommonProxyErrors.not_premium_user.value}"
        )

    for enforced_param in enforced_params:
        _enforced_params = enforced_param.split(".")
        if len(_enforced_params) == 1:
            if _enforced_params[0] not in request_body:
                raise ValueError(
                    f"BadRequest please pass param={_enforced_params[0]} in request body. This is a required param"
                )
        elif len(_enforced_params) == 2:
            # this is a scenario where user requires request['metadata']['generation_name'] to exist
            if _enforced_params[0] not in request_body:
                raise ValueError(
                    f"BadRequest please pass param={_enforced_params[0]} in request body. This is a required param"
                )
            if _enforced_params[1] not in request_body[_enforced_params[0]]:
                raise ValueError(
                    f"BadRequest please pass param=[{_enforced_params[0]}][{_enforced_params[1]}] in request body. This is a required param"
                )
    return True


def _add_guardrails_from_key_or_team_metadata(
    key_metadata: Optional[dict],
    team_metadata: Optional[dict],
    data: dict,
    metadata_variable_name: str,
) -> None:
    """
    Helper add guardrails from key or team metadata to request data

    Args:
        key_metadata: The key metadata dictionary to check for guardrails
        team_metadata: The team metadata dictionary to check for guardrails
        data: The request data to update
        metadata_variable_name: The name of the metadata field in data

    """
    from litellm.proxy.utils import _premium_user_check

    for _management_object_metadata in [key_metadata, team_metadata]:
        if _management_object_metadata and "guardrails" in _management_object_metadata:
            if len(_management_object_metadata["guardrails"]) > 0:
                _premium_user_check()

            data[metadata_variable_name]["guardrails"] = _management_object_metadata[
                "guardrails"
            ]


def move_guardrails_to_metadata(
    data: dict,
    _metadata_variable_name: str,
    user_api_key_dict: UserAPIKeyAuth,
):
    """
    Helper to add guardrails from request to metadata

    - If guardrails set on API Key metadata then sets guardrails on request metadata
    - If guardrails not set on API key, then checks request metadata
    """
    # Check key-level guardrails
    _add_guardrails_from_key_or_team_metadata(
        key_metadata=user_api_key_dict.metadata,
        team_metadata=user_api_key_dict.team_metadata,
        data=data,
        metadata_variable_name=_metadata_variable_name,
    )

    # Check request-level guardrails
    if "guardrails" in data:
        data[_metadata_variable_name]["guardrails"] = data["guardrails"]
        del data["guardrails"]

    if "guardrail_config" in data:
        data[_metadata_variable_name]["guardrail_config"] = data["guardrail_config"]
        del data["guardrail_config"]


def add_provider_specific_headers_to_request(
    data: dict,
    headers: dict,
):
    anthropic_headers = {}
    # boolean to indicate if a header was added
    added_header = False
    for header in ANTHROPIC_API_HEADERS:
        if header in headers:
            header_value = headers[header]
            anthropic_headers[header] = header_value
            added_header = True

    if added_header is True:
        data["provider_specific_header"] = ProviderSpecificHeader(
            custom_llm_provider="anthropic",
            extra_headers=anthropic_headers,
        )

    return


def _add_otel_traceparent_to_data(data: dict, request: Request):
    from litellm.proxy.proxy_server import open_telemetry_logger

    if data is None:
        return
    if open_telemetry_logger is None:
        # if user is not use OTEL don't send extra_headers
        # relevant issue: https://github.com/BerriAI/litellm/issues/4448
        return

    if litellm.forward_traceparent_to_llm_provider is True:
        if request.headers:
            if "traceparent" in request.headers:
                # we want to forward this to the LLM Provider
                # Relevant issue: https://github.com/BerriAI/litellm/issues/4419
                # pass this in extra_headers
                if "extra_headers" not in data:
                    data["extra_headers"] = {}
                _exra_headers = data["extra_headers"]
                if "traceparent" not in _exra_headers:
                    _exra_headers["traceparent"] = request.headers["traceparent"]

# === NexusCore/openenv\Lib\site-packages\psutil\_psbsd.py ===
# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""FreeBSD, OpenBSD and NetBSD platforms implementation."""

import contextlib
import errno
import functools
import os
from collections import defaultdict
from collections import namedtuple
from xml.etree import ElementTree

from . import _common
from . import _psposix
from . import _psutil_bsd as cext
from . import _psutil_posix as cext_posix
from ._common import FREEBSD
from ._common import NETBSD
from ._common import OPENBSD
from ._common import AccessDenied
from ._common import NoSuchProcess
from ._common import ZombieProcess
from ._common import conn_tmap
from ._common import conn_to_ntuple
from ._common import debug
from ._common import memoize
from ._common import memoize_when_activated
from ._common import usage_percent
from ._compat import FileNotFoundError
from ._compat import PermissionError
from ._compat import ProcessLookupError
from ._compat import which


__extra__all__ = []


# =====================================================================
# --- globals
# =====================================================================


if FREEBSD:
    PROC_STATUSES = {
        cext.SIDL: _common.STATUS_IDLE,
        cext.SRUN: _common.STATUS_RUNNING,
        cext.SSLEEP: _common.STATUS_SLEEPING,
        cext.SSTOP: _common.STATUS_STOPPED,
        cext.SZOMB: _common.STATUS_ZOMBIE,
        cext.SWAIT: _common.STATUS_WAITING,
        cext.SLOCK: _common.STATUS_LOCKED,
    }
elif OPENBSD:
    PROC_STATUSES = {
        cext.SIDL: _common.STATUS_IDLE,
        cext.SSLEEP: _common.STATUS_SLEEPING,
        cext.SSTOP: _common.STATUS_STOPPED,
        # According to /usr/include/sys/proc.h SZOMB is unused.
        # test_zombie_process() shows that SDEAD is the right
        # equivalent. Also it appears there's no equivalent of
        # psutil.STATUS_DEAD. SDEAD really means STATUS_ZOMBIE.
        # cext.SZOMB: _common.STATUS_ZOMBIE,
        cext.SDEAD: _common.STATUS_ZOMBIE,
        cext.SZOMB: _common.STATUS_ZOMBIE,
        # From http://www.eecs.harvard.edu/~margo/cs161/videos/proc.h.txt
        # OpenBSD has SRUN and SONPROC: SRUN indicates that a process
        # is runnable but *not* yet running, i.e. is on a run queue.
        # SONPROC indicates that the process is actually executing on
        # a CPU, i.e. it is no longer on a run queue.
        # As such we'll map SRUN to STATUS_WAKING and SONPROC to
        # STATUS_RUNNING
        cext.SRUN: _common.STATUS_WAKING,
        cext.SONPROC: _common.STATUS_RUNNING,
    }
elif NETBSD:
    PROC_STATUSES = {
        cext.SIDL: _common.STATUS_IDLE,
        cext.SSLEEP: _common.STATUS_SLEEPING,
        cext.SSTOP: _common.STATUS_STOPPED,
        cext.SZOMB: _common.STATUS_ZOMBIE,
        cext.SRUN: _common.STATUS_WAKING,
        cext.SONPROC: _common.STATUS_RUNNING,
    }

TCP_STATUSES = {
    cext.TCPS_ESTABLISHED: _common.CONN_ESTABLISHED,
    cext.TCPS_SYN_SENT: _common.CONN_SYN_SENT,
    cext.TCPS_SYN_RECEIVED: _common.CONN_SYN_RECV,
    cext.TCPS_FIN_WAIT_1: _common.CONN_FIN_WAIT1,
    cext.TCPS_FIN_WAIT_2: _common.CONN_FIN_WAIT2,
    cext.TCPS_TIME_WAIT: _common.CONN_TIME_WAIT,
    cext.TCPS_CLOSED: _common.CONN_CLOSE,
    cext.TCPS_CLOSE_WAIT: _common.CONN_CLOSE_WAIT,
    cext.TCPS_LAST_ACK: _common.CONN_LAST_ACK,
    cext.TCPS_LISTEN: _common.CONN_LISTEN,
    cext.TCPS_CLOSING: _common.CONN_CLOSING,
    cext.PSUTIL_CONN_NONE: _common.CONN_NONE,
}

PAGESIZE = cext_posix.getpagesize()
AF_LINK = cext_posix.AF_LINK

HAS_PER_CPU_TIMES = hasattr(cext, "per_cpu_times")
HAS_PROC_NUM_THREADS = hasattr(cext, "proc_num_threads")
HAS_PROC_OPEN_FILES = hasattr(cext, 'proc_open_files')
HAS_PROC_NUM_FDS = hasattr(cext, 'proc_num_fds')

kinfo_proc_map = dict(
    ppid=0,
    status=1,
    real_uid=2,
    effective_uid=3,
    saved_uid=4,
    real_gid=5,
    effective_gid=6,
    saved_gid=7,
    ttynr=8,
    create_time=9,
    ctx_switches_vol=10,
    ctx_switches_unvol=11,
    read_io_count=12,
    write_io_count=13,
    user_time=14,
    sys_time=15,
    ch_user_time=16,
    ch_sys_time=17,
    rss=18,
    vms=19,
    memtext=20,
    memdata=21,
    memstack=22,
    cpunum=23,
    name=24,
)


# =====================================================================
# --- named tuples
# =====================================================================


# fmt: off
# psutil.virtual_memory()
svmem = namedtuple(
    'svmem', ['total', 'available', 'percent', 'used', 'free',
              'active', 'inactive', 'buffers', 'cached', 'shared', 'wired'])
# psutil.cpu_times()
scputimes = namedtuple(
    'scputimes', ['user', 'nice', 'system', 'idle', 'irq'])
# psutil.Process.memory_info()
pmem = namedtuple('pmem', ['rss', 'vms', 'text', 'data', 'stack'])
# psutil.Process.memory_full_info()
pfullmem = pmem
# psutil.Process.cpu_times()
pcputimes = namedtuple('pcputimes',
                       ['user', 'system', 'children_user', 'children_system'])
# psutil.Process.memory_maps(grouped=True)
pmmap_grouped = namedtuple(
    'pmmap_grouped', 'path rss, private, ref_count, shadow_count')
# psutil.Process.memory_maps(grouped=False)
pmmap_ext = namedtuple(
    'pmmap_ext', 'addr, perms path rss, private, ref_count, shadow_count')
# psutil.disk_io_counters()
if FREEBSD:
    sdiskio = namedtuple('sdiskio', ['read_count', 'write_count',
                                     'read_bytes', 'write_bytes',
                                     'read_time', 'write_time',
                                     'busy_time'])
else:
    sdiskio = namedtuple('sdiskio', ['read_count', 'write_count',
                                     'read_bytes', 'write_bytes'])
# fmt: on


# =====================================================================
# --- memory
# =====================================================================


def virtual_memory():
    mem = cext.virtual_mem()
    if NETBSD:
        total, free, active, inactive, wired, cached = mem
        # On NetBSD buffers and shared mem is determined via /proc.
        # The C ext set them to 0.
        with open('/proc/meminfo', 'rb') as f:
            for line in f:
                if line.startswith(b'Buffers:'):
                    buffers = int(line.split()[1]) * 1024
                elif line.startswith(b'MemShared:'):
                    shared = int(line.split()[1]) * 1024
        # Before avail was calculated as (inactive + cached + free),
        # same as zabbix, but it turned out it could exceed total (see
        # #2233), so zabbix seems to be wrong. Htop calculates it
        # differently, and the used value seem more realistic, so let's
        # match htop.
        # https://github.com/htop-dev/htop/blob/e7f447b/netbsd/NetBSDProcessList.c#L162  # noqa
        # https://github.com/zabbix/zabbix/blob/af5e0f8/src/libs/zbxsysinfo/netbsd/memory.c#L135  # noqa
        used = active + wired
        avail = total - used
    else:
        total, free, active, inactive, wired, cached, buffers, shared = mem
        # matches freebsd-memory CLI:
        # * https://people.freebsd.org/~rse/dist/freebsd-memory
        # * https://www.cyberciti.biz/files/scripts/freebsd-memory.pl.txt
        # matches zabbix:
        # * https://github.com/zabbix/zabbix/blob/af5e0f8/src/libs/zbxsysinfo/freebsd/memory.c#L143  # noqa
        avail = inactive + cached + free
        used = active + wired + cached

    percent = usage_percent((total - avail), total, round_=1)
    return svmem(
        total,
        avail,
        percent,
        used,
        free,
        active,
        inactive,
        buffers,
        cached,
        shared,
        wired,
    )


def swap_memory():
    """System swap memory as (total, used, free, sin, sout) namedtuple."""
    total, used, free, sin, sout = cext.swap_mem()
    percent = usage_percent(used, total, round_=1)
    return _common.sswap(total, used, free, percent, sin, sout)


# =====================================================================
# --- CPU
# =====================================================================


def cpu_times():
    """Return system per-CPU times as a namedtuple."""
    user, nice, system, idle, irq = cext.cpu_times()
    return scputimes(user, nice, system, idle, irq)


if HAS_PER_CPU_TIMES:

    def per_cpu_times():
        """Return system CPU times as a namedtuple."""
        ret = []
        for cpu_t in cext.per_cpu_times():
            user, nice, system, idle, irq = cpu_t
            item = scputimes(user, nice, system, idle, irq)
            ret.append(item)
        return ret

else:
    # XXX
    # Ok, this is very dirty.
    # On FreeBSD < 8 we cannot gather per-cpu information, see:
    # https://github.com/giampaolo/psutil/issues/226
    # If num cpus > 1, on first call we return single cpu times to avoid a
    # crash at psutil import time.
    # Next calls will fail with NotImplementedError
    def per_cpu_times():
        """Return system CPU times as a namedtuple."""
        if cpu_count_logical() == 1:
            return [cpu_times()]
        if per_cpu_times.__called__:
            msg = "supported only starting from FreeBSD 8"
            raise NotImplementedError(msg)
        per_cpu_times.__called__ = True
        return [cpu_times()]

    per_cpu_times.__called__ = False


def cpu_count_logical():
    """Return the number of logical CPUs in the system."""
    return cext.cpu_count_logical()


if OPENBSD or NETBSD:

    def cpu_count_cores():
        # OpenBSD and NetBSD do not implement this.
        return 1 if cpu_count_logical() == 1 else None

else:

    def cpu_count_cores():
        """Return the number of CPU cores in the system."""
        # From the C module we'll get an XML string similar to this:
        # http://manpages.ubuntu.com/manpages/precise/man4/smp.4freebsd.html
        # We may get None in case "sysctl kern.sched.topology_spec"
        # is not supported on this BSD version, in which case we'll mimic
        # os.cpu_count() and return None.
        ret = None
        s = cext.cpu_topology()
        if s is not None:
            # get rid of padding chars appended at the end of the string
            index = s.rfind("</groups>")
            if index != -1:
                s = s[: index + 9]
                root = ElementTree.fromstring(s)
                try:
                    ret = len(root.findall('group/children/group/cpu')) or None
                finally:
                    # needed otherwise it will memleak
                    root.clear()
        if not ret:
            # If logical CPUs == 1 it's obvious we' have only 1 core.
            if cpu_count_logical() == 1:
                return 1
        return ret


def cpu_stats():
    """Return various CPU stats as a named tuple."""
    if FREEBSD:
        # Note: the C ext is returning some metrics we are not exposing:
        # traps.
        ctxsw, intrs, soft_intrs, syscalls, traps = cext.cpu_stats()
    elif NETBSD:
        # XXX
        # Note about intrs: the C extension returns 0. intrs
        # can be determined via /proc/stat; it has the same value as
        # soft_intrs thought so the kernel is faking it (?).
        #
        # Note about syscalls: the C extension always sets it to 0 (?).
        #
        # Note: the C ext is returning some metrics we are not exposing:
        # traps, faults and forks.
        ctxsw, intrs, soft_intrs, syscalls, traps, faults, forks = (
            cext.cpu_stats()
        )
        with open('/proc/stat', 'rb') as f:
            for line in f:
                if line.startswith(b'intr'):
                    intrs = int(line.split()[1])
    elif OPENBSD:
        # Note: the C ext is returning some metrics we are not exposing:
        # traps, faults and forks.
        ctxsw, intrs, soft_intrs, syscalls, traps, faults, forks = (
            cext.cpu_stats()
        )
    return _common.scpustats(ctxsw, intrs, soft_intrs, syscalls)


if FREEBSD:

    def cpu_freq():
        """Return frequency metrics for CPUs. As of Dec 2018 only
        CPU 0 appears to be supported by FreeBSD and all other cores
        match the frequency of CPU 0.
        """
        ret = []
        num_cpus = cpu_count_logical()
        for cpu in range(num_cpus):
            try:
                current, available_freq = cext.cpu_freq(cpu)
            except NotImplementedError:
                continue
            if available_freq:
                try:
                    min_freq = int(available_freq.split(" ")[-1].split("/")[0])
                except (IndexError, ValueError):
                    min_freq = None
                try:
                    max_freq = int(available_freq.split(" ")[0].split("/")[0])
                except (IndexError, ValueError):
                    max_freq = None
            ret.append(_common.scpufreq(current, min_freq, max_freq))
        return ret

elif OPENBSD:

    def cpu_freq():
        curr = float(cext.cpu_freq())
        return [_common.scpufreq(curr, 0.0, 0.0)]


# =====================================================================
# --- disks
# =====================================================================


def disk_partitions(all=False):
    """Return mounted disk partitions as a list of namedtuples.
    'all' argument is ignored, see:
    https://github.com/giampaolo/psutil/issues/906.
    """
    retlist = []
    partitions = cext.disk_partitions()
    for partition in partitions:
        device, mountpoint, fstype, opts = partition
        maxfile = maxpath = None  # set later
        ntuple = _common.sdiskpart(
            device, mountpoint, fstype, opts, maxfile, maxpath
        )
        retlist.append(ntuple)
    return retlist


disk_usage = _psposix.disk_usage
disk_io_counters = cext.disk_io_counters


# =====================================================================
# --- network
# =====================================================================


net_io_counters = cext.net_io_counters
net_if_addrs = cext_posix.net_if_addrs


def net_if_stats():
    """Get NIC stats (isup, duplex, speed, mtu)."""
    names = net_io_counters().keys()
    ret = {}
    for name in names:
        try:
            mtu = cext_posix.net_if_mtu(name)
            flags = cext_posix.net_if_flags(name)
            duplex, speed = cext_posix.net_if_duplex_speed(name)
        except OSError as err:
            # https://github.com/giampaolo/psutil/issues/1279
            if err.errno != errno.ENODEV:
                raise
        else:
            if hasattr(_common, 'NicDuplex'):
                duplex = _common.NicDuplex(duplex)
            output_flags = ','.join(flags)
            isup = 'running' in flags
            ret[name] = _common.snicstats(
                isup, duplex, speed, mtu, output_flags
            )
    return ret


def net_connections(kind):
    """System-wide network connections."""
    if kind not in _common.conn_tmap:
        raise ValueError(
            "invalid %r kind argument; choose between %s"
            % (kind, ', '.join([repr(x) for x in conn_tmap]))
        )
    families, types = conn_tmap[kind]
    ret = set()

    if OPENBSD:
        rawlist = cext.net_connections(-1, families, types)
    elif NETBSD:
        rawlist = cext.net_connections(-1, kind)
    else:  # FreeBSD
        rawlist = cext.net_connections(families, types)

    for item in rawlist:
        fd, fam, type, laddr, raddr, status, pid = item
        nt = conn_to_ntuple(
            fd, fam, type, laddr, raddr, status, TCP_STATUSES, pid
        )
        ret.add(nt)
    return list(ret)


# =====================================================================
#  --- sensors
# =====================================================================


if FREEBSD:

    def sensors_battery():
        """Return battery info."""
        try:
            percent, minsleft, power_plugged = cext.sensors_battery()
        except NotImplementedError:
            # See: https://github.com/giampaolo/psutil/issues/1074
            return None
        power_plugged = power_plugged == 1
        if power_plugged:
            secsleft = _common.POWER_TIME_UNLIMITED
        elif minsleft == -1:
            secsleft = _common.POWER_TIME_UNKNOWN
        else:
            secsleft = minsleft * 60
        return _common.sbattery(percent, secsleft, power_plugged)

    def sensors_temperatures():
        """Return CPU cores temperatures if available, else an empty dict."""
        ret = defaultdict(list)
        num_cpus = cpu_count_logical()
        for cpu in range(num_cpus):
            try:
                current, high = cext.sensors_cpu_temperature(cpu)
                if high <= 0:
                    high = None
                name = "Core %s" % cpu
                ret["coretemp"].append(
                    _common.shwtemp(name, current, high, high)
                )
            except NotImplementedError:
                pass

        return ret


# =====================================================================
#  --- other system functions
# =====================================================================


def boot_time():
    """The system boot time expressed in seconds since the epoch."""
    return cext.boot_time()


def users():
    """Return currently connected users as a list of namedtuples."""
    retlist = []
    rawlist = cext.users()
    for item in rawlist:
        user, tty, hostname, tstamp, pid = item
        if pid == -1:
            assert OPENBSD
            pid = None
        if tty == '~':
            continue  # reboot or shutdown
        nt = _common.suser(user, tty or None, hostname, tstamp, pid)
        retlist.append(nt)
    return retlist


# =====================================================================
# --- processes
# =====================================================================


@memoize
def _pid_0_exists():
    try:
        Process(0).name()
    except NoSuchProcess:
        return False
    except AccessDenied:
        return True
    else:
        return True


def pids():
    """Returns a list of PIDs currently running on the system."""
    ret = cext.pids()
    if OPENBSD and (0 not in ret) and _pid_0_exists():
        # On OpenBSD the kernel does not return PID 0 (neither does
        # ps) but it's actually querable (Process(0) will succeed).
        ret.insert(0, 0)
    return ret


if OPENBSD or NETBSD:

    def pid_exists(pid):
        """Return True if pid exists."""
        exists = _psposix.pid_exists(pid)
        if not exists:
            # We do this because _psposix.pid_exists() lies in case of
            # zombie processes.
            return pid in pids()
        else:
            return True

else:
    pid_exists = _psposix.pid_exists


def is_zombie(pid):
    try:
        st = cext.proc_oneshot_info(pid)[kinfo_proc_map['status']]
        return PROC_STATUSES.get(st) == _common.STATUS_ZOMBIE
    except OSError:
        return False


def wrap_exceptions(fun):
    """Decorator which translates bare OSError exceptions into
    NoSuchProcess and AccessDenied.
    """

    @functools.wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except ProcessLookupError:
            if is_zombie(self.pid):
                raise ZombieProcess(self.pid, self._name, self._ppid)
            else:
                raise NoSuchProcess(self.pid, self._name)
        except PermissionError:
            raise AccessDenied(self.pid, self._name)
        except OSError:
            if self.pid == 0:
                if 0 in pids():
                    raise AccessDenied(self.pid, self._name)
                else:
                    raise
            raise

    return wrapper


@contextlib.contextmanager
def wrap_exceptions_procfs(inst):
    """Same as above, for routines relying on reading /proc fs."""
    try:
        yield
    except (ProcessLookupError, FileNotFoundError):
        # ENOENT (no such file or directory) gets raised on open().
        # ESRCH (no such process) can get raised on read() if
        # process is gone in meantime.
        if is_zombie(inst.pid):
            raise ZombieProcess(inst.pid, inst._name, inst._ppid)
        else:
            raise NoSuchProcess(inst.pid, inst._name)
    except PermissionError:
        raise AccessDenied(inst.pid, inst._name)


class Process:
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_name", "_ppid", "_cache"]

    def __init__(self, pid):
        self.pid = pid
        self._name = None
        self._ppid = None

    def _assert_alive(self):
        """Raise NSP if the process disappeared on us."""
        # For those C function who do not raise NSP, possibly returning
        # incorrect or incomplete result.
        cext.proc_name(self.pid)

    @wrap_exceptions
    @memoize_when_activated
    def oneshot(self):
        """Retrieves multiple process info in one shot as a raw tuple."""
        ret = cext.proc_oneshot_info(self.pid)
        assert len(ret) == len(kinfo_proc_map)
        return ret

    def oneshot_enter(self):
        self.oneshot.cache_activate(self)

    def oneshot_exit(self):
        self.oneshot.cache_deactivate(self)

    @wrap_exceptions
    def name(self):
        name = self.oneshot()[kinfo_proc_map['name']]
        return name if name is not None else cext.proc_name(self.pid)

    @wrap_exceptions
    def exe(self):
        if FREEBSD:
            if self.pid == 0:
                return ''  # else NSP
            return cext.proc_exe(self.pid)
        elif NETBSD:
            if self.pid == 0:
                # /proc/0 dir exists but /proc/0/exe doesn't
                return ""
            with wrap_exceptions_procfs(self):
                return os.readlink("/proc/%s/exe" % self.pid)
        else:
            # OpenBSD: exe cannot be determined; references:
            # https://chromium.googlesource.com/chromium/src/base/+/
            #     master/base_paths_posix.cc
            # We try our best guess by using which against the first
            # cmdline arg (may return None).
            cmdline = self.cmdline()
            if cmdline:
                return which(cmdline[0]) or ""
            else:
                return ""

    @wrap_exceptions
    def cmdline(self):
        if OPENBSD and self.pid == 0:
            return []  # ...else it crashes
        elif NETBSD:
            # XXX - most of the times the underlying sysctl() call on
            # NetBSD and OpenBSD returns a truncated string. Also
            # /proc/pid/cmdline behaves the same so it looks like this
            # is a kernel bug.
            try:
                return cext.proc_cmdline(self.pid)
            except OSError as err:
                if err.errno == errno.EINVAL:
                    if is_zombie(self.pid):
                        raise ZombieProcess(self.pid, self._name, self._ppid)
                    elif not pid_exists(self.pid):
                        raise NoSuchProcess(self.pid, self._name, self._ppid)
                    else:
                        # XXX: this happens with unicode tests. It means the C
                        # routine is unable to decode invalid unicode chars.
                        debug("ignoring %r and returning an empty list" % err)
                        return []
                else:
                    raise
        else:
            return cext.proc_cmdline(self.pid)

    @wrap_exceptions
    def environ(self):
        return cext.proc_environ(self.pid)

    @wrap_exceptions
    def terminal(self):
        tty_nr = self.oneshot()[kinfo_proc_map['ttynr']]
        tmap = _psposix.get_terminal_map()
        try:
            return tmap[tty_nr]
        except KeyError:
            return None

    @wrap_exceptions
    def ppid(self):
        self._ppid = self.oneshot()[kinfo_proc_map['ppid']]
        return self._ppid

    @wrap_exceptions
    def uids(self):
        rawtuple = self.oneshot()
        return _common.puids(
            rawtuple[kinfo_proc_map['real_uid']],
            rawtuple[kinfo_proc_map['effective_uid']],
            rawtuple[kinfo_proc_map['saved_uid']],
        )

    @wrap_exceptions
    def gids(self):
        rawtuple = self.oneshot()
        return _common.pgids(
            rawtuple[kinfo_proc_map['real_gid']],
            rawtuple[kinfo_proc_map['effective_gid']],
            rawtuple[kinfo_proc_map['saved_gid']],
        )

    @wrap_exceptions
    def cpu_times(self):
        rawtuple = self.oneshot()
        return _common.pcputimes(
            rawtuple[kinfo_proc_map['user_time']],
            rawtuple[kinfo_proc_map['sys_time']],
            rawtuple[kinfo_proc_map['ch_user_time']],
            rawtuple[kinfo_proc_map['ch_sys_time']],
        )

    if FREEBSD:

        @wrap_exceptions
        def cpu_num(self):
            return self.oneshot()[kinfo_proc_map['cpunum']]

    @wrap_exceptions
    def memory_info(self):
        rawtuple = self.oneshot()
        return pmem(
            rawtuple[kinfo_proc_map['rss']],
            rawtuple[kinfo_proc_map['vms']],
            rawtuple[kinfo_proc_map['memtext']],
            rawtuple[kinfo_proc_map['memdata']],
            rawtuple[kinfo_proc_map['memstack']],
        )

    memory_full_info = memory_info

    @wrap_exceptions
    def create_time(self):
        return self.oneshot()[kinfo_proc_map['create_time']]

    @wrap_exceptions
    def num_threads(self):
        if HAS_PROC_NUM_THREADS:
            # FreeBSD
            return cext.proc_num_threads(self.pid)
        else:
            return len(self.threads())

    @wrap_exceptions
    def num_ctx_switches(self):
        rawtuple = self.oneshot()
        return _common.pctxsw(
            rawtuple[kinfo_proc_map['ctx_switches_vol']],
            rawtuple[kinfo_proc_map['ctx_switches_unvol']],
        )

    @wrap_exceptions
    def threads(self):
        # Note: on OpenSBD this (/dev/mem) requires root access.
        rawlist = cext.proc_threads(self.pid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = _common.pthread(thread_id, utime, stime)
            retlist.append(ntuple)
        if OPENBSD:
            self._assert_alive()
        return retlist

    @wrap_exceptions
    def connections(self, kind='inet'):
        if kind not in conn_tmap:
            raise ValueError(
                "invalid %r kind argument; choose between %s"
                % (kind, ', '.join([repr(x) for x in conn_tmap]))
            )
        families, types = conn_tmap[kind]
        ret = []

        if NETBSD:
            rawlist = cext.net_connections(self.pid, kind)
        elif OPENBSD:
            rawlist = cext.net_connections(self.pid, families, types)
        else:
            rawlist = cext.proc_connections(self.pid, families, types)

        for item in rawlist:
            fd, fam, type, laddr, raddr, status = item[:6]
            if FREEBSD:
                if (fam not in families) or (type not in types):
                    continue
            nt = conn_to_ntuple(
                fd, fam, type, laddr, raddr, status, TCP_STATUSES
            )
            ret.append(nt)

        self._assert_alive()
        return ret

    @wrap_exceptions
    def wait(self, timeout=None):
        return _psposix.wait_pid(self.pid, timeout, self._name)

    @wrap_exceptions
    def nice_get(self):
        return cext_posix.getpriority(self.pid)

    @wrap_exceptions
    def nice_set(self, value):
        return cext_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def status(self):
        code = self.oneshot()[kinfo_proc_map['status']]
        # XXX is '?' legit? (we're not supposed to return it anyway)
        return PROC_STATUSES.get(code, '?')

    @wrap_exceptions
    def io_counters(self):
        rawtuple = self.oneshot()
        return _common.pio(
            rawtuple[kinfo_proc_map['read_io_count']],
            rawtuple[kinfo_proc_map['write_io_count']],
            -1,
            -1,
        )

    @wrap_exceptions
    def cwd(self):
        """Return process current working directory."""
        # sometimes we get an empty string, in which case we turn
        # it into None
        if OPENBSD and self.pid == 0:
            return ""  # ...else it would raise EINVAL
        elif NETBSD or HAS_PROC_OPEN_FILES:
            # FreeBSD < 8 does not support functions based on
            # kinfo_getfile() and kinfo_getvmmap()
            return cext.proc_cwd(self.pid)
        else:
            raise NotImplementedError(
                "supported only starting from FreeBSD 8" if FREEBSD else ""
            )

    nt_mmap_grouped = namedtuple(
        'mmap', 'path rss, private, ref_count, shadow_count'
    )
    nt_mmap_ext = namedtuple(
        'mmap', 'addr, perms path rss, private, ref_count, shadow_count'
    )

    def _not_implemented(self):
        raise NotImplementedError

    # FreeBSD < 8 does not support functions based on kinfo_getfile()
    # and kinfo_getvmmap()
    if HAS_PROC_OPEN_FILES:

        @wrap_exceptions
        def open_files(self):
            """Return files opened by process as a list of namedtuples."""
            rawlist = cext.proc_open_files(self.pid)
            return [_common.popenfile(path, fd) for path, fd in rawlist]

    else:
        open_files = _not_implemented

    # FreeBSD < 8 does not support functions based on kinfo_getfile()
    # and kinfo_getvmmap()
    if HAS_PROC_NUM_FDS:

        @wrap_exceptions
        def num_fds(self):
            """Return the number of file descriptors opened by this process."""
            ret = cext.proc_num_fds(self.pid)
            if NETBSD:
                self._assert_alive()
            return ret

    else:
        num_fds = _not_implemented

    # --- FreeBSD only APIs

    if FREEBSD:

        @wrap_exceptions
        def cpu_affinity_get(self):
            return cext.proc_cpu_affinity_get(self.pid)

        @wrap_exceptions
        def cpu_affinity_set(self, cpus):
            # Pre-emptively check if CPUs are valid because the C
            # function has a weird behavior in case of invalid CPUs,
            # see: https://github.com/giampaolo/psutil/issues/586
            allcpus = tuple(range(len(per_cpu_times())))
            for cpu in cpus:
                if cpu not in allcpus:
                    raise ValueError(
                        "invalid CPU #%i (choose between %s)" % (cpu, allcpus)
                    )
            try:
                cext.proc_cpu_affinity_set(self.pid, cpus)
            except OSError as err:
                # 'man cpuset_setaffinity' about EDEADLK:
                # <<the call would leave a thread without a valid CPU to run
                # on because the set does not overlap with the thread's
                # anonymous mask>>
                if err.errno in (errno.EINVAL, errno.EDEADLK):
                    for cpu in cpus:
                        if cpu not in allcpus:
                            raise ValueError(
                                "invalid CPU #%i (choose between %s)"
                                % (cpu, allcpus)
                            )
                raise

        @wrap_exceptions
        def memory_maps(self):
            return cext.proc_memory_maps(self.pid)

        @wrap_exceptions
        def rlimit(self, resource, limits=None):
            if limits is None:
                return cext.proc_getrlimit(self.pid, resource)
            else:
                if len(limits) != 2:
                    raise ValueError(
                        "second argument must be a (soft, hard) tuple, got %s"
                        % repr(limits)
                    )
                soft, hard = limits
                return cext.proc_setrlimit(self.pid, resource, soft, hard)