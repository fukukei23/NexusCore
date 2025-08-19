
# === NexusCore/openenv\Lib\site-packages\anthropic\resources\messages.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import warnings
from typing import List, Union, Iterable
from functools import partial
from typing_extensions import Literal, overload

import httpx

from .. import _legacy_response
from ..types import message_create_params
from .._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from .._utils import (
    is_given,
    required_args,
    maybe_transform,
    async_maybe_transform,
)
from .._compat import cached_property
from .._resource import SyncAPIResource, AsyncAPIResource
from .._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from .._constants import DEFAULT_TIMEOUT
from .._streaming import Stream, AsyncStream
from .._base_client import make_request_options
from ..lib.streaming import MessageStreamManager, AsyncMessageStreamManager
from ..types.message import Message
from ..types.tool_param import ToolParam
from ..types.model_param import ModelParam
from ..types.message_param import MessageParam
from ..types.metadata_param import MetadataParam
from ..types.text_block_param import TextBlockParam
from ..types.tool_choice_param import ToolChoiceParam
from ..types.raw_message_stream_event import RawMessageStreamEvent

__all__ = ["Messages", "AsyncMessages"]


DEPRECATED_MODELS = {
    "claude-1.3": "November 6th, 2024",
    "claude-1.3-100k": "November 6th, 2024",
    "claude-instant-1.1": "November 6th, 2024",
    "claude-instant-1.1-100k": "November 6th, 2024",
    "claude-instant-1.2": "November 6th, 2024",
}


class Messages(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> MessagesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#accessing-raw-response-data-eg-headers
        """
        return MessagesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> MessagesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#with_streaming_response
        """
        return MessagesWithStreamingResponse(self)

    @overload
    def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[TextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Message:
        """
        Send a structured list of input messages with text and/or image content, and the
        model will generate the next message in the conversation.

        The Messages API can be used for either single queries or stateless multi-turn
        conversations.

        Args:
          max_tokens: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

              Different models have different maximum values for this parameter. See
              [models](https://docs.anthropic.com/en/docs/models-overview) for details.

          messages: Input messages.

              Our models are trained to operate on alternating `user` and `assistant`
              conversational turns. When creating a new `Message`, you specify the prior
              conversational turns with the `messages` parameter, and the model then generates
              the next `Message` in the conversation. Consecutive `user` or `assistant` turns
              in your request will be combined into a single turn.

              Each input message must be an object with a `role` and `content`. You can
              specify a single `user`-role message, or you can include multiple `user` and
              `assistant` messages.

              If the final message uses the `assistant` role, the response content will
              continue immediately from the content in that message. This can be used to
              constrain part of the model's response.

              Example with a single `user` message:

              ```json
              [{ "role": "user", "content": "Hello, Claude" }]
              ```

              Example with multiple conversational turns:

              ```json
              [
                { "role": "user", "content": "Hello there." },
                { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
                { "role": "user", "content": "Can you explain LLMs in plain English?" }
              ]
              ```

              Example with a partially-filled response from Claude:

              ```json
              [
                {
                  "role": "user",
                  "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
                },
                { "role": "assistant", "content": "The best answer is (" }
              ]
              ```

              Each input message `content` may be either a single `string` or an array of
              content blocks, where each block has a specific `type`. Using a `string` for
              `content` is shorthand for an array of one content block of type `"text"`. The
              following input messages are equivalent:

              ```json
              { "role": "user", "content": "Hello, Claude" }
              ```

              ```json
              { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
              ```

              Starting with Claude 3 models, you can also send image content blocks:

              ```json
              {
                "role": "user",
                "content": [
                  {
                    "type": "image",
                    "source": {
                      "type": "base64",
                      "media_type": "image/jpeg",
                      "data": "/9j/4AAQSkZJRg..."
                    }
                  },
                  { "type": "text", "text": "What is in this image?" }
                ]
              }
              ```

              We currently support the `base64` source type for images, and the `image/jpeg`,
              `image/png`, `image/gif`, and `image/webp` media types.

              See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
              more input examples.

              Note that if you want to include a
              [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
              the top-level `system` parameter — there is no `"system"` role for input
              messages in the Messages API.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          metadata: An object describing metadata about the request.

          stop_sequences: Custom text sequences that will cause the model to stop generating.

              Our models will normally stop when they have naturally completed their turn,
              which will result in a response `stop_reason` of `"end_turn"`.

              If you want the model to stop generating when it encounters custom strings of
              text, you can use the `stop_sequences` parameter. If the model encounters one of
              the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
              and the response `stop_sequence` value will contain the matched stop sequence.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
              details.

          system: System prompt.

              A system prompt is a way of providing context and instructions to Claude, such
              as specifying a particular goal or role. See our
              [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          tool_choice: How the model should use the provided tools. The model can use a specific tool,
              any available tool, or decide by itself.

          tools: Definitions of tools that the model may use.

              If you include `tools` in your API request, the model may return `tool_use`
              content blocks that represent the model's use of those tools. You can then run
              those tools using the tool input generated by the model and then optionally
              return results back to the model using `tool_result` content blocks.

              Each tool definition includes:

              - `name`: Name of the tool.
              - `description`: Optional, but strongly-recommended description of the tool.
              - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
                shape that the model will produce in `tool_use` output content blocks.

              For example, if you defined `tools` as:

              ```json
              [
                {
                  "name": "get_stock_price",
                  "description": "Get the current stock price for a given ticker symbol.",
                  "input_schema": {
                    "type": "object",
                    "properties": {
                      "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
                      }
                    },
                    "required": ["ticker"]
                  }
                }
              ]
              ```

              And then asked the model "What's the S&P 500 at today?", the model might produce
              `tool_use` content blocks in the response like this:

              ```json
              [
                {
                  "type": "tool_use",
                  "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "name": "get_stock_price",
                  "input": { "ticker": "^GSPC" }
                }
              ]
              ```

              You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
              input, and return the following back to the model in a subsequent `user`
              message:

              ```json
              [
                {
                  "type": "tool_result",
                  "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "content": "259.75 USD"
                }
              ]
              ```

              Tools can be used for workflows that include running client-side tools and
              functions, or more generally whenever you want the model to produce a particular
              JSON structure of output.

              See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        stream: Literal[True],
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[TextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Stream[RawMessageStreamEvent]:
        """
        Send a structured list of input messages with text and/or image content, and the
        model will generate the next message in the conversation.

        The Messages API can be used for either single queries or stateless multi-turn
        conversations.

        Args:
          max_tokens: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

              Different models have different maximum values for this parameter. See
              [models](https://docs.anthropic.com/en/docs/models-overview) for details.

          messages: Input messages.

              Our models are trained to operate on alternating `user` and `assistant`
              conversational turns. When creating a new `Message`, you specify the prior
              conversational turns with the `messages` parameter, and the model then generates
              the next `Message` in the conversation. Consecutive `user` or `assistant` turns
              in your request will be combined into a single turn.

              Each input message must be an object with a `role` and `content`. You can
              specify a single `user`-role message, or you can include multiple `user` and
              `assistant` messages.

              If the final message uses the `assistant` role, the response content will
              continue immediately from the content in that message. This can be used to
              constrain part of the model's response.

              Example with a single `user` message:

              ```json
              [{ "role": "user", "content": "Hello, Claude" }]
              ```

              Example with multiple conversational turns:

              ```json
              [
                { "role": "user", "content": "Hello there." },
                { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
                { "role": "user", "content": "Can you explain LLMs in plain English?" }
              ]
              ```

              Example with a partially-filled response from Claude:

              ```json
              [
                {
                  "role": "user",
                  "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
                },
                { "role": "assistant", "content": "The best answer is (" }
              ]
              ```

              Each input message `content` may be either a single `string` or an array of
              content blocks, where each block has a specific `type`. Using a `string` for
              `content` is shorthand for an array of one content block of type `"text"`. The
              following input messages are equivalent:

              ```json
              { "role": "user", "content": "Hello, Claude" }
              ```

              ```json
              { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
              ```

              Starting with Claude 3 models, you can also send image content blocks:

              ```json
              {
                "role": "user",
                "content": [
                  {
                    "type": "image",
                    "source": {
                      "type": "base64",
                      "media_type": "image/jpeg",
                      "data": "/9j/4AAQSkZJRg..."
                    }
                  },
                  { "type": "text", "text": "What is in this image?" }
                ]
              }
              ```

              We currently support the `base64` source type for images, and the `image/jpeg`,
              `image/png`, `image/gif`, and `image/webp` media types.

              See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
              more input examples.

              Note that if you want to include a
              [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
              the top-level `system` parameter — there is no `"system"` role for input
              messages in the Messages API.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
              details.

          metadata: An object describing metadata about the request.

          stop_sequences: Custom text sequences that will cause the model to stop generating.

              Our models will normally stop when they have naturally completed their turn,
              which will result in a response `stop_reason` of `"end_turn"`.

              If you want the model to stop generating when it encounters custom strings of
              text, you can use the `stop_sequences` parameter. If the model encounters one of
              the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
              and the response `stop_sequence` value will contain the matched stop sequence.

          system: System prompt.

              A system prompt is a way of providing context and instructions to Claude, such
              as specifying a particular goal or role. See our
              [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          tool_choice: How the model should use the provided tools. The model can use a specific tool,
              any available tool, or decide by itself.

          tools: Definitions of tools that the model may use.

              If you include `tools` in your API request, the model may return `tool_use`
              content blocks that represent the model's use of those tools. You can then run
              those tools using the tool input generated by the model and then optionally
              return results back to the model using `tool_result` content blocks.

              Each tool definition includes:

              - `name`: Name of the tool.
              - `description`: Optional, but strongly-recommended description of the tool.
              - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
                shape that the model will produce in `tool_use` output content blocks.

              For example, if you defined `tools` as:

              ```json
              [
                {
                  "name": "get_stock_price",
                  "description": "Get the current stock price for a given ticker symbol.",
                  "input_schema": {
                    "type": "object",
                    "properties": {
                      "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
                      }
                    },
                    "required": ["ticker"]
                  }
                }
              ]
              ```

              And then asked the model "What's the S&P 500 at today?", the model might produce
              `tool_use` content blocks in the response like this:

              ```json
              [
                {
                  "type": "tool_use",
                  "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "name": "get_stock_price",
                  "input": { "ticker": "^GSPC" }
                }
              ]
              ```

              You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
              input, and return the following back to the model in a subsequent `user`
              message:

              ```json
              [
                {
                  "type": "tool_result",
                  "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "content": "259.75 USD"
                }
              ]
              ```

              Tools can be used for workflows that include running client-side tools and
              functions, or more generally whenever you want the model to produce a particular
              JSON structure of output.

              See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        stream: bool,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[TextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Message | Stream[RawMessageStreamEvent]:
        """
        Send a structured list of input messages with text and/or image content, and the
        model will generate the next message in the conversation.

        The Messages API can be used for either single queries or stateless multi-turn
        conversations.

        Args:
          max_tokens: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

              Different models have different maximum values for this parameter. See
              [models](https://docs.anthropic.com/en/docs/models-overview) for details.

          messages: Input messages.

              Our models are trained to operate on alternating `user` and `assistant`
              conversational turns. When creating a new `Message`, you specify the prior
              conversational turns with the `messages` parameter, and the model then generates
              the next `Message` in the conversation. Consecutive `user` or `assistant` turns
              in your request will be combined into a single turn.

              Each input message must be an object with a `role` and `content`. You can
              specify a single `user`-role message, or you can include multiple `user` and
              `assistant` messages.

              If the final message uses the `assistant` role, the response content will
              continue immediately from the content in that message. This can be used to
              constrain part of the model's response.

              Example with a single `user` message:

              ```json
              [{ "role": "user", "content": "Hello, Claude" }]
              ```

              Example with multiple conversational turns:

              ```json
              [
                { "role": "user", "content": "Hello there." },
                { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
                { "role": "user", "content": "Can you explain LLMs in plain English?" }
              ]
              ```

              Example with a partially-filled response from Claude:

              ```json
              [
                {
                  "role": "user",
                  "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
                },
                { "role": "assistant", "content": "The best answer is (" }
              ]
              ```

              Each input message `content` may be either a single `string` or an array of
              content blocks, where each block has a specific `type`. Using a `string` for
              `content` is shorthand for an array of one content block of type `"text"`. The
              following input messages are equivalent:

              ```json
              { "role": "user", "content": "Hello, Claude" }
              ```

              ```json
              { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
              ```

              Starting with Claude 3 models, you can also send image content blocks:

              ```json
              {
                "role": "user",
                "content": [
                  {
                    "type": "image",
                    "source": {
                      "type": "base64",
                      "media_type": "image/jpeg",
                      "data": "/9j/4AAQSkZJRg..."
                    }
                  },
                  { "type": "text", "text": "What is in this image?" }
                ]
              }
              ```

              We currently support the `base64` source type for images, and the `image/jpeg`,
              `image/png`, `image/gif`, and `image/webp` media types.

              See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
              more input examples.

              Note that if you want to include a
              [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
              the top-level `system` parameter — there is no `"system"` role for input
              messages in the Messages API.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
              details.

          metadata: An object describing metadata about the request.

          stop_sequences: Custom text sequences that will cause the model to stop generating.

              Our models will normally stop when they have naturally completed their turn,
              which will result in a response `stop_reason` of `"end_turn"`.

              If you want the model to stop generating when it encounters custom strings of
              text, you can use the `stop_sequences` parameter. If the model encounters one of
              the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
              and the response `stop_sequence` value will contain the matched stop sequence.

          system: System prompt.

              A system prompt is a way of providing context and instructions to Claude, such
              as specifying a particular goal or role. See our
              [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          tool_choice: How the model should use the provided tools. The model can use a specific tool,
              any available tool, or decide by itself.

          tools: Definitions of tools that the model may use.

              If you include `tools` in your API request, the model may return `tool_use`
              content blocks that represent the model's use of those tools. You can then run
              those tools using the tool input generated by the model and then optionally
              return results back to the model using `tool_result` content blocks.

              Each tool definition includes:

              - `name`: Name of the tool.
              - `description`: Optional, but strongly-recommended description of the tool.
              - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
                shape that the model will produce in `tool_use` output content blocks.

              For example, if you defined `tools` as:

              ```json
              [
                {
                  "name": "get_stock_price",
                  "description": "Get the current stock price for a given ticker symbol.",
                  "input_schema": {
                    "type": "object",
                    "properties": {
                      "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
                      }
                    },
                    "required": ["ticker"]
                  }
                }
              ]
              ```

              And then asked the model "What's the S&P 500 at today?", the model might produce
              `tool_use` content blocks in the response like this:

              ```json
              [
                {
                  "type": "tool_use",
                  "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "name": "get_stock_price",
                  "input": { "ticker": "^GSPC" }
                }
              ]
              ```

              You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
              input, and return the following back to the model in a subsequent `user`
              message:

              ```json
              [
                {
                  "type": "tool_result",
                  "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "content": "259.75 USD"
                }
              ]
              ```

              Tools can be used for workflows that include running client-side tools and
              functions, or more generally whenever you want the model to produce a particular
              JSON structure of output.

              See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @required_args(["max_tokens", "messages", "model"], ["max_tokens", "messages", "model", "stream"])
    def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | Literal[True] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[TextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Message | Stream[RawMessageStreamEvent]:
        if not is_given(timeout) and self._client.timeout == DEFAULT_TIMEOUT:
            timeout = 600

        if model in DEPRECATED_MODELS:
            warnings.warn(
                f"The model '{model}' is deprecated and will reach end-of-life on {DEPRECATED_MODELS[model]}.\nPlease migrate to a newer model. Visit https://docs.anthropic.com/en/docs/resources/model-deprecations for more information.",
                DeprecationWarning,
                stacklevel=3,
            )

        return self._post(
            "/v1/messages",
            body=maybe_transform(
                {
                    "max_tokens": max_tokens,
                    "messages": messages,
                    "model": model,
                    "metadata": metadata,
                    "stop_sequences": stop_sequences,
                    "stream": stream,
                    "system": system,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_k": top_k,
                    "top_p": top_p,
                },
                message_create_params.MessageCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Message,
            stream=stream or False,
            stream_cls=Stream[RawMessageStreamEvent],
        )

    def stream(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[TextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> MessageStreamManager:
        """Create a Message stream"""
        if model in DEPRECATED_MODELS:
            warnings.warn(
                f"The model '{model}' is deprecated and will reach end-of-life on {DEPRECATED_MODELS[model]}.\nPlease migrate to a newer model. Visit https://docs.anthropic.com/en/docs/resources/model-deprecations for more information.",
                DeprecationWarning,
                stacklevel=3,
            )

        extra_headers = {
            "X-Stainless-Stream-Helper": "messages",
            **(extra_headers or {}),
        }
        make_request = partial(
            self._post,
            "/v1/messages",
            body=maybe_transform(
                {
                    "max_tokens": max_tokens,
                    "messages": messages,
                    "model": model,
                    "metadata": metadata,
                    "stop_sequences": stop_sequences,
                    "system": system,
                    "temperature": temperature,
                    "top_k": top_k,
                    "top_p": top_p,
                    "tools": tools,
                    "tool_choice": tool_choice,
                    "stream": True,
                },
                message_create_params.MessageCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Message,
            stream=True,
            stream_cls=Stream[RawMessageStreamEvent],
        )
        return MessageStreamManager(make_request)


class AsyncMessages(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncMessagesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#accessing-raw-response-data-eg-headers
        """
        return AsyncMessagesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncMessagesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#with_streaming_response
        """
        return AsyncMessagesWithStreamingResponse(self)

    @overload
    async def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[TextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Message:
        """
        Send a structured list of input messages with text and/or image content, and the
        model will generate the next message in the conversation.

        The Messages API can be used for either single queries or stateless multi-turn
        conversations.

        Args:
          max_tokens: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

              Different models have different maximum values for this parameter. See
              [models](https://docs.anthropic.com/en/docs/models-overview) for details.

          messages: Input messages.

              Our models are trained to operate on alternating `user` and `assistant`
              conversational turns. When creating a new `Message`, you specify the prior
              conversational turns with the `messages` parameter, and the model then generates
              the next `Message` in the conversation. Consecutive `user` or `assistant` turns
              in your request will be combined into a single turn.

              Each input message must be an object with a `role` and `content`. You can
              specify a single `user`-role message, or you can include multiple `user` and
              `assistant` messages.

              If the final message uses the `assistant` role, the response content will
              continue immediately from the content in that message. This can be used to
              constrain part of the model's response.

              Example with a single `user` message:

              ```json
              [{ "role": "user", "content": "Hello, Claude" }]
              ```

              Example with multiple conversational turns:

              ```json
              [
                { "role": "user", "content": "Hello there." },
                { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
                { "role": "user", "content": "Can you explain LLMs in plain English?" }
              ]
              ```

              Example with a partially-filled response from Claude:

              ```json
              [
                {
                  "role": "user",
                  "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
                },
                { "role": "assistant", "content": "The best answer is (" }
              ]
              ```

              Each input message `content` may be either a single `string` or an array of
              content blocks, where each block has a specific `type`. Using a `string` for
              `content` is shorthand for an array of one content block of type `"text"`. The
              following input messages are equivalent:

              ```json
              { "role": "user", "content": "Hello, Claude" }
              ```

              ```json
              { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
              ```

              Starting with Claude 3 models, you can also send image content blocks:

              ```json
              {
                "role": "user",
                "content": [
                  {
                    "type": "image",
                    "source": {
                      "type": "base64",
                      "media_type": "image/jpeg",
                      "data": "/9j/4AAQSkZJRg..."
                    }
                  },
                  { "type": "text", "text": "What is in this image?" }
                ]
              }
              ```

              We currently support the `base64` source type for images, and the `image/jpeg`,
              `image/png`, `image/gif`, and `image/webp` media types.

              See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
              more input examples.

              Note that if you want to include a
              [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
              the top-level `system` parameter — there is no `"system"` role for input
              messages in the Messages API.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          metadata: An object describing metadata about the request.

          stop_sequences: Custom text sequences that will cause the model to stop generating.

              Our models will normally stop when they have naturally completed their turn,
              which will result in a response `stop_reason` of `"end_turn"`.

              If you want the model to stop generating when it encounters custom strings of
              text, you can use the `stop_sequences` parameter. If the model encounters one of
              the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
              and the response `stop_sequence` value will contain the matched stop sequence.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
              details.

          system: System prompt.

              A system prompt is a way of providing context and instructions to Claude, such
              as specifying a particular goal or role. See our
              [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          tool_choice: How the model should use the provided tools. The model can use a specific tool,
              any available tool, or decide by itself.

          tools: Definitions of tools that the model may use.

              If you include `tools` in your API request, the model may return `tool_use`
              content blocks that represent the model's use of those tools. You can then run
              those tools using the tool input generated by the model and then optionally
              return results back to the model using `tool_result` content blocks.

              Each tool definition includes:

              - `name`: Name of the tool.
              - `description`: Optional, but strongly-recommended description of the tool.
              - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
                shape that the model will produce in `tool_use` output content blocks.

              For example, if you defined `tools` as:

              ```json
              [
                {
                  "name": "get_stock_price",
                  "description": "Get the current stock price for a given ticker symbol.",
                  "input_schema": {
                    "type": "object",
                    "properties": {
                      "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
                      }
                    },
                    "required": ["ticker"]
                  }
                }
              ]
              ```

              And then asked the model "What's the S&P 500 at today?", the model might produce
              `tool_use` content blocks in the response like this:

              ```json
              [
                {
                  "type": "tool_use",
                  "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "name": "get_stock_price",
                  "input": { "ticker": "^GSPC" }
                }
              ]
              ```

              You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
              input, and return the following back to the model in a subsequent `user`
              message:

              ```json
              [
                {
                  "type": "tool_result",
                  "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "content": "259.75 USD"
                }
              ]
              ```

              Tools can be used for workflows that include running client-side tools and
              functions, or more generally whenever you want the model to produce a particular
              JSON structure of output.

              See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    async def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        stream: Literal[True],
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[TextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncStream[RawMessageStreamEvent]:
        """
        Send a structured list of input messages with text and/or image content, and the
        model will generate the next message in the conversation.

        The Messages API can be used for either single queries or stateless multi-turn
        conversations.

        Args:
          max_tokens: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

              Different models have different maximum values for this parameter. See
              [models](https://docs.anthropic.com/en/docs/models-overview) for details.

          messages: Input messages.

              Our models are trained to operate on alternating `user` and `assistant`
              conversational turns. When creating a new `Message`, you specify the prior
              conversational turns with the `messages` parameter, and the model then generates
              the next `Message` in the conversation. Consecutive `user` or `assistant` turns
              in your request will be combined into a single turn.

              Each input message must be an object with a `role` and `content`. You can
              specify a single `user`-role message, or you can include multiple `user` and
              `assistant` messages.

              If the final message uses the `assistant` role, the response content will
              continue immediately from the content in that message. This can be used to
              constrain part of the model's response.

              Example with a single `user` message:

              ```json
              [{ "role": "user", "content": "Hello, Claude" }]
              ```

              Example with multiple conversational turns:

              ```json
              [
                { "role": "user", "content": "Hello there." },
                { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
                { "role": "user", "content": "Can you explain LLMs in plain English?" }
              ]
              ```

              Example with a partially-filled response from Claude:

              ```json
              [
                {
                  "role": "user",
                  "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
                },
                { "role": "assistant", "content": "The best answer is (" }
              ]
              ```

              Each input message `content` may be either a single `string` or an array of
              content blocks, where each block has a specific `type`. Using a `string` for
              `content` is shorthand for an array of one content block of type `"text"`. The
              following input messages are equivalent:

              ```json
              { "role": "user", "content": "Hello, Claude" }
              ```

              ```json
              { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
              ```

              Starting with Claude 3 models, you can also send image content blocks:

              ```json
              {
                "role": "user",
                "content": [
                  {
                    "type": "image",
                    "source": {
                      "type": "base64",
                      "media_type": "image/jpeg",
                      "data": "/9j/4AAQSkZJRg..."
                    }
                  },
                  { "type": "text", "text": "What is in this image?" }
                ]
              }
              ```

              We currently support the `base64` source type for images, and the `image/jpeg`,
              `image/png`, `image/gif`, and `image/webp` media types.

              See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
              more input examples.

              Note that if you want to include a
              [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
              the top-level `system` parameter — there is no `"system"` role for input
              messages in the Messages API.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
              details.

          metadata: An object describing metadata about the request.

          stop_sequences: Custom text sequences that will cause the model to stop generating.

              Our models will normally stop when they have naturally completed their turn,
              which will result in a response `stop_reason` of `"end_turn"`.

              If you want the model to stop generating when it encounters custom strings of
              text, you can use the `stop_sequences` parameter. If the model encounters one of
              the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
              and the response `stop_sequence` value will contain the matched stop sequence.

          system: System prompt.

              A system prompt is a way of providing context and instructions to Claude, such
              as specifying a particular goal or role. See our
              [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          tool_choice: How the model should use the provided tools. The model can use a specific tool,
              any available tool, or decide by itself.

          tools: Definitions of tools that the model may use.

              If you include `tools` in your API request, the model may return `tool_use`
              content blocks that represent the model's use of those tools. You can then run
              those tools using the tool input generated by the model and then optionally
              return results back to the model using `tool_result` content blocks.

              Each tool definition includes:

              - `name`: Name of the tool.
              - `description`: Optional, but strongly-recommended description of the tool.
              - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
                shape that the model will produce in `tool_use` output content blocks.

              For example, if you defined `tools` as:

              ```json
              [
                {
                  "name": "get_stock_price",
                  "description": "Get the current stock price for a given ticker symbol.",
                  "input_schema": {
                    "type": "object",
                    "properties": {
                      "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
                      }
                    },
                    "required": ["ticker"]
                  }
                }
              ]
              ```

              And then asked the model "What's the S&P 500 at today?", the model might produce
              `tool_use` content blocks in the response like this:

              ```json
              [
                {
                  "type": "tool_use",
                  "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "name": "get_stock_price",
                  "input": { "ticker": "^GSPC" }
                }
              ]
              ```

              You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
              input, and return the following back to the model in a subsequent `user`
              message:

              ```json
              [
                {
                  "type": "tool_result",
                  "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "content": "259.75 USD"
                }
              ]
              ```

              Tools can be used for workflows that include running client-side tools and
              functions, or more generally whenever you want the model to produce a particular
              JSON structure of output.

              See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    async def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        stream: bool,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[TextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Message | AsyncStream[RawMessageStreamEvent]:
        """
        Send a structured list of input messages with text and/or image content, and the
        model will generate the next message in the conversation.

        The Messages API can be used for either single queries or stateless multi-turn
        conversations.

        Args:
          max_tokens: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

              Different models have different maximum values for this parameter. See
              [models](https://docs.anthropic.com/en/docs/models-overview) for details.

          messages: Input messages.

              Our models are trained to operate on alternating `user` and `assistant`
              conversational turns. When creating a new `Message`, you specify the prior
              conversational turns with the `messages` parameter, and the model then generates
              the next `Message` in the conversation. Consecutive `user` or `assistant` turns
              in your request will be combined into a single turn.

              Each input message must be an object with a `role` and `content`. You can
              specify a single `user`-role message, or you can include multiple `user` and
              `assistant` messages.

              If the final message uses the `assistant` role, the response content will
              continue immediately from the content in that message. This can be used to
              constrain part of the model's response.

              Example with a single `user` message:

              ```json
              [{ "role": "user", "content": "Hello, Claude" }]
              ```

              Example with multiple conversational turns:

              ```json
              [
                { "role": "user", "content": "Hello there." },
                { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
                { "role": "user", "content": "Can you explain LLMs in plain English?" }
              ]
              ```

              Example with a partially-filled response from Claude:

              ```json
              [
                {
                  "role": "user",
                  "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
                },
                { "role": "assistant", "content": "The best answer is (" }
              ]
              ```

              Each input message `content` may be either a single `string` or an array of
              content blocks, where each block has a specific `type`. Using a `string` for
              `content` is shorthand for an array of one content block of type `"text"`. The
              following input messages are equivalent:

              ```json
              { "role": "user", "content": "Hello, Claude" }
              ```

              ```json
              { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
              ```

              Starting with Claude 3 models, you can also send image content blocks:

              ```json
              {
                "role": "user",
                "content": [
                  {
                    "type": "image",
                    "source": {
                      "type": "base64",
                      "media_type": "image/jpeg",
                      "data": "/9j/4AAQSkZJRg..."
                    }
                  },
                  { "type": "text", "text": "What is in this image?" }
                ]
              }
              ```

              We currently support the `base64` source type for images, and the `image/jpeg`,
              `image/png`, `image/gif`, and `image/webp` media types.

              See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
              more input examples.

              Note that if you want to include a
              [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
              the top-level `system` parameter — there is no `"system"` role for input
              messages in the Messages API.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
              details.

          metadata: An object describing metadata about the request.

          stop_sequences: Custom text sequences that will cause the model to stop generating.

              Our models will normally stop when they have naturally completed their turn,
              which will result in a response `stop_reason` of `"end_turn"`.

              If you want the model to stop generating when it encounters custom strings of
              text, you can use the `stop_sequences` parameter. If the model encounters one of
              the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
              and the response `stop_sequence` value will contain the matched stop sequence.

          system: System prompt.

              A system prompt is a way of providing context and instructions to Claude, such
              as specifying a particular goal or role. See our
              [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          tool_choice: How the model should use the provided tools. The model can use a specific tool,
              any available tool, or decide by itself.

          tools: Definitions of tools that the model may use.

              If you include `tools` in your API request, the model may return `tool_use`
              content blocks that represent the model's use of those tools. You can then run
              those tools using the tool input generated by the model and then optionally
              return results back to the model using `tool_result` content blocks.

              Each tool definition includes:

              - `name`: Name of the tool.
              - `description`: Optional, but strongly-recommended description of the tool.
              - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
                shape that the model will produce in `tool_use` output content blocks.

              For example, if you defined `tools` as:

              ```json
              [
                {
                  "name": "get_stock_price",
                  "description": "Get the current stock price for a given ticker symbol.",
                  "input_schema": {
                    "type": "object",
                    "properties": {
                      "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
                      }
                    },
                    "required": ["ticker"]
                  }
                }
              ]
              ```

              And then asked the model "What's the S&P 500 at today?", the model might produce
              `tool_use` content blocks in the response like this:

              ```json
              [
                {
                  "type": "tool_use",
                  "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "name": "get_stock_price",
                  "input": { "ticker": "^GSPC" }
                }
              ]
              ```

              You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
              input, and return the following back to the model in a subsequent `user`
              message:

              ```json
              [
                {
                  "type": "tool_result",
                  "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "content": "259.75 USD"
                }
              ]
              ```

              Tools can be used for workflows that include running client-side tools and
              functions, or more generally whenever you want the model to produce a particular
              JSON structure of output.

              See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @required_args(["max_tokens", "messages", "model"], ["max_tokens", "messages", "model", "stream"])
    async def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | Literal[True] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[TextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Message | AsyncStream[RawMessageStreamEvent]:
        if not is_given(timeout) and self._client.timeout == DEFAULT_TIMEOUT:
            timeout = 600

        if model in DEPRECATED_MODELS:
            warnings.warn(
                f"The model '{model}' is deprecated and will reach end-of-life on {DEPRECATED_MODELS[model]}.\nPlease migrate to a newer model. Visit https://docs.anthropic.com/en/docs/resources/model-deprecations for more information.",
                DeprecationWarning,
                stacklevel=3,
            )

        return await self._post(
            "/v1/messages",
            body=await async_maybe_transform(
                {
                    "max_tokens": max_tokens,
                    "messages": messages,
                    "model": model,
                    "metadata": metadata,
                    "stop_sequences": stop_sequences,
                    "stream": stream,
                    "system": system,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_k": top_k,
                    "top_p": top_p,
                },
                message_create_params.MessageCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Message,
            stream=stream or False,
            stream_cls=AsyncStream[RawMessageStreamEvent],
        )

    def stream(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[TextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncMessageStreamManager:
        """Create a Message stream"""
        if model in DEPRECATED_MODELS:
            warnings.warn(
                f"The model '{model}' is deprecated and will reach end-of-life on {DEPRECATED_MODELS[model]}.\nPlease migrate to a newer model. Visit https://docs.anthropic.com/en/docs/resources/model-deprecations for more information.",
                DeprecationWarning,
                stacklevel=3,
            )

        extra_headers = {
            "X-Stainless-Stream-Helper": "messages",
            **(extra_headers or {}),
        }
        request = self._post(
            "/v1/messages",
            body=maybe_transform(
                {
                    "max_tokens": max_tokens,
                    "messages": messages,
                    "model": model,
                    "metadata": metadata,
                    "stop_sequences": stop_sequences,
                    "system": system,
                    "temperature": temperature,
                    "top_k": top_k,
                    "top_p": top_p,
                    "tools": tools,
                    "tool_choice": tool_choice,
                    "stream": True,
                },
                message_create_params.MessageCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Message,
            stream=True,
            stream_cls=AsyncStream[RawMessageStreamEvent],
        )
        return AsyncMessageStreamManager(request)


class MessagesWithRawResponse:
    def __init__(self, messages: Messages) -> None:
        self._messages = messages

        self.create = _legacy_response.to_raw_response_wrapper(
            messages.create,
        )


class AsyncMessagesWithRawResponse:
    def __init__(self, messages: AsyncMessages) -> None:
        self._messages = messages

        self.create = _legacy_response.async_to_raw_response_wrapper(
            messages.create,
        )


class MessagesWithStreamingResponse:
    def __init__(self, messages: Messages) -> None:
        self._messages = messages

        self.create = to_streamed_response_wrapper(
            messages.create,
        )


class AsyncMessagesWithStreamingResponse:
    def __init__(self, messages: AsyncMessages) -> None:
        self._messages = messages

        self.create = async_to_streamed_response_wrapper(
            messages.create,
        )

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_vim_builtins.py ===
"""
    pygments.lexers._vim_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This file is autogenerated by scripts/get_vimkw.py

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# Split up in multiple functions so it's importable by jython, which has a
# per-method size limit.

def _getauto():
    var = (
        ('BufAdd','BufAdd'),
        ('BufCreate','BufCreate'),
        ('BufDelete','BufDelete'),
        ('BufEnter','BufEnter'),
        ('BufFilePost','BufFilePost'),
        ('BufFilePre','BufFilePre'),
        ('BufHidden','BufHidden'),
        ('BufLeave','BufLeave'),
        ('BufNew','BufNew'),
        ('BufNewFile','BufNewFile'),
        ('BufRead','BufRead'),
        ('BufReadCmd','BufReadCmd'),
        ('BufReadPost','BufReadPost'),
        ('BufReadPre','BufReadPre'),
        ('BufUnload','BufUnload'),
        ('BufWinEnter','BufWinEnter'),
        ('BufWinLeave','BufWinLeave'),
        ('BufWipeout','BufWipeout'),
        ('BufWrite','BufWrite'),
        ('BufWriteCmd','BufWriteCmd'),
        ('BufWritePost','BufWritePost'),
        ('BufWritePre','BufWritePre'),
        ('Cmd','Cmd'),
        ('CmdwinEnter','CmdwinEnter'),
        ('CmdwinLeave','CmdwinLeave'),
        ('ColorScheme','ColorScheme'),
        ('CompleteDone','CompleteDone'),
        ('CursorHold','CursorHold'),
        ('CursorHoldI','CursorHoldI'),
        ('CursorMoved','CursorMoved'),
        ('CursorMovedI','CursorMovedI'),
        ('EncodingChanged','EncodingChanged'),
        ('FileAppendCmd','FileAppendCmd'),
        ('FileAppendPost','FileAppendPost'),
        ('FileAppendPre','FileAppendPre'),
        ('FileChangedRO','FileChangedRO'),
        ('FileChangedShell','FileChangedShell'),
        ('FileChangedShellPost','FileChangedShellPost'),
        ('FileEncoding','FileEncoding'),
        ('FileReadCmd','FileReadCmd'),
        ('FileReadPost','FileReadPost'),
        ('FileReadPre','FileReadPre'),
        ('FileType','FileType'),
        ('FileWriteCmd','FileWriteCmd'),
        ('FileWritePost','FileWritePost'),
        ('FileWritePre','FileWritePre'),
        ('FilterReadPost','FilterReadPost'),
        ('FilterReadPre','FilterReadPre'),
        ('FilterWritePost','FilterWritePost'),
        ('FilterWritePre','FilterWritePre'),
        ('FocusGained','FocusGained'),
        ('FocusLost','FocusLost'),
        ('FuncUndefined','FuncUndefined'),
        ('GUIEnter','GUIEnter'),
        ('GUIFailed','GUIFailed'),
        ('InsertChange','InsertChange'),
        ('InsertCharPre','InsertCharPre'),
        ('InsertEnter','InsertEnter'),
        ('InsertLeave','InsertLeave'),
        ('MenuPopup','MenuPopup'),
        ('QuickFixCmdPost','QuickFixCmdPost'),
        ('QuickFixCmdPre','QuickFixCmdPre'),
        ('QuitPre','QuitPre'),
        ('RemoteReply','RemoteReply'),
        ('SessionLoadPost','SessionLoadPost'),
        ('ShellCmdPost','ShellCmdPost'),
        ('ShellFilterPost','ShellFilterPost'),
        ('SourceCmd','SourceCmd'),
        ('SourcePre','SourcePre'),
        ('SpellFileMissing','SpellFileMissing'),
        ('StdinReadPost','StdinReadPost'),
        ('StdinReadPre','StdinReadPre'),
        ('SwapExists','SwapExists'),
        ('Syntax','Syntax'),
        ('TabEnter','TabEnter'),
        ('TabLeave','TabLeave'),
        ('TermChanged','TermChanged'),
        ('TermResponse','TermResponse'),
        ('TextChanged','TextChanged'),
        ('TextChangedI','TextChangedI'),
        ('User','User'),
        ('UserGettingBored','UserGettingBored'),
        ('VimEnter','VimEnter'),
        ('VimLeave','VimLeave'),
        ('VimLeavePre','VimLeavePre'),
        ('VimResized','VimResized'),
        ('WinEnter','WinEnter'),
        ('WinLeave','WinLeave'),
        ('event','event'),
    )
    return var
auto = _getauto()

def _getcommand():
    var = (
        ('a','a'),
        ('ab','ab'),
        ('abc','abclear'),
        ('abo','aboveleft'),
        ('al','all'),
        ('ar','ar'),
        ('ar','args'),
        ('arga','argadd'),
        ('argd','argdelete'),
        ('argdo','argdo'),
        ('arge','argedit'),
        ('argg','argglobal'),
        ('argl','arglocal'),
        ('argu','argument'),
        ('as','ascii'),
        ('au','au'),
        ('b','buffer'),
        ('bN','bNext'),
        ('ba','ball'),
        ('bad','badd'),
        ('bd','bdelete'),
        ('bel','belowright'),
        ('bf','bfirst'),
        ('bl','blast'),
        ('bm','bmodified'),
        ('bn','bnext'),
        ('bo','botright'),
        ('bp','bprevious'),
        ('br','br'),
        ('br','brewind'),
        ('brea','break'),
        ('breaka','breakadd'),
        ('breakd','breakdel'),
        ('breakl','breaklist'),
        ('bro','browse'),
        ('bu','bu'),
        ('buf','buf'),
        ('bufdo','bufdo'),
        ('buffers','buffers'),
        ('bun','bunload'),
        ('bw','bwipeout'),
        ('c','c'),
        ('c','change'),
        ('cN','cN'),
        ('cN','cNext'),
        ('cNf','cNf'),
        ('cNf','cNfile'),
        ('cabc','cabclear'),
        ('cad','cad'),
        ('cad','caddexpr'),
        ('caddb','caddbuffer'),
        ('caddf','caddfile'),
        ('cal','call'),
        ('cat','catch'),
        ('cb','cbuffer'),
        ('cc','cc'),
        ('ccl','cclose'),
        ('cd','cd'),
        ('ce','center'),
        ('cex','cexpr'),
        ('cf','cfile'),
        ('cfir','cfirst'),
        ('cg','cgetfile'),
        ('cgetb','cgetbuffer'),
        ('cgete','cgetexpr'),
        ('changes','changes'),
        ('chd','chdir'),
        ('che','checkpath'),
        ('checkt','checktime'),
        ('cl','cl'),
        ('cl','clist'),
        ('cla','clast'),
        ('clo','close'),
        ('cmapc','cmapclear'),
        ('cn','cn'),
        ('cn','cnext'),
        ('cnew','cnewer'),
        ('cnf','cnf'),
        ('cnf','cnfile'),
        ('co','copy'),
        ('col','colder'),
        ('colo','colorscheme'),
        ('com','com'),
        ('comc','comclear'),
        ('comp','compiler'),
        ('con','con'),
        ('con','continue'),
        ('conf','confirm'),
        ('cope','copen'),
        ('cp','cprevious'),
        ('cpf','cpfile'),
        ('cq','cquit'),
        ('cr','crewind'),
        ('cs','cs'),
        ('cscope','cscope'),
        ('cstag','cstag'),
        ('cuna','cunabbrev'),
        ('cw','cwindow'),
        ('d','d'),
        ('d','delete'),
        ('de','de'),
        ('debug','debug'),
        ('debugg','debuggreedy'),
        ('del','del'),
        ('delc','delcommand'),
        ('delel','delel'),
        ('delep','delep'),
        ('deletel','deletel'),
        ('deletep','deletep'),
        ('deletl','deletl'),
        ('deletp','deletp'),
        ('delf','delf'),
        ('delf','delfunction'),
        ('dell','dell'),
        ('delm','delmarks'),
        ('delp','delp'),
        ('dep','dep'),
        ('di','di'),
        ('di','display'),
        ('diffg','diffget'),
        ('diffo','diffoff'),
        ('diffp','diffpatch'),
        ('diffpu','diffput'),
        ('diffs','diffsplit'),
        ('difft','diffthis'),
        ('diffu','diffupdate'),
        ('dig','dig'),
        ('dig','digraphs'),
        ('dir','dir'),
        ('dj','djump'),
        ('dl','dl'),
        ('dli','dlist'),
        ('do','do'),
        ('doau','doau'),
        ('dp','dp'),
        ('dr','drop'),
        ('ds','dsearch'),
        ('dsp','dsplit'),
        ('e','e'),
        ('e','edit'),
        ('ea','ea'),
        ('earlier','earlier'),
        ('ec','ec'),
        ('echoe','echoerr'),
        ('echom','echomsg'),
        ('echon','echon'),
        ('el','else'),
        ('elsei','elseif'),
        ('em','emenu'),
        ('en','en'),
        ('en','endif'),
        ('endf','endf'),
        ('endf','endfunction'),
        ('endfo','endfor'),
        ('endfun','endfun'),
        ('endt','endtry'),
        ('endw','endwhile'),
        ('ene','enew'),
        ('ex','ex'),
        ('exi','exit'),
        ('exu','exusage'),
        ('f','f'),
        ('f','file'),
        ('files','files'),
        ('filet','filet'),
        ('filetype','filetype'),
        ('fin','fin'),
        ('fin','find'),
        ('fina','finally'),
        ('fini','finish'),
        ('fir','first'),
        ('fix','fixdel'),
        ('fo','fold'),
        ('foldc','foldclose'),
        ('foldd','folddoopen'),
        ('folddoc','folddoclosed'),
        ('foldo','foldopen'),
        ('for','for'),
        ('fu','fu'),
        ('fu','function'),
        ('fun','fun'),
        ('g','g'),
        ('go','goto'),
        ('gr','grep'),
        ('grepa','grepadd'),
        ('gui','gui'),
        ('gvim','gvim'),
        ('h','h'),
        ('h','help'),
        ('ha','hardcopy'),
        ('helpf','helpfind'),
        ('helpg','helpgrep'),
        ('helpt','helptags'),
        ('hi','hi'),
        ('hid','hide'),
        ('his','history'),
        ('i','i'),
        ('ia','ia'),
        ('iabc','iabclear'),
        ('if','if'),
        ('ij','ijump'),
        ('il','ilist'),
        ('imapc','imapclear'),
        ('in','in'),
        ('intro','intro'),
        ('is','isearch'),
        ('isp','isplit'),
        ('iuna','iunabbrev'),
        ('j','join'),
        ('ju','jumps'),
        ('k','k'),
        ('kee','keepmarks'),
        ('keepa','keepa'),
        ('keepalt','keepalt'),
        ('keepj','keepjumps'),
        ('keepp','keeppatterns'),
        ('l','l'),
        ('l','list'),
        ('lN','lN'),
        ('lN','lNext'),
        ('lNf','lNf'),
        ('lNf','lNfile'),
        ('la','la'),
        ('la','last'),
        ('lad','lad'),
        ('lad','laddexpr'),
        ('laddb','laddbuffer'),
        ('laddf','laddfile'),
        ('lan','lan'),
        ('lan','language'),
        ('lat','lat'),
        ('later','later'),
        ('lb','lbuffer'),
        ('lc','lcd'),
        ('lch','lchdir'),
        ('lcl','lclose'),
        ('lcs','lcs'),
        ('lcscope','lcscope'),
        ('le','left'),
        ('lefta','leftabove'),
        ('lex','lexpr'),
        ('lf','lfile'),
        ('lfir','lfirst'),
        ('lg','lgetfile'),
        ('lgetb','lgetbuffer'),
        ('lgete','lgetexpr'),
        ('lgr','lgrep'),
        ('lgrepa','lgrepadd'),
        ('lh','lhelpgrep'),
        ('ll','ll'),
        ('lla','llast'),
        ('lli','llist'),
        ('lmak','lmake'),
        ('lmapc','lmapclear'),
        ('lne','lne'),
        ('lne','lnext'),
        ('lnew','lnewer'),
        ('lnf','lnf'),
        ('lnf','lnfile'),
        ('lo','lo'),
        ('lo','loadview'),
        ('loadk','loadk'),
        ('loadkeymap','loadkeymap'),
        ('loc','lockmarks'),
        ('lockv','lockvar'),
        ('lol','lolder'),
        ('lop','lopen'),
        ('lp','lprevious'),
        ('lpf','lpfile'),
        ('lr','lrewind'),
        ('ls','ls'),
        ('lt','ltag'),
        ('lua','lua'),
        ('luado','luado'),
        ('luafile','luafile'),
        ('lv','lvimgrep'),
        ('lvimgrepa','lvimgrepadd'),
        ('lw','lwindow'),
        ('m','move'),
        ('ma','ma'),
        ('ma','mark'),
        ('mak','make'),
        ('marks','marks'),
        ('mat','match'),
        ('menut','menut'),
        ('menut','menutranslate'),
        ('mes','mes'),
        ('messages','messages'),
        ('mk','mk'),
        ('mk','mkexrc'),
        ('mks','mksession'),
        ('mksp','mkspell'),
        ('mkv','mkv'),
        ('mkv','mkvimrc'),
        ('mkvie','mkview'),
        ('mo','mo'),
        ('mod','mode'),
        ('mz','mz'),
        ('mz','mzscheme'),
        ('mzf','mzfile'),
        ('n','n'),
        ('n','next'),
        ('nb','nbkey'),
        ('nbc','nbclose'),
        ('nbs','nbstart'),
        ('ne','ne'),
        ('new','new'),
        ('nmapc','nmapclear'),
        ('noa','noa'),
        ('noautocmd','noautocmd'),
        ('noh','nohlsearch'),
        ('nu','number'),
        ('o','o'),
        ('o','open'),
        ('ol','oldfiles'),
        ('omapc','omapclear'),
        ('on','only'),
        ('opt','options'),
        ('ownsyntax','ownsyntax'),
        ('p','p'),
        ('p','print'),
        ('pc','pclose'),
        ('pe','pe'),
        ('pe','perl'),
        ('ped','pedit'),
        ('perld','perldo'),
        ('po','pop'),
        ('popu','popu'),
        ('popu','popup'),
        ('pp','ppop'),
        ('pr','pr'),
        ('pre','preserve'),
        ('prev','previous'),
        ('pro','pro'),
        ('prof','profile'),
        ('profd','profdel'),
        ('promptf','promptfind'),
        ('promptr','promptrepl'),
        ('ps','psearch'),
        ('ptN','ptN'),
        ('ptN','ptNext'),
        ('pta','ptag'),
        ('ptf','ptfirst'),
        ('ptj','ptjump'),
        ('ptl','ptlast'),
        ('ptn','ptn'),
        ('ptn','ptnext'),
        ('ptp','ptprevious'),
        ('ptr','ptrewind'),
        ('pts','ptselect'),
        ('pu','put'),
        ('pw','pwd'),
        ('py','py'),
        ('py','python'),
        ('py3','py3'),
        ('py3','py3'),
        ('py3do','py3do'),
        ('pydo','pydo'),
        ('pyf','pyfile'),
        ('python3','python3'),
        ('q','q'),
        ('q','quit'),
        ('qa','qall'),
        ('quita','quitall'),
        ('r','r'),
        ('r','read'),
        ('re','re'),
        ('rec','recover'),
        ('red','red'),
        ('red','redo'),
        ('redi','redir'),
        ('redr','redraw'),
        ('redraws','redrawstatus'),
        ('reg','registers'),
        ('res','resize'),
        ('ret','retab'),
        ('retu','return'),
        ('rew','rewind'),
        ('ri','right'),
        ('rightb','rightbelow'),
        ('ru','ru'),
        ('ru','runtime'),
        ('rub','ruby'),
        ('rubyd','rubydo'),
        ('rubyf','rubyfile'),
        ('rundo','rundo'),
        ('rv','rviminfo'),
        ('sN','sNext'),
        ('sa','sargument'),
        ('sal','sall'),
        ('san','sandbox'),
        ('sav','saveas'),
        ('sb','sbuffer'),
        ('sbN','sbNext'),
        ('sba','sball'),
        ('sbf','sbfirst'),
        ('sbl','sblast'),
        ('sbm','sbmodified'),
        ('sbn','sbnext'),
        ('sbp','sbprevious'),
        ('sbr','sbrewind'),
        ('scrip','scrip'),
        ('scrip','scriptnames'),
        ('scripte','scriptencoding'),
        ('scs','scs'),
        ('scscope','scscope'),
        ('se','set'),
        ('setf','setfiletype'),
        ('setg','setglobal'),
        ('setl','setlocal'),
        ('sf','sfind'),
        ('sfir','sfirst'),
        ('sh','shell'),
        ('si','si'),
        ('sig','sig'),
        ('sign','sign'),
        ('sil','silent'),
        ('sim','simalt'),
        ('sl','sl'),
        ('sl','sleep'),
        ('sla','slast'),
        ('sm','smagic'),
        ('sm','smap'),
        ('sme','sme'),
        ('smenu','smenu'),
        ('sn','snext'),
        ('sni','sniff'),
        ('sno','snomagic'),
        ('snoreme','snoreme'),
        ('snoremenu','snoremenu'),
        ('so','so'),
        ('so','source'),
        ('sor','sort'),
        ('sp','split'),
        ('spe','spe'),
        ('spe','spellgood'),
        ('spelld','spelldump'),
        ('spelli','spellinfo'),
        ('spellr','spellrepall'),
        ('spellu','spellundo'),
        ('spellw','spellwrong'),
        ('spr','sprevious'),
        ('sre','srewind'),
        ('st','st'),
        ('st','stop'),
        ('sta','stag'),
        ('star','star'),
        ('star','startinsert'),
        ('start','start'),
        ('startg','startgreplace'),
        ('startr','startreplace'),
        ('stj','stjump'),
        ('stopi','stopinsert'),
        ('sts','stselect'),
        ('sun','sunhide'),
        ('sunme','sunme'),
        ('sunmenu','sunmenu'),
        ('sus','suspend'),
        ('sv','sview'),
        ('sw','swapname'),
        ('sy','sy'),
        ('syn','syn'),
        ('sync','sync'),
        ('syncbind','syncbind'),
        ('syntime','syntime'),
        ('t','t'),
        ('tN','tN'),
        ('tN','tNext'),
        ('ta','ta'),
        ('ta','tag'),
        ('tab','tab'),
        ('tabN','tabN'),
        ('tabN','tabNext'),
        ('tabc','tabclose'),
        ('tabd','tabdo'),
        ('tabe','tabedit'),
        ('tabf','tabfind'),
        ('tabfir','tabfirst'),
        ('tabl','tablast'),
        ('tabm','tabmove'),
        ('tabn','tabnext'),
        ('tabnew','tabnew'),
        ('tabo','tabonly'),
        ('tabp','tabprevious'),
        ('tabr','tabrewind'),
        ('tabs','tabs'),
        ('tags','tags'),
        ('tc','tcl'),
        ('tcld','tcldo'),
        ('tclf','tclfile'),
        ('te','tearoff'),
        ('tf','tfirst'),
        ('th','throw'),
        ('tj','tjump'),
        ('tl','tlast'),
        ('tm','tm'),
        ('tm','tmenu'),
        ('tn','tn'),
        ('tn','tnext'),
        ('to','topleft'),
        ('tp','tprevious'),
        ('tr','tr'),
        ('tr','trewind'),
        ('try','try'),
        ('ts','tselect'),
        ('tu','tu'),
        ('tu','tunmenu'),
        ('u','u'),
        ('u','undo'),
        ('un','un'),
        ('una','unabbreviate'),
        ('undoj','undojoin'),
        ('undol','undolist'),
        ('unh','unhide'),
        ('unl','unl'),
        ('unlo','unlockvar'),
        ('uns','unsilent'),
        ('up','update'),
        ('v','v'),
        ('ve','ve'),
        ('ve','version'),
        ('verb','verbose'),
        ('vert','vertical'),
        ('vi','vi'),
        ('vi','visual'),
        ('vie','view'),
        ('vim','vimgrep'),
        ('vimgrepa','vimgrepadd'),
        ('viu','viusage'),
        ('vmapc','vmapclear'),
        ('vne','vnew'),
        ('vs','vsplit'),
        ('w','w'),
        ('w','write'),
        ('wN','wNext'),
        ('wa','wall'),
        ('wh','while'),
        ('win','win'),
        ('win','winsize'),
        ('winc','wincmd'),
        ('windo','windo'),
        ('winp','winpos'),
        ('wn','wnext'),
        ('wp','wprevious'),
        ('wq','wq'),
        ('wqa','wqall'),
        ('ws','wsverb'),
        ('wundo','wundo'),
        ('wv','wviminfo'),
        ('x','x'),
        ('x','xit'),
        ('xa','xall'),
        ('xmapc','xmapclear'),
        ('xme','xme'),
        ('xmenu','xmenu'),
        ('xnoreme','xnoreme'),
        ('xnoremenu','xnoremenu'),
        ('xunme','xunme'),
        ('xunmenu','xunmenu'),
        ('xwininfo','xwininfo'),
        ('y','yank'),
    )
    return var
command = _getcommand()

def _getoption():
    var = (
        ('acd','acd'),
        ('ai','ai'),
        ('akm','akm'),
        ('al','al'),
        ('aleph','aleph'),
        ('allowrevins','allowrevins'),
        ('altkeymap','altkeymap'),
        ('ambiwidth','ambiwidth'),
        ('ambw','ambw'),
        ('anti','anti'),
        ('antialias','antialias'),
        ('ar','ar'),
        ('arab','arab'),
        ('arabic','arabic'),
        ('arabicshape','arabicshape'),
        ('ari','ari'),
        ('arshape','arshape'),
        ('autochdir','autochdir'),
        ('autoindent','autoindent'),
        ('autoread','autoread'),
        ('autowrite','autowrite'),
        ('autowriteall','autowriteall'),
        ('aw','aw'),
        ('awa','awa'),
        ('background','background'),
        ('backspace','backspace'),
        ('backup','backup'),
        ('backupcopy','backupcopy'),
        ('backupdir','backupdir'),
        ('backupext','backupext'),
        ('backupskip','backupskip'),
        ('balloondelay','balloondelay'),
        ('ballooneval','ballooneval'),
        ('balloonexpr','balloonexpr'),
        ('bdir','bdir'),
        ('bdlay','bdlay'),
        ('beval','beval'),
        ('bex','bex'),
        ('bexpr','bexpr'),
        ('bg','bg'),
        ('bh','bh'),
        ('bin','bin'),
        ('binary','binary'),
        ('biosk','biosk'),
        ('bioskey','bioskey'),
        ('bk','bk'),
        ('bkc','bkc'),
        ('bl','bl'),
        ('bomb','bomb'),
        ('breakat','breakat'),
        ('brk','brk'),
        ('browsedir','browsedir'),
        ('bs','bs'),
        ('bsdir','bsdir'),
        ('bsk','bsk'),
        ('bt','bt'),
        ('bufhidden','bufhidden'),
        ('buflisted','buflisted'),
        ('buftype','buftype'),
        ('casemap','casemap'),
        ('cb','cb'),
        ('cc','cc'),
        ('ccv','ccv'),
        ('cd','cd'),
        ('cdpath','cdpath'),
        ('cedit','cedit'),
        ('cf','cf'),
        ('cfu','cfu'),
        ('ch','ch'),
        ('charconvert','charconvert'),
        ('ci','ci'),
        ('cin','cin'),
        ('cindent','cindent'),
        ('cink','cink'),
        ('cinkeys','cinkeys'),
        ('cino','cino'),
        ('cinoptions','cinoptions'),
        ('cinw','cinw'),
        ('cinwords','cinwords'),
        ('clipboard','clipboard'),
        ('cmdheight','cmdheight'),
        ('cmdwinheight','cmdwinheight'),
        ('cmp','cmp'),
        ('cms','cms'),
        ('co','co'),
        ('cocu','cocu'),
        ('cole','cole'),
        ('colorcolumn','colorcolumn'),
        ('columns','columns'),
        ('com','com'),
        ('comments','comments'),
        ('commentstring','commentstring'),
        ('compatible','compatible'),
        ('complete','complete'),
        ('completefunc','completefunc'),
        ('completeopt','completeopt'),
        ('concealcursor','concealcursor'),
        ('conceallevel','conceallevel'),
        ('confirm','confirm'),
        ('consk','consk'),
        ('conskey','conskey'),
        ('copyindent','copyindent'),
        ('cot','cot'),
        ('cp','cp'),
        ('cpo','cpo'),
        ('cpoptions','cpoptions'),
        ('cpt','cpt'),
        ('crb','crb'),
        ('cryptmethod','cryptmethod'),
        ('cscopepathcomp','cscopepathcomp'),
        ('cscopeprg','cscopeprg'),
        ('cscopequickfix','cscopequickfix'),
        ('cscoperelative','cscoperelative'),
        ('cscopetag','cscopetag'),
        ('cscopetagorder','cscopetagorder'),
        ('cscopeverbose','cscopeverbose'),
        ('cspc','cspc'),
        ('csprg','csprg'),
        ('csqf','csqf'),
        ('csre','csre'),
        ('cst','cst'),
        ('csto','csto'),
        ('csverb','csverb'),
        ('cuc','cuc'),
        ('cul','cul'),
        ('cursorbind','cursorbind'),
        ('cursorcolumn','cursorcolumn'),
        ('cursorline','cursorline'),
        ('cwh','cwh'),
        ('debug','debug'),
        ('deco','deco'),
        ('def','def'),
        ('define','define'),
        ('delcombine','delcombine'),
        ('dex','dex'),
        ('dg','dg'),
        ('dict','dict'),
        ('dictionary','dictionary'),
        ('diff','diff'),
        ('diffexpr','diffexpr'),
        ('diffopt','diffopt'),
        ('digraph','digraph'),
        ('dip','dip'),
        ('dir','dir'),
        ('directory','directory'),
        ('display','display'),
        ('dy','dy'),
        ('ea','ea'),
        ('ead','ead'),
        ('eadirection','eadirection'),
        ('eb','eb'),
        ('ed','ed'),
        ('edcompatible','edcompatible'),
        ('ef','ef'),
        ('efm','efm'),
        ('ei','ei'),
        ('ek','ek'),
        ('enc','enc'),
        ('encoding','encoding'),
        ('endofline','endofline'),
        ('eol','eol'),
        ('ep','ep'),
        ('equalalways','equalalways'),
        ('equalprg','equalprg'),
        ('errorbells','errorbells'),
        ('errorfile','errorfile'),
        ('errorformat','errorformat'),
        ('esckeys','esckeys'),
        ('et','et'),
        ('eventignore','eventignore'),
        ('ex','ex'),
        ('expandtab','expandtab'),
        ('exrc','exrc'),
        ('fcl','fcl'),
        ('fcs','fcs'),
        ('fdc','fdc'),
        ('fde','fde'),
        ('fdi','fdi'),
        ('fdl','fdl'),
        ('fdls','fdls'),
        ('fdm','fdm'),
        ('fdn','fdn'),
        ('fdo','fdo'),
        ('fdt','fdt'),
        ('fen','fen'),
        ('fenc','fenc'),
        ('fencs','fencs'),
        ('fex','fex'),
        ('ff','ff'),
        ('ffs','ffs'),
        ('fic','fic'),
        ('fileencoding','fileencoding'),
        ('fileencodings','fileencodings'),
        ('fileformat','fileformat'),
        ('fileformats','fileformats'),
        ('fileignorecase','fileignorecase'),
        ('filetype','filetype'),
        ('fillchars','fillchars'),
        ('fk','fk'),
        ('fkmap','fkmap'),
        ('flp','flp'),
        ('fml','fml'),
        ('fmr','fmr'),
        ('fo','fo'),
        ('foldclose','foldclose'),
        ('foldcolumn','foldcolumn'),
        ('foldenable','foldenable'),
        ('foldexpr','foldexpr'),
        ('foldignore','foldignore'),
        ('foldlevel','foldlevel'),
        ('foldlevelstart','foldlevelstart'),
        ('foldmarker','foldmarker'),
        ('foldmethod','foldmethod'),
        ('foldminlines','foldminlines'),
        ('foldnestmax','foldnestmax'),
        ('foldopen','foldopen'),
        ('foldtext','foldtext'),
        ('formatexpr','formatexpr'),
        ('formatlistpat','formatlistpat'),
        ('formatoptions','formatoptions'),
        ('formatprg','formatprg'),
        ('fp','fp'),
        ('fs','fs'),
        ('fsync','fsync'),
        ('ft','ft'),
        ('gcr','gcr'),
        ('gd','gd'),
        ('gdefault','gdefault'),
        ('gfm','gfm'),
        ('gfn','gfn'),
        ('gfs','gfs'),
        ('gfw','gfw'),
        ('ghr','ghr'),
        ('go','go'),
        ('gp','gp'),
        ('grepformat','grepformat'),
        ('grepprg','grepprg'),
        ('gtl','gtl'),
        ('gtt','gtt'),
        ('guicursor','guicursor'),
        ('guifont','guifont'),
        ('guifontset','guifontset'),
        ('guifontwide','guifontwide'),
        ('guiheadroom','guiheadroom'),
        ('guioptions','guioptions'),
        ('guipty','guipty'),
        ('guitablabel','guitablabel'),
        ('guitabtooltip','guitabtooltip'),
        ('helpfile','helpfile'),
        ('helpheight','helpheight'),
        ('helplang','helplang'),
        ('hf','hf'),
        ('hh','hh'),
        ('hi','hi'),
        ('hid','hid'),
        ('hidden','hidden'),
        ('highlight','highlight'),
        ('history','history'),
        ('hk','hk'),
        ('hkmap','hkmap'),
        ('hkmapp','hkmapp'),
        ('hkp','hkp'),
        ('hl','hl'),
        ('hlg','hlg'),
        ('hls','hls'),
        ('hlsearch','hlsearch'),
        ('ic','ic'),
        ('icon','icon'),
        ('iconstring','iconstring'),
        ('ignorecase','ignorecase'),
        ('im','im'),
        ('imactivatefunc','imactivatefunc'),
        ('imactivatekey','imactivatekey'),
        ('imaf','imaf'),
        ('imak','imak'),
        ('imc','imc'),
        ('imcmdline','imcmdline'),
        ('imd','imd'),
        ('imdisable','imdisable'),
        ('imi','imi'),
        ('iminsert','iminsert'),
        ('ims','ims'),
        ('imsearch','imsearch'),
        ('imsf','imsf'),
        ('imstatusfunc','imstatusfunc'),
        ('inc','inc'),
        ('include','include'),
        ('includeexpr','includeexpr'),
        ('incsearch','incsearch'),
        ('inde','inde'),
        ('indentexpr','indentexpr'),
        ('indentkeys','indentkeys'),
        ('indk','indk'),
        ('inex','inex'),
        ('inf','inf'),
        ('infercase','infercase'),
        ('inoremap','inoremap'),
        ('insertmode','insertmode'),
        ('invacd','invacd'),
        ('invai','invai'),
        ('invakm','invakm'),
        ('invallowrevins','invallowrevins'),
        ('invaltkeymap','invaltkeymap'),
        ('invanti','invanti'),
        ('invantialias','invantialias'),
        ('invar','invar'),
        ('invarab','invarab'),
        ('invarabic','invarabic'),
        ('invarabicshape','invarabicshape'),
        ('invari','invari'),
        ('invarshape','invarshape'),
        ('invautochdir','invautochdir'),
        ('invautoindent','invautoindent'),
        ('invautoread','invautoread'),
        ('invautowrite','invautowrite'),
        ('invautowriteall','invautowriteall'),
        ('invaw','invaw'),
        ('invawa','invawa'),
        ('invbackup','invbackup'),
        ('invballooneval','invballooneval'),
        ('invbeval','invbeval'),
        ('invbin','invbin'),
        ('invbinary','invbinary'),
        ('invbiosk','invbiosk'),
        ('invbioskey','invbioskey'),
        ('invbk','invbk'),
        ('invbl','invbl'),
        ('invbomb','invbomb'),
        ('invbuflisted','invbuflisted'),
        ('invcf','invcf'),
        ('invci','invci'),
        ('invcin','invcin'),
        ('invcindent','invcindent'),
        ('invcompatible','invcompatible'),
        ('invconfirm','invconfirm'),
        ('invconsk','invconsk'),
        ('invconskey','invconskey'),
        ('invcopyindent','invcopyindent'),
        ('invcp','invcp'),
        ('invcrb','invcrb'),
        ('invcscoperelative','invcscoperelative'),
        ('invcscopetag','invcscopetag'),
        ('invcscopeverbose','invcscopeverbose'),
        ('invcsre','invcsre'),
        ('invcst','invcst'),
        ('invcsverb','invcsverb'),
        ('invcuc','invcuc'),
        ('invcul','invcul'),
        ('invcursorbind','invcursorbind'),
        ('invcursorcolumn','invcursorcolumn'),
        ('invcursorline','invcursorline'),
        ('invdeco','invdeco'),
        ('invdelcombine','invdelcombine'),
        ('invdg','invdg'),
        ('invdiff','invdiff'),
        ('invdigraph','invdigraph'),
        ('invea','invea'),
        ('inveb','inveb'),
        ('inved','inved'),
        ('invedcompatible','invedcompatible'),
        ('invek','invek'),
        ('invendofline','invendofline'),
        ('inveol','inveol'),
        ('invequalalways','invequalalways'),
        ('inverrorbells','inverrorbells'),
        ('invesckeys','invesckeys'),
        ('invet','invet'),
        ('invex','invex'),
        ('invexpandtab','invexpandtab'),
        ('invexrc','invexrc'),
        ('invfen','invfen'),
        ('invfic','invfic'),
        ('invfileignorecase','invfileignorecase'),
        ('invfk','invfk'),
        ('invfkmap','invfkmap'),
        ('invfoldenable','invfoldenable'),
        ('invgd','invgd'),
        ('invgdefault','invgdefault'),
        ('invguipty','invguipty'),
        ('invhid','invhid'),
        ('invhidden','invhidden'),
        ('invhk','invhk'),
        ('invhkmap','invhkmap'),
        ('invhkmapp','invhkmapp'),
        ('invhkp','invhkp'),
        ('invhls','invhls'),
        ('invhlsearch','invhlsearch'),
        ('invic','invic'),
        ('invicon','invicon'),
        ('invignorecase','invignorecase'),
        ('invim','invim'),
        ('invimc','invimc'),
        ('invimcmdline','invimcmdline'),
        ('invimd','invimd'),
        ('invimdisable','invimdisable'),
        ('invincsearch','invincsearch'),
        ('invinf','invinf'),
        ('invinfercase','invinfercase'),
        ('invinsertmode','invinsertmode'),
        ('invis','invis'),
        ('invjoinspaces','invjoinspaces'),
        ('invjs','invjs'),
        ('invlazyredraw','invlazyredraw'),
        ('invlbr','invlbr'),
        ('invlinebreak','invlinebreak'),
        ('invlisp','invlisp'),
        ('invlist','invlist'),
        ('invloadplugins','invloadplugins'),
        ('invlpl','invlpl'),
        ('invlz','invlz'),
        ('invma','invma'),
        ('invmacatsui','invmacatsui'),
        ('invmagic','invmagic'),
        ('invmh','invmh'),
        ('invml','invml'),
        ('invmod','invmod'),
        ('invmodeline','invmodeline'),
        ('invmodifiable','invmodifiable'),
        ('invmodified','invmodified'),
        ('invmore','invmore'),
        ('invmousef','invmousef'),
        ('invmousefocus','invmousefocus'),
        ('invmousehide','invmousehide'),
        ('invnu','invnu'),
        ('invnumber','invnumber'),
        ('invodev','invodev'),
        ('invopendevice','invopendevice'),
        ('invpaste','invpaste'),
        ('invpi','invpi'),
        ('invpreserveindent','invpreserveindent'),
        ('invpreviewwindow','invpreviewwindow'),
        ('invprompt','invprompt'),
        ('invpvw','invpvw'),
        ('invreadonly','invreadonly'),
        ('invrelativenumber','invrelativenumber'),
        ('invremap','invremap'),
        ('invrestorescreen','invrestorescreen'),
        ('invrevins','invrevins'),
        ('invri','invri'),
        ('invrightleft','invrightleft'),
        ('invrl','invrl'),
        ('invrnu','invrnu'),
        ('invro','invro'),
        ('invrs','invrs'),
        ('invru','invru'),
        ('invruler','invruler'),
        ('invsb','invsb'),
        ('invsc','invsc'),
        ('invscb','invscb'),
        ('invscrollbind','invscrollbind'),
        ('invscs','invscs'),
        ('invsecure','invsecure'),
        ('invsft','invsft'),
        ('invshellslash','invshellslash'),
        ('invshelltemp','invshelltemp'),
        ('invshiftround','invshiftround'),
        ('invshortname','invshortname'),
        ('invshowcmd','invshowcmd'),
        ('invshowfulltag','invshowfulltag'),
        ('invshowmatch','invshowmatch'),
        ('invshowmode','invshowmode'),
        ('invsi','invsi'),
        ('invsm','invsm'),
        ('invsmartcase','invsmartcase'),
        ('invsmartindent','invsmartindent'),
        ('invsmarttab','invsmarttab'),
        ('invsmd','invsmd'),
        ('invsn','invsn'),
        ('invsol','invsol'),
        ('invspell','invspell'),
        ('invsplitbelow','invsplitbelow'),
        ('invsplitright','invsplitright'),
        ('invspr','invspr'),
        ('invsr','invsr'),
        ('invssl','invssl'),
        ('invsta','invsta'),
        ('invstartofline','invstartofline'),
        ('invstmp','invstmp'),
        ('invswapfile','invswapfile'),
        ('invswf','invswf'),
        ('invta','invta'),
        ('invtagbsearch','invtagbsearch'),
        ('invtagrelative','invtagrelative'),
        ('invtagstack','invtagstack'),
        ('invtbi','invtbi'),
        ('invtbidi','invtbidi'),
        ('invtbs','invtbs'),
        ('invtermbidi','invtermbidi'),
        ('invterse','invterse'),
        ('invtextauto','invtextauto'),
        ('invtextmode','invtextmode'),
        ('invtf','invtf'),
        ('invtgst','invtgst'),
        ('invtildeop','invtildeop'),
        ('invtimeout','invtimeout'),
        ('invtitle','invtitle'),
        ('invto','invto'),
        ('invtop','invtop'),
        ('invtr','invtr'),
        ('invttimeout','invttimeout'),
        ('invttybuiltin','invttybuiltin'),
        ('invttyfast','invttyfast'),
        ('invtx','invtx'),
        ('invudf','invudf'),
        ('invundofile','invundofile'),
        ('invvb','invvb'),
        ('invvisualbell','invvisualbell'),
        ('invwa','invwa'),
        ('invwarn','invwarn'),
        ('invwb','invwb'),
        ('invweirdinvert','invweirdinvert'),
        ('invwfh','invwfh'),
        ('invwfw','invwfw'),
        ('invwic','invwic'),
        ('invwildignorecase','invwildignorecase'),
        ('invwildmenu','invwildmenu'),
        ('invwinfixheight','invwinfixheight'),
        ('invwinfixwidth','invwinfixwidth'),
        ('invwiv','invwiv'),
        ('invwmnu','invwmnu'),
        ('invwrap','invwrap'),
        ('invwrapscan','invwrapscan'),
        ('invwrite','invwrite'),
        ('invwriteany','invwriteany'),
        ('invwritebackup','invwritebackup'),
        ('invws','invws'),
        ('is','is'),
        ('isf','isf'),
        ('isfname','isfname'),
        ('isi','isi'),
        ('isident','isident'),
        ('isk','isk'),
        ('iskeyword','iskeyword'),
        ('isp','isp'),
        ('isprint','isprint'),
        ('joinspaces','joinspaces'),
        ('js','js'),
        ('key','key'),
        ('keymap','keymap'),
        ('keymodel','keymodel'),
        ('keywordprg','keywordprg'),
        ('km','km'),
        ('kmp','kmp'),
        ('kp','kp'),
        ('langmap','langmap'),
        ('langmenu','langmenu'),
        ('laststatus','laststatus'),
        ('lazyredraw','lazyredraw'),
        ('lbr','lbr'),
        ('lcs','lcs'),
        ('linebreak','linebreak'),
        ('lines','lines'),
        ('linespace','linespace'),
        ('lisp','lisp'),
        ('lispwords','lispwords'),
        ('list','list'),
        ('listchars','listchars'),
        ('lm','lm'),
        ('lmap','lmap'),
        ('loadplugins','loadplugins'),
        ('lpl','lpl'),
        ('ls','ls'),
        ('lsp','lsp'),
        ('lw','lw'),
        ('lz','lz'),
        ('ma','ma'),
        ('macatsui','macatsui'),
        ('magic','magic'),
        ('makeef','makeef'),
        ('makeprg','makeprg'),
        ('mat','mat'),
        ('matchpairs','matchpairs'),
        ('matchtime','matchtime'),
        ('maxcombine','maxcombine'),
        ('maxfuncdepth','maxfuncdepth'),
        ('maxmapdepth','maxmapdepth'),
        ('maxmem','maxmem'),
        ('maxmempattern','maxmempattern'),
        ('maxmemtot','maxmemtot'),
        ('mco','mco'),
        ('mef','mef'),
        ('menuitems','menuitems'),
        ('mfd','mfd'),
        ('mh','mh'),
        ('mis','mis'),
        ('mkspellmem','mkspellmem'),
        ('ml','ml'),
        ('mls','mls'),
        ('mm','mm'),
        ('mmd','mmd'),
        ('mmp','mmp'),
        ('mmt','mmt'),
        ('mod','mod'),
        ('modeline','modeline'),
        ('modelines','modelines'),
        ('modifiable','modifiable'),
        ('modified','modified'),
        ('more','more'),
        ('mouse','mouse'),
        ('mousef','mousef'),
        ('mousefocus','mousefocus'),
        ('mousehide','mousehide'),
        ('mousem','mousem'),
        ('mousemodel','mousemodel'),
        ('mouses','mouses'),
        ('mouseshape','mouseshape'),
        ('mouset','mouset'),
        ('mousetime','mousetime'),
        ('mp','mp'),
        ('mps','mps'),
        ('msm','msm'),
        ('mzq','mzq'),
        ('mzquantum','mzquantum'),
        ('nf','nf'),
        ('nnoremap','nnoremap'),
        ('noacd','noacd'),
        ('noai','noai'),
        ('noakm','noakm'),
        ('noallowrevins','noallowrevins'),
        ('noaltkeymap','noaltkeymap'),
        ('noanti','noanti'),
        ('noantialias','noantialias'),
        ('noar','noar'),
        ('noarab','noarab'),
        ('noarabic','noarabic'),
        ('noarabicshape','noarabicshape'),
        ('noari','noari'),
        ('noarshape','noarshape'),
        ('noautochdir','noautochdir'),
        ('noautoindent','noautoindent'),
        ('noautoread','noautoread'),
        ('noautowrite','noautowrite'),
        ('noautowriteall','noautowriteall'),
        ('noaw','noaw'),
        ('noawa','noawa'),
        ('nobackup','nobackup'),
        ('noballooneval','noballooneval'),
        ('nobeval','nobeval'),
        ('nobin','nobin'),
        ('nobinary','nobinary'),
        ('nobiosk','nobiosk'),
        ('nobioskey','nobioskey'),
        ('nobk','nobk'),
        ('nobl','nobl'),
        ('nobomb','nobomb'),
        ('nobuflisted','nobuflisted'),
        ('nocf','nocf'),
        ('noci','noci'),
        ('nocin','nocin'),
        ('nocindent','nocindent'),
        ('nocompatible','nocompatible'),
        ('noconfirm','noconfirm'),
        ('noconsk','noconsk'),
        ('noconskey','noconskey'),
        ('nocopyindent','nocopyindent'),
        ('nocp','nocp'),
        ('nocrb','nocrb'),
        ('nocscoperelative','nocscoperelative'),
        ('nocscopetag','nocscopetag'),
        ('nocscopeverbose','nocscopeverbose'),
        ('nocsre','nocsre'),
        ('nocst','nocst'),
        ('nocsverb','nocsverb'),
        ('nocuc','nocuc'),
        ('nocul','nocul'),
        ('nocursorbind','nocursorbind'),
        ('nocursorcolumn','nocursorcolumn'),
        ('nocursorline','nocursorline'),
        ('nodeco','nodeco'),
        ('nodelcombine','nodelcombine'),
        ('nodg','nodg'),
        ('nodiff','nodiff'),
        ('nodigraph','nodigraph'),
        ('noea','noea'),
        ('noeb','noeb'),
        ('noed','noed'),
        ('noedcompatible','noedcompatible'),
        ('noek','noek'),
        ('noendofline','noendofline'),
        ('noeol','noeol'),
        ('noequalalways','noequalalways'),
        ('noerrorbells','noerrorbells'),
        ('noesckeys','noesckeys'),
        ('noet','noet'),
        ('noex','noex'),
        ('noexpandtab','noexpandtab'),
        ('noexrc','noexrc'),
        ('nofen','nofen'),
        ('nofic','nofic'),
        ('nofileignorecase','nofileignorecase'),
        ('nofk','nofk'),
        ('nofkmap','nofkmap'),
        ('nofoldenable','nofoldenable'),
        ('nogd','nogd'),
        ('nogdefault','nogdefault'),
        ('noguipty','noguipty'),
        ('nohid','nohid'),
        ('nohidden','nohidden'),
        ('nohk','nohk'),
        ('nohkmap','nohkmap'),
        ('nohkmapp','nohkmapp'),
        ('nohkp','nohkp'),
        ('nohls','nohls'),
        ('nohlsearch','nohlsearch'),
        ('noic','noic'),
        ('noicon','noicon'),
        ('noignorecase','noignorecase'),
        ('noim','noim'),
        ('noimc','noimc'),
        ('noimcmdline','noimcmdline'),
        ('noimd','noimd'),
        ('noimdisable','noimdisable'),
        ('noincsearch','noincsearch'),
        ('noinf','noinf'),
        ('noinfercase','noinfercase'),
        ('noinsertmode','noinsertmode'),
        ('nois','nois'),
        ('nojoinspaces','nojoinspaces'),
        ('nojs','nojs'),
        ('nolazyredraw','nolazyredraw'),
        ('nolbr','nolbr'),
        ('nolinebreak','nolinebreak'),
        ('nolisp','nolisp'),
        ('nolist','nolist'),
        ('noloadplugins','noloadplugins'),
        ('nolpl','nolpl'),
        ('nolz','nolz'),
        ('noma','noma'),
        ('nomacatsui','nomacatsui'),
        ('nomagic','nomagic'),
        ('nomh','nomh'),
        ('noml','noml'),
        ('nomod','nomod'),
        ('nomodeline','nomodeline'),
        ('nomodifiable','nomodifiable'),
        ('nomodified','nomodified'),
        ('nomore','nomore'),
        ('nomousef','nomousef'),
        ('nomousefocus','nomousefocus'),
        ('nomousehide','nomousehide'),
        ('nonu','nonu'),
        ('nonumber','nonumber'),
        ('noodev','noodev'),
        ('noopendevice','noopendevice'),
        ('nopaste','nopaste'),
        ('nopi','nopi'),
        ('nopreserveindent','nopreserveindent'),
        ('nopreviewwindow','nopreviewwindow'),
        ('noprompt','noprompt'),
        ('nopvw','nopvw'),
        ('noreadonly','noreadonly'),
        ('norelativenumber','norelativenumber'),
        ('noremap','noremap'),
        ('norestorescreen','norestorescreen'),
        ('norevins','norevins'),
        ('nori','nori'),
        ('norightleft','norightleft'),
        ('norl','norl'),
        ('nornu','nornu'),
        ('noro','noro'),
        ('nors','nors'),
        ('noru','noru'),
        ('noruler','noruler'),
        ('nosb','nosb'),
        ('nosc','nosc'),
        ('noscb','noscb'),
        ('noscrollbind','noscrollbind'),
        ('noscs','noscs'),
        ('nosecure','nosecure'),
        ('nosft','nosft'),
        ('noshellslash','noshellslash'),
        ('noshelltemp','noshelltemp'),
        ('noshiftround','noshiftround'),
        ('noshortname','noshortname'),
        ('noshowcmd','noshowcmd'),
        ('noshowfulltag','noshowfulltag'),
        ('noshowmatch','noshowmatch'),
        ('noshowmode','noshowmode'),
        ('nosi','nosi'),
        ('nosm','nosm'),
        ('nosmartcase','nosmartcase'),
        ('nosmartindent','nosmartindent'),
        ('nosmarttab','nosmarttab'),
        ('nosmd','nosmd'),
        ('nosn','nosn'),
        ('nosol','nosol'),
        ('nospell','nospell'),
        ('nosplitbelow','nosplitbelow'),
        ('nosplitright','nosplitright'),
        ('nospr','nospr'),
        ('nosr','nosr'),
        ('nossl','nossl'),
        ('nosta','nosta'),
        ('nostartofline','nostartofline'),
        ('nostmp','nostmp'),
        ('noswapfile','noswapfile'),
        ('noswf','noswf'),
        ('nota','nota'),
        ('notagbsearch','notagbsearch'),
        ('notagrelative','notagrelative'),
        ('notagstack','notagstack'),
        ('notbi','notbi'),
        ('notbidi','notbidi'),
        ('notbs','notbs'),
        ('notermbidi','notermbidi'),
        ('noterse','noterse'),
        ('notextauto','notextauto'),
        ('notextmode','notextmode'),
        ('notf','notf'),
        ('notgst','notgst'),
        ('notildeop','notildeop'),
        ('notimeout','notimeout'),
        ('notitle','notitle'),
        ('noto','noto'),
        ('notop','notop'),
        ('notr','notr'),
        ('nottimeout','nottimeout'),
        ('nottybuiltin','nottybuiltin'),
        ('nottyfast','nottyfast'),
        ('notx','notx'),
        ('noudf','noudf'),
        ('noundofile','noundofile'),
        ('novb','novb'),
        ('novisualbell','novisualbell'),
        ('nowa','nowa'),
        ('nowarn','nowarn'),
        ('nowb','nowb'),
        ('noweirdinvert','noweirdinvert'),
        ('nowfh','nowfh'),
        ('nowfw','nowfw'),
        ('nowic','nowic'),
        ('nowildignorecase','nowildignorecase'),
        ('nowildmenu','nowildmenu'),
        ('nowinfixheight','nowinfixheight'),
        ('nowinfixwidth','nowinfixwidth'),
        ('nowiv','nowiv'),
        ('nowmnu','nowmnu'),
        ('nowrap','nowrap'),
        ('nowrapscan','nowrapscan'),
        ('nowrite','nowrite'),
        ('nowriteany','nowriteany'),
        ('nowritebackup','nowritebackup'),
        ('nows','nows'),
        ('nrformats','nrformats'),
        ('nu','nu'),
        ('number','number'),
        ('numberwidth','numberwidth'),
        ('nuw','nuw'),
        ('odev','odev'),
        ('oft','oft'),
        ('ofu','ofu'),
        ('omnifunc','omnifunc'),
        ('opendevice','opendevice'),
        ('operatorfunc','operatorfunc'),
        ('opfunc','opfunc'),
        ('osfiletype','osfiletype'),
        ('pa','pa'),
        ('para','para'),
        ('paragraphs','paragraphs'),
        ('paste','paste'),
        ('pastetoggle','pastetoggle'),
        ('patchexpr','patchexpr'),
        ('patchmode','patchmode'),
        ('path','path'),
        ('pdev','pdev'),
        ('penc','penc'),
        ('pex','pex'),
        ('pexpr','pexpr'),
        ('pfn','pfn'),
        ('ph','ph'),
        ('pheader','pheader'),
        ('pi','pi'),
        ('pm','pm'),
        ('pmbcs','pmbcs'),
        ('pmbfn','pmbfn'),
        ('popt','popt'),
        ('preserveindent','preserveindent'),
        ('previewheight','previewheight'),
        ('previewwindow','previewwindow'),
        ('printdevice','printdevice'),
        ('printencoding','printencoding'),
        ('printexpr','printexpr'),
        ('printfont','printfont'),
        ('printheader','printheader'),
        ('printmbcharset','printmbcharset'),
        ('printmbfont','printmbfont'),
        ('printoptions','printoptions'),
        ('prompt','prompt'),
        ('pt','pt'),
        ('pumheight','pumheight'),
        ('pvh','pvh'),
        ('pvw','pvw'),
        ('qe','qe'),
        ('quoteescape','quoteescape'),
        ('rdt','rdt'),
        ('re','re'),
        ('readonly','readonly'),
        ('redrawtime','redrawtime'),
        ('regexpengine','regexpengine'),
        ('relativenumber','relativenumber'),
        ('remap','remap'),
        ('report','report'),
        ('restorescreen','restorescreen'),
        ('revins','revins'),
        ('ri','ri'),
        ('rightleft','rightleft'),
        ('rightleftcmd','rightleftcmd'),
        ('rl','rl'),
        ('rlc','rlc'),
        ('rnu','rnu'),
        ('ro','ro'),
        ('rs','rs'),
        ('rtp','rtp'),
        ('ru','ru'),
        ('ruf','ruf'),
        ('ruler','ruler'),
        ('rulerformat','rulerformat'),
        ('runtimepath','runtimepath'),
        ('sb','sb'),
        ('sbo','sbo'),
        ('sbr','sbr'),
        ('sc','sc'),
        ('scb','scb'),
        ('scr','scr'),
        ('scroll','scroll'),
        ('scrollbind','scrollbind'),
        ('scrolljump','scrolljump'),
        ('scrolloff','scrolloff'),
        ('scrollopt','scrollopt'),
        ('scs','scs'),
        ('sect','sect'),
        ('sections','sections'),
        ('secure','secure'),
        ('sel','sel'),
        ('selection','selection'),
        ('selectmode','selectmode'),
        ('sessionoptions','sessionoptions'),
        ('sft','sft'),
        ('sh','sh'),
        ('shcf','shcf'),
        ('shell','shell'),
        ('shellcmdflag','shellcmdflag'),
        ('shellpipe','shellpipe'),
        ('shellquote','shellquote'),
        ('shellredir','shellredir'),
        ('shellslash','shellslash'),
        ('shelltemp','shelltemp'),
        ('shelltype','shelltype'),
        ('shellxescape','shellxescape'),
        ('shellxquote','shellxquote'),
        ('shiftround','shiftround'),
        ('shiftwidth','shiftwidth'),
        ('shm','shm'),
        ('shortmess','shortmess'),
        ('shortname','shortname'),
        ('showbreak','showbreak'),
        ('showcmd','showcmd'),
        ('showfulltag','showfulltag'),
        ('showmatch','showmatch'),
        ('showmode','showmode'),
        ('showtabline','showtabline'),
        ('shq','shq'),
        ('si','si'),
        ('sidescroll','sidescroll'),
        ('sidescrolloff','sidescrolloff'),
        ('siso','siso'),
        ('sj','sj'),
        ('slm','slm'),
        ('sm','sm'),
        ('smartcase','smartcase'),
        ('smartindent','smartindent'),
        ('smarttab','smarttab'),
        ('smc','smc'),
        ('smd','smd'),
        ('sn','sn'),
        ('so','so'),
        ('softtabstop','softtabstop'),
        ('sol','sol'),
        ('sp','sp'),
        ('spc','spc'),
        ('spell','spell'),
        ('spellcapcheck','spellcapcheck'),
        ('spellfile','spellfile'),
        ('spelllang','spelllang'),
        ('spellsuggest','spellsuggest'),
        ('spf','spf'),
        ('spl','spl'),
        ('splitbelow','splitbelow'),
        ('splitright','splitright'),
        ('spr','spr'),
        ('sps','sps'),
        ('sr','sr'),
        ('srr','srr'),
        ('ss','ss'),
        ('ssl','ssl'),
        ('ssop','ssop'),
        ('st','st'),
        ('sta','sta'),
        ('stal','stal'),
        ('startofline','startofline'),
        ('statusline','statusline'),
        ('stl','stl'),
        ('stmp','stmp'),
        ('sts','sts'),
        ('su','su'),
        ('sua','sua'),
        ('suffixes','suffixes'),
        ('suffixesadd','suffixesadd'),
        ('sw','sw'),
        ('swapfile','swapfile'),
        ('swapsync','swapsync'),
        ('swb','swb'),
        ('swf','swf'),
        ('switchbuf','switchbuf'),
        ('sws','sws'),
        ('sxe','sxe'),
        ('sxq','sxq'),
        ('syn','syn'),
        ('synmaxcol','synmaxcol'),
        ('syntax','syntax'),
        ('t_AB','t_AB'),
        ('t_AF','t_AF'),
        ('t_AL','t_AL'),
        ('t_CS','t_CS'),
        ('t_CV','t_CV'),
        ('t_Ce','t_Ce'),
        ('t_Co','t_Co'),
        ('t_Cs','t_Cs'),
        ('t_DL','t_DL'),
        ('t_EI','t_EI'),
        ('t_F1','t_F1'),
        ('t_F2','t_F2'),
        ('t_F3','t_F3'),
        ('t_F4','t_F4'),
        ('t_F5','t_F5'),
        ('t_F6','t_F6'),
        ('t_F7','t_F7'),
        ('t_F8','t_F8'),
        ('t_F9','t_F9'),
        ('t_IE','t_IE'),
        ('t_IS','t_IS'),
        ('t_K1','t_K1'),
        ('t_K3','t_K3'),
        ('t_K4','t_K4'),
        ('t_K5','t_K5'),
        ('t_K6','t_K6'),
        ('t_K7','t_K7'),
        ('t_K8','t_K8'),
        ('t_K9','t_K9'),
        ('t_KA','t_KA'),
        ('t_KB','t_KB'),
        ('t_KC','t_KC'),
        ('t_KD','t_KD'),
        ('t_KE','t_KE'),
        ('t_KF','t_KF'),
        ('t_KG','t_KG'),
        ('t_KH','t_KH'),
        ('t_KI','t_KI'),
        ('t_KJ','t_KJ'),
        ('t_KK','t_KK'),
        ('t_KL','t_KL'),
        ('t_RI','t_RI'),
        ('t_RV','t_RV'),
        ('t_SI','t_SI'),
        ('t_Sb','t_Sb'),
        ('t_Sf','t_Sf'),
        ('t_WP','t_WP'),
        ('t_WS','t_WS'),
        ('t_ZH','t_ZH'),
        ('t_ZR','t_ZR'),
        ('t_al','t_al'),
        ('t_bc','t_bc'),
        ('t_cd','t_cd'),
        ('t_ce','t_ce'),
        ('t_cl','t_cl'),
        ('t_cm','t_cm'),
        ('t_cs','t_cs'),
        ('t_da','t_da'),
        ('t_db','t_db'),
        ('t_dl','t_dl'),
        ('t_fs','t_fs'),
        ('t_k1','t_k1'),
        ('t_k2','t_k2'),
        ('t_k3','t_k3'),
        ('t_k4','t_k4'),
        ('t_k5','t_k5'),
        ('t_k6','t_k6'),
        ('t_k7','t_k7'),
        ('t_k8','t_k8'),
        ('t_k9','t_k9'),
        ('t_kB','t_kB'),
        ('t_kD','t_kD'),
        ('t_kI','t_kI'),
        ('t_kN','t_kN'),
        ('t_kP','t_kP'),
        ('t_kb','t_kb'),
        ('t_kd','t_kd'),
        ('t_ke','t_ke'),
        ('t_kh','t_kh'),
        ('t_kl','t_kl'),
        ('t_kr','t_kr'),
        ('t_ks','t_ks'),
        ('t_ku','t_ku'),
        ('t_le','t_le'),
        ('t_mb','t_mb'),
        ('t_md','t_md'),
        ('t_me','t_me'),
        ('t_mr','t_mr'),
        ('t_ms','t_ms'),
        ('t_nd','t_nd'),
        ('t_op','t_op'),
        ('t_se','t_se'),
        ('t_so','t_so'),
        ('t_sr','t_sr'),
        ('t_te','t_te'),
        ('t_ti','t_ti'),
        ('t_ts','t_ts'),
        ('t_u7','t_u7'),
        ('t_ue','t_ue'),
        ('t_us','t_us'),
        ('t_ut','t_ut'),
        ('t_vb','t_vb'),
        ('t_ve','t_ve'),
        ('t_vi','t_vi'),
        ('t_vs','t_vs'),
        ('t_xs','t_xs'),
        ('ta','ta'),
        ('tabline','tabline'),
        ('tabpagemax','tabpagemax'),
        ('tabstop','tabstop'),
        ('tag','tag'),
        ('tagbsearch','tagbsearch'),
        ('taglength','taglength'),
        ('tagrelative','tagrelative'),
        ('tags','tags'),
        ('tagstack','tagstack'),
        ('tal','tal'),
        ('tb','tb'),
        ('tbi','tbi'),
        ('tbidi','tbidi'),
        ('tbis','tbis'),
        ('tbs','tbs'),
        ('tenc','tenc'),
        ('term','term'),
        ('termbidi','termbidi'),
        ('termencoding','termencoding'),
        ('terse','terse'),
        ('textauto','textauto'),
        ('textmode','textmode'),
        ('textwidth','textwidth'),
        ('tf','tf'),
        ('tgst','tgst'),
        ('thesaurus','thesaurus'),
        ('tildeop','tildeop'),
        ('timeout','timeout'),
        ('timeoutlen','timeoutlen'),
        ('title','title'),
        ('titlelen','titlelen'),
        ('titleold','titleold'),
        ('titlestring','titlestring'),
        ('tl','tl'),
        ('tm','tm'),
        ('to','to'),
        ('toolbar','toolbar'),
        ('toolbariconsize','toolbariconsize'),
        ('top','top'),
        ('tpm','tpm'),
        ('tr','tr'),
        ('ts','ts'),
        ('tsl','tsl'),
        ('tsr','tsr'),
        ('ttimeout','ttimeout'),
        ('ttimeoutlen','ttimeoutlen'),
        ('ttm','ttm'),
        ('tty','tty'),
        ('ttybuiltin','ttybuiltin'),
        ('ttyfast','ttyfast'),
        ('ttym','ttym'),
        ('ttymouse','ttymouse'),
        ('ttyscroll','ttyscroll'),
        ('ttytype','ttytype'),
        ('tw','tw'),
        ('tx','tx'),
        ('uc','uc'),
        ('udf','udf'),
        ('udir','udir'),
        ('ul','ul'),
        ('undodir','undodir'),
        ('undofile','undofile'),
        ('undolevels','undolevels'),
        ('undoreload','undoreload'),
        ('updatecount','updatecount'),
        ('updatetime','updatetime'),
        ('ur','ur'),
        ('ut','ut'),
        ('vb','vb'),
        ('vbs','vbs'),
        ('vdir','vdir'),
        ('ve','ve'),
        ('verbose','verbose'),
        ('verbosefile','verbosefile'),
        ('vfile','vfile'),
        ('vi','vi'),
        ('viewdir','viewdir'),
        ('viewoptions','viewoptions'),
        ('viminfo','viminfo'),
        ('virtualedit','virtualedit'),
        ('visualbell','visualbell'),
        ('vnoremap','vnoremap'),
        ('vop','vop'),
        ('wa','wa'),
        ('wak','wak'),
        ('warn','warn'),
        ('wb','wb'),
        ('wc','wc'),
        ('wcm','wcm'),
        ('wd','wd'),
        ('weirdinvert','weirdinvert'),
        ('wfh','wfh'),
        ('wfw','wfw'),
        ('wh','wh'),
        ('whichwrap','whichwrap'),
        ('wi','wi'),
        ('wic','wic'),
        ('wig','wig'),
        ('wildchar','wildchar'),
        ('wildcharm','wildcharm'),
        ('wildignore','wildignore'),
        ('wildignorecase','wildignorecase'),
        ('wildmenu','wildmenu'),
        ('wildmode','wildmode'),
        ('wildoptions','wildoptions'),
        ('wim','wim'),
        ('winaltkeys','winaltkeys'),
        ('window','window'),
        ('winfixheight','winfixheight'),
        ('winfixwidth','winfixwidth'),
        ('winheight','winheight'),
        ('winminheight','winminheight'),
        ('winminwidth','winminwidth'),
        ('winwidth','winwidth'),
        ('wiv','wiv'),
        ('wiw','wiw'),
        ('wm','wm'),
        ('wmh','wmh'),
        ('wmnu','wmnu'),
        ('wmw','wmw'),
        ('wop','wop'),
        ('wrap','wrap'),
        ('wrapmargin','wrapmargin'),
        ('wrapscan','wrapscan'),
        ('write','write'),
        ('writeany','writeany'),
        ('writebackup','writebackup'),
        ('writedelay','writedelay'),
        ('ws','ws'),
        ('ww','ww'),
    )
    return var
option = _getoption()


# === NexusCore/openenv\Lib\site-packages\openai\resources\beta\threads\threads.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import typing_extensions
from typing import Union, Iterable, Optional
from functools import partial
from typing_extensions import Literal, overload

import httpx

from .... import _legacy_response
from .messages import (
    Messages,
    AsyncMessages,
    MessagesWithRawResponse,
    AsyncMessagesWithRawResponse,
    MessagesWithStreamingResponse,
    AsyncMessagesWithStreamingResponse,
)
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import required_args, maybe_transform, async_maybe_transform
from .runs.runs import (
    Runs,
    AsyncRuns,
    RunsWithRawResponse,
    AsyncRunsWithRawResponse,
    RunsWithStreamingResponse,
    AsyncRunsWithStreamingResponse,
)
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ...._streaming import Stream, AsyncStream
from ....types.beta import (
    thread_create_params,
    thread_update_params,
    thread_create_and_run_params,
)
from ...._base_client import make_request_options
from ....lib.streaming import (
    AssistantEventHandler,
    AssistantEventHandlerT,
    AssistantStreamManager,
    AsyncAssistantEventHandler,
    AsyncAssistantEventHandlerT,
    AsyncAssistantStreamManager,
)
from ....types.beta.thread import Thread
from ....types.beta.threads.run import Run
from ....types.shared.chat_model import ChatModel
from ....types.beta.thread_deleted import ThreadDeleted
from ....types.shared_params.metadata import Metadata
from ....types.beta.assistant_tool_param import AssistantToolParam
from ....types.beta.assistant_stream_event import AssistantStreamEvent
from ....types.beta.assistant_tool_choice_option_param import AssistantToolChoiceOptionParam
from ....types.beta.assistant_response_format_option_param import AssistantResponseFormatOptionParam

__all__ = ["Threads", "AsyncThreads"]


class Threads(SyncAPIResource):
    @cached_property
    def runs(self) -> Runs:
        return Runs(self._client)

    @cached_property
    def messages(self) -> Messages:
        return Messages(self._client)

    @cached_property
    def with_raw_response(self) -> ThreadsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return ThreadsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> ThreadsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return ThreadsWithStreamingResponse(self)

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def create(
        self,
        *,
        messages: Iterable[thread_create_params.Message] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_params.ToolResources] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Thread:
        """
        Create a thread.

        Args:
          messages: A list of [messages](https://platform.openai.com/docs/api-reference/messages) to
              start the thread with.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          tool_resources: A set of resources that are made available to the assistant's tools in this
              thread. The resources are specific to the type of tool. For example, the
              `code_interpreter` tool requires a list of file IDs, while the `file_search`
              tool requires a list of vector store IDs.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            "/threads",
            body=maybe_transform(
                {
                    "messages": messages,
                    "metadata": metadata,
                    "tool_resources": tool_resources,
                },
                thread_create_params.ThreadCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Thread,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def retrieve(
        self,
        thread_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Thread:
        """
        Retrieves a thread.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get(
            f"/threads/{thread_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Thread,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def update(
        self,
        thread_id: str,
        *,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_update_params.ToolResources] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Thread:
        """
        Modifies a thread.

        Args:
          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          tool_resources: A set of resources that are made available to the assistant's tools in this
              thread. The resources are specific to the type of tool. For example, the
              `code_interpreter` tool requires a list of file IDs, while the `file_search`
              tool requires a list of vector store IDs.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            f"/threads/{thread_id}",
            body=maybe_transform(
                {
                    "metadata": metadata,
                    "tool_resources": tool_resources,
                },
                thread_update_params.ThreadUpdateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Thread,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def delete(
        self,
        thread_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ThreadDeleted:
        """
        Delete a thread.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._delete(
            f"/threads/{thread_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ThreadDeleted,
        )

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def create_and_run(
        self,
        *,
        assistant_id: str,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        Create a thread and run it in one request.

        Args:
          assistant_id: The ID of the
              [assistant](https://platform.openai.com/docs/api-reference/assistants) to use to
              execute this run.

          instructions: Override the default system message of the assistant. This is useful for
              modifying the behavior on a per-run basis.

          max_completion_tokens: The maximum number of completion tokens that may be used over the course of the
              run. The run will make a best effort to use only the number of completion tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              completion tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          max_prompt_tokens: The maximum number of prompt tokens that may be used over the course of the run.
              The run will make a best effort to use only the number of prompt tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              prompt tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: The ID of the [Model](https://platform.openai.com/docs/api-reference/models) to
              be used to execute this run. If a value is provided here, it will override the
              model associated with the assistant. If not, the model associated with the
              assistant will be used.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          thread: Options to create a new thread. If no thread is provided when running a request,
              an empty thread will be created.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tools and instead generates a message. `auto` is the default value
              and means the model can pick between generating a message or calling one or more
              tools. `required` means the model must call one or more tools before responding
              to the user. Specifying a particular tool like `{"type": "file_search"}` or
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

          tool_resources: A set of resources that are used by the assistant's tools. The resources are
              specific to the type of tool. For example, the `code_interpreter` tool requires
              a list of file IDs, while the `file_search` tool requires a list of vector store
              IDs.

          tools: Override the tools the assistant can use for this run. This is useful for
              modifying the behavior on a per-run basis.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          truncation_strategy: Controls for how a thread will be truncated prior to the run. Use this to
              control the intial context window of the run.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def create_and_run(
        self,
        *,
        assistant_id: str,
        stream: Literal[True],
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Stream[AssistantStreamEvent]:
        """
        Create a thread and run it in one request.

        Args:
          assistant_id: The ID of the
              [assistant](https://platform.openai.com/docs/api-reference/assistants) to use to
              execute this run.

          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          instructions: Override the default system message of the assistant. This is useful for
              modifying the behavior on a per-run basis.

          max_completion_tokens: The maximum number of completion tokens that may be used over the course of the
              run. The run will make a best effort to use only the number of completion tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              completion tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          max_prompt_tokens: The maximum number of prompt tokens that may be used over the course of the run.
              The run will make a best effort to use only the number of prompt tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              prompt tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: The ID of the [Model](https://platform.openai.com/docs/api-reference/models) to
              be used to execute this run. If a value is provided here, it will override the
              model associated with the assistant. If not, the model associated with the
              assistant will be used.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          thread: Options to create a new thread. If no thread is provided when running a request,
              an empty thread will be created.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tools and instead generates a message. `auto` is the default value
              and means the model can pick between generating a message or calling one or more
              tools. `required` means the model must call one or more tools before responding
              to the user. Specifying a particular tool like `{"type": "file_search"}` or
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

          tool_resources: A set of resources that are used by the assistant's tools. The resources are
              specific to the type of tool. For example, the `code_interpreter` tool requires
              a list of file IDs, while the `file_search` tool requires a list of vector store
              IDs.

          tools: Override the tools the assistant can use for this run. This is useful for
              modifying the behavior on a per-run basis.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          truncation_strategy: Controls for how a thread will be truncated prior to the run. Use this to
              control the intial context window of the run.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def create_and_run(
        self,
        *,
        assistant_id: str,
        stream: bool,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run | Stream[AssistantStreamEvent]:
        """
        Create a thread and run it in one request.

        Args:
          assistant_id: The ID of the
              [assistant](https://platform.openai.com/docs/api-reference/assistants) to use to
              execute this run.

          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          instructions: Override the default system message of the assistant. This is useful for
              modifying the behavior on a per-run basis.

          max_completion_tokens: The maximum number of completion tokens that may be used over the course of the
              run. The run will make a best effort to use only the number of completion tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              completion tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          max_prompt_tokens: The maximum number of prompt tokens that may be used over the course of the run.
              The run will make a best effort to use only the number of prompt tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              prompt tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: The ID of the [Model](https://platform.openai.com/docs/api-reference/models) to
              be used to execute this run. If a value is provided here, it will override the
              model associated with the assistant. If not, the model associated with the
              assistant will be used.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          thread: Options to create a new thread. If no thread is provided when running a request,
              an empty thread will be created.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tools and instead generates a message. `auto` is the default value
              and means the model can pick between generating a message or calling one or more
              tools. `required` means the model must call one or more tools before responding
              to the user. Specifying a particular tool like `{"type": "file_search"}` or
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

          tool_resources: A set of resources that are used by the assistant's tools. The resources are
              specific to the type of tool. For example, the `code_interpreter` tool requires
              a list of file IDs, while the `file_search` tool requires a list of vector store
              IDs.

          tools: Override the tools the assistant can use for this run. This is useful for
              modifying the behavior on a per-run basis.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          truncation_strategy: Controls for how a thread will be truncated prior to the run. Use this to
              control the intial context window of the run.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    @required_args(["assistant_id"], ["assistant_id", "stream"])
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def create_and_run(
        self,
        *,
        assistant_id: str,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run | Stream[AssistantStreamEvent]:
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            "/threads/runs",
            body=maybe_transform(
                {
                    "assistant_id": assistant_id,
                    "instructions": instructions,
                    "max_completion_tokens": max_completion_tokens,
                    "max_prompt_tokens": max_prompt_tokens,
                    "metadata": metadata,
                    "model": model,
                    "parallel_tool_calls": parallel_tool_calls,
                    "response_format": response_format,
                    "stream": stream,
                    "temperature": temperature,
                    "thread": thread,
                    "tool_choice": tool_choice,
                    "tool_resources": tool_resources,
                    "tools": tools,
                    "top_p": top_p,
                    "truncation_strategy": truncation_strategy,
                },
                thread_create_and_run_params.ThreadCreateAndRunParamsStreaming
                if stream
                else thread_create_and_run_params.ThreadCreateAndRunParamsNonStreaming,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
            stream=stream or False,
            stream_cls=Stream[AssistantStreamEvent],
        )

    def create_and_run_poll(
        self,
        *,
        assistant_id: str,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        poll_interval_ms: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        A helper to create a thread, start a run and then poll for a terminal state.
        More information on Run lifecycles can be found here:
        https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps
        """
        run = self.create_and_run(  # pyright: ignore[reportDeprecated]
            assistant_id=assistant_id,
            instructions=instructions,
            max_completion_tokens=max_completion_tokens,
            max_prompt_tokens=max_prompt_tokens,
            metadata=metadata,
            model=model,
            parallel_tool_calls=parallel_tool_calls,
            response_format=response_format,
            temperature=temperature,
            stream=False,
            thread=thread,
            tool_resources=tool_resources,
            tool_choice=tool_choice,
            truncation_strategy=truncation_strategy,
            top_p=top_p,
            tools=tools,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
        )
        return self.runs.poll(run.id, run.thread_id, extra_headers, extra_query, extra_body, timeout, poll_interval_ms)  # pyright: ignore[reportDeprecated]

    @overload
    def create_and_run_stream(
        self,
        *,
        assistant_id: str,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AssistantStreamManager[AssistantEventHandler]:
        """Create a thread and stream the run back"""
        ...

    @overload
    def create_and_run_stream(
        self,
        *,
        assistant_id: str,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        event_handler: AssistantEventHandlerT,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AssistantStreamManager[AssistantEventHandlerT]:
        """Create a thread and stream the run back"""
        ...

    def create_and_run_stream(
        self,
        *,
        assistant_id: str,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        event_handler: AssistantEventHandlerT | None = None,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AssistantStreamManager[AssistantEventHandler] | AssistantStreamManager[AssistantEventHandlerT]:
        """Create a thread and stream the run back"""
        extra_headers = {
            "OpenAI-Beta": "assistants=v2",
            "X-Stainless-Stream-Helper": "threads.create_and_run_stream",
            "X-Stainless-Custom-Event-Handler": "true" if event_handler else "false",
            **(extra_headers or {}),
        }
        make_request = partial(
            self._post,
            "/threads/runs",
            body=maybe_transform(
                {
                    "assistant_id": assistant_id,
                    "instructions": instructions,
                    "max_completion_tokens": max_completion_tokens,
                    "max_prompt_tokens": max_prompt_tokens,
                    "metadata": metadata,
                    "model": model,
                    "parallel_tool_calls": parallel_tool_calls,
                    "response_format": response_format,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "stream": True,
                    "thread": thread,
                    "tools": tools,
                    "tool_resources": tool_resources,
                    "truncation_strategy": truncation_strategy,
                    "top_p": top_p,
                },
                thread_create_and_run_params.ThreadCreateAndRunParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
            stream=True,
            stream_cls=Stream[AssistantStreamEvent],
        )
        return AssistantStreamManager(make_request, event_handler=event_handler or AssistantEventHandler())


class AsyncThreads(AsyncAPIResource):
    @cached_property
    def runs(self) -> AsyncRuns:
        return AsyncRuns(self._client)

    @cached_property
    def messages(self) -> AsyncMessages:
        return AsyncMessages(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncThreadsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncThreadsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncThreadsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncThreadsWithStreamingResponse(self)

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def create(
        self,
        *,
        messages: Iterable[thread_create_params.Message] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_params.ToolResources] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Thread:
        """
        Create a thread.

        Args:
          messages: A list of [messages](https://platform.openai.com/docs/api-reference/messages) to
              start the thread with.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          tool_resources: A set of resources that are made available to the assistant's tools in this
              thread. The resources are specific to the type of tool. For example, the
              `code_interpreter` tool requires a list of file IDs, while the `file_search`
              tool requires a list of vector store IDs.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            "/threads",
            body=await async_maybe_transform(
                {
                    "messages": messages,
                    "metadata": metadata,
                    "tool_resources": tool_resources,
                },
                thread_create_params.ThreadCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Thread,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def retrieve(
        self,
        thread_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Thread:
        """
        Retrieves a thread.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._get(
            f"/threads/{thread_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Thread,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def update(
        self,
        thread_id: str,
        *,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_update_params.ToolResources] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Thread:
        """
        Modifies a thread.

        Args:
          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          tool_resources: A set of resources that are made available to the assistant's tools in this
              thread. The resources are specific to the type of tool. For example, the
              `code_interpreter` tool requires a list of file IDs, while the `file_search`
              tool requires a list of vector store IDs.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            f"/threads/{thread_id}",
            body=await async_maybe_transform(
                {
                    "metadata": metadata,
                    "tool_resources": tool_resources,
                },
                thread_update_params.ThreadUpdateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Thread,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def delete(
        self,
        thread_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ThreadDeleted:
        """
        Delete a thread.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._delete(
            f"/threads/{thread_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ThreadDeleted,
        )

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def create_and_run(
        self,
        *,
        assistant_id: str,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        Create a thread and run it in one request.

        Args:
          assistant_id: The ID of the
              [assistant](https://platform.openai.com/docs/api-reference/assistants) to use to
              execute this run.

          instructions: Override the default system message of the assistant. This is useful for
              modifying the behavior on a per-run basis.

          max_completion_tokens: The maximum number of completion tokens that may be used over the course of the
              run. The run will make a best effort to use only the number of completion tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              completion tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          max_prompt_tokens: The maximum number of prompt tokens that may be used over the course of the run.
              The run will make a best effort to use only the number of prompt tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              prompt tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: The ID of the [Model](https://platform.openai.com/docs/api-reference/models) to
              be used to execute this run. If a value is provided here, it will override the
              model associated with the assistant. If not, the model associated with the
              assistant will be used.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          thread: Options to create a new thread. If no thread is provided when running a request,
              an empty thread will be created.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tools and instead generates a message. `auto` is the default value
              and means the model can pick between generating a message or calling one or more
              tools. `required` means the model must call one or more tools before responding
              to the user. Specifying a particular tool like `{"type": "file_search"}` or
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

          tool_resources: A set of resources that are used by the assistant's tools. The resources are
              specific to the type of tool. For example, the `code_interpreter` tool requires
              a list of file IDs, while the `file_search` tool requires a list of vector store
              IDs.

          tools: Override the tools the assistant can use for this run. This is useful for
              modifying the behavior on a per-run basis.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          truncation_strategy: Controls for how a thread will be truncated prior to the run. Use this to
              control the intial context window of the run.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def create_and_run(
        self,
        *,
        assistant_id: str,
        stream: Literal[True],
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncStream[AssistantStreamEvent]:
        """
        Create a thread and run it in one request.

        Args:
          assistant_id: The ID of the
              [assistant](https://platform.openai.com/docs/api-reference/assistants) to use to
              execute this run.

          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          instructions: Override the default system message of the assistant. This is useful for
              modifying the behavior on a per-run basis.

          max_completion_tokens: The maximum number of completion tokens that may be used over the course of the
              run. The run will make a best effort to use only the number of completion tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              completion tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          max_prompt_tokens: The maximum number of prompt tokens that may be used over the course of the run.
              The run will make a best effort to use only the number of prompt tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              prompt tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: The ID of the [Model](https://platform.openai.com/docs/api-reference/models) to
              be used to execute this run. If a value is provided here, it will override the
              model associated with the assistant. If not, the model associated with the
              assistant will be used.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          thread: Options to create a new thread. If no thread is provided when running a request,
              an empty thread will be created.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tools and instead generates a message. `auto` is the default value
              and means the model can pick between generating a message or calling one or more
              tools. `required` means the model must call one or more tools before responding
              to the user. Specifying a particular tool like `{"type": "file_search"}` or
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

          tool_resources: A set of resources that are used by the assistant's tools. The resources are
              specific to the type of tool. For example, the `code_interpreter` tool requires
              a list of file IDs, while the `file_search` tool requires a list of vector store
              IDs.

          tools: Override the tools the assistant can use for this run. This is useful for
              modifying the behavior on a per-run basis.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          truncation_strategy: Controls for how a thread will be truncated prior to the run. Use this to
              control the intial context window of the run.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def create_and_run(
        self,
        *,
        assistant_id: str,
        stream: bool,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run | AsyncStream[AssistantStreamEvent]:
        """
        Create a thread and run it in one request.

        Args:
          assistant_id: The ID of the
              [assistant](https://platform.openai.com/docs/api-reference/assistants) to use to
              execute this run.

          stream: If `true`, returns a stream of events that happen during the Run as server-sent
              events, terminating when the Run enters a terminal state with a `data: [DONE]`
              message.

          instructions: Override the default system message of the assistant. This is useful for
              modifying the behavior on a per-run basis.

          max_completion_tokens: The maximum number of completion tokens that may be used over the course of the
              run. The run will make a best effort to use only the number of completion tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              completion tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          max_prompt_tokens: The maximum number of prompt tokens that may be used over the course of the run.
              The run will make a best effort to use only the number of prompt tokens
              specified, across multiple turns of the run. If the run exceeds the number of
              prompt tokens specified, the run will end with status `incomplete`. See
              `incomplete_details` for more info.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: The ID of the [Model](https://platform.openai.com/docs/api-reference/models) to
              be used to execute this run. If a value is provided here, it will override the
              model associated with the assistant. If not, the model associated with the
              assistant will be used.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          response_format: Specifies the format that the model must output. Compatible with
              [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
              [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
              and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
              message the model generates is valid JSON.

              **Important:** when using JSON mode, you **must** also instruct the model to
              produce JSON yourself via a system or user message. Without this, the model may
              generate an unending stream of whitespace until the generation reaches the token
              limit, resulting in a long-running and seemingly "stuck" request. Also note that
              the message content may be partially cut off if `finish_reason="length"`, which
              indicates the generation exceeded `max_tokens` or the conversation exceeded the
              max context length.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic.

          thread: Options to create a new thread. If no thread is provided when running a request,
              an empty thread will be created.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tools and instead generates a message. `auto` is the default value
              and means the model can pick between generating a message or calling one or more
              tools. `required` means the model must call one or more tools before responding
              to the user. Specifying a particular tool like `{"type": "file_search"}` or
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

          tool_resources: A set of resources that are used by the assistant's tools. The resources are
              specific to the type of tool. For example, the `code_interpreter` tool requires
              a list of file IDs, while the `file_search` tool requires a list of vector store
              IDs.

          tools: Override the tools the assistant can use for this run. This is useful for
              modifying the behavior on a per-run basis.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or temperature but not both.

          truncation_strategy: Controls for how a thread will be truncated prior to the run. Use this to
              control the intial context window of the run.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    @required_args(["assistant_id"], ["assistant_id", "stream"])
    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def create_and_run(
        self,
        *,
        assistant_id: str,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run | AsyncStream[AssistantStreamEvent]:
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            "/threads/runs",
            body=await async_maybe_transform(
                {
                    "assistant_id": assistant_id,
                    "instructions": instructions,
                    "max_completion_tokens": max_completion_tokens,
                    "max_prompt_tokens": max_prompt_tokens,
                    "metadata": metadata,
                    "model": model,
                    "parallel_tool_calls": parallel_tool_calls,
                    "response_format": response_format,
                    "stream": stream,
                    "temperature": temperature,
                    "thread": thread,
                    "tool_choice": tool_choice,
                    "tool_resources": tool_resources,
                    "tools": tools,
                    "top_p": top_p,
                    "truncation_strategy": truncation_strategy,
                },
                thread_create_and_run_params.ThreadCreateAndRunParamsStreaming
                if stream
                else thread_create_and_run_params.ThreadCreateAndRunParamsNonStreaming,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
            stream=stream or False,
            stream_cls=AsyncStream[AssistantStreamEvent],
        )

    async def create_and_run_poll(
        self,
        *,
        assistant_id: str,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        poll_interval_ms: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Run:
        """
        A helper to create a thread, start a run and then poll for a terminal state.
        More information on Run lifecycles can be found here:
        https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps
        """
        run = await self.create_and_run(  # pyright: ignore[reportDeprecated]
            assistant_id=assistant_id,
            instructions=instructions,
            max_completion_tokens=max_completion_tokens,
            max_prompt_tokens=max_prompt_tokens,
            metadata=metadata,
            model=model,
            parallel_tool_calls=parallel_tool_calls,
            response_format=response_format,
            temperature=temperature,
            stream=False,
            thread=thread,
            tool_resources=tool_resources,
            tool_choice=tool_choice,
            truncation_strategy=truncation_strategy,
            top_p=top_p,
            tools=tools,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
        )
        return await self.runs.poll(  # pyright: ignore[reportDeprecated]
            run.id, run.thread_id, extra_headers, extra_query, extra_body, timeout, poll_interval_ms
        )

    @overload
    def create_and_run_stream(
        self,
        *,
        assistant_id: str,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncAssistantStreamManager[AsyncAssistantEventHandler]:
        """Create a thread and stream the run back"""
        ...

    @overload
    def create_and_run_stream(
        self,
        *,
        assistant_id: str,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        event_handler: AsyncAssistantEventHandlerT,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncAssistantStreamManager[AsyncAssistantEventHandlerT]:
        """Create a thread and stream the run back"""
        ...

    def create_and_run_stream(
        self,
        *,
        assistant_id: str,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_prompt_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel, None] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        response_format: Optional[AssistantResponseFormatOptionParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        thread: thread_create_and_run_params.Thread | NotGiven = NOT_GIVEN,
        tool_choice: Optional[AssistantToolChoiceOptionParam] | NotGiven = NOT_GIVEN,
        tool_resources: Optional[thread_create_and_run_params.ToolResources] | NotGiven = NOT_GIVEN,
        tools: Optional[Iterable[AssistantToolParam]] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation_strategy: Optional[thread_create_and_run_params.TruncationStrategy] | NotGiven = NOT_GIVEN,
        event_handler: AsyncAssistantEventHandlerT | None = None,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> (
        AsyncAssistantStreamManager[AsyncAssistantEventHandler]
        | AsyncAssistantStreamManager[AsyncAssistantEventHandlerT]
    ):
        """Create a thread and stream the run back"""
        extra_headers = {
            "OpenAI-Beta": "assistants=v2",
            "X-Stainless-Stream-Helper": "threads.create_and_run_stream",
            "X-Stainless-Custom-Event-Handler": "true" if event_handler else "false",
            **(extra_headers or {}),
        }
        request = self._post(
            "/threads/runs",
            body=maybe_transform(
                {
                    "assistant_id": assistant_id,
                    "instructions": instructions,
                    "max_completion_tokens": max_completion_tokens,
                    "max_prompt_tokens": max_prompt_tokens,
                    "metadata": metadata,
                    "model": model,
                    "parallel_tool_calls": parallel_tool_calls,
                    "response_format": response_format,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "stream": True,
                    "thread": thread,
                    "tools": tools,
                    "tool_resources": tool_resources,
                    "truncation_strategy": truncation_strategy,
                    "top_p": top_p,
                },
                thread_create_and_run_params.ThreadCreateAndRunParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Run,
            stream=True,
            stream_cls=AsyncStream[AssistantStreamEvent],
        )
        return AsyncAssistantStreamManager(request, event_handler=event_handler or AsyncAssistantEventHandler())


class ThreadsWithRawResponse:
    def __init__(self, threads: Threads) -> None:
        self._threads = threads

        self.create = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                threads.create  # pyright: ignore[reportDeprecated],
            )
        )
        self.retrieve = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                threads.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.update = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                threads.update  # pyright: ignore[reportDeprecated],
            )
        )
        self.delete = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                threads.delete  # pyright: ignore[reportDeprecated],
            )
        )
        self.create_and_run = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                threads.create_and_run  # pyright: ignore[reportDeprecated],
            )
        )

    @cached_property
    def runs(self) -> RunsWithRawResponse:
        return RunsWithRawResponse(self._threads.runs)

    @cached_property
    def messages(self) -> MessagesWithRawResponse:
        return MessagesWithRawResponse(self._threads.messages)


class AsyncThreadsWithRawResponse:
    def __init__(self, threads: AsyncThreads) -> None:
        self._threads = threads

        self.create = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                threads.create  # pyright: ignore[reportDeprecated],
            )
        )
        self.retrieve = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                threads.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.update = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                threads.update  # pyright: ignore[reportDeprecated],
            )
        )
        self.delete = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                threads.delete  # pyright: ignore[reportDeprecated],
            )
        )
        self.create_and_run = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                threads.create_and_run  # pyright: ignore[reportDeprecated],
            )
        )

    @cached_property
    def runs(self) -> AsyncRunsWithRawResponse:
        return AsyncRunsWithRawResponse(self._threads.runs)

    @cached_property
    def messages(self) -> AsyncMessagesWithRawResponse:
        return AsyncMessagesWithRawResponse(self._threads.messages)


class ThreadsWithStreamingResponse:
    def __init__(self, threads: Threads) -> None:
        self._threads = threads

        self.create = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                threads.create  # pyright: ignore[reportDeprecated],
            )
        )
        self.retrieve = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                threads.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.update = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                threads.update  # pyright: ignore[reportDeprecated],
            )
        )
        self.delete = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                threads.delete  # pyright: ignore[reportDeprecated],
            )
        )
        self.create_and_run = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                threads.create_and_run  # pyright: ignore[reportDeprecated],
            )
        )

    @cached_property
    def runs(self) -> RunsWithStreamingResponse:
        return RunsWithStreamingResponse(self._threads.runs)

    @cached_property
    def messages(self) -> MessagesWithStreamingResponse:
        return MessagesWithStreamingResponse(self._threads.messages)


class AsyncThreadsWithStreamingResponse:
    def __init__(self, threads: AsyncThreads) -> None:
        self._threads = threads

        self.create = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                threads.create  # pyright: ignore[reportDeprecated],
            )
        )
        self.retrieve = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                threads.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.update = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                threads.update  # pyright: ignore[reportDeprecated],
            )
        )
        self.delete = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                threads.delete  # pyright: ignore[reportDeprecated],
            )
        )
        self.create_and_run = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                threads.create_and_run  # pyright: ignore[reportDeprecated],
            )
        )

    @cached_property
    def runs(self) -> AsyncRunsWithStreamingResponse:
        return AsyncRunsWithStreamingResponse(self._threads.runs)

    @cached_property
    def messages(self) -> AsyncMessagesWithStreamingResponse:
        return AsyncMessagesWithStreamingResponse(self._threads.messages)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_comm.py ===
""" pydevd - a debugging daemon
This is the daemon you launch for python remote debugging.

Protocol:
each command has a format:
    id\tsequence-num\ttext
    id: protocol command number
    sequence-num: each request has a sequence number. Sequence numbers
    originating at the debugger are odd, sequence numbers originating
    at the daemon are even. Every response uses the same sequence number
    as the request.
    payload: it is protocol dependent. When response is a complex structure, it
    is returned as XML. Each attribute value is urlencoded, and then the whole
    payload is urlencoded again to prevent stray characters corrupting protocol/xml encodings

    Commands:

    NUMBER   NAME                     FROM*     ARGUMENTS                     RESPONSE      NOTE
100 series: program execution
    101      RUN                      JAVA      -                             -
    102      LIST_THREADS             JAVA                                    RETURN with XML listing of all threads
    103      THREAD_CREATE            PYDB      -                             XML with thread information
    104      THREAD_KILL              JAVA      id (or * to exit)             kills the thread
                                      PYDB      id                            nofies JAVA that thread was killed
    105      THREAD_SUSPEND           JAVA      XML of the stack,             suspends the thread
                                                reason for suspension
                                      PYDB      id                            notifies JAVA that thread was suspended

    106      CMD_THREAD_RUN           JAVA      id                            resume the thread
                                      PYDB      id \t reason                  notifies JAVA that thread was resumed

    107      STEP_INTO                JAVA      thread_id
    108      STEP_OVER                JAVA      thread_id
    109      STEP_RETURN              JAVA      thread_id

    110      GET_VARIABLE             JAVA      thread_id \t frame_id \t      GET_VARIABLE with XML of var content
                                                FRAME|GLOBAL \t attributes*

    111      SET_BREAK                JAVA      file/line of the breakpoint
    112      REMOVE_BREAK             JAVA      file/line of the return
    113      CMD_EVALUATE_EXPRESSION  JAVA      expression                    result of evaluating the expression
    114      CMD_GET_FRAME            JAVA                                    request for frame contents
    115      CMD_EXEC_EXPRESSION      JAVA
    116      CMD_WRITE_TO_CONSOLE     PYDB
    117      CMD_CHANGE_VARIABLE
    118      CMD_RUN_TO_LINE
    119      CMD_RELOAD_CODE
    120      CMD_GET_COMPLETIONS      JAVA

    200      CMD_REDIRECT_OUTPUT      JAVA      streams to redirect as string -
                                                'STDOUT' (redirect only STDOUT)
                                                'STDERR' (redirect only STDERR)
                                                'STDOUT STDERR' (redirect both streams)

500 series diagnostics/ok
    501      VERSION                  either      Version string (1.0)        Currently just used at startup
    502      RETURN                   either      Depends on caller    -

900 series: errors
    901      ERROR                    either      -                           This is reserved for unexpected errors.

    * JAVA - remote debugger, the java end
    * PYDB - pydevd, the python end
"""

import linecache
import os

from _pydev_bundle.pydev_imports import _queue
from _pydev_bundle._pydev_saved_modules import time, ThreadingEvent
from _pydev_bundle._pydev_saved_modules import socket as socket_module
from _pydevd_bundle.pydevd_constants import (
    DebugInfoHolder,
    IS_WINDOWS,
    IS_JYTHON,
    IS_WASM,
    IS_PY36_OR_GREATER,
    STATE_RUN,
    ASYNC_EVAL_TIMEOUT_SEC,
    get_global_debugger,
    GetGlobalDebugger,
    set_global_debugger,  # Keep for backward compatibility @UnusedImport
    silence_warnings_decorator,
    filter_all_warnings,
    IS_PY311_OR_GREATER,
)
from _pydev_bundle.pydev_override import overrides
import weakref
from _pydev_bundle._pydev_completer import extract_token_and_qualifier
from _pydevd_bundle._debug_adapter.pydevd_schema import (
    VariablesResponseBody,
    SetVariableResponseBody,
    StepInTarget,
    StepInTargetsResponseBody,
)
from _pydevd_bundle._debug_adapter import pydevd_base_schema, pydevd_schema
from _pydevd_bundle.pydevd_net_command import NetCommand
from _pydevd_bundle.pydevd_xml import ExceptionOnEvaluate
from _pydevd_bundle.pydevd_constants import ForkSafeLock, NULL
from _pydevd_bundle.pydevd_daemon_thread import PyDBDaemonThread
from _pydevd_bundle.pydevd_thread_lifecycle import pydevd_find_thread_by_id, resume_threads
from _pydevd_bundle.pydevd_dont_trace_files import PYDEV_FILE
import dis
import pydevd_file_utils
import itertools
from urllib.parse import quote_plus, unquote_plus
import pydevconsole
from _pydevd_bundle import pydevd_vars, pydevd_io, pydevd_reload
from _pydevd_bundle import pydevd_bytecode_utils
from _pydevd_bundle import pydevd_xml
from _pydevd_bundle import pydevd_vm_type
import sys
import traceback
from _pydevd_bundle.pydevd_utils import (
    quote_smart as quote,
    compare_object_attrs_key,
    notify_about_gevent_if_needed,
    isinstance_checked,
    ScopeRequest,
    getattr_checked,
    Timer,
    is_current_thread_main_thread,
)
from _pydev_bundle import pydev_log, fsnotify
from _pydev_bundle.pydev_log import exception as pydev_log_exception
from _pydev_bundle import _pydev_completer

from pydevd_tracing import get_exception_traceback_str
from _pydevd_bundle import pydevd_console
from _pydev_bundle.pydev_monkey import disable_trace_thread_modules, enable_trace_thread_modules
from io import StringIO

# CMD_XXX constants imported for backward compatibility
from _pydevd_bundle.pydevd_comm_constants import *  # @UnusedWildImport

# Socket import aliases:
AF_INET, AF_INET6, SOCK_STREAM, SHUT_WR, SOL_SOCKET, IPPROTO_TCP, socket = (
    socket_module.AF_INET,
    socket_module.AF_INET6,
    socket_module.SOCK_STREAM,
    socket_module.SHUT_WR,
    socket_module.SOL_SOCKET,
    socket_module.IPPROTO_TCP,
    socket_module.socket,
)

if IS_WINDOWS and not IS_JYTHON:
    SO_EXCLUSIVEADDRUSE = socket_module.SO_EXCLUSIVEADDRUSE
if not IS_WASM:
    SO_REUSEADDR = socket_module.SO_REUSEADDR


class ReaderThread(PyDBDaemonThread):
    """reader thread reads and dispatches commands in an infinite loop"""

    def __init__(self, sock, py_db, PyDevJsonCommandProcessor, process_net_command, terminate_on_socket_close=True):
        assert sock is not None
        PyDBDaemonThread.__init__(self, py_db)
        self.__terminate_on_socket_close = terminate_on_socket_close

        self.sock = sock
        self._buffer = b""
        self.name = "pydevd.Reader"
        self.process_net_command = process_net_command
        self.process_net_command_json = PyDevJsonCommandProcessor(self._from_json).process_net_command_json

    def _from_json(self, json_msg, update_ids_from_dap=False):
        return pydevd_base_schema.from_json(json_msg, update_ids_from_dap, on_dict_loaded=self._on_dict_loaded)

    def _on_dict_loaded(self, dct):
        for listener in self.py_db.dap_messages_listeners:
            listener.after_receive(dct)

    @overrides(PyDBDaemonThread.do_kill_pydev_thread)
    def do_kill_pydev_thread(self):
        PyDBDaemonThread.do_kill_pydev_thread(self)
        # Note that we no longer shutdown the reader, just the writer. The idea is that we shutdown
        # the writer to send that the communication has finished, then, the client will shutdown its
        # own writer when it receives an empty read, at which point this reader will also shutdown.

        # That way, we can *almost* guarantee that all messages have been properly sent -- it's not
        # completely guaranteed because it's possible that the process exits before the whole
        # message was sent as having this thread alive won't stop the process from exiting -- we
        # have a timeout when exiting the process waiting for this thread to finish -- see:
        # PyDB.dispose_and_kill_all_pydevd_threads()).

        # try:
        #    self.sock.shutdown(SHUT_RD)
        # except:
        #    pass
        # try:
        #    self.sock.close()
        # except:
        #    pass

    def _read(self, size):
        while True:
            buffer_len = len(self._buffer)
            if buffer_len == size:
                ret = self._buffer
                self._buffer = b""
                return ret

            if buffer_len > size:
                ret = self._buffer[:size]
                self._buffer = self._buffer[size:]
                return ret

            try:
                r = self.sock.recv(max(size - buffer_len, 1024))
            except OSError:
                return b""
            if not r:
                return b""
            self._buffer += r

    def _read_line(self):
        while True:
            i = self._buffer.find(b"\n")
            if i != -1:
                i += 1  # Add the newline to the return
                ret = self._buffer[:i]
                self._buffer = self._buffer[i:]
                return ret
            else:
                try:
                    r = self.sock.recv(1024)
                except OSError:
                    return b""
                if not r:
                    return b""
                self._buffer += r

    @overrides(PyDBDaemonThread._on_run)
    def _on_run(self):
        try:
            content_len = -1

            while True:
                # i.e.: even if we received a kill, we should only exit the ReaderThread when the
                # client itself closes the connection (although on kill received we stop actually
                # processing anything read).
                try:
                    notify_about_gevent_if_needed()
                    line = self._read_line()

                    if len(line) == 0:
                        pydev_log.debug("ReaderThread: empty contents received (len(line) == 0).")
                        self._terminate_on_socket_close()
                        return  # Finished communication.

                    if self._kill_received:
                        continue

                    if line.startswith(b"Content-Length:"):
                        content_len = int(line.strip().split(b":", 1)[1])
                        continue

                    if content_len != -1:
                        # If we previously received a content length, read until a '\r\n'.
                        if line == b"\r\n":
                            json_contents = self._read(content_len)

                            content_len = -1

                            if len(json_contents) == 0:
                                pydev_log.debug("ReaderThread: empty contents received (len(json_contents) == 0).")
                                self._terminate_on_socket_close()
                                return  # Finished communication.

                            if self._kill_received:
                                continue

                            # We just received a json message, let's process it.
                            self.process_net_command_json(self.py_db, json_contents)

                        continue
                    else:
                        # No content len, regular line-based protocol message (remove trailing new-line).
                        if line.endswith(b"\n\n"):
                            line = line[:-2]

                        elif line.endswith(b"\n"):
                            line = line[:-1]

                        elif line.endswith(b"\r"):
                            line = line[:-1]
                except:
                    if not self._kill_received:
                        pydev_log_exception()
                        self._terminate_on_socket_close()
                    return  # Finished communication.

                # Note: the java backend is always expected to pass utf-8 encoded strings. We now work with str
                # internally and thus, we may need to convert to the actual encoding where needed (i.e.: filenames
                # on python 2 may need to be converted to the filesystem encoding).
                if hasattr(line, "decode"):
                    line = line.decode("utf-8")

                if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 3:
                    pydev_log.debug("debugger: received >>%s<<\n", line)

                args = line.split("\t", 2)
                try:
                    cmd_id = int(args[0])
                    if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 3:
                        pydev_log.debug("Received command: %s %s\n", ID_TO_MEANING.get(str(cmd_id), "???"), line)
                    self.process_command(cmd_id, int(args[1]), args[2])
                except:
                    if sys is not None and pydev_log_exception is not None:  # Could happen at interpreter shutdown
                        pydev_log_exception("Can't process net command: %s.", line)

        except:
            if not self._kill_received:
                if sys is not None and pydev_log_exception is not None:  # Could happen at interpreter shutdown
                    pydev_log_exception()

            self._terminate_on_socket_close()
        finally:
            pydev_log.debug("ReaderThread: exit")

    def _terminate_on_socket_close(self):
        if self.__terminate_on_socket_close:
            self.py_db.dispose_and_kill_all_pydevd_threads()

    def process_command(self, cmd_id, seq, text):
        self.process_net_command(self.py_db, cmd_id, seq, text)


class FSNotifyThread(PyDBDaemonThread):
    def __init__(self, py_db, api, watch_dirs):
        PyDBDaemonThread.__init__(self, py_db)
        self.api = api
        self.name = "pydevd.FSNotifyThread"
        self.watcher = fsnotify.Watcher()
        self.watch_dirs = watch_dirs

    @overrides(PyDBDaemonThread._on_run)
    def _on_run(self):
        try:
            pydev_log.info("Watching directories for code reload:\n---\n%s\n---" % ("\n".join(sorted(self.watch_dirs))))

            # i.e.: The first call to set_tracked_paths will do a full scan, so, do it in the thread
            # too (after everything is configured).
            self.watcher.set_tracked_paths(self.watch_dirs)
            while not self._kill_received:
                for change_enum, change_path in self.watcher.iter_changes():
                    # We're only interested in modified events
                    if change_enum == fsnotify.Change.modified:
                        pydev_log.info("Modified: %s", change_path)
                        self.api.request_reload_code(self.py_db, -1, None, change_path)
                    else:
                        pydev_log.info("Ignored (add or remove) change in: %s", change_path)
        except:
            pydev_log.exception("Error when waiting for filesystem changes in FSNotifyThread.")

    @overrides(PyDBDaemonThread.do_kill_pydev_thread)
    def do_kill_pydev_thread(self):
        self.watcher.dispose()
        PyDBDaemonThread.do_kill_pydev_thread(self)


class WriterThread(PyDBDaemonThread):
    """writer thread writes out the commands in an infinite loop"""

    def __init__(self, sock, py_db, terminate_on_socket_close=True):
        PyDBDaemonThread.__init__(self, py_db)
        self.sock = sock
        self.__terminate_on_socket_close = terminate_on_socket_close
        self.name = "pydevd.Writer"
        self._cmd_queue = _queue.Queue()
        if pydevd_vm_type.get_vm_type() == "python":
            self.timeout = 0
        else:
            self.timeout = 0.1

    def add_command(self, cmd):
        """cmd is NetCommand"""
        if not self._kill_received:  # we don't take new data after everybody die
            self._cmd_queue.put(cmd, False)

    @overrides(PyDBDaemonThread._on_run)
    def _on_run(self):
        """just loop and write responses"""

        try:
            while True:
                try:
                    try:
                        cmd = self._cmd_queue.get(True, 0.1)
                    except _queue.Empty:
                        if self._kill_received:
                            pydev_log.debug("WriterThread: kill_received (sock.shutdown(SHUT_WR))")
                            try:
                                self.sock.shutdown(SHUT_WR)
                            except:
                                pass
                            # Note: don't close the socket, just send the shutdown,
                            # then, when no data is received on the reader, it can close
                            # the socket.
                            # See: https://blog.netherlabs.nl/articles/2009/01/18/the-ultimate-so_linger-page-or-why-is-my-tcp-not-reliable

                            # try:
                            #     self.sock.close()
                            # except:
                            #     pass

                            return  # break if queue is empty and _kill_received
                        else:
                            continue
                except:
                    # pydev_log.info('Finishing debug communication...(1)')
                    # when liberating the thread here, we could have errors because we were shutting down
                    # but the thread was still not liberated
                    return

                if cmd.as_dict is not None:
                    for listener in self.py_db.dap_messages_listeners:
                        listener.before_send(cmd.as_dict)

                notify_about_gevent_if_needed()
                cmd.send(self.sock)

                if cmd.id == CMD_EXIT:
                    pydev_log.debug("WriterThread: CMD_EXIT received")
                    break
                if time is None:
                    break  # interpreter shutdown
                time.sleep(self.timeout)
        except Exception:
            if self.__terminate_on_socket_close:
                self.py_db.dispose_and_kill_all_pydevd_threads()
                if DebugInfoHolder.DEBUG_TRACE_LEVEL > 0:
                    pydev_log_exception()
        finally:
            pydev_log.debug("WriterThread: exit")

    def empty(self):
        return self._cmd_queue.empty()

    @overrides(PyDBDaemonThread.do_kill_pydev_thread)
    def do_kill_pydev_thread(self):
        if not self._kill_received:
            # Add command before setting the kill flag (otherwise the command may not be added).
            exit_cmd = self.py_db.cmd_factory.make_exit_command(self.py_db)
            self.add_command(exit_cmd)

        PyDBDaemonThread.do_kill_pydev_thread(self)


def create_server_socket(host, port):
    try:
        server = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        if IS_WINDOWS and not IS_JYTHON:
            server.setsockopt(SOL_SOCKET, SO_EXCLUSIVEADDRUSE, 1)
        elif not IS_WASM:
            server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

        server.bind((host, port))
        server.settimeout(None)
    except Exception:
        server.close()
        raise

    return server


def start_server(port):
    """binds to a port, waits for the debugger to connect"""
    s = create_server_socket(host="", port=port)

    try:
        s.listen(1)
        # Let the user know it's halted waiting for the connection.
        host, port = s.getsockname()
        msg = f"pydevd: waiting for connection at: {host}:{port}"
        print(msg, file=sys.stderr)
        pydev_log.info(msg)

        new_socket, _addr = s.accept()
        pydev_log.info("Connection accepted")
        # closing server socket is not necessary but we don't need it
        s.close()
        return new_socket
    except:
        pydev_log.exception("Could not bind to port: %s\n", port)
        raise


def start_client(host, port):
    """connects to a host/port"""
    pydev_log.info("Connecting to %s:%s", host, port)

    address_family = AF_INET
    for res in socket_module.getaddrinfo(host, port, 0, SOCK_STREAM):
        if res[0] == AF_INET:
            address_family = res[0]
            # Prefer IPv4 addresses for backward compat.
            break
        if res[0] == AF_INET6:
            # Don't break after this - if the socket is dual-stack prefer IPv4.
            address_family = res[0]

    s = socket(address_family, SOCK_STREAM)

    #  Set TCP keepalive on an open socket.
    #  It activates after 1 second (TCP_KEEPIDLE,) of idleness,
    #  then sends a keepalive ping once every 3 seconds (TCP_KEEPINTVL),
    #  and closes the connection after 5 failed ping (TCP_KEEPCNT), or 15 seconds
    try:
        s.setsockopt(SOL_SOCKET, socket_module.SO_KEEPALIVE, 1)
    except (AttributeError, OSError):
        pass  # May not be available everywhere.
    try:
        s.setsockopt(socket_module.IPPROTO_TCP, socket_module.TCP_KEEPIDLE, 1)
    except (AttributeError, OSError):
        pass  # May not be available everywhere.
    try:
        s.setsockopt(socket_module.IPPROTO_TCP, socket_module.TCP_KEEPINTVL, 3)
    except (AttributeError, OSError):
        pass  # May not be available everywhere.
    try:
        s.setsockopt(socket_module.IPPROTO_TCP, socket_module.TCP_KEEPCNT, 5)
    except (AttributeError, OSError):
        pass  # May not be available everywhere.

    try:
        # 10 seconds default timeout
        timeout = int(os.environ.get("PYDEVD_CONNECT_TIMEOUT", 10))
        s.settimeout(timeout)
        s.connect((host, port))
        s.settimeout(None)  # no timeout after connected
        pydev_log.info(f"Connected to: {s}.")
        return s
    except:
        pydev_log.exception("Could not connect to %s: %s", host, port)
        raise


INTERNAL_TERMINATE_THREAD = 1
INTERNAL_SUSPEND_THREAD = 2


class InternalThreadCommand(object):
    """internal commands are generated/executed by the debugger.

    The reason for their existence is that some commands have to be executed
    on specific threads. These are the InternalThreadCommands that get
    get posted to PyDB.
    """

    def __init__(self, thread_id, method=None, *args, **kwargs):
        self.thread_id = thread_id
        self.method = method
        self.args = args
        self.kwargs = kwargs

    def can_be_executed_by(self, thread_id):
        """By default, it must be in the same thread to be executed"""
        return self.thread_id == thread_id or self.thread_id.endswith("|" + thread_id)

    def do_it(self, dbg):
        try:
            if self.method is not None:
                self.method(dbg, *self.args, **self.kwargs)
            else:
                raise NotImplementedError("you have to override do_it")
        finally:
            self.args = None
            self.kwargs = None

    def __str__(self):
        return "InternalThreadCommands(%s, %s, %s)" % (self.method, self.args, self.kwargs)

    __repr__ = __str__


class InternalThreadCommandForAnyThread(InternalThreadCommand):
    def __init__(self, thread_id, method=None, *args, **kwargs):
        assert thread_id == "*"

        InternalThreadCommand.__init__(self, thread_id, method, *args, **kwargs)

        self.executed = False
        self.lock = ForkSafeLock()

    def can_be_executed_by(self, thread_id):
        return True  # Can be executed by any thread.

    def do_it(self, dbg):
        with self.lock:
            if self.executed:
                return
            self.executed = True

        InternalThreadCommand.do_it(self, dbg)


def _send_io_message(py_db, s):
    cmd = py_db.cmd_factory.make_io_message(s, 2)
    if py_db.writer is not None:
        py_db.writer.add_command(cmd)


def internal_reload_code(dbg, seq, module_name, filename):
    try:
        found_module_to_reload = False
        if module_name is not None:
            module_name = module_name
            if module_name not in sys.modules:
                if "." in module_name:
                    new_module_name = module_name.split(".")[-1]
                    if new_module_name in sys.modules:
                        module_name = new_module_name

        modules_to_reload = {}
        module = sys.modules.get(module_name)
        if module is not None:
            modules_to_reload[id(module)] = (module, module_name)

        if filename:
            filename = pydevd_file_utils.normcase(filename)
            for module_name, module in sys.modules.copy().items():
                f = getattr_checked(module, "__file__")
                if f is not None:
                    if f.endswith((".pyc", ".pyo")):
                        f = f[:-1]

                    if pydevd_file_utils.normcase(f) == filename:
                        modules_to_reload[id(module)] = (module, module_name)

        if not modules_to_reload:
            if filename and module_name:
                _send_io_message(dbg, "code reload: Unable to find module %s to reload for path: %s\n" % (module_name, filename))
            elif filename:
                _send_io_message(dbg, "code reload: Unable to find module to reload for path: %s\n" % (filename,))
            elif module_name:
                _send_io_message(dbg, "code reload: Unable to find module to reload: %s\n" % (module_name,))

        else:
            # Too much info...
            # _send_io_message(dbg, 'code reload: This usually means you are trying to reload the __main__ module (which cannot be reloaded).\n')
            for module, module_name in modules_to_reload.values():
                _send_io_message(dbg, 'code reload: Start reloading module: "' + module_name + '" ... \n')
                found_module_to_reload = True

                if pydevd_reload.xreload(module):
                    _send_io_message(dbg, "code reload: reload finished\n")
                else:
                    _send_io_message(dbg, "code reload: reload finished without applying any change\n")

        cmd = dbg.cmd_factory.make_reloaded_code_message(seq, found_module_to_reload)
        dbg.writer.add_command(cmd)
    except:
        pydev_log.exception("Error reloading code")


class InternalGetThreadStack(InternalThreadCommand):
    """
    This command will either wait for a given thread to be paused to get its stack or will provide
    it anyways after a timeout (in which case the stack will be gotten but local variables won't
    be available and it'll not be possible to interact with the frame as it's not actually
    stopped in a breakpoint).
    """

    def __init__(self, seq, thread_id, py_db, set_additional_thread_info, fmt, timeout=0.5, start_frame=0, levels=0):
        InternalThreadCommand.__init__(self, thread_id)
        self._py_db = weakref.ref(py_db)
        self._timeout = time.time() + timeout
        self.seq = seq
        self._cmd = None
        self._fmt = fmt
        self._start_frame = start_frame
        self._levels = levels

        # Note: receives set_additional_thread_info to avoid a circular import
        # in this module.
        self._set_additional_thread_info = set_additional_thread_info

    @overrides(InternalThreadCommand.can_be_executed_by)
    def can_be_executed_by(self, _thread_id):
        timed_out = time.time() >= self._timeout

        py_db = self._py_db()
        t = pydevd_find_thread_by_id(self.thread_id)
        frame = None
        if t and not getattr(t, "pydev_do_not_trace", None):
            additional_info = self._set_additional_thread_info(t)
            frame = additional_info.get_topmost_frame(t)
        try:
            self._cmd = py_db.cmd_factory.make_get_thread_stack_message(
                py_db,
                self.seq,
                self.thread_id,
                frame,
                self._fmt,
                must_be_suspended=not timed_out,
                start_frame=self._start_frame,
                levels=self._levels,
            )
        finally:
            frame = None
            t = None

        return self._cmd is not None or timed_out

    @overrides(InternalThreadCommand.do_it)
    def do_it(self, dbg):
        if self._cmd is not None:
            dbg.writer.add_command(self._cmd)
            self._cmd = None


def internal_step_in_thread(py_db, thread_id, cmd_id, set_additional_thread_info):
    thread_to_step = pydevd_find_thread_by_id(thread_id)
    if thread_to_step is not None:
        info = set_additional_thread_info(thread_to_step)
        info.pydev_original_step_cmd = cmd_id
        info.pydev_step_cmd = cmd_id
        info.pydev_step_stop = None
        info.pydev_state = STATE_RUN
        info.update_stepping_info()

    if py_db.stepping_resumes_all_threads:
        resume_threads("*", except_thread=thread_to_step)


def internal_smart_step_into(py_db, thread_id, offset, child_offset, set_additional_thread_info):
    thread_to_step = pydevd_find_thread_by_id(thread_id)
    if thread_to_step is not None:
        info = set_additional_thread_info(thread_to_step)
        info.pydev_original_step_cmd = CMD_SMART_STEP_INTO
        info.pydev_step_cmd = CMD_SMART_STEP_INTO
        info.pydev_step_stop = None
        info.pydev_smart_parent_offset = int(offset)
        info.pydev_smart_child_offset = int(child_offset)
        info.pydev_state = STATE_RUN
        info.update_stepping_info()

    if py_db.stepping_resumes_all_threads:
        resume_threads("*", except_thread=thread_to_step)


class InternalSetNextStatementThread(InternalThreadCommand):
    def __init__(self, thread_id, cmd_id, line, func_name, seq=0):
        """
        cmd_id may actually be one of:

        CMD_RUN_TO_LINE
        CMD_SET_NEXT_STATEMENT
        CMD_SMART_STEP_INTO
        """
        self.thread_id = thread_id
        self.cmd_id = cmd_id
        self.line = line
        self.seq = seq

        self.func_name = func_name

    def do_it(self, dbg):
        t = pydevd_find_thread_by_id(self.thread_id)
        if t is not None:
            info = t.additional_info
            info.pydev_original_step_cmd = self.cmd_id
            info.pydev_step_cmd = self.cmd_id
            info.pydev_step_stop = None
            info.pydev_next_line = int(self.line)
            info.pydev_func_name = self.func_name
            info.pydev_message = str(self.seq)
            info.pydev_smart_parent_offset = -1
            info.pydev_smart_child_offset = -1
            info.pydev_state = STATE_RUN
            info.update_stepping_info()


@silence_warnings_decorator
def internal_get_variable_json(py_db, request):
    """
    :param VariablesRequest request:
    """
    arguments = request.arguments  # : :type arguments: VariablesArguments
    variables_reference = arguments.variablesReference
    scope = None
    if isinstance_checked(variables_reference, ScopeRequest):
        scope = variables_reference
        variables_reference = variables_reference.variable_reference

    fmt = arguments.format
    if hasattr(fmt, "to_dict"):
        fmt = fmt.to_dict()

    variables = []
    try:
        try:
            variable = py_db.suspended_frames_manager.get_variable(variables_reference)
        except KeyError:
            pass
        else:
            for child_var in variable.get_children_variables(fmt=fmt, scope=scope):
                variables.append(child_var.get_var_data(fmt=fmt))
    except:
        try:
            exc, exc_type, tb = sys.exc_info()
            err = "".join(traceback.format_exception(exc, exc_type, tb))
            variables = [{"name": "<error>", "value": err, "type": "<error>", "variablesReference": 0}]
        except:
            err = "<Internal error - unable to get traceback when getting variables>"
            pydev_log.exception(err)
            variables = []

    body = VariablesResponseBody(variables)
    variables_response = pydevd_base_schema.build_response(request, kwargs={"body": body})
    py_db.writer.add_command(NetCommand(CMD_RETURN, 0, variables_response, is_json=True))


class InternalGetVariable(InternalThreadCommand):
    """gets the value of a variable"""

    def __init__(self, seq, thread_id, frame_id, scope, attrs):
        self.sequence = seq
        self.thread_id = thread_id
        self.frame_id = frame_id
        self.scope = scope
        self.attributes = attrs

    @silence_warnings_decorator
    def do_it(self, dbg):
        """Converts request into python variable"""
        try:
            xml = StringIO()
            xml.write("<xml>")
            type_name, val_dict = pydevd_vars.resolve_compound_variable_fields(
                dbg, self.thread_id, self.frame_id, self.scope, self.attributes
            )
            if val_dict is None:
                val_dict = {}

            # assume properly ordered if resolver returns 'OrderedDict'
            # check type as string to support OrderedDict backport for older Python
            keys = list(val_dict)
            if not (type_name == "OrderedDict" or val_dict.__class__.__name__ == "OrderedDict" or IS_PY36_OR_GREATER):
                keys = sorted(keys, key=compare_object_attrs_key)

            timer = Timer()
            for k in keys:
                val = val_dict[k]
                evaluate_full_value = pydevd_xml.should_evaluate_full_value(val)
                xml.write(pydevd_xml.var_to_xml(val, k, evaluate_full_value=evaluate_full_value))
                timer.report_if_compute_repr_attr_slow(self.attributes, k, type(val))

            xml.write("</xml>")
            cmd = dbg.cmd_factory.make_get_variable_message(self.sequence, xml.getvalue())
            xml.close()
            dbg.writer.add_command(cmd)
        except Exception:
            cmd = dbg.cmd_factory.make_error_message(self.sequence, "Error resolving variables %s" % (get_exception_traceback_str(),))
            dbg.writer.add_command(cmd)


class InternalGetArray(InternalThreadCommand):
    def __init__(self, seq, roffset, coffset, rows, cols, format, thread_id, frame_id, scope, attrs):
        self.sequence = seq
        self.thread_id = thread_id
        self.frame_id = frame_id
        self.scope = scope
        self.name = attrs.split("\t")[-1]
        self.attrs = attrs
        self.roffset = int(roffset)
        self.coffset = int(coffset)
        self.rows = int(rows)
        self.cols = int(cols)
        self.format = format

    def do_it(self, dbg):
        try:
            frame = dbg.find_frame(self.thread_id, self.frame_id)
            var = pydevd_vars.eval_in_context(self.name, frame.f_globals, frame.f_locals, py_db=dbg)
            xml = pydevd_vars.table_like_struct_to_xml(var, self.name, self.roffset, self.coffset, self.rows, self.cols, self.format)
            cmd = dbg.cmd_factory.make_get_array_message(self.sequence, xml)
            dbg.writer.add_command(cmd)
        except:
            cmd = dbg.cmd_factory.make_error_message(self.sequence, "Error resolving array: " + get_exception_traceback_str())
            dbg.writer.add_command(cmd)


def internal_change_variable(dbg, seq, thread_id, frame_id, scope, attr, value):
    """Changes the value of a variable"""
    try:
        frame = dbg.find_frame(thread_id, frame_id)
        if frame is not None:
            result = pydevd_vars.change_attr_expression(frame, attr, value, dbg)
        else:
            result = None
        xml = "<xml>"
        xml += pydevd_xml.var_to_xml(result, "")
        xml += "</xml>"
        cmd = dbg.cmd_factory.make_variable_changed_message(seq, xml)
        dbg.writer.add_command(cmd)
    except Exception:
        cmd = dbg.cmd_factory.make_error_message(
            seq, "Error changing variable attr:%s expression:%s traceback:%s" % (attr, value, get_exception_traceback_str())
        )
        dbg.writer.add_command(cmd)


def internal_change_variable_json(py_db, request):
    """
    The pydevd_vars.change_attr_expression(thread_id, frame_id, attr, value, dbg) can only
    deal with changing at a frame level, so, currently changing the contents of something
    in a different scope is currently not supported.

    :param SetVariableRequest request:
    """
    # : :type arguments: SetVariableArguments
    arguments = request.arguments
    variables_reference = arguments.variablesReference
    scope = None
    if isinstance_checked(variables_reference, ScopeRequest):
        scope = variables_reference
        variables_reference = variables_reference.variable_reference

    fmt = arguments.format
    if hasattr(fmt, "to_dict"):
        fmt = fmt.to_dict()

    try:
        variable = py_db.suspended_frames_manager.get_variable(variables_reference)
    except KeyError:
        variable = None

    if variable is None:
        _write_variable_response(
            py_db, request, value="", success=False, message="Unable to find variable container to change: %s." % (variables_reference,)
        )
        return

    child_var = variable.change_variable(arguments.name, arguments.value, py_db, fmt=fmt, scope=scope)

    if child_var is None:
        _write_variable_response(py_db, request, value="", success=False, message="Unable to change: %s." % (arguments.name,))
        return

    var_data = child_var.get_var_data(fmt=fmt)
    body = SetVariableResponseBody(
        value=var_data["value"],
        type=var_data["type"],
        variablesReference=var_data.get("variablesReference"),
        namedVariables=var_data.get("namedVariables"),
        indexedVariables=var_data.get("indexedVariables"),
    )
    variables_response = pydevd_base_schema.build_response(request, kwargs={"body": body})
    py_db.writer.add_command(NetCommand(CMD_RETURN, 0, variables_response, is_json=True))


def _write_variable_response(py_db, request, value, success, message):
    body = SetVariableResponseBody("")
    variables_response = pydevd_base_schema.build_response(request, kwargs={"body": body, "success": False, "message": message})
    cmd = NetCommand(CMD_RETURN, 0, variables_response, is_json=True)
    py_db.writer.add_command(cmd)


@silence_warnings_decorator
def internal_get_frame(dbg, seq, thread_id, frame_id):
    """Converts request into python variable"""
    try:
        frame = dbg.find_frame(thread_id, frame_id)
        if frame is not None:
            hidden_ns = pydevconsole.get_ipython_hidden_vars()
            xml = "<xml>"
            xml += pydevd_xml.frame_vars_to_xml(frame.f_locals, hidden_ns)
            del frame
            xml += "</xml>"
            cmd = dbg.cmd_factory.make_get_frame_message(seq, xml)
            dbg.writer.add_command(cmd)
        else:
            # pydevd_vars.dump_frames(thread_id)
            # don't print this error: frame not found: means that the client is not synchronized (but that's ok)
            cmd = dbg.cmd_factory.make_error_message(seq, "Frame not found: %s from thread: %s" % (frame_id, thread_id))
            dbg.writer.add_command(cmd)
    except:
        cmd = dbg.cmd_factory.make_error_message(seq, "Error resolving frame: %s from thread: %s" % (frame_id, thread_id))
        dbg.writer.add_command(cmd)


def internal_get_smart_step_into_variants(dbg, seq, thread_id, frame_id, start_line, end_line, set_additional_thread_info):
    try:
        thread = pydevd_find_thread_by_id(thread_id)
        frame = dbg.find_frame(thread_id, frame_id)

        if thread is None or frame is None:
            cmd = dbg.cmd_factory.make_error_message(seq, "Frame not found: %s from thread: %s" % (frame_id, thread_id))
            dbg.writer.add_command(cmd)
            return

        if pydevd_bytecode_utils is None:
            variants = []
        else:
            variants = pydevd_bytecode_utils.calculate_smart_step_into_variants(frame, int(start_line), int(end_line))

        info = set_additional_thread_info(thread)

        # Store the last request (may be used afterwards when stepping).
        info.pydev_smart_step_into_variants = tuple(variants)
        xml = "<xml>"

        for variant in variants:
            if variant.children_variants:
                for child_variant in variant.children_variants:
                    # If there are child variants, the current one is just an intermediary, so,
                    # just create variants for the child (notifying properly about the parent too).
                    xml += (
                        '<variant name="%s" isVisited="%s" line="%s" offset="%s" childOffset="%s" callOrder="%s" endlineno="%s" startcol="%s" endcol="%s"/>'
                        % (
                            quote(child_variant.name),
                            str(child_variant.is_visited).lower(),
                            child_variant.line,
                            variant.offset,
                            child_variant.offset,
                            child_variant.call_order,
                            variant.endlineno,
                            variant.startcol,
                            variant.endcol,
                        )
                    )
            else:
                xml += (
                    '<variant name="%s" isVisited="%s" line="%s" offset="%s" childOffset="-1" callOrder="%s" endlineno="%s" startcol="%s" endcol="%s"/>'
                    % (
                        quote(variant.name),
                        str(variant.is_visited).lower(),
                        variant.line,
                        variant.offset,
                        variant.call_order,
                        variant.endlineno,
                        variant.startcol,
                        variant.endcol,
                    )
                )

        xml += "</xml>"
        cmd = NetCommand(CMD_GET_SMART_STEP_INTO_VARIANTS, seq, xml)
        dbg.writer.add_command(cmd)
    except:
        # Error is expected (if `dis` module cannot be used -- i.e.: Jython).
        pydev_log.exception("Error calculating Smart Step Into Variants.")
        cmd = dbg.cmd_factory.make_error_message(
            seq, "Error getting smart step into variants for frame: %s from thread: %s" % (frame_id, thread_id)
        )
        dbg.writer.add_command(cmd)


def internal_get_step_in_targets_json(dbg, seq, thread_id, frame_id, request, set_additional_thread_info):
    try:
        thread = pydevd_find_thread_by_id(thread_id)
        frame = dbg.find_frame(thread_id, frame_id)

        if thread is None or frame is None:
            body = StepInTargetsResponseBody([])
            variables_response = pydevd_base_schema.build_response(
                request, kwargs={"body": body, "success": False, "message": "Thread to get step in targets seems to have resumed already."}
            )
            cmd = NetCommand(CMD_RETURN, 0, variables_response, is_json=True)
            dbg.writer.add_command(cmd)
            return

        start_line = 0
        end_line = 99999999
        if pydevd_bytecode_utils is None:
            variants = []
        else:
            variants = pydevd_bytecode_utils.calculate_smart_step_into_variants(frame, start_line, end_line)

        info = set_additional_thread_info(thread)
        targets = []
        counter = itertools.count(0)
        target_id_to_variant = {}
        for variant in variants:
            if not variant.is_visited:
                if variant.children_variants:
                    for child_variant in variant.children_variants:
                        target_id = next(counter)

                        if child_variant.call_order > 1:
                            targets.append(
                                StepInTarget(
                                    id=target_id,
                                    label="%s (call %s)" % (child_variant.name, child_variant.call_order),
                                )
                            )
                        else:
                            targets.append(StepInTarget(id=target_id, label=child_variant.name))
                        target_id_to_variant[target_id] = child_variant

                        if len(targets) >= 15:  # Show at most 15 targets.
                            break
                else:
                    target_id = next(counter)
                    if variant.call_order > 1:
                        targets.append(
                            StepInTarget(
                                id=target_id,
                                label="%s (call %s)" % (variant.name, variant.call_order),
                            )
                        )
                    else:
                        targets.append(StepInTarget(id=target_id, label=variant.name))
                    target_id_to_variant[target_id] = variant

                    if len(targets) >= 15:  # Show at most 15 targets.
                        break

        # Store the last request (may be used afterwards when stepping).
        info.pydev_smart_step_into_variants = tuple(variants)
        info.target_id_to_smart_step_into_variant = target_id_to_variant

        body = StepInTargetsResponseBody(targets=targets)
        response = pydevd_base_schema.build_response(request, kwargs={"body": body})
        cmd = NetCommand(CMD_RETURN, 0, response, is_json=True)
        dbg.writer.add_command(cmd)
    except Exception as e:
        # Error is expected (if `dis` module cannot be used -- i.e.: Jython).
        pydev_log.exception("Error calculating Smart Step Into Variants.")
        body = StepInTargetsResponseBody([])
        variables_response = pydevd_base_schema.build_response(request, kwargs={"body": body, "success": False, "message": str(e)})
        cmd = NetCommand(CMD_RETURN, 0, variables_response, is_json=True)
        dbg.writer.add_command(cmd)


def internal_get_next_statement_targets(dbg, seq, thread_id, frame_id):
    """gets the valid line numbers for use with set next statement"""
    try:
        frame = dbg.find_frame(thread_id, frame_id)
        if frame is not None:
            code = frame.f_code
            xml = "<xml>"
            try:
                linestarts = dis.findlinestarts(code)
            except:
                # i.e.: jython doesn't provide co_lnotab, so, we can only keep at the current line.
                xml += "<line>%d</line>" % (frame.f_lineno,)
            else:
                for _, line in linestarts:
                    if line is not None:
                        xml += "<line>%d</line>" % (line,)
            del frame
            xml += "</xml>"
            cmd = dbg.cmd_factory.make_get_next_statement_targets_message(seq, xml)
            dbg.writer.add_command(cmd)
        else:
            cmd = dbg.cmd_factory.make_error_message(seq, "Frame not found: %s from thread: %s" % (frame_id, thread_id))
            dbg.writer.add_command(cmd)
    except:
        cmd = dbg.cmd_factory.make_error_message(seq, "Error resolving frame: %s from thread: %s" % (frame_id, thread_id))
        dbg.writer.add_command(cmd)


def _evaluate_response(py_db, request, result, error_message=""):
    is_error = isinstance(result, ExceptionOnEvaluate)
    if is_error:
        result = result.result
    if not error_message:
        body = pydevd_schema.EvaluateResponseBody(result=result, variablesReference=0)
        variables_response = pydevd_base_schema.build_response(request, kwargs={"body": body})
        py_db.writer.add_command(NetCommand(CMD_RETURN, 0, variables_response, is_json=True))
    else:
        body = pydevd_schema.EvaluateResponseBody(result=result, variablesReference=0)
        variables_response = pydevd_base_schema.build_response(request, kwargs={"body": body, "success": False, "message": error_message})
        py_db.writer.add_command(NetCommand(CMD_RETURN, 0, variables_response, is_json=True))


_global_frame = None


def internal_evaluate_expression_json(py_db, request, thread_id):
    """
    :param EvaluateRequest request:
    """
    global _global_frame
    # : :type arguments: EvaluateArguments

    arguments = request.arguments
    expression = arguments.expression
    frame_id = arguments.frameId
    context = arguments.context
    fmt = arguments.format
    if hasattr(fmt, "to_dict"):
        fmt = fmt.to_dict()

    ctx = NULL
    if context == "repl":
        if not py_db.is_output_redirected:
            ctx = pydevd_io.redirect_stream_to_pydb_io_messages_context()
    else:
        # If we're not in a repl (watch, hover, ...) don't show warnings.
        ctx = filter_all_warnings()

    with ctx:
        try_exec = False
        if frame_id is None:
            if _global_frame is None:
                # Lazily create a frame to be used for evaluation with no frame id.

                def __create_frame():
                    yield sys._getframe()

                _global_frame = next(__create_frame())

            frame = _global_frame
            try_exec = True  # Always exec in this case
            eval_result = None
        else:
            frame = py_db.find_frame(thread_id, frame_id)

            eval_result = pydevd_vars.evaluate_expression(py_db, frame, expression, is_exec=False)
            is_error = isinstance_checked(eval_result, ExceptionOnEvaluate)
            if is_error:
                if context == "hover":  # In a hover it doesn't make sense to do an exec.
                    _evaluate_response(py_db, request, result="", error_message="Exception occurred during evaluation.")
                    return
                elif context == "watch":
                    # If it's a watch, don't show it as an exception object, rather, format
                    # it and show it as a string (with success=False).
                    msg = "%s: %s" % (
                        eval_result.result.__class__.__name__,
                        eval_result.result,
                    )
                    _evaluate_response(py_db, request, result=msg, error_message=msg)
                    return
                else:
                    # We only try the exec if the failure we had was due to not being able
                    # to evaluate the expression.
                    try:
                        pydevd_vars.compile_as_eval(expression)
                    except Exception:
                        try_exec = context == "repl"
                    else:
                        try_exec = False
                        if context == "repl":
                            # In the repl we should show the exception to the user.
                            _evaluate_response_return_exception(py_db, request, eval_result.etype, eval_result.result, eval_result.tb)
                            return

        if try_exec:
            try:
                pydevd_vars.evaluate_expression(py_db, frame, expression, is_exec=True)
            except (Exception, KeyboardInterrupt):
                _evaluate_response_return_exception(py_db, request, *sys.exc_info())
                return
            # No result on exec.
            _evaluate_response(py_db, request, result="")
            return

        # Ok, we have the result (could be an error), let's put it into the saved variables.
        frame_tracker = py_db.suspended_frames_manager.get_frame_tracker(thread_id)
        if frame_tracker is None:
            # This is not really expected.
            _evaluate_response(py_db, request, result="", error_message="Thread id: %s is not current thread id." % (thread_id,))
            return

        safe_repr_custom_attrs = {}
        if context == "clipboard":
            safe_repr_custom_attrs = dict(
                maxstring_outer=2**64,
                maxstring_inner=2**64,
                maxother_outer=2**64,
                maxother_inner=2**64,
            )

        if context == "repl" and eval_result is None:
            # We don't want "None" to appear when typing in the repl.
            body = pydevd_schema.EvaluateResponseBody(
                result="",
                variablesReference=0,
            )

        else:
            variable = frame_tracker.obtain_as_variable(expression, eval_result, frame=frame)
            var_data = variable.get_var_data(fmt=fmt, context=context, **safe_repr_custom_attrs)

            body = pydevd_schema.EvaluateResponseBody(
                result=var_data["value"],
                variablesReference=var_data.get("variablesReference", 0),
                type=var_data.get("type"),
                presentationHint=var_data.get("presentationHint"),
                namedVariables=var_data.get("namedVariables"),
                indexedVariables=var_data.get("indexedVariables"),
            )
        variables_response = pydevd_base_schema.build_response(request, kwargs={"body": body})
        py_db.writer.add_command(NetCommand(CMD_RETURN, 0, variables_response, is_json=True))


def _evaluate_response_return_exception(py_db, request, exc_type, exc, initial_tb):
    try:
        tb = initial_tb

        # Show the traceback without pydevd frames.
        temp_tb = tb
        while temp_tb:
            if py_db.get_file_type(temp_tb.tb_frame) == PYDEV_FILE:
                tb = temp_tb.tb_next
            temp_tb = temp_tb.tb_next

        if tb is None:
            tb = initial_tb
        err = "".join(traceback.format_exception(exc_type, exc, tb))

        # Make sure we don't keep references to them.
        exc = None
        exc_type = None
        tb = None
        temp_tb = None
        initial_tb = None
    except:
        err = "<Internal error - unable to get traceback when evaluating expression>"
        pydev_log.exception(err)

    # Currently there is an issue in VSC where returning success=false for an
    # eval request, in repl context, VSC does not show the error response in
    # the debug console. So return the error message in result as well.
    _evaluate_response(py_db, request, result=err, error_message=err)


@silence_warnings_decorator
def internal_evaluate_expression(dbg, seq, thread_id, frame_id, expression, is_exec, trim_if_too_big, attr_to_set_result):
    """gets the value of a variable"""
    try:
        frame = dbg.find_frame(thread_id, frame_id)
        if frame is not None:
            result = pydevd_vars.evaluate_expression(dbg, frame, expression, is_exec)
            if attr_to_set_result != "":
                pydevd_vars.change_attr_expression(frame, attr_to_set_result, expression, dbg, result)
        else:
            result = None

        xml = "<xml>"
        xml += pydevd_xml.var_to_xml(result, expression, trim_if_too_big)
        xml += "</xml>"
        cmd = dbg.cmd_factory.make_evaluate_expression_message(seq, xml)
        dbg.writer.add_command(cmd)
    except:
        exc = get_exception_traceback_str()
        cmd = dbg.cmd_factory.make_error_message(seq, "Error evaluating expression " + exc)
        dbg.writer.add_command(cmd)


def _set_expression_response(py_db, request, error_message):
    body = pydevd_schema.SetExpressionResponseBody(value="")
    variables_response = pydevd_base_schema.build_response(request, kwargs={"body": body, "success": False, "message": error_message})
    py_db.writer.add_command(NetCommand(CMD_RETURN, 0, variables_response, is_json=True))


def internal_set_expression_json(py_db, request, thread_id):
    # : :type arguments: SetExpressionArguments

    arguments = request.arguments
    expression = arguments.expression
    frame_id = arguments.frameId
    value = arguments.value
    fmt = arguments.format
    if hasattr(fmt, "to_dict"):
        fmt = fmt.to_dict()

    frame = py_db.find_frame(thread_id, frame_id)
    exec_code = "%s = (%s)" % (expression, value)
    try:
        pydevd_vars.evaluate_expression(py_db, frame, exec_code, is_exec=True)
    except (Exception, KeyboardInterrupt):
        _set_expression_response(py_db, request, error_message="Error executing: %s" % (exec_code,))
        return

    # Ok, we have the result (could be an error), let's put it into the saved variables.
    frame_tracker = py_db.suspended_frames_manager.get_frame_tracker(thread_id)
    if frame_tracker is None:
        # This is not really expected.
        _set_expression_response(py_db, request, error_message="Thread id: %s is not current thread id." % (thread_id,))
        return

    # Now that the exec is done, get the actual value changed to return.
    result = pydevd_vars.evaluate_expression(py_db, frame, expression, is_exec=False)
    variable = frame_tracker.obtain_as_variable(expression, result, frame=frame)
    var_data = variable.get_var_data(fmt=fmt)

    body = pydevd_schema.SetExpressionResponseBody(
        value=var_data["value"],
        variablesReference=var_data.get("variablesReference", 0),
        type=var_data.get("type"),
        presentationHint=var_data.get("presentationHint"),
        namedVariables=var_data.get("namedVariables"),
        indexedVariables=var_data.get("indexedVariables"),
    )
    variables_response = pydevd_base_schema.build_response(request, kwargs={"body": body})
    py_db.writer.add_command(NetCommand(CMD_RETURN, 0, variables_response, is_json=True))


def internal_get_completions(dbg, seq, thread_id, frame_id, act_tok, line=-1, column=-1):
    """
    Note that if the column is >= 0, the act_tok is considered text and the actual
    activation token/qualifier is computed in this command.
    """
    try:
        remove_path = None
        try:
            qualifier = ""
            if column >= 0:
                token_and_qualifier = extract_token_and_qualifier(act_tok, line, column)
                act_tok = token_and_qualifier[0]
                if act_tok:
                    act_tok += "."
                qualifier = token_and_qualifier[1]

            frame = dbg.find_frame(thread_id, frame_id)
            if frame is not None:
                completions = _pydev_completer.generate_completions(frame, act_tok)

                # Note that qualifier and start are only actually valid for the
                # Debug Adapter Protocol (for the line-based protocol, the IDE
                # is required to filter the completions returned).
                cmd = dbg.cmd_factory.make_get_completions_message(seq, completions, qualifier, start=column - len(qualifier))
                dbg.writer.add_command(cmd)
            else:
                cmd = dbg.cmd_factory.make_error_message(
                    seq, "internal_get_completions: Frame not found: %s from thread: %s" % (frame_id, thread_id)
                )
                dbg.writer.add_command(cmd)

        finally:
            if remove_path is not None:
                sys.path.remove(remove_path)

    except:
        exc = get_exception_traceback_str()
        sys.stderr.write("%s\n" % (exc,))
        cmd = dbg.cmd_factory.make_error_message(seq, "Error evaluating expression " + exc)
        dbg.writer.add_command(cmd)


def internal_get_description(dbg, seq, thread_id, frame_id, expression):
    """Fetch the variable description stub from the debug console"""
    try:
        frame = dbg.find_frame(thread_id, frame_id)
        description = pydevd_console.get_description(frame, thread_id, frame_id, expression)
        description = pydevd_xml.make_valid_xml_value(quote(description, "/>_= \t"))
        description_xml = '<xml><var name="" type="" value="%s"/></xml>' % description
        cmd = dbg.cmd_factory.make_get_description_message(seq, description_xml)
        dbg.writer.add_command(cmd)
    except:
        exc = get_exception_traceback_str()
        cmd = dbg.cmd_factory.make_error_message(seq, "Error in fetching description" + exc)
        dbg.writer.add_command(cmd)


def build_exception_info_response(dbg, thread_id, thread, request_seq, set_additional_thread_info, iter_visible_frames_info, max_frames):
    """
    :return ExceptionInfoResponse
    """
    additional_info = set_additional_thread_info(thread)
    topmost_frame = additional_info.get_topmost_frame(thread)

    current_paused_frame_name = ""

    source_path = ""  # This is an extra bit of data used by Visual Studio
    stack_str_lst = []
    name = None
    description = None

    if topmost_frame is not None:
        try:
            try:
                frames_list = dbg.suspended_frames_manager.get_frames_list(thread_id)
                while frames_list is not None and len(frames_list):
                    frames = []

                    frame = None

                    if not name:
                        exc_type = frames_list.exc_type
                        if exc_type is not None:
                            try:
                                name = exc_type.__qualname__
                            except:
                                try:
                                    name = exc_type.__name__
                                except:
                                    try:
                                        name = str(exc_type)
                                    except:
                                        pass

                    if not description:
                        exc_desc = frames_list.exc_desc
                        if exc_desc is not None:
                            try:
                                description = str(exc_desc)
                            except:
                                pass

                    for (
                        frame_id,
                        frame,
                        method_name,
                        original_filename,
                        filename_in_utf8,
                        lineno,
                        _applied_mapping,
                        show_as_current_frame,
                        line_col_info,
                    ) in iter_visible_frames_info(dbg, frames_list):
                        line_text = linecache.getline(original_filename, lineno)

                        # Never filter out plugin frames!
                        if not getattr(frame, "IS_PLUGIN_FRAME", False):
                            if dbg.is_files_filter_enabled and dbg.apply_files_filter(frame, original_filename, False):
                                continue

                        if show_as_current_frame:
                            current_paused_frame_name = method_name
                            method_name += " (Current frame)"
                        frames.append((filename_in_utf8, lineno, method_name, line_text, line_col_info))

                    if not source_path and frames:
                        source_path = frames[0][0]

                    if IS_PY311_OR_GREATER:
                        stack_summary = traceback.StackSummary()
                        for filename_in_utf8, lineno, method_name, line_text, line_col_info in frames[-max_frames:]:
                            if line_col_info is not None:
                                # End line might mean that we have a multiline statement.
                                if line_col_info.end_lineno is not None and lineno < line_col_info.end_lineno:
                                    line_text = "\n".join(linecache.getlines(filename_in_utf8)[lineno : line_col_info.end_lineno + 1])
                                frame_summary = traceback.FrameSummary(
                                    filename_in_utf8, 
                                    lineno, 
                                    method_name, 
                                    line=line_text, 
                                    end_lineno=line_col_info.end_lineno, 
                                    colno=line_col_info.colno, 
                                    end_colno=line_col_info.end_colno)
                                stack_summary.append(frame_summary)
                            else:
                                frame_summary = traceback.FrameSummary(filename_in_utf8, lineno, method_name, line=line_text)
                                stack_summary.append(frame_summary)

                        stack_str = "".join(stack_summary.format())

                    else:
                        # Note: remove col info (just used in 3.11).
                        stack_str = "".join(traceback.format_list((x[:-1] for x in frames[-max_frames:])))

                    try:
                        stype = frames_list.exc_type.__qualname__
                        smod = frames_list.exc_type.__module__
                        if smod not in ("__main__", "builtins"):
                            if not isinstance(smod, str):
                                smod = "<unknown>"
                            stype = smod + "." + stype
                    except Exception:
                        stype = "<unable to get exception type>"
                        pydev_log.exception("Error getting exception type.")

                    stack_str += "%s: %s\n" % (stype, frames_list.exc_desc)
                    stack_str += frames_list.exc_context_msg
                    stack_str_lst.append(stack_str)

                    frames_list = frames_list.chained_frames_list
                    if frames_list is None or not frames_list:
                        break

            except:
                pydev_log.exception("Error on build_exception_info_response.")
        finally:
            topmost_frame = None
    full_stack_str = "".join(reversed(stack_str_lst))

    if not name:
        name = "exception: type unknown"
    if not description:
        description = "exception: no description"

    if current_paused_frame_name:
        name += "       (note: full exception trace is shown but execution is paused at: %s)" % (current_paused_frame_name,)

    if thread.stop_reason == CMD_STEP_CAUGHT_EXCEPTION:
        break_mode = pydevd_schema.ExceptionBreakMode.ALWAYS
    else:
        break_mode = pydevd_schema.ExceptionBreakMode.UNHANDLED

    response = pydevd_schema.ExceptionInfoResponse(
        request_seq=request_seq,
        success=True,
        command="exceptionInfo",
        body=pydevd_schema.ExceptionInfoResponseBody(
            exceptionId=name,
            description=description,
            breakMode=break_mode,
            details=pydevd_schema.ExceptionDetails(
                message=description,
                typeName=name,
                stackTrace=full_stack_str,
                source=source_path,
                # Note: ExceptionDetails actually accepts an 'innerException', but
                # when passing it, VSCode is not showing the stack trace at all.
            ),
        ),
    )
    return response


def internal_get_exception_details_json(
    dbg, request, thread_id, thread, max_frames, set_additional_thread_info=None, iter_visible_frames_info=None
):
    """Fetch exception details"""
    try:
        response = build_exception_info_response(
            dbg, thread_id, thread, request.seq, set_additional_thread_info, iter_visible_frames_info, max_frames
        )
    except:
        exc = get_exception_traceback_str()
        response = pydevd_base_schema.build_response(request, kwargs={"success": False, "message": exc, "body": {}})
    dbg.writer.add_command(NetCommand(CMD_RETURN, 0, response, is_json=True))


class InternalGetBreakpointException(InternalThreadCommand):
    """Send details of exception raised while evaluating conditional breakpoint"""

    def __init__(self, thread_id, exc_type, stacktrace):
        self.sequence = 0
        self.thread_id = thread_id
        self.stacktrace = stacktrace
        self.exc_type = exc_type

    def do_it(self, dbg):
        try:
            callstack = "<xml>"

            makeValid = pydevd_xml.make_valid_xml_value

            for filename, line, methodname, methodobj in self.stacktrace:
                if not filesystem_encoding_is_utf8 and hasattr(filename, "decode"):
                    # filename is a byte string encoded using the file system encoding
                    # convert it to utf8
                    filename = filename.decode(file_system_encoding).encode("utf-8")

                callstack += '<frame thread_id = "%s" file="%s" line="%s" name="%s" obj="%s" />' % (
                    self.thread_id,
                    makeValid(filename),
                    line,
                    makeValid(methodname),
                    makeValid(methodobj),
                )
            callstack += "</xml>"

            cmd = dbg.cmd_factory.make_send_breakpoint_exception_message(self.sequence, self.exc_type + "\t" + callstack)
            dbg.writer.add_command(cmd)
        except:
            exc = get_exception_traceback_str()
            sys.stderr.write("%s\n" % (exc,))
            cmd = dbg.cmd_factory.make_error_message(self.sequence, "Error Sending Exception: " + exc)
            dbg.writer.add_command(cmd)


class InternalSendCurrExceptionTrace(InternalThreadCommand):
    """Send details of the exception that was caught and where we've broken in."""

    def __init__(self, thread_id, arg, curr_frame_id):
        """
        :param arg: exception type, description, traceback object
        """
        self.sequence = 0
        self.thread_id = thread_id
        self.curr_frame_id = curr_frame_id
        self.arg = arg

    def do_it(self, dbg):
        try:
            cmd = dbg.cmd_factory.make_send_curr_exception_trace_message(dbg, self.sequence, self.thread_id, self.curr_frame_id, *self.arg)
            del self.arg
            dbg.writer.add_command(cmd)
        except:
            exc = get_exception_traceback_str()
            sys.stderr.write("%s\n" % (exc,))
            cmd = dbg.cmd_factory.make_error_message(self.sequence, "Error Sending Current Exception Trace: " + exc)
            dbg.writer.add_command(cmd)


class InternalSendCurrExceptionTraceProceeded(InternalThreadCommand):
    """Send details of the exception that was caught and where we've broken in."""

    def __init__(self, thread_id):
        self.sequence = 0
        self.thread_id = thread_id

    def do_it(self, dbg):
        try:
            cmd = dbg.cmd_factory.make_send_curr_exception_trace_proceeded_message(self.sequence, self.thread_id)
            dbg.writer.add_command(cmd)
        except:
            exc = get_exception_traceback_str()
            sys.stderr.write("%s\n" % (exc,))
            cmd = dbg.cmd_factory.make_error_message(self.sequence, "Error Sending Current Exception Trace Proceeded: " + exc)
            dbg.writer.add_command(cmd)


class InternalEvaluateConsoleExpression(InternalThreadCommand):
    """Execute the given command in the debug console"""

    def __init__(self, seq, thread_id, frame_id, line, buffer_output=True):
        self.sequence = seq
        self.thread_id = thread_id
        self.frame_id = frame_id
        self.line = line
        self.buffer_output = buffer_output

    def do_it(self, dbg):
        """Create an XML for console output, error and more (true/false)
        <xml>
            <output message=output_message></output>
            <error message=error_message></error>
            <more>true/false</more>
        </xml>
        """
        try:
            frame = dbg.find_frame(self.thread_id, self.frame_id)
            if frame is not None:
                console_message = pydevd_console.execute_console_command(
                    frame, self.thread_id, self.frame_id, self.line, self.buffer_output
                )

                cmd = dbg.cmd_factory.make_send_console_message(self.sequence, console_message.to_xml())
            else:
                from _pydevd_bundle.pydevd_console import ConsoleMessage

                console_message = ConsoleMessage()
                console_message.add_console_message(
                    pydevd_console.CONSOLE_ERROR,
                    "Select the valid frame in the debug view (thread: %s, frame: %s invalid)" % (self.thread_id, self.frame_id),
                )
                cmd = dbg.cmd_factory.make_error_message(self.sequence, console_message.to_xml())
        except:
            exc = get_exception_traceback_str()
            cmd = dbg.cmd_factory.make_error_message(self.sequence, "Error evaluating expression " + exc)
        dbg.writer.add_command(cmd)


class InternalRunCustomOperation(InternalThreadCommand):
    """Run a custom command on an expression"""

    def __init__(self, seq, thread_id, frame_id, scope, attrs, style, encoded_code_or_file, fnname):
        self.sequence = seq
        self.thread_id = thread_id
        self.frame_id = frame_id
        self.scope = scope
        self.attrs = attrs
        self.style = style
        self.code_or_file = unquote_plus(encoded_code_or_file)
        self.fnname = fnname

    def do_it(self, dbg):
        try:
            res = pydevd_vars.custom_operation(
                dbg, self.thread_id, self.frame_id, self.scope, self.attrs, self.style, self.code_or_file, self.fnname
            )
            resEncoded = quote_plus(res)
            cmd = dbg.cmd_factory.make_custom_operation_message(self.sequence, resEncoded)
            dbg.writer.add_command(cmd)
        except:
            exc = get_exception_traceback_str()
            cmd = dbg.cmd_factory.make_error_message(self.sequence, "Error in running custom operation" + exc)
            dbg.writer.add_command(cmd)


class InternalConsoleGetCompletions(InternalThreadCommand):
    """Fetch the completions in the debug console"""

    def __init__(self, seq, thread_id, frame_id, act_tok):
        self.sequence = seq
        self.thread_id = thread_id
        self.frame_id = frame_id
        self.act_tok = act_tok

    def do_it(self, dbg):
        """Get completions and write back to the client"""
        try:
            frame = dbg.find_frame(self.thread_id, self.frame_id)
            completions_xml = pydevd_console.get_completions(frame, self.act_tok)
            cmd = dbg.cmd_factory.make_send_console_message(self.sequence, completions_xml)
            dbg.writer.add_command(cmd)
        except:
            exc = get_exception_traceback_str()
            cmd = dbg.cmd_factory.make_error_message(self.sequence, "Error in fetching completions" + exc)
            dbg.writer.add_command(cmd)


class InternalConsoleExec(InternalThreadCommand):
    """gets the value of a variable"""

    def __init__(self, seq, thread_id, frame_id, expression):
        self.sequence = seq
        self.thread_id = thread_id
        self.frame_id = frame_id
        self.expression = expression

    def init_matplotlib_in_debug_console(self, py_db):
        # import hook and patches for matplotlib support in debug console
        from _pydev_bundle.pydev_import_hook import import_hook_manager

        if is_current_thread_main_thread():
            for module in list(py_db.mpl_modules_for_patching):
                import_hook_manager.add_module_name(module, py_db.mpl_modules_for_patching.pop(module))

    def do_it(self, py_db):
        if not py_db.mpl_hooks_in_debug_console and not py_db.gui_in_use:
            # add import hooks for matplotlib patches if only debug console was started
            try:
                self.init_matplotlib_in_debug_console(py_db)
                py_db.gui_in_use = True
            except:
                pydev_log.debug("Matplotlib support in debug console failed", traceback.format_exc())
            py_db.mpl_hooks_in_debug_console = True

        try:
            try:
                # Don't trace new threads created by console command.
                disable_trace_thread_modules()

                result = pydevconsole.console_exec(self.thread_id, self.frame_id, self.expression, py_db)
                xml = "<xml>"
                xml += pydevd_xml.var_to_xml(result, "")
                xml += "</xml>"
                cmd = py_db.cmd_factory.make_evaluate_expression_message(self.sequence, xml)
                py_db.writer.add_command(cmd)
            except:
                exc = get_exception_traceback_str()
                sys.stderr.write("%s\n" % (exc,))
                cmd = py_db.cmd_factory.make_error_message(self.sequence, "Error evaluating console expression " + exc)
                py_db.writer.add_command(cmd)
        finally:
            enable_trace_thread_modules()

            sys.stderr.flush()
            sys.stdout.flush()


class InternalLoadFullValue(InternalThreadCommand):
    """
    Loads values asynchronously
    """

    def __init__(self, seq, thread_id, frame_id, vars):
        self.sequence = seq
        self.thread_id = thread_id
        self.frame_id = frame_id
        self.vars = vars

    @silence_warnings_decorator
    def do_it(self, dbg):
        """Starts a thread that will load values asynchronously"""
        try:
            var_objects = []
            for variable in self.vars:
                variable = variable.strip()
                if len(variable) > 0:
                    if "\t" in variable:  # there are attributes beyond scope
                        scope, attrs = variable.split("\t", 1)
                        name = attrs[0]
                    else:
                        scope, attrs = (variable, None)
                        name = scope
                    var_obj = pydevd_vars.getVariable(dbg, self.thread_id, self.frame_id, scope, attrs)
                    var_objects.append((var_obj, name))

            t = GetValueAsyncThreadDebug(dbg, dbg, self.sequence, var_objects)
            t.start()
        except:
            exc = get_exception_traceback_str()
            sys.stderr.write("%s\n" % (exc,))
            cmd = dbg.cmd_factory.make_error_message(self.sequence, "Error evaluating variable %s " % exc)
            dbg.writer.add_command(cmd)


class AbstractGetValueAsyncThread(PyDBDaemonThread):
    """
    Abstract class for a thread, which evaluates values for async variables
    """

    def __init__(self, py_db, frame_accessor, seq, var_objects):
        PyDBDaemonThread.__init__(self, py_db)
        self.frame_accessor = frame_accessor
        self.seq = seq
        self.var_objs = var_objects
        self.cancel_event = ThreadingEvent()

    def send_result(self, xml):
        raise NotImplementedError()

    @overrides(PyDBDaemonThread._on_run)
    def _on_run(self):
        start = time.time()
        xml = StringIO()
        xml.write("<xml>")
        for var_obj, name in self.var_objs:
            current_time = time.time()
            if current_time - start > ASYNC_EVAL_TIMEOUT_SEC or self.cancel_event.is_set():
                break
            xml.write(pydevd_xml.var_to_xml(var_obj, name, evaluate_full_value=True))
        xml.write("</xml>")
        self.send_result(xml)
        xml.close()


class GetValueAsyncThreadDebug(AbstractGetValueAsyncThread):
    """
    A thread for evaluation async values, which returns result for debugger
    Create message and send it via writer thread
    """

    def send_result(self, xml):
        if self.frame_accessor is not None:
            cmd = self.frame_accessor.cmd_factory.make_load_full_value_message(self.seq, xml.getvalue())
            self.frame_accessor.writer.add_command(cmd)


class GetValueAsyncThreadConsole(AbstractGetValueAsyncThread):
    """
    A thread for evaluation async values, which returns result for Console
    Send result directly to Console's server
    """

    def send_result(self, xml):
        if self.frame_accessor is not None:
            self.frame_accessor.ReturnFullValue(self.seq, xml.getvalue())

# === NexusCore/openenv\Lib\site-packages\win32\lib\win32traceutil.py ===
# This is a helper for the win32trace module

# If imported from a normal Python program, it sets up sys.stdout and sys.stderr
# so output goes to the collector.

# If run from the command line, it creates a collector loop.

# Eg:
# C:>start win32traceutil.py (or python.exe win32traceutil.py)
# will start a process with a (pretty much) blank screen.
#
# then, switch to a DOS prompt, and type:
# C:>python.exe
# Python X.X.X (#0, Apr 13 1999, ...
# >>> import win32traceutil
# Redirecting output to win32trace remote collector
# >>> print("Hello")
# >>>
# And the output will appear in the first collector process.

# Note - the client or the collector can be started first.
# There is a 0x20000 byte buffer.  If this gets full, it is reset, and new
# output appended from the start.

import win32trace


def RunAsCollector():
    import sys

    try:
        import win32api

        win32api.SetConsoleTitle("Python Trace Collector")
    except:
        pass  # Oh well!
    win32trace.InitRead()
    print("Collecting Python Trace Output...")
    try:
        while 1:
            # a short timeout means ctrl+c works next time we wake...
            sys.stdout.write(win32trace.blockingread(500))
    except KeyboardInterrupt:
        print("Ctrl+C")


def SetupForPrint():
    win32trace.InitWrite()
    try:  # Under certain servers, sys.stdout may be invalid.
        print("Redirecting output to win32trace remote collector")
    except:
        pass
    win32trace.setprint()  # this works in an rexec environment.


if __name__ == "__main__":
    RunAsCollector()
else:
    SetupForPrint()

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\crash.py ===
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
Crash dump support.

@group Crash reporting:
    Crash, CrashDictionary

@group Warnings:
    CrashWarning

@group Deprecated classes:
    CrashContainer, CrashTable, CrashTableMSSQL,
    VolatileCrashContainer, DummyCrashContainer
"""

__revision__ = "$Id$"

__all__ = [
    # Object that represents a crash in the debugee.
    "Crash",
    # Crash storage.
    "CrashDictionary",
    # Warnings.
    "CrashWarning",
    # Backwards compatibility with WinAppDbg 1.4 and before.
    "CrashContainer",
    "CrashTable",
    "CrashTableMSSQL",
    "VolatileCrashContainer",
    "DummyCrashContainer",
]

from winappdbg import win32
from winappdbg import compat
from winappdbg.system import System
from winappdbg.textio import HexDump, CrashDump
from winappdbg.util import StaticClass, MemoryAddresses, PathOperations

import sys
import os
import time
import zlib
import warnings

# lazy imports
sql = None
anydbm = None

# ==============================================================================

# Secure alternative to pickle, use it if present.
try:
    import cerealizer

    pickle = cerealizer

    # There is no optimization function for cerealized objects.
    def optimize(picklestring):
        return picklestring

    # There is no HIGHEST_PROTOCOL in cerealizer.
    HIGHEST_PROTOCOL = 0

    # Note: it's important NOT to provide backwards compatibility, otherwise
    # it'd be just the same as not having this!
    #
    # To disable this security upgrade simply uncomment the following line:
    #
    # raise ImportError("Fallback to pickle for backwards compatibility")

# If cerealizer is not present fallback to the insecure pickle module.
except ImportError:
    # Faster implementation of the pickle module as a C extension.
    try:
        import cPickle as pickle

    # If all fails fallback to the classic pickle module.
    except ImportError:
        import pickle

    # Fetch the highest protocol version.
    HIGHEST_PROTOCOL = pickle.HIGHEST_PROTOCOL

    # Try to use the pickle optimizer if found.
    try:
        from pickletools import optimize
    except ImportError:

        def optimize(picklestring):
            return picklestring


class Marshaller(StaticClass):
    """
    Custom pickler for L{Crash} objects. Optimizes the pickled data when using
    the standard C{pickle} (or C{cPickle}) module. The pickled data is then
    compressed using zlib.
    """

    @staticmethod
    def dumps(obj, protocol=HIGHEST_PROTOCOL):
        return zlib.compress(optimize(pickle.dumps(obj)), 9)

    @staticmethod
    def loads(data):
        return pickle.loads(zlib.decompress(data))


# ==============================================================================


class CrashWarning(Warning):
    """
    An error occurred while gathering crash data.
    Some data may be incomplete or missing.
    """


# ==============================================================================


# Crash object. Must be serializable.
class Crash(object):
    """
    Represents a crash, bug, or another interesting event in the debugee.

    @group Basic information:
        timeStamp, signature, eventCode, eventName, pid, tid, arch, os, bits,
        registers, labelPC, pc, sp, fp

    @group Optional information:
        debugString,
        modFileName,
        lpBaseOfDll,
        exceptionCode,
        exceptionName,
        exceptionDescription,
        exceptionAddress,
        exceptionLabel,
        firstChance,
        faultType,
        faultAddress,
        faultLabel,
        isOurBreakpoint,
        isSystemBreakpoint,
        stackTrace,
        stackTracePC,
        stackTraceLabels,
        stackTracePretty

    @group Extra information:
        commandLine,
        environment,
        environmentData,
        registersPeek,
        stackRange,
        stackFrame,
        stackPeek,
        faultCode,
        faultMem,
        faultPeek,
        faultDisasm,
        memoryMap

    @group Report:
        briefReport, fullReport, notesReport, environmentReport, isExploitable

    @group Notes:
        addNote, getNotes, iterNotes, hasNotes, clearNotes, notes

    @group Miscellaneous:
        fetch_extra_data

    @type timeStamp: float
    @ivar timeStamp: Timestamp as returned by time.time().

    @type signature: object
    @ivar signature: Approximately unique signature for the Crash object.

        This signature can be used as an heuristic to determine if two crashes
        were caused by the same software error. Ideally it should be treated as
        as opaque serializable object that can be tested for equality.

    @type notes: list( str )
    @ivar notes: List of strings, each string is a note.

    @type eventCode: int
    @ivar eventCode: Event code as defined by the Win32 API.

    @type eventName: str
    @ivar eventName: Event code user-friendly name.

    @type pid: int
    @ivar pid: Process global ID.

    @type tid: int
    @ivar tid: Thread global ID.

    @type arch: str
    @ivar arch: Processor architecture.

    @type os: str
    @ivar os: Operating system version.

        May indicate a 64 bit version even if L{arch} and L{bits} indicate 32
        bits. This means the crash occurred inside a WOW64 process.

    @type bits: int
    @ivar bits: C{32} or C{64} bits.

    @type commandLine: None or str
    @ivar commandLine: Command line for the target process.

        C{None} if unapplicable or unable to retrieve.

    @type environmentData: None or list of str
    @ivar environmentData: Environment data for the target process.

        C{None} if unapplicable or unable to retrieve.

    @type environment: None or dict( str S{->} str )
    @ivar environment: Environment variables for the target process.

        C{None} if unapplicable or unable to retrieve.

    @type registers: dict( str S{->} int )
    @ivar registers: Dictionary mapping register names to their values.

    @type registersPeek: None or dict( str S{->} str )
    @ivar registersPeek: Dictionary mapping register names to the data they point to.

        C{None} if unapplicable or unable to retrieve.

    @type labelPC: None or str
    @ivar labelPC: Label pointing to the program counter.

        C{None} or invalid if unapplicable or unable to retrieve.

    @type debugString: None or str
    @ivar debugString: Debug string sent by the debugee.

        C{None} if unapplicable or unable to retrieve.

    @type exceptionCode: None or int
    @ivar exceptionCode: Exception code as defined by the Win32 API.

        C{None} if unapplicable or unable to retrieve.

    @type exceptionName: None or str
    @ivar exceptionName: Exception code user-friendly name.

        C{None} if unapplicable or unable to retrieve.

    @type exceptionDescription: None or str
    @ivar exceptionDescription: Exception description.

        C{None} if unapplicable or unable to retrieve.

    @type exceptionAddress: None or int
    @ivar exceptionAddress: Memory address where the exception occured.

        C{None} if unapplicable or unable to retrieve.

    @type exceptionLabel: None or str
    @ivar exceptionLabel: Label pointing to the exception address.

        C{None} or invalid if unapplicable or unable to retrieve.

    @type faultType: None or int
    @ivar faultType: Access violation type.
        Only applicable to memory faults.
        Should be one of the following constants:

         - L{win32.ACCESS_VIOLATION_TYPE_READ}
         - L{win32.ACCESS_VIOLATION_TYPE_WRITE}
         - L{win32.ACCESS_VIOLATION_TYPE_DEP}

        C{None} if unapplicable or unable to retrieve.

    @type faultAddress: None or int
    @ivar faultAddress: Access violation memory address.
        Only applicable to memory faults.

        C{None} if unapplicable or unable to retrieve.

    @type faultLabel: None or str
    @ivar faultLabel: Label pointing to the access violation memory address.
        Only applicable to memory faults.

        C{None} if unapplicable or unable to retrieve.

    @type firstChance: None or bool
    @ivar firstChance:
        C{True} for first chance exceptions, C{False} for second chance.

        C{None} if unapplicable or unable to retrieve.

    @type isOurBreakpoint: bool
    @ivar isOurBreakpoint:
        C{True} for breakpoints defined by the L{Debug} class,
        C{False} otherwise.

        C{None} if unapplicable.

    @type isSystemBreakpoint: bool
    @ivar isSystemBreakpoint:
        C{True} for known system-defined breakpoints,
        C{False} otherwise.

        C{None} if unapplicable.

    @type modFileName: None or str
    @ivar modFileName: File name of module where the program counter points to.

        C{None} or invalid if unapplicable or unable to retrieve.

    @type lpBaseOfDll: None or int
    @ivar lpBaseOfDll: Base of module where the program counter points to.

        C{None} if unapplicable or unable to retrieve.

    @type stackTrace: None or tuple of tuple( int, int, str )
    @ivar stackTrace:
        Stack trace of the current thread as a tuple of
        ( frame pointer, return address, module filename ).

        C{None} or empty if unapplicable or unable to retrieve.

    @type stackTracePretty: None or tuple of tuple( int, str )
    @ivar stackTracePretty:
        Stack trace of the current thread as a tuple of
        ( frame pointer, return location ).

        C{None} or empty if unapplicable or unable to retrieve.

    @type stackTracePC: None or tuple( int... )
    @ivar stackTracePC: Tuple of return addresses in the stack trace.

        C{None} or empty if unapplicable or unable to retrieve.

    @type stackTraceLabels: None or tuple( str... )
    @ivar stackTraceLabels:
        Tuple of labels pointing to the return addresses in the stack trace.

        C{None} or empty if unapplicable or unable to retrieve.

    @type stackRange: tuple( int, int )
    @ivar stackRange:
        Stack beginning and end pointers, in memory addresses order.

        C{None} if unapplicable or unable to retrieve.

    @type stackFrame: None or str
    @ivar stackFrame: Data pointed to by the stack pointer.

        C{None} or empty if unapplicable or unable to retrieve.

    @type stackPeek: None or dict( int S{->} str )
    @ivar stackPeek: Dictionary mapping stack offsets to the data they point to.

        C{None} or empty if unapplicable or unable to retrieve.

    @type faultCode: None or str
    @ivar faultCode: Data pointed to by the program counter.

        C{None} or empty if unapplicable or unable to retrieve.

    @type faultMem: None or str
    @ivar faultMem: Data pointed to by the exception address.

        C{None} or empty if unapplicable or unable to retrieve.

    @type faultPeek: None or dict( intS{->} str )
    @ivar faultPeek: Dictionary mapping guessed pointers at L{faultMem} to the data they point to.

        C{None} or empty if unapplicable or unable to retrieve.

    @type faultDisasm: None or tuple of tuple( long, int, str, str )
    @ivar faultDisasm: Dissassembly around the program counter.

        C{None} or empty if unapplicable or unable to retrieve.

    @type memoryMap: None or list of L{win32.MemoryBasicInformation} objects.
    @ivar memoryMap: Memory snapshot of the program. May contain the actual
        data from the entire process memory if requested.
        See L{fetch_extra_data} for more details.

        C{None} or empty if unapplicable or unable to retrieve.

    @type _rowid: int
    @ivar _rowid: Row ID in the database. Internally used by the DAO layer.
        Only present in crash dumps retrieved from the database. Do not rely
        on this property to be present in future versions of WinAppDbg.
    """

    def __init__(self, event):
        """
        @type  event: L{Event}
        @param event: Event object for crash.
        """

        # First of all, take the timestamp.
        self.timeStamp = time.time()

        # Notes are initially empty.
        self.notes = list()

        # Get the process and thread, but dont't store them in the DB.
        process = event.get_process()
        thread = event.get_thread()

        # Determine the architecture.
        self.os = System.os
        self.arch = process.get_arch()
        self.bits = process.get_bits()

        # The following properties are always retrieved for all events.
        self.eventCode = event.get_event_code()
        self.eventName = event.get_event_name()
        self.pid = event.get_pid()
        self.tid = event.get_tid()
        self.registers = dict(thread.get_context())
        self.labelPC = process.get_label_at_address(self.pc)

        # The following properties are only retrieved for some events.
        self.commandLine = None
        self.environment = None
        self.environmentData = None
        self.registersPeek = None
        self.debugString = None
        self.modFileName = None
        self.lpBaseOfDll = None
        self.exceptionCode = None
        self.exceptionName = None
        self.exceptionDescription = None
        self.exceptionAddress = None
        self.exceptionLabel = None
        self.firstChance = None
        self.faultType = None
        self.faultAddress = None
        self.faultLabel = None
        self.isOurBreakpoint = None
        self.isSystemBreakpoint = None
        self.stackTrace = None
        self.stackTracePC = None
        self.stackTraceLabels = None
        self.stackTracePretty = None
        self.stackRange = None
        self.stackFrame = None
        self.stackPeek = None
        self.faultCode = None
        self.faultMem = None
        self.faultPeek = None
        self.faultDisasm = None
        self.memoryMap = None

        # Get information for debug string events.
        if self.eventCode == win32.OUTPUT_DEBUG_STRING_EVENT:
            self.debugString = event.get_debug_string()

        # Get information for module load and unload events.
        # For create and exit process events, get the information
        # for the main module.
        elif self.eventCode in (
            win32.CREATE_PROCESS_DEBUG_EVENT,
            win32.EXIT_PROCESS_DEBUG_EVENT,
            win32.LOAD_DLL_DEBUG_EVENT,
            win32.UNLOAD_DLL_DEBUG_EVENT,
        ):
            aModule = event.get_module()
            self.modFileName = event.get_filename()
            if not self.modFileName:
                self.modFileName = aModule.get_filename()
            self.lpBaseOfDll = event.get_module_base()
            if not self.lpBaseOfDll:
                self.lpBaseOfDll = aModule.get_base()

        # Get some information for exception events.
        # To get the remaining information call fetch_extra_data().
        elif self.eventCode == win32.EXCEPTION_DEBUG_EVENT:
            # Exception information.
            self.exceptionCode = event.get_exception_code()
            self.exceptionName = event.get_exception_name()
            self.exceptionDescription = event.get_exception_description()
            self.exceptionAddress = event.get_exception_address()
            self.firstChance = event.is_first_chance()
            self.exceptionLabel = process.get_label_at_address(self.exceptionAddress)
            if self.exceptionCode in (win32.EXCEPTION_ACCESS_VIOLATION, win32.EXCEPTION_GUARD_PAGE, win32.EXCEPTION_IN_PAGE_ERROR):
                self.faultType = event.get_fault_type()
                self.faultAddress = event.get_fault_address()
                self.faultLabel = process.get_label_at_address(self.faultAddress)
            elif self.exceptionCode in (win32.EXCEPTION_BREAKPOINT, win32.EXCEPTION_SINGLE_STEP):
                self.isOurBreakpoint = hasattr(event, "breakpoint") and event.breakpoint
                self.isSystemBreakpoint = process.is_system_defined_breakpoint(self.exceptionAddress)

            # Stack trace.
            try:
                self.stackTracePretty = thread.get_stack_trace_with_labels()
            except Exception:
                e = sys.exc_info()[1]
                warnings.warn("Cannot get stack trace with labels, reason: %s" % str(e), CrashWarning)
            try:
                self.stackTrace = thread.get_stack_trace()
                stackTracePC = [ra for (_, ra, _) in self.stackTrace]
                self.stackTracePC = tuple(stackTracePC)
                stackTraceLabels = [process.get_label_at_address(ra) for ra in self.stackTracePC]
                self.stackTraceLabels = tuple(stackTraceLabels)
            except Exception:
                e = sys.exc_info()[1]
                warnings.warn("Cannot get stack trace, reason: %s" % str(e), CrashWarning)

    def fetch_extra_data(self, event, takeMemorySnapshot=0):
        """
        Fetch extra data from the L{Event} object.

        @note: Since this method may take a little longer to run, it's best to
            call it only after you've determined the crash is interesting and
            you want to save it.

        @type  event: L{Event}
        @param event: Event object for crash.

        @type  takeMemorySnapshot: int
        @param takeMemorySnapshot:
            Memory snapshot behavior:
             - C{0} to take no memory information (default).
             - C{1} to take only the memory map.
               See L{Process.get_memory_map}.
             - C{2} to take a full memory snapshot.
               See L{Process.take_memory_snapshot}.
             - C{3} to take a live memory snapshot.
               See L{Process.generate_memory_snapshot}.
        """

        # Get the process and thread, we'll use them below.
        process = event.get_process()
        thread = event.get_thread()

        # Get the command line for the target process.
        try:
            self.commandLine = process.get_command_line()
        except Exception:
            e = sys.exc_info()[1]
            warnings.warn("Cannot get command line, reason: %s" % str(e), CrashWarning)

        # Get the environment variables for the target process.
        try:
            self.environmentData = process.get_environment_data()
            self.environment = process.parse_environment_data(self.environmentData)
        except Exception:
            e = sys.exc_info()[1]
            warnings.warn("Cannot get environment, reason: %s" % str(e), CrashWarning)

        # Data pointed to by registers.
        self.registersPeek = thread.peek_pointers_in_registers()

        # Module where execution is taking place.
        aModule = process.get_module_at_address(self.pc)
        if aModule is not None:
            self.modFileName = aModule.get_filename()
            self.lpBaseOfDll = aModule.get_base()

        # Contents of the stack frame.
        try:
            self.stackRange = thread.get_stack_range()
        except Exception:
            e = sys.exc_info()[1]
            warnings.warn("Cannot get stack range, reason: %s" % str(e), CrashWarning)
        try:
            self.stackFrame = thread.get_stack_frame()
            stackFrame = self.stackFrame
        except Exception:
            self.stackFrame = thread.peek_stack_data()
            stackFrame = self.stackFrame[:64]
        if stackFrame:
            self.stackPeek = process.peek_pointers_in_data(stackFrame)

        # Code being executed.
        self.faultCode = thread.peek_code_bytes()
        try:
            self.faultDisasm = thread.disassemble_around_pc(32)
        except Exception:
            e = sys.exc_info()[1]
            warnings.warn("Cannot disassemble, reason: %s" % str(e), CrashWarning)

        # For memory related exceptions, get the memory contents
        # of the location that caused the exception to be raised.
        if self.eventCode == win32.EXCEPTION_DEBUG_EVENT:
            if self.pc != self.exceptionAddress and self.exceptionCode in (
                win32.EXCEPTION_ACCESS_VIOLATION,
                win32.EXCEPTION_ARRAY_BOUNDS_EXCEEDED,
                win32.EXCEPTION_DATATYPE_MISALIGNMENT,
                win32.EXCEPTION_IN_PAGE_ERROR,
                win32.EXCEPTION_STACK_OVERFLOW,
                win32.EXCEPTION_GUARD_PAGE,
            ):
                self.faultMem = process.peek(self.exceptionAddress, 64)
                if self.faultMem:
                    self.faultPeek = process.peek_pointers_in_data(self.faultMem)

        # TODO: maybe add names and versions of DLLs and EXE?

        # Take a snapshot of the process memory. Additionally get the
        # memory contents if requested.
        if takeMemorySnapshot == 1:
            self.memoryMap = process.get_memory_map()
            mappedFilenames = process.get_mapped_filenames(self.memoryMap)
            for mbi in self.memoryMap:
                mbi.filename = mappedFilenames.get(mbi.BaseAddress, None)
                mbi.content = None
        elif takeMemorySnapshot == 2:
            self.memoryMap = process.take_memory_snapshot()
        elif takeMemorySnapshot == 3:
            self.memoryMap = process.generate_memory_snapshot()

    @property
    def pc(self):
        """
        Value of the program counter register.

        @rtype:  int
        """
        try:
            return self.registers["Eip"]  # i386
        except KeyError:
            return self.registers["Rip"]  # amd64

    @property
    def sp(self):
        """
        Value of the stack pointer register.

        @rtype:  int
        """
        try:
            return self.registers["Esp"]  # i386
        except KeyError:
            return self.registers["Rsp"]  # amd64

    @property
    def fp(self):
        """
        Value of the frame pointer register.

        @rtype:  int
        """
        try:
            return self.registers["Ebp"]  # i386
        except KeyError:
            return self.registers["Rbp"]  # amd64

    def __str__(self):
        return self.fullReport()

    def key(self):
        """
        Alias of L{signature}. Deprecated since WinAppDbg 1.5.
        """
        warnings.warn("Crash.key() method was deprecated in WinAppDbg 1.5", DeprecationWarning)
        return self.signature

    @property
    def signature(self):
        if self.labelPC:
            pc = self.labelPC
        else:
            pc = self.pc
        if self.stackTraceLabels:
            trace = self.stackTraceLabels
        else:
            trace = self.stackTracePC
        return (
            self.arch,
            self.eventCode,
            self.exceptionCode,
            pc,
            trace,
            self.debugString,
        )
        # TODO
        # add the name and version of the binary where the crash happened?

    def isExploitable(self):
        """
        Guess how likely is it that the bug causing the crash can be leveraged
        into an exploitable vulnerability.

        @note: Don't take this as an equivalent of a real exploitability
            analysis, that can only be done by a human being! This is only
            a guideline, useful for example to sort crashes - placing the most
            interesting ones at the top.

        @see: The heuristics are similar to those of the B{!exploitable}
            extension for I{WinDBG}, which can be downloaded from here:

            U{http://www.codeplex.com/msecdbg}

        @rtype: tuple( str, str, str )
        @return: The first element of the tuple is the result of the analysis,
            being one of the following:

             - Not an exception
             - Not exploitable
             - Not likely exploitable
             - Unknown
             - Probably exploitable
             - Exploitable

            The second element of the tuple is a code to identify the matched
            heuristic rule.

            The third element of the tuple is a description string of the
            reason behind the result.
        """

        # Terminal rules

        if self.eventCode != win32.EXCEPTION_DEBUG_EVENT:
            return ("Not an exception", "NotAnException", "The event is not an exception.")

        if self.stackRange and self.pc is not None and self.stackRange[0] <= self.pc < self.stackRange[1]:
            return ("Exploitable", "StackCodeExecution", "Code execution from the stack is considered exploitable.")

        # This rule is NOT from !exploitable
        if self.stackRange and self.sp is not None and not (self.stackRange[0] <= self.sp < self.stackRange[1]):
            return ("Exploitable", "StackPointerCorruption", "Stack pointer corruption is considered exploitable.")

        if self.exceptionCode == win32.EXCEPTION_ILLEGAL_INSTRUCTION:
            return (
                "Exploitable",
                "IllegalInstruction",
                "An illegal instruction exception indicates that the attacker controls execution flow.",
            )

        if self.exceptionCode == win32.EXCEPTION_PRIV_INSTRUCTION:
            return (
                "Exploitable",
                "PrivilegedInstruction",
                "A privileged instruction exception indicates that the attacker controls execution flow.",
            )

        if self.exceptionCode == win32.EXCEPTION_GUARD_PAGE:
            return (
                "Exploitable",
                "GuardPage",
                "A guard page violation indicates a stack overflow has occured, and the stack of another thread was reached (possibly the overflow length is not controlled by the attacker).",
            )

        if self.exceptionCode == win32.STATUS_STACK_BUFFER_OVERRUN:
            return (
                "Exploitable",
                "GSViolation",
                "An overrun of a protected stack buffer has been detected. This is considered exploitable, and must be fixed.",
            )

        if self.exceptionCode == win32.STATUS_HEAP_CORRUPTION:
            return (
                "Exploitable",
                "HeapCorruption",
                "Heap Corruption has been detected. This is considered exploitable, and must be fixed.",
            )

        if self.exceptionCode == win32.EXCEPTION_ACCESS_VIOLATION:
            nearNull = self.faultAddress is None or MemoryAddresses.align_address_to_page_start(self.faultAddress) == 0
            controlFlow = self.__is_control_flow()
            blockDataMove = self.__is_block_data_move()
            if self.faultType == win32.EXCEPTION_EXECUTE_FAULT:
                if nearNull:
                    return (
                        "Probably exploitable",
                        "DEPViolation",
                        "User mode DEP access violations are probably exploitable if near NULL.",
                    )
                else:
                    return ("Exploitable", "DEPViolation", "User mode DEP access violations are exploitable.")
            elif self.faultType == win32.EXCEPTION_WRITE_FAULT:
                if nearNull:
                    return (
                        "Probably exploitable",
                        "WriteAV",
                        "User mode write access violations that are near NULL are probably exploitable.",
                    )
                else:
                    return ("Exploitable", "WriteAV", "User mode write access violations that are not near NULL are exploitable.")
            elif self.faultType == win32.EXCEPTION_READ_FAULT:
                if self.faultAddress == self.pc:
                    if nearNull:
                        return (
                            "Probably exploitable",
                            "ReadAVonIP",
                            "Access violations at the instruction pointer are probably exploitable if near NULL.",
                        )
                    else:
                        return (
                            "Exploitable",
                            "ReadAVonIP",
                            "Access violations at the instruction pointer are exploitable if not near NULL.",
                        )
                if controlFlow:
                    if nearNull:
                        return (
                            "Probably exploitable",
                            "ReadAVonControlFlow",
                            "Access violations near null in control flow instructions are considered probably exploitable.",
                        )
                    else:
                        return (
                            "Exploitable",
                            "ReadAVonControlFlow",
                            "Access violations not near null in control flow instructions are considered exploitable.",
                        )
                if blockDataMove:
                    return (
                        "Probably exploitable",
                        "ReadAVonBlockMove",
                        "This is a read access violation in a block data move, and is therefore classified as probably exploitable.",
                    )

                # Rule: Tainted information used to control branch addresses is considered probably exploitable
                # Rule: Tainted information used to control the target of a later write is probably exploitable

        # Non terminal rules

        # XXX TODO add rule to check if code is in writeable memory (probably exploitable)

        # XXX TODO maybe we should be returning a list of tuples instead?

        result = ("Unknown", "Unknown", "Exploitability unknown.")

        if self.exceptionCode == win32.EXCEPTION_ACCESS_VIOLATION:
            if self.faultType == win32.EXCEPTION_READ_FAULT:
                if nearNull:
                    result = (
                        "Not likely exploitable",
                        "ReadAVNearNull",
                        "This is a user mode read access violation near null, and is probably not exploitable.",
                    )

        elif self.exceptionCode == win32.EXCEPTION_INT_DIVIDE_BY_ZERO:
            result = ("Not likely exploitable", "DivideByZero", "This is an integer divide by zero, and is probably not exploitable.")

        elif self.exceptionCode == win32.EXCEPTION_FLT_DIVIDE_BY_ZERO:
            result = ("Not likely exploitable", "DivideByZero", "This is a floating point divide by zero, and is probably not exploitable.")

        elif self.exceptionCode in (win32.EXCEPTION_BREAKPOINT, win32.STATUS_WX86_BREAKPOINT):
            result = (
                "Unknown",
                "Breakpoint",
                "While a breakpoint itself is probably not exploitable, it may also be an indication that an attacker is testing a target. In either case breakpoints should not exist in production code.",
            )

        # Rule: If the stack contains unknown symbols in user mode, call that out
        # Rule: Tainted information used to control the source of a later block move unknown, but called out explicitly
        # Rule: Tainted information used as an argument to a function is an unknown risk, but called out explicitly
        # Rule: Tainted information used to control branch selection is an unknown risk, but called out explicitly

        return result

    def __is_control_flow(self):
        """
        Private method to tell if the instruction pointed to by the program
        counter is a control flow instruction.

        Currently only works for x86 and amd64 architectures.
        """
        jump_instructions = (
            "jmp",
            "jecxz",
            "jcxz",
            "ja",
            "jnbe",
            "jae",
            "jnb",
            "jb",
            "jnae",
            "jbe",
            "jna",
            "jc",
            "je",
            "jz",
            "jnc",
            "jne",
            "jnz",
            "jnp",
            "jpo",
            "jp",
            "jpe",
            "jg",
            "jnle",
            "jge",
            "jnl",
            "jl",
            "jnge",
            "jle",
            "jng",
            "jno",
            "jns",
            "jo",
            "js",
        )
        call_instructions = ("call", "ret", "retn")
        loop_instructions = ("loop", "loopz", "loopnz", "loope", "loopne")
        control_flow_instructions = call_instructions + loop_instructions + jump_instructions
        isControlFlow = False
        instruction = None
        if self.pc is not None and self.faultDisasm:
            for disasm in self.faultDisasm:
                if disasm[0] == self.pc:
                    instruction = disasm[2].lower().strip()
                    break
        if instruction:
            for x in control_flow_instructions:
                if x in instruction:
                    isControlFlow = True
                    break
        return isControlFlow

    def __is_block_data_move(self):
        """
        Private method to tell if the instruction pointed to by the program
        counter is a block data move instruction.

        Currently only works for x86 and amd64 architectures.
        """
        block_data_move_instructions = ("movs", "stos", "lods")
        isBlockDataMove = False
        instruction = None
        if self.pc is not None and self.faultDisasm:
            for disasm in self.faultDisasm:
                if disasm[0] == self.pc:
                    instruction = disasm[2].lower().strip()
                    break
        if instruction:
            for x in block_data_move_instructions:
                if x in instruction:
                    isBlockDataMove = True
                    break
        return isBlockDataMove

    def briefReport(self):
        """
        @rtype:  str
        @return: Short description of the event.
        """
        if self.exceptionCode is not None:
            if self.exceptionCode == win32.EXCEPTION_BREAKPOINT:
                if self.isOurBreakpoint:
                    what = "Breakpoint hit"
                elif self.isSystemBreakpoint:
                    what = "System breakpoint hit"
                else:
                    what = "Assertion failed"
            elif self.exceptionDescription:
                what = self.exceptionDescription
            elif self.exceptionName:
                what = self.exceptionName
            else:
                what = "Exception %s" % HexDump.integer(self.exceptionCode, self.bits)
            if self.firstChance:
                chance = "first"
            else:
                chance = "second"
            if self.exceptionLabel:
                where = self.exceptionLabel
            elif self.exceptionAddress:
                where = HexDump.address(self.exceptionAddress, self.bits)
            elif self.labelPC:
                where = self.labelPC
            else:
                where = HexDump.address(self.pc, self.bits)
            msg = "%s (%s chance) at %s" % (what, chance, where)
        elif self.debugString is not None:
            if self.labelPC:
                where = self.labelPC
            else:
                where = HexDump.address(self.pc, self.bits)
            msg = "Debug string from %s: %r" % (where, self.debugString)
        else:
            if self.labelPC:
                where = self.labelPC
            else:
                where = HexDump.address(self.pc, self.bits)
            msg = "%s (%s) at %s" % (self.eventName, HexDump.integer(self.eventCode, self.bits), where)
        return msg

    def fullReport(self, bShowNotes=True):
        """
        @type  bShowNotes: bool
        @param bShowNotes: C{True} to show the user notes, C{False} otherwise.

        @rtype:  str
        @return: Long description of the event.
        """
        msg = self.briefReport()
        msg += "\n"

        if self.bits == 32:
            width = 16
        else:
            width = 8

        if self.eventCode == win32.EXCEPTION_DEBUG_EVENT:
            (exploitability, expcode, expdescription) = self.isExploitable()
            msg += "\nSecurity risk level: %s\n" % exploitability
            msg += "  %s\n" % expdescription

        if bShowNotes and self.notes:
            msg += "\nNotes:\n"
            msg += self.notesReport()

        if self.commandLine:
            msg += "\nCommand line: %s\n" % self.commandLine

        if self.environment:
            msg += "\nEnvironment:\n"
            msg += self.environmentReport()

        if not self.labelPC:
            base = HexDump.address(self.lpBaseOfDll, self.bits)
            if self.modFileName:
                fn = PathOperations.pathname_to_filename(self.modFileName)
                msg += "\nRunning in %s (%s)\n" % (fn, base)
            else:
                msg += "\nRunning in module at %s\n" % base

        if self.registers:
            msg += "\nRegisters:\n"
            msg += CrashDump.dump_registers(self.registers)
            if self.registersPeek:
                msg += "\n"
                msg += CrashDump.dump_registers_peek(self.registers, self.registersPeek, width=width)

        if self.faultDisasm:
            msg += "\nCode disassembly:\n"
            msg += CrashDump.dump_code(self.faultDisasm, self.pc, bits=self.bits)

        if self.stackTrace:
            msg += "\nStack trace:\n"
            if self.stackTracePretty:
                msg += CrashDump.dump_stack_trace_with_labels(self.stackTracePretty, bits=self.bits)
            else:
                msg += CrashDump.dump_stack_trace(self.stackTrace, bits=self.bits)

        if self.stackFrame:
            if self.stackPeek:
                msg += "\nStack pointers:\n"
                msg += CrashDump.dump_stack_peek(self.stackPeek, width=width)
            msg += "\nStack dump:\n"
            msg += HexDump.hexblock(self.stackFrame, self.sp, bits=self.bits, width=width)

        if self.faultCode and not self.modFileName:
            msg += "\nCode dump:\n"
            msg += HexDump.hexblock(self.faultCode, self.pc, bits=self.bits, width=width)

        if self.faultMem:
            if self.faultPeek:
                msg += "\nException address pointers:\n"
                msg += CrashDump.dump_data_peek(self.faultPeek, self.exceptionAddress, bits=self.bits, width=width)
            msg += "\nException address dump:\n"
            msg += HexDump.hexblock(self.faultMem, self.exceptionAddress, bits=self.bits, width=width)

        if self.memoryMap:
            msg += "\nMemory map:\n"
            mappedFileNames = dict()
            for mbi in self.memoryMap:
                if hasattr(mbi, "filename") and mbi.filename:
                    mappedFileNames[mbi.BaseAddress] = mbi.filename
            msg += CrashDump.dump_memory_map(self.memoryMap, mappedFileNames, bits=self.bits)

        if not msg.endswith("\n\n"):
            if not msg.endswith("\n"):
                msg += "\n"
            msg += "\n"
        return msg

    def environmentReport(self):
        """
        @rtype: str
        @return: The process environment variables,
            merged and formatted for a report.
        """
        msg = ""
        if self.environment:
            for key, value in compat.iteritems(self.environment):
                msg += "  %s=%s\n" % (key, value)
        return msg

    def notesReport(self):
        """
        @rtype:  str
        @return: All notes, merged and formatted for a report.
        """
        msg = ""
        if self.notes:
            for n in self.notes:
                n = n.strip("\n")
                if "\n" in n:
                    n = n.strip("\n")
                    msg += " * %s\n" % n.pop(0)
                    for x in n:
                        msg += "   %s\n" % x
                else:
                    msg += " * %s\n" % n
        return msg

    def addNote(self, msg):
        """
        Add a note to the crash event.

        @type msg:  str
        @param msg: Note text.
        """
        self.notes.append(msg)

    def clearNotes(self):
        """
        Clear the notes of this crash event.
        """
        self.notes = list()

    def getNotes(self):
        """
        Get the list of notes of this crash event.

        @rtype:  list( str )
        @return: List of notes.
        """
        return self.notes

    def iterNotes(self):
        """
        Iterate the notes of this crash event.

        @rtype:  listiterator
        @return: Iterator of the list of notes.
        """
        return self.notes.__iter__()

    def hasNotes(self):
        """
        @rtype:  bool
        @return: C{True} if there are notes for this crash event.
        """
        return bool(self.notes)


# ==============================================================================


class CrashContainer(object):
    """
    Old crash dump persistencer using a DBM database.
    Doesn't support duplicate crashes.

    @warning:
        DBM database support is provided for backwards compatibility with older
        versions of WinAppDbg. New applications should not use this class.
        Also, DBM databases in Python suffer from multiple problems that can
        easily be avoided by switching to a SQL database.

    @see: If you really must use a DBM database, try the standard C{shelve}
        module instead: U{http://docs.python.org/library/shelve.html}

    @group Marshalling configuration:
        optimizeKeys, optimizeValues, compressKeys, compressValues, escapeKeys,
        escapeValues, binaryKeys, binaryValues

    @type optimizeKeys: bool
    @cvar optimizeKeys: Ignored by the current implementation.

        Up to WinAppDbg 1.4 this setting caused the database keys to be
        optimized when pickled with the standard C{pickle} module.

        But with a DBM database backend that causes inconsistencies, since the
        same key can be serialized into multiple optimized pickles, thus losing
        uniqueness.

    @type optimizeValues: bool
    @cvar optimizeValues: C{True} to optimize the marshalling of keys, C{False}
        otherwise. Only used with the C{pickle} module, ignored when using the
        more secure C{cerealizer} module.

    @type compressKeys: bool
    @cvar compressKeys: C{True} to compress keys when marshalling, C{False}
        to leave them uncompressed.

    @type compressValues: bool
    @cvar compressValues: C{True} to compress values when marshalling, C{False}
        to leave them uncompressed.

    @type escapeKeys: bool
    @cvar escapeKeys: C{True} to escape keys when marshalling, C{False}
        to leave them uncompressed.

    @type escapeValues: bool
    @cvar escapeValues: C{True} to escape values when marshalling, C{False}
        to leave them uncompressed.

    @type binaryKeys: bool
    @cvar binaryKeys: C{True} to marshall keys to binary format (the Python
        C{buffer} type), C{False} to use text marshalled keys (C{str} type).

    @type binaryValues: bool
    @cvar binaryValues: C{True} to marshall values to binary format (the Python
        C{buffer} type), C{False} to use text marshalled values (C{str} type).
    """

    optimizeKeys = False
    optimizeValues = True
    compressKeys = False
    compressValues = True
    escapeKeys = False
    escapeValues = False
    binaryKeys = False
    binaryValues = False

    def __init__(self, filename=None, allowRepeatedKeys=False):
        """
        @type  filename: str
        @param filename: (Optional) File name for crash database.
            If no filename is specified, the container is volatile.

            Volatile containers are stored only in memory and
            destroyed when they go out of scope.

        @type  allowRepeatedKeys: bool
        @param allowRepeatedKeys:
            Currently not supported, always use C{False}.
        """
        if allowRepeatedKeys:
            raise NotImplementedError()
        self.__filename = filename
        if filename:
            global anydbm
            if not anydbm:
                import anydbm
            self.__db = anydbm.open(filename, "c")
            self.__keys = dict([(self.unmarshall_key(mk), mk) for mk in self.__db.keys()])
        else:
            self.__db = dict()
            self.__keys = dict()

    def remove_key(self, key):
        """
        Removes the given key from the set of known keys.

        @type  key: L{Crash} key.
        @param key: Key to remove.
        """
        del self.__keys[key]

    def marshall_key(self, key):
        """
        Marshalls a Crash key to be used in the database.

        @see: L{__init__}

        @type  key: L{Crash} key.
        @param key: Key to convert.

        @rtype:  str or buffer
        @return: Converted key.
        """
        if key in self.__keys:
            return self.__keys[key]
        skey = pickle.dumps(key, protocol=0)
        if self.compressKeys:
            skey = zlib.compress(skey, zlib.Z_BEST_COMPRESSION)
        if self.escapeKeys:
            skey = skey.encode("hex")
        if self.binaryKeys:
            skey = buffer(skey)
        self.__keys[key] = skey
        return skey

    def unmarshall_key(self, key):
        """
        Unmarshalls a Crash key read from the database.

        @type  key: str or buffer
        @param key: Key to convert.

        @rtype:  L{Crash} key.
        @return: Converted key.
        """
        key = str(key)
        if self.escapeKeys:
            key = key.decode("hex")
        if self.compressKeys:
            key = zlib.decompress(key)
        key = pickle.loads(key)
        return key

    def marshall_value(self, value, storeMemoryMap=False):
        """
        Marshalls a Crash object to be used in the database.
        By default the C{memoryMap} member is B{NOT} stored here.

        @warning: Setting the C{storeMemoryMap} argument to C{True} can lead to
            a severe performance penalty!

        @type  value: L{Crash}
        @param value: Object to convert.

        @type  storeMemoryMap: bool
        @param storeMemoryMap: C{True} to store the memory map, C{False}
            otherwise.

        @rtype:  str
        @return: Converted object.
        """
        if hasattr(value, "memoryMap"):
            crash = value
            memoryMap = crash.memoryMap
            try:
                crash.memoryMap = None
                if storeMemoryMap and memoryMap is not None:
                    # convert the generator to a list
                    crash.memoryMap = list(memoryMap)
                if self.optimizeValues:
                    value = pickle.dumps(crash, protocol=HIGHEST_PROTOCOL)
                    value = optimize(value)
                else:
                    value = pickle.dumps(crash, protocol=0)
            finally:
                crash.memoryMap = memoryMap
                del memoryMap
                del crash
        if self.compressValues:
            value = zlib.compress(value, zlib.Z_BEST_COMPRESSION)
        if self.escapeValues:
            value = value.encode("hex")
        if self.binaryValues:
            value = buffer(value)
        return value

    def unmarshall_value(self, value):
        """
        Unmarshalls a Crash object read from the database.

        @type  value: str
        @param value: Object to convert.

        @rtype:  L{Crash}
        @return: Converted object.
        """
        value = str(value)
        if self.escapeValues:
            value = value.decode("hex")
        if self.compressValues:
            value = zlib.decompress(value)
        value = pickle.loads(value)
        return value

    # The interface is meant to be similar to a Python set.
    # However it may not be necessary to implement all of the set methods.
    # Other methods like get, has_key, iterkeys and itervalues
    # are dictionary-like.

    def __len__(self):
        """
        @rtype:  int
        @return: Count of known keys.
        """
        return len(self.__keys)

    def __bool__(self):
        """
        @rtype:  bool
        @return: C{False} if there are no known keys.
        """
        return bool(self.__keys)

    def __contains__(self, crash):
        """
        @type  crash: L{Crash}
        @param crash: Crash object.

        @rtype:  bool
        @return:
            C{True} if a Crash object with the same key is in the container.
        """
        return self.has_key(crash.key())

    def has_key(self, key):
        """
        @type  key: L{Crash} key.
        @param key: Key to find.

        @rtype:  bool
        @return: C{True} if the key is present in the set of known keys.
        """
        return key in self.__keys

    def iterkeys(self):
        """
        @rtype:  iterator
        @return: Iterator of known L{Crash} keys.
        """
        return compat.iterkeys(self.__keys)

    class __CrashContainerIterator(object):
        """
        Iterator of Crash objects. Returned by L{CrashContainer.__iter__}.
        """

        def __init__(self, container):
            """
            @type  container: L{CrashContainer}
            @param container: Crash set to iterate.
            """
            # It's important to keep a reference to the CrashContainer,
            # rather than it's underlying database.
            # Otherwise the destructor of CrashContainer may close the
            # database while we're still iterating it.
            #
            # TODO: lock the database when iterating it.
            #
            self.__container = container
            self.__keys_iter = compat.iterkeys(container)

        def next(self):
            """
            @rtype:  L{Crash}
            @return: A B{copy} of a Crash object in the L{CrashContainer}.
            @raise StopIteration: No more items left.
            """
            key = self.__keys_iter.next()
            return self.__container.get(key)

    def __del__(self):
        "Class destructor. Closes the database when this object is destroyed."
        try:
            if self.__filename:
                self.__db.close()
        except:
            pass

    def __iter__(self):
        """
        @see:    L{itervalues}
        @rtype:  iterator
        @return: Iterator of the contained L{Crash} objects.
        """
        return self.itervalues()

    def itervalues(self):
        """
        @rtype:  iterator
        @return: Iterator of the contained L{Crash} objects.

        @warning: A B{copy} of each object is returned,
            so any changes made to them will be lost.

            To preserve changes do the following:
                1. Keep a reference to the object.
                2. Delete the object from the set.
                3. Modify the object and add it again.
        """
        return self.__CrashContainerIterator(self)

    def add(self, crash):
        """
        Adds a new crash to the container.
        If the crash appears to be already known, it's ignored.

        @see: L{Crash.key}

        @type  crash: L{Crash}
        @param crash: Crash object to add.
        """
        if crash not in self:
            key = crash.key()
            skey = self.marshall_key(key)
            data = self.marshall_value(crash, storeMemoryMap=True)
            self.__db[skey] = data

    def __delitem__(self, key):
        """
        Removes a crash from the container.

        @type  key: L{Crash} unique key.
        @param key: Key of the crash to get.
        """
        skey = self.marshall_key(key)
        del self.__db[skey]
        self.remove_key(key)

    def remove(self, crash):
        """
        Removes a crash from the container.

        @type  crash: L{Crash}
        @param crash: Crash object to remove.
        """
        del self[crash.key()]

    def get(self, key):
        """
        Retrieves a crash from the container.

        @type  key: L{Crash} unique key.
        @param key: Key of the crash to get.

        @rtype:  L{Crash} object.
        @return: Crash matching the given key.

        @see:     L{iterkeys}
        @warning: A B{copy} of each object is returned,
            so any changes made to them will be lost.

            To preserve changes do the following:
                1. Keep a reference to the object.
                2. Delete the object from the set.
                3. Modify the object and add it again.
        """
        skey = self.marshall_key(key)
        data = self.__db[skey]
        crash = self.unmarshall_value(data)
        return crash

    def __getitem__(self, key):
        """
        Retrieves a crash from the container.

        @type  key: L{Crash} unique key.
        @param key: Key of the crash to get.

        @rtype:  L{Crash} object.
        @return: Crash matching the given key.

        @see:     L{iterkeys}
        @warning: A B{copy} of each object is returned,
            so any changes made to them will be lost.

            To preserve changes do the following:
                1. Keep a reference to the object.
                2. Delete the object from the set.
                3. Modify the object and add it again.
        """
        return self.get(key)


# ==============================================================================


class CrashDictionary(object):
    """
    Dictionary-like persistence interface for L{Crash} objects.

    Currently the only implementation is through L{sql.CrashDAO}.
    """

    def __init__(self, url, creator=None, allowRepeatedKeys=True):
        """
        @type  url: str
        @param url: Connection URL of the crash database.
            See L{sql.CrashDAO.__init__} for more details.

        @type  creator: callable
        @param creator: (Optional) Callback function that creates the SQL
            database connection.

            Normally it's not necessary to use this argument. However in some
            odd cases you may need to customize the database connection, for
            example when using the integrated authentication in MSSQL.

        @type  allowRepeatedKeys: bool
        @param allowRepeatedKeys:
            If C{True} all L{Crash} objects are stored.

            If C{False} any L{Crash} object with the same signature as a
            previously existing object will be ignored.
        """
        global sql
        if sql is None:
            from winappdbg import sql
        self._allowRepeatedKeys = allowRepeatedKeys
        self._dao = sql.CrashDAO(url, creator)

    def add(self, crash):
        """
        Adds a new crash to the container.

        @note:
            When the C{allowRepeatedKeys} parameter of the constructor
            is set to C{False}, duplicated crashes are ignored.

        @see: L{Crash.key}

        @type  crash: L{Crash}
        @param crash: Crash object to add.
        """
        self._dao.add(crash, self._allowRepeatedKeys)

    def get(self, key):
        """
        Retrieves a crash from the container.

        @type  key: L{Crash} signature.
        @param key: Heuristic signature of the crash to get.

        @rtype:  L{Crash} object.
        @return: Crash matching the given signature. If more than one is found,
            retrieve the newest one.

        @see:     L{iterkeys}
        @warning: A B{copy} of each object is returned,
            so any changes made to them will be lost.

            To preserve changes do the following:
                1. Keep a reference to the object.
                2. Delete the object from the set.
                3. Modify the object and add it again.
        """
        found = self._dao.find(signature=key, limit=1, order=-1)
        if not found:
            raise KeyError(key)
        return found[0]

    def __iter__(self):
        """
        @rtype:  iterator
        @return: Iterator of the contained L{Crash} objects.
        """
        offset = 0
        limit = 10
        while 1:
            found = self._dao.find(offset=offset, limit=limit)
            if not found:
                break
            offset += len(found)
            for crash in found:
                yield crash

    def itervalues(self):
        """
        @rtype:  iterator
        @return: Iterator of the contained L{Crash} objects.
        """
        return self.__iter__()

    def iterkeys(self):
        """
        @rtype:  iterator
        @return: Iterator of the contained L{Crash} heuristic signatures.
        """
        for crash in self:
            yield crash.signature  # FIXME this gives repeated results!

    def __contains__(self, crash):
        """
        @type  crash: L{Crash}
        @param crash: Crash object.

        @rtype:  bool
        @return: C{True} if the Crash object is in the container.
        """
        return self._dao.count(signature=crash.signature) > 0

    def has_key(self, key):
        """
        @type  key: L{Crash} signature.
        @param key: Heuristic signature of the crash to get.

        @rtype:  bool
        @return: C{True} if a matching L{Crash} object is in the container.
        """
        return self._dao.count(signature=key) > 0

    def __len__(self):
        """
        @rtype:  int
        @return: Count of L{Crash} elements in the container.
        """
        return self._dao.count()

    def __bool__(self):
        """
        @rtype:  bool
        @return: C{False} if the container is empty.
        """
        return bool(len(self))


class CrashTable(CrashDictionary):
    """
    Old crash dump persistencer using a SQLite database.

    @warning:
        Superceded by L{CrashDictionary} since WinAppDbg 1.5.
        New applications should not use this class.
    """

    def __init__(self, location=None, allowRepeatedKeys=True):
        """
        @type  location: str
        @param location: (Optional) Location of the crash database.
            If the location is a filename, it's an SQLite database file.

            If no location is specified, the container is volatile.
            Volatile containers are stored only in memory and
            destroyed when they go out of scope.

        @type  allowRepeatedKeys: bool
        @param allowRepeatedKeys:
            If C{True} all L{Crash} objects are stored.

            If C{False} any L{Crash} object with the same signature as a
            previously existing object will be ignored.
        """
        warnings.warn("The %s class is deprecated since WinAppDbg 1.5." % self.__class__, DeprecationWarning)
        if location:
            url = "sqlite:///%s" % location
        else:
            url = "sqlite://"
        super(CrashTable, self).__init__(url, allowRepeatedKeys)


class CrashTableMSSQL(CrashDictionary):
    """
    Old crash dump persistencer using a Microsoft SQL Server database.

    @warning:
        Superceded by L{CrashDictionary} since WinAppDbg 1.5.
        New applications should not use this class.
    """

    def __init__(self, location=None, allowRepeatedKeys=True):
        """
        @type  location: str
        @param location: Location of the crash database.
            It must be an ODBC connection string.

        @type  allowRepeatedKeys: bool
        @param allowRepeatedKeys:
            If C{True} all L{Crash} objects are stored.

            If C{False} any L{Crash} object with the same signature as a
            previously existing object will be ignored.
        """
        warnings.warn("The %s class is deprecated since WinAppDbg 1.5." % self.__class__, DeprecationWarning)
        import urllib

        url = "mssql+pyodbc:///?odbc_connect=" + urllib.quote_plus(location)
        super(CrashTableMSSQL, self).__init__(url, allowRepeatedKeys)


class VolatileCrashContainer(CrashTable):
    """
    Old in-memory crash dump storage.

    @warning:
        Superceded by L{CrashDictionary} since WinAppDbg 1.5.
        New applications should not use this class.
    """

    def __init__(self, allowRepeatedKeys=True):
        """
        Volatile containers are stored only in memory and
        destroyed when they go out of scope.

        @type  allowRepeatedKeys: bool
        @param allowRepeatedKeys:
            If C{True} all L{Crash} objects are stored.

            If C{False} any L{Crash} object with the same key as a
            previously existing object will be ignored.
        """
        super(VolatileCrashContainer, self).__init__(allowRepeatedKeys=allowRepeatedKeys)


class DummyCrashContainer(object):
    """
    Fakes a database of volatile Crash objects,
    trying to mimic part of it's interface, but
    doesn't actually store anything.

    Normally applications don't need to use this.

    @see: L{CrashDictionary}
    """

    def __init__(self, allowRepeatedKeys=True):
        """
        Fake containers don't store L{Crash} objects, but they implement the
        interface properly.

        @type  allowRepeatedKeys: bool
        @param allowRepeatedKeys:
            Mimics the duplicate filter behavior found in real containers.
        """
        self.__keys = set()
        self.__count = 0
        self.__allowRepeatedKeys = allowRepeatedKeys

    def __contains__(self, crash):
        """
        @type  crash: L{Crash}
        @param crash: Crash object.

        @rtype:  bool
        @return: C{True} if the Crash object is in the container.
        """
        return crash.signature in self.__keys

    def __len__(self):
        """
        @rtype:  int
        @return: Count of L{Crash} elements in the container.
        """
        if self.__allowRepeatedKeys:
            return self.__count
        return len(self.__keys)

    def __bool__(self):
        """
        @rtype:  bool
        @return: C{False} if the container is empty.
        """
        return bool(len(self))

    def add(self, crash):
        """
        Adds a new crash to the container.

        @note:
            When the C{allowRepeatedKeys} parameter of the constructor
            is set to C{False}, duplicated crashes are ignored.

        @see: L{Crash.key}

        @type  crash: L{Crash}
        @param crash: Crash object to add.
        """
        self.__keys.add(crash.signature)
        self.__count += 1

    def get(self, key):
        """
        This method is not supported.
        """
        raise NotImplementedError()

    def has_key(self, key):
        """
        @type  key: L{Crash} signature.
        @param key: Heuristic signature of the crash to get.

        @rtype:  bool
        @return: C{True} if a matching L{Crash} object is in the container.
        """
        return self.__keys.has_key(key)

    def iterkeys(self):
        """
        @rtype:  iterator
        @return: Iterator of the contained L{Crash} object keys.

        @see:     L{get}
        @warning: A B{copy} of each object is returned,
            so any changes made to them will be lost.

            To preserve changes do the following:
                1. Keep a reference to the object.
                2. Delete the object from the set.
                3. Modify the object and add it again.
        """
        return iter(self.__keys)


# ==============================================================================
# Register the Crash class with the secure serializer.

try:
    cerealizer.register(Crash)
    cerealizer.register(win32.MemoryBasicInformation)
except NameError:
    pass

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\streaming_handler.py ===
import asyncio
import collections.abc
import datetime
import json
import threading
import time
import traceback
import uuid
from typing import Any, Callable, Dict, List, Optional, Union, cast

import httpx
from pydantic import BaseModel

import litellm
from litellm import verbose_logger
from litellm.litellm_core_utils.redact_messages import LiteLLMLoggingObject
from litellm.litellm_core_utils.thread_pool_executor import executor
from litellm.types.llms.openai import ChatCompletionChunk
from litellm.types.router import GenericLiteLLMParams
from litellm.types.utils import Delta
from litellm.types.utils import GenericStreamingChunk as GChunk
from litellm.types.utils import (
    ModelResponse,
    ModelResponseStream,
    StreamingChoices,
    Usage,
)

from ..exceptions import OpenAIError
from .core_helpers import map_finish_reason, process_response_headers
from .exception_mapping_utils import exception_type
from .llm_response_utils.get_api_base import get_api_base
from .rules import Rules


def is_async_iterable(obj: Any) -> bool:
    """
    Check if an object is an async iterable (can be used with 'async for').

    Args:
        obj: Any Python object to check

    Returns:
        bool: True if the object is async iterable, False otherwise
    """
    return isinstance(obj, collections.abc.AsyncIterable)


def print_verbose(print_statement):
    try:
        if litellm.set_verbose:
            print(print_statement)  # noqa
    except Exception:
        pass


class CustomStreamWrapper:
    def __init__(
        self,
        completion_stream,
        model,
        logging_obj: Any,
        custom_llm_provider: Optional[str] = None,
        stream_options=None,
        make_call: Optional[Callable] = None,
        _response_headers: Optional[dict] = None,
    ):
        self.model = model
        self.make_call = make_call
        self.custom_llm_provider = custom_llm_provider
        self.logging_obj: LiteLLMLoggingObject = logging_obj
        self.completion_stream = completion_stream
        self.sent_first_chunk = False
        self.sent_last_chunk = False

        litellm_params: GenericLiteLLMParams = GenericLiteLLMParams(
            **self.logging_obj.model_call_details.get("litellm_params", {})
        )
        self.merge_reasoning_content_in_choices: bool = (
            litellm_params.merge_reasoning_content_in_choices or False
        )
        self.sent_first_thinking_block = False
        self.sent_last_thinking_block = False
        self.thinking_content = ""

        self.system_fingerprint: Optional[str] = None
        self.received_finish_reason: Optional[str] = None
        self.intermittent_finish_reason: Optional[
            str
        ] = None  # finish reasons that show up mid-stream
        self.special_tokens = [
            "<|assistant|>",
            "<|system|>",
            "<|user|>",
            "<s>",
            "</s>",
            "<|im_end|>",
            "<|im_start|>",
        ]
        self.holding_chunk = ""
        self.complete_response = ""
        self.response_uptil_now = ""
        _model_info: Dict = litellm_params.model_info or {}

        _api_base = get_api_base(
            model=model or "",
            optional_params=self.logging_obj.model_call_details.get(
                "litellm_params", {}
            ),
        )

        self._hidden_params = {
            "model_id": (_model_info.get("id", None)),
            "api_base": _api_base,
        }  # returned as x-litellm-model-id response header in proxy

        self._hidden_params["additional_headers"] = process_response_headers(
            _response_headers or {}
        )  # GUARANTEE OPENAI HEADERS IN RESPONSE

        self._response_headers = _response_headers
        self.response_id: Optional[str] = None
        self.logging_loop = None
        self.rules = Rules()
        self.stream_options = stream_options or getattr(
            logging_obj, "stream_options", None
        )
        self.messages = getattr(logging_obj, "messages", None)
        self.sent_stream_usage = False
        self.send_stream_usage = (
            True if self.check_send_stream_usage(self.stream_options) else False
        )
        self.tool_call = False
        self.chunks: List = (
            []
        )  # keep track of the returned chunks - used for calculating the input/output tokens for stream options
        self.is_function_call = self.check_is_function_call(logging_obj=logging_obj)
        self.created: Optional[int] = None

    def __iter__(self):
        return self

    def __aiter__(self):
        return self

    def check_send_stream_usage(self, stream_options: Optional[dict]):
        return (
            stream_options is not None
            and stream_options.get("include_usage", False) is True
        )

    def check_is_function_call(self, logging_obj) -> bool:
        from litellm.litellm_core_utils.prompt_templates.common_utils import (
            is_function_call,
        )

        if hasattr(logging_obj, "optional_params") and isinstance(
            logging_obj.optional_params, dict
        ):
            if is_function_call(logging_obj.optional_params):
                return True

        return False

    def process_chunk(self, chunk: str):
        """
        NLP Cloud streaming returns the entire response, for each chunk. Process this, to only return the delta.
        """
        try:
            chunk = chunk.strip()
            self.complete_response = self.complete_response.strip()

            if chunk.startswith(self.complete_response):
                # Remove last_sent_chunk only if it appears at the start of the new chunk
                chunk = chunk[len(self.complete_response) :]

            self.complete_response += chunk
            return chunk
        except Exception as e:
            raise e

    def safety_checker(self) -> None:
        """
        Fixes - https://github.com/BerriAI/litellm/issues/5158

        if the model enters a loop and starts repeating the same chunk again, break out of loop and raise an internalservererror - allows for retries.

        Raises - InternalServerError, if LLM enters infinite loop while streaming
        """
        if len(self.chunks) >= litellm.REPEATED_STREAMING_CHUNK_LIMIT:
            # Get the last n chunks
            last_chunks = self.chunks[-litellm.REPEATED_STREAMING_CHUNK_LIMIT :]

            # Extract the relevant content from the chunks
            last_contents = [chunk.choices[0].delta.content for chunk in last_chunks]

            # Check if all extracted contents are identical
            if all(content == last_contents[0] for content in last_contents):
                if (
                    last_contents[0] is not None
                    and isinstance(last_contents[0], str)
                    and len(last_contents[0]) > 2
                ):  # ignore empty content - https://github.com/BerriAI/litellm/issues/5158#issuecomment-2287156946
                    # All last n chunks are identical
                    raise litellm.InternalServerError(
                        message="The model is repeating the same chunk = {}.".format(
                            last_contents[0]
                        ),
                        model="",
                        llm_provider="",
                    )

    def check_special_tokens(self, chunk: str, finish_reason: Optional[str]):
        """
        Output parse <s> / </s> special tokens for sagemaker + hf streaming.
        """
        hold = False
        if self.custom_llm_provider != "sagemaker":
            return hold, chunk

        if finish_reason:
            for token in self.special_tokens:
                if token in chunk:
                    chunk = chunk.replace(token, "")
            return hold, chunk

        if self.sent_first_chunk is True:
            return hold, chunk

        curr_chunk = self.holding_chunk + chunk
        curr_chunk = curr_chunk.strip()

        for token in self.special_tokens:
            if len(curr_chunk) < len(token) and curr_chunk in token:
                hold = True
                self.holding_chunk = curr_chunk
            elif len(curr_chunk) >= len(token):
                if token in curr_chunk:
                    self.holding_chunk = curr_chunk.replace(token, "")
                    hold = True
            else:
                pass

        if hold is False:  # reset
            self.holding_chunk = ""
        return hold, curr_chunk

    def handle_predibase_chunk(self, chunk):
        try:
            if not isinstance(chunk, str):
                chunk = chunk.decode(
                    "utf-8"
                )  # DO NOT REMOVE this: This is required for HF inference API + Streaming
            text = ""
            is_finished = False
            finish_reason = ""
            print_verbose(f"chunk: {chunk}")
            if chunk.startswith("data:"):
                data_json = json.loads(chunk[5:])
                print_verbose(f"data json: {data_json}")
                if "token" in data_json and "text" in data_json["token"]:
                    text = data_json["token"]["text"]
                if data_json.get("details", False) and data_json["details"].get(
                    "finish_reason", False
                ):
                    is_finished = True
                    finish_reason = data_json["details"]["finish_reason"]
                elif data_json.get(
                    "generated_text", False
                ):  # if full generated text exists, then stream is complete
                    text = ""  # don't return the final bos token
                    is_finished = True
                    finish_reason = "stop"
                elif data_json.get("error", False):
                    raise Exception(data_json.get("error"))
                return {
                    "text": text,
                    "is_finished": is_finished,
                    "finish_reason": finish_reason,
                }
            elif "error" in chunk:
                raise ValueError(chunk)
            return {
                "text": text,
                "is_finished": is_finished,
                "finish_reason": finish_reason,
            }
        except Exception as e:
            raise e

    def handle_ai21_chunk(self, chunk):  # fake streaming
        chunk = chunk.decode("utf-8")
        data_json = json.loads(chunk)
        try:
            text = data_json["completions"][0]["data"]["text"]
            is_finished = True
            finish_reason = "stop"
            return {
                "text": text,
                "is_finished": is_finished,
                "finish_reason": finish_reason,
            }
        except Exception:
            raise ValueError(f"Unable to parse response. Original response: {chunk}")

    def handle_maritalk_chunk(self, chunk):  # fake streaming
        chunk = chunk.decode("utf-8")
        data_json = json.loads(chunk)
        try:
            text = data_json["answer"]
            is_finished = True
            finish_reason = "stop"
            return {
                "text": text,
                "is_finished": is_finished,
                "finish_reason": finish_reason,
            }
        except Exception:
            raise ValueError(f"Unable to parse response. Original response: {chunk}")

    def handle_nlp_cloud_chunk(self, chunk):
        text = ""
        is_finished = False
        finish_reason = ""
        try:
            if self.model and "dolphin" in self.model:
                chunk = self.process_chunk(chunk=chunk)
            else:
                data_json = json.loads(chunk)
                chunk = data_json["generated_text"]
            text = chunk
            if "[DONE]" in text:
                text = text.replace("[DONE]", "")
                is_finished = True
                finish_reason = "stop"
            return {
                "text": text,
                "is_finished": is_finished,
                "finish_reason": finish_reason,
            }
        except Exception:
            raise ValueError(f"Unable to parse response. Original response: {chunk}")

    def handle_aleph_alpha_chunk(self, chunk):
        chunk = chunk.decode("utf-8")
        data_json = json.loads(chunk)
        try:
            text = data_json["completions"][0]["completion"]
            is_finished = True
            finish_reason = "stop"
            return {
                "text": text,
                "is_finished": is_finished,
                "finish_reason": finish_reason,
            }
        except Exception:
            raise ValueError(f"Unable to parse response. Original response: {chunk}")

    def handle_azure_chunk(self, chunk):
        is_finished = False
        finish_reason = ""
        text = ""
        print_verbose(f"chunk: {chunk}")
        if "data: [DONE]" in chunk:
            text = ""
            is_finished = True
            finish_reason = "stop"
            return {
                "text": text,
                "is_finished": is_finished,
                "finish_reason": finish_reason,
            }
        elif chunk.startswith("data:"):
            data_json = json.loads(chunk[5:])  # chunk.startswith("data:"):
            try:
                if len(data_json["choices"]) > 0:
                    delta = data_json["choices"][0]["delta"]
                    text = "" if delta is None else delta.get("content", "")
                    if data_json["choices"][0].get("finish_reason", None):
                        is_finished = True
                        finish_reason = data_json["choices"][0]["finish_reason"]
                print_verbose(
                    f"text: {text}; is_finished: {is_finished}; finish_reason: {finish_reason}"
                )
                return {
                    "text": text,
                    "is_finished": is_finished,
                    "finish_reason": finish_reason,
                }
            except Exception:
                raise ValueError(
                    f"Unable to parse response. Original response: {chunk}"
                )
        elif "error" in chunk:
            raise ValueError(f"Unable to parse response. Original response: {chunk}")
        else:
            return {
                "text": text,
                "is_finished": is_finished,
                "finish_reason": finish_reason,
            }

    def handle_replicate_chunk(self, chunk):
        try:
            text = ""
            is_finished = False
            finish_reason = ""
            if "output" in chunk:
                text = chunk["output"]
            if "status" in chunk:
                if chunk["status"] == "succeeded":
                    is_finished = True
                    finish_reason = "stop"
            elif chunk.get("error", None):
                raise Exception(chunk["error"])
            return {
                "text": text,
                "is_finished": is_finished,
                "finish_reason": finish_reason,
            }
        except Exception:
            raise ValueError(f"Unable to parse response. Original response: {chunk}")

    def handle_openai_chat_completion_chunk(self, chunk):
        try:
            print_verbose(f"\nRaw OpenAI Chunk\n{chunk}\n")
            str_line = chunk
            text = ""
            is_finished = False
            finish_reason = None
            logprobs = None
            usage = None

            if str_line and str_line.choices and len(str_line.choices) > 0:
                if (
                    str_line.choices[0].delta is not None
                    and str_line.choices[0].delta.content is not None
                ):
                    text = str_line.choices[0].delta.content
                else:  # function/tool calling chunk - when content is None. in this case we just return the original chunk from openai
                    pass
                if str_line.choices[0].finish_reason:
                    is_finished = (
                        True  # check if str_line._hidden_params["is_finished"] is True
                    )
                    if (
                        hasattr(str_line, "_hidden_params")
                        and str_line._hidden_params.get("is_finished") is not None
                    ):
                        is_finished = str_line._hidden_params.get("is_finished")
                    finish_reason = str_line.choices[0].finish_reason

                # checking for logprobs
                if (
                    hasattr(str_line.choices[0], "logprobs")
                    and str_line.choices[0].logprobs is not None
                ):
                    logprobs = str_line.choices[0].logprobs
                else:
                    logprobs = None

            usage = getattr(str_line, "usage", None)

            return {
                "text": text,
                "is_finished": is_finished,
                "finish_reason": finish_reason,
                "logprobs": logprobs,
                "original_chunk": str_line,
                "usage": usage,
            }
        except Exception as e:
            raise e

    def handle_azure_text_completion_chunk(self, chunk):
        try:
            print_verbose(f"\nRaw OpenAI Chunk\n{chunk}\n")
            text = ""
            is_finished = False
            finish_reason = None
            choices = getattr(chunk, "choices", [])
            if len(choices) > 0:
                text = choices[0].text
                if choices[0].finish_reason is not None:
                    is_finished = True
                    finish_reason = choices[0].finish_reason
            return {
                "text": text,
                "is_finished": is_finished,
                "finish_reason": finish_reason,
            }

        except Exception as e:
            raise e

    def handle_openai_text_completion_chunk(self, chunk):
        try:
            print_verbose(f"\nRaw OpenAI Chunk\n{chunk}\n")
            text = ""
            is_finished = False
            finish_reason = None
            usage = None
            choices = getattr(chunk, "choices", [])
            if len(choices) > 0:
                text = choices[0].text
                if choices[0].finish_reason is not None:
                    is_finished = True
                    finish_reason = choices[0].finish_reason
            usage = getattr(chunk, "usage", None)
            return {
                "text": text,
                "is_finished": is_finished,
                "finish_reason": finish_reason,
                "usage": usage,
            }

        except Exception as e:
            raise e

    def handle_baseten_chunk(self, chunk):
        try:
            chunk = chunk.decode("utf-8")
            if len(chunk) > 0:
                if chunk.startswith("data:"):
                    data_json = json.loads(chunk[5:])
                    if "token" in data_json and "text" in data_json["token"]:
                        return data_json["token"]["text"]
                    else:
                        return ""
                data_json = json.loads(chunk)
                if "model_output" in data_json:
                    if (
                        isinstance(data_json["model_output"], dict)
                        and "data" in data_json["model_output"]
                        and isinstance(data_json["model_output"]["data"], list)
                    ):
                        return data_json["model_output"]["data"][0]
                    elif isinstance(data_json["model_output"], str):
                        return data_json["model_output"]
                    elif "completion" in data_json and isinstance(
                        data_json["completion"], str
                    ):
                        return data_json["completion"]
                    else:
                        raise ValueError(
                            f"Unable to parse response. Original response: {chunk}"
                        )
                else:
                    return ""
            else:
                return ""
        except Exception as e:
            verbose_logger.exception(
                "litellm.CustomStreamWrapper.handle_baseten_chunk(): Exception occured - {}".format(
                    str(e)
                )
            )
            return ""

    def handle_triton_stream(self, chunk):
        try:
            if isinstance(chunk, dict):
                parsed_response = chunk
            elif isinstance(chunk, (str, bytes)):
                if isinstance(chunk, bytes):
                    chunk = chunk.decode("utf-8")
                if "text_output" in chunk:
                    response = (
                        CustomStreamWrapper._strip_sse_data_from_chunk(chunk) or ""
                    )
                    response = response.strip()
                    parsed_response = json.loads(response)
                else:
                    return {
                        "text": "",
                        "is_finished": False,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                    }
            else:
                print_verbose(f"chunk: {chunk} (Type: {type(chunk)})")
                raise ValueError(
                    f"Unable to parse response. Original response: {chunk}"
                )
            text = parsed_response.get("text_output", "")
            finish_reason = parsed_response.get("stop_reason")
            is_finished = parsed_response.get("is_finished", False)
            return {
                "text": text,
                "is_finished": is_finished,
                "finish_reason": finish_reason,
                "prompt_tokens": parsed_response.get("input_token_count", 0),
                "completion_tokens": parsed_response.get("generated_token_count", 0),
            }
            return {"text": "", "is_finished": False}
        except Exception as e:
            raise e

    def model_response_creator(
        self, chunk: Optional[dict] = None, hidden_params: Optional[dict] = None
    ):
        _model = self.model
        _received_llm_provider = self.custom_llm_provider
        _logging_obj_llm_provider = self.logging_obj.model_call_details.get("custom_llm_provider", None)  # type: ignore
        if (
            _received_llm_provider == "openai"
            and _received_llm_provider != _logging_obj_llm_provider
        ):
            _model = "{}/{}".format(_logging_obj_llm_provider, _model)
        if chunk is None:
            chunk = {}
        else:
            # pop model keyword
            chunk.pop("model", None)

        chunk_dict = {}
        for key, value in chunk.items():
            if key != "stream":
                chunk_dict[key] = value

        args = {
            "model": _model,
            "stream_options": self.stream_options,
            **chunk_dict,
        }

        model_response = ModelResponseStream(**args)
        if self.response_id is not None:
            model_response.id = self.response_id
        if self.system_fingerprint is not None:
            model_response.system_fingerprint = self.system_fingerprint

        if (
            self.created is not None
        ):  # maintain same 'created' across all chunks - https://github.com/BerriAI/litellm/issues/11437
            model_response.created = self.created
        else:
            self.created = model_response.created
        if hidden_params is not None:
            model_response._hidden_params = hidden_params
        model_response._hidden_params["custom_llm_provider"] = _logging_obj_llm_provider
        model_response._hidden_params["created_at"] = time.time()
        model_response._hidden_params = {
            **model_response._hidden_params,
            **self._hidden_params,
        }

        if (
            len(model_response.choices) > 0
            and getattr(model_response.choices[0], "delta") is not None
        ):
            # do nothing, if object instantiated
            pass
        else:
            model_response.choices = [StreamingChoices(finish_reason=None)]
        return model_response

    def is_delta_empty(self, delta: Delta) -> bool:
        is_empty = True
        if delta.content:
            is_empty = False
        elif delta.tool_calls is not None:
            is_empty = False
        elif delta.function_call is not None:
            is_empty = False
        return is_empty

    def set_model_id(
        self, id: str, model_response: ModelResponseStream
    ) -> ModelResponseStream:
        """
        Set the model id and response id to the given id.

        Ensure model id is always the same across all chunks.

        If a valid ID is received in any chunk, use it for the response.
        """
        if self.response_id is None and id and isinstance(id, str) and id.strip():
            self.response_id = id

        if id and isinstance(id, str) and id.strip():
            model_response._hidden_params["received_model_id"] = id

        if self.response_id is not None and isinstance(self.response_id, str):
            model_response.id = self.response_id
        return model_response

    def copy_model_response_level_provider_specific_fields(
        self,
        original_chunk: Union[ModelResponseStream, ChatCompletionChunk],
        model_response: ModelResponseStream,
    ) -> ModelResponseStream:
        """
        Copy provider_specific_fields from original_chunk to model_response.
        """
        provider_specific_fields = getattr(
            original_chunk, "provider_specific_fields", None
        )
        if provider_specific_fields is not None:
            model_response.provider_specific_fields = provider_specific_fields
            for k, v in provider_specific_fields.items():
                setattr(model_response, k, v)
        return model_response

    def is_chunk_non_empty(
        self,
        completion_obj: Dict[str, Any],
        model_response: ModelResponseStream,
        response_obj: Dict[str, Any],
    ) -> bool:
        if (
            "content" in completion_obj
            and (
                isinstance(completion_obj["content"], str)
                and len(completion_obj["content"]) > 0
            )
            or (
                "tool_calls" in completion_obj
                and completion_obj["tool_calls"] is not None
                and len(completion_obj["tool_calls"]) > 0
            )
            or (
                "function_call" in completion_obj
                and completion_obj["function_call"] is not None
            )
            or (
                "reasoning_content" in model_response.choices[0].delta
                and model_response.choices[0].delta.reasoning_content is not None
            )
            or (model_response.choices[0].delta.provider_specific_fields is not None)
            or (
                "provider_specific_fields" in model_response
                and model_response.choices[0].delta.provider_specific_fields is not None
            )
            or (
                "provider_specific_fields" in response_obj
                and response_obj["provider_specific_fields"] is not None
            )
            or (
                "annotations" in model_response.choices[0].delta
                and model_response.choices[0].delta.annotations is not None
            )
        ):
            return True
        else:
            return False

    def return_processed_chunk_logic(  # noqa
        self,
        completion_obj: Dict[str, Any],
        model_response: ModelResponseStream,
        response_obj: Dict[str, Any],
    ):
        print_verbose(
            f"completion_obj: {completion_obj}, model_response.choices[0]: {model_response.choices[0]}, response_obj: {response_obj}"
        )
        is_chunk_non_empty = self.is_chunk_non_empty(
            completion_obj, model_response, response_obj
        )
        if (
            is_chunk_non_empty
        ):  # cannot set content of an OpenAI Object to be an empty string
            self.safety_checker()
            hold, model_response_str = self.check_special_tokens(
                chunk=completion_obj["content"],
                finish_reason=model_response.choices[0].finish_reason,
            )  # filter out bos/eos tokens from openai-compatible hf endpoints
            print_verbose(f"hold - {hold}, model_response_str - {model_response_str}")
            if hold is False:
                ## check if openai/azure chunk
                original_chunk = response_obj.get("original_chunk", None)
                if original_chunk:
                    if len(original_chunk.choices) > 0:
                        choices = []
                        for choice in original_chunk.choices:
                            try:
                                if isinstance(choice, BaseModel):
                                    choice_json = choice.model_dump()  # type: ignore
                                    choice_json.pop(
                                        "finish_reason", None
                                    )  # for mistral etc. which return a value in their last chunk (not-openai compatible).
                                    print_verbose(f"choice_json: {choice_json}")
                                    choices.append(StreamingChoices(**choice_json))
                            except Exception:
                                choices.append(StreamingChoices())
                        print_verbose(f"choices in streaming: {choices}")
                        setattr(model_response, "choices", choices)
                    else:
                        return
                    model_response.system_fingerprint = (
                        original_chunk.system_fingerprint
                    )
                    setattr(
                        model_response,
                        "citations",
                        getattr(original_chunk, "citations", None),
                    )
                    print_verbose(f"self.sent_first_chunk: {self.sent_first_chunk}")
                    if self.sent_first_chunk is False:
                        model_response.choices[0].delta["role"] = "assistant"
                        self.sent_first_chunk = True
                    elif self.sent_first_chunk is True and hasattr(
                        model_response.choices[0].delta, "role"
                    ):
                        _initial_delta = model_response.choices[0].delta.model_dump()

                        _initial_delta.pop("role", None)
                        model_response.choices[0].delta = Delta(**_initial_delta)
                    verbose_logger.debug(
                        f"model_response.choices[0].delta: {model_response.choices[0].delta}"
                    )
                else:
                    ## else
                    completion_obj["content"] = model_response_str
                    if self.sent_first_chunk is False:
                        completion_obj["role"] = "assistant"
                        self.sent_first_chunk = True
                    if response_obj.get("provider_specific_fields") is not None:
                        completion_obj["provider_specific_fields"] = response_obj[
                            "provider_specific_fields"
                        ]
                    model_response.choices[0].delta = Delta(**completion_obj)
                    _index: Optional[int] = completion_obj.get("index")
                    if _index is not None:
                        model_response.choices[0].index = _index

                self._optional_combine_thinking_block_in_choices(
                    model_response=model_response
                )
                print_verbose(f"returning model_response: {model_response}")
                return model_response
            else:
                return
        elif self.received_finish_reason is not None:
            if self.sent_last_chunk is True:
                # Bedrock returns the guardrail trace in the last chunk - we want to return this here
                if self.custom_llm_provider == "bedrock" and "trace" in model_response:
                    return model_response

                # Default - return StopIteration
                if hasattr(model_response, "usage"):
                    self.chunks.append(model_response)
                raise StopIteration
            # flush any remaining holding chunk
            if len(self.holding_chunk) > 0:
                if model_response.choices[0].delta.content is None:
                    model_response.choices[0].delta.content = self.holding_chunk
                else:
                    model_response.choices[0].delta.content = (
                        self.holding_chunk + model_response.choices[0].delta.content
                    )
                self.holding_chunk = ""
            # if delta is None
            _is_delta_empty = self.is_delta_empty(delta=model_response.choices[0].delta)

            if _is_delta_empty:
                model_response.choices[0].delta = Delta(
                    content=None
                )  # ensure empty delta chunk returned
                # get any function call arguments
                model_response.choices[0].finish_reason = map_finish_reason(
                    finish_reason=self.received_finish_reason
                )  # ensure consistent output to openai

                self.sent_last_chunk = True

            return model_response
        elif (
            model_response.choices[0].delta.tool_calls is not None
            or model_response.choices[0].delta.function_call is not None
        ):
            if self.sent_first_chunk is False:
                model_response.choices[0].delta["role"] = "assistant"
                self.sent_first_chunk = True
            return model_response
        elif (
            len(model_response.choices) > 0
            and hasattr(model_response.choices[0].delta, "audio")
            and model_response.choices[0].delta.audio is not None
        ):
            return model_response
        else:
            if hasattr(model_response, "usage"):
                self.chunks.append(model_response)
            return

    def _optional_combine_thinking_block_in_choices(
        self, model_response: ModelResponseStream
    ) -> None:
        """
        UI's Like OpenWebUI expect to get 1 chunk with <think>...</think> tags in the chunk content

        In place updates the model_response object with reasoning_content in content with <think>...</think> tags

        Enabled when `merge_reasoning_content_in_choices=True` passed in request params


        """
        if self.merge_reasoning_content_in_choices is True:
            reasoning_content = getattr(
                model_response.choices[0].delta, "reasoning_content", None
            )
            if reasoning_content:
                if self.sent_first_thinking_block is False:
                    model_response.choices[0].delta.content += (
                        "<think>" + reasoning_content
                    )
                    self.sent_first_thinking_block = True
                elif (
                    self.sent_first_thinking_block is True
                    and hasattr(model_response.choices[0].delta, "reasoning_content")
                    and model_response.choices[0].delta.reasoning_content
                ):
                    model_response.choices[0].delta.content = reasoning_content
            elif (
                self.sent_first_thinking_block is True
                and not self.sent_last_thinking_block
                and model_response.choices[0].delta.content
            ):
                model_response.choices[0].delta.content = (
                    "</think>" + model_response.choices[0].delta.content
                )
                self.sent_last_thinking_block = True

            if hasattr(model_response.choices[0].delta, "reasoning_content"):
                del model_response.choices[0].delta.reasoning_content
        return

    def chunk_creator(self, chunk: Any):  # type: ignore  # noqa: PLR0915
        model_response = self.model_response_creator()
        response_obj: Dict[str, Any] = {}
        try:
            # return this for all models
            completion_obj: Dict[str, Any] = {"content": ""}
            from litellm.types.utils import GenericStreamingChunk as GChunk

            if (
                isinstance(chunk, dict)
                and generic_chunk_has_all_required_fields(
                    chunk=chunk
                )  # check if chunk is a generic streaming chunk
            ) or (
                self.custom_llm_provider
                and self.custom_llm_provider in litellm._custom_providers
            ):
                if self.received_finish_reason is not None:
                    if "provider_specific_fields" not in chunk:
                        raise StopIteration
                anthropic_response_obj: GChunk = cast(GChunk, chunk)
                completion_obj["content"] = anthropic_response_obj["text"]
                if anthropic_response_obj["is_finished"]:
                    self.received_finish_reason = anthropic_response_obj[
                        "finish_reason"
                    ]

                if anthropic_response_obj["finish_reason"]:
                    self.intermittent_finish_reason = anthropic_response_obj[
                        "finish_reason"
                    ]

                if anthropic_response_obj["usage"] is not None:
                    setattr(
                        model_response,
                        "usage",
                        litellm.Usage(**anthropic_response_obj["usage"]),
                    )

                if (
                    "tool_use" in anthropic_response_obj
                    and anthropic_response_obj["tool_use"] is not None
                ):
                    completion_obj["tool_calls"] = [anthropic_response_obj["tool_use"]]

                if (
                    "provider_specific_fields" in anthropic_response_obj
                    and anthropic_response_obj["provider_specific_fields"] is not None
                ):
                    for key, value in anthropic_response_obj[
                        "provider_specific_fields"
                    ].items():
                        setattr(model_response, key, value)

                response_obj = cast(Dict[str, Any], anthropic_response_obj)
            elif self.model == "replicate" or self.custom_llm_provider == "replicate":
                response_obj = self.handle_replicate_chunk(chunk)
                completion_obj["content"] = response_obj["text"]
                if response_obj["is_finished"]:
                    self.received_finish_reason = response_obj["finish_reason"]
            elif self.custom_llm_provider and self.custom_llm_provider == "predibase":
                response_obj = self.handle_predibase_chunk(chunk)
                completion_obj["content"] = response_obj["text"]
                if response_obj["is_finished"]:
                    self.received_finish_reason = response_obj["finish_reason"]
            elif (
                self.custom_llm_provider and self.custom_llm_provider == "baseten"
            ):  # baseten doesn't provide streaming
                completion_obj["content"] = self.handle_baseten_chunk(chunk)
            elif (
                self.custom_llm_provider and self.custom_llm_provider == "ai21"
            ):  # ai21 doesn't provide streaming
                response_obj = self.handle_ai21_chunk(chunk)
                completion_obj["content"] = response_obj["text"]
                if response_obj["is_finished"]:
                    self.received_finish_reason = response_obj["finish_reason"]
            elif self.custom_llm_provider and self.custom_llm_provider == "maritalk":
                response_obj = self.handle_maritalk_chunk(chunk)
                completion_obj["content"] = response_obj["text"]
                if response_obj["is_finished"]:
                    self.received_finish_reason = response_obj["finish_reason"]
            elif self.custom_llm_provider and self.custom_llm_provider == "vllm":
                completion_obj["content"] = chunk[0].outputs[0].text
            elif (
                self.custom_llm_provider and self.custom_llm_provider == "aleph_alpha"
            ):  # aleph alpha doesn't provide streaming
                response_obj = self.handle_aleph_alpha_chunk(chunk)
                completion_obj["content"] = response_obj["text"]
                if response_obj["is_finished"]:
                    self.received_finish_reason = response_obj["finish_reason"]
            elif self.custom_llm_provider == "nlp_cloud":
                try:
                    response_obj = self.handle_nlp_cloud_chunk(chunk)
                    completion_obj["content"] = response_obj["text"]
                    if response_obj["is_finished"]:
                        self.received_finish_reason = response_obj["finish_reason"]
                except Exception as e:
                    if self.received_finish_reason:
                        raise e
                    else:
                        if self.sent_first_chunk is False:
                            raise Exception("An unknown error occurred with the stream")
                        self.received_finish_reason = "stop"
            elif self.custom_llm_provider == "vertex_ai" and not isinstance(
                chunk, ModelResponseStream
            ):
                import proto  # type: ignore

                if hasattr(chunk, "candidates") is True:
                    try:
                        try:
                            completion_obj["content"] = chunk.text  # type: ignore
                        except Exception as e:
                            original_exception = e
                            if "Part has no text." in str(e):
                                ## check for function calling
                                function_call = (
                                    chunk.candidates[0].content.parts[0].function_call  # type: ignore
                                )

                                args_dict = {}

                                # Check if it's a RepeatedComposite instance
                                for key, val in function_call.args.items():
                                    if isinstance(
                                        val,
                                        proto.marshal.collections.repeated.RepeatedComposite,  # type: ignore
                                    ):
                                        # If so, convert to list
                                        args_dict[key] = [v for v in val]
                                    else:
                                        args_dict[key] = val

                                try:
                                    args_str = json.dumps(args_dict)
                                except Exception as e:
                                    raise e
                                _delta_obj = litellm.utils.Delta(
                                    content=None,
                                    tool_calls=[
                                        {
                                            "id": f"call_{str(uuid.uuid4())}",
                                            "function": {
                                                "arguments": args_str,
                                                "name": function_call.name,
                                            },
                                            "type": "function",
                                        }
                                    ],
                                )
                                _streaming_response = StreamingChoices(delta=_delta_obj)
                                _model_response = ModelResponse(stream=True)
                                _model_response.choices = [_streaming_response]
                                response_obj = {"original_chunk": _model_response}
                            else:
                                raise original_exception
                        if (
                            hasattr(chunk.candidates[0], "finish_reason")  # type: ignore
                            and chunk.candidates[0].finish_reason.name  # type: ignore
                            != "FINISH_REASON_UNSPECIFIED"
                        ):  # every non-final chunk in vertex ai has this
                            self.received_finish_reason = chunk.candidates[  # type: ignore
                                0
                            ].finish_reason.name
                    except Exception:
                        if chunk.candidates[0].finish_reason.name == "SAFETY":  # type: ignore
                            raise Exception(
                                f"The response was blocked by VertexAI. {str(chunk)}"
                            )
                else:
                    completion_obj["content"] = str(chunk)
            elif self.custom_llm_provider == "petals":
                if len(self.completion_stream) == 0:
                    if self.received_finish_reason is not None:
                        raise StopIteration
                    else:
                        self.received_finish_reason = "stop"
                chunk_size = 30
                new_chunk = self.completion_stream[:chunk_size]
                completion_obj["content"] = new_chunk
                self.completion_stream = self.completion_stream[chunk_size:]
            elif self.custom_llm_provider == "palm":
                # fake streaming
                response_obj = {}
                if len(self.completion_stream) == 0:
                    if self.received_finish_reason is not None:
                        raise StopIteration
                    else:
                        self.received_finish_reason = "stop"
                chunk_size = 30
                new_chunk = self.completion_stream[:chunk_size]
                completion_obj["content"] = new_chunk
                self.completion_stream = self.completion_stream[chunk_size:]
            elif self.custom_llm_provider == "triton":
                response_obj = self.handle_triton_stream(chunk)
                completion_obj["content"] = response_obj["text"]
                print_verbose(f"completion obj content: {completion_obj['content']}")
                if response_obj["is_finished"]:
                    self.received_finish_reason = response_obj["finish_reason"]
            elif self.custom_llm_provider == "text-completion-openai":
                response_obj = self.handle_openai_text_completion_chunk(chunk)
                completion_obj["content"] = response_obj["text"]
                print_verbose(f"completion obj content: {completion_obj['content']}")
                if response_obj["is_finished"]:
                    self.received_finish_reason = response_obj["finish_reason"]
                if response_obj["usage"] is not None:
                    setattr(
                        model_response,
                        "usage",
                        litellm.Usage(
                            prompt_tokens=response_obj["usage"].prompt_tokens,
                            completion_tokens=response_obj["usage"].completion_tokens,
                            total_tokens=response_obj["usage"].total_tokens,
                        ),
                    )
            elif self.custom_llm_provider == "text-completion-codestral":
                if not isinstance(chunk, str):
                    raise ValueError(f"chunk is not a string: {chunk}")
                response_obj = cast(
                    Dict[str, Any],
                    litellm.CodestralTextCompletionConfig()._chunk_parser(chunk),
                )
                completion_obj["content"] = response_obj["text"]
                print_verbose(f"completion obj content: {completion_obj['content']}")
                if response_obj["is_finished"]:
                    self.received_finish_reason = response_obj["finish_reason"]
                if "usage" in response_obj is not None:
                    setattr(
                        model_response,
                        "usage",
                        litellm.Usage(
                            prompt_tokens=response_obj["usage"].prompt_tokens,
                            completion_tokens=response_obj["usage"].completion_tokens,
                            total_tokens=response_obj["usage"].total_tokens,
                        ),
                    )
            elif self.custom_llm_provider == "azure_text":
                response_obj = self.handle_azure_text_completion_chunk(chunk)
                completion_obj["content"] = response_obj["text"]
                print_verbose(f"completion obj content: {completion_obj['content']}")
                if response_obj["is_finished"]:
                    self.received_finish_reason = response_obj["finish_reason"]
            elif self.custom_llm_provider == "cached_response":
                chunk = cast(ModelResponseStream, chunk)
                response_obj = {
                    "text": chunk.choices[0].delta.content,
                    "is_finished": True,
                    "finish_reason": chunk.choices[0].finish_reason,
                    "original_chunk": chunk,
                    "tool_calls": (
                        chunk.choices[0].delta.tool_calls
                        if hasattr(chunk.choices[0].delta, "tool_calls")
                        else None
                    ),
                }

                completion_obj["content"] = response_obj["text"]
                if response_obj["tool_calls"] is not None:
                    completion_obj["tool_calls"] = response_obj["tool_calls"]
                print_verbose(f"completion obj content: {completion_obj['content']}")
                if hasattr(chunk, "id"):
                    model_response.id = chunk.id
                    self.response_id = chunk.id
                if hasattr(chunk, "system_fingerprint"):
                    self.system_fingerprint = chunk.system_fingerprint
                if response_obj["is_finished"]:
                    self.received_finish_reason = response_obj["finish_reason"]
            else:  # openai / azure chat model
                if self.custom_llm_provider == "azure":
                    if isinstance(chunk, BaseModel) and hasattr(chunk, "model"):
                        # for azure, we need to pass the model from the orignal chunk
                        self.model = getattr(chunk, "model", self.model)
                response_obj = self.handle_openai_chat_completion_chunk(chunk)
                if response_obj is None:
                    return
                completion_obj["content"] = response_obj["text"]
                if response_obj["is_finished"]:
                    if response_obj["finish_reason"] == "error":
                        raise Exception(
                            "{} raised a streaming error - finish_reason: error, no content string given. Received Chunk={}".format(
                                self.custom_llm_provider, response_obj
                            )
                        )
                    self.received_finish_reason = response_obj["finish_reason"]
                if response_obj.get("original_chunk", None) is not None:
                    if hasattr(response_obj["original_chunk"], "id"):
                        model_response = self.set_model_id(
                            response_obj["original_chunk"].id, model_response
                        )
                    if hasattr(response_obj["original_chunk"], "system_fingerprint"):
                        model_response.system_fingerprint = response_obj[
                            "original_chunk"
                        ].system_fingerprint
                        self.system_fingerprint = response_obj[
                            "original_chunk"
                        ].system_fingerprint
                if response_obj["logprobs"] is not None:
                    model_response.choices[0].logprobs = response_obj["logprobs"]

                if response_obj["usage"] is not None:
                    if isinstance(response_obj["usage"], dict):
                        setattr(
                            model_response,
                            "usage",
                            litellm.Usage(
                                prompt_tokens=response_obj["usage"].get(
                                    "prompt_tokens", None
                                )
                                or None,
                                completion_tokens=response_obj["usage"].get(
                                    "completion_tokens", None
                                )
                                or None,
                                total_tokens=response_obj["usage"].get(
                                    "total_tokens", None
                                )
                                or None,
                            ),
                        )
                    elif isinstance(response_obj["usage"], Usage):
                        setattr(
                            model_response,
                            "usage",
                            response_obj["usage"],
                        )
                    elif isinstance(response_obj["usage"], BaseModel):
                        setattr(
                            model_response,
                            "usage",
                            litellm.Usage(**response_obj["usage"].model_dump()),
                        )

            model_response.model = self.model
            print_verbose(
                f"model_response finish reason 3: {self.received_finish_reason}; response_obj={response_obj}"
            )
            ## FUNCTION CALL PARSING
            if (
                response_obj is not None
                and response_obj.get("original_chunk", None) is not None
            ):  # function / tool calling branch - only set for openai/azure compatible endpoints
                # enter this branch when no content has been passed in response
                original_chunk = response_obj.get("original_chunk", None)
                if hasattr(original_chunk, "id"):
                    model_response = self.set_model_id(
                        original_chunk.id, model_response
                    )
                if hasattr(original_chunk, "provider_specific_fields"):
                    model_response = (
                        self.copy_model_response_level_provider_specific_fields(
                            original_chunk, model_response
                        )
                    )
                if original_chunk.choices and len(original_chunk.choices) > 0:
                    delta = original_chunk.choices[0].delta
                    if delta is not None and (
                        delta.function_call is not None or delta.tool_calls is not None
                    ):
                        try:
                            model_response.system_fingerprint = (
                                original_chunk.system_fingerprint
                            )
                            ## AZURE - check if arguments is not None
                            if (
                                original_chunk.choices[0].delta.function_call
                                is not None
                            ):
                                if (
                                    getattr(
                                        original_chunk.choices[0].delta.function_call,
                                        "arguments",
                                    )
                                    is None
                                ):
                                    original_chunk.choices[
                                        0
                                    ].delta.function_call.arguments = ""
                            elif original_chunk.choices[0].delta.tool_calls is not None:
                                if isinstance(
                                    original_chunk.choices[0].delta.tool_calls, list
                                ):
                                    for t in original_chunk.choices[0].delta.tool_calls:
                                        if hasattr(t, "functions") and hasattr(
                                            t.functions, "arguments"
                                        ):
                                            if (
                                                getattr(
                                                    t.function,
                                                    "arguments",
                                                )
                                                is None
                                            ):
                                                t.function.arguments = ""
                            _json_delta = delta.model_dump()
                            print_verbose(f"_json_delta: {_json_delta}")
                            if "role" not in _json_delta or _json_delta["role"] is None:
                                _json_delta[
                                    "role"
                                ] = "assistant"  # mistral's api returns role as None
                            if "tool_calls" in _json_delta and isinstance(
                                _json_delta["tool_calls"], list
                            ):
                                for tool in _json_delta["tool_calls"]:
                                    if (
                                        isinstance(tool, dict)
                                        and "function" in tool
                                        and isinstance(tool["function"], dict)
                                        and ("type" not in tool or tool["type"] is None)
                                    ):
                                        # if function returned but type set to None - mistral's api returns type: None
                                        tool["type"] = "function"
                            model_response.choices[0].delta = Delta(**_json_delta)
                        except Exception as e:
                            verbose_logger.exception(
                                "litellm.CustomStreamWrapper.chunk_creator(): Exception occured - {}".format(
                                    str(e)
                                )
                            )
                            model_response.choices[0].delta = Delta()
                    elif (
                        delta is not None and getattr(delta, "audio", None) is not None
                    ):
                        model_response.choices[0].delta.audio = delta.audio
                    else:
                        try:
                            delta = (
                                dict()
                                if original_chunk.choices[0].delta is None
                                else dict(original_chunk.choices[0].delta)
                            )
                            print_verbose(f"original delta: {delta}")
                            model_response.choices[0].delta = Delta(**delta)
                            print_verbose(
                                f"new delta: {model_response.choices[0].delta}"
                            )
                        except Exception:
                            model_response.choices[0].delta = Delta()
                else:
                    if (
                        self.stream_options is not None
                        and self.stream_options["include_usage"] is True
                    ):
                        return model_response
                    return
            print_verbose(
                f"model_response.choices[0].delta: {model_response.choices[0].delta}; completion_obj: {completion_obj}"
            )
            print_verbose(f"self.sent_first_chunk: {self.sent_first_chunk}")

            ## CHECK FOR TOOL USE

            if "tool_calls" in completion_obj and len(completion_obj["tool_calls"]) > 0:
                if self.is_function_call is True:  # user passed in 'functions' param
                    completion_obj["function_call"] = completion_obj["tool_calls"][0][
                        "function"
                    ]
                    completion_obj["tool_calls"] = None

                self.tool_call = True

            ## RETURN ARG
            return self.return_processed_chunk_logic(
                completion_obj=completion_obj,
                model_response=model_response,  # type: ignore
                response_obj=response_obj,
            )

        except StopIteration:
            raise StopIteration
        except Exception as e:
            traceback.format_exc()
            setattr(e, "message", str(e))
            raise exception_type(
                model=self.model,
                custom_llm_provider=self.custom_llm_provider,
                original_exception=e,
            )

    def set_logging_event_loop(self, loop):
        """
        import litellm, asyncio

        loop = asyncio.get_event_loop() # 👈 gets the current event loop

        response = litellm.completion(.., stream=True)

        response.set_logging_event_loop(loop=loop) # 👈 enables async_success callbacks for sync logging

        for chunk in response:
            ...
        """
        self.logging_loop = loop

    def cache_streaming_response(self, processed_chunk, cache_hit: bool):
        """
        Caches the streaming response
        """
        if not cache_hit and self.logging_obj._llm_caching_handler is not None:
            self.logging_obj._llm_caching_handler._sync_add_streaming_response_to_cache(
                processed_chunk
            )

    async def async_cache_streaming_response(self, processed_chunk, cache_hit: bool):
        """
        Caches the streaming response
        """
        if not cache_hit and self.logging_obj._llm_caching_handler is not None:
            await self.logging_obj._llm_caching_handler._add_streaming_response_to_cache(
                processed_chunk
            )

    def run_success_logging_and_cache_storage(self, processed_chunk, cache_hit: bool):
        """
        Runs success logging in a thread and adds the response to the cache
        """
        if litellm.disable_streaming_logging is True:
            """
            [NOT RECOMMENDED]
            Set this via `litellm.disable_streaming_logging = True`.

            Disables streaming logging.
            """
            return
        ## ASYNC LOGGING
        # Create an event loop for the new thread
        if self.logging_loop is not None:
            future = asyncio.run_coroutine_threadsafe(
                self.logging_obj.async_success_handler(
                    processed_chunk, None, None, cache_hit
                ),
                loop=self.logging_loop,
            )
            future.result()
        else:
            asyncio.run(
                self.logging_obj.async_success_handler(
                    processed_chunk, None, None, cache_hit
                )
            )
        ## SYNC LOGGING
        self.logging_obj.success_handler(processed_chunk, None, None, cache_hit)

    def finish_reason_handler(self):
        model_response = self.model_response_creator()
        _finish_reason = self.received_finish_reason or self.intermittent_finish_reason
        if _finish_reason is not None:
            model_response.choices[0].finish_reason = _finish_reason
        else:
            model_response.choices[0].finish_reason = "stop"

        ## if tool use
        if (
            model_response.choices[0].finish_reason == "stop" and self.tool_call
        ):  # don't overwrite for other - potential error finish reasons
            model_response.choices[0].finish_reason = "tool_calls"
        return model_response

    def __next__(self):  # noqa: PLR0915
        cache_hit = False
        if (
            self.custom_llm_provider is not None
            and self.custom_llm_provider == "cached_response"
        ):
            cache_hit = True
        try:
            if self.completion_stream is None:
                self.fetch_sync_stream()

            while True:
                if (
                    isinstance(self.completion_stream, str)
                    or isinstance(self.completion_stream, bytes)
                    or isinstance(self.completion_stream, ModelResponse)
                ):
                    chunk = self.completion_stream
                else:
                    chunk = next(self.completion_stream)
                if chunk is not None and chunk != b"":
                    print_verbose(
                        f"PROCESSED CHUNK PRE CHUNK CREATOR: {chunk}; custom_llm_provider: {self.custom_llm_provider}"
                    )
                    response: Optional[ModelResponseStream] = self.chunk_creator(
                        chunk=chunk
                    )
                    print_verbose(f"PROCESSED CHUNK POST CHUNK CREATOR: {response}")

                    if response is None:
                        continue
                    if self.logging_obj.completion_start_time is None:
                        self.logging_obj._update_completion_start_time(
                            completion_start_time=datetime.datetime.now()
                        )
                    ## LOGGING
                    executor.submit(
                        self.run_success_logging_and_cache_storage,
                        response,
                        cache_hit,
                    )  # log response
                    choice = response.choices[0]
                    if isinstance(choice, StreamingChoices):
                        self.response_uptil_now += choice.delta.get("content", "") or ""
                    else:
                        self.response_uptil_now += ""
                    self.rules.post_call_rules(
                        input=self.response_uptil_now, model=self.model
                    )
                    # HANDLE STREAM OPTIONS
                    self.chunks.append(response)
                    if hasattr(
                        response, "usage"
                    ):  # remove usage from chunk, only send on final chunk
                        # Convert the object to a dictionary
                        obj_dict = response.dict()

                        # Remove an attribute (e.g., 'attr2')
                        if "usage" in obj_dict:
                            del obj_dict["usage"]

                        # Create a new object without the removed attribute
                        response = self.model_response_creator(
                            chunk=obj_dict, hidden_params=response._hidden_params
                        )
                    # add usage as hidden param
                    if self.sent_last_chunk is True and self.stream_options is None:
                        usage = calculate_total_usage(chunks=self.chunks)
                        response._hidden_params["usage"] = usage
                    # RETURN RESULT
                    return response

        except StopIteration:
            if self.sent_last_chunk is True:
                complete_streaming_response = litellm.stream_chunk_builder(
                    chunks=self.chunks, messages=self.messages
                )
                response = self.model_response_creator()
                if complete_streaming_response is not None:
                    setattr(
                        response,
                        "usage",
                        getattr(complete_streaming_response, "usage"),
                    )
                    self.cache_streaming_response(
                        processed_chunk=complete_streaming_response.model_copy(
                            deep=True
                        ),
                        cache_hit=cache_hit,
                    )
                    executor.submit(
                        self.logging_obj.success_handler,
                        complete_streaming_response.model_copy(deep=True),
                        None,
                        None,
                        cache_hit,
                    )
                else:
                    executor.submit(
                        self.logging_obj.success_handler,
                        response,
                        None,
                        None,
                        cache_hit,
                    )
                if self.sent_stream_usage is False and self.send_stream_usage is True:
                    self.sent_stream_usage = True
                    return response
                raise  # Re-raise StopIteration
            else:
                self.sent_last_chunk = True
                processed_chunk = self.finish_reason_handler()
                if self.stream_options is None:  # add usage as hidden param
                    usage = calculate_total_usage(chunks=self.chunks)
                    processed_chunk._hidden_params["usage"] = usage
                ## LOGGING
                executor.submit(
                    self.run_success_logging_and_cache_storage,
                    processed_chunk,
                    cache_hit,
                )  # log response
                return processed_chunk
        except Exception as e:
            traceback_exception = traceback.format_exc()
            # LOG FAILURE - handle streaming failure logging in the _next_ object, remove `handle_failure` once it's deprecated
            threading.Thread(
                target=self.logging_obj.failure_handler, args=(e, traceback_exception)
            ).start()
            if isinstance(e, OpenAIError):
                raise e
            else:
                raise exception_type(
                    model=self.model,
                    original_exception=e,
                    custom_llm_provider=self.custom_llm_provider,
                )

    def fetch_sync_stream(self):
        if self.completion_stream is None and self.make_call is not None:
            # Call make_call to get the completion stream
            self.completion_stream = self.make_call(client=litellm.module_level_client)
            self._stream_iter = self.completion_stream.__iter__()

        return self.completion_stream

    async def fetch_stream(self):
        if self.completion_stream is None and self.make_call is not None:
            # Call make_call to get the completion stream
            self.completion_stream = await self.make_call(
                client=litellm.module_level_aclient
            )
            self._stream_iter = self.completion_stream.__aiter__()

        return self.completion_stream

    async def __anext__(self):  # noqa: PLR0915
        cache_hit = False
        if (
            self.custom_llm_provider is not None
            and self.custom_llm_provider == "cached_response"
        ):
            cache_hit = True
        try:
            if self.completion_stream is None:
                await self.fetch_stream()

            if is_async_iterable(self.completion_stream):
                async for chunk in self.completion_stream:
                    if chunk == "None" or chunk is None:
                        continue  # skip None chunks

                    elif (
                        self.custom_llm_provider == "gemini"
                        and hasattr(chunk, "parts")
                        and len(chunk.parts) == 0
                    ):
                        continue
                    # chunk_creator() does logging/stream chunk building. We need to let it know its being called in_async_func, so we don't double add chunks.
                    # __anext__ also calls async_success_handler, which does logging
                    verbose_logger.debug(
                        f"PROCESSED ASYNC CHUNK PRE CHUNK CREATOR: {chunk}"
                    )

                    processed_chunk: Optional[ModelResponseStream] = self.chunk_creator(
                        chunk=chunk
                    )
                    verbose_logger.debug(
                        f"PROCESSED ASYNC CHUNK POST CHUNK CREATOR: {processed_chunk}"
                    )
                    if processed_chunk is None:
                        continue

                    if self.logging_obj.completion_start_time is None:
                        self.logging_obj._update_completion_start_time(
                            completion_start_time=datetime.datetime.now()
                        )

                    choice = processed_chunk.choices[0]
                    if isinstance(choice, StreamingChoices):
                        self.response_uptil_now += choice.delta.get("content", "") or ""
                    else:
                        self.response_uptil_now += ""
                    self.rules.post_call_rules(
                        input=self.response_uptil_now, model=self.model
                    )
                    self.chunks.append(processed_chunk)
                    if hasattr(
                        processed_chunk, "usage"
                    ):  # remove usage from chunk, only send on final chunk
                        # Convert the object to a dictionary
                        obj_dict = processed_chunk.dict()

                        # Remove an attribute (e.g., 'attr2')
                        if "usage" in obj_dict:
                            del obj_dict["usage"]

                        # Create a new object without the removed attribute
                        processed_chunk = self.model_response_creator(chunk=obj_dict)
                    print_verbose(f"final returned processed chunk: {processed_chunk}")
                    return processed_chunk
                raise StopAsyncIteration
            else:  # temporary patch for non-aiohttp async calls
                # example - boto3 bedrock llms
                while True:
                    if isinstance(self.completion_stream, str) or isinstance(
                        self.completion_stream, bytes
                    ):
                        chunk = self.completion_stream
                    else:
                        chunk = next(self.completion_stream)
                    if chunk is not None and chunk != b"":
                        print_verbose(f"PROCESSED CHUNK PRE CHUNK CREATOR: {chunk}")
                        processed_chunk: Optional[
                            ModelResponseStream
                        ] = self.chunk_creator(chunk=chunk)
                        print_verbose(
                            f"PROCESSED CHUNK POST CHUNK CREATOR: {processed_chunk}"
                        )
                        if processed_chunk is None:
                            continue

                        choice = processed_chunk.choices[0]
                        if isinstance(choice, StreamingChoices):
                            self.response_uptil_now += (
                                choice.delta.get("content", "") or ""
                            )
                        else:
                            self.response_uptil_now += ""
                        self.rules.post_call_rules(
                            input=self.response_uptil_now, model=self.model
                        )
                        # RETURN RESULT
                        self.chunks.append(processed_chunk)
                        return processed_chunk
        except (StopAsyncIteration, StopIteration):
            if self.sent_last_chunk is True:
                # log the final chunk with accurate streaming values
                complete_streaming_response = litellm.stream_chunk_builder(
                    chunks=self.chunks, messages=self.messages
                )
                response = self.model_response_creator()
                if complete_streaming_response is not None:
                    setattr(
                        response,
                        "usage",
                        getattr(complete_streaming_response, "usage"),
                    )
                    asyncio.create_task(
                        self.async_cache_streaming_response(
                            processed_chunk=complete_streaming_response.model_copy(
                                deep=True
                            ),
                            cache_hit=cache_hit,
                        )
                    )
                if self.sent_stream_usage is False and self.send_stream_usage is True:
                    self.sent_stream_usage = True
                    return response

                asyncio.create_task(
                    self.logging_obj.async_success_handler(
                        complete_streaming_response,
                        cache_hit=cache_hit,
                        start_time=None,
                        end_time=None,
                    )
                )

                executor.submit(
                    self.logging_obj.success_handler,
                    complete_streaming_response,
                    cache_hit=cache_hit,
                    start_time=None,
                    end_time=None,
                )

                raise StopAsyncIteration  # Re-raise StopIteration
            else:
                self.sent_last_chunk = True
                processed_chunk = self.finish_reason_handler()
                return processed_chunk
        except httpx.TimeoutException as e:  # if httpx read timeout error occues
            traceback_exception = traceback.format_exc()
            ## ADD DEBUG INFORMATION - E.G. LITELLM REQUEST TIMEOUT
            traceback_exception += "\nLiteLLM Default Request Timeout - {}".format(
                litellm.request_timeout
            )
            if self.logging_obj is not None:
                ## LOGGING
                threading.Thread(
                    target=self.logging_obj.failure_handler,
                    args=(e, traceback_exception),
                ).start()  # log response
                # Handle any exceptions that might occur during streaming
                asyncio.create_task(
                    self.logging_obj.async_failure_handler(e, traceback_exception)
                )
            raise e
        except Exception as e:
            traceback_exception = traceback.format_exc()
            if self.logging_obj is not None:
                ## LOGGING
                threading.Thread(
                    target=self.logging_obj.failure_handler,
                    args=(e, traceback_exception),
                ).start()  # log response
                # Handle any exceptions that might occur during streaming
                asyncio.create_task(
                    self.logging_obj.async_failure_handler(e, traceback_exception)  # type: ignore
                )
            ## Map to OpenAI Exception
            raise exception_type(
                model=self.model,
                custom_llm_provider=self.custom_llm_provider,
                original_exception=e,
                completion_kwargs={},
                extra_kwargs={},
            )

    @staticmethod
    def _strip_sse_data_from_chunk(chunk: Optional[str]) -> Optional[str]:
        """
        Strips the 'data: ' prefix from Server-Sent Events (SSE) chunks.

        Some providers like sagemaker send it as `data:`, need to handle both

        SSE messages are prefixed with 'data: ' which is part of the protocol,
        not the actual content from the LLM. This method removes that prefix
        and returns the actual content.

        Args:
            chunk: The SSE chunk that may contain the 'data: ' prefix (string or bytes)

        Returns:
            The chunk with the 'data: ' prefix removed, or the original chunk
            if no prefix was found. Returns None if input is None.

        See OpenAI Python Ref for this: https://github.com/openai/openai-python/blob/041bf5a8ec54da19aad0169671793c2078bd6173/openai/api_requestor.py#L100
        """
        if chunk is None:
            return None

        if isinstance(chunk, str):
            # OpenAI sends `data: `
            if chunk.startswith("data: "):
                # Strip the prefix and any leading whitespace that might follow it
                _length_of_sse_data_prefix = len("data: ")
                return chunk[_length_of_sse_data_prefix:]
            elif chunk.startswith("data:"):
                # Sagemaker sends `data:`, no trailing whitespace
                _length_of_sse_data_prefix = len("data:")
                return chunk[_length_of_sse_data_prefix:]

        return chunk


def calculate_total_usage(chunks: List[ModelResponse]) -> Usage:
    """Assume most recent usage chunk has total usage uptil then."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    for chunk in chunks:
        if "usage" in chunk:
            if "prompt_tokens" in chunk["usage"]:
                prompt_tokens = chunk["usage"].get("prompt_tokens", 0) or 0
            if "completion_tokens" in chunk["usage"]:
                completion_tokens = chunk["usage"].get("completion_tokens", 0) or 0

    returned_usage_chunk = Usage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )

    return returned_usage_chunk


def generic_chunk_has_all_required_fields(chunk: dict) -> bool:
    """
    Checks if the provided chunk dictionary contains all required fields for GenericStreamingChunk.

    :param chunk: The dictionary to check.
    :return: True if all required fields are present, False otherwise.
    """
    _all_fields = GChunk.__annotations__

    decision = all(key in _all_fields for key in chunk)
    return decision