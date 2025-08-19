
# === NexusCore/openenv\Lib\site-packages\openai\resources\beta\chat\completions.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, List, Type, Union, Iterable, Optional, cast
from functools import partial
from typing_extensions import Literal

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import maybe_transform, async_maybe_transform
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ...._streaming import Stream
from ....types.chat import completion_create_params
from ...._base_client import make_request_options
from ....lib._parsing import (
    ResponseFormatT,
    validate_input_tools as _validate_input_tools,
    parse_chat_completion as _parse_chat_completion,
    type_to_response_format_param as _type_to_response_format,
)
from ....types.chat_model import ChatModel
from ....lib.streaming.chat import ChatCompletionStreamManager, AsyncChatCompletionStreamManager
from ....types.shared_params import Metadata, ReasoningEffort
from ....types.chat.chat_completion import ChatCompletion
from ....types.chat.chat_completion_chunk import ChatCompletionChunk
from ....types.chat.parsed_chat_completion import ParsedChatCompletion
from ....types.chat.chat_completion_tool_param import ChatCompletionToolParam
from ....types.chat.chat_completion_audio_param import ChatCompletionAudioParam
from ....types.chat.chat_completion_message_param import ChatCompletionMessageParam
from ....types.chat.chat_completion_stream_options_param import ChatCompletionStreamOptionsParam
from ....types.chat.chat_completion_prediction_content_param import ChatCompletionPredictionContentParam
from ....types.chat.chat_completion_tool_choice_option_param import ChatCompletionToolChoiceOptionParam

__all__ = ["Completions", "AsyncCompletions"]


class Completions(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> CompletionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return CompletionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> CompletionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return CompletionsWithStreamingResponse(self)

    def parse(
        self,
        *,
        messages: Iterable[ChatCompletionMessageParam],
        model: Union[str, ChatModel],
        audio: Optional[ChatCompletionAudioParam] | NotGiven = NOT_GIVEN,
        response_format: type[ResponseFormatT] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: completion_create_params.FunctionCall | NotGiven = NOT_GIVEN,
        functions: Iterable[completion_create_params.Function] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[bool] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        modalities: Optional[List[Literal["text", "audio"]]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        prediction: Optional[ChatCompletionPredictionContentParam] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: ChatCompletionToolChoiceOptionParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        top_logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        web_search_options: completion_create_params.WebSearchOptions | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ParsedChatCompletion[ResponseFormatT]:
        """Wrapper over the `client.chat.completions.create()` method that provides richer integrations with Python specific types
        & returns a `ParsedChatCompletion` object, which is a subclass of the standard `ChatCompletion` class.

        You can pass a pydantic model to this method and it will automatically convert the model
        into a JSON schema, send it to the API and parse the response content back into the given model.

        This method will also automatically parse `function` tool calls if:
        - You use the `openai.pydantic_function_tool()` helper method
        - You mark your tool schema with `"strict": True`

        Example usage:
        ```py
        from pydantic import BaseModel
        from openai import OpenAI


        class Step(BaseModel):
            explanation: str
            output: str


        class MathResponse(BaseModel):
            steps: List[Step]
            final_answer: str


        client = OpenAI()
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are a helpful math tutor."},
                {"role": "user", "content": "solve 8x + 31 = 2"},
            ],
            response_format=MathResponse,
        )

        message = completion.choices[0].message
        if message.parsed:
            print(message.parsed.steps)
            print("answer: ", message.parsed.final_answer)
        ```
        """
        _validate_input_tools(tools)

        extra_headers = {
            "X-Stainless-Helper-Method": "beta.chat.completions.parse",
            **(extra_headers or {}),
        }

        def parser(raw_completion: ChatCompletion) -> ParsedChatCompletion[ResponseFormatT]:
            return _parse_chat_completion(
                response_format=response_format,
                chat_completion=raw_completion,
                input_tools=tools,
            )

        return self._post(
            "/chat/completions",
            body=maybe_transform(
                {
                    "messages": messages,
                    "model": model,
                    "audio": audio,
                    "frequency_penalty": frequency_penalty,
                    "function_call": function_call,
                    "functions": functions,
                    "logit_bias": logit_bias,
                    "logprobs": logprobs,
                    "max_completion_tokens": max_completion_tokens,
                    "max_tokens": max_tokens,
                    "metadata": metadata,
                    "modalities": modalities,
                    "n": n,
                    "parallel_tool_calls": parallel_tool_calls,
                    "prediction": prediction,
                    "presence_penalty": presence_penalty,
                    "reasoning_effort": reasoning_effort,
                    "response_format": _type_to_response_format(response_format),
                    "seed": seed,
                    "service_tier": service_tier,
                    "stop": stop,
                    "store": store,
                    "stream": False,
                    "stream_options": stream_options,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_logprobs": top_logprobs,
                    "top_p": top_p,
                    "user": user,
                    "web_search_options": web_search_options,
                },
                completion_create_params.CompletionCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                post_parser=parser,
            ),
            # we turn the `ChatCompletion` instance into a `ParsedChatCompletion`
            # in the `parser` function above
            cast_to=cast(Type[ParsedChatCompletion[ResponseFormatT]], ChatCompletion),
            stream=False,
        )

    def stream(
        self,
        *,
        messages: Iterable[ChatCompletionMessageParam],
        model: Union[str, ChatModel],
        audio: Optional[ChatCompletionAudioParam] | NotGiven = NOT_GIVEN,
        response_format: completion_create_params.ResponseFormat | type[ResponseFormatT] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: completion_create_params.FunctionCall | NotGiven = NOT_GIVEN,
        functions: Iterable[completion_create_params.Function] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[bool] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        modalities: Optional[List[Literal["text", "audio"]]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        prediction: Optional[ChatCompletionPredictionContentParam] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: ChatCompletionToolChoiceOptionParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        top_logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        web_search_options: completion_create_params.WebSearchOptions | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ChatCompletionStreamManager[ResponseFormatT]:
        """Wrapper over the `client.chat.completions.create(stream=True)` method that provides a more granular event API
        and automatic accumulation of each delta.

        This also supports all of the parsing utilities that `.parse()` does.

        Unlike `.create(stream=True)`, the `.stream()` method requires usage within a context manager to prevent accidental leakage of the response:

        ```py
        with client.beta.chat.completions.stream(
            model="gpt-4o-2024-08-06",
            messages=[...],
        ) as stream:
            for event in stream:
                if event.type == "content.delta":
                    print(event.delta, flush=True, end="")
        ```

        When the context manager is entered, a `ChatCompletionStream` instance is returned which, like `.create(stream=True)` is an iterator. The full list of events that are yielded by the iterator are outlined in [these docs](https://github.com/openai/openai-python/blob/main/helpers.md#chat-completions-events).

        When the context manager exits, the response will be closed, however the `stream` instance is still available outside
        the context manager.
        """
        extra_headers = {
            "X-Stainless-Helper-Method": "beta.chat.completions.stream",
            **(extra_headers or {}),
        }

        api_request: partial[Stream[ChatCompletionChunk]] = partial(
            self._client.chat.completions.create,
            messages=messages,
            model=model,
            audio=audio,
            stream=True,
            response_format=_type_to_response_format(response_format),
            frequency_penalty=frequency_penalty,
            function_call=function_call,
            functions=functions,
            logit_bias=logit_bias,
            logprobs=logprobs,
            max_completion_tokens=max_completion_tokens,
            max_tokens=max_tokens,
            metadata=metadata,
            modalities=modalities,
            n=n,
            parallel_tool_calls=parallel_tool_calls,
            prediction=prediction,
            presence_penalty=presence_penalty,
            reasoning_effort=reasoning_effort,
            seed=seed,
            service_tier=service_tier,
            store=store,
            stop=stop,
            stream_options=stream_options,
            temperature=temperature,
            tool_choice=tool_choice,
            tools=tools,
            top_logprobs=top_logprobs,
            top_p=top_p,
            user=user,
            web_search_options=web_search_options,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
        )
        return ChatCompletionStreamManager(
            api_request,
            response_format=response_format,
            input_tools=tools,
        )


class AsyncCompletions(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncCompletionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncCompletionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncCompletionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncCompletionsWithStreamingResponse(self)

    async def parse(
        self,
        *,
        messages: Iterable[ChatCompletionMessageParam],
        model: Union[str, ChatModel],
        audio: Optional[ChatCompletionAudioParam] | NotGiven = NOT_GIVEN,
        response_format: type[ResponseFormatT] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: completion_create_params.FunctionCall | NotGiven = NOT_GIVEN,
        functions: Iterable[completion_create_params.Function] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[bool] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        modalities: Optional[List[Literal["text", "audio"]]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        prediction: Optional[ChatCompletionPredictionContentParam] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: ChatCompletionToolChoiceOptionParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        top_logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        web_search_options: completion_create_params.WebSearchOptions | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ParsedChatCompletion[ResponseFormatT]:
        """Wrapper over the `client.chat.completions.create()` method that provides richer integrations with Python specific types
        & returns a `ParsedChatCompletion` object, which is a subclass of the standard `ChatCompletion` class.

        You can pass a pydantic model to this method and it will automatically convert the model
        into a JSON schema, send it to the API and parse the response content back into the given model.

        This method will also automatically parse `function` tool calls if:
        - You use the `openai.pydantic_function_tool()` helper method
        - You mark your tool schema with `"strict": True`

        Example usage:
        ```py
        from pydantic import BaseModel
        from openai import AsyncOpenAI


        class Step(BaseModel):
            explanation: str
            output: str


        class MathResponse(BaseModel):
            steps: List[Step]
            final_answer: str


        client = AsyncOpenAI()
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are a helpful math tutor."},
                {"role": "user", "content": "solve 8x + 31 = 2"},
            ],
            response_format=MathResponse,
        )

        message = completion.choices[0].message
        if message.parsed:
            print(message.parsed.steps)
            print("answer: ", message.parsed.final_answer)
        ```
        """
        _validate_input_tools(tools)

        extra_headers = {
            "X-Stainless-Helper-Method": "beta.chat.completions.parse",
            **(extra_headers or {}),
        }

        def parser(raw_completion: ChatCompletion) -> ParsedChatCompletion[ResponseFormatT]:
            return _parse_chat_completion(
                response_format=response_format,
                chat_completion=raw_completion,
                input_tools=tools,
            )

        return await self._post(
            "/chat/completions",
            body=await async_maybe_transform(
                {
                    "messages": messages,
                    "model": model,
                    "audio": audio,
                    "frequency_penalty": frequency_penalty,
                    "function_call": function_call,
                    "functions": functions,
                    "logit_bias": logit_bias,
                    "logprobs": logprobs,
                    "max_completion_tokens": max_completion_tokens,
                    "max_tokens": max_tokens,
                    "metadata": metadata,
                    "modalities": modalities,
                    "n": n,
                    "parallel_tool_calls": parallel_tool_calls,
                    "prediction": prediction,
                    "presence_penalty": presence_penalty,
                    "reasoning_effort": reasoning_effort,
                    "response_format": _type_to_response_format(response_format),
                    "seed": seed,
                    "service_tier": service_tier,
                    "store": store,
                    "stop": stop,
                    "stream": False,
                    "stream_options": stream_options,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_logprobs": top_logprobs,
                    "top_p": top_p,
                    "user": user,
                    "web_search_options": web_search_options,
                },
                completion_create_params.CompletionCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                post_parser=parser,
            ),
            # we turn the `ChatCompletion` instance into a `ParsedChatCompletion`
            # in the `parser` function above
            cast_to=cast(Type[ParsedChatCompletion[ResponseFormatT]], ChatCompletion),
            stream=False,
        )

    def stream(
        self,
        *,
        messages: Iterable[ChatCompletionMessageParam],
        model: Union[str, ChatModel],
        audio: Optional[ChatCompletionAudioParam] | NotGiven = NOT_GIVEN,
        response_format: completion_create_params.ResponseFormat | type[ResponseFormatT] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: completion_create_params.FunctionCall | NotGiven = NOT_GIVEN,
        functions: Iterable[completion_create_params.Function] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[bool] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        modalities: Optional[List[Literal["text", "audio"]]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        prediction: Optional[ChatCompletionPredictionContentParam] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: ChatCompletionToolChoiceOptionParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        top_logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        web_search_options: completion_create_params.WebSearchOptions | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncChatCompletionStreamManager[ResponseFormatT]:
        """Wrapper over the `client.chat.completions.create(stream=True)` method that provides a more granular event API
        and automatic accumulation of each delta.

        This also supports all of the parsing utilities that `.parse()` does.

        Unlike `.create(stream=True)`, the `.stream()` method requires usage within a context manager to prevent accidental leakage of the response:

        ```py
        async with client.beta.chat.completions.stream(
            model="gpt-4o-2024-08-06",
            messages=[...],
        ) as stream:
            async for event in stream:
                if event.type == "content.delta":
                    print(event.delta, flush=True, end="")
        ```

        When the context manager is entered, an `AsyncChatCompletionStream` instance is returned which, like `.create(stream=True)` is an async iterator. The full list of events that are yielded by the iterator are outlined in [these docs](https://github.com/openai/openai-python/blob/main/helpers.md#chat-completions-events).

        When the context manager exits, the response will be closed, however the `stream` instance is still available outside
        the context manager.
        """
        _validate_input_tools(tools)

        extra_headers = {
            "X-Stainless-Helper-Method": "beta.chat.completions.stream",
            **(extra_headers or {}),
        }

        api_request = self._client.chat.completions.create(
            messages=messages,
            model=model,
            audio=audio,
            stream=True,
            response_format=_type_to_response_format(response_format),
            frequency_penalty=frequency_penalty,
            function_call=function_call,
            functions=functions,
            logit_bias=logit_bias,
            logprobs=logprobs,
            max_completion_tokens=max_completion_tokens,
            max_tokens=max_tokens,
            metadata=metadata,
            modalities=modalities,
            n=n,
            parallel_tool_calls=parallel_tool_calls,
            prediction=prediction,
            presence_penalty=presence_penalty,
            reasoning_effort=reasoning_effort,
            seed=seed,
            service_tier=service_tier,
            stop=stop,
            store=store,
            stream_options=stream_options,
            temperature=temperature,
            tool_choice=tool_choice,
            tools=tools,
            top_logprobs=top_logprobs,
            top_p=top_p,
            user=user,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
            web_search_options=web_search_options,
        )
        return AsyncChatCompletionStreamManager(
            api_request,
            response_format=response_format,
            input_tools=tools,
        )


class CompletionsWithRawResponse:
    def __init__(self, completions: Completions) -> None:
        self._completions = completions

        self.parse = _legacy_response.to_raw_response_wrapper(
            completions.parse,
        )


class AsyncCompletionsWithRawResponse:
    def __init__(self, completions: AsyncCompletions) -> None:
        self._completions = completions

        self.parse = _legacy_response.async_to_raw_response_wrapper(
            completions.parse,
        )


class CompletionsWithStreamingResponse:
    def __init__(self, completions: Completions) -> None:
        self._completions = completions

        self.parse = to_streamed_response_wrapper(
            completions.parse,
        )


class AsyncCompletionsWithStreamingResponse:
    def __init__(self, completions: AsyncCompletions) -> None:
        self._completions = completions

        self.parse = async_to_streamed_response_wrapper(
            completions.parse,
        )

# === NexusCore/openenv\Lib\site-packages\openai\resources\evals\runs\runs.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Optional
from typing_extensions import Literal

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import maybe_transform, async_maybe_transform
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from .output_items import (
    OutputItems,
    AsyncOutputItems,
    OutputItemsWithRawResponse,
    AsyncOutputItemsWithRawResponse,
    OutputItemsWithStreamingResponse,
    AsyncOutputItemsWithStreamingResponse,
)
from ....pagination import SyncCursorPage, AsyncCursorPage
from ....types.evals import run_list_params, run_create_params
from ...._base_client import AsyncPaginator, make_request_options
from ....types.shared_params.metadata import Metadata
from ....types.evals.run_list_response import RunListResponse
from ....types.evals.run_cancel_response import RunCancelResponse
from ....types.evals.run_create_response import RunCreateResponse
from ....types.evals.run_delete_response import RunDeleteResponse
from ....types.evals.run_retrieve_response import RunRetrieveResponse

__all__ = ["Runs", "AsyncRuns"]


class Runs(SyncAPIResource):
    @cached_property
    def output_items(self) -> OutputItems:
        return OutputItems(self._client)

    @cached_property
    def with_raw_response(self) -> RunsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return RunsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> RunsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return RunsWithStreamingResponse(self)

    def create(
        self,
        eval_id: str,
        *,
        data_source: run_create_params.DataSource,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        name: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> RunCreateResponse:
        """
        Kicks off a new run for a given evaluation, specifying the data source, and what
        model configuration to use to test. The datasource will be validated against the
        schema specified in the config of the evaluation.

        Args:
          data_source: Details about the run's data source.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          name: The name of the run.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        return self._post(
            f"/evals/{eval_id}/runs",
            body=maybe_transform(
                {
                    "data_source": data_source,
                    "metadata": metadata,
                    "name": name,
                },
                run_create_params.RunCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=RunCreateResponse,
        )

    def retrieve(
        self,
        run_id: str,
        *,
        eval_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> RunRetrieveResponse:
        """
        Get an evaluation run by ID.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        return self._get(
            f"/evals/{eval_id}/runs/{run_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=RunRetrieveResponse,
        )

    def list(
        self,
        eval_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        status: Literal["queued", "in_progress", "completed", "canceled", "failed"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[RunListResponse]:
        """
        Get a list of runs for an evaluation.

        Args:
          after: Identifier for the last run from the previous pagination request.

          limit: Number of runs to retrieve.

          order: Sort order for runs by timestamp. Use `asc` for ascending order or `desc` for
              descending order. Defaults to `asc`.

          status: Filter runs by status. One of `queued` | `in_progress` | `failed` | `completed`
              | `canceled`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        return self._get_api_list(
            f"/evals/{eval_id}/runs",
            page=SyncCursorPage[RunListResponse],
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
                        "status": status,
                    },
                    run_list_params.RunListParams,
                ),
            ),
            model=RunListResponse,
        )

    def delete(
        self,
        run_id: str,
        *,
        eval_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> RunDeleteResponse:
        """
        Delete an eval run.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        return self._delete(
            f"/evals/{eval_id}/runs/{run_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=RunDeleteResponse,
        )

    def cancel(
        self,
        run_id: str,
        *,
        eval_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> RunCancelResponse:
        """
        Cancel an ongoing evaluation run.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        return self._post(
            f"/evals/{eval_id}/runs/{run_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=RunCancelResponse,
        )


class AsyncRuns(AsyncAPIResource):
    @cached_property
    def output_items(self) -> AsyncOutputItems:
        return AsyncOutputItems(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncRunsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncRunsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncRunsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncRunsWithStreamingResponse(self)

    async def create(
        self,
        eval_id: str,
        *,
        data_source: run_create_params.DataSource,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        name: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> RunCreateResponse:
        """
        Kicks off a new run for a given evaluation, specifying the data source, and what
        model configuration to use to test. The datasource will be validated against the
        schema specified in the config of the evaluation.

        Args:
          data_source: Details about the run's data source.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          name: The name of the run.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        return await self._post(
            f"/evals/{eval_id}/runs",
            body=await async_maybe_transform(
                {
                    "data_source": data_source,
                    "metadata": metadata,
                    "name": name,
                },
                run_create_params.RunCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=RunCreateResponse,
        )

    async def retrieve(
        self,
        run_id: str,
        *,
        eval_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> RunRetrieveResponse:
        """
        Get an evaluation run by ID.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        return await self._get(
            f"/evals/{eval_id}/runs/{run_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=RunRetrieveResponse,
        )

    def list(
        self,
        eval_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        status: Literal["queued", "in_progress", "completed", "canceled", "failed"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[RunListResponse, AsyncCursorPage[RunListResponse]]:
        """
        Get a list of runs for an evaluation.

        Args:
          after: Identifier for the last run from the previous pagination request.

          limit: Number of runs to retrieve.

          order: Sort order for runs by timestamp. Use `asc` for ascending order or `desc` for
              descending order. Defaults to `asc`.

          status: Filter runs by status. One of `queued` | `in_progress` | `failed` | `completed`
              | `canceled`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        return self._get_api_list(
            f"/evals/{eval_id}/runs",
            page=AsyncCursorPage[RunListResponse],
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
                        "status": status,
                    },
                    run_list_params.RunListParams,
                ),
            ),
            model=RunListResponse,
        )

    async def delete(
        self,
        run_id: str,
        *,
        eval_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> RunDeleteResponse:
        """
        Delete an eval run.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        return await self._delete(
            f"/evals/{eval_id}/runs/{run_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=RunDeleteResponse,
        )

    async def cancel(
        self,
        run_id: str,
        *,
        eval_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> RunCancelResponse:
        """
        Cancel an ongoing evaluation run.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not eval_id:
            raise ValueError(f"Expected a non-empty value for `eval_id` but received {eval_id!r}")
        if not run_id:
            raise ValueError(f"Expected a non-empty value for `run_id` but received {run_id!r}")
        return await self._post(
            f"/evals/{eval_id}/runs/{run_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=RunCancelResponse,
        )


class RunsWithRawResponse:
    def __init__(self, runs: Runs) -> None:
        self._runs = runs

        self.create = _legacy_response.to_raw_response_wrapper(
            runs.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            runs.retrieve,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            runs.list,
        )
        self.delete = _legacy_response.to_raw_response_wrapper(
            runs.delete,
        )
        self.cancel = _legacy_response.to_raw_response_wrapper(
            runs.cancel,
        )

    @cached_property
    def output_items(self) -> OutputItemsWithRawResponse:
        return OutputItemsWithRawResponse(self._runs.output_items)


class AsyncRunsWithRawResponse:
    def __init__(self, runs: AsyncRuns) -> None:
        self._runs = runs

        self.create = _legacy_response.async_to_raw_response_wrapper(
            runs.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            runs.retrieve,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            runs.list,
        )
        self.delete = _legacy_response.async_to_raw_response_wrapper(
            runs.delete,
        )
        self.cancel = _legacy_response.async_to_raw_response_wrapper(
            runs.cancel,
        )

    @cached_property
    def output_items(self) -> AsyncOutputItemsWithRawResponse:
        return AsyncOutputItemsWithRawResponse(self._runs.output_items)


class RunsWithStreamingResponse:
    def __init__(self, runs: Runs) -> None:
        self._runs = runs

        self.create = to_streamed_response_wrapper(
            runs.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            runs.retrieve,
        )
        self.list = to_streamed_response_wrapper(
            runs.list,
        )
        self.delete = to_streamed_response_wrapper(
            runs.delete,
        )
        self.cancel = to_streamed_response_wrapper(
            runs.cancel,
        )

    @cached_property
    def output_items(self) -> OutputItemsWithStreamingResponse:
        return OutputItemsWithStreamingResponse(self._runs.output_items)


class AsyncRunsWithStreamingResponse:
    def __init__(self, runs: AsyncRuns) -> None:
        self._runs = runs

        self.create = async_to_streamed_response_wrapper(
            runs.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            runs.retrieve,
        )
        self.list = async_to_streamed_response_wrapper(
            runs.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            runs.delete,
        )
        self.cancel = async_to_streamed_response_wrapper(
            runs.cancel,
        )

    @cached_property
    def output_items(self) -> AsyncOutputItemsWithStreamingResponse:
        return AsyncOutputItemsWithStreamingResponse(self._runs.output_items)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\req\req_uninstall.py ===
import functools
import os
import sys
import sysconfig
from importlib.util import cache_from_source
from typing import Any, Callable, Dict, Generator, Iterable, List, Optional, Set, Tuple

from pip._internal.exceptions import LegacyDistutilsInstall, UninstallMissingRecord
from pip._internal.locations import get_bin_prefix, get_bin_user
from pip._internal.metadata import BaseDistribution
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.egg_link import egg_link_path_from_location
from pip._internal.utils.logging import getLogger, indent_log
from pip._internal.utils.misc import ask, normalize_path, renames, rmtree
from pip._internal.utils.temp_dir import AdjacentTempDirectory, TempDirectory
from pip._internal.utils.virtualenv import running_under_virtualenv

logger = getLogger(__name__)


def _script_names(
    bin_dir: str, script_name: str, is_gui: bool
) -> Generator[str, None, None]:
    """Create the fully qualified name of the files created by
    {console,gui}_scripts for the given ``dist``.
    Returns the list of file names
    """
    exe_name = os.path.join(bin_dir, script_name)
    yield exe_name
    if not WINDOWS:
        return
    yield f"{exe_name}.exe"
    yield f"{exe_name}.exe.manifest"
    if is_gui:
        yield f"{exe_name}-script.pyw"
    else:
        yield f"{exe_name}-script.py"


def _unique(
    fn: Callable[..., Generator[Any, None, None]]
) -> Callable[..., Generator[Any, None, None]]:
    @functools.wraps(fn)
    def unique(*args: Any, **kw: Any) -> Generator[Any, None, None]:
        seen: Set[Any] = set()
        for item in fn(*args, **kw):
            if item not in seen:
                seen.add(item)
                yield item

    return unique


@_unique
def uninstallation_paths(dist: BaseDistribution) -> Generator[str, None, None]:
    """
    Yield all the uninstallation paths for dist based on RECORD-without-.py[co]

    Yield paths to all the files in RECORD. For each .py file in RECORD, add
    the .pyc and .pyo in the same directory.

    UninstallPathSet.add() takes care of the __pycache__ .py[co].

    If RECORD is not found, raises an error,
    with possible information from the INSTALLER file.

    https://packaging.python.org/specifications/recording-installed-packages/
    """
    location = dist.location
    assert location is not None, "not installed"

    entries = dist.iter_declared_entries()
    if entries is None:
        raise UninstallMissingRecord(distribution=dist)

    for entry in entries:
        path = os.path.join(location, entry)
        yield path
        if path.endswith(".py"):
            dn, fn = os.path.split(path)
            base = fn[:-3]
            path = os.path.join(dn, base + ".pyc")
            yield path
            path = os.path.join(dn, base + ".pyo")
            yield path


def compact(paths: Iterable[str]) -> Set[str]:
    """Compact a path set to contain the minimal number of paths
    necessary to contain all paths in the set. If /a/path/ and
    /a/path/to/a/file.txt are both in the set, leave only the
    shorter path."""

    sep = os.path.sep
    short_paths: Set[str] = set()
    for path in sorted(paths, key=len):
        should_skip = any(
            path.startswith(shortpath.rstrip("*"))
            and path[len(shortpath.rstrip("*").rstrip(sep))] == sep
            for shortpath in short_paths
        )
        if not should_skip:
            short_paths.add(path)
    return short_paths


def compress_for_rename(paths: Iterable[str]) -> Set[str]:
    """Returns a set containing the paths that need to be renamed.

    This set may include directories when the original sequence of paths
    included every file on disk.
    """
    case_map = {os.path.normcase(p): p for p in paths}
    remaining = set(case_map)
    unchecked = sorted({os.path.split(p)[0] for p in case_map.values()}, key=len)
    wildcards: Set[str] = set()

    def norm_join(*a: str) -> str:
        return os.path.normcase(os.path.join(*a))

    for root in unchecked:
        if any(os.path.normcase(root).startswith(w) for w in wildcards):
            # This directory has already been handled.
            continue

        all_files: Set[str] = set()
        all_subdirs: Set[str] = set()
        for dirname, subdirs, files in os.walk(root):
            all_subdirs.update(norm_join(root, dirname, d) for d in subdirs)
            all_files.update(norm_join(root, dirname, f) for f in files)
        # If all the files we found are in our remaining set of files to
        # remove, then remove them from the latter set and add a wildcard
        # for the directory.
        if not (all_files - remaining):
            remaining.difference_update(all_files)
            wildcards.add(root + os.sep)

    return set(map(case_map.__getitem__, remaining)) | wildcards


def compress_for_output_listing(paths: Iterable[str]) -> Tuple[Set[str], Set[str]]:
    """Returns a tuple of 2 sets of which paths to display to user

    The first set contains paths that would be deleted. Files of a package
    are not added and the top-level directory of the package has a '*' added
    at the end - to signify that all it's contents are removed.

    The second set contains files that would have been skipped in the above
    folders.
    """

    will_remove = set(paths)
    will_skip = set()

    # Determine folders and files
    folders = set()
    files = set()
    for path in will_remove:
        if path.endswith(".pyc"):
            continue
        if path.endswith("__init__.py") or ".dist-info" in path:
            folders.add(os.path.dirname(path))
        files.add(path)

    _normcased_files = set(map(os.path.normcase, files))

    folders = compact(folders)

    # This walks the tree using os.walk to not miss extra folders
    # that might get added.
    for folder in folders:
        for dirpath, _, dirfiles in os.walk(folder):
            for fname in dirfiles:
                if fname.endswith(".pyc"):
                    continue

                file_ = os.path.join(dirpath, fname)
                if (
                    os.path.isfile(file_)
                    and os.path.normcase(file_) not in _normcased_files
                ):
                    # We are skipping this file. Add it to the set.
                    will_skip.add(file_)

    will_remove = files | {os.path.join(folder, "*") for folder in folders}

    return will_remove, will_skip


class StashedUninstallPathSet:
    """A set of file rename operations to stash files while
    tentatively uninstalling them."""

    def __init__(self) -> None:
        # Mapping from source file root to [Adjacent]TempDirectory
        # for files under that directory.
        self._save_dirs: Dict[str, TempDirectory] = {}
        # (old path, new path) tuples for each move that may need
        # to be undone.
        self._moves: List[Tuple[str, str]] = []

    def _get_directory_stash(self, path: str) -> str:
        """Stashes a directory.

        Directories are stashed adjacent to their original location if
        possible, or else moved/copied into the user's temp dir."""

        try:
            save_dir: TempDirectory = AdjacentTempDirectory(path)
        except OSError:
            save_dir = TempDirectory(kind="uninstall")
        self._save_dirs[os.path.normcase(path)] = save_dir

        return save_dir.path

    def _get_file_stash(self, path: str) -> str:
        """Stashes a file.

        If no root has been provided, one will be created for the directory
        in the user's temp directory."""
        path = os.path.normcase(path)
        head, old_head = os.path.dirname(path), None
        save_dir = None

        while head != old_head:
            try:
                save_dir = self._save_dirs[head]
                break
            except KeyError:
                pass
            head, old_head = os.path.dirname(head), head
        else:
            # Did not find any suitable root
            head = os.path.dirname(path)
            save_dir = TempDirectory(kind="uninstall")
            self._save_dirs[head] = save_dir

        relpath = os.path.relpath(path, head)
        if relpath and relpath != os.path.curdir:
            return os.path.join(save_dir.path, relpath)
        return save_dir.path

    def stash(self, path: str) -> str:
        """Stashes the directory or file and returns its new location.
        Handle symlinks as files to avoid modifying the symlink targets.
        """
        path_is_dir = os.path.isdir(path) and not os.path.islink(path)
        if path_is_dir:
            new_path = self._get_directory_stash(path)
        else:
            new_path = self._get_file_stash(path)

        self._moves.append((path, new_path))
        if path_is_dir and os.path.isdir(new_path):
            # If we're moving a directory, we need to
            # remove the destination first or else it will be
            # moved to inside the existing directory.
            # We just created new_path ourselves, so it will
            # be removable.
            os.rmdir(new_path)
        renames(path, new_path)
        return new_path

    def commit(self) -> None:
        """Commits the uninstall by removing stashed files."""
        for save_dir in self._save_dirs.values():
            save_dir.cleanup()
        self._moves = []
        self._save_dirs = {}

    def rollback(self) -> None:
        """Undoes the uninstall by moving stashed files back."""
        for p in self._moves:
            logger.info("Moving to %s\n from %s", *p)

        for new_path, path in self._moves:
            try:
                logger.debug("Replacing %s from %s", new_path, path)
                if os.path.isfile(new_path) or os.path.islink(new_path):
                    os.unlink(new_path)
                elif os.path.isdir(new_path):
                    rmtree(new_path)
                renames(path, new_path)
            except OSError as ex:
                logger.error("Failed to restore %s", new_path)
                logger.debug("Exception: %s", ex)

        self.commit()

    @property
    def can_rollback(self) -> bool:
        return bool(self._moves)


class UninstallPathSet:
    """A set of file paths to be removed in the uninstallation of a
    requirement."""

    def __init__(self, dist: BaseDistribution) -> None:
        self._paths: Set[str] = set()
        self._refuse: Set[str] = set()
        self._pth: Dict[str, UninstallPthEntries] = {}
        self._dist = dist
        self._moved_paths = StashedUninstallPathSet()
        # Create local cache of normalize_path results. Creating an UninstallPathSet
        # can result in hundreds/thousands of redundant calls to normalize_path with
        # the same args, which hurts performance.
        self._normalize_path_cached = functools.lru_cache(normalize_path)

    def _permitted(self, path: str) -> bool:
        """
        Return True if the given path is one we are permitted to
        remove/modify, False otherwise.

        """
        # aka is_local, but caching normalized sys.prefix
        if not running_under_virtualenv():
            return True
        return path.startswith(self._normalize_path_cached(sys.prefix))

    def add(self, path: str) -> None:
        head, tail = os.path.split(path)

        # we normalize the head to resolve parent directory symlinks, but not
        # the tail, since we only want to uninstall symlinks, not their targets
        path = os.path.join(self._normalize_path_cached(head), os.path.normcase(tail))

        if not os.path.exists(path):
            return
        if self._permitted(path):
            self._paths.add(path)
        else:
            self._refuse.add(path)

        # __pycache__ files can show up after 'installed-files.txt' is created,
        # due to imports
        if os.path.splitext(path)[1] == ".py":
            self.add(cache_from_source(path))

    def add_pth(self, pth_file: str, entry: str) -> None:
        pth_file = self._normalize_path_cached(pth_file)
        if self._permitted(pth_file):
            if pth_file not in self._pth:
                self._pth[pth_file] = UninstallPthEntries(pth_file)
            self._pth[pth_file].add(entry)
        else:
            self._refuse.add(pth_file)

    def remove(self, auto_confirm: bool = False, verbose: bool = False) -> None:
        """Remove paths in ``self._paths`` with confirmation (unless
        ``auto_confirm`` is True)."""

        if not self._paths:
            logger.info(
                "Can't uninstall '%s'. No files were found to uninstall.",
                self._dist.raw_name,
            )
            return

        dist_name_version = f"{self._dist.raw_name}-{self._dist.raw_version}"
        logger.info("Uninstalling %s:", dist_name_version)

        with indent_log():
            if auto_confirm or self._allowed_to_proceed(verbose):
                moved = self._moved_paths

                for_rename = compress_for_rename(self._paths)

                for path in sorted(compact(for_rename)):
                    moved.stash(path)
                    logger.verbose("Removing file or directory %s", path)

                for pth in self._pth.values():
                    pth.remove()

                logger.info("Successfully uninstalled %s", dist_name_version)

    def _allowed_to_proceed(self, verbose: bool) -> bool:
        """Display which files would be deleted and prompt for confirmation"""

        def _display(msg: str, paths: Iterable[str]) -> None:
            if not paths:
                return

            logger.info(msg)
            with indent_log():
                for path in sorted(compact(paths)):
                    logger.info(path)

        if not verbose:
            will_remove, will_skip = compress_for_output_listing(self._paths)
        else:
            # In verbose mode, display all the files that are going to be
            # deleted.
            will_remove = set(self._paths)
            will_skip = set()

        _display("Would remove:", will_remove)
        _display("Would not remove (might be manually added):", will_skip)
        _display("Would not remove (outside of prefix):", self._refuse)
        if verbose:
            _display("Will actually move:", compress_for_rename(self._paths))

        return ask("Proceed (Y/n)? ", ("y", "n", "")) != "n"

    def rollback(self) -> None:
        """Rollback the changes previously made by remove()."""
        if not self._moved_paths.can_rollback:
            logger.error(
                "Can't roll back %s; was not uninstalled",
                self._dist.raw_name,
            )
            return
        logger.info("Rolling back uninstall of %s", self._dist.raw_name)
        self._moved_paths.rollback()
        for pth in self._pth.values():
            pth.rollback()

    def commit(self) -> None:
        """Remove temporary save dir: rollback will no longer be possible."""
        self._moved_paths.commit()

    @classmethod
    def from_dist(cls, dist: BaseDistribution) -> "UninstallPathSet":
        dist_location = dist.location
        info_location = dist.info_location
        if dist_location is None:
            logger.info(
                "Not uninstalling %s since it is not installed",
                dist.canonical_name,
            )
            return cls(dist)

        normalized_dist_location = normalize_path(dist_location)
        if not dist.local:
            logger.info(
                "Not uninstalling %s at %s, outside environment %s",
                dist.canonical_name,
                normalized_dist_location,
                sys.prefix,
            )
            return cls(dist)

        if normalized_dist_location in {
            p
            for p in {sysconfig.get_path("stdlib"), sysconfig.get_path("platstdlib")}
            if p
        }:
            logger.info(
                "Not uninstalling %s at %s, as it is in the standard library.",
                dist.canonical_name,
                normalized_dist_location,
            )
            return cls(dist)

        paths_to_remove = cls(dist)
        develop_egg_link = egg_link_path_from_location(dist.raw_name)

        # Distribution is installed with metadata in a "flat" .egg-info
        # directory. This means it is not a modern .dist-info installation, an
        # egg, or legacy editable.
        setuptools_flat_installation = (
            dist.installed_with_setuptools_egg_info
            and info_location is not None
            and os.path.exists(info_location)
            # If dist is editable and the location points to a ``.egg-info``,
            # we are in fact in the legacy editable case.
            and not info_location.endswith(f"{dist.setuptools_filename}.egg-info")
        )

        # Uninstall cases order do matter as in the case of 2 installs of the
        # same package, pip needs to uninstall the currently detected version
        if setuptools_flat_installation:
            if info_location is not None:
                paths_to_remove.add(info_location)
            installed_files = dist.iter_declared_entries()
            if installed_files is not None:
                for installed_file in installed_files:
                    paths_to_remove.add(os.path.join(dist_location, installed_file))
            # FIXME: need a test for this elif block
            # occurs with --single-version-externally-managed/--record outside
            # of pip
            elif dist.is_file("top_level.txt"):
                try:
                    namespace_packages = dist.read_text("namespace_packages.txt")
                except FileNotFoundError:
                    namespaces = []
                else:
                    namespaces = namespace_packages.splitlines(keepends=False)
                for top_level_pkg in [
                    p
                    for p in dist.read_text("top_level.txt").splitlines()
                    if p and p not in namespaces
                ]:
                    path = os.path.join(dist_location, top_level_pkg)
                    paths_to_remove.add(path)
                    paths_to_remove.add(f"{path}.py")
                    paths_to_remove.add(f"{path}.pyc")
                    paths_to_remove.add(f"{path}.pyo")

        elif dist.installed_by_distutils:
            raise LegacyDistutilsInstall(distribution=dist)

        elif dist.installed_as_egg:
            # package installed by easy_install
            # We cannot match on dist.egg_name because it can slightly vary
            # i.e. setuptools-0.6c11-py2.6.egg vs setuptools-0.6rc11-py2.6.egg
            paths_to_remove.add(dist_location)
            easy_install_egg = os.path.split(dist_location)[1]
            easy_install_pth = os.path.join(
                os.path.dirname(dist_location),
                "easy-install.pth",
            )
            paths_to_remove.add_pth(easy_install_pth, "./" + easy_install_egg)

        elif dist.installed_with_dist_info:
            for path in uninstallation_paths(dist):
                paths_to_remove.add(path)

        elif develop_egg_link:
            # PEP 660 modern editable is handled in the ``.dist-info`` case
            # above, so this only covers the setuptools-style editable.
            with open(develop_egg_link) as fh:
                link_pointer = os.path.normcase(fh.readline().strip())
                normalized_link_pointer = paths_to_remove._normalize_path_cached(
                    link_pointer
                )
            assert os.path.samefile(
                normalized_link_pointer, normalized_dist_location
            ), (
                f"Egg-link {develop_egg_link} (to {link_pointer}) does not match "
                f"installed location of {dist.raw_name} (at {dist_location})"
            )
            paths_to_remove.add(develop_egg_link)
            easy_install_pth = os.path.join(
                os.path.dirname(develop_egg_link), "easy-install.pth"
            )
            paths_to_remove.add_pth(easy_install_pth, dist_location)

        else:
            logger.debug(
                "Not sure how to uninstall: %s - Check: %s",
                dist,
                dist_location,
            )

        if dist.in_usersite:
            bin_dir = get_bin_user()
        else:
            bin_dir = get_bin_prefix()

        # find distutils scripts= scripts
        try:
            for script in dist.iter_distutils_script_names():
                paths_to_remove.add(os.path.join(bin_dir, script))
                if WINDOWS:
                    paths_to_remove.add(os.path.join(bin_dir, f"{script}.bat"))
        except (FileNotFoundError, NotADirectoryError):
            pass

        # find console_scripts and gui_scripts
        def iter_scripts_to_remove(
            dist: BaseDistribution,
            bin_dir: str,
        ) -> Generator[str, None, None]:
            for entry_point in dist.iter_entry_points():
                if entry_point.group == "console_scripts":
                    yield from _script_names(bin_dir, entry_point.name, False)
                elif entry_point.group == "gui_scripts":
                    yield from _script_names(bin_dir, entry_point.name, True)

        for s in iter_scripts_to_remove(dist, bin_dir):
            paths_to_remove.add(s)

        return paths_to_remove


class UninstallPthEntries:
    def __init__(self, pth_file: str) -> None:
        self.file = pth_file
        self.entries: Set[str] = set()
        self._saved_lines: Optional[List[bytes]] = None

    def add(self, entry: str) -> None:
        entry = os.path.normcase(entry)
        # On Windows, os.path.normcase converts the entry to use
        # backslashes.  This is correct for entries that describe absolute
        # paths outside of site-packages, but all the others use forward
        # slashes.
        # os.path.splitdrive is used instead of os.path.isabs because isabs
        # treats non-absolute paths with drive letter markings like c:foo\bar
        # as absolute paths. It also does not recognize UNC paths if they don't
        # have more than "\\sever\share". Valid examples: "\\server\share\" or
        # "\\server\share\folder".
        if WINDOWS and not os.path.splitdrive(entry)[0]:
            entry = entry.replace("\\", "/")
        self.entries.add(entry)

    def remove(self) -> None:
        logger.verbose("Removing pth entries from %s:", self.file)

        # If the file doesn't exist, log a warning and return
        if not os.path.isfile(self.file):
            logger.warning("Cannot remove entries from nonexistent file %s", self.file)
            return
        with open(self.file, "rb") as fh:
            # windows uses '\r\n' with py3k, but uses '\n' with py2.x
            lines = fh.readlines()
            self._saved_lines = lines
        if any(b"\r\n" in line for line in lines):
            endline = "\r\n"
        else:
            endline = "\n"
        # handle missing trailing newline
        if lines and not lines[-1].endswith(endline.encode("utf-8")):
            lines[-1] = lines[-1] + endline.encode("utf-8")
        for entry in self.entries:
            try:
                logger.verbose("Removing entry: %s", entry)
                lines.remove((entry + endline).encode("utf-8"))
            except ValueError:
                pass
        with open(self.file, "wb") as fh:
            fh.writelines(lines)

    def rollback(self) -> bool:
        if self._saved_lines is None:
            logger.error("Cannot roll back changes to %s, none were made", self.file)
            return False
        logger.debug("Rolling %s back to previous state", self.file)
        with open(self.file, "wb") as fh:
            fh.writelines(self._saved_lines)
        return True

# === NexusCore/openenv\Lib\site-packages\nltk\sentiment\vader.py ===
# Natural Language Toolkit: vader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: C.J. Hutto <Clayton.Hutto@gtri.gatech.edu>
#         Ewan Klein <ewan@inf.ed.ac.uk> (modifications)
#         Pierpaolo Pantone <24alsecondo@gmail.com> (modifications)
#         George Berry <geb97@cornell.edu> (modifications)
#         Malavika Suresh <malavika.suresh0794@gmail.com> (modifications)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# Modifications to the original VADER code have been made in order to
# integrate it into NLTK. These have involved changes to
# ensure Python 3 compatibility, and refactoring to achieve greater modularity.

"""
If you use the VADER sentiment analysis tools, please cite:

Hutto, C.J. & Gilbert, E.E. (2014). VADER: A Parsimonious Rule-based Model for
Sentiment Analysis of Social Media Text. Eighth International Conference on
Weblogs and Social Media (ICWSM-14). Ann Arbor, MI, June 2014.
"""

import math
import re
import string
from itertools import product

import nltk.data
from nltk.util import pairwise


class VaderConstants:
    """
    A class to keep the Vader lists and constants.
    """

    ##Constants##
    # (empirically derived mean sentiment intensity rating increase for booster words)
    B_INCR = 0.293
    B_DECR = -0.293

    # (empirically derived mean sentiment intensity rating increase for using
    # ALLCAPs to emphasize a word)
    C_INCR = 0.733

    N_SCALAR = -0.74

    NEGATE = {
        "aint",
        "arent",
        "cannot",
        "cant",
        "couldnt",
        "darent",
        "didnt",
        "doesnt",
        "ain't",
        "aren't",
        "can't",
        "couldn't",
        "daren't",
        "didn't",
        "doesn't",
        "dont",
        "hadnt",
        "hasnt",
        "havent",
        "isnt",
        "mightnt",
        "mustnt",
        "neither",
        "don't",
        "hadn't",
        "hasn't",
        "haven't",
        "isn't",
        "mightn't",
        "mustn't",
        "neednt",
        "needn't",
        "never",
        "none",
        "nope",
        "nor",
        "not",
        "nothing",
        "nowhere",
        "oughtnt",
        "shant",
        "shouldnt",
        "uhuh",
        "wasnt",
        "werent",
        "oughtn't",
        "shan't",
        "shouldn't",
        "uh-uh",
        "wasn't",
        "weren't",
        "without",
        "wont",
        "wouldnt",
        "won't",
        "wouldn't",
        "rarely",
        "seldom",
        "despite",
    }

    # booster/dampener 'intensifiers' or 'degree adverbs'
    # https://en.wiktionary.org/wiki/Category:English_degree_adverbs

    BOOSTER_DICT = {
        "absolutely": B_INCR,
        "amazingly": B_INCR,
        "awfully": B_INCR,
        "completely": B_INCR,
        "considerably": B_INCR,
        "decidedly": B_INCR,
        "deeply": B_INCR,
        "effing": B_INCR,
        "enormously": B_INCR,
        "entirely": B_INCR,
        "especially": B_INCR,
        "exceptionally": B_INCR,
        "extremely": B_INCR,
        "fabulously": B_INCR,
        "flipping": B_INCR,
        "flippin": B_INCR,
        "fricking": B_INCR,
        "frickin": B_INCR,
        "frigging": B_INCR,
        "friggin": B_INCR,
        "fully": B_INCR,
        "fucking": B_INCR,
        "greatly": B_INCR,
        "hella": B_INCR,
        "highly": B_INCR,
        "hugely": B_INCR,
        "incredibly": B_INCR,
        "intensely": B_INCR,
        "majorly": B_INCR,
        "more": B_INCR,
        "most": B_INCR,
        "particularly": B_INCR,
        "purely": B_INCR,
        "quite": B_INCR,
        "really": B_INCR,
        "remarkably": B_INCR,
        "so": B_INCR,
        "substantially": B_INCR,
        "thoroughly": B_INCR,
        "totally": B_INCR,
        "tremendously": B_INCR,
        "uber": B_INCR,
        "unbelievably": B_INCR,
        "unusually": B_INCR,
        "utterly": B_INCR,
        "very": B_INCR,
        "almost": B_DECR,
        "barely": B_DECR,
        "hardly": B_DECR,
        "just enough": B_DECR,
        "kind of": B_DECR,
        "kinda": B_DECR,
        "kindof": B_DECR,
        "kind-of": B_DECR,
        "less": B_DECR,
        "little": B_DECR,
        "marginally": B_DECR,
        "occasionally": B_DECR,
        "partly": B_DECR,
        "scarcely": B_DECR,
        "slightly": B_DECR,
        "somewhat": B_DECR,
        "sort of": B_DECR,
        "sorta": B_DECR,
        "sortof": B_DECR,
        "sort-of": B_DECR,
    }

    # check for special case idioms using a sentiment-laden keyword known to SAGE
    SPECIAL_CASE_IDIOMS = {
        "the shit": 3,
        "the bomb": 3,
        "bad ass": 1.5,
        "yeah right": -2,
        "cut the mustard": 2,
        "kiss of death": -1.5,
        "hand to mouth": -2,
    }

    # for removing punctuation
    REGEX_REMOVE_PUNCTUATION = re.compile(f"[{re.escape(string.punctuation)}]")

    PUNC_LIST = [
        ".",
        "!",
        "?",
        ",",
        ";",
        ":",
        "-",
        "'",
        '"',
        "!!",
        "!!!",
        "??",
        "???",
        "?!?",
        "!?!",
        "?!?!",
        "!?!?",
    ]

    def __init__(self):
        pass

    def negated(self, input_words, include_nt=True):
        """
        Determine if input contains negation words
        """
        neg_words = self.NEGATE
        if any(word.lower() in neg_words for word in input_words):
            return True
        if include_nt:
            if any("n't" in word.lower() for word in input_words):
                return True
        for first, second in pairwise(input_words):
            if second.lower() == "least" and first.lower() != "at":
                return True
        return False

    def normalize(self, score, alpha=15):
        """
        Normalize the score to be between -1 and 1 using an alpha that
        approximates the max expected value
        """
        norm_score = score / math.sqrt((score * score) + alpha)
        return norm_score

    def scalar_inc_dec(self, word, valence, is_cap_diff):
        """
        Check if the preceding words increase, decrease, or negate/nullify the
        valence
        """
        scalar = 0.0
        word_lower = word.lower()
        if word_lower in self.BOOSTER_DICT:
            scalar = self.BOOSTER_DICT[word_lower]
            if valence < 0:
                scalar *= -1
            # check if booster/dampener word is in ALLCAPS (while others aren't)
            if word.isupper() and is_cap_diff:
                if valence > 0:
                    scalar += self.C_INCR
                else:
                    scalar -= self.C_INCR
        return scalar


class SentiText:
    """
    Identify sentiment-relevant string-level properties of input text.
    """

    def __init__(self, text, punc_list, regex_remove_punctuation):
        if not isinstance(text, str):
            text = str(text.encode("utf-8"))
        self.text = text
        self.PUNC_LIST = punc_list
        self.REGEX_REMOVE_PUNCTUATION = regex_remove_punctuation
        self.words_and_emoticons = self._words_and_emoticons()
        # doesn't separate words from
        # adjacent punctuation (keeps emoticons & contractions)
        self.is_cap_diff = self.allcap_differential(self.words_and_emoticons)

    def _words_plus_punc(self):
        """
        Returns mapping of form:
        {
            'cat,': 'cat',
            ',cat': 'cat',
        }
        """
        no_punc_text = self.REGEX_REMOVE_PUNCTUATION.sub("", self.text)
        # removes punctuation (but loses emoticons & contractions)
        words_only = no_punc_text.split()
        # remove singletons
        words_only = {w for w in words_only if len(w) > 1}
        # the product gives ('cat', ',') and (',', 'cat')
        punc_before = {"".join(p): p[1] for p in product(self.PUNC_LIST, words_only)}
        punc_after = {"".join(p): p[0] for p in product(words_only, self.PUNC_LIST)}
        words_punc_dict = punc_before
        words_punc_dict.update(punc_after)
        return words_punc_dict

    def _words_and_emoticons(self):
        """
        Removes leading and trailing puncutation
        Leaves contractions and most emoticons
            Does not preserve punc-plus-letter emoticons (e.g. :D)
        """
        wes = self.text.split()
        words_punc_dict = self._words_plus_punc()
        wes = [we for we in wes if len(we) > 1]
        for i, we in enumerate(wes):
            if we in words_punc_dict:
                wes[i] = words_punc_dict[we]
        return wes

    def allcap_differential(self, words):
        """
        Check whether just some words in the input are ALL CAPS

        :param list words: The words to inspect
        :returns: `True` if some but not all items in `words` are ALL CAPS
        """
        is_different = False
        allcap_words = 0
        for word in words:
            if word.isupper():
                allcap_words += 1
        cap_differential = len(words) - allcap_words
        if 0 < cap_differential < len(words):
            is_different = True
        return is_different


class SentimentIntensityAnalyzer:
    """
    Give a sentiment intensity score to sentences.
    """

    def __init__(
        self,
        lexicon_file="sentiment/vader_lexicon.zip/vader_lexicon/vader_lexicon.txt",
    ):
        self.lexicon_file = nltk.data.load(lexicon_file)
        self.lexicon = self.make_lex_dict()
        self.constants = VaderConstants()

    def make_lex_dict(self):
        """
        Convert lexicon file to a dictionary
        """
        lex_dict = {}
        for line in self.lexicon_file.split("\n"):
            (word, measure) = line.strip().split("\t")[0:2]
            lex_dict[word] = float(measure)
        return lex_dict

    def polarity_scores(self, text):
        """
        Return a float for sentiment strength based on the input text.
        Positive values are positive valence, negative value are negative
        valence.

        :note: Hashtags are not taken into consideration (e.g. #BAD is neutral). If you
            are interested in processing the text in the hashtags too, then we recommend
            preprocessing your data to remove the #, after which the hashtag text may be
            matched as if it was a normal word in the sentence.
        """
        # text, words_and_emoticons, is_cap_diff = self.preprocess(text)
        sentitext = SentiText(
            text, self.constants.PUNC_LIST, self.constants.REGEX_REMOVE_PUNCTUATION
        )
        sentiments = []
        words_and_emoticons = sentitext.words_and_emoticons
        for item in words_and_emoticons:
            valence = 0
            i = words_and_emoticons.index(item)
            if (
                i < len(words_and_emoticons) - 1
                and item.lower() == "kind"
                and words_and_emoticons[i + 1].lower() == "of"
            ) or item.lower() in self.constants.BOOSTER_DICT:
                sentiments.append(valence)
                continue

            sentiments = self.sentiment_valence(valence, sentitext, item, i, sentiments)

        sentiments = self._but_check(words_and_emoticons, sentiments)

        return self.score_valence(sentiments, text)

    def sentiment_valence(self, valence, sentitext, item, i, sentiments):
        is_cap_diff = sentitext.is_cap_diff
        words_and_emoticons = sentitext.words_and_emoticons
        item_lowercase = item.lower()
        if item_lowercase in self.lexicon:
            # get the sentiment valence
            valence = self.lexicon[item_lowercase]

            # check if sentiment laden word is in ALL CAPS (while others aren't)
            if item.isupper() and is_cap_diff:
                if valence > 0:
                    valence += self.constants.C_INCR
                else:
                    valence -= self.constants.C_INCR

            for start_i in range(0, 3):
                if (
                    i > start_i
                    and words_and_emoticons[i - (start_i + 1)].lower()
                    not in self.lexicon
                ):
                    # dampen the scalar modifier of preceding words and emoticons
                    # (excluding the ones that immediately preceed the item) based
                    # on their distance from the current item.
                    s = self.constants.scalar_inc_dec(
                        words_and_emoticons[i - (start_i + 1)], valence, is_cap_diff
                    )
                    if start_i == 1 and s != 0:
                        s = s * 0.95
                    if start_i == 2 and s != 0:
                        s = s * 0.9
                    valence = valence + s
                    valence = self._never_check(
                        valence, words_and_emoticons, start_i, i
                    )
                    if start_i == 2:
                        valence = self._idioms_check(valence, words_and_emoticons, i)

                        # future work: consider other sentiment-laden idioms
                        # other_idioms =
                        # {"back handed": -2, "blow smoke": -2, "blowing smoke": -2,
                        #  "upper hand": 1, "break a leg": 2,
                        #  "cooking with gas": 2, "in the black": 2, "in the red": -2,
                        #  "on the ball": 2,"under the weather": -2}

            valence = self._least_check(valence, words_and_emoticons, i)

        sentiments.append(valence)
        return sentiments

    def _least_check(self, valence, words_and_emoticons, i):
        # check for negation case using "least"
        if (
            i > 1
            and words_and_emoticons[i - 1].lower() not in self.lexicon
            and words_and_emoticons[i - 1].lower() == "least"
        ):
            if (
                words_and_emoticons[i - 2].lower() != "at"
                and words_and_emoticons[i - 2].lower() != "very"
            ):
                valence = valence * self.constants.N_SCALAR
        elif (
            i > 0
            and words_and_emoticons[i - 1].lower() not in self.lexicon
            and words_and_emoticons[i - 1].lower() == "least"
        ):
            valence = valence * self.constants.N_SCALAR
        return valence

    def _but_check(self, words_and_emoticons, sentiments):
        words_and_emoticons = [w_e.lower() for w_e in words_and_emoticons]
        but = {"but"} & set(words_and_emoticons)
        if but:
            bi = words_and_emoticons.index(next(iter(but)))
            for sidx, sentiment in enumerate(sentiments):
                if sidx < bi:
                    sentiments[sidx] = sentiment * 0.5
                elif sidx > bi:
                    sentiments[sidx] = sentiment * 1.5
        return sentiments

    def _idioms_check(self, valence, words_and_emoticons, i):
        onezero = f"{words_and_emoticons[i - 1]} {words_and_emoticons[i]}"

        twoonezero = "{} {} {}".format(
            words_and_emoticons[i - 2],
            words_and_emoticons[i - 1],
            words_and_emoticons[i],
        )

        twoone = f"{words_and_emoticons[i - 2]} {words_and_emoticons[i - 1]}"

        threetwoone = "{} {} {}".format(
            words_and_emoticons[i - 3],
            words_and_emoticons[i - 2],
            words_and_emoticons[i - 1],
        )

        threetwo = "{} {}".format(
            words_and_emoticons[i - 3], words_and_emoticons[i - 2]
        )

        sequences = [onezero, twoonezero, twoone, threetwoone, threetwo]

        for seq in sequences:
            if seq in self.constants.SPECIAL_CASE_IDIOMS:
                valence = self.constants.SPECIAL_CASE_IDIOMS[seq]
                break

        if len(words_and_emoticons) - 1 > i:
            zeroone = f"{words_and_emoticons[i]} {words_and_emoticons[i + 1]}"
            if zeroone in self.constants.SPECIAL_CASE_IDIOMS:
                valence = self.constants.SPECIAL_CASE_IDIOMS[zeroone]
        if len(words_and_emoticons) - 1 > i + 1:
            zeroonetwo = "{} {} {}".format(
                words_and_emoticons[i],
                words_and_emoticons[i + 1],
                words_and_emoticons[i + 2],
            )
            if zeroonetwo in self.constants.SPECIAL_CASE_IDIOMS:
                valence = self.constants.SPECIAL_CASE_IDIOMS[zeroonetwo]

        # check for booster/dampener bi-grams such as 'sort of' or 'kind of'
        if (
            threetwo in self.constants.BOOSTER_DICT
            or twoone in self.constants.BOOSTER_DICT
        ):
            valence = valence + self.constants.B_DECR
        return valence

    def _never_check(self, valence, words_and_emoticons, start_i, i):
        if start_i == 0:
            if self.constants.negated([words_and_emoticons[i - 1]]):
                valence = valence * self.constants.N_SCALAR
        if start_i == 1:
            if words_and_emoticons[i - 2] == "never" and (
                words_and_emoticons[i - 1] == "so"
                or words_and_emoticons[i - 1] == "this"
            ):
                valence = valence * 1.5
            elif self.constants.negated([words_and_emoticons[i - (start_i + 1)]]):
                valence = valence * self.constants.N_SCALAR
        if start_i == 2:
            if (
                words_and_emoticons[i - 3] == "never"
                and (
                    words_and_emoticons[i - 2] == "so"
                    or words_and_emoticons[i - 2] == "this"
                )
                or (
                    words_and_emoticons[i - 1] == "so"
                    or words_and_emoticons[i - 1] == "this"
                )
            ):
                valence = valence * 1.25
            elif self.constants.negated([words_and_emoticons[i - (start_i + 1)]]):
                valence = valence * self.constants.N_SCALAR
        return valence

    def _punctuation_emphasis(self, sum_s, text):
        # add emphasis from exclamation points and question marks
        ep_amplifier = self._amplify_ep(text)
        qm_amplifier = self._amplify_qm(text)
        punct_emph_amplifier = ep_amplifier + qm_amplifier
        return punct_emph_amplifier

    def _amplify_ep(self, text):
        # check for added emphasis resulting from exclamation points (up to 4 of them)
        ep_count = text.count("!")
        if ep_count > 4:
            ep_count = 4
        # (empirically derived mean sentiment intensity rating increase for
        # exclamation points)
        ep_amplifier = ep_count * 0.292
        return ep_amplifier

    def _amplify_qm(self, text):
        # check for added emphasis resulting from question marks (2 or 3+)
        qm_count = text.count("?")
        qm_amplifier = 0
        if qm_count > 1:
            if qm_count <= 3:
                # (empirically derived mean sentiment intensity rating increase for
                # question marks)
                qm_amplifier = qm_count * 0.18
            else:
                qm_amplifier = 0.96
        return qm_amplifier

    def _sift_sentiment_scores(self, sentiments):
        # want separate positive versus negative sentiment scores
        pos_sum = 0.0
        neg_sum = 0.0
        neu_count = 0
        for sentiment_score in sentiments:
            if sentiment_score > 0:
                pos_sum += (
                    float(sentiment_score) + 1
                )  # compensates for neutral words that are counted as 1
            if sentiment_score < 0:
                neg_sum += (
                    float(sentiment_score) - 1
                )  # when used with math.fabs(), compensates for neutrals
            if sentiment_score == 0:
                neu_count += 1
        return pos_sum, neg_sum, neu_count

    def score_valence(self, sentiments, text):
        if sentiments:
            sum_s = float(sum(sentiments))
            # compute and add emphasis from punctuation in text
            punct_emph_amplifier = self._punctuation_emphasis(sum_s, text)
            if sum_s > 0:
                sum_s += punct_emph_amplifier
            elif sum_s < 0:
                sum_s -= punct_emph_amplifier

            compound = self.constants.normalize(sum_s)
            # discriminate between positive, negative and neutral sentiment scores
            pos_sum, neg_sum, neu_count = self._sift_sentiment_scores(sentiments)

            if pos_sum > math.fabs(neg_sum):
                pos_sum += punct_emph_amplifier
            elif pos_sum < math.fabs(neg_sum):
                neg_sum -= punct_emph_amplifier

            total = pos_sum + math.fabs(neg_sum) + neu_count
            pos = math.fabs(pos_sum / total)
            neg = math.fabs(neg_sum / total)
            neu = math.fabs(neu_count / total)

        else:
            compound = 0.0
            pos = 0.0
            neg = 0.0
            neu = 0.0

        sentiment_dict = {
            "neg": round(neg, 3),
            "neu": round(neu, 3),
            "pos": round(pos, 3),
            "compound": round(compound, 4),
        }

        return sentiment_dict

# === NexusCore/openenv\Lib\site-packages\numpy\_core\numerictypes.py ===
"""
numerictypes: Define the numeric type objects

This module is designed so "from numerictypes import \\*" is safe.
Exported symbols include:

  Dictionary with all registered number types (including aliases):
    sctypeDict

  Type objects (not all will be available, depends on platform):
      see variable sctypes for which ones you have

    Bit-width names

    int8 int16 int32 int64
    uint8 uint16 uint32 uint64
    float16 float32 float64 float96 float128
    complex64 complex128 complex192 complex256
    datetime64 timedelta64

    c-based names

    bool

    object_

    void, str_

    byte, ubyte,
    short, ushort
    intc, uintc,
    intp, uintp,
    int_, uint,
    longlong, ulonglong,

    single, csingle,
    double, cdouble,
    longdouble, clongdouble,

   As part of the type-hierarchy:    xx -- is bit-width

   generic
     +-> bool                                   (kind=b)
     +-> number
     |   +-> integer
     |   |   +-> signedinteger     (intxx)      (kind=i)
     |   |   |     byte
     |   |   |     short
     |   |   |     intc
     |   |   |     intp
     |   |   |     int_
     |   |   |     longlong
     |   |   \\-> unsignedinteger  (uintxx)     (kind=u)
     |   |         ubyte
     |   |         ushort
     |   |         uintc
     |   |         uintp
     |   |         uint
     |   |         ulonglong
     |   +-> inexact
     |       +-> floating          (floatxx)    (kind=f)
     |       |     half
     |       |     single
     |       |     double
     |       |     longdouble
     |       \\-> complexfloating  (complexxx)  (kind=c)
     |             csingle
     |             cdouble
     |             clongdouble
     +-> flexible
     |   +-> character
     |   |     bytes_                           (kind=S)
     |   |     str_                             (kind=U)
     |   |
     |   \\-> void                              (kind=V)
     \\-> object_ (not used much)               (kind=O)

"""
import numbers
import warnings

from numpy._utils import set_module

from . import multiarray as ma
from .multiarray import (
    busday_count,
    busday_offset,
    busdaycalendar,
    datetime_as_string,
    datetime_data,
    dtype,
    is_busday,
    ndarray,
)

# we add more at the bottom
__all__ = [
    'ScalarType', 'typecodes', 'issubdtype', 'datetime_data',
    'datetime_as_string', 'busday_offset', 'busday_count',
    'is_busday', 'busdaycalendar', 'isdtype'
]

# we don't need all these imports, but we need to keep them for compatibility
# for users using np._core.numerictypes.UPPER_TABLE
# we don't export these for import *, but we do want them accessible
# as numerictypes.bool, etc.
from builtins import bool, bytes, complex, float, int, object, str  # noqa: F401, UP029

from ._dtype import _kind_name
from ._string_helpers import (  # noqa: F401
    LOWER_TABLE,
    UPPER_TABLE,
    english_capitalize,
    english_lower,
    english_upper,
)
from ._type_aliases import allTypes, sctypeDict, sctypes

# We use this later
generic = allTypes['generic']

genericTypeRank = ['bool', 'int8', 'uint8', 'int16', 'uint16',
                   'int32', 'uint32', 'int64', 'uint64',
                   'float16', 'float32', 'float64', 'float96', 'float128',
                   'complex64', 'complex128', 'complex192', 'complex256',
                   'object']

@set_module('numpy')
def maximum_sctype(t):
    """
    Return the scalar type of highest precision of the same kind as the input.

    .. deprecated:: 2.0
        Use an explicit dtype like int64 or float64 instead.

    Parameters
    ----------
    t : dtype or dtype specifier
        The input data type. This can be a `dtype` object or an object that
        is convertible to a `dtype`.

    Returns
    -------
    out : dtype
        The highest precision data type of the same kind (`dtype.kind`) as `t`.

    See Also
    --------
    obj2sctype, mintypecode, sctype2char
    dtype

    Examples
    --------
    >>> from numpy._core.numerictypes import maximum_sctype
    >>> maximum_sctype(int)
    <class 'numpy.int64'>
    >>> maximum_sctype(np.uint8)
    <class 'numpy.uint64'>
    >>> maximum_sctype(complex)
    <class 'numpy.complex256'> # may vary

    >>> maximum_sctype(str)
    <class 'numpy.str_'>

    >>> maximum_sctype('i2')
    <class 'numpy.int64'>
    >>> maximum_sctype('f4')
    <class 'numpy.float128'> # may vary

    """

    # Deprecated in NumPy 2.0, 2023-07-11
    warnings.warn(
        "`maximum_sctype` is deprecated. Use an explicit dtype like int64 "
        "or float64 instead. (deprecated in NumPy 2.0)",
        DeprecationWarning,
        stacklevel=2
    )

    g = obj2sctype(t)
    if g is None:
        return t
    t = g
    base = _kind_name(dtype(t))
    if base in sctypes:
        return sctypes[base][-1]
    else:
        return t


@set_module('numpy')
def issctype(rep):
    """
    Determines whether the given object represents a scalar data-type.

    Parameters
    ----------
    rep : any
        If `rep` is an instance of a scalar dtype, True is returned. If not,
        False is returned.

    Returns
    -------
    out : bool
        Boolean result of check whether `rep` is a scalar dtype.

    See Also
    --------
    issubsctype, issubdtype, obj2sctype, sctype2char

    Examples
    --------
    >>> from numpy._core.numerictypes import issctype
    >>> issctype(np.int32)
    True
    >>> issctype(list)
    False
    >>> issctype(1.1)
    False

    Strings are also a scalar type:

    >>> issctype(np.dtype('str'))
    True

    """
    if not isinstance(rep, (type, dtype)):
        return False
    try:
        res = obj2sctype(rep)
        if res and res != object_:
            return True
        else:
            return False
    except Exception:
        return False


def obj2sctype(rep, default=None):
    """
    Return the scalar dtype or NumPy equivalent of Python type of an object.

    Parameters
    ----------
    rep : any
        The object of which the type is returned.
    default : any, optional
        If given, this is returned for objects whose types can not be
        determined. If not given, None is returned for those objects.

    Returns
    -------
    dtype : dtype or Python type
        The data type of `rep`.

    See Also
    --------
    sctype2char, issctype, issubsctype, issubdtype

    Examples
    --------
    >>> from numpy._core.numerictypes import obj2sctype
    >>> obj2sctype(np.int32)
    <class 'numpy.int32'>
    >>> obj2sctype(np.array([1., 2.]))
    <class 'numpy.float64'>
    >>> obj2sctype(np.array([1.j]))
    <class 'numpy.complex128'>

    >>> obj2sctype(dict)
    <class 'numpy.object_'>
    >>> obj2sctype('string')

    >>> obj2sctype(1, default=list)
    <class 'list'>

    """
    # prevent abstract classes being upcast
    if isinstance(rep, type) and issubclass(rep, generic):
        return rep
    # extract dtype from arrays
    if isinstance(rep, ndarray):
        return rep.dtype.type
    # fall back on dtype to convert
    try:
        res = dtype(rep)
    except Exception:
        return default
    else:
        return res.type


@set_module('numpy')
def issubclass_(arg1, arg2):
    """
    Determine if a class is a subclass of a second class.

    `issubclass_` is equivalent to the Python built-in ``issubclass``,
    except that it returns False instead of raising a TypeError if one
    of the arguments is not a class.

    Parameters
    ----------
    arg1 : class
        Input class. True is returned if `arg1` is a subclass of `arg2`.
    arg2 : class or tuple of classes.
        Input class. If a tuple of classes, True is returned if `arg1` is a
        subclass of any of the tuple elements.

    Returns
    -------
    out : bool
        Whether `arg1` is a subclass of `arg2` or not.

    See Also
    --------
    issubsctype, issubdtype, issctype

    Examples
    --------
    >>> np.issubclass_(np.int32, int)
    False
    >>> np.issubclass_(np.int32, float)
    False
    >>> np.issubclass_(np.float64, float)
    True

    """
    try:
        return issubclass(arg1, arg2)
    except TypeError:
        return False


@set_module('numpy')
def issubsctype(arg1, arg2):
    """
    Determine if the first argument is a subclass of the second argument.

    Parameters
    ----------
    arg1, arg2 : dtype or dtype specifier
        Data-types.

    Returns
    -------
    out : bool
        The result.

    See Also
    --------
    issctype, issubdtype, obj2sctype

    Examples
    --------
    >>> from numpy._core import issubsctype
    >>> issubsctype('S8', str)
    False
    >>> issubsctype(np.array([1]), int)
    True
    >>> issubsctype(np.array([1]), float)
    False

    """
    return issubclass(obj2sctype(arg1), obj2sctype(arg2))


class _PreprocessDTypeError(Exception):
    pass


def _preprocess_dtype(dtype):
    """
    Preprocess dtype argument by:
      1. fetching type from a data type
      2. verifying that types are built-in NumPy dtypes
    """
    if isinstance(dtype, ma.dtype):
        dtype = dtype.type
    if isinstance(dtype, ndarray) or dtype not in allTypes.values():
        raise _PreprocessDTypeError
    return dtype


@set_module('numpy')
def isdtype(dtype, kind):
    """
    Determine if a provided dtype is of a specified data type ``kind``.

    This function only supports built-in NumPy's data types.
    Third-party dtypes are not yet supported.

    Parameters
    ----------
    dtype : dtype
        The input dtype.
    kind : dtype or str or tuple of dtypes/strs.
        dtype or dtype kind. Allowed dtype kinds are:
        * ``'bool'`` : boolean kind
        * ``'signed integer'`` : signed integer data types
        * ``'unsigned integer'`` : unsigned integer data types
        * ``'integral'`` : integer data types
        * ``'real floating'`` : real-valued floating-point data types
        * ``'complex floating'`` : complex floating-point data types
        * ``'numeric'`` : numeric data types

    Returns
    -------
    out : bool

    See Also
    --------
    issubdtype

    Examples
    --------
    >>> import numpy as np
    >>> np.isdtype(np.float32, np.float64)
    False
    >>> np.isdtype(np.float32, "real floating")
    True
    >>> np.isdtype(np.complex128, ("real floating", "complex floating"))
    True

    """
    try:
        dtype = _preprocess_dtype(dtype)
    except _PreprocessDTypeError:
        raise TypeError(
            "dtype argument must be a NumPy dtype, "
            f"but it is a {type(dtype)}."
        ) from None

    input_kinds = kind if isinstance(kind, tuple) else (kind,)

    processed_kinds = set()

    for kind in input_kinds:
        if kind == "bool":
            processed_kinds.add(allTypes["bool"])
        elif kind == "signed integer":
            processed_kinds.update(sctypes["int"])
        elif kind == "unsigned integer":
            processed_kinds.update(sctypes["uint"])
        elif kind == "integral":
            processed_kinds.update(sctypes["int"] + sctypes["uint"])
        elif kind == "real floating":
            processed_kinds.update(sctypes["float"])
        elif kind == "complex floating":
            processed_kinds.update(sctypes["complex"])
        elif kind == "numeric":
            processed_kinds.update(
                sctypes["int"] + sctypes["uint"] +
                sctypes["float"] + sctypes["complex"]
            )
        elif isinstance(kind, str):
            raise ValueError(
                "kind argument is a string, but"
                f" {kind!r} is not a known kind name."
            )
        else:
            try:
                kind = _preprocess_dtype(kind)
            except _PreprocessDTypeError:
                raise TypeError(
                    "kind argument must be comprised of "
                    "NumPy dtypes or strings only, "
                    f"but is a {type(kind)}."
                ) from None
            processed_kinds.add(kind)

    return dtype in processed_kinds


@set_module('numpy')
def issubdtype(arg1, arg2):
    r"""
    Returns True if first argument is a typecode lower/equal in type hierarchy.

    This is like the builtin :func:`issubclass`, but for `dtype`\ s.

    Parameters
    ----------
    arg1, arg2 : dtype_like
        `dtype` or object coercible to one

    Returns
    -------
    out : bool

    See Also
    --------
    :ref:`arrays.scalars` : Overview of the numpy type hierarchy.

    Examples
    --------
    `issubdtype` can be used to check the type of arrays:

    >>> ints = np.array([1, 2, 3], dtype=np.int32)
    >>> np.issubdtype(ints.dtype, np.integer)
    True
    >>> np.issubdtype(ints.dtype, np.floating)
    False

    >>> floats = np.array([1, 2, 3], dtype=np.float32)
    >>> np.issubdtype(floats.dtype, np.integer)
    False
    >>> np.issubdtype(floats.dtype, np.floating)
    True

    Similar types of different sizes are not subdtypes of each other:

    >>> np.issubdtype(np.float64, np.float32)
    False
    >>> np.issubdtype(np.float32, np.float64)
    False

    but both are subtypes of `floating`:

    >>> np.issubdtype(np.float64, np.floating)
    True
    >>> np.issubdtype(np.float32, np.floating)
    True

    For convenience, dtype-like objects are allowed too:

    >>> np.issubdtype('S1', np.bytes_)
    True
    >>> np.issubdtype('i4', np.signedinteger)
    True

    """
    if not issubclass_(arg1, generic):
        arg1 = dtype(arg1).type
    if not issubclass_(arg2, generic):
        arg2 = dtype(arg2).type

    return issubclass(arg1, arg2)


@set_module('numpy')
def sctype2char(sctype):
    """
    Return the string representation of a scalar dtype.

    Parameters
    ----------
    sctype : scalar dtype or object
        If a scalar dtype, the corresponding string character is
        returned. If an object, `sctype2char` tries to infer its scalar type
        and then return the corresponding string character.

    Returns
    -------
    typechar : str
        The string character corresponding to the scalar type.

    Raises
    ------
    ValueError
        If `sctype` is an object for which the type can not be inferred.

    See Also
    --------
    obj2sctype, issctype, issubsctype, mintypecode

    Examples
    --------
    >>> from numpy._core.numerictypes import sctype2char
    >>> for sctype in [np.int32, np.double, np.cdouble, np.bytes_, np.ndarray]:
    ...     print(sctype2char(sctype))
    l # may vary
    d
    D
    S
    O

    >>> x = np.array([1., 2-1.j])
    >>> sctype2char(x)
    'D'
    >>> sctype2char(list)
    'O'

    """
    sctype = obj2sctype(sctype)
    if sctype is None:
        raise ValueError("unrecognized type")
    if sctype not in sctypeDict.values():
        # for compatibility
        raise KeyError(sctype)
    return dtype(sctype).char


def _scalar_type_key(typ):
    """A ``key`` function for `sorted`."""
    dt = dtype(typ)
    return (dt.kind.lower(), dt.itemsize)


ScalarType = [int, float, complex, bool, bytes, str, memoryview]
ScalarType += sorted(set(sctypeDict.values()), key=_scalar_type_key)
ScalarType = tuple(ScalarType)


# Now add the types we've determined to this module
for key in allTypes:
    globals()[key] = allTypes[key]
    __all__.append(key)

del key

typecodes = {'Character': 'c',
             'Integer': 'bhilqnp',
             'UnsignedInteger': 'BHILQNP',
             'Float': 'efdg',
             'Complex': 'FDG',
             'AllInteger': 'bBhHiIlLqQnNpP',
             'AllFloat': 'efdgFDG',
             'Datetime': 'Mm',
             'All': '?bhilqnpBHILQNPefdgFDGSUVOMm'}

# backwards compatibility --- deprecated name
# Formal deprecation: Numpy 1.20.0, 2020-10-19 (see numpy/__init__.py)
typeDict = sctypeDict

def _register_types():
    numbers.Integral.register(integer)
    numbers.Complex.register(inexact)
    numbers.Real.register(floating)
    numbers.Number.register(number)


_register_types()

# === NexusCore/openenv\Lib\site-packages\pip\_internal\req\req_uninstall.py ===
import functools
import os
import sys
import sysconfig
from importlib.util import cache_from_source
from typing import Any, Callable, Dict, Generator, Iterable, List, Optional, Set, Tuple

from pip._internal.exceptions import LegacyDistutilsInstall, UninstallMissingRecord
from pip._internal.locations import get_bin_prefix, get_bin_user
from pip._internal.metadata import BaseDistribution
from pip._internal.utils.compat import WINDOWS
from pip._internal.utils.egg_link import egg_link_path_from_location
from pip._internal.utils.logging import getLogger, indent_log
from pip._internal.utils.misc import ask, normalize_path, renames, rmtree
from pip._internal.utils.temp_dir import AdjacentTempDirectory, TempDirectory
from pip._internal.utils.virtualenv import running_under_virtualenv

logger = getLogger(__name__)


def _script_names(
    bin_dir: str, script_name: str, is_gui: bool
) -> Generator[str, None, None]:
    """Create the fully qualified name of the files created by
    {console,gui}_scripts for the given ``dist``.
    Returns the list of file names
    """
    exe_name = os.path.join(bin_dir, script_name)
    yield exe_name
    if not WINDOWS:
        return
    yield f"{exe_name}.exe"
    yield f"{exe_name}.exe.manifest"
    if is_gui:
        yield f"{exe_name}-script.pyw"
    else:
        yield f"{exe_name}-script.py"


def _unique(
    fn: Callable[..., Generator[Any, None, None]]
) -> Callable[..., Generator[Any, None, None]]:
    @functools.wraps(fn)
    def unique(*args: Any, **kw: Any) -> Generator[Any, None, None]:
        seen: Set[Any] = set()
        for item in fn(*args, **kw):
            if item not in seen:
                seen.add(item)
                yield item

    return unique


@_unique
def uninstallation_paths(dist: BaseDistribution) -> Generator[str, None, None]:
    """
    Yield all the uninstallation paths for dist based on RECORD-without-.py[co]

    Yield paths to all the files in RECORD. For each .py file in RECORD, add
    the .pyc and .pyo in the same directory.

    UninstallPathSet.add() takes care of the __pycache__ .py[co].

    If RECORD is not found, raises an error,
    with possible information from the INSTALLER file.

    https://packaging.python.org/specifications/recording-installed-packages/
    """
    location = dist.location
    assert location is not None, "not installed"

    entries = dist.iter_declared_entries()
    if entries is None:
        raise UninstallMissingRecord(distribution=dist)

    for entry in entries:
        path = os.path.join(location, entry)
        yield path
        if path.endswith(".py"):
            dn, fn = os.path.split(path)
            base = fn[:-3]
            path = os.path.join(dn, base + ".pyc")
            yield path
            path = os.path.join(dn, base + ".pyo")
            yield path


def compact(paths: Iterable[str]) -> Set[str]:
    """Compact a path set to contain the minimal number of paths
    necessary to contain all paths in the set. If /a/path/ and
    /a/path/to/a/file.txt are both in the set, leave only the
    shorter path."""

    sep = os.path.sep
    short_paths: Set[str] = set()
    for path in sorted(paths, key=len):
        should_skip = any(
            path.startswith(shortpath.rstrip("*"))
            and path[len(shortpath.rstrip("*").rstrip(sep))] == sep
            for shortpath in short_paths
        )
        if not should_skip:
            short_paths.add(path)
    return short_paths


def compress_for_rename(paths: Iterable[str]) -> Set[str]:
    """Returns a set containing the paths that need to be renamed.

    This set may include directories when the original sequence of paths
    included every file on disk.
    """
    case_map = {os.path.normcase(p): p for p in paths}
    remaining = set(case_map)
    unchecked = sorted({os.path.split(p)[0] for p in case_map.values()}, key=len)
    wildcards: Set[str] = set()

    def norm_join(*a: str) -> str:
        return os.path.normcase(os.path.join(*a))

    for root in unchecked:
        if any(os.path.normcase(root).startswith(w) for w in wildcards):
            # This directory has already been handled.
            continue

        all_files: Set[str] = set()
        all_subdirs: Set[str] = set()
        for dirname, subdirs, files in os.walk(root):
            all_subdirs.update(norm_join(root, dirname, d) for d in subdirs)
            all_files.update(norm_join(root, dirname, f) for f in files)
        # If all the files we found are in our remaining set of files to
        # remove, then remove them from the latter set and add a wildcard
        # for the directory.
        if not (all_files - remaining):
            remaining.difference_update(all_files)
            wildcards.add(root + os.sep)

    return set(map(case_map.__getitem__, remaining)) | wildcards


def compress_for_output_listing(paths: Iterable[str]) -> Tuple[Set[str], Set[str]]:
    """Returns a tuple of 2 sets of which paths to display to user

    The first set contains paths that would be deleted. Files of a package
    are not added and the top-level directory of the package has a '*' added
    at the end - to signify that all it's contents are removed.

    The second set contains files that would have been skipped in the above
    folders.
    """

    will_remove = set(paths)
    will_skip = set()

    # Determine folders and files
    folders = set()
    files = set()
    for path in will_remove:
        if path.endswith(".pyc"):
            continue
        if path.endswith("__init__.py") or ".dist-info" in path:
            folders.add(os.path.dirname(path))
        files.add(path)

    _normcased_files = set(map(os.path.normcase, files))

    folders = compact(folders)

    # This walks the tree using os.walk to not miss extra folders
    # that might get added.
    for folder in folders:
        for dirpath, _, dirfiles in os.walk(folder):
            for fname in dirfiles:
                if fname.endswith(".pyc"):
                    continue

                file_ = os.path.join(dirpath, fname)
                if (
                    os.path.isfile(file_)
                    and os.path.normcase(file_) not in _normcased_files
                ):
                    # We are skipping this file. Add it to the set.
                    will_skip.add(file_)

    will_remove = files | {os.path.join(folder, "*") for folder in folders}

    return will_remove, will_skip


class StashedUninstallPathSet:
    """A set of file rename operations to stash files while
    tentatively uninstalling them."""

    def __init__(self) -> None:
        # Mapping from source file root to [Adjacent]TempDirectory
        # for files under that directory.
        self._save_dirs: Dict[str, TempDirectory] = {}
        # (old path, new path) tuples for each move that may need
        # to be undone.
        self._moves: List[Tuple[str, str]] = []

    def _get_directory_stash(self, path: str) -> str:
        """Stashes a directory.

        Directories are stashed adjacent to their original location if
        possible, or else moved/copied into the user's temp dir."""

        try:
            save_dir: TempDirectory = AdjacentTempDirectory(path)
        except OSError:
            save_dir = TempDirectory(kind="uninstall")
        self._save_dirs[os.path.normcase(path)] = save_dir

        return save_dir.path

    def _get_file_stash(self, path: str) -> str:
        """Stashes a file.

        If no root has been provided, one will be created for the directory
        in the user's temp directory."""
        path = os.path.normcase(path)
        head, old_head = os.path.dirname(path), None
        save_dir = None

        while head != old_head:
            try:
                save_dir = self._save_dirs[head]
                break
            except KeyError:
                pass
            head, old_head = os.path.dirname(head), head
        else:
            # Did not find any suitable root
            head = os.path.dirname(path)
            save_dir = TempDirectory(kind="uninstall")
            self._save_dirs[head] = save_dir

        relpath = os.path.relpath(path, head)
        if relpath and relpath != os.path.curdir:
            return os.path.join(save_dir.path, relpath)
        return save_dir.path

    def stash(self, path: str) -> str:
        """Stashes the directory or file and returns its new location.
        Handle symlinks as files to avoid modifying the symlink targets.
        """
        path_is_dir = os.path.isdir(path) and not os.path.islink(path)
        if path_is_dir:
            new_path = self._get_directory_stash(path)
        else:
            new_path = self._get_file_stash(path)

        self._moves.append((path, new_path))
        if path_is_dir and os.path.isdir(new_path):
            # If we're moving a directory, we need to
            # remove the destination first or else it will be
            # moved to inside the existing directory.
            # We just created new_path ourselves, so it will
            # be removable.
            os.rmdir(new_path)
        renames(path, new_path)
        return new_path

    def commit(self) -> None:
        """Commits the uninstall by removing stashed files."""
        for save_dir in self._save_dirs.values():
            save_dir.cleanup()
        self._moves = []
        self._save_dirs = {}

    def rollback(self) -> None:
        """Undoes the uninstall by moving stashed files back."""
        for p in self._moves:
            logger.info("Moving to %s\n from %s", *p)

        for new_path, path in self._moves:
            try:
                logger.debug("Replacing %s from %s", new_path, path)
                if os.path.isfile(new_path) or os.path.islink(new_path):
                    os.unlink(new_path)
                elif os.path.isdir(new_path):
                    rmtree(new_path)
                renames(path, new_path)
            except OSError as ex:
                logger.error("Failed to restore %s", new_path)
                logger.debug("Exception: %s", ex)

        self.commit()

    @property
    def can_rollback(self) -> bool:
        return bool(self._moves)


class UninstallPathSet:
    """A set of file paths to be removed in the uninstallation of a
    requirement."""

    def __init__(self, dist: BaseDistribution) -> None:
        self._paths: Set[str] = set()
        self._refuse: Set[str] = set()
        self._pth: Dict[str, UninstallPthEntries] = {}
        self._dist = dist
        self._moved_paths = StashedUninstallPathSet()
        # Create local cache of normalize_path results. Creating an UninstallPathSet
        # can result in hundreds/thousands of redundant calls to normalize_path with
        # the same args, which hurts performance.
        self._normalize_path_cached = functools.lru_cache(normalize_path)

    def _permitted(self, path: str) -> bool:
        """
        Return True if the given path is one we are permitted to
        remove/modify, False otherwise.

        """
        # aka is_local, but caching normalized sys.prefix
        if not running_under_virtualenv():
            return True
        return path.startswith(self._normalize_path_cached(sys.prefix))

    def add(self, path: str) -> None:
        head, tail = os.path.split(path)

        # we normalize the head to resolve parent directory symlinks, but not
        # the tail, since we only want to uninstall symlinks, not their targets
        path = os.path.join(self._normalize_path_cached(head), os.path.normcase(tail))

        if not os.path.exists(path):
            return
        if self._permitted(path):
            self._paths.add(path)
        else:
            self._refuse.add(path)

        # __pycache__ files can show up after 'installed-files.txt' is created,
        # due to imports
        if os.path.splitext(path)[1] == ".py":
            self.add(cache_from_source(path))

    def add_pth(self, pth_file: str, entry: str) -> None:
        pth_file = self._normalize_path_cached(pth_file)
        if self._permitted(pth_file):
            if pth_file not in self._pth:
                self._pth[pth_file] = UninstallPthEntries(pth_file)
            self._pth[pth_file].add(entry)
        else:
            self._refuse.add(pth_file)

    def remove(self, auto_confirm: bool = False, verbose: bool = False) -> None:
        """Remove paths in ``self._paths`` with confirmation (unless
        ``auto_confirm`` is True)."""

        if not self._paths:
            logger.info(
                "Can't uninstall '%s'. No files were found to uninstall.",
                self._dist.raw_name,
            )
            return

        dist_name_version = f"{self._dist.raw_name}-{self._dist.raw_version}"
        logger.info("Uninstalling %s:", dist_name_version)

        with indent_log():
            if auto_confirm or self._allowed_to_proceed(verbose):
                moved = self._moved_paths

                for_rename = compress_for_rename(self._paths)

                for path in sorted(compact(for_rename)):
                    moved.stash(path)
                    logger.verbose("Removing file or directory %s", path)

                for pth in self._pth.values():
                    pth.remove()

                logger.info("Successfully uninstalled %s", dist_name_version)

    def _allowed_to_proceed(self, verbose: bool) -> bool:
        """Display which files would be deleted and prompt for confirmation"""

        def _display(msg: str, paths: Iterable[str]) -> None:
            if not paths:
                return

            logger.info(msg)
            with indent_log():
                for path in sorted(compact(paths)):
                    logger.info(path)

        if not verbose:
            will_remove, will_skip = compress_for_output_listing(self._paths)
        else:
            # In verbose mode, display all the files that are going to be
            # deleted.
            will_remove = set(self._paths)
            will_skip = set()

        _display("Would remove:", will_remove)
        _display("Would not remove (might be manually added):", will_skip)
        _display("Would not remove (outside of prefix):", self._refuse)
        if verbose:
            _display("Will actually move:", compress_for_rename(self._paths))

        return ask("Proceed (Y/n)? ", ("y", "n", "")) != "n"

    def rollback(self) -> None:
        """Rollback the changes previously made by remove()."""
        if not self._moved_paths.can_rollback:
            logger.error(
                "Can't roll back %s; was not uninstalled",
                self._dist.raw_name,
            )
            return
        logger.info("Rolling back uninstall of %s", self._dist.raw_name)
        self._moved_paths.rollback()
        for pth in self._pth.values():
            pth.rollback()

    def commit(self) -> None:
        """Remove temporary save dir: rollback will no longer be possible."""
        self._moved_paths.commit()

    @classmethod
    def from_dist(cls, dist: BaseDistribution) -> "UninstallPathSet":
        dist_location = dist.location
        info_location = dist.info_location
        if dist_location is None:
            logger.info(
                "Not uninstalling %s since it is not installed",
                dist.canonical_name,
            )
            return cls(dist)

        normalized_dist_location = normalize_path(dist_location)
        if not dist.local:
            logger.info(
                "Not uninstalling %s at %s, outside environment %s",
                dist.canonical_name,
                normalized_dist_location,
                sys.prefix,
            )
            return cls(dist)

        if normalized_dist_location in {
            p
            for p in {sysconfig.get_path("stdlib"), sysconfig.get_path("platstdlib")}
            if p
        }:
            logger.info(
                "Not uninstalling %s at %s, as it is in the standard library.",
                dist.canonical_name,
                normalized_dist_location,
            )
            return cls(dist)

        paths_to_remove = cls(dist)
        develop_egg_link = egg_link_path_from_location(dist.raw_name)

        # Distribution is installed with metadata in a "flat" .egg-info
        # directory. This means it is not a modern .dist-info installation, an
        # egg, or legacy editable.
        setuptools_flat_installation = (
            dist.installed_with_setuptools_egg_info
            and info_location is not None
            and os.path.exists(info_location)
            # If dist is editable and the location points to a ``.egg-info``,
            # we are in fact in the legacy editable case.
            and not info_location.endswith(f"{dist.setuptools_filename}.egg-info")
        )

        # Uninstall cases order do matter as in the case of 2 installs of the
        # same package, pip needs to uninstall the currently detected version
        if setuptools_flat_installation:
            if info_location is not None:
                paths_to_remove.add(info_location)
            installed_files = dist.iter_declared_entries()
            if installed_files is not None:
                for installed_file in installed_files:
                    paths_to_remove.add(os.path.join(dist_location, installed_file))
            # FIXME: need a test for this elif block
            # occurs with --single-version-externally-managed/--record outside
            # of pip
            elif dist.is_file("top_level.txt"):
                try:
                    namespace_packages = dist.read_text("namespace_packages.txt")
                except FileNotFoundError:
                    namespaces = []
                else:
                    namespaces = namespace_packages.splitlines(keepends=False)
                for top_level_pkg in [
                    p
                    for p in dist.read_text("top_level.txt").splitlines()
                    if p and p not in namespaces
                ]:
                    path = os.path.join(dist_location, top_level_pkg)
                    paths_to_remove.add(path)
                    paths_to_remove.add(f"{path}.py")
                    paths_to_remove.add(f"{path}.pyc")
                    paths_to_remove.add(f"{path}.pyo")

        elif dist.installed_by_distutils:
            raise LegacyDistutilsInstall(distribution=dist)

        elif dist.installed_as_egg:
            # package installed by easy_install
            # We cannot match on dist.egg_name because it can slightly vary
            # i.e. setuptools-0.6c11-py2.6.egg vs setuptools-0.6rc11-py2.6.egg
            paths_to_remove.add(dist_location)
            easy_install_egg = os.path.split(dist_location)[1]
            easy_install_pth = os.path.join(
                os.path.dirname(dist_location),
                "easy-install.pth",
            )
            paths_to_remove.add_pth(easy_install_pth, "./" + easy_install_egg)

        elif dist.installed_with_dist_info:
            for path in uninstallation_paths(dist):
                paths_to_remove.add(path)

        elif develop_egg_link:
            # PEP 660 modern editable is handled in the ``.dist-info`` case
            # above, so this only covers the setuptools-style editable.
            with open(develop_egg_link) as fh:
                link_pointer = os.path.normcase(fh.readline().strip())
                normalized_link_pointer = paths_to_remove._normalize_path_cached(
                    link_pointer
                )
            assert os.path.samefile(
                normalized_link_pointer, normalized_dist_location
            ), (
                f"Egg-link {develop_egg_link} (to {link_pointer}) does not match "
                f"installed location of {dist.raw_name} (at {dist_location})"
            )
            paths_to_remove.add(develop_egg_link)
            easy_install_pth = os.path.join(
                os.path.dirname(develop_egg_link), "easy-install.pth"
            )
            paths_to_remove.add_pth(easy_install_pth, dist_location)

        else:
            logger.debug(
                "Not sure how to uninstall: %s - Check: %s",
                dist,
                dist_location,
            )

        if dist.in_usersite:
            bin_dir = get_bin_user()
        else:
            bin_dir = get_bin_prefix()

        # find distutils scripts= scripts
        try:
            for script in dist.iter_distutils_script_names():
                paths_to_remove.add(os.path.join(bin_dir, script))
                if WINDOWS:
                    paths_to_remove.add(os.path.join(bin_dir, f"{script}.bat"))
        except (FileNotFoundError, NotADirectoryError):
            pass

        # find console_scripts and gui_scripts
        def iter_scripts_to_remove(
            dist: BaseDistribution,
            bin_dir: str,
        ) -> Generator[str, None, None]:
            for entry_point in dist.iter_entry_points():
                if entry_point.group == "console_scripts":
                    yield from _script_names(bin_dir, entry_point.name, False)
                elif entry_point.group == "gui_scripts":
                    yield from _script_names(bin_dir, entry_point.name, True)

        for s in iter_scripts_to_remove(dist, bin_dir):
            paths_to_remove.add(s)

        return paths_to_remove


class UninstallPthEntries:
    def __init__(self, pth_file: str) -> None:
        self.file = pth_file
        self.entries: Set[str] = set()
        self._saved_lines: Optional[List[bytes]] = None

    def add(self, entry: str) -> None:
        entry = os.path.normcase(entry)
        # On Windows, os.path.normcase converts the entry to use
        # backslashes.  This is correct for entries that describe absolute
        # paths outside of site-packages, but all the others use forward
        # slashes.
        # os.path.splitdrive is used instead of os.path.isabs because isabs
        # treats non-absolute paths with drive letter markings like c:foo\bar
        # as absolute paths. It also does not recognize UNC paths if they don't
        # have more than "\\sever\share". Valid examples: "\\server\share\" or
        # "\\server\share\folder".
        if WINDOWS and not os.path.splitdrive(entry)[0]:
            entry = entry.replace("\\", "/")
        self.entries.add(entry)

    def remove(self) -> None:
        logger.verbose("Removing pth entries from %s:", self.file)

        # If the file doesn't exist, log a warning and return
        if not os.path.isfile(self.file):
            logger.warning("Cannot remove entries from nonexistent file %s", self.file)
            return
        with open(self.file, "rb") as fh:
            # windows uses '\r\n' with py3k, but uses '\n' with py2.x
            lines = fh.readlines()
            self._saved_lines = lines
        if any(b"\r\n" in line for line in lines):
            endline = "\r\n"
        else:
            endline = "\n"
        # handle missing trailing newline
        if lines and not lines[-1].endswith(endline.encode("utf-8")):
            lines[-1] = lines[-1] + endline.encode("utf-8")
        for entry in self.entries:
            try:
                logger.verbose("Removing entry: %s", entry)
                lines.remove((entry + endline).encode("utf-8"))
            except ValueError:
                pass
        with open(self.file, "wb") as fh:
            fh.writelines(lines)

    def rollback(self) -> bool:
        if self._saved_lines is None:
            logger.error("Cannot roll back changes to %s, none were made", self.file)
            return False
        logger.debug("Rolling %s back to previous state", self.file)
        with open(self.file, "wb") as fh:
            fh.writelines(self._saved_lines)
        return True

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\jaraco\functools\__init__.py ===
import collections.abc
import functools
import inspect
import itertools
import operator
import time
import types
import warnings

import more_itertools


def compose(*funcs):
    """
    Compose any number of unary functions into a single unary function.

    >>> import textwrap
    >>> expected = str.strip(textwrap.dedent(compose.__doc__))
    >>> strip_and_dedent = compose(str.strip, textwrap.dedent)
    >>> strip_and_dedent(compose.__doc__) == expected
    True

    Compose also allows the innermost function to take arbitrary arguments.

    >>> round_three = lambda x: round(x, ndigits=3)
    >>> f = compose(round_three, int.__truediv__)
    >>> [f(3*x, x+1) for x in range(1,10)]
    [1.5, 2.0, 2.25, 2.4, 2.5, 2.571, 2.625, 2.667, 2.7]
    """

    def compose_two(f1, f2):
        return lambda *args, **kwargs: f1(f2(*args, **kwargs))

    return functools.reduce(compose_two, funcs)


def once(func):
    """
    Decorate func so it's only ever called the first time.

    This decorator can ensure that an expensive or non-idempotent function
    will not be expensive on subsequent calls and is idempotent.

    >>> add_three = once(lambda a: a+3)
    >>> add_three(3)
    6
    >>> add_three(9)
    6
    >>> add_three('12')
    6

    To reset the stored value, simply clear the property ``saved_result``.

    >>> del add_three.saved_result
    >>> add_three(9)
    12
    >>> add_three(8)
    12

    Or invoke 'reset()' on it.

    >>> add_three.reset()
    >>> add_three(-3)
    0
    >>> add_three(0)
    0
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not hasattr(wrapper, 'saved_result'):
            wrapper.saved_result = func(*args, **kwargs)
        return wrapper.saved_result

    wrapper.reset = lambda: vars(wrapper).__delitem__('saved_result')
    return wrapper


def method_cache(method, cache_wrapper=functools.lru_cache()):
    """
    Wrap lru_cache to support storing the cache data in the object instances.

    Abstracts the common paradigm where the method explicitly saves an
    underscore-prefixed protected property on first call and returns that
    subsequently.

    >>> class MyClass:
    ...     calls = 0
    ...
    ...     @method_cache
    ...     def method(self, value):
    ...         self.calls += 1
    ...         return value

    >>> a = MyClass()
    >>> a.method(3)
    3
    >>> for x in range(75):
    ...     res = a.method(x)
    >>> a.calls
    75

    Note that the apparent behavior will be exactly like that of lru_cache
    except that the cache is stored on each instance, so values in one
    instance will not flush values from another, and when an instance is
    deleted, so are the cached values for that instance.

    >>> b = MyClass()
    >>> for x in range(35):
    ...     res = b.method(x)
    >>> b.calls
    35
    >>> a.method(0)
    0
    >>> a.calls
    75

    Note that if method had been decorated with ``functools.lru_cache()``,
    a.calls would have been 76 (due to the cached value of 0 having been
    flushed by the 'b' instance).

    Clear the cache with ``.cache_clear()``

    >>> a.method.cache_clear()

    Same for a method that hasn't yet been called.

    >>> c = MyClass()
    >>> c.method.cache_clear()

    Another cache wrapper may be supplied:

    >>> cache = functools.lru_cache(maxsize=2)
    >>> MyClass.method2 = method_cache(lambda self: 3, cache_wrapper=cache)
    >>> a = MyClass()
    >>> a.method2()
    3

    Caution - do not subsequently wrap the method with another decorator, such
    as ``@property``, which changes the semantics of the function.

    See also
    http://code.activestate.com/recipes/577452-a-memoize-decorator-for-instance-methods/
    for another implementation and additional justification.
    """

    def wrapper(self, *args, **kwargs):
        # it's the first call, replace the method with a cached, bound method
        bound_method = types.MethodType(method, self)
        cached_method = cache_wrapper(bound_method)
        setattr(self, method.__name__, cached_method)
        return cached_method(*args, **kwargs)

    # Support cache clear even before cache has been created.
    wrapper.cache_clear = lambda: None

    return _special_method_cache(method, cache_wrapper) or wrapper


def _special_method_cache(method, cache_wrapper):
    """
    Because Python treats special methods differently, it's not
    possible to use instance attributes to implement the cached
    methods.

    Instead, install the wrapper method under a different name
    and return a simple proxy to that wrapper.

    https://github.com/jaraco/jaraco.functools/issues/5
    """
    name = method.__name__
    special_names = '__getattr__', '__getitem__'

    if name not in special_names:
        return None

    wrapper_name = '__cached' + name

    def proxy(self, /, *args, **kwargs):
        if wrapper_name not in vars(self):
            bound = types.MethodType(method, self)
            cache = cache_wrapper(bound)
            setattr(self, wrapper_name, cache)
        else:
            cache = getattr(self, wrapper_name)
        return cache(*args, **kwargs)

    return proxy


def apply(transform):
    """
    Decorate a function with a transform function that is
    invoked on results returned from the decorated function.

    >>> @apply(reversed)
    ... def get_numbers(start):
    ...     "doc for get_numbers"
    ...     return range(start, start+3)
    >>> list(get_numbers(4))
    [6, 5, 4]
    >>> get_numbers.__doc__
    'doc for get_numbers'
    """

    def wrap(func):
        return functools.wraps(func)(compose(transform, func))

    return wrap


def result_invoke(action):
    r"""
    Decorate a function with an action function that is
    invoked on the results returned from the decorated
    function (for its side effect), then return the original
    result.

    >>> @result_invoke(print)
    ... def add_two(a, b):
    ...     return a + b
    >>> x = add_two(2, 3)
    5
    >>> x
    5
    """

    def wrap(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            action(result)
            return result

        return wrapper

    return wrap


def invoke(f, /, *args, **kwargs):
    """
    Call a function for its side effect after initialization.

    The benefit of using the decorator instead of simply invoking a function
    after defining it is that it makes explicit the author's intent for the
    function to be called immediately. Whereas if one simply calls the
    function immediately, it's less obvious if that was intentional or
    incidental. It also avoids repeating the name - the two actions, defining
    the function and calling it immediately are modeled separately, but linked
    by the decorator construct.

    The benefit of having a function construct (opposed to just invoking some
    behavior inline) is to serve as a scope in which the behavior occurs. It
    avoids polluting the global namespace with local variables, provides an
    anchor on which to attach documentation (docstring), keeps the behavior
    logically separated (instead of conceptually separated or not separated at
    all), and provides potential to re-use the behavior for testing or other
    purposes.

    This function is named as a pithy way to communicate, "call this function
    primarily for its side effect", or "while defining this function, also
    take it aside and call it". It exists because there's no Python construct
    for "define and call" (nor should there be, as decorators serve this need
    just fine). The behavior happens immediately and synchronously.

    >>> @invoke
    ... def func(): print("called")
    called
    >>> func()
    called

    Use functools.partial to pass parameters to the initial call

    >>> @functools.partial(invoke, name='bingo')
    ... def func(name): print('called with', name)
    called with bingo
    """
    f(*args, **kwargs)
    return f


class Throttler:
    """Rate-limit a function (or other callable)."""

    def __init__(self, func, max_rate=float('Inf')):
        if isinstance(func, Throttler):
            func = func.func
        self.func = func
        self.max_rate = max_rate
        self.reset()

    def reset(self):
        self.last_called = 0

    def __call__(self, *args, **kwargs):
        self._wait()
        return self.func(*args, **kwargs)

    def _wait(self):
        """Ensure at least 1/max_rate seconds from last call."""
        elapsed = time.time() - self.last_called
        must_wait = 1 / self.max_rate - elapsed
        time.sleep(max(0, must_wait))
        self.last_called = time.time()

    def __get__(self, obj, owner=None):
        return first_invoke(self._wait, functools.partial(self.func, obj))


def first_invoke(func1, func2):
    """
    Return a function that when invoked will invoke func1 without
    any parameters (for its side effect) and then invoke func2
    with whatever parameters were passed, returning its result.
    """

    def wrapper(*args, **kwargs):
        func1()
        return func2(*args, **kwargs)

    return wrapper


method_caller = first_invoke(
    lambda: warnings.warn(
        '`jaraco.functools.method_caller` is deprecated, '
        'use `operator.methodcaller` instead',
        DeprecationWarning,
        stacklevel=3,
    ),
    operator.methodcaller,
)


def retry_call(func, cleanup=lambda: None, retries=0, trap=()):
    """
    Given a callable func, trap the indicated exceptions
    for up to 'retries' times, invoking cleanup on the
    exception. On the final attempt, allow any exceptions
    to propagate.
    """
    attempts = itertools.count() if retries == float('inf') else range(retries)
    for _ in attempts:
        try:
            return func()
        except trap:
            cleanup()

    return func()


def retry(*r_args, **r_kwargs):
    """
    Decorator wrapper for retry_call. Accepts arguments to retry_call
    except func and then returns a decorator for the decorated function.

    Ex:

    >>> @retry(retries=3)
    ... def my_func(a, b):
    ...     "this is my funk"
    ...     print(a, b)
    >>> my_func.__doc__
    'this is my funk'
    """

    def decorate(func):
        @functools.wraps(func)
        def wrapper(*f_args, **f_kwargs):
            bound = functools.partial(func, *f_args, **f_kwargs)
            return retry_call(bound, *r_args, **r_kwargs)

        return wrapper

    return decorate


def print_yielded(func):
    """
    Convert a generator into a function that prints all yielded elements.

    >>> @print_yielded
    ... def x():
    ...     yield 3; yield None
    >>> x()
    3
    None
    """
    print_all = functools.partial(map, print)
    print_results = compose(more_itertools.consume, print_all, func)
    return functools.wraps(func)(print_results)


def pass_none(func):
    """
    Wrap func so it's not called if its first param is None.

    >>> print_text = pass_none(print)
    >>> print_text('text')
    text
    >>> print_text(None)
    """

    @functools.wraps(func)
    def wrapper(param, /, *args, **kwargs):
        if param is not None:
            return func(param, *args, **kwargs)
        return None

    return wrapper


def assign_params(func, namespace):
    """
    Assign parameters from namespace where func solicits.

    >>> def func(x, y=3):
    ...     print(x, y)
    >>> assigned = assign_params(func, dict(x=2, z=4))
    >>> assigned()
    2 3

    The usual errors are raised if a function doesn't receive
    its required parameters:

    >>> assigned = assign_params(func, dict(y=3, z=4))
    >>> assigned()
    Traceback (most recent call last):
    TypeError: func() ...argument...

    It even works on methods:

    >>> class Handler:
    ...     def meth(self, arg):
    ...         print(arg)
    >>> assign_params(Handler().meth, dict(arg='crystal', foo='clear'))()
    crystal
    """
    sig = inspect.signature(func)
    params = sig.parameters.keys()
    call_ns = {k: namespace[k] for k in params if k in namespace}
    return functools.partial(func, **call_ns)


def save_method_args(method):
    """
    Wrap a method such that when it is called, the args and kwargs are
    saved on the method.

    >>> class MyClass:
    ...     @save_method_args
    ...     def method(self, a, b):
    ...         print(a, b)
    >>> my_ob = MyClass()
    >>> my_ob.method(1, 2)
    1 2
    >>> my_ob._saved_method.args
    (1, 2)
    >>> my_ob._saved_method.kwargs
    {}
    >>> my_ob.method(a=3, b='foo')
    3 foo
    >>> my_ob._saved_method.args
    ()
    >>> my_ob._saved_method.kwargs == dict(a=3, b='foo')
    True

    The arguments are stored on the instance, allowing for
    different instance to save different args.

    >>> your_ob = MyClass()
    >>> your_ob.method({str('x'): 3}, b=[4])
    {'x': 3} [4]
    >>> your_ob._saved_method.args
    ({'x': 3},)
    >>> my_ob._saved_method.args
    ()
    """
    args_and_kwargs = collections.namedtuple('args_and_kwargs', 'args kwargs')

    @functools.wraps(method)
    def wrapper(self, /, *args, **kwargs):
        attr_name = '_saved_' + method.__name__
        attr = args_and_kwargs(args, kwargs)
        setattr(self, attr_name, attr)
        return method(self, *args, **kwargs)

    return wrapper


def except_(*exceptions, replace=None, use=None):
    """
    Replace the indicated exceptions, if raised, with the indicated
    literal replacement or evaluated expression (if present).

    >>> safe_int = except_(ValueError)(int)
    >>> safe_int('five')
    >>> safe_int('5')
    5

    Specify a literal replacement with ``replace``.

    >>> safe_int_r = except_(ValueError, replace=0)(int)
    >>> safe_int_r('five')
    0

    Provide an expression to ``use`` to pass through particular parameters.

    >>> safe_int_pt = except_(ValueError, use='args[0]')(int)
    >>> safe_int_pt('five')
    'five'

    """

    def decorate(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exceptions:
                try:
                    return eval(use)
                except TypeError:
                    return replace

        return wrapper

    return decorate


def identity(x):
    """
    Return the argument.

    >>> o = object()
    >>> identity(o) is o
    True
    """
    return x


def bypass_when(check, *, _op=identity):
    """
    Decorate a function to return its parameter when ``check``.

    >>> bypassed = []  # False

    >>> @bypass_when(bypassed)
    ... def double(x):
    ...     return x * 2
    >>> double(2)
    4
    >>> bypassed[:] = [object()]  # True
    >>> double(2)
    2
    """

    def decorate(func):
        @functools.wraps(func)
        def wrapper(param, /):
            return param if _op(check) else func(param)

        return wrapper

    return decorate


def bypass_unless(check):
    """
    Decorate a function to return its parameter unless ``check``.

    >>> enabled = [object()]  # True

    >>> @bypass_unless(enabled)
    ... def double(x):
    ...     return x * 2
    >>> double(2)
    4
    >>> del enabled[:]  # False
    >>> double(2)
    2
    """
    return bypass_when(check, _op=operator.not_)


@functools.singledispatch
def _splat_inner(args, func):
    """Splat args to func."""
    return func(*args)


@_splat_inner.register
def _(args: collections.abc.Mapping, func):
    """Splat kargs to func as kwargs."""
    return func(**args)


def splat(func):
    """
    Wrap func to expect its parameters to be passed positionally in a tuple.

    Has a similar effect to that of ``itertools.starmap`` over
    simple ``map``.

    >>> pairs = [(-1, 1), (0, 2)]
    >>> more_itertools.consume(itertools.starmap(print, pairs))
    -1 1
    0 2
    >>> more_itertools.consume(map(splat(print), pairs))
    -1 1
    0 2

    The approach generalizes to other iterators that don't have a "star"
    equivalent, such as a "starfilter".

    >>> list(filter(splat(operator.add), pairs))
    [(0, 2)]

    Splat also accepts a mapping argument.

    >>> def is_nice(msg, code):
    ...     return "smile" in msg or code == 0
    >>> msgs = [
    ...     dict(msg='smile!', code=20),
    ...     dict(msg='error :(', code=1),
    ...     dict(msg='unknown', code=0),
    ... ]
    >>> for msg in filter(splat(is_nice), msgs):
    ...     print(msg)
    {'msg': 'smile!', 'code': 20}
    {'msg': 'unknown', 'code': 0}
    """
    return functools.wraps(func)(functools.partial(_splat_inner, func=func))

# === NexusCore/openenv\Lib\site-packages\pyreadline3\rlmain.py ===
# -*- coding: utf-8 -*-
# *****************************************************************************
#       Copyright (C) 2003-2006 Gary Bishop.
#       Copyright (C) 2006-2020 Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#       Copyright (C) 2020 Bassem Girgis. <brgirgis@gmail.com>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# *****************************************************************************


import os
import re
import sys
import time
from glob import glob

import pyreadline3
import pyreadline3.clipboard as clipboard
import pyreadline3.console as console
import pyreadline3.lineeditor.history as history
import pyreadline3.lineeditor.lineobj as lineobj
import pyreadline3.logger as logger
from pyreadline3.keysyms.common import make_KeyPress_from_keydescr
from pyreadline3.py3k_compat import is_ironpython
from pyreadline3.unicode_helper import ensure_str, ensure_unicode

from .error import GetSetError, ReadlineError
from .logger import log
from .modes import editingmodes
from .py3k_compat import execfile, is_callable

# an attempt to implement readline for Python in Python using ctypes


if is_ironpython:  # ironpython does not provide a prompt string to readline
    import System

    default_prompt = ">>> "
else:
    default_prompt = ""


class MockConsoleError(Exception):
    pass


class MockConsole(object):
    """object used during refactoring. Should raise errors when someone tries
    to use it.
    """

    def __setattr__(self, _name, _value):
        raise MockConsoleError("Should not try to get attributes from MockConsole")

    def cursor(self, size=50):
        pass


class BaseReadline(object):
    def __init__(self):
        self.allow_ctrl_c = False
        self.ctrl_c_tap_time_interval = 0.3

        self.debug = False
        self.bell_style = "none"
        self.mark = -1
        self.console = MockConsole()
        self.disable_readline = False
        # this code needs to follow l_buffer and history creation
        self.editingmodes = [mode(self) for mode in editingmodes]
        for mode in self.editingmodes:
            mode.init_editing_mode(None)
        self.mode = self.editingmodes[0]

        self.read_inputrc()
        log("\n".join(self.mode.rl_settings_to_string()))

        self.callback = None

    def parse_and_bind(self, string):
        """Parse and execute single line of a readline init file."""
        try:
            log('parse_and_bind("%s")' % string)
            if string.startswith("#"):
                return
            if string.startswith("set"):
                m = re.compile(r"set\s+([-a-zA-Z0-9]+)\s+(.+)\s*$").match(string)
                if m:
                    var_name = m.group(1)
                    val = m.group(2)
                    try:
                        setattr(self.mode, var_name.replace("-", "_"), val)
                    except AttributeError:
                        log('unknown var="%s" val="%s"' % (var_name, val))
                else:
                    log('bad set "%s"' % string)
                return
            m = re.compile(r"\s*(\S+)\s*:\s*([-a-zA-Z]+)\s*$").match(string)
            if m:
                key = m.group(1)
                func_name = m.group(2)
                py_name = func_name.replace("-", "_")
                try:
                    func = getattr(self.mode, py_name)
                except AttributeError:
                    log('unknown func key="%s" func="%s"' % (key, func_name))
                    if self.debug:
                        print(
                            "pyreadline3 parse_and_bind error, unknown "
                            'function to bind: "%s"' % func_name
                        )
                    return
                self.mode._bind_key(key, func)
        except BaseException:
            log("error")
            raise

    def _set_prompt(self, prompt):
        self.mode.prompt = prompt

    def _get_prompt(self):
        return self.mode.prompt

    prompt = property(_get_prompt, _set_prompt)

    def get_line_buffer(self):
        """Return the current contents of the line buffer."""
        return self.mode.l_buffer.get_line_text()

    def insert_text(self, string):
        """Insert text into the command line."""
        self.mode.insert_text(string)

    def read_init_file(self, filename=None):
        """Parse a readline initialization file. The default filename is the last filename used."""
        log('read_init_file("%s")' % filename)

    # History file book keeping methods (non-bindable)

    def add_history(self, line):
        """Append a line to the history buffer, as if it was the last line typed."""
        self.mode._history.add_history(line)

    def get_current_history_length(self):
        """Return the number of lines currently in the history.
        (This is different from get_history_length(), which returns
        the maximum number of lines that will be written to a history file.)"""
        return self.mode._history.get_current_history_length()

    def get_history_length(self):
        """Return the desired length of the history file.

        Negative values imply unlimited history file size."""
        return self.mode._history.get_history_length()

    def set_history_length(self, length):
        """Set the number of lines to save in the history file.

        write_history_file() uses this value to truncate the history file
        when saving. Negative values imply unlimited history file size.
        """
        self.mode._history.set_history_length(length)

    def get_history_item(self, index):
        """Return the current contents of history item at index."""
        return self.mode._history.get_history_item(index)

    def clear_history(self):
        """Clear readline history"""
        self.mode._history.clear_history()

    def read_history_file(self, filename=None):
        """Load a readline history file. The default filename is ~/.history."""
        if filename is None:
            filename = self.mode._history.history_filename
        log("read_history_file from %s" % ensure_unicode(filename))
        self.mode._history.read_history_file(filename)

    def write_history_file(self, filename=None):
        """Save a readline history file. The default filename is ~/.history."""
        self.mode._history.write_history_file(filename)

    # Completer functions

    def set_completer(self, function=None):
        """Set or remove the completer function.

        If function is specified, it will be used as the new completer
        function; if omitted or None, any completer function already
        installed is removed. The completer function is called as
        function(text, state), for state in 0, 1, 2, ..., until it returns a
        non-string value. It should return the next possible completion
        starting with text.
        """
        log("set_completer")
        self.mode.completer = function

    def get_completer(self):
        """Get the completer function."""
        log("get_completer")
        return self.mode.completer

    def get_begidx(self):
        """Get the beginning index of the readline tab-completion scope."""
        return self.mode.begidx

    def get_endidx(self):
        """Get the ending index of the readline tab-completion scope."""
        return self.mode.endidx

    def set_completer_delims(self, string):
        """Set the readline word delimiters for tab-completion."""
        self.mode.completer_delims = string

    def get_completer_delims(self):
        """Get the readline word delimiters for tab-completion."""
        return self.mode.completer_delims

    def set_startup_hook(self, function=None):
        """Set or remove the startup_hook function.

        If function is specified, it will be used as the new startup_hook
        function; if omitted or None, any hook function already installed is
        removed. The startup_hook function is called with no arguments just
        before readline prints the first prompt.

        """
        self.mode.startup_hook = function

    def set_pre_input_hook(self, function=None):
        """Set or remove the pre_input_hook function.

        If function is specified, it will be used as the new pre_input_hook
        function; if omitted or None, any hook function already installed is
        removed. The pre_input_hook function is called with no arguments
        after the first prompt has been printed and just before readline
        starts reading input characters.

        """
        self.mode.pre_input_hook = function

    # Functions that are not relevant for all Readlines but should at least
    # have a NOP

    def _bell(self):
        pass

    #
    # Standard call, not available for all implementations
    #

    def readline(self, prompt=""):
        raise NotImplementedError

    #
    # Callback interface
    #
    def process_keyevent(self, keyinfo):
        return self.mode.process_keyevent(keyinfo)

    def readline_setup(self, prompt=""):
        return self.mode.readline_setup(prompt)

    def keyboard_poll(self):
        return self.mode._readline_from_keyboard_poll()

    def callback_handler_install(self, prompt, callback):
        """bool readline_callback_handler_install ( string prompt, callback callback)
        Initializes the readline callback interface and terminal, prints the prompt and returns immediately
        """
        self.callback = callback
        self.readline_setup(prompt)

    def callback_handler_remove(self):
        """Removes a previously installed callback handler and restores terminal settings"""
        self.callback = None

    def callback_read_char(self):
        """Reads a character and informs the readline callback interface when a line is received"""
        if self.keyboard_poll():
            line = self.get_line_buffer() + "\n"
            # however there is another newline added by
            # self.mode.readline_setup(prompt) which is called by callback_handler_install
            # this differs from GNU readline
            self.add_history(self.mode.l_buffer)
            # TADA:
            self.callback(line)

    def read_inputrc(
        self,  # in 2.4 we cannot call expanduser with unicode string
        inputrcpath=os.path.expanduser(ensure_str("~/pyreadlineconfig.ini")),
    ):
        modes = dict([(x.mode, x) for x in self.editingmodes])
        mode = self.editingmodes[0].mode

        def setmode(name):
            self.mode = modes[name]

        def bind_key(key, name):
            import types

            if is_callable(name):
                modes[mode]._bind_key(key, types.MethodType(name, modes[mode]))
            elif hasattr(modes[mode], name):
                modes[mode]._bind_key(key, getattr(modes[mode], name))
            else:
                print("Trying to bind unknown command '%s' to key '%s'" % (name, key))

        def un_bind_key(key):
            keyinfo = make_KeyPress_from_keydescr(key).tuple()
            if keyinfo in modes[mode].key_dispatch:
                del modes[mode].key_dispatch[keyinfo]

        def bind_exit_key(key):
            modes[mode]._bind_exit_key(key)

        def un_bind_exit_key(key):
            keyinfo = make_KeyPress_from_keydescr(key).tuple()
            if keyinfo in modes[mode].exit_dispatch:
                del modes[mode].exit_dispatch[keyinfo]

        def setkill_ring_to_clipboard(killring):
            import pyreadline3.lineeditor.lineobj

            pyreadline3.lineeditor.lineobj.kill_ring_to_clipboard = killring

        def sethistoryfilename(filename):
            self.mode._history.history_filename = os.path.expanduser(
                ensure_str(filename)
            )

        def setbellstyle(mode):
            self.bell_style = mode

        def disable_readline(mode):
            self.disable_readline = mode

        def sethistorylength(length):
            self.mode._history.history_length = int(length)

        def allow_ctrl_c(mode):
            log("allow_ctrl_c:%s:%s" % (self.allow_ctrl_c, mode))
            self.allow_ctrl_c = mode

        def setbellstyle(mode):
            self.bell_style = mode

        def show_all_if_ambiguous(mode):
            self.mode.show_all_if_ambiguous = mode

        def ctrl_c_tap_time_interval(mode):
            self.ctrl_c_tap_time_interval = mode

        def mark_directories(mode):
            self.mode.mark_directories = mode

        def completer_delims(delims):
            self.mode.completer_delims = delims

        def complete_filesystem(delims):
            self.mode.complete_filesystem = delims.lower()

        def enable_ipython_paste_for_paths(boolean):
            self.mode.enable_ipython_paste_for_paths = boolean

        def debug_output(
            on, filename="pyreadline_debug_log.txt"
        ):  # Not implemented yet
            if on in ["on", "on_nologfile"]:
                self.debug = True

            if on == "on":
                logger.start_file_log(filename)
                logger.start_socket_log()
                logger.log("STARTING LOG")
            elif on == "on_nologfile":
                logger.start_socket_log()
                logger.log("STARTING LOG")
            else:
                logger.log("STOPING LOG")
                logger.stop_file_log()
                logger.stop_socket_log()

        _color_trtable = {
            "black": 0,
            "darkred": 4,
            "darkgreen": 2,
            "darkyellow": 6,
            "darkblue": 1,
            "darkmagenta": 5,
            "darkcyan": 3,
            "gray": 7,
            "red": 4 + 8,
            "green": 2 + 8,
            "yellow": 6 + 8,
            "blue": 1 + 8,
            "magenta": 5 + 8,
            "cyan": 3 + 8,
            "white": 7 + 8,
        }

        def set_prompt_color(color):
            self.prompt_color = self._color_trtable.get(color.lower(), 7)

        def set_input_color(color):
            self.command_color = self._color_trtable.get(color.lower(), 7)

        loc = {
            "version": pyreadline3.__version__,
            "mode": mode,
            "modes": modes,
            "set_mode": setmode,
            "bind_key": bind_key,
            "disable_readline": disable_readline,
            "bind_exit_key": bind_exit_key,
            "un_bind_key": un_bind_key,
            "un_bind_exit_key": un_bind_exit_key,
            "bell_style": setbellstyle,
            "mark_directories": mark_directories,
            "show_all_if_ambiguous": show_all_if_ambiguous,
            "completer_delims": completer_delims,
            "complete_filesystem": complete_filesystem,
            "debug_output": debug_output,
            "history_filename": sethistoryfilename,
            "history_length": sethistorylength,
            "set_prompt_color": set_prompt_color,
            "set_input_color": set_input_color,
            "allow_ctrl_c": allow_ctrl_c,
            "ctrl_c_tap_time_interval": ctrl_c_tap_time_interval,
            "kill_ring_to_clipboard": setkill_ring_to_clipboard,
            "enable_ipython_paste_for_paths": enable_ipython_paste_for_paths,
        }
        if os.path.isfile(inputrcpath):
            try:
                execfile(inputrcpath, loc, loc)
            except Exception as x:
                raise
                import traceback

                print("Error reading .pyinputrc", file=sys.stderr)
                filepath, lineno = traceback.extract_tb(sys.exc_info()[2])[1][:2]
                print("Line: %s in file %s" % (lineno, filepath), file=sys.stderr)
                print(x, file=sys.stderr)
                raise ReadlineError("Error reading .pyinputrc")

    def redisplay(self):
        pass


class Readline(BaseReadline):
    """Baseclass for readline based on a console"""

    def __init__(self):
        super().__init__()

        self.console = console.Console()
        self.selection_color = self.console.saveattr << 4
        self.command_color = None
        self.prompt_color = None
        self.size = self.console.size()

        # variables you can control with parse_and_bind

    #  To export as readline interface

    # Internal functions

    def _bell(self):
        """ring the bell if requested."""
        if self.bell_style == "none":
            pass
        elif self.bell_style == "visible":
            raise NotImplementedError("Bellstyle visible is not implemented yet.")
        elif self.bell_style == "audible":
            self.console.bell()
        else:
            raise ReadlineError("Bellstyle %s unknown." % self.bell_style)

    def _clear_after(self):
        c = self.console
        x, y = c.pos()
        w, h = c.size()
        c.rectangle((x, y, w + 1, y + 1))
        c.rectangle((0, y + 1, w, min(y + 3, h)))

    def _set_cursor(self):
        c = self.console
        xc, yc = self.prompt_end_pos
        w, h = c.size()
        xc += self.mode.l_buffer.visible_line_width()
        while xc >= w:
            xc -= w
            yc += 1
        c.pos(xc, yc)

    def _print_prompt(self):
        c = self.console
        x, y = c.pos()

        n = c.write_scrolling(self.prompt, self.prompt_color)
        self.prompt_begin_pos = (x, y - n)
        self.prompt_end_pos = c.pos()
        self.size = c.size()

    def _update_prompt_pos(self, n):
        if n != 0:
            bx, by = self.prompt_begin_pos
            ex, ey = self.prompt_end_pos
            self.prompt_begin_pos = (bx, by - n)
            self.prompt_end_pos = (ex, ey - n)

    def _update_line(self):
        c = self.console
        l_buffer = self.mode.l_buffer
        c.cursor(0)  # Hide cursor avoiding flicking
        c.pos(*self.prompt_begin_pos)
        self._print_prompt()
        ltext = l_buffer.quoted_text()
        if l_buffer.enable_selection and (l_buffer.selection_mark >= 0):
            start = len(l_buffer[: l_buffer.selection_mark].quoted_text())
            stop = len(l_buffer[: l_buffer.point].quoted_text())
            if start > stop:
                stop, start = start, stop
            n = c.write_scrolling(ltext[:start], self.command_color)
            n = c.write_scrolling(ltext[start:stop], self.selection_color)
            n = c.write_scrolling(ltext[stop:], self.command_color)
        else:
            n = c.write_scrolling(ltext, self.command_color)

        x, y = c.pos()  # Preserve one line for Asian IME(Input Method Editor) statusbar
        w, h = c.size()
        if (y >= h - 1) or (n > 0):
            c.scroll_window(-1)
            c.scroll((0, 0, w, h), 0, -1)
            n += 1

        self._update_prompt_pos(n)
        if hasattr(
            c, "clear_to_end_of_window"
        ):  # Work around function for ironpython due
            c.clear_to_end_of_window()  # to System.Console's lack of FillFunction
        else:
            self._clear_after()

        # Show cursor, set size vi mode changes size in insert/overwrite mode
        c.cursor(1, size=self.mode.cursor_size)
        self._set_cursor()

    def callback_read_char(self):
        # Override base to get automatic newline
        """Reads a character and informs the readline callback interface when a line is received"""
        if self.keyboard_poll():
            line = self.get_line_buffer() + "\n"
            self.console.write("\r\n")
            # however there is another newline added by
            # self.mode.readline_setup(prompt) which is called by callback_handler_install
            # this differs from GNU readline
            self.add_history(self.mode.l_buffer)
            # TADA:
            self.callback(line)

    def event_available(self):
        return self.console.peek() or (len(self.paste_line_buffer) > 0)

    def _readline_from_keyboard(self):
        while True:
            if self._readline_from_keyboard_poll():
                break

    def _readline_from_keyboard_poll(self):
        pastebuffer = self.mode.paste_line_buffer
        if len(pastebuffer) > 0:
            # paste first line in multiline paste buffer
            self.l_buffer = lineobj.ReadLineTextBuffer(pastebuffer[0])
            self._update_line()
            self.mode.paste_line_buffer = pastebuffer[1:]
            return True

        c = self.console

        def nop(e):
            pass

        try:
            event = c.getkeypress()
        except KeyboardInterrupt:
            event = self.handle_ctrl_c()
        try:
            result = self.mode.process_keyevent(event.keyinfo)
        except EOFError:
            logger.stop_logging()
            raise
        self._update_line()
        return result

    def readline_setup(self, prompt=""):
        BaseReadline.readline_setup(self, prompt)
        self._print_prompt()
        self._update_line()

    def readline(self, prompt=""):
        self.readline_setup(prompt)
        self.ctrl_c_timeout = time.time()
        self._readline_from_keyboard()
        self.console.write("\r\n")
        log("returning(%s)" % self.get_line_buffer())
        return self.get_line_buffer() + "\n"

    def handle_ctrl_c(self):
        from pyreadline3.console.event import Event
        from pyreadline3.keysyms.common import KeyPress

        log("KBDIRQ")
        event = Event(0, 0)
        event.char = "c"
        event.keyinfo = KeyPress(
            "c", shift=False, control=True, meta=False, keyname=None
        )
        if self.allow_ctrl_c:
            now = time.time()
            if (now - self.ctrl_c_timeout) < self.ctrl_c_tap_time_interval:
                log("Raise KeyboardInterrupt")
                raise KeyboardInterrupt
            else:
                self.ctrl_c_timeout = now
        else:
            raise KeyboardInterrupt
        return event

    def redisplay(self):
        BaseReadline.redisplay(self)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\platformdirs\__init__.py ===
"""
Utilities for determining application-specific dirs.

See <https://github.com/platformdirs/platformdirs> for details and usage.

"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from .api import PlatformDirsABC
from .version import __version__
from .version import __version_tuple__ as __version_info__

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal

if sys.platform == "win32":
    from pip._vendor.platformdirs.windows import Windows as _Result
elif sys.platform == "darwin":
    from pip._vendor.platformdirs.macos import MacOS as _Result
else:
    from pip._vendor.platformdirs.unix import Unix as _Result


def _set_platform_dir_class() -> type[PlatformDirsABC]:
    if os.getenv("ANDROID_DATA") == "/data" and os.getenv("ANDROID_ROOT") == "/system":
        if os.getenv("SHELL") or os.getenv("PREFIX"):
            return _Result

        from pip._vendor.platformdirs.android import _android_folder  # noqa: PLC0415

        if _android_folder() is not None:
            from pip._vendor.platformdirs.android import Android  # noqa: PLC0415

            return Android  # return to avoid redefinition of a result

    return _Result


if TYPE_CHECKING:
    # Work around mypy issue: https://github.com/python/mypy/issues/10962
    PlatformDirs = _Result
else:
    PlatformDirs = _set_platform_dir_class()  #: Currently active platform
AppDirs = PlatformDirs  #: Backwards compatibility with appdirs


def user_data_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_data_dir


def site_data_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `roaming <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data directory shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_data_dir


def user_config_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_config_dir


def site_config_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `roaming <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config directory shared by the users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_config_dir


def user_cache_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_cache_dir


def site_cache_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_cache_dir


def user_state_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: state directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_state_dir


def user_log_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: log directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_log_dir


def user_documents_dir() -> str:
    """:returns: documents directory tied to the user"""
    return PlatformDirs().user_documents_dir


def user_downloads_dir() -> str:
    """:returns: downloads directory tied to the user"""
    return PlatformDirs().user_downloads_dir


def user_pictures_dir() -> str:
    """:returns: pictures directory tied to the user"""
    return PlatformDirs().user_pictures_dir


def user_videos_dir() -> str:
    """:returns: videos directory tied to the user"""
    return PlatformDirs().user_videos_dir


def user_music_dir() -> str:
    """:returns: music directory tied to the user"""
    return PlatformDirs().user_music_dir


def user_desktop_dir() -> str:
    """:returns: desktop directory tied to the user"""
    return PlatformDirs().user_desktop_dir


def user_runtime_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_runtime_dir


def site_runtime_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime directory shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_runtime_dir


def user_data_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_data_path


def site_data_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `multipath <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data path shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_data_path


def user_config_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_config_path


def site_config_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `roaming <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config path shared by the users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_config_path


def site_cache_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_cache_path


def user_cache_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_cache_path


def user_state_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: state path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_state_path


def user_log_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: log path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_log_path


def user_documents_path() -> Path:
    """:returns: documents a path tied to the user"""
    return PlatformDirs().user_documents_path


def user_downloads_path() -> Path:
    """:returns: downloads path tied to the user"""
    return PlatformDirs().user_downloads_path


def user_pictures_path() -> Path:
    """:returns: pictures path tied to the user"""
    return PlatformDirs().user_pictures_path


def user_videos_path() -> Path:
    """:returns: videos path tied to the user"""
    return PlatformDirs().user_videos_path


def user_music_path() -> Path:
    """:returns: music path tied to the user"""
    return PlatformDirs().user_music_path


def user_desktop_path() -> Path:
    """:returns: desktop path tied to the user"""
    return PlatformDirs().user_desktop_path


def user_runtime_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_runtime_path


def site_runtime_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime path shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_runtime_path


__all__ = [
    "AppDirs",
    "PlatformDirs",
    "PlatformDirsABC",
    "__version__",
    "__version_info__",
    "site_cache_dir",
    "site_cache_path",
    "site_config_dir",
    "site_config_path",
    "site_data_dir",
    "site_data_path",
    "site_runtime_dir",
    "site_runtime_path",
    "user_cache_dir",
    "user_cache_path",
    "user_config_dir",
    "user_config_path",
    "user_data_dir",
    "user_data_path",
    "user_desktop_dir",
    "user_desktop_path",
    "user_documents_dir",
    "user_documents_path",
    "user_downloads_dir",
    "user_downloads_path",
    "user_log_dir",
    "user_log_path",
    "user_music_dir",
    "user_music_path",
    "user_pictures_dir",
    "user_pictures_path",
    "user_runtime_dir",
    "user_runtime_path",
    "user_state_dir",
    "user_state_path",
    "user_videos_dir",
    "user_videos_path",
]

# === NexusCore/openenv\Lib\site-packages\aiohttp\web_ws.py ===
import asyncio
import base64
import binascii
import hashlib
import json
import sys
from typing import Any, Final, Iterable, Optional, Tuple, Union, cast

import attr
from multidict import CIMultiDict

from . import hdrs
from ._websocket.reader import WebSocketDataQueue
from ._websocket.writer import DEFAULT_LIMIT
from .abc import AbstractStreamWriter
from .client_exceptions import WSMessageTypeError
from .helpers import calculate_timeout_when, set_exception, set_result
from .http import (
    WS_CLOSED_MESSAGE,
    WS_CLOSING_MESSAGE,
    WS_KEY,
    WebSocketError,
    WebSocketReader,
    WebSocketWriter,
    WSCloseCode,
    WSMessage,
    WSMsgType as WSMsgType,
    ws_ext_gen,
    ws_ext_parse,
)
from .http_websocket import _INTERNAL_RECEIVE_TYPES
from .log import ws_logger
from .streams import EofStream
from .typedefs import JSONDecoder, JSONEncoder
from .web_exceptions import HTTPBadRequest, HTTPException
from .web_request import BaseRequest
from .web_response import StreamResponse

if sys.version_info >= (3, 11):
    import asyncio as async_timeout
else:
    import async_timeout

__all__ = (
    "WebSocketResponse",
    "WebSocketReady",
    "WSMsgType",
)

THRESHOLD_CONNLOST_ACCESS: Final[int] = 5


@attr.s(auto_attribs=True, frozen=True, slots=True)
class WebSocketReady:
    ok: bool
    protocol: Optional[str]

    def __bool__(self) -> bool:
        return self.ok


class WebSocketResponse(StreamResponse):

    _length_check: bool = False
    _ws_protocol: Optional[str] = None
    _writer: Optional[WebSocketWriter] = None
    _reader: Optional[WebSocketDataQueue] = None
    _closed: bool = False
    _closing: bool = False
    _conn_lost: int = 0
    _close_code: Optional[int] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _waiting: bool = False
    _close_wait: Optional[asyncio.Future[None]] = None
    _exception: Optional[BaseException] = None
    _heartbeat_when: float = 0.0
    _heartbeat_cb: Optional[asyncio.TimerHandle] = None
    _pong_response_cb: Optional[asyncio.TimerHandle] = None
    _ping_task: Optional[asyncio.Task[None]] = None

    def __init__(
        self,
        *,
        timeout: float = 10.0,
        receive_timeout: Optional[float] = None,
        autoclose: bool = True,
        autoping: bool = True,
        heartbeat: Optional[float] = None,
        protocols: Iterable[str] = (),
        compress: bool = True,
        max_msg_size: int = 4 * 1024 * 1024,
        writer_limit: int = DEFAULT_LIMIT,
    ) -> None:
        super().__init__(status=101)
        self._protocols = protocols
        self._timeout = timeout
        self._receive_timeout = receive_timeout
        self._autoclose = autoclose
        self._autoping = autoping
        self._heartbeat = heartbeat
        if heartbeat is not None:
            self._pong_heartbeat = heartbeat / 2.0
        self._compress: Union[bool, int] = compress
        self._max_msg_size = max_msg_size
        self._writer_limit = writer_limit

    def _cancel_heartbeat(self) -> None:
        self._cancel_pong_response_cb()
        if self._heartbeat_cb is not None:
            self._heartbeat_cb.cancel()
            self._heartbeat_cb = None
        if self._ping_task is not None:
            self._ping_task.cancel()
            self._ping_task = None

    def _cancel_pong_response_cb(self) -> None:
        if self._pong_response_cb is not None:
            self._pong_response_cb.cancel()
            self._pong_response_cb = None

    def _reset_heartbeat(self) -> None:
        if self._heartbeat is None:
            return
        self._cancel_pong_response_cb()
        req = self._req
        timeout_ceil_threshold = (
            req._protocol._timeout_ceil_threshold if req is not None else 5
        )
        loop = self._loop
        assert loop is not None
        now = loop.time()
        when = calculate_timeout_when(now, self._heartbeat, timeout_ceil_threshold)
        self._heartbeat_when = when
        if self._heartbeat_cb is None:
            # We do not cancel the previous heartbeat_cb here because
            # it generates a significant amount of TimerHandle churn
            # which causes asyncio to rebuild the heap frequently.
            # Instead _send_heartbeat() will reschedule the next
            # heartbeat if it fires too early.
            self._heartbeat_cb = loop.call_at(when, self._send_heartbeat)

    def _send_heartbeat(self) -> None:
        self._heartbeat_cb = None
        loop = self._loop
        assert loop is not None and self._writer is not None
        now = loop.time()
        if now < self._heartbeat_when:
            # Heartbeat fired too early, reschedule
            self._heartbeat_cb = loop.call_at(
                self._heartbeat_when, self._send_heartbeat
            )
            return

        req = self._req
        timeout_ceil_threshold = (
            req._protocol._timeout_ceil_threshold if req is not None else 5
        )
        when = calculate_timeout_when(now, self._pong_heartbeat, timeout_ceil_threshold)
        self._cancel_pong_response_cb()
        self._pong_response_cb = loop.call_at(when, self._pong_not_received)

        coro = self._writer.send_frame(b"", WSMsgType.PING)
        if sys.version_info >= (3, 12):
            # Optimization for Python 3.12, try to send the ping
            # immediately to avoid having to schedule
            # the task on the event loop.
            ping_task = asyncio.Task(coro, loop=loop, eager_start=True)
        else:
            ping_task = loop.create_task(coro)

        if not ping_task.done():
            self._ping_task = ping_task
            ping_task.add_done_callback(self._ping_task_done)
        else:
            self._ping_task_done(ping_task)

    def _ping_task_done(self, task: "asyncio.Task[None]") -> None:
        """Callback for when the ping task completes."""
        if not task.cancelled() and (exc := task.exception()):
            self._handle_ping_pong_exception(exc)
        self._ping_task = None

    def _pong_not_received(self) -> None:
        if self._req is not None and self._req.transport is not None:
            self._handle_ping_pong_exception(
                asyncio.TimeoutError(
                    f"No PONG received after {self._pong_heartbeat} seconds"
                )
            )

    def _handle_ping_pong_exception(self, exc: BaseException) -> None:
        """Handle exceptions raised during ping/pong processing."""
        if self._closed:
            return
        self._set_closed()
        self._set_code_close_transport(WSCloseCode.ABNORMAL_CLOSURE)
        self._exception = exc
        if self._waiting and not self._closing and self._reader is not None:
            self._reader.feed_data(WSMessage(WSMsgType.ERROR, exc, None), 0)

    def _set_closed(self) -> None:
        """Set the connection to closed.

        Cancel any heartbeat timers and set the closed flag.
        """
        self._closed = True
        self._cancel_heartbeat()

    async def prepare(self, request: BaseRequest) -> AbstractStreamWriter:
        # make pre-check to don't hide it by do_handshake() exceptions
        if self._payload_writer is not None:
            return self._payload_writer

        protocol, writer = self._pre_start(request)
        payload_writer = await super().prepare(request)
        assert payload_writer is not None
        self._post_start(request, protocol, writer)
        await payload_writer.drain()
        return payload_writer

    def _handshake(
        self, request: BaseRequest
    ) -> Tuple["CIMultiDict[str]", Optional[str], int, bool]:
        headers = request.headers
        if "websocket" != headers.get(hdrs.UPGRADE, "").lower().strip():
            raise HTTPBadRequest(
                text=(
                    "No WebSocket UPGRADE hdr: {}\n Can "
                    '"Upgrade" only to "WebSocket".'
                ).format(headers.get(hdrs.UPGRADE))
            )

        if "upgrade" not in headers.get(hdrs.CONNECTION, "").lower():
            raise HTTPBadRequest(
                text="No CONNECTION upgrade hdr: {}".format(
                    headers.get(hdrs.CONNECTION)
                )
            )

        # find common sub-protocol between client and server
        protocol: Optional[str] = None
        if hdrs.SEC_WEBSOCKET_PROTOCOL in headers:
            req_protocols = [
                str(proto.strip())
                for proto in headers[hdrs.SEC_WEBSOCKET_PROTOCOL].split(",")
            ]

            for proto in req_protocols:
                if proto in self._protocols:
                    protocol = proto
                    break
            else:
                # No overlap found: Return no protocol as per spec
                ws_logger.warning(
                    "%s: Client protocols %r don’t overlap server-known ones %r",
                    request.remote,
                    req_protocols,
                    self._protocols,
                )

        # check supported version
        version = headers.get(hdrs.SEC_WEBSOCKET_VERSION, "")
        if version not in ("13", "8", "7"):
            raise HTTPBadRequest(text=f"Unsupported version: {version}")

        # check client handshake for validity
        key = headers.get(hdrs.SEC_WEBSOCKET_KEY)
        try:
            if not key or len(base64.b64decode(key)) != 16:
                raise HTTPBadRequest(text=f"Handshake error: {key!r}")
        except binascii.Error:
            raise HTTPBadRequest(text=f"Handshake error: {key!r}") from None

        accept_val = base64.b64encode(
            hashlib.sha1(key.encode() + WS_KEY).digest()
        ).decode()
        response_headers = CIMultiDict(
            {
                hdrs.UPGRADE: "websocket",
                hdrs.CONNECTION: "upgrade",
                hdrs.SEC_WEBSOCKET_ACCEPT: accept_val,
            }
        )

        notakeover = False
        compress = 0
        if self._compress:
            extensions = headers.get(hdrs.SEC_WEBSOCKET_EXTENSIONS)
            # Server side always get return with no exception.
            # If something happened, just drop compress extension
            compress, notakeover = ws_ext_parse(extensions, isserver=True)
            if compress:
                enabledext = ws_ext_gen(
                    compress=compress, isserver=True, server_notakeover=notakeover
                )
                response_headers[hdrs.SEC_WEBSOCKET_EXTENSIONS] = enabledext

        if protocol:
            response_headers[hdrs.SEC_WEBSOCKET_PROTOCOL] = protocol
        return (
            response_headers,
            protocol,
            compress,
            notakeover,
        )

    def _pre_start(self, request: BaseRequest) -> Tuple[Optional[str], WebSocketWriter]:
        self._loop = request._loop

        headers, protocol, compress, notakeover = self._handshake(request)

        self.set_status(101)
        self.headers.update(headers)
        self.force_close()
        self._compress = compress
        transport = request._protocol.transport
        assert transport is not None
        writer = WebSocketWriter(
            request._protocol,
            transport,
            compress=compress,
            notakeover=notakeover,
            limit=self._writer_limit,
        )

        return protocol, writer

    def _post_start(
        self, request: BaseRequest, protocol: Optional[str], writer: WebSocketWriter
    ) -> None:
        self._ws_protocol = protocol
        self._writer = writer

        self._reset_heartbeat()

        loop = self._loop
        assert loop is not None
        self._reader = WebSocketDataQueue(request._protocol, 2**16, loop=loop)
        request.protocol.set_parser(
            WebSocketReader(
                self._reader, self._max_msg_size, compress=bool(self._compress)
            )
        )
        # disable HTTP keepalive for WebSocket
        request.protocol.keep_alive(False)

    def can_prepare(self, request: BaseRequest) -> WebSocketReady:
        if self._writer is not None:
            raise RuntimeError("Already started")
        try:
            _, protocol, _, _ = self._handshake(request)
        except HTTPException:
            return WebSocketReady(False, None)
        else:
            return WebSocketReady(True, protocol)

    @property
    def prepared(self) -> bool:
        return self._writer is not None

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def close_code(self) -> Optional[int]:
        return self._close_code

    @property
    def ws_protocol(self) -> Optional[str]:
        return self._ws_protocol

    @property
    def compress(self) -> Union[int, bool]:
        return self._compress

    def get_extra_info(self, name: str, default: Any = None) -> Any:
        """Get optional transport information.

        If no value associated with ``name`` is found, ``default`` is returned.
        """
        writer = self._writer
        if writer is None:
            return default
        transport = writer.transport
        if transport is None:
            return default
        return transport.get_extra_info(name, default)

    def exception(self) -> Optional[BaseException]:
        return self._exception

    async def ping(self, message: bytes = b"") -> None:
        if self._writer is None:
            raise RuntimeError("Call .prepare() first")
        await self._writer.send_frame(message, WSMsgType.PING)

    async def pong(self, message: bytes = b"") -> None:
        # unsolicited pong
        if self._writer is None:
            raise RuntimeError("Call .prepare() first")
        await self._writer.send_frame(message, WSMsgType.PONG)

    async def send_frame(
        self, message: bytes, opcode: WSMsgType, compress: Optional[int] = None
    ) -> None:
        """Send a frame over the websocket."""
        if self._writer is None:
            raise RuntimeError("Call .prepare() first")
        await self._writer.send_frame(message, opcode, compress)

    async def send_str(self, data: str, compress: Optional[int] = None) -> None:
        if self._writer is None:
            raise RuntimeError("Call .prepare() first")
        if not isinstance(data, str):
            raise TypeError("data argument must be str (%r)" % type(data))
        await self._writer.send_frame(
            data.encode("utf-8"), WSMsgType.TEXT, compress=compress
        )

    async def send_bytes(self, data: bytes, compress: Optional[int] = None) -> None:
        if self._writer is None:
            raise RuntimeError("Call .prepare() first")
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data argument must be byte-ish (%r)" % type(data))
        await self._writer.send_frame(data, WSMsgType.BINARY, compress=compress)

    async def send_json(
        self,
        data: Any,
        compress: Optional[int] = None,
        *,
        dumps: JSONEncoder = json.dumps,
    ) -> None:
        await self.send_str(dumps(data), compress=compress)

    async def write_eof(self) -> None:  # type: ignore[override]
        if self._eof_sent:
            return
        if self._payload_writer is None:
            raise RuntimeError("Response has not been started")

        await self.close()
        self._eof_sent = True

    async def close(
        self, *, code: int = WSCloseCode.OK, message: bytes = b"", drain: bool = True
    ) -> bool:
        """Close websocket connection."""
        if self._writer is None:
            raise RuntimeError("Call .prepare() first")

        if self._closed:
            return False
        self._set_closed()

        try:
            await self._writer.close(code, message)
            writer = self._payload_writer
            assert writer is not None
            if drain:
                await writer.drain()
        except (asyncio.CancelledError, asyncio.TimeoutError):
            self._set_code_close_transport(WSCloseCode.ABNORMAL_CLOSURE)
            raise
        except Exception as exc:
            self._exception = exc
            self._set_code_close_transport(WSCloseCode.ABNORMAL_CLOSURE)
            return True

        reader = self._reader
        assert reader is not None
        # we need to break `receive()` cycle before we can call
        # `reader.read()` as `close()` may be called from different task
        if self._waiting:
            assert self._loop is not None
            assert self._close_wait is None
            self._close_wait = self._loop.create_future()
            reader.feed_data(WS_CLOSING_MESSAGE, 0)
            await self._close_wait

        if self._closing:
            self._close_transport()
            return True

        try:
            async with async_timeout.timeout(self._timeout):
                while True:
                    msg = await reader.read()
                    if msg.type is WSMsgType.CLOSE:
                        self._set_code_close_transport(msg.data)
                        return True
        except asyncio.CancelledError:
            self._set_code_close_transport(WSCloseCode.ABNORMAL_CLOSURE)
            raise
        except Exception as exc:
            self._exception = exc
            self._set_code_close_transport(WSCloseCode.ABNORMAL_CLOSURE)
            return True

    def _set_closing(self, code: WSCloseCode) -> None:
        """Set the close code and mark the connection as closing."""
        self._closing = True
        self._close_code = code
        self._cancel_heartbeat()

    def _set_code_close_transport(self, code: WSCloseCode) -> None:
        """Set the close code and close the transport."""
        self._close_code = code
        self._close_transport()

    def _close_transport(self) -> None:
        """Close the transport."""
        if self._req is not None and self._req.transport is not None:
            self._req.transport.close()

    async def receive(self, timeout: Optional[float] = None) -> WSMessage:
        if self._reader is None:
            raise RuntimeError("Call .prepare() first")

        receive_timeout = timeout or self._receive_timeout
        while True:
            if self._waiting:
                raise RuntimeError("Concurrent call to receive() is not allowed")

            if self._closed:
                self._conn_lost += 1
                if self._conn_lost >= THRESHOLD_CONNLOST_ACCESS:
                    raise RuntimeError("WebSocket connection is closed.")
                return WS_CLOSED_MESSAGE
            elif self._closing:
                return WS_CLOSING_MESSAGE

            try:
                self._waiting = True
                try:
                    if receive_timeout:
                        # Entering the context manager and creating
                        # Timeout() object can take almost 50% of the
                        # run time in this loop so we avoid it if
                        # there is no read timeout.
                        async with async_timeout.timeout(receive_timeout):
                            msg = await self._reader.read()
                    else:
                        msg = await self._reader.read()
                    self._reset_heartbeat()
                finally:
                    self._waiting = False
                    if self._close_wait:
                        set_result(self._close_wait, None)
            except asyncio.TimeoutError:
                raise
            except EofStream:
                self._close_code = WSCloseCode.OK
                await self.close()
                return WSMessage(WSMsgType.CLOSED, None, None)
            except WebSocketError as exc:
                self._close_code = exc.code
                await self.close(code=exc.code)
                return WSMessage(WSMsgType.ERROR, exc, None)
            except Exception as exc:
                self._exception = exc
                self._set_closing(WSCloseCode.ABNORMAL_CLOSURE)
                await self.close()
                return WSMessage(WSMsgType.ERROR, exc, None)

            if msg.type not in _INTERNAL_RECEIVE_TYPES:
                # If its not a close/closing/ping/pong message
                # we can return it immediately
                return msg

            if msg.type is WSMsgType.CLOSE:
                self._set_closing(msg.data)
                # Could be closed while awaiting reader.
                if not self._closed and self._autoclose:
                    # The client is likely going to close the
                    # connection out from under us so we do not
                    # want to drain any pending writes as it will
                    # likely result writing to a broken pipe.
                    await self.close(drain=False)
            elif msg.type is WSMsgType.CLOSING:
                self._set_closing(WSCloseCode.OK)
            elif msg.type is WSMsgType.PING and self._autoping:
                await self.pong(msg.data)
                continue
            elif msg.type is WSMsgType.PONG and self._autoping:
                continue

            return msg

    async def receive_str(self, *, timeout: Optional[float] = None) -> str:
        msg = await self.receive(timeout)
        if msg.type is not WSMsgType.TEXT:
            raise WSMessageTypeError(
                f"Received message {msg.type}:{msg.data!r} is not WSMsgType.TEXT"
            )
        return cast(str, msg.data)

    async def receive_bytes(self, *, timeout: Optional[float] = None) -> bytes:
        msg = await self.receive(timeout)
        if msg.type is not WSMsgType.BINARY:
            raise WSMessageTypeError(
                f"Received message {msg.type}:{msg.data!r} is not WSMsgType.BINARY"
            )
        return cast(bytes, msg.data)

    async def receive_json(
        self, *, loads: JSONDecoder = json.loads, timeout: Optional[float] = None
    ) -> Any:
        data = await self.receive_str(timeout=timeout)
        return loads(data)

    async def write(self, data: bytes) -> None:
        raise RuntimeError("Cannot call .write() for websocket")

    def __aiter__(self) -> "WebSocketResponse":
        return self

    async def __anext__(self) -> WSMessage:
        msg = await self.receive()
        if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
            raise StopAsyncIteration
        return msg

    def _cancel(self, exc: BaseException) -> None:
        # web_protocol calls this from connection_lost
        # or when the server is shutting down.
        self._closing = True
        self._cancel_heartbeat()
        if self._reader is not None:
            set_exception(self._reader, exc)

# === NexusCore/openenv\Lib\site-packages\platformdirs\__init__.py ===
"""
Utilities for determining application-specific dirs.

See <https://github.com/platformdirs/platformdirs> for details and usage.

"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from .api import PlatformDirsABC
from .version import __version__
from .version import __version_tuple__ as __version_info__

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal

if sys.platform == "win32":
    from platformdirs.windows import Windows as _Result
elif sys.platform == "darwin":
    from platformdirs.macos import MacOS as _Result
else:
    from platformdirs.unix import Unix as _Result


def _set_platform_dir_class() -> type[PlatformDirsABC]:
    if os.getenv("ANDROID_DATA") == "/data" and os.getenv("ANDROID_ROOT") == "/system":
        if os.getenv("SHELL") or os.getenv("PREFIX"):
            return _Result

        from platformdirs.android import _android_folder  # noqa: PLC0415

        if _android_folder() is not None:
            from platformdirs.android import Android  # noqa: PLC0415

            return Android  # return to avoid redefinition of a result

    return _Result


if TYPE_CHECKING:
    # Work around mypy issue: https://github.com/python/mypy/issues/10962
    PlatformDirs = _Result
else:
    PlatformDirs = _set_platform_dir_class()  #: Currently active platform
AppDirs = PlatformDirs  #: Backwards compatibility with appdirs


def user_data_dir(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_data_dir


def site_data_dir(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `roaming <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data directory shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_data_dir


def user_config_dir(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_config_dir


def site_config_dir(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `roaming <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config directory shared by the users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_config_dir


def user_cache_dir(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_cache_dir


def site_cache_dir(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_cache_dir


def user_state_dir(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: state directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_state_dir


def user_log_dir(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: log directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_log_dir


def user_documents_dir() -> str:
    """:returns: documents directory tied to the user"""
    return PlatformDirs().user_documents_dir


def user_downloads_dir() -> str:
    """:returns: downloads directory tied to the user"""
    return PlatformDirs().user_downloads_dir


def user_pictures_dir() -> str:
    """:returns: pictures directory tied to the user"""
    return PlatformDirs().user_pictures_dir


def user_videos_dir() -> str:
    """:returns: videos directory tied to the user"""
    return PlatformDirs().user_videos_dir


def user_music_dir() -> str:
    """:returns: music directory tied to the user"""
    return PlatformDirs().user_music_dir


def user_desktop_dir() -> str:
    """:returns: desktop directory tied to the user"""
    return PlatformDirs().user_desktop_dir


def user_runtime_dir(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_runtime_dir


def site_runtime_dir(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime directory shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_runtime_dir


def user_data_path(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_data_path


def site_data_path(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `multipath <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data path shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_data_path


def user_config_path(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_config_path


def site_config_path(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `roaming <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config path shared by the users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_config_path


def site_cache_path(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_cache_path


def user_cache_path(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_cache_path


def user_state_path(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: state path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_state_path


def user_log_path(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: log path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_log_path


def user_documents_path() -> Path:
    """:returns: documents a path tied to the user"""
    return PlatformDirs().user_documents_path


def user_downloads_path() -> Path:
    """:returns: downloads path tied to the user"""
    return PlatformDirs().user_downloads_path


def user_pictures_path() -> Path:
    """:returns: pictures path tied to the user"""
    return PlatformDirs().user_pictures_path


def user_videos_path() -> Path:
    """:returns: videos path tied to the user"""
    return PlatformDirs().user_videos_path


def user_music_path() -> Path:
    """:returns: music path tied to the user"""
    return PlatformDirs().user_music_path


def user_desktop_path() -> Path:
    """:returns: desktop path tied to the user"""
    return PlatformDirs().user_desktop_path


def user_runtime_path(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_runtime_path


def site_runtime_path(
    appname: str | None = None,
    appauthor: str | Literal[False] | None = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime path shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_runtime_path


__all__ = [
    "AppDirs",
    "PlatformDirs",
    "PlatformDirsABC",
    "__version__",
    "__version_info__",
    "site_cache_dir",
    "site_cache_path",
    "site_config_dir",
    "site_config_path",
    "site_data_dir",
    "site_data_path",
    "site_runtime_dir",
    "site_runtime_path",
    "user_cache_dir",
    "user_cache_path",
    "user_config_dir",
    "user_config_path",
    "user_data_dir",
    "user_data_path",
    "user_desktop_dir",
    "user_desktop_path",
    "user_documents_dir",
    "user_documents_path",
    "user_downloads_dir",
    "user_downloads_path",
    "user_log_dir",
    "user_log_path",
    "user_music_dir",
    "user_music_path",
    "user_pictures_dir",
    "user_pictures_path",
    "user_runtime_dir",
    "user_runtime_path",
    "user_state_dir",
    "user_state_path",
    "user_videos_dir",
    "user_videos_path",
]

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\cff.py ===
from collections import namedtuple
from fontTools.cffLib import (
    maxStackLimit,
    TopDictIndex,
    buildOrder,
    topDictOperators,
    topDictOperators2,
    privateDictOperators,
    privateDictOperators2,
    FDArrayIndex,
    FontDict,
    VarStoreData,
)
from io import BytesIO
from fontTools.cffLib.specializer import specializeCommands, commandsToProgram
from fontTools.ttLib import newTable
from fontTools import varLib
from fontTools.varLib.models import allEqual
from fontTools.misc.loggingTools import deprecateFunction
from fontTools.misc.roundTools import roundFunc
from fontTools.misc.psCharStrings import T2CharString, T2OutlineExtractor
from fontTools.pens.t2CharStringPen import T2CharStringPen
from functools import partial

from .errors import (
    VarLibCFFDictMergeError,
    VarLibCFFPointTypeMergeError,
    VarLibCFFHintTypeMergeError,
    VarLibMergeError,
)


# Backwards compatibility
MergeDictError = VarLibCFFDictMergeError
MergeTypeError = VarLibCFFPointTypeMergeError


def addCFFVarStore(varFont, varModel, varDataList, masterSupports):
    fvarTable = varFont["fvar"]
    axisKeys = [axis.axisTag for axis in fvarTable.axes]
    varTupleList = varLib.builder.buildVarRegionList(masterSupports, axisKeys)
    varStoreCFFV = varLib.builder.buildVarStore(varTupleList, varDataList)

    topDict = varFont["CFF2"].cff.topDictIndex[0]
    topDict.VarStore = VarStoreData(otVarStore=varStoreCFFV)
    if topDict.FDArray[0].vstore is None:
        fdArray = topDict.FDArray
        for fontDict in fdArray:
            if hasattr(fontDict, "Private"):
                fontDict.Private.vstore = topDict.VarStore


@deprecateFunction("Use fontTools.cffLib.CFFToCFF2.convertCFFToCFF2 instead.")
def convertCFFtoCFF2(varFont):
    from fontTools.cffLib.CFFToCFF2 import convertCFFToCFF2

    return convertCFFToCFF2(varFont)


def conv_to_int(num):
    if isinstance(num, float) and num.is_integer():
        return int(num)
    return num


pd_blend_fields = (
    "BlueValues",
    "OtherBlues",
    "FamilyBlues",
    "FamilyOtherBlues",
    "BlueScale",
    "BlueShift",
    "BlueFuzz",
    "StdHW",
    "StdVW",
    "StemSnapH",
    "StemSnapV",
)


def get_private(regionFDArrays, fd_index, ri, fd_map):
    region_fdArray = regionFDArrays[ri]
    region_fd_map = fd_map[fd_index]
    if ri in region_fd_map:
        region_fdIndex = region_fd_map[ri]
        private = region_fdArray[region_fdIndex].Private
    else:
        private = None
    return private


def merge_PrivateDicts(top_dicts, vsindex_dict, var_model, fd_map):
    """
    I step through the FontDicts in the FDArray of the varfont TopDict.
    For each varfont FontDict:

    * step through each key in FontDict.Private.
    * For each key, step through each relevant source font Private dict, and
      build a list of values to blend.

    The 'relevant' source fonts are selected by first getting the right
    submodel using ``vsindex_dict[vsindex]``. The indices of the
    ``subModel.locations`` are mapped to source font list indices by
    assuming the latter order is the same as the order of the
    ``var_model.locations``. I can then get the index of each subModel
    location in the list of ``var_model.locations``.
    """

    topDict = top_dicts[0]
    region_top_dicts = top_dicts[1:]
    if hasattr(region_top_dicts[0], "FDArray"):
        regionFDArrays = [fdTopDict.FDArray for fdTopDict in region_top_dicts]
    else:
        regionFDArrays = [[fdTopDict] for fdTopDict in region_top_dicts]
    for fd_index, font_dict in enumerate(topDict.FDArray):
        private_dict = font_dict.Private
        vsindex = getattr(private_dict, "vsindex", 0)
        # At the moment, no PrivateDict has a vsindex key, but let's support
        # how it should work. See comment at end of
        # merge_charstrings() - still need to optimize use of vsindex.
        sub_model, _ = vsindex_dict[vsindex]
        master_indices = []
        for loc in sub_model.locations[1:]:
            i = var_model.locations.index(loc) - 1
            master_indices.append(i)
        pds = [private_dict]
        last_pd = private_dict
        for ri in master_indices:
            pd = get_private(regionFDArrays, fd_index, ri, fd_map)
            # If the region font doesn't have this FontDict, just reference
            # the last one used.
            if pd is None:
                pd = last_pd
            else:
                last_pd = pd
            pds.append(pd)
        num_masters = len(pds)
        for key, value in private_dict.rawDict.items():
            dataList = []
            if key not in pd_blend_fields:
                continue
            if isinstance(value, list):
                try:
                    values = [pd.rawDict[key] for pd in pds]
                except KeyError:
                    print(
                        "Warning: {key} in default font Private dict is "
                        "missing from another font, and was "
                        "discarded.".format(key=key)
                    )
                    continue
                try:
                    values = zip(*values)
                except IndexError:
                    raise VarLibCFFDictMergeError(key, value, values)
                """
				Row 0 contains the first  value from each master.
				Convert each row from absolute values to relative
				values from the previous row.
				e.g for three masters,	a list of values was:
				master 0 OtherBlues = [-217,-205]
				master 1 OtherBlues = [-234,-222]
				master 1 OtherBlues = [-188,-176]
				The call to zip() converts this to:
				[(-217, -234, -188), (-205, -222, -176)]
				and is converted finally to:
				OtherBlues = [[-217, 17.0, 46.0], [-205, 0.0, 0.0]]
				"""
                prev_val_list = [0] * num_masters
                any_points_differ = False
                for val_list in values:
                    rel_list = [
                        (val - prev_val_list[i]) for (i, val) in enumerate(val_list)
                    ]
                    if (not any_points_differ) and not allEqual(rel_list):
                        any_points_differ = True
                    prev_val_list = val_list
                    deltas = sub_model.getDeltas(rel_list)
                    # For PrivateDict BlueValues, the default font
                    # values are absolute, not relative to the prior value.
                    deltas[0] = val_list[0]
                    dataList.append(deltas)
                # If there are no blend values,then
                # we can collapse the blend lists.
                if not any_points_differ:
                    dataList = [data[0] for data in dataList]
            else:
                values = [pd.rawDict[key] for pd in pds]
                if not allEqual(values):
                    dataList = sub_model.getDeltas(values)
                else:
                    dataList = values[0]

            # Convert numbers with no decimal part to an int
            if isinstance(dataList, list):
                for i, item in enumerate(dataList):
                    if isinstance(item, list):
                        for j, jtem in enumerate(item):
                            dataList[i][j] = conv_to_int(jtem)
                    else:
                        dataList[i] = conv_to_int(item)
            else:
                dataList = conv_to_int(dataList)

            private_dict.rawDict[key] = dataList


def _cff_or_cff2(font):
    if "CFF " in font:
        return font["CFF "]
    return font["CFF2"]


def getfd_map(varFont, fonts_list):
    """Since a subset source font may have fewer FontDicts in their
    FDArray than the default font, we have to match up the FontDicts in
    the different fonts . We do this with the FDSelect array, and by
    assuming that the same glyph will reference  matching FontDicts in
    each source font. We return a mapping from fdIndex in the default
    font to a dictionary which maps each master list index of each
    region font to the equivalent fdIndex in the region font."""
    fd_map = {}
    default_font = fonts_list[0]
    region_fonts = fonts_list[1:]
    num_regions = len(region_fonts)
    topDict = _cff_or_cff2(default_font).cff.topDictIndex[0]
    if not hasattr(topDict, "FDSelect"):
        # All glyphs reference only one FontDict.
        # Map the FD index for regions to index 0.
        fd_map[0] = {ri: 0 for ri in range(num_regions)}
        return fd_map

    gname_mapping = {}
    default_fdSelect = topDict.FDSelect
    glyphOrder = default_font.getGlyphOrder()
    for gid, fdIndex in enumerate(default_fdSelect):
        gname_mapping[glyphOrder[gid]] = fdIndex
        if fdIndex not in fd_map:
            fd_map[fdIndex] = {}
    for ri, region_font in enumerate(region_fonts):
        region_glyphOrder = region_font.getGlyphOrder()
        region_topDict = _cff_or_cff2(region_font).cff.topDictIndex[0]
        if not hasattr(region_topDict, "FDSelect"):
            # All the glyphs share the same FontDict. Pick any glyph.
            default_fdIndex = gname_mapping[region_glyphOrder[0]]
            fd_map[default_fdIndex][ri] = 0
        else:
            region_fdSelect = region_topDict.FDSelect
            for gid, fdIndex in enumerate(region_fdSelect):
                default_fdIndex = gname_mapping[region_glyphOrder[gid]]
                region_map = fd_map[default_fdIndex]
                if ri not in region_map:
                    region_map[ri] = fdIndex
    return fd_map


CVarData = namedtuple("CVarData", "varDataList masterSupports vsindex_dict")


def merge_region_fonts(varFont, model, ordered_fonts_list, glyphOrder):
    topDict = varFont["CFF2"].cff.topDictIndex[0]
    top_dicts = [topDict] + [
        _cff_or_cff2(ttFont).cff.topDictIndex[0] for ttFont in ordered_fonts_list[1:]
    ]
    num_masters = len(model.mapping)
    cvData = merge_charstrings(glyphOrder, num_masters, top_dicts, model)
    fd_map = getfd_map(varFont, ordered_fonts_list)
    merge_PrivateDicts(top_dicts, cvData.vsindex_dict, model, fd_map)
    addCFFVarStore(varFont, model, cvData.varDataList, cvData.masterSupports)


def _get_cs(charstrings, glyphName, filterEmpty=False):
    if glyphName not in charstrings:
        return None
    cs = charstrings[glyphName]

    if filterEmpty:
        cs.decompile()
        if cs.program == []:  # CFF2 empty charstring
            return None
        elif (
            len(cs.program) <= 2
            and cs.program[-1] == "endchar"
            and (len(cs.program) == 1 or type(cs.program[0]) in (int, float))
        ):  # CFF1 empty charstring
            return None

    return cs


def _add_new_vsindex(
    model, key, masterSupports, vsindex_dict, vsindex_by_key, varDataList
):
    varTupleIndexes = []
    for support in model.supports[1:]:
        if support not in masterSupports:
            masterSupports.append(support)
        varTupleIndexes.append(masterSupports.index(support))
    var_data = varLib.builder.buildVarData(varTupleIndexes, None, False)
    vsindex = len(vsindex_dict)
    vsindex_by_key[key] = vsindex
    vsindex_dict[vsindex] = (model, [key])
    varDataList.append(var_data)
    return vsindex


def merge_charstrings(glyphOrder, num_masters, top_dicts, masterModel):
    vsindex_dict = {}
    vsindex_by_key = {}
    varDataList = []
    masterSupports = []
    default_charstrings = top_dicts[0].CharStrings
    for gid, gname in enumerate(glyphOrder):
        # interpret empty non-default masters as missing glyphs from a sparse master
        all_cs = [
            _get_cs(td.CharStrings, gname, i != 0) for i, td in enumerate(top_dicts)
        ]
        model, model_cs = masterModel.getSubModel(all_cs)
        # create the first pass CFF2 charstring, from
        # the default charstring.
        default_charstring = model_cs[0]
        var_pen = CFF2CharStringMergePen([], gname, num_masters, 0)
        # We need to override outlineExtractor because these
        # charstrings do have widths in the 'program'; we need to drop these
        # values rather than post assertion error for them.
        default_charstring.outlineExtractor = MergeOutlineExtractor
        default_charstring.draw(var_pen)

        # Add the coordinates from all the other regions to the
        # blend lists in the CFF2 charstring.
        region_cs = model_cs[1:]
        for region_idx, region_charstring in enumerate(region_cs, start=1):
            var_pen.restart(region_idx)
            region_charstring.outlineExtractor = MergeOutlineExtractor
            region_charstring.draw(var_pen)

        # Collapse each coordinate list to a blend operator and its args.
        new_cs = var_pen.getCharString(
            private=default_charstring.private,
            globalSubrs=default_charstring.globalSubrs,
            var_model=model,
            optimize=True,
        )
        default_charstrings[gname] = new_cs

        if not region_cs:
            continue

        if (not var_pen.seen_moveto) or ("blend" not in new_cs.program):
            # If this is not a marking glyph, or if there are no blend
            # arguments, then we can use vsindex 0. No need to
            # check if we need a new vsindex.
            continue

        # If the charstring required a new model, create
        # a VarData table to go with, and set vsindex.
        key = tuple(v is not None for v in all_cs)
        try:
            vsindex = vsindex_by_key[key]
        except KeyError:
            vsindex = _add_new_vsindex(
                model, key, masterSupports, vsindex_dict, vsindex_by_key, varDataList
            )
        # We do not need to check for an existing new_cs.private.vsindex,
        # as we know it doesn't exist yet.
        if vsindex != 0:
            new_cs.program[:0] = [vsindex, "vsindex"]

    # If there is no variation in any of the charstrings, then vsindex_dict
    # never gets built. This could still be needed if there is variation
    # in the PrivatDict, so we will build the default data for vsindex = 0.
    if not vsindex_dict:
        key = (True,) * num_masters
        _add_new_vsindex(
            masterModel, key, masterSupports, vsindex_dict, vsindex_by_key, varDataList
        )
    cvData = CVarData(
        varDataList=varDataList,
        masterSupports=masterSupports,
        vsindex_dict=vsindex_dict,
    )
    # XXX To do: optimize use of vsindex between the PrivateDicts and
    # charstrings
    return cvData


class CFFToCFF2OutlineExtractor(T2OutlineExtractor):
    """This class is used to remove the initial width from the CFF
    charstring without trying to add the width to self.nominalWidthX,
    which is None."""

    def popallWidth(self, evenOdd=0):
        args = self.popall()
        if not self.gotWidth:
            if evenOdd ^ (len(args) % 2):
                args = args[1:]
            self.width = self.defaultWidthX
            self.gotWidth = 1
        return args


class MergeOutlineExtractor(CFFToCFF2OutlineExtractor):
    """Used to extract the charstring commands - including hints - from a
    CFF charstring in order to merge it as another set of region data
    into a CFF2 variable font charstring."""

    def __init__(
        self,
        pen,
        localSubrs,
        globalSubrs,
        nominalWidthX,
        defaultWidthX,
        private=None,
        blender=None,
    ):
        super().__init__(
            pen, localSubrs, globalSubrs, nominalWidthX, defaultWidthX, private, blender
        )

    def countHints(self):
        args = self.popallWidth()
        self.hintCount = self.hintCount + len(args) // 2
        return args

    def _hint_op(self, type, args):
        self.pen.add_hint(type, args)

    def op_hstem(self, index):
        args = self.countHints()
        self._hint_op("hstem", args)

    def op_vstem(self, index):
        args = self.countHints()
        self._hint_op("vstem", args)

    def op_hstemhm(self, index):
        args = self.countHints()
        self._hint_op("hstemhm", args)

    def op_vstemhm(self, index):
        args = self.countHints()
        self._hint_op("vstemhm", args)

    def _get_hintmask(self, index):
        if not self.hintMaskBytes:
            args = self.countHints()
            if args:
                self._hint_op("vstemhm", args)
            self.hintMaskBytes = (self.hintCount + 7) // 8
        hintMaskBytes, index = self.callingStack[-1].getBytes(index, self.hintMaskBytes)
        return index, hintMaskBytes

    def op_hintmask(self, index):
        index, hintMaskBytes = self._get_hintmask(index)
        self.pen.add_hintmask("hintmask", [hintMaskBytes])
        return hintMaskBytes, index

    def op_cntrmask(self, index):
        index, hintMaskBytes = self._get_hintmask(index)
        self.pen.add_hintmask("cntrmask", [hintMaskBytes])
        return hintMaskBytes, index


class CFF2CharStringMergePen(T2CharStringPen):
    """Pen to merge Type 2 CharStrings."""

    def __init__(
        self, default_commands, glyphName, num_masters, master_idx, roundTolerance=0.01
    ):
        # For roundTolerance see https://github.com/fonttools/fonttools/issues/2838
        super().__init__(
            width=None, glyphSet=None, CFF2=True, roundTolerance=roundTolerance
        )
        self.pt_index = 0
        self._commands = default_commands
        self.m_index = master_idx
        self.num_masters = num_masters
        self.prev_move_idx = 0
        self.seen_moveto = False
        self.glyphName = glyphName
        self.round = roundFunc(roundTolerance, round=round)

    def add_point(self, point_type, pt_coords):
        if self.m_index == 0:
            self._commands.append([point_type, [pt_coords]])
        else:
            cmd = self._commands[self.pt_index]
            if cmd[0] != point_type:
                raise VarLibCFFPointTypeMergeError(
                    point_type, self.pt_index, len(cmd[1]), cmd[0], self.glyphName
                )
            cmd[1].append(pt_coords)
        self.pt_index += 1

    def add_hint(self, hint_type, args):
        if self.m_index == 0:
            self._commands.append([hint_type, [args]])
        else:
            cmd = self._commands[self.pt_index]
            if cmd[0] != hint_type:
                raise VarLibCFFHintTypeMergeError(
                    hint_type, self.pt_index, len(cmd[1]), cmd[0], self.glyphName
                )
            cmd[1].append(args)
        self.pt_index += 1

    def add_hintmask(self, hint_type, abs_args):
        # For hintmask, fonttools.cffLib.specializer.py expects
        # each of these to be represented by two sequential commands:
        # first holding only the operator name, with an empty arg list,
        # second with an empty string as the op name, and the mask arg list.
        if self.m_index == 0:
            self._commands.append([hint_type, []])
            self._commands.append(["", [abs_args]])
        else:
            cmd = self._commands[self.pt_index]
            if cmd[0] != hint_type:
                raise VarLibCFFHintTypeMergeError(
                    hint_type, self.pt_index, len(cmd[1]), cmd[0], self.glyphName
                )
            self.pt_index += 1
            cmd = self._commands[self.pt_index]
            cmd[1].append(abs_args)
        self.pt_index += 1

    def _moveTo(self, pt):
        if not self.seen_moveto:
            self.seen_moveto = True
        pt_coords = self._p(pt)
        self.add_point("rmoveto", pt_coords)
        # I set prev_move_idx here because add_point()
        # can change self.pt_index.
        self.prev_move_idx = self.pt_index - 1

    def _lineTo(self, pt):
        pt_coords = self._p(pt)
        self.add_point("rlineto", pt_coords)

    def _curveToOne(self, pt1, pt2, pt3):
        _p = self._p
        pt_coords = _p(pt1) + _p(pt2) + _p(pt3)
        self.add_point("rrcurveto", pt_coords)

    def _closePath(self):
        pass

    def _endPath(self):
        pass

    def restart(self, region_idx):
        self.pt_index = 0
        self.m_index = region_idx
        self._p0 = (0, 0)

    def getCommands(self):
        return self._commands

    def reorder_blend_args(self, commands, get_delta_func):
        """
        We first re-order the master coordinate values.
        For a moveto to lineto, the args are now arranged as::

                [ [master_0 x,y], [master_1 x,y], [master_2 x,y] ]

        We re-arrange this to::

                [	[master_0 x, master_1 x, master_2 x],
                        [master_0 y, master_1 y, master_2 y]
                ]

        If the master values are all the same, we collapse the list to
        as single value instead of a list.

        We then convert this to::

                [ [master_0 x] + [x delta tuple] + [numBlends=1]
                  [master_0 y] + [y delta tuple] + [numBlends=1]
                ]
        """
        for cmd in commands:
            # arg[i] is the set of arguments for this operator from master i.
            args = cmd[1]
            m_args = zip(*args)
            # m_args[n] is now all num_master args for the i'th argument
            # for this operation.
            cmd[1] = list(m_args)
        lastOp = None
        for cmd in commands:
            op = cmd[0]
            # masks are represented by two cmd's: first has only op names,
            # second has only args.
            if lastOp in ["hintmask", "cntrmask"]:
                coord = list(cmd[1])
                if not allEqual(coord):
                    raise VarLibMergeError(
                        "Hintmask values cannot differ between source fonts."
                    )
                cmd[1] = [coord[0][0]]
            else:
                coords = cmd[1]
                new_coords = []
                for coord in coords:
                    if allEqual(coord):
                        new_coords.append(coord[0])
                    else:
                        # convert to deltas
                        deltas = get_delta_func(coord)[1:]
                        coord = [coord[0]] + deltas
                        coord.append(1)
                        new_coords.append(coord)
                cmd[1] = new_coords
            lastOp = op
        return commands

    def getCharString(
        self, private=None, globalSubrs=None, var_model=None, optimize=True
    ):
        commands = self._commands
        commands = self.reorder_blend_args(
            commands, partial(var_model.getDeltas, round=self.round)
        )
        if optimize:
            commands = specializeCommands(
                commands, generalizeFirst=False, maxstack=maxStackLimit
            )
        program = commandsToProgram(commands)
        charString = T2CharString(
            program=program, private=private, globalSubrs=globalSubrs
        )
        return charString

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\platformdirs\__init__.py ===
"""
Utilities for determining application-specific dirs.

See <https://github.com/platformdirs/platformdirs> for details and usage.

"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from .api import PlatformDirsABC
from .version import __version__
from .version import __version_tuple__ as __version_info__

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal

if sys.platform == "win32":
    from pip._vendor.platformdirs.windows import Windows as _Result
elif sys.platform == "darwin":
    from pip._vendor.platformdirs.macos import MacOS as _Result
else:
    from pip._vendor.platformdirs.unix import Unix as _Result


def _set_platform_dir_class() -> type[PlatformDirsABC]:
    if os.getenv("ANDROID_DATA") == "/data" and os.getenv("ANDROID_ROOT") == "/system":
        if os.getenv("SHELL") or os.getenv("PREFIX"):
            return _Result

        from pip._vendor.platformdirs.android import _android_folder  # noqa: PLC0415

        if _android_folder() is not None:
            from pip._vendor.platformdirs.android import Android  # noqa: PLC0415

            return Android  # return to avoid redefinition of a result

    return _Result


if TYPE_CHECKING:
    # Work around mypy issue: https://github.com/python/mypy/issues/10962
    PlatformDirs = _Result
else:
    PlatformDirs = _set_platform_dir_class()  #: Currently active platform
AppDirs = PlatformDirs  #: Backwards compatibility with appdirs


def user_data_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_data_dir


def site_data_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `roaming <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data directory shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_data_dir


def user_config_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_config_dir


def site_config_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `roaming <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config directory shared by the users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_config_dir


def user_cache_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_cache_dir


def site_cache_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_cache_dir


def user_state_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: state directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_state_dir


def user_log_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: log directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_log_dir


def user_documents_dir() -> str:
    """:returns: documents directory tied to the user"""
    return PlatformDirs().user_documents_dir


def user_downloads_dir() -> str:
    """:returns: downloads directory tied to the user"""
    return PlatformDirs().user_downloads_dir


def user_pictures_dir() -> str:
    """:returns: pictures directory tied to the user"""
    return PlatformDirs().user_pictures_dir


def user_videos_dir() -> str:
    """:returns: videos directory tied to the user"""
    return PlatformDirs().user_videos_dir


def user_music_dir() -> str:
    """:returns: music directory tied to the user"""
    return PlatformDirs().user_music_dir


def user_desktop_dir() -> str:
    """:returns: desktop directory tied to the user"""
    return PlatformDirs().user_desktop_dir


def user_runtime_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_runtime_dir


def site_runtime_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime directory shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_runtime_dir


def user_data_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_data_path


def site_data_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `multipath <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data path shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_data_path


def user_config_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_config_path


def site_config_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `roaming <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config path shared by the users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_config_path


def site_cache_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_cache_path


def user_cache_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_cache_path


def user_state_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: state path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_state_path


def user_log_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: log path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_log_path


def user_documents_path() -> Path:
    """:returns: documents a path tied to the user"""
    return PlatformDirs().user_documents_path


def user_downloads_path() -> Path:
    """:returns: downloads path tied to the user"""
    return PlatformDirs().user_downloads_path


def user_pictures_path() -> Path:
    """:returns: pictures path tied to the user"""
    return PlatformDirs().user_pictures_path


def user_videos_path() -> Path:
    """:returns: videos path tied to the user"""
    return PlatformDirs().user_videos_path


def user_music_path() -> Path:
    """:returns: music path tied to the user"""
    return PlatformDirs().user_music_path


def user_desktop_path() -> Path:
    """:returns: desktop path tied to the user"""
    return PlatformDirs().user_desktop_path


def user_runtime_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_runtime_path


def site_runtime_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime path shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_runtime_path


__all__ = [
    "AppDirs",
    "PlatformDirs",
    "PlatformDirsABC",
    "__version__",
    "__version_info__",
    "site_cache_dir",
    "site_cache_path",
    "site_config_dir",
    "site_config_path",
    "site_data_dir",
    "site_data_path",
    "site_runtime_dir",
    "site_runtime_path",
    "user_cache_dir",
    "user_cache_path",
    "user_config_dir",
    "user_config_path",
    "user_data_dir",
    "user_data_path",
    "user_desktop_dir",
    "user_desktop_path",
    "user_documents_dir",
    "user_documents_path",
    "user_downloads_dir",
    "user_downloads_path",
    "user_log_dir",
    "user_log_path",
    "user_music_dir",
    "user_music_path",
    "user_pictures_dir",
    "user_pictures_path",
    "user_runtime_dir",
    "user_runtime_path",
    "user_state_dir",
    "user_state_path",
    "user_videos_dir",
    "user_videos_path",
]

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\childes.py ===
# CHILDES XML Corpus Reader

# Copyright (C) 2001-2024 NLTK Project
# Author: Tomonori Nagano <tnagano@gc.cuny.edu>
#         Alexis Dimitriadis <A.Dimitriadis@uu.nl>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Corpus reader for the XML version of the CHILDES corpus.
"""

__docformat__ = "epytext en"

import re
from collections import defaultdict

from nltk.corpus.reader.util import concat
from nltk.corpus.reader.xmldocs import ElementTree, XMLCorpusReader
from nltk.util import LazyConcatenation, LazyMap, flatten

# to resolve the namespace issue
NS = "http://www.talkbank.org/ns/talkbank"


class CHILDESCorpusReader(XMLCorpusReader):
    """
    Corpus reader for the XML version of the CHILDES corpus.
    The CHILDES corpus is available at ``https://childes.talkbank.org/``. The XML
    version of CHILDES is located at ``https://childes.talkbank.org/data-xml/``.
    Copy the needed parts of the CHILDES XML corpus into the NLTK data directory
    (``nltk_data/corpora/CHILDES/``).

    For access to the file text use the usual nltk functions,
    ``words()``, ``sents()``, ``tagged_words()`` and ``tagged_sents()``.
    """

    def __init__(self, root, fileids, lazy=True):
        XMLCorpusReader.__init__(self, root, fileids)
        self._lazy = lazy

    def words(
        self,
        fileids=None,
        speaker="ALL",
        stem=False,
        relation=False,
        strip_space=True,
        replace=False,
    ):
        """
        :return: the given file(s) as a list of words
        :rtype: list(str)

        :param speaker: If specified, select specific speaker(s) defined
            in the corpus. Default is 'ALL' (all participants). Common choices
            are 'CHI' (the child), 'MOT' (mother), ['CHI','MOT'] (exclude
            researchers)
        :param stem: If true, then use word stems instead of word strings.
        :param relation: If true, then return tuples of (stem, index,
            dependent_index)
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced (intended) word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        sent = None
        pos = False
        if not self._lazy:
            return [
                self._get_words(
                    fileid, speaker, sent, stem, relation, pos, strip_space, replace
                )
                for fileid in self.abspaths(fileids)
            ]

        get_words = lambda fileid: self._get_words(
            fileid, speaker, sent, stem, relation, pos, strip_space, replace
        )
        return LazyConcatenation(LazyMap(get_words, self.abspaths(fileids)))

    def tagged_words(
        self,
        fileids=None,
        speaker="ALL",
        stem=False,
        relation=False,
        strip_space=True,
        replace=False,
    ):
        """
        :return: the given file(s) as a list of tagged
            words and punctuation symbols, encoded as tuples
            ``(word,tag)``.
        :rtype: list(tuple(str,str))

        :param speaker: If specified, select specific speaker(s) defined
            in the corpus. Default is 'ALL' (all participants). Common choices
            are 'CHI' (the child), 'MOT' (mother), ['CHI','MOT'] (exclude
            researchers)
        :param stem: If true, then use word stems instead of word strings.
        :param relation: If true, then return tuples of (stem, index,
            dependent_index)
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced (intended) word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        sent = None
        pos = True
        if not self._lazy:
            return [
                self._get_words(
                    fileid, speaker, sent, stem, relation, pos, strip_space, replace
                )
                for fileid in self.abspaths(fileids)
            ]

        get_words = lambda fileid: self._get_words(
            fileid, speaker, sent, stem, relation, pos, strip_space, replace
        )
        return LazyConcatenation(LazyMap(get_words, self.abspaths(fileids)))

    def sents(
        self,
        fileids=None,
        speaker="ALL",
        stem=False,
        relation=None,
        strip_space=True,
        replace=False,
    ):
        """
        :return: the given file(s) as a list of sentences or utterances, each
            encoded as a list of word strings.
        :rtype: list(list(str))

        :param speaker: If specified, select specific speaker(s) defined
            in the corpus. Default is 'ALL' (all participants). Common choices
            are 'CHI' (the child), 'MOT' (mother), ['CHI','MOT'] (exclude
            researchers)
        :param stem: If true, then use word stems instead of word strings.
        :param relation: If true, then return tuples of ``(str,pos,relation_list)``.
            If there is manually-annotated relation info, it will return
            tuples of ``(str,pos,test_relation_list,str,pos,gold_relation_list)``
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced (intended) word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        sent = True
        pos = False
        if not self._lazy:
            return [
                self._get_words(
                    fileid, speaker, sent, stem, relation, pos, strip_space, replace
                )
                for fileid in self.abspaths(fileids)
            ]

        get_words = lambda fileid: self._get_words(
            fileid, speaker, sent, stem, relation, pos, strip_space, replace
        )
        return LazyConcatenation(LazyMap(get_words, self.abspaths(fileids)))

    def tagged_sents(
        self,
        fileids=None,
        speaker="ALL",
        stem=False,
        relation=None,
        strip_space=True,
        replace=False,
    ):
        """
        :return: the given file(s) as a list of
            sentences, each encoded as a list of ``(word,tag)`` tuples.
        :rtype: list(list(tuple(str,str)))

        :param speaker: If specified, select specific speaker(s) defined
            in the corpus. Default is 'ALL' (all participants). Common choices
            are 'CHI' (the child), 'MOT' (mother), ['CHI','MOT'] (exclude
            researchers)
        :param stem: If true, then use word stems instead of word strings.
        :param relation: If true, then return tuples of ``(str,pos,relation_list)``.
            If there is manually-annotated relation info, it will return
            tuples of ``(str,pos,test_relation_list,str,pos,gold_relation_list)``
        :param strip_space: If true, then strip trailing spaces from word
            tokens. Otherwise, leave the spaces on the tokens.
        :param replace: If true, then use the replaced (intended) word instead
            of the original word (e.g., 'wat' will be replaced with 'watch')
        """
        sent = True
        pos = True
        if not self._lazy:
            return [
                self._get_words(
                    fileid, speaker, sent, stem, relation, pos, strip_space, replace
                )
                for fileid in self.abspaths(fileids)
            ]

        get_words = lambda fileid: self._get_words(
            fileid, speaker, sent, stem, relation, pos, strip_space, replace
        )
        return LazyConcatenation(LazyMap(get_words, self.abspaths(fileids)))

    def corpus(self, fileids=None):
        """
        :return: the given file(s) as a dict of ``(corpus_property_key, value)``
        :rtype: list(dict)
        """
        if not self._lazy:
            return [self._get_corpus(fileid) for fileid in self.abspaths(fileids)]
        return LazyMap(self._get_corpus, self.abspaths(fileids))

    def _get_corpus(self, fileid):
        results = dict()
        xmldoc = ElementTree.parse(fileid).getroot()
        for key, value in xmldoc.items():
            results[key] = value
        return results

    def participants(self, fileids=None):
        """
        :return: the given file(s) as a dict of
            ``(participant_property_key, value)``
        :rtype: list(dict)
        """
        if not self._lazy:
            return [self._get_participants(fileid) for fileid in self.abspaths(fileids)]
        return LazyMap(self._get_participants, self.abspaths(fileids))

    def _get_participants(self, fileid):
        # multidimensional dicts
        def dictOfDicts():
            return defaultdict(dictOfDicts)

        xmldoc = ElementTree.parse(fileid).getroot()
        # getting participants' data
        pat = dictOfDicts()
        for participant in xmldoc.findall(
            f".//{{{NS}}}Participants/{{{NS}}}participant"
        ):
            for key, value in participant.items():
                pat[participant.get("id")][key] = value
        return pat

    def age(self, fileids=None, speaker="CHI", month=False):
        """
        :return: the given file(s) as string or int
        :rtype: list or int

        :param month: If true, return months instead of year-month-date
        """
        if not self._lazy:
            return [
                self._get_age(fileid, speaker, month)
                for fileid in self.abspaths(fileids)
            ]
        get_age = lambda fileid: self._get_age(fileid, speaker, month)
        return LazyMap(get_age, self.abspaths(fileids))

    def _get_age(self, fileid, speaker, month):
        xmldoc = ElementTree.parse(fileid).getroot()
        for pat in xmldoc.findall(f".//{{{NS}}}Participants/{{{NS}}}participant"):
            try:
                if pat.get("id") == speaker:
                    age = pat.get("age")
                    if month:
                        age = self.convert_age(age)
                    return age
            # some files don't have age data
            except (TypeError, AttributeError) as e:
                return None

    def convert_age(self, age_year):
        "Caclculate age in months from a string in CHILDES format"
        m = re.match(r"P(\d+)Y(\d+)M?(\d?\d?)D?", age_year)
        age_month = int(m.group(1)) * 12 + int(m.group(2))
        try:
            if int(m.group(3)) > 15:
                age_month += 1
        # some corpora don't have age information?
        except ValueError as e:
            pass
        return age_month

    def MLU(self, fileids=None, speaker="CHI"):
        """
        :return: the given file(s) as a floating number
        :rtype: list(float)
        """
        if not self._lazy:
            return [
                self._getMLU(fileid, speaker=speaker)
                for fileid in self.abspaths(fileids)
            ]
        get_MLU = lambda fileid: self._getMLU(fileid, speaker=speaker)
        return LazyMap(get_MLU, self.abspaths(fileids))

    def _getMLU(self, fileid, speaker):
        sents = self._get_words(
            fileid,
            speaker=speaker,
            sent=True,
            stem=True,
            relation=False,
            pos=True,
            strip_space=True,
            replace=True,
        )
        results = []
        lastSent = []
        numFillers = 0
        sentDiscount = 0
        for sent in sents:
            posList = [pos for (word, pos) in sent]
            # if any part of the sentence is intelligible
            if any(pos == "unk" for pos in posList):
                continue
            # if the sentence is null
            elif sent == []:
                continue
            # if the sentence is the same as the last sent
            elif sent == lastSent:
                continue
            else:
                results.append([word for (word, pos) in sent])
                # count number of fillers
                if len({"co", None}.intersection(posList)) > 0:
                    numFillers += posList.count("co")
                    numFillers += posList.count(None)
                    sentDiscount += 1
            lastSent = sent
        try:
            thisWordList = flatten(results)
            # count number of morphemes
            # (e.g., 'read' = 1 morpheme but 'read-PAST' is 2 morphemes)
            numWords = (
                len(flatten([word.split("-") for word in thisWordList])) - numFillers
            )
            numSents = len(results) - sentDiscount
            mlu = numWords / numSents
        except ZeroDivisionError:
            mlu = 0
        # return {'mlu':mlu,'wordNum':numWords,'sentNum':numSents}
        return mlu

    def _get_words(
        self, fileid, speaker, sent, stem, relation, pos, strip_space, replace
    ):
        if (
            isinstance(speaker, str) and speaker != "ALL"
        ):  # ensure we have a list of speakers
            speaker = [speaker]
        xmldoc = ElementTree.parse(fileid).getroot()
        # processing each xml doc
        results = []
        for xmlsent in xmldoc.findall(".//{%s}u" % NS):
            sents = []
            # select speakers
            if speaker == "ALL" or xmlsent.get("who") in speaker:
                for xmlword in xmlsent.findall(".//{%s}w" % NS):
                    infl = None
                    suffixStem = None
                    suffixTag = None
                    # getting replaced words
                    if replace and xmlsent.find(f".//{{{NS}}}w/{{{NS}}}replacement"):
                        xmlword = xmlsent.find(
                            f".//{{{NS}}}w/{{{NS}}}replacement/{{{NS}}}w"
                        )
                    elif replace and xmlsent.find(f".//{{{NS}}}w/{{{NS}}}wk"):
                        xmlword = xmlsent.find(f".//{{{NS}}}w/{{{NS}}}wk")
                    # get text
                    if xmlword.text:
                        word = xmlword.text
                    else:
                        word = ""
                    # strip tailing space
                    if strip_space:
                        word = word.strip()
                    # stem
                    if relation or stem:
                        try:
                            xmlstem = xmlword.find(".//{%s}stem" % NS)
                            word = xmlstem.text
                        except AttributeError as e:
                            pass
                        # if there is an inflection
                        try:
                            xmlinfl = xmlword.find(
                                f".//{{{NS}}}mor/{{{NS}}}mw/{{{NS}}}mk"
                            )
                            word += "-" + xmlinfl.text
                        except:
                            pass
                        # if there is a suffix
                        try:
                            xmlsuffix = xmlword.find(
                                ".//{%s}mor/{%s}mor-post/{%s}mw/{%s}stem"
                                % (NS, NS, NS, NS)
                            )
                            suffixStem = xmlsuffix.text
                        except AttributeError:
                            suffixStem = ""
                        if suffixStem:
                            word += "~" + suffixStem
                    # pos
                    if relation or pos:
                        try:
                            xmlpos = xmlword.findall(".//{%s}c" % NS)
                            xmlpos2 = xmlword.findall(".//{%s}s" % NS)
                            if xmlpos2 != []:
                                tag = xmlpos[0].text + ":" + xmlpos2[0].text
                            else:
                                tag = xmlpos[0].text
                        except (AttributeError, IndexError) as e:
                            tag = ""
                        try:
                            xmlsuffixpos = xmlword.findall(
                                ".//{%s}mor/{%s}mor-post/{%s}mw/{%s}pos/{%s}c"
                                % (NS, NS, NS, NS, NS)
                            )
                            xmlsuffixpos2 = xmlword.findall(
                                ".//{%s}mor/{%s}mor-post/{%s}mw/{%s}pos/{%s}s"
                                % (NS, NS, NS, NS, NS)
                            )
                            if xmlsuffixpos2:
                                suffixTag = (
                                    xmlsuffixpos[0].text + ":" + xmlsuffixpos2[0].text
                                )
                            else:
                                suffixTag = xmlsuffixpos[0].text
                        except:
                            pass
                        if suffixTag:
                            tag += "~" + suffixTag
                        word = (word, tag)
                    # relational
                    # the gold standard is stored in
                    # <mor></mor><mor type="trn"><gra type="grt">
                    if relation == True:
                        for xmlstem_rel in xmlword.findall(
                            f".//{{{NS}}}mor/{{{NS}}}gra"
                        ):
                            if not xmlstem_rel.get("type") == "grt":
                                word = (
                                    word[0],
                                    word[1],
                                    xmlstem_rel.get("index")
                                    + "|"
                                    + xmlstem_rel.get("head")
                                    + "|"
                                    + xmlstem_rel.get("relation"),
                                )
                            else:
                                word = (
                                    word[0],
                                    word[1],
                                    word[2],
                                    word[0],
                                    word[1],
                                    xmlstem_rel.get("index")
                                    + "|"
                                    + xmlstem_rel.get("head")
                                    + "|"
                                    + xmlstem_rel.get("relation"),
                                )
                        try:
                            for xmlpost_rel in xmlword.findall(
                                f".//{{{NS}}}mor/{{{NS}}}mor-post/{{{NS}}}gra"
                            ):
                                if not xmlpost_rel.get("type") == "grt":
                                    suffixStem = (
                                        suffixStem[0],
                                        suffixStem[1],
                                        xmlpost_rel.get("index")
                                        + "|"
                                        + xmlpost_rel.get("head")
                                        + "|"
                                        + xmlpost_rel.get("relation"),
                                    )
                                else:
                                    suffixStem = (
                                        suffixStem[0],
                                        suffixStem[1],
                                        suffixStem[2],
                                        suffixStem[0],
                                        suffixStem[1],
                                        xmlpost_rel.get("index")
                                        + "|"
                                        + xmlpost_rel.get("head")
                                        + "|"
                                        + xmlpost_rel.get("relation"),
                                    )
                        except:
                            pass
                    sents.append(word)
                if sent or relation:
                    results.append(sents)
                else:
                    results.extend(sents)
        return LazyMap(lambda x: x, results)

    # Ready-to-use browser opener

    """
    The base URL for viewing files on the childes website. This
    shouldn't need to be changed, unless CHILDES changes the configuration
    of their server or unless the user sets up their own corpus webserver.
    """
    childes_url_base = r"https://childes.talkbank.org/browser/index.php?url="

    def webview_file(self, fileid, urlbase=None):
        """Map a corpus file to its web version on the CHILDES website,
        and open it in a web browser.

        The complete URL to be used is:
            childes.childes_url_base + urlbase + fileid.replace('.xml', '.cha')

        If no urlbase is passed, we try to calculate it.  This
        requires that the childes corpus was set up to mirror the
        folder hierarchy under childes.psy.cmu.edu/data-xml/, e.g.:
        nltk_data/corpora/childes/Eng-USA/Cornell/??? or
        nltk_data/corpora/childes/Romance/Spanish/Aguirre/???

        The function first looks (as a special case) if "Eng-USA" is
        on the path consisting of <corpus root>+fileid; then if
        "childes", possibly followed by "data-xml", appears. If neither
        one is found, we use the unmodified fileid and hope for the best.
        If this is not right, specify urlbase explicitly, e.g., if the
        corpus root points to the Cornell folder, urlbase='Eng-USA/Cornell'.
        """

        import webbrowser

        if urlbase:
            path = urlbase + "/" + fileid
        else:
            full = self.root + "/" + fileid
            full = re.sub(r"\\", "/", full)
            if "/childes/" in full.lower():
                # Discard /data-xml/ if present
                path = re.findall(r"(?i)/childes(?:/data-xml)?/(.*)\.xml", full)[0]
            elif "eng-usa" in full.lower():
                path = "Eng-USA/" + re.findall(r"/(?i)Eng-USA/(.*)\.xml", full)[0]
            else:
                path = fileid

        # Strip ".xml" and add ".cha", as necessary:
        if path.endswith(".xml"):
            path = path[:-4]

        if not path.endswith(".cha"):
            path = path + ".cha"

        url = self.childes_url_base + path

        webbrowser.open_new_tab(url)
        print("Opening in browser:", url)
        # Pausing is a good idea, but it's up to the user...
        # raw_input("Hit Return to continue")


def demo(corpus_root=None):
    """
    The CHILDES corpus should be manually downloaded and saved
    to ``[NLTK_Data_Dir]/corpora/childes/``
    """
    if not corpus_root:
        from nltk.data import find

        corpus_root = find("corpora/childes/data-xml/Eng-USA/")

    try:
        childes = CHILDESCorpusReader(corpus_root, ".*.xml")
        # describe all corpus
        for file in childes.fileids()[:5]:
            corpus = ""
            corpus_id = ""
            for key, value in childes.corpus(file)[0].items():
                if key == "Corpus":
                    corpus = value
                if key == "Id":
                    corpus_id = value
            print("Reading", corpus, corpus_id, " .....")
            print("words:", childes.words(file)[:7], "...")
            print(
                "words with replaced words:",
                childes.words(file, replace=True)[:7],
                " ...",
            )
            print("words with pos tags:", childes.tagged_words(file)[:7], " ...")
            print("words (only MOT):", childes.words(file, speaker="MOT")[:7], "...")
            print("words (only CHI):", childes.words(file, speaker="CHI")[:7], "...")
            print("stemmed words:", childes.words(file, stem=True)[:7], " ...")
            print(
                "words with relations and pos-tag:",
                childes.words(file, relation=True)[:5],
                " ...",
            )
            print("sentence:", childes.sents(file)[:2], " ...")
            for participant, values in childes.participants(file)[0].items():
                for key, value in values.items():
                    print("\tparticipant", participant, key, ":", value)
            print("num of sent:", len(childes.sents(file)))
            print("num of morphemes:", len(childes.words(file, stem=True)))
            print("age:", childes.age(file))
            print("age in month:", childes.age(file, month=True))
            print("MLU:", childes.MLU(file))
            print()

    except LookupError as e:
        print(
            """The CHILDES corpus, or the parts you need, should be manually
        downloaded from https://childes.talkbank.org/data-xml/ and saved at
        [NLTK_Data_Dir]/corpora/childes/
            Alternately, you can call the demo with the path to a portion of the CHILDES corpus, e.g.:
        demo('/path/to/childes/data-xml/Eng-USA/")
        """
        )
        # corpus_root_http = urllib2.urlopen('https://childes.talkbank.org/data-xml/Eng-USA/Bates.zip')
        # corpus_root_http_bates = zipfile.ZipFile(cStringIO.StringIO(corpus_root_http.read()))
        ##this fails
        # childes = CHILDESCorpusReader(corpus_root_http_bates,corpus_root_http_bates.namelist())


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\file_service\async_client.py ===
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
from google.protobuf import timestamp_pb2  # type: ignore
from google.rpc import status_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.services.file_service import pagers
from google.ai.generativelanguage_v1beta.types import file, file_service

from .client import FileServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, FileServiceTransport
from .transports.grpc_asyncio import FileServiceGrpcAsyncIOTransport


class FileServiceAsyncClient:
    """An API for uploading and managing files."""

    _client: FileServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = FileServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = FileServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = FileServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = FileServiceClient._DEFAULT_UNIVERSE

    file_path = staticmethod(FileServiceClient.file_path)
    parse_file_path = staticmethod(FileServiceClient.parse_file_path)
    common_billing_account_path = staticmethod(
        FileServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        FileServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(FileServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(FileServiceClient.parse_common_folder_path)
    common_organization_path = staticmethod(FileServiceClient.common_organization_path)
    parse_common_organization_path = staticmethod(
        FileServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(FileServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        FileServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(FileServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        FileServiceClient.parse_common_location_path
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
            FileServiceAsyncClient: The constructed client.
        """
        return FileServiceClient.from_service_account_info.__func__(FileServiceAsyncClient, info, *args, **kwargs)  # type: ignore

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
            FileServiceAsyncClient: The constructed client.
        """
        return FileServiceClient.from_service_account_file.__func__(FileServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

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
        return FileServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> FileServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            FileServiceTransport: The transport used by the client instance.
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
        type(FileServiceClient).get_transport_class, type(FileServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, FileServiceTransport, Callable[..., FileServiceTransport]]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the file service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,FileServiceTransport,Callable[..., FileServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the FileServiceTransport constructor.
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
        self._client = FileServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def create_file(
        self,
        request: Optional[Union[file_service.CreateFileRequest, dict]] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> file_service.CreateFileResponse:
        r"""Creates a ``File``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_create_file():
                # Create a client
                client = generativelanguage_v1beta.FileServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.CreateFileRequest(
                )

                # Make the request
                response = await client.create_file(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.CreateFileRequest, dict]]):
                The request object. Request for ``CreateFile``.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.CreateFileResponse:
                Response for CreateFile.
        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, file_service.CreateFileRequest):
            request = file_service.CreateFileRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.create_file
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

    async def list_files(
        self,
        request: Optional[Union[file_service.ListFilesRequest, dict]] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListFilesAsyncPager:
        r"""Lists the metadata for ``File``\ s owned by the requesting
        project.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_list_files():
                # Create a client
                client = generativelanguage_v1beta.FileServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListFilesRequest(
                )

                # Make the request
                page_result = client.list_files(request=request)

                # Handle the response
                async for response in page_result:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.ListFilesRequest, dict]]):
                The request object. Request for ``ListFiles``.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.file_service.pagers.ListFilesAsyncPager:
                Response for ListFiles.

                Iterating over this object will yield results and
                resolve additional pages automatically.

        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, file_service.ListFilesRequest):
            request = file_service.ListFilesRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.list_files
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
        response = pagers.ListFilesAsyncPager(
            method=rpc,
            request=request,
            response=response,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def get_file(
        self,
        request: Optional[Union[file_service.GetFileRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> file.File:
        r"""Gets the metadata for the given ``File``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_get_file():
                # Create a client
                client = generativelanguage_v1beta.FileServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetFileRequest(
                    name="name_value",
                )

                # Make the request
                response = await client.get_file(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.GetFileRequest, dict]]):
                The request object. Request for ``GetFile``.
            name (:class:`str`):
                Required. The name of the ``File`` to get. Example:
                ``files/abc-123``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.File:
                A file uploaded to the API.
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
        if not isinstance(request, file_service.GetFileRequest):
            request = file_service.GetFileRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[self._client._transport.get_file]

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

    async def delete_file(
        self,
        request: Optional[Union[file_service.DeleteFileRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes the ``File``.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_delete_file():
                # Create a client
                client = generativelanguage_v1beta.FileServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.DeleteFileRequest(
                    name="name_value",
                )

                # Make the request
                await client.delete_file(request=request)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.DeleteFileRequest, dict]]):
                The request object. Request for ``DeleteFile``.
            name (:class:`str`):
                Required. The name of the ``File`` to delete. Example:
                ``files/abc-123``

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
        if not isinstance(request, file_service.DeleteFileRequest):
            request = file_service.DeleteFileRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.delete_file
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

    async def __aenter__(self) -> "FileServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("FileServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\guardrails\guardrail_hooks\bedrock_guardrails.py ===
# +-------------------------------------------------------------+
#
#           Use Bedrock Guardrails for your LLM calls
#
# +-------------------------------------------------------------+
#  Thank you users! We ❤️ you! - Krrish & Ishaan

import os
import sys

sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import json
import sys
from typing import Any, AsyncGenerator, List, Literal, Optional, Tuple, Union

from fastapi import HTTPException

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.caching import DualCache
from litellm.integrations.custom_guardrail import (
    CustomGuardrail,
    log_guardrail_information,
)
from litellm.llms.bedrock.base_aws_llm import BaseAWSLLM
from litellm.llms.custom_httpx.http_handler import (
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.proxy._types import UserAPIKeyAuth
from litellm.types.guardrails import GuardrailEventHooks
from litellm.types.llms.openai import AllMessageValues
from litellm.types.proxy.guardrails.guardrail_hooks.bedrock_guardrails import (
    BedrockContentItem,
    BedrockGuardrailOutput,
    BedrockGuardrailResponse,
    BedrockRequest,
    BedrockTextContent,
)
from litellm.types.utils import ModelResponse, ModelResponseStream

GUARDRAIL_NAME = "bedrock"


class BedrockGuardrail(CustomGuardrail, BaseAWSLLM):
    def __init__(
        self,
        guardrailIdentifier: Optional[str] = None,
        guardrailVersion: Optional[str] = None,
        **kwargs,
    ):
        self.async_handler = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.GuardrailCallback
        )
        self.guardrailIdentifier = guardrailIdentifier
        self.guardrailVersion = guardrailVersion

        # store kwargs as optional_params
        self.optional_params = kwargs

        super().__init__(**kwargs)
        BaseAWSLLM.__init__(self)

        verbose_proxy_logger.debug(
            "Bedrock Guardrail initialized with guardrailIdentifier: %s, guardrailVersion: %s",
            self.guardrailIdentifier,
            self.guardrailVersion,
        )

    def convert_to_bedrock_format(
        self,
        messages: Optional[List[AllMessageValues]] = None,
        response: Optional[Union[Any, ModelResponse]] = None,
    ) -> BedrockRequest:
        bedrock_request: BedrockRequest = BedrockRequest(source="INPUT")
        bedrock_request_content: List[BedrockContentItem] = []

        if messages:
            for message in messages:
                message_text_content: Optional[
                    List[str]
                ] = self.get_content_for_message(message=message)
                if message_text_content is None:
                    continue
                for text_content in message_text_content:
                    bedrock_content_item = BedrockContentItem(
                        text=BedrockTextContent(text=text_content)
                    )
                    bedrock_request_content.append(bedrock_content_item)

            bedrock_request["content"] = bedrock_request_content
        if response:
            bedrock_request["source"] = "OUTPUT"
            if isinstance(response, litellm.ModelResponse):
                for choice in response.choices:
                    if isinstance(choice, litellm.Choices):
                        if choice.message.content and isinstance(
                            choice.message.content, str
                        ):
                            bedrock_content_item = BedrockContentItem(
                                text=BedrockTextContent(text=choice.message.content)
                            )
                            bedrock_request_content.append(bedrock_content_item)
                bedrock_request["content"] = bedrock_request_content
        return bedrock_request

    #### CALL HOOKS - proxy only ####
    def _load_credentials(
        self,
    ):
        try:
            from botocore.credentials import Credentials
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")
        ## CREDENTIALS ##
        aws_secret_access_key = self.optional_params.get("aws_secret_access_key", None)
        aws_access_key_id = self.optional_params.get("aws_access_key_id", None)
        aws_session_token = self.optional_params.get("aws_session_token", None)
        aws_region_name = self.optional_params.get("aws_region_name", None)
        aws_role_name = self.optional_params.get("aws_role_name", None)
        aws_session_name = self.optional_params.get("aws_session_name", None)
        aws_profile_name = self.optional_params.get("aws_profile_name", None)
        aws_web_identity_token = self.optional_params.get(
            "aws_web_identity_token", None
        )
        aws_sts_endpoint = self.optional_params.get("aws_sts_endpoint", None)

        ### SET REGION NAME ###
        aws_region_name = self.get_aws_region_name_for_non_llm_api_calls(
            aws_region_name=aws_region_name,
        )

        credentials: Credentials = self.get_credentials(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            aws_region_name=aws_region_name,
            aws_session_name=aws_session_name,
            aws_profile_name=aws_profile_name,
            aws_role_name=aws_role_name,
            aws_web_identity_token=aws_web_identity_token,
            aws_sts_endpoint=aws_sts_endpoint,
        )
        return credentials, aws_region_name

    def _prepare_request(
        self,
        credentials,
        data: dict,
        optional_params: dict,
        aws_region_name: str,
        extra_headers: Optional[dict] = None,
    ):
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
        except ImportError:
            raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")

        sigv4 = SigV4Auth(credentials, "bedrock", aws_region_name)
        api_base = f"https://bedrock-runtime.{aws_region_name}.amazonaws.com/guardrail/{self.guardrailIdentifier}/version/{self.guardrailVersion}/apply"

        encoded_data = json.dumps(data).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if extra_headers is not None:
            headers = {"Content-Type": "application/json", **extra_headers}

        request = AWSRequest(
            method="POST", url=api_base, data=encoded_data, headers=headers
        )
        sigv4.add_auth(request)
        if (
            extra_headers is not None and "Authorization" in extra_headers
        ):  # prevent sigv4 from overwriting the auth header
            request.headers["Authorization"] = extra_headers["Authorization"]

        prepped_request = request.prepare()

        return prepped_request

    async def make_bedrock_api_request(
        self, kwargs: dict, response: Optional[Union[Any, litellm.ModelResponse]] = None
    ) -> BedrockGuardrailResponse:
        credentials, aws_region_name = self._load_credentials()
        bedrock_request_data: dict = dict(
            self.convert_to_bedrock_format(
                messages=kwargs.get("messages"), response=response
            )
        )
        bedrock_guardrail_response: BedrockGuardrailResponse = (
            BedrockGuardrailResponse()
        )
        bedrock_request_data.update(
            self.get_guardrail_dynamic_request_body_params(request_data=kwargs)
        )
        prepared_request = self._prepare_request(
            credentials=credentials,
            data=bedrock_request_data,
            optional_params=self.optional_params,
            aws_region_name=aws_region_name,
        )
        verbose_proxy_logger.debug(
            "Bedrock AI request body: %s, url %s, headers: %s",
            bedrock_request_data,
            prepared_request.url,
            prepared_request.headers,
        )

        response = await self.async_handler.post(
            url=prepared_request.url,
            data=prepared_request.body,  # type: ignore
            headers=prepared_request.headers,  # type: ignore
        )
        verbose_proxy_logger.debug("Bedrock AI response: %s", response.text)
        if response.status_code == 200:
            # check if the response was flagged
            _json_response = response.json()
            bedrock_guardrail_response = BedrockGuardrailResponse(**_json_response)
            if self._should_raise_guardrail_blocked_exception(
                bedrock_guardrail_response
            ):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Violated guardrail policy",
                        "bedrock_guardrail_response": _json_response,
                    },
                )
        else:
            verbose_proxy_logger.error(
                "Bedrock AI: error in response. Status code: %s, response: %s",
                response.status_code,
                response.text,
            )

        return bedrock_guardrail_response

    def _should_raise_guardrail_blocked_exception(
        self, response: BedrockGuardrailResponse
    ) -> bool:
        """
        By default always raise an exception when a guardrail intervention is detected.

        If `self.mask_request_content` or `self.mask_response_content` is set to `True`, then use the output from the guardrail to mask the request or response content.
        """

        # if user opted into masking, return False. since we'll use the masked output from the guardrail
        if self.mask_request_content or self.mask_response_content:
            return False

        # if intervention, return True
        if response.get("action") == "GUARDRAIL_INTERVENED":
            return True

        # if no intervention, return False
        return False

    @log_guardrail_information
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
    ) -> Union[Exception, str, dict, None]:
        verbose_proxy_logger.debug("Inside AIM Pre-Call Hook")

        from litellm.proxy.common_utils.callback_utils import (
            add_guardrail_to_applied_guardrails_header,
        )

        event_type: GuardrailEventHooks = GuardrailEventHooks.pre_call
        if self.should_run_guardrail(data=data, event_type=event_type) is not True:
            return data

        new_messages: Optional[List[AllMessageValues]] = data.get("messages")
        if new_messages is None:
            verbose_proxy_logger.warning(
                "Bedrock AI: not running guardrail. No messages in data"
            )
            return data

        #########################################################
        ########## 1. Make the Bedrock API request ##########
        #########################################################
        bedrock_guardrail_response = await self.make_bedrock_api_request(kwargs=data)
        #########################################################

        #########################################################
        ########## 2. Update the messages with the guardrail response ##########
        #########################################################
        data[
            "messages"
        ] = self._update_messages_with_updated_bedrock_guardrail_response(
            messages=new_messages,
            bedrock_guardrail_response=bedrock_guardrail_response,
        )

        #########################################################
        ########## 3. Add the guardrail to the applied guardrails header ##########
        #########################################################
        add_guardrail_to_applied_guardrails_header(
            request_data=data, guardrail_name=self.guardrail_name
        )

        return data

    @log_guardrail_information
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
    ):
        from litellm.proxy.common_utils.callback_utils import (
            add_guardrail_to_applied_guardrails_header,
        )

        event_type: GuardrailEventHooks = GuardrailEventHooks.during_call
        if self.should_run_guardrail(data=data, event_type=event_type) is not True:
            return

        new_messages: Optional[List[AllMessageValues]] = data.get("messages")
        if new_messages is None:
            verbose_proxy_logger.warning(
                "Bedrock AI: not running guardrail. No messages in data"
            )
            return

        #########################################################
        ########## 1. Make the Bedrock API request ##########
        #########################################################
        bedrock_guardrail_response = await self.make_bedrock_api_request(kwargs=data)
        #########################################################

        #########################################################
        ########## 2. Update the messages with the guardrail response ##########
        #########################################################
        data[
            "messages"
        ] = self._update_messages_with_updated_bedrock_guardrail_response(
            messages=new_messages,
            bedrock_guardrail_response=bedrock_guardrail_response,
        )

        #########################################################
        ########## 3. Add the guardrail to the applied guardrails header ##########
        #########################################################
        add_guardrail_to_applied_guardrails_header(
            request_data=data, guardrail_name=self.guardrail_name
        )

        return data

    @log_guardrail_information
    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        response,
    ):
        from litellm.proxy.common_utils.callback_utils import (
            add_guardrail_to_applied_guardrails_header,
        )
        from litellm.types.guardrails import GuardrailEventHooks

        if (
            self.should_run_guardrail(
                data=data, event_type=GuardrailEventHooks.post_call
            )
            is not True
        ):
            return

        new_messages: Optional[List[AllMessageValues]] = data.get("messages")
        if new_messages is None:
            verbose_proxy_logger.warning(
                "Bedrock AI: not running guardrail. No messages in data"
            )
            return

        #########################################################
        ########## 1. Make the Bedrock API request ##########
        #########################################################
        bedrock_guardrail_response = await self.make_bedrock_api_request(
            kwargs=data, response=response
        )
        #########################################################

        #########################################################
        ########## 2. Update the messages with the guardrail response ##########
        #########################################################
        data[
            "messages"
        ] = self._update_messages_with_updated_bedrock_guardrail_response(
            messages=new_messages,
            bedrock_guardrail_response=bedrock_guardrail_response,
        )

        #########################################################
        ########## 3. Add the guardrail to the applied guardrails header ##########
        #########################################################
        add_guardrail_to_applied_guardrails_header(
            request_data=data, guardrail_name=self.guardrail_name
        )

    ###########  HELPER FUNCTIONS for bedrock guardrails ############################
    ##############################################################################
    ##############################################################################
    def _update_messages_with_updated_bedrock_guardrail_response(
        self,
        messages: List[AllMessageValues],
        bedrock_guardrail_response: BedrockGuardrailResponse,
    ) -> List[AllMessageValues]:
        """
        Use the output from the bedrock guardrail to mask sensitive content in messages.

        Args:
            messages: Original list of messages
            bedrock_guardrail_response: Response from Bedrock guardrail containing masked content

        Returns:
            List of messages with content masked according to guardrail response
        """
        # Skip processing if masking is not enabled
        if not (self.mask_request_content or self.mask_response_content):
            return messages

        # Get masked texts from guardrail response
        masked_texts = self._extract_masked_texts_from_response(
            bedrock_guardrail_response
        )
        if not masked_texts:
            return messages

        # Apply masking to messages using index tracking
        return self._apply_masking_to_messages(
            messages=messages, masked_texts=masked_texts
        )

    async def async_post_call_streaming_iterator_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        response: Any,
        request_data: dict,
    ) -> AsyncGenerator[ModelResponseStream, None]:
        """
        Process streaming response chunks.

        Collect content from the stream and make a bedrock api request to get the guardrail response.
        """
        # Import here to avoid circular imports
        from litellm.llms.base_llm.base_model_iterator import MockResponseIterator
        from litellm.main import stream_chunk_builder
        from litellm.types.utils import TextCompletionResponse

        # Collect all chunks to process them together
        all_chunks: List[ModelResponseStream] = []
        async for chunk in response:
            all_chunks.append(chunk)

        assembled_model_response: Optional[
            Union[ModelResponse, TextCompletionResponse]
        ] = stream_chunk_builder(
            chunks=all_chunks,
        )
        if isinstance(assembled_model_response, ModelResponse):
            ####################################################################
            ########## 1. Make the Bedrock Apply Guardrail API request ##########

            # Bedrock will raise an exception if this violates the guardrail policy
            ###################################################################
            await self.make_bedrock_api_request(
                kwargs=request_data, response=assembled_model_response
            )

            #########################################################################
            ########## If guardrail passed, then return the collected chunks ##########
            #########################################################################
            mock_response = MockResponseIterator(
                model_response=assembled_model_response
            )

            # Return the reconstructed stream
            async for chunk in mock_response:
                yield chunk
        else:
            for chunk in all_chunks:
                yield chunk

    def _extract_masked_texts_from_response(
        self, bedrock_guardrail_response: BedrockGuardrailResponse
    ) -> List[str]:
        """
        Extract all masked text outputs from the guardrail response.

        Args:
            bedrock_guardrail_response: Response from Bedrock guardrail

        Returns:
            List of masked text strings
        """
        masked_output_text: List[str] = []
        masked_outputs: Optional[List[BedrockGuardrailOutput]] = (
            bedrock_guardrail_response.get("outputs", []) or []
        )
        if not masked_outputs:
            verbose_proxy_logger.debug("No masked outputs found in guardrail response")
            return []

        for output in masked_outputs:
            text_content: Optional[str] = output.get("text")
            if text_content is not None:
                masked_output_text.append(text_content)

        return masked_output_text

    def _apply_masking_to_messages(
        self, messages: List[AllMessageValues], masked_texts: List[str]
    ) -> List[AllMessageValues]:
        """
        Apply masked texts to message content using index tracking.

        Args:
            messages: Original messages
            masked_texts: List of masked text strings from guardrail

        Returns:
            Updated messages with masked content
        """
        updated_messages = []
        masking_index = 0

        for message in messages:
            new_message = message.copy()
            content = new_message.get("content")

            # Skip messages with no content
            if content is None:
                updated_messages.append(new_message)
                continue

            # Handle string content
            if isinstance(content, str):
                if masking_index < len(masked_texts):
                    new_message["content"] = masked_texts[masking_index]
                    masking_index += 1
            # Handle list content
            elif isinstance(content, list):
                new_message["content"], masking_index = self._mask_content_list(
                    content_list=content,
                    masked_texts=masked_texts,
                    masking_index=masking_index,
                )

            updated_messages.append(new_message)

        return updated_messages

    def _mask_content_list(
        self, content_list: List[Any], masked_texts: List[str], masking_index: int
    ) -> Tuple[List[Any], int]:
        """
        Apply masking to a list of content items.

        Args:
            content_list: List of content items
            masked_texts: List of masked text strings
            starting_index: Starting index in the masked_texts list

        Returns:
            Updated content list with masked items
        """
        new_content: List[Union[dict, str]] = []
        for item in content_list:
            if isinstance(item, dict) and "text" in item:
                new_item = item.copy()
                if masking_index < len(masked_texts):
                    new_item["text"] = masked_texts[masking_index]
                    masking_index += 1
                new_content.append(new_item)
            elif isinstance(item, str):
                if masking_index < len(masked_texts):
                    item = masked_texts[masking_index]
                    masking_index += 1
                if item is not None:
                    new_content.append(item)

        return new_content, masking_index

    def get_content_for_message(self, message: AllMessageValues) -> Optional[List[str]]:
        """
        Get the content for a message.

        For bedrock guardrails we create a list of all the text content in the message.

        If a message has a list of content items, we flatten the list and return a list of text content.
        """
        message_text_content = []
        content = message.get("content")
        if content is None:
            return None
        if isinstance(content, str):
            message_text_content.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    message_text_content.append(item["text"])
                elif isinstance(item, str):
                    message_text_content.append(item)
        return message_text_content