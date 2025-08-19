
# === NexusCore/tools\exports\export_20250803_114325\combined_185.py ===

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\_inference_endpoints.py ===
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional, Union

from huggingface_hub.errors import InferenceEndpointError, InferenceEndpointTimeoutError

from .utils import get_session, logging, parse_datetime


if TYPE_CHECKING:
    from .hf_api import HfApi
    from .inference._client import InferenceClient
    from .inference._generated._async_client import AsyncInferenceClient

logger = logging.get_logger(__name__)


class InferenceEndpointStatus(str, Enum):
    PENDING = "pending"
    INITIALIZING = "initializing"
    UPDATING = "updating"
    UPDATE_FAILED = "updateFailed"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    SCALED_TO_ZERO = "scaledToZero"


class InferenceEndpointType(str, Enum):
    PUBlIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"


@dataclass
class InferenceEndpoint:
    """
    Contains information about a deployed Inference Endpoint.

    Args:
        name (`str`):
            The unique name of the Inference Endpoint.
        namespace (`str`):
            The namespace where the Inference Endpoint is located.
        repository (`str`):
            The name of the model repository deployed on this Inference Endpoint.
        status ([`InferenceEndpointStatus`]):
            The current status of the Inference Endpoint.
        url (`str`, *optional*):
            The URL of the Inference Endpoint, if available. Only a deployed Inference Endpoint will have a URL.
        framework (`str`):
            The machine learning framework used for the model.
        revision (`str`):
            The specific model revision deployed on the Inference Endpoint.
        task (`str`):
            The task associated with the deployed model.
        created_at (`datetime.datetime`):
            The timestamp when the Inference Endpoint was created.
        updated_at (`datetime.datetime`):
            The timestamp of the last update of the Inference Endpoint.
        type ([`InferenceEndpointType`]):
            The type of the Inference Endpoint (public, protected, private).
        raw (`Dict`):
            The raw dictionary data returned from the API.
        token (`str` or `bool`, *optional*):
            Authentication token for the Inference Endpoint, if set when requesting the API. Will default to the
            locally saved token if not provided. Pass `token=False` if you don't want to send your token to the server.

    Example:
        ```python
        >>> from huggingface_hub import get_inference_endpoint
        >>> endpoint = get_inference_endpoint("my-text-to-image")
        >>> endpoint
        InferenceEndpoint(name='my-text-to-image', ...)

        # Get status
        >>> endpoint.status
        'running'
        >>> endpoint.url
        'https://my-text-to-image.region.vendor.endpoints.huggingface.cloud'

        # Run inference
        >>> endpoint.client.text_to_image(...)

        # Pause endpoint to save $$$
        >>> endpoint.pause()

        # ...
        # Resume and wait for deployment
        >>> endpoint.resume()
        >>> endpoint.wait()
        >>> endpoint.client.text_to_image(...)
        ```
    """

    # Field in __repr__
    name: str = field(init=False)
    namespace: str
    repository: str = field(init=False)
    status: InferenceEndpointStatus = field(init=False)
    url: Optional[str] = field(init=False)

    # Other fields
    framework: str = field(repr=False, init=False)
    revision: str = field(repr=False, init=False)
    task: str = field(repr=False, init=False)
    created_at: datetime = field(repr=False, init=False)
    updated_at: datetime = field(repr=False, init=False)
    type: InferenceEndpointType = field(repr=False, init=False)

    # Raw dict from the API
    raw: Dict = field(repr=False)

    # Internal fields
    _token: Union[str, bool, None] = field(repr=False, compare=False)
    _api: "HfApi" = field(repr=False, compare=False)

    @classmethod
    def from_raw(
        cls, raw: Dict, namespace: str, token: Union[str, bool, None] = None, api: Optional["HfApi"] = None
    ) -> "InferenceEndpoint":
        """Initialize object from raw dictionary."""
        if api is None:
            from .hf_api import HfApi

            api = HfApi()
        if token is None:
            token = api.token

        # All other fields are populated in __post_init__
        return cls(raw=raw, namespace=namespace, _token=token, _api=api)

    def __post_init__(self) -> None:
        """Populate fields from raw dictionary."""
        self._populate_from_raw()

    @property
    def client(self) -> "InferenceClient":
        """Returns a client to make predictions on this Inference Endpoint.

        Returns:
            [`InferenceClient`]: an inference client pointing to the deployed endpoint.

        Raises:
            [`InferenceEndpointError`]: If the Inference Endpoint is not yet deployed.
        """
        if self.url is None:
            raise InferenceEndpointError(
                "Cannot create a client for this Inference Endpoint as it is not yet deployed. "
                "Please wait for the Inference Endpoint to be deployed using `endpoint.wait()` and try again."
            )
        from .inference._client import InferenceClient

        return InferenceClient(
            model=self.url,
            token=self._token,  # type: ignore[arg-type] # boolean token shouldn't be possible. In practice it's ok.
        )

    @property
    def async_client(self) -> "AsyncInferenceClient":
        """Returns a client to make predictions on this Inference Endpoint.

        Returns:
            [`AsyncInferenceClient`]: an asyncio-compatible inference client pointing to the deployed endpoint.

        Raises:
            [`InferenceEndpointError`]: If the Inference Endpoint is not yet deployed.
        """
        if self.url is None:
            raise InferenceEndpointError(
                "Cannot create a client for this Inference Endpoint as it is not yet deployed. "
                "Please wait for the Inference Endpoint to be deployed using `endpoint.wait()` and try again."
            )
        from .inference._generated._async_client import AsyncInferenceClient

        return AsyncInferenceClient(
            model=self.url,
            token=self._token,  # type: ignore[arg-type] # boolean token shouldn't be possible. In practice it's ok.
        )

    def wait(self, timeout: Optional[int] = None, refresh_every: int = 5) -> "InferenceEndpoint":
        """Wait for the Inference Endpoint to be deployed.

        Information from the server will be fetched every 1s. If the Inference Endpoint is not deployed after `timeout`
        seconds, a [`InferenceEndpointTimeoutError`] will be raised. The [`InferenceEndpoint`] will be mutated in place with the latest
        data.

        Args:
            timeout (`int`, *optional*):
                The maximum time to wait for the Inference Endpoint to be deployed, in seconds. If `None`, will wait
                indefinitely.
            refresh_every (`int`, *optional*):
                The time to wait between each fetch of the Inference Endpoint status, in seconds. Defaults to 5s.

        Returns:
            [`InferenceEndpoint`]: the same Inference Endpoint, mutated in place with the latest data.

        Raises:
            [`InferenceEndpointError`]
                If the Inference Endpoint ended up in a failed state.
            [`InferenceEndpointTimeoutError`]
                If the Inference Endpoint is not deployed after `timeout` seconds.
        """
        if timeout is not None and timeout < 0:
            raise ValueError("`timeout` cannot be negative.")
        if refresh_every <= 0:
            raise ValueError("`refresh_every` must be positive.")

        start = time.time()
        while True:
            if self.status == InferenceEndpointStatus.FAILED:
                raise InferenceEndpointError(
                    f"Inference Endpoint {self.name} failed to deploy. Please check the logs for more information."
                )
            if self.status == InferenceEndpointStatus.UPDATE_FAILED:
                raise InferenceEndpointError(
                    f"Inference Endpoint {self.name} failed to update. Please check the logs for more information."
                )
            if self.status == InferenceEndpointStatus.RUNNING and self.url is not None:
                # Verify the endpoint is actually reachable
                response = get_session().get(self.url, headers=self._api._build_hf_headers(token=self._token))
                if response.status_code == 200:
                    logger.info("Inference Endpoint is ready to be used.")
                    return self

            if timeout is not None:
                if time.time() - start > timeout:
                    raise InferenceEndpointTimeoutError("Timeout while waiting for Inference Endpoint to be deployed.")
            logger.info(f"Inference Endpoint is not deployed yet ({self.status}). Waiting {refresh_every}s...")
            time.sleep(refresh_every)
            self.fetch()

    def fetch(self) -> "InferenceEndpoint":
        """Fetch latest information about the Inference Endpoint.

        Returns:
            [`InferenceEndpoint`]: the same Inference Endpoint, mutated in place with the latest data.
        """
        obj = self._api.get_inference_endpoint(name=self.name, namespace=self.namespace, token=self._token)  # type: ignore [arg-type]
        self.raw = obj.raw
        self._populate_from_raw()
        return self

    def update(
        self,
        *,
        # Compute update
        accelerator: Optional[str] = None,
        instance_size: Optional[str] = None,
        instance_type: Optional[str] = None,
        min_replica: Optional[int] = None,
        max_replica: Optional[int] = None,
        scale_to_zero_timeout: Optional[int] = None,
        # Model update
        repository: Optional[str] = None,
        framework: Optional[str] = None,
        revision: Optional[str] = None,
        task: Optional[str] = None,
        custom_image: Optional[Dict] = None,
        secrets: Optional[Dict[str, str]] = None,
    ) -> "InferenceEndpoint":
        """Update the Inference Endpoint.

        This method allows the update of either the compute configuration, the deployed model, or both. All arguments are
        optional but at least one must be provided.

        This is an alias for [`HfApi.update_inference_endpoint`]. The current object is mutated in place with the
        latest data from the server.

        Args:
            accelerator (`str`, *optional*):
                The hardware accelerator to be used for inference (e.g. `"cpu"`).
            instance_size (`str`, *optional*):
                The size or type of the instance to be used for hosting the model (e.g. `"x4"`).
            instance_type (`str`, *optional*):
                The cloud instance type where the Inference Endpoint will be deployed (e.g. `"intel-icl"`).
            min_replica (`int`, *optional*):
                The minimum number of replicas (instances) to keep running for the Inference Endpoint.
            max_replica (`int`, *optional*):
                The maximum number of replicas (instances) to scale to for the Inference Endpoint.
            scale_to_zero_timeout (`int`, *optional*):
                The duration in minutes before an inactive endpoint is scaled to zero.

            repository (`str`, *optional*):
                The name of the model repository associated with the Inference Endpoint (e.g. `"gpt2"`).
            framework (`str`, *optional*):
                The machine learning framework used for the model (e.g. `"custom"`).
            revision (`str`, *optional*):
                The specific model revision to deploy on the Inference Endpoint (e.g. `"6c0e6080953db56375760c0471a8c5f2929baf11"`).
            task (`str`, *optional*):
                The task on which to deploy the model (e.g. `"text-classification"`).
            custom_image (`Dict`, *optional*):
                A custom Docker image to use for the Inference Endpoint. This is useful if you want to deploy an
                Inference Endpoint running on the `text-generation-inference` (TGI) framework (see examples).
            secrets (`Dict[str, str]`, *optional*):
                Secret values to inject in the container environment.
        Returns:
            [`InferenceEndpoint`]: the same Inference Endpoint, mutated in place with the latest data.
        """
        # Make API call
        obj = self._api.update_inference_endpoint(
            name=self.name,
            namespace=self.namespace,
            accelerator=accelerator,
            instance_size=instance_size,
            instance_type=instance_type,
            min_replica=min_replica,
            max_replica=max_replica,
            scale_to_zero_timeout=scale_to_zero_timeout,
            repository=repository,
            framework=framework,
            revision=revision,
            task=task,
            custom_image=custom_image,
            secrets=secrets,
            token=self._token,  # type: ignore [arg-type]
        )

        # Mutate current object
        self.raw = obj.raw
        self._populate_from_raw()
        return self

    def pause(self) -> "InferenceEndpoint":
        """Pause the Inference Endpoint.

        A paused Inference Endpoint will not be charged. It can be resumed at any time using [`InferenceEndpoint.resume`].
        This is different than scaling the Inference Endpoint to zero with [`InferenceEndpoint.scale_to_zero`], which
        would be automatically restarted when a request is made to it.

        This is an alias for [`HfApi.pause_inference_endpoint`]. The current object is mutated in place with the
        latest data from the server.

        Returns:
            [`InferenceEndpoint`]: the same Inference Endpoint, mutated in place with the latest data.
        """
        obj = self._api.pause_inference_endpoint(name=self.name, namespace=self.namespace, token=self._token)  # type: ignore [arg-type]
        self.raw = obj.raw
        self._populate_from_raw()
        return self

    def resume(self, running_ok: bool = True) -> "InferenceEndpoint":
        """Resume the Inference Endpoint.

        This is an alias for [`HfApi.resume_inference_endpoint`]. The current object is mutated in place with the
        latest data from the server.

        Args:
            running_ok (`bool`, *optional*):
                If `True`, the method will not raise an error if the Inference Endpoint is already running. Defaults to
                `True`.

        Returns:
            [`InferenceEndpoint`]: the same Inference Endpoint, mutated in place with the latest data.
        """
        obj = self._api.resume_inference_endpoint(
            name=self.name, namespace=self.namespace, running_ok=running_ok, token=self._token
        )  # type: ignore [arg-type]
        self.raw = obj.raw
        self._populate_from_raw()
        return self

    def scale_to_zero(self) -> "InferenceEndpoint":
        """Scale Inference Endpoint to zero.

        An Inference Endpoint scaled to zero will not be charged. It will be resume on the next request to it, with a
        cold start delay. This is different than pausing the Inference Endpoint with [`InferenceEndpoint.pause`], which
        would require a manual resume with [`InferenceEndpoint.resume`].

        This is an alias for [`HfApi.scale_to_zero_inference_endpoint`]. The current object is mutated in place with the
        latest data from the server.

        Returns:
            [`InferenceEndpoint`]: the same Inference Endpoint, mutated in place with the latest data.
        """
        obj = self._api.scale_to_zero_inference_endpoint(name=self.name, namespace=self.namespace, token=self._token)  # type: ignore [arg-type]
        self.raw = obj.raw
        self._populate_from_raw()
        return self

    def delete(self) -> None:
        """Delete the Inference Endpoint.

        This operation is not reversible. If you don't want to be charged for an Inference Endpoint, it is preferable
        to pause it with [`InferenceEndpoint.pause`] or scale it to zero with [`InferenceEndpoint.scale_to_zero`].

        This is an alias for [`HfApi.delete_inference_endpoint`].
        """
        self._api.delete_inference_endpoint(name=self.name, namespace=self.namespace, token=self._token)  # type: ignore [arg-type]

    def _populate_from_raw(self) -> None:
        """Populate fields from raw dictionary.

        Called in __post_init__ + each time the Inference Endpoint is updated.
        """
        # Repr fields
        self.name = self.raw["name"]
        self.repository = self.raw["model"]["repository"]
        self.status = self.raw["status"]["state"]
        self.url = self.raw["status"].get("url")

        # Other fields
        self.framework = self.raw["model"]["framework"]
        self.revision = self.raw["model"]["revision"]
        self.task = self.raw["model"]["task"]
        self.created_at = parse_datetime(self.raw["status"]["createdAt"])
        self.updated_at = parse_datetime(self.raw["status"]["updatedAt"])
        self.type = self.raw["type"]

# === NexusCore/openenv\Lib\site-packages\openai\_streaming.py ===
# Note: initially copied from https://github.com/florimondmanca/httpx-sse/blob/master/src/httpx_sse/_decoders.py
from __future__ import annotations

import json
import inspect
from types import TracebackType
from typing import TYPE_CHECKING, Any, Generic, TypeVar, Iterator, AsyncIterator, cast
from typing_extensions import Self, Protocol, TypeGuard, override, get_origin, runtime_checkable

import httpx

from ._utils import is_mapping, extract_type_var_from_base
from ._exceptions import APIError

if TYPE_CHECKING:
    from ._client import OpenAI, AsyncOpenAI


_T = TypeVar("_T")


class Stream(Generic[_T]):
    """Provides the core interface to iterate over a synchronous stream response."""

    response: httpx.Response

    _decoder: SSEBytesDecoder

    def __init__(
        self,
        *,
        cast_to: type[_T],
        response: httpx.Response,
        client: OpenAI,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client
        self._decoder = client._make_sse_decoder()
        self._iterator = self.__stream__()

    def __next__(self) -> _T:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[_T]:
        for item in self._iterator:
            yield item

    def _iter_events(self) -> Iterator[ServerSentEvent]:
        yield from self._decoder.iter_bytes(self.response.iter_bytes())

    def __stream__(self) -> Iterator[_T]:
        cast_to = cast(Any, self._cast_to)
        response = self.response
        process_data = self._client._process_response_data
        iterator = self._iter_events()

        for sse in iterator:
            if sse.data.startswith("[DONE]"):
                break

            if sse.event is None or sse.event.startswith("response.") or sse.event.startswith("transcript."):
                data = sse.json()
                if is_mapping(data) and data.get("error"):
                    message = None
                    error = data.get("error")
                    if is_mapping(error):
                        message = error.get("message")
                    if not message or not isinstance(message, str):
                        message = "An error occurred during streaming"

                    raise APIError(
                        message=message,
                        request=self.response.request,
                        body=data["error"],
                    )

                yield process_data(data=data, cast_to=cast_to, response=response)

            else:
                data = sse.json()

                if sse.event == "error" and is_mapping(data) and data.get("error"):
                    message = None
                    error = data.get("error")
                    if is_mapping(error):
                        message = error.get("message")
                    if not message or not isinstance(message, str):
                        message = "An error occurred during streaming"

                    raise APIError(
                        message=message,
                        request=self.response.request,
                        body=data["error"],
                    )

                yield process_data(data={"data": data, "event": sse.event}, cast_to=cast_to, response=response)

        # Ensure the entire stream is consumed
        for _sse in iterator:
            ...

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        self.response.close()


class AsyncStream(Generic[_T]):
    """Provides the core interface to iterate over an asynchronous stream response."""

    response: httpx.Response

    _decoder: SSEDecoder | SSEBytesDecoder

    def __init__(
        self,
        *,
        cast_to: type[_T],
        response: httpx.Response,
        client: AsyncOpenAI,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client
        self._decoder = client._make_sse_decoder()
        self._iterator = self.__stream__()

    async def __anext__(self) -> _T:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[_T]:
        async for item in self._iterator:
            yield item

    async def _iter_events(self) -> AsyncIterator[ServerSentEvent]:
        async for sse in self._decoder.aiter_bytes(self.response.aiter_bytes()):
            yield sse

    async def __stream__(self) -> AsyncIterator[_T]:
        cast_to = cast(Any, self._cast_to)
        response = self.response
        process_data = self._client._process_response_data
        iterator = self._iter_events()

        async for sse in iterator:
            if sse.data.startswith("[DONE]"):
                break

            if sse.event is None or sse.event.startswith("response.") or sse.event.startswith("transcript."):
                data = sse.json()
                if is_mapping(data) and data.get("error"):
                    message = None
                    error = data.get("error")
                    if is_mapping(error):
                        message = error.get("message")
                    if not message or not isinstance(message, str):
                        message = "An error occurred during streaming"

                    raise APIError(
                        message=message,
                        request=self.response.request,
                        body=data["error"],
                    )

                yield process_data(data=data, cast_to=cast_to, response=response)

            else:
                data = sse.json()

                if sse.event == "error" and is_mapping(data) and data.get("error"):
                    message = None
                    error = data.get("error")
                    if is_mapping(error):
                        message = error.get("message")
                    if not message or not isinstance(message, str):
                        message = "An error occurred during streaming"

                    raise APIError(
                        message=message,
                        request=self.response.request,
                        body=data["error"],
                    )

                yield process_data(data={"data": data, "event": sse.event}, cast_to=cast_to, response=response)

        # Ensure the entire stream is consumed
        async for _sse in iterator:
            ...

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        await self.response.aclose()


class ServerSentEvent:
    def __init__(
        self,
        *,
        event: str | None = None,
        data: str | None = None,
        id: str | None = None,
        retry: int | None = None,
    ) -> None:
        if data is None:
            data = ""

        self._id = id
        self._data = data
        self._event = event or None
        self._retry = retry

    @property
    def event(self) -> str | None:
        return self._event

    @property
    def id(self) -> str | None:
        return self._id

    @property
    def retry(self) -> int | None:
        return self._retry

    @property
    def data(self) -> str:
        return self._data

    def json(self) -> Any:
        return json.loads(self.data)

    @override
    def __repr__(self) -> str:
        return f"ServerSentEvent(event={self.event}, data={self.data}, id={self.id}, retry={self.retry})"


class SSEDecoder:
    _data: list[str]
    _event: str | None
    _retry: int | None
    _last_event_id: str | None

    def __init__(self) -> None:
        self._event = None
        self._data = []
        self._last_event_id = None
        self._retry = None

    def iter_bytes(self, iterator: Iterator[bytes]) -> Iterator[ServerSentEvent]:
        """Given an iterator that yields raw binary data, iterate over it & yield every event encountered"""
        for chunk in self._iter_chunks(iterator):
            # Split before decoding so splitlines() only uses \r and \n
            for raw_line in chunk.splitlines():
                line = raw_line.decode("utf-8")
                sse = self.decode(line)
                if sse:
                    yield sse

    def _iter_chunks(self, iterator: Iterator[bytes]) -> Iterator[bytes]:
        """Given an iterator that yields raw binary data, iterate over it and yield individual SSE chunks"""
        data = b""
        for chunk in iterator:
            for line in chunk.splitlines(keepends=True):
                data += line
                if data.endswith((b"\r\r", b"\n\n", b"\r\n\r\n")):
                    yield data
                    data = b""
        if data:
            yield data

    async def aiter_bytes(self, iterator: AsyncIterator[bytes]) -> AsyncIterator[ServerSentEvent]:
        """Given an iterator that yields raw binary data, iterate over it & yield every event encountered"""
        async for chunk in self._aiter_chunks(iterator):
            # Split before decoding so splitlines() only uses \r and \n
            for raw_line in chunk.splitlines():
                line = raw_line.decode("utf-8")
                sse = self.decode(line)
                if sse:
                    yield sse

    async def _aiter_chunks(self, iterator: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
        """Given an iterator that yields raw binary data, iterate over it and yield individual SSE chunks"""
        data = b""
        async for chunk in iterator:
            for line in chunk.splitlines(keepends=True):
                data += line
                if data.endswith((b"\r\r", b"\n\n", b"\r\n\r\n")):
                    yield data
                    data = b""
        if data:
            yield data

    def decode(self, line: str) -> ServerSentEvent | None:
        # See: https://html.spec.whatwg.org/multipage/server-sent-events.html#event-stream-interpretation  # noqa: E501

        if not line:
            if not self._event and not self._data and not self._last_event_id and self._retry is None:
                return None

            sse = ServerSentEvent(
                event=self._event,
                data="\n".join(self._data),
                id=self._last_event_id,
                retry=self._retry,
            )

            # NOTE: as per the SSE spec, do not reset last_event_id.
            self._event = None
            self._data = []
            self._retry = None

            return sse

        if line.startswith(":"):
            return None

        fieldname, _, value = line.partition(":")

        if value.startswith(" "):
            value = value[1:]

        if fieldname == "event":
            self._event = value
        elif fieldname == "data":
            self._data.append(value)
        elif fieldname == "id":
            if "\0" in value:
                pass
            else:
                self._last_event_id = value
        elif fieldname == "retry":
            try:
                self._retry = int(value)
            except (TypeError, ValueError):
                pass
        else:
            pass  # Field is ignored.

        return None


@runtime_checkable
class SSEBytesDecoder(Protocol):
    def iter_bytes(self, iterator: Iterator[bytes]) -> Iterator[ServerSentEvent]:
        """Given an iterator that yields raw binary data, iterate over it & yield every event encountered"""
        ...

    def aiter_bytes(self, iterator: AsyncIterator[bytes]) -> AsyncIterator[ServerSentEvent]:
        """Given an async iterator that yields raw binary data, iterate over it & yield every event encountered"""
        ...


def is_stream_class_type(typ: type) -> TypeGuard[type[Stream[object]] | type[AsyncStream[object]]]:
    """TypeGuard for determining whether or not the given type is a subclass of `Stream` / `AsyncStream`"""
    origin = get_origin(typ) or typ
    return inspect.isclass(origin) and issubclass(origin, (Stream, AsyncStream))


def extract_stream_chunk_type(
    stream_cls: type,
    *,
    failure_message: str | None = None,
) -> type:
    """Given a type like `Stream[T]`, returns the generic type variable `T`.

    This also handles the case where a concrete subclass is given, e.g.
    ```py
    class MyStream(Stream[bytes]):
        ...

    extract_stream_chunk_type(MyStream) -> bytes
    ```
    """
    from ._base_client import Stream, AsyncStream

    return extract_type_var_from_base(
        stream_cls,
        index=0,
        generic_bases=cast("tuple[type, ...]", (Stream, AsyncStream)),
        failure_message=failure_message,
    )

# === NexusCore/openenv\Lib\site-packages\tornado\httpserver.py ===
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

"""A non-blocking, single-threaded HTTP server.

Typical applications have little direct interaction with the `HTTPServer`
class except to start a server at the beginning of the process
(and even that is often done indirectly via `tornado.web.Application.listen`).

.. versionchanged:: 4.0

   The ``HTTPRequest`` class that used to live in this module has been moved
   to `tornado.httputil.HTTPServerRequest`.  The old name remains as an alias.
"""

import socket
import ssl

from tornado.escape import native_str
from tornado.http1connection import HTTP1ServerConnection, HTTP1ConnectionParameters
from tornado import httputil
from tornado import iostream
from tornado import netutil
from tornado.tcpserver import TCPServer
from tornado.util import Configurable

import typing
from typing import Union, Any, Dict, Callable, List, Type, Tuple, Optional, Awaitable

if typing.TYPE_CHECKING:
    from typing import Set  # noqa: F401


class HTTPServer(TCPServer, Configurable, httputil.HTTPServerConnectionDelegate):
    r"""A non-blocking, single-threaded HTTP server.

    A server is defined by a subclass of `.HTTPServerConnectionDelegate`,
    or, for backwards compatibility, a callback that takes an
    `.HTTPServerRequest` as an argument. The delegate is usually a
    `tornado.web.Application`.

    `HTTPServer` supports keep-alive connections by default
    (automatically for HTTP/1.1, or for HTTP/1.0 when the client
    requests ``Connection: keep-alive``).

    If ``xheaders`` is ``True``, we support the
    ``X-Real-Ip``/``X-Forwarded-For`` and
    ``X-Scheme``/``X-Forwarded-Proto`` headers, which override the
    remote IP and URI scheme/protocol for all requests.  These headers
    are useful when running Tornado behind a reverse proxy or load
    balancer.  The ``protocol`` argument can also be set to ``https``
    if Tornado is run behind an SSL-decoding proxy that does not set one of
    the supported ``xheaders``.

    By default, when parsing the ``X-Forwarded-For`` header, Tornado will
    select the last (i.e., the closest) address on the list of hosts as the
    remote host IP address.  To select the next server in the chain, a list of
    trusted downstream hosts may be passed as the ``trusted_downstream``
    argument.  These hosts will be skipped when parsing the ``X-Forwarded-For``
    header.

    To make this server serve SSL traffic, send the ``ssl_options`` keyword
    argument with an `ssl.SSLContext` object. For compatibility with older
    versions of Python ``ssl_options`` may also be a dictionary of keyword
    arguments for the `ssl.SSLContext.wrap_socket` method.::

       ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
       ssl_ctx.load_cert_chain(os.path.join(data_dir, "mydomain.crt"),
                               os.path.join(data_dir, "mydomain.key"))
       HTTPServer(application, ssl_options=ssl_ctx)

    `HTTPServer` initialization follows one of three patterns (the
    initialization methods are defined on `tornado.tcpserver.TCPServer`):

    1. `~tornado.tcpserver.TCPServer.listen`: single-process::

            async def main():
                server = HTTPServer()
                server.listen(8888)
                await asyncio.Event().wait()

            asyncio.run(main())

       In many cases, `tornado.web.Application.listen` can be used to avoid
       the need to explicitly create the `HTTPServer`.

       While this example does not create multiple processes on its own, when
       the ``reuse_port=True`` argument is passed to ``listen()`` you can run
       the program multiple times to create a multi-process service.

    2. `~tornado.tcpserver.TCPServer.add_sockets`: multi-process::

            sockets = bind_sockets(8888)
            tornado.process.fork_processes(0)
            async def post_fork_main():
                server = HTTPServer()
                server.add_sockets(sockets)
                await asyncio.Event().wait()
            asyncio.run(post_fork_main())

       The ``add_sockets`` interface is more complicated, but it can be used with
       `tornado.process.fork_processes` to run a multi-process service with all
       worker processes forked from a single parent.  ``add_sockets`` can also be
       used in single-process servers if you want to create your listening
       sockets in some way other than `~tornado.netutil.bind_sockets`.

       Note that when using this pattern, nothing that touches the event loop
       can be run before ``fork_processes``.

    3. `~tornado.tcpserver.TCPServer.bind`/`~tornado.tcpserver.TCPServer.start`:
       simple **deprecated** multi-process::

            server = HTTPServer()
            server.bind(8888)
            server.start(0)  # Forks multiple sub-processes
            IOLoop.current().start()

       This pattern is deprecated because it requires interfaces in the
       `asyncio` module that have been deprecated since Python 3.10. Support for
       creating multiple processes in the ``start`` method will be removed in a
       future version of Tornado.

    .. versionchanged:: 4.0
       Added ``decompress_request``, ``chunk_size``, ``max_header_size``,
       ``idle_connection_timeout``, ``body_timeout``, ``max_body_size``
       arguments.  Added support for `.HTTPServerConnectionDelegate`
       instances as ``request_callback``.

    .. versionchanged:: 4.1
       `.HTTPServerConnectionDelegate.start_request` is now called with
       two arguments ``(server_conn, request_conn)`` (in accordance with the
       documentation) instead of one ``(request_conn)``.

    .. versionchanged:: 4.2
       `HTTPServer` is now a subclass of `tornado.util.Configurable`.

    .. versionchanged:: 4.5
       Added the ``trusted_downstream`` argument.

    .. versionchanged:: 5.0
       The ``io_loop`` argument has been removed.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Ignore args to __init__; real initialization belongs in
        # initialize since we're Configurable. (there's something
        # weird in initialization order between this class,
        # Configurable, and TCPServer so we can't leave __init__ out
        # completely)
        pass

    def initialize(
        self,
        request_callback: Union[
            httputil.HTTPServerConnectionDelegate,
            Callable[[httputil.HTTPServerRequest], None],
        ],
        no_keep_alive: bool = False,
        xheaders: bool = False,
        ssl_options: Optional[Union[Dict[str, Any], ssl.SSLContext]] = None,
        protocol: Optional[str] = None,
        decompress_request: bool = False,
        chunk_size: Optional[int] = None,
        max_header_size: Optional[int] = None,
        idle_connection_timeout: Optional[float] = None,
        body_timeout: Optional[float] = None,
        max_body_size: Optional[int] = None,
        max_buffer_size: Optional[int] = None,
        trusted_downstream: Optional[List[str]] = None,
    ) -> None:
        # This method's signature is not extracted with autodoc
        # because we want its arguments to appear on the class
        # constructor. When changing this signature, also update the
        # copy in httpserver.rst.
        self.request_callback = request_callback
        self.xheaders = xheaders
        self.protocol = protocol
        self.conn_params = HTTP1ConnectionParameters(
            decompress=decompress_request,
            chunk_size=chunk_size,
            max_header_size=max_header_size,
            header_timeout=idle_connection_timeout or 3600,
            max_body_size=max_body_size,
            body_timeout=body_timeout,
            no_keep_alive=no_keep_alive,
        )
        TCPServer.__init__(
            self,
            ssl_options=ssl_options,
            max_buffer_size=max_buffer_size,
            read_chunk_size=chunk_size,
        )
        self._connections = set()  # type: Set[HTTP1ServerConnection]
        self.trusted_downstream = trusted_downstream

    @classmethod
    def configurable_base(cls) -> Type[Configurable]:
        return HTTPServer

    @classmethod
    def configurable_default(cls) -> Type[Configurable]:
        return HTTPServer

    async def close_all_connections(self) -> None:
        """Close all open connections and asynchronously wait for them to finish.

        This method is used in combination with `~.TCPServer.stop` to
        support clean shutdowns (especially for unittests). Typical
        usage would call ``stop()`` first to stop accepting new
        connections, then ``await close_all_connections()`` to wait for
        existing connections to finish.

        This method does not currently close open websocket connections.

        Note that this method is a coroutine and must be called with ``await``.

        """
        while self._connections:
            # Peek at an arbitrary element of the set
            conn = next(iter(self._connections))
            await conn.close()

    def handle_stream(self, stream: iostream.IOStream, address: Tuple) -> None:
        context = _HTTPRequestContext(
            stream, address, self.protocol, self.trusted_downstream
        )
        conn = HTTP1ServerConnection(stream, self.conn_params, context)
        self._connections.add(conn)
        conn.start_serving(self)

    def start_request(
        self, server_conn: object, request_conn: httputil.HTTPConnection
    ) -> httputil.HTTPMessageDelegate:
        if isinstance(self.request_callback, httputil.HTTPServerConnectionDelegate):
            delegate = self.request_callback.start_request(server_conn, request_conn)
        else:
            delegate = _CallableAdapter(self.request_callback, request_conn)

        if self.xheaders:
            delegate = _ProxyAdapter(delegate, request_conn)

        return delegate

    def on_close(self, server_conn: object) -> None:
        self._connections.remove(typing.cast(HTTP1ServerConnection, server_conn))


class _CallableAdapter(httputil.HTTPMessageDelegate):
    def __init__(
        self,
        request_callback: Callable[[httputil.HTTPServerRequest], None],
        request_conn: httputil.HTTPConnection,
    ) -> None:
        self.connection = request_conn
        self.request_callback = request_callback
        self.request = None  # type: Optional[httputil.HTTPServerRequest]
        self.delegate = None
        self._chunks = []  # type: List[bytes]

    def headers_received(
        self,
        start_line: Union[httputil.RequestStartLine, httputil.ResponseStartLine],
        headers: httputil.HTTPHeaders,
    ) -> Optional[Awaitable[None]]:
        self.request = httputil.HTTPServerRequest(
            connection=self.connection,
            start_line=typing.cast(httputil.RequestStartLine, start_line),
            headers=headers,
        )
        return None

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        self._chunks.append(chunk)
        return None

    def finish(self) -> None:
        assert self.request is not None
        self.request.body = b"".join(self._chunks)
        self.request._parse_body()
        self.request_callback(self.request)

    def on_connection_close(self) -> None:
        del self._chunks


class _HTTPRequestContext:
    def __init__(
        self,
        stream: iostream.IOStream,
        address: Tuple,
        protocol: Optional[str],
        trusted_downstream: Optional[List[str]] = None,
    ) -> None:
        self.address = address
        # Save the socket's address family now so we know how to
        # interpret self.address even after the stream is closed
        # and its socket attribute replaced with None.
        if stream.socket is not None:
            self.address_family = stream.socket.family
        else:
            self.address_family = None
        # In HTTPServerRequest we want an IP, not a full socket address.
        if (
            self.address_family in (socket.AF_INET, socket.AF_INET6)
            and address is not None
        ):
            self.remote_ip = address[0]
        else:
            # Unix (or other) socket; fake the remote address.
            self.remote_ip = "0.0.0.0"
        if protocol:
            self.protocol = protocol
        elif isinstance(stream, iostream.SSLIOStream):
            self.protocol = "https"
        else:
            self.protocol = "http"
        self._orig_remote_ip = self.remote_ip
        self._orig_protocol = self.protocol
        self.trusted_downstream = set(trusted_downstream or [])

    def __str__(self) -> str:
        if self.address_family in (socket.AF_INET, socket.AF_INET6):
            return self.remote_ip
        elif isinstance(self.address, bytes):
            # Python 3 with the -bb option warns about str(bytes),
            # so convert it explicitly.
            # Unix socket addresses are str on mac but bytes on linux.
            return native_str(self.address)
        else:
            return str(self.address)

    def _apply_xheaders(self, headers: httputil.HTTPHeaders) -> None:
        """Rewrite the ``remote_ip`` and ``protocol`` fields."""
        # Squid uses X-Forwarded-For, others use X-Real-Ip
        ip = headers.get("X-Forwarded-For", self.remote_ip)
        # Skip trusted downstream hosts in X-Forwarded-For list
        for ip in (cand.strip() for cand in reversed(ip.split(","))):
            if ip not in self.trusted_downstream:
                break
        ip = headers.get("X-Real-Ip", ip)
        if netutil.is_valid_ip(ip):
            self.remote_ip = ip
        # AWS uses X-Forwarded-Proto
        proto_header = headers.get(
            "X-Scheme", headers.get("X-Forwarded-Proto", self.protocol)
        )
        if proto_header:
            # use only the last proto entry if there is more than one
            # TODO: support trusting multiple layers of proxied protocol
            proto_header = proto_header.split(",")[-1].strip()
        if proto_header in ("http", "https"):
            self.protocol = proto_header

    def _unapply_xheaders(self) -> None:
        """Undo changes from `_apply_xheaders`.

        Xheaders are per-request so they should not leak to the next
        request on the same connection.
        """
        self.remote_ip = self._orig_remote_ip
        self.protocol = self._orig_protocol


class _ProxyAdapter(httputil.HTTPMessageDelegate):
    def __init__(
        self,
        delegate: httputil.HTTPMessageDelegate,
        request_conn: httputil.HTTPConnection,
    ) -> None:
        self.connection = request_conn
        self.delegate = delegate

    def headers_received(
        self,
        start_line: Union[httputil.RequestStartLine, httputil.ResponseStartLine],
        headers: httputil.HTTPHeaders,
    ) -> Optional[Awaitable[None]]:
        # TODO: either make context an official part of the
        # HTTPConnection interface or figure out some other way to do this.
        self.connection.context._apply_xheaders(headers)  # type: ignore
        return self.delegate.headers_received(start_line, headers)

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        return self.delegate.data_received(chunk)

    def finish(self) -> None:
        self.delegate.finish()
        self._cleanup()

    def on_connection_close(self) -> None:
        self.delegate.on_connection_close()
        self._cleanup()

    def _cleanup(self) -> None:
        self.connection.context._unapply_xheaders()  # type: ignore


HTTPRequest = httputil.HTTPServerRequest

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\win32\psapi.py ===
#!/usr/bin/env python
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
Wrapper for psapi.dll in ctypes.
"""

__revision__ = "$Id$"

from winappdbg.win32.defines import *

# ==============================================================================
# This is used later on to calculate the list of exported symbols.
_all = None
_all = set(vars().keys())
# ==============================================================================

# --- PSAPI structures and constants -------------------------------------------

LIST_MODULES_DEFAULT = 0x00
LIST_MODULES_32BIT = 0x01
LIST_MODULES_64BIT = 0x02
LIST_MODULES_ALL = 0x03


# typedef struct _MODULEINFO {
#   LPVOID lpBaseOfDll;
#   DWORD  SizeOfImage;
#   LPVOID EntryPoint;
# } MODULEINFO, *LPMODULEINFO;
class MODULEINFO(Structure):
    _fields_ = [
        ("lpBaseOfDll", LPVOID),  # remote pointer
        ("SizeOfImage", DWORD),
        ("EntryPoint", LPVOID),  # remote pointer
    ]


LPMODULEINFO = POINTER(MODULEINFO)

# --- psapi.dll ----------------------------------------------------------------


# BOOL WINAPI EnumDeviceDrivers(
#   __out  LPVOID *lpImageBase,
#   __in   DWORD cb,
#   __out  LPDWORD lpcbNeeded
# );
def EnumDeviceDrivers():
    _EnumDeviceDrivers = windll.psapi.EnumDeviceDrivers
    _EnumDeviceDrivers.argtypes = [LPVOID, DWORD, LPDWORD]
    _EnumDeviceDrivers.restype = bool
    _EnumDeviceDrivers.errcheck = RaiseIfZero

    size = 0x1000
    lpcbNeeded = DWORD(size)
    unit = sizeof(LPVOID)
    while 1:
        lpImageBase = (LPVOID * (size // unit))()
        _EnumDeviceDrivers(byref(lpImageBase), lpcbNeeded, byref(lpcbNeeded))
        needed = lpcbNeeded.value
        if needed <= size:
            break
        size = needed
    return [lpImageBase[index] for index in compat.xrange(0, (needed // unit))]


# BOOL WINAPI EnumProcesses(
#   __out  DWORD *pProcessIds,
#   __in   DWORD cb,
#   __out  DWORD *pBytesReturned
# );
def EnumProcesses():
    _EnumProcesses = windll.psapi.EnumProcesses
    _EnumProcesses.argtypes = [LPVOID, DWORD, LPDWORD]
    _EnumProcesses.restype = bool
    _EnumProcesses.errcheck = RaiseIfZero

    size = 0x1000
    cbBytesReturned = DWORD()
    unit = sizeof(DWORD)
    while 1:
        ProcessIds = (DWORD * (size // unit))()
        cbBytesReturned.value = size
        _EnumProcesses(byref(ProcessIds), cbBytesReturned, byref(cbBytesReturned))
        returned = cbBytesReturned.value
        if returned < size:
            break
        size = size + 0x1000
    ProcessIdList = list()
    for ProcessId in ProcessIds:
        if ProcessId is None:
            break
        ProcessIdList.append(ProcessId)
    return ProcessIdList


# BOOL WINAPI EnumProcessModules(
#   __in   HANDLE hProcess,
#   __out  HMODULE *lphModule,
#   __in   DWORD cb,
#   __out  LPDWORD lpcbNeeded
# );
def EnumProcessModules(hProcess):
    _EnumProcessModules = windll.psapi.EnumProcessModules
    _EnumProcessModules.argtypes = [HANDLE, LPVOID, DWORD, LPDWORD]
    _EnumProcessModules.restype = bool
    _EnumProcessModules.errcheck = RaiseIfZero

    size = 0x1000
    lpcbNeeded = DWORD(size)
    unit = sizeof(HMODULE)
    while 1:
        lphModule = (HMODULE * (size // unit))()
        _EnumProcessModules(hProcess, byref(lphModule), lpcbNeeded, byref(lpcbNeeded))
        needed = lpcbNeeded.value
        if needed <= size:
            break
        size = needed
    return [lphModule[index] for index in compat.xrange(0, int(needed // unit))]


# BOOL WINAPI EnumProcessModulesEx(
#   __in   HANDLE hProcess,
#   __out  HMODULE *lphModule,
#   __in   DWORD cb,
#   __out  LPDWORD lpcbNeeded,
#   __in   DWORD dwFilterFlag
# );
def EnumProcessModulesEx(hProcess, dwFilterFlag=LIST_MODULES_DEFAULT):
    _EnumProcessModulesEx = windll.psapi.EnumProcessModulesEx
    _EnumProcessModulesEx.argtypes = [HANDLE, LPVOID, DWORD, LPDWORD, DWORD]
    _EnumProcessModulesEx.restype = bool
    _EnumProcessModulesEx.errcheck = RaiseIfZero

    size = 0x1000
    lpcbNeeded = DWORD(size)
    unit = sizeof(HMODULE)
    while 1:
        lphModule = (HMODULE * (size // unit))()
        _EnumProcessModulesEx(hProcess, byref(lphModule), lpcbNeeded, byref(lpcbNeeded), dwFilterFlag)
        needed = lpcbNeeded.value
        if needed <= size:
            break
        size = needed
    return [lphModule[index] for index in compat.xrange(0, (needed // unit))]


# DWORD WINAPI GetDeviceDriverBaseName(
#   __in   LPVOID ImageBase,
#   __out  LPTSTR lpBaseName,
#   __in   DWORD nSize
# );
def GetDeviceDriverBaseNameA(ImageBase):
    _GetDeviceDriverBaseNameA = windll.psapi.GetDeviceDriverBaseNameA
    _GetDeviceDriverBaseNameA.argtypes = [LPVOID, LPSTR, DWORD]
    _GetDeviceDriverBaseNameA.restype = DWORD

    nSize = MAX_PATH
    while 1:
        lpBaseName = ctypes.create_string_buffer("", nSize)
        nCopied = _GetDeviceDriverBaseNameA(ImageBase, lpBaseName, nSize)
        if nCopied == 0:
            raise ctypes.WinError()
        if nCopied < (nSize - 1):
            break
        nSize = nSize + MAX_PATH
    return lpBaseName.value


def GetDeviceDriverBaseNameW(ImageBase):
    _GetDeviceDriverBaseNameW = windll.psapi.GetDeviceDriverBaseNameW
    _GetDeviceDriverBaseNameW.argtypes = [LPVOID, LPWSTR, DWORD]
    _GetDeviceDriverBaseNameW.restype = DWORD

    nSize = MAX_PATH
    while 1:
        lpBaseName = ctypes.create_unicode_buffer("", nSize)
        nCopied = _GetDeviceDriverBaseNameW(ImageBase, lpBaseName, nSize)
        if nCopied == 0:
            raise ctypes.WinError()
        if nCopied < (nSize - 1):
            break
        nSize = nSize + MAX_PATH
    return lpBaseName.value


GetDeviceDriverBaseName = GuessStringType(GetDeviceDriverBaseNameA, GetDeviceDriverBaseNameW)


# DWORD WINAPI GetDeviceDriverFileName(
#   __in   LPVOID ImageBase,
#   __out  LPTSTR lpFilename,
#   __in   DWORD nSize
# );
def GetDeviceDriverFileNameA(ImageBase):
    _GetDeviceDriverFileNameA = windll.psapi.GetDeviceDriverFileNameA
    _GetDeviceDriverFileNameA.argtypes = [LPVOID, LPSTR, DWORD]
    _GetDeviceDriverFileNameA.restype = DWORD

    nSize = MAX_PATH
    while 1:
        lpFilename = ctypes.create_string_buffer("", nSize)
        nCopied = ctypes.windll.psapi.GetDeviceDriverFileNameA(ImageBase, lpFilename, nSize)
        if nCopied == 0:
            raise ctypes.WinError()
        if nCopied < (nSize - 1):
            break
        nSize = nSize + MAX_PATH
    return lpFilename.value


def GetDeviceDriverFileNameW(ImageBase):
    _GetDeviceDriverFileNameW = windll.psapi.GetDeviceDriverFileNameW
    _GetDeviceDriverFileNameW.argtypes = [LPVOID, LPWSTR, DWORD]
    _GetDeviceDriverFileNameW.restype = DWORD

    nSize = MAX_PATH
    while 1:
        lpFilename = ctypes.create_unicode_buffer("", nSize)
        nCopied = ctypes.windll.psapi.GetDeviceDriverFileNameW(ImageBase, lpFilename, nSize)
        if nCopied == 0:
            raise ctypes.WinError()
        if nCopied < (nSize - 1):
            break
        nSize = nSize + MAX_PATH
    return lpFilename.value


GetDeviceDriverFileName = GuessStringType(GetDeviceDriverFileNameA, GetDeviceDriverFileNameW)


# DWORD WINAPI GetMappedFileName(
#   __in   HANDLE hProcess,
#   __in   LPVOID lpv,
#   __out  LPTSTR lpFilename,
#   __in   DWORD nSize
# );
def GetMappedFileNameA(hProcess, lpv):
    _GetMappedFileNameA = ctypes.windll.psapi.GetMappedFileNameA
    _GetMappedFileNameA.argtypes = [HANDLE, LPVOID, LPSTR, DWORD]
    _GetMappedFileNameA.restype = DWORD

    nSize = MAX_PATH
    while 1:
        lpFilename = ctypes.create_string_buffer("", nSize)
        nCopied = _GetMappedFileNameA(hProcess, lpv, lpFilename, nSize)
        if nCopied == 0:
            raise ctypes.WinError()
        if nCopied < (nSize - 1):
            break
        nSize = nSize + MAX_PATH
    return lpFilename.value


def GetMappedFileNameW(hProcess, lpv):
    _GetMappedFileNameW = ctypes.windll.psapi.GetMappedFileNameW
    _GetMappedFileNameW.argtypes = [HANDLE, LPVOID, LPWSTR, DWORD]
    _GetMappedFileNameW.restype = DWORD

    nSize = MAX_PATH
    while 1:
        lpFilename = ctypes.create_unicode_buffer("", nSize)
        nCopied = _GetMappedFileNameW(hProcess, lpv, lpFilename, nSize)
        if nCopied == 0:
            raise ctypes.WinError()
        if nCopied < (nSize - 1):
            break
        nSize = nSize + MAX_PATH
    return lpFilename.value


GetMappedFileName = GuessStringType(GetMappedFileNameA, GetMappedFileNameW)


# DWORD WINAPI GetModuleFileNameEx(
#   __in      HANDLE hProcess,
#   __in_opt  HMODULE hModule,
#   __out     LPTSTR lpFilename,
#   __in      DWORD nSize
# );
def GetModuleFileNameExA(hProcess, hModule=None):
    _GetModuleFileNameExA = ctypes.windll.psapi.GetModuleFileNameExA
    _GetModuleFileNameExA.argtypes = [HANDLE, HMODULE, LPSTR, DWORD]
    _GetModuleFileNameExA.restype = DWORD

    nSize = MAX_PATH
    while 1:
        lpFilename = ctypes.create_string_buffer("", nSize)
        nCopied = _GetModuleFileNameExA(hProcess, hModule, lpFilename, nSize)
        if nCopied == 0:
            raise ctypes.WinError()
        if nCopied < (nSize - 1):
            break
        nSize = nSize + MAX_PATH
    return lpFilename.value


def GetModuleFileNameExW(hProcess, hModule=None):
    _GetModuleFileNameExW = ctypes.windll.psapi.GetModuleFileNameExW
    _GetModuleFileNameExW.argtypes = [HANDLE, HMODULE, LPWSTR, DWORD]
    _GetModuleFileNameExW.restype = DWORD

    nSize = MAX_PATH
    while 1:
        lpFilename = ctypes.create_unicode_buffer("", nSize)
        nCopied = _GetModuleFileNameExW(hProcess, hModule, lpFilename, nSize)
        if nCopied == 0:
            raise ctypes.WinError()
        if nCopied < (nSize - 1):
            break
        nSize = nSize + MAX_PATH
    return lpFilename.value


GetModuleFileNameEx = GuessStringType(GetModuleFileNameExA, GetModuleFileNameExW)


# BOOL WINAPI GetModuleInformation(
#   __in   HANDLE hProcess,
#   __in   HMODULE hModule,
#   __out  LPMODULEINFO lpmodinfo,
#   __in   DWORD cb
# );
def GetModuleInformation(hProcess, hModule, lpmodinfo=None):
    _GetModuleInformation = windll.psapi.GetModuleInformation
    _GetModuleInformation.argtypes = [HANDLE, HMODULE, LPMODULEINFO, DWORD]
    _GetModuleInformation.restype = bool
    _GetModuleInformation.errcheck = RaiseIfZero

    if lpmodinfo is None:
        lpmodinfo = MODULEINFO()
    _GetModuleInformation(hProcess, hModule, byref(lpmodinfo), sizeof(lpmodinfo))
    return lpmodinfo


# DWORD WINAPI GetProcessImageFileName(
#   __in   HANDLE hProcess,
#   __out  LPTSTR lpImageFileName,
#   __in   DWORD nSize
# );
def GetProcessImageFileNameA(hProcess):
    _GetProcessImageFileNameA = windll.psapi.GetProcessImageFileNameA
    _GetProcessImageFileNameA.argtypes = [HANDLE, LPSTR, DWORD]
    _GetProcessImageFileNameA.restype = DWORD

    nSize = MAX_PATH
    while 1:
        lpFilename = ctypes.create_string_buffer("", nSize)
        nCopied = _GetProcessImageFileNameA(hProcess, lpFilename, nSize)
        if nCopied == 0:
            raise ctypes.WinError()
        if nCopied < (nSize - 1):
            break
        nSize = nSize + MAX_PATH
    return lpFilename.value


def GetProcessImageFileNameW(hProcess):
    _GetProcessImageFileNameW = windll.psapi.GetProcessImageFileNameW
    _GetProcessImageFileNameW.argtypes = [HANDLE, LPWSTR, DWORD]
    _GetProcessImageFileNameW.restype = DWORD

    nSize = MAX_PATH
    while 1:
        lpFilename = ctypes.create_unicode_buffer("", nSize)
        nCopied = _GetProcessImageFileNameW(hProcess, lpFilename, nSize)
        if nCopied == 0:
            raise ctypes.WinError()
        if nCopied < (nSize - 1):
            break
        nSize = nSize + MAX_PATH
    return lpFilename.value


GetProcessImageFileName = GuessStringType(GetProcessImageFileNameA, GetProcessImageFileNameW)

# ==============================================================================
# This calculates the list of exported symbols.
_all = set(vars().keys()).difference(_all)
__all__ = [_x for _x in _all if not _x.startswith("_")]
__all__.sort()
# ==============================================================================

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pyproject_hooks\_impl.py ===
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from os.path import abspath
from os.path import join as pjoin
from subprocess import STDOUT, check_call, check_output
from typing import TYPE_CHECKING, Any, Iterator, Mapping, Optional, Sequence

from ._in_process import _in_proc_script_path

if TYPE_CHECKING:
    from typing import Protocol

    class SubprocessRunner(Protocol):
        """A protocol for the subprocess runner."""

        def __call__(
            self,
            cmd: Sequence[str],
            cwd: Optional[str] = None,
            extra_environ: Optional[Mapping[str, str]] = None,
        ) -> None:
            ...


def write_json(obj: Mapping[str, Any], path: str, **kwargs) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, **kwargs)


def read_json(path: str) -> Mapping[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class BackendUnavailable(Exception):
    """Will be raised if the backend cannot be imported in the hook process."""

    def __init__(
        self,
        traceback: str,
        message: Optional[str] = None,
        backend_name: Optional[str] = None,
        backend_path: Optional[Sequence[str]] = None,
    ) -> None:
        # Preserving arg order for the sake of API backward compatibility.
        self.backend_name = backend_name
        self.backend_path = backend_path
        self.traceback = traceback
        super().__init__(message or "Error while importing backend")


class HookMissing(Exception):
    """Will be raised on missing hooks (if a fallback can't be used)."""

    def __init__(self, hook_name: str) -> None:
        super().__init__(hook_name)
        self.hook_name = hook_name


class UnsupportedOperation(Exception):
    """May be raised by build_sdist if the backend indicates that it can't."""

    def __init__(self, traceback: str) -> None:
        self.traceback = traceback


def default_subprocess_runner(
    cmd: Sequence[str],
    cwd: Optional[str] = None,
    extra_environ: Optional[Mapping[str, str]] = None,
) -> None:
    """The default method of calling the wrapper subprocess.

    This uses :func:`subprocess.check_call` under the hood.
    """
    env = os.environ.copy()
    if extra_environ:
        env.update(extra_environ)

    check_call(cmd, cwd=cwd, env=env)


def quiet_subprocess_runner(
    cmd: Sequence[str],
    cwd: Optional[str] = None,
    extra_environ: Optional[Mapping[str, str]] = None,
) -> None:
    """Call the subprocess while suppressing output.

    This uses :func:`subprocess.check_output` under the hood.
    """
    env = os.environ.copy()
    if extra_environ:
        env.update(extra_environ)

    check_output(cmd, cwd=cwd, env=env, stderr=STDOUT)


def norm_and_check(source_tree: str, requested: str) -> str:
    """Normalise and check a backend path.

    Ensure that the requested backend path is specified as a relative path,
    and resolves to a location under the given source tree.

    Return an absolute version of the requested path.
    """
    if os.path.isabs(requested):
        raise ValueError("paths must be relative")

    abs_source = os.path.abspath(source_tree)
    abs_requested = os.path.normpath(os.path.join(abs_source, requested))
    # We have to use commonprefix for Python 2.7 compatibility. So we
    # normalise case to avoid problems because commonprefix is a character
    # based comparison :-(
    norm_source = os.path.normcase(abs_source)
    norm_requested = os.path.normcase(abs_requested)
    if os.path.commonprefix([norm_source, norm_requested]) != norm_source:
        raise ValueError("paths must be inside source tree")

    return abs_requested


class BuildBackendHookCaller:
    """A wrapper to call the build backend hooks for a source directory."""

    def __init__(
        self,
        source_dir: str,
        build_backend: str,
        backend_path: Optional[Sequence[str]] = None,
        runner: Optional["SubprocessRunner"] = None,
        python_executable: Optional[str] = None,
    ) -> None:
        """
        :param source_dir: The source directory to invoke the build backend for
        :param build_backend: The build backend spec
        :param backend_path: Additional path entries for the build backend spec
        :param runner: The :ref:`subprocess runner <Subprocess Runners>` to use
        :param python_executable:
            The Python executable used to invoke the build backend
        """
        if runner is None:
            runner = default_subprocess_runner

        self.source_dir = abspath(source_dir)
        self.build_backend = build_backend
        if backend_path:
            backend_path = [norm_and_check(self.source_dir, p) for p in backend_path]
        self.backend_path = backend_path
        self._subprocess_runner = runner
        if not python_executable:
            python_executable = sys.executable
        self.python_executable = python_executable

    @contextmanager
    def subprocess_runner(self, runner: "SubprocessRunner") -> Iterator[None]:
        """A context manager for temporarily overriding the default
        :ref:`subprocess runner <Subprocess Runners>`.

        :param runner: The new subprocess runner to use within the context.

        .. code-block:: python

            hook_caller = BuildBackendHookCaller(...)
            with hook_caller.subprocess_runner(quiet_subprocess_runner):
                ...
        """
        prev = self._subprocess_runner
        self._subprocess_runner = runner
        try:
            yield
        finally:
            self._subprocess_runner = prev

    def _supported_features(self) -> Sequence[str]:
        """Return the list of optional features supported by the backend."""
        return self._call_hook("_supported_features", {})

    def get_requires_for_build_wheel(
        self,
        config_settings: Optional[Mapping[str, Any]] = None,
    ) -> Sequence[str]:
        """Get additional dependencies required for building a wheel.

        :param config_settings: The configuration settings for the build backend
        :returns: A list of :pep:`dependency specifiers <508>`.

        .. admonition:: Fallback

            If the build backend does not defined a hook with this name, an
            empty list will be returned.
        """
        return self._call_hook(
            "get_requires_for_build_wheel", {"config_settings": config_settings}
        )

    def prepare_metadata_for_build_wheel(
        self,
        metadata_directory: str,
        config_settings: Optional[Mapping[str, Any]] = None,
        _allow_fallback: bool = True,
    ) -> str:
        """Prepare a ``*.dist-info`` folder with metadata for this project.

        :param metadata_directory: The directory to write the metadata to
        :param config_settings: The configuration settings for the build backend
        :param _allow_fallback:
            Whether to allow the fallback to building a wheel and extracting
            the metadata from it. Should be passed as a keyword argument only.

        :returns: Name of the newly created subfolder within
                  ``metadata_directory``, containing the metadata.

        .. admonition:: Fallback

            If the build backend does not define a hook with this name and
            ``_allow_fallback`` is truthy, the backend will be asked to build a
            wheel via the ``build_wheel`` hook and the dist-info extracted from
            that will be returned.
        """
        return self._call_hook(
            "prepare_metadata_for_build_wheel",
            {
                "metadata_directory": abspath(metadata_directory),
                "config_settings": config_settings,
                "_allow_fallback": _allow_fallback,
            },
        )

    def build_wheel(
        self,
        wheel_directory: str,
        config_settings: Optional[Mapping[str, Any]] = None,
        metadata_directory: Optional[str] = None,
    ) -> str:
        """Build a wheel from this project.

        :param wheel_directory: The directory to write the wheel to
        :param config_settings: The configuration settings for the build backend
        :param metadata_directory: The directory to reuse existing metadata from
        :returns:
            The name of the newly created wheel within ``wheel_directory``.

        .. admonition:: Interaction with fallback

            If the ``build_wheel`` hook was called in the fallback for
            :meth:`prepare_metadata_for_build_wheel`, the build backend would
            not be invoked. Instead, the previously built wheel will be copied
            to ``wheel_directory`` and the name of that file will be returned.
        """
        if metadata_directory is not None:
            metadata_directory = abspath(metadata_directory)
        return self._call_hook(
            "build_wheel",
            {
                "wheel_directory": abspath(wheel_directory),
                "config_settings": config_settings,
                "metadata_directory": metadata_directory,
            },
        )

    def get_requires_for_build_editable(
        self,
        config_settings: Optional[Mapping[str, Any]] = None,
    ) -> Sequence[str]:
        """Get additional dependencies required for building an editable wheel.

        :param config_settings: The configuration settings for the build backend
        :returns: A list of :pep:`dependency specifiers <508>`.

        .. admonition:: Fallback

            If the build backend does not defined a hook with this name, an
            empty list will be returned.
        """
        return self._call_hook(
            "get_requires_for_build_editable", {"config_settings": config_settings}
        )

    def prepare_metadata_for_build_editable(
        self,
        metadata_directory: str,
        config_settings: Optional[Mapping[str, Any]] = None,
        _allow_fallback: bool = True,
    ) -> Optional[str]:
        """Prepare a ``*.dist-info`` folder with metadata for this project.

        :param metadata_directory: The directory to write the metadata to
        :param config_settings: The configuration settings for the build backend
        :param _allow_fallback:
            Whether to allow the fallback to building a wheel and extracting
            the metadata from it. Should be passed as a keyword argument only.
        :returns: Name of the newly created subfolder within
                  ``metadata_directory``, containing the metadata.

        .. admonition:: Fallback

            If the build backend does not define a hook with this name and
            ``_allow_fallback`` is truthy, the backend will be asked to build a
            wheel via the ``build_editable`` hook and the dist-info
            extracted from that will be returned.
        """
        return self._call_hook(
            "prepare_metadata_for_build_editable",
            {
                "metadata_directory": abspath(metadata_directory),
                "config_settings": config_settings,
                "_allow_fallback": _allow_fallback,
            },
        )

    def build_editable(
        self,
        wheel_directory: str,
        config_settings: Optional[Mapping[str, Any]] = None,
        metadata_directory: Optional[str] = None,
    ) -> str:
        """Build an editable wheel from this project.

        :param wheel_directory: The directory to write the wheel to
        :param config_settings: The configuration settings for the build backend
        :param metadata_directory: The directory to reuse existing metadata from
        :returns:
            The name of the newly created wheel within ``wheel_directory``.

        .. admonition:: Interaction with fallback

            If the ``build_editable`` hook was called in the fallback for
            :meth:`prepare_metadata_for_build_editable`, the build backend
            would not be invoked. Instead, the previously built wheel will be
            copied to ``wheel_directory`` and the name of that file will be
            returned.
        """
        if metadata_directory is not None:
            metadata_directory = abspath(metadata_directory)
        return self._call_hook(
            "build_editable",
            {
                "wheel_directory": abspath(wheel_directory),
                "config_settings": config_settings,
                "metadata_directory": metadata_directory,
            },
        )

    def get_requires_for_build_sdist(
        self,
        config_settings: Optional[Mapping[str, Any]] = None,
    ) -> Sequence[str]:
        """Get additional dependencies required for building an sdist.

        :returns: A list of :pep:`dependency specifiers <508>`.
        """
        return self._call_hook(
            "get_requires_for_build_sdist", {"config_settings": config_settings}
        )

    def build_sdist(
        self,
        sdist_directory: str,
        config_settings: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """Build an sdist from this project.

        :returns:
            The name of the newly created sdist within ``wheel_directory``.
        """
        return self._call_hook(
            "build_sdist",
            {
                "sdist_directory": abspath(sdist_directory),
                "config_settings": config_settings,
            },
        )

    def _call_hook(self, hook_name: str, kwargs: Mapping[str, Any]) -> Any:
        extra_environ = {"_PYPROJECT_HOOKS_BUILD_BACKEND": self.build_backend}

        if self.backend_path:
            backend_path = os.pathsep.join(self.backend_path)
            extra_environ["_PYPROJECT_HOOKS_BACKEND_PATH"] = backend_path

        with tempfile.TemporaryDirectory() as td:
            hook_input = {"kwargs": kwargs}
            write_json(hook_input, pjoin(td, "input.json"), indent=2)

            # Run the hook in a subprocess
            with _in_proc_script_path() as script:
                python = self.python_executable
                self._subprocess_runner(
                    [python, abspath(str(script)), hook_name, td],
                    cwd=self.source_dir,
                    extra_environ=extra_environ,
                )

            data = read_json(pjoin(td, "output.json"))
            if data.get("unsupported"):
                raise UnsupportedOperation(data.get("traceback", ""))
            if data.get("no_backend"):
                raise BackendUnavailable(
                    data.get("traceback", ""),
                    message=data.get("backend_error", ""),
                    backend_name=self.build_backend,
                    backend_path=self.backend_path,
                )
            if data.get("hook_missing"):
                raise HookMissing(data.get("missing_hook_name") or hook_name)
            return data["return_val"]

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\theorem.py ===
"""
    pygments.lexers.theorem
    ~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for theorem-proving languages.

    See also :mod:`pygments.lexers.lean`

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, bygroups, default, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Generic, Whitespace
# compatibility import
from pygments.lexers.lean import LeanLexer # noqa: F401

__all__ = ['CoqLexer', 'IsabelleLexer']


class CoqLexer(RegexLexer):
    """
    For the Coq theorem prover.
    """

    name = 'Coq'
    url = 'http://coq.inria.fr/'
    aliases = ['coq']
    filenames = ['*.v']
    mimetypes = ['text/x-coq']
    version_added = '1.5'

    flags = 0 # no re.MULTILINE

    keywords1 = (
        # Vernacular commands
        'Section', 'Module', 'End', 'Require', 'Import', 'Export', 'Include', 'Variable',
        'Variables', 'Parameter', 'Parameters', 'Axiom', 'Axioms', 'Hypothesis',
        'Hypotheses', 'Notation', 'Local', 'Tactic', 'Reserved', 'Scope',
        'Open', 'Close', 'Bind', 'Declare', 'Delimit', 'Definition', 'Example', 'Let',
        'Ltac', 'Ltac2', 'Fixpoint', 'CoFixpoint', 'Morphism', 'Relation', 'Implicit',
        'Arguments', 'Types', 'Contextual', 'Strict', 'Prenex',
        'Implicits', 'Inductive', 'CoInductive', 'Record', 'Structure',
        'Variant', 'Canonical', 'Coercion', 'Theorem', 'Lemma', 'Fact',
        'Remark', 'Corollary', 'Proposition', 'Property', 'Goal',
        'Proof', 'Restart', 'Save', 'Qed', 'Defined', 'Abort', 'Admitted',
        'Hint', 'Resolve', 'Rewrite', 'View', 'Search', 'Compute', 'Eval',
        'Show', 'Print', 'Printing', 'All', 'Graph', 'Projections', 'inside',
        'outside', 'Check', 'Global', 'Instance', 'Class', 'Existing',
        'Universe', 'Polymorphic', 'Monomorphic', 'Context', 'Scheme', 'From',
        'Undo', 'Fail', 'Function', 'Program', 'Elpi', 'Extract', 'Opaque',
        'Transparent', 'Unshelve', 'Next Obligation',
    )
    keywords2 = (
        # Gallina
        'forall', 'exists', 'exists2', 'fun', 'fix', 'cofix', 'struct',
        'match', 'end',  'in', 'return', 'let', 'if', 'is', 'then', 'else',
        'for', 'of', 'nosimpl', 'with', 'as',
    )
    keywords3 = (
        # Sorts
        'Type', 'Prop', 'SProp', 'Set',
    )
    keywords4 = (
        # Tactics
        'pose', 'set', 'move', 'case', 'elim', 'apply', 'clear', 'hnf', 'intro',
        'intros', 'generalize', 'rename', 'pattern', 'after', 'destruct',
        'induction', 'using', 'refine', 'inversion', 'injection', 'rewrite',
        'congr', 'unlock', 'compute', 'ring', 'field', 'replace', 'fold',
        'unfold', 'change', 'cutrewrite', 'simpl', 'have', 'suff', 'wlog',
        'suffices', 'without', 'loss', 'nat_norm', 'assert', 'cut', 'trivial',
        'revert', 'bool_congr', 'nat_congr', 'symmetry', 'transitivity', 'auto',
        'split', 'left', 'right', 'autorewrite', 'tauto', 'setoid_rewrite',
        'intuition', 'eauto', 'eapply', 'econstructor', 'etransitivity',
        'constructor', 'erewrite', 'red', 'cbv', 'lazy', 'vm_compute',
        'native_compute', 'subst',
    )
    keywords5 = (
        # Terminators
        'by', 'now', 'done', 'exact', 'reflexivity',
        'tauto', 'romega', 'omega', 'lia', 'nia', 'lra', 'nra', 'psatz',
        'assumption', 'solve', 'contradiction', 'discriminate',
        'congruence', 'admit'
    )
    keywords6 = (
        # Control
        'do', 'last', 'first', 'try', 'idtac', 'repeat',
    )
    # 'as', 'assert', 'begin', 'class', 'constraint', 'do', 'done',
    # 'downto', 'else', 'end', 'exception', 'external', 'false',
    # 'for', 'fun', 'function', 'functor', 'if', 'in', 'include',
    # 'inherit', 'initializer', 'lazy', 'let', 'match', 'method',
    # 'module', 'mutable', 'new', 'object', 'of', 'open', 'private',
    # 'raise', 'rec', 'sig', 'struct', 'then', 'to', 'true', 'try',
    # 'type', 'val', 'virtual', 'when', 'while', 'with'
    keyopts = (
        '!=', '#', '&', '&&', r'\(', r'\)', r'\*', r'\+', ',', '-', r'-\.',
        '->', r'\.', r'\.\.', ':', '::', ':=', ':>', ';', ';;', '<', '<-',
        '<->', '=', '>', '>]', r'>\}', r'\?', r'\?\?', r'\[', r'\[<', r'\[>',
        r'\[\|', ']', '_', '`', r'\{', r'\{<', r'lp:\{\{', r'\|', r'\|]', r'\}', '~', '=>',
        r'/\\', r'\\/', r'\{\|', r'\|\}',
        # 'Π', 'Σ', # Not defined in the standard library
        'λ', '¬', '∧', '∨', '∀', '∃', '→', '↔', '≠', '≤', '≥',
    )
    operators = r'[!$%&*+\./:<=>?@^|~-]'
    prefix_syms = r'[!?~]'
    infix_syms = r'[=<>@^|&+\*/$%-]'

    tokens = {
        'root': [
            (r'\s+', Text),
            (r'false|true|\(\)|\[\]', Name.Builtin.Pseudo),
            (r'\(\*', Comment, 'comment'),
            (r'\b(?:[^\W\d][\w\']*\.)+[^\W\d][\w\']*\b', Name),
            (r'\bEquations\b\??', Keyword.Namespace),
            (r'\b(Elpi)(\s+)(Program|Query|Accumulate|Command|Typecheck|Db|Export|Tactic)?\b', bygroups(Keyword.Namespace,Text,Keyword.Namespace)),
            # Very weak heuristic to distinguish the Set vernacular from the Set sort
            (r'\bUnset\b|\bSet(?=[ \t]+[A-Z][a-z][^\n]*?\.)', Keyword.Namespace, 'set-options'),
            (r'\b(?:String|Number)\s+Notation', Keyword.Namespace, 'sn-notation'),
            (words(keywords1, prefix=r'\b', suffix=r'\b'), Keyword.Namespace),
            (words(keywords2, prefix=r'\b', suffix=r'\b'), Keyword),
            (words(keywords3, prefix=r'\b', suffix=r'\b'), Keyword.Type),
            (words(keywords4, prefix=r'\b', suffix=r'\b'), Keyword),
            (words(keywords5, prefix=r'\b', suffix=r'\b'), Keyword.Pseudo),
            (words(keywords6, prefix=r'\b', suffix=r'\b'), Keyword.Reserved),
            # (r'\b([A-Z][\w\']*)(\.)', Name.Namespace, 'dotted'),
            (r'\b([A-Z][\w\']*)', Name),
            (r'({})'.format('|'.join(keyopts[::-1])), Operator),
            (rf'({infix_syms}|{prefix_syms})?{operators}', Operator),

            (r"[^\W\d][\w']*", Name),

            (r'\d[\d_]*', Number.Integer),
            (r'0[xX][\da-fA-F][\da-fA-F_]*', Number.Hex),
            (r'0[oO][0-7][0-7_]*', Number.Oct),
            (r'0[bB][01][01_]*', Number.Bin),
            (r'-?\d[\d_]*(.[\d_]*)?([eE][+\-]?\d[\d_]*)', Number.Float),

            (r"'(?:(\\[\\\"'ntbr ])|(\\[0-9]{3})|(\\x[0-9a-fA-F]{2}))'", String.Char),

            (r"'.'", String.Char),
            (r"'", Keyword),  # a stray quote is another syntax element

            (r'"', String.Double, 'string'),

            (r'[~?][a-z][\w\']*:', Name),
            (r'\S', Name.Builtin.Pseudo),
        ],
        'set-options': [
            (r'\s+', Text),
            (r'[A-Z]\w*', Keyword.Namespace),
            (r'"', String.Double, 'string'),
            (r'\d+', Number.Integer),
            (r'\.', Punctuation, '#pop'),
        ],
        'sn-notation': [
            (r'\s+', Text),
            # Extra keywords to highlight only in this scope
            (r'\b(?:via|mapping|abstract|warning|after)\b', Keyword),
            (r'=>|[()\[\]:,]', Operator),
            (r'\b[^\W\d][\w\']*(?:\.[^\W\d][\w\']*)*\b', Name),
            (r'\d[\d_]*', Number.Integer),
            (r'0[xX][\da-fA-F][\da-fA-F_]*', Number.Hex),
            (r'\(\*', Comment, 'comment'),
            (r'\.', Punctuation, '#pop'),
        ],
        'comment': [
            # Consume comments like ***** as one token
            (r'([^(*)]+|\*+(?!\)))+', Comment),
            (r'\(\*', Comment, '#push'),
            (r'\*\)', Comment, '#pop'),
            (r'[(*)]', Comment),
        ],
        'string': [
            (r'[^"]+', String.Double),
            (r'""', String.Double),
            (r'"', String.Double, '#pop'),
        ],
        'dotted': [
            (r'\s+', Text),
            (r'\.', Punctuation),
            (r'[A-Z][\w\']*(?=\s*\.)', Name.Namespace),
            (r'[A-Z][\w\']*', Name.Class, '#pop'),
            (r'[a-z][a-z0-9_\']*', Name, '#pop'),
            default('#pop')
        ],
    }

    def analyse_text(text):
        if 'Qed' in text and 'Proof' in text:
            return 1


class IsabelleLexer(RegexLexer):
    """
    For the Isabelle proof assistant.
    """

    name = 'Isabelle'
    url = 'https://isabelle.in.tum.de/'
    aliases = ['isabelle']
    filenames = ['*.thy']
    mimetypes = ['text/x-isabelle']
    version_added = '2.0'

    keyword_minor = (
        'and', 'assumes', 'attach', 'avoids', 'binder', 'checking',
        'class_instance', 'class_relation', 'code_module', 'congs',
        'constant', 'constrains', 'datatypes', 'defines', 'file', 'fixes',
        'for', 'functions', 'hints', 'identifier', 'if', 'imports', 'in',
        'includes', 'infix', 'infixl', 'infixr', 'is', 'keywords', 'lazy',
        'module_name', 'monos', 'morphisms', 'no_discs_sels', 'notes',
        'obtains', 'open', 'output', 'overloaded', 'parametric', 'permissive',
        'pervasive', 'rep_compat', 'shows', 'structure', 'type_class',
        'type_constructor', 'unchecked', 'unsafe', 'where',
    )

    keyword_diag = (
        'ML_command', 'ML_val', 'class_deps', 'code_deps', 'code_thms',
        'display_drafts', 'find_consts', 'find_theorems', 'find_unused_assms',
        'full_prf', 'help', 'locale_deps', 'nitpick', 'pr', 'prf',
        'print_abbrevs', 'print_antiquotations', 'print_attributes',
        'print_binds', 'print_bnfs', 'print_bundles',
        'print_case_translations', 'print_cases', 'print_claset',
        'print_classes', 'print_codeproc', 'print_codesetup',
        'print_coercions', 'print_commands', 'print_context',
        'print_defn_rules', 'print_dependencies', 'print_facts',
        'print_induct_rules', 'print_inductives', 'print_interps',
        'print_locale', 'print_locales', 'print_methods', 'print_options',
        'print_orders', 'print_quot_maps', 'print_quotconsts',
        'print_quotients', 'print_quotientsQ3', 'print_quotmapsQ3',
        'print_rules', 'print_simpset', 'print_state', 'print_statement',
        'print_syntax', 'print_theorems', 'print_theory', 'print_trans_rules',
        'prop', 'pwd', 'quickcheck', 'refute', 'sledgehammer', 'smt_status',
        'solve_direct', 'spark_status', 'term', 'thm', 'thm_deps', 'thy_deps',
        'try', 'try0', 'typ', 'unused_thms', 'value', 'values', 'welcome',
        'print_ML_antiquotations', 'print_term_bindings', 'values_prolog',
    )

    keyword_thy = ('theory', 'begin', 'end')

    keyword_section = ('header', 'chapter')

    keyword_subsection = (
        'section', 'subsection', 'subsubsection', 'sect', 'subsect',
        'subsubsect',
    )

    keyword_theory_decl = (
        'ML', 'ML_file', 'abbreviation', 'adhoc_overloading', 'arities',
        'atom_decl', 'attribute_setup', 'axiomatization', 'bundle',
        'case_of_simps', 'class', 'classes', 'classrel', 'codatatype',
        'code_abort', 'code_class', 'code_const', 'code_datatype',
        'code_identifier', 'code_include', 'code_instance', 'code_modulename',
        'code_monad', 'code_printing', 'code_reflect', 'code_reserved',
        'code_type', 'coinductive', 'coinductive_set', 'consts', 'context',
        'datatype', 'datatype_new', 'datatype_new_compat', 'declaration',
        'declare', 'default_sort', 'defer_recdef', 'definition', 'defs',
        'domain', 'domain_isomorphism', 'domaindef', 'equivariance',
        'export_code', 'extract', 'extract_type', 'fixrec', 'fun',
        'fun_cases', 'hide_class', 'hide_const', 'hide_fact', 'hide_type',
        'import_const_map', 'import_file', 'import_tptp', 'import_type_map',
        'inductive', 'inductive_set', 'instantiation', 'judgment', 'lemmas',
        'lifting_forget', 'lifting_update', 'local_setup', 'locale',
        'method_setup', 'nitpick_params', 'no_adhoc_overloading',
        'no_notation', 'no_syntax', 'no_translations', 'no_type_notation',
        'nominal_datatype', 'nonterminal', 'notation', 'notepad', 'oracle',
        'overloading', 'parse_ast_translation', 'parse_translation',
        'partial_function', 'primcorec', 'primrec', 'primrec_new',
        'print_ast_translation', 'print_translation', 'quickcheck_generator',
        'quickcheck_params', 'realizability', 'realizers', 'recdef', 'record',
        'refute_params', 'setup', 'setup_lifting', 'simproc_setup',
        'simps_of_case', 'sledgehammer_params', 'spark_end', 'spark_open',
        'spark_open_siv', 'spark_open_vcg', 'spark_proof_functions',
        'spark_types', 'statespace', 'syntax', 'syntax_declaration', 'text',
        'text_raw', 'theorems', 'translations', 'type_notation',
        'type_synonym', 'typed_print_translation', 'typedecl', 'hoarestate',
        'install_C_file', 'install_C_types', 'wpc_setup', 'c_defs', 'c_types',
        'memsafe', 'SML_export', 'SML_file', 'SML_import', 'approximate',
        'bnf_axiomatization', 'cartouche', 'datatype_compat',
        'free_constructors', 'functor', 'nominal_function',
        'nominal_termination', 'permanent_interpretation',
        'binds', 'defining', 'smt2_status', 'term_cartouche',
        'boogie_file', 'text_cartouche',
    )

    keyword_theory_script = ('inductive_cases', 'inductive_simps')

    keyword_theory_goal = (
        'ax_specification', 'bnf', 'code_pred', 'corollary', 'cpodef',
        'crunch', 'crunch_ignore',
        'enriched_type', 'function', 'instance', 'interpretation', 'lemma',
        'lift_definition', 'nominal_inductive', 'nominal_inductive2',
        'nominal_primrec', 'pcpodef', 'primcorecursive',
        'quotient_definition', 'quotient_type', 'recdef_tc', 'rep_datatype',
        'schematic_corollary', 'schematic_lemma', 'schematic_theorem',
        'spark_vc', 'specification', 'subclass', 'sublocale', 'termination',
        'theorem', 'typedef', 'wrap_free_constructors',
    )

    keyword_qed = ('by', 'done', 'qed')
    keyword_abandon_proof = ('sorry', 'oops')

    keyword_proof_goal = ('have', 'hence', 'interpret')

    keyword_proof_block = ('next', 'proof')

    keyword_proof_chain = (
        'finally', 'from', 'then', 'ultimately', 'with',
    )

    keyword_proof_decl = (
        'ML_prf', 'also', 'include', 'including', 'let', 'moreover', 'note',
        'txt', 'txt_raw', 'unfolding', 'using', 'write',
    )

    keyword_proof_asm = ('assume', 'case', 'def', 'fix', 'presume')

    keyword_proof_asm_goal = ('guess', 'obtain', 'show', 'thus')

    keyword_proof_script = (
        'apply', 'apply_end', 'apply_trace', 'back', 'defer', 'prefer',
    )

    operators = (
        '::', ':', '(', ')', '[', ']', '_', '=', ',', '|',
        '+', '-', '!', '?',
    )

    proof_operators = ('{', '}', '.', '..')

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'\(\*', Comment, 'comment'),
            (r'\\<open>', String.Symbol, 'cartouche'),
            (r'\{\*|‹', String, 'cartouche'),

            (words(operators), Operator),
            (words(proof_operators), Operator.Word),

            (words(keyword_minor, prefix=r'\b', suffix=r'\b'), Keyword.Pseudo),

            (words(keyword_diag, prefix=r'\b', suffix=r'\b'), Keyword.Type),

            (words(keyword_thy, prefix=r'\b', suffix=r'\b'), Keyword),
            (words(keyword_theory_decl, prefix=r'\b', suffix=r'\b'), Keyword),

            (words(keyword_section, prefix=r'\b', suffix=r'\b'), Generic.Heading),
            (words(keyword_subsection, prefix=r'\b', suffix=r'\b'), Generic.Subheading),

            (words(keyword_theory_goal, prefix=r'\b', suffix=r'\b'), Keyword.Namespace),
            (words(keyword_theory_script, prefix=r'\b', suffix=r'\b'), Keyword.Namespace),

            (words(keyword_abandon_proof, prefix=r'\b', suffix=r'\b'), Generic.Error),

            (words(keyword_qed, prefix=r'\b', suffix=r'\b'), Keyword),
            (words(keyword_proof_goal, prefix=r'\b', suffix=r'\b'), Keyword),
            (words(keyword_proof_block, prefix=r'\b', suffix=r'\b'), Keyword),
            (words(keyword_proof_decl, prefix=r'\b', suffix=r'\b'), Keyword),

            (words(keyword_proof_chain, prefix=r'\b', suffix=r'\b'), Keyword),
            (words(keyword_proof_asm, prefix=r'\b', suffix=r'\b'), Keyword),
            (words(keyword_proof_asm_goal, prefix=r'\b', suffix=r'\b'), Keyword),

            (words(keyword_proof_script, prefix=r'\b', suffix=r'\b'), Keyword.Pseudo),

            (r'\\<(\w|\^)*>', Text.Symbol),

            (r"'[^\W\d][.\w']*", Name.Type),

            (r'0[xX][\da-fA-F][\da-fA-F_]*', Number.Hex),
            (r'0[oO][0-7][0-7_]*', Number.Oct),
            (r'0[bB][01][01_]*', Number.Bin),

            (r'"', String, 'string'),
            (r'`', String.Other, 'fact'),
            (r'[^\s:|\[\]\-()=,+!?{}._][^\s:|\[\]\-()=,+!?{}]*', Name),
        ],
        'comment': [
            (r'[^(*)]+', Comment),
            (r'\(\*', Comment, '#push'),
            (r'\*\)', Comment, '#pop'),
            (r'[(*)]', Comment),
        ],
        'cartouche': [
            (r'[^{*}\\‹›]+', String),
            (r'\\<open>', String.Symbol, '#push'),
            (r'\{\*|‹', String, '#push'),
            (r'\\<close>', String.Symbol, '#pop'),
            (r'\*\}|›', String, '#pop'),
            (r'\\<(\w|\^)*>', String.Symbol),
            (r'[{*}\\]', String),
        ],
        'string': [
            (r'[^"\\]+', String),
            (r'\\<(\w|\^)*>', String.Symbol),
            (r'\\"', String),
            (r'\\', String),
            (r'"', String, '#pop'),
        ],
        'fact': [
            (r'[^`\\]+', String.Other),
            (r'\\<(\w|\^)*>', String.Symbol),
            (r'\\`', String.Other),
            (r'\\', String.Other),
            (r'`', String.Other, '#pop'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\joblib\externals\loky\backend\synchronize.py ===
###############################################################################
# Synchronization primitives based on our SemLock implementation
#
# author: Thomas Moreau and Olivier Grisel
#
# adapted from multiprocessing/synchronize.py (17/02/2017)
#  * Remove ctx argument for compatibility reason
#  * Registers a cleanup function with the loky resource_tracker to remove the
#    semaphore when the process dies instead.
#
# TODO: investigate which Python version is required to be able to use
# multiprocessing.resource_tracker and therefore multiprocessing.synchronize
# instead of a loky-specific fork.

import os
import sys
import tempfile
import threading
import _multiprocessing
from time import time as _time
from multiprocessing import process, util
from multiprocessing.context import assert_spawning

from . import resource_tracker

__all__ = [
    "Lock",
    "RLock",
    "Semaphore",
    "BoundedSemaphore",
    "Condition",
    "Event",
]
# Try to import the mp.synchronize module cleanly, if it fails
# raise ImportError for platforms lacking a working sem_open implementation.
# See issue 3770
try:
    from _multiprocessing import SemLock as _SemLock
    from _multiprocessing import sem_unlink
except ImportError:
    raise ImportError(
        "This platform lacks a functioning sem_open"
        " implementation, therefore, the required"
        " synchronization primitives needed will not"
        " function, see issue 3770."
    )

#
# Constants
#

RECURSIVE_MUTEX, SEMAPHORE = range(2)
SEM_VALUE_MAX = _multiprocessing.SemLock.SEM_VALUE_MAX


#
# Base class for semaphores and mutexes; wraps `_multiprocessing.SemLock`
#


class SemLock:

    _rand = tempfile._RandomNameSequence()

    def __init__(self, kind, value, maxvalue, name=None):
        # unlink_now is only used on win32 or when we are using fork.
        unlink_now = False
        if name is None:
            # Try to find an unused name for the SemLock instance.
            for _ in range(100):
                try:
                    self._semlock = _SemLock(
                        kind, value, maxvalue, SemLock._make_name(), unlink_now
                    )
                except FileExistsError:  # pragma: no cover
                    pass
                else:
                    break
            else:  # pragma: no cover
                raise FileExistsError("cannot find name for semaphore")
        else:
            self._semlock = _SemLock(kind, value, maxvalue, name, unlink_now)
        self.name = name
        util.debug(
            f"created semlock with handle {self._semlock.handle} and name "
            f'"{self.name}"'
        )

        self._make_methods()

        def _after_fork(obj):
            obj._semlock._after_fork()

        util.register_after_fork(self, _after_fork)

        # When the object is garbage collected or the
        # process shuts down we unlink the semaphore name
        resource_tracker.register(self._semlock.name, "semlock")
        util.Finalize(
            self, SemLock._cleanup, (self._semlock.name,), exitpriority=0
        )

    @staticmethod
    def _cleanup(name):
        try:
            sem_unlink(name)
        except FileNotFoundError:
            # Already unlinked, possibly by user code: ignore and make sure to
            # unregister the semaphore from the resource tracker.
            pass
        finally:
            resource_tracker.unregister(name, "semlock")

    def _make_methods(self):
        self.acquire = self._semlock.acquire
        self.release = self._semlock.release

    def __enter__(self):
        return self._semlock.acquire()

    def __exit__(self, *args):
        return self._semlock.release()

    def __getstate__(self):
        assert_spawning(self)
        sl = self._semlock
        h = sl.handle
        return (h, sl.kind, sl.maxvalue, sl.name)

    def __setstate__(self, state):
        self._semlock = _SemLock._rebuild(*state)
        util.debug(
            f'recreated blocker with handle {state[0]!r} and name "{state[3]}"'
        )
        self._make_methods()

    @staticmethod
    def _make_name():
        # OSX does not support long names for semaphores
        return f"/loky-{os.getpid()}-{next(SemLock._rand)}"


#
# Semaphore
#


class Semaphore(SemLock):
    def __init__(self, value=1):
        SemLock.__init__(self, SEMAPHORE, value, SEM_VALUE_MAX)

    def get_value(self):
        if sys.platform == "darwin":
            raise NotImplementedError("OSX does not implement sem_getvalue")
        return self._semlock._get_value()

    def __repr__(self):
        try:
            value = self._semlock._get_value()
        except Exception:
            value = "unknown"
        return f"<{self.__class__.__name__}(value={value})>"


#
# Bounded semaphore
#


class BoundedSemaphore(Semaphore):
    def __init__(self, value=1):
        SemLock.__init__(self, SEMAPHORE, value, value)

    def __repr__(self):
        try:
            value = self._semlock._get_value()
        except Exception:
            value = "unknown"
        return (
            f"<{self.__class__.__name__}(value={value}, "
            f"maxvalue={self._semlock.maxvalue})>"
        )


#
# Non-recursive lock
#


class Lock(SemLock):
    def __init__(self):
        super().__init__(SEMAPHORE, 1, 1)

    def __repr__(self):
        try:
            if self._semlock._is_mine():
                name = process.current_process().name
                if threading.current_thread().name != "MainThread":
                    name = f"{name}|{threading.current_thread().name}"
            elif self._semlock._get_value() == 1:
                name = "None"
            elif self._semlock._count() > 0:
                name = "SomeOtherThread"
            else:
                name = "SomeOtherProcess"
        except Exception:
            name = "unknown"
        return f"<{self.__class__.__name__}(owner={name})>"


#
# Recursive lock
#


class RLock(SemLock):
    def __init__(self):
        super().__init__(RECURSIVE_MUTEX, 1, 1)

    def __repr__(self):
        try:
            if self._semlock._is_mine():
                name = process.current_process().name
                if threading.current_thread().name != "MainThread":
                    name = f"{name}|{threading.current_thread().name}"
                count = self._semlock._count()
            elif self._semlock._get_value() == 1:
                name, count = "None", 0
            elif self._semlock._count() > 0:
                name, count = "SomeOtherThread", "nonzero"
            else:
                name, count = "SomeOtherProcess", "nonzero"
        except Exception:
            name, count = "unknown", "unknown"
        return f"<{self.__class__.__name__}({name}, {count})>"


#
# Condition variable
#


class Condition:
    def __init__(self, lock=None):
        self._lock = lock or RLock()
        self._sleeping_count = Semaphore(0)
        self._woken_count = Semaphore(0)
        self._wait_semaphore = Semaphore(0)
        self._make_methods()

    def __getstate__(self):
        assert_spawning(self)
        return (
            self._lock,
            self._sleeping_count,
            self._woken_count,
            self._wait_semaphore,
        )

    def __setstate__(self, state):
        (
            self._lock,
            self._sleeping_count,
            self._woken_count,
            self._wait_semaphore,
        ) = state
        self._make_methods()

    def __enter__(self):
        return self._lock.__enter__()

    def __exit__(self, *args):
        return self._lock.__exit__(*args)

    def _make_methods(self):
        self.acquire = self._lock.acquire
        self.release = self._lock.release

    def __repr__(self):
        try:
            num_waiters = (
                self._sleeping_count._semlock._get_value()
                - self._woken_count._semlock._get_value()
            )
        except Exception:
            num_waiters = "unknown"
        return f"<{self.__class__.__name__}({self._lock}, {num_waiters})>"

    def wait(self, timeout=None):
        assert (
            self._lock._semlock._is_mine()
        ), "must acquire() condition before using wait()"

        # indicate that this thread is going to sleep
        self._sleeping_count.release()

        # release lock
        count = self._lock._semlock._count()
        for _ in range(count):
            self._lock.release()

        try:
            # wait for notification or timeout
            return self._wait_semaphore.acquire(True, timeout)
        finally:
            # indicate that this thread has woken
            self._woken_count.release()

            # reacquire lock
            for _ in range(count):
                self._lock.acquire()

    def notify(self):
        assert self._lock._semlock._is_mine(), "lock is not owned"
        assert not self._wait_semaphore.acquire(False)

        # to take account of timeouts since last notify() we subtract
        # woken_count from sleeping_count and rezero woken_count
        while self._woken_count.acquire(False):
            res = self._sleeping_count.acquire(False)
            assert res

        if self._sleeping_count.acquire(False):  # try grabbing a sleeper
            self._wait_semaphore.release()  # wake up one sleeper
            self._woken_count.acquire()  # wait for the sleeper to wake

            # rezero _wait_semaphore in case a timeout just happened
            self._wait_semaphore.acquire(False)

    def notify_all(self):
        assert self._lock._semlock._is_mine(), "lock is not owned"
        assert not self._wait_semaphore.acquire(False)

        # to take account of timeouts since last notify*() we subtract
        # woken_count from sleeping_count and rezero woken_count
        while self._woken_count.acquire(False):
            res = self._sleeping_count.acquire(False)
            assert res

        sleepers = 0
        while self._sleeping_count.acquire(False):
            self._wait_semaphore.release()  # wake up one sleeper
            sleepers += 1

        if sleepers:
            for _ in range(sleepers):
                self._woken_count.acquire()  # wait for a sleeper to wake

            # rezero wait_semaphore in case some timeouts just happened
            while self._wait_semaphore.acquire(False):
                pass

    def wait_for(self, predicate, timeout=None):
        result = predicate()
        if result:
            return result
        if timeout is not None:
            endtime = _time() + timeout
        else:
            endtime = None
            waittime = None
        while not result:
            if endtime is not None:
                waittime = endtime - _time()
                if waittime <= 0:
                    break
            self.wait(waittime)
            result = predicate()
        return result


#
# Event
#


class Event:
    def __init__(self):
        self._cond = Condition(Lock())
        self._flag = Semaphore(0)

    def is_set(self):
        with self._cond:
            if self._flag.acquire(False):
                self._flag.release()
                return True
            return False

    def set(self):
        with self._cond:
            self._flag.acquire(False)
            self._flag.release()
            self._cond.notify_all()

    def clear(self):
        with self._cond:
            self._flag.acquire(False)

    def wait(self, timeout=None):
        with self._cond:
            if self._flag.acquire(False):
                self._flag.release()
            else:
                self._cond.wait(timeout)

            if self._flag.acquire(False):
                self._flag.release()
                return True
            return False

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\custom_logger.py ===
#### What this does ####
#    On success, logs events to Promptlayer
import traceback
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
)

from pydantic import BaseModel

from litellm.caching.caching import DualCache
from litellm.proxy._types import UserAPIKeyAuth
from litellm.types.integrations.argilla import ArgillaItem
from litellm.types.llms.openai import AllMessageValues, ChatCompletionRequest
from litellm.types.utils import (
    AdapterCompletionStreamWrapper,
    CallTypes,
    LLMResponseTypes,
    ModelResponse,
    ModelResponseStream,
    StandardCallbackDynamicParams,
    StandardLoggingPayload,
)

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj

    Span = Union[_Span, Any]
else:
    Span = Any
    LiteLLMLoggingObj = Any


class CustomLogger:  # https://docs.litellm.ai/docs/observability/custom_callback#callback-class
    # Class variables or attributes
    def __init__(self, message_logging: bool = True, **kwargs) -> None:
        self.message_logging = message_logging
        pass

    def log_pre_api_call(self, model, messages, kwargs):
        pass

    def log_post_api_call(self, kwargs, response_obj, start_time, end_time):
        pass

    def log_stream_event(self, kwargs, response_obj, start_time, end_time):
        pass

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        pass

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        pass

    #### ASYNC ####

    async def async_log_stream_event(self, kwargs, response_obj, start_time, end_time):
        pass

    async def async_log_pre_api_call(self, model, messages, kwargs):
        pass

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        pass

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        pass

    #### PROMPT MANAGEMENT HOOKS ####

    async def async_get_chat_completion_prompt(
        self,
        model: str,
        messages: List[AllMessageValues],
        non_default_params: dict,
        prompt_id: Optional[str],
        prompt_variables: Optional[dict],
        dynamic_callback_params: StandardCallbackDynamicParams,
        litellm_logging_obj: LiteLLMLoggingObj,
        tools: Optional[List[Dict]] = None,
        prompt_label: Optional[str] = None,
    ) -> Tuple[str, List[AllMessageValues], dict]:
        """
        Returns:
        - model: str - the model to use (can be pulled from prompt management tool)
        - messages: List[AllMessageValues] - the messages to use (can be pulled from prompt management tool)
        - non_default_params: dict - update with any optional params (e.g. temperature, max_tokens, etc.) to use (can be pulled from prompt management tool)
        """
        return model, messages, non_default_params

    def get_chat_completion_prompt(
        self,
        model: str,
        messages: List[AllMessageValues],
        non_default_params: dict,
        prompt_id: Optional[str],
        prompt_variables: Optional[dict],
        dynamic_callback_params: StandardCallbackDynamicParams,
        prompt_label: Optional[str] = None,
    ) -> Tuple[str, List[AllMessageValues], dict]:
        """
        Returns:
        - model: str - the model to use (can be pulled from prompt management tool)
        - messages: List[AllMessageValues] - the messages to use (can be pulled from prompt management tool)
        - non_default_params: dict - update with any optional params (e.g. temperature, max_tokens, etc.) to use (can be pulled from prompt management tool)
        """
        return model, messages, non_default_params

    #### PRE-CALL CHECKS - router/proxy only ####
    """
    Allows usage-based-routing-v2 to run pre-call rpm checks within the picked deployment's semaphore (concurrency-safe tpm/rpm checks).
    """

    async def async_filter_deployments(
        self,
        model: str,
        healthy_deployments: List,
        messages: Optional[List[AllMessageValues]],
        request_kwargs: Optional[dict] = None,
        parent_otel_span: Optional[Span] = None,
    ) -> List[dict]:
        return healthy_deployments

    async def async_pre_call_deployment_hook(
        self, kwargs: Dict[str, Any], call_type: Optional[CallTypes]
    ) -> Optional[dict]:
        """
        Allow modifying the request just before it's sent to the deployment.

        Use this instead of 'async_pre_call_hook' when you need to modify the request AFTER a deployment is selected, but BEFORE the request is sent.

        Used in managed_files.py
        """
        pass

    async def async_pre_call_check(
        self, deployment: dict, parent_otel_span: Optional[Span]
    ) -> Optional[dict]:
        pass

    def pre_call_check(self, deployment: dict) -> Optional[dict]:
        pass

    #### Fallback Events - router/proxy only ####
    async def log_model_group_rate_limit_error(
        self, exception: Exception, original_model_group: Optional[str], kwargs: dict
    ):
        pass

    async def log_success_fallback_event(
        self, original_model_group: str, kwargs: dict, original_exception: Exception
    ):
        pass

    async def log_failure_fallback_event(
        self, original_model_group: str, kwargs: dict, original_exception: Exception
    ):
        pass

    #### ADAPTERS #### Allow calling 100+ LLMs in custom format - https://github.com/BerriAI/litellm/pulls

    def translate_completion_input_params(
        self, kwargs
    ) -> Optional[ChatCompletionRequest]:
        """
        Translates the input params, from the provider's native format to the litellm.completion() format.
        """
        pass

    def translate_completion_output_params(
        self, response: ModelResponse
    ) -> Optional[BaseModel]:
        """
        Translates the output params, from the OpenAI format to the custom format.
        """
        pass

    def translate_completion_output_params_streaming(
        self, completion_stream: Any
    ) -> Optional[AdapterCompletionStreamWrapper]:
        """
        Translates the streaming chunk, from the OpenAI format to the custom format.
        """
        pass

    ### DATASET HOOKS #### - currently only used for Argilla

    async def async_dataset_hook(
        self,
        logged_item: ArgillaItem,
        standard_logging_payload: Optional[StandardLoggingPayload],
    ) -> Optional[ArgillaItem]:
        """
        - Decide if the result should be logged to Argilla.
        - Modify the result before logging to Argilla.
        - Return None if the result should not be logged to Argilla.
        """
        raise NotImplementedError("async_dataset_hook not implemented")

    #### CALL HOOKS - proxy only ####
    """
    Control the modify incoming / outgoung data before calling the model
    """

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: Literal[
            "completion",
            "text_completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
            "pass_through_endpoint",
            "rerank",
        ],
    ) -> Optional[
        Union[Exception, str, dict]
    ]:  # raise exception if invalid, return a str for the user to receive - if rejected, or return a modified dictionary for passing into litellm
        pass

    async def async_post_call_failure_hook(
        self,
        request_data: dict,
        original_exception: Exception,
        user_api_key_dict: UserAPIKeyAuth,
        traceback_str: Optional[str] = None,
    ):
        pass

    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        response: LLMResponseTypes,
    ) -> Any:
        pass

    async def async_logging_hook(
        self, kwargs: dict, result: Any, call_type: str
    ) -> Tuple[dict, Any]:
        """For masking logged request/response. Return a modified version of the request/result."""
        return kwargs, result

    def logging_hook(
        self, kwargs: dict, result: Any, call_type: str
    ) -> Tuple[dict, Any]:
        """For masking logged request/response. Return a modified version of the request/result."""
        return kwargs, result

    async def async_moderation_hook(
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        call_type: Literal[
            "completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
            "responses",
        ],
    ) -> Any:
        pass

    async def async_post_call_streaming_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        response: str,
    ) -> Any:
        pass

    async def async_post_call_streaming_iterator_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        response: Any,
        request_data: dict,
    ) -> AsyncGenerator[ModelResponseStream, None]:
        async for item in response:
            yield item

    #### SINGLE-USE #### - https://docs.litellm.ai/docs/observability/custom_callback#using-your-custom-callback-function

    def log_input_event(self, model, messages, kwargs, print_verbose, callback_func):
        try:
            kwargs["model"] = model
            kwargs["messages"] = messages
            kwargs["log_event_type"] = "pre_api_call"
            callback_func(
                kwargs,
            )
            print_verbose(f"Custom Logger - model call details: {kwargs}")
        except Exception:
            print_verbose(f"Custom Logger Error - {traceback.format_exc()}")

    async def async_log_input_event(
        self, model, messages, kwargs, print_verbose, callback_func
    ):
        try:
            kwargs["model"] = model
            kwargs["messages"] = messages
            kwargs["log_event_type"] = "pre_api_call"
            await callback_func(
                kwargs,
            )
            print_verbose(f"Custom Logger - model call details: {kwargs}")
        except Exception:
            print_verbose(f"Custom Logger Error - {traceback.format_exc()}")

    def log_event(
        self, kwargs, response_obj, start_time, end_time, print_verbose, callback_func
    ):
        # Method definition
        try:
            kwargs["log_event_type"] = "post_api_call"
            callback_func(
                kwargs,  # kwargs to func
                response_obj,
                start_time,
                end_time,
            )
        except Exception:
            print_verbose(f"Custom Logger Error - {traceback.format_exc()}")
            pass

    async def async_log_event(
        self, kwargs, response_obj, start_time, end_time, print_verbose, callback_func
    ):
        # Method definition
        try:
            kwargs["log_event_type"] = "post_api_call"
            await callback_func(
                kwargs,  # kwargs to func
                response_obj,
                start_time,
                end_time,
            )
        except Exception:
            print_verbose(f"Custom Logger Error - {traceback.format_exc()}")
            pass

    # Useful helpers for custom logger classes

    def truncate_standard_logging_payload_content(
        self,
        standard_logging_object: StandardLoggingPayload,
    ):
        """
        Truncate error strings and message content in logging payload

        Some loggers like DataDog/ GCS Bucket have a limit on the size of the payload. (1MB)

        This function truncates the error string and the message content if they exceed a certain length.
        """
        MAX_STR_LENGTH = 10_000

        # Truncate fields that might exceed max length
        fields_to_truncate = ["error_str", "messages", "response"]
        for field in fields_to_truncate:
            self._truncate_field(
                standard_logging_object=standard_logging_object,
                field_name=field,
                max_length=MAX_STR_LENGTH,
            )

    def _truncate_field(
        self,
        standard_logging_object: StandardLoggingPayload,
        field_name: str,
        max_length: int,
    ) -> None:
        """
        Helper function to truncate a field in the logging payload

        This converts the field to a string and then truncates it if it exceeds the max length.

        Why convert to string ?
        1. User was sending a poorly formatted list for `messages` field, we could not predict where they would send content
            - Converting to string and then truncating the logged content catches this
        2. We want to avoid modifying the original `messages`, `response`, and `error_str` in the logging payload since these are in kwargs and could be returned to the user
        """
        field_value = standard_logging_object.get(field_name)  # type: ignore
        if field_value:
            str_value = str(field_value)
            if len(str_value) > max_length:
                standard_logging_object[field_name] = self._truncate_text(  # type: ignore
                    text=str_value, max_length=max_length
                )

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text if it exceeds max_length"""
        return (
            text[:max_length]
            + "...truncated by litellm, this logger does not support large content"
            if len(text) > max_length
            else text
        )

# === NexusCore/openenv\Lib\site-packages\nltk\translate\meteor_score.py ===
# Natural Language Toolkit: Machine Translation
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Uday Krishna <udaykrishna5@gmail.com>
# Contributor: Tom Aarsen
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT


from itertools import chain, product
from typing import Callable, Iterable, List, Tuple

from nltk.corpus import WordNetCorpusReader, wordnet
from nltk.stem.api import StemmerI
from nltk.stem.porter import PorterStemmer


def _generate_enums(
    hypothesis: Iterable[str],
    reference: Iterable[str],
    preprocess: Callable[[str], str] = str.lower,
) -> Tuple[List[Tuple[int, str]], List[Tuple[int, str]]]:
    """
    Takes in pre-tokenized inputs for hypothesis and reference and returns
    enumerated word lists for each of them

    :param hypothesis: pre-tokenized hypothesis
    :param reference: pre-tokenized reference
    :preprocess: preprocessing method (default str.lower)
    :return: enumerated words list
    """
    if isinstance(hypothesis, str):
        raise TypeError(
            f'"hypothesis" expects pre-tokenized hypothesis (Iterable[str]): {hypothesis}'
        )

    if isinstance(reference, str):
        raise TypeError(
            f'"reference" expects pre-tokenized reference (Iterable[str]): {reference}'
        )

    enum_hypothesis_list = list(enumerate(map(preprocess, hypothesis)))
    enum_reference_list = list(enumerate(map(preprocess, reference)))
    return enum_hypothesis_list, enum_reference_list


def exact_match(
    hypothesis: Iterable[str], reference: Iterable[str]
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, str]], List[Tuple[int, str]]]:
    """
    matches exact words in hypothesis and reference
    and returns a word mapping based on the enumerated
    word id between hypothesis and reference

    :param hypothesis: pre-tokenized hypothesis
    :param reference: pre-tokenized reference
    :return: enumerated matched tuples, enumerated unmatched hypothesis tuples,
             enumerated unmatched reference tuples
    """
    enum_hypothesis_list, enum_reference_list = _generate_enums(hypothesis, reference)
    return _match_enums(enum_hypothesis_list, enum_reference_list)


def _match_enums(
    enum_hypothesis_list: List[Tuple[int, str]],
    enum_reference_list: List[Tuple[int, str]],
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, str]], List[Tuple[int, str]]]:
    """
    matches exact words in hypothesis and reference and returns
    a word mapping between enum_hypothesis_list and enum_reference_list
    based on the enumerated word id.

    :param enum_hypothesis_list: enumerated hypothesis list
    :param enum_reference_list: enumerated reference list
    :return: enumerated matched tuples, enumerated unmatched hypothesis tuples,
             enumerated unmatched reference tuples
    """
    word_match = []
    for i in range(len(enum_hypothesis_list))[::-1]:
        for j in range(len(enum_reference_list))[::-1]:
            if enum_hypothesis_list[i][1] == enum_reference_list[j][1]:
                word_match.append(
                    (enum_hypothesis_list[i][0], enum_reference_list[j][0])
                )
                enum_hypothesis_list.pop(i)
                enum_reference_list.pop(j)
                break
    return word_match, enum_hypothesis_list, enum_reference_list


def _enum_stem_match(
    enum_hypothesis_list: List[Tuple[int, str]],
    enum_reference_list: List[Tuple[int, str]],
    stemmer: StemmerI = PorterStemmer(),
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, str]], List[Tuple[int, str]]]:
    """
    Stems each word and matches them in hypothesis and reference
    and returns a word mapping between enum_hypothesis_list and
    enum_reference_list based on the enumerated word id. The function also
    returns a enumerated list of unmatched words for hypothesis and reference.

    :param enum_hypothesis_list: enumerated hypothesis list
    :param enum_reference_list: enumerated reference list
    :param stemmer: nltk.stem.api.StemmerI object (default PorterStemmer())
    :return: enumerated matched tuples, enumerated unmatched hypothesis tuples,
             enumerated unmatched reference tuples
    """
    stemmed_enum_hypothesis_list = [
        (word_pair[0], stemmer.stem(word_pair[1])) for word_pair in enum_hypothesis_list
    ]

    stemmed_enum_reference_list = [
        (word_pair[0], stemmer.stem(word_pair[1])) for word_pair in enum_reference_list
    ]

    return _match_enums(stemmed_enum_hypothesis_list, stemmed_enum_reference_list)


def stem_match(
    hypothesis: Iterable[str],
    reference: Iterable[str],
    stemmer: StemmerI = PorterStemmer(),
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, str]], List[Tuple[int, str]]]:
    """
    Stems each word and matches them in hypothesis and reference
    and returns a word mapping between hypothesis and reference

    :param hypothesis: pre-tokenized hypothesis
    :param reference: pre-tokenized reference
    :param stemmer: nltk.stem.api.StemmerI object (default PorterStemmer())
    :return: enumerated matched tuples, enumerated unmatched hypothesis tuples,
             enumerated unmatched reference tuples
    """
    enum_hypothesis_list, enum_reference_list = _generate_enums(hypothesis, reference)
    return _enum_stem_match(enum_hypothesis_list, enum_reference_list, stemmer=stemmer)


def _enum_wordnetsyn_match(
    enum_hypothesis_list: List[Tuple[int, str]],
    enum_reference_list: List[Tuple[int, str]],
    wordnet: WordNetCorpusReader = wordnet,
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, str]], List[Tuple[int, str]]]:
    """
    Matches each word in reference to a word in hypothesis
    if any synonym of a hypothesis word is the exact match
    to the reference word.

    :param enum_hypothesis_list: enumerated hypothesis list
    :param enum_reference_list: enumerated reference list
    :param wordnet: a wordnet corpus reader object (default nltk.corpus.wordnet)
    """
    word_match = []
    for i in range(len(enum_hypothesis_list))[::-1]:
        hypothesis_syns = set(
            chain.from_iterable(
                (
                    lemma.name()
                    for lemma in synset.lemmas()
                    if lemma.name().find("_") < 0
                )
                for synset in wordnet.synsets(enum_hypothesis_list[i][1])
            )
        ).union({enum_hypothesis_list[i][1]})
        for j in range(len(enum_reference_list))[::-1]:
            if enum_reference_list[j][1] in hypothesis_syns:
                word_match.append(
                    (enum_hypothesis_list[i][0], enum_reference_list[j][0])
                )
                enum_hypothesis_list.pop(i)
                enum_reference_list.pop(j)
                break
    return word_match, enum_hypothesis_list, enum_reference_list


def wordnetsyn_match(
    hypothesis: Iterable[str],
    reference: Iterable[str],
    wordnet: WordNetCorpusReader = wordnet,
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, str]], List[Tuple[int, str]]]:
    """
    Matches each word in reference to a word in hypothesis if any synonym
    of a hypothesis word is the exact match to the reference word.

    :param hypothesis: pre-tokenized hypothesis
    :param reference: pre-tokenized reference
    :param wordnet: a wordnet corpus reader object (default nltk.corpus.wordnet)
    :return: list of mapped tuples
    """
    enum_hypothesis_list, enum_reference_list = _generate_enums(hypothesis, reference)
    return _enum_wordnetsyn_match(
        enum_hypothesis_list, enum_reference_list, wordnet=wordnet
    )


def _enum_align_words(
    enum_hypothesis_list: List[Tuple[int, str]],
    enum_reference_list: List[Tuple[int, str]],
    stemmer: StemmerI = PorterStemmer(),
    wordnet: WordNetCorpusReader = wordnet,
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, str]], List[Tuple[int, str]]]:
    """
    Aligns/matches words in the hypothesis to reference by sequentially
    applying exact match, stemmed match and wordnet based synonym match.
    in case there are multiple matches the match which has the least number
    of crossing is chosen. Takes enumerated list as input instead of
    string input

    :param enum_hypothesis_list: enumerated hypothesis list
    :param enum_reference_list: enumerated reference list
    :param stemmer: nltk.stem.api.StemmerI object (default PorterStemmer())
    :param wordnet: a wordnet corpus reader object (default nltk.corpus.wordnet)
    :return: sorted list of matched tuples, unmatched hypothesis list,
             unmatched reference list
    """
    exact_matches, enum_hypothesis_list, enum_reference_list = _match_enums(
        enum_hypothesis_list, enum_reference_list
    )

    stem_matches, enum_hypothesis_list, enum_reference_list = _enum_stem_match(
        enum_hypothesis_list, enum_reference_list, stemmer=stemmer
    )

    wns_matches, enum_hypothesis_list, enum_reference_list = _enum_wordnetsyn_match(
        enum_hypothesis_list, enum_reference_list, wordnet=wordnet
    )

    return (
        sorted(
            exact_matches + stem_matches + wns_matches, key=lambda wordpair: wordpair[0]
        ),
        enum_hypothesis_list,
        enum_reference_list,
    )


def align_words(
    hypothesis: Iterable[str],
    reference: Iterable[str],
    stemmer: StemmerI = PorterStemmer(),
    wordnet: WordNetCorpusReader = wordnet,
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, str]], List[Tuple[int, str]]]:
    """
    Aligns/matches words in the hypothesis to reference by sequentially
    applying exact match, stemmed match and wordnet based synonym match.
    In case there are multiple matches the match which has the least number
    of crossing is chosen.

    :param hypothesis: pre-tokenized hypothesis
    :param reference: pre-tokenized reference
    :param stemmer: nltk.stem.api.StemmerI object (default PorterStemmer())
    :param wordnet: a wordnet corpus reader object (default nltk.corpus.wordnet)
    :return: sorted list of matched tuples, unmatched hypothesis list, unmatched reference list
    """
    enum_hypothesis_list, enum_reference_list = _generate_enums(hypothesis, reference)
    return _enum_align_words(
        enum_hypothesis_list, enum_reference_list, stemmer=stemmer, wordnet=wordnet
    )


def _count_chunks(matches: List[Tuple[int, int]]) -> int:
    """
    Counts the fewest possible number of chunks such that matched unigrams
    of each chunk are adjacent to each other. This is used to calculate the
    fragmentation part of the metric.

    :param matches: list containing a mapping of matched words (output of align_words)
    :return: Number of chunks a sentence is divided into post alignment
    """
    i = 0
    chunks = 1
    while i < len(matches) - 1:
        if (matches[i + 1][0] == matches[i][0] + 1) and (
            matches[i + 1][1] == matches[i][1] + 1
        ):
            i += 1
            continue
        i += 1
        chunks += 1
    return chunks


def single_meteor_score(
    reference: Iterable[str],
    hypothesis: Iterable[str],
    preprocess: Callable[[str], str] = str.lower,
    stemmer: StemmerI = PorterStemmer(),
    wordnet: WordNetCorpusReader = wordnet,
    alpha: float = 0.9,
    beta: float = 3.0,
    gamma: float = 0.5,
) -> float:
    """
    Calculates METEOR score for single hypothesis and reference as per
    "Meteor: An Automatic Metric for MT Evaluation with HighLevels of
    Correlation with Human Judgments" by Alon Lavie and Abhaya Agarwal,
    in Proceedings of ACL.
    https://www.cs.cmu.edu/~alavie/METEOR/pdf/Lavie-Agarwal-2007-METEOR.pdf


    >>> hypothesis1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which', 'ensures', 'that', 'the', 'military', 'always', 'obeys', 'the', 'commands', 'of', 'the', 'party']

    >>> reference1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'that', 'ensures', 'that', 'the', 'military', 'will', 'forever', 'heed', 'Party', 'commands']


    >>> round(single_meteor_score(reference1, hypothesis1),4)
    0.6944

        If there is no words match during the alignment the method returns the
        score as 0. We can safely  return a zero instead of raising a
        division by zero error as no match usually implies a bad translation.

    >>> round(single_meteor_score(['this', 'is', 'a', 'cat'], ['non', 'matching', 'hypothesis']),4)
    0.0

    :param reference: pre-tokenized reference
    :param hypothesis: pre-tokenized hypothesis
    :param preprocess: preprocessing function (default str.lower)
    :param stemmer: nltk.stem.api.StemmerI object (default PorterStemmer())
    :param wordnet: a wordnet corpus reader object (default nltk.corpus.wordnet)
    :param alpha: parameter for controlling relative weights of precision and recall.
    :param beta: parameter for controlling shape of penalty as a
                 function of as a function of fragmentation.
    :param gamma: relative weight assigned to fragmentation penalty.
    :return: The sentence-level METEOR score.
    """
    enum_hypothesis, enum_reference = _generate_enums(
        hypothesis, reference, preprocess=preprocess
    )
    translation_length = len(enum_hypothesis)
    reference_length = len(enum_reference)
    matches, _, _ = _enum_align_words(
        enum_hypothesis, enum_reference, stemmer=stemmer, wordnet=wordnet
    )
    matches_count = len(matches)
    try:
        precision = float(matches_count) / translation_length
        recall = float(matches_count) / reference_length
        fmean = (precision * recall) / (alpha * precision + (1 - alpha) * recall)
        chunk_count = float(_count_chunks(matches))
        frag_frac = chunk_count / matches_count
    except ZeroDivisionError:
        return 0.0
    penalty = gamma * frag_frac**beta
    return (1 - penalty) * fmean


def meteor_score(
    references: Iterable[Iterable[str]],
    hypothesis: Iterable[str],
    preprocess: Callable[[str], str] = str.lower,
    stemmer: StemmerI = PorterStemmer(),
    wordnet: WordNetCorpusReader = wordnet,
    alpha: float = 0.9,
    beta: float = 3.0,
    gamma: float = 0.5,
) -> float:
    """
    Calculates METEOR score for hypothesis with multiple references as
    described in "Meteor: An Automatic Metric for MT Evaluation with
    HighLevels of Correlation with Human Judgments" by Alon Lavie and
    Abhaya Agarwal, in Proceedings of ACL.
    https://www.cs.cmu.edu/~alavie/METEOR/pdf/Lavie-Agarwal-2007-METEOR.pdf


    In case of multiple references the best score is chosen. This method
    iterates over single_meteor_score and picks the best pair among all
    the references for a given hypothesis

    >>> hypothesis1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which', 'ensures', 'that', 'the', 'military', 'always', 'obeys', 'the', 'commands', 'of', 'the', 'party']
    >>> hypothesis2 = ['It', 'is', 'to', 'insure', 'the', 'troops', 'forever', 'hearing', 'the', 'activity', 'guidebook', 'that', 'party', 'direct']

    >>> reference1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'that', 'ensures', 'that', 'the', 'military', 'will', 'forever', 'heed', 'Party', 'commands']
    >>> reference2 = ['It', 'is', 'the', 'guiding', 'principle', 'which', 'guarantees', 'the', 'military', 'forces', 'always', 'being', 'under', 'the', 'command', 'of', 'the', 'Party']
    >>> reference3 = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the', 'army', 'always', 'to', 'heed', 'the', 'directions', 'of', 'the', 'party']

    >>> round(meteor_score([reference1, reference2, reference3], hypothesis1),4)
    0.6944

        If there is no words match during the alignment the method returns the
        score as 0. We can safely  return a zero instead of raising a
        division by zero error as no match usually implies a bad translation.

    >>> round(meteor_score([['this', 'is', 'a', 'cat']], ['non', 'matching', 'hypothesis']),4)
    0.0

    :param references: pre-tokenized reference sentences
    :param hypothesis: a pre-tokenized hypothesis sentence
    :param preprocess: preprocessing function (default str.lower)
    :param stemmer: nltk.stem.api.StemmerI object (default PorterStemmer())
    :param wordnet: a wordnet corpus reader object (default nltk.corpus.wordnet)
    :param alpha: parameter for controlling relative weights of precision and recall.
    :param beta: parameter for controlling shape of penalty as a function
                 of as a function of fragmentation.
    :param gamma: relative weight assigned to fragmentation penalty.
    :return: The sentence-level METEOR score.
    """
    return max(
        single_meteor_score(
            reference,
            hypothesis,
            preprocess=preprocess,
            stemmer=stemmer,
            wordnet=wordnet,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
        )
        for reference in references
    )

# === NexusCore/openenv\Lib\site-packages\openai\types\chat\completion_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, List, Union, Iterable, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from ..shared.chat_model import ChatModel
from ..shared_params.metadata import Metadata
from ..shared.reasoning_effort import ReasoningEffort
from .chat_completion_tool_param import ChatCompletionToolParam
from .chat_completion_audio_param import ChatCompletionAudioParam
from .chat_completion_message_param import ChatCompletionMessageParam
from ..shared_params.function_parameters import FunctionParameters
from ..shared_params.response_format_text import ResponseFormatText
from .chat_completion_stream_options_param import ChatCompletionStreamOptionsParam
from .chat_completion_prediction_content_param import ChatCompletionPredictionContentParam
from .chat_completion_tool_choice_option_param import ChatCompletionToolChoiceOptionParam
from ..shared_params.response_format_json_object import ResponseFormatJSONObject
from ..shared_params.response_format_json_schema import ResponseFormatJSONSchema
from .chat_completion_function_call_option_param import ChatCompletionFunctionCallOptionParam

__all__ = [
    "CompletionCreateParamsBase",
    "FunctionCall",
    "Function",
    "ResponseFormat",
    "WebSearchOptions",
    "WebSearchOptionsUserLocation",
    "WebSearchOptionsUserLocationApproximate",
    "CompletionCreateParamsNonStreaming",
    "CompletionCreateParamsStreaming",
]


class CompletionCreateParamsBase(TypedDict, total=False):
    messages: Required[Iterable[ChatCompletionMessageParam]]
    """A list of messages comprising the conversation so far.

    Depending on the [model](https://platform.openai.com/docs/models) you use,
    different message types (modalities) are supported, like
    [text](https://platform.openai.com/docs/guides/text-generation),
    [images](https://platform.openai.com/docs/guides/vision), and
    [audio](https://platform.openai.com/docs/guides/audio).
    """

    model: Required[Union[str, ChatModel]]
    """Model ID used to generate the response, like `gpt-4o` or `o3`.

    OpenAI offers a wide range of models with different capabilities, performance
    characteristics, and price points. Refer to the
    [model guide](https://platform.openai.com/docs/models) to browse and compare
    available models.
    """

    audio: Optional[ChatCompletionAudioParam]
    """Parameters for audio output.

    Required when audio output is requested with `modalities: ["audio"]`.
    [Learn more](https://platform.openai.com/docs/guides/audio).
    """

    frequency_penalty: Optional[float]
    """Number between -2.0 and 2.0.

    Positive values penalize new tokens based on their existing frequency in the
    text so far, decreasing the model's likelihood to repeat the same line verbatim.
    """

    function_call: FunctionCall
    """Deprecated in favor of `tool_choice`.

    Controls which (if any) function is called by the model.

    `none` means the model will not call a function and instead generates a message.

    `auto` means the model can pick between generating a message or calling a
    function.

    Specifying a particular function via `{"name": "my_function"}` forces the model
    to call that function.

    `none` is the default when no functions are present. `auto` is the default if
    functions are present.
    """

    functions: Iterable[Function]
    """Deprecated in favor of `tools`.

    A list of functions the model may generate JSON inputs for.
    """

    logit_bias: Optional[Dict[str, int]]
    """Modify the likelihood of specified tokens appearing in the completion.

    Accepts a JSON object that maps tokens (specified by their token ID in the
    tokenizer) to an associated bias value from -100 to 100. Mathematically, the
    bias is added to the logits generated by the model prior to sampling. The exact
    effect will vary per model, but values between -1 and 1 should decrease or
    increase likelihood of selection; values like -100 or 100 should result in a ban
    or exclusive selection of the relevant token.
    """

    logprobs: Optional[bool]
    """Whether to return log probabilities of the output tokens or not.

    If true, returns the log probabilities of each output token returned in the
    `content` of `message`.
    """

    max_completion_tokens: Optional[int]
    """
    An upper bound for the number of tokens that can be generated for a completion,
    including visible output tokens and
    [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).
    """

    max_tokens: Optional[int]
    """
    The maximum number of [tokens](/tokenizer) that can be generated in the chat
    completion. This value can be used to control
    [costs](https://openai.com/api/pricing/) for text generated via API.

    This value is now deprecated in favor of `max_completion_tokens`, and is not
    compatible with
    [o-series models](https://platform.openai.com/docs/guides/reasoning).
    """

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    modalities: Optional[List[Literal["text", "audio"]]]
    """
    Output types that you would like the model to generate. Most models are capable
    of generating text, which is the default:

    `["text"]`

    The `gpt-4o-audio-preview` model can also be used to
    [generate audio](https://platform.openai.com/docs/guides/audio). To request that
    this model generate both text and audio responses, you can use:

    `["text", "audio"]`
    """

    n: Optional[int]
    """How many chat completion choices to generate for each input message.

    Note that you will be charged based on the number of generated tokens across all
    of the choices. Keep `n` as `1` to minimize costs.
    """

    parallel_tool_calls: bool
    """
    Whether to enable
    [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
    during tool use.
    """

    prediction: Optional[ChatCompletionPredictionContentParam]
    """
    Static predicted output content, such as the content of a text file that is
    being regenerated.
    """

    presence_penalty: Optional[float]
    """Number between -2.0 and 2.0.

    Positive values penalize new tokens based on whether they appear in the text so
    far, increasing the model's likelihood to talk about new topics.
    """

    reasoning_effort: Optional[ReasoningEffort]
    """**o-series models only**

    Constrains effort on reasoning for
    [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
    supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
    result in faster responses and fewer tokens used on reasoning in a response.
    """

    response_format: ResponseFormat
    """An object specifying the format that the model must output.

    Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
    Outputs which ensures the model will match your supplied JSON schema. Learn more
    in the
    [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

    Setting to `{ "type": "json_object" }` enables the older JSON mode, which
    ensures the message the model generates is valid JSON. Using `json_schema` is
    preferred for models that support it.
    """

    seed: Optional[int]
    """
    This feature is in Beta. If specified, our system will make a best effort to
    sample deterministically, such that repeated requests with the same `seed` and
    parameters should return the same result. Determinism is not guaranteed, and you
    should refer to the `system_fingerprint` response parameter to monitor changes
    in the backend.
    """

    service_tier: Optional[Literal["auto", "default", "flex", "scale"]]
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

    stop: Union[Optional[str], List[str], None]
    """Not supported with latest reasoning models `o3` and `o4-mini`.

    Up to 4 sequences where the API will stop generating further tokens. The
    returned text will not contain the stop sequence.
    """

    store: Optional[bool]
    """
    Whether or not to store the output of this chat completion request for use in
    our [model distillation](https://platform.openai.com/docs/guides/distillation)
    or [evals](https://platform.openai.com/docs/guides/evals) products.
    """

    stream_options: Optional[ChatCompletionStreamOptionsParam]
    """Options for streaming response. Only set this when you set `stream: true`."""

    temperature: Optional[float]
    """What sampling temperature to use, between 0 and 2.

    Higher values like 0.8 will make the output more random, while lower values like
    0.2 will make it more focused and deterministic. We generally recommend altering
    this or `top_p` but not both.
    """

    tool_choice: ChatCompletionToolChoiceOptionParam
    """
    Controls which (if any) tool is called by the model. `none` means the model will
    not call any tool and instead generates a message. `auto` means the model can
    pick between generating a message or calling one or more tools. `required` means
    the model must call one or more tools. Specifying a particular tool via
    `{"type": "function", "function": {"name": "my_function"}}` forces the model to
    call that tool.

    `none` is the default when no tools are present. `auto` is the default if tools
    are present.
    """

    tools: Iterable[ChatCompletionToolParam]
    """A list of tools the model may call.

    Currently, only functions are supported as a tool. Use this to provide a list of
    functions the model may generate JSON inputs for. A max of 128 functions are
    supported.
    """

    top_logprobs: Optional[int]
    """
    An integer between 0 and 20 specifying the number of most likely tokens to
    return at each token position, each with an associated log probability.
    `logprobs` must be set to `true` if this parameter is used.
    """

    top_p: Optional[float]
    """
    An alternative to sampling with temperature, called nucleus sampling, where the
    model considers the results of the tokens with top_p probability mass. So 0.1
    means only the tokens comprising the top 10% probability mass are considered.

    We generally recommend altering this or `temperature` but not both.
    """

    user: str
    """A stable identifier for your end-users.

    Used to boost cache hit rates by better bucketing similar requests and to help
    OpenAI detect and prevent abuse.
    [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).
    """

    web_search_options: WebSearchOptions
    """
    This tool searches the web for relevant results to use in a response. Learn more
    about the
    [web search tool](https://platform.openai.com/docs/guides/tools-web-search?api-mode=chat).
    """


FunctionCall: TypeAlias = Union[Literal["none", "auto"], ChatCompletionFunctionCallOptionParam]


class Function(TypedDict, total=False):
    name: Required[str]
    """The name of the function to be called.

    Must be a-z, A-Z, 0-9, or contain underscores and dashes, with a maximum length
    of 64.
    """

    description: str
    """
    A description of what the function does, used by the model to choose when and
    how to call the function.
    """

    parameters: FunctionParameters
    """The parameters the functions accepts, described as a JSON Schema object.

    See the [guide](https://platform.openai.com/docs/guides/function-calling) for
    examples, and the
    [JSON Schema reference](https://json-schema.org/understanding-json-schema/) for
    documentation about the format.

    Omitting `parameters` defines a function with an empty parameter list.
    """


ResponseFormat: TypeAlias = Union[ResponseFormatText, ResponseFormatJSONSchema, ResponseFormatJSONObject]


class WebSearchOptionsUserLocationApproximate(TypedDict, total=False):
    city: str
    """Free text input for the city of the user, e.g. `San Francisco`."""

    country: str
    """
    The two-letter [ISO country code](https://en.wikipedia.org/wiki/ISO_3166-1) of
    the user, e.g. `US`.
    """

    region: str
    """Free text input for the region of the user, e.g. `California`."""

    timezone: str
    """
    The [IANA timezone](https://timeapi.io/documentation/iana-timezones) of the
    user, e.g. `America/Los_Angeles`.
    """


class WebSearchOptionsUserLocation(TypedDict, total=False):
    approximate: Required[WebSearchOptionsUserLocationApproximate]
    """Approximate location parameters for the search."""

    type: Required[Literal["approximate"]]
    """The type of location approximation. Always `approximate`."""


class WebSearchOptions(TypedDict, total=False):
    search_context_size: Literal["low", "medium", "high"]
    """
    High level guidance for the amount of context window space to use for the
    search. One of `low`, `medium`, or `high`. `medium` is the default.
    """

    user_location: Optional[WebSearchOptionsUserLocation]
    """Approximate location parameters for the search."""


class CompletionCreateParamsNonStreaming(CompletionCreateParamsBase, total=False):
    stream: Optional[Literal[False]]
    """
    If set to true, the model response data will be streamed to the client as it is
    generated using
    [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
    See the
    [Streaming section below](https://platform.openai.com/docs/api-reference/chat/streaming)
    for more information, along with the
    [streaming responses](https://platform.openai.com/docs/guides/streaming-responses)
    guide for more information on how to handle the streaming events.
    """


class CompletionCreateParamsStreaming(CompletionCreateParamsBase):
    stream: Required[Literal[True]]
    """
    If set to true, the model response data will be streamed to the client as it is
    generated using
    [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
    See the
    [Streaming section below](https://platform.openai.com/docs/api-reference/chat/streaming)
    for more information, along with the
    [streaming responses](https://platform.openai.com/docs/guides/streaming-responses)
    guide for more information on how to handle the streaming events.
    """


CompletionCreateParams = Union[CompletionCreateParamsNonStreaming, CompletionCreateParamsStreaming]

# === NexusCore/openenv\Lib\site-packages\jinja2\bccache.py ===
"""The optional bytecode cache system. This is useful if you have very
complex template situations and the compilation of all those templates
slows down your application too much.

Situations where this is useful are often forking web applications that
are initialized on the first request.
"""

import errno
import fnmatch
import marshal
import os
import pickle
import stat
import sys
import tempfile
import typing as t
from hashlib import sha1
from io import BytesIO
from types import CodeType

if t.TYPE_CHECKING:
    import typing_extensions as te

    from .environment import Environment

    class _MemcachedClient(te.Protocol):
        def get(self, key: str) -> bytes: ...

        def set(
            self, key: str, value: bytes, timeout: t.Optional[int] = None
        ) -> None: ...


bc_version = 5
# Magic bytes to identify Jinja bytecode cache files. Contains the
# Python major and minor version to avoid loading incompatible bytecode
# if a project upgrades its Python version.
bc_magic = (
    b"j2"
    + pickle.dumps(bc_version, 2)
    + pickle.dumps((sys.version_info[0] << 24) | sys.version_info[1], 2)
)


class Bucket:
    """Buckets are used to store the bytecode for one template.  It's created
    and initialized by the bytecode cache and passed to the loading functions.

    The buckets get an internal checksum from the cache assigned and use this
    to automatically reject outdated cache material.  Individual bytecode
    cache subclasses don't have to care about cache invalidation.
    """

    def __init__(self, environment: "Environment", key: str, checksum: str) -> None:
        self.environment = environment
        self.key = key
        self.checksum = checksum
        self.reset()

    def reset(self) -> None:
        """Resets the bucket (unloads the bytecode)."""
        self.code: t.Optional[CodeType] = None

    def load_bytecode(self, f: t.BinaryIO) -> None:
        """Loads bytecode from a file or file like object."""
        # make sure the magic header is correct
        magic = f.read(len(bc_magic))
        if magic != bc_magic:
            self.reset()
            return
        # the source code of the file changed, we need to reload
        checksum = pickle.load(f)
        if self.checksum != checksum:
            self.reset()
            return
        # if marshal_load fails then we need to reload
        try:
            self.code = marshal.load(f)
        except (EOFError, ValueError, TypeError):
            self.reset()
            return

    def write_bytecode(self, f: t.IO[bytes]) -> None:
        """Dump the bytecode into the file or file like object passed."""
        if self.code is None:
            raise TypeError("can't write empty bucket")
        f.write(bc_magic)
        pickle.dump(self.checksum, f, 2)
        marshal.dump(self.code, f)

    def bytecode_from_string(self, string: bytes) -> None:
        """Load bytecode from bytes."""
        self.load_bytecode(BytesIO(string))

    def bytecode_to_string(self) -> bytes:
        """Return the bytecode as bytes."""
        out = BytesIO()
        self.write_bytecode(out)
        return out.getvalue()


class BytecodeCache:
    """To implement your own bytecode cache you have to subclass this class
    and override :meth:`load_bytecode` and :meth:`dump_bytecode`.  Both of
    these methods are passed a :class:`~jinja2.bccache.Bucket`.

    A very basic bytecode cache that saves the bytecode on the file system::

        from os import path

        class MyCache(BytecodeCache):

            def __init__(self, directory):
                self.directory = directory

            def load_bytecode(self, bucket):
                filename = path.join(self.directory, bucket.key)
                if path.exists(filename):
                    with open(filename, 'rb') as f:
                        bucket.load_bytecode(f)

            def dump_bytecode(self, bucket):
                filename = path.join(self.directory, bucket.key)
                with open(filename, 'wb') as f:
                    bucket.write_bytecode(f)

    A more advanced version of a filesystem based bytecode cache is part of
    Jinja.
    """

    def load_bytecode(self, bucket: Bucket) -> None:
        """Subclasses have to override this method to load bytecode into a
        bucket.  If they are not able to find code in the cache for the
        bucket, it must not do anything.
        """
        raise NotImplementedError()

    def dump_bytecode(self, bucket: Bucket) -> None:
        """Subclasses have to override this method to write the bytecode
        from a bucket back to the cache.  If it unable to do so it must not
        fail silently but raise an exception.
        """
        raise NotImplementedError()

    def clear(self) -> None:
        """Clears the cache.  This method is not used by Jinja but should be
        implemented to allow applications to clear the bytecode cache used
        by a particular environment.
        """

    def get_cache_key(
        self, name: str, filename: t.Optional[t.Union[str]] = None
    ) -> str:
        """Returns the unique hash key for this template name."""
        hash = sha1(name.encode("utf-8"))

        if filename is not None:
            hash.update(f"|{filename}".encode())

        return hash.hexdigest()

    def get_source_checksum(self, source: str) -> str:
        """Returns a checksum for the source."""
        return sha1(source.encode("utf-8")).hexdigest()

    def get_bucket(
        self,
        environment: "Environment",
        name: str,
        filename: t.Optional[str],
        source: str,
    ) -> Bucket:
        """Return a cache bucket for the given template.  All arguments are
        mandatory but filename may be `None`.
        """
        key = self.get_cache_key(name, filename)
        checksum = self.get_source_checksum(source)
        bucket = Bucket(environment, key, checksum)
        self.load_bytecode(bucket)
        return bucket

    def set_bucket(self, bucket: Bucket) -> None:
        """Put the bucket into the cache."""
        self.dump_bytecode(bucket)


class FileSystemBytecodeCache(BytecodeCache):
    """A bytecode cache that stores bytecode on the filesystem.  It accepts
    two arguments: The directory where the cache items are stored and a
    pattern string that is used to build the filename.

    If no directory is specified a default cache directory is selected.  On
    Windows the user's temp directory is used, on UNIX systems a directory
    is created for the user in the system temp directory.

    The pattern can be used to have multiple separate caches operate on the
    same directory.  The default pattern is ``'__jinja2_%s.cache'``.  ``%s``
    is replaced with the cache key.

    >>> bcc = FileSystemBytecodeCache('/tmp/jinja_cache', '%s.cache')

    This bytecode cache supports clearing of the cache using the clear method.
    """

    def __init__(
        self, directory: t.Optional[str] = None, pattern: str = "__jinja2_%s.cache"
    ) -> None:
        if directory is None:
            directory = self._get_default_cache_dir()
        self.directory = directory
        self.pattern = pattern

    def _get_default_cache_dir(self) -> str:
        def _unsafe_dir() -> "te.NoReturn":
            raise RuntimeError(
                "Cannot determine safe temp directory.  You "
                "need to explicitly provide one."
            )

        tmpdir = tempfile.gettempdir()

        # On windows the temporary directory is used specific unless
        # explicitly forced otherwise.  We can just use that.
        if os.name == "nt":
            return tmpdir
        if not hasattr(os, "getuid"):
            _unsafe_dir()

        dirname = f"_jinja2-cache-{os.getuid()}"
        actual_dir = os.path.join(tmpdir, dirname)

        try:
            os.mkdir(actual_dir, stat.S_IRWXU)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        try:
            os.chmod(actual_dir, stat.S_IRWXU)
            actual_dir_stat = os.lstat(actual_dir)
            if (
                actual_dir_stat.st_uid != os.getuid()
                or not stat.S_ISDIR(actual_dir_stat.st_mode)
                or stat.S_IMODE(actual_dir_stat.st_mode) != stat.S_IRWXU
            ):
                _unsafe_dir()
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        actual_dir_stat = os.lstat(actual_dir)
        if (
            actual_dir_stat.st_uid != os.getuid()
            or not stat.S_ISDIR(actual_dir_stat.st_mode)
            or stat.S_IMODE(actual_dir_stat.st_mode) != stat.S_IRWXU
        ):
            _unsafe_dir()

        return actual_dir

    def _get_cache_filename(self, bucket: Bucket) -> str:
        return os.path.join(self.directory, self.pattern % (bucket.key,))

    def load_bytecode(self, bucket: Bucket) -> None:
        filename = self._get_cache_filename(bucket)

        # Don't test for existence before opening the file, since the
        # file could disappear after the test before the open.
        try:
            f = open(filename, "rb")
        except (FileNotFoundError, IsADirectoryError, PermissionError):
            # PermissionError can occur on Windows when an operation is
            # in progress, such as calling clear().
            return

        with f:
            bucket.load_bytecode(f)

    def dump_bytecode(self, bucket: Bucket) -> None:
        # Write to a temporary file, then rename to the real name after
        # writing. This avoids another process reading the file before
        # it is fully written.
        name = self._get_cache_filename(bucket)
        f = tempfile.NamedTemporaryFile(
            mode="wb",
            dir=os.path.dirname(name),
            prefix=os.path.basename(name),
            suffix=".tmp",
            delete=False,
        )

        def remove_silent() -> None:
            try:
                os.remove(f.name)
            except OSError:
                # Another process may have called clear(). On Windows,
                # another program may be holding the file open.
                pass

        try:
            with f:
                bucket.write_bytecode(f)
        except BaseException:
            remove_silent()
            raise

        try:
            os.replace(f.name, name)
        except OSError:
            # Another process may have called clear(). On Windows,
            # another program may be holding the file open.
            remove_silent()
        except BaseException:
            remove_silent()
            raise

    def clear(self) -> None:
        # imported lazily here because google app-engine doesn't support
        # write access on the file system and the function does not exist
        # normally.
        from os import remove

        files = fnmatch.filter(os.listdir(self.directory), self.pattern % ("*",))
        for filename in files:
            try:
                remove(os.path.join(self.directory, filename))
            except OSError:
                pass


class MemcachedBytecodeCache(BytecodeCache):
    """This class implements a bytecode cache that uses a memcache cache for
    storing the information.  It does not enforce a specific memcache library
    (tummy's memcache or cmemcache) but will accept any class that provides
    the minimal interface required.

    Libraries compatible with this class:

    -   `cachelib <https://github.com/pallets/cachelib>`_
    -   `python-memcached <https://pypi.org/project/python-memcached/>`_

    (Unfortunately the django cache interface is not compatible because it
    does not support storing binary data, only text. You can however pass
    the underlying cache client to the bytecode cache which is available
    as `django.core.cache.cache._client`.)

    The minimal interface for the client passed to the constructor is this:

    .. class:: MinimalClientInterface

        .. method:: set(key, value[, timeout])

            Stores the bytecode in the cache.  `value` is a string and
            `timeout` the timeout of the key.  If timeout is not provided
            a default timeout or no timeout should be assumed, if it's
            provided it's an integer with the number of seconds the cache
            item should exist.

        .. method:: get(key)

            Returns the value for the cache key.  If the item does not
            exist in the cache the return value must be `None`.

    The other arguments to the constructor are the prefix for all keys that
    is added before the actual cache key and the timeout for the bytecode in
    the cache system.  We recommend a high (or no) timeout.

    This bytecode cache does not support clearing of used items in the cache.
    The clear method is a no-operation function.

    .. versionadded:: 2.7
       Added support for ignoring memcache errors through the
       `ignore_memcache_errors` parameter.
    """

    def __init__(
        self,
        client: "_MemcachedClient",
        prefix: str = "jinja2/bytecode/",
        timeout: t.Optional[int] = None,
        ignore_memcache_errors: bool = True,
    ):
        self.client = client
        self.prefix = prefix
        self.timeout = timeout
        self.ignore_memcache_errors = ignore_memcache_errors

    def load_bytecode(self, bucket: Bucket) -> None:
        try:
            code = self.client.get(self.prefix + bucket.key)
        except Exception:
            if not self.ignore_memcache_errors:
                raise
        else:
            bucket.bytecode_from_string(code)

    def dump_bytecode(self, bucket: Bucket) -> None:
        key = self.prefix + bucket.key
        value = bucket.bytecode_to_string()

        try:
            if self.timeout is not None:
                self.client.set(key, value, self.timeout)
            else:
                self.client.set(key, value)
        except Exception:
            if not self.ignore_memcache_errors:
                raise

# === NexusCore/openenv\Lib\site-packages\jupyter_core\command.py ===
# PYTHON_ARGCOMPLETE_OK
"""The root `jupyter` command.

This does nothing other than dispatch to subcommands or output path info.
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import argparse
import errno
import json
import os
import site
import sys
import sysconfig
from pathlib import Path
from shutil import which
from subprocess import Popen
from typing import Any

from . import paths
from .version import __version__


class JupyterParser(argparse.ArgumentParser):
    """A Jupyter argument parser."""

    @property
    def epilog(self) -> str:
        """Add subcommands to epilog on request

        Avoids searching PATH for subcommands unless help output is requested.
        """
        subcommands: str = " ".join(list_subcommands())
        return f"Available subcommands: {subcommands}"

    @epilog.setter
    def epilog(self, x: Any) -> None:
        """Ignore epilog set in Parser.__init__"""

    def argcomplete(self) -> None:
        """Trigger auto-completion, if enabled"""
        try:
            import argcomplete

            argcomplete.autocomplete(self)
        except ImportError:
            pass


def jupyter_parser() -> JupyterParser:
    """Create a jupyter parser object."""
    parser = JupyterParser(
        description="Jupyter: Interactive Computing",
    )
    group = parser.add_mutually_exclusive_group(required=False)
    # don't use argparse's version action because it prints to stderr on py2
    group.add_argument(
        "--version", action="store_true", help="show the versions of core jupyter packages and exit"
    )
    subcommand_action = group.add_argument(
        "subcommand", type=str, nargs="?", help="the subcommand to launch"
    )
    # For argcomplete, supply all known subcommands
    subcommand_action.completer = lambda *args, **kwargs: list_subcommands()  # type: ignore[attr-defined]  # noqa: ARG005

    group.add_argument("--config-dir", action="store_true", help="show Jupyter config dir")
    group.add_argument("--data-dir", action="store_true", help="show Jupyter data dir")
    group.add_argument("--runtime-dir", action="store_true", help="show Jupyter runtime dir")
    group.add_argument(
        "--paths",
        action="store_true",
        help="show all Jupyter paths. Add --json for machine-readable format.",
    )
    parser.add_argument("--json", action="store_true", help="output paths as machine-readable json")
    parser.add_argument("--debug", action="store_true", help="output debug information about paths")

    return parser


def list_subcommands() -> list[str]:
    """List all jupyter subcommands

    searches PATH for `jupyter-name`

    Returns a list of jupyter's subcommand names, without the `jupyter-` prefix.
    Nested children (e.g. jupyter-sub-subsub) are not included.
    """
    subcommand_tuples = set()
    # construct a set of `('foo', 'bar') from `jupyter-foo-bar`
    for d in _path_with_self():
        try:
            bin_paths = list(Path(d).iterdir())
        except OSError:
            continue
        for path in bin_paths:
            name = path.name
            if name.startswith("jupyter-"):
                if sys.platform.startswith("win"):
                    # remove file-extension on Windows
                    name = path.stem
                subcommand_tuples.add(tuple(name.split("-")[1:]))
    # build a set of subcommand strings, excluding subcommands whose parents are defined
    subcommands = set()
    # Only include `jupyter-foo-bar` if `jupyter-foo` is not already present
    for sub_tup in subcommand_tuples:
        if not any(sub_tup[:i] in subcommand_tuples for i in range(1, len(sub_tup))):
            subcommands.add("-".join(sub_tup))
    return sorted(subcommands)


def _execvp(cmd: str, argv: list[str]) -> None:
    """execvp, except on Windows where it uses Popen

    Python provides execvp on Windows, but its behavior is problematic (Python bug#9148).
    """
    if sys.platform.startswith("win"):
        # PATH is ignored when shell=False,
        # so rely on shutil.which
        cmd_path = which(cmd)
        if cmd_path is None:
            msg = f"{cmd!r} not found"
            raise OSError(msg, errno.ENOENT)
        p = Popen([cmd_path] + argv[1:])  # noqa: S603
        # Don't raise KeyboardInterrupt in the parent process.
        # Set this after spawning, to avoid subprocess inheriting handler.
        import signal

        signal.signal(signal.SIGINT, signal.SIG_IGN)
        p.wait()
        sys.exit(p.returncode)
    else:
        os.execvp(cmd, argv)  # noqa: S606


def _jupyter_abspath(subcommand: str) -> str:
    """This method get the abspath of a specified jupyter-subcommand with no
    changes on ENV.
    """
    # get env PATH with self
    search_path = os.pathsep.join(_path_with_self())
    # get the abs path for the jupyter-<subcommand>
    jupyter_subcommand = f"jupyter-{subcommand}"
    abs_path = which(jupyter_subcommand, path=search_path)
    if abs_path is None:
        msg = f"\nJupyter command `{jupyter_subcommand}` not found."
        raise Exception(msg)

    if not os.access(abs_path, os.X_OK):
        msg = f"\nJupyter command `{jupyter_subcommand}` is not executable."
        raise Exception(msg)

    return abs_path


def _path_with_self() -> list[str]:
    """Put `jupyter`'s dir at the front of PATH

    Ensures that /path/to/jupyter subcommand
    will do /path/to/jupyter-subcommand
    even if /other/jupyter-subcommand is ahead of it on PATH
    """
    path_list = (os.environ.get("PATH") or os.defpath).split(os.pathsep)

    # Insert the "scripts" directory for this Python installation
    # This allows the "jupyter" command to be relocated, while still
    # finding subcommands that have been installed in the default
    # location.
    # We put the scripts directory at the *end* of PATH, so that
    # if the user explicitly overrides a subcommand, that override
    # still takes effect.
    try:
        bindir = sysconfig.get_path("scripts")
    except KeyError:
        # The Python environment does not specify a "scripts" location
        pass
    else:
        path_list.append(bindir)

    scripts = [sys.argv[0]]
    if Path(scripts[0]).is_symlink():
        # include realpath, if `jupyter` is a symlink
        scripts.append(os.path.realpath(scripts[0]))

    for script in scripts:
        bindir = str(Path(script).parent)
        if Path(bindir).is_dir() and os.access(script, os.X_OK):  # only if it's a script
            # ensure executable's dir is on PATH
            # avoids missing subcommands when jupyter is run via absolute path
            path_list.insert(0, bindir)
    return path_list


def _evaluate_argcomplete(parser: JupyterParser) -> list[str]:
    """If argcomplete is enabled, trigger autocomplete or return current words

    If the first word looks like a subcommand, return the current command
    that is attempting to be completed so that the subcommand can evaluate it;
    otherwise auto-complete using the main parser.
    """
    try:
        # traitlets >= 5.8 provides some argcomplete support,
        # use helper methods to jump to argcomplete
        from traitlets.config.argcomplete_config import (
            get_argcomplete_cwords,
            increment_argcomplete_index,
        )

        cwords = get_argcomplete_cwords()
        if cwords and len(cwords) > 1 and not cwords[1].startswith("-"):
            # If first completion word looks like a subcommand,
            # increment word from which to start handling arguments
            increment_argcomplete_index()
            return cwords
        # Otherwise no subcommand, directly autocomplete and exit
        parser.argcomplete()
    except ImportError:
        # traitlets >= 5.8 not available, just try to complete this without
        # worrying about subcommands
        parser.argcomplete()
    msg = "Control flow should not reach end of autocomplete()"
    raise AssertionError(msg)


def main() -> None:
    """The command entry point."""
    parser = jupyter_parser()
    argv = sys.argv
    subcommand = None
    if "_ARGCOMPLETE" in os.environ:
        argv = _evaluate_argcomplete(parser)
        subcommand = argv[1]
    elif len(argv) > 1 and not argv[1].startswith("-"):
        # Don't parse if a subcommand is given
        # Avoids argparse gobbling up args passed to subcommand, such as `-h`.
        subcommand = argv[1]
    else:
        args, opts = parser.parse_known_args()
        subcommand = args.subcommand
        if args.version:
            print("Selected Jupyter core packages...")
            for package in [
                "IPython",
                "ipykernel",
                "ipywidgets",
                "jupyter_client",
                "jupyter_core",
                "jupyter_server",
                "jupyterlab",
                "nbclient",
                "nbconvert",
                "nbformat",
                "notebook",
                "qtconsole",
                "traitlets",
            ]:
                try:
                    if package == "jupyter_core":  # We're already here
                        version = __version__
                    else:
                        mod = __import__(package)
                        version = mod.__version__
                except ImportError:
                    version = "not installed"
                print(f"{package:<17}:", version)
            return
        if args.json and not args.paths:
            sys.exit("--json is only used with --paths")
        if args.debug and not args.paths:
            sys.exit("--debug is only used with --paths")
        if args.debug and args.json:
            sys.exit("--debug cannot be used with --json")
        if args.config_dir:
            print(paths.jupyter_config_dir())
            return
        if args.data_dir:
            print(paths.jupyter_data_dir())
            return
        if args.runtime_dir:
            print(paths.jupyter_runtime_dir())
            return
        if args.paths:
            data = {}
            data["runtime"] = [paths.jupyter_runtime_dir()]
            data["config"] = paths.jupyter_config_path()
            data["data"] = paths.jupyter_path()
            if args.json:
                print(json.dumps(data))
            else:
                if args.debug:
                    env = os.environ

                    if paths.use_platform_dirs():
                        print(
                            "JUPYTER_PLATFORM_DIRS is set to a true value, so we use platformdirs to find platform-specific directories"
                        )
                    else:
                        print(
                            "JUPYTER_PLATFORM_DIRS is set to a false value, or is not set, so we use hardcoded legacy paths for platform-specific directories"
                        )

                    if paths.prefer_environment_over_user():
                        print(
                            "JUPYTER_PREFER_ENV_PATH is set to a true value, or JUPYTER_PREFER_ENV_PATH is not set and we detected a virtual environment, making the environment-level path preferred over the user-level path for data and config"
                        )
                    else:
                        print(
                            "JUPYTER_PREFER_ENV_PATH is set to a false value, or JUPYTER_PREFER_ENV_PATH is not set and we did not detect a virtual environment, making the user-level path preferred over the environment-level path for data and config"
                        )

                    # config path list
                    if env.get("JUPYTER_NO_CONFIG"):
                        print(
                            "JUPYTER_NO_CONFIG is set, making the config path list only a single temporary directory"
                        )
                    else:
                        print(
                            "JUPYTER_NO_CONFIG is not set, so we use the full path list for config"
                        )

                    if env.get("JUPYTER_CONFIG_PATH"):
                        print(
                            f"JUPYTER_CONFIG_PATH is set to '{env.get('JUPYTER_CONFIG_PATH')}', which is prepended to the config path list (unless JUPYTER_NO_CONFIG is set)"
                        )
                    else:
                        print(
                            "JUPYTER_CONFIG_PATH is not set, so we do not prepend anything to the config paths"
                        )

                    if env.get("JUPYTER_CONFIG_DIR"):
                        print(
                            f"JUPYTER_CONFIG_DIR is set to '{env.get('JUPYTER_CONFIG_DIR')}', overriding the default user-level config directory"
                        )
                    else:
                        print(
                            "JUPYTER_CONFIG_DIR is not set, so we use the default user-level config directory"
                        )

                    if site.ENABLE_USER_SITE:
                        print(
                            f"Python's site.ENABLE_USER_SITE is True, so we add the user site directory '{site.getuserbase()}'"
                        )
                    else:
                        print(
                            f"Python's site.ENABLE_USER_SITE is not True, so we do not add the Python site user directory '{site.getuserbase()}'"
                        )

                    # data path list
                    if env.get("JUPYTER_PATH"):
                        print(
                            f"JUPYTER_PATH is set to '{env.get('JUPYTER_PATH')}', which is prepended to the data paths"
                        )
                    else:
                        print(
                            "JUPYTER_PATH is not set, so we do not prepend anything to the data paths"
                        )

                    if env.get("JUPYTER_DATA_DIR"):
                        print(
                            f"JUPYTER_DATA_DIR is set to '{env.get('JUPYTER_DATA_DIR')}', overriding the default user-level data directory"
                        )
                    else:
                        print(
                            "JUPYTER_DATA_DIR is not set, so we use the default user-level data directory"
                        )

                    # runtime directory
                    if env.get("JUPYTER_RUNTIME_DIR"):
                        print(
                            f"JUPYTER_RUNTIME_DIR is set to '{env.get('JUPYTER_RUNTIME_DIR')}', overriding the default runtime directory"
                        )
                    else:
                        print(
                            "JUPYTER_RUNTIME_DIR is not set, so we use the default runtime directory"
                        )

                    print()

                for name in sorted(data):
                    path = data[name]
                    print(f"{name}:")
                    for p in path:
                        print("    " + p)
            return

    if not subcommand:
        parser.print_help(file=sys.stderr)
        sys.exit("\nPlease specify a subcommand or one of the optional arguments.")

    try:
        command = _jupyter_abspath(subcommand)
    except Exception as e:
        parser.print_help(file=sys.stderr)
        # special-case alias of "jupyter help" to "jupyter --help"
        if subcommand == "help":
            return
        sys.exit(str(e))

    try:
        _execvp(command, [command] + argv[2:])
    except OSError as e:
        sys.exit(f"Error executing Jupyter command {subcommand!r}: {e}")


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\google\protobuf\internal\type_checkers.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Provides type checking routines.

This module defines type checking utilities in the forms of dictionaries:

VALUE_CHECKERS: A dictionary of field types and a value validation object.
TYPE_TO_BYTE_SIZE_FN: A dictionary with field types and a size computing
  function.
TYPE_TO_SERIALIZE_METHOD: A dictionary with field types and serialization
  function.
FIELD_TYPE_TO_WIRE_TYPE: A dictionary with field typed and their
  corresponding wire types.
TYPE_TO_DESERIALIZE_METHOD: A dictionary with field types and deserialization
  function.
"""

__author__ = 'robinson@google.com (Will Robinson)'

import ctypes
import numbers

from google.protobuf.internal import decoder
from google.protobuf.internal import encoder
from google.protobuf.internal import wire_format
from google.protobuf import descriptor

_FieldDescriptor = descriptor.FieldDescriptor


def TruncateToFourByteFloat(original):
  return ctypes.c_float(original).value


def ToShortestFloat(original):
  """Returns the shortest float that has same value in wire."""
  # All 4 byte floats have between 6 and 9 significant digits, so we
  # start with 6 as the lower bound.
  # It has to be iterative because use '.9g' directly can not get rid
  # of the noises for most values. For example if set a float_field=0.9
  # use '.9g' will print 0.899999976.
  precision = 6
  rounded = float('{0:.{1}g}'.format(original, precision))
  while TruncateToFourByteFloat(rounded) != original:
    precision += 1
    rounded = float('{0:.{1}g}'.format(original, precision))
  return rounded


def GetTypeChecker(field):
  """Returns a type checker for a message field of the specified types.

  Args:
    field: FieldDescriptor object for this field.

  Returns:
    An instance of TypeChecker which can be used to verify the types
    of values assigned to a field of the specified type.
  """
  if (field.cpp_type == _FieldDescriptor.CPPTYPE_STRING and
      field.type == _FieldDescriptor.TYPE_STRING):
    return UnicodeValueChecker()
  if field.cpp_type == _FieldDescriptor.CPPTYPE_ENUM:
    if field.enum_type.is_closed:
      return EnumValueChecker(field.enum_type)
    else:
      # When open enums are supported, any int32 can be assigned.
      return _VALUE_CHECKERS[_FieldDescriptor.CPPTYPE_INT32]
  return _VALUE_CHECKERS[field.cpp_type]


# None of the typecheckers below make any attempt to guard against people
# subclassing builtin types and doing weird things.  We're not trying to
# protect against malicious clients here, just people accidentally shooting
# themselves in the foot in obvious ways.
class TypeChecker(object):

  """Type checker used to catch type errors as early as possible
  when the client is setting scalar fields in protocol messages.
  """

  def __init__(self, *acceptable_types):
    self._acceptable_types = acceptable_types

  def CheckValue(self, proposed_value):
    """Type check the provided value and return it.

    The returned value might have been normalized to another type.
    """
    if not isinstance(proposed_value, self._acceptable_types):
      message = ('%.1024r has type %s, but expected one of: %s' %
                 (proposed_value, type(proposed_value), self._acceptable_types))
      raise TypeError(message)
    return proposed_value


class TypeCheckerWithDefault(TypeChecker):

  def __init__(self, default_value, *acceptable_types):
    TypeChecker.__init__(self, *acceptable_types)
    self._default_value = default_value

  def DefaultValue(self):
    return self._default_value


class BoolValueChecker(object):
  """Type checker used for bool fields."""

  def CheckValue(self, proposed_value):
    if not hasattr(proposed_value, '__index__') or (
        type(proposed_value).__module__ == 'numpy' and
        type(proposed_value).__name__ == 'ndarray'):
      message = ('%.1024r has type %s, but expected one of: %s' %
                 (proposed_value, type(proposed_value), (bool, int)))
      raise TypeError(message)
    return bool(proposed_value)

  def DefaultValue(self):
    return False


# IntValueChecker and its subclasses perform integer type-checks
# and bounds-checks.
class IntValueChecker(object):

  """Checker used for integer fields.  Performs type-check and range check."""

  def CheckValue(self, proposed_value):
    if not hasattr(proposed_value, '__index__') or (
        type(proposed_value).__module__ == 'numpy' and
        type(proposed_value).__name__ == 'ndarray'):
      message = ('%.1024r has type %s, but expected one of: %s' %
                 (proposed_value, type(proposed_value), (int,)))
      raise TypeError(message)

    if not self._MIN <= int(proposed_value) <= self._MAX:
      raise ValueError('Value out of range: %d' % proposed_value)
    # We force all values to int to make alternate implementations where the
    # distinction is more significant (e.g. the C++ implementation) simpler.
    proposed_value = int(proposed_value)
    return proposed_value

  def DefaultValue(self):
    return 0


class EnumValueChecker(object):

  """Checker used for enum fields.  Performs type-check and range check."""

  def __init__(self, enum_type):
    self._enum_type = enum_type

  def CheckValue(self, proposed_value):
    if not isinstance(proposed_value, numbers.Integral):
      message = ('%.1024r has type %s, but expected one of: %s' %
                 (proposed_value, type(proposed_value), (int,)))
      raise TypeError(message)
    if int(proposed_value) not in self._enum_type.values_by_number:
      raise ValueError('Unknown enum value: %d' % proposed_value)
    return proposed_value

  def DefaultValue(self):
    return self._enum_type.values[0].number


class UnicodeValueChecker(object):

  """Checker used for string fields.

  Always returns a unicode value, even if the input is of type str.
  """

  def CheckValue(self, proposed_value):
    if not isinstance(proposed_value, (bytes, str)):
      message = ('%.1024r has type %s, but expected one of: %s' %
                 (proposed_value, type(proposed_value), (bytes, str)))
      raise TypeError(message)

    # If the value is of type 'bytes' make sure that it is valid UTF-8 data.
    if isinstance(proposed_value, bytes):
      try:
        proposed_value = proposed_value.decode('utf-8')
      except UnicodeDecodeError:
        raise ValueError('%.1024r has type bytes, but isn\'t valid UTF-8 '
                         'encoding. Non-UTF-8 strings must be converted to '
                         'unicode objects before being added.' %
                         (proposed_value))
    else:
      try:
        proposed_value.encode('utf8')
      except UnicodeEncodeError:
        raise ValueError('%.1024r isn\'t a valid unicode string and '
                         'can\'t be encoded in UTF-8.'%
                         (proposed_value))

    return proposed_value

  def DefaultValue(self):
    return u""


class Int32ValueChecker(IntValueChecker):
  # We're sure to use ints instead of longs here since comparison may be more
  # efficient.
  _MIN = -2147483648
  _MAX = 2147483647


class Uint32ValueChecker(IntValueChecker):
  _MIN = 0
  _MAX = (1 << 32) - 1


class Int64ValueChecker(IntValueChecker):
  _MIN = -(1 << 63)
  _MAX = (1 << 63) - 1


class Uint64ValueChecker(IntValueChecker):
  _MIN = 0
  _MAX = (1 << 64) - 1


# The max 4 bytes float is about 3.4028234663852886e+38
_FLOAT_MAX = float.fromhex('0x1.fffffep+127')
_FLOAT_MIN = -_FLOAT_MAX
_INF = float('inf')
_NEG_INF = float('-inf')


class DoubleValueChecker(object):
  """Checker used for double fields.

  Performs type-check and range check.
  """

  def CheckValue(self, proposed_value):
    """Check and convert proposed_value to float."""
    if (not hasattr(proposed_value, '__float__') and
        not hasattr(proposed_value, '__index__')) or (
            type(proposed_value).__module__ == 'numpy' and
            type(proposed_value).__name__ == 'ndarray'):
      message = ('%.1024r has type %s, but expected one of: int, float' %
                 (proposed_value, type(proposed_value)))
      raise TypeError(message)
    return float(proposed_value)

  def DefaultValue(self):
    return 0.0


class FloatValueChecker(DoubleValueChecker):
  """Checker used for float fields.

  Performs type-check and range check.

  Values exceeding a 32-bit float will be converted to inf/-inf.
  """

  def CheckValue(self, proposed_value):
    """Check and convert proposed_value to float."""
    converted_value = super().CheckValue(proposed_value)
    # This inf rounding matches the C++ proto SafeDoubleToFloat logic.
    if converted_value > _FLOAT_MAX:
      return _INF
    if converted_value < _FLOAT_MIN:
      return _NEG_INF

    return TruncateToFourByteFloat(converted_value)

# Type-checkers for all scalar CPPTYPEs.
_VALUE_CHECKERS = {
    _FieldDescriptor.CPPTYPE_INT32: Int32ValueChecker(),
    _FieldDescriptor.CPPTYPE_INT64: Int64ValueChecker(),
    _FieldDescriptor.CPPTYPE_UINT32: Uint32ValueChecker(),
    _FieldDescriptor.CPPTYPE_UINT64: Uint64ValueChecker(),
    _FieldDescriptor.CPPTYPE_DOUBLE: DoubleValueChecker(),
    _FieldDescriptor.CPPTYPE_FLOAT: FloatValueChecker(),
    _FieldDescriptor.CPPTYPE_BOOL: BoolValueChecker(),
    _FieldDescriptor.CPPTYPE_STRING: TypeCheckerWithDefault(b'', bytes),
}


# Map from field type to a function F, such that F(field_num, value)
# gives the total byte size for a value of the given type.  This
# byte size includes tag information and any other additional space
# associated with serializing "value".
TYPE_TO_BYTE_SIZE_FN = {
    _FieldDescriptor.TYPE_DOUBLE: wire_format.DoubleByteSize,
    _FieldDescriptor.TYPE_FLOAT: wire_format.FloatByteSize,
    _FieldDescriptor.TYPE_INT64: wire_format.Int64ByteSize,
    _FieldDescriptor.TYPE_UINT64: wire_format.UInt64ByteSize,
    _FieldDescriptor.TYPE_INT32: wire_format.Int32ByteSize,
    _FieldDescriptor.TYPE_FIXED64: wire_format.Fixed64ByteSize,
    _FieldDescriptor.TYPE_FIXED32: wire_format.Fixed32ByteSize,
    _FieldDescriptor.TYPE_BOOL: wire_format.BoolByteSize,
    _FieldDescriptor.TYPE_STRING: wire_format.StringByteSize,
    _FieldDescriptor.TYPE_GROUP: wire_format.GroupByteSize,
    _FieldDescriptor.TYPE_MESSAGE: wire_format.MessageByteSize,
    _FieldDescriptor.TYPE_BYTES: wire_format.BytesByteSize,
    _FieldDescriptor.TYPE_UINT32: wire_format.UInt32ByteSize,
    _FieldDescriptor.TYPE_ENUM: wire_format.EnumByteSize,
    _FieldDescriptor.TYPE_SFIXED32: wire_format.SFixed32ByteSize,
    _FieldDescriptor.TYPE_SFIXED64: wire_format.SFixed64ByteSize,
    _FieldDescriptor.TYPE_SINT32: wire_format.SInt32ByteSize,
    _FieldDescriptor.TYPE_SINT64: wire_format.SInt64ByteSize
    }


# Maps from field types to encoder constructors.
TYPE_TO_ENCODER = {
    _FieldDescriptor.TYPE_DOUBLE: encoder.DoubleEncoder,
    _FieldDescriptor.TYPE_FLOAT: encoder.FloatEncoder,
    _FieldDescriptor.TYPE_INT64: encoder.Int64Encoder,
    _FieldDescriptor.TYPE_UINT64: encoder.UInt64Encoder,
    _FieldDescriptor.TYPE_INT32: encoder.Int32Encoder,
    _FieldDescriptor.TYPE_FIXED64: encoder.Fixed64Encoder,
    _FieldDescriptor.TYPE_FIXED32: encoder.Fixed32Encoder,
    _FieldDescriptor.TYPE_BOOL: encoder.BoolEncoder,
    _FieldDescriptor.TYPE_STRING: encoder.StringEncoder,
    _FieldDescriptor.TYPE_GROUP: encoder.GroupEncoder,
    _FieldDescriptor.TYPE_MESSAGE: encoder.MessageEncoder,
    _FieldDescriptor.TYPE_BYTES: encoder.BytesEncoder,
    _FieldDescriptor.TYPE_UINT32: encoder.UInt32Encoder,
    _FieldDescriptor.TYPE_ENUM: encoder.EnumEncoder,
    _FieldDescriptor.TYPE_SFIXED32: encoder.SFixed32Encoder,
    _FieldDescriptor.TYPE_SFIXED64: encoder.SFixed64Encoder,
    _FieldDescriptor.TYPE_SINT32: encoder.SInt32Encoder,
    _FieldDescriptor.TYPE_SINT64: encoder.SInt64Encoder,
    }


# Maps from field types to sizer constructors.
TYPE_TO_SIZER = {
    _FieldDescriptor.TYPE_DOUBLE: encoder.DoubleSizer,
    _FieldDescriptor.TYPE_FLOAT: encoder.FloatSizer,
    _FieldDescriptor.TYPE_INT64: encoder.Int64Sizer,
    _FieldDescriptor.TYPE_UINT64: encoder.UInt64Sizer,
    _FieldDescriptor.TYPE_INT32: encoder.Int32Sizer,
    _FieldDescriptor.TYPE_FIXED64: encoder.Fixed64Sizer,
    _FieldDescriptor.TYPE_FIXED32: encoder.Fixed32Sizer,
    _FieldDescriptor.TYPE_BOOL: encoder.BoolSizer,
    _FieldDescriptor.TYPE_STRING: encoder.StringSizer,
    _FieldDescriptor.TYPE_GROUP: encoder.GroupSizer,
    _FieldDescriptor.TYPE_MESSAGE: encoder.MessageSizer,
    _FieldDescriptor.TYPE_BYTES: encoder.BytesSizer,
    _FieldDescriptor.TYPE_UINT32: encoder.UInt32Sizer,
    _FieldDescriptor.TYPE_ENUM: encoder.EnumSizer,
    _FieldDescriptor.TYPE_SFIXED32: encoder.SFixed32Sizer,
    _FieldDescriptor.TYPE_SFIXED64: encoder.SFixed64Sizer,
    _FieldDescriptor.TYPE_SINT32: encoder.SInt32Sizer,
    _FieldDescriptor.TYPE_SINT64: encoder.SInt64Sizer,
    }


# Maps from field type to a decoder constructor.
TYPE_TO_DECODER = {
    _FieldDescriptor.TYPE_DOUBLE: decoder.DoubleDecoder,
    _FieldDescriptor.TYPE_FLOAT: decoder.FloatDecoder,
    _FieldDescriptor.TYPE_INT64: decoder.Int64Decoder,
    _FieldDescriptor.TYPE_UINT64: decoder.UInt64Decoder,
    _FieldDescriptor.TYPE_INT32: decoder.Int32Decoder,
    _FieldDescriptor.TYPE_FIXED64: decoder.Fixed64Decoder,
    _FieldDescriptor.TYPE_FIXED32: decoder.Fixed32Decoder,
    _FieldDescriptor.TYPE_BOOL: decoder.BoolDecoder,
    _FieldDescriptor.TYPE_STRING: decoder.StringDecoder,
    _FieldDescriptor.TYPE_GROUP: decoder.GroupDecoder,
    _FieldDescriptor.TYPE_MESSAGE: decoder.MessageDecoder,
    _FieldDescriptor.TYPE_BYTES: decoder.BytesDecoder,
    _FieldDescriptor.TYPE_UINT32: decoder.UInt32Decoder,
    _FieldDescriptor.TYPE_ENUM: decoder.EnumDecoder,
    _FieldDescriptor.TYPE_SFIXED32: decoder.SFixed32Decoder,
    _FieldDescriptor.TYPE_SFIXED64: decoder.SFixed64Decoder,
    _FieldDescriptor.TYPE_SINT32: decoder.SInt32Decoder,
    _FieldDescriptor.TYPE_SINT64: decoder.SInt64Decoder,
    }

# Maps from field type to expected wiretype.
FIELD_TYPE_TO_WIRE_TYPE = {
    _FieldDescriptor.TYPE_DOUBLE: wire_format.WIRETYPE_FIXED64,
    _FieldDescriptor.TYPE_FLOAT: wire_format.WIRETYPE_FIXED32,
    _FieldDescriptor.TYPE_INT64: wire_format.WIRETYPE_VARINT,
    _FieldDescriptor.TYPE_UINT64: wire_format.WIRETYPE_VARINT,
    _FieldDescriptor.TYPE_INT32: wire_format.WIRETYPE_VARINT,
    _FieldDescriptor.TYPE_FIXED64: wire_format.WIRETYPE_FIXED64,
    _FieldDescriptor.TYPE_FIXED32: wire_format.WIRETYPE_FIXED32,
    _FieldDescriptor.TYPE_BOOL: wire_format.WIRETYPE_VARINT,
    _FieldDescriptor.TYPE_STRING:
      wire_format.WIRETYPE_LENGTH_DELIMITED,
    _FieldDescriptor.TYPE_GROUP: wire_format.WIRETYPE_START_GROUP,
    _FieldDescriptor.TYPE_MESSAGE:
      wire_format.WIRETYPE_LENGTH_DELIMITED,
    _FieldDescriptor.TYPE_BYTES:
      wire_format.WIRETYPE_LENGTH_DELIMITED,
    _FieldDescriptor.TYPE_UINT32: wire_format.WIRETYPE_VARINT,
    _FieldDescriptor.TYPE_ENUM: wire_format.WIRETYPE_VARINT,
    _FieldDescriptor.TYPE_SFIXED32: wire_format.WIRETYPE_FIXED32,
    _FieldDescriptor.TYPE_SFIXED64: wire_format.WIRETYPE_FIXED64,
    _FieldDescriptor.TYPE_SINT32: wire_format.WIRETYPE_VARINT,
    _FieldDescriptor.TYPE_SINT64: wire_format.WIRETYPE_VARINT,
    }

# === NexusCore/openenv\Lib\site-packages\tiktoken\core.py ===
from __future__ import annotations

import functools
from concurrent.futures import ThreadPoolExecutor
from typing import AbstractSet, Collection, Literal, NoReturn, Optional, Union

import regex

from tiktoken import _tiktoken


class Encoding:
    def __init__(
        self,
        name: str,
        *,
        pat_str: str,
        mergeable_ranks: dict[bytes, int],
        special_tokens: dict[str, int],
        explicit_n_vocab: Optional[int] = None,
    ):
        """Creates an Encoding object.

        See openai_public.py for examples of how to construct an Encoding object.

        Args:
            name: The name of the encoding. It should be clear from the name of the encoding
                what behaviour to expect, in particular, encodings with different special tokens
                should have different names.
            pat_str: A regex pattern string that is used to split the input text.
            mergeable_ranks: A dictionary mapping mergeable token bytes to their ranks. The ranks
                must correspond to merge priority.
            special_tokens: A dictionary mapping special token strings to their token values.
            explicit_n_vocab: The number of tokens in the vocabulary. If provided, it is checked
                that the number of mergeable tokens and special tokens is equal to this number.
        """
        self.name = name

        self._pat_str = pat_str
        self._mergeable_ranks = mergeable_ranks
        self._special_tokens = special_tokens

        self.max_token_value = max(
            max(mergeable_ranks.values()), max(special_tokens.values(), default=0)
        )
        if explicit_n_vocab:
            assert len(mergeable_ranks) + len(special_tokens) == explicit_n_vocab
            assert self.max_token_value == explicit_n_vocab - 1

        self._core_bpe = _tiktoken.CoreBPE(mergeable_ranks, special_tokens, pat_str)

    def __repr__(self) -> str:
        return f"<Encoding {self.name!r}>"

    # ====================
    # Encoding
    # ====================

    def encode_ordinary(self, text: str) -> list[int]:
        """Encodes a string into tokens, ignoring special tokens.

        This is equivalent to `encode(text, disallowed_special=())` (but slightly faster).

        ```
        >>> enc.encode_ordinary("hello world")
        [31373, 995]
        """
        try:
            return self._core_bpe.encode_ordinary(text)
        except UnicodeEncodeError:
            # See comment in encode
            text = text.encode("utf-16", "surrogatepass").decode("utf-16", "replace")
            return self._core_bpe.encode_ordinary(text)

    def encode(
        self,
        text: str,
        *,
        allowed_special: Union[Literal["all"], AbstractSet[str]] = set(),  # noqa: B006
        disallowed_special: Union[Literal["all"], Collection[str]] = "all",
    ) -> list[int]:
        """Encodes a string into tokens.

        Special tokens are artificial tokens used to unlock capabilities from a model,
        such as fill-in-the-middle. So we want to be careful about accidentally encoding special
        tokens, since they can be used to trick a model into doing something we don't want it to do.

        Hence, by default, encode will raise an error if it encounters text that corresponds
        to a special token. This can be controlled on a per-token level using the `allowed_special`
        and `disallowed_special` parameters. In particular:
        - Setting `disallowed_special` to () will prevent this function from raising errors and
          cause all text corresponding to special tokens to be encoded as natural text.
        - Setting `allowed_special` to "all" will cause this function to treat all text
          corresponding to special tokens to be encoded as special tokens.

        ```
        >>> enc.encode("hello world")
        [31373, 995]
        >>> enc.encode("<|endoftext|>", allowed_special={"<|endoftext|>"})
        [50256]
        >>> enc.encode("<|endoftext|>", allowed_special="all")
        [50256]
        >>> enc.encode("<|endoftext|>")
        # Raises ValueError
        >>> enc.encode("<|endoftext|>", disallowed_special=())
        [27, 91, 437, 1659, 5239, 91, 29]
        ```
        """
        if allowed_special == "all":
            allowed_special = self.special_tokens_set
        if disallowed_special == "all":
            disallowed_special = self.special_tokens_set - allowed_special
        if disallowed_special:
            if not isinstance(disallowed_special, frozenset):
                disallowed_special = frozenset(disallowed_special)
            if match := _special_token_regex(disallowed_special).search(text):
                raise_disallowed_special_token(match.group())

        # https://github.com/PyO3/pyo3/pull/3632
        if isinstance(allowed_special, frozenset):
            allowed_special = set(allowed_special)

        try:
            return self._core_bpe.encode(text, allowed_special)
        except UnicodeEncodeError:
            # BPE operates on bytes, but the regex operates on unicode. If we pass a str that is
            # invalid UTF-8 to Rust, it will rightfully complain. Here we do a quick and dirty
            # fixup for any surrogate pairs that may have sneaked their way into the text.
            # Technically, this introduces a place where encode + decode doesn't roundtrip a Python
            # string, but given that this is input we want to support, maybe that's okay.
            # Also we use errors="replace" to handle weird things like lone surrogates.
            text = text.encode("utf-16", "surrogatepass").decode("utf-16", "replace")
            return self._core_bpe.encode(text, allowed_special)

    def encode_ordinary_batch(self, text: list[str], *, num_threads: int = 8) -> list[list[int]]:
        """Encodes a list of strings into tokens, in parallel, ignoring special tokens.

        This is equivalent to `encode_batch(text, disallowed_special=())` (but slightly faster).

        ```
        >>> enc.encode_ordinary_batch(["hello world", "goodbye world"])
        [[31373, 995], [11274, 16390, 995]]
        ```
        """
        encoder = functools.partial(self.encode_ordinary)
        with ThreadPoolExecutor(num_threads) as e:
            return list(e.map(encoder, text))

    def encode_batch(
        self,
        text: list[str],
        *,
        num_threads: int = 8,
        allowed_special: Union[Literal["all"], AbstractSet[str]] = set(),  # noqa: B006
        disallowed_special: Union[Literal["all"], Collection[str]] = "all",
    ) -> list[list[int]]:
        """Encodes a list of strings into tokens, in parallel.

        See `encode` for more details on `allowed_special` and `disallowed_special`.

        ```
        >>> enc.encode_batch(["hello world", "goodbye world"])
        [[31373, 995], [11274, 16390, 995]]
        ```
        """
        if allowed_special == "all":
            allowed_special = self.special_tokens_set
        if disallowed_special == "all":
            disallowed_special = self.special_tokens_set - allowed_special
        if not isinstance(disallowed_special, frozenset):
            disallowed_special = frozenset(disallowed_special)

        encoder = functools.partial(
            self.encode, allowed_special=allowed_special, disallowed_special=disallowed_special
        )
        with ThreadPoolExecutor(num_threads) as e:
            return list(e.map(encoder, text))

    def encode_with_unstable(
        self,
        text: str,
        *,
        allowed_special: Union[Literal["all"], AbstractSet[str]] = set(),  # noqa: B006
        disallowed_special: Union[Literal["all"], Collection[str]] = "all",
    ) -> tuple[list[int], list[list[int]]]:
        """Encodes a string into stable tokens and possible completion sequences.

        Note that the stable tokens will only represent a substring of `text`.

        See `encode` for more details on `allowed_special` and `disallowed_special`.

        This API should itself be considered unstable.

        ```
        >>> enc.encode_with_unstable("hello fanta")
        ([31373], [(277, 4910), (5113, 265), ..., (8842,)])

        >>> text = "..."
        >>> stable_tokens, completions = enc.encode_with_unstable(text)
        >>> assert text.encode().startswith(enc.decode_bytes(stable_tokens))
        >>> assert all(enc.decode_bytes(stable_tokens + seq).startswith(text.encode()) for seq in completions)
        ```
        """
        if allowed_special == "all":
            allowed_special = self.special_tokens_set
        if disallowed_special == "all":
            disallowed_special = self.special_tokens_set - allowed_special
        if disallowed_special:
            if not isinstance(disallowed_special, frozenset):
                disallowed_special = frozenset(disallowed_special)
            if match := _special_token_regex(disallowed_special).search(text):
                raise_disallowed_special_token(match.group())

        return self._core_bpe.encode_with_unstable(text, allowed_special)

    def encode_single_token(self, text_or_bytes: Union[str, bytes]) -> int:
        """Encodes text corresponding to a single token to its token value.

        NOTE: this will encode all special tokens.

        Raises `KeyError` if the token is not in the vocabulary.

        ```
        >>> enc.encode_single_token("hello")
        31373
        ```
        """
        if isinstance(text_or_bytes, str):
            text_or_bytes = text_or_bytes.encode("utf-8")
        return self._core_bpe.encode_single_token(text_or_bytes)

    # ====================
    # Decoding
    # ====================

    def decode_bytes(self, tokens: list[int]) -> bytes:
        """Decodes a list of tokens into bytes.

        ```
        >>> enc.decode_bytes([31373, 995])
        b'hello world'
        ```
        """
        return self._core_bpe.decode_bytes(tokens)

    def decode(self, tokens: list[int], errors: str = "replace") -> str:
        """Decodes a list of tokens into a string.

        WARNING: the default behaviour of this function is lossy, since decoded bytes are not
        guaranteed to be valid UTF-8. You can control this behaviour using the `errors` parameter,
        for instance, setting `errors=strict`.

        ```
        >>> enc.decode([31373, 995])
        'hello world'
        ```
        """
        return self._core_bpe.decode_bytes(tokens).decode("utf-8", errors=errors)

    def decode_single_token_bytes(self, token: int) -> bytes:
        """Decodes a token into bytes.

        NOTE: this will decode all special tokens.

        Raises `KeyError` if the token is not in the vocabulary.

        ```
        >>> enc.decode_single_token_bytes(31373)
        b'hello'
        ```
        """
        return self._core_bpe.decode_single_token_bytes(token)

    def decode_tokens_bytes(self, tokens: list[int]) -> list[bytes]:
        """Decodes a list of tokens into a list of bytes.

        Useful for visualising tokenisation.
        >>> enc.decode_tokens_bytes([31373, 995])
        [b'hello', b' world']
        """
        return [self.decode_single_token_bytes(token) for token in tokens]

    def decode_with_offsets(self, tokens: list[int]) -> tuple[str, list[int]]:
        """Decodes a list of tokens into a string and a list of offsets.

        Each offset is the index into text corresponding to the start of each token.
        If UTF-8 character boundaries do not line up with token boundaries, the offset is the index
        of the first character that contains bytes from the token.

        This will currently raise if given tokens that decode to invalid UTF-8; this behaviour may
        change in the future to be more permissive.

        >>> enc.decode_with_offsets([31373, 995])
        ('hello world', [0, 5])
        """
        token_bytes = self.decode_tokens_bytes(tokens)

        text_len = 0
        offsets = []
        for token in token_bytes:
            offsets.append(max(0, text_len - (0x80 <= token[0] < 0xC0)))
            text_len += sum(1 for c in token if not 0x80 <= c < 0xC0)

        # TODO: assess correctness for errors="ignore" and errors="replace"
        text = b"".join(token_bytes).decode("utf-8", errors="strict")
        return text, offsets

    def decode_batch(
        self, batch: list[list[int]], *, errors: str = "replace", num_threads: int = 8
    ) -> list[str]:
        """Decodes a batch (list of lists of tokens) into a list of strings."""
        decoder = functools.partial(self.decode, errors=errors)
        with ThreadPoolExecutor(num_threads) as e:
            return list(e.map(decoder, batch))

    def decode_bytes_batch(self, batch: list[list[int]], *, num_threads: int = 8) -> list[bytes]:
        """Decodes a batch (list of lists of tokens) into a list of bytes."""
        with ThreadPoolExecutor(num_threads) as e:
            return list(e.map(self.decode_bytes, batch))

    # ====================
    # Miscellaneous
    # ====================

    def token_byte_values(self) -> list[bytes]:
        """Returns the list of all token byte values."""
        return self._core_bpe.token_byte_values()

    @property
    def eot_token(self) -> int:
        return self._special_tokens["<|endoftext|>"]

    @functools.cached_property
    def special_tokens_set(self) -> set[str]:
        return set(self._special_tokens.keys())

    @property
    def n_vocab(self) -> int:
        """For backwards compatibility. Prefer to use `enc.max_token_value + 1`."""
        return self.max_token_value + 1

    # ====================
    # Private
    # ====================

    def _encode_single_piece(self, text_or_bytes: Union[str, bytes]) -> list[int]:
        """Encodes text corresponding to bytes without a regex split.

        NOTE: this will not encode any special tokens.

        ```
        >>> enc.encode_single_piece("helloqqqq")
        [31373, 38227, 38227]
        ```
        """
        if isinstance(text_or_bytes, str):
            text_or_bytes = text_or_bytes.encode("utf-8")
        return self._core_bpe.encode_single_piece(text_or_bytes)

    def _encode_only_native_bpe(self, text: str) -> list[int]:
        """Encodes a string into tokens, but do regex splitting in Python."""
        _unused_pat = regex.compile(self._pat_str)
        ret = []
        for piece in regex.findall(_unused_pat, text):
            ret.extend(self._core_bpe.encode_single_piece(piece))
        return ret

    def _encode_bytes(self, text: bytes) -> list[int]:
        return self._core_bpe._encode_bytes(text)

    def __getstate__(self) -> object:
        import tiktoken.registry

        # As an optimisation, pickle registered encodings by reference
        if self is tiktoken.registry.ENCODINGS.get(self.name):
            return self.name
        return {
            "name": self.name,
            "pat_str": self._pat_str,
            "mergeable_ranks": self._mergeable_ranks,
            "special_tokens": self._special_tokens,
        }

    def __setstate__(self, value: object) -> None:
        import tiktoken.registry

        if isinstance(value, str):
            self.__dict__ = tiktoken.registry.get_encoding(value).__dict__
            return
        self.__init__(**value)


@functools.lru_cache(maxsize=128)
def _special_token_regex(tokens: frozenset[str]) -> "regex.Pattern[str]":
    inner = "|".join(regex.escape(token) for token in tokens)
    return regex.compile(f"({inner})")


def raise_disallowed_special_token(token: str) -> NoReturn:
    raise ValueError(
        f"Encountered text corresponding to disallowed special token {token!r}.\n"
        "If you want this text to be encoded as a special token, "
        f"pass it to `allowed_special`, e.g. `allowed_special={{{token!r}, ...}}`.\n"
        f"If you want this text to be encoded as normal text, disable the check for this token "
        f"by passing `disallowed_special=(enc.special_tokens_set - {{{token!r}}})`.\n"
        "To disable this check for all special tokens, pass `disallowed_special=()`.\n"
    )

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_tracing.py ===
from _pydevd_bundle.pydevd_constants import (
    get_frame,
    IS_CPYTHON,
    IS_64BIT_PROCESS,
    IS_WINDOWS,
    IS_LINUX,
    IS_MAC,
    DebugInfoHolder,
    LOAD_NATIVE_LIB_FLAG,
    ENV_FALSE_LOWER_VALUES,
    ForkSafeLock,
    PYDEVD_USE_SYS_MONITORING,
)
from _pydev_bundle._pydev_saved_modules import thread, threading
from _pydev_bundle import pydev_log, pydev_monkey
import os.path
import platform
import ctypes
from io import StringIO
import sys
import traceback

_original_settrace = sys.settrace


class TracingFunctionHolder:
    """This class exists just to keep some variables (so that we don't keep them in the global namespace)."""

    _original_tracing = None
    _warn = True
    _traceback_limit = 1
    _warnings_shown = {}


def get_exception_traceback_str():
    exc_info = sys.exc_info()
    s = StringIO()
    traceback.print_exception(exc_info[0], exc_info[1], exc_info[2], file=s)
    return s.getvalue()


def _get_stack_str(frame):
    msg = (
        "\nIf this is needed, please check: "
        + "\nhttp://pydev.blogspot.com/2007/06/why-cant-pydev-debugger-work-with.html"
        + "\nto see how to restore the debug tracing back correctly.\n"
    )

    if TracingFunctionHolder._traceback_limit:
        s = StringIO()
        s.write("Call Location:\n")
        traceback.print_stack(f=frame, limit=TracingFunctionHolder._traceback_limit, file=s)
        msg = msg + s.getvalue()

    return msg


def _internal_set_trace(tracing_func):
    if PYDEVD_USE_SYS_MONITORING:
        raise RuntimeError("pydevd: Using sys.monitoring, sys.settrace should not be called.")
    if TracingFunctionHolder._warn:
        frame = get_frame()
        if frame is not None and frame.f_back is not None:
            filename = os.path.splitext(frame.f_back.f_code.co_filename.lower())[0]
            if filename.endswith("threadpool") and "gevent" in filename:
                if tracing_func is None:
                    pydev_log.debug("Disabled internal sys.settrace from gevent threadpool.")
                    return

            elif not filename.endswith(
                (
                    "threading",
                    "pydevd_tracing",
                )
            ):
                message = (
                    "\nPYDEV DEBUGGER WARNING:"
                    + "\nsys.settrace() should not be used when the debugger is being used."
                    + "\nThis may cause the debugger to stop working correctly."
                    + "%s" % _get_stack_str(frame.f_back)
                )

                if message not in TracingFunctionHolder._warnings_shown:
                    # only warn about each message once...
                    TracingFunctionHolder._warnings_shown[message] = 1
                    sys.stderr.write("%s\n" % (message,))
                    sys.stderr.flush()

    if TracingFunctionHolder._original_tracing:
        TracingFunctionHolder._original_tracing(tracing_func)


_last_tracing_func_thread_local = threading.local()


def SetTrace(tracing_func):
    if PYDEVD_USE_SYS_MONITORING:
        raise RuntimeError("SetTrace should not be used when using sys.monitoring.")
    _last_tracing_func_thread_local.tracing_func = tracing_func

    if tracing_func is not None:
        if set_trace_to_threads(tracing_func, thread_idents=[thread.get_ident()], create_dummy_thread=False) == 0:
            # If we can use our own tracer instead of the one from sys.settrace, do it (the reason
            # is that this is faster than the Python version because we don't call
            # PyFrame_FastToLocalsWithError and PyFrame_LocalsToFast at each event!
            # (the difference can be huge when checking line events on frames as the
            # time increases based on the number of local variables in the scope)
            # See: InternalCallTrampoline (on the C side) for details.
            return

    # If it didn't work (or if it was None), use the Python version.
    set_trace = TracingFunctionHolder._original_tracing or sys.settrace
    set_trace(tracing_func)


def reapply_settrace():
    try:
        tracing_func = _last_tracing_func_thread_local.tracing_func
    except AttributeError:
        return
    else:
        SetTrace(tracing_func)


def replace_sys_set_trace_func():
    if PYDEVD_USE_SYS_MONITORING:
        return
    if TracingFunctionHolder._original_tracing is None:
        TracingFunctionHolder._original_tracing = sys.settrace
        sys.settrace = _internal_set_trace


def restore_sys_set_trace_func():
    if PYDEVD_USE_SYS_MONITORING:
        return
    if TracingFunctionHolder._original_tracing is not None:
        sys.settrace = TracingFunctionHolder._original_tracing
        TracingFunctionHolder._original_tracing = None


_lock = ForkSafeLock()


def _load_python_helper_lib():
    try:
        # If it's already loaded, just return it.
        return _load_python_helper_lib.__lib__
    except AttributeError:
        pass
    with _lock:
        try:
            return _load_python_helper_lib.__lib__
        except AttributeError:
            pass

        lib = _load_python_helper_lib_uncached()
        _load_python_helper_lib.__lib__ = lib
        return lib


def get_python_helper_lib_filename():
    # Note: we have an independent (and similar -- but not equal) version of this method in
    # `add_code_to_python_process.py` which should be kept synchronized with this one (we do a copy
    # because the `pydevd_attach_to_process` is mostly independent and shouldn't be imported in the
    # debugger -- the only situation where it's imported is if the user actually does an attach to
    # process, through `attach_pydevd.py`, but this should usually be called from the IDE directly
    # and not from the debugger).
    libdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pydevd_attach_to_process")

    if not os.path.exists(libdir):
        pydev_log.critical("Expected the directory: %s to exist!", libdir)

    arch = ""
    if IS_WINDOWS:
        # prefer not using platform.machine() when possible (it's a bit heavyweight as it may
        # spawn a subprocess).
        arch = os.environ.get("PROCESSOR_ARCHITEW6432", os.environ.get("PROCESSOR_ARCHITECTURE", ""))

    if not arch:
        arch = platform.machine()
        if not arch:
            pydev_log.info("platform.machine() did not return valid value.")  # This shouldn't happen...
            return None

    if IS_WINDOWS:
        extension = ".dll"
        suffix_64 = "amd64"
        suffix_32 = "x86"

    elif IS_LINUX:
        extension = ".so"
        suffix_64 = "amd64"
        suffix_32 = "x86"

    elif IS_MAC:
        extension = ".dylib"
        suffix_64 = "x86_64"
        suffix_32 = "x86"

    else:
        pydev_log.info("Unable to set trace to all threads in platform: %s", sys.platform)
        return None

    if arch.lower() not in ("amd64", "x86", "x86_64", "i386", "x86"):
        # We don't support this processor by default. Still, let's support the case where the
        # user manually compiled it himself with some heuristics.
        #
        # Ideally the user would provide a library in the format: "attach_<arch>.<extension>"
        # based on the way it's currently compiled -- see:
        # - windows/compile_windows.bat
        # - linux_and_mac/compile_linux.sh
        # - linux_and_mac/compile_mac.sh

        try:
            found = [name for name in os.listdir(libdir) if name.startswith("attach_") and name.endswith(extension)]
        except:
            if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 1:
                # There is no need to show this unless debug tracing is enabled.
                pydev_log.exception("Error listing dir: %s", libdir)
            return None

        expected_name = "attach_" + arch + extension
        expected_name_linux = "attach_linux_" + arch + extension

        filename = None
        if expected_name in found:  # Heuristic: user compiled with "attach_<arch>.<extension>"
            filename = os.path.join(libdir, expected_name)

        elif IS_LINUX and expected_name_linux in found:  # Heuristic: user compiled with "attach_linux_<arch>.<extension>"
            filename = os.path.join(libdir, expected_name_linux)

        elif len(found) == 1:  # Heuristic: user removed all libraries and just left his own lib.
            filename = os.path.join(libdir, found[0])

        else:  # Heuristic: there's one additional library which doesn't seem to be our own. Find the odd one.
            filtered = [name for name in found if not name.endswith((suffix_64 + extension, suffix_32 + extension))]
            if len(filtered) == 1:  # If more than one is available we can't be sure...
                filename = os.path.join(libdir, found[0])

        if filename is None:
            pydev_log.info("Unable to set trace to all threads in arch: %s (did not find a %s lib in %s).", arch, expected_name, libdir)
            return None

        pydev_log.info("Using %s lib in arch: %s.", filename, arch)

    else:
        # Happy path for which we have pre-compiled binaries.
        if IS_64BIT_PROCESS:
            suffix = suffix_64
        else:
            suffix = suffix_32

        if IS_WINDOWS or IS_MAC:  # just the extension changes
            prefix = "attach_"
        elif IS_LINUX:  #
            prefix = "attach_linux_"  # historically it has a different name
        else:
            pydev_log.info("Unable to set trace to all threads in platform: %s", sys.platform)
            return None

        filename = os.path.join(libdir, "%s%s%s" % (prefix, suffix, extension))

    if not os.path.exists(filename):
        pydev_log.critical("Expected: %s to exist.", filename)
        return None

    return filename


def _load_python_helper_lib_uncached():
    if (
        not IS_CPYTHON
        or sys.version_info[:2] > (3, 11)
        or hasattr(sys, "gettotalrefcount")
        or LOAD_NATIVE_LIB_FLAG in ENV_FALSE_LOWER_VALUES
    ):
        pydev_log.info("Helper lib to set tracing to all threads not loaded.")
        return None

    try:
        filename = get_python_helper_lib_filename()
        if filename is None:
            return None
        # Load as pydll so that we don't release the gil.
        lib = ctypes.pydll.LoadLibrary(filename)
        pydev_log.info("Successfully Loaded helper lib to set tracing to all threads.")
        return lib
    except:
        if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 1:
            # Only show message if tracing is on (we don't have pre-compiled
            # binaries for all architectures -- i.e.: ARM).
            pydev_log.exception("Error loading: %s", filename)
        return None


def set_trace_to_threads(tracing_func, thread_idents=None, create_dummy_thread=True):
    if PYDEVD_USE_SYS_MONITORING:
        raise RuntimeError("Should not be called when using sys.monitoring.")
    assert tracing_func is not None

    ret = 0

    # Note: use sys._current_frames() keys to get the thread ids because it'll return
    # thread ids created in C/C++ where there's user code running, unlike the APIs
    # from the threading module which see only threads created through it (unless
    # a call for threading.current_thread() was previously done in that thread,
    # in which case a dummy thread would've been created for it).
    if thread_idents is None:
        thread_idents = set(sys._current_frames().keys())

        for t in threading.enumerate():
            # PY-44778: ignore pydevd threads and also add any thread that wasn't found on
            # sys._current_frames() as some existing threads may not appear in
            # sys._current_frames() but may be available through the `threading` module.
            if getattr(t, "pydev_do_not_trace", False):
                thread_idents.discard(t.ident)
            else:
                thread_idents.add(t.ident)

    curr_ident = thread.get_ident()
    curr_thread = threading._active.get(curr_ident)

    if curr_ident in thread_idents and len(thread_idents) != 1:
        # The current thread must be updated first (because we need to set
        # the reference to `curr_thread`).
        thread_idents = list(thread_idents)
        thread_idents.remove(curr_ident)
        thread_idents.insert(0, curr_ident)

    for thread_ident in thread_idents:
        # If that thread is not available in the threading module we also need to create a
        # dummy thread for it (otherwise it'll be invisible to the debugger).
        if create_dummy_thread:
            if thread_ident not in threading._active:

                class _DummyThread(threading._DummyThread):
                    def _set_ident(self):
                        # Note: Hack to set the thread ident that we want.
                        self._ident = thread_ident

                t = _DummyThread()
                # Reset to the base class (don't expose our own version of the class).
                t.__class__ = threading._DummyThread

                if thread_ident == curr_ident:
                    curr_thread = t

                with threading._active_limbo_lock:
                    # On Py2 it'll put in active getting the current indent, not using the
                    # ident that was set, so, we have to update it (should be harmless on Py3
                    # so, do it always).
                    threading._active[thread_ident] = t
                    threading._active[curr_ident] = curr_thread

                    if t.ident != thread_ident:
                        # Check if it actually worked.
                        pydev_log.critical("pydevd: creation of _DummyThread with fixed thread ident did not succeed.")

        # Some (ptvsd) tests failed because of this, so, leave it always disabled for now.
        # show_debug_info = 1 if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 1 else 0
        show_debug_info = 0

        # Hack to increase _Py_TracingPossible.
        # See comments on py_custom_pyeval_settrace.hpp
        proceed = thread.allocate_lock()
        proceed.acquire()

        def dummy_trace(frame, event, arg):
            return dummy_trace

        def increase_tracing_count():
            set_trace = TracingFunctionHolder._original_tracing or sys.settrace
            set_trace(dummy_trace)
            proceed.release()

        start_new_thread = pydev_monkey.get_original_start_new_thread(thread)
        start_new_thread(increase_tracing_count, ())
        proceed.acquire()  # Only proceed after the release() is done.
        proceed = None

        # Note: The set_trace_func is not really used anymore in the C side.
        set_trace_func = TracingFunctionHolder._original_tracing or sys.settrace

        lib = _load_python_helper_lib()
        if lib is None:  # This is the case if it's not CPython.
            pydev_log.info("Unable to load helper lib to set tracing to all threads (unsupported python vm).")
            ret = -1
        else:
            try:
                result = lib.AttachDebuggerTracing(
                    ctypes.c_int(show_debug_info),
                    ctypes.py_object(set_trace_func),
                    ctypes.py_object(tracing_func),
                    ctypes.c_uint(thread_ident),
                    ctypes.py_object(None),
                )
            except:
                if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 1:
                    # There is no need to show this unless debug tracing is enabled.
                    pydev_log.exception("Error attaching debugger tracing")
                ret = -1
            else:
                if result != 0:
                    pydev_log.info("Unable to set tracing for existing thread. Result: %s", result)
                    ret = result

    return ret

# === NexusCore/openenv\Lib\site-packages\google\auth\transport\_mtls_helper.py ===
# Copyright 2020 Google LLC
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

"""Helper functions for getting mTLS cert and key."""

import json
import logging
from os import environ, path
import re
import subprocess

from google.auth import exceptions

CONTEXT_AWARE_METADATA_PATH = "~/.secureConnect/context_aware_metadata.json"
CERTIFICATE_CONFIGURATION_DEFAULT_PATH = "~/.config/gcloud/certificate_config.json"
_CERTIFICATE_CONFIGURATION_ENV = "GOOGLE_API_CERTIFICATE_CONFIG"
_CERT_PROVIDER_COMMAND = "cert_provider_command"
_CERT_REGEX = re.compile(
    b"-----BEGIN CERTIFICATE-----.+-----END CERTIFICATE-----\r?\n?", re.DOTALL
)

# support various format of key files, e.g.
# "-----BEGIN PRIVATE KEY-----...",
# "-----BEGIN EC PRIVATE KEY-----...",
# "-----BEGIN RSA PRIVATE KEY-----..."
# "-----BEGIN ENCRYPTED PRIVATE KEY-----"
_KEY_REGEX = re.compile(
    b"-----BEGIN [A-Z ]*PRIVATE KEY-----.+-----END [A-Z ]*PRIVATE KEY-----\r?\n?",
    re.DOTALL,
)

_LOGGER = logging.getLogger(__name__)


_PASSPHRASE_REGEX = re.compile(
    b"-----BEGIN PASSPHRASE-----(.+)-----END PASSPHRASE-----", re.DOTALL
)


def _check_config_path(config_path):
    """Checks for config file path. If it exists, returns the absolute path with user expansion;
    otherwise returns None.

    Args:
        config_path (str): The config file path for either context_aware_metadata.json or certificate_config.json for example

    Returns:
        str: absolute path if exists and None otherwise.
    """
    config_path = path.expanduser(config_path)
    if not path.exists(config_path):
        _LOGGER.debug("%s is not found.", config_path)
        return None
    return config_path


def _load_json_file(path):
    """Reads and loads JSON from the given path. Used to read both X509 workload certificate and
    secure connect configurations.

    Args:
        path (str): the path to read from.

    Returns:
        Dict[str, str]: The JSON stored at the file.

    Raises:
        google.auth.exceptions.ClientCertError: If failed to parse the file as JSON.
    """
    try:
        with open(path) as f:
            json_data = json.load(f)
    except ValueError as caught_exc:
        new_exc = exceptions.ClientCertError(caught_exc)
        raise new_exc from caught_exc

    return json_data


def _get_workload_cert_and_key(certificate_config_path=None):
    """Read the workload identity cert and key files specified in the certificate config provided.
    If no config path is provided, check the environment variable: "GOOGLE_API_CERTIFICATE_CONFIG"
    first, then the well known gcloud location: "~/.config/gcloud/certificate_config.json".

    Args:
        certificate_config_path (string): The certificate config path. If no path is provided,
        the environment variable will be checked first, then the well known gcloud location.

    Returns:
        Tuple[Optional[bytes], Optional[bytes]]: client certificate bytes in PEM format and key
            bytes in PEM format.

    Raises:
        google.auth.exceptions.ClientCertError: if problems occurs when retrieving
        the certificate or key information.
    """

    cert_path, key_path = _get_workload_cert_and_key_paths(certificate_config_path)

    if cert_path is None and key_path is None:
        return None, None

    return _read_cert_and_key_files(cert_path, key_path)


def _get_cert_config_path(certificate_config_path=None):
    """Get the certificate configuration path based on the following order:

    1: Explicit override, if set
    2: Environment variable, if set
    3: Well-known location

    Returns "None" if the selected config file does not exist.

    Args:
        certificate_config_path (string): The certificate config path. If provided, the well known
        location and environment variable will be ignored.

    Returns:
        The absolute path of the certificate config file, and None if the file does not exist.
    """

    if certificate_config_path is None:
        env_path = environ.get(_CERTIFICATE_CONFIGURATION_ENV, None)
        if env_path is not None and env_path != "":
            certificate_config_path = env_path
        else:
            certificate_config_path = CERTIFICATE_CONFIGURATION_DEFAULT_PATH

    certificate_config_path = path.expanduser(certificate_config_path)
    if not path.exists(certificate_config_path):
        return None
    return certificate_config_path


def _get_workload_cert_and_key_paths(config_path):
    absolute_path = _get_cert_config_path(config_path)
    if absolute_path is None:
        return None, None

    data = _load_json_file(absolute_path)

    if "cert_configs" not in data:
        raise exceptions.ClientCertError(
            'Certificate config file {} is in an invalid format, a "cert configs" object is expected'.format(
                absolute_path
            )
        )
    cert_configs = data["cert_configs"]

    if "workload" not in cert_configs:
        raise exceptions.ClientCertError(
            'Certificate config file {} is in an invalid format, a "workload" cert config is expected'.format(
                absolute_path
            )
        )
    workload = cert_configs["workload"]

    if "cert_path" not in workload:
        raise exceptions.ClientCertError(
            'Certificate config file {} is in an invalid format, a "cert_path" is expected in the workload cert config'.format(
                absolute_path
            )
        )
    cert_path = workload["cert_path"]

    if "key_path" not in workload:
        raise exceptions.ClientCertError(
            'Certificate config file {} is in an invalid format, a "key_path" is expected in the workload cert config'.format(
                absolute_path
            )
        )
    key_path = workload["key_path"]

    return cert_path, key_path


def _read_cert_and_key_files(cert_path, key_path):
    cert_data = _read_cert_file(cert_path)
    key_data = _read_key_file(key_path)

    return cert_data, key_data


def _read_cert_file(cert_path):
    with open(cert_path, "rb") as cert_file:
        cert_data = cert_file.read()

    cert_match = re.findall(_CERT_REGEX, cert_data)
    if len(cert_match) != 1:
        raise exceptions.ClientCertError(
            "Certificate file {} is in an invalid format, a single PEM formatted certificate is expected".format(
                cert_path
            )
        )
    return cert_match[0]


def _read_key_file(key_path):
    with open(key_path, "rb") as key_file:
        key_data = key_file.read()

    key_match = re.findall(_KEY_REGEX, key_data)
    if len(key_match) != 1:
        raise exceptions.ClientCertError(
            "Private key file {} is in an invalid format, a single PEM formatted private key is expected".format(
                key_path
            )
        )

    return key_match[0]


def _run_cert_provider_command(command, expect_encrypted_key=False):
    """Run the provided command, and return client side mTLS cert, key and
    passphrase.

    Args:
        command (List[str]): cert provider command.
        expect_encrypted_key (bool): If encrypted private key is expected.

    Returns:
        Tuple[bytes, bytes, bytes]: client certificate bytes in PEM format, key
            bytes in PEM format and passphrase bytes.

    Raises:
        google.auth.exceptions.ClientCertError: if problems occurs when running
            the cert provider command or generating cert, key and passphrase.
    """
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
    except OSError as caught_exc:
        new_exc = exceptions.ClientCertError(caught_exc)
        raise new_exc from caught_exc

    # Check cert provider command execution error.
    if process.returncode != 0:
        raise exceptions.ClientCertError(
            "Cert provider command returns non-zero status code %s" % process.returncode
        )

    # Extract certificate (chain), key and passphrase.
    cert_match = re.findall(_CERT_REGEX, stdout)
    if len(cert_match) != 1:
        raise exceptions.ClientCertError("Client SSL certificate is missing or invalid")
    key_match = re.findall(_KEY_REGEX, stdout)
    if len(key_match) != 1:
        raise exceptions.ClientCertError("Client SSL key is missing or invalid")
    passphrase_match = re.findall(_PASSPHRASE_REGEX, stdout)

    if expect_encrypted_key:
        if len(passphrase_match) != 1:
            raise exceptions.ClientCertError("Passphrase is missing or invalid")
        if b"ENCRYPTED" not in key_match[0]:
            raise exceptions.ClientCertError("Encrypted private key is expected")
        return cert_match[0], key_match[0], passphrase_match[0].strip()

    if b"ENCRYPTED" in key_match[0]:
        raise exceptions.ClientCertError("Encrypted private key is not expected")
    if len(passphrase_match) > 0:
        raise exceptions.ClientCertError("Passphrase is not expected")
    return cert_match[0], key_match[0], None


def get_client_ssl_credentials(
    generate_encrypted_key=False,
    context_aware_metadata_path=CONTEXT_AWARE_METADATA_PATH,
    certificate_config_path=CERTIFICATE_CONFIGURATION_DEFAULT_PATH,
):
    """Returns the client side certificate, private key and passphrase.

    We look for certificates and keys with the following order of priority:
        1. Certificate and key specified by certificate_config.json.
               Currently, only X.509 workload certificates are supported.
        2. Certificate and key specified by context aware metadata (i.e. SecureConnect).

    Args:
        generate_encrypted_key (bool): If set to True, encrypted private key
            and passphrase will be generated; otherwise, unencrypted private key
            will be generated and passphrase will be None. This option only
            affects keys obtained via context_aware_metadata.json.
        context_aware_metadata_path (str): The context_aware_metadata.json file path.
        certificate_config_path (str): The certificate_config.json file path.

    Returns:
        Tuple[bool, bytes, bytes, bytes]:
            A boolean indicating if cert, key and passphrase are obtained, the
            cert bytes and key bytes both in PEM format, and passphrase bytes.

    Raises:
        google.auth.exceptions.ClientCertError: if problems occurs when getting
            the cert, key and passphrase.
    """

    # 1. Check for certificate config json.
    cert_config_path = _check_config_path(certificate_config_path)
    if cert_config_path:
        # Attempt to retrieve X.509 Workload cert and key.
        cert, key = _get_workload_cert_and_key(cert_config_path)
        if cert and key:
            return True, cert, key, None

    # 2. Check for context aware metadata json
    metadata_path = _check_config_path(context_aware_metadata_path)

    if metadata_path:
        metadata_json = _load_json_file(metadata_path)

        if _CERT_PROVIDER_COMMAND not in metadata_json:
            raise exceptions.ClientCertError("Cert provider command is not found")

        command = metadata_json[_CERT_PROVIDER_COMMAND]

        if generate_encrypted_key and "--with_passphrase" not in command:
            command.append("--with_passphrase")

        # Execute the command.
        cert, key, passphrase = _run_cert_provider_command(
            command, expect_encrypted_key=generate_encrypted_key
        )
        return True, cert, key, passphrase

    return False, None, None, None


def get_client_cert_and_key(client_cert_callback=None):
    """Returns the client side certificate and private key. The function first
    tries to get certificate and key from client_cert_callback; if the callback
    is None or doesn't provide certificate and key, the function tries application
    default SSL credentials.

    Args:
        client_cert_callback (Optional[Callable[[], (bytes, bytes)]]): An
            optional callback which returns client certificate bytes and private
            key bytes both in PEM format.

    Returns:
        Tuple[bool, bytes, bytes]:
            A boolean indicating if cert and key are obtained, the cert bytes
            and key bytes both in PEM format.

    Raises:
        google.auth.exceptions.ClientCertError: if problems occurs when getting
            the cert and key.
    """
    if client_cert_callback:
        cert, key = client_cert_callback()
        return True, cert, key

    has_cert, cert, key, _ = get_client_ssl_credentials(generate_encrypted_key=False)
    return has_cert, cert, key


def decrypt_private_key(key, passphrase):
    """A helper function to decrypt the private key with the given passphrase.
    google-auth library doesn't support passphrase protected private key for
    mutual TLS channel. This helper function can be used to decrypt the
    passphrase protected private key in order to estalish mutual TLS channel.

    For example, if you have a function which produces client cert, passphrase
    protected private key and passphrase, you can convert it to a client cert
    callback function accepted by google-auth::

        from google.auth.transport import _mtls_helper

        def your_client_cert_function():
            return cert, encrypted_key, passphrase

        # callback accepted by google-auth for mutual TLS channel.
        def client_cert_callback():
            cert, encrypted_key, passphrase = your_client_cert_function()
            decrypted_key = _mtls_helper.decrypt_private_key(encrypted_key,
                passphrase)
            return cert, decrypted_key

    Args:
        key (bytes): The private key bytes in PEM format.
        passphrase (bytes): The passphrase bytes.

    Returns:
        bytes: The decrypted private key in PEM format.

    Raises:
        ImportError: If pyOpenSSL is not installed.
        OpenSSL.crypto.Error: If there is any problem decrypting the private key.
    """
    from OpenSSL import crypto

    # First convert encrypted_key_bytes to PKey object
    pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key, passphrase=passphrase)

    # Then dump the decrypted key bytes
    return crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey)

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\vector_stores\bedrock_vector_store.py ===
# +-------------------------------------------------------------+
#
#           Add Bedrock Knowledge Base Context to your LLM calls
#
# +-------------------------------------------------------------+
#  Thank you users! We ❤️ you! - Krrish & Ishaan

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import litellm
from litellm._logging import verbose_logger, verbose_proxy_logger
from litellm.integrations.custom_logger import CustomLogger
from litellm.integrations.vector_stores.base_vector_store import BaseVectorStore
from litellm.llms.bedrock.base_aws_llm import BaseAWSLLM
from litellm.llms.custom_httpx.http_handler import (
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.types.integrations.rag.bedrock_knowledgebase import (
    BedrockKBContent,
    BedrockKBGuardrailConfiguration,
    BedrockKBRequest,
    BedrockKBResponse,
    BedrockKBRetrievalConfiguration,
    BedrockKBRetrievalQuery,
    BedrockKBRetrievalResult,
)
from litellm.types.llms.openai import AllMessageValues, ChatCompletionUserMessage
from litellm.types.utils import StandardLoggingVectorStoreRequest
from litellm.types.vector_stores import (
    VectorStoreResultContent,
    VectorStoreSearchResponse,
    VectorStoreSearchResult,
)

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import StandardCallbackDynamicParams
else:
    StandardCallbackDynamicParams = Any


class BedrockVectorStore(BaseVectorStore, BaseAWSLLM):
    CONTENT_PREFIX_STRING = "Context: \n\n"
    CUSTOM_LLM_PROVIDER = "bedrock"

    def __init__(
        self,
        **kwargs,
    ):
        self.async_handler = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.LoggingCallback
        )

        # store kwargs as optional_params
        self.optional_params = kwargs

        super().__init__(**kwargs)
        BaseAWSLLM.__init__(self)

    async def async_get_chat_completion_prompt(
        self,
        model: str,
        messages: List[AllMessageValues],
        non_default_params: dict,
        prompt_id: Optional[str],
        prompt_variables: Optional[dict],
        dynamic_callback_params: StandardCallbackDynamicParams,
        litellm_logging_obj: LiteLLMLoggingObj,
        tools: Optional[List[Dict]] = None,
        prompt_label: Optional[str] = None,
    ) -> Tuple[str, List[AllMessageValues], dict]:
        """
        Retrieves the context from the Bedrock Knowledge Base and appends it to the messages.
        """
        if litellm.vector_store_registry is None:
            return model, messages, non_default_params

        vector_store_ids = litellm.vector_store_registry.pop_vector_store_ids_to_run(
            non_default_params=non_default_params, tools=tools
        )
        vector_store_request_metadata: List[StandardLoggingVectorStoreRequest] = []
        if vector_store_ids:
            for vector_store_id in vector_store_ids:
                start_time = datetime.now()
                query = self._get_kb_query_from_messages(messages)
                bedrock_kb_response = await self.make_bedrock_kb_retrieve_request(
                    knowledge_base_id=vector_store_id,
                    query=query,
                    non_default_params=non_default_params,
                )
                verbose_logger.debug(
                    f"Bedrock Knowledge Base Response: {bedrock_kb_response}"
                )

                (
                    context_message,
                    context_string,
                ) = self.get_chat_completion_message_from_bedrock_kb_response(
                    bedrock_kb_response
                )
                if context_message is not None:
                    messages.append(context_message)

                #################################################################################################
                ########## LOGGING for Standard Logging Payload, Langfuse, s3, LiteLLM DB etc. ##################
                #################################################################################################
                vector_store_search_response: VectorStoreSearchResponse = (
                    self.transform_bedrock_kb_response_to_vector_store_search_response(
                        bedrock_kb_response=bedrock_kb_response, query=query
                    )
                )
                vector_store_request_metadata.append(
                    StandardLoggingVectorStoreRequest(
                        vector_store_id=vector_store_id,
                        query=query,
                        vector_store_search_response=vector_store_search_response,
                        custom_llm_provider=self.CUSTOM_LLM_PROVIDER,
                        start_time=start_time.timestamp(),
                        end_time=datetime.now().timestamp(),
                    )
                )

            litellm_logging_obj.model_call_details[
                "vector_store_request_metadata"
            ] = vector_store_request_metadata

        return model, messages, non_default_params

    def transform_bedrock_kb_response_to_vector_store_search_response(
        self,
        bedrock_kb_response: BedrockKBResponse,
        query: str,
    ) -> VectorStoreSearchResponse:
        """
        Transform a BedrockKBResponse to a VectorStoreSearchResponse
        """
        retrieval_results: Optional[
            List[BedrockKBRetrievalResult]
        ] = bedrock_kb_response.get("retrievalResults", None)
        vector_store_search_response: VectorStoreSearchResponse = (
            VectorStoreSearchResponse(search_query=query, data=[])
        )
        if retrieval_results is None:
            return vector_store_search_response

        vector_search_response_data: List[VectorStoreSearchResult] = []
        for retrieval_result in retrieval_results:
            content: Optional[BedrockKBContent] = retrieval_result.get("content", None)
            if content is None:
                continue
            content_text: Optional[str] = content.get("text", None)
            if content_text is None:
                continue
            vector_store_search_result: VectorStoreSearchResult = (
                VectorStoreSearchResult(
                    score=retrieval_result.get("score", None),
                    content=[VectorStoreResultContent(text=content_text, type="text")],
                )
            )
            vector_search_response_data.append(vector_store_search_result)
        vector_store_search_response["data"] = vector_search_response_data
        return vector_store_search_response

    def _get_kb_query_from_messages(self, messages: List[AllMessageValues]) -> str:
        """
        Uses the text `content` field of the last message in the list of messages
        """
        if len(messages) == 0:
            return ""
        last_message = messages[-1]
        last_message_content = last_message.get("content", None)
        if last_message_content is None:
            return ""
        if isinstance(last_message_content, str):
            return last_message_content
        elif isinstance(last_message_content, list):
            return "\n".join([item.get("text", "") for item in last_message_content])
        return ""

    def _prepare_request(
        self,
        credentials: Any,
        data: BedrockKBRequest,
        optional_params: dict,
        aws_region_name: str,
        api_base: str,
        extra_headers: Optional[dict] = None,
    ) -> Any:
        """
        Prepare a signed AWS request.

        Args:
            credentials: AWS credentials
            data: Request data
            optional_params: Additional parameters
            aws_region_name: AWS region name
            api_base: Base API URL
            extra_headers: Additional headers

        Returns:
            AWSRequest: A signed AWS request
        """
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")

        sigv4 = SigV4Auth(credentials, "bedrock", aws_region_name)

        encoded_data = json.dumps(data).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if extra_headers is not None:
            headers = {"Content-Type": "application/json", **extra_headers}

        request = AWSRequest(
            method="POST", url=api_base, data=encoded_data, headers=headers
        )
        sigv4.add_auth(request)
        if extra_headers is not None and "Authorization" in extra_headers:
            # prevent sigv4 from overwriting the auth header
            request.headers["Authorization"] = extra_headers["Authorization"]

        return request.prepare()

    async def make_bedrock_kb_retrieve_request(
        self,
        knowledge_base_id: str,
        query: str,
        guardrail_id: Optional[str] = None,
        guardrail_version: Optional[str] = None,
        next_token: Optional[str] = None,
        retrieval_configuration: Optional[BedrockKBRetrievalConfiguration] = None,
        non_default_params: Optional[dict] = None,
    ) -> BedrockKBResponse:
        """
        Make a Bedrock Knowledge Base retrieve request.

        Args:
            knowledge_base_id (str): The unique identifier of the knowledge base to query
            query (str): The query text to search for
            guardrail_id (Optional[str]): The guardrail ID to apply
            guardrail_version (Optional[str]): The version of the guardrail to apply
            next_token (Optional[str]): Token for pagination
            retrieval_configuration (Optional[BedrockKBRetrievalConfiguration]): Configuration for the retrieval process

        Returns:
            BedrockKBRetrievalResponse: A typed response object containing the retrieval results
        """
        from fastapi import HTTPException

        non_default_params = non_default_params or {}
        credentials_dict: Dict[str, Any] = {}
        if litellm.vector_store_registry is not None:
            credentials_dict = (
                litellm.vector_store_registry.get_credentials_for_vector_store(
                    knowledge_base_id
                )
            )

        credentials = self.get_credentials(
            aws_access_key_id=credentials_dict.get(
                "aws_access_key_id", non_default_params.get("aws_access_key_id", None)
            ),
            aws_secret_access_key=credentials_dict.get(
                "aws_secret_access_key",
                non_default_params.get("aws_secret_access_key", None),
            ),
            aws_session_token=credentials_dict.get(
                "aws_session_token", non_default_params.get("aws_session_token", None)
            ),
            aws_region_name=credentials_dict.get(
                "aws_region_name", non_default_params.get("aws_region_name", None)
            ),
            aws_session_name=credentials_dict.get(
                "aws_session_name", non_default_params.get("aws_session_name", None)
            ),
            aws_profile_name=credentials_dict.get(
                "aws_profile_name", non_default_params.get("aws_profile_name", None)
            ),
            aws_role_name=credentials_dict.get(
                "aws_role_name", non_default_params.get("aws_role_name", None)
            ),
            aws_web_identity_token=credentials_dict.get(
                "aws_web_identity_token",
                non_default_params.get("aws_web_identity_token", None),
            ),
            aws_sts_endpoint=credentials_dict.get(
                "aws_sts_endpoint", non_default_params.get("aws_sts_endpoint", None)
            ),
        )
        aws_region_name = self.get_aws_region_name_for_non_llm_api_calls(
            aws_region_name=credentials_dict.get(
                "aws_region_name", non_default_params.get("aws_region_name", None)
            ),
        )

        # Prepare request data
        request_data: BedrockKBRequest = BedrockKBRequest(
            retrievalQuery=BedrockKBRetrievalQuery(text=query),
        )
        if next_token:
            request_data["nextToken"] = next_token
        if retrieval_configuration:
            request_data["retrievalConfiguration"] = retrieval_configuration
        if guardrail_id and guardrail_version:
            request_data["guardrailConfiguration"] = BedrockKBGuardrailConfiguration(
                guardrailId=guardrail_id, guardrailVersion=guardrail_version
            )
        verbose_logger.debug(
            f"Request Data: {json.dumps(request_data, indent=4, default=str)}"
        )

        # Prepare the request
        api_base = f"https://bedrock-agent-runtime.{aws_region_name}.amazonaws.com/knowledgebases/{knowledge_base_id}/retrieve"

        prepared_request = self._prepare_request(
            credentials=credentials,
            data=request_data,
            optional_params=self.optional_params,
            aws_region_name=aws_region_name,
            api_base=api_base,
        )

        verbose_proxy_logger.debug(
            "Bedrock Knowledge Base request body: %s, url %s, headers: %s",
            request_data,
            prepared_request.url,
            prepared_request.headers,
        )

        response = await self.async_handler.post(
            url=prepared_request.url,
            data=prepared_request.body,  # type: ignore
            headers=prepared_request.headers,  # type: ignore
        )

        verbose_proxy_logger.debug("Bedrock Knowledge Base response: %s", response.text)

        if response.status_code == 200:
            response_data = response.json()
            return BedrockKBResponse(**response_data)
        else:
            verbose_proxy_logger.error(
                "Bedrock Knowledge Base: error in response. Status code: %s, response: %s",
                response.status_code,
                response.text,
            )
            raise HTTPException(
                status_code=response.status_code,
                detail={
                    "error": "Error calling Bedrock Knowledge Base",
                    "response": response.text,
                },
            )

    @staticmethod
    def get_initialized_custom_logger() -> Optional[CustomLogger]:
        from litellm.litellm_core_utils.litellm_logging import (
            _init_custom_logger_compatible_class,
        )

        return _init_custom_logger_compatible_class(
            logging_integration="bedrock_vector_store",
            internal_usage_cache=None,
            llm_router=None,
        )

    @staticmethod
    def get_chat_completion_message_from_bedrock_kb_response(
        response: BedrockKBResponse,
    ) -> Tuple[Optional[ChatCompletionUserMessage], str]:
        """
        Retrieves the context from the Bedrock Knowledge Base response and returns a ChatCompletionUserMessage object.
        """
        retrieval_results: Optional[List[BedrockKBRetrievalResult]] = response.get(
            "retrievalResults", None
        )
        if retrieval_results is None:
            return None, ""

        # string to combine the context from the knowledge base
        context_string: str = BedrockVectorStore.CONTENT_PREFIX_STRING
        for retrieval_result in retrieval_results:
            retrieval_result_content: Optional[BedrockKBContent] = (
                retrieval_result.get("content", None) or {}
            )
            if retrieval_result_content is None:
                continue
            retrieval_result_text: Optional[str] = retrieval_result_content.get(
                "text", None
            )
            if retrieval_result_text is None:
                continue
            context_string += retrieval_result_text
        message = ChatCompletionUserMessage(
            role="user",
            content=context_string,
        )
        return message, context_string

# === NexusCore/openenv\Lib\site-packages\nltk\chunk\named_entity.py ===
# Natural Language Toolkit: Chunk parsing API
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Eric Kafe <kafe.eric@gmail.com> (tab-format models)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Named entity chunker
"""

import os
import re
from xml.etree import ElementTree as ET

from nltk.tag import ClassifierBasedTagger, pos_tag

try:
    from nltk.classify import MaxentClassifier
except ImportError:
    pass

from nltk.chunk.api import ChunkParserI
from nltk.chunk.util import ChunkScore
from nltk.data import find
from nltk.tokenize import word_tokenize
from nltk.tree import Tree


class NEChunkParserTagger(ClassifierBasedTagger):
    """
    The IOB tagger used by the chunk parser.
    """

    def __init__(self, train=None, classifier=None):
        ClassifierBasedTagger.__init__(
            self,
            train=train,
            classifier_builder=self._classifier_builder,
            classifier=classifier,
        )

    def _classifier_builder(self, train):
        return MaxentClassifier.train(
            #          "megam" cannot be the default algorithm since it requires compiling with ocaml
            train,
            algorithm="iis",
            gaussian_prior_sigma=1,
            trace=2,
        )

    def _english_wordlist(self):
        try:
            wl = self._en_wordlist
        except AttributeError:
            from nltk.corpus import words

            self._en_wordlist = set(words.words("en-basic"))
            wl = self._en_wordlist
        return wl

    def _feature_detector(self, tokens, index, history):
        word = tokens[index][0]
        pos = simplify_pos(tokens[index][1])
        if index == 0:
            prevword = prevprevword = None
            prevpos = prevprevpos = None
            prevshape = prevtag = prevprevtag = None
        elif index == 1:
            prevword = tokens[index - 1][0].lower()
            prevprevword = None
            prevpos = simplify_pos(tokens[index - 1][1])
            prevprevpos = None
            prevtag = history[index - 1][0]
            prevshape = prevprevtag = None
        else:
            prevword = tokens[index - 1][0].lower()
            prevprevword = tokens[index - 2][0].lower()
            prevpos = simplify_pos(tokens[index - 1][1])
            prevprevpos = simplify_pos(tokens[index - 2][1])
            prevtag = history[index - 1]
            prevprevtag = history[index - 2]
            prevshape = shape(prevword)
        if index == len(tokens) - 1:
            nextword = nextnextword = None
            nextpos = nextnextpos = None
        elif index == len(tokens) - 2:
            nextword = tokens[index + 1][0].lower()
            nextpos = tokens[index + 1][1].lower()
            nextnextword = None
            nextnextpos = None
        else:
            nextword = tokens[index + 1][0].lower()
            nextpos = tokens[index + 1][1].lower()
            nextnextword = tokens[index + 2][0].lower()
            nextnextpos = tokens[index + 2][1].lower()

        # 89.6
        features = {
            "bias": True,
            "shape": shape(word),
            "wordlen": len(word),
            "prefix3": word[:3].lower(),
            "suffix3": word[-3:].lower(),
            "pos": pos,
            "word": word,
            "en-wordlist": (word in self._english_wordlist()),
            "prevtag": prevtag,
            "prevpos": prevpos,
            "nextpos": nextpos,
            "prevword": prevword,
            "nextword": nextword,
            "word+nextpos": f"{word.lower()}+{nextpos}",
            "pos+prevtag": f"{pos}+{prevtag}",
            "shape+prevtag": f"{prevshape}+{prevtag}",
        }

        return features


class NEChunkParser(ChunkParserI):
    """
    Expected input: list of pos-tagged words
    """

    def __init__(self, train):
        self._train(train)

    def parse(self, tokens):
        """
        Each token should be a pos-tagged word
        """
        tagged = self._tagger.tag(tokens)
        tree = self._tagged_to_parse(tagged)
        return tree

    def _train(self, corpus):
        # Convert to tagged sequence
        corpus = [self._parse_to_tagged(s) for s in corpus]

        self._tagger = NEChunkParserTagger(train=corpus)

    def _tagged_to_parse(self, tagged_tokens):
        """
        Convert a list of tagged tokens to a chunk-parse tree.
        """
        sent = Tree("S", [])

        for tok, tag in tagged_tokens:
            if tag == "O":
                sent.append(tok)
            elif tag.startswith("B-"):
                sent.append(Tree(tag[2:], [tok]))
            elif tag.startswith("I-"):
                if sent and isinstance(sent[-1], Tree) and sent[-1].label() == tag[2:]:
                    sent[-1].append(tok)
                else:
                    sent.append(Tree(tag[2:], [tok]))
        return sent

    @staticmethod
    def _parse_to_tagged(sent):
        """
        Convert a chunk-parse tree to a list of tagged tokens.
        """
        toks = []
        for child in sent:
            if isinstance(child, Tree):
                if len(child) == 0:
                    print("Warning -- empty chunk in sentence")
                    continue
                toks.append((child[0], f"B-{child.label()}"))
                for tok in child[1:]:
                    toks.append((tok, f"I-{child.label()}"))
            else:
                toks.append((child, "O"))
        return toks


def shape(word):
    if re.match(r"[0-9]+(\.[0-9]*)?|[0-9]*\.[0-9]+$", word, re.UNICODE):
        return "number"
    elif re.match(r"\W+$", word, re.UNICODE):
        return "punct"
    elif re.match(r"\w+$", word, re.UNICODE):
        if word.istitle():
            return "upcase"
        elif word.islower():
            return "downcase"
        else:
            return "mixedcase"
    else:
        return "other"


def simplify_pos(s):
    if s.startswith("V"):
        return "V"
    else:
        return s.split("-")[0]


def postag_tree(tree):
    # Part-of-speech tagging.
    words = tree.leaves()
    tag_iter = (pos for (word, pos) in pos_tag(words))
    newtree = Tree("S", [])
    for child in tree:
        if isinstance(child, Tree):
            newtree.append(Tree(child.label(), []))
            for subchild in child:
                newtree[-1].append((subchild, next(tag_iter)))
        else:
            newtree.append((child, next(tag_iter)))
    return newtree


def load_ace_data(roots, fmt="binary", skip_bnews=True):
    for root in roots:
        for root, dirs, files in os.walk(root):
            if root.endswith("bnews") and skip_bnews:
                continue
            for f in files:
                if f.endswith(".sgm"):
                    yield from load_ace_file(os.path.join(root, f), fmt)


def load_ace_file(textfile, fmt):
    print(f"  - {os.path.split(textfile)[1]}")
    annfile = textfile + ".tmx.rdc.xml"

    # Read the xml file, and get a list of entities
    entities = []
    with open(annfile) as infile:
        xml = ET.parse(infile).getroot()
    for entity in xml.findall("document/entity"):
        typ = entity.find("entity_type").text
        for mention in entity.findall("entity_mention"):
            if mention.get("TYPE") != "NAME":
                continue  # only NEs
            s = int(mention.find("head/charseq/start").text)
            e = int(mention.find("head/charseq/end").text) + 1
            entities.append((s, e, typ))

    # Read the text file, and mark the entities.
    with open(textfile) as infile:
        text = infile.read()

    # Strip XML tags, since they don't count towards the indices
    text = re.sub("<(?!/?TEXT)[^>]+>", "", text)

    # Blank out anything before/after <TEXT>
    def subfunc(m):
        return " " * (m.end() - m.start() - 6)

    text = re.sub(r"[\s\S]*<TEXT>", subfunc, text)
    text = re.sub(r"</TEXT>[\s\S]*", "", text)

    # Simplify quotes
    text = re.sub("``", ' "', text)
    text = re.sub("''", '" ', text)

    entity_types = {typ for (s, e, typ) in entities}

    # Binary distinction (NE or not NE)
    if fmt == "binary":
        i = 0
        toks = Tree("S", [])
        for s, e, typ in sorted(entities):
            if s < i:
                s = i  # Overlapping!  Deal with this better?
            if e <= s:
                continue
            toks.extend(word_tokenize(text[i:s]))
            toks.append(Tree("NE", text[s:e].split()))
            i = e
        toks.extend(word_tokenize(text[i:]))
        yield toks

    # Multiclass distinction (NE type)
    elif fmt == "multiclass":
        i = 0
        toks = Tree("S", [])
        for s, e, typ in sorted(entities):
            if s < i:
                s = i  # Overlapping!  Deal with this better?
            if e <= s:
                continue
            toks.extend(word_tokenize(text[i:s]))
            toks.append(Tree(typ, text[s:e].split()))
            i = e
        toks.extend(word_tokenize(text[i:]))
        yield toks

    else:
        raise ValueError("bad fmt value")


# This probably belongs in a more general-purpose location (as does
# the parse_to_tagged function).
def cmp_chunks(correct, guessed):
    correct = NEChunkParser._parse_to_tagged(correct)
    guessed = NEChunkParser._parse_to_tagged(guessed)
    ellipsis = False
    for (w, ct), (w, gt) in zip(correct, guessed):
        if ct == gt == "O":
            if not ellipsis:
                print(f"  {ct:15} {gt:15} {w}")
                print("  {:15} {:15} {2}".format("...", "...", "..."))
                ellipsis = True
        else:
            ellipsis = False
            print(f"  {ct:15} {gt:15} {w}")


# ======================================================================================


class Maxent_NE_Chunker(NEChunkParser):
    """
    Expected input: list of pos-tagged words
    """

    def __init__(self, fmt="multiclass"):
        from nltk.data import find

        self._fmt = fmt
        self._tab_dir = find(f"chunkers/maxent_ne_chunker_tab/english_ace_{fmt}/")
        self.load_params()

    def load_params(self):
        from nltk.classify.maxent import BinaryMaxentFeatureEncoding, load_maxent_params

        wgt, mpg, lab, aon = load_maxent_params(self._tab_dir)
        mc = MaxentClassifier(
            BinaryMaxentFeatureEncoding(lab, mpg, alwayson_features=aon), wgt
        )
        self._tagger = NEChunkParserTagger(classifier=mc)

    def save_params(self):
        from nltk.classify.maxent import save_maxent_params

        classif = self._tagger._classifier
        ecg = classif._encoding
        wgt = classif._weights
        mpg = ecg._mapping
        lab = ecg._labels
        aon = ecg._alwayson
        fmt = self._fmt
        save_maxent_params(wgt, mpg, lab, aon, tab_dir=f"/tmp/english_ace_{fmt}/")


def build_model(fmt="multiclass"):
    chunker = Maxent_NE_Chunker(fmt)
    chunker.save_params()
    return chunker


# ======================================================================================

"""
2004 update: pickles are not supported anymore.

Deprecated:

def build_model(fmt="binary"):
    print("Loading training data...")
    train_paths = [
        find("corpora/ace_data/ace.dev"),
        find("corpora/ace_data/ace.heldout"),
        find("corpora/ace_data/bbn.dev"),
        find("corpora/ace_data/muc.dev"),
    ]
    train_trees = load_ace_data(train_paths, fmt)
    train_data = [postag_tree(t) for t in train_trees]
    print("Training...")
    cp = NEChunkParser(train_data)
    del train_data

    print("Loading eval data...")
    eval_paths = [find("corpora/ace_data/ace.eval")]
    eval_trees = load_ace_data(eval_paths, fmt)
    eval_data = [postag_tree(t) for t in eval_trees]

    print("Evaluating...")
    chunkscore = ChunkScore()
    for i, correct in enumerate(eval_data):
        guess = cp.parse(correct.leaves())
        chunkscore.score(correct, guess)
        if i < 3:
            cmp_chunks(correct, guess)
    print(chunkscore)

    outfilename = f"/tmp/ne_chunker_{fmt}.pickle"
    print(f"Saving chunker to {outfilename}...")

    with open(outfilename, "wb") as outfile:
        pickle.dump(cp, outfile, -1)

    return cp
"""

if __name__ == "__main__":
    # Make sure that the object has the right class name:
    build_model("binary")
    build_model("multiclass")

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\command\build_py.py ===
"""distutils.command.build_py

Implements the Distutils 'build_py' command."""

import glob
import importlib.util
import os
import sys
from distutils._log import log
from typing import ClassVar

from ..core import Command
from ..errors import DistutilsFileError, DistutilsOptionError
from ..util import convert_path


class build_py(Command):
    description = "\"build\" pure Python modules (copy to build directory)"

    user_options = [
        ('build-lib=', 'd', "directory to \"build\" (copy) to"),
        ('compile', 'c', "compile .py to .pyc"),
        ('no-compile', None, "don't compile .py files [default]"),
        (
            'optimize=',
            'O',
            "also compile with optimization: -O1 for \"python -O\", "
            "-O2 for \"python -OO\", and -O0 to disable [default: -O0]",
        ),
        ('force', 'f', "forcibly build everything (ignore file timestamps)"),
    ]

    boolean_options: ClassVar[list[str]] = ['compile', 'force']
    negative_opt: ClassVar[dict[str, str]] = {'no-compile': 'compile'}

    def initialize_options(self):
        self.build_lib = None
        self.py_modules = None
        self.package = None
        self.package_data = None
        self.package_dir = None
        self.compile = False
        self.optimize = 0
        self.force = None

    def finalize_options(self) -> None:
        self.set_undefined_options(
            'build', ('build_lib', 'build_lib'), ('force', 'force')
        )

        # Get the distribution options that are aliases for build_py
        # options -- list of packages and list of modules.
        self.packages = self.distribution.packages
        self.py_modules = self.distribution.py_modules
        self.package_data = self.distribution.package_data
        self.package_dir = {}
        if self.distribution.package_dir:
            for name, path in self.distribution.package_dir.items():
                self.package_dir[name] = convert_path(path)
        self.data_files = self.get_data_files()

        # Ick, copied straight from install_lib.py (fancy_getopt needs a
        # type system!  Hell, *everything* needs a type system!!!)
        if not isinstance(self.optimize, int):
            try:
                self.optimize = int(self.optimize)
                assert 0 <= self.optimize <= 2
            except (ValueError, AssertionError):
                raise DistutilsOptionError("optimize must be 0, 1, or 2")

    def run(self) -> None:
        # XXX copy_file by default preserves atime and mtime.  IMHO this is
        # the right thing to do, but perhaps it should be an option -- in
        # particular, a site administrator might want installed files to
        # reflect the time of installation rather than the last
        # modification time before the installed release.

        # XXX copy_file by default preserves mode, which appears to be the
        # wrong thing to do: if a file is read-only in the working
        # directory, we want it to be installed read/write so that the next
        # installation of the same module distribution can overwrite it
        # without problems.  (This might be a Unix-specific issue.)  Thus
        # we turn off 'preserve_mode' when copying to the build directory,
        # since the build directory is supposed to be exactly what the
        # installation will look like (ie. we preserve mode when
        # installing).

        # Two options control which modules will be installed: 'packages'
        # and 'py_modules'.  The former lets us work with whole packages, not
        # specifying individual modules at all; the latter is for
        # specifying modules one-at-a-time.

        if self.py_modules:
            self.build_modules()
        if self.packages:
            self.build_packages()
            self.build_package_data()

        self.byte_compile(self.get_outputs(include_bytecode=False))

    def get_data_files(self):
        """Generate list of '(package,src_dir,build_dir,filenames)' tuples"""
        data = []
        if not self.packages:
            return data
        for package in self.packages:
            # Locate package source directory
            src_dir = self.get_package_dir(package)

            # Compute package build directory
            build_dir = os.path.join(*([self.build_lib] + package.split('.')))

            # Length of path to strip from found files
            plen = 0
            if src_dir:
                plen = len(src_dir) + 1

            # Strip directory from globbed filenames
            filenames = [file[plen:] for file in self.find_data_files(package, src_dir)]
            data.append((package, src_dir, build_dir, filenames))
        return data

    def find_data_files(self, package, src_dir):
        """Return filenames for package's data files in 'src_dir'"""
        globs = self.package_data.get('', []) + self.package_data.get(package, [])
        files = []
        for pattern in globs:
            # Each pattern has to be converted to a platform-specific path
            filelist = glob.glob(
                os.path.join(glob.escape(src_dir), convert_path(pattern))
            )
            # Files that match more than one pattern are only added once
            files.extend([
                fn for fn in filelist if fn not in files and os.path.isfile(fn)
            ])
        return files

    def build_package_data(self) -> None:
        """Copy data files into build directory"""
        for _package, src_dir, build_dir, filenames in self.data_files:
            for filename in filenames:
                target = os.path.join(build_dir, filename)
                self.mkpath(os.path.dirname(target))
                self.copy_file(
                    os.path.join(src_dir, filename), target, preserve_mode=False
                )

    def get_package_dir(self, package):
        """Return the directory, relative to the top of the source
        distribution, where package 'package' should be found
        (at least according to the 'package_dir' option, if any)."""
        path = package.split('.')

        if not self.package_dir:
            if path:
                return os.path.join(*path)
            else:
                return ''
        else:
            tail = []
            while path:
                try:
                    pdir = self.package_dir['.'.join(path)]
                except KeyError:
                    tail.insert(0, path[-1])
                    del path[-1]
                else:
                    tail.insert(0, pdir)
                    return os.path.join(*tail)
            else:
                # Oops, got all the way through 'path' without finding a
                # match in package_dir.  If package_dir defines a directory
                # for the root (nameless) package, then fallback on it;
                # otherwise, we might as well have not consulted
                # package_dir at all, as we just use the directory implied
                # by 'tail' (which should be the same as the original value
                # of 'path' at this point).
                pdir = self.package_dir.get('')
                if pdir is not None:
                    tail.insert(0, pdir)

                if tail:
                    return os.path.join(*tail)
                else:
                    return ''

    def check_package(self, package, package_dir):
        # Empty dir name means current directory, which we can probably
        # assume exists.  Also, os.path.exists and isdir don't know about
        # my "empty string means current dir" convention, so we have to
        # circumvent them.
        if package_dir != "":
            if not os.path.exists(package_dir):
                raise DistutilsFileError(
                    f"package directory '{package_dir}' does not exist"
                )
            if not os.path.isdir(package_dir):
                raise DistutilsFileError(
                    f"supposed package directory '{package_dir}' exists, "
                    "but is not a directory"
                )

        # Directories without __init__.py are namespace packages (PEP 420).
        if package:
            init_py = os.path.join(package_dir, "__init__.py")
            if os.path.isfile(init_py):
                return init_py

        # Either not in a package at all (__init__.py not expected), or
        # __init__.py doesn't exist -- so don't return the filename.
        return None

    def check_module(self, module, module_file):
        if not os.path.isfile(module_file):
            log.warning("file %s (for module %s) not found", module_file, module)
            return False
        else:
            return True

    def find_package_modules(self, package, package_dir):
        self.check_package(package, package_dir)
        module_files = glob.glob(os.path.join(glob.escape(package_dir), "*.py"))
        modules = []
        setup_script = os.path.abspath(self.distribution.script_name)

        for f in module_files:
            abs_f = os.path.abspath(f)
            if abs_f != setup_script:
                module = os.path.splitext(os.path.basename(f))[0]
                modules.append((package, module, f))
            else:
                self.debug_print(f"excluding {setup_script}")
        return modules

    def find_modules(self):
        """Finds individually-specified Python modules, ie. those listed by
        module name in 'self.py_modules'.  Returns a list of tuples (package,
        module_base, filename): 'package' is a tuple of the path through
        package-space to the module; 'module_base' is the bare (no
        packages, no dots) module name, and 'filename' is the path to the
        ".py" file (relative to the distribution root) that implements the
        module.
        """
        # Map package names to tuples of useful info about the package:
        #    (package_dir, checked)
        # package_dir - the directory where we'll find source files for
        #   this package
        # checked - true if we have checked that the package directory
        #   is valid (exists, contains __init__.py, ... ?)
        packages = {}

        # List of (package, module, filename) tuples to return
        modules = []

        # We treat modules-in-packages almost the same as toplevel modules,
        # just the "package" for a toplevel is empty (either an empty
        # string or empty list, depending on context).  Differences:
        #   - don't check for __init__.py in directory for empty package
        for module in self.py_modules:
            path = module.split('.')
            package = '.'.join(path[0:-1])
            module_base = path[-1]

            try:
                (package_dir, checked) = packages[package]
            except KeyError:
                package_dir = self.get_package_dir(package)
                checked = False

            if not checked:
                init_py = self.check_package(package, package_dir)
                packages[package] = (package_dir, 1)
                if init_py:
                    modules.append((package, "__init__", init_py))

            # XXX perhaps we should also check for just .pyc files
            # (so greedy closed-source bastards can distribute Python
            # modules too)
            module_file = os.path.join(package_dir, module_base + ".py")
            if not self.check_module(module, module_file):
                continue

            modules.append((package, module_base, module_file))

        return modules

    def find_all_modules(self):
        """Compute the list of all modules that will be built, whether
        they are specified one-module-at-a-time ('self.py_modules') or
        by whole packages ('self.packages').  Return a list of tuples
        (package, module, module_file), just like 'find_modules()' and
        'find_package_modules()' do."""
        modules = []
        if self.py_modules:
            modules.extend(self.find_modules())
        if self.packages:
            for package in self.packages:
                package_dir = self.get_package_dir(package)
                m = self.find_package_modules(package, package_dir)
                modules.extend(m)
        return modules

    def get_source_files(self):
        return [module[-1] for module in self.find_all_modules()]

    def get_module_outfile(self, build_dir, package, module):
        outfile_path = [build_dir] + list(package) + [module + ".py"]
        return os.path.join(*outfile_path)

    def get_outputs(self, include_bytecode: bool = True) -> list[str]:
        modules = self.find_all_modules()
        outputs = []
        for package, module, _module_file in modules:
            package = package.split('.')
            filename = self.get_module_outfile(self.build_lib, package, module)
            outputs.append(filename)
            if include_bytecode:
                if self.compile:
                    outputs.append(
                        importlib.util.cache_from_source(filename, optimization='')
                    )
                if self.optimize > 0:
                    outputs.append(
                        importlib.util.cache_from_source(
                            filename, optimization=self.optimize
                        )
                    )

        outputs += [
            os.path.join(build_dir, filename)
            for package, src_dir, build_dir, filenames in self.data_files
            for filename in filenames
        ]

        return outputs

    def build_module(self, module, module_file, package):
        if isinstance(package, str):
            package = package.split('.')
        elif not isinstance(package, (list, tuple)):
            raise TypeError(
                "'package' must be a string (dot-separated), list, or tuple"
            )

        # Now put the module source file into the "build" area -- this is
        # easy, we just copy it somewhere under self.build_lib (the build
        # directory for Python source).
        outfile = self.get_module_outfile(self.build_lib, package, module)
        dir = os.path.dirname(outfile)
        self.mkpath(dir)
        return self.copy_file(module_file, outfile, preserve_mode=False)

    def build_modules(self) -> None:
        modules = self.find_modules()
        for package, module, module_file in modules:
            # Now "build" the module -- ie. copy the source file to
            # self.build_lib (the build directory for Python source).
            # (Actually, it gets copied to the directory for this package
            # under self.build_lib.)
            self.build_module(module, module_file, package)

    def build_packages(self) -> None:
        for package in self.packages:
            # Get list of (package, module, module_file) tuples based on
            # scanning the package directory.  'package' is only included
            # in the tuple so that 'find_modules()' and
            # 'find_package_tuples()' have a consistent interface; it's
            # ignored here (apart from a sanity check).  Also, 'module' is
            # the *unqualified* module name (ie. no dots, no package -- we
            # already know its package!), and 'module_file' is the path to
            # the .py file, relative to the current directory
            # (ie. including 'package_dir').
            package_dir = self.get_package_dir(package)
            modules = self.find_package_modules(package, package_dir)

            # Now loop over the modules we found, "building" each one (just
            # copy it to self.build_lib).
            for package_, module, module_file in modules:
                assert package == package_
                self.build_module(module, module_file, package)

    def byte_compile(self, files) -> None:
        if sys.dont_write_bytecode:
            self.warn('byte-compiling is disabled, skipping.')
            return

        from ..util import byte_compile

        prefix = self.build_lib
        if prefix[-1] != os.sep:
            prefix = prefix + os.sep

        # XXX this code is essentially the same as the 'byte_compile()
        # method of the "install_lib" command, except for the determination
        # of the 'prefix' string.  Hmmm.
        if self.compile:
            byte_compile(
                files, optimize=0, force=self.force, prefix=prefix, dry_run=self.dry_run
            )
        if self.optimize > 0:
            byte_compile(
                files,
                optimize=self.optimize,
                force=self.force,
                prefix=prefix,
                dry_run=self.dry_run,
            )

# === NexusCore/openenv\Lib\site-packages\httpx\_transports\default.py ===
"""
Custom transports, with nicely configured defaults.

The following additional keyword arguments are currently supported by httpcore...

* uds: str
* local_address: str
* retries: int

Example usages...

# Disable HTTP/2 on a single specific domain.
mounts = {
    "all://": httpx.HTTPTransport(http2=True),
    "all://*example.org": httpx.HTTPTransport()
}

# Using advanced httpcore configuration, with connection retries.
transport = httpx.HTTPTransport(retries=1)
client = httpx.Client(transport=transport)

# Using advanced httpcore configuration, with unix domain sockets.
transport = httpx.HTTPTransport(uds="socket.uds")
client = httpx.Client(transport=transport)
"""

from __future__ import annotations

import contextlib
import typing
from types import TracebackType

if typing.TYPE_CHECKING:
    import ssl  # pragma: no cover

    import httpx  # pragma: no cover

from .._config import DEFAULT_LIMITS, Limits, Proxy, create_ssl_context
from .._exceptions import (
    ConnectError,
    ConnectTimeout,
    LocalProtocolError,
    NetworkError,
    PoolTimeout,
    ProtocolError,
    ProxyError,
    ReadError,
    ReadTimeout,
    RemoteProtocolError,
    TimeoutException,
    UnsupportedProtocol,
    WriteError,
    WriteTimeout,
)
from .._models import Request, Response
from .._types import AsyncByteStream, CertTypes, ProxyTypes, SyncByteStream
from .._urls import URL
from .base import AsyncBaseTransport, BaseTransport

T = typing.TypeVar("T", bound="HTTPTransport")
A = typing.TypeVar("A", bound="AsyncHTTPTransport")

SOCKET_OPTION = typing.Union[
    typing.Tuple[int, int, int],
    typing.Tuple[int, int, typing.Union[bytes, bytearray]],
    typing.Tuple[int, int, None, int],
]

__all__ = ["AsyncHTTPTransport", "HTTPTransport"]

HTTPCORE_EXC_MAP: dict[type[Exception], type[httpx.HTTPError]] = {}


def _load_httpcore_exceptions() -> dict[type[Exception], type[httpx.HTTPError]]:
    import httpcore

    return {
        httpcore.TimeoutException: TimeoutException,
        httpcore.ConnectTimeout: ConnectTimeout,
        httpcore.ReadTimeout: ReadTimeout,
        httpcore.WriteTimeout: WriteTimeout,
        httpcore.PoolTimeout: PoolTimeout,
        httpcore.NetworkError: NetworkError,
        httpcore.ConnectError: ConnectError,
        httpcore.ReadError: ReadError,
        httpcore.WriteError: WriteError,
        httpcore.ProxyError: ProxyError,
        httpcore.UnsupportedProtocol: UnsupportedProtocol,
        httpcore.ProtocolError: ProtocolError,
        httpcore.LocalProtocolError: LocalProtocolError,
        httpcore.RemoteProtocolError: RemoteProtocolError,
    }


@contextlib.contextmanager
def map_httpcore_exceptions() -> typing.Iterator[None]:
    global HTTPCORE_EXC_MAP
    if len(HTTPCORE_EXC_MAP) == 0:
        HTTPCORE_EXC_MAP = _load_httpcore_exceptions()
    try:
        yield
    except Exception as exc:
        mapped_exc = None

        for from_exc, to_exc in HTTPCORE_EXC_MAP.items():
            if not isinstance(exc, from_exc):
                continue
            # We want to map to the most specific exception we can find.
            # Eg if `exc` is an `httpcore.ReadTimeout`, we want to map to
            # `httpx.ReadTimeout`, not just `httpx.TimeoutException`.
            if mapped_exc is None or issubclass(to_exc, mapped_exc):
                mapped_exc = to_exc

        if mapped_exc is None:  # pragma: no cover
            raise

        message = str(exc)
        raise mapped_exc(message) from exc


class ResponseStream(SyncByteStream):
    def __init__(self, httpcore_stream: typing.Iterable[bytes]) -> None:
        self._httpcore_stream = httpcore_stream

    def __iter__(self) -> typing.Iterator[bytes]:
        with map_httpcore_exceptions():
            for part in self._httpcore_stream:
                yield part

    def close(self) -> None:
        if hasattr(self._httpcore_stream, "close"):
            self._httpcore_stream.close()


class HTTPTransport(BaseTransport):
    def __init__(
        self,
        verify: ssl.SSLContext | str | bool = True,
        cert: CertTypes | None = None,
        trust_env: bool = True,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        proxy: ProxyTypes | None = None,
        uds: str | None = None,
        local_address: str | None = None,
        retries: int = 0,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> None:
        import httpcore

        proxy = Proxy(url=proxy) if isinstance(proxy, (str, URL)) else proxy
        ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

        if proxy is None:
            self._pool = httpcore.ConnectionPool(
                ssl_context=ssl_context,
                max_connections=limits.max_connections,
                max_keepalive_connections=limits.max_keepalive_connections,
                keepalive_expiry=limits.keepalive_expiry,
                http1=http1,
                http2=http2,
                uds=uds,
                local_address=local_address,
                retries=retries,
                socket_options=socket_options,
            )
        elif proxy.url.scheme in ("http", "https"):
            self._pool = httpcore.HTTPProxy(
                proxy_url=httpcore.URL(
                    scheme=proxy.url.raw_scheme,
                    host=proxy.url.raw_host,
                    port=proxy.url.port,
                    target=proxy.url.raw_path,
                ),
                proxy_auth=proxy.raw_auth,
                proxy_headers=proxy.headers.raw,
                ssl_context=ssl_context,
                proxy_ssl_context=proxy.ssl_context,
                max_connections=limits.max_connections,
                max_keepalive_connections=limits.max_keepalive_connections,
                keepalive_expiry=limits.keepalive_expiry,
                http1=http1,
                http2=http2,
                socket_options=socket_options,
            )
        elif proxy.url.scheme in ("socks5", "socks5h"):
            try:
                import socksio  # noqa
            except ImportError:  # pragma: no cover
                raise ImportError(
                    "Using SOCKS proxy, but the 'socksio' package is not installed. "
                    "Make sure to install httpx using `pip install httpx[socks]`."
                ) from None

            self._pool = httpcore.SOCKSProxy(
                proxy_url=httpcore.URL(
                    scheme=proxy.url.raw_scheme,
                    host=proxy.url.raw_host,
                    port=proxy.url.port,
                    target=proxy.url.raw_path,
                ),
                proxy_auth=proxy.raw_auth,
                ssl_context=ssl_context,
                max_connections=limits.max_connections,
                max_keepalive_connections=limits.max_keepalive_connections,
                keepalive_expiry=limits.keepalive_expiry,
                http1=http1,
                http2=http2,
            )
        else:  # pragma: no cover
            raise ValueError(
                "Proxy protocol must be either 'http', 'https', 'socks5', or 'socks5h',"
                f" but got {proxy.url.scheme!r}."
            )

    def __enter__(self: T) -> T:  # Use generics for subclass support.
        self._pool.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        with map_httpcore_exceptions():
            self._pool.__exit__(exc_type, exc_value, traceback)

    def handle_request(
        self,
        request: Request,
    ) -> Response:
        assert isinstance(request.stream, SyncByteStream)
        import httpcore

        req = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )
        with map_httpcore_exceptions():
            resp = self._pool.handle_request(req)

        assert isinstance(resp.stream, typing.Iterable)

        return Response(
            status_code=resp.status,
            headers=resp.headers,
            stream=ResponseStream(resp.stream),
            extensions=resp.extensions,
        )

    def close(self) -> None:
        self._pool.close()


class AsyncResponseStream(AsyncByteStream):
    def __init__(self, httpcore_stream: typing.AsyncIterable[bytes]) -> None:
        self._httpcore_stream = httpcore_stream

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        with map_httpcore_exceptions():
            async for part in self._httpcore_stream:
                yield part

    async def aclose(self) -> None:
        if hasattr(self._httpcore_stream, "aclose"):
            await self._httpcore_stream.aclose()


class AsyncHTTPTransport(AsyncBaseTransport):
    def __init__(
        self,
        verify: ssl.SSLContext | str | bool = True,
        cert: CertTypes | None = None,
        trust_env: bool = True,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        proxy: ProxyTypes | None = None,
        uds: str | None = None,
        local_address: str | None = None,
        retries: int = 0,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> None:
        import httpcore

        proxy = Proxy(url=proxy) if isinstance(proxy, (str, URL)) else proxy
        ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

        if proxy is None:
            self._pool = httpcore.AsyncConnectionPool(
                ssl_context=ssl_context,
                max_connections=limits.max_connections,
                max_keepalive_connections=limits.max_keepalive_connections,
                keepalive_expiry=limits.keepalive_expiry,
                http1=http1,
                http2=http2,
                uds=uds,
                local_address=local_address,
                retries=retries,
                socket_options=socket_options,
            )
        elif proxy.url.scheme in ("http", "https"):
            self._pool = httpcore.AsyncHTTPProxy(
                proxy_url=httpcore.URL(
                    scheme=proxy.url.raw_scheme,
                    host=proxy.url.raw_host,
                    port=proxy.url.port,
                    target=proxy.url.raw_path,
                ),
                proxy_auth=proxy.raw_auth,
                proxy_headers=proxy.headers.raw,
                proxy_ssl_context=proxy.ssl_context,
                ssl_context=ssl_context,
                max_connections=limits.max_connections,
                max_keepalive_connections=limits.max_keepalive_connections,
                keepalive_expiry=limits.keepalive_expiry,
                http1=http1,
                http2=http2,
                socket_options=socket_options,
            )
        elif proxy.url.scheme in ("socks5", "socks5h"):
            try:
                import socksio  # noqa
            except ImportError:  # pragma: no cover
                raise ImportError(
                    "Using SOCKS proxy, but the 'socksio' package is not installed. "
                    "Make sure to install httpx using `pip install httpx[socks]`."
                ) from None

            self._pool = httpcore.AsyncSOCKSProxy(
                proxy_url=httpcore.URL(
                    scheme=proxy.url.raw_scheme,
                    host=proxy.url.raw_host,
                    port=proxy.url.port,
                    target=proxy.url.raw_path,
                ),
                proxy_auth=proxy.raw_auth,
                ssl_context=ssl_context,
                max_connections=limits.max_connections,
                max_keepalive_connections=limits.max_keepalive_connections,
                keepalive_expiry=limits.keepalive_expiry,
                http1=http1,
                http2=http2,
            )
        else:  # pragma: no cover
            raise ValueError(
                "Proxy protocol must be either 'http', 'https', 'socks5', or 'socks5h',"
                " but got {proxy.url.scheme!r}."
            )

    async def __aenter__(self: A) -> A:  # Use generics for subclass support.
        await self._pool.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        with map_httpcore_exceptions():
            await self._pool.__aexit__(exc_type, exc_value, traceback)

    async def handle_async_request(
        self,
        request: Request,
    ) -> Response:
        assert isinstance(request.stream, AsyncByteStream)
        import httpcore

        req = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )
        with map_httpcore_exceptions():
            resp = await self._pool.handle_async_request(req)

        assert isinstance(resp.stream, typing.AsyncIterable)

        return Response(
            status_code=resp.status,
            headers=resp.headers,
            stream=AsyncResponseStream(resp.stream),
            extensions=resp.extensions,
        )

    async def aclose(self) -> None:
        await self._pool.aclose()

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\wgsl.py ===
"""
    pygments.lexers.wgsl
    ~~~~~~~~~~~~~~~~~~~~

    Lexer for the WebGPU Shading Language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, words, default
from pygments.token import Comment, Operator, Keyword, Name, \
    Number, Punctuation, Whitespace
from pygments import unistring as uni

__all__ = ['WgslLexer']

LF = '\\u000a'
VT = '\\u000b'
FF = '\\u000c'
CR = '\\u000d'
NextLine = '\\u0085'
LineSep = '\\u2028'
ParaSep = '\\u2029'
LineEndCodePoints = [LF,VT,FF,CR,NextLine,LineSep,ParaSep]
NotLineEndRE = '[^' + "".join(LineEndCodePoints) + ']'
LineEndRE = '[' + "".join(LineEndCodePoints) + ']'

# https://www.w3.org/TR/WGSL/#syntax-ident_pattern_token
ident_pattern_token = f'([{uni.xid_start}][{uni.xid_continue}]+)|[{uni.xid_start}]'


class WgslLexer(RegexLexer):
    """
    Lexer for the WebGPU Shading Language.
    """
    name = 'WebGPU Shading Language'
    url = 'https://www.w3.org/TR/WGSL/'
    aliases = ['wgsl']
    filenames = ['*.wgsl']
    mimetypes = ['text/wgsl']
    version_added = '2.15'

    # https://www.w3.org/TR/WGSL/#var-and-value
    keyword_decl = (words('var let const override'.split(),suffix=r'\b'), Keyword.Declaration)
    # https://www.w3.org/TR/WGSL/#keyword-summary
    keywords = (words("""
                alias
                break
                case
                const_assert
                continue
                continuing
                default
                diagnostic
                discard
                else
                enable
                false
                fn
                for
                if
                loop
                requires
                return
                struct
                switch
                true
                while
                """.split(), suffix=r'\b'), Keyword)

    # https://www.w3.org/TR/WGSL/#reserved-words
    keyword_reserved = (words("""
                NULL
                Self
                abstract
                active
                alignas
                alignof
                as
                asm
                asm_fragment
                async
                attribute
                auto
                await
                become
                binding_array
                cast
                catch
                class
                co_await
                co_return
                co_yield
                coherent
                column_major
                common
                compile
                compile_fragment
                concept
                const_cast
                consteval
                constexpr
                constinit
                crate
                debugger
                decltype
                delete
                demote
                demote_to_helper
                do
                dynamic_cast
                enum
                explicit
                export
                extends
                extern
                external
                fallthrough
                filter
                final
                finally
                friend
                from
                fxgroup
                get
                goto
                groupshared
                highp
                impl
                implements
                import
                inline
                instanceof
                interface
                layout
                lowp
                macro
                macro_rules
                match
                mediump
                meta
                mod
                module
                move
                mut
                mutable
                namespace
                new
                nil
                noexcept
                noinline
                nointerpolation
                noperspective
                null
                nullptr
                of
                operator
                package
                packoffset
                partition
                pass
                patch
                pixelfragment
                precise
                precision
                premerge
                priv
                protected
                pub
                public
                readonly
                ref
                regardless
                register
                reinterpret_cast
                require
                resource
                restrict
                self
                set
                shared
                sizeof
                smooth
                snorm
                static
                static_assert
                static_cast
                std
                subroutine
                super
                target
                template
                this
                thread_local
                throw
                trait
                try
                type
                typedef
                typeid
                typename
                typeof
                union
                unless
                unorm
                unsafe
                unsized
                use
                using
                varying
                virtual
                volatile
                wgsl
                where
                with
                writeonly
                yield
                """.split(), suffix=r'\b'), Keyword.Reserved)

    # https://www.w3.org/TR/WGSL/#predeclared-enumerants
    predeclared_enums = (words("""
          read write read_write
          function private workgroup uniform storage
          perspective linear flat
          center centroid sample
          vertex_index instance_index position front_facing frag_depth
              local_invocation_id local_invocation_index
              global_invocation_id workgroup_id num_workgroups
              sample_index sample_mask
          rgba8unorm
          rgba8snorm
          rgba8uint
          rgba8sint
          rgba16uint
          rgba16sint
          rgba16float
          r32uint
          r32sint
          r32float
          rg32uint
          rg32sint
          rg32float
          rgba32uint
          rgba32sint
          rgba32float
          bgra8unorm
          """.split(), suffix=r'\b'), Name.Builtin)

    # https://www.w3.org/TR/WGSL/#predeclared-types
    predeclared_types = (words("""
          bool
          f16
          f32
          i32
          sampler sampler_comparison
          texture_depth_2d
          texture_depth_2d_array
          texture_depth_cube
          texture_depth_cube_array
          texture_depth_multisampled_2d
          texture_external
          texture_external
          u32
          """.split(), suffix=r'\b'), Name.Builtin)

    # https://www.w3.org/TR/WGSL/#predeclared-types
    predeclared_type_generators = (words("""
          array
          atomic
          mat2x2
          mat2x3
          mat2x4
          mat3x2
          mat3x3
          mat3x4
          mat4x2
          mat4x3
          mat4x4
          ptr
          texture_1d
          texture_2d
          texture_2d_array
          texture_3d
          texture_cube
          texture_cube_array
          texture_multisampled_2d
          texture_storage_1d
          texture_storage_2d
          texture_storage_2d_array
          texture_storage_3d
          vec2
          vec3
          vec4
          """.split(), suffix=r'\b'), Name.Builtin)

    # Predeclared type aliases for vectors
    # https://www.w3.org/TR/WGSL/#vector-types
    predeclared_type_alias_vectors = (words("""
          vec2i vec3i vec4i
          vec2u vec3u vec4u
          vec2f vec3f vec4f
          vec2h vec3h vec4h
          """.split(), suffix=r'\b'), Name.Builtin)

    # Predeclared type aliases for matrices
    # https://www.w3.org/TR/WGSL/#matrix-types
    predeclared_type_alias_matrices = (words("""
          mat2x2f mat2x3f mat2x4f
          mat3x2f mat3x3f mat3x4f
          mat4x2f mat4x3f mat4x4f
          mat2x2h mat2x3h mat2x4h
          mat3x2h mat3x3h mat3x4h
          mat4x2h mat4x3h mat4x4h
          """.split(), suffix=r'\b'), Name.Builtin)

    tokens = {
        'blankspace': [
            # https://www.w3.org/TR/WGSL/#blankspace
            (r'[\u0020\u0009\u000a\u000b\u000c\u000d\u0085\u200e\u200f\u2028\u2029]+', Whitespace),
        ],
        'comments': [
            # Line ending comments
            # Match up CR/LF pair first.
            (rf'//{NotLineEndRE}*{CR}{LF}', Comment.Single),
            (rf'//{NotLineEndRE}*{LineEndRE}', Comment.Single),
            (r'/\*', Comment.Multiline, 'block_comment'),
        ],
        'attribute': [
            include('blankspace'),
            include('comments'),
            (ident_pattern_token, Name.Decorator,'#pop'),
            default('#pop'),
        ],
        'root': [
            include('blankspace'),
            include('comments'),

            # Attributes.
            # https://www.w3.org/TR/WGSL/#attributes
            # Mark the '@' and the attribute name as a decorator.
            (r'@', Name.Decorator, 'attribute'),

            # Keywords
            (r'(true|false)\b', Keyword.Constant),
            keyword_decl,
            keywords,
            keyword_reserved,

            # Predeclared
            predeclared_enums,
            predeclared_types,
            predeclared_type_generators,
            predeclared_type_alias_vectors,
            predeclared_type_alias_matrices,

            # Decimal float literals
            # https://www.w3.org/TR/WGSL/#syntax-decimal_float_literal
            # 0, with type-specifying suffix.
            (r'0[fh]', Number.Float),
            # Other decimal integer, with type-specifying suffix.
            (r'[1-9][0-9]*[fh]', Number.Float),
            #    Has decimal point, at least one digit after decimal.
            (r'[0-9]*\.[0-9]+([eE][+-]?[0-9]+)?[fh]?', Number.Float),
            #    Has decimal point, at least one digit before decimal.
            (r'[0-9]+\.[0-9]*([eE][+-]?[0-9]+)?[fh]?', Number.Float),
            #    Has at least one digit, and has an exponent.
            (r'[0-9]+[eE][+-]?[0-9]+[fh]?', Number.Float),

            # Hex float literals
            # https://www.w3.org/TR/WGSL/#syntax-hex_float_literal
            (r'0[xX][0-9a-fA-F]*\.[0-9a-fA-F]+([pP][+-]?[0-9]+[fh]?)?', Number.Float),
            (r'0[xX][0-9a-fA-F]+\.[0-9a-fA-F]*([pP][+-]?[0-9]+[fh]?)?', Number.Float),
            (r'0[xX][0-9a-fA-F]+[pP][+-]?[0-9]+[fh]?', Number.Float),

            # Hexadecimal integer literals
            # https://www.w3.org/TR/WGSL/#syntax-hex_int_literal
            (r'0[xX][0-9a-fA-F]+[iu]?', Number.Hex),
            # Decimal integer literals
            # https://www.w3.org/TR/WGSL/#syntax-decimal_int_literal
            # We need two rules here because 01 is not valid.
            (r'[1-9][0-9]*[iu]?', Number.Integer),
            (r'0[iu]?', Number.Integer), # Must match last.

            # Operators and Punctuation
            (r'[{}()\[\],\.;:]', Punctuation),
            (r'->', Punctuation), # Return-type arrow
            (r'[+\-*/%&|<>^!~=]', Operator),

            # TODO: Treat context-depedendent names specially
            # https://www.w3.org/TR/WGSL/#context-dependent-name

            # Identifiers
            (ident_pattern_token, Name),

            # TODO: templates start and end tokens.
            # https://www.w3.org/TR/WGSL/#template-lists-sec
        ],
        'block_comment': [
            # https://www.w3.org/TR/WGSL/#block-comment
            (r'[^*/]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\trio\_highlevel_open_tcp_stream.py ===
from __future__ import annotations

import sys
from contextlib import contextmanager, suppress
from typing import TYPE_CHECKING, Any

import trio
from trio.socket import SOCK_STREAM, SocketType, getaddrinfo, socket

if TYPE_CHECKING:
    from collections.abc import Generator, MutableSequence
    from socket import AddressFamily, SocketKind

    from trio._socket import AddressFormat

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup


# Implementation of RFC 6555 "Happy eyeballs"
# https://tools.ietf.org/html/rfc6555
#
# Basically, the problem here is that if we want to connect to some host, and
# DNS returns multiple IP addresses, then we don't know which of them will
# actually work -- it can happen that some of them are reachable, and some of
# them are not. One particularly common situation where this happens is on a
# host that thinks it has ipv6 connectivity, but really doesn't. But in
# principle this could happen for any kind of multi-home situation (e.g. the
# route to one mirror is down but another is up).
#
# The naive algorithm (e.g. the stdlib's socket.create_connection) would be to
# pick one of the IP addresses and try to connect; if that fails, try the
# next; etc. The problem with this is that TCP is stubborn, and if the first
# address is a blackhole then it might take a very long time (tens of seconds)
# before that connection attempt fails.
#
# That's where RFC 6555 comes in. It tells us that what we do is:
# - get the list of IPs from getaddrinfo, trusting the order it gives us (with
#   one exception noted in section 5.4)
# - start a connection attempt to the first IP
# - when this fails OR if it's still going after DELAY seconds, then start a
#   connection attempt to the second IP
# - when this fails OR if it's still going after another DELAY seconds, then
#   start a connection attempt to the third IP
# - ... repeat until we run out of IPs.
#
# Our implementation is similarly straightforward: we spawn a chain of tasks,
# where each one (a) waits until the previous connection has failed or DELAY
# seconds have passed, (b) spawns the next task, (c) attempts to connect. As
# soon as any task crashes or succeeds, we cancel all the tasks and return.
#
# Note: this currently doesn't attempt to cache any results, so if you make
# multiple connections to the same host it'll re-run the happy-eyeballs
# algorithm each time. RFC 6555 is pretty confusing about whether this is
# allowed. Section 4 describes an algorithm that attempts ipv4 and ipv6
# simultaneously, and then says "The client MUST cache information regarding
# the outcome of each connection attempt, and it uses that information to
# avoid thrashing the network with subsequent attempts." Then section 4.2 says
# "implementations MUST prefer the first IP address family returned by the
# host's address preference policy, unless implementing a stateful
# algorithm". Here "stateful" means "one that caches information about
# previous attempts". So my reading of this is that IF you're starting ipv4
# and ipv6 at the same time then you MUST cache the result for ~ten minutes,
# but IF you're "preferring" one protocol by trying it first (like we are),
# then you don't need to cache.
#
# Caching is quite tricky: to get it right you need to do things like detect
# when the network interfaces are reconfigured, and if you get it wrong then
# connection attempts basically just don't work. So we don't even try.

# "Firefox and Chrome use 300 ms"
# https://tools.ietf.org/html/rfc6555#section-6
# Though
#   https://www.researchgate.net/profile/Vaibhav_Bajpai3/publication/304568993_Measuring_the_Effects_of_Happy_Eyeballs/links/5773848e08ae6f328f6c284c/Measuring-the-Effects-of-Happy-Eyeballs.pdf
# claims that Firefox actually uses 0 ms, unless an about:config option is
# toggled and then it uses 250 ms.
DEFAULT_DELAY = 0.250

# How should we call getaddrinfo? In particular, should we use AI_ADDRCONFIG?
#
# The idea of AI_ADDRCONFIG is that it only returns addresses that might
# work. E.g., if getaddrinfo knows that you don't have any IPv6 connectivity,
# then it doesn't return any IPv6 addresses. And this is kinda nice, because
# it means maybe you can skip sending AAAA requests entirely. But in practice,
# it doesn't really work right.
#
# - on Linux/glibc, empirically, the default is to return all addresses, and
# with AI_ADDRCONFIG then it only returns IPv6 addresses if there is at least
# one non-loopback IPv6 address configured... but this can be a link-local
# address, so in practice I guess this is basically always configured if IPv6
# is enabled at all. OTOH if you pass in "::1" as the target address with
# AI_ADDRCONFIG and there's no *external* IPv6 address configured, you get an
# error. So AI_ADDRCONFIG mostly doesn't do anything, even when you would want
# it to, and when it does do something it might break things that would have
# worked.
#
# - on Windows 10, empirically, if no IPv6 address is configured then by
# default they are also suppressed from getaddrinfo (flags=0 and
# flags=AI_ADDRCONFIG seem to do the same thing). If you pass AI_ALL, then you
# get the full list.
# ...except for localhost! getaddrinfo("localhost", "80") gives me ::1, even
# though there's no ipv6 and other queries only return ipv4.
# If you pass in and IPv6 IP address as the target address, then that's always
# returned OK, even with AI_ADDRCONFIG set and no IPv6 configured.
#
# But I guess other versions of windows messed this up, judging from these bug
# reports:
# https://bugs.chromium.org/p/chromium/issues/detail?id=5234
# https://bugs.chromium.org/p/chromium/issues/detail?id=32522#c50
#
# So basically the options are either to use AI_ADDRCONFIG and then add some
# complicated special cases to work around its brokenness, or else don't use
# AI_ADDRCONFIG and accept that sometimes on legacy/misconfigured networks
# we'll waste 300 ms trying to connect to a blackholed destination.
#
# Twisted and Tornado always uses default flags. I think we'll do the same.


@contextmanager
def close_all() -> Generator[set[SocketType], None, None]:
    sockets_to_close: set[SocketType] = set()
    try:
        yield sockets_to_close
    finally:
        errs = []
        for sock in sockets_to_close:
            try:
                sock.close()
            except BaseException as exc:
                errs.append(exc)
        if len(errs) == 1:
            raise errs[0]
        elif errs:
            raise BaseExceptionGroup("", errs)


def reorder_for_rfc_6555_section_5_4(  # type: ignore[explicit-any]
    targets: MutableSequence[tuple[AddressFamily, SocketKind, int, str, Any]],
) -> None:
    # RFC 6555 section 5.4 says that if getaddrinfo returns multiple address
    # families (e.g. IPv4 and IPv6), then you should make sure that your first
    # and second attempts use different families:
    #
    #    https://tools.ietf.org/html/rfc6555#section-5.4
    #
    # This function post-processes the results from getaddrinfo, in-place, to
    # satisfy this requirement.
    for i in range(1, len(targets)):
        if targets[i][0] != targets[0][0]:
            # Found the first entry with a different address family; move it
            # so that it becomes the second item on the list.
            if i != 1:
                targets.insert(1, targets.pop(i))
            break


def format_host_port(host: str | bytes, port: int | str) -> str:
    host = host.decode("ascii") if isinstance(host, bytes) else host
    if ":" in host:
        return f"[{host}]:{port}"
    else:
        return f"{host}:{port}"


# Twisted's HostnameEndpoint has a good set of configurables:
#   https://twistedmatrix.com/documents/current/api/twisted.internet.endpoints.HostnameEndpoint.html
#
# - per-connection timeout
#   this doesn't seem useful -- we let you set a timeout on the whole thing
#   using Trio's normal mechanisms, and that seems like enough
# - delay between attempts
# - bind address (but not port!)
#   they *don't* support multiple address bindings, like giving the ipv4 and
#   ipv6 addresses of the host.
#   I think maybe our semantics should be: we accept a list of bind addresses,
#   and we bind to the first one that is compatible with the
#   connection attempt we want to make, and if none are compatible then we
#   don't try to connect to that target.
#
# XX TODO: implement bind address support
#
# Actually, the best option is probably to be explicit: {AF_INET: "...",
#   AF_INET6: "..."}
# this might be simpler after
async def open_tcp_stream(
    host: str | bytes,
    port: int,
    *,
    happy_eyeballs_delay: float | None = DEFAULT_DELAY,
    local_address: str | None = None,
) -> trio.SocketStream:
    """Connect to the given host and port over TCP.

    If the given ``host`` has multiple IP addresses associated with it, then
    we have a problem: which one do we use?

    One approach would be to attempt to connect to the first one, and then if
    that fails, attempt to connect to the second one ... until we've tried all
    of them. But the problem with this is that if the first IP address is
    unreachable (for example, because it's an IPv6 address and our network
    discards IPv6 packets), then we might end up waiting tens of seconds for
    the first connection attempt to timeout before we try the second address.

    Another approach would be to attempt to connect to all of the addresses at
    the same time, in parallel, and then use whichever connection succeeds
    first, abandoning the others. This would be fast, but create a lot of
    unnecessary load on the network and the remote server.

    This function strikes a balance between these two extremes: it works its
    way through the available addresses one at a time, like the first
    approach; but, if ``happy_eyeballs_delay`` seconds have passed and it's
    still waiting for an attempt to succeed or fail, then it gets impatient
    and starts the next connection attempt in parallel. As soon as any one
    connection attempt succeeds, all the other attempts are cancelled. This
    avoids unnecessary load because most connections will succeed after just
    one or two attempts, but if one of the addresses is unreachable then it
    doesn't slow us down too much.

    This is known as a "happy eyeballs" algorithm, and our particular variant
    is modelled after how Chrome connects to webservers; see `RFC 6555
    <https://tools.ietf.org/html/rfc6555>`__ for more details.

    Args:
      host (str or bytes): The host to connect to. Can be an IPv4 address,
          IPv6 address, or a hostname.

      port (int): The port to connect to.

      happy_eyeballs_delay (float or None): How many seconds to wait for each
          connection attempt to succeed or fail before getting impatient and
          starting another one in parallel. Set to `None` if you want
          to limit to only one connection attempt at a time (like
          :func:`socket.create_connection`). Default: 0.25 (250 ms).

      local_address (None or str): The local IP address or hostname to use as
          the source for outgoing connections. If ``None``, we let the OS pick
          the source IP.

          This is useful in some exotic networking configurations where your
          host has multiple IP addresses, and you want to force the use of a
          specific one.

          Note that if you pass an IPv4 ``local_address``, then you won't be
          able to connect to IPv6 hosts, and vice-versa. If you want to take
          advantage of this to force the use of IPv4 or IPv6 without
          specifying an exact source address, you can use the IPv4 wildcard
          address ``local_address="0.0.0.0"``, or the IPv6 wildcard address
          ``local_address="::"``.

    Returns:
      SocketStream: a :class:`~trio.abc.Stream` connected to the given server.

    Raises:
      OSError: if the connection fails.

    See also:
      open_ssl_over_tcp_stream

    """

    # To keep our public API surface smaller, rule out some cases that
    # getaddrinfo will accept in some circumstances, but that act weird or
    # have non-portable behavior or are just plain not useful.
    if not isinstance(host, (str, bytes)):
        raise ValueError(f"host must be str or bytes, not {host!r}")
    if not isinstance(port, int):
        raise TypeError(f"port must be int, not {port!r}")

    if happy_eyeballs_delay is None:
        happy_eyeballs_delay = DEFAULT_DELAY

    targets = await getaddrinfo(host, port, type=SOCK_STREAM)

    # I don't think this can actually happen -- if there are no results,
    # getaddrinfo should have raised OSError instead of returning an empty
    # list. But let's be paranoid and handle it anyway:
    if not targets:
        msg = f"no results found for hostname lookup: {format_host_port(host, port)}"
        raise OSError(msg)

    reorder_for_rfc_6555_section_5_4(targets)

    # This list records all the connection failures that we ignored.
    oserrors: list[OSError] = []

    # Keeps track of the socket that we're going to complete with,
    # need to make sure this isn't automatically closed
    winning_socket: SocketType | None = None

    # Try connecting to the specified address. Possible outcomes:
    # - success: record connected socket in winning_socket and cancel
    #   concurrent attempts
    # - failure: record exception in oserrors, set attempt_failed allowing
    #   the next connection attempt to start early
    # code needs to ensure sockets can be closed appropriately in the
    # face of crash or cancellation
    async def attempt_connect(
        socket_args: tuple[AddressFamily, SocketKind, int],
        sockaddr: AddressFormat,
        attempt_failed: trio.Event,
    ) -> None:
        nonlocal winning_socket

        try:
            sock = socket(*socket_args)
            open_sockets.add(sock)

            if local_address is not None:
                # TCP connections are identified by a 4-tuple:
                #
                #   (local IP, local port, remote IP, remote port)
                #
                # So if a single local IP wants to make multiple connections
                # to the same (remote IP, remote port) pair, then those
                # connections have to use different local ports, or else TCP
                # won't be able to tell them apart. OTOH, if you have multiple
                # connections to different remote IP/ports, then those
                # connections can share a local port.
                #
                # Normally, when you call bind(), the kernel will immediately
                # assign a specific local port to your socket. At this point
                # the kernel doesn't know which (remote IP, remote port)
                # you're going to use, so it has to pick a local port that
                # *no* other connection is using. That's the only way to
                # guarantee that this local port will be usable later when we
                # call connect(). (Alternatively, you can set SO_REUSEADDR to
                # allow multiple nascent connections to share the same port,
                # but then connect() might fail with EADDRNOTAVAIL if we get
                # unlucky and our TCP 4-tuple ends up colliding with another
                # unrelated connection.)
                #
                # So calling bind() before connect() works, but it disables
                # sharing of local ports. This is inefficient: it makes you
                # more likely to run out of local ports.
                #
                # But on some versions of Linux, we can re-enable sharing of
                # local ports by setting a special flag. This flag tells
                # bind() to only bind the IP, and not the port. That way,
                # connect() is allowed to pick the the port, and it can do a
                # better job of it because it knows the remote IP/port.
                with suppress(OSError, AttributeError):
                    sock.setsockopt(
                        trio.socket.IPPROTO_IP,
                        trio.socket.IP_BIND_ADDRESS_NO_PORT,
                        1,
                    )
                try:
                    await sock.bind((local_address, 0))
                except OSError:
                    raise OSError(
                        f"local_address={local_address!r} is incompatible "
                        f"with remote address {sockaddr!r}",
                    ) from None

            await sock.connect(sockaddr)

            # Success! Save the winning socket and cancel all outstanding
            # connection attempts.
            winning_socket = sock
            nursery.cancel_scope.cancel()
        except OSError as exc:
            # This connection attempt failed, but the next one might
            # succeed. Save the error for later so we can report it if
            # everything fails, and tell the next attempt that it should go
            # ahead (if it hasn't already).
            oserrors.append(exc)
            attempt_failed.set()

    with close_all() as open_sockets:
        # nursery spawns a task for each connection attempt, will be
        # cancelled by the task that gets a successful connection
        async with trio.open_nursery() as nursery:
            for address_family, socket_type, proto, _, addr in targets:
                # create an event to indicate connection failure,
                # allowing the next target to be tried early
                attempt_failed = trio.Event()

                # workaround to check types until typing of nursery.start_soon improved
                if TYPE_CHECKING:
                    await attempt_connect(
                        (address_family, socket_type, proto),
                        addr,
                        attempt_failed,
                    )

                nursery.start_soon(
                    attempt_connect,
                    (address_family, socket_type, proto),
                    addr,
                    attempt_failed,
                )

                # give this attempt at most this time before moving on
                with trio.move_on_after(happy_eyeballs_delay):
                    await attempt_failed.wait()

        # nothing succeeded
        if winning_socket is None:
            assert len(oserrors) == len(targets)
            msg = f"all attempts to connect to {format_host_port(host, port)} failed"
            raise OSError(msg) from ExceptionGroup(msg, oserrors)
        else:
            stream = trio.SocketStream(winning_socket)
            open_sockets.remove(winning_socket)
            return stream

# === NexusCore/openenv\Lib\site-packages\fontTools\qu2cu\qu2cu.py ===
# cython: language_level=3
# distutils: define_macros=CYTHON_TRACE_NOGIL=1

# Copyright 2023 Google Inc. All Rights Reserved.
# Copyright 2023 Behdad Esfahbod. All Rights Reserved.
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

try:
    import cython
except (AttributeError, ImportError):
    # if cython not installed, use mock module with no-op decorators and types
    from fontTools.misc import cython
COMPILED = cython.compiled

from fontTools.misc.bezierTools import splitCubicAtTC
from collections import namedtuple
import math
from typing import (
    List,
    Tuple,
    Union,
)


__all__ = ["quadratic_to_curves"]


# Copied from cu2qu
@cython.cfunc
@cython.returns(cython.int)
@cython.locals(
    tolerance=cython.double,
    p0=cython.complex,
    p1=cython.complex,
    p2=cython.complex,
    p3=cython.complex,
)
@cython.locals(mid=cython.complex, deriv3=cython.complex)
def cubic_farthest_fit_inside(p0, p1, p2, p3, tolerance):
    """Check if a cubic Bezier lies within a given distance of the origin.

    "Origin" means *the* origin (0,0), not the start of the curve. Note that no
    checks are made on the start and end positions of the curve; this function
    only checks the inside of the curve.

    Args:
        p0 (complex): Start point of curve.
        p1 (complex): First handle of curve.
        p2 (complex): Second handle of curve.
        p3 (complex): End point of curve.
        tolerance (double): Distance from origin.

    Returns:
        bool: True if the cubic Bezier ``p`` entirely lies within a distance
        ``tolerance`` of the origin, False otherwise.
    """
    # First check p2 then p1, as p2 has higher error early on.
    if abs(p2) <= tolerance and abs(p1) <= tolerance:
        return True

    # Split.
    mid = (p0 + 3 * (p1 + p2) + p3) * 0.125
    if abs(mid) > tolerance:
        return False
    deriv3 = (p3 + p2 - p1 - p0) * 0.125
    return cubic_farthest_fit_inside(
        p0, (p0 + p1) * 0.5, mid - deriv3, mid, tolerance
    ) and cubic_farthest_fit_inside(mid, mid + deriv3, (p2 + p3) * 0.5, p3, tolerance)


@cython.locals(
    p0=cython.complex,
    p1=cython.complex,
    p2=cython.complex,
    p1_2_3=cython.complex,
)
def elevate_quadratic(p0, p1, p2):
    """Given a quadratic bezier curve, return its degree-elevated cubic."""

    # https://pomax.github.io/bezierinfo/#reordering
    p1_2_3 = p1 * (2 / 3)
    return (
        p0,
        (p0 * (1 / 3) + p1_2_3),
        (p2 * (1 / 3) + p1_2_3),
        p2,
    )


@cython.cfunc
@cython.locals(
    start=cython.int,
    n=cython.int,
    k=cython.int,
    prod_ratio=cython.double,
    sum_ratio=cython.double,
    ratio=cython.double,
    t=cython.double,
    p0=cython.complex,
    p1=cython.complex,
    p2=cython.complex,
    p3=cython.complex,
)
def merge_curves(curves, start, n):
    """Give a cubic-Bezier spline, reconstruct one cubic-Bezier
    that has the same endpoints and tangents and approxmates
    the spline."""

    # Reconstruct the t values of the cut segments
    prod_ratio = 1.0
    sum_ratio = 1.0
    ts = [1]
    for k in range(1, n):
        ck = curves[start + k]
        c_before = curves[start + k - 1]

        # |t_(k+1) - t_k| / |t_k - t_(k - 1)| = ratio
        assert ck[0] == c_before[3]
        ratio = abs(ck[1] - ck[0]) / abs(c_before[3] - c_before[2])

        prod_ratio *= ratio
        sum_ratio += prod_ratio
        ts.append(sum_ratio)

    # (t(n) - t(n - 1)) / (t_(1) - t(0)) = prod_ratio

    ts = [t / sum_ratio for t in ts[:-1]]

    p0 = curves[start][0]
    p1 = curves[start][1]
    p2 = curves[start + n - 1][2]
    p3 = curves[start + n - 1][3]

    # Build the curve by scaling the control-points.
    p1 = p0 + (p1 - p0) / (ts[0] if ts else 1)
    p2 = p3 + (p2 - p3) / ((1 - ts[-1]) if ts else 1)

    curve = (p0, p1, p2, p3)

    return curve, ts


@cython.locals(
    count=cython.int,
    num_offcurves=cython.int,
    i=cython.int,
    off1=cython.complex,
    off2=cython.complex,
    on=cython.complex,
)
def add_implicit_on_curves(p):
    q = list(p)
    count = 0
    num_offcurves = len(p) - 2
    for i in range(1, num_offcurves):
        off1 = p[i]
        off2 = p[i + 1]
        on = off1 + (off2 - off1) * 0.5
        q.insert(i + 1 + count, on)
        count += 1
    return q


Point = Union[Tuple[float, float], complex]


@cython.locals(
    cost=cython.int,
    is_complex=cython.int,
)
def quadratic_to_curves(
    quads: List[List[Point]],
    max_err: float = 0.5,
    all_cubic: bool = False,
) -> List[Tuple[Point, ...]]:
    """Converts a connecting list of quadratic splines to a list of quadratic
    and cubic curves.

    A quadratic spline is specified as a list of points.  Either each point is
    a 2-tuple of X,Y coordinates, or each point is a complex number with
    real/imaginary components representing X,Y coordinates.

    The first and last points are on-curve points and the rest are off-curve
    points, with an implied on-curve point in the middle between every two
    consequtive off-curve points.

    Returns:
        The output is a list of tuples of points. Points are represented
        in the same format as the input, either as 2-tuples or complex numbers.

        Each tuple is either of length three, for a quadratic curve, or four,
        for a cubic curve.  Each curve's last point is the same as the next
        curve's first point.

    Args:
        quads: quadratic splines

        max_err: absolute error tolerance; defaults to 0.5

        all_cubic: if True, only cubic curves are generated; defaults to False
    """
    is_complex = type(quads[0][0]) is complex
    if not is_complex:
        quads = [[complex(x, y) for (x, y) in p] for p in quads]

    q = [quads[0][0]]
    costs = [1]
    cost = 1
    for p in quads:
        assert q[-1] == p[0]
        for i in range(len(p) - 2):
            cost += 1
            costs.append(cost)
            costs.append(cost)
        qq = add_implicit_on_curves(p)[1:]
        costs.pop()
        q.extend(qq)
        cost += 1
        costs.append(cost)

    curves = spline_to_curves(q, costs, max_err, all_cubic)

    if not is_complex:
        curves = [tuple((c.real, c.imag) for c in curve) for curve in curves]
    return curves


Solution = namedtuple("Solution", ["num_points", "error", "start_index", "is_cubic"])


@cython.locals(
    i=cython.int,
    j=cython.int,
    k=cython.int,
    start=cython.int,
    i_sol_count=cython.int,
    j_sol_count=cython.int,
    this_sol_count=cython.int,
    tolerance=cython.double,
    err=cython.double,
    error=cython.double,
    i_sol_error=cython.double,
    j_sol_error=cython.double,
    all_cubic=cython.int,
    is_cubic=cython.int,
    count=cython.int,
    p0=cython.complex,
    p1=cython.complex,
    p2=cython.complex,
    p3=cython.complex,
    v=cython.complex,
    u=cython.complex,
)
def spline_to_curves(q, costs, tolerance=0.5, all_cubic=False):
    """
    q: quadratic spline with alternating on-curve / off-curve points.

    costs: cumulative list of encoding cost of q in terms of number of
      points that need to be encoded.  Implied on-curve points do not
      contribute to the cost. If all points need to be encoded, then
      costs will be range(1, len(q)+1).
    """

    assert len(q) >= 3, "quadratic spline requires at least 3 points"

    # Elevate quadratic segments to cubic
    elevated_quadratics = [
        elevate_quadratic(*q[i : i + 3]) for i in range(0, len(q) - 2, 2)
    ]

    # Find sharp corners; they have to be oncurves for sure.
    forced = set()
    for i in range(1, len(elevated_quadratics)):
        p0 = elevated_quadratics[i - 1][2]
        p1 = elevated_quadratics[i][0]
        p2 = elevated_quadratics[i][1]
        if abs(p1 - p0) + abs(p2 - p1) > tolerance + abs(p2 - p0):
            forced.add(i)

    # Dynamic-Programming to find the solution with fewest number of
    # cubic curves, and within those the one with smallest error.
    sols = [Solution(0, 0, 0, False)]
    impossible = Solution(len(elevated_quadratics) * 3 + 1, 0, 1, False)
    start = 0
    for i in range(1, len(elevated_quadratics) + 1):
        best_sol = impossible
        for j in range(start, i):
            j_sol_count, j_sol_error = sols[j].num_points, sols[j].error

            if not all_cubic:
                # Solution with quadratics between j:i
                this_count = costs[2 * i - 1] - costs[2 * j] + 1
                i_sol_count = j_sol_count + this_count
                i_sol_error = j_sol_error
                i_sol = Solution(i_sol_count, i_sol_error, i - j, False)
                if i_sol < best_sol:
                    best_sol = i_sol

                if this_count <= 3:
                    # Can't get any better than this in the path below
                    continue

            # Fit elevated_quadratics[j:i] into one cubic
            try:
                curve, ts = merge_curves(elevated_quadratics, j, i - j)
            except ZeroDivisionError:
                continue

            # Now reconstruct the segments from the fitted curve
            reconstructed_iter = splitCubicAtTC(*curve, *ts)
            reconstructed = []

            # Knot errors
            error = 0
            for k, reconst in enumerate(reconstructed_iter):
                orig = elevated_quadratics[j + k]
                err = abs(reconst[3] - orig[3])
                error = max(error, err)
                if error > tolerance:
                    break
                reconstructed.append(reconst)
            if error > tolerance:
                # Not feasible
                continue

            # Interior errors
            for k, reconst in enumerate(reconstructed):
                orig = elevated_quadratics[j + k]
                p0, p1, p2, p3 = tuple(v - u for v, u in zip(reconst, orig))

                if not cubic_farthest_fit_inside(p0, p1, p2, p3, tolerance):
                    error = tolerance + 1
                    break
            if error > tolerance:
                # Not feasible
                continue

            # Save best solution
            i_sol_count = j_sol_count + 3
            i_sol_error = max(j_sol_error, error)
            i_sol = Solution(i_sol_count, i_sol_error, i - j, True)
            if i_sol < best_sol:
                best_sol = i_sol

            if i_sol_count == 3:
                # Can't get any better than this
                break

        sols.append(best_sol)
        if i in forced:
            start = i

    # Reconstruct solution
    splits = []
    cubic = []
    i = len(sols) - 1
    while i:
        count, is_cubic = sols[i].start_index, sols[i].is_cubic
        splits.append(i)
        cubic.append(is_cubic)
        i -= count
    curves = []
    j = 0
    for i, is_cubic in reversed(list(zip(splits, cubic))):
        if is_cubic:
            curves.append(merge_curves(elevated_quadratics, j, i - j)[0])
        else:
            for k in range(j, i):
                curves.append(q[k * 2 : k * 2 + 3])
        j = i

    return curves


def main():
    from fontTools.cu2qu.benchmark import generate_curve
    from fontTools.cu2qu import curve_to_quadratic

    tolerance = 0.05
    reconstruct_tolerance = tolerance * 1
    curve = generate_curve()
    quadratics = curve_to_quadratic(curve, tolerance)
    print(
        "cu2qu tolerance %g. qu2cu tolerance %g." % (tolerance, reconstruct_tolerance)
    )
    print("One random cubic turned into %d quadratics." % len(quadratics))
    curves = quadratic_to_curves([quadratics], reconstruct_tolerance)
    print("Those quadratics turned back into %d cubics. " % len(curves))
    print("Original curve:", curve)
    print("Reconstructed curve(s):", curves)


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\joblib\externals\loky\backend\context.py ===
###############################################################################
# Basic context management with LokyContext
#
# author: Thomas Moreau and Olivier Grisel
#
# adapted from multiprocessing/context.py
#  * Create a context ensuring loky uses only objects that are compatible
#  * Add LokyContext to the list of context of multiprocessing so loky can be
#    used with multiprocessing.set_start_method
#  * Implement a CFS-aware amd physical-core aware cpu_count function.
#
import os
import sys
import math
import subprocess
import traceback
import warnings
import multiprocessing as mp
from multiprocessing import get_context as mp_get_context
from multiprocessing.context import BaseContext
from concurrent.futures.process import _MAX_WINDOWS_WORKERS


from .process import LokyProcess, LokyInitMainProcess

# Apparently, on older Python versions, loky cannot work 61 workers on Windows
# but instead 60: ¯\_(ツ)_/¯
if sys.version_info < (3, 10):
    _MAX_WINDOWS_WORKERS = _MAX_WINDOWS_WORKERS - 1

START_METHODS = ["loky", "loky_init_main", "spawn"]
if sys.platform != "win32":
    START_METHODS += ["fork", "forkserver"]

_DEFAULT_START_METHOD = None

# Cache for the number of physical cores to avoid repeating subprocess calls.
# It should not change during the lifetime of the program.
physical_cores_cache = None


def get_context(method=None):
    # Try to overload the default context
    method = method or _DEFAULT_START_METHOD or "loky"
    if method == "fork":
        # If 'fork' is explicitly requested, warn user about potential issues.
        warnings.warn(
            "`fork` start method should not be used with "
            "`loky` as it does not respect POSIX. Try using "
            "`spawn` or `loky` instead.",
            UserWarning,
        )
    try:
        return mp_get_context(method)
    except ValueError:
        raise ValueError(
            f"Unknown context '{method}'. Value should be in "
            f"{START_METHODS}."
        )


def set_start_method(method, force=False):
    global _DEFAULT_START_METHOD
    if _DEFAULT_START_METHOD is not None and not force:
        raise RuntimeError("context has already been set")
    assert method is None or method in START_METHODS, (
        f"'{method}' is not a valid start_method. It should be in "
        f"{START_METHODS}"
    )

    _DEFAULT_START_METHOD = method


def get_start_method():
    return _DEFAULT_START_METHOD


def cpu_count(only_physical_cores=False):
    """Return the number of CPUs the current process can use.

    The returned number of CPUs accounts for:
     * the number of CPUs in the system, as given by
       ``multiprocessing.cpu_count``;
     * the CPU affinity settings of the current process
       (available on some Unix systems);
     * Cgroup CPU bandwidth limit (available on Linux only, typically
       set by docker and similar container orchestration systems);
     * the value of the LOKY_MAX_CPU_COUNT environment variable if defined.
    and is given as the minimum of these constraints.

    If ``only_physical_cores`` is True, return the number of physical cores
    instead of the number of logical cores (hyperthreading / SMT). Note that
    this option is not enforced if the number of usable cores is controlled in
    any other way such as: process affinity, Cgroup restricted CPU bandwidth
    or the LOKY_MAX_CPU_COUNT environment variable. If the number of physical
    cores is not found, return the number of logical cores.

    Note that on Windows, the returned number of CPUs cannot exceed 61 (or 60 for
    Python < 3.10), see:
    https://bugs.python.org/issue26903.

    It is also always larger or equal to 1.
    """
    # Note: os.cpu_count() is allowed to return None in its docstring
    os_cpu_count = os.cpu_count() or 1
    if sys.platform == "win32":
        # On Windows, attempting to use more than 61 CPUs would result in a
        # OS-level error. See https://bugs.python.org/issue26903. According to
        # https://learn.microsoft.com/en-us/windows/win32/procthread/processor-groups
        # it might be possible to go beyond with a lot of extra work but this
        # does not look easy.
        os_cpu_count = min(os_cpu_count, _MAX_WINDOWS_WORKERS)

    cpu_count_user = _cpu_count_user(os_cpu_count)
    aggregate_cpu_count = max(min(os_cpu_count, cpu_count_user), 1)

    if not only_physical_cores:
        return aggregate_cpu_count

    if cpu_count_user < os_cpu_count:
        # Respect user setting
        return max(cpu_count_user, 1)

    cpu_count_physical, exception = _count_physical_cores()
    if cpu_count_physical != "not found":
        return cpu_count_physical

    # Fallback to default behavior
    if exception is not None:
        # warns only the first time
        warnings.warn(
            "Could not find the number of physical cores for the "
            f"following reason:\n{exception}\n"
            "Returning the number of logical cores instead. You can "
            "silence this warning by setting LOKY_MAX_CPU_COUNT to "
            "the number of cores you want to use."
        )
        traceback.print_tb(exception.__traceback__)

    return aggregate_cpu_count


def _cpu_count_cgroup(os_cpu_count):
    # Cgroup CPU bandwidth limit available in Linux since 2.6 kernel
    cpu_max_fname = "/sys/fs/cgroup/cpu.max"
    cfs_quota_fname = "/sys/fs/cgroup/cpu/cpu.cfs_quota_us"
    cfs_period_fname = "/sys/fs/cgroup/cpu/cpu.cfs_period_us"
    if os.path.exists(cpu_max_fname):
        # cgroup v2
        # https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html
        with open(cpu_max_fname) as fh:
            cpu_quota_us, cpu_period_us = fh.read().strip().split()
    elif os.path.exists(cfs_quota_fname) and os.path.exists(cfs_period_fname):
        # cgroup v1
        # https://www.kernel.org/doc/html/latest/scheduler/sched-bwc.html#management
        with open(cfs_quota_fname) as fh:
            cpu_quota_us = fh.read().strip()
        with open(cfs_period_fname) as fh:
            cpu_period_us = fh.read().strip()
    else:
        # No Cgroup CPU bandwidth limit (e.g. non-Linux platform)
        cpu_quota_us = "max"
        cpu_period_us = 100_000  # unused, for consistency with default values

    if cpu_quota_us == "max":
        # No active Cgroup quota on a Cgroup-capable platform
        return os_cpu_count
    else:
        cpu_quota_us = int(cpu_quota_us)
        cpu_period_us = int(cpu_period_us)
        if cpu_quota_us > 0 and cpu_period_us > 0:
            return math.ceil(cpu_quota_us / cpu_period_us)
        else:  # pragma: no cover
            # Setting a negative cpu_quota_us value is a valid way to disable
            # cgroup CPU bandwith limits
            return os_cpu_count


def _cpu_count_affinity(os_cpu_count):
    # Number of available CPUs given affinity settings
    if hasattr(os, "sched_getaffinity"):
        try:
            return len(os.sched_getaffinity(0))
        except NotImplementedError:
            pass

    # On some platforms, os.sched_getaffinity does not exist or raises
    # NotImplementedError, let's try with the psutil if installed.
    try:
        import psutil

        p = psutil.Process()
        if hasattr(p, "cpu_affinity"):
            return len(p.cpu_affinity())

    except ImportError:  # pragma: no cover
        if (
            sys.platform == "linux"
            and os.environ.get("LOKY_MAX_CPU_COUNT") is None
        ):
            # Some platforms don't implement os.sched_getaffinity on Linux which
            # can cause severe oversubscription problems. Better warn the
            # user in this particularly pathological case which can wreck
            # havoc, typically on CI workers.
            warnings.warn(
                "Failed to inspect CPU affinity constraints on this system. "
                "Please install psutil or explictly set LOKY_MAX_CPU_COUNT."
            )

    # This can happen for platforms that do not implement any kind of CPU
    # infinity such as macOS-based platforms.
    return os_cpu_count


def _cpu_count_user(os_cpu_count):
    """Number of user defined available CPUs"""
    cpu_count_affinity = _cpu_count_affinity(os_cpu_count)

    cpu_count_cgroup = _cpu_count_cgroup(os_cpu_count)

    # User defined soft-limit passed as a loky specific environment variable.
    cpu_count_loky = int(os.environ.get("LOKY_MAX_CPU_COUNT", os_cpu_count))

    return min(cpu_count_affinity, cpu_count_cgroup, cpu_count_loky)


def _count_physical_cores():
    """Return a tuple (number of physical cores, exception)

    If the number of physical cores is found, exception is set to None.
    If it has not been found, return ("not found", exception).

    The number of physical cores is cached to avoid repeating subprocess calls.
    """
    exception = None

    # First check if the value is cached
    global physical_cores_cache
    if physical_cores_cache is not None:
        return physical_cores_cache, exception

    # Not cached yet, find it
    try:
        if sys.platform == "linux":
            cpu_count_physical = _count_physical_cores_linux()
        elif sys.platform == "win32":
            cpu_count_physical = _count_physical_cores_win32()
        elif sys.platform == "darwin":
            cpu_count_physical = _count_physical_cores_darwin()
        else:
            raise NotImplementedError(f"unsupported platform: {sys.platform}")

        # if cpu_count_physical < 1, we did not find a valid value
        if cpu_count_physical < 1:
            raise ValueError(f"found {cpu_count_physical} physical cores < 1")

    except Exception as e:
        exception = e
        cpu_count_physical = "not found"

    # Put the result in cache
    physical_cores_cache = cpu_count_physical

    return cpu_count_physical, exception


def _count_physical_cores_linux():
    try:
        cpu_info = subprocess.run(
            "lscpu --parse=core".split(), capture_output=True, text=True
        )
        cpu_info = cpu_info.stdout.splitlines()
        cpu_info = {line for line in cpu_info if not line.startswith("#")}
        return len(cpu_info)
    except:
        pass  # fallback to /proc/cpuinfo

    cpu_info = subprocess.run(
        "cat /proc/cpuinfo".split(), capture_output=True, text=True
    )
    cpu_info = cpu_info.stdout.splitlines()
    cpu_info = {line for line in cpu_info if line.startswith("core id")}
    return len(cpu_info)


def _count_physical_cores_win32():
    try:
        cmd = "-Command (Get-CimInstance -ClassName Win32_Processor).NumberOfCores"
        cpu_info = subprocess.run(
            f"powershell.exe {cmd}".split(),
            capture_output=True,
            text=True,
        )
        cpu_info = cpu_info.stdout.splitlines()
        return int(cpu_info[0])
    except:
        pass  # fallback to wmic (older Windows versions; deprecated now)

    cpu_info = subprocess.run(
        "wmic CPU Get NumberOfCores /Format:csv".split(),
        capture_output=True,
        text=True,
    )
    cpu_info = cpu_info.stdout.splitlines()
    cpu_info = [
        l.split(",")[1] for l in cpu_info if (l and l != "Node,NumberOfCores")
    ]
    return sum(map(int, cpu_info))


def _count_physical_cores_darwin():
    cpu_info = subprocess.run(
        "sysctl -n hw.physicalcpu".split(),
        capture_output=True,
        text=True,
    )
    cpu_info = cpu_info.stdout
    return int(cpu_info)


class LokyContext(BaseContext):
    """Context relying on the LokyProcess."""

    _name = "loky"
    Process = LokyProcess
    cpu_count = staticmethod(cpu_count)

    def Queue(self, maxsize=0, reducers=None):
        """Returns a queue object"""
        from .queues import Queue

        return Queue(maxsize, reducers=reducers, ctx=self.get_context())

    def SimpleQueue(self, reducers=None):
        """Returns a queue object"""
        from .queues import SimpleQueue

        return SimpleQueue(reducers=reducers, ctx=self.get_context())

    if sys.platform != "win32":
        """For Unix platform, use our custom implementation of synchronize
        ensuring that we use the loky.backend.resource_tracker to clean-up
        the semaphores in case of a worker crash.
        """

        def Semaphore(self, value=1):
            """Returns a semaphore object"""
            from .synchronize import Semaphore

            return Semaphore(value=value)

        def BoundedSemaphore(self, value):
            """Returns a bounded semaphore object"""
            from .synchronize import BoundedSemaphore

            return BoundedSemaphore(value)

        def Lock(self):
            """Returns a lock object"""
            from .synchronize import Lock

            return Lock()

        def RLock(self):
            """Returns a recurrent lock object"""
            from .synchronize import RLock

            return RLock()

        def Condition(self, lock=None):
            """Returns a condition object"""
            from .synchronize import Condition

            return Condition(lock)

        def Event(self):
            """Returns an event object"""
            from .synchronize import Event

            return Event()


class LokyInitMainContext(LokyContext):
    """Extra context with LokyProcess, which does load the main module

    This context is used for compatibility in the case ``cloudpickle`` is not
    present on the running system. This permits to load functions defined in
    the ``main`` module, using proper safeguards. The declaration of the
    ``executor`` should be protected by ``if __name__ == "__main__":`` and the
    functions and variable used from main should be out of this block.

    This mimics the default behavior of multiprocessing under Windows and the
    behavior of the ``spawn`` start method on a posix system.
    For more details, see the end of the following section of python doc
    https://docs.python.org/3/library/multiprocessing.html#multiprocessing-programming
    """

    _name = "loky_init_main"
    Process = LokyInitMainProcess


# Register loky context so it works with multiprocessing.get_context
ctx_loky = LokyContext()
mp.context._concrete_contexts["loky"] = ctx_loky
mp.context._concrete_contexts["loky_init_main"] = LokyInitMainContext()

# === NexusCore/openenv\Lib\site-packages\litellm\llms\fireworks_ai\chat\transformation.py ===
import json
import uuid
from typing import Any, List, Literal, Optional, Tuple, Union, cast

import httpx

import litellm
from litellm.constants import RESPONSE_FORMAT_TOOL_NAME
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.litellm_core_utils.llm_response_utils.get_headers import (
    get_response_headers,
)
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionImageObject,
    ChatCompletionToolParam,
    OpenAIChatCompletionToolParam,
)
from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Choices,
    Function,
    Message,
    ModelResponse,
    ProviderSpecificModelInfo,
)
from litellm.utils import supports_function_calling, supports_tool_choice

from ...openai.chat.gpt_transformation import OpenAIGPTConfig
from ..common_utils import FireworksAIException


class FireworksAIConfig(OpenAIGPTConfig):
    """
    Reference: https://docs.fireworks.ai/api-reference/post-chatcompletions

    The class `FireworksAIConfig` provides configuration for the Fireworks's Chat Completions API interface. Below are the parameters:
    """

    tools: Optional[list] = None
    tool_choice: Optional[Union[str, dict]] = None
    max_tokens: Optional[int] = None
    temperature: Optional[int] = None
    top_p: Optional[int] = None
    top_k: Optional[int] = None
    frequency_penalty: Optional[int] = None
    presence_penalty: Optional[int] = None
    n: Optional[int] = None
    stop: Optional[Union[str, list]] = None
    response_format: Optional[dict] = None
    user: Optional[str] = None
    logprobs: Optional[int] = None

    # Non OpenAI parameters - Fireworks AI only params
    prompt_truncate_length: Optional[int] = None
    context_length_exceeded_behavior: Optional[Literal["error", "truncate"]] = None

    def __init__(
        self,
        tools: Optional[list] = None,
        tool_choice: Optional[Union[str, dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[int] = None,
        top_p: Optional[int] = None,
        top_k: Optional[int] = None,
        frequency_penalty: Optional[int] = None,
        presence_penalty: Optional[int] = None,
        n: Optional[int] = None,
        stop: Optional[Union[str, list]] = None,
        response_format: Optional[dict] = None,
        user: Optional[str] = None,
        logprobs: Optional[int] = None,
        prompt_truncate_length: Optional[int] = None,
        context_length_exceeded_behavior: Optional[Literal["error", "truncate"]] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

    def get_supported_openai_params(self, model: str):
        # Base parameters supported by all models
        supported_params = [
            "stream",
            "max_completion_tokens",
            "max_tokens",
            "temperature",
            "top_p",
            "top_k",
            "frequency_penalty",
            "presence_penalty",
            "n",
            "stop",
            "response_format",
            "user",
            "logprobs",
            "prompt_truncate_length",
            "context_length_exceeded_behavior",
        ]
        
        # Only add tools for models that support function calling
        if supports_function_calling(model=model, custom_llm_provider="fireworks_ai"):
            supported_params.append("tools")
        
        # Only add tool_choice for models that explicitly support it
        if supports_tool_choice(model=model, custom_llm_provider="fireworks_ai"):
            supported_params.append("tool_choice")
        
        return supported_params

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        supported_openai_params = self.get_supported_openai_params(model=model)
        is_tools_set = any(
            param == "tools" and value is not None
            for param, value in non_default_params.items()
        )

        for param, value in non_default_params.items():
            if param == "tool_choice":
                if value == "required":
                    # relevant issue: https://github.com/BerriAI/litellm/issues/4416
                    optional_params["tool_choice"] = "any"
                else:
                    # pass through the value of tool choice
                    optional_params["tool_choice"] = value
            elif param == "response_format":
                if (
                    is_tools_set
                ):  # fireworks ai doesn't support tools and response_format together
                    optional_params = self._add_response_format_to_tools(
                        optional_params=optional_params,
                        value=value,
                        is_response_format_supported=False,
                        enforce_tool_choice=False,  # tools and response_format are both set, don't enforce tool_choice
                    )
                elif "json_schema" in value:
                    optional_params["response_format"] = {
                        "type": "json_object",
                        "schema": value["json_schema"]["schema"],
                    }
                else:
                    optional_params["response_format"] = value
            elif param == "max_completion_tokens":
                optional_params["max_tokens"] = value
            elif param in supported_openai_params:
                if value is not None:
                    optional_params[param] = value

        return optional_params

    def _add_transform_inline_image_block(
        self,
        content: ChatCompletionImageObject,
        model: str,
        disable_add_transform_inline_image_block: Optional[bool],
    ) -> ChatCompletionImageObject:
        """
        Add transform_inline to the image_url (allows non-vision models to parse documents/images/etc.)
        - ignore if model is a vision model
        - ignore if user has disabled this feature
        """
        if (
            "vision" in model or disable_add_transform_inline_image_block
        ):  # allow user to toggle this feature.
            return content
        if isinstance(content["image_url"], str):
            content["image_url"] = f"{content['image_url']}#transform=inline"
        elif isinstance(content["image_url"], dict):
            content["image_url"][
                "url"
            ] = f"{content['image_url']['url']}#transform=inline"
        return content

    def _transform_tools(
        self, tools: List[OpenAIChatCompletionToolParam]
    ) -> List[OpenAIChatCompletionToolParam]:
        for tool in tools:
            if tool.get("type") == "function":
                tool["function"].pop("strict", None)
        return tools

    def _transform_messages_helper(
        self, messages: List[AllMessageValues], model: str, litellm_params: dict
    ) -> List[AllMessageValues]:
        """
        Add 'transform=inline' to the url of the image_url
        """
        from litellm.litellm_core_utils.prompt_templates.common_utils import (
            filter_value_from_dict,
            migrate_file_to_image_url,
        )

        disable_add_transform_inline_image_block = cast(
            Optional[bool],
            litellm_params.get("disable_add_transform_inline_image_block")
            or litellm.disable_add_transform_inline_image_block,
        )
        ## For any 'file' message type with pdf content, move to 'image_url' message type
        for message in messages:
            if message["role"] == "user":
                _message_content = message.get("content")
                if _message_content is not None and isinstance(_message_content, list):
                    for idx, content in enumerate(_message_content):
                        if content["type"] == "file":
                            _message_content[idx] = migrate_file_to_image_url(content)
        for message in messages:
            if message["role"] == "user":
                _message_content = message.get("content")
                if _message_content is not None and isinstance(_message_content, list):
                    for content in _message_content:
                        if content["type"] == "image_url":
                            content = self._add_transform_inline_image_block(
                                content=content,
                                model=model,
                                disable_add_transform_inline_image_block=disable_add_transform_inline_image_block,
                            )
            filter_value_from_dict(cast(dict, message), "cache_control")

        return messages

    def get_provider_info(self, model: str) -> ProviderSpecificModelInfo:
        provider_specific_model_info = ProviderSpecificModelInfo(
            supports_function_calling=True,
            supports_prompt_caching=True,  # https://docs.fireworks.ai/guides/prompt-caching
            supports_pdf_input=True,  # via document inlining
            supports_vision=True,  # via document inlining
        )
        return provider_specific_model_info

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        if not model.startswith("accounts/"):
            model = f"accounts/fireworks/models/{model}"
        messages = self._transform_messages_helper(
            messages=messages, model=model, litellm_params=litellm_params
        )
        if "tools" in optional_params and optional_params["tools"] is not None:
            tools = self._transform_tools(tools=optional_params["tools"])
            optional_params["tools"] = tools
        return super().transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            headers=headers,
        )

    def _handle_message_content_with_tool_calls(
        self,
        message: Message,
        tool_calls: Optional[List[ChatCompletionToolParam]],
    ) -> Message:
        """
        Fireworks AI sends tool calls in the content field instead of tool_calls

        Relevant Issue: https://github.com/BerriAI/litellm/issues/7209#issuecomment-2813208780
        """
        if (
            tool_calls is not None
            and message.content is not None
            and message.tool_calls is None
        ):
            try:
                function = Function(**json.loads(message.content))
                if function.name != RESPONSE_FORMAT_TOOL_NAME and function.name in [
                    tool["function"]["name"] for tool in tool_calls
                ]:
                    tool_call = ChatCompletionMessageToolCall(
                        function=function, id=str(uuid.uuid4()), type="function"
                    )
                    message.tool_calls = [tool_call]

                    message.content = None
            except Exception:
                pass

        return message

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        ## LOGGING
        logging_obj.post_call(
            input=messages,
            api_key=api_key,
            original_response=raw_response.text,
            additional_args={"complete_input_dict": request_data},
        )

        ## RESPONSE OBJECT
        try:
            completion_response = raw_response.json()
        except Exception as e:
            response_headers = getattr(raw_response, "headers", None)
            raise FireworksAIException(
                message="Unable to get json response - {}, Original Response: {}".format(
                    str(e), raw_response.text
                ),
                status_code=raw_response.status_code,
                headers=response_headers,
            )

        raw_response_headers = dict(raw_response.headers)

        additional_headers = get_response_headers(raw_response_headers)

        response = ModelResponse(**completion_response)

        if response.model is not None:
            response.model = "fireworks_ai/" + response.model

        ## FIREWORKS AI sends tool calls in the content field instead of tool_calls
        for choice in response.choices:
            cast(
                Choices, choice
            ).message = self._handle_message_content_with_tool_calls(
                message=cast(Choices, choice).message,
                tool_calls=optional_params.get("tools", None),
            )

        response._hidden_params = {"additional_headers": additional_headers}

        return response

    def _get_openai_compatible_provider_info(
        self, api_base: Optional[str], api_key: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        api_base = (
            api_base
            or get_secret_str("FIREWORKS_API_BASE")
            or "https://api.fireworks.ai/inference/v1"
        )  # type: ignore
        dynamic_api_key = api_key or (
            get_secret_str("FIREWORKS_API_KEY")
            or get_secret_str("FIREWORKS_AI_API_KEY")
            or get_secret_str("FIREWORKSAI_API_KEY")
            or get_secret_str("FIREWORKS_AI_TOKEN")
        )
        return api_base, dynamic_api_key

    def get_models(self, api_key: Optional[str] = None, api_base: Optional[str] = None):
        api_base, api_key = self._get_openai_compatible_provider_info(
            api_base=api_base, api_key=api_key
        )
        if api_base is None or api_key is None:
            raise ValueError(
                "FIREWORKS_API_BASE or FIREWORKS_API_KEY is not set. Please set the environment variable, to query Fireworks AI's `/models` endpoint."
            )

        account_id = get_secret_str("FIREWORKS_ACCOUNT_ID")
        if account_id is None:
            raise ValueError(
                "FIREWORKS_ACCOUNT_ID is not set. Please set the environment variable, to query Fireworks AI's `/models` endpoint."
            )

        response = litellm.module_level_client.get(
            url=f"{api_base}/v1/accounts/{account_id}/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )

        if response.status_code != 200:
            raise ValueError(
                f"Failed to fetch models from Fireworks AI. Status code: {response.status_code}, Response: {response.json()}"
            )

        models = response.json()["models"]

        return ["fireworks_ai/" + model["name"] for model in models]

    @staticmethod
    def get_api_key(api_key: Optional[str] = None) -> Optional[str]:
        return api_key or (
            get_secret_str("FIREWORKS_API_KEY")
            or get_secret_str("FIREWORKS_AI_API_KEY")
            or get_secret_str("FIREWORKSAI_API_KEY")
            or get_secret_str("FIREWORKS_AI_TOKEN")
        )