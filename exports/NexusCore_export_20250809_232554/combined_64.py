
# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\tools\exports\export_20250803_114325\combined_17.py ===

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_regression.py ===
import os

import numpy as np
from numpy.testing import (
    _assert_valid_refcount,
    assert_,
    assert_array_almost_equal,
    assert_array_equal,
    assert_equal,
    assert_raises,
)


class TestRegression:
    def test_poly1d(self):
        # Ticket #28
        assert_equal(np.poly1d([1]) - np.poly1d([1, 0]),
                     np.poly1d([-1, 1]))

    def test_cov_parameters(self):
        # Ticket #91
        x = np.random.random((3, 3))
        y = x.copy()
        np.cov(x, rowvar=True)
        np.cov(y, rowvar=False)
        assert_array_equal(x, y)

    def test_mem_digitize(self):
        # Ticket #95
        for i in range(100):
            np.digitize([1, 2, 3, 4], [1, 3])
            np.digitize([0, 1, 2, 3, 4], [1, 3])

    def test_unique_zero_sized(self):
        # Ticket #205
        assert_array_equal([], np.unique(np.array([])))

    def test_mem_vectorise(self):
        # Ticket #325
        vt = np.vectorize(lambda *args: args)
        vt(np.zeros((1, 2, 1)), np.zeros((2, 1, 1)), np.zeros((1, 1, 2)))
        vt(np.zeros((1, 2, 1)), np.zeros((2, 1, 1)), np.zeros((1,
           1, 2)), np.zeros((2, 2)))

    def test_mgrid_single_element(self):
        # Ticket #339
        assert_array_equal(np.mgrid[0:0:1j], [0])
        assert_array_equal(np.mgrid[0:0], [])

    def test_refcount_vectorize(self):
        # Ticket #378
        def p(x, y):
            return 123
        v = np.vectorize(p)
        _assert_valid_refcount(v)

    def test_poly1d_nan_roots(self):
        # Ticket #396
        p = np.poly1d([np.nan, np.nan, 1], r=False)
        assert_raises(np.linalg.LinAlgError, getattr, p, "r")

    def test_mem_polymul(self):
        # Ticket #448
        np.polymul([], [1.])

    def test_mem_string_concat(self):
        # Ticket #469
        x = np.array([])
        np.append(x, 'asdasd\tasdasd')

    def test_poly_div(self):
        # Ticket #553
        u = np.poly1d([1, 2, 3])
        v = np.poly1d([1, 2, 3, 4, 5])
        q, r = np.polydiv(u, v)
        assert_equal(q * v + r, u)

    def test_poly_eq(self):
        # Ticket #554
        x = np.poly1d([1, 2, 3])
        y = np.poly1d([3, 4])
        assert_(x != y)
        assert_(x == x)

    def test_polyfit_build(self):
        # Ticket #628
        ref = [-1.06123820e-06, 5.70886914e-04, -1.13822012e-01,
               9.95368241e+00, -3.14526520e+02]
        x = [90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103,
             104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115,
             116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 129,
             130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141,
             146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157,
             158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169,
             170, 171, 172, 173, 174, 175, 176]
        y = [9.0, 3.0, 7.0, 4.0, 4.0, 8.0, 6.0, 11.0, 9.0, 8.0, 11.0, 5.0,
             6.0, 5.0, 9.0, 8.0, 6.0, 10.0, 6.0, 10.0, 7.0, 6.0, 6.0, 6.0,
             13.0, 4.0, 9.0, 11.0, 4.0, 5.0, 8.0, 5.0, 7.0, 7.0, 6.0, 12.0,
             7.0, 7.0, 9.0, 4.0, 12.0, 6.0, 6.0, 4.0, 3.0, 9.0, 8.0, 8.0,
             6.0, 7.0, 9.0, 10.0, 6.0, 8.0, 4.0, 7.0, 7.0, 10.0, 8.0, 8.0,
             6.0, 3.0, 8.0, 4.0, 5.0, 7.0, 8.0, 6.0, 6.0, 4.0, 12.0, 9.0,
             8.0, 8.0, 8.0, 6.0, 7.0, 4.0, 4.0, 5.0, 7.0]
        tested = np.polyfit(x, y, 4)
        assert_array_almost_equal(ref, tested)

    def test_polydiv_type(self):
        # Make polydiv work for complex types
        msg = "Wrong type, should be complex"
        x = np.ones(3, dtype=complex)
        q, r = np.polydiv(x, x)
        assert_(q.dtype == complex, msg)
        msg = "Wrong type, should be float"
        x = np.ones(3, dtype=int)
        q, r = np.polydiv(x, x)
        assert_(q.dtype == float, msg)

    def test_histogramdd_too_many_bins(self):
        # Ticket 928.
        assert_raises(ValueError, np.histogramdd, np.ones((1, 10)), bins=2**10)

    def test_polyint_type(self):
        # Ticket #944
        msg = "Wrong type, should be complex"
        x = np.ones(3, dtype=complex)
        assert_(np.polyint(x).dtype == complex, msg)
        msg = "Wrong type, should be float"
        x = np.ones(3, dtype=int)
        assert_(np.polyint(x).dtype == float, msg)

    def test_ndenumerate_crash(self):
        # Ticket 1140
        # Shouldn't crash:
        list(np.ndenumerate(np.array([[]])))

    def test_large_fancy_indexing(self):
        # Large enough to fail on 64-bit.
        nbits = np.dtype(np.intp).itemsize * 8
        thesize = int((2**nbits)**(1.0 / 5.0) + 1)

        def dp():
            n = 3
            a = np.ones((n,) * 5)
            i = np.random.randint(0, n, size=thesize)
            a[np.ix_(i, i, i, i, i)] = 0

        def dp2():
            n = 3
            a = np.ones((n,) * 5)
            i = np.random.randint(0, n, size=thesize)
            a[np.ix_(i, i, i, i, i)]

        assert_raises(ValueError, dp)
        assert_raises(ValueError, dp2)

    def test_void_coercion(self):
        dt = np.dtype([('a', 'f4'), ('b', 'i4')])
        x = np.zeros((1,), dt)
        assert_(np.r_[x, x].dtype == dt)

    def test_include_dirs(self):
        # As a sanity check, just test that get_include
        # includes something reasonable.  Somewhat
        # related to ticket #1405.
        include_dirs = [np.get_include()]
        for path in include_dirs:
            assert_(isinstance(path, str))
            assert_(path != '')

    def test_polyder_return_type(self):
        # Ticket #1249
        assert_(isinstance(np.polyder(np.poly1d([1]), 0), np.poly1d))
        assert_(isinstance(np.polyder([1], 0), np.ndarray))
        assert_(isinstance(np.polyder(np.poly1d([1]), 1), np.poly1d))
        assert_(isinstance(np.polyder([1], 1), np.ndarray))

    def test_append_fields_dtype_list(self):
        # Ticket #1676
        from numpy.lib.recfunctions import append_fields

        base = np.array([1, 2, 3], dtype=np.int32)
        names = ['a', 'b', 'c']
        data = np.eye(3).astype(np.int32)
        dlist = [np.float64, np.int32, np.int32]
        try:
            append_fields(base, names, data, dlist)
        except Exception:
            raise AssertionError

    def test_loadtxt_fields_subarrays(self):
        # For ticket #1936
        from io import StringIO

        dt = [("a", 'u1', 2), ("b", 'u1', 2)]
        x = np.loadtxt(StringIO("0 1 2 3"), dtype=dt)
        assert_equal(x, np.array([((0, 1), (2, 3))], dtype=dt))

        dt = [("a", [("a", 'u1', (1, 3)), ("b", 'u1')])]
        x = np.loadtxt(StringIO("0 1 2 3"), dtype=dt)
        assert_equal(x, np.array([(((0, 1, 2), 3),)], dtype=dt))

        dt = [("a", 'u1', (2, 2))]
        x = np.loadtxt(StringIO("0 1 2 3"), dtype=dt)
        assert_equal(x, np.array([(((0, 1), (2, 3)),)], dtype=dt))

        dt = [("a", 'u1', (2, 3, 2))]
        x = np.loadtxt(StringIO("0 1 2 3 4 5 6 7 8 9 10 11"), dtype=dt)
        data = [((((0, 1), (2, 3), (4, 5)), ((6, 7), (8, 9), (10, 11))),)]
        assert_equal(x, np.array(data, dtype=dt))

    def test_nansum_with_boolean(self):
        # gh-2978
        a = np.zeros(2, dtype=bool)
        try:
            np.nansum(a)
        except Exception:
            raise AssertionError

    def test_py3_compat(self):
        # gh-2561
        # Test if the oldstyle class test is bypassed in python3
        class C:
            """Old-style class in python2, normal class in python3"""
            pass

        out = open(os.devnull, 'w')
        try:
            np.info(C(), output=out)
        except AttributeError:
            raise AssertionError
        finally:
            out.close()

# === NexusCore/openenv\Lib\site-packages\litellm\utils.py ===
# +-----------------------------------------------+
# |                                               |
# |           Give Feedback / Get Help            |
# | https://github.com/BerriAI/litellm/issues/new |
# |                                               |
# +-----------------------------------------------+
#
#  Thank you users! We ❤️ you! - Krrish & Ishaan

import ast
import asyncio
import base64
import binascii
import copy
import datetime
import hashlib
import inspect
import io
import itertools
import json
import logging
import os
import random  # type: ignore
import re
import struct
import subprocess

# What is this?
## Generic utils.py file. Problem-specific utils (e.g. 'cost calculation), should all be in `litellm_core_utils/`.
import sys
import textwrap
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from functools import lru_cache, wraps
from importlib import resources
from inspect import iscoroutine
from os.path import abspath, dirname, join

import aiohttp
import dotenv
import httpx
import openai
import tiktoken
from httpx import Proxy
from httpx._utils import get_environment_proxies
from openai.lib import _parsing, _pydantic
from openai.types.chat.completion_create_params import ResponseFormat
from pydantic import BaseModel
from tiktoken import Encoding
from tokenizers import Tokenizer

import litellm
import litellm._service_logger  # for storing API inputs, outputs, and metadata
import litellm.litellm_core_utils
import litellm.litellm_core_utils.audio_utils.utils
import litellm.litellm_core_utils.json_validation_rule
import litellm.llms
import litellm.llms.gemini
from litellm.caching._internal_lru_cache import lru_cache_wrapper
from litellm.caching.caching import DualCache
from litellm.caching.caching_handler import CachingHandlerResponse, LLMCachingHandler
from litellm.constants import (
    DEFAULT_CHAT_COMPLETION_PARAM_VALUES,
    DEFAULT_EMBEDDING_PARAM_VALUES,
    DEFAULT_MAX_LRU_CACHE_SIZE,
    DEFAULT_TRIM_RATIO,
    FUNCTION_DEFINITION_TOKEN_COUNT,
    INITIAL_RETRY_DELAY,
    JITTER,
    MAX_RETRY_DELAY,
    MAX_TOKEN_TRIMMING_ATTEMPTS,
    MINIMUM_PROMPT_CACHE_TOKEN_COUNT,
    OPENAI_EMBEDDING_PARAMS,
    TOOL_CHOICE_OBJECT_TOKEN_COUNT,
)
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.integrations.custom_logger import CustomLogger
from litellm.integrations.vector_stores.base_vector_store import BaseVectorStore
from litellm.litellm_core_utils.core_helpers import (
    map_finish_reason,
    process_response_headers,
)
from litellm.litellm_core_utils.credential_accessor import CredentialAccessor
from litellm.litellm_core_utils.default_encoding import encoding
from litellm.litellm_core_utils.exception_mapping_utils import (
    _get_response_headers,
    exception_type,
    get_error_message,
)
from litellm.litellm_core_utils.get_litellm_params import (
    _get_base_model_from_litellm_call_metadata,
    get_litellm_params,
)
from litellm.litellm_core_utils.get_llm_provider_logic import (
    _is_non_openai_azure_model,
    get_llm_provider,
)
from litellm.litellm_core_utils.get_supported_openai_params import (
    get_supported_openai_params,
)
from litellm.litellm_core_utils.llm_request_utils import _ensure_extra_body_is_safe
from litellm.litellm_core_utils.llm_response_utils.convert_dict_to_response import (
    LiteLLMResponseObjectHandler,
    _handle_invalid_parallel_tool_calls,
    _parse_content_for_reasoning,
    convert_to_model_response_object,
    convert_to_streaming_response,
    convert_to_streaming_response_async,
)
from litellm.litellm_core_utils.llm_response_utils.get_api_base import get_api_base
from litellm.litellm_core_utils.llm_response_utils.get_formatted_prompt import (
    get_formatted_prompt,
)
from litellm.litellm_core_utils.llm_response_utils.get_headers import (
    get_response_headers,
)
from litellm.litellm_core_utils.llm_response_utils.response_metadata import (
    ResponseMetadata,
)
from litellm.litellm_core_utils.redact_messages import (
    LiteLLMLoggingObject,
    redact_message_input_output_from_logging,
)
from litellm.litellm_core_utils.rules import Rules
from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.litellm_core_utils.token_counter import get_modified_max_tokens
from litellm.llms.bedrock.common_utils import BedrockModelInfo
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler, HTTPHandler
from litellm.router_utils.get_retry_from_policy import (
    get_num_retries_from_retry_policy,
    reset_retry_policy,
)
from litellm.secret_managers.main import get_secret
from litellm.types.llms.anthropic import (
    ANTHROPIC_API_ONLY_HEADERS,
    AnthropicThinkingParam,
)
from litellm.types.llms.openai import (
    AllMessageValues,
    AllPromptValues,
    ChatCompletionAssistantToolCall,
    ChatCompletionNamedToolChoiceParam,
    ChatCompletionToolParam,
    ChatCompletionToolParamFunctionChunk,
    OpenAITextCompletionUserMessage,
    OpenAIWebSearchOptions,
)
from litellm.types.rerank import RerankResponse
from litellm.types.utils import FileTypes  # type: ignore
from litellm.types.utils import (
    OPENAI_RESPONSE_HEADERS,
    CallTypes,
    ChatCompletionDeltaToolCall,
    ChatCompletionMessageToolCall,
    Choices,
    CostPerToken,
    CredentialItem,
    CustomHuggingfaceTokenizer,
    Delta,
    Embedding,
    EmbeddingResponse,
    Function,
    ImageResponse,
    LlmProviders,
    LlmProvidersSet,
    Message,
    ModelInfo,
    ModelInfoBase,
    ModelResponse,
    ModelResponseStream,
    ProviderField,
    ProviderSpecificModelInfo,
    RawRequestTypedDict,
    SelectTokenizerResponse,
    StreamingChoices,
    TextChoices,
    TextCompletionResponse,
    TranscriptionResponse,
    Usage,
    all_litellm_params,
)

try:
    # Python 3.9+
    with resources.files("litellm.litellm_core_utils.tokenizers").joinpath(
        "anthropic_tokenizer.json"
    ).open("r", encoding="utf-8") as f:
        json_data = json.load(f)
except (ImportError, AttributeError, TypeError):
    with resources.open_text(
        "litellm.litellm_core_utils.tokenizers", "anthropic_tokenizer.json"
    ) as f:
        json_data = json.load(f)

# Convert to str (if necessary)
claude_json_str = json.dumps(json_data)
import importlib.metadata
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
    get_args,
)

from openai import OpenAIError as OriginalError

from litellm.litellm_core_utils.thread_pool_executor import executor
from litellm.litellm_core_utils.token_counter import token_counter as token_counter_new
from litellm.llms.base_llm.anthropic_messages.transformation import (
    BaseAnthropicMessagesConfig,
)
from litellm.llms.base_llm.audio_transcription.transformation import (
    BaseAudioTranscriptionConfig,
)
from litellm.llms.base_llm.base_utils import (
    BaseLLMModelInfo,
    type_to_response_format_param,
)
from litellm.llms.base_llm.chat.transformation import BaseConfig
from litellm.llms.base_llm.completion.transformation import BaseTextCompletionConfig
from litellm.llms.base_llm.embedding.transformation import BaseEmbeddingConfig
from litellm.llms.base_llm.files.transformation import BaseFilesConfig
from litellm.llms.base_llm.image_edit.transformation import BaseImageEditConfig
from litellm.llms.base_llm.image_generation.transformation import (
    BaseImageGenerationConfig,
)
from litellm.llms.base_llm.image_variations.transformation import (
    BaseImageVariationConfig,
)
from litellm.llms.base_llm.realtime.transformation import BaseRealtimeConfig
from litellm.llms.base_llm.rerank.transformation import BaseRerankConfig
from litellm.llms.base_llm.responses.transformation import BaseResponsesAPIConfig

from ._logging import _is_debugging_on, verbose_logger
from .caching.caching import (
    Cache,
    QdrantSemanticCache,
    RedisCache,
    RedisSemanticCache,
    S3Cache,
)
from .exceptions import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    BadRequestError,
    BudgetExceededError,
    ContentPolicyViolationError,
    ContextWindowExceededError,
    NotFoundError,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
    UnprocessableEntityError,
    UnsupportedParamsError,
)
from .proxy._types import AllowedModelRegion, KeyManagementSystem
from .types.llms.openai import (
    ChatCompletionDeltaToolCallChunk,
    ChatCompletionToolCallChunk,
    ChatCompletionToolCallFunctionChunk,
)
from .types.router import LiteLLM_Params

####### ENVIRONMENT VARIABLES ####################
# Adjust to your specific application needs / system capabilities.
sentry_sdk_instance = None
capture_exception = None
add_breadcrumb = None
posthog = None
slack_app = None
alerts_channel = None
heliconeLogger = None
athinaLogger = None
promptLayerLogger = None
langsmithLogger = None
logfireLogger = None
weightsBiasesLogger = None
customLogger = None
langFuseLogger = None
openMeterLogger = None
lagoLogger = None
dataDogLogger = None
prometheusLogger = None
dynamoLogger = None
s3Logger = None
greenscaleLogger = None
lunaryLogger = None
aispendLogger = None
supabaseClient = None
callback_list: Optional[List[str]] = []
user_logger_fn = None
additional_details: Optional[Dict[str, str]] = {}
local_cache: Optional[Dict[str, str]] = {}
last_fetched_at = None
last_fetched_at_keys = None
######## Model Response #########################

# All liteLLM Model responses will be in this format, Follows the OpenAI Format
# https://docs.litellm.ai/docs/completion/output
# {
#   'choices': [
#      {
#         'finish_reason': 'stop',
#         'index': 0,
#         'message': {
#            'role': 'assistant',
#             'content': " I'm doing well, thank you for asking. I am Claude, an AI assistant created by Anthropic."
#         }
#       }
#     ],
#  'created': 1691429984.3852863,
#  'model': 'claude-instant-1',
#  'usage': {'prompt_tokens': 18, 'completion_tokens': 23, 'total_tokens': 41}
# }


############################################################
def print_verbose(
    print_statement,
    logger_only: bool = False,
    log_level: Literal["DEBUG", "INFO", "ERROR"] = "DEBUG",
):
    try:
        if log_level == "DEBUG":
            verbose_logger.debug(print_statement)
        elif log_level == "INFO":
            verbose_logger.info(print_statement)
        elif log_level == "ERROR":
            verbose_logger.error(print_statement)
        if litellm.set_verbose is True and logger_only is False:
            print(print_statement)  # noqa
    except Exception:
        pass


####### CLIENT ###################
# make it easy to log if completion/embedding runs succeeded or failed + see what happened | Non-Blocking
def custom_llm_setup():
    """
    Add custom_llm provider to provider list
    """
    for custom_llm in litellm.custom_provider_map:
        if custom_llm["provider"] not in litellm.provider_list:
            litellm.provider_list.append(custom_llm["provider"])

        if custom_llm["provider"] not in litellm._custom_providers:
            litellm._custom_providers.append(custom_llm["provider"])


def _add_custom_logger_callback_to_specific_event(
    callback: str, logging_event: Literal["success", "failure"]
) -> None:
    """
    Add a custom logger callback to the specific event
    """
    from litellm import _custom_logger_compatible_callbacks_literal
    from litellm.litellm_core_utils.litellm_logging import (
        _init_custom_logger_compatible_class,
    )

    if callback not in litellm._known_custom_logger_compatible_callbacks:
        verbose_logger.debug(
            f"Callback {callback} is not a valid custom logger compatible callback. Known list - {litellm._known_custom_logger_compatible_callbacks}"
        )
        return

    callback_class = _init_custom_logger_compatible_class(
        cast(_custom_logger_compatible_callbacks_literal, callback),
        internal_usage_cache=None,
        llm_router=None,
    )

    if callback_class:
        if (
            logging_event == "success"
            and _custom_logger_class_exists_in_success_callbacks(callback_class)
            is False
        ):
            litellm.logging_callback_manager.add_litellm_success_callback(
                callback_class
            )
            litellm.logging_callback_manager.add_litellm_async_success_callback(
                callback_class
            )
            if callback in litellm.success_callback:
                litellm.success_callback.remove(
                    callback
                )  # remove the string from the callback list
            if callback in litellm._async_success_callback:
                litellm._async_success_callback.remove(
                    callback
                )  # remove the string from the callback list
        elif (
            logging_event == "failure"
            and _custom_logger_class_exists_in_failure_callbacks(callback_class)
            is False
        ):
            litellm.logging_callback_manager.add_litellm_failure_callback(
                callback_class
            )
            litellm.logging_callback_manager.add_litellm_async_failure_callback(
                callback_class
            )
            if callback in litellm.failure_callback:
                litellm.failure_callback.remove(
                    callback
                )  # remove the string from the callback list
            if callback in litellm._async_failure_callback:
                litellm._async_failure_callback.remove(
                    callback
                )  # remove the string from the callback list


def _custom_logger_class_exists_in_success_callbacks(
    callback_class: CustomLogger,
) -> bool:
    """
    Returns True if an instance of the custom logger exists in litellm.success_callback or litellm._async_success_callback

    e.g if `LangfusePromptManagement` is passed in, it will return True if an instance of `LangfusePromptManagement` exists in litellm.success_callback or litellm._async_success_callback

    Prevents double adding a custom logger callback to the litellm callbacks
    """
    return any(
        isinstance(cb, type(callback_class))
        for cb in litellm.success_callback + litellm._async_success_callback
    )


def _custom_logger_class_exists_in_failure_callbacks(
    callback_class: CustomLogger,
) -> bool:
    """
    Returns True if an instance of the custom logger exists in litellm.failure_callback or litellm._async_failure_callback

    e.g if `LangfusePromptManagement` is passed in, it will return True if an instance of `LangfusePromptManagement` exists in litellm.failure_callback or litellm._async_failure_callback

    Prevents double adding a custom logger callback to the litellm callbacks
    """
    return any(
        isinstance(cb, type(callback_class))
        for cb in litellm.failure_callback + litellm._async_failure_callback
    )


def get_request_guardrails(kwargs: Dict[str, Any]) -> List[str]:
    """
    Get the request guardrails from the kwargs
    """
    metadata = kwargs.get("metadata") or {}
    requester_metadata = metadata.get("requester_metadata") or {}
    applied_guardrails = requester_metadata.get("guardrails") or []
    return applied_guardrails


def get_applied_guardrails(kwargs: Dict[str, Any]) -> List[str]:
    """
    - Add 'default_on' guardrails to the list
    - Add request guardrails to the list
    """

    request_guardrails = get_request_guardrails(kwargs)
    applied_guardrails = []
    for callback in litellm.callbacks:
        if callback is not None and isinstance(callback, CustomGuardrail):
            if callback.guardrail_name is not None:
                if callback.default_on is True:
                    applied_guardrails.append(callback.guardrail_name)
                elif callback.guardrail_name in request_guardrails:
                    applied_guardrails.append(callback.guardrail_name)

    return applied_guardrails


def load_credentials_from_list(kwargs: dict):
    """
    Updates kwargs with the credentials if credential_name in kwarg
    """
    credential_name = kwargs.get("litellm_credential_name")
    if credential_name and litellm.credential_list:
        credential_accessor = CredentialAccessor.get_credential_values(credential_name)
        for key, value in credential_accessor.items():
            if key not in kwargs:
                kwargs[key] = value


def get_dynamic_callbacks(
    dynamic_callbacks: Optional[List[Union[str, Callable, CustomLogger]]],
) -> List:
    returned_callbacks = litellm.callbacks.copy()
    if dynamic_callbacks:
        returned_callbacks.extend(dynamic_callbacks)  # type: ignore
    return returned_callbacks


def function_setup(  # noqa: PLR0915
    original_function: str, rules_obj, start_time, *args, **kwargs
):  # just run once to check if user wants to send their data anywhere - PostHog/Sentry/Slack/etc.
    ### NOTICES ###
    from litellm import Logging as LiteLLMLogging
    from litellm.litellm_core_utils.litellm_logging import set_callbacks

    if litellm.set_verbose is True:
        verbose_logger.warning(
            "`litellm.set_verbose` is deprecated. Please set `os.environ['LITELLM_LOG'] = 'DEBUG'` for debug logs."
        )
    try:
        global callback_list, add_breadcrumb, user_logger_fn, Logging

        ## CUSTOM LLM SETUP ##
        custom_llm_setup()

        ## GET APPLIED GUARDRAILS
        applied_guardrails = get_applied_guardrails(kwargs)

        ## LOGGING SETUP
        function_id: Optional[str] = kwargs["id"] if "id" in kwargs else None

        ## DYNAMIC CALLBACKS ##
        dynamic_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = kwargs.pop("callbacks", None)
        all_callbacks = get_dynamic_callbacks(dynamic_callbacks=dynamic_callbacks)

        if len(all_callbacks) > 0:
            for callback in all_callbacks:
                # check if callback is a string - e.g. "lago", "openmeter"
                if isinstance(callback, str):
                    callback = litellm.litellm_core_utils.litellm_logging._init_custom_logger_compatible_class(  # type: ignore
                        callback, internal_usage_cache=None, llm_router=None  # type: ignore
                    )
                    if callback is None or any(
                        isinstance(cb, type(callback))
                        for cb in litellm._async_success_callback
                    ):  # don't double add a callback
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
            print_verbose(
                f"Initialized litellm callbacks, Async Success Callbacks: {litellm._async_success_callback}"
            )

        if (
            len(litellm.input_callback) > 0
            or len(litellm.success_callback) > 0
            or len(litellm.failure_callback) > 0
        ) and len(
            callback_list  # type: ignore
        ) == 0:  # type: ignore
            callback_list = list(
                set(
                    litellm.input_callback  # type: ignore
                    + litellm.success_callback
                    + litellm.failure_callback
                )
            )
            set_callbacks(callback_list=callback_list, function_id=function_id)
        ## ASYNC CALLBACKS
        if len(litellm.input_callback) > 0:
            removed_async_items = []
            for index, callback in enumerate(litellm.input_callback):  # type: ignore
                if inspect.iscoroutinefunction(callback):
                    litellm._async_input_callback.append(callback)
                    removed_async_items.append(index)

            # Pop the async items from input_callback in reverse order to avoid index issues
            for index in reversed(removed_async_items):
                litellm.input_callback.pop(index)
        if len(litellm.success_callback) > 0:
            removed_async_items = []
            for index, callback in enumerate(litellm.success_callback):  # type: ignore
                if inspect.iscoroutinefunction(callback):
                    litellm.logging_callback_manager.add_litellm_async_success_callback(
                        callback
                    )
                    removed_async_items.append(index)
                elif callback == "dynamodb" or callback == "openmeter":
                    # dynamo is an async callback, it's used for the proxy and needs to be async
                    # we only support async dynamo db logging for acompletion/aembedding since that's used on proxy
                    litellm.logging_callback_manager.add_litellm_async_success_callback(
                        callback
                    )
                    removed_async_items.append(index)
                elif (
                    callback in litellm._known_custom_logger_compatible_callbacks
                    and isinstance(callback, str)
                ):
                    _add_custom_logger_callback_to_specific_event(callback, "success")

            # Pop the async items from success_callback in reverse order to avoid index issues
            for index in reversed(removed_async_items):
                litellm.success_callback.pop(index)

        if len(litellm.failure_callback) > 0:
            removed_async_items = []
            for index, callback in enumerate(litellm.failure_callback):  # type: ignore
                if inspect.iscoroutinefunction(callback):
                    litellm.logging_callback_manager.add_litellm_async_failure_callback(
                        callback
                    )
                    removed_async_items.append(index)
                elif (
                    callback in litellm._known_custom_logger_compatible_callbacks
                    and isinstance(callback, str)
                ):
                    _add_custom_logger_callback_to_specific_event(callback, "failure")

            # Pop the async items from failure_callback in reverse order to avoid index issues
            for index in reversed(removed_async_items):
                litellm.failure_callback.pop(index)
        ### DYNAMIC CALLBACKS ###
        dynamic_success_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = None
        dynamic_async_success_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = None
        dynamic_failure_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = None
        dynamic_async_failure_callbacks: Optional[
            List[Union[str, Callable, CustomLogger]]
        ] = None
        if kwargs.get("success_callback", None) is not None and isinstance(
            kwargs["success_callback"], list
        ):
            removed_async_items = []
            for index, callback in enumerate(kwargs["success_callback"]):
                if (
                    inspect.iscoroutinefunction(callback)
                    or callback == "dynamodb"
                    or callback == "s3"
                ):
                    if dynamic_async_success_callbacks is not None and isinstance(
                        dynamic_async_success_callbacks, list
                    ):
                        dynamic_async_success_callbacks.append(callback)
                    else:
                        dynamic_async_success_callbacks = [callback]
                    removed_async_items.append(index)
            # Pop the async items from success_callback in reverse order to avoid index issues
            for index in reversed(removed_async_items):
                kwargs["success_callback"].pop(index)
            dynamic_success_callbacks = kwargs.pop("success_callback")
        if kwargs.get("failure_callback", None) is not None and isinstance(
            kwargs["failure_callback"], list
        ):
            dynamic_failure_callbacks = kwargs.pop("failure_callback")

        if add_breadcrumb:
            try:
                details_to_log = copy.deepcopy(kwargs)
            except Exception:
                details_to_log = kwargs

            if litellm.turn_off_message_logging:
                # make a copy of the _model_Call_details and log it
                details_to_log.pop("messages", None)
                details_to_log.pop("input", None)
                details_to_log.pop("prompt", None)
            add_breadcrumb(
                category="litellm.llm_call",
                message=f"Keyword Args: {details_to_log}",
                level="info",
            )
        if "logger_fn" in kwargs:
            user_logger_fn = kwargs["logger_fn"]
        # INIT LOGGER - for user-specified integrations
        model = args[0] if len(args) > 0 else kwargs.get("model", None)
        call_type = original_function
        if (
            call_type == CallTypes.completion.value
            or call_type == CallTypes.acompletion.value
            or call_type == CallTypes.anthropic_messages.value
        ):
            messages = None
            if len(args) > 1:
                messages = args[1]
            elif kwargs.get("messages", None):
                messages = kwargs["messages"]
            ### PRE-CALL RULES ###
            if (
                isinstance(messages, list)
                and len(messages) > 0
                and isinstance(messages[0], dict)
                and "content" in messages[0]
            ):
                rules_obj.pre_call_rules(
                    input="".join(
                        m.get("content", "")
                        for m in messages
                        if "content" in m and isinstance(m["content"], str)
                    ),
                    model=model,
                )
        elif (
            call_type == CallTypes.embedding.value
            or call_type == CallTypes.aembedding.value
        ):
            messages = args[1] if len(args) > 1 else kwargs.get("input", None)
        elif (
            call_type == CallTypes.image_generation.value
            or call_type == CallTypes.aimage_generation.value
        ):
            messages = args[0] if len(args) > 0 else kwargs["prompt"]
        elif (
            call_type == CallTypes.moderation.value
            or call_type == CallTypes.amoderation.value
        ):
            messages = args[1] if len(args) > 1 else kwargs["input"]
        elif (
            call_type == CallTypes.atext_completion.value
            or call_type == CallTypes.text_completion.value
        ):
            messages = args[0] if len(args) > 0 else kwargs["prompt"]
        elif (
            call_type == CallTypes.rerank.value or call_type == CallTypes.arerank.value
        ):
            messages = kwargs.get("query")
        elif (
            call_type == CallTypes.atranscription.value
            or call_type == CallTypes.transcription.value
        ):
            _file_obj: FileTypes = args[1] if len(args) > 1 else kwargs["file"]
            file_checksum = (
                litellm.litellm_core_utils.audio_utils.utils.get_audio_file_name(
                    file_obj=_file_obj
                )
            )
            if "metadata" in kwargs:
                kwargs["metadata"]["file_checksum"] = file_checksum
            else:
                kwargs["metadata"] = {"file_checksum": file_checksum}
            messages = file_checksum
        elif (
            call_type == CallTypes.aspeech.value or call_type == CallTypes.speech.value
        ):
            messages = kwargs.get("input", "speech")
        elif (
            call_type == CallTypes.aresponses.value
            or call_type == CallTypes.responses.value
        ):
            messages = args[0] if len(args) > 0 else kwargs["input"]
        else:
            messages = "default-message-value"
        stream = True if "stream" in kwargs and kwargs["stream"] is True else False
        logging_obj = LiteLLMLogging(
            model=model,  # type: ignore
            messages=messages,
            stream=stream,
            litellm_call_id=kwargs["litellm_call_id"],
            litellm_trace_id=kwargs.get("litellm_trace_id"),
            function_id=function_id or "",
            call_type=call_type,
            start_time=start_time,
            dynamic_success_callbacks=dynamic_success_callbacks,
            dynamic_failure_callbacks=dynamic_failure_callbacks,
            dynamic_async_success_callbacks=dynamic_async_success_callbacks,
            dynamic_async_failure_callbacks=dynamic_async_failure_callbacks,
            kwargs=kwargs,
            applied_guardrails=applied_guardrails,
        )

        ## check if metadata is passed in
        litellm_params: Dict[str, Any] = {"api_base": ""}
        if "metadata" in kwargs:
            litellm_params["metadata"] = kwargs["metadata"]
        logging_obj.update_environment_variables(
            model=model,
            user="",
            optional_params={},
            litellm_params=litellm_params,
            stream_options=kwargs.get("stream_options", None),
        )
        return logging_obj, kwargs
    except Exception as e:
        verbose_logger.exception(
            "litellm.utils.py::function_setup() - [Non-Blocking] Error in function_setup"
        )
        raise e


async def _client_async_logging_helper(
    logging_obj: LiteLLMLoggingObject,
    result,
    start_time,
    end_time,
    is_completion_with_fallbacks: bool,
):
    if (
        is_completion_with_fallbacks is False
    ):  # don't log the parent event litellm.completion_with_fallbacks as a 'log_success_event', this will lead to double logging the same call - https://github.com/BerriAI/litellm/issues/7477
        print_verbose(
            f"Async Wrapper: Completed Call, calling async_success_handler: {logging_obj.async_success_handler}"
        )
        # check if user does not want this to be logged
        asyncio.create_task(
            logging_obj.async_success_handler(result, start_time, end_time)
        )
        logging_obj.handle_sync_success_callbacks_for_async_calls(
            result=result,
            start_time=start_time,
            end_time=end_time,
        )


def _get_wrapper_num_retries(
    kwargs: Dict[str, Any], exception: Exception
) -> Tuple[Optional[int], Dict[str, Any]]:
    """
    Get the number of retries from the kwargs and the retry policy.
    Used for the wrapper functions.
    """

    num_retries = kwargs.get("num_retries", None)
    if num_retries is None:
        num_retries = litellm.num_retries
    if kwargs.get("retry_policy", None):
        retry_policy_num_retries = get_num_retries_from_retry_policy(
            exception=exception,
            retry_policy=kwargs.get("retry_policy"),
        )
        kwargs["retry_policy"] = reset_retry_policy()
        if retry_policy_num_retries is not None:
            num_retries = retry_policy_num_retries

    return num_retries, kwargs


def _get_wrapper_timeout(
    kwargs: Dict[str, Any], exception: Exception
) -> Optional[Union[float, int, httpx.Timeout]]:
    """
    Get the timeout from the kwargs
    Used for the wrapper functions.
    """

    timeout = cast(
        Optional[Union[float, int, httpx.Timeout]], kwargs.get("timeout", None)
    )

    return timeout


def client(original_function):  # noqa: PLR0915
    rules_obj = Rules()

    def check_coroutine(value) -> bool:
        if inspect.iscoroutine(value):
            return True
        elif inspect.iscoroutinefunction(value):
            return True
        else:
            return False

    async def async_pre_call_deployment_hook(kwargs: Dict[str, Any], call_type: str):
        """
        Allow modifying the request just before it's sent to the deployment.

        Use this instead of 'async_pre_call_hook' when you need to modify the request AFTER a deployment is selected, but BEFORE the request is sent.
        """
        try:
            typed_call_type = CallTypes(call_type)
        except ValueError:
            typed_call_type = None  # unknown call type

        modified_kwargs = kwargs.copy()
        for callback in litellm.callbacks:
            if isinstance(callback, CustomLogger):
                result = await callback.async_pre_call_deployment_hook(
                    modified_kwargs, typed_call_type
                )
                if result is not None:
                    modified_kwargs = result

        return modified_kwargs

    def post_call_processing(original_response, model, optional_params: Optional[dict]):
        try:
            if original_response is None:
                pass
            else:
                call_type = original_function.__name__
                if (
                    call_type == CallTypes.completion.value
                    or call_type == CallTypes.acompletion.value
                ):
                    is_coroutine = check_coroutine(original_response)
                    if is_coroutine is True:
                        pass
                    else:
                        if (
                            isinstance(original_response, ModelResponse)
                            and len(original_response.choices) > 0
                        ):
                            model_response: Optional[str] = original_response.choices[
                                0
                            ].message.content  # type: ignore
                            if model_response is not None:
                                ### POST-CALL RULES ###
                                rules_obj.post_call_rules(
                                    input=model_response, model=model
                                )
                                ### JSON SCHEMA VALIDATION ###
                                if litellm.enable_json_schema_validation is True:
                                    try:
                                        if (
                                            optional_params is not None
                                            and "response_format" in optional_params
                                            and optional_params["response_format"]
                                            is not None
                                        ):
                                            json_response_format: Optional[dict] = None
                                            if (
                                                isinstance(
                                                    optional_params["response_format"],
                                                    dict,
                                                )
                                                and optional_params[
                                                    "response_format"
                                                ].get("json_schema")
                                                is not None
                                            ):
                                                json_response_format = optional_params[
                                                    "response_format"
                                                ]
                                            elif _parsing._completions.is_basemodel_type(
                                                optional_params["response_format"]  # type: ignore
                                            ):
                                                json_response_format = (
                                                    type_to_response_format_param(
                                                        response_format=optional_params[
                                                            "response_format"
                                                        ]
                                                    )
                                                )
                                            if json_response_format is not None:
                                                litellm.litellm_core_utils.json_validation_rule.validate_schema(
                                                    schema=json_response_format[
                                                        "json_schema"
                                                    ]["schema"],
                                                    response=model_response,
                                                )
                                    except TypeError:
                                        pass
                                if (
                                    optional_params is not None
                                    and "response_format" in optional_params
                                    and isinstance(
                                        optional_params["response_format"], dict
                                    )
                                    and "type" in optional_params["response_format"]
                                    and optional_params["response_format"]["type"]
                                    == "json_object"
                                    and "response_schema"
                                    in optional_params["response_format"]
                                    and isinstance(
                                        optional_params["response_format"][
                                            "response_schema"
                                        ],
                                        dict,
                                    )
                                    and "enforce_validation"
                                    in optional_params["response_format"]
                                    and optional_params["response_format"][
                                        "enforce_validation"
                                    ]
                                    is True
                                ):
                                    # schema given, json response expected, and validation enforced
                                    litellm.litellm_core_utils.json_validation_rule.validate_schema(
                                        schema=optional_params["response_format"][
                                            "response_schema"
                                        ],
                                        response=model_response,
                                    )

        except Exception as e:
            raise e

    @wraps(original_function)
    def wrapper(*args, **kwargs):  # noqa: PLR0915
        # DO NOT MOVE THIS. It always needs to run first
        # Check if this is an async function. If so only execute the async function
        call_type = original_function.__name__
        if _is_async_request(kwargs):
            # [OPTIONAL] CHECK MAX RETRIES / REQUEST
            if litellm.num_retries_per_request is not None:
                # check if previous_models passed in as ['litellm_params']['metadata]['previous_models']
                previous_models = kwargs.get("metadata", {}).get(
                    "previous_models", None
                )
                if previous_models is not None:
                    if litellm.num_retries_per_request <= len(previous_models):
                        raise Exception("Max retries per request hit!")

            # MODEL CALL
            result = original_function(*args, **kwargs)
            if "stream" in kwargs and kwargs["stream"] is True:
                if (
                    "complete_response" in kwargs
                    and kwargs["complete_response"] is True
                ):
                    chunks = []
                    for idx, chunk in enumerate(result):
                        chunks.append(chunk)
                    return litellm.stream_chunk_builder(
                        chunks, messages=kwargs.get("messages", None)
                    )
                else:
                    return result

            return result

        # Prints Exactly what was passed to litellm function - don't execute any logic here - it should just print
        print_args_passed_to_litellm(original_function, args, kwargs)
        start_time = datetime.datetime.now()
        result = None
        logging_obj: Optional[LiteLLMLoggingObject] = kwargs.get(
            "litellm_logging_obj", None
        )

        # only set litellm_call_id if its not in kwargs
        if "litellm_call_id" not in kwargs:
            kwargs["litellm_call_id"] = str(uuid.uuid4())

        model: Optional[str] = args[0] if len(args) > 0 else kwargs.get("model", None)

        try:
            if logging_obj is None:
                logging_obj, kwargs = function_setup(
                    original_function.__name__, rules_obj, start_time, *args, **kwargs
                )
            ## LOAD CREDENTIALS
            load_credentials_from_list(kwargs)
            kwargs["litellm_logging_obj"] = logging_obj
            _llm_caching_handler: LLMCachingHandler = LLMCachingHandler(
                original_function=original_function,
                request_kwargs=kwargs,
                start_time=start_time,
            )
            logging_obj._llm_caching_handler = _llm_caching_handler

            # CHECK FOR 'os.environ/' in kwargs
            for k, v in kwargs.items():
                if v is not None and isinstance(v, str) and v.startswith("os.environ/"):
                    kwargs[k] = litellm.get_secret(v)
            # [OPTIONAL] CHECK BUDGET
            if litellm.max_budget:
                if litellm._current_cost > litellm.max_budget:
                    raise BudgetExceededError(
                        current_cost=litellm._current_cost,
                        max_budget=litellm.max_budget,
                    )

            # [OPTIONAL] CHECK MAX RETRIES / REQUEST
            if litellm.num_retries_per_request is not None:
                # check if previous_models passed in as ['litellm_params']['metadata]['previous_models']
                previous_models = kwargs.get("metadata", {}).get(
                    "previous_models", None
                )
                if previous_models is not None:
                    if litellm.num_retries_per_request <= len(previous_models):
                        raise Exception("Max retries per request hit!")

            # [OPTIONAL] CHECK CACHE
            print_verbose(
                f"SYNC kwargs[caching]: {kwargs.get('caching', False)}; litellm.cache: {litellm.cache}; kwargs.get('cache')['no-cache']: {kwargs.get('cache', {}).get('no-cache', False)}"
            )
            # if caching is false or cache["no-cache"]==True, don't run this
            if (
                (
                    (
                        (
                            kwargs.get("caching", None) is None
                            and litellm.cache is not None
                        )
                        or kwargs.get("caching", False) is True
                    )
                    and kwargs.get("cache", {}).get("no-cache", False) is not True
                )
                and kwargs.get("aembedding", False) is not True
                and kwargs.get("atext_completion", False) is not True
                and kwargs.get("acompletion", False) is not True
                and kwargs.get("aimg_generation", False) is not True
                and kwargs.get("atranscription", False) is not True
                and kwargs.get("arerank", False) is not True
                and kwargs.get("_arealtime", False) is not True
            ):  # allow users to control returning cached responses from the completion function
                # checking cache
                verbose_logger.debug("INSIDE CHECKING SYNC CACHE")
                caching_handler_response: CachingHandlerResponse = (
                    _llm_caching_handler._sync_get_cache(
                        model=model or "",
                        original_function=original_function,
                        logging_obj=logging_obj,
                        start_time=start_time,
                        call_type=call_type,
                        kwargs=kwargs,
                        args=args,
                    )
                )

                if caching_handler_response.cached_result is not None:
                    verbose_logger.debug("Cache hit!")
                    return caching_handler_response.cached_result

            # CHECK MAX TOKENS
            if (
                kwargs.get("max_tokens", None) is not None
                and model is not None
                and litellm.modify_params
                is True  # user is okay with params being modified
                and (
                    call_type == CallTypes.acompletion.value
                    or call_type == CallTypes.completion.value
                )
            ):
                try:
                    base_model = model
                    if kwargs.get("hf_model_name", None) is not None:
                        base_model = f"huggingface/{kwargs.get('hf_model_name')}"
                    messages = None
                    if len(args) > 1:
                        messages = args[1]
                    elif kwargs.get("messages", None):
                        messages = kwargs["messages"]
                    user_max_tokens = kwargs.get("max_tokens")
                    modified_max_tokens = get_modified_max_tokens(
                        model=model,
                        base_model=base_model,
                        messages=messages,
                        user_max_tokens=user_max_tokens,
                        buffer_num=None,
                        buffer_perc=None,
                    )
                    kwargs["max_tokens"] = modified_max_tokens
                except Exception as e:
                    print_verbose(f"Error while checking max token limit: {str(e)}")
            # MODEL CALL
            result = original_function(*args, **kwargs)
            end_time = datetime.datetime.now()
            if "stream" in kwargs and kwargs["stream"] is True:
                if (
                    "complete_response" in kwargs
                    and kwargs["complete_response"] is True
                ):
                    chunks = []
                    for idx, chunk in enumerate(result):
                        chunks.append(chunk)
                    return litellm.stream_chunk_builder(
                        chunks, messages=kwargs.get("messages", None)
                    )
                else:
                    # RETURN RESULT
                    update_response_metadata(
                        result=result,
                        logging_obj=logging_obj,
                        model=model,
                        kwargs=kwargs,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    return result
            elif "acompletion" in kwargs and kwargs["acompletion"] is True:
                return result
            elif "aembedding" in kwargs and kwargs["aembedding"] is True:
                return result
            elif "aimg_generation" in kwargs and kwargs["aimg_generation"] is True:
                return result
            elif "atranscription" in kwargs and kwargs["atranscription"] is True:
                return result
            elif "aspeech" in kwargs and kwargs["aspeech"] is True:
                return result
            elif asyncio.iscoroutine(result):  # bubble up to relevant async function
                return result

            ### POST-CALL RULES ###
            post_call_processing(
                original_response=result,
                model=model or None,
                optional_params=kwargs,
            )

            # [OPTIONAL] ADD TO CACHE
            _llm_caching_handler.sync_set_cache(
                result=result,
                args=args,
                kwargs=kwargs,
            )

            # LOG SUCCESS - handle streaming success logging in the _next_ object, remove `handle_success` once it's deprecated
            verbose_logger.info("Wrapper: Completed Call, calling success_handler")
            executor.submit(
                logging_obj.success_handler,
                result,
                start_time,
                end_time,
            )
            # RETURN RESULT
            update_response_metadata(
                result=result,
                logging_obj=logging_obj,
                model=model,
                kwargs=kwargs,
                start_time=start_time,
                end_time=end_time,
            )
            return result
        except Exception as e:
            call_type = original_function.__name__
            if call_type == CallTypes.completion.value:
                num_retries = (
                    kwargs.get("num_retries", None) or litellm.num_retries or None
                )
                if kwargs.get("retry_policy", None):
                    num_retries = get_num_retries_from_retry_policy(
                        exception=e,
                        retry_policy=kwargs.get("retry_policy"),
                    )
                    kwargs[
                        "retry_policy"
                    ] = reset_retry_policy()  # prevent infinite loops
                litellm.num_retries = (
                    None  # set retries to None to prevent infinite loops
                )
                context_window_fallback_dict = kwargs.get(
                    "context_window_fallback_dict", {}
                )

                _is_litellm_router_call = "model_group" in kwargs.get(
                    "metadata", {}
                )  # check if call from litellm.router/proxy
                if (
                    num_retries and not _is_litellm_router_call
                ):  # only enter this if call is not from litellm router/proxy. router has it's own logic for retrying
                    if (
                        isinstance(e, openai.APIError)
                        or isinstance(e, openai.Timeout)
                        or isinstance(e, openai.APIConnectionError)
                    ):
                        kwargs["num_retries"] = num_retries
                        return litellm.completion_with_retries(*args, **kwargs)
                elif (
                    isinstance(e, litellm.exceptions.ContextWindowExceededError)
                    and context_window_fallback_dict
                    and model in context_window_fallback_dict
                    and not _is_litellm_router_call
                ):
                    if len(args) > 0:
                        args[0] = context_window_fallback_dict[model]  # type: ignore
                    else:
                        kwargs["model"] = context_window_fallback_dict[model]
                    return original_function(*args, **kwargs)
            traceback_exception = traceback.format_exc()
            end_time = datetime.datetime.now()

            # LOG FAILURE - handle streaming failure logging in the _next_ object, remove `handle_failure` once it's deprecated
            if logging_obj:
                logging_obj.failure_handler(
                    e, traceback_exception, start_time, end_time
                )  # DO NOT MAKE THREADED - router retry fallback relies on this!
            raise e

    @wraps(original_function)
    async def wrapper_async(*args, **kwargs):  # noqa: PLR0915
        print_args_passed_to_litellm(original_function, args, kwargs)
        start_time = datetime.datetime.now()
        result = None
        logging_obj: Optional[LiteLLMLoggingObject] = kwargs.get(
            "litellm_logging_obj", None
        )
        _llm_caching_handler: LLMCachingHandler = LLMCachingHandler(
            original_function=original_function,
            request_kwargs=kwargs,
            start_time=start_time,
        )
        # only set litellm_call_id if its not in kwargs
        call_type = original_function.__name__
        if "litellm_call_id" not in kwargs:
            kwargs["litellm_call_id"] = str(uuid.uuid4())

        model: Optional[str] = args[0] if len(args) > 0 else kwargs.get("model", None)
        is_completion_with_fallbacks = kwargs.get("fallbacks") is not None

        try:
            if logging_obj is None:
                logging_obj, kwargs = function_setup(
                    original_function.__name__, rules_obj, start_time, *args, **kwargs
                )
            modified_kwargs = await async_pre_call_deployment_hook(kwargs, call_type)
            if modified_kwargs is not None:
                kwargs = modified_kwargs

            kwargs["litellm_logging_obj"] = logging_obj
            ## LOAD CREDENTIALS
            load_credentials_from_list(kwargs)
            logging_obj._llm_caching_handler = _llm_caching_handler
            # [OPTIONAL] CHECK BUDGET
            if litellm.max_budget:
                if litellm._current_cost > litellm.max_budget:
                    raise BudgetExceededError(
                        current_cost=litellm._current_cost,
                        max_budget=litellm.max_budget,
                    )

            # [OPTIONAL] CHECK CACHE
            print_verbose(
                f"ASYNC kwargs[caching]: {kwargs.get('caching', False)}; litellm.cache: {litellm.cache}; kwargs.get('cache'): {kwargs.get('cache', None)}"
            )
            _caching_handler_response: CachingHandlerResponse = (
                await _llm_caching_handler._async_get_cache(
                    model=model or "",
                    original_function=original_function,
                    logging_obj=logging_obj,
                    start_time=start_time,
                    call_type=call_type,
                    kwargs=kwargs,
                    args=args,
                )
            )

            if (
                _caching_handler_response.cached_result is not None
                and _caching_handler_response.final_embedding_cached_response is None
            ):
                return _caching_handler_response.cached_result

            elif _caching_handler_response.embedding_all_elements_cache_hit is True:
                return _caching_handler_response.final_embedding_cached_response

            # MODEL CALL
            result = await original_function(*args, **kwargs)
            end_time = datetime.datetime.now()
            if "stream" in kwargs and kwargs["stream"] is True:
                if (
                    "complete_response" in kwargs
                    and kwargs["complete_response"] is True
                ):
                    chunks = []
                    for idx, chunk in enumerate(result):
                        chunks.append(chunk)
                    return litellm.stream_chunk_builder(
                        chunks, messages=kwargs.get("messages", None)
                    )
                else:
                    update_response_metadata(
                        result=result,
                        logging_obj=logging_obj,
                        model=model,
                        kwargs=kwargs,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    return result
            elif call_type == CallTypes.arealtime.value:
                return result
            ### POST-CALL RULES ###
            post_call_processing(
                original_response=result, model=model, optional_params=kwargs
            )

            ## Add response to cache
            await _llm_caching_handler.async_set_cache(
                result=result,
                original_function=original_function,
                kwargs=kwargs,
                args=args,
            )

            # LOG SUCCESS - handle streaming success logging in the _next_ object
            asyncio.create_task(
                _client_async_logging_helper(
                    logging_obj=logging_obj,
                    result=result,
                    start_time=start_time,
                    end_time=end_time,
                    is_completion_with_fallbacks=is_completion_with_fallbacks,
                )
            )
            logging_obj.handle_sync_success_callbacks_for_async_calls(
                result=result,
                start_time=start_time,
                end_time=end_time,
            )
            # REBUILD EMBEDDING CACHING
            if (
                isinstance(result, EmbeddingResponse)
                and _caching_handler_response.final_embedding_cached_response
                is not None
            ):
                return _llm_caching_handler._combine_cached_embedding_response_with_api_result(
                    _caching_handler_response=_caching_handler_response,
                    embedding_response=result,
                    start_time=start_time,
                    end_time=end_time,
                )

            update_response_metadata(
                result=result,
                logging_obj=logging_obj,
                model=model,
                kwargs=kwargs,
                start_time=start_time,
                end_time=end_time,
            )

            return result
        except Exception as e:
            traceback_exception = traceback.format_exc()
            end_time = datetime.datetime.now()
            if logging_obj:
                try:
                    logging_obj.failure_handler(
                        e, traceback_exception, start_time, end_time
                    )  # DO NOT MAKE THREADED - router retry fallback relies on this!
                except Exception as e:
                    raise e
                try:
                    await logging_obj.async_failure_handler(
                        e, traceback_exception, start_time, end_time
                    )
                except Exception as e:
                    raise e

            call_type = original_function.__name__
            num_retries, kwargs = _get_wrapper_num_retries(kwargs=kwargs, exception=e)
            if call_type == CallTypes.acompletion.value:
                context_window_fallback_dict = kwargs.get(
                    "context_window_fallback_dict", {}
                )

                _is_litellm_router_call = "model_group" in kwargs.get(
                    "metadata", {}
                )  # check if call from litellm.router/proxy

                if (
                    num_retries and not _is_litellm_router_call
                ):  # only enter this if call is not from litellm router/proxy. router has it's own logic for retrying
                    try:
                        litellm.num_retries = (
                            None  # set retries to None to prevent infinite loops
                        )
                        kwargs["num_retries"] = num_retries
                        kwargs["original_function"] = original_function
                        if isinstance(
                            e, openai.RateLimitError
                        ):  # rate limiting specific error
                            kwargs["retry_strategy"] = "exponential_backoff_retry"
                        elif isinstance(e, openai.APIError):  # generic api error
                            kwargs["retry_strategy"] = "constant_retry"
                        return await litellm.acompletion_with_retries(*args, **kwargs)
                    except Exception:
                        pass
                elif (
                    isinstance(e, litellm.exceptions.ContextWindowExceededError)
                    and context_window_fallback_dict
                    and model in context_window_fallback_dict
                ):
                    if len(args) > 0:
                        args[0] = context_window_fallback_dict[model]  # type: ignore
                    else:
                        kwargs["model"] = context_window_fallback_dict[model]
                    return await original_function(*args, **kwargs)

            setattr(
                e, "num_retries", num_retries
            )  ## IMPORTANT: returns the deployment's num_retries to the router

            timeout = _get_wrapper_timeout(kwargs=kwargs, exception=e)
            setattr(e, "timeout", timeout)
            raise e

    is_coroutine = inspect.iscoroutinefunction(original_function)

    # Return the appropriate wrapper based on the original function type
    if is_coroutine:
        return wrapper_async
    else:
        return wrapper


def _is_async_request(
    kwargs: Optional[dict],
    is_pass_through: bool = False,
) -> bool:
    """
    Returns True if the call type is an internal async request.

    eg. litellm.acompletion, litellm.aimage_generation, litellm.acreate_batch, litellm._arealtime

    Args:
        kwargs (dict): The kwargs passed to the litellm function
        is_pass_through (bool): Whether the call is a pass-through call. By default all pass through calls are async.
    """
    if kwargs is None:
        return False
    if (
        kwargs.get("acompletion", False) is True
        or kwargs.get("aembedding", False) is True
        or kwargs.get("aimg_generation", False) is True
        or kwargs.get("amoderation", False) is True
        or kwargs.get("atext_completion", False) is True
        or kwargs.get("atranscription", False) is True
        or kwargs.get("arerank", False) is True
        or kwargs.get("_arealtime", False) is True
        or kwargs.get("acreate_batch", False) is True
        or kwargs.get("acreate_fine_tuning_job", False) is True
        or is_pass_through is True
    ):
        return True
    return False


def update_response_metadata(
    result: Any,
    logging_obj: LiteLLMLoggingObject,
    model: Optional[str],
    kwargs: dict,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
) -> None:
    """
    Updates response metadata, adds the following:
        - response._hidden_params
        - response._hidden_params["litellm_overhead_time_ms"]
        - response.response_time_ms
    """
    if result is None:
        return

    metadata = ResponseMetadata(result)
    metadata.set_hidden_params(logging_obj=logging_obj, model=model, kwargs=kwargs)
    metadata.set_timing_metrics(
        start_time=start_time, end_time=end_time, logging_obj=logging_obj
    )
    metadata.apply()


def _select_tokenizer(
    model: str, custom_tokenizer: Optional[CustomHuggingfaceTokenizer] = None
):
    if custom_tokenizer is not None:
        _tokenizer = create_pretrained_tokenizer(
            identifier=custom_tokenizer["identifier"],
            revision=custom_tokenizer["revision"],
            auth_token=custom_tokenizer["auth_token"],
        )
        return _tokenizer
    return _select_tokenizer_helper(model=model)


@lru_cache(maxsize=DEFAULT_MAX_LRU_CACHE_SIZE)
def _select_tokenizer_helper(model: str) -> SelectTokenizerResponse:
    if litellm.disable_hf_tokenizer_download is True:
        return _return_openai_tokenizer(model)

    try:
        result = _return_huggingface_tokenizer(model)
        if result is not None:
            return result
    except Exception as e:
        verbose_logger.debug(f"Error selecting tokenizer: {e}")

    # default - tiktoken
    return _return_openai_tokenizer(model)


def _return_openai_tokenizer(model: str) -> SelectTokenizerResponse:
    return {"type": "openai_tokenizer", "tokenizer": encoding}


def _return_huggingface_tokenizer(model: str) -> Optional[SelectTokenizerResponse]:
    if model in litellm.cohere_models and "command-r" in model:
        # cohere
        cohere_tokenizer = Tokenizer.from_pretrained(
            "Xenova/c4ai-command-r-v01-tokenizer"
        )
        return {"type": "huggingface_tokenizer", "tokenizer": cohere_tokenizer}
    # anthropic
    elif model in litellm.anthropic_models and "claude-3" not in model:
        claude_tokenizer = Tokenizer.from_str(claude_json_str)
        return {"type": "huggingface_tokenizer", "tokenizer": claude_tokenizer}
    # llama2
    elif "llama-2" in model.lower() or "replicate" in model.lower():
        tokenizer = Tokenizer.from_pretrained("hf-internal-testing/llama-tokenizer")
        return {"type": "huggingface_tokenizer", "tokenizer": tokenizer}
    # llama3
    elif "llama-3" in model.lower():
        tokenizer = Tokenizer.from_pretrained("Xenova/llama-3-tokenizer")
        return {"type": "huggingface_tokenizer", "tokenizer": tokenizer}
    else:
        return None


def encode(model="", text="", custom_tokenizer: Optional[dict] = None):
    """
    Encodes the given text using the specified model.

    Args:
        model (str): The name of the model to use for tokenization.
        custom_tokenizer (Optional[dict]): A custom tokenizer created with the `create_pretrained_tokenizer` or `create_tokenizer` method. Must be a dictionary with a string value for `type` and Tokenizer for `tokenizer`. Default is None.
        text (str): The text to be encoded.

    Returns:
        enc: The encoded text.
    """
    tokenizer_json = custom_tokenizer or _select_tokenizer(model=model)
    if isinstance(tokenizer_json["tokenizer"], Encoding):
        enc = tokenizer_json["tokenizer"].encode(text, disallowed_special=())
    else:
        enc = tokenizer_json["tokenizer"].encode(text)
    return enc


def decode(model="", tokens: List[int] = [], custom_tokenizer: Optional[dict] = None):
    tokenizer_json = custom_tokenizer or _select_tokenizer(model=model)
    dec = tokenizer_json["tokenizer"].decode(tokens)
    return dec


def create_pretrained_tokenizer(
    identifier: str, revision="main", auth_token: Optional[str] = None
):
    """
    Creates a tokenizer from an existing file on a HuggingFace repository to be used with `token_counter`.

    Args:
    identifier (str): The identifier of a Model on the Hugging Face Hub, that contains a tokenizer.json file
    revision (str, defaults to main): A branch or commit id
    auth_token (str, optional, defaults to None): An optional auth token used to access private repositories on the Hugging Face Hub

    Returns:
    dict: A dictionary with the tokenizer and its type.
    """

    try:
        tokenizer = Tokenizer.from_pretrained(
            identifier, revision=revision, auth_token=auth_token  # type: ignore
        )
    except Exception as e:
        verbose_logger.error(
            f"Error creating pretrained tokenizer: {e}. Defaulting to version without 'auth_token'."
        )
        tokenizer = Tokenizer.from_pretrained(identifier, revision=revision)
    return {"type": "huggingface_tokenizer", "tokenizer": tokenizer}


def create_tokenizer(json: str):
    """
    Creates a tokenizer from a valid JSON string for use with `token_counter`.

    Args:
    json (str): A valid JSON string representing a previously serialized tokenizer

    Returns:
    dict: A dictionary with the tokenizer and its type.
    """

    tokenizer = Tokenizer.from_str(json)
    return {"type": "huggingface_tokenizer", "tokenizer": tokenizer}


def token_counter(
    model="",
    custom_tokenizer: Optional[Union[dict, SelectTokenizerResponse]] = None,
    text: Optional[Union[str, List[str]]] = None,
    messages: Optional[List] = None,
    count_response_tokens: Optional[bool] = False,
    tools: Optional[List[ChatCompletionToolParam]] = None,
    tool_choice: Optional[ChatCompletionNamedToolChoiceParam] = None,
    use_default_image_token_count: Optional[bool] = False,
    default_token_count: Optional[int] = None,
) -> int:
    """
    The same as `litellm.litellm_core_utils.token_counter`.

    Kept for backwards compatibility.
    """

    #########################################################
    # Flag to disable token counter
    # We've gotten reports of this consuming CPU cycles,
    # exposing this flag to allow users to disable
    # it to confirm if this is indeed the issue
    #########################################################
    if litellm.disable_token_counter is True:
        return 0

    return token_counter_new(
        model,
        custom_tokenizer,
        text,
        messages,
        count_response_tokens,
        tools,
        tool_choice,
        use_default_image_token_count,
        default_token_count,
    )


def supports_httpx_timeout(custom_llm_provider: str) -> bool:
    """
    Helper function to know if a provider implementation supports httpx timeout
    """
    supported_providers = ["openai", "azure", "bedrock"]

    if custom_llm_provider in supported_providers:
        return True

    return False


def supports_system_messages(model: str, custom_llm_provider: Optional[str]) -> bool:
    """
    Check if the given model supports system messages and return a boolean value.

    Parameters:
    model (str): The model name to be checked.
    custom_llm_provider (str): The provider to be checked.

    Returns:
    bool: True if the model supports system messages, False otherwise.

    Raises:
    Exception: If the given model is not found in model_prices_and_context_window.json.
    """
    return _supports_factory(
        model=model,
        custom_llm_provider=custom_llm_provider,
        key="supports_system_messages",
    )


def supports_web_search(model: str, custom_llm_provider: Optional[str] = None) -> bool:
    """
    Check if the given model supports web search and return a boolean value.

    Parameters:
    model (str): The model name to be checked.
    custom_llm_provider (str): The provider to be checked.

    Returns:
    bool: True if the model supports web search, False otherwise.

    Raises:
    Exception: If the given model is not found in model_prices_and_context_window.json.
    """
    return _supports_factory(
        model=model,
        custom_llm_provider=custom_llm_provider,
        key="supports_web_search",
    )


def supports_url_context(model: str, custom_llm_provider: Optional[str] = None) -> bool:
    """
    Check if the given model supports URL context and return a boolean value.

    Parameters:
    model (str): The model name to be checked.
    custom_llm_provider (str): The provider to be checked.

    Returns:
    bool: True if the model supports URL context, False otherwise.

    Raises:
    Exception: If the given model is not found in model_prices_and_context_window.json.
    """
    return _supports_factory(
        model=model,
        custom_llm_provider=custom_llm_provider,
        key="supports_url_context",
    )


def supports_native_streaming(model: str, custom_llm_provider: Optional[str]) -> bool:
    """
    Check if the given model supports native streaming and return a boolean value.

    Parameters:
    model (str): The model name to be checked.
    custom_llm_provider (str): The provider to be checked.

    Returns:
    bool: True if the model supports native streaming, False otherwise.

    Raises:
    Exception: If the given model is not found in model_prices_and_context_window.json.
    """
    try:
        model, custom_llm_provider, _, _ = litellm.get_llm_provider(
            model=model, custom_llm_provider=custom_llm_provider
        )

        model_info = _get_model_info_helper(
            model=model, custom_llm_provider=custom_llm_provider
        )
        supports_native_streaming = model_info.get("supports_native_streaming", True)
        if supports_native_streaming is None:
            supports_native_streaming = True
        return supports_native_streaming
    except Exception as e:
        verbose_logger.debug(
            f"Model not found or error in checking supports_native_streaming support. You passed model={model}, custom_llm_provider={custom_llm_provider}. Error: {str(e)}"
        )
        return False


def supports_response_schema(
    model: str, custom_llm_provider: Optional[str] = None
) -> bool:
    """
    Check if the given model + provider supports 'response_schema' as a param.

    Parameters:
    model (str): The model name to be checked.
    custom_llm_provider (str): The provider to be checked.

    Returns:
    bool: True if the model supports response_schema, False otherwise.

    Does not raise error. Defaults to 'False'. Outputs logging.error.
    """
    ## GET LLM PROVIDER ##
    try:
        model, custom_llm_provider, _, _ = get_llm_provider(
            model=model, custom_llm_provider=custom_llm_provider
        )
    except Exception as e:
        verbose_logger.debug(
            f"Model not found or error in checking response schema support. You passed model={model}, custom_llm_provider={custom_llm_provider}. Error: {str(e)}"
        )
        return False

    # providers that globally support response schema
    PROVIDERS_GLOBALLY_SUPPORT_RESPONSE_SCHEMA = [
        litellm.LlmProviders.PREDIBASE,
        litellm.LlmProviders.FIREWORKS_AI,
        litellm.LlmProviders.LM_STUDIO,
        litellm.LlmProviders.NEBIUS,
    ]

    if custom_llm_provider in PROVIDERS_GLOBALLY_SUPPORT_RESPONSE_SCHEMA:
        return True
    return _supports_factory(
        model=model,
        custom_llm_provider=custom_llm_provider,
        key="supports_response_schema",
    )


def supports_parallel_function_calling(
    model: str, custom_llm_provider: Optional[str] = None
) -> bool:
    """
    Check if the given model supports parallel tool calls and return a boolean value.
    """
    return _supports_factory(
        model=model,
        custom_llm_provider=custom_llm_provider,
        key="supports_parallel_function_calling",
    )


def supports_function_calling(
    model: str, custom_llm_provider: Optional[str] = None
) -> bool:
    """
    Check if the given model supports function calling and return a boolean value.

    Parameters:
    model (str): The model name to be checked.
    custom_llm_provider (Optional[str]): The provider to be checked.

    Returns:
    bool: True if the model supports function calling, False otherwise.

    Raises:
    Exception: If the given model is not found or there's an error in retrieval.
    """
    return _supports_factory(
        model=model,
        custom_llm_provider=custom_llm_provider,
        key="supports_function_calling",
    )


def supports_tool_choice(model: str, custom_llm_provider: Optional[str] = None) -> bool:
    """
    Check if the given model supports `tool_choice` and return a boolean value.
    """
    return _supports_factory(
        model=model, custom_llm_provider=custom_llm_provider, key="supports_tool_choice"
    )


def _supports_provider_info_factory(
    model: str, custom_llm_provider: Optional[str], key: str
) -> Optional[Literal[True]]:
    """
    Check if the given model supports a provider specific model info and return a boolean value.
    """

    provider_info = get_provider_info(
        model=model, custom_llm_provider=custom_llm_provider
    )

    if provider_info is not None and provider_info.get(key, False) is True:
        return True
    return None


def _supports_factory(model: str, custom_llm_provider: Optional[str], key: str) -> bool:
    """
    Check if the given model supports function calling and return a boolean value.

    Parameters:
    model (str): The model name to be checked.
    custom_llm_provider (Optional[str]): The provider to be checked.

    Returns:
    bool: True if the model supports function calling, False otherwise.

    Raises:
    Exception: If the given model is not found or there's an error in retrieval.
    """
    try:
        model, custom_llm_provider, _, _ = litellm.get_llm_provider(
            model=model, custom_llm_provider=custom_llm_provider
        )

        model_info = _get_model_info_helper(
            model=model, custom_llm_provider=custom_llm_provider
        )

        if model_info.get(key, False) is True:
            return True
        elif model_info.get(key) is None:  # don't check if 'False' explicitly set
            supported_by_provider = _supports_provider_info_factory(
                model, custom_llm_provider, key
            )
            if supported_by_provider is not None:
                return supported_by_provider

        return False
    except Exception as e:
        verbose_logger.debug(
            f"Model not found or error in checking {key} support. You passed model={model}, custom_llm_provider={custom_llm_provider}. Error: {str(e)}"
        )

        supported_by_provider = _supports_provider_info_factory(
            model, custom_llm_provider, key
        )
        if supported_by_provider is not None:
            return supported_by_provider

        return False


def supports_audio_input(model: str, custom_llm_provider: Optional[str] = None) -> bool:
    """Check if a given model supports audio input in a chat completion call"""
    return _supports_factory(
        model=model, custom_llm_provider=custom_llm_provider, key="supports_audio_input"
    )


def supports_pdf_input(model: str, custom_llm_provider: Optional[str] = None) -> bool:
    """Check if a given model supports pdf input in a chat completion call"""
    return _supports_factory(
        model=model, custom_llm_provider=custom_llm_provider, key="supports_pdf_input"
    )


def supports_audio_output(
    model: str, custom_llm_provider: Optional[str] = None
) -> bool:
    """Check if a given model supports audio output in a chat completion call"""
    return _supports_factory(
        model=model, custom_llm_provider=custom_llm_provider, key="supports_audio_input"
    )


def supports_prompt_caching(
    model: str, custom_llm_provider: Optional[str] = None
) -> bool:
    """
    Check if the given model supports prompt caching and return a boolean value.

    Parameters:
    model (str): The model name to be checked.
    custom_llm_provider (Optional[str]): The provider to be checked.

    Returns:
    bool: True if the model supports prompt caching, False otherwise.

    Raises:
    Exception: If the given model is not found or there's an error in retrieval.
    """
    return _supports_factory(
        model=model,
        custom_llm_provider=custom_llm_provider,
        key="supports_prompt_caching",
    )


def supports_computer_use(
    model: str, custom_llm_provider: Optional[str] = None
) -> bool:
    """
    Check if the given model supports computer use and return a boolean value.

    Parameters:
    model (str): The model name to be checked.
    custom_llm_provider (Optional[str]): The provider to be checked.

    Returns:
    bool: True if the model supports computer use, False otherwise.

    Raises:
    Exception: If the given model is not found or there's an error in retrieval.
    """
    return _supports_factory(
        model=model,
        custom_llm_provider=custom_llm_provider,
        key="supports_computer_use",
    )


def supports_vision(model: str, custom_llm_provider: Optional[str] = None) -> bool:
    """
    Check if the given model supports vision and return a boolean value.

    Parameters:
    model (str): The model name to be checked.
    custom_llm_provider (Optional[str]): The provider to be checked.

    Returns:
    bool: True if the model supports vision, False otherwise.
    """
    return _supports_factory(
        model=model,
        custom_llm_provider=custom_llm_provider,
        key="supports_vision",
    )


def supports_reasoning(model: str, custom_llm_provider: Optional[str] = None) -> bool:
    """
    Check if the given model supports reasoning and return a boolean value.
    """
    return _supports_factory(
        model=model, custom_llm_provider=custom_llm_provider, key="supports_reasoning"
    )


def get_supported_regions(
    model: str, custom_llm_provider: Optional[str] = None
) -> Optional[List[str]]:
    """
    Get a list of supported regions for a given model and provider.

    Parameters:
    model (str): The model name to be checked.
    custom_llm_provider (Optional[str]): The provider to be checked.
    """
    try:
        model, custom_llm_provider, _, _ = litellm.get_llm_provider(
            model=model, custom_llm_provider=custom_llm_provider
        )

        model_info = _get_model_info_helper(
            model=model, custom_llm_provider=custom_llm_provider
        )

        supported_regions = model_info.get("supported_regions", None)
        if supported_regions is None:
            return None

        #########################################################
        # Ensure only list supported regions are returned
        #########################################################
        if isinstance(supported_regions, list):
            return supported_regions
        else:
            return None
    except Exception as e:
        verbose_logger.debug(
            f"Model not found or error in checking supported_regions support. You passed model={model}, custom_llm_provider={custom_llm_provider}. Error: {str(e)}"
        )
        return None


def supports_embedding_image_input(
    model: str, custom_llm_provider: Optional[str] = None
) -> bool:
    """
    Check if the given model supports embedding image input and return a boolean value.
    """
    return _supports_factory(
        model=model,
        custom_llm_provider=custom_llm_provider,
        key="supports_embedding_image_input",
    )


####### HELPER FUNCTIONS ################
def _update_dictionary(existing_dict: Dict, new_dict: dict) -> dict:
    for k, v in new_dict.items():
        if v is not None:
            # Convert stringified numbers to appropriate numeric types
            existing_dict[k] = _convert_stringified_numbers(v)

    return existing_dict


def _convert_stringified_numbers(value):
    """Convert stringified numbers (including scientific notation) to appropriate numeric types."""
    if isinstance(value, str):
        try:
            # Try to convert to float first to handle scientific notation like "3e-07"
            if "e" in value.lower() or "." in value:
                return float(value)
            # Try to convert to int for whole numbers like "8192"
            else:
                return int(value)
        except (ValueError, TypeError):
            # If conversion fails, return the original string
            return value
    return value


def register_model(model_cost: Union[str, dict]):  # noqa: PLR0915
    """
    Register new / Override existing models (and their pricing) to specific providers.
    Provide EITHER a model cost dictionary or a url to a hosted json blob
    Example usage:
    model_cost_dict = {
        "gpt-4": {
            "max_tokens": 8192,
            "input_cost_per_token": 0.00003,
            "output_cost_per_token": 0.00006,
            "litellm_provider": "openai",
            "mode": "chat"
        },
    }
    """

    loaded_model_cost = {}
    if isinstance(model_cost, dict):
        # Convert stringified numbers to appropriate numeric types
        loaded_model_cost = model_cost
    elif isinstance(model_cost, str):
        loaded_model_cost = litellm.get_model_cost_map(url=model_cost)

    for key, value in loaded_model_cost.items():
        ## get model info ##
        try:
            existing_model: dict = cast(dict, get_model_info(model=key))
            model_cost_key = existing_model["key"]
        except Exception:
            existing_model = {}
            model_cost_key = key
        ## override / add new keys to the existing model cost dictionary
        updated_dictionary = _update_dictionary(existing_model, value)
        litellm.model_cost.setdefault(model_cost_key, {}).update(updated_dictionary)
        verbose_logger.debug(
            f"added/updated model={model_cost_key} in litellm.model_cost: {model_cost_key}"
        )
        # add new model names to provider lists
        if value.get("litellm_provider") == "openai":
            if key not in litellm.open_ai_chat_completion_models:
                litellm.open_ai_chat_completion_models.append(key)
        elif value.get("litellm_provider") == "text-completion-openai":
            if key not in litellm.open_ai_text_completion_models:
                litellm.open_ai_text_completion_models.append(key)
        elif value.get("litellm_provider") == "cohere":
            if key not in litellm.cohere_models:
                litellm.cohere_models.append(key)
        elif value.get("litellm_provider") == "anthropic":
            if key not in litellm.anthropic_models:
                litellm.anthropic_models.append(key)
        elif value.get("litellm_provider") == "openrouter":
            split_string = key.split("/", 1)
            if key not in litellm.openrouter_models:
                litellm.openrouter_models.append(split_string[1])
        elif value.get("litellm_provider") == "vertex_ai-text-models":
            if key not in litellm.vertex_text_models:
                litellm.vertex_text_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-code-text-models":
            if key not in litellm.vertex_code_text_models:
                litellm.vertex_code_text_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-chat-models":
            if key not in litellm.vertex_chat_models:
                litellm.vertex_chat_models.append(key)
        elif value.get("litellm_provider") == "vertex_ai-code-chat-models":
            if key not in litellm.vertex_code_chat_models:
                litellm.vertex_code_chat_models.append(key)
        elif value.get("litellm_provider") == "ai21":
            if key not in litellm.ai21_models:
                litellm.ai21_models.append(key)
        elif value.get("litellm_provider") == "nlp_cloud":
            if key not in litellm.nlp_cloud_models:
                litellm.nlp_cloud_models.append(key)
        elif value.get("litellm_provider") == "aleph_alpha":
            if key not in litellm.aleph_alpha_models:
                litellm.aleph_alpha_models.append(key)
        elif value.get("litellm_provider") == "bedrock":
            if key not in litellm.bedrock_models:
                litellm.bedrock_models.append(key)
        elif value.get("litellm_provider") == "novita":
            if key not in litellm.novita_models:
                litellm.novita_models.append(key)
    return model_cost


def _should_drop_param(k, additional_drop_params) -> bool:
    if (
        additional_drop_params is not None
        and isinstance(additional_drop_params, list)
        and k in additional_drop_params
    ):
        return True  # allow user to drop specific params for a model - e.g. vllm - logit bias

    return False


def _get_non_default_params(
    passed_params: dict, default_params: dict, additional_drop_params: Optional[bool]
) -> dict:
    non_default_params = {}
    for k, v in passed_params.items():
        if (
            k in default_params
            and v != default_params[k]
            and _should_drop_param(k=k, additional_drop_params=additional_drop_params)
            is False
        ):
            non_default_params[k] = v

    return non_default_params


def get_optional_params_transcription(
    model: str,
    custom_llm_provider: str,
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    response_format: Optional[str] = None,
    temperature: Optional[int] = None,
    timestamp_granularities: Optional[List[Literal["word", "segment"]]] = None,
    drop_params: Optional[bool] = None,
    **kwargs,
):
    from litellm.constants import OPENAI_TRANSCRIPTION_PARAMS

    # retrieve all parameters passed to the function
    passed_params = locals()
    custom_llm_provider = passed_params.pop("custom_llm_provider")
    drop_params = passed_params.pop("drop_params")
    special_params = passed_params.pop("kwargs")
    for k, v in special_params.items():
        passed_params[k] = v

    default_params = {
        "language": None,
        "prompt": None,
        "response_format": None,
        "temperature": None,  # openai defaults this to 0
    }

    non_default_params = {
        k: v
        for k, v in passed_params.items()
        if (k in default_params and v != default_params[k])
    }
    optional_params = {}

    ## raise exception if non-default value passed for non-openai/azure embedding calls
    def _check_valid_arg(supported_params):
        if len(non_default_params.keys()) > 0:
            keys = list(non_default_params.keys())
            for k in keys:
                if (
                    drop_params is True or litellm.drop_params is True
                ) and k not in supported_params:  # drop the unsupported non-default values
                    non_default_params.pop(k, None)
                elif k not in supported_params:
                    raise UnsupportedParamsError(
                        status_code=500,
                        message=f"Setting user/encoding format is not supported by {custom_llm_provider}. To drop it from the call, set `litellm.drop_params = True`.",
                    )
            return non_default_params

    provider_config: Optional[BaseAudioTranscriptionConfig] = None
    if custom_llm_provider is not None:
        provider_config = ProviderConfigManager.get_provider_audio_transcription_config(
            model=model,
            provider=LlmProviders(custom_llm_provider),
        )

    if custom_llm_provider == "openai" or custom_llm_provider == "azure":
        optional_params = non_default_params
    elif custom_llm_provider == "groq":
        supported_params = litellm.GroqSTTConfig().get_supported_openai_params_stt()
        _check_valid_arg(supported_params=supported_params)
        optional_params = litellm.GroqSTTConfig().map_openai_params_stt(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=drop_params if drop_params is not None else False,
        )
    elif provider_config is not None:  # handles fireworks ai, and any future providers
        supported_params = provider_config.get_supported_openai_params(model=model)
        _check_valid_arg(supported_params=supported_params)
        optional_params = provider_config.map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=drop_params if drop_params is not None else False,
        )
    optional_params = add_provider_specific_params_to_optional_params(
        optional_params=optional_params,
        passed_params=passed_params,
        custom_llm_provider=custom_llm_provider,
        openai_params=OPENAI_TRANSCRIPTION_PARAMS,
        additional_drop_params=kwargs.get("additional_drop_params", None),
    )

    return optional_params


def get_optional_params_image_gen(
    model: Optional[str] = None,
    n: Optional[int] = None,
    quality: Optional[str] = None,
    response_format: Optional[str] = None,
    size: Optional[str] = None,
    style: Optional[str] = None,
    user: Optional[str] = None,
    custom_llm_provider: Optional[str] = None,
    additional_drop_params: Optional[bool] = None,
    provider_config: Optional[BaseImageGenerationConfig] = None,
    drop_params: Optional[bool] = None,
    **kwargs,
):
    # retrieve all parameters passed to the function
    passed_params = locals()
    model = passed_params.pop("model", None)
    custom_llm_provider = passed_params.pop("custom_llm_provider")
    provider_config = passed_params.pop("provider_config", None)
    drop_params = passed_params.pop("drop_params", None)
    additional_drop_params = passed_params.pop("additional_drop_params", None)
    special_params = passed_params.pop("kwargs")
    for k, v in special_params.items():
        if k.startswith("aws_") and (
            custom_llm_provider != "bedrock" and custom_llm_provider != "sagemaker"
        ):  # allow dynamically setting boto3 init logic
            continue
        elif k == "hf_model_name" and custom_llm_provider != "sagemaker":
            continue
        elif (
            k.startswith("vertex_")
            and custom_llm_provider != "vertex_ai"
            and custom_llm_provider != "vertex_ai_beta"
        ):  # allow dynamically setting vertex ai init logic
            continue
        passed_params[k] = v

    default_params = {
        "n": None,
        "quality": None,
        "response_format": None,
        "size": None,
        "style": None,
        "user": None,
    }

    non_default_params = _get_non_default_params(
        passed_params=passed_params,
        default_params=default_params,
        additional_drop_params=additional_drop_params,
    )
    optional_params: Dict[str, Any] = {}

    ## raise exception if non-default value passed for non-openai/azure embedding calls
    def _check_valid_arg(supported_params):
        if len(non_default_params.keys()) > 0:
            keys = list(non_default_params.keys())
            for k in keys:
                if (
                    litellm.drop_params is True or drop_params is True
                ) and k not in supported_params:  # drop the unsupported non-default values
                    non_default_params.pop(k, None)
                elif k not in supported_params:
                    raise UnsupportedParamsError(
                        status_code=500,
                        message=f"Setting `{k}` is not supported by {custom_llm_provider}, {model}. To drop it from the call, set `litellm.drop_params = True`.",
                    )
            return non_default_params

    if provider_config is not None:
        supported_params = provider_config.get_supported_openai_params(
            model=model or ""
        )
        _check_valid_arg(supported_params=supported_params)
        optional_params = provider_config.map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model or "",
            drop_params=drop_params if drop_params is not None else False,
        )
    elif (
        custom_llm_provider == "openai"
        or custom_llm_provider == "azure"
        or custom_llm_provider in litellm.openai_compatible_providers
    ):
        optional_params = non_default_params
    elif custom_llm_provider == "bedrock":
        # use stability3 config class if model is a stability3 model
        config_class = (
            litellm.AmazonStability3Config
            if litellm.AmazonStability3Config._is_stability_3_model(model=model)
            else (
                litellm.AmazonNovaCanvasConfig
                if litellm.AmazonNovaCanvasConfig._is_nova_model(model=model)
                else litellm.AmazonStabilityConfig
            )
        )
        supported_params = config_class.get_supported_openai_params(model=model)
        _check_valid_arg(supported_params=supported_params)
        optional_params = config_class.map_openai_params(
            non_default_params=non_default_params, optional_params={}
        )
    elif custom_llm_provider == "vertex_ai":
        supported_params = ["n"]
        """
        All params here: https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/imagegeneration?project=adroit-crow-413218
        """
        _check_valid_arg(supported_params=supported_params)
        if n is not None:
            optional_params["sampleCount"] = int(n)

    for k in passed_params.keys():
        if k not in default_params.keys():
            optional_params[k] = passed_params[k]
    return optional_params


def get_optional_params_embeddings(  # noqa: PLR0915
    # 2 optional params
    model: str,
    user: Optional[str] = None,
    encoding_format: Optional[str] = None,
    dimensions: Optional[int] = None,
    custom_llm_provider="",
    drop_params: Optional[bool] = None,
    additional_drop_params: Optional[List[str]] = None,
    **kwargs,
):
    # retrieve all parameters passed to the function
    passed_params = locals()
    custom_llm_provider = passed_params.pop("custom_llm_provider", None)
    special_params = passed_params.pop("kwargs")

    drop_params = passed_params.pop("drop_params", None)
    additional_drop_params = passed_params.pop("additional_drop_params", None)

    def _check_valid_arg(supported_params: Optional[list]):
        if supported_params is None:
            return
        unsupported_params = {}
        for k in non_default_params.keys():
            if k not in supported_params:
                unsupported_params[k] = non_default_params[k]
        if unsupported_params:
            if litellm.drop_params is True or (
                drop_params is not None and drop_params is True
            ):
                pass
            else:
                raise UnsupportedParamsError(
                    status_code=500,
                    message=f"{custom_llm_provider} does not support parameters: {unsupported_params}, for model={model}. To drop these, set `litellm.drop_params=True` or for proxy:\n\n`litellm_settings:\n drop_params: true`\n",
                )

    non_default_params = (
        PreProcessNonDefaultParams.embedding_pre_process_non_default_params(
            passed_params=passed_params,
            special_params=special_params,
            custom_llm_provider=custom_llm_provider,
            additional_drop_params=additional_drop_params,
            model=model,
        )
    )

    provider_config: Optional[BaseEmbeddingConfig] = None

    optional_params = {}
    if (
        custom_llm_provider is not None
        and custom_llm_provider in LlmProviders._member_map_.values()
    ):
        provider_config = ProviderConfigManager.get_provider_embedding_config(
            model=model,
            provider=LlmProviders(custom_llm_provider),
        )

    if provider_config is not None:
        supported_params: Optional[list] = provider_config.get_supported_openai_params(
            model=model
        )
        _check_valid_arg(supported_params=supported_params)
        optional_params = provider_config.map_openai_params(
            non_default_params=non_default_params,
            optional_params={},
            model=model,
            drop_params=drop_params if drop_params is not None else False,
        )
    ## raise exception if non-default value passed for non-openai/azure embedding calls
    elif custom_llm_provider == "openai":
        # 'dimensions` is only supported in `text-embedding-3` and later models

        if (
            model is not None
            and "text-embedding-3" not in model
            and "dimensions" in non_default_params.keys()
        ):
            raise UnsupportedParamsError(
                status_code=500,
                message="Setting dimensions is not supported for OpenAI `text-embedding-3` and later models. To drop it from the call, set `litellm.drop_params = True`.",
            )
        else:
            optional_params = non_default_params
    elif custom_llm_provider == "triton":
        supported_params = get_supported_openai_params(
            model=model,
            custom_llm_provider=custom_llm_provider,
            request_type="embeddings",
        )
        _check_valid_arg(supported_params=supported_params)
        optional_params = litellm.TritonEmbeddingConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params={},
            model=model,
            drop_params=drop_params if drop_params is not None else False,
        )
    elif custom_llm_provider == "databricks":
        supported_params = get_supported_openai_params(
            model=model or "",
            custom_llm_provider="databricks",
            request_type="embeddings",
        )
        _check_valid_arg(supported_params=supported_params)
        optional_params = litellm.DatabricksEmbeddingConfig().map_openai_params(
            non_default_params=non_default_params, optional_params={}
        )

    elif custom_llm_provider == "nvidia_nim":
        supported_params = get_supported_openai_params(
            model=model or "",
            custom_llm_provider="nvidia_nim",
            request_type="embeddings",
        )
        _check_valid_arg(supported_params=supported_params)
        optional_params = litellm.nvidiaNimEmbeddingConfig.map_openai_params(
            non_default_params=non_default_params, optional_params={}, kwargs=kwargs
        )
    elif custom_llm_provider == "vertex_ai" or custom_llm_provider == "gemini":
        supported_params = get_supported_openai_params(
            model=model,
            custom_llm_provider="vertex_ai",
            request_type="embeddings",
        )
        _check_valid_arg(supported_params=supported_params)
        (
            optional_params,
            kwargs,
        ) = litellm.VertexAITextEmbeddingConfig().map_openai_params(
            non_default_params=non_default_params, optional_params={}, kwargs=kwargs
        )
    elif custom_llm_provider == "lm_studio":
        supported_params = (
            litellm.LmStudioEmbeddingConfig().get_supported_openai_params()
        )
        _check_valid_arg(supported_params=supported_params)
        optional_params = litellm.LmStudioEmbeddingConfig().map_openai_params(
            non_default_params=non_default_params, optional_params={}
        )
    elif custom_llm_provider == "bedrock":
        # if dimensions is in non_default_params -> pass it for model=bedrock/amazon.titan-embed-text-v2
        if "amazon.titan-embed-text-v1" in model:
            object: Any = litellm.AmazonTitanG1Config()
        elif "amazon.titan-embed-image-v1" in model:
            object = litellm.AmazonTitanMultimodalEmbeddingG1Config()
        elif "amazon.titan-embed-text-v2:0" in model:
            object = litellm.AmazonTitanV2Config()
        elif "cohere.embed-multilingual-v3" in model:
            object = litellm.BedrockCohereEmbeddingConfig()
        else:  # unmapped model
            supported_params = []
            _check_valid_arg(supported_params=supported_params)
            final_params = {**kwargs}
            return final_params

        supported_params = object.get_supported_openai_params()
        _check_valid_arg(supported_params=supported_params)
        optional_params = object.map_openai_params(
            non_default_params=non_default_params, optional_params={}
        )
    elif custom_llm_provider == "mistral":
        supported_params = get_supported_openai_params(
            model=model,
            custom_llm_provider="mistral",
            request_type="embeddings",
        )
        _check_valid_arg(supported_params=supported_params)
        optional_params = litellm.MistralEmbeddingConfig().map_openai_params(
            non_default_params=non_default_params, optional_params={}
        )
    elif custom_llm_provider == "jina_ai":
        supported_params = get_supported_openai_params(
            model=model,
            custom_llm_provider="jina_ai",
            request_type="embeddings",
        )
        _check_valid_arg(supported_params=supported_params)
        optional_params = litellm.JinaAIEmbeddingConfig().map_openai_params(
            non_default_params=non_default_params, optional_params={}
        )
    elif custom_llm_provider == "voyage":
        supported_params = get_supported_openai_params(
            model=model,
            custom_llm_provider="voyage",
            request_type="embeddings",
        )
        _check_valid_arg(supported_params=supported_params)
        optional_params = litellm.VoyageEmbeddingConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params={},
            model=model,
            drop_params=drop_params if drop_params is not None else False,
        )
    elif custom_llm_provider == "infinity":
        supported_params = get_supported_openai_params(
            model=model,
            custom_llm_provider="infinity",
            request_type="embeddings",
        )
        _check_valid_arg(supported_params=supported_params)
        optional_params = litellm.InfinityEmbeddingConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params={},
            model=model,
            drop_params=drop_params if drop_params is not None else False,
        )
    elif custom_llm_provider == "fireworks_ai":
        supported_params = get_supported_openai_params(
            model=model,
            custom_llm_provider="fireworks_ai",
            request_type="embeddings",
        )
        _check_valid_arg(supported_params=supported_params)
        optional_params = litellm.FireworksAIEmbeddingConfig().map_openai_params(
            non_default_params=non_default_params, optional_params={}, model=model
        )

    elif (
        custom_llm_provider != "openai"
        and custom_llm_provider != "azure"
        and custom_llm_provider not in litellm.openai_compatible_providers
    ):
        if len(non_default_params.keys()) > 0:
            if (
                litellm.drop_params is True or drop_params is True
            ):  # drop the unsupported non-default values
                keys = list(non_default_params.keys())
                for k in keys:
                    non_default_params.pop(k, None)
            else:
                raise UnsupportedParamsError(
                    status_code=500,
                    message=f"Setting {non_default_params} is not supported by {custom_llm_provider}. To drop it from the call, set `litellm.drop_params = True`.",
                )
        else:
            optional_params = non_default_params
    else:
        optional_params = non_default_params

    final_params = add_provider_specific_params_to_optional_params(
        optional_params=optional_params,
        passed_params=passed_params,
        custom_llm_provider=custom_llm_provider,
        openai_params=list(DEFAULT_EMBEDDING_PARAM_VALUES.keys()),
        additional_drop_params=kwargs.get("additional_drop_params", None),
    )

    if "extra_body" in final_params and len(final_params["extra_body"]) == 0:
        final_params.pop("extra_body", None)

    return final_params


def _remove_additional_properties(schema):
    """
    clean out 'additionalProperties = False'. Causes vertexai/gemini OpenAI API Schema errors - https://github.com/langchain-ai/langchainjs/issues/5240

    Relevant Issues: https://github.com/BerriAI/litellm/issues/6136, https://github.com/BerriAI/litellm/issues/6088
    """
    if isinstance(schema, dict):
        # Remove the 'additionalProperties' key if it exists and is set to False
        if "additionalProperties" in schema and schema["additionalProperties"] is False:
            del schema["additionalProperties"]

        # Recursively process all dictionary values
        for key, value in schema.items():
            _remove_additional_properties(value)

    elif isinstance(schema, list):
        # Recursively process all items in the list
        for item in schema:
            _remove_additional_properties(item)

    return schema


def _remove_strict_from_schema(schema):
    """
    Relevant Issues: https://github.com/BerriAI/litellm/issues/6136, https://github.com/BerriAI/litellm/issues/6088
    """
    if isinstance(schema, dict):
        # Remove the 'additionalProperties' key if it exists and is set to False
        if "strict" in schema:
            del schema["strict"]

        # Recursively process all dictionary values
        for key, value in schema.items():
            _remove_strict_from_schema(value)

    elif isinstance(schema, list):
        # Recursively process all items in the list
        for item in schema:
            _remove_strict_from_schema(item)

    return schema


def _remove_unsupported_params(
    non_default_params: dict, supported_openai_params: Optional[List[str]]
) -> dict:
    """
    Remove unsupported params from non_default_params
    """
    remove_keys = []
    if supported_openai_params is None:
        return {}  # no supported params, so no optional openai params to send
    for param in non_default_params.keys():
        if param not in supported_openai_params:
            remove_keys.append(param)
    for key in remove_keys:
        non_default_params.pop(key, None)
    return non_default_params


class PreProcessNonDefaultParams:
    @staticmethod
    def base_pre_process_non_default_params(
        passed_params: dict,
        special_params: dict,
        custom_llm_provider: str,
        additional_drop_params: Optional[List[str]],
        default_param_values: dict,
        additional_endpoint_specific_params: List[str],
    ) -> dict:
        for k, v in special_params.items():
            if k.startswith("aws_") and (
                custom_llm_provider != "bedrock"
                and not custom_llm_provider.startswith("sagemaker")
            ):  # allow dynamically setting boto3 init logic
                continue
            elif k == "hf_model_name" and custom_llm_provider != "sagemaker":
                continue
            elif (
                k.startswith("vertex_")
                and custom_llm_provider != "vertex_ai"
                and custom_llm_provider != "vertex_ai_beta"
            ):  # allow dynamically setting vertex ai init logic
                continue
            passed_params[k] = v

        # filter out those parameters that were passed with non-default values
        non_default_params = {
            k: v
            for k, v in passed_params.items()
            if (
                k != "model"
                and k != "custom_llm_provider"
                and k != "api_version"
                and k != "drop_params"
                and k != "allowed_openai_params"
                and k != "additional_drop_params"
                and k not in additional_endpoint_specific_params
                and k in default_param_values
                and v != default_param_values[k]
                and _should_drop_param(
                    k=k, additional_drop_params=additional_drop_params
                )
                is False
            )
        }

        return non_default_params

    @staticmethod
    def embedding_pre_process_non_default_params(
        passed_params: dict,
        special_params: dict,
        custom_llm_provider: str,
        additional_drop_params: Optional[List[str]],
        model: str,
        remove_sensitive_keys: bool = False,
        add_provider_specific_params: bool = False,
    ) -> dict:
        non_default_params = (
            PreProcessNonDefaultParams.base_pre_process_non_default_params(
                passed_params=passed_params,
                special_params=special_params,
                custom_llm_provider=custom_llm_provider,
                additional_drop_params=additional_drop_params,
                default_param_values={k: None for k in OPENAI_EMBEDDING_PARAMS},
                additional_endpoint_specific_params=["input"],
            )
        )

        return non_default_params


def pre_process_non_default_params(
    passed_params: dict,
    special_params: dict,
    custom_llm_provider: str,
    additional_drop_params: Optional[List[str]],
    model: str,
    remove_sensitive_keys: bool = False,
    add_provider_specific_params: bool = False,
) -> dict:
    """
    Pre-process non-default params to a standardized format
    """
    # retrieve all parameters passed to the function

    non_default_params = PreProcessNonDefaultParams.base_pre_process_non_default_params(
        passed_params=passed_params,
        special_params=special_params,
        custom_llm_provider=custom_llm_provider,
        additional_drop_params=additional_drop_params,
        default_param_values=DEFAULT_CHAT_COMPLETION_PARAM_VALUES,
        additional_endpoint_specific_params=["messages"],
    )

    provider_config: Optional[BaseConfig] = None
    if custom_llm_provider is not None and custom_llm_provider in [
        provider.value for provider in LlmProviders
    ]:
        provider_config = ProviderConfigManager.get_provider_chat_config(
            model=model, provider=LlmProviders(custom_llm_provider)
        )

    if "response_format" in non_default_params:
        if provider_config is not None:
            non_default_params[
                "response_format"
            ] = provider_config.get_json_schema_from_pydantic_object(
                response_format=non_default_params["response_format"]
            )
        else:
            non_default_params["response_format"] = type_to_response_format_param(
                response_format=non_default_params["response_format"]
            )

    if "tools" in non_default_params and isinstance(
        non_default_params, list
    ):  # fixes https://github.com/BerriAI/litellm/issues/4933
        tools = non_default_params["tools"]
        for (
            tool
        ) in (
            tools
        ):  # clean out 'additionalProperties = False'. Causes vertexai/gemini OpenAI API Schema errors - https://github.com/langchain-ai/langchainjs/issues/5240
            tool_function = tool.get("function", {})
            parameters = tool_function.get("parameters", None)
            if parameters is not None:
                new_parameters = copy.deepcopy(parameters)
                if (
                    "additionalProperties" in new_parameters
                    and new_parameters["additionalProperties"] is False
                ):
                    new_parameters.pop("additionalProperties", None)
                tool_function["parameters"] = new_parameters

    if add_provider_specific_params:
        non_default_params = add_provider_specific_params_to_optional_params(
            optional_params=non_default_params,
            passed_params=passed_params,
            custom_llm_provider=custom_llm_provider,
            openai_params=list(DEFAULT_CHAT_COMPLETION_PARAM_VALUES.keys()),
            additional_drop_params=additional_drop_params,
        )

    if remove_sensitive_keys:
        non_default_params = remove_sensitive_keys_from_dict(non_default_params)
    return non_default_params


def remove_sensitive_keys_from_dict(d: dict) -> dict:
    """
    Remove sensitive keys from a dictionary
    """
    sensitive_key_phrases = ["key", "secret", "access", "credential"]
    remove_keys = []
    for key in d.keys():
        if any(phrase in key.lower() for phrase in sensitive_key_phrases):
            remove_keys.append(key)
    for key in remove_keys:
        d.pop(key)
    return d


def pre_process_optional_params(
    passed_params: dict, non_default_params: dict, custom_llm_provider: str
) -> dict:
    """For .completion(), preprocess optional params"""
    optional_params: Dict = {}

    common_auth_dict = litellm.common_cloud_provider_auth_params
    if custom_llm_provider in common_auth_dict["providers"]:
        """
        Check if params = ["project", "region_name", "token"]
        and correctly translate for = ["azure", "vertex_ai", "watsonx", "aws"]
        """
        if custom_llm_provider == "azure":
            optional_params = litellm.AzureOpenAIConfig().map_special_auth_params(
                non_default_params=passed_params, optional_params=optional_params
            )
        elif custom_llm_provider == "bedrock":
            optional_params = (
                litellm.AmazonBedrockGlobalConfig().map_special_auth_params(
                    non_default_params=passed_params, optional_params=optional_params
                )
            )
        elif (
            custom_llm_provider == "vertex_ai"
            or custom_llm_provider == "vertex_ai_beta"
        ):
            optional_params = litellm.VertexAIConfig().map_special_auth_params(
                non_default_params=passed_params, optional_params=optional_params
            )
        elif custom_llm_provider == "watsonx":
            optional_params = litellm.IBMWatsonXAIConfig().map_special_auth_params(
                non_default_params=passed_params, optional_params=optional_params
            )

    ## raise exception if function calling passed in for a provider that doesn't support it
    if (
        "functions" in non_default_params
        or "function_call" in non_default_params
        or "tools" in non_default_params
    ):
        if (
            custom_llm_provider == "ollama"
            and custom_llm_provider != "text-completion-openai"
            and custom_llm_provider != "azure"
            and custom_llm_provider != "vertex_ai"
            and custom_llm_provider != "anyscale"
            and custom_llm_provider != "together_ai"
            and custom_llm_provider != "groq"
            and custom_llm_provider != "nvidia_nim"
            and custom_llm_provider != "cerebras"
            and custom_llm_provider != "xai"
            and custom_llm_provider != "ai21_chat"
            and custom_llm_provider != "volcengine"
            and custom_llm_provider != "deepseek"
            and custom_llm_provider != "codestral"
            and custom_llm_provider != "mistral"
            and custom_llm_provider != "anthropic"
            and custom_llm_provider != "cohere_chat"
            and custom_llm_provider != "cohere"
            and custom_llm_provider != "bedrock"
            and custom_llm_provider != "ollama_chat"
            and custom_llm_provider != "openrouter"
            and custom_llm_provider != "nebius"
            and custom_llm_provider not in litellm.openai_compatible_providers
        ):
            if custom_llm_provider == "ollama":
                # ollama actually supports json output
                optional_params["format"] = "json"
                litellm.add_function_to_prompt = (
                    True  # so that main.py adds the function call to the prompt
                )
                if "tools" in non_default_params:
                    optional_params[
                        "functions_unsupported_model"
                    ] = non_default_params.pop("tools")
                    non_default_params.pop(
                        "tool_choice", None
                    )  # causes ollama requests to hang
                elif "functions" in non_default_params:
                    optional_params[
                        "functions_unsupported_model"
                    ] = non_default_params.pop("functions")
            elif (
                litellm.add_function_to_prompt
            ):  # if user opts to add it to prompt instead
                optional_params["functions_unsupported_model"] = non_default_params.pop(
                    "tools", non_default_params.pop("functions", None)
                )
            else:
                raise UnsupportedParamsError(
                    status_code=500,
                    message=f"Function calling is not supported by {custom_llm_provider}.",
                )

    return optional_params


def get_optional_params(  # noqa: PLR0915
    # use the openai defaults
    # https://platform.openai.com/docs/api-reference/chat/create
    model: str,
    functions=None,
    function_call=None,
    temperature=None,
    top_p=None,
    n=None,
    stream=False,
    stream_options=None,
    stop=None,
    max_tokens=None,
    max_completion_tokens=None,
    modalities=None,
    prediction=None,
    audio=None,
    presence_penalty=None,
    frequency_penalty=None,
    logit_bias=None,
    user=None,
    custom_llm_provider="",
    response_format=None,
    seed=None,
    tools=None,
    tool_choice=None,
    max_retries=None,
    logprobs=None,
    top_logprobs=None,
    extra_headers=None,
    api_version=None,
    parallel_tool_calls=None,
    drop_params=None,
    allowed_openai_params: Optional[List[str]] = None,
    reasoning_effort=None,
    additional_drop_params=None,
    messages: Optional[List[AllMessageValues]] = None,
    thinking: Optional[AnthropicThinkingParam] = None,
    web_search_options: Optional[OpenAIWebSearchOptions] = None,
    **kwargs,
):
    passed_params = locals().copy()
    special_params = passed_params.pop("kwargs")
    non_default_params = pre_process_non_default_params(
        passed_params=passed_params,
        special_params=special_params,
        custom_llm_provider=custom_llm_provider,
        additional_drop_params=additional_drop_params,
        model=model,
    )
    optional_params = pre_process_optional_params(
        passed_params=passed_params,
        non_default_params=non_default_params,
        custom_llm_provider=custom_llm_provider,
    )
    provider_config: Optional[BaseConfig] = None
    if custom_llm_provider is not None and custom_llm_provider in [
        provider.value for provider in LlmProviders
    ]:
        provider_config = ProviderConfigManager.get_provider_chat_config(
            model=model, provider=LlmProviders(custom_llm_provider)
        )

    def _check_valid_arg(supported_params: List[str]):
        """
        Check if the params passed to completion() are supported by the provider

        Args:
            supported_params: List[str] - supported params from the litellm config
        """
        verbose_logger.info(
            f"\nLiteLLM completion() model= {model}; provider = {custom_llm_provider}"
        )
        verbose_logger.debug(
            f"\nLiteLLM: Params passed to completion() {passed_params}"
        )
        verbose_logger.debug(
            f"\nLiteLLM: Non-Default params passed to completion() {non_default_params}"
        )
        unsupported_params = {}
        for k in non_default_params.keys():
            if k not in supported_params:
                if k == "user" or k == "stream_options" or k == "stream":
                    continue
                if k == "n" and n == 1:  # langchain sends n=1 as a default value
                    continue  # skip this param
                if (
                    k == "max_retries"
                ):  # TODO: This is a patch. We support max retries for OpenAI, Azure. For non OpenAI LLMs we need to add support for max retries
                    continue  # skip this param
                # Always keeps this in elif code blocks
                else:
                    unsupported_params[k] = non_default_params[k]

        if unsupported_params:
            if litellm.drop_params is True or (
                drop_params is not None and drop_params is True
            ):
                for k in unsupported_params.keys():
                    non_default_params.pop(k, None)
            else:
                raise UnsupportedParamsError(
                    status_code=500,
                    message=f"{custom_llm_provider} does not support parameters: {list(unsupported_params.keys())}, for model={model}. To drop these, set `litellm.drop_params=True` or for proxy:\n\n`litellm_settings:\n drop_params: true`\n. \n If you want to use these params dynamically send allowed_openai_params={list(unsupported_params.keys())} in your request.",
                )

    supported_params = get_supported_openai_params(
        model=model, custom_llm_provider=custom_llm_provider
    )
    if supported_params is None:
        supported_params = get_supported_openai_params(
            model=model, custom_llm_provider="openai"
        )

    supported_params = supported_params or []
    allowed_openai_params = allowed_openai_params or []
    supported_params.extend(allowed_openai_params)

    _check_valid_arg(
        supported_params=supported_params or [],
    )
    ## raise exception if provider doesn't support passed in param
    if custom_llm_provider == "anthropic":
        ## check if unsupported param passed in
        optional_params = litellm.AnthropicConfig().map_openai_params(
            model=model,
            non_default_params=non_default_params,
            optional_params=optional_params,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "anthropic_text":
        optional_params = litellm.AnthropicTextConfig().map_openai_params(
            model=model,
            non_default_params=non_default_params,
            optional_params=optional_params,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
        optional_params = litellm.AnthropicTextConfig().map_openai_params(
            model=model,
            non_default_params=non_default_params,
            optional_params=optional_params,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )

    elif custom_llm_provider == "cohere":
        ## check if unsupported param passed in
        # handle cohere params
        optional_params = litellm.CohereConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "cohere_chat":
        # handle cohere params
        optional_params = litellm.CohereChatConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "triton":
        optional_params = litellm.TritonConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=drop_params if drop_params is not None else False,
        )

    elif custom_llm_provider == "maritalk":
        optional_params = litellm.MaritalkConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "replicate":
        optional_params = litellm.ReplicateConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "predibase":
        optional_params = litellm.PredibaseConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "huggingface":
        optional_params = litellm.HuggingFaceChatConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "together_ai":
        optional_params = litellm.TogetherAIConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "vertex_ai" and (
        model in litellm.vertex_chat_models
        or model in litellm.vertex_code_chat_models
        or model in litellm.vertex_text_models
        or model in litellm.vertex_code_text_models
        or model in litellm.vertex_language_models
        or model in litellm.vertex_vision_models
    ):
        optional_params = litellm.VertexGeminiConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )

    elif custom_llm_provider == "gemini":
        optional_params = litellm.GoogleAIStudioGeminiConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "vertex_ai_beta" or (
        custom_llm_provider == "vertex_ai" and "gemini" in model
    ):
        optional_params = litellm.VertexGeminiConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif litellm.VertexAIAnthropicConfig.is_supported_model(
        model=model, custom_llm_provider=custom_llm_provider
    ):
        optional_params = litellm.VertexAIAnthropicConfig().map_openai_params(
            model=model,
            non_default_params=non_default_params,
            optional_params=optional_params,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "vertex_ai":
        if model in litellm.vertex_mistral_models:
            if "codestral" in model:
                optional_params = (
                    litellm.CodestralTextCompletionConfig().map_openai_params(
                        model=model,
                        non_default_params=non_default_params,
                        optional_params=optional_params,
                        drop_params=(
                            drop_params
                            if drop_params is not None and isinstance(drop_params, bool)
                            else False
                        ),
                    )
                )
            else:
                optional_params = litellm.MistralConfig().map_openai_params(
                    model=model,
                    non_default_params=non_default_params,
                    optional_params=optional_params,
                    drop_params=(
                        drop_params
                        if drop_params is not None and isinstance(drop_params, bool)
                        else False
                    ),
                )
        elif model in litellm.vertex_ai_ai21_models:
            optional_params = litellm.VertexAIAi21Config().map_openai_params(
                non_default_params=non_default_params,
                optional_params=optional_params,
                model=model,
                drop_params=(
                    drop_params
                    if drop_params is not None and isinstance(drop_params, bool)
                    else False
                ),
            )
        else:  # use generic openai-like param mapping
            optional_params = litellm.VertexAILlama3Config().map_openai_params(
                non_default_params=non_default_params,
                optional_params=optional_params,
                model=model,
                drop_params=(
                    drop_params
                    if drop_params is not None and isinstance(drop_params, bool)
                    else False
                ),
            )

    elif custom_llm_provider == "sagemaker":
        # temperature, top_p, n, stream, stop, max_tokens, n, presence_penalty default to None
        optional_params = litellm.SagemakerConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "bedrock":
        bedrock_route = BedrockModelInfo.get_bedrock_route(model)
        bedrock_base_model = BedrockModelInfo.get_base_model(model)
        if bedrock_route == "converse" or bedrock_route == "converse_like":
            optional_params = litellm.AmazonConverseConfig().map_openai_params(
                model=model,
                non_default_params=non_default_params,
                optional_params=optional_params,
                drop_params=(
                    drop_params
                    if drop_params is not None and isinstance(drop_params, bool)
                    else False
                ),
            )

        elif "anthropic" in bedrock_base_model and bedrock_route == "invoke":
            if bedrock_base_model.startswith("anthropic.claude-3"):
                optional_params = (
                    litellm.AmazonAnthropicClaude3Config().map_openai_params(
                        non_default_params=non_default_params,
                        optional_params=optional_params,
                        model=model,
                        drop_params=(
                            drop_params
                            if drop_params is not None and isinstance(drop_params, bool)
                            else False
                        ),
                    )
                )

            else:
                optional_params = litellm.AmazonAnthropicConfig().map_openai_params(
                    non_default_params=non_default_params,
                    optional_params=optional_params,
                    model=model,
                    drop_params=(
                        drop_params
                        if drop_params is not None and isinstance(drop_params, bool)
                        else False
                    ),
                )
        elif provider_config is not None:
            optional_params = provider_config.map_openai_params(
                non_default_params=non_default_params,
                optional_params=optional_params,
                model=model,
                drop_params=(
                    drop_params
                    if drop_params is not None and isinstance(drop_params, bool)
                    else False
                ),
            )
    elif custom_llm_provider == "cloudflare":
        optional_params = litellm.CloudflareChatConfig().map_openai_params(
            model=model,
            non_default_params=non_default_params,
            optional_params=optional_params,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "ollama":
        optional_params = litellm.OllamaConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "ollama_chat":
        optional_params = litellm.OllamaChatConfig().map_openai_params(
            model=model,
            non_default_params=non_default_params,
            optional_params=optional_params,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "nlp_cloud":
        optional_params = litellm.NLPCloudConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )

    elif custom_llm_provider == "petals":
        optional_params = litellm.PetalsConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "deepinfra":
        optional_params = litellm.DeepInfraConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "perplexity" and provider_config is not None:
        optional_params = provider_config.map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "mistral" or custom_llm_provider == "codestral":
        optional_params = litellm.MistralConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "text-completion-codestral":
        optional_params = litellm.CodestralTextCompletionConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )

    elif custom_llm_provider == "databricks":
        optional_params = litellm.DatabricksConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "nvidia_nim":
        optional_params = litellm.NvidiaNimConfig().map_openai_params(
            model=model,
            non_default_params=non_default_params,
            optional_params=optional_params,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "cerebras":
        optional_params = litellm.CerebrasConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "xai":
        optional_params = litellm.XAIChatConfig().map_openai_params(
            model=model,
            non_default_params=non_default_params,
            optional_params=optional_params,
        )
    elif custom_llm_provider == "ai21_chat" or custom_llm_provider == "ai21":
        optional_params = litellm.AI21ChatConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "fireworks_ai":
        optional_params = litellm.FireworksAIConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "volcengine":
        optional_params = litellm.VolcEngineConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "hosted_vllm":
        optional_params = litellm.HostedVLLMChatConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "vllm":
        optional_params = litellm.VLLMConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "groq":
        optional_params = litellm.GroqChatConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "deepseek":
        optional_params = litellm.OpenAIConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "openrouter":
        optional_params = litellm.OpenrouterConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )

    elif custom_llm_provider == "watsonx":
        optional_params = litellm.IBMWatsonXChatConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
        # WatsonX-text param check
        for param in passed_params.keys():
            if litellm.IBMWatsonXAIConfig().is_watsonx_text_param(param):
                raise ValueError(
                    f"LiteLLM now defaults to Watsonx's `/text/chat` endpoint. Please use the `watsonx_text` provider instead, to call the `/text/generation` endpoint. Param: {param}"
                )
    elif custom_llm_provider == "watsonx_text":
        optional_params = litellm.IBMWatsonXAIConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "openai":
        optional_params = litellm.OpenAIConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "nebius":
        optional_params = litellm.NebiusConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    elif custom_llm_provider == "azure":
        if litellm.AzureOpenAIO1Config().is_o_series_model(model=model):
            optional_params = litellm.AzureOpenAIO1Config().map_openai_params(
                non_default_params=non_default_params,
                optional_params=optional_params,
                model=model,
                drop_params=(
                    drop_params
                    if drop_params is not None and isinstance(drop_params, bool)
                    else False
                ),
            )
        else:
            verbose_logger.debug(
                "Azure optional params - api_version: api_version={}, litellm.api_version={}, os.environ['AZURE_API_VERSION']={}".format(
                    api_version, litellm.api_version, get_secret("AZURE_API_VERSION")
                )
            )
            api_version = (
                api_version
                or litellm.api_version
                or get_secret("AZURE_API_VERSION")
                or litellm.AZURE_DEFAULT_API_VERSION
            )
            optional_params = litellm.AzureOpenAIConfig().map_openai_params(
                non_default_params=non_default_params,
                optional_params=optional_params,
                model=model,
                api_version=api_version,  # type: ignore
                drop_params=(
                    drop_params
                    if drop_params is not None and isinstance(drop_params, bool)
                    else False
                ),
            )
    elif provider_config is not None:
        optional_params = provider_config.map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    else:  # assume passing in params for openai-like api
        optional_params = litellm.OpenAILikeChatConfig().map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=(
                drop_params
                if drop_params is not None and isinstance(drop_params, bool)
                else False
            ),
        )
    # if user passed in non-default kwargs for specific providers/models, pass them along
    optional_params = add_provider_specific_params_to_optional_params(
        optional_params=optional_params,
        passed_params=passed_params,
        custom_llm_provider=custom_llm_provider,
        openai_params=list(DEFAULT_CHAT_COMPLETION_PARAM_VALUES.keys()),
        additional_drop_params=additional_drop_params,
    )
    print_verbose(f"Final returned optional params: {optional_params}")
    optional_params = _apply_openai_param_overrides(
        optional_params=optional_params,
        non_default_params=non_default_params,
        allowed_openai_params=allowed_openai_params,
    )
    return optional_params


def add_provider_specific_params_to_optional_params(
    optional_params: dict,
    passed_params: dict,
    custom_llm_provider: str,
    openai_params: List[str],
    additional_drop_params: Optional[list] = None,
) -> dict:
    """
    Add provider specific params to optional_params
    """
    if (
        custom_llm_provider
        in ["openai", "azure", "text-completion-openai"]
        + litellm.openai_compatible_providers
    ):
        # for openai, azure we should pass the extra/passed params within `extra_body` https://github.com/openai/openai-python/blob/ac33853ba10d13ac149b1fa3ca6dba7d613065c9/src/openai/resources/models.py#L46
        if (
            _should_drop_param(
                k="extra_body", additional_drop_params=additional_drop_params
            )
            is False
        ):
            extra_body = passed_params.pop("extra_body", {})
            for k in passed_params.keys():
                if k not in openai_params:
                    extra_body[k] = passed_params[k]
            optional_params.setdefault("extra_body", {})
            initial_extra_body = {
                **optional_params["extra_body"],
                **extra_body,
            }

            if additional_drop_params is not None:
                processed_extra_body = {
                    k: v
                    for k, v in initial_extra_body.items()
                    if k not in additional_drop_params
                }
            else:
                processed_extra_body = initial_extra_body

            optional_params["extra_body"] = _ensure_extra_body_is_safe(
                extra_body=processed_extra_body
            )
    else:
        for k in passed_params.keys():
            if k not in openai_params:
                optional_params[k] = passed_params[k]
    return optional_params


def _apply_openai_param_overrides(
    optional_params: dict, non_default_params: dict, allowed_openai_params: list
):
    """
    If user passes in allowed_openai_params, apply them to optional_params

    These params will get passed as is to the LLM API since the user opted in to passing them in the request
    """
    if allowed_openai_params:
        for param in allowed_openai_params:
            if param not in optional_params:
                optional_params[param] = non_default_params.pop(param, None)
    return optional_params


def get_non_default_params(passed_params: dict) -> dict:
    # filter out those parameters that were passed with non-default values
    non_default_params = {
        k: v
        for k, v in passed_params.items()
        if (
            k != "model"
            and k != "custom_llm_provider"
            and k in DEFAULT_CHAT_COMPLETION_PARAM_VALUES
            and v != DEFAULT_CHAT_COMPLETION_PARAM_VALUES[k]
        )
    }

    return non_default_params


def calculate_max_parallel_requests(
    max_parallel_requests: Optional[int],
    rpm: Optional[int],
    tpm: Optional[int],
    default_max_parallel_requests: Optional[int],
) -> Optional[int]:
    """
    Returns the max parallel requests to send to a deployment.

    Used in semaphore for async requests on router.

    Parameters:
    - max_parallel_requests - Optional[int] - max_parallel_requests allowed for that deployment
    - rpm - Optional[int] - requests per minute allowed for that deployment
    - tpm - Optional[int] - tokens per minute allowed for that deployment
    - default_max_parallel_requests - Optional[int] - default_max_parallel_requests allowed for any deployment

    Returns:
    - int or None (if all params are None)

    Order:
    max_parallel_requests > rpm > tpm / 6 (azure formula) > default max_parallel_requests

    Azure RPM formula:
    6 rpm per 1000 TPM
    https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-limits


    """
    if max_parallel_requests is not None:
        return max_parallel_requests
    elif rpm is not None:
        return rpm
    elif tpm is not None:
        calculated_rpm = int(tpm / 1000 / 6)
        if calculated_rpm == 0:
            calculated_rpm = 1
        return calculated_rpm
    elif default_max_parallel_requests is not None:
        return default_max_parallel_requests
    return None


def _get_order_filtered_deployments(healthy_deployments: List[Dict]) -> List:
    min_order = min(
        (
            deployment["litellm_params"]["order"]
            for deployment in healthy_deployments
            if "order" in deployment["litellm_params"]
        ),
        default=None,
    )

    if min_order is not None:
        filtered_deployments = [
            deployment
            for deployment in healthy_deployments
            if deployment["litellm_params"].get("order") == min_order
        ]

        return filtered_deployments
    return healthy_deployments


def _get_model_region(
    custom_llm_provider: str, litellm_params: LiteLLM_Params
) -> Optional[str]:
    """
    Return the region for a model, for a given provider
    """
    if custom_llm_provider == "vertex_ai":
        # check 'vertex_location'
        vertex_ai_location = (
            litellm_params.vertex_location
            or litellm.vertex_location
            or get_secret("VERTEXAI_LOCATION")
            or get_secret("VERTEX_LOCATION")
        )
        if vertex_ai_location is not None and isinstance(vertex_ai_location, str):
            return vertex_ai_location
    elif custom_llm_provider == "bedrock":
        aws_region_name = litellm_params.aws_region_name
        if aws_region_name is not None:
            return aws_region_name
    elif custom_llm_provider == "watsonx":
        watsonx_region_name = litellm_params.watsonx_region_name
        if watsonx_region_name is not None:
            return watsonx_region_name
    return litellm_params.region_name


def _infer_model_region(litellm_params: LiteLLM_Params) -> Optional[AllowedModelRegion]:
    """
    Infer if a model is in the EU or US region

    Returns:
    - str (region) - "eu" or "us"
    - None (if region not found)
    """
    model, custom_llm_provider, _, _ = litellm.get_llm_provider(
        model=litellm_params.model, litellm_params=litellm_params
    )

    model_region = _get_model_region(
        custom_llm_provider=custom_llm_provider, litellm_params=litellm_params
    )

    if model_region is None:
        verbose_logger.debug(
            "Cannot infer model region for model: {}".format(litellm_params.model)
        )
        return None

    if custom_llm_provider == "azure":
        eu_regions = litellm.AzureOpenAIConfig().get_eu_regions()
        us_regions = litellm.AzureOpenAIConfig().get_us_regions()
    elif custom_llm_provider == "vertex_ai":
        eu_regions = litellm.VertexAIConfig().get_eu_regions()
        us_regions = litellm.VertexAIConfig().get_us_regions()
    elif custom_llm_provider == "bedrock":
        eu_regions = litellm.AmazonBedrockGlobalConfig().get_eu_regions()
        us_regions = litellm.AmazonBedrockGlobalConfig().get_us_regions()
    elif custom_llm_provider == "watsonx":
        eu_regions = litellm.IBMWatsonXAIConfig().get_eu_regions()
        us_regions = litellm.IBMWatsonXAIConfig().get_us_regions()
    else:
        eu_regions = []
        us_regions = []

    for region in eu_regions:
        if region in model_region.lower():
            return "eu"
    for region in us_regions:
        if region in model_region.lower():
            return "us"
    return None


def _is_region_eu(litellm_params: LiteLLM_Params) -> bool:
    """
    Return true/false if a deployment is in the EU
    """
    if litellm_params.region_name == "eu":
        return True

    ## Else - try and infer from model region
    model_region = _infer_model_region(litellm_params=litellm_params)
    if model_region is not None and model_region == "eu":
        return True
    return False


def _is_region_us(litellm_params: LiteLLM_Params) -> bool:
    """
    Return true/false if a deployment is in the US
    """
    if litellm_params.region_name == "us":
        return True

    ## Else - try and infer from model region
    model_region = _infer_model_region(litellm_params=litellm_params)
    if model_region is not None and model_region == "us":
        return True
    return False


def is_region_allowed(
    litellm_params: LiteLLM_Params, allowed_model_region: str
) -> bool:
    """
    Return true/false if a deployment is in the EU
    """
    if litellm_params.region_name == allowed_model_region:
        return True
    return False


def get_model_region(
    litellm_params: LiteLLM_Params, mode: Optional[str]
) -> Optional[str]:
    """
    Pass the litellm params for an azure model, and get back the region
    """
    if (
        "azure" in litellm_params.model
        and isinstance(litellm_params.api_key, str)
        and isinstance(litellm_params.api_base, str)
    ):
        _model = litellm_params.model.replace("azure/", "")
        response: dict = litellm.AzureChatCompletion().get_headers(
            model=_model,
            api_key=litellm_params.api_key,
            api_base=litellm_params.api_base,
            api_version=litellm_params.api_version or litellm.AZURE_DEFAULT_API_VERSION,
            timeout=10,
            mode=mode or "chat",
        )

        region: Optional[str] = response.get("x-ms-region", None)
        return region
    return None


def get_first_chars_messages(kwargs: dict) -> str:
    try:
        _messages = kwargs.get("messages")
        _messages = str(_messages)[:100]
        return _messages
    except Exception:
        return ""


def _count_characters(text: str) -> int:
    # Remove white spaces and count characters
    filtered_text = "".join(char for char in text if not char.isspace())
    return len(filtered_text)


def get_response_string(response_obj: Union[ModelResponse, ModelResponseStream]) -> str:
    _choices: Union[
        List[Union[Choices, StreamingChoices]], List[StreamingChoices]
    ] = response_obj.choices

    response_str = ""
    for choice in _choices:
        if isinstance(choice, Choices):
            if choice.message.content is not None:
                response_str += choice.message.content
        elif isinstance(choice, StreamingChoices):
            if choice.delta.content is not None:
                response_str += choice.delta.content

    return response_str


def get_api_key(llm_provider: str, dynamic_api_key: Optional[str]):
    api_key = dynamic_api_key or litellm.api_key
    # openai
    if llm_provider == "openai" or llm_provider == "text-completion-openai":
        api_key = api_key or litellm.openai_key or get_secret("OPENAI_API_KEY")
    # anthropic
    elif llm_provider == "anthropic" or llm_provider == "anthropic_text":
        api_key = api_key or litellm.anthropic_key or get_secret("ANTHROPIC_API_KEY")
    # ai21
    elif llm_provider == "ai21":
        api_key = api_key or litellm.ai21_key or get_secret("AI211_API_KEY")
    # aleph_alpha
    elif llm_provider == "aleph_alpha":
        api_key = (
            api_key or litellm.aleph_alpha_key or get_secret("ALEPH_ALPHA_API_KEY")
        )
    # baseten
    elif llm_provider == "baseten":
        api_key = api_key or litellm.baseten_key or get_secret("BASETEN_API_KEY")
    # cohere
    elif llm_provider == "cohere" or llm_provider == "cohere_chat":
        api_key = api_key or litellm.cohere_key or get_secret("COHERE_API_KEY")
    # huggingface
    elif llm_provider == "huggingface":
        api_key = (
            api_key or litellm.huggingface_key or get_secret("HUGGINGFACE_API_KEY")
        )
    # nlp_cloud
    elif llm_provider == "nlp_cloud":
        api_key = api_key or litellm.nlp_cloud_key or get_secret("NLP_CLOUD_API_KEY")
    # replicate
    elif llm_provider == "replicate":
        api_key = api_key or litellm.replicate_key or get_secret("REPLICATE_API_KEY")
    # together_ai
    elif llm_provider == "together_ai":
        api_key = (
            api_key
            or litellm.togetherai_api_key
            or get_secret("TOGETHERAI_API_KEY")
            or get_secret("TOGETHER_AI_TOKEN")
        )
    # nebius
    elif llm_provider == "nebius":
        api_key = api_key or litellm.nebius_key or get_secret("NEBIUS_API_KEY")
    return api_key


def get_utc_datetime():
    import datetime as dt
    from datetime import datetime

    if hasattr(dt, "UTC"):
        return datetime.now(dt.UTC)  # type: ignore
    else:
        return datetime.utcnow()  # type: ignore


def get_max_tokens(model: str) -> Optional[int]:
    """
    Get the maximum number of output tokens allowed for a given model.

    Parameters:
    model (str): The name of the model.

    Returns:
        int: The maximum number of tokens allowed for the given model.

    Raises:
        Exception: If the model is not mapped yet.

    Example:
        >>> get_max_tokens("gpt-4")
        8192
    """

    def _get_max_position_embeddings(model_name):
        # Construct the URL for the config.json file
        config_url = f"https://huggingface.co/{model_name}/raw/main/config.json"
        try:
            # Make the HTTP request to get the raw JSON file
            response = litellm.module_level_client.get(config_url)
            response.raise_for_status()  # Raise an exception for bad responses (4xx or 5xx)

            # Parse the JSON response
            config_json = response.json()
            # Extract and return the max_position_embeddings
            max_position_embeddings = config_json.get("max_position_embeddings")
            if max_position_embeddings is not None:
                return max_position_embeddings
            else:
                return None
        except Exception:
            return None

    try:
        if model in litellm.model_cost:
            if "max_output_tokens" in litellm.model_cost[model]:
                return litellm.model_cost[model]["max_output_tokens"]
            elif "max_tokens" in litellm.model_cost[model]:
                return litellm.model_cost[model]["max_tokens"]
        model, custom_llm_provider, _, _ = get_llm_provider(model=model)
        if custom_llm_provider == "huggingface":
            max_tokens = _get_max_position_embeddings(model_name=model)
            return max_tokens
        if model in litellm.model_cost:  # check if extracted model is in model_list
            if "max_output_tokens" in litellm.model_cost[model]:
                return litellm.model_cost[model]["max_output_tokens"]
            elif "max_tokens" in litellm.model_cost[model]:
                return litellm.model_cost[model]["max_tokens"]
        else:
            raise Exception()
        return None
    except Exception:
        raise Exception(
            f"Model {model} isn't mapped yet. Add it here - https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json"
        )


def _strip_stable_vertex_version(model_name) -> str:
    return re.sub(r"-\d+$", "", model_name)


def _get_base_bedrock_model(model_name) -> str:
    """
    Get the base model from the given model name.

    Handle model names like - "us.meta.llama3-2-11b-instruct-v1:0" -> "meta.llama3-2-11b-instruct-v1"
    AND "meta.llama3-2-11b-instruct-v1:0" -> "meta.llama3-2-11b-instruct-v1"
    """
    from litellm.llms.bedrock.common_utils import BedrockModelInfo

    return BedrockModelInfo.get_base_model(model_name)


def _strip_openai_finetune_model_name(model_name: str) -> str:
    """
    Strips the organization, custom suffix, and ID from an OpenAI fine-tuned model name.

    input: ft:gpt-3.5-turbo:my-org:custom_suffix:id
    output: ft:gpt-3.5-turbo

    Args:
    model_name (str): The full model name

    Returns:
    str: The stripped model name
    """
    return re.sub(r"(:[^:]+){3}$", "", model_name)


def _strip_model_name(model: str, custom_llm_provider: Optional[str]) -> str:
    if custom_llm_provider and custom_llm_provider == "bedrock":
        stripped_bedrock_model = _get_base_bedrock_model(model_name=model)
        return stripped_bedrock_model
    elif custom_llm_provider and (
        custom_llm_provider == "vertex_ai" or custom_llm_provider == "gemini"
    ):
        strip_version = _strip_stable_vertex_version(model_name=model)
        return strip_version
    elif custom_llm_provider and (custom_llm_provider == "databricks"):
        strip_version = _strip_stable_vertex_version(model_name=model)
        return strip_version
    elif "ft:" in model:
        strip_finetune = _strip_openai_finetune_model_name(model_name=model)
        return strip_finetune
    else:
        return model


def _get_model_info_from_model_cost(key: str) -> dict:
    return litellm.model_cost[key]


def _check_provider_match(model_info: dict, custom_llm_provider: Optional[str]) -> bool:
    """
    Check if the model info provider matches the custom provider.
    """
    if custom_llm_provider and (
        "litellm_provider" in model_info
        and model_info["litellm_provider"] != custom_llm_provider
    ):
        if custom_llm_provider == "vertex_ai" and model_info[
            "litellm_provider"
        ].startswith("vertex_ai"):
            return True
        elif custom_llm_provider == "fireworks_ai" and model_info[
            "litellm_provider"
        ].startswith("fireworks_ai"):
            return True
        elif custom_llm_provider.startswith("bedrock") and model_info[
            "litellm_provider"
        ].startswith("bedrock"):
            return True
        elif (
            custom_llm_provider == "litellm_proxy"
        ):  # litellm_proxy is a special case, it's not a provider, it's a proxy for the provider
            return True
        else:
            return False

    return True


from typing import TypedDict


class PotentialModelNamesAndCustomLLMProvider(TypedDict):
    split_model: str
    combined_model_name: str
    stripped_model_name: str
    combined_stripped_model_name: str
    custom_llm_provider: str


def _get_potential_model_names(
    model: str, custom_llm_provider: Optional[str]
) -> PotentialModelNamesAndCustomLLMProvider:
    if custom_llm_provider is None:
        # Get custom_llm_provider
        try:
            split_model, custom_llm_provider, _, _ = get_llm_provider(model=model)
        except Exception:
            split_model = model
        combined_model_name = model
        stripped_model_name = _strip_model_name(
            model=model, custom_llm_provider=custom_llm_provider
        )
        combined_stripped_model_name = stripped_model_name
    elif custom_llm_provider and model.startswith(
        custom_llm_provider + "/"
    ):  # handle case where custom_llm_provider is provided and model starts with custom_llm_provider
        split_model = model.split("/", 1)[1]
        combined_model_name = model
        stripped_model_name = _strip_model_name(
            model=split_model, custom_llm_provider=custom_llm_provider
        )
        combined_stripped_model_name = "{}/{}".format(
            custom_llm_provider, stripped_model_name
        )
    else:
        split_model = model
        combined_model_name = "{}/{}".format(custom_llm_provider, model)
        stripped_model_name = _strip_model_name(
            model=model, custom_llm_provider=custom_llm_provider
        )
        combined_stripped_model_name = "{}/{}".format(
            custom_llm_provider,
            stripped_model_name,
        )

    return PotentialModelNamesAndCustomLLMProvider(
        split_model=split_model,
        combined_model_name=combined_model_name,
        stripped_model_name=stripped_model_name,
        combined_stripped_model_name=combined_stripped_model_name,
        custom_llm_provider=cast(str, custom_llm_provider),
    )


def _get_max_position_embeddings(model_name: str) -> Optional[int]:
    # Construct the URL for the config.json file
    config_url = f"https://huggingface.co/{model_name}/raw/main/config.json"

    try:
        # Make the HTTP request to get the raw JSON file
        response = litellm.module_level_client.get(config_url)
        response.raise_for_status()  # Raise an exception for bad responses (4xx or 5xx)

        # Parse the JSON response
        config_json = response.json()

        # Extract and return the max_position_embeddings
        max_position_embeddings = config_json.get("max_position_embeddings")

        if max_position_embeddings is not None:
            return max_position_embeddings
        else:
            return None
    except Exception:
        return None


def _cached_get_model_info_helper(
    model: str, custom_llm_provider: Optional[str]
) -> ModelInfoBase:
    """
    _get_model_info_helper wrapped with lru_cache

    Speed Optimization to hit high RPS
    """
    return _get_model_info_helper(model=model, custom_llm_provider=custom_llm_provider)


def get_provider_info(
    model: str, custom_llm_provider: Optional[str]
) -> Optional[ProviderSpecificModelInfo]:
    ## PROVIDER-SPECIFIC INFORMATION
    # if custom_llm_provider == "predibase":
    #     _model_info["supports_response_schema"] = True
    provider_config: Optional[BaseLLMModelInfo] = None
    if custom_llm_provider and custom_llm_provider in LlmProvidersSet:
        # Check if the provider string exists in LlmProviders enum
        provider_config = ProviderConfigManager.get_provider_model_info(
            model=model, provider=LlmProviders(custom_llm_provider)
        )

    model_info: Optional[ProviderSpecificModelInfo] = None
    if provider_config:
        model_info = provider_config.get_provider_info(model=model)

    return model_info


def _is_potential_model_name_in_model_cost(
    potential_model_names: PotentialModelNamesAndCustomLLMProvider,
) -> bool:
    """
    Check if the potential model name is in the model cost.
    """
    return any(
        potential_model_name in litellm.model_cost
        for potential_model_name in potential_model_names.values()
    )


def _get_model_info_helper(  # noqa: PLR0915
    model: str, custom_llm_provider: Optional[str] = None
) -> ModelInfoBase:
    """
    Helper for 'get_model_info'. Separated out to avoid infinite loop caused by returning 'supported_openai_param's
    """
    try:
        azure_llms = {**litellm.azure_llms, **litellm.azure_embedding_models}
        if model in azure_llms:
            model = azure_llms[model]
        if custom_llm_provider is not None and custom_llm_provider == "vertex_ai_beta":
            custom_llm_provider = "vertex_ai"
        if custom_llm_provider is not None and custom_llm_provider == "vertex_ai":
            if "meta/" + model in litellm.vertex_llama3_models:
                model = "meta/" + model
            elif model + "@latest" in litellm.vertex_mistral_models:
                model = model + "@latest"
            elif model + "@latest" in litellm.vertex_ai_ai21_models:
                model = model + "@latest"
        ##########################
        potential_model_names = _get_potential_model_names(
            model=model, custom_llm_provider=custom_llm_provider
        )

        verbose_logger.debug(
            f"checking potential_model_names in litellm.model_cost: {potential_model_names}"
        )

        combined_model_name = potential_model_names["combined_model_name"]
        stripped_model_name = potential_model_names["stripped_model_name"]
        combined_stripped_model_name = potential_model_names[
            "combined_stripped_model_name"
        ]
        split_model = potential_model_names["split_model"]
        custom_llm_provider = potential_model_names["custom_llm_provider"]
        #########################
        if custom_llm_provider == "huggingface":
            max_tokens = _get_max_position_embeddings(model_name=model)
            return ModelInfoBase(
                key=model,
                max_tokens=max_tokens,  # type: ignore
                max_input_tokens=None,
                max_output_tokens=None,
                input_cost_per_token=0,
                output_cost_per_token=0,
                litellm_provider="huggingface",
                mode="chat",
                supports_system_messages=None,
                supports_response_schema=None,
                supports_function_calling=None,
                supports_tool_choice=None,
                supports_assistant_prefill=None,
                supports_prompt_caching=None,
                supports_computer_use=None,
                supports_pdf_input=None,
            )
        elif (
            custom_llm_provider == "ollama" or custom_llm_provider == "ollama_chat"
        ) and not _is_potential_model_name_in_model_cost(potential_model_names):
            return litellm.OllamaConfig().get_model_info(model)
        else:
            """
            Check if: (in order of specificity)
            1. 'custom_llm_provider/model' in litellm.model_cost. Checks "groq/llama3-8b-8192" if model="llama3-8b-8192" and custom_llm_provider="groq"
            2. 'model' in litellm.model_cost. Checks "gemini-1.5-pro-002" in  litellm.model_cost if model="gemini-1.5-pro-002" and custom_llm_provider=None
            3. 'combined_stripped_model_name' in litellm.model_cost. Checks if 'gemini/gemini-1.5-flash' in model map, if 'gemini/gemini-1.5-flash-001' given.
            4. 'stripped_model_name' in litellm.model_cost. Checks if 'ft:gpt-3.5-turbo' in model map, if 'ft:gpt-3.5-turbo:my-org:custom_suffix:id' given.
            5. 'split_model' in litellm.model_cost. Checks "llama3-8b-8192" in litellm.model_cost if model="groq/llama3-8b-8192"
            """

            _model_info: Optional[Dict[str, Any]] = None
            key: Optional[str] = None

            if combined_model_name in litellm.model_cost:
                key = combined_model_name
                _model_info = _get_model_info_from_model_cost(key=cast(str, key))
                if not _check_provider_match(
                    model_info=_model_info, custom_llm_provider=custom_llm_provider
                ):
                    _model_info = None
            if _model_info is None and model in litellm.model_cost:
                key = model
                _model_info = _get_model_info_from_model_cost(key=cast(str, key))
                if not _check_provider_match(
                    model_info=_model_info, custom_llm_provider=custom_llm_provider
                ):
                    _model_info = None
            if (
                _model_info is None
                and combined_stripped_model_name in litellm.model_cost
            ):
                key = combined_stripped_model_name
                _model_info = _get_model_info_from_model_cost(key=cast(str, key))
                if not _check_provider_match(
                    model_info=_model_info, custom_llm_provider=custom_llm_provider
                ):
                    _model_info = None
            if _model_info is None and stripped_model_name in litellm.model_cost:
                key = stripped_model_name
                _model_info = _get_model_info_from_model_cost(key=cast(str, key))
                if not _check_provider_match(
                    model_info=_model_info, custom_llm_provider=custom_llm_provider
                ):
                    _model_info = None
            if _model_info is None and split_model in litellm.model_cost:
                key = split_model
                _model_info = _get_model_info_from_model_cost(key=cast(str, key))
                if not _check_provider_match(
                    model_info=_model_info, custom_llm_provider=custom_llm_provider
                ):
                    _model_info = None

            if _model_info is None or key is None:
                raise ValueError(
                    "This model isn't mapped yet. Add it here - https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json"
                )

            _input_cost_per_token: Optional[float] = _model_info.get(
                "input_cost_per_token"
            )
            if _input_cost_per_token is None:
                # default value to 0, be noisy about this
                verbose_logger.debug(
                    "model={}, custom_llm_provider={} has no input_cost_per_token in model_cost_map. Defaulting to 0.".format(
                        model, custom_llm_provider
                    )
                )
                _input_cost_per_token = 0

            _output_cost_per_token: Optional[float] = _model_info.get(
                "output_cost_per_token"
            )
            if _output_cost_per_token is None:
                # default value to 0, be noisy about this
                verbose_logger.debug(
                    "model={}, custom_llm_provider={} has no output_cost_per_token in model_cost_map. Defaulting to 0.".format(
                        model, custom_llm_provider
                    )
                )
                _output_cost_per_token = 0

            return ModelInfoBase(
                key=key,
                max_tokens=_model_info.get("max_tokens", None),
                max_input_tokens=_model_info.get("max_input_tokens", None),
                max_output_tokens=_model_info.get("max_output_tokens", None),
                input_cost_per_token=_input_cost_per_token,
                cache_creation_input_token_cost=_model_info.get(
                    "cache_creation_input_token_cost", None
                ),
                cache_read_input_token_cost=_model_info.get(
                    "cache_read_input_token_cost", None
                ),
                input_cost_per_character=_model_info.get(
                    "input_cost_per_character", None
                ),
                input_cost_per_token_above_128k_tokens=_model_info.get(
                    "input_cost_per_token_above_128k_tokens", None
                ),
                input_cost_per_token_above_200k_tokens=_model_info.get(
                    "input_cost_per_token_above_200k_tokens", None
                ),
                input_cost_per_query=_model_info.get("input_cost_per_query", None),
                input_cost_per_second=_model_info.get("input_cost_per_second", None),
                input_cost_per_audio_token=_model_info.get(
                    "input_cost_per_audio_token", None
                ),
                input_cost_per_token_batches=_model_info.get(
                    "input_cost_per_token_batches"
                ),
                output_cost_per_token_batches=_model_info.get(
                    "output_cost_per_token_batches"
                ),
                output_cost_per_token=_output_cost_per_token,
                output_cost_per_audio_token=_model_info.get(
                    "output_cost_per_audio_token", None
                ),
                output_cost_per_character=_model_info.get(
                    "output_cost_per_character", None
                ),
                output_cost_per_reasoning_token=_model_info.get(
                    "output_cost_per_reasoning_token", None
                ),
                output_cost_per_token_above_128k_tokens=_model_info.get(
                    "output_cost_per_token_above_128k_tokens", None
                ),
                output_cost_per_character_above_128k_tokens=_model_info.get(
                    "output_cost_per_character_above_128k_tokens", None
                ),
                output_cost_per_token_above_200k_tokens=_model_info.get(
                    "output_cost_per_token_above_200k_tokens", None
                ),
                output_cost_per_second=_model_info.get("output_cost_per_second", None),
                output_cost_per_image=_model_info.get("output_cost_per_image", None),
                output_vector_size=_model_info.get("output_vector_size", None),
                litellm_provider=_model_info.get(
                    "litellm_provider", custom_llm_provider
                ),
                mode=_model_info.get("mode"),  # type: ignore
                supports_system_messages=_model_info.get(
                    "supports_system_messages", None
                ),
                supports_response_schema=_model_info.get(
                    "supports_response_schema", None
                ),
                supports_vision=_model_info.get("supports_vision", None),
                supports_function_calling=_model_info.get(
                    "supports_function_calling", None
                ),
                supports_tool_choice=_model_info.get("supports_tool_choice", None),
                supports_assistant_prefill=_model_info.get(
                    "supports_assistant_prefill", None
                ),
                supports_prompt_caching=_model_info.get(
                    "supports_prompt_caching", None
                ),
                supports_audio_input=_model_info.get("supports_audio_input", None),
                supports_audio_output=_model_info.get("supports_audio_output", None),
                supports_pdf_input=_model_info.get("supports_pdf_input", None),
                supports_embedding_image_input=_model_info.get(
                    "supports_embedding_image_input", None
                ),
                supports_native_streaming=_model_info.get(
                    "supports_native_streaming", None
                ),
                supports_web_search=_model_info.get("supports_web_search", None),
                supports_url_context=_model_info.get("supports_url_context", None),
                supports_reasoning=_model_info.get("supports_reasoning", None),
                supports_computer_use=_model_info.get("supports_computer_use", None),
                search_context_cost_per_query=_model_info.get(
                    "search_context_cost_per_query", None
                ),
                tpm=_model_info.get("tpm", None),
                rpm=_model_info.get("rpm", None),
            )
    except Exception as e:
        verbose_logger.debug(f"Error getting model info: {e}")
        if "OllamaError" in str(e):
            raise e
        raise Exception(
            "This model isn't mapped yet. model={}, custom_llm_provider={}. Add it here - https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json.".format(
                model, custom_llm_provider
            )
        )


def get_model_info(model: str, custom_llm_provider: Optional[str] = None) -> ModelInfo:
    """
    Get a dict for the maximum tokens (context window), input_cost_per_token, output_cost_per_token  for a given model.

    Parameters:
    - model (str): The name of the model.
    - custom_llm_provider (str | null): the provider used for the model. If provided, used to check if the litellm model info is for that provider.

    Returns:
        dict: A dictionary containing the following information:
            key: Required[str] # the key in litellm.model_cost which is returned
            max_tokens: Required[Optional[int]]
            max_input_tokens: Required[Optional[int]]
            max_output_tokens: Required[Optional[int]]
            input_cost_per_token: Required[float]
            input_cost_per_character: Optional[float]  # only for vertex ai models
            input_cost_per_token_above_128k_tokens: Optional[float]  # only for vertex ai models
            input_cost_per_character_above_128k_tokens: Optional[
                float
            ]  # only for vertex ai models
            input_cost_per_query: Optional[float] # only for rerank models
            input_cost_per_image: Optional[float]  # only for vertex ai models
            input_cost_per_audio_token: Optional[float]
            input_cost_per_audio_per_second: Optional[float]  # only for vertex ai models
            input_cost_per_video_per_second: Optional[float]  # only for vertex ai models
            output_cost_per_token: Required[float]
            output_cost_per_audio_token: Optional[float]
            output_cost_per_character: Optional[float]  # only for vertex ai models
            output_cost_per_token_above_128k_tokens: Optional[
                float
            ]  # only for vertex ai models
            output_cost_per_character_above_128k_tokens: Optional[
                float
            ]  # only for vertex ai models
            output_cost_per_image: Optional[float]
            output_vector_size: Optional[int]
            output_cost_per_video_per_second: Optional[float]  # only for vertex ai models
            output_cost_per_audio_per_second: Optional[float]  # only for vertex ai models
            litellm_provider: Required[str]
            mode: Required[
                Literal[
                    "completion", "embedding", "image_generation", "chat", "audio_transcription"
                ]
            ]
            supported_openai_params: Required[Optional[List[str]]]
            supports_system_messages: Optional[bool]
            supports_response_schema: Optional[bool]
            supports_vision: Optional[bool]
            supports_function_calling: Optional[bool]
            supports_tool_choice: Optional[bool]
            supports_prompt_caching: Optional[bool]
            supports_audio_input: Optional[bool]
            supports_audio_output: Optional[bool]
            supports_pdf_input: Optional[bool]
            supports_web_search: Optional[bool]
            supports_url_context: Optional[bool]
            supports_reasoning: Optional[bool]
    Raises:
        Exception: If the model is not mapped yet.

    Example:
        >>> get_model_info("gpt-4")
        {
            "max_tokens": 8192,
            "input_cost_per_token": 0.00003,
            "output_cost_per_token": 0.00006,
            "litellm_provider": "openai",
            "mode": "chat",
            "supported_openai_params": ["temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty"]
        }
    """
    supported_openai_params = litellm.get_supported_openai_params(
        model=model, custom_llm_provider=custom_llm_provider
    )

    _model_info = _get_model_info_helper(
        model=model,
        custom_llm_provider=custom_llm_provider,
    )

    verbose_logger.debug(f"model_info: {_model_info}")

    returned_model_info = ModelInfo(
        **_model_info, supported_openai_params=supported_openai_params
    )

    return returned_model_info


def json_schema_type(python_type_name: str):
    """Converts standard python types to json schema types

    Parameters
    ----------
    python_type_name : str
        __name__ of type

    Returns
    -------
    str
        a standard JSON schema type, "string" if not recognized.
    """
    python_to_json_schema_types = {
        str.__name__: "string",
        int.__name__: "integer",
        float.__name__: "number",
        bool.__name__: "boolean",
        list.__name__: "array",
        dict.__name__: "object",
        "NoneType": "null",
    }

    return python_to_json_schema_types.get(python_type_name, "string")


def function_to_dict(input_function):  # noqa: C901
    """Using type hints and numpy-styled docstring,
    produce a dictionnary usable for OpenAI function calling

    Parameters
    ----------
    input_function : function
        A function with a numpy-style docstring

    Returns
    -------
    dictionnary
        A dictionnary to add to the list passed to `functions` parameter of `litellm.completion`
    """
    # Get function name and docstring
    try:
        import inspect
        from ast import literal_eval

        from numpydoc.docscrape import NumpyDocString
    except Exception as e:
        raise e

    name = input_function.__name__
    docstring = inspect.getdoc(input_function)
    numpydoc = NumpyDocString(docstring)
    description = "\n".join([s.strip() for s in numpydoc["Summary"]])

    # Get function parameters and their types from annotations and docstring
    parameters = {}
    required_params = []
    param_info = inspect.signature(input_function).parameters

    for param_name, param in param_info.items():
        if hasattr(param, "annotation"):
            param_type = json_schema_type(param.annotation.__name__)
        else:
            param_type = None
        param_description = None
        param_enum = None

        # Try to extract param description from docstring using numpydoc
        for param_data in numpydoc["Parameters"]:
            if param_data.name == param_name:
                if hasattr(param_data, "type"):
                    # replace type from docstring rather than annotation
                    param_type = param_data.type
                    if "optional" in param_type:
                        param_type = param_type.split(",")[0]
                    elif "{" in param_type:
                        # may represent a set of acceptable values
                        # translating as enum for function calling
                        try:
                            param_enum = str(list(literal_eval(param_type)))
                            param_type = "string"
                        except Exception:
                            pass
                    param_type = json_schema_type(param_type)
                param_description = "\n".join([s.strip() for s in param_data.desc])

        param_dict = {
            "type": param_type,
            "description": param_description,
            "enum": param_enum,
        }

        parameters[param_name] = dict(
            [(k, v) for k, v in param_dict.items() if isinstance(v, str)]
        )

        # Check if the parameter has no default value (i.e., it's required)
        if param.default == param.empty:
            required_params.append(param_name)

    # Create the dictionary
    result = {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": parameters,
        },
    }

    # Add "required" key if there are required parameters
    if required_params:
        result["parameters"]["required"] = required_params

    return result


def modify_url(original_url, new_path):
    url = httpx.URL(original_url)
    modified_url = url.copy_with(path=new_path)
    return str(modified_url)


def load_test_model(
    model: str,
    custom_llm_provider: str = "",
    api_base: str = "",
    prompt: str = "",
    num_calls: int = 0,
    force_timeout: int = 0,
):
    test_prompt = "Hey, how's it going"
    test_calls = 100
    if prompt:
        test_prompt = prompt
    if num_calls:
        test_calls = num_calls
    messages = [[{"role": "user", "content": test_prompt}] for _ in range(test_calls)]
    start_time = time.time()
    try:
        litellm.batch_completion(
            model=model,
            messages=messages,
            custom_llm_provider=custom_llm_provider,
            api_base=api_base,
            force_timeout=force_timeout,
        )
        end_time = time.time()
        response_time = end_time - start_time
        return {
            "total_response_time": response_time,
            "calls_made": 100,
            "status": "success",
            "exception": None,
        }
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        return {
            "total_response_time": response_time,
            "calls_made": 100,
            "status": "failed",
            "exception": e,
        }


def get_provider_fields(custom_llm_provider: str) -> List[ProviderField]:
    """Return the fields required for each provider"""

    if custom_llm_provider == "databricks":
        return litellm.DatabricksConfig().get_required_params()

    elif custom_llm_provider == "ollama":
        return litellm.OllamaConfig().get_required_params()

    elif custom_llm_provider == "azure_ai":
        return litellm.AzureAIStudioConfig().get_required_params()

    else:
        return []


def create_proxy_transport_and_mounts():
    proxies = {
        key: None if url is None else Proxy(url=url)
        for key, url in get_environment_proxies().items()
    }

    sync_proxy_mounts = {}
    async_proxy_mounts = {}

    # Retrieve NO_PROXY environment variable
    no_proxy = os.getenv("NO_PROXY", None)
    no_proxy_urls = no_proxy.split(",") if no_proxy else []

    for key, proxy in proxies.items():
        if proxy is None:
            sync_proxy_mounts[key] = httpx.HTTPTransport()
            async_proxy_mounts[key] = httpx.AsyncHTTPTransport()
        else:
            sync_proxy_mounts[key] = httpx.HTTPTransport(proxy=proxy)
            async_proxy_mounts[key] = httpx.AsyncHTTPTransport(proxy=proxy)

    for url in no_proxy_urls:
        sync_proxy_mounts[url] = httpx.HTTPTransport()
        async_proxy_mounts[url] = httpx.AsyncHTTPTransport()

    return sync_proxy_mounts, async_proxy_mounts


def validate_environment(  # noqa: PLR0915
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> dict:
    """
    Checks if the environment variables are valid for the given model.

    Args:
        model (Optional[str]): The name of the model. Defaults to None.
        api_key (Optional[str]): If the user passed in an api key, of their own.

    Returns:
        dict: A dictionary containing the following keys:
            - keys_in_environment (bool): True if all the required keys are present in the environment, False otherwise.
            - missing_keys (List[str]): A list of missing keys in the environment.
    """
    keys_in_environment = False
    missing_keys: List[str] = []

    if model is None:
        return {
            "keys_in_environment": keys_in_environment,
            "missing_keys": missing_keys,
        }
    ## EXTRACT LLM PROVIDER - if model name provided
    try:
        _, custom_llm_provider, _, _ = get_llm_provider(model=model)
    except Exception:
        custom_llm_provider = None

    if custom_llm_provider:
        if custom_llm_provider == "openai":
            if "OPENAI_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("OPENAI_API_KEY")
        elif custom_llm_provider == "azure":
            if (
                "AZURE_API_BASE" in os.environ
                and "AZURE_API_VERSION" in os.environ
                and "AZURE_API_KEY" in os.environ
            ):
                keys_in_environment = True
            else:
                missing_keys.extend(
                    ["AZURE_API_BASE", "AZURE_API_VERSION", "AZURE_API_KEY"]
                )
        elif custom_llm_provider == "anthropic":
            if "ANTHROPIC_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("ANTHROPIC_API_KEY")
        elif custom_llm_provider == "cohere":
            if "COHERE_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("COHERE_API_KEY")
        elif custom_llm_provider == "replicate":
            if "REPLICATE_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("REPLICATE_API_KEY")
        elif custom_llm_provider == "openrouter":
            if "OPENROUTER_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("OPENROUTER_API_KEY")
        elif custom_llm_provider == "datarobot":
            if "DATAROBOT_API_TOKEN" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("DATAROBOT_API_TOKEN")
        elif custom_llm_provider == "vertex_ai":
            if "VERTEXAI_PROJECT" in os.environ and "VERTEXAI_LOCATION" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.extend(["VERTEXAI_PROJECT", "VERTEXAI_LOCATION"])
        elif custom_llm_provider == "huggingface":
            if "HUGGINGFACE_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("HUGGINGFACE_API_KEY")
        elif custom_llm_provider == "ai21":
            if "AI21_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("AI21_API_KEY")
        elif custom_llm_provider == "together_ai":
            if "TOGETHERAI_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("TOGETHERAI_API_KEY")
        elif custom_llm_provider == "aleph_alpha":
            if "ALEPH_ALPHA_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("ALEPH_ALPHA_API_KEY")
        elif custom_llm_provider == "baseten":
            if "BASETEN_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("BASETEN_API_KEY")
        elif custom_llm_provider == "nlp_cloud":
            if "NLP_CLOUD_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("NLP_CLOUD_API_KEY")
        elif custom_llm_provider == "bedrock" or custom_llm_provider == "sagemaker":
            if (
                "AWS_ACCESS_KEY_ID" in os.environ
                and "AWS_SECRET_ACCESS_KEY" in os.environ
            ):
                keys_in_environment = True
            else:
                missing_keys.append("AWS_ACCESS_KEY_ID")
                missing_keys.append("AWS_SECRET_ACCESS_KEY")
        elif custom_llm_provider in ["ollama", "ollama_chat"]:
            if "OLLAMA_API_BASE" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("OLLAMA_API_BASE")
        elif custom_llm_provider == "anyscale":
            if "ANYSCALE_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("ANYSCALE_API_KEY")
        elif custom_llm_provider == "deepinfra":
            if "DEEPINFRA_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("DEEPINFRA_API_KEY")
        elif custom_llm_provider == "featherless_ai":
            if "FEATHERLESS_AI_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("FEATHERLESS_AI_API_KEY")
        elif custom_llm_provider == "gemini":
            if "GEMINI_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("GEMINI_API_KEY")
        elif custom_llm_provider == "groq":
            if "GROQ_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("GROQ_API_KEY")
        elif custom_llm_provider == "nvidia_nim":
            if "NVIDIA_NIM_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("NVIDIA_NIM_API_KEY")
        elif custom_llm_provider == "cerebras":
            if "CEREBRAS_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("CEREBRAS_API_KEY")
        elif custom_llm_provider == "xai":
            if "XAI_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("XAI_API_KEY")
        elif custom_llm_provider == "ai21_chat":
            if "AI21_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("AI21_API_KEY")
        elif custom_llm_provider == "volcengine":
            if "VOLCENGINE_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("VOLCENGINE_API_KEY")
        elif (
            custom_llm_provider == "codestral"
            or custom_llm_provider == "text-completion-codestral"
        ):
            if "CODESTRAL_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("CODESTRAL_API_KEY")
        elif custom_llm_provider == "deepseek":
            if "DEEPSEEK_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("DEEPSEEK_API_KEY")
        elif custom_llm_provider == "mistral":
            if "MISTRAL_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("MISTRAL_API_KEY")
        elif custom_llm_provider == "palm":
            if "PALM_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("PALM_API_KEY")
        elif custom_llm_provider == "perplexity":
            if "PERPLEXITYAI_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("PERPLEXITYAI_API_KEY")
        elif custom_llm_provider == "voyage":
            if "VOYAGE_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("VOYAGE_API_KEY")
        elif custom_llm_provider == "infinity":
            if "INFINITY_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("INFINITY_API_KEY")
        elif custom_llm_provider == "fireworks_ai":
            if (
                "FIREWORKS_AI_API_KEY" in os.environ
                or "FIREWORKS_API_KEY" in os.environ
                or "FIREWORKSAI_API_KEY" in os.environ
                or "FIREWORKS_AI_TOKEN" in os.environ
            ):
                keys_in_environment = True
            else:
                missing_keys.append("FIREWORKS_AI_API_KEY")
        elif custom_llm_provider == "cloudflare":
            if "CLOUDFLARE_API_KEY" in os.environ and (
                "CLOUDFLARE_ACCOUNT_ID" in os.environ
                or "CLOUDFLARE_API_BASE" in os.environ
            ):
                keys_in_environment = True
            else:
                missing_keys.append("CLOUDFLARE_API_KEY")
                missing_keys.append("CLOUDFLARE_API_BASE")
        elif custom_llm_provider == "novita":
            if "NOVITA_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("NOVITA_API_KEY")
        elif custom_llm_provider == "nebius":
            if "NEBIUS_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("NEBIUS_API_KEY")
    else:
        ## openai - chatcompletion + text completion
        if (
            model in litellm.open_ai_chat_completion_models
            or model in litellm.open_ai_text_completion_models
            or model in litellm.open_ai_embedding_models
            or model in litellm.openai_image_generation_models
        ):
            if "OPENAI_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("OPENAI_API_KEY")
        ## anthropic
        elif model in litellm.anthropic_models:
            if "ANTHROPIC_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("ANTHROPIC_API_KEY")
        ## cohere
        elif model in litellm.cohere_models:
            if "COHERE_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("COHERE_API_KEY")
        ## replicate
        elif model in litellm.replicate_models:
            if "REPLICATE_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("REPLICATE_API_KEY")
        ## openrouter
        elif model in litellm.openrouter_models:
            if "OPENROUTER_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("OPENROUTER_API_KEY")
        ## datarobot
        elif model in litellm.datarobot_models:
            if "DATAROBOT_API_TOKEN" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("DATAROBOT_API_TOKEN")
        ## vertex - text + chat models
        elif (
            model in litellm.vertex_chat_models
            or model in litellm.vertex_text_models
            or model in litellm.models_by_provider["vertex_ai"]
        ):
            if "VERTEXAI_PROJECT" in os.environ and "VERTEXAI_LOCATION" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.extend(["VERTEXAI_PROJECT", "VERTEXAI_LOCATION"])
        ## huggingface
        elif model in litellm.huggingface_models:
            if "HUGGINGFACE_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("HUGGINGFACE_API_KEY")
        ## ai21
        elif model in litellm.ai21_models:
            if "AI21_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("AI21_API_KEY")
        ## together_ai
        elif model in litellm.together_ai_models:
            if "TOGETHERAI_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("TOGETHERAI_API_KEY")
        ## aleph_alpha
        elif model in litellm.aleph_alpha_models:
            if "ALEPH_ALPHA_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("ALEPH_ALPHA_API_KEY")
        ## baseten
        elif model in litellm.baseten_models:
            if "BASETEN_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("BASETEN_API_KEY")
        ## nlp_cloud
        elif model in litellm.nlp_cloud_models:
            if "NLP_CLOUD_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("NLP_CLOUD_API_KEY")
        elif model in litellm.novita_models:
            if "NOVITA_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("NOVITA_API_KEY")
        elif model in litellm.nebius_models:
            if "NEBIUS_API_KEY" in os.environ:
                keys_in_environment = True
            else:
                missing_keys.append("NEBIUS_API_KEY")

    if api_key is not None:
        new_missing_keys = []
        for key in missing_keys:
            if "api_key" not in key.lower():
                new_missing_keys.append(key)
        missing_keys = new_missing_keys

    if api_base is not None:
        new_missing_keys = []
        for key in missing_keys:
            if "api_base" not in key.lower():
                new_missing_keys.append(key)
        missing_keys = new_missing_keys

    if len(missing_keys) == 0:  # no missing keys
        keys_in_environment = True

    return {"keys_in_environment": keys_in_environment, "missing_keys": missing_keys}


def acreate(*args, **kwargs):  ## Thin client to handle the acreate langchain call
    return litellm.acompletion(*args, **kwargs)


def prompt_token_calculator(model, messages):
    # use tiktoken or anthropic's tokenizer depending on the model
    text = " ".join(message["content"] for message in messages)
    num_tokens = 0
    if "claude" in model:
        try:
            import anthropic
        except Exception:
            Exception("Anthropic import failed please run `pip install anthropic`")
        from anthropic import AI_PROMPT, HUMAN_PROMPT, Anthropic

        anthropic_obj = Anthropic()
        num_tokens = anthropic_obj.count_tokens(text)  # type: ignore
    else:
        num_tokens = len(encoding.encode(text))
    return num_tokens


def valid_model(model):
    try:
        # for a given model name, check if the user has the right permissions to access the model
        if (
            model in litellm.open_ai_chat_completion_models
            or model in litellm.open_ai_text_completion_models
        ):
            openai.models.retrieve(model)
        else:
            messages = [{"role": "user", "content": "Hello World"}]
            litellm.completion(model=model, messages=messages)
    except Exception:
        raise BadRequestError(message="", model=model, llm_provider="")


def check_valid_key(model: str, api_key: str):
    """
    Checks if a given API key is valid for a specific model by making a litellm.completion call with max_tokens=10

    Args:
        model (str): The name of the model to check the API key against.
        api_key (str): The API key to be checked.

    Returns:
        bool: True if the API key is valid for the model, False otherwise.
    """
    messages = [{"role": "user", "content": "Hey, how's it going?"}]
    try:
        litellm.completion(
            model=model, messages=messages, api_key=api_key, max_tokens=10
        )
        return True
    except AuthenticationError:
        return False
    except Exception:
        return False


def _should_retry(status_code: int):
    """
    Retries on 408, 409, 429 and 500 errors.

    Any client error in the 400-499 range that isn't explicitly handled (such as 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, etc.) would not trigger a retry.

    Reimplementation of openai's should retry logic, since that one can't be imported.
    https://github.com/openai/openai-python/blob/af67cfab4210d8e497c05390ce14f39105c77519/src/openai/_base_client.py#L639
    """
    # If the server explicitly says whether or not to retry, obey.
    # Retry on request timeouts.
    if status_code == 408:
        return True

    # Retry on lock timeouts.
    if status_code == 409:
        return True

    # Retry on rate limits.
    if status_code == 429:
        return True

    # Retry internal errors.
    if status_code >= 500:
        return True

    return False


def _get_retry_after_from_exception_header(
    response_headers: Optional[httpx.Headers] = None,
):
    """
    Reimplementation of openai's calculate retry after, since that one can't be imported.
    https://github.com/openai/openai-python/blob/af67cfab4210d8e497c05390ce14f39105c77519/src/openai/_base_client.py#L631
    """
    try:
        import email  # openai import

        # About the Retry-After header: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Retry-After
        #
        # <http-date>". See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Retry-After#syntax for
        # details.
        if response_headers is not None:
            retry_header = response_headers.get("retry-after")
            try:
                retry_after = int(retry_header)
            except Exception:
                retry_date_tuple = email.utils.parsedate_tz(retry_header)  # type: ignore
                if retry_date_tuple is None:
                    retry_after = -1
                else:
                    retry_date = email.utils.mktime_tz(retry_date_tuple)  # type: ignore
                    retry_after = int(retry_date - time.time())
        else:
            retry_after = -1

        return retry_after

    except Exception:
        retry_after = -1


def _calculate_retry_after(
    remaining_retries: int,
    max_retries: int,
    response_headers: Optional[httpx.Headers] = None,
    min_timeout: int = 0,
) -> Union[float, int]:
    retry_after = _get_retry_after_from_exception_header(response_headers)

    # If the API asks us to wait a certain amount of time (and it's a reasonable amount), just do what it says.
    if retry_after is not None and 0 < retry_after <= 60:
        return retry_after

    initial_retry_delay = INITIAL_RETRY_DELAY
    max_retry_delay = MAX_RETRY_DELAY
    nb_retries = max_retries - remaining_retries

    # Apply exponential backoff, but not more than the max.
    sleep_seconds = min(initial_retry_delay * pow(2.0, nb_retries), max_retry_delay)

    # Apply some jitter, plus-or-minus half a second.
    jitter = JITTER * random.random()
    timeout = sleep_seconds * jitter
    return timeout if timeout >= min_timeout else min_timeout


# custom prompt helper function
def register_prompt_template(
    model: str,
    roles: dict = {},
    initial_prompt_value: str = "",
    final_prompt_value: str = "",
    tokenizer_config: dict = {},
):
    """
    Register a prompt template to follow your custom format for a given model

    Args:
        model (str): The name of the model.
        roles (dict): A dictionary mapping roles to their respective prompt values.
        initial_prompt_value (str, optional): The initial prompt value. Defaults to "".
        final_prompt_value (str, optional): The final prompt value. Defaults to "".

    Returns:
        dict: The updated custom prompt dictionary.
    Example usage:
    ```
    import litellm
    litellm.register_prompt_template(
            model="llama-2",
        initial_prompt_value="You are a good assistant" # [OPTIONAL]
            roles={
            "system": {
                "pre_message": "[INST] <<SYS>>\n", # [OPTIONAL]
                "post_message": "\n<</SYS>>\n [/INST]\n" # [OPTIONAL]
            },
            "user": {
                "pre_message": "[INST] ", # [OPTIONAL]
                "post_message": " [/INST]" # [OPTIONAL]
            },
            "assistant": {
                "pre_message": "\n" # [OPTIONAL]
                "post_message": "\n" # [OPTIONAL]
            }
        }
        final_prompt_value="Now answer as best you can:" # [OPTIONAL]
    )
    ```
    """
    complete_model = model
    potential_models = [complete_model]
    try:
        model = get_llm_provider(model=model)[0]
        potential_models.append(model)
    except Exception:
        pass
    if tokenizer_config:
        for m in potential_models:
            litellm.known_tokenizer_config[m] = {
                "tokenizer": tokenizer_config,
                "status": "success",
            }
    else:
        for m in potential_models:
            litellm.custom_prompt_dict[m] = {
                "roles": roles,
                "initial_prompt_value": initial_prompt_value,
                "final_prompt_value": final_prompt_value,
            }

    return litellm.custom_prompt_dict


class TextCompletionStreamWrapper:
    def __init__(
        self,
        completion_stream,
        model,
        stream_options: Optional[dict] = None,
        custom_llm_provider: Optional[str] = None,
    ):
        self.completion_stream = completion_stream
        self.model = model
        self.stream_options = stream_options
        self.custom_llm_provider = custom_llm_provider

    def __iter__(self):
        return self

    def __aiter__(self):
        return self

    def convert_to_text_completion_object(self, chunk: ModelResponse):
        try:
            response = TextCompletionResponse()
            response["id"] = chunk.get("id", None)
            response["object"] = "text_completion"
            response["created"] = chunk.get("created", None)
            response["model"] = chunk.get("model", None)
            text_choices = TextChoices()
            if isinstance(
                chunk, Choices
            ):  # chunk should always be of type StreamingChoices
                raise Exception
            text_choices["text"] = chunk["choices"][0]["delta"]["content"]
            text_choices["index"] = chunk["choices"][0]["index"]
            text_choices["finish_reason"] = chunk["choices"][0]["finish_reason"]
            response["choices"] = [text_choices]

            # only pass usage when stream_options["include_usage"] is True
            if (
                self.stream_options
                and self.stream_options.get("include_usage", False) is True
            ):
                response["usage"] = chunk.get("usage", None)

            return response
        except Exception as e:
            raise Exception(
                f"Error occurred converting to text completion object - chunk: {chunk}; Error: {str(e)}"
            )

    def __next__(self):
        # model_response = ModelResponse(stream=True, model=self.model)
        TextCompletionResponse()
        try:
            for chunk in self.completion_stream:
                if chunk == "None" or chunk is None:
                    raise Exception
                processed_chunk = self.convert_to_text_completion_object(chunk=chunk)
                return processed_chunk
            raise StopIteration
        except StopIteration:
            raise StopIteration
        except Exception as e:
            raise exception_type(
                model=self.model,
                custom_llm_provider=self.custom_llm_provider or "",
                original_exception=e,
                completion_kwargs={},
                extra_kwargs={},
            )

    async def __anext__(self):
        try:
            async for chunk in self.completion_stream:
                if chunk == "None" or chunk is None:
                    raise Exception
                processed_chunk = self.convert_to_text_completion_object(chunk=chunk)
                return processed_chunk
            raise StopIteration
        except StopIteration:
            raise StopAsyncIteration


def mock_completion_streaming_obj(
    model_response, mock_response, model, n: Optional[int] = None
):
    if isinstance(mock_response, litellm.MockException):
        raise mock_response
    for i in range(0, len(mock_response), 3):
        completion_obj = Delta(role="assistant", content=mock_response[i : i + 3])
        if n is None:
            model_response.choices[0].delta = completion_obj
        else:
            _all_choices = []
            for j in range(n):
                _streaming_choice = litellm.utils.StreamingChoices(
                    index=j,
                    delta=litellm.utils.Delta(
                        role="assistant", content=mock_response[i : i + 3]
                    ),
                )
                _all_choices.append(_streaming_choice)
            model_response.choices = _all_choices
        yield model_response


async def async_mock_completion_streaming_obj(
    model_response, mock_response, model, n: Optional[int] = None
):
    if isinstance(mock_response, litellm.MockException):
        raise mock_response
    for i in range(0, len(mock_response), 3):
        completion_obj = Delta(role="assistant", content=mock_response[i : i + 3])
        if n is None:
            model_response.choices[0].delta = completion_obj
        else:
            _all_choices = []
            for j in range(n):
                _streaming_choice = litellm.utils.StreamingChoices(
                    index=j,
                    delta=litellm.utils.Delta(
                        role="assistant", content=mock_response[i : i + 3]
                    ),
                )
                _all_choices.append(_streaming_choice)
            model_response.choices = _all_choices
        yield model_response


########## Reading Config File ############################
def read_config_args(config_path) -> dict:
    try:
        import os

        os.getcwd()
        with open(config_path, "r") as config_file:
            config = json.load(config_file)

        # read keys/ values from config file and return them
        return config
    except Exception as e:
        raise e


########## experimental completion variants ############################


def process_system_message(system_message, max_tokens, model):
    system_message_event = {"role": "system", "content": system_message}
    system_message_tokens = get_token_count([system_message_event], model)

    if system_message_tokens > max_tokens:
        print_verbose(
            "`tokentrimmer`: Warning, system message exceeds token limit. Trimming..."
        )
        # shorten system message to fit within max_tokens
        new_system_message = shorten_message_to_fit_limit(
            system_message_event, max_tokens, model
        )
        system_message_tokens = get_token_count([new_system_message], model)

    return system_message_event, max_tokens - system_message_tokens


def process_messages(messages, max_tokens, model):
    # Process messages from older to more recent
    messages = messages[::-1]
    final_messages = []
    verbose_logger.debug(
        f"calling process_messages with messages: {messages}, max_tokens: {max_tokens}, model: {model}"
    )
    for message in messages:
        verbose_logger.debug(f"processing final_messages: {final_messages}")
        used_tokens = get_token_count(final_messages, model)
        available_tokens = max_tokens - used_tokens
        verbose_logger.debug(
            f"used_tokens: {used_tokens}, available_tokens: {available_tokens}"
        )
        if available_tokens <= 3:
            break

        final_messages = attempt_message_addition(
            final_messages=final_messages,
            message=message,
            available_tokens=available_tokens,
            max_tokens=max_tokens,
            model=model,
        )
        verbose_logger.debug(
            f"final_messages after attempt_message_addition: {final_messages}"
        )
    verbose_logger.debug(f"Final messages: {final_messages}")
    return final_messages


def attempt_message_addition(
    final_messages, message, available_tokens, max_tokens, model
):
    temp_messages = [message] + final_messages
    temp_message_tokens = get_token_count(messages=temp_messages, model=model)
    verbose_logger.debug(
        f"temp_message_tokens: {temp_message_tokens}, max_tokens: {max_tokens}"
    )
    if temp_message_tokens <= max_tokens:
        return temp_messages

    # if temp_message_tokens > max_tokens, try shortening temp_messages
    elif "function_call" not in message:
        verbose_logger.debug("attempting to shorten message to fit limit")
        # fit updated_message to be within temp_message_tokens - max_tokens (aka the amount temp_message_tokens is greate than max_tokens)
        updated_message = shorten_message_to_fit_limit(message, available_tokens, model)
        if can_add_message(updated_message, final_messages, max_tokens, model):
            verbose_logger.debug(
                "can add message, returning [updated_message] + final_messages"
            )
            return [updated_message] + final_messages
        else:
            verbose_logger.debug("cannot add message, returning final_messages")
    return final_messages


def can_add_message(message, messages, max_tokens, model):
    if get_token_count(messages + [message], model) <= max_tokens:
        return True
    return False


def get_token_count(messages, model):
    return token_counter(model=model, messages=messages)


def shorten_message_to_fit_limit(
    message, tokens_needed, model: Optional[str], raise_error_on_max_limit: bool = False
):
    """
    Shorten a message to fit within a token limit by removing characters from the middle.

    Args:
        message: The message to shorten
        tokens_needed: The maximum number of tokens allowed
        model: The model being used (optional)
        raise_error_on_max_limit: If True, raises an error when max attempts reached. If False, returns final trimmed content.
    """

    # For OpenAI models, even blank messages cost 7 token,
    # and if the buffer is less than 3, the while loop will never end,
    # hence the value 10.
    if model is not None and "gpt" in model and tokens_needed <= 10:
        return message

    content = message["content"]
    attempts = 0

    verbose_logger.debug(f"content: {content}")

    while attempts < MAX_TOKEN_TRIMMING_ATTEMPTS:
        verbose_logger.debug(f"getting token count for message: {message}")
        total_tokens = get_token_count([message], model)
        verbose_logger.debug(
            f"total_tokens: {total_tokens}, tokens_needed: {tokens_needed}"
        )

        if total_tokens <= tokens_needed:
            break

        ratio = (tokens_needed) / total_tokens

        new_length = int(len(content) * ratio) - 1
        new_length = max(0, new_length)

        half_length = new_length // 2
        left_half = content[:half_length]
        right_half = content[-half_length:]

        trimmed_content = left_half + ".." + right_half
        message["content"] = trimmed_content
        verbose_logger.debug(f"trimmed_content: {trimmed_content}")
        content = trimmed_content
        attempts += 1

    if attempts >= MAX_TOKEN_TRIMMING_ATTEMPTS and raise_error_on_max_limit:
        raise Exception(
            f"Failed to trim message to fit within {tokens_needed} tokens after {MAX_TOKEN_TRIMMING_ATTEMPTS} attempts"
        )

    return message


# LiteLLM token trimmer
# this code is borrowed from https://github.com/KillianLucas/tokentrim/blob/main/tokentrim/tokentrim.py
# Credits for this code go to Killian Lucas
def trim_messages(
    messages,
    model: Optional[str] = None,
    trim_ratio: float = DEFAULT_TRIM_RATIO,
    return_response_tokens: bool = False,
    max_tokens=None,
):
    """
    Trim a list of messages to fit within a model's token limit.

    Args:
        messages: Input messages to be trimmed. Each message is a dictionary with 'role' and 'content'.
        model: The LiteLLM model being used (determines the token limit).
        trim_ratio: Target ratio of tokens to use after trimming. Default is 0.75, meaning it will trim messages so they use about 75% of the model's token limit.
        return_response_tokens: If True, also return the number of tokens left available for the response after trimming.
        max_tokens: Instead of specifying a model or trim_ratio, you can specify this directly.

    Returns:
        Trimmed messages and optionally the number of tokens available for response.
    """
    # Initialize max_tokens
    # if users pass in max tokens, trim to this amount
    messages = copy.deepcopy(messages)
    try:
        if max_tokens is None:
            # Check if model is valid
            if model in litellm.model_cost:
                max_tokens_for_model = litellm.model_cost[model].get(
                    "max_input_tokens", litellm.model_cost[model]["max_tokens"]
                )
                max_tokens = int(max_tokens_for_model * trim_ratio)
            else:
                # if user did not specify max (input) tokens
                # or passed an llm litellm does not know
                # do nothing, just return messages
                return messages

        system_message = ""
        for message in messages:
            if message["role"] == "system":
                system_message += "\n" if system_message else ""
                system_message += message["content"]

        ## Handle Tool Call ## - check if last message is a tool response, return as is - https://github.com/BerriAI/litellm/issues/4931
        tool_messages = []

        for message in reversed(messages):
            if message["role"] != "tool":
                break
            tool_messages.append(message)
        # # Remove the collected tool messages from the original list
        if len(tool_messages):
            messages = messages[: -len(tool_messages)]

        current_tokens = token_counter(model=model or "", messages=messages)
        print_verbose(f"Current tokens: {current_tokens}, max tokens: {max_tokens}")

        # Do nothing if current tokens under messages
        if current_tokens < max_tokens:
            return messages

        #### Trimming messages if current_tokens > max_tokens
        print_verbose(
            f"Need to trim input messages: {messages}, current_tokens{current_tokens}, max_tokens: {max_tokens}"
        )
        system_message_event: Optional[dict] = None
        if system_message:
            system_message_event, max_tokens = process_system_message(
                system_message=system_message, max_tokens=max_tokens, model=model
            )

            if max_tokens == 0:  # the system messages are too long
                return [system_message_event]

            # Since all system messages are combined and trimmed to fit the max_tokens,
            # we remove all system messages from the messages list
            messages = [message for message in messages if message["role"] != "system"]

        verbose_logger.debug(f"Processed system message: {system_message_event}")
        final_messages = process_messages(
            messages=messages, max_tokens=max_tokens, model=model
        )
        verbose_logger.debug(f"Processed messages: {final_messages}")

        # Add system message to the beginning of the final messages
        if system_message_event:
            final_messages = [system_message_event] + final_messages

        if len(tool_messages) > 0:
            final_messages.extend(tool_messages)

        verbose_logger.debug(
            f"Final messages: {final_messages}, return_response_tokens: {return_response_tokens}"
        )
        if (
            return_response_tokens
        ):  # if user wants token count with new trimmed messages
            response_tokens = max_tokens - get_token_count(final_messages, model)
            return final_messages, response_tokens
        return final_messages
    except Exception as e:  # [NON-Blocking, if error occurs just return final_messages
        verbose_logger.exception(
            "Got exception while token trimming - {}".format(str(e))
        )
        return messages


from litellm.caching.in_memory_cache import InMemoryCache


class AvailableModelsCache(InMemoryCache):
    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        super().__init__(ttl_seconds, max_size)
        self._env_hash: Optional[str] = None

    def _get_env_hash(self) -> str:
        """Create a hash of relevant environment variables"""
        env_vars = {
            k: v
            for k, v in os.environ.items()
            if k.startswith(("OPENAI", "ANTHROPIC", "AZURE", "AWS"))
        }
        return str(hash(frozenset(env_vars.items())))

    def _check_env_changed(self) -> bool:
        """Check if environment variables have changed"""
        current_hash = self._get_env_hash()
        if self._env_hash is None:
            self._env_hash = current_hash
            return True
        return current_hash != self._env_hash

    def _get_cache_key(
        self,
        custom_llm_provider: Optional[str],
        litellm_params: Optional[LiteLLM_Params],
    ) -> str:
        valid_str = ""

        if litellm_params is not None:
            valid_str = litellm_params.model_dump_json()
        if custom_llm_provider is not None:
            valid_str = f"{custom_llm_provider}:{valid_str}"
        return hashlib.sha256(valid_str.encode()).hexdigest()

    def get_cached_model_info(
        self,
        custom_llm_provider: Optional[str] = None,
        litellm_params: Optional[LiteLLM_Params] = None,
    ) -> Optional[List[str]]:
        """Get cached model info"""
        # Check if environment has changed
        if litellm_params is None and self._check_env_changed():
            self.cache_dict.clear()
            return None

        cache_key = self._get_cache_key(custom_llm_provider, litellm_params)

        result = cast(Optional[List[str]], self.get_cache(cache_key))

        if result is not None:
            return copy.deepcopy(result)
        return result

    def set_cached_model_info(
        self,
        custom_llm_provider: str,
        litellm_params: Optional[LiteLLM_Params],
        available_models: List[str],
    ):
        """Set cached model info"""
        cache_key = self._get_cache_key(custom_llm_provider, litellm_params)
        self.set_cache(cache_key, copy.deepcopy(available_models))


# Global cache instance
_model_cache = AvailableModelsCache()


def _infer_valid_provider_from_env_vars(
    custom_llm_provider: Optional[str] = None,
) -> List[str]:
    valid_providers: List[str] = []
    environ_keys = os.environ.keys()
    for provider in litellm.provider_list:
        if custom_llm_provider and provider != custom_llm_provider:
            continue

        # edge case litellm has together_ai as a provider, it should be togetherai
        env_provider_1 = provider.replace("_", "")
        env_provider_2 = provider

        # litellm standardizes expected provider keys to
        # PROVIDER_API_KEY. Example: OPENAI_API_KEY, COHERE_API_KEY
        expected_provider_key_1 = f"{env_provider_1.upper()}_API_KEY"
        expected_provider_key_2 = f"{env_provider_2.upper()}_API_KEY"
        if (
            expected_provider_key_1 in environ_keys
            or expected_provider_key_2 in environ_keys
        ):
            # key is set
            valid_providers.append(provider)

    return valid_providers


def _get_valid_models_from_provider_api(
    provider_config: BaseLLMModelInfo,
    custom_llm_provider: str,
    litellm_params: Optional[LiteLLM_Params] = None,
) -> List[str]:
    try:
        cached_result = _model_cache.get_cached_model_info(
            custom_llm_provider, litellm_params
        )

        if cached_result is not None:
            return cached_result
        models = provider_config.get_models(
            api_key=litellm_params.api_key if litellm_params is not None else None,
            api_base=litellm_params.api_base if litellm_params is not None else None,
        )

        _model_cache.set_cached_model_info(custom_llm_provider, litellm_params, models)
        return models
    except Exception as e:
        verbose_logger.warning(f"Error getting valid models: {e}")
        return []


def get_valid_models(
    check_provider_endpoint: Optional[bool] = None,
    custom_llm_provider: Optional[str] = None,
    litellm_params: Optional[LiteLLM_Params] = None,
) -> List[str]:
    """
    Returns a list of valid LLMs based on the set environment variables

    Args:
        check_provider_endpoint: If True, will check the provider's endpoint for valid models.
        custom_llm_provider: If provided, will only check the provider's endpoint for valid models.
    Returns:
        A list of valid LLMs
    """

    try:
        check_provider_endpoint = (
            check_provider_endpoint or litellm.check_provider_endpoint
        )
        # get keys set in .env

        valid_providers: List[str] = []
        valid_models: List[str] = []
        # for all valid providers, make a list of supported llms

        if custom_llm_provider:
            valid_providers = [custom_llm_provider]
        else:
            valid_providers = _infer_valid_provider_from_env_vars(custom_llm_provider)

        for provider in valid_providers:
            provider_config = ProviderConfigManager.get_provider_model_info(
                model=None,
                provider=LlmProviders(provider),
            )

            if custom_llm_provider and provider != custom_llm_provider:
                continue

            if provider == "azure":
                valid_models.append("Azure-LLM")
            elif (
                provider_config is not None
                and check_provider_endpoint
                and provider is not None
            ):
                valid_models.extend(
                    _get_valid_models_from_provider_api(
                        provider_config,
                        provider,
                        litellm_params,
                    )
                )
            else:
                models_for_provider = copy.deepcopy(
                    litellm.models_by_provider.get(provider, [])
                )
                valid_models.extend(models_for_provider)

        return valid_models
    except Exception as e:
        verbose_logger.warning(f"Error getting valid models: {e}")
        return []  # NON-Blocking


def print_args_passed_to_litellm(original_function, args, kwargs):
    if not _is_debugging_on():
        return
    try:
        # we've already printed this for acompletion, don't print for completion
        if (
            "acompletion" in kwargs
            and kwargs["acompletion"] is True
            and original_function.__name__ == "completion"
        ):
            return
        elif (
            "aembedding" in kwargs
            and kwargs["aembedding"] is True
            and original_function.__name__ == "embedding"
        ):
            return
        elif (
            "aimg_generation" in kwargs
            and kwargs["aimg_generation"] is True
            and original_function.__name__ == "img_generation"
        ):
            return

        args_str = ", ".join(map(repr, args))
        kwargs_str = ", ".join(f"{key}={repr(value)}" for key, value in kwargs.items())
        print_verbose(
            "\n",
        )  # new line before
        print_verbose(
            "\033[92mRequest to litellm:\033[0m",
        )
        if args and kwargs:
            print_verbose(
                f"\033[92mlitellm.{original_function.__name__}({args_str}, {kwargs_str})\033[0m"
            )
        elif args:
            print_verbose(
                f"\033[92mlitellm.{original_function.__name__}({args_str})\033[0m"
            )
        elif kwargs:
            print_verbose(
                f"\033[92mlitellm.{original_function.__name__}({kwargs_str})\033[0m"
            )
        else:
            print_verbose(f"\033[92mlitellm.{original_function.__name__}()\033[0m")
        print_verbose("\n")  # new line after
    except Exception:
        # This should always be non blocking
        pass


def get_logging_id(start_time, response_obj):
    try:
        response_id = (
            "time-" + start_time.strftime("%H-%M-%S-%f") + "_" + response_obj.get("id")
        )
        return response_id
    except Exception:
        return None


def _get_base_model_from_metadata(model_call_details=None):
    if model_call_details is None:
        return None
    litellm_params = model_call_details.get("litellm_params", {})
    if litellm_params is not None:
        _base_model = litellm_params.get("base_model", None)
        if _base_model is not None:
            return _base_model
        metadata = litellm_params.get("metadata", {})

        return _get_base_model_from_litellm_call_metadata(metadata=metadata)
    return None


class ModelResponseIterator:
    def __init__(self, model_response: ModelResponse, convert_to_delta: bool = False):
        if convert_to_delta is True:
            self.model_response = ModelResponse(stream=True)
            _delta = self.model_response.choices[0].delta  # type: ignore
            _delta.content = model_response.choices[0].message.content  # type: ignore
        else:
            self.model_response = model_response
        self.is_done = False

    # Sync iterator
    def __iter__(self):
        return self

    def __next__(self):
        if self.is_done:
            raise StopIteration
        self.is_done = True
        return self.model_response

    # Async iterator
    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.is_done:
            raise StopAsyncIteration
        self.is_done = True
        return self.model_response


class ModelResponseListIterator:
    def __init__(self, model_responses, delay: Optional[float] = None):
        self.model_responses = model_responses
        self.index = 0
        self.delay = delay

    # Sync iterator
    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.model_responses):
            raise StopIteration
        model_response = self.model_responses[self.index]
        self.index += 1
        if self.delay:
            time.sleep(self.delay)
        return model_response

    # Async iterator
    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.model_responses):
            raise StopAsyncIteration
        model_response = self.model_responses[self.index]
        self.index += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        return model_response


class CustomModelResponseIterator(Iterable):
    def __init__(self) -> None:
        super().__init__()


def is_cached_message(message: AllMessageValues) -> bool:
    """
    Returns true, if message is marked as needing to be cached.

    Used for anthropic/gemini context caching.

    Follows the anthropic format {"cache_control": {"type": "ephemeral"}}
    """
    if "content" not in message:
        return False
    if message["content"] is None or isinstance(message["content"], str):
        return False

    for content in message["content"]:
        if (
            content["type"] == "text"
            and content.get("cache_control") is not None
            and content["cache_control"]["type"] == "ephemeral"  # type: ignore
        ):
            return True

    return False


def is_base64_encoded(s: str) -> bool:
    try:
        # Strip out the prefix if it exists
        if not s.startswith(
            "data:"
        ):  # require `data:` for base64 str, like openai. Prevents false positives like s='Dog'
            return False

        s = s.split(",")[1]

        # Try to decode the string
        decoded_bytes = base64.b64decode(s, validate=True)

        # Check if the original string can be re-encoded to the same string
        return base64.b64encode(decoded_bytes).decode("utf-8") == s
    except Exception:
        return False


def get_base64_str(s: str) -> str:
    """
    s: b64str OR data:image/png;base64,b64str
    """
    if "," in s:
        return s.split(",")[1]
    return s


def has_tool_call_blocks(messages: List[AllMessageValues]) -> bool:
    """
    Returns true, if messages has tool call blocks.

    Used for anthropic/bedrock message validation.
    """
    for message in messages:
        if message.get("tool_calls") is not None:
            return True
    return False


def add_dummy_tool(custom_llm_provider: str) -> List[ChatCompletionToolParam]:
    """
    Prevent Anthropic from raising error when tool_use block exists but no tools are provided.

    Relevent Issues: https://github.com/BerriAI/litellm/issues/5388, https://github.com/BerriAI/litellm/issues/5747
    """
    return [
        ChatCompletionToolParam(
            type="function",
            function=ChatCompletionToolParamFunctionChunk(
                name="dummy_tool",
                description="This is a dummy tool call",  # provided to satisfy bedrock constraint.
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
        )
    ]


from litellm.types.llms.openai import (
    ChatCompletionAudioObject,
    ChatCompletionImageObject,
    ChatCompletionTextObject,
    ChatCompletionUserMessage,
    OpenAIMessageContent,
    ValidUserMessageContentTypes,
)


def convert_to_dict(message: Union[BaseModel, dict]) -> dict:
    """
    Converts a message to a dictionary if it's a Pydantic model.

    Args:
        message: The message, which may be a Pydantic model or a dictionary.

    Returns:
        dict: The converted message.
    """
    if isinstance(message, BaseModel):
        return message.model_dump(exclude_none=True)
    elif isinstance(message, dict):
        return message
    else:
        raise TypeError(
            f"Invalid message type: {type(message)}. Expected dict or Pydantic model."
        )


def convert_list_message_to_dict(messages: List):
    new_messages = []
    for message in messages:
        convert_msg_to_dict = cast(AllMessageValues, convert_to_dict(message))
        cleaned_message = cleanup_none_field_in_message(message=convert_msg_to_dict)
        new_messages.append(cleaned_message)
    return new_messages


def validate_and_fix_openai_messages(messages: List):
    """
    Ensures all messages are valid OpenAI chat completion messages.

    Handles missing role for assistant messages.
    """
    new_messages = []
    for message in messages:
        if not message.get("role"):
            message["role"] = "assistant"
        if message.get("tool_calls"):
            message["tool_calls"] = jsonify_tools(tools=message["tool_calls"])

        convert_msg_to_dict = cast(AllMessageValues, convert_to_dict(message))
        cleaned_message = cleanup_none_field_in_message(message=convert_msg_to_dict)
        new_messages.append(cleaned_message)
    return validate_chat_completion_user_messages(messages=new_messages)


def cleanup_none_field_in_message(message: AllMessageValues):
    """
    Cleans up the message by removing the none field.

    remove None fields in the message - e.g. {"function": None} - some providers raise validation errors
    """
    new_message = message.copy()
    return {k: v for k, v in new_message.items() if v is not None}


def validate_chat_completion_user_messages(messages: List[AllMessageValues]):
    """
    Ensures all user messages are valid OpenAI chat completion messages.

    Args:
        messages: List of message dictionaries
        message_content_type: Type to validate content against

    Returns:
        List[dict]: The validated messages

    Raises:
        ValueError: If any message is invalid
    """
    for idx, m in enumerate(messages):
        try:
            if m["role"] == "user":
                user_content = m.get("content")
                if user_content is not None:
                    if isinstance(user_content, str):
                        continue
                    elif isinstance(user_content, list):
                        for item in user_content:
                            if isinstance(item, dict):
                                if item.get("type") not in ValidUserMessageContentTypes:
                                    raise Exception("invalid content type")
        except Exception as e:
            if isinstance(e, KeyError):
                raise Exception(
                    f"Invalid message={m} at index {idx}. Please ensure all messages are valid OpenAI chat completion messages."
                )
            if "invalid content type" in str(e):
                raise Exception(
                    f"Invalid user message={m} at index {idx}. Please ensure all user messages are valid OpenAI chat completion messages."
                )
            else:
                raise e

    return messages


def validate_chat_completion_tool_choice(
    tool_choice: Optional[Union[dict, str]],
) -> Optional[Union[dict, str]]:
    """
    Confirm the tool choice is passed in the OpenAI format.

    Prevents user errors like: https://github.com/BerriAI/litellm/issues/7483
    """
    from litellm.types.llms.openai import (
        ChatCompletionToolChoiceObjectParam,
        ChatCompletionToolChoiceStringValues,
    )

    if tool_choice is None:
        return tool_choice
    elif isinstance(tool_choice, str):
        return tool_choice
    elif isinstance(tool_choice, dict):
        if tool_choice.get("type") is None or tool_choice.get("function") is None:
            raise Exception(
                f"Invalid tool choice, tool_choice={tool_choice}. Please ensure tool_choice follows the OpenAI spec"
            )
        return tool_choice
    raise Exception(
        f"Invalid tool choice, tool_choice={tool_choice}. Got={type(tool_choice)}. Expecting str, or dict. Please ensure tool_choice follows the OpenAI tool_choice spec"
    )


class ProviderConfigManager:
    @staticmethod
    def get_provider_chat_config(  # noqa: PLR0915
        model: str, provider: LlmProviders
    ) -> Optional[BaseConfig]:
        """
        Returns the provider config for a given provider.
        """
        if (
            provider == LlmProviders.OPENAI
            and litellm.openaiOSeriesConfig.is_model_o_series_model(model=model)
        ):
            return litellm.openaiOSeriesConfig
        elif litellm.LlmProviders.DEEPSEEK == provider:
            return litellm.DeepSeekChatConfig()
        elif litellm.LlmProviders.GROQ == provider:
            return litellm.GroqChatConfig()
        elif litellm.LlmProviders.DATABRICKS == provider:
            return litellm.DatabricksConfig()
        elif litellm.LlmProviders.XAI == provider:
            return litellm.XAIChatConfig()
        elif litellm.LlmProviders.LLAMA == provider:
            return litellm.LlamaAPIConfig()
        elif litellm.LlmProviders.TEXT_COMPLETION_OPENAI == provider:
            return litellm.OpenAITextCompletionConfig()
        elif litellm.LlmProviders.COHERE_CHAT == provider:
            return litellm.CohereChatConfig()
        elif litellm.LlmProviders.COHERE == provider:
            return litellm.CohereConfig()
        elif litellm.LlmProviders.SNOWFLAKE == provider:
            return litellm.SnowflakeConfig()
        elif litellm.LlmProviders.CLARIFAI == provider:
            return litellm.ClarifaiConfig()
        elif litellm.LlmProviders.ANTHROPIC == provider:
            return litellm.AnthropicConfig()
        elif litellm.LlmProviders.ANTHROPIC_TEXT == provider:
            return litellm.AnthropicTextConfig()
        elif litellm.LlmProviders.VERTEX_AI_BETA == provider:
            return litellm.VertexGeminiConfig()
        elif litellm.LlmProviders.VERTEX_AI == provider:
            if "gemini" in model:
                return litellm.VertexGeminiConfig()
            elif "claude" in model:
                return litellm.VertexAIAnthropicConfig()
            elif model in litellm.vertex_mistral_models:
                if "codestral" in model:
                    return litellm.CodestralTextCompletionConfig()
                else:
                    return litellm.MistralConfig()
            elif model in litellm.vertex_ai_ai21_models:
                return litellm.VertexAIAi21Config()
            else:  # use generic openai-like param mapping
                return litellm.VertexAILlama3Config()
        elif litellm.LlmProviders.CLOUDFLARE == provider:
            return litellm.CloudflareChatConfig()
        elif litellm.LlmProviders.SAGEMAKER_CHAT == provider:
            return litellm.SagemakerChatConfig()
        elif litellm.LlmProviders.SAGEMAKER == provider:
            return litellm.SagemakerConfig()
        elif litellm.LlmProviders.FIREWORKS_AI == provider:
            return litellm.FireworksAIConfig()
        elif litellm.LlmProviders.FRIENDLIAI == provider:
            return litellm.FriendliaiChatConfig()
        elif litellm.LlmProviders.WATSONX == provider:
            return litellm.IBMWatsonXChatConfig()
        elif litellm.LlmProviders.WATSONX_TEXT == provider:
            return litellm.IBMWatsonXAIConfig()
        elif litellm.LlmProviders.EMPOWER == provider:
            return litellm.EmpowerChatConfig()
        elif litellm.LlmProviders.GITHUB == provider:
            return litellm.GithubChatConfig()
        elif (
            litellm.LlmProviders.CUSTOM == provider
            or litellm.LlmProviders.CUSTOM_OPENAI == provider
            or litellm.LlmProviders.OPENAI_LIKE == provider
        ):
            return litellm.OpenAILikeChatConfig()
        elif litellm.LlmProviders.AIOHTTP_OPENAI == provider:
            return litellm.AiohttpOpenAIChatConfig()
        elif litellm.LlmProviders.HOSTED_VLLM == provider:
            return litellm.HostedVLLMChatConfig()
        elif litellm.LlmProviders.LLAMAFILE == provider:
            return litellm.LlamafileChatConfig()
        elif litellm.LlmProviders.LM_STUDIO == provider:
            return litellm.LMStudioChatConfig()
        elif litellm.LlmProviders.GALADRIEL == provider:
            return litellm.GaladrielChatConfig()
        elif litellm.LlmProviders.REPLICATE == provider:
            return litellm.ReplicateConfig()
        elif litellm.LlmProviders.HUGGINGFACE == provider:
            return litellm.HuggingFaceChatConfig()
        elif litellm.LlmProviders.TOGETHER_AI == provider:
            return litellm.TogetherAIConfig()
        elif litellm.LlmProviders.OPENROUTER == provider:
            return litellm.OpenrouterConfig()
        elif litellm.LlmProviders.DATAROBOT == provider:
            return litellm.DataRobotConfig()
        elif litellm.LlmProviders.GEMINI == provider:
            return litellm.GoogleAIStudioGeminiConfig()
        elif (
            litellm.LlmProviders.AI21 == provider
            or litellm.LlmProviders.AI21_CHAT == provider
        ):
            return litellm.AI21ChatConfig()
        elif litellm.LlmProviders.AZURE == provider:
            if litellm.AzureOpenAIO1Config().is_o_series_model(model=model):
                return litellm.AzureOpenAIO1Config()
            return litellm.AzureOpenAIConfig()
        elif litellm.LlmProviders.AZURE_AI == provider:
            return litellm.AzureAIStudioConfig()
        elif litellm.LlmProviders.AZURE_TEXT == provider:
            return litellm.AzureOpenAITextConfig()
        elif litellm.LlmProviders.HOSTED_VLLM == provider:
            return litellm.HostedVLLMChatConfig()
        elif litellm.LlmProviders.NLP_CLOUD == provider:
            return litellm.NLPCloudConfig()
        elif litellm.LlmProviders.OOBABOOGA == provider:
            return litellm.OobaboogaConfig()
        elif litellm.LlmProviders.OLLAMA_CHAT == provider:
            return litellm.OllamaChatConfig()
        elif litellm.LlmProviders.DEEPINFRA == provider:
            return litellm.DeepInfraConfig()
        elif litellm.LlmProviders.PERPLEXITY == provider:
            return litellm.PerplexityChatConfig()
        elif (
            litellm.LlmProviders.MISTRAL == provider
            or litellm.LlmProviders.CODESTRAL == provider
        ):
            return litellm.MistralConfig()
        elif litellm.LlmProviders.NVIDIA_NIM == provider:
            return litellm.NvidiaNimConfig()
        elif litellm.LlmProviders.CEREBRAS == provider:
            return litellm.CerebrasConfig()
        elif litellm.LlmProviders.VOLCENGINE == provider:
            return litellm.VolcEngineConfig()
        elif litellm.LlmProviders.TEXT_COMPLETION_CODESTRAL == provider:
            return litellm.CodestralTextCompletionConfig()
        elif litellm.LlmProviders.SAMBANOVA == provider:
            return litellm.SambanovaConfig()
        elif litellm.LlmProviders.MARITALK == provider:
            return litellm.MaritalkConfig()
        elif litellm.LlmProviders.CLOUDFLARE == provider:
            return litellm.CloudflareChatConfig()
        elif litellm.LlmProviders.ANTHROPIC_TEXT == provider:
            return litellm.AnthropicTextConfig()
        elif litellm.LlmProviders.VLLM == provider:
            return litellm.VLLMConfig()
        elif litellm.LlmProviders.OLLAMA == provider:
            return litellm.OllamaConfig()
        elif litellm.LlmProviders.PREDIBASE == provider:
            return litellm.PredibaseConfig()
        elif litellm.LlmProviders.TRITON == provider:
            return litellm.TritonConfig()
        elif litellm.LlmProviders.PETALS == provider:
            return litellm.PetalsConfig()
        elif litellm.LlmProviders.FEATHERLESS_AI == provider:
            return litellm.FeatherlessAIConfig()
        elif litellm.LlmProviders.NOVITA == provider:
            return litellm.NovitaConfig()
        elif litellm.LlmProviders.NEBIUS == provider:
            return litellm.NebiusConfig()
        elif litellm.LlmProviders.BEDROCK == provider:
            bedrock_route = BedrockModelInfo.get_bedrock_route(model)
            bedrock_invoke_provider = litellm.BedrockLLM.get_bedrock_invoke_provider(
                model=model
            )
            base_model = BedrockModelInfo.get_base_model(model)

            if bedrock_route == "converse" or bedrock_route == "converse_like":
                return litellm.AmazonConverseConfig()
            elif bedrock_route == "agent":
                from litellm.llms.bedrock.chat.invoke_agent.transformation import (
                    AmazonInvokeAgentConfig,
                )

                return AmazonInvokeAgentConfig()
            elif bedrock_invoke_provider == "amazon":  # amazon titan llms
                return litellm.AmazonTitanConfig()
            elif bedrock_invoke_provider == "anthropic":
                if base_model.startswith("anthropic.claude-3"):
                    return litellm.AmazonAnthropicClaude3Config()
                else:
                    return litellm.AmazonAnthropicConfig()
            elif (
                bedrock_invoke_provider == "meta" or bedrock_invoke_provider == "llama"
            ):  # amazon / meta llms
                return litellm.AmazonLlamaConfig()
            elif bedrock_invoke_provider == "ai21":  # ai21 llms
                return litellm.AmazonAI21Config()
            elif bedrock_invoke_provider == "cohere":  # cohere models on bedrock
                return litellm.AmazonCohereConfig()
            elif bedrock_invoke_provider == "mistral":  # mistral models on bedrock
                return litellm.AmazonMistralConfig()
            elif bedrock_invoke_provider == "deepseek_r1":  # deepseek models on bedrock
                return litellm.AmazonDeepSeekR1Config()
            elif bedrock_invoke_provider == "nova":
                return litellm.AmazonInvokeNovaConfig()
            else:
                return litellm.AmazonInvokeConfig()
        elif litellm.LlmProviders.LITELLM_PROXY == provider:
            return litellm.LiteLLMProxyChatConfig()
        elif litellm.LlmProviders.OPENAI == provider:
            return litellm.OpenAIGPTConfig()
        elif litellm.LlmProviders.NSCALE == provider:
            return litellm.NscaleConfig()
        return None

    @staticmethod
    def get_provider_embedding_config(
        model: str,
        provider: LlmProviders,
    ) -> Optional[BaseEmbeddingConfig]:
        if litellm.LlmProviders.VOYAGE == provider:
            return litellm.VoyageEmbeddingConfig()
        elif litellm.LlmProviders.TRITON == provider:
            return litellm.TritonEmbeddingConfig()
        elif litellm.LlmProviders.WATSONX == provider:
            return litellm.IBMWatsonXEmbeddingConfig()
        elif litellm.LlmProviders.INFINITY == provider:
            return litellm.InfinityEmbeddingConfig()
        elif (
            litellm.LlmProviders.COHERE == provider
            or litellm.LlmProviders.COHERE_CHAT == provider
        ):
            from litellm.llms.cohere.embed.transformation import CohereEmbeddingConfig

            return CohereEmbeddingConfig()
        return None

    @staticmethod
    def get_provider_rerank_config(
        model: str,
        provider: LlmProviders,
        api_base: Optional[str],
        present_version_params: List[str],
    ) -> BaseRerankConfig:
        if (
            litellm.LlmProviders.COHERE == provider
            or litellm.LlmProviders.COHERE_CHAT == provider
        ):
            if should_use_cohere_v1_client(api_base, present_version_params):
                return litellm.CohereRerankConfig()
            else:
                return litellm.CohereRerankV2Config()
        elif litellm.LlmProviders.AZURE_AI == provider:
            return litellm.AzureAIRerankConfig()
        elif litellm.LlmProviders.INFINITY == provider:
            return litellm.InfinityRerankConfig()
        elif litellm.LlmProviders.JINA_AI == provider:
            return litellm.JinaAIRerankConfig()
        elif litellm.LlmProviders.HUGGINGFACE == provider:
            return litellm.HuggingFaceRerankConfig()
        return litellm.CohereRerankConfig()

    @staticmethod
    def get_provider_anthropic_messages_config(
        model: str,
        provider: LlmProviders,
    ) -> Optional[BaseAnthropicMessagesConfig]:
        if litellm.LlmProviders.ANTHROPIC == provider:
            return litellm.AnthropicMessagesConfig()
        # The 'BEDROCK' provider corresponds to Amazon's implementation of Anthropic Claude v3.
        # This mapping ensures that the correct configuration is returned for BEDROCK.
        elif litellm.LlmProviders.BEDROCK == provider:
            return litellm.AmazonAnthropicClaude3MessagesConfig()
        elif litellm.LlmProviders.VERTEX_AI == provider:
            if "claude" in model:
                from litellm.llms.vertex_ai.vertex_ai_partner_models.anthropic.experimental_pass_through.transformation import (
                    VertexAIPartnerModelsAnthropicMessagesConfig,
                )

                return VertexAIPartnerModelsAnthropicMessagesConfig()
        return None

    @staticmethod
    def get_provider_audio_transcription_config(
        model: str,
        provider: LlmProviders,
    ) -> Optional[BaseAudioTranscriptionConfig]:
        if litellm.LlmProviders.FIREWORKS_AI == provider:
            return litellm.FireworksAIAudioTranscriptionConfig()
        elif litellm.LlmProviders.DEEPGRAM == provider:
            return litellm.DeepgramAudioTranscriptionConfig()
        elif litellm.LlmProviders.OPENAI == provider:
            if "gpt-4o" in model:
                return litellm.OpenAIGPTAudioTranscriptionConfig()
            else:
                return litellm.OpenAIWhisperAudioTranscriptionConfig()
        return None

    @staticmethod
    def get_provider_responses_api_config(
        provider: LlmProviders,
        model: Optional[str] = None,
    ) -> Optional[BaseResponsesAPIConfig]:
        if litellm.LlmProviders.OPENAI == provider:
            return litellm.OpenAIResponsesAPIConfig()
        elif litellm.LlmProviders.AZURE == provider:
            return litellm.AzureOpenAIResponsesAPIConfig()
        return None

    @staticmethod
    def get_provider_text_completion_config(
        model: str,
        provider: LlmProviders,
    ) -> BaseTextCompletionConfig:
        if LlmProviders.FIREWORKS_AI == provider:
            return litellm.FireworksAITextCompletionConfig()
        elif LlmProviders.TOGETHER_AI == provider:
            return litellm.TogetherAITextCompletionConfig()
        return litellm.OpenAITextCompletionConfig()

    @staticmethod
    def get_provider_model_info(
        model: Optional[str],
        provider: LlmProviders,
    ) -> Optional[BaseLLMModelInfo]:
        if LlmProviders.FIREWORKS_AI == provider:
            return litellm.FireworksAIConfig()
        elif LlmProviders.OPENAI == provider:
            return litellm.OpenAIGPTConfig()
        elif LlmProviders.GEMINI == provider:
            return litellm.GeminiModelInfo()
        elif LlmProviders.LITELLM_PROXY == provider:
            return litellm.LiteLLMProxyChatConfig()
        elif LlmProviders.TOPAZ == provider:
            return litellm.TopazModelInfo()
        elif LlmProviders.ANTHROPIC == provider:
            return litellm.AnthropicModelInfo()
        elif LlmProviders.XAI == provider:
            return litellm.XAIModelInfo()
        elif LlmProviders.OLLAMA == provider or LlmProviders.OLLAMA_CHAT == provider:
            # Dynamic model listing for Ollama server
            from litellm.llms.ollama.common_utils import OllamaModelInfo

            return OllamaModelInfo()
        elif LlmProviders.VLLM == provider or LlmProviders.HOSTED_VLLM == provider:
            from litellm.llms.vllm.common_utils import (
                VLLMModelInfo,  # experimental approach, to reduce bloat on __init__.py
            )

            return VLLMModelInfo()
        return None

    @staticmethod
    def get_provider_image_variation_config(
        model: str,
        provider: LlmProviders,
    ) -> Optional[BaseImageVariationConfig]:
        if LlmProviders.OPENAI == provider:
            return litellm.OpenAIImageVariationConfig()
        elif LlmProviders.TOPAZ == provider:
            return litellm.TopazImageVariationConfig()
        return None

    @staticmethod
    def get_provider_files_config(
        model: str,
        provider: LlmProviders,
    ) -> Optional[BaseFilesConfig]:
        if LlmProviders.GEMINI == provider:
            from litellm.llms.gemini.files.transformation import (
                GoogleAIStudioFilesHandler,  # experimental approach, to reduce bloat on __init__.py
            )

            return GoogleAIStudioFilesHandler()
        elif LlmProviders.VERTEX_AI == provider:
            from litellm.llms.vertex_ai.files.transformation import VertexAIFilesConfig

            return VertexAIFilesConfig()
        return None

    @staticmethod
    def get_provider_vector_store_config(
        provider: LlmProviders,
    ) -> Optional[CustomLogger]:
        from litellm.integrations.vector_stores.bedrock_vector_store import (
            BedrockVectorStore,
        )

        if LlmProviders.BEDROCK == provider:
            return BedrockVectorStore.get_initialized_custom_logger()
        return None

    @staticmethod
    def get_provider_image_generation_config(
        model: str,
        provider: LlmProviders,
    ) -> Optional[BaseImageGenerationConfig]:
        if LlmProviders.OPENAI == provider:
            from litellm.llms.openai.image_generation import (
                get_openai_image_generation_config,
            )

            return get_openai_image_generation_config(model)
        elif LlmProviders.AZURE == provider:
            from litellm.llms.azure.image_generation import (
                get_azure_image_generation_config,
            )

            return get_azure_image_generation_config(model)
        return None

    @staticmethod
    def get_provider_realtime_config(
        model: str,
        provider: LlmProviders,
    ) -> Optional[BaseRealtimeConfig]:
        if LlmProviders.GEMINI == provider:
            from litellm.llms.gemini.realtime.transformation import GeminiRealtimeConfig

            return GeminiRealtimeConfig()
        return None

    @staticmethod
    def get_provider_image_edit_config(
        model: str,
        provider: LlmProviders,
    ) -> Optional[BaseImageEditConfig]:
        if LlmProviders.OPENAI == provider:
            from litellm.llms.openai.image_edit.transformation import (
                OpenAIImageEditConfig,
            )

            return OpenAIImageEditConfig()
        if LlmProviders.AZURE == provider:
            from litellm.llms.azure.image_edit.transformation import (
                AzureImageEditConfig,
            )

            return AzureImageEditConfig()
        return None


def get_end_user_id_for_cost_tracking(
    litellm_params: dict,
    service_type: Literal["litellm_logging", "prometheus"] = "litellm_logging",
) -> Optional[str]:
    """
    Used for enforcing `disable_end_user_cost_tracking` param.

    service_type: "litellm_logging" or "prometheus" - used to allow prometheus only disable cost tracking.
    """
    _metadata = cast(dict, litellm_params.get("metadata", {}) or {})

    end_user_id = cast(
        Optional[str],
        litellm_params.get("user_api_key_end_user_id")
        or _metadata.get("user_api_key_end_user_id"),
    )
    if litellm.disable_end_user_cost_tracking:
        return None

    #######################################
    # By default we don't track end_user on prometheus since we don't want to increase cardinality
    # by default litellm.enable_end_user_cost_tracking_prometheus_only is None, so we don't track end_user on prometheus
    #######################################
    if service_type == "prometheus":
        if litellm.enable_end_user_cost_tracking_prometheus_only is not True:
            return None
    return end_user_id


def should_use_cohere_v1_client(
    api_base: Optional[str], present_version_params: List[str]
):
    if not api_base:
        return False
    uses_v1_params = ("max_chunks_per_doc" in present_version_params) and (
        "max_tokens_per_doc" not in present_version_params
    )
    return api_base.endswith("/v1/rerank") or (
        uses_v1_params and not api_base.endswith("/v2/rerank")
    )


def is_prompt_caching_valid_prompt(
    model: str,
    messages: Optional[List[AllMessageValues]],
    tools: Optional[List[ChatCompletionToolParam]] = None,
    custom_llm_provider: Optional[str] = None,
) -> bool:
    """
    Returns true if the prompt is valid for prompt caching.

    OpenAI + Anthropic providers have a minimum token count of 1024 for prompt caching.
    """
    try:
        if messages is None and tools is None:
            return False
        if custom_llm_provider is not None and not model.startswith(
            custom_llm_provider
        ):
            model = custom_llm_provider + "/" + model
        token_count = token_counter(
            messages=messages,
            tools=tools,
            model=model,
            use_default_image_token_count=True,
        )
        return token_count >= MINIMUM_PROMPT_CACHE_TOKEN_COUNT
    except Exception as e:
        verbose_logger.error(f"Error in is_prompt_caching_valid_prompt: {e}")
        return False


def extract_duration_from_srt_or_vtt(srt_or_vtt_content: str) -> Optional[float]:
    """
    Extracts the total duration (in seconds) from SRT or VTT content.

    Args:
        srt_or_vtt_content (str): The content of an SRT or VTT file as a string.

    Returns:
        Optional[float]: The total duration in seconds, or None if no timestamps are found.
    """
    # Regular expression to match timestamps in the format "hh:mm:ss,ms" or "hh:mm:ss.ms"
    timestamp_pattern = r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})"

    timestamps = re.findall(timestamp_pattern, srt_or_vtt_content)

    if not timestamps:
        return None

    # Convert timestamps to seconds and find the max (end time)
    durations = []
    for match in timestamps:
        hours, minutes, seconds, milliseconds = map(int, match)
        total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
        durations.append(total_seconds)

    return max(durations) if durations else None


import httpx


def _add_path_to_api_base(api_base: str, ending_path: str) -> str:
    """
    Adds an ending path to an API base URL while preventing duplicate path segments.

    Args:
        api_base: Base URL string
        ending_path: Path to append to the base URL

    Returns:
        Modified URL string with proper path handling
    """
    original_url = httpx.URL(api_base)
    base_url = original_url.copy_with(params={})  # Removes query params
    base_path = original_url.path.rstrip("/")
    end_path = ending_path.lstrip("/")

    # Split paths into segments
    base_segments = [s for s in base_path.split("/") if s]
    end_segments = [s for s in end_path.split("/") if s]

    # Find overlapping segments from the end of base_path and start of ending_path
    final_segments = []
    for i in range(len(base_segments)):
        if base_segments[i:] == end_segments[: len(base_segments) - i]:
            final_segments = base_segments[:i] + end_segments
            break
    else:
        # No overlap found, just combine all segments
        final_segments = base_segments + end_segments

    # Construct the new path
    modified_path = "/" + "/".join(final_segments)
    modified_url = base_url.copy_with(path=modified_path)

    # Re-add the original query parameters
    return str(modified_url.copy_with(params=original_url.params))


def get_standard_openai_params(params: dict) -> dict:
    return {
        k: v
        for k, v in params.items()
        if k in litellm.OPENAI_CHAT_COMPLETION_PARAMS and v is not None
    }


def get_non_default_completion_params(kwargs: dict) -> dict:
    openai_params = litellm.OPENAI_CHAT_COMPLETION_PARAMS
    default_params = openai_params + all_litellm_params
    non_default_params = {
        k: v for k, v in kwargs.items() if k not in default_params
    }  # model-specific params - pass them straight to the model/provider

    return non_default_params


def get_non_default_transcription_params(kwargs: dict) -> dict:
    from litellm.constants import OPENAI_TRANSCRIPTION_PARAMS

    default_params = OPENAI_TRANSCRIPTION_PARAMS + all_litellm_params
    non_default_params = {k: v for k, v in kwargs.items() if k not in default_params}
    return non_default_params


def add_openai_metadata(metadata: dict) -> dict:
    """
    Add metadata to openai optional parameters, excluding hidden params.

    OpenAI 'metadata' only supports string values.

    Args:
        params (dict): Dictionary of API parameters
        metadata (dict, optional): Metadata to include in the request

    Returns:
        dict: Updated parameters dictionary with visible metadata only
    """
    if metadata is None:
        return None
    # Only include non-hidden parameters
    visible_metadata = {
        k: v
        for k, v in metadata.items()
        if k != "hidden_params" and isinstance(v, (str))
    }

    # max 16 keys allowed by openai - trim down to 16
    if len(visible_metadata) > 16:
        filtered_metadata = {}
        idx = 0
        for k, v in visible_metadata.items():
            if idx < 16:
                filtered_metadata[k] = v
            idx += 1
        visible_metadata = filtered_metadata

    return visible_metadata.copy()


def return_raw_request(endpoint: CallTypes, kwargs: dict) -> RawRequestTypedDict:
    """
    Return the json str of the request

    This is currently in BETA, and tested for `/chat/completions` -> `litellm.completion` calls.
    """
    from datetime import datetime

    from litellm.litellm_core_utils.litellm_logging import Logging

    litellm_logging_obj = Logging(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "hi"}],
        stream=False,
        call_type="acompletion",
        litellm_call_id="1234",
        start_time=datetime.now(),
        function_id="1234",
        log_raw_request_response=True,
    )

    llm_api_endpoint = getattr(litellm, endpoint.value)

    received_exception = ""

    try:
        llm_api_endpoint(
            **kwargs,
            litellm_logging_obj=litellm_logging_obj,
            api_key="my-fake-api-key",  # 👈 ensure the request fails
        )
    except Exception as e:
        received_exception = str(e)

    raw_request_typed_dict = litellm_logging_obj.model_call_details.get(
        "raw_request_typed_dict"
    )
    if raw_request_typed_dict:
        return cast(RawRequestTypedDict, raw_request_typed_dict)
    else:
        return RawRequestTypedDict(
            error=received_exception,
        )


def jsonify_tools(tools: List[Any]) -> List[Dict]:
    """
    Fixes https://github.com/BerriAI/litellm/issues/9321

    Where user passes in a pydantic base model
    """
    new_tools: List[Dict] = []
    for tool in tools:
        if isinstance(tool, BaseModel):
            tool = tool.model_dump(exclude_none=True)
        elif isinstance(tool, dict):
            tool = tool.copy()
        if isinstance(tool, dict):
            new_tools.append(tool)
    return new_tools


def get_empty_usage() -> Usage:
    return Usage(
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
    )

# === NexusCore/openenv\Lib\site-packages\win32\lib\win32evtlogutil.py ===
"""Event Log Utilities - helper for win32evtlog.pyd"""

import win32api
import win32con
import win32evtlog
import winerror

error = win32api.error  # Re-exported alias (The error the evtlog module raises).
langid = win32api.MAKELANGID(win32con.LANG_NEUTRAL, win32con.SUBLANG_NEUTRAL)


def AddSourceToRegistry(
    appName,
    msgDLL=None,
    eventLogType="Application",
    eventLogFlags=None,
    categoryDLL=None,
    categoryCount=0,
):
    """Add a source of messages to the event log.

    Allows Python program to register a custom source of messages in the
    registry.  You must also provide the DLL name that has the message table, so the
    full message text appears in the event log.

    Note that the win32evtlog.pyd file has a number of string entries with just "%1"
    built in, so many Python programs can simply use this DLL.  Disadvantages are that
    you do not get language translation, and the full text is stored in the event log,
    blowing the size of the log up.
    """

    # When an application uses the RegisterEventSource or OpenEventLog
    # function to get a handle of an event log, the event logging service
    # searches for the specified source name in the registry. You can add a
    # new source name to the registry by opening a new registry subkey
    # under the Application key and adding registry values to the new
    # subkey.

    if msgDLL is None:
        msgDLL = win32evtlog.__file__
    # Create a new key for our application
    hkey = win32api.RegCreateKey(
        win32con.HKEY_LOCAL_MACHINE,
        f"SYSTEM\\CurrentControlSet\\Services\\EventLog\\{eventLogType}\\{appName}",
    )

    # Add the Event-ID message-file name to the subkey.
    win32api.RegSetValueEx(
        hkey,
        "EventMessageFile",  # value name \
        0,  # reserved \
        win32con.REG_EXPAND_SZ,  # value type \
        msgDLL,
    )

    # Set the supported types flags and add it to the subkey.
    if eventLogFlags is None:
        eventLogFlags = (
            win32evtlog.EVENTLOG_ERROR_TYPE
            | win32evtlog.EVENTLOG_WARNING_TYPE
            | win32evtlog.EVENTLOG_INFORMATION_TYPE
        )
    win32api.RegSetValueEx(
        hkey,  # subkey handle \
        "TypesSupported",  # value name \
        0,  # reserved \
        win32con.REG_DWORD,  # value type \
        eventLogFlags,
    )

    if categoryCount > 0:
        # Optionally, you can specify a message file that contains the categories
        if categoryDLL is None:
            categoryDLL = win32evtlog.__file__
        win32api.RegSetValueEx(
            hkey,  # subkey handle \
            "CategoryMessageFile",  # value name \
            0,  # reserved \
            win32con.REG_EXPAND_SZ,  # value type \
            categoryDLL,
        )

        win32api.RegSetValueEx(
            hkey,  # subkey handle \
            "CategoryCount",  # value name \
            0,  # reserved \
            win32con.REG_DWORD,  # value type \
            categoryCount,
        )
    win32api.RegCloseKey(hkey)


def RemoveSourceFromRegistry(appName, eventLogType="Application"):
    """Removes a source of messages from the event log."""

    # Delete our key
    try:
        win32api.RegDeleteKey(
            win32con.HKEY_LOCAL_MACHINE,
            f"SYSTEM\\CurrentControlSet\\Services\\EventLog\\{eventLogType}\\{appName}",
        )
    except win32api.error as exc:
        if exc.winerror != winerror.ERROR_FILE_NOT_FOUND:
            raise


def ReportEvent(
    appName,
    eventID,
    eventCategory=0,
    eventType=win32evtlog.EVENTLOG_ERROR_TYPE,
    strings=None,
    data=None,
    sid=None,
):
    """Report an event for a previously added event source."""
    # Get a handle to the Application event log
    hAppLog = win32evtlog.RegisterEventSource(None, appName)

    # Now report the event, which will add this event to the event log */
    win32evtlog.ReportEvent(
        hAppLog,  # event-log handle \
        eventType,
        eventCategory,
        eventID,
        sid,
        strings,
        data,
    )

    win32evtlog.DeregisterEventSource(hAppLog)


def FormatMessage(eventLogRecord, logType="Application"):
    """Given a tuple from ReadEventLog, and optionally where the event
    record came from, load the message, and process message inserts.

    Note that this function may raise win32api.error.  See also the
    function SafeFormatMessage which will return None if the message can
    not be processed.
    """

    # From the event log source name, we know the name of the registry
    # key to look under for the name of the message DLL that contains
    # the messages we need to extract with FormatMessage. So first get
    # the event log source name...
    keyName = "SYSTEM\\CurrentControlSet\\Services\\EventLog\\{}\\{}".format(
        logType,
        eventLogRecord.SourceName,
    )

    # Now open this key and get the EventMessageFile value, which is
    # the name of the message DLL.
    handle = win32api.RegOpenKey(win32con.HKEY_LOCAL_MACHINE, keyName)
    try:
        dllNames = win32api.RegQueryValueEx(handle, "EventMessageFile")[0].split(";")
        # Win2k etc appear to allow multiple DLL names
        data = None
        for dllName in dllNames:
            try:
                # Expand environment variable strings in the message DLL path name,
                # in case any are there.
                dllName = win32api.ExpandEnvironmentStrings(dllName)

                dllHandle = win32api.LoadLibraryEx(
                    dllName, 0, win32con.LOAD_LIBRARY_AS_DATAFILE
                )
                try:
                    data = win32api.FormatMessageW(
                        win32con.FORMAT_MESSAGE_FROM_HMODULE,
                        dllHandle,
                        eventLogRecord.EventID,
                        langid,
                        eventLogRecord.StringInserts,
                    )
                finally:
                    win32api.FreeLibrary(dllHandle)
            except win32api.error:
                pass  # Not in this DLL - try the next
            if data is not None:
                break
    finally:
        win32api.RegCloseKey(handle)
    return data or ""  # Don't want "None" ever being returned.


def SafeFormatMessage(eventLogRecord, logType=None):
    """As for FormatMessage, except returns an error message if
    the message can not be processed.
    """
    if logType is None:
        logType = "Application"
    try:
        return FormatMessage(eventLogRecord, logType)
    except win32api.error:
        if eventLogRecord.StringInserts is None:
            desc = ""
        else:
            desc = ", ".join(eventLogRecord.StringInserts)
        return (
            "<The description for Event ID ( %d ) in Source ( %r ) could not be found. It contains the following insertion string(s):%r.>"
            % (
                winerror.HRESULT_CODE(eventLogRecord.EventID),
                eventLogRecord.SourceName,
                desc,
            )
        )


def FeedEventLogRecords(
    feeder, machineName=None, logName="Application", readFlags=None
):
    if readFlags is None:
        readFlags = (
            win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        )
    h = win32evtlog.OpenEventLog(machineName, logName)
    try:
        while 1:
            objects = win32evtlog.ReadEventLog(h, readFlags, 0)
            if not objects:
                break
            map(lambda item, feeder=feeder: feeder(*(item,)), objects)
    finally:
        win32evtlog.CloseEventLog(h)

# === NexusCore/openenv\Lib\site-packages\numpy\lib\_arrayterator_impl.py ===
"""
A buffered iterator for big arrays.

This module solves the problem of iterating over a big file-based array
without having to read it into memory. The `Arrayterator` class wraps
an array object, and when iterated it will return sub-arrays with at most
a user-specified number of elements.

"""
from functools import reduce
from operator import mul

__all__ = ['Arrayterator']


class Arrayterator:
    """
    Buffered iterator for big arrays.

    `Arrayterator` creates a buffered iterator for reading big arrays in small
    contiguous blocks. The class is useful for objects stored in the
    file system. It allows iteration over the object *without* reading
    everything in memory; instead, small blocks are read and iterated over.

    `Arrayterator` can be used with any object that supports multidimensional
    slices. This includes NumPy arrays, but also variables from
    Scientific.IO.NetCDF or pynetcdf for example.

    Parameters
    ----------
    var : array_like
        The object to iterate over.
    buf_size : int, optional
        The buffer size. If `buf_size` is supplied, the maximum amount of
        data that will be read into memory is `buf_size` elements.
        Default is None, which will read as many element as possible
        into memory.

    Attributes
    ----------
    var
    buf_size
    start
    stop
    step
    shape
    flat

    See Also
    --------
    numpy.ndenumerate : Multidimensional array iterator.
    numpy.flatiter : Flat array iterator.
    numpy.memmap : Create a memory-map to an array stored
                   in a binary file on disk.

    Notes
    -----
    The algorithm works by first finding a "running dimension", along which
    the blocks will be extracted. Given an array of dimensions
    ``(d1, d2, ..., dn)``, e.g. if `buf_size` is smaller than ``d1``, the
    first dimension will be used. If, on the other hand,
    ``d1 < buf_size < d1*d2`` the second dimension will be used, and so on.
    Blocks are extracted along this dimension, and when the last block is
    returned the process continues from the next dimension, until all
    elements have been read.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(3 * 4 * 5 * 6).reshape(3, 4, 5, 6)
    >>> a_itor = np.lib.Arrayterator(a, 2)
    >>> a_itor.shape
    (3, 4, 5, 6)

    Now we can iterate over ``a_itor``, and it will return arrays of size
    two. Since `buf_size` was smaller than any dimension, the first
    dimension will be iterated over first:

    >>> for subarr in a_itor:
    ...     if not subarr.all():
    ...         print(subarr, subarr.shape) # doctest: +SKIP
    >>> # [[[[0 1]]]] (1, 1, 1, 2)

    """

    __module__ = "numpy.lib"

    def __init__(self, var, buf_size=None):
        self.var = var
        self.buf_size = buf_size

        self.start = [0 for dim in var.shape]
        self.stop = list(var.shape)
        self.step = [1 for dim in var.shape]

    def __getattr__(self, attr):
        return getattr(self.var, attr)

    def __getitem__(self, index):
        """
        Return a new arrayterator.

        """
        # Fix index, handling ellipsis and incomplete slices.
        if not isinstance(index, tuple):
            index = (index,)
        fixed = []
        length, dims = len(index), self.ndim
        for slice_ in index:
            if slice_ is Ellipsis:
                fixed.extend([slice(None)] * (dims - length + 1))
                length = len(fixed)
            elif isinstance(slice_, int):
                fixed.append(slice(slice_, slice_ + 1, 1))
            else:
                fixed.append(slice_)
        index = tuple(fixed)
        if len(index) < dims:
            index += (slice(None),) * (dims - len(index))

        # Return a new arrayterator object.
        out = self.__class__(self.var, self.buf_size)
        for i, (start, stop, step, slice_) in enumerate(
                zip(self.start, self.stop, self.step, index)):
            out.start[i] = start + (slice_.start or 0)
            out.step[i] = step * (slice_.step or 1)
            out.stop[i] = start + (slice_.stop or stop - start)
            out.stop[i] = min(stop, out.stop[i])
        return out

    def __array__(self, dtype=None, copy=None):
        """
        Return corresponding data.

        """
        slice_ = tuple(slice(*t) for t in zip(
                self.start, self.stop, self.step))
        return self.var[slice_]

    @property
    def flat(self):
        """
        A 1-D flat iterator for Arrayterator objects.

        This iterator returns elements of the array to be iterated over in
        `~lib.Arrayterator` one by one.
        It is similar to `flatiter`.

        See Also
        --------
        lib.Arrayterator
        flatiter

        Examples
        --------
        >>> a = np.arange(3 * 4 * 5 * 6).reshape(3, 4, 5, 6)
        >>> a_itor = np.lib.Arrayterator(a, 2)

        >>> for subarr in a_itor.flat:
        ...     if not subarr:
        ...         print(subarr, type(subarr))
        ...
        0 <class 'numpy.int64'>

        """
        for block in self:
            yield from block.flat

    @property
    def shape(self):
        """
        The shape of the array to be iterated over.

        For an example, see `Arrayterator`.

        """
        return tuple(((stop - start - 1) // step + 1) for start, stop, step in
                zip(self.start, self.stop, self.step))

    def __iter__(self):
        # Skip arrays with degenerate dimensions
        if [dim for dim in self.shape if dim <= 0]:
            return

        start = self.start[:]
        stop = self.stop[:]
        step = self.step[:]
        ndims = self.var.ndim

        while True:
            count = self.buf_size or reduce(mul, self.shape)

            # iterate over each dimension, looking for the
            # running dimension (ie, the dimension along which
            # the blocks will be built from)
            rundim = 0
            for i in range(ndims - 1, -1, -1):
                # if count is zero we ran out of elements to read
                # along higher dimensions, so we read only a single position
                if count == 0:
                    stop[i] = start[i] + 1
                elif count <= self.shape[i]:
                    # limit along this dimension
                    stop[i] = start[i] + count * step[i]
                    rundim = i
                else:
                    # read everything along this dimension
                    stop[i] = self.stop[i]
                stop[i] = min(self.stop[i], stop[i])
                count = count // self.shape[i]

            # yield a block
            slice_ = tuple(slice(*t) for t in zip(start, stop, step))
            yield self.var[slice_]

            # Update start position, taking care of overflow to
            # other dimensions
            start[rundim] = stop[rundim]  # start where we stopped
            for i in range(ndims - 1, 0, -1):
                if start[i] >= self.stop[i]:
                    start[i] = self.start[i]
                    start[i - 1] += self.step[i - 1]
            if start[0] >= self.stop[0]:
                return

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

# === NexusCore/openenv\Lib\site-packages\numpy\_core\_add_newdocs.py ===
"""
This is only meant to add docs to objects defined in C-extension modules.
The purpose is to allow easier editing of the docstrings without
requiring a re-compile.

NOTE: Many of the methods of ndarray have corresponding functions.
      If you update these docstrings, please keep also the ones in
      _core/fromnumeric.py, matrixlib/defmatrix.py up-to-date.

"""

from numpy._core.function_base import add_newdoc
from numpy._core.overrides import get_array_function_like_doc  # noqa: F401

###############################################################################
#
# flatiter
#
# flatiter needs a toplevel description
#
###############################################################################

add_newdoc('numpy._core', 'flatiter',
    """
    Flat iterator object to iterate over arrays.

    A `flatiter` iterator is returned by ``x.flat`` for any array `x`.
    It allows iterating over the array as if it were a 1-D array,
    either in a for-loop or by calling its `next` method.

    Iteration is done in row-major, C-style order (the last
    index varying the fastest). The iterator can also be indexed using
    basic slicing or advanced indexing.

    See Also
    --------
    ndarray.flat : Return a flat iterator over an array.
    ndarray.flatten : Returns a flattened copy of an array.

    Notes
    -----
    A `flatiter` iterator can not be constructed directly from Python code
    by calling the `flatiter` constructor.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(6).reshape(2, 3)
    >>> fl = x.flat
    >>> type(fl)
    <class 'numpy.flatiter'>
    >>> for item in fl:
    ...     print(item)
    ...
    0
    1
    2
    3
    4
    5

    >>> fl[2:4]
    array([2, 3])

    """)

# flatiter attributes

add_newdoc('numpy._core', 'flatiter', ('base',
    """
    A reference to the array that is iterated over.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(5)
    >>> fl = x.flat
    >>> fl.base is x
    True

    """))


add_newdoc('numpy._core', 'flatiter', ('coords',
    """
    An N-dimensional tuple of current coordinates.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(6).reshape(2, 3)
    >>> fl = x.flat
    >>> fl.coords
    (0, 0)
    >>> next(fl)
    0
    >>> fl.coords
    (0, 1)

    """))


add_newdoc('numpy._core', 'flatiter', ('index',
    """
    Current flat index into the array.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(6).reshape(2, 3)
    >>> fl = x.flat
    >>> fl.index
    0
    >>> next(fl)
    0
    >>> fl.index
    1

    """))

# flatiter functions

add_newdoc('numpy._core', 'flatiter', ('__array__',
    """__array__(type=None) Get array from iterator

    """))


add_newdoc('numpy._core', 'flatiter', ('copy',
    """
    copy()

    Get a copy of the iterator as a 1-D array.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(6).reshape(2, 3)
    >>> x
    array([[0, 1, 2],
           [3, 4, 5]])
    >>> fl = x.flat
    >>> fl.copy()
    array([0, 1, 2, 3, 4, 5])

    """))


###############################################################################
#
# nditer
#
###############################################################################

add_newdoc('numpy._core', 'nditer',
    """
    nditer(op, flags=None, op_flags=None, op_dtypes=None, order='K',
        casting='safe', op_axes=None, itershape=None, buffersize=0)

    Efficient multi-dimensional iterator object to iterate over arrays.
    To get started using this object, see the
    :ref:`introductory guide to array iteration <arrays.nditer>`.

    Parameters
    ----------
    op : ndarray or sequence of array_like
        The array(s) to iterate over.

    flags : sequence of str, optional
          Flags to control the behavior of the iterator.

          * ``buffered`` enables buffering when required.
          * ``c_index`` causes a C-order index to be tracked.
          * ``f_index`` causes a Fortran-order index to be tracked.
          * ``multi_index`` causes a multi-index, or a tuple of indices
            with one per iteration dimension, to be tracked.
          * ``common_dtype`` causes all the operands to be converted to
            a common data type, with copying or buffering as necessary.
          * ``copy_if_overlap`` causes the iterator to determine if read
            operands have overlap with write operands, and make temporary
            copies as necessary to avoid overlap. False positives (needless
            copying) are possible in some cases.
          * ``delay_bufalloc`` delays allocation of the buffers until
            a reset() call is made. Allows ``allocate`` operands to
            be initialized before their values are copied into the buffers.
          * ``external_loop`` causes the ``values`` given to be
            one-dimensional arrays with multiple values instead of
            zero-dimensional arrays.
          * ``grow_inner`` allows the ``value`` array sizes to be made
            larger than the buffer size when both ``buffered`` and
            ``external_loop`` is used.
          * ``ranged`` allows the iterator to be restricted to a sub-range
            of the iterindex values.
          * ``refs_ok`` enables iteration of reference types, such as
            object arrays.
          * ``reduce_ok`` enables iteration of ``readwrite`` operands
            which are broadcasted, also known as reduction operands.
          * ``zerosize_ok`` allows `itersize` to be zero.
    op_flags : list of list of str, optional
          This is a list of flags for each operand. At minimum, one of
          ``readonly``, ``readwrite``, or ``writeonly`` must be specified.

          * ``readonly`` indicates the operand will only be read from.
          * ``readwrite`` indicates the operand will be read from and written to.
          * ``writeonly`` indicates the operand will only be written to.
          * ``no_broadcast`` prevents the operand from being broadcasted.
          * ``contig`` forces the operand data to be contiguous.
          * ``aligned`` forces the operand data to be aligned.
          * ``nbo`` forces the operand data to be in native byte order.
          * ``copy`` allows a temporary read-only copy if required.
          * ``updateifcopy`` allows a temporary read-write copy if required.
          * ``allocate`` causes the array to be allocated if it is None
            in the ``op`` parameter.
          * ``no_subtype`` prevents an ``allocate`` operand from using a subtype.
          * ``arraymask`` indicates that this operand is the mask to use
            for selecting elements when writing to operands with the
            'writemasked' flag set. The iterator does not enforce this,
            but when writing from a buffer back to the array, it only
            copies those elements indicated by this mask.
          * ``writemasked`` indicates that only elements where the chosen
            ``arraymask`` operand is True will be written to.
          * ``overlap_assume_elementwise`` can be used to mark operands that are
            accessed only in the iterator order, to allow less conservative
            copying when ``copy_if_overlap`` is present.
    op_dtypes : dtype or tuple of dtype(s), optional
        The required data type(s) of the operands. If copying or buffering
        is enabled, the data will be converted to/from their original types.
    order : {'C', 'F', 'A', 'K'}, optional
        Controls the iteration order. 'C' means C order, 'F' means
        Fortran order, 'A' means 'F' order if all the arrays are Fortran
        contiguous, 'C' order otherwise, and 'K' means as close to the
        order the array elements appear in memory as possible. This also
        affects the element memory order of ``allocate`` operands, as they
        are allocated to be compatible with iteration order.
        Default is 'K'.
    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        Controls what kind of data casting may occur when making a copy
        or buffering.  Setting this to 'unsafe' is not recommended,
        as it can adversely affect accumulations.

        * 'no' means the data types should not be cast at all.
        * 'equiv' means only byte-order changes are allowed.
        * 'safe' means only casts which can preserve values are allowed.
        * 'same_kind' means only safe casts or casts within a kind,
          like float64 to float32, are allowed.
        * 'unsafe' means any data conversions may be done.
    op_axes : list of list of ints, optional
        If provided, is a list of ints or None for each operands.
        The list of axes for an operand is a mapping from the dimensions
        of the iterator to the dimensions of the operand. A value of
        -1 can be placed for entries, causing that dimension to be
        treated as `newaxis`.
    itershape : tuple of ints, optional
        The desired shape of the iterator. This allows ``allocate`` operands
        with a dimension mapped by op_axes not corresponding to a dimension
        of a different operand to get a value not equal to 1 for that
        dimension.
    buffersize : int, optional
        When buffering is enabled, controls the size of the temporary
        buffers. Set to 0 for the default value.

    Attributes
    ----------
    dtypes : tuple of dtype(s)
        The data types of the values provided in `value`. This may be
        different from the operand data types if buffering is enabled.
        Valid only before the iterator is closed.
    finished : bool
        Whether the iteration over the operands is finished or not.
    has_delayed_bufalloc : bool
        If True, the iterator was created with the ``delay_bufalloc`` flag,
        and no reset() function was called on it yet.
    has_index : bool
        If True, the iterator was created with either the ``c_index`` or
        the ``f_index`` flag, and the property `index` can be used to
        retrieve it.
    has_multi_index : bool
        If True, the iterator was created with the ``multi_index`` flag,
        and the property `multi_index` can be used to retrieve it.
    index
        When the ``c_index`` or ``f_index`` flag was used, this property
        provides access to the index. Raises a ValueError if accessed
        and ``has_index`` is False.
    iterationneedsapi : bool
        Whether iteration requires access to the Python API, for example
        if one of the operands is an object array.
    iterindex : int
        An index which matches the order of iteration.
    itersize : int
        Size of the iterator.
    itviews
        Structured view(s) of `operands` in memory, matching the reordered
        and optimized iterator access pattern. Valid only before the iterator
        is closed.
    multi_index
        When the ``multi_index`` flag was used, this property
        provides access to the index. Raises a ValueError if accessed
        accessed and ``has_multi_index`` is False.
    ndim : int
        The dimensions of the iterator.
    nop : int
        The number of iterator operands.
    operands : tuple of operand(s)
        The array(s) to be iterated over. Valid only before the iterator is
        closed.
    shape : tuple of ints
        Shape tuple, the shape of the iterator.
    value
        Value of ``operands`` at current iteration. Normally, this is a
        tuple of array scalars, but if the flag ``external_loop`` is used,
        it is a tuple of one dimensional arrays.

    Notes
    -----
    `nditer` supersedes `flatiter`.  The iterator implementation behind
    `nditer` is also exposed by the NumPy C API.

    The Python exposure supplies two iteration interfaces, one which follows
    the Python iterator protocol, and another which mirrors the C-style
    do-while pattern.  The native Python approach is better in most cases, but
    if you need the coordinates or index of an iterator, use the C-style pattern.

    Examples
    --------
    Here is how we might write an ``iter_add`` function, using the
    Python iterator protocol:

    >>> import numpy as np

    >>> def iter_add_py(x, y, out=None):
    ...     addop = np.add
    ...     it = np.nditer([x, y, out], [],
    ...                 [['readonly'], ['readonly'], ['writeonly','allocate']])
    ...     with it:
    ...         for (a, b, c) in it:
    ...             addop(a, b, out=c)
    ...         return it.operands[2]

    Here is the same function, but following the C-style pattern:

    >>> def iter_add(x, y, out=None):
    ...    addop = np.add
    ...    it = np.nditer([x, y, out], [],
    ...                [['readonly'], ['readonly'], ['writeonly','allocate']])
    ...    with it:
    ...        while not it.finished:
    ...            addop(it[0], it[1], out=it[2])
    ...            it.iternext()
    ...        return it.operands[2]

    Here is an example outer product function:

    >>> def outer_it(x, y, out=None):
    ...     mulop = np.multiply
    ...     it = np.nditer([x, y, out], ['external_loop'],
    ...             [['readonly'], ['readonly'], ['writeonly', 'allocate']],
    ...             op_axes=[list(range(x.ndim)) + [-1] * y.ndim,
    ...                      [-1] * x.ndim + list(range(y.ndim)),
    ...                      None])
    ...     with it:
    ...         for (a, b, c) in it:
    ...             mulop(a, b, out=c)
    ...         return it.operands[2]

    >>> a = np.arange(2)+1
    >>> b = np.arange(3)+1
    >>> outer_it(a,b)
    array([[1, 2, 3],
           [2, 4, 6]])

    Here is an example function which operates like a "lambda" ufunc:

    >>> def luf(lamdaexpr, *args, **kwargs):
    ...    '''luf(lambdaexpr, op1, ..., opn, out=None, order='K', casting='safe', buffersize=0)'''
    ...    nargs = len(args)
    ...    op = (kwargs.get('out',None),) + args
    ...    it = np.nditer(op, ['buffered','external_loop'],
    ...            [['writeonly','allocate','no_broadcast']] +
    ...                            [['readonly','nbo','aligned']]*nargs,
    ...            order=kwargs.get('order','K'),
    ...            casting=kwargs.get('casting','safe'),
    ...            buffersize=kwargs.get('buffersize',0))
    ...    while not it.finished:
    ...        it[0] = lamdaexpr(*it[1:])
    ...        it.iternext()
    ...    return it.operands[0]

    >>> a = np.arange(5)
    >>> b = np.ones(5)
    >>> luf(lambda i,j:i*i + j/2, a, b)
    array([  0.5,   1.5,   4.5,   9.5,  16.5])

    If operand flags ``"writeonly"`` or ``"readwrite"`` are used the
    operands may be views into the original data with the
    `WRITEBACKIFCOPY` flag. In this case `nditer` must be used as a
    context manager or the `nditer.close` method must be called before
    using the result. The temporary data will be written back to the
    original data when the :meth:`~object.__exit__` function is called
    but not before:

    >>> a = np.arange(6, dtype='i4')[::-2]
    >>> with np.nditer(a, [],
    ...        [['writeonly', 'updateifcopy']],
    ...        casting='unsafe',
    ...        op_dtypes=[np.dtype('f4')]) as i:
    ...    x = i.operands[0]
    ...    x[:] = [-1, -2, -3]
    ...    # a still unchanged here
    >>> a, x
    (array([-1, -2, -3], dtype=int32), array([-1., -2., -3.], dtype=float32))

    It is important to note that once the iterator is exited, dangling
    references (like `x` in the example) may or may not share data with
    the original data `a`. If writeback semantics were active, i.e. if
    `x.base.flags.writebackifcopy` is `True`, then exiting the iterator
    will sever the connection between `x` and `a`, writing to `x` will
    no longer write to `a`. If writeback semantics are not active, then
    `x.data` will still point at some part of `a.data`, and writing to
    one will affect the other.

    Context management and the `close` method appeared in version 1.15.0.

    """)

# nditer methods

add_newdoc('numpy._core', 'nditer', ('copy',
    """
    copy()

    Get a copy of the iterator in its current state.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(10)
    >>> y = x + 1
    >>> it = np.nditer([x, y])
    >>> next(it)
    (array(0), array(1))
    >>> it2 = it.copy()
    >>> next(it2)
    (array(1), array(2))

    """))

add_newdoc('numpy._core', 'nditer', ('operands',
    """
    operands[`Slice`]

    The array(s) to be iterated over. Valid only before the iterator is closed.
    """))

add_newdoc('numpy._core', 'nditer', ('debug_print',
    """
    debug_print()

    Print the current state of the `nditer` instance and debug info to stdout.

    """))

add_newdoc('numpy._core', 'nditer', ('enable_external_loop',
    """
    enable_external_loop()

    When the "external_loop" was not used during construction, but
    is desired, this modifies the iterator to behave as if the flag
    was specified.

    """))

add_newdoc('numpy._core', 'nditer', ('iternext',
    """
    iternext()

    Check whether iterations are left, and perform a single internal iteration
    without returning the result.  Used in the C-style pattern do-while
    pattern.  For an example, see `nditer`.

    Returns
    -------
    iternext : bool
        Whether or not there are iterations left.

    """))

add_newdoc('numpy._core', 'nditer', ('remove_axis',
    """
    remove_axis(i, /)

    Removes axis `i` from the iterator. Requires that the flag "multi_index"
    be enabled.

    """))

add_newdoc('numpy._core', 'nditer', ('remove_multi_index',
    """
    remove_multi_index()

    When the "multi_index" flag was specified, this removes it, allowing
    the internal iteration structure to be optimized further.

    """))

add_newdoc('numpy._core', 'nditer', ('reset',
    """
    reset()

    Reset the iterator to its initial state.

    """))

add_newdoc('numpy._core', 'nested_iters',
    """
    nested_iters(op, axes, flags=None, op_flags=None, op_dtypes=None, \
    order="K", casting="safe", buffersize=0)

    Create nditers for use in nested loops

    Create a tuple of `nditer` objects which iterate in nested loops over
    different axes of the op argument. The first iterator is used in the
    outermost loop, the last in the innermost loop. Advancing one will change
    the subsequent iterators to point at its new element.

    Parameters
    ----------
    op : ndarray or sequence of array_like
        The array(s) to iterate over.

    axes : list of list of int
        Each item is used as an "op_axes" argument to an nditer

    flags, op_flags, op_dtypes, order, casting, buffersize (optional)
        See `nditer` parameters of the same name

    Returns
    -------
    iters : tuple of nditer
        An nditer for each item in `axes`, outermost first

    See Also
    --------
    nditer

    Examples
    --------

    Basic usage. Note how y is the "flattened" version of
    [a[:, 0, :], a[:, 1, 0], a[:, 2, :]] since we specified
    the first iter's axes as [1]

    >>> import numpy as np
    >>> a = np.arange(12).reshape(2, 3, 2)
    >>> i, j = np.nested_iters(a, [[1], [0, 2]], flags=["multi_index"])
    >>> for x in i:
    ...      print(i.multi_index)
    ...      for y in j:
    ...          print('', j.multi_index, y)
    (0,)
     (0, 0) 0
     (0, 1) 1
     (1, 0) 6
     (1, 1) 7
    (1,)
     (0, 0) 2
     (0, 1) 3
     (1, 0) 8
     (1, 1) 9
    (2,)
     (0, 0) 4
     (0, 1) 5
     (1, 0) 10
     (1, 1) 11

    """)

add_newdoc('numpy._core', 'nditer', ('close',
    """
    close()

    Resolve all writeback semantics in writeable operands.

    See Also
    --------

    :ref:`nditer-context-manager`

    """))


###############################################################################
#
# broadcast
#
###############################################################################

add_newdoc('numpy._core', 'broadcast',
    """
    Produce an object that mimics broadcasting.

    Parameters
    ----------
    in1, in2, ... : array_like
        Input parameters.

    Returns
    -------
    b : broadcast object
        Broadcast the input parameters against one another, and
        return an object that encapsulates the result.
        Amongst others, it has ``shape`` and ``nd`` properties, and
        may be used as an iterator.

    See Also
    --------
    broadcast_arrays
    broadcast_to
    broadcast_shapes

    Examples
    --------

    Manually adding two vectors, using broadcasting:

    >>> import numpy as np
    >>> x = np.array([[1], [2], [3]])
    >>> y = np.array([4, 5, 6])
    >>> b = np.broadcast(x, y)

    >>> out = np.empty(b.shape)
    >>> out.flat = [u+v for (u,v) in b]
    >>> out
    array([[5.,  6.,  7.],
           [6.,  7.,  8.],
           [7.,  8.,  9.]])

    Compare against built-in broadcasting:

    >>> x + y
    array([[5, 6, 7],
           [6, 7, 8],
           [7, 8, 9]])

    """)

# attributes

add_newdoc('numpy._core', 'broadcast', ('index',
    """
    current index in broadcasted result

    Examples
    --------

    >>> import numpy as np
    >>> x = np.array([[1], [2], [3]])
    >>> y = np.array([4, 5, 6])
    >>> b = np.broadcast(x, y)
    >>> b.index
    0
    >>> next(b), next(b), next(b)
    ((1, 4), (1, 5), (1, 6))
    >>> b.index
    3

    """))

add_newdoc('numpy._core', 'broadcast', ('iters',
    """
    tuple of iterators along ``self``'s "components."

    Returns a tuple of `numpy.flatiter` objects, one for each "component"
    of ``self``.

    See Also
    --------
    numpy.flatiter

    Examples
    --------

    >>> import numpy as np
    >>> x = np.array([1, 2, 3])
    >>> y = np.array([[4], [5], [6]])
    >>> b = np.broadcast(x, y)
    >>> row, col = b.iters
    >>> next(row), next(col)
    (1, 4)

    """))

add_newdoc('numpy._core', 'broadcast', ('ndim',
    """
    Number of dimensions of broadcasted result. Alias for `nd`.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 3])
    >>> y = np.array([[4], [5], [6]])
    >>> b = np.broadcast(x, y)
    >>> b.ndim
    2

    """))

add_newdoc('numpy._core', 'broadcast', ('nd',
    """
    Number of dimensions of broadcasted result. For code intended for NumPy
    1.12.0 and later the more consistent `ndim` is preferred.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 3])
    >>> y = np.array([[4], [5], [6]])
    >>> b = np.broadcast(x, y)
    >>> b.nd
    2

    """))

add_newdoc('numpy._core', 'broadcast', ('numiter',
    """
    Number of iterators possessed by the broadcasted result.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 3])
    >>> y = np.array([[4], [5], [6]])
    >>> b = np.broadcast(x, y)
    >>> b.numiter
    2

    """))

add_newdoc('numpy._core', 'broadcast', ('shape',
    """
    Shape of broadcasted result.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 3])
    >>> y = np.array([[4], [5], [6]])
    >>> b = np.broadcast(x, y)
    >>> b.shape
    (3, 3)

    """))

add_newdoc('numpy._core', 'broadcast', ('size',
    """
    Total size of broadcasted result.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 3])
    >>> y = np.array([[4], [5], [6]])
    >>> b = np.broadcast(x, y)
    >>> b.size
    9

    """))

add_newdoc('numpy._core', 'broadcast', ('reset',
    """
    reset()

    Reset the broadcasted result's iterator(s).

    Parameters
    ----------
    None

    Returns
    -------
    None

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 3])
    >>> y = np.array([[4], [5], [6]])
    >>> b = np.broadcast(x, y)
    >>> b.index
    0
    >>> next(b), next(b), next(b)
    ((1, 4), (2, 4), (3, 4))
    >>> b.index
    3
    >>> b.reset()
    >>> b.index
    0

    """))

###############################################################################
#
# numpy functions
#
###############################################################################

add_newdoc('numpy._core.multiarray', 'array',
    """
    array(object, dtype=None, *, copy=True, order='K', subok=False, ndmin=0,
          like=None)

    Create an array.

    Parameters
    ----------
    object : array_like
        An array, any object exposing the array interface, an object whose
        ``__array__`` method returns an array, or any (nested) sequence.
        If object is a scalar, a 0-dimensional array containing object is
        returned.
    dtype : data-type, optional
        The desired data-type for the array. If not given, NumPy will try to use
        a default ``dtype`` that can represent the values (by applying promotion
        rules when necessary.)
    copy : bool, optional
        If ``True`` (default), then the array data is copied. If ``None``,
        a copy will only be made if ``__array__`` returns a copy, if obj is
        a nested sequence, or if a copy is needed to satisfy any of the other
        requirements (``dtype``, ``order``, etc.). Note that any copy of
        the data is shallow, i.e., for arrays with object dtype, the new
        array will point to the same objects. See Examples for `ndarray.copy`.
        For ``False`` it raises a ``ValueError`` if a copy cannot be avoided.
        Default: ``True``.
    order : {'K', 'A', 'C', 'F'}, optional
        Specify the memory layout of the array. If object is not an array, the
        newly created array will be in C order (row major) unless 'F' is
        specified, in which case it will be in Fortran order (column major).
        If object is an array the following holds.

        ===== ========= ===================================================
        order  no copy                     copy=True
        ===== ========= ===================================================
        'K'   unchanged F & C order preserved, otherwise most similar order
        'A'   unchanged F order if input is F and not C, otherwise C order
        'C'   C order   C order
        'F'   F order   F order
        ===== ========= ===================================================

        When ``copy=None`` and a copy is made for other reasons, the result is
        the same as if ``copy=True``, with some exceptions for 'A', see the
        Notes section. The default order is 'K'.
    subok : bool, optional
        If True, then sub-classes will be passed-through, otherwise
        the returned array will be forced to be a base-class array (default).
    ndmin : int, optional
        Specifies the minimum number of dimensions that the resulting
        array should have.  Ones will be prepended to the shape as
        needed to meet this requirement.
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray
        An array object satisfying the specified requirements.

    See Also
    --------
    empty_like : Return an empty array with shape and type of input.
    ones_like : Return an array of ones with shape and type of input.
    zeros_like : Return an array of zeros with shape and type of input.
    full_like : Return a new array with shape of input filled with value.
    empty : Return a new uninitialized array.
    ones : Return a new array setting values to one.
    zeros : Return a new array setting values to zero.
    full : Return a new array of given shape filled with value.
    copy: Return an array copy of the given object.


    Notes
    -----
    When order is 'A' and ``object`` is an array in neither 'C' nor 'F' order,
    and a copy is forced by a change in dtype, then the order of the result is
    not necessarily 'C' as expected. This is likely a bug.

    Examples
    --------
    >>> import numpy as np
    >>> np.array([1, 2, 3])
    array([1, 2, 3])

    Upcasting:

    >>> np.array([1, 2, 3.0])
    array([ 1.,  2.,  3.])

    More than one dimension:

    >>> np.array([[1, 2], [3, 4]])
    array([[1, 2],
           [3, 4]])

    Minimum dimensions 2:

    >>> np.array([1, 2, 3], ndmin=2)
    array([[1, 2, 3]])

    Type provided:

    >>> np.array([1, 2, 3], dtype=complex)
    array([ 1.+0.j,  2.+0.j,  3.+0.j])

    Data-type consisting of more than one element:

    >>> x = np.array([(1,2),(3,4)],dtype=[('a','<i4'),('b','<i4')])
    >>> x['a']
    array([1, 3], dtype=int32)

    Creating an array from sub-classes:

    >>> np.array(np.asmatrix('1 2; 3 4'))
    array([[1, 2],
           [3, 4]])

    >>> np.array(np.asmatrix('1 2; 3 4'), subok=True)
    matrix([[1, 2],
            [3, 4]])

    """)

add_newdoc('numpy._core.multiarray', 'asarray',
    """
    asarray(a, dtype=None, order=None, *, device=None, copy=None, like=None)

    Convert the input to an array.

    Parameters
    ----------
    a : array_like
        Input data, in any form that can be converted to an array.  This
        includes lists, lists of tuples, tuples, tuples of tuples, tuples
        of lists and ndarrays.
    dtype : data-type, optional
        By default, the data-type is inferred from the input data.
    order : {'C', 'F', 'A', 'K'}, optional
        Memory layout.  'A' and 'K' depend on the order of input array a.
        'C' row-major (C-style),
        'F' column-major (Fortran-style) memory representation.
        'A' (any) means 'F' if `a` is Fortran contiguous, 'C' otherwise
        'K' (keep) preserve input order
        Defaults to 'K'.
    device : str, optional
        The device on which to place the created array. Default: ``None``.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.0.0
    copy : bool, optional
        If ``True``, then the object is copied. If ``None`` then the object is
        copied only if needed, i.e. if ``__array__`` returns a copy, if obj
        is a nested sequence, or if a copy is needed to satisfy any of
        the other requirements (``dtype``, ``order``, etc.).
        For ``False`` it raises a ``ValueError`` if a copy cannot be avoided.
        Default: ``None``.

        .. versionadded:: 2.0.0
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray
        Array interpretation of ``a``.  No copy is performed if the input
        is already an ndarray with matching dtype and order.  If ``a`` is a
        subclass of ndarray, a base class ndarray is returned.

    See Also
    --------
    asanyarray : Similar function which passes through subclasses.
    ascontiguousarray : Convert input to a contiguous array.
    asfortranarray : Convert input to an ndarray with column-major
                     memory order.
    asarray_chkfinite : Similar function which checks input for NaNs and Infs.
    fromiter : Create an array from an iterator.
    fromfunction : Construct an array by executing a function on grid
                   positions.

    Examples
    --------
    Convert a list into an array:

    >>> a = [1, 2]
    >>> import numpy as np
    >>> np.asarray(a)
    array([1, 2])

    Existing arrays are not copied:

    >>> a = np.array([1, 2])
    >>> np.asarray(a) is a
    True

    If `dtype` is set, array is copied only if dtype does not match:

    >>> a = np.array([1, 2], dtype=np.float32)
    >>> np.shares_memory(np.asarray(a, dtype=np.float32), a)
    True
    >>> np.shares_memory(np.asarray(a, dtype=np.float64), a)
    False

    Contrary to `asanyarray`, ndarray subclasses are not passed through:

    >>> issubclass(np.recarray, np.ndarray)
    True
    >>> a = np.array([(1., 2), (3., 4)], dtype='f4,i4').view(np.recarray)
    >>> np.asarray(a) is a
    False
    >>> np.asanyarray(a) is a
    True

    """)

add_newdoc('numpy._core.multiarray', 'asanyarray',
    """
    asanyarray(a, dtype=None, order=None, *, device=None, copy=None, like=None)

    Convert the input to an ndarray, but pass ndarray subclasses through.

    Parameters
    ----------
    a : array_like
        Input data, in any form that can be converted to an array.  This
        includes scalars, lists, lists of tuples, tuples, tuples of tuples,
        tuples of lists, and ndarrays.
    dtype : data-type, optional
        By default, the data-type is inferred from the input data.
    order : {'C', 'F', 'A', 'K'}, optional
        Memory layout.  'A' and 'K' depend on the order of input array a.
        'C' row-major (C-style),
        'F' column-major (Fortran-style) memory representation.
        'A' (any) means 'F' if `a` is Fortran contiguous, 'C' otherwise
        'K' (keep) preserve input order
        Defaults to 'C'.
    device : str, optional
        The device on which to place the created array. Default: ``None``.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.1.0

    copy : bool, optional
        If ``True``, then the object is copied. If ``None`` then the object is
        copied only if needed, i.e. if ``__array__`` returns a copy, if obj
        is a nested sequence, or if a copy is needed to satisfy any of
        the other requirements (``dtype``, ``order``, etc.).
        For ``False`` it raises a ``ValueError`` if a copy cannot be avoided.
        Default: ``None``.

        .. versionadded:: 2.1.0

    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray or an ndarray subclass
        Array interpretation of `a`.  If `a` is an ndarray or a subclass
        of ndarray, it is returned as-is and no copy is performed.

    See Also
    --------
    asarray : Similar function which always returns ndarrays.
    ascontiguousarray : Convert input to a contiguous array.
    asfortranarray : Convert input to an ndarray with column-major
                     memory order.
    asarray_chkfinite : Similar function which checks input for NaNs and
                        Infs.
    fromiter : Create an array from an iterator.
    fromfunction : Construct an array by executing a function on grid
                   positions.

    Examples
    --------
    Convert a list into an array:

    >>> a = [1, 2]
    >>> import numpy as np
    >>> np.asanyarray(a)
    array([1, 2])

    Instances of `ndarray` subclasses are passed through as-is:

    >>> a = np.array([(1., 2), (3., 4)], dtype='f4,i4').view(np.recarray)
    >>> np.asanyarray(a) is a
    True

    """)

add_newdoc('numpy._core.multiarray', 'ascontiguousarray',
    """
    ascontiguousarray(a, dtype=None, *, like=None)

    Return a contiguous array (ndim >= 1) in memory (C order).

    Parameters
    ----------
    a : array_like
        Input array.
    dtype : str or dtype object, optional
        Data-type of returned array.
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray
        Contiguous array of same shape and content as `a`, with type `dtype`
        if specified.

    See Also
    --------
    asfortranarray : Convert input to an ndarray with column-major
                     memory order.
    require : Return an ndarray that satisfies requirements.
    ndarray.flags : Information about the memory layout of the array.

    Examples
    --------
    Starting with a Fortran-contiguous array:

    >>> import numpy as np
    >>> x = np.ones((2, 3), order='F')
    >>> x.flags['F_CONTIGUOUS']
    True

    Calling ``ascontiguousarray`` makes a C-contiguous copy:

    >>> y = np.ascontiguousarray(x)
    >>> y.flags['C_CONTIGUOUS']
    True
    >>> np.may_share_memory(x, y)
    False

    Now, starting with a C-contiguous array:

    >>> x = np.ones((2, 3), order='C')
    >>> x.flags['C_CONTIGUOUS']
    True

    Then, calling ``ascontiguousarray`` returns the same object:

    >>> y = np.ascontiguousarray(x)
    >>> x is y
    True

    Note: This function returns an array with at least one-dimension (1-d)
    so it will not preserve 0-d arrays.

    """)

add_newdoc('numpy._core.multiarray', 'asfortranarray',
    """
    asfortranarray(a, dtype=None, *, like=None)

    Return an array (ndim >= 1) laid out in Fortran order in memory.

    Parameters
    ----------
    a : array_like
        Input array.
    dtype : str or dtype object, optional
        By default, the data-type is inferred from the input data.
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray
        The input `a` in Fortran, or column-major, order.

    See Also
    --------
    ascontiguousarray : Convert input to a contiguous (C order) array.
    asanyarray : Convert input to an ndarray with either row or
        column-major memory order.
    require : Return an ndarray that satisfies requirements.
    ndarray.flags : Information about the memory layout of the array.

    Examples
    --------
    Starting with a C-contiguous array:

    >>> import numpy as np
    >>> x = np.ones((2, 3), order='C')
    >>> x.flags['C_CONTIGUOUS']
    True

    Calling ``asfortranarray`` makes a Fortran-contiguous copy:

    >>> y = np.asfortranarray(x)
    >>> y.flags['F_CONTIGUOUS']
    True
    >>> np.may_share_memory(x, y)
    False

    Now, starting with a Fortran-contiguous array:

    >>> x = np.ones((2, 3), order='F')
    >>> x.flags['F_CONTIGUOUS']
    True

    Then, calling ``asfortranarray`` returns the same object:

    >>> y = np.asfortranarray(x)
    >>> x is y
    True

    Note: This function returns an array with at least one-dimension (1-d)
    so it will not preserve 0-d arrays.

    """)

add_newdoc('numpy._core.multiarray', 'empty',
    """
    empty(shape, dtype=float, order='C', *, device=None, like=None)

    Return a new array of given shape and type, without initializing entries.

    Parameters
    ----------
    shape : int or tuple of int
        Shape of the empty array, e.g., ``(2, 3)`` or ``2``.
    dtype : data-type, optional
        Desired output data-type for the array, e.g, `numpy.int8`. Default is
        `numpy.float64`.
    order : {'C', 'F'}, optional, default: 'C'
        Whether to store multi-dimensional data in row-major
        (C-style) or column-major (Fortran-style) order in
        memory.
    device : str, optional
        The device on which to place the created array. Default: ``None``.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.0.0
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray
        Array of uninitialized (arbitrary) data of the given shape, dtype, and
        order.  Object arrays will be initialized to None.

    See Also
    --------
    empty_like : Return an empty array with shape and type of input.
    ones : Return a new array setting values to one.
    zeros : Return a new array setting values to zero.
    full : Return a new array of given shape filled with value.

    Notes
    -----
    Unlike other array creation functions (e.g. `zeros`, `ones`, `full`),
    `empty` does not initialize the values of the array, and may therefore be
    marginally faster. However, the values stored in the newly allocated array
    are arbitrary. For reproducible behavior, be sure to set each element of
    the array before reading.

    Examples
    --------
    >>> import numpy as np
    >>> np.empty([2, 2])
    array([[ -9.74499359e+001,   6.69583040e-309],
           [  2.13182611e-314,   3.06959433e-309]])         #uninitialized

    >>> np.empty([2, 2], dtype=int)
    array([[-1073741821, -1067949133],
           [  496041986,    19249760]])                     #uninitialized

    """)

add_newdoc('numpy._core.multiarray', 'scalar',
    """
    scalar(dtype, obj)

    Return a new scalar array of the given type initialized with obj.

    This function is meant mainly for pickle support. `dtype` must be a
    valid data-type descriptor. If `dtype` corresponds to an object
    descriptor, then `obj` can be any object, otherwise `obj` must be a
    string. If `obj` is not given, it will be interpreted as None for object
    type and as zeros for all other types.

    """)

add_newdoc('numpy._core.multiarray', 'zeros',
    """
    zeros(shape, dtype=float, order='C', *, like=None)

    Return a new array of given shape and type, filled with zeros.

    Parameters
    ----------
    shape : int or tuple of ints
        Shape of the new array, e.g., ``(2, 3)`` or ``2``.
    dtype : data-type, optional
        The desired data-type for the array, e.g., `numpy.int8`.  Default is
        `numpy.float64`.
    order : {'C', 'F'}, optional, default: 'C'
        Whether to store multi-dimensional data in row-major
        (C-style) or column-major (Fortran-style) order in
        memory.
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray
        Array of zeros with the given shape, dtype, and order.

    See Also
    --------
    zeros_like : Return an array of zeros with shape and type of input.
    empty : Return a new uninitialized array.
    ones : Return a new array setting values to one.
    full : Return a new array of given shape filled with value.

    Examples
    --------
    >>> import numpy as np
    >>> np.zeros(5)
    array([ 0.,  0.,  0.,  0.,  0.])

    >>> np.zeros((5,), dtype=int)
    array([0, 0, 0, 0, 0])

    >>> np.zeros((2, 1))
    array([[ 0.],
           [ 0.]])

    >>> s = (2,2)
    >>> np.zeros(s)
    array([[ 0.,  0.],
           [ 0.,  0.]])

    >>> np.zeros((2,), dtype=[('x', 'i4'), ('y', 'i4')]) # custom dtype
    array([(0, 0), (0, 0)],
          dtype=[('x', '<i4'), ('y', '<i4')])

    """)

add_newdoc('numpy._core.multiarray', 'set_typeDict',
    """set_typeDict(dict)

    Set the internal dictionary that can look up an array type using a
    registered code.

    """)

add_newdoc('numpy._core.multiarray', 'fromstring',
    """
    fromstring(string, dtype=float, count=-1, *, sep, like=None)

    A new 1-D array initialized from text data in a string.

    Parameters
    ----------
    string : str
        A string containing the data.
    dtype : data-type, optional
        The data type of the array; default: float.  For binary input data,
        the data must be in exactly this format. Most builtin numeric types are
        supported and extension types may be supported.
    count : int, optional
        Read this number of `dtype` elements from the data.  If this is
        negative (the default), the count will be determined from the
        length of the data.
    sep : str, optional
        The string separating numbers in the data; extra whitespace between
        elements is also ignored.

        .. deprecated:: 1.14
            Passing ``sep=''``, the default, is deprecated since it will
            trigger the deprecated binary mode of this function. This mode
            interprets `string` as binary bytes, rather than ASCII text with
            decimal numbers, an operation which is better spelt
            ``frombuffer(string, dtype, count)``. If `string` contains unicode
            text, the binary mode of `fromstring` will first encode it into
            bytes using utf-8, which will not produce sane results.

    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    arr : ndarray
        The constructed array.

    Raises
    ------
    ValueError
        If the string is not the correct size to satisfy the requested
        `dtype` and `count`.

    See Also
    --------
    frombuffer, fromfile, fromiter

    Examples
    --------
    >>> import numpy as np
    >>> np.fromstring('1 2', dtype=int, sep=' ')
    array([1, 2])
    >>> np.fromstring('1, 2', dtype=int, sep=',')
    array([1, 2])

    """)

add_newdoc('numpy._core.multiarray', 'compare_chararrays',
    """
    compare_chararrays(a1, a2, cmp, rstrip)

    Performs element-wise comparison of two string arrays using the
    comparison operator specified by `cmp`.

    Parameters
    ----------
    a1, a2 : array_like
        Arrays to be compared.
    cmp : {"<", "<=", "==", ">=", ">", "!="}
        Type of comparison.
    rstrip : Boolean
        If True, the spaces at the end of Strings are removed before the comparison.

    Returns
    -------
    out : ndarray
        The output array of type Boolean with the same shape as a and b.

    Raises
    ------
    ValueError
        If `cmp` is not valid.
    TypeError
        If at least one of `a` or `b` is a non-string array

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array(["a", "b", "cde"])
    >>> b = np.array(["a", "a", "dec"])
    >>> np.char.compare_chararrays(a, b, ">", True)
    array([False,  True, False])

    """)

add_newdoc('numpy._core.multiarray', 'fromiter',
    """
    fromiter(iter, dtype, count=-1, *, like=None)

    Create a new 1-dimensional array from an iterable object.

    Parameters
    ----------
    iter : iterable object
        An iterable object providing data for the array.
    dtype : data-type
        The data-type of the returned array.

        .. versionchanged:: 1.23
            Object and subarray dtypes are now supported (note that the final
            result is not 1-D for a subarray dtype).

    count : int, optional
        The number of items to read from *iterable*.  The default is -1,
        which means all data is read.
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray
        The output array.

    Notes
    -----
    Specify `count` to improve performance.  It allows ``fromiter`` to
    pre-allocate the output array, instead of resizing it on demand.

    Examples
    --------
    >>> import numpy as np
    >>> iterable = (x*x for x in range(5))
    >>> np.fromiter(iterable, float)
    array([  0.,   1.,   4.,   9.,  16.])

    A carefully constructed subarray dtype will lead to higher dimensional
    results:

    >>> iterable = ((x+1, x+2) for x in range(5))
    >>> np.fromiter(iterable, dtype=np.dtype((int, 2)))
    array([[1, 2],
           [2, 3],
           [3, 4],
           [4, 5],
           [5, 6]])


    """)

add_newdoc('numpy._core.multiarray', 'fromfile',
    """
    fromfile(file, dtype=float, count=-1, sep='', offset=0, *, like=None)

    Construct an array from data in a text or binary file.

    A highly efficient way of reading binary data with a known data-type,
    as well as parsing simply formatted text files.  Data written using the
    `tofile` method can be read using this function.

    Parameters
    ----------
    file : file or str or Path
        Open file object or filename.
    dtype : data-type
        Data type of the returned array.
        For binary files, it is used to determine the size and byte-order
        of the items in the file.
        Most builtin numeric types are supported and extension types may be supported.
    count : int
        Number of items to read. ``-1`` means all items (i.e., the complete
        file).
    sep : str
        Separator between items if file is a text file.
        Empty ("") separator means the file should be treated as binary.
        Spaces (" ") in the separator match zero or more whitespace characters.
        A separator consisting only of spaces must match at least one
        whitespace.
    offset : int
        The offset (in bytes) from the file's current position. Defaults to 0.
        Only permitted for binary files.
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    See also
    --------
    load, save
    ndarray.tofile
    loadtxt : More flexible way of loading data from a text file.

    Notes
    -----
    Do not rely on the combination of `tofile` and `fromfile` for
    data storage, as the binary files generated are not platform
    independent.  In particular, no byte-order or data-type information is
    saved.  Data can be stored in the platform independent ``.npy`` format
    using `save` and `load` instead.

    Examples
    --------
    Construct an ndarray:

    >>> import numpy as np
    >>> dt = np.dtype([('time', [('min', np.int64), ('sec', np.int64)]),
    ...                ('temp', float)])
    >>> x = np.zeros((1,), dtype=dt)
    >>> x['time']['min'] = 10; x['temp'] = 98.25
    >>> x
    array([((10, 0), 98.25)],
          dtype=[('time', [('min', '<i8'), ('sec', '<i8')]), ('temp', '<f8')])

    Save the raw data to disk:

    >>> import tempfile
    >>> fname = tempfile.mkstemp()[1]
    >>> x.tofile(fname)

    Read the raw data from disk:

    >>> np.fromfile(fname, dtype=dt)
    array([((10, 0), 98.25)],
          dtype=[('time', [('min', '<i8'), ('sec', '<i8')]), ('temp', '<f8')])

    The recommended way to store and load data:

    >>> np.save(fname, x)
    >>> np.load(fname + '.npy')
    array([((10, 0), 98.25)],
          dtype=[('time', [('min', '<i8'), ('sec', '<i8')]), ('temp', '<f8')])

    """)

add_newdoc('numpy._core.multiarray', 'frombuffer',
    """
    frombuffer(buffer, dtype=float, count=-1, offset=0, *, like=None)

    Interpret a buffer as a 1-dimensional array.

    Parameters
    ----------
    buffer : buffer_like
        An object that exposes the buffer interface.
    dtype : data-type, optional
        Data-type of the returned array; default: float.
    count : int, optional
        Number of items to read. ``-1`` means all data in the buffer.
    offset : int, optional
        Start reading the buffer from this offset (in bytes); default: 0.
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    out : ndarray

    See also
    --------
    ndarray.tobytes
        Inverse of this operation, construct Python bytes from the raw data
        bytes in the array.

    Notes
    -----
    If the buffer has data that is not in machine byte-order, this should
    be specified as part of the data-type, e.g.::

      >>> dt = np.dtype(int)
      >>> dt = dt.newbyteorder('>')
      >>> np.frombuffer(buf, dtype=dt) # doctest: +SKIP

    The data of the resulting array will not be byteswapped, but will be
    interpreted correctly.

    This function creates a view into the original object.  This should be safe
    in general, but it may make sense to copy the result when the original
    object is mutable or untrusted.

    Examples
    --------
    >>> import numpy as np
    >>> s = b'hello world'
    >>> np.frombuffer(s, dtype='S1', count=5, offset=6)
    array([b'w', b'o', b'r', b'l', b'd'], dtype='|S1')

    >>> np.frombuffer(b'\\x01\\x02', dtype=np.uint8)
    array([1, 2], dtype=uint8)
    >>> np.frombuffer(b'\\x01\\x02\\x03\\x04\\x05', dtype=np.uint8, count=3)
    array([1, 2, 3], dtype=uint8)

    """)

add_newdoc('numpy._core.multiarray', 'from_dlpack',
    """
    from_dlpack(x, /, *, device=None, copy=None)

    Create a NumPy array from an object implementing the ``__dlpack__``
    protocol. Generally, the returned NumPy array is a view of the input
    object. See [1]_ and [2]_ for more details.

    Parameters
    ----------
    x : object
        A Python object that implements the ``__dlpack__`` and
        ``__dlpack_device__`` methods.
    device : device, optional
        Device on which to place the created array. Default: ``None``.
        Must be ``"cpu"`` if passed which may allow importing an array
        that is not already CPU available.
    copy : bool, optional
        Boolean indicating whether or not to copy the input. If ``True``,
        the copy will be made. If ``False``, the function will never copy,
        and will raise ``BufferError`` in case a copy is deemed necessary.
        Passing it requests a copy from the exporter who may or may not
        implement the capability.
        If ``None``, the function will reuse the existing memory buffer if
        possible and copy otherwise. Default: ``None``.


    Returns
    -------
    out : ndarray

    References
    ----------
    .. [1] Array API documentation,
       https://data-apis.org/array-api/latest/design_topics/data_interchange.html#syntax-for-data-interchange-with-dlpack

    .. [2] Python specification for DLPack,
       https://dmlc.github.io/dlpack/latest/python_spec.html

    Examples
    --------
    >>> import torch  # doctest: +SKIP
    >>> x = torch.arange(10)  # doctest: +SKIP
    >>> # create a view of the torch tensor "x" in NumPy
    >>> y = np.from_dlpack(x)  # doctest: +SKIP
    """)

add_newdoc('numpy._core.multiarray', 'correlate',
    """cross_correlate(a,v, mode=0)""")

add_newdoc('numpy._core.multiarray', 'arange',
    """
    arange([start,] stop[, step,], dtype=None, *, device=None, like=None)

    Return evenly spaced values within a given interval.

    ``arange`` can be called with a varying number of positional arguments:

    * ``arange(stop)``: Values are generated within the half-open interval
      ``[0, stop)`` (in other words, the interval including `start` but
      excluding `stop`).
    * ``arange(start, stop)``: Values are generated within the half-open
      interval ``[start, stop)``.
    * ``arange(start, stop, step)`` Values are generated within the half-open
      interval ``[start, stop)``, with spacing between values given by
      ``step``.

    For integer arguments the function is roughly equivalent to the Python
    built-in :py:class:`range`, but returns an ndarray rather than a ``range``
    instance.

    When using a non-integer step, such as 0.1, it is often better to use
    `numpy.linspace`.

    See the Warning sections below for more information.

    Parameters
    ----------
    start : integer or real, optional
        Start of interval.  The interval includes this value.  The default
        start value is 0.
    stop : integer or real
        End of interval.  The interval does not include this value, except
        in some cases where `step` is not an integer and floating point
        round-off affects the length of `out`.
    step : integer or real, optional
        Spacing between values.  For any output `out`, this is the distance
        between two adjacent values, ``out[i+1] - out[i]``.  The default
        step size is 1.  If `step` is specified as a position argument,
        `start` must also be given.
    dtype : dtype, optional
        The type of the output array.  If `dtype` is not given, infer the data
        type from the other input arguments.
    device : str, optional
        The device on which to place the created array. Default: ``None``.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.0.0
    ${ARRAY_FUNCTION_LIKE}

        .. versionadded:: 1.20.0

    Returns
    -------
    arange : ndarray
        Array of evenly spaced values.

        For floating point arguments, the length of the result is
        ``ceil((stop - start)/step)``.  Because of floating point overflow,
        this rule may result in the last element of `out` being greater
        than `stop`.

    Warnings
    --------
    The length of the output might not be numerically stable.

    Another stability issue is due to the internal implementation of
    `numpy.arange`.
    The actual step value used to populate the array is
    ``dtype(start + step) - dtype(start)`` and not `step`. Precision loss
    can occur here, due to casting or due to using floating points when
    `start` is much larger than `step`. This can lead to unexpected
    behaviour. For example::

      >>> np.arange(0, 5, 0.5, dtype=int)
      array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
      >>> np.arange(-3, 3, 0.5, dtype=int)
      array([-3, -2, -1,  0,  1,  2,  3,  4,  5,  6,  7,  8])

    In such cases, the use of `numpy.linspace` should be preferred.

    The built-in :py:class:`range` generates :std:doc:`Python built-in integers
    that have arbitrary size <python:c-api/long>`, while `numpy.arange`
    produces `numpy.int32` or `numpy.int64` numbers. This may result in
    incorrect results for large integer values::

      >>> power = 40
      >>> modulo = 10000
      >>> x1 = [(n ** power) % modulo for n in range(8)]
      >>> x2 = [(n ** power) % modulo for n in np.arange(8)]
      >>> print(x1)
      [0, 1, 7776, 8801, 6176, 625, 6576, 4001]  # correct
      >>> print(x2)
      [0, 1, 7776, 7185, 0, 5969, 4816, 3361]  # incorrect

    See Also
    --------
    numpy.linspace : Evenly spaced numbers with careful handling of endpoints.
    numpy.ogrid: Arrays of evenly spaced numbers in N-dimensions.
    numpy.mgrid: Grid-shaped arrays of evenly spaced numbers in N-dimensions.
    :ref:`how-to-partition`

    Examples
    --------
    >>> import numpy as np
    >>> np.arange(3)
    array([0, 1, 2])
    >>> np.arange(3.0)
    array([ 0.,  1.,  2.])
    >>> np.arange(3,7)
    array([3, 4, 5, 6])
    >>> np.arange(3,7,2)
    array([3, 5])

    """)

add_newdoc('numpy._core.multiarray', '_get_ndarray_c_version',
    """_get_ndarray_c_version()

    Return the compile time NPY_VERSION (formerly called NDARRAY_VERSION) number.

    """)

add_newdoc('numpy._core.multiarray', '_reconstruct',
    """_reconstruct(subtype, shape, dtype)

    Construct an empty array. Used by Pickles.

    """)

add_newdoc('numpy._core.multiarray', 'promote_types',
    """
    promote_types(type1, type2)

    Returns the data type with the smallest size and smallest scalar
    kind to which both ``type1`` and ``type2`` may be safely cast.
    The returned data type is always considered "canonical", this mainly
    means that the promoted dtype will always be in native byte order.

    This function is symmetric, but rarely associative.

    Parameters
    ----------
    type1 : dtype or dtype specifier
        First data type.
    type2 : dtype or dtype specifier
        Second data type.

    Returns
    -------
    out : dtype
        The promoted data type.

    Notes
    -----
    Please see `numpy.result_type` for additional information about promotion.

    Starting in NumPy 1.9, promote_types function now returns a valid string
    length when given an integer or float dtype as one argument and a string
    dtype as another argument. Previously it always returned the input string
    dtype, even if it wasn't long enough to store the max integer/float value
    converted to a string.

    .. versionchanged:: 1.23.0

    NumPy now supports promotion for more structured dtypes.  It will now
    remove unnecessary padding from a structure dtype and promote included
    fields individually.

    See Also
    --------
    result_type, dtype, can_cast

    Examples
    --------
    >>> import numpy as np
    >>> np.promote_types('f4', 'f8')
    dtype('float64')

    >>> np.promote_types('i8', 'f4')
    dtype('float64')

    >>> np.promote_types('>i8', '<c8')
    dtype('complex128')

    >>> np.promote_types('i4', 'S8')
    dtype('S11')

    An example of a non-associative case:

    >>> p = np.promote_types
    >>> p('S', p('i1', 'u1'))
    dtype('S6')
    >>> p(p('S', 'i1'), 'u1')
    dtype('S4')

    """)

add_newdoc('numpy._core.multiarray', 'c_einsum',
    """
    c_einsum(subscripts, *operands, out=None, dtype=None, order='K',
           casting='safe')

    *This documentation shadows that of the native python implementation of the `einsum` function,
    except all references and examples related to the `optimize` argument (v 0.12.0) have been removed.*

    Evaluates the Einstein summation convention on the operands.

    Using the Einstein summation convention, many common multi-dimensional,
    linear algebraic array operations can be represented in a simple fashion.
    In *implicit* mode `einsum` computes these values.

    In *explicit* mode, `einsum` provides further flexibility to compute
    other array operations that might not be considered classical Einstein
    summation operations, by disabling, or forcing summation over specified
    subscript labels.

    See the notes and examples for clarification.

    Parameters
    ----------
    subscripts : str
        Specifies the subscripts for summation as comma separated list of
        subscript labels. An implicit (classical Einstein summation)
        calculation is performed unless the explicit indicator '->' is
        included as well as subscript labels of the precise output form.
    operands : list of array_like
        These are the arrays for the operation.
    out : ndarray, optional
        If provided, the calculation is done into this array.
    dtype : {data-type, None}, optional
        If provided, forces the calculation to use the data type specified.
        Note that you may have to also give a more liberal `casting`
        parameter to allow the conversions. Default is None.
    order : {'C', 'F', 'A', 'K'}, optional
        Controls the memory layout of the output. 'C' means it should
        be C contiguous. 'F' means it should be Fortran contiguous,
        'A' means it should be 'F' if the inputs are all 'F', 'C' otherwise.
        'K' means it should be as close to the layout of the inputs as
        is possible, including arbitrarily permuted axes.
        Default is 'K'.
    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        Controls what kind of data casting may occur.  Setting this to
        'unsafe' is not recommended, as it can adversely affect accumulations.

          * 'no' means the data types should not be cast at all.
          * 'equiv' means only byte-order changes are allowed.
          * 'safe' means only casts which can preserve values are allowed.
          * 'same_kind' means only safe casts or casts within a kind,
            like float64 to float32, are allowed.
          * 'unsafe' means any data conversions may be done.

        Default is 'safe'.
    optimize : {False, True, 'greedy', 'optimal'}, optional
        Controls if intermediate optimization should occur. No optimization
        will occur if False and True will default to the 'greedy' algorithm.
        Also accepts an explicit contraction list from the ``np.einsum_path``
        function. See ``np.einsum_path`` for more details. Defaults to False.

    Returns
    -------
    output : ndarray
        The calculation based on the Einstein summation convention.

    See Also
    --------
    einsum_path, dot, inner, outer, tensordot, linalg.multi_dot

    Notes
    -----
    The Einstein summation convention can be used to compute
    many multi-dimensional, linear algebraic array operations. `einsum`
    provides a succinct way of representing these.

    A non-exhaustive list of these operations,
    which can be computed by `einsum`, is shown below along with examples:

    * Trace of an array, :py:func:`numpy.trace`.
    * Return a diagonal, :py:func:`numpy.diag`.
    * Array axis summations, :py:func:`numpy.sum`.
    * Transpositions and permutations, :py:func:`numpy.transpose`.
    * Matrix multiplication and dot product, :py:func:`numpy.matmul` :py:func:`numpy.dot`.
    * Vector inner and outer products, :py:func:`numpy.inner` :py:func:`numpy.outer`.
    * Broadcasting, element-wise and scalar multiplication, :py:func:`numpy.multiply`.
    * Tensor contractions, :py:func:`numpy.tensordot`.
    * Chained array operations, in efficient calculation order, :py:func:`numpy.einsum_path`.

    The subscripts string is a comma-separated list of subscript labels,
    where each label refers to a dimension of the corresponding operand.
    Whenever a label is repeated it is summed, so ``np.einsum('i,i', a, b)``
    is equivalent to :py:func:`np.inner(a,b) <numpy.inner>`. If a label
    appears only once, it is not summed, so ``np.einsum('i', a)`` produces a
    view of ``a`` with no changes. A further example ``np.einsum('ij,jk', a, b)``
    describes traditional matrix multiplication and is equivalent to
    :py:func:`np.matmul(a,b) <numpy.matmul>`. Repeated subscript labels in one
    operand take the diagonal. For example, ``np.einsum('ii', a)`` is equivalent
    to :py:func:`np.trace(a) <numpy.trace>`.

    In *implicit mode*, the chosen subscripts are important
    since the axes of the output are reordered alphabetically.  This
    means that ``np.einsum('ij', a)`` doesn't affect a 2D array, while
    ``np.einsum('ji', a)`` takes its transpose. Additionally,
    ``np.einsum('ij,jk', a, b)`` returns a matrix multiplication, while,
    ``np.einsum('ij,jh', a, b)`` returns the transpose of the
    multiplication since subscript 'h' precedes subscript 'i'.

    In *explicit mode* the output can be directly controlled by
    specifying output subscript labels.  This requires the
    identifier '->' as well as the list of output subscript labels.
    This feature increases the flexibility of the function since
    summing can be disabled or forced when required. The call
    ``np.einsum('i->', a)`` is like :py:func:`np.sum(a) <numpy.sum>`
    if ``a`` is a 1-D array, and ``np.einsum('ii->i', a)``
    is like :py:func:`np.diag(a) <numpy.diag>` if ``a`` is a square 2-D array.
    The difference is that `einsum` does not allow broadcasting by default.
    Additionally ``np.einsum('ij,jh->ih', a, b)`` directly specifies the
    order of the output subscript labels and therefore returns matrix
    multiplication, unlike the example above in implicit mode.

    To enable and control broadcasting, use an ellipsis.  Default
    NumPy-style broadcasting is done by adding an ellipsis
    to the left of each term, like ``np.einsum('...ii->...i', a)``.
    ``np.einsum('...i->...', a)`` is like
    :py:func:`np.sum(a, axis=-1) <numpy.sum>` for array ``a`` of any shape.
    To take the trace along the first and last axes,
    you can do ``np.einsum('i...i', a)``, or to do a matrix-matrix
    product with the left-most indices instead of rightmost, one can do
    ``np.einsum('ij...,jk...->ik...', a, b)``.

    When there is only one operand, no axes are summed, and no output
    parameter is provided, a view into the operand is returned instead
    of a new array.  Thus, taking the diagonal as ``np.einsum('ii->i', a)``
    produces a view (changed in version 1.10.0).

    `einsum` also provides an alternative way to provide the subscripts
    and operands as ``einsum(op0, sublist0, op1, sublist1, ..., [sublistout])``.
    If the output shape is not provided in this format `einsum` will be
    calculated in implicit mode, otherwise it will be performed explicitly.
    The examples below have corresponding `einsum` calls with the two
    parameter methods.

    Views returned from einsum are now writeable whenever the input array
    is writeable. For example, ``np.einsum('ijk...->kji...', a)`` will now
    have the same effect as :py:func:`np.swapaxes(a, 0, 2) <numpy.swapaxes>`
    and ``np.einsum('ii->i', a)`` will return a writeable view of the diagonal
    of a 2D array.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(25).reshape(5,5)
    >>> b = np.arange(5)
    >>> c = np.arange(6).reshape(2,3)

    Trace of a matrix:

    >>> np.einsum('ii', a)
    60
    >>> np.einsum(a, [0,0])
    60
    >>> np.trace(a)
    60

    Extract the diagonal (requires explicit form):

    >>> np.einsum('ii->i', a)
    array([ 0,  6, 12, 18, 24])
    >>> np.einsum(a, [0,0], [0])
    array([ 0,  6, 12, 18, 24])
    >>> np.diag(a)
    array([ 0,  6, 12, 18, 24])

    Sum over an axis (requires explicit form):

    >>> np.einsum('ij->i', a)
    array([ 10,  35,  60,  85, 110])
    >>> np.einsum(a, [0,1], [0])
    array([ 10,  35,  60,  85, 110])
    >>> np.sum(a, axis=1)
    array([ 10,  35,  60,  85, 110])

    For higher dimensional arrays summing a single axis can be done with ellipsis:

    >>> np.einsum('...j->...', a)
    array([ 10,  35,  60,  85, 110])
    >>> np.einsum(a, [Ellipsis,1], [Ellipsis])
    array([ 10,  35,  60,  85, 110])

    Compute a matrix transpose, or reorder any number of axes:

    >>> np.einsum('ji', c)
    array([[0, 3],
           [1, 4],
           [2, 5]])
    >>> np.einsum('ij->ji', c)
    array([[0, 3],
           [1, 4],
           [2, 5]])
    >>> np.einsum(c, [1,0])
    array([[0, 3],
           [1, 4],
           [2, 5]])
    >>> np.transpose(c)
    array([[0, 3],
           [1, 4],
           [2, 5]])

    Vector inner products:

    >>> np.einsum('i,i', b, b)
    30
    >>> np.einsum(b, [0], b, [0])
    30
    >>> np.inner(b,b)
    30

    Matrix vector multiplication:

    >>> np.einsum('ij,j', a, b)
    array([ 30,  80, 130, 180, 230])
    >>> np.einsum(a, [0,1], b, [1])
    array([ 30,  80, 130, 180, 230])
    >>> np.dot(a, b)
    array([ 30,  80, 130, 180, 230])
    >>> np.einsum('...j,j', a, b)
    array([ 30,  80, 130, 180, 230])

    Broadcasting and scalar multiplication:

    >>> np.einsum('..., ...', 3, c)
    array([[ 0,  3,  6],
           [ 9, 12, 15]])
    >>> np.einsum(',ij', 3, c)
    array([[ 0,  3,  6],
           [ 9, 12, 15]])
    >>> np.einsum(3, [Ellipsis], c, [Ellipsis])
    array([[ 0,  3,  6],
           [ 9, 12, 15]])
    >>> np.multiply(3, c)
    array([[ 0,  3,  6],
           [ 9, 12, 15]])

    Vector outer product:

    >>> np.einsum('i,j', np.arange(2)+1, b)
    array([[0, 1, 2, 3, 4],
           [0, 2, 4, 6, 8]])
    >>> np.einsum(np.arange(2)+1, [0], b, [1])
    array([[0, 1, 2, 3, 4],
           [0, 2, 4, 6, 8]])
    >>> np.outer(np.arange(2)+1, b)
    array([[0, 1, 2, 3, 4],
           [0, 2, 4, 6, 8]])

    Tensor contraction:

    >>> a = np.arange(60.).reshape(3,4,5)
    >>> b = np.arange(24.).reshape(4,3,2)
    >>> np.einsum('ijk,jil->kl', a, b)
    array([[ 4400.,  4730.],
           [ 4532.,  4874.],
           [ 4664.,  5018.],
           [ 4796.,  5162.],
           [ 4928.,  5306.]])
    >>> np.einsum(a, [0,1,2], b, [1,0,3], [2,3])
    array([[ 4400.,  4730.],
           [ 4532.,  4874.],
           [ 4664.,  5018.],
           [ 4796.,  5162.],
           [ 4928.,  5306.]])
    >>> np.tensordot(a,b, axes=([1,0],[0,1]))
    array([[ 4400.,  4730.],
           [ 4532.,  4874.],
           [ 4664.,  5018.],
           [ 4796.,  5162.],
           [ 4928.,  5306.]])

    Writeable returned arrays (since version 1.10.0):

    >>> a = np.zeros((3, 3))
    >>> np.einsum('ii->i', a)[:] = 1
    >>> a
    array([[ 1.,  0.,  0.],
           [ 0.,  1.,  0.],
           [ 0.,  0.,  1.]])

    Example of ellipsis use:

    >>> a = np.arange(6).reshape((3,2))
    >>> b = np.arange(12).reshape((4,3))
    >>> np.einsum('ki,jk->ij', a, b)
    array([[10, 28, 46, 64],
           [13, 40, 67, 94]])
    >>> np.einsum('ki,...k->i...', a, b)
    array([[10, 28, 46, 64],
           [13, 40, 67, 94]])
    >>> np.einsum('k...,jk', a, b)
    array([[10, 28, 46, 64],
           [13, 40, 67, 94]])

    """)


##############################################################################
#
# Documentation for ndarray attributes and methods
#
##############################################################################


##############################################################################
#
# ndarray object
#
##############################################################################


add_newdoc('numpy._core.multiarray', 'ndarray',
    """
    ndarray(shape, dtype=float, buffer=None, offset=0,
            strides=None, order=None)

    An array object represents a multidimensional, homogeneous array
    of fixed-size items.  An associated data-type object describes the
    format of each element in the array (its byte-order, how many bytes it
    occupies in memory, whether it is an integer, a floating point number,
    or something else, etc.)

    Arrays should be constructed using `array`, `zeros` or `empty` (refer
    to the See Also section below).  The parameters given here refer to
    a low-level method (`ndarray(...)`) for instantiating an array.

    For more information, refer to the `numpy` module and examine the
    methods and attributes of an array.

    Parameters
    ----------
    (for the __new__ method; see Notes below)

    shape : tuple of ints
        Shape of created array.
    dtype : data-type, optional
        Any object that can be interpreted as a numpy data type.
    buffer : object exposing buffer interface, optional
        Used to fill the array with data.
    offset : int, optional
        Offset of array data in buffer.
    strides : tuple of ints, optional
        Strides of data in memory.
    order : {'C', 'F'}, optional
        Row-major (C-style) or column-major (Fortran-style) order.

    Attributes
    ----------
    T : ndarray
        Transpose of the array.
    data : buffer
        The array's elements, in memory.
    dtype : dtype object
        Describes the format of the elements in the array.
    flags : dict
        Dictionary containing information related to memory use, e.g.,
        'C_CONTIGUOUS', 'OWNDATA', 'WRITEABLE', etc.
    flat : numpy.flatiter object
        Flattened version of the array as an iterator.  The iterator
        allows assignments, e.g., ``x.flat = 3`` (See `ndarray.flat` for
        assignment examples; TODO).
    imag : ndarray
        Imaginary part of the array.
    real : ndarray
        Real part of the array.
    size : int
        Number of elements in the array.
    itemsize : int
        The memory use of each array element in bytes.
    nbytes : int
        The total number of bytes required to store the array data,
        i.e., ``itemsize * size``.
    ndim : int
        The array's number of dimensions.
    shape : tuple of ints
        Shape of the array.
    strides : tuple of ints
        The step-size required to move from one element to the next in
        memory. For example, a contiguous ``(3, 4)`` array of type
        ``int16`` in C-order has strides ``(8, 2)``.  This implies that
        to move from element to element in memory requires jumps of 2 bytes.
        To move from row-to-row, one needs to jump 8 bytes at a time
        (``2 * 4``).
    ctypes : ctypes object
        Class containing properties of the array needed for interaction
        with ctypes.
    base : ndarray
        If the array is a view into another array, that array is its `base`
        (unless that array is also a view).  The `base` array is where the
        array data is actually stored.

    See Also
    --------
    array : Construct an array.
    zeros : Create an array, each element of which is zero.
    empty : Create an array, but leave its allocated memory unchanged (i.e.,
            it contains "garbage").
    dtype : Create a data-type.
    numpy.typing.NDArray : An ndarray alias :term:`generic <generic type>`
                           w.r.t. its `dtype.type <numpy.dtype.type>`.

    Notes
    -----
    There are two modes of creating an array using ``__new__``:

    1. If `buffer` is None, then only `shape`, `dtype`, and `order`
       are used.
    2. If `buffer` is an object exposing the buffer interface, then
       all keywords are interpreted.

    No ``__init__`` method is needed because the array is fully initialized
    after the ``__new__`` method.

    Examples
    --------
    These examples illustrate the low-level `ndarray` constructor.  Refer
    to the `See Also` section above for easier ways of constructing an
    ndarray.

    First mode, `buffer` is None:

    >>> import numpy as np
    >>> np.ndarray(shape=(2,2), dtype=float, order='F')
    array([[0.0e+000, 0.0e+000], # random
           [     nan, 2.5e-323]])

    Second mode:

    >>> np.ndarray((2,), buffer=np.array([1,2,3]),
    ...            offset=np.int_().itemsize,
    ...            dtype=int) # offset = 1*itemsize, i.e. skip first element
    array([2, 3])

    """)


##############################################################################
#
# ndarray attributes
#
##############################################################################


add_newdoc('numpy._core.multiarray', 'ndarray', ('__array_interface__',
    """Array protocol: Python side."""))


add_newdoc('numpy._core.multiarray', 'ndarray', ('__array_priority__',
    """Array priority."""))


add_newdoc('numpy._core.multiarray', 'ndarray', ('__array_struct__',
    """Array protocol: C-struct side."""))

add_newdoc('numpy._core.multiarray', 'ndarray', ('__dlpack__',
    """
    a.__dlpack__(*, stream=None, max_version=None, dl_device=None, copy=None)

    DLPack Protocol: Part of the Array API.

    """))

add_newdoc('numpy._core.multiarray', 'ndarray', ('__dlpack_device__',
    """
    a.__dlpack_device__()

    DLPack Protocol: Part of the Array API.

    """))

add_newdoc('numpy._core.multiarray', 'ndarray', ('base',
    """
    Base object if memory is from some other object.

    Examples
    --------
    The base of an array that owns its memory is None:

    >>> import numpy as np
    >>> x = np.array([1,2,3,4])
    >>> x.base is None
    True

    Slicing creates a view, whose memory is shared with x:

    >>> y = x[2:]
    >>> y.base is x
    True

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('ctypes',
    """
    An object to simplify the interaction of the array with the ctypes
    module.

    This attribute creates an object that makes it easier to use arrays
    when calling shared libraries with the ctypes module. The returned
    object has, among others, data, shape, and strides attributes (see
    Notes below) which themselves return ctypes objects that can be used
    as arguments to a shared library.

    Parameters
    ----------
    None

    Returns
    -------
    c : Python object
        Possessing attributes data, shape, strides, etc.

    See Also
    --------
    numpy.ctypeslib

    Notes
    -----
    Below are the public attributes of this object which were documented
    in "Guide to NumPy" (we have omitted undocumented public attributes,
    as well as documented private attributes):

    .. autoattribute:: numpy._core._internal._ctypes.data
        :noindex:

    .. autoattribute:: numpy._core._internal._ctypes.shape
        :noindex:

    .. autoattribute:: numpy._core._internal._ctypes.strides
        :noindex:

    .. automethod:: numpy._core._internal._ctypes.data_as
        :noindex:

    .. automethod:: numpy._core._internal._ctypes.shape_as
        :noindex:

    .. automethod:: numpy._core._internal._ctypes.strides_as
        :noindex:

    If the ctypes module is not available, then the ctypes attribute
    of array objects still returns something useful, but ctypes objects
    are not returned and errors may be raised instead. In particular,
    the object will still have the ``as_parameter`` attribute which will
    return an integer equal to the data attribute.

    Examples
    --------
    >>> import numpy as np
    >>> import ctypes
    >>> x = np.array([[0, 1], [2, 3]], dtype=np.int32)
    >>> x
    array([[0, 1],
           [2, 3]], dtype=int32)
    >>> x.ctypes.data
    31962608 # may vary
    >>> x.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
    <__main__.LP_c_uint object at 0x7ff2fc1fc200> # may vary
    >>> x.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32)).contents
    c_uint(0)
    >>> x.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64)).contents
    c_ulong(4294967296)
    >>> x.ctypes.shape
    <numpy._core._internal.c_long_Array_2 object at 0x7ff2fc1fce60> # may vary
    >>> x.ctypes.strides
    <numpy._core._internal.c_long_Array_2 object at 0x7ff2fc1ff320> # may vary

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('data',
    """Python buffer object pointing to the start of the array's data."""))


add_newdoc('numpy._core.multiarray', 'ndarray', ('dtype',
    """
    Data-type of the array's elements.

    .. warning::

        Setting ``arr.dtype`` is discouraged and may be deprecated in the
        future.  Setting will replace the ``dtype`` without modifying the
        memory (see also `ndarray.view` and `ndarray.astype`).

    Parameters
    ----------
    None

    Returns
    -------
    d : numpy dtype object

    See Also
    --------
    ndarray.astype : Cast the values contained in the array to a new data-type.
    ndarray.view : Create a view of the same data but a different data-type.
    numpy.dtype

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(4).reshape((2, 2))
    >>> x
    array([[0, 1],
           [2, 3]])
    >>> x.dtype
    dtype('int64')   # may vary (OS, bitness)
    >>> isinstance(x.dtype, np.dtype)
    True

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('imag',
    """
    The imaginary part of the array.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.sqrt([1+0j, 0+1j])
    >>> x.imag
    array([ 0.        ,  0.70710678])
    >>> x.imag.dtype
    dtype('float64')

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('itemsize',
    """
    Length of one array element in bytes.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1,2,3], dtype=np.float64)
    >>> x.itemsize
    8
    >>> x = np.array([1,2,3], dtype=np.complex128)
    >>> x.itemsize
    16

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('flags',
    """
    Information about the memory layout of the array.

    Attributes
    ----------
    C_CONTIGUOUS (C)
        The data is in a single, C-style contiguous segment.
    F_CONTIGUOUS (F)
        The data is in a single, Fortran-style contiguous segment.
    OWNDATA (O)
        The array owns the memory it uses or borrows it from another object.
    WRITEABLE (W)
        The data area can be written to.  Setting this to False locks
        the data, making it read-only.  A view (slice, etc.) inherits WRITEABLE
        from its base array at creation time, but a view of a writeable
        array may be subsequently locked while the base array remains writeable.
        (The opposite is not true, in that a view of a locked array may not
        be made writeable.  However, currently, locking a base object does not
        lock any views that already reference it, so under that circumstance it
        is possible to alter the contents of a locked array via a previously
        created writeable view onto it.)  Attempting to change a non-writeable
        array raises a RuntimeError exception.
    ALIGNED (A)
        The data and all elements are aligned appropriately for the hardware.
    WRITEBACKIFCOPY (X)
        This array is a copy of some other array. The C-API function
        PyArray_ResolveWritebackIfCopy must be called before deallocating
        to the base array will be updated with the contents of this array.
    FNC
        F_CONTIGUOUS and not C_CONTIGUOUS.
    FORC
        F_CONTIGUOUS or C_CONTIGUOUS (one-segment test).
    BEHAVED (B)
        ALIGNED and WRITEABLE.
    CARRAY (CA)
        BEHAVED and C_CONTIGUOUS.
    FARRAY (FA)
        BEHAVED and F_CONTIGUOUS and not C_CONTIGUOUS.

    Notes
    -----
    The `flags` object can be accessed dictionary-like (as in ``a.flags['WRITEABLE']``),
    or by using lowercased attribute names (as in ``a.flags.writeable``). Short flag
    names are only supported in dictionary access.

    Only the WRITEBACKIFCOPY, WRITEABLE, and ALIGNED flags can be
    changed by the user, via direct assignment to the attribute or dictionary
    entry, or by calling `ndarray.setflags`.

    The array flags cannot be set arbitrarily:

    - WRITEBACKIFCOPY can only be set ``False``.
    - ALIGNED can only be set ``True`` if the data is truly aligned.
    - WRITEABLE can only be set ``True`` if the array owns its own memory
      or the ultimate owner of the memory exposes a writeable buffer
      interface or is a string.

    Arrays can be both C-style and Fortran-style contiguous simultaneously.
    This is clear for 1-dimensional arrays, but can also be true for higher
    dimensional arrays.

    Even for contiguous arrays a stride for a given dimension
    ``arr.strides[dim]`` may be *arbitrary* if ``arr.shape[dim] == 1``
    or the array has no elements.
    It does *not* generally hold that ``self.strides[-1] == self.itemsize``
    for C-style contiguous arrays or ``self.strides[0] == self.itemsize`` for
    Fortran-style contiguous arrays is true.
    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('flat',
    """
    A 1-D iterator over the array.

    This is a `numpy.flatiter` instance, which acts similarly to, but is not
    a subclass of, Python's built-in iterator object.

    See Also
    --------
    flatten : Return a copy of the array collapsed into one dimension.

    flatiter

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(1, 7).reshape(2, 3)
    >>> x
    array([[1, 2, 3],
           [4, 5, 6]])
    >>> x.flat[3]
    4
    >>> x.T
    array([[1, 4],
           [2, 5],
           [3, 6]])
    >>> x.T.flat[3]
    5
    >>> type(x.flat)
    <class 'numpy.flatiter'>

    An assignment example:

    >>> x.flat = 3; x
    array([[3, 3, 3],
           [3, 3, 3]])
    >>> x.flat[[1,4]] = 1; x
    array([[3, 1, 3],
           [3, 1, 3]])

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('nbytes',
    """
    Total bytes consumed by the elements of the array.

    Notes
    -----
    Does not include memory consumed by non-element attributes of the
    array object.

    See Also
    --------
    sys.getsizeof
        Memory consumed by the object itself without parents in case view.
        This does include memory consumed by non-element attributes.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.zeros((3,5,2), dtype=np.complex128)
    >>> x.nbytes
    480
    >>> np.prod(x.shape) * x.itemsize
    480

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('ndim',
    """
    Number of array dimensions.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 3])
    >>> x.ndim
    1
    >>> y = np.zeros((2, 3, 4))
    >>> y.ndim
    3

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('real',
    """
    The real part of the array.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.sqrt([1+0j, 0+1j])
    >>> x.real
    array([ 1.        ,  0.70710678])
    >>> x.real.dtype
    dtype('float64')

    See Also
    --------
    numpy.real : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('shape',
    """
    Tuple of array dimensions.

    The shape property is usually used to get the current shape of an array,
    but may also be used to reshape the array in-place by assigning a tuple of
    array dimensions to it.  As with `numpy.reshape`, one of the new shape
    dimensions can be -1, in which case its value is inferred from the size of
    the array and the remaining dimensions. Reshaping an array in-place will
    fail if a copy is required.

    .. warning::

        Setting ``arr.shape`` is discouraged and may be deprecated in the
        future.  Using `ndarray.reshape` is the preferred approach.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 3, 4])
    >>> x.shape
    (4,)
    >>> y = np.zeros((2, 3, 4))
    >>> y.shape
    (2, 3, 4)
    >>> y.shape = (3, 8)
    >>> y
    array([[ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.],
           [ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.],
           [ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]])
    >>> y.shape = (3, 6)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    ValueError: cannot reshape array of size 24 into shape (3,6)
    >>> np.zeros((4,2))[::2].shape = (-1,)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    AttributeError: Incompatible shape for in-place modification. Use
    `.reshape()` to make a copy with the desired shape.

    See Also
    --------
    numpy.shape : Equivalent getter function.
    numpy.reshape : Function similar to setting ``shape``.
    ndarray.reshape : Method similar to setting ``shape``.

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('size',
    """
    Number of elements in the array.

    Equal to ``np.prod(a.shape)``, i.e., the product of the array's
    dimensions.

    Notes
    -----
    `a.size` returns a standard arbitrary precision Python integer. This
    may not be the case with other methods of obtaining the same value
    (like the suggested ``np.prod(a.shape)``, which returns an instance
    of ``np.int_``), and may be relevant if the value is used further in
    calculations that may overflow a fixed size integer type.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.zeros((3, 5, 2), dtype=np.complex128)
    >>> x.size
    30
    >>> np.prod(x.shape)
    30

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('strides',
    """
    Tuple of bytes to step in each dimension when traversing an array.

    The byte offset of element ``(i[0], i[1], ..., i[n])`` in an array `a`
    is::

        offset = sum(np.array(i) * a.strides)

    A more detailed explanation of strides can be found in
    :ref:`arrays.ndarray`.

    .. warning::

        Setting ``arr.strides`` is discouraged and may be deprecated in the
        future.  `numpy.lib.stride_tricks.as_strided` should be preferred
        to create a new view of the same data in a safer way.

    Notes
    -----
    Imagine an array of 32-bit integers (each 4 bytes)::

      x = np.array([[0, 1, 2, 3, 4],
                    [5, 6, 7, 8, 9]], dtype=np.int32)

    This array is stored in memory as 40 bytes, one after the other
    (known as a contiguous block of memory).  The strides of an array tell
    us how many bytes we have to skip in memory to move to the next position
    along a certain axis.  For example, we have to skip 4 bytes (1 value) to
    move to the next column, but 20 bytes (5 values) to get to the same
    position in the next row.  As such, the strides for the array `x` will be
    ``(20, 4)``.

    See Also
    --------
    numpy.lib.stride_tricks.as_strided

    Examples
    --------
    >>> import numpy as np
    >>> y = np.reshape(np.arange(2 * 3 * 4, dtype=np.int32), (2, 3, 4))
    >>> y
    array([[[ 0,  1,  2,  3],
            [ 4,  5,  6,  7],
            [ 8,  9, 10, 11]],
           [[12, 13, 14, 15],
            [16, 17, 18, 19],
            [20, 21, 22, 23]]], dtype=np.int32)
    >>> y.strides
    (48, 16, 4)
    >>> y[1, 1, 1]
    np.int32(17)
    >>> offset = sum(y.strides * np.array((1, 1, 1)))
    >>> offset // y.itemsize
    np.int64(17)

    >>> x = np.reshape(np.arange(5*6*7*8, dtype=np.int32), (5, 6, 7, 8))
    >>> x = x.transpose(2, 3, 1, 0)
    >>> x.strides
    (32, 4, 224, 1344)
    >>> i = np.array([3, 5, 2, 2], dtype=np.int32)
    >>> offset = sum(i * x.strides)
    >>> x[3, 5, 2, 2]
    np.int32(813)
    >>> offset // x.itemsize
    np.int64(813)

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('T',
    """
    View of the transposed array.

    Same as ``self.transpose()``.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> a
    array([[1, 2],
           [3, 4]])
    >>> a.T
    array([[1, 3],
           [2, 4]])

    >>> a = np.array([1, 2, 3, 4])
    >>> a
    array([1, 2, 3, 4])
    >>> a.T
    array([1, 2, 3, 4])

    See Also
    --------
    transpose

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('mT',
    """
    View of the matrix transposed array.

    The matrix transpose is the transpose of the last two dimensions, even
    if the array is of higher dimension.

    .. versionadded:: 2.0

    Raises
    ------
    ValueError
        If the array is of dimension less than 2.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> a
    array([[1, 2],
           [3, 4]])
    >>> a.mT
    array([[1, 3],
           [2, 4]])

    >>> a = np.arange(8).reshape((2, 2, 2))
    >>> a
    array([[[0, 1],
            [2, 3]],
    <BLANKLINE>
           [[4, 5],
            [6, 7]]])
    >>> a.mT
    array([[[0, 2],
            [1, 3]],
    <BLANKLINE>
           [[4, 6],
            [5, 7]]])

    """))
##############################################################################
#
# ndarray methods
#
##############################################################################


add_newdoc('numpy._core.multiarray', 'ndarray', ('__array__',
    """
    a.__array__([dtype], *, copy=None)

    For ``dtype`` parameter it returns a new reference to self if
    ``dtype`` is not given or it matches array's data type.
    A new array of provided data type is returned if ``dtype``
    is different from the current data type of the array.
    For ``copy`` parameter it returns a new reference to self if
    ``copy=False`` or ``copy=None`` and copying isn't enforced by ``dtype``
    parameter. The method returns a new array for ``copy=True``, regardless of
    ``dtype`` parameter.

    A more detailed explanation of the ``__array__`` interface
    can be found in :ref:`dunder_array.interface`.

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('__array_finalize__',
    """
    a.__array_finalize__(obj, /)

    Present so subclasses can call super. Does nothing.

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('__array_wrap__',
    """
    a.__array_wrap__(array[, context], /)

    Returns a view of `array` with the same type as self.

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('__copy__',
    """
    a.__copy__()

    Used if :func:`copy.copy` is called on an array. Returns a copy of the array.

    Equivalent to ``a.copy(order='K')``.

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('__class_getitem__',
    """
    a.__class_getitem__(item, /)

    Return a parametrized wrapper around the `~numpy.ndarray` type.

    .. versionadded:: 1.22

    Returns
    -------
    alias : types.GenericAlias
        A parametrized `~numpy.ndarray` type.

    Examples
    --------
    >>> from typing import Any
    >>> import numpy as np

    >>> np.ndarray[Any, np.dtype[np.uint8]]
    numpy.ndarray[typing.Any, numpy.dtype[numpy.uint8]]

    See Also
    --------
    :pep:`585` : Type hinting generics in standard collections.
    numpy.typing.NDArray : An ndarray alias :term:`generic <generic type>`
                        w.r.t. its `dtype.type <numpy.dtype.type>`.

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('__deepcopy__',
    """
    a.__deepcopy__(memo, /)

    Used if :func:`copy.deepcopy` is called on an array.

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('__reduce__',
    """
    a.__reduce__()

    For pickling.

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('__setstate__',
    """
    a.__setstate__(state, /)

    For unpickling.

    The `state` argument must be a sequence that contains the following
    elements:

    Parameters
    ----------
    version : int
        optional pickle version. If omitted defaults to 0.
    shape : tuple
    dtype : data-type
    isFortran : bool
    rawdata : string or list
        a binary string with the data (or a list if 'a' is an object array)

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('all',
    """
    a.all(axis=None, out=None, keepdims=False, *, where=True)

    Returns True if all elements evaluate to True.

    Refer to `numpy.all` for full documentation.

    See Also
    --------
    numpy.all : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('any',
    """
    a.any(axis=None, out=None, keepdims=False, *, where=True)

    Returns True if any of the elements of `a` evaluate to True.

    Refer to `numpy.any` for full documentation.

    See Also
    --------
    numpy.any : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('argmax',
    """
    a.argmax(axis=None, out=None, *, keepdims=False)

    Return indices of the maximum values along the given axis.

    Refer to `numpy.argmax` for full documentation.

    See Also
    --------
    numpy.argmax : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('argmin',
    """
    a.argmin(axis=None, out=None, *, keepdims=False)

    Return indices of the minimum values along the given axis.

    Refer to `numpy.argmin` for detailed documentation.

    See Also
    --------
    numpy.argmin : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('argsort',
    """
    a.argsort(axis=-1, kind=None, order=None)

    Returns the indices that would sort this array.

    Refer to `numpy.argsort` for full documentation.

    See Also
    --------
    numpy.argsort : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('argpartition',
    """
    a.argpartition(kth, axis=-1, kind='introselect', order=None)

    Returns the indices that would partition this array.

    Refer to `numpy.argpartition` for full documentation.

    See Also
    --------
    numpy.argpartition : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('astype',
    """
    a.astype(dtype, order='K', casting='unsafe', subok=True, copy=True)

    Copy of the array, cast to a specified type.

    Parameters
    ----------
    dtype : str or dtype
        Typecode or data-type to which the array is cast.
    order : {'C', 'F', 'A', 'K'}, optional
        Controls the memory layout order of the result.
        'C' means C order, 'F' means Fortran order, 'A'
        means 'F' order if all the arrays are Fortran contiguous,
        'C' order otherwise, and 'K' means as close to the
        order the array elements appear in memory as possible.
        Default is 'K'.
    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        Controls what kind of data casting may occur. Defaults to 'unsafe'
        for backwards compatibility.

        * 'no' means the data types should not be cast at all.
        * 'equiv' means only byte-order changes are allowed.
        * 'safe' means only casts which can preserve values are allowed.
        * 'same_kind' means only safe casts or casts within a kind,
          like float64 to float32, are allowed.
        * 'unsafe' means any data conversions may be done.
    subok : bool, optional
        If True, then sub-classes will be passed-through (default), otherwise
        the returned array will be forced to be a base-class array.
    copy : bool, optional
        By default, astype always returns a newly allocated array. If this
        is set to false, and the `dtype`, `order`, and `subok`
        requirements are satisfied, the input array is returned instead
        of a copy.

    Returns
    -------
    arr_t : ndarray
        Unless `copy` is False and the other conditions for returning the input
        array are satisfied (see description for `copy` input parameter), `arr_t`
        is a new array of the same shape as the input array, with dtype, order
        given by `dtype`, `order`.

    Raises
    ------
    ComplexWarning
        When casting from complex to float or int. To avoid this,
        one should use ``a.real.astype(t)``.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([1, 2, 2.5])
    >>> x
    array([1. ,  2. ,  2.5])

    >>> x.astype(int)
    array([1, 2, 2])

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('byteswap',
    """
    a.byteswap(inplace=False)

    Swap the bytes of the array elements

    Toggle between low-endian and big-endian data representation by
    returning a byteswapped array, optionally swapped in-place.
    Arrays of byte-strings are not swapped. The real and imaginary
    parts of a complex number are swapped individually.

    Parameters
    ----------
    inplace : bool, optional
        If ``True``, swap bytes in-place, default is ``False``.

    Returns
    -------
    out : ndarray
        The byteswapped array. If `inplace` is ``True``, this is
        a view to self.

    Examples
    --------
    >>> import numpy as np
    >>> A = np.array([1, 256, 8755], dtype=np.int16)
    >>> list(map(hex, A))
    ['0x1', '0x100', '0x2233']
    >>> A.byteswap(inplace=True)
    array([  256,     1, 13090], dtype=int16)
    >>> list(map(hex, A))
    ['0x100', '0x1', '0x3322']

    Arrays of byte-strings are not swapped

    >>> A = np.array([b'ceg', b'fac'])
    >>> A.byteswap()
    array([b'ceg', b'fac'], dtype='|S3')

    ``A.view(A.dtype.newbyteorder()).byteswap()`` produces an array with
    the same values but different representation in memory

    >>> A = np.array([1, 2, 3],dtype=np.int64)
    >>> A.view(np.uint8)
    array([1, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0,
           0, 0], dtype=uint8)
    >>> A.view(A.dtype.newbyteorder()).byteswap(inplace=True)
    array([1, 2, 3], dtype='>i8')
    >>> A.view(np.uint8)
    array([0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0,
           0, 3], dtype=uint8)

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('choose',
    """
    a.choose(choices, out=None, mode='raise')

    Use an index array to construct a new array from a set of choices.

    Refer to `numpy.choose` for full documentation.

    See Also
    --------
    numpy.choose : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('clip',
    """
    a.clip(min=None, max=None, out=None, **kwargs)

    Return an array whose values are limited to ``[min, max]``.
    One of max or min must be given.

    Refer to `numpy.clip` for full documentation.

    See Also
    --------
    numpy.clip : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('compress',
    """
    a.compress(condition, axis=None, out=None)

    Return selected slices of this array along given axis.

    Refer to `numpy.compress` for full documentation.

    See Also
    --------
    numpy.compress : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('conj',
    """
    a.conj()

    Complex-conjugate all elements.

    Refer to `numpy.conjugate` for full documentation.

    See Also
    --------
    numpy.conjugate : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('conjugate',
    """
    a.conjugate()

    Return the complex conjugate, element-wise.

    Refer to `numpy.conjugate` for full documentation.

    See Also
    --------
    numpy.conjugate : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('copy',
    """
    a.copy(order='C')

    Return a copy of the array.

    Parameters
    ----------
    order : {'C', 'F', 'A', 'K'}, optional
        Controls the memory layout of the copy. 'C' means C-order,
        'F' means F-order, 'A' means 'F' if `a` is Fortran contiguous,
        'C' otherwise. 'K' means match the layout of `a` as closely
        as possible. (Note that this function and :func:`numpy.copy` are very
        similar but have different default values for their order=
        arguments, and this function always passes sub-classes through.)

    See also
    --------
    numpy.copy : Similar function with different default behavior
    numpy.copyto

    Notes
    -----
    This function is the preferred method for creating an array copy.  The
    function :func:`numpy.copy` is similar, but it defaults to using order 'K',
    and will not pass sub-classes through by default.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([[1,2,3],[4,5,6]], order='F')

    >>> y = x.copy()

    >>> x.fill(0)

    >>> x
    array([[0, 0, 0],
           [0, 0, 0]])

    >>> y
    array([[1, 2, 3],
           [4, 5, 6]])

    >>> y.flags['C_CONTIGUOUS']
    True

    For arrays containing Python objects (e.g. dtype=object),
    the copy is a shallow one. The new array will contain the
    same object which may lead to surprises if that object can
    be modified (is mutable):

    >>> a = np.array([1, 'm', [2, 3, 4]], dtype=object)
    >>> b = a.copy()
    >>> b[2][0] = 10
    >>> a
    array([1, 'm', list([10, 3, 4])], dtype=object)

    To ensure all elements within an ``object`` array are copied,
    use `copy.deepcopy`:

    >>> import copy
    >>> a = np.array([1, 'm', [2, 3, 4]], dtype=object)
    >>> c = copy.deepcopy(a)
    >>> c[2][0] = 10
    >>> c
    array([1, 'm', list([10, 3, 4])], dtype=object)
    >>> a
    array([1, 'm', list([2, 3, 4])], dtype=object)

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('cumprod',
    """
    a.cumprod(axis=None, dtype=None, out=None)

    Return the cumulative product of the elements along the given axis.

    Refer to `numpy.cumprod` for full documentation.

    See Also
    --------
    numpy.cumprod : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('cumsum',
    """
    a.cumsum(axis=None, dtype=None, out=None)

    Return the cumulative sum of the elements along the given axis.

    Refer to `numpy.cumsum` for full documentation.

    See Also
    --------
    numpy.cumsum : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('diagonal',
    """
    a.diagonal(offset=0, axis1=0, axis2=1)

    Return specified diagonals. In NumPy 1.9 the returned array is a
    read-only view instead of a copy as in previous NumPy versions.  In
    a future version the read-only restriction will be removed.

    Refer to :func:`numpy.diagonal` for full documentation.

    See Also
    --------
    numpy.diagonal : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('dot'))


add_newdoc('numpy._core.multiarray', 'ndarray', ('dump',
    """
    a.dump(file)

    Dump a pickle of the array to the specified file.
    The array can be read back with pickle.load or numpy.load.

    Parameters
    ----------
    file : str or Path
        A string naming the dump file.

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('dumps',
    """
    a.dumps()

    Returns the pickle of the array as a string.
    pickle.loads will convert the string back to an array.

    Parameters
    ----------
    None

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('fill',
    """
    a.fill(value)

    Fill the array with a scalar value.

    Parameters
    ----------
    value : scalar
        All elements of `a` will be assigned this value.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([1, 2])
    >>> a.fill(0)
    >>> a
    array([0, 0])
    >>> a = np.empty(2)
    >>> a.fill(1)
    >>> a
    array([1.,  1.])

    Fill expects a scalar value and always behaves the same as assigning
    to a single array element.  The following is a rare example where this
    distinction is important:

    >>> a = np.array([None, None], dtype=object)
    >>> a[0] = np.array(3)
    >>> a
    array([array(3), None], dtype=object)
    >>> a.fill(np.array(3))
    >>> a
    array([array(3), array(3)], dtype=object)

    Where other forms of assignments will unpack the array being assigned:

    >>> a[...] = np.array(3)
    >>> a
    array([3, 3], dtype=object)

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('flatten',
    """
    a.flatten(order='C')

    Return a copy of the array collapsed into one dimension.

    Parameters
    ----------
    order : {'C', 'F', 'A', 'K'}, optional
        'C' means to flatten in row-major (C-style) order.
        'F' means to flatten in column-major (Fortran-
        style) order. 'A' means to flatten in column-major
        order if `a` is Fortran *contiguous* in memory,
        row-major order otherwise. 'K' means to flatten
        `a` in the order the elements occur in memory.
        The default is 'C'.

    Returns
    -------
    y : ndarray
        A copy of the input array, flattened to one dimension.

    See Also
    --------
    ravel : Return a flattened array.
    flat : A 1-D flat iterator over the array.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1,2], [3,4]])
    >>> a.flatten()
    array([1, 2, 3, 4])
    >>> a.flatten('F')
    array([1, 3, 2, 4])

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('getfield',
    """
    a.getfield(dtype, offset=0)

    Returns a field of the given array as a certain type.

    A field is a view of the array data with a given data-type. The values in
    the view are determined by the given type and the offset into the current
    array in bytes. The offset needs to be such that the view dtype fits in the
    array dtype; for example an array of dtype complex128 has 16-byte elements.
    If taking a view with a 32-bit integer (4 bytes), the offset needs to be
    between 0 and 12 bytes.

    Parameters
    ----------
    dtype : str or dtype
        The data type of the view. The dtype size of the view can not be larger
        than that of the array itself.
    offset : int
        Number of bytes to skip before beginning the element view.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.diag([1.+1.j]*2)
    >>> x[1, 1] = 2 + 4.j
    >>> x
    array([[1.+1.j,  0.+0.j],
           [0.+0.j,  2.+4.j]])
    >>> x.getfield(np.float64)
    array([[1.,  0.],
           [0.,  2.]])

    By choosing an offset of 8 bytes we can select the complex part of the
    array for our view:

    >>> x.getfield(np.float64, offset=8)
    array([[1.,  0.],
           [0.,  4.]])

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('item',
    """
    a.item(*args)

    Copy an element of an array to a standard Python scalar and return it.

    Parameters
    ----------
    \\*args : Arguments (variable number and type)

        * none: in this case, the method only works for arrays
          with one element (`a.size == 1`), which element is
          copied into a standard Python scalar object and returned.

        * int_type: this argument is interpreted as a flat index into
          the array, specifying which element to copy and return.

        * tuple of int_types: functions as does a single int_type argument,
          except that the argument is interpreted as an nd-index into the
          array.

    Returns
    -------
    z : Standard Python scalar object
        A copy of the specified element of the array as a suitable
        Python scalar

    Notes
    -----
    When the data type of `a` is longdouble or clongdouble, item() returns
    a scalar array object because there is no available Python scalar that
    would not lose information. Void arrays return a buffer object for item(),
    unless fields are defined, in which case a tuple is returned.

    `item` is very similar to a[args], except, instead of an array scalar,
    a standard Python scalar is returned. This can be useful for speeding up
    access to elements of the array and doing arithmetic on elements of the
    array using Python's optimized math.

    Examples
    --------
    >>> import numpy as np
    >>> np.random.seed(123)
    >>> x = np.random.randint(9, size=(3, 3))
    >>> x
    array([[2, 2, 6],
           [1, 3, 6],
           [1, 0, 1]])
    >>> x.item(3)
    1
    >>> x.item(7)
    0
    >>> x.item((0, 1))
    2
    >>> x.item((2, 2))
    1

    For an array with object dtype, elements are returned as-is.

    >>> a = np.array([np.int64(1)], dtype=object)
    >>> a.item() #return np.int64
    np.int64(1)

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('max',
    """
    a.max(axis=None, out=None, keepdims=False, initial=<no value>, where=True)

    Return the maximum along a given axis.

    Refer to `numpy.amax` for full documentation.

    See Also
    --------
    numpy.amax : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('mean',
    """
    a.mean(axis=None, dtype=None, out=None, keepdims=False, *, where=True)

    Returns the average of the array elements along given axis.

    Refer to `numpy.mean` for full documentation.

    See Also
    --------
    numpy.mean : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('min',
    """
    a.min(axis=None, out=None, keepdims=False, initial=<no value>, where=True)

    Return the minimum along a given axis.

    Refer to `numpy.amin` for full documentation.

    See Also
    --------
    numpy.amin : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('nonzero',
    """
    a.nonzero()

    Return the indices of the elements that are non-zero.

    Refer to `numpy.nonzero` for full documentation.

    See Also
    --------
    numpy.nonzero : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('prod',
    """
    a.prod(axis=None, dtype=None, out=None, keepdims=False,
        initial=1, where=True)

    Return the product of the array elements over the given axis

    Refer to `numpy.prod` for full documentation.

    See Also
    --------
    numpy.prod : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('put',
    """
    a.put(indices, values, mode='raise')

    Set ``a.flat[n] = values[n]`` for all `n` in indices.

    Refer to `numpy.put` for full documentation.

    See Also
    --------
    numpy.put : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('ravel',
    """
    a.ravel([order])

    Return a flattened array.

    Refer to `numpy.ravel` for full documentation.

    See Also
    --------
    numpy.ravel : equivalent function

    ndarray.flat : a flat iterator on the array.

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('repeat',
    """
    a.repeat(repeats, axis=None)

    Repeat elements of an array.

    Refer to `numpy.repeat` for full documentation.

    See Also
    --------
    numpy.repeat : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('reshape',
    """
    a.reshape(shape, /, *, order='C', copy=None)

    Returns an array containing the same data with a new shape.

    Refer to `numpy.reshape` for full documentation.

    See Also
    --------
    numpy.reshape : equivalent function

    Notes
    -----
    Unlike the free function `numpy.reshape`, this method on `ndarray` allows
    the elements of the shape parameter to be passed in as separate arguments.
    For example, ``a.reshape(10, 11)`` is equivalent to
    ``a.reshape((10, 11))``.

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('resize',
    """
    a.resize(new_shape, refcheck=True)

    Change shape and size of array in-place.

    Parameters
    ----------
    new_shape : tuple of ints, or `n` ints
        Shape of resized array.
    refcheck : bool, optional
        If False, reference count will not be checked. Default is True.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If `a` does not own its own data or references or views to it exist,
        and the data memory must be changed.
        PyPy only: will always raise if the data memory must be changed, since
        there is no reliable way to determine if references or views to it
        exist.

    SystemError
        If the `order` keyword argument is specified. This behaviour is a
        bug in NumPy.

    See Also
    --------
    resize : Return a new array with the specified shape.

    Notes
    -----
    This reallocates space for the data area if necessary.

    Only contiguous arrays (data elements consecutive in memory) can be
    resized.

    The purpose of the reference count check is to make sure you
    do not use this array as a buffer for another Python object and then
    reallocate the memory. However, reference counts can increase in
    other ways so if you are sure that you have not shared the memory
    for this array with another Python object, then you may safely set
    `refcheck` to False.

    Examples
    --------
    Shrinking an array: array is flattened (in the order that the data are
    stored in memory), resized, and reshaped:

    >>> import numpy as np

    >>> a = np.array([[0, 1], [2, 3]], order='C')
    >>> a.resize((2, 1))
    >>> a
    array([[0],
           [1]])

    >>> a = np.array([[0, 1], [2, 3]], order='F')
    >>> a.resize((2, 1))
    >>> a
    array([[0],
           [2]])

    Enlarging an array: as above, but missing entries are filled with zeros:

    >>> b = np.array([[0, 1], [2, 3]])
    >>> b.resize(2, 3) # new_shape parameter doesn't have to be a tuple
    >>> b
    array([[0, 1, 2],
           [3, 0, 0]])

    Referencing an array prevents resizing...

    >>> c = a
    >>> a.resize((1, 1))
    Traceback (most recent call last):
    ...
    ValueError: cannot resize an array that references or is referenced ...

    Unless `refcheck` is False:

    >>> a.resize((1, 1), refcheck=False)
    >>> a
    array([[0]])
    >>> c
    array([[0]])

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('round',
    """
    a.round(decimals=0, out=None)

    Return `a` with each element rounded to the given number of decimals.

    Refer to `numpy.around` for full documentation.

    See Also
    --------
    numpy.around : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('searchsorted',
    """
    a.searchsorted(v, side='left', sorter=None)

    Find indices where elements of v should be inserted in a to maintain order.

    For full documentation, see `numpy.searchsorted`

    See Also
    --------
    numpy.searchsorted : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('setfield',
    """
    a.setfield(val, dtype, offset=0)

    Put a value into a specified place in a field defined by a data-type.

    Place `val` into `a`'s field defined by `dtype` and beginning `offset`
    bytes into the field.

    Parameters
    ----------
    val : object
        Value to be placed in field.
    dtype : dtype object
        Data-type of the field in which to place `val`.
    offset : int, optional
        The number of bytes into the field at which to place `val`.

    Returns
    -------
    None

    See Also
    --------
    getfield

    Examples
    --------
    >>> import numpy as np
    >>> x = np.eye(3)
    >>> x.getfield(np.float64)
    array([[1.,  0.,  0.],
           [0.,  1.,  0.],
           [0.,  0.,  1.]])
    >>> x.setfield(3, np.int32)
    >>> x.getfield(np.int32)
    array([[3, 3, 3],
           [3, 3, 3],
           [3, 3, 3]], dtype=int32)
    >>> x
    array([[1.0e+000, 1.5e-323, 1.5e-323],
           [1.5e-323, 1.0e+000, 1.5e-323],
           [1.5e-323, 1.5e-323, 1.0e+000]])
    >>> x.setfield(np.eye(3), np.int32)
    >>> x
    array([[1.,  0.,  0.],
           [0.,  1.,  0.],
           [0.,  0.,  1.]])

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('setflags',
    """
    a.setflags(write=None, align=None, uic=None)

    Set array flags WRITEABLE, ALIGNED, WRITEBACKIFCOPY,
    respectively.

    These Boolean-valued flags affect how numpy interprets the memory
    area used by `a` (see Notes below). The ALIGNED flag can only
    be set to True if the data is actually aligned according to the type.
    The WRITEBACKIFCOPY flag can never be set
    to True. The flag WRITEABLE can only be set to True if the array owns its
    own memory, or the ultimate owner of the memory exposes a writeable buffer
    interface, or is a string. (The exception for string is made so that
    unpickling can be done without copying memory.)

    Parameters
    ----------
    write : bool, optional
        Describes whether or not `a` can be written to.
    align : bool, optional
        Describes whether or not `a` is aligned properly for its type.
    uic : bool, optional
        Describes whether or not `a` is a copy of another "base" array.

    Notes
    -----
    Array flags provide information about how the memory area used
    for the array is to be interpreted. There are 7 Boolean flags
    in use, only three of which can be changed by the user:
    WRITEBACKIFCOPY, WRITEABLE, and ALIGNED.

    WRITEABLE (W) the data area can be written to;

    ALIGNED (A) the data and strides are aligned appropriately for the hardware
    (as determined by the compiler);

    WRITEBACKIFCOPY (X) this array is a copy of some other array (referenced
    by .base). When the C-API function PyArray_ResolveWritebackIfCopy is
    called, the base array will be updated with the contents of this array.

    All flags can be accessed using the single (upper case) letter as well
    as the full name.

    Examples
    --------
    >>> import numpy as np
    >>> y = np.array([[3, 1, 7],
    ...               [2, 0, 0],
    ...               [8, 5, 9]])
    >>> y
    array([[3, 1, 7],
           [2, 0, 0],
           [8, 5, 9]])
    >>> y.flags
      C_CONTIGUOUS : True
      F_CONTIGUOUS : False
      OWNDATA : True
      WRITEABLE : True
      ALIGNED : True
      WRITEBACKIFCOPY : False
    >>> y.setflags(write=0, align=0)
    >>> y.flags
      C_CONTIGUOUS : True
      F_CONTIGUOUS : False
      OWNDATA : True
      WRITEABLE : False
      ALIGNED : False
      WRITEBACKIFCOPY : False
    >>> y.setflags(uic=1)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    ValueError: cannot set WRITEBACKIFCOPY flag to True

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('sort',
    """
    a.sort(axis=-1, kind=None, order=None)

    Sort an array in-place. Refer to `numpy.sort` for full documentation.

    Parameters
    ----------
    axis : int, optional
        Axis along which to sort. Default is -1, which means sort along the
        last axis.
    kind : {'quicksort', 'mergesort', 'heapsort', 'stable'}, optional
        Sorting algorithm. The default is 'quicksort'. Note that both 'stable'
        and 'mergesort' use timsort under the covers and, in general, the
        actual implementation will vary with datatype. The 'mergesort' option
        is retained for backwards compatibility.
    order : str or list of str, optional
        When `a` is an array with fields defined, this argument specifies
        which fields to compare first, second, etc.  A single field can
        be specified as a string, and not all fields need be specified,
        but unspecified fields will still be used, in the order in which
        they come up in the dtype, to break ties.

    See Also
    --------
    numpy.sort : Return a sorted copy of an array.
    numpy.argsort : Indirect sort.
    numpy.lexsort : Indirect stable sort on multiple keys.
    numpy.searchsorted : Find elements in sorted array.
    numpy.partition: Partial sort.

    Notes
    -----
    See `numpy.sort` for notes on the different sorting algorithms.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1,4], [3,1]])
    >>> a.sort(axis=1)
    >>> a
    array([[1, 4],
           [1, 3]])
    >>> a.sort(axis=0)
    >>> a
    array([[1, 3],
           [1, 4]])

    Use the `order` keyword to specify a field to use when sorting a
    structured array:

    >>> a = np.array([('a', 2), ('c', 1)], dtype=[('x', 'S1'), ('y', int)])
    >>> a.sort(order='y')
    >>> a
    array([(b'c', 1), (b'a', 2)],
          dtype=[('x', 'S1'), ('y', '<i8')])

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('partition',
    """
    a.partition(kth, axis=-1, kind='introselect', order=None)

    Partially sorts the elements in the array in such a way that the value of
    the element in k-th position is in the position it would be in a sorted
    array. In the output array, all elements smaller than the k-th element
    are located to the left of this element and all equal or greater are
    located to its right. The ordering of the elements in the two partitions
    on the either side of the k-th element in the output array is undefined.

    Parameters
    ----------
    kth : int or sequence of ints
        Element index to partition by. The kth element value will be in its
        final sorted position and all smaller elements will be moved before it
        and all equal or greater elements behind it.
        The order of all elements in the partitions is undefined.
        If provided with a sequence of kth it will partition all elements
        indexed by kth of them into their sorted position at once.

        .. deprecated:: 1.22.0
            Passing booleans as index is deprecated.
    axis : int, optional
        Axis along which to sort. Default is -1, which means sort along the
        last axis.
    kind : {'introselect'}, optional
        Selection algorithm. Default is 'introselect'.
    order : str or list of str, optional
        When `a` is an array with fields defined, this argument specifies
        which fields to compare first, second, etc. A single field can
        be specified as a string, and not all fields need to be specified,
        but unspecified fields will still be used, in the order in which
        they come up in the dtype, to break ties.

    See Also
    --------
    numpy.partition : Return a partitioned copy of an array.
    argpartition : Indirect partition.
    sort : Full sort.

    Notes
    -----
    See ``np.partition`` for notes on the different algorithms.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([3, 4, 2, 1])
    >>> a.partition(3)
    >>> a
    array([2, 1, 3, 4]) # may vary

    >>> a.partition((1, 3))
    >>> a
    array([1, 2, 3, 4])
    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('squeeze',
    """
    a.squeeze(axis=None)

    Remove axes of length one from `a`.

    Refer to `numpy.squeeze` for full documentation.

    See Also
    --------
    numpy.squeeze : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('std',
    """
    a.std(axis=None, dtype=None, out=None, ddof=0, keepdims=False, *, where=True)

    Returns the standard deviation of the array elements along given axis.

    Refer to `numpy.std` for full documentation.

    See Also
    --------
    numpy.std : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('sum',
    """
    a.sum(axis=None, dtype=None, out=None, keepdims=False, initial=0, where=True)

    Return the sum of the array elements over the given axis.

    Refer to `numpy.sum` for full documentation.

    See Also
    --------
    numpy.sum : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('swapaxes',
    """
    a.swapaxes(axis1, axis2)

    Return a view of the array with `axis1` and `axis2` interchanged.

    Refer to `numpy.swapaxes` for full documentation.

    See Also
    --------
    numpy.swapaxes : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('take',
    """
    a.take(indices, axis=None, out=None, mode='raise')

    Return an array formed from the elements of `a` at the given indices.

    Refer to `numpy.take` for full documentation.

    See Also
    --------
    numpy.take : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('tofile',
    """
    a.tofile(fid, sep="", format="%s")

    Write array to a file as text or binary (default).

    Data is always written in 'C' order, independent of the order of `a`.
    The data produced by this method can be recovered using the function
    fromfile().

    Parameters
    ----------
    fid : file or str or Path
        An open file object, or a string containing a filename.
    sep : str
        Separator between array items for text output.
        If "" (empty), a binary file is written, equivalent to
        ``file.write(a.tobytes())``.
    format : str
        Format string for text file output.
        Each entry in the array is formatted to text by first converting
        it to the closest Python type, and then using "format" % item.

    Notes
    -----
    This is a convenience function for quick storage of array data.
    Information on endianness and precision is lost, so this method is not a
    good choice for files intended to archive data or transport data between
    machines with different endianness. Some of these problems can be overcome
    by outputting the data as text files, at the expense of speed and file
    size.

    When fid is a file object, array contents are directly written to the
    file, bypassing the file object's ``write`` method. As a result, tofile
    cannot be used with files objects supporting compression (e.g., GzipFile)
    or file-like objects that do not support ``fileno()`` (e.g., BytesIO).

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('tolist',
    """
    a.tolist()

    Return the array as an ``a.ndim``-levels deep nested list of Python scalars.

    Return a copy of the array data as a (nested) Python list.
    Data items are converted to the nearest compatible builtin Python type, via
    the `~numpy.ndarray.item` function.

    If ``a.ndim`` is 0, then since the depth of the nested list is 0, it will
    not be a list at all, but a simple Python scalar.

    Parameters
    ----------
    none

    Returns
    -------
    y : object, or list of object, or list of list of object, or ...
        The possibly nested list of array elements.

    Notes
    -----
    The array may be recreated via ``a = np.array(a.tolist())``, although this
    may sometimes lose precision.

    Examples
    --------
    For a 1D array, ``a.tolist()`` is almost the same as ``list(a)``,
    except that ``tolist`` changes numpy scalars to Python scalars:

    >>> import numpy as np
    >>> a = np.uint32([1, 2])
    >>> a_list = list(a)
    >>> a_list
    [np.uint32(1), np.uint32(2)]
    >>> type(a_list[0])
    <class 'numpy.uint32'>
    >>> a_tolist = a.tolist()
    >>> a_tolist
    [1, 2]
    >>> type(a_tolist[0])
    <class 'int'>

    Additionally, for a 2D array, ``tolist`` applies recursively:

    >>> a = np.array([[1, 2], [3, 4]])
    >>> list(a)
    [array([1, 2]), array([3, 4])]
    >>> a.tolist()
    [[1, 2], [3, 4]]

    The base case for this recursion is a 0D array:

    >>> a = np.array(1)
    >>> list(a)
    Traceback (most recent call last):
      ...
    TypeError: iteration over a 0-d array
    >>> a.tolist()
    1
    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('tobytes', """
    a.tobytes(order='C')

    Construct Python bytes containing the raw data bytes in the array.

    Constructs Python bytes showing a copy of the raw contents of
    data memory. The bytes object is produced in C-order by default.
    This behavior is controlled by the ``order`` parameter.

    Parameters
    ----------
    order : {'C', 'F', 'A'}, optional
        Controls the memory layout of the bytes object. 'C' means C-order,
        'F' means F-order, 'A' (short for *Any*) means 'F' if `a` is
        Fortran contiguous, 'C' otherwise. Default is 'C'.

    Returns
    -------
    s : bytes
        Python bytes exhibiting a copy of `a`'s raw data.

    See also
    --------
    frombuffer
        Inverse of this operation, construct a 1-dimensional array from Python
        bytes.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([[0, 1], [2, 3]], dtype='<u2')
    >>> x.tobytes()
    b'\\x00\\x00\\x01\\x00\\x02\\x00\\x03\\x00'
    >>> x.tobytes('C') == x.tobytes()
    True
    >>> x.tobytes('F')
    b'\\x00\\x00\\x02\\x00\\x01\\x00\\x03\\x00'

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('trace',
    """
    a.trace(offset=0, axis1=0, axis2=1, dtype=None, out=None)

    Return the sum along diagonals of the array.

    Refer to `numpy.trace` for full documentation.

    See Also
    --------
    numpy.trace : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('transpose',
    """
    a.transpose(*axes)

    Returns a view of the array with axes transposed.

    Refer to `numpy.transpose` for full documentation.

    Parameters
    ----------
    axes : None, tuple of ints, or `n` ints

     * None or no argument: reverses the order of the axes.

     * tuple of ints: `i` in the `j`-th place in the tuple means that the
       array's `i`-th axis becomes the transposed array's `j`-th axis.

     * `n` ints: same as an n-tuple of the same ints (this form is
       intended simply as a "convenience" alternative to the tuple form).

    Returns
    -------
    p : ndarray
        View of the array with its axes suitably permuted.

    See Also
    --------
    transpose : Equivalent function.
    ndarray.T : Array property returning the array transposed.
    ndarray.reshape : Give a new shape to an array without changing its data.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> a
    array([[1, 2],
           [3, 4]])
    >>> a.transpose()
    array([[1, 3],
           [2, 4]])
    >>> a.transpose((1, 0))
    array([[1, 3],
           [2, 4]])
    >>> a.transpose(1, 0)
    array([[1, 3],
           [2, 4]])

    >>> a = np.array([1, 2, 3, 4])
    >>> a
    array([1, 2, 3, 4])
    >>> a.transpose()
    array([1, 2, 3, 4])

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('var',
    """
    a.var(axis=None, dtype=None, out=None, ddof=0, keepdims=False, *, where=True)

    Returns the variance of the array elements, along given axis.

    Refer to `numpy.var` for full documentation.

    See Also
    --------
    numpy.var : equivalent function

    """))


add_newdoc('numpy._core.multiarray', 'ndarray', ('view',
    """
    a.view([dtype][, type])

    New view of array with the same data.

    .. note::
        Passing None for ``dtype`` is different from omitting the parameter,
        since the former invokes ``dtype(None)`` which is an alias for
        ``dtype('float64')``.

    Parameters
    ----------
    dtype : data-type or ndarray sub-class, optional
        Data-type descriptor of the returned view, e.g., float32 or int16.
        Omitting it results in the view having the same data-type as `a`.
        This argument can also be specified as an ndarray sub-class, which
        then specifies the type of the returned object (this is equivalent to
        setting the ``type`` parameter).
    type : Python type, optional
        Type of the returned view, e.g., ndarray or matrix.  Again, omission
        of the parameter results in type preservation.

    Notes
    -----
    ``a.view()`` is used two different ways:

    ``a.view(some_dtype)`` or ``a.view(dtype=some_dtype)`` constructs a view
    of the array's memory with a different data-type.  This can cause a
    reinterpretation of the bytes of memory.

    ``a.view(ndarray_subclass)`` or ``a.view(type=ndarray_subclass)`` just
    returns an instance of `ndarray_subclass` that looks at the same array
    (same shape, dtype, etc.)  This does not cause a reinterpretation of the
    memory.

    For ``a.view(some_dtype)``, if ``some_dtype`` has a different number of
    bytes per entry than the previous dtype (for example, converting a regular
    array to a structured array), then the last axis of ``a`` must be
    contiguous. This axis will be resized in the result.

    .. versionchanged:: 1.23.0
       Only the last axis needs to be contiguous. Previously, the entire array
       had to be C-contiguous.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.array([(-1, 2)], dtype=[('a', np.int8), ('b', np.int8)])

    Viewing array data using a different type and dtype:

    >>> nonneg = np.dtype([("a", np.uint8), ("b", np.uint8)])
    >>> y = x.view(dtype=nonneg, type=np.recarray)
    >>> x["a"]
    array([-1], dtype=int8)
    >>> y.a
    array([255], dtype=uint8)

    Creating a view on a structured array so it can be used in calculations

    >>> x = np.array([(1, 2),(3,4)], dtype=[('a', np.int8), ('b', np.int8)])
    >>> xv = x.view(dtype=np.int8).reshape(-1,2)
    >>> xv
    array([[1, 2],
           [3, 4]], dtype=int8)
    >>> xv.mean(0)
    array([2.,  3.])

    Making changes to the view changes the underlying array

    >>> xv[0,1] = 20
    >>> x
    array([(1, 20), (3,  4)], dtype=[('a', 'i1'), ('b', 'i1')])

    Using a view to convert an array to a recarray:

    >>> z = x.view(np.recarray)
    >>> z.a
    array([1, 3], dtype=int8)

    Views share data:

    >>> x[0] = (9, 10)
    >>> z[0]
    np.record((9, 10), dtype=[('a', 'i1'), ('b', 'i1')])

    Views that change the dtype size (bytes per entry) should normally be
    avoided on arrays defined by slices, transposes, fortran-ordering, etc.:

    >>> x = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int16)
    >>> y = x[:, ::2]
    >>> y
    array([[1, 3],
           [4, 6]], dtype=int16)
    >>> y.view(dtype=[('width', np.int16), ('length', np.int16)])
    Traceback (most recent call last):
        ...
    ValueError: To change to a dtype of a different size, the last axis must be contiguous
    >>> z = y.copy()
    >>> z.view(dtype=[('width', np.int16), ('length', np.int16)])
    array([[(1, 3)],
           [(4, 6)]], dtype=[('width', '<i2'), ('length', '<i2')])

    However, views that change dtype are totally fine for arrays with a
    contiguous last axis, even if the rest of the axes are not C-contiguous:

    >>> x = np.arange(2 * 3 * 4, dtype=np.int8).reshape(2, 3, 4)
    >>> x.transpose(1, 0, 2).view(np.int16)
    array([[[ 256,  770],
            [3340, 3854]],
    <BLANKLINE>
           [[1284, 1798],
            [4368, 4882]],
    <BLANKLINE>
           [[2312, 2826],
            [5396, 5910]]], dtype=int16)

    """))


##############################################################################
#
# umath functions
#
##############################################################################

add_newdoc('numpy._core.umath', 'frompyfunc',
    """
    frompyfunc(func, /, nin, nout, *[, identity])

    Takes an arbitrary Python function and returns a NumPy ufunc.

    Can be used, for example, to add broadcasting to a built-in Python
    function (see Examples section).

    Parameters
    ----------
    func : Python function object
        An arbitrary Python function.
    nin : int
        The number of input arguments.
    nout : int
        The number of objects returned by `func`.
    identity : object, optional
        The value to use for the `~numpy.ufunc.identity` attribute of the resulting
        object. If specified, this is equivalent to setting the underlying
        C ``identity`` field to ``PyUFunc_IdentityValue``.
        If omitted, the identity is set to ``PyUFunc_None``. Note that this is
        _not_ equivalent to setting the identity to ``None``, which implies the
        operation is reorderable.

    Returns
    -------
    out : ufunc
        Returns a NumPy universal function (``ufunc``) object.

    See Also
    --------
    vectorize : Evaluates pyfunc over input arrays using broadcasting rules of numpy.

    Notes
    -----
    The returned ufunc always returns PyObject arrays.

    Examples
    --------
    Use frompyfunc to add broadcasting to the Python function ``oct``:

    >>> import numpy as np
    >>> oct_array = np.frompyfunc(oct, 1, 1)
    >>> oct_array(np.array((10, 30, 100)))
    array(['0o12', '0o36', '0o144'], dtype=object)
    >>> np.array((oct(10), oct(30), oct(100))) # for comparison
    array(['0o12', '0o36', '0o144'], dtype='<U5')

    """)


##############################################################################
#
# compiled_base functions
#
##############################################################################

add_newdoc('numpy._core.multiarray', 'add_docstring',
    """
    add_docstring(obj, docstring)

    Add a docstring to a built-in obj if possible.
    If the obj already has a docstring raise a RuntimeError
    If this routine does not know how to add a docstring to the object
    raise a TypeError
    """)

add_newdoc('numpy._core.umath', '_add_newdoc_ufunc',
    """
    add_ufunc_docstring(ufunc, new_docstring)

    Replace the docstring for a ufunc with new_docstring.
    This method will only work if the current docstring for
    the ufunc is NULL. (At the C level, i.e. when ufunc->doc is NULL.)

    Parameters
    ----------
    ufunc : numpy.ufunc
        A ufunc whose current doc is NULL.
    new_docstring : string
        The new docstring for the ufunc.

    Notes
    -----
    This method allocates memory for new_docstring on
    the heap. Technically this creates a memory leak, since this
    memory will not be reclaimed until the end of the program
    even if the ufunc itself is removed. However this will only
    be a problem if the user is repeatedly creating ufuncs with
    no documentation, adding documentation via add_newdoc_ufunc,
    and then throwing away the ufunc.
    """)

add_newdoc('numpy._core.multiarray', 'get_handler_name',
    """
    get_handler_name(a: ndarray) -> str,None

    Return the name of the memory handler used by `a`. If not provided, return
    the name of the memory handler that will be used to allocate data for the
    next `ndarray` in this context. May return None if `a` does not own its
    memory, in which case you can traverse ``a.base`` for a memory handler.
    """)

add_newdoc('numpy._core.multiarray', 'get_handler_version',
    """
    get_handler_version(a: ndarray) -> int,None

    Return the version of the memory handler used by `a`. If not provided,
    return the version of the memory handler that will be used to allocate data
    for the next `ndarray` in this context. May return None if `a` does not own
    its memory, in which case you can traverse ``a.base`` for a memory handler.
    """)

add_newdoc('numpy._core._multiarray_umath', '_array_converter',
    """
    _array_converter(*array_likes)

    Helper to convert one or more objects to arrays.  Integrates machinery
    to deal with the ``result_type`` and ``__array_wrap__``.

    The reason for this is that e.g. ``result_type`` needs to convert to arrays
    to find the ``dtype``.  But converting to an array before calling
    ``result_type`` would incorrectly "forget" whether it was a Python int,
    float, or complex.
    """)

add_newdoc(
    'numpy._core._multiarray_umath', '_array_converter', ('scalar_input',
    """
    A tuple which indicates for each input whether it was a scalar that
    was coerced to a 0-D array (and was not already an array or something
    converted via a protocol like ``__array__()``).
    """))

add_newdoc('numpy._core._multiarray_umath', '_array_converter', ('as_arrays',
    """
    as_arrays(/, subok=True, pyscalars="convert_if_no_array")

    Return the inputs as arrays or scalars.

    Parameters
    ----------
    subok : True or False, optional
        Whether array subclasses are preserved.
    pyscalars : {"convert", "preserve", "convert_if_no_array"}, optional
        To allow NEP 50 weak promotion later, it may be desirable to preserve
        Python scalars.  As default, these are preserved unless all inputs
        are Python scalars.  "convert" enforces an array return.
    """))

add_newdoc('numpy._core._multiarray_umath', '_array_converter', ('result_type',
    """result_type(/, extra_dtype=None, ensure_inexact=False)

    Find the ``result_type`` just as ``np.result_type`` would, but taking
    into account that the original inputs (before converting to an array) may
    have been Python scalars with weak promotion.

    Parameters
    ----------
    extra_dtype : dtype instance or class
        An additional DType or dtype instance to promote (e.g. could be used
        to ensure the result precision is at least float32).
    ensure_inexact : True or False
        When ``True``, ensures a floating point (or complex) result replacing
        the ``arr * 1.`` or ``result_type(..., 0.0)`` pattern.
    """))

add_newdoc('numpy._core._multiarray_umath', '_array_converter', ('wrap',
    """
    wrap(arr, /, to_scalar=None)

    Call ``__array_wrap__`` on ``arr`` if ``arr`` is not the same subclass
    as the input the ``__array_wrap__`` method was retrieved from.

    Parameters
    ----------
    arr : ndarray
        The object to be wrapped. Normally an ndarray or subclass,
        although for backward compatibility NumPy scalars are also accepted
        (these will be converted to a NumPy array before being passed on to
        the ``__array_wrap__`` method).
    to_scalar : {True, False, None}, optional
        When ``True`` will convert a 0-d array to a scalar via ``result[()]``
        (with a fast-path for non-subclasses).  If ``False`` the result should
        be an array-like (as ``__array_wrap__`` is free to return a non-array).
        By default (``None``), a scalar is returned if all inputs were scalar.
    """))


add_newdoc('numpy._core.multiarray', '_get_madvise_hugepage',
    """
    _get_madvise_hugepage() -> bool

    Get use of ``madvise (2)`` MADV_HUGEPAGE support when
    allocating the array data. Returns the currently set value.
    See `global_state` for more information.
    """)

add_newdoc('numpy._core.multiarray', '_set_madvise_hugepage',
    """
    _set_madvise_hugepage(enabled: bool) -> bool

    Set  or unset use of ``madvise (2)`` MADV_HUGEPAGE support when
    allocating the array data. Returns the previously set value.
    See `global_state` for more information.
    """)


##############################################################################
#
# Documentation for ufunc attributes and methods
#
##############################################################################


##############################################################################
#
# ufunc object
#
##############################################################################

add_newdoc('numpy._core', 'ufunc',
    """
    Functions that operate element by element on whole arrays.

    To see the documentation for a specific ufunc, use `info`.  For
    example, ``np.info(np.sin)``.  Because ufuncs are written in C
    (for speed) and linked into Python with NumPy's ufunc facility,
    Python's help() function finds this page whenever help() is called
    on a ufunc.

    A detailed explanation of ufuncs can be found in the docs for :ref:`ufuncs`.

    **Calling ufuncs:** ``op(*x[, out], where=True, **kwargs)``

    Apply `op` to the arguments `*x` elementwise, broadcasting the arguments.

    The broadcasting rules are:

    * Dimensions of length 1 may be prepended to either array.
    * Arrays may be repeated along dimensions of length 1.

    Parameters
    ----------
    *x : array_like
        Input arrays.
    out : ndarray, None, ..., or tuple of ndarray and None, optional
        Location(s) into which the result(s) are stored.
        If not provided or None, new array(s) are created by the ufunc.
        If passed as a keyword argument, can be Ellipses (``out=...``) to
        ensure an array is returned even if the result is 0-dimensional,
        or a tuple with length equal to the number of outputs (where None
        can be used for allocation by the ufunc).

        .. versionadded:: 2.3
            Support for ``out=...`` was added.

    where : array_like, optional
        This condition is broadcast over the input. At locations where the
        condition is True, the `out` array will be set to the ufunc result.
        Elsewhere, the `out` array will retain its original value.
        Note that if an uninitialized `out` array is created via the default
        ``out=None``, locations within it where the condition is False will
        remain uninitialized.
    **kwargs
        For other keyword-only arguments, see the :ref:`ufunc docs <ufuncs.kwargs>`.

    Returns
    -------
    r : ndarray or tuple of ndarray
        `r` will have the shape that the arrays in `x` broadcast to; if `out` is
        provided, it will be returned. If not, `r` will be allocated and
        may contain uninitialized values. If the function has more than one
        output, then the result will be a tuple of arrays.

    """)


##############################################################################
#
# ufunc attributes
#
##############################################################################

add_newdoc('numpy._core', 'ufunc', ('identity',
    """
    The identity value.

    Data attribute containing the identity element for the ufunc,
    if it has one. If it does not, the attribute value is None.

    Examples
    --------
    >>> import numpy as np
    >>> np.add.identity
    0
    >>> np.multiply.identity
    1
    >>> print(np.power.identity)
    None
    >>> print(np.exp.identity)
    None
    """))

add_newdoc('numpy._core', 'ufunc', ('nargs',
    """
    The number of arguments.

    Data attribute containing the number of arguments the ufunc takes, including
    optional ones.

    Notes
    -----
    Typically this value will be one more than what you might expect
    because all ufuncs take  the optional "out" argument.

    Examples
    --------
    >>> import numpy as np
    >>> np.add.nargs
    3
    >>> np.multiply.nargs
    3
    >>> np.power.nargs
    3
    >>> np.exp.nargs
    2
    """))

add_newdoc('numpy._core', 'ufunc', ('nin',
    """
    The number of inputs.

    Data attribute containing the number of arguments the ufunc treats as input.

    Examples
    --------
    >>> import numpy as np
    >>> np.add.nin
    2
    >>> np.multiply.nin
    2
    >>> np.power.nin
    2
    >>> np.exp.nin
    1
    """))

add_newdoc('numpy._core', 'ufunc', ('nout',
    """
    The number of outputs.

    Data attribute containing the number of arguments the ufunc treats as output.

    Notes
    -----
    Since all ufuncs can take output arguments, this will always be at least 1.

    Examples
    --------
    >>> import numpy as np
    >>> np.add.nout
    1
    >>> np.multiply.nout
    1
    >>> np.power.nout
    1
    >>> np.exp.nout
    1

    """))

add_newdoc('numpy._core', 'ufunc', ('ntypes',
    """
    The number of types.

    The number of numerical NumPy types - of which there are 18 total - on which
    the ufunc can operate.

    See Also
    --------
    numpy.ufunc.types

    Examples
    --------
    >>> import numpy as np
    >>> np.add.ntypes
    22
    >>> np.multiply.ntypes
    23
    >>> np.power.ntypes
    21
    >>> np.exp.ntypes
    10
    >>> np.remainder.ntypes
    16

    """))

add_newdoc('numpy._core', 'ufunc', ('types',
    """
    Returns a list with types grouped input->output.

    Data attribute listing the data-type "Domain-Range" groupings the ufunc can
    deliver. The data-types are given using the character codes.

    See Also
    --------
    numpy.ufunc.ntypes

    Examples
    --------
    >>> import numpy as np
    >>> np.add.types
    ['??->?', 'bb->b', 'BB->B', 'hh->h', 'HH->H', 'ii->i', 'II->I', ...

    >>> np.power.types
    ['bb->b', 'BB->B', 'hh->h', 'HH->H', 'ii->i', 'II->I', 'll->l', ...

    >>> np.exp.types
    ['e->e', 'f->f', 'd->d', 'f->f', 'd->d', 'g->g', 'F->F', 'D->D', 'G->G', 'O->O']

    >>> np.remainder.types
    ['bb->b', 'BB->B', 'hh->h', 'HH->H', 'ii->i', 'II->I', 'll->l', ...

    """))

add_newdoc('numpy._core', 'ufunc', ('signature',
    """
    Definition of the core elements a generalized ufunc operates on.

    The signature determines how the dimensions of each input/output array
    are split into core and loop dimensions:

    1. Each dimension in the signature is matched to a dimension of the
       corresponding passed-in array, starting from the end of the shape tuple.
    2. Core dimensions assigned to the same label in the signature must have
       exactly matching sizes, no broadcasting is performed.
    3. The core dimensions are removed from all inputs and the remaining
       dimensions are broadcast together, defining the loop dimensions.

    Notes
    -----
    Generalized ufuncs are used internally in many linalg functions, and in
    the testing suite; the examples below are taken from these.
    For ufuncs that operate on scalars, the signature is None, which is
    equivalent to '()' for every argument.

    Examples
    --------
    >>> import numpy as np
    >>> np.linalg._umath_linalg.det.signature
    '(m,m)->()'
    >>> np.matmul.signature
    '(n?,k),(k,m?)->(n?,m?)'
    >>> np.add.signature is None
    True  # equivalent to '(),()->()'
    """))

##############################################################################
#
# ufunc methods
#
##############################################################################

add_newdoc('numpy._core', 'ufunc', ('reduce',
    """
    reduce(array, axis=0, dtype=None, out=None, keepdims=False, initial=<no value>, where=True)

    Reduces `array`'s dimension by one, by applying ufunc along one axis.

    Let :math:`array.shape = (N_0, ..., N_i, ..., N_{M-1})`.  Then
    :math:`ufunc.reduce(array, axis=i)[k_0, ..,k_{i-1}, k_{i+1}, .., k_{M-1}]` =
    the result of iterating `j` over :math:`range(N_i)`, cumulatively applying
    ufunc to each :math:`array[k_0, ..,k_{i-1}, j, k_{i+1}, .., k_{M-1}]`.
    For a one-dimensional array, reduce produces results equivalent to:
    ::

     r = op.identity # op = ufunc
     for i in range(len(A)):
       r = op(r, A[i])
     return r

    For example, add.reduce() is equivalent to sum().

    Parameters
    ----------
    array : array_like
        The array to act on.
    axis : None or int or tuple of ints, optional
        Axis or axes along which a reduction is performed.
        The default (`axis` = 0) is perform a reduction over the first
        dimension of the input array. `axis` may be negative, in
        which case it counts from the last to the first axis.

        If this is None, a reduction is performed over all the axes.
        If this is a tuple of ints, a reduction is performed on multiple
        axes, instead of a single axis or all the axes as before.

        For operations which are either not commutative or not associative,
        doing a reduction over multiple axes is not well-defined. The
        ufuncs do not currently raise an exception in this case, but will
        likely do so in the future.
    dtype : data-type code, optional
        The data type used to perform the operation. Defaults to that of
        ``out`` if given, and the data type of ``array`` otherwise (though
        upcast to conserve precision for some cases, such as
        ``numpy.add.reduce`` for integer or boolean input).
    out : ndarray, None, ..., or tuple of ndarray and None, optional
        Location into which the result is stored.
        If not provided or None, a freshly-allocated array is returned.
        If passed as a keyword argument, can be Ellipses (``out=...``) to
        ensure an array is returned even if the result is 0-dimensional
        (which is useful especially for object dtype), or a 1-element tuple
        (latter for consistency with ``ufunc.__call__``).

        .. versionadded:: 2.3
            Support for ``out=...`` was added.

    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `array`.
    initial : scalar, optional
        The value with which to start the reduction.
        If the ufunc has no identity or the dtype is object, this defaults
        to None - otherwise it defaults to ufunc.identity.
        If ``None`` is given, the first element of the reduction is used,
        and an error is thrown if the reduction is empty.
    where : array_like of bool, optional
        A boolean array which is broadcasted to match the dimensions
        of `array`, and selects elements to include in the reduction. Note
        that for ufuncs like ``minimum`` that do not have an identity
        defined, one has to pass in also ``initial``.

    Returns
    -------
    r : ndarray
        The reduced array. If `out` was supplied, `r` is a reference to it.

    Examples
    --------
    >>> import numpy as np
    >>> np.multiply.reduce([2,3,5])
    30

    A multi-dimensional array example:

    >>> X = np.arange(8).reshape((2,2,2))
    >>> X
    array([[[0, 1],
            [2, 3]],
           [[4, 5],
            [6, 7]]])
    >>> np.add.reduce(X, 0)
    array([[ 4,  6],
           [ 8, 10]])
    >>> np.add.reduce(X) # confirm: default axis value is 0
    array([[ 4,  6],
           [ 8, 10]])
    >>> np.add.reduce(X, 1)
    array([[ 2,  4],
           [10, 12]])
    >>> np.add.reduce(X, 2)
    array([[ 1,  5],
           [ 9, 13]])

    You can use the ``initial`` keyword argument to initialize the reduction
    with a different value, and ``where`` to select specific elements to include:

    >>> np.add.reduce([10], initial=5)
    15
    >>> np.add.reduce(np.ones((2, 2, 2)), axis=(0, 2), initial=10)
    array([14., 14.])
    >>> a = np.array([10., np.nan, 10])
    >>> np.add.reduce(a, where=~np.isnan(a))
    20.0

    Allows reductions of empty arrays where they would normally fail, i.e.
    for ufuncs without an identity.

    >>> np.minimum.reduce([], initial=np.inf)
    inf
    >>> np.minimum.reduce([[1., 2.], [3., 4.]], initial=10., where=[True, False])
    array([ 1., 10.])
    >>> np.minimum.reduce([])
    Traceback (most recent call last):
        ...
    ValueError: zero-size array to reduction operation minimum which has no identity
    """))

add_newdoc('numpy._core', 'ufunc', ('accumulate',
    """
    accumulate(array, axis=0, dtype=None, out=None)

    Accumulate the result of applying the operator to all elements.

    For a one-dimensional array, accumulate produces results equivalent to::

      r = np.empty(len(A))
      t = op.identity        # op = the ufunc being applied to A's  elements
      for i in range(len(A)):
          t = op(t, A[i])
          r[i] = t
      return r

    For example, add.accumulate() is equivalent to np.cumsum().

    For a multi-dimensional array, accumulate is applied along only one
    axis (axis zero by default; see Examples below) so repeated use is
    necessary if one wants to accumulate over multiple axes.

    Parameters
    ----------
    array : array_like
        The array to act on.
    axis : int, optional
        The axis along which to apply the accumulation; default is zero.
    dtype : data-type code, optional
        The data-type used to represent the intermediate results. Defaults
        to the data-type of the output array if such is provided, or the
        data-type of the input array if no output array is provided.
    out : ndarray, None, or tuple of ndarray and None, optional
        Location into which the result is stored.
        If not provided or None, a freshly-allocated array is returned.
        For consistency with ``ufunc.__call__``, if passed as a keyword
        argument, can be Ellipses (``out=...``, which has the same effect
        as None as an array is always returned), or a 1-element tuple.

    Returns
    -------
    r : ndarray
        The accumulated values. If `out` was supplied, `r` is a reference to
        `out`.

    Examples
    --------
    1-D array examples:

    >>> import numpy as np
    >>> np.add.accumulate([2, 3, 5])
    array([ 2,  5, 10])
    >>> np.multiply.accumulate([2, 3, 5])
    array([ 2,  6, 30])

    2-D array examples:

    >>> I = np.eye(2)
    >>> I
    array([[1.,  0.],
           [0.,  1.]])

    Accumulate along axis 0 (rows), down columns:

    >>> np.add.accumulate(I, 0)
    array([[1.,  0.],
           [1.,  1.]])
    >>> np.add.accumulate(I) # no axis specified = axis zero
    array([[1.,  0.],
           [1.,  1.]])

    Accumulate along axis 1 (columns), through rows:

    >>> np.add.accumulate(I, 1)
    array([[1.,  1.],
           [0.,  1.]])

    """))

add_newdoc('numpy._core', 'ufunc', ('reduceat',
    """
    reduceat(array, indices, axis=0, dtype=None, out=None)

    Performs a (local) reduce with specified slices over a single axis.

    For i in ``range(len(indices))``, `reduceat` computes
    ``ufunc.reduce(array[indices[i]:indices[i+1]])``, which becomes the i-th
    generalized "row" parallel to `axis` in the final result (i.e., in a
    2-D array, for example, if `axis = 0`, it becomes the i-th row, but if
    `axis = 1`, it becomes the i-th column).  There are three exceptions to this:

    * when ``i = len(indices) - 1`` (so for the last index),
      ``indices[i+1] = array.shape[axis]``.
    * if ``indices[i] >= indices[i + 1]``, the i-th generalized "row" is
      simply ``array[indices[i]]``.
    * if ``indices[i] >= len(array)`` or ``indices[i] < 0``, an error is raised.

    The shape of the output depends on the size of `indices`, and may be
    larger than `array` (this happens if ``len(indices) > array.shape[axis]``).

    Parameters
    ----------
    array : array_like
        The array to act on.
    indices : array_like
        Paired indices, comma separated (not colon), specifying slices to
        reduce.
    axis : int, optional
        The axis along which to apply the reduceat.
    dtype : data-type code, optional
        The data type used to perform the operation. Defaults to that of
        ``out`` if given, and the data type of ``array`` otherwise (though
        upcast to conserve precision for some cases, such as
        ``numpy.add.reduce`` for integer or boolean input).
    out : ndarray, None, or tuple of ndarray and None, optional
        Location into which the result is stored.
        If not provided or None, a freshly-allocated array is returned.
        For consistency with ``ufunc.__call__``, if passed as a keyword
        argument, can be Ellipses (``out=...``, which has the same effect
        as None as an array is always returned), or a 1-element tuple.

    Returns
    -------
    r : ndarray
        The reduced values. If `out` was supplied, `r` is a reference to
        `out`.

    Notes
    -----
    A descriptive example:

    If `array` is 1-D, the function `ufunc.accumulate(array)` is the same as
    ``ufunc.reduceat(array, indices)[::2]`` where `indices` is
    ``range(len(array) - 1)`` with a zero placed
    in every other element:
    ``indices = zeros(2 * len(array) - 1)``,
    ``indices[1::2] = range(1, len(array))``.

    Don't be fooled by this attribute's name: `reduceat(array)` is not
    necessarily smaller than `array`.

    Examples
    --------
    To take the running sum of four successive values:

    >>> import numpy as np
    >>> np.add.reduceat(np.arange(8),[0,4, 1,5, 2,6, 3,7])[::2]
    array([ 6, 10, 14, 18])

    A 2-D example:

    >>> x = np.linspace(0, 15, 16).reshape(4,4)
    >>> x
    array([[ 0.,   1.,   2.,   3.],
           [ 4.,   5.,   6.,   7.],
           [ 8.,   9.,  10.,  11.],
           [12.,  13.,  14.,  15.]])

    ::

     # reduce such that the result has the following five rows:
     # [row1 + row2 + row3]
     # [row4]
     # [row2]
     # [row3]
     # [row1 + row2 + row3 + row4]

    >>> np.add.reduceat(x, [0, 3, 1, 2, 0])
    array([[12.,  15.,  18.,  21.],
           [12.,  13.,  14.,  15.],
           [ 4.,   5.,   6.,   7.],
           [ 8.,   9.,  10.,  11.],
           [24.,  28.,  32.,  36.]])

    ::

     # reduce such that result has the following two columns:
     # [col1 * col2 * col3, col4]

    >>> np.multiply.reduceat(x, [0, 3], 1)
    array([[   0.,     3.],
           [ 120.,     7.],
           [ 720.,    11.],
           [2184.,    15.]])

    """))

add_newdoc('numpy._core', 'ufunc', ('outer',
    r"""
    outer(A, B, /, **kwargs)

    Apply the ufunc `op` to all pairs (a, b) with a in `A` and b in `B`.

    Let ``M = A.ndim``, ``N = B.ndim``. Then the result, `C`, of
    ``op.outer(A, B)`` is an array of dimension M + N such that:

    .. math:: C[i_0, ..., i_{M-1}, j_0, ..., j_{N-1}] =
       op(A[i_0, ..., i_{M-1}], B[j_0, ..., j_{N-1}])

    For `A` and `B` one-dimensional, this is equivalent to::

      r = empty(len(A),len(B))
      for i in range(len(A)):
          for j in range(len(B)):
              r[i,j] = op(A[i], B[j])  # op = ufunc in question

    Parameters
    ----------
    A : array_like
        First array
    B : array_like
        Second array
    kwargs : any
        Arguments to pass on to the ufunc. Typically `dtype` or `out`.
        See `ufunc` for a comprehensive overview of all available arguments.

    Returns
    -------
    r : ndarray
        Output array

    See Also
    --------
    numpy.outer : A less powerful version of ``np.multiply.outer``
                  that `ravel`\ s all inputs to 1D. This exists
                  primarily for compatibility with old code.

    tensordot : ``np.tensordot(a, b, axes=((), ()))`` and
                ``np.multiply.outer(a, b)`` behave same for all
                dimensions of a and b.

    Examples
    --------
    >>> np.multiply.outer([1, 2, 3], [4, 5, 6])
    array([[ 4,  5,  6],
           [ 8, 10, 12],
           [12, 15, 18]])

    A multi-dimensional example:

    >>> A = np.array([[1, 2, 3], [4, 5, 6]])
    >>> A.shape
    (2, 3)
    >>> B = np.array([[1, 2, 3, 4]])
    >>> B.shape
    (1, 4)
    >>> C = np.multiply.outer(A, B)
    >>> C.shape; C
    (2, 3, 1, 4)
    array([[[[ 1,  2,  3,  4]],
            [[ 2,  4,  6,  8]],
            [[ 3,  6,  9, 12]]],
           [[[ 4,  8, 12, 16]],
            [[ 5, 10, 15, 20]],
            [[ 6, 12, 18, 24]]]])

    """))

add_newdoc('numpy._core', 'ufunc', ('at',
    """
    at(a, indices, b=None, /)

    Performs unbuffered in place operation on operand 'a' for elements
    specified by 'indices'. For addition ufunc, this method is equivalent to
    ``a[indices] += b``, except that results are accumulated for elements that
    are indexed more than once. For example, ``a[[0,0]] += 1`` will only
    increment the first element once because of buffering, whereas
    ``add.at(a, [0,0], 1)`` will increment the first element twice.

    Parameters
    ----------
    a : array_like
        The array to perform in place operation on.
    indices : array_like or tuple
        Array like index object or slice object for indexing into first
        operand. If first operand has multiple dimensions, indices can be a
        tuple of array like index objects or slice objects.
    b : array_like
        Second operand for ufuncs requiring two operands. Operand must be
        broadcastable over first operand after indexing or slicing.

    Examples
    --------
    Set items 0 and 1 to their negative values:

    >>> import numpy as np
    >>> a = np.array([1, 2, 3, 4])
    >>> np.negative.at(a, [0, 1])
    >>> a
    array([-1, -2,  3,  4])

    Increment items 0 and 1, and increment item 2 twice:

    >>> a = np.array([1, 2, 3, 4])
    >>> np.add.at(a, [0, 1, 2, 2], 1)
    >>> a
    array([2, 3, 5, 4])

    Add items 0 and 1 in first array to second array,
    and store results in first array:

    >>> a = np.array([1, 2, 3, 4])
    >>> b = np.array([1, 2])
    >>> np.add.at(a, [0, 1], b)
    >>> a
    array([2, 4, 3, 4])

    """))

add_newdoc('numpy._core', 'ufunc', ('resolve_dtypes',
    """
    resolve_dtypes(dtypes, *, signature=None, casting=None, reduction=False)

    Find the dtypes NumPy will use for the operation.  Both input and
    output dtypes are returned and may differ from those provided.

    .. note::

        This function always applies NEP 50 rules since it is not provided
        any actual values.  The Python types ``int``, ``float``, and
        ``complex`` thus behave weak and should be passed for "untyped"
        Python input.

    Parameters
    ----------
    dtypes : tuple of dtypes, None, or literal int, float, complex
        The input dtypes for each operand.  Output operands can be
        None, indicating that the dtype must be found.
    signature : tuple of DTypes or None, optional
        If given, enforces exact DType (classes) of the specific operand.
        The ufunc ``dtype`` argument is equivalent to passing a tuple with
        only output dtypes set.
    casting : {'no', 'equiv', 'safe', 'same_kind', 'unsafe'}, optional
        The casting mode when casting is necessary.  This is identical to
        the ufunc call casting modes.
    reduction : boolean
        If given, the resolution assumes a reduce operation is happening
        which slightly changes the promotion and type resolution rules.
        `dtypes` is usually something like ``(None, np.dtype("i2"), None)``
        for reductions (first input is also the output).

        .. note::

            The default casting mode is "same_kind", however, as of
            NumPy 1.24, NumPy uses "unsafe" for reductions.

    Returns
    -------
    dtypes : tuple of dtypes
        The dtypes which NumPy would use for the calculation.  Note that
        dtypes may not match the passed in ones (casting is necessary).


    Examples
    --------
    This API requires passing dtypes, define them for convenience:

    >>> import numpy as np
    >>> int32 = np.dtype("int32")
    >>> float32 = np.dtype("float32")

    The typical ufunc call does not pass an output dtype.  `numpy.add` has two
    inputs and one output, so leave the output as ``None`` (not provided):

    >>> np.add.resolve_dtypes((int32, float32, None))
    (dtype('float64'), dtype('float64'), dtype('float64'))

    The loop found uses "float64" for all operands (including the output), the
    first input would be cast.

    ``resolve_dtypes`` supports "weak" handling for Python scalars by passing
    ``int``, ``float``, or ``complex``:

    >>> np.add.resolve_dtypes((float32, float, None))
    (dtype('float32'), dtype('float32'), dtype('float32'))

    Where the Python ``float`` behaves similar to a Python value ``0.0``
    in a ufunc call.  (See :ref:`NEP 50 <NEP50>` for details.)

    """))

add_newdoc('numpy._core', 'ufunc', ('_resolve_dtypes_and_context',
    """
    _resolve_dtypes_and_context(dtypes, *, signature=None, casting=None, reduction=False)

    See `numpy.ufunc.resolve_dtypes` for parameter information.  This
    function is considered *unstable*.  You may use it, but the returned
    information is NumPy version specific and expected to change.
    Large API/ABI changes are not expected, but a new NumPy version is
    expected to require updating code using this functionality.

    This function is designed to be used in conjunction with
    `numpy.ufunc._get_strided_loop`.  The calls are split to mirror the C API
    and allow future improvements.

    Returns
    -------
    dtypes : tuple of dtypes
    call_info :
        PyCapsule with all necessary information to get access to low level
        C calls.  See `numpy.ufunc._get_strided_loop` for more information.

    """))

add_newdoc('numpy._core', 'ufunc', ('_get_strided_loop',
    """
    _get_strided_loop(call_info, /, *, fixed_strides=None)

    This function fills in the ``call_info`` capsule to include all
    information necessary to call the low-level strided loop from NumPy.

    See notes for more information.

    Parameters
    ----------
    call_info : PyCapsule
        The PyCapsule returned by `numpy.ufunc._resolve_dtypes_and_context`.
    fixed_strides : tuple of int or None, optional
        A tuple with fixed byte strides of all input arrays.  NumPy may use
        this information to find specialized loops, so any call must follow
        the given stride.  Use ``None`` to indicate that the stride is not
        known (or not fixed) for all calls.

    Notes
    -----
    Together with `numpy.ufunc._resolve_dtypes_and_context` this function
    gives low-level access to the NumPy ufunc loops.
    The first function does general preparation and returns the required
    information. It returns this as a C capsule with the version specific
    name ``numpy_1.24_ufunc_call_info``.
    The NumPy 1.24 ufunc call info capsule has the following layout::

        typedef struct {
            PyArrayMethod_StridedLoop *strided_loop;
            PyArrayMethod_Context *context;
            NpyAuxData *auxdata;

            /* Flag information (expected to change) */
            npy_bool requires_pyapi;  /* GIL is required by loop */

            /* Loop doesn't set FPE flags; if not set check FPE flags */
            npy_bool no_floatingpoint_errors;
        } ufunc_call_info;

    Note that the first call only fills in the ``context``.  The call to
    ``_get_strided_loop`` fills in all other data.  The main thing to note is
    that the new-style loops return 0 on success, -1 on failure.  They are
    passed context as new first input and ``auxdata`` as (replaced) last.

    Only the ``strided_loop``signature is considered guaranteed stable
    for NumPy bug-fix releases.  All other API is tied to the experimental
    API versioning.

    The reason for the split call is that cast information is required to
    decide what the fixed-strides will be.

    NumPy ties the lifetime of the ``auxdata`` information to the capsule.

    """))


##############################################################################
#
# Documentation for dtype attributes and methods
#
##############################################################################

##############################################################################
#
# dtype object
#
##############################################################################

add_newdoc('numpy._core.multiarray', 'dtype',
    """
    dtype(dtype, align=False, copy=False, [metadata])

    Create a data type object.

    A numpy array is homogeneous, and contains elements described by a
    dtype object. A dtype object can be constructed from different
    combinations of fundamental numeric types.

    Parameters
    ----------
    dtype
        Object to be converted to a data type object.
    align : bool, optional
        Add padding to the fields to match what a C compiler would output
        for a similar C-struct. Can be ``True`` only if `obj` is a dictionary
        or a comma-separated string. If a struct dtype is being created,
        this also sets a sticky alignment flag ``isalignedstruct``.
    copy : bool, optional
        Make a new copy of the data-type object. If ``False``, the result
        may just be a reference to a built-in data-type object.
    metadata : dict, optional
        An optional dictionary with dtype metadata.

    See also
    --------
    result_type

    Examples
    --------
    Using array-scalar type:

    >>> import numpy as np
    >>> np.dtype(np.int16)
    dtype('int16')

    Structured type, one field name 'f1', containing int16:

    >>> np.dtype([('f1', np.int16)])
    dtype([('f1', '<i2')])

    Structured type, one field named 'f1', in itself containing a structured
    type with one field:

    >>> np.dtype([('f1', [('f1', np.int16)])])
    dtype([('f1', [('f1', '<i2')])])

    Structured type, two fields: the first field contains an unsigned int, the
    second an int32:

    >>> np.dtype([('f1', np.uint64), ('f2', np.int32)])
    dtype([('f1', '<u8'), ('f2', '<i4')])

    Using array-protocol type strings:

    >>> np.dtype([('a','f8'),('b','S10')])
    dtype([('a', '<f8'), ('b', 'S10')])

    Using comma-separated field formats.  The shape is (2,3):

    >>> np.dtype("i4, (2,3)f8")
    dtype([('f0', '<i4'), ('f1', '<f8', (2, 3))])

    Using tuples.  ``int`` is a fixed type, 3 the field's shape.  ``void``
    is a flexible type, here of size 10:

    >>> np.dtype([('hello',(np.int64,3)),('world',np.void,10)])
    dtype([('hello', '<i8', (3,)), ('world', 'V10')])

    Subdivide ``int16`` into 2 ``int8``'s, called x and y.  0 and 1 are
    the offsets in bytes:

    >>> np.dtype((np.int16, {'x':(np.int8,0), 'y':(np.int8,1)}))
    dtype((numpy.int16, [('x', 'i1'), ('y', 'i1')]))

    Using dictionaries.  Two fields named 'gender' and 'age':

    >>> np.dtype({'names':['gender','age'], 'formats':['S1',np.uint8]})
    dtype([('gender', 'S1'), ('age', 'u1')])

    Offsets in bytes, here 0 and 25:

    >>> np.dtype({'surname':('S25',0),'age':(np.uint8,25)})
    dtype([('surname', 'S25'), ('age', 'u1')])

    """)

##############################################################################
#
# dtype attributes
#
##############################################################################

add_newdoc('numpy._core.multiarray', 'dtype', ('alignment',
    """
    The required alignment (bytes) of this data-type according to the compiler.

    More information is available in the C-API section of the manual.

    Examples
    --------

    >>> import numpy as np
    >>> x = np.dtype('i4')
    >>> x.alignment
    4

    >>> x = np.dtype(float)
    >>> x.alignment
    8

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('byteorder',
    """
    A character indicating the byte-order of this data-type object.

    One of:

    ===  ==============
    '='  native
    '<'  little-endian
    '>'  big-endian
    '|'  not applicable
    ===  ==============

    All built-in data-type objects have byteorder either '=' or '|'.

    Examples
    --------

    >>> import numpy as np
    >>> dt = np.dtype('i2')
    >>> dt.byteorder
    '='
    >>> # endian is not relevant for 8 bit numbers
    >>> np.dtype('i1').byteorder
    '|'
    >>> # or ASCII strings
    >>> np.dtype('S2').byteorder
    '|'
    >>> # Even if specific code is given, and it is native
    >>> # '=' is the byteorder
    >>> import sys
    >>> sys_is_le = sys.byteorder == 'little'
    >>> native_code = '<' if sys_is_le else '>'
    >>> swapped_code = '>' if sys_is_le else '<'
    >>> dt = np.dtype(native_code + 'i2')
    >>> dt.byteorder
    '='
    >>> # Swapped code shows up as itself
    >>> dt = np.dtype(swapped_code + 'i2')
    >>> dt.byteorder == swapped_code
    True

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('char',
    """A unique character code for each of the 21 different built-in types.

    Examples
    --------

    >>> import numpy as np
    >>> x = np.dtype(float)
    >>> x.char
    'd'

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('descr',
    """
    `__array_interface__` description of the data-type.

    The format is that required by the 'descr' key in the
    `__array_interface__` attribute.

    Warning: This attribute exists specifically for `__array_interface__`,
    and passing it directly to `numpy.dtype` will not accurately reconstruct
    some dtypes (e.g., scalar and subarray dtypes).

    Examples
    --------

    >>> import numpy as np
    >>> x = np.dtype(float)
    >>> x.descr
    [('', '<f8')]

    >>> dt = np.dtype([('name', np.str_, 16), ('grades', np.float64, (2,))])
    >>> dt.descr
    [('name', '<U16'), ('grades', '<f8', (2,))]

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('fields',
    """
    Dictionary of named fields defined for this data type, or ``None``.

    The dictionary is indexed by keys that are the names of the fields.
    Each entry in the dictionary is a tuple fully describing the field::

      (dtype, offset[, title])

    Offset is limited to C int, which is signed and usually 32 bits.
    If present, the optional title can be any object (if it is a string
    or unicode then it will also be a key in the fields dictionary,
    otherwise it's meta-data). Notice also that the first two elements
    of the tuple can be passed directly as arguments to the
    ``ndarray.getfield`` and ``ndarray.setfield`` methods.

    See Also
    --------
    ndarray.getfield, ndarray.setfield

    Examples
    --------

    >>> import numpy as np
    >>> dt = np.dtype([('name', np.str_, 16), ('grades', np.float64, (2,))])
    >>> print(dt.fields)
    {'name': (dtype('|S16'), 0), 'grades': (dtype(('float64',(2,))), 16)}

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('flags',
    """
    Bit-flags describing how this data type is to be interpreted.

    Bit-masks are in ``numpy._core.multiarray`` as the constants
    `ITEM_HASOBJECT`, `LIST_PICKLE`, `ITEM_IS_POINTER`, `NEEDS_INIT`,
    `NEEDS_PYAPI`, `USE_GETITEM`, `USE_SETITEM`. A full explanation
    of these flags is in C-API documentation; they are largely useful
    for user-defined data-types.

    The following example demonstrates that operations on this particular
    dtype requires Python C-API.

    Examples
    --------

    >>> import numpy as np
    >>> x = np.dtype([('a', np.int32, 8), ('b', np.float64, 6)])
    >>> x.flags
    16
    >>> np._core.multiarray.NEEDS_PYAPI
    16

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('hasobject',
    """
    Boolean indicating whether this dtype contains any reference-counted
    objects in any fields or sub-dtypes.

    Recall that what is actually in the ndarray memory representing
    the Python object is the memory address of that object (a pointer).
    Special handling may be required, and this attribute is useful for
    distinguishing data types that may contain arbitrary Python objects
    and data-types that won't.

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('isbuiltin',
    """
    Integer indicating how this dtype relates to the built-in dtypes.

    Read-only.

    =  ========================================================================
    0  if this is a structured array type, with fields
    1  if this is a dtype compiled into numpy (such as ints, floats etc)
    2  if the dtype is for a user-defined numpy type
       A user-defined type uses the numpy C-API machinery to extend
       numpy to handle a new array type. See
       :ref:`user.user-defined-data-types` in the NumPy manual.
    =  ========================================================================

    Examples
    --------

    >>> import numpy as np
    >>> dt = np.dtype('i2')
    >>> dt.isbuiltin
    1
    >>> dt = np.dtype('f8')
    >>> dt.isbuiltin
    1
    >>> dt = np.dtype([('field1', 'f8')])
    >>> dt.isbuiltin
    0

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('isnative',
    """
    Boolean indicating whether the byte order of this dtype is native
    to the platform.

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('isalignedstruct',
    """
    Boolean indicating whether the dtype is a struct which maintains
    field alignment. This flag is sticky, so when combining multiple
    structs together, it is preserved and produces new dtypes which
    are also aligned.

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('itemsize',
    """
    The element size of this data-type object.

    For 18 of the 21 types this number is fixed by the data-type.
    For the flexible data-types, this number can be anything.

    Examples
    --------

    >>> import numpy as np
    >>> arr = np.array([[1, 2], [3, 4]])
    >>> arr.dtype
    dtype('int64')
    >>> arr.itemsize
    8

    >>> dt = np.dtype([('name', np.str_, 16), ('grades', np.float64, (2,))])
    >>> dt.itemsize
    80

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('kind',
    """
    A character code (one of 'biufcmMOSTUV') identifying the general kind of data.

    =  ======================
    b  boolean
    i  signed integer
    u  unsigned integer
    f  floating-point
    c  complex floating-point
    m  timedelta
    M  datetime
    O  object
    S  (byte-)string
    T  string (StringDType)
    U  Unicode
    V  void
    =  ======================

    Examples
    --------

    >>> import numpy as np
    >>> dt = np.dtype('i4')
    >>> dt.kind
    'i'
    >>> dt = np.dtype('f8')
    >>> dt.kind
    'f'
    >>> dt = np.dtype([('field1', 'f8')])
    >>> dt.kind
    'V'

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('metadata',
    """
    Either ``None`` or a readonly dictionary of metadata (mappingproxy).

    The metadata field can be set using any dictionary at data-type
    creation. NumPy currently has no uniform approach to propagating
    metadata; although some array operations preserve it, there is no
    guarantee that others will.

    .. warning::

        Although used in certain projects, this feature was long undocumented
        and is not well supported. Some aspects of metadata propagation
        are expected to change in the future.

    Examples
    --------

    >>> import numpy as np
    >>> dt = np.dtype(float, metadata={"key": "value"})
    >>> dt.metadata["key"]
    'value'
    >>> arr = np.array([1, 2, 3], dtype=dt)
    >>> arr.dtype.metadata
    mappingproxy({'key': 'value'})

    Adding arrays with identical datatypes currently preserves the metadata:

    >>> (arr + arr).dtype.metadata
    mappingproxy({'key': 'value'})

    If the arrays have different dtype metadata, the first one wins:

    >>> dt2 = np.dtype(float, metadata={"key2": "value2"})
    >>> arr2 = np.array([3, 2, 1], dtype=dt2)
    >>> print((arr + arr2).dtype.metadata)
    {'key': 'value'}
    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('name',
    """
    A bit-width name for this data-type.

    Un-sized flexible data-type objects do not have this attribute.

    Examples
    --------

    >>> import numpy as np
    >>> x = np.dtype(float)
    >>> x.name
    'float64'
    >>> x = np.dtype([('a', np.int32, 8), ('b', np.float64, 6)])
    >>> x.name
    'void640'

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('names',
    """
    Ordered list of field names, or ``None`` if there are no fields.

    The names are ordered according to increasing byte offset. This can be
    used, for example, to walk through all of the named fields in offset order.

    Examples
    --------
    >>> dt = np.dtype([('name', np.str_, 16), ('grades', np.float64, (2,))])
    >>> dt.names
    ('name', 'grades')

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('num',
    """
    A unique number for each of the 21 different built-in types.

    These are roughly ordered from least-to-most precision.

    Examples
    --------

    >>> import numpy as np
    >>> dt = np.dtype(str)
    >>> dt.num
    19

    >>> dt = np.dtype(float)
    >>> dt.num
    12

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('shape',
    """
    Shape tuple of the sub-array if this data type describes a sub-array,
    and ``()`` otherwise.

    Examples
    --------

    >>> import numpy as np
    >>> dt = np.dtype(('i4', 4))
    >>> dt.shape
    (4,)

    >>> dt = np.dtype(('i4', (2, 3)))
    >>> dt.shape
    (2, 3)

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('ndim',
    """
    Number of dimensions of the sub-array if this data type describes a
    sub-array, and ``0`` otherwise.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.dtype(float)
    >>> x.ndim
    0

    >>> x = np.dtype((float, 8))
    >>> x.ndim
    1

    >>> x = np.dtype(('i4', (3, 4)))
    >>> x.ndim
    2

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('str',
    """The array-protocol typestring of this data-type object."""))

add_newdoc('numpy._core.multiarray', 'dtype', ('subdtype',
    """
    Tuple ``(item_dtype, shape)`` if this `dtype` describes a sub-array, and
    None otherwise.

    The *shape* is the fixed shape of the sub-array described by this
    data type, and *item_dtype* the data type of the array.

    If a field whose dtype object has this attribute is retrieved,
    then the extra dimensions implied by *shape* are tacked on to
    the end of the retrieved array.

    See Also
    --------
    dtype.base

    Examples
    --------
    >>> import numpy as np
    >>> x = np.dtype('8f')
    >>> x.subdtype
    (dtype('float32'), (8,))

    >>> x =  np.dtype('i2')
    >>> x.subdtype
    >>>

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('base',
    """
    Returns dtype for the base element of the subarrays,
    regardless of their dimension or shape.

    See Also
    --------
    dtype.subdtype

    Examples
    --------
    >>> import numpy as np
    >>> x = np.dtype('8f')
    >>> x.base
    dtype('float32')

    >>> x =  np.dtype('i2')
    >>> x.base
    dtype('int16')

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('type',
    """The type object used to instantiate a scalar of this data-type."""))

##############################################################################
#
# dtype methods
#
##############################################################################

add_newdoc('numpy._core.multiarray', 'dtype', ('newbyteorder',
    """
    newbyteorder(new_order='S', /)

    Return a new dtype with a different byte order.

    Changes are also made in all fields and sub-arrays of the data type.

    Parameters
    ----------
    new_order : string, optional
        Byte order to force; a value from the byte order specifications
        below.  The default value ('S') results in swapping the current
        byte order.  `new_order` codes can be any of:

        * 'S' - swap dtype from current to opposite endian
        * {'<', 'little'} - little endian
        * {'>', 'big'} - big endian
        * {'=', 'native'} - native order
        * {'|', 'I'} - ignore (no change to byte order)

    Returns
    -------
    new_dtype : dtype
        New dtype object with the given change to the byte order.

    Notes
    -----
    Changes are also made in all fields and sub-arrays of the data type.

    Examples
    --------
    >>> import sys
    >>> sys_is_le = sys.byteorder == 'little'
    >>> native_code = '<' if sys_is_le else '>'
    >>> swapped_code = '>' if sys_is_le else '<'
    >>> import numpy as np
    >>> native_dt = np.dtype(native_code+'i2')
    >>> swapped_dt = np.dtype(swapped_code+'i2')
    >>> native_dt.newbyteorder('S') == swapped_dt
    True
    >>> native_dt.newbyteorder() == swapped_dt
    True
    >>> native_dt == swapped_dt.newbyteorder('S')
    True
    >>> native_dt == swapped_dt.newbyteorder('=')
    True
    >>> native_dt == swapped_dt.newbyteorder('N')
    True
    >>> native_dt == native_dt.newbyteorder('|')
    True
    >>> np.dtype('<i2') == native_dt.newbyteorder('<')
    True
    >>> np.dtype('<i2') == native_dt.newbyteorder('L')
    True
    >>> np.dtype('>i2') == native_dt.newbyteorder('>')
    True
    >>> np.dtype('>i2') == native_dt.newbyteorder('B')
    True

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('__class_getitem__',
    """
    __class_getitem__(item, /)

    Return a parametrized wrapper around the `~numpy.dtype` type.

    .. versionadded:: 1.22

    Returns
    -------
    alias : types.GenericAlias
        A parametrized `~numpy.dtype` type.

    Examples
    --------
    >>> import numpy as np

    >>> np.dtype[np.int64]
    numpy.dtype[numpy.int64]

    See Also
    --------
    :pep:`585` : Type hinting generics in standard collections.

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('__ge__',
    """
    __ge__(value, /)

    Return ``self >= value``.

    Equivalent to ``np.can_cast(value, self, casting="safe")``.

    See Also
    --------
    can_cast : Returns True if cast between data types can occur according to
               the casting rule.

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('__le__',
    """
    __le__(value, /)

    Return ``self <= value``.

    Equivalent to ``np.can_cast(self, value, casting="safe")``.

    See Also
    --------
    can_cast : Returns True if cast between data types can occur according to
               the casting rule.

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('__gt__',
    """
    __ge__(value, /)

    Return ``self > value``.

    Equivalent to
    ``self != value and np.can_cast(value, self, casting="safe")``.

    See Also
    --------
    can_cast : Returns True if cast between data types can occur according to
               the casting rule.

    """))

add_newdoc('numpy._core.multiarray', 'dtype', ('__lt__',
    """
    __lt__(value, /)

    Return ``self < value``.

    Equivalent to
    ``self != value and np.can_cast(self, value, casting="safe")``.

    See Also
    --------
    can_cast : Returns True if cast between data types can occur according to
               the casting rule.

    """))

##############################################################################
#
# Datetime-related Methods
#
##############################################################################

add_newdoc('numpy._core.multiarray', 'busdaycalendar',
    """
    busdaycalendar(weekmask='1111100', holidays=None)

    A business day calendar object that efficiently stores information
    defining valid days for the busday family of functions.

    The default valid days are Monday through Friday ("business days").
    A busdaycalendar object can be specified with any set of weekly
    valid days, plus an optional "holiday" dates that always will be invalid.

    Once a busdaycalendar object is created, the weekmask and holidays
    cannot be modified.

    Parameters
    ----------
    weekmask : str or array_like of bool, optional
        A seven-element array indicating which of Monday through Sunday are
        valid days. May be specified as a length-seven list or array, like
        [1,1,1,1,1,0,0]; a length-seven string, like '1111100'; or a string
        like "Mon Tue Wed Thu Fri", made up of 3-character abbreviations for
        weekdays, optionally separated by white space. Valid abbreviations
        are: Mon Tue Wed Thu Fri Sat Sun
    holidays : array_like of datetime64[D], optional
        An array of dates to consider as invalid dates, no matter which
        weekday they fall upon.  Holiday dates may be specified in any
        order, and NaT (not-a-time) dates are ignored.  This list is
        saved in a normalized form that is suited for fast calculations
        of valid days.

    Returns
    -------
    out : busdaycalendar
        A business day calendar object containing the specified
        weekmask and holidays values.

    See Also
    --------
    is_busday : Returns a boolean array indicating valid days.
    busday_offset : Applies an offset counted in valid days.
    busday_count : Counts how many valid days are in a half-open date range.

    Attributes
    ----------
    weekmask : (copy) seven-element array of bool
    holidays : (copy) sorted array of datetime64[D]

    Notes
    -----
    Once a busdaycalendar object is created, you cannot modify the
    weekmask or holidays.  The attributes return copies of internal data.

    Examples
    --------
    >>> import numpy as np
    >>> # Some important days in July
    ... bdd = np.busdaycalendar(
    ...             holidays=['2011-07-01', '2011-07-04', '2011-07-17'])
    >>> # Default is Monday to Friday weekdays
    ... bdd.weekmask
    array([ True,  True,  True,  True,  True, False, False])
    >>> # Any holidays already on the weekend are removed
    ... bdd.holidays
    array(['2011-07-01', '2011-07-04'], dtype='datetime64[D]')
    """)

add_newdoc('numpy._core.multiarray', 'busdaycalendar', ('weekmask',
    """A copy of the seven-element boolean mask indicating valid days."""))

add_newdoc('numpy._core.multiarray', 'busdaycalendar', ('holidays',
    """A copy of the holiday array indicating additional invalid days."""))

add_newdoc('numpy._core.multiarray', 'normalize_axis_index',
    """
    normalize_axis_index(axis, ndim, msg_prefix=None)

    Normalizes an axis index, `axis`, such that is a valid positive index into
    the shape of array with `ndim` dimensions. Raises an AxisError with an
    appropriate message if this is not possible.

    Used internally by all axis-checking logic.

    Parameters
    ----------
    axis : int
        The un-normalized index of the axis. Can be negative
    ndim : int
        The number of dimensions of the array that `axis` should be normalized
        against
    msg_prefix : str
        A prefix to put before the message, typically the name of the argument

    Returns
    -------
    normalized_axis : int
        The normalized axis index, such that `0 <= normalized_axis < ndim`

    Raises
    ------
    AxisError
        If the axis index is invalid, when `-ndim <= axis < ndim` is false.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.lib.array_utils import normalize_axis_index
    >>> normalize_axis_index(0, ndim=3)
    0
    >>> normalize_axis_index(1, ndim=3)
    1
    >>> normalize_axis_index(-1, ndim=3)
    2

    >>> normalize_axis_index(3, ndim=3)
    Traceback (most recent call last):
    ...
    numpy.exceptions.AxisError: axis 3 is out of bounds for array ...
    >>> normalize_axis_index(-4, ndim=3, msg_prefix='axes_arg')
    Traceback (most recent call last):
    ...
    numpy.exceptions.AxisError: axes_arg: axis -4 is out of bounds ...
    """)

add_newdoc('numpy._core.multiarray', 'datetime_data',
    """
    datetime_data(dtype, /)

    Get information about the step size of a date or time type.

    The returned tuple can be passed as the second argument of `numpy.datetime64` and
    `numpy.timedelta64`.

    Parameters
    ----------
    dtype : dtype
        The dtype object, which must be a `datetime64` or `timedelta64` type.

    Returns
    -------
    unit : str
        The :ref:`datetime unit <arrays.dtypes.dateunits>` on which this dtype
        is based.
    count : int
        The number of base units in a step.

    Examples
    --------
    >>> import numpy as np
    >>> dt_25s = np.dtype('timedelta64[25s]')
    >>> np.datetime_data(dt_25s)
    ('s', 25)
    >>> np.array(10, dt_25s).astype('timedelta64[s]')
    array(250, dtype='timedelta64[s]')

    The result can be used to construct a datetime that uses the same units
    as a timedelta

    >>> np.datetime64('2010', np.datetime_data(dt_25s))
    np.datetime64('2010-01-01T00:00:00','25s')
    """)


##############################################################################
#
# Documentation for `generic` attributes and methods
#
##############################################################################

add_newdoc('numpy._core.numerictypes', 'generic',
    """
    Base class for numpy scalar types.

    Class from which most (all?) numpy scalar types are derived.  For
    consistency, exposes the same API as `ndarray`, despite many
    consequent attributes being either "get-only," or completely irrelevant.
    This is the class from which it is strongly suggested users should derive
    custom scalar types.

    """)

# Attributes

def refer_to_array_attribute(attr, method=True):
    docstring = """
    Scalar {} identical to the corresponding array attribute.

    Please see `ndarray.{}`.
    """

    return attr, docstring.format("method" if method else "attribute", attr)


add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('T', method=False))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('base', method=False))

add_newdoc('numpy._core.numerictypes', 'generic', ('data',
    """Pointer to start of data."""))

add_newdoc('numpy._core.numerictypes', 'generic', ('dtype',
    """Get array data-descriptor."""))

add_newdoc('numpy._core.numerictypes', 'generic', ('flags',
    """The integer value of flags."""))

add_newdoc('numpy._core.numerictypes', 'generic', ('flat',
    """A 1-D view of the scalar."""))

add_newdoc('numpy._core.numerictypes', 'generic', ('imag',
    """The imaginary part of the scalar."""))

add_newdoc('numpy._core.numerictypes', 'generic', ('itemsize',
    """The length of one element in bytes."""))

add_newdoc('numpy._core.numerictypes', 'generic', ('ndim',
    """The number of array dimensions."""))

add_newdoc('numpy._core.numerictypes', 'generic', ('real',
    """The real part of the scalar."""))

add_newdoc('numpy._core.numerictypes', 'generic', ('shape',
    """Tuple of array dimensions."""))

add_newdoc('numpy._core.numerictypes', 'generic', ('size',
    """The number of elements in the gentype."""))

add_newdoc('numpy._core.numerictypes', 'generic', ('strides',
    """Tuple of bytes steps in each dimension."""))

# Methods

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('all'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('any'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('argmax'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('argmin'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('argsort'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('astype'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('byteswap'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('choose'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('clip'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('compress'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('conjugate'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('copy'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('cumprod'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('cumsum'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('diagonal'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('dump'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('dumps'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('fill'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('flatten'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('getfield'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('item'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('max'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('mean'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('min'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('nonzero'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('prod'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('put'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('ravel'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('repeat'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('reshape'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('resize'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('round'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('searchsorted'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('setfield'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('setflags'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('sort'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('squeeze'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('std'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('sum'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('swapaxes'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('take'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('tofile'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('tolist'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('tostring'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('trace'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('transpose'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('var'))

add_newdoc('numpy._core.numerictypes', 'generic',
           refer_to_array_attribute('view'))

add_newdoc('numpy._core.numerictypes', 'number', ('__class_getitem__',
    """
    __class_getitem__(item, /)

    Return a parametrized wrapper around the `~numpy.number` type.

    .. versionadded:: 1.22

    Returns
    -------
    alias : types.GenericAlias
        A parametrized `~numpy.number` type.

    Examples
    --------
    >>> from typing import Any
    >>> import numpy as np

    >>> np.signedinteger[Any]
    numpy.signedinteger[typing.Any]

    See Also
    --------
    :pep:`585` : Type hinting generics in standard collections.

    """))

##############################################################################
#
# Documentation for scalar type abstract base classes in type hierarchy
#
##############################################################################


add_newdoc('numpy._core.numerictypes', 'number',
    """
    Abstract base class of all numeric scalar types.

    """)

add_newdoc('numpy._core.numerictypes', 'integer',
    """
    Abstract base class of all integer scalar types.

    """)

add_newdoc('numpy._core.numerictypes', 'signedinteger',
    """
    Abstract base class of all signed integer scalar types.

    """)

add_newdoc('numpy._core.numerictypes', 'unsignedinteger',
    """
    Abstract base class of all unsigned integer scalar types.

    """)

add_newdoc('numpy._core.numerictypes', 'inexact',
    """
    Abstract base class of all numeric scalar types with a (potentially)
    inexact representation of the values in its range, such as
    floating-point numbers.

    """)

add_newdoc('numpy._core.numerictypes', 'floating',
    """
    Abstract base class of all floating-point scalar types.

    """)

add_newdoc('numpy._core.numerictypes', 'complexfloating',
    """
    Abstract base class of all complex number scalar types that are made up of
    floating-point numbers.

    """)

add_newdoc('numpy._core.numerictypes', 'flexible',
    """
    Abstract base class of all scalar types without predefined length.
    The actual size of these types depends on the specific `numpy.dtype`
    instantiation.

    """)

add_newdoc('numpy._core.numerictypes', 'character',
    """
    Abstract base class of all character string scalar types.

    """)

add_newdoc('numpy._core.multiarray', 'StringDType',
    """
    StringDType(*, na_object=np._NoValue, coerce=True)

    Create a StringDType instance.

    StringDType can be used to store UTF-8 encoded variable-width strings in
    a NumPy array.

    Parameters
    ----------
    na_object : object, optional
        Object used to represent missing data. If unset, the array will not
        use a missing data sentinel.
    coerce : bool, optional
        Whether or not items in an array-like passed to an array creation
        function that are neither a str or str subtype should be coerced to
        str. Defaults to True. If set to False, creating a StringDType
        array from an array-like containing entries that are not already
        strings will raise an error.

    Examples
    --------

    >>> import numpy as np

    >>> from numpy.dtypes import StringDType
    >>> np.array(["hello", "world"], dtype=StringDType())
    array(["hello", "world"], dtype=StringDType())

    >>> arr = np.array(["hello", None, "world"],
    ...                dtype=StringDType(na_object=None))
    >>> arr
    array(["hello", None, "world"], dtype=StringDType(na_object=None))
    >>> arr[1] is None
    True

    >>> arr = np.array(["hello", np.nan, "world"],
    ...                dtype=StringDType(na_object=np.nan))
    >>> np.isnan(arr)
    array([False, True, False])

    >>> np.array([1.2, object(), "hello world"],
    ...          dtype=StringDType(coerce=False))
    Traceback (most recent call last):
        ...
    ValueError: StringDType only allows string data when string coercion is disabled.

    >>> np.array(["hello", "world"], dtype=StringDType(coerce=True))
    array(["hello", "world"], dtype=StringDType(coerce=True))
    """)