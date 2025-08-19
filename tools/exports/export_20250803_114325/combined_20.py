
# === NexusCore/openenv\Lib\site-packages\numpy\lib\mixins.py ===
"""
Mixin classes for custom array types that don't inherit from ndarray.
"""

__all__ = ['NDArrayOperatorsMixin']


def _disables_array_ufunc(obj):
    """True when __array_ufunc__ is set to None."""
    try:
        return obj.__array_ufunc__ is None
    except AttributeError:
        return False


def _binary_method(ufunc, name):
    """Implement a forward binary method with a ufunc, e.g., __add__."""
    def func(self, other):
        if _disables_array_ufunc(other):
            return NotImplemented
        return ufunc(self, other)
    func.__name__ = f'__{name}__'
    return func


def _reflected_binary_method(ufunc, name):
    """Implement a reflected binary method with a ufunc, e.g., __radd__."""
    def func(self, other):
        if _disables_array_ufunc(other):
            return NotImplemented
        return ufunc(other, self)
    func.__name__ = f'__r{name}__'
    return func


def _inplace_binary_method(ufunc, name):
    """Implement an in-place binary method with a ufunc, e.g., __iadd__."""
    def func(self, other):
        return ufunc(self, other, out=(self,))
    func.__name__ = f'__i{name}__'
    return func


def _numeric_methods(ufunc, name):
    """Implement forward, reflected and inplace binary methods with a ufunc."""
    return (_binary_method(ufunc, name),
            _reflected_binary_method(ufunc, name),
            _inplace_binary_method(ufunc, name))


def _unary_method(ufunc, name):
    """Implement a unary special method with a ufunc."""
    def func(self):
        return ufunc(self)
    func.__name__ = f'__{name}__'
    return func


class NDArrayOperatorsMixin:
    """Mixin defining all operator special methods using __array_ufunc__.

    This class implements the special methods for almost all of Python's
    builtin operators defined in the `operator` module, including comparisons
    (``==``, ``>``, etc.) and arithmetic (``+``, ``*``, ``-``, etc.), by
    deferring to the ``__array_ufunc__`` method, which subclasses must
    implement.

    It is useful for writing classes that do not inherit from `numpy.ndarray`,
    but that should support arithmetic and numpy universal functions like
    arrays as described in :external+neps:doc:`nep-0013-ufunc-overrides`.

    As an trivial example, consider this implementation of an ``ArrayLike``
    class that simply wraps a NumPy array and ensures that the result of any
    arithmetic operation is also an ``ArrayLike`` object:

        >>> import numbers
        >>> class ArrayLike(np.lib.mixins.NDArrayOperatorsMixin):
        ...     def __init__(self, value):
        ...         self.value = np.asarray(value)
        ...
        ...     # One might also consider adding the built-in list type to this
        ...     # list, to support operations like np.add(array_like, list)
        ...     _HANDLED_TYPES = (np.ndarray, numbers.Number)
        ...
        ...     def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        ...         out = kwargs.get('out', ())
        ...         for x in inputs + out:
        ...             # Only support operations with instances of
        ...             # _HANDLED_TYPES. Use ArrayLike instead of type(self)
        ...             # for isinstance to allow subclasses that don't
        ...             # override __array_ufunc__ to handle ArrayLike objects.
        ...             if not isinstance(
        ...                 x, self._HANDLED_TYPES + (ArrayLike,)
        ...             ):
        ...                 return NotImplemented
        ...
        ...         # Defer to the implementation of the ufunc
        ...         # on unwrapped values.
        ...         inputs = tuple(x.value if isinstance(x, ArrayLike) else x
        ...                     for x in inputs)
        ...         if out:
        ...             kwargs['out'] = tuple(
        ...                 x.value if isinstance(x, ArrayLike) else x
        ...                 for x in out)
        ...         result = getattr(ufunc, method)(*inputs, **kwargs)
        ...
        ...         if type(result) is tuple:
        ...             # multiple return values
        ...             return tuple(type(self)(x) for x in result)
        ...         elif method == 'at':
        ...             # no return value
        ...             return None
        ...         else:
        ...             # one return value
        ...             return type(self)(result)
        ...
        ...     def __repr__(self):
        ...         return '%s(%r)' % (type(self).__name__, self.value)

    In interactions between ``ArrayLike`` objects and numbers or numpy arrays,
    the result is always another ``ArrayLike``:

        >>> x = ArrayLike([1, 2, 3])
        >>> x - 1
        ArrayLike(array([0, 1, 2]))
        >>> 1 - x
        ArrayLike(array([ 0, -1, -2]))
        >>> np.arange(3) - x
        ArrayLike(array([-1, -1, -1]))
        >>> x - np.arange(3)
        ArrayLike(array([1, 1, 1]))

    Note that unlike ``numpy.ndarray``, ``ArrayLike`` does not allow operations
    with arbitrary, unrecognized types. This ensures that interactions with
    ArrayLike preserve a well-defined casting hierarchy.

    """
    from numpy._core import umath as um

    __slots__ = ()
    # Like np.ndarray, this mixin class implements "Option 1" from the ufunc
    # overrides NEP.

    # comparisons don't have reflected and in-place versions
    __lt__ = _binary_method(um.less, 'lt')
    __le__ = _binary_method(um.less_equal, 'le')
    __eq__ = _binary_method(um.equal, 'eq')
    __ne__ = _binary_method(um.not_equal, 'ne')
    __gt__ = _binary_method(um.greater, 'gt')
    __ge__ = _binary_method(um.greater_equal, 'ge')

    # numeric methods
    __add__, __radd__, __iadd__ = _numeric_methods(um.add, 'add')
    __sub__, __rsub__, __isub__ = _numeric_methods(um.subtract, 'sub')
    __mul__, __rmul__, __imul__ = _numeric_methods(um.multiply, 'mul')
    __matmul__, __rmatmul__, __imatmul__ = _numeric_methods(
        um.matmul, 'matmul')
    __truediv__, __rtruediv__, __itruediv__ = _numeric_methods(
        um.true_divide, 'truediv')
    __floordiv__, __rfloordiv__, __ifloordiv__ = _numeric_methods(
        um.floor_divide, 'floordiv')
    __mod__, __rmod__, __imod__ = _numeric_methods(um.remainder, 'mod')
    __divmod__ = _binary_method(um.divmod, 'divmod')
    __rdivmod__ = _reflected_binary_method(um.divmod, 'divmod')
    # __idivmod__ does not exist
    # TODO: handle the optional third argument for __pow__?
    __pow__, __rpow__, __ipow__ = _numeric_methods(um.power, 'pow')
    __lshift__, __rlshift__, __ilshift__ = _numeric_methods(
        um.left_shift, 'lshift')
    __rshift__, __rrshift__, __irshift__ = _numeric_methods(
        um.right_shift, 'rshift')
    __and__, __rand__, __iand__ = _numeric_methods(um.bitwise_and, 'and')
    __xor__, __rxor__, __ixor__ = _numeric_methods(um.bitwise_xor, 'xor')
    __or__, __ror__, __ior__ = _numeric_methods(um.bitwise_or, 'or')

    # unary methods
    __neg__ = _unary_method(um.negative, 'neg')
    __pos__ = _unary_method(um.positive, 'pos')
    __abs__ = _unary_method(um.absolute, 'abs')
    __invert__ = _unary_method(um.invert, 'invert')

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\lib\llmfn_output_row.py ===
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
"""LLMFnOutputRow."""
from __future__ import annotations

import abc
from typing import Any, Iterator, Mapping


# The type of value stored in a cell.
_CELLVALUETYPE = Any


def _get_name_of_type(x: type[Any]) -> str:
    if hasattr(x, "__name__"):
        return x.__name__
    return str(x)


def _validate_is_result_type(value: Any, result_type: type[Any]) -> None:
    if result_type == Any:
        return
    if not isinstance(value, result_type):
        raise ValueError(
            'Value of last entry must be of type "{}", got "{}"'.format(
                _get_name_of_type(result_type),
                _get_name_of_type(type(value)),
            )
        )


class LLMFnOutputRowView(Mapping[str, _CELLVALUETYPE], metaclass=abc.ABCMeta):
    """Immutable view of LLMFnOutputRow."""

    # Additional methods (not required by Mapping[str, _CELLVALUETYPE])
    @abc.abstractmethod
    def __contains__(self, k: str) -> bool:
        """For expressions like: x in this_instance."""

    @abc.abstractmethod
    def __str__(self) -> str:
        """For expressions like: str(this_instance)."""

    # Own methods.
    @abc.abstractmethod
    def result_type(self) -> type[Any]:
        """Returns the type enforced for the result cell."""

    @abc.abstractmethod
    def result_value(self) -> Any:
        """Get the value of the result cell."""

    @abc.abstractmethod
    def result_key(self) -> str:
        """Get the key of the result cell."""


class LLMFnOutputRow(LLMFnOutputRowView):
    """Container that represents a single row in a table of outputs.

    We represent outputs as a table. This class represents a single row in the
    table like a dictionary, where the key is the column name and the value is the
    cell value.

    A single cell is designated the "result". This contains the output of the LLM
    model after running any post-processing functions specified by the user.

    In addition to behaving like a dictionary, this class provides additional
    methods, including:
    - Getting the value of the "result" cell
    - Setting the value (and optionally the key) of the "result" cell.
    - Add a new non-result cell

    Notes: As an implementation detail, the result-cell is always kept as the
    rightmost cell.
    """

    def __init__(self, data: Mapping[str, _CELLVALUETYPE], result_type: type[Any]):
        """Constructor.

        Args:
          data: The initial value of the row. The last entry will be treated as the
            result. Cannot be empty. The value of the last entry must be `str`.
          result_type: The type of the result cell. This will be enforced at
            runtime.
        """
        self._data: dict[str, _CELLVALUETYPE] = dict(data)
        if not self._data:
            raise ValueError("Must provide non-empty data")

        self._result_type = result_type
        result_value = list(self._data.values())[-1]
        _validate_is_result_type(result_value, self._result_type)

    # Methods needed for Mapping[str, _CELLVALUETYPE]:
    def __iter__(self) -> Iterator[str]:
        return self._data.__iter__()

    def __len__(self) -> int:
        return self._data.__len__()

    def __getitem__(self, k: str) -> _CELLVALUETYPE:
        return self._data.__getitem__(k)

    # Additional methods for LLMFnOutputRowView.
    def __contains__(self, k: str) -> bool:
        return self._data.__contains__(k)

    def __str__(self) -> str:
        return "LLMFnOutputRow: {}".format(self._data.__str__())

    def result_type(self) -> type[Any]:
        return self._result_type

    def result_value(self) -> Any:
        return self._data[self.result_key()]

    def result_key(self) -> str:
        # Our invariant is that the result-cell is always the rightmost cell.
        return list(self._data.keys())[-1]

    # Mutable methods.
    def set_result_value(self, value: Any, key: str | None = None) -> None:
        """Set the value of the result cell.

        Sets the value (and optionally the key) of the result cell.

        Args:
          value: The value to set the result cell today.
          key: Optionally change the key as well.
        """
        _validate_is_result_type(value, self._result_type)

        current_key = self.result_key()
        if key is None or key == current_key:
            self._data[current_key] = value
            return

        del self._data[current_key]
        self._data[key] = value

    def add(self, key: str, value: _CELLVALUETYPE) -> None:
        """Add a non-result cell.

        Adds a new non-result cell. This does not affect the result cell.

        Args:
          key: The key of the new cell to add.
          value: The value of the new cell to add.
        """
        # Handle collisions with `key`.
        if key in self._data:
            idx = 1
            candidate_key = key
            while candidate_key in self._data:
                candidate_key = "{}_{}".format(key, idx)
                idx = idx + 1
            key = candidate_key

        # Insert the new key/value into the second rightmost position to keep
        # the result cell as the rightmost cell.
        result_key = self.result_key()
        result_value = self._data.pop(result_key)
        self._data[key] = value
        self._data[result_key] = result_value

# === NexusCore/openenv\Lib\site-packages\litellm\main.py ===
# +-----------------------------------------------+
# |                                               |
# |           Give Feedback / Get Help            |
# | https://github.com/BerriAI/litellm/issues/new |
# |                                               |
# +-----------------------------------------------+
#
#  Thank you ! We ❤️ you! - Krrish & Ishaan

import asyncio
import contextvars
import datetime
import inspect
import json
import os
import random
import sys
import time
import traceback
import uuid
from concurrent import futures
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from copy import deepcopy
from functools import partial
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Type,
    Union,
    cast,
    get_args,
)

import dotenv
import httpx
import openai
import tiktoken
from pydantic import BaseModel
from typing_extensions import overload

import litellm
from litellm import (  # type: ignore
    Logging,
    client,
    exception_type,
    get_litellm_params,
    get_optional_params,
)
from litellm.constants import (
    DEFAULT_MOCK_RESPONSE_COMPLETION_TOKEN_COUNT,
    DEFAULT_MOCK_RESPONSE_PROMPT_TOKEN_COUNT,
)
from litellm.exceptions import LiteLLMUnknownProvider
from litellm.integrations.custom_logger import CustomLogger
from litellm.litellm_core_utils.audio_utils.utils import get_audio_file_for_health_check
from litellm.litellm_core_utils.dd_tracing import tracer
from litellm.litellm_core_utils.health_check_utils import (
    _create_health_check_response,
    _filter_model_params,
)
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.litellm_core_utils.llm_request_utils import (
    pick_cheapest_chat_models_from_llm_provider,
)
from litellm.litellm_core_utils.mock_functions import (
    mock_embedding,
    mock_image_generation,
)
from litellm.litellm_core_utils.prompt_templates.common_utils import (
    get_content_from_model_response,
)
from litellm.llms.base_llm import BaseConfig, BaseImageGenerationConfig
from litellm.llms.bedrock.common_utils import BedrockModelInfo
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler, HTTPHandler
from litellm.realtime_api.main import _realtime_health_check
from litellm.secret_managers.main import get_secret_str
from litellm.types.router import GenericLiteLLMParams
from litellm.types.utils import RawRequestTypedDict
from litellm.utils import (
    CustomStreamWrapper,
    ProviderConfigManager,
    Usage,
    _get_model_info_helper,
    add_openai_metadata,
    add_provider_specific_params_to_optional_params,
    async_mock_completion_streaming_obj,
    convert_to_model_response_object,
    create_pretrained_tokenizer,
    create_tokenizer,
    get_api_key,
    get_llm_provider,
    get_non_default_completion_params,
    get_non_default_transcription_params,
    get_optional_params_embeddings,
    get_optional_params_image_gen,
    get_optional_params_transcription,
    get_secret,
    get_standard_openai_params,
    mock_completion_streaming_obj,
    pre_process_non_default_params,
    read_config_args,
    supports_httpx_timeout,
    token_counter,
    validate_and_fix_openai_messages,
    validate_chat_completion_tool_choice,
)

from ._logging import verbose_logger
from .caching.caching import disable_cache, enable_cache, update_cache
from .litellm_core_utils.fallback_utils import (
    async_completion_with_fallbacks,
    completion_with_fallbacks,
)
from .litellm_core_utils.prompt_templates.common_utils import (
    get_completion_messages,
    update_messages_with_model_file_ids,
)
from .litellm_core_utils.prompt_templates.factory import (
    custom_prompt,
    function_call_prompt,
    map_system_message_pt,
    ollama_pt,
    prompt_factory,
    stringify_json_tool_call_content,
)
from .litellm_core_utils.streaming_chunk_builder_utils import ChunkProcessor
from .llms import baseten
from .llms.anthropic.chat import AnthropicChatCompletion
from .llms.azure.audio_transcriptions import AzureAudioTranscription
from .llms.azure.azure import AzureChatCompletion, _check_dynamic_azure_params
from .llms.azure.chat.o_series_handler import AzureOpenAIO1ChatCompletion
from .llms.azure.completion.handler import AzureTextCompletion
from .llms.azure_ai.embed import AzureAIEmbedding
from .llms.bedrock.chat import BedrockConverseLLM, BedrockLLM
from .llms.bedrock.embed.embedding import BedrockEmbedding
from .llms.bedrock.image.image_handler import BedrockImageGeneration
from .llms.codestral.completion.handler import CodestralTextCompletion
from .llms.cohere.embed import handler as cohere_embed
from .llms.custom_httpx.aiohttp_handler import BaseLLMAIOHTTPHandler
from .llms.custom_httpx.llm_http_handler import BaseLLMHTTPHandler
from .llms.custom_llm import CustomLLM, custom_chat_llm_router
from .llms.databricks.embed.handler import DatabricksEmbeddingHandler
from .llms.deprecated_providers import aleph_alpha, palm
from .llms.groq.chat.handler import GroqChatCompletion
from .llms.huggingface.embedding.handler import HuggingFaceEmbedding
from .llms.nlp_cloud.chat.handler import completion as nlp_cloud_chat_completion
from .llms.ollama.completion import handler as ollama
from .llms.oobabooga.chat import oobabooga
from .llms.openai.completion.handler import OpenAITextCompletion
from .llms.openai.image_variations.handler import OpenAIImageVariationsHandler
from .llms.openai.openai import OpenAIChatCompletion
from .llms.openai.transcriptions.handler import OpenAIAudioTranscription
from .llms.openai_like.chat.handler import OpenAILikeChatHandler
from .llms.openai_like.embedding.handler import OpenAILikeEmbeddingHandler
from .llms.petals.completion import handler as petals_handler
from .llms.predibase.chat.handler import PredibaseChatCompletion
from .llms.replicate.chat.handler import completion as replicate_chat_completion
from .llms.sagemaker.chat.handler import SagemakerChatHandler
from .llms.sagemaker.completion.handler import SagemakerLLM
from .llms.vertex_ai import vertex_ai_non_gemini
from .llms.vertex_ai.gemini.vertex_and_google_ai_studio_gemini import VertexLLM
from .llms.vertex_ai.gemini_embeddings.batch_embed_content_handler import (
    GoogleBatchEmbeddings,
)
from .llms.vertex_ai.image_generation.image_generation_handler import (
    VertexImageGeneration,
)
from .llms.vertex_ai.multimodal_embeddings.embedding_handler import (
    VertexMultimodalEmbedding,
)
from .llms.vertex_ai.text_to_speech.text_to_speech_handler import VertexTextToSpeechAPI
from .llms.vertex_ai.vertex_ai_partner_models.main import VertexAIPartnerModels
from .llms.vertex_ai.vertex_embeddings.embedding_handler import VertexEmbedding
from .llms.vertex_ai.vertex_model_garden.main import VertexAIModelGardenModels
from .llms.vllm.completion import handler as vllm_handler
from .llms.watsonx.chat.handler import WatsonXChatHandler
from .llms.watsonx.common_utils import IBMWatsonXMixin
from .types.llms.anthropic import AnthropicThinkingParam
from .types.llms.openai import (
    ChatCompletionAssistantMessage,
    ChatCompletionAudioParam,
    ChatCompletionModality,
    ChatCompletionPredictionContentParam,
    ChatCompletionUserMessage,
    HttpxBinaryResponseContent,
    OpenAIModerationResponse,
    OpenAIWebSearchOptions,
)
from .types.utils import (
    AdapterCompletionStreamWrapper,
    ChatCompletionMessageToolCall,
    CompletionTokensDetails,
    FileTypes,
    HiddenParams,
    LlmProviders,
    PromptTokensDetails,
    ProviderSpecificHeader,
    all_litellm_params,
)

encoding = tiktoken.get_encoding("cl100k_base")
from litellm.utils import (
    Choices,
    EmbeddingResponse,
    Message,
    ModelResponse,
    TextChoices,
    TextCompletionResponse,
    TextCompletionStreamWrapper,
    TranscriptionResponse,
)

####### ENVIRONMENT VARIABLES ###################
openai_chat_completions = OpenAIChatCompletion()
openai_text_completions = OpenAITextCompletion()
openai_audio_transcriptions = OpenAIAudioTranscription()
openai_image_variations = OpenAIImageVariationsHandler()
groq_chat_completions = GroqChatCompletion()
azure_ai_embedding = AzureAIEmbedding()
anthropic_chat_completions = AnthropicChatCompletion()
azure_chat_completions = AzureChatCompletion()
azure_o1_chat_completions = AzureOpenAIO1ChatCompletion()
azure_text_completions = AzureTextCompletion()
azure_audio_transcriptions = AzureAudioTranscription()
huggingface_embed = HuggingFaceEmbedding()
predibase_chat_completions = PredibaseChatCompletion()
codestral_text_completions = CodestralTextCompletion()
bedrock_converse_chat_completion = BedrockConverseLLM()
bedrock_embedding = BedrockEmbedding()
bedrock_image_generation = BedrockImageGeneration()
vertex_chat_completion = VertexLLM()
vertex_embedding = VertexEmbedding()
vertex_multimodal_embedding = VertexMultimodalEmbedding()
vertex_image_generation = VertexImageGeneration()
google_batch_embeddings = GoogleBatchEmbeddings()
vertex_partner_models_chat_completion = VertexAIPartnerModels()
vertex_model_garden_chat_completion = VertexAIModelGardenModels()
vertex_text_to_speech = VertexTextToSpeechAPI()
sagemaker_llm = SagemakerLLM()
watsonx_chat_completion = WatsonXChatHandler()
openai_like_embedding = OpenAILikeEmbeddingHandler()
openai_like_chat_completion = OpenAILikeChatHandler()
databricks_embedding = DatabricksEmbeddingHandler()
base_llm_http_handler = BaseLLMHTTPHandler()
base_llm_aiohttp_handler = BaseLLMAIOHTTPHandler()
sagemaker_chat_completion = SagemakerChatHandler()
####### COMPLETION ENDPOINTS ################


class LiteLLM:
    def __init__(
        self,
        *,
        api_key=None,
        organization: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = 600,
        max_retries: Optional[int] = litellm.num_retries,
        default_headers: Optional[Mapping[str, str]] = None,
    ):
        self.params = locals()
        self.chat = Chat(self.params, router_obj=None)


class Chat:
    def __init__(self, params, router_obj: Optional[Any]):
        self.params = params
        if self.params.get("acompletion", False) is True:
            self.params.pop("acompletion")
            self.completions: Union[AsyncCompletions, Completions] = AsyncCompletions(
                self.params, router_obj=router_obj
            )
        else:
            self.completions = Completions(self.params, router_obj=router_obj)


class Completions:
    def __init__(self, params, router_obj: Optional[Any]):
        self.params = params
        self.router_obj = router_obj

    def create(self, messages, model=None, **kwargs):
        for k, v in kwargs.items():
            self.params[k] = v
        model = model or self.params.get("model")
        if self.router_obj is not None:
            response = self.router_obj.completion(
                model=model, messages=messages, **self.params
            )
        else:
            response = completion(model=model, messages=messages, **self.params)
        return response


class AsyncCompletions:
    def __init__(self, params, router_obj: Optional[Any]):
        self.params = params
        self.router_obj = router_obj

    async def create(self, messages, model=None, **kwargs):
        for k, v in kwargs.items():
            self.params[k] = v
        model = model or self.params.get("model")
        if self.router_obj is not None:
            response = await self.router_obj.acompletion(
                model=model, messages=messages, **self.params
            )
        else:
            response = await acompletion(model=model, messages=messages, **self.params)
        return response


@tracer.wrap()
@client
async def acompletion(
    model: str,
    # Optional OpenAI params: see https://platform.openai.com/docs/api-reference/chat/create
    messages: List = [],
    functions: Optional[List] = None,
    function_call: Optional[str] = None,
    timeout: Optional[Union[float, int]] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    n: Optional[int] = None,
    stream: Optional[bool] = None,
    stream_options: Optional[dict] = None,
    stop=None,
    max_tokens: Optional[int] = None,
    max_completion_tokens: Optional[int] = None,
    modalities: Optional[List[ChatCompletionModality]] = None,
    prediction: Optional[ChatCompletionPredictionContentParam] = None,
    audio: Optional[ChatCompletionAudioParam] = None,
    presence_penalty: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    logit_bias: Optional[dict] = None,
    user: Optional[str] = None,
    # openai v1.0+ new params
    response_format: Optional[Union[dict, Type[BaseModel]]] = None,
    seed: Optional[int] = None,
    tools: Optional[List] = None,
    tool_choice: Optional[Union[str, dict]] = None,
    parallel_tool_calls: Optional[bool] = None,
    logprobs: Optional[bool] = None,
    top_logprobs: Optional[int] = None,
    deployment_id=None,
    reasoning_effort: Optional[Literal["low", "medium", "high"]] = None,
    # set api_base, api_version, api_key
    base_url: Optional[str] = None,
    api_version: Optional[str] = None,
    api_key: Optional[str] = None,
    model_list: Optional[list] = None,  # pass in a list of api_base,keys, etc.
    extra_headers: Optional[dict] = None,
    # Optional liteLLM function params
    thinking: Optional[AnthropicThinkingParam] = None,
    web_search_options: Optional[OpenAIWebSearchOptions] = None,
    **kwargs,
) -> Union[ModelResponse, CustomStreamWrapper]:
    """
    Asynchronously executes a litellm.completion() call for any of litellm supported llms (example gpt-4, gpt-3.5-turbo, claude-2, command-nightly)

    Parameters:
        model (str): The name of the language model to use for text completion. see all supported LLMs: https://docs.litellm.ai/docs/providers/
        messages (List): A list of message objects representing the conversation context (default is an empty list).

        OPTIONAL PARAMS
        functions (List, optional): A list of functions to apply to the conversation messages (default is an empty list).
        function_call (str, optional): The name of the function to call within the conversation (default is an empty string).
        temperature (float, optional): The temperature parameter for controlling the randomness of the output (default is 1.0).
        top_p (float, optional): The top-p parameter for nucleus sampling (default is 1.0).
        n (int, optional): The number of completions to generate (default is 1).
        stream (bool, optional): If True, return a streaming response (default is False).
        stream_options (dict, optional): A dictionary containing options for the streaming response. Only use this if stream is True.
        stop(string/list, optional): - Up to 4 sequences where the LLM API will stop generating further tokens.
        max_tokens (integer, optional): The maximum number of tokens in the generated completion (default is infinity).
        max_completion_tokens (integer, optional): An upper bound for the number of tokens that can be generated for a completion, including visible output tokens and reasoning tokens.
        modalities (List[ChatCompletionModality], optional): Output types that you would like the model to generate for this request. You can use `["text", "audio"]`
        prediction (ChatCompletionPredictionContentParam, optional): Configuration for a Predicted Output, which can greatly improve response times when large parts of the model response are known ahead of time. This is most common when you are regenerating a file with only minor changes to most of the content.
        audio (ChatCompletionAudioParam, optional): Parameters for audio output. Required when audio output is requested with modalities: ["audio"]
        presence_penalty (float, optional): It is used to penalize new tokens based on their existence in the text so far.
        frequency_penalty: It is used to penalize new tokens based on their frequency in the text so far.
        logit_bias (dict, optional): Used to modify the probability of specific tokens appearing in the completion.
        user (str, optional):  A unique identifier representing your end-user. This can help the LLM provider to monitor and detect abuse.
        metadata (dict, optional): Pass in additional metadata to tag your completion calls - eg. prompt version, details, etc.
        api_base (str, optional): Base URL for the API (default is None).
        api_version (str, optional): API version (default is None).
        api_key (str, optional): API key (default is None).
        model_list (list, optional): List of api base, version, keys
        timeout (float, optional): The maximum execution time in seconds for the completion request.

        LITELLM Specific Params
        mock_response (str, optional): If provided, return a mock completion response for testing or debugging purposes (default is None).
        custom_llm_provider (str, optional): Used for Non-OpenAI LLMs, Example usage for bedrock, set model="amazon.titan-tg1-large" and custom_llm_provider="bedrock"
    Returns:
        ModelResponse: A response object containing the generated completion and associated metadata.

    Notes:
        - This function is an asynchronous version of the `completion` function.
        - The `completion` function is called using `run_in_executor` to execute synchronously in the event loop.
        - If `stream` is True, the function returns an async generator that yields completion lines.
    """
    fallbacks = kwargs.get("fallbacks", None)
    mock_timeout = kwargs.get("mock_timeout", None)

    if mock_timeout is True:
        await _handle_mock_timeout_async(mock_timeout, timeout, model)

    loop = asyncio.get_event_loop()
    custom_llm_provider = kwargs.get("custom_llm_provider", None)

    ## PROMPT MANAGEMENT HOOKS ##
    #########################################################
    #########################################################
    litellm_logging_obj = kwargs.get("litellm_logging_obj", None)
    if isinstance(litellm_logging_obj, LiteLLMLoggingObj) and (
        litellm_logging_obj.should_run_prompt_management_hooks(
            prompt_id=kwargs.get("prompt_id", None),
            non_default_params=kwargs,
            tools=tools,
        )
    ):
        (
            model,
            messages,
            _,
        ) = await litellm_logging_obj.async_get_chat_completion_prompt(
            model=model,
            messages=messages,
            non_default_params=kwargs,
            prompt_id=kwargs.get("prompt_id", None),
            prompt_variables=kwargs.get("prompt_variables", None),
            tools=tools,
            prompt_label=kwargs.get("prompt_label", None),
        )
        #########################################################
        # if the chat completion logging hook removed all tools,
        # set tools to None
        # eg. in certain cases when users send vector stores as tools
        # we don't want the tools to go to the upstream llm
        # relevant issue: https://github.com/BerriAI/litellm/issues/11404
        #########################################################
        if tools is not None and len(tools) == 0:
            tools = None

    #########################################################
    #########################################################

    # Adjusted to use explicit arguments instead of *args and **kwargs
    completion_kwargs = {
        "model": model,
        "messages": messages,
        "functions": functions,
        "function_call": function_call,
        "timeout": timeout,
        "temperature": temperature,
        "top_p": top_p,
        "n": n,
        "stream": stream,
        "stream_options": stream_options,
        "stop": stop,
        "max_tokens": max_tokens,
        "max_completion_tokens": max_completion_tokens,
        "modalities": modalities,
        "prediction": prediction,
        "audio": audio,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "logit_bias": logit_bias,
        "user": user,
        "response_format": response_format,
        "seed": seed,
        "tools": tools,
        "tool_choice": tool_choice,
        "parallel_tool_calls": parallel_tool_calls,
        "logprobs": logprobs,
        "top_logprobs": top_logprobs,
        "deployment_id": deployment_id,
        "base_url": base_url,
        "api_version": api_version,
        "api_key": api_key,
        "model_list": model_list,
        "reasoning_effort": reasoning_effort,
        "extra_headers": extra_headers,
        "acompletion": True,  # assuming this is a required parameter
        "thinking": thinking,
        "web_search_options": web_search_options,
    }
    if custom_llm_provider is None:
        _, custom_llm_provider, _, _ = get_llm_provider(
            model=model, api_base=completion_kwargs.get("base_url", None)
        )

    fallbacks = fallbacks or litellm.model_fallbacks
    if fallbacks is not None:
        response = await async_completion_with_fallbacks(
            **completion_kwargs, kwargs={"fallbacks": fallbacks, **kwargs}
        )
        if response is None:
            raise Exception(
                "No response from fallbacks. Got none. Turn on `litellm.set_verbose=True` to see more details."
            )
        return response

    try:
        # Use a partial function to pass your keyword arguments
        func = partial(completion, **completion_kwargs, **kwargs)

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        init_response = await loop.run_in_executor(None, func_with_context)
        if isinstance(init_response, dict) or isinstance(
            init_response, ModelResponse
        ):  ## CACHING SCENARIO
            if isinstance(init_response, dict):
                response = ModelResponse(**init_response)
            response = init_response
        elif asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response  # type: ignore

        if (
            custom_llm_provider == "text-completion-openai"
            or custom_llm_provider == "text-completion-codestral"
        ) and isinstance(response, TextCompletionResponse):
            response = litellm.OpenAITextCompletionConfig().convert_to_chat_model_response_object(
                response_object=response,
                model_response_object=litellm.ModelResponse(),
            )
        if isinstance(response, CustomStreamWrapper):
            response.set_logging_event_loop(
                loop=loop
            )  # sets the logging event loop if the user does sync streaming (e.g. on proxy for sagemaker calls)
        return response
    except Exception as e:
        custom_llm_provider = custom_llm_provider or "openai"
        raise exception_type(
            model=model,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=completion_kwargs,
            extra_kwargs=kwargs,
        )


async def _async_streaming(response, model, custom_llm_provider, args):
    try:
        print_verbose(f"received response in _async_streaming: {response}")
        if asyncio.iscoroutine(response):
            response = await response
        async for line in response:
            print_verbose(f"line in async streaming: {line}")
            yield line
    except Exception as e:
        custom_llm_provider = custom_llm_provider or "openai"
        raise exception_type(
            model=model,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
        )


def _handle_mock_potential_exceptions(
    mock_response: Union[str, Exception, dict],
    model: str,
    custom_llm_provider: Optional[str] = None,
):
    if isinstance(mock_response, Exception):
        if isinstance(mock_response, openai.APIError):
            raise mock_response
        raise litellm.MockException(
            status_code=getattr(mock_response, "status_code", 500),  # type: ignore
            message=getattr(mock_response, "text", str(mock_response)),
            llm_provider=getattr(
                mock_response, "llm_provider", custom_llm_provider or "openai"
            ),  # type: ignore
            model=model,  # type: ignore
            request=httpx.Request(method="POST", url="https://api.openai.com/v1/"),
        )
    elif isinstance(mock_response, str) and mock_response == "litellm.RateLimitError":
        raise litellm.RateLimitError(
            message="this is a mock rate limit error",
            llm_provider=getattr(
                mock_response, "llm_provider", custom_llm_provider or "openai"
            ),  # type: ignore
            model=model,
        )
    elif (
        isinstance(mock_response, str)
        and mock_response == "litellm.ContextWindowExceededError"
    ):
        raise litellm.ContextWindowExceededError(
            message="this is a mock context window exceeded error",
            llm_provider=getattr(
                mock_response, "llm_provider", custom_llm_provider or "openai"
            ),  # type: ignore
            model=model,
        )
    elif (
        isinstance(mock_response, str)
        and mock_response == "litellm.InternalServerError"
    ):
        raise litellm.InternalServerError(
            message="this is a mock internal server error",
            llm_provider=getattr(
                mock_response, "llm_provider", custom_llm_provider or "openai"
            ),  # type: ignore
            model=model,
        )
    elif isinstance(mock_response, str) and mock_response.startswith(
        "Exception: content_filter_policy"
    ):
        raise litellm.MockException(
            status_code=400,
            message=mock_response,
            llm_provider="azure",
            model=model,  # type: ignore
            request=httpx.Request(method="POST", url="https://api.openai.com/v1/"),
        )


def _handle_mock_timeout(
    mock_timeout: Optional[bool],
    timeout: Optional[Union[float, str, httpx.Timeout]],
    model: str,
):
    if mock_timeout is True and timeout is not None:
        _sleep_for_timeout(timeout)
        raise litellm.Timeout(
            message="This is a mock timeout error",
            llm_provider="openai",
            model=model,
        )


async def _handle_mock_timeout_async(
    mock_timeout: Optional[bool],
    timeout: Optional[Union[float, str, httpx.Timeout]],
    model: str,
):
    if mock_timeout is True and timeout is not None:
        await _sleep_for_timeout_async(timeout)
        raise litellm.Timeout(
            message="This is a mock timeout error",
            llm_provider="openai",
            model=model,
        )


def _sleep_for_timeout(timeout: Union[float, str, httpx.Timeout]):
    if isinstance(timeout, float):
        time.sleep(timeout)
    elif isinstance(timeout, str):
        time.sleep(float(timeout))
    elif isinstance(timeout, httpx.Timeout) and timeout.connect is not None:
        time.sleep(timeout.connect)


async def _sleep_for_timeout_async(timeout: Union[float, str, httpx.Timeout]):
    if isinstance(timeout, float):
        await asyncio.sleep(timeout)
    elif isinstance(timeout, str):
        await asyncio.sleep(float(timeout))
    elif isinstance(timeout, httpx.Timeout) and timeout.connect is not None:
        await asyncio.sleep(timeout.connect)


def mock_completion(
    model: str,
    messages: List,
    stream: Optional[bool] = False,
    n: Optional[int] = None,
    mock_response: Union[str, Exception, dict] = "This is a mock request",
    mock_tool_calls: Optional[List] = None,
    mock_timeout: Optional[bool] = False,
    logging=None,
    custom_llm_provider=None,
    timeout: Optional[Union[float, str, httpx.Timeout]] = None,
    **kwargs,
):
    """
    Generate a mock completion response for testing or debugging purposes.

    This is a helper function that simulates the response structure of the OpenAI completion API.

    Parameters:
        model (str): The name of the language model for which the mock response is generated.
        messages (List): A list of message objects representing the conversation context.
        stream (bool, optional): If True, returns a mock streaming response (default is False).
        mock_response (str, optional): The content of the mock response (default is "This is a mock request").
        mock_timeout (bool, optional): If True, the mock response will be a timeout error (default is False).
        timeout (float, optional): The timeout value to use for the mock response (default is None).
        **kwargs: Additional keyword arguments that can be used but are not required.

    Returns:
        litellm.ModelResponse: A ModelResponse simulating a completion response with the specified model, messages, and mock response.

    Raises:
        Exception: If an error occurs during the generation of the mock completion response.
    Note:
        - This function is intended for testing or debugging purposes to generate mock completion responses.
        - If 'stream' is True, it returns a response that mimics the behavior of a streaming completion.
    """
    try:
        if mock_response is None:
            mock_response = "This is a mock request"

        _handle_mock_timeout(mock_timeout=mock_timeout, timeout=timeout, model=model)

        ## LOGGING
        if logging is not None:
            logging.pre_call(
                input=messages,
                api_key="mock-key",
            )

        _handle_mock_potential_exceptions(
            mock_response=mock_response,
            model=model,
            custom_llm_provider=custom_llm_provider,
        )

        mock_response = cast(
            Union[str, dict], mock_response
        )  # after this point, mock_response is a string or dict
        if isinstance(mock_response, str) and mock_response.startswith(
            "Exception: mock_streaming_error"
        ):
            mock_response = litellm.MockException(
                message="This is a mock error raised mid-stream",
                llm_provider="anthropic",
                model=model,
                status_code=529,
            )
        time_delay = kwargs.get("mock_delay", None)
        if time_delay is not None:
            time.sleep(time_delay)

        if isinstance(mock_response, dict):
            return ModelResponse(**mock_response)

        model_response = ModelResponse(stream=stream)
        if stream is True:
            # don't try to access stream object,
            if kwargs.get("acompletion", False) is True:
                return CustomStreamWrapper(
                    completion_stream=async_mock_completion_streaming_obj(
                        model_response, mock_response=mock_response, model=model, n=n
                    ),
                    model=model,
                    custom_llm_provider="openai",
                    logging_obj=logging,
                )
            return CustomStreamWrapper(
                completion_stream=mock_completion_streaming_obj(
                    model_response, mock_response=mock_response, model=model, n=n
                ),
                model=model,
                custom_llm_provider="openai",
                logging_obj=logging,
            )
        if isinstance(mock_response, litellm.MockException):
            raise mock_response
        if n is None:
            model_response.choices[0].message.content = mock_response  # type: ignore
        else:
            _all_choices = []
            for i in range(n):
                _choice = litellm.utils.Choices(
                    index=i,
                    message=litellm.utils.Message(
                        content=mock_response, role="assistant"
                    ),
                )
                _all_choices.append(_choice)
            model_response.choices = _all_choices  # type: ignore
        model_response.created = int(time.time())
        model_response.model = model

        if mock_tool_calls:
            model_response.choices[0].message.tool_calls = [  # type: ignore
                ChatCompletionMessageToolCall(**tool_call)
                for tool_call in mock_tool_calls
            ]

        setattr(
            model_response,
            "usage",
            Usage(
                prompt_tokens=DEFAULT_MOCK_RESPONSE_PROMPT_TOKEN_COUNT,
                completion_tokens=DEFAULT_MOCK_RESPONSE_COMPLETION_TOKEN_COUNT,
                total_tokens=DEFAULT_MOCK_RESPONSE_PROMPT_TOKEN_COUNT
                + DEFAULT_MOCK_RESPONSE_COMPLETION_TOKEN_COUNT,
            ),
        )

        try:
            _, custom_llm_provider, _, _ = litellm.utils.get_llm_provider(model=model)
            model_response._hidden_params["custom_llm_provider"] = custom_llm_provider
        except Exception:
            # dont let setting a hidden param block a mock_respose
            pass

        if logging is not None:
            logging.post_call(
                input=messages,
                api_key="my-secret-key",
                original_response="my-original-response",
            )
        return model_response

    except Exception as e:
        if isinstance(e, openai.APIError):
            raise e
        raise Exception("Mock completion response failed - {}".format(e))


@tracer.wrap()
@client
def completion(  # type: ignore # noqa: PLR0915
    model: str,
    # Optional OpenAI params: see https://platform.openai.com/docs/api-reference/chat/create
    messages: List = [],
    timeout: Optional[Union[float, str, httpx.Timeout]] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    n: Optional[int] = None,
    stream: Optional[bool] = None,
    stream_options: Optional[dict] = None,
    stop=None,
    max_completion_tokens: Optional[int] = None,
    max_tokens: Optional[int] = None,
    modalities: Optional[List[ChatCompletionModality]] = None,
    prediction: Optional[ChatCompletionPredictionContentParam] = None,
    audio: Optional[ChatCompletionAudioParam] = None,
    presence_penalty: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    logit_bias: Optional[dict] = None,
    user: Optional[str] = None,
    # openai v1.0+ new params
    reasoning_effort: Optional[Literal["low", "medium", "high"]] = None,
    response_format: Optional[Union[dict, Type[BaseModel]]] = None,
    seed: Optional[int] = None,
    tools: Optional[List] = None,
    tool_choice: Optional[Union[str, dict]] = None,
    logprobs: Optional[bool] = None,
    top_logprobs: Optional[int] = None,
    parallel_tool_calls: Optional[bool] = None,
    web_search_options: Optional[OpenAIWebSearchOptions] = None,
    deployment_id=None,
    extra_headers: Optional[dict] = None,
    # soon to be deprecated params by OpenAI
    functions: Optional[List] = None,
    function_call: Optional[str] = None,
    # set api_base, api_version, api_key
    base_url: Optional[str] = None,
    api_version: Optional[str] = None,
    api_key: Optional[str] = None,
    model_list: Optional[list] = None,  # pass in a list of api_base,keys, etc.
    # Optional liteLLM function params
    thinking: Optional[AnthropicThinkingParam] = None,
    **kwargs,
) -> Union[ModelResponse, CustomStreamWrapper]:
    """
    Perform a completion() using any of litellm supported llms (example gpt-4, gpt-3.5-turbo, claude-2, command-nightly)
    Parameters:
        model (str): The name of the language model to use for text completion. see all supported LLMs: https://docs.litellm.ai/docs/providers/
        messages (List): A list of message objects representing the conversation context (default is an empty list).

        OPTIONAL PARAMS
        functions (List, optional): A list of functions to apply to the conversation messages (default is an empty list).
        function_call (str, optional): The name of the function to call within the conversation (default is an empty string).
        temperature (float, optional): The temperature parameter for controlling the randomness of the output (default is 1.0).
        top_p (float, optional): The top-p parameter for nucleus sampling (default is 1.0).
        n (int, optional): The number of completions to generate (default is 1).
        stream (bool, optional): If True, return a streaming response (default is False).
        stream_options (dict, optional): A dictionary containing options for the streaming response. Only set this when you set stream: true.
        stop(string/list, optional): - Up to 4 sequences where the LLM API will stop generating further tokens.
        max_tokens (integer, optional): The maximum number of tokens in the generated completion (default is infinity).
        max_completion_tokens (integer, optional): An upper bound for the number of tokens that can be generated for a completion, including visible output tokens and reasoning tokens.
        modalities (List[ChatCompletionModality], optional): Output types that you would like the model to generate for this request.. You can use `["text", "audio"]`
        prediction (ChatCompletionPredictionContentParam, optional): Configuration for a Predicted Output, which can greatly improve response times when large parts of the model response are known ahead of time. This is most common when you are regenerating a file with only minor changes to most of the content.
        audio (ChatCompletionAudioParam, optional): Parameters for audio output. Required when audio output is requested with modalities: ["audio"]
        presence_penalty (float, optional): It is used to penalize new tokens based on their existence in the text so far.
        frequency_penalty: It is used to penalize new tokens based on their frequency in the text so far.
        logit_bias (dict, optional): Used to modify the probability of specific tokens appearing in the completion.
        user (str, optional):  A unique identifier representing your end-user. This can help the LLM provider to monitor and detect abuse.
        logprobs (bool, optional): Whether to return log probabilities of the output tokens or not. If true, returns the log probabilities of each output token returned in the content of message
        top_logprobs (int, optional): An integer between 0 and 5 specifying the number of most likely tokens to return at each token position, each with an associated log probability. logprobs must be set to true if this parameter is used.
        metadata (dict, optional): Pass in additional metadata to tag your completion calls - eg. prompt version, details, etc.
        api_base (str, optional): Base URL for the API (default is None).
        api_version (str, optional): API version (default is None).
        api_key (str, optional): API key (default is None).
        model_list (list, optional): List of api base, version, keys
        extra_headers (dict, optional): Additional headers to include in the request.

        LITELLM Specific Params
        mock_response (str, optional): If provided, return a mock completion response for testing or debugging purposes (default is None).
        custom_llm_provider (str, optional): Used for Non-OpenAI LLMs, Example usage for bedrock, set model="amazon.titan-tg1-large" and custom_llm_provider="bedrock"
        max_retries (int, optional): The number of retries to attempt (default is 0).
    Returns:
        ModelResponse: A response object containing the generated completion and associated metadata.

    Note:
        - This function is used to perform completions() using the specified language model.
        - It supports various optional parameters for customizing the completion behavior.
        - If 'mock_response' is provided, a mock completion response is returned for testing or debugging.
    """
    ### VALIDATE Request ###
    if model is None:
        raise ValueError("model param not passed in.")
    # validate messages
    messages = validate_and_fix_openai_messages(messages=messages)
    # validate tool_choice
    tool_choice = validate_chat_completion_tool_choice(tool_choice=tool_choice)
    ######### unpacking kwargs #####################
    args = locals()
    api_base = kwargs.get("api_base", None)
    mock_response = kwargs.get("mock_response", None)
    mock_tool_calls = kwargs.get("mock_tool_calls", None)
    mock_timeout = cast(Optional[bool], kwargs.get("mock_timeout", None))
    force_timeout = kwargs.get("force_timeout", 600)  ## deprecated
    logger_fn = kwargs.get("logger_fn", None)
    verbose = kwargs.get("verbose", False)
    custom_llm_provider = kwargs.get("custom_llm_provider", None)
    litellm_logging_obj = kwargs.get("litellm_logging_obj", None)
    id = kwargs.get("id", None)
    metadata = kwargs.get("metadata", None)
    model_info = kwargs.get("model_info", None)
    proxy_server_request = kwargs.get("proxy_server_request", None)
    fallbacks = kwargs.get("fallbacks", None)
    provider_specific_header = cast(
        Optional[ProviderSpecificHeader], kwargs.get("provider_specific_header", None)
    )
    headers = kwargs.get("headers", None) or extra_headers

    ensure_alternating_roles: Optional[bool] = kwargs.get(
        "ensure_alternating_roles", None
    )
    user_continue_message: Optional[ChatCompletionUserMessage] = kwargs.get(
        "user_continue_message", None
    )
    assistant_continue_message: Optional[ChatCompletionAssistantMessage] = kwargs.get(
        "assistant_continue_message", None
    )
    if headers is None:
        headers = {}
    if extra_headers is not None:
        headers.update(extra_headers)
    num_retries = kwargs.get(
        "num_retries", None
    )  ## alt. param for 'max_retries'. Use this to pass retries w/ instructor.
    max_retries = kwargs.get("max_retries", None)
    cooldown_time = kwargs.get("cooldown_time", None)
    context_window_fallback_dict = kwargs.get("context_window_fallback_dict", None)
    organization = kwargs.get("organization", None)
    ### VERIFY SSL ###
    ssl_verify = kwargs.get("ssl_verify", None)
    ### CUSTOM MODEL COST ###
    input_cost_per_token = kwargs.get("input_cost_per_token", None)
    output_cost_per_token = kwargs.get("output_cost_per_token", None)
    input_cost_per_second = kwargs.get("input_cost_per_second", None)
    output_cost_per_second = kwargs.get("output_cost_per_second", None)
    ### CUSTOM PROMPT TEMPLATE ###
    initial_prompt_value = kwargs.get("initial_prompt_value", None)
    roles = kwargs.get("roles", None)
    final_prompt_value = kwargs.get("final_prompt_value", None)
    bos_token = kwargs.get("bos_token", None)
    eos_token = kwargs.get("eos_token", None)
    preset_cache_key = kwargs.get("preset_cache_key", None)
    hf_model_name = kwargs.get("hf_model_name", None)
    supports_system_message = kwargs.get("supports_system_message", None)
    base_model = kwargs.get("base_model", None)
    ### DISABLE FLAGS ###
    disable_add_transform_inline_image_block = kwargs.get(
        "disable_add_transform_inline_image_block", None
    )
    ### TEXT COMPLETION CALLS ###
    text_completion = kwargs.get("text_completion", False)
    atext_completion = kwargs.get("atext_completion", False)
    ### ASYNC CALLS ###
    acompletion = kwargs.get("acompletion", False)
    client = kwargs.get("client", None)
    ### Admin Controls ###
    no_log = kwargs.get("no-log", False)
    ### PROMPT MANAGEMENT ###
    prompt_id = cast(Optional[str], kwargs.get("prompt_id", None))
    prompt_variables = cast(Optional[dict], kwargs.get("prompt_variables", None))
    ### COPY MESSAGES ### - related issue https://github.com/BerriAI/litellm/discussions/4489
    messages = get_completion_messages(
        messages=messages,
        ensure_alternating_roles=ensure_alternating_roles or False,
        user_continue_message=user_continue_message,
        assistant_continue_message=assistant_continue_message,
    )
    ######## end of unpacking kwargs ###########
    non_default_params = get_non_default_completion_params(kwargs=kwargs)
    litellm_params = {}  # used to prevent unbound var errors
    ## PROMPT MANAGEMENT HOOKS ##
    if isinstance(litellm_logging_obj, LiteLLMLoggingObj) and (
        litellm_logging_obj.should_run_prompt_management_hooks(
            prompt_id=prompt_id, non_default_params=non_default_params
        )
    ):
        (
            model,
            messages,
            optional_params,
        ) = litellm_logging_obj.get_chat_completion_prompt(
            model=model,
            messages=messages,
            non_default_params=non_default_params,
            prompt_id=prompt_id,
            prompt_variables=prompt_variables,
            prompt_label=kwargs.get("prompt_label", None),
        )

    try:
        if base_url is not None:
            api_base = base_url
        if num_retries is not None:
            max_retries = num_retries
        logging = litellm_logging_obj
        fallbacks = fallbacks or litellm.model_fallbacks
        if fallbacks is not None:
            return completion_with_fallbacks(**args)
        if model_list is not None:
            deployments = [
                m["litellm_params"] for m in model_list if m["model_name"] == model
            ]
            return litellm.batch_completion_models(deployments=deployments, **args)
        if litellm.model_alias_map and model in litellm.model_alias_map:
            model = litellm.model_alias_map[
                model
            ]  # update the model to the actual value if an alias has been passed in
        model_response = ModelResponse()
        setattr(model_response, "usage", litellm.Usage())
        if (
            kwargs.get("azure", False) is True
        ):  # don't remove flag check, to remain backwards compatible for repos like Codium
            custom_llm_provider = "azure"
        if deployment_id is not None:  # azure llms
            model = deployment_id
            custom_llm_provider = "azure"
        model, custom_llm_provider, dynamic_api_key, api_base = get_llm_provider(
            model=model,
            custom_llm_provider=custom_llm_provider,
            api_base=api_base,
            api_key=api_key,
        )

        if (
            provider_specific_header is not None
            and provider_specific_header["custom_llm_provider"] == custom_llm_provider
        ):
            headers.update(provider_specific_header["extra_headers"])

        if model_response is not None and hasattr(model_response, "_hidden_params"):
            model_response._hidden_params["custom_llm_provider"] = custom_llm_provider
            model_response._hidden_params["region_name"] = kwargs.get(
                "aws_region_name", None
            )  # support region-based pricing for bedrock

        ### TIMEOUT LOGIC ###
        timeout = timeout or kwargs.get("request_timeout", 600) or 600
        # set timeout for 10 minutes by default
        if isinstance(timeout, httpx.Timeout) and not supports_httpx_timeout(
            custom_llm_provider
        ):
            timeout = timeout.read or 600  # default 10 min timeout
        elif not isinstance(timeout, httpx.Timeout):
            timeout = float(timeout)  # type: ignore

        ### REGISTER CUSTOM MODEL PRICING -- IF GIVEN ###
        if input_cost_per_token is not None and output_cost_per_token is not None:
            litellm.register_model(
                {
                    f"{custom_llm_provider}/{model}": {
                        "input_cost_per_token": input_cost_per_token,
                        "output_cost_per_token": output_cost_per_token,
                        "litellm_provider": custom_llm_provider,
                    }
                }
            )
        elif (
            input_cost_per_second is not None
        ):  # time based pricing just needs cost in place
            output_cost_per_second = output_cost_per_second
            litellm.register_model(
                {
                    f"{custom_llm_provider}/{model}": {
                        "input_cost_per_second": input_cost_per_second,
                        "output_cost_per_second": output_cost_per_second,
                        "litellm_provider": custom_llm_provider,
                    }
                }
            )
        ### BUILD CUSTOM PROMPT TEMPLATE -- IF GIVEN ###
        custom_prompt_dict = {}  # type: ignore
        if (
            initial_prompt_value
            or roles
            or final_prompt_value
            or bos_token
            or eos_token
        ):
            custom_prompt_dict = {model: {}}
            if initial_prompt_value:
                custom_prompt_dict[model]["initial_prompt_value"] = initial_prompt_value
            if roles:
                custom_prompt_dict[model]["roles"] = roles
            if final_prompt_value:
                custom_prompt_dict[model]["final_prompt_value"] = final_prompt_value
            if bos_token:
                custom_prompt_dict[model]["bos_token"] = bos_token
            if eos_token:
                custom_prompt_dict[model]["eos_token"] = eos_token

        if kwargs.get("model_file_id_mapping"):
            messages = update_messages_with_model_file_ids(
                messages=messages,
                model_id=kwargs.get("model_info", {}).get("id", None),
                model_file_id_mapping=cast(
                    Dict[str, Dict[str, str]], kwargs.get("model_file_id_mapping")
                ),
            )

        provider_config: Optional[BaseConfig] = None
        if custom_llm_provider is not None and custom_llm_provider in [
            provider.value for provider in LlmProviders
        ]:
            provider_config = ProviderConfigManager.get_provider_chat_config(
                model=model, provider=LlmProviders(custom_llm_provider)
            )

        if provider_config is not None:
            messages = provider_config.translate_developer_role_to_system_role(
                messages=messages
            )

        if (
            supports_system_message is not None
            and isinstance(supports_system_message, bool)
            and supports_system_message is False
        ):
            messages = map_system_message_pt(messages=messages)

        if dynamic_api_key is not None:
            api_key = dynamic_api_key
        # check if user passed in any of the OpenAI optional params
        optional_param_args = {
            "functions": functions,
            "function_call": function_call,
            "temperature": temperature,
            "top_p": top_p,
            "n": n,
            "stream": stream,
            "stream_options": stream_options,
            "stop": stop,
            "max_tokens": max_tokens,
            "max_completion_tokens": max_completion_tokens,
            "modalities": modalities,
            "prediction": prediction,
            "audio": audio,
            "presence_penalty": presence_penalty,
            "frequency_penalty": frequency_penalty,
            "logit_bias": logit_bias,
            "user": user,
            # params to identify the model
            "model": model,
            "custom_llm_provider": custom_llm_provider,
            "response_format": response_format,
            "seed": seed,
            "tools": tools,
            "tool_choice": tool_choice,
            "max_retries": max_retries,
            "logprobs": logprobs,
            "top_logprobs": top_logprobs,
            "api_version": api_version,
            "parallel_tool_calls": parallel_tool_calls,
            "messages": messages,
            "reasoning_effort": reasoning_effort,
            "thinking": thinking,
            "web_search_options": web_search_options,
            "allowed_openai_params": kwargs.get("allowed_openai_params"),
        }
        optional_params = get_optional_params(
            **optional_param_args, **non_default_params
        )
        processed_non_default_params = pre_process_non_default_params(
            model=model,
            passed_params=optional_param_args,
            special_params=non_default_params,
            custom_llm_provider=custom_llm_provider,
            additional_drop_params=kwargs.get("additional_drop_params"),
            remove_sensitive_keys=True,
            add_provider_specific_params=True,
        )

        if litellm.add_function_to_prompt and optional_params.get(
            "functions_unsupported_model", None
        ):  # if user opts to add it to prompt, when API doesn't support function calling
            functions_unsupported_model = optional_params.pop(
                "functions_unsupported_model"
            )
            messages = function_call_prompt(
                messages=messages, functions=functions_unsupported_model
            )

        # For logging - save the values of the litellm-specific params passed in
        litellm_params = get_litellm_params(
            acompletion=acompletion,
            api_key=api_key,
            force_timeout=force_timeout,
            logger_fn=logger_fn,
            verbose=verbose,
            custom_llm_provider=custom_llm_provider,
            api_base=api_base,
            litellm_call_id=kwargs.get("litellm_call_id", None),
            model_alias_map=litellm.model_alias_map,
            completion_call_id=id,
            metadata=metadata,
            model_info=model_info,
            proxy_server_request=proxy_server_request,
            preset_cache_key=preset_cache_key,
            no_log=no_log,
            input_cost_per_second=input_cost_per_second,
            input_cost_per_token=input_cost_per_token,
            output_cost_per_second=output_cost_per_second,
            output_cost_per_token=output_cost_per_token,
            cooldown_time=cooldown_time,
            text_completion=kwargs.get("text_completion"),
            azure_ad_token_provider=kwargs.get("azure_ad_token_provider"),
            user_continue_message=kwargs.get("user_continue_message"),
            base_model=base_model,
            litellm_trace_id=kwargs.get("litellm_trace_id"),
            litellm_session_id=kwargs.get("litellm_session_id"),
            hf_model_name=hf_model_name,
            custom_prompt_dict=custom_prompt_dict,
            litellm_metadata=kwargs.get("litellm_metadata"),
            disable_add_transform_inline_image_block=disable_add_transform_inline_image_block,
            drop_params=kwargs.get("drop_params"),
            prompt_id=prompt_id,
            prompt_variables=prompt_variables,
            ssl_verify=ssl_verify,
            merge_reasoning_content_in_choices=kwargs.get(
                "merge_reasoning_content_in_choices", None
            ),
            use_litellm_proxy=kwargs.get("use_litellm_proxy", False),
            api_version=api_version,
            azure_ad_token=kwargs.get("azure_ad_token"),
            tenant_id=kwargs.get("tenant_id"),
            client_id=kwargs.get("client_id"),
            client_secret=kwargs.get("client_secret"),
            azure_username=kwargs.get("azure_username"),
            azure_password=kwargs.get("azure_password"),
            azure_scope=kwargs.get("azure_scope"),
            max_retries=max_retries,
            timeout=timeout,
        )
        cast(LiteLLMLoggingObj, logging).update_environment_variables(
            model=model,
            user=user,
            optional_params=processed_non_default_params,  # [IMPORTANT] - using processed_non_default_params ensures consistent params logged to langfuse for finetuning / eval datasets.
            litellm_params=litellm_params,
            custom_llm_provider=custom_llm_provider,
        )
        if mock_response or mock_tool_calls or mock_timeout:
            kwargs.pop("mock_timeout", None)  # remove for any fallbacks triggered
            return mock_completion(
                model,
                messages,
                stream=stream,
                n=n,
                mock_response=mock_response,
                mock_tool_calls=mock_tool_calls,
                logging=logging,
                acompletion=acompletion,
                mock_delay=kwargs.get("mock_delay", None),
                custom_llm_provider=custom_llm_provider,
                mock_timeout=mock_timeout,
                timeout=timeout,
            )

        ## RESPONSES API BRIDGE LOGIC ## - check if model has 'mode: responses' in litellm.model_cost map
        try:
            model_info = _get_model_info_helper(
                model=model, custom_llm_provider=custom_llm_provider
            )
        except Exception as e:
            verbose_logger.debug("Error getting model info: {}".format(e))
            model_info = {}

        if model_info.get("mode") == "responses":
            from litellm.completion_extras import responses_api_bridge

            return responses_api_bridge.completion(
                model=model,
                messages=messages,
                headers=headers,
                model_response=model_response,
                api_key=api_key,
                api_base=api_base,
                acompletion=acompletion,
                logging_obj=logging,
                optional_params=optional_params,
                litellm_params=litellm_params,
                timeout=timeout,  # type: ignore
                client=client,  # pass AsyncOpenAI, OpenAI client
                custom_llm_provider=custom_llm_provider,
                encoding=encoding,
                stream=stream,
            )

        if custom_llm_provider == "azure":
            # azure configs
            ## check dynamic params ##
            dynamic_params = False
            if client is not None and (
                isinstance(client, openai.AzureOpenAI)
                or isinstance(client, openai.AsyncAzureOpenAI)
            ):
                dynamic_params = _check_dynamic_azure_params(
                    azure_client_params={"api_version": api_version},
                    azure_client=client,
                )

            api_type = get_secret("AZURE_API_TYPE") or "azure"

            api_base = api_base or litellm.api_base or get_secret("AZURE_API_BASE")

            api_version = (
                api_version
                or litellm.api_version
                or get_secret("AZURE_API_VERSION")
                or litellm.AZURE_DEFAULT_API_VERSION
            )

            api_key = (
                api_key
                or litellm.api_key
                or litellm.azure_key
                or get_secret("AZURE_OPENAI_API_KEY")
                or get_secret("AZURE_API_KEY")
            )

            azure_ad_token = optional_params.get("extra_body", {}).pop(
                "azure_ad_token", None
            ) or get_secret("AZURE_AD_TOKEN")

            azure_ad_token_provider = litellm_params.get(
                "azure_ad_token_provider", None
            )

            headers = headers or litellm.headers

            if extra_headers is not None:
                optional_params["extra_headers"] = extra_headers
            if max_retries is not None:
                optional_params["max_retries"] = max_retries

            if litellm.AzureOpenAIO1Config().is_o_series_model(model=model):
                ## LOAD CONFIG - if set
                config = litellm.AzureOpenAIO1Config.get_config()
                for k, v in config.items():
                    if (
                        k not in optional_params
                    ):  # completion(top_k=3) > azure_config(top_k=3) <- allows for dynamic variables to be passed in
                        optional_params[k] = v

                response = azure_o1_chat_completions.completion(
                    model=model,
                    messages=messages,
                    headers=headers,
                    api_key=api_key,
                    api_base=api_base,
                    api_version=api_version,
                    dynamic_params=dynamic_params,
                    azure_ad_token=azure_ad_token,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    logging_obj=logging,
                    acompletion=acompletion,
                    timeout=timeout,  # type: ignore
                    client=client,  # pass AsyncAzureOpenAI, AzureOpenAI client
                    custom_llm_provider=custom_llm_provider,
                )
            else:
                ## LOAD CONFIG - if set
                config = litellm.AzureOpenAIConfig.get_config()
                for k, v in config.items():
                    if (
                        k not in optional_params
                    ):  # completion(top_k=3) > azure_config(top_k=3) <- allows for dynamic variables to be passed in
                        optional_params[k] = v

                ## COMPLETION CALL
                response = azure_chat_completions.completion(
                    model=model,
                    messages=messages,
                    headers=headers,
                    api_key=api_key,
                    api_base=api_base,
                    api_version=api_version,
                    api_type=api_type,
                    dynamic_params=dynamic_params,
                    azure_ad_token=azure_ad_token,
                    azure_ad_token_provider=azure_ad_token_provider,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    logging_obj=logging,
                    acompletion=acompletion,
                    timeout=timeout,  # type: ignore
                    client=client,  # pass AsyncAzureOpenAI, AzureOpenAI client
                )

            if optional_params.get("stream", False):
                ## LOGGING
                logging.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=response,
                    additional_args={
                        "headers": headers,
                        "api_version": api_version,
                        "api_base": api_base,
                    },
                )
        elif custom_llm_provider == "azure_text":
            # azure configs
            api_type = get_secret("AZURE_API_TYPE") or "azure"

            api_base = api_base or litellm.api_base or get_secret("AZURE_API_BASE")

            api_version = (
                api_version or litellm.api_version or get_secret("AZURE_API_VERSION")
            )

            api_key = (
                api_key
                or litellm.api_key
                or litellm.azure_key
                or get_secret("AZURE_OPENAI_API_KEY")
                or get_secret("AZURE_API_KEY")
            )

            azure_ad_token = optional_params.get("extra_body", {}).pop(
                "azure_ad_token", None
            ) or get_secret("AZURE_AD_TOKEN")

            azure_ad_token_provider = litellm_params.get(
                "azure_ad_token_provider", None
            )

            headers = headers or litellm.headers

            if extra_headers is not None:
                optional_params["extra_headers"] = extra_headers

            ## LOAD CONFIG - if set
            config = litellm.AzureOpenAIConfig.get_config()
            for k, v in config.items():
                if (
                    k not in optional_params
                ):  # completion(top_k=3) > azure_config(top_k=3) <- allows for dynamic variables to be passed in
                    optional_params[k] = v

            ## COMPLETION CALL
            response = azure_text_completions.completion(
                model=model,
                messages=messages,
                headers=headers,
                api_key=api_key,
                api_base=api_base,
                api_version=api_version,
                api_type=api_type,
                azure_ad_token=azure_ad_token,
                azure_ad_token_provider=azure_ad_token_provider,
                model_response=model_response,
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                logging_obj=logging,
                acompletion=acompletion,
                timeout=timeout,
                client=client,  # pass AsyncAzureOpenAI, AzureOpenAI client
            )

            if optional_params.get("stream", False) or acompletion is True:
                ## LOGGING
                logging.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=response,
                    additional_args={
                        "headers": headers,
                        "api_version": api_version,
                        "api_base": api_base,
                    },
                )
        elif custom_llm_provider == "deepseek":
            ## COMPLETION CALL
            try:
                response = base_llm_http_handler.completion(
                    model=model,
                    messages=messages,
                    headers=headers,
                    model_response=model_response,
                    api_key=api_key,
                    api_base=api_base,
                    acompletion=acompletion,
                    logging_obj=logging,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    timeout=timeout,  # type: ignore
                    client=client,
                    custom_llm_provider=custom_llm_provider,
                    encoding=encoding,
                    stream=stream,
                    provider_config=provider_config,
                )
            except Exception as e:
                ## LOGGING - log the original exception returned
                logging.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=str(e),
                    additional_args={"headers": headers},
                )
                raise e

        elif custom_llm_provider == "azure_ai":
            api_base = (
                api_base  # for deepinfra/perplexity/anyscale/groq/friendliai we check in get_llm_provider and pass in the api base from there
                or litellm.api_base
                or get_secret("AZURE_AI_API_BASE")
            )
            # set API KEY
            api_key = (
                api_key
                or litellm.api_key  # for deepinfra/perplexity/anyscale/friendliai we check in get_llm_provider and pass in the api key from there
                or litellm.openai_key
                or get_secret("AZURE_AI_API_KEY")
            )

            headers = headers or litellm.headers

            if extra_headers is not None:
                optional_params["extra_headers"] = extra_headers

            ## FOR COHERE
            if "command-r" in model:  # make sure tool call in messages are str
                messages = stringify_json_tool_call_content(messages=messages)

            ## COMPLETION CALL
            try:
                response = base_llm_http_handler.completion(
                    model=model,
                    messages=messages,
                    headers=headers,
                    model_response=model_response,
                    api_key=api_key,
                    api_base=api_base,
                    acompletion=acompletion,
                    logging_obj=logging,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    timeout=timeout,  # type: ignore
                    client=client,  # pass AsyncOpenAI, OpenAI client
                    custom_llm_provider=custom_llm_provider,
                    encoding=encoding,
                    stream=stream,
                )
            except Exception as e:
                ## LOGGING - log the original exception returned
                logging.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=str(e),
                    additional_args={"headers": headers},
                )
                raise e

            if optional_params.get("stream", False):
                ## LOGGING
                logging.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=response,
                    additional_args={"headers": headers},
                )
        elif (
            custom_llm_provider == "text-completion-openai"
            or "ft:babbage-002" in model
            or "ft:davinci-002" in model  # support for finetuned completion models
            or custom_llm_provider
            in litellm.openai_text_completion_compatible_providers
            and kwargs.get("text_completion") is True
        ):
            openai.api_type = "openai"

            api_base = (
                api_base
                or litellm.api_base
                or get_secret("OPENAI_BASE_URL")
                or get_secret("OPENAI_API_BASE")
                or "https://api.openai.com/v1"
            )

            openai.api_version = None
            # set API KEY

            api_key = (
                api_key
                or litellm.api_key
                or litellm.openai_key
                or get_secret("OPENAI_API_KEY")
            )

            headers = headers or litellm.headers

            if extra_headers is not None:
                optional_params["extra_headers"] = extra_headers

            ## LOAD CONFIG - if set
            config = litellm.OpenAITextCompletionConfig.get_config()
            for k, v in config.items():
                if (
                    k not in optional_params
                ):  # completion(top_k=3) > openai_text_config(top_k=3) <- allows for dynamic variables to be passed in
                    optional_params[k] = v
            if litellm.organization:
                openai.organization = litellm.organization

            if (
                len(messages) > 0
                and "content" in messages[0]
                and isinstance(messages[0]["content"], list)
            ):
                # text-davinci-003 can accept a string or array, if it's an array, assume the array is set in messages[0]['content']
                # https://platform.openai.com/docs/api-reference/completions/create
                prompt = messages[0]["content"]
            else:
                prompt = " ".join([message["content"] for message in messages])  # type: ignore

            ## COMPLETION CALL
            _response = openai_text_completions.completion(
                model=model,
                messages=messages,
                model_response=model_response,
                print_verbose=print_verbose,
                api_key=api_key,
                custom_llm_provider=custom_llm_provider,
                api_base=api_base,
                acompletion=acompletion,
                client=client,  # pass AsyncOpenAI, OpenAI client
                logging_obj=logging,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                timeout=timeout,  # type: ignore
            )

            if (
                optional_params.get("stream", False) is False
                and acompletion is False
                and text_completion is False
            ):
                # convert to chat completion response
                _response = litellm.OpenAITextCompletionConfig().convert_to_chat_model_response_object(
                    response_object=_response, model_response_object=model_response
                )

            if optional_params.get("stream", False) or acompletion is True:
                ## LOGGING
                logging.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=_response,
                    additional_args={"headers": headers},
                )
            response = _response
        elif custom_llm_provider == "fireworks_ai":
            ## COMPLETION CALL
            try:
                response = base_llm_http_handler.completion(
                    model=model,
                    messages=messages,
                    headers=headers,
                    model_response=model_response,
                    api_key=api_key,
                    api_base=api_base,
                    acompletion=acompletion,
                    logging_obj=logging,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    timeout=timeout,  # type: ignore
                    client=client,
                    custom_llm_provider=custom_llm_provider,
                    encoding=encoding,
                    stream=stream,
                    provider_config=provider_config,
                )
            except Exception as e:
                ## LOGGING - log the original exception returned
                logging.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=str(e),
                    additional_args={"headers": headers},
                )
                raise e

        elif custom_llm_provider == "groq":
            api_base = (
                api_base  # for deepinfra/perplexity/anyscale/groq/friendliai we check in get_llm_provider and pass in the api base from there
                or litellm.api_base
                or get_secret("GROQ_API_BASE")
                or "https://api.groq.com/openai/v1"
            )

            # set API KEY
            api_key = (
                api_key
                or litellm.api_key  # for deepinfra/perplexity/anyscale/friendliai we check in get_llm_provider and pass in the api key from there
                or litellm.groq_key
                or get_secret("GROQ_API_KEY")
            )

            headers = headers or litellm.headers

            ## LOAD CONFIG - if set
            config = litellm.GroqChatConfig.get_config()
            for k, v in config.items():
                if (
                    k not in optional_params
                ):  # completion(top_k=3) > openai_config(top_k=3) <- allows for dynamic variables to be passed in
                    optional_params[k] = v

            response = base_llm_http_handler.completion(
                model=model,
                stream=stream,
                messages=messages,
                acompletion=acompletion,
                api_base=api_base,
                model_response=model_response,
                optional_params=optional_params,
                litellm_params=litellm_params,
                custom_llm_provider=custom_llm_provider,
                timeout=timeout,
                headers=headers,
                encoding=encoding,
                api_key=api_key,
                logging_obj=logging,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
                client=client,
            )
        elif custom_llm_provider == "aiohttp_openai":
            # NEW aiohttp provider for 10-100x higher RPS
            api_base = (
                api_base  # for deepinfra/perplexity/anyscale/groq/friendliai we check in get_llm_provider and pass in the api base from there
                or litellm.api_base
                or get_secret("OPENAI_BASE_URL")
                or get_secret("OPENAI_API_BASE")
                or "https://api.openai.com/v1"
            )
            # set API KEY
            api_key = (
                api_key
                or litellm.api_key  # for deepinfra/perplexity/anyscale/friendliai we check in get_llm_provider and pass in the api key from there
                or litellm.openai_key
                or get_secret("OPENAI_API_KEY")
            )

            headers = headers or litellm.headers

            if extra_headers is not None:
                optional_params["extra_headers"] = extra_headers
            response = base_llm_aiohttp_handler.completion(
                model=model,
                messages=messages,
                headers=headers,
                model_response=model_response,
                api_key=api_key,
                api_base=api_base,
                acompletion=acompletion,
                logging_obj=logging,
                optional_params=optional_params,
                litellm_params=litellm_params,
                timeout=timeout,
                client=client,
                custom_llm_provider=custom_llm_provider,
                encoding=encoding,
                stream=stream,
            )
        elif (
            model in litellm.open_ai_chat_completion_models
            or custom_llm_provider == "custom_openai"
            or custom_llm_provider == "deepinfra"
            or custom_llm_provider == "perplexity"
            or custom_llm_provider == "nvidia_nim"
            or custom_llm_provider == "cerebras"
            or custom_llm_provider == "sambanova"
            or custom_llm_provider == "volcengine"
            or custom_llm_provider == "anyscale"
            or custom_llm_provider == "mistral"
            or custom_llm_provider == "openai"
            or custom_llm_provider == "together_ai"
            or custom_llm_provider == "nebius"
            or custom_llm_provider in litellm.openai_compatible_providers
            or "ft:gpt-3.5-turbo" in model  # finetune gpt-3.5-turbo
        ):  # allow user to make an openai call with a custom base
            # note: if a user sets a custom base - we should ensure this works
            # allow for the setting of dynamic and stateful api-bases
            api_base = (
                api_base  # for deepinfra/perplexity/anyscale/groq/friendliai we check in get_llm_provider and pass in the api base from there
                or litellm.api_base
                or get_secret("OPENAI_BASE_URL")
                or get_secret("OPENAI_API_BASE")
                or "https://api.openai.com/v1"
            )
            organization = (
                organization
                or litellm.organization
                or get_secret("OPENAI_ORGANIZATION")
                or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
            )
            openai.organization = organization
            # set API KEY
            api_key = (
                api_key
                or litellm.api_key  # for deepinfra/perplexity/anyscale/friendliai we check in get_llm_provider and pass in the api key from there
                or litellm.openai_key
                or get_secret("OPENAI_API_KEY")
            )

            headers = headers or litellm.headers

            if extra_headers is not None:
                optional_params["extra_headers"] = extra_headers

            if (
                litellm.enable_preview_features and metadata is not None
            ):  # [PREVIEW] allow metadata to be passed to OPENAI
                optional_params["metadata"] = add_openai_metadata(metadata)

            ## LOAD CONFIG - if set
            config = litellm.OpenAIConfig.get_config()
            for k, v in config.items():
                if (
                    k not in optional_params
                ):  # completion(top_k=3) > openai_config(top_k=3) <- allows for dynamic variables to be passed in
                    optional_params[k] = v

            ## COMPLETION CALL
            try:
                response = openai_chat_completions.completion(
                    model=model,
                    messages=messages,
                    headers=headers,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    api_key=api_key,
                    api_base=api_base,
                    acompletion=acompletion,
                    logging_obj=logging,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    timeout=timeout,  # type: ignore
                    custom_prompt_dict=custom_prompt_dict,
                    client=client,  # pass AsyncOpenAI, OpenAI client
                    organization=organization,
                    custom_llm_provider=custom_llm_provider,
                )
            except Exception as e:
                ## LOGGING - log the original exception returned
                logging.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=str(e),
                    additional_args={"headers": headers},
                )
                raise e

            if optional_params.get("stream", False):
                ## LOGGING
                logging.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=response,
                    additional_args={"headers": headers},
                )

        elif (
            "replicate" in model
            or custom_llm_provider == "replicate"
            or model in litellm.replicate_models
        ):
            # Setting the relevant API KEY for replicate, replicate defaults to using os.environ.get("REPLICATE_API_TOKEN")
            replicate_key = (
                api_key
                or litellm.replicate_key
                or litellm.api_key
                or get_secret("REPLICATE_API_KEY")
                or get_secret("REPLICATE_API_TOKEN")
            )

            api_base = (
                api_base
                or litellm.api_base
                or get_secret("REPLICATE_API_BASE")
                or "https://api.replicate.com/v1"
            )

            custom_prompt_dict = custom_prompt_dict or litellm.custom_prompt_dict

            model_response = replicate_chat_completion(  # type: ignore
                model=model,
                messages=messages,
                api_base=api_base,
                model_response=model_response,
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                encoding=encoding,  # for calculating input/output tokens
                api_key=replicate_key,
                logging_obj=logging,
                custom_prompt_dict=custom_prompt_dict,
                acompletion=acompletion,
                headers=headers,
            )

            if optional_params.get("stream", False) is True:
                ## LOGGING
                logging.post_call(
                    input=messages,
                    api_key=replicate_key,
                    original_response=model_response,
                )

            response = model_response
        elif (
            "clarifai" in model
            or custom_llm_provider == "clarifai"
            or model in litellm.clarifai_models
        ):
            clarifai_key = None
            clarifai_key = (
                api_key
                or litellm.clarifai_key
                or litellm.api_key
                or get_secret("CLARIFAI_API_KEY")
                or get_secret("CLARIFAI_API_TOKEN")
            )

            api_base = (
                api_base
                or litellm.api_base
                or get_secret("CLARIFAI_API_BASE")
                or "https://api.clarifai.com/v2"
            )
            api_base = litellm.ClarifaiConfig()._convert_model_to_url(model, api_base)
            response = base_llm_http_handler.completion(
                model=model,
                stream=stream,
                fake_stream=True,  # clarifai does not support streaming, we fake it
                messages=messages,
                acompletion=acompletion,
                api_base=api_base,
                model_response=model_response,
                optional_params=optional_params,
                litellm_params=litellm_params,
                custom_llm_provider="clarifai",
                timeout=timeout,
                headers=headers,
                encoding=encoding,
                api_key=clarifai_key,
                logging_obj=logging,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
            )
        elif custom_llm_provider == "anthropic_text":
            api_key = (
                api_key
                or litellm.anthropic_key
                or litellm.api_key
                or os.environ.get("ANTHROPIC_API_KEY")
            )
            custom_prompt_dict = custom_prompt_dict or litellm.custom_prompt_dict
            api_base = (
                api_base
                or litellm.api_base
                or get_secret("ANTHROPIC_API_BASE")
                or get_secret("ANTHROPIC_BASE_URL")
                or "https://api.anthropic.com/v1/complete"
            )

            if api_base is not None and not api_base.endswith("/v1/complete"):
                api_base += "/v1/complete"

            response = base_llm_http_handler.completion(
                model=model,
                stream=stream,
                messages=messages,
                acompletion=acompletion,
                api_base=api_base,
                model_response=model_response,
                optional_params=optional_params,
                litellm_params=litellm_params,
                custom_llm_provider="anthropic_text",
                timeout=timeout,
                headers=headers,
                encoding=encoding,
                api_key=api_key,
                logging_obj=logging,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
            )
        elif custom_llm_provider == "anthropic":
            api_key = (
                api_key
                or litellm.anthropic_key
                or litellm.api_key
                or os.environ.get("ANTHROPIC_API_KEY")
            )
            custom_prompt_dict = custom_prompt_dict or litellm.custom_prompt_dict
            # call /messages
            # default route for all anthropic models
            api_base = (
                api_base
                or litellm.api_base
                or get_secret("ANTHROPIC_API_BASE")
                or get_secret("ANTHROPIC_BASE_URL")
                or "https://api.anthropic.com/v1/messages"
            )

            if api_base is not None and not api_base.endswith("/v1/messages"):
                api_base += "/v1/messages"

            response = anthropic_chat_completions.completion(
                model=model,
                messages=messages,
                api_base=api_base,
                acompletion=acompletion,
                custom_prompt_dict=litellm.custom_prompt_dict,
                model_response=model_response,
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                encoding=encoding,  # for calculating input/output tokens
                api_key=api_key,
                logging_obj=logging,
                headers=headers,
                timeout=timeout,
                client=client,
                custom_llm_provider=custom_llm_provider,
            )
            if optional_params.get("stream", False) or acompletion is True:
                ## LOGGING
                logging.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=response,
                )
            response = response
        elif custom_llm_provider == "nlp_cloud":
            nlp_cloud_key = (
                api_key
                or litellm.nlp_cloud_key
                or get_secret("NLP_CLOUD_API_KEY")
                or litellm.api_key
            )

            api_base = (
                api_base
                or litellm.api_base
                or get_secret("NLP_CLOUD_API_BASE")
                or "https://api.nlpcloud.io/v1/gpu/"
            )

            response = nlp_cloud_chat_completion(
                model=model,
                messages=messages,
                api_base=api_base,
                model_response=model_response,
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                encoding=encoding,
                api_key=nlp_cloud_key,
                logging_obj=logging,
            )

            if "stream" in optional_params and optional_params["stream"] is True:
                # don't try to access stream object,
                response = CustomStreamWrapper(
                    response,
                    model,
                    custom_llm_provider="nlp_cloud",
                    logging_obj=logging,
                )

            if optional_params.get("stream", False) or acompletion is True:
                ## LOGGING
                logging.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=response,
                )

            response = response
        elif custom_llm_provider == "aleph_alpha":
            aleph_alpha_key = (
                api_key
                or litellm.aleph_alpha_key
                or get_secret("ALEPH_ALPHA_API_KEY")
                or get_secret("ALEPHALPHA_API_KEY")
                or litellm.api_key
            )

            api_base = (
                api_base
                or litellm.api_base
                or get_secret("ALEPH_ALPHA_API_BASE")
                or "https://api.aleph-alpha.com/complete"
            )

            model_response = aleph_alpha.completion(
                model=model,
                messages=messages,
                api_base=api_base,
                model_response=model_response,
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                encoding=encoding,
                default_max_tokens_to_sample=litellm.max_tokens,
                api_key=aleph_alpha_key,
                logging_obj=logging,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
            )

            if "stream" in optional_params and optional_params["stream"] is True:
                # don't try to access stream object,
                response = CustomStreamWrapper(
                    model_response,
                    model,
                    custom_llm_provider="aleph_alpha",
                    logging_obj=logging,
                )
                return response
            response = model_response
        elif custom_llm_provider == "cohere":
            cohere_key = (
                api_key
                or litellm.cohere_key
                or get_secret("COHERE_API_KEY")
                or get_secret("CO_API_KEY")
                or litellm.api_key
            )

            api_base = (
                api_base
                or litellm.api_base
                or get_secret("COHERE_API_BASE")
                or "https://api.cohere.ai/v1/generate"
            )

            headers = headers or litellm.headers or {}
            if headers is None:
                headers = {}

            if extra_headers is not None:
                headers.update(extra_headers)

            response = base_llm_http_handler.completion(
                model=model,
                stream=stream,
                messages=messages,
                acompletion=acompletion,
                api_base=api_base,
                model_response=model_response,
                optional_params=optional_params,
                litellm_params=litellm_params,
                custom_llm_provider="cohere",
                timeout=timeout,
                headers=headers,
                encoding=encoding,
                api_key=cohere_key,
                logging_obj=logging,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
                client=client,
            )
        elif custom_llm_provider == "cohere_chat":
            cohere_key = (
                api_key
                or litellm.cohere_key
                or get_secret_str("COHERE_API_KEY")
                or get_secret_str("CO_API_KEY")
                or litellm.api_key
            )

            api_base = (
                api_base
                or litellm.api_base
                or get_secret_str("COHERE_API_BASE")
                or "https://api.cohere.ai/v1/chat"
            )

            headers = headers or litellm.headers or {}
            if headers is None:
                headers = {}

            if extra_headers is not None:
                headers.update(extra_headers)

            response = base_llm_http_handler.completion(
                model=model,
                stream=stream,
                messages=messages,
                acompletion=acompletion,
                api_base=api_base,
                model_response=model_response,
                optional_params=optional_params,
                litellm_params=litellm_params,
                custom_llm_provider="cohere_chat",
                timeout=timeout,
                headers=headers,
                encoding=encoding,
                api_key=cohere_key,
                logging_obj=logging,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
            )
        elif custom_llm_provider == "maritalk":
            maritalk_key = (
                api_key
                or litellm.maritalk_key
                or get_secret("MARITALK_API_KEY")
                or litellm.api_key
            )

            api_base = (
                api_base
                or litellm.api_base
                or get_secret("MARITALK_API_BASE")
                or "https://chat.maritaca.ai/api"
            )

            model_response = openai_like_chat_completion.completion(
                model=model,
                messages=messages,
                api_base=api_base,
                model_response=model_response,
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                encoding=encoding,
                api_key=maritalk_key,
                logging_obj=logging,
                custom_llm_provider="maritalk",
                custom_prompt_dict=custom_prompt_dict,
            )

            response = model_response
        elif custom_llm_provider == "huggingface":
            huggingface_key = (
                api_key
                or litellm.huggingface_key
                or os.environ.get("HF_TOKEN")
                or os.environ.get("HUGGINGFACE_API_KEY")
                or litellm.api_key
            )
            hf_headers = headers or litellm.headers
            response = base_llm_http_handler.completion(
                model=model,
                messages=messages,
                headers=hf_headers,
                model_response=model_response,
                api_key=huggingface_key,
                api_base=api_base,
                acompletion=acompletion,
                logging_obj=logging,
                optional_params=optional_params,
                litellm_params=litellm_params,
                timeout=timeout,  # type: ignore
                client=client,
                custom_llm_provider=custom_llm_provider,
                encoding=encoding,
                stream=stream,
            )
        elif custom_llm_provider == "oobabooga":
            custom_llm_provider = "oobabooga"
            model_response = oobabooga.completion(
                model=model,
                messages=messages,
                model_response=model_response,
                api_base=api_base,  # type: ignore
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                api_key=None,
                logger_fn=logger_fn,
                encoding=encoding,
                logging_obj=logging,
            )
            if "stream" in optional_params and optional_params["stream"] is True:
                # don't try to access stream object,
                response = CustomStreamWrapper(
                    model_response,
                    model,
                    custom_llm_provider="oobabooga",
                    logging_obj=logging,
                )
                return response
            response = model_response
        elif custom_llm_provider == "databricks":
            api_base = (
                api_base  # for databricks we check in get_llm_provider and pass in the api base from there
                or litellm.api_base
                or os.getenv("DATABRICKS_API_BASE")
            )

            # set API KEY
            api_key = (
                api_key
                or litellm.api_key  # for databricks we check in get_llm_provider and pass in the api key from there
                or litellm.databricks_key
                or get_secret("DATABRICKS_API_KEY")
            )

            headers = headers or litellm.headers

            ## COMPLETION CALL
            try:
                response = base_llm_http_handler.completion(
                    model=model,
                    stream=stream,
                    messages=messages,
                    acompletion=acompletion,
                    api_base=api_base,
                    model_response=model_response,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    custom_llm_provider="databricks",
                    timeout=timeout,
                    headers=headers,
                    encoding=encoding,
                    api_key=api_key,
                    logging_obj=logging,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
                    client=client,
                )
            except Exception as e:
                ## LOGGING - log the original exception returned
                logging.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=str(e),
                    additional_args={"headers": headers},
                )
                raise e

            if optional_params.get("stream", False):
                ## LOGGING
                logging.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=response,
                    additional_args={"headers": headers},
                )

        elif custom_llm_provider == "datarobot":
            response = base_llm_http_handler.completion(
                model=model,
                messages=messages,
                headers=headers,
                model_response=model_response,
                api_key=api_key,
                api_base=api_base,
                acompletion=acompletion,
                logging_obj=logging,
                optional_params=optional_params,
                litellm_params=litellm_params,
                timeout=timeout,  # type: ignore
                client=client,
                custom_llm_provider=custom_llm_provider,
                encoding=encoding,
                stream=stream,
                provider_config=provider_config,
            )
        elif custom_llm_provider == "openrouter":
            api_base = (
                api_base
                or litellm.api_base
                or get_secret_str("OPENROUTER_API_BASE")
                or "https://openrouter.ai/api/v1"
            )

            api_key = (
                api_key
                or litellm.api_key
                or litellm.openrouter_key
                or get_secret("OPENROUTER_API_KEY")
                or get_secret("OR_API_KEY")
            )

            openrouter_site_url = get_secret("OR_SITE_URL") or "https://litellm.ai"
            openrouter_app_name = get_secret("OR_APP_NAME") or "liteLLM"

            openrouter_headers = {
                "HTTP-Referer": openrouter_site_url,
                "X-Title": openrouter_app_name,
            }

            _headers = headers or litellm.headers
            if _headers:
                openrouter_headers.update(_headers)

            headers = openrouter_headers

            ## Load Config
            config = litellm.OpenrouterConfig.get_config()
            for k, v in config.items():
                if k == "extra_body":
                    # we use openai 'extra_body' to pass openrouter specific params - transforms, route, models
                    if "extra_body" in optional_params:
                        optional_params[k].update(v)
                    else:
                        optional_params[k] = v
                elif k not in optional_params:
                    optional_params[k] = v

            data = {"model": model, "messages": messages, **optional_params}

            ## COMPLETION CALL
            response = base_llm_http_handler.completion(
                model=model,
                stream=stream,
                messages=messages,
                acompletion=acompletion,
                api_base=api_base,
                model_response=model_response,
                optional_params=optional_params,
                litellm_params=litellm_params,
                custom_llm_provider="openrouter",
                timeout=timeout,
                headers=headers,
                encoding=encoding,
                api_key=api_key,
                logging_obj=logging,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
                client=client,
            )
            ## LOGGING
            logging.post_call(
                input=messages, api_key=openai.api_key, original_response=response
            )
        elif (
            custom_llm_provider == "together_ai"
            or ("togethercomputer" in model)
            or (model in litellm.together_ai_models)
        ):
            """
            Deprecated. We now do together ai calls via the openai client - https://docs.together.ai/docs/openai-api-compatibility
            """
            pass
        elif custom_llm_provider == "palm":
            raise ValueError(
                "Palm was decommisioned on October 2024. Please use the `gemini/` route for Gemini Google AI Studio Models. Announcement: https://ai.google.dev/palm_docs/palm?hl=en"
            )
        elif custom_llm_provider == "vertex_ai_beta" or custom_llm_provider == "gemini":
            vertex_ai_project = (
                optional_params.pop("vertex_project", None)
                or optional_params.pop("vertex_ai_project", None)
                or litellm.vertex_project
                or get_secret("VERTEXAI_PROJECT")
            )
            vertex_ai_location = (
                optional_params.pop("vertex_location", None)
                or optional_params.pop("vertex_ai_location", None)
                or litellm.vertex_location
                or get_secret("VERTEXAI_LOCATION")
            )
            vertex_credentials = (
                optional_params.pop("vertex_credentials", None)
                or optional_params.pop("vertex_ai_credentials", None)
                or get_secret("VERTEXAI_CREDENTIALS")
            )

            gemini_api_key = (
                api_key
                or get_secret("GEMINI_API_KEY")
                or get_secret("PALM_API_KEY")  # older palm api key should also work
                or litellm.api_key
            )

            api_base = api_base or litellm.api_base or get_secret("GEMINI_API_BASE")

            new_params = deepcopy(optional_params)
            response = vertex_chat_completion.completion(  # type: ignore
                model=model,
                messages=messages,
                model_response=model_response,
                print_verbose=print_verbose,
                optional_params=new_params,
                litellm_params=litellm_params,  # type: ignore
                logger_fn=logger_fn,
                encoding=encoding,
                vertex_location=vertex_ai_location,
                vertex_project=vertex_ai_project,
                vertex_credentials=vertex_credentials,
                gemini_api_key=gemini_api_key,
                logging_obj=logging,
                acompletion=acompletion,
                timeout=timeout,
                custom_llm_provider=custom_llm_provider,
                client=client,
                api_base=api_base,
                extra_headers=extra_headers,
            )

        elif custom_llm_provider == "vertex_ai":
            vertex_ai_project = (
                optional_params.pop("vertex_project", None)
                or optional_params.pop("vertex_ai_project", None)
                or litellm.vertex_project
                or get_secret("VERTEXAI_PROJECT")
            )
            vertex_ai_location = (
                optional_params.pop("vertex_location", None)
                or optional_params.pop("vertex_ai_location", None)
                or litellm.vertex_location
                or get_secret("VERTEXAI_LOCATION")
            )
            vertex_credentials = (
                optional_params.pop("vertex_credentials", None)
                or optional_params.pop("vertex_ai_credentials", None)
                or get_secret("VERTEXAI_CREDENTIALS")
            )

            api_base = api_base or litellm.api_base or get_secret("VERTEXAI_API_BASE")

            new_params = deepcopy(optional_params)
            if (
                model.startswith("meta/")
                or model.startswith("mistral")
                or model.startswith("codestral")
                or model.startswith("jamba")
                or model.startswith("claude")
            ):
                model_response = vertex_partner_models_chat_completion.completion(
                    model=model,
                    messages=messages,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    optional_params=new_params,
                    litellm_params=litellm_params,  # type: ignore
                    logger_fn=logger_fn,
                    encoding=encoding,
                    api_base=api_base,
                    vertex_location=vertex_ai_location,
                    vertex_project=vertex_ai_project,
                    vertex_credentials=vertex_credentials,
                    logging_obj=logging,
                    acompletion=acompletion,
                    headers=headers,
                    custom_prompt_dict=custom_prompt_dict,
                    timeout=timeout,
                    client=client,
                )
            elif "gemini" in model or (
                litellm_params.get("base_model") is not None
                and "gemini" in litellm_params["base_model"]
            ):
                model_response = vertex_chat_completion.completion(  # type: ignore
                    model=model,
                    messages=messages,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    optional_params=new_params,
                    litellm_params=litellm_params,  # type: ignore
                    logger_fn=logger_fn,
                    encoding=encoding,
                    vertex_location=vertex_ai_location,
                    vertex_project=vertex_ai_project,
                    vertex_credentials=vertex_credentials,
                    gemini_api_key=None,
                    logging_obj=logging,
                    acompletion=acompletion,
                    timeout=timeout,
                    custom_llm_provider=custom_llm_provider,
                    client=client,
                    api_base=api_base,
                    extra_headers=extra_headers,
                )
            elif "openai" in model:
                # Vertex Model Garden - OpenAI compatible models
                model_response = vertex_model_garden_chat_completion.completion(
                    model=model,
                    messages=messages,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    optional_params=new_params,
                    litellm_params=litellm_params,  # type: ignore
                    logger_fn=logger_fn,
                    encoding=encoding,
                    api_base=api_base,
                    vertex_location=vertex_ai_location,
                    vertex_project=vertex_ai_project,
                    vertex_credentials=vertex_credentials,
                    logging_obj=logging,
                    acompletion=acompletion,
                    headers=headers,
                    custom_prompt_dict=custom_prompt_dict,
                    timeout=timeout,
                    client=client,
                )
            else:
                model_response = vertex_ai_non_gemini.completion(
                    model=model,
                    messages=messages,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    optional_params=new_params,
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    encoding=encoding,
                    vertex_location=vertex_ai_location,
                    vertex_project=vertex_ai_project,
                    vertex_credentials=vertex_credentials,
                    logging_obj=logging,
                    acompletion=acompletion,
                )

                if (
                    "stream" in optional_params
                    and optional_params["stream"] is True
                    and acompletion is False
                ):
                    response = CustomStreamWrapper(
                        model_response,
                        model,
                        custom_llm_provider="vertex_ai",
                        logging_obj=logging,
                    )
                    return response
            response = model_response
        elif custom_llm_provider == "predibase":
            tenant_id = (
                optional_params.pop("tenant_id", None)
                or optional_params.pop("predibase_tenant_id", None)
                or litellm.predibase_tenant_id
                or get_secret("PREDIBASE_TENANT_ID")
            )

            if tenant_id is None:
                raise ValueError(
                    "Missing Predibase Tenant ID - Required for making the request. Set dynamically (e.g. `completion(..tenant_id=<MY-ID>)`) or in env - `PREDIBASE_TENANT_ID`."
                )

            api_base = (
                api_base
                or optional_params.pop("api_base", None)
                or optional_params.pop("base_url", None)
                or litellm.api_base
                or get_secret("PREDIBASE_API_BASE")
            )

            api_key = (
                api_key
                or litellm.api_key
                or litellm.predibase_key
                or get_secret("PREDIBASE_API_KEY")
            )

            _model_response = predibase_chat_completions.completion(
                model=model,
                messages=messages,
                model_response=model_response,
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                encoding=encoding,
                logging_obj=logging,
                acompletion=acompletion,
                api_base=api_base,
                custom_prompt_dict=custom_prompt_dict,
                api_key=api_key,
                tenant_id=tenant_id,
                timeout=timeout,
            )

            if (
                "stream" in optional_params
                and optional_params["stream"] is True
                and acompletion is False
            ):
                return _model_response
            response = _model_response
        elif custom_llm_provider == "text-completion-codestral":
            api_base = (
                api_base
                or optional_params.pop("api_base", None)
                or optional_params.pop("base_url", None)
                or litellm.api_base
                or "https://codestral.mistral.ai/v1/fim/completions"
            )

            api_key = api_key or litellm.api_key or get_secret("CODESTRAL_API_KEY")

            text_completion_model_response = litellm.TextCompletionResponse(
                stream=stream
            )

            _model_response = codestral_text_completions.completion(  # type: ignore
                model=model,
                messages=messages,
                model_response=text_completion_model_response,
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                encoding=encoding,
                logging_obj=logging,
                acompletion=acompletion,
                api_base=api_base,
                custom_prompt_dict=custom_prompt_dict,
                api_key=api_key,
                timeout=timeout,
            )

            if (
                "stream" in optional_params
                and optional_params["stream"] is True
                and acompletion is False
            ):
                return _model_response
            response = _model_response
        elif custom_llm_provider == "sagemaker_chat":
            # boto3 reads keys from .env
            model_response = base_llm_http_handler.completion(
                model=model,
                stream=stream,
                messages=messages,
                acompletion=acompletion,
                api_base=api_base,
                model_response=model_response,
                optional_params=optional_params,
                litellm_params=litellm_params,
                custom_llm_provider="sagemaker_chat",
                timeout=timeout,
                headers=headers,
                encoding=encoding,
                api_key=api_key,
                logging_obj=logging,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
                client=client,
            )

            ## RESPONSE OBJECT
            response = model_response
        elif custom_llm_provider == "sagemaker":
            # boto3 reads keys from .env
            model_response = sagemaker_llm.completion(
                model=model,
                messages=messages,
                model_response=model_response,
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                custom_prompt_dict=custom_prompt_dict,
                hf_model_name=hf_model_name,
                logger_fn=logger_fn,
                encoding=encoding,
                logging_obj=logging,
                acompletion=acompletion,
            )

            ## RESPONSE OBJECT
            response = model_response
        elif custom_llm_provider == "bedrock":
            # boto3 reads keys from .env
            custom_prompt_dict = custom_prompt_dict or litellm.custom_prompt_dict

            if "aws_bedrock_client" in optional_params:
                verbose_logger.warning(
                    "'aws_bedrock_client' is a deprecated param. Please move to another auth method - https://docs.litellm.ai/docs/providers/bedrock#boto3---authentication."
                )
                # Extract credentials for legacy boto3 client and pass thru to httpx
                aws_bedrock_client = optional_params.pop("aws_bedrock_client")
                creds = aws_bedrock_client._get_credentials().get_frozen_credentials()

                if creds.access_key:
                    optional_params["aws_access_key_id"] = creds.access_key
                if creds.secret_key:
                    optional_params["aws_secret_access_key"] = creds.secret_key
                if creds.token:
                    optional_params["aws_session_token"] = creds.token
                if (
                    "aws_region_name" not in optional_params
                    or optional_params["aws_region_name"] is None
                ):
                    optional_params["aws_region_name"] = (
                        aws_bedrock_client.meta.region_name
                    )

            bedrock_route = BedrockModelInfo.get_bedrock_route(model)
            if bedrock_route == "converse":
                model = model.replace("converse/", "")
                response = bedrock_converse_chat_completion.completion(
                    model=model,
                    messages=messages,
                    custom_prompt_dict=custom_prompt_dict,
                    model_response=model_response,
                    optional_params=optional_params,
                    litellm_params=litellm_params,  # type: ignore
                    logger_fn=logger_fn,
                    encoding=encoding,
                    logging_obj=logging,
                    extra_headers=extra_headers,
                    timeout=timeout,
                    acompletion=acompletion,
                    client=client,
                    api_base=api_base,
                )
            elif bedrock_route == "converse_like":
                model = model.replace("converse_like/", "")
                response = base_llm_http_handler.completion(
                    model=model,
                    stream=stream,
                    messages=messages,
                    acompletion=acompletion,
                    api_base=api_base,
                    model_response=model_response,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    custom_llm_provider="bedrock",
                    timeout=timeout,
                    headers=headers,
                    encoding=encoding,
                    api_key=api_key,
                    logging_obj=logging,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
                    client=client,
                )
            else:
                response = base_llm_http_handler.completion(
                    model=model,
                    stream=stream,
                    messages=messages,
                    acompletion=acompletion,
                    api_base=api_base,
                    model_response=model_response,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    custom_llm_provider="bedrock",
                    timeout=timeout,
                    headers=headers,
                    encoding=encoding,
                    api_key=api_key,
                    logging_obj=logging,
                    client=client,
                )
        elif custom_llm_provider == "watsonx":
            response = watsonx_chat_completion.completion(
                model=model,
                messages=messages,
                headers=headers,
                model_response=model_response,
                print_verbose=print_verbose,
                api_key=api_key,
                api_base=api_base,
                acompletion=acompletion,
                logging_obj=logging,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                timeout=timeout,  # type: ignore
                custom_prompt_dict=custom_prompt_dict,
                client=client,  # pass AsyncOpenAI, OpenAI client
                encoding=encoding,
                custom_llm_provider="watsonx",
            )
        elif custom_llm_provider == "watsonx_text":
            api_key = (
                api_key
                or optional_params.pop("apikey", None)
                or get_secret_str("WATSONX_APIKEY")
                or get_secret_str("WATSONX_API_KEY")
                or get_secret_str("WX_API_KEY")
            )

            api_base = (
                api_base
                or optional_params.pop(
                    "url",
                    optional_params.pop(
                        "api_base", optional_params.pop("base_url", None)
                    ),
                )
                or get_secret_str("WATSONX_API_BASE")
                or get_secret_str("WATSONX_URL")
                or get_secret_str("WX_URL")
                or get_secret_str("WML_URL")
            )

            wx_credentials = optional_params.pop(
                "wx_credentials",
                optional_params.pop(
                    "watsonx_credentials", None
                ),  # follow {provider}_credentials, same as vertex ai
            )

            token: Optional[str] = None
            if wx_credentials is not None:
                api_base = wx_credentials.get("url", api_base)
                api_key = wx_credentials.get(
                    "apikey", wx_credentials.get("api_key", api_key)
                )
                token = wx_credentials.get(
                    "token",
                    wx_credentials.get(
                        "watsonx_token", None
                    ),  # follow format of {provider}_token, same as azure - e.g. 'azure_ad_token=..'
                )

            if token is not None:
                optional_params["token"] = token

            response = base_llm_http_handler.completion(
                model=model,
                stream=stream,
                messages=messages,
                acompletion=acompletion,
                api_base=api_base,
                model_response=model_response,
                optional_params=optional_params,
                litellm_params=litellm_params,
                custom_llm_provider="watsonx_text",
                timeout=timeout,
                headers=headers,
                encoding=encoding,
                api_key=api_key,
                logging_obj=logging,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
                client=client,
            )
        elif custom_llm_provider == "vllm":
            custom_prompt_dict = custom_prompt_dict or litellm.custom_prompt_dict
            model_response = vllm_handler.completion(
                model=model,
                messages=messages,
                custom_prompt_dict=custom_prompt_dict,
                model_response=model_response,
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                encoding=encoding,
                logging_obj=logging,
            )

            if (
                "stream" in optional_params and optional_params["stream"] is True
            ):  ## [BETA]
                # don't try to access stream object,
                response = CustomStreamWrapper(
                    model_response,
                    model,
                    custom_llm_provider="vllm",
                    logging_obj=logging,
                )
                return response

            ## RESPONSE OBJECT
            response = model_response
        elif custom_llm_provider == "ollama":
            api_base = (
                litellm.api_base
                or api_base
                or get_secret("OLLAMA_API_BASE")
                or "http://localhost:11434"
            )
            response = base_llm_http_handler.completion(
                model=model,
                stream=stream,
                messages=messages,
                acompletion=acompletion,
                api_base=api_base,
                model_response=model_response,
                optional_params=optional_params,
                litellm_params=litellm_params,
                custom_llm_provider="ollama",
                timeout=timeout,
                headers=headers,
                encoding=encoding,
                api_key=api_key,
                logging_obj=logging,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
                client=client,
            )

        elif custom_llm_provider == "ollama_chat":
            api_base = (
                litellm.api_base
                or api_base
                or get_secret("OLLAMA_API_BASE")
                or "http://localhost:11434"
            )

            api_key = (
                api_key
                or litellm.ollama_key
                or os.environ.get("OLLAMA_API_KEY")
                or litellm.api_key
            )

            response = base_llm_http_handler.completion(
                model=model,
                stream=stream,
                messages=messages,
                acompletion=acompletion,
                api_base=api_base,
                model_response=model_response,
                optional_params=optional_params,
                litellm_params=litellm_params,
                custom_llm_provider="ollama_chat",
                timeout=timeout,
                headers=headers,
                encoding=encoding,
                api_key=api_key,
                logging_obj=logging,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
                client=client,
            )

        elif custom_llm_provider == "triton":
            api_base = litellm.api_base or api_base
            response = base_llm_http_handler.completion(
                model=model,
                stream=stream,
                messages=messages,
                acompletion=acompletion,
                api_base=api_base,
                model_response=model_response,
                optional_params=optional_params,
                litellm_params=litellm_params,
                custom_llm_provider=custom_llm_provider,
                timeout=timeout,
                headers=headers,
                encoding=encoding,
                api_key=api_key,
                logging_obj=logging,
            )
        elif custom_llm_provider == "cloudflare":
            api_key = (
                api_key
                or litellm.cloudflare_api_key
                or litellm.api_key
                or get_secret("CLOUDFLARE_API_KEY")
            )
            account_id = get_secret("CLOUDFLARE_ACCOUNT_ID")
            api_base = (
                api_base
                or litellm.api_base
                or get_secret("CLOUDFLARE_API_BASE")
                or f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/"
            )

            custom_prompt_dict = custom_prompt_dict or litellm.custom_prompt_dict
            response = base_llm_http_handler.completion(
                model=model,
                stream=stream,
                messages=messages,
                acompletion=acompletion,
                api_base=api_base,
                model_response=model_response,
                optional_params=optional_params,
                litellm_params=litellm_params,
                custom_llm_provider="cloudflare",
                timeout=timeout,
                headers=headers,
                encoding=encoding,
                api_key=api_key,
                logging_obj=logging,  # model call logging done inside the class as we make need to modify I/O to fit aleph alpha's requirements
            )
        elif (
            custom_llm_provider == "baseten"
            or litellm.api_base == "https://app.baseten.co"
        ):
            custom_llm_provider = "baseten"
            baseten_key = (
                api_key
                or litellm.baseten_key
                or os.environ.get("BASETEN_API_KEY")
                or litellm.api_key
            )

            model_response = baseten.completion(
                model=model,
                messages=messages,
                model_response=model_response,
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                encoding=encoding,
                api_key=baseten_key,
                logging_obj=logging,
            )
            if inspect.isgenerator(model_response) or (
                "stream" in optional_params and optional_params["stream"] is True
            ):
                # don't try to access stream object,
                response = CustomStreamWrapper(
                    model_response,
                    model,
                    custom_llm_provider="baseten",
                    logging_obj=logging,
                )
                return response
            response = model_response
        elif custom_llm_provider == "petals" or model in litellm.petals_models:
            api_base = api_base or litellm.api_base

            custom_llm_provider = "petals"
            stream = optional_params.pop("stream", False)
            model_response = petals_handler.completion(
                model=model,
                messages=messages,
                api_base=api_base,
                model_response=model_response,
                print_verbose=print_verbose,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                encoding=encoding,
                logging_obj=logging,
                client=client,
            )
            if stream is True:  ## [BETA]
                # Fake streaming for petals
                resp_string = model_response["choices"][0]["message"]["content"]
                response = CustomStreamWrapper(
                    resp_string,
                    model,
                    custom_llm_provider="petals",
                    logging_obj=logging,
                )
                return response
            response = model_response
        elif custom_llm_provider == "snowflake" or model in litellm.snowflake_models:
            try:
                client = (
                    HTTPHandler(timeout=timeout) if stream is False else None
                )  # Keep this here, otherwise, the httpx.client closes and streaming is impossible
                response = base_llm_http_handler.completion(
                    model=model,
                    messages=messages,
                    headers=headers,
                    model_response=model_response,
                    api_key=api_key,
                    api_base=api_base,
                    acompletion=acompletion,
                    logging_obj=logging,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    timeout=timeout,  # type: ignore
                    client=client,
                    custom_llm_provider=custom_llm_provider,
                    encoding=encoding,
                    stream=stream,
                )

            except Exception as e:
                ## LOGGING - log the original exception returned
                logging.post_call(
                    input=messages,
                    api_key=api_key,
                    original_response=str(e),
                    additional_args={"headers": headers},
                )
                raise e

        elif custom_llm_provider == "custom":
            url = litellm.api_base or api_base or ""
            if url is None or url == "":
                raise ValueError(
                    "api_base not set. Set api_base or litellm.api_base for custom endpoints"
                )

            """
            assume input to custom LLM api bases follow this format:
            resp = litellm.module_level_client.post(
                api_base,
                json={
                    'model': 'meta-llama/Llama-2-13b-hf', # model name
                    'params': {
                        'prompt': ["The capital of France is P"],
                        'max_tokens': 32,
                        'temperature': 0.7,
                        'top_p': 1.0,
                        'top_k': 40,
                    }
                }
            )

            """
            prompt = " ".join([message["content"] for message in messages])  # type: ignore
            resp = litellm.module_level_client.post(
                url,
                json={
                    "model": model,
                    "params": {
                        "prompt": [prompt],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "top_p": top_p,
                        "top_k": kwargs.get("top_k"),
                    },
                },
            )
            response_json = resp.json()
            """
            assume all responses from custom api_bases of this format:
            {
                'data': [
                    {
                        'prompt': 'The capital of France is P',
                        'output': ['The capital of France is PARIS.\nThe capital of France is PARIS.\nThe capital of France is PARIS.\nThe capital of France is PARIS.\nThe capital of France is PARIS.\nThe capital of France is PARIS.\nThe capital of France is PARIS.\nThe capital of France is PARIS.\nThe capital of France is PARIS.\nThe capital of France is PARIS.\nThe capital of France is PARIS.\nThe capital of France is PARIS.\nThe capital of France is PARIS.\nThe capital of France'],
                        'params': {'temperature': 0.7, 'top_k': 40, 'top_p': 1}}],
                        'message': 'ok'
                    }
                ]
            }
            """
            string_response = response_json["data"][0]["output"][0]
            ## RESPONSE OBJECT
            model_response.choices[0].message.content = string_response  # type: ignore
            model_response.created = int(time.time())
            model_response.model = model
            response = model_response

        elif (
            custom_llm_provider in litellm._custom_providers
        ):  # Assume custom LLM provider
            # Get the Custom Handler
            custom_handler: Optional[CustomLLM] = None
            for item in litellm.custom_provider_map:
                if item["provider"] == custom_llm_provider:
                    custom_handler = item["custom_handler"]

            if custom_handler is None:
                raise LiteLLMUnknownProvider(
                    model=model, custom_llm_provider=custom_llm_provider
                )

            ## ROUTE LLM CALL ##
            handler_fn = custom_chat_llm_router(
                async_fn=acompletion, stream=stream, custom_llm=custom_handler
            )

            headers = headers or litellm.headers

            ## CALL FUNCTION
            response = handler_fn(
                model=model,
                messages=messages,
                headers=headers,
                model_response=model_response,
                print_verbose=print_verbose,
                api_key=api_key,
                api_base=api_base,
                acompletion=acompletion,
                logging_obj=logging,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                timeout=timeout,  # type: ignore
                custom_prompt_dict=custom_prompt_dict,
                client=client,  # pass AsyncOpenAI, OpenAI client
                encoding=encoding,
            )
            if stream is True:
                return CustomStreamWrapper(
                    completion_stream=response,
                    model=model,
                    custom_llm_provider=custom_llm_provider,
                    logging_obj=logging,
                )

        else:
            raise LiteLLMUnknownProvider(
                model=model, custom_llm_provider=custom_llm_provider
            )
        return response
    except Exception as e:
        ## Map to OpenAI Exception
        raise exception_type(
            model=model,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=args,
            extra_kwargs=kwargs,
        )


def completion_with_retries(*args, **kwargs):
    """
    Executes a litellm.completion() with 3 retries
    """
    try:
        import tenacity
    except Exception as e:
        raise Exception(
            f"tenacity import failed please run `pip install tenacity`. Error{e}"
        )

    num_retries = kwargs.pop("num_retries", 3)
    # reset retries in .completion()
    kwargs["max_retries"] = 0
    kwargs["num_retries"] = 0
    retry_strategy: Literal["exponential_backoff_retry", "constant_retry"] = kwargs.pop(
        "retry_strategy", "constant_retry"
    )  # type: ignore
    original_function = kwargs.pop("original_function", completion)
    if retry_strategy == "exponential_backoff_retry":
        retryer = tenacity.Retrying(
            wait=tenacity.wait_exponential(multiplier=1, max=10),
            stop=tenacity.stop_after_attempt(num_retries),
            reraise=True,
        )
    else:
        retryer = tenacity.Retrying(
            stop=tenacity.stop_after_attempt(num_retries), reraise=True
        )
    return retryer(original_function, *args, **kwargs)


async def acompletion_with_retries(*args, **kwargs):
    """
    [DEPRECATED]. Use 'acompletion' or router.acompletion instead!
    Executes a litellm.completion() with 3 retries
    """
    try:
        import tenacity
    except Exception as e:
        raise Exception(
            f"tenacity import failed please run `pip install tenacity`. Error{e}"
        )

    num_retries = kwargs.pop("num_retries", 3)
    kwargs["max_retries"] = 0
    kwargs["num_retries"] = 0
    retry_strategy = kwargs.pop("retry_strategy", "constant_retry")
    original_function = kwargs.pop("original_function", completion)
    if retry_strategy == "exponential_backoff_retry":
        retryer = tenacity.Retrying(
            wait=tenacity.wait_exponential(multiplier=1, max=10),
            stop=tenacity.stop_after_attempt(num_retries),
            reraise=True,
        )
    else:
        retryer = tenacity.Retrying(
            stop=tenacity.stop_after_attempt(num_retries), reraise=True
        )
    return await retryer(original_function, *args, **kwargs)


### EMBEDDING ENDPOINTS ####################
@client
async def aembedding(*args, **kwargs) -> EmbeddingResponse:
    """
    Asynchronously calls the `embedding` function with the given arguments and keyword arguments.

    Parameters:
    - `args` (tuple): Positional arguments to be passed to the `embedding` function.
    - `kwargs` (dict): Keyword arguments to be passed to the `embedding` function.

    Returns:
    - `response` (Any): The response returned by the `embedding` function.
    """
    loop = asyncio.get_event_loop()
    model = args[0] if len(args) > 0 else kwargs["model"]
    ### PASS ARGS TO Embedding ###
    kwargs["aembedding"] = True
    custom_llm_provider = None
    try:
        # Use a partial function to pass your keyword arguments
        func = partial(embedding, *args, **kwargs)

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        _, custom_llm_provider, _, _ = get_llm_provider(
            model=model, api_base=kwargs.get("api_base", None)
        )

        # Await normally
        init_response = await loop.run_in_executor(None, func_with_context)

        response: Optional[EmbeddingResponse] = None
        if isinstance(init_response, dict):
            response = EmbeddingResponse(**init_response)
        elif isinstance(init_response, EmbeddingResponse):  ## CACHING SCENARIO
            response = init_response
        elif asyncio.iscoroutine(init_response):
            response = await init_response  # type: ignore
        if (
            response is not None
            and isinstance(response, EmbeddingResponse)
            and hasattr(response, "_hidden_params")
        ):
            response._hidden_params["custom_llm_provider"] = custom_llm_provider

        if response is None:
            raise ValueError(
                "Unable to get Embedding Response. Please pass a valid llm_provider."
            )
        return response
    except Exception as e:
        custom_llm_provider = custom_llm_provider or "openai"
        raise exception_type(
            model=model,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=args,
            extra_kwargs=kwargs,
        )


@client
def embedding(  # noqa: PLR0915
    model,
    input=[],
    # Optional params
    dimensions: Optional[int] = None,
    encoding_format: Optional[str] = None,
    timeout=600,  # default to 10 minutes
    # set api_base, api_version, api_key
    api_base: Optional[str] = None,
    api_version: Optional[str] = None,
    api_key: Optional[str] = None,
    api_type: Optional[str] = None,
    caching: bool = False,
    user: Optional[str] = None,
    custom_llm_provider=None,
    litellm_call_id=None,
    logger_fn=None,
    **kwargs,
) -> Union[EmbeddingResponse, Coroutine[Any, Any, EmbeddingResponse]]:
    """
    Embedding function that calls an API to generate embeddings for the given input.

    Parameters:
    - model: The embedding model to use.
    - input: The input for which embeddings are to be generated.
    - encoding_format: Optional[str] The format to return the embeddings in. Can be either `float` or `base64`
    - dimensions: The number of dimensions the resulting output embeddings should have. Only supported in text-embedding-3 and later models.
    - timeout: The timeout value for the API call, default 10 mins
    - litellm_call_id: The call ID for litellm logging.
    - litellm_logging_obj: The litellm logging object.
    - logger_fn: The logger function.
    - api_base: Optional. The base URL for the API.
    - api_version: Optional. The version of the API.
    - api_key: Optional. The API key to use.
    - api_type: Optional. The type of the API.
    - caching: A boolean indicating whether to enable caching.
    - custom_llm_provider: The custom llm provider.

    Returns:
    - response: The response received from the API call.

    Raises:
    - exception_type: If an exception occurs during the API call.
    """
    azure = kwargs.get("azure", None)
    client = kwargs.pop("client", None)
    max_retries = kwargs.get("max_retries", None)
    litellm_logging_obj: LiteLLMLoggingObj = kwargs.get("litellm_logging_obj")  # type: ignore
    mock_response: Optional[List[float]] = kwargs.get("mock_response", None)  # type: ignore
    azure_ad_token_provider = kwargs.pop("azure_ad_token_provider", None)
    aembedding = kwargs.get("aembedding", None)
    extra_headers = kwargs.get("extra_headers", None)
    headers = kwargs.get("headers", None)
    ### CUSTOM MODEL COST ###
    input_cost_per_token = kwargs.get("input_cost_per_token", None)
    output_cost_per_token = kwargs.get("output_cost_per_token", None)
    input_cost_per_second = kwargs.get("input_cost_per_second", None)
    output_cost_per_second = kwargs.get("output_cost_per_second", None)
    openai_params = [
        "user",
        "dimensions",
        "request_timeout",
        "api_base",
        "api_version",
        "api_key",
        "deployment_id",
        "organization",
        "base_url",
        "default_headers",
        "timeout",
        "max_retries",
        "encoding_format",
    ]
    litellm_params = [
        "aembedding",
        "extra_headers",
    ] + all_litellm_params

    default_params = openai_params + litellm_params
    non_default_params = {
        k: v for k, v in kwargs.items() if k not in default_params
    }  # model-specific params - pass them straight to the model/provider

    model, custom_llm_provider, dynamic_api_key, api_base = get_llm_provider(
        model=model,
        custom_llm_provider=custom_llm_provider,
        api_base=api_base,
        api_key=api_key,
    )

    if dynamic_api_key is not None:
        api_key = dynamic_api_key

    optional_params = get_optional_params_embeddings(
        model=model,
        user=user,
        dimensions=dimensions,
        encoding_format=encoding_format,
        custom_llm_provider=custom_llm_provider,
        **non_default_params,
    )

    ### REGISTER CUSTOM MODEL PRICING -- IF GIVEN ###
    if input_cost_per_token is not None and output_cost_per_token is not None:
        litellm.register_model(
            {
                f"{custom_llm_provider}/{model}": {
                    "input_cost_per_token": input_cost_per_token,
                    "output_cost_per_token": output_cost_per_token,
                    "litellm_provider": custom_llm_provider,
                }
            }
        )
    if input_cost_per_second is not None:  # time based pricing just needs cost in place
        output_cost_per_second = output_cost_per_second or 0.0
        litellm.register_model(
            {
                f"{custom_llm_provider}/{model}": {
                    "input_cost_per_second": input_cost_per_second,
                    "output_cost_per_second": output_cost_per_second,
                    "litellm_provider": custom_llm_provider,
                }
            }
        )

    litellm_params_dict = get_litellm_params(**kwargs)

    logging: Logging = litellm_logging_obj  # type: ignore
    logging.update_environment_variables(
        model=model,
        user=user,
        optional_params=optional_params,
        litellm_params=litellm_params_dict,
        custom_llm_provider=custom_llm_provider,
    )

    if mock_response is not None:
        return mock_embedding(model=model, mock_response=mock_response)
    try:
        response: Optional[
            Union[EmbeddingResponse, Coroutine[Any, Any, EmbeddingResponse]]
        ] = None

        if azure is True or custom_llm_provider == "azure":
            # azure configs

            api_base = api_base or litellm.api_base or get_secret_str("AZURE_API_BASE")

            api_version = (
                api_version
                or litellm.api_version
                or get_secret_str("AZURE_API_VERSION")
                or litellm.AZURE_DEFAULT_API_VERSION
            )

            azure_ad_token = optional_params.pop(
                "azure_ad_token", None
            ) or get_secret_str("AZURE_AD_TOKEN")

            api_key = (
                api_key
                or litellm.api_key
                or litellm.azure_key
                or get_secret_str("AZURE_API_KEY")
            )

            if api_base is None:
                raise ValueError(
                    "No API Base provided for Azure OpenAI LLM provider. Set 'AZURE_API_BASE' in .env"
                )

            ## EMBEDDING CALL
            response = azure_chat_completions.embedding(
                model=model,
                input=input,
                api_base=api_base,
                api_key=api_key,
                api_version=api_version,
                azure_ad_token=azure_ad_token,
                azure_ad_token_provider=azure_ad_token_provider,
                logging_obj=logging,
                timeout=timeout,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                client=client,
                aembedding=aembedding,
                max_retries=max_retries,
                headers=headers or extra_headers,
                litellm_params=litellm_params_dict,
            )
        elif (
            model in litellm.open_ai_embedding_models
            or custom_llm_provider == "openai"
            or custom_llm_provider == "together_ai"
            or custom_llm_provider == "nvidia_nim"
            or custom_llm_provider == "litellm_proxy"
        ):
            api_base = (
                api_base
                or litellm.api_base
                or get_secret_str("OPENAI_BASE_URL")
                or get_secret_str("OPENAI_API_BASE")
                or "https://api.openai.com/v1"
            )
            openai.organization = (
                litellm.organization
                or get_secret_str("OPENAI_ORGANIZATION")
                or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
            )
            # set API KEY
            api_key = (
                api_key
                or litellm.api_key
                or litellm.openai_key
                or get_secret_str("OPENAI_API_KEY")
            )

            if extra_headers is not None:
                optional_params["extra_headers"] = extra_headers

            api_version = None

            ## EMBEDDING CALL
            response = openai_chat_completions.embedding(
                model=model,
                input=input,
                api_base=api_base,
                api_key=api_key,
                logging_obj=logging,
                timeout=timeout,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                client=client,
                aembedding=aembedding,
                max_retries=max_retries,
            )
        elif custom_llm_provider == "databricks":
            api_base = api_base or litellm.api_base or get_secret("DATABRICKS_API_BASE")  # type: ignore

            # set API KEY
            api_key = (
                api_key
                or litellm.api_key
                or litellm.databricks_key
                or get_secret("DATABRICKS_API_KEY")
            )  # type: ignore

            ## EMBEDDING CALL
            response = databricks_embedding.embedding(
                model=model,
                input=input,
                api_base=api_base,
                api_key=api_key,
                logging_obj=logging,
                timeout=timeout,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                client=client,
                aembedding=aembedding,
            )
        elif (
            custom_llm_provider == "openai_like"
            or custom_llm_provider == "jina_ai"
            or custom_llm_provider == "hosted_vllm"
            or custom_llm_provider == "llamafile"
            or custom_llm_provider == "lm_studio"
        ):
            api_base = (
                api_base or litellm.api_base or get_secret_str("OPENAI_LIKE_API_BASE")
            )

            # set API KEY
            if api_key is None:
                api_key = (
                    api_key
                    or litellm.api_key
                    or litellm.openai_like_key
                    or get_secret_str("OPENAI_LIKE_API_KEY")
                )

            ## EMBEDDING CALL
            response = openai_like_embedding.embedding(
                model=model,
                input=input,
                api_base=api_base,
                api_key=api_key,
                logging_obj=logging,
                timeout=timeout,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                client=client,
                aembedding=aembedding,
            )
        elif custom_llm_provider == "cohere" or custom_llm_provider == "cohere_chat":
            cohere_key = (
                api_key
                or litellm.cohere_key
                or get_secret_str("COHERE_API_KEY")
                or get_secret_str("CO_API_KEY")
                or litellm.api_key
            )

            if extra_headers is not None and isinstance(extra_headers, dict):
                headers = extra_headers
            else:
                headers = {}

            response = base_llm_http_handler.embedding(
                model=model,
                input=input,
                custom_llm_provider=custom_llm_provider,
                api_base=api_base,
                api_key=cohere_key,
                logging_obj=logging,
                timeout=timeout,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                client=client,
                aembedding=aembedding,
                litellm_params=litellm_params_dict,
                headers=headers,
            )
        elif custom_llm_provider == "huggingface":
            api_key = (
                api_key
                or litellm.huggingface_key
                or get_secret("HUGGINGFACE_API_KEY")
                or litellm.api_key
            )  # type: ignore
            response = huggingface_embed.embedding(
                model=model,
                input=input,
                encoding=encoding,  # type: ignore
                api_key=api_key,
                api_base=api_base,
                logging_obj=logging,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                client=client,
                aembedding=aembedding,
                litellm_params=litellm_params_dict,
            )
        elif custom_llm_provider == "bedrock":
            if isinstance(input, str):
                transformed_input = [input]
            else:
                transformed_input = input
            response = bedrock_embedding.embeddings(
                model=model,
                input=transformed_input,
                encoding=encoding,
                logging_obj=logging,
                optional_params=optional_params,
                model_response=EmbeddingResponse(),
                client=client,
                timeout=timeout,
                aembedding=aembedding,
                litellm_params={},
                api_base=api_base,
                print_verbose=print_verbose,
                extra_headers=extra_headers,
            )
        elif custom_llm_provider == "triton":
            if api_base is None:
                raise ValueError(
                    "api_base is required for triton. Please pass `api_base`"
                )
            response = base_llm_http_handler.embedding(
                model=model,
                input=input,
                custom_llm_provider=custom_llm_provider,
                api_base=api_base,
                api_key=api_key,
                logging_obj=logging,
                timeout=timeout,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                client=client,
                aembedding=aembedding,
                litellm_params={},
            )
        elif custom_llm_provider == "gemini":
            gemini_api_key = (
                api_key or get_secret_str("GEMINI_API_KEY") or litellm.api_key
            )

            api_base = api_base or litellm.api_base or get_secret_str("GEMINI_API_BASE")

            response = google_batch_embeddings.batch_embeddings(  # type: ignore
                model=model,
                input=input,
                encoding=encoding,
                logging_obj=logging,
                optional_params=optional_params,
                model_response=EmbeddingResponse(),
                vertex_project=None,
                vertex_location=None,
                vertex_credentials=None,
                aembedding=aembedding,
                print_verbose=print_verbose,
                custom_llm_provider="gemini",
                api_key=gemini_api_key,
                api_base=api_base,
                client=client,
            )

        elif custom_llm_provider == "vertex_ai":
            vertex_ai_project = (
                optional_params.pop("vertex_project", None)
                or optional_params.pop("vertex_ai_project", None)
                or litellm.vertex_project
                or get_secret_str("VERTEXAI_PROJECT")
                or get_secret_str("VERTEX_PROJECT")
            )
            vertex_ai_location = (
                optional_params.pop("vertex_location", None)
                or optional_params.pop("vertex_ai_location", None)
                or litellm.vertex_location
                or get_secret_str("VERTEXAI_LOCATION")
                or get_secret_str("VERTEX_LOCATION")
            )
            vertex_credentials = (
                optional_params.pop("vertex_credentials", None)
                or optional_params.pop("vertex_ai_credentials", None)
                or get_secret_str("VERTEXAI_CREDENTIALS")
                or get_secret_str("VERTEX_CREDENTIALS")
            )

            api_base = (
                api_base
                or litellm.api_base
                or get_secret_str("VERTEXAI_API_BASE")
                or get_secret_str("VERTEX_API_BASE")
            )

            if (
                "image" in optional_params
                or "video" in optional_params
                or model
                in vertex_multimodal_embedding.SUPPORTED_MULTIMODAL_EMBEDDING_MODELS
            ):
                # multimodal embedding is supported on vertex httpx
                response = vertex_multimodal_embedding.multimodal_embedding(
                    model=model,
                    input=input,
                    encoding=encoding,
                    logging_obj=logging,
                    optional_params=optional_params,
                    litellm_params=litellm_params_dict,
                    model_response=EmbeddingResponse(),
                    vertex_project=vertex_ai_project,
                    vertex_location=vertex_ai_location,
                    vertex_credentials=vertex_credentials,
                    aembedding=aembedding,
                    print_verbose=print_verbose,
                    custom_llm_provider="vertex_ai",
                    client=client,
                    api_base=api_base,
                )
            else:
                response = vertex_embedding.embedding(
                    model=model,
                    input=input,
                    encoding=encoding,
                    logging_obj=logging,
                    optional_params=optional_params,
                    model_response=EmbeddingResponse(),
                    vertex_project=vertex_ai_project,
                    vertex_location=vertex_ai_location,
                    vertex_credentials=vertex_credentials,
                    custom_llm_provider="vertex_ai",
                    timeout=timeout,
                    aembedding=aembedding,
                    print_verbose=print_verbose,
                    api_key=api_key,
                    api_base=api_base,
                    client=client,
                )
        elif custom_llm_provider == "oobabooga":
            response = oobabooga.embedding(
                model=model,
                input=input,
                encoding=encoding,
                api_base=api_base,
                logging_obj=logging,
                optional_params=optional_params,
                model_response=EmbeddingResponse(),
                api_key=api_key,
            )
        elif custom_llm_provider == "ollama":
            api_base = (
                litellm.api_base
                or api_base
                or get_secret_str("OLLAMA_API_BASE")
                or "http://localhost:11434"
            )  # type: ignore

            if isinstance(input, str):
                input = [input]
            if not all(isinstance(item, str) for item in input):
                raise litellm.BadRequestError(
                    message=f"Invalid input for ollama embeddings. input={input}",
                    model=model,  # type: ignore
                    llm_provider="ollama",  # type: ignore
                )
            ollama_embeddings_fn = (
                ollama.ollama_aembeddings
                if aembedding is True
                else ollama.ollama_embeddings
            )
            response = ollama_embeddings_fn(  # type: ignore
                api_base=api_base,
                model=model,
                prompts=input,
                encoding=encoding,
                logging_obj=logging,
                optional_params=optional_params,
                model_response=EmbeddingResponse(),
            )
        elif custom_llm_provider == "sagemaker":
            response = sagemaker_llm.embedding(
                model=model,
                input=input,
                encoding=encoding,
                logging_obj=logging,
                optional_params=optional_params,
                model_response=EmbeddingResponse(),
                print_verbose=print_verbose,
            )
        elif custom_llm_provider == "mistral":
            api_key = api_key or litellm.api_key or get_secret_str("MISTRAL_API_KEY")
            response = openai_chat_completions.embedding(
                model=model,
                input=input,
                api_base=api_base,
                api_key=api_key,
                logging_obj=logging,
                timeout=timeout,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                client=client,
                aembedding=aembedding,
            )
        elif custom_llm_provider == "fireworks_ai":
            api_key = (
                api_key or litellm.api_key or get_secret_str("FIREWORKS_AI_API_KEY")
            )
            response = openai_chat_completions.embedding(
                model=model,
                input=input,
                api_base=api_base,
                api_key=api_key,
                logging_obj=logging,
                timeout=timeout,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                client=client,
                aembedding=aembedding,
            )
        elif custom_llm_provider == "nebius":
            api_key = api_key or litellm.api_key or get_secret_str("NEBIUS_API_KEY")
            api_base = (
                api_base
                or litellm.api_base
                or get_secret_str("NEBIUS_API_BASE")
                or "api.studio.nebius.ai/v1"
            )

            response = openai_chat_completions.embedding(
                model=model,
                input=input,
                api_base=api_base,
                api_key=api_key,
                logging_obj=logging,
                timeout=timeout,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                client=client,
                aembedding=aembedding,
            )
        elif custom_llm_provider == "voyage":
            response = base_llm_http_handler.embedding(
                model=model,
                input=input,
                custom_llm_provider=custom_llm_provider,
                api_base=api_base,
                api_key=api_key,
                logging_obj=logging,
                timeout=timeout,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                client=client,
                aembedding=aembedding,
                litellm_params={},
            )
        elif custom_llm_provider == "infinity":
            response = base_llm_http_handler.embedding(
                model=model,
                input=input,
                custom_llm_provider=custom_llm_provider,
                api_base=api_base,
                api_key=api_key,
                logging_obj=logging,
                timeout=timeout,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                client=client,
                aembedding=aembedding,
                litellm_params={},
            )
        elif custom_llm_provider == "watsonx":
            credentials = IBMWatsonXMixin.get_watsonx_credentials(
                optional_params=optional_params, api_key=api_key, api_base=api_base
            )

            api_key = credentials["api_key"]
            api_base = credentials["api_base"]

            if "token" in credentials:
                optional_params["token"] = credentials["token"]

            response = base_llm_http_handler.embedding(
                model=model,
                input=input,
                custom_llm_provider=custom_llm_provider,
                api_base=api_base,
                api_key=api_key,
                logging_obj=logging,
                timeout=timeout,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                litellm_params={},
                client=client,
                aembedding=aembedding,
            )
        elif custom_llm_provider == "xinference":
            api_key = (
                api_key
                or litellm.api_key
                or get_secret_str("XINFERENCE_API_KEY")
                or "stub-xinference-key"
            )  # xinference does not need an api key, pass a stub key if user did not set one
            api_base = (
                api_base
                or litellm.api_base
                or get_secret_str("XINFERENCE_API_BASE")
                or "http://127.0.0.1:9997/v1"
            )
            response = openai_chat_completions.embedding(
                model=model,
                input=input,
                api_base=api_base,
                api_key=api_key,
                logging_obj=logging,
                timeout=timeout,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                client=client,
                aembedding=aembedding,
            )
        elif custom_llm_provider == "azure_ai":
            api_base = (
                api_base  # for deepinfra/perplexity/anyscale/groq/friendliai we check in get_llm_provider and pass in the api base from there
                or litellm.api_base
                or get_secret_str("AZURE_AI_API_BASE")
            )
            # set API KEY
            api_key = (
                api_key
                or litellm.api_key  # for deepinfra/perplexity/anyscale/friendliai we check in get_llm_provider and pass in the api key from there
                or litellm.openai_key
                or get_secret_str("AZURE_AI_API_KEY")
            )

            ## EMBEDDING CALL
            response = azure_ai_embedding.embedding(
                model=model,
                input=input,
                api_base=api_base,
                api_key=api_key,
                logging_obj=logging,
                timeout=timeout,
                model_response=EmbeddingResponse(),
                optional_params=optional_params,
                client=client,
                aembedding=aembedding,
            )
        elif custom_llm_provider in litellm._custom_providers:
            custom_handler: Optional[CustomLLM] = None
            for item in litellm.custom_provider_map:
                if item["provider"] == custom_llm_provider:
                    custom_handler = item["custom_handler"]

            if custom_handler is None:
                raise LiteLLMUnknownProvider(
                    model=model, custom_llm_provider=custom_llm_provider
                )

            handler_fn = (
                custom_handler.embedding
                if not aembedding
                else custom_handler.aembedding
            )

            response = handler_fn(
                model=model,
                input=input,
                logging_obj=logging,
                api_base=api_base,
                api_key=api_key,
                timeout=timeout,
                optional_params=optional_params,
                model_response=EmbeddingResponse(),
                print_verbose=print_verbose,
                litellm_params=litellm_params_dict,
            )
        else:
            raise LiteLLMUnknownProvider(
                model=model, custom_llm_provider=custom_llm_provider
            )
        if (
            response is not None
            and hasattr(response, "_hidden_params")
            and isinstance(response, EmbeddingResponse)
        ):
            response._hidden_params["custom_llm_provider"] = custom_llm_provider

        if response is None:
            raise LiteLLMUnknownProvider(
                model=model, custom_llm_provider=custom_llm_provider
            )
        return response
    except Exception as e:
        ## LOGGING
        litellm_logging_obj.post_call(
            input=input,
            api_key=api_key,
            original_response=str(e),
        )
        ## Map to OpenAI Exception
        raise exception_type(
            model=model,
            original_exception=e,
            custom_llm_provider=custom_llm_provider,
            extra_kwargs=kwargs,
        )


###### Text Completion ################
@client
async def atext_completion(
    *args, **kwargs
) -> Union[TextCompletionResponse, TextCompletionStreamWrapper]:
    """
    Implemented to handle async streaming for the text completion endpoint
    """
    loop = asyncio.get_event_loop()
    model = args[0] if len(args) > 0 else kwargs["model"]
    ### PASS ARGS TO COMPLETION ###
    kwargs["acompletion"] = True
    custom_llm_provider = None
    try:
        # Use a partial function to pass your keyword arguments
        func = partial(text_completion, *args, **kwargs)

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        init_response = await loop.run_in_executor(None, func_with_context)
        if isinstance(init_response, dict) or isinstance(
            init_response, TextCompletionResponse
        ):  ## CACHING SCENARIO
            if isinstance(init_response, dict):
                response = TextCompletionResponse(**init_response)
            else:
                response = init_response
        elif asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response  # type: ignore

        if (
            kwargs.get("stream", False) is True
            or isinstance(response, TextCompletionStreamWrapper)
            or isinstance(response, CustomStreamWrapper)
        ):  # return an async generator
            return TextCompletionStreamWrapper(
                completion_stream=_async_streaming(
                    response=response,
                    model=model,
                    custom_llm_provider=custom_llm_provider,
                    args=args,
                ),
                model=model,
                custom_llm_provider=custom_llm_provider,
                stream_options=kwargs.get("stream_options"),
            )
        else:
            ## OpenAI / Azure Text Completion Returns here
            if isinstance(response, TextCompletionResponse):
                return response
            elif asyncio.iscoroutine(response):
                response = await response

            text_completion_response = TextCompletionResponse()
            text_completion_response = litellm.utils.LiteLLMResponseObjectHandler.convert_chat_to_text_completion(
                text_completion_response=text_completion_response,
                response=response,
                custom_llm_provider=custom_llm_provider,
            )
            return text_completion_response
    except Exception as e:
        custom_llm_provider = custom_llm_provider or "openai"
        raise exception_type(
            model=model,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=args,
            extra_kwargs=kwargs,
        )


@client
def text_completion(  # noqa: PLR0915
    prompt: Union[
        str, List[Union[str, List[Union[str, List[int]]]]]
    ],  # Required: The prompt(s) to generate completions for.
    model: Optional[str] = None,  # Optional: either `model` or `engine` can be set
    best_of: Optional[
        int
    ] = None,  # Optional: Generates best_of completions server-side.
    echo: Optional[
        bool
    ] = None,  # Optional: Echo back the prompt in addition to the completion.
    frequency_penalty: Optional[
        float
    ] = None,  # Optional: Penalize new tokens based on their existing frequency.
    logit_bias: Optional[
        Dict[int, int]
    ] = None,  # Optional: Modify the likelihood of specified tokens.
    logprobs: Optional[
        int
    ] = None,  # Optional: Include the log probabilities on the most likely tokens.
    max_tokens: Optional[
        int
    ] = None,  # Optional: The maximum number of tokens to generate in the completion.
    n: Optional[
        int
    ] = None,  # Optional: How many completions to generate for each prompt.
    presence_penalty: Optional[
        float
    ] = None,  # Optional: Penalize new tokens based on whether they appear in the text so far.
    stop: Optional[
        Union[str, List[str]]
    ] = None,  # Optional: Sequences where the API will stop generating further tokens.
    stream: Optional[bool] = None,  # Optional: Whether to stream back partial progress.
    stream_options: Optional[dict] = None,
    suffix: Optional[
        str
    ] = None,  # Optional: The suffix that comes after a completion of inserted text.
    temperature: Optional[float] = None,  # Optional: Sampling temperature to use.
    top_p: Optional[float] = None,  # Optional: Nucleus sampling parameter.
    user: Optional[
        str
    ] = None,  # Optional: A unique identifier representing your end-user.
    # set api_base, api_version, api_key
    api_base: Optional[str] = None,
    api_version: Optional[str] = None,
    api_key: Optional[str] = None,
    model_list: Optional[list] = None,  # pass in a list of api_base,keys, etc.
    # Optional liteLLM function params
    custom_llm_provider: Optional[str] = None,
    *args,
    **kwargs,
):
    import copy

    """
    Generate text completions using the OpenAI API.

    Args:
        model (str): ID of the model to use.
        prompt (Union[str, List[Union[str, List[Union[str, List[int]]]]]): The prompt(s) to generate completions for.
        best_of (Optional[int], optional): Generates best_of completions server-side. Defaults to 1.
        echo (Optional[bool], optional): Echo back the prompt in addition to the completion. Defaults to False.
        frequency_penalty (Optional[float], optional): Penalize new tokens based on their existing frequency. Defaults to 0.
        logit_bias (Optional[Dict[int, int]], optional): Modify the likelihood of specified tokens. Defaults to None.
        logprobs (Optional[int], optional): Include the log probabilities on the most likely tokens. Defaults to None.
        max_tokens (Optional[int], optional): The maximum number of tokens to generate in the completion. Defaults to 16.
        n (Optional[int], optional): How many completions to generate for each prompt. Defaults to 1.
        presence_penalty (Optional[float], optional): Penalize new tokens based on whether they appear in the text so far. Defaults to 0.
        stop (Optional[Union[str, List[str]]], optional): Sequences where the API will stop generating further tokens. Defaults to None.
        stream (Optional[bool], optional): Whether to stream back partial progress. Defaults to False.
        suffix (Optional[str], optional): The suffix that comes after a completion of inserted text. Defaults to None.
        temperature (Optional[float], optional): Sampling temperature to use. Defaults to 1.
        top_p (Optional[float], optional): Nucleus sampling parameter. Defaults to 1.
        user (Optional[str], optional): A unique identifier representing your end-user.
    Returns:
        TextCompletionResponse: A response object containing the generated completion and associated metadata.

    Example:
        Your example of how to use this function goes here.
    """
    if "engine" in kwargs:
        _engine = kwargs["engine"]
        if model is None and isinstance(_engine, str):
            # only use engine when model not passed
            model = _engine
        kwargs.pop("engine")

    text_completion_response = TextCompletionResponse()

    optional_params: Dict[str, Any] = {}
    # default values for all optional params are none, litellm only passes them to the llm when they are set to non None values
    if best_of is not None:
        optional_params["best_of"] = best_of
    if echo is not None:
        optional_params["echo"] = echo
    if frequency_penalty is not None:
        optional_params["frequency_penalty"] = frequency_penalty
    if logit_bias is not None:
        optional_params["logit_bias"] = logit_bias
    if logprobs is not None:
        optional_params["logprobs"] = logprobs
    if max_tokens is not None:
        optional_params["max_tokens"] = max_tokens
    if n is not None:
        optional_params["n"] = n
    if presence_penalty is not None:
        optional_params["presence_penalty"] = presence_penalty
    if stop is not None:
        optional_params["stop"] = stop
    if stream is not None:
        optional_params["stream"] = stream
    if stream_options is not None:
        optional_params["stream_options"] = stream_options
    if suffix is not None:
        optional_params["suffix"] = suffix
    if temperature is not None:
        optional_params["temperature"] = temperature
    if top_p is not None:
        optional_params["top_p"] = top_p
    if user is not None:
        optional_params["user"] = user
    if api_base is not None:
        optional_params["api_base"] = api_base
    if api_version is not None:
        optional_params["api_version"] = api_version
    if api_key is not None:
        optional_params["api_key"] = api_key
    if custom_llm_provider is not None:
        optional_params["custom_llm_provider"] = custom_llm_provider

    # get custom_llm_provider
    _model, custom_llm_provider, dynamic_api_key, api_base = get_llm_provider(
        model=model,  # type: ignore
        custom_llm_provider=custom_llm_provider,
        api_base=api_base,
    )

    if custom_llm_provider == "huggingface":
        # if echo == True, for TGI llms we need to set top_n_tokens to 3
        if echo is True:
            # for tgi llms
            if "top_n_tokens" not in kwargs:
                kwargs["top_n_tokens"] = 3

        # processing prompt - users can pass raw tokens to OpenAI Completion()
        if isinstance(prompt, list):
            import concurrent.futures

            tokenizer = tiktoken.encoding_for_model("text-davinci-003")
            ## if it's a 2d list - each element in the list is a text_completion() request
            if len(prompt) > 0 and isinstance(prompt[0], list):
                responses = [None for x in prompt]  # init responses

                def process_prompt(i, individual_prompt):
                    decoded_prompt = tokenizer.decode(individual_prompt)
                    all_params = {**kwargs, **optional_params}
                    response: TextCompletionResponse = text_completion(  # type: ignore
                        model=model,
                        prompt=decoded_prompt,
                        num_retries=3,  # ensure this does not fail for the batch
                        *args,
                        **all_params,
                    )

                    text_completion_response["id"] = response.get("id", None)
                    text_completion_response["object"] = "text_completion"
                    text_completion_response["created"] = response.get("created", None)
                    text_completion_response["model"] = response.get("model", None)
                    return response["choices"][0]

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    completed_futures = [
                        executor.submit(process_prompt, i, individual_prompt)
                        for i, individual_prompt in enumerate(prompt)
                    ]
                    for i, future in enumerate(
                        concurrent.futures.as_completed(completed_futures)
                    ):
                        responses[i] = future.result()
                    text_completion_response.choices = responses  # type: ignore

                return text_completion_response
    # else:
    # check if non default values passed in for best_of, echo, logprobs, suffix
    # these are the params supported by Completion() but not ChatCompletion

    # default case, non OpenAI requests go through here
    # handle prompt formatting if prompt is a string vs. list of strings
    messages = []
    if isinstance(prompt, list) and len(prompt) > 0 and isinstance(prompt[0], str):
        for p in prompt:
            message = {"role": "user", "content": p}
            messages.append(message)
    elif isinstance(prompt, str):
        messages = [{"role": "user", "content": prompt}]
    elif (
        (
            custom_llm_provider == "openai"
            or custom_llm_provider == "azure"
            or custom_llm_provider == "azure_text"
            or custom_llm_provider == "text-completion-codestral"
            or custom_llm_provider == "text-completion-openai"
        )
        and isinstance(prompt, list)
        and len(prompt) > 0
        and isinstance(prompt[0], list)
    ):
        verbose_logger.warning(
            msg="List of lists being passed. If this is for tokens, then it might not work across all models."
        )
        messages = [{"role": "user", "content": prompt}]  # type: ignore
    else:
        raise Exception(
            f"Unmapped prompt format. Your prompt is neither a list of strings nor a string. prompt={prompt}. File an issue - https://github.com/BerriAI/litellm/issues"
        )

    kwargs.pop("prompt", None)

    if _model is not None and (
        custom_llm_provider == "openai"
    ):  # for openai compatible endpoints - e.g. vllm, call the native /v1/completions endpoint for text completion calls
        if _model not in litellm.open_ai_chat_completion_models:
            model = "text-completion-openai/" + _model
            optional_params.pop("custom_llm_provider", None)

    if model is None:
        raise ValueError("model is not set. Set either via 'model' or 'engine' param.")
    kwargs["text_completion"] = True
    response = completion(
        model=model,
        messages=messages,
        *args,
        **kwargs,
        **optional_params,
    )
    if kwargs.get("acompletion", False) is True:
        return response
    if (
        stream is True
        or kwargs.get("stream", False) is True
        or isinstance(response, CustomStreamWrapper)
    ):
        response = TextCompletionStreamWrapper(
            completion_stream=response,
            model=model,
            stream_options=stream_options,
            custom_llm_provider=custom_llm_provider,
        )
        return response
    elif isinstance(response, TextCompletionStreamWrapper):
        return response

    # OpenAI Text / Azure Text will return here
    if isinstance(response, TextCompletionResponse):
        return response

    text_completion_response = (
        litellm.utils.LiteLLMResponseObjectHandler.convert_chat_to_text_completion(
            response=response,
            text_completion_response=text_completion_response,
        )
    )

    return text_completion_response


###### Adapter Completion ################


async def aadapter_completion(
    *, adapter_id: str, **kwargs
) -> Optional[Union[BaseModel, AdapterCompletionStreamWrapper]]:
    """
    Implemented to handle async calls for adapter_completion()
    """
    try:
        translation_obj: Optional[CustomLogger] = None
        for item in litellm.adapters:
            if item["id"] == adapter_id:
                translation_obj = item["adapter"]

        if translation_obj is None:
            raise ValueError(
                "No matching adapter given. Received 'adapter_id'={}, litellm.adapters={}".format(
                    adapter_id, litellm.adapters
                )
            )

        new_kwargs = translation_obj.translate_completion_input_params(kwargs=kwargs)

        response: Union[ModelResponse, CustomStreamWrapper] = await acompletion(**new_kwargs)  # type: ignore
        translated_response: Optional[
            Union[BaseModel, AdapterCompletionStreamWrapper]
        ] = None
        if isinstance(response, ModelResponse):
            translated_response = translation_obj.translate_completion_output_params(
                response=response
            )
        if isinstance(response, CustomStreamWrapper):
            translated_response = (
                translation_obj.translate_completion_output_params_streaming(
                    completion_stream=response
                )
            )

        return translated_response
    except Exception as e:
        raise e


def adapter_completion(
    *, adapter_id: str, **kwargs
) -> Optional[Union[BaseModel, AdapterCompletionStreamWrapper]]:
    translation_obj: Optional[CustomLogger] = None
    for item in litellm.adapters:
        if item["id"] == adapter_id:
            translation_obj = item["adapter"]

    if translation_obj is None:
        raise ValueError(
            "No matching adapter given. Received 'adapter_id'={}, litellm.adapters={}".format(
                adapter_id, litellm.adapters
            )
        )

    new_kwargs = translation_obj.translate_completion_input_params(kwargs=kwargs)

    response: Union[ModelResponse, CustomStreamWrapper] = completion(**new_kwargs)  # type: ignore
    translated_response: Optional[Union[BaseModel, AdapterCompletionStreamWrapper]] = (
        None
    )
    if isinstance(response, ModelResponse):
        translated_response = translation_obj.translate_completion_output_params(
            response=response
        )
    elif isinstance(response, CustomStreamWrapper) or inspect.isgenerator(response):
        translated_response = (
            translation_obj.translate_completion_output_params_streaming(
                completion_stream=response
            )
        )

    return translated_response


##### Moderation #######################


def moderation(
    input: str, model: Optional[str] = None, api_key: Optional[str] = None, **kwargs
) -> OpenAIModerationResponse:
    # only supports open ai for now
    api_key = (
        api_key
        or litellm.api_key
        or litellm.openai_key
        or get_secret_str("OPENAI_API_KEY")
    )

    openai_client = kwargs.get("client", None)
    if openai_client is None:
        openai_client = openai.OpenAI(
            api_key=api_key,
        )

    if model is not None:
        response = openai_client.moderations.create(input=input, model=model)
    else:
        response = openai_client.moderations.create(input=input)

    response_dict: Dict = response.model_dump()
    return litellm.utils.LiteLLMResponseObjectHandler.convert_to_moderation_response(
        response_object=response_dict,
    )


@client
async def amoderation(
    input: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
) -> OpenAIModerationResponse:
    from openai import AsyncOpenAI

    # only supports open ai for now
    api_key = (
        api_key
        or litellm.api_key
        or litellm.openai_key
        or get_secret_str("OPENAI_API_KEY")
    )
    openai_client = kwargs.get("client", None)
    if openai_client is None or not isinstance(openai_client, AsyncOpenAI):
        # call helper to get OpenAI client
        # _get_openai_client maintains in-memory caching logic for OpenAI clients
        _openai_client: AsyncOpenAI = openai_chat_completions._get_openai_client(  # type: ignore
            is_async=True,
            api_key=api_key,
        )
    else:
        _openai_client = openai_client

    optional_params = GenericLiteLLMParams(**kwargs)
    litellm_logging_obj: Optional[LiteLLMLoggingObj] = kwargs.get(
        "litellm_logging_obj", None
    )
    try:
        (
            model,
            custom_llm_provider,
            _dynamic_api_key,
            _dynamic_api_base,
        ) = litellm.get_llm_provider(
            model=model or "",
            custom_llm_provider=custom_llm_provider,
            api_base=optional_params.api_base,
            api_key=optional_params.api_key,
        )
    except litellm.BadRequestError:
        # `model` is optional field for moderation - get_llm_provider will throw BadRequestError if model is not set / not recognized
        pass

    # update litellm_logging_obj with environment variables
    custom_llm_provider = custom_llm_provider or litellm.LlmProviders.OPENAI.value
    if litellm_logging_obj is not None:
        litellm_logging_obj.update_environment_variables(
            model=model,
            user=kwargs.get("user", None),
            optional_params={},
            litellm_params={
                **kwargs,
            },
            custom_llm_provider=custom_llm_provider,
        )

    if model is not None:
        response = await _openai_client.moderations.create(input=input, model=model)
    else:
        response = await _openai_client.moderations.create(input=input)
    response_dict: Dict = response.model_dump()
    return litellm.utils.LiteLLMResponseObjectHandler.convert_to_moderation_response(
        response_object=response_dict,
    )


##### Transcription #######################


@client
async def atranscription(*args, **kwargs) -> TranscriptionResponse:
    """
    Calls openai + azure whisper endpoints.

    Allows router to load balance between them
    """
    loop = asyncio.get_event_loop()
    model = args[0] if len(args) > 0 else kwargs["model"]
    ### PASS ARGS TO Image Generation ###
    kwargs["atranscription"] = True
    custom_llm_provider = None
    try:
        # Use a partial function to pass your keyword arguments
        func = partial(transcription, *args, **kwargs)

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        _, custom_llm_provider, _, _ = get_llm_provider(
            model=model, api_base=kwargs.get("api_base", None)
        )

        # Await normally
        init_response = await loop.run_in_executor(None, func_with_context)
        if isinstance(init_response, dict):
            response = TranscriptionResponse(**init_response)
        elif isinstance(init_response, TranscriptionResponse):  ## CACHING SCENARIO
            response = init_response
        elif asyncio.iscoroutine(init_response):
            response = await init_response  # type: ignore
        else:
            # Call the synchronous function using run_in_executor
            response = await loop.run_in_executor(None, func_with_context)
        if not isinstance(response, TranscriptionResponse):
            raise ValueError(
                f"Invalid response from transcription provider, expected TranscriptionResponse, but got {type(response)}"
            )
        return response
    except Exception as e:
        custom_llm_provider = custom_llm_provider or "openai"
        raise exception_type(
            model=model,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=args,
            extra_kwargs=kwargs,
        )


@client
def transcription(
    model: str,
    file: FileTypes,
    ## OPTIONAL OPENAI PARAMS ##
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    response_format: Optional[
        Literal["json", "text", "srt", "verbose_json", "vtt"]
    ] = None,
    timestamp_granularities: Optional[List[Literal["word", "segment"]]] = None,
    temperature: Optional[int] = None,  # openai defaults this to 0
    ## LITELLM PARAMS ##
    user: Optional[str] = None,
    timeout=600,  # default to 10 minutes
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    api_version: Optional[str] = None,
    max_retries: Optional[int] = None,
    custom_llm_provider=None,
    **kwargs,
) -> Union[TranscriptionResponse, Coroutine[Any, Any, TranscriptionResponse]]:
    """
    Calls openai + azure whisper endpoints.

    Allows router to load balance between them
    """
    litellm_call_id = kwargs.get("litellm_call_id", None)
    proxy_server_request = kwargs.get("proxy_server_request", None)
    model_info = kwargs.get("model_info", None)
    metadata = kwargs.get("metadata", None)
    atranscription = kwargs.get("atranscription", False)
    atranscription = kwargs.get("atranscription", False)
    litellm_logging_obj: LiteLLMLoggingObj = kwargs.get("litellm_logging_obj")  # type: ignore
    extra_headers = kwargs.get("extra_headers", None)
    kwargs.pop("tags", [])
    non_default_params = get_non_default_transcription_params(kwargs)

    client: Optional[
        Union[
            openai.AsyncOpenAI,
            openai.OpenAI,
            openai.AzureOpenAI,
            openai.AsyncAzureOpenAI,
        ]
    ] = kwargs.pop("client", None)

    if litellm_logging_obj:
        litellm_logging_obj.model_call_details["client"] = str(client)

    if max_retries is None:
        max_retries = openai.DEFAULT_MAX_RETRIES

    model_response = litellm.utils.TranscriptionResponse()

    model, custom_llm_provider, dynamic_api_key, api_base = get_llm_provider(
        model=model, custom_llm_provider=custom_llm_provider, api_base=api_base
    )  # type: ignore

    if dynamic_api_key is not None:
        api_key = dynamic_api_key

    optional_params = get_optional_params_transcription(
        model=model,
        language=language,
        prompt=prompt,
        response_format=response_format,
        timestamp_granularities=timestamp_granularities,
        temperature=temperature,
        custom_llm_provider=custom_llm_provider,
        **non_default_params,
    )
    litellm_params_dict = get_litellm_params(**kwargs)

    litellm_logging_obj.update_environment_variables(
        model=model,
        user=user,
        optional_params={},
        litellm_params={
            "litellm_call_id": litellm_call_id,
            "proxy_server_request": proxy_server_request,
            "model_info": model_info,
            "metadata": metadata,
            "preset_cache_key": None,
            "stream_response": {},
            **kwargs,
        },
        custom_llm_provider=custom_llm_provider,
    )

    response: Optional[
        Union[TranscriptionResponse, Coroutine[Any, Any, TranscriptionResponse]]
    ] = None

    provider_config = ProviderConfigManager.get_provider_audio_transcription_config(
        model=model,
        provider=LlmProviders(custom_llm_provider),
    )

    if custom_llm_provider == "azure":
        # azure configs
        api_base = api_base or litellm.api_base or get_secret_str("AZURE_API_BASE")

        api_version = (
            api_version or litellm.api_version or get_secret_str("AZURE_API_VERSION")
        )

        azure_ad_token = kwargs.pop("azure_ad_token", None) or get_secret_str(
            "AZURE_AD_TOKEN"
        )

        api_key = (
            api_key
            or litellm.api_key
            or litellm.azure_key
            or get_secret_str("AZURE_API_KEY")
        )

        optional_params["extra_headers"] = extra_headers

        response = azure_audio_transcriptions.audio_transcriptions(
            model=model,
            audio_file=file,
            optional_params=optional_params,
            model_response=model_response,
            atranscription=atranscription,
            client=client,
            timeout=timeout,
            logging_obj=litellm_logging_obj,
            api_base=api_base,
            api_key=api_key,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            max_retries=max_retries,
            litellm_params=litellm_params_dict,
        )
    elif (
        custom_llm_provider == "openai"
        or custom_llm_provider in litellm.openai_compatible_providers
    ):
        api_base = (
            api_base
            or litellm.api_base
            or get_secret("OPENAI_BASE_URL")
            or get_secret("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        )  # type: ignore
        openai.organization = (
            litellm.organization
            or get_secret("OPENAI_ORGANIZATION")
            or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
        )
        # set API KEY
        api_key = api_key or litellm.api_key or litellm.openai_key or get_secret("OPENAI_API_KEY")  # type: ignore
        response = openai_audio_transcriptions.audio_transcriptions(
            model=model,
            audio_file=file,
            optional_params=optional_params,
            model_response=model_response,
            atranscription=atranscription,
            client=client,
            timeout=timeout,
            logging_obj=litellm_logging_obj,
            max_retries=max_retries,
            api_base=api_base,
            api_key=api_key,
            provider_config=provider_config,
            litellm_params=litellm_params_dict,
        )
    elif custom_llm_provider == "deepgram":
        response = base_llm_http_handler.audio_transcriptions(
            model=model,
            audio_file=file,
            optional_params=optional_params,
            litellm_params=litellm_params_dict,
            model_response=model_response,
            atranscription=atranscription,
            client=(
                client
                if client is not None
                and (
                    isinstance(client, HTTPHandler)
                    or isinstance(client, AsyncHTTPHandler)
                )
                else None
            ),
            timeout=timeout,
            max_retries=max_retries,
            logging_obj=litellm_logging_obj,
            api_base=api_base,
            api_key=api_key,
            custom_llm_provider="deepgram",
            headers={},
            provider_config=provider_config,
        )
    if response is None:
        raise ValueError("Unmapped provider passed in. Unable to get the response.")
    return response


@client
async def aspeech(*args, **kwargs) -> HttpxBinaryResponseContent:
    """
    Calls openai tts endpoints.
    """
    loop = asyncio.get_event_loop()
    model = args[0] if len(args) > 0 else kwargs["model"]
    ### PASS ARGS TO Image Generation ###
    kwargs["aspeech"] = True
    custom_llm_provider = kwargs.get("custom_llm_provider", None)
    try:
        # Use a partial function to pass your keyword arguments
        func = partial(speech, *args, **kwargs)

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        _, custom_llm_provider, _, _ = get_llm_provider(
            model=model, api_base=kwargs.get("api_base", None)
        )

        # Await normally
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            # Call the synchronous function using run_in_executor
            response = await loop.run_in_executor(None, func_with_context)
        return response  # type: ignore
    except Exception as e:
        custom_llm_provider = custom_llm_provider or "openai"
        raise exception_type(
            model=model,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=args,
            extra_kwargs=kwargs,
        )


@client
def speech(  # noqa: PLR0915
    model: str,
    input: str,
    voice: Optional[Union[str, dict]] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    api_version: Optional[str] = None,
    organization: Optional[str] = None,
    project: Optional[str] = None,
    max_retries: Optional[int] = None,
    metadata: Optional[dict] = None,
    timeout: Optional[Union[float, httpx.Timeout]] = None,
    response_format: Optional[str] = None,
    speed: Optional[int] = None,
    instructions: Optional[str] = None,
    client=None,
    headers: Optional[dict] = None,
    custom_llm_provider: Optional[str] = None,
    aspeech: Optional[bool] = None,
    **kwargs,
) -> HttpxBinaryResponseContent:
    user = kwargs.get("user", None)
    litellm_call_id: Optional[str] = kwargs.get("litellm_call_id", None)
    proxy_server_request = kwargs.get("proxy_server_request", None)
    extra_headers = kwargs.get("extra_headers", None)
    model_info = kwargs.get("model_info", None)
    model, custom_llm_provider, dynamic_api_key, api_base = get_llm_provider(
        model=model, custom_llm_provider=custom_llm_provider, api_base=api_base
    )  # type: ignore
    kwargs.pop("tags", [])

    optional_params = {}
    if response_format is not None:
        optional_params["response_format"] = response_format
    if speed is not None:
        optional_params["speed"] = speed  # type: ignore
    if instructions is not None:
        optional_params["instructions"] = instructions
    if timeout is None:
        timeout = litellm.request_timeout

    if max_retries is None:
        max_retries = litellm.num_retries or openai.DEFAULT_MAX_RETRIES
    litellm_params_dict = get_litellm_params(**kwargs)
    logging_obj = kwargs.get("litellm_logging_obj", None)
    logging_obj.update_environment_variables(
        model=model,
        user=user,
        optional_params={},
        litellm_params={
            "litellm_call_id": litellm_call_id,
            "proxy_server_request": proxy_server_request,
            "model_info": model_info,
            "metadata": metadata,
            "preset_cache_key": None,
            "stream_response": {},
            **kwargs,
        },
        custom_llm_provider=custom_llm_provider,
    )
    response: Optional[HttpxBinaryResponseContent] = None
    if (
        custom_llm_provider == "openai"
        or custom_llm_provider in litellm.openai_compatible_providers
    ):
        if voice is None or not (isinstance(voice, str)):
            raise litellm.BadRequestError(
                message="'voice' is required to be passed as a string for OpenAI TTS",
                model=model,
                llm_provider=custom_llm_provider,
            )
        api_base = (
            api_base  # for deepinfra/perplexity/anyscale/groq/friendliai we check in get_llm_provider and pass in the api base from there
            or litellm.api_base
            or get_secret("OPENAI_BASE_URL")
            or get_secret("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        )  # type: ignore
        # set API KEY
        api_key = (
            api_key
            or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
            or litellm.openai_key
            or get_secret("OPENAI_API_KEY")
        )  # type: ignore

        organization = (
            organization
            or litellm.organization
            or get_secret("OPENAI_ORGANIZATION")
            or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
        )  # type: ignore

        project = (
            project
            or litellm.project
            or get_secret("OPENAI_PROJECT")
            or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
        )  # type: ignore

        headers = headers or litellm.headers

        response = openai_chat_completions.audio_speech(
            model=model,
            input=input,
            voice=voice,
            optional_params=optional_params,
            api_key=api_key,
            api_base=api_base,
            organization=organization,
            project=project,
            max_retries=max_retries,
            timeout=timeout,
            client=client,  # pass AsyncOpenAI, OpenAI client
            aspeech=aspeech,
        )
    elif custom_llm_provider == "azure":
        # azure configs
        if voice is None or not (isinstance(voice, str)):
            raise litellm.BadRequestError(
                message="'voice' is required to be passed as a string for Azure TTS",
                model=model,
                llm_provider=custom_llm_provider,
            )
        api_base = api_base or litellm.api_base or get_secret("AZURE_API_BASE")  # type: ignore

        api_version = api_version or litellm.api_version or get_secret("AZURE_API_VERSION")  # type: ignore

        api_key = (
            api_key
            or litellm.api_key
            or litellm.azure_key
            or get_secret("AZURE_OPENAI_API_KEY")
            or get_secret("AZURE_API_KEY")
        )  # type: ignore

        azure_ad_token: Optional[str] = optional_params.get("extra_body", {}).pop(  # type: ignore
            "azure_ad_token", None
        ) or get_secret(
            "AZURE_AD_TOKEN"
        )
        azure_ad_token_provider = kwargs.get("azure_ad_token_provider", None)

        if extra_headers:
            optional_params["extra_headers"] = extra_headers

        response = azure_chat_completions.audio_speech(
            model=model,
            input=input,
            voice=voice,
            optional_params=optional_params,
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            azure_ad_token_provider=azure_ad_token_provider,
            organization=organization,
            max_retries=max_retries,
            timeout=timeout,
            client=client,  # pass AsyncOpenAI, OpenAI client
            aspeech=aspeech,
            litellm_params=litellm_params_dict,
        )
    elif custom_llm_provider == "vertex_ai" or custom_llm_provider == "vertex_ai_beta":
        generic_optional_params = GenericLiteLLMParams(**kwargs)

        api_base = generic_optional_params.api_base or ""
        vertex_ai_project = (
            generic_optional_params.vertex_project
            or litellm.vertex_project
            or get_secret_str("VERTEXAI_PROJECT")
        )
        vertex_ai_location = (
            generic_optional_params.vertex_location
            or litellm.vertex_location
            or get_secret_str("VERTEXAI_LOCATION")
        )
        vertex_credentials = (
            generic_optional_params.vertex_credentials
            or get_secret_str("VERTEXAI_CREDENTIALS")
        )

        if voice is not None and not isinstance(voice, dict):
            raise litellm.BadRequestError(
                message=f"'voice' is required to be passed as a dict for Vertex AI TTS, passed in voice={voice}",
                model=model,
                llm_provider=custom_llm_provider,
            )
        if "gemini" in model:
            from .endpoints.speech.speech_to_completion_bridge.handler import (
                speech_to_completion_bridge_handler,
            )

            return speech_to_completion_bridge_handler.speech(
                model=model,
                input=input,
                voice=voice,
                optional_params=optional_params,
                litellm_params=litellm_params_dict,
                headers=headers or {},
                logging_obj=logging_obj,
                custom_llm_provider=custom_llm_provider,
            )
        response = vertex_text_to_speech.audio_speech(
            _is_async=aspeech,
            vertex_credentials=vertex_credentials,
            vertex_project=vertex_ai_project,
            vertex_location=vertex_ai_location,
            timeout=timeout,
            api_base=api_base,
            model=model,
            input=input,
            voice=voice,
            optional_params=optional_params,
            kwargs=kwargs,
            logging_obj=logging_obj,
        )
    elif custom_llm_provider == "gemini":
        from .endpoints.speech.speech_to_completion_bridge.handler import (
            speech_to_completion_bridge_handler,
        )

        return speech_to_completion_bridge_handler.speech(
            model=model,
            input=input,
            voice=voice,
            optional_params=optional_params,
            litellm_params=litellm_params_dict,
            headers=headers or {},
            logging_obj=logging_obj,
            custom_llm_provider=custom_llm_provider,
        )

    if response is None:
        raise Exception(
            "Unable to map the custom llm provider={} to a known provider={}.".format(
                custom_llm_provider, litellm.provider_list
            )
        )
    return response


##### Health Endpoints #######################


async def ahealth_check_wildcard_models(
    model: str,
    custom_llm_provider: str,
    model_params: dict,
    litellm_logging_obj: Logging,
) -> dict:
    # this is a wildcard model, we need to pick a random model from the provider
    cheapest_models = pick_cheapest_chat_models_from_llm_provider(
        custom_llm_provider=custom_llm_provider, n=3
    )
    if len(cheapest_models) == 0:
        raise Exception(
            f"Unable to health check wildcard model for provider {custom_llm_provider}. Add a model on your config.yaml or contribute here - https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json"
        )
    if len(cheapest_models) > 1:
        fallback_models = cheapest_models[
            1:
        ]  # Pick the last 2 models from the shuffled list
    else:
        fallback_models = None
    model_params["model"] = cheapest_models[0]
    model_params["litellm_logging_obj"] = litellm_logging_obj
    model_params["fallbacks"] = fallback_models
    model_params["max_tokens"] = 1
    await acompletion(**model_params)
    return {}


async def ahealth_check(
    model_params: dict,
    mode: Optional[
        Literal[
            "chat",
            "completion",
            "embedding",
            "audio_speech",
            "audio_transcription",
            "image_generation",
            "batch",
            "rerank",
            "realtime",
        ]
    ] = "chat",
    prompt: Optional[str] = None,
    input: Optional[List] = None,
):
    """
    Support health checks for different providers. Return remaining rate limit, etc.

    Returns:
        {
            "x-ratelimit-remaining-requests": int,
            "x-ratelimit-remaining-tokens": int,
            "x-ms-region": str,
        }
    """
    # Map modes to their corresponding health check calls
    litellm_logging_obj = Logging(
        model="",
        messages=[],
        stream=False,
        call_type="acompletion",
        litellm_call_id="1234",
        start_time=datetime.datetime.now(),
        function_id="1234",
        log_raw_request_response=True,
    )
    try:
        model: Optional[str] = model_params.get("model", None)
        if model is None:
            raise Exception("model not set")

        if model in litellm.model_cost and mode is None:
            mode = litellm.model_cost[model].get("mode")

        model, custom_llm_provider, _, _ = get_llm_provider(model=model)
        if model in litellm.model_cost and mode is None:
            mode = litellm.model_cost[model].get("mode")

        model_params["cache"] = {
            "no-cache": True
        }  # don't used cached responses for making health check calls
        mode = mode or "chat"
        if "*" in model:
            return await ahealth_check_wildcard_models(
                model=model,
                custom_llm_provider=custom_llm_provider,
                model_params=model_params,
                litellm_logging_obj=litellm_logging_obj,
            )
        model_params["litellm_logging_obj"] = litellm_logging_obj

        mode_handlers = {
            "chat": lambda: litellm.acompletion(
                **model_params,
            ),
            "completion": lambda: litellm.atext_completion(
                **_filter_model_params(model_params),
                prompt=prompt or "test",
            ),
            "embedding": lambda: litellm.aembedding(
                **_filter_model_params(model_params),
                input=input or ["test"],
            ),
            "audio_speech": lambda: litellm.aspeech(
                **_filter_model_params(model_params),
                input=prompt or "test",
                voice="alloy",
            ),
            "audio_transcription": lambda: litellm.atranscription(
                **_filter_model_params(model_params),
                file=get_audio_file_for_health_check(),
            ),
            "image_generation": lambda: litellm.aimage_generation(
                **_filter_model_params(model_params),
                prompt=prompt,
            ),
            "rerank": lambda: litellm.arerank(
                **_filter_model_params(model_params),
                query=prompt or "",
                documents=["my sample text"],
            ),
            "realtime": lambda: _realtime_health_check(
                model=model,
                custom_llm_provider=custom_llm_provider,
                api_base=model_params.get("api_base", None),
                api_key=model_params.get("api_key", None),
                api_version=model_params.get("api_version", None),
            ),
        }

        if mode in mode_handlers:
            _response = await mode_handlers[mode]()
            # Only process headers for chat mode
            _response_headers: dict = (
                getattr(_response, "_hidden_params", {}).get("headers", {}) or {}
            )
            return _create_health_check_response(_response_headers)
        else:
            raise Exception(
                f"Mode {mode} not supported. See modes here: https://docs.litellm.ai/docs/proxy/health"
            )
    except Exception as e:
        stack_trace = traceback.format_exc()
        if isinstance(stack_trace, str):
            stack_trace = stack_trace[:1000]

        if mode is None:
            return {
                "error": f"error:{str(e)}. Missing `mode`. Set the `mode` for the model - https://docs.litellm.ai/docs/proxy/health#embedding-models  \nstacktrace: {stack_trace}"
            }

        error_to_return = str(e) + "\nstack trace: " + stack_trace

        raw_request_typed_dict = litellm_logging_obj.model_call_details.get(
            "raw_request_typed_dict"
        )

        return {
            "error": error_to_return,
            "raw_request_typed_dict": raw_request_typed_dict,
        }


####### HELPER FUNCTIONS ################
## Set verbose to true -> ```litellm.set_verbose = True```
def print_verbose(print_statement):
    try:
        verbose_logger.debug(print_statement)
        if litellm.set_verbose:
            print(print_statement)  # noqa
    except Exception:
        pass


def config_completion(**kwargs):
    if litellm.config_path is not None:
        config_args = read_config_args(litellm.config_path)
        # overwrite any args passed in with config args
        return completion(**kwargs, **config_args)
    else:
        raise ValueError(
            "No config path set, please set a config path using `litellm.config_path = 'path/to/config.json'`"
        )


def stream_chunk_builder_text_completion(
    chunks: list, messages: Optional[List] = None
) -> TextCompletionResponse:
    id = chunks[0]["id"]
    object = chunks[0]["object"]
    created = chunks[0]["created"]
    model = chunks[0]["model"]
    system_fingerprint = chunks[0].get("system_fingerprint", None)
    finish_reason = chunks[-1]["choices"][0]["finish_reason"]
    logprobs = chunks[-1]["choices"][0]["logprobs"]

    response = {
        "id": id,
        "object": object,
        "created": created,
        "model": model,
        "system_fingerprint": system_fingerprint,
        "choices": [
            {
                "text": None,
                "index": 0,
                "logprobs": logprobs,
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        },
    }
    content_list = []
    for chunk in chunks:
        choices = chunk["choices"]
        for choice in choices:
            if (
                choice is not None
                and hasattr(choice, "text")
                and choice.get("text") is not None
            ):
                _choice = choice.get("text")
                content_list.append(_choice)

    # Combine the "content" strings into a single string || combine the 'function' strings into a single string
    combined_content = "".join(content_list)

    # Update the "content" field within the response dictionary
    response["choices"][0]["text"] = combined_content

    if len(combined_content) > 0:
        pass
    else:
        pass
    # # Update usage information if needed
    try:
        response["usage"]["prompt_tokens"] = token_counter(
            model=model, messages=messages
        )
    except (
        Exception
    ):  # don't allow this failing to block a complete streaming response from being returned
        print_verbose("token_counter failed, assuming prompt tokens is 0")
        response["usage"]["prompt_tokens"] = 0
    response["usage"]["completion_tokens"] = token_counter(
        model=model,
        text=combined_content,
        count_response_tokens=True,  # count_response_tokens is a Flag to tell token counter this is a response, No need to add extra tokens we do for input messages
    )
    response["usage"]["total_tokens"] = (
        response["usage"]["prompt_tokens"] + response["usage"]["completion_tokens"]
    )
    return TextCompletionResponse(**response)


def stream_chunk_builder(  # noqa: PLR0915
    chunks: list, messages: Optional[list] = None, start_time=None, end_time=None
) -> Optional[Union[ModelResponse, TextCompletionResponse]]:
    try:
        if chunks is None:
            raise litellm.APIError(
                status_code=500,
                message="Error building chunks for logging/streaming usage calculation",
                llm_provider="",
                model="",
            )
        if not chunks:
            return None

        processor = ChunkProcessor(chunks, messages)
        chunks = processor.chunks

        ### BASE-CASE ###
        if len(chunks) == 0:
            return None
        ## Route to the text completion logic
        if isinstance(
            chunks[0]["choices"][0], litellm.utils.TextChoices
        ):  # route to the text completion logic
            return stream_chunk_builder_text_completion(
                chunks=chunks, messages=messages
            )

        model = chunks[0]["model"]
        # Initialize the response dictionary
        response = processor.build_base_response(chunks)

        tool_call_chunks = [
            chunk
            for chunk in chunks
            if len(chunk["choices"]) > 0
            and "tool_calls" in chunk["choices"][0]["delta"]
            and chunk["choices"][0]["delta"]["tool_calls"] is not None
        ]

        if len(tool_call_chunks) > 0:
            tool_calls_list = processor.get_combined_tool_content(tool_call_chunks)
            _choice = cast(Choices, response.choices[0])
            _choice.message.content = None
            _choice.message.tool_calls = tool_calls_list

        function_call_chunks = [
            chunk
            for chunk in chunks
            if len(chunk["choices"]) > 0
            and "function_call" in chunk["choices"][0]["delta"]
            and chunk["choices"][0]["delta"]["function_call"] is not None
        ]

        if len(function_call_chunks) > 0:
            _choice = cast(Choices, response.choices[0])
            _choice.message.content = None
            _choice.message.function_call = (
                processor.get_combined_function_call_content(function_call_chunks)
            )

        content_chunks = [
            chunk
            for chunk in chunks
            if len(chunk["choices"]) > 0
            and "content" in chunk["choices"][0]["delta"]
            and chunk["choices"][0]["delta"]["content"] is not None
        ]

        if len(content_chunks) > 0:
            response["choices"][0]["message"]["content"] = (
                processor.get_combined_content(content_chunks)
            )

        reasoning_chunks = [
            chunk
            for chunk in chunks
            if len(chunk["choices"]) > 0
            and "reasoning_content" in chunk["choices"][0]["delta"]
            and chunk["choices"][0]["delta"]["reasoning_content"] is not None
        ]

        if len(reasoning_chunks) > 0:
            response["choices"][0]["message"]["reasoning_content"] = (
                processor.get_combined_reasoning_content(reasoning_chunks)
            )

        audio_chunks = [
            chunk
            for chunk in chunks
            if len(chunk["choices"]) > 0
            and "audio" in chunk["choices"][0]["delta"]
            and chunk["choices"][0]["delta"]["audio"] is not None
        ]

        if len(audio_chunks) > 0:
            _choice = cast(Choices, response.choices[0])
            _choice.message.audio = processor.get_combined_audio_content(audio_chunks)

        completion_output = get_content_from_model_response(response)

        reasoning_tokens = processor.count_reasoning_tokens(response)

        usage = processor.calculate_usage(
            chunks=chunks,
            model=model,
            completion_output=completion_output,
            messages=messages,
            reasoning_tokens=reasoning_tokens,
        )

        setattr(response, "usage", usage)

        return response
    except Exception as e:
        verbose_logger.exception(
            "litellm.main.py::stream_chunk_builder() - Exception occurred - {}".format(
                str(e)
            )
        )
        raise litellm.APIError(
            status_code=500,
            message="Error building chunks for logging/streaming usage calculation",
            llm_provider="",
            model="",
        )

# === NexusCore/openenv\Lib\site-packages\openai\lib\_parsing\_responses.py ===
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, List, Iterable, cast
from typing_extensions import TypeVar, assert_never

import pydantic

from .._tools import ResponsesPydanticFunctionTool
from ..._types import NotGiven
from ..._utils import is_given
from ..._compat import PYDANTIC_V2, model_parse_json
from ..._models import construct_type_unchecked
from .._pydantic import is_basemodel_type, is_dataclass_like_type
from ._completions import solve_response_format_t, type_to_response_format_param
from ...types.responses import (
    Response,
    ToolParam,
    ParsedContent,
    ParsedResponse,
    FunctionToolParam,
    ParsedResponseOutputItem,
    ParsedResponseOutputText,
    ResponseFunctionToolCall,
    ParsedResponseOutputMessage,
    ResponseFormatTextConfigParam,
    ParsedResponseFunctionToolCall,
)
from ...types.chat.completion_create_params import ResponseFormat

TextFormatT = TypeVar(
    "TextFormatT",
    # if it isn't given then we don't do any parsing
    default=None,
)


def type_to_text_format_param(type_: type) -> ResponseFormatTextConfigParam:
    response_format_dict = type_to_response_format_param(type_)
    assert is_given(response_format_dict)
    response_format_dict = cast(ResponseFormat, response_format_dict)  # pyright: ignore[reportUnnecessaryCast]
    assert response_format_dict["type"] == "json_schema"
    assert "schema" in response_format_dict["json_schema"]

    return {
        "type": "json_schema",
        "strict": True,
        "name": response_format_dict["json_schema"]["name"],
        "schema": response_format_dict["json_schema"]["schema"],
    }


def parse_response(
    *,
    text_format: type[TextFormatT] | NotGiven,
    input_tools: Iterable[ToolParam] | NotGiven | None,
    response: Response | ParsedResponse[object],
) -> ParsedResponse[TextFormatT]:
    solved_t = solve_response_format_t(text_format)
    output_list: List[ParsedResponseOutputItem[TextFormatT]] = []

    for output in response.output:
        if output.type == "message":
            content_list: List[ParsedContent[TextFormatT]] = []
            for item in output.content:
                if item.type != "output_text":
                    content_list.append(item)
                    continue

                content_list.append(
                    construct_type_unchecked(
                        type_=cast(Any, ParsedResponseOutputText)[solved_t],
                        value={
                            **item.to_dict(),
                            "parsed": parse_text(item.text, text_format=text_format),
                        },
                    )
                )

            output_list.append(
                construct_type_unchecked(
                    type_=cast(Any, ParsedResponseOutputMessage)[solved_t],
                    value={
                        **output.to_dict(),
                        "content": content_list,
                    },
                )
            )
        elif output.type == "function_call":
            output_list.append(
                construct_type_unchecked(
                    type_=ParsedResponseFunctionToolCall,
                    value={
                        **output.to_dict(),
                        "parsed_arguments": parse_function_tool_arguments(
                            input_tools=input_tools, function_call=output
                        ),
                    },
                )
            )
        elif (
            output.type == "computer_call"
            or output.type == "file_search_call"
            or output.type == "web_search_call"
            or output.type == "reasoning"
            or output.type == "mcp_call"
            or output.type == "mcp_approval_request"
            or output.type == "image_generation_call"
            or output.type == "code_interpreter_call"
            or output.type == "local_shell_call"
            or output.type == "mcp_list_tools"
            or output.type == "exec"
        ):
            output_list.append(output)
        elif TYPE_CHECKING:  # type: ignore
            assert_never(output)
        else:
            output_list.append(output)

    return cast(
        ParsedResponse[TextFormatT],
        construct_type_unchecked(
            type_=cast(Any, ParsedResponse)[solved_t],
            value={
                **response.to_dict(),
                "output": output_list,
            },
        ),
    )


def parse_text(text: str, text_format: type[TextFormatT] | NotGiven) -> TextFormatT | None:
    if not is_given(text_format):
        return None

    if is_basemodel_type(text_format):
        return cast(TextFormatT, model_parse_json(text_format, text))

    if is_dataclass_like_type(text_format):
        if not PYDANTIC_V2:
            raise TypeError(f"Non BaseModel types are only supported with Pydantic v2 - {text_format}")

        return pydantic.TypeAdapter(text_format).validate_json(text)

    raise TypeError(f"Unable to automatically parse response format type {text_format}")


def get_input_tool_by_name(*, input_tools: Iterable[ToolParam], name: str) -> FunctionToolParam | None:
    for tool in input_tools:
        if tool["type"] == "function" and tool.get("name") == name:
            return tool

    return None


def parse_function_tool_arguments(
    *,
    input_tools: Iterable[ToolParam] | NotGiven | None,
    function_call: ParsedResponseFunctionToolCall | ResponseFunctionToolCall,
) -> object:
    if input_tools is None or not is_given(input_tools):
        return None

    input_tool = get_input_tool_by_name(input_tools=input_tools, name=function_call.name)
    if not input_tool:
        return None

    tool = cast(object, input_tool)
    if isinstance(tool, ResponsesPydanticFunctionTool):
        return model_parse_json(tool.model, function_call.arguments)

    if not input_tool.get("strict"):
        return None

    return json.loads(function_call.arguments)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_lasso_builtins.py ===
"""
    pygments.lexers._lasso_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Built-in Lasso types, traits, methods, and members.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

BUILTINS = {
    'Types': (
        'array',
        'atbegin',
        'boolean',
        'bson_iter',
        'bson',
        'bytes_document_body',
        'bytes',
        'cache_server_element',
        'cache_server',
        'capture',
        'client_address',
        'client_ip',
        'component_container',
        'component_render_state',
        'component',
        'curl',
        'curltoken',
        'currency',
        'custom',
        'data_document',
        'database_registry',
        'date',
        'dateandtime',
        'dbgp_packet',
        'dbgp_server',
        'debugging_stack',
        'decimal',
        'delve',
        'dir',
        'dirdesc',
        'dns_response',
        'document_base',
        'document_body',
        'document_header',
        'dsinfo',
        'duration',
        'eacher',
        'email_compose',
        'email_parse',
        'email_pop',
        'email_queue_impl_base',
        'email_queue_impl',
        'email_smtp',
        'email_stage_impl_base',
        'email_stage_impl',
        'fastcgi_each_fcgi_param',
        'fastcgi_server',
        'fcgi_record',
        'fcgi_request',
        'file',
        'filedesc',
        'filemaker_datasource',
        'generateforeachkeyed',
        'generateforeachunkeyed',
        'generateseries',
        'hash_map',
        'html_atomic_element',
        'html_attr',
        'html_base',
        'html_binary',
        'html_br',
        'html_cdata',
        'html_container_element',
        'html_div',
        'html_document_body',
        'html_document_head',
        'html_eol',
        'html_fieldset',
        'html_form',
        'html_h1',
        'html_h2',
        'html_h3',
        'html_h4',
        'html_h5',
        'html_h6',
        'html_hr',
        'html_img',
        'html_input',
        'html_json',
        'html_label',
        'html_legend',
        'html_link',
        'html_meta',
        'html_object',
        'html_option',
        'html_raw',
        'html_script',
        'html_select',
        'html_span',
        'html_style',
        'html_table',
        'html_td',
        'html_text',
        'html_th',
        'html_tr',
        'http_document_header',
        'http_document',
        'http_error',
        'http_header_field',
        'http_server_connection_handler_globals',
        'http_server_connection_handler',
        'http_server_request_logger_thread',
        'http_server_web_connection',
        'http_server',
        'image',
        'include_cache',
        'inline_type',
        'integer',
        'java_jnienv',
        'jbyte',
        'jbytearray',
        'jchar',
        'jchararray',
        'jfieldid',
        'jfloat',
        'jint',
        'jmethodid',
        'jobject',
        'jshort',
        'json_decode',
        'json_encode',
        'json_literal',
        'json_object',
        'keyword',
        'lassoapp_compiledsrc_appsource',
        'lassoapp_compiledsrc_fileresource',
        'lassoapp_content_rep_halt',
        'lassoapp_dirsrc_appsource',
        'lassoapp_dirsrc_fileresource',
        'lassoapp_installer',
        'lassoapp_livesrc_appsource',
        'lassoapp_livesrc_fileresource',
        'lassoapp_long_expiring_bytes',
        'lassoapp_manualsrc_appsource',
        'lassoapp_zip_file_server',
        'lassoapp_zipsrc_appsource',
        'lassoapp_zipsrc_fileresource',
        'ldap',
        'library_thread_loader',
        'list_node',
        'list',
        'locale',
        'log_impl_base',
        'log_impl',
        'magick_image',
        'map_node',
        'map',
        'memberstream',
        'memory_session_driver_impl_entry',
        'memory_session_driver_impl',
        'memory_session_driver',
        'mime_reader',
        'mongo_client',
        'mongo_collection',
        'mongo_cursor',
        'mustache_ctx',
        'mysql_session_driver_impl',
        'mysql_session_driver',
        'net_named_pipe',
        'net_tcp_ssl',
        'net_tcp',
        'net_udp_packet',
        'net_udp',
        'null',
        'odbc_session_driver_impl',
        'odbc_session_driver',
        'opaque',
        'os_process',
        'pair_compare',
        'pair',
        'pairup',
        'pdf_barcode',
        'pdf_chunk',
        'pdf_color',
        'pdf_doc',
        'pdf_font',
        'pdf_hyphenator',
        'pdf_image',
        'pdf_list',
        'pdf_paragraph',
        'pdf_phrase',
        'pdf_read',
        'pdf_table',
        'pdf_text',
        'pdf_typebase',
        'percent',
        'portal_impl',
        'queriable_groupby',
        'queriable_grouping',
        'queriable_groupjoin',
        'queriable_join',
        'queriable_orderby',
        'queriable_orderbydescending',
        'queriable_select',
        'queriable_selectmany',
        'queriable_skip',
        'queriable_take',
        'queriable_thenby',
        'queriable_thenbydescending',
        'queriable_where',
        'queue',
        'raw_document_body',
        'regexp',
        'repeat',
        'scientific',
        'security_registry',
        'serialization_element',
        'serialization_object_identity_compare',
        'serialization_reader',
        'serialization_writer_ref',
        'serialization_writer_standin',
        'serialization_writer',
        'session_delete_expired_thread',
        'set',
        'signature',
        'sourcefile',
        'sqlite_column',
        'sqlite_currentrow',
        'sqlite_db',
        'sqlite_results',
        'sqlite_session_driver_impl_entry',
        'sqlite_session_driver_impl',
        'sqlite_session_driver',
        'sqlite_table',
        'sqlite3_stmt',
        'sqlite3',
        'staticarray',
        'string',
        'sys_process',
        'tag',
        'text_document',
        'tie',
        'timeonly',
        'trait',
        'tree_base',
        'tree_node',
        'tree_nullnode',
        'ucal',
        'usgcpu',
        'usgvm',
        'void',
        'web_error_atend',
        'web_node_base',
        'web_node_content_representation_css_specialized',
        'web_node_content_representation_html_specialized',
        'web_node_content_representation_js_specialized',
        'web_node_content_representation_xhr_container',
        'web_node_echo',
        'web_node_root',
        'web_request_impl',
        'web_request',
        'web_response_impl',
        'web_response',
        'web_router',
        'websocket_handler',
        'worker_pool',
        'xml_attr',
        'xml_cdatasection',
        'xml_characterdata',
        'xml_comment',
        'xml_document',
        'xml_documentfragment',
        'xml_documenttype',
        'xml_domimplementation',
        'xml_element',
        'xml_entity',
        'xml_entityreference',
        'xml_namednodemap_attr',
        'xml_namednodemap_ht',
        'xml_namednodemap',
        'xml_node',
        'xml_nodelist',
        'xml_notation',
        'xml_processinginstruction',
        'xml_text',
        'xmlstream',
        'zip_file_impl',
        'zip_file',
        'zip_impl',
        'zip',
    ),
    'Traits': (
        'any',
        'formattingbase',
        'html_attributed',
        'html_element_coreattrs',
        'html_element_eventsattrs',
        'html_element_i18nattrs',
        'lassoapp_capabilities',
        'lassoapp_resource',
        'lassoapp_source',
        'queriable_asstring',
        'session_driver',
        'trait_array',
        'trait_asstring',
        'trait_backcontractible',
        'trait_backended',
        'trait_backexpandable',
        'trait_close',
        'trait_contractible',
        'trait_decompose_assignment',
        'trait_doubleended',
        'trait_each_sub',
        'trait_encodeurl',
        'trait_endedfullymutable',
        'trait_expandable',
        'trait_file',
        'trait_finite',
        'trait_finiteforeach',
        'trait_foreach',
        'trait_foreachtextelement',
        'trait_frontcontractible',
        'trait_frontended',
        'trait_frontexpandable',
        'trait_fullymutable',
        'trait_generator',
        'trait_generatorcentric',
        'trait_hashable',
        'trait_json_serialize',
        'trait_keyed',
        'trait_keyedfinite',
        'trait_keyedforeach',
        'trait_keyedmutable',
        'trait_list',
        'trait_map',
        'trait_net',
        'trait_pathcomponents',
        'trait_positionallykeyed',
        'trait_positionallysearchable',
        'trait_queriable',
        'trait_queriablelambda',
        'trait_readbytes',
        'trait_readstring',
        'trait_scalar',
        'trait_searchable',
        'trait_serializable',
        'trait_setencoding',
        'trait_setoperations',
        'trait_stack',
        'trait_treenode',
        'trait_writebytes',
        'trait_writestring',
        'trait_xml_elementcompat',
        'trait_xml_nodecompat',
        'web_connection',
        'web_node_container',
        'web_node_content_css_specialized',
        'web_node_content_document',
        'web_node_content_html_specialized',
        'web_node_content_js_specialized',
        'web_node_content_json_specialized',
        'web_node_content_representation',
        'web_node_content',
        'web_node_postable',
        'web_node',
    ),
    'Unbound Methods': (
        'abort_clear',
        'abort_now',
        'abort',
        'action_param',
        'action_params',
        'action_statement',
        'admin_authorization',
        'admin_currentgroups',
        'admin_currentuserid',
        'admin_currentusername',
        'admin_getpref',
        'admin_initialize',
        'admin_lassoservicepath',
        'admin_removepref',
        'admin_setpref',
        'admin_userexists',
        'all',
        'auth_admin',
        'auth_check',
        'auth_custom',
        'auth_group',
        'auth_prompt',
        'auth_user',
        'bom_utf16be',
        'bom_utf16le',
        'bom_utf32be',
        'bom_utf32le',
        'bom_utf8',
        'bw',
        'capture_nearestloopabort',
        'capture_nearestloopcontinue',
        'capture_nearestloopcount',
        'checked',
        'cipher_decrypt_private',
        'cipher_decrypt_public',
        'cipher_decrypt',
        'cipher_digest',
        'cipher_encrypt_private',
        'cipher_encrypt_public',
        'cipher_encrypt',
        'cipher_generate_key',
        'cipher_hmac',
        'cipher_keylength',
        'cipher_list',
        'cipher_open',
        'cipher_seal',
        'cipher_sign',
        'cipher_verify',
        'client_addr',
        'client_authorization',
        'client_browser',
        'client_contentlength',
        'client_contenttype',
        'client_cookielist',
        'client_cookies',
        'client_encoding',
        'client_formmethod',
        'client_getargs',
        'client_getparam',
        'client_getparams',
        'client_headers',
        'client_integertoip',
        'client_iptointeger',
        'client_password',
        'client_postargs',
        'client_postparam',
        'client_postparams',
        'client_type',
        'client_url',
        'client_username',
        'cn',
        'column_name',
        'column_names',
        'column_type',
        'column',
        'compress',
        'content_addheader',
        'content_body',
        'content_encoding',
        'content_header',
        'content_replaceheader',
        'content_type',
        'cookie_set',
        'cookie',
        'curl_easy_cleanup',
        'curl_easy_duphandle',
        'curl_easy_getinfo',
        'curl_easy_init',
        'curl_easy_reset',
        'curl_easy_setopt',
        'curl_easy_strerror',
        'curl_getdate',
        'curl_http_version_1_0',
        'curl_http_version_1_1',
        'curl_http_version_none',
        'curl_ipresolve_v4',
        'curl_ipresolve_v6',
        'curl_ipresolve_whatever',
        'curl_multi_perform',
        'curl_multi_result',
        'curl_netrc_ignored',
        'curl_netrc_optional',
        'curl_netrc_required',
        'curl_sslversion_default',
        'curl_sslversion_sslv2',
        'curl_sslversion_sslv3',
        'curl_sslversion_tlsv1',
        'curl_version_asynchdns',
        'curl_version_debug',
        'curl_version_gssnegotiate',
        'curl_version_idn',
        'curl_version_info',
        'curl_version_ipv6',
        'curl_version_kerberos4',
        'curl_version_largefile',
        'curl_version_libz',
        'curl_version_ntlm',
        'curl_version_spnego',
        'curl_version_ssl',
        'curl_version',
        'curlauth_any',
        'curlauth_anysafe',
        'curlauth_basic',
        'curlauth_digest',
        'curlauth_gssnegotiate',
        'curlauth_none',
        'curlauth_ntlm',
        'curle_aborted_by_callback',
        'curle_bad_calling_order',
        'curle_bad_content_encoding',
        'curle_bad_download_resume',
        'curle_bad_function_argument',
        'curle_bad_password_entered',
        'curle_couldnt_connect',
        'curle_couldnt_resolve_host',
        'curle_couldnt_resolve_proxy',
        'curle_failed_init',
        'curle_file_couldnt_read_file',
        'curle_filesize_exceeded',
        'curle_ftp_access_denied',
        'curle_ftp_cant_get_host',
        'curle_ftp_cant_reconnect',
        'curle_ftp_couldnt_get_size',
        'curle_ftp_couldnt_retr_file',
        'curle_ftp_couldnt_set_ascii',
        'curle_ftp_couldnt_set_binary',
        'curle_ftp_couldnt_use_rest',
        'curle_ftp_port_failed',
        'curle_ftp_quote_error',
        'curle_ftp_ssl_failed',
        'curle_ftp_user_password_incorrect',
        'curle_ftp_weird_227_format',
        'curle_ftp_weird_pass_reply',
        'curle_ftp_weird_pasv_reply',
        'curle_ftp_weird_server_reply',
        'curle_ftp_weird_user_reply',
        'curle_ftp_write_error',
        'curle_function_not_found',
        'curle_got_nothing',
        'curle_http_post_error',
        'curle_http_range_error',
        'curle_http_returned_error',
        'curle_interface_failed',
        'curle_ldap_cannot_bind',
        'curle_ldap_invalid_url',
        'curle_ldap_search_failed',
        'curle_library_not_found',
        'curle_login_denied',
        'curle_malformat_user',
        'curle_obsolete',
        'curle_ok',
        'curle_operation_timeouted',
        'curle_out_of_memory',
        'curle_partial_file',
        'curle_read_error',
        'curle_recv_error',
        'curle_send_error',
        'curle_send_fail_rewind',
        'curle_share_in_use',
        'curle_ssl_cacert',
        'curle_ssl_certproblem',
        'curle_ssl_cipher',
        'curle_ssl_connect_error',
        'curle_ssl_engine_initfailed',
        'curle_ssl_engine_notfound',
        'curle_ssl_engine_setfailed',
        'curle_ssl_peer_certificate',
        'curle_telnet_option_syntax',
        'curle_too_many_redirects',
        'curle_unknown_telnet_option',
        'curle_unsupported_protocol',
        'curle_url_malformat_user',
        'curle_url_malformat',
        'curle_write_error',
        'curlftpauth_default',
        'curlftpauth_ssl',
        'curlftpauth_tls',
        'curlftpssl_all',
        'curlftpssl_control',
        'curlftpssl_last',
        'curlftpssl_none',
        'curlftpssl_try',
        'curlinfo_connect_time',
        'curlinfo_content_length_download',
        'curlinfo_content_length_upload',
        'curlinfo_content_type',
        'curlinfo_effective_url',
        'curlinfo_filetime',
        'curlinfo_header_size',
        'curlinfo_http_connectcode',
        'curlinfo_httpauth_avail',
        'curlinfo_namelookup_time',
        'curlinfo_num_connects',
        'curlinfo_os_errno',
        'curlinfo_pretransfer_time',
        'curlinfo_proxyauth_avail',
        'curlinfo_redirect_count',
        'curlinfo_redirect_time',
        'curlinfo_request_size',
        'curlinfo_response_code',
        'curlinfo_size_download',
        'curlinfo_size_upload',
        'curlinfo_speed_download',
        'curlinfo_speed_upload',
        'curlinfo_ssl_engines',
        'curlinfo_ssl_verifyresult',
        'curlinfo_starttransfer_time',
        'curlinfo_total_time',
        'curlmsg_done',
        'curlopt_autoreferer',
        'curlopt_buffersize',
        'curlopt_cainfo',
        'curlopt_capath',
        'curlopt_connecttimeout',
        'curlopt_cookie',
        'curlopt_cookiefile',
        'curlopt_cookiejar',
        'curlopt_cookiesession',
        'curlopt_crlf',
        'curlopt_customrequest',
        'curlopt_dns_use_global_cache',
        'curlopt_egdsocket',
        'curlopt_encoding',
        'curlopt_failonerror',
        'curlopt_filetime',
        'curlopt_followlocation',
        'curlopt_forbid_reuse',
        'curlopt_fresh_connect',
        'curlopt_ftp_account',
        'curlopt_ftp_create_missing_dirs',
        'curlopt_ftp_response_timeout',
        'curlopt_ftp_ssl',
        'curlopt_ftp_use_eprt',
        'curlopt_ftp_use_epsv',
        'curlopt_ftpappend',
        'curlopt_ftplistonly',
        'curlopt_ftpport',
        'curlopt_ftpsslauth',
        'curlopt_header',
        'curlopt_http_version',
        'curlopt_http200aliases',
        'curlopt_httpauth',
        'curlopt_httpget',
        'curlopt_httpheader',
        'curlopt_httppost',
        'curlopt_httpproxytunnel',
        'curlopt_infilesize_large',
        'curlopt_infilesize',
        'curlopt_interface',
        'curlopt_ipresolve',
        'curlopt_krb4level',
        'curlopt_low_speed_limit',
        'curlopt_low_speed_time',
        'curlopt_mail_from',
        'curlopt_mail_rcpt',
        'curlopt_maxconnects',
        'curlopt_maxfilesize_large',
        'curlopt_maxfilesize',
        'curlopt_maxredirs',
        'curlopt_netrc_file',
        'curlopt_netrc',
        'curlopt_nobody',
        'curlopt_noprogress',
        'curlopt_port',
        'curlopt_post',
        'curlopt_postfields',
        'curlopt_postfieldsize_large',
        'curlopt_postfieldsize',
        'curlopt_postquote',
        'curlopt_prequote',
        'curlopt_proxy',
        'curlopt_proxyauth',
        'curlopt_proxyport',
        'curlopt_proxytype',
        'curlopt_proxyuserpwd',
        'curlopt_put',
        'curlopt_quote',
        'curlopt_random_file',
        'curlopt_range',
        'curlopt_readdata',
        'curlopt_referer',
        'curlopt_resume_from_large',
        'curlopt_resume_from',
        'curlopt_ssl_cipher_list',
        'curlopt_ssl_verifyhost',
        'curlopt_ssl_verifypeer',
        'curlopt_sslcert',
        'curlopt_sslcerttype',
        'curlopt_sslengine_default',
        'curlopt_sslengine',
        'curlopt_sslkey',
        'curlopt_sslkeypasswd',
        'curlopt_sslkeytype',
        'curlopt_sslversion',
        'curlopt_tcp_nodelay',
        'curlopt_timecondition',
        'curlopt_timeout',
        'curlopt_timevalue',
        'curlopt_transfertext',
        'curlopt_unrestricted_auth',
        'curlopt_upload',
        'curlopt_url',
        'curlopt_use_ssl',
        'curlopt_useragent',
        'curlopt_userpwd',
        'curlopt_verbose',
        'curlopt_writedata',
        'curlproxy_http',
        'curlproxy_socks4',
        'curlproxy_socks5',
        'database_adddefaultsqlitehost',
        'database_database',
        'database_initialize',
        'database_name',
        'database_qs',
        'database_table_database_tables',
        'database_table_datasource_databases',
        'database_table_datasource_hosts',
        'database_table_datasources',
        'database_table_table_fields',
        'database_util_cleanpath',
        'dbgp_stop_stack_name',
        'debugging_break',
        'debugging_breakpoint_get',
        'debugging_breakpoint_list',
        'debugging_breakpoint_remove',
        'debugging_breakpoint_set',
        'debugging_breakpoint_update',
        'debugging_context_locals',
        'debugging_context_self',
        'debugging_context_vars',
        'debugging_detach',
        'debugging_enabled',
        'debugging_get_context',
        'debugging_get_stack',
        'debugging_run',
        'debugging_step_in',
        'debugging_step_out',
        'debugging_step_over',
        'debugging_stop',
        'debugging_terminate',
        'decimal_random',
        'decompress',
        'decrypt_blowfish',
        'define_atbegin',
        'define_atend',
        'dns_default',
        'dns_lookup',
        'document',
        'email_attachment_mime_type',
        'email_batch',
        'email_digestchallenge',
        'email_digestresponse',
        'email_extract',
        'email_findemails',
        'email_fix_address_list',
        'email_fix_address',
        'email_fs_error_clean',
        'email_immediate',
        'email_initialize',
        'email_merge',
        'email_mxlookup',
        'email_pop_priv_extract',
        'email_pop_priv_quote',
        'email_pop_priv_substring',
        'email_queue',
        'email_result',
        'email_safeemail',
        'email_send',
        'email_status',
        'email_token',
        'email_translatebreakstocrlf',
        'encode_qheader',
        'encoding_iso88591',
        'encoding_utf8',
        'encrypt_blowfish',
        'encrypt_crammd5',
        'encrypt_hmac',
        'encrypt_md5',
        'eol',
        'eq',
        'error_code_aborted',
        'error_code_dividebyzero',
        'error_code_filenotfound',
        'error_code_invalidparameter',
        'error_code_methodnotfound',
        'error_code_networkerror',
        'error_code_noerror',
        'error_code_resnotfound',
        'error_code_runtimeassertion',
        'error_code',
        'error_msg_aborted',
        'error_msg_dividebyzero',
        'error_msg_filenotfound',
        'error_msg_invalidparameter',
        'error_msg_methodnotfound',
        'error_msg_networkerror',
        'error_msg_noerror',
        'error_msg_resnotfound',
        'error_msg_runtimeassertion',
        'error_msg',
        'error_obj',
        'error_pop',
        'error_push',
        'error_reset',
        'error_stack',
        'escape_tag',
        'evdns_resolve_ipv4',
        'evdns_resolve_ipv6',
        'evdns_resolve_reverse_ipv6',
        'evdns_resolve_reverse',
        'ew',
        'fail_if',
        'fail_ifnot',
        'fail_now',
        'fail',
        'failure_clear',
        'fastcgi_createfcgirequest',
        'fastcgi_handlecon',
        'fastcgi_handlereq',
        'fastcgi_initialize',
        'fastcgi_initiate_request',
        'fcgi_abort_request',
        'fcgi_authorize',
        'fcgi_begin_request',
        'fcgi_bodychunksize',
        'fcgi_cant_mpx_conn',
        'fcgi_data',
        'fcgi_end_request',
        'fcgi_filter',
        'fcgi_get_values_result',
        'fcgi_get_values',
        'fcgi_keep_conn',
        'fcgi_makeendrequestbody',
        'fcgi_makestdoutbody',
        'fcgi_max_conns',
        'fcgi_max_reqs',
        'fcgi_mpxs_conns',
        'fcgi_null_request_id',
        'fcgi_overloaded',
        'fcgi_params',
        'fcgi_read_timeout_seconds',
        'fcgi_readparam',
        'fcgi_request_complete',
        'fcgi_responder',
        'fcgi_stderr',
        'fcgi_stdin',
        'fcgi_stdout',
        'fcgi_unknown_role',
        'fcgi_unknown_type',
        'fcgi_version_1',
        'fcgi_x_stdin',
        'field_name',
        'field_names',
        'field',
        'file_copybuffersize',
        'file_defaultencoding',
        'file_forceroot',
        'file_modechar',
        'file_modeline',
        'file_stderr',
        'file_stdin',
        'file_stdout',
        'file_tempfile',
        'filemakerds_initialize',
        'filemakerds',
        'found_count',
        'ft',
        'ftp_deletefile',
        'ftp_getdata',
        'ftp_getfile',
        'ftp_getlisting',
        'ftp_putdata',
        'ftp_putfile',
        'full',
        'generateforeach',
        'gt',
        'gte',
        'handle_failure',
        'handle',
        'hash_primes',
        'html_comment',
        'http_char_colon',
        'http_char_cr',
        'http_char_htab',
        'http_char_lf',
        'http_char_question',
        'http_char_space',
        'http_default_files',
        'http_read_headers',
        'http_read_timeout_secs',
        'http_server_apps_path',
        'http_server_request_logger',
        'if_empty',
        'if_false',
        'if_null',
        'if_true',
        'include_cache_compare',
        'include_currentpath',
        'include_filepath',
        'include_localpath',
        'include_once',
        'include_path',
        'include_raw',
        'include_url',
        'include',
        'includes',
        'inline_colinfo_name_pos',
        'inline_colinfo_type_pos',
        'inline_colinfo_valuelist_pos',
        'inline_columninfo_pos',
        'inline_foundcount_pos',
        'inline_namedget',
        'inline_namedput',
        'inline_resultrows_pos',
        'inline_scopeget',
        'inline_scopepop',
        'inline_scopepush',
        'inline',
        'integer_bitor',
        'integer_random',
        'io_dir_dt_blk',
        'io_dir_dt_chr',
        'io_dir_dt_dir',
        'io_dir_dt_fifo',
        'io_dir_dt_lnk',
        'io_dir_dt_reg',
        'io_dir_dt_sock',
        'io_dir_dt_unknown',
        'io_dir_dt_wht',
        'io_file_access',
        'io_file_chdir',
        'io_file_chmod',
        'io_file_chown',
        'io_file_dirname',
        'io_file_f_dupfd',
        'io_file_f_getfd',
        'io_file_f_getfl',
        'io_file_f_getlk',
        'io_file_f_rdlck',
        'io_file_f_setfd',
        'io_file_f_setfl',
        'io_file_f_setlk',
        'io_file_f_setlkw',
        'io_file_f_test',
        'io_file_f_tlock',
        'io_file_f_ulock',
        'io_file_f_unlck',
        'io_file_f_wrlck',
        'io_file_fd_cloexec',
        'io_file_fioasync',
        'io_file_fioclex',
        'io_file_fiodtype',
        'io_file_fiogetown',
        'io_file_fionbio',
        'io_file_fionclex',
        'io_file_fionread',
        'io_file_fiosetown',
        'io_file_getcwd',
        'io_file_lchown',
        'io_file_link',
        'io_file_lockf',
        'io_file_lstat_atime',
        'io_file_lstat_mode',
        'io_file_lstat_mtime',
        'io_file_lstat_size',
        'io_file_mkdir',
        'io_file_mkfifo',
        'io_file_mkstemp',
        'io_file_o_append',
        'io_file_o_async',
        'io_file_o_creat',
        'io_file_o_excl',
        'io_file_o_exlock',
        'io_file_o_fsync',
        'io_file_o_nofollow',
        'io_file_o_nonblock',
        'io_file_o_rdonly',
        'io_file_o_rdwr',
        'io_file_o_shlock',
        'io_file_o_sync',
        'io_file_o_trunc',
        'io_file_o_wronly',
        'io_file_pipe',
        'io_file_readlink',
        'io_file_realpath',
        'io_file_remove',
        'io_file_rename',
        'io_file_rmdir',
        'io_file_s_ifblk',
        'io_file_s_ifchr',
        'io_file_s_ifdir',
        'io_file_s_ififo',
        'io_file_s_iflnk',
        'io_file_s_ifmt',
        'io_file_s_ifreg',
        'io_file_s_ifsock',
        'io_file_s_irgrp',
        'io_file_s_iroth',
        'io_file_s_irusr',
        'io_file_s_irwxg',
        'io_file_s_irwxo',
        'io_file_s_irwxu',
        'io_file_s_isgid',
        'io_file_s_isuid',
        'io_file_s_isvtx',
        'io_file_s_iwgrp',
        'io_file_s_iwoth',
        'io_file_s_iwusr',
        'io_file_s_ixgrp',
        'io_file_s_ixoth',
        'io_file_s_ixusr',
        'io_file_seek_cur',
        'io_file_seek_end',
        'io_file_seek_set',
        'io_file_stat_atime',
        'io_file_stat_mode',
        'io_file_stat_mtime',
        'io_file_stat_size',
        'io_file_stderr',
        'io_file_stdin',
        'io_file_stdout',
        'io_file_symlink',
        'io_file_tempnam',
        'io_file_truncate',
        'io_file_umask',
        'io_file_unlink',
        'io_net_accept',
        'io_net_af_inet',
        'io_net_af_inet6',
        'io_net_af_unix',
        'io_net_bind',
        'io_net_connect',
        'io_net_getpeername',
        'io_net_getsockname',
        'io_net_ipproto_ip',
        'io_net_ipproto_udp',
        'io_net_listen',
        'io_net_msg_oob',
        'io_net_msg_peek',
        'io_net_msg_waitall',
        'io_net_recv',
        'io_net_recvfrom',
        'io_net_send',
        'io_net_sendto',
        'io_net_shut_rd',
        'io_net_shut_rdwr',
        'io_net_shut_wr',
        'io_net_shutdown',
        'io_net_so_acceptconn',
        'io_net_so_broadcast',
        'io_net_so_debug',
        'io_net_so_dontroute',
        'io_net_so_error',
        'io_net_so_keepalive',
        'io_net_so_linger',
        'io_net_so_oobinline',
        'io_net_so_rcvbuf',
        'io_net_so_rcvlowat',
        'io_net_so_rcvtimeo',
        'io_net_so_reuseaddr',
        'io_net_so_sndbuf',
        'io_net_so_sndlowat',
        'io_net_so_sndtimeo',
        'io_net_so_timestamp',
        'io_net_so_type',
        'io_net_so_useloopback',
        'io_net_sock_dgram',
        'io_net_sock_raw',
        'io_net_sock_rdm',
        'io_net_sock_seqpacket',
        'io_net_sock_stream',
        'io_net_socket',
        'io_net_sol_socket',
        'io_net_ssl_accept',
        'io_net_ssl_begin',
        'io_net_ssl_connect',
        'io_net_ssl_end',
        'io_net_ssl_error',
        'io_net_ssl_errorstring',
        'io_net_ssl_funcerrorstring',
        'io_net_ssl_liberrorstring',
        'io_net_ssl_read',
        'io_net_ssl_reasonerrorstring',
        'io_net_ssl_setacceptstate',
        'io_net_ssl_setconnectstate',
        'io_net_ssl_setverifylocations',
        'io_net_ssl_shutdown',
        'io_net_ssl_usecertificatechainfile',
        'io_net_ssl_useprivatekeyfile',
        'io_net_ssl_write',
        'java_jvm_create',
        'java_jvm_getenv',
        'jdbc_initialize',
        'json_back_slash',
        'json_back_space',
        'json_close_array',
        'json_close_object',
        'json_colon',
        'json_comma',
        'json_consume_array',
        'json_consume_object',
        'json_consume_string',
        'json_consume_token',
        'json_cr',
        'json_debug',
        'json_deserialize',
        'json_e_lower',
        'json_e_upper',
        'json_f_lower',
        'json_form_feed',
        'json_forward_slash',
        'json_lf',
        'json_n_lower',
        'json_negative',
        'json_open_array',
        'json_open_object',
        'json_period',
        'json_positive',
        'json_quote_double',
        'json_rpccall',
        'json_serialize',
        'json_t_lower',
        'json_tab',
        'json_white_space',
        'keycolumn_name',
        'keycolumn_value',
        'keyfield_name',
        'keyfield_value',
        'lasso_currentaction',
        'lasso_errorreporting',
        'lasso_executiontimelimit',
        'lasso_methodexists',
        'lasso_tagexists',
        'lasso_uniqueid',
        'lasso_version',
        'lassoapp_current_app',
        'lassoapp_current_include',
        'lassoapp_do_with_include',
        'lassoapp_exists',
        'lassoapp_find_missing_file',
        'lassoapp_format_mod_date',
        'lassoapp_get_capabilities_name',
        'lassoapp_include_current',
        'lassoapp_include',
        'lassoapp_initialize_db',
        'lassoapp_initialize',
        'lassoapp_invoke_resource',
        'lassoapp_issourcefileextension',
        'lassoapp_link',
        'lassoapp_load_module',
        'lassoapp_mime_get',
        'lassoapp_mime_type_appcache',
        'lassoapp_mime_type_css',
        'lassoapp_mime_type_csv',
        'lassoapp_mime_type_doc',
        'lassoapp_mime_type_docx',
        'lassoapp_mime_type_eof',
        'lassoapp_mime_type_eot',
        'lassoapp_mime_type_gif',
        'lassoapp_mime_type_html',
        'lassoapp_mime_type_ico',
        'lassoapp_mime_type_jpg',
        'lassoapp_mime_type_js',
        'lassoapp_mime_type_lasso',
        'lassoapp_mime_type_map',
        'lassoapp_mime_type_pdf',
        'lassoapp_mime_type_png',
        'lassoapp_mime_type_ppt',
        'lassoapp_mime_type_rss',
        'lassoapp_mime_type_svg',
        'lassoapp_mime_type_swf',
        'lassoapp_mime_type_tif',
        'lassoapp_mime_type_ttf',
        'lassoapp_mime_type_txt',
        'lassoapp_mime_type_woff',
        'lassoapp_mime_type_xaml',
        'lassoapp_mime_type_xap',
        'lassoapp_mime_type_xbap',
        'lassoapp_mime_type_xhr',
        'lassoapp_mime_type_xml',
        'lassoapp_mime_type_zip',
        'lassoapp_path_to_method_name',
        'lassoapp_settingsdb',
        'layout_name',
        'lcapi_datasourceadd',
        'lcapi_datasourcecloseconnection',
        'lcapi_datasourcedelete',
        'lcapi_datasourceduplicate',
        'lcapi_datasourceexecsql',
        'lcapi_datasourcefindall',
        'lcapi_datasourceimage',
        'lcapi_datasourceinfo',
        'lcapi_datasourceinit',
        'lcapi_datasourcematchesname',
        'lcapi_datasourcenames',
        'lcapi_datasourcenothing',
        'lcapi_datasourceopand',
        'lcapi_datasourceopany',
        'lcapi_datasourceopbw',
        'lcapi_datasourceopct',
        'lcapi_datasourceopeq',
        'lcapi_datasourceopew',
        'lcapi_datasourceopft',
        'lcapi_datasourceopgt',
        'lcapi_datasourceopgteq',
        'lcapi_datasourceopin',
        'lcapi_datasourceoplt',
        'lcapi_datasourceoplteq',
        'lcapi_datasourceopnbw',
        'lcapi_datasourceopnct',
        'lcapi_datasourceopneq',
        'lcapi_datasourceopnew',
        'lcapi_datasourceopnin',
        'lcapi_datasourceopno',
        'lcapi_datasourceopnot',
        'lcapi_datasourceopnrx',
        'lcapi_datasourceopor',
        'lcapi_datasourceoprx',
        'lcapi_datasourcepreparesql',
        'lcapi_datasourceprotectionnone',
        'lcapi_datasourceprotectionreadonly',
        'lcapi_datasourcerandom',
        'lcapi_datasourceschemanames',
        'lcapi_datasourcescripts',
        'lcapi_datasourcesearch',
        'lcapi_datasourcesortascending',
        'lcapi_datasourcesortcustom',
        'lcapi_datasourcesortdescending',
        'lcapi_datasourcetablenames',
        'lcapi_datasourceterm',
        'lcapi_datasourcetickle',
        'lcapi_datasourcetypeblob',
        'lcapi_datasourcetypeboolean',
        'lcapi_datasourcetypedate',
        'lcapi_datasourcetypedecimal',
        'lcapi_datasourcetypeinteger',
        'lcapi_datasourcetypestring',
        'lcapi_datasourceunpreparesql',
        'lcapi_datasourceupdate',
        'lcapi_fourchartointeger',
        'lcapi_listdatasources',
        'lcapi_loadmodule',
        'lcapi_loadmodules',
        'lcapi_updatedatasourceslist',
        'ldap_scope_base',
        'ldap_scope_children',
        'ldap_scope_onelevel',
        'ldap_scope_subtree',
        'library_once',
        'library',
        'ljapi_initialize',
        'locale_availablelocales',
        'locale_canada',
        'locale_canadafrench',
        'locale_china',
        'locale_chinese',
        'locale_default',
        'locale_english',
        'locale_format_style_date_time',
        'locale_format_style_default',
        'locale_format_style_full',
        'locale_format_style_long',
        'locale_format_style_medium',
        'locale_format_style_none',
        'locale_format_style_short',
        'locale_format',
        'locale_france',
        'locale_french',
        'locale_german',
        'locale_germany',
        'locale_isocountries',
        'locale_isolanguages',
        'locale_italian',
        'locale_italy',
        'locale_japan',
        'locale_japanese',
        'locale_korea',
        'locale_korean',
        'locale_prc',
        'locale_setdefault',
        'locale_simplifiedchinese',
        'locale_taiwan',
        'locale_traditionalchinese',
        'locale_uk',
        'locale_us',
        'log_always',
        'log_critical',
        'log_deprecated',
        'log_destination_console',
        'log_destination_database',
        'log_destination_file',
        'log_detail',
        'log_initialize',
        'log_level_critical',
        'log_level_deprecated',
        'log_level_detail',
        'log_level_sql',
        'log_level_warning',
        'log_max_file_size',
        'log_setdestination',
        'log_sql',
        'log_trim_file_size',
        'log_warning',
        'log',
        'loop_abort',
        'loop_continue',
        'loop_count',
        'loop_key_pop',
        'loop_key_push',
        'loop_key',
        'loop_pop',
        'loop_push',
        'loop_value_pop',
        'loop_value_push',
        'loop_value',
        'loop',
        'lt',
        'lte',
        'main_thread_only',
        'max',
        'maxrecords_value',
        'median',
        'method_name',
        'micros',
        'millis',
        'min',
        'minimal',
        'mongo_insert_continue_on_error',
        'mongo_insert_no_validate',
        'mongo_insert_none',
        'mongo_query_await_data',
        'mongo_query_exhaust',
        'mongo_query_no_cursor_timeout',
        'mongo_query_none',
        'mongo_query_oplog_replay',
        'mongo_query_partial',
        'mongo_query_slave_ok',
        'mongo_query_tailable_cursor',
        'mongo_remove_none',
        'mongo_remove_single_remove',
        'mongo_update_multi_update',
        'mongo_update_no_validate',
        'mongo_update_none',
        'mongo_update_upsert',
        'mustache_compile_file',
        'mustache_compile_string',
        'mustache_include',
        'mysqlds',
        'namespace_global',
        'namespace_import',
        'namespace_using',
        'nbw',
        'ncn',
        'neq',
        'net_connectinprogress',
        'net_connectok',
        'net_typessl',
        'net_typessltcp',
        'net_typessludp',
        'net_typetcp',
        'net_typeudp',
        'net_waitread',
        'net_waittimeout',
        'net_waitwrite',
        'new',
        'none',
        'nrx',
        'nslookup',
        'odbc_session_driver_mssql',
        'odbc',
        'output_none',
        'output',
        'pdf_package',
        'pdf_rectangle',
        'pdf_serve',
        'pi',
        'portal',
        'postgresql',
        'process',
        'protect_now',
        'protect',
        'queriable_average',
        'queriable_defaultcompare',
        'queriable_do',
        'queriable_internal_combinebindings',
        'queriable_max',
        'queriable_min',
        'queriable_qsort',
        'queriable_reversecompare',
        'queriable_sum',
        'random_seed',
        'range',
        'records_array',
        'records_map',
        'records',
        'redirect_url',
        'referer_url',
        'referrer_url',
        'register_thread',
        'register',
        'response_filepath',
        'response_localpath',
        'response_path',
        'response_realm',
        'response_root',
        'resultset_count',
        'resultset',
        'resultsets',
        'rows_array',
        'rows_impl',
        'rows',
        'rx',
        'schema_name',
        'security_database',
        'security_default_realm',
        'security_initialize',
        'security_table_groups',
        'security_table_ug_map',
        'security_table_users',
        'selected',
        'series',
        'server_admin',
        'server_ip',
        'server_name',
        'server_port',
        'server_protocol',
        'server_push',
        'server_signature',
        'server_software',
        'session_abort',
        'session_addvar',
        'session_decorate',
        'session_deleteexpired',
        'session_end',
        'session_getdefaultdriver',
        'session_id',
        'session_initialize',
        'session_removevar',
        'session_result',
        'session_setdefaultdriver',
        'session_start',
        'shown_count',
        'shown_first',
        'shown_last',
        'site_id',
        'site_name',
        'skiprecords_value',
        'sleep',
        'split_thread',
        'sqlite_abort',
        'sqlite_auth',
        'sqlite_blob',
        'sqlite_busy',
        'sqlite_cantopen',
        'sqlite_constraint',
        'sqlite_corrupt',
        'sqlite_createdb',
        'sqlite_done',
        'sqlite_empty',
        'sqlite_error',
        'sqlite_float',
        'sqlite_format',
        'sqlite_full',
        'sqlite_integer',
        'sqlite_internal',
        'sqlite_interrupt',
        'sqlite_ioerr',
        'sqlite_locked',
        'sqlite_mismatch',
        'sqlite_misuse',
        'sqlite_nolfs',
        'sqlite_nomem',
        'sqlite_notadb',
        'sqlite_notfound',
        'sqlite_null',
        'sqlite_ok',
        'sqlite_perm',
        'sqlite_protocol',
        'sqlite_range',
        'sqlite_readonly',
        'sqlite_row',
        'sqlite_schema',
        'sqlite_setsleepmillis',
        'sqlite_setsleeptries',
        'sqlite_text',
        'sqlite_toobig',
        'sqliteconnector',
        'staticarray_join',
        'stdout',
        'stdoutnl',
        'string_validcharset',
        'suspend',
        'sys_appspath',
        'sys_chroot',
        'sys_clock',
        'sys_clockspersec',
        'sys_credits',
        'sys_databasespath',
        'sys_detach_exec',
        'sys_difftime',
        'sys_dll_ext',
        'sys_drand48',
        'sys_environ',
        'sys_eol',
        'sys_erand48',
        'sys_errno',
        'sys_exec_pid_to_os_pid',
        'sys_exec',
        'sys_exit',
        'sys_fork',
        'sys_garbagecollect',
        'sys_getbytessincegc',
        'sys_getchar',
        'sys_getegid',
        'sys_getenv',
        'sys_geteuid',
        'sys_getgid',
        'sys_getgrnam',
        'sys_getheapfreebytes',
        'sys_getheapsize',
        'sys_getlogin',
        'sys_getpid',
        'sys_getppid',
        'sys_getpwnam',
        'sys_getpwuid',
        'sys_getstartclock',
        'sys_getthreadcount',
        'sys_getuid',
        'sys_growheapby',
        'sys_homepath',
        'sys_is_full_path',
        'sys_is_windows',
        'sys_isfullpath',
        'sys_iswindows',
        'sys_iterate',
        'sys_jrand48',
        'sys_kill_exec',
        'sys_kill',
        'sys_lcong48',
        'sys_librariespath',
        'sys_listtraits',
        'sys_listtypes',
        'sys_listunboundmethods',
        'sys_loadlibrary',
        'sys_lrand48',
        'sys_masterhomepath',
        'sys_mrand48',
        'sys_nrand48',
        'sys_pid_exec',
        'sys_pointersize',
        'sys_rand',
        'sys_random',
        'sys_seed48',
        'sys_setenv',
        'sys_setgid',
        'sys_setsid',
        'sys_setuid',
        'sys_sigabrt',
        'sys_sigalrm',
        'sys_sigbus',
        'sys_sigchld',
        'sys_sigcont',
        'sys_sigfpe',
        'sys_sighup',
        'sys_sigill',
        'sys_sigint',
        'sys_sigkill',
        'sys_sigpipe',
        'sys_sigprof',
        'sys_sigquit',
        'sys_sigsegv',
        'sys_sigstop',
        'sys_sigsys',
        'sys_sigterm',
        'sys_sigtrap',
        'sys_sigtstp',
        'sys_sigttin',
        'sys_sigttou',
        'sys_sigurg',
        'sys_sigusr1',
        'sys_sigusr2',
        'sys_sigvtalrm',
        'sys_sigxcpu',
        'sys_sigxfsz',
        'sys_srand',
        'sys_srand48',
        'sys_srandom',
        'sys_strerror',
        'sys_supportpath',
        'sys_test_exec',
        'sys_time',
        'sys_uname',
        'sys_unsetenv',
        'sys_usercapimodulepath',
        'sys_userstartuppath',
        'sys_version',
        'sys_wait_exec',
        'sys_waitpid',
        'sys_wcontinued',
        'sys_while',
        'sys_wnohang',
        'sys_wuntraced',
        'table_name',
        'tag_exists',
        'tag_name',
        'thread_var_get',
        'thread_var_pop',
        'thread_var_push',
        'threadvar_find',
        'threadvar_get',
        'threadvar_set_asrt',
        'threadvar_set',
        'timer',
        'token_value',
        'treemap',
        'u_lb_alphabetic',
        'u_lb_ambiguous',
        'u_lb_break_after',
        'u_lb_break_before',
        'u_lb_break_both',
        'u_lb_break_symbols',
        'u_lb_carriage_return',
        'u_lb_close_punctuation',
        'u_lb_combining_mark',
        'u_lb_complex_context',
        'u_lb_contingent_break',
        'u_lb_exclamation',
        'u_lb_glue',
        'u_lb_h2',
        'u_lb_h3',
        'u_lb_hyphen',
        'u_lb_ideographic',
        'u_lb_infix_numeric',
        'u_lb_inseparable',
        'u_lb_jl',
        'u_lb_jt',
        'u_lb_jv',
        'u_lb_line_feed',
        'u_lb_mandatory_break',
        'u_lb_next_line',
        'u_lb_nonstarter',
        'u_lb_numeric',
        'u_lb_open_punctuation',
        'u_lb_postfix_numeric',
        'u_lb_prefix_numeric',
        'u_lb_quotation',
        'u_lb_space',
        'u_lb_surrogate',
        'u_lb_unknown',
        'u_lb_word_joiner',
        'u_lb_zwspace',
        'u_nt_decimal',
        'u_nt_digit',
        'u_nt_none',
        'u_nt_numeric',
        'u_sb_aterm',
        'u_sb_close',
        'u_sb_format',
        'u_sb_lower',
        'u_sb_numeric',
        'u_sb_oletter',
        'u_sb_other',
        'u_sb_sep',
        'u_sb_sp',
        'u_sb_sterm',
        'u_sb_upper',
        'u_wb_aletter',
        'u_wb_extendnumlet',
        'u_wb_format',
        'u_wb_katakana',
        'u_wb_midletter',
        'u_wb_midnum',
        'u_wb_numeric',
        'u_wb_other',
        'ucal_ampm',
        'ucal_dayofmonth',
        'ucal_dayofweek',
        'ucal_dayofweekinmonth',
        'ucal_dayofyear',
        'ucal_daysinfirstweek',
        'ucal_dowlocal',
        'ucal_dstoffset',
        'ucal_era',
        'ucal_extendedyear',
        'ucal_firstdayofweek',
        'ucal_hour',
        'ucal_hourofday',
        'ucal_julianday',
        'ucal_lenient',
        'ucal_listtimezones',
        'ucal_millisecond',
        'ucal_millisecondsinday',
        'ucal_minute',
        'ucal_month',
        'ucal_second',
        'ucal_weekofmonth',
        'ucal_weekofyear',
        'ucal_year',
        'ucal_yearwoy',
        'ucal_zoneoffset',
        'uchar_age',
        'uchar_alphabetic',
        'uchar_ascii_hex_digit',
        'uchar_bidi_class',
        'uchar_bidi_control',
        'uchar_bidi_mirrored',
        'uchar_bidi_mirroring_glyph',
        'uchar_block',
        'uchar_canonical_combining_class',
        'uchar_case_folding',
        'uchar_case_sensitive',
        'uchar_dash',
        'uchar_decomposition_type',
        'uchar_default_ignorable_code_point',
        'uchar_deprecated',
        'uchar_diacritic',
        'uchar_east_asian_width',
        'uchar_extender',
        'uchar_full_composition_exclusion',
        'uchar_general_category_mask',
        'uchar_general_category',
        'uchar_grapheme_base',
        'uchar_grapheme_cluster_break',
        'uchar_grapheme_extend',
        'uchar_grapheme_link',
        'uchar_hangul_syllable_type',
        'uchar_hex_digit',
        'uchar_hyphen',
        'uchar_id_continue',
        'uchar_ideographic',
        'uchar_ids_binary_operator',
        'uchar_ids_trinary_operator',
        'uchar_iso_comment',
        'uchar_join_control',
        'uchar_joining_group',
        'uchar_joining_type',
        'uchar_lead_canonical_combining_class',
        'uchar_line_break',
        'uchar_logical_order_exception',
        'uchar_lowercase_mapping',
        'uchar_lowercase',
        'uchar_math',
        'uchar_name',
        'uchar_nfc_inert',
        'uchar_nfc_quick_check',
        'uchar_nfd_inert',
        'uchar_nfd_quick_check',
        'uchar_nfkc_inert',
        'uchar_nfkc_quick_check',
        'uchar_nfkd_inert',
        'uchar_nfkd_quick_check',
        'uchar_noncharacter_code_point',
        'uchar_numeric_type',
        'uchar_numeric_value',
        'uchar_pattern_syntax',
        'uchar_pattern_white_space',
        'uchar_posix_alnum',
        'uchar_posix_blank',
        'uchar_posix_graph',
        'uchar_posix_print',
        'uchar_posix_xdigit',
        'uchar_quotation_mark',
        'uchar_radical',
        'uchar_s_term',
        'uchar_script',
        'uchar_segment_starter',
        'uchar_sentence_break',
        'uchar_simple_case_folding',
        'uchar_simple_lowercase_mapping',
        'uchar_simple_titlecase_mapping',
        'uchar_simple_uppercase_mapping',
        'uchar_soft_dotted',
        'uchar_terminal_punctuation',
        'uchar_titlecase_mapping',
        'uchar_trail_canonical_combining_class',
        'uchar_unicode_1_name',
        'uchar_unified_ideograph',
        'uchar_uppercase_mapping',
        'uchar_uppercase',
        'uchar_variation_selector',
        'uchar_white_space',
        'uchar_word_break',
        'uchar_xid_continue',
        'uncompress',
        'usage',
        'uuid_compare',
        'uuid_copy',
        'uuid_generate_random',
        'uuid_generate_time',
        'uuid_generate',
        'uuid_is_null',
        'uuid_parse',
        'uuid_unparse_lower',
        'uuid_unparse_upper',
        'uuid_unparse',
        'value_list',
        'value_listitem',
        'valuelistitem',
        'var_keys',
        'var_values',
        'wap_isenabled',
        'wap_maxbuttons',
        'wap_maxcolumns',
        'wap_maxhorzpixels',
        'wap_maxrows',
        'wap_maxvertpixels',
        'web_handlefcgirequest',
        'web_node_content_representation_css',
        'web_node_content_representation_html',
        'web_node_content_representation_js',
        'web_node_content_representation_xhr',
        'web_node_forpath',
        'web_nodes_initialize',
        'web_nodes_normalizeextension',
        'web_nodes_processcontentnode',
        'web_nodes_requesthandler',
        'web_response_nodesentry',
        'web_router_database',
        'web_router_initialize',
        'websocket_handler_timeout',
        'wexitstatus',
        'wifcontinued',
        'wifexited',
        'wifsignaled',
        'wifstopped',
        'wstopsig',
        'wtermsig',
        'xml_transform',
        'xml',
        'zip_add_dir',
        'zip_add',
        'zip_checkcons',
        'zip_close',
        'zip_cm_bzip2',
        'zip_cm_default',
        'zip_cm_deflate',
        'zip_cm_deflate64',
        'zip_cm_implode',
        'zip_cm_pkware_implode',
        'zip_cm_reduce_1',
        'zip_cm_reduce_2',
        'zip_cm_reduce_3',
        'zip_cm_reduce_4',
        'zip_cm_shrink',
        'zip_cm_store',
        'zip_create',
        'zip_delete',
        'zip_em_3des_112',
        'zip_em_3des_168',
        'zip_em_aes_128',
        'zip_em_aes_192',
        'zip_em_aes_256',
        'zip_em_des',
        'zip_em_none',
        'zip_em_rc2_old',
        'zip_em_rc2',
        'zip_em_rc4',
        'zip_em_trad_pkware',
        'zip_em_unknown',
        'zip_er_changed',
        'zip_er_close',
        'zip_er_compnotsupp',
        'zip_er_crc',
        'zip_er_deleted',
        'zip_er_eof',
        'zip_er_exists',
        'zip_er_incons',
        'zip_er_internal',
        'zip_er_inval',
        'zip_er_memory',
        'zip_er_multidisk',
        'zip_er_noent',
        'zip_er_nozip',
        'zip_er_ok',
        'zip_er_open',
        'zip_er_read',
        'zip_er_remove',
        'zip_er_rename',
        'zip_er_seek',
        'zip_er_tmpopen',
        'zip_er_write',
        'zip_er_zipclosed',
        'zip_er_zlib',
        'zip_error_get_sys_type',
        'zip_error_get',
        'zip_error_to_str',
        'zip_et_none',
        'zip_et_sys',
        'zip_et_zlib',
        'zip_excl',
        'zip_fclose',
        'zip_file_error_get',
        'zip_file_strerror',
        'zip_fl_compressed',
        'zip_fl_nocase',
        'zip_fl_nodir',
        'zip_fl_unchanged',
        'zip_fopen_index',
        'zip_fopen',
        'zip_fread',
        'zip_get_archive_comment',
        'zip_get_file_comment',
        'zip_get_name',
        'zip_get_num_files',
        'zip_name_locate',
        'zip_open',
        'zip_rename',
        'zip_replace',
        'zip_set_archive_comment',
        'zip_set_file_comment',
        'zip_stat_index',
        'zip_stat',
        'zip_strerror',
        'zip_unchange_all',
        'zip_unchange_archive',
        'zip_unchange',
        'zlib_version',
    ),
    'Lasso 8 Tags': (
        '__char',
        '__sync_timestamp__',
        '_admin_addgroup',
        '_admin_adduser',
        '_admin_defaultconnector',
        '_admin_defaultconnectornames',
        '_admin_defaultdatabase',
        '_admin_defaultfield',
        '_admin_defaultgroup',
        '_admin_defaulthost',
        '_admin_defaulttable',
        '_admin_defaultuser',
        '_admin_deleteconnector',
        '_admin_deletedatabase',
        '_admin_deletefield',
        '_admin_deletegroup',
        '_admin_deletehost',
        '_admin_deletetable',
        '_admin_deleteuser',
        '_admin_duplicategroup',
        '_admin_internaldatabase',
        '_admin_listconnectors',
        '_admin_listdatabases',
        '_admin_listfields',
        '_admin_listgroups',
        '_admin_listhosts',
        '_admin_listtables',
        '_admin_listusers',
        '_admin_refreshconnector',
        '_admin_refreshsecurity',
        '_admin_servicepath',
        '_admin_updateconnector',
        '_admin_updatedatabase',
        '_admin_updatefield',
        '_admin_updategroup',
        '_admin_updatehost',
        '_admin_updatetable',
        '_admin_updateuser',
        '_chartfx_activation_string',
        '_chartfx_getchallengestring',
        '_chop_args',
        '_chop_mimes',
        '_client_addr_old',
        '_client_address_old',
        '_client_ip_old',
        '_database_names',
        '_datasource_reload',
        '_date_current',
        '_date_format',
        '_date_msec',
        '_date_parse',
        '_execution_timelimit',
        '_file_chmod',
        '_initialize',
        '_jdbc_acceptsurl',
        '_jdbc_debug',
        '_jdbc_deletehost',
        '_jdbc_driverclasses',
        '_jdbc_driverinfo',
        '_jdbc_metainfo',
        '_jdbc_propertyinfo',
        '_jdbc_setdriver',
        '_lasso_param',
        '_log_helper',
        '_proc_noparam',
        '_proc_withparam',
        '_recursion_limit',
        '_request_param',
        '_security_binaryexpiration',
        '_security_flushcaches',
        '_security_isserialized',
        '_security_serialexpiration',
        '_srand',
        '_strict_literals',
        '_substring',
        '_xmlrpc_exconverter',
        '_xmlrpc_inconverter',
        '_xmlrpc_xmlinconverter',
        'abort',
        'action_addinfo',
        'action_addrecord',
        'action_param',
        'action_params',
        'action_setfoundcount',
        'action_setrecordid',
        'action_settotalcount',
        'action_statement',
        'admin_allowedfileroots',
        'admin_changeuser',
        'admin_createuser',
        'admin_currentgroups',
        'admin_currentuserid',
        'admin_currentusername',
        'admin_getpref',
        'admin_groupassignuser',
        'admin_grouplistusers',
        'admin_groupremoveuser',
        'admin_lassoservicepath',
        'admin_listgroups',
        'admin_refreshlicensing',
        'admin_refreshsecurity',
        'admin_reloaddatasource',
        'admin_removepref',
        'admin_setpref',
        'admin_userexists',
        'admin_userlistgroups',
        'all',
        'and',
        'array',
        'array_iterator',
        'auth',
        'auth_admin',
        'auth_auth',
        'auth_custom',
        'auth_group',
        'auth_prompt',
        'auth_user',
        'base64',
        'bean',
        'bigint',
        'bom_utf16be',
        'bom_utf16le',
        'bom_utf32be',
        'bom_utf32le',
        'bom_utf8',
        'boolean',
        'bw',
        'bytes',
        'cache',
        'cache_delete',
        'cache_empty',
        'cache_exists',
        'cache_fetch',
        'cache_internal',
        'cache_maintenance',
        'cache_object',
        'cache_preferences',
        'cache_store',
        'case',
        'chartfx',
        'chartfx_records',
        'chartfx_serve',
        'checked',
        'choice_list',
        'choice_listitem',
        'choicelistitem',
        'cipher_decrypt',
        'cipher_digest',
        'cipher_encrypt',
        'cipher_hmac',
        'cipher_keylength',
        'cipher_list',
        'click_text',
        'client_addr',
        'client_address',
        'client_authorization',
        'client_browser',
        'client_contentlength',
        'client_contenttype',
        'client_cookielist',
        'client_cookies',
        'client_encoding',
        'client_formmethod',
        'client_getargs',
        'client_getparams',
        'client_headers',
        'client_ip',
        'client_ipfrominteger',
        'client_iptointeger',
        'client_password',
        'client_postargs',
        'client_postparams',
        'client_type',
        'client_url',
        'client_username',
        'cn',
        'column',
        'column_name',
        'column_names',
        'compare_beginswith',
        'compare_contains',
        'compare_endswith',
        'compare_equalto',
        'compare_greaterthan',
        'compare_greaterthanorequals',
        'compare_greaterthanorequls',
        'compare_lessthan',
        'compare_lessthanorequals',
        'compare_notbeginswith',
        'compare_notcontains',
        'compare_notendswith',
        'compare_notequalto',
        'compare_notregexp',
        'compare_regexp',
        'compare_strictequalto',
        'compare_strictnotequalto',
        'compiler_removecacheddoc',
        'compiler_setdefaultparserflags',
        'compress',
        'content_body',
        'content_encoding',
        'content_header',
        'content_type',
        'cookie',
        'cookie_set',
        'curl_ftp_getfile',
        'curl_ftp_getlisting',
        'curl_ftp_putfile',
        'curl_include_url',
        'currency',
        'database_changecolumn',
        'database_changefield',
        'database_createcolumn',
        'database_createfield',
        'database_createtable',
        'database_fmcontainer',
        'database_hostinfo',
        'database_inline',
        'database_name',
        'database_nameitem',
        'database_names',
        'database_realname',
        'database_removecolumn',
        'database_removefield',
        'database_removetable',
        'database_repeating',
        'database_repeating_valueitem',
        'database_repeatingvalueitem',
        'database_schemanameitem',
        'database_schemanames',
        'database_tablecolumn',
        'database_tablenameitem',
        'database_tablenames',
        'datasource_name',
        'datasource_register',
        'date',
        'date__date_current',
        'date__date_format',
        'date__date_msec',
        'date__date_parse',
        'date_add',
        'date_date',
        'date_difference',
        'date_duration',
        'date_format',
        'date_getcurrentdate',
        'date_getday',
        'date_getdayofweek',
        'date_gethour',
        'date_getlocaltimezone',
        'date_getminute',
        'date_getmonth',
        'date_getsecond',
        'date_gettime',
        'date_getyear',
        'date_gmttolocal',
        'date_localtogmt',
        'date_maximum',
        'date_minimum',
        'date_msec',
        'date_setformat',
        'date_subtract',
        'db_layoutnameitem',
        'db_layoutnames',
        'db_nameitem',
        'db_names',
        'db_tablenameitem',
        'db_tablenames',
        'dbi_column_names',
        'dbi_field_names',
        'decimal',
        'decimal_setglobaldefaultprecision',
        'decode_base64',
        'decode_bheader',
        'decode_hex',
        'decode_html',
        'decode_json',
        'decode_qheader',
        'decode_quotedprintable',
        'decode_quotedprintablebytes',
        'decode_url',
        'decode_xml',
        'decompress',
        'decrypt_blowfish',
        'decrypt_blowfish2',
        'default',
        'define_atbegin',
        'define_atend',
        'define_constant',
        'define_prototype',
        'define_tag',
        'define_tagp',
        'define_type',
        'define_typep',
        'deserialize',
        'directory_directorynameitem',
        'directory_lister',
        'directory_nameitem',
        'directorynameitem',
        'dns_default',
        'dns_lookup',
        'dns_response',
        'duration',
        'else',
        'email_batch',
        'email_compose',
        'email_digestchallenge',
        'email_digestresponse',
        'email_extract',
        'email_findemails',
        'email_immediate',
        'email_merge',
        'email_mxerror',
        'email_mxlookup',
        'email_parse',
        'email_pop',
        'email_queue',
        'email_result',
        'email_safeemail',
        'email_send',
        'email_smtp',
        'email_status',
        'email_token',
        'email_translatebreakstocrlf',
        'encode_base64',
        'encode_bheader',
        'encode_break',
        'encode_breaks',
        'encode_crc32',
        'encode_hex',
        'encode_html',
        'encode_htmltoxml',
        'encode_json',
        'encode_qheader',
        'encode_quotedprintable',
        'encode_quotedprintablebytes',
        'encode_set',
        'encode_smart',
        'encode_sql',
        'encode_sql92',
        'encode_stricturl',
        'encode_url',
        'encode_xml',
        'encrypt_blowfish',
        'encrypt_blowfish2',
        'encrypt_crammd5',
        'encrypt_hmac',
        'encrypt_md5',
        'eq',
        'error_adderror',
        'error_code',
        'error_code_aborted',
        'error_code_assert',
        'error_code_bof',
        'error_code_connectioninvalid',
        'error_code_couldnotclosefile',
        'error_code_couldnotcreateoropenfile',
        'error_code_couldnotdeletefile',
        'error_code_couldnotdisposememory',
        'error_code_couldnotlockmemory',
        'error_code_couldnotreadfromfile',
        'error_code_couldnotunlockmemory',
        'error_code_couldnotwritetofile',
        'error_code_criterianotmet',
        'error_code_datasourceerror',
        'error_code_directoryfull',
        'error_code_diskfull',
        'error_code_dividebyzero',
        'error_code_eof',
        'error_code_failure',
        'error_code_fieldrestriction',
        'error_code_file',
        'error_code_filealreadyexists',
        'error_code_filecorrupt',
        'error_code_fileinvalid',
        'error_code_fileinvalidaccessmode',
        'error_code_fileisclosed',
        'error_code_fileisopen',
        'error_code_filelocked',
        'error_code_filenotfound',
        'error_code_fileunlocked',
        'error_code_httpfilenotfound',
        'error_code_illegalinstruction',
        'error_code_illegaluseoffrozeninstance',
        'error_code_invaliddatabase',
        'error_code_invalidfilename',
        'error_code_invalidmemoryobject',
        'error_code_invalidparameter',
        'error_code_invalidpassword',
        'error_code_invalidpathname',
        'error_code_invalidusername',
        'error_code_ioerror',
        'error_code_loopaborted',
        'error_code_memory',
        'error_code_network',
        'error_code_nilpointer',
        'error_code_noerr',
        'error_code_nopermission',
        'error_code_outofmemory',
        'error_code_outofstackspace',
        'error_code_overflow',
        'error_code_postconditionfailed',
        'error_code_preconditionfailed',
        'error_code_resnotfound',
        'error_code_resource',
        'error_code_streamreaderror',
        'error_code_streamwriteerror',
        'error_code_syntaxerror',
        'error_code_tagnotfound',
        'error_code_unknownerror',
        'error_code_varnotfound',
        'error_code_volumedoesnotexist',
        'error_code_webactionnotsupported',
        'error_code_webadderror',
        'error_code_webdeleteerror',
        'error_code_webmodulenotfound',
        'error_code_webnosuchobject',
        'error_code_webrepeatingrelatedfield',
        'error_code_webrequiredfieldmissing',
        'error_code_webtimeout',
        'error_code_webupdateerror',
        'error_columnrestriction',
        'error_currenterror',
        'error_databaseconnectionunavailable',
        'error_databasetimeout',
        'error_deleteerror',
        'error_fieldrestriction',
        'error_filenotfound',
        'error_invaliddatabase',
        'error_invalidpassword',
        'error_invalidusername',
        'error_modulenotfound',
        'error_msg',
        'error_msg_aborted',
        'error_msg_assert',
        'error_msg_bof',
        'error_msg_connectioninvalid',
        'error_msg_couldnotclosefile',
        'error_msg_couldnotcreateoropenfile',
        'error_msg_couldnotdeletefile',
        'error_msg_couldnotdisposememory',
        'error_msg_couldnotlockmemory',
        'error_msg_couldnotreadfromfile',
        'error_msg_couldnotunlockmemory',
        'error_msg_couldnotwritetofile',
        'error_msg_criterianotmet',
        'error_msg_datasourceerror',
        'error_msg_directoryfull',
        'error_msg_diskfull',
        'error_msg_dividebyzero',
        'error_msg_eof',
        'error_msg_failure',
        'error_msg_fieldrestriction',
        'error_msg_file',
        'error_msg_filealreadyexists',
        'error_msg_filecorrupt',
        'error_msg_fileinvalid',
        'error_msg_fileinvalidaccessmode',
        'error_msg_fileisclosed',
        'error_msg_fileisopen',
        'error_msg_filelocked',
        'error_msg_filenotfound',
        'error_msg_fileunlocked',
        'error_msg_httpfilenotfound',
        'error_msg_illegalinstruction',
        'error_msg_illegaluseoffrozeninstance',
        'error_msg_invaliddatabase',
        'error_msg_invalidfilename',
        'error_msg_invalidmemoryobject',
        'error_msg_invalidparameter',
        'error_msg_invalidpassword',
        'error_msg_invalidpathname',
        'error_msg_invalidusername',
        'error_msg_ioerror',
        'error_msg_loopaborted',
        'error_msg_memory',
        'error_msg_network',
        'error_msg_nilpointer',
        'error_msg_noerr',
        'error_msg_nopermission',
        'error_msg_outofmemory',
        'error_msg_outofstackspace',
        'error_msg_overflow',
        'error_msg_postconditionfailed',
        'error_msg_preconditionfailed',
        'error_msg_resnotfound',
        'error_msg_resource',
        'error_msg_streamreaderror',
        'error_msg_streamwriteerror',
        'error_msg_syntaxerror',
        'error_msg_tagnotfound',
        'error_msg_unknownerror',
        'error_msg_varnotfound',
        'error_msg_volumedoesnotexist',
        'error_msg_webactionnotsupported',
        'error_msg_webadderror',
        'error_msg_webdeleteerror',
        'error_msg_webmodulenotfound',
        'error_msg_webnosuchobject',
        'error_msg_webrepeatingrelatedfield',
        'error_msg_webrequiredfieldmissing',
        'error_msg_webtimeout',
        'error_msg_webupdateerror',
        'error_noerror',
        'error_nopermission',
        'error_norecordsfound',
        'error_outofmemory',
        'error_pop',
        'error_push',
        'error_reqcolumnmissing',
        'error_reqfieldmissing',
        'error_requiredcolumnmissing',
        'error_requiredfieldmissing',
        'error_reset',
        'error_seterrorcode',
        'error_seterrormessage',
        'error_updateerror',
        'euro',
        'event_schedule',
        'ew',
        'fail',
        'fail_if',
        'false',
        'field',
        'field_name',
        'field_names',
        'file',
        'file_autoresolvefullpaths',
        'file_chmod',
        'file_control',
        'file_copy',
        'file_create',
        'file_creationdate',
        'file_currenterror',
        'file_delete',
        'file_exists',
        'file_getlinecount',
        'file_getsize',
        'file_isdirectory',
        'file_listdirectory',
        'file_moddate',
        'file_modechar',
        'file_modeline',
        'file_move',
        'file_openread',
        'file_openreadwrite',
        'file_openwrite',
        'file_openwriteappend',
        'file_openwritetruncate',
        'file_probeeol',
        'file_processuploads',
        'file_read',
        'file_readline',
        'file_rename',
        'file_serve',
        'file_setsize',
        'file_stream',
        'file_streamcopy',
        'file_uploads',
        'file_waitread',
        'file_waittimeout',
        'file_waitwrite',
        'file_write',
        'find_soap_ops',
        'form_param',
        'found_count',
        'ft',
        'ftp_getfile',
        'ftp_getlisting',
        'ftp_putfile',
        'full',
        'global',
        'global_defined',
        'global_remove',
        'global_reset',
        'globals',
        'gt',
        'gte',
        'handle',
        'handle_error',
        'header',
        'html_comment',
        'http_getfile',
        'ical_alarm',
        'ical_attribute',
        'ical_calendar',
        'ical_daylight',
        'ical_event',
        'ical_freebusy',
        'ical_item',
        'ical_journal',
        'ical_parse',
        'ical_standard',
        'ical_timezone',
        'ical_todo',
        'if',
        'if_empty',
        'if_false',
        'if_null',
        'if_true',
        'image',
        'image_url',
        'img',
        'include',
        'include_cgi',
        'include_currentpath',
        'include_once',
        'include_raw',
        'include_url',
        'inline',
        'integer',
        'iterate',
        'iterator',
        'java',
        'java_bean',
        'json_records',
        'json_rpccall',
        'keycolumn_name',
        'keycolumn_value',
        'keyfield_name',
        'keyfield_value',
        'lasso_comment',
        'lasso_currentaction',
        'lasso_datasourceis',
        'lasso_datasourceis4d',
        'lasso_datasourceisfilemaker',
        'lasso_datasourceisfilemaker7',
        'lasso_datasourceisfilemaker9',
        'lasso_datasourceisfilemakersa',
        'lasso_datasourceisjdbc',
        'lasso_datasourceislassomysql',
        'lasso_datasourceismysql',
        'lasso_datasourceisodbc',
        'lasso_datasourceisopenbase',
        'lasso_datasourceisoracle',
        'lasso_datasourceispostgresql',
        'lasso_datasourceisspotlight',
        'lasso_datasourceissqlite',
        'lasso_datasourceissqlserver',
        'lasso_datasourcemodulename',
        'lasso_datatype',
        'lasso_disableondemand',
        'lasso_errorreporting',
        'lasso_executiontimelimit',
        'lasso_parser',
        'lasso_process',
        'lasso_sessionid',
        'lasso_siteid',
        'lasso_siteisrunning',
        'lasso_sitename',
        'lasso_siterestart',
        'lasso_sitestart',
        'lasso_sitestop',
        'lasso_tagexists',
        'lasso_tagmodulename',
        'lasso_uniqueid',
        'lasso_updatecheck',
        'lasso_uptime',
        'lasso_version',
        'lassoapp_create',
        'lassoapp_dump',
        'lassoapp_flattendir',
        'lassoapp_getappdata',
        'lassoapp_link',
        'lassoapp_list',
        'lassoapp_process',
        'lassoapp_unitize',
        'layout_name',
        'ldap',
        'ldap_scope_base',
        'ldap_scope_onelevel',
        'ldap_scope_subtree',
        'ldml',
        'ldml_ldml',
        'library',
        'library_once',
        'link',
        'link_currentaction',
        'link_currentactionparams',
        'link_currentactionurl',
        'link_currentgroup',
        'link_currentgroupparams',
        'link_currentgroupurl',
        'link_currentrecord',
        'link_currentrecordparams',
        'link_currentrecordurl',
        'link_currentsearch',
        'link_currentsearchparams',
        'link_currentsearchurl',
        'link_detail',
        'link_detailparams',
        'link_detailurl',
        'link_firstgroup',
        'link_firstgroupparams',
        'link_firstgroupurl',
        'link_firstrecord',
        'link_firstrecordparams',
        'link_firstrecordurl',
        'link_lastgroup',
        'link_lastgroupparams',
        'link_lastgroupurl',
        'link_lastrecord',
        'link_lastrecordparams',
        'link_lastrecordurl',
        'link_nextgroup',
        'link_nextgroupparams',
        'link_nextgroupurl',
        'link_nextrecord',
        'link_nextrecordparams',
        'link_nextrecordurl',
        'link_params',
        'link_prevgroup',
        'link_prevgroupparams',
        'link_prevgroupurl',
        'link_prevrecord',
        'link_prevrecordparams',
        'link_prevrecordurl',
        'link_setformat',
        'link_url',
        'list',
        'list_additem',
        'list_fromlist',
        'list_fromstring',
        'list_getitem',
        'list_itemcount',
        'list_iterator',
        'list_removeitem',
        'list_replaceitem',
        'list_reverseiterator',
        'list_tostring',
        'literal',
        'ljax_end',
        'ljax_hastarget',
        'ljax_include',
        'ljax_start',
        'ljax_target',
        'local',
        'local_defined',
        'local_remove',
        'local_reset',
        'locale_format',
        'locals',
        'log',
        'log_always',
        'log_critical',
        'log_deprecated',
        'log_destination_console',
        'log_destination_database',
        'log_destination_file',
        'log_detail',
        'log_level_critical',
        'log_level_deprecated',
        'log_level_detail',
        'log_level_sql',
        'log_level_warning',
        'log_setdestination',
        'log_sql',
        'log_warning',
        'logicalop_value',
        'logicaloperator_value',
        'loop',
        'loop_abort',
        'loop_continue',
        'loop_count',
        'lt',
        'lte',
        'magick_image',
        'map',
        'map_iterator',
        'match_comparator',
        'match_notrange',
        'match_notregexp',
        'match_range',
        'match_regexp',
        'math_abs',
        'math_acos',
        'math_add',
        'math_asin',
        'math_atan',
        'math_atan2',
        'math_ceil',
        'math_converteuro',
        'math_cos',
        'math_div',
        'math_exp',
        'math_floor',
        'math_internal_rand',
        'math_internal_randmax',
        'math_internal_srand',
        'math_ln',
        'math_log',
        'math_log10',
        'math_max',
        'math_min',
        'math_mod',
        'math_mult',
        'math_pow',
        'math_random',
        'math_range',
        'math_rint',
        'math_roman',
        'math_round',
        'math_sin',
        'math_sqrt',
        'math_sub',
        'math_tan',
        'maxrecords_value',
        'memory_session_driver',
        'mime_type',
        'minimal',
        'misc__srand',
        'misc_randomnumber',
        'misc_roman',
        'misc_valid_creditcard',
        'mysql_session_driver',
        'named_param',
        'namespace_current',
        'namespace_delimiter',
        'namespace_exists',
        'namespace_file_fullpathexists',
        'namespace_global',
        'namespace_import',
        'namespace_load',
        'namespace_page',
        'namespace_unload',
        'namespace_using',
        'neq',
        'net',
        'net_connectinprogress',
        'net_connectok',
        'net_typessl',
        'net_typessltcp',
        'net_typessludp',
        'net_typetcp',
        'net_typeudp',
        'net_waitread',
        'net_waittimeout',
        'net_waitwrite',
        'no_default_output',
        'none',
        'noprocess',
        'not',
        'nrx',
        'nslookup',
        'null',
        'object',
        'once',
        'oneoff',
        'op_logicalvalue',
        'operator_logicalvalue',
        'option',
        'or',
        'os_process',
        'output',
        'output_none',
        'pair',
        'params_up',
        'pdf_barcode',
        'pdf_color',
        'pdf_doc',
        'pdf_font',
        'pdf_image',
        'pdf_list',
        'pdf_read',
        'pdf_serve',
        'pdf_table',
        'pdf_text',
        'percent',
        'portal',
        'postcondition',
        'precondition',
        'prettyprintingnsmap',
        'prettyprintingtypemap',
        'priorityqueue',
        'private',
        'proc_convert',
        'proc_convertbody',
        'proc_convertone',
        'proc_extract',
        'proc_extractone',
        'proc_find',
        'proc_first',
        'proc_foreach',
        'proc_get',
        'proc_join',
        'proc_lasso',
        'proc_last',
        'proc_map_entry',
        'proc_null',
        'proc_regexp',
        'proc_xml',
        'proc_xslt',
        'process',
        'protect',
        'queue',
        'rand',
        'randomnumber',
        'raw',
        'recid_value',
        'record_count',
        'recordcount',
        'recordid_value',
        'records',
        'records_array',
        'records_map',
        'redirect_url',
        'reference',
        'referer',
        'referer_url',
        'referrer',
        'referrer_url',
        'regexp',
        'repeating',
        'repeating_valueitem',
        'repeatingvalueitem',
        'repetition',
        'req_column',
        'req_field',
        'required_column',
        'required_field',
        'response_fileexists',
        'response_filepath',
        'response_localpath',
        'response_path',
        'response_realm',
        'resultset',
        'resultset_count',
        'return',
        'return_value',
        'reverseiterator',
        'roman',
        'row_count',
        'rows',
        'rows_array',
        'run_children',
        'rx',
        'schema_name',
        'scientific',
        'search_args',
        'search_arguments',
        'search_columnitem',
        'search_fielditem',
        'search_operatoritem',
        'search_opitem',
        'search_valueitem',
        'searchfielditem',
        'searchoperatoritem',
        'searchopitem',
        'searchvalueitem',
        'select',
        'selected',
        'self',
        'serialize',
        'series',
        'server_date',
        'server_day',
        'server_ip',
        'server_name',
        'server_port',
        'server_push',
        'server_siteisrunning',
        'server_sitestart',
        'server_sitestop',
        'server_time',
        'session_abort',
        'session_addoutputfilter',
        'session_addvar',
        'session_addvariable',
        'session_deleteexpired',
        'session_driver',
        'session_end',
        'session_id',
        'session_removevar',
        'session_removevariable',
        'session_result',
        'session_setdriver',
        'session_start',
        'set',
        'set_iterator',
        'set_reverseiterator',
        'shown_count',
        'shown_first',
        'shown_last',
        'site_atbegin',
        'site_id',
        'site_name',
        'site_restart',
        'skiprecords_value',
        'sleep',
        'soap_convertpartstopairs',
        'soap_definetag',
        'soap_info',
        'soap_lastrequest',
        'soap_lastresponse',
        'soap_stub',
        'sort_args',
        'sort_arguments',
        'sort_columnitem',
        'sort_fielditem',
        'sort_orderitem',
        'sortcolumnitem',
        'sortfielditem',
        'sortorderitem',
        'sqlite_createdb',
        'sqlite_session_driver',
        'sqlite_setsleepmillis',
        'sqlite_setsleeptries',
        'srand',
        'stack',
        'stock_quote',
        'string',
        'string_charfromname',
        'string_concatenate',
        'string_countfields',
        'string_endswith',
        'string_extract',
        'string_findposition',
        'string_findregexp',
        'string_fordigit',
        'string_getfield',
        'string_getunicodeversion',
        'string_insert',
        'string_isalpha',
        'string_isalphanumeric',
        'string_isdigit',
        'string_ishexdigit',
        'string_islower',
        'string_isnumeric',
        'string_ispunctuation',
        'string_isspace',
        'string_isupper',
        'string_length',
        'string_lowercase',
        'string_remove',
        'string_removeleading',
        'string_removetrailing',
        'string_replace',
        'string_replaceregexp',
        'string_todecimal',
        'string_tointeger',
        'string_uppercase',
        'string_validcharset',
        'table_name',
        'table_realname',
        'tag',
        'tag_name',
        'tags',
        'tags_find',
        'tags_list',
        'tcp_close',
        'tcp_open',
        'tcp_send',
        'tcp_tcp_close',
        'tcp_tcp_open',
        'tcp_tcp_send',
        'thread_abort',
        'thread_atomic',
        'thread_event',
        'thread_exists',
        'thread_getcurrentid',
        'thread_getpriority',
        'thread_info',
        'thread_list',
        'thread_lock',
        'thread_pipe',
        'thread_priority_default',
        'thread_priority_high',
        'thread_priority_low',
        'thread_rwlock',
        'thread_semaphore',
        'thread_setpriority',
        'token_value',
        'total_records',
        'treemap',
        'treemap_iterator',
        'true',
        'url_rewrite',
        'valid_creditcard',
        'valid_date',
        'valid_email',
        'valid_url',
        'value_list',
        'value_listitem',
        'valuelistitem',
        'var',
        'var_defined',
        'var_remove',
        'var_reset',
        'var_set',
        'variable',
        'variable_defined',
        'variable_set',
        'variables',
        'variant_count',
        'vars',
        'wap_isenabled',
        'wap_maxbuttons',
        'wap_maxcolumns',
        'wap_maxhorzpixels',
        'wap_maxrows',
        'wap_maxvertpixels',
        'while',
        'wsdl_extract',
        'wsdl_getbinding',
        'wsdl_getbindingforoperation',
        'wsdl_getbindingoperations',
        'wsdl_getmessagenamed',
        'wsdl_getmessageparts',
        'wsdl_getmessagetriofromporttype',
        'wsdl_getopbodystyle',
        'wsdl_getopbodyuse',
        'wsdl_getoperation',
        'wsdl_getoplocation',
        'wsdl_getopmessagetypes',
        'wsdl_getopsoapaction',
        'wsdl_getportaddress',
        'wsdl_getportsforservice',
        'wsdl_getporttype',
        'wsdl_getporttypeoperation',
        'wsdl_getservicedocumentation',
        'wsdl_getservices',
        'wsdl_gettargetnamespace',
        'wsdl_issoapoperation',
        'wsdl_listoperations',
        'wsdl_maketest',
        'xml',
        'xml_extract',
        'xml_rpc',
        'xml_rpccall',
        'xml_rw',
        'xml_serve',
        'xml_transform',
        'xml_xml',
        'xml_xmlstream',
        'xmlstream',
        'xsd_attribute',
        'xsd_blankarraybase',
        'xsd_blankbase',
        'xsd_buildtype',
        'xsd_cache',
        'xsd_checkcardinality',
        'xsd_continueall',
        'xsd_continueannotation',
        'xsd_continueany',
        'xsd_continueanyattribute',
        'xsd_continueattribute',
        'xsd_continueattributegroup',
        'xsd_continuechoice',
        'xsd_continuecomplexcontent',
        'xsd_continuecomplextype',
        'xsd_continuedocumentation',
        'xsd_continueextension',
        'xsd_continuegroup',
        'xsd_continuekey',
        'xsd_continuelist',
        'xsd_continuerestriction',
        'xsd_continuesequence',
        'xsd_continuesimplecontent',
        'xsd_continuesimpletype',
        'xsd_continueunion',
        'xsd_deserialize',
        'xsd_fullyqualifyname',
        'xsd_generate',
        'xsd_generateblankfromtype',
        'xsd_generateblanksimpletype',
        'xsd_generatetype',
        'xsd_getschematype',
        'xsd_issimpletype',
        'xsd_loadschema',
        'xsd_lookupnamespaceuri',
        'xsd_lookuptype',
        'xsd_processany',
        'xsd_processattribute',
        'xsd_processattributegroup',
        'xsd_processcomplextype',
        'xsd_processelement',
        'xsd_processgroup',
        'xsd_processimport',
        'xsd_processinclude',
        'xsd_processschema',
        'xsd_processsimpletype',
        'xsd_ref',
        'xsd_type',
    )
}
MEMBERS = {
    'Member Methods': (
        'abort',
        'abs',
        'accept_charset',
        'accept',
        'acceptconnections',
        'acceptdeserializedelement',
        'acceptnossl',
        'acceptpost',
        'accesskey',
        'acos',
        'acosh',
        'action',
        'actionparams',
        'active_tick',
        'add',
        'addatend',
        'addattachment',
        'addbarcode',
        'addchapter',
        'addcheckbox',
        'addcolumninfo',
        'addcombobox',
        'addcomment',
        'addcomponent',
        'addcomponents',
        'addcss',
        'adddatabasetable',
        'adddatasource',
        'adddatasourcedatabase',
        'adddatasourcehost',
        'adddir',
        'adddirpath',
        'addendjs',
        'addendjstext',
        'adderror',
        'addfavicon',
        'addfile',
        'addgroup',
        'addheader',
        'addhiddenfield',
        'addhtmlpart',
        'addimage',
        'addjavascript',
        'addjs',
        'addjstext',
        'addlist',
        'addmathfunctions',
        'addmember',
        'addoneheaderline',
        'addpage',
        'addparagraph',
        'addpart',
        'addpasswordfield',
        'addphrase',
        'addpostdispatch',
        'addpredispatch',
        'addradiobutton',
        'addradiogroup',
        'addresetbutton',
        'addrow',
        'addsection',
        'addselectlist',
        'addset',
        'addsubmitbutton',
        'addsubnode',
        'addtable',
        'addtask',
        'addtext',
        'addtextarea',
        'addtextfield',
        'addtextpart',
        'addtobuffer',
        'addtrait',
        'adduser',
        'addusertogroup',
        'addwarning',
        'addzip',
        'allocobject',
        'am',
        'ampm',
        'annotate',
        'answer',
        'apop',
        'append',
        'appendarray',
        'appendarraybegin',
        'appendarrayend',
        'appendbool',
        'appendbytes',
        'appendchar',
        'appendchild',
        'appendcolon',
        'appendcomma',
        'appenddata',
        'appenddatetime',
        'appenddbpointer',
        'appenddecimal',
        'appenddocument',
        'appendimagetolist',
        'appendinteger',
        'appendnowutc',
        'appendnull',
        'appendoid',
        'appendregex',
        'appendreplacement',
        'appendstring',
        'appendtail',
        'appendtime',
        'applyheatcolors',
        'appmessage',
        'appname',
        'appprefix',
        'appstatus',
        'arc',
        'archive',
        'arguments',
        'argumentvalue',
        'asarray',
        'asarraystring',
        'asasync',
        'asbytes',
        'ascopy',
        'ascopydeep',
        'asdecimal',
        'asgenerator',
        'asin',
        'asinh',
        'asinteger',
        'askeyedgenerator',
        'aslazystring',
        'aslist',
        'asraw',
        'asstaticarray',
        'asstring',
        'asstringhex',
        'asstringoct',
        'asxml',
        'atan',
        'atan2',
        'atanh',
        'atend',
        'atends',
        'atime',
        'attributecount',
        'attributes',
        'attrs',
        'auth',
        'authenticate',
        'authorize',
        'autocollectbuffer',
        'average',
        'back',
        'basename',
        'basepaths',
        'baseuri',
        'bcc',
        'beginssl',
        'beginswith',
        'begintls',
        'bestcharset',
        'bind_blob',
        'bind_double',
        'bind_int',
        'bind_null',
        'bind_parameter_index',
        'bind_text',
        'bind',
        'bindcount',
        'bindone',
        'bindparam',
        'bitand',
        'bitclear',
        'bitflip',
        'bitformat',
        'bitnot',
        'bitor',
        'bitset',
        'bitshiftleft',
        'bitshiftright',
        'bittest',
        'bitxor',
        'blur',
        'body',
        'bodybytes',
        'boundary',
        'bptoxml',
        'bptypetostr',
        'bucketnumber',
        'buff',
        'buildquery',
        'businessdaysbetween',
        'by',
        'bytes',
        'cachedappprefix',
        'cachedroot',
        'callboolean',
        'callbooleanmethod',
        'callbytemethod',
        'callcharmethod',
        'calldoublemethod',
        'calledname',
        'callfirst',
        'callfloat',
        'callfloatmethod',
        'callint',
        'callintmethod',
        'calllongmethod',
        'callnonvirtualbooleanmethod',
        'callnonvirtualbytemethod',
        'callnonvirtualcharmethod',
        'callnonvirtualdoublemethod',
        'callnonvirtualfloatmethod',
        'callnonvirtualintmethod',
        'callnonvirtuallongmethod',
        'callnonvirtualobjectmethod',
        'callnonvirtualshortmethod',
        'callnonvirtualvoidmethod',
        'callobject',
        'callobjectmethod',
        'callshortmethod',
        'callsite_col',
        'callsite_file',
        'callsite_line',
        'callstack',
        'callstaticboolean',
        'callstaticbooleanmethod',
        'callstaticbytemethod',
        'callstaticcharmethod',
        'callstaticdoublemethod',
        'callstaticfloatmethod',
        'callstaticint',
        'callstaticintmethod',
        'callstaticlongmethod',
        'callstaticobject',
        'callstaticobjectmethod',
        'callstaticshortmethod',
        'callstaticstring',
        'callstaticvoidmethod',
        'callstring',
        'callvoid',
        'callvoidmethod',
        'cancel',
        'cap',
        'capa',
        'capabilities',
        'capi',
        'cbrt',
        'cc',
        'ceil',
        'chardigitvalue',
        'charname',
        'charset',
        'chartype',
        'checkdebugging',
        'checked',
        'checkuser',
        'childnodes',
        'chk',
        'chmod',
        'choosecolumntype',
        'chown',
        'chunked',
        'circle',
        'class',
        'classid',
        'clear',
        'clonenode',
        'close',
        'closepath',
        'closeprepared',
        'closewrite',
        'code',
        'codebase',
        'codetype',
        'colmap',
        'colorspace',
        'column_blob',
        'column_count',
        'column_decltype',
        'column_double',
        'column_int64',
        'column_name',
        'column_text',
        'column_type',
        'command',
        'comments',
        'compare',
        'comparecodepointorder',
        'componentdelimiter',
        'components',
        'composite',
        'compress',
        'concat',
        'condtoint',
        'configureds',
        'configuredskeys',
        'connect',
        'connection',
        'connectionhandler',
        'connhandler',
        'consume_domain',
        'consume_label',
        'consume_message',
        'consume_rdata',
        'consume_string',
        'contains',
        'content_disposition',
        'content_transfer_encoding',
        'content_type',
        'content',
        'contentlength',
        'contents',
        'contenttype',
        'continuation',
        'continuationpacket',
        'continuationpoint',
        'continuationstack',
        'continue',
        'contrast',
        'conventionaltop',
        'convert',
        'cookie',
        'cookies',
        'cookiesarray',
        'cookiesary',
        'copyto',
        'cos',
        'cosh',
        'count',
        'countkeys',
        'country',
        'countusersbygroup',
        'crc',
        'create',
        'createattribute',
        'createattributens',
        'createcdatasection',
        'createcomment',
        'createdocument',
        'createdocumentfragment',
        'createdocumenttype',
        'createelement',
        'createelementns',
        'createentityreference',
        'createindex',
        'createprocessinginstruction',
        'createtable',
        'createtextnode',
        'criteria',
        'crop',
        'csscontent',
        'curl',
        'current',
        'currentfile',
        'curveto',
        'd',
        'data',
        'databasecolumnnames',
        'databasecolumns',
        'databasemap',
        'databasename',
        'datasourcecolumnnames',
        'datasourcecolumns',
        'datasourcemap',
        'date',
        'day',
        'dayofmonth',
        'dayofweek',
        'dayofweekinmonth',
        'dayofyear',
        'days',
        'daysbetween',
        'db',
        'dbtablestable',
        'debug',
        'declare',
        'decodebase64',
        'decodehex',
        'decodehtml',
        'decodeqp',
        'decodeurl',
        'decodexml',
        'decompose',
        'decomposeassignment',
        'defaultcontentrepresentation',
        'defer',
        'deg2rad',
        'dele',
        'delete',
        'deletedata',
        'deleteglobalref',
        'deletelocalref',
        'delim',
        'depth',
        'dereferencepointer',
        'describe',
        'description',
        'deserialize',
        'detach',
        'detectcharset',
        'didinclude',
        'difference',
        'digit',
        'dir',
        'displaycountry',
        'displaylanguage',
        'displayname',
        'displayscript',
        'displayvariant',
        'div',
        'dns_response',
        'do',
        'doatbegins',
        'doatends',
        'doccomment',
        'doclose',
        'doctype',
        'document',
        'documentelement',
        'documentroot',
        'domainbody',
        'done',
        'dosessions',
        'dowithclose',
        'dowlocal',
        'download',
        'drawtext',
        'drop',
        'dropindex',
        'dsdbtable',
        'dshoststable',
        'dsinfo',
        'dst',
        'dstable',
        'dstoffset',
        'dtdid',
        'dup',
        'dup2',
        'each',
        'eachbyte',
        'eachcharacter',
        'eachchild',
        'eachcomponent',
        'eachdir',
        'eachdirpath',
        'eachdirpathrecursive',
        'eachentry',
        'eachfile',
        'eachfilename',
        'eachfilepath',
        'eachfilepathrecursive',
        'eachkey',
        'eachline',
        'eachlinebreak',
        'eachmatch',
        'eachnode',
        'eachpair',
        'eachpath',
        'eachpathrecursive',
        'eachrow',
        'eachsub',
        'eachword',
        'eachwordbreak',
        'element',
        'eligiblepath',
        'eligiblepaths',
        'encodebase64',
        'encodehex',
        'encodehtml',
        'encodehtmltoxml',
        'encodemd5',
        'encodepassword',
        'encodeqp',
        'encodesql',
        'encodesql92',
        'encodeurl',
        'encodevalue',
        'encodexml',
        'encoding',
        'enctype',
        'end',
        'endjs',
        'endssl',
        'endswith',
        'endtls',
        'enhance',
        'ensurestopped',
        'entities',
        'entry',
        'env',
        'equals',
        'era',
        'erf',
        'erfc',
        'err',
        'errcode',
        'errmsg',
        'error',
        'errors',
        'errstack',
        'escape_member',
        'establisherrorstate',
        'exceptioncheck',
        'exceptionclear',
        'exceptiondescribe',
        'exceptionoccurred',
        'exchange',
        'execinits',
        'execinstalls',
        'execute',
        'executelazy',
        'executenow',
        'exists',
        'exit',
        'exitcode',
        'exp',
        'expire',
        'expireminutes',
        'expiresminutes',
        'expm1',
        'export16bits',
        'export32bits',
        'export64bits',
        'export8bits',
        'exportas',
        'exportbytes',
        'exportfdf',
        'exportpointerbits',
        'exportsigned16bits',
        'exportsigned32bits',
        'exportsigned64bits',
        'exportsigned8bits',
        'exportstring',
        'expose',
        'extendedyear',
        'extensiondelimiter',
        'extensions',
        'extract',
        'extractfast',
        'extractfastone',
        'extractimage',
        'extractone',
        'f',
        'fabs',
        'fail',
        'failnoconnectionhandler',
        'family',
        'fatalerror',
        'fcgireq',
        'fchdir',
        'fchmod',
        'fchown',
        'fd',
        'features',
        'fetchdata',
        'fieldnames',
        'fieldposition',
        'fieldstable',
        'fieldtype',
        'fieldvalue',
        'file',
        'filename',
        'filenames',
        'filequeue',
        'fileuploads',
        'fileuploadsary',
        'filterinputcolumn',
        'finalize',
        'find',
        'findall',
        'findandmodify',
        'findbucket',
        'findcase',
        'findclass',
        'findcount',
        'finddescendant',
        'findfirst',
        'findinclude',
        'findinctx',
        'findindex',
        'findlast',
        'findpattern',
        'findposition',
        'findsymbols',
        'first',
        'firstchild',
        'firstcomponent',
        'firstdayofweek',
        'firstnode',
        'fixformat',
        'flags',
        'fliph',
        'flipv',
        'floor',
        'flush',
        'foldcase',
        'foo',
        'for',
        'forcedrowid',
        'foreach',
        'foreachaccept',
        'foreachbyte',
        'foreachcharacter',
        'foreachchild',
        'foreachday',
        'foreachentry',
        'foreachfile',
        'foreachfilename',
        'foreachkey',
        'foreachline',
        'foreachlinebreak',
        'foreachmatch',
        'foreachnode',
        'foreachpair',
        'foreachpathcomponent',
        'foreachrow',
        'foreachspool',
        'foreachsub',
        'foreachwordbreak',
        'form',
        'format',
        'formatas',
        'formatcontextelement',
        'formatcontextelements',
        'formatnumber',
        'free',
        'frexp',
        'from',
        'fromname',
        'fromport',
        'fromreflectedfield',
        'fromreflectedmethod',
        'front',
        'fsync',
        'ftpdeletefile',
        'ftpgetlisting',
        'ftruncate',
        'fullpath',
        'fx',
        'gamma',
        'gatewayinterface',
        'gen',
        'generatechecksum',
        'get',
        'getabswidth',
        'getalignment',
        'getappsource',
        'getarraylength',
        'getattr',
        'getattribute',
        'getattributenamespace',
        'getattributenode',
        'getattributenodens',
        'getattributens',
        'getbarheight',
        'getbarmultiplier',
        'getbarwidth',
        'getbaseline',
        'getbold',
        'getbooleanarrayelements',
        'getbooleanarrayregion',
        'getbooleanfield',
        'getbordercolor',
        'getborderwidth',
        'getbytearrayelements',
        'getbytearrayregion',
        'getbytefield',
        'getchararrayelements',
        'getchararrayregion',
        'getcharfield',
        'getclass',
        'getcode',
        'getcolor',
        'getcolumn',
        'getcolumncount',
        'getcolumns',
        'getdatabasebyalias',
        'getdatabasebyid',
        'getdatabasebyname',
        'getdatabasehost',
        'getdatabasetable',
        'getdatabasetablebyalias',
        'getdatabasetablebyid',
        'getdatabasetablepart',
        'getdatasource',
        'getdatasourcedatabase',
        'getdatasourcedatabasebyid',
        'getdatasourcehost',
        'getdatasourceid',
        'getdatasourcename',
        'getdefaultstorage',
        'getdoublearrayelements',
        'getdoublearrayregion',
        'getdoublefield',
        'getelementbyid',
        'getelementsbytagname',
        'getelementsbytagnamens',
        'getencoding',
        'getface',
        'getfield',
        'getfieldid',
        'getfile',
        'getfloatarrayelements',
        'getfloatarrayregion',
        'getfloatfield',
        'getfont',
        'getformat',
        'getfullfontname',
        'getgroup',
        'getgroupid',
        'getheader',
        'getheaders',
        'gethostdatabase',
        'gethtmlattr',
        'gethtmlattrstring',
        'getinclude',
        'getintarrayelements',
        'getintarrayregion',
        'getintfield',
        'getisocomment',
        'getitalic',
        'getlasterror',
        'getlcapitype',
        'getlibrary',
        'getlongarrayelements',
        'getlongarrayregion',
        'getlongfield',
        'getmargins',
        'getmethodid',
        'getmode',
        'getnameditem',
        'getnameditemns',
        'getnode',
        'getnumericvalue',
        'getobjectarrayelement',
        'getobjectclass',
        'getobjectfield',
        'getpadding',
        'getpagenumber',
        'getparts',
        'getprefs',
        'getpropertyvalue',
        'getprowcount',
        'getpsfontname',
        'getrange',
        'getrowcount',
        'getset',
        'getshortarrayelements',
        'getshortarrayregion',
        'getshortfield',
        'getsize',
        'getsortfieldspart',
        'getspacing',
        'getstaticbooleanfield',
        'getstaticbytefield',
        'getstaticcharfield',
        'getstaticdoublefield',
        'getstaticfieldid',
        'getstaticfloatfield',
        'getstaticintfield',
        'getstaticlongfield',
        'getstaticmethodid',
        'getstaticobjectfield',
        'getstaticshortfield',
        'getstatus',
        'getstringchars',
        'getstringlength',
        'getstyle',
        'getsupportedencodings',
        'gettablebyid',
        'gettext',
        'gettextalignment',
        'gettextsize',
        'gettrigger',
        'gettype',
        'getunderline',
        'getuniquealiasname',
        'getuser',
        'getuserbykey',
        'getuserid',
        'getversion',
        'getzipfilebytes',
        'givenblock',
        'gmt',
        'gotconnection',
        'gotfileupload',
        'groupby',
        'groupcolumns',
        'groupcount',
        'groupjoin',
        'handlebreakpointget',
        'handlebreakpointlist',
        'handlebreakpointremove',
        'handlebreakpointset',
        'handlebreakpointupdate',
        'handlecontextget',
        'handlecontextnames',
        'handlecontinuation',
        'handledefinitionbody',
        'handledefinitionhead',
        'handledefinitionresource',
        'handledevconnection',
        'handleevalexpired',
        'handlefeatureget',
        'handlefeatureset',
        'handlelassoappcontent',
        'handlelassoappresponse',
        'handlenested',
        'handlenormalconnection',
        'handlepop',
        'handleresource',
        'handlesource',
        'handlestackget',
        'handlestderr',
        'handlestdin',
        'handlestdout',
        'handshake',
        'hasattribute',
        'hasattributens',
        'hasattributes',
        'hasbinaryproperty',
        'haschildnodes',
        'hasexpired',
        'hasfeature',
        'hasfield',
        'hash',
        'hashtmlattr',
        'hasmethod',
        'hastable',
        'hastrailingcomponent',
        'hasvalue',
        'head',
        'header',
        'headerbytes',
        'headers',
        'headersarray',
        'headersmap',
        'height',
        'histogram',
        'home',
        'host',
        'hostcolumnnames',
        'hostcolumnnames2',
        'hostcolumns',
        'hostcolumns2',
        'hostdatasource',
        'hostextra',
        'hostid',
        'hostisdynamic',
        'hostmap',
        'hostmap2',
        'hostname',
        'hostpassword',
        'hostport',
        'hostschema',
        'hosttableencoding',
        'hosttonet16',
        'hosttonet32',
        'hosttonet64',
        'hostusername',
        'hour',
        'hourofampm',
        'hourofday',
        'hoursbetween',
        'href',
        'hreflang',
        'htmlcontent',
        'htmlizestacktrace',
        'htmlizestacktracelink',
        'httpaccept',
        'httpacceptencoding',
        'httpacceptlanguage',
        'httpauthorization',
        'httpcachecontrol',
        'httpconnection',
        'httpcookie',
        'httpequiv',
        'httphost',
        'httpreferer',
        'httpreferrer',
        'httpuseragent',
        'hypot',
        'id',
        'idealinmemory',
        'idle',
        'idmap',
        'ifempty',
        'ifkey',
        'ifnotempty',
        'ifnotkey',
        'ignorecase',
        'ilogb',
        'imgptr',
        'implementation',
        'import16bits',
        'import32bits',
        'import64bits',
        'import8bits',
        'importas',
        'importbytes',
        'importfdf',
        'importnode',
        'importpointer',
        'importstring',
        'in',
        'include',
        'includebytes',
        'includelibrary',
        'includelibraryonce',
        'includeonce',
        'includes',
        'includestack',
        'indaylighttime',
        'index',
        'init',
        'initialize',
        'initrequest',
        'inits',
        'inneroncompare',
        'input',
        'inputcolumns',
        'inputtype',
        'insert',
        'insertback',
        'insertbefore',
        'insertdata',
        'insertfirst',
        'insertfrom',
        'insertfront',
        'insertinternal',
        'insertlast',
        'insertpage',
        'install',
        'installs',
        'integer',
        'internalsubset',
        'interrupt',
        'intersection',
        'inttocond',
        'invoke',
        'invokeautocollect',
        'invokeuntil',
        'invokewhile',
        'ioctl',
        'isa',
        'isalive',
        'isallof',
        'isalnum',
        'isalpha',
        'isanyof',
        'isbase',
        'isblank',
        'iscntrl',
        'isdigit',
        'isdir',
        'isdirectory',
        'isempty',
        'isemptyelement',
        'isfirststep',
        'isfullpath',
        'isgraph',
        'ishttps',
        'isidle',
        'isinstanceof',
        'islink',
        'islower',
        'ismultipart',
        'isnan',
        'isnota',
        'isnotempty',
        'isnothing',
        'iso3country',
        'iso3language',
        'isopen',
        'isprint',
        'ispunct',
        'issameobject',
        'isset',
        'issourcefile',
        'isspace',
        'isssl',
        'issupported',
        'istitle',
        'istruetype',
        'istype',
        'isualphabetic',
        'isulowercase',
        'isupper',
        'isuuppercase',
        'isuwhitespace',
        'isvalid',
        'iswhitespace',
        'isxdigit',
        'isxhr',
        'item',
        'j0',
        'j1',
        'javascript',
        'jbarcode',
        'jcolor',
        'jfont',
        'jimage',
        'jlist',
        'jn',
        'jobjectisa',
        'join',
        'jread',
        'jscontent',
        'jsonfornode',
        'jsonhtml',
        'jsonisleaf',
        'jsonlabel',
        'jtable',
        'jtext',
        'julianday',
        'kernel',
        'key',
        'keycolumns',
        'keys',
        'keywords',
        'kill',
        'label',
        'lang',
        'language',
        'last_insert_rowid',
        'last',
        'lastaccessdate',
        'lastaccesstime',
        'lastchild',
        'lastcomponent',
        'lasterror',
        'lastinsertid',
        'lastnode',
        'lastpoint',
        'lasttouched',
        'lazyvalue',
        'ldexp',
        'leaveopen',
        'left',
        'length',
        'lgamma',
        'line',
        'linediffers',
        'linkto',
        'linktype',
        'list',
        'listactivedatasources',
        'listalldatabases',
        'listalltables',
        'listdatabasetables',
        'listdatasourcedatabases',
        'listdatasourcehosts',
        'listdatasources',
        'listen',
        'listgroups',
        'listgroupsbyuser',
        'listhostdatabases',
        'listhosts',
        'listmethods',
        'listnode',
        'listusers',
        'listusersbygroup',
        'loadcerts',
        'loaddatasourcehostinfo',
        'loaddatasourceinfo',
        'loadlibrary',
        'localaddress',
        'localname',
        'locals',
        'lock',
        'log',
        'log10',
        'log1p',
        'logb',
        'lookupnamespace',
        'lop',
        'lowagiefont',
        'lowercase',
        'makecolor',
        'makecolumnlist',
        'makecolumnmap',
        'makecookieyumyum',
        'makefullpath',
        'makeinheritedcopy',
        'makenonrelative',
        'makeurl',
        'map',
        'marker',
        'matches',
        'matchesstart',
        'matchposition',
        'matchstring',
        'matchtriggers',
        'max',
        'maxinmemory',
        'maxlength',
        'maxrows',
        'maxworkers',
        'maybeslash',
        'maybevalue',
        'md5hex',
        'media',
        'members',
        'merge',
        'meta',
        'method',
        'methodname',
        'millisecond',
        'millisecondsinday',
        'mime_boundary',
        'mime_contenttype',
        'mime_hdrs',
        'mime',
        'mimes',
        'min',
        'minute',
        'minutesbetween',
        'moddatestr',
        'mode',
        'modf',
        'modificationdate',
        'modificationtime',
        'modulate',
        'monitorenter',
        'monitorexit',
        'month',
        'moveto',
        'movetoattribute',
        'movetoattributenamespace',
        'movetoelement',
        'movetofirstattribute',
        'movetonextattribute',
        'msg',
        'mtime',
        'multiple',
        'n',
        'name',
        'named',
        'namespaceuri',
        'needinitialization',
        'net',
        'nettohost16',
        'nettohost32',
        'nettohost64',
        'new',
        'newbooleanarray',
        'newbytearray',
        'newchararray',
        'newdoublearray',
        'newfloatarray',
        'newglobalref',
        'newintarray',
        'newlongarray',
        'newobject',
        'newobjectarray',
        'newshortarray',
        'newstring',
        'next',
        'nextafter',
        'nextnode',
        'nextprime',
        'nextprune',
        'nextprunedelta',
        'nextsibling',
        'nodeforpath',
        'nodelist',
        'nodename',
        'nodetype',
        'nodevalue',
        'noop',
        'normalize',
        'notationname',
        'notations',
        'novaluelists',
        'numsets',
        'object',
        'objects',
        'objecttype',
        'onclick',
        'oncompare',
        'oncomparestrict',
        'onconvert',
        'oncreate',
        'ondblclick',
        'onkeydown',
        'onkeypress',
        'onkeyup',
        'onmousedown',
        'onmousemove',
        'onmouseout',
        'onmouseover',
        'onmouseup',
        'onreset',
        'onsubmit',
        'ontop',
        'open',
        'openappend',
        'openread',
        'opentruncate',
        'openwith',
        'openwrite',
        'openwriteonly',
        'orderby',
        'orderbydescending',
        'out',
        'output',
        'outputencoding',
        'ownerdocument',
        'ownerelement',
        'padleading',
        'padtrailing',
        'padzero',
        'pagecount',
        'pagerotation',
        'pagesize',
        'param',
        'paramdescs',
        'params',
        'parent',
        'parentdir',
        'parentnode',
        'parse_body',
        'parse_boundary',
        'parse_charset',
        'parse_content_disposition',
        'parse_content_transfer_encoding',
        'parse_content_type',
        'parse_hdrs',
        'parse_mode',
        'parse_msg',
        'parse_parts',
        'parse_rawhdrs',
        'parse',
        'parseas',
        'parsedocument',
        'parsenumber',
        'parseoneheaderline',
        'pass',
        'path',
        'pathinfo',
        'pathtouri',
        'pathtranslated',
        'pause',
        'payload',
        'pdifference',
        'perform',
        'performonce',
        'perms',
        'pid',
        'pixel',
        'pm',
        'polldbg',
        'pollide',
        'pop_capa',
        'pop_cmd',
        'pop_debug',
        'pop_err',
        'pop_get',
        'pop_ids',
        'pop_index',
        'pop_log',
        'pop_mode',
        'pop_net',
        'pop_res',
        'pop_server',
        'pop_timeout',
        'pop_token',
        'pop',
        'popctx',
        'popinclude',
        'populate',
        'port',
        'position',
        'postdispatch',
        'postparam',
        'postparams',
        'postparamsary',
        'poststring',
        'pow',
        'predispatch',
        'prefix',
        'preflight',
        'prepare',
        'prepared',
        'pretty',
        'prev',
        'previoussibling',
        'printsimplemsg',
        'private_compare',
        'private_find',
        'private_findlast',
        'private_merge',
        'private_rebalanceforinsert',
        'private_rebalanceforremove',
        'private_replaceall',
        'private_replacefirst',
        'private_rotateleft',
        'private_rotateright',
        'private_setrange',
        'private_split',
        'probemimetype',
        'provides',
        'proxying',
        'prune',
        'publicid',
        'pullhttpheader',
        'pullmimepost',
        'pulloneheaderline',
        'pullpost',
        'pullrawpost',
        'pullrawpostchunks',
        'pullrequest',
        'pullrequestline',
        'push',
        'pushctx',
        'pushinclude',
        'qdarray',
        'qdcount',
        'queryparam',
        'queryparams',
        'queryparamsary',
        'querystring',
        'queue_maintenance',
        'queue_messages',
        'queue_status',
        'queue',
        'quit',
        'r',
        'raw',
        'rawcontent',
        'rawdiff',
        'rawheader',
        'rawheaders',
        'rawinvokable',
        'read',
        'readattributevalue',
        'readbytes',
        'readbytesfully',
        'readdestinations',
        'readerror',
        'readidobjects',
        'readline',
        'readmessage',
        'readnumber',
        'readobject',
        'readobjecttcp',
        'readpacket',
        'readsomebytes',
        'readstring',
        'ready',
        'realdoc',
        'realpath',
        'receivefd',
        'recipients',
        'recover',
        'rect',
        'rectype',
        'red',
        'redirectto',
        'referrals',
        'refid',
        'refobj',
        'refresh',
        'rel',
        'remainder',
        'remoteaddr',
        'remoteaddress',
        'remoteport',
        'remove',
        'removeall',
        'removeattribute',
        'removeattributenode',
        'removeattributens',
        'removeback',
        'removechild',
        'removedatabasetable',
        'removedatasource',
        'removedatasourcedatabase',
        'removedatasourcehost',
        'removefield',
        'removefirst',
        'removefront',
        'removegroup',
        'removelast',
        'removeleading',
        'removenameditem',
        'removenameditemns',
        'removenode',
        'removesubnode',
        'removetrailing',
        'removeuser',
        'removeuserfromallgroups',
        'removeuserfromgroup',
        'rename',
        'renderbytes',
        'renderdocumentbytes',
        'renderstring',
        'replace',
        'replaceall',
        'replacechild',
        'replacedata',
        'replacefirst',
        'replaceheader',
        'replacepattern',
        'representnode',
        'representnoderesult',
        'reqid',
        'requestid',
        'requestmethod',
        'requestparams',
        'requesturi',
        'requires',
        'reserve',
        'reset',
        'resize',
        'resolutionh',
        'resolutionv',
        'resolvelinks',
        'resourcedata',
        'resourceinvokable',
        'resourcename',
        'resources',
        'respond',
        'restart',
        'restname',
        'result',
        'results',
        'resume',
        'retr',
        'retrieve',
        'returncolumns',
        'returntype',
        'rev',
        'reverse',
        'rewind',
        'right',
        'rint',
        'roll',
        'root',
        'rootmap',
        'rotate',
        'route',
        'rowsfound',
        'rset',
        'rule',
        'rules',
        'run',
        'running',
        'runonce',
        's',
        'sa',
        'safeexport8bits',
        'sameas',
        'save',
        'savedata',
        'scalb',
        'scale',
        'scanfordatasource',
        'scantasks',
        'scanworkers',
        'schemaname',
        'scheme',
        'script',
        'scriptextensions',
        'scriptfilename',
        'scriptname',
        'scripttype',
        'scripturi',
        'scripturl',
        'scrubkeywords',
        'search',
        'searchinbucket',
        'searchurl',
        'second',
        'secondsbetween',
        'seek',
        'select',
        'selected',
        'selectmany',
        'self',
        'send',
        'sendchunk',
        'sendfd',
        'sendfile',
        'sendpacket',
        'sendresponse',
        'separator',
        'serializationelements',
        'serialize',
        'serveraddr',
        'serveradmin',
        'servername',
        'serverport',
        'serverprotocol',
        'serversignature',
        'serversoftware',
        'sessionsdump',
        'sessionsmap',
        'set',
        'setalignment',
        'setattr',
        'setattribute',
        'setattributenode',
        'setattributenodens',
        'setattributens',
        'setbarheight',
        'setbarmultiplier',
        'setbarwidth',
        'setbaseline',
        'setbold',
        'setbooleanarrayregion',
        'setbooleanfield',
        'setbordercolor',
        'setborderwidth',
        'setbytearrayregion',
        'setbytefield',
        'setchararrayregion',
        'setcharfield',
        'setcode',
        'setcolor',
        'setcolorspace',
        'setcookie',
        'setcwd',
        'setdefaultstorage',
        'setdestination',
        'setdoublearrayregion',
        'setdoublefield',
        'setencoding',
        'setface',
        'setfieldvalue',
        'setfindpattern',
        'setfloatarrayregion',
        'setfloatfield',
        'setfont',
        'setformat',
        'setgeneratechecksum',
        'setheaders',
        'sethtmlattr',
        'setignorecase',
        'setinput',
        'setintarrayregion',
        'setintfield',
        'setitalic',
        'setlinewidth',
        'setlongarrayregion',
        'setlongfield',
        'setmarker',
        'setmaxfilesize',
        'setmode',
        'setname',
        'setnameditem',
        'setnameditemns',
        'setobjectarrayelement',
        'setobjectfield',
        'setpadding',
        'setpagenumber',
        'setpagerange',
        'setposition',
        'setrange',
        'setreplacepattern',
        'setshortarrayregion',
        'setshortfield',
        'setshowchecksum',
        'setsize',
        'setspacing',
        'setstaticbooleanfield',
        'setstaticbytefield',
        'setstaticcharfield',
        'setstaticdoublefield',
        'setstaticfloatfield',
        'setstaticintfield',
        'setstaticlongfield',
        'setstaticobjectfield',
        'setstaticshortfield',
        'setstatus',
        'settextalignment',
        'settextsize',
        'settimezone',
        'settrait',
        'setunderline',
        'sharpen',
        'shouldabort',
        'shouldclose',
        'showchecksum',
        'showcode39startstop',
        'showeanguardbars',
        'shutdownrd',
        'shutdownrdwr',
        'shutdownwr',
        'sin',
        'sinh',
        'size',
        'skip',
        'skiprows',
        'sort',
        'sortcolumns',
        'source',
        'sourcecolumn',
        'sourcefile',
        'sourceline',
        'specified',
        'split',
        'splitconnection',
        'splitdebuggingthread',
        'splitextension',
        'splittext',
        'splitthread',
        'splittoprivatedev',
        'splituppath',
        'sql',
        'sqlite3',
        'sqrt',
        'src',
        'srcpath',
        'sslerrfail',
        'stack',
        'standby',
        'start',
        'startone',
        'startup',
        'stat',
        'statement',
        'statementonly',
        'stats',
        'status',
        'statuscode',
        'statusmsg',
        'stdin',
        'step',
        'stls',
        'stop',
        'stoprunning',
        'storedata',
        'stripfirstcomponent',
        'striplastcomponent',
        'style',
        'styletype',
        'sub',
        'subject',
        'subnode',
        'subnodes',
        'substringdata',
        'subtract',
        'subtraits',
        'sum',
        'supportscontentrepresentation',
        'swapbytes',
        'systemid',
        't',
        'tabindex',
        'table',
        'tablecolumnnames',
        'tablecolumns',
        'tablehascolumn',
        'tableizestacktrace',
        'tableizestacktracelink',
        'tablemap',
        'tablename',
        'tables',
        'tabs',
        'tabstr',
        'tag',
        'tagname',
        'take',
        'tan',
        'tanh',
        'target',
        'tasks',
        'tb',
        'tell',
        'testexitcode',
        'testlock',
        'textwidth',
        'thenby',
        'thenbydescending',
        'threadreaddesc',
        'throw',
        'thrownew',
        'time',
        'timezone',
        'title',
        'titlecase',
        'to',
        'token',
        'tolower',
        'top',
        'toreflectedfield',
        'toreflectedmethod',
        'total_changes',
        'totitle',
        'touch',
        'toupper',
        'toxmlstring',
        'trace',
        'trackingid',
        'trait',
        'transform',
        'trigger',
        'trim',
        'trunk',
        'tryfinderrorfile',
        'trylock',
        'tryreadobject',
        'type',
        'typename',
        'uidl',
        'uncompress',
        'unescape',
        'union',
        'uniqueid',
        'unlock',
        'unspool',
        'up',
        'update',
        'updategroup',
        'upload',
        'uppercase',
        'url',
        'used',
        'usemap',
        'user',
        'usercolumns',
        'valid',
        'validate',
        'validatesessionstable',
        'value',
        'values',
        'valuetype',
        'variant',
        'version',
        'wait',
        'waitforcompletion',
        'warnings',
        'week',
        'weekofmonth',
        'weekofyear',
        'where',
        'width',
        'workers',
        'workinginputcolumns',
        'workingkeycolumns',
        'workingkeyfield_name',
        'workingreturncolumns',
        'workingsortcolumns',
        'write',
        'writebodybytes',
        'writebytes',
        'writeheader',
        'writeheaderbytes',
        'writeheaderline',
        'writeid',
        'writemessage',
        'writeobject',
        'writeobjecttcp',
        'writestring',
        'wroteheaders',
        'xhtml',
        'xmllang',
        'y0',
        'y1',
        'year',
        'yearwoy',
        'yn',
        'z',
        'zip',
        'zipfile',
        'zipfilename',
        'zipname',
        'zips',
        'zoneoffset',
    ),
    'Lasso 8 Member Tags': (
        'accept',
        'add',
        'addattachment',
        'addattribute',
        'addbarcode',
        'addchapter',
        'addcheckbox',
        'addchild',
        'addcombobox',
        'addcomment',
        'addcontent',
        'addhiddenfield',
        'addhtmlpart',
        'addimage',
        'addjavascript',
        'addlist',
        'addnamespace',
        'addnextsibling',
        'addpage',
        'addparagraph',
        'addparenttype',
        'addpart',
        'addpasswordfield',
        'addphrase',
        'addprevsibling',
        'addradiobutton',
        'addradiogroup',
        'addresetbutton',
        'addsection',
        'addselectlist',
        'addsibling',
        'addsubmitbutton',
        'addtable',
        'addtext',
        'addtextarea',
        'addtextfield',
        'addtextpart',
        'alarms',
        'annotate',
        'answer',
        'append',
        'appendreplacement',
        'appendtail',
        'arc',
        'asasync',
        'astype',
        'atbegin',
        'atbottom',
        'atend',
        'atfarleft',
        'atfarright',
        'attop',
        'attributecount',
        'attributes',
        'authenticate',
        'authorize',
        'backward',
        'baseuri',
        'bcc',
        'beanproperties',
        'beginswith',
        'bind',
        'bitand',
        'bitclear',
        'bitflip',
        'bitformat',
        'bitnot',
        'bitor',
        'bitset',
        'bitshiftleft',
        'bitshiftright',
        'bittest',
        'bitxor',
        'blur',
        'body',
        'boundary',
        'bytes',
        'call',
        'cancel',
        'capabilities',
        'cc',
        'chardigitvalue',
        'charname',
        'charset',
        'chartype',
        'children',
        'circle',
        'close',
        'closepath',
        'closewrite',
        'code',
        'colorspace',
        'command',
        'comments',
        'compare',
        'comparecodepointorder',
        'compile',
        'composite',
        'connect',
        'contains',
        'content_disposition',
        'content_transfer_encoding',
        'content_type',
        'contents',
        'contrast',
        'convert',
        'crop',
        'curveto',
        'data',
        'date',
        'day',
        'daylights',
        'dayofweek',
        'dayofyear',
        'decrement',
        'delete',
        'depth',
        'describe',
        'description',
        'deserialize',
        'detach',
        'detachreference',
        'difference',
        'digit',
        'document',
        'down',
        'drawtext',
        'dst',
        'dump',
        'endswith',
        'enhance',
        'equals',
        'errors',
        'eval',
        'events',
        'execute',
        'export16bits',
        'export32bits',
        'export64bits',
        'export8bits',
        'exportfdf',
        'exportstring',
        'extract',
        'extractone',
        'fieldnames',
        'fieldtype',
        'fieldvalue',
        'file',
        'find',
        'findindex',
        'findnamespace',
        'findnamespacebyhref',
        'findpattern',
        'findposition',
        'first',
        'firstchild',
        'fliph',
        'flipv',
        'flush',
        'foldcase',
        'foreach',
        'format',
        'forward',
        'freebusies',
        'freezetype',
        'freezevalue',
        'from',
        'fulltype',
        'generatechecksum',
        'get',
        'getabswidth',
        'getalignment',
        'getattribute',
        'getattributenamespace',
        'getbarheight',
        'getbarmultiplier',
        'getbarwidth',
        'getbaseline',
        'getbordercolor',
        'getborderwidth',
        'getcode',
        'getcolor',
        'getcolumncount',
        'getencoding',
        'getface',
        'getfont',
        'getformat',
        'getfullfontname',
        'getheaders',
        'getmargins',
        'getmethod',
        'getnumericvalue',
        'getpadding',
        'getpagenumber',
        'getparams',
        'getproperty',
        'getpsfontname',
        'getrange',
        'getrowcount',
        'getsize',
        'getspacing',
        'getsupportedencodings',
        'gettextalignment',
        'gettextsize',
        'gettype',
        'gmt',
        'groupcount',
        'hasattribute',
        'haschildren',
        'hasvalue',
        'header',
        'headers',
        'height',
        'histogram',
        'hosttonet16',
        'hosttonet32',
        'hour',
        'id',
        'ignorecase',
        'import16bits',
        'import32bits',
        'import64bits',
        'import8bits',
        'importfdf',
        'importstring',
        'increment',
        'input',
        'insert',
        'insertatcurrent',
        'insertfirst',
        'insertfrom',
        'insertlast',
        'insertpage',
        'integer',
        'intersection',
        'invoke',
        'isa',
        'isalnum',
        'isalpha',
        'isbase',
        'iscntrl',
        'isdigit',
        'isemptyelement',
        'islower',
        'isopen',
        'isprint',
        'isspace',
        'istitle',
        'istruetype',
        'isualphabetic',
        'isulowercase',
        'isupper',
        'isuuppercase',
        'isuwhitespace',
        'iswhitespace',
        'iterator',
        'javascript',
        'join',
        'journals',
        'key',
        'keys',
        'last',
        'lastchild',
        'lasterror',
        'left',
        'length',
        'line',
        'listen',
        'localaddress',
        'localname',
        'lock',
        'lookupnamespace',
        'lowercase',
        'marker',
        'matches',
        'matchesstart',
        'matchposition',
        'matchstring',
        'merge',
        'millisecond',
        'minute',
        'mode',
        'modulate',
        'month',
        'moveto',
        'movetoattributenamespace',
        'movetoelement',
        'movetofirstattribute',
        'movetonextattribute',
        'name',
        'namespaces',
        'namespaceuri',
        'nettohost16',
        'nettohost32',
        'newchild',
        'next',
        'nextsibling',
        'nodetype',
        'open',
        'output',
        'padleading',
        'padtrailing',
        'pagecount',
        'pagesize',
        'paraminfo',
        'params',
        'parent',
        'path',
        'pixel',
        'position',
        'prefix',
        'previoussibling',
        'properties',
        'rawheaders',
        'read',
        'readattributevalue',
        'readerror',
        'readfrom',
        'readline',
        'readlock',
        'readstring',
        'readunlock',
        'recipients',
        'rect',
        'refcount',
        'referrals',
        'remoteaddress',
        'remove',
        'removeall',
        'removeattribute',
        'removechild',
        'removecurrent',
        'removefirst',
        'removelast',
        'removeleading',
        'removenamespace',
        'removetrailing',
        'render',
        'replace',
        'replaceall',
        'replacefirst',
        'replacepattern',
        'replacewith',
        'reserve',
        'reset',
        'resolutionh',
        'resolutionv',
        'response',
        'results',
        'retrieve',
        'returntype',
        'reverse',
        'reverseiterator',
        'right',
        'rotate',
        'run',
        'save',
        'scale',
        'search',
        'second',
        'send',
        'serialize',
        'set',
        'setalignment',
        'setbarheight',
        'setbarmultiplier',
        'setbarwidth',
        'setbaseline',
        'setblocking',
        'setbordercolor',
        'setborderwidth',
        'setbytes',
        'setcode',
        'setcolor',
        'setcolorspace',
        'setdatatype',
        'setencoding',
        'setface',
        'setfieldvalue',
        'setfont',
        'setformat',
        'setgeneratechecksum',
        'setheight',
        'setlassodata',
        'setlinewidth',
        'setmarker',
        'setmode',
        'setname',
        'setpadding',
        'setpagenumber',
        'setpagerange',
        'setposition',
        'setproperty',
        'setrange',
        'setshowchecksum',
        'setsize',
        'setspacing',
        'settemplate',
        'settemplatestr',
        'settextalignment',
        'settextdata',
        'settextsize',
        'settype',
        'setunderline',
        'setwidth',
        'setxmldata',
        'sharpen',
        'showchecksum',
        'showcode39startstop',
        'showeanguardbars',
        'signal',
        'signalall',
        'size',
        'smooth',
        'sort',
        'sortwith',
        'split',
        'standards',
        'steal',
        'subject',
        'substring',
        'subtract',
        'swapbytes',
        'textwidth',
        'time',
        'timezones',
        'titlecase',
        'to',
        'todos',
        'tolower',
        'totitle',
        'toupper',
        'transform',
        'trim',
        'type',
        'unescape',
        'union',
        'uniqueid',
        'unlock',
        'unserialize',
        'up',
        'uppercase',
        'value',
        'values',
        'valuetype',
        'wait',
        'waskeyword',
        'week',
        'width',
        'write',
        'writelock',
        'writeto',
        'writeunlock',
        'xmllang',
        'xmlschematype',
        'year',
    )
}