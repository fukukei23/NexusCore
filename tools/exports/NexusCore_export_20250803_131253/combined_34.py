
# === NexusCore/openenv\Lib\site-packages\anthropic\lib\streaming\_prompt_caching_beta_messages.py ===
from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable, cast
from typing_extensions import Self, Iterator, Awaitable, AsyncIterator, assert_never

import httpx

from ...types import ContentBlock
from ..._utils import consume_sync_iterator, consume_async_iterator
from ..._models import build, construct_type
from ..._streaming import Stream, AsyncStream
from ._prompt_caching_beta_types import (
    TextEvent,
    InputJsonEvent,
    MessageStopEvent,
    ContentBlockStopEvent,
    PromptCachingBetaMessageStreamEvent,
)
from ...types.beta.prompt_caching import PromptCachingBetaMessage, RawPromptCachingBetaMessageStreamEvent

if TYPE_CHECKING:
    from ..._client import Anthropic, AsyncAnthropic


class PromptCachingBetaMessageStream:
    text_stream: Iterator[str]
    """Iterator over just the text deltas in the stream.

    ```py
    for text in stream.text_stream:
        print(text, end="", flush=True)
    print()
    ```
    """

    response: httpx.Response

    def __init__(
        self,
        *,
        cast_to: type[RawPromptCachingBetaMessageStreamEvent],
        response: httpx.Response,
        client: Anthropic,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client

        self.text_stream = self.__stream_text__()
        self.__final_message_snapshot: PromptCachingBetaMessage | None = None

        self._iterator = self.__stream__()
        self._raw_stream: Stream[RawPromptCachingBetaMessageStreamEvent] = Stream(
            cast_to=cast_to, response=response, client=client
        )

    def __next__(self) -> PromptCachingBetaMessageStreamEvent:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[PromptCachingBetaMessageStreamEvent]:
        for item in self._iterator:
            yield item

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

    def get_final_message(self) -> PromptCachingBetaMessage:
        """Waits until the stream has been read to completion and returns
        the accumulated `PromptCachingBetaMessage` object.
        """
        self.until_done()
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    def get_final_text(self) -> str:
        """Returns all `text` content blocks concatenated together.

        > [!NOTE]
        > Currently the API will only respond with a single content block.

        Will raise an error if no `text` content blocks were returned.
        """
        message = self.get_final_message()
        text_blocks: list[str] = []
        for block in message.content:
            if block.type == "text":
                text_blocks.append(block.text)

        if not text_blocks:
            raise RuntimeError("Expected to have received at least 1 text block")

        return "".join(text_blocks)

    def until_done(self) -> None:
        """Blocks until the stream has been consumed"""
        consume_sync_iterator(self)

    # properties
    @property
    def current_message_snapshot(self) -> PromptCachingBetaMessage:
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    def __stream__(self) -> Iterator[PromptCachingBetaMessageStreamEvent]:
        for sse_event in self._raw_stream:
            self.__final_message_snapshot = accumulate_event(
                event=sse_event,
                current_snapshot=self.__final_message_snapshot,
            )

            events_to_fire = build_events(event=sse_event, message_snapshot=self.current_message_snapshot)
            for event in events_to_fire:
                yield event

    def __stream_text__(self) -> Iterator[str]:
        for chunk in self:
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                yield chunk.delta.text


class PromptCachingBetaMessageStreamManager:
    """Wrapper over PromptCachingBetaMessageStream that is returned by `.stream()`.

    ```py
    with client.beta.prompt_caching.messages.stream(...) as stream:
        for chunk in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Callable[[], Stream[RawPromptCachingBetaMessageStreamEvent]],
    ) -> None:
        self.__stream: PromptCachingBetaMessageStream | None = None
        self.__api_request = api_request

    def __enter__(self) -> PromptCachingBetaMessageStream:
        raw_stream = self.__api_request()

        self.__stream = PromptCachingBetaMessageStream(
            cast_to=raw_stream._cast_to,
            response=raw_stream.response,
            client=raw_stream._client,
        )

        return self.__stream

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            self.__stream.close()


class AsyncPromptCachingBetaMessageStream:
    text_stream: AsyncIterator[str]
    """Async iterator over just the text deltas in the stream.

    ```py
    async for text in stream.text_stream:
        print(text, end="", flush=True)
    print()
    ```
    """

    response: httpx.Response

    def __init__(
        self,
        *,
        cast_to: type[RawPromptCachingBetaMessageStreamEvent],
        response: httpx.Response,
        client: AsyncAnthropic,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client

        self.text_stream = self.__stream_text__()
        self.__final_message_snapshot: PromptCachingBetaMessage | None = None

        self._iterator = self.__stream__()
        self._raw_stream: AsyncStream[RawPromptCachingBetaMessageStreamEvent] = AsyncStream(
            cast_to=cast_to, response=response, client=client
        )

    async def __anext__(self) -> PromptCachingBetaMessageStreamEvent:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[PromptCachingBetaMessageStreamEvent]:
        async for item in self._iterator:
            yield item

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

    async def get_final_message(self) -> PromptCachingBetaMessage:
        """Waits until the stream has been read to completion and returns
        the accumulated `PromptCachingBetaMessage` object.
        """
        await self.until_done()
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    async def get_final_text(self) -> str:
        """Returns all `text` content blocks concatenated together.

        > [!NOTE]
        > Currently the API will only respond with a single content block.

        Will raise an error if no `text` content blocks were returned.
        """
        message = await self.get_final_message()
        text_blocks: list[str] = []
        for block in message.content:
            if block.type == "text":
                text_blocks.append(block.text)

        if not text_blocks:
            raise RuntimeError("Expected to have received at least 1 text block")

        return "".join(text_blocks)

    async def until_done(self) -> None:
        """Waits until the stream has been consumed"""
        await consume_async_iterator(self)

    # properties
    @property
    def current_message_snapshot(self) -> PromptCachingBetaMessage:
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    async def __stream__(self) -> AsyncIterator[PromptCachingBetaMessageStreamEvent]:
        async for sse_event in self._raw_stream:
            self.__final_message_snapshot = accumulate_event(
                event=sse_event,
                current_snapshot=self.__final_message_snapshot,
            )

            events_to_fire = build_events(event=sse_event, message_snapshot=self.current_message_snapshot)
            for event in events_to_fire:
                yield event

    async def __stream_text__(self) -> AsyncIterator[str]:
        async for chunk in self:
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                yield chunk.delta.text


class AsyncPromptCachingBetaMessageStreamManager:
    """Wrapper over AsyncMessageStream that is returned by `.stream()`
    so that an async context manager can be used without `await`ing the
    original client call.

    ```py
    async with client.messages.stream(...) as stream:
        async for chunk in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Awaitable[AsyncStream[RawPromptCachingBetaMessageStreamEvent]],
    ) -> None:
        self.__stream: AsyncPromptCachingBetaMessageStream | None = None
        self.__api_request = api_request

    async def __aenter__(self) -> AsyncPromptCachingBetaMessageStream:
        raw_stream = await self.__api_request

        self.__stream = AsyncPromptCachingBetaMessageStream(
            cast_to=raw_stream._cast_to,
            response=raw_stream.response,
            client=raw_stream._client,
        )

        return self.__stream

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            await self.__stream.close()


def build_events(
    *,
    event: RawPromptCachingBetaMessageStreamEvent,
    message_snapshot: PromptCachingBetaMessage,
) -> list[PromptCachingBetaMessageStreamEvent]:
    events_to_fire: list[PromptCachingBetaMessageStreamEvent] = []

    if event.type == "message_start":
        events_to_fire.append(event)
    elif event.type == "message_delta":
        events_to_fire.append(event)
    elif event.type == "message_stop":
        events_to_fire.append(build(MessageStopEvent, type="message_stop", message=message_snapshot))
    elif event.type == "content_block_start":
        events_to_fire.append(event)
    elif event.type == "content_block_delta":
        events_to_fire.append(event)

        content_block = message_snapshot.content[event.index]
        if event.delta.type == "text_delta" and content_block.type == "text":
            events_to_fire.append(
                build(
                    TextEvent,
                    type="text",
                    text=event.delta.text,
                    snapshot=content_block.text,
                )
            )
        elif event.delta.type == "input_json_delta" and content_block.type == "tool_use":
            events_to_fire.append(
                build(
                    InputJsonEvent,
                    type="input_json",
                    partial_json=event.delta.partial_json,
                    snapshot=content_block.input,
                )
            )
    elif event.type == "content_block_stop":
        content_block = message_snapshot.content[event.index]

        events_to_fire.append(
            build(ContentBlockStopEvent, type="content_block_stop", index=event.index, content_block=content_block),
        )
    else:
        # we only want exhaustive checking for linters, not at runtime
        if TYPE_CHECKING:  # type: ignore[unreachable]
            assert_never(event)

    return events_to_fire


JSON_BUF_PROPERTY = "__json_buf"


def accumulate_event(
    *,
    event: RawPromptCachingBetaMessageStreamEvent,
    current_snapshot: PromptCachingBetaMessage | None,
) -> PromptCachingBetaMessage:
    if current_snapshot is None:
        if event.type == "message_start":
            return PromptCachingBetaMessage.construct(**cast(Any, event.message.to_dict()))

        raise RuntimeError(f'Unexpected event order, got {event.type} before "message_start"')

    if event.type == "content_block_start":
        # TODO: check index
        current_snapshot.content.append(
            cast(
                ContentBlock,
                construct_type(type_=ContentBlock, value=event.content_block.model_dump()),
            ),
        )
    elif event.type == "content_block_delta":
        content = current_snapshot.content[event.index]
        if content.type == "text" and event.delta.type == "text_delta":
            content.text += event.delta.text
        elif content.type == "tool_use" and event.delta.type == "input_json_delta":
            from jiter import from_json

            # we need to keep track of the raw JSON string as well so that we can
            # re-parse it for each delta, for now we just store it as an untyped
            # property on the snapshot
            json_buf = cast(bytes, getattr(content, JSON_BUF_PROPERTY, b""))
            json_buf += bytes(event.delta.partial_json, "utf-8")

            if json_buf:
                content.input = from_json(json_buf, partial_mode=True)

            setattr(content, JSON_BUF_PROPERTY, json_buf)
    elif event.type == "message_delta":
        current_snapshot.stop_reason = event.delta.stop_reason
        current_snapshot.stop_sequence = event.delta.stop_sequence
        current_snapshot.usage.output_tokens = event.usage.output_tokens

    return current_snapshot

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\anthropic\lib\streaming\_prompt_caching_beta_messages.py ===
from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable, cast
from typing_extensions import Self, Iterator, Awaitable, AsyncIterator, assert_never

import httpx

from ...types import ContentBlock
from ..._utils import consume_sync_iterator, consume_async_iterator
from ..._models import build, construct_type
from ..._streaming import Stream, AsyncStream
from ._prompt_caching_beta_types import (
    TextEvent,
    InputJsonEvent,
    MessageStopEvent,
    ContentBlockStopEvent,
    PromptCachingBetaMessageStreamEvent,
)
from ...types.beta.prompt_caching import PromptCachingBetaMessage, RawPromptCachingBetaMessageStreamEvent

if TYPE_CHECKING:
    from ..._client import Anthropic, AsyncAnthropic


class PromptCachingBetaMessageStream:
    text_stream: Iterator[str]
    """Iterator over just the text deltas in the stream.

    ```py
    for text in stream.text_stream:
        print(text, end="", flush=True)
    print()
    ```
    """

    response: httpx.Response

    def __init__(
        self,
        *,
        cast_to: type[RawPromptCachingBetaMessageStreamEvent],
        response: httpx.Response,
        client: Anthropic,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client

        self.text_stream = self.__stream_text__()
        self.__final_message_snapshot: PromptCachingBetaMessage | None = None

        self._iterator = self.__stream__()
        self._raw_stream: Stream[RawPromptCachingBetaMessageStreamEvent] = Stream(
            cast_to=cast_to, response=response, client=client
        )

    def __next__(self) -> PromptCachingBetaMessageStreamEvent:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[PromptCachingBetaMessageStreamEvent]:
        for item in self._iterator:
            yield item

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

    def get_final_message(self) -> PromptCachingBetaMessage:
        """Waits until the stream has been read to completion and returns
        the accumulated `PromptCachingBetaMessage` object.
        """
        self.until_done()
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    def get_final_text(self) -> str:
        """Returns all `text` content blocks concatenated together.

        > [!NOTE]
        > Currently the API will only respond with a single content block.

        Will raise an error if no `text` content blocks were returned.
        """
        message = self.get_final_message()
        text_blocks: list[str] = []
        for block in message.content:
            if block.type == "text":
                text_blocks.append(block.text)

        if not text_blocks:
            raise RuntimeError("Expected to have received at least 1 text block")

        return "".join(text_blocks)

    def until_done(self) -> None:
        """Blocks until the stream has been consumed"""
        consume_sync_iterator(self)

    # properties
    @property
    def current_message_snapshot(self) -> PromptCachingBetaMessage:
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    def __stream__(self) -> Iterator[PromptCachingBetaMessageStreamEvent]:
        for sse_event in self._raw_stream:
            self.__final_message_snapshot = accumulate_event(
                event=sse_event,
                current_snapshot=self.__final_message_snapshot,
            )

            events_to_fire = build_events(event=sse_event, message_snapshot=self.current_message_snapshot)
            for event in events_to_fire:
                yield event

    def __stream_text__(self) -> Iterator[str]:
        for chunk in self:
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                yield chunk.delta.text


class PromptCachingBetaMessageStreamManager:
    """Wrapper over PromptCachingBetaMessageStream that is returned by `.stream()`.

    ```py
    with client.beta.prompt_caching.messages.stream(...) as stream:
        for chunk in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Callable[[], Stream[RawPromptCachingBetaMessageStreamEvent]],
    ) -> None:
        self.__stream: PromptCachingBetaMessageStream | None = None
        self.__api_request = api_request

    def __enter__(self) -> PromptCachingBetaMessageStream:
        raw_stream = self.__api_request()

        self.__stream = PromptCachingBetaMessageStream(
            cast_to=raw_stream._cast_to,
            response=raw_stream.response,
            client=raw_stream._client,
        )

        return self.__stream

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            self.__stream.close()


class AsyncPromptCachingBetaMessageStream:
    text_stream: AsyncIterator[str]
    """Async iterator over just the text deltas in the stream.

    ```py
    async for text in stream.text_stream:
        print(text, end="", flush=True)
    print()
    ```
    """

    response: httpx.Response

    def __init__(
        self,
        *,
        cast_to: type[RawPromptCachingBetaMessageStreamEvent],
        response: httpx.Response,
        client: AsyncAnthropic,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client

        self.text_stream = self.__stream_text__()
        self.__final_message_snapshot: PromptCachingBetaMessage | None = None

        self._iterator = self.__stream__()
        self._raw_stream: AsyncStream[RawPromptCachingBetaMessageStreamEvent] = AsyncStream(
            cast_to=cast_to, response=response, client=client
        )

    async def __anext__(self) -> PromptCachingBetaMessageStreamEvent:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[PromptCachingBetaMessageStreamEvent]:
        async for item in self._iterator:
            yield item

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

    async def get_final_message(self) -> PromptCachingBetaMessage:
        """Waits until the stream has been read to completion and returns
        the accumulated `PromptCachingBetaMessage` object.
        """
        await self.until_done()
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    async def get_final_text(self) -> str:
        """Returns all `text` content blocks concatenated together.

        > [!NOTE]
        > Currently the API will only respond with a single content block.

        Will raise an error if no `text` content blocks were returned.
        """
        message = await self.get_final_message()
        text_blocks: list[str] = []
        for block in message.content:
            if block.type == "text":
                text_blocks.append(block.text)

        if not text_blocks:
            raise RuntimeError("Expected to have received at least 1 text block")

        return "".join(text_blocks)

    async def until_done(self) -> None:
        """Waits until the stream has been consumed"""
        await consume_async_iterator(self)

    # properties
    @property
    def current_message_snapshot(self) -> PromptCachingBetaMessage:
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    async def __stream__(self) -> AsyncIterator[PromptCachingBetaMessageStreamEvent]:
        async for sse_event in self._raw_stream:
            self.__final_message_snapshot = accumulate_event(
                event=sse_event,
                current_snapshot=self.__final_message_snapshot,
            )

            events_to_fire = build_events(event=sse_event, message_snapshot=self.current_message_snapshot)
            for event in events_to_fire:
                yield event

    async def __stream_text__(self) -> AsyncIterator[str]:
        async for chunk in self:
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                yield chunk.delta.text


class AsyncPromptCachingBetaMessageStreamManager:
    """Wrapper over AsyncMessageStream that is returned by `.stream()`
    so that an async context manager can be used without `await`ing the
    original client call.

    ```py
    async with client.messages.stream(...) as stream:
        async for chunk in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Awaitable[AsyncStream[RawPromptCachingBetaMessageStreamEvent]],
    ) -> None:
        self.__stream: AsyncPromptCachingBetaMessageStream | None = None
        self.__api_request = api_request

    async def __aenter__(self) -> AsyncPromptCachingBetaMessageStream:
        raw_stream = await self.__api_request

        self.__stream = AsyncPromptCachingBetaMessageStream(
            cast_to=raw_stream._cast_to,
            response=raw_stream.response,
            client=raw_stream._client,
        )

        return self.__stream

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            await self.__stream.close()


def build_events(
    *,
    event: RawPromptCachingBetaMessageStreamEvent,
    message_snapshot: PromptCachingBetaMessage,
) -> list[PromptCachingBetaMessageStreamEvent]:
    events_to_fire: list[PromptCachingBetaMessageStreamEvent] = []

    if event.type == "message_start":
        events_to_fire.append(event)
    elif event.type == "message_delta":
        events_to_fire.append(event)
    elif event.type == "message_stop":
        events_to_fire.append(build(MessageStopEvent, type="message_stop", message=message_snapshot))
    elif event.type == "content_block_start":
        events_to_fire.append(event)
    elif event.type == "content_block_delta":
        events_to_fire.append(event)

        content_block = message_snapshot.content[event.index]
        if event.delta.type == "text_delta" and content_block.type == "text":
            events_to_fire.append(
                build(
                    TextEvent,
                    type="text",
                    text=event.delta.text,
                    snapshot=content_block.text,
                )
            )
        elif event.delta.type == "input_json_delta" and content_block.type == "tool_use":
            events_to_fire.append(
                build(
                    InputJsonEvent,
                    type="input_json",
                    partial_json=event.delta.partial_json,
                    snapshot=content_block.input,
                )
            )
    elif event.type == "content_block_stop":
        content_block = message_snapshot.content[event.index]

        events_to_fire.append(
            build(ContentBlockStopEvent, type="content_block_stop", index=event.index, content_block=content_block),
        )
    else:
        # we only want exhaustive checking for linters, not at runtime
        if TYPE_CHECKING:  # type: ignore[unreachable]
            assert_never(event)

    return events_to_fire


JSON_BUF_PROPERTY = "__json_buf"


def accumulate_event(
    *,
    event: RawPromptCachingBetaMessageStreamEvent,
    current_snapshot: PromptCachingBetaMessage | None,
) -> PromptCachingBetaMessage:
    if current_snapshot is None:
        if event.type == "message_start":
            return PromptCachingBetaMessage.construct(**cast(Any, event.message.to_dict()))

        raise RuntimeError(f'Unexpected event order, got {event.type} before "message_start"')

    if event.type == "content_block_start":
        # TODO: check index
        current_snapshot.content.append(
            cast(
                ContentBlock,
                construct_type(type_=ContentBlock, value=event.content_block.model_dump()),
            ),
        )
    elif event.type == "content_block_delta":
        content = current_snapshot.content[event.index]
        if content.type == "text" and event.delta.type == "text_delta":
            content.text += event.delta.text
        elif content.type == "tool_use" and event.delta.type == "input_json_delta":
            from jiter import from_json

            # we need to keep track of the raw JSON string as well so that we can
            # re-parse it for each delta, for now we just store it as an untyped
            # property on the snapshot
            json_buf = cast(bytes, getattr(content, JSON_BUF_PROPERTY, b""))
            json_buf += bytes(event.delta.partial_json, "utf-8")

            if json_buf:
                content.input = from_json(json_buf, partial_mode=True)

            setattr(content, JSON_BUF_PROPERTY, json_buf)
    elif event.type == "message_delta":
        current_snapshot.stop_reason = event.delta.stop_reason
        current_snapshot.stop_sequence = event.delta.stop_sequence
        current_snapshot.usage.output_tokens = event.usage.output_tokens

    return current_snapshot

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\streaming\_messages.py ===
from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable, cast
from typing_extensions import Self, Iterator, Awaitable, AsyncIterator, assert_never

import httpx

from ._types import (
    TextEvent,
    InputJsonEvent,
    MessageStopEvent,
    MessageStreamEvent,
    ContentBlockStopEvent,
)
from ...types import Message, ContentBlock, RawMessageStreamEvent
from ..._utils import consume_sync_iterator, consume_async_iterator
from ..._models import build, construct_type
from ..._streaming import Stream, AsyncStream

if TYPE_CHECKING:
    from ..._client import Anthropic, AsyncAnthropic


class MessageStream:
    text_stream: Iterator[str]
    """Iterator over just the text deltas in the stream.

    ```py
    for text in stream.text_stream:
        print(text, end="", flush=True)
    print()
    ```
    """

    response: httpx.Response

    def __init__(
        self,
        *,
        cast_to: type[RawMessageStreamEvent],
        response: httpx.Response,
        client: Anthropic,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client

        self.text_stream = self.__stream_text__()
        self.__final_message_snapshot: Message | None = None

        self._iterator = self.__stream__()
        self._raw_stream: Stream[RawMessageStreamEvent] = Stream(cast_to=cast_to, response=response, client=client)

    def __next__(self) -> MessageStreamEvent:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[MessageStreamEvent]:
        for item in self._iterator:
            yield item

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

    def get_final_message(self) -> Message:
        """Waits until the stream has been read to completion and returns
        the accumulated `Message` object.
        """
        self.until_done()
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    def get_final_text(self) -> str:
        """Returns all `text` content blocks concatenated together.

        > [!NOTE]
        > Currently the API will only respond with a single content block.

        Will raise an error if no `text` content blocks were returned.
        """
        message = self.get_final_message()
        text_blocks: list[str] = []
        for block in message.content:
            if block.type == "text":
                text_blocks.append(block.text)

        if not text_blocks:
            raise RuntimeError("Expected to have received at least 1 text block")

        return "".join(text_blocks)

    def until_done(self) -> None:
        """Blocks until the stream has been consumed"""
        consume_sync_iterator(self)

    # properties
    @property
    def current_message_snapshot(self) -> Message:
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    def __stream__(self) -> Iterator[MessageStreamEvent]:
        for sse_event in self._raw_stream:
            self.__final_message_snapshot = accumulate_event(
                event=sse_event,
                current_snapshot=self.__final_message_snapshot,
            )

            events_to_fire = build_events(event=sse_event, message_snapshot=self.current_message_snapshot)
            for event in events_to_fire:
                yield event

    def __stream_text__(self) -> Iterator[str]:
        for chunk in self:
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                yield chunk.delta.text


class MessageStreamManager:
    """Wrapper over MessageStream that is returned by `.stream()`.

    ```py
    with client.messages.stream(...) as stream:
        for chunk in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Callable[[], Stream[RawMessageStreamEvent]],
    ) -> None:
        self.__stream: MessageStream | None = None
        self.__api_request = api_request

    def __enter__(self) -> MessageStream:
        raw_stream = self.__api_request()

        self.__stream = MessageStream(
            cast_to=raw_stream._cast_to,
            response=raw_stream.response,
            client=raw_stream._client,
        )

        return self.__stream

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            self.__stream.close()


class AsyncMessageStream:
    text_stream: AsyncIterator[str]
    """Async iterator over just the text deltas in the stream.

    ```py
    async for text in stream.text_stream:
        print(text, end="", flush=True)
    print()
    ```
    """

    response: httpx.Response

    def __init__(
        self,
        *,
        cast_to: type[RawMessageStreamEvent],
        response: httpx.Response,
        client: AsyncAnthropic,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client

        self.text_stream = self.__stream_text__()
        self.__final_message_snapshot: Message | None = None

        self._iterator = self.__stream__()
        self._raw_stream: AsyncStream[RawMessageStreamEvent] = AsyncStream(
            cast_to=cast_to, response=response, client=client
        )

    async def __anext__(self) -> MessageStreamEvent:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[MessageStreamEvent]:
        async for item in self._iterator:
            yield item

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

    async def get_final_message(self) -> Message:
        """Waits until the stream has been read to completion and returns
        the accumulated `Message` object.
        """
        await self.until_done()
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    async def get_final_text(self) -> str:
        """Returns all `text` content blocks concatenated together.

        > [!NOTE]
        > Currently the API will only respond with a single content block.

        Will raise an error if no `text` content blocks were returned.
        """
        message = await self.get_final_message()
        text_blocks: list[str] = []
        for block in message.content:
            if block.type == "text":
                text_blocks.append(block.text)

        if not text_blocks:
            raise RuntimeError("Expected to have received at least 1 text block")

        return "".join(text_blocks)

    async def until_done(self) -> None:
        """Waits until the stream has been consumed"""
        await consume_async_iterator(self)

    # properties
    @property
    def current_message_snapshot(self) -> Message:
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    async def __stream__(self) -> AsyncIterator[MessageStreamEvent]:
        async for sse_event in self._raw_stream:
            self.__final_message_snapshot = accumulate_event(
                event=sse_event,
                current_snapshot=self.__final_message_snapshot,
            )

            events_to_fire = build_events(event=sse_event, message_snapshot=self.current_message_snapshot)
            for event in events_to_fire:
                yield event

    async def __stream_text__(self) -> AsyncIterator[str]:
        async for chunk in self:
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                yield chunk.delta.text


class AsyncMessageStreamManager:
    """Wrapper over AsyncMessageStream that is returned by `.stream()`
    so that an async context manager can be used without `await`ing the
    original client call.

    ```py
    async with client.messages.stream(...) as stream:
        async for chunk in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Awaitable[AsyncStream[RawMessageStreamEvent]],
    ) -> None:
        self.__stream: AsyncMessageStream | None = None
        self.__api_request = api_request

    async def __aenter__(self) -> AsyncMessageStream:
        raw_stream = await self.__api_request

        self.__stream = AsyncMessageStream(
            cast_to=raw_stream._cast_to,
            response=raw_stream.response,
            client=raw_stream._client,
        )

        return self.__stream

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            await self.__stream.close()


def build_events(
    *,
    event: RawMessageStreamEvent,
    message_snapshot: Message,
) -> list[MessageStreamEvent]:
    events_to_fire: list[MessageStreamEvent] = []

    if event.type == "message_start":
        events_to_fire.append(event)
    elif event.type == "message_delta":
        events_to_fire.append(event)
    elif event.type == "message_stop":
        events_to_fire.append(build(MessageStopEvent, type="message_stop", message=message_snapshot))
    elif event.type == "content_block_start":
        events_to_fire.append(event)
    elif event.type == "content_block_delta":
        events_to_fire.append(event)

        content_block = message_snapshot.content[event.index]
        if event.delta.type == "text_delta" and content_block.type == "text":
            events_to_fire.append(
                build(
                    TextEvent,
                    type="text",
                    text=event.delta.text,
                    snapshot=content_block.text,
                )
            )
        elif event.delta.type == "input_json_delta" and content_block.type == "tool_use":
            events_to_fire.append(
                build(
                    InputJsonEvent,
                    type="input_json",
                    partial_json=event.delta.partial_json,
                    snapshot=content_block.input,
                )
            )
    elif event.type == "content_block_stop":
        content_block = message_snapshot.content[event.index]

        events_to_fire.append(
            build(ContentBlockStopEvent, type="content_block_stop", index=event.index, content_block=content_block),
        )
    else:
        # we only want exhaustive checking for linters, not at runtime
        if TYPE_CHECKING:  # type: ignore[unreachable]
            assert_never(event)

    return events_to_fire


JSON_BUF_PROPERTY = "__json_buf"


def accumulate_event(
    *,
    event: RawMessageStreamEvent,
    current_snapshot: Message | None,
) -> Message:
    if current_snapshot is None:
        if event.type == "message_start":
            return Message.construct(**cast(Any, event.message.to_dict()))

        raise RuntimeError(f'Unexpected event order, got {event.type} before "message_start"')

    if event.type == "content_block_start":
        # TODO: check index
        current_snapshot.content.append(
            cast(
                ContentBlock,
                construct_type(type_=ContentBlock, value=event.content_block.model_dump()),
            ),
        )
    elif event.type == "content_block_delta":
        content = current_snapshot.content[event.index]
        if content.type == "text" and event.delta.type == "text_delta":
            content.text += event.delta.text
        elif content.type == "tool_use" and event.delta.type == "input_json_delta":
            from jiter import from_json

            # we need to keep track of the raw JSON string as well so that we can
            # re-parse it for each delta, for now we just store it as an untyped
            # property on the snapshot
            json_buf = cast(bytes, getattr(content, JSON_BUF_PROPERTY, b""))
            json_buf += bytes(event.delta.partial_json, "utf-8")

            if json_buf:
                content.input = from_json(json_buf, partial_mode=True)

            setattr(content, JSON_BUF_PROPERTY, json_buf)
    elif event.type == "message_delta":
        current_snapshot.stop_reason = event.delta.stop_reason
        current_snapshot.stop_sequence = event.delta.stop_sequence
        current_snapshot.usage.output_tokens = event.usage.output_tokens

    return current_snapshot

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\anthropic\lib\streaming\_messages.py ===
from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable, cast
from typing_extensions import Self, Iterator, Awaitable, AsyncIterator, assert_never

import httpx

from ._types import (
    TextEvent,
    InputJsonEvent,
    MessageStopEvent,
    MessageStreamEvent,
    ContentBlockStopEvent,
)
from ...types import Message, ContentBlock, RawMessageStreamEvent
from ..._utils import consume_sync_iterator, consume_async_iterator
from ..._models import build, construct_type
from ..._streaming import Stream, AsyncStream

if TYPE_CHECKING:
    from ..._client import Anthropic, AsyncAnthropic


class MessageStream:
    text_stream: Iterator[str]
    """Iterator over just the text deltas in the stream.

    ```py
    for text in stream.text_stream:
        print(text, end="", flush=True)
    print()
    ```
    """

    response: httpx.Response

    def __init__(
        self,
        *,
        cast_to: type[RawMessageStreamEvent],
        response: httpx.Response,
        client: Anthropic,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client

        self.text_stream = self.__stream_text__()
        self.__final_message_snapshot: Message | None = None

        self._iterator = self.__stream__()
        self._raw_stream: Stream[RawMessageStreamEvent] = Stream(cast_to=cast_to, response=response, client=client)

    def __next__(self) -> MessageStreamEvent:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[MessageStreamEvent]:
        for item in self._iterator:
            yield item

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

    def get_final_message(self) -> Message:
        """Waits until the stream has been read to completion and returns
        the accumulated `Message` object.
        """
        self.until_done()
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    def get_final_text(self) -> str:
        """Returns all `text` content blocks concatenated together.

        > [!NOTE]
        > Currently the API will only respond with a single content block.

        Will raise an error if no `text` content blocks were returned.
        """
        message = self.get_final_message()
        text_blocks: list[str] = []
        for block in message.content:
            if block.type == "text":
                text_blocks.append(block.text)

        if not text_blocks:
            raise RuntimeError("Expected to have received at least 1 text block")

        return "".join(text_blocks)

    def until_done(self) -> None:
        """Blocks until the stream has been consumed"""
        consume_sync_iterator(self)

    # properties
    @property
    def current_message_snapshot(self) -> Message:
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    def __stream__(self) -> Iterator[MessageStreamEvent]:
        for sse_event in self._raw_stream:
            self.__final_message_snapshot = accumulate_event(
                event=sse_event,
                current_snapshot=self.__final_message_snapshot,
            )

            events_to_fire = build_events(event=sse_event, message_snapshot=self.current_message_snapshot)
            for event in events_to_fire:
                yield event

    def __stream_text__(self) -> Iterator[str]:
        for chunk in self:
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                yield chunk.delta.text


class MessageStreamManager:
    """Wrapper over MessageStream that is returned by `.stream()`.

    ```py
    with client.messages.stream(...) as stream:
        for chunk in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Callable[[], Stream[RawMessageStreamEvent]],
    ) -> None:
        self.__stream: MessageStream | None = None
        self.__api_request = api_request

    def __enter__(self) -> MessageStream:
        raw_stream = self.__api_request()

        self.__stream = MessageStream(
            cast_to=raw_stream._cast_to,
            response=raw_stream.response,
            client=raw_stream._client,
        )

        return self.__stream

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            self.__stream.close()


class AsyncMessageStream:
    text_stream: AsyncIterator[str]
    """Async iterator over just the text deltas in the stream.

    ```py
    async for text in stream.text_stream:
        print(text, end="", flush=True)
    print()
    ```
    """

    response: httpx.Response

    def __init__(
        self,
        *,
        cast_to: type[RawMessageStreamEvent],
        response: httpx.Response,
        client: AsyncAnthropic,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client

        self.text_stream = self.__stream_text__()
        self.__final_message_snapshot: Message | None = None

        self._iterator = self.__stream__()
        self._raw_stream: AsyncStream[RawMessageStreamEvent] = AsyncStream(
            cast_to=cast_to, response=response, client=client
        )

    async def __anext__(self) -> MessageStreamEvent:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[MessageStreamEvent]:
        async for item in self._iterator:
            yield item

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

    async def get_final_message(self) -> Message:
        """Waits until the stream has been read to completion and returns
        the accumulated `Message` object.
        """
        await self.until_done()
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    async def get_final_text(self) -> str:
        """Returns all `text` content blocks concatenated together.

        > [!NOTE]
        > Currently the API will only respond with a single content block.

        Will raise an error if no `text` content blocks were returned.
        """
        message = await self.get_final_message()
        text_blocks: list[str] = []
        for block in message.content:
            if block.type == "text":
                text_blocks.append(block.text)

        if not text_blocks:
            raise RuntimeError("Expected to have received at least 1 text block")

        return "".join(text_blocks)

    async def until_done(self) -> None:
        """Waits until the stream has been consumed"""
        await consume_async_iterator(self)

    # properties
    @property
    def current_message_snapshot(self) -> Message:
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    async def __stream__(self) -> AsyncIterator[MessageStreamEvent]:
        async for sse_event in self._raw_stream:
            self.__final_message_snapshot = accumulate_event(
                event=sse_event,
                current_snapshot=self.__final_message_snapshot,
            )

            events_to_fire = build_events(event=sse_event, message_snapshot=self.current_message_snapshot)
            for event in events_to_fire:
                yield event

    async def __stream_text__(self) -> AsyncIterator[str]:
        async for chunk in self:
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                yield chunk.delta.text


class AsyncMessageStreamManager:
    """Wrapper over AsyncMessageStream that is returned by `.stream()`
    so that an async context manager can be used without `await`ing the
    original client call.

    ```py
    async with client.messages.stream(...) as stream:
        async for chunk in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Awaitable[AsyncStream[RawMessageStreamEvent]],
    ) -> None:
        self.__stream: AsyncMessageStream | None = None
        self.__api_request = api_request

    async def __aenter__(self) -> AsyncMessageStream:
        raw_stream = await self.__api_request

        self.__stream = AsyncMessageStream(
            cast_to=raw_stream._cast_to,
            response=raw_stream.response,
            client=raw_stream._client,
        )

        return self.__stream

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            await self.__stream.close()


def build_events(
    *,
    event: RawMessageStreamEvent,
    message_snapshot: Message,
) -> list[MessageStreamEvent]:
    events_to_fire: list[MessageStreamEvent] = []

    if event.type == "message_start":
        events_to_fire.append(event)
    elif event.type == "message_delta":
        events_to_fire.append(event)
    elif event.type == "message_stop":
        events_to_fire.append(build(MessageStopEvent, type="message_stop", message=message_snapshot))
    elif event.type == "content_block_start":
        events_to_fire.append(event)
    elif event.type == "content_block_delta":
        events_to_fire.append(event)

        content_block = message_snapshot.content[event.index]
        if event.delta.type == "text_delta" and content_block.type == "text":
            events_to_fire.append(
                build(
                    TextEvent,
                    type="text",
                    text=event.delta.text,
                    snapshot=content_block.text,
                )
            )
        elif event.delta.type == "input_json_delta" and content_block.type == "tool_use":
            events_to_fire.append(
                build(
                    InputJsonEvent,
                    type="input_json",
                    partial_json=event.delta.partial_json,
                    snapshot=content_block.input,
                )
            )
    elif event.type == "content_block_stop":
        content_block = message_snapshot.content[event.index]

        events_to_fire.append(
            build(ContentBlockStopEvent, type="content_block_stop", index=event.index, content_block=content_block),
        )
    else:
        # we only want exhaustive checking for linters, not at runtime
        if TYPE_CHECKING:  # type: ignore[unreachable]
            assert_never(event)

    return events_to_fire


JSON_BUF_PROPERTY = "__json_buf"


def accumulate_event(
    *,
    event: RawMessageStreamEvent,
    current_snapshot: Message | None,
) -> Message:
    if current_snapshot is None:
        if event.type == "message_start":
            return Message.construct(**cast(Any, event.message.to_dict()))

        raise RuntimeError(f'Unexpected event order, got {event.type} before "message_start"')

    if event.type == "content_block_start":
        # TODO: check index
        current_snapshot.content.append(
            cast(
                ContentBlock,
                construct_type(type_=ContentBlock, value=event.content_block.model_dump()),
            ),
        )
    elif event.type == "content_block_delta":
        content = current_snapshot.content[event.index]
        if content.type == "text" and event.delta.type == "text_delta":
            content.text += event.delta.text
        elif content.type == "tool_use" and event.delta.type == "input_json_delta":
            from jiter import from_json

            # we need to keep track of the raw JSON string as well so that we can
            # re-parse it for each delta, for now we just store it as an untyped
            # property on the snapshot
            json_buf = cast(bytes, getattr(content, JSON_BUF_PROPERTY, b""))
            json_buf += bytes(event.delta.partial_json, "utf-8")

            if json_buf:
                content.input = from_json(json_buf, partial_mode=True)

            setattr(content, JSON_BUF_PROPERTY, json_buf)
    elif event.type == "message_delta":
        current_snapshot.stop_reason = event.delta.stop_reason
        current_snapshot.stop_sequence = event.delta.stop_sequence
        current_snapshot.usage.output_tokens = event.usage.output_tokens

    return current_snapshot

# === NexusCore/sandbox_repo\app\main.py ===
def add(a, b):
    """
    Add two numbers and return the result.

    Args:
    a (int or float): The first number.
    b (int or float): The second number.

    Returns:
    int or float: The sum of the two numbers.
    """
    return a + b

# === NexusCore/src\sandbox_logs\repair_20250713_125710_fixed.py ===
エラーの内容から見ると、Pythonのコードではなく、コメント部分に非ASCII文字（日本語）が含まれていることが原因でSyntaxErrorが発生しています。Pythonのコメントは基本的にASCII文字のみを使用するべきです。

また、関数の内容自体も間違っているようです。addという関数名から推測するに、この関数は2つの数値を加算することが期待されますが、現在の実装では引き算を行っています。

これらの問題を修正したコードは以下の通りです。

```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition
```

ただし、エラーメッセージにはユニットテストの実行に関する情報も含まれています。この情報から推測するに、このコードはユニットテストの一部として実行されている可能性があります。その場合、テストコードも同様に修正する必要があります。ただし、具体的なテストコードが示されていないため、その部分については具体的な修正案を提供できません。

# === NexusCore/src\sandbox_logs\repair_20250713_125723_original.py ===
エラーの内容から見ると、Pythonのコードではなく、コメント部分に非ASCII文字（日本語）が含まれていることが原因でSyntaxErrorが発生しています。Pythonのコメントは基本的にASCII文字のみを使用するべきです。

また、関数の内容自体も間違っているようです。addという関数名から推測するに、この関数は2つの数値を加算することが期待されますが、現在の実装では引き算を行っています。

これらの問題を修正したコードは以下の通りです。

```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition
```

ただし、エラーメッセージにはユニットテストの実行に関する情報も含まれています。この情報から推測するに、このコードはユニットテストの一部として実行されている可能性があります。その場合、テストコードも同様に修正する必要があります。ただし、具体的なテストコードが示されていないため、その部分については具体的な修正案を提供できません。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\sandbox_repo\app\main.py ===
def add(a, b):
    """
    Add two numbers and return the result.

    Args:
    a (int or float): The first number.
    b (int or float): The second number.

    Returns:
    int or float: The sum of the two numbers.
    """
    return a + b

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_125710_fixed.py ===
エラーの内容から見ると、Pythonのコードではなく、コメント部分に非ASCII文字（日本語）が含まれていることが原因でSyntaxErrorが発生しています。Pythonのコメントは基本的にASCII文字のみを使用するべきです。

また、関数の内容自体も間違っているようです。addという関数名から推測するに、この関数は2つの数値を加算することが期待されますが、現在の実装では引き算を行っています。

これらの問題を修正したコードは以下の通りです。

```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition
```

ただし、エラーメッセージにはユニットテストの実行に関する情報も含まれています。この情報から推測するに、このコードはユニットテストの一部として実行されている可能性があります。その場合、テストコードも同様に修正する必要があります。ただし、具体的なテストコードが示されていないため、その部分については具体的な修正案を提供できません。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_125723_original.py ===
エラーの内容から見ると、Pythonのコードではなく、コメント部分に非ASCII文字（日本語）が含まれていることが原因でSyntaxErrorが発生しています。Pythonのコメントは基本的にASCII文字のみを使用するべきです。

また、関数の内容自体も間違っているようです。addという関数名から推測するに、この関数は2つの数値を加算することが期待されますが、現在の実装では引き算を行っています。

これらの問題を修正したコードは以下の通りです。

```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition
```

ただし、エラーメッセージにはユニットテストの実行に関する情報も含まれています。この情報から推測するに、このコードはユニットテストの一部として実行されている可能性があります。その場合、テストコードも同様に修正する必要があります。ただし、具体的なテストコードが示されていないため、その部分については具体的な修正案を提供できません。

# === NexusCore/openenv\Lib\site-packages\win32\lib\sspi.py ===
"""
Helper classes for SSPI authentication via the win32security module.

SSPI authentication involves a token-exchange "dance", the exact details
of which depends on the authentication provider used.  There are also
a number of complex flags and constants that need to be used - in most
cases, there are reasonable defaults.

These classes attempt to hide these details from you until you really need
to know.  They are not designed to handle all cases, just the common ones.
If you need finer control than offered here, just use the win32security
functions directly.
"""

# Based on Roger Upole's sspi demos.
# $Id$
import sspicon
import win32security

error = win32security.error  # Re-exported alias


class _BaseAuth:
    def __init__(self):
        self.reset()

    def reset(self):
        """Reset everything to an unauthorized state"""
        self.ctxt: win32security.PyCtxtHandleType | None = None
        self.authenticated = False
        self.initiator_name = None
        self.service_name = None

        # The next seq_num for an encrypt/sign operation
        self.next_seq_num = 0

    def _get_next_seq_num(self):
        """Get the next sequence number for a transmission.  Default
        implementation is to increment a counter
        """
        ret = self.next_seq_num
        self.next_seq_num += 1
        return ret

    def encrypt(self, data):
        """Encrypt a string, returning a tuple of (encrypted_data, trailer).
        These can be passed to decrypt to get back the original string.
        """
        pkg_size_info = self.ctxt.QueryContextAttributes(sspicon.SECPKG_ATTR_SIZES)
        trailersize = pkg_size_info["SecurityTrailer"]

        encbuf = win32security.PySecBufferDescType()
        encbuf.append(win32security.PySecBufferType(len(data), sspicon.SECBUFFER_DATA))
        encbuf.append(
            win32security.PySecBufferType(trailersize, sspicon.SECBUFFER_TOKEN)
        )
        encbuf[0].Buffer = data
        self.ctxt.EncryptMessage(0, encbuf, self._get_next_seq_num())
        return encbuf[0].Buffer, encbuf[1].Buffer

    def decrypt(self, data, trailer):
        """Decrypt a previously encrypted string, returning the orignal data"""
        encbuf = win32security.PySecBufferDescType()
        encbuf.append(win32security.PySecBufferType(len(data), sspicon.SECBUFFER_DATA))
        encbuf.append(
            win32security.PySecBufferType(len(trailer), sspicon.SECBUFFER_TOKEN)
        )
        encbuf[0].Buffer = data
        encbuf[1].Buffer = trailer
        self.ctxt.DecryptMessage(encbuf, self._get_next_seq_num())
        return encbuf[0].Buffer

    def sign(self, data):
        """sign a string suitable for transmission, returning the signature.
        Passing the data and signature to verify will determine if the data
        is unchanged.
        """
        pkg_size_info = self.ctxt.QueryContextAttributes(sspicon.SECPKG_ATTR_SIZES)
        sigsize = pkg_size_info["MaxSignature"]
        sigbuf = win32security.PySecBufferDescType()
        sigbuf.append(win32security.PySecBufferType(len(data), sspicon.SECBUFFER_DATA))
        sigbuf.append(win32security.PySecBufferType(sigsize, sspicon.SECBUFFER_TOKEN))
        sigbuf[0].Buffer = data

        self.ctxt.MakeSignature(0, sigbuf, self._get_next_seq_num())
        return sigbuf[1].Buffer

    def verify(self, data, sig):
        """Verifies data and its signature.  If verification fails, an sspi.error
        will be raised.
        """
        sigbuf = win32security.PySecBufferDescType()
        sigbuf.append(win32security.PySecBufferType(len(data), sspicon.SECBUFFER_DATA))
        sigbuf.append(win32security.PySecBufferType(len(sig), sspicon.SECBUFFER_TOKEN))

        sigbuf[0].Buffer = data
        sigbuf[1].Buffer = sig
        self.ctxt.VerifySignature(sigbuf, self._get_next_seq_num())

    def unwrap(self, token):
        """
        GSSAPI's unwrap with SSPI.
        https://learn.microsoft.com/en-us/windows/win32/secauthn/sspi-kerberos-interoperability-with-gssapi

        Usable mainly with Kerberos SSPI package, but this is not enforced.

        Return the clear text, and a boolean that is True if the token was encrypted.
        """
        buffer = win32security.PySecBufferDescType()
        # This buffer will contain a "stream", which is the token coming from the other side
        buffer.append(
            win32security.PySecBufferType(len(token), sspicon.SECBUFFER_STREAM)
        )
        buffer[0].Buffer = token

        # This buffer will receive the clear, or just unwrapped text if no encryption was used.
        # Will be resized by the lib.
        buffer.append(win32security.PySecBufferType(0, sspicon.SECBUFFER_DATA))

        pfQOP = self.ctxt.DecryptMessage(buffer, self._get_next_seq_num())

        r = buffer[1].Buffer
        return r, not (pfQOP == sspicon.SECQOP_WRAP_NO_ENCRYPT)

    def wrap(self, msg, encrypt=False):
        """
        GSSAPI's wrap with SSPI.
        https://learn.microsoft.com/en-us/windows/win32/secauthn/sspi-kerberos-interoperability-with-gssapi

        Usable mainly with Kerberos SSPI package, but this is not enforced.

        Wrap a message to be sent to the other side. Encrypted if encrypt is True.
        """

        size_info = self.ctxt.QueryContextAttributes(sspicon.SECPKG_ATTR_SIZES)
        trailer_size = size_info["SecurityTrailer"]
        block_size = size_info["BlockSize"]

        buffer = win32security.PySecBufferDescType()

        # This buffer will contain unencrypted data to wrap, and maybe encrypt.
        buffer.append(win32security.PySecBufferType(len(msg), sspicon.SECBUFFER_DATA))
        buffer[0].Buffer = msg

        # Will receive the token that forms the beginning of the msg
        buffer.append(
            win32security.PySecBufferType(trailer_size, sspicon.SECBUFFER_TOKEN)
        )

        # The trailer is needed in case of block encryption
        buffer.append(
            win32security.PySecBufferType(block_size, sspicon.SECBUFFER_PADDING)
        )

        fQOP = 0 if encrypt else sspicon.SECQOP_WRAP_NO_ENCRYPT
        self.ctxt.EncryptMessage(fQOP, buffer, self._get_next_seq_num())

        # Sec token, then data, then padding
        r = buffer[1].Buffer + buffer[0].Buffer + buffer[2].Buffer
        return r

    def _amend_ctx_name(self):
        """Adds initiator and service names in the security context for ease of use"""
        if not self.authenticated:
            raise ValueError("Sec context is not completely authenticated")

        try:
            names = self.ctxt.QueryContextAttributes(sspicon.SECPKG_ATTR_NATIVE_NAMES)
        except error:
            # The SSP doesn't provide these attributes.
            pass
        else:
            self.initiator_name, self.service_name = names


class ClientAuth(_BaseAuth):
    """Manages the client side of an SSPI authentication handshake"""

    def __init__(
        self,
        pkg_name,  # Name of the package to used.
        client_name=None,  # User for whom credentials are used.
        auth_info=None,  # or a tuple of (username, domain, password)
        targetspn=None,  # Target security context provider name.
        scflags=None,  # security context flags
        datarep=sspicon.SECURITY_NETWORK_DREP,
    ):
        if scflags is None:
            scflags = (
                sspicon.ISC_REQ_INTEGRITY
                | sspicon.ISC_REQ_SEQUENCE_DETECT
                | sspicon.ISC_REQ_REPLAY_DETECT
                | sspicon.ISC_REQ_CONFIDENTIALITY
            )
        self.scflags = scflags
        self.datarep = datarep
        self.targetspn = targetspn
        self.pkg_info = win32security.QuerySecurityPackageInfo(pkg_name)
        (
            self.credentials,
            self.credentials_expiry,
        ) = win32security.AcquireCredentialsHandle(
            client_name,
            self.pkg_info["Name"],
            sspicon.SECPKG_CRED_OUTBOUND,
            None,
            auth_info,
        )
        _BaseAuth.__init__(self)

    def authorize(self, sec_buffer_in):
        """Perform *one* step of the client authentication process. Pass None for the first round"""
        if sec_buffer_in is not None and not isinstance(
            sec_buffer_in, win32security.PySecBufferDescType
        ):
            # User passed us the raw data - wrap it into a SecBufferDesc
            sec_buffer_new = win32security.PySecBufferDescType()
            tokenbuf = win32security.PySecBufferType(
                self.pkg_info["MaxToken"], sspicon.SECBUFFER_TOKEN
            )
            tokenbuf.Buffer = sec_buffer_in
            sec_buffer_new.append(tokenbuf)
            sec_buffer_in = sec_buffer_new
        sec_buffer_out = win32security.PySecBufferDescType()
        tokenbuf = win32security.PySecBufferType(
            self.pkg_info["MaxToken"], sspicon.SECBUFFER_TOKEN
        )
        sec_buffer_out.append(tokenbuf)
        ## input context handle should be NULL on first call
        ctxtin = self.ctxt
        if self.ctxt is None:
            self.ctxt = win32security.PyCtxtHandleType()
        err, attr, exp = win32security.InitializeSecurityContext(
            self.credentials,
            ctxtin,
            self.targetspn,
            self.scflags,
            self.datarep,
            sec_buffer_in,
            self.ctxt,
            sec_buffer_out,
        )
        # Stash these away incase someone needs to know the state from the
        # final call.
        self.ctxt_attr = attr
        self.ctxt_expiry = exp

        if err in (sspicon.SEC_I_COMPLETE_NEEDED, sspicon.SEC_I_COMPLETE_AND_CONTINUE):
            self.ctxt.CompleteAuthToken(sec_buffer_out)

        self.authenticated = err == 0
        if self.authenticated:
            self._amend_ctx_name()

        return err, sec_buffer_out


class ServerAuth(_BaseAuth):
    """Manages the server side of an SSPI authentication handshake"""

    def __init__(
        self, pkg_name, spn=None, scflags=None, datarep=sspicon.SECURITY_NETWORK_DREP
    ):
        self.spn = spn
        self.datarep = datarep

        if scflags is None:
            scflags = (
                sspicon.ASC_REQ_INTEGRITY
                | sspicon.ASC_REQ_SEQUENCE_DETECT
                | sspicon.ASC_REQ_REPLAY_DETECT
                | sspicon.ASC_REQ_CONFIDENTIALITY
            )
        # Should we default to sspicon.KerbAddExtraCredentialsMessage
        # if pkg_name=='Kerberos'?
        self.scflags = scflags

        self.pkg_info = win32security.QuerySecurityPackageInfo(pkg_name)

        (
            self.credentials,
            self.credentials_expiry,
        ) = win32security.AcquireCredentialsHandle(
            spn, self.pkg_info["Name"], sspicon.SECPKG_CRED_INBOUND, None, None
        )
        _BaseAuth.__init__(self)

    def authorize(self, sec_buffer_in):
        """Perform *one* step of the server authentication process."""
        if sec_buffer_in is not None and not isinstance(
            sec_buffer_in, win32security.PySecBufferDescType
        ):
            # User passed us the raw data - wrap it into a SecBufferDesc
            sec_buffer_new = win32security.PySecBufferDescType()
            tokenbuf = win32security.PySecBufferType(
                self.pkg_info["MaxToken"], sspicon.SECBUFFER_TOKEN
            )
            tokenbuf.Buffer = sec_buffer_in
            sec_buffer_new.append(tokenbuf)
            sec_buffer_in = sec_buffer_new

        sec_buffer_out = win32security.PySecBufferDescType()
        tokenbuf = win32security.PySecBufferType(
            self.pkg_info["MaxToken"], sspicon.SECBUFFER_TOKEN
        )
        sec_buffer_out.append(tokenbuf)
        ## input context handle is None initially, then handle returned from last call thereafter
        ctxtin = self.ctxt
        if self.ctxt is None:
            self.ctxt = win32security.PyCtxtHandleType()
        err, attr, exp = win32security.AcceptSecurityContext(
            self.credentials,
            ctxtin,
            sec_buffer_in,
            self.scflags,
            self.datarep,
            self.ctxt,
            sec_buffer_out,
        )

        # Stash these away incase someone needs to know the state from the
        # final call.
        self.ctxt_attr = attr
        self.ctxt_expiry = exp

        if err in (sspicon.SEC_I_COMPLETE_NEEDED, sspicon.SEC_I_COMPLETE_AND_CONTINUE):
            self.ctxt.CompleteAuthToken(sec_buffer_out)

        self.authenticated = err == 0
        if self.authenticated:
            self._amend_ctx_name()

        return err, sec_buffer_out


if __name__ == "__main__":
    # This is the security package (the security support provider / the security backend)
    # we want to use for this example.
    ssp = "Kerberos"  # or "NTLM" or "Negotiate" which enable negotiation between
    # Kerberos (prefered) and NTLM (if not supported on the other side).

    flags = (
        sspicon.ISC_REQ_MUTUAL_AUTH
        | sspicon.ISC_REQ_INTEGRITY  # mutual authentication
        | sspicon.ISC_REQ_SEQUENCE_DETECT  # check for integrity
        | sspicon.ISC_REQ_CONFIDENTIALITY  # enable out-of-order messages
        | sspicon.ISC_REQ_REPLAY_DETECT  # request confidentiality  # request replay detection
    )

    # Get our identity, mandatory for the Kerberos case *for this example*
    # Kerberos cannot be used if we don't tell it the target we want
    # to authenticate to.
    cred_handle, exp = win32security.AcquireCredentialsHandle(
        None, ssp, sspicon.SECPKG_CRED_INBOUND, None, None
    )
    cred = cred_handle.QueryCredentialsAttributes(sspicon.SECPKG_CRED_ATTR_NAMES)
    print("We are:", cred)

    # Setup the 2 contexts. In real life, only one is needed: the other one is
    # created in the process we want to communicate with.
    sspiclient = ClientAuth(ssp, scflags=flags, targetspn=cred)
    sspiserver = ServerAuth(ssp, scflags=flags)

    print(
        "SSP : {} ({})".format(
            sspiclient.pkg_info["Name"], sspiclient.pkg_info["Comment"]
        )
    )

    # Perform the authentication dance, each loop exchanging more information
    # on the way to completing authentication.
    sec_buffer = None
    client_step = 0
    server_step = 0
    while not sspiclient.authenticated or (sec_buffer and len(sec_buffer[0].Buffer)):
        client_step += 1
        err, sec_buffer = sspiclient.authorize(sec_buffer)
        print("Client step %s" % client_step)
        if sspiserver.authenticated and len(sec_buffer[0].Buffer) == 0:
            break

        server_step += 1
        err, sec_buffer = sspiserver.authorize(sec_buffer)
        print("Server step %s" % server_step)

    # Authentication process is finished.
    print("Initiator name from the service side:", sspiserver.initiator_name)
    print("Service name from the client side:   ", sspiclient.service_name)

    data = b"hello"

    # Simple signature, not compatible with GSSAPI.
    sig = sspiclient.sign(data)
    sspiserver.verify(data, sig)

    # Encryption
    encrypted, sig = sspiclient.encrypt(data)
    decrypted = sspiserver.decrypt(encrypted, sig)
    assert decrypted == data

    # GSSAPI wrapping, no encryption (NTLM always encrypts)
    wrapped = sspiclient.wrap(data)
    unwrapped, was_encrypted = sspiserver.unwrap(wrapped)
    print("encrypted ?", was_encrypted)
    assert data == unwrapped

    # GSSAPI wrapping, with encryption
    wrapped = sspiserver.wrap(data, encrypt=True)
    unwrapped, was_encrypted = sspiclient.unwrap(wrapped)
    print("encrypted ?", was_encrypted)
    assert data == unwrapped

    print("cool!")

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\sspi.py ===
"""
Helper classes for SSPI authentication via the win32security module.

SSPI authentication involves a token-exchange "dance", the exact details
of which depends on the authentication provider used.  There are also
a number of complex flags and constants that need to be used - in most
cases, there are reasonable defaults.

These classes attempt to hide these details from you until you really need
to know.  They are not designed to handle all cases, just the common ones.
If you need finer control than offered here, just use the win32security
functions directly.
"""

# Based on Roger Upole's sspi demos.
# $Id$
import sspicon
import win32security

error = win32security.error  # Re-exported alias


class _BaseAuth:
    def __init__(self):
        self.reset()

    def reset(self):
        """Reset everything to an unauthorized state"""
        self.ctxt: win32security.PyCtxtHandleType | None = None
        self.authenticated = False
        self.initiator_name = None
        self.service_name = None

        # The next seq_num for an encrypt/sign operation
        self.next_seq_num = 0

    def _get_next_seq_num(self):
        """Get the next sequence number for a transmission.  Default
        implementation is to increment a counter
        """
        ret = self.next_seq_num
        self.next_seq_num += 1
        return ret

    def encrypt(self, data):
        """Encrypt a string, returning a tuple of (encrypted_data, trailer).
        These can be passed to decrypt to get back the original string.
        """
        pkg_size_info = self.ctxt.QueryContextAttributes(sspicon.SECPKG_ATTR_SIZES)
        trailersize = pkg_size_info["SecurityTrailer"]

        encbuf = win32security.PySecBufferDescType()
        encbuf.append(win32security.PySecBufferType(len(data), sspicon.SECBUFFER_DATA))
        encbuf.append(
            win32security.PySecBufferType(trailersize, sspicon.SECBUFFER_TOKEN)
        )
        encbuf[0].Buffer = data
        self.ctxt.EncryptMessage(0, encbuf, self._get_next_seq_num())
        return encbuf[0].Buffer, encbuf[1].Buffer

    def decrypt(self, data, trailer):
        """Decrypt a previously encrypted string, returning the orignal data"""
        encbuf = win32security.PySecBufferDescType()
        encbuf.append(win32security.PySecBufferType(len(data), sspicon.SECBUFFER_DATA))
        encbuf.append(
            win32security.PySecBufferType(len(trailer), sspicon.SECBUFFER_TOKEN)
        )
        encbuf[0].Buffer = data
        encbuf[1].Buffer = trailer
        self.ctxt.DecryptMessage(encbuf, self._get_next_seq_num())
        return encbuf[0].Buffer

    def sign(self, data):
        """sign a string suitable for transmission, returning the signature.
        Passing the data and signature to verify will determine if the data
        is unchanged.
        """
        pkg_size_info = self.ctxt.QueryContextAttributes(sspicon.SECPKG_ATTR_SIZES)
        sigsize = pkg_size_info["MaxSignature"]
        sigbuf = win32security.PySecBufferDescType()
        sigbuf.append(win32security.PySecBufferType(len(data), sspicon.SECBUFFER_DATA))
        sigbuf.append(win32security.PySecBufferType(sigsize, sspicon.SECBUFFER_TOKEN))
        sigbuf[0].Buffer = data

        self.ctxt.MakeSignature(0, sigbuf, self._get_next_seq_num())
        return sigbuf[1].Buffer

    def verify(self, data, sig):
        """Verifies data and its signature.  If verification fails, an sspi.error
        will be raised.
        """
        sigbuf = win32security.PySecBufferDescType()
        sigbuf.append(win32security.PySecBufferType(len(data), sspicon.SECBUFFER_DATA))
        sigbuf.append(win32security.PySecBufferType(len(sig), sspicon.SECBUFFER_TOKEN))

        sigbuf[0].Buffer = data
        sigbuf[1].Buffer = sig
        self.ctxt.VerifySignature(sigbuf, self._get_next_seq_num())

    def unwrap(self, token):
        """
        GSSAPI's unwrap with SSPI.
        https://learn.microsoft.com/en-us/windows/win32/secauthn/sspi-kerberos-interoperability-with-gssapi

        Usable mainly with Kerberos SSPI package, but this is not enforced.

        Return the clear text, and a boolean that is True if the token was encrypted.
        """
        buffer = win32security.PySecBufferDescType()
        # This buffer will contain a "stream", which is the token coming from the other side
        buffer.append(
            win32security.PySecBufferType(len(token), sspicon.SECBUFFER_STREAM)
        )
        buffer[0].Buffer = token

        # This buffer will receive the clear, or just unwrapped text if no encryption was used.
        # Will be resized by the lib.
        buffer.append(win32security.PySecBufferType(0, sspicon.SECBUFFER_DATA))

        pfQOP = self.ctxt.DecryptMessage(buffer, self._get_next_seq_num())

        r = buffer[1].Buffer
        return r, not (pfQOP == sspicon.SECQOP_WRAP_NO_ENCRYPT)

    def wrap(self, msg, encrypt=False):
        """
        GSSAPI's wrap with SSPI.
        https://learn.microsoft.com/en-us/windows/win32/secauthn/sspi-kerberos-interoperability-with-gssapi

        Usable mainly with Kerberos SSPI package, but this is not enforced.

        Wrap a message to be sent to the other side. Encrypted if encrypt is True.
        """

        size_info = self.ctxt.QueryContextAttributes(sspicon.SECPKG_ATTR_SIZES)
        trailer_size = size_info["SecurityTrailer"]
        block_size = size_info["BlockSize"]

        buffer = win32security.PySecBufferDescType()

        # This buffer will contain unencrypted data to wrap, and maybe encrypt.
        buffer.append(win32security.PySecBufferType(len(msg), sspicon.SECBUFFER_DATA))
        buffer[0].Buffer = msg

        # Will receive the token that forms the beginning of the msg
        buffer.append(
            win32security.PySecBufferType(trailer_size, sspicon.SECBUFFER_TOKEN)
        )

        # The trailer is needed in case of block encryption
        buffer.append(
            win32security.PySecBufferType(block_size, sspicon.SECBUFFER_PADDING)
        )

        fQOP = 0 if encrypt else sspicon.SECQOP_WRAP_NO_ENCRYPT
        self.ctxt.EncryptMessage(fQOP, buffer, self._get_next_seq_num())

        # Sec token, then data, then padding
        r = buffer[1].Buffer + buffer[0].Buffer + buffer[2].Buffer
        return r

    def _amend_ctx_name(self):
        """Adds initiator and service names in the security context for ease of use"""
        if not self.authenticated:
            raise ValueError("Sec context is not completely authenticated")

        try:
            names = self.ctxt.QueryContextAttributes(sspicon.SECPKG_ATTR_NATIVE_NAMES)
        except error:
            # The SSP doesn't provide these attributes.
            pass
        else:
            self.initiator_name, self.service_name = names


class ClientAuth(_BaseAuth):
    """Manages the client side of an SSPI authentication handshake"""

    def __init__(
        self,
        pkg_name,  # Name of the package to used.
        client_name=None,  # User for whom credentials are used.
        auth_info=None,  # or a tuple of (username, domain, password)
        targetspn=None,  # Target security context provider name.
        scflags=None,  # security context flags
        datarep=sspicon.SECURITY_NETWORK_DREP,
    ):
        if scflags is None:
            scflags = (
                sspicon.ISC_REQ_INTEGRITY
                | sspicon.ISC_REQ_SEQUENCE_DETECT
                | sspicon.ISC_REQ_REPLAY_DETECT
                | sspicon.ISC_REQ_CONFIDENTIALITY
            )
        self.scflags = scflags
        self.datarep = datarep
        self.targetspn = targetspn
        self.pkg_info = win32security.QuerySecurityPackageInfo(pkg_name)
        (
            self.credentials,
            self.credentials_expiry,
        ) = win32security.AcquireCredentialsHandle(
            client_name,
            self.pkg_info["Name"],
            sspicon.SECPKG_CRED_OUTBOUND,
            None,
            auth_info,
        )
        _BaseAuth.__init__(self)

    def authorize(self, sec_buffer_in):
        """Perform *one* step of the client authentication process. Pass None for the first round"""
        if sec_buffer_in is not None and not isinstance(
            sec_buffer_in, win32security.PySecBufferDescType
        ):
            # User passed us the raw data - wrap it into a SecBufferDesc
            sec_buffer_new = win32security.PySecBufferDescType()
            tokenbuf = win32security.PySecBufferType(
                self.pkg_info["MaxToken"], sspicon.SECBUFFER_TOKEN
            )
            tokenbuf.Buffer = sec_buffer_in
            sec_buffer_new.append(tokenbuf)
            sec_buffer_in = sec_buffer_new
        sec_buffer_out = win32security.PySecBufferDescType()
        tokenbuf = win32security.PySecBufferType(
            self.pkg_info["MaxToken"], sspicon.SECBUFFER_TOKEN
        )
        sec_buffer_out.append(tokenbuf)
        ## input context handle should be NULL on first call
        ctxtin = self.ctxt
        if self.ctxt is None:
            self.ctxt = win32security.PyCtxtHandleType()
        err, attr, exp = win32security.InitializeSecurityContext(
            self.credentials,
            ctxtin,
            self.targetspn,
            self.scflags,
            self.datarep,
            sec_buffer_in,
            self.ctxt,
            sec_buffer_out,
        )
        # Stash these away incase someone needs to know the state from the
        # final call.
        self.ctxt_attr = attr
        self.ctxt_expiry = exp

        if err in (sspicon.SEC_I_COMPLETE_NEEDED, sspicon.SEC_I_COMPLETE_AND_CONTINUE):
            self.ctxt.CompleteAuthToken(sec_buffer_out)

        self.authenticated = err == 0
        if self.authenticated:
            self._amend_ctx_name()

        return err, sec_buffer_out


class ServerAuth(_BaseAuth):
    """Manages the server side of an SSPI authentication handshake"""

    def __init__(
        self, pkg_name, spn=None, scflags=None, datarep=sspicon.SECURITY_NETWORK_DREP
    ):
        self.spn = spn
        self.datarep = datarep

        if scflags is None:
            scflags = (
                sspicon.ASC_REQ_INTEGRITY
                | sspicon.ASC_REQ_SEQUENCE_DETECT
                | sspicon.ASC_REQ_REPLAY_DETECT
                | sspicon.ASC_REQ_CONFIDENTIALITY
            )
        # Should we default to sspicon.KerbAddExtraCredentialsMessage
        # if pkg_name=='Kerberos'?
        self.scflags = scflags

        self.pkg_info = win32security.QuerySecurityPackageInfo(pkg_name)

        (
            self.credentials,
            self.credentials_expiry,
        ) = win32security.AcquireCredentialsHandle(
            spn, self.pkg_info["Name"], sspicon.SECPKG_CRED_INBOUND, None, None
        )
        _BaseAuth.__init__(self)

    def authorize(self, sec_buffer_in):
        """Perform *one* step of the server authentication process."""
        if sec_buffer_in is not None and not isinstance(
            sec_buffer_in, win32security.PySecBufferDescType
        ):
            # User passed us the raw data - wrap it into a SecBufferDesc
            sec_buffer_new = win32security.PySecBufferDescType()
            tokenbuf = win32security.PySecBufferType(
                self.pkg_info["MaxToken"], sspicon.SECBUFFER_TOKEN
            )
            tokenbuf.Buffer = sec_buffer_in
            sec_buffer_new.append(tokenbuf)
            sec_buffer_in = sec_buffer_new

        sec_buffer_out = win32security.PySecBufferDescType()
        tokenbuf = win32security.PySecBufferType(
            self.pkg_info["MaxToken"], sspicon.SECBUFFER_TOKEN
        )
        sec_buffer_out.append(tokenbuf)
        ## input context handle is None initially, then handle returned from last call thereafter
        ctxtin = self.ctxt
        if self.ctxt is None:
            self.ctxt = win32security.PyCtxtHandleType()
        err, attr, exp = win32security.AcceptSecurityContext(
            self.credentials,
            ctxtin,
            sec_buffer_in,
            self.scflags,
            self.datarep,
            self.ctxt,
            sec_buffer_out,
        )

        # Stash these away incase someone needs to know the state from the
        # final call.
        self.ctxt_attr = attr
        self.ctxt_expiry = exp

        if err in (sspicon.SEC_I_COMPLETE_NEEDED, sspicon.SEC_I_COMPLETE_AND_CONTINUE):
            self.ctxt.CompleteAuthToken(sec_buffer_out)

        self.authenticated = err == 0
        if self.authenticated:
            self._amend_ctx_name()

        return err, sec_buffer_out


if __name__ == "__main__":
    # This is the security package (the security support provider / the security backend)
    # we want to use for this example.
    ssp = "Kerberos"  # or "NTLM" or "Negotiate" which enable negotiation between
    # Kerberos (prefered) and NTLM (if not supported on the other side).

    flags = (
        sspicon.ISC_REQ_MUTUAL_AUTH
        | sspicon.ISC_REQ_INTEGRITY  # mutual authentication
        | sspicon.ISC_REQ_SEQUENCE_DETECT  # check for integrity
        | sspicon.ISC_REQ_CONFIDENTIALITY  # enable out-of-order messages
        | sspicon.ISC_REQ_REPLAY_DETECT  # request confidentiality  # request replay detection
    )

    # Get our identity, mandatory for the Kerberos case *for this example*
    # Kerberos cannot be used if we don't tell it the target we want
    # to authenticate to.
    cred_handle, exp = win32security.AcquireCredentialsHandle(
        None, ssp, sspicon.SECPKG_CRED_INBOUND, None, None
    )
    cred = cred_handle.QueryCredentialsAttributes(sspicon.SECPKG_CRED_ATTR_NAMES)
    print("We are:", cred)

    # Setup the 2 contexts. In real life, only one is needed: the other one is
    # created in the process we want to communicate with.
    sspiclient = ClientAuth(ssp, scflags=flags, targetspn=cred)
    sspiserver = ServerAuth(ssp, scflags=flags)

    print(
        "SSP : {} ({})".format(
            sspiclient.pkg_info["Name"], sspiclient.pkg_info["Comment"]
        )
    )

    # Perform the authentication dance, each loop exchanging more information
    # on the way to completing authentication.
    sec_buffer = None
    client_step = 0
    server_step = 0
    while not sspiclient.authenticated or (sec_buffer and len(sec_buffer[0].Buffer)):
        client_step += 1
        err, sec_buffer = sspiclient.authorize(sec_buffer)
        print("Client step %s" % client_step)
        if sspiserver.authenticated and len(sec_buffer[0].Buffer) == 0:
            break

        server_step += 1
        err, sec_buffer = sspiserver.authorize(sec_buffer)
        print("Server step %s" % server_step)

    # Authentication process is finished.
    print("Initiator name from the service side:", sspiserver.initiator_name)
    print("Service name from the client side:   ", sspiclient.service_name)

    data = b"hello"

    # Simple signature, not compatible with GSSAPI.
    sig = sspiclient.sign(data)
    sspiserver.verify(data, sig)

    # Encryption
    encrypted, sig = sspiclient.encrypt(data)
    decrypted = sspiserver.decrypt(encrypted, sig)
    assert decrypted == data

    # GSSAPI wrapping, no encryption (NTLM always encrypts)
    wrapped = sspiclient.wrap(data)
    unwrapped, was_encrypted = sspiserver.unwrap(wrapped)
    print("encrypted ?", was_encrypted)
    assert data == unwrapped

    # GSSAPI wrapping, with encryption
    wrapped = sspiserver.wrap(data, encrypt=True)
    unwrapped, was_encrypted = sspiclient.unwrap(wrapped)
    print("encrypted ?", was_encrypted)
    assert data == unwrapped

    print("cool!")

# === NexusCore/tools\exports\export_20250803_114325\combined_43.py ===

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\vertex\_beta.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ._beta_messages import (
    Messages,
    AsyncMessages,
    MessagesWithRawResponse,
    AsyncMessagesWithRawResponse,
    MessagesWithStreamingResponse,
    AsyncMessagesWithStreamingResponse,
)

__all__ = ["Beta", "AsyncBeta"]


class Beta(SyncAPIResource):
    @cached_property
    def messages(self) -> Messages:
        return Messages(self._client)

    @cached_property
    def with_raw_response(self) -> BetaWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#accessing-raw-response-data-eg-headers
        """
        return BetaWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> BetaWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#with_streaming_response
        """
        return BetaWithStreamingResponse(self)


class AsyncBeta(AsyncAPIResource):
    @cached_property
    def messages(self) -> AsyncMessages:
        return AsyncMessages(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncBetaWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#accessing-raw-response-data-eg-headers
        """
        return AsyncBetaWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncBetaWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#with_streaming_response
        """
        return AsyncBetaWithStreamingResponse(self)


class BetaWithRawResponse:
    def __init__(self, beta: Beta) -> None:
        self._beta = beta

    @cached_property
    def messages(self) -> MessagesWithRawResponse:
        return MessagesWithRawResponse(self._beta.messages)


class AsyncBetaWithRawResponse:
    def __init__(self, beta: AsyncBeta) -> None:
        self._beta = beta

    @cached_property
    def messages(self) -> AsyncMessagesWithRawResponse:
        return AsyncMessagesWithRawResponse(self._beta.messages)


class BetaWithStreamingResponse:
    def __init__(self, beta: Beta) -> None:
        self._beta = beta

    @cached_property
    def messages(self) -> MessagesWithStreamingResponse:
        return MessagesWithStreamingResponse(self._beta.messages)


class AsyncBetaWithStreamingResponse:
    def __init__(self, beta: AsyncBeta) -> None:
        self._beta = beta

    @cached_property
    def messages(self) -> AsyncMessagesWithStreamingResponse:
        return AsyncMessagesWithStreamingResponse(self._beta.messages)

# === NexusCore/openenv\Lib\site-packages\IPython\lib\clipboard.py ===
""" Utilities for accessing the platform's clipboard.
"""

import os
import subprocess

from IPython.core.error import TryNext
import IPython.utils.py3compat as py3compat


class ClipboardEmpty(ValueError):
    pass


def win32_clipboard_get():
    """ Get the current clipboard's text on Windows.

    Requires Mark Hammond's pywin32 extensions.
    """
    try:
        import win32clipboard
    except ImportError as e:
        raise TryNext("Getting text from the clipboard requires the pywin32 "
                      "extensions: http://sourceforge.net/projects/pywin32/") from e
    win32clipboard.OpenClipboard()
    try:
        text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
    except (TypeError, win32clipboard.error):
        try:
            text = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
            text = py3compat.cast_unicode(text, py3compat.DEFAULT_ENCODING)
        except (TypeError, win32clipboard.error) as e:
            raise ClipboardEmpty from e
    finally:
        win32clipboard.CloseClipboard()
    return text


def osx_clipboard_get() -> str:
    """ Get the clipboard's text on OS X.
    """
    p = subprocess.Popen(['pbpaste', '-Prefer', 'ascii'],
        stdout=subprocess.PIPE)
    bytes_, stderr = p.communicate()
    # Text comes in with old Mac \r line endings. Change them to \n.
    bytes_ = bytes_.replace(b'\r', b'\n')
    text = py3compat.decode(bytes_)
    return text


def tkinter_clipboard_get():
    """ Get the clipboard's text using Tkinter.

    This is the default on systems that are not Windows or OS X. It may
    interfere with other UI toolkits and should be replaced with an
    implementation that uses that toolkit.
    """
    try:
        from tkinter import Tk, TclError 
    except ImportError as e:
        raise TryNext("Getting text from the clipboard on this platform requires tkinter.") from e
        
    root = Tk()
    root.withdraw()
    try:
        text = root.clipboard_get()
    except TclError as e:
        raise ClipboardEmpty from e
    finally:
        root.destroy()
    text = py3compat.cast_unicode(text, py3compat.DEFAULT_ENCODING)
    return text


def wayland_clipboard_get():
    """Get the clipboard's text under Wayland using wl-paste command.

    This requires Wayland and wl-clipboard installed and running.
    """
    if os.environ.get("XDG_SESSION_TYPE") != "wayland":
        raise TryNext("wayland is not detected")

    try:
        with subprocess.Popen(["wl-paste"], stdout=subprocess.PIPE) as p:
            raw, err = p.communicate()
            if p.wait():
                raise TryNext(err)
    except FileNotFoundError as e:
        raise TryNext(
            "Getting text from the clipboard under Wayland requires the wl-clipboard "
            "extension: https://github.com/bugaevc/wl-clipboard"
        ) from e

    if not raw:
        raise ClipboardEmpty

    try:
        text = py3compat.decode(raw)
    except UnicodeDecodeError as e:
        raise ClipboardEmpty from e

    return text

# === NexusCore/openenv\Lib\site-packages\pydantic\types.py ===
"""The types module contains custom types used by pydantic."""

from __future__ import annotations as _annotations

import base64
import dataclasses as _dataclasses
import re
from collections.abc import Hashable, Iterator
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from re import Pattern
from types import ModuleType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    ClassVar,
    Generic,
    Literal,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

import annotated_types
from annotated_types import BaseMetadata, MaxLen, MinLen
from pydantic_core import CoreSchema, PydanticCustomError, SchemaSerializer, core_schema
from typing_extensions import Protocol, TypeAlias, TypeAliasType, deprecated, get_args, get_origin
from typing_inspection.introspection import is_union_origin

from ._internal import _fields, _internal_dataclass, _utils, _validators
from ._migration import getattr_migration
from .annotated_handlers import GetCoreSchemaHandler, GetJsonSchemaHandler
from .errors import PydanticUserError
from .json_schema import JsonSchemaValue
from .warnings import PydanticDeprecatedSince20

if TYPE_CHECKING:
    from ._internal._core_metadata import CoreMetadata

__all__ = (
    'Strict',
    'StrictStr',
    'SocketPath',
    'conbytes',
    'conlist',
    'conset',
    'confrozenset',
    'constr',
    'ImportString',
    'conint',
    'PositiveInt',
    'NegativeInt',
    'NonNegativeInt',
    'NonPositiveInt',
    'confloat',
    'PositiveFloat',
    'NegativeFloat',
    'NonNegativeFloat',
    'NonPositiveFloat',
    'FiniteFloat',
    'condecimal',
    'UUID1',
    'UUID3',
    'UUID4',
    'UUID5',
    'UUID6',
    'UUID7',
    'UUID8',
    'FilePath',
    'DirectoryPath',
    'NewPath',
    'Json',
    'Secret',
    'SecretStr',
    'SecretBytes',
    'StrictBool',
    'StrictBytes',
    'StrictInt',
    'StrictFloat',
    'PaymentCardNumber',
    'ByteSize',
    'PastDate',
    'FutureDate',
    'PastDatetime',
    'FutureDatetime',
    'condate',
    'AwareDatetime',
    'NaiveDatetime',
    'AllowInfNan',
    'EncoderProtocol',
    'EncodedBytes',
    'EncodedStr',
    'Base64Encoder',
    'Base64Bytes',
    'Base64Str',
    'Base64UrlBytes',
    'Base64UrlStr',
    'GetPydanticSchema',
    'StringConstraints',
    'Tag',
    'Discriminator',
    'JsonValue',
    'OnErrorOmit',
    'FailFast',
)


T = TypeVar('T')


@_dataclasses.dataclass
class Strict(_fields.PydanticMetadata, BaseMetadata):
    """!!! abstract "Usage Documentation"
        [Strict Mode with `Annotated` `Strict`](../concepts/strict_mode.md#strict-mode-with-annotated-strict)

    A field metadata class to indicate that a field should be validated in strict mode.
    Use this class as an annotation via [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated), as seen below.

    Attributes:
        strict: Whether to validate the field in strict mode.

    Example:
        ```python
        from typing import Annotated

        from pydantic.types import Strict

        StrictBool = Annotated[bool, Strict()]
        ```
    """

    strict: bool = True

    def __hash__(self) -> int:
        return hash(self.strict)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ BOOLEAN TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

StrictBool = Annotated[bool, Strict()]
"""A boolean that must be either ``True`` or ``False``."""

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ INTEGER TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def conint(
    *,
    strict: bool | None = None,
    gt: int | None = None,
    ge: int | None = None,
    lt: int | None = None,
    le: int | None = None,
    multiple_of: int | None = None,
) -> type[int]:
    """
    !!! warning "Discouraged"
        This function is **discouraged** in favor of using
        [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated) with
        [`Field`][pydantic.fields.Field] instead.

        This function will be **deprecated** in Pydantic 3.0.

        The reason is that `conint` returns a type, which doesn't play well with static analysis tools.

        === ":x: Don't do this"
            ```python
            from pydantic import BaseModel, conint

            class Foo(BaseModel):
                bar: conint(strict=True, gt=0)
            ```

        === ":white_check_mark: Do this"
            ```python
            from typing import Annotated

            from pydantic import BaseModel, Field

            class Foo(BaseModel):
                bar: Annotated[int, Field(strict=True, gt=0)]
            ```

    A wrapper around `int` that allows for additional constraints.

    Args:
        strict: Whether to validate the integer in strict mode. Defaults to `None`.
        gt: The value must be greater than this.
        ge: The value must be greater than or equal to this.
        lt: The value must be less than this.
        le: The value must be less than or equal to this.
        multiple_of: The value must be a multiple of this.

    Returns:
        The wrapped integer type.

    ```python
    from pydantic import BaseModel, ValidationError, conint

    class ConstrainedExample(BaseModel):
        constrained_int: conint(gt=1)

    m = ConstrainedExample(constrained_int=2)
    print(repr(m))
    #> ConstrainedExample(constrained_int=2)

    try:
        ConstrainedExample(constrained_int=0)
    except ValidationError as e:
        print(e.errors())
        '''
        [
            {
                'type': 'greater_than',
                'loc': ('constrained_int',),
                'msg': 'Input should be greater than 1',
                'input': 0,
                'ctx': {'gt': 1},
                'url': 'https://errors.pydantic.dev/2/v/greater_than',
            }
        ]
        '''
    ```

    """  # noqa: D212
    return Annotated[  # pyright: ignore[reportReturnType]
        int,
        Strict(strict) if strict is not None else None,
        annotated_types.Interval(gt=gt, ge=ge, lt=lt, le=le),
        annotated_types.MultipleOf(multiple_of) if multiple_of is not None else None,
    ]


PositiveInt = Annotated[int, annotated_types.Gt(0)]
"""An integer that must be greater than zero.

```python
from pydantic import BaseModel, PositiveInt, ValidationError

class Model(BaseModel):
    positive_int: PositiveInt

m = Model(positive_int=1)
print(repr(m))
#> Model(positive_int=1)

try:
    Model(positive_int=-1)
except ValidationError as e:
    print(e.errors())
    '''
    [
        {
            'type': 'greater_than',
            'loc': ('positive_int',),
            'msg': 'Input should be greater than 0',
            'input': -1,
            'ctx': {'gt': 0},
            'url': 'https://errors.pydantic.dev/2/v/greater_than',
        }
    ]
    '''
```
"""
NegativeInt = Annotated[int, annotated_types.Lt(0)]
"""An integer that must be less than zero.

```python
from pydantic import BaseModel, NegativeInt, ValidationError

class Model(BaseModel):
    negative_int: NegativeInt

m = Model(negative_int=-1)
print(repr(m))
#> Model(negative_int=-1)

try:
    Model(negative_int=1)
except ValidationError as e:
    print(e.errors())
    '''
    [
        {
            'type': 'less_than',
            'loc': ('negative_int',),
            'msg': 'Input should be less than 0',
            'input': 1,
            'ctx': {'lt': 0},
            'url': 'https://errors.pydantic.dev/2/v/less_than',
        }
    ]
    '''
```
"""
NonPositiveInt = Annotated[int, annotated_types.Le(0)]
"""An integer that must be less than or equal to zero.

```python
from pydantic import BaseModel, NonPositiveInt, ValidationError

class Model(BaseModel):
    non_positive_int: NonPositiveInt

m = Model(non_positive_int=0)
print(repr(m))
#> Model(non_positive_int=0)

try:
    Model(non_positive_int=1)
except ValidationError as e:
    print(e.errors())
    '''
    [
        {
            'type': 'less_than_equal',
            'loc': ('non_positive_int',),
            'msg': 'Input should be less than or equal to 0',
            'input': 1,
            'ctx': {'le': 0},
            'url': 'https://errors.pydantic.dev/2/v/less_than_equal',
        }
    ]
    '''
```
"""
NonNegativeInt = Annotated[int, annotated_types.Ge(0)]
"""An integer that must be greater than or equal to zero.

```python
from pydantic import BaseModel, NonNegativeInt, ValidationError

class Model(BaseModel):
    non_negative_int: NonNegativeInt

m = Model(non_negative_int=0)
print(repr(m))
#> Model(non_negative_int=0)

try:
    Model(non_negative_int=-1)
except ValidationError as e:
    print(e.errors())
    '''
    [
        {
            'type': 'greater_than_equal',
            'loc': ('non_negative_int',),
            'msg': 'Input should be greater than or equal to 0',
            'input': -1,
            'ctx': {'ge': 0},
            'url': 'https://errors.pydantic.dev/2/v/greater_than_equal',
        }
    ]
    '''
```
"""
StrictInt = Annotated[int, Strict()]
"""An integer that must be validated in strict mode.

```python
from pydantic import BaseModel, StrictInt, ValidationError

class StrictIntModel(BaseModel):
    strict_int: StrictInt

try:
    StrictIntModel(strict_int=3.14159)
except ValidationError as e:
    print(e)
    '''
    1 validation error for StrictIntModel
    strict_int
      Input should be a valid integer [type=int_type, input_value=3.14159, input_type=float]
    '''
```
"""

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ FLOAT TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@_dataclasses.dataclass
class AllowInfNan(_fields.PydanticMetadata):
    """A field metadata class to indicate that a field should allow `-inf`, `inf`, and `nan`.

    Use this class as an annotation via [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated), as seen below.

    Attributes:
        allow_inf_nan: Whether to allow `-inf`, `inf`, and `nan`. Defaults to `True`.

    Example:
        ```python
        from typing import Annotated

        from pydantic.types import AllowInfNan

        LaxFloat = Annotated[float, AllowInfNan()]
        ```
    """

    allow_inf_nan: bool = True

    def __hash__(self) -> int:
        return hash(self.allow_inf_nan)


def confloat(
    *,
    strict: bool | None = None,
    gt: float | None = None,
    ge: float | None = None,
    lt: float | None = None,
    le: float | None = None,
    multiple_of: float | None = None,
    allow_inf_nan: bool | None = None,
) -> type[float]:
    """
    !!! warning "Discouraged"
        This function is **discouraged** in favor of using
        [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated) with
        [`Field`][pydantic.fields.Field] instead.

        This function will be **deprecated** in Pydantic 3.0.

        The reason is that `confloat` returns a type, which doesn't play well with static analysis tools.

        === ":x: Don't do this"
            ```python
            from pydantic import BaseModel, confloat

            class Foo(BaseModel):
                bar: confloat(strict=True, gt=0)
            ```

        === ":white_check_mark: Do this"
            ```python
            from typing import Annotated

            from pydantic import BaseModel, Field

            class Foo(BaseModel):
                bar: Annotated[float, Field(strict=True, gt=0)]
            ```

    A wrapper around `float` that allows for additional constraints.

    Args:
        strict: Whether to validate the float in strict mode.
        gt: The value must be greater than this.
        ge: The value must be greater than or equal to this.
        lt: The value must be less than this.
        le: The value must be less than or equal to this.
        multiple_of: The value must be a multiple of this.
        allow_inf_nan: Whether to allow `-inf`, `inf`, and `nan`.

    Returns:
        The wrapped float type.

    ```python
    from pydantic import BaseModel, ValidationError, confloat

    class ConstrainedExample(BaseModel):
        constrained_float: confloat(gt=1.0)

    m = ConstrainedExample(constrained_float=1.1)
    print(repr(m))
    #> ConstrainedExample(constrained_float=1.1)

    try:
        ConstrainedExample(constrained_float=0.9)
    except ValidationError as e:
        print(e.errors())
        '''
        [
            {
                'type': 'greater_than',
                'loc': ('constrained_float',),
                'msg': 'Input should be greater than 1',
                'input': 0.9,
                'ctx': {'gt': 1.0},
                'url': 'https://errors.pydantic.dev/2/v/greater_than',
            }
        ]
        '''
    ```
    """  # noqa: D212
    return Annotated[  # pyright: ignore[reportReturnType]
        float,
        Strict(strict) if strict is not None else None,
        annotated_types.Interval(gt=gt, ge=ge, lt=lt, le=le),
        annotated_types.MultipleOf(multiple_of) if multiple_of is not None else None,
        AllowInfNan(allow_inf_nan) if allow_inf_nan is not None else None,
    ]


PositiveFloat = Annotated[float, annotated_types.Gt(0)]
"""A float that must be greater than zero.

```python
from pydantic import BaseModel, PositiveFloat, ValidationError

class Model(BaseModel):
    positive_float: PositiveFloat

m = Model(positive_float=1.0)
print(repr(m))
#> Model(positive_float=1.0)

try:
    Model(positive_float=-1.0)
except ValidationError as e:
    print(e.errors())
    '''
    [
        {
            'type': 'greater_than',
            'loc': ('positive_float',),
            'msg': 'Input should be greater than 0',
            'input': -1.0,
            'ctx': {'gt': 0.0},
            'url': 'https://errors.pydantic.dev/2/v/greater_than',
        }
    ]
    '''
```
"""
NegativeFloat = Annotated[float, annotated_types.Lt(0)]
"""A float that must be less than zero.

```python
from pydantic import BaseModel, NegativeFloat, ValidationError

class Model(BaseModel):
    negative_float: NegativeFloat

m = Model(negative_float=-1.0)
print(repr(m))
#> Model(negative_float=-1.0)

try:
    Model(negative_float=1.0)
except ValidationError as e:
    print(e.errors())
    '''
    [
        {
            'type': 'less_than',
            'loc': ('negative_float',),
            'msg': 'Input should be less than 0',
            'input': 1.0,
            'ctx': {'lt': 0.0},
            'url': 'https://errors.pydantic.dev/2/v/less_than',
        }
    ]
    '''
```
"""
NonPositiveFloat = Annotated[float, annotated_types.Le(0)]
"""A float that must be less than or equal to zero.

```python
from pydantic import BaseModel, NonPositiveFloat, ValidationError

class Model(BaseModel):
    non_positive_float: NonPositiveFloat

m = Model(non_positive_float=0.0)
print(repr(m))
#> Model(non_positive_float=0.0)

try:
    Model(non_positive_float=1.0)
except ValidationError as e:
    print(e.errors())
    '''
    [
        {
            'type': 'less_than_equal',
            'loc': ('non_positive_float',),
            'msg': 'Input should be less than or equal to 0',
            'input': 1.0,
            'ctx': {'le': 0.0},
            'url': 'https://errors.pydantic.dev/2/v/less_than_equal',
        }
    ]
    '''
```
"""
NonNegativeFloat = Annotated[float, annotated_types.Ge(0)]
"""A float that must be greater than or equal to zero.

```python
from pydantic import BaseModel, NonNegativeFloat, ValidationError

class Model(BaseModel):
    non_negative_float: NonNegativeFloat

m = Model(non_negative_float=0.0)
print(repr(m))
#> Model(non_negative_float=0.0)

try:
    Model(non_negative_float=-1.0)
except ValidationError as e:
    print(e.errors())
    '''
    [
        {
            'type': 'greater_than_equal',
            'loc': ('non_negative_float',),
            'msg': 'Input should be greater than or equal to 0',
            'input': -1.0,
            'ctx': {'ge': 0.0},
            'url': 'https://errors.pydantic.dev/2/v/greater_than_equal',
        }
    ]
    '''
```
"""
StrictFloat = Annotated[float, Strict(True)]
"""A float that must be validated in strict mode.

```python
from pydantic import BaseModel, StrictFloat, ValidationError

class StrictFloatModel(BaseModel):
    strict_float: StrictFloat

try:
    StrictFloatModel(strict_float='1.0')
except ValidationError as e:
    print(e)
    '''
    1 validation error for StrictFloatModel
    strict_float
      Input should be a valid number [type=float_type, input_value='1.0', input_type=str]
    '''
```
"""
FiniteFloat = Annotated[float, AllowInfNan(False)]
"""A float that must be finite (not ``-inf``, ``inf``, or ``nan``).

```python
from pydantic import BaseModel, FiniteFloat

class Model(BaseModel):
    finite: FiniteFloat

m = Model(finite=1.0)
print(m)
#> finite=1.0
```
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ BYTES TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def conbytes(
    *,
    min_length: int | None = None,
    max_length: int | None = None,
    strict: bool | None = None,
) -> type[bytes]:
    """A wrapper around `bytes` that allows for additional constraints.

    Args:
        min_length: The minimum length of the bytes.
        max_length: The maximum length of the bytes.
        strict: Whether to validate the bytes in strict mode.

    Returns:
        The wrapped bytes type.
    """
    return Annotated[  # pyright: ignore[reportReturnType]
        bytes,
        Strict(strict) if strict is not None else None,
        annotated_types.Len(min_length or 0, max_length),
    ]


StrictBytes = Annotated[bytes, Strict()]
"""A bytes that must be validated in strict mode."""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ STRING TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@_dataclasses.dataclass(frozen=True)
class StringConstraints(annotated_types.GroupedMetadata):
    """!!! abstract "Usage Documentation"
        [`StringConstraints`](../concepts/fields.md#string-constraints)

    A field metadata class to apply constraints to `str` types.
    Use this class as an annotation via [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated), as seen below.

    Attributes:
        strip_whitespace: Whether to remove leading and trailing whitespace.
        to_upper: Whether to convert the string to uppercase.
        to_lower: Whether to convert the string to lowercase.
        strict: Whether to validate the string in strict mode.
        min_length: The minimum length of the string.
        max_length: The maximum length of the string.
        pattern: A regex pattern that the string must match.

    Example:
        ```python
        from typing import Annotated

        from pydantic.types import StringConstraints

        ConstrainedStr = Annotated[str, StringConstraints(min_length=1, max_length=10)]
        ```
    """

    strip_whitespace: bool | None = None
    to_upper: bool | None = None
    to_lower: bool | None = None
    strict: bool | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | Pattern[str] | None = None

    def __iter__(self) -> Iterator[BaseMetadata]:
        if self.min_length is not None:
            yield MinLen(self.min_length)
        if self.max_length is not None:
            yield MaxLen(self.max_length)
        if self.strict is not None:
            yield Strict(self.strict)
        if (
            self.strip_whitespace is not None
            or self.pattern is not None
            or self.to_lower is not None
            or self.to_upper is not None
        ):
            yield _fields.pydantic_general_metadata(
                strip_whitespace=self.strip_whitespace,
                to_upper=self.to_upper,
                to_lower=self.to_lower,
                pattern=self.pattern,
            )


def constr(
    *,
    strip_whitespace: bool | None = None,
    to_upper: bool | None = None,
    to_lower: bool | None = None,
    strict: bool | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | Pattern[str] | None = None,
) -> type[str]:
    """
    !!! warning "Discouraged"
        This function is **discouraged** in favor of using
        [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated) with
        [`StringConstraints`][pydantic.types.StringConstraints] instead.

        This function will be **deprecated** in Pydantic 3.0.

        The reason is that `constr` returns a type, which doesn't play well with static analysis tools.

        === ":x: Don't do this"
            ```python
            from pydantic import BaseModel, constr

            class Foo(BaseModel):
                bar: constr(strip_whitespace=True, to_upper=True, pattern=r'^[A-Z]+$')
            ```

        === ":white_check_mark: Do this"
            ```python
            from typing import Annotated

            from pydantic import BaseModel, StringConstraints

            class Foo(BaseModel):
                bar: Annotated[
                    str,
                    StringConstraints(
                        strip_whitespace=True, to_upper=True, pattern=r'^[A-Z]+$'
                    ),
                ]
            ```

    A wrapper around `str` that allows for additional constraints.

    ```python
    from pydantic import BaseModel, constr

    class Foo(BaseModel):
        bar: constr(strip_whitespace=True, to_upper=True)

    foo = Foo(bar='  hello  ')
    print(foo)
    #> bar='HELLO'
    ```

    Args:
        strip_whitespace: Whether to remove leading and trailing whitespace.
        to_upper: Whether to turn all characters to uppercase.
        to_lower: Whether to turn all characters to lowercase.
        strict: Whether to validate the string in strict mode.
        min_length: The minimum length of the string.
        max_length: The maximum length of the string.
        pattern: A regex pattern to validate the string against.

    Returns:
        The wrapped string type.
    """  # noqa: D212
    return Annotated[  # pyright: ignore[reportReturnType]
        str,
        StringConstraints(
            strip_whitespace=strip_whitespace,
            to_upper=to_upper,
            to_lower=to_lower,
            strict=strict,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
        ),
    ]


StrictStr = Annotated[str, Strict()]
"""A string that must be validated in strict mode."""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~ COLLECTION TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
HashableItemType = TypeVar('HashableItemType', bound=Hashable)


def conset(
    item_type: type[HashableItemType], *, min_length: int | None = None, max_length: int | None = None
) -> type[set[HashableItemType]]:
    """A wrapper around `typing.Set` that allows for additional constraints.

    Args:
        item_type: The type of the items in the set.
        min_length: The minimum length of the set.
        max_length: The maximum length of the set.

    Returns:
        The wrapped set type.
    """
    return Annotated[set[item_type], annotated_types.Len(min_length or 0, max_length)]  # pyright: ignore[reportReturnType]


def confrozenset(
    item_type: type[HashableItemType], *, min_length: int | None = None, max_length: int | None = None
) -> type[frozenset[HashableItemType]]:
    """A wrapper around `typing.FrozenSet` that allows for additional constraints.

    Args:
        item_type: The type of the items in the frozenset.
        min_length: The minimum length of the frozenset.
        max_length: The maximum length of the frozenset.

    Returns:
        The wrapped frozenset type.
    """
    return Annotated[frozenset[item_type], annotated_types.Len(min_length or 0, max_length)]  # pyright: ignore[reportReturnType]


AnyItemType = TypeVar('AnyItemType')


def conlist(
    item_type: type[AnyItemType],
    *,
    min_length: int | None = None,
    max_length: int | None = None,
    unique_items: bool | None = None,
) -> type[list[AnyItemType]]:
    """A wrapper around [`list`][] that adds validation.

    Args:
        item_type: The type of the items in the list.
        min_length: The minimum length of the list. Defaults to None.
        max_length: The maximum length of the list. Defaults to None.
        unique_items: Whether the items in the list must be unique. Defaults to None.
            !!! warning Deprecated
                The `unique_items` parameter is deprecated, use `Set` instead.
                See [this issue](https://github.com/pydantic/pydantic-core/issues/296) for more details.

    Returns:
        The wrapped list type.
    """
    if unique_items is not None:
        raise PydanticUserError(
            (
                '`unique_items` is removed, use `Set` instead'
                '(this feature is discussed in https://github.com/pydantic/pydantic-core/issues/296)'
            ),
            code='removed-kwargs',
        )
    return Annotated[list[item_type], annotated_types.Len(min_length or 0, max_length)]  # pyright: ignore[reportReturnType]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~ IMPORT STRING TYPE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

AnyType = TypeVar('AnyType')
if TYPE_CHECKING:
    ImportString = Annotated[AnyType, ...]
else:

    class ImportString:
        """A type that can be used to import a Python object from a string.

        `ImportString` expects a string and loads the Python object importable at that dotted path.
        Attributes of modules may be separated from the module by `:` or `.`, e.g. if `'math:cos'` is provided,
        the resulting field value would be the function `cos`. If a `.` is used and both an attribute and submodule
        are present at the same path, the module will be preferred.

        On model instantiation, pointers will be evaluated and imported. There is
        some nuance to this behavior, demonstrated in the examples below.

        ```python
        import math

        from pydantic import BaseModel, Field, ImportString, ValidationError

        class ImportThings(BaseModel):
            obj: ImportString

        # A string value will cause an automatic import
        my_cos = ImportThings(obj='math.cos')

        # You can use the imported function as you would expect
        cos_of_0 = my_cos.obj(0)
        assert cos_of_0 == 1

        # A string whose value cannot be imported will raise an error
        try:
            ImportThings(obj='foo.bar')
        except ValidationError as e:
            print(e)
            '''
            1 validation error for ImportThings
            obj
              Invalid python path: No module named 'foo.bar' [type=import_error, input_value='foo.bar', input_type=str]
            '''

        # Actual python objects can be assigned as well
        my_cos = ImportThings(obj=math.cos)
        my_cos_2 = ImportThings(obj='math.cos')
        my_cos_3 = ImportThings(obj='math:cos')
        assert my_cos == my_cos_2 == my_cos_3

        # You can set default field value either as Python object:
        class ImportThingsDefaultPyObj(BaseModel):
            obj: ImportString = math.cos

        # or as a string value (but only if used with `validate_default=True`)
        class ImportThingsDefaultString(BaseModel):
            obj: ImportString = Field(default='math.cos', validate_default=True)

        my_cos_default1 = ImportThingsDefaultPyObj()
        my_cos_default2 = ImportThingsDefaultString()
        assert my_cos_default1.obj == my_cos_default2.obj == math.cos

        # note: this will not work!
        class ImportThingsMissingValidateDefault(BaseModel):
            obj: ImportString = 'math.cos'

        my_cos_default3 = ImportThingsMissingValidateDefault()
        assert my_cos_default3.obj == 'math.cos'  # just string, not evaluated
        ```

        Serializing an `ImportString` type to json is also possible.

        ```python
        from pydantic import BaseModel, ImportString

        class ImportThings(BaseModel):
            obj: ImportString

        # Create an instance
        m = ImportThings(obj='math.cos')
        print(m)
        #> obj=<built-in function cos>
        print(m.model_dump_json())
        #> {"obj":"math.cos"}
        ```
        """

        @classmethod
        def __class_getitem__(cls, item: AnyType) -> AnyType:
            return Annotated[item, cls()]

        @classmethod
        def __get_pydantic_core_schema__(
            cls, source: type[Any], handler: GetCoreSchemaHandler
        ) -> core_schema.CoreSchema:
            serializer = core_schema.plain_serializer_function_ser_schema(cls._serialize, when_used='json')
            if cls is source:
                # Treat bare usage of ImportString (`schema is None`) as the same as ImportString[Any]
                return core_schema.no_info_plain_validator_function(
                    function=_validators.import_string, serialization=serializer
                )
            else:
                return core_schema.no_info_before_validator_function(
                    function=_validators.import_string, schema=handler(source), serialization=serializer
                )

        @classmethod
        def __get_pydantic_json_schema__(cls, cs: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
            return handler(core_schema.str_schema())

        @staticmethod
        def _serialize(v: Any) -> str:
            if isinstance(v, ModuleType):
                return v.__name__
            elif hasattr(v, '__module__') and hasattr(v, '__name__'):
                return f'{v.__module__}.{v.__name__}'
            # Handle special cases for sys.XXX streams
            # if we see more of these, we should consider a more general solution
            elif hasattr(v, 'name'):
                if v.name == '<stdout>':
                    return 'sys.stdout'
                elif v.name == '<stdin>':
                    return 'sys.stdin'
                elif v.name == '<stderr>':
                    return 'sys.stderr'
            else:
                return v

        def __repr__(self) -> str:
            return 'ImportString'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ DECIMAL TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def condecimal(
    *,
    strict: bool | None = None,
    gt: int | Decimal | None = None,
    ge: int | Decimal | None = None,
    lt: int | Decimal | None = None,
    le: int | Decimal | None = None,
    multiple_of: int | Decimal | None = None,
    max_digits: int | None = None,
    decimal_places: int | None = None,
    allow_inf_nan: bool | None = None,
) -> type[Decimal]:
    """
    !!! warning "Discouraged"
        This function is **discouraged** in favor of using
        [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated) with
        [`Field`][pydantic.fields.Field] instead.

        This function will be **deprecated** in Pydantic 3.0.

        The reason is that `condecimal` returns a type, which doesn't play well with static analysis tools.

        === ":x: Don't do this"
            ```python
            from pydantic import BaseModel, condecimal

            class Foo(BaseModel):
                bar: condecimal(strict=True, allow_inf_nan=True)
            ```

        === ":white_check_mark: Do this"
            ```python
            from decimal import Decimal
            from typing import Annotated

            from pydantic import BaseModel, Field

            class Foo(BaseModel):
                bar: Annotated[Decimal, Field(strict=True, allow_inf_nan=True)]
            ```

    A wrapper around Decimal that adds validation.

    Args:
        strict: Whether to validate the value in strict mode. Defaults to `None`.
        gt: The value must be greater than this. Defaults to `None`.
        ge: The value must be greater than or equal to this. Defaults to `None`.
        lt: The value must be less than this. Defaults to `None`.
        le: The value must be less than or equal to this. Defaults to `None`.
        multiple_of: The value must be a multiple of this. Defaults to `None`.
        max_digits: The maximum number of digits. Defaults to `None`.
        decimal_places: The number of decimal places. Defaults to `None`.
        allow_inf_nan: Whether to allow infinity and NaN. Defaults to `None`.

    ```python
    from decimal import Decimal

    from pydantic import BaseModel, ValidationError, condecimal

    class ConstrainedExample(BaseModel):
        constrained_decimal: condecimal(gt=Decimal('1.0'))

    m = ConstrainedExample(constrained_decimal=Decimal('1.1'))
    print(repr(m))
    #> ConstrainedExample(constrained_decimal=Decimal('1.1'))

    try:
        ConstrainedExample(constrained_decimal=Decimal('0.9'))
    except ValidationError as e:
        print(e.errors())
        '''
        [
            {
                'type': 'greater_than',
                'loc': ('constrained_decimal',),
                'msg': 'Input should be greater than 1.0',
                'input': Decimal('0.9'),
                'ctx': {'gt': Decimal('1.0')},
                'url': 'https://errors.pydantic.dev/2/v/greater_than',
            }
        ]
        '''
    ```
    """  # noqa: D212
    return Annotated[  # pyright: ignore[reportReturnType]
        Decimal,
        Strict(strict) if strict is not None else None,
        annotated_types.Interval(gt=gt, ge=ge, lt=lt, le=le),
        annotated_types.MultipleOf(multiple_of) if multiple_of is not None else None,
        _fields.pydantic_general_metadata(max_digits=max_digits, decimal_places=decimal_places),
        AllowInfNan(allow_inf_nan) if allow_inf_nan is not None else None,
    ]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ UUID TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@_dataclasses.dataclass(**_internal_dataclass.slots_true)
class UuidVersion:
    """A field metadata class to indicate a [UUID](https://docs.python.org/3/library/uuid.html) version.

    Use this class as an annotation via [`Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated), as seen below.

    Attributes:
        uuid_version: The version of the UUID. Must be one of 1, 3, 4, 5, or 7.

    Example:
        ```python
        from typing import Annotated
        from uuid import UUID

        from pydantic.types import UuidVersion

        UUID1 = Annotated[UUID, UuidVersion(1)]
        ```
    """

    uuid_version: Literal[1, 3, 4, 5, 6, 7, 8]

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        field_schema = handler(core_schema)
        field_schema.pop('anyOf', None)  # remove the bytes/str union
        field_schema.update(type='string', format=f'uuid{self.uuid_version}')
        return field_schema

    def __get_pydantic_core_schema__(self, source: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        if isinstance(self, source):
            # used directly as a type
            return core_schema.uuid_schema(version=self.uuid_version)
        else:
            # update existing schema with self.uuid_version
            schema = handler(source)
            _check_annotated_type(schema['type'], 'uuid', self.__class__.__name__)
            schema['version'] = self.uuid_version  # type: ignore
            return schema

    def __hash__(self) -> int:
        return hash(type(self.uuid_version))


UUID1 = Annotated[UUID, UuidVersion(1)]
"""A [UUID](https://docs.python.org/3/library/uuid.html) that must be version 1.

```python
import uuid

from pydantic import UUID1, BaseModel

class Model(BaseModel):
    uuid1: UUID1

Model(uuid1=uuid.uuid1())
```
"""
UUID3 = Annotated[UUID, UuidVersion(3)]
"""A [UUID](https://docs.python.org/3/library/uuid.html) that must be version 3.

```python
import uuid

from pydantic import UUID3, BaseModel

class Model(BaseModel):
    uuid3: UUID3

Model(uuid3=uuid.uuid3(uuid.NAMESPACE_DNS, 'pydantic.org'))
```
"""
UUID4 = Annotated[UUID, UuidVersion(4)]
"""A [UUID](https://docs.python.org/3/library/uuid.html) that must be version 4.

```python
import uuid

from pydantic import UUID4, BaseModel

class Model(BaseModel):
    uuid4: UUID4

Model(uuid4=uuid.uuid4())
```
"""
UUID5 = Annotated[UUID, UuidVersion(5)]
"""A [UUID](https://docs.python.org/3/library/uuid.html) that must be version 5.

```python
import uuid

from pydantic import UUID5, BaseModel

class Model(BaseModel):
    uuid5: UUID5

Model(uuid5=uuid.uuid5(uuid.NAMESPACE_DNS, 'pydantic.org'))
```
"""
UUID6 = Annotated[UUID, UuidVersion(6)]
"""A [UUID](https://docs.python.org/3/library/uuid.html) that must be version 6.

```python
import uuid

from pydantic import UUID6, BaseModel

class Model(BaseModel):
    uuid6: UUID6

Model(uuid6=uuid.UUID('1efea953-c2d6-6790-aa0a-69db8c87df97'))
```
"""
UUID7 = Annotated[UUID, UuidVersion(7)]
"""A [UUID](https://docs.python.org/3/library/uuid.html) that must be version 7.

```python
import uuid

from pydantic import UUID7, BaseModel

class Model(BaseModel):
    uuid7: UUID7

Model(uuid7=uuid.UUID('0194fdcb-1c47-7a09-b52c-561154de0b4a'))
```
"""
UUID8 = Annotated[UUID, UuidVersion(8)]
"""A [UUID](https://docs.python.org/3/library/uuid.html) that must be version 8.

```python
import uuid

from pydantic import UUID8, BaseModel

class Model(BaseModel):
    uuid8: UUID8

Model(uuid8=uuid.UUID('81a0b92e-6078-8551-9c81-8ccb666bdab8'))
```
"""

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PATH TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@_dataclasses.dataclass
class PathType:
    path_type: Literal['file', 'dir', 'new', 'socket']

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        field_schema = handler(core_schema)
        format_conversion = {'file': 'file-path', 'dir': 'directory-path'}
        field_schema.update(format=format_conversion.get(self.path_type, 'path'), type='string')
        return field_schema

    def __get_pydantic_core_schema__(self, source: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        function_lookup = {
            'file': cast(core_schema.WithInfoValidatorFunction, self.validate_file),
            'dir': cast(core_schema.WithInfoValidatorFunction, self.validate_directory),
            'new': cast(core_schema.WithInfoValidatorFunction, self.validate_new),
            'socket': cast(core_schema.WithInfoValidatorFunction, self.validate_socket),
        }

        return core_schema.with_info_after_validator_function(
            function_lookup[self.path_type],
            handler(source),
        )

    @staticmethod
    def validate_file(path: Path, _: core_schema.ValidationInfo) -> Path:
        if path.is_file():
            return path
        else:
            raise PydanticCustomError('path_not_file', 'Path does not point to a file')

    @staticmethod
    def validate_socket(path: Path, _: core_schema.ValidationInfo) -> Path:
        if path.is_socket():
            return path
        else:
            raise PydanticCustomError('path_not_socket', 'Path does not point to a socket')

    @staticmethod
    def validate_directory(path: Path, _: core_schema.ValidationInfo) -> Path:
        if path.is_dir():
            return path
        else:
            raise PydanticCustomError('path_not_directory', 'Path does not point to a directory')

    @staticmethod
    def validate_new(path: Path, _: core_schema.ValidationInfo) -> Path:
        if path.exists():
            raise PydanticCustomError('path_exists', 'Path already exists')
        elif not path.parent.exists():
            raise PydanticCustomError('parent_does_not_exist', 'Parent directory does not exist')
        else:
            return path

    def __hash__(self) -> int:
        return hash(type(self.path_type))


FilePath = Annotated[Path, PathType('file')]
"""A path that must point to a file.

```python
from pathlib import Path

from pydantic import BaseModel, FilePath, ValidationError

class Model(BaseModel):
    f: FilePath

path = Path('text.txt')
path.touch()
m = Model(f='text.txt')
print(m.model_dump())
#> {'f': PosixPath('text.txt')}
path.unlink()

path = Path('directory')
path.mkdir(exist_ok=True)
try:
    Model(f='directory')  # directory
except ValidationError as e:
    print(e)
    '''
    1 validation error for Model
    f
      Path does not point to a file [type=path_not_file, input_value='directory', input_type=str]
    '''
path.rmdir()

try:
    Model(f='not-exists-file')
except ValidationError as e:
    print(e)
    '''
    1 validation error for Model
    f
      Path does not point to a file [type=path_not_file, input_value='not-exists-file', input_type=str]
    '''
```
"""
DirectoryPath = Annotated[Path, PathType('dir')]
"""A path that must point to a directory.

```python
from pathlib import Path

from pydantic import BaseModel, DirectoryPath, ValidationError

class Model(BaseModel):
    f: DirectoryPath

path = Path('directory/')
path.mkdir()
m = Model(f='directory/')
print(m.model_dump())
#> {'f': PosixPath('directory')}
path.rmdir()

path = Path('file.txt')
path.touch()
try:
    Model(f='file.txt')  # file
except ValidationError as e:
    print(e)
    '''
    1 validation error for Model
    f
      Path does not point to a directory [type=path_not_directory, input_value='file.txt', input_type=str]
    '''
path.unlink()

try:
    Model(f='not-exists-directory')
except ValidationError as e:
    print(e)
    '''
    1 validation error for Model
    f
      Path does not point to a directory [type=path_not_directory, input_value='not-exists-directory', input_type=str]
    '''
```
"""
NewPath = Annotated[Path, PathType('new')]
"""A path for a new file or directory that must not already exist. The parent directory must already exist."""

SocketPath = Annotated[Path, PathType('socket')]
"""A path to an existing socket file"""

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ JSON TYPE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if TYPE_CHECKING:
    # Json[list[str]] will be recognized by type checkers as list[str]
    Json = Annotated[AnyType, ...]

else:

    class Json:
        """A special type wrapper which loads JSON before parsing.

        You can use the `Json` data type to make Pydantic first load a raw JSON string before
        validating the loaded data into the parametrized type:

        ```python
        from typing import Any

        from pydantic import BaseModel, Json, ValidationError

        class AnyJsonModel(BaseModel):
            json_obj: Json[Any]

        class ConstrainedJsonModel(BaseModel):
            json_obj: Json[list[int]]

        print(AnyJsonModel(json_obj='{"b": 1}'))
        #> json_obj={'b': 1}
        print(ConstrainedJsonModel(json_obj='[1, 2, 3]'))
        #> json_obj=[1, 2, 3]

        try:
            ConstrainedJsonModel(json_obj=12)
        except ValidationError as e:
            print(e)
            '''
            1 validation error for ConstrainedJsonModel
            json_obj
              JSON input should be string, bytes or bytearray [type=json_type, input_value=12, input_type=int]
            '''

        try:
            ConstrainedJsonModel(json_obj='[a, b]')
        except ValidationError as e:
            print(e)
            '''
            1 validation error for ConstrainedJsonModel
            json_obj
              Invalid JSON: expected value at line 1 column 2 [type=json_invalid, input_value='[a, b]', input_type=str]
            '''

        try:
            ConstrainedJsonModel(json_obj='["a", "b"]')
        except ValidationError as e:
            print(e)
            '''
            2 validation errors for ConstrainedJsonModel
            json_obj.0
              Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='a', input_type=str]
            json_obj.1
              Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='b', input_type=str]
            '''
        ```

        When you dump the model using `model_dump` or `model_dump_json`, the dumped value will be the result of validation,
        not the original JSON string. However, you can use the argument `round_trip=True` to get the original JSON string back:

        ```python
        from pydantic import BaseModel, Json

        class ConstrainedJsonModel(BaseModel):
            json_obj: Json[list[int]]

        print(ConstrainedJsonModel(json_obj='[1, 2, 3]').model_dump_json())
        #> {"json_obj":[1,2,3]}
        print(
            ConstrainedJsonModel(json_obj='[1, 2, 3]').model_dump_json(round_trip=True)
        )
        #> {"json_obj":"[1,2,3]"}
        ```
        """

        @classmethod
        def __class_getitem__(cls, item: AnyType) -> AnyType:
            return Annotated[item, cls()]

        @classmethod
        def __get_pydantic_core_schema__(cls, source: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
            if cls is source:
                return core_schema.json_schema(None)
            else:
                return core_schema.json_schema(handler(source))

        def __repr__(self) -> str:
            return 'Json'

        def __hash__(self) -> int:
            return hash(type(self))

        def __eq__(self, other: Any) -> bool:
            return type(other) is type(self)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ SECRET TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SecretType = TypeVar('SecretType')


class _SecretBase(Generic[SecretType]):
    def __init__(self, secret_value: SecretType) -> None:
        self._secret_value: SecretType = secret_value

    def get_secret_value(self) -> SecretType:
        """Get the secret value.

        Returns:
            The secret value.
        """
        return self._secret_value

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and self.get_secret_value() == other.get_secret_value()

    def __hash__(self) -> int:
        return hash(self.get_secret_value())

    def __str__(self) -> str:
        return str(self._display())

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._display()!r})'

    def _display(self) -> str | bytes:
        raise NotImplementedError


def _serialize_secret(value: Secret[SecretType], info: core_schema.SerializationInfo) -> str | Secret[SecretType]:
    if info.mode == 'json':
        return str(value)
    else:
        return value


class Secret(_SecretBase[SecretType]):
    """A generic base class used for defining a field with sensitive information that you do not want to be visible in logging or tracebacks.

    You may either directly parametrize `Secret` with a type, or subclass from `Secret` with a parametrized type. The benefit of subclassing
    is that you can define a custom `_display` method, which will be used for `repr()` and `str()` methods. The examples below demonstrate both
    ways of using `Secret` to create a new secret type.

    1. Directly parametrizing `Secret` with a type:

    ```python
    from pydantic import BaseModel, Secret

    SecretBool = Secret[bool]

    class Model(BaseModel):
        secret_bool: SecretBool

    m = Model(secret_bool=True)
    print(m.model_dump())
    #> {'secret_bool': Secret('**********')}

    print(m.model_dump_json())
    #> {"secret_bool":"**********"}

    print(m.secret_bool.get_secret_value())
    #> True
    ```

    2. Subclassing from parametrized `Secret`:

    ```python
    from datetime import date

    from pydantic import BaseModel, Secret

    class SecretDate(Secret[date]):
        def _display(self) -> str:
            return '****/**/**'

    class Model(BaseModel):
        secret_date: SecretDate

    m = Model(secret_date=date(2022, 1, 1))
    print(m.model_dump())
    #> {'secret_date': SecretDate('****/**/**')}

    print(m.model_dump_json())
    #> {"secret_date":"****/**/**"}

    print(m.secret_date.get_secret_value())
    #> 2022-01-01
    ```

    The value returned by the `_display` method will be used for `repr()` and `str()`.

    You can enforce constraints on the underlying type through annotations:
    For example:

    ```python
    from typing import Annotated

    from pydantic import BaseModel, Field, Secret, ValidationError

    SecretPosInt = Secret[Annotated[int, Field(gt=0, strict=True)]]

    class Model(BaseModel):
        sensitive_int: SecretPosInt

    m = Model(sensitive_int=42)
    print(m.model_dump())
    #> {'sensitive_int': Secret('**********')}

    try:
        m = Model(sensitive_int=-42)  # (1)!
    except ValidationError as exc_info:
        print(exc_info.errors(include_url=False, include_input=False))
        '''
        [
            {
                'type': 'greater_than',
                'loc': ('sensitive_int',),
                'msg': 'Input should be greater than 0',
                'ctx': {'gt': 0},
            }
        ]
        '''

    try:
        m = Model(sensitive_int='42')  # (2)!
    except ValidationError as exc_info:
        print(exc_info.errors(include_url=False, include_input=False))
        '''
        [
            {
                'type': 'int_type',
                'loc': ('sensitive_int',),
                'msg': 'Input should be a valid integer',
            }
        ]
        '''
    ```

    1. The input value is not greater than 0, so it raises a validation error.
    2. The input value is not an integer, so it raises a validation error because the `SecretPosInt` type has strict mode enabled.
    """

    def _display(self) -> str | bytes:
        return '**********' if self.get_secret_value() else ''

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[Any], handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        inner_type = None
        # if origin_type is Secret, then cls is a GenericAlias, and we can extract the inner type directly
        origin_type = get_origin(source)
        if origin_type is not None:
            inner_type = get_args(source)[0]
        # otherwise, we need to get the inner type from the base class
        else:
            bases = getattr(cls, '__orig_bases__', getattr(cls, '__bases__', []))
            for base in bases:
                if get_origin(base) is Secret:
                    inner_type = get_args(base)[0]
            if bases == [] or inner_type is None:
                raise TypeError(
                    f"Can't get secret type from {cls.__name__}. "
                    'Please use Secret[<type>], or subclass from Secret[<type>] instead.'
                )

        inner_schema = handler.generate_schema(inner_type)  # type: ignore

        def validate_secret_value(value, handler) -> Secret[SecretType]:
            if isinstance(value, Secret):
                value = value.get_secret_value()
            validated_inner = handler(value)
            return cls(validated_inner)

        return core_schema.json_or_python_schema(
            python_schema=core_schema.no_info_wrap_validator_function(
                validate_secret_value,
                inner_schema,
            ),
            json_schema=core_schema.no_info_after_validator_function(lambda x: cls(x), inner_schema),
            serialization=core_schema.plain_serializer_function_ser_schema(
                _serialize_secret,
                info_arg=True,
                when_used='always',
            ),
        )

    __pydantic_serializer__ = SchemaSerializer(
        core_schema.any_schema(
            serialization=core_schema.plain_serializer_function_ser_schema(
                _serialize_secret,
                info_arg=True,
                when_used='always',
            )
        )
    )


def _secret_display(value: SecretType) -> str:  # type: ignore
    return '**********' if value else ''


def _serialize_secret_field(
    value: _SecretField[SecretType], info: core_schema.SerializationInfo
) -> str | _SecretField[SecretType]:
    if info.mode == 'json':
        # we want the output to always be string without the `b'` prefix for bytes,
        # hence we just use `secret_display`
        return _secret_display(value.get_secret_value())
    else:
        return value


class _SecretField(_SecretBase[SecretType]):
    _inner_schema: ClassVar[CoreSchema]
    _error_kind: ClassVar[str]

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[Any], handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        def get_json_schema(_core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
            json_schema = handler(cls._inner_schema)
            _utils.update_not_none(
                json_schema,
                type='string',
                writeOnly=True,
                format='password',
            )
            return json_schema

        def get_secret_schema(strict: bool) -> CoreSchema:
            inner_schema = {**cls._inner_schema, 'strict': strict}
            json_schema = core_schema.no_info_after_validator_function(
                source,  # construct the type
                inner_schema,  # pyright: ignore[reportArgumentType]
            )
            return core_schema.json_or_python_schema(
                python_schema=core_schema.union_schema(
                    [
                        core_schema.is_instance_schema(source),
                        json_schema,
                    ],
                    custom_error_type=cls._error_kind,
                ),
                json_schema=json_schema,
                serialization=core_schema.plain_serializer_function_ser_schema(
                    _serialize_secret_field,
                    info_arg=True,
                    when_used='always',
                ),
            )

        return core_schema.lax_or_strict_schema(
            lax_schema=get_secret_schema(strict=False),
            strict_schema=get_secret_schema(strict=True),
            metadata={'pydantic_js_functions': [get_json_schema]},
        )

    __pydantic_serializer__ = SchemaSerializer(
        core_schema.any_schema(
            serialization=core_schema.plain_serializer_function_ser_schema(
                _serialize_secret_field,
                info_arg=True,
                when_used='always',
            )
        )
    )


class SecretStr(_SecretField[str]):
    """A string used for storing sensitive information that you do not want to be visible in logging or tracebacks.

    When the secret value is nonempty, it is displayed as `'**********'` instead of the underlying value in
    calls to `repr()` and `str()`. If the value _is_ empty, it is displayed as `''`.

    ```python
    from pydantic import BaseModel, SecretStr

    class User(BaseModel):
        username: str
        password: SecretStr

    user = User(username='scolvin', password='password1')

    print(user)
    #> username='scolvin' password=SecretStr('**********')
    print(user.password.get_secret_value())
    #> password1
    print((SecretStr('password'), SecretStr('')))
    #> (SecretStr('**********'), SecretStr(''))
    ```

    As seen above, by default, [`SecretStr`][pydantic.types.SecretStr] (and [`SecretBytes`][pydantic.types.SecretBytes])
    will be serialized as `**********` when serializing to json.

    You can use the [`field_serializer`][pydantic.functional_serializers.field_serializer] to dump the
    secret as plain-text when serializing to json.

    ```python
    from pydantic import BaseModel, SecretBytes, SecretStr, field_serializer

    class Model(BaseModel):
        password: SecretStr
        password_bytes: SecretBytes

        @field_serializer('password', 'password_bytes', when_used='json')
        def dump_secret(self, v):
            return v.get_secret_value()

    model = Model(password='IAmSensitive', password_bytes=b'IAmSensitiveBytes')
    print(model)
    #> password=SecretStr('**********') password_bytes=SecretBytes(b'**********')
    print(model.password)
    #> **********
    print(model.model_dump())
    '''
    {
        'password': SecretStr('**********'),
        'password_bytes': SecretBytes(b'**********'),
    }
    '''
    print(model.model_dump_json())
    #> {"password":"IAmSensitive","password_bytes":"IAmSensitiveBytes"}
    ```
    """

    _inner_schema: ClassVar[CoreSchema] = core_schema.str_schema()
    _error_kind: ClassVar[str] = 'string_type'

    def __len__(self) -> int:
        return len(self._secret_value)

    def _display(self) -> str:
        return _secret_display(self._secret_value)


class SecretBytes(_SecretField[bytes]):
    """A bytes used for storing sensitive information that you do not want to be visible in logging or tracebacks.

    It displays `b'**********'` instead of the string value on `repr()` and `str()` calls.
    When the secret value is nonempty, it is displayed as `b'**********'` instead of the underlying value in
    calls to `repr()` and `str()`. If the value _is_ empty, it is displayed as `b''`.

    ```python
    from pydantic import BaseModel, SecretBytes

    class User(BaseModel):
        username: str
        password: SecretBytes

    user = User(username='scolvin', password=b'password1')
    #> username='scolvin' password=SecretBytes(b'**********')
    print(user.password.get_secret_value())
    #> b'password1'
    print((SecretBytes(b'password'), SecretBytes(b'')))
    #> (SecretBytes(b'**********'), SecretBytes(b''))
    ```
    """

    _inner_schema: ClassVar[CoreSchema] = core_schema.bytes_schema()
    _error_kind: ClassVar[str] = 'bytes_type'

    def __len__(self) -> int:
        return len(self._secret_value)

    def _display(self) -> bytes:
        return _secret_display(self._secret_value).encode()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ PAYMENT CARD TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class PaymentCardBrand(str, Enum):
    amex = 'American Express'
    mastercard = 'Mastercard'
    visa = 'Visa'
    other = 'other'

    def __str__(self) -> str:
        return self.value


@deprecated(
    'The `PaymentCardNumber` class is deprecated, use `pydantic_extra_types` instead. '
    'See https://docs.pydantic.dev/latest/api/pydantic_extra_types_payment/#pydantic_extra_types.payment.PaymentCardNumber.',
    category=PydanticDeprecatedSince20,
)
class PaymentCardNumber(str):
    """Based on: https://en.wikipedia.org/wiki/Payment_card_number."""

    strip_whitespace: ClassVar[bool] = True
    min_length: ClassVar[int] = 12
    max_length: ClassVar[int] = 19
    bin: str
    last4: str
    brand: PaymentCardBrand

    def __init__(self, card_number: str):
        self.validate_digits(card_number)

        card_number = self.validate_luhn_check_digit(card_number)

        self.bin = card_number[:6]
        self.last4 = card_number[-4:]
        self.brand = self.validate_brand(card_number)

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[Any], handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.with_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(
                min_length=cls.min_length, max_length=cls.max_length, strip_whitespace=cls.strip_whitespace
            ),
        )

    @classmethod
    def validate(cls, input_value: str, /, _: core_schema.ValidationInfo) -> PaymentCardNumber:
        """Validate the card number and return a `PaymentCardNumber` instance."""
        return cls(input_value)

    @property
    def masked(self) -> str:
        """Mask all but the last 4 digits of the card number.

        Returns:
            A masked card number string.
        """
        num_masked = len(self) - 10  # len(bin) + len(last4) == 10
        return f'{self.bin}{"*" * num_masked}{self.last4}'

    @classmethod
    def validate_digits(cls, card_number: str) -> None:
        """Validate that the card number is all digits."""
        if not card_number.isdigit():
            raise PydanticCustomError('payment_card_number_digits', 'Card number is not all digits')

    @classmethod
    def validate_luhn_check_digit(cls, card_number: str) -> str:
        """Based on: https://en.wikipedia.org/wiki/Luhn_algorithm."""
        sum_ = int(card_number[-1])
        length = len(card_number)
        parity = length % 2
        for i in range(length - 1):
            digit = int(card_number[i])
            if i % 2 == parity:
                digit *= 2
            if digit > 9:
                digit -= 9
            sum_ += digit
        valid = sum_ % 10 == 0
        if not valid:
            raise PydanticCustomError('payment_card_number_luhn', 'Card number is not luhn valid')
        return card_number

    @staticmethod
    def validate_brand(card_number: str) -> PaymentCardBrand:
        """Validate length based on BIN for major brands:
        https://en.wikipedia.org/wiki/Payment_card_number#Issuer_identification_number_(IIN).
        """
        if card_number[0] == '4':
            brand = PaymentCardBrand.visa
        elif 51 <= int(card_number[:2]) <= 55:
            brand = PaymentCardBrand.mastercard
        elif card_number[:2] in {'34', '37'}:
            brand = PaymentCardBrand.amex
        else:
            brand = PaymentCardBrand.other

        required_length: None | int | str = None
        if brand in PaymentCardBrand.mastercard:
            required_length = 16
            valid = len(card_number) == required_length
        elif brand == PaymentCardBrand.visa:
            required_length = '13, 16 or 19'
            valid = len(card_number) in {13, 16, 19}
        elif brand == PaymentCardBrand.amex:
            required_length = 15
            valid = len(card_number) == required_length
        else:
            valid = True

        if not valid:
            raise PydanticCustomError(
                'payment_card_number_brand',
                'Length for a {brand} card must be {required_length}',
                {'brand': brand, 'required_length': required_length},
            )
        return brand


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ BYTE SIZE TYPE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ByteSize(int):
    """Converts a string representing a number of bytes with units (such as `'1KB'` or `'11.5MiB'`) into an integer.

    You can use the `ByteSize` data type to (case-insensitively) convert a string representation of a number of bytes into
    an integer, and also to print out human-readable strings representing a number of bytes.

    In conformance with [IEC 80000-13 Standard](https://en.wikipedia.org/wiki/ISO/IEC_80000) we interpret `'1KB'` to mean 1000 bytes,
    and `'1KiB'` to mean 1024 bytes. In general, including a middle `'i'` will cause the unit to be interpreted as a power of 2,
    rather than a power of 10 (so, for example, `'1 MB'` is treated as `1_000_000` bytes, whereas `'1 MiB'` is treated as `1_048_576` bytes).

    !!! info
        Note that `1b` will be parsed as "1 byte" and not "1 bit".

    ```python
    from pydantic import BaseModel, ByteSize

    class MyModel(BaseModel):
        size: ByteSize

    print(MyModel(size=52000).size)
    #> 52000
    print(MyModel(size='3000 KiB').size)
    #> 3072000

    m = MyModel(size='50 PB')
    print(m.size.human_readable())
    #> 44.4PiB
    print(m.size.human_readable(decimal=True))
    #> 50.0PB
    print(m.size.human_readable(separator=' '))
    #> 44.4 PiB

    print(m.size.to('TiB'))
    #> 45474.73508864641
    ```
    """

    byte_sizes = {
        'b': 1,
        'kb': 10**3,
        'mb': 10**6,
        'gb': 10**9,
        'tb': 10**12,
        'pb': 10**15,
        'eb': 10**18,
        'kib': 2**10,
        'mib': 2**20,
        'gib': 2**30,
        'tib': 2**40,
        'pib': 2**50,
        'eib': 2**60,
        'bit': 1 / 8,
        'kbit': 10**3 / 8,
        'mbit': 10**6 / 8,
        'gbit': 10**9 / 8,
        'tbit': 10**12 / 8,
        'pbit': 10**15 / 8,
        'ebit': 10**18 / 8,
        'kibit': 2**10 / 8,
        'mibit': 2**20 / 8,
        'gibit': 2**30 / 8,
        'tibit': 2**40 / 8,
        'pibit': 2**50 / 8,
        'eibit': 2**60 / 8,
    }
    byte_sizes.update({k.lower()[0]: v for k, v in byte_sizes.items() if 'i' not in k})

    byte_string_pattern = r'^\s*(\d*\.?\d+)\s*(\w+)?'
    byte_string_re = re.compile(byte_string_pattern, re.IGNORECASE)

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[Any], handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.with_info_after_validator_function(
            function=cls._validate,
            schema=core_schema.union_schema(
                [
                    core_schema.str_schema(pattern=cls.byte_string_pattern),
                    core_schema.int_schema(ge=0),
                ],
                custom_error_type='byte_size',
                custom_error_message='could not parse value and unit from byte string',
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                int, return_schema=core_schema.int_schema(ge=0)
            ),
        )

    @classmethod
    def _validate(cls, input_value: Any, /, _: core_schema.ValidationInfo) -> ByteSize:
        try:
            return cls(int(input_value))
        except ValueError:
            pass

        str_match = cls.byte_string_re.match(str(input_value))
        if str_match is None:
            raise PydanticCustomError('byte_size', 'could not parse value and unit from byte string')

        scalar, unit = str_match.groups()
        if unit is None:
            unit = 'b'

        try:
            unit_mult = cls.byte_sizes[unit.lower()]
        except KeyError:
            raise PydanticCustomError('byte_size_unit', 'could not interpret byte unit: {unit}', {'unit': unit})

        return cls(int(float(scalar) * unit_mult))

    def human_readable(self, decimal: bool = False, separator: str = '') -> str:
        """Converts a byte size to a human readable string.

        Args:
            decimal: If True, use decimal units (e.g. 1000 bytes per KB). If False, use binary units
                (e.g. 1024 bytes per KiB).
            separator: A string used to split the value and unit. Defaults to an empty string ('').

        Returns:
            A human readable string representation of the byte size.
        """
        if decimal:
            divisor = 1000
            units = 'B', 'KB', 'MB', 'GB', 'TB', 'PB'
            final_unit = 'EB'
        else:
            divisor = 1024
            units = 'B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'
            final_unit = 'EiB'

        num = float(self)
        for unit in units:
            if abs(num) < divisor:
                if unit == 'B':
                    return f'{num:0.0f}{separator}{unit}'
                else:
                    return f'{num:0.1f}{separator}{unit}'
            num /= divisor

        return f'{num:0.1f}{separator}{final_unit}'

    def to(self, unit: str) -> float:
        """Converts a byte size to another unit, including both byte and bit units.

        Args:
            unit: The unit to convert to. Must be one of the following: B, KB, MB, GB, TB, PB, EB,
                KiB, MiB, GiB, TiB, PiB, EiB (byte units) and
                bit, kbit, mbit, gbit, tbit, pbit, ebit,
                kibit, mibit, gibit, tibit, pibit, eibit (bit units).

        Returns:
            The byte size in the new unit.
        """
        try:
            unit_div = self.byte_sizes[unit.lower()]
        except KeyError:
            raise PydanticCustomError('byte_size_unit', 'Could not interpret byte unit: {unit}', {'unit': unit})

        return self / unit_div


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ DATE TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def _check_annotated_type(annotated_type: str, expected_type: str, annotation: str) -> None:
    if annotated_type != expected_type:
        raise PydanticUserError(f"'{annotation}' cannot annotate '{annotated_type}'.", code='invalid-annotated-type')


if TYPE_CHECKING:
    PastDate = Annotated[date, ...]
    FutureDate = Annotated[date, ...]
else:

    class PastDate:
        """A date in the past."""

        @classmethod
        def __get_pydantic_core_schema__(
            cls, source: type[Any], handler: GetCoreSchemaHandler
        ) -> core_schema.CoreSchema:
            if cls is source:
                # used directly as a type
                return core_schema.date_schema(now_op='past')
            else:
                schema = handler(source)
                _check_annotated_type(schema['type'], 'date', cls.__name__)
                schema['now_op'] = 'past'
                return schema

        def __repr__(self) -> str:
            return 'PastDate'

    class FutureDate:
        """A date in the future."""

        @classmethod
        def __get_pydantic_core_schema__(
            cls, source: type[Any], handler: GetCoreSchemaHandler
        ) -> core_schema.CoreSchema:
            if cls is source:
                # used directly as a type
                return core_schema.date_schema(now_op='future')
            else:
                schema = handler(source)
                _check_annotated_type(schema['type'], 'date', cls.__name__)
                schema['now_op'] = 'future'
                return schema

        def __repr__(self) -> str:
            return 'FutureDate'


def condate(
    *,
    strict: bool | None = None,
    gt: date | None = None,
    ge: date | None = None,
    lt: date | None = None,
    le: date | None = None,
) -> type[date]:
    """A wrapper for date that adds constraints.

    Args:
        strict: Whether to validate the date value in strict mode. Defaults to `None`.
        gt: The value must be greater than this. Defaults to `None`.
        ge: The value must be greater than or equal to this. Defaults to `None`.
        lt: The value must be less than this. Defaults to `None`.
        le: The value must be less than or equal to this. Defaults to `None`.

    Returns:
        A date type with the specified constraints.
    """
    return Annotated[  # pyright: ignore[reportReturnType]
        date,
        Strict(strict) if strict is not None else None,
        annotated_types.Interval(gt=gt, ge=ge, lt=lt, le=le),
    ]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ DATETIME TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if TYPE_CHECKING:
    AwareDatetime = Annotated[datetime, ...]
    NaiveDatetime = Annotated[datetime, ...]
    PastDatetime = Annotated[datetime, ...]
    FutureDatetime = Annotated[datetime, ...]

else:

    class AwareDatetime:
        """A datetime that requires timezone info."""

        @classmethod
        def __get_pydantic_core_schema__(
            cls, source: type[Any], handler: GetCoreSchemaHandler
        ) -> core_schema.CoreSchema:
            if cls is source:
                # used directly as a type
                return core_schema.datetime_schema(tz_constraint='aware')
            else:
                schema = handler(source)
                _check_annotated_type(schema['type'], 'datetime', cls.__name__)
                schema['tz_constraint'] = 'aware'
                return schema

        def __repr__(self) -> str:
            return 'AwareDatetime'

    class NaiveDatetime:
        """A datetime that doesn't require timezone info."""

        @classmethod
        def __get_pydantic_core_schema__(
            cls, source: type[Any], handler: GetCoreSchemaHandler
        ) -> core_schema.CoreSchema:
            if cls is source:
                # used directly as a type
                return core_schema.datetime_schema(tz_constraint='naive')
            else:
                schema = handler(source)
                _check_annotated_type(schema['type'], 'datetime', cls.__name__)
                schema['tz_constraint'] = 'naive'
                return schema

        def __repr__(self) -> str:
            return 'NaiveDatetime'

    class PastDatetime:
        """A datetime that must be in the past."""

        @classmethod
        def __get_pydantic_core_schema__(
            cls, source: type[Any], handler: GetCoreSchemaHandler
        ) -> core_schema.CoreSchema:
            if cls is source:
                # used directly as a type
                return core_schema.datetime_schema(now_op='past')
            else:
                schema = handler(source)
                _check_annotated_type(schema['type'], 'datetime', cls.__name__)
                schema['now_op'] = 'past'
                return schema

        def __repr__(self) -> str:
            return 'PastDatetime'

    class FutureDatetime:
        """A datetime that must be in the future."""

        @classmethod
        def __get_pydantic_core_schema__(
            cls, source: type[Any], handler: GetCoreSchemaHandler
        ) -> core_schema.CoreSchema:
            if cls is source:
                # used directly as a type
                return core_schema.datetime_schema(now_op='future')
            else:
                schema = handler(source)
                _check_annotated_type(schema['type'], 'datetime', cls.__name__)
                schema['now_op'] = 'future'
                return schema

        def __repr__(self) -> str:
            return 'FutureDatetime'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Encoded TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class EncoderProtocol(Protocol):
    """Protocol for encoding and decoding data to and from bytes."""

    @classmethod
    def decode(cls, data: bytes) -> bytes:
        """Decode the data using the encoder.

        Args:
            data: The data to decode.

        Returns:
            The decoded data.
        """
        ...

    @classmethod
    def encode(cls, value: bytes) -> bytes:
        """Encode the data using the encoder.

        Args:
            value: The data to encode.

        Returns:
            The encoded data.
        """
        ...

    @classmethod
    def get_json_format(cls) -> str:
        """Get the JSON format for the encoded data.

        Returns:
            The JSON format for the encoded data.
        """
        ...


class Base64Encoder(EncoderProtocol):
    """Standard (non-URL-safe) Base64 encoder."""

    @classmethod
    def decode(cls, data: bytes) -> bytes:
        """Decode the data from base64 encoded bytes to original bytes data.

        Args:
            data: The data to decode.

        Returns:
            The decoded data.
        """
        try:
            return base64.b64decode(data)
        except ValueError as e:
            raise PydanticCustomError('base64_decode', "Base64 decoding error: '{error}'", {'error': str(e)})

    @classmethod
    def encode(cls, value: bytes) -> bytes:
        """Encode the data from bytes to a base64 encoded bytes.

        Args:
            value: The data to encode.

        Returns:
            The encoded data.
        """
        return base64.b64encode(value)

    @classmethod
    def get_json_format(cls) -> Literal['base64']:
        """Get the JSON format for the encoded data.

        Returns:
            The JSON format for the encoded data.
        """
        return 'base64'


class Base64UrlEncoder(EncoderProtocol):
    """URL-safe Base64 encoder."""

    @classmethod
    def decode(cls, data: bytes) -> bytes:
        """Decode the data from base64 encoded bytes to original bytes data.

        Args:
            data: The data to decode.

        Returns:
            The decoded data.
        """
        try:
            return base64.urlsafe_b64decode(data)
        except ValueError as e:
            raise PydanticCustomError('base64_decode', "Base64 decoding error: '{error}'", {'error': str(e)})

    @classmethod
    def encode(cls, value: bytes) -> bytes:
        """Encode the data from bytes to a base64 encoded bytes.

        Args:
            value: The data to encode.

        Returns:
            The encoded data.
        """
        return base64.urlsafe_b64encode(value)

    @classmethod
    def get_json_format(cls) -> Literal['base64url']:
        """Get the JSON format for the encoded data.

        Returns:
            The JSON format for the encoded data.
        """
        return 'base64url'


@_dataclasses.dataclass(**_internal_dataclass.slots_true)
class EncodedBytes:
    """A bytes type that is encoded and decoded using the specified encoder.

    `EncodedBytes` needs an encoder that implements `EncoderProtocol` to operate.

    ```python
    from typing import Annotated

    from pydantic import BaseModel, EncodedBytes, EncoderProtocol, ValidationError

    class MyEncoder(EncoderProtocol):
        @classmethod
        def decode(cls, data: bytes) -> bytes:
            if data == b'**undecodable**':
                raise ValueError('Cannot decode data')
            return data[13:]

        @classmethod
        def encode(cls, value: bytes) -> bytes:
            return b'**encoded**: ' + value

        @classmethod
        def get_json_format(cls) -> str:
            return 'my-encoder'

    MyEncodedBytes = Annotated[bytes, EncodedBytes(encoder=MyEncoder)]

    class Model(BaseModel):
        my_encoded_bytes: MyEncodedBytes

    # Initialize the model with encoded data
    m = Model(my_encoded_bytes=b'**encoded**: some bytes')

    # Access decoded value
    print(m.my_encoded_bytes)
    #> b'some bytes'

    # Serialize into the encoded form
    print(m.model_dump())
    #> {'my_encoded_bytes': b'**encoded**: some bytes'}

    # Validate encoded data
    try:
        Model(my_encoded_bytes=b'**undecodable**')
    except ValidationError as e:
        print(e)
        '''
        1 validation error for Model
        my_encoded_bytes
          Value error, Cannot decode data [type=value_error, input_value=b'**undecodable**', input_type=bytes]
        '''
    ```
    """

    encoder: type[EncoderProtocol]

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        field_schema = handler(core_schema)
        field_schema.update(type='string', format=self.encoder.get_json_format())
        return field_schema

    def __get_pydantic_core_schema__(self, source: type[Any], handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        schema = handler(source)
        _check_annotated_type(schema['type'], 'bytes', self.__class__.__name__)
        return core_schema.with_info_after_validator_function(
            function=self.decode,
            schema=schema,
            serialization=core_schema.plain_serializer_function_ser_schema(function=self.encode),
        )

    def decode(self, data: bytes, _: core_schema.ValidationInfo) -> bytes:
        """Decode the data using the specified encoder.

        Args:
            data: The data to decode.

        Returns:
            The decoded data.
        """
        return self.encoder.decode(data)

    def encode(self, value: bytes) -> bytes:
        """Encode the data using the specified encoder.

        Args:
            value: The data to encode.

        Returns:
            The encoded data.
        """
        return self.encoder.encode(value)

    def __hash__(self) -> int:
        return hash(self.encoder)


@_dataclasses.dataclass(**_internal_dataclass.slots_true)
class EncodedStr:
    """A str type that is encoded and decoded using the specified encoder.

    `EncodedStr` needs an encoder that implements `EncoderProtocol` to operate.

    ```python
    from typing import Annotated

    from pydantic import BaseModel, EncodedStr, EncoderProtocol, ValidationError

    class MyEncoder(EncoderProtocol):
        @classmethod
        def decode(cls, data: bytes) -> bytes:
            if data == b'**undecodable**':
                raise ValueError('Cannot decode data')
            return data[13:]

        @classmethod
        def encode(cls, value: bytes) -> bytes:
            return b'**encoded**: ' + value

        @classmethod
        def get_json_format(cls) -> str:
            return 'my-encoder'

    MyEncodedStr = Annotated[str, EncodedStr(encoder=MyEncoder)]

    class Model(BaseModel):
        my_encoded_str: MyEncodedStr

    # Initialize the model with encoded data
    m = Model(my_encoded_str='**encoded**: some str')

    # Access decoded value
    print(m.my_encoded_str)
    #> some str

    # Serialize into the encoded form
    print(m.model_dump())
    #> {'my_encoded_str': '**encoded**: some str'}

    # Validate encoded data
    try:
        Model(my_encoded_str='**undecodable**')
    except ValidationError as e:
        print(e)
        '''
        1 validation error for Model
        my_encoded_str
          Value error, Cannot decode data [type=value_error, input_value='**undecodable**', input_type=str]
        '''
    ```
    """

    encoder: type[EncoderProtocol]

    def __get_pydantic_json_schema__(
        self, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        field_schema = handler(core_schema)
        field_schema.update(type='string', format=self.encoder.get_json_format())
        return field_schema

    def __get_pydantic_core_schema__(self, source: type[Any], handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        schema = handler(source)
        _check_annotated_type(schema['type'], 'str', self.__class__.__name__)
        return core_schema.with_info_after_validator_function(
            function=self.decode_str,
            schema=schema,
            serialization=core_schema.plain_serializer_function_ser_schema(function=self.encode_str),
        )

    def decode_str(self, data: str, _: core_schema.ValidationInfo) -> str:
        """Decode the data using the specified encoder.

        Args:
            data: The data to decode.

        Returns:
            The decoded data.
        """
        return self.encoder.decode(data.encode()).decode()

    def encode_str(self, value: str) -> str:
        """Encode the data using the specified encoder.

        Args:
            value: The data to encode.

        Returns:
            The encoded data.
        """
        return self.encoder.encode(value.encode()).decode()  # noqa: UP008

    def __hash__(self) -> int:
        return hash(self.encoder)


Base64Bytes = Annotated[bytes, EncodedBytes(encoder=Base64Encoder)]
"""A bytes type that is encoded and decoded using the standard (non-URL-safe) base64 encoder.

Note:
    Under the hood, `Base64Bytes` uses the standard library `base64.b64encode` and `base64.b64decode` functions.

    As a result, attempting to decode url-safe base64 data using the `Base64Bytes` type may fail or produce an incorrect
    decoding.

Warning:
    In versions of Pydantic prior to v2.10, `Base64Bytes` used [`base64.encodebytes`][base64.encodebytes]
    and [`base64.decodebytes`][base64.decodebytes] functions. According to the [base64 documentation](https://docs.python.org/3/library/base64.html),
    these methods are considered legacy implementation, and thus, Pydantic v2.10+ now uses the modern
    [`base64.b64encode`][base64.b64encode] and [`base64.b64decode`][base64.b64decode] functions.

    If you'd still like to use these legacy encoders / decoders, you can achieve this by creating a custom annotated type,
    like follows:

    ```python
    import base64
    from typing import Annotated, Literal

    from pydantic_core import PydanticCustomError

    from pydantic import EncodedBytes, EncoderProtocol

    class LegacyBase64Encoder(EncoderProtocol):
        @classmethod
        def decode(cls, data: bytes) -> bytes:
            try:
                return base64.decodebytes(data)
            except ValueError as e:
                raise PydanticCustomError(
                    'base64_decode',
                    "Base64 decoding error: '{error}'",
                    {'error': str(e)},
                )

        @classmethod
        def encode(cls, value: bytes) -> bytes:
            return base64.encodebytes(value)

        @classmethod
        def get_json_format(cls) -> Literal['base64']:
            return 'base64'

    LegacyBase64Bytes = Annotated[bytes, EncodedBytes(encoder=LegacyBase64Encoder)]
    ```

```python
from pydantic import Base64Bytes, BaseModel, ValidationError

class Model(BaseModel):
    base64_bytes: Base64Bytes

# Initialize the model with base64 data
m = Model(base64_bytes=b'VGhpcyBpcyB0aGUgd2F5')

# Access decoded value
print(m.base64_bytes)
#> b'This is the way'

# Serialize into the base64 form
print(m.model_dump())
#> {'base64_bytes': b'VGhpcyBpcyB0aGUgd2F5'}

# Validate base64 data
try:
    print(Model(base64_bytes=b'undecodable').base64_bytes)
except ValidationError as e:
    print(e)
    '''
    1 validation error for Model
    base64_bytes
      Base64 decoding error: 'Incorrect padding' [type=base64_decode, input_value=b'undecodable', input_type=bytes]
    '''
```
"""
Base64Str = Annotated[str, EncodedStr(encoder=Base64Encoder)]
"""A str type that is encoded and decoded using the standard (non-URL-safe) base64 encoder.

Note:
    Under the hood, `Base64Str` uses the standard library `base64.b64encode` and `base64.b64decode` functions.

    As a result, attempting to decode url-safe base64 data using the `Base64Str` type may fail or produce an incorrect
    decoding.

Warning:
    In versions of Pydantic prior to v2.10, `Base64Str` used [`base64.encodebytes`][base64.encodebytes]
    and [`base64.decodebytes`][base64.decodebytes] functions. According to the [base64 documentation](https://docs.python.org/3/library/base64.html),
    these methods are considered legacy implementation, and thus, Pydantic v2.10+ now uses the modern
    [`base64.b64encode`][base64.b64encode] and [`base64.b64decode`][base64.b64decode] functions.

    See the [`Base64Bytes`][pydantic.types.Base64Bytes] type for more information on how to
    replicate the old behavior with the legacy encoders / decoders.

```python
from pydantic import Base64Str, BaseModel, ValidationError

class Model(BaseModel):
    base64_str: Base64Str

# Initialize the model with base64 data
m = Model(base64_str='VGhlc2UgYXJlbid0IHRoZSBkcm9pZHMgeW91J3JlIGxvb2tpbmcgZm9y')

# Access decoded value
print(m.base64_str)
#> These aren't the droids you're looking for

# Serialize into the base64 form
print(m.model_dump())
#> {'base64_str': 'VGhlc2UgYXJlbid0IHRoZSBkcm9pZHMgeW91J3JlIGxvb2tpbmcgZm9y'}

# Validate base64 data
try:
    print(Model(base64_str='undecodable').base64_str)
except ValidationError as e:
    print(e)
    '''
    1 validation error for Model
    base64_str
      Base64 decoding error: 'Incorrect padding' [type=base64_decode, input_value='undecodable', input_type=str]
    '''
```
"""
Base64UrlBytes = Annotated[bytes, EncodedBytes(encoder=Base64UrlEncoder)]
"""A bytes type that is encoded and decoded using the URL-safe base64 encoder.

Note:
    Under the hood, `Base64UrlBytes` use standard library `base64.urlsafe_b64encode` and `base64.urlsafe_b64decode`
    functions.

    As a result, the `Base64UrlBytes` type can be used to faithfully decode "vanilla" base64 data
    (using `'+'` and `'/'`).

```python
from pydantic import Base64UrlBytes, BaseModel

class Model(BaseModel):
    base64url_bytes: Base64UrlBytes

# Initialize the model with base64 data
m = Model(base64url_bytes=b'SHc_dHc-TXc==')
print(m)
#> base64url_bytes=b'Hw?tw>Mw'
```
"""
Base64UrlStr = Annotated[str, EncodedStr(encoder=Base64UrlEncoder)]
"""A str type that is encoded and decoded using the URL-safe base64 encoder.

Note:
    Under the hood, `Base64UrlStr` use standard library `base64.urlsafe_b64encode` and `base64.urlsafe_b64decode`
    functions.

    As a result, the `Base64UrlStr` type can be used to faithfully decode "vanilla" base64 data (using `'+'` and `'/'`).

```python
from pydantic import Base64UrlStr, BaseModel

class Model(BaseModel):
    base64url_str: Base64UrlStr

# Initialize the model with base64 data
m = Model(base64url_str='SHc_dHc-TXc==')
print(m)
#> base64url_str='Hw?tw>Mw'
```
"""


__getattr__ = getattr_migration(__name__)


@_dataclasses.dataclass(**_internal_dataclass.slots_true)
class GetPydanticSchema:
    """!!! abstract "Usage Documentation"
        [Using `GetPydanticSchema` to Reduce Boilerplate](../concepts/types.md#using-getpydanticschema-to-reduce-boilerplate)

    A convenience class for creating an annotation that provides pydantic custom type hooks.

    This class is intended to eliminate the need to create a custom "marker" which defines the
     `__get_pydantic_core_schema__` and `__get_pydantic_json_schema__` custom hook methods.

    For example, to have a field treated by type checkers as `int`, but by pydantic as `Any`, you can do:
    ```python
    from typing import Annotated, Any

    from pydantic import BaseModel, GetPydanticSchema

    HandleAsAny = GetPydanticSchema(lambda _s, h: h(Any))

    class Model(BaseModel):
        x: Annotated[int, HandleAsAny]  # pydantic sees `x: Any`

    print(repr(Model(x='abc').x))
    #> 'abc'
    ```
    """

    get_pydantic_core_schema: Callable[[Any, GetCoreSchemaHandler], CoreSchema] | None = None
    get_pydantic_json_schema: Callable[[Any, GetJsonSchemaHandler], JsonSchemaValue] | None = None

    # Note: we may want to consider adding a convenience staticmethod `def for_type(type_: Any) -> GetPydanticSchema:`
    #   which returns `GetPydanticSchema(lambda _s, h: h(type_))`

    if not TYPE_CHECKING:
        # We put `__getattr__` in a non-TYPE_CHECKING block because otherwise, mypy allows arbitrary attribute access

        def __getattr__(self, item: str) -> Any:
            """Use this rather than defining `__get_pydantic_core_schema__` etc. to reduce the number of nested calls."""
            if item == '__get_pydantic_core_schema__' and self.get_pydantic_core_schema:
                return self.get_pydantic_core_schema
            elif item == '__get_pydantic_json_schema__' and self.get_pydantic_json_schema:
                return self.get_pydantic_json_schema
            else:
                return object.__getattribute__(self, item)

    __hash__ = object.__hash__


@_dataclasses.dataclass(**_internal_dataclass.slots_true, frozen=True)
class Tag:
    """Provides a way to specify the expected tag to use for a case of a (callable) discriminated union.

    Also provides a way to label a union case in error messages.

    When using a callable `Discriminator`, attach a `Tag` to each case in the `Union` to specify the tag that
    should be used to identify that case. For example, in the below example, the `Tag` is used to specify that
    if `get_discriminator_value` returns `'apple'`, the input should be validated as an `ApplePie`, and if it
    returns `'pumpkin'`, the input should be validated as a `PumpkinPie`.

    The primary role of the `Tag` here is to map the return value from the callable `Discriminator` function to
    the appropriate member of the `Union` in question.

    ```python
    from typing import Annotated, Any, Literal, Union

    from pydantic import BaseModel, Discriminator, Tag

    class Pie(BaseModel):
        time_to_cook: int
        num_ingredients: int

    class ApplePie(Pie):
        fruit: Literal['apple'] = 'apple'

    class PumpkinPie(Pie):
        filling: Literal['pumpkin'] = 'pumpkin'

    def get_discriminator_value(v: Any) -> str:
        if isinstance(v, dict):
            return v.get('fruit', v.get('filling'))
        return getattr(v, 'fruit', getattr(v, 'filling', None))

    class ThanksgivingDinner(BaseModel):
        dessert: Annotated[
            Union[
                Annotated[ApplePie, Tag('apple')],
                Annotated[PumpkinPie, Tag('pumpkin')],
            ],
            Discriminator(get_discriminator_value),
        ]

    apple_variation = ThanksgivingDinner.model_validate(
        {'dessert': {'fruit': 'apple', 'time_to_cook': 60, 'num_ingredients': 8}}
    )
    print(repr(apple_variation))
    '''
    ThanksgivingDinner(dessert=ApplePie(time_to_cook=60, num_ingredients=8, fruit='apple'))
    '''

    pumpkin_variation = ThanksgivingDinner.model_validate(
        {
            'dessert': {
                'filling': 'pumpkin',
                'time_to_cook': 40,
                'num_ingredients': 6,
            }
        }
    )
    print(repr(pumpkin_variation))
    '''
    ThanksgivingDinner(dessert=PumpkinPie(time_to_cook=40, num_ingredients=6, filling='pumpkin'))
    '''
    ```

    !!! note
        You must specify a `Tag` for every case in a `Tag` that is associated with a
        callable `Discriminator`. Failing to do so will result in a `PydanticUserError` with code
        [`callable-discriminator-no-tag`](../errors/usage_errors.md#callable-discriminator-no-tag).

    See the [Discriminated Unions] concepts docs for more details on how to use `Tag`s.

    [Discriminated Unions]: ../concepts/unions.md#discriminated-unions
    """

    tag: str

    def __get_pydantic_core_schema__(self, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        schema = handler(source_type)
        metadata = cast('CoreMetadata', schema.setdefault('metadata', {}))
        metadata['pydantic_internal_union_tag_key'] = self.tag
        return schema


@_dataclasses.dataclass(**_internal_dataclass.slots_true, frozen=True)
class Discriminator:
    """!!! abstract "Usage Documentation"
        [Discriminated Unions with `Callable` `Discriminator`](../concepts/unions.md#discriminated-unions-with-callable-discriminator)

    Provides a way to use a custom callable as the way to extract the value of a union discriminator.

    This allows you to get validation behavior like you'd get from `Field(discriminator=<field_name>)`,
    but without needing to have a single shared field across all the union choices. This also makes it
    possible to handle unions of models and primitive types with discriminated-union-style validation errors.
    Finally, this allows you to use a custom callable as the way to identify which member of a union a value
    belongs to, while still seeing all the performance benefits of a discriminated union.

    Consider this example, which is much more performant with the use of `Discriminator` and thus a `TaggedUnion`
    than it would be as a normal `Union`.

    ```python
    from typing import Annotated, Any, Literal, Union

    from pydantic import BaseModel, Discriminator, Tag

    class Pie(BaseModel):
        time_to_cook: int
        num_ingredients: int

    class ApplePie(Pie):
        fruit: Literal['apple'] = 'apple'

    class PumpkinPie(Pie):
        filling: Literal['pumpkin'] = 'pumpkin'

    def get_discriminator_value(v: Any) -> str:
        if isinstance(v, dict):
            return v.get('fruit', v.get('filling'))
        return getattr(v, 'fruit', getattr(v, 'filling', None))

    class ThanksgivingDinner(BaseModel):
        dessert: Annotated[
            Union[
                Annotated[ApplePie, Tag('apple')],
                Annotated[PumpkinPie, Tag('pumpkin')],
            ],
            Discriminator(get_discriminator_value),
        ]

    apple_variation = ThanksgivingDinner.model_validate(
        {'dessert': {'fruit': 'apple', 'time_to_cook': 60, 'num_ingredients': 8}}
    )
    print(repr(apple_variation))
    '''
    ThanksgivingDinner(dessert=ApplePie(time_to_cook=60, num_ingredients=8, fruit='apple'))
    '''

    pumpkin_variation = ThanksgivingDinner.model_validate(
        {
            'dessert': {
                'filling': 'pumpkin',
                'time_to_cook': 40,
                'num_ingredients': 6,
            }
        }
    )
    print(repr(pumpkin_variation))
    '''
    ThanksgivingDinner(dessert=PumpkinPie(time_to_cook=40, num_ingredients=6, filling='pumpkin'))
    '''
    ```

    See the [Discriminated Unions] concepts docs for more details on how to use `Discriminator`s.

    [Discriminated Unions]: ../concepts/unions.md#discriminated-unions
    """

    discriminator: str | Callable[[Any], Hashable]
    """The callable or field name for discriminating the type in a tagged union.

    A `Callable` discriminator must extract the value of the discriminator from the input.
    A `str` discriminator must be the name of a field to discriminate against.
    """
    custom_error_type: str | None = None
    """Type to use in [custom errors](../errors/errors.md) replacing the standard discriminated union
    validation errors.
    """
    custom_error_message: str | None = None
    """Message to use in custom errors."""
    custom_error_context: dict[str, int | str | float] | None = None
    """Context to use in custom errors."""

    def __get_pydantic_core_schema__(self, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        if not is_union_origin(get_origin(source_type)):
            raise TypeError(f'{type(self).__name__} must be used with a Union type, not {source_type}')

        if isinstance(self.discriminator, str):
            from pydantic import Field

            return handler(Annotated[source_type, Field(discriminator=self.discriminator)])
        else:
            original_schema = handler(source_type)
            return self._convert_schema(original_schema)

    def _convert_schema(self, original_schema: core_schema.CoreSchema) -> core_schema.TaggedUnionSchema:
        if original_schema['type'] != 'union':
            # This likely indicates that the schema was a single-item union that was simplified.
            # In this case, we do the same thing we do in
            # `pydantic._internal._discriminated_union._ApplyInferredDiscriminator._apply_to_root`, namely,
            # package the generated schema back into a single-item union.
            original_schema = core_schema.union_schema([original_schema])

        tagged_union_choices = {}
        for choice in original_schema['choices']:
            tag = None
            if isinstance(choice, tuple):
                choice, tag = choice
            metadata = cast('CoreMetadata | None', choice.get('metadata'))
            if metadata is not None:
                tag = metadata.get('pydantic_internal_union_tag_key') or tag
            if tag is None:
                raise PydanticUserError(
                    f'`Tag` not provided for choice {choice} used with `Discriminator`',
                    code='callable-discriminator-no-tag',
                )
            tagged_union_choices[tag] = choice

        # Have to do these verbose checks to ensure falsy values ('' and {}) don't get ignored
        custom_error_type = self.custom_error_type
        if custom_error_type is None:
            custom_error_type = original_schema.get('custom_error_type')

        custom_error_message = self.custom_error_message
        if custom_error_message is None:
            custom_error_message = original_schema.get('custom_error_message')

        custom_error_context = self.custom_error_context
        if custom_error_context is None:
            custom_error_context = original_schema.get('custom_error_context')

        custom_error_type = original_schema.get('custom_error_type') if custom_error_type is None else custom_error_type
        return core_schema.tagged_union_schema(
            tagged_union_choices,
            self.discriminator,
            custom_error_type=custom_error_type,
            custom_error_message=custom_error_message,
            custom_error_context=custom_error_context,
            strict=original_schema.get('strict'),
            ref=original_schema.get('ref'),
            metadata=original_schema.get('metadata'),
            serialization=original_schema.get('serialization'),
        )


_JSON_TYPES = {int, float, str, bool, list, dict, type(None)}


def _get_type_name(x: Any) -> str:
    type_ = type(x)
    if type_ in _JSON_TYPES:
        return type_.__name__

    # Handle proper subclasses; note we don't need to handle None or bool here
    if isinstance(x, int):
        return 'int'
    if isinstance(x, float):
        return 'float'
    if isinstance(x, str):
        return 'str'
    if isinstance(x, list):
        return 'list'
    if isinstance(x, dict):
        return 'dict'

    # Fail by returning the type's actual name
    return getattr(type_, '__name__', '<no type name>')


class _AllowAnyJson:
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        python_schema = handler(source_type)
        return core_schema.json_or_python_schema(json_schema=core_schema.any_schema(), python_schema=python_schema)


if TYPE_CHECKING:
    # This seems to only be necessary for mypy
    JsonValue: TypeAlias = Union[
        list['JsonValue'],
        dict[str, 'JsonValue'],
        str,
        bool,
        int,
        float,
        None,
    ]
    """A `JsonValue` is used to represent a value that can be serialized to JSON.

    It may be one of:

    * `list['JsonValue']`
    * `dict[str, 'JsonValue']`
    * `str`
    * `bool`
    * `int`
    * `float`
    * `None`

    The following example demonstrates how to use `JsonValue` to validate JSON data,
    and what kind of errors to expect when input data is not json serializable.

    ```python
    import json

    from pydantic import BaseModel, JsonValue, ValidationError

    class Model(BaseModel):
        j: JsonValue

    valid_json_data = {'j': {'a': {'b': {'c': 1, 'd': [2, None]}}}}
    invalid_json_data = {'j': {'a': {'b': ...}}}

    print(repr(Model.model_validate(valid_json_data)))
    #> Model(j={'a': {'b': {'c': 1, 'd': [2, None]}}})
    print(repr(Model.model_validate_json(json.dumps(valid_json_data))))
    #> Model(j={'a': {'b': {'c': 1, 'd': [2, None]}}})

    try:
        Model.model_validate(invalid_json_data)
    except ValidationError as e:
        print(e)
        '''
        1 validation error for Model
        j.dict.a.dict.b
          input was not a valid JSON value [type=invalid-json-value, input_value=Ellipsis, input_type=ellipsis]
        '''
    ```
    """

else:
    JsonValue = TypeAliasType(
        'JsonValue',
        Annotated[
            Union[
                Annotated[list['JsonValue'], Tag('list')],
                Annotated[dict[str, 'JsonValue'], Tag('dict')],
                Annotated[str, Tag('str')],
                Annotated[bool, Tag('bool')],
                Annotated[int, Tag('int')],
                Annotated[float, Tag('float')],
                Annotated[None, Tag('NoneType')],
            ],
            Discriminator(
                _get_type_name,
                custom_error_type='invalid-json-value',
                custom_error_message='input was not a valid JSON value',
            ),
            _AllowAnyJson,
        ],
    )


class _OnErrorOmit:
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        # there is no actual default value here but we use with_default_schema since it already has the on_error
        # behavior implemented and it would be no more efficient to implement it on every other validator
        # or as a standalone validator
        return core_schema.with_default_schema(schema=handler(source_type), on_error='omit')


OnErrorOmit = Annotated[T, _OnErrorOmit]
"""
When used as an item in a list, the key type in a dict, optional values of a TypedDict, etc.
this annotation omits the item from the iteration if there is any error validating it.
That is, instead of a [`ValidationError`][pydantic_core.ValidationError] being propagated up and the entire iterable being discarded
any invalid items are discarded and the valid ones are returned.
"""


@_dataclasses.dataclass
class FailFast(_fields.PydanticMetadata, BaseMetadata):
    """A `FailFast` annotation can be used to specify that validation should stop at the first error.

    This can be useful when you want to validate a large amount of data and you only need to know if it's valid or not.

    You might want to enable this setting if you want to validate your data faster (basically, if you use this,
    validation will be more performant with the caveat that you get less information).

    ```python
    from typing import Annotated

    from pydantic import BaseModel, FailFast, ValidationError

    class Model(BaseModel):
        x: Annotated[list[int], FailFast()]

    # This will raise a single error for the first invalid value and stop validation
    try:
        obj = Model(x=[1, 2, 'a', 4, 5, 'b', 7, 8, 9, 'c'])
    except ValidationError as e:
        print(e)
        '''
        1 validation error for Model
        x.2
          Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='a', input_type=str]
        '''
    ```
    """

    fail_fast: bool = True

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\lisp.py ===
"""
    pygments.lexers.lisp
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for Lispy languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, words, default
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Literal, Error, Whitespace

from pygments.lexers.python import PythonLexer

from pygments.lexers._scheme_builtins import scheme_keywords, scheme_builtins

__all__ = ['SchemeLexer', 'CommonLispLexer', 'HyLexer', 'RacketLexer',
           'NewLispLexer', 'EmacsLispLexer', 'ShenLexer', 'CPSALexer',
           'XtlangLexer', 'FennelLexer', 'JanetLexer']


class SchemeLexer(RegexLexer):
    """
    A Scheme lexer.

    This parser is checked with pastes from the LISP pastebin
    at http://paste.lisp.org/ to cover as much syntax as possible.

    It supports the full Scheme syntax as defined in R5RS.
    """
    name = 'Scheme'
    url = 'http://www.scheme-reports.org/'
    aliases = ['scheme', 'scm']
    filenames = ['*.scm', '*.ss']
    mimetypes = ['text/x-scheme', 'application/x-scheme']
    version_added = '0.6'

    flags = re.DOTALL | re.MULTILINE

    # valid names for identifiers
    # well, names can only not consist fully of numbers
    # but this should be good enough for now
    valid_name = r'[\w!$%&*+,/:<=>?@^~|-]+'

    # Use within verbose regexes
    token_end = r'''
      (?=
        \s         # whitespace
        | ;        # comment
        | \#[;|!] # fancy comments
        | [)\]]    # end delimiters
        | $        # end of file
      )
    '''

    # Recognizing builtins.
    def get_tokens_unprocessed(self, text):
        for index, token, value in super().get_tokens_unprocessed(text):
            if token is Name.Function or token is Name.Variable:
                if value in scheme_keywords:
                    yield index, Keyword, value
                elif value in scheme_builtins:
                    yield index, Name.Builtin, value
                else:
                    yield index, token, value
            else:
                yield index, token, value

    # Scheme has funky syntactic rules for numbers. These are all
    # valid number literals: 5.0e55|14, 14/13, -1+5j, +1@5, #b110,
    # #o#Iinf.0-nan.0i.  This is adapted from the formal grammar given
    # in http://www.r6rs.org/final/r6rs.pdf, section 4.2.1.  Take a
    # deep breath ...

    # It would be simpler if we could just not bother about invalid
    # numbers like #b35. But we cannot parse 'abcdef' without #x as a
    # number.

    number_rules = {}
    for base in (2, 8, 10, 16):
        if base == 2:
            digit = r'[01]'
            radix = r'( \#[bB] )'
        elif base == 8:
            digit = r'[0-7]'
            radix = r'( \#[oO] )'
        elif base == 10:
            digit = r'[0-9]'
            radix = r'( (\#[dD])? )'
        elif base == 16:
            digit = r'[0-9a-fA-F]'
            radix = r'( \#[xX] )'

        # Radix, optional exactness indicator.
        prefix = rf'''
          (
            {radix} (\#[iIeE])?
            | \#[iIeE] {radix}
          )
        '''

        # Simple unsigned number or fraction.
        ureal = rf'''
          (
            {digit}+
            ( / {digit}+ )?
          )
        '''

        # Add decimal numbers.
        if base == 10:
            decimal = r'''
              (
                # Decimal part
                (
                  [0-9]+ ([.][0-9]*)?
                  | [.][0-9]+
                )

                # Optional exponent
                (
                  [eEsSfFdDlL] [+-]? [0-9]+
                )?

                # Optional mantissa width
                (
                  \|[0-9]+
                )?
              )
            '''
            ureal = rf'''
              (
                {decimal} (?!/)
                | {ureal}
              )
            '''

        naninf = r'(nan.0|inf.0)'

        real = rf'''
          (
            [+-] {naninf}  # Sign mandatory
            | [+-]? {ureal}    # Sign optional
          )
        '''

        complex_ = rf'''
          (
            {real}?  [+-]  ({naninf}|{ureal})?  i
            | {real} (@ {real})?

          )
        '''

        num = rf'''(?x)
          (
            {prefix}
            {complex_}
          )
          # Need to ensure we have a full token. 1+ is not a
          # number followed by something else, but a function
          # name.
          {token_end}
        '''

        number_rules[base] = num

    # If you have a headache now, say thanks to RnRS editors.

    # Doing it this way is simpler than splitting the number(10)
    # regex in a floating-point and a no-floating-point version.
    def decimal_cb(self, match):
        if '.' in match.group():
            token_type = Number.Float # includes [+-](inf|nan).0
        else:
            token_type = Number.Integer
        yield match.start(), token_type, match.group()

    # --

    # The 'scheme-root' state parses as many expressions as needed, always
    # delegating to the 'scheme-value' state. The latter parses one complete
    # expression and immediately pops back. This is needed for the LilyPondLexer.
    # When LilyPond encounters a #, it starts parsing embedded Scheme code, and
    # returns to normal syntax after one expression. We implement this
    # by letting the LilyPondLexer subclass the SchemeLexer. When it finds
    # the #, the LilyPondLexer goes to the 'value' state, which then pops back
    # to LilyPondLexer. The 'root' state of the SchemeLexer merely delegates the
    # work to 'scheme-root'; this is so that LilyPondLexer can inherit
    # 'scheme-root' and redefine 'root'.

    tokens = {
        'root': [
            default('scheme-root'),
        ],
        'scheme-root': [
            default('value'),
        ],
        'value': [
            # the comments
            # and going to the end of the line
            (r';.*?$', Comment.Single),
            # multi-line comment
            (r'#\|', Comment.Multiline, 'multiline-comment'),
            # commented form (entire sexpr following)
            (r'#;[([]', Comment, 'commented-form'),
            # commented datum
            (r'#;', Comment, 'commented-datum'),
            # signifies that the program text that follows is written with the
            # lexical and datum syntax described in r6rs
            (r'#!r6rs', Comment),

            # whitespaces - usually not relevant
            (r'\s+', Whitespace),

            # numbers
            (number_rules[2], Number.Bin, '#pop'),
            (number_rules[8], Number.Oct, '#pop'),
            (number_rules[10], decimal_cb, '#pop'),
            (number_rules[16], Number.Hex, '#pop'),

            # strings, symbols, keywords and characters
            (r'"', String, 'string'),
            (r"'" + valid_name, String.Symbol, "#pop"),
            (r'#:' + valid_name, Keyword.Declaration, '#pop'),
            (r"#\\([()/'\"._!§$%& ?=+-]|[a-zA-Z0-9]+)", String.Char, "#pop"),

            # constants
            (r'(#t|#f)', Name.Constant, '#pop'),

            # special operators
            (r"('|#|`|,@|,|\.)", Operator),

            # first variable in a quoted string like
            # '(this is syntactic sugar)
            (r"(?<='\()" + valid_name, Name.Variable, '#pop'),
            (r"(?<=#\()" + valid_name, Name.Variable, '#pop'),

            # Functions -- note that this also catches variables
            # defined in let/let*, but there is little that can
            # be done about it.
            (r'(?<=\()' + valid_name, Name.Function, '#pop'),

            # find the remaining variables
            (valid_name, Name.Variable, '#pop'),

            # the famous parentheses!

            # Push scheme-root to enter a state that will parse as many things
            # as needed in the parentheses.
            (r'[([]', Punctuation, 'scheme-root'),
            # Pop one 'value', one 'scheme-root', and yet another 'value', so
            # we get back to a state parsing expressions as needed in the
            # enclosing context.
            (r'[)\]]', Punctuation, '#pop:3'),
        ],
        'multiline-comment': [
            (r'#\|', Comment.Multiline, '#push'),
            (r'\|#', Comment.Multiline, '#pop'),
            (r'[^|#]+', Comment.Multiline),
            (r'[|#]', Comment.Multiline),
        ],
        'commented-form': [
            (r'[([]', Comment, '#push'),
            (r'[)\]]', Comment, '#pop'),
            (r'[^()[\]]+', Comment),
        ],
        'commented-datum': [
            (rf'(?x).*?{token_end}', Comment, '#pop'),
        ],
        'string': [
            # Pops back from 'string', and pops 'value' as well.
            ('"', String, '#pop:2'),
            # Hex escape sequences, R6RS-style.
            (r'\\x[0-9a-fA-F]+;', String.Escape),
            # We try R6RS style first, but fall back to Guile-style.
            (r'\\x[0-9a-fA-F]{2}', String.Escape),
            # Other special escape sequences implemented by Guile.
            (r'\\u[0-9a-fA-F]{4}', String.Escape),
            (r'\\U[0-9a-fA-F]{6}', String.Escape),
            # Escape sequences are not overly standardized. Recognizing
            # a single character after the backslash should be good enough.
            # NB: we have DOTALL.
            (r'\\.', String.Escape),
            # The rest
            (r'[^\\"]+', String),
        ]
    }


class CommonLispLexer(RegexLexer):
    """
    A Common Lisp lexer.
    """
    name = 'Common Lisp'
    url = 'https://lisp-lang.org/'
    aliases = ['common-lisp', 'cl', 'lisp']
    filenames = ['*.cl', '*.lisp']
    mimetypes = ['text/x-common-lisp']
    version_added = '0.9'

    flags = re.IGNORECASE | re.MULTILINE

    # couple of useful regexes

    # characters that are not macro-characters and can be used to begin a symbol
    nonmacro = r'\\.|[\w!$%&*+-/<=>?@\[\]^{}~]'
    constituent = nonmacro + '|[#.:]'
    terminated = r'(?=[ "()\'\n,;`])'  # whitespace or terminating macro characters

    # symbol token, reverse-engineered from hyperspec
    # Take a deep breath...
    symbol = rf'(\|[^|]+\||(?:{nonmacro})(?:{constituent})*)'

    def __init__(self, **options):
        from pygments.lexers._cl_builtins import BUILTIN_FUNCTIONS, \
            SPECIAL_FORMS, MACROS, LAMBDA_LIST_KEYWORDS, DECLARATIONS, \
            BUILTIN_TYPES, BUILTIN_CLASSES
        self.builtin_function = BUILTIN_FUNCTIONS
        self.special_forms = SPECIAL_FORMS
        self.macros = MACROS
        self.lambda_list_keywords = LAMBDA_LIST_KEYWORDS
        self.declarations = DECLARATIONS
        self.builtin_types = BUILTIN_TYPES
        self.builtin_classes = BUILTIN_CLASSES
        RegexLexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        stack = ['root']
        for index, token, value in RegexLexer.get_tokens_unprocessed(self, text, stack):
            if token is Name.Variable:
                if value in self.builtin_function:
                    yield index, Name.Builtin, value
                    continue
                if value in self.special_forms:
                    yield index, Keyword, value
                    continue
                if value in self.macros:
                    yield index, Name.Builtin, value
                    continue
                if value in self.lambda_list_keywords:
                    yield index, Keyword, value
                    continue
                if value in self.declarations:
                    yield index, Keyword, value
                    continue
                if value in self.builtin_types:
                    yield index, Keyword.Type, value
                    continue
                if value in self.builtin_classes:
                    yield index, Name.Class, value
                    continue
            yield index, token, value

    tokens = {
        'root': [
            default('body'),
        ],
        'multiline-comment': [
            (r'#\|', Comment.Multiline, '#push'),  # (cf. Hyperspec 2.4.8.19)
            (r'\|#', Comment.Multiline, '#pop'),
            (r'[^|#]+', Comment.Multiline),
            (r'[|#]', Comment.Multiline),
        ],
        'commented-form': [
            (r'\(', Comment.Preproc, '#push'),
            (r'\)', Comment.Preproc, '#pop'),
            (r'[^()]+', Comment.Preproc),
        ],
        'body': [
            # whitespace
            (r'\s+', Whitespace),

            # single-line comment
            (r';.*$', Comment.Single),

            # multi-line comment
            (r'#\|', Comment.Multiline, 'multiline-comment'),

            # encoding comment (?)
            (r'#\d*Y.*$', Comment.Special),

            # strings and characters
            (r'"(\\.|\\\n|[^"\\])*"', String),
            # quoting
            (r":" + symbol, String.Symbol),
            (r"::" + symbol, String.Symbol),
            (r":#" + symbol, String.Symbol),
            (r"'" + symbol, String.Symbol),
            (r"'", Operator),
            (r"`", Operator),

            # decimal numbers
            (r'[-+]?\d+\.?' + terminated, Number.Integer),
            (r'[-+]?\d+/\d+' + terminated, Number),
            (r'[-+]?(\d*\.\d+([defls][-+]?\d+)?|\d+(\.\d*)?[defls][-+]?\d+)' +
             terminated, Number.Float),

            # sharpsign strings and characters
            (r"#\\." + terminated, String.Char),
            (r"#\\" + symbol, String.Char),

            # vector
            (r'#\(', Operator, 'body'),

            # bitstring
            (r'#\d*\*[01]*', Literal.Other),

            # uninterned symbol
            (r'#:' + symbol, String.Symbol),

            # read-time and load-time evaluation
            (r'#[.,]', Operator),

            # function shorthand
            (r'#\'', Name.Function),

            # binary rational
            (r'#b[+-]?[01]+(/[01]+)?', Number.Bin),

            # octal rational
            (r'#o[+-]?[0-7]+(/[0-7]+)?', Number.Oct),

            # hex rational
            (r'#x[+-]?[0-9a-f]+(/[0-9a-f]+)?', Number.Hex),

            # radix rational
            (r'#\d+r[+-]?[0-9a-z]+(/[0-9a-z]+)?', Number),

            # complex
            (r'(#c)(\()', bygroups(Number, Punctuation), 'body'),

            # array
            (r'(#\d+a)(\()', bygroups(Literal.Other, Punctuation), 'body'),

            # structure
            (r'(#s)(\()', bygroups(Literal.Other, Punctuation), 'body'),

            # path
            (r'#p?"(\\.|[^"])*"', Literal.Other),

            # reference
            (r'#\d+=', Operator),
            (r'#\d+#', Operator),

            # read-time comment
            (r'#+nil' + terminated + r'\s*\(', Comment.Preproc, 'commented-form'),

            # read-time conditional
            (r'#[+-]', Operator),

            # special operators that should have been parsed already
            (r'(,@|,|\.)', Operator),

            # special constants
            (r'(t|nil)' + terminated, Name.Constant),

            # functions and variables
            (r'\*' + symbol + r'\*', Name.Variable.Global),
            (symbol, Name.Variable),

            # parentheses
            (r'\(', Punctuation, 'body'),
            (r'\)', Punctuation, '#pop'),
        ],
    }

    def analyse_text(text):
        """Competes with Visual Prolog on *.cl"""
        # This is a *really* good indicator (and not conflicting with Visual Prolog)
        # '(defun ' first on a line
        # section keyword alone on line e.g. 'clauses'
        if re.search(r'^\s*\(defun\s', text):
            return 0.8
        else:
            return 0


class HyLexer(RegexLexer):
    """
    Lexer for Hy source code.
    """
    name = 'Hy'
    url = 'http://hylang.org/'
    aliases = ['hylang', 'hy']
    filenames = ['*.hy']
    mimetypes = ['text/x-hy', 'application/x-hy']
    version_added = '2.0'

    special_forms = (
        'cond', 'for', '->', '->>', 'car',
        'cdr', 'first', 'rest', 'let', 'when', 'unless',
        'import', 'do', 'progn', 'get', 'slice', 'assoc', 'with-decorator',
        ',', 'list_comp', 'kwapply', '~', 'is', 'in', 'is-not', 'not-in',
        'quasiquote', 'unquote', 'unquote-splice', 'quote', '|', '<<=', '>>=',
        'foreach', 'while',
        'eval-and-compile', 'eval-when-compile'
    )

    declarations = (
        'def', 'defn', 'defun', 'defmacro', 'defclass', 'lambda', 'fn', 'setv'
    )

    hy_builtins = ()

    hy_core = (
        'cycle', 'dec', 'distinct', 'drop', 'even?', 'filter', 'inc',
        'instance?', 'iterable?', 'iterate', 'iterator?', 'neg?',
        'none?', 'nth', 'numeric?', 'odd?', 'pos?', 'remove', 'repeat',
        'repeatedly', 'take', 'take_nth', 'take_while', 'zero?'
    )

    builtins = hy_builtins + hy_core

    # valid names for identifiers
    # well, names can only not consist fully of numbers
    # but this should be good enough for now
    valid_name = r"[^ \t\n\r\f\v()[\]{};\"'`~]+"

    def _multi_escape(entries):
        return words(entries, suffix=' ')

    tokens = {
        'root': [
            # the comments - always starting with semicolon
            # and going to the end of the line
            (r';.*$', Comment.Single),

            # whitespaces - usually not relevant
            (r'[ \t\n\r\f\v]+', Whitespace),

            # numbers
            (r'-?\d+\.\d+', Number.Float),
            (r'-?\d+', Number.Integer),
            (r'0[0-7]+j?', Number.Oct),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),

            # strings, symbols and characters
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),
            (r"'" + valid_name, String.Symbol),
            (r"\\(.|[a-z]+)", String.Char),
            (r'^(\s*)([rRuU]{,2}"""(?:.|\n)*?""")', bygroups(Text, String.Doc)),
            (r"^(\s*)([rRuU]{,2}'''(?:.|\n)*?''')", bygroups(Text, String.Doc)),

            # keywords
            (r'::?' + valid_name, String.Symbol),

            # special operators
            (r'~@|[`\'#^~&@]', Operator),

            include('py-keywords'),
            include('py-builtins'),

            # highlight the special forms
            (_multi_escape(special_forms), Keyword),

            # Technically, only the special forms are 'keywords'. The problem
            # is that only treating them as keywords means that things like
            # 'defn' and 'ns' need to be highlighted as builtins. This is ugly
            # and weird for most styles. So, as a compromise we're going to
            # highlight them as Keyword.Declarations.
            (_multi_escape(declarations), Keyword.Declaration),

            # highlight the builtins
            (_multi_escape(builtins), Name.Builtin),

            # the remaining functions
            (r'(?<=\()' + valid_name, Name.Function),

            # find the remaining variables
            (valid_name, Name.Variable),

            # Hy accepts vector notation
            (r'(\[|\])', Punctuation),

            # Hy accepts map notation
            (r'(\{|\})', Punctuation),

            # the famous parentheses!
            (r'(\(|\))', Punctuation),

        ],
        'py-keywords': PythonLexer.tokens['keywords'],
        'py-builtins': PythonLexer.tokens['builtins'],
    }

    def analyse_text(text):
        if '(import ' in text or '(defn ' in text:
            return 0.9


class RacketLexer(RegexLexer):
    """
    Lexer for Racket source code (formerly
    known as PLT Scheme).
    """

    name = 'Racket'
    url = 'http://racket-lang.org/'
    aliases = ['racket', 'rkt']
    filenames = ['*.rkt', '*.rktd', '*.rktl']
    mimetypes = ['text/x-racket', 'application/x-racket']
    version_added = '1.6'

    # Generated by example.rkt
    _keywords = (
        '#%app', '#%datum', '#%declare', '#%expression', '#%module-begin',
        '#%plain-app', '#%plain-lambda', '#%plain-module-begin',
        '#%printing-module-begin', '#%provide', '#%require',
        '#%stratified-body', '#%top', '#%top-interaction',
        '#%variable-reference', '->', '->*', '->*m', '->d', '->dm', '->i',
        '->m', '...', ':do-in', '==', '=>', '_', 'absent', 'abstract',
        'all-defined-out', 'all-from-out', 'and', 'any', 'augment', 'augment*',
        'augment-final', 'augment-final*', 'augride', 'augride*', 'begin',
        'begin-for-syntax', 'begin0', 'case', 'case->', 'case->m',
        'case-lambda', 'class', 'class*', 'class-field-accessor',
        'class-field-mutator', 'class/c', 'class/derived', 'combine-in',
        'combine-out', 'command-line', 'compound-unit', 'compound-unit/infer',
        'cond', 'cons/dc', 'contract', 'contract-out', 'contract-struct',
        'contracted', 'define', 'define-compound-unit',
        'define-compound-unit/infer', 'define-contract-struct',
        'define-custom-hash-types', 'define-custom-set-types',
        'define-for-syntax', 'define-local-member-name', 'define-logger',
        'define-match-expander', 'define-member-name',
        'define-module-boundary-contract', 'define-namespace-anchor',
        'define-opt/c', 'define-sequence-syntax', 'define-serializable-class',
        'define-serializable-class*', 'define-signature',
        'define-signature-form', 'define-struct', 'define-struct/contract',
        'define-struct/derived', 'define-syntax', 'define-syntax-rule',
        'define-syntaxes', 'define-unit', 'define-unit-binding',
        'define-unit-from-context', 'define-unit/contract',
        'define-unit/new-import-export', 'define-unit/s', 'define-values',
        'define-values-for-export', 'define-values-for-syntax',
        'define-values/invoke-unit', 'define-values/invoke-unit/infer',
        'define/augment', 'define/augment-final', 'define/augride',
        'define/contract', 'define/final-prop', 'define/match',
        'define/overment', 'define/override', 'define/override-final',
        'define/private', 'define/public', 'define/public-final',
        'define/pubment', 'define/subexpression-pos-prop',
        'define/subexpression-pos-prop/name', 'delay', 'delay/idle',
        'delay/name', 'delay/strict', 'delay/sync', 'delay/thread', 'do',
        'else', 'except', 'except-in', 'except-out', 'export', 'extends',
        'failure-cont', 'false', 'false/c', 'field', 'field-bound?', 'file',
        'flat-murec-contract', 'flat-rec-contract', 'for', 'for*', 'for*/and',
        'for*/async', 'for*/first', 'for*/fold', 'for*/fold/derived',
        'for*/hash', 'for*/hasheq', 'for*/hasheqv', 'for*/last', 'for*/list',
        'for*/lists', 'for*/mutable-set', 'for*/mutable-seteq',
        'for*/mutable-seteqv', 'for*/or', 'for*/product', 'for*/set',
        'for*/seteq', 'for*/seteqv', 'for*/stream', 'for*/sum', 'for*/vector',
        'for*/weak-set', 'for*/weak-seteq', 'for*/weak-seteqv', 'for-label',
        'for-meta', 'for-syntax', 'for-template', 'for/and', 'for/async',
        'for/first', 'for/fold', 'for/fold/derived', 'for/hash', 'for/hasheq',
        'for/hasheqv', 'for/last', 'for/list', 'for/lists', 'for/mutable-set',
        'for/mutable-seteq', 'for/mutable-seteqv', 'for/or', 'for/product',
        'for/set', 'for/seteq', 'for/seteqv', 'for/stream', 'for/sum',
        'for/vector', 'for/weak-set', 'for/weak-seteq', 'for/weak-seteqv',
        'gen:custom-write', 'gen:dict', 'gen:equal+hash', 'gen:set',
        'gen:stream', 'generic', 'get-field', 'hash/dc', 'if', 'implies',
        'import', 'include', 'include-at/relative-to',
        'include-at/relative-to/reader', 'include/reader', 'inherit',
        'inherit-field', 'inherit/inner', 'inherit/super', 'init',
        'init-depend', 'init-field', 'init-rest', 'inner', 'inspect',
        'instantiate', 'interface', 'interface*', 'invariant-assertion',
        'invoke-unit', 'invoke-unit/infer', 'lambda', 'lazy', 'let', 'let*',
        'let*-values', 'let-syntax', 'let-syntaxes', 'let-values', 'let/cc',
        'let/ec', 'letrec', 'letrec-syntax', 'letrec-syntaxes',
        'letrec-syntaxes+values', 'letrec-values', 'lib', 'link', 'local',
        'local-require', 'log-debug', 'log-error', 'log-fatal', 'log-info',
        'log-warning', 'match', 'match*', 'match*/derived', 'match-define',
        'match-define-values', 'match-lambda', 'match-lambda*',
        'match-lambda**', 'match-let', 'match-let*', 'match-let*-values',
        'match-let-values', 'match-letrec', 'match-letrec-values',
        'match/derived', 'match/values', 'member-name-key', 'mixin', 'module',
        'module*', 'module+', 'nand', 'new', 'nor', 'object-contract',
        'object/c', 'only', 'only-in', 'only-meta-in', 'open', 'opt/c', 'or',
        'overment', 'overment*', 'override', 'override*', 'override-final',
        'override-final*', 'parameterize', 'parameterize*',
        'parameterize-break', 'parametric->/c', 'place', 'place*',
        'place/context', 'planet', 'prefix', 'prefix-in', 'prefix-out',
        'private', 'private*', 'prompt-tag/c', 'protect-out', 'provide',
        'provide-signature-elements', 'provide/contract', 'public', 'public*',
        'public-final', 'public-final*', 'pubment', 'pubment*', 'quasiquote',
        'quasisyntax', 'quasisyntax/loc', 'quote', 'quote-syntax',
        'quote-syntax/prune', 'recontract-out', 'recursive-contract',
        'relative-in', 'rename', 'rename-in', 'rename-inner', 'rename-out',
        'rename-super', 'require', 'send', 'send*', 'send+', 'send-generic',
        'send/apply', 'send/keyword-apply', 'set!', 'set!-values',
        'set-field!', 'shared', 'stream', 'stream*', 'stream-cons', 'struct',
        'struct*', 'struct-copy', 'struct-field-index', 'struct-out',
        'struct/c', 'struct/ctc', 'struct/dc', 'submod', 'super',
        'super-instantiate', 'super-make-object', 'super-new', 'syntax',
        'syntax-case', 'syntax-case*', 'syntax-id-rules', 'syntax-rules',
        'syntax/loc', 'tag', 'this', 'this%', 'thunk', 'thunk*', 'time',
        'unconstrained-domain->', 'unit', 'unit-from-context', 'unit/c',
        'unit/new-import-export', 'unit/s', 'unless', 'unquote',
        'unquote-splicing', 'unsyntax', 'unsyntax-splicing', 'values/drop',
        'when', 'with-continuation-mark', 'with-contract',
        'with-contract-continuation-mark', 'with-handlers', 'with-handlers*',
        'with-method', 'with-syntax', 'λ'
    )

    # Generated by example.rkt
    _builtins = (
        '*', '*list/c', '+', '-', '/', '<', '</c', '<=', '<=/c', '=', '=/c',
        '>', '>/c', '>=', '>=/c', 'abort-current-continuation', 'abs',
        'absolute-path?', 'acos', 'add-between', 'add1', 'alarm-evt',
        'always-evt', 'and/c', 'andmap', 'angle', 'any/c', 'append', 'append*',
        'append-map', 'apply', 'argmax', 'argmin', 'arithmetic-shift',
        'arity-at-least', 'arity-at-least-value', 'arity-at-least?',
        'arity-checking-wrapper', 'arity-includes?', 'arity=?',
        'arrow-contract-info', 'arrow-contract-info-accepts-arglist',
        'arrow-contract-info-chaperone-procedure',
        'arrow-contract-info-check-first-order', 'arrow-contract-info?',
        'asin', 'assf', 'assoc', 'assq', 'assv', 'atan',
        'bad-number-of-results', 'banner', 'base->-doms/c', 'base->-rngs/c',
        'base->?', 'between/c', 'bitwise-and', 'bitwise-bit-field',
        'bitwise-bit-set?', 'bitwise-ior', 'bitwise-not', 'bitwise-xor',
        'blame-add-car-context', 'blame-add-cdr-context', 'blame-add-context',
        'blame-add-missing-party', 'blame-add-nth-arg-context',
        'blame-add-range-context', 'blame-add-unknown-context',
        'blame-context', 'blame-contract', 'blame-fmt->-string',
        'blame-missing-party?', 'blame-negative', 'blame-original?',
        'blame-positive', 'blame-replace-negative', 'blame-source',
        'blame-swap', 'blame-swapped?', 'blame-update', 'blame-value',
        'blame?', 'boolean=?', 'boolean?', 'bound-identifier=?', 'box',
        'box-cas!', 'box-immutable', 'box-immutable/c', 'box/c', 'box?',
        'break-enabled', 'break-parameterization?', 'break-thread',
        'build-chaperone-contract-property', 'build-compound-type-name',
        'build-contract-property', 'build-flat-contract-property',
        'build-list', 'build-path', 'build-path/convention-type',
        'build-string', 'build-vector', 'byte-pregexp', 'byte-pregexp?',
        'byte-ready?', 'byte-regexp', 'byte-regexp?', 'byte?', 'bytes',
        'bytes->immutable-bytes', 'bytes->list', 'bytes->path',
        'bytes->path-element', 'bytes->string/latin-1', 'bytes->string/locale',
        'bytes->string/utf-8', 'bytes-append', 'bytes-append*',
        'bytes-close-converter', 'bytes-convert', 'bytes-convert-end',
        'bytes-converter?', 'bytes-copy', 'bytes-copy!',
        'bytes-environment-variable-name?', 'bytes-fill!', 'bytes-join',
        'bytes-length', 'bytes-no-nuls?', 'bytes-open-converter', 'bytes-ref',
        'bytes-set!', 'bytes-utf-8-index', 'bytes-utf-8-length',
        'bytes-utf-8-ref', 'bytes<?', 'bytes=?', 'bytes>?', 'bytes?', 'caaaar',
        'caaadr', 'caaar', 'caadar', 'caaddr', 'caadr', 'caar', 'cadaar',
        'cadadr', 'cadar', 'caddar', 'cadddr', 'caddr', 'cadr',
        'call-in-nested-thread', 'call-with-atomic-output-file',
        'call-with-break-parameterization',
        'call-with-composable-continuation', 'call-with-continuation-barrier',
        'call-with-continuation-prompt', 'call-with-current-continuation',
        'call-with-default-reading-parameterization',
        'call-with-escape-continuation', 'call-with-exception-handler',
        'call-with-file-lock/timeout', 'call-with-immediate-continuation-mark',
        'call-with-input-bytes', 'call-with-input-file',
        'call-with-input-file*', 'call-with-input-string',
        'call-with-output-bytes', 'call-with-output-file',
        'call-with-output-file*', 'call-with-output-string',
        'call-with-parameterization', 'call-with-semaphore',
        'call-with-semaphore/enable-break', 'call-with-values', 'call/cc',
        'call/ec', 'car', 'cartesian-product', 'cdaaar', 'cdaadr', 'cdaar',
        'cdadar', 'cdaddr', 'cdadr', 'cdar', 'cddaar', 'cddadr', 'cddar',
        'cdddar', 'cddddr', 'cdddr', 'cddr', 'cdr', 'ceiling', 'channel-get',
        'channel-put', 'channel-put-evt', 'channel-put-evt?',
        'channel-try-get', 'channel/c', 'channel?', 'chaperone-box',
        'chaperone-channel', 'chaperone-continuation-mark-key',
        'chaperone-contract-property?', 'chaperone-contract?', 'chaperone-evt',
        'chaperone-hash', 'chaperone-hash-set', 'chaperone-of?',
        'chaperone-procedure', 'chaperone-procedure*', 'chaperone-prompt-tag',
        'chaperone-struct', 'chaperone-struct-type', 'chaperone-vector',
        'chaperone?', 'char->integer', 'char-alphabetic?', 'char-blank?',
        'char-ci<=?', 'char-ci<?', 'char-ci=?', 'char-ci>=?', 'char-ci>?',
        'char-downcase', 'char-foldcase', 'char-general-category',
        'char-graphic?', 'char-in', 'char-in/c', 'char-iso-control?',
        'char-lower-case?', 'char-numeric?', 'char-punctuation?',
        'char-ready?', 'char-symbolic?', 'char-title-case?', 'char-titlecase',
        'char-upcase', 'char-upper-case?', 'char-utf-8-length',
        'char-whitespace?', 'char<=?', 'char<?', 'char=?', 'char>=?', 'char>?',
        'char?', 'check-duplicate-identifier', 'check-duplicates',
        'checked-procedure-check-and-extract', 'choice-evt',
        'class->interface', 'class-info', 'class-seal', 'class-unseal',
        'class?', 'cleanse-path', 'close-input-port', 'close-output-port',
        'coerce-chaperone-contract', 'coerce-chaperone-contracts',
        'coerce-contract', 'coerce-contract/f', 'coerce-contracts',
        'coerce-flat-contract', 'coerce-flat-contracts', 'collect-garbage',
        'collection-file-path', 'collection-path', 'combinations', 'compile',
        'compile-allow-set!-undefined', 'compile-context-preservation-enabled',
        'compile-enforce-module-constants', 'compile-syntax',
        'compiled-expression-recompile', 'compiled-expression?',
        'compiled-module-expression?', 'complete-path?', 'complex?', 'compose',
        'compose1', 'conjoin', 'conjugate', 'cons', 'cons/c', 'cons?', 'const',
        'continuation-mark-key/c', 'continuation-mark-key?',
        'continuation-mark-set->context', 'continuation-mark-set->list',
        'continuation-mark-set->list*', 'continuation-mark-set-first',
        'continuation-mark-set?', 'continuation-marks',
        'continuation-prompt-available?', 'continuation-prompt-tag?',
        'continuation?', 'contract-continuation-mark-key',
        'contract-custom-write-property-proc', 'contract-exercise',
        'contract-first-order', 'contract-first-order-passes?',
        'contract-late-neg-projection', 'contract-name', 'contract-proc',
        'contract-projection', 'contract-property?',
        'contract-random-generate', 'contract-random-generate-fail',
        'contract-random-generate-fail?',
        'contract-random-generate-get-current-environment',
        'contract-random-generate-stash', 'contract-random-generate/choose',
        'contract-stronger?', 'contract-struct-exercise',
        'contract-struct-generate', 'contract-struct-late-neg-projection',
        'contract-struct-list-contract?', 'contract-val-first-projection',
        'contract?', 'convert-stream', 'copy-directory/files', 'copy-file',
        'copy-port', 'cos', 'cosh', 'count', 'current-blame-format',
        'current-break-parameterization', 'current-code-inspector',
        'current-command-line-arguments', 'current-compile',
        'current-compiled-file-roots', 'current-continuation-marks',
        'current-contract-region', 'current-custodian', 'current-directory',
        'current-directory-for-user', 'current-drive',
        'current-environment-variables', 'current-error-port', 'current-eval',
        'current-evt-pseudo-random-generator',
        'current-force-delete-permissions', 'current-future',
        'current-gc-milliseconds', 'current-get-interaction-input-port',
        'current-inexact-milliseconds', 'current-input-port',
        'current-inspector', 'current-library-collection-links',
        'current-library-collection-paths', 'current-load',
        'current-load-extension', 'current-load-relative-directory',
        'current-load/use-compiled', 'current-locale', 'current-logger',
        'current-memory-use', 'current-milliseconds',
        'current-module-declare-name', 'current-module-declare-source',
        'current-module-name-resolver', 'current-module-path-for-load',
        'current-namespace', 'current-output-port', 'current-parameterization',
        'current-plumber', 'current-preserved-thread-cell-values',
        'current-print', 'current-process-milliseconds', 'current-prompt-read',
        'current-pseudo-random-generator', 'current-read-interaction',
        'current-reader-guard', 'current-readtable', 'current-seconds',
        'current-security-guard', 'current-subprocess-custodian-mode',
        'current-thread', 'current-thread-group',
        'current-thread-initial-stack-size',
        'current-write-relative-directory', 'curry', 'curryr',
        'custodian-box-value', 'custodian-box?', 'custodian-limit-memory',
        'custodian-managed-list', 'custodian-memory-accounting-available?',
        'custodian-require-memory', 'custodian-shutdown-all', 'custodian?',
        'custom-print-quotable-accessor', 'custom-print-quotable?',
        'custom-write-accessor', 'custom-write-property-proc', 'custom-write?',
        'date', 'date*', 'date*-nanosecond', 'date*-time-zone-name', 'date*?',
        'date-day', 'date-dst?', 'date-hour', 'date-minute', 'date-month',
        'date-second', 'date-time-zone-offset', 'date-week-day', 'date-year',
        'date-year-day', 'date?', 'datum->syntax', 'datum-intern-literal',
        'default-continuation-prompt-tag', 'degrees->radians',
        'delete-directory', 'delete-directory/files', 'delete-file',
        'denominator', 'dict->list', 'dict-can-functional-set?',
        'dict-can-remove-keys?', 'dict-clear', 'dict-clear!', 'dict-copy',
        'dict-count', 'dict-empty?', 'dict-for-each', 'dict-has-key?',
        'dict-implements/c', 'dict-implements?', 'dict-iter-contract',
        'dict-iterate-first', 'dict-iterate-key', 'dict-iterate-next',
        'dict-iterate-value', 'dict-key-contract', 'dict-keys', 'dict-map',
        'dict-mutable?', 'dict-ref', 'dict-ref!', 'dict-remove',
        'dict-remove!', 'dict-set', 'dict-set!', 'dict-set*', 'dict-set*!',
        'dict-update', 'dict-update!', 'dict-value-contract', 'dict-values',
        'dict?', 'directory-exists?', 'directory-list', 'disjoin', 'display',
        'display-lines', 'display-lines-to-file', 'display-to-file',
        'displayln', 'double-flonum?', 'drop', 'drop-common-prefix',
        'drop-right', 'dropf', 'dropf-right', 'dump-memory-stats',
        'dup-input-port', 'dup-output-port', 'dynamic->*', 'dynamic-get-field',
        'dynamic-object/c', 'dynamic-place', 'dynamic-place*',
        'dynamic-require', 'dynamic-require-for-syntax', 'dynamic-send',
        'dynamic-set-field!', 'dynamic-wind', 'eighth', 'empty',
        'empty-sequence', 'empty-stream', 'empty?',
        'environment-variables-copy', 'environment-variables-names',
        'environment-variables-ref', 'environment-variables-set!',
        'environment-variables?', 'eof', 'eof-evt', 'eof-object?',
        'ephemeron-value', 'ephemeron?', 'eprintf', 'eq-contract-val',
        'eq-contract?', 'eq-hash-code', 'eq?', 'equal-contract-val',
        'equal-contract?', 'equal-hash-code', 'equal-secondary-hash-code',
        'equal<%>', 'equal?', 'equal?/recur', 'eqv-hash-code', 'eqv?', 'error',
        'error-display-handler', 'error-escape-handler',
        'error-print-context-length', 'error-print-source-location',
        'error-print-width', 'error-value->string-handler', 'eval',
        'eval-jit-enabled', 'eval-syntax', 'even?', 'evt/c', 'evt?',
        'exact->inexact', 'exact-ceiling', 'exact-floor', 'exact-integer?',
        'exact-nonnegative-integer?', 'exact-positive-integer?', 'exact-round',
        'exact-truncate', 'exact?', 'executable-yield-handler', 'exit',
        'exit-handler', 'exn', 'exn-continuation-marks', 'exn-message',
        'exn:break', 'exn:break-continuation', 'exn:break:hang-up',
        'exn:break:hang-up?', 'exn:break:terminate', 'exn:break:terminate?',
        'exn:break?', 'exn:fail', 'exn:fail:contract',
        'exn:fail:contract:arity', 'exn:fail:contract:arity?',
        'exn:fail:contract:blame', 'exn:fail:contract:blame-object',
        'exn:fail:contract:blame?', 'exn:fail:contract:continuation',
        'exn:fail:contract:continuation?', 'exn:fail:contract:divide-by-zero',
        'exn:fail:contract:divide-by-zero?',
        'exn:fail:contract:non-fixnum-result',
        'exn:fail:contract:non-fixnum-result?', 'exn:fail:contract:variable',
        'exn:fail:contract:variable-id', 'exn:fail:contract:variable?',
        'exn:fail:contract?', 'exn:fail:filesystem',
        'exn:fail:filesystem:errno', 'exn:fail:filesystem:errno-errno',
        'exn:fail:filesystem:errno?', 'exn:fail:filesystem:exists',
        'exn:fail:filesystem:exists?', 'exn:fail:filesystem:missing-module',
        'exn:fail:filesystem:missing-module-path',
        'exn:fail:filesystem:missing-module?', 'exn:fail:filesystem:version',
        'exn:fail:filesystem:version?', 'exn:fail:filesystem?',
        'exn:fail:network', 'exn:fail:network:errno',
        'exn:fail:network:errno-errno', 'exn:fail:network:errno?',
        'exn:fail:network?', 'exn:fail:object', 'exn:fail:object?',
        'exn:fail:out-of-memory', 'exn:fail:out-of-memory?', 'exn:fail:read',
        'exn:fail:read-srclocs', 'exn:fail:read:eof', 'exn:fail:read:eof?',
        'exn:fail:read:non-char', 'exn:fail:read:non-char?', 'exn:fail:read?',
        'exn:fail:syntax', 'exn:fail:syntax-exprs',
        'exn:fail:syntax:missing-module',
        'exn:fail:syntax:missing-module-path',
        'exn:fail:syntax:missing-module?', 'exn:fail:syntax:unbound',
        'exn:fail:syntax:unbound?', 'exn:fail:syntax?', 'exn:fail:unsupported',
        'exn:fail:unsupported?', 'exn:fail:user', 'exn:fail:user?',
        'exn:fail?', 'exn:misc:match?', 'exn:missing-module-accessor',
        'exn:missing-module?', 'exn:srclocs-accessor', 'exn:srclocs?', 'exn?',
        'exp', 'expand', 'expand-once', 'expand-syntax', 'expand-syntax-once',
        'expand-syntax-to-top-form', 'expand-to-top-form', 'expand-user-path',
        'explode-path', 'expt', 'externalizable<%>', 'failure-result/c',
        'false?', 'field-names', 'fifth', 'file->bytes', 'file->bytes-lines',
        'file->lines', 'file->list', 'file->string', 'file->value',
        'file-exists?', 'file-name-from-path', 'file-or-directory-identity',
        'file-or-directory-modify-seconds', 'file-or-directory-permissions',
        'file-position', 'file-position*', 'file-size',
        'file-stream-buffer-mode', 'file-stream-port?', 'file-truncate',
        'filename-extension', 'filesystem-change-evt',
        'filesystem-change-evt-cancel', 'filesystem-change-evt?',
        'filesystem-root-list', 'filter', 'filter-map', 'filter-not',
        'filter-read-input-port', 'find-executable-path', 'find-files',
        'find-library-collection-links', 'find-library-collection-paths',
        'find-relative-path', 'find-system-path', 'findf', 'first',
        'first-or/c', 'fixnum?', 'flat-contract', 'flat-contract-predicate',
        'flat-contract-property?', 'flat-contract?', 'flat-named-contract',
        'flatten', 'floating-point-bytes->real', 'flonum?', 'floor',
        'flush-output', 'fold-files', 'foldl', 'foldr', 'for-each', 'force',
        'format', 'fourth', 'fprintf', 'free-identifier=?',
        'free-label-identifier=?', 'free-template-identifier=?',
        'free-transformer-identifier=?', 'fsemaphore-count', 'fsemaphore-post',
        'fsemaphore-try-wait?', 'fsemaphore-wait', 'fsemaphore?', 'future',
        'future?', 'futures-enabled?', 'gcd', 'generate-member-key',
        'generate-temporaries', 'generic-set?', 'generic?', 'gensym',
        'get-output-bytes', 'get-output-string', 'get-preference',
        'get/build-late-neg-projection', 'get/build-val-first-projection',
        'getenv', 'global-port-print-handler', 'group-by', 'group-execute-bit',
        'group-read-bit', 'group-write-bit', 'guard-evt', 'handle-evt',
        'handle-evt?', 'has-blame?', 'has-contract?', 'hash', 'hash->list',
        'hash-clear', 'hash-clear!', 'hash-copy', 'hash-copy-clear',
        'hash-count', 'hash-empty?', 'hash-eq?', 'hash-equal?', 'hash-eqv?',
        'hash-for-each', 'hash-has-key?', 'hash-iterate-first',
        'hash-iterate-key', 'hash-iterate-key+value', 'hash-iterate-next',
        'hash-iterate-pair', 'hash-iterate-value', 'hash-keys', 'hash-map',
        'hash-placeholder?', 'hash-ref', 'hash-ref!', 'hash-remove',
        'hash-remove!', 'hash-set', 'hash-set!', 'hash-set*', 'hash-set*!',
        'hash-update', 'hash-update!', 'hash-values', 'hash-weak?', 'hash/c',
        'hash?', 'hasheq', 'hasheqv', 'identifier-binding',
        'identifier-binding-symbol', 'identifier-label-binding',
        'identifier-prune-lexical-context',
        'identifier-prune-to-source-module',
        'identifier-remove-from-definition-context',
        'identifier-template-binding', 'identifier-transformer-binding',
        'identifier?', 'identity', 'if/c', 'imag-part', 'immutable?',
        'impersonate-box', 'impersonate-channel',
        'impersonate-continuation-mark-key', 'impersonate-hash',
        'impersonate-hash-set', 'impersonate-procedure',
        'impersonate-procedure*', 'impersonate-prompt-tag',
        'impersonate-struct', 'impersonate-vector', 'impersonator-contract?',
        'impersonator-ephemeron', 'impersonator-of?',
        'impersonator-prop:application-mark', 'impersonator-prop:blame',
        'impersonator-prop:contracted',
        'impersonator-property-accessor-procedure?', 'impersonator-property?',
        'impersonator?', 'implementation?', 'implementation?/c', 'in-bytes',
        'in-bytes-lines', 'in-combinations', 'in-cycle', 'in-dict',
        'in-dict-keys', 'in-dict-pairs', 'in-dict-values', 'in-directory',
        'in-hash', 'in-hash-keys', 'in-hash-pairs', 'in-hash-values',
        'in-immutable-hash', 'in-immutable-hash-keys',
        'in-immutable-hash-pairs', 'in-immutable-hash-values',
        'in-immutable-set', 'in-indexed', 'in-input-port-bytes',
        'in-input-port-chars', 'in-lines', 'in-list', 'in-mlist',
        'in-mutable-hash', 'in-mutable-hash-keys', 'in-mutable-hash-pairs',
        'in-mutable-hash-values', 'in-mutable-set', 'in-naturals',
        'in-parallel', 'in-permutations', 'in-port', 'in-producer', 'in-range',
        'in-sequences', 'in-set', 'in-slice', 'in-stream', 'in-string',
        'in-syntax', 'in-value', 'in-values*-sequence', 'in-values-sequence',
        'in-vector', 'in-weak-hash', 'in-weak-hash-keys', 'in-weak-hash-pairs',
        'in-weak-hash-values', 'in-weak-set', 'inexact->exact',
        'inexact-real?', 'inexact?', 'infinite?', 'input-port-append',
        'input-port?', 'inspector?', 'instanceof/c', 'integer->char',
        'integer->integer-bytes', 'integer-bytes->integer', 'integer-in',
        'integer-length', 'integer-sqrt', 'integer-sqrt/remainder', 'integer?',
        'interface->method-names', 'interface-extension?', 'interface?',
        'internal-definition-context-binding-identifiers',
        'internal-definition-context-introduce',
        'internal-definition-context-seal', 'internal-definition-context?',
        'is-a?', 'is-a?/c', 'keyword->string', 'keyword-apply', 'keyword<?',
        'keyword?', 'keywords-match', 'kill-thread', 'last', 'last-pair',
        'lcm', 'length', 'liberal-define-context?', 'link-exists?', 'list',
        'list*', 'list*of', 'list->bytes', 'list->mutable-set',
        'list->mutable-seteq', 'list->mutable-seteqv', 'list->set',
        'list->seteq', 'list->seteqv', 'list->string', 'list->vector',
        'list->weak-set', 'list->weak-seteq', 'list->weak-seteqv',
        'list-contract?', 'list-prefix?', 'list-ref', 'list-set', 'list-tail',
        'list-update', 'list/c', 'list?', 'listen-port-number?', 'listof',
        'load', 'load-extension', 'load-on-demand-enabled', 'load-relative',
        'load-relative-extension', 'load/cd', 'load/use-compiled',
        'local-expand', 'local-expand/capture-lifts',
        'local-transformer-expand', 'local-transformer-expand/capture-lifts',
        'locale-string-encoding', 'log', 'log-all-levels', 'log-level-evt',
        'log-level?', 'log-max-level', 'log-message', 'log-receiver?',
        'logger-name', 'logger?', 'magnitude', 'make-arity-at-least',
        'make-base-empty-namespace', 'make-base-namespace', 'make-bytes',
        'make-channel', 'make-chaperone-contract',
        'make-continuation-mark-key', 'make-continuation-prompt-tag',
        'make-contract', 'make-custodian', 'make-custodian-box',
        'make-custom-hash', 'make-custom-hash-types', 'make-custom-set',
        'make-custom-set-types', 'make-date', 'make-date*',
        'make-derived-parameter', 'make-directory', 'make-directory*',
        'make-do-sequence', 'make-empty-namespace',
        'make-environment-variables', 'make-ephemeron', 'make-exn',
        'make-exn:break', 'make-exn:break:hang-up', 'make-exn:break:terminate',
        'make-exn:fail', 'make-exn:fail:contract',
        'make-exn:fail:contract:arity', 'make-exn:fail:contract:blame',
        'make-exn:fail:contract:continuation',
        'make-exn:fail:contract:divide-by-zero',
        'make-exn:fail:contract:non-fixnum-result',
        'make-exn:fail:contract:variable', 'make-exn:fail:filesystem',
        'make-exn:fail:filesystem:errno', 'make-exn:fail:filesystem:exists',
        'make-exn:fail:filesystem:missing-module',
        'make-exn:fail:filesystem:version', 'make-exn:fail:network',
        'make-exn:fail:network:errno', 'make-exn:fail:object',
        'make-exn:fail:out-of-memory', 'make-exn:fail:read',
        'make-exn:fail:read:eof', 'make-exn:fail:read:non-char',
        'make-exn:fail:syntax', 'make-exn:fail:syntax:missing-module',
        'make-exn:fail:syntax:unbound', 'make-exn:fail:unsupported',
        'make-exn:fail:user', 'make-file-or-directory-link',
        'make-flat-contract', 'make-fsemaphore', 'make-generic',
        'make-handle-get-preference-locked', 'make-hash',
        'make-hash-placeholder', 'make-hasheq', 'make-hasheq-placeholder',
        'make-hasheqv', 'make-hasheqv-placeholder',
        'make-immutable-custom-hash', 'make-immutable-hash',
        'make-immutable-hasheq', 'make-immutable-hasheqv',
        'make-impersonator-property', 'make-input-port',
        'make-input-port/read-to-peek', 'make-inspector',
        'make-keyword-procedure', 'make-known-char-range-list',
        'make-limited-input-port', 'make-list', 'make-lock-file-name',
        'make-log-receiver', 'make-logger', 'make-mixin-contract',
        'make-mutable-custom-set', 'make-none/c', 'make-object',
        'make-output-port', 'make-parameter', 'make-parent-directory*',
        'make-phantom-bytes', 'make-pipe', 'make-pipe-with-specials',
        'make-placeholder', 'make-plumber', 'make-polar', 'make-prefab-struct',
        'make-primitive-class', 'make-proj-contract',
        'make-pseudo-random-generator', 'make-reader-graph', 'make-readtable',
        'make-rectangular', 'make-rename-transformer',
        'make-resolved-module-path', 'make-security-guard', 'make-semaphore',
        'make-set!-transformer', 'make-shared-bytes', 'make-sibling-inspector',
        'make-special-comment', 'make-srcloc', 'make-string',
        'make-struct-field-accessor', 'make-struct-field-mutator',
        'make-struct-type', 'make-struct-type-property',
        'make-syntax-delta-introducer', 'make-syntax-introducer',
        'make-temporary-file', 'make-tentative-pretty-print-output-port',
        'make-thread-cell', 'make-thread-group', 'make-vector',
        'make-weak-box', 'make-weak-custom-hash', 'make-weak-custom-set',
        'make-weak-hash', 'make-weak-hasheq', 'make-weak-hasheqv',
        'make-will-executor', 'map', 'match-equality-test',
        'matches-arity-exactly?', 'max', 'mcar', 'mcdr', 'mcons', 'member',
        'member-name-key-hash-code', 'member-name-key=?', 'member-name-key?',
        'memf', 'memq', 'memv', 'merge-input', 'method-in-interface?', 'min',
        'mixin-contract', 'module->exports', 'module->imports',
        'module->language-info', 'module->namespace',
        'module-compiled-cross-phase-persistent?', 'module-compiled-exports',
        'module-compiled-imports', 'module-compiled-language-info',
        'module-compiled-name', 'module-compiled-submodules',
        'module-declared?', 'module-path-index-join',
        'module-path-index-resolve', 'module-path-index-split',
        'module-path-index-submodule', 'module-path-index?', 'module-path?',
        'module-predefined?', 'module-provide-protected?', 'modulo', 'mpair?',
        'mutable-set', 'mutable-seteq', 'mutable-seteqv', 'n->th',
        'nack-guard-evt', 'namespace-anchor->empty-namespace',
        'namespace-anchor->namespace', 'namespace-anchor?',
        'namespace-attach-module', 'namespace-attach-module-declaration',
        'namespace-base-phase', 'namespace-mapped-symbols',
        'namespace-module-identifier', 'namespace-module-registry',
        'namespace-require', 'namespace-require/constant',
        'namespace-require/copy', 'namespace-require/expansion-time',
        'namespace-set-variable-value!', 'namespace-symbol->identifier',
        'namespace-syntax-introduce', 'namespace-undefine-variable!',
        'namespace-unprotect-module', 'namespace-variable-value', 'namespace?',
        'nan?', 'natural-number/c', 'negate', 'negative?', 'never-evt',
        'new-∀/c', 'new-∃/c', 'newline', 'ninth', 'non-empty-listof',
        'non-empty-string?', 'none/c', 'normal-case-path', 'normalize-arity',
        'normalize-path', 'normalized-arity?', 'not', 'not/c', 'null', 'null?',
        'number->string', 'number?', 'numerator', 'object%', 'object->vector',
        'object-info', 'object-interface', 'object-method-arity-includes?',
        'object-name', 'object-or-false=?', 'object=?', 'object?', 'odd?',
        'one-of/c', 'open-input-bytes', 'open-input-file',
        'open-input-output-file', 'open-input-string', 'open-output-bytes',
        'open-output-file', 'open-output-nowhere', 'open-output-string',
        'or/c', 'order-of-magnitude', 'ormap', 'other-execute-bit',
        'other-read-bit', 'other-write-bit', 'output-port?', 'pair?',
        'parameter-procedure=?', 'parameter/c', 'parameter?',
        'parameterization?', 'parse-command-line', 'partition', 'path->bytes',
        'path->complete-path', 'path->directory-path', 'path->string',
        'path-add-suffix', 'path-convention-type', 'path-element->bytes',
        'path-element->string', 'path-element?', 'path-for-some-system?',
        'path-list-string->path-list', 'path-only', 'path-replace-suffix',
        'path-string?', 'path<?', 'path?', 'pathlist-closure', 'peek-byte',
        'peek-byte-or-special', 'peek-bytes', 'peek-bytes!', 'peek-bytes!-evt',
        'peek-bytes-avail!', 'peek-bytes-avail!*', 'peek-bytes-avail!-evt',
        'peek-bytes-avail!/enable-break', 'peek-bytes-evt', 'peek-char',
        'peek-char-or-special', 'peek-string', 'peek-string!',
        'peek-string!-evt', 'peek-string-evt', 'peeking-input-port',
        'permutations', 'phantom-bytes?', 'pi', 'pi.f', 'pipe-content-length',
        'place-break', 'place-channel', 'place-channel-get',
        'place-channel-put', 'place-channel-put/get', 'place-channel?',
        'place-dead-evt', 'place-enabled?', 'place-kill', 'place-location?',
        'place-message-allowed?', 'place-sleep', 'place-wait', 'place?',
        'placeholder-get', 'placeholder-set!', 'placeholder?',
        'plumber-add-flush!', 'plumber-flush-all',
        'plumber-flush-handle-remove!', 'plumber-flush-handle?', 'plumber?',
        'poll-guard-evt', 'port->bytes', 'port->bytes-lines', 'port->lines',
        'port->list', 'port->string', 'port-closed-evt', 'port-closed?',
        'port-commit-peeked', 'port-count-lines!', 'port-count-lines-enabled',
        'port-counts-lines?', 'port-display-handler', 'port-file-identity',
        'port-file-unlock', 'port-next-location', 'port-number?',
        'port-print-handler', 'port-progress-evt',
        'port-provides-progress-evts?', 'port-read-handler',
        'port-try-file-lock?', 'port-write-handler', 'port-writes-atomic?',
        'port-writes-special?', 'port?', 'positive?', 'predicate/c',
        'prefab-key->struct-type', 'prefab-key?', 'prefab-struct-key',
        'preferences-lock-file-mode', 'pregexp', 'pregexp?', 'pretty-display',
        'pretty-format', 'pretty-print', 'pretty-print-.-symbol-without-bars',
        'pretty-print-abbreviate-read-macros', 'pretty-print-columns',
        'pretty-print-current-style-table', 'pretty-print-depth',
        'pretty-print-exact-as-decimal', 'pretty-print-extend-style-table',
        'pretty-print-handler', 'pretty-print-newline',
        'pretty-print-post-print-hook', 'pretty-print-pre-print-hook',
        'pretty-print-print-hook', 'pretty-print-print-line',
        'pretty-print-remap-stylable', 'pretty-print-show-inexactness',
        'pretty-print-size-hook', 'pretty-print-style-table?',
        'pretty-printing', 'pretty-write', 'primitive-closure?',
        'primitive-result-arity', 'primitive?', 'print', 'print-as-expression',
        'print-boolean-long-form', 'print-box', 'print-graph',
        'print-hash-table', 'print-mpair-curly-braces',
        'print-pair-curly-braces', 'print-reader-abbreviations',
        'print-struct', 'print-syntax-width', 'print-unreadable',
        'print-vector-length', 'printable/c', 'printable<%>', 'printf',
        'println', 'procedure->method', 'procedure-arity',
        'procedure-arity-includes/c', 'procedure-arity-includes?',
        'procedure-arity?', 'procedure-closure-contents-eq?',
        'procedure-extract-target', 'procedure-keywords',
        'procedure-reduce-arity', 'procedure-reduce-keyword-arity',
        'procedure-rename', 'procedure-result-arity', 'procedure-specialize',
        'procedure-struct-type?', 'procedure?', 'process', 'process*',
        'process*/ports', 'process/ports', 'processor-count', 'progress-evt?',
        'promise-forced?', 'promise-running?', 'promise/c', 'promise/name?',
        'promise?', 'prop:arity-string', 'prop:arrow-contract',
        'prop:arrow-contract-get-info', 'prop:arrow-contract?', 'prop:blame',
        'prop:chaperone-contract', 'prop:checked-procedure', 'prop:contract',
        'prop:contracted', 'prop:custom-print-quotable', 'prop:custom-write',
        'prop:dict', 'prop:dict/contract', 'prop:equal+hash', 'prop:evt',
        'prop:exn:missing-module', 'prop:exn:srclocs',
        'prop:expansion-contexts', 'prop:flat-contract',
        'prop:impersonator-of', 'prop:input-port',
        'prop:liberal-define-context', 'prop:object-name',
        'prop:opt-chaperone-contract', 'prop:opt-chaperone-contract-get-test',
        'prop:opt-chaperone-contract?', 'prop:orc-contract',
        'prop:orc-contract-get-subcontracts', 'prop:orc-contract?',
        'prop:output-port', 'prop:place-location', 'prop:procedure',
        'prop:recursive-contract', 'prop:recursive-contract-unroll',
        'prop:recursive-contract?', 'prop:rename-transformer', 'prop:sequence',
        'prop:set!-transformer', 'prop:stream', 'proper-subset?',
        'pseudo-random-generator->vector', 'pseudo-random-generator-vector?',
        'pseudo-random-generator?', 'put-preferences', 'putenv', 'quotient',
        'quotient/remainder', 'radians->degrees', 'raise',
        'raise-argument-error', 'raise-arguments-error', 'raise-arity-error',
        'raise-blame-error', 'raise-contract-error', 'raise-mismatch-error',
        'raise-not-cons-blame-error', 'raise-range-error',
        'raise-result-error', 'raise-syntax-error', 'raise-type-error',
        'raise-user-error', 'random', 'random-seed', 'range', 'rational?',
        'rationalize', 'read', 'read-accept-bar-quote', 'read-accept-box',
        'read-accept-compiled', 'read-accept-dot', 'read-accept-graph',
        'read-accept-infix-dot', 'read-accept-lang', 'read-accept-quasiquote',
        'read-accept-reader', 'read-byte', 'read-byte-or-special',
        'read-bytes', 'read-bytes!', 'read-bytes!-evt', 'read-bytes-avail!',
        'read-bytes-avail!*', 'read-bytes-avail!-evt',
        'read-bytes-avail!/enable-break', 'read-bytes-evt', 'read-bytes-line',
        'read-bytes-line-evt', 'read-case-sensitive', 'read-cdot', 'read-char',
        'read-char-or-special', 'read-curly-brace-as-paren',
        'read-curly-brace-with-tag', 'read-decimal-as-inexact',
        'read-eval-print-loop', 'read-language', 'read-line', 'read-line-evt',
        'read-on-demand-source', 'read-square-bracket-as-paren',
        'read-square-bracket-with-tag', 'read-string', 'read-string!',
        'read-string!-evt', 'read-string-evt', 'read-syntax',
        'read-syntax/recursive', 'read/recursive', 'readtable-mapping',
        'readtable?', 'real->decimal-string', 'real->double-flonum',
        'real->floating-point-bytes', 'real->single-flonum', 'real-in',
        'real-part', 'real?', 'reencode-input-port', 'reencode-output-port',
        'regexp', 'regexp-match', 'regexp-match*', 'regexp-match-evt',
        'regexp-match-exact?', 'regexp-match-peek',
        'regexp-match-peek-immediate', 'regexp-match-peek-positions',
        'regexp-match-peek-positions*',
        'regexp-match-peek-positions-immediate',
        'regexp-match-peek-positions-immediate/end',
        'regexp-match-peek-positions/end', 'regexp-match-positions',
        'regexp-match-positions*', 'regexp-match-positions/end',
        'regexp-match/end', 'regexp-match?', 'regexp-max-lookbehind',
        'regexp-quote', 'regexp-replace', 'regexp-replace*',
        'regexp-replace-quote', 'regexp-replaces', 'regexp-split',
        'regexp-try-match', 'regexp?', 'relative-path?', 'relocate-input-port',
        'relocate-output-port', 'remainder', 'remf', 'remf*', 'remove',
        'remove*', 'remove-duplicates', 'remq', 'remq*', 'remv', 'remv*',
        'rename-contract', 'rename-file-or-directory',
        'rename-transformer-target', 'rename-transformer?', 'replace-evt',
        'reroot-path', 'resolve-path', 'resolved-module-path-name',
        'resolved-module-path?', 'rest', 'reverse', 'round', 'second',
        'seconds->date', 'security-guard?', 'semaphore-peek-evt',
        'semaphore-peek-evt?', 'semaphore-post', 'semaphore-try-wait?',
        'semaphore-wait', 'semaphore-wait/enable-break', 'semaphore?',
        'sequence->list', 'sequence->stream', 'sequence-add-between',
        'sequence-andmap', 'sequence-append', 'sequence-count',
        'sequence-filter', 'sequence-fold', 'sequence-for-each',
        'sequence-generate', 'sequence-generate*', 'sequence-length',
        'sequence-map', 'sequence-ormap', 'sequence-ref', 'sequence-tail',
        'sequence/c', 'sequence?', 'set', 'set!-transformer-procedure',
        'set!-transformer?', 'set->list', 'set->stream', 'set-add', 'set-add!',
        'set-box!', 'set-clear', 'set-clear!', 'set-copy', 'set-copy-clear',
        'set-count', 'set-empty?', 'set-eq?', 'set-equal?', 'set-eqv?',
        'set-first', 'set-for-each', 'set-implements/c', 'set-implements?',
        'set-intersect', 'set-intersect!', 'set-map', 'set-mcar!', 'set-mcdr!',
        'set-member?', 'set-mutable?', 'set-phantom-bytes!',
        'set-port-next-location!', 'set-remove', 'set-remove!', 'set-rest',
        'set-some-basic-contracts!', 'set-subtract', 'set-subtract!',
        'set-symmetric-difference', 'set-symmetric-difference!', 'set-union',
        'set-union!', 'set-weak?', 'set/c', 'set=?', 'set?', 'seteq', 'seteqv',
        'seventh', 'sgn', 'shared-bytes', 'shell-execute', 'shrink-path-wrt',
        'shuffle', 'simple-form-path', 'simplify-path', 'sin',
        'single-flonum?', 'sinh', 'sixth', 'skip-projection-wrapper?', 'sleep',
        'some-system-path->string', 'sort', 'special-comment-value',
        'special-comment?', 'special-filter-input-port', 'split-at',
        'split-at-right', 'split-common-prefix', 'split-path', 'splitf-at',
        'splitf-at-right', 'sqr', 'sqrt', 'srcloc', 'srcloc->string',
        'srcloc-column', 'srcloc-line', 'srcloc-position', 'srcloc-source',
        'srcloc-span', 'srcloc?', 'stop-after', 'stop-before', 'stream->list',
        'stream-add-between', 'stream-andmap', 'stream-append', 'stream-count',
        'stream-empty?', 'stream-filter', 'stream-first', 'stream-fold',
        'stream-for-each', 'stream-length', 'stream-map', 'stream-ormap',
        'stream-ref', 'stream-rest', 'stream-tail', 'stream/c', 'stream?',
        'string', 'string->bytes/latin-1', 'string->bytes/locale',
        'string->bytes/utf-8', 'string->immutable-string', 'string->keyword',
        'string->list', 'string->number', 'string->path',
        'string->path-element', 'string->some-system-path', 'string->symbol',
        'string->uninterned-symbol', 'string->unreadable-symbol',
        'string-append', 'string-append*', 'string-ci<=?', 'string-ci<?',
        'string-ci=?', 'string-ci>=?', 'string-ci>?', 'string-contains?',
        'string-copy', 'string-copy!', 'string-downcase',
        'string-environment-variable-name?', 'string-fill!', 'string-foldcase',
        'string-join', 'string-len/c', 'string-length', 'string-locale-ci<?',
        'string-locale-ci=?', 'string-locale-ci>?', 'string-locale-downcase',
        'string-locale-upcase', 'string-locale<?', 'string-locale=?',
        'string-locale>?', 'string-no-nuls?', 'string-normalize-nfc',
        'string-normalize-nfd', 'string-normalize-nfkc',
        'string-normalize-nfkd', 'string-normalize-spaces', 'string-port?',
        'string-prefix?', 'string-ref', 'string-replace', 'string-set!',
        'string-split', 'string-suffix?', 'string-titlecase', 'string-trim',
        'string-upcase', 'string-utf-8-length', 'string<=?', 'string<?',
        'string=?', 'string>=?', 'string>?', 'string?', 'struct->vector',
        'struct-accessor-procedure?', 'struct-constructor-procedure?',
        'struct-info', 'struct-mutator-procedure?',
        'struct-predicate-procedure?', 'struct-type-info',
        'struct-type-make-constructor', 'struct-type-make-predicate',
        'struct-type-property-accessor-procedure?', 'struct-type-property/c',
        'struct-type-property?', 'struct-type?', 'struct:arity-at-least',
        'struct:arrow-contract-info', 'struct:date', 'struct:date*',
        'struct:exn', 'struct:exn:break', 'struct:exn:break:hang-up',
        'struct:exn:break:terminate', 'struct:exn:fail',
        'struct:exn:fail:contract', 'struct:exn:fail:contract:arity',
        'struct:exn:fail:contract:blame',
        'struct:exn:fail:contract:continuation',
        'struct:exn:fail:contract:divide-by-zero',
        'struct:exn:fail:contract:non-fixnum-result',
        'struct:exn:fail:contract:variable', 'struct:exn:fail:filesystem',
        'struct:exn:fail:filesystem:errno',
        'struct:exn:fail:filesystem:exists',
        'struct:exn:fail:filesystem:missing-module',
        'struct:exn:fail:filesystem:version', 'struct:exn:fail:network',
        'struct:exn:fail:network:errno', 'struct:exn:fail:object',
        'struct:exn:fail:out-of-memory', 'struct:exn:fail:read',
        'struct:exn:fail:read:eof', 'struct:exn:fail:read:non-char',
        'struct:exn:fail:syntax', 'struct:exn:fail:syntax:missing-module',
        'struct:exn:fail:syntax:unbound', 'struct:exn:fail:unsupported',
        'struct:exn:fail:user', 'struct:srcloc',
        'struct:wrapped-extra-arg-arrow', 'struct?', 'sub1', 'subbytes',
        'subclass?', 'subclass?/c', 'subprocess', 'subprocess-group-enabled',
        'subprocess-kill', 'subprocess-pid', 'subprocess-status',
        'subprocess-wait', 'subprocess?', 'subset?', 'substring', 'suggest/c',
        'symbol->string', 'symbol-interned?', 'symbol-unreadable?', 'symbol<?',
        'symbol=?', 'symbol?', 'symbols', 'sync', 'sync/enable-break',
        'sync/timeout', 'sync/timeout/enable-break', 'syntax->datum',
        'syntax->list', 'syntax-arm', 'syntax-column', 'syntax-debug-info',
        'syntax-disarm', 'syntax-e', 'syntax-line',
        'syntax-local-bind-syntaxes', 'syntax-local-certifier',
        'syntax-local-context', 'syntax-local-expand-expression',
        'syntax-local-get-shadower', 'syntax-local-identifier-as-binding',
        'syntax-local-introduce', 'syntax-local-lift-context',
        'syntax-local-lift-expression', 'syntax-local-lift-module',
        'syntax-local-lift-module-end-declaration',
        'syntax-local-lift-provide', 'syntax-local-lift-require',
        'syntax-local-lift-values-expression',
        'syntax-local-make-definition-context',
        'syntax-local-make-delta-introducer',
        'syntax-local-module-defined-identifiers',
        'syntax-local-module-exports',
        'syntax-local-module-required-identifiers', 'syntax-local-name',
        'syntax-local-phase-level', 'syntax-local-submodules',
        'syntax-local-transforming-module-provides?', 'syntax-local-value',
        'syntax-local-value/immediate', 'syntax-original?', 'syntax-position',
        'syntax-property', 'syntax-property-preserved?',
        'syntax-property-symbol-keys', 'syntax-protect', 'syntax-rearm',
        'syntax-recertify', 'syntax-shift-phase-level', 'syntax-source',
        'syntax-source-module', 'syntax-span', 'syntax-taint',
        'syntax-tainted?', 'syntax-track-origin',
        'syntax-transforming-module-expression?',
        'syntax-transforming-with-lifts?', 'syntax-transforming?', 'syntax/c',
        'syntax?', 'system', 'system*', 'system*/exit-code',
        'system-big-endian?', 'system-idle-evt', 'system-language+country',
        'system-library-subpath', 'system-path-convention-type', 'system-type',
        'system/exit-code', 'tail-marks-match?', 'take', 'take-common-prefix',
        'take-right', 'takef', 'takef-right', 'tan', 'tanh',
        'tcp-abandon-port', 'tcp-accept', 'tcp-accept-evt',
        'tcp-accept-ready?', 'tcp-accept/enable-break', 'tcp-addresses',
        'tcp-close', 'tcp-connect', 'tcp-connect/enable-break', 'tcp-listen',
        'tcp-listener?', 'tcp-port?', 'tentative-pretty-print-port-cancel',
        'tentative-pretty-print-port-transfer', 'tenth', 'terminal-port?',
        'the-unsupplied-arg', 'third', 'thread', 'thread-cell-ref',
        'thread-cell-set!', 'thread-cell-values?', 'thread-cell?',
        'thread-dead-evt', 'thread-dead?', 'thread-group?', 'thread-receive',
        'thread-receive-evt', 'thread-resume', 'thread-resume-evt',
        'thread-rewind-receive', 'thread-running?', 'thread-send',
        'thread-suspend', 'thread-suspend-evt', 'thread-try-receive',
        'thread-wait', 'thread/suspend-to-kill', 'thread?', 'time-apply',
        'touch', 'transplant-input-port', 'transplant-output-port', 'true',
        'truncate', 'udp-addresses', 'udp-bind!', 'udp-bound?', 'udp-close',
        'udp-connect!', 'udp-connected?', 'udp-multicast-interface',
        'udp-multicast-join-group!', 'udp-multicast-leave-group!',
        'udp-multicast-loopback?', 'udp-multicast-set-interface!',
        'udp-multicast-set-loopback!', 'udp-multicast-set-ttl!',
        'udp-multicast-ttl', 'udp-open-socket', 'udp-receive!',
        'udp-receive!*', 'udp-receive!-evt', 'udp-receive!/enable-break',
        'udp-receive-ready-evt', 'udp-send', 'udp-send*', 'udp-send-evt',
        'udp-send-ready-evt', 'udp-send-to', 'udp-send-to*', 'udp-send-to-evt',
        'udp-send-to/enable-break', 'udp-send/enable-break', 'udp?', 'unbox',
        'uncaught-exception-handler', 'unit?', 'unspecified-dom',
        'unsupplied-arg?', 'use-collection-link-paths',
        'use-compiled-file-paths', 'use-user-specific-search-paths',
        'user-execute-bit', 'user-read-bit', 'user-write-bit', 'value-blame',
        'value-contract', 'values', 'variable-reference->empty-namespace',
        'variable-reference->module-base-phase',
        'variable-reference->module-declaration-inspector',
        'variable-reference->module-path-index',
        'variable-reference->module-source', 'variable-reference->namespace',
        'variable-reference->phase',
        'variable-reference->resolved-module-path',
        'variable-reference-constant?', 'variable-reference?', 'vector',
        'vector->immutable-vector', 'vector->list',
        'vector->pseudo-random-generator', 'vector->pseudo-random-generator!',
        'vector->values', 'vector-append', 'vector-argmax', 'vector-argmin',
        'vector-copy', 'vector-copy!', 'vector-count', 'vector-drop',
        'vector-drop-right', 'vector-fill!', 'vector-filter',
        'vector-filter-not', 'vector-immutable', 'vector-immutable/c',
        'vector-immutableof', 'vector-length', 'vector-map', 'vector-map!',
        'vector-member', 'vector-memq', 'vector-memv', 'vector-ref',
        'vector-set!', 'vector-set*!', 'vector-set-performance-stats!',
        'vector-split-at', 'vector-split-at-right', 'vector-take',
        'vector-take-right', 'vector/c', 'vector?', 'vectorof', 'version',
        'void', 'void?', 'weak-box-value', 'weak-box?', 'weak-set',
        'weak-seteq', 'weak-seteqv', 'will-execute', 'will-executor?',
        'will-register', 'will-try-execute', 'with-input-from-bytes',
        'with-input-from-file', 'with-input-from-string',
        'with-output-to-bytes', 'with-output-to-file', 'with-output-to-string',
        'would-be-future', 'wrap-evt', 'wrapped-extra-arg-arrow',
        'wrapped-extra-arg-arrow-extra-neg-party-argument',
        'wrapped-extra-arg-arrow-real-func', 'wrapped-extra-arg-arrow?',
        'writable<%>', 'write', 'write-byte', 'write-bytes',
        'write-bytes-avail', 'write-bytes-avail*', 'write-bytes-avail-evt',
        'write-bytes-avail/enable-break', 'write-char', 'write-special',
        'write-special-avail*', 'write-special-evt', 'write-string',
        'write-to-file', 'writeln', 'xor', 'zero?', '~.a', '~.s', '~.v', '~a',
        '~e', '~r', '~s', '~v'
    )

    _opening_parenthesis = r'[([{]'
    _closing_parenthesis = r'[)\]}]'
    _delimiters = r'()[\]{}",\'`;\s'
    _symbol = rf'(?:\|[^|]*\||\\[\w\W]|[^|\\{_delimiters}]+)+'
    _exact_decimal_prefix = r'(?:#e)?(?:#d)?(?:#e)?'
    _exponent = r'(?:[defls][-+]?\d+)'
    _inexact_simple_no_hashes = r'(?:\d+(?:/\d+|\.\d*)?|\.\d+)'
    _inexact_simple = (rf'(?:{_inexact_simple_no_hashes}|(?:\d+#+(?:\.#*|/\d+#*)?|\.\d+#+|'
                       r'\d+(?:\.\d*#+|/\d+#+)))')
    _inexact_normal_no_hashes = rf'(?:{_inexact_simple_no_hashes}{_exponent}?)'
    _inexact_normal = rf'(?:{_inexact_simple}{_exponent}?)'
    _inexact_special = r'(?:(?:inf|nan)\.[0f])'
    _inexact_real = rf'(?:[-+]?{_inexact_normal}|[-+]{_inexact_special})'
    _inexact_unsigned = rf'(?:{_inexact_normal}|{_inexact_special})'

    tokens = {
        'root': [
            (_closing_parenthesis, Error),
            (r'(?!\Z)', Text, 'unquoted-datum')
        ],
        'datum': [
            (r'(?s)#;|#![ /]([^\\\n]|\\.)*', Comment),
            (r';[^\n\r\x85\u2028\u2029]*', Comment.Single),
            (r'#\|', Comment.Multiline, 'block-comment'),

            # Whitespaces
            (r'(?u)\s+', Whitespace),

            # Numbers: Keep in mind Racket reader hash prefixes, which
            # can denote the base or the type. These don't map neatly
            # onto Pygments token types; some judgment calls here.

            # #d or no prefix
            (rf'(?i){_exact_decimal_prefix}[-+]?\d+(?=[{_delimiters}])',
             Number.Integer, '#pop'),
            (rf'(?i){_exact_decimal_prefix}[-+]?(\d+(\.\d*)?|\.\d+)([deflst][-+]?\d+)?(?=[{_delimiters}])', Number.Float, '#pop'),
            (rf'(?i){_exact_decimal_prefix}[-+]?({_inexact_normal_no_hashes}([-+]{_inexact_normal_no_hashes}?i)?|[-+]{_inexact_normal_no_hashes}?i)(?=[{_delimiters}])', Number, '#pop'),

            # Inexact without explicit #i
            (rf'(?i)(#d)?({_inexact_real}([-+]{_inexact_unsigned}?i)?|[-+]{_inexact_unsigned}?i|{_inexact_real}@{_inexact_real})(?=[{_delimiters}])', Number.Float,
             '#pop'),

            # The remaining extflonums
            (rf'(?i)(([-+]?{_inexact_simple}t[-+]?\d+)|[-+](inf|nan)\.t)(?=[{_delimiters}])', Number.Float, '#pop'),

            # #b
            (rf'(?iu)(#[ei])?#b{_symbol}', Number.Bin, '#pop'),

            # #o
            (rf'(?iu)(#[ei])?#o{_symbol}', Number.Oct, '#pop'),

            # #x
            (rf'(?iu)(#[ei])?#x{_symbol}', Number.Hex, '#pop'),

            # #i is always inexact, i.e. float
            (rf'(?iu)(#d)?#i{_symbol}', Number.Float, '#pop'),

            # Strings and characters
            (r'#?"', String.Double, ('#pop', 'string')),
            (r'#<<(.+)\n(^(?!\1$).*$\n)*^\1$', String.Heredoc, '#pop'),
            (r'#\\(u[\da-fA-F]{1,4}|U[\da-fA-F]{1,8})', String.Char, '#pop'),
            (r'(?is)#\\([0-7]{3}|[a-z]+|.)', String.Char, '#pop'),
            (r'(?s)#[pr]x#?"(\\?.)*?"', String.Regex, '#pop'),

            # Constants
            (r'#(true|false|[tTfF])', Name.Constant, '#pop'),

            # Keyword argument names (e.g. #:keyword)
            (rf'#:{_symbol}', Keyword.Declaration, '#pop'),

            # Reader extensions
            (r'(#lang |#!)(\S+)',
             bygroups(Keyword.Namespace, Name.Namespace)),
            (r'#reader', Keyword.Namespace, 'quoted-datum'),

            # Other syntax
            (rf"(?i)\.(?=[{_delimiters}])|#c[is]|#['`]|#,@?", Operator),
            (rf"'|#[s&]|#hash(eqv?)?|#\d*(?={_opening_parenthesis})",
             Operator, ('#pop', 'quoted-datum'))
        ],
        'datum*': [
            (r'`|,@?', Operator),
            (_symbol, String.Symbol, '#pop'),
            (r'[|\\]', Error),
            default('#pop')
        ],
        'list': [
            (_closing_parenthesis, Punctuation, '#pop')
        ],
        'unquoted-datum': [
            include('datum'),
            (rf'quote(?=[{_delimiters}])', Keyword,
             ('#pop', 'quoted-datum')),
            (r'`', Operator, ('#pop', 'quasiquoted-datum')),
            (rf'quasiquote(?=[{_delimiters}])', Keyword,
             ('#pop', 'quasiquoted-datum')),
            (_opening_parenthesis, Punctuation, ('#pop', 'unquoted-list')),
            (words(_keywords, suffix=f'(?=[{_delimiters}])'),
             Keyword, '#pop'),
            (words(_builtins, suffix=f'(?=[{_delimiters}])'),
             Name.Builtin, '#pop'),
            (_symbol, Name, '#pop'),
            include('datum*')
        ],
        'unquoted-list': [
            include('list'),
            (r'(?!\Z)', Text, 'unquoted-datum')
        ],
        'quasiquoted-datum': [
            include('datum'),
            (r',@?', Operator, ('#pop', 'unquoted-datum')),
            (rf'unquote(-splicing)?(?=[{_delimiters}])', Keyword,
             ('#pop', 'unquoted-datum')),
            (_opening_parenthesis, Punctuation, ('#pop', 'quasiquoted-list')),
            include('datum*')
        ],
        'quasiquoted-list': [
            include('list'),
            (r'(?!\Z)', Text, 'quasiquoted-datum')
        ],
        'quoted-datum': [
            include('datum'),
            (_opening_parenthesis, Punctuation, ('#pop', 'quoted-list')),
            include('datum*')
        ],
        'quoted-list': [
            include('list'),
            (r'(?!\Z)', Text, 'quoted-datum')
        ],
        'block-comment': [
            (r'#\|', Comment.Multiline, '#push'),
            (r'\|#', Comment.Multiline, '#pop'),
            (r'[^#|]+|.', Comment.Multiline)
        ],
        'string': [
            (r'"', String.Double, '#pop'),
            (r'(?s)\\([0-7]{1,3}|x[\da-fA-F]{1,2}|u[\da-fA-F]{1,4}|'
             r'U[\da-fA-F]{1,8}|.)', String.Escape),
            (r'[^\\"]+', String.Double)
        ]
    }


class NewLispLexer(RegexLexer):
    """
    For newLISP source code (version 10.3.0).
    """

    name = 'NewLisp'
    url = 'http://www.newlisp.org/'
    aliases = ['newlisp']
    filenames = ['*.lsp', '*.nl', '*.kif']
    mimetypes = ['text/x-newlisp', 'application/x-newlisp']
    version_added = '1.5'

    flags = re.IGNORECASE | re.MULTILINE

    # list of built-in functions for newLISP version 10.3
    builtins = (
        '^', '--', '-', ':', '!', '!=', '?', '@', '*', '/', '&', '%', '+', '++',
        '<', '<<', '<=', '=', '>', '>=', '>>', '|', '~', '$', '$0', '$1', '$10',
        '$11', '$12', '$13', '$14', '$15', '$2', '$3', '$4', '$5', '$6', '$7',
        '$8', '$9', '$args', '$idx', '$it', '$main-args', 'abort', 'abs',
        'acos', 'acosh', 'add', 'address', 'amb', 'and',  'append-file',
        'append', 'apply', 'args', 'array-list', 'array?', 'array', 'asin',
        'asinh', 'assoc', 'atan', 'atan2', 'atanh', 'atom?', 'base64-dec',
        'base64-enc', 'bayes-query', 'bayes-train', 'begin',
        'beta', 'betai', 'bind', 'binomial', 'bits', 'callback',
        'case', 'catch', 'ceil', 'change-dir', 'char', 'chop', 'Class', 'clean',
        'close', 'command-event', 'cond', 'cons', 'constant',
        'context?', 'context', 'copy-file', 'copy', 'cos', 'cosh', 'count',
        'cpymem', 'crc32', 'crit-chi2', 'crit-z', 'current-line', 'curry',
        'date-list', 'date-parse', 'date-value', 'date', 'debug', 'dec',
        'def-new', 'default', 'define-macro', 'define',
        'delete-file', 'delete-url', 'delete', 'destroy', 'det', 'device',
        'difference', 'directory?', 'directory', 'div', 'do-until', 'do-while',
        'doargs',  'dolist',  'dostring', 'dotimes',  'dotree', 'dump', 'dup',
        'empty?', 'encrypt', 'ends-with', 'env', 'erf', 'error-event',
        'eval-string', 'eval', 'exec', 'exists', 'exit', 'exp', 'expand',
        'explode', 'extend', 'factor', 'fft', 'file-info', 'file?', 'filter',
        'find-all', 'find', 'first', 'flat', 'float?', 'float', 'floor', 'flt',
        'fn', 'for-all', 'for', 'fork', 'format', 'fv', 'gammai', 'gammaln',
        'gcd', 'get-char', 'get-float', 'get-int', 'get-long', 'get-string',
        'get-url', 'global?', 'global', 'if-not', 'if', 'ifft', 'import', 'inc',
        'index', 'inf?', 'int', 'integer?', 'integer', 'intersect', 'invert',
        'irr', 'join', 'lambda-macro', 'lambda?', 'lambda', 'last-error',
        'last', 'legal?', 'length', 'let', 'letex', 'letn',
        'list?', 'list', 'load', 'local', 'log', 'lookup',
        'lower-case', 'macro?', 'main-args', 'MAIN', 'make-dir', 'map', 'mat',
        'match', 'max', 'member', 'min', 'mod', 'module', 'mul', 'multiply',
        'NaN?', 'net-accept', 'net-close', 'net-connect', 'net-error',
        'net-eval', 'net-interface', 'net-ipv', 'net-listen', 'net-local',
        'net-lookup', 'net-packet', 'net-peek', 'net-peer', 'net-ping',
        'net-receive-from', 'net-receive-udp', 'net-receive', 'net-select',
        'net-send-to', 'net-send-udp', 'net-send', 'net-service',
        'net-sessions', 'new', 'nil?', 'nil', 'normal', 'not', 'now', 'nper',
        'npv', 'nth', 'null?', 'number?', 'open', 'or', 'ostype', 'pack',
        'parse-date', 'parse', 'peek', 'pipe', 'pmt', 'pop-assoc', 'pop',
        'post-url', 'pow', 'prefix', 'pretty-print', 'primitive?', 'print',
        'println', 'prob-chi2', 'prob-z', 'process', 'prompt-event',
        'protected?', 'push', 'put-url', 'pv', 'quote?', 'quote', 'rand',
        'random', 'randomize', 'read', 'read-char', 'read-expr', 'read-file',
        'read-key', 'read-line', 'read-utf8', 'reader-event',
        'real-path', 'receive', 'ref-all', 'ref', 'regex-comp', 'regex',
        'remove-dir', 'rename-file', 'replace', 'reset', 'rest', 'reverse',
        'rotate', 'round', 'save', 'search', 'seed', 'seek', 'select', 'self',
        'semaphore', 'send', 'sequence', 'series', 'set-locale', 'set-ref-all',
        'set-ref', 'set', 'setf',  'setq', 'sgn', 'share', 'signal', 'silent',
        'sin', 'sinh', 'sleep', 'slice', 'sort', 'source', 'spawn', 'sqrt',
        'starts-with', 'string?', 'string', 'sub', 'swap', 'sym', 'symbol?',
        'symbols', 'sync', 'sys-error', 'sys-info', 'tan', 'tanh', 'term',
        'throw-error', 'throw', 'time-of-day', 'time', 'timer', 'title-case',
        'trace-highlight', 'trace', 'transpose', 'Tree', 'trim', 'true?',
        'true', 'unicode', 'unify', 'unique', 'unless', 'unpack', 'until',
        'upper-case', 'utf8', 'utf8len', 'uuid', 'wait-pid', 'when', 'while',
        'write', 'write-char', 'write-file', 'write-line',
        'xfer-event', 'xml-error', 'xml-parse', 'xml-type-tags', 'zero?',
    )

    # valid names
    valid_name = r'([\w!$%&*+.,/<=>?@^~|-])+|(\[.*?\])+'

    tokens = {
        'root': [
            # shebang
            (r'#!(.*?)$', Comment.Preproc),
            # comments starting with semicolon
            (r';.*$', Comment.Single),
            # comments starting with #
            (r'#.*$', Comment.Single),

            # whitespace
            (r'\s+', Whitespace),

            # strings, symbols and characters
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),

            # braces
            (r'\{', String, "bracestring"),

            # [text] ... [/text] delimited strings
            (r'\[text\]*', String, "tagstring"),

            # 'special' operators...
            (r"('|:)", Operator),

            # highlight the builtins
            (words(builtins, suffix=r'\b'),
             Keyword),

            # the remaining functions
            (r'(?<=\()' + valid_name, Name.Variable),

            # the remaining variables
            (valid_name, String.Symbol),

            # parentheses
            (r'(\(|\))', Punctuation),
        ],

        # braced strings...
        'bracestring': [
            (r'\{', String, "#push"),
            (r'\}', String, "#pop"),
            ('[^{}]+', String),
        ],

        # tagged [text]...[/text] delimited strings...
        'tagstring': [
            (r'(?s)(.*?)(\[/text\])', String, '#pop'),
        ],
    }


class EmacsLispLexer(RegexLexer):
    """
    An ELisp lexer, parsing a stream and outputting the tokens
    needed to highlight elisp code.
    """
    name = 'EmacsLisp'
    aliases = ['emacs-lisp', 'elisp', 'emacs']
    filenames = ['*.el']
    mimetypes = ['text/x-elisp', 'application/x-elisp']
    url = 'https://www.gnu.org/software/emacs'
    version_added = '2.1'

    flags = re.MULTILINE

    # couple of useful regexes

    # characters that are not macro-characters and can be used to begin a symbol
    nonmacro = r'\\.|[\w!$%&*+-/<=>?@^{}~|]'
    constituent = nonmacro + '|[#.:]'
    terminated = r'(?=[ "()\]\'\n,;`])'  # whitespace or terminating macro characters

    # symbol token, reverse-engineered from hyperspec
    # Take a deep breath...
    symbol = rf'((?:{nonmacro})(?:{constituent})*)'

    macros = {
        'atomic-change-group', 'case', 'block', 'cl-block', 'cl-callf', 'cl-callf2',
        'cl-case', 'cl-decf', 'cl-declaim', 'cl-declare',
        'cl-define-compiler-macro', 'cl-defmacro', 'cl-defstruct',
        'cl-defsubst', 'cl-deftype', 'cl-defun', 'cl-destructuring-bind',
        'cl-do', 'cl-do*', 'cl-do-all-symbols', 'cl-do-symbols', 'cl-dolist',
        'cl-dotimes', 'cl-ecase', 'cl-etypecase', 'eval-when', 'cl-eval-when', 'cl-flet',
        'cl-flet*', 'cl-function', 'cl-incf', 'cl-labels', 'cl-letf',
        'cl-letf*', 'cl-load-time-value', 'cl-locally', 'cl-loop',
        'cl-macrolet', 'cl-multiple-value-bind', 'cl-multiple-value-setq',
        'cl-progv', 'cl-psetf', 'cl-psetq', 'cl-pushnew', 'cl-remf',
        'cl-return', 'cl-return-from', 'cl-rotatef', 'cl-shiftf',
        'cl-symbol-macrolet', 'cl-tagbody', 'cl-the', 'cl-typecase',
        'combine-after-change-calls', 'condition-case-unless-debug', 'decf',
        'declaim', 'declare', 'declare-function', 'def-edebug-spec',
        'defadvice', 'defclass', 'defcustom', 'defface', 'defgeneric',
        'defgroup', 'define-advice', 'define-alternatives',
        'define-compiler-macro', 'define-derived-mode', 'define-generic-mode',
        'define-global-minor-mode', 'define-globalized-minor-mode',
        'define-minor-mode', 'define-modify-macro',
        'define-obsolete-face-alias', 'define-obsolete-function-alias',
        'define-obsolete-variable-alias', 'define-setf-expander',
        'define-skeleton', 'defmacro', 'defmethod', 'defsetf', 'defstruct',
        'defsubst', 'deftheme', 'deftype', 'defun', 'defvar-local',
        'delay-mode-hooks', 'destructuring-bind', 'do', 'do*',
        'do-all-symbols', 'do-symbols', 'dolist', 'dont-compile', 'dotimes',
        'dotimes-with-progress-reporter', 'ecase', 'ert-deftest', 'etypecase',
        'eval-and-compile', 'eval-when-compile', 'flet', 'ignore-errors',
        'incf', 'labels', 'lambda', 'letrec', 'lexical-let', 'lexical-let*',
        'loop', 'multiple-value-bind', 'multiple-value-setq', 'noreturn',
        'oref', 'oref-default', 'oset', 'oset-default', 'pcase',
        'pcase-defmacro', 'pcase-dolist', 'pcase-exhaustive', 'pcase-let',
        'pcase-let*', 'pop', 'psetf', 'psetq', 'push', 'pushnew', 'remf',
        'return', 'rotatef', 'rx', 'save-match-data', 'save-selected-window',
        'save-window-excursion', 'setf', 'setq-local', 'shiftf',
        'track-mouse', 'typecase', 'unless', 'use-package', 'when',
        'while-no-input', 'with-case-table', 'with-category-table',
        'with-coding-priority', 'with-current-buffer', 'with-demoted-errors',
        'with-eval-after-load', 'with-file-modes', 'with-local-quit',
        'with-output-to-string', 'with-output-to-temp-buffer',
        'with-parsed-tramp-file-name', 'with-selected-frame',
        'with-selected-window', 'with-silent-modifications', 'with-slots',
        'with-syntax-table', 'with-temp-buffer', 'with-temp-file',
        'with-temp-message', 'with-timeout', 'with-tramp-connection-property',
        'with-tramp-file-property', 'with-tramp-progress-reporter',
        'with-wrapper-hook', 'load-time-value', 'locally', 'macrolet', 'progv',
        'return-from',
    }

    special_forms = {
        'and', 'catch', 'cond', 'condition-case', 'defconst', 'defvar',
        'function', 'if', 'interactive', 'let', 'let*', 'or', 'prog1',
        'prog2', 'progn', 'quote', 'save-current-buffer', 'save-excursion',
        'save-restriction', 'setq', 'setq-default', 'subr-arity',
        'unwind-protect', 'while',
    }

    builtin_function = {
        '%', '*', '+', '-', '/', '/=', '1+', '1-', '<', '<=', '=', '>', '>=',
        'Snarf-documentation', 'abort-recursive-edit', 'abs',
        'accept-process-output', 'access-file', 'accessible-keymaps', 'acos',
        'active-minibuffer-window', 'add-face-text-property',
        'add-name-to-file', 'add-text-properties', 'all-completions',
        'append', 'apply', 'apropos-internal', 'aref', 'arrayp', 'aset',
        'ash', 'asin', 'assoc', 'assoc-string', 'assq', 'atan', 'atom',
        'autoload', 'autoload-do-load', 'backtrace', 'backtrace--locals',
        'backtrace-debug', 'backtrace-eval', 'backtrace-frame',
        'backward-char', 'backward-prefix-chars', 'barf-if-buffer-read-only',
        'base64-decode-region', 'base64-decode-string',
        'base64-encode-region', 'base64-encode-string', 'beginning-of-line',
        'bidi-find-overridden-directionality', 'bidi-resolved-levels',
        'bitmap-spec-p', 'bobp', 'bolp', 'bool-vector',
        'bool-vector-count-consecutive', 'bool-vector-count-population',
        'bool-vector-exclusive-or', 'bool-vector-intersection',
        'bool-vector-not', 'bool-vector-p', 'bool-vector-set-difference',
        'bool-vector-subsetp', 'bool-vector-union', 'boundp',
        'buffer-base-buffer', 'buffer-chars-modified-tick',
        'buffer-enable-undo', 'buffer-file-name', 'buffer-has-markers-at',
        'buffer-list', 'buffer-live-p', 'buffer-local-value',
        'buffer-local-variables', 'buffer-modified-p', 'buffer-modified-tick',
        'buffer-name', 'buffer-size', 'buffer-string', 'buffer-substring',
        'buffer-substring-no-properties', 'buffer-swap-text', 'bufferp',
        'bury-buffer-internal', 'byte-code', 'byte-code-function-p',
        'byte-to-position', 'byte-to-string', 'byteorder',
        'call-interactively', 'call-last-kbd-macro', 'call-process',
        'call-process-region', 'cancel-kbd-macro-events', 'capitalize',
        'capitalize-region', 'capitalize-word', 'car', 'car-less-than-car',
        'car-safe', 'case-table-p', 'category-docstring',
        'category-set-mnemonics', 'category-table', 'category-table-p',
        'ccl-execute', 'ccl-execute-on-string', 'ccl-program-p', 'cdr',
        'cdr-safe', 'ceiling', 'char-after', 'char-before',
        'char-category-set', 'char-charset', 'char-equal', 'char-or-string-p',
        'char-resolve-modifiers', 'char-syntax', 'char-table-extra-slot',
        'char-table-p', 'char-table-parent', 'char-table-range',
        'char-table-subtype', 'char-to-string', 'char-width', 'characterp',
        'charset-after', 'charset-id-internal', 'charset-plist',
        'charset-priority-list', 'charsetp', 'check-coding-system',
        'check-coding-systems-region', 'clear-buffer-auto-save-failure',
        'clear-charset-maps', 'clear-face-cache', 'clear-font-cache',
        'clear-image-cache', 'clear-string', 'clear-this-command-keys',
        'close-font', 'clrhash', 'coding-system-aliases',
        'coding-system-base', 'coding-system-eol-type', 'coding-system-p',
        'coding-system-plist', 'coding-system-priority-list',
        'coding-system-put', 'color-distance', 'color-gray-p',
        'color-supported-p', 'combine-after-change-execute',
        'command-error-default-function', 'command-remapping', 'commandp',
        'compare-buffer-substrings', 'compare-strings',
        'compare-window-configurations', 'completing-read',
        'compose-region-internal', 'compose-string-internal',
        'composition-get-gstring', 'compute-motion', 'concat', 'cons',
        'consp', 'constrain-to-field', 'continue-process',
        'controlling-tty-p', 'coordinates-in-window-p', 'copy-alist',
        'copy-category-table', 'copy-file', 'copy-hash-table', 'copy-keymap',
        'copy-marker', 'copy-sequence', 'copy-syntax-table', 'copysign',
        'cos', 'current-active-maps', 'current-bidi-paragraph-direction',
        'current-buffer', 'current-case-table', 'current-column',
        'current-global-map', 'current-idle-time', 'current-indentation',
        'current-input-mode', 'current-local-map', 'current-message',
        'current-minor-mode-maps', 'current-time', 'current-time-string',
        'current-time-zone', 'current-window-configuration',
        'cygwin-convert-file-name-from-windows',
        'cygwin-convert-file-name-to-windows', 'daemon-initialized',
        'daemonp', 'dbus--init-bus', 'dbus-get-unique-name',
        'dbus-message-internal', 'debug-timer-check', 'declare-equiv-charset',
        'decode-big5-char', 'decode-char', 'decode-coding-region',
        'decode-coding-string', 'decode-sjis-char', 'decode-time',
        'default-boundp', 'default-file-modes', 'default-printer-name',
        'default-toplevel-value', 'default-value', 'define-category',
        'define-charset-alias', 'define-charset-internal',
        'define-coding-system-alias', 'define-coding-system-internal',
        'define-fringe-bitmap', 'define-hash-table-test', 'define-key',
        'define-prefix-command', 'delete',
        'delete-all-overlays', 'delete-and-extract-region', 'delete-char',
        'delete-directory-internal', 'delete-field', 'delete-file',
        'delete-frame', 'delete-other-windows-internal', 'delete-overlay',
        'delete-process', 'delete-region', 'delete-terminal',
        'delete-window-internal', 'delq', 'describe-buffer-bindings',
        'describe-vector', 'destroy-fringe-bitmap', 'detect-coding-region',
        'detect-coding-string', 'ding', 'directory-file-name',
        'directory-files', 'directory-files-and-attributes', 'discard-input',
        'display-supports-face-attributes-p', 'do-auto-save', 'documentation',
        'documentation-property', 'downcase', 'downcase-region',
        'downcase-word', 'draw-string', 'dump-colors', 'dump-emacs',
        'dump-face', 'dump-frame-glyph-matrix', 'dump-glyph-matrix',
        'dump-glyph-row', 'dump-redisplay-history', 'dump-tool-bar-row',
        'elt', 'emacs-pid', 'encode-big5-char', 'encode-char',
        'encode-coding-region', 'encode-coding-string', 'encode-sjis-char',
        'encode-time', 'end-kbd-macro', 'end-of-line', 'eobp', 'eolp', 'eq',
        'eql', 'equal', 'equal-including-properties', 'erase-buffer',
        'error-message-string', 'eval', 'eval-buffer', 'eval-region',
        'event-convert-list', 'execute-kbd-macro', 'exit-recursive-edit',
        'exp', 'expand-file-name', 'expt', 'external-debugging-output',
        'face-attribute-relative-p', 'face-attributes-as-vector', 'face-font',
        'fboundp', 'fceiling', 'fetch-bytecode', 'ffloor',
        'field-beginning', 'field-end', 'field-string',
        'field-string-no-properties', 'file-accessible-directory-p',
        'file-acl', 'file-attributes', 'file-attributes-lessp',
        'file-directory-p', 'file-executable-p', 'file-exists-p',
        'file-locked-p', 'file-modes', 'file-name-absolute-p',
        'file-name-all-completions', 'file-name-as-directory',
        'file-name-completion', 'file-name-directory',
        'file-name-nondirectory', 'file-newer-than-file-p', 'file-readable-p',
        'file-regular-p', 'file-selinux-context', 'file-symlink-p',
        'file-system-info', 'file-system-info', 'file-writable-p',
        'fillarray', 'find-charset-region', 'find-charset-string',
        'find-coding-systems-region-internal', 'find-composition-internal',
        'find-file-name-handler', 'find-font', 'find-operation-coding-system',
        'float', 'float-time', 'floatp', 'floor', 'fmakunbound',
        'following-char', 'font-at', 'font-drive-otf', 'font-face-attributes',
        'font-family-list', 'font-get', 'font-get-glyphs',
        'font-get-system-font', 'font-get-system-normal-font', 'font-info',
        'font-match-p', 'font-otf-alternates', 'font-put',
        'font-shape-gstring', 'font-spec', 'font-variation-glyphs',
        'font-xlfd-name', 'fontp', 'fontset-font', 'fontset-info',
        'fontset-list', 'fontset-list-all', 'force-mode-line-update',
        'force-window-update', 'format', 'format-mode-line',
        'format-network-address', 'format-time-string', 'forward-char',
        'forward-comment', 'forward-line', 'forward-word',
        'frame-border-width', 'frame-bottom-divider-width',
        'frame-can-run-window-configuration-change-hook', 'frame-char-height',
        'frame-char-width', 'frame-face-alist', 'frame-first-window',
        'frame-focus', 'frame-font-cache', 'frame-fringe-width', 'frame-list',
        'frame-live-p', 'frame-or-buffer-changed-p', 'frame-parameter',
        'frame-parameters', 'frame-pixel-height', 'frame-pixel-width',
        'frame-pointer-visible-p', 'frame-right-divider-width',
        'frame-root-window', 'frame-scroll-bar-height',
        'frame-scroll-bar-width', 'frame-selected-window', 'frame-terminal',
        'frame-text-cols', 'frame-text-height', 'frame-text-lines',
        'frame-text-width', 'frame-total-cols', 'frame-total-lines',
        'frame-visible-p', 'framep', 'frexp', 'fringe-bitmaps-at-pos',
        'fround', 'fset', 'ftruncate', 'funcall', 'funcall-interactively',
        'function-equal', 'functionp', 'gap-position', 'gap-size',
        'garbage-collect', 'gc-status', 'generate-new-buffer-name', 'get',
        'get-buffer', 'get-buffer-create', 'get-buffer-process',
        'get-buffer-window', 'get-byte', 'get-char-property',
        'get-char-property-and-overlay', 'get-file-buffer', 'get-file-char',
        'get-internal-run-time', 'get-load-suffixes', 'get-pos-property',
        'get-process', 'get-screen-color', 'get-text-property',
        'get-unicode-property-internal', 'get-unused-category',
        'get-unused-iso-final-char', 'getenv-internal', 'gethash',
        'gfile-add-watch', 'gfile-rm-watch', 'global-key-binding',
        'gnutls-available-p', 'gnutls-boot', 'gnutls-bye', 'gnutls-deinit',
        'gnutls-error-fatalp', 'gnutls-error-string', 'gnutls-errorp',
        'gnutls-get-initstage', 'gnutls-peer-status',
        'gnutls-peer-status-warning-describe', 'goto-char', 'gpm-mouse-start',
        'gpm-mouse-stop', 'group-gid', 'group-real-gid',
        'handle-save-session', 'handle-switch-frame', 'hash-table-count',
        'hash-table-p', 'hash-table-rehash-size',
        'hash-table-rehash-threshold', 'hash-table-size', 'hash-table-test',
        'hash-table-weakness', 'iconify-frame', 'identity', 'image-flush',
        'image-mask-p', 'image-metadata', 'image-size', 'imagemagick-types',
        'imagep', 'indent-to', 'indirect-function', 'indirect-variable',
        'init-image-library', 'inotify-add-watch', 'inotify-rm-watch',
        'input-pending-p', 'insert', 'insert-and-inherit',
        'insert-before-markers', 'insert-before-markers-and-inherit',
        'insert-buffer-substring', 'insert-byte', 'insert-char',
        'insert-file-contents', 'insert-startup-screen', 'int86',
        'integer-or-marker-p', 'integerp', 'interactive-form', 'intern',
        'intern-soft', 'internal--track-mouse', 'internal-char-font',
        'internal-complete-buffer', 'internal-copy-lisp-face',
        'internal-default-process-filter',
        'internal-default-process-sentinel', 'internal-describe-syntax-value',
        'internal-event-symbol-parse-modifiers',
        'internal-face-x-get-resource', 'internal-get-lisp-face-attribute',
        'internal-lisp-face-attribute-values', 'internal-lisp-face-empty-p',
        'internal-lisp-face-equal-p', 'internal-lisp-face-p',
        'internal-make-lisp-face', 'internal-make-var-non-special',
        'internal-merge-in-global-face',
        'internal-set-alternative-font-family-alist',
        'internal-set-alternative-font-registry-alist',
        'internal-set-font-selection-order',
        'internal-set-lisp-face-attribute',
        'internal-set-lisp-face-attribute-from-resource',
        'internal-show-cursor', 'internal-show-cursor-p', 'interrupt-process',
        'invisible-p', 'invocation-directory', 'invocation-name', 'isnan',
        'iso-charset', 'key-binding', 'key-description',
        'keyboard-coding-system', 'keymap-parent', 'keymap-prompt', 'keymapp',
        'keywordp', 'kill-all-local-variables', 'kill-buffer', 'kill-emacs',
        'kill-local-variable', 'kill-process', 'last-nonminibuffer-frame',
        'lax-plist-get', 'lax-plist-put', 'ldexp', 'length',
        'libxml-parse-html-region', 'libxml-parse-xml-region',
        'line-beginning-position', 'line-end-position', 'line-pixel-height',
        'list', 'list-fonts', 'list-system-processes', 'listp', 'load',
        'load-average', 'local-key-binding', 'local-variable-if-set-p',
        'local-variable-p', 'locale-info', 'locate-file-internal',
        'lock-buffer', 'log', 'logand', 'logb', 'logior', 'lognot', 'logxor',
        'looking-at', 'lookup-image', 'lookup-image-map', 'lookup-key',
        'lower-frame', 'lsh', 'macroexpand', 'make-bool-vector',
        'make-byte-code', 'make-category-set', 'make-category-table',
        'make-char', 'make-char-table', 'make-directory-internal',
        'make-frame-invisible', 'make-frame-visible', 'make-hash-table',
        'make-indirect-buffer', 'make-keymap', 'make-list',
        'make-local-variable', 'make-marker', 'make-network-process',
        'make-overlay', 'make-serial-process', 'make-sparse-keymap',
        'make-string', 'make-symbol', 'make-symbolic-link', 'make-temp-name',
        'make-terminal-frame', 'make-variable-buffer-local',
        'make-variable-frame-local', 'make-vector', 'makunbound',
        'map-char-table', 'map-charset-chars', 'map-keymap',
        'map-keymap-internal', 'mapatoms', 'mapc', 'mapcar', 'mapconcat',
        'maphash', 'mark-marker', 'marker-buffer', 'marker-insertion-type',
        'marker-position', 'markerp', 'match-beginning', 'match-data',
        'match-end', 'matching-paren', 'max', 'max-char', 'md5', 'member',
        'memory-info', 'memory-limit', 'memory-use-counts', 'memq', 'memql',
        'menu-bar-menu-at-x-y', 'menu-or-popup-active-p',
        'menu-or-popup-active-p', 'merge-face-attribute', 'message',
        'message-box', 'message-or-box', 'min',
        'minibuffer-completion-contents', 'minibuffer-contents',
        'minibuffer-contents-no-properties', 'minibuffer-depth',
        'minibuffer-prompt', 'minibuffer-prompt-end',
        'minibuffer-selected-window', 'minibuffer-window', 'minibufferp',
        'minor-mode-key-binding', 'mod', 'modify-category-entry',
        'modify-frame-parameters', 'modify-syntax-entry',
        'mouse-pixel-position', 'mouse-position', 'move-overlay',
        'move-point-visually', 'move-to-column', 'move-to-window-line',
        'msdos-downcase-filename', 'msdos-long-file-names', 'msdos-memget',
        'msdos-memput', 'msdos-mouse-disable', 'msdos-mouse-enable',
        'msdos-mouse-init', 'msdos-mouse-p', 'msdos-remember-default-colors',
        'msdos-set-keyboard', 'msdos-set-mouse-buttons',
        'multibyte-char-to-unibyte', 'multibyte-string-p', 'narrow-to-region',
        'natnump', 'nconc', 'network-interface-info',
        'network-interface-list', 'new-fontset', 'newline-cache-check',
        'next-char-property-change', 'next-frame', 'next-overlay-change',
        'next-property-change', 'next-read-file-uses-dialog-p',
        'next-single-char-property-change', 'next-single-property-change',
        'next-window', 'nlistp', 'nreverse', 'nth', 'nthcdr', 'null',
        'number-or-marker-p', 'number-to-string', 'numberp',
        'open-dribble-file', 'open-font', 'open-termscript',
        'optimize-char-table', 'other-buffer', 'other-window-for-scrolling',
        'overlay-buffer', 'overlay-end', 'overlay-get', 'overlay-lists',
        'overlay-properties', 'overlay-put', 'overlay-recenter',
        'overlay-start', 'overlayp', 'overlays-at', 'overlays-in',
        'parse-partial-sexp', 'play-sound-internal', 'plist-get',
        'plist-member', 'plist-put', 'point', 'point-marker', 'point-max',
        'point-max-marker', 'point-min', 'point-min-marker',
        'pos-visible-in-window-p', 'position-bytes', 'posix-looking-at',
        'posix-search-backward', 'posix-search-forward', 'posix-string-match',
        'posn-at-point', 'posn-at-x-y', 'preceding-char',
        'prefix-numeric-value', 'previous-char-property-change',
        'previous-frame', 'previous-overlay-change',
        'previous-property-change', 'previous-single-char-property-change',
        'previous-single-property-change', 'previous-window', 'prin1',
        'prin1-to-string', 'princ', 'print', 'process-attributes',
        'process-buffer', 'process-coding-system', 'process-command',
        'process-connection', 'process-contact', 'process-datagram-address',
        'process-exit-status', 'process-filter', 'process-filter-multibyte-p',
        'process-id', 'process-inherit-coding-system-flag', 'process-list',
        'process-mark', 'process-name', 'process-plist',
        'process-query-on-exit-flag', 'process-running-child-p',
        'process-send-eof', 'process-send-region', 'process-send-string',
        'process-sentinel', 'process-status', 'process-tty-name',
        'process-type', 'processp', 'profiler-cpu-log',
        'profiler-cpu-running-p', 'profiler-cpu-start', 'profiler-cpu-stop',
        'profiler-memory-log', 'profiler-memory-running-p',
        'profiler-memory-start', 'profiler-memory-stop', 'propertize',
        'purecopy', 'put', 'put-text-property',
        'put-unicode-property-internal', 'puthash', 'query-font',
        'query-fontset', 'quit-process', 'raise-frame', 'random', 'rassoc',
        'rassq', 're-search-backward', 're-search-forward', 'read',
        'read-buffer', 'read-char', 'read-char-exclusive',
        'read-coding-system', 'read-command', 'read-event',
        'read-from-minibuffer', 'read-from-string', 'read-function',
        'read-key-sequence', 'read-key-sequence-vector',
        'read-no-blanks-input', 'read-non-nil-coding-system', 'read-string',
        'read-variable', 'recent-auto-save-p', 'recent-doskeys',
        'recent-keys', 'recenter', 'recursion-depth', 'recursive-edit',
        'redirect-debugging-output', 'redirect-frame-focus', 'redisplay',
        'redraw-display', 'redraw-frame', 'regexp-quote', 'region-beginning',
        'region-end', 'register-ccl-program', 'register-code-conversion-map',
        'remhash', 'remove-list-of-text-properties', 'remove-text-properties',
        'rename-buffer', 'rename-file', 'replace-match',
        'reset-this-command-lengths', 'resize-mini-window-internal',
        'restore-buffer-modified-p', 'resume-tty', 'reverse', 'round',
        'run-hook-with-args', 'run-hook-with-args-until-failure',
        'run-hook-with-args-until-success', 'run-hook-wrapped', 'run-hooks',
        'run-window-configuration-change-hook', 'run-window-scroll-functions',
        'safe-length', 'scan-lists', 'scan-sexps', 'scroll-down',
        'scroll-left', 'scroll-other-window', 'scroll-right', 'scroll-up',
        'search-backward', 'search-forward', 'secure-hash', 'select-frame',
        'select-window', 'selected-frame', 'selected-window',
        'self-insert-command', 'send-string-to-terminal', 'sequencep',
        'serial-process-configure', 'set', 'set-buffer',
        'set-buffer-auto-saved', 'set-buffer-major-mode',
        'set-buffer-modified-p', 'set-buffer-multibyte', 'set-case-table',
        'set-category-table', 'set-char-table-extra-slot',
        'set-char-table-parent', 'set-char-table-range', 'set-charset-plist',
        'set-charset-priority', 'set-coding-system-priority',
        'set-cursor-size', 'set-default', 'set-default-file-modes',
        'set-default-toplevel-value', 'set-file-acl', 'set-file-modes',
        'set-file-selinux-context', 'set-file-times', 'set-fontset-font',
        'set-frame-height', 'set-frame-position', 'set-frame-selected-window',
        'set-frame-size', 'set-frame-width', 'set-fringe-bitmap-face',
        'set-input-interrupt-mode', 'set-input-meta-mode', 'set-input-mode',
        'set-keyboard-coding-system-internal', 'set-keymap-parent',
        'set-marker', 'set-marker-insertion-type', 'set-match-data',
        'set-message-beep', 'set-minibuffer-window',
        'set-mouse-pixel-position', 'set-mouse-position',
        'set-network-process-option', 'set-output-flow-control',
        'set-process-buffer', 'set-process-coding-system',
        'set-process-datagram-address', 'set-process-filter',
        'set-process-filter-multibyte',
        'set-process-inherit-coding-system-flag', 'set-process-plist',
        'set-process-query-on-exit-flag', 'set-process-sentinel',
        'set-process-window-size', 'set-quit-char',
        'set-safe-terminal-coding-system-internal', 'set-screen-color',
        'set-standard-case-table', 'set-syntax-table',
        'set-terminal-coding-system-internal', 'set-terminal-local-value',
        'set-terminal-parameter', 'set-text-properties', 'set-time-zone-rule',
        'set-visited-file-modtime', 'set-window-buffer',
        'set-window-combination-limit', 'set-window-configuration',
        'set-window-dedicated-p', 'set-window-display-table',
        'set-window-fringes', 'set-window-hscroll', 'set-window-margins',
        'set-window-new-normal', 'set-window-new-pixel',
        'set-window-new-total', 'set-window-next-buffers',
        'set-window-parameter', 'set-window-point', 'set-window-prev-buffers',
        'set-window-redisplay-end-trigger', 'set-window-scroll-bars',
        'set-window-start', 'set-window-vscroll', 'setcar', 'setcdr',
        'setplist', 'show-face-resources', 'signal', 'signal-process', 'sin',
        'single-key-description', 'skip-chars-backward', 'skip-chars-forward',
        'skip-syntax-backward', 'skip-syntax-forward', 'sleep-for', 'sort',
        'sort-charsets', 'special-variable-p', 'split-char',
        'split-window-internal', 'sqrt', 'standard-case-table',
        'standard-category-table', 'standard-syntax-table', 'start-kbd-macro',
        'start-process', 'stop-process', 'store-kbd-macro-event', 'string',
        'string=', 'string<', 'string>', 'string-as-multibyte',
        'string-as-unibyte', 'string-bytes', 'string-collate-equalp',
        'string-collate-lessp', 'string-equal', 'string-greaterp',
        'string-lessp', 'string-make-multibyte', 'string-make-unibyte',
        'string-match', 'string-to-char', 'string-to-multibyte',
        'string-to-number', 'string-to-syntax', 'string-to-unibyte',
        'string-width', 'stringp', 'subr-name', 'subrp',
        'subst-char-in-region', 'substitute-command-keys',
        'substitute-in-file-name', 'substring', 'substring-no-properties',
        'suspend-emacs', 'suspend-tty', 'suspicious-object', 'sxhash',
        'symbol-function', 'symbol-name', 'symbol-plist', 'symbol-value',
        'symbolp', 'syntax-table', 'syntax-table-p', 'system-groups',
        'system-move-file-to-trash', 'system-name', 'system-users', 'tan',
        'terminal-coding-system', 'terminal-list', 'terminal-live-p',
        'terminal-local-value', 'terminal-name', 'terminal-parameter',
        'terminal-parameters', 'terpri', 'test-completion',
        'text-char-description', 'text-properties-at', 'text-property-any',
        'text-property-not-all', 'this-command-keys',
        'this-command-keys-vector', 'this-single-command-keys',
        'this-single-command-raw-keys', 'time-add', 'time-less-p',
        'time-subtract', 'tool-bar-get-system-style', 'tool-bar-height',
        'tool-bar-pixel-width', 'top-level', 'trace-redisplay',
        'trace-to-stderr', 'translate-region-internal', 'transpose-regions',
        'truncate', 'try-completion', 'tty-display-color-cells',
        'tty-display-color-p', 'tty-no-underline',
        'tty-suppress-bold-inverse-default-colors', 'tty-top-frame',
        'tty-type', 'type-of', 'undo-boundary', 'unencodable-char-position',
        'unhandled-file-name-directory', 'unibyte-char-to-multibyte',
        'unibyte-string', 'unicode-property-table-internal', 'unify-charset',
        'unintern', 'unix-sync', 'unlock-buffer', 'upcase', 'upcase-initials',
        'upcase-initials-region', 'upcase-region', 'upcase-word',
        'use-global-map', 'use-local-map', 'user-full-name',
        'user-login-name', 'user-real-login-name', 'user-real-uid',
        'user-uid', 'variable-binding-locus', 'vconcat', 'vector',
        'vector-or-char-table-p', 'vectorp', 'verify-visited-file-modtime',
        'vertical-motion', 'visible-frame-list', 'visited-file-modtime',
        'w16-get-clipboard-data', 'w16-selection-exists-p',
        'w16-set-clipboard-data', 'w32-battery-status',
        'w32-default-color-map', 'w32-define-rgb-color',
        'w32-display-monitor-attributes-list', 'w32-frame-menu-bar-size',
        'w32-frame-rect', 'w32-get-clipboard-data',
        'w32-get-codepage-charset', 'w32-get-console-codepage',
        'w32-get-console-output-codepage', 'w32-get-current-locale-id',
        'w32-get-default-locale-id', 'w32-get-keyboard-layout',
        'w32-get-locale-info', 'w32-get-valid-codepages',
        'w32-get-valid-keyboard-layouts', 'w32-get-valid-locale-ids',
        'w32-has-winsock', 'w32-long-file-name', 'w32-reconstruct-hot-key',
        'w32-register-hot-key', 'w32-registered-hot-keys',
        'w32-selection-exists-p', 'w32-send-sys-command',
        'w32-set-clipboard-data', 'w32-set-console-codepage',
        'w32-set-console-output-codepage', 'w32-set-current-locale',
        'w32-set-keyboard-layout', 'w32-set-process-priority',
        'w32-shell-execute', 'w32-short-file-name', 'w32-toggle-lock-key',
        'w32-unload-winsock', 'w32-unregister-hot-key', 'w32-window-exists-p',
        'w32notify-add-watch', 'w32notify-rm-watch',
        'waiting-for-user-input-p', 'where-is-internal', 'widen',
        'widget-apply', 'widget-get', 'widget-put',
        'window-absolute-pixel-edges', 'window-at', 'window-body-height',
        'window-body-width', 'window-bottom-divider-width', 'window-buffer',
        'window-combination-limit', 'window-configuration-frame',
        'window-configuration-p', 'window-dedicated-p',
        'window-display-table', 'window-edges', 'window-end', 'window-frame',
        'window-fringes', 'window-header-line-height', 'window-hscroll',
        'window-inside-absolute-pixel-edges', 'window-inside-edges',
        'window-inside-pixel-edges', 'window-left-child',
        'window-left-column', 'window-line-height', 'window-list',
        'window-list-1', 'window-live-p', 'window-margins',
        'window-minibuffer-p', 'window-mode-line-height', 'window-new-normal',
        'window-new-pixel', 'window-new-total', 'window-next-buffers',
        'window-next-sibling', 'window-normal-size', 'window-old-point',
        'window-parameter', 'window-parameters', 'window-parent',
        'window-pixel-edges', 'window-pixel-height', 'window-pixel-left',
        'window-pixel-top', 'window-pixel-width', 'window-point',
        'window-prev-buffers', 'window-prev-sibling',
        'window-redisplay-end-trigger', 'window-resize-apply',
        'window-resize-apply-total', 'window-right-divider-width',
        'window-scroll-bar-height', 'window-scroll-bar-width',
        'window-scroll-bars', 'window-start', 'window-system',
        'window-text-height', 'window-text-pixel-size', 'window-text-width',
        'window-top-child', 'window-top-line', 'window-total-height',
        'window-total-width', 'window-use-time', 'window-valid-p',
        'window-vscroll', 'windowp', 'write-char', 'write-region',
        'x-backspace-delete-keys-p', 'x-change-window-property',
        'x-change-window-property', 'x-close-connection',
        'x-close-connection', 'x-create-frame', 'x-create-frame',
        'x-delete-window-property', 'x-delete-window-property',
        'x-disown-selection-internal', 'x-display-backing-store',
        'x-display-backing-store', 'x-display-color-cells',
        'x-display-color-cells', 'x-display-grayscale-p',
        'x-display-grayscale-p', 'x-display-list', 'x-display-list',
        'x-display-mm-height', 'x-display-mm-height', 'x-display-mm-width',
        'x-display-mm-width', 'x-display-monitor-attributes-list',
        'x-display-pixel-height', 'x-display-pixel-height',
        'x-display-pixel-width', 'x-display-pixel-width', 'x-display-planes',
        'x-display-planes', 'x-display-save-under', 'x-display-save-under',
        'x-display-screens', 'x-display-screens', 'x-display-visual-class',
        'x-display-visual-class', 'x-family-fonts', 'x-file-dialog',
        'x-file-dialog', 'x-file-dialog', 'x-focus-frame', 'x-frame-geometry',
        'x-frame-geometry', 'x-get-atom-name', 'x-get-resource',
        'x-get-selection-internal', 'x-hide-tip', 'x-hide-tip',
        'x-list-fonts', 'x-load-color-file', 'x-menu-bar-open-internal',
        'x-menu-bar-open-internal', 'x-open-connection', 'x-open-connection',
        'x-own-selection-internal', 'x-parse-geometry', 'x-popup-dialog',
        'x-popup-menu', 'x-register-dnd-atom', 'x-select-font',
        'x-select-font', 'x-selection-exists-p', 'x-selection-owner-p',
        'x-send-client-message', 'x-server-max-request-size',
        'x-server-max-request-size', 'x-server-vendor', 'x-server-vendor',
        'x-server-version', 'x-server-version', 'x-show-tip', 'x-show-tip',
        'x-synchronize', 'x-synchronize', 'x-uses-old-gtk-dialog',
        'x-window-property', 'x-window-property', 'x-wm-set-size-hint',
        'xw-color-defined-p', 'xw-color-defined-p', 'xw-color-values',
        'xw-color-values', 'xw-display-color-p', 'xw-display-color-p',
        'yes-or-no-p', 'zlib-available-p', 'zlib-decompress-region',
        'forward-point',
    }

    builtin_function_highlighted = {
        'defvaralias', 'provide', 'require',
        'with-no-warnings', 'define-widget', 'with-electric-help',
        'throw', 'defalias', 'featurep'
    }

    lambda_list_keywords = {
        '&allow-other-keys', '&aux', '&body', '&environment', '&key', '&optional',
        '&rest', '&whole',
    }

    error_keywords = {
        'cl-assert', 'cl-check-type', 'error', 'signal',
        'user-error', 'warn',
    }

    def get_tokens_unprocessed(self, text):
        stack = ['root']
        for index, token, value in RegexLexer.get_tokens_unprocessed(self, text, stack):
            if token is Name.Variable:
                if value in EmacsLispLexer.builtin_function:
                    yield index, Name.Function, value
                    continue
                if value in EmacsLispLexer.special_forms:
                    yield index, Keyword, value
                    continue
                if value in EmacsLispLexer.error_keywords:
                    yield index, Name.Exception, value
                    continue
                if value in EmacsLispLexer.builtin_function_highlighted:
                    yield index, Name.Builtin, value
                    continue
                if value in EmacsLispLexer.macros:
                    yield index, Name.Builtin, value
                    continue
                if value in EmacsLispLexer.lambda_list_keywords:
                    yield index, Keyword.Pseudo, value
                    continue
            yield index, token, value

    tokens = {
        'root': [
            default('body'),
        ],
        'body': [
            # whitespace
            (r'\s+', Whitespace),

            # single-line comment
            (r';.*$', Comment.Single),

            # strings and characters
            (r'"', String, 'string'),
            (r'\?([^\\]|\\.)', String.Char),
            # quoting
            (r":" + symbol, Name.Builtin),
            (r"::" + symbol, String.Symbol),
            (r"'" + symbol, String.Symbol),
            (r"'", Operator),
            (r"`", Operator),

            # decimal numbers
            (r'[-+]?\d+\.?' + terminated, Number.Integer),
            (r'[-+]?\d+/\d+' + terminated, Number),
            (r'[-+]?(\d*\.\d+([defls][-+]?\d+)?|\d+(\.\d*)?[defls][-+]?\d+)' +
             terminated, Number.Float),

            # vectors
            (r'\[|\]', Punctuation),

            # uninterned symbol
            (r'#:' + symbol, String.Symbol),

            # read syntax for char tables
            (r'#\^\^?', Operator),

            # function shorthand
            (r'#\'', Name.Function),

            # binary rational
            (r'#[bB][+-]?[01]+(/[01]+)?', Number.Bin),

            # octal rational
            (r'#[oO][+-]?[0-7]+(/[0-7]+)?', Number.Oct),

            # hex rational
            (r'#[xX][+-]?[0-9a-fA-F]+(/[0-9a-fA-F]+)?', Number.Hex),

            # radix rational
            (r'#\d+r[+-]?[0-9a-zA-Z]+(/[0-9a-zA-Z]+)?', Number),

            # reference
            (r'#\d+=', Operator),
            (r'#\d+#', Operator),

            # special operators that should have been parsed already
            (r'(,@|,|\.|:)', Operator),

            # special constants
            (r'(t|nil)' + terminated, Name.Constant),

            # functions and variables
            (r'\*' + symbol + r'\*', Name.Variable.Global),
            (symbol, Name.Variable),

            # parentheses
            (r'#\(', Operator, 'body'),
            (r'\(', Punctuation, 'body'),
            (r'\)', Punctuation, '#pop'),
        ],
        'string': [
            (r'[^"\\`]+', String),
            (rf'`{symbol}\'', String.Symbol),
            (r'`', String),
            (r'\\.', String),
            (r'\\\n', String),
            (r'"', String, '#pop'),
        ],
    }


class ShenLexer(RegexLexer):
    """
    Lexer for Shen source code.
    """
    name = 'Shen'
    url = 'http://shenlanguage.org/'
    aliases = ['shen']
    filenames = ['*.shen']
    mimetypes = ['text/x-shen', 'application/x-shen']
    version_added = '2.1'

    DECLARATIONS = (
        'datatype', 'define', 'defmacro', 'defprolog', 'defcc',
        'synonyms', 'declare', 'package', 'type', 'function',
    )

    SPECIAL_FORMS = (
        'lambda', 'get', 'let', 'if', 'cases', 'cond', 'put', 'time', 'freeze',
        'value', 'load', '$', 'protect', 'or', 'and', 'not', 'do', 'output',
        'prolog?', 'trap-error', 'error', 'make-string', '/.', 'set', '@p',
        '@s', '@v',
    )

    BUILTINS = (
        '==', '=', '*', '+', '-', '/', '<', '>', '>=', '<=', '<-address',
        '<-vector', 'abort', 'absvector', 'absvector?', 'address->', 'adjoin',
        'append', 'arity', 'assoc', 'bind', 'boolean?', 'bound?', 'call', 'cd',
        'close', 'cn', 'compile', 'concat', 'cons', 'cons?', 'cut', 'destroy',
        'difference', 'element?', 'empty?', 'enable-type-theory',
        'error-to-string', 'eval', 'eval-kl', 'exception', 'explode', 'external',
        'fail', 'fail-if', 'file', 'findall', 'fix', 'fst', 'fwhen', 'gensym',
        'get-time', 'hash', 'hd', 'hdstr', 'hdv', 'head', 'identical',
        'implementation', 'in', 'include', 'include-all-but', 'inferences',
        'input', 'input+', 'integer?', 'intern', 'intersection', 'is', 'kill',
        'language', 'length', 'limit', 'lineread', 'loaded', 'macro', 'macroexpand',
        'map', 'mapcan', 'maxinferences', 'mode', 'n->string', 'nl', 'nth', 'null',
        'number?', 'occurrences', 'occurs-check', 'open', 'os', 'out', 'port',
        'porters', 'pos', 'pr', 'preclude', 'preclude-all-but', 'print', 'profile',
        'profile-results', 'ps', 'quit', 'read', 'read+', 'read-byte', 'read-file',
        'read-file-as-bytelist', 'read-file-as-string', 'read-from-string',
        'release', 'remove', 'return', 'reverse', 'run', 'save', 'set',
        'simple-error', 'snd', 'specialise', 'spy', 'step', 'stinput', 'stoutput',
        'str', 'string->n', 'string->symbol', 'string?', 'subst', 'symbol?',
        'systemf', 'tail', 'tc', 'tc?', 'thaw', 'tl', 'tlstr', 'tlv', 'track',
        'tuple?', 'undefmacro', 'unify', 'unify!', 'union', 'unprofile',
        'unspecialise', 'untrack', 'variable?', 'vector', 'vector->', 'vector?',
        'verified', 'version', 'warn', 'when', 'write-byte', 'write-to-file',
        'y-or-n?',
    )

    BUILTINS_ANYWHERE = ('where', 'skip', '>>', '_', '!', '<e>', '<!>')

    MAPPINGS = {s: Keyword for s in DECLARATIONS}
    MAPPINGS.update((s, Name.Builtin) for s in BUILTINS)
    MAPPINGS.update((s, Keyword) for s in SPECIAL_FORMS)

    valid_symbol_chars = r'[\w!$%*+,<=>?/.\'@&#:-]'
    valid_name = f'{valid_symbol_chars}+'
    symbol_name = rf'[a-z!$%*+,<=>?/.\'@&#_-]{valid_symbol_chars}*'
    variable = rf'[A-Z]{valid_symbol_chars}*'

    tokens = {
        'string': [
            (r'"', String, '#pop'),
            (r'c#\d{1,3};', String.Escape),
            (r'~[ARS%]', String.Interpol),
            (r'(?s).', String),
        ],

        'root': [
            (r'(?s)\\\*.*?\*\\', Comment.Multiline),  # \* ... *\
            (r'\\\\.*', Comment.Single),              # \\ ...
            (r'\s+', Whitespace),
            (r'_{5,}', Punctuation),
            (r'={5,}', Punctuation),
            (r'(;|:=|\||--?>|<--?)', Punctuation),
            (r'(:-|:|\{|\})', Literal),
            (r'[+-]*\d*\.\d+(e[+-]?\d+)?', Number.Float),
            (r'[+-]*\d+', Number.Integer),
            (r'"', String, 'string'),
            (variable, Name.Variable),
            (r'(true|false|<>|\[\])', Keyword.Pseudo),
            (symbol_name, Literal),
            (r'(\[|\]|\(|\))', Punctuation),
        ],
    }

    def get_tokens_unprocessed(self, text):
        tokens = RegexLexer.get_tokens_unprocessed(self, text)
        tokens = self._process_symbols(tokens)
        tokens = self._process_declarations(tokens)
        return tokens

    def _relevant(self, token):
        return token not in (Text, Whitespace, Comment.Single, Comment.Multiline)

    def _process_declarations(self, tokens):
        opening_paren = False
        for index, token, value in tokens:
            yield index, token, value
            if self._relevant(token):
                if opening_paren and token == Keyword and value in self.DECLARATIONS:
                    declaration = value
                    yield from self._process_declaration(declaration, tokens)
                opening_paren = value == '(' and token == Punctuation

    def _process_symbols(self, tokens):
        opening_paren = False
        for index, token, value in tokens:
            if opening_paren and token in (Literal, Name.Variable):
                token = self.MAPPINGS.get(value, Name.Function)
            elif token == Literal and value in self.BUILTINS_ANYWHERE:
                token = Name.Builtin
            opening_paren = value == '(' and token == Punctuation
            yield index, token, value

    def _process_declaration(self, declaration, tokens):
        for index, token, value in tokens:
            if self._relevant(token):
                break
            yield index, token, value

        if declaration == 'datatype':
            prev_was_colon = False
            token = Keyword.Type if token == Literal else token
            yield index, token, value
            for index, token, value in tokens:
                if prev_was_colon and token == Literal:
                    token = Keyword.Type
                yield index, token, value
                if self._relevant(token):
                    prev_was_colon = token == Literal and value == ':'
        elif declaration == 'package':
            token = Name.Namespace if token == Literal else token
            yield index, token, value
        elif declaration == 'define':
            token = Name.Function if token == Literal else token
            yield index, token, value
            for index, token, value in tokens:
                if self._relevant(token):
                    break
                yield index, token, value
            if value == '{' and token == Literal:
                yield index, Punctuation, value
                for index, token, value in self._process_signature(tokens):
                    yield index, token, value
            else:
                yield index, token, value
        else:
            token = Name.Function if token == Literal else token
            yield index, token, value

        return

    def _process_signature(self, tokens):
        for index, token, value in tokens:
            if token == Literal and value == '}':
                yield index, Punctuation, value
                return
            elif token in (Literal, Name.Function):
                token = Name.Variable if value.istitle() else Keyword.Type
            yield index, token, value


class CPSALexer(RegexLexer):
    """
    A CPSA lexer based on the CPSA language as of version 2.2.12
    """
    name = 'CPSA'
    aliases = ['cpsa']
    filenames = ['*.cpsa']
    mimetypes = []
    url = 'https://web.cs.wpi.edu/~guttman/cs564/cpsauser.html'
    version_added = '2.1'

    # list of known keywords and builtins taken form vim 6.4 scheme.vim
    # syntax file.
    _keywords = (
        'herald', 'vars', 'defmacro', 'include', 'defprotocol', 'defrole',
        'defskeleton', 'defstrand', 'deflistener', 'non-orig', 'uniq-orig',
        'pen-non-orig', 'precedes', 'trace', 'send', 'recv', 'name', 'text',
        'skey', 'akey', 'data', 'mesg',
    )
    _builtins = (
        'cat', 'enc', 'hash', 'privk', 'pubk', 'invk', 'ltk', 'gen', 'exp',
    )

    # valid names for identifiers
    # well, names can only not consist fully of numbers
    # but this should be good enough for now
    valid_name = r'[\w!$%&*+,/:<=>?@^~|-]+'

    tokens = {
        'root': [
            # the comments - always starting with semicolon
            # and going to the end of the line
            (r';.*$', Comment.Single),

            # whitespaces - usually not relevant
            (r'\s+', Whitespace),

            # numbers
            (r'-?\d+\.\d+', Number.Float),
            (r'-?\d+', Number.Integer),
            # support for uncommon kinds of numbers -
            # have to figure out what the characters mean
            # (r'(#e|#i|#b|#o|#d|#x)[\d.]+', Number),

            # strings, symbols and characters
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),
            (r"'" + valid_name, String.Symbol),
            (r"#\\([()/'\"._!§$%& ?=+-]|[a-zA-Z0-9]+)", String.Char),

            # constants
            (r'(#t|#f)', Name.Constant),

            # special operators
            (r"('|#|`|,@|,|\.)", Operator),

            # highlight the keywords
            (words(_keywords, suffix=r'\b'), Keyword),

            # first variable in a quoted string like
            # '(this is syntactic sugar)
            (r"(?<='\()" + valid_name, Name.Variable),
            (r"(?<=#\()" + valid_name, Name.Variable),

            # highlight the builtins
            (words(_builtins, prefix=r'(?<=\()', suffix=r'\b'), Name.Builtin),

            # the remaining functions
            (r'(?<=\()' + valid_name, Name.Function),
            # find the remaining variables
            (valid_name, Name.Variable),

            # the famous parentheses!
            (r'(\(|\))', Punctuation),
            (r'(\[|\])', Punctuation),
        ],
    }


class XtlangLexer(RegexLexer):
    """An xtlang lexer for the Extempore programming environment.

    This is a mixture of Scheme and xtlang, really. Keyword lists are
    taken from the Extempore Emacs mode
    (https://github.com/extemporelang/extempore-emacs-mode)
    """
    name = 'xtlang'
    url = 'http://extempore.moso.com.au'
    aliases = ['extempore']
    filenames = ['*.xtm']
    mimetypes = []
    version_added = '2.2'

    common_keywords = (
        'lambda', 'define', 'if', 'else', 'cond', 'and',
        'or', 'let', 'begin', 'set!', 'map', 'for-each',
    )
    scheme_keywords = (
        'do', 'delay', 'quasiquote', 'unquote', 'unquote-splicing', 'eval',
        'case', 'let*', 'letrec', 'quote',
    )
    xtlang_bind_keywords = (
        'bind-func', 'bind-val', 'bind-lib', 'bind-type', 'bind-alias',
        'bind-poly', 'bind-dylib', 'bind-lib-func', 'bind-lib-val',
    )
    xtlang_keywords = (
        'letz', 'memzone', 'cast', 'convert', 'dotimes', 'doloop',
    )
    common_functions = (
        '*', '+', '-', '/', '<', '<=', '=', '>', '>=', '%', 'abs', 'acos',
        'angle', 'append', 'apply', 'asin', 'assoc', 'assq', 'assv',
        'atan', 'boolean?', 'caaaar', 'caaadr', 'caaar', 'caadar',
        'caaddr', 'caadr', 'caar', 'cadaar', 'cadadr', 'cadar',
        'caddar', 'cadddr', 'caddr', 'cadr', 'car', 'cdaaar',
        'cdaadr', 'cdaar', 'cdadar', 'cdaddr', 'cdadr', 'cdar',
        'cddaar', 'cddadr', 'cddar', 'cdddar', 'cddddr', 'cdddr',
        'cddr', 'cdr', 'ceiling', 'cons', 'cos', 'floor', 'length',
        'list', 'log', 'max', 'member', 'min', 'modulo', 'not',
        'reverse', 'round', 'sin', 'sqrt', 'substring', 'tan',
        'println', 'random', 'null?', 'callback', 'now',
    )
    scheme_functions = (
        'call-with-current-continuation', 'call-with-input-file',
        'call-with-output-file', 'call-with-values', 'call/cc',
        'char->integer', 'char-alphabetic?', 'char-ci<=?', 'char-ci<?',
        'char-ci=?', 'char-ci>=?', 'char-ci>?', 'char-downcase',
        'char-lower-case?', 'char-numeric?', 'char-ready?',
        'char-upcase', 'char-upper-case?', 'char-whitespace?',
        'char<=?', 'char<?', 'char=?', 'char>=?', 'char>?', 'char?',
        'close-input-port', 'close-output-port', 'complex?',
        'current-input-port', 'current-output-port', 'denominator',
        'display', 'dynamic-wind', 'eof-object?', 'eq?', 'equal?',
        'eqv?', 'even?', 'exact->inexact', 'exact?', 'exp', 'expt',
        'force', 'gcd', 'imag-part', 'inexact->exact', 'inexact?',
        'input-port?', 'integer->char', 'integer?',
        'interaction-environment', 'lcm', 'list->string',
        'list->vector', 'list-ref', 'list-tail', 'list?', 'load',
        'magnitude', 'make-polar', 'make-rectangular', 'make-string',
        'make-vector', 'memq', 'memv', 'negative?', 'newline',
        'null-environment', 'number->string', 'number?',
        'numerator', 'odd?', 'open-input-file', 'open-output-file',
        'output-port?', 'pair?', 'peek-char', 'port?', 'positive?',
        'procedure?', 'quotient', 'rational?', 'rationalize', 'read',
        'read-char', 'real-part', 'real?',
        'remainder', 'scheme-report-environment', 'set-car!', 'set-cdr!',
        'string', 'string->list', 'string->number', 'string->symbol',
        'string-append', 'string-ci<=?', 'string-ci<?', 'string-ci=?',
        'string-ci>=?', 'string-ci>?', 'string-copy', 'string-fill!',
        'string-length', 'string-ref', 'string-set!', 'string<=?',
        'string<?', 'string=?', 'string>=?', 'string>?', 'string?',
        'symbol->string', 'symbol?', 'transcript-off', 'transcript-on',
        'truncate', 'values', 'vector', 'vector->list', 'vector-fill!',
        'vector-length', 'vector?',
        'with-input-from-file', 'with-output-to-file', 'write',
        'write-char', 'zero?',
    )
    xtlang_functions = (
        'toString', 'afill!', 'pfill!', 'tfill!', 'tbind', 'vfill!',
        'array-fill!', 'pointer-fill!', 'tuple-fill!', 'vector-fill!', 'free',
        'array', 'tuple', 'list', '~', 'cset!', 'cref', '&', 'bor',
        'ang-names', '<<', '>>', 'nil', 'printf', 'sprintf', 'null', 'now',
        'pset!', 'pref-ptr', 'vset!', 'vref', 'aset!', 'aref', 'aref-ptr',
        'tset!', 'tref', 'tref-ptr', 'salloc', 'halloc', 'zalloc', 'alloc',
        'schedule', 'exp', 'log', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
        'sqrt', 'expt', 'floor', 'ceiling', 'truncate', 'round',
        'llvm_printf', 'push_zone', 'pop_zone', 'memzone', 'callback',
        'llvm_sprintf', 'make-array', 'array-set!', 'array-ref',
        'array-ref-ptr', 'pointer-set!', 'pointer-ref', 'pointer-ref-ptr',
        'stack-alloc', 'heap-alloc', 'zone-alloc', 'make-tuple', 'tuple-set!',
        'tuple-ref', 'tuple-ref-ptr', 'closure-set!', 'closure-ref', 'pref',
        'pdref', 'impc_null', 'bitcast', 'void', 'ifret', 'ret->', 'clrun->',
        'make-env-zone', 'make-env', '<>', 'dtof', 'ftod', 'i1tof',
        'i1tod', 'i1toi8', 'i1toi32', 'i1toi64', 'i8tof', 'i8tod',
        'i8toi1', 'i8toi32', 'i8toi64', 'i32tof', 'i32tod', 'i32toi1',
        'i32toi8', 'i32toi64', 'i64tof', 'i64tod', 'i64toi1',
        'i64toi8', 'i64toi32',
    )

    # valid names for Scheme identifiers (names cannot consist fully
    # of numbers, but this should be good enough for now)
    valid_scheme_name = r'[\w!$%&*+,/:<=>?@^~|-]+'

    # valid characters in xtlang names & types
    valid_xtlang_name = r'[\w.!-]+'
    valid_xtlang_type = r'[]{}[\w<>,*/|!-]+'

    tokens = {
        # keep track of when we're exiting the xtlang form
        'xtlang': [
            (r'\(', Punctuation, '#push'),
            (r'\)', Punctuation, '#pop'),

            (r'(?<=bind-func\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-val\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-type\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-alias\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-poly\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-lib\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-dylib\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-lib-func\s)' + valid_xtlang_name, Name.Function),
            (r'(?<=bind-lib-val\s)' + valid_xtlang_name, Name.Function),

            # type annotations
            (r':' + valid_xtlang_type, Keyword.Type),

            # types
            (r'(<' + valid_xtlang_type + r'>|\|' + valid_xtlang_type + r'\||/' +
             valid_xtlang_type + r'/|' + valid_xtlang_type + r'\*)\**',
             Keyword.Type),

            # keywords
            (words(xtlang_keywords, prefix=r'(?<=\()'), Keyword),

            # builtins
            (words(xtlang_functions, prefix=r'(?<=\()'), Name.Function),

            include('common'),

            # variables
            (valid_xtlang_name, Name.Variable),
        ],
        'scheme': [
            # quoted symbols
            (r"'" + valid_scheme_name, String.Symbol),

            # char literals
            (r"#\\([()/'\"._!§$%& ?=+-]|[a-zA-Z0-9]+)", String.Char),

            # special operators
            (r"('|#|`|,@|,|\.)", Operator),

            # keywords
            (words(scheme_keywords, prefix=r'(?<=\()'), Keyword),

            # builtins
            (words(scheme_functions, prefix=r'(?<=\()'), Name.Function),

            include('common'),

            # variables
            (valid_scheme_name, Name.Variable),
        ],
        # common to both xtlang and Scheme
        'common': [
            # comments
            (r';.*$', Comment.Single),

            # whitespaces - usually not relevant
            (r'\s+', Whitespace),

            # numbers
            (r'-?\d+\.\d+', Number.Float),
            (r'-?\d+', Number.Integer),

            # binary/oct/hex literals
            (r'(#b|#o|#x)[\d.]+', Number),

            # strings
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),

            # true/false constants
            (r'(#t|#f)', Name.Constant),

            # keywords
            (words(common_keywords, prefix=r'(?<=\()'), Keyword),

            # builtins
            (words(common_functions, prefix=r'(?<=\()'), Name.Function),

            # the famous parentheses!
            (r'(\(|\))', Punctuation),
        ],
        'root': [
            # go into xtlang mode
            (words(xtlang_bind_keywords, prefix=r'(?<=\()', suffix=r'\b'),
             Keyword, 'xtlang'),

            include('scheme')
        ],
    }


class FennelLexer(RegexLexer):
    """A lexer for the Fennel programming language.

    Fennel compiles to Lua, so all the Lua builtins are recognized as well
    as the special forms that are particular to the Fennel compiler.
    """
    name = 'Fennel'
    url = 'https://fennel-lang.org'
    aliases = ['fennel', 'fnl']
    filenames = ['*.fnl']
    version_added = '2.3'

    # this list is current as of Fennel version 0.10.0.
    special_forms = (
        '#', '%', '*', '+', '-', '->', '->>', '-?>', '-?>>', '.', '..',
        '/', '//', ':', '<', '<=', '=', '>', '>=', '?.', '^', 'accumulate',
        'and', 'band', 'bnot', 'bor', 'bxor', 'collect', 'comment', 'do', 'doc',
        'doto', 'each', 'eval-compiler', 'for', 'hashfn', 'icollect', 'if',
        'import-macros', 'include', 'length', 'let', 'lshift', 'lua',
        'macrodebug', 'match', 'not', 'not=', 'or', 'partial', 'pick-args',
        'pick-values', 'quote', 'require-macros', 'rshift', 'set',
        'set-forcibly!', 'tset', 'values', 'when', 'while', 'with-open', '~='
    )

    declarations = (
        'fn', 'global', 'lambda', 'local', 'macro', 'macros', 'var', 'λ'
    )

    builtins = (
        '_G', '_VERSION', 'arg', 'assert', 'bit32', 'collectgarbage',
        'coroutine', 'debug', 'dofile', 'error', 'getfenv',
        'getmetatable', 'io', 'ipairs', 'load', 'loadfile', 'loadstring',
        'math', 'next', 'os', 'package', 'pairs', 'pcall', 'print',
        'rawequal', 'rawget', 'rawlen', 'rawset', 'require', 'select',
        'setfenv', 'setmetatable', 'string', 'table', 'tonumber',
        'tostring', 'type', 'unpack', 'xpcall'
    )

    # based on the scheme definition, but disallowing leading digits and
    # commas, and @ is not allowed.
    valid_name = r'[a-zA-Z_!$%&*+/:<=>?^~|-][\w!$%&*+/:<=>?^~|\.-]*'

    tokens = {
        'root': [
            # the only comment form is a semicolon; goes to the end of the line
            (r';.*$', Comment.Single),

            (r',+', Text),
            (r'\s+', Whitespace),
            (r'-?\d+\.\d+', Number.Float),
            (r'-?\d+', Number.Integer),

            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),

            (r'(true|false|nil)', Name.Constant),

            # these are technically strings, but it's worth visually
            # distinguishing them because their intent is different
            # from regular strings.
            (r':' + valid_name, String.Symbol),

            # special forms are keywords
            (words(special_forms, suffix=' '), Keyword),
            # these are ... even more special!
            (words(declarations, suffix=' '), Keyword.Declaration),
            # lua standard library are builtins
            (words(builtins, suffix=' '), Name.Builtin),
            # special-case the vararg symbol
            (r'\.\.\.', Name.Variable),
            # regular identifiers
            (valid_name, Name.Variable),

            # all your normal paired delimiters for your programming enjoyment
            (r'(\(|\))', Punctuation),
            (r'(\[|\])', Punctuation),
            (r'(\{|\})', Punctuation),

            # the # symbol is shorthand for a lambda function
            (r'#', Punctuation),
        ]
    }


class JanetLexer(RegexLexer):
    """A lexer for the Janet programming language.
    """
    name = 'Janet'
    url =  'https://janet-lang.org/'
    aliases = ['janet']
    filenames = ['*.janet', '*.jdn']
    mimetypes = ['text/x-janet', 'application/x-janet']
    version_added = '2.18'

    # XXX: gets too slow
    #flags = re.MULTILINE | re.VERBOSE

    special_forms = (
        'break', 'def', 'do', 'fn', 'if', 'quote', 'quasiquote', 'splice',
        'set', 'unquote', 'upscope', 'var', 'while'
    )

    builtin_macros = (
        '%=', '*=', '++', '+=', '--', '-=', '->', '->>', '-?>',
        '-?>>', '/=', 'and', 'as->', 'as-macro', 'as?->',
        'assert', 'case', 'catseq', 'chr', 'comment', 'compif',
        'comptime', 'compwhen', 'cond', 'coro', 'def-',
        'default', 'defdyn', 'defer', 'defmacro', 'defmacro-',
        'defn', 'defn-', 'delay', 'doc', 'each', 'eachk',
        'eachp', 'edefer', 'ev/do-thread', 'ev/gather',
        'ev/spawn', 'ev/spawn-thread', 'ev/with-deadline',
        'ffi/defbind', 'fiber-fn', 'for', 'forever', 'forv',
        'generate', 'if-let', 'if-not', 'if-with', 'import',
        'juxt', 'label', 'let', 'loop', 'match', 'or', 'prompt',
        'protect', 'repeat', 'seq', 'short-fn', 'tabseq',
        'toggle', 'tracev', 'try', 'unless', 'use', 'var-',
        'varfn', 'when', 'when-let', 'when-with', 'with',
        'with-dyns', 'with-syms', 'with-vars',
        # obsolete builtin macros
        'eachy'
    )

    builtin_functions = (
        '%', '*', '+', '-', '/', '<', '<=', '=', '>', '>=',
        'abstract?', 'accumulate', 'accumulate2', 'all',
        'all-bindings', 'all-dynamics', 'any?', 'apply',
        'array', 'array/clear', 'array/concat', 'array/ensure',
        'array/fill', 'array/insert', 'array/new',
        'array/new-filled', 'array/peek', 'array/pop',
        'array/push', 'array/remove', 'array/slice',
        'array/trim', 'array/weak', 'array?', 'asm',
        'bad-compile', 'bad-parse', 'band', 'blshift', 'bnot',
        'boolean?', 'bor', 'brshift', 'brushift', 'buffer',
        'buffer/bit', 'buffer/bit-clear', 'buffer/bit-set',
        'buffer/bit-toggle', 'buffer/blit', 'buffer/clear',
        'buffer/fill', 'buffer/format', 'buffer/from-bytes',
        'buffer/new', 'buffer/new-filled', 'buffer/popn',
        'buffer/push', 'buffer/push-at', 'buffer/push-byte',
        'buffer/push-string', 'buffer/push-word',
        'buffer/slice', 'buffer/trim', 'buffer?', 'bxor',
        'bytes?', 'cancel', 'cfunction?', 'cli-main', 'cmp',
        'comp', 'compare', 'compare<', 'compare<=', 'compare=',
        'compare>', 'compare>=', 'compile', 'complement',
        'count', 'curenv', 'debug', 'debug/arg-stack',
        'debug/break', 'debug/fbreak', 'debug/lineage',
        'debug/stack', 'debug/stacktrace', 'debug/step',
        'debug/unbreak', 'debug/unfbreak', 'debugger',
        'debugger-on-status', 'dec', 'deep-not=', 'deep=',
        'defglobal', 'describe', 'dictionary?', 'disasm',
        'distinct', 'div', 'doc*', 'doc-format', 'doc-of',
        'dofile', 'drop', 'drop-until', 'drop-while', 'dyn',
        'eflush', 'empty?', 'env-lookup', 'eprin', 'eprinf',
        'eprint', 'eprintf', 'error', 'errorf',
        'ev/acquire-lock', 'ev/acquire-rlock',
        'ev/acquire-wlock', 'ev/all-tasks', 'ev/call',
        'ev/cancel', 'ev/capacity', 'ev/chan', 'ev/chan-close',
        'ev/chunk', 'ev/close', 'ev/count', 'ev/deadline',
        'ev/full', 'ev/give', 'ev/give-supervisor', 'ev/go',
        'ev/lock', 'ev/read', 'ev/release-lock',
        'ev/release-rlock', 'ev/release-wlock', 'ev/rselect',
        'ev/rwlock', 'ev/select', 'ev/sleep', 'ev/take',
        'ev/thread', 'ev/thread-chan', 'ev/write', 'eval',
        'eval-string', 'even?', 'every?', 'extreme', 'false?',
        'ffi/align', 'ffi/call', 'ffi/calling-conventions',
        'ffi/close', 'ffi/context', 'ffi/free', 'ffi/jitfn',
        'ffi/lookup', 'ffi/malloc', 'ffi/native',
        'ffi/pointer-buffer', 'ffi/pointer-cfunction',
        'ffi/read', 'ffi/signature', 'ffi/size', 'ffi/struct',
        'ffi/trampoline', 'ffi/write', 'fiber/can-resume?',
        'fiber/current', 'fiber/getenv', 'fiber/last-value',
        'fiber/maxstack', 'fiber/new', 'fiber/root',
        'fiber/setenv', 'fiber/setmaxstack', 'fiber/status',
        'fiber?', 'file/close', 'file/flush', 'file/lines',
        'file/open', 'file/read', 'file/seek', 'file/tell',
        'file/temp', 'file/write', 'filter', 'find',
        'find-index', 'first', 'flatten', 'flatten-into',
        'flush', 'flycheck', 'freeze', 'frequencies',
        'from-pairs', 'function?', 'gccollect', 'gcinterval',
        'gcsetinterval', 'gensym', 'get', 'get-in', 'getline',
        'getproto', 'group-by', 'has-key?', 'has-value?',
        'hash', 'idempotent?', 'identity', 'import*', 'in',
        'inc', 'index-of', 'indexed?', 'int/s64',
        'int/to-bytes', 'int/to-number', 'int/u64', 'int?',
        'interleave', 'interpose', 'invert', 'juxt*', 'keep',
        'keep-syntax', 'keep-syntax!', 'keys', 'keyword',
        'keyword/slice', 'keyword?', 'kvs', 'last', 'length',
        'lengthable?', 'load-image', 'macex', 'macex1',
        'maclintf', 'make-env', 'make-image', 'map', 'mapcat',
        'marshal', 'math/abs', 'math/acos', 'math/acosh',
        'math/asin', 'math/asinh', 'math/atan', 'math/atan2',
        'math/atanh', 'math/cbrt', 'math/ceil', 'math/cos',
        'math/cosh', 'math/erf', 'math/erfc', 'math/exp',
        'math/exp2', 'math/expm1', 'math/floor', 'math/gamma',
        'math/gcd', 'math/hypot', 'math/lcm', 'math/log',
        'math/log-gamma', 'math/log10', 'math/log1p',
        'math/log2', 'math/next', 'math/pow', 'math/random',
        'math/rng', 'math/rng-buffer', 'math/rng-int',
        'math/rng-uniform', 'math/round', 'math/seedrandom',
        'math/sin', 'math/sinh', 'math/sqrt', 'math/tan',
        'math/tanh', 'math/trunc', 'max', 'max-of', 'mean',
        'memcmp', 'merge', 'merge-into', 'merge-module', 'min',
        'min-of', 'mod', 'module/add-paths',
        'module/expand-path', 'module/find', 'module/value',
        'nan?', 'nat?', 'native', 'neg?', 'net/accept',
        'net/accept-loop', 'net/address', 'net/address-unpack',
        'net/chunk', 'net/close', 'net/connect', 'net/flush',
        'net/listen', 'net/localname', 'net/peername',
        'net/read', 'net/recv-from', 'net/send-to',
        'net/server', 'net/setsockopt', 'net/shutdown',
        'net/write', 'next', 'nil?', 'not', 'not=', 'number?',
        'odd?', 'one?', 'os/arch', 'os/cd', 'os/chmod',
        'os/clock', 'os/compiler', 'os/cpu-count',
        'os/cryptorand', 'os/cwd', 'os/date', 'os/dir',
        'os/environ', 'os/execute', 'os/exit', 'os/getenv',
        'os/isatty', 'os/link', 'os/lstat', 'os/mkdir',
        'os/mktime', 'os/open', 'os/perm-int', 'os/perm-string',
        'os/pipe', 'os/posix-exec', 'os/posix-fork',
        'os/proc-close', 'os/proc-kill', 'os/proc-wait',
        'os/readlink', 'os/realpath', 'os/rename', 'os/rm',
        'os/rmdir', 'os/setenv', 'os/shell', 'os/sigaction',
        'os/sleep', 'os/spawn', 'os/stat', 'os/strftime',
        'os/symlink', 'os/time', 'os/touch', 'os/umask',
        'os/which', 'pairs', 'parse', 'parse-all',
        'parser/byte', 'parser/clone', 'parser/consume',
        'parser/eof', 'parser/error', 'parser/flush',
        'parser/has-more', 'parser/insert', 'parser/new',
        'parser/produce', 'parser/state', 'parser/status',
        'parser/where', 'partial', 'partition', 'partition-by',
        'peg/compile', 'peg/find', 'peg/find-all', 'peg/match',
        'peg/replace', 'peg/replace-all', 'pos?', 'postwalk',
        'pp', 'prewalk', 'prin', 'prinf', 'print', 'printf',
        'product', 'propagate', 'put', 'put-in', 'quit',
        'range', 'reduce', 'reduce2', 'repl', 'require',
        'resume', 'return', 'reverse', 'reverse!',
        'run-context', 'sandbox', 'scan-number', 'setdyn',
        'signal', 'slice', 'slurp', 'some', 'sort', 'sort-by',
        'sorted', 'sorted-by', 'spit', 'string',
        'string/ascii-lower', 'string/ascii-upper',
        'string/bytes', 'string/check-set', 'string/find',
        'string/find-all', 'string/format', 'string/from-bytes',
        'string/has-prefix?', 'string/has-suffix?',
        'string/join', 'string/repeat', 'string/replace',
        'string/replace-all', 'string/reverse', 'string/slice',
        'string/split', 'string/trim', 'string/triml',
        'string/trimr', 'string?', 'struct', 'struct/getproto',
        'struct/proto-flatten', 'struct/to-table',
        'struct/with-proto', 'struct?', 'sum', 'symbol',
        'symbol/slice', 'symbol?', 'table', 'table/clear',
        'table/clone', 'table/getproto', 'table/new',
        'table/proto-flatten', 'table/rawget', 'table/setproto',
        'table/to-struct', 'table/weak', 'table/weak-keys',
        'table/weak-values', 'table?', 'take', 'take-until',
        'take-while', 'thaw', 'trace', 'true?', 'truthy?',
        'tuple', 'tuple/brackets', 'tuple/setmap',
        'tuple/slice', 'tuple/sourcemap', 'tuple/type',
        'tuple?', 'type', 'unmarshal', 'untrace', 'update',
        'update-in', 'values', 'varglobal', 'walk',
        'warn-compile', 'xprin', 'xprinf', 'xprint', 'xprintf',
        'yield', 'zero?', 'zipcoll',
        # obsolete builtin functions
        'tarray/buffer', 'tarray/copy-bytes', 'tarray/length',
        'tarray/new', 'tarray/properties', 'tarray/slice',
        'tarray/swap-bytes', 'thread/close', 'thread/current',
        'thread/exit', 'thread/new', 'thread/receive',
        'thread/send'
    )

    builtin_variables = (
        'debugger-env', 'default-peg-grammar', 'janet/build',
        'janet/config-bits', 'janet/version', 'load-image-dict',
        'make-image-dict', 'math/-inf', 'math/e', 'math/inf',
        'math/int-max', 'math/int-min', 'math/int32-max',
        'math/int32-min', 'math/nan', 'math/pi', 'module/cache',
        'module/loaders', 'module/loading', 'module/paths',
        'root-env', 'stderr', 'stdin', 'stdout'
    )

    constants = (
        'false', 'nil', 'true'
    )

    # XXX: this form not usable to pass to `suffix=`
    #_token_end = r'''
    #  (?=            # followed by one of:
    #      \s           # whitespace
    #    | \#           # comment
    #    | [)\]]        # end delimiters
    #    | $            # end of file
    #  )
    #'''

    # ...so, express it like this
    _token_end = r'(?=\s|#|[)\]]|$)'

    _first_char = r'[a-zA-Z!$%&*+\-./<=>?@^_]'
    _rest_char = rf'([0-9:]|{_first_char})'

    valid_name = rf'{_first_char}({_rest_char})*'

    _radix_unit = r'[0-9a-zA-Z][0-9a-zA-Z_]*'

    # exponent marker, optional sign, one or more alphanumeric
    _radix_exp = r'&[+-]?[0-9a-zA-Z]+'

    # 2af3__bee_
    _hex_unit = r'[0-9a-fA-F][0-9a-fA-F_]*'

    # 12_000__
    _dec_unit = r'[0-9][0-9_]*'

    # E-23
    # lower or uppercase e, optional sign, one or more digits
    _dec_exp = r'[eE][+-]?[0-9]+'

    tokens = {
        'root': [
            (r'#.*$', Comment.Single),

            (r'\s+', Whitespace),

            # radix number
            (rf'''(?x)
                  [+-]? [0-9]{{1,2}} r {_radix_unit} \. ({_radix_unit})?
                  ({_radix_exp})?
               ''',
             Number),

            (rf'''(?x)
                  [+-]? [0-9]{{1,2}} r (\.)? {_radix_unit}
                  ({_radix_exp})?
               ''',
             Number),

            # hex number
            (rf'(?x) [+-]? 0x {_hex_unit} \. ({_hex_unit})?',
             Number.Hex),

            (rf'(?x) [+-]? 0x (\.)? {_hex_unit}',
             Number.Hex),

            # decimal number
            (rf'(?x) [+-]? {_dec_unit} \. ({_dec_unit})? ({_dec_exp})?',
             Number.Float),

            (rf'(?x) [+-]? (\.)? {_dec_unit} ({_dec_exp})?',
             Number.Float),

            # strings and buffers
            (r'@?"', String, 'string'),

            # long-strings and long-buffers
            #
            #   non-empty content enclosed by a pair of n-backticks
            #   with optional leading @
            (r'@?(`+)(.|\n)+?\1', String),

            # things that hang out on front
            #
            #   ' ~ , ; |
            (r"['~,;|]", Operator),

            # collection delimiters
            #
            #   @( ( )
            #   @[ [ ]
            #   @{ { }
            (r'@?[(\[{]|[)\]}]', Punctuation),

            # constants
            (words(constants, suffix=_token_end), Keyword.Constants),

            # keywords
            (rf'(:({_rest_char})+|:)', Name.Constant),

            # symbols
            (words(builtin_variables, suffix=_token_end),
             Name.Variable.Global),

            (words(special_forms, prefix=r'(?<=\()', suffix=_token_end),
             Keyword.Reserved),

            (words(builtin_macros, prefix=r'(?<=\()', suffix=_token_end),
             Name.Builtin),

            (words(builtin_functions, prefix=r'(?<=\()', suffix=_token_end),
             Name.Function),

            # other symbols
            (valid_name, Name.Variable),
        ],
        'string': [
            (r'\\(u[0-9a-fA-F]{4}|U[0-9a-fA-F]{6})', String.Escape),
            (r'\\x[0-9a-fA-F]{2}', String.Escape),
            (r'\\.', String.Escape),
            (r'"', String, '#pop'),
            (r'[^\\"]+', String),
        ]
    }

# === NexusCore/openenv\Lib\site-packages\click\core.py ===
from __future__ import annotations

import collections.abc as cabc
import enum
import errno
import inspect
import os
import sys
import typing as t
from collections import abc
from collections import Counter
from contextlib import AbstractContextManager
from contextlib import contextmanager
from contextlib import ExitStack
from functools import update_wrapper
from gettext import gettext as _
from gettext import ngettext
from itertools import repeat
from types import TracebackType

from . import types
from .exceptions import Abort
from .exceptions import BadParameter
from .exceptions import ClickException
from .exceptions import Exit
from .exceptions import MissingParameter
from .exceptions import NoArgsIsHelpError
from .exceptions import UsageError
from .formatting import HelpFormatter
from .formatting import join_options
from .globals import pop_context
from .globals import push_context
from .parser import _flag_needs_value
from .parser import _OptionParser
from .parser import _split_opt
from .termui import confirm
from .termui import prompt
from .termui import style
from .utils import _detect_program_name
from .utils import _expand_args
from .utils import echo
from .utils import make_default_short_help
from .utils import make_str
from .utils import PacifyFlushWrapper

if t.TYPE_CHECKING:
    from .shell_completion import CompletionItem

F = t.TypeVar("F", bound="t.Callable[..., t.Any]")
V = t.TypeVar("V")


def _complete_visible_commands(
    ctx: Context, incomplete: str
) -> cabc.Iterator[tuple[str, Command]]:
    """List all the subcommands of a group that start with the
    incomplete value and aren't hidden.

    :param ctx: Invocation context for the group.
    :param incomplete: Value being completed. May be empty.
    """
    multi = t.cast(Group, ctx.command)

    for name in multi.list_commands(ctx):
        if name.startswith(incomplete):
            command = multi.get_command(ctx, name)

            if command is not None and not command.hidden:
                yield name, command


def _check_nested_chain(
    base_command: Group, cmd_name: str, cmd: Command, register: bool = False
) -> None:
    if not base_command.chain or not isinstance(cmd, Group):
        return

    if register:
        message = (
            f"It is not possible to add the group {cmd_name!r} to another"
            f" group {base_command.name!r} that is in chain mode."
        )
    else:
        message = (
            f"Found the group {cmd_name!r} as subcommand to another group "
            f" {base_command.name!r} that is in chain mode. This is not supported."
        )

    raise RuntimeError(message)


def batch(iterable: cabc.Iterable[V], batch_size: int) -> list[tuple[V, ...]]:
    return list(zip(*repeat(iter(iterable), batch_size), strict=False))


@contextmanager
def augment_usage_errors(
    ctx: Context, param: Parameter | None = None
) -> cabc.Iterator[None]:
    """Context manager that attaches extra information to exceptions."""
    try:
        yield
    except BadParameter as e:
        if e.ctx is None:
            e.ctx = ctx
        if param is not None and e.param is None:
            e.param = param
        raise
    except UsageError as e:
        if e.ctx is None:
            e.ctx = ctx
        raise


def iter_params_for_processing(
    invocation_order: cabc.Sequence[Parameter],
    declaration_order: cabc.Sequence[Parameter],
) -> list[Parameter]:
    """Returns all declared parameters in the order they should be processed.

    The declared parameters are re-shuffled depending on the order in which
    they were invoked, as well as the eagerness of each parameters.

    The invocation order takes precedence over the declaration order. I.e. the
    order in which the user provided them to the CLI is respected.

    This behavior and its effect on callback evaluation is detailed at:
    https://click.palletsprojects.com/en/stable/advanced/#callback-evaluation-order
    """

    def sort_key(item: Parameter) -> tuple[bool, float]:
        try:
            idx: float = invocation_order.index(item)
        except ValueError:
            idx = float("inf")

        return not item.is_eager, idx

    return sorted(declaration_order, key=sort_key)


class ParameterSource(enum.Enum):
    """This is an :class:`~enum.Enum` that indicates the source of a
    parameter's value.

    Use :meth:`click.Context.get_parameter_source` to get the
    source for a parameter by name.

    .. versionchanged:: 8.0
        Use :class:`~enum.Enum` and drop the ``validate`` method.

    .. versionchanged:: 8.0
        Added the ``PROMPT`` value.
    """

    COMMANDLINE = enum.auto()
    """The value was provided by the command line args."""
    ENVIRONMENT = enum.auto()
    """The value was provided with an environment variable."""
    DEFAULT = enum.auto()
    """Used the default specified by the parameter."""
    DEFAULT_MAP = enum.auto()
    """Used a default provided by :attr:`Context.default_map`."""
    PROMPT = enum.auto()
    """Used a prompt to confirm a default or provide a value."""


class Context:
    """The context is a special internal object that holds state relevant
    for the script execution at every single level.  It's normally invisible
    to commands unless they opt-in to getting access to it.

    The context is useful as it can pass internal objects around and can
    control special execution features such as reading data from
    environment variables.

    A context can be used as context manager in which case it will call
    :meth:`close` on teardown.

    :param command: the command class for this context.
    :param parent: the parent context.
    :param info_name: the info name for this invocation.  Generally this
                      is the most descriptive name for the script or
                      command.  For the toplevel script it is usually
                      the name of the script, for commands below it it's
                      the name of the script.
    :param obj: an arbitrary object of user data.
    :param auto_envvar_prefix: the prefix to use for automatic environment
                               variables.  If this is `None` then reading
                               from environment variables is disabled.  This
                               does not affect manually set environment
                               variables which are always read.
    :param default_map: a dictionary (like object) with default values
                        for parameters.
    :param terminal_width: the width of the terminal.  The default is
                           inherit from parent context.  If no context
                           defines the terminal width then auto
                           detection will be applied.
    :param max_content_width: the maximum width for content rendered by
                              Click (this currently only affects help
                              pages).  This defaults to 80 characters if
                              not overridden.  In other words: even if the
                              terminal is larger than that, Click will not
                              format things wider than 80 characters by
                              default.  In addition to that, formatters might
                              add some safety mapping on the right.
    :param resilient_parsing: if this flag is enabled then Click will
                              parse without any interactivity or callback
                              invocation.  Default values will also be
                              ignored.  This is useful for implementing
                              things such as completion support.
    :param allow_extra_args: if this is set to `True` then extra arguments
                             at the end will not raise an error and will be
                             kept on the context.  The default is to inherit
                             from the command.
    :param allow_interspersed_args: if this is set to `False` then options
                                    and arguments cannot be mixed.  The
                                    default is to inherit from the command.
    :param ignore_unknown_options: instructs click to ignore options it does
                                   not know and keeps them for later
                                   processing.
    :param help_option_names: optionally a list of strings that define how
                              the default help parameter is named.  The
                              default is ``['--help']``.
    :param token_normalize_func: an optional function that is used to
                                 normalize tokens (options, choices,
                                 etc.).  This for instance can be used to
                                 implement case insensitive behavior.
    :param color: controls if the terminal supports ANSI colors or not.  The
                  default is autodetection.  This is only needed if ANSI
                  codes are used in texts that Click prints which is by
                  default not the case.  This for instance would affect
                  help output.
    :param show_default: Show the default value for commands. If this
        value is not set, it defaults to the value from the parent
        context. ``Command.show_default`` overrides this default for the
        specific command.

    .. versionchanged:: 8.2
        The ``protected_args`` attribute is deprecated and will be removed in
        Click 9.0. ``args`` will contain remaining unparsed tokens.

    .. versionchanged:: 8.1
        The ``show_default`` parameter is overridden by
        ``Command.show_default``, instead of the other way around.

    .. versionchanged:: 8.0
        The ``show_default`` parameter defaults to the value from the
        parent context.

    .. versionchanged:: 7.1
       Added the ``show_default`` parameter.

    .. versionchanged:: 4.0
        Added the ``color``, ``ignore_unknown_options``, and
        ``max_content_width`` parameters.

    .. versionchanged:: 3.0
        Added the ``allow_extra_args`` and ``allow_interspersed_args``
        parameters.

    .. versionchanged:: 2.0
        Added the ``resilient_parsing``, ``help_option_names``, and
        ``token_normalize_func`` parameters.
    """

    #: The formatter class to create with :meth:`make_formatter`.
    #:
    #: .. versionadded:: 8.0
    formatter_class: type[HelpFormatter] = HelpFormatter

    def __init__(
        self,
        command: Command,
        parent: Context | None = None,
        info_name: str | None = None,
        obj: t.Any | None = None,
        auto_envvar_prefix: str | None = None,
        default_map: cabc.MutableMapping[str, t.Any] | None = None,
        terminal_width: int | None = None,
        max_content_width: int | None = None,
        resilient_parsing: bool = False,
        allow_extra_args: bool | None = None,
        allow_interspersed_args: bool | None = None,
        ignore_unknown_options: bool | None = None,
        help_option_names: list[str] | None = None,
        token_normalize_func: t.Callable[[str], str] | None = None,
        color: bool | None = None,
        show_default: bool | None = None,
    ) -> None:
        #: the parent context or `None` if none exists.
        self.parent = parent
        #: the :class:`Command` for this context.
        self.command = command
        #: the descriptive information name
        self.info_name = info_name
        #: Map of parameter names to their parsed values. Parameters
        #: with ``expose_value=False`` are not stored.
        self.params: dict[str, t.Any] = {}
        #: the leftover arguments.
        self.args: list[str] = []
        #: protected arguments.  These are arguments that are prepended
        #: to `args` when certain parsing scenarios are encountered but
        #: must be never propagated to another arguments.  This is used
        #: to implement nested parsing.
        self._protected_args: list[str] = []
        #: the collected prefixes of the command's options.
        self._opt_prefixes: set[str] = set(parent._opt_prefixes) if parent else set()

        if obj is None and parent is not None:
            obj = parent.obj

        #: the user object stored.
        self.obj: t.Any = obj
        self._meta: dict[str, t.Any] = getattr(parent, "meta", {})

        #: A dictionary (-like object) with defaults for parameters.
        if (
            default_map is None
            and info_name is not None
            and parent is not None
            and parent.default_map is not None
        ):
            default_map = parent.default_map.get(info_name)

        self.default_map: cabc.MutableMapping[str, t.Any] | None = default_map

        #: This flag indicates if a subcommand is going to be executed. A
        #: group callback can use this information to figure out if it's
        #: being executed directly or because the execution flow passes
        #: onwards to a subcommand. By default it's None, but it can be
        #: the name of the subcommand to execute.
        #:
        #: If chaining is enabled this will be set to ``'*'`` in case
        #: any commands are executed.  It is however not possible to
        #: figure out which ones.  If you require this knowledge you
        #: should use a :func:`result_callback`.
        self.invoked_subcommand: str | None = None

        if terminal_width is None and parent is not None:
            terminal_width = parent.terminal_width

        #: The width of the terminal (None is autodetection).
        self.terminal_width: int | None = terminal_width

        if max_content_width is None and parent is not None:
            max_content_width = parent.max_content_width

        #: The maximum width of formatted content (None implies a sensible
        #: default which is 80 for most things).
        self.max_content_width: int | None = max_content_width

        if allow_extra_args is None:
            allow_extra_args = command.allow_extra_args

        #: Indicates if the context allows extra args or if it should
        #: fail on parsing.
        #:
        #: .. versionadded:: 3.0
        self.allow_extra_args = allow_extra_args

        if allow_interspersed_args is None:
            allow_interspersed_args = command.allow_interspersed_args

        #: Indicates if the context allows mixing of arguments and
        #: options or not.
        #:
        #: .. versionadded:: 3.0
        self.allow_interspersed_args: bool = allow_interspersed_args

        if ignore_unknown_options is None:
            ignore_unknown_options = command.ignore_unknown_options

        #: Instructs click to ignore options that a command does not
        #: understand and will store it on the context for later
        #: processing.  This is primarily useful for situations where you
        #: want to call into external programs.  Generally this pattern is
        #: strongly discouraged because it's not possibly to losslessly
        #: forward all arguments.
        #:
        #: .. versionadded:: 4.0
        self.ignore_unknown_options: bool = ignore_unknown_options

        if help_option_names is None:
            if parent is not None:
                help_option_names = parent.help_option_names
            else:
                help_option_names = ["--help"]

        #: The names for the help options.
        self.help_option_names: list[str] = help_option_names

        if token_normalize_func is None and parent is not None:
            token_normalize_func = parent.token_normalize_func

        #: An optional normalization function for tokens.  This is
        #: options, choices, commands etc.
        self.token_normalize_func: t.Callable[[str], str] | None = token_normalize_func

        #: Indicates if resilient parsing is enabled.  In that case Click
        #: will do its best to not cause any failures and default values
        #: will be ignored. Useful for completion.
        self.resilient_parsing: bool = resilient_parsing

        # If there is no envvar prefix yet, but the parent has one and
        # the command on this level has a name, we can expand the envvar
        # prefix automatically.
        if auto_envvar_prefix is None:
            if (
                parent is not None
                and parent.auto_envvar_prefix is not None
                and self.info_name is not None
            ):
                auto_envvar_prefix = (
                    f"{parent.auto_envvar_prefix}_{self.info_name.upper()}"
                )
        else:
            auto_envvar_prefix = auto_envvar_prefix.upper()

        if auto_envvar_prefix is not None:
            auto_envvar_prefix = auto_envvar_prefix.replace("-", "_")

        self.auto_envvar_prefix: str | None = auto_envvar_prefix

        if color is None and parent is not None:
            color = parent.color

        #: Controls if styling output is wanted or not.
        self.color: bool | None = color

        if show_default is None and parent is not None:
            show_default = parent.show_default

        #: Show option default values when formatting help text.
        self.show_default: bool | None = show_default

        self._close_callbacks: list[t.Callable[[], t.Any]] = []
        self._depth = 0
        self._parameter_source: dict[str, ParameterSource] = {}
        self._exit_stack = ExitStack()

    @property
    def protected_args(self) -> list[str]:
        import warnings

        warnings.warn(
            "'protected_args' is deprecated and will be removed in Click 9.0."
            " 'args' will contain remaining unparsed tokens.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._protected_args

    def to_info_dict(self) -> dict[str, t.Any]:
        """Gather information that could be useful for a tool generating
        user-facing documentation. This traverses the entire CLI
        structure.

        .. code-block:: python

            with Context(cli) as ctx:
                info = ctx.to_info_dict()

        .. versionadded:: 8.0
        """
        return {
            "command": self.command.to_info_dict(self),
            "info_name": self.info_name,
            "allow_extra_args": self.allow_extra_args,
            "allow_interspersed_args": self.allow_interspersed_args,
            "ignore_unknown_options": self.ignore_unknown_options,
            "auto_envvar_prefix": self.auto_envvar_prefix,
        }

    def __enter__(self) -> Context:
        self._depth += 1
        push_context(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._depth -= 1
        if self._depth == 0:
            self.close()
        pop_context()

    @contextmanager
    def scope(self, cleanup: bool = True) -> cabc.Iterator[Context]:
        """This helper method can be used with the context object to promote
        it to the current thread local (see :func:`get_current_context`).
        The default behavior of this is to invoke the cleanup functions which
        can be disabled by setting `cleanup` to `False`.  The cleanup
        functions are typically used for things such as closing file handles.

        If the cleanup is intended the context object can also be directly
        used as a context manager.

        Example usage::

            with ctx.scope():
                assert get_current_context() is ctx

        This is equivalent::

            with ctx:
                assert get_current_context() is ctx

        .. versionadded:: 5.0

        :param cleanup: controls if the cleanup functions should be run or
                        not.  The default is to run these functions.  In
                        some situations the context only wants to be
                        temporarily pushed in which case this can be disabled.
                        Nested pushes automatically defer the cleanup.
        """
        if not cleanup:
            self._depth += 1
        try:
            with self as rv:
                yield rv
        finally:
            if not cleanup:
                self._depth -= 1

    @property
    def meta(self) -> dict[str, t.Any]:
        """This is a dictionary which is shared with all the contexts
        that are nested.  It exists so that click utilities can store some
        state here if they need to.  It is however the responsibility of
        that code to manage this dictionary well.

        The keys are supposed to be unique dotted strings.  For instance
        module paths are a good choice for it.  What is stored in there is
        irrelevant for the operation of click.  However what is important is
        that code that places data here adheres to the general semantics of
        the system.

        Example usage::

            LANG_KEY = f'{__name__}.lang'

            def set_language(value):
                ctx = get_current_context()
                ctx.meta[LANG_KEY] = value

            def get_language():
                return get_current_context().meta.get(LANG_KEY, 'en_US')

        .. versionadded:: 5.0
        """
        return self._meta

    def make_formatter(self) -> HelpFormatter:
        """Creates the :class:`~click.HelpFormatter` for the help and
        usage output.

        To quickly customize the formatter class used without overriding
        this method, set the :attr:`formatter_class` attribute.

        .. versionchanged:: 8.0
            Added the :attr:`formatter_class` attribute.
        """
        return self.formatter_class(
            width=self.terminal_width, max_width=self.max_content_width
        )

    def with_resource(self, context_manager: AbstractContextManager[V]) -> V:
        """Register a resource as if it were used in a ``with``
        statement. The resource will be cleaned up when the context is
        popped.

        Uses :meth:`contextlib.ExitStack.enter_context`. It calls the
        resource's ``__enter__()`` method and returns the result. When
        the context is popped, it closes the stack, which calls the
        resource's ``__exit__()`` method.

        To register a cleanup function for something that isn't a
        context manager, use :meth:`call_on_close`. Or use something
        from :mod:`contextlib` to turn it into a context manager first.

        .. code-block:: python

            @click.group()
            @click.option("--name")
            @click.pass_context
            def cli(ctx):
                ctx.obj = ctx.with_resource(connect_db(name))

        :param context_manager: The context manager to enter.
        :return: Whatever ``context_manager.__enter__()`` returns.

        .. versionadded:: 8.0
        """
        return self._exit_stack.enter_context(context_manager)

    def call_on_close(self, f: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
        """Register a function to be called when the context tears down.

        This can be used to close resources opened during the script
        execution. Resources that support Python's context manager
        protocol which would be used in a ``with`` statement should be
        registered with :meth:`with_resource` instead.

        :param f: The function to execute on teardown.
        """
        return self._exit_stack.callback(f)

    def close(self) -> None:
        """Invoke all close callbacks registered with
        :meth:`call_on_close`, and exit all context managers entered
        with :meth:`with_resource`.
        """
        self._exit_stack.close()
        # In case the context is reused, create a new exit stack.
        self._exit_stack = ExitStack()

    @property
    def command_path(self) -> str:
        """The computed command path.  This is used for the ``usage``
        information on the help page.  It's automatically created by
        combining the info names of the chain of contexts to the root.
        """
        rv = ""
        if self.info_name is not None:
            rv = self.info_name
        if self.parent is not None:
            parent_command_path = [self.parent.command_path]

            if isinstance(self.parent.command, Command):
                for param in self.parent.command.get_params(self):
                    parent_command_path.extend(param.get_usage_pieces(self))

            rv = f"{' '.join(parent_command_path)} {rv}"
        return rv.lstrip()

    def find_root(self) -> Context:
        """Finds the outermost context."""
        node = self
        while node.parent is not None:
            node = node.parent
        return node

    def find_object(self, object_type: type[V]) -> V | None:
        """Finds the closest object of a given type."""
        node: Context | None = self

        while node is not None:
            if isinstance(node.obj, object_type):
                return node.obj

            node = node.parent

        return None

    def ensure_object(self, object_type: type[V]) -> V:
        """Like :meth:`find_object` but sets the innermost object to a
        new instance of `object_type` if it does not exist.
        """
        rv = self.find_object(object_type)
        if rv is None:
            self.obj = rv = object_type()
        return rv

    @t.overload
    def lookup_default(
        self, name: str, call: t.Literal[True] = True
    ) -> t.Any | None: ...

    @t.overload
    def lookup_default(
        self, name: str, call: t.Literal[False] = ...
    ) -> t.Any | t.Callable[[], t.Any] | None: ...

    def lookup_default(self, name: str, call: bool = True) -> t.Any | None:
        """Get the default for a parameter from :attr:`default_map`.

        :param name: Name of the parameter.
        :param call: If the default is a callable, call it. Disable to
            return the callable instead.

        .. versionchanged:: 8.0
            Added the ``call`` parameter.
        """
        if self.default_map is not None:
            value = self.default_map.get(name)

            if call and callable(value):
                return value()

            return value

        return None

    def fail(self, message: str) -> t.NoReturn:
        """Aborts the execution of the program with a specific error
        message.

        :param message: the error message to fail with.
        """
        raise UsageError(message, self)

    def abort(self) -> t.NoReturn:
        """Aborts the script."""
        raise Abort()

    def exit(self, code: int = 0) -> t.NoReturn:
        """Exits the application with a given exit code.

        .. versionchanged:: 8.2
            Callbacks and context managers registered with :meth:`call_on_close`
            and :meth:`with_resource` are closed before exiting.
        """
        self.close()
        raise Exit(code)

    def get_usage(self) -> str:
        """Helper method to get formatted usage string for the current
        context and command.
        """
        return self.command.get_usage(self)

    def get_help(self) -> str:
        """Helper method to get formatted help page for the current
        context and command.
        """
        return self.command.get_help(self)

    def _make_sub_context(self, command: Command) -> Context:
        """Create a new context of the same type as this context, but
        for a new command.

        :meta private:
        """
        return type(self)(command, info_name=command.name, parent=self)

    @t.overload
    def invoke(
        self, callback: t.Callable[..., V], /, *args: t.Any, **kwargs: t.Any
    ) -> V: ...

    @t.overload
    def invoke(self, callback: Command, /, *args: t.Any, **kwargs: t.Any) -> t.Any: ...

    def invoke(
        self, callback: Command | t.Callable[..., V], /, *args: t.Any, **kwargs: t.Any
    ) -> t.Any | V:
        """Invokes a command callback in exactly the way it expects.  There
        are two ways to invoke this method:

        1.  the first argument can be a callback and all other arguments and
            keyword arguments are forwarded directly to the function.
        2.  the first argument is a click command object.  In that case all
            arguments are forwarded as well but proper click parameters
            (options and click arguments) must be keyword arguments and Click
            will fill in defaults.

        .. versionchanged:: 8.0
            All ``kwargs`` are tracked in :attr:`params` so they will be
            passed if :meth:`forward` is called at multiple levels.

        .. versionchanged:: 3.2
            A new context is created, and missing arguments use default values.
        """
        if isinstance(callback, Command):
            other_cmd = callback

            if other_cmd.callback is None:
                raise TypeError(
                    "The given command does not have a callback that can be invoked."
                )
            else:
                callback = t.cast("t.Callable[..., V]", other_cmd.callback)

            ctx = self._make_sub_context(other_cmd)

            for param in other_cmd.params:
                if param.name not in kwargs and param.expose_value:
                    kwargs[param.name] = param.type_cast_value(  # type: ignore
                        ctx, param.get_default(ctx)
                    )

            # Track all kwargs as params, so that forward() will pass
            # them on in subsequent calls.
            ctx.params.update(kwargs)
        else:
            ctx = self

        with augment_usage_errors(self):
            with ctx:
                return callback(*args, **kwargs)

    def forward(self, cmd: Command, /, *args: t.Any, **kwargs: t.Any) -> t.Any:
        """Similar to :meth:`invoke` but fills in default keyword
        arguments from the current context if the other command expects
        it.  This cannot invoke callbacks directly, only other commands.

        .. versionchanged:: 8.0
            All ``kwargs`` are tracked in :attr:`params` so they will be
            passed if ``forward`` is called at multiple levels.
        """
        # Can only forward to other commands, not direct callbacks.
        if not isinstance(cmd, Command):
            raise TypeError("Callback is not a command.")

        for param in self.params:
            if param not in kwargs:
                kwargs[param] = self.params[param]

        return self.invoke(cmd, *args, **kwargs)

    def set_parameter_source(self, name: str, source: ParameterSource) -> None:
        """Set the source of a parameter. This indicates the location
        from which the value of the parameter was obtained.

        :param name: The name of the parameter.
        :param source: A member of :class:`~click.core.ParameterSource`.
        """
        self._parameter_source[name] = source

    def get_parameter_source(self, name: str) -> ParameterSource | None:
        """Get the source of a parameter. This indicates the location
        from which the value of the parameter was obtained.

        This can be useful for determining when a user specified a value
        on the command line that is the same as the default value. It
        will be :attr:`~click.core.ParameterSource.DEFAULT` only if the
        value was actually taken from the default.

        :param name: The name of the parameter.
        :rtype: ParameterSource

        .. versionchanged:: 8.0
            Returns ``None`` if the parameter was not provided from any
            source.
        """
        return self._parameter_source.get(name)


class Command:
    """Commands are the basic building block of command line interfaces in
    Click.  A basic command handles command line parsing and might dispatch
    more parsing to commands nested below it.

    :param name: the name of the command to use unless a group overrides it.
    :param context_settings: an optional dictionary with defaults that are
                             passed to the context object.
    :param callback: the callback to invoke.  This is optional.
    :param params: the parameters to register with this command.  This can
                   be either :class:`Option` or :class:`Argument` objects.
    :param help: the help string to use for this command.
    :param epilog: like the help string but it's printed at the end of the
                   help page after everything else.
    :param short_help: the short help to use for this command.  This is
                       shown on the command listing of the parent command.
    :param add_help_option: by default each command registers a ``--help``
                            option.  This can be disabled by this parameter.
    :param no_args_is_help: this controls what happens if no arguments are
                            provided.  This option is disabled by default.
                            If enabled this will add ``--help`` as argument
                            if no arguments are passed
    :param hidden: hide this command from help outputs.
    :param deprecated: If ``True`` or non-empty string, issues a message
                        indicating that the command is deprecated and highlights
                        its deprecation in --help. The message can be customized
                        by using a string as the value.

    .. versionchanged:: 8.2
        This is the base class for all commands, not ``BaseCommand``.
        ``deprecated`` can be set to a string as well to customize the
        deprecation message.

    .. versionchanged:: 8.1
        ``help``, ``epilog``, and ``short_help`` are stored unprocessed,
        all formatting is done when outputting help text, not at init,
        and is done even if not using the ``@command`` decorator.

    .. versionchanged:: 8.0
        Added a ``repr`` showing the command name.

    .. versionchanged:: 7.1
        Added the ``no_args_is_help`` parameter.

    .. versionchanged:: 2.0
        Added the ``context_settings`` parameter.
    """

    #: The context class to create with :meth:`make_context`.
    #:
    #: .. versionadded:: 8.0
    context_class: type[Context] = Context

    #: the default for the :attr:`Context.allow_extra_args` flag.
    allow_extra_args = False

    #: the default for the :attr:`Context.allow_interspersed_args` flag.
    allow_interspersed_args = True

    #: the default for the :attr:`Context.ignore_unknown_options` flag.
    ignore_unknown_options = False

    def __init__(
        self,
        name: str | None,
        context_settings: cabc.MutableMapping[str, t.Any] | None = None,
        callback: t.Callable[..., t.Any] | None = None,
        params: list[Parameter] | None = None,
        help: str | None = None,
        epilog: str | None = None,
        short_help: str | None = None,
        options_metavar: str | None = "[OPTIONS]",
        add_help_option: bool = True,
        no_args_is_help: bool = False,
        hidden: bool = False,
        deprecated: bool | str = False,
    ) -> None:
        #: the name the command thinks it has.  Upon registering a command
        #: on a :class:`Group` the group will default the command name
        #: with this information.  You should instead use the
        #: :class:`Context`\'s :attr:`~Context.info_name` attribute.
        self.name = name

        if context_settings is None:
            context_settings = {}

        #: an optional dictionary with defaults passed to the context.
        self.context_settings: cabc.MutableMapping[str, t.Any] = context_settings

        #: the callback to execute when the command fires.  This might be
        #: `None` in which case nothing happens.
        self.callback = callback
        #: the list of parameters for this command in the order they
        #: should show up in the help page and execute.  Eager parameters
        #: will automatically be handled before non eager ones.
        self.params: list[Parameter] = params or []
        self.help = help
        self.epilog = epilog
        self.options_metavar = options_metavar
        self.short_help = short_help
        self.add_help_option = add_help_option
        self._help_option = None
        self.no_args_is_help = no_args_is_help
        self.hidden = hidden
        self.deprecated = deprecated

    def to_info_dict(self, ctx: Context) -> dict[str, t.Any]:
        return {
            "name": self.name,
            "params": [param.to_info_dict() for param in self.get_params(ctx)],
            "help": self.help,
            "epilog": self.epilog,
            "short_help": self.short_help,
            "hidden": self.hidden,
            "deprecated": self.deprecated,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.name}>"

    def get_usage(self, ctx: Context) -> str:
        """Formats the usage line into a string and returns it.

        Calls :meth:`format_usage` internally.
        """
        formatter = ctx.make_formatter()
        self.format_usage(ctx, formatter)
        return formatter.getvalue().rstrip("\n")

    def get_params(self, ctx: Context) -> list[Parameter]:
        params = self.params
        help_option = self.get_help_option(ctx)

        if help_option is not None:
            params = [*params, help_option]

        if __debug__:
            import warnings

            opts = [opt for param in params for opt in param.opts]
            opts_counter = Counter(opts)
            duplicate_opts = (opt for opt, count in opts_counter.items() if count > 1)

            for duplicate_opt in duplicate_opts:
                warnings.warn(
                    (
                        f"The parameter {duplicate_opt} is used more than once. "
                        "Remove its duplicate as parameters should be unique."
                    ),
                    stacklevel=3,
                )

        return params

    def format_usage(self, ctx: Context, formatter: HelpFormatter) -> None:
        """Writes the usage line into the formatter.

        This is a low-level method called by :meth:`get_usage`.
        """
        pieces = self.collect_usage_pieces(ctx)
        formatter.write_usage(ctx.command_path, " ".join(pieces))

    def collect_usage_pieces(self, ctx: Context) -> list[str]:
        """Returns all the pieces that go into the usage line and returns
        it as a list of strings.
        """
        rv = [self.options_metavar] if self.options_metavar else []

        for param in self.get_params(ctx):
            rv.extend(param.get_usage_pieces(ctx))

        return rv

    def get_help_option_names(self, ctx: Context) -> list[str]:
        """Returns the names for the help option."""
        all_names = set(ctx.help_option_names)
        for param in self.params:
            all_names.difference_update(param.opts)
            all_names.difference_update(param.secondary_opts)
        return list(all_names)

    def get_help_option(self, ctx: Context) -> Option | None:
        """Returns the help option object.

        Skipped if :attr:`add_help_option` is ``False``.

        .. versionchanged:: 8.1.8
            The help option is now cached to avoid creating it multiple times.
        """
        help_option_names = self.get_help_option_names(ctx)

        if not help_option_names or not self.add_help_option:
            return None

        # Cache the help option object in private _help_option attribute to
        # avoid creating it multiple times. Not doing this will break the
        # callback odering by iter_params_for_processing(), which relies on
        # object comparison.
        if self._help_option is None:
            # Avoid circular import.
            from .decorators import help_option

            # Apply help_option decorator and pop resulting option
            help_option(*help_option_names)(self)
            self._help_option = self.params.pop()  # type: ignore[assignment]

        return self._help_option

    def make_parser(self, ctx: Context) -> _OptionParser:
        """Creates the underlying option parser for this command."""
        parser = _OptionParser(ctx)
        for param in self.get_params(ctx):
            param.add_to_parser(parser, ctx)
        return parser

    def get_help(self, ctx: Context) -> str:
        """Formats the help into a string and returns it.

        Calls :meth:`format_help` internally.
        """
        formatter = ctx.make_formatter()
        self.format_help(ctx, formatter)
        return formatter.getvalue().rstrip("\n")

    def get_short_help_str(self, limit: int = 45) -> str:
        """Gets short help for the command or makes it by shortening the
        long help string.
        """
        if self.short_help:
            text = inspect.cleandoc(self.short_help)
        elif self.help:
            text = make_default_short_help(self.help, limit)
        else:
            text = ""

        if self.deprecated:
            deprecated_message = (
                f"(DEPRECATED: {self.deprecated})"
                if isinstance(self.deprecated, str)
                else "(DEPRECATED)"
            )
            text = _("{text} {deprecated_message}").format(
                text=text, deprecated_message=deprecated_message
            )

        return text.strip()

    def format_help(self, ctx: Context, formatter: HelpFormatter) -> None:
        """Writes the help into the formatter if it exists.

        This is a low-level method called by :meth:`get_help`.

        This calls the following methods:

        -   :meth:`format_usage`
        -   :meth:`format_help_text`
        -   :meth:`format_options`
        -   :meth:`format_epilog`
        """
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_epilog(ctx, formatter)

    def format_help_text(self, ctx: Context, formatter: HelpFormatter) -> None:
        """Writes the help text to the formatter if it exists."""
        if self.help is not None:
            # truncate the help text to the first form feed
            text = inspect.cleandoc(self.help).partition("\f")[0]
        else:
            text = ""

        if self.deprecated:
            deprecated_message = (
                f"(DEPRECATED: {self.deprecated})"
                if isinstance(self.deprecated, str)
                else "(DEPRECATED)"
            )
            text = _("{text} {deprecated_message}").format(
                text=text, deprecated_message=deprecated_message
            )

        if text:
            formatter.write_paragraph()

            with formatter.indentation():
                formatter.write_text(text)

    def format_options(self, ctx: Context, formatter: HelpFormatter) -> None:
        """Writes all the options into the formatter if they exist."""
        opts = []
        for param in self.get_params(ctx):
            rv = param.get_help_record(ctx)
            if rv is not None:
                opts.append(rv)

        if opts:
            with formatter.section(_("Options")):
                formatter.write_dl(opts)

    def format_epilog(self, ctx: Context, formatter: HelpFormatter) -> None:
        """Writes the epilog into the formatter if it exists."""
        if self.epilog:
            epilog = inspect.cleandoc(self.epilog)
            formatter.write_paragraph()

            with formatter.indentation():
                formatter.write_text(epilog)

    def make_context(
        self,
        info_name: str | None,
        args: list[str],
        parent: Context | None = None,
        **extra: t.Any,
    ) -> Context:
        """This function when given an info name and arguments will kick
        off the parsing and create a new :class:`Context`.  It does not
        invoke the actual command callback though.

        To quickly customize the context class used without overriding
        this method, set the :attr:`context_class` attribute.

        :param info_name: the info name for this invocation.  Generally this
                          is the most descriptive name for the script or
                          command.  For the toplevel script it's usually
                          the name of the script, for commands below it's
                          the name of the command.
        :param args: the arguments to parse as list of strings.
        :param parent: the parent context if available.
        :param extra: extra keyword arguments forwarded to the context
                      constructor.

        .. versionchanged:: 8.0
            Added the :attr:`context_class` attribute.
        """
        for key, value in self.context_settings.items():
            if key not in extra:
                extra[key] = value

        ctx = self.context_class(self, info_name=info_name, parent=parent, **extra)

        with ctx.scope(cleanup=False):
            self.parse_args(ctx, args)
        return ctx

    def parse_args(self, ctx: Context, args: list[str]) -> list[str]:
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            raise NoArgsIsHelpError(ctx)

        parser = self.make_parser(ctx)
        opts, args, param_order = parser.parse_args(args=args)

        for param in iter_params_for_processing(param_order, self.get_params(ctx)):
            value, args = param.handle_parse_result(ctx, opts, args)

        if args and not ctx.allow_extra_args and not ctx.resilient_parsing:
            ctx.fail(
                ngettext(
                    "Got unexpected extra argument ({args})",
                    "Got unexpected extra arguments ({args})",
                    len(args),
                ).format(args=" ".join(map(str, args)))
            )

        ctx.args = args
        ctx._opt_prefixes.update(parser._opt_prefixes)
        return args

    def invoke(self, ctx: Context) -> t.Any:
        """Given a context, this invokes the attached callback (if it exists)
        in the right way.
        """
        if self.deprecated:
            extra_message = (
                f" {self.deprecated}" if isinstance(self.deprecated, str) else ""
            )
            message = _(
                "DeprecationWarning: The command {name!r} is deprecated.{extra_message}"
            ).format(name=self.name, extra_message=extra_message)
            echo(style(message, fg="red"), err=True)

        if self.callback is not None:
            return ctx.invoke(self.callback, **ctx.params)

    def shell_complete(self, ctx: Context, incomplete: str) -> list[CompletionItem]:
        """Return a list of completions for the incomplete value. Looks
        at the names of options and chained multi-commands.

        Any command could be part of a chained multi-command, so sibling
        commands are valid at any point during command completion.

        :param ctx: Invocation context for this command.
        :param incomplete: Value being completed. May be empty.

        .. versionadded:: 8.0
        """
        from click.shell_completion import CompletionItem

        results: list[CompletionItem] = []

        if incomplete and not incomplete[0].isalnum():
            for param in self.get_params(ctx):
                if (
                    not isinstance(param, Option)
                    or param.hidden
                    or (
                        not param.multiple
                        and ctx.get_parameter_source(param.name)  # type: ignore
                        is ParameterSource.COMMANDLINE
                    )
                ):
                    continue

                results.extend(
                    CompletionItem(name, help=param.help)
                    for name in [*param.opts, *param.secondary_opts]
                    if name.startswith(incomplete)
                )

        while ctx.parent is not None:
            ctx = ctx.parent

            if isinstance(ctx.command, Group) and ctx.command.chain:
                results.extend(
                    CompletionItem(name, help=command.get_short_help_str())
                    for name, command in _complete_visible_commands(ctx, incomplete)
                    if name not in ctx._protected_args
                )

        return results

    @t.overload
    def main(
        self,
        args: cabc.Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: t.Literal[True] = True,
        **extra: t.Any,
    ) -> t.NoReturn: ...

    @t.overload
    def main(
        self,
        args: cabc.Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = ...,
        **extra: t.Any,
    ) -> t.Any: ...

    def main(
        self,
        args: cabc.Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = True,
        windows_expand_args: bool = True,
        **extra: t.Any,
    ) -> t.Any:
        """This is the way to invoke a script with all the bells and
        whistles as a command line application.  This will always terminate
        the application after a call.  If this is not wanted, ``SystemExit``
        needs to be caught.

        This method is also available by directly calling the instance of
        a :class:`Command`.

        :param args: the arguments that should be used for parsing.  If not
                     provided, ``sys.argv[1:]`` is used.
        :param prog_name: the program name that should be used.  By default
                          the program name is constructed by taking the file
                          name from ``sys.argv[0]``.
        :param complete_var: the environment variable that controls the
                             bash completion support.  The default is
                             ``"_<prog_name>_COMPLETE"`` with prog_name in
                             uppercase.
        :param standalone_mode: the default behavior is to invoke the script
                                in standalone mode.  Click will then
                                handle exceptions and convert them into
                                error messages and the function will never
                                return but shut down the interpreter.  If
                                this is set to `False` they will be
                                propagated to the caller and the return
                                value of this function is the return value
                                of :meth:`invoke`.
        :param windows_expand_args: Expand glob patterns, user dir, and
            env vars in command line args on Windows.
        :param extra: extra keyword arguments are forwarded to the context
                      constructor.  See :class:`Context` for more information.

        .. versionchanged:: 8.0.1
            Added the ``windows_expand_args`` parameter to allow
            disabling command line arg expansion on Windows.

        .. versionchanged:: 8.0
            When taking arguments from ``sys.argv`` on Windows, glob
            patterns, user dir, and env vars are expanded.

        .. versionchanged:: 3.0
           Added the ``standalone_mode`` parameter.
        """
        if args is None:
            args = sys.argv[1:]

            if os.name == "nt" and windows_expand_args:
                args = _expand_args(args)
        else:
            args = list(args)

        if prog_name is None:
            prog_name = _detect_program_name()

        # Process shell completion requests and exit early.
        self._main_shell_completion(extra, prog_name, complete_var)

        try:
            try:
                with self.make_context(prog_name, args, **extra) as ctx:
                    rv = self.invoke(ctx)
                    if not standalone_mode:
                        return rv
                    # it's not safe to `ctx.exit(rv)` here!
                    # note that `rv` may actually contain data like "1" which
                    # has obvious effects
                    # more subtle case: `rv=[None, None]` can come out of
                    # chained commands which all returned `None` -- so it's not
                    # even always obvious that `rv` indicates success/failure
                    # by its truthiness/falsiness
                    ctx.exit()
            except (EOFError, KeyboardInterrupt) as e:
                echo(file=sys.stderr)
                raise Abort() from e
            except ClickException as e:
                if not standalone_mode:
                    raise
                e.show()
                sys.exit(e.exit_code)
            except OSError as e:
                if e.errno == errno.EPIPE:
                    sys.stdout = t.cast(t.TextIO, PacifyFlushWrapper(sys.stdout))
                    sys.stderr = t.cast(t.TextIO, PacifyFlushWrapper(sys.stderr))
                    sys.exit(1)
                else:
                    raise
        except Exit as e:
            if standalone_mode:
                sys.exit(e.exit_code)
            else:
                # in non-standalone mode, return the exit code
                # note that this is only reached if `self.invoke` above raises
                # an Exit explicitly -- thus bypassing the check there which
                # would return its result
                # the results of non-standalone execution may therefore be
                # somewhat ambiguous: if there are codepaths which lead to
                # `ctx.exit(1)` and to `return 1`, the caller won't be able to
                # tell the difference between the two
                return e.exit_code
        except Abort:
            if not standalone_mode:
                raise
            echo(_("Aborted!"), file=sys.stderr)
            sys.exit(1)

    def _main_shell_completion(
        self,
        ctx_args: cabc.MutableMapping[str, t.Any],
        prog_name: str,
        complete_var: str | None = None,
    ) -> None:
        """Check if the shell is asking for tab completion, process
        that, then exit early. Called from :meth:`main` before the
        program is invoked.

        :param prog_name: Name of the executable in the shell.
        :param complete_var: Name of the environment variable that holds
            the completion instruction. Defaults to
            ``_{PROG_NAME}_COMPLETE``.

        .. versionchanged:: 8.2.0
            Dots (``.``) in ``prog_name`` are replaced with underscores (``_``).
        """
        if complete_var is None:
            complete_name = prog_name.replace("-", "_").replace(".", "_")
            complete_var = f"_{complete_name}_COMPLETE".upper()

        instruction = os.environ.get(complete_var)

        if not instruction:
            return

        from .shell_completion import shell_complete

        rv = shell_complete(self, ctx_args, prog_name, complete_var, instruction)
        sys.exit(rv)

    def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        """Alias for :meth:`main`."""
        return self.main(*args, **kwargs)


class _FakeSubclassCheck(type):
    def __subclasscheck__(cls, subclass: type) -> bool:
        return issubclass(subclass, cls.__bases__[0])

    def __instancecheck__(cls, instance: t.Any) -> bool:
        return isinstance(instance, cls.__bases__[0])


class _BaseCommand(Command, metaclass=_FakeSubclassCheck):
    """
    .. deprecated:: 8.2
        Will be removed in Click 9.0. Use ``Command`` instead.
    """


class Group(Command):
    """A group is a command that nests other commands (or more groups).

    :param name: The name of the group command.
    :param commands: Map names to :class:`Command` objects. Can be a list, which
        will use :attr:`Command.name` as the keys.
    :param invoke_without_command: Invoke the group's callback even if a
        subcommand is not given.
    :param no_args_is_help: If no arguments are given, show the group's help and
        exit. Defaults to the opposite of ``invoke_without_command``.
    :param subcommand_metavar: How to represent the subcommand argument in help.
        The default will represent whether ``chain`` is set or not.
    :param chain: Allow passing more than one subcommand argument. After parsing
        a command's arguments, if any arguments remain another command will be
        matched, and so on.
    :param result_callback: A function to call after the group's and
        subcommand's callbacks. The value returned by the subcommand is passed.
        If ``chain`` is enabled, the value will be a list of values returned by
        all the commands. If ``invoke_without_command`` is enabled, the value
        will be the value returned by the group's callback, or an empty list if
        ``chain`` is enabled.
    :param kwargs: Other arguments passed to :class:`Command`.

    .. versionchanged:: 8.0
        The ``commands`` argument can be a list of command objects.

    .. versionchanged:: 8.2
        Merged with and replaces the ``MultiCommand`` base class.
    """

    allow_extra_args = True
    allow_interspersed_args = False

    #: If set, this is used by the group's :meth:`command` decorator
    #: as the default :class:`Command` class. This is useful to make all
    #: subcommands use a custom command class.
    #:
    #: .. versionadded:: 8.0
    command_class: type[Command] | None = None

    #: If set, this is used by the group's :meth:`group` decorator
    #: as the default :class:`Group` class. This is useful to make all
    #: subgroups use a custom group class.
    #:
    #: If set to the special value :class:`type` (literally
    #: ``group_class = type``), this group's class will be used as the
    #: default class. This makes a custom group class continue to make
    #: custom groups.
    #:
    #: .. versionadded:: 8.0
    group_class: type[Group] | type[type] | None = None
    # Literal[type] isn't valid, so use Type[type]

    def __init__(
        self,
        name: str | None = None,
        commands: cabc.MutableMapping[str, Command]
        | cabc.Sequence[Command]
        | None = None,
        invoke_without_command: bool = False,
        no_args_is_help: bool | None = None,
        subcommand_metavar: str | None = None,
        chain: bool = False,
        result_callback: t.Callable[..., t.Any] | None = None,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(name, **kwargs)

        if commands is None:
            commands = {}
        elif isinstance(commands, abc.Sequence):
            commands = {c.name: c for c in commands if c.name is not None}

        #: The registered subcommands by their exported names.
        self.commands: cabc.MutableMapping[str, Command] = commands

        if no_args_is_help is None:
            no_args_is_help = not invoke_without_command

        self.no_args_is_help = no_args_is_help
        self.invoke_without_command = invoke_without_command

        if subcommand_metavar is None:
            if chain:
                subcommand_metavar = "COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]..."
            else:
                subcommand_metavar = "COMMAND [ARGS]..."

        self.subcommand_metavar = subcommand_metavar
        self.chain = chain
        # The result callback that is stored. This can be set or
        # overridden with the :func:`result_callback` decorator.
        self._result_callback = result_callback

        if self.chain:
            for param in self.params:
                if isinstance(param, Argument) and not param.required:
                    raise RuntimeError(
                        "A group in chain mode cannot have optional arguments."
                    )

    def to_info_dict(self, ctx: Context) -> dict[str, t.Any]:
        info_dict = super().to_info_dict(ctx)
        commands = {}

        for name in self.list_commands(ctx):
            command = self.get_command(ctx, name)

            if command is None:
                continue

            sub_ctx = ctx._make_sub_context(command)

            with sub_ctx.scope(cleanup=False):
                commands[name] = command.to_info_dict(sub_ctx)

        info_dict.update(commands=commands, chain=self.chain)
        return info_dict

    def add_command(self, cmd: Command, name: str | None = None) -> None:
        """Registers another :class:`Command` with this group.  If the name
        is not provided, the name of the command is used.
        """
        name = name or cmd.name
        if name is None:
            raise TypeError("Command has no name.")
        _check_nested_chain(self, name, cmd, register=True)
        self.commands[name] = cmd

    @t.overload
    def command(self, __func: t.Callable[..., t.Any]) -> Command: ...

    @t.overload
    def command(
        self, *args: t.Any, **kwargs: t.Any
    ) -> t.Callable[[t.Callable[..., t.Any]], Command]: ...

    def command(
        self, *args: t.Any, **kwargs: t.Any
    ) -> t.Callable[[t.Callable[..., t.Any]], Command] | Command:
        """A shortcut decorator for declaring and attaching a command to
        the group. This takes the same arguments as :func:`command` and
        immediately registers the created command with this group by
        calling :meth:`add_command`.

        To customize the command class used, set the
        :attr:`command_class` attribute.

        .. versionchanged:: 8.1
            This decorator can be applied without parentheses.

        .. versionchanged:: 8.0
            Added the :attr:`command_class` attribute.
        """
        from .decorators import command

        func: t.Callable[..., t.Any] | None = None

        if args and callable(args[0]):
            assert len(args) == 1 and not kwargs, (
                "Use 'command(**kwargs)(callable)' to provide arguments."
            )
            (func,) = args
            args = ()

        if self.command_class and kwargs.get("cls") is None:
            kwargs["cls"] = self.command_class

        def decorator(f: t.Callable[..., t.Any]) -> Command:
            cmd: Command = command(*args, **kwargs)(f)
            self.add_command(cmd)
            return cmd

        if func is not None:
            return decorator(func)

        return decorator

    @t.overload
    def group(self, __func: t.Callable[..., t.Any]) -> Group: ...

    @t.overload
    def group(
        self, *args: t.Any, **kwargs: t.Any
    ) -> t.Callable[[t.Callable[..., t.Any]], Group]: ...

    def group(
        self, *args: t.Any, **kwargs: t.Any
    ) -> t.Callable[[t.Callable[..., t.Any]], Group] | Group:
        """A shortcut decorator for declaring and attaching a group to
        the group. This takes the same arguments as :func:`group` and
        immediately registers the created group with this group by
        calling :meth:`add_command`.

        To customize the group class used, set the :attr:`group_class`
        attribute.

        .. versionchanged:: 8.1
            This decorator can be applied without parentheses.

        .. versionchanged:: 8.0
            Added the :attr:`group_class` attribute.
        """
        from .decorators import group

        func: t.Callable[..., t.Any] | None = None

        if args and callable(args[0]):
            assert len(args) == 1 and not kwargs, (
                "Use 'group(**kwargs)(callable)' to provide arguments."
            )
            (func,) = args
            args = ()

        if self.group_class is not None and kwargs.get("cls") is None:
            if self.group_class is type:
                kwargs["cls"] = type(self)
            else:
                kwargs["cls"] = self.group_class

        def decorator(f: t.Callable[..., t.Any]) -> Group:
            cmd: Group = group(*args, **kwargs)(f)
            self.add_command(cmd)
            return cmd

        if func is not None:
            return decorator(func)

        return decorator

    def result_callback(self, replace: bool = False) -> t.Callable[[F], F]:
        """Adds a result callback to the command.  By default if a
        result callback is already registered this will chain them but
        this can be disabled with the `replace` parameter.  The result
        callback is invoked with the return value of the subcommand
        (or the list of return values from all subcommands if chaining
        is enabled) as well as the parameters as they would be passed
        to the main callback.

        Example::

            @click.group()
            @click.option('-i', '--input', default=23)
            def cli(input):
                return 42

            @cli.result_callback()
            def process_result(result, input):
                return result + input

        :param replace: if set to `True` an already existing result
                        callback will be removed.

        .. versionchanged:: 8.0
            Renamed from ``resultcallback``.

        .. versionadded:: 3.0
        """

        def decorator(f: F) -> F:
            old_callback = self._result_callback

            if old_callback is None or replace:
                self._result_callback = f
                return f

            def function(value: t.Any, /, *args: t.Any, **kwargs: t.Any) -> t.Any:
                inner = old_callback(value, *args, **kwargs)
                return f(inner, *args, **kwargs)

            self._result_callback = rv = update_wrapper(t.cast(F, function), f)
            return rv  # type: ignore[return-value]

        return decorator

    def get_command(self, ctx: Context, cmd_name: str) -> Command | None:
        """Given a context and a command name, this returns a :class:`Command`
        object if it exists or returns ``None``.
        """
        return self.commands.get(cmd_name)

    def list_commands(self, ctx: Context) -> list[str]:
        """Returns a list of subcommand names in the order they should appear."""
        return sorted(self.commands)

    def collect_usage_pieces(self, ctx: Context) -> list[str]:
        rv = super().collect_usage_pieces(ctx)
        rv.append(self.subcommand_metavar)
        return rv

    def format_options(self, ctx: Context, formatter: HelpFormatter) -> None:
        super().format_options(ctx, formatter)
        self.format_commands(ctx, formatter)

    def format_commands(self, ctx: Context, formatter: HelpFormatter) -> None:
        """Extra format methods for multi methods that adds all the commands
        after the options.
        """
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            # What is this, the tool lied about a command.  Ignore it
            if cmd is None:
                continue
            if cmd.hidden:
                continue

            commands.append((subcommand, cmd))

        # allow for 3 times the default spacing
        if len(commands):
            limit = formatter.width - 6 - max(len(cmd[0]) for cmd in commands)

            rows = []
            for subcommand, cmd in commands:
                help = cmd.get_short_help_str(limit)
                rows.append((subcommand, help))

            if rows:
                with formatter.section(_("Commands")):
                    formatter.write_dl(rows)

    def parse_args(self, ctx: Context, args: list[str]) -> list[str]:
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            raise NoArgsIsHelpError(ctx)

        rest = super().parse_args(ctx, args)

        if self.chain:
            ctx._protected_args = rest
            ctx.args = []
        elif rest:
            ctx._protected_args, ctx.args = rest[:1], rest[1:]

        return ctx.args

    def invoke(self, ctx: Context) -> t.Any:
        def _process_result(value: t.Any) -> t.Any:
            if self._result_callback is not None:
                value = ctx.invoke(self._result_callback, value, **ctx.params)
            return value

        if not ctx._protected_args:
            if self.invoke_without_command:
                # No subcommand was invoked, so the result callback is
                # invoked with the group return value for regular
                # groups, or an empty list for chained groups.
                with ctx:
                    rv = super().invoke(ctx)
                    return _process_result([] if self.chain else rv)
            ctx.fail(_("Missing command."))

        # Fetch args back out
        args = [*ctx._protected_args, *ctx.args]
        ctx.args = []
        ctx._protected_args = []

        # If we're not in chain mode, we only allow the invocation of a
        # single command but we also inform the current context about the
        # name of the command to invoke.
        if not self.chain:
            # Make sure the context is entered so we do not clean up
            # resources until the result processor has worked.
            with ctx:
                cmd_name, cmd, args = self.resolve_command(ctx, args)
                assert cmd is not None
                ctx.invoked_subcommand = cmd_name
                super().invoke(ctx)
                sub_ctx = cmd.make_context(cmd_name, args, parent=ctx)
                with sub_ctx:
                    return _process_result(sub_ctx.command.invoke(sub_ctx))

        # In chain mode we create the contexts step by step, but after the
        # base command has been invoked.  Because at that point we do not
        # know the subcommands yet, the invoked subcommand attribute is
        # set to ``*`` to inform the command that subcommands are executed
        # but nothing else.
        with ctx:
            ctx.invoked_subcommand = "*" if args else None
            super().invoke(ctx)

            # Otherwise we make every single context and invoke them in a
            # chain.  In that case the return value to the result processor
            # is the list of all invoked subcommand's results.
            contexts = []
            while args:
                cmd_name, cmd, args = self.resolve_command(ctx, args)
                assert cmd is not None
                sub_ctx = cmd.make_context(
                    cmd_name,
                    args,
                    parent=ctx,
                    allow_extra_args=True,
                    allow_interspersed_args=False,
                )
                contexts.append(sub_ctx)
                args, sub_ctx.args = sub_ctx.args, []

            rv = []
            for sub_ctx in contexts:
                with sub_ctx:
                    rv.append(sub_ctx.command.invoke(sub_ctx))
            return _process_result(rv)

    def resolve_command(
        self, ctx: Context, args: list[str]
    ) -> tuple[str | None, Command | None, list[str]]:
        cmd_name = make_str(args[0])
        original_cmd_name = cmd_name

        # Get the command
        cmd = self.get_command(ctx, cmd_name)

        # If we can't find the command but there is a normalization
        # function available, we try with that one.
        if cmd is None and ctx.token_normalize_func is not None:
            cmd_name = ctx.token_normalize_func(cmd_name)
            cmd = self.get_command(ctx, cmd_name)

        # If we don't find the command we want to show an error message
        # to the user that it was not provided.  However, there is
        # something else we should do: if the first argument looks like
        # an option we want to kick off parsing again for arguments to
        # resolve things like --help which now should go to the main
        # place.
        if cmd is None and not ctx.resilient_parsing:
            if _split_opt(cmd_name)[0]:
                self.parse_args(ctx, args)
            ctx.fail(_("No such command {name!r}.").format(name=original_cmd_name))
        return cmd_name if cmd else None, cmd, args[1:]

    def shell_complete(self, ctx: Context, incomplete: str) -> list[CompletionItem]:
        """Return a list of completions for the incomplete value. Looks
        at the names of options, subcommands, and chained
        multi-commands.

        :param ctx: Invocation context for this command.
        :param incomplete: Value being completed. May be empty.

        .. versionadded:: 8.0
        """
        from click.shell_completion import CompletionItem

        results = [
            CompletionItem(name, help=command.get_short_help_str())
            for name, command in _complete_visible_commands(ctx, incomplete)
        ]
        results.extend(super().shell_complete(ctx, incomplete))
        return results


class _MultiCommand(Group, metaclass=_FakeSubclassCheck):
    """
    .. deprecated:: 8.2
        Will be removed in Click 9.0. Use ``Group`` instead.
    """


class CommandCollection(Group):
    """A :class:`Group` that looks up subcommands on other groups. If a command
    is not found on this group, each registered source is checked in order.
    Parameters on a source are not added to this group, and a source's callback
    is not invoked when invoking its commands. In other words, this "flattens"
    commands in many groups into this one group.

    :param name: The name of the group command.
    :param sources: A list of :class:`Group` objects to look up commands from.
    :param kwargs: Other arguments passed to :class:`Group`.

    .. versionchanged:: 8.2
        This is a subclass of ``Group``. Commands are looked up first on this
        group, then each of its sources.
    """

    def __init__(
        self,
        name: str | None = None,
        sources: list[Group] | None = None,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(name, **kwargs)
        #: The list of registered groups.
        self.sources: list[Group] = sources or []

    def add_source(self, group: Group) -> None:
        """Add a group as a source of commands."""
        self.sources.append(group)

    def get_command(self, ctx: Context, cmd_name: str) -> Command | None:
        rv = super().get_command(ctx, cmd_name)

        if rv is not None:
            return rv

        for source in self.sources:
            rv = source.get_command(ctx, cmd_name)

            if rv is not None:
                if self.chain:
                    _check_nested_chain(self, cmd_name, rv)

                return rv

        return None

    def list_commands(self, ctx: Context) -> list[str]:
        rv: set[str] = set(super().list_commands(ctx))

        for source in self.sources:
            rv.update(source.list_commands(ctx))

        return sorted(rv)


def _check_iter(value: t.Any) -> cabc.Iterator[t.Any]:
    """Check if the value is iterable but not a string. Raises a type
    error, or return an iterator over the value.
    """
    if isinstance(value, str):
        raise TypeError

    return iter(value)


class Parameter:
    r"""A parameter to a command comes in two versions: they are either
    :class:`Option`\s or :class:`Argument`\s.  Other subclasses are currently
    not supported by design as some of the internals for parsing are
    intentionally not finalized.

    Some settings are supported by both options and arguments.

    :param param_decls: the parameter declarations for this option or
                        argument.  This is a list of flags or argument
                        names.
    :param type: the type that should be used.  Either a :class:`ParamType`
                 or a Python type.  The latter is converted into the former
                 automatically if supported.
    :param required: controls if this is optional or not.
    :param default: the default value if omitted.  This can also be a callable,
                    in which case it's invoked when the default is needed
                    without any arguments.
    :param callback: A function to further process or validate the value
        after type conversion. It is called as ``f(ctx, param, value)``
        and must return the value. It is called for all sources,
        including prompts.
    :param nargs: the number of arguments to match.  If not ``1`` the return
                  value is a tuple instead of single value.  The default for
                  nargs is ``1`` (except if the type is a tuple, then it's
                  the arity of the tuple). If ``nargs=-1``, all remaining
                  parameters are collected.
    :param metavar: how the value is represented in the help page.
    :param expose_value: if this is `True` then the value is passed onwards
                         to the command callback and stored on the context,
                         otherwise it's skipped.
    :param is_eager: eager values are processed before non eager ones.  This
                     should not be set for arguments or it will inverse the
                     order of processing.
    :param envvar: a string or list of strings that are environment variables
                   that should be checked.
    :param shell_complete: A function that returns custom shell
        completions. Used instead of the param's type completion if
        given. Takes ``ctx, param, incomplete`` and must return a list
        of :class:`~click.shell_completion.CompletionItem` or a list of
        strings.
    :param deprecated: If ``True`` or non-empty string, issues a message
                        indicating that the argument is deprecated and highlights
                        its deprecation in --help. The message can be customized
                        by using a string as the value. A deprecated parameter
                        cannot be required, a ValueError will be raised otherwise.

    .. versionchanged:: 8.2.0
        Introduction of ``deprecated``.

    .. versionchanged:: 8.2
        Adding duplicate parameter names to a :class:`~click.core.Command` will
        result in a ``UserWarning`` being shown.

    .. versionchanged:: 8.2
        Adding duplicate parameter names to a :class:`~click.core.Command` will
        result in a ``UserWarning`` being shown.

    .. versionchanged:: 8.0
        ``process_value`` validates required parameters and bounded
        ``nargs``, and invokes the parameter callback before returning
        the value. This allows the callback to validate prompts.
        ``full_process_value`` is removed.

    .. versionchanged:: 8.0
        ``autocompletion`` is renamed to ``shell_complete`` and has new
        semantics described above. The old name is deprecated and will
        be removed in 8.1, until then it will be wrapped to match the
        new requirements.

    .. versionchanged:: 8.0
        For ``multiple=True, nargs>1``, the default must be a list of
        tuples.

    .. versionchanged:: 8.0
        Setting a default is no longer required for ``nargs>1``, it will
        default to ``None``. ``multiple=True`` or ``nargs=-1`` will
        default to ``()``.

    .. versionchanged:: 7.1
        Empty environment variables are ignored rather than taking the
        empty string value. This makes it possible for scripts to clear
        variables if they can't unset them.

    .. versionchanged:: 2.0
        Changed signature for parameter callback to also be passed the
        parameter. The old callback format will still work, but it will
        raise a warning to give you a chance to migrate the code easier.
    """

    param_type_name = "parameter"

    def __init__(
        self,
        param_decls: cabc.Sequence[str] | None = None,
        type: types.ParamType | t.Any | None = None,
        required: bool = False,
        default: t.Any | t.Callable[[], t.Any] | None = None,
        callback: t.Callable[[Context, Parameter, t.Any], t.Any] | None = None,
        nargs: int | None = None,
        multiple: bool = False,
        metavar: str | None = None,
        expose_value: bool = True,
        is_eager: bool = False,
        envvar: str | cabc.Sequence[str] | None = None,
        shell_complete: t.Callable[
            [Context, Parameter, str], list[CompletionItem] | list[str]
        ]
        | None = None,
        deprecated: bool | str = False,
    ) -> None:
        self.name: str | None
        self.opts: list[str]
        self.secondary_opts: list[str]
        self.name, self.opts, self.secondary_opts = self._parse_decls(
            param_decls or (), expose_value
        )
        self.type: types.ParamType = types.convert_type(type, default)

        # Default nargs to what the type tells us if we have that
        # information available.
        if nargs is None:
            if self.type.is_composite:
                nargs = self.type.arity
            else:
                nargs = 1

        self.required = required
        self.callback = callback
        self.nargs = nargs
        self.multiple = multiple
        self.expose_value = expose_value
        self.default = default
        self.is_eager = is_eager
        self.metavar = metavar
        self.envvar = envvar
        self._custom_shell_complete = shell_complete
        self.deprecated = deprecated

        if __debug__:
            if self.type.is_composite and nargs != self.type.arity:
                raise ValueError(
                    f"'nargs' must be {self.type.arity} (or None) for"
                    f" type {self.type!r}, but it was {nargs}."
                )

            # Skip no default or callable default.
            check_default = default if not callable(default) else None

            if check_default is not None:
                if multiple:
                    try:
                        # Only check the first value against nargs.
                        check_default = next(_check_iter(check_default), None)
                    except TypeError:
                        raise ValueError(
                            "'default' must be a list when 'multiple' is true."
                        ) from None

                # Can be None for multiple with empty default.
                if nargs != 1 and check_default is not None:
                    try:
                        _check_iter(check_default)
                    except TypeError:
                        if multiple:
                            message = (
                                "'default' must be a list of lists when 'multiple' is"
                                " true and 'nargs' != 1."
                            )
                        else:
                            message = "'default' must be a list when 'nargs' != 1."

                        raise ValueError(message) from None

                    if nargs > 1 and len(check_default) != nargs:
                        subject = "item length" if multiple else "length"
                        raise ValueError(
                            f"'default' {subject} must match nargs={nargs}."
                        )

            if required and deprecated:
                raise ValueError(
                    f"The {self.param_type_name} '{self.human_readable_name}' "
                    "is deprecated and still required. A deprecated "
                    f"{self.param_type_name} cannot be required."
                )

    def to_info_dict(self) -> dict[str, t.Any]:
        """Gather information that could be useful for a tool generating
        user-facing documentation.

        Use :meth:`click.Context.to_info_dict` to traverse the entire
        CLI structure.

        .. versionadded:: 8.0
        """
        return {
            "name": self.name,
            "param_type_name": self.param_type_name,
            "opts": self.opts,
            "secondary_opts": self.secondary_opts,
            "type": self.type.to_info_dict(),
            "required": self.required,
            "nargs": self.nargs,
            "multiple": self.multiple,
            "default": self.default,
            "envvar": self.envvar,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.name}>"

    def _parse_decls(
        self, decls: cabc.Sequence[str], expose_value: bool
    ) -> tuple[str | None, list[str], list[str]]:
        raise NotImplementedError()

    @property
    def human_readable_name(self) -> str:
        """Returns the human readable name of this parameter.  This is the
        same as the name for options, but the metavar for arguments.
        """
        return self.name  # type: ignore

    def make_metavar(self, ctx: Context) -> str:
        if self.metavar is not None:
            return self.metavar

        metavar = self.type.get_metavar(param=self, ctx=ctx)

        if metavar is None:
            metavar = self.type.name.upper()

        if self.nargs != 1:
            metavar += "..."

        return metavar

    @t.overload
    def get_default(
        self, ctx: Context, call: t.Literal[True] = True
    ) -> t.Any | None: ...

    @t.overload
    def get_default(
        self, ctx: Context, call: bool = ...
    ) -> t.Any | t.Callable[[], t.Any] | None: ...

    def get_default(
        self, ctx: Context, call: bool = True
    ) -> t.Any | t.Callable[[], t.Any] | None:
        """Get the default for the parameter. Tries
        :meth:`Context.lookup_default` first, then the local default.

        :param ctx: Current context.
        :param call: If the default is a callable, call it. Disable to
            return the callable instead.

        .. versionchanged:: 8.0.2
            Type casting is no longer performed when getting a default.

        .. versionchanged:: 8.0.1
            Type casting can fail in resilient parsing mode. Invalid
            defaults will not prevent showing help text.

        .. versionchanged:: 8.0
            Looks at ``ctx.default_map`` first.

        .. versionchanged:: 8.0
            Added the ``call`` parameter.
        """
        value = ctx.lookup_default(self.name, call=False)  # type: ignore

        if value is None:
            value = self.default

        if call and callable(value):
            value = value()

        return value

    def add_to_parser(self, parser: _OptionParser, ctx: Context) -> None:
        raise NotImplementedError()

    def consume_value(
        self, ctx: Context, opts: cabc.Mapping[str, t.Any]
    ) -> tuple[t.Any, ParameterSource]:
        value = opts.get(self.name)  # type: ignore
        source = ParameterSource.COMMANDLINE

        if value is None:
            value = self.value_from_envvar(ctx)
            source = ParameterSource.ENVIRONMENT

        if value is None:
            value = ctx.lookup_default(self.name)  # type: ignore
            source = ParameterSource.DEFAULT_MAP

        if value is None:
            value = self.get_default(ctx)
            source = ParameterSource.DEFAULT

        return value, source

    def type_cast_value(self, ctx: Context, value: t.Any) -> t.Any:
        """Convert and validate a value against the option's
        :attr:`type`, :attr:`multiple`, and :attr:`nargs`.
        """
        if value is None:
            return () if self.multiple or self.nargs == -1 else None

        def check_iter(value: t.Any) -> cabc.Iterator[t.Any]:
            try:
                return _check_iter(value)
            except TypeError:
                # This should only happen when passing in args manually,
                # the parser should construct an iterable when parsing
                # the command line.
                raise BadParameter(
                    _("Value must be an iterable."), ctx=ctx, param=self
                ) from None

        if self.nargs == 1 or self.type.is_composite:

            def convert(value: t.Any) -> t.Any:
                return self.type(value, param=self, ctx=ctx)

        elif self.nargs == -1:

            def convert(value: t.Any) -> t.Any:  # tuple[t.Any, ...]
                return tuple(self.type(x, self, ctx) for x in check_iter(value))

        else:  # nargs > 1

            def convert(value: t.Any) -> t.Any:  # tuple[t.Any, ...]
                value = tuple(check_iter(value))

                if len(value) != self.nargs:
                    raise BadParameter(
                        ngettext(
                            "Takes {nargs} values but 1 was given.",
                            "Takes {nargs} values but {len} were given.",
                            len(value),
                        ).format(nargs=self.nargs, len=len(value)),
                        ctx=ctx,
                        param=self,
                    )

                return tuple(self.type(x, self, ctx) for x in value)

        if self.multiple:
            return tuple(convert(x) for x in check_iter(value))

        return convert(value)

    def value_is_missing(self, value: t.Any) -> bool:
        if value is None:
            return True

        if (self.nargs != 1 or self.multiple) and value == ():
            return True

        return False

    def process_value(self, ctx: Context, value: t.Any) -> t.Any:
        value = self.type_cast_value(ctx, value)

        if self.required and self.value_is_missing(value):
            raise MissingParameter(ctx=ctx, param=self)

        if self.callback is not None:
            value = self.callback(ctx, self, value)

        return value

    def resolve_envvar_value(self, ctx: Context) -> str | None:
        if self.envvar is None:
            return None

        if isinstance(self.envvar, str):
            rv = os.environ.get(self.envvar)

            if rv:
                return rv
        else:
            for envvar in self.envvar:
                rv = os.environ.get(envvar)

                if rv:
                    return rv

        return None

    def value_from_envvar(self, ctx: Context) -> t.Any | None:
        rv: t.Any | None = self.resolve_envvar_value(ctx)

        if rv is not None and self.nargs != 1:
            rv = self.type.split_envvar_value(rv)

        return rv

    def handle_parse_result(
        self, ctx: Context, opts: cabc.Mapping[str, t.Any], args: list[str]
    ) -> tuple[t.Any, list[str]]:
        with augment_usage_errors(ctx, param=self):
            value, source = self.consume_value(ctx, opts)

            if (
                self.deprecated
                and value is not None
                and source
                not in (
                    ParameterSource.DEFAULT,
                    ParameterSource.DEFAULT_MAP,
                )
            ):
                extra_message = (
                    f" {self.deprecated}" if isinstance(self.deprecated, str) else ""
                )
                message = _(
                    "DeprecationWarning: The {param_type} {name!r} is deprecated."
                    "{extra_message}"
                ).format(
                    param_type=self.param_type_name,
                    name=self.human_readable_name,
                    extra_message=extra_message,
                )
                echo(style(message, fg="red"), err=True)

            ctx.set_parameter_source(self.name, source)  # type: ignore

            try:
                value = self.process_value(ctx, value)
            except Exception:
                if not ctx.resilient_parsing:
                    raise

                value = None

        if self.expose_value:
            ctx.params[self.name] = value  # type: ignore

        return value, args

    def get_help_record(self, ctx: Context) -> tuple[str, str] | None:
        pass

    def get_usage_pieces(self, ctx: Context) -> list[str]:
        return []

    def get_error_hint(self, ctx: Context) -> str:
        """Get a stringified version of the param for use in error messages to
        indicate which param caused the error.
        """
        hint_list = self.opts or [self.human_readable_name]
        return " / ".join(f"'{x}'" for x in hint_list)

    def shell_complete(self, ctx: Context, incomplete: str) -> list[CompletionItem]:
        """Return a list of completions for the incomplete value. If a
        ``shell_complete`` function was given during init, it is used.
        Otherwise, the :attr:`type`
        :meth:`~click.types.ParamType.shell_complete` function is used.

        :param ctx: Invocation context for this command.
        :param incomplete: Value being completed. May be empty.

        .. versionadded:: 8.0
        """
        if self._custom_shell_complete is not None:
            results = self._custom_shell_complete(ctx, self, incomplete)

            if results and isinstance(results[0], str):
                from click.shell_completion import CompletionItem

                results = [CompletionItem(c) for c in results]

            return t.cast("list[CompletionItem]", results)

        return self.type.shell_complete(ctx, self, incomplete)


class Option(Parameter):
    """Options are usually optional values on the command line and
    have some extra features that arguments don't have.

    All other parameters are passed onwards to the parameter constructor.

    :param show_default: Show the default value for this option in its
        help text. Values are not shown by default, unless
        :attr:`Context.show_default` is ``True``. If this value is a
        string, it shows that string in parentheses instead of the
        actual value. This is particularly useful for dynamic options.
        For single option boolean flags, the default remains hidden if
        its value is ``False``.
    :param show_envvar: Controls if an environment variable should be
        shown on the help page and error messages.
        Normally, environment variables are not shown.
    :param prompt: If set to ``True`` or a non empty string then the
        user will be prompted for input. If set to ``True`` the prompt
        will be the option name capitalized. A deprecated option cannot be
        prompted.
    :param confirmation_prompt: Prompt a second time to confirm the
        value if it was prompted for. Can be set to a string instead of
        ``True`` to customize the message.
    :param prompt_required: If set to ``False``, the user will be
        prompted for input only when the option was specified as a flag
        without a value.
    :param hide_input: If this is ``True`` then the input on the prompt
        will be hidden from the user. This is useful for password input.
    :param is_flag: forces this option to act as a flag.  The default is
                    auto detection.
    :param flag_value: which value should be used for this flag if it's
                       enabled.  This is set to a boolean automatically if
                       the option string contains a slash to mark two options.
    :param multiple: if this is set to `True` then the argument is accepted
                     multiple times and recorded.  This is similar to ``nargs``
                     in how it works but supports arbitrary number of
                     arguments.
    :param count: this flag makes an option increment an integer.
    :param allow_from_autoenv: if this is enabled then the value of this
                               parameter will be pulled from an environment
                               variable in case a prefix is defined on the
                               context.
    :param help: the help string.
    :param hidden: hide this option from help outputs.
    :param attrs: Other command arguments described in :class:`Parameter`.

    .. versionchanged:: 8.2
        ``envvar`` used with ``flag_value`` will always use the ``flag_value``,
        previously it would use the value of the environment variable.

    .. versionchanged:: 8.1
        Help text indentation is cleaned here instead of only in the
        ``@option`` decorator.

    .. versionchanged:: 8.1
        The ``show_default`` parameter overrides
        ``Context.show_default``.

    .. versionchanged:: 8.1
        The default of a single option boolean flag is not shown if the
        default value is ``False``.

    .. versionchanged:: 8.0.1
        ``type`` is detected from ``flag_value`` if given.
    """

    param_type_name = "option"

    def __init__(
        self,
        param_decls: cabc.Sequence[str] | None = None,
        show_default: bool | str | None = None,
        prompt: bool | str = False,
        confirmation_prompt: bool | str = False,
        prompt_required: bool = True,
        hide_input: bool = False,
        is_flag: bool | None = None,
        flag_value: t.Any | None = None,
        multiple: bool = False,
        count: bool = False,
        allow_from_autoenv: bool = True,
        type: types.ParamType | t.Any | None = None,
        help: str | None = None,
        hidden: bool = False,
        show_choices: bool = True,
        show_envvar: bool = False,
        deprecated: bool | str = False,
        **attrs: t.Any,
    ) -> None:
        if help:
            help = inspect.cleandoc(help)

        default_is_missing = "default" not in attrs
        super().__init__(
            param_decls, type=type, multiple=multiple, deprecated=deprecated, **attrs
        )

        if prompt is True:
            if self.name is None:
                raise TypeError("'name' is required with 'prompt=True'.")

            prompt_text: str | None = self.name.replace("_", " ").capitalize()
        elif prompt is False:
            prompt_text = None
        else:
            prompt_text = prompt

        if deprecated:
            deprecated_message = (
                f"(DEPRECATED: {deprecated})"
                if isinstance(deprecated, str)
                else "(DEPRECATED)"
            )
            help = help + deprecated_message if help is not None else deprecated_message

        self.prompt = prompt_text
        self.confirmation_prompt = confirmation_prompt
        self.prompt_required = prompt_required
        self.hide_input = hide_input
        self.hidden = hidden

        # If prompt is enabled but not required, then the option can be
        # used as a flag to indicate using prompt or flag_value.
        self._flag_needs_value = self.prompt is not None and not self.prompt_required

        if is_flag is None:
            if flag_value is not None:
                # Implicitly a flag because flag_value was set.
                is_flag = True
            elif self._flag_needs_value:
                # Not a flag, but when used as a flag it shows a prompt.
                is_flag = False
            else:
                # Implicitly a flag because flag options were given.
                is_flag = bool(self.secondary_opts)
        elif is_flag is False and not self._flag_needs_value:
            # Not a flag, and prompt is not enabled, can be used as a
            # flag if flag_value is set.
            self._flag_needs_value = flag_value is not None

        self.default: t.Any | t.Callable[[], t.Any]

        if is_flag and default_is_missing and not self.required:
            if multiple:
                self.default = ()
            else:
                self.default = False

        if is_flag and flag_value is None:
            flag_value = not self.default

        self.type: types.ParamType
        if is_flag and type is None:
            # Re-guess the type from the flag value instead of the
            # default.
            self.type = types.convert_type(None, flag_value)

        self.is_flag: bool = is_flag
        self.is_bool_flag: bool = is_flag and isinstance(self.type, types.BoolParamType)
        self.flag_value: t.Any = flag_value

        # Counting
        self.count = count
        if count:
            if type is None:
                self.type = types.IntRange(min=0)
            if default_is_missing:
                self.default = 0

        self.allow_from_autoenv = allow_from_autoenv
        self.help = help
        self.show_default = show_default
        self.show_choices = show_choices
        self.show_envvar = show_envvar

        if __debug__:
            if deprecated and prompt:
                raise ValueError("`deprecated` options cannot use `prompt`.")

            if self.nargs == -1:
                raise TypeError("nargs=-1 is not supported for options.")

            if self.prompt and self.is_flag and not self.is_bool_flag:
                raise TypeError("'prompt' is not valid for non-boolean flag.")

            if not self.is_bool_flag and self.secondary_opts:
                raise TypeError("Secondary flag is not valid for non-boolean flag.")

            if self.is_bool_flag and self.hide_input and self.prompt is not None:
                raise TypeError(
                    "'prompt' with 'hide_input' is not valid for boolean flag."
                )

            if self.count:
                if self.multiple:
                    raise TypeError("'count' is not valid with 'multiple'.")

                if self.is_flag:
                    raise TypeError("'count' is not valid with 'is_flag'.")

    def to_info_dict(self) -> dict[str, t.Any]:
        info_dict = super().to_info_dict()
        info_dict.update(
            help=self.help,
            prompt=self.prompt,
            is_flag=self.is_flag,
            flag_value=self.flag_value,
            count=self.count,
            hidden=self.hidden,
        )
        return info_dict

    def get_error_hint(self, ctx: Context) -> str:
        result = super().get_error_hint(ctx)
        if self.show_envvar:
            result += f" (env var: '{self.envvar}')"
        return result

    def _parse_decls(
        self, decls: cabc.Sequence[str], expose_value: bool
    ) -> tuple[str | None, list[str], list[str]]:
        opts = []
        secondary_opts = []
        name = None
        possible_names = []

        for decl in decls:
            if decl.isidentifier():
                if name is not None:
                    raise TypeError(f"Name '{name}' defined twice")
                name = decl
            else:
                split_char = ";" if decl[:1] == "/" else "/"
                if split_char in decl:
                    first, second = decl.split(split_char, 1)
                    first = first.rstrip()
                    if first:
                        possible_names.append(_split_opt(first))
                        opts.append(first)
                    second = second.lstrip()
                    if second:
                        secondary_opts.append(second.lstrip())
                    if first == second:
                        raise ValueError(
                            f"Boolean option {decl!r} cannot use the"
                            " same flag for true/false."
                        )
                else:
                    possible_names.append(_split_opt(decl))
                    opts.append(decl)

        if name is None and possible_names:
            possible_names.sort(key=lambda x: -len(x[0]))  # group long options first
            name = possible_names[0][1].replace("-", "_").lower()
            if not name.isidentifier():
                name = None

        if name is None:
            if not expose_value:
                return None, opts, secondary_opts
            raise TypeError(
                f"Could not determine name for option with declarations {decls!r}"
            )

        if not opts and not secondary_opts:
            raise TypeError(
                f"No options defined but a name was passed ({name})."
                " Did you mean to declare an argument instead? Did"
                f" you mean to pass '--{name}'?"
            )

        return name, opts, secondary_opts

    def add_to_parser(self, parser: _OptionParser, ctx: Context) -> None:
        if self.multiple:
            action = "append"
        elif self.count:
            action = "count"
        else:
            action = "store"

        if self.is_flag:
            action = f"{action}_const"

            if self.is_bool_flag and self.secondary_opts:
                parser.add_option(
                    obj=self, opts=self.opts, dest=self.name, action=action, const=True
                )
                parser.add_option(
                    obj=self,
                    opts=self.secondary_opts,
                    dest=self.name,
                    action=action,
                    const=False,
                )
            else:
                parser.add_option(
                    obj=self,
                    opts=self.opts,
                    dest=self.name,
                    action=action,
                    const=self.flag_value,
                )
        else:
            parser.add_option(
                obj=self,
                opts=self.opts,
                dest=self.name,
                action=action,
                nargs=self.nargs,
            )

    def get_help_record(self, ctx: Context) -> tuple[str, str] | None:
        if self.hidden:
            return None

        any_prefix_is_slash = False

        def _write_opts(opts: cabc.Sequence[str]) -> str:
            nonlocal any_prefix_is_slash

            rv, any_slashes = join_options(opts)

            if any_slashes:
                any_prefix_is_slash = True

            if not self.is_flag and not self.count:
                rv += f" {self.make_metavar(ctx=ctx)}"

            return rv

        rv = [_write_opts(self.opts)]

        if self.secondary_opts:
            rv.append(_write_opts(self.secondary_opts))

        help = self.help or ""

        extra = self.get_help_extra(ctx)
        extra_items = []
        if "envvars" in extra:
            extra_items.append(
                _("env var: {var}").format(var=", ".join(extra["envvars"]))
            )
        if "default" in extra:
            extra_items.append(_("default: {default}").format(default=extra["default"]))
        if "range" in extra:
            extra_items.append(extra["range"])
        if "required" in extra:
            extra_items.append(_(extra["required"]))

        if extra_items:
            extra_str = "; ".join(extra_items)
            help = f"{help}  [{extra_str}]" if help else f"[{extra_str}]"

        return ("; " if any_prefix_is_slash else " / ").join(rv), help

    def get_help_extra(self, ctx: Context) -> types.OptionHelpExtra:
        extra: types.OptionHelpExtra = {}

        if self.show_envvar:
            envvar = self.envvar

            if envvar is None:
                if (
                    self.allow_from_autoenv
                    and ctx.auto_envvar_prefix is not None
                    and self.name is not None
                ):
                    envvar = f"{ctx.auto_envvar_prefix}_{self.name.upper()}"

            if envvar is not None:
                if isinstance(envvar, str):
                    extra["envvars"] = (envvar,)
                else:
                    extra["envvars"] = tuple(str(d) for d in envvar)

        # Temporarily enable resilient parsing to avoid type casting
        # failing for the default. Might be possible to extend this to
        # help formatting in general.
        resilient = ctx.resilient_parsing
        ctx.resilient_parsing = True

        try:
            default_value = self.get_default(ctx, call=False)
        finally:
            ctx.resilient_parsing = resilient

        show_default = False
        show_default_is_str = False

        if self.show_default is not None:
            if isinstance(self.show_default, str):
                show_default_is_str = show_default = True
            else:
                show_default = self.show_default
        elif ctx.show_default is not None:
            show_default = ctx.show_default

        if show_default_is_str or (show_default and (default_value is not None)):
            if show_default_is_str:
                default_string = f"({self.show_default})"
            elif isinstance(default_value, (list, tuple)):
                default_string = ", ".join(str(d) for d in default_value)
            elif inspect.isfunction(default_value):
                default_string = _("(dynamic)")
            elif self.is_bool_flag and self.secondary_opts:
                # For boolean flags that have distinct True/False opts,
                # use the opt without prefix instead of the value.
                default_string = _split_opt(
                    (self.opts if default_value else self.secondary_opts)[0]
                )[1]
            elif self.is_bool_flag and not self.secondary_opts and not default_value:
                default_string = ""
            elif default_value == "":
                default_string = '""'
            else:
                default_string = str(default_value)

            if default_string:
                extra["default"] = default_string

        if (
            isinstance(self.type, types._NumberRangeBase)
            # skip count with default range type
            and not (self.count and self.type.min == 0 and self.type.max is None)
        ):
            range_str = self.type._describe_range()

            if range_str:
                extra["range"] = range_str

        if self.required:
            extra["required"] = "required"

        return extra

    @t.overload
    def get_default(
        self, ctx: Context, call: t.Literal[True] = True
    ) -> t.Any | None: ...

    @t.overload
    def get_default(
        self, ctx: Context, call: bool = ...
    ) -> t.Any | t.Callable[[], t.Any] | None: ...

    def get_default(
        self, ctx: Context, call: bool = True
    ) -> t.Any | t.Callable[[], t.Any] | None:
        # If we're a non boolean flag our default is more complex because
        # we need to look at all flags in the same group to figure out
        # if we're the default one in which case we return the flag
        # value as default.
        if self.is_flag and not self.is_bool_flag:
            for param in ctx.command.params:
                if param.name == self.name and param.default:
                    return t.cast(Option, param).flag_value

            return None

        return super().get_default(ctx, call=call)

    def prompt_for_value(self, ctx: Context) -> t.Any:
        """This is an alternative flow that can be activated in the full
        value processing if a value does not exist.  It will prompt the
        user until a valid value exists and then returns the processed
        value as result.
        """
        assert self.prompt is not None

        # Calculate the default before prompting anything to be stable.
        default = self.get_default(ctx)

        # If this is a prompt for a flag we need to handle this
        # differently.
        if self.is_bool_flag:
            return confirm(self.prompt, default)

        # If show_default is set to True/False, provide this to `prompt` as well. For
        # non-bool values of `show_default`, we use `prompt`'s default behavior
        prompt_kwargs: t.Any = {}
        if isinstance(self.show_default, bool):
            prompt_kwargs["show_default"] = self.show_default

        return prompt(
            self.prompt,
            default=default,
            type=self.type,
            hide_input=self.hide_input,
            show_choices=self.show_choices,
            confirmation_prompt=self.confirmation_prompt,
            value_proc=lambda x: self.process_value(ctx, x),
            **prompt_kwargs,
        )

    def resolve_envvar_value(self, ctx: Context) -> str | None:
        rv = super().resolve_envvar_value(ctx)

        if rv is not None:
            if self.is_flag and self.flag_value:
                return str(self.flag_value)
            return rv

        if (
            self.allow_from_autoenv
            and ctx.auto_envvar_prefix is not None
            and self.name is not None
        ):
            envvar = f"{ctx.auto_envvar_prefix}_{self.name.upper()}"
            rv = os.environ.get(envvar)

            if rv:
                return rv

        return None

    def value_from_envvar(self, ctx: Context) -> t.Any | None:
        rv: t.Any | None = self.resolve_envvar_value(ctx)

        if rv is None:
            return None

        value_depth = (self.nargs != 1) + bool(self.multiple)

        if value_depth > 0:
            rv = self.type.split_envvar_value(rv)

            if self.multiple and self.nargs != 1:
                rv = batch(rv, self.nargs)

        return rv

    def consume_value(
        self, ctx: Context, opts: cabc.Mapping[str, Parameter]
    ) -> tuple[t.Any, ParameterSource]:
        value, source = super().consume_value(ctx, opts)

        # The parser will emit a sentinel value if the option can be
        # given as a flag without a value. This is different from None
        # to distinguish from the flag not being given at all.
        if value is _flag_needs_value:
            if self.prompt is not None and not ctx.resilient_parsing:
                value = self.prompt_for_value(ctx)
                source = ParameterSource.PROMPT
            else:
                value = self.flag_value
                source = ParameterSource.COMMANDLINE

        elif (
            self.multiple
            and value is not None
            and any(v is _flag_needs_value for v in value)
        ):
            value = [self.flag_value if v is _flag_needs_value else v for v in value]
            source = ParameterSource.COMMANDLINE

        # The value wasn't set, or used the param's default, prompt if
        # prompting is enabled.
        elif (
            source in {None, ParameterSource.DEFAULT}
            and self.prompt is not None
            and (self.required or self.prompt_required)
            and not ctx.resilient_parsing
        ):
            value = self.prompt_for_value(ctx)
            source = ParameterSource.PROMPT

        return value, source


class Argument(Parameter):
    """Arguments are positional parameters to a command.  They generally
    provide fewer features than options but can have infinite ``nargs``
    and are required by default.

    All parameters are passed onwards to the constructor of :class:`Parameter`.
    """

    param_type_name = "argument"

    def __init__(
        self,
        param_decls: cabc.Sequence[str],
        required: bool | None = None,
        **attrs: t.Any,
    ) -> None:
        if required is None:
            if attrs.get("default") is not None:
                required = False
            else:
                required = attrs.get("nargs", 1) > 0

        if "multiple" in attrs:
            raise TypeError("__init__() got an unexpected keyword argument 'multiple'.")

        super().__init__(param_decls, required=required, **attrs)

        if __debug__:
            if self.default is not None and self.nargs == -1:
                raise TypeError("'default' is not supported for nargs=-1.")

    @property
    def human_readable_name(self) -> str:
        if self.metavar is not None:
            return self.metavar
        return self.name.upper()  # type: ignore

    def make_metavar(self, ctx: Context) -> str:
        if self.metavar is not None:
            return self.metavar
        var = self.type.get_metavar(param=self, ctx=ctx)
        if not var:
            var = self.name.upper()  # type: ignore
        if self.deprecated:
            var += "!"
        if not self.required:
            var = f"[{var}]"
        if self.nargs != 1:
            var += "..."
        return var

    def _parse_decls(
        self, decls: cabc.Sequence[str], expose_value: bool
    ) -> tuple[str | None, list[str], list[str]]:
        if not decls:
            if not expose_value:
                return None, [], []
            raise TypeError("Argument is marked as exposed, but does not have a name.")
        if len(decls) == 1:
            name = arg = decls[0]
            name = name.replace("-", "_").lower()
        else:
            raise TypeError(
                "Arguments take exactly one parameter declaration, got"
                f" {len(decls)}: {decls}."
            )
        return name, [arg], []

    def get_usage_pieces(self, ctx: Context) -> list[str]:
        return [self.make_metavar(ctx)]

    def get_error_hint(self, ctx: Context) -> str:
        return f"'{self.make_metavar(ctx)}'"

    def add_to_parser(self, parser: _OptionParser, ctx: Context) -> None:
        parser.add_argument(dest=self.name, nargs=self.nargs, obj=self)


def __getattr__(name: str) -> object:
    import warnings

    if name == "BaseCommand":
        warnings.warn(
            "'BaseCommand' is deprecated and will be removed in Click 9.0. Use"
            " 'Command' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _BaseCommand

    if name == "MultiCommand":
        warnings.warn(
            "'MultiCommand' is deprecated and will be removed in Click 9.0. Use"
            " 'Group' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _MultiCommand

    raise AttributeError(name)

# === NexusCore/openenv\Lib\site-packages\numpy\lib\__init__.py ===
"""
``numpy.lib`` is mostly a space for implementing functions that don't
belong in core or in another NumPy submodule with a clear purpose
(e.g. ``random``, ``fft``, ``linalg``, ``ma``).

``numpy.lib``'s private submodules contain basic functions that are used by
other public modules and are useful to have in the main name-space.

"""

# Public submodules
# Note: recfunctions is public, but not imported
from numpy._core._multiarray_umath import add_docstring, tracemalloc_domain
from numpy._core.function_base import add_newdoc

# Private submodules
# load module names. See https://github.com/networkx/networkx/issues/5838
from . import (
    _arraypad_impl,
    _arraysetops_impl,
    _arrayterator_impl,
    _function_base_impl,
    _histograms_impl,
    _index_tricks_impl,
    _nanfunctions_impl,
    _npyio_impl,
    _polynomial_impl,
    _shape_base_impl,
    _stride_tricks_impl,
    _twodim_base_impl,
    _type_check_impl,
    _ufunclike_impl,
    _utils_impl,
    _version,
    array_utils,
    format,
    introspect,
    mixins,
    npyio,
    scimath,
    stride_tricks,
)

# numpy.lib namespace members
from ._arrayterator_impl import Arrayterator
from ._version import NumpyVersion

__all__ = [
    "Arrayterator", "add_docstring", "add_newdoc", "array_utils",
    "format", "introspect", "mixins", "NumpyVersion", "npyio", "scimath",
    "stride_tricks", "tracemalloc_domain",
]

add_newdoc.__module__ = "numpy.lib"

from numpy._pytesttester import PytestTester

test = PytestTester(__name__)
del PytestTester

def __getattr__(attr):
    # Warn for deprecated/removed aliases
    import math
    import warnings

    if attr == "math":
        warnings.warn(
            "`np.lib.math` is a deprecated alias for the standard library "
            "`math` module (Deprecated Numpy 1.25). Replace usages of "
            "`numpy.lib.math` with `math`", DeprecationWarning, stacklevel=2)
        return math
    elif attr == "emath":
        raise AttributeError(
            "numpy.lib.emath was an alias for emath module that was removed "
            "in NumPy 2.0. Replace usages of numpy.lib.emath with "
            "numpy.emath.",
            name=None
        )
    elif attr in (
        "histograms", "type_check", "nanfunctions", "function_base",
        "arraypad", "arraysetops", "ufunclike", "utils", "twodim_base",
        "shape_base", "polynomial", "index_tricks",
    ):
        raise AttributeError(
            f"numpy.lib.{attr} is now private. If you are using a public "
            "function, it should be available in the main numpy namespace, "
            "otherwise check the NumPy 2.0 migration guide.",
            name=None
        )
    elif attr == "arrayterator":
        raise AttributeError(
            "numpy.lib.arrayterator submodule is now private. To access "
            "Arrayterator class use numpy.lib.Arrayterator.",
            name=None
        )
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {attr!r}")

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_ufunclike.py ===
import numpy as np
from numpy import fix, isneginf, isposinf
from numpy.testing import assert_, assert_array_equal, assert_equal, assert_raises


class TestUfunclike:

    def test_isposinf(self):
        a = np.array([np.inf, -np.inf, np.nan, 0.0, 3.0, -3.0])
        out = np.zeros(a.shape, bool)
        tgt = np.array([True, False, False, False, False, False])

        res = isposinf(a)
        assert_equal(res, tgt)
        res = isposinf(a, out)
        assert_equal(res, tgt)
        assert_equal(out, tgt)

        a = a.astype(np.complex128)
        with assert_raises(TypeError):
            isposinf(a)

    def test_isneginf(self):
        a = np.array([np.inf, -np.inf, np.nan, 0.0, 3.0, -3.0])
        out = np.zeros(a.shape, bool)
        tgt = np.array([False, True, False, False, False, False])

        res = isneginf(a)
        assert_equal(res, tgt)
        res = isneginf(a, out)
        assert_equal(res, tgt)
        assert_equal(out, tgt)

        a = a.astype(np.complex128)
        with assert_raises(TypeError):
            isneginf(a)

    def test_fix(self):
        a = np.array([[1.0, 1.1, 1.5, 1.8], [-1.0, -1.1, -1.5, -1.8]])
        out = np.zeros(a.shape, float)
        tgt = np.array([[1., 1., 1., 1.], [-1., -1., -1., -1.]])

        res = fix(a)
        assert_equal(res, tgt)
        res = fix(a, out)
        assert_equal(res, tgt)
        assert_equal(out, tgt)
        assert_equal(fix(3.14), 3)

    def test_fix_with_subclass(self):
        class MyArray(np.ndarray):
            def __new__(cls, data, metadata=None):
                res = np.array(data, copy=True).view(cls)
                res.metadata = metadata
                return res

            def __array_wrap__(self, obj, context=None, return_scalar=False):
                if not isinstance(obj, MyArray):
                    obj = obj.view(MyArray)
                if obj.metadata is None:
                    obj.metadata = self.metadata
                return obj

            def __array_finalize__(self, obj):
                self.metadata = getattr(obj, 'metadata', None)
                return self

        a = np.array([1.1, -1.1])
        m = MyArray(a, metadata='foo')
        f = fix(m)
        assert_array_equal(f, np.array([1, -1]))
        assert_(isinstance(f, MyArray))
        assert_equal(f.metadata, 'foo')

        # check 0d arrays don't decay to scalars
        m0d = m[0, ...]
        m0d.metadata = 'bar'
        f0d = fix(m0d)
        assert_(isinstance(f0d, MyArray))
        assert_equal(f0d.metadata, 'bar')

    def test_scalar(self):
        x = np.inf
        actual = np.isposinf(x)
        expected = np.True_
        assert_equal(actual, expected)
        assert_equal(type(actual), type(expected))

        x = -3.4
        actual = np.fix(x)
        expected = np.float64(-3.0)
        assert_equal(actual, expected)
        assert_equal(type(actual), type(expected))

        out = np.array(0.0)
        actual = np.fix(x, out=out)
        assert_(actual is out)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\utils.py ===
import asyncio
import copy
import hashlib
import json
import os
import smtplib
import threading
import time
import traceback
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Union,
    cast,
    overload,
)

from litellm.constants import MAX_TEAM_LIST_LIMIT
from litellm.proxy._types import (
    DB_CONNECTION_ERROR_TYPES,
    CommonProxyErrors,
    ProxyErrorTypes,
    ProxyException,
    SpendLogsMetadata,
    SpendLogsPayload,
)
from litellm.types.guardrails import GuardrailEventHooks

try:
    import backoff
except ImportError:
    raise ImportError(
        "backoff is not installed. Please install it via 'pip install backoff'"
    )

from fastapi import HTTPException, status

import litellm
import litellm.litellm_core_utils
import litellm.litellm_core_utils.litellm_logging
from litellm import (
    EmbeddingResponse,
    ImageResponse,
    ModelResponse,
    ModelResponseStream,
    Router,
)
from litellm._logging import verbose_proxy_logger
from litellm._service_logger import ServiceLogging, ServiceTypes
from litellm.litellm_core_utils.safe_json_dumps import safe_dumps
from litellm.litellm_core_utils.safe_json_loads import safe_json_loads
from litellm.caching.caching import DualCache, RedisCache
from litellm.exceptions import RejectedRequestError
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.integrations.custom_logger import CustomLogger
from litellm.integrations.SlackAlerting.slack_alerting import SlackAlerting
from litellm.integrations.SlackAlerting.utils import _add_langfuse_trace_id_to_alert
from litellm.litellm_core_utils.litellm_logging import Logging
from litellm.llms.custom_httpx.httpx_handler import HTTPHandler
from litellm.proxy._types import (
    AlertType,
    CallInfo,
    LiteLLM_VerificationTokenView,
    Member,
    UserAPIKeyAuth,
)
from litellm.proxy.db.create_views import (
    create_missing_views,
    should_create_missing_views,
)
from litellm.proxy.db.db_spend_update_writer import DBSpendUpdateWriter
from litellm.proxy.db.log_db_metrics import log_db_metrics
from litellm.proxy.db.prisma_client import PrismaWrapper
from litellm.proxy.hooks import PROXY_HOOKS, get_proxy_hook
from litellm.proxy.hooks.cache_control_check import _PROXY_CacheControlCheck
from litellm.proxy.hooks.max_budget_limiter import _PROXY_MaxBudgetLimiter
from litellm.proxy.hooks.parallel_request_limiter import (
    _PROXY_MaxParallelRequestsHandler,
)
from litellm.proxy.litellm_pre_call_utils import LiteLLMProxyRequestSetup
from litellm.secret_managers.main import str_to_bool
from litellm.types.integrations.slack_alerting import DEFAULT_ALERT_TYPES
from litellm.types.utils import CallTypes, LLMResponseTypes, LoggedLiteLLMParams

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    Span = Union[_Span, Any]
else:
    Span = Any


def print_verbose(print_statement):
    """
    Prints the given `print_statement` to the console if `litellm.set_verbose` is True.
    Also logs the `print_statement` at the debug level using `verbose_proxy_logger`.

    :param print_statement: The statement to be printed and logged.
    :type print_statement: Any
    """
    import traceback

    verbose_proxy_logger.debug("{}\n{}".format(print_statement, traceback.format_exc()))
    if litellm.set_verbose:
        print(f"LiteLLM Proxy: {print_statement}")  # noqa


def safe_deep_copy(data):
    """
    Safe Deep Copy

    The LiteLLM Request has some object that can-not be pickled / deep copied

    Use this function to safely deep copy the LiteLLM Request
    """
    if litellm.safe_memory_mode is True:
        return data

    litellm_parent_otel_span: Optional[Any] = None
    # Step 1: Remove the litellm_parent_otel_span
    litellm_parent_otel_span = None
    if isinstance(data, dict):
        # remove litellm_parent_otel_span since this is not picklable
        if "metadata" in data and "litellm_parent_otel_span" in data["metadata"]:
            litellm_parent_otel_span = data["metadata"].pop("litellm_parent_otel_span")
    new_data = copy.deepcopy(data)

    # Step 2: re-add the litellm_parent_otel_span after doing a deep copy
    if isinstance(data, dict) and litellm_parent_otel_span is not None:
        if "metadata" in data:
            data["metadata"]["litellm_parent_otel_span"] = litellm_parent_otel_span
    return new_data


class InternalUsageCache:
    def __init__(self, dual_cache: DualCache):
        self.dual_cache: DualCache = dual_cache

    async def async_get_cache(
        self,
        key,
        litellm_parent_otel_span: Union[Span, None],
        local_only: bool = False,
        **kwargs,
    ) -> Any:
        return await self.dual_cache.async_get_cache(
            key=key,
            local_only=local_only,
            parent_otel_span=litellm_parent_otel_span,
            **kwargs,
        )

    async def async_set_cache(
        self,
        key,
        value,
        litellm_parent_otel_span: Union[Span, None],
        local_only: bool = False,
        **kwargs,
    ) -> None:
        return await self.dual_cache.async_set_cache(
            key=key,
            value=value,
            local_only=local_only,
            litellm_parent_otel_span=litellm_parent_otel_span,
            **kwargs,
        )

    async def async_batch_set_cache(
        self,
        cache_list: List,
        litellm_parent_otel_span: Union[Span, None],
        local_only: bool = False,
        **kwargs,
    ) -> None:
        return await self.dual_cache.async_set_cache_pipeline(
            cache_list=cache_list,
            local_only=local_only,
            litellm_parent_otel_span=litellm_parent_otel_span,
            **kwargs,
        )

    async def async_batch_get_cache(
        self,
        keys: list,
        parent_otel_span: Optional[Span] = None,
        local_only: bool = False,
    ):
        return await self.dual_cache.async_batch_get_cache(
            keys=keys,
            parent_otel_span=parent_otel_span,
            local_only=local_only,
        )

    async def async_increment_cache(
        self,
        key,
        value: float,
        litellm_parent_otel_span: Union[Span, None],
        local_only: bool = False,
        **kwargs,
    ):
        return await self.dual_cache.async_increment_cache(
            key=key,
            value=value,
            local_only=local_only,
            parent_otel_span=litellm_parent_otel_span,
            **kwargs,
        )

    def set_cache(
        self,
        key,
        value,
        local_only: bool = False,
        **kwargs,
    ) -> None:
        return self.dual_cache.set_cache(
            key=key,
            value=value,
            local_only=local_only,
            **kwargs,
        )

    def get_cache(
        self,
        key,
        local_only: bool = False,
        **kwargs,
    ) -> Any:
        return self.dual_cache.get_cache(
            key=key,
            local_only=local_only,
            **kwargs,
        )


### LOGGING ###
class ProxyLogging:
    """
    Logging/Custom Handlers for proxy.

    Implemented mainly to:
    - log successful/failed db read/writes
    - support the max parallel request integration
    """

    def __init__(
        self,
        user_api_key_cache: DualCache,
        premium_user: bool = False,
    ):
        ## INITIALIZE  LITELLM CALLBACKS ##
        self.call_details: dict = {}
        self.call_details["user_api_key_cache"] = user_api_key_cache
        self.internal_usage_cache: InternalUsageCache = InternalUsageCache(
            dual_cache=DualCache(default_in_memory_ttl=1)  # ping redis cache every 1s
        )
        self.max_parallel_request_limiter = _PROXY_MaxParallelRequestsHandler(
            self.internal_usage_cache
        )
        self.max_budget_limiter = _PROXY_MaxBudgetLimiter()
        self.cache_control_check = _PROXY_CacheControlCheck()
        self.alerting: Optional[List] = None
        self.alerting_threshold: float = 300  # default to 5 min. threshold
        self.alert_types: List[AlertType] = DEFAULT_ALERT_TYPES
        self.alert_to_webhook_url: Optional[dict] = None
        self.slack_alerting_instance: SlackAlerting = SlackAlerting(
            alerting_threshold=self.alerting_threshold,
            alerting=self.alerting,
            internal_usage_cache=self.internal_usage_cache.dual_cache,
        )
        self.premium_user = premium_user
        self.service_logging_obj = ServiceLogging()
        self.db_spend_update_writer = DBSpendUpdateWriter()
        self.proxy_hook_mapping: Dict[str, CustomLogger] = {}

        # Guard flags to prevent duplicate background tasks
        self.daily_report_started: bool = False
        self.hanging_requests_check_started: bool = False

    def startup_event(
        self,
        llm_router: Optional[Router],
        redis_usage_cache: Optional[RedisCache],
    ):
        """Initialize logging and alerting on proxy startup"""
        ## UPDATE SLACK ALERTING ##
        self.slack_alerting_instance.update_values(llm_router=llm_router)

        ## UPDATE INTERNAL USAGE CACHE ##
        self.update_values(
            redis_cache=redis_usage_cache
        )  # used by parallel request limiter for rate limiting keys across instances

        self._init_litellm_callbacks(
            llm_router=llm_router
        )  # INITIALIZE LITELLM CALLBACKS ON SERVER STARTUP <- do this to catch any logging errors on startup, not when calls are being made

        if (
            self.slack_alerting_instance is not None
            and "daily_reports" in self.slack_alerting_instance.alert_types
            and not self.daily_report_started
        ):
            asyncio.create_task(
                self.slack_alerting_instance._run_scheduled_daily_report(
                    llm_router=llm_router
                )
            )  # RUN DAILY REPORT (if scheduled)
            self.daily_report_started = True

        if (
            self.slack_alerting_instance is not None
            and AlertType.llm_requests_hanging
            in self.slack_alerting_instance.alert_types
            and not self.hanging_requests_check_started
        ):
            asyncio.create_task(
                self.slack_alerting_instance.hanging_request_check.check_for_hanging_requests()
            )  # RUN HANGING REQUEST CHECK (if user wants to alert on hanging requests)
            self.hanging_requests_check_started = True

    def update_values(
        self,
        alerting: Optional[List] = None,
        alerting_threshold: Optional[float] = None,
        redis_cache: Optional[RedisCache] = None,
        alert_types: Optional[List[AlertType]] = None,
        alerting_args: Optional[dict] = None,
        alert_to_webhook_url: Optional[dict] = None,
    ):
        updated_slack_alerting: bool = False
        if alerting is not None:
            self.alerting = alerting
            updated_slack_alerting = True
        if alerting_threshold is not None:
            self.alerting_threshold = alerting_threshold
            updated_slack_alerting = True
        if alert_types is not None:
            self.alert_types = alert_types
            updated_slack_alerting = True
        if alert_to_webhook_url is not None:
            self.alert_to_webhook_url = alert_to_webhook_url
            updated_slack_alerting = True

        if updated_slack_alerting is True:
            self.slack_alerting_instance.update_values(
                alerting=self.alerting,
                alerting_threshold=self.alerting_threshold,
                alert_types=self.alert_types,
                alerting_args=alerting_args,
                alert_to_webhook_url=self.alert_to_webhook_url,
            )

            if self.alerting is not None and "slack" in self.alerting:
                # NOTE: ENSURE we only add callbacks when alerting is on
                # We should NOT add callbacks when alerting is off
                if "daily_reports" in self.alert_types:
                    litellm.logging_callback_manager.add_litellm_callback(self.slack_alerting_instance)  # type: ignore
                litellm.logging_callback_manager.add_litellm_success_callback(
                    self.slack_alerting_instance.response_taking_too_long_callback
                )

        if redis_cache is not None:
            self.internal_usage_cache.dual_cache.redis_cache = redis_cache
            self.db_spend_update_writer.redis_update_buffer.redis_cache = redis_cache
            self.db_spend_update_writer.pod_lock_manager.redis_cache = redis_cache

    def _add_proxy_hooks(self, llm_router: Optional[Router] = None):
        """
        Add proxy hooks to litellm.callbacks
        """
        from litellm.proxy.proxy_server import prisma_client

        for hook in PROXY_HOOKS:
            proxy_hook = get_proxy_hook(hook)
            import inspect

            expected_args = inspect.getfullargspec(proxy_hook).args
            passed_in_args: Dict[str, Any] = {}
            if "internal_usage_cache" in expected_args:
                passed_in_args["internal_usage_cache"] = self.internal_usage_cache
            if "prisma_client" in expected_args:
                passed_in_args["prisma_client"] = prisma_client
            proxy_hook_obj = cast(CustomLogger, proxy_hook(**passed_in_args))
            litellm.logging_callback_manager.add_litellm_callback(proxy_hook_obj)

            self.proxy_hook_mapping[hook] = proxy_hook_obj

    def get_proxy_hook(self, hook: str) -> Optional[CustomLogger]:
        """
        Get a proxy hook from the proxy_hook_mapping
        """
        return self.proxy_hook_mapping.get(hook)

    def _init_litellm_callbacks(self, llm_router: Optional[Router] = None):
        self._add_proxy_hooks(llm_router)
        litellm.logging_callback_manager.add_litellm_callback(self.service_logging_obj)  # type: ignore
        for callback in litellm.callbacks:
            if isinstance(callback, str):
                callback = litellm.litellm_core_utils.litellm_logging._init_custom_logger_compatible_class(  # type: ignore
                    callback,
                    internal_usage_cache=self.internal_usage_cache.dual_cache,
                    llm_router=llm_router,
                )
                if callback is None:
                    continue
            if callback not in litellm.input_callback:
                litellm.input_callback.append(callback)  # type: ignore
            if callback not in litellm.success_callback:
                litellm.logging_callback_manager.add_litellm_success_callback(callback)  # type: ignore
            if callback not in litellm.failure_callback:
                litellm.logging_callback_manager.add_litellm_failure_callback(callback)  # type: ignore
            if callback not in litellm._async_success_callback:
                litellm.logging_callback_manager.add_litellm_async_success_callback(callback)  # type: ignore
            if callback not in litellm._async_failure_callback:
                litellm.logging_callback_manager.add_litellm_async_failure_callback(callback)  # type: ignore
            if callback not in litellm.service_callback:
                litellm.service_callback.append(callback)  # type: ignore

        if (
            len(litellm.input_callback) > 0
            or len(litellm.success_callback) > 0
            or len(litellm.failure_callback) > 0
        ):
            callback_list = list(
                set(
                    litellm.input_callback
                    + litellm.success_callback
                    + litellm.failure_callback
                )
            )
            litellm.litellm_core_utils.litellm_logging.set_callbacks(
                callback_list=callback_list
            )

    async def update_request_status(
        self, litellm_call_id: str, status: Literal["success", "fail"]
    ):
        # only use this if slack alerting is being used
        if self.alerting is None:
            return

        # current alerting threshold
        alerting_threshold: float = self.alerting_threshold

        # add a 100 second buffer to the alerting threshold
        # ensures we don't send errant hanging request slack alerts
        alerting_threshold += 100

        await self.internal_usage_cache.async_set_cache(
            key="request_status:{}".format(litellm_call_id),
            value=status,
            local_only=True,
            ttl=alerting_threshold,
            litellm_parent_otel_span=None,
        )

    async def process_pre_call_hook_response(self, response, data, call_type):
        if isinstance(response, Exception):
            raise response
        if isinstance(response, dict):
            return response
        if isinstance(response, str):
            if call_type in ["completion", "text_completion"]:
                raise RejectedRequestError(
                    message=response,
                    model=data.get("model", ""),
                    llm_provider="",
                    request_data=data,
                )
            else:
                raise HTTPException(status_code=400, detail={"error": response})
        return data

    # The actual implementation of the function
    @overload
    async def pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        data: None,
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
    ) -> None:
        pass

    @overload
    async def pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
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
    ) -> dict:
        pass

    async def pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        data: Optional[dict],
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
    ) -> Optional[dict]:
        """
        Allows users to modify/reject the incoming request to the proxy, without having to deal with parsing Request body.

        Covers:
        1. /chat/completions
        2. /embeddings
        3. /image/generation
        """
        verbose_proxy_logger.debug("Inside Proxy Logging Pre-call hook!")

        self._init_response_taking_too_long_task(data=data)

        if data is None:
            return None

        try:
            for callback in litellm.callbacks:
                _callback = None
                if isinstance(callback, str):
                    _callback = litellm.litellm_core_utils.litellm_logging.get_custom_logger_compatible_class(
                        callback
                    )
                else:
                    _callback = callback  # type: ignore
                if _callback is not None and isinstance(_callback, CustomGuardrail):
                    from litellm.types.guardrails import GuardrailEventHooks

                    if (
                        _callback.should_run_guardrail(
                            data=data, event_type=GuardrailEventHooks.pre_call
                        )
                        is not True
                    ):
                        continue

                    response = await _callback.async_pre_call_hook(
                        user_api_key_dict=user_api_key_dict,
                        cache=self.call_details["user_api_key_cache"],
                        data=data,  # type: ignore
                        call_type=call_type,
                    )
                    if response is not None:
                        data = await self.process_pre_call_hook_response(
                            response=response, data=data, call_type=call_type
                        )

                elif (
                    _callback is not None
                    and isinstance(_callback, CustomLogger)
                    and "async_pre_call_hook" in vars(_callback.__class__)
                    and _callback.__class__.async_pre_call_hook
                    != CustomLogger.async_pre_call_hook
                ):
                    response = await _callback.async_pre_call_hook(
                        user_api_key_dict=user_api_key_dict,
                        cache=self.call_details["user_api_key_cache"],
                        data=data,  # type: ignore
                        call_type=call_type,
                    )
                    if response is not None:
                        data = await self.process_pre_call_hook_response(
                            response=response, data=data, call_type=call_type
                        )

            return data
        except Exception as e:
            raise e

    async def during_call_hook(
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        call_type: Literal[
            "completion",
            "responses",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
        ],
    ):
        """
        Runs the CustomGuardrail's async_moderation_hook()
        """
        for callback in litellm.callbacks:
            try:
                if isinstance(callback, CustomGuardrail):
                    ################################################################
                    # Check if guardrail should be run for GuardrailEventHooks.during_call hook
                    ################################################################

                    # V1 implementation - backwards compatibility
                    if callback.event_hook is None and hasattr(
                        callback, "moderation_check"
                    ):
                        if callback.moderation_check == "pre_call":  # type: ignore
                            return
                    else:
                        # Main - V2 Guardrails implementation
                        from litellm.types.guardrails import GuardrailEventHooks

                        if (
                            callback.should_run_guardrail(
                                data=data, event_type=GuardrailEventHooks.during_call
                            )
                            is not True
                        ):
                            continue
                    await callback.async_moderation_hook(
                        data=data,
                        user_api_key_dict=user_api_key_dict,
                        call_type=call_type,
                    )
            except Exception as e:
                raise e
        return data

    async def failed_tracking_alert(
        self,
        error_message: str,
        failing_model: str,
    ):
        if self.alerting is None:
            return

        if self.slack_alerting_instance:
            await self.slack_alerting_instance.failed_tracking_alert(
                error_message=error_message,
                failing_model=failing_model,
            )

    async def budget_alerts(
        self,
        type: Literal[
            "token_budget",
            "user_budget",
            "soft_budget",
            "team_budget",
            "proxy_budget",
            "projected_limit_exceeded",
        ],
        user_info: CallInfo,
    ):
        if self.alerting is None:
            # do nothing if alerting is not switched on
            return
        await self.slack_alerting_instance.budget_alerts(
            type=type,
            user_info=user_info,
        )

    async def alerting_handler(
        self,
        message: str,
        level: Literal["Low", "Medium", "High"],
        alert_type: AlertType,
        request_data: Optional[dict] = None,
    ):
        """
        Alerting based on thresholds: - https://github.com/BerriAI/litellm/issues/1298

        - Responses taking too long
        - Requests are hanging
        - Calls are failing
        - DB Read/Writes are failing
        - Proxy Close to max budget
        - Key Close to max budget

        Parameters:
            level: str - Low|Medium|High - if calls might fail (Medium) or are failing (High); Currently, no alerts would be 'Low'.
            message: str - what is the alert about
        """
        if self.alerting is None:
            return

        from datetime import datetime

        # Get the current timestamp
        current_time = datetime.now().strftime("%H:%M:%S")
        _proxy_base_url = os.getenv("PROXY_BASE_URL", None)
        formatted_message = (
            f"Level: `{level}`\nTimestamp: `{current_time}`\n\nMessage: {message}"
        )
        if _proxy_base_url is not None:
            formatted_message += f"\n\nProxy URL: `{_proxy_base_url}`"

        extra_kwargs = {}
        alerting_metadata = {}
        if request_data is not None:
            _url = await _add_langfuse_trace_id_to_alert(request_data=request_data)

            if _url is not None:
                extra_kwargs["🪢 Langfuse Trace"] = _url
                formatted_message += "\n\n🪢 Langfuse Trace: {}".format(_url)
            if (
                "metadata" in request_data
                and request_data["metadata"].get("alerting_metadata", None) is not None
                and isinstance(request_data["metadata"]["alerting_metadata"], dict)
            ):
                alerting_metadata = request_data["metadata"]["alerting_metadata"]
        for client in self.alerting:
            if client == "slack":
                await self.slack_alerting_instance.send_alert(
                    message=message,
                    level=level,
                    alert_type=alert_type,
                    user_info=None,
                    alerting_metadata=alerting_metadata,
                    **extra_kwargs,
                )
            elif client == "sentry":
                if litellm.utils.sentry_sdk_instance is not None:
                    litellm.utils.sentry_sdk_instance.capture_message(formatted_message)
                else:
                    raise Exception("Missing SENTRY_DSN from environment")

    async def failure_handler(
        self, original_exception, duration: float, call_type: str, traceback_str=""
    ):
        """
        Log failed db read/writes

        Currently only logs exceptions to sentry
        """
        ### ALERTING ###
        if AlertType.db_exceptions not in self.alert_types:
            return
        if isinstance(original_exception, HTTPException):
            if isinstance(original_exception.detail, str):
                error_message = original_exception.detail
            elif isinstance(original_exception.detail, dict):
                error_message = json.dumps(original_exception.detail)
            else:
                error_message = str(original_exception)
        else:
            error_message = str(original_exception)
        if isinstance(traceback_str, str):
            error_message += traceback_str[:1000]
        asyncio.create_task(
            self.alerting_handler(
                message=f"DB read/write call failed: {error_message}",
                level="High",
                alert_type=AlertType.db_exceptions,
                request_data={},
            )
        )

        if hasattr(self, "service_logging_obj"):
            await self.service_logging_obj.async_service_failure_hook(
                service=ServiceTypes.DB,
                duration=duration,
                error=error_message,
                call_type=call_type,
            )

        if litellm.utils.capture_exception:
            litellm.utils.capture_exception(error=original_exception)

    async def post_call_failure_hook(
        self,
        request_data: dict,
        original_exception: Exception,
        user_api_key_dict: UserAPIKeyAuth,
        error_type: Optional[ProxyErrorTypes] = None,
        route: Optional[str] = None,
        traceback_str: Optional[str] = None,
    ):
        """
        Allows users to raise custom exceptions/log when a call fails, without having to deal with parsing Request body.

        Covers:
        1. /chat/completions
        2. /embeddings
        3. /image/generation

        Args:
            - request_data: dict - The request data.
            - original_exception: Exception - The original exception.
            - user_api_key_dict: UserAPIKeyAuth - The user api key dict.
            - error_type: Optional[ProxyErrorTypes] - The error type.
            - route: Optional[str] - The route.
            - traceback_str: Optional[str] - The traceback string, sometimes upstream endpoints might need to send the upstream traceback. In which case we use this
        """

        ### ALERTING ###
        await self.update_request_status(
            litellm_call_id=request_data.get("litellm_call_id", ""), status="fail"
        )
        if AlertType.llm_exceptions in self.alert_types and not isinstance(
            original_exception, HTTPException
        ):
            """
            Just alert on LLM API exceptions. Do not alert on user errors

            Related issue - https://github.com/BerriAI/litellm/issues/3395
            """
            litellm_debug_info = getattr(original_exception, "litellm_debug_info", None)
            exception_str = str(original_exception)
            if litellm_debug_info is not None:
                exception_str += litellm_debug_info

            asyncio.create_task(
                self.alerting_handler(
                    message=f"LLM API call failed: `{exception_str}`",
                    level="High",
                    alert_type=AlertType.llm_exceptions,
                    request_data=request_data,
                )
            )

        ### LOGGING ###
        if self._is_proxy_only_error(
            original_exception=original_exception, error_type=error_type
        ):
            await self._handle_logging_proxy_only_error(
                request_data=request_data,
                user_api_key_dict=user_api_key_dict,
                route=route,
                original_exception=original_exception,
            )

        for callback in litellm.callbacks:
            try:
                _callback: Optional[CustomLogger] = None
                if isinstance(callback, str):
                    _callback = litellm.litellm_core_utils.litellm_logging.get_custom_logger_compatible_class(
                        callback
                    )
                else:
                    _callback = callback  # type: ignore
                if _callback is not None and isinstance(_callback, CustomLogger):
                    asyncio.create_task(
                        _callback.async_post_call_failure_hook(
                            request_data=request_data,
                            user_api_key_dict=user_api_key_dict,
                            original_exception=original_exception,
                            traceback_str=traceback_str,
                        )
                    )
            except Exception as e:
                verbose_proxy_logger.exception(
                    f"[Non-Blocking] Error in post_call_failure_hook: {e}"
                )
        return

    def _is_proxy_only_error(
        self,
        original_exception: Exception,
        error_type: Optional[ProxyErrorTypes] = None,
    ) -> bool:
        """
        Return True if the error is a Proxy Only Error

        Prevents double logging of LLM API exceptions

        e.g should only return True for:
            - Authentication Errors from user_api_key_auth
            - HTTP HTTPException (rate limit errors)
        """
        return isinstance(original_exception, HTTPException) or (
            error_type == ProxyErrorTypes.auth_error
        )

    async def _handle_logging_proxy_only_error(
        self,
        request_data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        route: Optional[str] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        Handle logging for proxy only errors by calling `litellm_logging_obj.async_failure_handler`

        Is triggered when self._is_proxy_only_error() returns True
        """
        litellm_logging_obj: Optional[Logging] = request_data.get(
            "litellm_logging_obj", None
        )
        if litellm_logging_obj is None:
            import uuid

            request_data["litellm_call_id"] = str(uuid.uuid4())
            user_api_key_logged_metadata = (
                LiteLLMProxyRequestSetup.get_sanitized_user_information_from_key(
                    user_api_key_dict=user_api_key_dict
                )
            )

            litellm_logging_obj, data = litellm.utils.function_setup(
                original_function=route or "IGNORE_THIS",
                rules_obj=litellm.utils.Rules(),
                start_time=datetime.now(),
                **request_data,
            )
            if "metadata" not in request_data:
                request_data["metadata"] = {}
            request_data["metadata"].update(user_api_key_logged_metadata)

        if litellm_logging_obj is not None:
            ## UPDATE LOGGING INPUT
            _optional_params = {}
            _litellm_params = {}

            litellm_param_keys = LoggedLiteLLMParams.__annotations__.keys()
            for k, v in request_data.items():
                if k in litellm_param_keys:
                    _litellm_params[k] = v
                elif k != "model" and k != "user":
                    _optional_params[k] = v

            litellm_logging_obj.update_environment_variables(
                model=request_data.get("model", ""),
                user=request_data.get("user", ""),
                optional_params=_optional_params,
                litellm_params=_litellm_params,
            )

            input: Union[list, str, dict] = ""
            if "messages" in request_data and isinstance(
                request_data["messages"], list
            ):
                input = request_data["messages"]
                litellm_logging_obj.model_call_details["messages"] = input
                litellm_logging_obj.call_type = CallTypes.acompletion.value
            elif "prompt" in request_data and isinstance(request_data["prompt"], str):
                input = request_data["prompt"]
                litellm_logging_obj.model_call_details["prompt"] = input
                litellm_logging_obj.call_type = CallTypes.atext_completion.value
            elif "input" in request_data and isinstance(request_data["input"], list):
                input = request_data["input"]
                litellm_logging_obj.model_call_details["input"] = input
                litellm_logging_obj.call_type = CallTypes.aembedding.value
            litellm_logging_obj.pre_call(
                input=input,
                api_key="",
            )

            # log the custom exception
            await litellm_logging_obj.async_failure_handler(
                exception=original_exception,
                traceback_exception=traceback.format_exc(),
            )

            threading.Thread(
                target=litellm_logging_obj.failure_handler,
                args=(
                    original_exception,
                    traceback.format_exc(),
                ),
            ).start()

    async def post_call_success_hook(
        self,
        data: dict,
        response: LLMResponseTypes,
        user_api_key_dict: UserAPIKeyAuth,
    ):
        """
        Allow user to modify outgoing data

        Covers:
        1. /chat/completions
        2. /embeddings
        3. /image/generation
        4. /files
        """

        for callback in litellm.callbacks:
            try:
                _callback: Optional[CustomLogger] = None
                if isinstance(callback, str):
                    _callback = litellm.litellm_core_utils.litellm_logging.get_custom_logger_compatible_class(
                        callback
                    )
                else:
                    _callback = callback  # type: ignore

                if _callback is not None:
                    ############## Handle Guardrails ########################################
                    #############################################################################
                    if isinstance(callback, CustomGuardrail):
                        # Main - V2 Guardrails implementation
                        from litellm.types.guardrails import GuardrailEventHooks

                        if (
                            callback.should_run_guardrail(
                                data=data, event_type=GuardrailEventHooks.post_call
                            )
                            is not True
                        ):
                            continue

                        await callback.async_post_call_success_hook(
                            user_api_key_dict=user_api_key_dict,
                            data=data,
                            response=response,
                        )

                    ############ Handle CustomLogger ###############################
                    #################################################################
                    elif isinstance(_callback, CustomLogger):
                        await _callback.async_post_call_success_hook(
                            user_api_key_dict=user_api_key_dict,
                            data=data,
                            response=response,
                        )
            except Exception as e:
                raise e
        return response

    async def async_post_call_streaming_hook(
        self,
        response: Union[
            ModelResponse, EmbeddingResponse, ImageResponse, ModelResponseStream
        ],
        user_api_key_dict: UserAPIKeyAuth,
    ):
        """
        Allow user to modify outgoing streaming data -> per chunk

        Covers:
        1. /chat/completions
        """
        response_str: Optional[str] = None
        if isinstance(response, (ModelResponse, ModelResponseStream)):
            response_str = litellm.get_response_string(response_obj=response)
        if response_str is not None:
            for callback in litellm.callbacks:
                try:
                    _callback: Optional[CustomLogger] = None
                    if isinstance(callback, str):
                        _callback = litellm.litellm_core_utils.litellm_logging.get_custom_logger_compatible_class(
                            callback
                        )
                    else:
                        _callback = callback  # type: ignore
                    if _callback is not None and isinstance(_callback, CustomLogger):
                        await _callback.async_post_call_streaming_hook(
                            user_api_key_dict=user_api_key_dict, response=response_str
                        )
                except Exception as e:
                    raise e
        return response

    def async_post_call_streaming_iterator_hook(
        self,
        response,
        user_api_key_dict: UserAPIKeyAuth,
        request_data: dict,
    ):
        """
        Allow user to modify outgoing streaming data -> Given a whole response iterator.
        This hook is best used when you need to modify multiple chunks of the response at once.

        Covers:
        1. /chat/completions
        """
        for callback in litellm.callbacks:
            _callback: Optional[CustomLogger] = None
            if isinstance(callback, str):
                _callback = litellm.litellm_core_utils.litellm_logging.get_custom_logger_compatible_class(
                    callback
                )
            else:
                _callback = callback  # type: ignore
            if _callback is not None and isinstance(_callback, CustomLogger):
                if not isinstance(
                    _callback, CustomGuardrail
                ) or _callback.should_run_guardrail(
                    data=request_data, event_type=GuardrailEventHooks.post_call
                ):
                    response = _callback.async_post_call_streaming_iterator_hook(
                        user_api_key_dict=user_api_key_dict,
                        response=response,
                        request_data=request_data,
                    )
        return response

    async def post_call_streaming_hook(
        self,
        response: str,
        user_api_key_dict: UserAPIKeyAuth,
    ):
        """
        - Check outgoing streaming response uptil that point
        - Run through moderation check
        - Reject request if it fails moderation check
        """
        new_response = copy.deepcopy(response)
        for callback in litellm.callbacks:
            try:
                if isinstance(callback, CustomLogger):
                    await callback.async_post_call_streaming_hook(
                        user_api_key_dict=user_api_key_dict, response=new_response
                    )
            except Exception as e:
                raise e
        return new_response

    def _init_response_taking_too_long_task(self, data: Optional[dict] = None):
        """
        Initialize the response taking too long task if user is using slack alerting

        Only run task if user is using slack alerting

        This handles checking for if a request is hanging for too long
        """
        ## ALERTING ###
        if (
            self.slack_alerting_instance
            and self.slack_alerting_instance.alerting is not None
        ):
            asyncio.create_task(
                self.slack_alerting_instance.response_taking_too_long(request_data=data)
            )


### DB CONNECTOR ###
# Define the retry decorator with backoff strategy
# Function to be called whenever a retry is about to happen
def on_backoff(details):
    # The 'tries' key in the details dictionary contains the number of completed tries
    print_verbose(f"Backing off... this was attempt #{details['tries']}")


def jsonify_object(data: dict) -> dict:
    db_data = copy.deepcopy(data)

    for k, v in db_data.items():
        if isinstance(v, dict):
            try:
                db_data[k] = json.dumps(v)
            except Exception:
                # This avoids Prisma retrying this 5 times, and making 5 clients
                db_data[k] = "failed-to-serialize-json"
    return db_data


class PrismaClient:
    spend_log_transactions: List = []

    def __init__(
        self,
        database_url: str,
        proxy_logging_obj: ProxyLogging,
        http_client: Optional[Any] = None,
    ):
        ## init logging object
        self.proxy_logging_obj = proxy_logging_obj
        self.iam_token_db_auth: Optional[bool] = str_to_bool(
            os.getenv("IAM_TOKEN_DB_AUTH")
        )
        verbose_proxy_logger.debug("Creating Prisma Client..")
        try:
            from prisma import Prisma  # type: ignore
        except Exception:
            raise Exception("Unable to find Prisma binaries.")
        if http_client is not None:
            self.db = PrismaWrapper(
                original_prisma=Prisma(http=http_client),
                iam_token_db_auth=(
                    self.iam_token_db_auth
                    if self.iam_token_db_auth is not None
                    else False
                ),
            )
        else:
            self.db = PrismaWrapper(
                original_prisma=Prisma(),
                iam_token_db_auth=(
                    self.iam_token_db_auth
                    if self.iam_token_db_auth is not None
                    else False
                ),
            )  # Client to connect to Prisma db
        verbose_proxy_logger.debug("Success - Created Prisma Client")

    def get_request_status(
        self, payload: Union[dict, SpendLogsPayload]
    ) -> Literal["success", "failure"]:
        """
        Determine if a request was successful or failed based on payload metadata.

        Args:
            payload (Union[dict, SpendLogsPayload]): Request payload containing metadata

        Returns:
            Literal["success", "failure"]: Request status
        """
        try:
            # Get metadata and convert to dict if it's a JSON string
            payload_metadata: Union[Dict, SpendLogsMetadata, str] = payload.get(
                "metadata", {}
            )
            if isinstance(payload_metadata, str):
                payload_metadata_json: Union[Dict, SpendLogsMetadata] = cast(
                    Dict, json.loads(payload_metadata)
                )
            else:
                payload_metadata_json = payload_metadata

            # Check status in metadata dict
            return (
                "failure"
                if payload_metadata_json.get("status") == "failure"
                else "success"
            )

        except (json.JSONDecodeError, AttributeError):
            # Default to success if metadata parsing fails
            return "success"

    def hash_token(self, token: str):
        # Hash the string using SHA-256
        hashed_token = hashlib.sha256(token.encode()).hexdigest()

        return hashed_token

    def jsonify_object(self, data: dict) -> dict:
        db_data = copy.deepcopy(data)

        for k, v in db_data.items():
            if isinstance(v, dict):
                try:
                    db_data[k] = json.dumps(v)
                except Exception:
                    # This avoids Prisma retrying this 5 times, and making 5 clients
                    db_data[k] = "failed-to-serialize-json"
        return db_data

    @backoff.on_exception(
        backoff.expo,
        Exception,  # base exception to catch for the backoff
        max_tries=3,  # maximum number of retries
        max_time=10,  # maximum total time to retry for
        on_backoff=on_backoff,  # specifying the function to call on backoff
    )
    async def check_view_exists(self):
        """
        Checks if the LiteLLM_VerificationTokenView and MonthlyGlobalSpend exists in the user's db.

        LiteLLM_VerificationTokenView: This view is used for getting the token + team data in user_api_key_auth

        MonthlyGlobalSpend: This view is used for the admin view to see global spend for this month

        If the view doesn't exist, one will be created.
        """

        # Check to see if all of the necessary views exist and if they do, simply return
        # This is more efficient because it lets us check for all views in one
        # query instead of multiple queries.
        try:
            expected_views = [
                "LiteLLM_VerificationTokenView",
                "MonthlyGlobalSpend",
                "Last30dKeysBySpend",
                "Last30dModelsBySpend",
                "MonthlyGlobalSpendPerKey",
                "MonthlyGlobalSpendPerUserPerKey",
                "Last30dTopEndUsersSpend",
                "DailyTagSpend",
            ]
            required_view = "LiteLLM_VerificationTokenView"
            expected_views_str = ", ".join(f"'{view}'" for view in expected_views)
            pg_schema = os.getenv("DATABASE_SCHEMA", "public")
            ret = await self.db.query_raw(
                f"""
                WITH existing_views AS (
                    SELECT viewname
                    FROM pg_views
                    WHERE schemaname = '{pg_schema}' AND viewname IN (
                        {expected_views_str}
                    )
                )
                SELECT
                    (SELECT COUNT(*) FROM existing_views) AS view_count,
                    ARRAY_AGG(viewname) AS view_names
                FROM existing_views
                """
            )
            expected_total_views = len(expected_views)
            if ret[0]["view_count"] == expected_total_views:
                verbose_proxy_logger.info("All necessary views exist!")
                return
            else:
                ## check if required view exists ##
                if ret[0]["view_names"] and required_view not in ret[0]["view_names"]:
                    await self.health_check()  # make sure we can connect to db
                    await self.db.execute_raw(
                        """
                            CREATE VIEW "LiteLLM_VerificationTokenView" AS
                            SELECT
                            v.*,
                            t.spend AS team_spend,
                            t.max_budget AS team_max_budget,
                            t.tpm_limit AS team_tpm_limit,
                            t.rpm_limit AS team_rpm_limit
                            FROM "LiteLLM_VerificationToken" v
                            LEFT JOIN "LiteLLM_TeamTable" t ON v.team_id = t.team_id;
                        """
                    )

                    verbose_proxy_logger.info(
                        "LiteLLM_VerificationTokenView Created in DB!"
                    )
                else:
                    should_create_views = await should_create_missing_views(db=self.db)
                    if should_create_views:
                        await create_missing_views(db=self.db)
                    else:
                        # don't block execution if these views are missing
                        # Convert lists to sets for efficient difference calculation
                        ret_view_names_set = (
                            set(ret[0]["view_names"]) if ret[0]["view_names"] else set()
                        )
                        expected_views_set = set(expected_views)
                        # Find missing views
                        missing_views = expected_views_set - ret_view_names_set

                        verbose_proxy_logger.warning(
                            "\n\n\033[93mNot all views exist in db, needed for UI 'Usage' tab. Missing={}.\nRun 'create_views.py' from https://github.com/BerriAI/litellm/tree/main/db_scripts to create missing views.\033[0m\n".format(
                                missing_views
                            )
                        )

        except Exception:
            raise
        return

    @log_db_metrics
    @backoff.on_exception(
        backoff.expo,
        Exception,  # base exception to catch for the backoff
        max_tries=1,  # maximum number of retries
        max_time=2,  # maximum total time to retry for
        on_backoff=on_backoff,  # specifying the function to call on backoff
    )
    async def get_generic_data(
        self,
        key: str,
        value: Any,
        table_name: Literal["users", "keys", "config", "spend"],
    ):
        """
        Generic implementation of get data
        """
        start_time = time.time()
        try:
            if table_name == "users":
                response = await self.db.litellm_usertable.find_first(
                    where={key: value}  # type: ignore
                )
            elif table_name == "keys":
                response = await self.db.litellm_verificationtoken.find_first(  # type: ignore
                    where={key: value}  # type: ignore
                )
            elif table_name == "config":
                response = await self.db.litellm_config.find_first(  # type: ignore
                    where={key: value}  # type: ignore
                )
            elif table_name == "spend":
                response = await self.db.l.find_first(  # type: ignore
                    where={key: value}  # type: ignore
                )
            return response
        except Exception as e:
            import traceback

            error_msg = f"LiteLLM Prisma Client Exception get_generic_data: {str(e)}"
            verbose_proxy_logger.error(error_msg)
            error_msg = error_msg + "\nException Type: {}".format(type(e))
            error_traceback = error_msg + "\n" + traceback.format_exc()
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.proxy_logging_obj.failure_handler(
                    original_exception=e,
                    duration=_duration,
                    traceback_str=error_traceback,
                    call_type="get_generic_data",
                )
            )

            raise e

    @backoff.on_exception(
        backoff.expo,
        Exception,  # base exception to catch for the backoff
        max_tries=3,  # maximum number of retries
        max_time=10,  # maximum total time to retry for
        on_backoff=on_backoff,  # specifying the function to call on backoff
    )
    @log_db_metrics
    async def get_data(  # noqa: PLR0915
        self,
        token: Optional[Union[str, list]] = None,
        user_id: Optional[str] = None,
        user_id_list: Optional[list] = None,
        team_id: Optional[str] = None,
        team_id_list: Optional[list] = None,
        key_val: Optional[dict] = None,
        table_name: Optional[
            Literal[
                "user",
                "key",
                "config",
                "spend",
                "enduser",
                "budget",
                "team",
                "user_notification",
                "combined_view",
            ]
        ] = None,
        query_type: Literal["find_unique", "find_all"] = "find_unique",
        expires: Optional[datetime] = None,
        reset_at: Optional[datetime] = None,
        offset: Optional[int] = None,  # pagination, what row number to start from
        limit: Optional[
            int
        ] = None,  # pagination, number of rows to getch when find_all==True
        parent_otel_span: Optional[Span] = None,
        proxy_logging_obj: Optional[ProxyLogging] = None,
        budget_id_list: Optional[List[str]] = None,
    ):
        args_passed_in = locals()
        start_time = time.time()
        hashed_token: Optional[str] = None
        try:
            response: Any = None
            if (token is not None and table_name is None) or (
                table_name is not None and table_name == "key"
            ):
                # check if plain text or hash
                if token is not None:
                    if isinstance(token, str):
                        hashed_token = _hash_token_if_needed(token=token)
                        verbose_proxy_logger.debug(
                            f"PrismaClient: find_unique for token: {hashed_token}"
                        )
                if query_type == "find_unique" and hashed_token is not None:
                    if token is None:
                        raise HTTPException(
                            status_code=400,
                            detail={"error": f"No token passed in. Token={token}"},
                        )
                    response = await self.db.litellm_verificationtoken.find_unique(
                        where={"token": hashed_token},  # type: ignore
                        include={"litellm_budget_table": True},
                    )
                    if response is not None:
                        # for prisma we need to cast the expires time to str
                        if response.expires is not None and isinstance(
                            response.expires, datetime
                        ):
                            response.expires = response.expires.isoformat()
                    else:
                        # Token does not exist.
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"Authentication Error: invalid user key - user key does not exist in db. User Key={token}",
                        )
                elif query_type == "find_all" and user_id is not None:
                    response = await self.db.litellm_verificationtoken.find_many(
                        where={"user_id": user_id},
                        include={"litellm_budget_table": True},
                    )
                    if response is not None and len(response) > 0:
                        for r in response:
                            if isinstance(r.expires, datetime):
                                r.expires = r.expires.isoformat()
                elif query_type == "find_all" and team_id is not None:
                    response = await self.db.litellm_verificationtoken.find_many(
                        where={"team_id": team_id},
                        include={"litellm_budget_table": True},
                    )
                    if response is not None and len(response) > 0:
                        for r in response:
                            if isinstance(r.expires, datetime):
                                r.expires = r.expires.isoformat()
                elif (
                    query_type == "find_all"
                    and expires is not None
                    and reset_at is not None
                ):
                    response = await self.db.litellm_verificationtoken.find_many(
                        where={  # type:ignore
                            "OR": [
                                {"expires": None},
                                {"expires": {"gt": expires}},
                            ],
                            "budget_reset_at": {"lt": reset_at},
                        }
                    )
                    if response is not None and len(response) > 0:
                        for r in response:
                            if isinstance(r.expires, datetime):
                                r.expires = r.expires.isoformat()
                elif query_type == "find_all":
                    where_filter: dict = {}
                    if token is not None:
                        where_filter["token"] = {}
                        if isinstance(token, str):
                            token = _hash_token_if_needed(token=token)
                            where_filter["token"]["in"] = [token]
                        elif isinstance(token, list):
                            hashed_tokens = []
                            for t in token:
                                assert isinstance(t, str)
                                if t.startswith("sk-"):
                                    new_token = self.hash_token(token=t)
                                    hashed_tokens.append(new_token)
                                else:
                                    hashed_tokens.append(t)
                            where_filter["token"]["in"] = hashed_tokens
                    response = await self.db.litellm_verificationtoken.find_many(
                        order={"spend": "desc"},
                        where=where_filter,  # type: ignore
                        include={"litellm_budget_table": True},
                    )
                if response is not None:
                    return response
                else:
                    # Token does not exist.
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication Error: invalid user key - token does not exist",
                    )
            elif (user_id is not None and table_name is None) or (
                table_name is not None and table_name == "user"
            ):
                if query_type == "find_unique":
                    if key_val is None:
                        key_val = {"user_id": user_id}

                    response = await self.db.litellm_usertable.find_unique(  # type: ignore
                        where=key_val,  # type: ignore
                        include={"organization_memberships": True},
                    )

                elif query_type == "find_all" and key_val is not None:
                    response = await self.db.litellm_usertable.find_many(
                        where=key_val  # type: ignore
                    )  # type: ignore
                elif query_type == "find_all" and reset_at is not None:
                    response = await self.db.litellm_usertable.find_many(
                        where={  # type:ignore
                            "budget_reset_at": {"lt": reset_at},
                        }
                    )
                elif query_type == "find_all" and user_id_list is not None:
                    response = await self.db.litellm_usertable.find_many(
                        where={"user_id": {"in": user_id_list}}
                    )
                elif query_type == "find_all":
                    if expires is not None:
                        response = await self.db.litellm_usertable.find_many(  # type: ignore
                            order={"spend": "desc"},
                            where={  # type:ignore
                                "OR": [
                                    {"expires": None},  # type:ignore
                                    {"expires": {"gt": expires}},  # type:ignore
                                ],
                            },
                        )
                    else:
                        # return all users in the table, get their key aliases ordered by spend
                        sql_query = """
                        SELECT
                            u.*,
                            json_agg(v.key_alias) AS key_aliases
                        FROM
                            "LiteLLM_UserTable" u
                        LEFT JOIN "LiteLLM_VerificationToken" v ON u.user_id = v.user_id
                        GROUP BY
                            u.user_id
                        ORDER BY u.spend DESC
                        LIMIT $1
                        OFFSET $2
                        """
                        response = await self.db.query_raw(sql_query, limit, offset)
                return response
            elif table_name == "spend":
                verbose_proxy_logger.debug(
                    "PrismaClient: get_data: table_name == 'spend'"
                )
                if key_val is not None:
                    if query_type == "find_unique":
                        response = await self.db.litellm_spendlogs.find_unique(  # type: ignore
                            where={  # type: ignore
                                key_val["key"]: key_val["value"],  # type: ignore
                            }
                        )
                    elif query_type == "find_all":
                        response = await self.db.litellm_spendlogs.find_many(  # type: ignore
                            where={
                                key_val["key"]: key_val["value"],  # type: ignore
                            }
                        )
                    return response
                else:
                    response = await self.db.litellm_spendlogs.find_many(  # type: ignore
                        order={"startTime": "desc"},
                    )
                    return response
            elif table_name == "budget" and reset_at is not None:
                if query_type == "find_all":
                    response = await self.db.litellm_budgettable.find_many(
                        where={  # type:ignore
                            "OR": [
                                {
                                    "AND": [
                                        {"budget_reset_at": None},
                                        {"NOT": {"budget_duration": None}},
                                    ]
                                },
                                {"budget_reset_at": {"lt": reset_at}},
                            ]
                        }
                    )
                    return response

            elif table_name == "enduser" and budget_id_list is not None:
                if query_type == "find_all":
                    response = await self.db.litellm_endusertable.find_many(
                        where={"budget_id": {"in": budget_id_list}}
                    )
                    return response
            elif table_name == "team":
                if query_type == "find_unique":
                    response = await self.db.litellm_teamtable.find_unique(
                        where={"team_id": team_id},  # type: ignore
                        include={"litellm_model_table": True},  # type: ignore
                    )
                elif query_type == "find_all" and reset_at is not None:
                    response = await self.db.litellm_teamtable.find_many(
                        where={  # type:ignore
                            "budget_reset_at": {"lt": reset_at},
                        }
                    )
                elif query_type == "find_all" and user_id is not None:
                    response = await self.db.litellm_teamtable.find_many(
                        where={
                            "members": {"has": user_id},
                        },
                        include={"litellm_budget_table": True},
                    )
                elif query_type == "find_all" and team_id_list is not None:
                    response = await self.db.litellm_teamtable.find_many(
                        where={"team_id": {"in": team_id_list}}
                    )
                elif query_type == "find_all" and team_id_list is None:
                    response = await self.db.litellm_teamtable.find_many(
                        take=MAX_TEAM_LIST_LIMIT
                    )
                return response
            elif table_name == "user_notification":
                if query_type == "find_unique":
                    response = await self.db.litellm_usernotifications.find_unique(  # type: ignore
                        where={"user_id": user_id}  # type: ignore
                    )
                elif query_type == "find_all":
                    response = await self.db.litellm_usernotifications.find_many()  # type: ignore
                return response
            elif table_name == "combined_view":
                # check if plain text or hash
                if token is not None:
                    if isinstance(token, str):
                        hashed_token = _hash_token_if_needed(token=token)
                        verbose_proxy_logger.debug(
                            f"PrismaClient: find_unique for token: {hashed_token}"
                        )
                if query_type == "find_unique":
                    if token is None:
                        raise HTTPException(
                            status_code=400,
                            detail={"error": f"No token passed in. Token={token}"},
                        )

                    sql_query = f"""
                        SELECT 
                            v.*,
                            t.spend AS team_spend, 
                            t.max_budget AS team_max_budget, 
                            t.tpm_limit AS team_tpm_limit,
                            t.rpm_limit AS team_rpm_limit,
                            t.models AS team_models,
                            t.metadata AS team_metadata,
                            t.blocked AS team_blocked,
                            t.team_alias AS team_alias,
                            t.metadata AS team_metadata,
                            t.members_with_roles AS team_members_with_roles,
                            t.organization_id as org_id,
                            tm.spend AS team_member_spend,
                            m.aliases AS team_model_aliases,
                            -- Added comma to separate b.* columns
                            b.max_budget AS litellm_budget_table_max_budget,
                            b.tpm_limit AS litellm_budget_table_tpm_limit,
                            b.rpm_limit AS litellm_budget_table_rpm_limit,
                            b.model_max_budget as litellm_budget_table_model_max_budget,
                            b.soft_budget as litellm_budget_table_soft_budget
                        FROM "LiteLLM_VerificationToken" AS v
                        LEFT JOIN "LiteLLM_TeamTable" AS t ON v.team_id = t.team_id
                        LEFT JOIN "LiteLLM_TeamMembership" AS tm ON v.team_id = tm.team_id AND tm.user_id = v.user_id
                        LEFT JOIN "LiteLLM_ModelTable" m ON t.model_id = m.id
                        LEFT JOIN "LiteLLM_BudgetTable" AS b ON v.budget_id = b.budget_id
                        WHERE v.token = '{token}'
                    """

                    print_verbose("sql_query being made={}".format(sql_query))
                    response = await self.db.query_first(query=sql_query)

                    if response is not None:
                        if response["team_models"] is None:
                            response["team_models"] = []
                        if response["team_blocked"] is None:
                            response["team_blocked"] = False

                        team_member: Optional[Member] = None
                        if (
                            response["team_members_with_roles"] is not None
                            and response["user_id"] is not None
                        ):
                            ## find the team member corresponding to user id
                            """
                            [
                                {
                                    "role": "admin",
                                    "user_id": "default_user_id",
                                    "user_email": null
                                },
                                {
                                    "role": "user",
                                    "user_id": null,
                                    "user_email": "test@email.com"
                                }
                            ]
                            """
                            for tm in response["team_members_with_roles"]:
                                if tm.get("user_id") is not None and response[
                                    "user_id"
                                ] == tm.get("user_id"):
                                    team_member = Member(**tm)
                        response["team_member"] = team_member
                        response = LiteLLM_VerificationTokenView(
                            **response, last_refreshed_at=time.time()
                        )
                        # for prisma we need to cast the expires time to str
                        if response.expires is not None and isinstance(
                            response.expires, datetime
                        ):
                            response.expires = response.expires.isoformat()
                    return response
        except Exception as e:
            import traceback

            prisma_query_info = f"LiteLLM Prisma Client Exception: Error with `get_data`. Args passed in: {args_passed_in}"
            error_msg = prisma_query_info + str(e)
            print_verbose(error_msg)
            error_traceback = error_msg + "\n" + traceback.format_exc()
            verbose_proxy_logger.debug(error_traceback)
            end_time = time.time()
            _duration = end_time - start_time

            asyncio.create_task(
                self.proxy_logging_obj.failure_handler(
                    original_exception=e,
                    duration=_duration,
                    call_type="get_data",
                    traceback_str=error_traceback,
                )
            )
            raise e

    def jsonify_team_object(self, db_data: dict):
        db_data = self.jsonify_object(data=db_data)
        if db_data.get("members_with_roles", None) is not None and isinstance(
            db_data["members_with_roles"], list
        ):
            db_data["members_with_roles"] = json.dumps(db_data["members_with_roles"])
        return db_data

    # Define a retrying strategy with exponential backoff
    @backoff.on_exception(
        backoff.expo,
        Exception,  # base exception to catch for the backoff
        max_tries=3,  # maximum number of retries
        max_time=10,  # maximum total time to retry for
        on_backoff=on_backoff,  # specifying the function to call on backoff
    )
    async def insert_data(  # noqa: PLR0915
        self,
        data: dict,
        table_name: Literal[
            "user", "key", "config", "spend", "team", "user_notification"
        ],
    ):
        """
        Add a key to the database. If it already exists, do nothing.
        """
        start_time = time.time()
        try:
            verbose_proxy_logger.debug("PrismaClient: insert_data: %s", data)
            if table_name == "key":
                token = data["token"]
                hashed_token = self.hash_token(token=token)
                db_data = self.jsonify_object(data=data)
                db_data["token"] = hashed_token
                print_verbose(
                    "PrismaClient: Before upsert into litellm_verificationtoken"
                )
                new_verification_token = await self.db.litellm_verificationtoken.upsert(  # type: ignore
                    where={
                        "token": hashed_token,
                    },
                    data={
                        "create": {**db_data},  # type: ignore
                        "update": {},  # don't do anything if it already exists
                    },
                    include={"litellm_budget_table": True},
                )
                verbose_proxy_logger.info("Data Inserted into Keys Table")
                return new_verification_token
            elif table_name == "user":
                db_data = self.jsonify_object(data=data)
                try:
                    new_user_row = await self.db.litellm_usertable.upsert(
                        where={"user_id": data["user_id"]},
                        data={
                            "create": {**db_data},  # type: ignore
                            "update": {},  # don't do anything if it already exists
                        },
                    )
                except Exception as e:
                    if (
                        "Foreign key constraint failed on the field: `LiteLLM_UserTable_organization_id_fkey (index)`"
                        in str(e)
                    ):
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "error": f"Foreign Key Constraint failed. Organization ID={db_data['organization_id']} does not exist in LiteLLM_OrganizationTable. Create via `/organization/new`."
                            },
                        )
                    raise e
                verbose_proxy_logger.info("Data Inserted into User Table")
                return new_user_row
            elif table_name == "team":
                db_data = self.jsonify_team_object(db_data=data)
                new_team_row = await self.db.litellm_teamtable.upsert(
                    where={"team_id": data["team_id"]},
                    data={
                        "create": {**db_data},  # type: ignore
                        "update": {},  # don't do anything if it already exists
                    },
                )
                verbose_proxy_logger.info("Data Inserted into Team Table")
                return new_team_row
            elif table_name == "config":
                """
                For each param,
                get the existing table values

                Add the new values

                Update DB
                """
                tasks = []
                for k, v in data.items():
                    updated_data = v
                    updated_data = json.dumps(updated_data)
                    updated_table_row = self.db.litellm_config.upsert(
                        where={"param_name": k},  # type: ignore
                        data={
                            "create": {"param_name": k, "param_value": updated_data},  # type: ignore
                            "update": {"param_value": updated_data},
                        },
                    )

                    tasks.append(updated_table_row)
                await asyncio.gather(*tasks)
                verbose_proxy_logger.info("Data Inserted into Config Table")
            elif table_name == "spend":
                db_data = self.jsonify_object(data=data)
                new_spend_row = await self.db.litellm_spendlogs.upsert(
                    where={"request_id": data["request_id"]},
                    data={
                        "create": {**db_data},  # type: ignore
                        "update": {},  # don't do anything if it already exists
                    },
                )
                verbose_proxy_logger.info("Data Inserted into Spend Table")
                return new_spend_row
            elif table_name == "user_notification":
                db_data = self.jsonify_object(data=data)
                new_user_notification_row = (
                    await self.db.litellm_usernotifications.upsert(  # type: ignore
                        where={"request_id": data["request_id"]},
                        data={
                            "create": {**db_data},  # type: ignore
                            "update": {},  # don't do anything if it already exists
                        },
                    )
                )
                verbose_proxy_logger.info("Data Inserted into Model Request Table")
                return new_user_notification_row

        except Exception as e:
            import traceback

            error_msg = f"LiteLLM Prisma Client Exception in insert_data: {str(e)}"
            print_verbose(error_msg)
            error_traceback = error_msg + "\n" + traceback.format_exc()
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.proxy_logging_obj.failure_handler(
                    original_exception=e,
                    duration=_duration,
                    call_type="insert_data",
                    traceback_str=error_traceback,
                )
            )
            raise e

    # Define a retrying strategy with exponential backoff
    @backoff.on_exception(
        backoff.expo,
        Exception,  # base exception to catch for the backoff
        max_tries=3,  # maximum number of retries
        max_time=10,  # maximum total time to retry for
        on_backoff=on_backoff,  # specifying the function to call on backoff
    )
    async def update_data(  # noqa: PLR0915
        self,
        token: Optional[str] = None,
        data: dict = {},
        data_list: Optional[List] = None,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
        query_type: Literal["update", "update_many"] = "update",
        table_name: Optional[
            Literal["user", "key", "config", "spend", "team", "enduser", "budget"]
        ] = None,
        update_key_values: Optional[dict] = None,
        update_key_values_custom_query: Optional[dict] = None,
    ):
        """
        Update existing data
        """
        verbose_proxy_logger.debug(
            f"PrismaClient: update_data, table_name: {table_name}"
        )
        start_time = time.time()
        try:
            db_data = self.jsonify_object(data=data)
            if update_key_values is not None:
                update_key_values = self.jsonify_object(data=update_key_values)
            if token is not None:
                print_verbose(f"token: {token}")
                # check if plain text or hash
                token = _hash_token_if_needed(token=token)
                db_data["token"] = token
                response = await self.db.litellm_verificationtoken.update(
                    where={"token": token},  # type: ignore
                    data={**db_data},  # type: ignore
                )
                verbose_proxy_logger.debug(
                    "\033[91m"
                    + f"DB Token Table update succeeded {response}"
                    + "\033[0m"
                )
                _data: dict = {}
                if response is not None:
                    try:
                        _data = response.model_dump()  # type: ignore
                    except Exception:
                        _data = response.dict()
                return {"token": token, "data": _data}
            elif (
                user_id is not None
                or (table_name is not None and table_name == "user")
                and query_type == "update"
            ):
                """
                If data['spend'] + data['user'], update the user table with spend info as well
                """
                if user_id is None:
                    user_id = db_data["user_id"]
                if update_key_values is None:
                    if update_key_values_custom_query is not None:
                        update_key_values = update_key_values_custom_query
                    else:
                        update_key_values = db_data
                update_user_row = await self.db.litellm_usertable.upsert(
                    where={"user_id": user_id},  # type: ignore
                    data={
                        "create": {**db_data},  # type: ignore
                        "update": {
                            **update_key_values  # type: ignore
                        },  # just update user-specified values, if it already exists
                    },
                )
                verbose_proxy_logger.info(
                    "\033[91m"
                    + f"DB User Table - update succeeded {update_user_row}"
                    + "\033[0m"
                )
                return {"user_id": user_id, "data": update_user_row}
            elif (
                team_id is not None
                or (table_name is not None and table_name == "team")
                and query_type == "update"
            ):
                """
                If data['spend'] + data['user'], update the user table with spend info as well
                """
                if team_id is None:
                    team_id = db_data["team_id"]
                if update_key_values is None:
                    update_key_values = db_data
                if "team_id" not in db_data and team_id is not None:
                    db_data["team_id"] = team_id
                if "members_with_roles" in db_data and isinstance(
                    db_data["members_with_roles"], list
                ):
                    db_data["members_with_roles"] = json.dumps(
                        db_data["members_with_roles"]
                    )
                if "members_with_roles" in update_key_values and isinstance(
                    update_key_values["members_with_roles"], list
                ):
                    update_key_values["members_with_roles"] = json.dumps(
                        update_key_values["members_with_roles"]
                    )
                update_team_row = await self.db.litellm_teamtable.upsert(
                    where={"team_id": team_id},  # type: ignore
                    data={
                        "create": {**db_data},  # type: ignore
                        "update": {
                            **update_key_values  # type: ignore
                        },  # just update user-specified values, if it already exists
                    },
                )
                verbose_proxy_logger.info(
                    "\033[91m"
                    + f"DB Team Table - update succeeded {update_team_row}"
                    + "\033[0m"
                )
                return {"team_id": team_id, "data": update_team_row}
            elif (
                table_name is not None
                and table_name == "key"
                and query_type == "update_many"
                and data_list is not None
                and isinstance(data_list, list)
            ):
                """
                Batch write update queries
                """
                batcher = self.db.batch_()
                for idx, t in enumerate(data_list):
                    # check if plain text or hash
                    if t.token.startswith("sk-"):  # type: ignore
                        t.token = self.hash_token(token=t.token)  # type: ignore
                    try:
                        data_json = self.jsonify_object(
                            data=t.model_dump(exclude_none=True)
                        )
                    except Exception:
                        data_json = self.jsonify_object(data=t.dict(exclude_none=True))
                    batcher.litellm_verificationtoken.update(
                        where={"token": t.token},  # type: ignore
                        data={**data_json},  # type: ignore
                    )
                await batcher.commit()
                print_verbose(
                    "\033[91m" + "DB Token Table update succeeded" + "\033[0m"
                )
            elif (
                table_name is not None
                and table_name == "user"
                and query_type == "update_many"
                and data_list is not None
                and isinstance(data_list, list)
            ):
                """
                Batch write update queries
                """
                batcher = self.db.batch_()
                for idx, user in enumerate(data_list):
                    try:
                        data_json = self.jsonify_object(
                            data=user.model_dump(exclude_none=True)
                        )
                    except Exception:
                        data_json = self.jsonify_object(data=user.dict())
                    batcher.litellm_usertable.upsert(
                        where={"user_id": user.user_id},  # type: ignore
                        data={
                            "create": {**data_json},  # type: ignore
                            "update": {
                                **data_json  # type: ignore
                            },  # just update user-specified values, if it already exists
                        },
                    )
                await batcher.commit()
                verbose_proxy_logger.info(
                    "\033[91m" + "DB User Table Batch update succeeded" + "\033[0m"
                )
            elif (
                table_name is not None
                and table_name == "enduser"
                and query_type == "update_many"
                and data_list is not None
                and isinstance(data_list, list)
            ):
                """
                Batch write update queries
                """
                batcher = self.db.batch_()
                for enduser in data_list:
                    try:
                        data_json = self.jsonify_object(
                            data=enduser.model_dump(exclude_none=True)
                        )
                    except Exception:
                        data_json = self.jsonify_object(data=enduser.dict())
                    batcher.litellm_endusertable.upsert(
                        where={"user_id": enduser.user_id},  # type: ignore
                        data={
                            "create": {**data_json},  # type: ignore
                            "update": {
                                **data_json  # type: ignore
                            },  # just update end-user-specified values, if it already exists
                        },
                    )
                await batcher.commit()
                verbose_proxy_logger.info(
                    "\033[91m" + "DB End User Table Batch update succeeded" + "\033[0m"
                )
            elif (
                table_name is not None
                and table_name == "budget"
                and query_type == "update_many"
                and data_list is not None
                and isinstance(data_list, list)
            ):
                """
                Batch write update queries
                """
                batcher = self.db.batch_()
                for budget in data_list:
                    try:
                        data_json = self.jsonify_object(
                            data=budget.model_dump(exclude_none=True)
                        )
                    except Exception:
                        data_json = self.jsonify_object(data=budget.dict())
                    batcher.litellm_budgettable.upsert(
                        where={"budget_id": budget.budget_id},  # type: ignore
                        data={
                            "create": {**data_json},  # type: ignore
                            "update": {
                                **data_json  # type: ignore
                            },  # just update end-user-specified values, if it already exists
                        },
                    )
                await batcher.commit()
                verbose_proxy_logger.info(
                    "\033[91m" + "DB Budget Table Batch update succeeded" + "\033[0m"
                )
            elif (
                table_name is not None
                and table_name == "team"
                and query_type == "update_many"
                and data_list is not None
                and isinstance(data_list, list)
            ):
                # Batch write update queries
                batcher = self.db.batch_()
                for idx, team in enumerate(data_list):
                    try:
                        data_json = self.jsonify_team_object(
                            db_data=team.model_dump(exclude_none=True)
                        )
                    except Exception:
                        data_json = self.jsonify_object(
                            data=team.dict(exclude_none=True)
                        )
                    batcher.litellm_teamtable.upsert(
                        where={"team_id": team.team_id},  # type: ignore
                        data={
                            "create": {**data_json},  # type: ignore
                            "update": {
                                **data_json  # type: ignore
                            },  # just update user-specified values, if it already exists
                        },
                    )
                await batcher.commit()
                verbose_proxy_logger.info(
                    "\033[91m" + "DB Team Table Batch update succeeded" + "\033[0m"
                )

        except Exception as e:
            import traceback

            error_msg = f"LiteLLM Prisma Client Exception - update_data: {str(e)}"
            print_verbose(error_msg)
            error_traceback = error_msg + "\n" + traceback.format_exc()
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.proxy_logging_obj.failure_handler(
                    original_exception=e,
                    duration=_duration,
                    call_type="update_data",
                    traceback_str=error_traceback,
                )
            )
            raise e

    # Define a retrying strategy with exponential backoff
    @backoff.on_exception(
        backoff.expo,
        Exception,  # base exception to catch for the backoff
        max_tries=3,  # maximum number of retries
        max_time=10,  # maximum total time to retry for
        on_backoff=on_backoff,  # specifying the function to call on backoff
    )
    async def delete_data(
        self,
        tokens: Optional[List] = None,
        team_id_list: Optional[List] = None,
        table_name: Optional[Literal["user", "key", "config", "spend", "team"]] = None,
        user_id: Optional[str] = None,
    ):
        """
        Allow user to delete a key(s)

        Ensure user owns that key, unless admin.
        """
        start_time = time.time()
        try:
            if tokens is not None and isinstance(tokens, List):
                hashed_tokens = []
                for token in tokens:
                    if isinstance(token, str) and token.startswith("sk-"):
                        hashed_token = self.hash_token(token=token)
                    else:
                        hashed_token = token
                    hashed_tokens.append(hashed_token)
                filter_query: dict = {}
                if user_id is not None:
                    filter_query = {
                        "AND": [{"token": {"in": hashed_tokens}}, {"user_id": user_id}]
                    }
                else:
                    filter_query = {"token": {"in": hashed_tokens}}

                deleted_tokens = await self.db.litellm_verificationtoken.delete_many(
                    where=filter_query  # type: ignore
                )
                verbose_proxy_logger.debug("deleted_tokens: %s", deleted_tokens)
                return {"deleted_keys": deleted_tokens}
            elif (
                table_name == "team"
                and team_id_list is not None
                and isinstance(team_id_list, List)
            ):
                # admin only endpoint -> `/team/delete`
                await self.db.litellm_teamtable.delete_many(
                    where={"team_id": {"in": team_id_list}}
                )
                return {"deleted_teams": team_id_list}
            elif (
                table_name == "key"
                and team_id_list is not None
                and isinstance(team_id_list, List)
            ):
                # admin only endpoint -> `/team/delete`
                await self.db.litellm_verificationtoken.delete_many(
                    where={"team_id": {"in": team_id_list}}
                )
        except Exception as e:
            import traceback

            error_msg = f"LiteLLM Prisma Client Exception - delete_data: {str(e)}"
            print_verbose(error_msg)
            error_traceback = error_msg + "\n" + traceback.format_exc()
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.proxy_logging_obj.failure_handler(
                    original_exception=e,
                    duration=_duration,
                    call_type="delete_data",
                    traceback_str=error_traceback,
                )
            )
            raise e

    # Define a retrying strategy with exponential backoff
    @backoff.on_exception(
        backoff.expo,
        Exception,  # base exception to catch for the backoff
        max_tries=3,  # maximum number of retries
        max_time=10,  # maximum total time to retry for
        on_backoff=on_backoff,  # specifying the function to call on backoff
    )
    async def connect(self):
        start_time = time.time()
        try:
            verbose_proxy_logger.debug(
                "PrismaClient: connect() called Attempting to Connect to DB"
            )
            if self.db.is_connected() is False:
                verbose_proxy_logger.debug(
                    "PrismaClient: DB not connected, Attempting to Connect to DB"
                )
                await self.db.connect()
        except Exception as e:
            import traceback

            error_msg = f"LiteLLM Prisma Client Exception connect(): {str(e)}"
            print_verbose(error_msg)
            error_traceback = error_msg + "\n" + traceback.format_exc()
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.proxy_logging_obj.failure_handler(
                    original_exception=e,
                    duration=_duration,
                    call_type="connect",
                    traceback_str=error_traceback,
                )
            )
            raise e

    # Define a retrying strategy with exponential backoff
    @backoff.on_exception(
        backoff.expo,
        Exception,  # base exception to catch for the backoff
        max_tries=3,  # maximum number of retries
        max_time=10,  # maximum total time to retry for
        on_backoff=on_backoff,  # specifying the function to call on backoff
    )
    async def disconnect(self):
        start_time = time.time()
        try:
            await self.db.disconnect()
        except Exception as e:
            import traceback

            error_msg = f"LiteLLM Prisma Client Exception disconnect(): {str(e)}"
            print_verbose(error_msg)
            error_traceback = error_msg + "\n" + traceback.format_exc()
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.proxy_logging_obj.failure_handler(
                    original_exception=e,
                    duration=_duration,
                    call_type="disconnect",
                    traceback_str=error_traceback,
                )
            )
            raise e

    async def health_check(self):
        """
        Health check endpoint for the prisma client
        """
        start_time = time.time()
        try:
            sql_query = "SELECT 1"

            # Execute the raw query
            # The asterisk before `user_id_list` unpacks the list into separate arguments
            response = await self.db.query_raw(sql_query)
            return response
        except Exception as e:
            import traceback

            error_msg = f"LiteLLM Prisma Client Exception disconnect(): {str(e)}"
            print_verbose(error_msg)
            error_traceback = error_msg + "\n" + traceback.format_exc()
            end_time = time.time()
            _duration = end_time - start_time
            asyncio.create_task(
                self.proxy_logging_obj.failure_handler(
                    original_exception=e,
                    duration=_duration,
                    call_type="health_check",
                    traceback_str=error_traceback,
                )
            )
            raise e

    async def _get_spend_logs_row_count(self) -> int:
        try:
            sql_query = """
            SELECT reltuples::BIGINT
            FROM pg_class
            WHERE oid = '"LiteLLM_SpendLogs"'::regclass;
            """
            result = await self.db.query_raw(query=sql_query)
            return result[0]["reltuples"]
        except Exception as e:
            verbose_proxy_logger.error(
                f"Error getting LiteLLM_SpendLogs row count: {e}"
            )
            return 0

    async def _set_spend_logs_row_count_in_proxy_state(self) -> None:
        """
        Set the `LiteLLM_SpendLogs`row count in proxy state.

        This is used later to determine if we should run expensive UI Usage queries.
        """
        from litellm.proxy.proxy_server import proxy_state

        _num_spend_logs_rows = await self._get_spend_logs_row_count()
        proxy_state.set_proxy_state_variable(
            variable_name="spend_logs_row_count",
            value=_num_spend_logs_rows,
        )

    # Health Check Database Methods
    def _validate_response_time(self, response_time_ms: Optional[float]) -> Optional[float]:
        """Validate and clean response time value"""
        if response_time_ms is None:
            return None
        try:
            value = float(response_time_ms)
            return value if value == value and value not in (float('inf'), float('-inf')) else None
        except (ValueError, TypeError):
            verbose_proxy_logger.warning(f"Invalid response_time_ms value: {response_time_ms}")
            return None

    def _clean_details(self, details: Optional[dict]) -> Optional[dict]:
        """Clean and validate details JSON"""
        if not isinstance(details, dict):
            return None
        try:
            return safe_json_loads(safe_dumps(details))
        except Exception as e:
            verbose_proxy_logger.warning(f"Failed to clean details JSON: {e}")
            return None

    async def save_health_check_result(
        self,
        model_name: str,
        status: str,
        healthy_count: int = 0,
        unhealthy_count: int = 0,
        error_message: Optional[str] = None,
        response_time_ms: Optional[float] = None,
        details: Optional[dict] = None,
        checked_by: Optional[str] = None,
        model_id: Optional[str] = None,
    ):
        """Save health check result to database"""
        try:
            # Build base data with required fields
            health_check_data = {
                "model_name": str(model_name),
                "status": str(status),
                "healthy_count": int(healthy_count),
                "unhealthy_count": int(unhealthy_count),
            }
            
            # Add optional fields using dict comprehension and helper methods
            optional_fields = {
                "error_message": str(error_message)[:500] if error_message else None,
                "response_time_ms": self._validate_response_time(response_time_ms),
                "details": self._clean_details(details),
                "checked_by": str(checked_by) if checked_by else None,
                "model_id": str(model_id) if model_id else None,
            }
            
            # Add only non-None optional fields
            health_check_data.update({k: v for k, v in optional_fields.items() if v is not None})
            
            verbose_proxy_logger.debug(f"Saving health check data: {health_check_data}")
            return await self.db.litellm_healthchecktable.create(data=health_check_data)
            
        except Exception as e:
            verbose_proxy_logger.error(f"Error saving health check result for model {model_name}: {e}")
            return None

    async def get_health_check_history(
        self,
        model_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        status_filter: Optional[str] = None,
    ):
        """
        Get health check history with optional filtering
        """
        try:
            where_clause = {}
            if model_name:
                where_clause["model_name"] = model_name
            if status_filter:
                where_clause["status"] = status_filter

            results = await self.db.litellm_healthchecktable.find_many(
                where=where_clause,
                order={"checked_at": "desc"},
                take=limit,
                skip=offset,
            )
            return results
        except Exception as e:
            verbose_proxy_logger.error(f"Error getting health check history: {e}")
            return []

    async def get_all_latest_health_checks(self):
        """
        Get the latest health check for each model
        """
        try:
            # Get all unique model names first
            all_checks = await self.db.litellm_healthchecktable.find_many(
                order={"checked_at": "desc"}
            )
            
            # Group by model_name and get the latest for each
            latest_checks = {}
            for check in all_checks:
                if check.model_name not in latest_checks:
                    latest_checks[check.model_name] = check
            
            return list(latest_checks.values())
        except Exception as e:
            verbose_proxy_logger.error(f"Error getting all latest health checks: {e}")
            return []


### HELPER FUNCTIONS ###

async def _cache_user_row(user_id: str, cache: DualCache, db: PrismaClient):
    """
    Check if a user_id exists in cache,
    if not retrieve it.
    """
    cache_key = f"{user_id}_user_api_key_user_id"
    response = cache.get_cache(key=cache_key)
    if response is None:  # Cache miss
        user_row = await db.get_data(user_id=user_id)
        if user_row is not None:
            print_verbose(f"User Row: {user_row}, type = {type(user_row)}")
            if hasattr(user_row, "model_dump_json") and callable(
                getattr(user_row, "model_dump_json")
            ):
                cache_value = user_row.model_dump_json()
                cache.set_cache(
                    key=cache_key, value=cache_value, ttl=600
                )  # store for 10 minutes
    return


async def send_email(
    receiver_email: Optional[str] = None,
    subject: Optional[str] = None,
    html: Optional[str] = None,
):
    """
    smtp_host,
    smtp_port,
    smtp_username,
    smtp_password,
    sender_name,
    sender_email,
    """
    ## SERVER SETUP ##

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))  # default to port 587
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SMTP_SENDER_EMAIL", None)
    if sender_email is None:
        raise ValueError("Trying to use SMTP, but SMTP_SENDER_EMAIL is not set")
    if receiver_email is None:
        raise ValueError(f"No receiver email provided for SMTP email. {receiver_email}")
    if subject is None:
        raise ValueError(f"No subject provided for SMTP email. {subject}")
    if html is None:
        raise ValueError(f"No HTML body provided for SMTP email. {html}")

    ## EMAIL SETUP ##
    email_message = MIMEMultipart()
    email_message["From"] = sender_email
    email_message["To"] = receiver_email
    email_message["Subject"] = subject
    verbose_proxy_logger.debug(
        "sending email from %s to %s", sender_email, receiver_email
    )

    if smtp_host is None:
        raise ValueError("Trying to use SMTP, but SMTP_HOST is not set")

    # Attach the body to the email
    email_message.attach(MIMEText(html, "html"))

    try:
        # Establish a secure connection with the SMTP server
        with smtplib.SMTP(
            host=smtp_host,
            port=smtp_port,
        ) as server:
            if os.getenv("SMTP_TLS", "True") != "False":
                server.starttls()

            # Login to your email account only if smtp_username and smtp_password are provided
            if smtp_username and smtp_password:
                server.login(
                    user=smtp_username,
                    password=smtp_password,
                )

            # Send the email
            server.send_message(
                msg=email_message,
                from_addr=sender_email,
                to_addrs=receiver_email,
            )

    except Exception as e:
        verbose_proxy_logger.exception(
            "An error occurred while sending the email:" + str(e)
        )


def hash_token(token: str):
    import hashlib

    # Hash the string using SHA-256
    hashed_token = hashlib.sha256(token.encode()).hexdigest()

    return hashed_token


def _hash_token_if_needed(token: str) -> str:
    """
    Hash the token if it's a string and starts with "sk-"

    Else return the token as is
    """
    if token.startswith("sk-"):
        return hash_token(token=token)
    else:
        return token


class ProxyUpdateSpend:
    @staticmethod
    async def update_end_user_spend(
        n_retry_times: int,
        prisma_client: PrismaClient,
        proxy_logging_obj: ProxyLogging,
        end_user_list_transactions: Dict[str, float],
    ):
        for i in range(n_retry_times + 1):
            start_time = time.time()
            try:
                async with prisma_client.db.tx(
                    timeout=timedelta(seconds=60)
                ) as transaction:
                    async with transaction.batch_() as batcher:
                        for (
                            end_user_id,
                            response_cost,
                        ) in end_user_list_transactions.items():
                            if litellm.max_end_user_budget is not None:
                                pass
                            batcher.litellm_endusertable.upsert(
                                where={"user_id": end_user_id},
                                data={
                                    "create": {
                                        "user_id": end_user_id,
                                        "spend": response_cost,
                                        "blocked": False,
                                    },
                                    "update": {"spend": {"increment": response_cost}},
                                },
                            )

                break
            except DB_CONNECTION_ERROR_TYPES as e:
                if i >= n_retry_times:  # If we've reached the maximum number of retries
                    _raise_failed_update_spend_exception(
                        e=e, start_time=start_time, proxy_logging_obj=proxy_logging_obj
                    )
                # Optionally, sleep for a bit before retrying
                await asyncio.sleep(2**i)  # Exponential backoff
            except Exception as e:
                _raise_failed_update_spend_exception(
                    e=e, start_time=start_time, proxy_logging_obj=proxy_logging_obj
                )

    @staticmethod
    async def update_spend_logs(
        n_retry_times: int,
        prisma_client: PrismaClient,
        db_writer_client: Optional[HTTPHandler],
        proxy_logging_obj: ProxyLogging,
    ):
        BATCH_SIZE = 100  # Preferred size of each batch to write to the database
        MAX_LOGS_PER_INTERVAL = (
            1000  # Maximum number of logs to flush in a single interval
        )
        # Get initial logs to process
        logs_to_process = prisma_client.spend_log_transactions[:MAX_LOGS_PER_INTERVAL]
        start_time = time.time()
        try:
            for i in range(n_retry_times + 1):
                try:
                    base_url = os.getenv("SPEND_LOGS_URL", None)
                    if (
                        len(logs_to_process) > 0
                        and base_url is not None
                        and db_writer_client is not None
                    ):
                        if not base_url.endswith("/"):
                            base_url += "/"
                        verbose_proxy_logger.debug("base_url: {}".format(base_url))
                        response = await db_writer_client.post(
                            url=base_url + "spend/update",
                            data=json.dumps(logs_to_process),
                            headers={"Content-Type": "application/json"},
                        )
                        if response.status_code == 200:
                            prisma_client.spend_log_transactions = (
                                prisma_client.spend_log_transactions[
                                    len(logs_to_process) :
                                ]
                            )
                    else:
                        for j in range(0, len(logs_to_process), BATCH_SIZE):
                            batch = logs_to_process[j : j + BATCH_SIZE]
                            batch_with_dates = [
                                prisma_client.jsonify_object({**entry})
                                for entry in batch
                            ]
                            await prisma_client.db.litellm_spendlogs.create_many(
                                data=batch_with_dates, skip_duplicates=True
                            )
                            verbose_proxy_logger.debug(
                                f"Flushed {len(batch)} logs to the DB."
                            )

                        prisma_client.spend_log_transactions = (
                            prisma_client.spend_log_transactions[len(logs_to_process) :]
                        )
                        verbose_proxy_logger.debug(
                            f"{len(logs_to_process)} logs processed. Remaining in queue: {len(prisma_client.spend_log_transactions)}"
                        )
                    break
                except DB_CONNECTION_ERROR_TYPES:
                    if i is None:
                        i = 0
                    if i >= n_retry_times:
                        raise
                    await asyncio.sleep(2**i)
        except Exception as e:
            prisma_client.spend_log_transactions = prisma_client.spend_log_transactions[
                len(logs_to_process) :
            ]
            _raise_failed_update_spend_exception(
                e=e, start_time=start_time, proxy_logging_obj=proxy_logging_obj
            )

    @staticmethod
    def disable_spend_updates() -> bool:
        """
        returns True if should not update spend in db
        Skips writing spend logs and updates to key, team, user spend to DB
        """
        from litellm.proxy.proxy_server import general_settings

        if general_settings.get("disable_spend_updates") is True:
            return True
        return False


async def update_spend(  # noqa: PLR0915
    prisma_client: PrismaClient,
    db_writer_client: Optional[HTTPHandler],
    proxy_logging_obj: ProxyLogging,
):
    """
    Batch write updates to db.

    Triggered every minute.

    Requires:
    user_id_list: dict,
    keys_list: list,
    team_list: list,
    spend_logs: list,
    """
    n_retry_times = 3
    await proxy_logging_obj.db_spend_update_writer.db_update_spend_transaction_handler(
        prisma_client=prisma_client,
        n_retry_times=n_retry_times,
        proxy_logging_obj=proxy_logging_obj,
    )

    ### UPDATE SPEND LOGS ###
    verbose_proxy_logger.debug(
        "Spend Logs transactions: {}".format(len(prisma_client.spend_log_transactions))
    )

    if len(prisma_client.spend_log_transactions) > 0:
        await ProxyUpdateSpend.update_spend_logs(
            n_retry_times=n_retry_times,
            prisma_client=prisma_client,
            proxy_logging_obj=proxy_logging_obj,
            db_writer_client=db_writer_client,
        )


def _raise_failed_update_spend_exception(
    e: Exception, start_time: float, proxy_logging_obj: ProxyLogging
):
    """
    Raise an exception for failed update spend logs

    - Calls proxy_logging_obj.failure_handler to log the error
    - Ensures error messages says "Non-Blocking"
    """
    import traceback

    error_msg = (
        f"[Non-Blocking]LiteLLM Prisma Client Exception - update spend logs: {str(e)}"
    )
    error_traceback = error_msg + "\n" + traceback.format_exc()
    end_time = time.time()
    _duration = end_time - start_time
    asyncio.create_task(
        proxy_logging_obj.failure_handler(
            original_exception=e,
            duration=_duration,
            call_type="update_spend",
            traceback_str=error_traceback,
        )
    )
    raise e


def _is_projected_spend_over_limit(
    current_spend: float, soft_budget_limit: Optional[float]
):
    from datetime import date

    if soft_budget_limit is None:
        # If there's no limit, we can't exceed it.
        return False

    today = date.today()

    # Finding the first day of the next month, then subtracting one day to get the end of the current month.
    if today.month == 12:  # December edge case
        end_month = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_month = date(today.year, today.month + 1, 1) - timedelta(days=1)

    remaining_days = (end_month - today).days

    # Check for the start of the month to avoid division by zero
    if today.day == 1:
        daily_spend_estimate = current_spend
    else:
        daily_spend_estimate = current_spend / (today.day - 1)

    # Total projected spend for the month
    projected_spend = current_spend + (daily_spend_estimate * remaining_days)

    if projected_spend > soft_budget_limit:
        print_verbose("Projected spend exceeds soft budget limit!")
        return True
    return False


def _get_projected_spend_over_limit(
    current_spend: float, soft_budget_limit: Optional[float]
) -> Optional[tuple]:
    import datetime

    if soft_budget_limit is None:
        return None

    today = datetime.date.today()
    end_month = datetime.date(today.year, today.month + 1, 1) - datetime.timedelta(
        days=1
    )
    remaining_days = (end_month - today).days

    daily_spend = current_spend / (
        today.day - 1
    )  # assuming the current spend till today (not including today)
    projected_spend = daily_spend * remaining_days

    if projected_spend > soft_budget_limit:
        approx_days = soft_budget_limit / daily_spend
        limit_exceed_date = today + datetime.timedelta(days=approx_days)

        # return the projected spend and the date it will exceeded
        return projected_spend, limit_exceed_date

    return None


def _is_valid_team_configs(team_id=None, team_config=None, request_data=None):
    if team_id is None or team_config is None or request_data is None:
        return
    # check if valid model called for team
    if "models" in team_config:
        valid_models = team_config.pop("models")
        model_in_request = request_data["model"]
        if model_in_request not in valid_models:
            raise Exception(
                f"Invalid model for team {team_id}: {model_in_request}.  Valid models for team are: {valid_models}\n"
            )
    return


def _to_ns(dt):
    return int(dt.timestamp() * 1e9)


def get_error_message_str(e: Exception) -> str:
    error_message = ""
    if isinstance(e, HTTPException):
        if isinstance(e.detail, str):
            error_message = e.detail
        elif isinstance(e.detail, dict):
            error_message = json.dumps(e.detail)
        elif hasattr(e, "message"):
            _error = getattr(e, "message", None)
            if isinstance(_error, str):
                error_message = _error
            elif isinstance(_error, dict):
                error_message = json.dumps(_error)
        else:
            error_message = str(e)
    else:
        error_message = str(e)
    return error_message


def _get_redoc_url() -> str:
    """
    Get the redoc URL from the environment variables.

    - If REDOC_URL is set, return it.
    - Otherwise, default to "/redoc".
    """
    return os.getenv("REDOC_URL", "/redoc")


def _get_docs_url() -> Optional[str]:
    """
    Get the docs URL from the environment variables.

    - If DOCS_URL is set, return it.
    - If NO_DOCS is True, return None.
    - Otherwise, default to "/".
    """
    docs_url = os.getenv("DOCS_URL", None)
    if docs_url:
        return docs_url

    if os.getenv("NO_DOCS", "False") == "True":
        return None

    # default to "/"
    return "/"


def handle_exception_on_proxy(e: Exception) -> ProxyException:
    """
    Returns an Exception as ProxyException, this ensures all exceptions are OpenAI API compatible
    """
    from fastapi import status

    verbose_proxy_logger.exception(f"Exception: {e}")

    if isinstance(e, HTTPException):
        return ProxyException(
            message=getattr(e, "detail", f"error({str(e)})"),
            type=ProxyErrorTypes.internal_server_error,
            param=getattr(e, "param", "None"),
            code=getattr(e, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
        )
    elif isinstance(e, ProxyException):
        return e
    return ProxyException(
        message="Internal Server Error, " + str(e),
        type=ProxyErrorTypes.internal_server_error,
        param=getattr(e, "param", "None"),
        code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _premium_user_check():
    """
    Raises an HTTPException if the user is not a premium user
    """
    from litellm.proxy.proxy_server import premium_user

    if not premium_user:
        raise HTTPException(
            status_code=403,
            detail={
                "error": f"This feature is only available for LiteLLM Enterprise users. {CommonProxyErrors.not_premium_user.value}"
            },
        )


def is_known_model(model: Optional[str], llm_router: Optional[Router]) -> bool:
    """
    Returns True if the model is in the llm_router model names
    """
    if model is None or llm_router is None:
        return False
    model_names = llm_router.get_model_names()

    is_in_list = False
    if model in model_names:
        is_in_list = True

    return is_in_list


def join_paths(base_path: str, route: str) -> str:
    # Remove trailing slashes from base_path and leading slashes from route
    base_path = base_path.rstrip("/")
    route = route.lstrip("/")
    
    # If base_path is empty, return route with leading slash
    if not base_path:
        return f"/{route}" if route else "/"
    
    # If route is empty, return just base_path
    if not route:
        return base_path
    
    # Join with single slash
    return f"{base_path}/{route}"


def get_custom_url(request_base_url: str, route: Optional[str] = None) -> str:
    # Use environment variable value, otherwise use URL from request
    server_base_url = get_proxy_base_url()
    if server_base_url is not None:
        base_url = server_base_url
    else:
        base_url = request_base_url
    
    server_root_path = get_server_root_path()
    if route is not None:
        if server_root_path != "":
            # First join base_url with server_root_path, then with route
            intermediate_url = join_paths(base_url, server_root_path)
            return join_paths(intermediate_url, route)
        else:
            return join_paths(base_url, route)
    else:
        return join_paths(base_url, server_root_path)


def get_proxy_base_url() -> Optional[str]:
    """
    Get the proxy base url from the environment variables.
    """
    return os.getenv("PROXY_BASE_URL")


def get_server_root_path() -> str:
    """
    Get the server root path from the environment variables.

    - If SERVER_ROOT_PATH is set, return it.
    - Otherwise, default to "/".
    """
    return os.getenv("SERVER_ROOT_PATH", "/")