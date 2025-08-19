
# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_generated\_async_client.py ===
# coding=utf-8
# Copyright 2023-present, the HuggingFace Inc. team.
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
# WARNING
# This entire file has been adapted from the sync-client code in `src/huggingface_hub/inference/_client.py`.
# Any change in InferenceClient will be automatically reflected in AsyncInferenceClient.
# To re-generate the code, run `make style` or `python ./utils/generate_async_inference_client.py --update`.
# WARNING
import asyncio
import base64
import logging
import re
import warnings
from typing import TYPE_CHECKING, Any, AsyncIterable, Dict, List, Literal, Optional, Set, Union, overload

from huggingface_hub import constants
from huggingface_hub.errors import InferenceTimeoutError
from huggingface_hub.inference._common import (
    TASKS_EXPECTING_IMAGES,
    ContentT,
    ModelStatus,
    RequestParameters,
    _async_stream_chat_completion_response,
    _async_stream_text_generation_response,
    _b64_encode,
    _b64_to_image,
    _bytes_to_dict,
    _bytes_to_image,
    _bytes_to_list,
    _get_unsupported_text_generation_kwargs,
    _import_numpy,
    _open_as_binary,
    _set_unsupported_text_generation_kwargs,
    raise_text_generation_error,
)
from huggingface_hub.inference._generated.types import (
    AudioClassificationOutputElement,
    AudioClassificationOutputTransform,
    AudioToAudioOutputElement,
    AutomaticSpeechRecognitionOutput,
    ChatCompletionInputGrammarType,
    ChatCompletionInputMessage,
    ChatCompletionInputStreamOptions,
    ChatCompletionInputTool,
    ChatCompletionInputToolChoiceClass,
    ChatCompletionInputToolChoiceEnum,
    ChatCompletionOutput,
    ChatCompletionStreamOutput,
    DocumentQuestionAnsweringOutputElement,
    FillMaskOutputElement,
    ImageClassificationOutputElement,
    ImageClassificationOutputTransform,
    ImageSegmentationOutputElement,
    ImageSegmentationSubtask,
    ImageToImageTargetSize,
    ImageToTextOutput,
    ObjectDetectionOutputElement,
    Padding,
    QuestionAnsweringOutputElement,
    SummarizationOutput,
    SummarizationTruncationStrategy,
    TableQuestionAnsweringOutputElement,
    TextClassificationOutputElement,
    TextClassificationOutputTransform,
    TextGenerationInputGrammarType,
    TextGenerationOutput,
    TextGenerationStreamOutput,
    TextToSpeechEarlyStoppingEnum,
    TokenClassificationAggregationStrategy,
    TokenClassificationOutputElement,
    TranslationOutput,
    TranslationTruncationStrategy,
    VisualQuestionAnsweringOutputElement,
    ZeroShotClassificationOutputElement,
    ZeroShotImageClassificationOutputElement,
)
from huggingface_hub.inference._providers import PROVIDER_OR_POLICY_T, get_provider_helper
from huggingface_hub.utils import build_hf_headers, get_session, hf_raise_for_status
from huggingface_hub.utils._auth import get_token
from huggingface_hub.utils._deprecation import _deprecate_method

from .._common import _async_yield_from, _import_aiohttp


if TYPE_CHECKING:
    import numpy as np
    from aiohttp import ClientResponse, ClientSession
    from PIL.Image import Image

logger = logging.getLogger(__name__)


MODEL_KWARGS_NOT_USED_REGEX = re.compile(r"The following `model_kwargs` are not used by the model: \[(.*?)\]")


class AsyncInferenceClient:
    """
    Initialize a new Inference Client.

    [`InferenceClient`] aims to provide a unified experience to perform inference. The client can be used
    seamlessly with either the (free) Inference API, self-hosted Inference Endpoints, or third-party Inference Providers.

    Args:
        model (`str`, `optional`):
            The model to run inference with. Can be a model id hosted on the Hugging Face Hub, e.g. `meta-llama/Meta-Llama-3-8B-Instruct`
            or a URL to a deployed Inference Endpoint. Defaults to None, in which case a recommended model is
            automatically selected for the task.
            Note: for better compatibility with OpenAI's client, `model` has been aliased as `base_url`. Those 2
            arguments are mutually exclusive. If using `base_url` for chat completion, the `/chat/completions` suffix
            path will be appended to the base URL (see the [TGI Messages API](https://huggingface.co/docs/text-generation-inference/en/messages_api)
            documentation for details). When passing a URL as `model`, the client will not append any suffix path to it.
        provider (`str`, *optional*):
            Name of the provider to use for inference. Can be `"black-forest-labs"`, `"cerebras"`, `"cohere"`, `"fal-ai"`, `"featherless-ai"`, `"fireworks-ai"`, `"groq"`, `"hf-inference"`, `"hyperbolic"`, `"nebius"`, `"novita"`, `"nscale"`, `"openai"`, `"replicate"`, "sambanova"` or `"together"`.
            Defaults to "auto" i.e. the first of the providers available for the model, sorted by the user's order in https://hf.co/settings/inference-providers.
            If model is a URL or `base_url` is passed, then `provider` is not used.
        token (`str`, *optional*):
            Hugging Face token. Will default to the locally saved token if not provided.
            Note: for better compatibility with OpenAI's client, `token` has been aliased as `api_key`. Those 2
            arguments are mutually exclusive and have the exact same behavior.
        timeout (`float`, `optional`):
            The maximum number of seconds to wait for a response from the server. Defaults to None, meaning it will loop until the server is available.
        headers (`Dict[str, str]`, `optional`):
            Additional headers to send to the server. By default only the authorization and user-agent headers are sent.
            Values in this dictionary will override the default values.
        bill_to (`str`, `optional`):
            The billing account to use for the requests. By default the requests are billed on the user's account.
            Requests can only be billed to an organization the user is a member of, and which has subscribed to Enterprise Hub.
        cookies (`Dict[str, str]`, `optional`):
            Additional cookies to send to the server.
        trust_env ('bool', 'optional'):
            Trust environment settings for proxy configuration if the parameter is `True` (`False` by default).
        proxies (`Any`, `optional`):
            Proxies to use for the request.
        base_url (`str`, `optional`):
            Base URL to run inference. This is a duplicated argument from `model` to make [`InferenceClient`]
            follow the same pattern as `openai.OpenAI` client. Cannot be used if `model` is set. Defaults to None.
        api_key (`str`, `optional`):
            Token to use for authentication. This is a duplicated argument from `token` to make [`InferenceClient`]
            follow the same pattern as `openai.OpenAI` client. Cannot be used if `token` is set. Defaults to None.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        *,
        provider: Optional[PROVIDER_OR_POLICY_T] = None,
        token: Optional[str] = None,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        trust_env: bool = False,
        proxies: Optional[Any] = None,
        bill_to: Optional[str] = None,
        # OpenAI compatibility
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        if model is not None and base_url is not None:
            raise ValueError(
                "Received both `model` and `base_url` arguments. Please provide only one of them."
                " `base_url` is an alias for `model` to make the API compatible with OpenAI's client."
                " If using `base_url` for chat completion, the `/chat/completions` suffix path will be appended to the base url."
                " When passing a URL as `model`, the client will not append any suffix path to it."
            )
        if token is not None and api_key is not None:
            raise ValueError(
                "Received both `token` and `api_key` arguments. Please provide only one of them."
                " `api_key` is an alias for `token` to make the API compatible with OpenAI's client."
                " It has the exact same behavior as `token`."
            )
        token = token if token is not None else api_key
        if isinstance(token, bool):
            # Legacy behavior: previously is was possible to pass `token=False` to disable authentication. This is not
            # supported anymore as authentication is required. Better to explicitly raise here rather than risking
            # sending the locally saved token without the user knowing about it.
            if token is False:
                raise ValueError(
                    "Cannot use `token=False` to disable authentication as authentication is required to run Inference."
                )
            warnings.warn(
                "Using `token=True` to automatically use the locally saved token is deprecated and will be removed in a future release. "
                "Please use `token=None` instead (default).",
                DeprecationWarning,
            )
            token = get_token()

        self.model: Optional[str] = base_url or model
        self.token: Optional[str] = token

        self.headers = {**headers} if headers is not None else {}
        if bill_to is not None:
            if (
                constants.HUGGINGFACE_HEADER_X_BILL_TO in self.headers
                and self.headers[constants.HUGGINGFACE_HEADER_X_BILL_TO] != bill_to
            ):
                warnings.warn(
                    f"Overriding existing '{self.headers[constants.HUGGINGFACE_HEADER_X_BILL_TO]}' value in headers with '{bill_to}'.",
                    UserWarning,
                )
            self.headers[constants.HUGGINGFACE_HEADER_X_BILL_TO] = bill_to

            if token is not None and not token.startswith("hf_"):
                warnings.warn(
                    "You've provided an external provider's API key, so requests will be billed directly by the provider. "
                    "The `bill_to` parameter is only applicable for Hugging Face billing and will be ignored.",
                    UserWarning,
                )

        # Configure provider
        self.provider = provider

        self.cookies = cookies
        self.timeout = timeout
        self.trust_env = trust_env
        self.proxies = proxies

        # Keep track of the sessions to close them properly
        self._sessions: Dict["ClientSession", Set["ClientResponse"]] = dict()

    def __repr__(self):
        return f"<InferenceClient(model='{self.model if self.model else ''}', timeout={self.timeout})>"

    @overload
    async def _inner_post(  # type: ignore[misc]
        self, request_parameters: RequestParameters, *, stream: Literal[False] = ...
    ) -> bytes: ...

    @overload
    async def _inner_post(  # type: ignore[misc]
        self, request_parameters: RequestParameters, *, stream: Literal[True] = ...
    ) -> AsyncIterable[bytes]: ...

    @overload
    async def _inner_post(
        self, request_parameters: RequestParameters, *, stream: bool = False
    ) -> Union[bytes, AsyncIterable[bytes]]: ...

    async def _inner_post(
        self, request_parameters: RequestParameters, *, stream: bool = False
    ) -> Union[bytes, AsyncIterable[bytes]]:
        """Make a request to the inference server."""

        aiohttp = _import_aiohttp()

        # TODO: this should be handled in provider helpers directly
        if request_parameters.task in TASKS_EXPECTING_IMAGES and "Accept" not in request_parameters.headers:
            request_parameters.headers["Accept"] = "image/png"

        with _open_as_binary(request_parameters.data) as data_as_binary:
            # Do not use context manager as we don't want to close the connection immediately when returning
            # a stream
            session = self._get_client_session(headers=request_parameters.headers)

            try:
                response = await session.post(
                    request_parameters.url, json=request_parameters.json, data=data_as_binary, proxy=self.proxies
                )
                response_error_payload = None
                if response.status != 200:
                    try:
                        response_error_payload = await response.json()  # get payload before connection closed
                    except Exception:
                        pass
                response.raise_for_status()
                if stream:
                    return _async_yield_from(session, response)
                else:
                    content = await response.read()
                    await session.close()
                    return content
            except asyncio.TimeoutError as error:
                await session.close()
                # Convert any `TimeoutError` to a `InferenceTimeoutError`
                raise InferenceTimeoutError(f"Inference call timed out: {request_parameters.url}") from error  # type: ignore
            except aiohttp.ClientResponseError as error:
                error.response_error_payload = response_error_payload
                await session.close()
                raise error
            except Exception:
                await session.close()
                raise

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    def __del__(self):
        if len(self._sessions) > 0:
            warnings.warn(
                "Deleting 'AsyncInferenceClient' client but some sessions are still open. "
                "This can happen if you've stopped streaming data from the server before the stream was complete. "
                "To close the client properly, you must call `await client.close()` "
                "or use an async context (e.g. `async with AsyncInferenceClient(): ...`."
            )

    async def close(self):
        """Close all open sessions.

        By default, 'aiohttp.ClientSession' objects are closed automatically when a call is completed. However, if you
        are streaming data from the server and you stop before the stream is complete, you must call this method to
        close the session properly.

        Another possibility is to use an async context (e.g. `async with AsyncInferenceClient(): ...`).
        """
        await asyncio.gather(*[session.close() for session in self._sessions.keys()])

    async def audio_classification(
        self,
        audio: ContentT,
        *,
        model: Optional[str] = None,
        top_k: Optional[int] = None,
        function_to_apply: Optional["AudioClassificationOutputTransform"] = None,
    ) -> List[AudioClassificationOutputElement]:
        """
        Perform audio classification on the provided audio content.

        Args:
            audio (Union[str, Path, bytes, BinaryIO]):
                The audio content to classify. It can be raw audio bytes, a local audio file, or a URL pointing to an
                audio file.
            model (`str`, *optional*):
                The model to use for audio classification. Can be a model ID hosted on the Hugging Face Hub
                or a URL to a deployed Inference Endpoint. If not provided, the default recommended model for
                audio classification will be used.
            top_k (`int`, *optional*):
                When specified, limits the output to the top K most probable classes.
            function_to_apply (`"AudioClassificationOutputTransform"`, *optional*):
                The function to apply to the model outputs in order to retrieve the scores.

        Returns:
            `List[AudioClassificationOutputElement]`: List of [`AudioClassificationOutputElement`] items containing the predicted labels and their confidence.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.audio_classification("audio.flac")
        [
            AudioClassificationOutputElement(score=0.4976358711719513, label='hap'),
            AudioClassificationOutputElement(score=0.3677836060523987, label='neu'),
            ...
        ]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="audio-classification", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=audio,
            parameters={"function_to_apply": function_to_apply, "top_k": top_k},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return AudioClassificationOutputElement.parse_obj_as_list(response)

    async def audio_to_audio(
        self,
        audio: ContentT,
        *,
        model: Optional[str] = None,
    ) -> List[AudioToAudioOutputElement]:
        """
        Performs multiple tasks related to audio-to-audio depending on the model (eg: speech enhancement, source separation).

        Args:
            audio (Union[str, Path, bytes, BinaryIO]):
                The audio content for the model. It can be raw audio bytes, a local audio file, or a URL pointing to an
                audio file.
            model (`str`, *optional*):
                The model can be any model which takes an audio file and returns another audio file. Can be a model ID hosted on the Hugging Face Hub
                or a URL to a deployed Inference Endpoint. If not provided, the default recommended model for
                audio_to_audio will be used.

        Returns:
            `List[AudioToAudioOutputElement]`: A list of [`AudioToAudioOutputElement`] items containing audios label, content-type, and audio content in blob.

        Raises:
            `InferenceTimeoutError`:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> audio_output = await client.audio_to_audio("audio.flac")
        >>> async for i, item in enumerate(audio_output):
        >>>     with open(f"output_{i}.flac", "wb") as f:
                    f.write(item.blob)
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="audio-to-audio", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=audio,
            parameters={},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        audio_output = AudioToAudioOutputElement.parse_obj_as_list(response)
        for item in audio_output:
            item.blob = base64.b64decode(item.blob)
        return audio_output

    async def automatic_speech_recognition(
        self,
        audio: ContentT,
        *,
        model: Optional[str] = None,
        extra_body: Optional[Dict] = None,
    ) -> AutomaticSpeechRecognitionOutput:
        """
        Perform automatic speech recognition (ASR or audio-to-text) on the given audio content.

        Args:
            audio (Union[str, Path, bytes, BinaryIO]):
                The content to transcribe. It can be raw audio bytes, local audio file, or a URL to an audio file.
            model (`str`, *optional*):
                The model to use for ASR. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. If not provided, the default recommended model for ASR will be used.
            extra_body (`Dict`, *optional*):
                Additional provider-specific parameters to pass to the model. Refer to the provider's documentation
                for supported parameters.
        Returns:
            [`AutomaticSpeechRecognitionOutput`]: An item containing the transcribed text and optionally the timestamp chunks.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.automatic_speech_recognition("hello_world.flac").text
        "hello world"
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="automatic-speech-recognition", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=audio,
            parameters={**(extra_body or {})},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return AutomaticSpeechRecognitionOutput.parse_obj_as_instance(response)

    @overload
    async def chat_completion(  # type: ignore
        self,
        messages: List[Union[Dict, ChatCompletionInputMessage]],
        *,
        model: Optional[str] = None,
        stream: Literal[False] = False,
        frequency_penalty: Optional[float] = None,
        logit_bias: Optional[List[float]] = None,
        logprobs: Optional[bool] = None,
        max_tokens: Optional[int] = None,
        n: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        response_format: Optional[ChatCompletionInputGrammarType] = None,
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stream_options: Optional[ChatCompletionInputStreamOptions] = None,
        temperature: Optional[float] = None,
        tool_choice: Optional[Union[ChatCompletionInputToolChoiceClass, "ChatCompletionInputToolChoiceEnum"]] = None,
        tool_prompt: Optional[str] = None,
        tools: Optional[List[ChatCompletionInputTool]] = None,
        top_logprobs: Optional[int] = None,
        top_p: Optional[float] = None,
        extra_body: Optional[Dict] = None,
    ) -> ChatCompletionOutput: ...

    @overload
    async def chat_completion(  # type: ignore
        self,
        messages: List[Union[Dict, ChatCompletionInputMessage]],
        *,
        model: Optional[str] = None,
        stream: Literal[True] = True,
        frequency_penalty: Optional[float] = None,
        logit_bias: Optional[List[float]] = None,
        logprobs: Optional[bool] = None,
        max_tokens: Optional[int] = None,
        n: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        response_format: Optional[ChatCompletionInputGrammarType] = None,
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stream_options: Optional[ChatCompletionInputStreamOptions] = None,
        temperature: Optional[float] = None,
        tool_choice: Optional[Union[ChatCompletionInputToolChoiceClass, "ChatCompletionInputToolChoiceEnum"]] = None,
        tool_prompt: Optional[str] = None,
        tools: Optional[List[ChatCompletionInputTool]] = None,
        top_logprobs: Optional[int] = None,
        top_p: Optional[float] = None,
        extra_body: Optional[Dict] = None,
    ) -> AsyncIterable[ChatCompletionStreamOutput]: ...

    @overload
    async def chat_completion(
        self,
        messages: List[Union[Dict, ChatCompletionInputMessage]],
        *,
        model: Optional[str] = None,
        stream: bool = False,
        frequency_penalty: Optional[float] = None,
        logit_bias: Optional[List[float]] = None,
        logprobs: Optional[bool] = None,
        max_tokens: Optional[int] = None,
        n: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        response_format: Optional[ChatCompletionInputGrammarType] = None,
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stream_options: Optional[ChatCompletionInputStreamOptions] = None,
        temperature: Optional[float] = None,
        tool_choice: Optional[Union[ChatCompletionInputToolChoiceClass, "ChatCompletionInputToolChoiceEnum"]] = None,
        tool_prompt: Optional[str] = None,
        tools: Optional[List[ChatCompletionInputTool]] = None,
        top_logprobs: Optional[int] = None,
        top_p: Optional[float] = None,
        extra_body: Optional[Dict] = None,
    ) -> Union[ChatCompletionOutput, AsyncIterable[ChatCompletionStreamOutput]]: ...

    async def chat_completion(
        self,
        messages: List[Union[Dict, ChatCompletionInputMessage]],
        *,
        model: Optional[str] = None,
        stream: bool = False,
        # Parameters from ChatCompletionInput (handled manually)
        frequency_penalty: Optional[float] = None,
        logit_bias: Optional[List[float]] = None,
        logprobs: Optional[bool] = None,
        max_tokens: Optional[int] = None,
        n: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        response_format: Optional[ChatCompletionInputGrammarType] = None,
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stream_options: Optional[ChatCompletionInputStreamOptions] = None,
        temperature: Optional[float] = None,
        tool_choice: Optional[Union[ChatCompletionInputToolChoiceClass, "ChatCompletionInputToolChoiceEnum"]] = None,
        tool_prompt: Optional[str] = None,
        tools: Optional[List[ChatCompletionInputTool]] = None,
        top_logprobs: Optional[int] = None,
        top_p: Optional[float] = None,
        extra_body: Optional[Dict] = None,
    ) -> Union[ChatCompletionOutput, AsyncIterable[ChatCompletionStreamOutput]]:
        """
        A method for completing conversations using a specified language model.

        <Tip>

        The `client.chat_completion` method is aliased as `client.chat.completions.create` for compatibility with OpenAI's client.
        Inputs and outputs are strictly the same and using either syntax will yield the same results.
        Check out the [Inference guide](https://huggingface.co/docs/huggingface_hub/guides/inference#openai-compatibility)
        for more details about OpenAI's compatibility.

        </Tip>

        <Tip>
        You can pass provider-specific parameters to the model by using the `extra_body` argument.
        </Tip>

        Args:
            messages (List of [`ChatCompletionInputMessage`]):
                Conversation history consisting of roles and content pairs.
            model (`str`, *optional*):
                The model to use for chat-completion. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. If not provided, the default recommended model for chat-based text-generation will be used.
                See https://huggingface.co/tasks/text-generation for more details.
                If `model` is a model ID, it is passed to the server as the `model` parameter. If you want to define a
                custom URL while setting `model` in the request payload, you must set `base_url` when initializing [`InferenceClient`].
            frequency_penalty (`float`, *optional*):
                Penalizes new tokens based on their existing frequency
                in the text so far. Range: [-2.0, 2.0]. Defaults to 0.0.
            logit_bias (`List[float]`, *optional*):
                Adjusts the likelihood of specific tokens appearing in the generated output.
            logprobs (`bool`, *optional*):
                Whether to return log probabilities of the output tokens or not. If true, returns the log
                probabilities of each output token returned in the content of message.
            max_tokens (`int`, *optional*):
                Maximum number of tokens allowed in the response. Defaults to 100.
            n (`int`, *optional*):
                The number of completions to generate for each prompt.
            presence_penalty (`float`, *optional*):
                Number between -2.0 and 2.0. Positive values penalize new tokens based on whether they appear in the
                text so far, increasing the model's likelihood to talk about new topics.
            response_format ([`ChatCompletionInputGrammarType`], *optional*):
                Grammar constraints. Can be either a JSONSchema or a regex.
            seed (Optional[`int`], *optional*):
                Seed for reproducible control flow. Defaults to None.
            stop (`List[str]`, *optional*):
                Up to four strings which trigger the end of the response.
                Defaults to None.
            stream (`bool`, *optional*):
                Enable realtime streaming of responses. Defaults to False.
            stream_options ([`ChatCompletionInputStreamOptions`], *optional*):
                Options for streaming completions.
            temperature (`float`, *optional*):
                Controls randomness of the generations. Lower values ensure
                less random completions. Range: [0, 2]. Defaults to 1.0.
            top_logprobs (`int`, *optional*):
                An integer between 0 and 5 specifying the number of most likely tokens to return at each token
                position, each with an associated log probability. logprobs must be set to true if this parameter is
                used.
            top_p (`float`, *optional*):
                Fraction of the most likely next words to sample from.
                Must be between 0 and 1. Defaults to 1.0.
            tool_choice ([`ChatCompletionInputToolChoiceClass`] or [`ChatCompletionInputToolChoiceEnum`], *optional*):
                The tool to use for the completion. Defaults to "auto".
            tool_prompt (`str`, *optional*):
                A prompt to be appended before the tools.
            tools (List of [`ChatCompletionInputTool`], *optional*):
                A list of tools the model may call. Currently, only functions are supported as a tool. Use this to
                provide a list of functions the model may generate JSON inputs for.
            extra_body (`Dict`, *optional*):
                Additional provider-specific parameters to pass to the model. Refer to the provider's documentation
                for supported parameters.
        Returns:
            [`ChatCompletionOutput`] or Iterable of [`ChatCompletionStreamOutput`]:
            Generated text returned from the server:
            - if `stream=False`, the generated text is returned as a [`ChatCompletionOutput`] (default).
            - if `stream=True`, the generated text is returned token by token as a sequence of [`ChatCompletionStreamOutput`].

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:

        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> messages = [{"role": "user", "content": "What is the capital of France?"}]
        >>> client = AsyncInferenceClient("meta-llama/Meta-Llama-3-8B-Instruct")
        >>> await client.chat_completion(messages, max_tokens=100)
        ChatCompletionOutput(
            choices=[
                ChatCompletionOutputComplete(
                    finish_reason='eos_token',
                    index=0,
                    message=ChatCompletionOutputMessage(
                        role='assistant',
                        content='The capital of France is Paris.',
                        name=None,
                        tool_calls=None
                    ),
                    logprobs=None
                )
            ],
            created=1719907176,
            id='',
            model='meta-llama/Meta-Llama-3-8B-Instruct',
            object='text_completion',
            system_fingerprint='2.0.4-sha-f426a33',
            usage=ChatCompletionOutputUsage(
                completion_tokens=8,
                prompt_tokens=17,
                total_tokens=25
            )
        )
        ```

        Example using streaming:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> messages = [{"role": "user", "content": "What is the capital of France?"}]
        >>> client = AsyncInferenceClient("meta-llama/Meta-Llama-3-8B-Instruct")
        >>> async for token in await client.chat_completion(messages, max_tokens=10, stream=True):
        ...     print(token)
        ChatCompletionStreamOutput(choices=[ChatCompletionStreamOutputChoice(delta=ChatCompletionStreamOutputDelta(content='The', role='assistant'), index=0, finish_reason=None)], created=1710498504)
        ChatCompletionStreamOutput(choices=[ChatCompletionStreamOutputChoice(delta=ChatCompletionStreamOutputDelta(content=' capital', role='assistant'), index=0, finish_reason=None)], created=1710498504)
        (...)
        ChatCompletionStreamOutput(choices=[ChatCompletionStreamOutputChoice(delta=ChatCompletionStreamOutputDelta(content=' may', role='assistant'), index=0, finish_reason=None)], created=1710498504)
        ```

        Example using OpenAI's syntax:
        ```py
        # Must be run in an async context
        # instead of `from openai import OpenAI`
        from huggingface_hub import AsyncInferenceClient

        # instead of `client = OpenAI(...)`
        client = AsyncInferenceClient(
            base_url=...,
            api_key=...,
        )

        output = await client.chat.completions.create(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Count to 10"},
            ],
            stream=True,
            max_tokens=1024,
        )

        for chunk in output:
            print(chunk.choices[0].delta.content)
        ```

        Example using a third-party provider directly with extra (provider-specific) parameters. Usage will be billed on your Together AI account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="together",  # Use Together AI provider
        ...     api_key="<together_api_key>",  # Pass your Together API key directly
        ... )
        >>> client.chat_completion(
        ...     model="meta-llama/Meta-Llama-3-8B-Instruct",
        ...     messages=[{"role": "user", "content": "What is the capital of France?"}],
        ...     extra_body={"safety_model": "Meta-Llama/Llama-Guard-7b"},
        ... )
        ```

        Example using a third-party provider through Hugging Face Routing. Usage will be billed on your Hugging Face account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="sambanova",  # Use Sambanova provider
        ...     api_key="hf_...",  # Pass your HF token
        ... )
        >>> client.chat_completion(
        ...     model="meta-llama/Meta-Llama-3-8B-Instruct",
        ...     messages=[{"role": "user", "content": "What is the capital of France?"}],
        ... )
        ```

        Example using Image + Text as input:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient

        # provide a remote URL
        >>> image_url ="https://cdn.britannica.com/61/93061-050-99147DCE/Statue-of-Liberty-Island-New-York-Bay.jpg"
        # or a base64-encoded image
        >>> image_path = "/path/to/image.jpeg"
        >>> with open(image_path, "rb") as f:
        ...     base64_image = base64.b64encode(f.read()).decode("utf-8")
        >>> image_url = f"data:image/jpeg;base64,{base64_image}"

        >>> client = AsyncInferenceClient("meta-llama/Llama-3.2-11B-Vision-Instruct")
        >>> output = await client.chat.completions.create(
        ...     messages=[
        ...         {
        ...             "role": "user",
        ...             "content": [
        ...                 {
        ...                     "type": "image_url",
        ...                     "image_url": {"url": image_url},
        ...                 },
        ...                 {
        ...                     "type": "text",
        ...                     "text": "Describe this image in one sentence.",
        ...                 },
        ...             ],
        ...         },
        ...     ],
        ... )
        >>> output
        The image depicts the iconic Statue of Liberty situated in New York Harbor, New York, on a clear day.
        ```

        Example using tools:
        ```py
        # Must be run in an async context
        >>> client = AsyncInferenceClient("meta-llama/Meta-Llama-3-70B-Instruct")
        >>> messages = [
        ...     {
        ...         "role": "system",
        ...         "content": "Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous.",
        ...     },
        ...     {
        ...         "role": "user",
        ...         "content": "What's the weather like the next 3 days in San Francisco, CA?",
        ...     },
        ... ]
        >>> tools = [
        ...     {
        ...         "type": "function",
        ...         "function": {
        ...             "name": "get_current_weather",
        ...             "description": "Get the current weather",
        ...             "parameters": {
        ...                 "type": "object",
        ...                 "properties": {
        ...                     "location": {
        ...                         "type": "string",
        ...                         "description": "The city and state, e.g. San Francisco, CA",
        ...                     },
        ...                     "format": {
        ...                         "type": "string",
        ...                         "enum": ["celsius", "fahrenheit"],
        ...                         "description": "The temperature unit to use. Infer this from the users location.",
        ...                     },
        ...                 },
        ...                 "required": ["location", "format"],
        ...             },
        ...         },
        ...     },
        ...     {
        ...         "type": "function",
        ...         "function": {
        ...             "name": "get_n_day_weather_forecast",
        ...             "description": "Get an N-day weather forecast",
        ...             "parameters": {
        ...                 "type": "object",
        ...                 "properties": {
        ...                     "location": {
        ...                         "type": "string",
        ...                         "description": "The city and state, e.g. San Francisco, CA",
        ...                     },
        ...                     "format": {
        ...                         "type": "string",
        ...                         "enum": ["celsius", "fahrenheit"],
        ...                         "description": "The temperature unit to use. Infer this from the users location.",
        ...                     },
        ...                     "num_days": {
        ...                         "type": "integer",
        ...                         "description": "The number of days to forecast",
        ...                     },
        ...                 },
        ...                 "required": ["location", "format", "num_days"],
        ...             },
        ...         },
        ...     },
        ... ]

        >>> response = await client.chat_completion(
        ...     model="meta-llama/Meta-Llama-3-70B-Instruct",
        ...     messages=messages,
        ...     tools=tools,
        ...     tool_choice="auto",
        ...     max_tokens=500,
        ... )
        >>> response.choices[0].message.tool_calls[0].function
        ChatCompletionOutputFunctionDefinition(
            arguments={
                'location': 'San Francisco, CA',
                'format': 'fahrenheit',
                'num_days': 3
            },
            name='get_n_day_weather_forecast',
            description=None
        )
        ```

        Example using response_format:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient("meta-llama/Meta-Llama-3-70B-Instruct")
        >>> messages = [
        ...     {
        ...         "role": "user",
        ...         "content": "I saw a puppy a cat and a raccoon during my bike ride in the park. What did I saw and when?",
        ...     },
        ... ]
        >>> response_format = {
        ...     "type": "json",
        ...     "value": {
        ...         "properties": {
        ...             "location": {"type": "string"},
        ...             "activity": {"type": "string"},
        ...             "animals_seen": {"type": "integer", "minimum": 1, "maximum": 5},
        ...             "animals": {"type": "array", "items": {"type": "string"}},
        ...         },
        ...         "required": ["location", "activity", "animals_seen", "animals"],
        ...     },
        ... }
        >>> response = await client.chat_completion(
        ...     messages=messages,
        ...     response_format=response_format,
        ...     max_tokens=500,
        ... )
        >>> response.choices[0].message.content
        '{\n\n"activity": "bike ride",\n"animals": ["puppy", "cat", "raccoon"],\n"animals_seen": 3,\n"location": "park"}'
        ```
        """
        # Since `chat_completion(..., model=xxx)` is also a payload parameter for the server, we need to handle 'model' differently.
        # `self.model` takes precedence over 'model' argument for building URL.
        # `model` takes precedence for payload value.
        model_id_or_url = self.model or model
        payload_model = model or self.model

        # Get the provider helper
        provider_helper = get_provider_helper(
            self.provider,
            task="conversational",
            model=model_id_or_url
            if model_id_or_url is not None and model_id_or_url.startswith(("http://", "https://"))
            else payload_model,
        )

        # Prepare the payload
        parameters = {
            "model": payload_model,
            "frequency_penalty": frequency_penalty,
            "logit_bias": logit_bias,
            "logprobs": logprobs,
            "max_tokens": max_tokens,
            "n": n,
            "presence_penalty": presence_penalty,
            "response_format": response_format,
            "seed": seed,
            "stop": stop,
            "temperature": temperature,
            "tool_choice": tool_choice,
            "tool_prompt": tool_prompt,
            "tools": tools,
            "top_logprobs": top_logprobs,
            "top_p": top_p,
            "stream": stream,
            "stream_options": stream_options,
            **(extra_body or {}),
        }
        request_parameters = provider_helper.prepare_request(
            inputs=messages,
            parameters=parameters,
            headers=self.headers,
            model=model_id_or_url,
            api_key=self.token,
        )
        data = await self._inner_post(request_parameters, stream=stream)

        if stream:
            return _async_stream_chat_completion_response(data)  # type: ignore[arg-type]

        return ChatCompletionOutput.parse_obj_as_instance(data)  # type: ignore[arg-type]

    async def document_question_answering(
        self,
        image: ContentT,
        question: str,
        *,
        model: Optional[str] = None,
        doc_stride: Optional[int] = None,
        handle_impossible_answer: Optional[bool] = None,
        lang: Optional[str] = None,
        max_answer_len: Optional[int] = None,
        max_question_len: Optional[int] = None,
        max_seq_len: Optional[int] = None,
        top_k: Optional[int] = None,
        word_boxes: Optional[List[Union[List[float], str]]] = None,
    ) -> List[DocumentQuestionAnsweringOutputElement]:
        """
        Answer questions on document images.

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The input image for the context. It can be raw bytes, an image file, or a URL to an online image.
            question (`str`):
                Question to be answered.
            model (`str`, *optional*):
                The model to use for the document question answering task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended document question answering model will be used.
                Defaults to None.
            doc_stride (`int`, *optional*):
                If the words in the document are too long to fit with the question for the model, it will be split in
                several chunks with some overlap. This argument controls the size of that overlap.
            handle_impossible_answer (`bool`, *optional*):
                Whether to accept impossible as an answer
            lang (`str`, *optional*):
                Language to use while running OCR. Defaults to english.
            max_answer_len (`int`, *optional*):
                The maximum length of predicted answers (e.g., only answers with a shorter length are considered).
            max_question_len (`int`, *optional*):
                The maximum length of the question after tokenization. It will be truncated if needed.
            max_seq_len (`int`, *optional*):
                The maximum length of the total sentence (context + question) in tokens of each chunk passed to the
                model. The context will be split in several chunks (using doc_stride as overlap) if needed.
            top_k (`int`, *optional*):
                The number of answers to return (will be chosen by order of likelihood). Can return less than top_k
                answers if there are not enough options available within the context.
            word_boxes (`List[Union[List[float], str`, *optional*):
                A list of words and bounding boxes (normalized 0->1000). If provided, the inference will skip the OCR
                step and use the provided bounding boxes instead.
        Returns:
            `List[DocumentQuestionAnsweringOutputElement]`: a list of [`DocumentQuestionAnsweringOutputElement`] items containing the predicted label, associated probability, word ids, and page number.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.


        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.document_question_answering(image="https://huggingface.co/spaces/impira/docquery/resolve/2359223c1837a7587402bda0f2643382a6eefeab/invoice.png", question="What is the invoice number?")
        [DocumentQuestionAnsweringOutputElement(answer='us-001', end=16, score=0.9999666213989258, start=16)]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="document-question-answering", model=model_id)
        inputs: Dict[str, Any] = {"question": question, "image": _b64_encode(image)}
        request_parameters = provider_helper.prepare_request(
            inputs=inputs,
            parameters={
                "doc_stride": doc_stride,
                "handle_impossible_answer": handle_impossible_answer,
                "lang": lang,
                "max_answer_len": max_answer_len,
                "max_question_len": max_question_len,
                "max_seq_len": max_seq_len,
                "top_k": top_k,
                "word_boxes": word_boxes,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return DocumentQuestionAnsweringOutputElement.parse_obj_as_list(response)

    async def feature_extraction(
        self,
        text: str,
        *,
        normalize: Optional[bool] = None,
        prompt_name: Optional[str] = None,
        truncate: Optional[bool] = None,
        truncation_direction: Optional[Literal["Left", "Right"]] = None,
        model: Optional[str] = None,
    ) -> "np.ndarray":
        """
        Generate embeddings for a given text.

        Args:
            text (`str`):
                The text to embed.
            model (`str`, *optional*):
                The model to use for the feature extraction task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended feature extraction model will be used.
                Defaults to None.
            normalize (`bool`, *optional*):
                Whether to normalize the embeddings or not.
                Only available on server powered by Text-Embedding-Inference.
            prompt_name (`str`, *optional*):
                The name of the prompt that should be used by for encoding. If not set, no prompt will be applied.
                Must be a key in the `Sentence Transformers` configuration `prompts` dictionary.
                For example if ``prompt_name`` is "query" and the ``prompts`` is {"query": "query: ",...},
                then the sentence "What is the capital of France?" will be encoded as "query: What is the capital of France?"
                because the prompt text will be prepended before any text to encode.
            truncate (`bool`, *optional*):
                Whether to truncate the embeddings or not.
                Only available on server powered by Text-Embedding-Inference.
            truncation_direction (`Literal["Left", "Right"]`, *optional*):
                Which side of the input should be truncated when `truncate=True` is passed.

        Returns:
            `np.ndarray`: The embedding representing the input text as a float32 numpy array.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.feature_extraction("Hi, who are you?")
        array([[ 2.424802  ,  2.93384   ,  1.1750331 , ...,  1.240499, -0.13776633, -0.7889173 ],
        [-0.42943227, -0.6364878 , -1.693462  , ...,  0.41978157, -2.4336355 ,  0.6162071 ],
        ...,
        [ 0.28552425, -0.928395  , -1.2077185 , ...,  0.76810825, -2.1069427 ,  0.6236161 ]], dtype=float32)
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="feature-extraction", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters={
                "normalize": normalize,
                "prompt_name": prompt_name,
                "truncate": truncate,
                "truncation_direction": truncation_direction,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        np = _import_numpy()
        return np.array(provider_helper.get_response(response), dtype="float32")

    async def fill_mask(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        targets: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> List[FillMaskOutputElement]:
        """
        Fill in a hole with a missing word (token to be precise).

        Args:
            text (`str`):
                a string to be filled from, must contain the [MASK] token (check model card for exact name of the mask).
            model (`str`, *optional*):
                The model to use for the fill mask task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended fill mask model will be used.
            targets (`List[str`, *optional*):
                When passed, the model will limit the scores to the passed targets instead of looking up in the whole
                vocabulary. If the provided targets are not in the model vocab, they will be tokenized and the first
                resulting token will be used (with a warning, and that might be slower).
            top_k (`int`, *optional*):
                When passed, overrides the number of predictions to return.
        Returns:
            `List[FillMaskOutputElement]`: a list of [`FillMaskOutputElement`] items containing the predicted label, associated
            probability, token reference, and completed text.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.fill_mask("The goal of life is <mask>.")
        [
            FillMaskOutputElement(score=0.06897063553333282, token=11098, token_str=' happiness', sequence='The goal of life is happiness.'),
            FillMaskOutputElement(score=0.06554922461509705, token=45075, token_str=' immortality', sequence='The goal of life is immortality.')
        ]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="fill-mask", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters={"targets": targets, "top_k": top_k},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return FillMaskOutputElement.parse_obj_as_list(response)

    async def image_classification(
        self,
        image: ContentT,
        *,
        model: Optional[str] = None,
        function_to_apply: Optional["ImageClassificationOutputTransform"] = None,
        top_k: Optional[int] = None,
    ) -> List[ImageClassificationOutputElement]:
        """
        Perform image classification on the given image using the specified model.

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The image to classify. It can be raw bytes, an image file, or a URL to an online image.
            model (`str`, *optional*):
                The model to use for image classification. Can be a model ID hosted on the Hugging Face Hub or a URL to a
                deployed Inference Endpoint. If not provided, the default recommended model for image classification will be used.
            function_to_apply (`"ImageClassificationOutputTransform"`, *optional*):
                The function to apply to the model outputs in order to retrieve the scores.
            top_k (`int`, *optional*):
                When specified, limits the output to the top K most probable classes.
        Returns:
            `List[ImageClassificationOutputElement]`: a list of [`ImageClassificationOutputElement`] items containing the predicted label and associated probability.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.image_classification("https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Cute_dog.jpg/320px-Cute_dog.jpg")
        [ImageClassificationOutputElement(label='Blenheim spaniel', score=0.9779096841812134), ...]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="image-classification", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=image,
            parameters={"function_to_apply": function_to_apply, "top_k": top_k},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return ImageClassificationOutputElement.parse_obj_as_list(response)

    async def image_segmentation(
        self,
        image: ContentT,
        *,
        model: Optional[str] = None,
        mask_threshold: Optional[float] = None,
        overlap_mask_area_threshold: Optional[float] = None,
        subtask: Optional["ImageSegmentationSubtask"] = None,
        threshold: Optional[float] = None,
    ) -> List[ImageSegmentationOutputElement]:
        """
        Perform image segmentation on the given image using the specified model.

        <Tip warning={true}>

        You must have `PIL` installed if you want to work with images (`pip install Pillow`).

        </Tip>

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The image to segment. It can be raw bytes, an image file, or a URL to an online image.
            model (`str`, *optional*):
                The model to use for image segmentation. Can be a model ID hosted on the Hugging Face Hub or a URL to a
                deployed Inference Endpoint. If not provided, the default recommended model for image segmentation will be used.
            mask_threshold (`float`, *optional*):
                Threshold to use when turning the predicted masks into binary values.
            overlap_mask_area_threshold (`float`, *optional*):
                Mask overlap threshold to eliminate small, disconnected segments.
            subtask (`"ImageSegmentationSubtask"`, *optional*):
                Segmentation task to be performed, depending on model capabilities.
            threshold (`float`, *optional*):
                Probability threshold to filter out predicted masks.
        Returns:
            `List[ImageSegmentationOutputElement]`: A list of [`ImageSegmentationOutputElement`] items containing the segmented masks and associated attributes.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.image_segmentation("cat.jpg")
        [ImageSegmentationOutputElement(score=0.989008, label='LABEL_184', mask=<PIL.PngImagePlugin.PngImageFile image mode=L size=400x300 at 0x7FDD2B129CC0>), ...]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="image-segmentation", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=image,
            parameters={
                "mask_threshold": mask_threshold,
                "overlap_mask_area_threshold": overlap_mask_area_threshold,
                "subtask": subtask,
                "threshold": threshold,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        output = ImageSegmentationOutputElement.parse_obj_as_list(response)
        for item in output:
            item.mask = _b64_to_image(item.mask)  # type: ignore [assignment]
        return output

    async def image_to_image(
        self,
        image: ContentT,
        prompt: Optional[str] = None,
        *,
        negative_prompt: Optional[str] = None,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        model: Optional[str] = None,
        target_size: Optional[ImageToImageTargetSize] = None,
        **kwargs,
    ) -> "Image":
        """
        Perform image-to-image translation using a specified model.

        <Tip warning={true}>

        You must have `PIL` installed if you want to work with images (`pip install Pillow`).

        </Tip>

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The input image for translation. It can be raw bytes, an image file, or a URL to an online image.
            prompt (`str`, *optional*):
                The text prompt to guide the image generation.
            negative_prompt (`str`, *optional*):
                One prompt to guide what NOT to include in image generation.
            num_inference_steps (`int`, *optional*):
                For diffusion models. The number of denoising steps. More denoising steps usually lead to a higher
                quality image at the expense of slower inference.
            guidance_scale (`float`, *optional*):
                For diffusion models. A higher guidance scale value encourages the model to generate images closely
                linked to the text prompt at the expense of lower image quality.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. This parameter overrides the model defined at the instance level. Defaults to None.
            target_size (`ImageToImageTargetSize`, *optional*):
                The size in pixel of the output image.

        Returns:
            `Image`: The translated image.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> image = await client.image_to_image("cat.jpg", prompt="turn the cat into a tiger")
        >>> image.save("tiger.jpg")
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="image-to-image", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=image,
            parameters={
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "target_size": target_size,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                **kwargs,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return _bytes_to_image(response)

    async def image_to_text(self, image: ContentT, *, model: Optional[str] = None) -> ImageToTextOutput:
        """
        Takes an input image and return text.

        Models can have very different outputs depending on your use case (image captioning, optical character recognition
        (OCR), Pix2Struct, etc). Please have a look to the model card to learn more about a model's specificities.

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The input image to caption. It can be raw bytes, an image file, or a URL to an online image..
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. This parameter overrides the model defined at the instance level. Defaults to None.

        Returns:
            [`ImageToTextOutput`]: The generated text.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.image_to_text("cat.jpg")
        'a cat standing in a grassy field '
        >>> await client.image_to_text("https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Cute_dog.jpg/320px-Cute_dog.jpg")
        'a dog laying on the grass next to a flower pot '
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="image-to-text", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=image,
            parameters={},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        output = ImageToTextOutput.parse_obj(response)
        return output[0] if isinstance(output, list) else output

    async def object_detection(
        self, image: ContentT, *, model: Optional[str] = None, threshold: Optional[float] = None
    ) -> List[ObjectDetectionOutputElement]:
        """
        Perform object detection on the given image using the specified model.

        <Tip warning={true}>

        You must have `PIL` installed if you want to work with images (`pip install Pillow`).

        </Tip>

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The image to detect objects on. It can be raw bytes, an image file, or a URL to an online image.
            model (`str`, *optional*):
                The model to use for object detection. Can be a model ID hosted on the Hugging Face Hub or a URL to a
                deployed Inference Endpoint. If not provided, the default recommended model for object detection (DETR) will be used.
            threshold (`float`, *optional*):
                The probability necessary to make a prediction.
        Returns:
            `List[ObjectDetectionOutputElement]`: A list of [`ObjectDetectionOutputElement`] items containing the bounding boxes and associated attributes.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.
            `ValueError`:
                If the request output is not a List.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.object_detection("people.jpg")
        [ObjectDetectionOutputElement(score=0.9486683011054993, label='person', box=ObjectDetectionBoundingBox(xmin=59, ymin=39, xmax=420, ymax=510)), ...]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="object-detection", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=image,
            parameters={"threshold": threshold},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return ObjectDetectionOutputElement.parse_obj_as_list(response)

    async def question_answering(
        self,
        question: str,
        context: str,
        *,
        model: Optional[str] = None,
        align_to_words: Optional[bool] = None,
        doc_stride: Optional[int] = None,
        handle_impossible_answer: Optional[bool] = None,
        max_answer_len: Optional[int] = None,
        max_question_len: Optional[int] = None,
        max_seq_len: Optional[int] = None,
        top_k: Optional[int] = None,
    ) -> Union[QuestionAnsweringOutputElement, List[QuestionAnsweringOutputElement]]:
        """
        Retrieve the answer to a question from a given text.

        Args:
            question (`str`):
                Question to be answered.
            context (`str`):
                The context of the question.
            model (`str`):
                The model to use for the question answering task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint.
            align_to_words (`bool`, *optional*):
                Attempts to align the answer to real words. Improves quality on space separated languages. Might hurt
                on non-space-separated languages (like Japanese or Chinese)
            doc_stride (`int`, *optional*):
                If the context is too long to fit with the question for the model, it will be split in several chunks
                with some overlap. This argument controls the size of that overlap.
            handle_impossible_answer (`bool`, *optional*):
                Whether to accept impossible as an answer.
            max_answer_len (`int`, *optional*):
                The maximum length of predicted answers (e.g., only answers with a shorter length are considered).
            max_question_len (`int`, *optional*):
                The maximum length of the question after tokenization. It will be truncated if needed.
            max_seq_len (`int`, *optional*):
                The maximum length of the total sentence (context + question) in tokens of each chunk passed to the
                model. The context will be split in several chunks (using docStride as overlap) if needed.
            top_k (`int`, *optional*):
                The number of answers to return (will be chosen by order of likelihood). Note that we return less than
                topk answers if there are not enough options available within the context.

        Returns:
            Union[`QuestionAnsweringOutputElement`, List[`QuestionAnsweringOutputElement`]]:
                When top_k is 1 or not provided, it returns a single `QuestionAnsweringOutputElement`.
                When top_k is greater than 1, it returns a list of `QuestionAnsweringOutputElement`.
        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.question_answering(question="What's my name?", context="My name is Clara and I live in Berkeley.")
        QuestionAnsweringOutputElement(answer='Clara', end=16, score=0.9326565265655518, start=11)
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="question-answering", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs={"question": question, "context": context},
            parameters={
                "align_to_words": align_to_words,
                "doc_stride": doc_stride,
                "handle_impossible_answer": handle_impossible_answer,
                "max_answer_len": max_answer_len,
                "max_question_len": max_question_len,
                "max_seq_len": max_seq_len,
                "top_k": top_k,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        # Parse the response as a single `QuestionAnsweringOutputElement` when top_k is 1 or not provided, or a list of `QuestionAnsweringOutputElement` to ensure backward compatibility.
        output = QuestionAnsweringOutputElement.parse_obj(response)
        return output

    async def sentence_similarity(
        self, sentence: str, other_sentences: List[str], *, model: Optional[str] = None
    ) -> List[float]:
        """
        Compute the semantic similarity between a sentence and a list of other sentences by comparing their embeddings.

        Args:
            sentence (`str`):
                The main sentence to compare to others.
            other_sentences (`List[str]`):
                The list of sentences to compare to.
            model (`str`, *optional*):
                The model to use for the sentence similarity task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended sentence similarity model will be used.
                Defaults to None.

        Returns:
            `List[float]`: The embedding representing the input text.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.sentence_similarity(
        ...     "Machine learning is so easy.",
        ...     other_sentences=[
        ...         "Deep learning is so straightforward.",
        ...         "This is so difficult, like rocket science.",
        ...         "I can't believe how much I struggled with this.",
        ...     ],
        ... )
        [0.7785726189613342, 0.45876261591911316, 0.2906220555305481]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="sentence-similarity", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs={"source_sentence": sentence, "sentences": other_sentences},
            parameters={},
            extra_payload={},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return _bytes_to_list(response)

    async def summarization(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        clean_up_tokenization_spaces: Optional[bool] = None,
        generate_parameters: Optional[Dict[str, Any]] = None,
        truncation: Optional["SummarizationTruncationStrategy"] = None,
    ) -> SummarizationOutput:
        """
        Generate a summary of a given text using a specified model.

        Args:
            text (`str`):
                The input text to summarize.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. If not provided, the default recommended model for summarization will be used.
            clean_up_tokenization_spaces (`bool`, *optional*):
                Whether to clean up the potential extra spaces in the text output.
            generate_parameters (`Dict[str, Any]`, *optional*):
                Additional parametrization of the text generation algorithm.
            truncation (`"SummarizationTruncationStrategy"`, *optional*):
                The truncation strategy to use.
        Returns:
            [`SummarizationOutput`]: The generated summary text.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.summarization("The Eiffel tower...")
        SummarizationOutput(generated_text="The Eiffel tower is one of the most famous landmarks in the world....")
        ```
        """
        parameters = {
            "clean_up_tokenization_spaces": clean_up_tokenization_spaces,
            "generate_parameters": generate_parameters,
            "truncation": truncation,
        }
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="summarization", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters=parameters,
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return SummarizationOutput.parse_obj_as_list(response)[0]

    async def table_question_answering(
        self,
        table: Dict[str, Any],
        query: str,
        *,
        model: Optional[str] = None,
        padding: Optional["Padding"] = None,
        sequential: Optional[bool] = None,
        truncation: Optional[bool] = None,
    ) -> TableQuestionAnsweringOutputElement:
        """
        Retrieve the answer to a question from information given in a table.

        Args:
            table (`str`):
                A table of data represented as a dict of lists where entries are headers and the lists are all the
                values, all lists must have the same size.
            query (`str`):
                The query in plain text that you want to ask the table.
            model (`str`):
                The model to use for the table-question-answering task. Can be a model ID hosted on the Hugging Face
                Hub or a URL to a deployed Inference Endpoint.
            padding (`"Padding"`, *optional*):
                Activates and controls padding.
            sequential (`bool`, *optional*):
                Whether to do inference sequentially or as a batch. Batching is faster, but models like SQA require the
                inference to be done sequentially to extract relations within sequences, given their conversational
                nature.
            truncation (`bool`, *optional*):
                Activates and controls truncation.

        Returns:
            [`TableQuestionAnsweringOutputElement`]: a table question answering output containing the answer, coordinates, cells and the aggregator used.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> query = "How many stars does the transformers repository have?"
        >>> table = {"Repository": ["Transformers", "Datasets", "Tokenizers"], "Stars": ["36542", "4512", "3934"]}
        >>> await client.table_question_answering(table, query, model="google/tapas-base-finetuned-wtq")
        TableQuestionAnsweringOutputElement(answer='36542', coordinates=[[0, 1]], cells=['36542'], aggregator='AVERAGE')
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="table-question-answering", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs={"query": query, "table": table},
            parameters={"model": model, "padding": padding, "sequential": sequential, "truncation": truncation},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return TableQuestionAnsweringOutputElement.parse_obj_as_instance(response)

    async def tabular_classification(self, table: Dict[str, Any], *, model: Optional[str] = None) -> List[str]:
        """
        Classifying a target category (a group) based on a set of attributes.

        Args:
            table (`Dict[str, Any]`):
                Set of attributes to classify.
            model (`str`, *optional*):
                The model to use for the tabular classification task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended tabular classification model will be used.
                Defaults to None.

        Returns:
            `List`: a list of labels, one per row in the initial table.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> table = {
        ...     "fixed_acidity": ["7.4", "7.8", "10.3"],
        ...     "volatile_acidity": ["0.7", "0.88", "0.32"],
        ...     "citric_acid": ["0", "0", "0.45"],
        ...     "residual_sugar": ["1.9", "2.6", "6.4"],
        ...     "chlorides": ["0.076", "0.098", "0.073"],
        ...     "free_sulfur_dioxide": ["11", "25", "5"],
        ...     "total_sulfur_dioxide": ["34", "67", "13"],
        ...     "density": ["0.9978", "0.9968", "0.9976"],
        ...     "pH": ["3.51", "3.2", "3.23"],
        ...     "sulphates": ["0.56", "0.68", "0.82"],
        ...     "alcohol": ["9.4", "9.8", "12.6"],
        ... }
        >>> await client.tabular_classification(table=table, model="julien-c/wine-quality")
        ["5", "5", "5"]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="tabular-classification", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=None,
            extra_payload={"table": table},
            parameters={},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return _bytes_to_list(response)

    async def tabular_regression(self, table: Dict[str, Any], *, model: Optional[str] = None) -> List[float]:
        """
        Predicting a numerical target value given a set of attributes/features in a table.

        Args:
            table (`Dict[str, Any]`):
                Set of attributes stored in a table. The attributes used to predict the target can be both numerical and categorical.
            model (`str`, *optional*):
                The model to use for the tabular regression task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended tabular regression model will be used.
                Defaults to None.

        Returns:
            `List`: a list of predicted numerical target values.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> table = {
        ...     "Height": ["11.52", "12.48", "12.3778"],
        ...     "Length1": ["23.2", "24", "23.9"],
        ...     "Length2": ["25.4", "26.3", "26.5"],
        ...     "Length3": ["30", "31.2", "31.1"],
        ...     "Species": ["Bream", "Bream", "Bream"],
        ...     "Width": ["4.02", "4.3056", "4.6961"],
        ... }
        >>> await client.tabular_regression(table, model="scikit-learn/Fish-Weight")
        [110, 120, 130]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="tabular-regression", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=None,
            parameters={},
            extra_payload={"table": table},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return _bytes_to_list(response)

    async def text_classification(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        top_k: Optional[int] = None,
        function_to_apply: Optional["TextClassificationOutputTransform"] = None,
    ) -> List[TextClassificationOutputElement]:
        """
        Perform text classification (e.g. sentiment-analysis) on the given text.

        Args:
            text (`str`):
                A string to be classified.
            model (`str`, *optional*):
                The model to use for the text classification task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended text classification model will be used.
                Defaults to None.
            top_k (`int`, *optional*):
                When specified, limits the output to the top K most probable classes.
            function_to_apply (`"TextClassificationOutputTransform"`, *optional*):
                The function to apply to the model outputs in order to retrieve the scores.

        Returns:
            `List[TextClassificationOutputElement]`: a list of [`TextClassificationOutputElement`] items containing the predicted label and associated probability.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.text_classification("I like you")
        [
            TextClassificationOutputElement(label='POSITIVE', score=0.9998695850372314),
            TextClassificationOutputElement(label='NEGATIVE', score=0.0001304351753788069),
        ]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="text-classification", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters={
                "function_to_apply": function_to_apply,
                "top_k": top_k,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return TextClassificationOutputElement.parse_obj_as_list(response)[0]  # type: ignore [return-value]

    @overload
    async def text_generation(  # type: ignore
        self,
        prompt: str,
        *,
        details: Literal[False] = ...,
        stream: Literal[False] = ...,
        model: Optional[str] = None,
        # Parameters from `TextGenerationInputGenerateParameters` (maintained manually)
        adapter_id: Optional[str] = None,
        best_of: Optional[int] = None,
        decoder_input_details: Optional[bool] = None,
        do_sample: Optional[bool] = False,  # Manual default value
        frequency_penalty: Optional[float] = None,
        grammar: Optional[TextGenerationInputGrammarType] = None,
        max_new_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        return_full_text: Optional[bool] = False,  # Manual default value
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stop_sequences: Optional[List[str]] = None,  # Deprecated, use `stop` instead
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_n_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        truncate: Optional[int] = None,
        typical_p: Optional[float] = None,
        watermark: Optional[bool] = None,
    ) -> str: ...

    @overload
    async def text_generation(  # type: ignore
        self,
        prompt: str,
        *,
        details: Literal[True] = ...,
        stream: Literal[False] = ...,
        model: Optional[str] = None,
        # Parameters from `TextGenerationInputGenerateParameters` (maintained manually)
        adapter_id: Optional[str] = None,
        best_of: Optional[int] = None,
        decoder_input_details: Optional[bool] = None,
        do_sample: Optional[bool] = False,  # Manual default value
        frequency_penalty: Optional[float] = None,
        grammar: Optional[TextGenerationInputGrammarType] = None,
        max_new_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        return_full_text: Optional[bool] = False,  # Manual default value
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stop_sequences: Optional[List[str]] = None,  # Deprecated, use `stop` instead
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_n_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        truncate: Optional[int] = None,
        typical_p: Optional[float] = None,
        watermark: Optional[bool] = None,
    ) -> TextGenerationOutput: ...

    @overload
    async def text_generation(  # type: ignore
        self,
        prompt: str,
        *,
        details: Literal[False] = ...,
        stream: Literal[True] = ...,
        model: Optional[str] = None,
        # Parameters from `TextGenerationInputGenerateParameters` (maintained manually)
        adapter_id: Optional[str] = None,
        best_of: Optional[int] = None,
        decoder_input_details: Optional[bool] = None,
        do_sample: Optional[bool] = False,  # Manual default value
        frequency_penalty: Optional[float] = None,
        grammar: Optional[TextGenerationInputGrammarType] = None,
        max_new_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        return_full_text: Optional[bool] = False,  # Manual default value
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stop_sequences: Optional[List[str]] = None,  # Deprecated, use `stop` instead
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_n_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        truncate: Optional[int] = None,
        typical_p: Optional[float] = None,
        watermark: Optional[bool] = None,
    ) -> AsyncIterable[str]: ...

    @overload
    async def text_generation(  # type: ignore
        self,
        prompt: str,
        *,
        details: Literal[True] = ...,
        stream: Literal[True] = ...,
        model: Optional[str] = None,
        # Parameters from `TextGenerationInputGenerateParameters` (maintained manually)
        adapter_id: Optional[str] = None,
        best_of: Optional[int] = None,
        decoder_input_details: Optional[bool] = None,
        do_sample: Optional[bool] = False,  # Manual default value
        frequency_penalty: Optional[float] = None,
        grammar: Optional[TextGenerationInputGrammarType] = None,
        max_new_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        return_full_text: Optional[bool] = False,  # Manual default value
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stop_sequences: Optional[List[str]] = None,  # Deprecated, use `stop` instead
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_n_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        truncate: Optional[int] = None,
        typical_p: Optional[float] = None,
        watermark: Optional[bool] = None,
    ) -> AsyncIterable[TextGenerationStreamOutput]: ...

    @overload
    async def text_generation(
        self,
        prompt: str,
        *,
        details: Literal[True] = ...,
        stream: bool = ...,
        model: Optional[str] = None,
        # Parameters from `TextGenerationInputGenerateParameters` (maintained manually)
        adapter_id: Optional[str] = None,
        best_of: Optional[int] = None,
        decoder_input_details: Optional[bool] = None,
        do_sample: Optional[bool] = False,  # Manual default value
        frequency_penalty: Optional[float] = None,
        grammar: Optional[TextGenerationInputGrammarType] = None,
        max_new_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        return_full_text: Optional[bool] = False,  # Manual default value
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stop_sequences: Optional[List[str]] = None,  # Deprecated, use `stop` instead
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_n_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        truncate: Optional[int] = None,
        typical_p: Optional[float] = None,
        watermark: Optional[bool] = None,
    ) -> Union[TextGenerationOutput, AsyncIterable[TextGenerationStreamOutput]]: ...

    async def text_generation(
        self,
        prompt: str,
        *,
        details: bool = False,
        stream: bool = False,
        model: Optional[str] = None,
        # Parameters from `TextGenerationInputGenerateParameters` (maintained manually)
        adapter_id: Optional[str] = None,
        best_of: Optional[int] = None,
        decoder_input_details: Optional[bool] = None,
        do_sample: Optional[bool] = False,  # Manual default value
        frequency_penalty: Optional[float] = None,
        grammar: Optional[TextGenerationInputGrammarType] = None,
        max_new_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        return_full_text: Optional[bool] = False,  # Manual default value
        seed: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stop_sequences: Optional[List[str]] = None,  # Deprecated, use `stop` instead
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_n_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        truncate: Optional[int] = None,
        typical_p: Optional[float] = None,
        watermark: Optional[bool] = None,
    ) -> Union[str, TextGenerationOutput, AsyncIterable[str], AsyncIterable[TextGenerationStreamOutput]]:
        """
        Given a prompt, generate the following text.

        <Tip>

        If you want to generate a response from chat messages, you should use the [`InferenceClient.chat_completion`] method.
        It accepts a list of messages instead of a single text prompt and handles the chat templating for you.

        </Tip>

        Args:
            prompt (`str`):
                Input text.
            details (`bool`, *optional*):
                By default, text_generation returns a string. Pass `details=True` if you want a detailed output (tokens,
                probabilities, seed, finish reason, etc.). Only available for models running on with the
                `text-generation-inference` backend.
            stream (`bool`, *optional*):
                By default, text_generation returns the full generated text. Pass `stream=True` if you want a stream of
                tokens to be returned. Only available for models running on with the `text-generation-inference`
                backend.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. This parameter overrides the model defined at the instance level. Defaults to None.
            adapter_id (`str`, *optional*):
                Lora adapter id.
            best_of (`int`, *optional*):
                Generate best_of sequences and return the one if the highest token logprobs.
            decoder_input_details (`bool`, *optional*):
                Return the decoder input token logprobs and ids. You must set `details=True` as well for it to be taken
                into account. Defaults to `False`.
            do_sample (`bool`, *optional*):
                Activate logits sampling
            frequency_penalty (`float`, *optional*):
                Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in
                the text so far, decreasing the model's likelihood to repeat the same line verbatim.
            grammar ([`TextGenerationInputGrammarType`], *optional*):
                Grammar constraints. Can be either a JSONSchema or a regex.
            max_new_tokens (`int`, *optional*):
                Maximum number of generated tokens. Defaults to 100.
            repetition_penalty (`float`, *optional*):
                The parameter for repetition penalty. 1.0 means no penalty. See [this
                paper](https://arxiv.org/pdf/1909.05858.pdf) for more details.
            return_full_text (`bool`, *optional*):
                Whether to prepend the prompt to the generated text
            seed (`int`, *optional*):
                Random sampling seed
            stop (`List[str]`, *optional*):
                Stop generating tokens if a member of `stop` is generated.
            stop_sequences (`List[str]`, *optional*):
                Deprecated argument. Use `stop` instead.
            temperature (`float`, *optional*):
                The value used to module the logits distribution.
            top_n_tokens (`int`, *optional*):
                Return information about the `top_n_tokens` most likely tokens at each generation step, instead of
                just the sampled token.
            top_k (`int`, *optional`):
                The number of highest probability vocabulary tokens to keep for top-k-filtering.
            top_p (`float`, *optional`):
                If set to < 1, only the smallest set of most probable tokens with probabilities that add up to `top_p` or
                higher are kept for generation.
            truncate (`int`, *optional`):
                Truncate inputs tokens to the given size.
            typical_p (`float`, *optional`):
                Typical Decoding mass
                See [Typical Decoding for Natural Language Generation](https://arxiv.org/abs/2202.00666) for more information
            watermark (`bool`, *optional`):
                Watermarking with [A Watermark for Large Language Models](https://arxiv.org/abs/2301.10226)

        Returns:
            `Union[str, TextGenerationOutput, Iterable[str], Iterable[TextGenerationStreamOutput]]`:
            Generated text returned from the server:
            - if `stream=False` and `details=False`, the generated text is returned as a `str` (default)
            - if `stream=True` and `details=False`, the generated text is returned token by token as a `Iterable[str]`
            - if `stream=False` and `details=True`, the generated text is returned with more details as a [`~huggingface_hub.TextGenerationOutput`]
            - if `details=True` and `stream=True`, the generated text is returned token by token as a iterable of [`~huggingface_hub.TextGenerationStreamOutput`]

        Raises:
            `ValidationError`:
                If input values are not valid. No HTTP call is made to the server.
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()

        # Case 1: generate text
        >>> await client.text_generation("The huggingface_hub library is ", max_new_tokens=12)
        '100% open source and built to be easy to use.'

        # Case 2: iterate over the generated tokens. Useful for large generation.
        >>> async for token in await client.text_generation("The huggingface_hub library is ", max_new_tokens=12, stream=True):
        ...     print(token)
        100
        %
        open
        source
        and
        built
        to
        be
        easy
        to
        use
        .

        # Case 3: get more details about the generation process.
        >>> await client.text_generation("The huggingface_hub library is ", max_new_tokens=12, details=True)
        TextGenerationOutput(
            generated_text='100% open source and built to be easy to use.',
            details=TextGenerationDetails(
                finish_reason='length',
                generated_tokens=12,
                seed=None,
                prefill=[
                    TextGenerationPrefillOutputToken(id=487, text='The', logprob=None),
                    TextGenerationPrefillOutputToken(id=53789, text=' hugging', logprob=-13.171875),
                    (...)
                    TextGenerationPrefillOutputToken(id=204, text=' ', logprob=-7.0390625)
                ],
                tokens=[
                    TokenElement(id=1425, text='100', logprob=-1.0175781, special=False),
                    TokenElement(id=16, text='%', logprob=-0.0463562, special=False),
                    (...)
                    TokenElement(id=25, text='.', logprob=-0.5703125, special=False)
                ],
                best_of_sequences=None
            )
        )

        # Case 4: iterate over the generated tokens with more details.
        # Last object is more complete, containing the full generated text and the finish reason.
        >>> async for details in await client.text_generation("The huggingface_hub library is ", max_new_tokens=12, details=True, stream=True):
        ...     print(details)
        ...
        TextGenerationStreamOutput(token=TokenElement(id=1425, text='100', logprob=-1.0175781, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=16, text='%', logprob=-0.0463562, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=1314, text=' open', logprob=-1.3359375, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=3178, text=' source', logprob=-0.28100586, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=273, text=' and', logprob=-0.5961914, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=3426, text=' built', logprob=-1.9423828, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=271, text=' to', logprob=-1.4121094, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=314, text=' be', logprob=-1.5224609, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=1833, text=' easy', logprob=-2.1132812, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=271, text=' to', logprob=-0.08520508, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(id=745, text=' use', logprob=-0.39453125, special=False), generated_text=None, details=None)
        TextGenerationStreamOutput(token=TokenElement(
            id=25,
            text='.',
            logprob=-0.5703125,
            special=False),
            generated_text='100% open source and built to be easy to use.',
            details=TextGenerationStreamOutputStreamDetails(finish_reason='length', generated_tokens=12, seed=None)
        )

        # Case 5: generate constrained output using grammar
        >>> response = await client.text_generation(
        ...     prompt="I saw a puppy a cat and a raccoon during my bike ride in the park",
        ...     model="HuggingFaceH4/zephyr-orpo-141b-A35b-v0.1",
        ...     max_new_tokens=100,
        ...     repetition_penalty=1.3,
        ...     grammar={
        ...         "type": "json",
        ...         "value": {
        ...             "properties": {
        ...                 "location": {"type": "string"},
        ...                 "activity": {"type": "string"},
        ...                 "animals_seen": {"type": "integer", "minimum": 1, "maximum": 5},
        ...                 "animals": {"type": "array", "items": {"type": "string"}},
        ...             },
        ...             "required": ["location", "activity", "animals_seen", "animals"],
        ...         },
        ...     },
        ... )
        >>> json.loads(response)
        {
            "activity": "bike riding",
            "animals": ["puppy", "cat", "raccoon"],
            "animals_seen": 3,
            "location": "park"
        }
        ```
        """
        if decoder_input_details and not details:
            warnings.warn(
                "`decoder_input_details=True` has been passed to the server but `details=False` is set meaning that"
                " the output from the server will be truncated."
            )
            decoder_input_details = False

        if stop_sequences is not None:
            warnings.warn(
                "`stop_sequences` is a deprecated argument for `text_generation` task"
                " and will be removed in version '0.28.0'. Use `stop` instead.",
                FutureWarning,
            )
        if stop is None:
            stop = stop_sequences  # use deprecated arg if provided

        # Build payload
        parameters = {
            "adapter_id": adapter_id,
            "best_of": best_of,
            "decoder_input_details": decoder_input_details,
            "details": details,
            "do_sample": do_sample,
            "frequency_penalty": frequency_penalty,
            "grammar": grammar,
            "max_new_tokens": max_new_tokens,
            "repetition_penalty": repetition_penalty,
            "return_full_text": return_full_text,
            "seed": seed,
            "stop": stop if stop is not None else [],
            "temperature": temperature,
            "top_k": top_k,
            "top_n_tokens": top_n_tokens,
            "top_p": top_p,
            "truncate": truncate,
            "typical_p": typical_p,
            "watermark": watermark,
        }

        # Remove some parameters if not a TGI server
        unsupported_kwargs = _get_unsupported_text_generation_kwargs(model)
        if len(unsupported_kwargs) > 0:
            # The server does not support some parameters
            # => means it is not a TGI server
            # => remove unsupported parameters and warn the user

            ignored_parameters = []
            for key in unsupported_kwargs:
                if parameters.get(key):
                    ignored_parameters.append(key)
                parameters.pop(key, None)
            if len(ignored_parameters) > 0:
                warnings.warn(
                    "API endpoint/model for text-generation is not served via TGI. Ignoring following parameters:"
                    f" {', '.join(ignored_parameters)}.",
                    UserWarning,
                )
            if details:
                warnings.warn(
                    "API endpoint/model for text-generation is not served via TGI. Parameter `details=True` will"
                    " be ignored meaning only the generated text will be returned.",
                    UserWarning,
                )
                details = False
            if stream:
                raise ValueError(
                    "API endpoint/model for text-generation is not served via TGI. Cannot return output as a stream."
                    " Please pass `stream=False` as input."
                )

        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="text-generation", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=prompt,
            parameters=parameters,
            extra_payload={"stream": stream},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )

        # Handle errors separately for more precise error messages
        try:
            bytes_output = await self._inner_post(request_parameters, stream=stream)
        except _import_aiohttp().ClientResponseError as e:
            match = MODEL_KWARGS_NOT_USED_REGEX.search(e.response_error_payload["error"])
            if e.status == 400 and match:
                unused_params = [kwarg.strip("' ") for kwarg in match.group(1).split(",")]
                _set_unsupported_text_generation_kwargs(model, unused_params)
                return await self.text_generation(  # type: ignore
                    prompt=prompt,
                    details=details,
                    stream=stream,
                    model=model_id,
                    adapter_id=adapter_id,
                    best_of=best_of,
                    decoder_input_details=decoder_input_details,
                    do_sample=do_sample,
                    frequency_penalty=frequency_penalty,
                    grammar=grammar,
                    max_new_tokens=max_new_tokens,
                    repetition_penalty=repetition_penalty,
                    return_full_text=return_full_text,
                    seed=seed,
                    stop=stop,
                    temperature=temperature,
                    top_k=top_k,
                    top_n_tokens=top_n_tokens,
                    top_p=top_p,
                    truncate=truncate,
                    typical_p=typical_p,
                    watermark=watermark,
                )
            raise_text_generation_error(e)

        # Parse output
        if stream:
            return _async_stream_text_generation_response(bytes_output, details)  # type: ignore

        data = _bytes_to_dict(bytes_output)  # type: ignore[arg-type]

        # Data can be a single element (dict) or an iterable of dicts where we select the first element of.
        if isinstance(data, list):
            data = data[0]
        response = provider_helper.get_response(data, request_parameters)
        return TextGenerationOutput.parse_obj_as_instance(response) if details else response["generated_text"]

    async def text_to_image(
        self,
        prompt: str,
        *,
        negative_prompt: Optional[str] = None,
        height: Optional[int] = None,
        width: Optional[int] = None,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        model: Optional[str] = None,
        scheduler: Optional[str] = None,
        seed: Optional[int] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> "Image":
        """
        Generate an image based on a given text using a specified model.

        <Tip warning={true}>

        You must have `PIL` installed if you want to work with images (`pip install Pillow`).

        </Tip>

        <Tip>
        You can pass provider-specific parameters to the model by using the `extra_body` argument.
        </Tip>

        Args:
            prompt (`str`):
                The prompt to generate an image from.
            negative_prompt (`str`, *optional*):
                One prompt to guide what NOT to include in image generation.
            height (`int`, *optional*):
                The height in pixels of the output image
            width (`int`, *optional*):
                The width in pixels of the output image
            num_inference_steps (`int`, *optional*):
                The number of denoising steps. More denoising steps usually lead to a higher quality image at the
                expense of slower inference.
            guidance_scale (`float`, *optional*):
                A higher guidance scale value encourages the model to generate images closely linked to the text
                prompt, but values too high may cause saturation and other artifacts.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. If not provided, the default recommended text-to-image model will be used.
                Defaults to None.
            scheduler (`str`, *optional*):
                Override the scheduler with a compatible one.
            seed (`int`, *optional*):
                Seed for the random number generator.
            extra_body (`Dict[str, Any]`, *optional*):
                Additional provider-specific parameters to pass to the model. Refer to the provider's documentation
                for supported parameters.

        Returns:
            `Image`: The generated image.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()

        >>> image = await client.text_to_image("An astronaut riding a horse on the moon.")
        >>> image.save("astronaut.png")

        >>> image = await client.text_to_image(
        ...     "An astronaut riding a horse on the moon.",
        ...     negative_prompt="low resolution, blurry",
        ...     model="stabilityai/stable-diffusion-2-1",
        ... )
        >>> image.save("better_astronaut.png")
        ```
        Example using a third-party provider directly. Usage will be billed on your fal.ai account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="fal-ai",  # Use fal.ai provider
        ...     api_key="fal-ai-api-key",  # Pass your fal.ai API key
        ... )
        >>> image = client.text_to_image(
        ...     "A majestic lion in a fantasy forest",
        ...     model="black-forest-labs/FLUX.1-schnell",
        ... )
        >>> image.save("lion.png")
        ```

        Example using a third-party provider through Hugging Face Routing. Usage will be billed on your Hugging Face account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="replicate",  # Use replicate provider
        ...     api_key="hf_...",  # Pass your HF token
        ... )
        >>> image = client.text_to_image(
        ...     "An astronaut riding a horse on the moon.",
        ...     model="black-forest-labs/FLUX.1-dev",
        ... )
        >>> image.save("astronaut.png")
        ```

        Example using Replicate provider with extra parameters
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="replicate",  # Use replicate provider
        ...     api_key="hf_...",  # Pass your HF token
        ... )
        >>> image = client.text_to_image(
        ...     "An astronaut riding a horse on the moon.",
        ...     model="black-forest-labs/FLUX.1-schnell",
        ...     extra_body={"output_quality": 100},
        ... )
        >>> image.save("astronaut.png")
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="text-to-image", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=prompt,
            parameters={
                "negative_prompt": negative_prompt,
                "height": height,
                "width": width,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "scheduler": scheduler,
                "seed": seed,
                **(extra_body or {}),
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        response = provider_helper.get_response(response)
        return _bytes_to_image(response)

    async def text_to_video(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        guidance_scale: Optional[float] = None,
        negative_prompt: Optional[List[str]] = None,
        num_frames: Optional[float] = None,
        num_inference_steps: Optional[int] = None,
        seed: Optional[int] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """
        Generate a video based on a given text.

        <Tip>
        You can pass provider-specific parameters to the model by using the `extra_body` argument.
        </Tip>

        Args:
            prompt (`str`):
                The prompt to generate a video from.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. If not provided, the default recommended text-to-video model will be used.
                Defaults to None.
            guidance_scale (`float`, *optional*):
                A higher guidance scale value encourages the model to generate videos closely linked to the text
                prompt, but values too high may cause saturation and other artifacts.
            negative_prompt (`List[str]`, *optional*):
                One or several prompt to guide what NOT to include in video generation.
            num_frames (`float`, *optional*):
                The num_frames parameter determines how many video frames are generated.
            num_inference_steps (`int`, *optional*):
                The number of denoising steps. More denoising steps usually lead to a higher quality video at the
                expense of slower inference.
            seed (`int`, *optional*):
                Seed for the random number generator.
            extra_body (`Dict[str, Any]`, *optional*):
                Additional provider-specific parameters to pass to the model. Refer to the provider's documentation
                for supported parameters.

        Returns:
            `bytes`: The generated video.

        Example:

        Example using a third-party provider directly. Usage will be billed on your fal.ai account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="fal-ai",  # Using fal.ai provider
        ...     api_key="fal-ai-api-key",  # Pass your fal.ai API key
        ... )
        >>> video = client.text_to_video(
        ...     "A majestic lion running in a fantasy forest",
        ...     model="tencent/HunyuanVideo",
        ... )
        >>> with open("lion.mp4", "wb") as file:
        ...     file.write(video)
        ```

        Example using a third-party provider through Hugging Face Routing. Usage will be billed on your Hugging Face account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="replicate",  # Using replicate provider
        ...     api_key="hf_...",  # Pass your HF token
        ... )
        >>> video = client.text_to_video(
        ...     "A cat running in a park",
        ...     model="genmo/mochi-1-preview",
        ... )
        >>> with open("cat.mp4", "wb") as file:
        ...     file.write(video)
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="text-to-video", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=prompt,
            parameters={
                "guidance_scale": guidance_scale,
                "negative_prompt": negative_prompt,
                "num_frames": num_frames,
                "num_inference_steps": num_inference_steps,
                "seed": seed,
                **(extra_body or {}),
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        response = provider_helper.get_response(response, request_parameters)
        return response

    async def text_to_speech(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        do_sample: Optional[bool] = None,
        early_stopping: Optional[Union[bool, "TextToSpeechEarlyStoppingEnum"]] = None,
        epsilon_cutoff: Optional[float] = None,
        eta_cutoff: Optional[float] = None,
        max_length: Optional[int] = None,
        max_new_tokens: Optional[int] = None,
        min_length: Optional[int] = None,
        min_new_tokens: Optional[int] = None,
        num_beam_groups: Optional[int] = None,
        num_beams: Optional[int] = None,
        penalty_alpha: Optional[float] = None,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        typical_p: Optional[float] = None,
        use_cache: Optional[bool] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """
        Synthesize an audio of a voice pronouncing a given text.

        <Tip>
        You can pass provider-specific parameters to the model by using the `extra_body` argument.
        </Tip>

        Args:
            text (`str`):
                The text to synthesize.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. If not provided, the default recommended text-to-speech model will be used.
                Defaults to None.
            do_sample (`bool`, *optional*):
                Whether to use sampling instead of greedy decoding when generating new tokens.
            early_stopping (`Union[bool, "TextToSpeechEarlyStoppingEnum"]`, *optional*):
                Controls the stopping condition for beam-based methods.
            epsilon_cutoff (`float`, *optional*):
                If set to float strictly between 0 and 1, only tokens with a conditional probability greater than
                epsilon_cutoff will be sampled. In the paper, suggested values range from 3e-4 to 9e-4, depending on
                the size of the model. See [Truncation Sampling as Language Model
                Desmoothing](https://hf.co/papers/2210.15191) for more details.
            eta_cutoff (`float`, *optional*):
                Eta sampling is a hybrid of locally typical sampling and epsilon sampling. If set to float strictly
                between 0 and 1, a token is only considered if it is greater than either eta_cutoff or sqrt(eta_cutoff)
                * exp(-entropy(softmax(next_token_logits))). The latter term is intuitively the expected next token
                probability, scaled by sqrt(eta_cutoff). In the paper, suggested values range from 3e-4 to 2e-3,
                depending on the size of the model. See [Truncation Sampling as Language Model
                Desmoothing](https://hf.co/papers/2210.15191) for more details.
            max_length (`int`, *optional*):
                The maximum length (in tokens) of the generated text, including the input.
            max_new_tokens (`int`, *optional*):
                The maximum number of tokens to generate. Takes precedence over max_length.
            min_length (`int`, *optional*):
                The minimum length (in tokens) of the generated text, including the input.
            min_new_tokens (`int`, *optional*):
                The minimum number of tokens to generate. Takes precedence over min_length.
            num_beam_groups (`int`, *optional*):
                Number of groups to divide num_beams into in order to ensure diversity among different groups of beams.
                See [this paper](https://hf.co/papers/1610.02424) for more details.
            num_beams (`int`, *optional*):
                Number of beams to use for beam search.
            penalty_alpha (`float`, *optional*):
                The value balances the model confidence and the degeneration penalty in contrastive search decoding.
            temperature (`float`, *optional*):
                The value used to modulate the next token probabilities.
            top_k (`int`, *optional*):
                The number of highest probability vocabulary tokens to keep for top-k-filtering.
            top_p (`float`, *optional*):
                If set to float < 1, only the smallest set of most probable tokens with probabilities that add up to
                top_p or higher are kept for generation.
            typical_p (`float`, *optional*):
                Local typicality measures how similar the conditional probability of predicting a target token next is
                to the expected conditional probability of predicting a random token next, given the partial text
                already generated. If set to float < 1, the smallest set of the most locally typical tokens with
                probabilities that add up to typical_p or higher are kept for generation. See [this
                paper](https://hf.co/papers/2202.00666) for more details.
            use_cache (`bool`, *optional*):
                Whether the model should use the past last key/values attentions to speed up decoding
            extra_body (`Dict[str, Any]`, *optional*):
                Additional provider-specific parameters to pass to the model. Refer to the provider's documentation
                for supported parameters.
        Returns:
            `bytes`: The generated audio.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from pathlib import Path
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()

        >>> audio = await client.text_to_speech("Hello world")
        >>> Path("hello_world.flac").write_bytes(audio)
        ```

        Example using a third-party provider directly. Usage will be billed on your Replicate account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="replicate",
        ...     api_key="your-replicate-api-key",  # Pass your Replicate API key directly
        ... )
        >>> audio = client.text_to_speech(
        ...     text="Hello world",
        ...     model="OuteAI/OuteTTS-0.3-500M",
        ... )
        >>> Path("hello_world.flac").write_bytes(audio)
        ```

        Example using a third-party provider through Hugging Face Routing. Usage will be billed on your Hugging Face account.
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="replicate",
        ...     api_key="hf_...",  # Pass your HF token
        ... )
        >>> audio =client.text_to_speech(
        ...     text="Hello world",
        ...     model="OuteAI/OuteTTS-0.3-500M",
        ... )
        >>> Path("hello_world.flac").write_bytes(audio)
        ```
        Example using Replicate provider with extra parameters
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> client = InferenceClient(
        ...     provider="replicate",  # Use replicate provider
        ...     api_key="hf_...",  # Pass your HF token
        ... )
        >>> audio = client.text_to_speech(
        ...     "Hello, my name is Kororo, an awesome text-to-speech model.",
        ...     model="hexgrad/Kokoro-82M",
        ...     extra_body={"voice": "af_nicole"},
        ... )
        >>> Path("hello.flac").write_bytes(audio)
        ```

        Example music-gen using "YuE-s1-7B-anneal-en-cot" on fal.ai
        ```py
        >>> from huggingface_hub import InferenceClient
        >>> lyrics = '''
        ... [verse]
        ... In the town where I was born
        ... Lived a man who sailed to sea
        ... And he told us of his life
        ... In the land of submarines
        ... So we sailed on to the sun
        ... 'Til we found a sea of green
        ... And we lived beneath the waves
        ... In our yellow submarine

        ... [chorus]
        ... We all live in a yellow submarine
        ... Yellow submarine, yellow submarine
        ... We all live in a yellow submarine
        ... Yellow submarine, yellow submarine
        ... '''
        >>> genres = "pavarotti-style tenor voice"
        >>> client = InferenceClient(
        ...     provider="fal-ai",
        ...     model="m-a-p/YuE-s1-7B-anneal-en-cot",
        ...     api_key=...,
        ... )
        >>> audio = client.text_to_speech(lyrics, extra_body={"genres": genres})
        >>> with open("output.mp3", "wb") as f:
        ...     f.write(audio)
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="text-to-speech", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters={
                "do_sample": do_sample,
                "early_stopping": early_stopping,
                "epsilon_cutoff": epsilon_cutoff,
                "eta_cutoff": eta_cutoff,
                "max_length": max_length,
                "max_new_tokens": max_new_tokens,
                "min_length": min_length,
                "min_new_tokens": min_new_tokens,
                "num_beam_groups": num_beam_groups,
                "num_beams": num_beams,
                "penalty_alpha": penalty_alpha,
                "temperature": temperature,
                "top_k": top_k,
                "top_p": top_p,
                "typical_p": typical_p,
                "use_cache": use_cache,
                **(extra_body or {}),
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        response = provider_helper.get_response(response)
        return response

    async def token_classification(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        aggregation_strategy: Optional["TokenClassificationAggregationStrategy"] = None,
        ignore_labels: Optional[List[str]] = None,
        stride: Optional[int] = None,
    ) -> List[TokenClassificationOutputElement]:
        """
        Perform token classification on the given text.
        Usually used for sentence parsing, either grammatical, or Named Entity Recognition (NER) to understand keywords contained within text.

        Args:
            text (`str`):
                A string to be classified.
            model (`str`, *optional*):
                The model to use for the token classification task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended token classification model will be used.
                Defaults to None.
            aggregation_strategy (`"TokenClassificationAggregationStrategy"`, *optional*):
                The strategy used to fuse tokens based on model predictions
            ignore_labels (`List[str`, *optional*):
                A list of labels to ignore
            stride (`int`, *optional*):
                The number of overlapping tokens between chunks when splitting the input text.

        Returns:
            `List[TokenClassificationOutputElement]`: List of [`TokenClassificationOutputElement`] items containing the entity group, confidence score, word, start and end index.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.token_classification("My name is Sarah Jessica Parker but you can call me Jessica")
        [
            TokenClassificationOutputElement(
                entity_group='PER',
                score=0.9971321225166321,
                word='Sarah Jessica Parker',
                start=11,
                end=31,
            ),
            TokenClassificationOutputElement(
                entity_group='PER',
                score=0.9773476123809814,
                word='Jessica',
                start=52,
                end=59,
            )
        ]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="token-classification", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters={
                "aggregation_strategy": aggregation_strategy,
                "ignore_labels": ignore_labels,
                "stride": stride,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return TokenClassificationOutputElement.parse_obj_as_list(response)

    async def translation(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        src_lang: Optional[str] = None,
        tgt_lang: Optional[str] = None,
        clean_up_tokenization_spaces: Optional[bool] = None,
        truncation: Optional["TranslationTruncationStrategy"] = None,
        generate_parameters: Optional[Dict[str, Any]] = None,
    ) -> TranslationOutput:
        """
        Convert text from one language to another.

        Check out https://huggingface.co/tasks/translation for more information on how to choose the best model for
        your specific use case. Source and target languages usually depend on the model.
        However, it is possible to specify source and target languages for certain models. If you are working with one of these models,
        you can use `src_lang` and `tgt_lang` arguments to pass the relevant information.

        Args:
            text (`str`):
                A string to be translated.
            model (`str`, *optional*):
                The model to use for the translation task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended translation model will be used.
                Defaults to None.
            src_lang (`str`, *optional*):
                The source language of the text. Required for models that can translate from multiple languages.
            tgt_lang (`str`, *optional*):
                Target language to translate to. Required for models that can translate to multiple languages.
            clean_up_tokenization_spaces (`bool`, *optional*):
                Whether to clean up the potential extra spaces in the text output.
            truncation (`"TranslationTruncationStrategy"`, *optional*):
                The truncation strategy to use.
            generate_parameters (`Dict[str, Any]`, *optional*):
                Additional parametrization of the text generation algorithm.

        Returns:
            [`TranslationOutput`]: The generated translated text.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.
            `ValueError`:
                If only one of the `src_lang` and `tgt_lang` arguments are provided.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.translation("My name is Wolfgang and I live in Berlin")
        'Mein Name ist Wolfgang und ich lebe in Berlin.'
        >>> await client.translation("My name is Wolfgang and I live in Berlin", model="Helsinki-NLP/opus-mt-en-fr")
        TranslationOutput(translation_text='Je m'appelle Wolfgang et je vis à Berlin.')
        ```

        Specifying languages:
        ```py
        >>> client.translation("My name is Sarah Jessica Parker but you can call me Jessica", model="facebook/mbart-large-50-many-to-many-mmt", src_lang="en_XX", tgt_lang="fr_XX")
        "Mon nom est Sarah Jessica Parker mais vous pouvez m'appeler Jessica"
        ```
        """
        # Throw error if only one of `src_lang` and `tgt_lang` was given
        if src_lang is not None and tgt_lang is None:
            raise ValueError("You cannot specify `src_lang` without specifying `tgt_lang`.")

        if src_lang is None and tgt_lang is not None:
            raise ValueError("You cannot specify `tgt_lang` without specifying `src_lang`.")

        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="translation", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters={
                "src_lang": src_lang,
                "tgt_lang": tgt_lang,
                "clean_up_tokenization_spaces": clean_up_tokenization_spaces,
                "truncation": truncation,
                "generate_parameters": generate_parameters,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return TranslationOutput.parse_obj_as_list(response)[0]

    async def visual_question_answering(
        self,
        image: ContentT,
        question: str,
        *,
        model: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[VisualQuestionAnsweringOutputElement]:
        """
        Answering open-ended questions based on an image.

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The input image for the context. It can be raw bytes, an image file, or a URL to an online image.
            question (`str`):
                Question to be answered.
            model (`str`, *optional*):
                The model to use for the visual question answering task. Can be a model ID hosted on the Hugging Face Hub or a URL to
                a deployed Inference Endpoint. If not provided, the default recommended visual question answering model will be used.
                Defaults to None.
            top_k (`int`, *optional*):
                The number of answers to return (will be chosen by order of likelihood). Note that we return less than
                topk answers if there are not enough options available within the context.
        Returns:
            `List[VisualQuestionAnsweringOutputElement]`: a list of [`VisualQuestionAnsweringOutputElement`] items containing the predicted label and associated probability.

        Raises:
            `InferenceTimeoutError`:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.visual_question_answering(
        ...     image="https://huggingface.co/datasets/mishig/sample_images/resolve/main/tiger.jpg",
        ...     question="What is the animal doing?"
        ... )
        [
            VisualQuestionAnsweringOutputElement(score=0.778609573841095, answer='laying down'),
            VisualQuestionAnsweringOutputElement(score=0.6957435607910156, answer='sitting'),
        ]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="visual-question-answering", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=image,
            parameters={"top_k": top_k},
            headers=self.headers,
            model=model_id,
            api_key=self.token,
            extra_payload={"question": question, "image": _b64_encode(image)},
        )
        response = await self._inner_post(request_parameters)
        return VisualQuestionAnsweringOutputElement.parse_obj_as_list(response)

    async def zero_shot_classification(
        self,
        text: str,
        candidate_labels: List[str],
        *,
        multi_label: Optional[bool] = False,
        hypothesis_template: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[ZeroShotClassificationOutputElement]:
        """
        Provide as input a text and a set of candidate labels to classify the input text.

        Args:
            text (`str`):
                The input text to classify.
            candidate_labels (`List[str]`):
                The set of possible class labels to classify the text into.
            labels (`List[str]`, *optional*):
                (deprecated) List of strings. Each string is the verbalization of a possible label for the input text.
            multi_label (`bool`, *optional*):
                Whether multiple candidate labels can be true. If false, the scores are normalized such that the sum of
                the label likelihoods for each sequence is 1. If true, the labels are considered independent and
                probabilities are normalized for each candidate.
            hypothesis_template (`str`, *optional*):
                The sentence used in conjunction with `candidate_labels` to attempt the text classification by
                replacing the placeholder with the candidate labels.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. This parameter overrides the model defined at the instance level. If not provided, the default recommended zero-shot classification model will be used.


        Returns:
            `List[ZeroShotClassificationOutputElement]`: List of [`ZeroShotClassificationOutputElement`] items containing the predicted labels and their confidence.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example with `multi_label=False`:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> text = (
        ...     "A new model offers an explanation for how the Galilean satellites formed around the solar system's"
        ...     "largest world. Konstantin Batygin did not set out to solve one of the solar system's most puzzling"
        ...     " mysteries when he went for a run up a hill in Nice, France."
        ... )
        >>> labels = ["space & cosmos", "scientific discovery", "microbiology", "robots", "archeology"]
        >>> await client.zero_shot_classification(text, labels)
        [
            ZeroShotClassificationOutputElement(label='scientific discovery', score=0.7961668968200684),
            ZeroShotClassificationOutputElement(label='space & cosmos', score=0.18570658564567566),
            ZeroShotClassificationOutputElement(label='microbiology', score=0.00730885099619627),
            ZeroShotClassificationOutputElement(label='archeology', score=0.006258360575884581),
            ZeroShotClassificationOutputElement(label='robots', score=0.004559356719255447),
        ]
        >>> await client.zero_shot_classification(text, labels, multi_label=True)
        [
            ZeroShotClassificationOutputElement(label='scientific discovery', score=0.9829297661781311),
            ZeroShotClassificationOutputElement(label='space & cosmos', score=0.755190908908844),
            ZeroShotClassificationOutputElement(label='microbiology', score=0.0005462635890580714),
            ZeroShotClassificationOutputElement(label='archeology', score=0.00047131875180639327),
            ZeroShotClassificationOutputElement(label='robots', score=0.00030448526376858354),
        ]
        ```

        Example with `multi_label=True` and a custom `hypothesis_template`:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.zero_shot_classification(
        ...    text="I really like our dinner and I'm very happy. I don't like the weather though.",
        ...    labels=["positive", "negative", "pessimistic", "optimistic"],
        ...    multi_label=True,
        ...    hypothesis_template="This text is {} towards the weather"
        ... )
        [
            ZeroShotClassificationOutputElement(label='negative', score=0.9231801629066467),
            ZeroShotClassificationOutputElement(label='pessimistic', score=0.8760990500450134),
            ZeroShotClassificationOutputElement(label='optimistic', score=0.0008674879791215062),
            ZeroShotClassificationOutputElement(label='positive', score=0.0005250611575320363)
        ]
        ```
        """
        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="zero-shot-classification", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=text,
            parameters={
                "candidate_labels": candidate_labels,
                "multi_label": multi_label,
                "hypothesis_template": hypothesis_template,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        output = _bytes_to_dict(response)
        return [
            ZeroShotClassificationOutputElement.parse_obj_as_instance({"label": label, "score": score})
            for label, score in zip(output["labels"], output["scores"])
        ]

    async def zero_shot_image_classification(
        self,
        image: ContentT,
        candidate_labels: List[str],
        *,
        model: Optional[str] = None,
        hypothesis_template: Optional[str] = None,
        # deprecated argument
        labels: List[str] = None,  # type: ignore
    ) -> List[ZeroShotImageClassificationOutputElement]:
        """
        Provide input image and text labels to predict text labels for the image.

        Args:
            image (`Union[str, Path, bytes, BinaryIO]`):
                The input image to caption. It can be raw bytes, an image file, or a URL to an online image.
            candidate_labels (`List[str]`):
                The candidate labels for this image
            labels (`List[str]`, *optional*):
                (deprecated) List of string possible labels. There must be at least 2 labels.
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. This parameter overrides the model defined at the instance level. If not provided, the default recommended zero-shot image classification model will be used.
            hypothesis_template (`str`, *optional*):
                The sentence used in conjunction with `candidate_labels` to attempt the image classification by
                replacing the placeholder with the candidate labels.

        Returns:
            `List[ZeroShotImageClassificationOutputElement]`: List of [`ZeroShotImageClassificationOutputElement`] items containing the predicted labels and their confidence.

        Raises:
            [`InferenceTimeoutError`]:
                If the model is unavailable or the request times out.
            `aiohttp.ClientResponseError`:
                If the request fails with an HTTP error status code other than HTTP 503.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()

        >>> await client.zero_shot_image_classification(
        ...     "https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Cute_dog.jpg/320px-Cute_dog.jpg",
        ...     labels=["dog", "cat", "horse"],
        ... )
        [ZeroShotImageClassificationOutputElement(label='dog', score=0.956),...]
        ```
        """
        # Raise ValueError if input is less than 2 labels
        if len(candidate_labels) < 2:
            raise ValueError("You must specify at least 2 classes to compare.")

        model_id = model or self.model
        provider_helper = get_provider_helper(self.provider, task="zero-shot-image-classification", model=model_id)
        request_parameters = provider_helper.prepare_request(
            inputs=image,
            parameters={
                "candidate_labels": candidate_labels,
                "hypothesis_template": hypothesis_template,
            },
            headers=self.headers,
            model=model_id,
            api_key=self.token,
        )
        response = await self._inner_post(request_parameters)
        return ZeroShotImageClassificationOutputElement.parse_obj_as_list(response)

    @_deprecate_method(
        version="0.35.0",
        message=(
            "HF Inference API is getting revamped and will only support warm models in the future (no cold start allowed)."
            " Use `HfApi.list_models(..., inference_provider='...')` to list warm models per provider."
        ),
    )
    async def list_deployed_models(
        self, frameworks: Union[None, str, Literal["all"], List[str]] = None
    ) -> Dict[str, List[str]]:
        """
        List models deployed on the HF Serverless Inference API service.

        This helper checks deployed models framework by framework. By default, it will check the 4 main frameworks that
        are supported and account for 95% of the hosted models. However, if you want a complete list of models you can
        specify `frameworks="all"` as input. Alternatively, if you know before-hand which framework you are interested
        in, you can also restrict to search to this one (e.g. `frameworks="text-generation-inference"`). The more
        frameworks are checked, the more time it will take.

        <Tip warning={true}>

        This endpoint method does not return a live list of all models available for the HF Inference API service.
        It searches over a cached list of models that were recently available and the list may not be up to date.
        If you want to know the live status of a specific model, use [`~InferenceClient.get_model_status`].

        </Tip>

        <Tip>

        This endpoint method is mostly useful for discoverability. If you already know which model you want to use and want to
        check its availability, you can directly use [`~InferenceClient.get_model_status`].

        </Tip>

        Args:
            frameworks (`Literal["all"]` or `List[str]` or `str`, *optional*):
                The frameworks to filter on. By default only a subset of the available frameworks are tested. If set to
                "all", all available frameworks will be tested. It is also possible to provide a single framework or a
                custom set of frameworks to check.

        Returns:
            `Dict[str, List[str]]`: A dictionary mapping task names to a sorted list of model IDs.

        Example:
        ```py
        # Must be run in an async contextthon
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()

        # Discover zero-shot-classification models currently deployed
        >>> models = await client.list_deployed_models()
        >>> models["zero-shot-classification"]
        ['Narsil/deberta-large-mnli-zero-cls', 'facebook/bart-large-mnli', ...]

        # List from only 1 framework
        >>> await client.list_deployed_models("text-generation-inference")
        {'text-generation': ['bigcode/starcoder', 'meta-llama/Llama-2-70b-chat-hf', ...], ...}
        ```
        """
        if self.provider != "hf-inference":
            raise ValueError(f"Listing deployed models is not supported on '{self.provider}'.")

        # Resolve which frameworks to check
        if frameworks is None:
            frameworks = constants.MAIN_INFERENCE_API_FRAMEWORKS
        elif frameworks == "all":
            frameworks = constants.ALL_INFERENCE_API_FRAMEWORKS
        elif isinstance(frameworks, str):
            frameworks = [frameworks]
        frameworks = list(set(frameworks))

        # Fetch them iteratively
        models_by_task: Dict[str, List[str]] = {}

        def _unpack_response(framework: str, items: List[Dict]) -> None:
            for model in items:
                if framework == "sentence-transformers":
                    # Model running with the `sentence-transformers` framework can work with both tasks even if not
                    # branded as such in the API response
                    models_by_task.setdefault("feature-extraction", []).append(model["model_id"])
                    models_by_task.setdefault("sentence-similarity", []).append(model["model_id"])
                else:
                    models_by_task.setdefault(model["task"], []).append(model["model_id"])

        for framework in frameworks:
            response = get_session().get(
                f"{constants.INFERENCE_ENDPOINT}/framework/{framework}", headers=build_hf_headers(token=self.token)
            )
            hf_raise_for_status(response)
            _unpack_response(framework, response.json())

        # Sort alphabetically for discoverability and return
        for task, models in models_by_task.items():
            models_by_task[task] = sorted(set(models), key=lambda x: x.lower())
        return models_by_task

    def _get_client_session(self, headers: Optional[Dict] = None) -> "ClientSession":
        aiohttp = _import_aiohttp()
        client_headers = self.headers.copy()
        if headers is not None:
            client_headers.update(headers)

        # Return a new aiohttp ClientSession with correct settings.
        session = aiohttp.ClientSession(
            headers=client_headers,
            cookies=self.cookies,
            timeout=aiohttp.ClientTimeout(self.timeout),
            trust_env=self.trust_env,
        )

        # Keep track of sessions to close them later
        self._sessions[session] = set()

        # Override the `._request` method to register responses to be closed
        session._wrapped_request = session._request

        async def _request(method, url, **kwargs):
            response = await session._wrapped_request(method, url, **kwargs)
            self._sessions[session].add(response)
            return response

        session._request = _request

        # Override the 'close' method to
        # 1. close ongoing responses
        # 2. deregister the session when closed
        session._close = session.close

        async def close_session():
            for response in self._sessions[session]:
                response.close()
            await session._close()
            self._sessions.pop(session, None)

        session.close = close_session
        return session

    async def get_endpoint_info(self, *, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about the deployed endpoint.

        This endpoint is only available on endpoints powered by Text-Generation-Inference (TGI) or Text-Embedding-Inference (TEI).
        Endpoints powered by `transformers` return an empty payload.

        Args:
            model (`str`, *optional*):
                The model to use for inference. Can be a model ID hosted on the Hugging Face Hub or a URL to a deployed
                Inference Endpoint. This parameter overrides the model defined at the instance level. Defaults to None.

        Returns:
            `Dict[str, Any]`: Information about the endpoint.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient("meta-llama/Meta-Llama-3-70B-Instruct")
        >>> await client.get_endpoint_info()
        {
            'model_id': 'meta-llama/Meta-Llama-3-70B-Instruct',
            'model_sha': None,
            'model_dtype': 'torch.float16',
            'model_device_type': 'cuda',
            'model_pipeline_tag': None,
            'max_concurrent_requests': 128,
            'max_best_of': 2,
            'max_stop_sequences': 4,
            'max_input_length': 8191,
            'max_total_tokens': 8192,
            'waiting_served_ratio': 0.3,
            'max_batch_total_tokens': 1259392,
            'max_waiting_tokens': 20,
            'max_batch_size': None,
            'validation_workers': 32,
            'max_client_batch_size': 4,
            'version': '2.0.2',
            'sha': 'dccab72549635c7eb5ddb17f43f0b7cdff07c214',
            'docker_label': 'sha-dccab72'
        }
        ```
        """
        if self.provider != "hf-inference":
            raise ValueError(f"Getting endpoint info is not supported on '{self.provider}'.")

        model = model or self.model
        if model is None:
            raise ValueError("Model id not provided.")
        if model.startswith(("http://", "https://")):
            url = model.rstrip("/") + "/info"
        else:
            url = f"{constants.INFERENCE_ENDPOINT}/models/{model}/info"

        async with self._get_client_session(headers=build_hf_headers(token=self.token)) as client:
            response = await client.get(url, proxy=self.proxies)
            response.raise_for_status()
            return await response.json()

    async def health_check(self, model: Optional[str] = None) -> bool:
        """
        Check the health of the deployed endpoint.

        Health check is only available with Inference Endpoints powered by Text-Generation-Inference (TGI) or Text-Embedding-Inference (TEI).
        For Inference API, please use [`InferenceClient.get_model_status`] instead.

        Args:
            model (`str`, *optional*):
                URL of the Inference Endpoint. This parameter overrides the model defined at the instance level. Defaults to None.

        Returns:
            `bool`: True if everything is working fine.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient("https://jzgu0buei5.us-east-1.aws.endpoints.huggingface.cloud")
        >>> await client.health_check()
        True
        ```
        """
        if self.provider != "hf-inference":
            raise ValueError(f"Health check is not supported on '{self.provider}'.")

        model = model or self.model
        if model is None:
            raise ValueError("Model id not provided.")
        if not model.startswith(("http://", "https://")):
            raise ValueError(
                "Model must be an Inference Endpoint URL. For serverless Inference API, please use `InferenceClient.get_model_status`."
            )
        url = model.rstrip("/") + "/health"

        async with self._get_client_session(headers=build_hf_headers(token=self.token)) as client:
            response = await client.get(url, proxy=self.proxies)
            return response.status == 200

    @_deprecate_method(
        version="0.35.0",
        message=(
            "HF Inference API is getting revamped and will only support warm models in the future (no cold start allowed)."
            " Use `HfApi.model_info` to get the model status both with HF Inference API and external providers."
        ),
    )
    async def get_model_status(self, model: Optional[str] = None) -> ModelStatus:
        """
        Get the status of a model hosted on the HF Inference API.

        <Tip>

        This endpoint is mostly useful when you already know which model you want to use and want to check its
        availability. If you want to discover already deployed models, you should rather use [`~InferenceClient.list_deployed_models`].

        </Tip>

        Args:
            model (`str`, *optional*):
                Identifier of the model for witch the status gonna be checked. If model is not provided,
                the model associated with this instance of [`InferenceClient`] will be used. Only HF Inference API service can be checked so the
                identifier cannot be a URL.


        Returns:
            [`ModelStatus`]: An instance of ModelStatus dataclass, containing information,
                         about the state of the model: load, state, compute type and framework.

        Example:
        ```py
        # Must be run in an async context
        >>> from huggingface_hub import AsyncInferenceClient
        >>> client = AsyncInferenceClient()
        >>> await client.get_model_status("meta-llama/Meta-Llama-3-8B-Instruct")
        ModelStatus(loaded=True, state='Loaded', compute_type='gpu', framework='text-generation-inference')
        ```
        """
        if self.provider != "hf-inference":
            raise ValueError(f"Getting model status is not supported on '{self.provider}'.")

        model = model or self.model
        if model is None:
            raise ValueError("Model id not provided.")
        if model.startswith("https://"):
            raise NotImplementedError("Model status is only available for Inference API endpoints.")
        url = f"{constants.INFERENCE_ENDPOINT}/status/{model}"

        async with self._get_client_session(headers=build_hf_headers(token=self.token)) as client:
            response = await client.get(url, proxy=self.proxies)
            response.raise_for_status()
            response_data = await response.json()

        if "error" in response_data:
            raise ValueError(response_data["error"])

        return ModelStatus(
            loaded=response_data["loaded"],
            state=response_data["state"],
            compute_type=response_data["compute_type"],
            framework=response_data["framework"],
        )

    @property
    def chat(self) -> "ProxyClientChat":
        return ProxyClientChat(self)


class _ProxyClient:
    """Proxy class to be able to call `client.chat.completion.create(...)` as OpenAI client."""

    def __init__(self, client: AsyncInferenceClient):
        self._client = client


class ProxyClientChat(_ProxyClient):
    """Proxy class to be able to call `client.chat.completion.create(...)` as OpenAI client."""

    @property
    def completions(self) -> "ProxyClientChatCompletions":
        return ProxyClientChatCompletions(self._client)


class ProxyClientChatCompletions(_ProxyClient):
    """Proxy class to be able to call `client.chat.completion.create(...)` as OpenAI client."""

    @property
    def create(self):
        return self._client.chat_completion

# === NexusCore/openenv\Lib\site-packages\matplotlib\backend_bases.py ===
"""
Abstract base classes define the primitives that renderers and
graphics contexts must implement to serve as a Matplotlib backend.

`RendererBase`
    An abstract base class to handle drawing/rendering operations.

`FigureCanvasBase`
    The abstraction layer that separates the `.Figure` from the backend
    specific details like a user interface drawing area.

`GraphicsContextBase`
    An abstract base class that provides color, line styles, etc.

`Event`
    The base class for all of the Matplotlib event handling.  Derived classes
    such as `KeyEvent` and `MouseEvent` store the meta data like keys and
    buttons pressed, x and y locations in pixel and `~.axes.Axes` coordinates.

`ShowBase`
    The base class for the ``Show`` class of each interactive backend; the
    'show' callable is then set to ``Show.__call__``.

`ToolContainerBase`
    The base class for the Toolbar class of each interactive backend.
"""

from collections import namedtuple
from contextlib import ExitStack, contextmanager, nullcontext
from enum import Enum, IntEnum
import functools
import importlib
import inspect
import io
import itertools
import logging
import os
import pathlib
import signal
import socket
import sys
import time
import weakref
from weakref import WeakKeyDictionary

import numpy as np

import matplotlib as mpl
from matplotlib import (
    _api, backend_tools as tools, cbook, colors, _docstring, text,
    _tight_bbox, transforms, widgets, is_interactive, rcParams)
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_managers import ToolManager
from matplotlib.cbook import _setattr_cm
from matplotlib.layout_engine import ConstrainedLayoutEngine
from matplotlib.path import Path
from matplotlib.texmanager import TexManager
from matplotlib.transforms import Affine2D
from matplotlib._enums import JoinStyle, CapStyle


_log = logging.getLogger(__name__)
_default_filetypes = {
    'eps': 'Encapsulated Postscript',
    'jpg': 'Joint Photographic Experts Group',
    'jpeg': 'Joint Photographic Experts Group',
    'pdf': 'Portable Document Format',
    'pgf': 'PGF code for LaTeX',
    'png': 'Portable Network Graphics',
    'ps': 'Postscript',
    'raw': 'Raw RGBA bitmap',
    'rgba': 'Raw RGBA bitmap',
    'svg': 'Scalable Vector Graphics',
    'svgz': 'Scalable Vector Graphics',
    'tif': 'Tagged Image File Format',
    'tiff': 'Tagged Image File Format',
    'webp': 'WebP Image Format',
}
_default_backends = {
    'eps': 'matplotlib.backends.backend_ps',
    'jpg': 'matplotlib.backends.backend_agg',
    'jpeg': 'matplotlib.backends.backend_agg',
    'pdf': 'matplotlib.backends.backend_pdf',
    'pgf': 'matplotlib.backends.backend_pgf',
    'png': 'matplotlib.backends.backend_agg',
    'ps': 'matplotlib.backends.backend_ps',
    'raw': 'matplotlib.backends.backend_agg',
    'rgba': 'matplotlib.backends.backend_agg',
    'svg': 'matplotlib.backends.backend_svg',
    'svgz': 'matplotlib.backends.backend_svg',
    'tif': 'matplotlib.backends.backend_agg',
    'tiff': 'matplotlib.backends.backend_agg',
    'webp': 'matplotlib.backends.backend_agg',
}


def register_backend(format, backend, description=None):
    """
    Register a backend for saving to a given file format.

    Parameters
    ----------
    format : str
        File extension
    backend : module string or canvas class
        Backend for handling file output
    description : str, default: ""
        Description of the file type.
    """
    if description is None:
        description = ''
    _default_backends[format] = backend
    _default_filetypes[format] = description


def get_registered_canvas_class(format):
    """
    Return the registered default canvas for given file format.
    Handles deferred import of required backend.
    """
    if format not in _default_backends:
        return None
    backend_class = _default_backends[format]
    if isinstance(backend_class, str):
        backend_class = importlib.import_module(backend_class).FigureCanvas
        _default_backends[format] = backend_class
    return backend_class


class RendererBase:
    """
    An abstract base class to handle drawing/rendering operations.

    The following methods must be implemented in the backend for full
    functionality (though just implementing `draw_path` alone would give a
    highly capable backend):

    * `draw_path`
    * `draw_image`
    * `draw_gouraud_triangles`

    The following methods *should* be implemented in the backend for
    optimization reasons:

    * `draw_text`
    * `draw_markers`
    * `draw_path_collection`
    * `draw_quad_mesh`
    """
    def __init__(self):
        super().__init__()
        self._texmanager = None
        self._text2path = text.TextToPath()
        self._raster_depth = 0
        self._rasterizing = False

    def open_group(self, s, gid=None):
        """
        Open a grouping element with label *s* and *gid* (if set) as id.

        Only used by the SVG renderer.
        """

    def close_group(self, s):
        """
        Close a grouping element with label *s*.

        Only used by the SVG renderer.
        """

    def draw_path(self, gc, path, transform, rgbFace=None):
        """Draw a `~.path.Path` instance using the given affine transform."""
        raise NotImplementedError

    def draw_markers(self, gc, marker_path, marker_trans, path,
                     trans, rgbFace=None):
        """
        Draw a marker at each of *path*'s vertices (excluding control points).

        The base (fallback) implementation makes multiple calls to `draw_path`.
        Backends may want to override this method in order to draw the marker
        only once and reuse it multiple times.

        Parameters
        ----------
        gc : `.GraphicsContextBase`
            The graphics context.
        marker_path : `~matplotlib.path.Path`
            The path for the marker.
        marker_trans : `~matplotlib.transforms.Transform`
            An affine transform applied to the marker.
        path : `~matplotlib.path.Path`
            The locations to draw the markers.
        trans : `~matplotlib.transforms.Transform`
            An affine transform applied to the path.
        rgbFace : :mpltype:`color`, optional
        """
        for vertices, codes in path.iter_segments(trans, simplify=False):
            if len(vertices):
                x, y = vertices[-2:]
                self.draw_path(gc, marker_path,
                               marker_trans +
                               transforms.Affine2D().translate(x, y),
                               rgbFace)

    def draw_path_collection(self, gc, master_transform, paths, all_transforms,
                             offsets, offset_trans, facecolors, edgecolors,
                             linewidths, linestyles, antialiaseds, urls,
                             offset_position):
        """
        Draw a collection of *paths*.

        Each path is first transformed by the corresponding entry
        in *all_transforms* (a list of (3, 3) matrices) and then by
        *master_transform*.  They are then translated by the corresponding
        entry in *offsets*, which has been first transformed by *offset_trans*.

        *facecolors*, *edgecolors*, *linewidths*, *linestyles*, and
        *antialiased* are lists that set the corresponding properties.

        *offset_position* is unused now, but the argument is kept for
        backwards compatibility.

        The base (fallback) implementation makes multiple calls to `draw_path`.
        Backends may want to override this in order to render each set of
        path data only once, and then reference that path multiple times with
        the different offsets, colors, styles etc.  The generator methods
        `_iter_collection_raw_paths` and `_iter_collection` are provided to
        help with (and standardize) the implementation across backends.  It
        is highly recommended to use those generators, so that changes to the
        behavior of `draw_path_collection` can be made globally.
        """
        path_ids = self._iter_collection_raw_paths(master_transform,
                                                   paths, all_transforms)

        for xo, yo, path_id, gc0, rgbFace in self._iter_collection(
                gc, list(path_ids), offsets, offset_trans,
                facecolors, edgecolors, linewidths, linestyles,
                antialiaseds, urls, offset_position):
            path, transform = path_id
            # Only apply another translation if we have an offset, else we
            # reuse the initial transform.
            if xo != 0 or yo != 0:
                # The transformation can be used by multiple paths. Since
                # translate is a inplace operation, we need to copy the
                # transformation by .frozen() before applying the translation.
                transform = transform.frozen()
                transform.translate(xo, yo)
            self.draw_path(gc0, path, transform, rgbFace)

    def draw_quad_mesh(self, gc, master_transform, meshWidth, meshHeight,
                       coordinates, offsets, offsetTrans, facecolors,
                       antialiased, edgecolors):
        """
        Draw a quadmesh.

        The base (fallback) implementation converts the quadmesh to paths and
        then calls `draw_path_collection`.
        """

        from matplotlib.collections import QuadMesh
        paths = QuadMesh._convert_mesh_to_paths(coordinates)

        if edgecolors is None:
            edgecolors = facecolors
        linewidths = np.array([gc.get_linewidth()], float)

        return self.draw_path_collection(
            gc, master_transform, paths, [], offsets, offsetTrans, facecolors,
            edgecolors, linewidths, [], [antialiased], [None], 'screen')

    def draw_gouraud_triangles(self, gc, triangles_array, colors_array,
                               transform):
        """
        Draw a series of Gouraud triangles.

        Parameters
        ----------
        gc : `.GraphicsContextBase`
            The graphics context.
        triangles_array : (N, 3, 2) array-like
            Array of *N* (x, y) points for the triangles.
        colors_array : (N, 3, 4) array-like
            Array of *N* RGBA colors for each point of the triangles.
        transform : `~matplotlib.transforms.Transform`
            An affine transform to apply to the points.
        """
        raise NotImplementedError

    def _iter_collection_raw_paths(self, master_transform, paths,
                                   all_transforms):
        """
        Helper method (along with `_iter_collection`) to implement
        `draw_path_collection` in a memory-efficient manner.

        This method yields all of the base path/transform combinations, given a
        master transform, a list of paths and list of transforms.

        The arguments should be exactly what is passed in to
        `draw_path_collection`.

        The backend should take each yielded path and transform and create an
        object that can be referenced (reused) later.
        """
        Npaths = len(paths)
        Ntransforms = len(all_transforms)
        N = max(Npaths, Ntransforms)

        if Npaths == 0:
            return

        transform = transforms.IdentityTransform()
        for i in range(N):
            path = paths[i % Npaths]
            if Ntransforms:
                transform = Affine2D(all_transforms[i % Ntransforms])
            yield path, transform + master_transform

    def _iter_collection_uses_per_path(self, paths, all_transforms,
                                       offsets, facecolors, edgecolors):
        """
        Compute how many times each raw path object returned by
        `_iter_collection_raw_paths` would be used when calling
        `_iter_collection`. This is intended for the backend to decide
        on the tradeoff between using the paths in-line and storing
        them once and reusing. Rounds up in case the number of uses
        is not the same for every path.
        """
        Npaths = len(paths)
        if Npaths == 0 or len(facecolors) == len(edgecolors) == 0:
            return 0
        Npath_ids = max(Npaths, len(all_transforms))
        N = max(Npath_ids, len(offsets))
        return (N + Npath_ids - 1) // Npath_ids

    def _iter_collection(self, gc, path_ids, offsets, offset_trans, facecolors,
                         edgecolors, linewidths, linestyles,
                         antialiaseds, urls, offset_position):
        """
        Helper method (along with `_iter_collection_raw_paths`) to implement
        `draw_path_collection` in a memory-efficient manner.

        This method yields all of the path, offset and graphics context
        combinations to draw the path collection.  The caller should already
        have looped over the results of `_iter_collection_raw_paths` to draw
        this collection.

        The arguments should be the same as that passed into
        `draw_path_collection`, with the exception of *path_ids*, which is a
        list of arbitrary objects that the backend will use to reference one of
        the paths created in the `_iter_collection_raw_paths` stage.

        Each yielded result is of the form::

           xo, yo, path_id, gc, rgbFace

        where *xo*, *yo* is an offset; *path_id* is one of the elements of
        *path_ids*; *gc* is a graphics context and *rgbFace* is a color to
        use for filling the path.
        """
        Npaths = len(path_ids)
        Noffsets = len(offsets)
        N = max(Npaths, Noffsets)
        Nfacecolors = len(facecolors)
        Nedgecolors = len(edgecolors)
        Nlinewidths = len(linewidths)
        Nlinestyles = len(linestyles)
        Nurls = len(urls)

        if (Nfacecolors == 0 and Nedgecolors == 0) or Npaths == 0:
            return

        gc0 = self.new_gc()
        gc0.copy_properties(gc)

        def cycle_or_default(seq, default=None):
            # Cycle over *seq* if it is not empty; else always yield *default*.
            return (itertools.cycle(seq) if len(seq)
                    else itertools.repeat(default))

        pathids = cycle_or_default(path_ids)
        toffsets = cycle_or_default(offset_trans.transform(offsets), (0, 0))
        fcs = cycle_or_default(facecolors)
        ecs = cycle_or_default(edgecolors)
        lws = cycle_or_default(linewidths)
        lss = cycle_or_default(linestyles)
        aas = cycle_or_default(antialiaseds)
        urls = cycle_or_default(urls)

        if Nedgecolors == 0:
            gc0.set_linewidth(0.0)

        for pathid, (xo, yo), fc, ec, lw, ls, aa, url in itertools.islice(
                zip(pathids, toffsets, fcs, ecs, lws, lss, aas, urls), N):
            if not (np.isfinite(xo) and np.isfinite(yo)):
                continue
            if Nedgecolors:
                if Nlinewidths:
                    gc0.set_linewidth(lw)
                if Nlinestyles:
                    gc0.set_dashes(*ls)
                if len(ec) == 4 and ec[3] == 0.0:
                    gc0.set_linewidth(0)
                else:
                    gc0.set_foreground(ec)
            if fc is not None and len(fc) == 4 and fc[3] == 0:
                fc = None
            gc0.set_antialiased(aa)
            if Nurls:
                gc0.set_url(url)
            yield xo, yo, pathid, gc0, fc
        gc0.restore()

    def get_image_magnification(self):
        """
        Get the factor by which to magnify images passed to `draw_image`.
        Allows a backend to have images at a different resolution to other
        artists.
        """
        return 1.0

    def draw_image(self, gc, x, y, im, transform=None):
        """
        Draw an RGBA image.

        Parameters
        ----------
        gc : `.GraphicsContextBase`
            A graphics context with clipping information.

        x : float
            The distance in physical units (i.e., dots or pixels) from the left
            hand side of the canvas.

        y : float
            The distance in physical units (i.e., dots or pixels) from the
            bottom side of the canvas.

        im : (N, M, 4) array of `numpy.uint8`
            An array of RGBA pixels.

        transform : `~matplotlib.transforms.Affine2DBase`
            If and only if the concrete backend is written such that
            `option_scale_image` returns ``True``, an affine transformation
            (i.e., an `.Affine2DBase`) *may* be passed to `draw_image`.  The
            translation vector of the transformation is given in physical units
            (i.e., dots or pixels). Note that the transformation does not
            override *x* and *y*, and has to be applied *before* translating
            the result by *x* and *y* (this can be accomplished by adding *x*
            and *y* to the translation vector defined by *transform*).
        """
        raise NotImplementedError

    def option_image_nocomposite(self):
        """
        Return whether image composition by Matplotlib should be skipped.

        Raster backends should usually return False (letting the C-level
        rasterizer take care of image composition); vector backends should
        usually return ``not rcParams["image.composite_image"]``.
        """
        return False

    def option_scale_image(self):
        """
        Return whether arbitrary affine transformations in `draw_image` are
        supported (True for most vector backends).
        """
        return False

    def draw_tex(self, gc, x, y, s, prop, angle, *, mtext=None):
        """
        Draw a TeX instance.

        Parameters
        ----------
        gc : `.GraphicsContextBase`
            The graphics context.
        x : float
            The x location of the text in display coords.
        y : float
            The y location of the text baseline in display coords.
        s : str
            The TeX text string.
        prop : `~matplotlib.font_manager.FontProperties`
            The font properties.
        angle : float
            The rotation angle in degrees anti-clockwise.
        mtext : `~matplotlib.text.Text`
            The original text object to be rendered.
        """
        self._draw_text_as_path(gc, x, y, s, prop, angle, ismath="TeX")

    def draw_text(self, gc, x, y, s, prop, angle, ismath=False, mtext=None):
        """
        Draw a text instance.

        Parameters
        ----------
        gc : `.GraphicsContextBase`
            The graphics context.
        x : float
            The x location of the text in display coords.
        y : float
            The y location of the text baseline in display coords.
        s : str
            The text string.
        prop : `~matplotlib.font_manager.FontProperties`
            The font properties.
        angle : float
            The rotation angle in degrees anti-clockwise.
        ismath : bool or "TeX"
            If True, use mathtext parser.
        mtext : `~matplotlib.text.Text`
            The original text object to be rendered.

        Notes
        -----
        **Notes for backend implementers:**

        `.RendererBase.draw_text` also supports passing "TeX" to the *ismath*
        parameter to use TeX rendering, but this is not required for actual
        rendering backends, and indeed many builtin backends do not support
        this.  Rather, TeX rendering is provided by `~.RendererBase.draw_tex`.
        """
        self._draw_text_as_path(gc, x, y, s, prop, angle, ismath)

    def _draw_text_as_path(self, gc, x, y, s, prop, angle, ismath):
        """
        Draw the text by converting them to paths using `.TextToPath`.

        This private helper supports the same parameters as
        `~.RendererBase.draw_text`; setting *ismath* to "TeX" triggers TeX
        rendering.
        """
        text2path = self._text2path
        fontsize = self.points_to_pixels(prop.get_size_in_points())
        verts, codes = text2path.get_text_path(prop, s, ismath=ismath)
        path = Path(verts, codes)
        if self.flipy():
            width, height = self.get_canvas_width_height()
            transform = (Affine2D()
                         .scale(fontsize / text2path.FONT_SCALE)
                         .rotate_deg(angle)
                         .translate(x, height - y))
        else:
            transform = (Affine2D()
                         .scale(fontsize / text2path.FONT_SCALE)
                         .rotate_deg(angle)
                         .translate(x, y))
        color = gc.get_rgb()
        gc.set_linewidth(0.0)
        self.draw_path(gc, path, transform, rgbFace=color)

    def get_text_width_height_descent(self, s, prop, ismath):
        """
        Get the width, height, and descent (offset from the bottom to the baseline), in
        display coords, of the string *s* with `.FontProperties` *prop*.

        Whitespace at the start and the end of *s* is included in the reported width.
        """
        fontsize = prop.get_size_in_points()

        if ismath == 'TeX':
            # todo: handle properties
            return self.get_texmanager().get_text_width_height_descent(
                s, fontsize, renderer=self)

        dpi = self.points_to_pixels(72)
        if ismath:
            dims = self._text2path.mathtext_parser.parse(s, dpi, prop)
            return dims[0:3]  # return width, height, descent

        flags = self._text2path._get_hinting_flag()
        font = self._text2path._get_font(prop)
        font.set_size(fontsize, dpi)
        # the width and height of unrotated string
        font.set_text(s, 0.0, flags=flags)
        w, h = font.get_width_height()
        d = font.get_descent()
        w /= 64.0  # convert from subpixels
        h /= 64.0
        d /= 64.0
        return w, h, d

    def flipy(self):
        """
        Return whether y values increase from top to bottom.

        Note that this only affects drawing of texts.
        """
        return True

    def get_canvas_width_height(self):
        """Return the canvas width and height in display coords."""
        return 1, 1

    def get_texmanager(self):
        """Return the `.TexManager` instance."""
        if self._texmanager is None:
            self._texmanager = TexManager()
        return self._texmanager

    def new_gc(self):
        """Return an instance of a `.GraphicsContextBase`."""
        return GraphicsContextBase()

    def points_to_pixels(self, points):
        """
        Convert points to display units.

        You need to override this function (unless your backend
        doesn't have a dpi, e.g., postscript or svg).  Some imaging
        systems assume some value for pixels per inch::

            points to pixels = points * pixels_per_inch/72 * dpi/72

        Parameters
        ----------
        points : float or array-like

        Returns
        -------
        Points converted to pixels
        """
        return points

    def start_rasterizing(self):
        """
        Switch to the raster renderer.

        Used by `.MixedModeRenderer`.
        """

    def stop_rasterizing(self):
        """
        Switch back to the vector renderer and draw the contents of the raster
        renderer as an image on the vector renderer.

        Used by `.MixedModeRenderer`.
        """

    def start_filter(self):
        """
        Switch to a temporary renderer for image filtering effects.

        Currently only supported by the agg renderer.
        """

    def stop_filter(self, filter_func):
        """
        Switch back to the original renderer.  The contents of the temporary
        renderer is processed with the *filter_func* and is drawn on the
        original renderer as an image.

        Currently only supported by the agg renderer.
        """

    def _draw_disabled(self):
        """
        Context manager to temporary disable drawing.

        This is used for getting the drawn size of Artists.  This lets us
        run the draw process to update any Python state but does not pay the
        cost of the draw_XYZ calls on the canvas.
        """
        no_ops = {
            meth_name: lambda *args, **kwargs: None
            for meth_name in dir(RendererBase)
            if (meth_name.startswith("draw_")
                or meth_name in ["open_group", "close_group"])
        }

        return _setattr_cm(self, **no_ops)


class GraphicsContextBase:
    """An abstract base class that provides color, line styles, etc."""

    def __init__(self):
        self._alpha = 1.0
        self._forced_alpha = False  # if True, _alpha overrides A from RGBA
        self._antialiased = 1  # use 0, 1 not True, False for extension code
        self._capstyle = CapStyle('butt')
        self._cliprect = None
        self._clippath = None
        self._dashes = 0, None
        self._joinstyle = JoinStyle('round')
        self._linestyle = 'solid'
        self._linewidth = 1
        self._rgb = (0.0, 0.0, 0.0, 1.0)
        self._hatch = None
        self._hatch_color = colors.to_rgba(rcParams['hatch.color'])
        self._hatch_linewidth = rcParams['hatch.linewidth']
        self._url = None
        self._gid = None
        self._snap = None
        self._sketch = None

    def copy_properties(self, gc):
        """Copy properties from *gc* to self."""
        self._alpha = gc._alpha
        self._forced_alpha = gc._forced_alpha
        self._antialiased = gc._antialiased
        self._capstyle = gc._capstyle
        self._cliprect = gc._cliprect
        self._clippath = gc._clippath
        self._dashes = gc._dashes
        self._joinstyle = gc._joinstyle
        self._linestyle = gc._linestyle
        self._linewidth = gc._linewidth
        self._rgb = gc._rgb
        self._hatch = gc._hatch
        self._hatch_color = gc._hatch_color
        self._hatch_linewidth = gc._hatch_linewidth
        self._url = gc._url
        self._gid = gc._gid
        self._snap = gc._snap
        self._sketch = gc._sketch

    def restore(self):
        """
        Restore the graphics context from the stack - needed only
        for backends that save graphics contexts on a stack.
        """

    def get_alpha(self):
        """
        Return the alpha value used for blending - not supported on all
        backends.
        """
        return self._alpha

    def get_antialiased(self):
        """Return whether the object should try to do antialiased rendering."""
        return self._antialiased

    def get_capstyle(self):
        """Return the `.CapStyle`."""
        return self._capstyle.name

    def get_clip_rectangle(self):
        """
        Return the clip rectangle as a `~matplotlib.transforms.Bbox` instance.
        """
        return self._cliprect

    def get_clip_path(self):
        """
        Return the clip path in the form (path, transform), where path
        is a `~.path.Path` instance, and transform is
        an affine transform to apply to the path before clipping.
        """
        if self._clippath is not None:
            tpath, tr = self._clippath.get_transformed_path_and_affine()
            if np.all(np.isfinite(tpath.vertices)):
                return tpath, tr
            else:
                _log.warning("Ill-defined clip_path detected. Returning None.")
                return None, None
        return None, None

    def get_dashes(self):
        """
        Return the dash style as an (offset, dash-list) pair.

        See `.set_dashes` for details.

        Default value is (None, None).
        """
        return self._dashes

    def get_forced_alpha(self):
        """
        Return whether the value given by get_alpha() should be used to
        override any other alpha-channel values.
        """
        return self._forced_alpha

    def get_joinstyle(self):
        """Return the `.JoinStyle`."""
        return self._joinstyle.name

    def get_linewidth(self):
        """Return the line width in points."""
        return self._linewidth

    def get_rgb(self):
        """Return a tuple of three or four floats from 0-1."""
        return self._rgb

    def get_url(self):
        """Return a url if one is set, None otherwise."""
        return self._url

    def get_gid(self):
        """Return the object identifier if one is set, None otherwise."""
        return self._gid

    def get_snap(self):
        """
        Return the snap setting, which can be:

        * True: snap vertices to the nearest pixel center
        * False: leave vertices as-is
        * None: (auto) If the path contains only rectilinear line segments,
          round to the nearest pixel center
        """
        return self._snap

    def set_alpha(self, alpha):
        """
        Set the alpha value used for blending - not supported on all backends.

        If ``alpha=None`` (the default), the alpha components of the
        foreground and fill colors will be used to set their respective
        transparencies (where applicable); otherwise, ``alpha`` will override
        them.
        """
        if alpha is not None:
            self._alpha = alpha
            self._forced_alpha = True
        else:
            self._alpha = 1.0
            self._forced_alpha = False
        self.set_foreground(self._rgb, isRGBA=True)

    def set_antialiased(self, b):
        """Set whether object should be drawn with antialiased rendering."""
        # Use ints to make life easier on extension code trying to read the gc.
        self._antialiased = int(bool(b))

    @_docstring.interpd
    def set_capstyle(self, cs):
        """
        Set how to draw endpoints of lines.

        Parameters
        ----------
        cs : `.CapStyle` or %(CapStyle)s
        """
        self._capstyle = CapStyle(cs)

    def set_clip_rectangle(self, rectangle):
        """Set the clip rectangle to a `.Bbox` or None."""
        self._cliprect = rectangle

    def set_clip_path(self, path):
        """Set the clip path to a `.TransformedPath` or None."""
        _api.check_isinstance((transforms.TransformedPath, None), path=path)
        self._clippath = path

    def set_dashes(self, dash_offset, dash_list):
        """
        Set the dash style for the gc.

        Parameters
        ----------
        dash_offset : float
            Distance, in points, into the dash pattern at which to
            start the pattern. It is usually set to 0.
        dash_list : array-like or None
            The on-off sequence as points.  None specifies a solid line. All
            values must otherwise be non-negative (:math:`\\ge 0`).

        Notes
        -----
        See p. 666 of the PostScript
        `Language Reference
        <https://www.adobe.com/jp/print/postscript/pdfs/PLRM.pdf>`_
        for more info.
        """
        if dash_list is not None:
            dl = np.asarray(dash_list)
            if np.any(dl < 0.0):
                raise ValueError(
                    "All values in the dash list must be non-negative")
            if dl.size and not np.any(dl > 0.0):
                raise ValueError(
                    'At least one value in the dash list must be positive')
        self._dashes = dash_offset, dash_list

    def set_foreground(self, fg, isRGBA=False):
        """
        Set the foreground color.

        Parameters
        ----------
        fg : :mpltype:`color`
        isRGBA : bool
            If *fg* is known to be an ``(r, g, b, a)`` tuple, *isRGBA* can be
            set to True to improve performance.
        """
        if self._forced_alpha and isRGBA:
            self._rgb = fg[:3] + (self._alpha,)
        elif self._forced_alpha:
            self._rgb = colors.to_rgba(fg, self._alpha)
        elif isRGBA:
            self._rgb = fg
        else:
            self._rgb = colors.to_rgba(fg)

    @_docstring.interpd
    def set_joinstyle(self, js):
        """
        Set how to draw connections between line segments.

        Parameters
        ----------
        js : `.JoinStyle` or %(JoinStyle)s
        """
        self._joinstyle = JoinStyle(js)

    def set_linewidth(self, w):
        """Set the linewidth in points."""
        self._linewidth = float(w)

    def set_url(self, url):
        """Set the url for links in compatible backends."""
        self._url = url

    def set_gid(self, id):
        """Set the id."""
        self._gid = id

    def set_snap(self, snap):
        """
        Set the snap setting which may be:

        * True: snap vertices to the nearest pixel center
        * False: leave vertices as-is
        * None: (auto) If the path contains only rectilinear line segments,
          round to the nearest pixel center
        """
        self._snap = snap

    def set_hatch(self, hatch):
        """Set the hatch style (for fills)."""
        self._hatch = hatch

    def get_hatch(self):
        """Get the current hatch style."""
        return self._hatch

    def get_hatch_path(self, density=6.0):
        """Return a `.Path` for the current hatch."""
        hatch = self.get_hatch()
        if hatch is None:
            return None
        return Path.hatch(hatch, density)

    def get_hatch_color(self):
        """Get the hatch color."""
        return self._hatch_color

    def set_hatch_color(self, hatch_color):
        """Set the hatch color."""
        self._hatch_color = hatch_color

    def get_hatch_linewidth(self):
        """Get the hatch linewidth."""
        return self._hatch_linewidth

    def set_hatch_linewidth(self, hatch_linewidth):
        """Set the hatch linewidth."""
        self._hatch_linewidth = hatch_linewidth

    def get_sketch_params(self):
        """
        Return the sketch parameters for the artist.

        Returns
        -------
        tuple or `None`

            A 3-tuple with the following elements:

            * ``scale``: The amplitude of the wiggle perpendicular to the
              source line.
            * ``length``: The length of the wiggle along the line.
            * ``randomness``: The scale factor by which the length is
              shrunken or expanded.

            May return `None` if no sketch parameters were set.
        """
        return self._sketch

    def set_sketch_params(self, scale=None, length=None, randomness=None):
        """
        Set the sketch parameters.

        Parameters
        ----------
        scale : float, optional
            The amplitude of the wiggle perpendicular to the source line, in
            pixels.  If scale is `None`, or not provided, no sketch filter will
            be provided.
        length : float, default: 128
            The length of the wiggle along the line, in pixels.
        randomness : float, default: 16
            The scale factor by which the length is shrunken or expanded.
        """
        self._sketch = (
            None if scale is None
            else (scale, length or 128., randomness or 16.))


class TimerBase:
    """
    A base class for providing timer events, useful for things animations.
    Backends need to implement a few specific methods in order to use their
    own timing mechanisms so that the timer events are integrated into their
    event loops.

    Subclasses must override the following methods:

    - ``_timer_start``: Backend-specific code for starting the timer.
    - ``_timer_stop``: Backend-specific code for stopping the timer.

    Subclasses may additionally override the following methods:

    - ``_timer_set_single_shot``: Code for setting the timer to single shot
      operating mode, if supported by the timer object.  If not, the `Timer`
      class itself will store the flag and the ``_on_timer`` method should be
      overridden to support such behavior.

    - ``_timer_set_interval``: Code for setting the interval on the timer, if
      there is a method for doing so on the timer object.

    - ``_on_timer``: The internal function that any timer object should call,
      which will handle the task of running all callbacks that have been set.
    """

    def __init__(self, interval=None, callbacks=None):
        """
        Parameters
        ----------
        interval : int, default: 1000ms
            The time between timer events in milliseconds.  Will be stored as
            ``timer.interval``.
        callbacks : list[tuple[callable, tuple, dict]]
            List of (func, args, kwargs) tuples that will be called upon timer
            events.  This list is accessible as ``timer.callbacks`` and can be
            manipulated directly, or the functions `~.TimerBase.add_callback`
            and `~.TimerBase.remove_callback` can be used.
        """
        self.callbacks = [] if callbacks is None else callbacks.copy()
        # Set .interval and not ._interval to go through the property setter.
        self.interval = 1000 if interval is None else interval
        self.single_shot = False

    def __del__(self):
        """Need to stop timer and possibly disconnect timer."""
        self._timer_stop()

    @_api.delete_parameter("3.9", "interval", alternative="timer.interval")
    def start(self, interval=None):
        """
        Start the timer object.

        Parameters
        ----------
        interval : int, optional
            Timer interval in milliseconds; overrides a previously set interval
            if provided.
        """
        if interval is not None:
            self.interval = interval
        self._timer_start()

    def stop(self):
        """Stop the timer."""
        self._timer_stop()

    def _timer_start(self):
        pass

    def _timer_stop(self):
        pass

    @property
    def interval(self):
        """The time between timer events, in milliseconds."""
        return self._interval

    @interval.setter
    def interval(self, interval):
        # Force to int since none of the backends actually support fractional
        # milliseconds, and some error or give warnings.
        # Some backends also fail when interval == 0, so ensure >= 1 msec
        interval = max(int(interval), 1)
        self._interval = interval
        self._timer_set_interval()

    @property
    def single_shot(self):
        """Whether this timer should stop after a single run."""
        return self._single

    @single_shot.setter
    def single_shot(self, ss):
        self._single = ss
        self._timer_set_single_shot()

    def add_callback(self, func, *args, **kwargs):
        """
        Register *func* to be called by timer when the event fires. Any
        additional arguments provided will be passed to *func*.

        This function returns *func*, which makes it possible to use it as a
        decorator.
        """
        self.callbacks.append((func, args, kwargs))
        return func

    def remove_callback(self, func, *args, **kwargs):
        """
        Remove *func* from list of callbacks.

        *args* and *kwargs* are optional and used to distinguish between copies
        of the same function registered to be called with different arguments.
        This behavior is deprecated.  In the future, ``*args, **kwargs`` won't
        be considered anymore; to keep a specific callback removable by itself,
        pass it to `add_callback` as a `functools.partial` object.
        """
        if args or kwargs:
            _api.warn_deprecated(
                "3.1", message="In a future version, Timer.remove_callback "
                "will not take *args, **kwargs anymore, but remove all "
                "callbacks where the callable matches; to keep a specific "
                "callback removable by itself, pass it to add_callback as a "
                "functools.partial object.")
            self.callbacks.remove((func, args, kwargs))
        else:
            funcs = [c[0] for c in self.callbacks]
            if func in funcs:
                self.callbacks.pop(funcs.index(func))

    def _timer_set_interval(self):
        """Used to set interval on underlying timer object."""

    def _timer_set_single_shot(self):
        """Used to set single shot on underlying timer object."""

    def _on_timer(self):
        """
        Runs all function that have been registered as callbacks. Functions
        can return False (or 0) if they should not be called any more. If there
        are no callbacks, the timer is automatically stopped.
        """
        for func, args, kwargs in self.callbacks:
            ret = func(*args, **kwargs)
            # docstring above explains why we use `if ret == 0` here,
            # instead of `if not ret`.
            # This will also catch `ret == False` as `False == 0`
            # but does not annoy the linters
            # https://docs.python.org/3/library/stdtypes.html#boolean-values
            if ret == 0:
                self.callbacks.remove((func, args, kwargs))

        if len(self.callbacks) == 0:
            self.stop()


class Event:
    """
    A Matplotlib event.

    The following attributes are defined and shown with their default values.
    Subclasses may define additional attributes.

    Attributes
    ----------
    name : str
        The event name.
    canvas : `FigureCanvasBase`
        The backend-specific canvas instance generating the event.
    guiEvent
        The GUI event that triggered the Matplotlib event.
    """

    def __init__(self, name, canvas, guiEvent=None):
        self.name = name
        self.canvas = canvas
        self.guiEvent = guiEvent

    def _process(self):
        """Process this event on ``self.canvas``, then unset ``guiEvent``."""
        self.canvas.callbacks.process(self.name, self)
        self.guiEvent = None


class DrawEvent(Event):
    """
    An event triggered by a draw operation on the canvas.

    In most backends, callbacks subscribed to this event will be fired after
    the rendering is complete but before the screen is updated. Any extra
    artists drawn to the canvas's renderer will be reflected without an
    explicit call to ``blit``.

    .. warning::

       Calling ``canvas.draw`` and ``canvas.blit`` in these callbacks may
       not be safe with all backends and may cause infinite recursion.

    A DrawEvent has a number of special attributes in addition to those defined
    by the parent `Event` class.

    Attributes
    ----------
    renderer : `RendererBase`
        The renderer for the draw event.
    """
    def __init__(self, name, canvas, renderer):
        super().__init__(name, canvas)
        self.renderer = renderer


class ResizeEvent(Event):
    """
    An event triggered by a canvas resize.

    A ResizeEvent has a number of special attributes in addition to those
    defined by the parent `Event` class.

    Attributes
    ----------
    width : int
        Width of the canvas in pixels.
    height : int
        Height of the canvas in pixels.
    """

    def __init__(self, name, canvas):
        super().__init__(name, canvas)
        self.width, self.height = canvas.get_width_height()


class CloseEvent(Event):
    """An event triggered by a figure being closed."""


class LocationEvent(Event):
    """
    An event that has a screen location.

    A LocationEvent has a number of special attributes in addition to those
    defined by the parent `Event` class.

    Attributes
    ----------
    x, y : int or None
        Event location in pixels from bottom left of canvas.
    inaxes : `~matplotlib.axes.Axes` or None
        The `~.axes.Axes` instance over which the mouse is, if any.
    xdata, ydata : float or None
        Data coordinates of the mouse within *inaxes*, or *None* if the mouse
        is not over an Axes.
    modifiers : frozenset
        The keyboard modifiers currently being pressed (except for KeyEvent).
    """

    _last_axes_ref = None

    def __init__(self, name, canvas, x, y, guiEvent=None, *, modifiers=None):
        super().__init__(name, canvas, guiEvent=guiEvent)
        # x position - pixels from left of canvas
        self.x = int(x) if x is not None else x
        # y position - pixels from right of canvas
        self.y = int(y) if y is not None else y
        self.inaxes = None  # the Axes instance the mouse is over
        self.xdata = None   # x coord of mouse in data coords
        self.ydata = None   # y coord of mouse in data coords
        self.modifiers = frozenset(modifiers if modifiers is not None else [])

        if x is None or y is None:
            # cannot check if event was in Axes if no (x, y) info
            return

        self._set_inaxes(self.canvas.inaxes((x, y))
                         if self.canvas.mouse_grabber is None else
                         self.canvas.mouse_grabber,
                         (x, y))

    # Splitting _set_inaxes out is useful for the axes_leave_event handler: it
    # needs to generate synthetic LocationEvents with manually-set inaxes.  In
    # that latter case, xy has already been cast to int so it can directly be
    # read from self.x, self.y; in the normal case, however, it is more
    # accurate to pass the untruncated float x, y values passed to the ctor.

    def _set_inaxes(self, inaxes, xy=None):
        self.inaxes = inaxes
        if inaxes is not None:
            try:
                self.xdata, self.ydata = inaxes.transData.inverted().transform(
                    xy if xy is not None else (self.x, self.y))
            except ValueError:
                pass


class MouseButton(IntEnum):
    LEFT = 1
    MIDDLE = 2
    RIGHT = 3
    BACK = 8
    FORWARD = 9


class MouseEvent(LocationEvent):
    """
    A mouse event ('button_press_event', 'button_release_event', \
'scroll_event', 'motion_notify_event').

    A MouseEvent has a number of special attributes in addition to those
    defined by the parent `Event` and `LocationEvent` classes.

    Attributes
    ----------
    button : None or `MouseButton` or {'up', 'down'}
        The button pressed. 'up' and 'down' are used for scroll events.

        Note that LEFT and RIGHT actually refer to the "primary" and
        "secondary" buttons, i.e. if the user inverts their left and right
        buttons ("left-handed setting") then the LEFT button will be the one
        physically on the right.

        If this is unset, *name* is "scroll_event", and *step* is nonzero, then
        this will be set to "up" or "down" depending on the sign of *step*.

    buttons : None or frozenset
        For 'motion_notify_event', the mouse buttons currently being pressed
        (a set of zero or more MouseButtons);
        for other events, None.

        .. note::
           For 'motion_notify_event', this attribute is more accurate than
           the ``button`` (singular) attribute, which is obtained from the last
           'button_press_event' or 'button_release_event' that occurred within
           the canvas (and thus 1. be wrong if the last change in mouse state
           occurred when the canvas did not have focus, and 2. cannot report
           when multiple buttons are pressed).

           This attribute is not set for 'button_press_event' and
           'button_release_event' because GUI toolkits are inconsistent as to
           whether they report the button state *before* or *after* the
           press/release occurred.

        .. warning::
           On macOS, the Tk backends only report a single button even if
           multiple buttons are pressed.

    key : None or str
        The key pressed when the mouse event triggered, e.g. 'shift'.
        See `KeyEvent`.

        .. warning::
           This key is currently obtained from the last 'key_press_event' or
           'key_release_event' that occurred within the canvas.  Thus, if the
           last change of keyboard state occurred while the canvas did not have
           focus, this attribute will be wrong.  On the other hand, the
           ``modifiers`` attribute should always be correct, but it can only
           report on modifier keys.

    step : float
        The number of scroll steps (positive for 'up', negative for 'down').
        This applies only to 'scroll_event' and defaults to 0 otherwise.

    dblclick : bool
        Whether the event is a double-click. This applies only to
        'button_press_event' and is False otherwise. In particular, it's
        not used in 'button_release_event'.

    Examples
    --------
    ::

        def on_press(event):
            print('you pressed', event.button, event.xdata, event.ydata)

        cid = fig.canvas.mpl_connect('button_press_event', on_press)
    """

    def __init__(self, name, canvas, x, y, button=None, key=None,
                 step=0, dblclick=False, guiEvent=None, *,
                 buttons=None, modifiers=None):
        super().__init__(
            name, canvas, x, y, guiEvent=guiEvent, modifiers=modifiers)
        if button in MouseButton.__members__.values():
            button = MouseButton(button)
        if name == "scroll_event" and button is None:
            if step > 0:
                button = "up"
            elif step < 0:
                button = "down"
        self.button = button
        if name == "motion_notify_event":
            self.buttons = frozenset(buttons if buttons is not None else [])
        else:
            # We don't support 'buttons' for button_press/release_event because
            # toolkits are inconsistent as to whether they report the state
            # before or after the event.
            if buttons:
                raise ValueError(
                    "'buttons' is only supported for 'motion_notify_event'")
            self.buttons = None
        self.key = key
        self.step = step
        self.dblclick = dblclick

    def __str__(self):
        return (f"{self.name}: "
                f"xy=({self.x}, {self.y}) xydata=({self.xdata}, {self.ydata}) "
                f"button={self.button} dblclick={self.dblclick} "
                f"inaxes={self.inaxes}")


class PickEvent(Event):
    """
    A pick event.

    This event is fired when the user picks a location on the canvas
    sufficiently close to an artist that has been made pickable with
    `.Artist.set_picker`.

    A PickEvent has a number of special attributes in addition to those defined
    by the parent `Event` class.

    Attributes
    ----------
    mouseevent : `MouseEvent`
        The mouse event that generated the pick.
    artist : `~matplotlib.artist.Artist`
        The picked artist.  Note that artists are not pickable by default
        (see `.Artist.set_picker`).
    other
        Additional attributes may be present depending on the type of the
        picked object; e.g., a `.Line2D` pick may define different extra
        attributes than a `.PatchCollection` pick.

    Examples
    --------
    Bind a function ``on_pick()`` to pick events, that prints the coordinates
    of the picked data point::

        ax.plot(np.rand(100), 'o', picker=5)  # 5 points tolerance

        def on_pick(event):
            line = event.artist
            xdata, ydata = line.get_data()
            ind = event.ind
            print(f'on pick line: {xdata[ind]:.3f}, {ydata[ind]:.3f}')

        cid = fig.canvas.mpl_connect('pick_event', on_pick)
    """

    def __init__(self, name, canvas, mouseevent, artist,
                 guiEvent=None, **kwargs):
        if guiEvent is None:
            guiEvent = mouseevent.guiEvent
        super().__init__(name, canvas, guiEvent)
        self.mouseevent = mouseevent
        self.artist = artist
        self.__dict__.update(kwargs)


class KeyEvent(LocationEvent):
    """
    A key event (key press, key release).

    A KeyEvent has a number of special attributes in addition to those defined
    by the parent `Event` and `LocationEvent` classes.

    Attributes
    ----------
    key : None or str
        The key(s) pressed. Could be *None*, a single case sensitive Unicode
        character ("g", "G", "#", etc.), a special key ("control", "shift",
        "f1", "up", etc.) or a combination of the above (e.g., "ctrl+alt+g",
        "ctrl+alt+G").

    Notes
    -----
    Modifier keys will be prefixed to the pressed key and will be in the order
    "ctrl", "alt", "super". The exception to this rule is when the pressed key
    is itself a modifier key, therefore "ctrl+alt" and "alt+control" can both
    be valid key values.

    Examples
    --------
    ::

        def on_key(event):
            print('you pressed', event.key, event.xdata, event.ydata)

        cid = fig.canvas.mpl_connect('key_press_event', on_key)
    """

    def __init__(self, name, canvas, key, x=0, y=0, guiEvent=None):
        super().__init__(name, canvas, x, y, guiEvent=guiEvent)
        self.key = key


# Default callback for key events.
def _key_handler(event):
    # Dead reckoning of key.
    if event.name == "key_press_event":
        event.canvas._key = event.key
    elif event.name == "key_release_event":
        event.canvas._key = None


# Default callback for mouse events.
def _mouse_handler(event):
    # Dead-reckoning of button and key.
    if event.name == "button_press_event":
        event.canvas._button = event.button
    elif event.name == "button_release_event":
        event.canvas._button = None
    elif event.name == "motion_notify_event" and event.button is None:
        event.button = event.canvas._button
    if event.key is None:
        event.key = event.canvas._key
    # Emit axes_enter/axes_leave.
    if event.name == "motion_notify_event":
        last_ref = LocationEvent._last_axes_ref
        last_axes = last_ref() if last_ref else None
        if last_axes != event.inaxes:
            if last_axes is not None:
                # Create a synthetic LocationEvent for the axes_leave_event.
                # Its inaxes attribute needs to be manually set (because the
                # cursor is actually *out* of that Axes at that point); this is
                # done with the internal _set_inaxes method which ensures that
                # the xdata and ydata attributes are also correct.
                try:
                    canvas = last_axes.get_figure(root=True).canvas
                    leave_event = LocationEvent(
                        "axes_leave_event", canvas,
                        event.x, event.y, event.guiEvent,
                        modifiers=event.modifiers)
                    leave_event._set_inaxes(last_axes)
                    canvas.callbacks.process("axes_leave_event", leave_event)
                except Exception:
                    pass  # The last canvas may already have been torn down.
            if event.inaxes is not None:
                event.canvas.callbacks.process("axes_enter_event", event)
        LocationEvent._last_axes_ref = (
            weakref.ref(event.inaxes) if event.inaxes else None)


def _get_renderer(figure, print_method=None):
    """
    Get the renderer that would be used to save a `.Figure`.

    If you need a renderer without any active draw methods use
    renderer._draw_disabled to temporary patch them out at your call site.
    """
    # This is implemented by triggering a draw, then immediately jumping out of
    # Figure.draw() by raising an exception.

    class Done(Exception):
        pass

    def _draw(renderer): raise Done(renderer)

    with cbook._setattr_cm(figure, draw=_draw), ExitStack() as stack:
        if print_method is None:
            fmt = figure.canvas.get_default_filetype()
            # Even for a canvas' default output type, a canvas switch may be
            # needed, e.g. for FigureCanvasBase.
            print_method = stack.enter_context(
                figure.canvas._switch_canvas_and_return_print_method(fmt))
        try:
            print_method(io.BytesIO())
        except Done as exc:
            renderer, = exc.args
            return renderer
        else:
            raise RuntimeError(f"{print_method} did not call Figure.draw, so "
                               f"no renderer is available")


def _no_output_draw(figure):
    # _no_output_draw was promoted to the figure level, but
    # keep this here in case someone was calling it...
    figure.draw_without_rendering()


def _is_non_interactive_terminal_ipython(ip):
    """
    Return whether we are in a terminal IPython, but non interactive.

    When in _terminal_ IPython, ip.parent will have and `interact` attribute,
    if this attribute is False we do not setup eventloop integration as the
    user will _not_ interact with IPython. In all other case (ZMQKernel, or is
    interactive), we do.
    """
    return (hasattr(ip, 'parent')
            and (ip.parent is not None)
            and getattr(ip.parent, 'interact', None) is False)


@contextmanager
def _allow_interrupt(prepare_notifier, handle_sigint):
    """
    A context manager that allows terminating a plot by sending a SIGINT.  It
    is necessary because the running backend prevents the Python interpreter
    from running and processing signals (i.e., to raise a KeyboardInterrupt).
    To solve this, one needs to somehow wake up the interpreter and make it
    close the plot window.  We do this by using the signal.set_wakeup_fd()
    function which organizes a write of the signal number into a socketpair.
    A backend-specific function, *prepare_notifier*, arranges to listen to
    the pair's read socket while the event loop is running.  (If it returns a
    notifier object, that object is kept alive while the context manager runs.)

    If SIGINT was indeed caught, after exiting the on_signal() function the
    interpreter reacts to the signal according to the handler function which
    had been set up by a signal.signal() call; here, we arrange to call the
    backend-specific *handle_sigint* function.  Finally, we call the old SIGINT
    handler with the same arguments that were given to our custom handler.

    We do this only if the old handler for SIGINT was not None, which means
    that a non-python handler was installed, i.e. in Julia, and not SIG_IGN
    which means we should ignore the interrupts.

    Parameters
    ----------
    prepare_notifier : Callable[[socket.socket], object]
    handle_sigint : Callable[[], object]
    """

    old_sigint_handler = signal.getsignal(signal.SIGINT)
    if old_sigint_handler in (None, signal.SIG_IGN, signal.SIG_DFL):
        yield
        return

    handler_args = None
    wsock, rsock = socket.socketpair()
    wsock.setblocking(False)
    rsock.setblocking(False)
    old_wakeup_fd = signal.set_wakeup_fd(wsock.fileno())
    notifier = prepare_notifier(rsock)

    def save_args_and_handle_sigint(*args):
        nonlocal handler_args
        handler_args = args
        handle_sigint()

    signal.signal(signal.SIGINT, save_args_and_handle_sigint)
    try:
        yield
    finally:
        wsock.close()
        rsock.close()
        signal.set_wakeup_fd(old_wakeup_fd)
        signal.signal(signal.SIGINT, old_sigint_handler)
        if handler_args is not None:
            old_sigint_handler(*handler_args)


class FigureCanvasBase:
    """
    The canvas the figure renders into.

    Attributes
    ----------
    figure : `~matplotlib.figure.Figure`
        A high-level figure instance.
    """

    # Set to one of {"qt", "gtk3", "gtk4", "wx", "tk", "macosx"} if an
    # interactive framework is required, or None otherwise.
    required_interactive_framework = None

    # The manager class instantiated by new_manager.
    # (This is defined as a classproperty because the manager class is
    # currently defined *after* the canvas class, but one could also assign
    # ``FigureCanvasBase.manager_class = FigureManagerBase``
    # after defining both classes.)
    manager_class = _api.classproperty(lambda cls: FigureManagerBase)

    events = [
        'resize_event',
        'draw_event',
        'key_press_event',
        'key_release_event',
        'button_press_event',
        'button_release_event',
        'scroll_event',
        'motion_notify_event',
        'pick_event',
        'figure_enter_event',
        'figure_leave_event',
        'axes_enter_event',
        'axes_leave_event',
        'close_event'
    ]

    fixed_dpi = None

    filetypes = _default_filetypes

    @_api.classproperty
    def supports_blit(cls):
        """If this Canvas sub-class supports blitting."""
        return (hasattr(cls, "copy_from_bbox")
                and hasattr(cls, "restore_region"))

    def __init__(self, figure=None):
        from matplotlib.figure import Figure
        self._fix_ipython_backend2gui()
        self._is_idle_drawing = True
        self._is_saving = False
        if figure is None:
            figure = Figure()
        figure.set_canvas(self)
        self.figure = figure
        self.manager = None
        self.widgetlock = widgets.LockDraw()
        self._button = None  # the button pressed
        self._key = None  # the key pressed
        self.mouse_grabber = None  # the Axes currently grabbing mouse
        self.toolbar = None  # NavigationToolbar2 will set me
        self._is_idle_drawing = False
        # We don't want to scale up the figure DPI more than once.
        figure._original_dpi = figure.dpi
        self._device_pixel_ratio = 1
        super().__init__()  # Typically the GUI widget init (if any).

    callbacks = property(lambda self: self.figure._canvas_callbacks)
    button_pick_id = property(lambda self: self.figure._button_pick_id)
    scroll_pick_id = property(lambda self: self.figure._scroll_pick_id)

    @classmethod
    @functools.cache
    def _fix_ipython_backend2gui(cls):
        # Fix hard-coded module -> toolkit mapping in IPython (used for
        # `ipython --auto`).  This cannot be done at import time due to
        # ordering issues, so we do it when creating a canvas, and should only
        # be done once per class (hence the `cache`).

        # This function will not be needed when Python 3.12, the latest version
        # supported by IPython < 8.24, reaches end-of-life in late 2028.
        # At that time this function can be made a no-op and deprecated.
        mod_ipython = sys.modules.get("IPython")
        if mod_ipython is None or mod_ipython.version_info[:2] >= (8, 24):
            # Use of backend2gui is not needed for IPython >= 8.24 as the
            # functionality has been moved to Matplotlib.
            return

        import IPython
        ip = IPython.get_ipython()
        if not ip:
            return
        from IPython.core import pylabtools as pt
        if (not hasattr(pt, "backend2gui")
                or not hasattr(ip, "enable_matplotlib")):
            # In case we ever move the patch to IPython and remove these APIs,
            # don't break on our side.
            return
        backend2gui_rif = {
            "qt": "qt",
            "gtk3": "gtk3",
            "gtk4": "gtk4",
            "wx": "wx",
            "macosx": "osx",
        }.get(cls.required_interactive_framework)
        if backend2gui_rif:
            if _is_non_interactive_terminal_ipython(ip):
                ip.enable_gui(backend2gui_rif)

    @classmethod
    def new_manager(cls, figure, num):
        """
        Create a new figure manager for *figure*, using this canvas class.

        Notes
        -----
        This method should not be reimplemented in subclasses.  If
        custom manager creation logic is needed, please reimplement
        ``FigureManager.create_with_canvas``.
        """
        return cls.manager_class.create_with_canvas(cls, figure, num)

    @contextmanager
    def _idle_draw_cntx(self):
        self._is_idle_drawing = True
        try:
            yield
        finally:
            self._is_idle_drawing = False

    def is_saving(self):
        """
        Return whether the renderer is in the process of saving
        to a file, rather than rendering for an on-screen buffer.
        """
        return self._is_saving

    def blit(self, bbox=None):
        """Blit the canvas in bbox (default entire canvas)."""

    def inaxes(self, xy):
        """
        Return the topmost visible `~.axes.Axes` containing the point *xy*.

        Parameters
        ----------
        xy : (float, float)
            (x, y) pixel positions from left/bottom of the canvas.

        Returns
        -------
        `~matplotlib.axes.Axes` or None
            The topmost visible Axes containing the point, or None if there
            is no Axes at the point.
        """
        axes_list = [a for a in self.figure.get_axes()
                     if a.patch.contains_point(xy) and a.get_visible()]
        if axes_list:
            axes = cbook._topmost_artist(axes_list)
        else:
            axes = None

        return axes

    def grab_mouse(self, ax):
        """
        Set the child `~.axes.Axes` which is grabbing the mouse events.

        Usually called by the widgets themselves. It is an error to call this
        if the mouse is already grabbed by another Axes.
        """
        if self.mouse_grabber not in (None, ax):
            raise RuntimeError("Another Axes already grabs mouse input")
        self.mouse_grabber = ax

    def release_mouse(self, ax):
        """
        Release the mouse grab held by the `~.axes.Axes` *ax*.

        Usually called by the widgets. It is ok to call this even if *ax*
        doesn't have the mouse grab currently.
        """
        if self.mouse_grabber is ax:
            self.mouse_grabber = None

    def set_cursor(self, cursor):
        """
        Set the current cursor.

        This may have no effect if the backend does not display anything.

        If required by the backend, this method should trigger an update in
        the backend event loop after the cursor is set, as this method may be
        called e.g. before a long-running task during which the GUI is not
        updated.

        Parameters
        ----------
        cursor : `.Cursors`
            The cursor to display over the canvas. Note: some backends may
            change the cursor for the entire window.
        """

    def draw(self, *args, **kwargs):
        """
        Render the `.Figure`.

        This method must walk the artist tree, even if no output is produced,
        because it triggers deferred work that users may want to access
        before saving output to disk. For example computing limits,
        auto-limits, and tick values.
        """

    def draw_idle(self, *args, **kwargs):
        """
        Request a widget redraw once control returns to the GUI event loop.

        Even if multiple calls to `draw_idle` occur before control returns
        to the GUI event loop, the figure will only be rendered once.

        Notes
        -----
        Backends may choose to override the method and implement their own
        strategy to prevent multiple renderings.

        """
        if not self._is_idle_drawing:
            with self._idle_draw_cntx():
                self.draw(*args, **kwargs)

    @property
    def device_pixel_ratio(self):
        """
        The ratio of physical to logical pixels used for the canvas on screen.

        By default, this is 1, meaning physical and logical pixels are the same
        size. Subclasses that support High DPI screens may set this property to
        indicate that said ratio is different. All Matplotlib interaction,
        unless working directly with the canvas, remains in logical pixels.

        """
        return self._device_pixel_ratio

    def _set_device_pixel_ratio(self, ratio):
        """
        Set the ratio of physical to logical pixels used for the canvas.

        Subclasses that support High DPI screens can set this property to
        indicate that said ratio is different. The canvas itself will be
        created at the physical size, while the client side will use the
        logical size. Thus the DPI of the Figure will change to be scaled by
        this ratio. Implementations that support High DPI screens should use
        physical pixels for events so that transforms back to Axes space are
        correct.

        By default, this is 1, meaning physical and logical pixels are the same
        size.

        Parameters
        ----------
        ratio : float
            The ratio of logical to physical pixels used for the canvas.

        Returns
        -------
        bool
            Whether the ratio has changed. Backends may interpret this as a
            signal to resize the window, repaint the canvas, or change any
            other relevant properties.
        """
        if self._device_pixel_ratio == ratio:
            return False
        # In cases with mixed resolution displays, we need to be careful if the
        # device pixel ratio changes - in this case we need to resize the
        # canvas accordingly. Some backends provide events that indicate a
        # change in DPI, but those that don't will update this before drawing.
        dpi = ratio * self.figure._original_dpi
        self.figure._set_dpi(dpi, forward=False)
        self._device_pixel_ratio = ratio
        return True

    def get_width_height(self, *, physical=False):
        """
        Return the figure width and height in integral points or pixels.

        When the figure is used on High DPI screens (and the backend supports
        it), the truncation to integers occurs after scaling by the device
        pixel ratio.

        Parameters
        ----------
        physical : bool, default: False
            Whether to return true physical pixels or logical pixels. Physical
            pixels may be used by backends that support HiDPI, but still
            configure the canvas using its actual size.

        Returns
        -------
        width, height : int
            The size of the figure, in points or pixels, depending on the
            backend.
        """
        return tuple(int(size / (1 if physical else self.device_pixel_ratio))
                     for size in self.figure.bbox.max)

    @classmethod
    def get_supported_filetypes(cls):
        """Return dict of savefig file formats supported by this backend."""
        return cls.filetypes

    @classmethod
    def get_supported_filetypes_grouped(cls):
        """
        Return a dict of savefig file formats supported by this backend,
        where the keys are a file type name, such as 'Joint Photographic
        Experts Group', and the values are a list of filename extensions used
        for that filetype, such as ['jpg', 'jpeg'].
        """
        groupings = {}
        for ext, name in cls.filetypes.items():
            groupings.setdefault(name, []).append(ext)
            groupings[name].sort()
        return groupings

    @contextmanager
    def _switch_canvas_and_return_print_method(self, fmt, backend=None):
        """
        Context manager temporarily setting the canvas for saving the figure::

            with (canvas._switch_canvas_and_return_print_method(fmt, backend)
                  as print_method):
                # ``print_method`` is a suitable ``print_{fmt}`` method, and
                # the figure's canvas is temporarily switched to the method's
                # canvas within the with... block.  ``print_method`` is also
                # wrapped to suppress extra kwargs passed by ``print_figure``.

        Parameters
        ----------
        fmt : str
            If *backend* is None, then determine a suitable canvas class for
            saving to format *fmt* -- either the current canvas class, if it
            supports *fmt*, or whatever `get_registered_canvas_class` returns;
            switch the figure canvas to that canvas class.
        backend : str or None, default: None
            If not None, switch the figure canvas to the ``FigureCanvas`` class
            of the given backend.
        """
        canvas = None
        if backend is not None:
            # Return a specific canvas class, if requested.
            from .backends.registry import backend_registry
            canvas_class = backend_registry.load_backend_module(backend).FigureCanvas
            if not hasattr(canvas_class, f"print_{fmt}"):
                raise ValueError(
                    f"The {backend!r} backend does not support {fmt} output")
            canvas = canvas_class(self.figure)
        elif hasattr(self, f"print_{fmt}"):
            # Return the current canvas if it supports the requested format.
            canvas = self
        else:
            # Return a default canvas for the requested format, if it exists.
            canvas_class = get_registered_canvas_class(fmt)
            if canvas_class is None:
                raise ValueError(
                    "Format {!r} is not supported (supported formats: {})".format(
                        fmt, ", ".join(sorted(self.get_supported_filetypes()))))
            canvas = canvas_class(self.figure)
        canvas._is_saving = self._is_saving
        meth = getattr(canvas, f"print_{fmt}")
        mod = (meth.func.__module__
               if hasattr(meth, "func")  # partialmethod, e.g. backend_wx.
               else meth.__module__)
        if mod.startswith(("matplotlib.", "mpl_toolkits.")):
            optional_kws = {  # Passed by print_figure for other renderers.
                "dpi", "facecolor", "edgecolor", "orientation",
                "bbox_inches_restore"}
            skip = optional_kws - {*inspect.signature(meth).parameters}
            print_method = functools.wraps(meth)(lambda *args, **kwargs: meth(
                *args, **{k: v for k, v in kwargs.items() if k not in skip}))
        else:  # Let third-parties do as they see fit.
            print_method = meth
        try:
            yield print_method
        finally:
            self.figure.canvas = self

    def print_figure(
            self, filename, dpi=None, facecolor=None, edgecolor=None,
            orientation='portrait', format=None, *,
            bbox_inches=None, pad_inches=None, bbox_extra_artists=None,
            backend=None, **kwargs):
        """
        Render the figure to hardcopy. Set the figure patch face and edge
        colors.  This is useful because some of the GUIs have a gray figure
        face color background and you'll probably want to override this on
        hardcopy.

        Parameters
        ----------
        filename : str or path-like or file-like
            The file where the figure is saved.

        dpi : float, default: :rc:`savefig.dpi`
            The dots per inch to save the figure in.

        facecolor : :mpltype:`color` or 'auto', default: :rc:`savefig.facecolor`
            The facecolor of the figure.  If 'auto', use the current figure
            facecolor.

        edgecolor : :mpltype:`color` or 'auto', default: :rc:`savefig.edgecolor`
            The edgecolor of the figure.  If 'auto', use the current figure
            edgecolor.

        orientation : {'landscape', 'portrait'}, default: 'portrait'
            Only currently applies to PostScript printing.

        format : str, optional
            Force a specific file format. If not given, the format is inferred
            from the *filename* extension, and if that fails from
            :rc:`savefig.format`.

        bbox_inches : 'tight' or `.Bbox`, default: :rc:`savefig.bbox`
            Bounding box in inches: only the given portion of the figure is
            saved.  If 'tight', try to figure out the tight bbox of the figure.

        pad_inches : float or 'layout', default: :rc:`savefig.pad_inches`
            Amount of padding in inches around the figure when bbox_inches is
            'tight'. If 'layout' use the padding from the constrained or
            compressed layout engine; ignored if one of those engines is not in
            use.

        bbox_extra_artists : list of `~matplotlib.artist.Artist`, optional
            A list of extra artists that will be considered when the
            tight bbox is calculated.

        backend : str, optional
            Use a non-default backend to render the file, e.g. to render a
            png file with the "cairo" backend rather than the default "agg",
            or a pdf file with the "pgf" backend rather than the default
            "pdf".  Note that the default backend is normally sufficient.  See
            :ref:`the-builtin-backends` for a list of valid backends for each
            file format.  Custom backends can be referenced as "module://...".
        """
        if format is None:
            # get format from filename, or from backend's default filetype
            if isinstance(filename, os.PathLike):
                filename = os.fspath(filename)
            if isinstance(filename, str):
                format = os.path.splitext(filename)[1][1:]
            if format is None or format == '':
                format = self.get_default_filetype()
                if isinstance(filename, str):
                    filename = filename.rstrip('.') + '.' + format
        format = format.lower()

        if dpi is None:
            dpi = rcParams['savefig.dpi']
        if dpi == 'figure':
            dpi = getattr(self.figure, '_original_dpi', self.figure.dpi)

        # Remove the figure manager, if any, to avoid resizing the GUI widget.
        with (cbook._setattr_cm(self, manager=None),
              self._switch_canvas_and_return_print_method(format, backend)
                 as print_method,
              cbook._setattr_cm(self.figure, dpi=dpi),
              cbook._setattr_cm(self.figure.canvas, _device_pixel_ratio=1),
              cbook._setattr_cm(self.figure.canvas, _is_saving=True),
              ExitStack() as stack):

            for prop in ["facecolor", "edgecolor"]:
                color = locals()[prop]
                if color is None:
                    color = rcParams[f"savefig.{prop}"]
                if not cbook._str_equal(color, "auto"):
                    stack.enter_context(self.figure._cm_set(**{prop: color}))

            if bbox_inches is None:
                bbox_inches = rcParams['savefig.bbox']

            layout_engine = self.figure.get_layout_engine()
            if layout_engine is not None or bbox_inches == "tight":
                # we need to trigger a draw before printing to make sure
                # CL works.  "tight" also needs a draw to get the right
                # locations:
                renderer = _get_renderer(
                    self.figure,
                    functools.partial(
                        print_method, orientation=orientation)
                )
                # we do this instead of `self.figure.draw_without_rendering`
                # so that we can inject the orientation
                with getattr(renderer, "_draw_disabled", nullcontext)():
                    self.figure.draw(renderer)
            if bbox_inches:
                if bbox_inches == "tight":
                    bbox_inches = self.figure.get_tightbbox(
                        renderer, bbox_extra_artists=bbox_extra_artists)
                    if (isinstance(layout_engine, ConstrainedLayoutEngine) and
                            pad_inches == "layout"):
                        h_pad = layout_engine.get()["h_pad"]
                        w_pad = layout_engine.get()["w_pad"]
                    else:
                        if pad_inches in [None, "layout"]:
                            pad_inches = rcParams['savefig.pad_inches']
                        h_pad = w_pad = pad_inches
                    bbox_inches = bbox_inches.padded(w_pad, h_pad)

                # call adjust_bbox to save only the given area
                restore_bbox = _tight_bbox.adjust_bbox(
                    self.figure, bbox_inches, self.figure.canvas.fixed_dpi)

                _bbox_inches_restore = (bbox_inches, restore_bbox)
            else:
                _bbox_inches_restore = None

            # we have already done layout above, so turn it off:
            stack.enter_context(self.figure._cm_set(layout_engine='none'))
            try:
                # _get_renderer may change the figure dpi (as vector formats
                # force the figure dpi to 72), so we need to set it again here.
                with cbook._setattr_cm(self.figure, dpi=dpi):
                    result = print_method(
                        filename,
                        facecolor=facecolor,
                        edgecolor=edgecolor,
                        orientation=orientation,
                        bbox_inches_restore=_bbox_inches_restore,
                        **kwargs)
            finally:
                if bbox_inches and restore_bbox:
                    restore_bbox()

            return result

    @classmethod
    def get_default_filetype(cls):
        """
        Return the default savefig file format as specified in
        :rc:`savefig.format`.

        The returned string does not include a period. This method is
        overridden in backends that only support a single file type.
        """
        return rcParams['savefig.format']

    def get_default_filename(self):
        """
        Return a suitable default filename, including the extension.
        """
        default_basename = (
            self.manager.get_window_title()
            if self.manager is not None
            else ''
        )
        default_basename = default_basename or 'image'
        # Characters to be avoided in a NT path:
        # https://msdn.microsoft.com/en-us/library/windows/desktop/aa365247(v=vs.85).aspx#naming_conventions
        # plus ' '
        removed_chars = '<>:"/\\|?*\0 '
        default_basename = default_basename.translate(
            {ord(c): "_" for c in removed_chars})
        default_filetype = self.get_default_filetype()
        return f'{default_basename}.{default_filetype}'

    def mpl_connect(self, s, func):
        """
        Bind function *func* to event *s*.

        Parameters
        ----------
        s : str
            One of the following events ids:

            - 'button_press_event'
            - 'button_release_event'
            - 'draw_event'
            - 'key_press_event'
            - 'key_release_event'
            - 'motion_notify_event'
            - 'pick_event'
            - 'resize_event'
            - 'scroll_event'
            - 'figure_enter_event',
            - 'figure_leave_event',
            - 'axes_enter_event',
            - 'axes_leave_event'
            - 'close_event'.

        func : callable
            The callback function to be executed, which must have the
            signature::

                def func(event: Event) -> Any

            For the location events (button and key press/release), if the
            mouse is over the Axes, the ``inaxes`` attribute of the event will
            be set to the `~matplotlib.axes.Axes` the event occurs is over, and
            additionally, the variables ``xdata`` and ``ydata`` attributes will
            be set to the mouse location in data coordinates.  See `.KeyEvent`
            and `.MouseEvent` for more info.

            .. note::

                If func is a method, this only stores a weak reference to the
                method. Thus, the figure does not influence the lifetime of
                the associated object. Usually, you want to make sure that the
                object is kept alive throughout the lifetime of the figure by
                holding a reference to it.

        Returns
        -------
        cid
            A connection id that can be used with
            `.FigureCanvasBase.mpl_disconnect`.

        Examples
        --------
        ::

            def on_press(event):
                print('you pressed', event.button, event.xdata, event.ydata)

            cid = canvas.mpl_connect('button_press_event', on_press)
        """

        return self.callbacks.connect(s, func)

    def mpl_disconnect(self, cid):
        """
        Disconnect the callback with id *cid*.

        Examples
        --------
        ::

            cid = canvas.mpl_connect('button_press_event', on_press)
            # ... later
            canvas.mpl_disconnect(cid)
        """
        self.callbacks.disconnect(cid)

    # Internal subclasses can override _timer_cls instead of new_timer, though
    # this is not a public API for third-party subclasses.
    _timer_cls = TimerBase

    def new_timer(self, interval=None, callbacks=None):
        """
        Create a new backend-specific subclass of `.Timer`.

        This is useful for getting periodic events through the backend's native
        event loop.  Implemented only for backends with GUIs.

        Parameters
        ----------
        interval : int
            Timer interval in milliseconds.

        callbacks : list[tuple[callable, tuple, dict]]
            Sequence of (func, args, kwargs) where ``func(*args, **kwargs)``
            will be executed by the timer every *interval*.

            Callbacks which return ``False`` or ``0`` will be removed from the
            timer.

        Examples
        --------
        >>> timer = fig.canvas.new_timer(callbacks=[(f1, (1,), {'a': 3})])
        """
        return self._timer_cls(interval=interval, callbacks=callbacks)

    def flush_events(self):
        """
        Flush the GUI events for the figure.

        Interactive backends need to reimplement this method.
        """

    def start_event_loop(self, timeout=0):
        """
        Start a blocking event loop.

        Such an event loop is used by interactive functions, such as
        `~.Figure.ginput` and `~.Figure.waitforbuttonpress`, to wait for
        events.

        The event loop blocks until a callback function triggers
        `stop_event_loop`, or *timeout* is reached.

        If *timeout* is 0 or negative, never timeout.

        Only interactive backends need to reimplement this method and it relies
        on `flush_events` being properly implemented.

        Interactive backends should implement this in a more native way.
        """
        if timeout <= 0:
            timeout = np.inf
        timestep = 0.01
        counter = 0
        self._looping = True
        while self._looping and counter * timestep < timeout:
            self.flush_events()
            time.sleep(timestep)
            counter += 1

    def stop_event_loop(self):
        """
        Stop the current blocking event loop.

        Interactive backends need to reimplement this to match
        `start_event_loop`
        """
        self._looping = False


def key_press_handler(event, canvas=None, toolbar=None):
    """
    Implement the default Matplotlib key bindings for the canvas and toolbar
    described at :ref:`key-event-handling`.

    Parameters
    ----------
    event : `KeyEvent`
        A key press/release event.
    canvas : `FigureCanvasBase`, default: ``event.canvas``
        The backend-specific canvas instance.  This parameter is kept for
        back-compatibility, but, if set, should always be equal to
        ``event.canvas``.
    toolbar : `NavigationToolbar2`, default: ``event.canvas.toolbar``
        The navigation cursor toolbar.  This parameter is kept for
        back-compatibility, but, if set, should always be equal to
        ``event.canvas.toolbar``.
    """
    if event.key is None:
        return
    if canvas is None:
        canvas = event.canvas
    if toolbar is None:
        toolbar = canvas.toolbar

    # toggle fullscreen mode (default key 'f', 'ctrl + f')
    if event.key in rcParams['keymap.fullscreen']:
        try:
            canvas.manager.full_screen_toggle()
        except AttributeError:
            pass

    # quit the figure (default key 'ctrl+w')
    if event.key in rcParams['keymap.quit']:
        Gcf.destroy_fig(canvas.figure)
    if event.key in rcParams['keymap.quit_all']:
        Gcf.destroy_all()

    if toolbar is not None:
        # home or reset mnemonic  (default key 'h', 'home' and 'r')
        if event.key in rcParams['keymap.home']:
            toolbar.home()
        # forward / backward keys to enable left handed quick navigation
        # (default key for backward: 'left', 'backspace' and 'c')
        elif event.key in rcParams['keymap.back']:
            toolbar.back()
        # (default key for forward: 'right' and 'v')
        elif event.key in rcParams['keymap.forward']:
            toolbar.forward()
        # pan mnemonic (default key 'p')
        elif event.key in rcParams['keymap.pan']:
            toolbar.pan()
            toolbar._update_cursor(event)
        # zoom mnemonic (default key 'o')
        elif event.key in rcParams['keymap.zoom']:
            toolbar.zoom()
            toolbar._update_cursor(event)
        # saving current figure (default key 's')
        elif event.key in rcParams['keymap.save']:
            toolbar.save_figure()

    if event.inaxes is None:
        return

    # these bindings require the mouse to be over an Axes to trigger
    def _get_uniform_gridstate(ticks):
        # Return True/False if all grid lines are on or off, None if they are
        # not all in the same state.
        return (True if all(tick.gridline.get_visible() for tick in ticks) else
                False if not any(tick.gridline.get_visible() for tick in ticks) else
                None)

    ax = event.inaxes
    # toggle major grids in current Axes (default key 'g')
    # Both here and below (for 'G'), we do nothing if *any* grid (major or
    # minor, x or y) is not in a uniform state, to avoid messing up user
    # customization.
    if (event.key in rcParams['keymap.grid']
            # Exclude minor grids not in a uniform state.
            and None not in [_get_uniform_gridstate(ax.xaxis.minorTicks),
                             _get_uniform_gridstate(ax.yaxis.minorTicks)]):
        x_state = _get_uniform_gridstate(ax.xaxis.majorTicks)
        y_state = _get_uniform_gridstate(ax.yaxis.majorTicks)
        cycle = [(False, False), (True, False), (True, True), (False, True)]
        try:
            x_state, y_state = (
                cycle[(cycle.index((x_state, y_state)) + 1) % len(cycle)])
        except ValueError:
            # Exclude major grids not in a uniform state.
            pass
        else:
            # If turning major grids off, also turn minor grids off.
            ax.grid(x_state, which="major" if x_state else "both", axis="x")
            ax.grid(y_state, which="major" if y_state else "both", axis="y")
            canvas.draw_idle()
    # toggle major and minor grids in current Axes (default key 'G')
    if (event.key in rcParams['keymap.grid_minor']
            # Exclude major grids not in a uniform state.
            and None not in [_get_uniform_gridstate(ax.xaxis.majorTicks),
                             _get_uniform_gridstate(ax.yaxis.majorTicks)]):
        x_state = _get_uniform_gridstate(ax.xaxis.minorTicks)
        y_state = _get_uniform_gridstate(ax.yaxis.minorTicks)
        cycle = [(False, False), (True, False), (True, True), (False, True)]
        try:
            x_state, y_state = (
                cycle[(cycle.index((x_state, y_state)) + 1) % len(cycle)])
        except ValueError:
            # Exclude minor grids not in a uniform state.
            pass
        else:
            ax.grid(x_state, which="both", axis="x")
            ax.grid(y_state, which="both", axis="y")
            canvas.draw_idle()
    # toggle scaling of y-axes between 'log and 'linear' (default key 'l')
    elif event.key in rcParams['keymap.yscale']:
        scale = ax.get_yscale()
        if scale == 'log':
            ax.set_yscale('linear')
            ax.get_figure(root=True).canvas.draw_idle()
        elif scale == 'linear':
            try:
                ax.set_yscale('log')
            except ValueError as exc:
                _log.warning(str(exc))
                ax.set_yscale('linear')
            ax.get_figure(root=True).canvas.draw_idle()
    # toggle scaling of x-axes between 'log and 'linear' (default key 'k')
    elif event.key in rcParams['keymap.xscale']:
        scalex = ax.get_xscale()
        if scalex == 'log':
            ax.set_xscale('linear')
            ax.get_figure(root=True).canvas.draw_idle()
        elif scalex == 'linear':
            try:
                ax.set_xscale('log')
            except ValueError as exc:
                _log.warning(str(exc))
                ax.set_xscale('linear')
            ax.get_figure(root=True).canvas.draw_idle()


def button_press_handler(event, canvas=None, toolbar=None):
    """
    The default Matplotlib button actions for extra mouse buttons.

    Parameters are as for `key_press_handler`, except that *event* is a
    `MouseEvent`.
    """
    if canvas is None:
        canvas = event.canvas
    if toolbar is None:
        toolbar = canvas.toolbar
    if toolbar is not None:
        button_name = str(MouseButton(event.button))
        if button_name in rcParams['keymap.back']:
            toolbar.back()
        elif button_name in rcParams['keymap.forward']:
            toolbar.forward()


class NonGuiException(Exception):
    """Raised when trying show a figure in a non-GUI backend."""
    pass


class FigureManagerBase:
    """
    A backend-independent abstraction of a figure container and controller.

    The figure manager is used by pyplot to interact with the window in a
    backend-independent way. It's an adapter for the real (GUI) framework that
    represents the visual figure on screen.

    The figure manager is connected to a specific canvas instance, which in turn
    is connected to a specific figure instance. To access a figure manager for
    a given figure in user code, you typically use ``fig.canvas.manager``.

    GUI backends derive from this class to translate common operations such
    as *show* or *resize* to the GUI-specific code. Non-GUI backends do not
    support these operations and can just use the base class.

    This following basic operations are accessible:

    **Window operations**

    - `~.FigureManagerBase.show`
    - `~.FigureManagerBase.destroy`
    - `~.FigureManagerBase.full_screen_toggle`
    - `~.FigureManagerBase.resize`
    - `~.FigureManagerBase.get_window_title`
    - `~.FigureManagerBase.set_window_title`

    **Key and mouse button press handling**

    The figure manager sets up default key and mouse button press handling by
    hooking up the `.key_press_handler` to the matplotlib event system. This
    ensures the same shortcuts and mouse actions across backends.

    **Other operations**

    Subclasses will have additional attributes and functions to access
    additional functionality. This is of course backend-specific. For example,
    most GUI backends have ``window`` and ``toolbar`` attributes that give
    access to the native GUI widgets of the respective framework.

    Attributes
    ----------
    canvas : `FigureCanvasBase`
        The backend-specific canvas instance.

    num : int or str
        The figure number.

    key_press_handler_id : int
        The default key handler cid, when using the toolmanager.
        To disable the default key press handling use::

            figure.canvas.mpl_disconnect(
                figure.canvas.manager.key_press_handler_id)

    button_press_handler_id : int
        The default mouse button handler cid, when using the toolmanager.
        To disable the default button press handling use::

            figure.canvas.mpl_disconnect(
                figure.canvas.manager.button_press_handler_id)
    """

    _toolbar2_class = None
    _toolmanager_toolbar_class = None

    def __init__(self, canvas, num):
        self.canvas = canvas
        canvas.manager = self  # store a pointer to parent
        self.num = num
        self.set_window_title(f"Figure {num:d}")

        self.key_press_handler_id = None
        self.button_press_handler_id = None
        if rcParams['toolbar'] != 'toolmanager':
            self.key_press_handler_id = self.canvas.mpl_connect(
                'key_press_event', key_press_handler)
            self.button_press_handler_id = self.canvas.mpl_connect(
                'button_press_event', button_press_handler)

        self.toolmanager = (ToolManager(canvas.figure)
                            if mpl.rcParams['toolbar'] == 'toolmanager'
                            else None)
        if (mpl.rcParams["toolbar"] == "toolbar2"
                and self._toolbar2_class):
            self.toolbar = self._toolbar2_class(self.canvas)
        elif (mpl.rcParams["toolbar"] == "toolmanager"
                and self._toolmanager_toolbar_class):
            self.toolbar = self._toolmanager_toolbar_class(self.toolmanager)
        else:
            self.toolbar = None

        if self.toolmanager:
            tools.add_tools_to_manager(self.toolmanager)
            if self.toolbar:
                tools.add_tools_to_container(self.toolbar)

        @self.canvas.figure.add_axobserver
        def notify_axes_change(fig):
            # Called whenever the current Axes is changed.
            if self.toolmanager is None and self.toolbar is not None:
                self.toolbar.update()

    @classmethod
    def create_with_canvas(cls, canvas_class, figure, num):
        """
        Create a manager for a given *figure* using a specific *canvas_class*.

        Backends should override this method if they have specific needs for
        setting up the canvas or the manager.
        """
        return cls(canvas_class(figure), num)

    @classmethod
    def start_main_loop(cls):
        """
        Start the main event loop.

        This method is called by `.FigureManagerBase.pyplot_show`, which is the
        implementation of `.pyplot.show`.  To customize the behavior of
        `.pyplot.show`, interactive backends should usually override
        `~.FigureManagerBase.start_main_loop`; if more customized logic is
        necessary, `~.FigureManagerBase.pyplot_show` can also be overridden.
        """

    @classmethod
    def pyplot_show(cls, *, block=None):
        """
        Show all figures.  This method is the implementation of `.pyplot.show`.

        To customize the behavior of `.pyplot.show`, interactive backends
        should usually override `~.FigureManagerBase.start_main_loop`; if more
        customized logic is necessary, `~.FigureManagerBase.pyplot_show` can
        also be overridden.

        Parameters
        ----------
        block : bool, optional
            Whether to block by calling ``start_main_loop``.  The default,
            None, means to block if we are neither in IPython's ``%pylab`` mode
            nor in ``interactive`` mode.
        """
        managers = Gcf.get_all_fig_managers()
        if not managers:
            return
        for manager in managers:
            try:
                manager.show()  # Emits a warning for non-interactive backend.
            except NonGuiException as exc:
                _api.warn_external(str(exc))
        if block is None:
            # Hack: Are we in IPython's %pylab mode?  In pylab mode, IPython
            # (>= 0.10) tacks a _needmain attribute onto pyplot.show (always
            # set to False).
            pyplot_show = getattr(sys.modules.get("matplotlib.pyplot"), "show", None)
            ipython_pylab = hasattr(pyplot_show, "_needmain")
            block = not ipython_pylab and not is_interactive()
        if block:
            cls.start_main_loop()

    def show(self):
        """
        For GUI backends, show the figure window and redraw.
        For non-GUI backends, raise an exception, unless running headless (i.e.
        on Linux with an unset DISPLAY); this exception is converted to a
        warning in `.Figure.show`.
        """
        # This should be overridden in GUI backends.
        if sys.platform == "linux" and not os.environ.get("DISPLAY"):
            # We cannot check _get_running_interactive_framework() ==
            # "headless" because that would also suppress the warning when
            # $DISPLAY exists but is invalid, which is more likely an error and
            # thus warrants a warning.
            return
        raise NonGuiException(
            f"{type(self.canvas).__name__} is non-interactive, and thus cannot be "
            f"shown")

    def destroy(self):
        pass

    def full_screen_toggle(self):
        pass

    def resize(self, w, h):
        """For GUI backends, resize the window (in physical pixels)."""

    def get_window_title(self):
        """Return the title text of the window containing the figure."""
        return self._window_title

    def set_window_title(self, title):
        """
        Set the title text of the window containing the figure.

        Examples
        --------
        >>> fig = plt.figure()
        >>> fig.canvas.manager.set_window_title('My figure')
        """
        # This attribute is not defined in __init__ (but __init__ calls this
        # setter), as derived classes (real GUI managers) will store this
        # information directly on the widget; only the base (non-GUI) manager
        # class needs a specific attribute for it (so that filename escaping
        # can be checked in the test suite).
        self._window_title = title


cursors = tools.cursors


class _Mode(str, Enum):
    NONE = ""
    PAN = "pan/zoom"
    ZOOM = "zoom rect"

    def __str__(self):
        return self.value

    @property
    def _navigate_mode(self):
        return self.name if self is not _Mode.NONE else None


class NavigationToolbar2:
    """
    Base class for the navigation cursor, version 2.

    Backends must implement a canvas that handles connections for
    'button_press_event' and 'button_release_event'.  See
    :meth:`FigureCanvasBase.mpl_connect` for more information.

    They must also define

    :meth:`save_figure`
        Save the current figure.

    :meth:`draw_rubberband` (optional)
        Draw the zoom to rect "rubberband" rectangle.

    :meth:`set_message` (optional)
        Display message.

    :meth:`set_history_buttons` (optional)
        You can change the history back / forward buttons to indicate disabled / enabled
        state.

    and override ``__init__`` to set up the toolbar -- without forgetting to
    call the base-class init.  Typically, ``__init__`` needs to set up toolbar
    buttons connected to the `home`, `back`, `forward`, `pan`, `zoom`, and
    `save_figure` methods and using standard icons in the "images" subdirectory
    of the data path.

    That's it, we'll do the rest!
    """

    # list of toolitems to add to the toolbar, format is:
    # (
    #   text, # the text of the button (often not visible to users)
    #   tooltip_text, # the tooltip shown on hover (where possible)
    #   image_file, # name of the image for the button (without the extension)
    #   name_of_method, # name of the method in NavigationToolbar2 to call
    # )
    toolitems = (
        ('Home', 'Reset original view', 'home', 'home'),
        ('Back', 'Back to previous view', 'back', 'back'),
        ('Forward', 'Forward to next view', 'forward', 'forward'),
        (None, None, None, None),
        ('Pan',
         'Left button pans, Right button zooms\n'
         'x/y fixes axis, CTRL fixes aspect',
         'move', 'pan'),
        ('Zoom', 'Zoom to rectangle\nx/y fixes axis', 'zoom_to_rect', 'zoom'),
        ('Subplots', 'Configure subplots', 'subplots', 'configure_subplots'),
        (None, None, None, None),
        ('Save', 'Save the figure', 'filesave', 'save_figure'),
      )

    UNKNOWN_SAVED_STATUS = object()

    def __init__(self, canvas):
        self.canvas = canvas
        canvas.toolbar = self
        self._nav_stack = cbook._Stack()
        # This cursor will be set after the initial draw.
        self._last_cursor = tools.Cursors.POINTER

        self._id_press = self.canvas.mpl_connect(
            'button_press_event', self._zoom_pan_handler)
        self._id_release = self.canvas.mpl_connect(
            'button_release_event', self._zoom_pan_handler)
        self._id_drag = self.canvas.mpl_connect(
            'motion_notify_event', self.mouse_move)
        self._pan_info = None
        self._zoom_info = None

        self.mode = _Mode.NONE  # a mode string for the status bar
        self.set_history_buttons()

    def set_message(self, s):
        """Display a message on toolbar or in status bar."""

    def draw_rubberband(self, event, x0, y0, x1, y1):
        """
        Draw a rectangle rubberband to indicate zoom limits.

        Note that it is not guaranteed that ``x0 <= x1`` and ``y0 <= y1``.
        """

    def remove_rubberband(self):
        """Remove the rubberband."""

    def home(self, *args):
        """
        Restore the original view.

        For convenience of being directly connected as a GUI callback, which
        often get passed additional parameters, this method accepts arbitrary
        parameters, but does not use them.
        """
        self._nav_stack.home()
        self.set_history_buttons()
        self._update_view()

    def back(self, *args):
        """
        Move back up the view lim stack.

        For convenience of being directly connected as a GUI callback, which
        often get passed additional parameters, this method accepts arbitrary
        parameters, but does not use them.
        """
        self._nav_stack.back()
        self.set_history_buttons()
        self._update_view()

    def forward(self, *args):
        """
        Move forward in the view lim stack.

        For convenience of being directly connected as a GUI callback, which
        often get passed additional parameters, this method accepts arbitrary
        parameters, but does not use them.
        """
        self._nav_stack.forward()
        self.set_history_buttons()
        self._update_view()

    def _update_cursor(self, event):
        """
        Update the cursor after a mouse move event or a tool (de)activation.
        """
        if self.mode and event.inaxes and event.inaxes.get_navigate():
            if (self.mode == _Mode.ZOOM
                    and self._last_cursor != tools.Cursors.SELECT_REGION):
                self.canvas.set_cursor(tools.Cursors.SELECT_REGION)
                self._last_cursor = tools.Cursors.SELECT_REGION
            elif (self.mode == _Mode.PAN
                  and self._last_cursor != tools.Cursors.MOVE):
                self.canvas.set_cursor(tools.Cursors.MOVE)
                self._last_cursor = tools.Cursors.MOVE
        elif self._last_cursor != tools.Cursors.POINTER:
            self.canvas.set_cursor(tools.Cursors.POINTER)
            self._last_cursor = tools.Cursors.POINTER

    @contextmanager
    def _wait_cursor_for_draw_cm(self):
        """
        Set the cursor to a wait cursor when drawing the canvas.

        In order to avoid constantly changing the cursor when the canvas
        changes frequently, do nothing if this context was triggered during the
        last second.  (Optimally we'd prefer only setting the wait cursor if
        the *current* draw takes too long, but the current draw blocks the GUI
        thread).
        """
        self._draw_time, last_draw_time = (
            time.time(), getattr(self, "_draw_time", -np.inf))
        if self._draw_time - last_draw_time > 1:
            try:
                self.canvas.set_cursor(tools.Cursors.WAIT)
                yield
            finally:
                self.canvas.set_cursor(self._last_cursor)
        else:
            yield

    @staticmethod
    def _mouse_event_to_message(event):
        if event.inaxes and event.inaxes.get_navigate():
            try:
                s = event.inaxes.format_coord(event.xdata, event.ydata)
            except (ValueError, OverflowError):
                pass
            else:
                s = s.rstrip()
                artists = [a for a in event.inaxes._mouseover_set
                           if a.contains(event)[0] and a.get_visible()]
                if artists:
                    a = cbook._topmost_artist(artists)
                    if a is not event.inaxes.patch:
                        data = a.get_cursor_data(event)
                        if data is not None:
                            data_str = a.format_cursor_data(data).rstrip()
                            if data_str:
                                s = s + '\n' + data_str
                return s
        return ""

    def mouse_move(self, event):
        self._update_cursor(event)
        self.set_message(self._mouse_event_to_message(event))

    def _zoom_pan_handler(self, event):
        if self.mode == _Mode.PAN:
            if event.name == "button_press_event":
                self.press_pan(event)
            elif event.name == "button_release_event":
                self.release_pan(event)
        if self.mode == _Mode.ZOOM:
            if event.name == "button_press_event":
                self.press_zoom(event)
            elif event.name == "button_release_event":
                self.release_zoom(event)

    def _start_event_axes_interaction(self, event, *, method):

        def _ax_filter(ax):
            return (ax.in_axes(event) and
                    ax.get_navigate() and
                    getattr(ax, f"can_{method}")()
                    )

        def _capture_events(ax):
            f = ax.get_forward_navigation_events()
            if f == "auto":  # (capture = patch visibility)
                f = not ax.patch.get_visible()
            return not f

        # get all relevant axes for the event
        axes = list(filter(_ax_filter, self.canvas.figure.get_axes()))

        if len(axes) == 0:
            return []

        if self._nav_stack() is None:
            self.push_current()   # Set the home button to this view.

        # group axes by zorder (reverse to trigger later axes first)
        grps = dict()
        for ax in reversed(axes):
            grps.setdefault(ax.get_zorder(), []).append(ax)

        axes_to_trigger = []
        # go through zorders in reverse until we hit a capturing axes
        for zorder in sorted(grps, reverse=True):
            for ax in grps[zorder]:
                axes_to_trigger.append(ax)
                # NOTE: shared axes are automatically triggered, but twin-axes not!
                axes_to_trigger.extend(ax._twinned_axes.get_siblings(ax))

                if _capture_events(ax):
                    break  # break if we hit a capturing axes
            else:
                # If the inner loop finished without an explicit break,
                # (e.g. no capturing axes was found) continue the
                # outer loop to the next zorder.
                continue

            # If the inner loop was terminated with an explicit break,
            # terminate the outer loop as well.
            break

        # avoid duplicated triggers (but keep order of list)
        axes_to_trigger = list(dict.fromkeys(axes_to_trigger))

        return axes_to_trigger

    def pan(self, *args):
        """
        Toggle the pan/zoom tool.

        Pan with left button, zoom with right.
        """
        if not self.canvas.widgetlock.available(self):
            self.set_message("pan unavailable")
            return
        if self.mode == _Mode.PAN:
            self.mode = _Mode.NONE
            self.canvas.widgetlock.release(self)
        else:
            self.mode = _Mode.PAN
            self.canvas.widgetlock(self)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self.mode._navigate_mode)

    _PanInfo = namedtuple("_PanInfo", "button axes cid")

    def press_pan(self, event):
        """Callback for mouse button press in pan/zoom mode."""
        if (event.button not in [MouseButton.LEFT, MouseButton.RIGHT]
                or event.x is None or event.y is None):
            return

        axes = self._start_event_axes_interaction(event, method="pan")
        if not axes:
            return

        # call "ax.start_pan(..)" on all relevant axes of an event
        for ax in axes:
            ax.start_pan(event.x, event.y, event.button)

        self.canvas.mpl_disconnect(self._id_drag)
        id_drag = self.canvas.mpl_connect("motion_notify_event", self.drag_pan)

        self._pan_info = self._PanInfo(
            button=event.button, axes=axes, cid=id_drag)

    def drag_pan(self, event):
        """Callback for dragging in pan/zoom mode."""
        for ax in self._pan_info.axes:
            # Using the recorded button at the press is safer than the current
            # button, as multiple buttons can get pressed during motion.
            ax.drag_pan(self._pan_info.button, event.key, event.x, event.y)
        self.canvas.draw_idle()

    def release_pan(self, event):
        """Callback for mouse button release in pan/zoom mode."""
        if self._pan_info is None:
            return
        self.canvas.mpl_disconnect(self._pan_info.cid)
        self._id_drag = self.canvas.mpl_connect(
            'motion_notify_event', self.mouse_move)
        for ax in self._pan_info.axes:
            ax.end_pan()
        self.canvas.draw_idle()
        self._pan_info = None
        self.push_current()

    def zoom(self, *args):
        if not self.canvas.widgetlock.available(self):
            self.set_message("zoom unavailable")
            return
        """Toggle zoom to rect mode."""
        if self.mode == _Mode.ZOOM:
            self.mode = _Mode.NONE
            self.canvas.widgetlock.release(self)
        else:
            self.mode = _Mode.ZOOM
            self.canvas.widgetlock(self)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self.mode._navigate_mode)

    _ZoomInfo = namedtuple("_ZoomInfo", "direction start_xy axes cid cbar")

    def press_zoom(self, event):
        """Callback for mouse button press in zoom to rect mode."""
        if (event.button not in [MouseButton.LEFT, MouseButton.RIGHT]
                or event.x is None or event.y is None):
            return

        axes = self._start_event_axes_interaction(event, method="zoom")
        if not axes:
            return

        id_zoom = self.canvas.mpl_connect(
            "motion_notify_event", self.drag_zoom)

        # A colorbar is one-dimensional, so we extend the zoom rectangle out
        # to the edge of the Axes bbox in the other dimension. To do that we
        # store the orientation of the colorbar for later.
        parent_ax = axes[0]
        if hasattr(parent_ax, "_colorbar"):
            cbar = parent_ax._colorbar.orientation
        else:
            cbar = None

        self._zoom_info = self._ZoomInfo(
            direction="in" if event.button == 1 else "out",
            start_xy=(event.x, event.y), axes=axes, cid=id_zoom, cbar=cbar)

    def drag_zoom(self, event):
        """Callback for dragging in zoom mode."""
        start_xy = self._zoom_info.start_xy
        ax = self._zoom_info.axes[0]
        (x1, y1), (x2, y2) = np.clip(
            [start_xy, [event.x, event.y]], ax.bbox.min, ax.bbox.max)
        key = event.key
        # Force the key on colorbars to extend the short-axis bbox
        if self._zoom_info.cbar == "horizontal":
            key = "x"
        elif self._zoom_info.cbar == "vertical":
            key = "y"
        if key == "x":
            y1, y2 = ax.bbox.intervaly
        elif key == "y":
            x1, x2 = ax.bbox.intervalx

        self.draw_rubberband(event, x1, y1, x2, y2)

    def release_zoom(self, event):
        """Callback for mouse button release in zoom to rect mode."""
        if self._zoom_info is None:
            return

        # We don't check the event button here, so that zooms can be cancelled
        # by (pressing and) releasing another mouse button.
        self.canvas.mpl_disconnect(self._zoom_info.cid)
        self.remove_rubberband()

        start_x, start_y = self._zoom_info.start_xy
        key = event.key
        # Force the key on colorbars to ignore the zoom-cancel on the
        # short-axis side
        if self._zoom_info.cbar == "horizontal":
            key = "x"
        elif self._zoom_info.cbar == "vertical":
            key = "y"
        # Ignore single clicks: 5 pixels is a threshold that allows the user to
        # "cancel" a zoom action by zooming by less than 5 pixels.
        if ((abs(event.x - start_x) < 5 and key != "y") or
                (abs(event.y - start_y) < 5 and key != "x")):
            self.canvas.draw_idle()
            self._zoom_info = None
            return

        for i, ax in enumerate(self._zoom_info.axes):
            # Detect whether this Axes is twinned with an earlier Axes in the
            # list of zoomed Axes, to avoid double zooming.
            twinx = any(ax.get_shared_x_axes().joined(ax, prev)
                        for prev in self._zoom_info.axes[:i])
            twiny = any(ax.get_shared_y_axes().joined(ax, prev)
                        for prev in self._zoom_info.axes[:i])
            ax._set_view_from_bbox(
                (start_x, start_y, event.x, event.y),
                self._zoom_info.direction, key, twinx, twiny)

        self.canvas.draw_idle()
        self._zoom_info = None
        self.push_current()

    def push_current(self):
        """Push the current view limits and position onto the stack."""
        self._nav_stack.push(
            WeakKeyDictionary(
                {ax: (ax._get_view(),
                      # Store both the original and modified positions.
                      (ax.get_position(True).frozen(),
                       ax.get_position().frozen()))
                 for ax in self.canvas.figure.axes}))
        self.set_history_buttons()

    def _update_view(self):
        """
        Update the viewlim and position from the view and position stack for
        each Axes.
        """
        nav_info = self._nav_stack()
        if nav_info is None:
            return
        # Retrieve all items at once to avoid any risk of GC deleting an Axes
        # while in the middle of the loop below.
        items = list(nav_info.items())
        for ax, (view, (pos_orig, pos_active)) in items:
            ax._set_view(view)
            # Restore both the original and modified positions
            ax._set_position(pos_orig, 'original')
            ax._set_position(pos_active, 'active')
        self.canvas.draw_idle()

    def configure_subplots(self, *args):
        if hasattr(self, "subplot_tool"):
            self.subplot_tool.figure.canvas.manager.show()
            return
        # This import needs to happen here due to circular imports.
        from matplotlib.figure import Figure
        with mpl.rc_context({"toolbar": "none"}):  # No navbar for the toolfig.
            manager = type(self.canvas).new_manager(Figure(figsize=(6, 3)), -1)
        manager.set_window_title("Subplot configuration tool")
        tool_fig = manager.canvas.figure
        tool_fig.subplots_adjust(top=0.9)
        self.subplot_tool = widgets.SubplotTool(self.canvas.figure, tool_fig)
        cid = self.canvas.mpl_connect(
            "close_event", lambda e: manager.destroy())

        def on_tool_fig_close(e):
            self.canvas.mpl_disconnect(cid)
            del self.subplot_tool

        tool_fig.canvas.mpl_connect("close_event", on_tool_fig_close)
        manager.show()
        return self.subplot_tool

    def save_figure(self, *args):
        """
        Save the current figure.

        Backend implementations may choose to return
        the absolute path of the saved file, if any, as
        a string.

        If no file is created then `None` is returned.

        If the backend does not implement this functionality
        then `NavigationToolbar2.UNKNOWN_SAVED_STATUS` is returned.

        Returns
        -------
        str or `NavigationToolbar2.UNKNOWN_SAVED_STATUS` or `None`
            The filepath of the saved figure.
            Returns `None` if figure is not saved.
            Returns `NavigationToolbar2.UNKNOWN_SAVED_STATUS` when
            the backend does not provide the information.
        """
        raise NotImplementedError

    def update(self):
        """Reset the Axes stack."""
        self._nav_stack.clear()
        self.set_history_buttons()

    def set_history_buttons(self):
        """Enable or disable the back/forward button."""


class ToolContainerBase:
    """
    Base class for all tool containers, e.g. toolbars.

    Attributes
    ----------
    toolmanager : `.ToolManager`
        The tools with which this `ToolContainer` wants to communicate.
    """

    _icon_extension = '.png'
    """
    Toolcontainer button icon image format extension

    **String**: Image extension
    """

    def __init__(self, toolmanager):
        self.toolmanager = toolmanager
        toolmanager.toolmanager_connect(
            'tool_message_event',
            lambda event: self.set_message(event.message))
        toolmanager.toolmanager_connect(
            'tool_removed_event',
            lambda event: self.remove_toolitem(event.tool.name))

    def _tool_toggled_cbk(self, event):
        """
        Capture the 'tool_trigger_[name]'

        This only gets used for toggled tools.
        """
        self.toggle_toolitem(event.tool.name, event.tool.toggled)

    def add_tool(self, tool, group, position=-1):
        """
        Add a tool to this container.

        Parameters
        ----------
        tool : tool_like
            The tool to add, see `.ToolManager.get_tool`.
        group : str
            The name of the group to add this tool to.
        position : int, default: -1
            The position within the group to place this tool.
        """
        tool = self.toolmanager.get_tool(tool)
        image = self._get_image_filename(tool)
        toggle = getattr(tool, 'toggled', None) is not None
        self.add_toolitem(tool.name, group, position,
                          image, tool.description, toggle)
        if toggle:
            self.toolmanager.toolmanager_connect('tool_trigger_%s' % tool.name,
                                                 self._tool_toggled_cbk)
            # If initially toggled
            if tool.toggled:
                self.toggle_toolitem(tool.name, True)

    def _get_image_filename(self, tool):
        """Resolve a tool icon's filename."""
        if not tool.image:
            return None
        if os.path.isabs(tool.image):
            filename = tool.image
        else:
            if "image" in getattr(tool, "__dict__", {}):
                raise ValueError("If 'tool.image' is an instance variable, "
                                 "it must be an absolute path")
            for cls in type(tool).__mro__:
                if "image" in vars(cls):
                    try:
                        src = inspect.getfile(cls)
                        break
                    except (OSError, TypeError):
                        raise ValueError("Failed to locate source file "
                                         "where 'tool.image' is defined") from None
            else:
                raise ValueError("Failed to find parent class defining 'tool.image'")
            filename = str(pathlib.Path(src).parent / tool.image)
        for filename in [filename, filename + self._icon_extension]:
            if os.path.isfile(filename):
                return os.path.abspath(filename)
        for fname in [  # Fallback; once deprecation elapses.
            tool.image,
            tool.image + self._icon_extension,
            cbook._get_data_path("images", tool.image),
            cbook._get_data_path("images", tool.image + self._icon_extension),
        ]:
            if os.path.isfile(fname):
                _api.warn_deprecated(
                    "3.9", message=f"Loading icon {tool.image!r} from the current "
                    "directory or from Matplotlib's image directory.  This behavior "
                    "is deprecated since %(since)s and will be removed in %(removal)s; "
                    "Tool.image should be set to a path relative to the Tool's source "
                    "file, or to an absolute path.")
                return os.path.abspath(fname)

    def trigger_tool(self, name):
        """
        Trigger the tool.

        Parameters
        ----------
        name : str
            Name (id) of the tool triggered from within the container.
        """
        self.toolmanager.trigger_tool(name, sender=self)

    def add_toolitem(self, name, group, position, image, description, toggle):
        """
        A hook to add a toolitem to the container.

        This hook must be implemented in each backend and contains the
        backend-specific code to add an element to the toolbar.

        .. warning::
            This is part of the backend implementation and should
            not be called by end-users.  They should instead call
            `.ToolContainerBase.add_tool`.

        The callback associated with the button click event
        must be *exactly* ``self.trigger_tool(name)``.

        Parameters
        ----------
        name : str
            Name of the tool to add, this gets used as the tool's ID and as the
            default label of the buttons.
        group : str
            Name of the group that this tool belongs to.
        position : int
            Position of the tool within its group, if -1 it goes at the end.
        image : str
            Filename of the image for the button or `None`.
        description : str
            Description of the tool, used for the tooltips.
        toggle : bool
            * `True` : The button is a toggle (change the pressed/unpressed
              state between consecutive clicks).
            * `False` : The button is a normal button (returns to unpressed
              state after release).
        """
        raise NotImplementedError

    def toggle_toolitem(self, name, toggled):
        """
        A hook to toggle a toolitem without firing an event.

        This hook must be implemented in each backend and contains the
        backend-specific code to silently toggle a toolbar element.

        .. warning::
            This is part of the backend implementation and should
            not be called by end-users.  They should instead call
            `.ToolManager.trigger_tool` or `.ToolContainerBase.trigger_tool`
            (which are equivalent).

        Parameters
        ----------
        name : str
            Id of the tool to toggle.
        toggled : bool
            Whether to set this tool as toggled or not.
        """
        raise NotImplementedError

    def remove_toolitem(self, name):
        """
        A hook to remove a toolitem from the container.

        This hook must be implemented in each backend and contains the
        backend-specific code to remove an element from the toolbar; it is
        called when `.ToolManager` emits a ``tool_removed_event``.

        Because some tools are present only on the `.ToolManager` but not on
        the `ToolContainer`, this method must be a no-op when called on a tool
        absent from the container.

        .. warning::
            This is part of the backend implementation and should
            not be called by end-users.  They should instead call
            `.ToolManager.remove_tool`.

        Parameters
        ----------
        name : str
            Name of the tool to remove.
        """
        raise NotImplementedError

    def set_message(self, s):
        """
        Display a message on the toolbar.

        Parameters
        ----------
        s : str
            Message text.
        """
        raise NotImplementedError


class _Backend:
    # A backend can be defined by using the following pattern:
    #
    # @_Backend.export
    # class FooBackend(_Backend):
    #     # override the attributes and methods documented below.

    # `backend_version` may be overridden by the subclass.
    backend_version = "unknown"

    # The `FigureCanvas` class must be defined.
    FigureCanvas = None

    # For interactive backends, the `FigureManager` class must be overridden.
    FigureManager = FigureManagerBase

    # For interactive backends, `mainloop` should be a function taking no
    # argument and starting the backend main loop.  It should be left as None
    # for non-interactive backends.
    mainloop = None

    # The following methods will be automatically defined and exported, but
    # can be overridden.

    @classmethod
    def new_figure_manager(cls, num, *args, **kwargs):
        """Create a new figure manager instance."""
        # This import needs to happen here due to circular imports.
        from matplotlib.figure import Figure
        fig_cls = kwargs.pop('FigureClass', Figure)
        fig = fig_cls(*args, **kwargs)
        return cls.new_figure_manager_given_figure(num, fig)

    @classmethod
    def new_figure_manager_given_figure(cls, num, figure):
        """Create a new figure manager instance for the given figure."""
        return cls.FigureCanvas.new_manager(figure, num)

    @classmethod
    def draw_if_interactive(cls):
        manager_class = cls.FigureCanvas.manager_class
        # Interactive backends reimplement start_main_loop or pyplot_show.
        backend_is_interactive = (
            manager_class.start_main_loop != FigureManagerBase.start_main_loop
            or manager_class.pyplot_show != FigureManagerBase.pyplot_show)
        if backend_is_interactive and is_interactive():
            manager = Gcf.get_active()
            if manager:
                manager.canvas.draw_idle()

    @classmethod
    def show(cls, *, block=None):
        """
        Show all figures.

        `show` blocks by calling `mainloop` if *block* is ``True``, or if it is
        ``None`` and we are not in `interactive` mode and if IPython's
        ``%matplotlib`` integration has not been activated.
        """
        managers = Gcf.get_all_fig_managers()
        if not managers:
            return
        for manager in managers:
            try:
                manager.show()  # Emits a warning for non-interactive backend.
            except NonGuiException as exc:
                _api.warn_external(str(exc))
        if cls.mainloop is None:
            return
        if block is None:
            # Hack: Is IPython's %matplotlib integration activated?  If so,
            # IPython's activate_matplotlib (>= 0.10) tacks a _needmain
            # attribute onto pyplot.show (always set to False).
            pyplot_show = getattr(sys.modules.get("matplotlib.pyplot"), "show", None)
            ipython_pylab = hasattr(pyplot_show, "_needmain")
            block = not ipython_pylab and not is_interactive()
        if block:
            cls.mainloop()

    # This method is the one actually exporting the required methods.

    @staticmethod
    def export(cls):
        for name in [
                "backend_version",
                "FigureCanvas",
                "FigureManager",
                "new_figure_manager",
                "new_figure_manager_given_figure",
                "draw_if_interactive",
                "show",
        ]:
            setattr(sys.modules[cls.__module__], name, getattr(cls, name))

        # For back-compatibility, generate a shim `Show` class.

        class Show(ShowBase):
            def mainloop(self):
                return cls.mainloop()

        setattr(sys.modules[cls.__module__], "Show", Show)
        return cls


class ShowBase(_Backend):
    """
    Simple base class to generate a ``show()`` function in backends.

    Subclass must override ``mainloop()`` method.
    """

    def __call__(self, block=None):
        return self.show(block=block)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\win32\peb_teb.py ===
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
PEB and TEB structures, constants and data types.
"""

__revision__ = "$Id$"

from winappdbg.win32.defines import *
from winappdbg.win32.version import os

# ==============================================================================
# This is used later on to calculate the list of exported symbols.
_all = None
_all = set(vars().keys())
# ==============================================================================

# --- PEB and TEB structures, constants and data types -------------------------


# From http://www.nirsoft.net/kernel_struct/vista/CLIENT_ID.html
#
# typedef struct _CLIENT_ID
# {
#     PVOID UniqueProcess;
#     PVOID UniqueThread;
# } CLIENT_ID, *PCLIENT_ID;
class CLIENT_ID(Structure):
    _fields_ = [
        ("UniqueProcess", PVOID),
        ("UniqueThread", PVOID),
    ]


# From MSDN:
#
# typedef struct _LDR_DATA_TABLE_ENTRY {
#     BYTE Reserved1[2];
#     LIST_ENTRY InMemoryOrderLinks;
#     PVOID Reserved2[2];
#     PVOID DllBase;
#     PVOID EntryPoint;
#     PVOID Reserved3;
#     UNICODE_STRING FullDllName;
#     BYTE Reserved4[8];
#     PVOID Reserved5[3];
#     union {
#         ULONG CheckSum;
#         PVOID Reserved6;
#     };
#     ULONG TimeDateStamp;
# } LDR_DATA_TABLE_ENTRY, *PLDR_DATA_TABLE_ENTRY;
##class LDR_DATA_TABLE_ENTRY(Structure):
##    _fields_ = [
##        ("Reserved1",           BYTE * 2),
##        ("InMemoryOrderLinks",  LIST_ENTRY),
##        ("Reserved2",           PVOID * 2),
##        ("DllBase",             PVOID),
##        ("EntryPoint",          PVOID),
##        ("Reserved3",           PVOID),
##        ("FullDllName",           UNICODE_STRING),
##        ("Reserved4",           BYTE * 8),
##        ("Reserved5",           PVOID * 3),
##        ("CheckSum",            ULONG),
##        ("TimeDateStamp",       ULONG),
##]

# From MSDN:
#
# typedef struct _PEB_LDR_DATA {
#   BYTE         Reserved1[8];
#   PVOID        Reserved2[3];
#   LIST_ENTRY   InMemoryOrderModuleList;
# } PEB_LDR_DATA,
#  *PPEB_LDR_DATA;
##class PEB_LDR_DATA(Structure):
##    _fields_ = [
##        ("Reserved1",               BYTE),
##        ("Reserved2",               PVOID),
##        ("InMemoryOrderModuleList", LIST_ENTRY),
##]

# From http://undocumented.ntinternals.net/UserMode/Structures/RTL_USER_PROCESS_PARAMETERS.html
# typedef struct _RTL_USER_PROCESS_PARAMETERS {
#   ULONG                   MaximumLength;
#   ULONG                   Length;
#   ULONG                   Flags;
#   ULONG                   DebugFlags;
#   PVOID                   ConsoleHandle;
#   ULONG                   ConsoleFlags;
#   HANDLE                  StdInputHandle;
#   HANDLE                  StdOutputHandle;
#   HANDLE                  StdErrorHandle;
#   UNICODE_STRING          CurrentDirectoryPath;
#   HANDLE                  CurrentDirectoryHandle;
#   UNICODE_STRING          DllPath;
#   UNICODE_STRING          ImagePathName;
#   UNICODE_STRING          CommandLine;
#   PVOID                   Environment;
#   ULONG                   StartingPositionLeft;
#   ULONG                   StartingPositionTop;
#   ULONG                   Width;
#   ULONG                   Height;
#   ULONG                   CharWidth;
#   ULONG                   CharHeight;
#   ULONG                   ConsoleTextAttributes;
#   ULONG                   WindowFlags;
#   ULONG                   ShowWindowFlags;
#   UNICODE_STRING          WindowTitle;
#   UNICODE_STRING          DesktopName;
#   UNICODE_STRING          ShellInfo;
#   UNICODE_STRING          RuntimeData;
#   RTL_DRIVE_LETTER_CURDIR DLCurrentDirectory[0x20];
# } RTL_USER_PROCESS_PARAMETERS, *PRTL_USER_PROCESS_PARAMETERS;

# kd> dt _RTL_USER_PROCESS_PARAMETERS
# ntdll!_RTL_USER_PROCESS_PARAMETERS
#    +0x000 MaximumLength    : Uint4B
#    +0x004 Length           : Uint4B
#    +0x008 Flags            : Uint4B
#    +0x00c DebugFlags       : Uint4B
#    +0x010 ConsoleHandle    : Ptr32 Void
#    +0x014 ConsoleFlags     : Uint4B
#    +0x018 StandardInput    : Ptr32 Void
#    +0x01c StandardOutput   : Ptr32 Void
#    +0x020 StandardError    : Ptr32 Void
#    +0x024 CurrentDirectory : _CURDIR
#    +0x030 DllPath          : _UNICODE_STRING
#    +0x038 ImagePathName    : _UNICODE_STRING
#    +0x040 CommandLine      : _UNICODE_STRING
#    +0x048 Environment      : Ptr32 Void
#    +0x04c StartingX        : Uint4B
#    +0x050 StartingY        : Uint4B
#    +0x054 CountX           : Uint4B
#    +0x058 CountY           : Uint4B
#    +0x05c CountCharsX      : Uint4B
#    +0x060 CountCharsY      : Uint4B
#    +0x064 FillAttribute    : Uint4B
#    +0x068 WindowFlags      : Uint4B
#    +0x06c ShowWindowFlags  : Uint4B
#    +0x070 WindowTitle      : _UNICODE_STRING
#    +0x078 DesktopInfo      : _UNICODE_STRING
#    +0x080 ShellInfo        : _UNICODE_STRING
#    +0x088 RuntimeData      : _UNICODE_STRING
#    +0x090 CurrentDirectores : [32] _RTL_DRIVE_LETTER_CURDIR
#    +0x290 EnvironmentSize  : Uint4B
##class RTL_USER_PROCESS_PARAMETERS(Structure):
##    _fields_ = [
##        ("MaximumLength",           ULONG),
##        ("Length",                  ULONG),
##        ("Flags",                   ULONG),
##        ("DebugFlags",              ULONG),
##        ("ConsoleHandle",           PVOID),
##        ("ConsoleFlags",            ULONG),
##        ("StandardInput",           HANDLE),
##        ("StandardOutput",          HANDLE),
##        ("StandardError",           HANDLE),
##        ("CurrentDirectory",        CURDIR),
##        ("DllPath",                 UNICODE_STRING),
##        ("ImagePathName",           UNICODE_STRING),
##        ("CommandLine",             UNICODE_STRING),
##        ("Environment",             PVOID),
##        ("StartingX",               ULONG),
##        ("StartingY",               ULONG),
##        ("CountX",                  ULONG),
##        ("CountY",                  ULONG),
##        ("CountCharsX",             ULONG),
##        ("CountCharsY",             ULONG),
##        ("FillAttribute",           ULONG),
##        ("WindowFlags",             ULONG),
##        ("ShowWindowFlags",         ULONG),
##        ("WindowTitle",             UNICODE_STRING),
##        ("DesktopInfo",             UNICODE_STRING),
##        ("ShellInfo",               UNICODE_STRING),
##        ("RuntimeData",             UNICODE_STRING),
##        ("CurrentDirectores",       RTL_DRIVE_LETTER_CURDIR * 32), # typo here?
##
##        # Windows 2008 and Vista
##        ("EnvironmentSize",         ULONG),
##]
##    @property
##    def CurrentDirectories(self):
##        return self.CurrentDirectores


# From MSDN:
#
# typedef struct _RTL_USER_PROCESS_PARAMETERS {
#   BYTE             Reserved1[16];
#   PVOID            Reserved2[10];
#   UNICODE_STRING   ImagePathName;
#   UNICODE_STRING   CommandLine;
# } RTL_USER_PROCESS_PARAMETERS,
#  *PRTL_USER_PROCESS_PARAMETERS;
class RTL_USER_PROCESS_PARAMETERS(Structure):
    _fields_ = [
        ("Reserved1", BYTE * 16),
        ("Reserved2", PVOID * 10),
        ("ImagePathName", UNICODE_STRING),
        ("CommandLine", UNICODE_STRING),
        ("Environment", PVOID),  # undocumented!
        #
        # XXX TODO
        # This structure should be defined with all undocumented fields for
        # each version of Windows, just like it's being done for PEB and TEB.
        #
    ]


PPS_POST_PROCESS_INIT_ROUTINE = PVOID

# from MSDN:
#
# typedef struct _PEB {
#     BYTE Reserved1[2];
#     BYTE BeingDebugged;
#     BYTE Reserved2[21];
#     PPEB_LDR_DATA LoaderData;
#     PRTL_USER_PROCESS_PARAMETERS ProcessParameters;
#     BYTE Reserved3[520];
#     PPS_POST_PROCESS_INIT_ROUTINE PostProcessInitRoutine;
#     BYTE Reserved4[136];
#     ULONG SessionId;
# } PEB;
##class PEB(Structure):
##    _fields_ = [
##        ("Reserved1",               BYTE * 2),
##        ("BeingDebugged",           BYTE),
##        ("Reserved2",               BYTE * 21),
##        ("LoaderData",              PVOID,    # PPEB_LDR_DATA
##        ("ProcessParameters",       PVOID,    # PRTL_USER_PROCESS_PARAMETERS
##        ("Reserved3",               BYTE * 520),
##        ("PostProcessInitRoutine",  PPS_POST_PROCESS_INIT_ROUTINE),
##        ("Reserved4",               BYTE),
##        ("SessionId",               ULONG),
##]

# from MSDN:
#
# typedef struct _TEB {
#   BYTE    Reserved1[1952];
#   PVOID   Reserved2[412];
#   PVOID   TlsSlots[64];
#   BYTE    Reserved3[8];
#   PVOID   Reserved4[26];
#   PVOID   ReservedForOle;
#   PVOID   Reserved5[4];
#   PVOID   TlsExpansionSlots;
# } TEB,
#  *PTEB;
##class TEB(Structure):
##    _fields_ = [
##        ("Reserved1",           PVOID * 1952),
##        ("Reserved2",           PVOID * 412),
##        ("TlsSlots",            PVOID * 64),
##        ("Reserved3",           BYTE  * 8),
##        ("Reserved4",           PVOID * 26),
##        ("ReservedForOle",      PVOID),
##        ("Reserved5",           PVOID * 4),
##        ("TlsExpansionSlots",   PVOID),
##]


# from http://undocumented.ntinternals.net/UserMode/Structures/LDR_MODULE.html
#
# typedef struct _LDR_MODULE {
#   LIST_ENTRY InLoadOrderModuleList;
#   LIST_ENTRY InMemoryOrderModuleList;
#   LIST_ENTRY InInitializationOrderModuleList;
#   PVOID BaseAddress;
#   PVOID EntryPoint;
#   ULONG SizeOfImage;
#   UNICODE_STRING FullDllName;
#   UNICODE_STRING BaseDllName;
#   ULONG Flags;
#   SHORT LoadCount;
#   SHORT TlsIndex;
#   LIST_ENTRY HashTableEntry;
#   ULONG TimeDateStamp;
# } LDR_MODULE, *PLDR_MODULE;
class LDR_MODULE(Structure):
    _fields_ = [
        ("InLoadOrderModuleList", LIST_ENTRY),
        ("InMemoryOrderModuleList", LIST_ENTRY),
        ("InInitializationOrderModuleList", LIST_ENTRY),
        ("BaseAddress", PVOID),
        ("EntryPoint", PVOID),
        ("SizeOfImage", ULONG),
        ("FullDllName", UNICODE_STRING),
        ("BaseDllName", UNICODE_STRING),
        ("Flags", ULONG),
        ("LoadCount", SHORT),
        ("TlsIndex", SHORT),
        ("HashTableEntry", LIST_ENTRY),
        ("TimeDateStamp", ULONG),
    ]


# from http://undocumented.ntinternals.net/UserMode/Structures/PEB_LDR_DATA.html
#
# typedef struct _PEB_LDR_DATA {
#   ULONG Length;
#   BOOLEAN Initialized;
#   PVOID SsHandle;
#   LIST_ENTRY InLoadOrderModuleList;
#   LIST_ENTRY InMemoryOrderModuleList;
#   LIST_ENTRY InInitializationOrderModuleList;
# } PEB_LDR_DATA, *PPEB_LDR_DATA;
class PEB_LDR_DATA(Structure):
    _fields_ = [
        ("Length", ULONG),
        ("Initialized", BOOLEAN),
        ("SsHandle", PVOID),
        ("InLoadOrderModuleList", LIST_ENTRY),
        ("InMemoryOrderModuleList", LIST_ENTRY),
        ("InInitializationOrderModuleList", LIST_ENTRY),
    ]


# From http://undocumented.ntinternals.net/UserMode/Undocumented%20Functions/NT%20Objects/Process/PEB_FREE_BLOCK.html
#
# typedef struct _PEB_FREE_BLOCK {
#   PEB_FREE_BLOCK *Next;
#   ULONG Size;
# } PEB_FREE_BLOCK, *PPEB_FREE_BLOCK;
class PEB_FREE_BLOCK(Structure):
    pass


##PPEB_FREE_BLOCK = POINTER(PEB_FREE_BLOCK)
PPEB_FREE_BLOCK = PVOID

PEB_FREE_BLOCK._fields_ = [
    ("Next", PPEB_FREE_BLOCK),
    ("Size", ULONG),
]


# From http://undocumented.ntinternals.net/UserMode/Structures/RTL_DRIVE_LETTER_CURDIR.html
#
# typedef struct _RTL_DRIVE_LETTER_CURDIR {
#   USHORT Flags;
#   USHORT Length;
#   ULONG TimeStamp;
#   UNICODE_STRING DosPath;
# } RTL_DRIVE_LETTER_CURDIR, *PRTL_DRIVE_LETTER_CURDIR;
class RTL_DRIVE_LETTER_CURDIR(Structure):
    _fields_ = [
        ("Flags", USHORT),
        ("Length", USHORT),
        ("TimeStamp", ULONG),
        ("DosPath", UNICODE_STRING),
    ]


# From http://www.nirsoft.net/kernel_struct/vista/CURDIR.html
#
# typedef struct _CURDIR
# {
#      UNICODE_STRING DosPath;
#      PVOID Handle;
# } CURDIR, *PCURDIR;
class CURDIR(Structure):
    _fields_ = [
        ("DosPath", UNICODE_STRING),
        ("Handle", PVOID),
    ]


# From http://www.nirsoft.net/kernel_struct/vista/RTL_CRITICAL_SECTION_DEBUG.html
#
# typedef struct _RTL_CRITICAL_SECTION_DEBUG
# {
#      WORD Type;
#      WORD CreatorBackTraceIndex;
#      PRTL_CRITICAL_SECTION CriticalSection;
#      LIST_ENTRY ProcessLocksList;
#      ULONG EntryCount;
#      ULONG ContentionCount;
#      ULONG Flags;
#      WORD CreatorBackTraceIndexHigh;
#      WORD SpareUSHORT;
# } RTL_CRITICAL_SECTION_DEBUG, *PRTL_CRITICAL_SECTION_DEBUG;
#
# From http://www.nirsoft.net/kernel_struct/vista/RTL_CRITICAL_SECTION.html
#
# typedef struct _RTL_CRITICAL_SECTION
# {
#      PRTL_CRITICAL_SECTION_DEBUG DebugInfo;
#      LONG LockCount;
#      LONG RecursionCount;
#      PVOID OwningThread;
#      PVOID LockSemaphore;
#      ULONG SpinCount;
# } RTL_CRITICAL_SECTION, *PRTL_CRITICAL_SECTION;
#
class RTL_CRITICAL_SECTION(Structure):
    _fields_ = [
        ("DebugInfo", PVOID),  # PRTL_CRITICAL_SECTION_DEBUG
        ("LockCount", LONG),
        ("RecursionCount", LONG),
        ("OwningThread", PVOID),
        ("LockSemaphore", PVOID),
        ("SpinCount", ULONG),
    ]


class RTL_CRITICAL_SECTION_DEBUG(Structure):
    _fields_ = [
        ("Type", WORD),
        ("CreatorBackTraceIndex", WORD),
        ("CriticalSection", PVOID),  # PRTL_CRITICAL_SECTION
        ("ProcessLocksList", LIST_ENTRY),
        ("EntryCount", ULONG),
        ("ContentionCount", ULONG),
        ("Flags", ULONG),
        ("CreatorBackTraceIndexHigh", WORD),
        ("SpareUSHORT", WORD),
    ]


PRTL_CRITICAL_SECTION = POINTER(RTL_CRITICAL_SECTION)
PRTL_CRITICAL_SECTION_DEBUG = POINTER(RTL_CRITICAL_SECTION_DEBUG)

PPEB_LDR_DATA = POINTER(PEB_LDR_DATA)
PRTL_USER_PROCESS_PARAMETERS = POINTER(RTL_USER_PROCESS_PARAMETERS)

PPEBLOCKROUTINE = PVOID

# BitField
ImageUsesLargePages = 1 << 0
IsProtectedProcess = 1 << 1
IsLegacyProcess = 1 << 2
IsImageDynamicallyRelocated = 1 << 3
SkipPatchingUser32Forwarders = 1 << 4

# CrossProcessFlags
ProcessInJob = 1 << 0
ProcessInitializing = 1 << 1
ProcessUsingVEH = 1 << 2
ProcessUsingVCH = 1 << 3
ProcessUsingFTH = 1 << 4

# TracingFlags
HeapTracingEnabled = 1 << 0
CritSecTracingEnabled = 1 << 1

# NtGlobalFlags
FLG_VALID_BITS = 0x003FFFFF  # not a flag
FLG_STOP_ON_EXCEPTION = 0x00000001
FLG_SHOW_LDR_SNAPS = 0x00000002
FLG_DEBUG_INITIAL_COMMAND = 0x00000004
FLG_STOP_ON_HUNG_GUI = 0x00000008
FLG_HEAP_ENABLE_TAIL_CHECK = 0x00000010
FLG_HEAP_ENABLE_FREE_CHECK = 0x00000020
FLG_HEAP_VALIDATE_PARAMETERS = 0x00000040
FLG_HEAP_VALIDATE_ALL = 0x00000080
FLG_POOL_ENABLE_TAIL_CHECK = 0x00000100
FLG_POOL_ENABLE_FREE_CHECK = 0x00000200
FLG_POOL_ENABLE_TAGGING = 0x00000400
FLG_HEAP_ENABLE_TAGGING = 0x00000800
FLG_USER_STACK_TRACE_DB = 0x00001000
FLG_KERNEL_STACK_TRACE_DB = 0x00002000
FLG_MAINTAIN_OBJECT_TYPELIST = 0x00004000
FLG_HEAP_ENABLE_TAG_BY_DLL = 0x00008000
FLG_IGNORE_DEBUG_PRIV = 0x00010000
FLG_ENABLE_CSRDEBUG = 0x00020000
FLG_ENABLE_KDEBUG_SYMBOL_LOAD = 0x00040000
FLG_DISABLE_PAGE_KERNEL_STACKS = 0x00080000
FLG_HEAP_ENABLE_CALL_TRACING = 0x00100000
FLG_HEAP_DISABLE_COALESCING = 0x00200000
FLG_ENABLE_CLOSE_EXCEPTION = 0x00400000
FLG_ENABLE_EXCEPTION_LOGGING = 0x00800000
FLG_ENABLE_HANDLE_TYPE_TAGGING = 0x01000000
FLG_HEAP_PAGE_ALLOCS = 0x02000000
FLG_DEBUG_WINLOGON = 0x04000000
FLG_ENABLE_DBGPRINT_BUFFERING = 0x08000000
FLG_EARLY_CRITICAL_SECTION_EVT = 0x10000000
FLG_DISABLE_DLL_VERIFICATION = 0x80000000


class _PEB_NT(Structure):
    _pack_ = 4
    _fields_ = [
        ("InheritedAddressSpace", BOOLEAN),
        ("ReadImageFileExecOptions", UCHAR),
        ("BeingDebugged", BOOLEAN),
        ("BitField", UCHAR),
        ("Mutant", HANDLE),
        ("ImageBaseAddress", PVOID),
        ("Ldr", PVOID),  # PPEB_LDR_DATA
        ("ProcessParameters", PVOID),  # PRTL_USER_PROCESS_PARAMETERS
        ("SubSystemData", PVOID),
        ("ProcessHeap", PVOID),
        ("FastPebLock", PVOID),
        ("FastPebLockRoutine", PVOID),  # PPEBLOCKROUTINE
        ("FastPebUnlockRoutine", PVOID),  # PPEBLOCKROUTINE
        ("EnvironmentUpdateCount", ULONG),
        ("KernelCallbackTable", PVOID),  # Ptr32 Ptr32 Void
        ("EventLogSection", PVOID),
        ("EventLog", PVOID),
        ("FreeList", PVOID),  # PPEB_FREE_BLOCK
        ("TlsExpansionCounter", ULONG),
        ("TlsBitmap", PVOID),
        ("TlsBitmapBits", ULONG * 2),
        ("ReadOnlySharedMemoryBase", PVOID),
        ("ReadOnlySharedMemoryHeap", PVOID),
        ("ReadOnlyStaticServerData", PVOID),  # Ptr32 Ptr32 Void
        ("AnsiCodePageData", PVOID),
        ("OemCodePageData", PVOID),
        ("UnicodeCaseTableData", PVOID),
        ("NumberOfProcessors", ULONG),
        ("NtGlobalFlag", ULONG),
        ("Spare2", BYTE * 4),
        ("CriticalSectionTimeout", LONGLONG),  # LARGE_INTEGER
        ("HeapSegmentReserve", ULONG),
        ("HeapSegmentCommit", ULONG),
        ("HeapDeCommitTotalFreeThreshold", ULONG),
        ("HeapDeCommitFreeBlockThreshold", ULONG),
        ("NumberOfHeaps", ULONG),
        ("MaximumNumberOfHeaps", ULONG),
        ("ProcessHeaps", PVOID),  # Ptr32 Ptr32 Void
        ("GdiSharedHandleTable", PVOID),
        ("ProcessStarterHelper", PVOID),
        ("GdiDCAttributeList", PVOID),
        ("LoaderLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("OSMajorVersion", ULONG),
        ("OSMinorVersion", ULONG),
        ("OSBuildNumber", ULONG),
        ("OSPlatformId", ULONG),
        ("ImageSubSystem", ULONG),
        ("ImageSubSystemMajorVersion", ULONG),
        ("ImageSubSystemMinorVersion", ULONG),
        ("ImageProcessAffinityMask", ULONG),
        ("GdiHandleBuffer", ULONG * 34),
        ("PostProcessInitRoutine", PPS_POST_PROCESS_INIT_ROUTINE),
        ("TlsExpansionBitmap", ULONG),
        ("TlsExpansionBitmapBits", BYTE * 128),
        ("SessionId", ULONG),
    ]


# not really, but "dt _PEB" in w2k isn't working for me :(
_PEB_2000 = _PEB_NT


#    +0x000 InheritedAddressSpace : UChar
#    +0x001 ReadImageFileExecOptions : UChar
#    +0x002 BeingDebugged    : UChar
#    +0x003 SpareBool        : UChar
#    +0x004 Mutant           : Ptr32 Void
#    +0x008 ImageBaseAddress : Ptr32 Void
#    +0x00c Ldr              : Ptr32 _PEB_LDR_DATA
#    +0x010 ProcessParameters : Ptr32 _RTL_USER_PROCESS_PARAMETERS
#    +0x014 SubSystemData    : Ptr32 Void
#    +0x018 ProcessHeap      : Ptr32 Void
#    +0x01c FastPebLock      : Ptr32 _RTL_CRITICAL_SECTION
#    +0x020 FastPebLockRoutine : Ptr32 Void
#    +0x024 FastPebUnlockRoutine : Ptr32 Void
#    +0x028 EnvironmentUpdateCount : Uint4B
#    +0x02c KernelCallbackTable : Ptr32 Void
#    +0x030 SystemReserved   : [1] Uint4B
#    +0x034 AtlThunkSListPtr32 : Uint4B
#    +0x038 FreeList         : Ptr32 _PEB_FREE_BLOCK
#    +0x03c TlsExpansionCounter : Uint4B
#    +0x040 TlsBitmap        : Ptr32 Void
#    +0x044 TlsBitmapBits    : [2] Uint4B
#    +0x04c ReadOnlySharedMemoryBase : Ptr32 Void
#    +0x050 ReadOnlySharedMemoryHeap : Ptr32 Void
#    +0x054 ReadOnlyStaticServerData : Ptr32 Ptr32 Void
#    +0x058 AnsiCodePageData : Ptr32 Void
#    +0x05c OemCodePageData  : Ptr32 Void
#    +0x060 UnicodeCaseTableData : Ptr32 Void
#    +0x064 NumberOfProcessors : Uint4B
#    +0x068 NtGlobalFlag     : Uint4B
#    +0x070 CriticalSectionTimeout : _LARGE_INTEGER
#    +0x078 HeapSegmentReserve : Uint4B
#    +0x07c HeapSegmentCommit : Uint4B
#    +0x080 HeapDeCommitTotalFreeThreshold : Uint4B
#    +0x084 HeapDeCommitFreeBlockThreshold : Uint4B
#    +0x088 NumberOfHeaps    : Uint4B
#    +0x08c MaximumNumberOfHeaps : Uint4B
#    +0x090 ProcessHeaps     : Ptr32 Ptr32 Void
#    +0x094 GdiSharedHandleTable : Ptr32 Void
#    +0x098 ProcessStarterHelper : Ptr32 Void
#    +0x09c GdiDCAttributeList : Uint4B
#    +0x0a0 LoaderLock       : Ptr32 Void
#    +0x0a4 OSMajorVersion   : Uint4B
#    +0x0a8 OSMinorVersion   : Uint4B
#    +0x0ac OSBuildNumber    : Uint2B
#    +0x0ae OSCSDVersion     : Uint2B
#    +0x0b0 OSPlatformId     : Uint4B
#    +0x0b4 ImageSubsystem   : Uint4B
#    +0x0b8 ImageSubsystemMajorVersion : Uint4B
#    +0x0bc ImageSubsystemMinorVersion : Uint4B
#    +0x0c0 ImageProcessAffinityMask : Uint4B
#    +0x0c4 GdiHandleBuffer  : [34] Uint4B
#    +0x14c PostProcessInitRoutine : Ptr32     void
#    +0x150 TlsExpansionBitmap : Ptr32 Void
#    +0x154 TlsExpansionBitmapBits : [32] Uint4B
#    +0x1d4 SessionId        : Uint4B
#    +0x1d8 AppCompatFlags   : _ULARGE_INTEGER
#    +0x1e0 AppCompatFlagsUser : _ULARGE_INTEGER
#    +0x1e8 pShimData        : Ptr32 Void
#    +0x1ec AppCompatInfo    : Ptr32 Void
#    +0x1f0 CSDVersion       : _UNICODE_STRING
#    +0x1f8 ActivationContextData : Ptr32 Void
#    +0x1fc ProcessAssemblyStorageMap : Ptr32 Void
#    +0x200 SystemDefaultActivationContextData : Ptr32 Void
#    +0x204 SystemAssemblyStorageMap : Ptr32 Void
#    +0x208 MinimumStackCommit : Uint4B
class _PEB_XP(Structure):
    _pack_ = 8
    _fields_ = [
        ("InheritedAddressSpace", BOOLEAN),
        ("ReadImageFileExecOptions", UCHAR),
        ("BeingDebugged", BOOLEAN),
        ("SpareBool", UCHAR),
        ("Mutant", HANDLE),
        ("ImageBaseAddress", PVOID),
        ("Ldr", PVOID),  # PPEB_LDR_DATA
        ("ProcessParameters", PVOID),  # PRTL_USER_PROCESS_PARAMETERS
        ("SubSystemData", PVOID),
        ("ProcessHeap", PVOID),
        ("FastPebLock", PVOID),
        ("FastPebLockRoutine", PVOID),
        ("FastPebUnlockRoutine", PVOID),
        ("EnvironmentUpdateCount", DWORD),
        ("KernelCallbackTable", PVOID),
        ("SystemReserved", DWORD),
        ("AtlThunkSListPtr32", DWORD),
        ("FreeList", PVOID),  # PPEB_FREE_BLOCK
        ("TlsExpansionCounter", DWORD),
        ("TlsBitmap", PVOID),
        ("TlsBitmapBits", DWORD * 2),
        ("ReadOnlySharedMemoryBase", PVOID),
        ("ReadOnlySharedMemoryHeap", PVOID),
        ("ReadOnlyStaticServerData", PVOID),  # Ptr32 Ptr32 Void
        ("AnsiCodePageData", PVOID),
        ("OemCodePageData", PVOID),
        ("UnicodeCaseTableData", PVOID),
        ("NumberOfProcessors", DWORD),
        ("NtGlobalFlag", DWORD),
        ("CriticalSectionTimeout", LONGLONG),  # LARGE_INTEGER
        ("HeapSegmentReserve", DWORD),
        ("HeapSegmentCommit", DWORD),
        ("HeapDeCommitTotalFreeThreshold", DWORD),
        ("HeapDeCommitFreeBlockThreshold", DWORD),
        ("NumberOfHeaps", DWORD),
        ("MaximumNumberOfHeaps", DWORD),
        ("ProcessHeaps", PVOID),  # Ptr32 Ptr32 Void
        ("GdiSharedHandleTable", PVOID),
        ("ProcessStarterHelper", PVOID),
        ("GdiDCAttributeList", DWORD),
        ("LoaderLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("OSMajorVersion", DWORD),
        ("OSMinorVersion", DWORD),
        ("OSBuildNumber", WORD),
        ("OSCSDVersion", WORD),
        ("OSPlatformId", DWORD),
        ("ImageSubsystem", DWORD),
        ("ImageSubsystemMajorVersion", DWORD),
        ("ImageSubsystemMinorVersion", DWORD),
        ("ImageProcessAffinityMask", DWORD),
        ("GdiHandleBuffer", DWORD * 34),
        ("PostProcessInitRoutine", PPS_POST_PROCESS_INIT_ROUTINE),
        ("TlsExpansionBitmap", PVOID),
        ("TlsExpansionBitmapBits", DWORD * 32),
        ("SessionId", DWORD),
        ("AppCompatFlags", ULONGLONG),  # ULARGE_INTEGER
        ("AppCompatFlagsUser", ULONGLONG),  # ULARGE_INTEGER
        ("pShimData", PVOID),
        ("AppCompatInfo", PVOID),
        ("CSDVersion", UNICODE_STRING),
        ("ActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("ProcessAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("SystemDefaultActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("SystemAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("MinimumStackCommit", DWORD),
    ]


#    +0x000 InheritedAddressSpace : UChar
#    +0x001 ReadImageFileExecOptions : UChar
#    +0x002 BeingDebugged    : UChar
#    +0x003 BitField         : UChar
#    +0x003 ImageUsesLargePages : Pos 0, 1 Bit
#    +0x003 SpareBits        : Pos 1, 7 Bits
#    +0x008 Mutant           : Ptr64 Void
#    +0x010 ImageBaseAddress : Ptr64 Void
#    +0x018 Ldr              : Ptr64 _PEB_LDR_DATA
#    +0x020 ProcessParameters : Ptr64 _RTL_USER_PROCESS_PARAMETERS
#    +0x028 SubSystemData    : Ptr64 Void
#    +0x030 ProcessHeap      : Ptr64 Void
#    +0x038 FastPebLock      : Ptr64 _RTL_CRITICAL_SECTION
#    +0x040 AtlThunkSListPtr : Ptr64 Void
#    +0x048 SparePtr2        : Ptr64 Void
#    +0x050 EnvironmentUpdateCount : Uint4B
#    +0x058 KernelCallbackTable : Ptr64 Void
#    +0x060 SystemReserved   : [1] Uint4B
#    +0x064 SpareUlong       : Uint4B
#    +0x068 FreeList         : Ptr64 _PEB_FREE_BLOCK
#    +0x070 TlsExpansionCounter : Uint4B
#    +0x078 TlsBitmap        : Ptr64 Void
#    +0x080 TlsBitmapBits    : [2] Uint4B
#    +0x088 ReadOnlySharedMemoryBase : Ptr64 Void
#    +0x090 ReadOnlySharedMemoryHeap : Ptr64 Void
#    +0x098 ReadOnlyStaticServerData : Ptr64 Ptr64 Void
#    +0x0a0 AnsiCodePageData : Ptr64 Void
#    +0x0a8 OemCodePageData  : Ptr64 Void
#    +0x0b0 UnicodeCaseTableData : Ptr64 Void
#    +0x0b8 NumberOfProcessors : Uint4B
#    +0x0bc NtGlobalFlag     : Uint4B
#    +0x0c0 CriticalSectionTimeout : _LARGE_INTEGER
#    +0x0c8 HeapSegmentReserve : Uint8B
#    +0x0d0 HeapSegmentCommit : Uint8B
#    +0x0d8 HeapDeCommitTotalFreeThreshold : Uint8B
#    +0x0e0 HeapDeCommitFreeBlockThreshold : Uint8B
#    +0x0e8 NumberOfHeaps    : Uint4B
#    +0x0ec MaximumNumberOfHeaps : Uint4B
#    +0x0f0 ProcessHeaps     : Ptr64 Ptr64 Void
#    +0x0f8 GdiSharedHandleTable : Ptr64 Void
#    +0x100 ProcessStarterHelper : Ptr64 Void
#    +0x108 GdiDCAttributeList : Uint4B
#    +0x110 LoaderLock       : Ptr64 _RTL_CRITICAL_SECTION
#    +0x118 OSMajorVersion   : Uint4B
#    +0x11c OSMinorVersion   : Uint4B
#    +0x120 OSBuildNumber    : Uint2B
#    +0x122 OSCSDVersion     : Uint2B
#    +0x124 OSPlatformId     : Uint4B
#    +0x128 ImageSubsystem   : Uint4B
#    +0x12c ImageSubsystemMajorVersion : Uint4B
#    +0x130 ImageSubsystemMinorVersion : Uint4B
#    +0x138 ImageProcessAffinityMask : Uint8B
#    +0x140 GdiHandleBuffer  : [60] Uint4B
#    +0x230 PostProcessInitRoutine : Ptr64     void
#    +0x238 TlsExpansionBitmap : Ptr64 Void
#    +0x240 TlsExpansionBitmapBits : [32] Uint4B
#    +0x2c0 SessionId        : Uint4B
#    +0x2c8 AppCompatFlags   : _ULARGE_INTEGER
#    +0x2d0 AppCompatFlagsUser : _ULARGE_INTEGER
#    +0x2d8 pShimData        : Ptr64 Void
#    +0x2e0 AppCompatInfo    : Ptr64 Void
#    +0x2e8 CSDVersion       : _UNICODE_STRING
#    +0x2f8 ActivationContextData : Ptr64 _ACTIVATION_CONTEXT_DATA
#    +0x300 ProcessAssemblyStorageMap : Ptr64 _ASSEMBLY_STORAGE_MAP
#    +0x308 SystemDefaultActivationContextData : Ptr64 _ACTIVATION_CONTEXT_DATA
#    +0x310 SystemAssemblyStorageMap : Ptr64 _ASSEMBLY_STORAGE_MAP
#    +0x318 MinimumStackCommit : Uint8B
#    +0x320 FlsCallback      : Ptr64 Ptr64 Void
#    +0x328 FlsListHead      : _LIST_ENTRY
#    +0x338 FlsBitmap        : Ptr64 Void
#    +0x340 FlsBitmapBits    : [4] Uint4B
#    +0x350 FlsHighIndex     : Uint4B
class _PEB_XP_64(Structure):
    _pack_ = 8
    _fields_ = [
        ("InheritedAddressSpace", BOOLEAN),
        ("ReadImageFileExecOptions", UCHAR),
        ("BeingDebugged", BOOLEAN),
        ("BitField", UCHAR),
        ("Mutant", HANDLE),
        ("ImageBaseAddress", PVOID),
        ("Ldr", PVOID),  # PPEB_LDR_DATA
        ("ProcessParameters", PVOID),  # PRTL_USER_PROCESS_PARAMETERS
        ("SubSystemData", PVOID),
        ("ProcessHeap", PVOID),
        ("FastPebLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("AtlThunkSListPtr", PVOID),
        ("SparePtr2", PVOID),
        ("EnvironmentUpdateCount", DWORD),
        ("KernelCallbackTable", PVOID),
        ("SystemReserved", DWORD),
        ("SpareUlong", DWORD),
        ("FreeList", PVOID),  # PPEB_FREE_BLOCK
        ("TlsExpansionCounter", DWORD),
        ("TlsBitmap", PVOID),
        ("TlsBitmapBits", DWORD * 2),
        ("ReadOnlySharedMemoryBase", PVOID),
        ("ReadOnlySharedMemoryHeap", PVOID),
        ("ReadOnlyStaticServerData", PVOID),  # Ptr64 Ptr64 Void
        ("AnsiCodePageData", PVOID),
        ("OemCodePageData", PVOID),
        ("UnicodeCaseTableData", PVOID),
        ("NumberOfProcessors", DWORD),
        ("NtGlobalFlag", DWORD),
        ("CriticalSectionTimeout", LONGLONG),  # LARGE_INTEGER
        ("HeapSegmentReserve", QWORD),
        ("HeapSegmentCommit", QWORD),
        ("HeapDeCommitTotalFreeThreshold", QWORD),
        ("HeapDeCommitFreeBlockThreshold", QWORD),
        ("NumberOfHeaps", DWORD),
        ("MaximumNumberOfHeaps", DWORD),
        ("ProcessHeaps", PVOID),  # Ptr64 Ptr64 Void
        ("GdiSharedHandleTable", PVOID),
        ("ProcessStarterHelper", PVOID),
        ("GdiDCAttributeList", DWORD),
        ("LoaderLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("OSMajorVersion", DWORD),
        ("OSMinorVersion", DWORD),
        ("OSBuildNumber", WORD),
        ("OSCSDVersion", WORD),
        ("OSPlatformId", DWORD),
        ("ImageSubsystem", DWORD),
        ("ImageSubsystemMajorVersion", DWORD),
        ("ImageSubsystemMinorVersion", DWORD),
        ("ImageProcessAffinityMask", QWORD),
        ("GdiHandleBuffer", DWORD * 60),
        ("PostProcessInitRoutine", PPS_POST_PROCESS_INIT_ROUTINE),
        ("TlsExpansionBitmap", PVOID),
        ("TlsExpansionBitmapBits", DWORD * 32),
        ("SessionId", DWORD),
        ("AppCompatFlags", ULONGLONG),  # ULARGE_INTEGER
        ("AppCompatFlagsUser", ULONGLONG),  # ULARGE_INTEGER
        ("pShimData", PVOID),
        ("AppCompatInfo", PVOID),
        ("CSDVersion", UNICODE_STRING),
        ("ActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("ProcessAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("SystemDefaultActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("SystemAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("MinimumStackCommit", QWORD),
        ("FlsCallback", PVOID),  # Ptr64 Ptr64 Void
        ("FlsListHead", LIST_ENTRY),
        ("FlsBitmap", PVOID),
        ("FlsBitmapBits", DWORD * 4),
        ("FlsHighIndex", DWORD),
    ]


#    +0x000 InheritedAddressSpace : UChar
#    +0x001 ReadImageFileExecOptions : UChar
#    +0x002 BeingDebugged    : UChar
#    +0x003 BitField         : UChar
#    +0x003 ImageUsesLargePages : Pos 0, 1 Bit
#    +0x003 SpareBits        : Pos 1, 7 Bits
#    +0x004 Mutant           : Ptr32 Void
#    +0x008 ImageBaseAddress : Ptr32 Void
#    +0x00c Ldr              : Ptr32 _PEB_LDR_DATA
#    +0x010 ProcessParameters : Ptr32 _RTL_USER_PROCESS_PARAMETERS
#    +0x014 SubSystemData    : Ptr32 Void
#    +0x018 ProcessHeap      : Ptr32 Void
#    +0x01c FastPebLock      : Ptr32 _RTL_CRITICAL_SECTION
#    +0x020 AtlThunkSListPtr : Ptr32 Void
#    +0x024 SparePtr2        : Ptr32 Void
#    +0x028 EnvironmentUpdateCount : Uint4B
#    +0x02c KernelCallbackTable : Ptr32 Void
#    +0x030 SystemReserved   : [1] Uint4B
#    +0x034 SpareUlong       : Uint4B
#    +0x038 FreeList         : Ptr32 _PEB_FREE_BLOCK
#    +0x03c TlsExpansionCounter : Uint4B
#    +0x040 TlsBitmap        : Ptr32 Void
#    +0x044 TlsBitmapBits    : [2] Uint4B
#    +0x04c ReadOnlySharedMemoryBase : Ptr32 Void
#    +0x050 ReadOnlySharedMemoryHeap : Ptr32 Void
#    +0x054 ReadOnlyStaticServerData : Ptr32 Ptr32 Void
#    +0x058 AnsiCodePageData : Ptr32 Void
#    +0x05c OemCodePageData  : Ptr32 Void
#    +0x060 UnicodeCaseTableData : Ptr32 Void
#    +0x064 NumberOfProcessors : Uint4B
#    +0x068 NtGlobalFlag     : Uint4B
#    +0x070 CriticalSectionTimeout : _LARGE_INTEGER
#    +0x078 HeapSegmentReserve : Uint4B
#    +0x07c HeapSegmentCommit : Uint4B
#    +0x080 HeapDeCommitTotalFreeThreshold : Uint4B
#    +0x084 HeapDeCommitFreeBlockThreshold : Uint4B
#    +0x088 NumberOfHeaps    : Uint4B
#    +0x08c MaximumNumberOfHeaps : Uint4B
#    +0x090 ProcessHeaps     : Ptr32 Ptr32 Void
#    +0x094 GdiSharedHandleTable : Ptr32 Void
#    +0x098 ProcessStarterHelper : Ptr32 Void
#    +0x09c GdiDCAttributeList : Uint4B
#    +0x0a0 LoaderLock       : Ptr32 _RTL_CRITICAL_SECTION
#    +0x0a4 OSMajorVersion   : Uint4B
#    +0x0a8 OSMinorVersion   : Uint4B
#    +0x0ac OSBuildNumber    : Uint2B
#    +0x0ae OSCSDVersion     : Uint2B
#    +0x0b0 OSPlatformId     : Uint4B
#    +0x0b4 ImageSubsystem   : Uint4B
#    +0x0b8 ImageSubsystemMajorVersion : Uint4B
#    +0x0bc ImageSubsystemMinorVersion : Uint4B
#    +0x0c0 ImageProcessAffinityMask : Uint4B
#    +0x0c4 GdiHandleBuffer  : [34] Uint4B
#    +0x14c PostProcessInitRoutine : Ptr32     void
#    +0x150 TlsExpansionBitmap : Ptr32 Void
#    +0x154 TlsExpansionBitmapBits : [32] Uint4B
#    +0x1d4 SessionId        : Uint4B
#    +0x1d8 AppCompatFlags   : _ULARGE_INTEGER
#    +0x1e0 AppCompatFlagsUser : _ULARGE_INTEGER
#    +0x1e8 pShimData        : Ptr32 Void
#    +0x1ec AppCompatInfo    : Ptr32 Void
#    +0x1f0 CSDVersion       : _UNICODE_STRING
#    +0x1f8 ActivationContextData : Ptr32 _ACTIVATION_CONTEXT_DATA
#    +0x1fc ProcessAssemblyStorageMap : Ptr32 _ASSEMBLY_STORAGE_MAP
#    +0x200 SystemDefaultActivationContextData : Ptr32 _ACTIVATION_CONTEXT_DATA
#    +0x204 SystemAssemblyStorageMap : Ptr32 _ASSEMBLY_STORAGE_MAP
#    +0x208 MinimumStackCommit : Uint4B
#    +0x20c FlsCallback      : Ptr32 Ptr32 Void
#    +0x210 FlsListHead      : _LIST_ENTRY
#    +0x218 FlsBitmap        : Ptr32 Void
#    +0x21c FlsBitmapBits    : [4] Uint4B
#    +0x22c FlsHighIndex     : Uint4B
class _PEB_2003(Structure):
    _pack_ = 8
    _fields_ = [
        ("InheritedAddressSpace", BOOLEAN),
        ("ReadImageFileExecOptions", UCHAR),
        ("BeingDebugged", BOOLEAN),
        ("BitField", UCHAR),
        ("Mutant", HANDLE),
        ("ImageBaseAddress", PVOID),
        ("Ldr", PVOID),  # PPEB_LDR_DATA
        ("ProcessParameters", PVOID),  # PRTL_USER_PROCESS_PARAMETERS
        ("SubSystemData", PVOID),
        ("ProcessHeap", PVOID),
        ("FastPebLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("AtlThunkSListPtr", PVOID),
        ("SparePtr2", PVOID),
        ("EnvironmentUpdateCount", DWORD),
        ("KernelCallbackTable", PVOID),
        ("SystemReserved", DWORD),
        ("SpareUlong", DWORD),
        ("FreeList", PVOID),  # PPEB_FREE_BLOCK
        ("TlsExpansionCounter", DWORD),
        ("TlsBitmap", PVOID),
        ("TlsBitmapBits", DWORD * 2),
        ("ReadOnlySharedMemoryBase", PVOID),
        ("ReadOnlySharedMemoryHeap", PVOID),
        ("ReadOnlyStaticServerData", PVOID),  # Ptr32 Ptr32 Void
        ("AnsiCodePageData", PVOID),
        ("OemCodePageData", PVOID),
        ("UnicodeCaseTableData", PVOID),
        ("NumberOfProcessors", DWORD),
        ("NtGlobalFlag", DWORD),
        ("CriticalSectionTimeout", LONGLONG),  # LARGE_INTEGER
        ("HeapSegmentReserve", DWORD),
        ("HeapSegmentCommit", DWORD),
        ("HeapDeCommitTotalFreeThreshold", DWORD),
        ("HeapDeCommitFreeBlockThreshold", DWORD),
        ("NumberOfHeaps", DWORD),
        ("MaximumNumberOfHeaps", DWORD),
        ("ProcessHeaps", PVOID),  # Ptr32 Ptr32 Void
        ("GdiSharedHandleTable", PVOID),
        ("ProcessStarterHelper", PVOID),
        ("GdiDCAttributeList", DWORD),
        ("LoaderLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("OSMajorVersion", DWORD),
        ("OSMinorVersion", DWORD),
        ("OSBuildNumber", WORD),
        ("OSCSDVersion", WORD),
        ("OSPlatformId", DWORD),
        ("ImageSubsystem", DWORD),
        ("ImageSubsystemMajorVersion", DWORD),
        ("ImageSubsystemMinorVersion", DWORD),
        ("ImageProcessAffinityMask", DWORD),
        ("GdiHandleBuffer", DWORD * 34),
        ("PostProcessInitRoutine", PPS_POST_PROCESS_INIT_ROUTINE),
        ("TlsExpansionBitmap", PVOID),
        ("TlsExpansionBitmapBits", DWORD * 32),
        ("SessionId", DWORD),
        ("AppCompatFlags", ULONGLONG),  # ULARGE_INTEGER
        ("AppCompatFlagsUser", ULONGLONG),  # ULARGE_INTEGER
        ("pShimData", PVOID),
        ("AppCompatInfo", PVOID),
        ("CSDVersion", UNICODE_STRING),
        ("ActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("ProcessAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("SystemDefaultActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("SystemAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("MinimumStackCommit", QWORD),
        ("FlsCallback", PVOID),  # Ptr32 Ptr32 Void
        ("FlsListHead", LIST_ENTRY),
        ("FlsBitmap", PVOID),
        ("FlsBitmapBits", DWORD * 4),
        ("FlsHighIndex", DWORD),
    ]


_PEB_2003_64 = _PEB_XP_64
_PEB_2003_R2 = _PEB_2003
_PEB_2003_R2_64 = _PEB_2003_64


#    +0x000 InheritedAddressSpace : UChar
#    +0x001 ReadImageFileExecOptions : UChar
#    +0x002 BeingDebugged    : UChar
#    +0x003 BitField         : UChar
#    +0x003 ImageUsesLargePages : Pos 0, 1 Bit
#    +0x003 IsProtectedProcess : Pos 1, 1 Bit
#    +0x003 IsLegacyProcess  : Pos 2, 1 Bit
#    +0x003 IsImageDynamicallyRelocated : Pos 3, 1 Bit
#    +0x003 SkipPatchingUser32Forwarders : Pos 4, 1 Bit
#    +0x003 SpareBits        : Pos 5, 3 Bits
#    +0x004 Mutant           : Ptr32 Void
#    +0x008 ImageBaseAddress : Ptr32 Void
#    +0x00c Ldr              : Ptr32 _PEB_LDR_DATA
#    +0x010 ProcessParameters : Ptr32 _RTL_USER_PROCESS_PARAMETERS
#    +0x014 SubSystemData    : Ptr32 Void
#    +0x018 ProcessHeap      : Ptr32 Void
#    +0x01c FastPebLock      : Ptr32 _RTL_CRITICAL_SECTION
#    +0x020 AtlThunkSListPtr : Ptr32 Void
#    +0x024 IFEOKey          : Ptr32 Void
#    +0x028 CrossProcessFlags : Uint4B
#    +0x028 ProcessInJob     : Pos 0, 1 Bit
#    +0x028 ProcessInitializing : Pos 1, 1 Bit
#    +0x028 ProcessUsingVEH  : Pos 2, 1 Bit
#    +0x028 ProcessUsingVCH  : Pos 3, 1 Bit
#    +0x028 ReservedBits0    : Pos 4, 28 Bits
#    +0x02c KernelCallbackTable : Ptr32 Void
#    +0x02c UserSharedInfoPtr : Ptr32 Void
#    +0x030 SystemReserved   : [1] Uint4B
#    +0x034 SpareUlong       : Uint4B
#    +0x038 SparePebPtr0     : Uint4B
#    +0x03c TlsExpansionCounter : Uint4B
#    +0x040 TlsBitmap        : Ptr32 Void
#    +0x044 TlsBitmapBits    : [2] Uint4B
#    +0x04c ReadOnlySharedMemoryBase : Ptr32 Void
#    +0x050 HotpatchInformation : Ptr32 Void
#    +0x054 ReadOnlyStaticServerData : Ptr32 Ptr32 Void
#    +0x058 AnsiCodePageData : Ptr32 Void
#    +0x05c OemCodePageData  : Ptr32 Void
#    +0x060 UnicodeCaseTableData : Ptr32 Void
#    +0x064 NumberOfProcessors : Uint4B
#    +0x068 NtGlobalFlag     : Uint4B
#    +0x070 CriticalSectionTimeout : _LARGE_INTEGER
#    +0x078 HeapSegmentReserve : Uint4B
#    +0x07c HeapSegmentCommit : Uint4B
#    +0x080 HeapDeCommitTotalFreeThreshold : Uint4B
#    +0x084 HeapDeCommitFreeBlockThreshold : Uint4B
#    +0x088 NumberOfHeaps    : Uint4B
#    +0x08c MaximumNumberOfHeaps : Uint4B
#    +0x090 ProcessHeaps     : Ptr32 Ptr32 Void
#    +0x094 GdiSharedHandleTable : Ptr32 Void
#    +0x098 ProcessStarterHelper : Ptr32 Void
#    +0x09c GdiDCAttributeList : Uint4B
#    +0x0a0 LoaderLock       : Ptr32 _RTL_CRITICAL_SECTION
#    +0x0a4 OSMajorVersion   : Uint4B
#    +0x0a8 OSMinorVersion   : Uint4B
#    +0x0ac OSBuildNumber    : Uint2B
#    +0x0ae OSCSDVersion     : Uint2B
#    +0x0b0 OSPlatformId     : Uint4B
#    +0x0b4 ImageSubsystem   : Uint4B
#    +0x0b8 ImageSubsystemMajorVersion : Uint4B
#    +0x0bc ImageSubsystemMinorVersion : Uint4B
#    +0x0c0 ActiveProcessAffinityMask : Uint4B
#    +0x0c4 GdiHandleBuffer  : [34] Uint4B
#    +0x14c PostProcessInitRoutine : Ptr32     void
#    +0x150 TlsExpansionBitmap : Ptr32 Void
#    +0x154 TlsExpansionBitmapBits : [32] Uint4B
#    +0x1d4 SessionId        : Uint4B
#    +0x1d8 AppCompatFlags   : _ULARGE_INTEGER
#    +0x1e0 AppCompatFlagsUser : _ULARGE_INTEGER
#    +0x1e8 pShimData        : Ptr32 Void
#    +0x1ec AppCompatInfo    : Ptr32 Void
#    +0x1f0 CSDVersion       : _UNICODE_STRING
#    +0x1f8 ActivationContextData : Ptr32 _ACTIVATION_CONTEXT_DATA
#    +0x1fc ProcessAssemblyStorageMap : Ptr32 _ASSEMBLY_STORAGE_MAP
#    +0x200 SystemDefaultActivationContextData : Ptr32 _ACTIVATION_CONTEXT_DATA
#    +0x204 SystemAssemblyStorageMap : Ptr32 _ASSEMBLY_STORAGE_MAP
#    +0x208 MinimumStackCommit : Uint4B
#    +0x20c FlsCallback      : Ptr32 _FLS_CALLBACK_INFO
#    +0x210 FlsListHead      : _LIST_ENTRY
#    +0x218 FlsBitmap        : Ptr32 Void
#    +0x21c FlsBitmapBits    : [4] Uint4B
#    +0x22c FlsHighIndex     : Uint4B
#    +0x230 WerRegistrationData : Ptr32 Void
#    +0x234 WerShipAssertPtr : Ptr32 Void
class _PEB_2008(Structure):
    _pack_ = 8
    _fields_ = [
        ("InheritedAddressSpace", BOOLEAN),
        ("ReadImageFileExecOptions", UCHAR),
        ("BeingDebugged", BOOLEAN),
        ("BitField", UCHAR),
        ("Mutant", HANDLE),
        ("ImageBaseAddress", PVOID),
        ("Ldr", PVOID),  # PPEB_LDR_DATA
        ("ProcessParameters", PVOID),  # PRTL_USER_PROCESS_PARAMETERS
        ("SubSystemData", PVOID),
        ("ProcessHeap", PVOID),
        ("FastPebLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("AtlThunkSListPtr", PVOID),
        ("IFEOKey", PVOID),
        ("CrossProcessFlags", DWORD),
        ("KernelCallbackTable", PVOID),
        ("SystemReserved", DWORD),
        ("SpareUlong", DWORD),
        ("SparePebPtr0", PVOID),
        ("TlsExpansionCounter", DWORD),
        ("TlsBitmap", PVOID),
        ("TlsBitmapBits", DWORD * 2),
        ("ReadOnlySharedMemoryBase", PVOID),
        ("HotpatchInformation", PVOID),
        ("ReadOnlyStaticServerData", PVOID),  # Ptr32 Ptr32 Void
        ("AnsiCodePageData", PVOID),
        ("OemCodePageData", PVOID),
        ("UnicodeCaseTableData", PVOID),
        ("NumberOfProcessors", DWORD),
        ("NtGlobalFlag", DWORD),
        ("CriticalSectionTimeout", LONGLONG),  # LARGE_INTEGER
        ("HeapSegmentReserve", DWORD),
        ("HeapSegmentCommit", DWORD),
        ("HeapDeCommitTotalFreeThreshold", DWORD),
        ("HeapDeCommitFreeBlockThreshold", DWORD),
        ("NumberOfHeaps", DWORD),
        ("MaximumNumberOfHeaps", DWORD),
        ("ProcessHeaps", PVOID),  # Ptr32 Ptr32 Void
        ("GdiSharedHandleTable", PVOID),
        ("ProcessStarterHelper", PVOID),
        ("GdiDCAttributeList", DWORD),
        ("LoaderLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("OSMajorVersion", DWORD),
        ("OSMinorVersion", DWORD),
        ("OSBuildNumber", WORD),
        ("OSCSDVersion", WORD),
        ("OSPlatformId", DWORD),
        ("ImageSubsystem", DWORD),
        ("ImageSubsystemMajorVersion", DWORD),
        ("ImageSubsystemMinorVersion", DWORD),
        ("ActiveProcessAffinityMask", DWORD),
        ("GdiHandleBuffer", DWORD * 34),
        ("PostProcessInitRoutine", PPS_POST_PROCESS_INIT_ROUTINE),
        ("TlsExpansionBitmap", PVOID),
        ("TlsExpansionBitmapBits", DWORD * 32),
        ("SessionId", DWORD),
        ("AppCompatFlags", ULONGLONG),  # ULARGE_INTEGER
        ("AppCompatFlagsUser", ULONGLONG),  # ULARGE_INTEGER
        ("pShimData", PVOID),
        ("AppCompatInfo", PVOID),
        ("CSDVersion", UNICODE_STRING),
        ("ActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("ProcessAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("SystemDefaultActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("SystemAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("MinimumStackCommit", DWORD),
        ("FlsCallback", PVOID),  # PFLS_CALLBACK_INFO
        ("FlsListHead", LIST_ENTRY),
        ("FlsBitmap", PVOID),
        ("FlsBitmapBits", DWORD * 4),
        ("FlsHighIndex", DWORD),
        ("WerRegistrationData", PVOID),
        ("WerShipAssertPtr", PVOID),
    ]

    def __get_UserSharedInfoPtr(self):
        return self.KernelCallbackTable

    def __set_UserSharedInfoPtr(self, value):
        self.KernelCallbackTable = value

    UserSharedInfoPtr = property(__get_UserSharedInfoPtr, __set_UserSharedInfoPtr)


#    +0x000 InheritedAddressSpace : UChar
#    +0x001 ReadImageFileExecOptions : UChar
#    +0x002 BeingDebugged    : UChar
#    +0x003 BitField         : UChar
#    +0x003 ImageUsesLargePages : Pos 0, 1 Bit
#    +0x003 IsProtectedProcess : Pos 1, 1 Bit
#    +0x003 IsLegacyProcess  : Pos 2, 1 Bit
#    +0x003 IsImageDynamicallyRelocated : Pos 3, 1 Bit
#    +0x003 SkipPatchingUser32Forwarders : Pos 4, 1 Bit
#    +0x003 SpareBits        : Pos 5, 3 Bits
#    +0x008 Mutant           : Ptr64 Void
#    +0x010 ImageBaseAddress : Ptr64 Void
#    +0x018 Ldr              : Ptr64 _PEB_LDR_DATA
#    +0x020 ProcessParameters : Ptr64 _RTL_USER_PROCESS_PARAMETERS
#    +0x028 SubSystemData    : Ptr64 Void
#    +0x030 ProcessHeap      : Ptr64 Void
#    +0x038 FastPebLock      : Ptr64 _RTL_CRITICAL_SECTION
#    +0x040 AtlThunkSListPtr : Ptr64 Void
#    +0x048 IFEOKey          : Ptr64 Void
#    +0x050 CrossProcessFlags : Uint4B
#    +0x050 ProcessInJob     : Pos 0, 1 Bit
#    +0x050 ProcessInitializing : Pos 1, 1 Bit
#    +0x050 ProcessUsingVEH  : Pos 2, 1 Bit
#    +0x050 ProcessUsingVCH  : Pos 3, 1 Bit
#    +0x050 ReservedBits0    : Pos 4, 28 Bits
#    +0x058 KernelCallbackTable : Ptr64 Void
#    +0x058 UserSharedInfoPtr : Ptr64 Void
#    +0x060 SystemReserved   : [1] Uint4B
#    +0x064 SpareUlong       : Uint4B
#    +0x068 SparePebPtr0     : Uint8B
#    +0x070 TlsExpansionCounter : Uint4B
#    +0x078 TlsBitmap        : Ptr64 Void
#    +0x080 TlsBitmapBits    : [2] Uint4B
#    +0x088 ReadOnlySharedMemoryBase : Ptr64 Void
#    +0x090 HotpatchInformation : Ptr64 Void
#    +0x098 ReadOnlyStaticServerData : Ptr64 Ptr64 Void
#    +0x0a0 AnsiCodePageData : Ptr64 Void
#    +0x0a8 OemCodePageData  : Ptr64 Void
#    +0x0b0 UnicodeCaseTableData : Ptr64 Void
#    +0x0b8 NumberOfProcessors : Uint4B
#    +0x0bc NtGlobalFlag     : Uint4B
#    +0x0c0 CriticalSectionTimeout : _LARGE_INTEGER
#    +0x0c8 HeapSegmentReserve : Uint8B
#    +0x0d0 HeapSegmentCommit : Uint8B
#    +0x0d8 HeapDeCommitTotalFreeThreshold : Uint8B
#    +0x0e0 HeapDeCommitFreeBlockThreshold : Uint8B
#    +0x0e8 NumberOfHeaps    : Uint4B
#    +0x0ec MaximumNumberOfHeaps : Uint4B
#    +0x0f0 ProcessHeaps     : Ptr64 Ptr64 Void
#    +0x0f8 GdiSharedHandleTable : Ptr64 Void
#    +0x100 ProcessStarterHelper : Ptr64 Void
#    +0x108 GdiDCAttributeList : Uint4B
#    +0x110 LoaderLock       : Ptr64 _RTL_CRITICAL_SECTION
#    +0x118 OSMajorVersion   : Uint4B
#    +0x11c OSMinorVersion   : Uint4B
#    +0x120 OSBuildNumber    : Uint2B
#    +0x122 OSCSDVersion     : Uint2B
#    +0x124 OSPlatformId     : Uint4B
#    +0x128 ImageSubsystem   : Uint4B
#    +0x12c ImageSubsystemMajorVersion : Uint4B
#    +0x130 ImageSubsystemMinorVersion : Uint4B
#    +0x138 ActiveProcessAffinityMask : Uint8B
#    +0x140 GdiHandleBuffer  : [60] Uint4B
#    +0x230 PostProcessInitRoutine : Ptr64     void
#    +0x238 TlsExpansionBitmap : Ptr64 Void
#    +0x240 TlsExpansionBitmapBits : [32] Uint4B
#    +0x2c0 SessionId        : Uint4B
#    +0x2c8 AppCompatFlags   : _ULARGE_INTEGER
#    +0x2d0 AppCompatFlagsUser : _ULARGE_INTEGER
#    +0x2d8 pShimData        : Ptr64 Void
#    +0x2e0 AppCompatInfo    : Ptr64 Void
#    +0x2e8 CSDVersion       : _UNICODE_STRING
#    +0x2f8 ActivationContextData : Ptr64 _ACTIVATION_CONTEXT_DATA
#    +0x300 ProcessAssemblyStorageMap : Ptr64 _ASSEMBLY_STORAGE_MAP
#    +0x308 SystemDefaultActivationContextData : Ptr64 _ACTIVATION_CONTEXT_DATA
#    +0x310 SystemAssemblyStorageMap : Ptr64 _ASSEMBLY_STORAGE_MAP
#    +0x318 MinimumStackCommit : Uint8B
#    +0x320 FlsCallback      : Ptr64 _FLS_CALLBACK_INFO
#    +0x328 FlsListHead      : _LIST_ENTRY
#    +0x338 FlsBitmap        : Ptr64 Void
#    +0x340 FlsBitmapBits    : [4] Uint4B
#    +0x350 FlsHighIndex     : Uint4B
#    +0x358 WerRegistrationData : Ptr64 Void
#    +0x360 WerShipAssertPtr : Ptr64 Void
class _PEB_2008_64(Structure):
    _pack_ = 8
    _fields_ = [
        ("InheritedAddressSpace", BOOLEAN),
        ("ReadImageFileExecOptions", UCHAR),
        ("BeingDebugged", BOOLEAN),
        ("BitField", UCHAR),
        ("Mutant", HANDLE),
        ("ImageBaseAddress", PVOID),
        ("Ldr", PVOID),  # PPEB_LDR_DATA
        ("ProcessParameters", PVOID),  # PRTL_USER_PROCESS_PARAMETERS
        ("SubSystemData", PVOID),
        ("ProcessHeap", PVOID),
        ("FastPebLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("AtlThunkSListPtr", PVOID),
        ("IFEOKey", PVOID),
        ("CrossProcessFlags", DWORD),
        ("KernelCallbackTable", PVOID),
        ("SystemReserved", DWORD),
        ("SpareUlong", DWORD),
        ("SparePebPtr0", PVOID),
        ("TlsExpansionCounter", DWORD),
        ("TlsBitmap", PVOID),
        ("TlsBitmapBits", DWORD * 2),
        ("ReadOnlySharedMemoryBase", PVOID),
        ("HotpatchInformation", PVOID),
        ("ReadOnlyStaticServerData", PVOID),  # Ptr64 Ptr64 Void
        ("AnsiCodePageData", PVOID),
        ("OemCodePageData", PVOID),
        ("UnicodeCaseTableData", PVOID),
        ("NumberOfProcessors", DWORD),
        ("NtGlobalFlag", DWORD),
        ("CriticalSectionTimeout", LONGLONG),  # LARGE_INTEGER
        ("HeapSegmentReserve", QWORD),
        ("HeapSegmentCommit", QWORD),
        ("HeapDeCommitTotalFreeThreshold", QWORD),
        ("HeapDeCommitFreeBlockThreshold", QWORD),
        ("NumberOfHeaps", DWORD),
        ("MaximumNumberOfHeaps", DWORD),
        ("ProcessHeaps", PVOID),  # Ptr64 Ptr64 Void
        ("GdiSharedHandleTable", PVOID),
        ("ProcessStarterHelper", PVOID),
        ("GdiDCAttributeList", DWORD),
        ("LoaderLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("OSMajorVersion", DWORD),
        ("OSMinorVersion", DWORD),
        ("OSBuildNumber", WORD),
        ("OSCSDVersion", WORD),
        ("OSPlatformId", DWORD),
        ("ImageSubsystem", DWORD),
        ("ImageSubsystemMajorVersion", DWORD),
        ("ImageSubsystemMinorVersion", DWORD),
        ("ActiveProcessAffinityMask", QWORD),
        ("GdiHandleBuffer", DWORD * 60),
        ("PostProcessInitRoutine", PPS_POST_PROCESS_INIT_ROUTINE),
        ("TlsExpansionBitmap", PVOID),
        ("TlsExpansionBitmapBits", DWORD * 32),
        ("SessionId", DWORD),
        ("AppCompatFlags", ULONGLONG),  # ULARGE_INTEGER
        ("AppCompatFlagsUser", ULONGLONG),  # ULARGE_INTEGER
        ("pShimData", PVOID),
        ("AppCompatInfo", PVOID),
        ("CSDVersion", UNICODE_STRING),
        ("ActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("ProcessAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("SystemDefaultActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("SystemAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("MinimumStackCommit", QWORD),
        ("FlsCallback", PVOID),  # PFLS_CALLBACK_INFO
        ("FlsListHead", LIST_ENTRY),
        ("FlsBitmap", PVOID),
        ("FlsBitmapBits", DWORD * 4),
        ("FlsHighIndex", DWORD),
        ("WerRegistrationData", PVOID),
        ("WerShipAssertPtr", PVOID),
    ]

    def __get_UserSharedInfoPtr(self):
        return self.KernelCallbackTable

    def __set_UserSharedInfoPtr(self, value):
        self.KernelCallbackTable = value

    UserSharedInfoPtr = property(__get_UserSharedInfoPtr, __set_UserSharedInfoPtr)


#    +0x000 InheritedAddressSpace : UChar
#    +0x001 ReadImageFileExecOptions : UChar
#    +0x002 BeingDebugged    : UChar
#    +0x003 BitField         : UChar
#    +0x003 ImageUsesLargePages : Pos 0, 1 Bit
#    +0x003 IsProtectedProcess : Pos 1, 1 Bit
#    +0x003 IsLegacyProcess  : Pos 2, 1 Bit
#    +0x003 IsImageDynamicallyRelocated : Pos 3, 1 Bit
#    +0x003 SkipPatchingUser32Forwarders : Pos 4, 1 Bit
#    +0x003 SpareBits        : Pos 5, 3 Bits
#    +0x004 Mutant           : Ptr32 Void
#    +0x008 ImageBaseAddress : Ptr32 Void
#    +0x00c Ldr              : Ptr32 _PEB_LDR_DATA
#    +0x010 ProcessParameters : Ptr32 _RTL_USER_PROCESS_PARAMETERS
#    +0x014 SubSystemData    : Ptr32 Void
#    +0x018 ProcessHeap      : Ptr32 Void
#    +0x01c FastPebLock      : Ptr32 _RTL_CRITICAL_SECTION
#    +0x020 AtlThunkSListPtr : Ptr32 Void
#    +0x024 IFEOKey          : Ptr32 Void
#    +0x028 CrossProcessFlags : Uint4B
#    +0x028 ProcessInJob     : Pos 0, 1 Bit
#    +0x028 ProcessInitializing : Pos 1, 1 Bit
#    +0x028 ProcessUsingVEH  : Pos 2, 1 Bit
#    +0x028 ProcessUsingVCH  : Pos 3, 1 Bit
#    +0x028 ProcessUsingFTH  : Pos 4, 1 Bit
#    +0x028 ReservedBits0    : Pos 5, 27 Bits
#    +0x02c KernelCallbackTable : Ptr32 Void
#    +0x02c UserSharedInfoPtr : Ptr32 Void
#    +0x030 SystemReserved   : [1] Uint4B
#    +0x034 AtlThunkSListPtr32 : Uint4B
#    +0x038 ApiSetMap        : Ptr32 Void
#    +0x03c TlsExpansionCounter : Uint4B
#    +0x040 TlsBitmap        : Ptr32 Void
#    +0x044 TlsBitmapBits    : [2] Uint4B
#    +0x04c ReadOnlySharedMemoryBase : Ptr32 Void
#    +0x050 HotpatchInformation : Ptr32 Void
#    +0x054 ReadOnlyStaticServerData : Ptr32 Ptr32 Void
#    +0x058 AnsiCodePageData : Ptr32 Void
#    +0x05c OemCodePageData  : Ptr32 Void
#    +0x060 UnicodeCaseTableData : Ptr32 Void
#    +0x064 NumberOfProcessors : Uint4B
#    +0x068 NtGlobalFlag     : Uint4B
#    +0x070 CriticalSectionTimeout : _LARGE_INTEGER
#    +0x078 HeapSegmentReserve : Uint4B
#    +0x07c HeapSegmentCommit : Uint4B
#    +0x080 HeapDeCommitTotalFreeThreshold : Uint4B
#    +0x084 HeapDeCommitFreeBlockThreshold : Uint4B
#    +0x088 NumberOfHeaps    : Uint4B
#    +0x08c MaximumNumberOfHeaps : Uint4B
#    +0x090 ProcessHeaps     : Ptr32 Ptr32 Void
#    +0x094 GdiSharedHandleTable : Ptr32 Void
#    +0x098 ProcessStarterHelper : Ptr32 Void
#    +0x09c GdiDCAttributeList : Uint4B
#    +0x0a0 LoaderLock       : Ptr32 _RTL_CRITICAL_SECTION
#    +0x0a4 OSMajorVersion   : Uint4B
#    +0x0a8 OSMinorVersion   : Uint4B
#    +0x0ac OSBuildNumber    : Uint2B
#    +0x0ae OSCSDVersion     : Uint2B
#    +0x0b0 OSPlatformId     : Uint4B
#    +0x0b4 ImageSubsystem   : Uint4B
#    +0x0b8 ImageSubsystemMajorVersion : Uint4B
#    +0x0bc ImageSubsystemMinorVersion : Uint4B
#    +0x0c0 ActiveProcessAffinityMask : Uint4B
#    +0x0c4 GdiHandleBuffer  : [34] Uint4B
#    +0x14c PostProcessInitRoutine : Ptr32     void
#    +0x150 TlsExpansionBitmap : Ptr32 Void
#    +0x154 TlsExpansionBitmapBits : [32] Uint4B
#    +0x1d4 SessionId        : Uint4B
#    +0x1d8 AppCompatFlags   : _ULARGE_INTEGER
#    +0x1e0 AppCompatFlagsUser : _ULARGE_INTEGER
#    +0x1e8 pShimData        : Ptr32 Void
#    +0x1ec AppCompatInfo    : Ptr32 Void
#    +0x1f0 CSDVersion       : _UNICODE_STRING
#    +0x1f8 ActivationContextData : Ptr32 _ACTIVATION_CONTEXT_DATA
#    +0x1fc ProcessAssemblyStorageMap : Ptr32 _ASSEMBLY_STORAGE_MAP
#    +0x200 SystemDefaultActivationContextData : Ptr32 _ACTIVATION_CONTEXT_DATA
#    +0x204 SystemAssemblyStorageMap : Ptr32 _ASSEMBLY_STORAGE_MAP
#    +0x208 MinimumStackCommit : Uint4B
#    +0x20c FlsCallback      : Ptr32 _FLS_CALLBACK_INFO
#    +0x210 FlsListHead      : _LIST_ENTRY
#    +0x218 FlsBitmap        : Ptr32 Void
#    +0x21c FlsBitmapBits    : [4] Uint4B
#    +0x22c FlsHighIndex     : Uint4B
#    +0x230 WerRegistrationData : Ptr32 Void
#    +0x234 WerShipAssertPtr : Ptr32 Void
#    +0x238 pContextData     : Ptr32 Void
#    +0x23c pImageHeaderHash : Ptr32 Void
#    +0x240 TracingFlags     : Uint4B
#    +0x240 HeapTracingEnabled : Pos 0, 1 Bit
#    +0x240 CritSecTracingEnabled : Pos 1, 1 Bit
#    +0x240 SpareTracingBits : Pos 2, 30 Bits
class _PEB_2008_R2(Structure):
    _pack_ = 8
    _fields_ = [
        ("InheritedAddressSpace", BOOLEAN),
        ("ReadImageFileExecOptions", UCHAR),
        ("BeingDebugged", BOOLEAN),
        ("BitField", UCHAR),
        ("Mutant", HANDLE),
        ("ImageBaseAddress", PVOID),
        ("Ldr", PVOID),  # PPEB_LDR_DATA
        ("ProcessParameters", PVOID),  # PRTL_USER_PROCESS_PARAMETERS
        ("SubSystemData", PVOID),
        ("ProcessHeap", PVOID),
        ("FastPebLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("AtlThunkSListPtr", PVOID),
        ("IFEOKey", PVOID),
        ("CrossProcessFlags", DWORD),
        ("KernelCallbackTable", PVOID),
        ("SystemReserved", DWORD),
        ("AtlThunkSListPtr32", PVOID),
        ("ApiSetMap", PVOID),
        ("TlsExpansionCounter", DWORD),
        ("TlsBitmap", PVOID),
        ("TlsBitmapBits", DWORD * 2),
        ("ReadOnlySharedMemoryBase", PVOID),
        ("HotpatchInformation", PVOID),
        ("ReadOnlyStaticServerData", PVOID),  # Ptr32 Ptr32 Void
        ("AnsiCodePageData", PVOID),
        ("OemCodePageData", PVOID),
        ("UnicodeCaseTableData", PVOID),
        ("NumberOfProcessors", DWORD),
        ("NtGlobalFlag", DWORD),
        ("CriticalSectionTimeout", LONGLONG),  # LARGE_INTEGER
        ("HeapSegmentReserve", DWORD),
        ("HeapSegmentCommit", DWORD),
        ("HeapDeCommitTotalFreeThreshold", DWORD),
        ("HeapDeCommitFreeBlockThreshold", DWORD),
        ("NumberOfHeaps", DWORD),
        ("MaximumNumberOfHeaps", DWORD),
        ("ProcessHeaps", PVOID),  # Ptr32 Ptr32 Void
        ("GdiSharedHandleTable", PVOID),
        ("ProcessStarterHelper", PVOID),
        ("GdiDCAttributeList", DWORD),
        ("LoaderLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("OSMajorVersion", DWORD),
        ("OSMinorVersion", DWORD),
        ("OSBuildNumber", WORD),
        ("OSCSDVersion", WORD),
        ("OSPlatformId", DWORD),
        ("ImageSubsystem", DWORD),
        ("ImageSubsystemMajorVersion", DWORD),
        ("ImageSubsystemMinorVersion", DWORD),
        ("ActiveProcessAffinityMask", DWORD),
        ("GdiHandleBuffer", DWORD * 34),
        ("PostProcessInitRoutine", PPS_POST_PROCESS_INIT_ROUTINE),
        ("TlsExpansionBitmap", PVOID),
        ("TlsExpansionBitmapBits", DWORD * 32),
        ("SessionId", DWORD),
        ("AppCompatFlags", ULONGLONG),  # ULARGE_INTEGER
        ("AppCompatFlagsUser", ULONGLONG),  # ULARGE_INTEGER
        ("pShimData", PVOID),
        ("AppCompatInfo", PVOID),
        ("CSDVersion", UNICODE_STRING),
        ("ActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("ProcessAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("SystemDefaultActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("SystemAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("MinimumStackCommit", DWORD),
        ("FlsCallback", PVOID),  # PFLS_CALLBACK_INFO
        ("FlsListHead", LIST_ENTRY),
        ("FlsBitmap", PVOID),
        ("FlsBitmapBits", DWORD * 4),
        ("FlsHighIndex", DWORD),
        ("WerRegistrationData", PVOID),
        ("WerShipAssertPtr", PVOID),
        ("pContextData", PVOID),
        ("pImageHeaderHash", PVOID),
        ("TracingFlags", DWORD),
    ]

    def __get_UserSharedInfoPtr(self):
        return self.KernelCallbackTable

    def __set_UserSharedInfoPtr(self, value):
        self.KernelCallbackTable = value

    UserSharedInfoPtr = property(__get_UserSharedInfoPtr, __set_UserSharedInfoPtr)


#    +0x000 InheritedAddressSpace : UChar
#    +0x001 ReadImageFileExecOptions : UChar
#    +0x002 BeingDebugged    : UChar
#    +0x003 BitField         : UChar
#    +0x003 ImageUsesLargePages : Pos 0, 1 Bit
#    +0x003 IsProtectedProcess : Pos 1, 1 Bit
#    +0x003 IsLegacyProcess  : Pos 2, 1 Bit
#    +0x003 IsImageDynamicallyRelocated : Pos 3, 1 Bit
#    +0x003 SkipPatchingUser32Forwarders : Pos 4, 1 Bit
#    +0x003 SpareBits        : Pos 5, 3 Bits
#    +0x008 Mutant           : Ptr64 Void
#    +0x010 ImageBaseAddress : Ptr64 Void
#    +0x018 Ldr              : Ptr64 _PEB_LDR_DATA
#    +0x020 ProcessParameters : Ptr64 _RTL_USER_PROCESS_PARAMETERS
#    +0x028 SubSystemData    : Ptr64 Void
#    +0x030 ProcessHeap      : Ptr64 Void
#    +0x038 FastPebLock      : Ptr64 _RTL_CRITICAL_SECTION
#    +0x040 AtlThunkSListPtr : Ptr64 Void
#    +0x048 IFEOKey          : Ptr64 Void
#    +0x050 CrossProcessFlags : Uint4B
#    +0x050 ProcessInJob     : Pos 0, 1 Bit
#    +0x050 ProcessInitializing : Pos 1, 1 Bit
#    +0x050 ProcessUsingVEH  : Pos 2, 1 Bit
#    +0x050 ProcessUsingVCH  : Pos 3, 1 Bit
#    +0x050 ProcessUsingFTH  : Pos 4, 1 Bit
#    +0x050 ReservedBits0    : Pos 5, 27 Bits
#    +0x058 KernelCallbackTable : Ptr64 Void
#    +0x058 UserSharedInfoPtr : Ptr64 Void
#    +0x060 SystemReserved   : [1] Uint4B
#    +0x064 AtlThunkSListPtr32 : Uint4B
#    +0x068 ApiSetMap        : Ptr64 Void
#    +0x070 TlsExpansionCounter : Uint4B
#    +0x078 TlsBitmap        : Ptr64 Void
#    +0x080 TlsBitmapBits    : [2] Uint4B
#    +0x088 ReadOnlySharedMemoryBase : Ptr64 Void
#    +0x090 HotpatchInformation : Ptr64 Void
#    +0x098 ReadOnlyStaticServerData : Ptr64 Ptr64 Void
#    +0x0a0 AnsiCodePageData : Ptr64 Void
#    +0x0a8 OemCodePageData  : Ptr64 Void
#    +0x0b0 UnicodeCaseTableData : Ptr64 Void
#    +0x0b8 NumberOfProcessors : Uint4B
#    +0x0bc NtGlobalFlag     : Uint4B
#    +0x0c0 CriticalSectionTimeout : _LARGE_INTEGER
#    +0x0c8 HeapSegmentReserve : Uint8B
#    +0x0d0 HeapSegmentCommit : Uint8B
#    +0x0d8 HeapDeCommitTotalFreeThreshold : Uint8B
#    +0x0e0 HeapDeCommitFreeBlockThreshold : Uint8B
#    +0x0e8 NumberOfHeaps    : Uint4B
#    +0x0ec MaximumNumberOfHeaps : Uint4B
#    +0x0f0 ProcessHeaps     : Ptr64 Ptr64 Void
#    +0x0f8 GdiSharedHandleTable : Ptr64 Void
#    +0x100 ProcessStarterHelper : Ptr64 Void
#    +0x108 GdiDCAttributeList : Uint4B
#    +0x110 LoaderLock       : Ptr64 _RTL_CRITICAL_SECTION
#    +0x118 OSMajorVersion   : Uint4B
#    +0x11c OSMinorVersion   : Uint4B
#    +0x120 OSBuildNumber    : Uint2B
#    +0x122 OSCSDVersion     : Uint2B
#    +0x124 OSPlatformId     : Uint4B
#    +0x128 ImageSubsystem   : Uint4B
#    +0x12c ImageSubsystemMajorVersion : Uint4B
#    +0x130 ImageSubsystemMinorVersion : Uint4B
#    +0x138 ActiveProcessAffinityMask : Uint8B
#    +0x140 GdiHandleBuffer  : [60] Uint4B
#    +0x230 PostProcessInitRoutine : Ptr64     void
#    +0x238 TlsExpansionBitmap : Ptr64 Void
#    +0x240 TlsExpansionBitmapBits : [32] Uint4B
#    +0x2c0 SessionId        : Uint4B
#    +0x2c8 AppCompatFlags   : _ULARGE_INTEGER
#    +0x2d0 AppCompatFlagsUser : _ULARGE_INTEGER
#    +0x2d8 pShimData        : Ptr64 Void
#    +0x2e0 AppCompatInfo    : Ptr64 Void
#    +0x2e8 CSDVersion       : _UNICODE_STRING
#    +0x2f8 ActivationContextData : Ptr64 _ACTIVATION_CONTEXT_DATA
#    +0x300 ProcessAssemblyStorageMap : Ptr64 _ASSEMBLY_STORAGE_MAP
#    +0x308 SystemDefaultActivationContextData : Ptr64 _ACTIVATION_CONTEXT_DATA
#    +0x310 SystemAssemblyStorageMap : Ptr64 _ASSEMBLY_STORAGE_MAP
#    +0x318 MinimumStackCommit : Uint8B
#    +0x320 FlsCallback      : Ptr64 _FLS_CALLBACK_INFO
#    +0x328 FlsListHead      : _LIST_ENTRY
#    +0x338 FlsBitmap        : Ptr64 Void
#    +0x340 FlsBitmapBits    : [4] Uint4B
#    +0x350 FlsHighIndex     : Uint4B
#    +0x358 WerRegistrationData : Ptr64 Void
#    +0x360 WerShipAssertPtr : Ptr64 Void
#    +0x368 pContextData     : Ptr64 Void
#    +0x370 pImageHeaderHash : Ptr64 Void
#    +0x378 TracingFlags     : Uint4B
#    +0x378 HeapTracingEnabled : Pos 0, 1 Bit
#    +0x378 CritSecTracingEnabled : Pos 1, 1 Bit
#    +0x378 SpareTracingBits : Pos 2, 30 Bits
class _PEB_2008_R2_64(Structure):
    _pack_ = 8
    _fields_ = [
        ("InheritedAddressSpace", BOOLEAN),
        ("ReadImageFileExecOptions", UCHAR),
        ("BeingDebugged", BOOLEAN),
        ("BitField", UCHAR),
        ("Mutant", HANDLE),
        ("ImageBaseAddress", PVOID),
        ("Ldr", PVOID),  # PPEB_LDR_DATA
        ("ProcessParameters", PVOID),  # PRTL_USER_PROCESS_PARAMETERS
        ("SubSystemData", PVOID),
        ("ProcessHeap", PVOID),
        ("FastPebLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("AtlThunkSListPtr", PVOID),
        ("IFEOKey", PVOID),
        ("CrossProcessFlags", DWORD),
        ("KernelCallbackTable", PVOID),
        ("SystemReserved", DWORD),
        ("AtlThunkSListPtr32", DWORD),
        ("ApiSetMap", PVOID),
        ("TlsExpansionCounter", DWORD),
        ("TlsBitmap", PVOID),
        ("TlsBitmapBits", DWORD * 2),
        ("ReadOnlySharedMemoryBase", PVOID),
        ("HotpatchInformation", PVOID),
        ("ReadOnlyStaticServerData", PVOID),  # Ptr32 Ptr32 Void
        ("AnsiCodePageData", PVOID),
        ("OemCodePageData", PVOID),
        ("UnicodeCaseTableData", PVOID),
        ("NumberOfProcessors", DWORD),
        ("NtGlobalFlag", DWORD),
        ("CriticalSectionTimeout", LONGLONG),  # LARGE_INTEGER
        ("HeapSegmentReserve", QWORD),
        ("HeapSegmentCommit", QWORD),
        ("HeapDeCommitTotalFreeThreshold", QWORD),
        ("HeapDeCommitFreeBlockThreshold", QWORD),
        ("NumberOfHeaps", DWORD),
        ("MaximumNumberOfHeaps", DWORD),
        ("ProcessHeaps", PVOID),  # Ptr64 Ptr64 Void
        ("GdiSharedHandleTable", PVOID),
        ("ProcessStarterHelper", PVOID),
        ("GdiDCAttributeList", DWORD),
        ("LoaderLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("OSMajorVersion", DWORD),
        ("OSMinorVersion", DWORD),
        ("OSBuildNumber", WORD),
        ("OSCSDVersion", WORD),
        ("OSPlatformId", DWORD),
        ("ImageSubsystem", DWORD),
        ("ImageSubsystemMajorVersion", DWORD),
        ("ImageSubsystemMinorVersion", DWORD),
        ("ActiveProcessAffinityMask", QWORD),
        ("GdiHandleBuffer", DWORD * 60),
        ("PostProcessInitRoutine", PPS_POST_PROCESS_INIT_ROUTINE),
        ("TlsExpansionBitmap", PVOID),
        ("TlsExpansionBitmapBits", DWORD * 32),
        ("SessionId", DWORD),
        ("AppCompatFlags", ULONGLONG),  # ULARGE_INTEGER
        ("AppCompatFlagsUser", ULONGLONG),  # ULARGE_INTEGER
        ("pShimData", PVOID),
        ("AppCompatInfo", PVOID),
        ("CSDVersion", UNICODE_STRING),
        ("ActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("ProcessAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("SystemDefaultActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("SystemAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("MinimumStackCommit", QWORD),
        ("FlsCallback", PVOID),  # PFLS_CALLBACK_INFO
        ("FlsListHead", LIST_ENTRY),
        ("FlsBitmap", PVOID),
        ("FlsBitmapBits", DWORD * 4),
        ("FlsHighIndex", DWORD),
        ("WerRegistrationData", PVOID),
        ("WerShipAssertPtr", PVOID),
        ("pContextData", PVOID),
        ("pImageHeaderHash", PVOID),
        ("TracingFlags", DWORD),
    ]

    def __get_UserSharedInfoPtr(self):
        return self.KernelCallbackTable

    def __set_UserSharedInfoPtr(self, value):
        self.KernelCallbackTable = value

    UserSharedInfoPtr = property(__get_UserSharedInfoPtr, __set_UserSharedInfoPtr)


_PEB_Vista = _PEB_2008
_PEB_Vista_64 = _PEB_2008_64
_PEB_W7 = _PEB_2008_R2
_PEB_W7_64 = _PEB_2008_R2_64


#    +0x000 InheritedAddressSpace : UChar
#    +0x001 ReadImageFileExecOptions : UChar
#    +0x002 BeingDebugged    : UChar
#    +0x003 BitField         : UChar
#    +0x003 ImageUsesLargePages : Pos 0, 1 Bit
#    +0x003 IsProtectedProcess : Pos 1, 1 Bit
#    +0x003 IsLegacyProcess  : Pos 2, 1 Bit
#    +0x003 IsImageDynamicallyRelocated : Pos 3, 1 Bit
#    +0x003 SkipPatchingUser32Forwarders : Pos 4, 1 Bit
#    +0x003 SpareBits        : Pos 5, 3 Bits
#    +0x004 Mutant           : Ptr32 Void
#    +0x008 ImageBaseAddress : Ptr32 Void
#    +0x00c Ldr              : Ptr32 _PEB_LDR_DATA
#    +0x010 ProcessParameters : Ptr32 _RTL_USER_PROCESS_PARAMETERS
#    +0x014 SubSystemData    : Ptr32 Void
#    +0x018 ProcessHeap      : Ptr32 Void
#    +0x01c FastPebLock      : Ptr32 _RTL_CRITICAL_SECTION
#    +0x020 AtlThunkSListPtr : Ptr32 Void
#    +0x024 IFEOKey          : Ptr32 Void
#    +0x028 CrossProcessFlags : Uint4B
#    +0x028 ProcessInJob     : Pos 0, 1 Bit
#    +0x028 ProcessInitializing : Pos 1, 1 Bit
#    +0x028 ProcessUsingVEH  : Pos 2, 1 Bit
#    +0x028 ProcessUsingVCH  : Pos 3, 1 Bit
#    +0x028 ProcessUsingFTH  : Pos 4, 1 Bit
#    +0x028 ReservedBits0    : Pos 5, 27 Bits
#    +0x02c KernelCallbackTable : Ptr32 Void
#    +0x02c UserSharedInfoPtr : Ptr32 Void
#    +0x030 SystemReserved   : [1] Uint4B
#    +0x034 TracingFlags     : Uint4B
#    +0x034 HeapTracingEnabled : Pos 0, 1 Bit
#    +0x034 CritSecTracingEnabled : Pos 1, 1 Bit
#    +0x034 SpareTracingBits : Pos 2, 30 Bits
#    +0x038 ApiSetMap        : Ptr32 Void
#    +0x03c TlsExpansionCounter : Uint4B
#    +0x040 TlsBitmap        : Ptr32 Void
#    +0x044 TlsBitmapBits    : [2] Uint4B
#    +0x04c ReadOnlySharedMemoryBase : Ptr32 Void
#    +0x050 HotpatchInformation : Ptr32 Void
#    +0x054 ReadOnlyStaticServerData : Ptr32 Ptr32 Void
#    +0x058 AnsiCodePageData : Ptr32 Void
#    +0x05c OemCodePageData  : Ptr32 Void
#    +0x060 UnicodeCaseTableData : Ptr32 Void
#    +0x064 NumberOfProcessors : Uint4B
#    +0x068 NtGlobalFlag     : Uint4B
#    +0x070 CriticalSectionTimeout : _LARGE_INTEGER
#    +0x078 HeapSegmentReserve : Uint4B
#    +0x07c HeapSegmentCommit : Uint4B
#    +0x080 HeapDeCommitTotalFreeThreshold : Uint4B
#    +0x084 HeapDeCommitFreeBlockThreshold : Uint4B
#    +0x088 NumberOfHeaps    : Uint4B
#    +0x08c MaximumNumberOfHeaps : Uint4B
#    +0x090 ProcessHeaps     : Ptr32 Ptr32 Void
#    +0x094 GdiSharedHandleTable : Ptr32 Void
#    +0x098 ProcessStarterHelper : Ptr32 Void
#    +0x09c GdiDCAttributeList : Uint4B
#    +0x0a0 LoaderLock       : Ptr32 _RTL_CRITICAL_SECTION
#    +0x0a4 OSMajorVersion   : Uint4B
#    +0x0a8 OSMinorVersion   : Uint4B
#    +0x0ac OSBuildNumber    : Uint2B
#    +0x0ae OSCSDVersion     : Uint2B
#    +0x0b0 OSPlatformId     : Uint4B
#    +0x0b4 ImageSubsystem   : Uint4B
#    +0x0b8 ImageSubsystemMajorVersion : Uint4B
#    +0x0bc ImageSubsystemMinorVersion : Uint4B
#    +0x0c0 ActiveProcessAffinityMask : Uint4B
#    +0x0c4 GdiHandleBuffer  : [34] Uint4B
#    +0x14c PostProcessInitRoutine : Ptr32     void
#    +0x150 TlsExpansionBitmap : Ptr32 Void
#    +0x154 TlsExpansionBitmapBits : [32] Uint4B
#    +0x1d4 SessionId        : Uint4B
#    +0x1d8 AppCompatFlags   : _ULARGE_INTEGER
#    +0x1e0 AppCompatFlagsUser : _ULARGE_INTEGER
#    +0x1e8 pShimData        : Ptr32 Void
#    +0x1ec AppCompatInfo    : Ptr32 Void
#    +0x1f0 CSDVersion       : _UNICODE_STRING
#    +0x1f8 ActivationContextData : Ptr32 _ACTIVATION_CONTEXT_DATA
#    +0x1fc ProcessAssemblyStorageMap : Ptr32 _ASSEMBLY_STORAGE_MAP
#    +0x200 SystemDefaultActivationContextData : Ptr32 _ACTIVATION_CONTEXT_DATA
#    +0x204 SystemAssemblyStorageMap : Ptr32 _ASSEMBLY_STORAGE_MAP
#    +0x208 MinimumStackCommit : Uint4B
#    +0x20c FlsCallback      : Ptr32 _FLS_CALLBACK_INFO
#    +0x210 FlsListHead      : _LIST_ENTRY
#    +0x218 FlsBitmap        : Ptr32 Void
#    +0x21c FlsBitmapBits    : [4] Uint4B
#    +0x22c FlsHighIndex     : Uint4B
#    +0x230 WerRegistrationData : Ptr32 Void
#    +0x234 WerShipAssertPtr : Ptr32 Void
#    +0x238 pContextData     : Ptr32 Void
#    +0x23c pImageHeaderHash : Ptr32 Void
class _PEB_W7_Beta(Structure):
    """
    This definition of the PEB structure is only valid for the beta versions
    of Windows 7. For the final version of Windows 7 use L{_PEB_W7} instead.
    This structure is not chosen automatically.
    """

    _pack_ = 8
    _fields_ = [
        ("InheritedAddressSpace", BOOLEAN),
        ("ReadImageFileExecOptions", UCHAR),
        ("BeingDebugged", BOOLEAN),
        ("BitField", UCHAR),
        ("Mutant", HANDLE),
        ("ImageBaseAddress", PVOID),
        ("Ldr", PVOID),  # PPEB_LDR_DATA
        ("ProcessParameters", PVOID),  # PRTL_USER_PROCESS_PARAMETERS
        ("SubSystemData", PVOID),
        ("ProcessHeap", PVOID),
        ("FastPebLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("AtlThunkSListPtr", PVOID),
        ("IFEOKey", PVOID),
        ("CrossProcessFlags", DWORD),
        ("KernelCallbackTable", PVOID),
        ("SystemReserved", DWORD),
        ("TracingFlags", DWORD),
        ("ApiSetMap", PVOID),
        ("TlsExpansionCounter", DWORD),
        ("TlsBitmap", PVOID),
        ("TlsBitmapBits", DWORD * 2),
        ("ReadOnlySharedMemoryBase", PVOID),
        ("HotpatchInformation", PVOID),
        ("ReadOnlyStaticServerData", PVOID),  # Ptr32 Ptr32 Void
        ("AnsiCodePageData", PVOID),
        ("OemCodePageData", PVOID),
        ("UnicodeCaseTableData", PVOID),
        ("NumberOfProcessors", DWORD),
        ("NtGlobalFlag", DWORD),
        ("CriticalSectionTimeout", LONGLONG),  # LARGE_INTEGER
        ("HeapSegmentReserve", DWORD),
        ("HeapSegmentCommit", DWORD),
        ("HeapDeCommitTotalFreeThreshold", DWORD),
        ("HeapDeCommitFreeBlockThreshold", DWORD),
        ("NumberOfHeaps", DWORD),
        ("MaximumNumberOfHeaps", DWORD),
        ("ProcessHeaps", PVOID),  # Ptr32 Ptr32 Void
        ("GdiSharedHandleTable", PVOID),
        ("ProcessStarterHelper", PVOID),
        ("GdiDCAttributeList", DWORD),
        ("LoaderLock", PVOID),  # PRTL_CRITICAL_SECTION
        ("OSMajorVersion", DWORD),
        ("OSMinorVersion", DWORD),
        ("OSBuildNumber", WORD),
        ("OSCSDVersion", WORD),
        ("OSPlatformId", DWORD),
        ("ImageSubsystem", DWORD),
        ("ImageSubsystemMajorVersion", DWORD),
        ("ImageSubsystemMinorVersion", DWORD),
        ("ActiveProcessAffinityMask", DWORD),
        ("GdiHandleBuffer", DWORD * 34),
        ("PostProcessInitRoutine", PPS_POST_PROCESS_INIT_ROUTINE),
        ("TlsExpansionBitmap", PVOID),
        ("TlsExpansionBitmapBits", DWORD * 32),
        ("SessionId", DWORD),
        ("AppCompatFlags", ULONGLONG),  # ULARGE_INTEGER
        ("AppCompatFlagsUser", ULONGLONG),  # ULARGE_INTEGER
        ("pShimData", PVOID),
        ("AppCompatInfo", PVOID),
        ("CSDVersion", UNICODE_STRING),
        ("ActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("ProcessAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("SystemDefaultActivationContextData", PVOID),  # ACTIVATION_CONTEXT_DATA
        ("SystemAssemblyStorageMap", PVOID),  # ASSEMBLY_STORAGE_MAP
        ("MinimumStackCommit", DWORD),
        ("FlsCallback", PVOID),  # PFLS_CALLBACK_INFO
        ("FlsListHead", LIST_ENTRY),
        ("FlsBitmap", PVOID),
        ("FlsBitmapBits", DWORD * 4),
        ("FlsHighIndex", DWORD),
        ("WerRegistrationData", PVOID),
        ("WerShipAssertPtr", PVOID),
        ("pContextData", PVOID),
        ("pImageHeaderHash", PVOID),
    ]

    def __get_UserSharedInfoPtr(self):
        return self.KernelCallbackTable

    def __set_UserSharedInfoPtr(self, value):
        self.KernelCallbackTable = value

    UserSharedInfoPtr = property(__get_UserSharedInfoPtr, __set_UserSharedInfoPtr)


# Use the correct PEB structure definition.
# Defaults to the latest Windows version.
class PEB(Structure):
    _pack_ = 8
    if os == "Windows NT":
        _pack_ = _PEB_NT._pack_
        _fields_ = _PEB_NT._fields_
    elif os == "Windows 2000":
        _pack_ = _PEB_2000._pack_
        _fields_ = _PEB_2000._fields_
    elif os == "Windows XP":
        _fields_ = _PEB_XP._fields_
    elif os == "Windows XP (64 bits)":
        _fields_ = _PEB_XP_64._fields_
    elif os == "Windows 2003":
        _fields_ = _PEB_2003._fields_
    elif os == "Windows 2003 (64 bits)":
        _fields_ = _PEB_2003_64._fields_
    elif os == "Windows 2003 R2":
        _fields_ = _PEB_2003_R2._fields_
    elif os == "Windows 2003 R2 (64 bits)":
        _fields_ = _PEB_2003_R2_64._fields_
    elif os == "Windows 2008":
        _fields_ = _PEB_2008._fields_
    elif os == "Windows 2008 (64 bits)":
        _fields_ = _PEB_2008_64._fields_
    elif os == "Windows 2008 R2":
        _fields_ = _PEB_2008_R2._fields_
    elif os == "Windows 2008 R2 (64 bits)":
        _fields_ = _PEB_2008_R2_64._fields_
    elif os == "Windows Vista":
        _fields_ = _PEB_Vista._fields_
    elif os == "Windows Vista (64 bits)":
        _fields_ = _PEB_Vista_64._fields_
    elif os == "Windows 7":
        _fields_ = _PEB_W7._fields_
    elif os == "Windows 7 (64 bits)":
        _fields_ = _PEB_W7_64._fields_
    elif sizeof(SIZE_T) == sizeof(DWORD):
        _fields_ = _PEB_W7._fields_
    else:
        _fields_ = _PEB_W7_64._fields_


PPEB = POINTER(PEB)


# PEB structure for WOW64 processes.
class PEB_32(Structure):
    _pack_ = 8
    if os == "Windows NT":
        _pack_ = _PEB_NT._pack_
        _fields_ = _PEB_NT._fields_
    elif os == "Windows 2000":
        _pack_ = _PEB_2000._pack_
        _fields_ = _PEB_2000._fields_
    elif os.startswith("Windows XP"):
        _fields_ = _PEB_XP._fields_
    elif os.startswith("Windows 2003 R2"):
        _fields_ = _PEB_2003_R2._fields_
    elif os.startswith("Windows 2003"):
        _fields_ = _PEB_2003._fields_
    elif os.startswith("Windows 2008 R2"):
        _fields_ = _PEB_2008_R2._fields_
    elif os.startswith("Windows 2008"):
        _fields_ = _PEB_2008._fields_
    elif os.startswith("Windows Vista"):
        _fields_ = _PEB_Vista._fields_
    else:  # if os.startswith('Windows 7'):
        _fields_ = _PEB_W7._fields_


# from https://vmexplorer.svn.codeplex.com/svn/VMExplorer/src/Win32/Threads.cs
#
# [StructLayout (LayoutKind.Sequential, Size = 0x0C)]
# public struct Wx86ThreadState
# {
# 	public IntPtr  CallBx86Eip; // Ptr32 to Uint4B
# 	public IntPtr  DeallocationCpu; // Ptr32 to Void
# 	public Byte  UseKnownWx86Dll; // UChar
# 	public Byte  OleStubInvoked; // Char
# };
class Wx86ThreadState(Structure):
    _fields_ = [
        ("CallBx86Eip", PVOID),
        ("DeallocationCpu", PVOID),
        ("UseKnownWx86Dll", UCHAR),
        ("OleStubInvoked", CHAR),
    ]


# ntdll!_RTL_ACTIVATION_CONTEXT_STACK_FRAME
#    +0x000 Previous         : Ptr64 _RTL_ACTIVATION_CONTEXT_STACK_FRAME
#    +0x008 ActivationContext : Ptr64 _ACTIVATION_CONTEXT
#    +0x010 Flags            : Uint4B
class RTL_ACTIVATION_CONTEXT_STACK_FRAME(Structure):
    _fields_ = [
        ("Previous", PVOID),
        ("ActivationContext", PVOID),
        ("Flags", DWORD),
    ]


# ntdll!_ACTIVATION_CONTEXT_STACK
#    +0x000 ActiveFrame      : Ptr64 _RTL_ACTIVATION_CONTEXT_STACK_FRAME
#    +0x008 FrameListCache   : _LIST_ENTRY
#    +0x018 Flags            : Uint4B
#    +0x01c NextCookieSequenceNumber : Uint4B
#    +0x020 StackId          : Uint4B
class ACTIVATION_CONTEXT_STACK(Structure):
    _fields_ = [
        ("ActiveFrame", PVOID),
        ("FrameListCache", LIST_ENTRY),
        ("Flags", DWORD),
        ("NextCookieSequenceNumber", DWORD),
        ("StackId", DWORD),
    ]


# typedef struct _PROCESSOR_NUMBER {
#   WORD Group;
#   BYTE Number;
#   BYTE Reserved;
# }PROCESSOR_NUMBER, *PPROCESSOR_NUMBER;
class PROCESSOR_NUMBER(Structure):
    _fields_ = [
        ("Group", WORD),
        ("Number", BYTE),
        ("Reserved", BYTE),
    ]


# from http://www.nirsoft.net/kernel_struct/vista/NT_TIB.html
#
# typedef struct _NT_TIB
# {
#      PEXCEPTION_REGISTRATION_RECORD ExceptionList;
#      PVOID StackBase;
#      PVOID StackLimit;
#      PVOID SubSystemTib;
#      union
#      {
#           PVOID FiberData;
#           ULONG Version;
#      };
#      PVOID ArbitraryUserPointer;
#      PNT_TIB Self;
# } NT_TIB, *PNT_TIB;
class _NT_TIB_UNION(Union):
    _fields_ = [
        ("FiberData", PVOID),
        ("Version", ULONG),
    ]


class NT_TIB(Structure):
    _fields_ = [
        ("ExceptionList", PVOID),  # PEXCEPTION_REGISTRATION_RECORD
        ("StackBase", PVOID),
        ("StackLimit", PVOID),
        ("SubSystemTib", PVOID),
        ("u", _NT_TIB_UNION),
        ("ArbitraryUserPointer", PVOID),
        ("Self", PVOID),  # PNTTIB
    ]

    def __get_FiberData(self):
        return self.u.FiberData

    def __set_FiberData(self, value):
        self.u.FiberData = value

    FiberData = property(__get_FiberData, __set_FiberData)

    def __get_Version(self):
        return self.u.Version

    def __set_Version(self, value):
        self.u.Version = value

    Version = property(__get_Version, __set_Version)


PNTTIB = POINTER(NT_TIB)


# From http://www.nirsoft.net/kernel_struct/vista/EXCEPTION_REGISTRATION_RECORD.html
#
# typedef struct _EXCEPTION_REGISTRATION_RECORD
# {
#      PEXCEPTION_REGISTRATION_RECORD Next;
#      PEXCEPTION_DISPOSITION Handler;
# } EXCEPTION_REGISTRATION_RECORD, *PEXCEPTION_REGISTRATION_RECORD;
class EXCEPTION_REGISTRATION_RECORD(Structure):
    pass


EXCEPTION_DISPOSITION = DWORD
##PEXCEPTION_DISPOSITION          = POINTER(EXCEPTION_DISPOSITION)
##PEXCEPTION_REGISTRATION_RECORD  = POINTER(EXCEPTION_REGISTRATION_RECORD)
PEXCEPTION_DISPOSITION = PVOID
PEXCEPTION_REGISTRATION_RECORD = PVOID

EXCEPTION_REGISTRATION_RECORD._fields_ = [
    ("Next", PEXCEPTION_REGISTRATION_RECORD),
    ("Handler", PEXCEPTION_DISPOSITION),
]

##PPEB = POINTER(PEB)
PPEB = PVOID


# From http://www.nirsoft.net/kernel_struct/vista/GDI_TEB_BATCH.html
#
# typedef struct _GDI_TEB_BATCH
# {
#      ULONG Offset;
#      ULONG HDC;
#      ULONG Buffer[310];
# } GDI_TEB_BATCH, *PGDI_TEB_BATCH;
class GDI_TEB_BATCH(Structure):
    _fields_ = [
        ("Offset", ULONG),
        ("HDC", ULONG),
        ("Buffer", ULONG * 310),
    ]


# ntdll!_TEB_ACTIVE_FRAME_CONTEXT
#    +0x000 Flags            : Uint4B
#    +0x008 FrameName        : Ptr64 Char
class TEB_ACTIVE_FRAME_CONTEXT(Structure):
    _fields_ = [
        ("Flags", DWORD),
        ("FrameName", LPVOID),  # LPCHAR
    ]


PTEB_ACTIVE_FRAME_CONTEXT = POINTER(TEB_ACTIVE_FRAME_CONTEXT)


# ntdll!_TEB_ACTIVE_FRAME
#    +0x000 Flags            : Uint4B
#    +0x008 Previous         : Ptr64 _TEB_ACTIVE_FRAME
#    +0x010 Context          : Ptr64 _TEB_ACTIVE_FRAME_CONTEXT
class TEB_ACTIVE_FRAME(Structure):
    _fields_ = [
        ("Flags", DWORD),
        ("Previous", LPVOID),  # PTEB_ACTIVE_FRAME
        ("Context", LPVOID),  # PTEB_ACTIVE_FRAME_CONTEXT
    ]


PTEB_ACTIVE_FRAME = POINTER(TEB_ACTIVE_FRAME)

# SameTebFlags
DbgSafeThunkCall = 1 << 0
DbgInDebugPrint = 1 << 1
DbgHasFiberData = 1 << 2
DbgSkipThreadAttach = 1 << 3
DbgWerInShipAssertCode = 1 << 4
DbgRanProcessInit = 1 << 5
DbgClonedThread = 1 << 6
DbgSuppressDebugMsg = 1 << 7
RtlDisableUserStackWalk = 1 << 8
RtlExceptionAttached = 1 << 9
RtlInitialThread = 1 << 10


# XXX This is quite wrong :P
class _TEB_NT(Structure):
    _pack_ = 4
    _fields_ = [
        ("NtTib", NT_TIB),
        ("EnvironmentPointer", PVOID),
        ("ClientId", CLIENT_ID),
        ("ActiveRpcHandle", HANDLE),
        ("ThreadLocalStoragePointer", PVOID),
        ("ProcessEnvironmentBlock", PPEB),
        ("LastErrorValue", ULONG),
        ("CountOfOwnedCriticalSections", ULONG),
        ("CsrClientThread", PVOID),
        ("Win32ThreadInfo", PVOID),
        ("User32Reserved", ULONG * 26),
        ("UserReserved", ULONG * 5),
        ("WOW32Reserved", PVOID),  # ptr to wow64cpu!X86SwitchTo64BitMode
        ("CurrentLocale", ULONG),
        ("FpSoftwareStatusRegister", ULONG),
        ("SystemReserved1", PVOID * 54),
        ("Spare1", PVOID),
        ("ExceptionCode", ULONG),
        ("ActivationContextStackPointer", PVOID),  # PACTIVATION_CONTEXT_STACK
        ("SpareBytes1", ULONG * 36),
        ("TxFsContext", ULONG),
        ("GdiTebBatch", GDI_TEB_BATCH),
        ("RealClientId", CLIENT_ID),
        ("GdiCachedProcessHandle", PVOID),
        ("GdiClientPID", ULONG),
        ("GdiClientTID", ULONG),
        ("GdiThreadLocalInfo", PVOID),
        ("Win32ClientInfo", PVOID * 62),
        ("glDispatchTable", PVOID * 233),
        ("glReserved1", ULONG * 29),
        ("glReserved2", PVOID),
        ("glSectionInfo", PVOID),
        ("glSection", PVOID),
        ("glTable", PVOID),
        ("glCurrentRC", PVOID),
        ("glContext", PVOID),
        ("LastStatusValue", NTSTATUS),
        ("StaticUnicodeString", UNICODE_STRING),
        ("StaticUnicodeBuffer", WCHAR * 261),
        ("DeallocationStack", PVOID),
        ("TlsSlots", PVOID * 64),
        ("TlsLinks", LIST_ENTRY),
        ("Vdm", PVOID),
        ("ReservedForNtRpc", PVOID),
        ("DbgSsReserved", PVOID * 2),
        ("HardErrorDisabled", ULONG),
        ("Instrumentation", PVOID * 9),
        ("ActivityId", GUID),
        ("SubProcessTag", PVOID),
        ("EtwLocalData", PVOID),
        ("EtwTraceData", PVOID),
        ("WinSockData", PVOID),
        ("GdiBatchCount", ULONG),
        ("SpareBool0", BOOLEAN),
        ("SpareBool1", BOOLEAN),
        ("SpareBool2", BOOLEAN),
        ("IdealProcessor", UCHAR),
        ("GuaranteedStackBytes", ULONG),
        ("ReservedForPerf", PVOID),
        ("ReservedForOle", PVOID),
        ("WaitingOnLoaderLock", ULONG),
        ("StackCommit", PVOID),
        ("StackCommitMax", PVOID),
        ("StackReserved", PVOID),
    ]


# not really, but "dt _TEB" in w2k isn't working for me :(
_TEB_2000 = _TEB_NT


#    +0x000 NtTib            : _NT_TIB
#    +0x01c EnvironmentPointer : Ptr32 Void
#    +0x020 ClientId         : _CLIENT_ID
#    +0x028 ActiveRpcHandle  : Ptr32 Void
#    +0x02c ThreadLocalStoragePointer : Ptr32 Void
#    +0x030 ProcessEnvironmentBlock : Ptr32 _PEB
#    +0x034 LastErrorValue   : Uint4B
#    +0x038 CountOfOwnedCriticalSections : Uint4B
#    +0x03c CsrClientThread  : Ptr32 Void
#    +0x040 Win32ThreadInfo  : Ptr32 Void
#    +0x044 User32Reserved   : [26] Uint4B
#    +0x0ac UserReserved     : [5] Uint4B
#    +0x0c0 WOW32Reserved    : Ptr32 Void
#    +0x0c4 CurrentLocale    : Uint4B
#    +0x0c8 FpSoftwareStatusRegister : Uint4B
#    +0x0cc SystemReserved1  : [54] Ptr32 Void
#    +0x1a4 ExceptionCode    : Int4B
#    +0x1a8 ActivationContextStack : _ACTIVATION_CONTEXT_STACK
#    +0x1bc SpareBytes1      : [24] UChar
#    +0x1d4 GdiTebBatch      : _GDI_TEB_BATCH
#    +0x6b4 RealClientId     : _CLIENT_ID
#    +0x6bc GdiCachedProcessHandle : Ptr32 Void
#    +0x6c0 GdiClientPID     : Uint4B
#    +0x6c4 GdiClientTID     : Uint4B
#    +0x6c8 GdiThreadLocalInfo : Ptr32 Void
#    +0x6cc Win32ClientInfo  : [62] Uint4B
#    +0x7c4 glDispatchTable  : [233] Ptr32 Void
#    +0xb68 glReserved1      : [29] Uint4B
#    +0xbdc glReserved2      : Ptr32 Void
#    +0xbe0 glSectionInfo    : Ptr32 Void
#    +0xbe4 glSection        : Ptr32 Void
#    +0xbe8 glTable          : Ptr32 Void
#    +0xbec glCurrentRC      : Ptr32 Void
#    +0xbf0 glContext        : Ptr32 Void
#    +0xbf4 LastStatusValue  : Uint4B
#    +0xbf8 StaticUnicodeString : _UNICODE_STRING
#    +0xc00 StaticUnicodeBuffer : [261] Uint2B
#    +0xe0c DeallocationStack : Ptr32 Void
#    +0xe10 TlsSlots         : [64] Ptr32 Void
#    +0xf10 TlsLinks         : _LIST_ENTRY
#    +0xf18 Vdm              : Ptr32 Void
#    +0xf1c ReservedForNtRpc : Ptr32 Void
#    +0xf20 DbgSsReserved    : [2] Ptr32 Void
#    +0xf28 HardErrorsAreDisabled : Uint4B
#    +0xf2c Instrumentation  : [16] Ptr32 Void
#    +0xf6c WinSockData      : Ptr32 Void
#    +0xf70 GdiBatchCount    : Uint4B
#    +0xf74 InDbgPrint       : UChar
#    +0xf75 FreeStackOnTermination : UChar
#    +0xf76 HasFiberData     : UChar
#    +0xf77 IdealProcessor   : UChar
#    +0xf78 Spare3           : Uint4B
#    +0xf7c ReservedForPerf  : Ptr32 Void
#    +0xf80 ReservedForOle   : Ptr32 Void
#    +0xf84 WaitingOnLoaderLock : Uint4B
#    +0xf88 Wx86Thread       : _Wx86ThreadState
#    +0xf94 TlsExpansionSlots : Ptr32 Ptr32 Void
#    +0xf98 ImpersonationLocale : Uint4B
#    +0xf9c IsImpersonating  : Uint4B
#    +0xfa0 NlsCache         : Ptr32 Void
#    +0xfa4 pShimData        : Ptr32 Void
#    +0xfa8 HeapVirtualAffinity : Uint4B
#    +0xfac CurrentTransactionHandle : Ptr32 Void
#    +0xfb0 ActiveFrame      : Ptr32 _TEB_ACTIVE_FRAME
#    +0xfb4 SafeThunkCall    : UChar
#    +0xfb5 BooleanSpare     : [3] UChar
class _TEB_XP(Structure):
    _pack_ = 8
    _fields_ = [
        ("NtTib", NT_TIB),
        ("EnvironmentPointer", PVOID),
        ("ClientId", CLIENT_ID),
        ("ActiveRpcHandle", HANDLE),
        ("ThreadLocalStoragePointer", PVOID),
        ("ProcessEnvironmentBlock", PVOID),  # PPEB
        ("LastErrorValue", DWORD),
        ("CountOfOwnedCriticalSections", DWORD),
        ("CsrClientThread", PVOID),
        ("Win32ThreadInfo", PVOID),
        ("User32Reserved", DWORD * 26),
        ("UserReserved", DWORD * 5),
        ("WOW32Reserved", PVOID),  # ptr to wow64cpu!X86SwitchTo64BitMode
        ("CurrentLocale", DWORD),
        ("FpSoftwareStatusRegister", DWORD),
        ("SystemReserved1", PVOID * 54),
        ("ExceptionCode", SDWORD),
        ("ActivationContextStackPointer", PVOID),  # PACTIVATION_CONTEXT_STACK
        ("SpareBytes1", UCHAR * 24),
        ("TxFsContext", DWORD),
        ("GdiTebBatch", GDI_TEB_BATCH),
        ("RealClientId", CLIENT_ID),
        ("GdiCachedProcessHandle", HANDLE),
        ("GdiClientPID", DWORD),
        ("GdiClientTID", DWORD),
        ("GdiThreadLocalInfo", PVOID),
        ("Win32ClientInfo", DWORD * 62),
        ("glDispatchTable", PVOID * 233),
        ("glReserved1", DWORD * 29),
        ("glReserved2", PVOID),
        ("glSectionInfo", PVOID),
        ("glSection", PVOID),
        ("glTable", PVOID),
        ("glCurrentRC", PVOID),
        ("glContext", PVOID),
        ("LastStatusValue", NTSTATUS),
        ("StaticUnicodeString", UNICODE_STRING),
        ("StaticUnicodeBuffer", WCHAR * 261),
        ("DeallocationStack", PVOID),
        ("TlsSlots", PVOID * 64),
        ("TlsLinks", LIST_ENTRY),
        ("Vdm", PVOID),
        ("ReservedForNtRpc", PVOID),
        ("DbgSsReserved", PVOID * 2),
        ("HardErrorsAreDisabled", DWORD),
        ("Instrumentation", PVOID * 16),
        ("WinSockData", PVOID),
        ("GdiBatchCount", DWORD),
        ("InDbgPrint", BOOLEAN),
        ("FreeStackOnTermination", BOOLEAN),
        ("HasFiberData", BOOLEAN),
        ("IdealProcessor", UCHAR),
        ("Spare3", DWORD),
        ("ReservedForPerf", PVOID),
        ("ReservedForOle", PVOID),
        ("WaitingOnLoaderLock", DWORD),
        ("Wx86Thread", Wx86ThreadState),
        ("TlsExpansionSlots", PVOID),  # Ptr32 Ptr32 Void
        ("ImpersonationLocale", DWORD),
        ("IsImpersonating", BOOL),
        ("NlsCache", PVOID),
        ("pShimData", PVOID),
        ("HeapVirtualAffinity", DWORD),
        ("CurrentTransactionHandle", HANDLE),
        ("ActiveFrame", PVOID),  # PTEB_ACTIVE_FRAME
        ("SafeThunkCall", BOOLEAN),
        ("BooleanSpare", BOOLEAN * 3),
    ]


#    +0x000 NtTib            : _NT_TIB
#    +0x038 EnvironmentPointer : Ptr64 Void
#    +0x040 ClientId         : _CLIENT_ID
#    +0x050 ActiveRpcHandle  : Ptr64 Void
#    +0x058 ThreadLocalStoragePointer : Ptr64 Void
#    +0x060 ProcessEnvironmentBlock : Ptr64 _PEB
#    +0x068 LastErrorValue   : Uint4B
#    +0x06c CountOfOwnedCriticalSections : Uint4B
#    +0x070 CsrClientThread  : Ptr64 Void
#    +0x078 Win32ThreadInfo  : Ptr64 Void
#    +0x080 User32Reserved   : [26] Uint4B
#    +0x0e8 UserReserved     : [5] Uint4B
#    +0x100 WOW32Reserved    : Ptr64 Void
#    +0x108 CurrentLocale    : Uint4B
#    +0x10c FpSoftwareStatusRegister : Uint4B
#    +0x110 SystemReserved1  : [54] Ptr64 Void
#    +0x2c0 ExceptionCode    : Int4B
#    +0x2c8 ActivationContextStackPointer : Ptr64 _ACTIVATION_CONTEXT_STACK
#    +0x2d0 SpareBytes1      : [28] UChar
#    +0x2f0 GdiTebBatch      : _GDI_TEB_BATCH
#    +0x7d8 RealClientId     : _CLIENT_ID
#    +0x7e8 GdiCachedProcessHandle : Ptr64 Void
#    +0x7f0 GdiClientPID     : Uint4B
#    +0x7f4 GdiClientTID     : Uint4B
#    +0x7f8 GdiThreadLocalInfo : Ptr64 Void
#    +0x800 Win32ClientInfo  : [62] Uint8B
#    +0x9f0 glDispatchTable  : [233] Ptr64 Void
#    +0x1138 glReserved1      : [29] Uint8B
#    +0x1220 glReserved2      : Ptr64 Void
#    +0x1228 glSectionInfo    : Ptr64 Void
#    +0x1230 glSection        : Ptr64 Void
#    +0x1238 glTable          : Ptr64 Void
#    +0x1240 glCurrentRC      : Ptr64 Void
#    +0x1248 glContext        : Ptr64 Void
#    +0x1250 LastStatusValue  : Uint4B
#    +0x1258 StaticUnicodeString : _UNICODE_STRING
#    +0x1268 StaticUnicodeBuffer : [261] Uint2B
#    +0x1478 DeallocationStack : Ptr64 Void
#    +0x1480 TlsSlots         : [64] Ptr64 Void
#    +0x1680 TlsLinks         : _LIST_ENTRY
#    +0x1690 Vdm              : Ptr64 Void
#    +0x1698 ReservedForNtRpc : Ptr64 Void
#    +0x16a0 DbgSsReserved    : [2] Ptr64 Void
#    +0x16b0 HardErrorMode    : Uint4B
#    +0x16b8 Instrumentation  : [14] Ptr64 Void
#    +0x1728 SubProcessTag    : Ptr64 Void
#    +0x1730 EtwTraceData     : Ptr64 Void
#    +0x1738 WinSockData      : Ptr64 Void
#    +0x1740 GdiBatchCount    : Uint4B
#    +0x1744 InDbgPrint       : UChar
#    +0x1745 FreeStackOnTermination : UChar
#    +0x1746 HasFiberData     : UChar
#    +0x1747 IdealProcessor   : UChar
#    +0x1748 GuaranteedStackBytes : Uint4B
#    +0x1750 ReservedForPerf  : Ptr64 Void
#    +0x1758 ReservedForOle   : Ptr64 Void
#    +0x1760 WaitingOnLoaderLock : Uint4B
#    +0x1768 SparePointer1    : Uint8B
#    +0x1770 SoftPatchPtr1    : Uint8B
#    +0x1778 SoftPatchPtr2    : Uint8B
#    +0x1780 TlsExpansionSlots : Ptr64 Ptr64 Void
#    +0x1788 DeallocationBStore : Ptr64 Void
#    +0x1790 BStoreLimit      : Ptr64 Void
#    +0x1798 ImpersonationLocale : Uint4B
#    +0x179c IsImpersonating  : Uint4B
#    +0x17a0 NlsCache         : Ptr64 Void
#    +0x17a8 pShimData        : Ptr64 Void
#    +0x17b0 HeapVirtualAffinity : Uint4B
#    +0x17b8 CurrentTransactionHandle : Ptr64 Void
#    +0x17c0 ActiveFrame      : Ptr64 _TEB_ACTIVE_FRAME
#    +0x17c8 FlsData          : Ptr64 Void
#    +0x17d0 SafeThunkCall    : UChar
#    +0x17d1 BooleanSpare     : [3] UChar
class _TEB_XP_64(Structure):
    _pack_ = 8
    _fields_ = [
        ("NtTib", NT_TIB),
        ("EnvironmentPointer", PVOID),
        ("ClientId", CLIENT_ID),
        ("ActiveRpcHandle", PVOID),
        ("ThreadLocalStoragePointer", PVOID),
        ("ProcessEnvironmentBlock", PVOID),  # PPEB
        ("LastErrorValue", DWORD),
        ("CountOfOwnedCriticalSections", DWORD),
        ("CsrClientThread", PVOID),
        ("Win32ThreadInfo", PVOID),
        ("User32Reserved", DWORD * 26),
        ("UserReserved", DWORD * 5),
        ("WOW32Reserved", PVOID),  # ptr to wow64cpu!X86SwitchTo64BitMode
        ("CurrentLocale", DWORD),
        ("FpSoftwareStatusRegister", DWORD),
        ("SystemReserved1", PVOID * 54),
        ("ExceptionCode", SDWORD),
        ("ActivationContextStackPointer", PVOID),  # PACTIVATION_CONTEXT_STACK
        ("SpareBytes1", UCHAR * 28),
        ("GdiTebBatch", GDI_TEB_BATCH),
        ("RealClientId", CLIENT_ID),
        ("GdiCachedProcessHandle", HANDLE),
        ("GdiClientPID", DWORD),
        ("GdiClientTID", DWORD),
        ("GdiThreadLocalInfo", PVOID),
        ("Win32ClientInfo", QWORD * 62),
        ("glDispatchTable", PVOID * 233),
        ("glReserved1", QWORD * 29),
        ("glReserved2", PVOID),
        ("glSectionInfo", PVOID),
        ("glSection", PVOID),
        ("glTable", PVOID),
        ("glCurrentRC", PVOID),
        ("glContext", PVOID),
        ("LastStatusValue", NTSTATUS),
        ("StaticUnicodeString", UNICODE_STRING),
        ("StaticUnicodeBuffer", WCHAR * 261),
        ("DeallocationStack", PVOID),
        ("TlsSlots", PVOID * 64),
        ("TlsLinks", LIST_ENTRY),
        ("Vdm", PVOID),
        ("ReservedForNtRpc", PVOID),
        ("DbgSsReserved", PVOID * 2),
        ("HardErrorMode", DWORD),
        ("Instrumentation", PVOID * 14),
        ("SubProcessTag", PVOID),
        ("EtwTraceData", PVOID),
        ("WinSockData", PVOID),
        ("GdiBatchCount", DWORD),
        ("InDbgPrint", BOOLEAN),
        ("FreeStackOnTermination", BOOLEAN),
        ("HasFiberData", BOOLEAN),
        ("IdealProcessor", UCHAR),
        ("GuaranteedStackBytes", DWORD),
        ("ReservedForPerf", PVOID),
        ("ReservedForOle", PVOID),
        ("WaitingOnLoaderLock", DWORD),
        ("SparePointer1", PVOID),
        ("SoftPatchPtr1", PVOID),
        ("SoftPatchPtr2", PVOID),
        ("TlsExpansionSlots", PVOID),  # Ptr64 Ptr64 Void
        ("DeallocationBStore", PVOID),
        ("BStoreLimit", PVOID),
        ("ImpersonationLocale", DWORD),
        ("IsImpersonating", BOOL),
        ("NlsCache", PVOID),
        ("pShimData", PVOID),
        ("HeapVirtualAffinity", DWORD),
        ("CurrentTransactionHandle", HANDLE),
        ("ActiveFrame", PVOID),  # PTEB_ACTIVE_FRAME
        ("FlsData", PVOID),
        ("SafeThunkCall", BOOLEAN),
        ("BooleanSpare", BOOLEAN * 3),
    ]


#    +0x000 NtTib            : _NT_TIB
#    +0x01c EnvironmentPointer : Ptr32 Void
#    +0x020 ClientId         : _CLIENT_ID
#    +0x028 ActiveRpcHandle  : Ptr32 Void
#    +0x02c ThreadLocalStoragePointer : Ptr32 Void
#    +0x030 ProcessEnvironmentBlock : Ptr32 _PEB
#    +0x034 LastErrorValue   : Uint4B
#    +0x038 CountOfOwnedCriticalSections : Uint4B
#    +0x03c CsrClientThread  : Ptr32 Void
#    +0x040 Win32ThreadInfo  : Ptr32 Void
#    +0x044 User32Reserved   : [26] Uint4B
#    +0x0ac UserReserved     : [5] Uint4B
#    +0x0c0 WOW32Reserved    : Ptr32 Void
#    +0x0c4 CurrentLocale    : Uint4B
#    +0x0c8 FpSoftwareStatusRegister : Uint4B
#    +0x0cc SystemReserved1  : [54] Ptr32 Void
#    +0x1a4 ExceptionCode    : Int4B
#    +0x1a8 ActivationContextStackPointer : Ptr32 _ACTIVATION_CONTEXT_STACK
#    +0x1ac SpareBytes1      : [40] UChar
#    +0x1d4 GdiTebBatch      : _GDI_TEB_BATCH
#    +0x6b4 RealClientId     : _CLIENT_ID
#    +0x6bc GdiCachedProcessHandle : Ptr32 Void
#    +0x6c0 GdiClientPID     : Uint4B
#    +0x6c4 GdiClientTID     : Uint4B
#    +0x6c8 GdiThreadLocalInfo : Ptr32 Void
#    +0x6cc Win32ClientInfo  : [62] Uint4B
#    +0x7c4 glDispatchTable  : [233] Ptr32 Void
#    +0xb68 glReserved1      : [29] Uint4B
#    +0xbdc glReserved2      : Ptr32 Void
#    +0xbe0 glSectionInfo    : Ptr32 Void
#    +0xbe4 glSection        : Ptr32 Void
#    +0xbe8 glTable          : Ptr32 Void
#    +0xbec glCurrentRC      : Ptr32 Void
#    +0xbf0 glContext        : Ptr32 Void
#    +0xbf4 LastStatusValue  : Uint4B
#    +0xbf8 StaticUnicodeString : _UNICODE_STRING
#    +0xc00 StaticUnicodeBuffer : [261] Uint2B
#    +0xe0c DeallocationStack : Ptr32 Void
#    +0xe10 TlsSlots         : [64] Ptr32 Void
#    +0xf10 TlsLinks         : _LIST_ENTRY
#    +0xf18 Vdm              : Ptr32 Void
#    +0xf1c ReservedForNtRpc : Ptr32 Void
#    +0xf20 DbgSsReserved    : [2] Ptr32 Void
#    +0xf28 HardErrorMode    : Uint4B
#    +0xf2c Instrumentation  : [14] Ptr32 Void
#    +0xf64 SubProcessTag    : Ptr32 Void
#    +0xf68 EtwTraceData     : Ptr32 Void
#    +0xf6c WinSockData      : Ptr32 Void
#    +0xf70 GdiBatchCount    : Uint4B
#    +0xf74 InDbgPrint       : UChar
#    +0xf75 FreeStackOnTermination : UChar
#    +0xf76 HasFiberData     : UChar
#    +0xf77 IdealProcessor   : UChar
#    +0xf78 GuaranteedStackBytes : Uint4B
#    +0xf7c ReservedForPerf  : Ptr32 Void
#    +0xf80 ReservedForOle   : Ptr32 Void
#    +0xf84 WaitingOnLoaderLock : Uint4B
#    +0xf88 SparePointer1    : Uint4B
#    +0xf8c SoftPatchPtr1    : Uint4B
#    +0xf90 SoftPatchPtr2    : Uint4B
#    +0xf94 TlsExpansionSlots : Ptr32 Ptr32 Void
#    +0xf98 ImpersonationLocale : Uint4B
#    +0xf9c IsImpersonating  : Uint4B
#    +0xfa0 NlsCache         : Ptr32 Void
#    +0xfa4 pShimData        : Ptr32 Void
#    +0xfa8 HeapVirtualAffinity : Uint4B
#    +0xfac CurrentTransactionHandle : Ptr32 Void
#    +0xfb0 ActiveFrame      : Ptr32 _TEB_ACTIVE_FRAME
#    +0xfb4 FlsData          : Ptr32 Void
#    +0xfb8 SafeThunkCall    : UChar
#    +0xfb9 BooleanSpare     : [3] UChar
class _TEB_2003(Structure):
    _pack_ = 8
    _fields_ = [
        ("NtTib", NT_TIB),
        ("EnvironmentPointer", PVOID),
        ("ClientId", CLIENT_ID),
        ("ActiveRpcHandle", HANDLE),
        ("ThreadLocalStoragePointer", PVOID),
        ("ProcessEnvironmentBlock", PVOID),  # PPEB
        ("LastErrorValue", DWORD),
        ("CountOfOwnedCriticalSections", DWORD),
        ("CsrClientThread", PVOID),
        ("Win32ThreadInfo", PVOID),
        ("User32Reserved", DWORD * 26),
        ("UserReserved", DWORD * 5),
        ("WOW32Reserved", PVOID),  # ptr to wow64cpu!X86SwitchTo64BitMode
        ("CurrentLocale", DWORD),
        ("FpSoftwareStatusRegister", DWORD),
        ("SystemReserved1", PVOID * 54),
        ("ExceptionCode", SDWORD),
        ("ActivationContextStackPointer", PVOID),  # PACTIVATION_CONTEXT_STACK
        ("SpareBytes1", UCHAR * 40),
        ("GdiTebBatch", GDI_TEB_BATCH),
        ("RealClientId", CLIENT_ID),
        ("GdiCachedProcessHandle", HANDLE),
        ("GdiClientPID", DWORD),
        ("GdiClientTID", DWORD),
        ("GdiThreadLocalInfo", PVOID),
        ("Win32ClientInfo", DWORD * 62),
        ("glDispatchTable", PVOID * 233),
        ("glReserved1", DWORD * 29),
        ("glReserved2", PVOID),
        ("glSectionInfo", PVOID),
        ("glSection", PVOID),
        ("glTable", PVOID),
        ("glCurrentRC", PVOID),
        ("glContext", PVOID),
        ("LastStatusValue", NTSTATUS),
        ("StaticUnicodeString", UNICODE_STRING),
        ("StaticUnicodeBuffer", WCHAR * 261),
        ("DeallocationStack", PVOID),
        ("TlsSlots", PVOID * 64),
        ("TlsLinks", LIST_ENTRY),
        ("Vdm", PVOID),
        ("ReservedForNtRpc", PVOID),
        ("DbgSsReserved", PVOID * 2),
        ("HardErrorMode", DWORD),
        ("Instrumentation", PVOID * 14),
        ("SubProcessTag", PVOID),
        ("EtwTraceData", PVOID),
        ("WinSockData", PVOID),
        ("GdiBatchCount", DWORD),
        ("InDbgPrint", BOOLEAN),
        ("FreeStackOnTermination", BOOLEAN),
        ("HasFiberData", BOOLEAN),
        ("IdealProcessor", UCHAR),
        ("GuaranteedStackBytes", DWORD),
        ("ReservedForPerf", PVOID),
        ("ReservedForOle", PVOID),
        ("WaitingOnLoaderLock", DWORD),
        ("SparePointer1", PVOID),
        ("SoftPatchPtr1", PVOID),
        ("SoftPatchPtr2", PVOID),
        ("TlsExpansionSlots", PVOID),  # Ptr32 Ptr32 Void
        ("ImpersonationLocale", DWORD),
        ("IsImpersonating", BOOL),
        ("NlsCache", PVOID),
        ("pShimData", PVOID),
        ("HeapVirtualAffinity", DWORD),
        ("CurrentTransactionHandle", HANDLE),
        ("ActiveFrame", PVOID),  # PTEB_ACTIVE_FRAME
        ("FlsData", PVOID),
        ("SafeThunkCall", BOOLEAN),
        ("BooleanSpare", BOOLEAN * 3),
    ]


_TEB_2003_64 = _TEB_XP_64
_TEB_2003_R2 = _TEB_2003
_TEB_2003_R2_64 = _TEB_2003_64


#    +0x000 NtTib            : _NT_TIB
#    +0x01c EnvironmentPointer : Ptr32 Void
#    +0x020 ClientId         : _CLIENT_ID
#    +0x028 ActiveRpcHandle  : Ptr32 Void
#    +0x02c ThreadLocalStoragePointer : Ptr32 Void
#    +0x030 ProcessEnvironmentBlock : Ptr32 _PEB
#    +0x034 LastErrorValue   : Uint4B
#    +0x038 CountOfOwnedCriticalSections : Uint4B
#    +0x03c CsrClientThread  : Ptr32 Void
#    +0x040 Win32ThreadInfo  : Ptr32 Void
#    +0x044 User32Reserved   : [26] Uint4B
#    +0x0ac UserReserved     : [5] Uint4B
#    +0x0c0 WOW32Reserved    : Ptr32 Void
#    +0x0c4 CurrentLocale    : Uint4B
#    +0x0c8 FpSoftwareStatusRegister : Uint4B
#    +0x0cc SystemReserved1  : [54] Ptr32 Void
#    +0x1a4 ExceptionCode    : Int4B
#    +0x1a8 ActivationContextStackPointer : Ptr32 _ACTIVATION_CONTEXT_STACK
#    +0x1ac SpareBytes1      : [36] UChar
#    +0x1d0 TxFsContext      : Uint4B
#    +0x1d4 GdiTebBatch      : _GDI_TEB_BATCH
#    +0x6b4 RealClientId     : _CLIENT_ID
#    +0x6bc GdiCachedProcessHandle : Ptr32 Void
#    +0x6c0 GdiClientPID     : Uint4B
#    +0x6c4 GdiClientTID     : Uint4B
#    +0x6c8 GdiThreadLocalInfo : Ptr32 Void
#    +0x6cc Win32ClientInfo  : [62] Uint4B
#    +0x7c4 glDispatchTable  : [233] Ptr32 Void
#    +0xb68 glReserved1      : [29] Uint4B
#    +0xbdc glReserved2      : Ptr32 Void
#    +0xbe0 glSectionInfo    : Ptr32 Void
#    +0xbe4 glSection        : Ptr32 Void
#    +0xbe8 glTable          : Ptr32 Void
#    +0xbec glCurrentRC      : Ptr32 Void
#    +0xbf0 glContext        : Ptr32 Void
#    +0xbf4 LastStatusValue  : Uint4B
#    +0xbf8 StaticUnicodeString : _UNICODE_STRING
#    +0xc00 StaticUnicodeBuffer : [261] Wchar
#    +0xe0c DeallocationStack : Ptr32 Void
#    +0xe10 TlsSlots         : [64] Ptr32 Void
#    +0xf10 TlsLinks         : _LIST_ENTRY
#    +0xf18 Vdm              : Ptr32 Void
#    +0xf1c ReservedForNtRpc : Ptr32 Void
#    +0xf20 DbgSsReserved    : [2] Ptr32 Void
#    +0xf28 HardErrorMode    : Uint4B
#    +0xf2c Instrumentation  : [9] Ptr32 Void
#    +0xf50 ActivityId       : _GUID
#    +0xf60 SubProcessTag    : Ptr32 Void
#    +0xf64 EtwLocalData     : Ptr32 Void
#    +0xf68 EtwTraceData     : Ptr32 Void
#    +0xf6c WinSockData      : Ptr32 Void
#    +0xf70 GdiBatchCount    : Uint4B
#    +0xf74 SpareBool0       : UChar
#    +0xf75 SpareBool1       : UChar
#    +0xf76 SpareBool2       : UChar
#    +0xf77 IdealProcessor   : UChar
#    +0xf78 GuaranteedStackBytes : Uint4B
#    +0xf7c ReservedForPerf  : Ptr32 Void
#    +0xf80 ReservedForOle   : Ptr32 Void
#    +0xf84 WaitingOnLoaderLock : Uint4B
#    +0xf88 SavedPriorityState : Ptr32 Void
#    +0xf8c SoftPatchPtr1    : Uint4B
#    +0xf90 ThreadPoolData   : Ptr32 Void
#    +0xf94 TlsExpansionSlots : Ptr32 Ptr32 Void
#    +0xf98 ImpersonationLocale : Uint4B
#    +0xf9c IsImpersonating  : Uint4B
#    +0xfa0 NlsCache         : Ptr32 Void
#    +0xfa4 pShimData        : Ptr32 Void
#    +0xfa8 HeapVirtualAffinity : Uint4B
#    +0xfac CurrentTransactionHandle : Ptr32 Void
#    +0xfb0 ActiveFrame      : Ptr32 _TEB_ACTIVE_FRAME
#    +0xfb4 FlsData          : Ptr32 Void
#    +0xfb8 PreferredLanguages : Ptr32 Void
#    +0xfbc UserPrefLanguages : Ptr32 Void
#    +0xfc0 MergedPrefLanguages : Ptr32 Void
#    +0xfc4 MuiImpersonation : Uint4B
#    +0xfc8 CrossTebFlags    : Uint2B
#    +0xfc8 SpareCrossTebBits : Pos 0, 16 Bits
#    +0xfca SameTebFlags     : Uint2B
#    +0xfca DbgSafeThunkCall : Pos 0, 1 Bit
#    +0xfca DbgInDebugPrint  : Pos 1, 1 Bit
#    +0xfca DbgHasFiberData  : Pos 2, 1 Bit
#    +0xfca DbgSkipThreadAttach : Pos 3, 1 Bit
#    +0xfca DbgWerInShipAssertCode : Pos 4, 1 Bit
#    +0xfca DbgRanProcessInit : Pos 5, 1 Bit
#    +0xfca DbgClonedThread  : Pos 6, 1 Bit
#    +0xfca DbgSuppressDebugMsg : Pos 7, 1 Bit
#    +0xfca RtlDisableUserStackWalk : Pos 8, 1 Bit
#    +0xfca RtlExceptionAttached : Pos 9, 1 Bit
#    +0xfca SpareSameTebBits : Pos 10, 6 Bits
#    +0xfcc TxnScopeEnterCallback : Ptr32 Void
#    +0xfd0 TxnScopeExitCallback : Ptr32 Void
#    +0xfd4 TxnScopeContext  : Ptr32 Void
#    +0xfd8 LockCount        : Uint4B
#    +0xfdc ProcessRundown   : Uint4B
#    +0xfe0 LastSwitchTime   : Uint8B
#    +0xfe8 TotalSwitchOutTime : Uint8B
#    +0xff0 WaitReasonBitMap : _LARGE_INTEGER
class _TEB_2008(Structure):
    _pack_ = 8
    _fields_ = [
        ("NtTib", NT_TIB),
        ("EnvironmentPointer", PVOID),
        ("ClientId", CLIENT_ID),
        ("ActiveRpcHandle", HANDLE),
        ("ThreadLocalStoragePointer", PVOID),
        ("ProcessEnvironmentBlock", PVOID),  # PPEB
        ("LastErrorValue", DWORD),
        ("CountOfOwnedCriticalSections", DWORD),
        ("CsrClientThread", PVOID),
        ("Win32ThreadInfo", PVOID),
        ("User32Reserved", DWORD * 26),
        ("UserReserved", DWORD * 5),
        ("WOW32Reserved", PVOID),  # ptr to wow64cpu!X86SwitchTo64BitMode
        ("CurrentLocale", DWORD),
        ("FpSoftwareStatusRegister", DWORD),
        ("SystemReserved1", PVOID * 54),
        ("ExceptionCode", SDWORD),
        ("ActivationContextStackPointer", PVOID),  # PACTIVATION_CONTEXT_STACK
        ("SpareBytes1", UCHAR * 36),
        ("TxFsContext", DWORD),
        ("GdiTebBatch", GDI_TEB_BATCH),
        ("RealClientId", CLIENT_ID),
        ("GdiCachedProcessHandle", HANDLE),
        ("GdiClientPID", DWORD),
        ("GdiClientTID", DWORD),
        ("GdiThreadLocalInfo", PVOID),
        ("Win32ClientInfo", DWORD * 62),
        ("glDispatchTable", PVOID * 233),
        ("glReserved1", DWORD * 29),
        ("glReserved2", PVOID),
        ("glSectionInfo", PVOID),
        ("glSection", PVOID),
        ("glTable", PVOID),
        ("glCurrentRC", PVOID),
        ("glContext", PVOID),
        ("LastStatusValue", NTSTATUS),
        ("StaticUnicodeString", UNICODE_STRING),
        ("StaticUnicodeBuffer", WCHAR * 261),
        ("DeallocationStack", PVOID),
        ("TlsSlots", PVOID * 64),
        ("TlsLinks", LIST_ENTRY),
        ("Vdm", PVOID),
        ("ReservedForNtRpc", PVOID),
        ("DbgSsReserved", PVOID * 2),
        ("HardErrorMode", DWORD),
        ("Instrumentation", PVOID * 9),
        ("ActivityId", GUID),
        ("SubProcessTag", PVOID),
        ("EtwLocalData", PVOID),
        ("EtwTraceData", PVOID),
        ("WinSockData", PVOID),
        ("GdiBatchCount", DWORD),
        ("SpareBool0", BOOLEAN),
        ("SpareBool1", BOOLEAN),
        ("SpareBool2", BOOLEAN),
        ("IdealProcessor", UCHAR),
        ("GuaranteedStackBytes", DWORD),
        ("ReservedForPerf", PVOID),
        ("ReservedForOle", PVOID),
        ("WaitingOnLoaderLock", DWORD),
        ("SavedPriorityState", PVOID),
        ("SoftPatchPtr1", PVOID),
        ("ThreadPoolData", PVOID),
        ("TlsExpansionSlots", PVOID),  # Ptr32 Ptr32 Void
        ("ImpersonationLocale", DWORD),
        ("IsImpersonating", BOOL),
        ("NlsCache", PVOID),
        ("pShimData", PVOID),
        ("HeapVirtualAffinity", DWORD),
        ("CurrentTransactionHandle", HANDLE),
        ("ActiveFrame", PVOID),  # PTEB_ACTIVE_FRAME
        ("FlsData", PVOID),
        ("PreferredLanguages", PVOID),
        ("UserPrefLanguages", PVOID),
        ("MergedPrefLanguages", PVOID),
        ("MuiImpersonation", BOOL),
        ("CrossTebFlags", WORD),
        ("SameTebFlags", WORD),
        ("TxnScopeEnterCallback", PVOID),
        ("TxnScopeExitCallback", PVOID),
        ("TxnScopeContext", PVOID),
        ("LockCount", DWORD),
        ("ProcessRundown", DWORD),
        ("LastSwitchTime", QWORD),
        ("TotalSwitchOutTime", QWORD),
        ("WaitReasonBitMap", LONGLONG),  # LARGE_INTEGER
    ]


#    +0x000 NtTib            : _NT_TIB
#    +0x038 EnvironmentPointer : Ptr64 Void
#    +0x040 ClientId         : _CLIENT_ID
#    +0x050 ActiveRpcHandle  : Ptr64 Void
#    +0x058 ThreadLocalStoragePointer : Ptr64 Void
#    +0x060 ProcessEnvironmentBlock : Ptr64 _PEB
#    +0x068 LastErrorValue   : Uint4B
#    +0x06c CountOfOwnedCriticalSections : Uint4B
#    +0x070 CsrClientThread  : Ptr64 Void
#    +0x078 Win32ThreadInfo  : Ptr64 Void
#    +0x080 User32Reserved   : [26] Uint4B
#    +0x0e8 UserReserved     : [5] Uint4B
#    +0x100 WOW32Reserved    : Ptr64 Void
#    +0x108 CurrentLocale    : Uint4B
#    +0x10c FpSoftwareStatusRegister : Uint4B
#    +0x110 SystemReserved1  : [54] Ptr64 Void
#    +0x2c0 ExceptionCode    : Int4B
#    +0x2c8 ActivationContextStackPointer : Ptr64 _ACTIVATION_CONTEXT_STACK
#    +0x2d0 SpareBytes1      : [24] UChar
#    +0x2e8 TxFsContext      : Uint4B
#    +0x2f0 GdiTebBatch      : _GDI_TEB_BATCH
#    +0x7d8 RealClientId     : _CLIENT_ID
#    +0x7e8 GdiCachedProcessHandle : Ptr64 Void
#    +0x7f0 GdiClientPID     : Uint4B
#    +0x7f4 GdiClientTID     : Uint4B
#    +0x7f8 GdiThreadLocalInfo : Ptr64 Void
#    +0x800 Win32ClientInfo  : [62] Uint8B
#    +0x9f0 glDispatchTable  : [233] Ptr64 Void
#    +0x1138 glReserved1      : [29] Uint8B
#    +0x1220 glReserved2      : Ptr64 Void
#    +0x1228 glSectionInfo    : Ptr64 Void
#    +0x1230 glSection        : Ptr64 Void
#    +0x1238 glTable          : Ptr64 Void
#    +0x1240 glCurrentRC      : Ptr64 Void
#    +0x1248 glContext        : Ptr64 Void
#    +0x1250 LastStatusValue  : Uint4B
#    +0x1258 StaticUnicodeString : _UNICODE_STRING
#    +0x1268 StaticUnicodeBuffer : [261] Wchar
#    +0x1478 DeallocationStack : Ptr64 Void
#    +0x1480 TlsSlots         : [64] Ptr64 Void
#    +0x1680 TlsLinks         : _LIST_ENTRY
#    +0x1690 Vdm              : Ptr64 Void
#    +0x1698 ReservedForNtRpc : Ptr64 Void
#    +0x16a0 DbgSsReserved    : [2] Ptr64 Void
#    +0x16b0 HardErrorMode    : Uint4B
#    +0x16b8 Instrumentation  : [11] Ptr64 Void
#    +0x1710 ActivityId       : _GUID
#    +0x1720 SubProcessTag    : Ptr64 Void
#    +0x1728 EtwLocalData     : Ptr64 Void
#    +0x1730 EtwTraceData     : Ptr64 Void
#    +0x1738 WinSockData      : Ptr64 Void
#    +0x1740 GdiBatchCount    : Uint4B
#    +0x1744 SpareBool0       : UChar
#    +0x1745 SpareBool1       : UChar
#    +0x1746 SpareBool2       : UChar
#    +0x1747 IdealProcessor   : UChar
#    +0x1748 GuaranteedStackBytes : Uint4B
#    +0x1750 ReservedForPerf  : Ptr64 Void
#    +0x1758 ReservedForOle   : Ptr64 Void
#    +0x1760 WaitingOnLoaderLock : Uint4B
#    +0x1768 SavedPriorityState : Ptr64 Void
#    +0x1770 SoftPatchPtr1    : Uint8B
#    +0x1778 ThreadPoolData   : Ptr64 Void
#    +0x1780 TlsExpansionSlots : Ptr64 Ptr64 Void
#    +0x1788 DeallocationBStore : Ptr64 Void
#    +0x1790 BStoreLimit      : Ptr64 Void
#    +0x1798 ImpersonationLocale : Uint4B
#    +0x179c IsImpersonating  : Uint4B
#    +0x17a0 NlsCache         : Ptr64 Void
#    +0x17a8 pShimData        : Ptr64 Void
#    +0x17b0 HeapVirtualAffinity : Uint4B
#    +0x17b8 CurrentTransactionHandle : Ptr64 Void
#    +0x17c0 ActiveFrame      : Ptr64 _TEB_ACTIVE_FRAME
#    +0x17c8 FlsData          : Ptr64 Void
#    +0x17d0 PreferredLanguages : Ptr64 Void
#    +0x17d8 UserPrefLanguages : Ptr64 Void
#    +0x17e0 MergedPrefLanguages : Ptr64 Void
#    +0x17e8 MuiImpersonation : Uint4B
#    +0x17ec CrossTebFlags    : Uint2B
#    +0x17ec SpareCrossTebBits : Pos 0, 16 Bits
#    +0x17ee SameTebFlags     : Uint2B
#    +0x17ee DbgSafeThunkCall : Pos 0, 1 Bit
#    +0x17ee DbgInDebugPrint  : Pos 1, 1 Bit
#    +0x17ee DbgHasFiberData  : Pos 2, 1 Bit
#    +0x17ee DbgSkipThreadAttach : Pos 3, 1 Bit
#    +0x17ee DbgWerInShipAssertCode : Pos 4, 1 Bit
#    +0x17ee DbgRanProcessInit : Pos 5, 1 Bit
#    +0x17ee DbgClonedThread  : Pos 6, 1 Bit
#    +0x17ee DbgSuppressDebugMsg : Pos 7, 1 Bit
#    +0x17ee RtlDisableUserStackWalk : Pos 8, 1 Bit
#    +0x17ee RtlExceptionAttached : Pos 9, 1 Bit
#    +0x17ee SpareSameTebBits : Pos 10, 6 Bits
#    +0x17f0 TxnScopeEnterCallback : Ptr64 Void
#    +0x17f8 TxnScopeExitCallback : Ptr64 Void
#    +0x1800 TxnScopeContext  : Ptr64 Void
#    +0x1808 LockCount        : Uint4B
#    +0x180c ProcessRundown   : Uint4B
#    +0x1810 LastSwitchTime   : Uint8B
#    +0x1818 TotalSwitchOutTime : Uint8B
#    +0x1820 WaitReasonBitMap : _LARGE_INTEGER
class _TEB_2008_64(Structure):
    _pack_ = 8
    _fields_ = [
        ("NtTib", NT_TIB),
        ("EnvironmentPointer", PVOID),
        ("ClientId", CLIENT_ID),
        ("ActiveRpcHandle", HANDLE),
        ("ThreadLocalStoragePointer", PVOID),
        ("ProcessEnvironmentBlock", PVOID),  # PPEB
        ("LastErrorValue", DWORD),
        ("CountOfOwnedCriticalSections", DWORD),
        ("CsrClientThread", PVOID),
        ("Win32ThreadInfo", PVOID),
        ("User32Reserved", DWORD * 26),
        ("UserReserved", DWORD * 5),
        ("WOW32Reserved", PVOID),  # ptr to wow64cpu!X86SwitchTo64BitMode
        ("CurrentLocale", DWORD),
        ("FpSoftwareStatusRegister", DWORD),
        ("SystemReserved1", PVOID * 54),
        ("ExceptionCode", SDWORD),
        ("ActivationContextStackPointer", PVOID),  # PACTIVATION_CONTEXT_STACK
        ("SpareBytes1", UCHAR * 24),
        ("TxFsContext", DWORD),
        ("GdiTebBatch", GDI_TEB_BATCH),
        ("RealClientId", CLIENT_ID),
        ("GdiCachedProcessHandle", HANDLE),
        ("GdiClientPID", DWORD),
        ("GdiClientTID", DWORD),
        ("GdiThreadLocalInfo", PVOID),
        ("Win32ClientInfo", QWORD * 62),
        ("glDispatchTable", PVOID * 233),
        ("glReserved1", QWORD * 29),
        ("glReserved2", PVOID),
        ("glSectionInfo", PVOID),
        ("glSection", PVOID),
        ("glTable", PVOID),
        ("glCurrentRC", PVOID),
        ("glContext", PVOID),
        ("LastStatusValue", NTSTATUS),
        ("StaticUnicodeString", UNICODE_STRING),
        ("StaticUnicodeBuffer", WCHAR * 261),
        ("DeallocationStack", PVOID),
        ("TlsSlots", PVOID * 64),
        ("TlsLinks", LIST_ENTRY),
        ("Vdm", PVOID),
        ("ReservedForNtRpc", PVOID),
        ("DbgSsReserved", PVOID * 2),
        ("HardErrorMode", DWORD),
        ("Instrumentation", PVOID * 11),
        ("ActivityId", GUID),
        ("SubProcessTag", PVOID),
        ("EtwLocalData", PVOID),
        ("EtwTraceData", PVOID),
        ("WinSockData", PVOID),
        ("GdiBatchCount", DWORD),
        ("SpareBool0", BOOLEAN),
        ("SpareBool1", BOOLEAN),
        ("SpareBool2", BOOLEAN),
        ("IdealProcessor", UCHAR),
        ("GuaranteedStackBytes", DWORD),
        ("ReservedForPerf", PVOID),
        ("ReservedForOle", PVOID),
        ("WaitingOnLoaderLock", DWORD),
        ("SavedPriorityState", PVOID),
        ("SoftPatchPtr1", PVOID),
        ("ThreadPoolData", PVOID),
        ("TlsExpansionSlots", PVOID),  # Ptr64 Ptr64 Void
        ("DeallocationBStore", PVOID),
        ("BStoreLimit", PVOID),
        ("ImpersonationLocale", DWORD),
        ("IsImpersonating", BOOL),
        ("NlsCache", PVOID),
        ("pShimData", PVOID),
        ("HeapVirtualAffinity", DWORD),
        ("CurrentTransactionHandle", HANDLE),
        ("ActiveFrame", PVOID),  # PTEB_ACTIVE_FRAME
        ("FlsData", PVOID),
        ("PreferredLanguages", PVOID),
        ("UserPrefLanguages", PVOID),
        ("MergedPrefLanguages", PVOID),
        ("MuiImpersonation", BOOL),
        ("CrossTebFlags", WORD),
        ("SameTebFlags", WORD),
        ("TxnScopeEnterCallback", PVOID),
        ("TxnScopeExitCallback", PVOID),
        ("TxnScopeContext", PVOID),
        ("LockCount", DWORD),
        ("ProcessRundown", DWORD),
        ("LastSwitchTime", QWORD),
        ("TotalSwitchOutTime", QWORD),
        ("WaitReasonBitMap", LONGLONG),  # LARGE_INTEGER
    ]


#    +0x000 NtTib            : _NT_TIB
#    +0x01c EnvironmentPointer : Ptr32 Void
#    +0x020 ClientId         : _CLIENT_ID
#    +0x028 ActiveRpcHandle  : Ptr32 Void
#    +0x02c ThreadLocalStoragePointer : Ptr32 Void
#    +0x030 ProcessEnvironmentBlock : Ptr32 _PEB
#    +0x034 LastErrorValue   : Uint4B
#    +0x038 CountOfOwnedCriticalSections : Uint4B
#    +0x03c CsrClientThread  : Ptr32 Void
#    +0x040 Win32ThreadInfo  : Ptr32 Void
#    +0x044 User32Reserved   : [26] Uint4B
#    +0x0ac UserReserved     : [5] Uint4B
#    +0x0c0 WOW32Reserved    : Ptr32 Void
#    +0x0c4 CurrentLocale    : Uint4B
#    +0x0c8 FpSoftwareStatusRegister : Uint4B
#    +0x0cc SystemReserved1  : [54] Ptr32 Void
#    +0x1a4 ExceptionCode    : Int4B
#    +0x1a8 ActivationContextStackPointer : Ptr32 _ACTIVATION_CONTEXT_STACK
#    +0x1ac SpareBytes       : [36] UChar
#    +0x1d0 TxFsContext      : Uint4B
#    +0x1d4 GdiTebBatch      : _GDI_TEB_BATCH
#    +0x6b4 RealClientId     : _CLIENT_ID
#    +0x6bc GdiCachedProcessHandle : Ptr32 Void
#    +0x6c0 GdiClientPID     : Uint4B
#    +0x6c4 GdiClientTID     : Uint4B
#    +0x6c8 GdiThreadLocalInfo : Ptr32 Void
#    +0x6cc Win32ClientInfo  : [62] Uint4B
#    +0x7c4 glDispatchTable  : [233] Ptr32 Void
#    +0xb68 glReserved1      : [29] Uint4B
#    +0xbdc glReserved2      : Ptr32 Void
#    +0xbe0 glSectionInfo    : Ptr32 Void
#    +0xbe4 glSection        : Ptr32 Void
#    +0xbe8 glTable          : Ptr32 Void
#    +0xbec glCurrentRC      : Ptr32 Void
#    +0xbf0 glContext        : Ptr32 Void
#    +0xbf4 LastStatusValue  : Uint4B
#    +0xbf8 StaticUnicodeString : _UNICODE_STRING
#    +0xc00 StaticUnicodeBuffer : [261] Wchar
#    +0xe0c DeallocationStack : Ptr32 Void
#    +0xe10 TlsSlots         : [64] Ptr32 Void
#    +0xf10 TlsLinks         : _LIST_ENTRY
#    +0xf18 Vdm              : Ptr32 Void
#    +0xf1c ReservedForNtRpc : Ptr32 Void
#    +0xf20 DbgSsReserved    : [2] Ptr32 Void
#    +0xf28 HardErrorMode    : Uint4B
#    +0xf2c Instrumentation  : [9] Ptr32 Void
#    +0xf50 ActivityId       : _GUID
#    +0xf60 SubProcessTag    : Ptr32 Void
#    +0xf64 EtwLocalData     : Ptr32 Void
#    +0xf68 EtwTraceData     : Ptr32 Void
#    +0xf6c WinSockData      : Ptr32 Void
#    +0xf70 GdiBatchCount    : Uint4B
#    +0xf74 CurrentIdealProcessor : _PROCESSOR_NUMBER
#    +0xf74 IdealProcessorValue : Uint4B
#    +0xf74 ReservedPad0     : UChar
#    +0xf75 ReservedPad1     : UChar
#    +0xf76 ReservedPad2     : UChar
#    +0xf77 IdealProcessor   : UChar
#    +0xf78 GuaranteedStackBytes : Uint4B
#    +0xf7c ReservedForPerf  : Ptr32 Void
#    +0xf80 ReservedForOle   : Ptr32 Void
#    +0xf84 WaitingOnLoaderLock : Uint4B
#    +0xf88 SavedPriorityState : Ptr32 Void
#    +0xf8c SoftPatchPtr1    : Uint4B
#    +0xf90 ThreadPoolData   : Ptr32 Void
#    +0xf94 TlsExpansionSlots : Ptr32 Ptr32 Void
#    +0xf98 MuiGeneration    : Uint4B
#    +0xf9c IsImpersonating  : Uint4B
#    +0xfa0 NlsCache         : Ptr32 Void
#    +0xfa4 pShimData        : Ptr32 Void
#    +0xfa8 HeapVirtualAffinity : Uint4B
#    +0xfac CurrentTransactionHandle : Ptr32 Void
#    +0xfb0 ActiveFrame      : Ptr32 _TEB_ACTIVE_FRAME
#    +0xfb4 FlsData          : Ptr32 Void
#    +0xfb8 PreferredLanguages : Ptr32 Void
#    +0xfbc UserPrefLanguages : Ptr32 Void
#    +0xfc0 MergedPrefLanguages : Ptr32 Void
#    +0xfc4 MuiImpersonation : Uint4B
#    +0xfc8 CrossTebFlags    : Uint2B
#    +0xfc8 SpareCrossTebBits : Pos 0, 16 Bits
#    +0xfca SameTebFlags     : Uint2B
#    +0xfca SafeThunkCall    : Pos 0, 1 Bit
#    +0xfca InDebugPrint     : Pos 1, 1 Bit
#    +0xfca HasFiberData     : Pos 2, 1 Bit
#    +0xfca SkipThreadAttach : Pos 3, 1 Bit
#    +0xfca WerInShipAssertCode : Pos 4, 1 Bit
#    +0xfca RanProcessInit   : Pos 5, 1 Bit
#    +0xfca ClonedThread     : Pos 6, 1 Bit
#    +0xfca SuppressDebugMsg : Pos 7, 1 Bit
#    +0xfca DisableUserStackWalk : Pos 8, 1 Bit
#    +0xfca RtlExceptionAttached : Pos 9, 1 Bit
#    +0xfca InitialThread    : Pos 10, 1 Bit
#    +0xfca SpareSameTebBits : Pos 11, 5 Bits
#    +0xfcc TxnScopeEnterCallback : Ptr32 Void
#    +0xfd0 TxnScopeExitCallback : Ptr32 Void
#    +0xfd4 TxnScopeContext  : Ptr32 Void
#    +0xfd8 LockCount        : Uint4B
#    +0xfdc SpareUlong0      : Uint4B
#    +0xfe0 ResourceRetValue : Ptr32 Void
class _TEB_2008_R2(Structure):
    _pack_ = 8
    _fields_ = [
        ("NtTib", NT_TIB),
        ("EnvironmentPointer", PVOID),
        ("ClientId", CLIENT_ID),
        ("ActiveRpcHandle", HANDLE),
        ("ThreadLocalStoragePointer", PVOID),
        ("ProcessEnvironmentBlock", PVOID),  # PPEB
        ("LastErrorValue", DWORD),
        ("CountOfOwnedCriticalSections", DWORD),
        ("CsrClientThread", PVOID),
        ("Win32ThreadInfo", PVOID),
        ("User32Reserved", DWORD * 26),
        ("UserReserved", DWORD * 5),
        ("WOW32Reserved", PVOID),  # ptr to wow64cpu!X86SwitchTo64BitMode
        ("CurrentLocale", DWORD),
        ("FpSoftwareStatusRegister", DWORD),
        ("SystemReserved1", PVOID * 54),
        ("ExceptionCode", SDWORD),
        ("ActivationContextStackPointer", PVOID),  # PACTIVATION_CONTEXT_STACK
        ("SpareBytes", UCHAR * 36),
        ("TxFsContext", DWORD),
        ("GdiTebBatch", GDI_TEB_BATCH),
        ("RealClientId", CLIENT_ID),
        ("GdiCachedProcessHandle", HANDLE),
        ("GdiClientPID", DWORD),
        ("GdiClientTID", DWORD),
        ("GdiThreadLocalInfo", PVOID),
        ("Win32ClientInfo", DWORD * 62),
        ("glDispatchTable", PVOID * 233),
        ("glReserved1", DWORD * 29),
        ("glReserved2", PVOID),
        ("glSectionInfo", PVOID),
        ("glSection", PVOID),
        ("glTable", PVOID),
        ("glCurrentRC", PVOID),
        ("glContext", PVOID),
        ("LastStatusValue", NTSTATUS),
        ("StaticUnicodeString", UNICODE_STRING),
        ("StaticUnicodeBuffer", WCHAR * 261),
        ("DeallocationStack", PVOID),
        ("TlsSlots", PVOID * 64),
        ("TlsLinks", LIST_ENTRY),
        ("Vdm", PVOID),
        ("ReservedForNtRpc", PVOID),
        ("DbgSsReserved", PVOID * 2),
        ("HardErrorMode", DWORD),
        ("Instrumentation", PVOID * 9),
        ("ActivityId", GUID),
        ("SubProcessTag", PVOID),
        ("EtwLocalData", PVOID),
        ("EtwTraceData", PVOID),
        ("WinSockData", PVOID),
        ("GdiBatchCount", DWORD),
        ("CurrentIdealProcessor", PROCESSOR_NUMBER),
        ("IdealProcessorValue", DWORD),
        ("ReservedPad0", UCHAR),
        ("ReservedPad1", UCHAR),
        ("ReservedPad2", UCHAR),
        ("IdealProcessor", UCHAR),
        ("GuaranteedStackBytes", DWORD),
        ("ReservedForPerf", PVOID),
        ("ReservedForOle", PVOID),
        ("WaitingOnLoaderLock", DWORD),
        ("SavedPriorityState", PVOID),
        ("SoftPatchPtr1", PVOID),
        ("ThreadPoolData", PVOID),
        ("TlsExpansionSlots", PVOID),  # Ptr32 Ptr32 Void
        ("MuiGeneration", DWORD),
        ("IsImpersonating", BOOL),
        ("NlsCache", PVOID),
        ("pShimData", PVOID),
        ("HeapVirtualAffinity", DWORD),
        ("CurrentTransactionHandle", HANDLE),
        ("ActiveFrame", PVOID),  # PTEB_ACTIVE_FRAME
        ("FlsData", PVOID),
        ("PreferredLanguages", PVOID),
        ("UserPrefLanguages", PVOID),
        ("MergedPrefLanguages", PVOID),
        ("MuiImpersonation", BOOL),
        ("CrossTebFlags", WORD),
        ("SameTebFlags", WORD),
        ("TxnScopeEnterCallback", PVOID),
        ("TxnScopeExitCallback", PVOID),
        ("TxnScopeContext", PVOID),
        ("LockCount", DWORD),
        ("SpareUlong0", ULONG),
        ("ResourceRetValue", PVOID),
    ]


#    +0x000 NtTib            : _NT_TIB
#    +0x038 EnvironmentPointer : Ptr64 Void
#    +0x040 ClientId         : _CLIENT_ID
#    +0x050 ActiveRpcHandle  : Ptr64 Void
#    +0x058 ThreadLocalStoragePointer : Ptr64 Void
#    +0x060 ProcessEnvironmentBlock : Ptr64 _PEB
#    +0x068 LastErrorValue   : Uint4B
#    +0x06c CountOfOwnedCriticalSections : Uint4B
#    +0x070 CsrClientThread  : Ptr64 Void
#    +0x078 Win32ThreadInfo  : Ptr64 Void
#    +0x080 User32Reserved   : [26] Uint4B
#    +0x0e8 UserReserved     : [5] Uint4B
#    +0x100 WOW32Reserved    : Ptr64 Void
#    +0x108 CurrentLocale    : Uint4B
#    +0x10c FpSoftwareStatusRegister : Uint4B
#    +0x110 SystemReserved1  : [54] Ptr64 Void
#    +0x2c0 ExceptionCode    : Int4B
#    +0x2c8 ActivationContextStackPointer : Ptr64 _ACTIVATION_CONTEXT_STACK
#    +0x2d0 SpareBytes       : [24] UChar
#    +0x2e8 TxFsContext      : Uint4B
#    +0x2f0 GdiTebBatch      : _GDI_TEB_BATCH
#    +0x7d8 RealClientId     : _CLIENT_ID
#    +0x7e8 GdiCachedProcessHandle : Ptr64 Void
#    +0x7f0 GdiClientPID     : Uint4B
#    +0x7f4 GdiClientTID     : Uint4B
#    +0x7f8 GdiThreadLocalInfo : Ptr64 Void
#    +0x800 Win32ClientInfo  : [62] Uint8B
#    +0x9f0 glDispatchTable  : [233] Ptr64 Void
#    +0x1138 glReserved1      : [29] Uint8B
#    +0x1220 glReserved2      : Ptr64 Void
#    +0x1228 glSectionInfo    : Ptr64 Void
#    +0x1230 glSection        : Ptr64 Void
#    +0x1238 glTable          : Ptr64 Void
#    +0x1240 glCurrentRC      : Ptr64 Void
#    +0x1248 glContext        : Ptr64 Void
#    +0x1250 LastStatusValue  : Uint4B
#    +0x1258 StaticUnicodeString : _UNICODE_STRING
#    +0x1268 StaticUnicodeBuffer : [261] Wchar
#    +0x1478 DeallocationStack : Ptr64 Void
#    +0x1480 TlsSlots         : [64] Ptr64 Void
#    +0x1680 TlsLinks         : _LIST_ENTRY
#    +0x1690 Vdm              : Ptr64 Void
#    +0x1698 ReservedForNtRpc : Ptr64 Void
#    +0x16a0 DbgSsReserved    : [2] Ptr64 Void
#    +0x16b0 HardErrorMode    : Uint4B
#    +0x16b8 Instrumentation  : [11] Ptr64 Void
#    +0x1710 ActivityId       : _GUID
#    +0x1720 SubProcessTag    : Ptr64 Void
#    +0x1728 EtwLocalData     : Ptr64 Void
#    +0x1730 EtwTraceData     : Ptr64 Void
#    +0x1738 WinSockData      : Ptr64 Void
#    +0x1740 GdiBatchCount    : Uint4B
#    +0x1744 CurrentIdealProcessor : _PROCESSOR_NUMBER
#    +0x1744 IdealProcessorValue : Uint4B
#    +0x1744 ReservedPad0     : UChar
#    +0x1745 ReservedPad1     : UChar
#    +0x1746 ReservedPad2     : UChar
#    +0x1747 IdealProcessor   : UChar
#    +0x1748 GuaranteedStackBytes : Uint4B
#    +0x1750 ReservedForPerf  : Ptr64 Void
#    +0x1758 ReservedForOle   : Ptr64 Void
#    +0x1760 WaitingOnLoaderLock : Uint4B
#    +0x1768 SavedPriorityState : Ptr64 Void
#    +0x1770 SoftPatchPtr1    : Uint8B
#    +0x1778 ThreadPoolData   : Ptr64 Void
#    +0x1780 TlsExpansionSlots : Ptr64 Ptr64 Void
#    +0x1788 DeallocationBStore : Ptr64 Void
#    +0x1790 BStoreLimit      : Ptr64 Void
#    +0x1798 MuiGeneration    : Uint4B
#    +0x179c IsImpersonating  : Uint4B
#    +0x17a0 NlsCache         : Ptr64 Void
#    +0x17a8 pShimData        : Ptr64 Void
#    +0x17b0 HeapVirtualAffinity : Uint4B
#    +0x17b8 CurrentTransactionHandle : Ptr64 Void
#    +0x17c0 ActiveFrame      : Ptr64 _TEB_ACTIVE_FRAME
#    +0x17c8 FlsData          : Ptr64 Void
#    +0x17d0 PreferredLanguages : Ptr64 Void
#    +0x17d8 UserPrefLanguages : Ptr64 Void
#    +0x17e0 MergedPrefLanguages : Ptr64 Void
#    +0x17e8 MuiImpersonation : Uint4B
#    +0x17ec CrossTebFlags    : Uint2B
#    +0x17ec SpareCrossTebBits : Pos 0, 16 Bits
#    +0x17ee SameTebFlags     : Uint2B
#    +0x17ee SafeThunkCall    : Pos 0, 1 Bit
#    +0x17ee InDebugPrint     : Pos 1, 1 Bit
#    +0x17ee HasFiberData     : Pos 2, 1 Bit
#    +0x17ee SkipThreadAttach : Pos 3, 1 Bit
#    +0x17ee WerInShipAssertCode : Pos 4, 1 Bit
#    +0x17ee RanProcessInit   : Pos 5, 1 Bit
#    +0x17ee ClonedThread     : Pos 6, 1 Bit
#    +0x17ee SuppressDebugMsg : Pos 7, 1 Bit
#    +0x17ee DisableUserStackWalk : Pos 8, 1 Bit
#    +0x17ee RtlExceptionAttached : Pos 9, 1 Bit
#    +0x17ee InitialThread    : Pos 10, 1 Bit
#    +0x17ee SpareSameTebBits : Pos 11, 5 Bits
#    +0x17f0 TxnScopeEnterCallback : Ptr64 Void
#    +0x17f8 TxnScopeExitCallback : Ptr64 Void
#    +0x1800 TxnScopeContext  : Ptr64 Void
#    +0x1808 LockCount        : Uint4B
#    +0x180c SpareUlong0      : Uint4B
#    +0x1810 ResourceRetValue : Ptr64 Void
class _TEB_2008_R2_64(Structure):
    _pack_ = 8
    _fields_ = [
        ("NtTib", NT_TIB),
        ("EnvironmentPointer", PVOID),
        ("ClientId", CLIENT_ID),
        ("ActiveRpcHandle", HANDLE),
        ("ThreadLocalStoragePointer", PVOID),
        ("ProcessEnvironmentBlock", PVOID),  # PPEB
        ("LastErrorValue", DWORD),
        ("CountOfOwnedCriticalSections", DWORD),
        ("CsrClientThread", PVOID),
        ("Win32ThreadInfo", PVOID),
        ("User32Reserved", DWORD * 26),
        ("UserReserved", DWORD * 5),
        ("WOW32Reserved", PVOID),  # ptr to wow64cpu!X86SwitchTo64BitMode
        ("CurrentLocale", DWORD),
        ("FpSoftwareStatusRegister", DWORD),
        ("SystemReserved1", PVOID * 54),
        ("ExceptionCode", SDWORD),
        ("ActivationContextStackPointer", PVOID),  # PACTIVATION_CONTEXT_STACK
        ("SpareBytes", UCHAR * 24),
        ("TxFsContext", DWORD),
        ("GdiTebBatch", GDI_TEB_BATCH),
        ("RealClientId", CLIENT_ID),
        ("GdiCachedProcessHandle", HANDLE),
        ("GdiClientPID", DWORD),
        ("GdiClientTID", DWORD),
        ("GdiThreadLocalInfo", PVOID),
        ("Win32ClientInfo", DWORD * 62),
        ("glDispatchTable", PVOID * 233),
        ("glReserved1", QWORD * 29),
        ("glReserved2", PVOID),
        ("glSectionInfo", PVOID),
        ("glSection", PVOID),
        ("glTable", PVOID),
        ("glCurrentRC", PVOID),
        ("glContext", PVOID),
        ("LastStatusValue", NTSTATUS),
        ("StaticUnicodeString", UNICODE_STRING),
        ("StaticUnicodeBuffer", WCHAR * 261),
        ("DeallocationStack", PVOID),
        ("TlsSlots", PVOID * 64),
        ("TlsLinks", LIST_ENTRY),
        ("Vdm", PVOID),
        ("ReservedForNtRpc", PVOID),
        ("DbgSsReserved", PVOID * 2),
        ("HardErrorMode", DWORD),
        ("Instrumentation", PVOID * 11),
        ("ActivityId", GUID),
        ("SubProcessTag", PVOID),
        ("EtwLocalData", PVOID),
        ("EtwTraceData", PVOID),
        ("WinSockData", PVOID),
        ("GdiBatchCount", DWORD),
        ("CurrentIdealProcessor", PROCESSOR_NUMBER),
        ("IdealProcessorValue", DWORD),
        ("ReservedPad0", UCHAR),
        ("ReservedPad1", UCHAR),
        ("ReservedPad2", UCHAR),
        ("IdealProcessor", UCHAR),
        ("GuaranteedStackBytes", DWORD),
        ("ReservedForPerf", PVOID),
        ("ReservedForOle", PVOID),
        ("WaitingOnLoaderLock", DWORD),
        ("SavedPriorityState", PVOID),
        ("SoftPatchPtr1", PVOID),
        ("ThreadPoolData", PVOID),
        ("TlsExpansionSlots", PVOID),  # Ptr64 Ptr64 Void
        ("DeallocationBStore", PVOID),
        ("BStoreLimit", PVOID),
        ("MuiGeneration", DWORD),
        ("IsImpersonating", BOOL),
        ("NlsCache", PVOID),
        ("pShimData", PVOID),
        ("HeapVirtualAffinity", DWORD),
        ("CurrentTransactionHandle", HANDLE),
        ("ActiveFrame", PVOID),  # PTEB_ACTIVE_FRAME
        ("FlsData", PVOID),
        ("PreferredLanguages", PVOID),
        ("UserPrefLanguages", PVOID),
        ("MergedPrefLanguages", PVOID),
        ("MuiImpersonation", BOOL),
        ("CrossTebFlags", WORD),
        ("SameTebFlags", WORD),
        ("TxnScopeEnterCallback", PVOID),
        ("TxnScopeExitCallback", PVOID),
        ("TxnScopeContext", PVOID),
        ("LockCount", DWORD),
        ("SpareUlong0", ULONG),
        ("ResourceRetValue", PVOID),
    ]


_TEB_Vista = _TEB_2008
_TEB_Vista_64 = _TEB_2008_64
_TEB_W7 = _TEB_2008_R2
_TEB_W7_64 = _TEB_2008_R2_64


# Use the correct TEB structure definition.
# Defaults to the latest Windows version.
class TEB(Structure):
    _pack_ = 8
    if os == "Windows NT":
        _pack_ = _TEB_NT._pack_
        _fields_ = _TEB_NT._fields_
    elif os == "Windows 2000":
        _pack_ = _TEB_2000._pack_
        _fields_ = _TEB_2000._fields_
    elif os == "Windows XP":
        _fields_ = _TEB_XP._fields_
    elif os == "Windows XP (64 bits)":
        _fields_ = _TEB_XP_64._fields_
    elif os == "Windows 2003":
        _fields_ = _TEB_2003._fields_
    elif os == "Windows 2003 (64 bits)":
        _fields_ = _TEB_2003_64._fields_
    elif os == "Windows 2008":
        _fields_ = _TEB_2008._fields_
    elif os == "Windows 2008 (64 bits)":
        _fields_ = _TEB_2008_64._fields_
    elif os == "Windows 2003 R2":
        _fields_ = _TEB_2003_R2._fields_
    elif os == "Windows 2003 R2 (64 bits)":
        _fields_ = _TEB_2003_R2_64._fields_
    elif os == "Windows 2008 R2":
        _fields_ = _TEB_2008_R2._fields_
    elif os == "Windows 2008 R2 (64 bits)":
        _fields_ = _TEB_2008_R2_64._fields_
    elif os == "Windows Vista":
        _fields_ = _TEB_Vista._fields_
    elif os == "Windows Vista (64 bits)":
        _fields_ = _TEB_Vista_64._fields_
    elif os == "Windows 7":
        _fields_ = _TEB_W7._fields_
    elif os == "Windows 7 (64 bits)":
        _fields_ = _TEB_W7_64._fields_
    elif sizeof(SIZE_T) == sizeof(DWORD):
        _fields_ = _TEB_W7._fields_
    else:
        _fields_ = _TEB_W7_64._fields_


PTEB = POINTER(TEB)

# ==============================================================================
# This calculates the list of exported symbols.
_all = set(vars().keys()).difference(_all)
__all__ = [_x for _x in _all if not _x.startswith("_")]
__all__.sort()
# ==============================================================================