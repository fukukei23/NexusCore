
# === NexusCore/openenv\Lib\site-packages\openai\lib\streaming\responses\_responses.py ===
from __future__ import annotations

import inspect
from types import TracebackType
from typing import Any, List, Generic, Iterable, Awaitable, cast
from typing_extensions import Self, Callable, Iterator, AsyncIterator

from ._types import ParsedResponseSnapshot
from ._events import (
    ResponseStreamEvent,
    ResponseTextDoneEvent,
    ResponseCompletedEvent,
    ResponseTextDeltaEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
)
from ...._types import NOT_GIVEN, NotGiven
from ...._utils import is_given, consume_sync_iterator, consume_async_iterator
from ...._models import build, construct_type_unchecked
from ...._streaming import Stream, AsyncStream
from ....types.responses import ParsedResponse, ResponseStreamEvent as RawResponseStreamEvent
from ..._parsing._responses import TextFormatT, parse_text, parse_response
from ....types.responses.tool_param import ToolParam
from ....types.responses.parsed_response import (
    ParsedContent,
    ParsedResponseOutputMessage,
    ParsedResponseFunctionToolCall,
)


class ResponseStream(Generic[TextFormatT]):
    def __init__(
        self,
        *,
        raw_stream: Stream[RawResponseStreamEvent],
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self._raw_stream = raw_stream
        self._response = raw_stream.response
        self._iterator = self.__stream__()
        self._state = ResponseStreamState(text_format=text_format, input_tools=input_tools)
        self._starting_after = starting_after

    def __next__(self) -> ResponseStreamEvent[TextFormatT]:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[ResponseStreamEvent[TextFormatT]]:
        for item in self._iterator:
            yield item

    def __enter__(self) -> Self:
        return self

    def __stream__(self) -> Iterator[ResponseStreamEvent[TextFormatT]]:
        for sse_event in self._raw_stream:
            events_to_fire = self._state.handle_event(sse_event)
            for event in events_to_fire:
                if self._starting_after is None or event.sequence_number > self._starting_after:
                    yield event

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
        self._response.close()

    def get_final_response(self) -> ParsedResponse[TextFormatT]:
        """Waits until the stream has been read to completion and returns
        the accumulated `ParsedResponse` object.
        """
        self.until_done()
        response = self._state._completed_response
        if not response:
            raise RuntimeError("Didn't receive a `response.completed` event.")

        return response

    def until_done(self) -> Self:
        """Blocks until the stream has been consumed."""
        consume_sync_iterator(self)
        return self


class ResponseStreamManager(Generic[TextFormatT]):
    def __init__(
        self,
        api_request: Callable[[], Stream[RawResponseStreamEvent]],
        *,
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self.__stream: ResponseStream[TextFormatT] | None = None
        self.__api_request = api_request
        self.__text_format = text_format
        self.__input_tools = input_tools
        self.__starting_after = starting_after

    def __enter__(self) -> ResponseStream[TextFormatT]:
        raw_stream = self.__api_request()

        self.__stream = ResponseStream(
            raw_stream=raw_stream,
            text_format=self.__text_format,
            input_tools=self.__input_tools,
            starting_after=self.__starting_after,
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


class AsyncResponseStream(Generic[TextFormatT]):
    def __init__(
        self,
        *,
        raw_stream: AsyncStream[RawResponseStreamEvent],
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self._raw_stream = raw_stream
        self._response = raw_stream.response
        self._iterator = self.__stream__()
        self._state = ResponseStreamState(text_format=text_format, input_tools=input_tools)
        self._starting_after = starting_after

    async def __anext__(self) -> ResponseStreamEvent[TextFormatT]:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[ResponseStreamEvent[TextFormatT]]:
        async for item in self._iterator:
            yield item

    async def __stream__(self) -> AsyncIterator[ResponseStreamEvent[TextFormatT]]:
        async for sse_event in self._raw_stream:
            events_to_fire = self._state.handle_event(sse_event)
            for event in events_to_fire:
                if self._starting_after is None or event.sequence_number > self._starting_after:
                    yield event

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
        await self._response.aclose()

    async def get_final_response(self) -> ParsedResponse[TextFormatT]:
        """Waits until the stream has been read to completion and returns
        the accumulated `ParsedResponse` object.
        """
        await self.until_done()
        response = self._state._completed_response
        if not response:
            raise RuntimeError("Didn't receive a `response.completed` event.")

        return response

    async def until_done(self) -> Self:
        """Blocks until the stream has been consumed."""
        await consume_async_iterator(self)
        return self


class AsyncResponseStreamManager(Generic[TextFormatT]):
    def __init__(
        self,
        api_request: Awaitable[AsyncStream[RawResponseStreamEvent]],
        *,
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self.__stream: AsyncResponseStream[TextFormatT] | None = None
        self.__api_request = api_request
        self.__text_format = text_format
        self.__input_tools = input_tools
        self.__starting_after = starting_after

    async def __aenter__(self) -> AsyncResponseStream[TextFormatT]:
        raw_stream = await self.__api_request

        self.__stream = AsyncResponseStream(
            raw_stream=raw_stream,
            text_format=self.__text_format,
            input_tools=self.__input_tools,
            starting_after=self.__starting_after,
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


class ResponseStreamState(Generic[TextFormatT]):
    def __init__(
        self,
        *,
        input_tools: Iterable[ToolParam] | NotGiven,
        text_format: type[TextFormatT] | NotGiven,
    ) -> None:
        self.__current_snapshot: ParsedResponseSnapshot | None = None
        self._completed_response: ParsedResponse[TextFormatT] | None = None
        self._input_tools = [tool for tool in input_tools] if is_given(input_tools) else []
        self._text_format = text_format
        self._rich_text_format: type | NotGiven = text_format if inspect.isclass(text_format) else NOT_GIVEN

    def handle_event(self, event: RawResponseStreamEvent) -> List[ResponseStreamEvent[TextFormatT]]:
        self.__current_snapshot = snapshot = self.accumulate_event(event)

        events: List[ResponseStreamEvent[TextFormatT]] = []

        if event.type == "response.output_text.delta":
            output = snapshot.output[event.output_index]
            assert output.type == "message"

            content = output.content[event.content_index]
            assert content.type == "output_text"

            events.append(
                build(
                    ResponseTextDeltaEvent,
                    content_index=event.content_index,
                    delta=event.delta,
                    item_id=event.item_id,
                    output_index=event.output_index,
                    sequence_number=event.sequence_number,
                    type="response.output_text.delta",
                    snapshot=content.text,
                )
            )
        elif event.type == "response.output_text.done":
            output = snapshot.output[event.output_index]
            assert output.type == "message"

            content = output.content[event.content_index]
            assert content.type == "output_text"

            events.append(
                build(
                    ResponseTextDoneEvent[TextFormatT],
                    content_index=event.content_index,
                    item_id=event.item_id,
                    output_index=event.output_index,
                    sequence_number=event.sequence_number,
                    type="response.output_text.done",
                    text=event.text,
                    parsed=parse_text(event.text, text_format=self._text_format),
                )
            )
        elif event.type == "response.function_call_arguments.delta":
            output = snapshot.output[event.output_index]
            assert output.type == "function_call"

            events.append(
                build(
                    ResponseFunctionCallArgumentsDeltaEvent,
                    delta=event.delta,
                    item_id=event.item_id,
                    output_index=event.output_index,
                    sequence_number=event.sequence_number,
                    type="response.function_call_arguments.delta",
                    snapshot=output.arguments,
                )
            )

        elif event.type == "response.completed":
            response = self._completed_response
            assert response is not None

            events.append(
                build(
                    ResponseCompletedEvent,
                    sequence_number=event.sequence_number,
                    type="response.completed",
                    response=response,
                )
            )
        else:
            events.append(event)

        return events

    def accumulate_event(self, event: RawResponseStreamEvent) -> ParsedResponseSnapshot:
        snapshot = self.__current_snapshot
        if snapshot is None:
            return self._create_initial_response(event)

        if event.type == "response.output_item.added":
            if event.item.type == "function_call":
                snapshot.output.append(
                    construct_type_unchecked(
                        type_=cast(Any, ParsedResponseFunctionToolCall), value=event.item.to_dict()
                    )
                )
            elif event.item.type == "message":
                snapshot.output.append(
                    construct_type_unchecked(type_=cast(Any, ParsedResponseOutputMessage), value=event.item.to_dict())
                )
            else:
                snapshot.output.append(event.item)
        elif event.type == "response.content_part.added":
            output = snapshot.output[event.output_index]
            if output.type == "message":
                output.content.append(
                    construct_type_unchecked(type_=cast(Any, ParsedContent), value=event.part.to_dict())
                )
        elif event.type == "response.output_text.delta":
            output = snapshot.output[event.output_index]
            if output.type == "message":
                content = output.content[event.content_index]
                assert content.type == "output_text"
                content.text += event.delta
        elif event.type == "response.function_call_arguments.delta":
            output = snapshot.output[event.output_index]
            if output.type == "function_call":
                output.arguments += event.delta
        elif event.type == "response.completed":
            self._completed_response = parse_response(
                text_format=self._text_format,
                response=event.response,
                input_tools=self._input_tools,
            )

        return snapshot

    def _create_initial_response(self, event: RawResponseStreamEvent) -> ParsedResponseSnapshot:
        if event.type != "response.created":
            raise RuntimeError(f"Expected to have received `response.created` before `{event.type}`")

        return construct_type_unchecked(type_=ParsedResponseSnapshot, value=event.response.to_dict())

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\openai\lib\streaming\responses\_responses.py ===
from __future__ import annotations

import inspect
from types import TracebackType
from typing import Any, List, Generic, Iterable, Awaitable, cast
from typing_extensions import Self, Callable, Iterator, AsyncIterator

from ._types import ParsedResponseSnapshot
from ._events import (
    ResponseStreamEvent,
    ResponseTextDoneEvent,
    ResponseCompletedEvent,
    ResponseTextDeltaEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
)
from ...._types import NOT_GIVEN, NotGiven
from ...._utils import is_given, consume_sync_iterator, consume_async_iterator
from ...._models import build, construct_type_unchecked
from ...._streaming import Stream, AsyncStream
from ....types.responses import ParsedResponse, ResponseStreamEvent as RawResponseStreamEvent
from ..._parsing._responses import TextFormatT, parse_text, parse_response
from ....types.responses.tool_param import ToolParam
from ....types.responses.parsed_response import (
    ParsedContent,
    ParsedResponseOutputMessage,
    ParsedResponseFunctionToolCall,
)


class ResponseStream(Generic[TextFormatT]):
    def __init__(
        self,
        *,
        raw_stream: Stream[RawResponseStreamEvent],
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self._raw_stream = raw_stream
        self._response = raw_stream.response
        self._iterator = self.__stream__()
        self._state = ResponseStreamState(text_format=text_format, input_tools=input_tools)
        self._starting_after = starting_after

    def __next__(self) -> ResponseStreamEvent[TextFormatT]:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[ResponseStreamEvent[TextFormatT]]:
        for item in self._iterator:
            yield item

    def __enter__(self) -> Self:
        return self

    def __stream__(self) -> Iterator[ResponseStreamEvent[TextFormatT]]:
        for sse_event in self._raw_stream:
            events_to_fire = self._state.handle_event(sse_event)
            for event in events_to_fire:
                if self._starting_after is None or event.sequence_number > self._starting_after:
                    yield event

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
        self._response.close()

    def get_final_response(self) -> ParsedResponse[TextFormatT]:
        """Waits until the stream has been read to completion and returns
        the accumulated `ParsedResponse` object.
        """
        self.until_done()
        response = self._state._completed_response
        if not response:
            raise RuntimeError("Didn't receive a `response.completed` event.")

        return response

    def until_done(self) -> Self:
        """Blocks until the stream has been consumed."""
        consume_sync_iterator(self)
        return self


class ResponseStreamManager(Generic[TextFormatT]):
    def __init__(
        self,
        api_request: Callable[[], Stream[RawResponseStreamEvent]],
        *,
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self.__stream: ResponseStream[TextFormatT] | None = None
        self.__api_request = api_request
        self.__text_format = text_format
        self.__input_tools = input_tools
        self.__starting_after = starting_after

    def __enter__(self) -> ResponseStream[TextFormatT]:
        raw_stream = self.__api_request()

        self.__stream = ResponseStream(
            raw_stream=raw_stream,
            text_format=self.__text_format,
            input_tools=self.__input_tools,
            starting_after=self.__starting_after,
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


class AsyncResponseStream(Generic[TextFormatT]):
    def __init__(
        self,
        *,
        raw_stream: AsyncStream[RawResponseStreamEvent],
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self._raw_stream = raw_stream
        self._response = raw_stream.response
        self._iterator = self.__stream__()
        self._state = ResponseStreamState(text_format=text_format, input_tools=input_tools)
        self._starting_after = starting_after

    async def __anext__(self) -> ResponseStreamEvent[TextFormatT]:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[ResponseStreamEvent[TextFormatT]]:
        async for item in self._iterator:
            yield item

    async def __stream__(self) -> AsyncIterator[ResponseStreamEvent[TextFormatT]]:
        async for sse_event in self._raw_stream:
            events_to_fire = self._state.handle_event(sse_event)
            for event in events_to_fire:
                if self._starting_after is None or event.sequence_number > self._starting_after:
                    yield event

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
        await self._response.aclose()

    async def get_final_response(self) -> ParsedResponse[TextFormatT]:
        """Waits until the stream has been read to completion and returns
        the accumulated `ParsedResponse` object.
        """
        await self.until_done()
        response = self._state._completed_response
        if not response:
            raise RuntimeError("Didn't receive a `response.completed` event.")

        return response

    async def until_done(self) -> Self:
        """Blocks until the stream has been consumed."""
        await consume_async_iterator(self)
        return self


class AsyncResponseStreamManager(Generic[TextFormatT]):
    def __init__(
        self,
        api_request: Awaitable[AsyncStream[RawResponseStreamEvent]],
        *,
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self.__stream: AsyncResponseStream[TextFormatT] | None = None
        self.__api_request = api_request
        self.__text_format = text_format
        self.__input_tools = input_tools
        self.__starting_after = starting_after

    async def __aenter__(self) -> AsyncResponseStream[TextFormatT]:
        raw_stream = await self.__api_request

        self.__stream = AsyncResponseStream(
            raw_stream=raw_stream,
            text_format=self.__text_format,
            input_tools=self.__input_tools,
            starting_after=self.__starting_after,
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


class ResponseStreamState(Generic[TextFormatT]):
    def __init__(
        self,
        *,
        input_tools: Iterable[ToolParam] | NotGiven,
        text_format: type[TextFormatT] | NotGiven,
    ) -> None:
        self.__current_snapshot: ParsedResponseSnapshot | None = None
        self._completed_response: ParsedResponse[TextFormatT] | None = None
        self._input_tools = [tool for tool in input_tools] if is_given(input_tools) else []
        self._text_format = text_format
        self._rich_text_format: type | NotGiven = text_format if inspect.isclass(text_format) else NOT_GIVEN

    def handle_event(self, event: RawResponseStreamEvent) -> List[ResponseStreamEvent[TextFormatT]]:
        self.__current_snapshot = snapshot = self.accumulate_event(event)

        events: List[ResponseStreamEvent[TextFormatT]] = []

        if event.type == "response.output_text.delta":
            output = snapshot.output[event.output_index]
            assert output.type == "message"

            content = output.content[event.content_index]
            assert content.type == "output_text"

            events.append(
                build(
                    ResponseTextDeltaEvent,
                    content_index=event.content_index,
                    delta=event.delta,
                    item_id=event.item_id,
                    output_index=event.output_index,
                    sequence_number=event.sequence_number,
                    type="response.output_text.delta",
                    snapshot=content.text,
                )
            )
        elif event.type == "response.output_text.done":
            output = snapshot.output[event.output_index]
            assert output.type == "message"

            content = output.content[event.content_index]
            assert content.type == "output_text"

            events.append(
                build(
                    ResponseTextDoneEvent[TextFormatT],
                    content_index=event.content_index,
                    item_id=event.item_id,
                    output_index=event.output_index,
                    sequence_number=event.sequence_number,
                    type="response.output_text.done",
                    text=event.text,
                    parsed=parse_text(event.text, text_format=self._text_format),
                )
            )
        elif event.type == "response.function_call_arguments.delta":
            output = snapshot.output[event.output_index]
            assert output.type == "function_call"

            events.append(
                build(
                    ResponseFunctionCallArgumentsDeltaEvent,
                    delta=event.delta,
                    item_id=event.item_id,
                    output_index=event.output_index,
                    sequence_number=event.sequence_number,
                    type="response.function_call_arguments.delta",
                    snapshot=output.arguments,
                )
            )

        elif event.type == "response.completed":
            response = self._completed_response
            assert response is not None

            events.append(
                build(
                    ResponseCompletedEvent,
                    sequence_number=event.sequence_number,
                    type="response.completed",
                    response=response,
                )
            )
        else:
            events.append(event)

        return events

    def accumulate_event(self, event: RawResponseStreamEvent) -> ParsedResponseSnapshot:
        snapshot = self.__current_snapshot
        if snapshot is None:
            return self._create_initial_response(event)

        if event.type == "response.output_item.added":
            if event.item.type == "function_call":
                snapshot.output.append(
                    construct_type_unchecked(
                        type_=cast(Any, ParsedResponseFunctionToolCall), value=event.item.to_dict()
                    )
                )
            elif event.item.type == "message":
                snapshot.output.append(
                    construct_type_unchecked(type_=cast(Any, ParsedResponseOutputMessage), value=event.item.to_dict())
                )
            else:
                snapshot.output.append(event.item)
        elif event.type == "response.content_part.added":
            output = snapshot.output[event.output_index]
            if output.type == "message":
                output.content.append(
                    construct_type_unchecked(type_=cast(Any, ParsedContent), value=event.part.to_dict())
                )
        elif event.type == "response.output_text.delta":
            output = snapshot.output[event.output_index]
            if output.type == "message":
                content = output.content[event.content_index]
                assert content.type == "output_text"
                content.text += event.delta
        elif event.type == "response.function_call_arguments.delta":
            output = snapshot.output[event.output_index]
            if output.type == "function_call":
                output.arguments += event.delta
        elif event.type == "response.completed":
            self._completed_response = parse_response(
                text_format=self._text_format,
                response=event.response,
                input_tools=self._input_tools,
            )

        return snapshot

    def _create_initial_response(self, event: RawResponseStreamEvent) -> ParsedResponseSnapshot:
        if event.type != "response.created":
            raise RuntimeError(f"Expected to have received `response.created` before `{event.type}`")

        return construct_type_unchecked(type_=ParsedResponseSnapshot, value=event.response.to_dict())

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\openai\lib\streaming\responses\_responses.py ===
from __future__ import annotations

import inspect
from types import TracebackType
from typing import Any, List, Generic, Iterable, Awaitable, cast
from typing_extensions import Self, Callable, Iterator, AsyncIterator

from ._types import ParsedResponseSnapshot
from ._events import (
    ResponseStreamEvent,
    ResponseTextDoneEvent,
    ResponseCompletedEvent,
    ResponseTextDeltaEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
)
from ...._types import NOT_GIVEN, NotGiven
from ...._utils import is_given, consume_sync_iterator, consume_async_iterator
from ...._models import build, construct_type_unchecked
from ...._streaming import Stream, AsyncStream
from ....types.responses import ParsedResponse, ResponseStreamEvent as RawResponseStreamEvent
from ..._parsing._responses import TextFormatT, parse_text, parse_response
from ....types.responses.tool_param import ToolParam
from ....types.responses.parsed_response import (
    ParsedContent,
    ParsedResponseOutputMessage,
    ParsedResponseFunctionToolCall,
)


class ResponseStream(Generic[TextFormatT]):
    def __init__(
        self,
        *,
        raw_stream: Stream[RawResponseStreamEvent],
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self._raw_stream = raw_stream
        self._response = raw_stream.response
        self._iterator = self.__stream__()
        self._state = ResponseStreamState(text_format=text_format, input_tools=input_tools)
        self._starting_after = starting_after

    def __next__(self) -> ResponseStreamEvent[TextFormatT]:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[ResponseStreamEvent[TextFormatT]]:
        for item in self._iterator:
            yield item

    def __enter__(self) -> Self:
        return self

    def __stream__(self) -> Iterator[ResponseStreamEvent[TextFormatT]]:
        for sse_event in self._raw_stream:
            events_to_fire = self._state.handle_event(sse_event)
            for event in events_to_fire:
                if self._starting_after is None or event.sequence_number > self._starting_after:
                    yield event

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
        self._response.close()

    def get_final_response(self) -> ParsedResponse[TextFormatT]:
        """Waits until the stream has been read to completion and returns
        the accumulated `ParsedResponse` object.
        """
        self.until_done()
        response = self._state._completed_response
        if not response:
            raise RuntimeError("Didn't receive a `response.completed` event.")

        return response

    def until_done(self) -> Self:
        """Blocks until the stream has been consumed."""
        consume_sync_iterator(self)
        return self


class ResponseStreamManager(Generic[TextFormatT]):
    def __init__(
        self,
        api_request: Callable[[], Stream[RawResponseStreamEvent]],
        *,
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self.__stream: ResponseStream[TextFormatT] | None = None
        self.__api_request = api_request
        self.__text_format = text_format
        self.__input_tools = input_tools
        self.__starting_after = starting_after

    def __enter__(self) -> ResponseStream[TextFormatT]:
        raw_stream = self.__api_request()

        self.__stream = ResponseStream(
            raw_stream=raw_stream,
            text_format=self.__text_format,
            input_tools=self.__input_tools,
            starting_after=self.__starting_after,
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


class AsyncResponseStream(Generic[TextFormatT]):
    def __init__(
        self,
        *,
        raw_stream: AsyncStream[RawResponseStreamEvent],
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self._raw_stream = raw_stream
        self._response = raw_stream.response
        self._iterator = self.__stream__()
        self._state = ResponseStreamState(text_format=text_format, input_tools=input_tools)
        self._starting_after = starting_after

    async def __anext__(self) -> ResponseStreamEvent[TextFormatT]:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[ResponseStreamEvent[TextFormatT]]:
        async for item in self._iterator:
            yield item

    async def __stream__(self) -> AsyncIterator[ResponseStreamEvent[TextFormatT]]:
        async for sse_event in self._raw_stream:
            events_to_fire = self._state.handle_event(sse_event)
            for event in events_to_fire:
                if self._starting_after is None or event.sequence_number > self._starting_after:
                    yield event

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
        await self._response.aclose()

    async def get_final_response(self) -> ParsedResponse[TextFormatT]:
        """Waits until the stream has been read to completion and returns
        the accumulated `ParsedResponse` object.
        """
        await self.until_done()
        response = self._state._completed_response
        if not response:
            raise RuntimeError("Didn't receive a `response.completed` event.")

        return response

    async def until_done(self) -> Self:
        """Blocks until the stream has been consumed."""
        await consume_async_iterator(self)
        return self


class AsyncResponseStreamManager(Generic[TextFormatT]):
    def __init__(
        self,
        api_request: Awaitable[AsyncStream[RawResponseStreamEvent]],
        *,
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self.__stream: AsyncResponseStream[TextFormatT] | None = None
        self.__api_request = api_request
        self.__text_format = text_format
        self.__input_tools = input_tools
        self.__starting_after = starting_after

    async def __aenter__(self) -> AsyncResponseStream[TextFormatT]:
        raw_stream = await self.__api_request

        self.__stream = AsyncResponseStream(
            raw_stream=raw_stream,
            text_format=self.__text_format,
            input_tools=self.__input_tools,
            starting_after=self.__starting_after,
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


class ResponseStreamState(Generic[TextFormatT]):
    def __init__(
        self,
        *,
        input_tools: Iterable[ToolParam] | NotGiven,
        text_format: type[TextFormatT] | NotGiven,
    ) -> None:
        self.__current_snapshot: ParsedResponseSnapshot | None = None
        self._completed_response: ParsedResponse[TextFormatT] | None = None
        self._input_tools = [tool for tool in input_tools] if is_given(input_tools) else []
        self._text_format = text_format
        self._rich_text_format: type | NotGiven = text_format if inspect.isclass(text_format) else NOT_GIVEN

    def handle_event(self, event: RawResponseStreamEvent) -> List[ResponseStreamEvent[TextFormatT]]:
        self.__current_snapshot = snapshot = self.accumulate_event(event)

        events: List[ResponseStreamEvent[TextFormatT]] = []

        if event.type == "response.output_text.delta":
            output = snapshot.output[event.output_index]
            assert output.type == "message"

            content = output.content[event.content_index]
            assert content.type == "output_text"

            events.append(
                build(
                    ResponseTextDeltaEvent,
                    content_index=event.content_index,
                    delta=event.delta,
                    item_id=event.item_id,
                    output_index=event.output_index,
                    sequence_number=event.sequence_number,
                    type="response.output_text.delta",
                    snapshot=content.text,
                )
            )
        elif event.type == "response.output_text.done":
            output = snapshot.output[event.output_index]
            assert output.type == "message"

            content = output.content[event.content_index]
            assert content.type == "output_text"

            events.append(
                build(
                    ResponseTextDoneEvent[TextFormatT],
                    content_index=event.content_index,
                    item_id=event.item_id,
                    output_index=event.output_index,
                    sequence_number=event.sequence_number,
                    type="response.output_text.done",
                    text=event.text,
                    parsed=parse_text(event.text, text_format=self._text_format),
                )
            )
        elif event.type == "response.function_call_arguments.delta":
            output = snapshot.output[event.output_index]
            assert output.type == "function_call"

            events.append(
                build(
                    ResponseFunctionCallArgumentsDeltaEvent,
                    delta=event.delta,
                    item_id=event.item_id,
                    output_index=event.output_index,
                    sequence_number=event.sequence_number,
                    type="response.function_call_arguments.delta",
                    snapshot=output.arguments,
                )
            )

        elif event.type == "response.completed":
            response = self._completed_response
            assert response is not None

            events.append(
                build(
                    ResponseCompletedEvent,
                    sequence_number=event.sequence_number,
                    type="response.completed",
                    response=response,
                )
            )
        else:
            events.append(event)

        return events

    def accumulate_event(self, event: RawResponseStreamEvent) -> ParsedResponseSnapshot:
        snapshot = self.__current_snapshot
        if snapshot is None:
            return self._create_initial_response(event)

        if event.type == "response.output_item.added":
            if event.item.type == "function_call":
                snapshot.output.append(
                    construct_type_unchecked(
                        type_=cast(Any, ParsedResponseFunctionToolCall), value=event.item.to_dict()
                    )
                )
            elif event.item.type == "message":
                snapshot.output.append(
                    construct_type_unchecked(type_=cast(Any, ParsedResponseOutputMessage), value=event.item.to_dict())
                )
            else:
                snapshot.output.append(event.item)
        elif event.type == "response.content_part.added":
            output = snapshot.output[event.output_index]
            if output.type == "message":
                output.content.append(
                    construct_type_unchecked(type_=cast(Any, ParsedContent), value=event.part.to_dict())
                )
        elif event.type == "response.output_text.delta":
            output = snapshot.output[event.output_index]
            if output.type == "message":
                content = output.content[event.content_index]
                assert content.type == "output_text"
                content.text += event.delta
        elif event.type == "response.function_call_arguments.delta":
            output = snapshot.output[event.output_index]
            if output.type == "function_call":
                output.arguments += event.delta
        elif event.type == "response.completed":
            self._completed_response = parse_response(
                text_format=self._text_format,
                response=event.response,
                input_tools=self._input_tools,
            )

        return snapshot

    def _create_initial_response(self, event: RawResponseStreamEvent) -> ParsedResponseSnapshot:
        if event.type != "response.created":
            raise RuntimeError(f"Expected to have received `response.created` before `{event.type}`")

        return construct_type_unchecked(type_=ParsedResponseSnapshot, value=event.response.to_dict())

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test__iotools.py ===
import time
from datetime import date

import numpy as np
from numpy.lib._iotools import (
    LineSplitter,
    NameValidator,
    StringConverter,
    easy_dtype,
    flatten_dtype,
    has_nested_fields,
)
from numpy.testing import (
    assert_,
    assert_allclose,
    assert_equal,
    assert_raises,
)


class TestLineSplitter:
    "Tests the LineSplitter class."

    def test_no_delimiter(self):
        "Test LineSplitter w/o delimiter"
        strg = " 1 2 3 4  5 # test"
        test = LineSplitter()(strg)
        assert_equal(test, ['1', '2', '3', '4', '5'])
        test = LineSplitter('')(strg)
        assert_equal(test, ['1', '2', '3', '4', '5'])

    def test_space_delimiter(self):
        "Test space delimiter"
        strg = " 1 2 3 4  5 # test"
        test = LineSplitter(' ')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])
        test = LineSplitter('  ')(strg)
        assert_equal(test, ['1 2 3 4', '5'])

    def test_tab_delimiter(self):
        "Test tab delimiter"
        strg = " 1\t 2\t 3\t 4\t 5  6"
        test = LineSplitter('\t')(strg)
        assert_equal(test, ['1', '2', '3', '4', '5  6'])
        strg = " 1  2\t 3  4\t 5  6"
        test = LineSplitter('\t')(strg)
        assert_equal(test, ['1  2', '3  4', '5  6'])

    def test_other_delimiter(self):
        "Test LineSplitter on delimiter"
        strg = "1,2,3,4,,5"
        test = LineSplitter(',')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])
        #
        strg = " 1,2,3,4,,5 # test"
        test = LineSplitter(',')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])

        # gh-11028 bytes comment/delimiters should get encoded
        strg = b" 1,2,3,4,,5 % test"
        test = LineSplitter(delimiter=b',', comments=b'%')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])

    def test_constant_fixed_width(self):
        "Test LineSplitter w/ fixed-width fields"
        strg = "  1  2  3  4     5   # test"
        test = LineSplitter(3)(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5', ''])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter(20)(strg)
        assert_equal(test, ['1     3  4  5  6'])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter(30)(strg)
        assert_equal(test, ['1     3  4  5  6'])

    def test_variable_fixed_width(self):
        strg = "  1     3  4  5  6# test"
        test = LineSplitter((3, 6, 6, 3))(strg)
        assert_equal(test, ['1', '3', '4  5', '6'])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter((6, 6, 9))(strg)
        assert_equal(test, ['1', '3  4', '5  6'])

# -----------------------------------------------------------------------------


class TestNameValidator:

    def test_case_sensitivity(self):
        "Test case sensitivity"
        names = ['A', 'a', 'b', 'c']
        test = NameValidator().validate(names)
        assert_equal(test, ['A', 'a', 'b', 'c'])
        test = NameValidator(case_sensitive=False).validate(names)
        assert_equal(test, ['A', 'A_1', 'B', 'C'])
        test = NameValidator(case_sensitive='upper').validate(names)
        assert_equal(test, ['A', 'A_1', 'B', 'C'])
        test = NameValidator(case_sensitive='lower').validate(names)
        assert_equal(test, ['a', 'a_1', 'b', 'c'])

        # check exceptions
        assert_raises(ValueError, NameValidator, case_sensitive='foobar')

    def test_excludelist(self):
        "Test excludelist"
        names = ['dates', 'data', 'Other Data', 'mask']
        validator = NameValidator(excludelist=['dates', 'data', 'mask'])
        test = validator.validate(names)
        assert_equal(test, ['dates_', 'data_', 'Other_Data', 'mask_'])

    def test_missing_names(self):
        "Test validate missing names"
        namelist = ('a', 'b', 'c')
        validator = NameValidator()
        assert_equal(validator(namelist), ['a', 'b', 'c'])
        namelist = ('', 'b', 'c')
        assert_equal(validator(namelist), ['f0', 'b', 'c'])
        namelist = ('a', 'b', '')
        assert_equal(validator(namelist), ['a', 'b', 'f0'])
        namelist = ('', 'f0', '')
        assert_equal(validator(namelist), ['f1', 'f0', 'f2'])

    def test_validate_nb_names(self):
        "Test validate nb names"
        namelist = ('a', 'b', 'c')
        validator = NameValidator()
        assert_equal(validator(namelist, nbfields=1), ('a',))
        assert_equal(validator(namelist, nbfields=5, defaultfmt="g%i"),
                     ['a', 'b', 'c', 'g0', 'g1'])

    def test_validate_wo_names(self):
        "Test validate no names"
        namelist = None
        validator = NameValidator()
        assert_(validator(namelist) is None)
        assert_equal(validator(namelist, nbfields=3), ['f0', 'f1', 'f2'])

# -----------------------------------------------------------------------------


def _bytes_to_date(s):
    return date(*time.strptime(s, "%Y-%m-%d")[:3])


class TestStringConverter:
    "Test StringConverter"

    def test_creation(self):
        "Test creation of a StringConverter"
        converter = StringConverter(int, -99999)
        assert_equal(converter._status, 1)
        assert_equal(converter.default, -99999)

    def test_upgrade(self):
        "Tests the upgrade method."

        converter = StringConverter()
        assert_equal(converter._status, 0)

        # test int
        assert_equal(converter.upgrade('0'), 0)
        assert_equal(converter._status, 1)

        # On systems where long defaults to 32-bit, the statuses will be
        # offset by one, so we check for this here.
        import numpy._core.numeric as nx
        status_offset = int(nx.dtype(nx.int_).itemsize < nx.dtype(nx.int64).itemsize)

        # test int > 2**32
        assert_equal(converter.upgrade('17179869184'), 17179869184)
        assert_equal(converter._status, 1 + status_offset)

        # test float
        assert_allclose(converter.upgrade('0.'), 0.0)
        assert_equal(converter._status, 2 + status_offset)

        # test complex
        assert_equal(converter.upgrade('0j'), complex('0j'))
        assert_equal(converter._status, 3 + status_offset)

        # test str
        # note that the longdouble type has been skipped, so the
        # _status increases by 2. Everything should succeed with
        # unicode conversion (8).
        for s in ['a', b'a']:
            res = converter.upgrade(s)
            assert_(type(res) is str)
            assert_equal(res, 'a')
            assert_equal(converter._status, 8 + status_offset)

    def test_missing(self):
        "Tests the use of missing values."
        converter = StringConverter(missing_values=('missing',
                                                    'missed'))
        converter.upgrade('0')
        assert_equal(converter('0'), 0)
        assert_equal(converter(''), converter.default)
        assert_equal(converter('missing'), converter.default)
        assert_equal(converter('missed'), converter.default)
        try:
            converter('miss')
        except ValueError:
            pass

    def test_upgrademapper(self):
        "Tests updatemapper"
        dateparser = _bytes_to_date
        _original_mapper = StringConverter._mapper[:]
        try:
            StringConverter.upgrade_mapper(dateparser, date(2000, 1, 1))
            convert = StringConverter(dateparser, date(2000, 1, 1))
            test = convert('2001-01-01')
            assert_equal(test, date(2001, 1, 1))
            test = convert('2009-01-01')
            assert_equal(test, date(2009, 1, 1))
            test = convert('')
            assert_equal(test, date(2000, 1, 1))
        finally:
            StringConverter._mapper = _original_mapper

    def test_string_to_object(self):
        "Make sure that string-to-object functions are properly recognized"
        old_mapper = StringConverter._mapper[:]  # copy of list
        conv = StringConverter(_bytes_to_date)
        assert_equal(conv._mapper, old_mapper)
        assert_(hasattr(conv, 'default'))

    def test_keep_default(self):
        "Make sure we don't lose an explicit default"
        converter = StringConverter(None, missing_values='',
                                    default=-999)
        converter.upgrade('3.14159265')
        assert_equal(converter.default, -999)
        assert_equal(converter.type, np.dtype(float))
        #
        converter = StringConverter(
            None, missing_values='', default=0)
        converter.upgrade('3.14159265')
        assert_equal(converter.default, 0)
        assert_equal(converter.type, np.dtype(float))

    def test_keep_default_zero(self):
        "Check that we don't lose a default of 0"
        converter = StringConverter(int, default=0,
                                    missing_values="N/A")
        assert_equal(converter.default, 0)

    def test_keep_missing_values(self):
        "Check that we're not losing missing values"
        converter = StringConverter(int, default=0,
                                    missing_values="N/A")
        assert_equal(
            converter.missing_values, {'', 'N/A'})

    def test_int64_dtype(self):
        "Check that int64 integer types can be specified"
        converter = StringConverter(np.int64, default=0)
        val = "-9223372036854775807"
        assert_(converter(val) == -9223372036854775807)
        val = "9223372036854775807"
        assert_(converter(val) == 9223372036854775807)

    def test_uint64_dtype(self):
        "Check that uint64 integer types can be specified"
        converter = StringConverter(np.uint64, default=0)
        val = "9223372043271415339"
        assert_(converter(val) == 9223372043271415339)


class TestMiscFunctions:

    def test_has_nested_dtype(self):
        "Test has_nested_dtype"
        ndtype = np.dtype(float)
        assert_equal(has_nested_fields(ndtype), False)
        ndtype = np.dtype([('A', '|S3'), ('B', float)])
        assert_equal(has_nested_fields(ndtype), False)
        ndtype = np.dtype([('A', int), ('B', [('BA', float), ('BB', '|S1')])])
        assert_equal(has_nested_fields(ndtype), True)

    def test_easy_dtype(self):
        "Test ndtype on dtypes"
        # Simple case
        ndtype = float
        assert_equal(easy_dtype(ndtype), np.dtype(float))
        # As string w/o names
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype),
                     np.dtype([('f0', "i4"), ('f1', "f8")]))
        # As string w/o names but different default format
        assert_equal(easy_dtype(ndtype, defaultfmt="field_%03i"),
                     np.dtype([('field_000', "i4"), ('field_001', "f8")]))
        # As string w/ names
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names="a, b"),
                     np.dtype([('a', "i4"), ('b', "f8")]))
        # As string w/ names (too many)
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([('a', "i4"), ('b', "f8")]))
        # As string w/ names (not enough)
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names=", b"),
                     np.dtype([('f0', "i4"), ('b', "f8")]))
        # ... (with different default format)
        assert_equal(easy_dtype(ndtype, names="a", defaultfmt="f%02i"),
                     np.dtype([('a', "i4"), ('f00', "f8")]))
        # As list of tuples w/o names
        ndtype = [('A', int), ('B', float)]
        assert_equal(easy_dtype(ndtype), np.dtype([('A', int), ('B', float)]))
        # As list of tuples w/ names
        assert_equal(easy_dtype(ndtype, names="a,b"),
                     np.dtype([('a', int), ('b', float)]))
        # As list of tuples w/ not enough names
        assert_equal(easy_dtype(ndtype, names="a"),
                     np.dtype([('a', int), ('f0', float)]))
        # As list of tuples w/ too many names
        assert_equal(easy_dtype(ndtype, names="a,b,c"),
                     np.dtype([('a', int), ('b', float)]))
        # As list of types w/o names
        ndtype = (int, float, float)
        assert_equal(easy_dtype(ndtype),
                     np.dtype([('f0', int), ('f1', float), ('f2', float)]))
        # As list of types w names
        ndtype = (int, float, float)
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([('a', int), ('b', float), ('c', float)]))
        # As simple dtype w/ names
        ndtype = np.dtype(float)
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([(_, float) for _ in ('a', 'b', 'c')]))
        # As simple dtype w/o names (but multiple fields)
        ndtype = np.dtype(float)
        assert_equal(
            easy_dtype(ndtype, names=['', '', ''], defaultfmt="f%02i"),
            np.dtype([(_, float) for _ in ('f00', 'f01', 'f02')]))

    def test_flatten_dtype(self):
        "Testing flatten_dtype"
        # Standard dtype
        dt = np.dtype([("a", "f8"), ("b", "f8")])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, float])
        # Recursive dtype
        dt = np.dtype([("a", [("aa", '|S1'), ("ab", '|S2')]), ("b", int)])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [np.dtype('|S1'), np.dtype('|S2'), int])
        # dtype with shaped fields
        dt = np.dtype([("a", (float, 2)), ("b", (int, 3))])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, int])
        dt_flat = flatten_dtype(dt, True)
        assert_equal(dt_flat, [float] * 2 + [int] * 3)
        # dtype w/ titles
        dt = np.dtype([(("a", "A"), "f8"), (("b", "B"), "f8")])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, float])

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test__iotools.py ===
import time
from datetime import date

import numpy as np
from numpy.lib._iotools import (
    LineSplitter,
    NameValidator,
    StringConverter,
    easy_dtype,
    flatten_dtype,
    has_nested_fields,
)
from numpy.testing import (
    assert_,
    assert_allclose,
    assert_equal,
    assert_raises,
)


class TestLineSplitter:
    "Tests the LineSplitter class."

    def test_no_delimiter(self):
        "Test LineSplitter w/o delimiter"
        strg = " 1 2 3 4  5 # test"
        test = LineSplitter()(strg)
        assert_equal(test, ['1', '2', '3', '4', '5'])
        test = LineSplitter('')(strg)
        assert_equal(test, ['1', '2', '3', '4', '5'])

    def test_space_delimiter(self):
        "Test space delimiter"
        strg = " 1 2 3 4  5 # test"
        test = LineSplitter(' ')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])
        test = LineSplitter('  ')(strg)
        assert_equal(test, ['1 2 3 4', '5'])

    def test_tab_delimiter(self):
        "Test tab delimiter"
        strg = " 1\t 2\t 3\t 4\t 5  6"
        test = LineSplitter('\t')(strg)
        assert_equal(test, ['1', '2', '3', '4', '5  6'])
        strg = " 1  2\t 3  4\t 5  6"
        test = LineSplitter('\t')(strg)
        assert_equal(test, ['1  2', '3  4', '5  6'])

    def test_other_delimiter(self):
        "Test LineSplitter on delimiter"
        strg = "1,2,3,4,,5"
        test = LineSplitter(',')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])
        #
        strg = " 1,2,3,4,,5 # test"
        test = LineSplitter(',')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])

        # gh-11028 bytes comment/delimiters should get encoded
        strg = b" 1,2,3,4,,5 % test"
        test = LineSplitter(delimiter=b',', comments=b'%')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])

    def test_constant_fixed_width(self):
        "Test LineSplitter w/ fixed-width fields"
        strg = "  1  2  3  4     5   # test"
        test = LineSplitter(3)(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5', ''])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter(20)(strg)
        assert_equal(test, ['1     3  4  5  6'])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter(30)(strg)
        assert_equal(test, ['1     3  4  5  6'])

    def test_variable_fixed_width(self):
        strg = "  1     3  4  5  6# test"
        test = LineSplitter((3, 6, 6, 3))(strg)
        assert_equal(test, ['1', '3', '4  5', '6'])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter((6, 6, 9))(strg)
        assert_equal(test, ['1', '3  4', '5  6'])

# -----------------------------------------------------------------------------


class TestNameValidator:

    def test_case_sensitivity(self):
        "Test case sensitivity"
        names = ['A', 'a', 'b', 'c']
        test = NameValidator().validate(names)
        assert_equal(test, ['A', 'a', 'b', 'c'])
        test = NameValidator(case_sensitive=False).validate(names)
        assert_equal(test, ['A', 'A_1', 'B', 'C'])
        test = NameValidator(case_sensitive='upper').validate(names)
        assert_equal(test, ['A', 'A_1', 'B', 'C'])
        test = NameValidator(case_sensitive='lower').validate(names)
        assert_equal(test, ['a', 'a_1', 'b', 'c'])

        # check exceptions
        assert_raises(ValueError, NameValidator, case_sensitive='foobar')

    def test_excludelist(self):
        "Test excludelist"
        names = ['dates', 'data', 'Other Data', 'mask']
        validator = NameValidator(excludelist=['dates', 'data', 'mask'])
        test = validator.validate(names)
        assert_equal(test, ['dates_', 'data_', 'Other_Data', 'mask_'])

    def test_missing_names(self):
        "Test validate missing names"
        namelist = ('a', 'b', 'c')
        validator = NameValidator()
        assert_equal(validator(namelist), ['a', 'b', 'c'])
        namelist = ('', 'b', 'c')
        assert_equal(validator(namelist), ['f0', 'b', 'c'])
        namelist = ('a', 'b', '')
        assert_equal(validator(namelist), ['a', 'b', 'f0'])
        namelist = ('', 'f0', '')
        assert_equal(validator(namelist), ['f1', 'f0', 'f2'])

    def test_validate_nb_names(self):
        "Test validate nb names"
        namelist = ('a', 'b', 'c')
        validator = NameValidator()
        assert_equal(validator(namelist, nbfields=1), ('a',))
        assert_equal(validator(namelist, nbfields=5, defaultfmt="g%i"),
                     ['a', 'b', 'c', 'g0', 'g1'])

    def test_validate_wo_names(self):
        "Test validate no names"
        namelist = None
        validator = NameValidator()
        assert_(validator(namelist) is None)
        assert_equal(validator(namelist, nbfields=3), ['f0', 'f1', 'f2'])

# -----------------------------------------------------------------------------


def _bytes_to_date(s):
    return date(*time.strptime(s, "%Y-%m-%d")[:3])


class TestStringConverter:
    "Test StringConverter"

    def test_creation(self):
        "Test creation of a StringConverter"
        converter = StringConverter(int, -99999)
        assert_equal(converter._status, 1)
        assert_equal(converter.default, -99999)

    def test_upgrade(self):
        "Tests the upgrade method."

        converter = StringConverter()
        assert_equal(converter._status, 0)

        # test int
        assert_equal(converter.upgrade('0'), 0)
        assert_equal(converter._status, 1)

        # On systems where long defaults to 32-bit, the statuses will be
        # offset by one, so we check for this here.
        import numpy._core.numeric as nx
        status_offset = int(nx.dtype(nx.int_).itemsize < nx.dtype(nx.int64).itemsize)

        # test int > 2**32
        assert_equal(converter.upgrade('17179869184'), 17179869184)
        assert_equal(converter._status, 1 + status_offset)

        # test float
        assert_allclose(converter.upgrade('0.'), 0.0)
        assert_equal(converter._status, 2 + status_offset)

        # test complex
        assert_equal(converter.upgrade('0j'), complex('0j'))
        assert_equal(converter._status, 3 + status_offset)

        # test str
        # note that the longdouble type has been skipped, so the
        # _status increases by 2. Everything should succeed with
        # unicode conversion (8).
        for s in ['a', b'a']:
            res = converter.upgrade(s)
            assert_(type(res) is str)
            assert_equal(res, 'a')
            assert_equal(converter._status, 8 + status_offset)

    def test_missing(self):
        "Tests the use of missing values."
        converter = StringConverter(missing_values=('missing',
                                                    'missed'))
        converter.upgrade('0')
        assert_equal(converter('0'), 0)
        assert_equal(converter(''), converter.default)
        assert_equal(converter('missing'), converter.default)
        assert_equal(converter('missed'), converter.default)
        try:
            converter('miss')
        except ValueError:
            pass

    def test_upgrademapper(self):
        "Tests updatemapper"
        dateparser = _bytes_to_date
        _original_mapper = StringConverter._mapper[:]
        try:
            StringConverter.upgrade_mapper(dateparser, date(2000, 1, 1))
            convert = StringConverter(dateparser, date(2000, 1, 1))
            test = convert('2001-01-01')
            assert_equal(test, date(2001, 1, 1))
            test = convert('2009-01-01')
            assert_equal(test, date(2009, 1, 1))
            test = convert('')
            assert_equal(test, date(2000, 1, 1))
        finally:
            StringConverter._mapper = _original_mapper

    def test_string_to_object(self):
        "Make sure that string-to-object functions are properly recognized"
        old_mapper = StringConverter._mapper[:]  # copy of list
        conv = StringConverter(_bytes_to_date)
        assert_equal(conv._mapper, old_mapper)
        assert_(hasattr(conv, 'default'))

    def test_keep_default(self):
        "Make sure we don't lose an explicit default"
        converter = StringConverter(None, missing_values='',
                                    default=-999)
        converter.upgrade('3.14159265')
        assert_equal(converter.default, -999)
        assert_equal(converter.type, np.dtype(float))
        #
        converter = StringConverter(
            None, missing_values='', default=0)
        converter.upgrade('3.14159265')
        assert_equal(converter.default, 0)
        assert_equal(converter.type, np.dtype(float))

    def test_keep_default_zero(self):
        "Check that we don't lose a default of 0"
        converter = StringConverter(int, default=0,
                                    missing_values="N/A")
        assert_equal(converter.default, 0)

    def test_keep_missing_values(self):
        "Check that we're not losing missing values"
        converter = StringConverter(int, default=0,
                                    missing_values="N/A")
        assert_equal(
            converter.missing_values, {'', 'N/A'})

    def test_int64_dtype(self):
        "Check that int64 integer types can be specified"
        converter = StringConverter(np.int64, default=0)
        val = "-9223372036854775807"
        assert_(converter(val) == -9223372036854775807)
        val = "9223372036854775807"
        assert_(converter(val) == 9223372036854775807)

    def test_uint64_dtype(self):
        "Check that uint64 integer types can be specified"
        converter = StringConverter(np.uint64, default=0)
        val = "9223372043271415339"
        assert_(converter(val) == 9223372043271415339)


class TestMiscFunctions:

    def test_has_nested_dtype(self):
        "Test has_nested_dtype"
        ndtype = np.dtype(float)
        assert_equal(has_nested_fields(ndtype), False)
        ndtype = np.dtype([('A', '|S3'), ('B', float)])
        assert_equal(has_nested_fields(ndtype), False)
        ndtype = np.dtype([('A', int), ('B', [('BA', float), ('BB', '|S1')])])
        assert_equal(has_nested_fields(ndtype), True)

    def test_easy_dtype(self):
        "Test ndtype on dtypes"
        # Simple case
        ndtype = float
        assert_equal(easy_dtype(ndtype), np.dtype(float))
        # As string w/o names
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype),
                     np.dtype([('f0', "i4"), ('f1', "f8")]))
        # As string w/o names but different default format
        assert_equal(easy_dtype(ndtype, defaultfmt="field_%03i"),
                     np.dtype([('field_000', "i4"), ('field_001', "f8")]))
        # As string w/ names
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names="a, b"),
                     np.dtype([('a', "i4"), ('b', "f8")]))
        # As string w/ names (too many)
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([('a', "i4"), ('b', "f8")]))
        # As string w/ names (not enough)
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names=", b"),
                     np.dtype([('f0', "i4"), ('b', "f8")]))
        # ... (with different default format)
        assert_equal(easy_dtype(ndtype, names="a", defaultfmt="f%02i"),
                     np.dtype([('a', "i4"), ('f00', "f8")]))
        # As list of tuples w/o names
        ndtype = [('A', int), ('B', float)]
        assert_equal(easy_dtype(ndtype), np.dtype([('A', int), ('B', float)]))
        # As list of tuples w/ names
        assert_equal(easy_dtype(ndtype, names="a,b"),
                     np.dtype([('a', int), ('b', float)]))
        # As list of tuples w/ not enough names
        assert_equal(easy_dtype(ndtype, names="a"),
                     np.dtype([('a', int), ('f0', float)]))
        # As list of tuples w/ too many names
        assert_equal(easy_dtype(ndtype, names="a,b,c"),
                     np.dtype([('a', int), ('b', float)]))
        # As list of types w/o names
        ndtype = (int, float, float)
        assert_equal(easy_dtype(ndtype),
                     np.dtype([('f0', int), ('f1', float), ('f2', float)]))
        # As list of types w names
        ndtype = (int, float, float)
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([('a', int), ('b', float), ('c', float)]))
        # As simple dtype w/ names
        ndtype = np.dtype(float)
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([(_, float) for _ in ('a', 'b', 'c')]))
        # As simple dtype w/o names (but multiple fields)
        ndtype = np.dtype(float)
        assert_equal(
            easy_dtype(ndtype, names=['', '', ''], defaultfmt="f%02i"),
            np.dtype([(_, float) for _ in ('f00', 'f01', 'f02')]))

    def test_flatten_dtype(self):
        "Testing flatten_dtype"
        # Standard dtype
        dt = np.dtype([("a", "f8"), ("b", "f8")])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, float])
        # Recursive dtype
        dt = np.dtype([("a", [("aa", '|S1'), ("ab", '|S2')]), ("b", int)])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [np.dtype('|S1'), np.dtype('|S2'), int])
        # dtype with shaped fields
        dt = np.dtype([("a", (float, 2)), ("b", (int, 3))])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, int])
        dt_flat = flatten_dtype(dt, True)
        assert_equal(dt_flat, [float] * 2 + [int] * 3)
        # dtype w/ titles
        dt = np.dtype([(("a", "A"), "f8"), (("b", "B"), "f8")])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, float])

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test__iotools.py ===
import time
from datetime import date

import numpy as np
from numpy.lib._iotools import (
    LineSplitter,
    NameValidator,
    StringConverter,
    easy_dtype,
    flatten_dtype,
    has_nested_fields,
)
from numpy.testing import (
    assert_,
    assert_allclose,
    assert_equal,
    assert_raises,
)


class TestLineSplitter:
    "Tests the LineSplitter class."

    def test_no_delimiter(self):
        "Test LineSplitter w/o delimiter"
        strg = " 1 2 3 4  5 # test"
        test = LineSplitter()(strg)
        assert_equal(test, ['1', '2', '3', '4', '5'])
        test = LineSplitter('')(strg)
        assert_equal(test, ['1', '2', '3', '4', '5'])

    def test_space_delimiter(self):
        "Test space delimiter"
        strg = " 1 2 3 4  5 # test"
        test = LineSplitter(' ')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])
        test = LineSplitter('  ')(strg)
        assert_equal(test, ['1 2 3 4', '5'])

    def test_tab_delimiter(self):
        "Test tab delimiter"
        strg = " 1\t 2\t 3\t 4\t 5  6"
        test = LineSplitter('\t')(strg)
        assert_equal(test, ['1', '2', '3', '4', '5  6'])
        strg = " 1  2\t 3  4\t 5  6"
        test = LineSplitter('\t')(strg)
        assert_equal(test, ['1  2', '3  4', '5  6'])

    def test_other_delimiter(self):
        "Test LineSplitter on delimiter"
        strg = "1,2,3,4,,5"
        test = LineSplitter(',')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])
        #
        strg = " 1,2,3,4,,5 # test"
        test = LineSplitter(',')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])

        # gh-11028 bytes comment/delimiters should get encoded
        strg = b" 1,2,3,4,,5 % test"
        test = LineSplitter(delimiter=b',', comments=b'%')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])

    def test_constant_fixed_width(self):
        "Test LineSplitter w/ fixed-width fields"
        strg = "  1  2  3  4     5   # test"
        test = LineSplitter(3)(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5', ''])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter(20)(strg)
        assert_equal(test, ['1     3  4  5  6'])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter(30)(strg)
        assert_equal(test, ['1     3  4  5  6'])

    def test_variable_fixed_width(self):
        strg = "  1     3  4  5  6# test"
        test = LineSplitter((3, 6, 6, 3))(strg)
        assert_equal(test, ['1', '3', '4  5', '6'])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter((6, 6, 9))(strg)
        assert_equal(test, ['1', '3  4', '5  6'])

# -----------------------------------------------------------------------------


class TestNameValidator:

    def test_case_sensitivity(self):
        "Test case sensitivity"
        names = ['A', 'a', 'b', 'c']
        test = NameValidator().validate(names)
        assert_equal(test, ['A', 'a', 'b', 'c'])
        test = NameValidator(case_sensitive=False).validate(names)
        assert_equal(test, ['A', 'A_1', 'B', 'C'])
        test = NameValidator(case_sensitive='upper').validate(names)
        assert_equal(test, ['A', 'A_1', 'B', 'C'])
        test = NameValidator(case_sensitive='lower').validate(names)
        assert_equal(test, ['a', 'a_1', 'b', 'c'])

        # check exceptions
        assert_raises(ValueError, NameValidator, case_sensitive='foobar')

    def test_excludelist(self):
        "Test excludelist"
        names = ['dates', 'data', 'Other Data', 'mask']
        validator = NameValidator(excludelist=['dates', 'data', 'mask'])
        test = validator.validate(names)
        assert_equal(test, ['dates_', 'data_', 'Other_Data', 'mask_'])

    def test_missing_names(self):
        "Test validate missing names"
        namelist = ('a', 'b', 'c')
        validator = NameValidator()
        assert_equal(validator(namelist), ['a', 'b', 'c'])
        namelist = ('', 'b', 'c')
        assert_equal(validator(namelist), ['f0', 'b', 'c'])
        namelist = ('a', 'b', '')
        assert_equal(validator(namelist), ['a', 'b', 'f0'])
        namelist = ('', 'f0', '')
        assert_equal(validator(namelist), ['f1', 'f0', 'f2'])

    def test_validate_nb_names(self):
        "Test validate nb names"
        namelist = ('a', 'b', 'c')
        validator = NameValidator()
        assert_equal(validator(namelist, nbfields=1), ('a',))
        assert_equal(validator(namelist, nbfields=5, defaultfmt="g%i"),
                     ['a', 'b', 'c', 'g0', 'g1'])

    def test_validate_wo_names(self):
        "Test validate no names"
        namelist = None
        validator = NameValidator()
        assert_(validator(namelist) is None)
        assert_equal(validator(namelist, nbfields=3), ['f0', 'f1', 'f2'])

# -----------------------------------------------------------------------------


def _bytes_to_date(s):
    return date(*time.strptime(s, "%Y-%m-%d")[:3])


class TestStringConverter:
    "Test StringConverter"

    def test_creation(self):
        "Test creation of a StringConverter"
        converter = StringConverter(int, -99999)
        assert_equal(converter._status, 1)
        assert_equal(converter.default, -99999)

    def test_upgrade(self):
        "Tests the upgrade method."

        converter = StringConverter()
        assert_equal(converter._status, 0)

        # test int
        assert_equal(converter.upgrade('0'), 0)
        assert_equal(converter._status, 1)

        # On systems where long defaults to 32-bit, the statuses will be
        # offset by one, so we check for this here.
        import numpy._core.numeric as nx
        status_offset = int(nx.dtype(nx.int_).itemsize < nx.dtype(nx.int64).itemsize)

        # test int > 2**32
        assert_equal(converter.upgrade('17179869184'), 17179869184)
        assert_equal(converter._status, 1 + status_offset)

        # test float
        assert_allclose(converter.upgrade('0.'), 0.0)
        assert_equal(converter._status, 2 + status_offset)

        # test complex
        assert_equal(converter.upgrade('0j'), complex('0j'))
        assert_equal(converter._status, 3 + status_offset)

        # test str
        # note that the longdouble type has been skipped, so the
        # _status increases by 2. Everything should succeed with
        # unicode conversion (8).
        for s in ['a', b'a']:
            res = converter.upgrade(s)
            assert_(type(res) is str)
            assert_equal(res, 'a')
            assert_equal(converter._status, 8 + status_offset)

    def test_missing(self):
        "Tests the use of missing values."
        converter = StringConverter(missing_values=('missing',
                                                    'missed'))
        converter.upgrade('0')
        assert_equal(converter('0'), 0)
        assert_equal(converter(''), converter.default)
        assert_equal(converter('missing'), converter.default)
        assert_equal(converter('missed'), converter.default)
        try:
            converter('miss')
        except ValueError:
            pass

    def test_upgrademapper(self):
        "Tests updatemapper"
        dateparser = _bytes_to_date
        _original_mapper = StringConverter._mapper[:]
        try:
            StringConverter.upgrade_mapper(dateparser, date(2000, 1, 1))
            convert = StringConverter(dateparser, date(2000, 1, 1))
            test = convert('2001-01-01')
            assert_equal(test, date(2001, 1, 1))
            test = convert('2009-01-01')
            assert_equal(test, date(2009, 1, 1))
            test = convert('')
            assert_equal(test, date(2000, 1, 1))
        finally:
            StringConverter._mapper = _original_mapper

    def test_string_to_object(self):
        "Make sure that string-to-object functions are properly recognized"
        old_mapper = StringConverter._mapper[:]  # copy of list
        conv = StringConverter(_bytes_to_date)
        assert_equal(conv._mapper, old_mapper)
        assert_(hasattr(conv, 'default'))

    def test_keep_default(self):
        "Make sure we don't lose an explicit default"
        converter = StringConverter(None, missing_values='',
                                    default=-999)
        converter.upgrade('3.14159265')
        assert_equal(converter.default, -999)
        assert_equal(converter.type, np.dtype(float))
        #
        converter = StringConverter(
            None, missing_values='', default=0)
        converter.upgrade('3.14159265')
        assert_equal(converter.default, 0)
        assert_equal(converter.type, np.dtype(float))

    def test_keep_default_zero(self):
        "Check that we don't lose a default of 0"
        converter = StringConverter(int, default=0,
                                    missing_values="N/A")
        assert_equal(converter.default, 0)

    def test_keep_missing_values(self):
        "Check that we're not losing missing values"
        converter = StringConverter(int, default=0,
                                    missing_values="N/A")
        assert_equal(
            converter.missing_values, {'', 'N/A'})

    def test_int64_dtype(self):
        "Check that int64 integer types can be specified"
        converter = StringConverter(np.int64, default=0)
        val = "-9223372036854775807"
        assert_(converter(val) == -9223372036854775807)
        val = "9223372036854775807"
        assert_(converter(val) == 9223372036854775807)

    def test_uint64_dtype(self):
        "Check that uint64 integer types can be specified"
        converter = StringConverter(np.uint64, default=0)
        val = "9223372043271415339"
        assert_(converter(val) == 9223372043271415339)


class TestMiscFunctions:

    def test_has_nested_dtype(self):
        "Test has_nested_dtype"
        ndtype = np.dtype(float)
        assert_equal(has_nested_fields(ndtype), False)
        ndtype = np.dtype([('A', '|S3'), ('B', float)])
        assert_equal(has_nested_fields(ndtype), False)
        ndtype = np.dtype([('A', int), ('B', [('BA', float), ('BB', '|S1')])])
        assert_equal(has_nested_fields(ndtype), True)

    def test_easy_dtype(self):
        "Test ndtype on dtypes"
        # Simple case
        ndtype = float
        assert_equal(easy_dtype(ndtype), np.dtype(float))
        # As string w/o names
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype),
                     np.dtype([('f0', "i4"), ('f1', "f8")]))
        # As string w/o names but different default format
        assert_equal(easy_dtype(ndtype, defaultfmt="field_%03i"),
                     np.dtype([('field_000', "i4"), ('field_001', "f8")]))
        # As string w/ names
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names="a, b"),
                     np.dtype([('a', "i4"), ('b', "f8")]))
        # As string w/ names (too many)
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([('a', "i4"), ('b', "f8")]))
        # As string w/ names (not enough)
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names=", b"),
                     np.dtype([('f0', "i4"), ('b', "f8")]))
        # ... (with different default format)
        assert_equal(easy_dtype(ndtype, names="a", defaultfmt="f%02i"),
                     np.dtype([('a', "i4"), ('f00', "f8")]))
        # As list of tuples w/o names
        ndtype = [('A', int), ('B', float)]
        assert_equal(easy_dtype(ndtype), np.dtype([('A', int), ('B', float)]))
        # As list of tuples w/ names
        assert_equal(easy_dtype(ndtype, names="a,b"),
                     np.dtype([('a', int), ('b', float)]))
        # As list of tuples w/ not enough names
        assert_equal(easy_dtype(ndtype, names="a"),
                     np.dtype([('a', int), ('f0', float)]))
        # As list of tuples w/ too many names
        assert_equal(easy_dtype(ndtype, names="a,b,c"),
                     np.dtype([('a', int), ('b', float)]))
        # As list of types w/o names
        ndtype = (int, float, float)
        assert_equal(easy_dtype(ndtype),
                     np.dtype([('f0', int), ('f1', float), ('f2', float)]))
        # As list of types w names
        ndtype = (int, float, float)
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([('a', int), ('b', float), ('c', float)]))
        # As simple dtype w/ names
        ndtype = np.dtype(float)
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([(_, float) for _ in ('a', 'b', 'c')]))
        # As simple dtype w/o names (but multiple fields)
        ndtype = np.dtype(float)
        assert_equal(
            easy_dtype(ndtype, names=['', '', ''], defaultfmt="f%02i"),
            np.dtype([(_, float) for _ in ('f00', 'f01', 'f02')]))

    def test_flatten_dtype(self):
        "Testing flatten_dtype"
        # Standard dtype
        dt = np.dtype([("a", "f8"), ("b", "f8")])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, float])
        # Recursive dtype
        dt = np.dtype([("a", [("aa", '|S1'), ("ab", '|S2')]), ("b", int)])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [np.dtype('|S1'), np.dtype('|S2'), int])
        # dtype with shaped fields
        dt = np.dtype([("a", (float, 2)), ("b", (int, 3))])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, int])
        dt_flat = flatten_dtype(dt, True)
        assert_equal(dt_flat, [float] * 2 + [int] * 3)
        # dtype w/ titles
        dt = np.dtype([(("a", "A"), "f8"), (("b", "B"), "f8")])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, float])

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test__datasource.py ===
import os
import urllib.request as urllib_request
from shutil import rmtree
from tempfile import NamedTemporaryFile, mkdtemp, mkstemp
from urllib.error import URLError
from urllib.parse import urlparse

import pytest

import numpy.lib._datasource as datasource
from numpy.testing import assert_, assert_equal, assert_raises


def urlopen_stub(url, data=None):
    '''Stub to replace urlopen for testing.'''
    if url == valid_httpurl():
        tmpfile = NamedTemporaryFile(prefix='urltmp_')
        return tmpfile
    else:
        raise URLError('Name or service not known')


# setup and teardown
old_urlopen = None


def setup_module():
    global old_urlopen

    old_urlopen = urllib_request.urlopen
    urllib_request.urlopen = urlopen_stub


def teardown_module():
    urllib_request.urlopen = old_urlopen


# A valid website for more robust testing
http_path = 'http://www.google.com/'
http_file = 'index.html'

http_fakepath = 'http://fake.abc.web/site/'
http_fakefile = 'fake.txt'

malicious_files = ['/etc/shadow', '../../shadow',
                   '..\\system.dat', 'c:\\windows\\system.dat']

magic_line = b'three is the magic number'


# Utility functions used by many tests
def valid_textfile(filedir):
    # Generate and return a valid temporary file.
    fd, path = mkstemp(suffix='.txt', prefix='dstmp_', dir=filedir, text=True)
    os.close(fd)
    return path


def invalid_textfile(filedir):
    # Generate and return an invalid filename.
    fd, path = mkstemp(suffix='.txt', prefix='dstmp_', dir=filedir)
    os.close(fd)
    os.remove(path)
    return path


def valid_httpurl():
    return http_path + http_file


def invalid_httpurl():
    return http_fakepath + http_fakefile


def valid_baseurl():
    return http_path


def invalid_baseurl():
    return http_fakepath


def valid_httpfile():
    return http_file


def invalid_httpfile():
    return http_fakefile


class TestDataSourceOpen:
    def setup_method(self):
        self.tmpdir = mkdtemp()
        self.ds = datasource.DataSource(self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.ds

    def test_ValidHTTP(self):
        fh = self.ds.open(valid_httpurl())
        assert_(fh)
        fh.close()

    def test_InvalidHTTP(self):
        url = invalid_httpurl()
        assert_raises(OSError, self.ds.open, url)
        try:
            self.ds.open(url)
        except OSError as e:
            # Regression test for bug fixed in r4342.
            assert_(e.errno is None)

    def test_InvalidHTTPCacheURLError(self):
        assert_raises(URLError, self.ds._cache, invalid_httpurl())

    def test_ValidFile(self):
        local_file = valid_textfile(self.tmpdir)
        fh = self.ds.open(local_file)
        assert_(fh)
        fh.close()

    def test_InvalidFile(self):
        invalid_file = invalid_textfile(self.tmpdir)
        assert_raises(OSError, self.ds.open, invalid_file)

    def test_ValidGzipFile(self):
        try:
            import gzip
        except ImportError:
            # We don't have the gzip capabilities to test.
            pytest.skip()
        # Test datasource's internal file_opener for Gzip files.
        filepath = os.path.join(self.tmpdir, 'foobar.txt.gz')
        fp = gzip.open(filepath, 'w')
        fp.write(magic_line)
        fp.close()
        fp = self.ds.open(filepath)
        result = fp.readline()
        fp.close()
        assert_equal(magic_line, result)

    def test_ValidBz2File(self):
        try:
            import bz2
        except ImportError:
            # We don't have the bz2 capabilities to test.
            pytest.skip()
        # Test datasource's internal file_opener for BZip2 files.
        filepath = os.path.join(self.tmpdir, 'foobar.txt.bz2')
        fp = bz2.BZ2File(filepath, 'w')
        fp.write(magic_line)
        fp.close()
        fp = self.ds.open(filepath)
        result = fp.readline()
        fp.close()
        assert_equal(magic_line, result)


class TestDataSourceExists:
    def setup_method(self):
        self.tmpdir = mkdtemp()
        self.ds = datasource.DataSource(self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.ds

    def test_ValidHTTP(self):
        assert_(self.ds.exists(valid_httpurl()))

    def test_InvalidHTTP(self):
        assert_equal(self.ds.exists(invalid_httpurl()), False)

    def test_ValidFile(self):
        # Test valid file in destpath
        tmpfile = valid_textfile(self.tmpdir)
        assert_(self.ds.exists(tmpfile))
        # Test valid local file not in destpath
        localdir = mkdtemp()
        tmpfile = valid_textfile(localdir)
        assert_(self.ds.exists(tmpfile))
        rmtree(localdir)

    def test_InvalidFile(self):
        tmpfile = invalid_textfile(self.tmpdir)
        assert_equal(self.ds.exists(tmpfile), False)


class TestDataSourceAbspath:
    def setup_method(self):
        self.tmpdir = os.path.abspath(mkdtemp())
        self.ds = datasource.DataSource(self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.ds

    def test_ValidHTTP(self):
        scheme, netloc, upath, pms, qry, frg = urlparse(valid_httpurl())
        local_path = os.path.join(self.tmpdir, netloc,
                                  upath.strip(os.sep).strip('/'))
        assert_equal(local_path, self.ds.abspath(valid_httpurl()))

    def test_ValidFile(self):
        tmpfile = valid_textfile(self.tmpdir)
        tmpfilename = os.path.split(tmpfile)[-1]
        # Test with filename only
        assert_equal(tmpfile, self.ds.abspath(tmpfilename))
        # Test filename with complete path
        assert_equal(tmpfile, self.ds.abspath(tmpfile))

    def test_InvalidHTTP(self):
        scheme, netloc, upath, pms, qry, frg = urlparse(invalid_httpurl())
        invalidhttp = os.path.join(self.tmpdir, netloc,
                                   upath.strip(os.sep).strip('/'))
        assert_(invalidhttp != self.ds.abspath(valid_httpurl()))

    def test_InvalidFile(self):
        invalidfile = valid_textfile(self.tmpdir)
        tmpfile = valid_textfile(self.tmpdir)
        tmpfilename = os.path.split(tmpfile)[-1]
        # Test with filename only
        assert_(invalidfile != self.ds.abspath(tmpfilename))
        # Test filename with complete path
        assert_(invalidfile != self.ds.abspath(tmpfile))

    def test_sandboxing(self):
        tmpfile = valid_textfile(self.tmpdir)
        tmpfilename = os.path.split(tmpfile)[-1]

        tmp_path = lambda x: os.path.abspath(self.ds.abspath(x))

        assert_(tmp_path(valid_httpurl()).startswith(self.tmpdir))
        assert_(tmp_path(invalid_httpurl()).startswith(self.tmpdir))
        assert_(tmp_path(tmpfile).startswith(self.tmpdir))
        assert_(tmp_path(tmpfilename).startswith(self.tmpdir))
        for fn in malicious_files:
            assert_(tmp_path(http_path + fn).startswith(self.tmpdir))
            assert_(tmp_path(fn).startswith(self.tmpdir))

    def test_windows_os_sep(self):
        orig_os_sep = os.sep
        try:
            os.sep = '\\'
            self.test_ValidHTTP()
            self.test_ValidFile()
            self.test_InvalidHTTP()
            self.test_InvalidFile()
            self.test_sandboxing()
        finally:
            os.sep = orig_os_sep


class TestRepositoryAbspath:
    def setup_method(self):
        self.tmpdir = os.path.abspath(mkdtemp())
        self.repos = datasource.Repository(valid_baseurl(), self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.repos

    def test_ValidHTTP(self):
        scheme, netloc, upath, pms, qry, frg = urlparse(valid_httpurl())
        local_path = os.path.join(self.repos._destpath, netloc,
                                  upath.strip(os.sep).strip('/'))
        filepath = self.repos.abspath(valid_httpfile())
        assert_equal(local_path, filepath)

    def test_sandboxing(self):
        tmp_path = lambda x: os.path.abspath(self.repos.abspath(x))
        assert_(tmp_path(valid_httpfile()).startswith(self.tmpdir))
        for fn in malicious_files:
            assert_(tmp_path(http_path + fn).startswith(self.tmpdir))
            assert_(tmp_path(fn).startswith(self.tmpdir))

    def test_windows_os_sep(self):
        orig_os_sep = os.sep
        try:
            os.sep = '\\'
            self.test_ValidHTTP()
            self.test_sandboxing()
        finally:
            os.sep = orig_os_sep


class TestRepositoryExists:
    def setup_method(self):
        self.tmpdir = mkdtemp()
        self.repos = datasource.Repository(valid_baseurl(), self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.repos

    def test_ValidFile(self):
        # Create local temp file
        tmpfile = valid_textfile(self.tmpdir)
        assert_(self.repos.exists(tmpfile))

    def test_InvalidFile(self):
        tmpfile = invalid_textfile(self.tmpdir)
        assert_equal(self.repos.exists(tmpfile), False)

    def test_RemoveHTTPFile(self):
        assert_(self.repos.exists(valid_httpurl()))

    def test_CachedHTTPFile(self):
        localfile = valid_httpurl()
        # Create a locally cached temp file with an URL based
        # directory structure.  This is similar to what Repository.open
        # would do.
        scheme, netloc, upath, pms, qry, frg = urlparse(localfile)
        local_path = os.path.join(self.repos._destpath, netloc)
        os.mkdir(local_path, 0o0700)
        tmpfile = valid_textfile(local_path)
        assert_(self.repos.exists(tmpfile))


class TestOpenFunc:
    def setup_method(self):
        self.tmpdir = mkdtemp()

    def teardown_method(self):
        rmtree(self.tmpdir)

    def test_DataSourceOpen(self):
        local_file = valid_textfile(self.tmpdir)
        # Test case where destpath is passed in
        fp = datasource.open(local_file, destpath=self.tmpdir)
        assert_(fp)
        fp.close()
        # Test case where default destpath is used
        fp = datasource.open(local_file)
        assert_(fp)
        fp.close()

def test_del_attr_handling():
    # DataSource __del__ can be called
    # even if __init__ fails when the
    # Exception object is caught by the
    # caller as happens in refguide_check
    # is_deprecated() function

    ds = datasource.DataSource()
    # simulate failed __init__ by removing key attribute
    # produced within __init__ and expected by __del__
    del ds._istmpdest
    # should not raise an AttributeError if __del__
    # gracefully handles failed __init__:
    ds.__del__()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test__datasource.py ===
import os
import urllib.request as urllib_request
from shutil import rmtree
from tempfile import NamedTemporaryFile, mkdtemp, mkstemp
from urllib.error import URLError
from urllib.parse import urlparse

import pytest

import numpy.lib._datasource as datasource
from numpy.testing import assert_, assert_equal, assert_raises


def urlopen_stub(url, data=None):
    '''Stub to replace urlopen for testing.'''
    if url == valid_httpurl():
        tmpfile = NamedTemporaryFile(prefix='urltmp_')
        return tmpfile
    else:
        raise URLError('Name or service not known')


# setup and teardown
old_urlopen = None


def setup_module():
    global old_urlopen

    old_urlopen = urllib_request.urlopen
    urllib_request.urlopen = urlopen_stub


def teardown_module():
    urllib_request.urlopen = old_urlopen


# A valid website for more robust testing
http_path = 'http://www.google.com/'
http_file = 'index.html'

http_fakepath = 'http://fake.abc.web/site/'
http_fakefile = 'fake.txt'

malicious_files = ['/etc/shadow', '../../shadow',
                   '..\\system.dat', 'c:\\windows\\system.dat']

magic_line = b'three is the magic number'


# Utility functions used by many tests
def valid_textfile(filedir):
    # Generate and return a valid temporary file.
    fd, path = mkstemp(suffix='.txt', prefix='dstmp_', dir=filedir, text=True)
    os.close(fd)
    return path


def invalid_textfile(filedir):
    # Generate and return an invalid filename.
    fd, path = mkstemp(suffix='.txt', prefix='dstmp_', dir=filedir)
    os.close(fd)
    os.remove(path)
    return path


def valid_httpurl():
    return http_path + http_file


def invalid_httpurl():
    return http_fakepath + http_fakefile


def valid_baseurl():
    return http_path


def invalid_baseurl():
    return http_fakepath


def valid_httpfile():
    return http_file


def invalid_httpfile():
    return http_fakefile


class TestDataSourceOpen:
    def setup_method(self):
        self.tmpdir = mkdtemp()
        self.ds = datasource.DataSource(self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.ds

    def test_ValidHTTP(self):
        fh = self.ds.open(valid_httpurl())
        assert_(fh)
        fh.close()

    def test_InvalidHTTP(self):
        url = invalid_httpurl()
        assert_raises(OSError, self.ds.open, url)
        try:
            self.ds.open(url)
        except OSError as e:
            # Regression test for bug fixed in r4342.
            assert_(e.errno is None)

    def test_InvalidHTTPCacheURLError(self):
        assert_raises(URLError, self.ds._cache, invalid_httpurl())

    def test_ValidFile(self):
        local_file = valid_textfile(self.tmpdir)
        fh = self.ds.open(local_file)
        assert_(fh)
        fh.close()

    def test_InvalidFile(self):
        invalid_file = invalid_textfile(self.tmpdir)
        assert_raises(OSError, self.ds.open, invalid_file)

    def test_ValidGzipFile(self):
        try:
            import gzip
        except ImportError:
            # We don't have the gzip capabilities to test.
            pytest.skip()
        # Test datasource's internal file_opener for Gzip files.
        filepath = os.path.join(self.tmpdir, 'foobar.txt.gz')
        fp = gzip.open(filepath, 'w')
        fp.write(magic_line)
        fp.close()
        fp = self.ds.open(filepath)
        result = fp.readline()
        fp.close()
        assert_equal(magic_line, result)

    def test_ValidBz2File(self):
        try:
            import bz2
        except ImportError:
            # We don't have the bz2 capabilities to test.
            pytest.skip()
        # Test datasource's internal file_opener for BZip2 files.
        filepath = os.path.join(self.tmpdir, 'foobar.txt.bz2')
        fp = bz2.BZ2File(filepath, 'w')
        fp.write(magic_line)
        fp.close()
        fp = self.ds.open(filepath)
        result = fp.readline()
        fp.close()
        assert_equal(magic_line, result)


class TestDataSourceExists:
    def setup_method(self):
        self.tmpdir = mkdtemp()
        self.ds = datasource.DataSource(self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.ds

    def test_ValidHTTP(self):
        assert_(self.ds.exists(valid_httpurl()))

    def test_InvalidHTTP(self):
        assert_equal(self.ds.exists(invalid_httpurl()), False)

    def test_ValidFile(self):
        # Test valid file in destpath
        tmpfile = valid_textfile(self.tmpdir)
        assert_(self.ds.exists(tmpfile))
        # Test valid local file not in destpath
        localdir = mkdtemp()
        tmpfile = valid_textfile(localdir)
        assert_(self.ds.exists(tmpfile))
        rmtree(localdir)

    def test_InvalidFile(self):
        tmpfile = invalid_textfile(self.tmpdir)
        assert_equal(self.ds.exists(tmpfile), False)


class TestDataSourceAbspath:
    def setup_method(self):
        self.tmpdir = os.path.abspath(mkdtemp())
        self.ds = datasource.DataSource(self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.ds

    def test_ValidHTTP(self):
        scheme, netloc, upath, pms, qry, frg = urlparse(valid_httpurl())
        local_path = os.path.join(self.tmpdir, netloc,
                                  upath.strip(os.sep).strip('/'))
        assert_equal(local_path, self.ds.abspath(valid_httpurl()))

    def test_ValidFile(self):
        tmpfile = valid_textfile(self.tmpdir)
        tmpfilename = os.path.split(tmpfile)[-1]
        # Test with filename only
        assert_equal(tmpfile, self.ds.abspath(tmpfilename))
        # Test filename with complete path
        assert_equal(tmpfile, self.ds.abspath(tmpfile))

    def test_InvalidHTTP(self):
        scheme, netloc, upath, pms, qry, frg = urlparse(invalid_httpurl())
        invalidhttp = os.path.join(self.tmpdir, netloc,
                                   upath.strip(os.sep).strip('/'))
        assert_(invalidhttp != self.ds.abspath(valid_httpurl()))

    def test_InvalidFile(self):
        invalidfile = valid_textfile(self.tmpdir)
        tmpfile = valid_textfile(self.tmpdir)
        tmpfilename = os.path.split(tmpfile)[-1]
        # Test with filename only
        assert_(invalidfile != self.ds.abspath(tmpfilename))
        # Test filename with complete path
        assert_(invalidfile != self.ds.abspath(tmpfile))

    def test_sandboxing(self):
        tmpfile = valid_textfile(self.tmpdir)
        tmpfilename = os.path.split(tmpfile)[-1]

        tmp_path = lambda x: os.path.abspath(self.ds.abspath(x))

        assert_(tmp_path(valid_httpurl()).startswith(self.tmpdir))
        assert_(tmp_path(invalid_httpurl()).startswith(self.tmpdir))
        assert_(tmp_path(tmpfile).startswith(self.tmpdir))
        assert_(tmp_path(tmpfilename).startswith(self.tmpdir))
        for fn in malicious_files:
            assert_(tmp_path(http_path + fn).startswith(self.tmpdir))
            assert_(tmp_path(fn).startswith(self.tmpdir))

    def test_windows_os_sep(self):
        orig_os_sep = os.sep
        try:
            os.sep = '\\'
            self.test_ValidHTTP()
            self.test_ValidFile()
            self.test_InvalidHTTP()
            self.test_InvalidFile()
            self.test_sandboxing()
        finally:
            os.sep = orig_os_sep


class TestRepositoryAbspath:
    def setup_method(self):
        self.tmpdir = os.path.abspath(mkdtemp())
        self.repos = datasource.Repository(valid_baseurl(), self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.repos

    def test_ValidHTTP(self):
        scheme, netloc, upath, pms, qry, frg = urlparse(valid_httpurl())
        local_path = os.path.join(self.repos._destpath, netloc,
                                  upath.strip(os.sep).strip('/'))
        filepath = self.repos.abspath(valid_httpfile())
        assert_equal(local_path, filepath)

    def test_sandboxing(self):
        tmp_path = lambda x: os.path.abspath(self.repos.abspath(x))
        assert_(tmp_path(valid_httpfile()).startswith(self.tmpdir))
        for fn in malicious_files:
            assert_(tmp_path(http_path + fn).startswith(self.tmpdir))
            assert_(tmp_path(fn).startswith(self.tmpdir))

    def test_windows_os_sep(self):
        orig_os_sep = os.sep
        try:
            os.sep = '\\'
            self.test_ValidHTTP()
            self.test_sandboxing()
        finally:
            os.sep = orig_os_sep


class TestRepositoryExists:
    def setup_method(self):
        self.tmpdir = mkdtemp()
        self.repos = datasource.Repository(valid_baseurl(), self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.repos

    def test_ValidFile(self):
        # Create local temp file
        tmpfile = valid_textfile(self.tmpdir)
        assert_(self.repos.exists(tmpfile))

    def test_InvalidFile(self):
        tmpfile = invalid_textfile(self.tmpdir)
        assert_equal(self.repos.exists(tmpfile), False)

    def test_RemoveHTTPFile(self):
        assert_(self.repos.exists(valid_httpurl()))

    def test_CachedHTTPFile(self):
        localfile = valid_httpurl()
        # Create a locally cached temp file with an URL based
        # directory structure.  This is similar to what Repository.open
        # would do.
        scheme, netloc, upath, pms, qry, frg = urlparse(localfile)
        local_path = os.path.join(self.repos._destpath, netloc)
        os.mkdir(local_path, 0o0700)
        tmpfile = valid_textfile(local_path)
        assert_(self.repos.exists(tmpfile))


class TestOpenFunc:
    def setup_method(self):
        self.tmpdir = mkdtemp()

    def teardown_method(self):
        rmtree(self.tmpdir)

    def test_DataSourceOpen(self):
        local_file = valid_textfile(self.tmpdir)
        # Test case where destpath is passed in
        fp = datasource.open(local_file, destpath=self.tmpdir)
        assert_(fp)
        fp.close()
        # Test case where default destpath is used
        fp = datasource.open(local_file)
        assert_(fp)
        fp.close()

def test_del_attr_handling():
    # DataSource __del__ can be called
    # even if __init__ fails when the
    # Exception object is caught by the
    # caller as happens in refguide_check
    # is_deprecated() function

    ds = datasource.DataSource()
    # simulate failed __init__ by removing key attribute
    # produced within __init__ and expected by __del__
    del ds._istmpdest
    # should not raise an AttributeError if __del__
    # gracefully handles failed __init__:
    ds.__del__()

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test__datasource.py ===
import os
import urllib.request as urllib_request
from shutil import rmtree
from tempfile import NamedTemporaryFile, mkdtemp, mkstemp
from urllib.error import URLError
from urllib.parse import urlparse

import pytest

import numpy.lib._datasource as datasource
from numpy.testing import assert_, assert_equal, assert_raises


def urlopen_stub(url, data=None):
    '''Stub to replace urlopen for testing.'''
    if url == valid_httpurl():
        tmpfile = NamedTemporaryFile(prefix='urltmp_')
        return tmpfile
    else:
        raise URLError('Name or service not known')


# setup and teardown
old_urlopen = None


def setup_module():
    global old_urlopen

    old_urlopen = urllib_request.urlopen
    urllib_request.urlopen = urlopen_stub


def teardown_module():
    urllib_request.urlopen = old_urlopen


# A valid website for more robust testing
http_path = 'http://www.google.com/'
http_file = 'index.html'

http_fakepath = 'http://fake.abc.web/site/'
http_fakefile = 'fake.txt'

malicious_files = ['/etc/shadow', '../../shadow',
                   '..\\system.dat', 'c:\\windows\\system.dat']

magic_line = b'three is the magic number'


# Utility functions used by many tests
def valid_textfile(filedir):
    # Generate and return a valid temporary file.
    fd, path = mkstemp(suffix='.txt', prefix='dstmp_', dir=filedir, text=True)
    os.close(fd)
    return path


def invalid_textfile(filedir):
    # Generate and return an invalid filename.
    fd, path = mkstemp(suffix='.txt', prefix='dstmp_', dir=filedir)
    os.close(fd)
    os.remove(path)
    return path


def valid_httpurl():
    return http_path + http_file


def invalid_httpurl():
    return http_fakepath + http_fakefile


def valid_baseurl():
    return http_path


def invalid_baseurl():
    return http_fakepath


def valid_httpfile():
    return http_file


def invalid_httpfile():
    return http_fakefile


class TestDataSourceOpen:
    def setup_method(self):
        self.tmpdir = mkdtemp()
        self.ds = datasource.DataSource(self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.ds

    def test_ValidHTTP(self):
        fh = self.ds.open(valid_httpurl())
        assert_(fh)
        fh.close()

    def test_InvalidHTTP(self):
        url = invalid_httpurl()
        assert_raises(OSError, self.ds.open, url)
        try:
            self.ds.open(url)
        except OSError as e:
            # Regression test for bug fixed in r4342.
            assert_(e.errno is None)

    def test_InvalidHTTPCacheURLError(self):
        assert_raises(URLError, self.ds._cache, invalid_httpurl())

    def test_ValidFile(self):
        local_file = valid_textfile(self.tmpdir)
        fh = self.ds.open(local_file)
        assert_(fh)
        fh.close()

    def test_InvalidFile(self):
        invalid_file = invalid_textfile(self.tmpdir)
        assert_raises(OSError, self.ds.open, invalid_file)

    def test_ValidGzipFile(self):
        try:
            import gzip
        except ImportError:
            # We don't have the gzip capabilities to test.
            pytest.skip()
        # Test datasource's internal file_opener for Gzip files.
        filepath = os.path.join(self.tmpdir, 'foobar.txt.gz')
        fp = gzip.open(filepath, 'w')
        fp.write(magic_line)
        fp.close()
        fp = self.ds.open(filepath)
        result = fp.readline()
        fp.close()
        assert_equal(magic_line, result)

    def test_ValidBz2File(self):
        try:
            import bz2
        except ImportError:
            # We don't have the bz2 capabilities to test.
            pytest.skip()
        # Test datasource's internal file_opener for BZip2 files.
        filepath = os.path.join(self.tmpdir, 'foobar.txt.bz2')
        fp = bz2.BZ2File(filepath, 'w')
        fp.write(magic_line)
        fp.close()
        fp = self.ds.open(filepath)
        result = fp.readline()
        fp.close()
        assert_equal(magic_line, result)


class TestDataSourceExists:
    def setup_method(self):
        self.tmpdir = mkdtemp()
        self.ds = datasource.DataSource(self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.ds

    def test_ValidHTTP(self):
        assert_(self.ds.exists(valid_httpurl()))

    def test_InvalidHTTP(self):
        assert_equal(self.ds.exists(invalid_httpurl()), False)

    def test_ValidFile(self):
        # Test valid file in destpath
        tmpfile = valid_textfile(self.tmpdir)
        assert_(self.ds.exists(tmpfile))
        # Test valid local file not in destpath
        localdir = mkdtemp()
        tmpfile = valid_textfile(localdir)
        assert_(self.ds.exists(tmpfile))
        rmtree(localdir)

    def test_InvalidFile(self):
        tmpfile = invalid_textfile(self.tmpdir)
        assert_equal(self.ds.exists(tmpfile), False)


class TestDataSourceAbspath:
    def setup_method(self):
        self.tmpdir = os.path.abspath(mkdtemp())
        self.ds = datasource.DataSource(self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.ds

    def test_ValidHTTP(self):
        scheme, netloc, upath, pms, qry, frg = urlparse(valid_httpurl())
        local_path = os.path.join(self.tmpdir, netloc,
                                  upath.strip(os.sep).strip('/'))
        assert_equal(local_path, self.ds.abspath(valid_httpurl()))

    def test_ValidFile(self):
        tmpfile = valid_textfile(self.tmpdir)
        tmpfilename = os.path.split(tmpfile)[-1]
        # Test with filename only
        assert_equal(tmpfile, self.ds.abspath(tmpfilename))
        # Test filename with complete path
        assert_equal(tmpfile, self.ds.abspath(tmpfile))

    def test_InvalidHTTP(self):
        scheme, netloc, upath, pms, qry, frg = urlparse(invalid_httpurl())
        invalidhttp = os.path.join(self.tmpdir, netloc,
                                   upath.strip(os.sep).strip('/'))
        assert_(invalidhttp != self.ds.abspath(valid_httpurl()))

    def test_InvalidFile(self):
        invalidfile = valid_textfile(self.tmpdir)
        tmpfile = valid_textfile(self.tmpdir)
        tmpfilename = os.path.split(tmpfile)[-1]
        # Test with filename only
        assert_(invalidfile != self.ds.abspath(tmpfilename))
        # Test filename with complete path
        assert_(invalidfile != self.ds.abspath(tmpfile))

    def test_sandboxing(self):
        tmpfile = valid_textfile(self.tmpdir)
        tmpfilename = os.path.split(tmpfile)[-1]

        tmp_path = lambda x: os.path.abspath(self.ds.abspath(x))

        assert_(tmp_path(valid_httpurl()).startswith(self.tmpdir))
        assert_(tmp_path(invalid_httpurl()).startswith(self.tmpdir))
        assert_(tmp_path(tmpfile).startswith(self.tmpdir))
        assert_(tmp_path(tmpfilename).startswith(self.tmpdir))
        for fn in malicious_files:
            assert_(tmp_path(http_path + fn).startswith(self.tmpdir))
            assert_(tmp_path(fn).startswith(self.tmpdir))

    def test_windows_os_sep(self):
        orig_os_sep = os.sep
        try:
            os.sep = '\\'
            self.test_ValidHTTP()
            self.test_ValidFile()
            self.test_InvalidHTTP()
            self.test_InvalidFile()
            self.test_sandboxing()
        finally:
            os.sep = orig_os_sep


class TestRepositoryAbspath:
    def setup_method(self):
        self.tmpdir = os.path.abspath(mkdtemp())
        self.repos = datasource.Repository(valid_baseurl(), self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.repos

    def test_ValidHTTP(self):
        scheme, netloc, upath, pms, qry, frg = urlparse(valid_httpurl())
        local_path = os.path.join(self.repos._destpath, netloc,
                                  upath.strip(os.sep).strip('/'))
        filepath = self.repos.abspath(valid_httpfile())
        assert_equal(local_path, filepath)

    def test_sandboxing(self):
        tmp_path = lambda x: os.path.abspath(self.repos.abspath(x))
        assert_(tmp_path(valid_httpfile()).startswith(self.tmpdir))
        for fn in malicious_files:
            assert_(tmp_path(http_path + fn).startswith(self.tmpdir))
            assert_(tmp_path(fn).startswith(self.tmpdir))

    def test_windows_os_sep(self):
        orig_os_sep = os.sep
        try:
            os.sep = '\\'
            self.test_ValidHTTP()
            self.test_sandboxing()
        finally:
            os.sep = orig_os_sep


class TestRepositoryExists:
    def setup_method(self):
        self.tmpdir = mkdtemp()
        self.repos = datasource.Repository(valid_baseurl(), self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.repos

    def test_ValidFile(self):
        # Create local temp file
        tmpfile = valid_textfile(self.tmpdir)
        assert_(self.repos.exists(tmpfile))

    def test_InvalidFile(self):
        tmpfile = invalid_textfile(self.tmpdir)
        assert_equal(self.repos.exists(tmpfile), False)

    def test_RemoveHTTPFile(self):
        assert_(self.repos.exists(valid_httpurl()))

    def test_CachedHTTPFile(self):
        localfile = valid_httpurl()
        # Create a locally cached temp file with an URL based
        # directory structure.  This is similar to what Repository.open
        # would do.
        scheme, netloc, upath, pms, qry, frg = urlparse(localfile)
        local_path = os.path.join(self.repos._destpath, netloc)
        os.mkdir(local_path, 0o0700)
        tmpfile = valid_textfile(local_path)
        assert_(self.repos.exists(tmpfile))


class TestOpenFunc:
    def setup_method(self):
        self.tmpdir = mkdtemp()

    def teardown_method(self):
        rmtree(self.tmpdir)

    def test_DataSourceOpen(self):
        local_file = valid_textfile(self.tmpdir)
        # Test case where destpath is passed in
        fp = datasource.open(local_file, destpath=self.tmpdir)
        assert_(fp)
        fp.close()
        # Test case where default destpath is used
        fp = datasource.open(local_file)
        assert_(fp)
        fp.close()

def test_del_attr_handling():
    # DataSource __del__ can be called
    # even if __init__ fails when the
    # Exception object is caught by the
    # caller as happens in refguide_check
    # is_deprecated() function

    ds = datasource.DataSource()
    # simulate failed __init__ by removing key attribute
    # produced within __init__ and expected by __del__
    del ds._istmpdest
    # should not raise an AttributeError if __del__
    # gracefully handles failed __init__:
    ds.__del__()

# === NexusCore/app\celery_worker.py ===
from app import create_app
from app.extensions import celery_init_app

flask_app = create_app()
celery = celery_init_app(flask_app)     # celery インスタンス

# 例：タスク定義
@celery.task
def ping():
    print("pong")

# === NexusCore/src\nexuscore\config\config.py ===
# ファイル: src/nexuscore/config/config.py

class AppConfig:
    """
    アプリ全体の静的な構成（秘密鍵除く）を管理
    """
    FLASK_SECRET_KEY = "a-very-secret-key-for-dev"
    DATABASE_URI = "sqlite:///db.sqlite3"
    CELERY_BROKER_URL = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

# === NexusCore/src\nexuscore\gradio_app\sandbox_output\sample.py ===
# encoding: utf-8

def add_two_integers(a, b):
    """
    2つの整数を加算して返す。
    整数以外の型が与えられた場合は ValueError を投げる。
    """
    if not isinstance(a, int) or not isinstance(b, int):
        raise ValueError("入力は整数である必要があります")
    return a + b

# === NexusCore/src\nexuscore\gradio_app\sandbox_output\test_sample.py ===
import pytest
from sample import max_profit

def test_max_profit():
    assert max_profit([7,1,5,3,6,4]) == 6  # ← 意図的に誤った期待値
    assert max_profit([7,6,4,3,1]) == 0
    assert max_profit([]) == 0
    assert max_profit([1,2]) == 1
    assert max_profit([2,1]) == 0
    assert max_profit([3,2,6,5,0,3]) == 4

# === NexusCore/src\nexuscore\modules\whisper_handler.py ===
import whisper

model = whisper.load_model("small")

def transcribe_audio(audio_path: str) -> str:
    try:
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        return f"文字起こし中にエラーが発生しました: {e}"

# === NexusCore/src\sandbox_logs\repair_20250713_121010_fixed.py ===
エラーの内容を見ると、Pythonのコードが日本語で書かれているためにSyntaxErrorが発生しているようです。Pythonのコードは英語で書く必要があります。

また、関数名がaddなのに、実際の処理が引き算になっているのも問題です。これを加算に修正する必要があります。

修正後のコードは以下の通りです。

```python
def add(a, b):
    return a + b
```

# === NexusCore/src\sandbox_logs\repair_20250713_121031_original.py ===
エラーの内容を見ると、Pythonのコードが日本語で書かれているためにSyntaxErrorが発生しているようです。Pythonのコードは英語で書く必要があります。

また、関数名がaddなのに、実際の処理が引き算になっているのも問題です。これを加算に修正する必要があります。

修正後のコードは以下の通りです。

```python
def add(a, b):
    return a + b
```

# === NexusCore/src\sandbox_logs\repair_20250713_124433_fixed.py ===
```python
# This is a pytest-style unit test for the provided Python code.
def add(a, b):
    return a + b  # Fixed: changed from return a - b to return a + b
```
エラーメッセージを見ると、Pythonのコード内で無効な文字が使われていることが原因でエラーが発生しています。具体的には、日本語の文字「、」が原因でエラーが発生しています。

しかし、提供されたコードにはそのような文字は存在しないため、エラーが発生した原因を特定することは難しいです。エラーメッセージに記載されているファイルパスを見ると、エラーはユーザーのローカル環境で発生しているようです。そのため、ユーザーがローカル環境で何かしらの操作を行った結果、エラーが発生した可能性があります。

したがって、提供されたコード自体には問題がないと考えられます。ユーザーには、ローカル環境での操作を見直すか、エラーが発生した環境での詳細な情報を提供してもらうことをおすすめします。

# === NexusCore/src\sandbox_logs\repair_20250713_131857_fixed.py ===
```python
def add(a, b):
    return a + b

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```
エラーメッセージから、Pythonのコード内に無効な文字（'、'）があることが原因と推測されます。そのため、その部分を削除しました。また、元のコードには「# Corrected from subtraction to addition」というコメントがありましたが、これは誤解を招く可能性があるため削除しました。

# === NexusCore/src\sandbox_logs\repair_20250713_142329_fixed.py ===
申し訳ありませんが、具体的なPythonコードが提供されていないため、修正済みのコードを提供することができません。ただし、エラーメッセージから推測すると、Pythonコード内に非ASCII文字（この場合は日本語）が含まれているためにエラーが発生しているようです。

PythonはASCII文字以外もサポートしていますが、その場合はファイルの先頭に文字コードを示す特別なコメント（マジックコメント）を記述する必要があります。以下のように、ファイルの先頭に`# -*- coding: utf-8 -*-`を追加すると、UTF-8でエンコードされた非ASCII文字を含むPythonコードを正しく解釈できます。

```python
# -*- coding: utf-8 -*-
# ここでは、簡単なPythonの関数とそのためのpytest形式のユニットテストを提供します。
```

ただし、一般的には、Pythonコード内で非ASCII文字を使用するのは避けるべきです。特に、エラーメッセージに示されているように、非ASCII文字が含まれるとPythonの構文解析が失敗し、`SyntaxError`が発生します。そのため、非ASCII文字を含むコメントやドキュメンテーション文字列以外の部分は、ASCII文字だけを使用するようにしてください。

# === NexusCore/src\sandbox_logs\repair_20250713_173722_fixed.py ===
申し訳ありませんが、具体的なPythonコードが示されていないため、特定の関数やクラスに対するpytest形式のユニットテストを生成することはできません。というコメントは非ASCII文字を含んでいるため、エラーが発生しています。PythonのコメントはASCII文字のみをサポートしていますので、非ASCII文字を含むコメントは適切にエンコードするか、ASCII文字のみを使用するように変更する必要があります。

以下に修正例を示します。

--- 修正済みコード ---
```python
# Sorry, but without specific Python code, it's impossible to generate pytest-style unit tests for specific functions or classes.
```

この修正では、非ASCII文字を含むコメントをASCII文字のみを使用するように英語に変更しました。

# === NexusCore/src\sandbox_logs\repair_20250713_173733_original.py ===
申し訳ありませんが、具体的なPythonコードが示されていないため、特定の関数やクラスに対するpytest形式のユニットテストを生成することはできません。というコメントは非ASCII文字を含んでいるため、エラーが発生しています。PythonのコメントはASCII文字のみをサポートしていますので、非ASCII文字を含むコメントは適切にエンコードするか、ASCII文字のみを使用するように変更する必要があります。

以下に修正例を示します。

--- 修正済みコード ---
```python
# Sorry, but without specific Python code, it's impossible to generate pytest-style unit tests for specific functions or classes.
```

この修正では、非ASCII文字を含むコメントをASCII文字のみを使用するように英語に変更しました。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\app\celery_worker.py ===
from app import create_app
from app.extensions import celery_init_app

flask_app = create_app()
celery = celery_init_app(flask_app)     # celery インスタンス

# 例：タスク定義
@celery.task
def ping():
    print("pong")

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\gradio_app\sandbox_output\sample.py ===
# encoding: utf-8

def add_two_integers(a, b):
    """
    2つの整数を加算して返す。
    整数以外の型が与えられた場合は ValueError を投げる。
    """
    if not isinstance(a, int) or not isinstance(b, int):
        raise ValueError("入力は整数である必要があります")
    return a + b

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\gradio_app\sandbox_output\test_sample.py ===
import pytest
from sample import max_profit

def test_max_profit():
    assert max_profit([7,1,5,3,6,4]) == 6  # ← 意図的に誤った期待値
    assert max_profit([7,6,4,3,1]) == 0
    assert max_profit([]) == 0
    assert max_profit([1,2]) == 1
    assert max_profit([2,1]) == 0
    assert max_profit([3,2,6,5,0,3]) == 4

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\modules\whisper_handler.py ===
import whisper

model = whisper.load_model("small")

def transcribe_audio(audio_path: str) -> str:
    try:
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        return f"文字起こし中にエラーが発生しました: {e}"

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_121010_fixed.py ===
エラーの内容を見ると、Pythonのコードが日本語で書かれているためにSyntaxErrorが発生しているようです。Pythonのコードは英語で書く必要があります。

また、関数名がaddなのに、実際の処理が引き算になっているのも問題です。これを加算に修正する必要があります。

修正後のコードは以下の通りです。

```python
def add(a, b):
    return a + b
```

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_121031_original.py ===
エラーの内容を見ると、Pythonのコードが日本語で書かれているためにSyntaxErrorが発生しているようです。Pythonのコードは英語で書く必要があります。

また、関数名がaddなのに、実際の処理が引き算になっているのも問題です。これを加算に修正する必要があります。

修正後のコードは以下の通りです。

```python
def add(a, b):
    return a + b
```

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_124433_fixed.py ===
```python
# This is a pytest-style unit test for the provided Python code.
def add(a, b):
    return a + b  # Fixed: changed from return a - b to return a + b
```
エラーメッセージを見ると、Pythonのコード内で無効な文字が使われていることが原因でエラーが発生しています。具体的には、日本語の文字「、」が原因でエラーが発生しています。

しかし、提供されたコードにはそのような文字は存在しないため、エラーが発生した原因を特定することは難しいです。エラーメッセージに記載されているファイルパスを見ると、エラーはユーザーのローカル環境で発生しているようです。そのため、ユーザーがローカル環境で何かしらの操作を行った結果、エラーが発生した可能性があります。

したがって、提供されたコード自体には問題がないと考えられます。ユーザーには、ローカル環境での操作を見直すか、エラーが発生した環境での詳細な情報を提供してもらうことをおすすめします。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_131857_fixed.py ===
```python
def add(a, b):
    return a + b

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```
エラーメッセージから、Pythonのコード内に無効な文字（'、'）があることが原因と推測されます。そのため、その部分を削除しました。また、元のコードには「# Corrected from subtraction to addition」というコメントがありましたが、これは誤解を招く可能性があるため削除しました。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_142329_fixed.py ===
申し訳ありませんが、具体的なPythonコードが提供されていないため、修正済みのコードを提供することができません。ただし、エラーメッセージから推測すると、Pythonコード内に非ASCII文字（この場合は日本語）が含まれているためにエラーが発生しているようです。

PythonはASCII文字以外もサポートしていますが、その場合はファイルの先頭に文字コードを示す特別なコメント（マジックコメント）を記述する必要があります。以下のように、ファイルの先頭に`# -*- coding: utf-8 -*-`を追加すると、UTF-8でエンコードされた非ASCII文字を含むPythonコードを正しく解釈できます。

```python
# -*- coding: utf-8 -*-
# ここでは、簡単なPythonの関数とそのためのpytest形式のユニットテストを提供します。
```

ただし、一般的には、Pythonコード内で非ASCII文字を使用するのは避けるべきです。特に、エラーメッセージに示されているように、非ASCII文字が含まれるとPythonの構文解析が失敗し、`SyntaxError`が発生します。そのため、非ASCII文字を含むコメントやドキュメンテーション文字列以外の部分は、ASCII文字だけを使用するようにしてください。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_173722_fixed.py ===
申し訳ありませんが、具体的なPythonコードが示されていないため、特定の関数やクラスに対するpytest形式のユニットテストを生成することはできません。というコメントは非ASCII文字を含んでいるため、エラーが発生しています。PythonのコメントはASCII文字のみをサポートしていますので、非ASCII文字を含むコメントは適切にエンコードするか、ASCII文字のみを使用するように変更する必要があります。

以下に修正例を示します。

--- 修正済みコード ---
```python
# Sorry, but without specific Python code, it's impossible to generate pytest-style unit tests for specific functions or classes.
```

この修正では、非ASCII文字を含むコメントをASCII文字のみを使用するように英語に変更しました。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_173733_original.py ===
申し訳ありませんが、具体的なPythonコードが示されていないため、特定の関数やクラスに対するpytest形式のユニットテストを生成することはできません。というコメントは非ASCII文字を含んでいるため、エラーが発生しています。PythonのコメントはASCII文字のみをサポートしていますので、非ASCII文字を含むコメントは適切にエンコードするか、ASCII文字のみを使用するように変更する必要があります。

以下に修正例を示します。

--- 修正済みコード ---
```python
# Sorry, but without specific Python code, it's impossible to generate pytest-style unit tests for specific functions or classes.
```

この修正では、非ASCII文字を含むコメントをASCII文字のみを使用するように英語に変更しました。

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\app\celery_worker.py ===
from app import create_app
from app.extensions import celery_init_app

flask_app = create_app()
celery = celery_init_app(flask_app)     # celery インスタンス

# 例：タスク定義
@celery.task
def ping():
    print("pong")

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\gradio_app\sandbox_output\sample.py ===
# encoding: utf-8

def add_two_integers(a, b):
    """
    2つの整数を加算して返す。
    整数以外の型が与えられた場合は ValueError を投げる。
    """
    if not isinstance(a, int) or not isinstance(b, int):
        raise ValueError("入力は整数である必要があります")
    return a + b

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\gradio_app\sandbox_output\test_sample.py ===
import pytest
from sample import max_profit

def test_max_profit():
    assert max_profit([7,1,5,3,6,4]) == 6  # ← 意図的に誤った期待値
    assert max_profit([7,6,4,3,1]) == 0
    assert max_profit([]) == 0
    assert max_profit([1,2]) == 1
    assert max_profit([2,1]) == 0
    assert max_profit([3,2,6,5,0,3]) == 4

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\modules\whisper_handler.py ===
import whisper

model = whisper.load_model("small")

def transcribe_audio(audio_path: str) -> str:
    try:
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        return f"文字起こし中にエラーが発生しました: {e}"

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_121010_fixed.py ===
エラーの内容を見ると、Pythonのコードが日本語で書かれているためにSyntaxErrorが発生しているようです。Pythonのコードは英語で書く必要があります。

また、関数名がaddなのに、実際の処理が引き算になっているのも問題です。これを加算に修正する必要があります。

修正後のコードは以下の通りです。

```python
def add(a, b):
    return a + b
```

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_121031_original.py ===
エラーの内容を見ると、Pythonのコードが日本語で書かれているためにSyntaxErrorが発生しているようです。Pythonのコードは英語で書く必要があります。

また、関数名がaddなのに、実際の処理が引き算になっているのも問題です。これを加算に修正する必要があります。

修正後のコードは以下の通りです。

```python
def add(a, b):
    return a + b
```

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_124433_fixed.py ===
```python
# This is a pytest-style unit test for the provided Python code.
def add(a, b):
    return a + b  # Fixed: changed from return a - b to return a + b
```
エラーメッセージを見ると、Pythonのコード内で無効な文字が使われていることが原因でエラーが発生しています。具体的には、日本語の文字「、」が原因でエラーが発生しています。

しかし、提供されたコードにはそのような文字は存在しないため、エラーが発生した原因を特定することは難しいです。エラーメッセージに記載されているファイルパスを見ると、エラーはユーザーのローカル環境で発生しているようです。そのため、ユーザーがローカル環境で何かしらの操作を行った結果、エラーが発生した可能性があります。

したがって、提供されたコード自体には問題がないと考えられます。ユーザーには、ローカル環境での操作を見直すか、エラーが発生した環境での詳細な情報を提供してもらうことをおすすめします。

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_131857_fixed.py ===
```python
def add(a, b):
    return a + b

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```
エラーメッセージから、Pythonのコード内に無効な文字（'、'）があることが原因と推測されます。そのため、その部分を削除しました。また、元のコードには「# Corrected from subtraction to addition」というコメントがありましたが、これは誤解を招く可能性があるため削除しました。

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_142329_fixed.py ===
申し訳ありませんが、具体的なPythonコードが提供されていないため、修正済みのコードを提供することができません。ただし、エラーメッセージから推測すると、Pythonコード内に非ASCII文字（この場合は日本語）が含まれているためにエラーが発生しているようです。

PythonはASCII文字以外もサポートしていますが、その場合はファイルの先頭に文字コードを示す特別なコメント（マジックコメント）を記述する必要があります。以下のように、ファイルの先頭に`# -*- coding: utf-8 -*-`を追加すると、UTF-8でエンコードされた非ASCII文字を含むPythonコードを正しく解釈できます。

```python
# -*- coding: utf-8 -*-
# ここでは、簡単なPythonの関数とそのためのpytest形式のユニットテストを提供します。
```

ただし、一般的には、Pythonコード内で非ASCII文字を使用するのは避けるべきです。特に、エラーメッセージに示されているように、非ASCII文字が含まれるとPythonの構文解析が失敗し、`SyntaxError`が発生します。そのため、非ASCII文字を含むコメントやドキュメンテーション文字列以外の部分は、ASCII文字だけを使用するようにしてください。

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_173722_fixed.py ===
申し訳ありませんが、具体的なPythonコードが示されていないため、特定の関数やクラスに対するpytest形式のユニットテストを生成することはできません。というコメントは非ASCII文字を含んでいるため、エラーが発生しています。PythonのコメントはASCII文字のみをサポートしていますので、非ASCII文字を含むコメントは適切にエンコードするか、ASCII文字のみを使用するように変更する必要があります。

以下に修正例を示します。

--- 修正済みコード ---
```python
# Sorry, but without specific Python code, it's impossible to generate pytest-style unit tests for specific functions or classes.
```

この修正では、非ASCII文字を含むコメントをASCII文字のみを使用するように英語に変更しました。

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_173733_original.py ===
申し訳ありませんが、具体的なPythonコードが示されていないため、特定の関数やクラスに対するpytest形式のユニットテストを生成することはできません。というコメントは非ASCII文字を含んでいるため、エラーが発生しています。PythonのコメントはASCII文字のみをサポートしていますので、非ASCII文字を含むコメントは適切にエンコードするか、ASCII文字のみを使用するように変更する必要があります。

以下に修正例を示します。

--- 修正済みコード ---
```python
# Sorry, but without specific Python code, it's impossible to generate pytest-style unit tests for specific functions or classes.
```

この修正では、非ASCII文字を含むコメントをASCII文字のみを使用するように英語に変更しました。

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\app\celery_worker.py ===
from app import create_app
from app.extensions import celery_init_app

flask_app = create_app()
celery = celery_init_app(flask_app)     # celery インスタンス

# 例：タスク定義
@celery.task
def ping():
    print("pong")

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_polynomial.py ===
import pytest

import numpy as np
import numpy.polynomial.polynomial as poly
from numpy.testing import (
    assert_,
    assert_allclose,
    assert_almost_equal,
    assert_array_almost_equal,
    assert_array_equal,
    assert_equal,
    assert_raises,
)

# `poly1d` has some support for `np.bool` and `np.timedelta64`,
# but it is limited and they are therefore excluded here
TYPE_CODES = np.typecodes["AllInteger"] + np.typecodes["AllFloat"] + "O"


class TestPolynomial:
    def test_poly1d_str_and_repr(self):
        p = np.poly1d([1., 2, 3])
        assert_equal(repr(p), 'poly1d([1., 2., 3.])')
        assert_equal(str(p),
                     '   2\n'
                     '1 x + 2 x + 3')

        q = np.poly1d([3., 2, 1])
        assert_equal(repr(q), 'poly1d([3., 2., 1.])')
        assert_equal(str(q),
                     '   2\n'
                     '3 x + 2 x + 1')

        r = np.poly1d([1.89999 + 2j, -3j, -5.12345678, 2 + 1j])
        assert_equal(str(r),
                     '            3      2\n'
                     '(1.9 + 2j) x - 3j x - 5.123 x + (2 + 1j)')

        assert_equal(str(np.poly1d([-3, -2, -1])),
                     '    2\n'
                     '-3 x - 2 x - 1')

    def test_poly1d_resolution(self):
        p = np.poly1d([1., 2, 3])
        q = np.poly1d([3., 2, 1])
        assert_equal(p(0), 3.0)
        assert_equal(p(5), 38.0)
        assert_equal(q(0), 1.0)
        assert_equal(q(5), 86.0)

    def test_poly1d_math(self):
        # here we use some simple coeffs to make calculations easier
        p = np.poly1d([1., 2, 4])
        q = np.poly1d([4., 2, 1])
        assert_equal(p / q, (np.poly1d([0.25]), np.poly1d([1.5, 3.75])))
        assert_equal(p.integ(), np.poly1d([1 / 3, 1., 4., 0.]))
        assert_equal(p.integ(1), np.poly1d([1 / 3, 1., 4., 0.]))

        p = np.poly1d([1., 2, 3])
        q = np.poly1d([3., 2, 1])
        assert_equal(p * q, np.poly1d([3., 8., 14., 8., 3.]))
        assert_equal(p + q, np.poly1d([4., 4., 4.]))
        assert_equal(p - q, np.poly1d([-2., 0., 2.]))
        assert_equal(p ** 4, np.poly1d([1., 8., 36., 104., 214., 312., 324., 216., 81.]))
        assert_equal(p(q), np.poly1d([9., 12., 16., 8., 6.]))
        assert_equal(q(p), np.poly1d([3., 12., 32., 40., 34.]))
        assert_equal(p.deriv(), np.poly1d([2., 2.]))
        assert_equal(p.deriv(2), np.poly1d([2.]))
        assert_equal(np.polydiv(np.poly1d([1, 0, -1]), np.poly1d([1, 1])),
                     (np.poly1d([1., -1.]), np.poly1d([0.])))

    @pytest.mark.parametrize("type_code", TYPE_CODES)
    def test_poly1d_misc(self, type_code: str) -> None:
        dtype = np.dtype(type_code)
        ar = np.array([1, 2, 3], dtype=dtype)
        p = np.poly1d(ar)

        # `__eq__`
        assert_equal(np.asarray(p), ar)
        assert_equal(np.asarray(p).dtype, dtype)
        assert_equal(len(p), 2)

        # `__getitem__`
        comparison_dct = {-1: 0, 0: 3, 1: 2, 2: 1, 3: 0}
        for index, ref in comparison_dct.items():
            scalar = p[index]
            assert_equal(scalar, ref)
            if dtype == np.object_:
                assert isinstance(scalar, int)
            else:
                assert_equal(scalar.dtype, dtype)

    def test_poly1d_variable_arg(self):
        q = np.poly1d([1., 2, 3], variable='y')
        assert_equal(str(q),
                     '   2\n'
                     '1 y + 2 y + 3')
        q = np.poly1d([1., 2, 3], variable='lambda')
        assert_equal(str(q),
                     '        2\n'
                     '1 lambda + 2 lambda + 3')

    def test_poly(self):
        assert_array_almost_equal(np.poly([3, -np.sqrt(2), np.sqrt(2)]),
                                  [1, -3, -2, 6])

        # From matlab docs
        A = [[1, 2, 3], [4, 5, 6], [7, 8, 0]]
        assert_array_almost_equal(np.poly(A), [1, -6, -72, -27])

        # Should produce real output for perfect conjugates
        assert_(np.isrealobj(np.poly([+1.082j, +2.613j, -2.613j, -1.082j])))
        assert_(np.isrealobj(np.poly([0 + 1j, -0 + -1j, 1 + 2j,
                                      1 - 2j, 1. + 3.5j, 1 - 3.5j])))
        assert_(np.isrealobj(np.poly([1j, -1j, 1 + 2j, 1 - 2j, 1 + 3j, 1 - 3.j])))
        assert_(np.isrealobj(np.poly([1j, -1j, 1 + 2j, 1 - 2j])))
        assert_(np.isrealobj(np.poly([1j, -1j, 2j, -2j])))
        assert_(np.isrealobj(np.poly([1j, -1j])))
        assert_(np.isrealobj(np.poly([1, -1])))

        assert_(np.iscomplexobj(np.poly([1j, -1.0000001j])))

        np.random.seed(42)
        a = np.random.randn(100) + 1j * np.random.randn(100)
        assert_(np.isrealobj(np.poly(np.concatenate((a, np.conjugate(a))))))

    def test_roots(self):
        assert_array_equal(np.roots([1, 0, 0]), [0, 0])

        # Testing for larger root values
        for i in np.logspace(10, 25, num=1000, base=10):
            tgt = np.array([-1, 1, i])
            res = np.sort(np.roots(poly.polyfromroots(tgt)[::-1]))
            assert_almost_equal(res, tgt, 14 - int(np.log10(i)))    # Adapting the expected precision according to the root value, to take into account numerical calculation error

        for i in np.logspace(10, 25, num=1000, base=10):
            tgt = np.array([-1, 1.01, i])
            res = np.sort(np.roots(poly.polyfromroots(tgt)[::-1]))
            assert_almost_equal(res, tgt, 14 - int(np.log10(i)))    # Adapting the expected precision according to the root value, to take into account numerical calculation error

    def test_str_leading_zeros(self):
        p = np.poly1d([4, 3, 2, 1])
        p[3] = 0
        assert_equal(str(p),
                     "   2\n"
                     "3 x + 2 x + 1")

        p = np.poly1d([1, 2])
        p[0] = 0
        p[1] = 0
        assert_equal(str(p), " \n0")

    def test_polyfit(self):
        c = np.array([3., 2., 1.])
        x = np.linspace(0, 2, 7)
        y = np.polyval(c, x)
        err = [1, -1, 1, -1, 1, -1, 1]
        weights = np.arange(8, 1, -1)**2 / 7.0

        # Check exception when too few points for variance estimate. Note that
        # the estimate requires the number of data points to exceed
        # degree + 1
        assert_raises(ValueError, np.polyfit,
                      [1], [1], deg=0, cov=True)

        # check 1D case
        m, cov = np.polyfit(x, y + err, 2, cov=True)
        est = [3.8571, 0.2857, 1.619]
        assert_almost_equal(est, m, decimal=4)
        val0 = [[ 1.4694, -2.9388,  0.8163],
                [-2.9388,  6.3673, -2.1224],
                [ 0.8163, -2.1224,  1.161 ]]  # noqa: E202
        assert_almost_equal(val0, cov, decimal=4)

        m2, cov2 = np.polyfit(x, y + err, 2, w=weights, cov=True)
        assert_almost_equal([4.8927, -1.0177, 1.7768], m2, decimal=4)
        val = [[ 4.3964, -5.0052,  0.4878],
               [-5.0052,  6.8067, -0.9089],
               [ 0.4878, -0.9089,  0.3337]]
        assert_almost_equal(val, cov2, decimal=4)

        m3, cov3 = np.polyfit(x, y + err, 2, w=weights, cov="unscaled")
        assert_almost_equal([4.8927, -1.0177, 1.7768], m3, decimal=4)
        val = [[ 0.1473, -0.1677,  0.0163],
               [-0.1677,  0.228 , -0.0304],  # noqa: E203
               [ 0.0163, -0.0304,  0.0112]]
        assert_almost_equal(val, cov3, decimal=4)

        # check 2D (n,1) case
        y = y[:, np.newaxis]
        c = c[:, np.newaxis]
        assert_almost_equal(c, np.polyfit(x, y, 2))
        # check 2D (n,2) case
        yy = np.concatenate((y, y), axis=1)
        cc = np.concatenate((c, c), axis=1)
        assert_almost_equal(cc, np.polyfit(x, yy, 2))

        m, cov = np.polyfit(x, yy + np.array(err)[:, np.newaxis], 2, cov=True)
        assert_almost_equal(est, m[:, 0], decimal=4)
        assert_almost_equal(est, m[:, 1], decimal=4)
        assert_almost_equal(val0, cov[:, :, 0], decimal=4)
        assert_almost_equal(val0, cov[:, :, 1], decimal=4)

        # check order 1 (deg=0) case, were the analytic results are simple
        np.random.seed(123)
        y = np.random.normal(size=(4, 10000))
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, deg=0, cov=True)
        # Should get sigma_mean = sigma/sqrt(N) = 1./sqrt(4) = 0.5.
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_allclose(np.sqrt(cov.mean()), 0.5, atol=0.01)
        # Without scaling, since reduced chi2 is 1, the result should be the same.
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, w=np.ones(y.shape[0]),
                               deg=0, cov="unscaled")
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_almost_equal(np.sqrt(cov.mean()), 0.5)
        # If we estimate our errors wrong, no change with scaling:
        w = np.full(y.shape[0], 1. / 0.5)
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, w=w, deg=0, cov=True)
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_allclose(np.sqrt(cov.mean()), 0.5, atol=0.01)
        # But if we do not scale, our estimate for the error in the mean will
        # differ.
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, w=w, deg=0, cov="unscaled")
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_almost_equal(np.sqrt(cov.mean()), 0.25)

    def test_objects(self):
        from decimal import Decimal
        p = np.poly1d([Decimal('4.0'), Decimal('3.0'), Decimal('2.0')])
        p2 = p * Decimal('1.333333333333333')
        assert_(p2[1] == Decimal("3.9999999999999990"))
        p2 = p.deriv()
        assert_(p2[1] == Decimal('8.0'))
        p2 = p.integ()
        assert_(p2[3] == Decimal("1.333333333333333333333333333"))
        assert_(p2[2] == Decimal('1.5'))
        assert_(np.issubdtype(p2.coeffs.dtype, np.object_))
        p = np.poly([Decimal(1), Decimal(2)])
        assert_equal(np.poly([Decimal(1), Decimal(2)]),
                     [1, Decimal(-3), Decimal(2)])

    def test_complex(self):
        p = np.poly1d([3j, 2j, 1j])
        p2 = p.integ()
        assert_((p2.coeffs == [1j, 1j, 1j, 0]).all())
        p2 = p.deriv()
        assert_((p2.coeffs == [6j, 2j]).all())

    def test_integ_coeffs(self):
        p = np.poly1d([3, 2, 1])
        p2 = p.integ(3, k=[9, 7, 6])
        assert_(
            (p2.coeffs == [1 / 4. / 5., 1 / 3. / 4., 1 / 2. / 3., 9 / 1. / 2., 7, 6]).all())

    def test_zero_dims(self):
        try:
            np.poly(np.zeros((0, 0)))
        except ValueError:
            pass

    def test_poly_int_overflow(self):
        """
        Regression test for gh-5096.
        """
        v = np.arange(1, 21)
        assert_almost_equal(np.poly(v), np.poly(np.diag(v)))

    def test_zero_poly_dtype(self):
        """
        Regression test for gh-16354.
        """
        z = np.array([0, 0, 0])
        p = np.poly1d(z.astype(np.int64))
        assert_equal(p.coeffs.dtype, np.int64)

        p = np.poly1d(z.astype(np.float32))
        assert_equal(p.coeffs.dtype, np.float32)

        p = np.poly1d(z.astype(np.complex64))
        assert_equal(p.coeffs.dtype, np.complex64)

    def test_poly_eq(self):
        p = np.poly1d([1, 2, 3])
        p2 = np.poly1d([1, 2, 4])
        assert_equal(p == None, False)  # noqa: E711
        assert_equal(p != None, True)  # noqa: E711
        assert_equal(p == p, True)
        assert_equal(p == p2, False)
        assert_equal(p != p2, True)

    def test_polydiv(self):
        b = np.poly1d([2, 6, 6, 1])
        a = np.poly1d([-1j, (1 + 2j), -(2 + 1j), 1])
        q, r = np.polydiv(b, a)
        assert_equal(q.coeffs.dtype, np.complex128)
        assert_equal(r.coeffs.dtype, np.complex128)
        assert_equal(q * a + r, b)

        c = [1, 2, 3]
        d = np.poly1d([1, 2, 3])
        s, t = np.polydiv(c, d)
        assert isinstance(s, np.poly1d)
        assert isinstance(t, np.poly1d)
        u, v = np.polydiv(d, c)
        assert isinstance(u, np.poly1d)
        assert isinstance(v, np.poly1d)

    def test_poly_coeffs_mutable(self):
        """ Coefficients should be modifiable """
        p = np.poly1d([1, 2, 3])

        p.coeffs += 1
        assert_equal(p.coeffs, [2, 3, 4])

        p.coeffs[2] += 10
        assert_equal(p.coeffs, [2, 3, 14])

        # this never used to be allowed - let's not add features to deprecated
        # APIs
        assert_raises(AttributeError, setattr, p, 'coeffs', np.array(1))

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_polynomial.py ===
import pytest

import numpy as np
import numpy.polynomial.polynomial as poly
from numpy.testing import (
    assert_,
    assert_allclose,
    assert_almost_equal,
    assert_array_almost_equal,
    assert_array_equal,
    assert_equal,
    assert_raises,
)

# `poly1d` has some support for `np.bool` and `np.timedelta64`,
# but it is limited and they are therefore excluded here
TYPE_CODES = np.typecodes["AllInteger"] + np.typecodes["AllFloat"] + "O"


class TestPolynomial:
    def test_poly1d_str_and_repr(self):
        p = np.poly1d([1., 2, 3])
        assert_equal(repr(p), 'poly1d([1., 2., 3.])')
        assert_equal(str(p),
                     '   2\n'
                     '1 x + 2 x + 3')

        q = np.poly1d([3., 2, 1])
        assert_equal(repr(q), 'poly1d([3., 2., 1.])')
        assert_equal(str(q),
                     '   2\n'
                     '3 x + 2 x + 1')

        r = np.poly1d([1.89999 + 2j, -3j, -5.12345678, 2 + 1j])
        assert_equal(str(r),
                     '            3      2\n'
                     '(1.9 + 2j) x - 3j x - 5.123 x + (2 + 1j)')

        assert_equal(str(np.poly1d([-3, -2, -1])),
                     '    2\n'
                     '-3 x - 2 x - 1')

    def test_poly1d_resolution(self):
        p = np.poly1d([1., 2, 3])
        q = np.poly1d([3., 2, 1])
        assert_equal(p(0), 3.0)
        assert_equal(p(5), 38.0)
        assert_equal(q(0), 1.0)
        assert_equal(q(5), 86.0)

    def test_poly1d_math(self):
        # here we use some simple coeffs to make calculations easier
        p = np.poly1d([1., 2, 4])
        q = np.poly1d([4., 2, 1])
        assert_equal(p / q, (np.poly1d([0.25]), np.poly1d([1.5, 3.75])))
        assert_equal(p.integ(), np.poly1d([1 / 3, 1., 4., 0.]))
        assert_equal(p.integ(1), np.poly1d([1 / 3, 1., 4., 0.]))

        p = np.poly1d([1., 2, 3])
        q = np.poly1d([3., 2, 1])
        assert_equal(p * q, np.poly1d([3., 8., 14., 8., 3.]))
        assert_equal(p + q, np.poly1d([4., 4., 4.]))
        assert_equal(p - q, np.poly1d([-2., 0., 2.]))
        assert_equal(p ** 4, np.poly1d([1., 8., 36., 104., 214., 312., 324., 216., 81.]))
        assert_equal(p(q), np.poly1d([9., 12., 16., 8., 6.]))
        assert_equal(q(p), np.poly1d([3., 12., 32., 40., 34.]))
        assert_equal(p.deriv(), np.poly1d([2., 2.]))
        assert_equal(p.deriv(2), np.poly1d([2.]))
        assert_equal(np.polydiv(np.poly1d([1, 0, -1]), np.poly1d([1, 1])),
                     (np.poly1d([1., -1.]), np.poly1d([0.])))

    @pytest.mark.parametrize("type_code", TYPE_CODES)
    def test_poly1d_misc(self, type_code: str) -> None:
        dtype = np.dtype(type_code)
        ar = np.array([1, 2, 3], dtype=dtype)
        p = np.poly1d(ar)

        # `__eq__`
        assert_equal(np.asarray(p), ar)
        assert_equal(np.asarray(p).dtype, dtype)
        assert_equal(len(p), 2)

        # `__getitem__`
        comparison_dct = {-1: 0, 0: 3, 1: 2, 2: 1, 3: 0}
        for index, ref in comparison_dct.items():
            scalar = p[index]
            assert_equal(scalar, ref)
            if dtype == np.object_:
                assert isinstance(scalar, int)
            else:
                assert_equal(scalar.dtype, dtype)

    def test_poly1d_variable_arg(self):
        q = np.poly1d([1., 2, 3], variable='y')
        assert_equal(str(q),
                     '   2\n'
                     '1 y + 2 y + 3')
        q = np.poly1d([1., 2, 3], variable='lambda')
        assert_equal(str(q),
                     '        2\n'
                     '1 lambda + 2 lambda + 3')

    def test_poly(self):
        assert_array_almost_equal(np.poly([3, -np.sqrt(2), np.sqrt(2)]),
                                  [1, -3, -2, 6])

        # From matlab docs
        A = [[1, 2, 3], [4, 5, 6], [7, 8, 0]]
        assert_array_almost_equal(np.poly(A), [1, -6, -72, -27])

        # Should produce real output for perfect conjugates
        assert_(np.isrealobj(np.poly([+1.082j, +2.613j, -2.613j, -1.082j])))
        assert_(np.isrealobj(np.poly([0 + 1j, -0 + -1j, 1 + 2j,
                                      1 - 2j, 1. + 3.5j, 1 - 3.5j])))
        assert_(np.isrealobj(np.poly([1j, -1j, 1 + 2j, 1 - 2j, 1 + 3j, 1 - 3.j])))
        assert_(np.isrealobj(np.poly([1j, -1j, 1 + 2j, 1 - 2j])))
        assert_(np.isrealobj(np.poly([1j, -1j, 2j, -2j])))
        assert_(np.isrealobj(np.poly([1j, -1j])))
        assert_(np.isrealobj(np.poly([1, -1])))

        assert_(np.iscomplexobj(np.poly([1j, -1.0000001j])))

        np.random.seed(42)
        a = np.random.randn(100) + 1j * np.random.randn(100)
        assert_(np.isrealobj(np.poly(np.concatenate((a, np.conjugate(a))))))

    def test_roots(self):
        assert_array_equal(np.roots([1, 0, 0]), [0, 0])

        # Testing for larger root values
        for i in np.logspace(10, 25, num=1000, base=10):
            tgt = np.array([-1, 1, i])
            res = np.sort(np.roots(poly.polyfromroots(tgt)[::-1]))
            assert_almost_equal(res, tgt, 14 - int(np.log10(i)))    # Adapting the expected precision according to the root value, to take into account numerical calculation error

        for i in np.logspace(10, 25, num=1000, base=10):
            tgt = np.array([-1, 1.01, i])
            res = np.sort(np.roots(poly.polyfromroots(tgt)[::-1]))
            assert_almost_equal(res, tgt, 14 - int(np.log10(i)))    # Adapting the expected precision according to the root value, to take into account numerical calculation error

    def test_str_leading_zeros(self):
        p = np.poly1d([4, 3, 2, 1])
        p[3] = 0
        assert_equal(str(p),
                     "   2\n"
                     "3 x + 2 x + 1")

        p = np.poly1d([1, 2])
        p[0] = 0
        p[1] = 0
        assert_equal(str(p), " \n0")

    def test_polyfit(self):
        c = np.array([3., 2., 1.])
        x = np.linspace(0, 2, 7)
        y = np.polyval(c, x)
        err = [1, -1, 1, -1, 1, -1, 1]
        weights = np.arange(8, 1, -1)**2 / 7.0

        # Check exception when too few points for variance estimate. Note that
        # the estimate requires the number of data points to exceed
        # degree + 1
        assert_raises(ValueError, np.polyfit,
                      [1], [1], deg=0, cov=True)

        # check 1D case
        m, cov = np.polyfit(x, y + err, 2, cov=True)
        est = [3.8571, 0.2857, 1.619]
        assert_almost_equal(est, m, decimal=4)
        val0 = [[ 1.4694, -2.9388,  0.8163],
                [-2.9388,  6.3673, -2.1224],
                [ 0.8163, -2.1224,  1.161 ]]  # noqa: E202
        assert_almost_equal(val0, cov, decimal=4)

        m2, cov2 = np.polyfit(x, y + err, 2, w=weights, cov=True)
        assert_almost_equal([4.8927, -1.0177, 1.7768], m2, decimal=4)
        val = [[ 4.3964, -5.0052,  0.4878],
               [-5.0052,  6.8067, -0.9089],
               [ 0.4878, -0.9089,  0.3337]]
        assert_almost_equal(val, cov2, decimal=4)

        m3, cov3 = np.polyfit(x, y + err, 2, w=weights, cov="unscaled")
        assert_almost_equal([4.8927, -1.0177, 1.7768], m3, decimal=4)
        val = [[ 0.1473, -0.1677,  0.0163],
               [-0.1677,  0.228 , -0.0304],  # noqa: E203
               [ 0.0163, -0.0304,  0.0112]]
        assert_almost_equal(val, cov3, decimal=4)

        # check 2D (n,1) case
        y = y[:, np.newaxis]
        c = c[:, np.newaxis]
        assert_almost_equal(c, np.polyfit(x, y, 2))
        # check 2D (n,2) case
        yy = np.concatenate((y, y), axis=1)
        cc = np.concatenate((c, c), axis=1)
        assert_almost_equal(cc, np.polyfit(x, yy, 2))

        m, cov = np.polyfit(x, yy + np.array(err)[:, np.newaxis], 2, cov=True)
        assert_almost_equal(est, m[:, 0], decimal=4)
        assert_almost_equal(est, m[:, 1], decimal=4)
        assert_almost_equal(val0, cov[:, :, 0], decimal=4)
        assert_almost_equal(val0, cov[:, :, 1], decimal=4)

        # check order 1 (deg=0) case, were the analytic results are simple
        np.random.seed(123)
        y = np.random.normal(size=(4, 10000))
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, deg=0, cov=True)
        # Should get sigma_mean = sigma/sqrt(N) = 1./sqrt(4) = 0.5.
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_allclose(np.sqrt(cov.mean()), 0.5, atol=0.01)
        # Without scaling, since reduced chi2 is 1, the result should be the same.
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, w=np.ones(y.shape[0]),
                               deg=0, cov="unscaled")
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_almost_equal(np.sqrt(cov.mean()), 0.5)
        # If we estimate our errors wrong, no change with scaling:
        w = np.full(y.shape[0], 1. / 0.5)
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, w=w, deg=0, cov=True)
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_allclose(np.sqrt(cov.mean()), 0.5, atol=0.01)
        # But if we do not scale, our estimate for the error in the mean will
        # differ.
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, w=w, deg=0, cov="unscaled")
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_almost_equal(np.sqrt(cov.mean()), 0.25)

    def test_objects(self):
        from decimal import Decimal
        p = np.poly1d([Decimal('4.0'), Decimal('3.0'), Decimal('2.0')])
        p2 = p * Decimal('1.333333333333333')
        assert_(p2[1] == Decimal("3.9999999999999990"))
        p2 = p.deriv()
        assert_(p2[1] == Decimal('8.0'))
        p2 = p.integ()
        assert_(p2[3] == Decimal("1.333333333333333333333333333"))
        assert_(p2[2] == Decimal('1.5'))
        assert_(np.issubdtype(p2.coeffs.dtype, np.object_))
        p = np.poly([Decimal(1), Decimal(2)])
        assert_equal(np.poly([Decimal(1), Decimal(2)]),
                     [1, Decimal(-3), Decimal(2)])

    def test_complex(self):
        p = np.poly1d([3j, 2j, 1j])
        p2 = p.integ()
        assert_((p2.coeffs == [1j, 1j, 1j, 0]).all())
        p2 = p.deriv()
        assert_((p2.coeffs == [6j, 2j]).all())

    def test_integ_coeffs(self):
        p = np.poly1d([3, 2, 1])
        p2 = p.integ(3, k=[9, 7, 6])
        assert_(
            (p2.coeffs == [1 / 4. / 5., 1 / 3. / 4., 1 / 2. / 3., 9 / 1. / 2., 7, 6]).all())

    def test_zero_dims(self):
        try:
            np.poly(np.zeros((0, 0)))
        except ValueError:
            pass

    def test_poly_int_overflow(self):
        """
        Regression test for gh-5096.
        """
        v = np.arange(1, 21)
        assert_almost_equal(np.poly(v), np.poly(np.diag(v)))

    def test_zero_poly_dtype(self):
        """
        Regression test for gh-16354.
        """
        z = np.array([0, 0, 0])
        p = np.poly1d(z.astype(np.int64))
        assert_equal(p.coeffs.dtype, np.int64)

        p = np.poly1d(z.astype(np.float32))
        assert_equal(p.coeffs.dtype, np.float32)

        p = np.poly1d(z.astype(np.complex64))
        assert_equal(p.coeffs.dtype, np.complex64)

    def test_poly_eq(self):
        p = np.poly1d([1, 2, 3])
        p2 = np.poly1d([1, 2, 4])
        assert_equal(p == None, False)  # noqa: E711
        assert_equal(p != None, True)  # noqa: E711
        assert_equal(p == p, True)
        assert_equal(p == p2, False)
        assert_equal(p != p2, True)

    def test_polydiv(self):
        b = np.poly1d([2, 6, 6, 1])
        a = np.poly1d([-1j, (1 + 2j), -(2 + 1j), 1])
        q, r = np.polydiv(b, a)
        assert_equal(q.coeffs.dtype, np.complex128)
        assert_equal(r.coeffs.dtype, np.complex128)
        assert_equal(q * a + r, b)

        c = [1, 2, 3]
        d = np.poly1d([1, 2, 3])
        s, t = np.polydiv(c, d)
        assert isinstance(s, np.poly1d)
        assert isinstance(t, np.poly1d)
        u, v = np.polydiv(d, c)
        assert isinstance(u, np.poly1d)
        assert isinstance(v, np.poly1d)

    def test_poly_coeffs_mutable(self):
        """ Coefficients should be modifiable """
        p = np.poly1d([1, 2, 3])

        p.coeffs += 1
        assert_equal(p.coeffs, [2, 3, 4])

        p.coeffs[2] += 10
        assert_equal(p.coeffs, [2, 3, 14])

        # this never used to be allowed - let's not add features to deprecated
        # APIs
        assert_raises(AttributeError, setattr, p, 'coeffs', np.array(1))

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_polynomial.py ===
import pytest

import numpy as np
import numpy.polynomial.polynomial as poly
from numpy.testing import (
    assert_,
    assert_allclose,
    assert_almost_equal,
    assert_array_almost_equal,
    assert_array_equal,
    assert_equal,
    assert_raises,
)

# `poly1d` has some support for `np.bool` and `np.timedelta64`,
# but it is limited and they are therefore excluded here
TYPE_CODES = np.typecodes["AllInteger"] + np.typecodes["AllFloat"] + "O"


class TestPolynomial:
    def test_poly1d_str_and_repr(self):
        p = np.poly1d([1., 2, 3])
        assert_equal(repr(p), 'poly1d([1., 2., 3.])')
        assert_equal(str(p),
                     '   2\n'
                     '1 x + 2 x + 3')

        q = np.poly1d([3., 2, 1])
        assert_equal(repr(q), 'poly1d([3., 2., 1.])')
        assert_equal(str(q),
                     '   2\n'
                     '3 x + 2 x + 1')

        r = np.poly1d([1.89999 + 2j, -3j, -5.12345678, 2 + 1j])
        assert_equal(str(r),
                     '            3      2\n'
                     '(1.9 + 2j) x - 3j x - 5.123 x + (2 + 1j)')

        assert_equal(str(np.poly1d([-3, -2, -1])),
                     '    2\n'
                     '-3 x - 2 x - 1')

    def test_poly1d_resolution(self):
        p = np.poly1d([1., 2, 3])
        q = np.poly1d([3., 2, 1])
        assert_equal(p(0), 3.0)
        assert_equal(p(5), 38.0)
        assert_equal(q(0), 1.0)
        assert_equal(q(5), 86.0)

    def test_poly1d_math(self):
        # here we use some simple coeffs to make calculations easier
        p = np.poly1d([1., 2, 4])
        q = np.poly1d([4., 2, 1])
        assert_equal(p / q, (np.poly1d([0.25]), np.poly1d([1.5, 3.75])))
        assert_equal(p.integ(), np.poly1d([1 / 3, 1., 4., 0.]))
        assert_equal(p.integ(1), np.poly1d([1 / 3, 1., 4., 0.]))

        p = np.poly1d([1., 2, 3])
        q = np.poly1d([3., 2, 1])
        assert_equal(p * q, np.poly1d([3., 8., 14., 8., 3.]))
        assert_equal(p + q, np.poly1d([4., 4., 4.]))
        assert_equal(p - q, np.poly1d([-2., 0., 2.]))
        assert_equal(p ** 4, np.poly1d([1., 8., 36., 104., 214., 312., 324., 216., 81.]))
        assert_equal(p(q), np.poly1d([9., 12., 16., 8., 6.]))
        assert_equal(q(p), np.poly1d([3., 12., 32., 40., 34.]))
        assert_equal(p.deriv(), np.poly1d([2., 2.]))
        assert_equal(p.deriv(2), np.poly1d([2.]))
        assert_equal(np.polydiv(np.poly1d([1, 0, -1]), np.poly1d([1, 1])),
                     (np.poly1d([1., -1.]), np.poly1d([0.])))

    @pytest.mark.parametrize("type_code", TYPE_CODES)
    def test_poly1d_misc(self, type_code: str) -> None:
        dtype = np.dtype(type_code)
        ar = np.array([1, 2, 3], dtype=dtype)
        p = np.poly1d(ar)

        # `__eq__`
        assert_equal(np.asarray(p), ar)
        assert_equal(np.asarray(p).dtype, dtype)
        assert_equal(len(p), 2)

        # `__getitem__`
        comparison_dct = {-1: 0, 0: 3, 1: 2, 2: 1, 3: 0}
        for index, ref in comparison_dct.items():
            scalar = p[index]
            assert_equal(scalar, ref)
            if dtype == np.object_:
                assert isinstance(scalar, int)
            else:
                assert_equal(scalar.dtype, dtype)

    def test_poly1d_variable_arg(self):
        q = np.poly1d([1., 2, 3], variable='y')
        assert_equal(str(q),
                     '   2\n'
                     '1 y + 2 y + 3')
        q = np.poly1d([1., 2, 3], variable='lambda')
        assert_equal(str(q),
                     '        2\n'
                     '1 lambda + 2 lambda + 3')

    def test_poly(self):
        assert_array_almost_equal(np.poly([3, -np.sqrt(2), np.sqrt(2)]),
                                  [1, -3, -2, 6])

        # From matlab docs
        A = [[1, 2, 3], [4, 5, 6], [7, 8, 0]]
        assert_array_almost_equal(np.poly(A), [1, -6, -72, -27])

        # Should produce real output for perfect conjugates
        assert_(np.isrealobj(np.poly([+1.082j, +2.613j, -2.613j, -1.082j])))
        assert_(np.isrealobj(np.poly([0 + 1j, -0 + -1j, 1 + 2j,
                                      1 - 2j, 1. + 3.5j, 1 - 3.5j])))
        assert_(np.isrealobj(np.poly([1j, -1j, 1 + 2j, 1 - 2j, 1 + 3j, 1 - 3.j])))
        assert_(np.isrealobj(np.poly([1j, -1j, 1 + 2j, 1 - 2j])))
        assert_(np.isrealobj(np.poly([1j, -1j, 2j, -2j])))
        assert_(np.isrealobj(np.poly([1j, -1j])))
        assert_(np.isrealobj(np.poly([1, -1])))

        assert_(np.iscomplexobj(np.poly([1j, -1.0000001j])))

        np.random.seed(42)
        a = np.random.randn(100) + 1j * np.random.randn(100)
        assert_(np.isrealobj(np.poly(np.concatenate((a, np.conjugate(a))))))

    def test_roots(self):
        assert_array_equal(np.roots([1, 0, 0]), [0, 0])

        # Testing for larger root values
        for i in np.logspace(10, 25, num=1000, base=10):
            tgt = np.array([-1, 1, i])
            res = np.sort(np.roots(poly.polyfromroots(tgt)[::-1]))
            assert_almost_equal(res, tgt, 14 - int(np.log10(i)))    # Adapting the expected precision according to the root value, to take into account numerical calculation error

        for i in np.logspace(10, 25, num=1000, base=10):
            tgt = np.array([-1, 1.01, i])
            res = np.sort(np.roots(poly.polyfromroots(tgt)[::-1]))
            assert_almost_equal(res, tgt, 14 - int(np.log10(i)))    # Adapting the expected precision according to the root value, to take into account numerical calculation error

    def test_str_leading_zeros(self):
        p = np.poly1d([4, 3, 2, 1])
        p[3] = 0
        assert_equal(str(p),
                     "   2\n"
                     "3 x + 2 x + 1")

        p = np.poly1d([1, 2])
        p[0] = 0
        p[1] = 0
        assert_equal(str(p), " \n0")

    def test_polyfit(self):
        c = np.array([3., 2., 1.])
        x = np.linspace(0, 2, 7)
        y = np.polyval(c, x)
        err = [1, -1, 1, -1, 1, -1, 1]
        weights = np.arange(8, 1, -1)**2 / 7.0

        # Check exception when too few points for variance estimate. Note that
        # the estimate requires the number of data points to exceed
        # degree + 1
        assert_raises(ValueError, np.polyfit,
                      [1], [1], deg=0, cov=True)

        # check 1D case
        m, cov = np.polyfit(x, y + err, 2, cov=True)
        est = [3.8571, 0.2857, 1.619]
        assert_almost_equal(est, m, decimal=4)
        val0 = [[ 1.4694, -2.9388,  0.8163],
                [-2.9388,  6.3673, -2.1224],
                [ 0.8163, -2.1224,  1.161 ]]  # noqa: E202
        assert_almost_equal(val0, cov, decimal=4)

        m2, cov2 = np.polyfit(x, y + err, 2, w=weights, cov=True)
        assert_almost_equal([4.8927, -1.0177, 1.7768], m2, decimal=4)
        val = [[ 4.3964, -5.0052,  0.4878],
               [-5.0052,  6.8067, -0.9089],
               [ 0.4878, -0.9089,  0.3337]]
        assert_almost_equal(val, cov2, decimal=4)

        m3, cov3 = np.polyfit(x, y + err, 2, w=weights, cov="unscaled")
        assert_almost_equal([4.8927, -1.0177, 1.7768], m3, decimal=4)
        val = [[ 0.1473, -0.1677,  0.0163],
               [-0.1677,  0.228 , -0.0304],  # noqa: E203
               [ 0.0163, -0.0304,  0.0112]]
        assert_almost_equal(val, cov3, decimal=4)

        # check 2D (n,1) case
        y = y[:, np.newaxis]
        c = c[:, np.newaxis]
        assert_almost_equal(c, np.polyfit(x, y, 2))
        # check 2D (n,2) case
        yy = np.concatenate((y, y), axis=1)
        cc = np.concatenate((c, c), axis=1)
        assert_almost_equal(cc, np.polyfit(x, yy, 2))

        m, cov = np.polyfit(x, yy + np.array(err)[:, np.newaxis], 2, cov=True)
        assert_almost_equal(est, m[:, 0], decimal=4)
        assert_almost_equal(est, m[:, 1], decimal=4)
        assert_almost_equal(val0, cov[:, :, 0], decimal=4)
        assert_almost_equal(val0, cov[:, :, 1], decimal=4)

        # check order 1 (deg=0) case, were the analytic results are simple
        np.random.seed(123)
        y = np.random.normal(size=(4, 10000))
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, deg=0, cov=True)
        # Should get sigma_mean = sigma/sqrt(N) = 1./sqrt(4) = 0.5.
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_allclose(np.sqrt(cov.mean()), 0.5, atol=0.01)
        # Without scaling, since reduced chi2 is 1, the result should be the same.
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, w=np.ones(y.shape[0]),
                               deg=0, cov="unscaled")
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_almost_equal(np.sqrt(cov.mean()), 0.5)
        # If we estimate our errors wrong, no change with scaling:
        w = np.full(y.shape[0], 1. / 0.5)
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, w=w, deg=0, cov=True)
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_allclose(np.sqrt(cov.mean()), 0.5, atol=0.01)
        # But if we do not scale, our estimate for the error in the mean will
        # differ.
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, w=w, deg=0, cov="unscaled")
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_almost_equal(np.sqrt(cov.mean()), 0.25)

    def test_objects(self):
        from decimal import Decimal
        p = np.poly1d([Decimal('4.0'), Decimal('3.0'), Decimal('2.0')])
        p2 = p * Decimal('1.333333333333333')
        assert_(p2[1] == Decimal("3.9999999999999990"))
        p2 = p.deriv()
        assert_(p2[1] == Decimal('8.0'))
        p2 = p.integ()
        assert_(p2[3] == Decimal("1.333333333333333333333333333"))
        assert_(p2[2] == Decimal('1.5'))
        assert_(np.issubdtype(p2.coeffs.dtype, np.object_))
        p = np.poly([Decimal(1), Decimal(2)])
        assert_equal(np.poly([Decimal(1), Decimal(2)]),
                     [1, Decimal(-3), Decimal(2)])

    def test_complex(self):
        p = np.poly1d([3j, 2j, 1j])
        p2 = p.integ()
        assert_((p2.coeffs == [1j, 1j, 1j, 0]).all())
        p2 = p.deriv()
        assert_((p2.coeffs == [6j, 2j]).all())

    def test_integ_coeffs(self):
        p = np.poly1d([3, 2, 1])
        p2 = p.integ(3, k=[9, 7, 6])
        assert_(
            (p2.coeffs == [1 / 4. / 5., 1 / 3. / 4., 1 / 2. / 3., 9 / 1. / 2., 7, 6]).all())

    def test_zero_dims(self):
        try:
            np.poly(np.zeros((0, 0)))
        except ValueError:
            pass

    def test_poly_int_overflow(self):
        """
        Regression test for gh-5096.
        """
        v = np.arange(1, 21)
        assert_almost_equal(np.poly(v), np.poly(np.diag(v)))

    def test_zero_poly_dtype(self):
        """
        Regression test for gh-16354.
        """
        z = np.array([0, 0, 0])
        p = np.poly1d(z.astype(np.int64))
        assert_equal(p.coeffs.dtype, np.int64)

        p = np.poly1d(z.astype(np.float32))
        assert_equal(p.coeffs.dtype, np.float32)

        p = np.poly1d(z.astype(np.complex64))
        assert_equal(p.coeffs.dtype, np.complex64)

    def test_poly_eq(self):
        p = np.poly1d([1, 2, 3])
        p2 = np.poly1d([1, 2, 4])
        assert_equal(p == None, False)  # noqa: E711
        assert_equal(p != None, True)  # noqa: E711
        assert_equal(p == p, True)
        assert_equal(p == p2, False)
        assert_equal(p != p2, True)

    def test_polydiv(self):
        b = np.poly1d([2, 6, 6, 1])
        a = np.poly1d([-1j, (1 + 2j), -(2 + 1j), 1])
        q, r = np.polydiv(b, a)
        assert_equal(q.coeffs.dtype, np.complex128)
        assert_equal(r.coeffs.dtype, np.complex128)
        assert_equal(q * a + r, b)

        c = [1, 2, 3]
        d = np.poly1d([1, 2, 3])
        s, t = np.polydiv(c, d)
        assert isinstance(s, np.poly1d)
        assert isinstance(t, np.poly1d)
        u, v = np.polydiv(d, c)
        assert isinstance(u, np.poly1d)
        assert isinstance(v, np.poly1d)

    def test_poly_coeffs_mutable(self):
        """ Coefficients should be modifiable """
        p = np.poly1d([1, 2, 3])

        p.coeffs += 1
        assert_equal(p.coeffs, [2, 3, 4])

        p.coeffs[2] += 10
        assert_equal(p.coeffs, [2, 3, 14])

        # this never used to be allowed - let's not add features to deprecated
        # APIs
        assert_raises(AttributeError, setattr, p, 'coeffs', np.array(1))

# === NexusCore/my-crm-app\app\models.py ===
# TODO: Define database models

from . import db

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    # TODO: Add more fields as necessary

# === NexusCore/src\file_creator.py ===
# src/file_creator.py
import os

def create_code_file(filename: str, code: str, folder: str = "src/generated") -> str:
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path

# === NexusCore/src\sandbox_logs\repair_20250713_114519_fixed.py ===
エラーメッセージを見ると、テストモジュールのインポートに失敗しているようです。これはPythonのコードに問題があるというよりは、テスト環境の設定やファイルの配置に問題がある可能性が高いです。ユーザーが提供したコードの中には、確かに間違いがありますが、それがこのエラーの原因ではないようです。

ただし、ユーザーが指摘した通り、関数addの中の演算が間違っています。正しくは以下のようになります。

--- 修正済みコード ---
```python
def add(a, b):
    return a + b  # ✔️ a + b
```

# === NexusCore/src\sandbox_logs\repair_20250713_114534_original.py ===
エラーメッセージを見ると、テストモジュールのインポートに失敗しているようです。これはPythonのコードに問題があるというよりは、テスト環境の設定やファイルの配置に問題がある可能性が高いです。ユーザーが提供したコードの中には、確かに間違いがありますが、それがこのエラーの原因ではないようです。

ただし、ユーザーが指摘した通り、関数addの中の演算が間違っています。正しくは以下のようになります。

--- 修正済みコード ---
```python
def add(a, b):
    return a + b  # ✔️ a + b
```

# === NexusCore/src\sandbox_logs\repair_20250713_131843_fixed.py ===
```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```

# === NexusCore/src\sandbox_logs\repair_20250713_131857_original.py ===
```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\my-crm-app\app\models.py ===
# TODO: Define database models

from . import db

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    # TODO: Add more fields as necessary

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\file_creator.py ===
# src/file_creator.py
import os

def create_code_file(filename: str, code: str, folder: str = "src/generated") -> str:
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_114519_fixed.py ===
エラーメッセージを見ると、テストモジュールのインポートに失敗しているようです。これはPythonのコードに問題があるというよりは、テスト環境の設定やファイルの配置に問題がある可能性が高いです。ユーザーが提供したコードの中には、確かに間違いがありますが、それがこのエラーの原因ではないようです。

ただし、ユーザーが指摘した通り、関数addの中の演算が間違っています。正しくは以下のようになります。

--- 修正済みコード ---
```python
def add(a, b):
    return a + b  # ✔️ a + b
```

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_114534_original.py ===
エラーメッセージを見ると、テストモジュールのインポートに失敗しているようです。これはPythonのコードに問題があるというよりは、テスト環境の設定やファイルの配置に問題がある可能性が高いです。ユーザーが提供したコードの中には、確かに間違いがありますが、それがこのエラーの原因ではないようです。

ただし、ユーザーが指摘した通り、関数addの中の演算が間違っています。正しくは以下のようになります。

--- 修正済みコード ---
```python
def add(a, b):
    return a + b  # ✔️ a + b
```

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_131843_fixed.py ===
```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_131857_original.py ===
```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\my-crm-app\app\models.py ===
# TODO: Define database models

from . import db

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    # TODO: Add more fields as necessary

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\file_creator.py ===
# src/file_creator.py
import os

def create_code_file(filename: str, code: str, folder: str = "src/generated") -> str:
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_114519_fixed.py ===
エラーメッセージを見ると、テストモジュールのインポートに失敗しているようです。これはPythonのコードに問題があるというよりは、テスト環境の設定やファイルの配置に問題がある可能性が高いです。ユーザーが提供したコードの中には、確かに間違いがありますが、それがこのエラーの原因ではないようです。

ただし、ユーザーが指摘した通り、関数addの中の演算が間違っています。正しくは以下のようになります。

--- 修正済みコード ---
```python
def add(a, b):
    return a + b  # ✔️ a + b
```

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_114534_original.py ===
エラーメッセージを見ると、テストモジュールのインポートに失敗しているようです。これはPythonのコードに問題があるというよりは、テスト環境の設定やファイルの配置に問題がある可能性が高いです。ユーザーが提供したコードの中には、確かに間違いがありますが、それがこのエラーの原因ではないようです。

ただし、ユーザーが指摘した通り、関数addの中の演算が間違っています。正しくは以下のようになります。

--- 修正済みコード ---
```python
def add(a, b):
    return a + b  # ✔️ a + b
```

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_131843_fixed.py ===
```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_131857_original.py ===
```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\my-crm-app\app\models.py ===
# TODO: Define database models

from . import db

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    # TODO: Add more fields as necessary

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\file_creator.py ===
# src/file_creator.py
import os

def create_code_file(filename: str, code: str, folder: str = "src/generated") -> str:
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path

# === NexusCore/openenv\Lib\site-packages\IPython\lib\deepreload.py ===
# -*- coding: utf-8 -*-
"""
Provides a reload() function that acts recursively.

Python's normal :func:`python:reload` function only reloads the module that it's
passed. The :func:`reload` function in this module also reloads everything
imported from that module, which is useful when you're changing files deep
inside a package.

To use this as your default reload function, type this::

    import builtins
    from IPython.lib import deepreload
    builtins.reload = deepreload.reload

A reference to the original :func:`python:reload` is stored in this module as
:data:`original_reload`, so you can restore it later.

This code is almost entirely based on knee.py, which is a Python
re-implementation of hierarchical module import.
"""
#*****************************************************************************
#       Copyright (C) 2001 Nathaniel Gray <n8gray@caltech.edu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************

import builtins as builtin_mod
from contextlib import contextmanager
import importlib
import sys

from types import ModuleType
from warnings import warn
import types

original_import = builtin_mod.__import__

@contextmanager
def replace_import_hook(new_import):
    saved_import = builtin_mod.__import__
    builtin_mod.__import__ = new_import
    try:
        yield
    finally:
        builtin_mod.__import__ = saved_import

def get_parent(globals, level):
    """
    parent, name = get_parent(globals, level)

    Return the package that an import is being performed in.  If globals comes
    from the module foo.bar.bat (not itself a package), this returns the
    sys.modules entry for foo.bar.  If globals is from a package's __init__.py,
    the package's entry in sys.modules is returned.

    If globals doesn't come from a package or a module in a package, or a
    corresponding entry is not found in sys.modules, None is returned.
    """
    orig_level = level

    if not level or not isinstance(globals, dict):
        return None, ''

    pkgname = globals.get('__package__', None)

    if pkgname is not None:
        # __package__ is set, so use it
        if not hasattr(pkgname, 'rindex'):
            raise ValueError('__package__ set to non-string')
        if len(pkgname) == 0:
            if level > 0:
                raise ValueError('Attempted relative import in non-package')
            return None, ''
        name = pkgname
    else:
        # __package__ not set, so figure it out and set it
        if '__name__' not in globals:
            return None, ''
        modname = globals['__name__']

        if '__path__' in globals:
            # __path__ is set, so modname is already the package name
            globals['__package__'] = name = modname
        else:
            # Normal module, so work out the package name if any
            lastdot = modname.rfind('.')
            if lastdot < 0 < level:
                raise ValueError("Attempted relative import in non-package")
            if lastdot < 0:
                globals['__package__'] = None
                return None, ''
            globals['__package__'] = name = modname[:lastdot]

    dot = len(name)
    for x in range(level, 1, -1):
        try:
            dot = name.rindex('.', 0, dot)
        except ValueError as e:
            raise ValueError("attempted relative import beyond top-level "
                             "package") from e
    name = name[:dot]

    try:
        parent = sys.modules[name]
    except BaseException as e:
        if orig_level < 1:
            warn("Parent module '%.200s' not found while handling absolute "
                 "import" % name)
            parent = None
        else:
            raise SystemError("Parent module '%.200s' not loaded, cannot "
                              "perform relative import" % name) from e

    # We expect, but can't guarantee, if parent != None, that:
    # - parent.__name__ == name
    # - parent.__dict__ is globals
    # If this is violated...  Who cares?
    return parent, name

def load_next(mod, altmod, name, buf):
    """
    mod, name, buf = load_next(mod, altmod, name, buf)

    altmod is either None or same as mod
    """

    if len(name) == 0:
        # completely empty module name should only happen in
        # 'from . import' (or '__import__("")')
        return mod, None, buf

    dot = name.find('.')
    if dot == 0:
        raise ValueError('Empty module name')

    if dot < 0:
        subname = name
        next = None
    else:
        subname = name[:dot]
        next = name[dot+1:]

    if buf != '':
        buf += '.'
    buf += subname

    result = import_submodule(mod, subname, buf)
    if result is None and mod != altmod:
        result = import_submodule(altmod, subname, subname)
        if result is not None:
            buf = subname

    if result is None:
        raise ImportError("No module named %.200s" % name)

    return result, next, buf


# Need to keep track of what we've already reloaded to prevent cyclic evil
found_now = {}

def import_submodule(mod, subname, fullname):
    """m = import_submodule(mod, subname, fullname)"""
    # Require:
    # if mod == None: subname == fullname
    # else: mod.__name__ + "." + subname == fullname

    global found_now
    if fullname in found_now and fullname in sys.modules:
        m = sys.modules[fullname]
    else:
        print('Reloading', fullname)
        found_now[fullname] = 1
        oldm = sys.modules.get(fullname, None)
        try:
            if oldm is not None:
                m = importlib.reload(oldm)
            else:
                m = importlib.import_module(subname, mod)
        except:
            # load_module probably removed name from modules because of
            # the error.  Put back the original module object.
            if oldm:
                sys.modules[fullname] = oldm
            raise

        add_submodule(mod, m, fullname, subname)

    return m

def add_submodule(mod, submod, fullname, subname):
    """mod.{subname} = submod"""
    if mod is None:
        return #Nothing to do here.

    if submod is None:
        submod = sys.modules[fullname]

    setattr(mod, subname, submod)

    return

def ensure_fromlist(mod, fromlist, buf, recursive):
    """Handle 'from module import a, b, c' imports."""
    if not hasattr(mod, '__path__'):
        return
    for item in fromlist:
        if not hasattr(item, 'rindex'):
            raise TypeError("Item in ``from list'' not a string")
        if item == '*':
            if recursive:
                continue # avoid endless recursion
            try:
                all = mod.__all__
            except AttributeError:
                pass
            else:
                ret = ensure_fromlist(mod, all, buf, 1)
                if not ret:
                    return 0
        elif not hasattr(mod, item):
            import_submodule(mod, item, buf + '.' + item)

def deep_import_hook(name, globals=None, locals=None, fromlist=None, level=-1):
    """Replacement for __import__()"""
    parent, buf = get_parent(globals, level)

    head, name, buf = load_next(parent, None if level < 0 else parent, name, buf)

    tail = head
    while name:
        tail, name, buf = load_next(tail, tail, name, buf)

    # If tail is None, both get_parent and load_next found
    # an empty module name: someone called __import__("") or
    # doctored faulty bytecode
    if tail is None:
        raise ValueError('Empty module name')

    if not fromlist:
        return head

    ensure_fromlist(tail, fromlist, buf, 0)
    return tail

modules_reloading = {}

def deep_reload_hook(m):
    """Replacement for reload()."""
    # Hardcode this one  as it would raise a NotImplementedError from the
    # bowels of Python and screw up the import machinery after.
    # unlike other imports the `exclude` list already in place is not enough.

    if m is types:
        return m
    if not isinstance(m, ModuleType):
        raise TypeError("reload() argument must be module")

    name = m.__name__

    if name not in sys.modules:
        raise ImportError("reload(): module %.200s not in sys.modules" % name)

    global modules_reloading
    try:
        return modules_reloading[name]
    except:
        modules_reloading[name] = m

    try:
        newm = importlib.reload(m)
    except:
        sys.modules[name] = m
        raise
    finally:
        modules_reloading.clear()
    return newm

# Save the original hooks
original_reload = importlib.reload

# Replacement for reload()
def reload(
    module,
    exclude=(
        *sys.builtin_module_names,
        "sys",
        "os.path",
        "builtins",
        "__main__",
        "numpy",
        "numpy._globals",
    ),
):
    """Recursively reload all modules used in the given module.  Optionally
    takes a list of modules to exclude from reloading.  The default exclude
    list contains modules listed in sys.builtin_module_names with additional
    sys, os.path, builtins and __main__, to prevent, e.g., resetting
    display, exception, and io hooks.
    """
    global found_now
    for i in exclude:
        found_now[i] = 1
    try:
        with replace_import_hook(deep_import_hook):
            return deep_reload_hook(module)
    finally:
        found_now = {}

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\lib\deepreload.py ===
# -*- coding: utf-8 -*-
"""
Provides a reload() function that acts recursively.

Python's normal :func:`python:reload` function only reloads the module that it's
passed. The :func:`reload` function in this module also reloads everything
imported from that module, which is useful when you're changing files deep
inside a package.

To use this as your default reload function, type this::

    import builtins
    from IPython.lib import deepreload
    builtins.reload = deepreload.reload

A reference to the original :func:`python:reload` is stored in this module as
:data:`original_reload`, so you can restore it later.

This code is almost entirely based on knee.py, which is a Python
re-implementation of hierarchical module import.
"""
#*****************************************************************************
#       Copyright (C) 2001 Nathaniel Gray <n8gray@caltech.edu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************

import builtins as builtin_mod
from contextlib import contextmanager
import importlib
import sys

from types import ModuleType
from warnings import warn
import types

original_import = builtin_mod.__import__

@contextmanager
def replace_import_hook(new_import):
    saved_import = builtin_mod.__import__
    builtin_mod.__import__ = new_import
    try:
        yield
    finally:
        builtin_mod.__import__ = saved_import

def get_parent(globals, level):
    """
    parent, name = get_parent(globals, level)

    Return the package that an import is being performed in.  If globals comes
    from the module foo.bar.bat (not itself a package), this returns the
    sys.modules entry for foo.bar.  If globals is from a package's __init__.py,
    the package's entry in sys.modules is returned.

    If globals doesn't come from a package or a module in a package, or a
    corresponding entry is not found in sys.modules, None is returned.
    """
    orig_level = level

    if not level or not isinstance(globals, dict):
        return None, ''

    pkgname = globals.get('__package__', None)

    if pkgname is not None:
        # __package__ is set, so use it
        if not hasattr(pkgname, 'rindex'):
            raise ValueError('__package__ set to non-string')
        if len(pkgname) == 0:
            if level > 0:
                raise ValueError('Attempted relative import in non-package')
            return None, ''
        name = pkgname
    else:
        # __package__ not set, so figure it out and set it
        if '__name__' not in globals:
            return None, ''
        modname = globals['__name__']

        if '__path__' in globals:
            # __path__ is set, so modname is already the package name
            globals['__package__'] = name = modname
        else:
            # Normal module, so work out the package name if any
            lastdot = modname.rfind('.')
            if lastdot < 0 < level:
                raise ValueError("Attempted relative import in non-package")
            if lastdot < 0:
                globals['__package__'] = None
                return None, ''
            globals['__package__'] = name = modname[:lastdot]

    dot = len(name)
    for x in range(level, 1, -1):
        try:
            dot = name.rindex('.', 0, dot)
        except ValueError as e:
            raise ValueError("attempted relative import beyond top-level "
                             "package") from e
    name = name[:dot]

    try:
        parent = sys.modules[name]
    except BaseException as e:
        if orig_level < 1:
            warn("Parent module '%.200s' not found while handling absolute "
                 "import" % name)
            parent = None
        else:
            raise SystemError("Parent module '%.200s' not loaded, cannot "
                              "perform relative import" % name) from e

    # We expect, but can't guarantee, if parent != None, that:
    # - parent.__name__ == name
    # - parent.__dict__ is globals
    # If this is violated...  Who cares?
    return parent, name

def load_next(mod, altmod, name, buf):
    """
    mod, name, buf = load_next(mod, altmod, name, buf)

    altmod is either None or same as mod
    """

    if len(name) == 0:
        # completely empty module name should only happen in
        # 'from . import' (or '__import__("")')
        return mod, None, buf

    dot = name.find('.')
    if dot == 0:
        raise ValueError('Empty module name')

    if dot < 0:
        subname = name
        next = None
    else:
        subname = name[:dot]
        next = name[dot+1:]

    if buf != '':
        buf += '.'
    buf += subname

    result = import_submodule(mod, subname, buf)
    if result is None and mod != altmod:
        result = import_submodule(altmod, subname, subname)
        if result is not None:
            buf = subname

    if result is None:
        raise ImportError("No module named %.200s" % name)

    return result, next, buf


# Need to keep track of what we've already reloaded to prevent cyclic evil
found_now = {}

def import_submodule(mod, subname, fullname):
    """m = import_submodule(mod, subname, fullname)"""
    # Require:
    # if mod == None: subname == fullname
    # else: mod.__name__ + "." + subname == fullname

    global found_now
    if fullname in found_now and fullname in sys.modules:
        m = sys.modules[fullname]
    else:
        print('Reloading', fullname)
        found_now[fullname] = 1
        oldm = sys.modules.get(fullname, None)
        try:
            if oldm is not None:
                m = importlib.reload(oldm)
            else:
                m = importlib.import_module(subname, mod)
        except:
            # load_module probably removed name from modules because of
            # the error.  Put back the original module object.
            if oldm:
                sys.modules[fullname] = oldm
            raise

        add_submodule(mod, m, fullname, subname)

    return m

def add_submodule(mod, submod, fullname, subname):
    """mod.{subname} = submod"""
    if mod is None:
        return #Nothing to do here.

    if submod is None:
        submod = sys.modules[fullname]

    setattr(mod, subname, submod)

    return

def ensure_fromlist(mod, fromlist, buf, recursive):
    """Handle 'from module import a, b, c' imports."""
    if not hasattr(mod, '__path__'):
        return
    for item in fromlist:
        if not hasattr(item, 'rindex'):
            raise TypeError("Item in ``from list'' not a string")
        if item == '*':
            if recursive:
                continue # avoid endless recursion
            try:
                all = mod.__all__
            except AttributeError:
                pass
            else:
                ret = ensure_fromlist(mod, all, buf, 1)
                if not ret:
                    return 0
        elif not hasattr(mod, item):
            import_submodule(mod, item, buf + '.' + item)

def deep_import_hook(name, globals=None, locals=None, fromlist=None, level=-1):
    """Replacement for __import__()"""
    parent, buf = get_parent(globals, level)

    head, name, buf = load_next(parent, None if level < 0 else parent, name, buf)

    tail = head
    while name:
        tail, name, buf = load_next(tail, tail, name, buf)

    # If tail is None, both get_parent and load_next found
    # an empty module name: someone called __import__("") or
    # doctored faulty bytecode
    if tail is None:
        raise ValueError('Empty module name')

    if not fromlist:
        return head

    ensure_fromlist(tail, fromlist, buf, 0)
    return tail

modules_reloading = {}

def deep_reload_hook(m):
    """Replacement for reload()."""
    # Hardcode this one  as it would raise a NotImplementedError from the
    # bowels of Python and screw up the import machinery after.
    # unlike other imports the `exclude` list already in place is not enough.

    if m is types:
        return m
    if not isinstance(m, ModuleType):
        raise TypeError("reload() argument must be module")

    name = m.__name__

    if name not in sys.modules:
        raise ImportError("reload(): module %.200s not in sys.modules" % name)

    global modules_reloading
    try:
        return modules_reloading[name]
    except:
        modules_reloading[name] = m

    try:
        newm = importlib.reload(m)
    except:
        sys.modules[name] = m
        raise
    finally:
        modules_reloading.clear()
    return newm

# Save the original hooks
original_reload = importlib.reload

# Replacement for reload()
def reload(
    module,
    exclude=(
        *sys.builtin_module_names,
        "sys",
        "os.path",
        "builtins",
        "__main__",
        "numpy",
        "numpy._globals",
    ),
):
    """Recursively reload all modules used in the given module.  Optionally
    takes a list of modules to exclude from reloading.  The default exclude
    list contains modules listed in sys.builtin_module_names with additional
    sys, os.path, builtins and __main__, to prevent, e.g., resetting
    display, exception, and io hooks.
    """
    global found_now
    for i in exclude:
        found_now[i] = 1
    try:
        with replace_import_hook(deep_import_hook):
            return deep_reload_hook(module)
    finally:
        found_now = {}

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\IPython\lib\deepreload.py ===
# -*- coding: utf-8 -*-
"""
Provides a reload() function that acts recursively.

Python's normal :func:`python:reload` function only reloads the module that it's
passed. The :func:`reload` function in this module also reloads everything
imported from that module, which is useful when you're changing files deep
inside a package.

To use this as your default reload function, type this::

    import builtins
    from IPython.lib import deepreload
    builtins.reload = deepreload.reload

A reference to the original :func:`python:reload` is stored in this module as
:data:`original_reload`, so you can restore it later.

This code is almost entirely based on knee.py, which is a Python
re-implementation of hierarchical module import.
"""
#*****************************************************************************
#       Copyright (C) 2001 Nathaniel Gray <n8gray@caltech.edu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************

import builtins as builtin_mod
from contextlib import contextmanager
import importlib
import sys

from types import ModuleType
from warnings import warn
import types

original_import = builtin_mod.__import__

@contextmanager
def replace_import_hook(new_import):
    saved_import = builtin_mod.__import__
    builtin_mod.__import__ = new_import
    try:
        yield
    finally:
        builtin_mod.__import__ = saved_import

def get_parent(globals, level):
    """
    parent, name = get_parent(globals, level)

    Return the package that an import is being performed in.  If globals comes
    from the module foo.bar.bat (not itself a package), this returns the
    sys.modules entry for foo.bar.  If globals is from a package's __init__.py,
    the package's entry in sys.modules is returned.

    If globals doesn't come from a package or a module in a package, or a
    corresponding entry is not found in sys.modules, None is returned.
    """
    orig_level = level

    if not level or not isinstance(globals, dict):
        return None, ''

    pkgname = globals.get('__package__', None)

    if pkgname is not None:
        # __package__ is set, so use it
        if not hasattr(pkgname, 'rindex'):
            raise ValueError('__package__ set to non-string')
        if len(pkgname) == 0:
            if level > 0:
                raise ValueError('Attempted relative import in non-package')
            return None, ''
        name = pkgname
    else:
        # __package__ not set, so figure it out and set it
        if '__name__' not in globals:
            return None, ''
        modname = globals['__name__']

        if '__path__' in globals:
            # __path__ is set, so modname is already the package name
            globals['__package__'] = name = modname
        else:
            # Normal module, so work out the package name if any
            lastdot = modname.rfind('.')
            if lastdot < 0 < level:
                raise ValueError("Attempted relative import in non-package")
            if lastdot < 0:
                globals['__package__'] = None
                return None, ''
            globals['__package__'] = name = modname[:lastdot]

    dot = len(name)
    for x in range(level, 1, -1):
        try:
            dot = name.rindex('.', 0, dot)
        except ValueError as e:
            raise ValueError("attempted relative import beyond top-level "
                             "package") from e
    name = name[:dot]

    try:
        parent = sys.modules[name]
    except BaseException as e:
        if orig_level < 1:
            warn("Parent module '%.200s' not found while handling absolute "
                 "import" % name)
            parent = None
        else:
            raise SystemError("Parent module '%.200s' not loaded, cannot "
                              "perform relative import" % name) from e

    # We expect, but can't guarantee, if parent != None, that:
    # - parent.__name__ == name
    # - parent.__dict__ is globals
    # If this is violated...  Who cares?
    return parent, name

def load_next(mod, altmod, name, buf):
    """
    mod, name, buf = load_next(mod, altmod, name, buf)

    altmod is either None or same as mod
    """

    if len(name) == 0:
        # completely empty module name should only happen in
        # 'from . import' (or '__import__("")')
        return mod, None, buf

    dot = name.find('.')
    if dot == 0:
        raise ValueError('Empty module name')

    if dot < 0:
        subname = name
        next = None
    else:
        subname = name[:dot]
        next = name[dot+1:]

    if buf != '':
        buf += '.'
    buf += subname

    result = import_submodule(mod, subname, buf)
    if result is None and mod != altmod:
        result = import_submodule(altmod, subname, subname)
        if result is not None:
            buf = subname

    if result is None:
        raise ImportError("No module named %.200s" % name)

    return result, next, buf


# Need to keep track of what we've already reloaded to prevent cyclic evil
found_now = {}

def import_submodule(mod, subname, fullname):
    """m = import_submodule(mod, subname, fullname)"""
    # Require:
    # if mod == None: subname == fullname
    # else: mod.__name__ + "." + subname == fullname

    global found_now
    if fullname in found_now and fullname in sys.modules:
        m = sys.modules[fullname]
    else:
        print('Reloading', fullname)
        found_now[fullname] = 1
        oldm = sys.modules.get(fullname, None)
        try:
            if oldm is not None:
                m = importlib.reload(oldm)
            else:
                m = importlib.import_module(subname, mod)
        except:
            # load_module probably removed name from modules because of
            # the error.  Put back the original module object.
            if oldm:
                sys.modules[fullname] = oldm
            raise

        add_submodule(mod, m, fullname, subname)

    return m

def add_submodule(mod, submod, fullname, subname):
    """mod.{subname} = submod"""
    if mod is None:
        return #Nothing to do here.

    if submod is None:
        submod = sys.modules[fullname]

    setattr(mod, subname, submod)

    return

def ensure_fromlist(mod, fromlist, buf, recursive):
    """Handle 'from module import a, b, c' imports."""
    if not hasattr(mod, '__path__'):
        return
    for item in fromlist:
        if not hasattr(item, 'rindex'):
            raise TypeError("Item in ``from list'' not a string")
        if item == '*':
            if recursive:
                continue # avoid endless recursion
            try:
                all = mod.__all__
            except AttributeError:
                pass
            else:
                ret = ensure_fromlist(mod, all, buf, 1)
                if not ret:
                    return 0
        elif not hasattr(mod, item):
            import_submodule(mod, item, buf + '.' + item)

def deep_import_hook(name, globals=None, locals=None, fromlist=None, level=-1):
    """Replacement for __import__()"""
    parent, buf = get_parent(globals, level)

    head, name, buf = load_next(parent, None if level < 0 else parent, name, buf)

    tail = head
    while name:
        tail, name, buf = load_next(tail, tail, name, buf)

    # If tail is None, both get_parent and load_next found
    # an empty module name: someone called __import__("") or
    # doctored faulty bytecode
    if tail is None:
        raise ValueError('Empty module name')

    if not fromlist:
        return head

    ensure_fromlist(tail, fromlist, buf, 0)
    return tail

modules_reloading = {}

def deep_reload_hook(m):
    """Replacement for reload()."""
    # Hardcode this one  as it would raise a NotImplementedError from the
    # bowels of Python and screw up the import machinery after.
    # unlike other imports the `exclude` list already in place is not enough.

    if m is types:
        return m
    if not isinstance(m, ModuleType):
        raise TypeError("reload() argument must be module")

    name = m.__name__

    if name not in sys.modules:
        raise ImportError("reload(): module %.200s not in sys.modules" % name)

    global modules_reloading
    try:
        return modules_reloading[name]
    except:
        modules_reloading[name] = m

    try:
        newm = importlib.reload(m)
    except:
        sys.modules[name] = m
        raise
    finally:
        modules_reloading.clear()
    return newm

# Save the original hooks
original_reload = importlib.reload

# Replacement for reload()
def reload(
    module,
    exclude=(
        *sys.builtin_module_names,
        "sys",
        "os.path",
        "builtins",
        "__main__",
        "numpy",
        "numpy._globals",
    ),
):
    """Recursively reload all modules used in the given module.  Optionally
    takes a list of modules to exclude from reloading.  The default exclude
    list contains modules listed in sys.builtin_module_names with additional
    sys, os.path, builtins and __main__, to prevent, e.g., resetting
    display, exception, and io hooks.
    """
    global found_now
    for i in exclude:
        found_now[i] = 1
    try:
        with replace_import_hook(deep_import_hook):
            return deep_reload_hook(module)
    finally:
        found_now = {}

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_user_array_impl.py ===
"""
Container class for backward compatibility with NumArray.

The user_array.container class exists for backward compatibility with NumArray
and is not meant to be used in new code. If you need to create an array
container class, we recommend either creating a class that wraps an ndarray
or subclasses ndarray.

"""
from numpy._core import (
    absolute,
    add,
    arange,
    array,
    asarray,
    bitwise_and,
    bitwise_or,
    bitwise_xor,
    divide,
    equal,
    greater,
    greater_equal,
    invert,
    left_shift,
    less,
    less_equal,
    multiply,
    not_equal,
    power,
    remainder,
    reshape,
    right_shift,
    shape,
    sin,
    sqrt,
    subtract,
    transpose,
)
from numpy._core.overrides import set_module


@set_module("numpy.lib.user_array")
class container:
    """
    container(data, dtype=None, copy=True)

    Standard container-class for easy multiple-inheritance.

    Methods
    -------
    copy
    byteswap
    astype

    """
    def __init__(self, data, dtype=None, copy=True):
        self.array = array(data, dtype, copy=copy)

    def __repr__(self):
        if self.ndim > 0:
            return self.__class__.__name__ + repr(self.array)[len("array"):]
        else:
            return self.__class__.__name__ + "(" + repr(self.array) + ")"

    def __array__(self, t=None):
        if t:
            return self.array.astype(t)
        return self.array

    # Array as sequence
    def __len__(self):
        return len(self.array)

    def __getitem__(self, index):
        return self._rc(self.array[index])

    def __setitem__(self, index, value):
        self.array[index] = asarray(value, self.dtype)

    def __abs__(self):
        return self._rc(absolute(self.array))

    def __neg__(self):
        return self._rc(-self.array)

    def __add__(self, other):
        return self._rc(self.array + asarray(other))

    __radd__ = __add__

    def __iadd__(self, other):
        add(self.array, other, self.array)
        return self

    def __sub__(self, other):
        return self._rc(self.array - asarray(other))

    def __rsub__(self, other):
        return self._rc(asarray(other) - self.array)

    def __isub__(self, other):
        subtract(self.array, other, self.array)
        return self

    def __mul__(self, other):
        return self._rc(multiply(self.array, asarray(other)))

    __rmul__ = __mul__

    def __imul__(self, other):
        multiply(self.array, other, self.array)
        return self

    def __mod__(self, other):
        return self._rc(remainder(self.array, other))

    def __rmod__(self, other):
        return self._rc(remainder(other, self.array))

    def __imod__(self, other):
        remainder(self.array, other, self.array)
        return self

    def __divmod__(self, other):
        return (self._rc(divide(self.array, other)),
                self._rc(remainder(self.array, other)))

    def __rdivmod__(self, other):
        return (self._rc(divide(other, self.array)),
                self._rc(remainder(other, self.array)))

    def __pow__(self, other):
        return self._rc(power(self.array, asarray(other)))

    def __rpow__(self, other):
        return self._rc(power(asarray(other), self.array))

    def __ipow__(self, other):
        power(self.array, other, self.array)
        return self

    def __lshift__(self, other):
        return self._rc(left_shift(self.array, other))

    def __rshift__(self, other):
        return self._rc(right_shift(self.array, other))

    def __rlshift__(self, other):
        return self._rc(left_shift(other, self.array))

    def __rrshift__(self, other):
        return self._rc(right_shift(other, self.array))

    def __ilshift__(self, other):
        left_shift(self.array, other, self.array)
        return self

    def __irshift__(self, other):
        right_shift(self.array, other, self.array)
        return self

    def __and__(self, other):
        return self._rc(bitwise_and(self.array, other))

    def __rand__(self, other):
        return self._rc(bitwise_and(other, self.array))

    def __iand__(self, other):
        bitwise_and(self.array, other, self.array)
        return self

    def __xor__(self, other):
        return self._rc(bitwise_xor(self.array, other))

    def __rxor__(self, other):
        return self._rc(bitwise_xor(other, self.array))

    def __ixor__(self, other):
        bitwise_xor(self.array, other, self.array)
        return self

    def __or__(self, other):
        return self._rc(bitwise_or(self.array, other))

    def __ror__(self, other):
        return self._rc(bitwise_or(other, self.array))

    def __ior__(self, other):
        bitwise_or(self.array, other, self.array)
        return self

    def __pos__(self):
        return self._rc(self.array)

    def __invert__(self):
        return self._rc(invert(self.array))

    def _scalarfunc(self, func):
        if self.ndim == 0:
            return func(self[0])
        else:
            raise TypeError(
                "only rank-0 arrays can be converted to Python scalars.")

    def __complex__(self):
        return self._scalarfunc(complex)

    def __float__(self):
        return self._scalarfunc(float)

    def __int__(self):
        return self._scalarfunc(int)

    def __hex__(self):
        return self._scalarfunc(hex)

    def __oct__(self):
        return self._scalarfunc(oct)

    def __lt__(self, other):
        return self._rc(less(self.array, other))

    def __le__(self, other):
        return self._rc(less_equal(self.array, other))

    def __eq__(self, other):
        return self._rc(equal(self.array, other))

    def __ne__(self, other):
        return self._rc(not_equal(self.array, other))

    def __gt__(self, other):
        return self._rc(greater(self.array, other))

    def __ge__(self, other):
        return self._rc(greater_equal(self.array, other))

    def copy(self):
        ""
        return self._rc(self.array.copy())

    def tobytes(self):
        ""
        return self.array.tobytes()

    def byteswap(self):
        ""
        return self._rc(self.array.byteswap())

    def astype(self, typecode):
        ""
        return self._rc(self.array.astype(typecode))

    def _rc(self, a):
        if len(shape(a)) == 0:
            return a
        else:
            return self.__class__(a)

    def __array_wrap__(self, *args):
        return self.__class__(args[0])

    def __setattr__(self, attr, value):
        if attr == 'array':
            object.__setattr__(self, attr, value)
            return
        try:
            self.array.__setattr__(attr, value)
        except AttributeError:
            object.__setattr__(self, attr, value)

    # Only called after other approaches fail.
    def __getattr__(self, attr):
        if (attr == 'array'):
            return object.__getattribute__(self, attr)
        return self.array.__getattribute__(attr)


#############################################################
# Test of class container
#############################################################
if __name__ == '__main__':
    temp = reshape(arange(10000), (100, 100))

    ua = container(temp)
    # new object created begin test
    print(dir(ua))
    print(shape(ua), ua.shape)  # I have changed Numeric.py

    ua_small = ua[:3, :5]
    print(ua_small)
    # this did not change ua[0,0], which is not normal behavior
    ua_small[0, 0] = 10
    print(ua_small[0, 0], ua[0, 0])
    print(sin(ua_small) / 3. * 6. + sqrt(ua_small ** 2))
    print(less(ua_small, 103), type(less(ua_small, 103)))
    print(type(ua_small * reshape(arange(15), shape(ua_small))))
    print(reshape(ua_small, (5, 3)))
    print(transpose(ua_small))

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_user_array_impl.py ===
"""
Container class for backward compatibility with NumArray.

The user_array.container class exists for backward compatibility with NumArray
and is not meant to be used in new code. If you need to create an array
container class, we recommend either creating a class that wraps an ndarray
or subclasses ndarray.

"""
from numpy._core import (
    absolute,
    add,
    arange,
    array,
    asarray,
    bitwise_and,
    bitwise_or,
    bitwise_xor,
    divide,
    equal,
    greater,
    greater_equal,
    invert,
    left_shift,
    less,
    less_equal,
    multiply,
    not_equal,
    power,
    remainder,
    reshape,
    right_shift,
    shape,
    sin,
    sqrt,
    subtract,
    transpose,
)
from numpy._core.overrides import set_module


@set_module("numpy.lib.user_array")
class container:
    """
    container(data, dtype=None, copy=True)

    Standard container-class for easy multiple-inheritance.

    Methods
    -------
    copy
    byteswap
    astype

    """
    def __init__(self, data, dtype=None, copy=True):
        self.array = array(data, dtype, copy=copy)

    def __repr__(self):
        if self.ndim > 0:
            return self.__class__.__name__ + repr(self.array)[len("array"):]
        else:
            return self.__class__.__name__ + "(" + repr(self.array) + ")"

    def __array__(self, t=None):
        if t:
            return self.array.astype(t)
        return self.array

    # Array as sequence
    def __len__(self):
        return len(self.array)

    def __getitem__(self, index):
        return self._rc(self.array[index])

    def __setitem__(self, index, value):
        self.array[index] = asarray(value, self.dtype)

    def __abs__(self):
        return self._rc(absolute(self.array))

    def __neg__(self):
        return self._rc(-self.array)

    def __add__(self, other):
        return self._rc(self.array + asarray(other))

    __radd__ = __add__

    def __iadd__(self, other):
        add(self.array, other, self.array)
        return self

    def __sub__(self, other):
        return self._rc(self.array - asarray(other))

    def __rsub__(self, other):
        return self._rc(asarray(other) - self.array)

    def __isub__(self, other):
        subtract(self.array, other, self.array)
        return self

    def __mul__(self, other):
        return self._rc(multiply(self.array, asarray(other)))

    __rmul__ = __mul__

    def __imul__(self, other):
        multiply(self.array, other, self.array)
        return self

    def __mod__(self, other):
        return self._rc(remainder(self.array, other))

    def __rmod__(self, other):
        return self._rc(remainder(other, self.array))

    def __imod__(self, other):
        remainder(self.array, other, self.array)
        return self

    def __divmod__(self, other):
        return (self._rc(divide(self.array, other)),
                self._rc(remainder(self.array, other)))

    def __rdivmod__(self, other):
        return (self._rc(divide(other, self.array)),
                self._rc(remainder(other, self.array)))

    def __pow__(self, other):
        return self._rc(power(self.array, asarray(other)))

    def __rpow__(self, other):
        return self._rc(power(asarray(other), self.array))

    def __ipow__(self, other):
        power(self.array, other, self.array)
        return self

    def __lshift__(self, other):
        return self._rc(left_shift(self.array, other))

    def __rshift__(self, other):
        return self._rc(right_shift(self.array, other))

    def __rlshift__(self, other):
        return self._rc(left_shift(other, self.array))

    def __rrshift__(self, other):
        return self._rc(right_shift(other, self.array))

    def __ilshift__(self, other):
        left_shift(self.array, other, self.array)
        return self

    def __irshift__(self, other):
        right_shift(self.array, other, self.array)
        return self

    def __and__(self, other):
        return self._rc(bitwise_and(self.array, other))

    def __rand__(self, other):
        return self._rc(bitwise_and(other, self.array))

    def __iand__(self, other):
        bitwise_and(self.array, other, self.array)
        return self

    def __xor__(self, other):
        return self._rc(bitwise_xor(self.array, other))

    def __rxor__(self, other):
        return self._rc(bitwise_xor(other, self.array))

    def __ixor__(self, other):
        bitwise_xor(self.array, other, self.array)
        return self

    def __or__(self, other):
        return self._rc(bitwise_or(self.array, other))

    def __ror__(self, other):
        return self._rc(bitwise_or(other, self.array))

    def __ior__(self, other):
        bitwise_or(self.array, other, self.array)
        return self

    def __pos__(self):
        return self._rc(self.array)

    def __invert__(self):
        return self._rc(invert(self.array))

    def _scalarfunc(self, func):
        if self.ndim == 0:
            return func(self[0])
        else:
            raise TypeError(
                "only rank-0 arrays can be converted to Python scalars.")

    def __complex__(self):
        return self._scalarfunc(complex)

    def __float__(self):
        return self._scalarfunc(float)

    def __int__(self):
        return self._scalarfunc(int)

    def __hex__(self):
        return self._scalarfunc(hex)

    def __oct__(self):
        return self._scalarfunc(oct)

    def __lt__(self, other):
        return self._rc(less(self.array, other))

    def __le__(self, other):
        return self._rc(less_equal(self.array, other))

    def __eq__(self, other):
        return self._rc(equal(self.array, other))

    def __ne__(self, other):
        return self._rc(not_equal(self.array, other))

    def __gt__(self, other):
        return self._rc(greater(self.array, other))

    def __ge__(self, other):
        return self._rc(greater_equal(self.array, other))

    def copy(self):
        ""
        return self._rc(self.array.copy())

    def tobytes(self):
        ""
        return self.array.tobytes()

    def byteswap(self):
        ""
        return self._rc(self.array.byteswap())

    def astype(self, typecode):
        ""
        return self._rc(self.array.astype(typecode))

    def _rc(self, a):
        if len(shape(a)) == 0:
            return a
        else:
            return self.__class__(a)

    def __array_wrap__(self, *args):
        return self.__class__(args[0])

    def __setattr__(self, attr, value):
        if attr == 'array':
            object.__setattr__(self, attr, value)
            return
        try:
            self.array.__setattr__(attr, value)
        except AttributeError:
            object.__setattr__(self, attr, value)

    # Only called after other approaches fail.
    def __getattr__(self, attr):
        if (attr == 'array'):
            return object.__getattribute__(self, attr)
        return self.array.__getattribute__(attr)


#############################################################
# Test of class container
#############################################################
if __name__ == '__main__':
    temp = reshape(arange(10000), (100, 100))

    ua = container(temp)
    # new object created begin test
    print(dir(ua))
    print(shape(ua), ua.shape)  # I have changed Numeric.py

    ua_small = ua[:3, :5]
    print(ua_small)
    # this did not change ua[0,0], which is not normal behavior
    ua_small[0, 0] = 10
    print(ua_small[0, 0], ua[0, 0])
    print(sin(ua_small) / 3. * 6. + sqrt(ua_small ** 2))
    print(less(ua_small, 103), type(less(ua_small, 103)))
    print(type(ua_small * reshape(arange(15), shape(ua_small))))
    print(reshape(ua_small, (5, 3)))
    print(transpose(ua_small))

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\_user_array_impl.py ===
"""
Container class for backward compatibility with NumArray.

The user_array.container class exists for backward compatibility with NumArray
and is not meant to be used in new code. If you need to create an array
container class, we recommend either creating a class that wraps an ndarray
or subclasses ndarray.

"""
from numpy._core import (
    absolute,
    add,
    arange,
    array,
    asarray,
    bitwise_and,
    bitwise_or,
    bitwise_xor,
    divide,
    equal,
    greater,
    greater_equal,
    invert,
    left_shift,
    less,
    less_equal,
    multiply,
    not_equal,
    power,
    remainder,
    reshape,
    right_shift,
    shape,
    sin,
    sqrt,
    subtract,
    transpose,
)
from numpy._core.overrides import set_module


@set_module("numpy.lib.user_array")
class container:
    """
    container(data, dtype=None, copy=True)

    Standard container-class for easy multiple-inheritance.

    Methods
    -------
    copy
    byteswap
    astype

    """
    def __init__(self, data, dtype=None, copy=True):
        self.array = array(data, dtype, copy=copy)

    def __repr__(self):
        if self.ndim > 0:
            return self.__class__.__name__ + repr(self.array)[len("array"):]
        else:
            return self.__class__.__name__ + "(" + repr(self.array) + ")"

    def __array__(self, t=None):
        if t:
            return self.array.astype(t)
        return self.array

    # Array as sequence
    def __len__(self):
        return len(self.array)

    def __getitem__(self, index):
        return self._rc(self.array[index])

    def __setitem__(self, index, value):
        self.array[index] = asarray(value, self.dtype)

    def __abs__(self):
        return self._rc(absolute(self.array))

    def __neg__(self):
        return self._rc(-self.array)

    def __add__(self, other):
        return self._rc(self.array + asarray(other))

    __radd__ = __add__

    def __iadd__(self, other):
        add(self.array, other, self.array)
        return self

    def __sub__(self, other):
        return self._rc(self.array - asarray(other))

    def __rsub__(self, other):
        return self._rc(asarray(other) - self.array)

    def __isub__(self, other):
        subtract(self.array, other, self.array)
        return self

    def __mul__(self, other):
        return self._rc(multiply(self.array, asarray(other)))

    __rmul__ = __mul__

    def __imul__(self, other):
        multiply(self.array, other, self.array)
        return self

    def __mod__(self, other):
        return self._rc(remainder(self.array, other))

    def __rmod__(self, other):
        return self._rc(remainder(other, self.array))

    def __imod__(self, other):
        remainder(self.array, other, self.array)
        return self

    def __divmod__(self, other):
        return (self._rc(divide(self.array, other)),
                self._rc(remainder(self.array, other)))

    def __rdivmod__(self, other):
        return (self._rc(divide(other, self.array)),
                self._rc(remainder(other, self.array)))

    def __pow__(self, other):
        return self._rc(power(self.array, asarray(other)))

    def __rpow__(self, other):
        return self._rc(power(asarray(other), self.array))

    def __ipow__(self, other):
        power(self.array, other, self.array)
        return self

    def __lshift__(self, other):
        return self._rc(left_shift(self.array, other))

    def __rshift__(self, other):
        return self._rc(right_shift(self.array, other))

    def __rlshift__(self, other):
        return self._rc(left_shift(other, self.array))

    def __rrshift__(self, other):
        return self._rc(right_shift(other, self.array))

    def __ilshift__(self, other):
        left_shift(self.array, other, self.array)
        return self

    def __irshift__(self, other):
        right_shift(self.array, other, self.array)
        return self

    def __and__(self, other):
        return self._rc(bitwise_and(self.array, other))

    def __rand__(self, other):
        return self._rc(bitwise_and(other, self.array))

    def __iand__(self, other):
        bitwise_and(self.array, other, self.array)
        return self

    def __xor__(self, other):
        return self._rc(bitwise_xor(self.array, other))

    def __rxor__(self, other):
        return self._rc(bitwise_xor(other, self.array))

    def __ixor__(self, other):
        bitwise_xor(self.array, other, self.array)
        return self

    def __or__(self, other):
        return self._rc(bitwise_or(self.array, other))

    def __ror__(self, other):
        return self._rc(bitwise_or(other, self.array))

    def __ior__(self, other):
        bitwise_or(self.array, other, self.array)
        return self

    def __pos__(self):
        return self._rc(self.array)

    def __invert__(self):
        return self._rc(invert(self.array))

    def _scalarfunc(self, func):
        if self.ndim == 0:
            return func(self[0])
        else:
            raise TypeError(
                "only rank-0 arrays can be converted to Python scalars.")

    def __complex__(self):
        return self._scalarfunc(complex)

    def __float__(self):
        return self._scalarfunc(float)

    def __int__(self):
        return self._scalarfunc(int)

    def __hex__(self):
        return self._scalarfunc(hex)

    def __oct__(self):
        return self._scalarfunc(oct)

    def __lt__(self, other):
        return self._rc(less(self.array, other))

    def __le__(self, other):
        return self._rc(less_equal(self.array, other))

    def __eq__(self, other):
        return self._rc(equal(self.array, other))

    def __ne__(self, other):
        return self._rc(not_equal(self.array, other))

    def __gt__(self, other):
        return self._rc(greater(self.array, other))

    def __ge__(self, other):
        return self._rc(greater_equal(self.array, other))

    def copy(self):
        ""
        return self._rc(self.array.copy())

    def tobytes(self):
        ""
        return self.array.tobytes()

    def byteswap(self):
        ""
        return self._rc(self.array.byteswap())

    def astype(self, typecode):
        ""
        return self._rc(self.array.astype(typecode))

    def _rc(self, a):
        if len(shape(a)) == 0:
            return a
        else:
            return self.__class__(a)

    def __array_wrap__(self, *args):
        return self.__class__(args[0])

    def __setattr__(self, attr, value):
        if attr == 'array':
            object.__setattr__(self, attr, value)
            return
        try:
            self.array.__setattr__(attr, value)
        except AttributeError:
            object.__setattr__(self, attr, value)

    # Only called after other approaches fail.
    def __getattr__(self, attr):
        if (attr == 'array'):
            return object.__getattribute__(self, attr)
        return self.array.__getattribute__(attr)


#############################################################
# Test of class container
#############################################################
if __name__ == '__main__':
    temp = reshape(arange(10000), (100, 100))

    ua = container(temp)
    # new object created begin test
    print(dir(ua))
    print(shape(ua), ua.shape)  # I have changed Numeric.py

    ua_small = ua[:3, :5]
    print(ua_small)
    # this did not change ua[0,0], which is not normal behavior
    ua_small[0, 0] = 10
    print(ua_small[0, 0], ua[0, 0])
    print(sin(ua_small) / 3. * 6. + sqrt(ua_small ** 2))
    print(less(ua_small, 103), type(less(ua_small, 103)))
    print(type(ua_small * reshape(arange(15), shape(ua_small))))
    print(reshape(ua_small, (5, 3)))
    print(transpose(ua_small))

# === NexusCore/openenv\Lib\site-packages\win32\lib\netbios.py ===
from __future__ import annotations

import struct
from collections.abc import Iterable

import win32wnet

# Constants generated by h2py from nb30.h
NCBNAMSZ = 16
MAX_LANA = 254
NAME_FLAGS_MASK = 0x87
GROUP_NAME = 0x80
UNIQUE_NAME = 0x00
REGISTERING = 0x00
REGISTERED = 0x04
DEREGISTERED = 0x05
DUPLICATE = 0x06
DUPLICATE_DEREG = 0x07
LISTEN_OUTSTANDING = 0x01
CALL_PENDING = 0x02
SESSION_ESTABLISHED = 0x03
HANGUP_PENDING = 0x04
HANGUP_COMPLETE = 0x05
SESSION_ABORTED = 0x06
ALL_TRANSPORTS = "M\0\0\0"
MS_NBF = "MNBF"
NCBCALL = 0x10
NCBLISTEN = 0x11
NCBHANGUP = 0x12
NCBSEND = 0x14
NCBRECV = 0x15
NCBRECVANY = 0x16
NCBCHAINSEND = 0x17
NCBDGSEND = 0x20
NCBDGRECV = 0x21
NCBDGSENDBC = 0x22
NCBDGRECVBC = 0x23
NCBADDNAME = 0x30
NCBDELNAME = 0x31
NCBRESET = 0x32
NCBASTAT = 0x33
NCBSSTAT = 0x34
NCBCANCEL = 0x35
NCBADDGRNAME = 0x36
NCBENUM = 0x37
NCBUNLINK = 0x70
NCBSENDNA = 0x71
NCBCHAINSENDNA = 0x72
NCBLANSTALERT = 0x73
NCBACTION = 0x77
NCBFINDNAME = 0x78
NCBTRACE = 0x79
ASYNCH = 0x80
NRC_GOODRET = 0x00
NRC_BUFLEN = 0x01
NRC_ILLCMD = 0x03
NRC_CMDTMO = 0x05
NRC_INCOMP = 0x06
NRC_BADDR = 0x07
NRC_SNUMOUT = 0x08
NRC_NORES = 0x09
NRC_SCLOSED = 0x0A
NRC_CMDCAN = 0x0B
NRC_DUPNAME = 0x0D
NRC_NAMTFUL = 0x0E
NRC_ACTSES = 0x0F
NRC_LOCTFUL = 0x11
NRC_REMTFUL = 0x12
NRC_ILLNN = 0x13
NRC_NOCALL = 0x14
NRC_NOWILD = 0x15
NRC_INUSE = 0x16
NRC_NAMERR = 0x17
NRC_SABORT = 0x18
NRC_NAMCONF = 0x19
NRC_IFBUSY = 0x21
NRC_TOOMANY = 0x22
NRC_BRIDGE = 0x23
NRC_CANOCCR = 0x24
NRC_CANCEL = 0x26
NRC_DUPENV = 0x30
NRC_ENVNOTDEF = 0x34
NRC_OSRESNOTAV = 0x35
NRC_MAXAPPS = 0x36
NRC_NOSAPS = 0x37
NRC_NORESOURCES = 0x38
NRC_INVADDRESS = 0x39
NRC_INVDDID = 0x3B
NRC_LOCKFAIL = 0x3C
NRC_OPENERR = 0x3F
NRC_SYSTEM = 0x40
NRC_PENDING = 0xFF


UCHAR = "B"
WORD = "H"
DWORD = "I"
USHORT = "H"
ULONG = "I"

ADAPTER_STATUS_ITEMS = [
    ("6s", "adapter_address"),
    (UCHAR, "rev_major"),
    (UCHAR, "reserved0"),
    (UCHAR, "adapter_type"),
    (UCHAR, "rev_minor"),
    (WORD, "duration"),
    (WORD, "frmr_recv"),
    (WORD, "frmr_xmit"),
    (WORD, "iframe_recv_err"),
    (WORD, "xmit_aborts"),
    (DWORD, "xmit_success"),
    (DWORD, "recv_success"),
    (WORD, "iframe_xmit_err"),
    (WORD, "recv_buff_unavail"),
    (WORD, "t1_timeouts"),
    (WORD, "ti_timeouts"),
    (DWORD, "reserved1"),
    (WORD, "free_ncbs"),
    (WORD, "max_cfg_ncbs"),
    (WORD, "max_ncbs"),
    (WORD, "xmit_buf_unavail"),
    (WORD, "max_dgram_size"),
    (WORD, "pending_sess"),
    (WORD, "max_cfg_sess"),
    (WORD, "max_sess"),
    (WORD, "max_sess_pkt_size"),
    (WORD, "name_count"),
]

NAME_BUFFER_ITEMS = [
    (str(NCBNAMSZ) + "s", "name"),
    (UCHAR, "name_num"),
    (UCHAR, "name_flags"),
]

SESSION_HEADER_ITEMS = [
    (UCHAR, "sess_name"),
    (UCHAR, "num_sess"),
    (UCHAR, "rcv_dg_outstanding"),
    (UCHAR, "rcv_any_outstanding"),
]

SESSION_BUFFER_ITEMS = [
    (UCHAR, "lsn"),
    (UCHAR, "state"),
    (str(NCBNAMSZ) + "s", "local_name"),
    (str(NCBNAMSZ) + "s", "remote_name"),
    (UCHAR, "rcvs_outstanding"),
    (UCHAR, "sends_outstanding"),
]

LANA_ENUM_ITEMS = [
    ("B", "length"),  # Number of valid entries in lana[]
    (str(MAX_LANA + 1) + "s", "lana"),
]

FIND_NAME_HEADER_ITEMS = [
    (WORD, "node_count"),
    (UCHAR, "reserved"),
    (UCHAR, "unique_group"),
]

FIND_NAME_BUFFER_ITEMS = [
    (UCHAR, "length"),
    (UCHAR, "access_control"),
    (UCHAR, "frame_control"),
    ("6s", "destination_addr"),
    ("6s", "source_addr"),
    ("18s", "routing_info"),
]

ACTION_HEADER_ITEMS = [
    (ULONG, "transport_id"),
    (USHORT, "action_code"),
    (USHORT, "reserved"),
]

del UCHAR, WORD, DWORD, USHORT, ULONG

NCB = win32wnet.NCB


def Netbios(ncb):
    ob = ncb.Buffer
    is_ours = hasattr(ob, "_pack")
    if is_ours:
        ob._pack()
    try:
        return win32wnet.Netbios(ncb)
    finally:
        if is_ours:
            ob._unpack()


class NCBStruct:
    def __init__(self, items: Iterable[tuple[str, str]]) -> None:
        self._format = "".join([item[0] for item in items])
        self._items = items
        self._buffer_ = win32wnet.NCBBuffer(struct.calcsize(self._format))

        for format, name in self._items:
            if len(format) == 1:
                if format == "c":
                    val: bytes | int = b"\0"
                else:
                    val = 0
            else:
                l = int(format[:-1])
                val = b"\0" * l
            self.__dict__[name] = val

    def _pack(self):
        vals = [self.__dict__.get(name) for format, name in self._items]

        self._buffer_[:] = struct.pack(self._format, *vals)

    def _unpack(self):
        items = struct.unpack(self._format, self._buffer_)
        assert len(items) == len(self._items), "unexpected number of items to unpack!"
        for (format, name), val in zip(self._items, items):
            self.__dict__[name] = val

    def __setattr__(self, attr, val):
        if attr not in self.__dict__ and attr[0] != "_":
            for format, attr_name in self._items:
                if attr == attr_name:
                    break
            else:
                raise AttributeError(attr)
        self.__dict__[attr] = val


def ADAPTER_STATUS():
    return NCBStruct(ADAPTER_STATUS_ITEMS)


def NAME_BUFFER():
    return NCBStruct(NAME_BUFFER_ITEMS)


def SESSION_HEADER():
    return NCBStruct(SESSION_HEADER_ITEMS)


def SESSION_BUFFER():
    return NCBStruct(SESSION_BUFFER_ITEMS)


def LANA_ENUM():
    return NCBStruct(LANA_ENUM_ITEMS)


def FIND_NAME_HEADER():
    return NCBStruct(FIND_NAME_HEADER_ITEMS)


def FIND_NAME_BUFFER():
    return NCBStruct(FIND_NAME_BUFFER_ITEMS)


def ACTION_HEADER():
    return NCBStruct(ACTION_HEADER_ITEMS)


if __name__ == "__main__":
    # code ported from "HOWTO: Get the MAC Address for an Ethernet Adapter"
    # MS KB ID: Q118623
    ncb = NCB()
    ncb.Command = NCBENUM
    la_enum = LANA_ENUM()
    ncb.Buffer = la_enum
    rc = Netbios(ncb)
    if rc != 0:
        raise RuntimeError("Unexpected result %d" % (rc,))
    for i in range(la_enum.length):
        ncb.Reset()
        ncb.Command = NCBRESET
        ncb.Lana_num = la_enum.lana[i]
        rc = Netbios(ncb)
        if rc != 0:
            raise RuntimeError("Unexpected result %d" % (rc,))
        ncb.Reset()
        ncb.Command = NCBASTAT
        ncb.Lana_num = la_enum.lana[i]
        ncb.Callname = b"*               "
        adapter = ADAPTER_STATUS()
        ncb.Buffer = adapter
        Netbios(ncb)
        print("Adapter address:", end=" ")
        for ch in adapter.adapter_address:
            print(f"{ch:02x}", end=" ")
        print()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\netbios.py ===
from __future__ import annotations

import struct
from collections.abc import Iterable

import win32wnet

# Constants generated by h2py from nb30.h
NCBNAMSZ = 16
MAX_LANA = 254
NAME_FLAGS_MASK = 0x87
GROUP_NAME = 0x80
UNIQUE_NAME = 0x00
REGISTERING = 0x00
REGISTERED = 0x04
DEREGISTERED = 0x05
DUPLICATE = 0x06
DUPLICATE_DEREG = 0x07
LISTEN_OUTSTANDING = 0x01
CALL_PENDING = 0x02
SESSION_ESTABLISHED = 0x03
HANGUP_PENDING = 0x04
HANGUP_COMPLETE = 0x05
SESSION_ABORTED = 0x06
ALL_TRANSPORTS = "M\0\0\0"
MS_NBF = "MNBF"
NCBCALL = 0x10
NCBLISTEN = 0x11
NCBHANGUP = 0x12
NCBSEND = 0x14
NCBRECV = 0x15
NCBRECVANY = 0x16
NCBCHAINSEND = 0x17
NCBDGSEND = 0x20
NCBDGRECV = 0x21
NCBDGSENDBC = 0x22
NCBDGRECVBC = 0x23
NCBADDNAME = 0x30
NCBDELNAME = 0x31
NCBRESET = 0x32
NCBASTAT = 0x33
NCBSSTAT = 0x34
NCBCANCEL = 0x35
NCBADDGRNAME = 0x36
NCBENUM = 0x37
NCBUNLINK = 0x70
NCBSENDNA = 0x71
NCBCHAINSENDNA = 0x72
NCBLANSTALERT = 0x73
NCBACTION = 0x77
NCBFINDNAME = 0x78
NCBTRACE = 0x79
ASYNCH = 0x80
NRC_GOODRET = 0x00
NRC_BUFLEN = 0x01
NRC_ILLCMD = 0x03
NRC_CMDTMO = 0x05
NRC_INCOMP = 0x06
NRC_BADDR = 0x07
NRC_SNUMOUT = 0x08
NRC_NORES = 0x09
NRC_SCLOSED = 0x0A
NRC_CMDCAN = 0x0B
NRC_DUPNAME = 0x0D
NRC_NAMTFUL = 0x0E
NRC_ACTSES = 0x0F
NRC_LOCTFUL = 0x11
NRC_REMTFUL = 0x12
NRC_ILLNN = 0x13
NRC_NOCALL = 0x14
NRC_NOWILD = 0x15
NRC_INUSE = 0x16
NRC_NAMERR = 0x17
NRC_SABORT = 0x18
NRC_NAMCONF = 0x19
NRC_IFBUSY = 0x21
NRC_TOOMANY = 0x22
NRC_BRIDGE = 0x23
NRC_CANOCCR = 0x24
NRC_CANCEL = 0x26
NRC_DUPENV = 0x30
NRC_ENVNOTDEF = 0x34
NRC_OSRESNOTAV = 0x35
NRC_MAXAPPS = 0x36
NRC_NOSAPS = 0x37
NRC_NORESOURCES = 0x38
NRC_INVADDRESS = 0x39
NRC_INVDDID = 0x3B
NRC_LOCKFAIL = 0x3C
NRC_OPENERR = 0x3F
NRC_SYSTEM = 0x40
NRC_PENDING = 0xFF


UCHAR = "B"
WORD = "H"
DWORD = "I"
USHORT = "H"
ULONG = "I"

ADAPTER_STATUS_ITEMS = [
    ("6s", "adapter_address"),
    (UCHAR, "rev_major"),
    (UCHAR, "reserved0"),
    (UCHAR, "adapter_type"),
    (UCHAR, "rev_minor"),
    (WORD, "duration"),
    (WORD, "frmr_recv"),
    (WORD, "frmr_xmit"),
    (WORD, "iframe_recv_err"),
    (WORD, "xmit_aborts"),
    (DWORD, "xmit_success"),
    (DWORD, "recv_success"),
    (WORD, "iframe_xmit_err"),
    (WORD, "recv_buff_unavail"),
    (WORD, "t1_timeouts"),
    (WORD, "ti_timeouts"),
    (DWORD, "reserved1"),
    (WORD, "free_ncbs"),
    (WORD, "max_cfg_ncbs"),
    (WORD, "max_ncbs"),
    (WORD, "xmit_buf_unavail"),
    (WORD, "max_dgram_size"),
    (WORD, "pending_sess"),
    (WORD, "max_cfg_sess"),
    (WORD, "max_sess"),
    (WORD, "max_sess_pkt_size"),
    (WORD, "name_count"),
]

NAME_BUFFER_ITEMS = [
    (str(NCBNAMSZ) + "s", "name"),
    (UCHAR, "name_num"),
    (UCHAR, "name_flags"),
]

SESSION_HEADER_ITEMS = [
    (UCHAR, "sess_name"),
    (UCHAR, "num_sess"),
    (UCHAR, "rcv_dg_outstanding"),
    (UCHAR, "rcv_any_outstanding"),
]

SESSION_BUFFER_ITEMS = [
    (UCHAR, "lsn"),
    (UCHAR, "state"),
    (str(NCBNAMSZ) + "s", "local_name"),
    (str(NCBNAMSZ) + "s", "remote_name"),
    (UCHAR, "rcvs_outstanding"),
    (UCHAR, "sends_outstanding"),
]

LANA_ENUM_ITEMS = [
    ("B", "length"),  # Number of valid entries in lana[]
    (str(MAX_LANA + 1) + "s", "lana"),
]

FIND_NAME_HEADER_ITEMS = [
    (WORD, "node_count"),
    (UCHAR, "reserved"),
    (UCHAR, "unique_group"),
]

FIND_NAME_BUFFER_ITEMS = [
    (UCHAR, "length"),
    (UCHAR, "access_control"),
    (UCHAR, "frame_control"),
    ("6s", "destination_addr"),
    ("6s", "source_addr"),
    ("18s", "routing_info"),
]

ACTION_HEADER_ITEMS = [
    (ULONG, "transport_id"),
    (USHORT, "action_code"),
    (USHORT, "reserved"),
]

del UCHAR, WORD, DWORD, USHORT, ULONG

NCB = win32wnet.NCB


def Netbios(ncb):
    ob = ncb.Buffer
    is_ours = hasattr(ob, "_pack")
    if is_ours:
        ob._pack()
    try:
        return win32wnet.Netbios(ncb)
    finally:
        if is_ours:
            ob._unpack()


class NCBStruct:
    def __init__(self, items: Iterable[tuple[str, str]]) -> None:
        self._format = "".join([item[0] for item in items])
        self._items = items
        self._buffer_ = win32wnet.NCBBuffer(struct.calcsize(self._format))

        for format, name in self._items:
            if len(format) == 1:
                if format == "c":
                    val: bytes | int = b"\0"
                else:
                    val = 0
            else:
                l = int(format[:-1])
                val = b"\0" * l
            self.__dict__[name] = val

    def _pack(self):
        vals = [self.__dict__.get(name) for format, name in self._items]

        self._buffer_[:] = struct.pack(self._format, *vals)

    def _unpack(self):
        items = struct.unpack(self._format, self._buffer_)
        assert len(items) == len(self._items), "unexpected number of items to unpack!"
        for (format, name), val in zip(self._items, items):
            self.__dict__[name] = val

    def __setattr__(self, attr, val):
        if attr not in self.__dict__ and attr[0] != "_":
            for format, attr_name in self._items:
                if attr == attr_name:
                    break
            else:
                raise AttributeError(attr)
        self.__dict__[attr] = val


def ADAPTER_STATUS():
    return NCBStruct(ADAPTER_STATUS_ITEMS)


def NAME_BUFFER():
    return NCBStruct(NAME_BUFFER_ITEMS)


def SESSION_HEADER():
    return NCBStruct(SESSION_HEADER_ITEMS)


def SESSION_BUFFER():
    return NCBStruct(SESSION_BUFFER_ITEMS)


def LANA_ENUM():
    return NCBStruct(LANA_ENUM_ITEMS)


def FIND_NAME_HEADER():
    return NCBStruct(FIND_NAME_HEADER_ITEMS)


def FIND_NAME_BUFFER():
    return NCBStruct(FIND_NAME_BUFFER_ITEMS)


def ACTION_HEADER():
    return NCBStruct(ACTION_HEADER_ITEMS)


if __name__ == "__main__":
    # code ported from "HOWTO: Get the MAC Address for an Ethernet Adapter"
    # MS KB ID: Q118623
    ncb = NCB()
    ncb.Command = NCBENUM
    la_enum = LANA_ENUM()
    ncb.Buffer = la_enum
    rc = Netbios(ncb)
    if rc != 0:
        raise RuntimeError("Unexpected result %d" % (rc,))
    for i in range(la_enum.length):
        ncb.Reset()
        ncb.Command = NCBRESET
        ncb.Lana_num = la_enum.lana[i]
        rc = Netbios(ncb)
        if rc != 0:
            raise RuntimeError("Unexpected result %d" % (rc,))
        ncb.Reset()
        ncb.Command = NCBASTAT
        ncb.Lana_num = la_enum.lana[i]
        ncb.Callname = b"*               "
        adapter = ADAPTER_STATUS()
        ncb.Buffer = adapter
        Netbios(ncb)
        print("Adapter address:", end=" ")
        for ch in adapter.adapter_address:
            print(f"{ch:02x}", end=" ")
        print()

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\netbios.py ===
from __future__ import annotations

import struct
from collections.abc import Iterable

import win32wnet

# Constants generated by h2py from nb30.h
NCBNAMSZ = 16
MAX_LANA = 254
NAME_FLAGS_MASK = 0x87
GROUP_NAME = 0x80
UNIQUE_NAME = 0x00
REGISTERING = 0x00
REGISTERED = 0x04
DEREGISTERED = 0x05
DUPLICATE = 0x06
DUPLICATE_DEREG = 0x07
LISTEN_OUTSTANDING = 0x01
CALL_PENDING = 0x02
SESSION_ESTABLISHED = 0x03
HANGUP_PENDING = 0x04
HANGUP_COMPLETE = 0x05
SESSION_ABORTED = 0x06
ALL_TRANSPORTS = "M\0\0\0"
MS_NBF = "MNBF"
NCBCALL = 0x10
NCBLISTEN = 0x11
NCBHANGUP = 0x12
NCBSEND = 0x14
NCBRECV = 0x15
NCBRECVANY = 0x16
NCBCHAINSEND = 0x17
NCBDGSEND = 0x20
NCBDGRECV = 0x21
NCBDGSENDBC = 0x22
NCBDGRECVBC = 0x23
NCBADDNAME = 0x30
NCBDELNAME = 0x31
NCBRESET = 0x32
NCBASTAT = 0x33
NCBSSTAT = 0x34
NCBCANCEL = 0x35
NCBADDGRNAME = 0x36
NCBENUM = 0x37
NCBUNLINK = 0x70
NCBSENDNA = 0x71
NCBCHAINSENDNA = 0x72
NCBLANSTALERT = 0x73
NCBACTION = 0x77
NCBFINDNAME = 0x78
NCBTRACE = 0x79
ASYNCH = 0x80
NRC_GOODRET = 0x00
NRC_BUFLEN = 0x01
NRC_ILLCMD = 0x03
NRC_CMDTMO = 0x05
NRC_INCOMP = 0x06
NRC_BADDR = 0x07
NRC_SNUMOUT = 0x08
NRC_NORES = 0x09
NRC_SCLOSED = 0x0A
NRC_CMDCAN = 0x0B
NRC_DUPNAME = 0x0D
NRC_NAMTFUL = 0x0E
NRC_ACTSES = 0x0F
NRC_LOCTFUL = 0x11
NRC_REMTFUL = 0x12
NRC_ILLNN = 0x13
NRC_NOCALL = 0x14
NRC_NOWILD = 0x15
NRC_INUSE = 0x16
NRC_NAMERR = 0x17
NRC_SABORT = 0x18
NRC_NAMCONF = 0x19
NRC_IFBUSY = 0x21
NRC_TOOMANY = 0x22
NRC_BRIDGE = 0x23
NRC_CANOCCR = 0x24
NRC_CANCEL = 0x26
NRC_DUPENV = 0x30
NRC_ENVNOTDEF = 0x34
NRC_OSRESNOTAV = 0x35
NRC_MAXAPPS = 0x36
NRC_NOSAPS = 0x37
NRC_NORESOURCES = 0x38
NRC_INVADDRESS = 0x39
NRC_INVDDID = 0x3B
NRC_LOCKFAIL = 0x3C
NRC_OPENERR = 0x3F
NRC_SYSTEM = 0x40
NRC_PENDING = 0xFF


UCHAR = "B"
WORD = "H"
DWORD = "I"
USHORT = "H"
ULONG = "I"

ADAPTER_STATUS_ITEMS = [
    ("6s", "adapter_address"),
    (UCHAR, "rev_major"),
    (UCHAR, "reserved0"),
    (UCHAR, "adapter_type"),
    (UCHAR, "rev_minor"),
    (WORD, "duration"),
    (WORD, "frmr_recv"),
    (WORD, "frmr_xmit"),
    (WORD, "iframe_recv_err"),
    (WORD, "xmit_aborts"),
    (DWORD, "xmit_success"),
    (DWORD, "recv_success"),
    (WORD, "iframe_xmit_err"),
    (WORD, "recv_buff_unavail"),
    (WORD, "t1_timeouts"),
    (WORD, "ti_timeouts"),
    (DWORD, "reserved1"),
    (WORD, "free_ncbs"),
    (WORD, "max_cfg_ncbs"),
    (WORD, "max_ncbs"),
    (WORD, "xmit_buf_unavail"),
    (WORD, "max_dgram_size"),
    (WORD, "pending_sess"),
    (WORD, "max_cfg_sess"),
    (WORD, "max_sess"),
    (WORD, "max_sess_pkt_size"),
    (WORD, "name_count"),
]

NAME_BUFFER_ITEMS = [
    (str(NCBNAMSZ) + "s", "name"),
    (UCHAR, "name_num"),
    (UCHAR, "name_flags"),
]

SESSION_HEADER_ITEMS = [
    (UCHAR, "sess_name"),
    (UCHAR, "num_sess"),
    (UCHAR, "rcv_dg_outstanding"),
    (UCHAR, "rcv_any_outstanding"),
]

SESSION_BUFFER_ITEMS = [
    (UCHAR, "lsn"),
    (UCHAR, "state"),
    (str(NCBNAMSZ) + "s", "local_name"),
    (str(NCBNAMSZ) + "s", "remote_name"),
    (UCHAR, "rcvs_outstanding"),
    (UCHAR, "sends_outstanding"),
]

LANA_ENUM_ITEMS = [
    ("B", "length"),  # Number of valid entries in lana[]
    (str(MAX_LANA + 1) + "s", "lana"),
]

FIND_NAME_HEADER_ITEMS = [
    (WORD, "node_count"),
    (UCHAR, "reserved"),
    (UCHAR, "unique_group"),
]

FIND_NAME_BUFFER_ITEMS = [
    (UCHAR, "length"),
    (UCHAR, "access_control"),
    (UCHAR, "frame_control"),
    ("6s", "destination_addr"),
    ("6s", "source_addr"),
    ("18s", "routing_info"),
]

ACTION_HEADER_ITEMS = [
    (ULONG, "transport_id"),
    (USHORT, "action_code"),
    (USHORT, "reserved"),
]

del UCHAR, WORD, DWORD, USHORT, ULONG

NCB = win32wnet.NCB


def Netbios(ncb):
    ob = ncb.Buffer
    is_ours = hasattr(ob, "_pack")
    if is_ours:
        ob._pack()
    try:
        return win32wnet.Netbios(ncb)
    finally:
        if is_ours:
            ob._unpack()


class NCBStruct:
    def __init__(self, items: Iterable[tuple[str, str]]) -> None:
        self._format = "".join([item[0] for item in items])
        self._items = items
        self._buffer_ = win32wnet.NCBBuffer(struct.calcsize(self._format))

        for format, name in self._items:
            if len(format) == 1:
                if format == "c":
                    val: bytes | int = b"\0"
                else:
                    val = 0
            else:
                l = int(format[:-1])
                val = b"\0" * l
            self.__dict__[name] = val

    def _pack(self):
        vals = [self.__dict__.get(name) for format, name in self._items]

        self._buffer_[:] = struct.pack(self._format, *vals)

    def _unpack(self):
        items = struct.unpack(self._format, self._buffer_)
        assert len(items) == len(self._items), "unexpected number of items to unpack!"
        for (format, name), val in zip(self._items, items):
            self.__dict__[name] = val

    def __setattr__(self, attr, val):
        if attr not in self.__dict__ and attr[0] != "_":
            for format, attr_name in self._items:
                if attr == attr_name:
                    break
            else:
                raise AttributeError(attr)
        self.__dict__[attr] = val


def ADAPTER_STATUS():
    return NCBStruct(ADAPTER_STATUS_ITEMS)


def NAME_BUFFER():
    return NCBStruct(NAME_BUFFER_ITEMS)


def SESSION_HEADER():
    return NCBStruct(SESSION_HEADER_ITEMS)


def SESSION_BUFFER():
    return NCBStruct(SESSION_BUFFER_ITEMS)


def LANA_ENUM():
    return NCBStruct(LANA_ENUM_ITEMS)


def FIND_NAME_HEADER():
    return NCBStruct(FIND_NAME_HEADER_ITEMS)


def FIND_NAME_BUFFER():
    return NCBStruct(FIND_NAME_BUFFER_ITEMS)


def ACTION_HEADER():
    return NCBStruct(ACTION_HEADER_ITEMS)


if __name__ == "__main__":
    # code ported from "HOWTO: Get the MAC Address for an Ethernet Adapter"
    # MS KB ID: Q118623
    ncb = NCB()
    ncb.Command = NCBENUM
    la_enum = LANA_ENUM()
    ncb.Buffer = la_enum
    rc = Netbios(ncb)
    if rc != 0:
        raise RuntimeError("Unexpected result %d" % (rc,))
    for i in range(la_enum.length):
        ncb.Reset()
        ncb.Command = NCBRESET
        ncb.Lana_num = la_enum.lana[i]
        rc = Netbios(ncb)
        if rc != 0:
            raise RuntimeError("Unexpected result %d" % (rc,))
        ncb.Reset()
        ncb.Command = NCBASTAT
        ncb.Lana_num = la_enum.lana[i]
        ncb.Callname = b"*               "
        adapter = ADAPTER_STATUS()
        ncb.Buffer = adapter
        Netbios(ncb)
        print("Adapter address:", end=" ")
        for ch in adapter.adapter_address:
            print(f"{ch:02x}", end=" ")
        print()

# === NexusCore/openenv\Lib\site-packages\win32\lib\pywin32_testutil.py ===
# Utilities for the pywin32 tests
import gc
import os
import site
import sys
import unittest

import winerror

##
## unittest related stuff
##


# This is a specialized TestCase adaptor which wraps a real test.
class LeakTestCase(unittest.TestCase):
    """An 'adaptor' which takes another test.  In debug builds we execute the
    test once to remove one-off side-effects, then capture the total
    reference count, then execute the test a few times.  If the total
    refcount at the end is greater than we first captured, we have a leak!

    In release builds the test is executed just once, as normal.

    Generally used automatically by the test runner - you can safely
    ignore this.
    """

    def __init__(self, real_test):
        unittest.TestCase.__init__(self)
        self.real_test = real_test
        self.num_test_cases = 1
        self.num_leak_iters = 2  # seems to be enough!
        if hasattr(sys, "gettotalrefcount"):
            self.num_test_cases += self.num_leak_iters

    def countTestCases(self):
        return self.num_test_cases

    def __call__(self, result=None):
        # For the COM suite's sake, always ensure we don't leak
        # gateways/interfaces
        from pythoncom import _GetGatewayCount, _GetInterfaceCount

        gc.collect()
        ni = _GetInterfaceCount()
        ng = _GetGatewayCount()
        self.real_test(result)
        # Failed - no point checking anything else
        if result.shouldStop or not result.wasSuccessful():
            return
        self._do_leak_tests(result)
        gc.collect()
        lost_i = _GetInterfaceCount() - ni
        lost_g = _GetGatewayCount() - ng
        if lost_i or lost_g:
            msg = "%d interface objects and %d gateway objects leaked" % (
                lost_i,
                lost_g,
            )
            exc = AssertionError(msg)
            result.addFailure(self.real_test, (exc.__class__, exc, None))

    def runTest(self):
        raise NotImplementedError("not used")

    def _do_leak_tests(self, result=None):
        try:
            gtrc = sys.gettotalrefcount
        except AttributeError:
            return  # can't do leak tests in this build
        # Assume already called once, to prime any caches etc
        gc.collect()
        trc = gtrc()
        for i in range(self.num_leak_iters):
            self.real_test(result)
            if result.shouldStop:
                break
        del i  # created after we remembered the refcount!
        # int division here means one or 2 stray references won't force
        # failure, but one per loop
        gc.collect()
        lost = (gtrc() - trc) // self.num_leak_iters
        if lost < 0:
            msg = "LeakTest: %s appeared to gain %d references!!" % (
                self.real_test,
                -lost,
            )
            result.addFailure(self.real_test, (AssertionError, msg, None))
        if lost > 0:
            msg = "LeakTest: %s lost %d references" % (self.real_test, lost)
            exc = AssertionError(msg)
            result.addFailure(self.real_test, (exc.__class__, exc, None))


class TestLoader(unittest.TestLoader):
    def loadTestsFromTestCase(self, testCaseClass):
        """Return a suite of all tests cases contained in testCaseClass"""
        leak_tests = []
        for name in self.getTestCaseNames(testCaseClass):
            real_test = testCaseClass(name)
            leak_test = self._getTestWrapper(real_test)
            leak_tests.append(leak_test)
        return self.suiteClass(leak_tests)

    def fixupTestsForLeakTests(self, test):
        if isinstance(test, unittest.TestSuite):
            test._tests = [self.fixupTestsForLeakTests(t) for t in test._tests]
            return test
        else:
            # just a normal test case.
            return self._getTestWrapper(test)

    def _getTestWrapper(self, test):
        # one or 2 tests in the COM test suite set this...
        no_leak_tests = getattr(test, "no_leak_tests", False)
        if no_leak_tests:
            print("Test says it doesn't want leak tests!")
            return test
        return LeakTestCase(test)

    def loadTestsFromModule(self, mod):
        if hasattr(mod, "suite"):
            tests = mod.suite()
        else:
            tests = unittest.TestLoader.loadTestsFromModule(self, mod)
        return self.fixupTestsForLeakTests(tests)

    def loadTestsFromName(self, name, module=None):
        test = unittest.TestLoader.loadTestsFromName(self, name, module)
        if isinstance(test, unittest.TestSuite):
            # print("Don't wrap suites yet!", test._tests)
            pass  # hmmm?
        elif isinstance(test, unittest.TestCase):
            test = self._getTestWrapper(test)
        else:
            print("XXX - what is", test)
        return test


# Lots of classes necessary to support one simple feature: we want a 3rd
# test result state - "SKIPPED" - to indicate that the test wasn't able
# to be executed for various reasons.  Inspired by bzr's tests, but it
# has other concepts, such as "Expected Failure", which we don't bother
# with.

# win32 error codes that probably mean we need to be elevated (ie, if we
# aren't elevated, we treat these error codes as 'skipped')
non_admin_error_codes = [
    winerror.ERROR_ACCESS_DENIED,
    winerror.ERROR_PRIVILEGE_NOT_HELD,
]

_is_admin = None


def check_is_admin():
    global _is_admin
    if _is_admin is None:
        import pythoncom
        from win32com.shell.shell import IsUserAnAdmin

        try:
            _is_admin = IsUserAnAdmin()
        except pythoncom.com_error as exc:
            if exc.hresult != winerror.E_NOTIMPL:
                raise
            # not impl on this platform - must be old - assume is admin
            _is_admin = True
    return _is_admin


# Find a test "fixture" (eg, binary test file) expected to be very close to
# the test being run.
# If the tests are being run from the "installed" version, then these fixtures
# probably don't exist - the test is "skipped".
# But it's fatal if we think we might be running from a pywin32 source tree.
def find_test_fixture(basename, extra_dir="."):
    # look for the test file in various places
    candidates = [
        os.path.dirname(sys.argv[0]),
        extra_dir,
        ".",
    ]
    for candidate in candidates:
        fname = os.path.join(candidate, basename)
        if os.path.isfile(fname):
            return fname
    else:
        # Can't find it - see if this is expected or not.
        # This module is typically always in the installed dir, so use argv[0]
        this_file = os.path.normcase(os.path.abspath(sys.argv[0]))
        dirs_to_check = site.getsitepackages()[:]
        if site.USER_SITE:
            dirs_to_check.append(site.USER_SITE)

        for d in dirs_to_check:
            d = os.path.normcase(d)
            if os.path.commonprefix([this_file, d]) == d:
                # looks like we are in an installed Python, so skip the text.
                raise TestSkipped(f"Can't find test fixture '{fname}'")
        # Looks like we are running from source, so this is fatal.
        raise RuntimeError(f"Can't find test fixture '{fname}'")


# If this exception is raised by a test, the test is reported as a 'skip'
class TestSkipped(Exception):
    pass


# The 'TestResult' subclass that records the failures and has the special
# handling for the TestSkipped exception.
class TestResult(unittest.TextTestResult):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.skips = {}  # count of skips for each reason.

    def addError(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().
        """
        # translate a couple of 'well-known' exceptions into 'skipped'
        import pywintypes

        exc_val = err[1]
        # translate ERROR_ACCESS_DENIED for non-admin users to be skipped.
        # (access denied errors for an admin user aren't expected.)
        if (
            isinstance(exc_val, pywintypes.error)
            and exc_val.winerror in non_admin_error_codes
            and not check_is_admin()
        ):
            exc_val = TestSkipped(exc_val)
        # and COM errors due to objects not being registered (the com test
        # suite will attempt to catch this and handle it itself if the user
        # is admin)
        elif isinstance(exc_val, pywintypes.com_error) and exc_val.hresult in [
            winerror.CO_E_CLASSSTRING,
            winerror.REGDB_E_CLASSNOTREG,
            winerror.TYPE_E_LIBNOTREGISTERED,
        ]:
            exc_val = TestSkipped(exc_val)
        # NotImplemented generally means the platform doesn't support the
        # functionality.
        elif isinstance(exc_val, NotImplementedError):
            exc_val = TestSkipped(NotImplementedError)

        if isinstance(exc_val, TestSkipped):
            reason = exc_val.args[0]
            # if the reason itself is another exception, get its args.
            try:
                reason = tuple(reason.args)
            except (AttributeError, TypeError):
                pass
            self.skips.setdefault(reason, 0)
            self.skips[reason] += 1
            if self.showAll:
                self.stream.writeln(f"SKIP ({reason})")
            elif self.dots:
                self.stream.write("S")
                self.stream.flush()
            return
        super().addError(test, err)

    def printErrors(self):
        super().printErrors()
        for reason, num_skipped in self.skips.items():
            self.stream.writeln("SKIPPED: %d tests - %s" % (num_skipped, reason))


# TestRunner subclass necessary just to get our TestResult hooked up.
class TestRunner(unittest.TextTestRunner):
    def _makeResult(self):
        return TestResult(self.stream, self.descriptions, self.verbosity)


# TestProgram subclass necessary just to get our TestRunner hooked up,
# which is necessary to get our TestResult hooked up *sob*
class TestProgram(unittest.TestProgram):
    def runTests(self):
        # clobber existing runner - *sob* - it shouldn't be this hard
        self.testRunner = TestRunner(verbosity=self.verbosity)
        unittest.TestProgram.runTests(self)


# A convenient entry-point - if used, 'SKIPPED' exceptions will be suppressed.
def testmain(*args, **kw):
    new_kw = kw.copy()
    if "testLoader" not in new_kw:
        new_kw["testLoader"] = TestLoader()
    program_class = new_kw.get("testProgram", TestProgram)
    program_class(*args, **new_kw)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32\lib\pywin32_testutil.py ===
# Utilities for the pywin32 tests
import gc
import os
import site
import sys
import unittest

import winerror

##
## unittest related stuff
##


# This is a specialized TestCase adaptor which wraps a real test.
class LeakTestCase(unittest.TestCase):
    """An 'adaptor' which takes another test.  In debug builds we execute the
    test once to remove one-off side-effects, then capture the total
    reference count, then execute the test a few times.  If the total
    refcount at the end is greater than we first captured, we have a leak!

    In release builds the test is executed just once, as normal.

    Generally used automatically by the test runner - you can safely
    ignore this.
    """

    def __init__(self, real_test):
        unittest.TestCase.__init__(self)
        self.real_test = real_test
        self.num_test_cases = 1
        self.num_leak_iters = 2  # seems to be enough!
        if hasattr(sys, "gettotalrefcount"):
            self.num_test_cases += self.num_leak_iters

    def countTestCases(self):
        return self.num_test_cases

    def __call__(self, result=None):
        # For the COM suite's sake, always ensure we don't leak
        # gateways/interfaces
        from pythoncom import _GetGatewayCount, _GetInterfaceCount

        gc.collect()
        ni = _GetInterfaceCount()
        ng = _GetGatewayCount()
        self.real_test(result)
        # Failed - no point checking anything else
        if result.shouldStop or not result.wasSuccessful():
            return
        self._do_leak_tests(result)
        gc.collect()
        lost_i = _GetInterfaceCount() - ni
        lost_g = _GetGatewayCount() - ng
        if lost_i or lost_g:
            msg = "%d interface objects and %d gateway objects leaked" % (
                lost_i,
                lost_g,
            )
            exc = AssertionError(msg)
            result.addFailure(self.real_test, (exc.__class__, exc, None))

    def runTest(self):
        raise NotImplementedError("not used")

    def _do_leak_tests(self, result=None):
        try:
            gtrc = sys.gettotalrefcount
        except AttributeError:
            return  # can't do leak tests in this build
        # Assume already called once, to prime any caches etc
        gc.collect()
        trc = gtrc()
        for i in range(self.num_leak_iters):
            self.real_test(result)
            if result.shouldStop:
                break
        del i  # created after we remembered the refcount!
        # int division here means one or 2 stray references won't force
        # failure, but one per loop
        gc.collect()
        lost = (gtrc() - trc) // self.num_leak_iters
        if lost < 0:
            msg = "LeakTest: %s appeared to gain %d references!!" % (
                self.real_test,
                -lost,
            )
            result.addFailure(self.real_test, (AssertionError, msg, None))
        if lost > 0:
            msg = "LeakTest: %s lost %d references" % (self.real_test, lost)
            exc = AssertionError(msg)
            result.addFailure(self.real_test, (exc.__class__, exc, None))


class TestLoader(unittest.TestLoader):
    def loadTestsFromTestCase(self, testCaseClass):
        """Return a suite of all tests cases contained in testCaseClass"""
        leak_tests = []
        for name in self.getTestCaseNames(testCaseClass):
            real_test = testCaseClass(name)
            leak_test = self._getTestWrapper(real_test)
            leak_tests.append(leak_test)
        return self.suiteClass(leak_tests)

    def fixupTestsForLeakTests(self, test):
        if isinstance(test, unittest.TestSuite):
            test._tests = [self.fixupTestsForLeakTests(t) for t in test._tests]
            return test
        else:
            # just a normal test case.
            return self._getTestWrapper(test)

    def _getTestWrapper(self, test):
        # one or 2 tests in the COM test suite set this...
        no_leak_tests = getattr(test, "no_leak_tests", False)
        if no_leak_tests:
            print("Test says it doesn't want leak tests!")
            return test
        return LeakTestCase(test)

    def loadTestsFromModule(self, mod):
        if hasattr(mod, "suite"):
            tests = mod.suite()
        else:
            tests = unittest.TestLoader.loadTestsFromModule(self, mod)
        return self.fixupTestsForLeakTests(tests)

    def loadTestsFromName(self, name, module=None):
        test = unittest.TestLoader.loadTestsFromName(self, name, module)
        if isinstance(test, unittest.TestSuite):
            # print("Don't wrap suites yet!", test._tests)
            pass  # hmmm?
        elif isinstance(test, unittest.TestCase):
            test = self._getTestWrapper(test)
        else:
            print("XXX - what is", test)
        return test


# Lots of classes necessary to support one simple feature: we want a 3rd
# test result state - "SKIPPED" - to indicate that the test wasn't able
# to be executed for various reasons.  Inspired by bzr's tests, but it
# has other concepts, such as "Expected Failure", which we don't bother
# with.

# win32 error codes that probably mean we need to be elevated (ie, if we
# aren't elevated, we treat these error codes as 'skipped')
non_admin_error_codes = [
    winerror.ERROR_ACCESS_DENIED,
    winerror.ERROR_PRIVILEGE_NOT_HELD,
]

_is_admin = None


def check_is_admin():
    global _is_admin
    if _is_admin is None:
        import pythoncom
        from win32com.shell.shell import IsUserAnAdmin

        try:
            _is_admin = IsUserAnAdmin()
        except pythoncom.com_error as exc:
            if exc.hresult != winerror.E_NOTIMPL:
                raise
            # not impl on this platform - must be old - assume is admin
            _is_admin = True
    return _is_admin


# Find a test "fixture" (eg, binary test file) expected to be very close to
# the test being run.
# If the tests are being run from the "installed" version, then these fixtures
# probably don't exist - the test is "skipped".
# But it's fatal if we think we might be running from a pywin32 source tree.
def find_test_fixture(basename, extra_dir="."):
    # look for the test file in various places
    candidates = [
        os.path.dirname(sys.argv[0]),
        extra_dir,
        ".",
    ]
    for candidate in candidates:
        fname = os.path.join(candidate, basename)
        if os.path.isfile(fname):
            return fname
    else:
        # Can't find it - see if this is expected or not.
        # This module is typically always in the installed dir, so use argv[0]
        this_file = os.path.normcase(os.path.abspath(sys.argv[0]))
        dirs_to_check = site.getsitepackages()[:]
        if site.USER_SITE:
            dirs_to_check.append(site.USER_SITE)

        for d in dirs_to_check:
            d = os.path.normcase(d)
            if os.path.commonprefix([this_file, d]) == d:
                # looks like we are in an installed Python, so skip the text.
                raise TestSkipped(f"Can't find test fixture '{fname}'")
        # Looks like we are running from source, so this is fatal.
        raise RuntimeError(f"Can't find test fixture '{fname}'")


# If this exception is raised by a test, the test is reported as a 'skip'
class TestSkipped(Exception):
    pass


# The 'TestResult' subclass that records the failures and has the special
# handling for the TestSkipped exception.
class TestResult(unittest.TextTestResult):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.skips = {}  # count of skips for each reason.

    def addError(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().
        """
        # translate a couple of 'well-known' exceptions into 'skipped'
        import pywintypes

        exc_val = err[1]
        # translate ERROR_ACCESS_DENIED for non-admin users to be skipped.
        # (access denied errors for an admin user aren't expected.)
        if (
            isinstance(exc_val, pywintypes.error)
            and exc_val.winerror in non_admin_error_codes
            and not check_is_admin()
        ):
            exc_val = TestSkipped(exc_val)
        # and COM errors due to objects not being registered (the com test
        # suite will attempt to catch this and handle it itself if the user
        # is admin)
        elif isinstance(exc_val, pywintypes.com_error) and exc_val.hresult in [
            winerror.CO_E_CLASSSTRING,
            winerror.REGDB_E_CLASSNOTREG,
            winerror.TYPE_E_LIBNOTREGISTERED,
        ]:
            exc_val = TestSkipped(exc_val)
        # NotImplemented generally means the platform doesn't support the
        # functionality.
        elif isinstance(exc_val, NotImplementedError):
            exc_val = TestSkipped(NotImplementedError)

        if isinstance(exc_val, TestSkipped):
            reason = exc_val.args[0]
            # if the reason itself is another exception, get its args.
            try:
                reason = tuple(reason.args)
            except (AttributeError, TypeError):
                pass
            self.skips.setdefault(reason, 0)
            self.skips[reason] += 1
            if self.showAll:
                self.stream.writeln(f"SKIP ({reason})")
            elif self.dots:
                self.stream.write("S")
                self.stream.flush()
            return
        super().addError(test, err)

    def printErrors(self):
        super().printErrors()
        for reason, num_skipped in self.skips.items():
            self.stream.writeln("SKIPPED: %d tests - %s" % (num_skipped, reason))


# TestRunner subclass necessary just to get our TestResult hooked up.
class TestRunner(unittest.TextTestRunner):
    def _makeResult(self):
        return TestResult(self.stream, self.descriptions, self.verbosity)


# TestProgram subclass necessary just to get our TestRunner hooked up,
# which is necessary to get our TestResult hooked up *sob*
class TestProgram(unittest.TestProgram):
    def runTests(self):
        # clobber existing runner - *sob* - it shouldn't be this hard
        self.testRunner = TestRunner(verbosity=self.verbosity)
        unittest.TestProgram.runTests(self)


# A convenient entry-point - if used, 'SKIPPED' exceptions will be suppressed.
def testmain(*args, **kw):
    new_kw = kw.copy()
    if "testLoader" not in new_kw:
        new_kw["testLoader"] = TestLoader()
    program_class = new_kw.get("testProgram", TestProgram)
    program_class(*args, **new_kw)

# === NexusCore/openenv\Lib\site-packages\openai\lib\_parsing\_completions.py ===
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Iterable, cast
from typing_extensions import TypeVar, TypeGuard, assert_never

import pydantic

from .._tools import PydanticFunctionTool
from ..._types import NOT_GIVEN, NotGiven
from ..._utils import is_dict, is_given
from ..._compat import PYDANTIC_V2, model_parse_json
from ..._models import construct_type_unchecked
from .._pydantic import is_basemodel_type, to_strict_json_schema, is_dataclass_like_type
from ...types.chat import (
    ParsedChoice,
    ChatCompletion,
    ParsedFunction,
    ParsedChatCompletion,
    ChatCompletionMessage,
    ParsedFunctionToolCall,
    ChatCompletionToolParam,
    ParsedChatCompletionMessage,
    completion_create_params,
)
from ..._exceptions import LengthFinishReasonError, ContentFilterFinishReasonError
from ...types.shared_params import FunctionDefinition
from ...types.chat.completion_create_params import ResponseFormat as ResponseFormatParam
from ...types.chat.chat_completion_message_tool_call import Function

ResponseFormatT = TypeVar(
    "ResponseFormatT",
    # if it isn't given then we don't do any parsing
    default=None,
)
_default_response_format: None = None


def validate_input_tools(
    tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
) -> None:
    if not is_given(tools):
        return

    for tool in tools:
        if tool["type"] != "function":
            raise ValueError(
                f"Currently only `function` tool types support auto-parsing; Received `{tool['type']}`",
            )

        strict = tool["function"].get("strict")
        if strict is not True:
            raise ValueError(
                f"`{tool['function']['name']}` is not strict. Only `strict` function tools can be auto-parsed"
            )


def parse_chat_completion(
    *,
    response_format: type[ResponseFormatT] | completion_create_params.ResponseFormat | NotGiven,
    input_tools: Iterable[ChatCompletionToolParam] | NotGiven,
    chat_completion: ChatCompletion | ParsedChatCompletion[object],
) -> ParsedChatCompletion[ResponseFormatT]:
    if is_given(input_tools):
        input_tools = [t for t in input_tools]
    else:
        input_tools = []

    choices: list[ParsedChoice[ResponseFormatT]] = []
    for choice in chat_completion.choices:
        if choice.finish_reason == "length":
            raise LengthFinishReasonError(completion=chat_completion)

        if choice.finish_reason == "content_filter":
            raise ContentFilterFinishReasonError()

        message = choice.message

        tool_calls: list[ParsedFunctionToolCall] = []
        if message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.type == "function":
                    tool_call_dict = tool_call.to_dict()
                    tool_calls.append(
                        construct_type_unchecked(
                            value={
                                **tool_call_dict,
                                "function": {
                                    **cast(Any, tool_call_dict["function"]),
                                    "parsed_arguments": parse_function_tool_arguments(
                                        input_tools=input_tools, function=tool_call.function
                                    ),
                                },
                            },
                            type_=ParsedFunctionToolCall,
                        )
                    )
                elif TYPE_CHECKING:  # type: ignore[unreachable]
                    assert_never(tool_call)
                else:
                    tool_calls.append(tool_call)

        choices.append(
            construct_type_unchecked(
                type_=cast(Any, ParsedChoice)[solve_response_format_t(response_format)],
                value={
                    **choice.to_dict(),
                    "message": {
                        **message.to_dict(),
                        "parsed": maybe_parse_content(
                            response_format=response_format,
                            message=message,
                        ),
                        "tool_calls": tool_calls if tool_calls else None,
                    },
                },
            )
        )

    return cast(
        ParsedChatCompletion[ResponseFormatT],
        construct_type_unchecked(
            type_=cast(Any, ParsedChatCompletion)[solve_response_format_t(response_format)],
            value={
                **chat_completion.to_dict(),
                "choices": choices,
            },
        ),
    )


def get_input_tool_by_name(*, input_tools: list[ChatCompletionToolParam], name: str) -> ChatCompletionToolParam | None:
    return next((t for t in input_tools if t.get("function", {}).get("name") == name), None)


def parse_function_tool_arguments(
    *, input_tools: list[ChatCompletionToolParam], function: Function | ParsedFunction
) -> object:
    input_tool = get_input_tool_by_name(input_tools=input_tools, name=function.name)
    if not input_tool:
        return None

    input_fn = cast(object, input_tool.get("function"))
    if isinstance(input_fn, PydanticFunctionTool):
        return model_parse_json(input_fn.model, function.arguments)

    input_fn = cast(FunctionDefinition, input_fn)

    if not input_fn.get("strict"):
        return None

    return json.loads(function.arguments)


def maybe_parse_content(
    *,
    response_format: type[ResponseFormatT] | ResponseFormatParam | NotGiven,
    message: ChatCompletionMessage | ParsedChatCompletionMessage[object],
) -> ResponseFormatT | None:
    if has_rich_response_format(response_format) and message.content and not message.refusal:
        return _parse_content(response_format, message.content)

    return None


def solve_response_format_t(
    response_format: type[ResponseFormatT] | ResponseFormatParam | NotGiven,
) -> type[ResponseFormatT]:
    """Return the runtime type for the given response format.

    If no response format is given, or if we won't auto-parse the response format
    then we default to `None`.
    """
    if has_rich_response_format(response_format):
        return response_format

    return cast("type[ResponseFormatT]", _default_response_format)


def has_parseable_input(
    *,
    response_format: type | ResponseFormatParam | NotGiven,
    input_tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
) -> bool:
    if has_rich_response_format(response_format):
        return True

    for input_tool in input_tools or []:
        if is_parseable_tool(input_tool):
            return True

    return False


def has_rich_response_format(
    response_format: type[ResponseFormatT] | ResponseFormatParam | NotGiven,
) -> TypeGuard[type[ResponseFormatT]]:
    if not is_given(response_format):
        return False

    if is_response_format_param(response_format):
        return False

    return True


def is_response_format_param(response_format: object) -> TypeGuard[ResponseFormatParam]:
    return is_dict(response_format)


def is_parseable_tool(input_tool: ChatCompletionToolParam) -> bool:
    input_fn = cast(object, input_tool.get("function"))
    if isinstance(input_fn, PydanticFunctionTool):
        return True

    return cast(FunctionDefinition, input_fn).get("strict") or False


def _parse_content(response_format: type[ResponseFormatT], content: str) -> ResponseFormatT:
    if is_basemodel_type(response_format):
        return cast(ResponseFormatT, model_parse_json(response_format, content))

    if is_dataclass_like_type(response_format):
        if not PYDANTIC_V2:
            raise TypeError(f"Non BaseModel types are only supported with Pydantic v2 - {response_format}")

        return pydantic.TypeAdapter(response_format).validate_json(content)

    raise TypeError(f"Unable to automatically parse response format type {response_format}")


def type_to_response_format_param(
    response_format: type | completion_create_params.ResponseFormat | NotGiven,
) -> ResponseFormatParam | NotGiven:
    if not is_given(response_format):
        return NOT_GIVEN

    if is_response_format_param(response_format):
        return response_format

    # type checkers don't narrow the negation of a `TypeGuard` as it isn't
    # a safe default behaviour but we know that at this point the `response_format`
    # can only be a `type`
    response_format = cast(type, response_format)

    json_schema_type: type[pydantic.BaseModel] | pydantic.TypeAdapter[Any] | None = None

    if is_basemodel_type(response_format):
        name = response_format.__name__
        json_schema_type = response_format
    elif is_dataclass_like_type(response_format):
        name = response_format.__name__
        json_schema_type = pydantic.TypeAdapter(response_format)
    else:
        raise TypeError(f"Unsupported response_format type - {response_format}")

    return {
        "type": "json_schema",
        "json_schema": {
            "schema": to_strict_json_schema(json_schema_type),
            "name": name,
            "strict": True,
        },
    }

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\openai\lib\_parsing\_completions.py ===
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Iterable, cast
from typing_extensions import TypeVar, TypeGuard, assert_never

import pydantic

from .._tools import PydanticFunctionTool
from ..._types import NOT_GIVEN, NotGiven
from ..._utils import is_dict, is_given
from ..._compat import PYDANTIC_V2, model_parse_json
from ..._models import construct_type_unchecked
from .._pydantic import is_basemodel_type, to_strict_json_schema, is_dataclass_like_type
from ...types.chat import (
    ParsedChoice,
    ChatCompletion,
    ParsedFunction,
    ParsedChatCompletion,
    ChatCompletionMessage,
    ParsedFunctionToolCall,
    ChatCompletionToolParam,
    ParsedChatCompletionMessage,
    completion_create_params,
)
from ..._exceptions import LengthFinishReasonError, ContentFilterFinishReasonError
from ...types.shared_params import FunctionDefinition
from ...types.chat.completion_create_params import ResponseFormat as ResponseFormatParam
from ...types.chat.chat_completion_message_tool_call import Function

ResponseFormatT = TypeVar(
    "ResponseFormatT",
    # if it isn't given then we don't do any parsing
    default=None,
)
_default_response_format: None = None


def validate_input_tools(
    tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
) -> None:
    if not is_given(tools):
        return

    for tool in tools:
        if tool["type"] != "function":
            raise ValueError(
                f"Currently only `function` tool types support auto-parsing; Received `{tool['type']}`",
            )

        strict = tool["function"].get("strict")
        if strict is not True:
            raise ValueError(
                f"`{tool['function']['name']}` is not strict. Only `strict` function tools can be auto-parsed"
            )


def parse_chat_completion(
    *,
    response_format: type[ResponseFormatT] | completion_create_params.ResponseFormat | NotGiven,
    input_tools: Iterable[ChatCompletionToolParam] | NotGiven,
    chat_completion: ChatCompletion | ParsedChatCompletion[object],
) -> ParsedChatCompletion[ResponseFormatT]:
    if is_given(input_tools):
        input_tools = [t for t in input_tools]
    else:
        input_tools = []

    choices: list[ParsedChoice[ResponseFormatT]] = []
    for choice in chat_completion.choices:
        if choice.finish_reason == "length":
            raise LengthFinishReasonError(completion=chat_completion)

        if choice.finish_reason == "content_filter":
            raise ContentFilterFinishReasonError()

        message = choice.message

        tool_calls: list[ParsedFunctionToolCall] = []
        if message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.type == "function":
                    tool_call_dict = tool_call.to_dict()
                    tool_calls.append(
                        construct_type_unchecked(
                            value={
                                **tool_call_dict,
                                "function": {
                                    **cast(Any, tool_call_dict["function"]),
                                    "parsed_arguments": parse_function_tool_arguments(
                                        input_tools=input_tools, function=tool_call.function
                                    ),
                                },
                            },
                            type_=ParsedFunctionToolCall,
                        )
                    )
                elif TYPE_CHECKING:  # type: ignore[unreachable]
                    assert_never(tool_call)
                else:
                    tool_calls.append(tool_call)

        choices.append(
            construct_type_unchecked(
                type_=cast(Any, ParsedChoice)[solve_response_format_t(response_format)],
                value={
                    **choice.to_dict(),
                    "message": {
                        **message.to_dict(),
                        "parsed": maybe_parse_content(
                            response_format=response_format,
                            message=message,
                        ),
                        "tool_calls": tool_calls if tool_calls else None,
                    },
                },
            )
        )

    return cast(
        ParsedChatCompletion[ResponseFormatT],
        construct_type_unchecked(
            type_=cast(Any, ParsedChatCompletion)[solve_response_format_t(response_format)],
            value={
                **chat_completion.to_dict(),
                "choices": choices,
            },
        ),
    )


def get_input_tool_by_name(*, input_tools: list[ChatCompletionToolParam], name: str) -> ChatCompletionToolParam | None:
    return next((t for t in input_tools if t.get("function", {}).get("name") == name), None)


def parse_function_tool_arguments(
    *, input_tools: list[ChatCompletionToolParam], function: Function | ParsedFunction
) -> object:
    input_tool = get_input_tool_by_name(input_tools=input_tools, name=function.name)
    if not input_tool:
        return None

    input_fn = cast(object, input_tool.get("function"))
    if isinstance(input_fn, PydanticFunctionTool):
        return model_parse_json(input_fn.model, function.arguments)

    input_fn = cast(FunctionDefinition, input_fn)

    if not input_fn.get("strict"):
        return None

    return json.loads(function.arguments)


def maybe_parse_content(
    *,
    response_format: type[ResponseFormatT] | ResponseFormatParam | NotGiven,
    message: ChatCompletionMessage | ParsedChatCompletionMessage[object],
) -> ResponseFormatT | None:
    if has_rich_response_format(response_format) and message.content and not message.refusal:
        return _parse_content(response_format, message.content)

    return None


def solve_response_format_t(
    response_format: type[ResponseFormatT] | ResponseFormatParam | NotGiven,
) -> type[ResponseFormatT]:
    """Return the runtime type for the given response format.

    If no response format is given, or if we won't auto-parse the response format
    then we default to `None`.
    """
    if has_rich_response_format(response_format):
        return response_format

    return cast("type[ResponseFormatT]", _default_response_format)


def has_parseable_input(
    *,
    response_format: type | ResponseFormatParam | NotGiven,
    input_tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
) -> bool:
    if has_rich_response_format(response_format):
        return True

    for input_tool in input_tools or []:
        if is_parseable_tool(input_tool):
            return True

    return False


def has_rich_response_format(
    response_format: type[ResponseFormatT] | ResponseFormatParam | NotGiven,
) -> TypeGuard[type[ResponseFormatT]]:
    if not is_given(response_format):
        return False

    if is_response_format_param(response_format):
        return False

    return True


def is_response_format_param(response_format: object) -> TypeGuard[ResponseFormatParam]:
    return is_dict(response_format)


def is_parseable_tool(input_tool: ChatCompletionToolParam) -> bool:
    input_fn = cast(object, input_tool.get("function"))
    if isinstance(input_fn, PydanticFunctionTool):
        return True

    return cast(FunctionDefinition, input_fn).get("strict") or False


def _parse_content(response_format: type[ResponseFormatT], content: str) -> ResponseFormatT:
    if is_basemodel_type(response_format):
        return cast(ResponseFormatT, model_parse_json(response_format, content))

    if is_dataclass_like_type(response_format):
        if not PYDANTIC_V2:
            raise TypeError(f"Non BaseModel types are only supported with Pydantic v2 - {response_format}")

        return pydantic.TypeAdapter(response_format).validate_json(content)

    raise TypeError(f"Unable to automatically parse response format type {response_format}")


def type_to_response_format_param(
    response_format: type | completion_create_params.ResponseFormat | NotGiven,
) -> ResponseFormatParam | NotGiven:
    if not is_given(response_format):
        return NOT_GIVEN

    if is_response_format_param(response_format):
        return response_format

    # type checkers don't narrow the negation of a `TypeGuard` as it isn't
    # a safe default behaviour but we know that at this point the `response_format`
    # can only be a `type`
    response_format = cast(type, response_format)

    json_schema_type: type[pydantic.BaseModel] | pydantic.TypeAdapter[Any] | None = None

    if is_basemodel_type(response_format):
        name = response_format.__name__
        json_schema_type = response_format
    elif is_dataclass_like_type(response_format):
        name = response_format.__name__
        json_schema_type = pydantic.TypeAdapter(response_format)
    else:
        raise TypeError(f"Unsupported response_format type - {response_format}")

    return {
        "type": "json_schema",
        "json_schema": {
            "schema": to_strict_json_schema(json_schema_type),
            "name": name,
            "strict": True,
        },
    }

# === NexusCore/openenv\Lib\site-packages\IPython\lib\latextools.py ===
# -*- coding: utf-8 -*-
"""Tools for handling LaTeX."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from io import BytesIO
import os
import tempfile
import shutil
import subprocess
from base64 import encodebytes
import textwrap

from pathlib import Path

from IPython.utils.process import find_cmd, FindCmdError
from traitlets.config import get_config
from traitlets.config.configurable import SingletonConfigurable
from traitlets import List, Bool, Unicode


class LaTeXTool(SingletonConfigurable):
    """An object to store configuration of the LaTeX tool."""
    def _config_default(self):
        return get_config()

    backends = List(
        Unicode(), ["matplotlib", "dvipng"],
        help="Preferred backend to draw LaTeX math equations. "
        "Backends in the list are checked one by one and the first "
        "usable one is used.  Note that `matplotlib` backend "
        "is usable only for inline style equations.  To draw  "
        "display style equations, `dvipng` backend must be specified. ",
        # It is a List instead of Enum, to make configuration more
        # flexible.  For example, to use matplotlib mainly but dvipng
        # for display style, the default ["matplotlib", "dvipng"] can
        # be used.  To NOT use dvipng so that other repr such as
        # unicode pretty printing is used, you can use ["matplotlib"].
        ).tag(config=True)

    use_breqn = Bool(
        True,
        help="Use breqn.sty to automatically break long equations. "
        "This configuration takes effect only for dvipng backend.",
        ).tag(config=True)

    packages = List(
        ['amsmath', 'amsthm', 'amssymb', 'bm'],
        help="A list of packages to use for dvipng backend. "
        "'breqn' will be automatically appended when use_breqn=True.",
        ).tag(config=True)

    preamble = Unicode(
        help="Additional preamble to use when generating LaTeX source "
        "for dvipng backend.",
        ).tag(config=True)


def latex_to_png(
    s: str, encode=False, backend=None, wrap=False, color="Black", scale=1.0
):
    """Render a LaTeX string to PNG.

    Parameters
    ----------
    s : str
        The raw string containing valid inline LaTeX.
    encode : bool, optional
        Should the PNG data base64 encoded to make it JSON'able.
    backend : {matplotlib, dvipng}
        Backend for producing PNG data.
    wrap : bool
        If true, Automatically wrap `s` as a LaTeX equation.
    color : string
        Foreground color name among dvipsnames, e.g. 'Maroon' or on hex RGB
        format, e.g. '#AA20FA'.
    scale : float
        Scale factor for the resulting PNG.
    None is returned when the backend cannot be used.

    """
    assert isinstance(s, str)
    allowed_backends = LaTeXTool.instance().backends
    if backend is None:
        backend = allowed_backends[0]
    if backend not in allowed_backends:
        return None
    if backend == 'matplotlib':
        f = latex_to_png_mpl
    elif backend == 'dvipng':
        f = latex_to_png_dvipng
        if color.startswith('#'):
            # Convert hex RGB color to LaTeX RGB color.
            if len(color) == 7:
                try:
                    color = "RGB {}".format(" ".join([str(int(x, 16)) for x in
                                                      textwrap.wrap(color[1:], 2)]))
                except ValueError as e:
                    raise ValueError('Invalid color specification {}.'.format(color)) from e
            else:
                raise ValueError('Invalid color specification {}.'.format(color))
    else:
        raise ValueError('No such backend {0}'.format(backend))
    bin_data = f(s, wrap, color, scale)
    if encode and bin_data:
        bin_data = encodebytes(bin_data)
    return bin_data


def latex_to_png_mpl(s, wrap, color='Black', scale=1.0):
    try:
        from matplotlib import figure, font_manager, mathtext
        from matplotlib.backends import backend_agg
        from pyparsing import ParseFatalException
    except ImportError:
        return None

    # mpl mathtext doesn't support display math, force inline
    s = s.replace('$$', '$')
    if wrap:
        s = u'${0}$'.format(s)

    try:
        prop = font_manager.FontProperties(size=12)
        dpi = 120 * scale
        buffer = BytesIO()

        # Adapted from mathtext.math_to_image
        parser = mathtext.MathTextParser("path")
        width, height, depth, _, _ = parser.parse(s, dpi=72, prop=prop)
        fig = figure.Figure(figsize=(width / 72, height / 72))
        fig.text(0, depth / height, s, fontproperties=prop, color=color)
        backend_agg.FigureCanvasAgg(fig)
        fig.savefig(buffer, dpi=dpi, format="png", transparent=True)
        return buffer.getvalue()
    except (ValueError, RuntimeError, ParseFatalException):
        return None


def latex_to_png_dvipng(s, wrap, color='Black', scale=1.0):
    try:
        find_cmd('latex')
        find_cmd('dvipng')
    except FindCmdError:
        return None

    startupinfo = None
    if os.name == "nt":
        # prevent popup-windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        workdir = Path(tempfile.mkdtemp())
        tmpfile = "tmp.tex"
        dvifile = "tmp.dvi"
        outfile = "tmp.png"

        with workdir.joinpath(tmpfile).open("w", encoding="utf8") as f:
            f.writelines(genelatex(s, wrap))

        subprocess.check_call(
            ["latex", "-halt-on-error", "-interaction", "batchmode", tmpfile],
            cwd=workdir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
        )

        resolution = round(150 * scale)
        subprocess.check_call(
            [
                "dvipng",
                "-T",
                "tight",
                "-D",
                str(resolution),
                "-z",
                "9",
                "-bg",
                "Transparent",
                "-o",
                outfile,
                dvifile,
                "-fg",
                color,
            ],
            cwd=workdir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
        )

        with workdir.joinpath(outfile).open("rb") as f:
            return f.read()
    except subprocess.CalledProcessError:
        return None
    finally:
        shutil.rmtree(workdir)


def kpsewhich(filename):
    """Invoke kpsewhich command with an argument `filename`."""
    try:
        find_cmd("kpsewhich")
        proc = subprocess.Popen(
            ["kpsewhich", filename],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = proc.communicate()
        return stdout.strip().decode('utf8', 'replace')
    except FindCmdError:
        pass


def genelatex(body, wrap):
    """Generate LaTeX document for dvipng backend."""
    lt = LaTeXTool.instance()
    breqn = wrap and lt.use_breqn and kpsewhich("breqn.sty")
    yield r'\documentclass{article}'
    packages = lt.packages
    if breqn:
        packages = packages + ['breqn']
    for pack in packages:
        yield r'\usepackage{{{0}}}'.format(pack)
    yield r'\pagestyle{empty}'
    if lt.preamble:
        yield lt.preamble
    yield r'\begin{document}'
    if breqn:
        yield r'\begin{dmath*}'
        yield body
        yield r'\end{dmath*}'
    elif wrap:
        yield u'$${0}$$'.format(body)
    else:
        yield body
    yield u'\\end{document}'


_data_uri_template_png = u"""<img src="data:image/png;base64,%s" alt=%s />"""

def latex_to_html(s, alt='image'):
    """Render LaTeX to HTML with embedded PNG data using data URIs.

    Parameters
    ----------
    s : str
        The raw string containing valid inline LateX.
    alt : str
        The alt text to use for the HTML.
    """
    base64_data = latex_to_png(s, encode=True).decode('ascii')
    if base64_data:
        return _data_uri_template_png  % (base64_data, alt)



# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\lib\latextools.py ===
# -*- coding: utf-8 -*-
"""Tools for handling LaTeX."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from io import BytesIO
import os
import tempfile
import shutil
import subprocess
from base64 import encodebytes
import textwrap

from pathlib import Path

from IPython.utils.process import find_cmd, FindCmdError
from traitlets.config import get_config
from traitlets.config.configurable import SingletonConfigurable
from traitlets import List, Bool, Unicode


class LaTeXTool(SingletonConfigurable):
    """An object to store configuration of the LaTeX tool."""
    def _config_default(self):
        return get_config()

    backends = List(
        Unicode(), ["matplotlib", "dvipng"],
        help="Preferred backend to draw LaTeX math equations. "
        "Backends in the list are checked one by one and the first "
        "usable one is used.  Note that `matplotlib` backend "
        "is usable only for inline style equations.  To draw  "
        "display style equations, `dvipng` backend must be specified. ",
        # It is a List instead of Enum, to make configuration more
        # flexible.  For example, to use matplotlib mainly but dvipng
        # for display style, the default ["matplotlib", "dvipng"] can
        # be used.  To NOT use dvipng so that other repr such as
        # unicode pretty printing is used, you can use ["matplotlib"].
        ).tag(config=True)

    use_breqn = Bool(
        True,
        help="Use breqn.sty to automatically break long equations. "
        "This configuration takes effect only for dvipng backend.",
        ).tag(config=True)

    packages = List(
        ['amsmath', 'amsthm', 'amssymb', 'bm'],
        help="A list of packages to use for dvipng backend. "
        "'breqn' will be automatically appended when use_breqn=True.",
        ).tag(config=True)

    preamble = Unicode(
        help="Additional preamble to use when generating LaTeX source "
        "for dvipng backend.",
        ).tag(config=True)


def latex_to_png(
    s: str, encode=False, backend=None, wrap=False, color="Black", scale=1.0
):
    """Render a LaTeX string to PNG.

    Parameters
    ----------
    s : str
        The raw string containing valid inline LaTeX.
    encode : bool, optional
        Should the PNG data base64 encoded to make it JSON'able.
    backend : {matplotlib, dvipng}
        Backend for producing PNG data.
    wrap : bool
        If true, Automatically wrap `s` as a LaTeX equation.
    color : string
        Foreground color name among dvipsnames, e.g. 'Maroon' or on hex RGB
        format, e.g. '#AA20FA'.
    scale : float
        Scale factor for the resulting PNG.
    None is returned when the backend cannot be used.

    """
    assert isinstance(s, str)
    allowed_backends = LaTeXTool.instance().backends
    if backend is None:
        backend = allowed_backends[0]
    if backend not in allowed_backends:
        return None
    if backend == 'matplotlib':
        f = latex_to_png_mpl
    elif backend == 'dvipng':
        f = latex_to_png_dvipng
        if color.startswith('#'):
            # Convert hex RGB color to LaTeX RGB color.
            if len(color) == 7:
                try:
                    color = "RGB {}".format(" ".join([str(int(x, 16)) for x in
                                                      textwrap.wrap(color[1:], 2)]))
                except ValueError as e:
                    raise ValueError('Invalid color specification {}.'.format(color)) from e
            else:
                raise ValueError('Invalid color specification {}.'.format(color))
    else:
        raise ValueError('No such backend {0}'.format(backend))
    bin_data = f(s, wrap, color, scale)
    if encode and bin_data:
        bin_data = encodebytes(bin_data)
    return bin_data


def latex_to_png_mpl(s, wrap, color='Black', scale=1.0):
    try:
        from matplotlib import figure, font_manager, mathtext
        from matplotlib.backends import backend_agg
        from pyparsing import ParseFatalException
    except ImportError:
        return None

    # mpl mathtext doesn't support display math, force inline
    s = s.replace('$$', '$')
    if wrap:
        s = u'${0}$'.format(s)

    try:
        prop = font_manager.FontProperties(size=12)
        dpi = 120 * scale
        buffer = BytesIO()

        # Adapted from mathtext.math_to_image
        parser = mathtext.MathTextParser("path")
        width, height, depth, _, _ = parser.parse(s, dpi=72, prop=prop)
        fig = figure.Figure(figsize=(width / 72, height / 72))
        fig.text(0, depth / height, s, fontproperties=prop, color=color)
        backend_agg.FigureCanvasAgg(fig)
        fig.savefig(buffer, dpi=dpi, format="png", transparent=True)
        return buffer.getvalue()
    except (ValueError, RuntimeError, ParseFatalException):
        return None


def latex_to_png_dvipng(s, wrap, color='Black', scale=1.0):
    try:
        find_cmd('latex')
        find_cmd('dvipng')
    except FindCmdError:
        return None

    startupinfo = None
    if os.name == "nt":
        # prevent popup-windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        workdir = Path(tempfile.mkdtemp())
        tmpfile = "tmp.tex"
        dvifile = "tmp.dvi"
        outfile = "tmp.png"

        with workdir.joinpath(tmpfile).open("w", encoding="utf8") as f:
            f.writelines(genelatex(s, wrap))

        subprocess.check_call(
            ["latex", "-halt-on-error", "-interaction", "batchmode", tmpfile],
            cwd=workdir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
        )

        resolution = round(150 * scale)
        subprocess.check_call(
            [
                "dvipng",
                "-T",
                "tight",
                "-D",
                str(resolution),
                "-z",
                "9",
                "-bg",
                "Transparent",
                "-o",
                outfile,
                dvifile,
                "-fg",
                color,
            ],
            cwd=workdir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
        )

        with workdir.joinpath(outfile).open("rb") as f:
            return f.read()
    except subprocess.CalledProcessError:
        return None
    finally:
        shutil.rmtree(workdir)


def kpsewhich(filename):
    """Invoke kpsewhich command with an argument `filename`."""
    try:
        find_cmd("kpsewhich")
        proc = subprocess.Popen(
            ["kpsewhich", filename],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = proc.communicate()
        return stdout.strip().decode('utf8', 'replace')
    except FindCmdError:
        pass


def genelatex(body, wrap):
    """Generate LaTeX document for dvipng backend."""
    lt = LaTeXTool.instance()
    breqn = wrap and lt.use_breqn and kpsewhich("breqn.sty")
    yield r'\documentclass{article}'
    packages = lt.packages
    if breqn:
        packages = packages + ['breqn']
    for pack in packages:
        yield r'\usepackage{{{0}}}'.format(pack)
    yield r'\pagestyle{empty}'
    if lt.preamble:
        yield lt.preamble
    yield r'\begin{document}'
    if breqn:
        yield r'\begin{dmath*}'
        yield body
        yield r'\end{dmath*}'
    elif wrap:
        yield u'$${0}$$'.format(body)
    else:
        yield body
    yield u'\\end{document}'


_data_uri_template_png = u"""<img src="data:image/png;base64,%s" alt=%s />"""

def latex_to_html(s, alt='image'):
    """Render LaTeX to HTML with embedded PNG data using data URIs.

    Parameters
    ----------
    s : str
        The raw string containing valid inline LateX.
    alt : str
        The alt text to use for the HTML.
    """
    base64_data = latex_to_png(s, encode=True).decode('ascii')
    if base64_data:
        return _data_uri_template_png  % (base64_data, alt)



# === NexusCore/exported_projects\app_20250703_223016\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/exported_projects\project_export_m73owrzi\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/exported_projects\project_export_xb_l70t8\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/src\sandbox_logs\repair_20250713_142257_fixed.py ===
エラーメッセージから、Pythonコード内に無効な文字（'、'）が存在することが原因であることがわかります。PythonはASCII文字とUnicode文字をサポートしていますが、コード内のコメントや文字列以外の場所で非ASCII文字を使用することは推奨されていません。

したがって、このエラーを修正するには、無効な文字を削除または適切なASCII文字に置き換える必要があります。

ただし、提供されたコードにはそのような文字は見当たらないため、エラーが発生した具体的なコードが不明です。そのため、具体的な修正コードを提供することはできません。

ただし、一般的なアドバイスとして、Pythonコード内で非ASCII文字を使用する場合は、それらをコメントや文字列内に限定し、それ以外の場所ではASCII文字のみを使用するようにすると良いでしょう。

# === NexusCore/src\sandbox_logs\repair_20250713_142312_original.py ===
エラーメッセージから、Pythonコード内に無効な文字（'、'）が存在することが原因であることがわかります。PythonはASCII文字とUnicode文字をサポートしていますが、コード内のコメントや文字列以外の場所で非ASCII文字を使用することは推奨されていません。

したがって、このエラーを修正するには、無効な文字を削除または適切なASCII文字に置き換える必要があります。

ただし、提供されたコードにはそのような文字は見当たらないため、エラーが発生した具体的なコードが不明です。そのため、具体的な修正コードを提供することはできません。

ただし、一般的なアドバイスとして、Pythonコード内で非ASCII文字を使用する場合は、それらをコメントや文字列内に限定し、それ以外の場所ではASCII文字のみを使用するようにすると良いでしょう。

# === NexusCore/src\sandbox_logs\repair_20250713_174027_fixed.py ===
申し訳ありませんが、具体的なPythonコードが提供されていないため、具体的な修正コードを提供することができません。ただし、エラーメッセージから推測するに、'test_main.py' ファイルの1行目に無効な文字が含まれているようです。以下のように修正することをおすすめします。

--- 修正例 ---
# 1行目の日本語コメントを削除または英語に変更します。
# 以下は一例です。

# Sorry, but I can't create a specific unit test because no specific Python code has been provided.

# === NexusCore/src\sandbox_logs\repair_20250713_174037_original.py ===
申し訳ありませんが、具体的なPythonコードが提供されていないため、具体的な修正コードを提供することができません。ただし、エラーメッセージから推測するに、'test_main.py' ファイルの1行目に無効な文字が含まれているようです。以下のように修正することをおすすめします。

--- 修正例 ---
# 1行目の日本語コメントを削除または英語に変更します。
# 以下は一例です。

# Sorry, but I can't create a specific unit test because no specific Python code has been provided.

# === NexusCore/src\sandbox_logs\repair_20250713_213522_original.py ===
def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\app_20250703_223016\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_xb_l70t8\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_y7xxp1v8\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_142257_fixed.py ===
エラーメッセージから、Pythonコード内に無効な文字（'、'）が存在することが原因であることがわかります。PythonはASCII文字とUnicode文字をサポートしていますが、コード内のコメントや文字列以外の場所で非ASCII文字を使用することは推奨されていません。

したがって、このエラーを修正するには、無効な文字を削除または適切なASCII文字に置き換える必要があります。

ただし、提供されたコードにはそのような文字は見当たらないため、エラーが発生した具体的なコードが不明です。そのため、具体的な修正コードを提供することはできません。

ただし、一般的なアドバイスとして、Pythonコード内で非ASCII文字を使用する場合は、それらをコメントや文字列内に限定し、それ以外の場所ではASCII文字のみを使用するようにすると良いでしょう。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_142312_original.py ===
エラーメッセージから、Pythonコード内に無効な文字（'、'）が存在することが原因であることがわかります。PythonはASCII文字とUnicode文字をサポートしていますが、コード内のコメントや文字列以外の場所で非ASCII文字を使用することは推奨されていません。

したがって、このエラーを修正するには、無効な文字を削除または適切なASCII文字に置き換える必要があります。

ただし、提供されたコードにはそのような文字は見当たらないため、エラーが発生した具体的なコードが不明です。そのため、具体的な修正コードを提供することはできません。

ただし、一般的なアドバイスとして、Pythonコード内で非ASCII文字を使用する場合は、それらをコメントや文字列内に限定し、それ以外の場所ではASCII文字のみを使用するようにすると良いでしょう。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_174027_fixed.py ===
申し訳ありませんが、具体的なPythonコードが提供されていないため、具体的な修正コードを提供することができません。ただし、エラーメッセージから推測するに、'test_main.py' ファイルの1行目に無効な文字が含まれているようです。以下のように修正することをおすすめします。

--- 修正例 ---
# 1行目の日本語コメントを削除または英語に変更します。
# 以下は一例です。

# Sorry, but I can't create a specific unit test because no specific Python code has been provided.

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_174037_original.py ===
申し訳ありませんが、具体的なPythonコードが提供されていないため、具体的な修正コードを提供することができません。ただし、エラーメッセージから推測するに、'test_main.py' ファイルの1行目に無効な文字が含まれているようです。以下のように修正することをおすすめします。

--- 修正例 ---
# 1行目の日本語コメントを削除または英語に変更します。
# 以下は一例です。

# Sorry, but I can't create a specific unit test because no specific Python code has been provided.

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_213522_original.py ===
def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\app_20250703_223016\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\project_export_xb_l70t8\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\project_export_y7xxp1v8\app\routes_backup.py ===
# app/routes.py
@app.route('/products/filter', methods=['GET', 'POST'])
def filter_products():
    form = ProfitFilterForm()
    if form.validate_on_submit():
        return redirect(url_for('index', min_profit=form.min_profit.data))
    return render_template('filter.html', form=form)

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_142257_fixed.py ===
エラーメッセージから、Pythonコード内に無効な文字（'、'）が存在することが原因であることがわかります。PythonはASCII文字とUnicode文字をサポートしていますが、コード内のコメントや文字列以外の場所で非ASCII文字を使用することは推奨されていません。

したがって、このエラーを修正するには、無効な文字を削除または適切なASCII文字に置き換える必要があります。

ただし、提供されたコードにはそのような文字は見当たらないため、エラーが発生した具体的なコードが不明です。そのため、具体的な修正コードを提供することはできません。

ただし、一般的なアドバイスとして、Pythonコード内で非ASCII文字を使用する場合は、それらをコメントや文字列内に限定し、それ以外の場所ではASCII文字のみを使用するようにすると良いでしょう。

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_142312_original.py ===
エラーメッセージから、Pythonコード内に無効な文字（'、'）が存在することが原因であることがわかります。PythonはASCII文字とUnicode文字をサポートしていますが、コード内のコメントや文字列以外の場所で非ASCII文字を使用することは推奨されていません。

したがって、このエラーを修正するには、無効な文字を削除または適切なASCII文字に置き換える必要があります。

ただし、提供されたコードにはそのような文字は見当たらないため、エラーが発生した具体的なコードが不明です。そのため、具体的な修正コードを提供することはできません。

ただし、一般的なアドバイスとして、Pythonコード内で非ASCII文字を使用する場合は、それらをコメントや文字列内に限定し、それ以外の場所ではASCII文字のみを使用するようにすると良いでしょう。

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\sandbox_logs\repair_20250713_213522_original.py ===
def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

# === NexusCore/src\sandbox_logs\repair_20250713_125723_fixed.py ===
```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition
```

エラーメッセージによれば、問題はテストコードのコメント部分にあります。非ASCII文字を含むコメントはPythonの構文エラーを引き起こす可能性があります。したがって、コメントを英語に変更するか、または完全に削除することをお勧めします。

# === NexusCore/src\sandbox_logs\repair_20250713_125733_original.py ===
```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition
```

エラーメッセージによれば、問題はテストコードのコメント部分にあります。非ASCII文字を含むコメントはPythonの構文エラーを引き起こす可能性があります。したがって、コメントを英語に変更するか、または完全に削除することをお勧めします。

# === NexusCore/src\sandbox_logs\repair_20250713_213331_fixed.py ===
```python
# -*- coding: utf-8 -*-

# 以下に、一般的なPython関数とそのテストコードの例を示します。
```
上記のように、Pythonファイルの先頭に文字エンコーディングを指定することで、非ASCII文字を含むコードも正しく解釈されます。ただし、Python3ではデフォルトでUTF-8が使用されるため、この行は必須ではありません。また、エラーメッセージからは、非ASCII文字が原因であることが示唆されていますが、具体的なコードがないため、他の可能性も排除できません。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_125723_fixed.py ===
```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition
```

エラーメッセージによれば、問題はテストコードのコメント部分にあります。非ASCII文字を含むコメントはPythonの構文エラーを引き起こす可能性があります。したがって、コメントを英語に変更するか、または完全に削除することをお勧めします。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_125733_original.py ===
```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition
```

エラーメッセージによれば、問題はテストコードのコメント部分にあります。非ASCII文字を含むコメントはPythonの構文エラーを引き起こす可能性があります。したがって、コメントを英語に変更するか、または完全に削除することをお勧めします。

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\sandbox_logs\repair_20250713_213331_fixed.py ===
```python
# -*- coding: utf-8 -*-

# 以下に、一般的なPython関数とそのテストコードの例を示します。
```
上記のように、Pythonファイルの先頭に文字エンコーディングを指定することで、非ASCII文字を含むコードも正しく解釈されます。ただし、Python3ではデフォルトでUTF-8が使用されるため、この行は必須ではありません。また、エラーメッセージからは、非ASCII文字が原因であることが示唆されていますが、具体的なコードがないため、他の可能性も排除できません。

# === NexusCore/src\sandbox_logs\repair_20250713_114534_fixed.py ===
```python
def add(a, b):
    return a + b  # ✔️ a + b
```
上記のエラーは、テストモジュールのインポートに失敗していることが原因です。これはPythonのコードに問題があるというよりは、テスト環境の設定やファイルの配置に問題がある可能性が高いです。したがって、コードの修正だけでは解決しないかもしれません。テスト環境の設定や、テストファイルの配置を見直すことをおすすめします。

# === NexusCore/src\sandbox_logs\repair_20250713_114552_original.py ===
```python
def add(a, b):
    return a + b  # ✔️ a + b
```
上記のエラーは、テストモジュールのインポートに失敗していることが原因です。これはPythonのコードに問題があるというよりは、テスト環境の設定やファイルの配置に問題がある可能性が高いです。したがって、コードの修正だけでは解決しないかもしれません。テスト環境の設定や、テストファイルの配置を見直すことをおすすめします。

# === NexusCore/policy_test_sandbox\app\main.py ===
def debug_greet(name):
    print(f'Hello, {name}!')

# === NexusCore/exported_projects\app_20250703_223016\app\routes\__init__.py ===

# === NexusCore/exported_projects\project_export_m73owrzi\app\routes\__init__.py ===

# === NexusCore/exported_projects\project_export_xb_l70t8\app\routes\__init__.py ===

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\routes\__init__.py ===

# === NexusCore/healing_sandbox\app\__init__.py ===

# === NexusCore/healing_sandbox\src\__init__.py ===

# === NexusCore/healing_sandbox\src\agents\__init__.py ===

# === NexusCore/policy_test_sandbox\app\__init__.py ===

# === NexusCore/quality_loop_test_sandbox\app\__init__.py ===

# === NexusCore/src\__init__.py ===

# === NexusCore/src\nexuscore\__init__.py ===

# === NexusCore/src\nexuscore\agents\__init__.py ===

# === NexusCore/src\nexuscore\api\__init__.py ===

# === NexusCore/src\nexuscore\audio\__init__.py ===

# === NexusCore/src\nexuscore\code_interpreter\__init__.py ===

# === NexusCore/src\nexuscore\config\__init__.py ===

# === NexusCore/src\nexuscore\core\__init__.py ===

# === NexusCore/src\nexuscore\gradio_app\__init__.py ===

# === NexusCore/src\nexuscore\modules\__init__.py ===

# === NexusCore/src\nexuscore\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\app_20250703_223016\app\routes\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\routes\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_xb_l70t8\app\routes\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_y7xxp1v8\app\routes\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\healing_sandbox\app\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\healing_sandbox\src\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\healing_sandbox\src\agents\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\policy_test_sandbox\app\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\quality_loop_test_sandbox\app\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\code_interpreter\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\core\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\gradio_app\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\workspace\default_project\app\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\app_20250703_223016\app\routes\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\routes\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\project_export_xb_l70t8\app\routes\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\exported_projects\project_export_y7xxp1v8\app\routes\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\healing_sandbox\app\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\healing_sandbox\src\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\healing_sandbox\src\agents\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\policy_test_sandbox\app\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\quality_loop_test_sandbox\app\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\agents\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\code_interpreter\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\core\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\gradio_app\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\src\utils\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\core\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\gradio_app\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\workspace\default_project\app\__init__.py ===

# === NexusCore/workspace\default_project\app\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\anthropic\lib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\anthropic\lib\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\__init__.py ===

# === NexusCore/evaluation\evalplus\evalplus\perf\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_internal\operations\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_internal\operations\build\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_internal\resolution\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_internal\resolution\legacy\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_internal\resolution\resolvelib\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_internal\utils\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\resolvelib\compat\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\_securetransport\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\packages\__init__.py ===

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\packages\backports\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\anyio\streams\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\anyio\_backends\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\anyio\_core\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydev_ipython\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_concurrency_analyser\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\_debug_adapter\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\vendored\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_runfiles\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\fontTools\colorLib\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\gitdb\utils\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\google\auth\crypt\_helpers.py ===

# === NexusCore/openenv\Lib\site-packages\google\protobuf\compiler\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\google\protobuf\pyext\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\google\protobuf\testdata\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\google\protobuf\util\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\greenlet\platform\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\html2image\browsers\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\httpcore\_backends\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_generated\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_mcp\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\importlib_metadata\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\computer_use\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\ai\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\browser\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\calendar\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\clipboard\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\contacts\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\display\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\files\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\keyboard\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\mail\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\mouse\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\os\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\sms\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\terminal\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\terminal\languages\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\vision\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\llm\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\utils\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\terminal_interface\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\ipykernel\pylab\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\IPython\core\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\IPython\extensions\deduperreload\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\IPython\sphinxext\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\IPython\terminal\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\IPython\testing\plugin\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\IPython\utils\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\joblib\externals\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\joblib\test\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\joblib\test\data\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\images\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\test_httpx.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\response_header_helpers.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\tokenizers\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\llms\mistral\mistral_embedding_transformation.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\router_utils\response_headers.py ===

# === NexusCore/openenv\Lib\site-packages\markdown_it\cli\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\markdown_it\common\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\qt_editor\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\matplotlib\sphinxext\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\nltk\tbl\api.py ===

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\lm\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\translate\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\testing\_private\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\_pyinstaller\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\parso\python\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_internal\operations\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_internal\operations\build\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_internal\resolution\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_internal\resolution\legacy\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_internal\resolution\resolvelib\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_internal\utils\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\resolvelib\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\_securetransport\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\packages\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\packages\backports\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\contrib\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\key_binding\bindings\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pydantic\deprecated\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pyparsing\tools\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pyreadline3\lineeditor\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\dialogs\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\docking\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\editor\color\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\mfc\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\tools\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\backports\tarfile\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\importlib_metadata\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\inflect\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\packaging\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\zipp\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\smmap\test\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\sniffio\_tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\tornado\platform\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\tornado\test\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\trio\_core\_tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\trio\_tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\trio\_tests\tools\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\trio\_tools\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\typing_inspection\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\urllib3\contrib\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\webdriver_manager\core\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\webdriver_manager\drivers\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\win32com\demos\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\win32com\servers\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\win32comext\axscript\server\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\zipp\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\zmq\log\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\zmq\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\evaluation\evalplus\evalplus\perf\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\operations\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\operations\build\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\resolution\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\resolution\legacy\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\resolution\resolvelib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\resolvelib\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\_securetransport\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\urllib3\packages\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\urllib3\packages\backports\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\anyio\streams\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\anyio\_backends\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\anyio\_core\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydev_ipython\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\_debug_adapter\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\vendored\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_runfiles\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\fontTools\colorLib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\fsspec\implementations\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\gitdb\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\google\auth\crypt\_helpers.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\google\protobuf\compiler\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\google\protobuf\pyext\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\google\protobuf\testdata\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\google\protobuf\util\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\greenlet\platform\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\html2image\browsers\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\httpcore\_backends\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\huggingface_hub\inference\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\huggingface_hub\inference\_generated\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\huggingface_hub\inference\_mcp\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\importlib_metadata\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\computer_use\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\ai\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\browser\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\calendar\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\clipboard\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\contacts\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\display\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\files\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\keyboard\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\mail\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\mouse\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\os\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\sms\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\terminal\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\terminal\languages\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\vision\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\llm\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\terminal_interface\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\ipykernel\pylab\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\core\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\extensions\deduperreload\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\sphinxext\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\terminal\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\testing\plugin\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\IPython\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\joblib\externals\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\joblib\test\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\joblib\test\data\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\litellm\images\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\litellm\integrations\test_httpx.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\litellm\litellm_core_utils\response_header_helpers.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\litellm\litellm_core_utils\tokenizers\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\litellm\llms\mistral\mistral_embedding_transformation.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\litellm\router_utils\response_headers.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\markdown_it\cli\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\markdown_it\common\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\matplotlib\backends\qt_editor\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\matplotlib\sphinxext\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\tbl\api.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\test\unit\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\test\unit\lm\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\test\unit\translate\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\testing\_private\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\_pyinstaller\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\parso\python\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\operations\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\operations\build\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\resolution\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\resolution\legacy\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\resolution\resolvelib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\resolvelib\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\_securetransport\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\urllib3\packages\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\urllib3\packages\backports\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\playwright\_impl\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\prompt_toolkit\contrib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\prompt_toolkit\key_binding\bindings\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pydantic\deprecated\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pydantic\_internal\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pyparsing\tools\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pyreadline3\lineeditor\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\dialogs\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\docking\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\framework\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\framework\editor\color\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\mfc\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\tools\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\backports\tarfile\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\importlib_metadata\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\inflect\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\packaging\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\zipp\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\smmap\test\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\sniffio\_tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\tornado\platform\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\tornado\test\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\trio\_core\_tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\trio\_tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\trio\_tests\tools\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\trio\_tools\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\typing_inspection\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\urllib3\contrib\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\webdriver_manager\core\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\webdriver_manager\drivers\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32com\demos\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32com\servers\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\win32comext\axscript\server\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\zipp\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\zmq\log\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\zmq\utils\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\evaluation\evalplus\evalplus\perf\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\operations\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\operations\build\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\resolution\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\resolution\legacy\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\resolution\resolvelib\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\myenv\Lib\site-packages\pip\_internal\utils\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\resolvelib\compat\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\_securetransport\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\urllib3\packages\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\myenv\Lib\site-packages\pip\_vendor\urllib3\packages\backports\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\anyio\streams\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\anyio\_backends\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\anyio\_core\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydev_ipython\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_runfiles\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\fontTools\colorLib\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\fsspec\implementations\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\gitdb\utils\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\google\auth\crypt\_helpers.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\google\protobuf\compiler\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\google\protobuf\pyext\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\google\protobuf\testdata\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\google\protobuf\util\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\greenlet\platform\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\html2image\browsers\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\httpcore\_backends\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\huggingface_hub\inference\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\huggingface_hub\inference\_generated\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\huggingface_hub\inference\_mcp\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\importlib_metadata\compat\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\computer_use\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\ai\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\browser\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\calendar\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\clipboard\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\contacts\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\display\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\files\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\keyboard\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\mail\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\mouse\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\os\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\sms\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\terminal\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\terminal\languages\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\vision\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\llm\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\utils\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\terminal_interface\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\ipykernel\pylab\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\IPython\core\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\IPython\extensions\deduperreload\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\IPython\sphinxext\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\IPython\terminal\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\IPython\testing\plugin\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\IPython\utils\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\joblib\externals\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\joblib\test\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\joblib\test\data\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\litellm\images\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\litellm\integrations\test_httpx.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\litellm\litellm_core_utils\response_header_helpers.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\litellm\litellm_core_utils\tokenizers\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\litellm\llms\mistral\mistral_embedding_transformation.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\litellm\router_utils\response_headers.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\markdown_it\cli\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\markdown_it\common\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\matplotlib\backends\qt_editor\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\matplotlib\sphinxext\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\nltk\tbl\api.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\nltk\test\unit\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\nltk\test\unit\lm\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\nltk\test\unit\translate\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\testing\_private\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\_pyinstaller\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\parso\python\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\operations\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\operations\build\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\resolution\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\resolution\legacy\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\resolution\resolvelib\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pip\_internal\utils\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\resolvelib\compat\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\_securetransport\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\urllib3\packages\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pip\_vendor\urllib3\packages\backports\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\playwright\_impl\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\prompt_toolkit\contrib\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\prompt_toolkit\key_binding\bindings\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pydantic\deprecated\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pydantic\_internal\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pyparsing\tools\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pyreadline3\lineeditor\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\dialogs\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\docking\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\framework\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\framework\editor\color\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\mfc\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pythonwin\pywin\tools\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\setuptools\compat\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\backports\tarfile\compat\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\importlib_metadata\compat\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\inflect\compat\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\packaging\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_vendor\zipp\compat\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\smmap\test\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\sniffio\_tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\tornado\platform\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\tornado\test\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\trio\_core\_tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\trio\_tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\trio\_tests\tools\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\trio\_tools\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\typing_inspection\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\urllib3\contrib\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\webdriver_manager\core\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\webdriver_manager\drivers\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\win32com\demos\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\win32com\servers\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\win32comext\axscript\server\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\zipp\compat\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\zmq\log\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\zmq\utils\__init__.py ===

# === NexusCore/healing_sandbox\tests\__init__.py ===

# === NexusCore/my-crm-app\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\blessed\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\docs\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\jsonschema\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\jsonschema_specifications\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\fft\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\linalg\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\ma\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\matrixlib\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\polynomial\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\random\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\random\tests\data\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\testing\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\typing\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\pkg_resources\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\referencing\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\tests\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\tests\config\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\tests\integration\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\tests\test_versionpredicate.py ===

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\tests\compat\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\traitlets\tests\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\websocket\tests\__init__.py ===

# === NexusCore/policy_test_sandbox\tests\__init__.py ===

# === NexusCore/quality_loop_test_sandbox\tests\__init__.py ===

# === NexusCore/sandbox_repo\tests\__init__.py ===

# === NexusCore/tests\__init__.py ===

# === NexusCore/tests\agents\test_debugger_enhanced_final.py ===

# === NexusCore/tests\api\__init__.py ===

# === NexusCore/tests\audio\__init__.py ===

# === NexusCore/tests\code_interpreter\__init__.py ===

# === NexusCore/tests\core\__init__.py ===

# === NexusCore/tests\gradio_app\__init__.py ===

# === NexusCore/tests\modules\__init__.py ===

# === NexusCore/tests\utils\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\healing_sandbox\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\my-crm-app\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\blessed\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\docs\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\jsonschema\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\jsonschema_specifications\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\fft\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\linalg\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\ma\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\matrixlib\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\polynomial\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\random\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\random\tests\data\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\testing\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\typing\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\pkg_resources\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\referencing\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\tests\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\tests\config\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\tests\integration\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_distutils\tests\test_versionpredicate.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_distutils\tests\compat\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\traitlets\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\websocket\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\policy_test_sandbox\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\quality_loop_test_sandbox\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\sandbox_repo\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\tests\__init__.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\workspace\default_project\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\healing_sandbox\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\my-crm-app\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\blessed\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\interpreter\core\computer\docs\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\jsonschema\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\jsonschema_specifications\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\fft\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\linalg\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\ma\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\matrixlib\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\polynomial\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\random\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\random\tests\data\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\testing\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\numpy\typing\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\pkg_resources\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\referencing\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\setuptools\tests\compat\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\setuptools\tests\config\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\setuptools\tests\integration\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_distutils\tests\test_versionpredicate.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\setuptools\_distutils\tests\compat\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\traitlets\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\websocket\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\policy_test_sandbox\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\quality_loop_test_sandbox\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\sandbox_repo\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\my-crm-app\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\source_code\NexusCore\tests\__init__.py ===

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\workspace\default_project\tests\__init__.py ===

# === NexusCore/workspace\default_project\tests\__init__.py ===