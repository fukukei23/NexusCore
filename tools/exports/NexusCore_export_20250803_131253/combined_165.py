
# === NexusCore/tools\exports\export_20250803_114325\combined_141.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\images\main.py ===
import asyncio
import contextvars
from functools import partial
from typing import Any, Coroutine, Dict, Literal, Optional, Union, cast

import httpx

import litellm
from litellm import Logging, client, exception_type, get_litellm_params
from litellm.constants import DEFAULT_IMAGE_ENDPOINT_MODEL
from litellm.constants import request_timeout as DEFAULT_REQUEST_TIMEOUT
from litellm.exceptions import LiteLLMUnknownProvider
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.litellm_core_utils.mock_functions import mock_image_generation
from litellm.llms.base_llm import BaseImageEditConfig, BaseImageGenerationConfig
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler, HTTPHandler
from litellm.llms.custom_llm import CustomLLM

#################### Initialize provider clients ####################
from litellm.main import (
    azure_chat_completions,
    base_llm_aiohttp_handler,
    base_llm_http_handler,
    bedrock_image_generation,
    openai_chat_completions,
    openai_image_variations,
    vertex_image_generation,
)
from litellm.secret_managers.main import get_secret_str
from litellm.types.images.main import ImageEditOptionalRequestParams
from litellm.types.llms.openai import ImageGenerationRequestQuality
from litellm.types.router import GenericLiteLLMParams
from litellm.types.utils import (
    LITELLM_IMAGE_VARIATION_PROVIDERS,
    FileTypes,
    LlmProviders,
    all_litellm_params,
)
from litellm.utils import (
    ImageResponse,
    ProviderConfigManager,
    get_llm_provider,
    get_optional_params_image_gen,
)

from .utils import ImageEditRequestUtils


##### Image Generation #######################
@client
async def aimage_generation(*args, **kwargs) -> ImageResponse:
    """
    Asynchronously calls the `image_generation` function with the given arguments and keyword arguments.

    Parameters:
    - `args` (tuple): Positional arguments to be passed to the `image_generation` function.
    - `kwargs` (dict): Keyword arguments to be passed to the `image_generation` function.

    Returns:
    - `response` (Any): The response returned by the `image_generation` function.
    """
    loop = asyncio.get_event_loop()
    model = args[0] if len(args) > 0 else kwargs["model"]
    ### PASS ARGS TO Image Generation ###
    kwargs["aimg_generation"] = True
    custom_llm_provider = None
    try:
        # Use a partial function to pass your keyword arguments
        func = partial(image_generation, *args, **kwargs)

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        _, custom_llm_provider, _, _ = get_llm_provider(
            model=model, api_base=kwargs.get("api_base", None)
        )

        # Await normally
        init_response = await loop.run_in_executor(None, func_with_context)
        if isinstance(init_response, dict) or isinstance(
            init_response, ImageResponse
        ):  ## CACHING SCENARIO
            if isinstance(init_response, dict):
                init_response = ImageResponse(**init_response)
            response = init_response
        elif asyncio.iscoroutine(init_response):
            response = await init_response  # type: ignore
        else:
            # Call the synchronous function using run_in_executor
            response = await loop.run_in_executor(None, func_with_context)
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
def image_generation(  # noqa: PLR0915
    prompt: str,
    model: Optional[str] = None,
    n: Optional[int] = None,
    quality: Optional[Union[str, ImageGenerationRequestQuality]] = None,
    response_format: Optional[str] = None,
    size: Optional[str] = None,
    style: Optional[str] = None,
    user: Optional[str] = None,
    timeout=600,  # default to 10 minutes
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    api_version: Optional[str] = None,
    custom_llm_provider=None,
    **kwargs,
) -> ImageResponse:
    """
    Maps the https://api.openai.com/v1/images/generations endpoint.

    Currently supports just Azure + OpenAI.
    """
    try:
        args = locals()
        aimg_generation = kwargs.get("aimg_generation", False)
        litellm_call_id = kwargs.get("litellm_call_id", None)
        logger_fn = kwargs.get("logger_fn", None)
        mock_response: Optional[str] = kwargs.get("mock_response", None)  # type: ignore
        proxy_server_request = kwargs.get("proxy_server_request", None)
        azure_ad_token_provider = kwargs.get("azure_ad_token_provider", None)
        model_info = kwargs.get("model_info", None)
        metadata = kwargs.get("metadata", {})
        litellm_logging_obj: LiteLLMLoggingObj = kwargs.get("litellm_logging_obj")  # type: ignore
        client = kwargs.get("client", None)
        extra_headers = kwargs.get("extra_headers", None)
        headers: dict = kwargs.get("headers", None) or {}
        base_model = kwargs.get("base_model", None)
        if extra_headers is not None:
            headers.update(extra_headers)
        model_response: ImageResponse = litellm.utils.ImageResponse()
        dynamic_api_key: Optional[str] = None
        if model is not None or custom_llm_provider is not None:
            model, custom_llm_provider, dynamic_api_key, api_base = get_llm_provider(
                model=model,  # type: ignore
                custom_llm_provider=custom_llm_provider,
                api_base=api_base,
            )
        else:
            model = "dall-e-2"
            custom_llm_provider = "openai"  # default to dall-e-2 on openai
        model_response._hidden_params["model"] = model
        openai_params = [
            "user",
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
            "n",
            "quality",
            "size",
            "style",
        ]
        litellm_params = all_litellm_params
        default_params = openai_params + litellm_params
        non_default_params = {
            k: v for k, v in kwargs.items() if k not in default_params
        }  # model-specific params - pass them straight to the model/provider

        image_generation_config: Optional[BaseImageGenerationConfig] = None
        if (
            custom_llm_provider is not None
            and custom_llm_provider in LlmProviders._member_map_.values()
        ):
            image_generation_config = (
                ProviderConfigManager.get_provider_image_generation_config(
                    model=base_model or model,
                    provider=LlmProviders(custom_llm_provider),
                )
            )

        optional_params = get_optional_params_image_gen(
            model=base_model or model,
            n=n,
            quality=quality,
            response_format=response_format,
            size=size,
            style=style,
            user=user,
            custom_llm_provider=custom_llm_provider,
            provider_config=image_generation_config,
            **non_default_params,
        )

        litellm_params_dict = get_litellm_params(**kwargs)

        logging: Logging = litellm_logging_obj
        logging.update_environment_variables(
            model=model,
            user=user,
            optional_params=optional_params,
            litellm_params={
                "timeout": timeout,
                "azure": False,
                "litellm_call_id": litellm_call_id,
                "logger_fn": logger_fn,
                "proxy_server_request": proxy_server_request,
                "model_info": model_info,
                "metadata": metadata,
                "preset_cache_key": None,
                "stream_response": {},
            },
            custom_llm_provider=custom_llm_provider,
        )
        if "custom_llm_provider" not in logging.model_call_details:
            logging.model_call_details["custom_llm_provider"] = custom_llm_provider
        if mock_response is not None:
            return mock_image_generation(model=model, mock_response=mock_response)

        if custom_llm_provider == "azure":
            # azure configs
            api_type = get_secret_str("AZURE_API_TYPE") or "azure"

            api_base = api_base or litellm.api_base or get_secret_str("AZURE_API_BASE")

            api_version = (
                api_version
                or litellm.api_version
                or get_secret_str("AZURE_API_VERSION")
            )

            api_key = (
                api_key
                or litellm.api_key
                or litellm.azure_key
                or get_secret_str("AZURE_OPENAI_API_KEY")
                or get_secret_str("AZURE_API_KEY")
            )

            azure_ad_token = optional_params.pop(
                "azure_ad_token", None
            ) or get_secret_str("AZURE_AD_TOKEN")

            default_headers = {
                "Content-Type": "application/json;",
                "api-key": api_key,
            }
            for k, v in default_headers.items():
                if k not in headers:
                    headers[k] = v

            model_response = azure_chat_completions.image_generation(
                model=model,
                prompt=prompt,
                timeout=timeout,
                api_key=api_key,
                api_base=api_base,
                azure_ad_token=azure_ad_token,
                azure_ad_token_provider=azure_ad_token_provider,
                logging_obj=litellm_logging_obj,
                optional_params=optional_params,
                model_response=model_response,
                api_version=api_version,
                aimg_generation=aimg_generation,
                client=client,
                headers=headers,
                litellm_params=litellm_params_dict,
            )
        elif (
            custom_llm_provider == "openai"
            or custom_llm_provider in litellm.openai_compatible_providers
        ):
            model_response = openai_chat_completions.image_generation(
                model=model,
                prompt=prompt,
                timeout=timeout,
                api_key=api_key or dynamic_api_key,
                api_base=api_base,
                logging_obj=litellm_logging_obj,
                optional_params=optional_params,
                model_response=model_response,
                aimg_generation=aimg_generation,
                client=client,
            )
        elif custom_llm_provider == "bedrock":
            if model is None:
                raise Exception("Model needs to be set for bedrock")
            model_response = bedrock_image_generation.image_generation(  # type: ignore
                model=model,
                prompt=prompt,
                timeout=timeout,
                logging_obj=litellm_logging_obj,
                optional_params=optional_params,
                model_response=model_response,
                aimg_generation=aimg_generation,
                client=client,
            )
        elif custom_llm_provider == "vertex_ai":
            vertex_ai_project = (
                optional_params.pop("vertex_project", None)
                or optional_params.pop("vertex_ai_project", None)
                or litellm.vertex_project
                or get_secret_str("VERTEXAI_PROJECT")
            )
            vertex_ai_location = (
                optional_params.pop("vertex_location", None)
                or optional_params.pop("vertex_ai_location", None)
                or litellm.vertex_location
                or get_secret_str("VERTEXAI_LOCATION")
            )
            vertex_credentials = (
                optional_params.pop("vertex_credentials", None)
                or optional_params.pop("vertex_ai_credentials", None)
                or get_secret_str("VERTEXAI_CREDENTIALS")
            )

            api_base = (
                api_base
                or litellm.api_base
                or get_secret_str("VERTEXAI_API_BASE")
                or get_secret_str("VERTEX_API_BASE")
            )

            model_response = vertex_image_generation.image_generation(
                model=model,
                prompt=prompt,
                timeout=timeout,
                logging_obj=litellm_logging_obj,
                optional_params=optional_params,
                model_response=model_response,
                vertex_project=vertex_ai_project,
                vertex_location=vertex_ai_location,
                vertex_credentials=vertex_credentials,
                aimg_generation=aimg_generation,
                api_base=api_base,
                client=client,
            )
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
            if aimg_generation is True:
                async_custom_client: Optional[AsyncHTTPHandler] = None
                if client is not None and isinstance(client, AsyncHTTPHandler):
                    async_custom_client = client

                ## CALL FUNCTION
                model_response = custom_handler.aimage_generation(  # type: ignore
                    model=model,
                    prompt=prompt,
                    api_key=api_key,
                    api_base=api_base,
                    model_response=model_response,
                    optional_params=optional_params,
                    logging_obj=litellm_logging_obj,
                    timeout=timeout,
                    client=async_custom_client,
                )
            else:
                custom_client: Optional[HTTPHandler] = None
                if client is not None and isinstance(client, HTTPHandler):
                    custom_client = client

                ## CALL FUNCTION
                model_response = custom_handler.image_generation(
                    model=model,
                    prompt=prompt,
                    api_key=api_key,
                    api_base=api_base,
                    model_response=model_response,
                    optional_params=optional_params,
                    logging_obj=litellm_logging_obj,
                    timeout=timeout,
                    client=custom_client,
                )

        return model_response
    except Exception as e:
        ## Map to OpenAI Exception
        raise exception_type(
            model=model,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=locals(),
            extra_kwargs=kwargs,
        )


@client
async def aimage_variation(*args, **kwargs) -> ImageResponse:
    """
    Asynchronously calls the `image_variation` function with the given arguments and keyword arguments.

    Parameters:
    - `args` (tuple): Positional arguments to be passed to the `image_variation` function.
    - `kwargs` (dict): Keyword arguments to be passed to the `image_variation` function.

    Returns:
    - `response` (Any): The response returned by the `image_variation` function.
    """
    loop = asyncio.get_event_loop()
    model = kwargs.get("model", None)
    custom_llm_provider = kwargs.get("custom_llm_provider", None)
    ### PASS ARGS TO Image Generation ###
    kwargs["async_call"] = True
    try:
        # Use a partial function to pass your keyword arguments
        func = partial(image_variation, *args, **kwargs)

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        if custom_llm_provider is None and model is not None:
            _, custom_llm_provider, _, _ = get_llm_provider(
                model=model, api_base=kwargs.get("api_base", None)
            )

        # Await normally
        init_response = await loop.run_in_executor(None, func_with_context)
        if isinstance(init_response, dict) or isinstance(
            init_response, ImageResponse
        ):  ## CACHING SCENARIO
            if isinstance(init_response, dict):
                init_response = ImageResponse(**init_response)
            response = init_response
        elif asyncio.iscoroutine(init_response):
            response = await init_response  # type: ignore
        else:
            # Call the synchronous function using run_in_executor
            response = await loop.run_in_executor(None, func_with_context)
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
def image_variation(
    image: FileTypes,
    model: str = "dall-e-2",  # set to dall-e-2 by default - like OpenAI.
    n: int = 1,
    response_format: Literal["url", "b64_json"] = "url",
    size: Optional[str] = None,
    user: Optional[str] = None,
    **kwargs,
) -> ImageResponse:
    # get non-default params
    client = kwargs.get("client", None)
    # get logging object
    litellm_logging_obj = cast(LiteLLMLoggingObj, kwargs.get("litellm_logging_obj"))

    # get the litellm params
    litellm_params = get_litellm_params(**kwargs)
    # get the custom llm provider
    model, custom_llm_provider, dynamic_api_key, api_base = get_llm_provider(
        model=model,
        custom_llm_provider=litellm_params.get("custom_llm_provider", None),
        api_base=litellm_params.get("api_base", None),
        api_key=litellm_params.get("api_key", None),
    )

    # route to the correct provider w/ the params
    try:
        llm_provider = LlmProviders(custom_llm_provider)
        image_variation_provider = LITELLM_IMAGE_VARIATION_PROVIDERS(llm_provider)
    except ValueError:
        raise ValueError(
            f"Invalid image variation provider: {custom_llm_provider}. Supported providers are: {LITELLM_IMAGE_VARIATION_PROVIDERS}"
        )
    model_response = ImageResponse()

    response: Optional[ImageResponse] = None

    provider_config = ProviderConfigManager.get_provider_model_info(
        model=model or "",  # openai defaults to dall-e-2
        provider=llm_provider,
    )

    if provider_config is None:
        raise ValueError(
            f"image variation provider has no known model info config - required for getting api keys, etc.: {custom_llm_provider}. Supported providers are: {LITELLM_IMAGE_VARIATION_PROVIDERS}"
        )

    api_key = provider_config.get_api_key(litellm_params.get("api_key", None))
    api_base = provider_config.get_api_base(litellm_params.get("api_base", None))

    if image_variation_provider == LITELLM_IMAGE_VARIATION_PROVIDERS.OPENAI:
        if api_key is None:
            raise ValueError("API key is required for OpenAI image variations")
        if api_base is None:
            raise ValueError("API base is required for OpenAI image variations")

        response = openai_image_variations.image_variations(
            model_response=model_response,
            api_key=api_key,
            api_base=api_base,
            model=model,
            image=image,
            timeout=litellm_params.get("timeout", None),
            custom_llm_provider=custom_llm_provider,
            logging_obj=litellm_logging_obj,
            optional_params={},
            litellm_params=litellm_params,
        )
    elif image_variation_provider == LITELLM_IMAGE_VARIATION_PROVIDERS.TOPAZ:
        if api_key is None:
            raise ValueError("API key is required for Topaz image variations")
        if api_base is None:
            raise ValueError("API base is required for Topaz image variations")

        response = base_llm_aiohttp_handler.image_variations(
            model_response=model_response,
            api_key=api_key,
            api_base=api_base,
            model=model,
            image=image,
            timeout=litellm_params.get("timeout", None) or DEFAULT_REQUEST_TIMEOUT,
            custom_llm_provider=custom_llm_provider,
            logging_obj=litellm_logging_obj,
            optional_params={},
            litellm_params=litellm_params,
            client=client,
        )

    # return the response
    if response is None:
        raise ValueError(
            f"Invalid image variation provider: {custom_llm_provider}. Supported providers are: {LITELLM_IMAGE_VARIATION_PROVIDERS}"
        )
    return response


@client
def image_edit(
    image: FileTypes,
    prompt: str,
    model: Optional[str] = None,
    mask: Optional[str] = None,
    n: Optional[int] = None,
    quality: Optional[Union[str, ImageGenerationRequestQuality]] = None,
    response_format: Optional[str] = None,
    size: Optional[str] = None,
    user: Optional[str] = None,
    # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
    # The extra values given here take precedence over values defined on the client or passed to this method.
    extra_headers: Optional[Dict[str, Any]] = None,
    extra_query: Optional[Dict[str, Any]] = None,
    extra_body: Optional[Dict[str, Any]] = None,
    timeout: Optional[Union[float, httpx.Timeout]] = None,
    # LiteLLM specific params,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
) -> Union[ImageResponse, Coroutine[Any, Any, ImageResponse]]:
    """
    Maps the image edit functionality, similar to OpenAI's images/edits endpoint.
    """
    local_vars = locals()
    try:
        litellm_logging_obj: LiteLLMLoggingObj = kwargs.get("litellm_logging_obj")  # type: ignore
        litellm_call_id: Optional[str] = kwargs.get("litellm_call_id", None)
        _is_async = kwargs.pop("async_call", False) is True

        # get llm provider logic
        litellm_params = GenericLiteLLMParams(**kwargs)
        model, custom_llm_provider, _, _ = get_llm_provider(
            model=model or DEFAULT_IMAGE_ENDPOINT_MODEL,
            custom_llm_provider=custom_llm_provider,
        )

        # get provider config
        image_edit_provider_config: Optional[
            BaseImageEditConfig
        ] = ProviderConfigManager.get_provider_image_edit_config(
            model=model,
            provider=litellm.LlmProviders(custom_llm_provider),
        )

        if image_edit_provider_config is None:
            raise ValueError(f"image edit is not supported for {custom_llm_provider}")

        local_vars.update(kwargs)
        # Get ImageEditOptionalRequestParams with only valid parameters
        image_edit_optional_params: ImageEditOptionalRequestParams = (
            ImageEditRequestUtils.get_requested_image_edit_optional_param(local_vars)
        )

        # Get optional parameters for the responses API
        image_edit_request_params: Dict = (
            ImageEditRequestUtils.get_optional_params_image_edit(
                model=model,
                image_edit_provider_config=image_edit_provider_config,
                image_edit_optional_params=image_edit_optional_params,
            )
        )

        # Pre Call logging
        litellm_logging_obj.update_environment_variables(
            model=model,
            user=user,
            optional_params=dict(image_edit_request_params),
            litellm_params={
                "litellm_call_id": litellm_call_id,
                **image_edit_request_params,
            },
            custom_llm_provider=custom_llm_provider,
        )

        # Call the handler with _is_async flag instead of directly calling the async handler
        return base_llm_http_handler.image_edit_handler(
            model=model,
            image=image,
            prompt=prompt,
            image_edit_provider_config=image_edit_provider_config,
            image_edit_optional_request_params=image_edit_request_params,
            custom_llm_provider=custom_llm_provider,
            litellm_params=litellm_params,
            logging_obj=litellm_logging_obj,
            extra_headers=extra_headers,
            extra_body=extra_body,
            timeout=timeout or DEFAULT_REQUEST_TIMEOUT,
            _is_async=_is_async,
            client=kwargs.get("client"),
        )

    except Exception as e:
        raise litellm.exception_type(
            model=model,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=local_vars,
            extra_kwargs=kwargs,
        )


@client
async def aimage_edit(
    image: FileTypes,
    model: str,
    prompt: str,
    mask: Optional[str] = None,
    n: Optional[int] = None,
    quality: Optional[Union[str, ImageGenerationRequestQuality]] = None,
    response_format: Optional[str] = None,
    size: Optional[str] = None,
    user: Optional[str] = None,
    # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
    # The extra values given here take precedence over values defined on the client or passed to this method.
    extra_headers: Optional[Dict[str, Any]] = None,
    extra_query: Optional[Dict[str, Any]] = None,
    extra_body: Optional[Dict[str, Any]] = None,
    timeout: Optional[Union[float, httpx.Timeout]] = None,
    # LiteLLM specific params,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
) -> ImageResponse:
    """
    Asynchronously calls the `image_edit` function with the given arguments and keyword arguments.

    Parameters:
    - `args` (tuple): Positional arguments to be passed to the `image_edit` function.
    - `kwargs` (dict): Keyword arguments to be passed to the `image_edit` function.

    Returns:
    - `response` (Any): The response returned by the `image_edit` function.
    """
    local_vars = locals()
    try:
        loop = asyncio.get_event_loop()
        kwargs["async_call"] = True

        # get custom llm provider so we can use this for mapping exceptions
        if custom_llm_provider is None:
            _, custom_llm_provider, _, _ = litellm.get_llm_provider(
                model=model, api_base=local_vars.get("base_url", None)
            )

        func = partial(
            image_edit,
            image=image,
            prompt=prompt,
            mask=mask,
            model=model,
            n=n,
            quality=quality,
            response_format=response_format,
            size=size,
            user=user,
            timeout=timeout,
            custom_llm_provider=custom_llm_provider,
            **kwargs,
        )

        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)

        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response

        return response
    except Exception as e:
        raise litellm.exception_type(
            model=model,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=local_vars,
            extra_kwargs=kwargs,
        )

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\text_service\transports\rest.py ===
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

import dataclasses
import json  # type: ignore
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, path_template, rest_helpers, rest_streaming
from google.api_core import exceptions as core_exceptions
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.auth.transport.requests import AuthorizedSession  # type: ignore
from google.protobuf import json_format
import grpc  # type: ignore
from requests import __version__ as requests_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore


from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.types import text_service

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO
from .base import TextServiceTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class TextServiceRestInterceptor:
    """Interceptor for TextService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the TextServiceRestTransport.

    .. code-block:: python
        class MyCustomTextServiceInterceptor(TextServiceRestInterceptor):
            def pre_batch_embed_text(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_batch_embed_text(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_count_text_tokens(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_count_text_tokens(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_embed_text(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_embed_text(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_generate_text(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_generate_text(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = TextServiceRestTransport(interceptor=MyCustomTextServiceInterceptor())
        client = TextServiceClient(transport=transport)


    """

    def pre_batch_embed_text(
        self,
        request: text_service.BatchEmbedTextRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[text_service.BatchEmbedTextRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for batch_embed_text

        Override in a subclass to manipulate the request or metadata
        before they are sent to the TextService server.
        """
        return request, metadata

    def post_batch_embed_text(
        self, response: text_service.BatchEmbedTextResponse
    ) -> text_service.BatchEmbedTextResponse:
        """Post-rpc interceptor for batch_embed_text

        Override in a subclass to manipulate the response
        after it is returned by the TextService server but before
        it is returned to user code.
        """
        return response

    def pre_count_text_tokens(
        self,
        request: text_service.CountTextTokensRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[text_service.CountTextTokensRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for count_text_tokens

        Override in a subclass to manipulate the request or metadata
        before they are sent to the TextService server.
        """
        return request, metadata

    def post_count_text_tokens(
        self, response: text_service.CountTextTokensResponse
    ) -> text_service.CountTextTokensResponse:
        """Post-rpc interceptor for count_text_tokens

        Override in a subclass to manipulate the response
        after it is returned by the TextService server but before
        it is returned to user code.
        """
        return response

    def pre_embed_text(
        self,
        request: text_service.EmbedTextRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[text_service.EmbedTextRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for embed_text

        Override in a subclass to manipulate the request or metadata
        before they are sent to the TextService server.
        """
        return request, metadata

    def post_embed_text(
        self, response: text_service.EmbedTextResponse
    ) -> text_service.EmbedTextResponse:
        """Post-rpc interceptor for embed_text

        Override in a subclass to manipulate the response
        after it is returned by the TextService server but before
        it is returned to user code.
        """
        return response

    def pre_generate_text(
        self,
        request: text_service.GenerateTextRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[text_service.GenerateTextRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for generate_text

        Override in a subclass to manipulate the request or metadata
        before they are sent to the TextService server.
        """
        return request, metadata

    def post_generate_text(
        self, response: text_service.GenerateTextResponse
    ) -> text_service.GenerateTextResponse:
        """Post-rpc interceptor for generate_text

        Override in a subclass to manipulate the response
        after it is returned by the TextService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class TextServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: TextServiceRestInterceptor


class TextServiceRestTransport(TextServiceTransport):
    """REST backend transport for TextService.

    API for using Generative Language Models (GLMs) trained to
    generate text.
    Also known as Large Language Models (LLM)s, these generate text
    given an input prompt from the user.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1

    """

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        url_scheme: str = "https",
        interceptor: Optional[TextServiceRestInterceptor] = None,
        api_audience: Optional[str] = None,
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'generativelanguage.googleapis.com').
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.

            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if ``channel`` is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if ``channel`` is provided.
            client_cert_source_for_mtls (Callable[[], Tuple[bytes, bytes]]): Client
                certificate to configure mutual TLS HTTP channel. It is ignored
                if ``channel`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you are developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
            url_scheme: the protocol scheme for the API endpoint.  Normally
                "https", but for testing or local servers,
                "http" can be specified.
        """
        # Run the base constructor
        # TODO(yon-mg): resolve other ctor params i.e. scopes, quota, etc.
        # TODO: When custom host (api_endpoint) is set, `scopes` must *also* be set on the
        # credentials object
        maybe_url_match = re.match("^(?P<scheme>http(?:s)?://)?(?P<host>.*)$", host)
        if maybe_url_match is None:
            raise ValueError(
                f"Unexpected hostname structure: {host}"
            )  # pragma: NO COVER

        url_match_items = maybe_url_match.groupdict()

        host = f"{url_scheme}://{host}" if not url_match_items["scheme"] else host

        super().__init__(
            host=host,
            credentials=credentials,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )
        self._session = AuthorizedSession(
            self._credentials, default_host=self.DEFAULT_HOST
        )
        if client_cert_source_for_mtls:
            self._session.configure_mtls_channel(client_cert_source_for_mtls)
        self._interceptor = interceptor or TextServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _BatchEmbedText(TextServiceRestStub):
        def __hash__(self):
            return hash("BatchEmbedText")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: text_service.BatchEmbedTextRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> text_service.BatchEmbedTextResponse:
            r"""Call the batch embed text method over HTTP.

            Args:
                request (~.text_service.BatchEmbedTextRequest):
                    The request object. Batch request to get a text embedding
                from the model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.text_service.BatchEmbedTextResponse:
                    The response to a EmbedTextRequest.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/{model=models/*}:batchEmbedText",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_batch_embed_text(
                request, metadata
            )
            pb_request = text_service.BatchEmbedTextRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = text_service.BatchEmbedTextResponse()
            pb_resp = text_service.BatchEmbedTextResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_batch_embed_text(resp)
            return resp

    class _CountTextTokens(TextServiceRestStub):
        def __hash__(self):
            return hash("CountTextTokens")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: text_service.CountTextTokensRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> text_service.CountTextTokensResponse:
            r"""Call the count text tokens method over HTTP.

            Args:
                request (~.text_service.CountTextTokensRequest):
                    The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.text_service.CountTextTokensResponse:
                    A response from ``CountTextTokens``.

                It returns the model's ``token_count`` for the
                ``prompt``.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/{model=models/*}:countTextTokens",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_count_text_tokens(
                request, metadata
            )
            pb_request = text_service.CountTextTokensRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = text_service.CountTextTokensResponse()
            pb_resp = text_service.CountTextTokensResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_count_text_tokens(resp)
            return resp

    class _EmbedText(TextServiceRestStub):
        def __hash__(self):
            return hash("EmbedText")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: text_service.EmbedTextRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> text_service.EmbedTextResponse:
            r"""Call the embed text method over HTTP.

            Args:
                request (~.text_service.EmbedTextRequest):
                    The request object. Request to get a text embedding from
                the model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.text_service.EmbedTextResponse:
                    The response to a EmbedTextRequest.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/{model=models/*}:embedText",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_embed_text(request, metadata)
            pb_request = text_service.EmbedTextRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = text_service.EmbedTextResponse()
            pb_resp = text_service.EmbedTextResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_embed_text(resp)
            return resp

    class _GenerateText(TextServiceRestStub):
        def __hash__(self):
            return hash("GenerateText")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: text_service.GenerateTextRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> text_service.GenerateTextResponse:
            r"""Call the generate text method over HTTP.

            Args:
                request (~.text_service.GenerateTextRequest):
                    The request object. Request to generate a text completion
                response from the model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.text_service.GenerateTextResponse:
                    The response from the model,
                including candidate completions.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/{model=models/*}:generateText",
                    "body": "*",
                },
                {
                    "method": "post",
                    "uri": "/v1beta/{model=tunedModels/*}:generateText",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_generate_text(request, metadata)
            pb_request = text_service.GenerateTextRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = text_service.GenerateTextResponse()
            pb_resp = text_service.GenerateTextResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_generate_text(resp)
            return resp

    @property
    def batch_embed_text(
        self,
    ) -> Callable[
        [text_service.BatchEmbedTextRequest], text_service.BatchEmbedTextResponse
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._BatchEmbedText(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def count_text_tokens(
        self,
    ) -> Callable[
        [text_service.CountTextTokensRequest], text_service.CountTextTokensResponse
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CountTextTokens(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def embed_text(
        self,
    ) -> Callable[[text_service.EmbedTextRequest], text_service.EmbedTextResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._EmbedText(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def generate_text(
        self,
    ) -> Callable[
        [text_service.GenerateTextRequest], text_service.GenerateTextResponse
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GenerateText(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("TextServiceRestTransport",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\text_service\transports\rest.py ===
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

import dataclasses
import json  # type: ignore
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, path_template, rest_helpers, rest_streaming
from google.api_core import exceptions as core_exceptions
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.auth.transport.requests import AuthorizedSession  # type: ignore
from google.protobuf import json_format
import grpc  # type: ignore
from requests import __version__ as requests_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore


from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1beta3.types import text_service

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO
from .base import TextServiceTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class TextServiceRestInterceptor:
    """Interceptor for TextService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the TextServiceRestTransport.

    .. code-block:: python
        class MyCustomTextServiceInterceptor(TextServiceRestInterceptor):
            def pre_batch_embed_text(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_batch_embed_text(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_count_text_tokens(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_count_text_tokens(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_embed_text(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_embed_text(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_generate_text(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_generate_text(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = TextServiceRestTransport(interceptor=MyCustomTextServiceInterceptor())
        client = TextServiceClient(transport=transport)


    """

    def pre_batch_embed_text(
        self,
        request: text_service.BatchEmbedTextRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[text_service.BatchEmbedTextRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for batch_embed_text

        Override in a subclass to manipulate the request or metadata
        before they are sent to the TextService server.
        """
        return request, metadata

    def post_batch_embed_text(
        self, response: text_service.BatchEmbedTextResponse
    ) -> text_service.BatchEmbedTextResponse:
        """Post-rpc interceptor for batch_embed_text

        Override in a subclass to manipulate the response
        after it is returned by the TextService server but before
        it is returned to user code.
        """
        return response

    def pre_count_text_tokens(
        self,
        request: text_service.CountTextTokensRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[text_service.CountTextTokensRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for count_text_tokens

        Override in a subclass to manipulate the request or metadata
        before they are sent to the TextService server.
        """
        return request, metadata

    def post_count_text_tokens(
        self, response: text_service.CountTextTokensResponse
    ) -> text_service.CountTextTokensResponse:
        """Post-rpc interceptor for count_text_tokens

        Override in a subclass to manipulate the response
        after it is returned by the TextService server but before
        it is returned to user code.
        """
        return response

    def pre_embed_text(
        self,
        request: text_service.EmbedTextRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[text_service.EmbedTextRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for embed_text

        Override in a subclass to manipulate the request or metadata
        before they are sent to the TextService server.
        """
        return request, metadata

    def post_embed_text(
        self, response: text_service.EmbedTextResponse
    ) -> text_service.EmbedTextResponse:
        """Post-rpc interceptor for embed_text

        Override in a subclass to manipulate the response
        after it is returned by the TextService server but before
        it is returned to user code.
        """
        return response

    def pre_generate_text(
        self,
        request: text_service.GenerateTextRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[text_service.GenerateTextRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for generate_text

        Override in a subclass to manipulate the request or metadata
        before they are sent to the TextService server.
        """
        return request, metadata

    def post_generate_text(
        self, response: text_service.GenerateTextResponse
    ) -> text_service.GenerateTextResponse:
        """Post-rpc interceptor for generate_text

        Override in a subclass to manipulate the response
        after it is returned by the TextService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class TextServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: TextServiceRestInterceptor


class TextServiceRestTransport(TextServiceTransport):
    """REST backend transport for TextService.

    API for using Generative Language Models (GLMs) trained to
    generate text.
    Also known as Large Language Models (LLM)s, these generate text
    given an input prompt from the user.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1

    """

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        url_scheme: str = "https",
        interceptor: Optional[TextServiceRestInterceptor] = None,
        api_audience: Optional[str] = None,
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'generativelanguage.googleapis.com').
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.

            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if ``channel`` is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if ``channel`` is provided.
            client_cert_source_for_mtls (Callable[[], Tuple[bytes, bytes]]): Client
                certificate to configure mutual TLS HTTP channel. It is ignored
                if ``channel`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you are developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
            url_scheme: the protocol scheme for the API endpoint.  Normally
                "https", but for testing or local servers,
                "http" can be specified.
        """
        # Run the base constructor
        # TODO(yon-mg): resolve other ctor params i.e. scopes, quota, etc.
        # TODO: When custom host (api_endpoint) is set, `scopes` must *also* be set on the
        # credentials object
        maybe_url_match = re.match("^(?P<scheme>http(?:s)?://)?(?P<host>.*)$", host)
        if maybe_url_match is None:
            raise ValueError(
                f"Unexpected hostname structure: {host}"
            )  # pragma: NO COVER

        url_match_items = maybe_url_match.groupdict()

        host = f"{url_scheme}://{host}" if not url_match_items["scheme"] else host

        super().__init__(
            host=host,
            credentials=credentials,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )
        self._session = AuthorizedSession(
            self._credentials, default_host=self.DEFAULT_HOST
        )
        if client_cert_source_for_mtls:
            self._session.configure_mtls_channel(client_cert_source_for_mtls)
        self._interceptor = interceptor or TextServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _BatchEmbedText(TextServiceRestStub):
        def __hash__(self):
            return hash("BatchEmbedText")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: text_service.BatchEmbedTextRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> text_service.BatchEmbedTextResponse:
            r"""Call the batch embed text method over HTTP.

            Args:
                request (~.text_service.BatchEmbedTextRequest):
                    The request object. Batch request to get a text embedding
                from the model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.text_service.BatchEmbedTextResponse:
                    The response to a EmbedTextRequest.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta3/{model=models/*}:batchEmbedText",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_batch_embed_text(
                request, metadata
            )
            pb_request = text_service.BatchEmbedTextRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = text_service.BatchEmbedTextResponse()
            pb_resp = text_service.BatchEmbedTextResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_batch_embed_text(resp)
            return resp

    class _CountTextTokens(TextServiceRestStub):
        def __hash__(self):
            return hash("CountTextTokens")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: text_service.CountTextTokensRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> text_service.CountTextTokensResponse:
            r"""Call the count text tokens method over HTTP.

            Args:
                request (~.text_service.CountTextTokensRequest):
                    The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.text_service.CountTextTokensResponse:
                    A response from ``CountTextTokens``.

                It returns the model's ``token_count`` for the
                ``prompt``.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta3/{model=models/*}:countTextTokens",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_count_text_tokens(
                request, metadata
            )
            pb_request = text_service.CountTextTokensRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = text_service.CountTextTokensResponse()
            pb_resp = text_service.CountTextTokensResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_count_text_tokens(resp)
            return resp

    class _EmbedText(TextServiceRestStub):
        def __hash__(self):
            return hash("EmbedText")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: text_service.EmbedTextRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> text_service.EmbedTextResponse:
            r"""Call the embed text method over HTTP.

            Args:
                request (~.text_service.EmbedTextRequest):
                    The request object. Request to get a text embedding from
                the model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.text_service.EmbedTextResponse:
                    The response to a EmbedTextRequest.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta3/{model=models/*}:embedText",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_embed_text(request, metadata)
            pb_request = text_service.EmbedTextRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = text_service.EmbedTextResponse()
            pb_resp = text_service.EmbedTextResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_embed_text(resp)
            return resp

    class _GenerateText(TextServiceRestStub):
        def __hash__(self):
            return hash("GenerateText")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: text_service.GenerateTextRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> text_service.GenerateTextResponse:
            r"""Call the generate text method over HTTP.

            Args:
                request (~.text_service.GenerateTextRequest):
                    The request object. Request to generate a text completion
                response from the model.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.text_service.GenerateTextResponse:
                    The response from the model,
                including candidate completions.

            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta3/{model=models/*}:generateText",
                    "body": "*",
                },
                {
                    "method": "post",
                    "uri": "/v1beta3/{model=tunedModels/*}:generateText",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_generate_text(request, metadata)
            pb_request = text_service.GenerateTextRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = text_service.GenerateTextResponse()
            pb_resp = text_service.GenerateTextResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_generate_text(resp)
            return resp

    @property
    def batch_embed_text(
        self,
    ) -> Callable[
        [text_service.BatchEmbedTextRequest], text_service.BatchEmbedTextResponse
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._BatchEmbedText(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def count_text_tokens(
        self,
    ) -> Callable[
        [text_service.CountTextTokensRequest], text_service.CountTextTokensResponse
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CountTextTokens(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def embed_text(
        self,
    ) -> Callable[[text_service.EmbedTextRequest], text_service.EmbedTextResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._EmbedText(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def generate_text(
        self,
    ) -> Callable[
        [text_service.GenerateTextRequest], text_service.GenerateTextResponse
    ]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GenerateText(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("TextServiceRestTransport",)

# === NexusCore/openenv\Scripts\pywin32_postinstall.py ===
# postinstall script for pywin32
#
# copies pywintypesXX.dll and pythoncomXX.dll into the system directory,
# and creates a pth file
import argparse
import glob
import os
import shutil
import sys
import sysconfig
import tempfile
import winreg

tee_f = open(
    os.path.join(
        tempfile.gettempdir(),  # Send output somewhere so it can be found if necessary...
        "pywin32_postinstall.log",
    ),
    "w",
)


class Tee:
    def __init__(self, file):
        self.f = file

    def write(self, what):
        if self.f is not None:
            try:
                self.f.write(what.replace("\n", "\r\n"))
            except OSError:
                pass
        tee_f.write(what)

    def flush(self):
        if self.f is not None:
            try:
                self.f.flush()
            except OSError:
                pass
        tee_f.flush()


sys.stderr = Tee(sys.stderr)
sys.stdout = Tee(sys.stdout)

com_modules = [
    # module_name,                      class_names
    ("win32com.servers.interp", "Interpreter"),
    ("win32com.servers.dictionary", "DictionaryPolicy"),
    ("win32com.axscript.client.pyscript", "PyScript"),
]

# Is this a 'silent' install - ie, avoid all dialogs.
# Different than 'verbose'
silent = 0

# Verbosity of output messages.
verbose = 1

root_key_name = "Software\\Python\\PythonCore\\" + sys.winver


def get_root_hkey():
    try:
        winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, root_key_name, 0, winreg.KEY_CREATE_SUB_KEY
        )
        return winreg.HKEY_LOCAL_MACHINE
    except OSError:
        # Either not exist, or no permissions to create subkey means
        # must be HKCU
        return winreg.HKEY_CURRENT_USER


# Create a function with the same signature as create_shortcut
# previously provided by bdist_wininst
def create_shortcut(
    path, description, filename, arguments="", workdir="", iconpath="", iconindex=0
):
    import pythoncom
    from win32com.shell import shell

    ilink = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink,
        None,
        pythoncom.CLSCTX_INPROC_SERVER,
        shell.IID_IShellLink,
    )
    ilink.SetPath(path)
    ilink.SetDescription(description)
    if arguments:
        ilink.SetArguments(arguments)
    if workdir:
        ilink.SetWorkingDirectory(workdir)
    if iconpath or iconindex:
        ilink.SetIconLocation(iconpath, iconindex)
    # now save it.
    ipf = ilink.QueryInterface(pythoncom.IID_IPersistFile)
    ipf.Save(filename, 0)


# Support the same list of "path names" as bdist_wininst used to
def get_special_folder_path(path_name):
    from win32com.shell import shell, shellcon

    for maybe in """
        CSIDL_COMMON_STARTMENU CSIDL_STARTMENU CSIDL_COMMON_APPDATA
        CSIDL_LOCAL_APPDATA CSIDL_APPDATA CSIDL_COMMON_DESKTOPDIRECTORY
        CSIDL_DESKTOPDIRECTORY CSIDL_COMMON_STARTUP CSIDL_STARTUP
        CSIDL_COMMON_PROGRAMS CSIDL_PROGRAMS CSIDL_PROGRAM_FILES_COMMON
        CSIDL_PROGRAM_FILES CSIDL_FONTS""".split():
        if maybe == path_name:
            csidl = getattr(shellcon, maybe)
            return shell.SHGetSpecialFolderPath(0, csidl, False)
    raise ValueError(f"{path_name} is an unknown path ID")


def CopyTo(desc, src, dest):
    import win32api
    import win32con

    while 1:
        try:
            win32api.CopyFile(src, dest, 0)
            return
        except win32api.error as details:
            if details.winerror == 5:  # access denied - user not admin.
                raise
            if silent:
                # Running silent mode - just re-raise the error.
                raise
            full_desc = (
                f"Error {desc}\n\n"
                "If you have any Python applications running, "
                f"please close them now\nand select 'Retry'\n\n{details.strerror}"
            )
            rc = win32api.MessageBox(
                0, full_desc, "Installation Error", win32con.MB_ABORTRETRYIGNORE
            )
            if rc == win32con.IDABORT:
                raise
            elif rc == win32con.IDIGNORE:
                return
            # else retry - around we go again.


# We need to import win32api to determine the Windows system directory,
# so we can copy our system files there - but importing win32api will
# load the pywintypes.dll already in the system directory preventing us
# from updating them!
# So, we pull the same trick pywintypes.py does, but it loads from
# our pywintypes_system32 directory.
def LoadSystemModule(lib_dir, modname):
    # See if this is a debug build.
    import importlib.machinery
    import importlib.util

    suffix = "_d" if "_d.pyd" in importlib.machinery.EXTENSION_SUFFIXES else ""
    filename = "%s%d%d%s.dll" % (
        modname,
        sys.version_info.major,
        sys.version_info.minor,
        suffix,
    )
    filename = os.path.join(lib_dir, "pywin32_system32", filename)
    loader = importlib.machinery.ExtensionFileLoader(modname, filename)
    spec = importlib.machinery.ModuleSpec(name=modname, loader=loader, origin=filename)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)


def SetPyKeyVal(key_name, value_name, value):
    root_hkey = get_root_hkey()
    root_key = winreg.OpenKey(root_hkey, root_key_name)
    try:
        my_key = winreg.CreateKey(root_key, key_name)
        try:
            winreg.SetValueEx(my_key, value_name, 0, winreg.REG_SZ, value)
            if verbose:
                print(f"-> {root_key_name}\\{key_name}[{value_name}]={value!r}")
        finally:
            my_key.Close()
    finally:
        root_key.Close()


def UnsetPyKeyVal(key_name, value_name, delete_key=False):
    root_hkey = get_root_hkey()
    root_key = winreg.OpenKey(root_hkey, root_key_name)
    try:
        my_key = winreg.OpenKey(root_key, key_name, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(my_key, value_name)
            if verbose:
                print(f"-> DELETE {root_key_name}\\{key_name}[{value_name}]")
        finally:
            my_key.Close()
        if delete_key:
            winreg.DeleteKey(root_key, key_name)
            if verbose:
                print(f"-> DELETE {root_key_name}\\{key_name}")
    except OSError as why:
        winerror = getattr(why, "winerror", why.errno)
        if winerror != 2:  # file not found
            raise
    finally:
        root_key.Close()


def RegisterCOMObjects(register=True):
    import win32com.server.register

    if register:
        func = win32com.server.register.RegisterClasses
    else:
        func = win32com.server.register.UnregisterClasses
    flags = {}
    if not verbose:
        flags["quiet"] = 1
    for module, klass_name in com_modules:
        __import__(module)
        mod = sys.modules[module]
        flags["finalize_register"] = getattr(mod, "DllRegisterServer", None)
        flags["finalize_unregister"] = getattr(mod, "DllUnregisterServer", None)
        klass = getattr(mod, klass_name)
        func(klass, **flags)


def RegisterHelpFile(register=True, lib_dir=None):
    if lib_dir is None:
        lib_dir = sysconfig.get_paths()["platlib"]
    if register:
        # Register the .chm help file.
        chm_file = os.path.join(lib_dir, "PyWin32.chm")
        if os.path.isfile(chm_file):
            # This isn't recursive, so if 'Help' doesn't exist, we croak
            SetPyKeyVal("Help", None, None)
            SetPyKeyVal("Help\\Pythonwin Reference", None, chm_file)
            return chm_file
        else:
            print("NOTE: PyWin32.chm can not be located, so has not been registered")
    else:
        UnsetPyKeyVal("Help\\Pythonwin Reference", None, delete_key=True)
    return None


def RegisterPythonwin(register=True, lib_dir=None):
    """Add (or remove) Pythonwin to context menu for python scripts.
    ??? Should probably also add Edit command for pys files also.
    Also need to remove these keys on uninstall, but there's no function
    to add registry entries to uninstall log ???
    """
    import os

    if lib_dir is None:
        lib_dir = sysconfig.get_paths()["platlib"]
    classes_root = get_root_hkey()
    ## Installer executable doesn't seem to pass anything to postinstall script indicating if it's a debug build
    pythonwin_exe = os.path.join(lib_dir, "Pythonwin", "Pythonwin.exe")
    pythonwin_edit_command = pythonwin_exe + ' -edit "%1"'

    keys_vals = [
        (
            "Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\Pythonwin.exe",
            "",
            pythonwin_exe,
        ),
        (
            "Software\\Classes\\Python.File\\shell\\Edit with Pythonwin",
            "command",
            pythonwin_edit_command,
        ),
        (
            "Software\\Classes\\Python.NoConFile\\shell\\Edit with Pythonwin",
            "command",
            pythonwin_edit_command,
        ),
    ]

    try:
        if register:
            for key, sub_key, val in keys_vals:
                ## Since winreg only uses the character Api functions, this can fail if Python
                ##  is installed to a path containing non-ascii characters
                hkey = winreg.CreateKey(classes_root, key)
                if sub_key:
                    hkey = winreg.CreateKey(hkey, sub_key)
                winreg.SetValueEx(hkey, None, 0, winreg.REG_SZ, val)
                hkey.Close()
        else:
            for key, sub_key, val in keys_vals:
                try:
                    if sub_key:
                        hkey = winreg.OpenKey(classes_root, key)
                        winreg.DeleteKey(hkey, sub_key)
                        hkey.Close()
                    winreg.DeleteKey(classes_root, key)
                except OSError as why:
                    winerror = getattr(why, "winerror", why.errno)
                    if winerror != 2:  # file not found
                        raise
    finally:
        # tell windows about the change
        from win32com.shell import shell, shellcon

        shell.SHChangeNotify(
            shellcon.SHCNE_ASSOCCHANGED, shellcon.SHCNF_IDLIST, None, None
        )


def get_shortcuts_folder():
    if get_root_hkey() == winreg.HKEY_LOCAL_MACHINE:
        try:
            fldr = get_special_folder_path("CSIDL_COMMON_PROGRAMS")
        except OSError:
            # No CSIDL_COMMON_PROGRAMS on this platform
            fldr = get_special_folder_path("CSIDL_PROGRAMS")
    else:
        # non-admin install - always goes in this user's start menu.
        fldr = get_special_folder_path("CSIDL_PROGRAMS")

    try:
        install_group = winreg.QueryValue(
            get_root_hkey(), root_key_name + "\\InstallPath\\InstallGroup"
        )
    except OSError:
        install_group = "Python %d.%d" % (
            sys.version_info.major,
            sys.version_info.minor,
        )
    return os.path.join(fldr, install_group)


# Get the system directory, which may be the Wow64 directory if we are a 32bit
# python on a 64bit OS.
def get_system_dir():
    import win32api  # we assume this exists.

    try:
        import pythoncom
        import win32process
        from win32com.shell import shell, shellcon

        try:
            if win32process.IsWow64Process():
                return shell.SHGetSpecialFolderPath(0, shellcon.CSIDL_SYSTEMX86)
            return shell.SHGetSpecialFolderPath(0, shellcon.CSIDL_SYSTEM)
        except (pythoncom.com_error, win32process.error):
            return win32api.GetSystemDirectory()
    except ImportError:
        return win32api.GetSystemDirectory()


def fixup_dbi():
    # We used to have a dbi.pyd with our .pyd files, but now have a .py file.
    # If the user didn't uninstall, they will find the .pyd which will cause
    # problems - so handle that.
    import win32api
    import win32con

    pyd_name = os.path.join(os.path.dirname(win32api.__file__), "dbi.pyd")
    pyd_d_name = os.path.join(os.path.dirname(win32api.__file__), "dbi_d.pyd")
    py_name = os.path.join(os.path.dirname(win32con.__file__), "dbi.py")
    for this_pyd in (pyd_name, pyd_d_name):
        this_dest = this_pyd + ".old"
        if os.path.isfile(this_pyd) and os.path.isfile(py_name):
            try:
                if os.path.isfile(this_dest):
                    print(
                        f"Old dbi '{this_dest}' already exists - deleting '{this_pyd}'"
                    )
                    os.remove(this_pyd)
                else:
                    os.rename(this_pyd, this_dest)
                    print(f"renamed '{this_pyd}'->'{this_pyd}.old'")
            except OSError as exc:
                print(f"FAILED to rename '{this_pyd}': {exc}")


def install(lib_dir):
    import traceback

    # The .pth file is now installed as a regular file.
    # Create the .pth file in the site-packages dir, and use only relative paths
    # We used to write a .pth directly to sys.prefix - clobber it.
    if os.path.isfile(os.path.join(sys.prefix, "pywin32.pth")):
        os.unlink(os.path.join(sys.prefix, "pywin32.pth"))
    # The .pth may be new and therefore not loaded in this session.
    # Setup the paths just in case.
    for name in "win32 win32\\lib Pythonwin".split():
        sys.path.append(os.path.join(lib_dir, name))
    # It is possible people with old versions installed with still have
    # pywintypes and pythoncom registered.  We no longer need this, and stale
    # entries hurt us.
    for name in "pythoncom pywintypes".split():
        keyname = "Software\\Python\\PythonCore\\" + sys.winver + "\\Modules\\" + name
        for root in winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER:
            try:
                winreg.DeleteKey(root, keyname + "\\Debug")
            except OSError:
                pass
            try:
                winreg.DeleteKey(root, keyname)
            except OSError:
                pass
    LoadSystemModule(lib_dir, "pywintypes")
    LoadSystemModule(lib_dir, "pythoncom")
    import win32api

    # and now we can get the system directory:
    files = glob.glob(os.path.join(lib_dir, "pywin32_system32\\*.*"))
    if not files:
        raise RuntimeError("No system files to copy!!")
    # Try the system32 directory first - if that fails due to "access denied",
    # it implies a non-admin user, and we use sys.prefix
    for dest_dir in [get_system_dir(), sys.prefix]:
        # and copy some files over there
        worked = 0
        try:
            for fname in files:
                base = os.path.basename(fname)
                dst = os.path.join(dest_dir, base)
                CopyTo("installing %s" % base, fname, dst)
                if verbose:
                    print(f"Copied {base} to {dst}")
                worked = 1
                # Nuke any other versions that may exist - having
                # duplicates causes major headaches.
                bad_dest_dirs = [
                    os.path.join(sys.prefix, "Library\\bin"),
                    os.path.join(sys.prefix, "Lib\\site-packages\\win32"),
                ]
                if dest_dir != sys.prefix:
                    bad_dest_dirs.append(sys.prefix)
                for bad_dest_dir in bad_dest_dirs:
                    bad_fname = os.path.join(bad_dest_dir, base)
                    if os.path.exists(bad_fname):
                        # let exceptions go here - delete must succeed
                        os.unlink(bad_fname)
            if worked:
                break
        except win32api.error as details:
            if details.winerror == 5:
                # access denied - user not admin - try sys.prefix dir,
                # but first check that a version doesn't already exist
                # in that place - otherwise that one will still get used!
                if os.path.exists(dst):
                    msg = (
                        "The file '%s' exists, but can not be replaced "
                        "due to insufficient permissions.  You must "
                        "reinstall this software as an Administrator" % dst
                    )
                    print(msg)
                    raise RuntimeError(msg)
                continue
            raise
    else:
        raise RuntimeError(
            "You don't have enough permissions to install the system files"
        )

    # Register our demo COM objects.
    try:
        try:
            RegisterCOMObjects()
        except win32api.error as details:
            if details.winerror != 5:  # ERROR_ACCESS_DENIED
                raise
            print("You do not have the permissions to install COM objects.")
            print("The sample COM objects were not registered.")
    except Exception:
        print("FAILED to register the Python COM objects")
        traceback.print_exc()

    # There may be no main Python key in HKCU if, eg, an admin installed
    # python itself.
    winreg.CreateKey(get_root_hkey(), root_key_name)

    chm_file = None
    try:
        chm_file = RegisterHelpFile(True, lib_dir)
    except Exception:
        print("Failed to register help file")
        traceback.print_exc()
    else:
        if verbose:
            print("Registered help file")

    # misc other fixups.
    fixup_dbi()

    # Register Pythonwin in context menu
    try:
        RegisterPythonwin(True, lib_dir)
    except Exception:
        print("Failed to register pythonwin as editor")
        traceback.print_exc()
    else:
        if verbose:
            print("Pythonwin has been registered in context menu")

    # Create the win32com\gen_py directory.
    make_dir = os.path.join(lib_dir, "win32com", "gen_py")
    if not os.path.isdir(make_dir):
        if verbose:
            print(f"Creating directory {make_dir}")
        os.mkdir(make_dir)

    try:
        # create shortcuts
        # CSIDL_COMMON_PROGRAMS only available works on NT/2000/XP, and
        # will fail there if the user has no admin rights.
        fldr = get_shortcuts_folder()
        # If the group doesn't exist, then we don't make shortcuts - its
        # possible that this isn't a "normal" install.
        if os.path.isdir(fldr):
            dst = os.path.join(fldr, "PythonWin.lnk")
            create_shortcut(
                os.path.join(lib_dir, "Pythonwin\\Pythonwin.exe"),
                "The Pythonwin IDE",
                dst,
                "",
                sys.prefix,
            )
            if verbose:
                print("Shortcut for Pythonwin created")
            # And the docs.
            if chm_file:
                dst = os.path.join(fldr, "Python for Windows Documentation.lnk")
                doc = "Documentation for the PyWin32 extensions"
                create_shortcut(chm_file, doc, dst)
                if verbose:
                    print("Shortcut to documentation created")
        else:
            if verbose:
                print(f"Can't install shortcuts - {fldr!r} is not a folder")
    except Exception as details:
        print(details)

    # importing win32com.client ensures the gen_py dir created - not strictly
    # necessary to do now, but this makes the installation "complete"
    try:
        import win32com.client  # noqa
    except ImportError:
        # Don't let this error sound fatal
        pass
    print("The pywin32 extensions were successfully installed.")


def uninstall(lib_dir):
    # First ensure our system modules are loaded from pywin32_system, so
    # we can remove the ones we copied...
    LoadSystemModule(lib_dir, "pywintypes")
    LoadSystemModule(lib_dir, "pythoncom")

    try:
        RegisterCOMObjects(False)
    except Exception as why:
        print(f"Failed to unregister COM objects: {why}")

    try:
        RegisterHelpFile(False, lib_dir)
    except Exception as why:
        print(f"Failed to unregister help file: {why}")
    else:
        if verbose:
            print("Unregistered help file")

    try:
        RegisterPythonwin(False, lib_dir)
    except Exception as why:
        print(f"Failed to unregister Pythonwin: {why}")
    else:
        if verbose:
            print("Unregistered Pythonwin")

    try:
        # remove gen_py directory.
        gen_dir = os.path.join(lib_dir, "win32com", "gen_py")
        if os.path.isdir(gen_dir):
            shutil.rmtree(gen_dir)
            if verbose:
                print(f"Removed directory {gen_dir}")

        # Remove pythonwin compiled "config" files.
        pywin_dir = os.path.join(lib_dir, "Pythonwin", "pywin")
        for fname in glob.glob(os.path.join(pywin_dir, "*.cfc")):
            os.remove(fname)

        # The dbi.pyd.old files we may have created.
        try:
            os.remove(os.path.join(lib_dir, "win32", "dbi.pyd.old"))
        except OSError:
            pass
        try:
            os.remove(os.path.join(lib_dir, "win32", "dbi_d.pyd.old"))
        except OSError:
            pass

    except Exception as why:
        print(f"Failed to remove misc files: {why}")

    try:
        fldr = get_shortcuts_folder()
        for link in ("PythonWin.lnk", "Python for Windows Documentation.lnk"):
            fqlink = os.path.join(fldr, link)
            if os.path.isfile(fqlink):
                os.remove(fqlink)
                if verbose:
                    print(f"Removed {link}")
    except Exception as why:
        print(f"Failed to remove shortcuts: {why}")
    # Now remove the system32 files.
    files = glob.glob(os.path.join(lib_dir, "pywin32_system32\\*.*"))
    # Try the system32 directory first - if that fails due to "access denied",
    # it implies a non-admin user, and we use sys.prefix
    try:
        for dest_dir in [get_system_dir(), sys.prefix]:
            # and copy some files over there
            worked = 0
            for fname in files:
                base = os.path.basename(fname)
                dst = os.path.join(dest_dir, base)
                if os.path.isfile(dst):
                    try:
                        os.remove(dst)
                        worked = 1
                        if verbose:
                            print("Removed file %s" % (dst))
                    except Exception:
                        print(f"FAILED to remove {dst}")
            if worked:
                break
    except Exception as why:
        print(f"FAILED to remove system files: {why}")


# NOTE: This used to be run from inside the bdist_wininst created binary un/installer.
# From inside the binary installer this script HAD to NOT
# call sys.exit() or raise SystemExit, otherwise the installer would also terminate!
# Out of principle, we're still not using system exits.


def verify_destination(location: str) -> str:
    location = os.path.abspath(location)
    if not os.path.isdir(location):
        raise argparse.ArgumentTypeError(
            f'Path "{location}" is not an existing directory!'
        )
    return location


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""A post-install script for the pywin32 extensions.

    * Typical usage:

    > python -m pywin32_postinstall -install

    * or (shorter but you don't have control over which python environment is used)

    > pywin32_postinstall -install

    You need to execute this script, with a '-install' parameter,
    to ensure the environment is setup correctly to install COM objects, services, etc.
    """,
    )
    parser.add_argument(
        "-install",
        default=False,
        action="store_true",
        help="Configure the Python environment correctly for pywin32.",
    )
    parser.add_argument(
        "-remove",
        default=False,
        action="store_true",
        help="Try and remove everything that was installed or copied.",
    )
    parser.add_argument(
        "-wait",
        type=int,
        help="Wait for the specified process to terminate before starting.",
    )
    parser.add_argument(
        "-silent",
        default=False,
        action="store_true",
        help='Don\'t display the "Abort/Retry/Ignore" dialog for files in use.',
    )
    parser.add_argument(
        "-quiet",
        default=False,
        action="store_true",
        help="Don't display progress messages.",
    )
    parser.add_argument(
        "-destination",
        default=sysconfig.get_paths()["platlib"],
        type=verify_destination,
        help="Location of the PyWin32 installation",
    )

    args = parser.parse_args()

    if not args.quiet:
        print(f"Parsed arguments are: {args}")

    if not args.install ^ args.remove:
        parser.error("You need to either choose to -install or -remove!")

    if args.wait is not None:
        try:
            os.waitpid(args.wait, 0)
        except OSError:
            # child already dead
            pass

    silent = args.silent
    verbose = not args.quiet

    if args.install:
        install(args.destination)

    if args.remove:
        uninstall(args.destination)


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\sortedcontainers\sortedset.py ===
"""Sorted Set
=============

:doc:`Sorted Containers<index>` is an Apache2 licensed Python sorted
collections library, written in pure-Python, and fast as C-extensions. The
:doc:`introduction<introduction>` is the best way to get started.

Sorted set implementations:

.. currentmodule:: sortedcontainers

* :class:`SortedSet`

"""

from itertools import chain
from operator import eq, ne, gt, ge, lt, le
from textwrap import dedent

from .sortedlist import SortedList, recursive_repr

###############################################################################
# BEGIN Python 2/3 Shims
###############################################################################

try:
    from collections.abc import MutableSet, Sequence, Set
except ImportError:
    from collections import MutableSet, Sequence, Set

###############################################################################
# END Python 2/3 Shims
###############################################################################


class SortedSet(MutableSet, Sequence):
    """Sorted set is a sorted mutable set.

    Sorted set values are maintained in sorted order. The design of sorted set
    is simple: sorted set uses a set for set-operations and maintains a sorted
    list of values.

    Sorted set values must be hashable and comparable. The hash and total
    ordering of values must not change while they are stored in the sorted set.

    Mutable set methods:

    * :func:`SortedSet.__contains__`
    * :func:`SortedSet.__iter__`
    * :func:`SortedSet.__len__`
    * :func:`SortedSet.add`
    * :func:`SortedSet.discard`

    Sequence methods:

    * :func:`SortedSet.__getitem__`
    * :func:`SortedSet.__delitem__`
    * :func:`SortedSet.__reversed__`

    Methods for removing values:

    * :func:`SortedSet.clear`
    * :func:`SortedSet.pop`
    * :func:`SortedSet.remove`

    Set-operation methods:

    * :func:`SortedSet.difference`
    * :func:`SortedSet.difference_update`
    * :func:`SortedSet.intersection`
    * :func:`SortedSet.intersection_update`
    * :func:`SortedSet.symmetric_difference`
    * :func:`SortedSet.symmetric_difference_update`
    * :func:`SortedSet.union`
    * :func:`SortedSet.update`

    Methods for miscellany:

    * :func:`SortedSet.copy`
    * :func:`SortedSet.count`
    * :func:`SortedSet.__repr__`
    * :func:`SortedSet._check`

    Sorted list methods available:

    * :func:`SortedList.bisect_left`
    * :func:`SortedList.bisect_right`
    * :func:`SortedList.index`
    * :func:`SortedList.irange`
    * :func:`SortedList.islice`
    * :func:`SortedList._reset`

    Additional sorted list methods available, if key-function used:

    * :func:`SortedKeyList.bisect_key_left`
    * :func:`SortedKeyList.bisect_key_right`
    * :func:`SortedKeyList.irange_key`

    Sorted set comparisons use subset and superset relations. Two sorted sets
    are equal if and only if every element of each sorted set is contained in
    the other (each is a subset of the other). A sorted set is less than
    another sorted set if and only if the first sorted set is a proper subset
    of the second sorted set (is a subset, but is not equal). A sorted set is
    greater than another sorted set if and only if the first sorted set is a
    proper superset of the second sorted set (is a superset, but is not equal).

    """
    def __init__(self, iterable=None, key=None):
        """Initialize sorted set instance.

        Optional `iterable` argument provides an initial iterable of values to
        initialize the sorted set.

        Optional `key` argument defines a callable that, like the `key`
        argument to Python's `sorted` function, extracts a comparison key from
        each value. The default, none, compares values directly.

        Runtime complexity: `O(n*log(n))`

        >>> ss = SortedSet([3, 1, 2, 5, 4])
        >>> ss
        SortedSet([1, 2, 3, 4, 5])
        >>> from operator import neg
        >>> ss = SortedSet([3, 1, 2, 5, 4], neg)
        >>> ss
        SortedSet([5, 4, 3, 2, 1], key=<built-in function neg>)

        :param iterable: initial values (optional)
        :param key: function used to extract comparison key (optional)

        """
        self._key = key

        # SortedSet._fromset calls SortedSet.__init__ after initializing the
        # _set attribute. So only create a new set if the _set attribute is not
        # already present.

        if not hasattr(self, '_set'):
            self._set = set()

        self._list = SortedList(self._set, key=key)

        # Expose some set methods publicly.

        _set = self._set
        self.isdisjoint = _set.isdisjoint
        self.issubset = _set.issubset
        self.issuperset = _set.issuperset

        # Expose some sorted list methods publicly.

        _list = self._list
        self.bisect_left = _list.bisect_left
        self.bisect = _list.bisect
        self.bisect_right = _list.bisect_right
        self.index = _list.index
        self.irange = _list.irange
        self.islice = _list.islice
        self._reset = _list._reset

        if key is not None:
            self.bisect_key_left = _list.bisect_key_left
            self.bisect_key_right = _list.bisect_key_right
            self.bisect_key = _list.bisect_key
            self.irange_key = _list.irange_key

        if iterable is not None:
            self._update(iterable)


    @classmethod
    def _fromset(cls, values, key=None):
        """Initialize sorted set from existing set.

        Used internally by set operations that return a new set.

        """
        sorted_set = object.__new__(cls)
        sorted_set._set = values
        sorted_set.__init__(key=key)
        return sorted_set


    @property
    def key(self):
        """Function used to extract comparison key from values.

        Sorted set compares values directly when the key function is none.

        """
        return self._key


    def __contains__(self, value):
        """Return true if `value` is an element of the sorted set.

        ``ss.__contains__(value)`` <==> ``value in ss``

        Runtime complexity: `O(1)`

        >>> ss = SortedSet([1, 2, 3, 4, 5])
        >>> 3 in ss
        True

        :param value: search for value in sorted set
        :return: true if `value` in sorted set

        """
        return value in self._set


    def __getitem__(self, index):
        """Lookup value at `index` in sorted set.

        ``ss.__getitem__(index)`` <==> ``ss[index]``

        Supports slicing.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> ss = SortedSet('abcde')
        >>> ss[2]
        'c'
        >>> ss[-1]
        'e'
        >>> ss[2:5]
        ['c', 'd', 'e']

        :param index: integer or slice for indexing
        :return: value or list of values
        :raises IndexError: if index out of range

        """
        return self._list[index]


    def __delitem__(self, index):
        """Remove value at `index` from sorted set.

        ``ss.__delitem__(index)`` <==> ``del ss[index]``

        Supports slicing.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> ss = SortedSet('abcde')
        >>> del ss[2]
        >>> ss
        SortedSet(['a', 'b', 'd', 'e'])
        >>> del ss[:2]
        >>> ss
        SortedSet(['d', 'e'])

        :param index: integer or slice for indexing
        :raises IndexError: if index out of range

        """
        _set = self._set
        _list = self._list
        if isinstance(index, slice):
            values = _list[index]
            _set.difference_update(values)
        else:
            value = _list[index]
            _set.remove(value)
        del _list[index]


    def __make_cmp(set_op, symbol, doc):
        "Make comparator method."
        def comparer(self, other):
            "Compare method for sorted set and set."
            if isinstance(other, SortedSet):
                return set_op(self._set, other._set)
            elif isinstance(other, Set):
                return set_op(self._set, other)
            return NotImplemented

        set_op_name = set_op.__name__
        comparer.__name__ = '__{0}__'.format(set_op_name)
        doc_str = """Return true if and only if sorted set is {0} `other`.

        ``ss.__{1}__(other)`` <==> ``ss {2} other``

        Comparisons use subset and superset semantics as with sets.

        Runtime complexity: `O(n)`

        :param other: `other` set
        :return: true if sorted set is {0} `other`

        """
        comparer.__doc__ = dedent(doc_str.format(doc, set_op_name, symbol))
        return comparer


    __eq__ = __make_cmp(eq, '==', 'equal to')
    __ne__ = __make_cmp(ne, '!=', 'not equal to')
    __lt__ = __make_cmp(lt, '<', 'a proper subset of')
    __gt__ = __make_cmp(gt, '>', 'a proper superset of')
    __le__ = __make_cmp(le, '<=', 'a subset of')
    __ge__ = __make_cmp(ge, '>=', 'a superset of')
    __make_cmp = staticmethod(__make_cmp)


    def __len__(self):
        """Return the size of the sorted set.

        ``ss.__len__()`` <==> ``len(ss)``

        :return: size of sorted set

        """
        return len(self._set)


    def __iter__(self):
        """Return an iterator over the sorted set.

        ``ss.__iter__()`` <==> ``iter(ss)``

        Iterating the sorted set while adding or deleting values may raise a
        :exc:`RuntimeError` or fail to iterate over all values.

        """
        return iter(self._list)


    def __reversed__(self):
        """Return a reverse iterator over the sorted set.

        ``ss.__reversed__()`` <==> ``reversed(ss)``

        Iterating the sorted set while adding or deleting values may raise a
        :exc:`RuntimeError` or fail to iterate over all values.

        """
        return reversed(self._list)


    def add(self, value):
        """Add `value` to sorted set.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> ss = SortedSet()
        >>> ss.add(3)
        >>> ss.add(1)
        >>> ss.add(2)
        >>> ss
        SortedSet([1, 2, 3])

        :param value: value to add to sorted set

        """
        _set = self._set
        if value not in _set:
            _set.add(value)
            self._list.add(value)

    _add = add


    def clear(self):
        """Remove all values from sorted set.

        Runtime complexity: `O(n)`

        """
        self._set.clear()
        self._list.clear()


    def copy(self):
        """Return a shallow copy of the sorted set.

        Runtime complexity: `O(n)`

        :return: new sorted set

        """
        return self._fromset(set(self._set), key=self._key)

    __copy__ = copy


    def count(self, value):
        """Return number of occurrences of `value` in the sorted set.

        Runtime complexity: `O(1)`

        >>> ss = SortedSet([1, 2, 3, 4, 5])
        >>> ss.count(3)
        1

        :param value: value to count in sorted set
        :return: count

        """
        return 1 if value in self._set else 0


    def discard(self, value):
        """Remove `value` from sorted set if it is a member.

        If `value` is not a member, do nothing.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> ss = SortedSet([1, 2, 3, 4, 5])
        >>> ss.discard(5)
        >>> ss.discard(0)
        >>> ss == set([1, 2, 3, 4])
        True

        :param value: `value` to discard from sorted set

        """
        _set = self._set
        if value in _set:
            _set.remove(value)
            self._list.remove(value)

    _discard = discard


    def pop(self, index=-1):
        """Remove and return value at `index` in sorted set.

        Raise :exc:`IndexError` if the sorted set is empty or index is out of
        range.

        Negative indices are supported.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> ss = SortedSet('abcde')
        >>> ss.pop()
        'e'
        >>> ss.pop(2)
        'c'
        >>> ss
        SortedSet(['a', 'b', 'd'])

        :param int index: index of value (default -1)
        :return: value
        :raises IndexError: if index is out of range

        """
        # pylint: disable=arguments-differ
        value = self._list.pop(index)
        self._set.remove(value)
        return value


    def remove(self, value):
        """Remove `value` from sorted set; `value` must be a member.

        If `value` is not a member, raise :exc:`KeyError`.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> ss = SortedSet([1, 2, 3, 4, 5])
        >>> ss.remove(5)
        >>> ss == set([1, 2, 3, 4])
        True
        >>> ss.remove(0)
        Traceback (most recent call last):
          ...
        KeyError: 0

        :param value: `value` to remove from sorted set
        :raises KeyError: if `value` is not in sorted set

        """
        self._set.remove(value)
        self._list.remove(value)


    def difference(self, *iterables):
        """Return the difference of two or more sets as a new sorted set.

        The `difference` method also corresponds to operator ``-``.

        ``ss.__sub__(iterable)`` <==> ``ss - iterable``

        The difference is all values that are in this sorted set but not the
        other `iterables`.

        >>> ss = SortedSet([1, 2, 3, 4, 5])
        >>> ss.difference([4, 5, 6, 7])
        SortedSet([1, 2, 3])

        :param iterables: iterable arguments
        :return: new sorted set

        """
        diff = self._set.difference(*iterables)
        return self._fromset(diff, key=self._key)

    __sub__ = difference


    def difference_update(self, *iterables):
        """Remove all values of `iterables` from this sorted set.

        The `difference_update` method also corresponds to operator ``-=``.

        ``ss.__isub__(iterable)`` <==> ``ss -= iterable``

        >>> ss = SortedSet([1, 2, 3, 4, 5])
        >>> _ = ss.difference_update([4, 5, 6, 7])
        >>> ss
        SortedSet([1, 2, 3])

        :param iterables: iterable arguments
        :return: itself

        """
        _set = self._set
        _list = self._list
        values = set(chain(*iterables))
        if (4 * len(values)) > len(_set):
            _set.difference_update(values)
            _list.clear()
            _list.update(_set)
        else:
            _discard = self._discard
            for value in values:
                _discard(value)
        return self

    __isub__ = difference_update


    def intersection(self, *iterables):
        """Return the intersection of two or more sets as a new sorted set.

        The `intersection` method also corresponds to operator ``&``.

        ``ss.__and__(iterable)`` <==> ``ss & iterable``

        The intersection is all values that are in this sorted set and each of
        the other `iterables`.

        >>> ss = SortedSet([1, 2, 3, 4, 5])
        >>> ss.intersection([4, 5, 6, 7])
        SortedSet([4, 5])

        :param iterables: iterable arguments
        :return: new sorted set

        """
        intersect = self._set.intersection(*iterables)
        return self._fromset(intersect, key=self._key)

    __and__ = intersection
    __rand__ = __and__


    def intersection_update(self, *iterables):
        """Update the sorted set with the intersection of `iterables`.

        The `intersection_update` method also corresponds to operator ``&=``.

        ``ss.__iand__(iterable)`` <==> ``ss &= iterable``

        Keep only values found in itself and all `iterables`.

        >>> ss = SortedSet([1, 2, 3, 4, 5])
        >>> _ = ss.intersection_update([4, 5, 6, 7])
        >>> ss
        SortedSet([4, 5])

        :param iterables: iterable arguments
        :return: itself

        """
        _set = self._set
        _list = self._list
        _set.intersection_update(*iterables)
        _list.clear()
        _list.update(_set)
        return self

    __iand__ = intersection_update


    def symmetric_difference(self, other):
        """Return the symmetric difference with `other` as a new sorted set.

        The `symmetric_difference` method also corresponds to operator ``^``.

        ``ss.__xor__(other)`` <==> ``ss ^ other``

        The symmetric difference is all values tha are in exactly one of the
        sets.

        >>> ss = SortedSet([1, 2, 3, 4, 5])
        >>> ss.symmetric_difference([4, 5, 6, 7])
        SortedSet([1, 2, 3, 6, 7])

        :param other: `other` iterable
        :return: new sorted set

        """
        diff = self._set.symmetric_difference(other)
        return self._fromset(diff, key=self._key)

    __xor__ = symmetric_difference
    __rxor__ = __xor__


    def symmetric_difference_update(self, other):
        """Update the sorted set with the symmetric difference with `other`.

        The `symmetric_difference_update` method also corresponds to operator
        ``^=``.

        ``ss.__ixor__(other)`` <==> ``ss ^= other``

        Keep only values found in exactly one of itself and `other`.

        >>> ss = SortedSet([1, 2, 3, 4, 5])
        >>> _ = ss.symmetric_difference_update([4, 5, 6, 7])
        >>> ss
        SortedSet([1, 2, 3, 6, 7])

        :param other: `other` iterable
        :return: itself

        """
        _set = self._set
        _list = self._list
        _set.symmetric_difference_update(other)
        _list.clear()
        _list.update(_set)
        return self

    __ixor__ = symmetric_difference_update


    def union(self, *iterables):
        """Return new sorted set with values from itself and all `iterables`.

        The `union` method also corresponds to operator ``|``.

        ``ss.__or__(iterable)`` <==> ``ss | iterable``

        >>> ss = SortedSet([1, 2, 3, 4, 5])
        >>> ss.union([4, 5, 6, 7])
        SortedSet([1, 2, 3, 4, 5, 6, 7])

        :param iterables: iterable arguments
        :return: new sorted set

        """
        return self.__class__(chain(iter(self), *iterables), key=self._key)

    __or__ = union
    __ror__ = __or__


    def update(self, *iterables):
        """Update the sorted set adding values from all `iterables`.

        The `update` method also corresponds to operator ``|=``.

        ``ss.__ior__(iterable)`` <==> ``ss |= iterable``

        >>> ss = SortedSet([1, 2, 3, 4, 5])
        >>> _ = ss.update([4, 5, 6, 7])
        >>> ss
        SortedSet([1, 2, 3, 4, 5, 6, 7])

        :param iterables: iterable arguments
        :return: itself

        """
        _set = self._set
        _list = self._list
        values = set(chain(*iterables))
        if (4 * len(values)) > len(_set):
            _list = self._list
            _set.update(values)
            _list.clear()
            _list.update(_set)
        else:
            _add = self._add
            for value in values:
                _add(value)
        return self

    __ior__ = update
    _update = update


    def __reduce__(self):
        """Support for pickle.

        The tricks played with exposing methods in :func:`SortedSet.__init__`
        confuse pickle so customize the reducer.

        """
        return (type(self), (self._set, self._key))


    @recursive_repr()
    def __repr__(self):
        """Return string representation of sorted set.

        ``ss.__repr__()`` <==> ``repr(ss)``

        :return: string representation

        """
        _key = self._key
        key = '' if _key is None else ', key={0!r}'.format(_key)
        type_name = type(self).__name__
        return '{0}({1!r}{2})'.format(type_name, list(self), key)


    def _check(self):
        """Check invariants of sorted set.

        Runtime complexity: `O(n)`

        """
        _set = self._set
        _list = self._list
        _list._check()
        assert len(_set) == len(_list)
        assert all(value in _set for value in _list)

# === NexusCore/openenv\Lib\site-packages\litellm\responses\litellm_completion_transformation\transformation.py ===
"""
Handles transforming from Responses API -> LiteLLM completion  (Chat Completion API)
"""

from typing import Any, Dict, List, Literal, Optional, Tuple, Union, cast

from openai.types.responses.tool_param import FunctionToolParam
from typing_extensions import TypedDict

from litellm._logging import verbose_logger

try:
    from litellm_enterprise.enterprise_callbacks.session_handler import (
        _ENTERPRISE_ResponsesSessionHandler,
    )
except Exception as e:
    verbose_logger.debug(
        f"[Non-Blocking] Unable to import _ENTERPRISE_ResponsesSessionHandler - LiteLLM Enterprise Feature - {str(e)}"
    )
    _ENTERPRISE_ResponsesSessionHandler = None
from litellm.caching import InMemoryCache
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionResponseMessage,
    ChatCompletionSystemMessage,
    ChatCompletionToolCallChunk,
    ChatCompletionToolCallFunctionChunk,
    ChatCompletionToolMessage,
    ChatCompletionToolParam,
    ChatCompletionToolParamFunctionChunk,
    ChatCompletionUserMessage,
    GenericChatCompletionMessage,
    OpenAIMcpServerTool,
    OpenAIWebSearchOptions,
    OpenAIWebSearchUserLocation,
    Reasoning,
    ResponseAPIUsage,
    ResponseInputParam,
    ResponsesAPIOptionalRequestParams,
    ResponsesAPIResponse,
    ResponseTextConfig,
)
from litellm.types.responses.main import (
    GenericResponseOutputItem,
    GenericResponseOutputItemContentAnnotation,
    OutputFunctionToolCall,
    OutputText,
)
from litellm.types.utils import (
    ChatCompletionAnnotation,
    ChatCompletionMessageToolCall,
    Choices,
    Function,
    Message,
    ModelResponse,
    Usage,
)

########### Initialize Classes used for Responses API  ###########
TOOL_CALLS_CACHE = InMemoryCache()


class ChatCompletionSession(TypedDict, total=False):
    messages: List[
        Union[
            AllMessageValues,
            GenericChatCompletionMessage,
            ChatCompletionMessageToolCall,
            ChatCompletionResponseMessage,
            Message,
        ]
    ]
    litellm_session_id: Optional[str]


########### End of Initialize Classes used for Responses API  ###########


class LiteLLMCompletionResponsesConfig:
    @staticmethod
    def get_supported_openai_params(model: str) -> list:
        """
        LiteLLM Adapter from OpenAI Responses API to Chat Completion API supports a subset of OpenAI Responses API params
        """
        return [
            "input",
            "model",
            "instructions",
            "max_output_tokens",
            "metadata",
            "parallel_tool_calls",
            "previous_response_id",
            "stream",
            "temperature",
            "tool_choice",
            "tools",
            "top_p",
            "user",
        ]

    @staticmethod
    def transform_responses_api_request_to_chat_completion_request(
        model: str,
        input: Union[str, ResponseInputParam],
        responses_api_request: ResponsesAPIOptionalRequestParams,
        custom_llm_provider: Optional[str] = None,
        stream: Optional[bool] = None,
        **kwargs,
    ) -> dict:
        """
        Transform a Responses API request into a Chat Completion request
        """
        tools, web_search_options = LiteLLMCompletionResponsesConfig.transform_responses_api_tools_to_chat_completion_tools(
            responses_api_request.get("tools") or []  # type: ignore
        )
        litellm_completion_request: dict = {
            "messages": LiteLLMCompletionResponsesConfig.transform_responses_api_input_to_messages(
                input=input,
                responses_api_request=responses_api_request,
            ),
            "model": model,
            "tool_choice": responses_api_request.get("tool_choice"),
            "tools": tools,
            "top_p": responses_api_request.get("top_p"),
            "user": responses_api_request.get("user"),
            "temperature": responses_api_request.get("temperature"),
            "parallel_tool_calls": responses_api_request.get("parallel_tool_calls"),
            "max_tokens": responses_api_request.get("max_output_tokens"),
            "stream": stream,
            "metadata": kwargs.get("metadata"),
            "service_tier": kwargs.get("service_tier"),
            "web_search_options": web_search_options,
            # litellm specific params
            "custom_llm_provider": custom_llm_provider,
        }

        # Responses API `Completed` events require usage, we pass `stream_options` to litellm.completion to include usage
        if stream is True:
            stream_options = {
                "include_usage": True,
            }
            litellm_completion_request["stream_options"] = stream_options
            litellm_logging_obj: Optional[LiteLLMLoggingObj] = kwargs.get(
                "litellm_logging_obj"
            )
            if litellm_logging_obj:
                litellm_logging_obj.stream_options = stream_options

        # only pass non-None values
        litellm_completion_request = {
            k: v for k, v in litellm_completion_request.items() if v is not None
        }

        return litellm_completion_request

    @staticmethod
    def transform_responses_api_input_to_messages(
        input: Union[str, ResponseInputParam],
        responses_api_request: Union[ResponsesAPIOptionalRequestParams, dict],
    ) -> List[
        Union[
            AllMessageValues,
            GenericChatCompletionMessage,
            ChatCompletionMessageToolCall,
            ChatCompletionResponseMessage,
            Message,
        ]
    ]:
        """
        Transform a Responses API input into a list of messages
        """
        messages: List[
            Union[
                AllMessageValues,
                GenericChatCompletionMessage,
                ChatCompletionMessageToolCall,
                ChatCompletionResponseMessage,
                Message,
            ]
        ] = []
        if responses_api_request.get("instructions"):
            messages.append(
                LiteLLMCompletionResponsesConfig.transform_instructions_to_system_message(
                    responses_api_request.get("instructions")
                )
            )

        messages.extend(
            LiteLLMCompletionResponsesConfig._transform_response_input_param_to_chat_completion_message(
                input=input,
            )
        )

        return messages

    @staticmethod
    async def async_responses_api_session_handler(
        previous_response_id: str,
        litellm_completion_request: dict,
    ) -> dict:
        """
        Async hook to get the chain of previous input and output pairs and return a list of Chat Completion messages
        """
        if _ENTERPRISE_ResponsesSessionHandler is not None:
            chat_completion_session = ChatCompletionSession(
                messages=[], litellm_session_id=None
            )
            if previous_response_id:
                chat_completion_session = await _ENTERPRISE_ResponsesSessionHandler.get_chat_completion_message_history_for_previous_response_id(
                    previous_response_id=previous_response_id
                )
            _messages = litellm_completion_request.get("messages") or []
            session_messages = chat_completion_session.get("messages") or []
            litellm_completion_request["messages"] = session_messages + _messages
            litellm_completion_request[
                "litellm_trace_id"
            ] = chat_completion_session.get("litellm_session_id")
        return litellm_completion_request

    @staticmethod
    def _transform_response_input_param_to_chat_completion_message(
        input: Union[str, ResponseInputParam],
    ) -> List[
        Union[
            AllMessageValues,
            GenericChatCompletionMessage,
            ChatCompletionMessageToolCall,
            ChatCompletionResponseMessage,
        ]
    ]:
        """
        Transform a ResponseInputParam into a Chat Completion message
        """
        messages: List[
            Union[
                AllMessageValues,
                GenericChatCompletionMessage,
                ChatCompletionMessageToolCall,
                ChatCompletionResponseMessage,
            ]
        ] = []
        tool_call_output_messages: List[
            Union[
                AllMessageValues,
                GenericChatCompletionMessage,
                ChatCompletionMessageToolCall,
                ChatCompletionResponseMessage,
            ]
        ] = []

        if isinstance(input, str):
            messages.append(ChatCompletionUserMessage(role="user", content=input))
        elif isinstance(input, list):
            for _input in input:
                chat_completion_messages = LiteLLMCompletionResponsesConfig._transform_responses_api_input_item_to_chat_completion_message(
                    input_item=_input
                )
                if LiteLLMCompletionResponsesConfig._is_input_item_tool_call_output(
                    input_item=_input
                ):
                    tool_call_output_messages.extend(chat_completion_messages)
                else:
                    messages.extend(chat_completion_messages)

        messages.extend(tool_call_output_messages)
        return messages

    @staticmethod
    def _ensure_tool_call_output_has_corresponding_tool_call(
        messages: List[Union[AllMessageValues, GenericChatCompletionMessage]],
    ) -> bool:
        """
        If any tool call output is present, ensure there is a corresponding tool call/tool_use block
        """
        for message in messages:
            if message.get("role") == "tool":
                return True
        return False

    @staticmethod
    def _transform_responses_api_input_item_to_chat_completion_message(
        input_item: Any,
    ) -> List[
        Union[
            AllMessageValues,
            GenericChatCompletionMessage,
            ChatCompletionResponseMessage,
        ]
    ]:
        """
        Transform a Responses API input item into a Chat Completion message

        - EasyInputMessageParam
        - Message
        - ResponseOutputMessageParam
        - ResponseFileSearchToolCallParam
        - ResponseComputerToolCallParam
        - ComputerCallOutput
        - ResponseFunctionWebSearchParam
        - ResponseFunctionToolCallParam
        - FunctionCallOutput
        - ResponseReasoningItemParam
        - ItemReference
        """
        if LiteLLMCompletionResponsesConfig._is_input_item_tool_call_output(input_item):
            # handle executed tool call results
            return LiteLLMCompletionResponsesConfig._transform_responses_api_tool_call_output_to_chat_completion_message(
                tool_call_output=input_item
            )
        else:
            return [
                GenericChatCompletionMessage(
                    role=input_item.get("role") or "user",
                    content=LiteLLMCompletionResponsesConfig._transform_responses_api_content_to_chat_completion_content(
                        input_item.get("content")
                    ),
                )
            ]

    @staticmethod
    def _is_input_item_tool_call_output(input_item: Any) -> bool:
        """
        Check if the input item is a tool call output
        """
        return input_item.get("type") in [
            "function_call_output",
            "web_search_call",
            "computer_call_output",
        ]

    @staticmethod
    def _transform_responses_api_tool_call_output_to_chat_completion_message(
        tool_call_output: Dict[str, Any],
    ) -> List[
        Union[
            AllMessageValues,
            GenericChatCompletionMessage,
            ChatCompletionResponseMessage,
        ]
    ]:
        """
        ChatCompletionToolMessage is used to indicate the output from a tool call
        """
        tool_output_message = ChatCompletionToolMessage(
            role="tool",
            content=tool_call_output.get("output") or "",
            tool_call_id=tool_call_output.get("call_id") or "",
        )

        _tool_use_definition = TOOL_CALLS_CACHE.get_cache(
            key=tool_call_output.get("call_id") or "",
        )
        if _tool_use_definition:
            """
            Append the tool use definition to the list of messages


            Providers like Anthropic require the tool use definition to be included with the tool output

            - Input:
                {'function':
                    arguments:'{"command": ["echo","<html>\\n<head>\\n  <title>Hello</title>\\n</head>\\n<body>\\n  <h1>Hi</h1>\\n</body>\\n</html>",">","index.html"]}',
                    name='shell',
                    'id': 'toolu_018KFWsEySHjdKZPdUzXpymJ',
                    'type': 'function'
                }
            - Output:
                {
                    "id": "toolu_018KFWsEySHjdKZPdUzXpymJ",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": "{\"latitude\":48.8566,\"longitude\":2.3522}"
                        }
                }

            """
            function: dict = _tool_use_definition.get("function") or {}
            tool_call_chunk = ChatCompletionToolCallChunk(
                id=_tool_use_definition.get("id") or "",
                type=_tool_use_definition.get("type") or "function",
                function=ChatCompletionToolCallFunctionChunk(
                    name=function.get("name") or "",
                    arguments=function.get("arguments") or "",
                ),
                index=0,
            )
            chat_completion_response_message = ChatCompletionResponseMessage(
                tool_calls=[tool_call_chunk],
                role="assistant",
            )
            return [chat_completion_response_message, tool_output_message]

        return [tool_output_message]

    @staticmethod
    def _transform_input_file_item_to_file_item(item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a Responses API input_file item to a Chat Completion file item

        Args:
            item: Dictionary containing input_file type with file_id and/or file_data

        Returns:
            Dictionary with transformed file structure for Chat Completion
        """
        file_dict: Dict[str, Any] = {}
        keys = ["file_id", "file_data"]
        for key in keys:
            if item.get(key):
                file_dict[key] = item.get(key)

        new_item: Dict[str, Any] = {"type": "file", "file": file_dict}
        return new_item

    @staticmethod
    def _transform_responses_api_content_to_chat_completion_content(
        content: Any,
    ) -> Union[str, List[Union[str, Dict[str, Any]]]]:
        """
        Transform a Responses API content into a Chat Completion content
        """

        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            content_list: List[Union[str, Dict[str, Any]]] = []
            for item in content:
                if isinstance(item, str):
                    content_list.append(item)
                elif isinstance(item, dict):
                    if item.get("type") == "input_file":
                        content_list.append(
                            LiteLLMCompletionResponsesConfig._transform_input_file_item_to_file_item(
                                item
                            )
                        )
                    else:
                        content_list.append(
                            {
                                "type": LiteLLMCompletionResponsesConfig._get_chat_completion_request_content_type(
                                    item.get("type") or "text"
                                ),
                                "text": item.get("text"),
                            }
                        )
            return content_list
        else:
            raise ValueError(f"Invalid content type: {type(content)}")

    @staticmethod
    def _get_chat_completion_request_content_type(content_type: str) -> str:
        """
        Get the Chat Completion request content type
        """
        # Responses API content has `input_` prefix, if it exists, remove it
        if content_type.startswith("input_"):
            return content_type[len("input_") :]
        else:
            return content_type

    @staticmethod
    def transform_instructions_to_system_message(
        instructions: Optional[str],
    ) -> ChatCompletionSystemMessage:
        """
        Transform a Instructions into a system message
        """
        return ChatCompletionSystemMessage(role="system", content=instructions or "")

    @staticmethod
    def transform_responses_api_tools_to_chat_completion_tools(
        tools: Optional[List[Union[FunctionToolParam, OpenAIMcpServerTool]]],
    ) -> Tuple[List[Union[ChatCompletionToolParam, OpenAIMcpServerTool]], Optional[OpenAIWebSearchOptions]]:
        """
        Transform a Responses API tools into a Chat Completion tools
        """
        if tools is None:
            return [], None
        chat_completion_tools: List[
            Union[ChatCompletionToolParam, OpenAIMcpServerTool]
        ] = []
        web_search_options: Optional[OpenAIWebSearchOptions] = None
        for tool in tools:
            if tool.get("type") == "mcp":
                chat_completion_tools.append(cast(OpenAIMcpServerTool, tool))
            elif tool.get("type") == "web_search_preview" or tool.get("type") == "web_search":
                _search_context_size: Literal["low", "medium", "high"] = cast(Literal["low", "medium", "high"], tool.get("search_context_size"))
                _user_location: Optional[OpenAIWebSearchUserLocation] = cast(Optional[OpenAIWebSearchUserLocation], tool.get("user_location") or None)
                web_search_options = OpenAIWebSearchOptions(
                    search_context_size=_search_context_size,
                    user_location=_user_location,
                )
            else:
                typed_tool = cast(FunctionToolParam, tool)
                chat_completion_tools.append(
                    ChatCompletionToolParam(
                        type="function",
                        function=ChatCompletionToolParamFunctionChunk(
                            name=typed_tool.get("name") or "",
                            description=typed_tool.get("description") or "",
                            parameters=dict(typed_tool.get("parameters", {}) or {}),
                            strict=typed_tool.get("strict", False) or False,
                        ),
                    )
                )
        return chat_completion_tools, web_search_options

    @staticmethod
    def transform_chat_completion_tools_to_responses_tools(
        chat_completion_response: ModelResponse,
    ) -> List[OutputFunctionToolCall]:
        """
        Transform a Chat Completion tools into a Responses API tools
        """
        all_chat_completion_tools: List[ChatCompletionMessageToolCall] = []
        for choice in chat_completion_response.choices:
            if isinstance(choice, Choices):
                if choice.message.tool_calls:
                    all_chat_completion_tools.extend(choice.message.tool_calls)
                    for tool_call in choice.message.tool_calls:
                        TOOL_CALLS_CACHE.set_cache(
                            key=tool_call.id,
                            value=tool_call,
                        )

        responses_tools: List[OutputFunctionToolCall] = []
        for tool in all_chat_completion_tools:
            if tool.type == "function":
                function_definition = tool.function
                responses_tools.append(
                    OutputFunctionToolCall(
                        name=function_definition.name or "",
                        arguments=function_definition.get("arguments") or "",
                        call_id=tool.id or "",
                        id=tool.id or "",
                        type="function_call",  # critical this is "function_call" to work with tools like openai codex
                        status=function_definition.get("status") or "completed",
                    )
                )
        return responses_tools

    @staticmethod
    def transform_chat_completion_response_to_responses_api_response(
        request_input: Union[str, ResponseInputParam],
        responses_api_request: ResponsesAPIOptionalRequestParams,
        chat_completion_response: Union[ModelResponse, dict],
    ) -> ResponsesAPIResponse:
        """
        Transform a Chat Completion response into a Responses API response
        """
        if isinstance(chat_completion_response, dict):
            chat_completion_response = ModelResponse(**chat_completion_response)
        responses_api_response: ResponsesAPIResponse = ResponsesAPIResponse(
            id=chat_completion_response.id,
            created_at=chat_completion_response.created,
            model=chat_completion_response.model,
            object=chat_completion_response.object,
            error=getattr(chat_completion_response, "error", None),
            incomplete_details=getattr(
                chat_completion_response, "incomplete_details", None
            ),
            instructions=getattr(chat_completion_response, "instructions", None),
            metadata=getattr(chat_completion_response, "metadata", {}),
            output=LiteLLMCompletionResponsesConfig._transform_chat_completion_choices_to_responses_output(
                chat_completion_response=chat_completion_response,
                choices=getattr(chat_completion_response, "choices", []),
            ),
            parallel_tool_calls=getattr(
                chat_completion_response, "parallel_tool_calls", False
            ),
            temperature=getattr(chat_completion_response, "temperature", 0),
            tool_choice=getattr(chat_completion_response, "tool_choice", "auto"),
            tools=getattr(chat_completion_response, "tools", []),
            top_p=getattr(chat_completion_response, "top_p", None),
            max_output_tokens=getattr(
                chat_completion_response, "max_output_tokens", None
            ),
            previous_response_id=getattr(
                chat_completion_response, "previous_response_id", None
            ),
            reasoning=Reasoning(),
            status=getattr(chat_completion_response, "status", "completed"),
            text=ResponseTextConfig(),
            truncation=getattr(chat_completion_response, "truncation", None),
            usage=LiteLLMCompletionResponsesConfig._transform_chat_completion_usage_to_responses_usage(
                chat_completion_response=chat_completion_response
            ),
            user=getattr(chat_completion_response, "user", None),
        )
        return responses_api_response

    @staticmethod
    def _transform_chat_completion_choices_to_responses_output(
        chat_completion_response: ModelResponse,
        choices: List[Choices],
    ) -> List[Union[GenericResponseOutputItem, OutputFunctionToolCall]]:
        responses_output: List[
            Union[GenericResponseOutputItem, OutputFunctionToolCall]
        ] = []
        for choice in choices:
            responses_output.append(
                GenericResponseOutputItem(
                    type="message",
                    id=chat_completion_response.id,
                    status=choice.finish_reason,
                    role=choice.message.role,
                    content=[
                        LiteLLMCompletionResponsesConfig._transform_chat_message_to_response_output_text(
                            choice.message
                        )
                    ],
                )
            )

        tool_calls = LiteLLMCompletionResponsesConfig.transform_chat_completion_tools_to_responses_tools(
            chat_completion_response=chat_completion_response
        )
        responses_output.extend(tool_calls)
        return responses_output

    @staticmethod
    def _transform_responses_api_outputs_to_chat_completion_messages(
        responses_api_output: ResponsesAPIResponse,
    ) -> List[
        Union[
            AllMessageValues,
            GenericChatCompletionMessage,
            ChatCompletionMessageToolCall,
        ]
    ]:
        messages: List[
            Union[
                AllMessageValues,
                GenericChatCompletionMessage,
                ChatCompletionMessageToolCall,
            ]
        ] = []
        output_items = responses_api_output.output
        for _output_item in output_items:
            output_item: dict = dict(_output_item)
            if output_item.get("type") == "function_call":
                # handle function call output
                messages.append(
                    LiteLLMCompletionResponsesConfig._transform_responses_output_tool_call_to_chat_completion_output_tool_call(
                        tool_call=output_item
                    )
                )
            else:
                # transform as generic ResponseOutputItem
                messages.append(
                    GenericChatCompletionMessage(
                        role=str(output_item.get("role")) or "user",
                        content=LiteLLMCompletionResponsesConfig._transform_responses_api_content_to_chat_completion_content(
                            output_item.get("content")
                        ),
                    )
                )
        return messages

    @staticmethod
    def _transform_responses_output_tool_call_to_chat_completion_output_tool_call(
        tool_call: dict,
    ) -> ChatCompletionMessageToolCall:
        return ChatCompletionMessageToolCall(
            id=tool_call.get("id") or "",
            type="function",
            function=Function(
                name=tool_call.get("name") or "",
                arguments=tool_call.get("arguments") or "",
            ),
        )

    @staticmethod
    def _transform_chat_message_to_response_output_text(
        message: Message,
    ) -> OutputText:
        return OutputText(
            type="output_text",
            text=message.content,
            annotations=LiteLLMCompletionResponsesConfig._transform_chat_completion_annotations_to_response_output_annotations(
                annotations=getattr(message, "annotations", None)
            ),
        )

    @staticmethod
    def _transform_chat_completion_annotations_to_response_output_annotations(
        annotations: Optional[List[ChatCompletionAnnotation]],
    ) -> List[GenericResponseOutputItemContentAnnotation]:
        response_output_annotations: List[
            GenericResponseOutputItemContentAnnotation
        ] = []

        if annotations is None:
            return response_output_annotations

        for annotation in annotations:
            annotation_type = annotation.get("type")
            if annotation_type == "url_citation" and "url_citation" in annotation:
                url_citation = annotation["url_citation"]
                response_output_annotations.append(
                    GenericResponseOutputItemContentAnnotation(
                        type=annotation_type,
                        start_index=url_citation.get("start_index"),
                        end_index=url_citation.get("end_index"),
                        url=url_citation.get("url"),
                        title=url_citation.get("title"),
                    )
                )
            # Handle other annotation types here

        return response_output_annotations

    @staticmethod
    def _transform_chat_completion_usage_to_responses_usage(
        chat_completion_response: Union[ModelResponse, Usage],
    ) -> ResponseAPIUsage:
        if isinstance(chat_completion_response, ModelResponse):
            usage: Optional[Usage] = getattr(chat_completion_response, "usage", None)
        else:
            usage = chat_completion_response
        if usage is None:
            return ResponseAPIUsage(
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
            )
        return ResponseAPIUsage(
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\perl.py ===
"""
    pygments.lexers.perl
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for Perl, Raku and related languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, ExtendedRegexLexer, include, bygroups, \
    using, this, default, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace
from pygments.util import shebang_matches

__all__ = ['PerlLexer', 'Perl6Lexer']


class PerlLexer(RegexLexer):
    """
    For Perl source code.
    """

    name = 'Perl'
    url = 'https://www.perl.org'
    aliases = ['perl', 'pl']
    filenames = ['*.pl', '*.pm', '*.t', '*.perl']
    mimetypes = ['text/x-perl', 'application/x-perl']
    version_added = ''

    flags = re.DOTALL | re.MULTILINE
    # TODO: give this to a perl guy who knows how to parse perl...
    tokens = {
        'balanced-regex': [
            (r'/(\\\\|\\[^\\]|[^\\/])*/[egimosx]*', String.Regex, '#pop'),
            (r'!(\\\\|\\[^\\]|[^\\!])*![egimosx]*', String.Regex, '#pop'),
            (r'\\(\\\\|[^\\])*\\[egimosx]*', String.Regex, '#pop'),
            (r'\{(\\\\|\\[^\\]|[^\\}])*\}[egimosx]*', String.Regex, '#pop'),
            (r'<(\\\\|\\[^\\]|[^\\>])*>[egimosx]*', String.Regex, '#pop'),
            (r'\[(\\\\|\\[^\\]|[^\\\]])*\][egimosx]*', String.Regex, '#pop'),
            (r'\((\\\\|\\[^\\]|[^\\)])*\)[egimosx]*', String.Regex, '#pop'),
            (r'@(\\\\|\\[^\\]|[^\\@])*@[egimosx]*', String.Regex, '#pop'),
            (r'%(\\\\|\\[^\\]|[^\\%])*%[egimosx]*', String.Regex, '#pop'),
            (r'\$(\\\\|\\[^\\]|[^\\$])*\$[egimosx]*', String.Regex, '#pop'),
        ],
        'root': [
            (r'\A\#!.+?$', Comment.Hashbang),
            (r'\#.*?$', Comment.Single),
            (r'^=[a-zA-Z0-9]+\s+.*?\n=cut', Comment.Multiline),
            (words((
                'case', 'continue', 'do', 'else', 'elsif', 'for', 'foreach',
                'if', 'last', 'my', 'next', 'our', 'redo', 'reset', 'then',
                'unless', 'until', 'while', 'print', 'new', 'BEGIN',
                'CHECK', 'INIT', 'END', 'return'), suffix=r'\b'),
             Keyword),
            (r'(format)(\s+)(\w+)(\s*)(=)(\s*\n)',
             bygroups(Keyword, Whitespace, Name, Whitespace, Punctuation, Whitespace), 'format'),
            (r'(eq|lt|gt|le|ge|ne|not|and|or|cmp)\b', Operator.Word),
            # common delimiters
            (r's/(\\\\|\\[^\\]|[^\\/])*/(\\\\|\\[^\\]|[^\\/])*/[egimosx]*',
                String.Regex),
            (r's!(\\\\|\\!|[^!])*!(\\\\|\\!|[^!])*![egimosx]*', String.Regex),
            (r's\\(\\\\|[^\\])*\\(\\\\|[^\\])*\\[egimosx]*', String.Regex),
            (r's@(\\\\|\\[^\\]|[^\\@])*@(\\\\|\\[^\\]|[^\\@])*@[egimosx]*',
                String.Regex),
            (r's%(\\\\|\\[^\\]|[^\\%])*%(\\\\|\\[^\\]|[^\\%])*%[egimosx]*',
                String.Regex),
            # balanced delimiters
            (r's\{(\\\\|\\[^\\]|[^\\}])*\}\s*', String.Regex, 'balanced-regex'),
            (r's<(\\\\|\\[^\\]|[^\\>])*>\s*', String.Regex, 'balanced-regex'),
            (r's\[(\\\\|\\[^\\]|[^\\\]])*\]\s*', String.Regex,
                'balanced-regex'),
            (r's\((\\\\|\\[^\\]|[^\\)])*\)\s*', String.Regex,
                'balanced-regex'),

            (r'm?/(\\\\|\\[^\\]|[^\\/\n])*/[gcimosx]*', String.Regex),
            (r'm(?=[/!\\{<\[(@%$])', String.Regex, 'balanced-regex'),
            (r'((?<==~)|(?<=\())\s*/(\\\\|\\[^\\]|[^\\/])*/[gcimosx]*',
                String.Regex),
            (r'\s+', Whitespace),
            (words((
                'abs', 'accept', 'alarm', 'atan2', 'bind', 'binmode', 'bless', 'caller', 'chdir',
                'chmod', 'chomp', 'chop', 'chown', 'chr', 'chroot', 'close', 'closedir', 'connect',
                'continue', 'cos', 'crypt', 'dbmclose', 'dbmopen', 'defined', 'delete', 'die',
                'dump', 'each', 'endgrent', 'endhostent', 'endnetent', 'endprotoent',
                'endpwent', 'endservent', 'eof', 'eval', 'exec', 'exists', 'exit', 'exp', 'fcntl',
                'fileno', 'flock', 'fork', 'format', 'formline', 'getc', 'getgrent', 'getgrgid',
                'getgrnam', 'gethostbyaddr', 'gethostbyname', 'gethostent', 'getlogin',
                'getnetbyaddr', 'getnetbyname', 'getnetent', 'getpeername', 'getpgrp',
                'getppid', 'getpriority', 'getprotobyname', 'getprotobynumber',
                'getprotoent', 'getpwent', 'getpwnam', 'getpwuid', 'getservbyname',
                'getservbyport', 'getservent', 'getsockname', 'getsockopt', 'glob', 'gmtime',
                'goto', 'grep', 'hex', 'import', 'index', 'int', 'ioctl', 'join', 'keys', 'kill', 'last',
                'lc', 'lcfirst', 'length', 'link', 'listen', 'local', 'localtime', 'log', 'lstat',
                'map', 'mkdir', 'msgctl', 'msgget', 'msgrcv', 'msgsnd', 'my', 'next', 'oct', 'open',
                'opendir', 'ord', 'our', 'pack', 'pipe', 'pop', 'pos', 'printf',
                'prototype', 'push', 'quotemeta', 'rand', 'read', 'readdir',
                'readline', 'readlink', 'readpipe', 'recv', 'redo', 'ref', 'rename',
                'reverse', 'rewinddir', 'rindex', 'rmdir', 'scalar', 'seek', 'seekdir',
                'select', 'semctl', 'semget', 'semop', 'send', 'setgrent', 'sethostent', 'setnetent',
                'setpgrp', 'setpriority', 'setprotoent', 'setpwent', 'setservent',
                'setsockopt', 'shift', 'shmctl', 'shmget', 'shmread', 'shmwrite', 'shutdown',
                'sin', 'sleep', 'socket', 'socketpair', 'sort', 'splice', 'split', 'sprintf', 'sqrt',
                'srand', 'stat', 'study', 'substr', 'symlink', 'syscall', 'sysopen', 'sysread',
                'sysseek', 'system', 'syswrite', 'tell', 'telldir', 'tie', 'tied', 'time', 'times', 'tr',
                'truncate', 'uc', 'ucfirst', 'umask', 'undef', 'unlink', 'unpack', 'unshift', 'untie',
                'utime', 'values', 'vec', 'wait', 'waitpid', 'wantarray', 'warn', 'write'), suffix=r'\b'),
             Name.Builtin),
            (r'((__(DATA|DIE|WARN)__)|(STD(IN|OUT|ERR)))\b', Name.Builtin.Pseudo),
            (r'(<<)([\'"]?)([a-zA-Z_]\w*)(\2;?\n.*?\n)(\3)(\n)',
             bygroups(String, String, String.Delimiter, String, String.Delimiter, Whitespace)),
            (r'__END__', Comment.Preproc, 'end-part'),
            (r'\$\^[ADEFHILMOPSTWX]', Name.Variable.Global),
            (r"\$[\\\"\[\]'&`+*.,;=%~?@$!<>(^|/-](?!\w)", Name.Variable.Global),
            (r'[$@%#]+', Name.Variable, 'varname'),
            (r'0_?[0-7]+(_[0-7]+)*', Number.Oct),
            (r'0x[0-9A-Fa-f]+(_[0-9A-Fa-f]+)*', Number.Hex),
            (r'0b[01]+(_[01]+)*', Number.Bin),
            (r'(?i)(\d*(_\d*)*\.\d+(_\d*)*|\d+(_\d*)*\.\d+(_\d*)*)(e[+-]?\d+)?',
             Number.Float),
            (r'(?i)\d+(_\d*)*e[+-]?\d+(_\d*)*', Number.Float),
            (r'\d+(_\d+)*', Number.Integer),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),
            (r'`(\\\\|\\[^\\]|[^`\\])*`', String.Backtick),
            (r'<([^\s>]+)>', String.Regex),
            (r'(q|qq|qw|qr|qx)\{', String.Other, 'cb-string'),
            (r'(q|qq|qw|qr|qx)\(', String.Other, 'rb-string'),
            (r'(q|qq|qw|qr|qx)\[', String.Other, 'sb-string'),
            (r'(q|qq|qw|qr|qx)\<', String.Other, 'lt-string'),
            (r'(q|qq|qw|qr|qx)([\W_])(.|\n)*?\2', String.Other),
            (r'(package)(\s+)([a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)*)',
             bygroups(Keyword, Whitespace, Name.Namespace)),
            (r'(use|require|no)(\s+)([a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)*)',
             bygroups(Keyword, Whitespace, Name.Namespace)),
            (r'(sub)(\s+)', bygroups(Keyword, Whitespace), 'funcname'),
            (words((
                'no', 'package', 'require', 'use'), suffix=r'\b'),
             Keyword),
            (r'(\[\]|\*\*|::|<<|>>|>=|<=>|<=|={3}|!=|=~|'
             r'!~|&&?|\|\||\.{1,3})', Operator),
            (r'[-+/*%=<>&^|!\\~]=?', Operator),
            (r'[()\[\]:;,<>/?{}]', Punctuation),  # yes, there's no shortage
                                                  # of punctuation in Perl!
            (r'(?=\w)', Name, 'name'),
        ],
        'format': [
            (r'\.\n', String.Interpol, '#pop'),
            (r'[^\n]*\n', String.Interpol),
        ],
        'varname': [
            (r'\s+', Whitespace),
            (r'\{', Punctuation, '#pop'),    # hash syntax?
            (r'\)|,', Punctuation, '#pop'),  # argument specifier
            (r'\w+::', Name.Namespace),
            (r'[\w:]+', Name.Variable, '#pop'),
        ],
        'name': [
            (r'[a-zA-Z_]\w*(::[a-zA-Z_]\w*)*(::)?(?=\s*->)', Name.Namespace, '#pop'),
            (r'[a-zA-Z_]\w*(::[a-zA-Z_]\w*)*::', Name.Namespace, '#pop'),
            (r'[\w:]+', Name, '#pop'),
            (r'[A-Z_]+(?=\W)', Name.Constant, '#pop'),
            (r'(?=\W)', Text, '#pop'),
        ],
        'funcname': [
            (r'[a-zA-Z_]\w*[!?]?', Name.Function),
            (r'\s+', Whitespace),
            # argument declaration
            (r'(\([$@%]*\))(\s*)', bygroups(Punctuation, Whitespace)),
            (r';', Punctuation, '#pop'),
            (r'.*?\{', Punctuation, '#pop'),
        ],
        'cb-string': [
            (r'\\[{}\\]', String.Other),
            (r'\\', String.Other),
            (r'\{', String.Other, 'cb-string'),
            (r'\}', String.Other, '#pop'),
            (r'[^{}\\]+', String.Other)
        ],
        'rb-string': [
            (r'\\[()\\]', String.Other),
            (r'\\', String.Other),
            (r'\(', String.Other, 'rb-string'),
            (r'\)', String.Other, '#pop'),
            (r'[^()]+', String.Other)
        ],
        'sb-string': [
            (r'\\[\[\]\\]', String.Other),
            (r'\\', String.Other),
            (r'\[', String.Other, 'sb-string'),
            (r'\]', String.Other, '#pop'),
            (r'[^\[\]]+', String.Other)
        ],
        'lt-string': [
            (r'\\[<>\\]', String.Other),
            (r'\\', String.Other),
            (r'\<', String.Other, 'lt-string'),
            (r'\>', String.Other, '#pop'),
            (r'[^<>]+', String.Other)
        ],
        'end-part': [
            (r'.+', Comment.Preproc, '#pop')
        ]
    }

    def analyse_text(text):
        if shebang_matches(text, r'perl'):
            return True

        result = 0

        if re.search(r'(?:my|our)\s+[$@%(]', text):
            result += 0.9

        if ':=' in text:
            # := is not valid Perl, but it appears in unicon, so we should
            # become less confident if we think we found Perl with :=
            result /= 2

        return result


class Perl6Lexer(ExtendedRegexLexer):
    """
    For Raku (a.k.a. Perl 6) source code.
    """

    name = 'Perl6'
    url = 'https://www.raku.org'
    aliases = ['perl6', 'pl6', 'raku']
    filenames = ['*.pl', '*.pm', '*.nqp', '*.p6', '*.6pl', '*.p6l', '*.pl6',
                 '*.6pm', '*.p6m', '*.pm6', '*.t', '*.raku', '*.rakumod',
                 '*.rakutest', '*.rakudoc']
    mimetypes = ['text/x-perl6', 'application/x-perl6']
    version_added = '2.0'
    flags = re.MULTILINE | re.DOTALL

    PERL6_IDENTIFIER_RANGE = r"['\w:-]"

    PERL6_KEYWORDS = (
        #Phasers
        'BEGIN','CATCH','CHECK','CLOSE','CONTROL','DOC','END','ENTER','FIRST',
        'INIT','KEEP','LAST','LEAVE','NEXT','POST','PRE','QUIT','UNDO',
        #Keywords
        'anon','augment','but','class','constant','default','does','else',
        'elsif','enum','for','gather','given','grammar','has','if','import',
        'is','let','loop','made','make','method','module','multi','my','need',
        'orwith','our','proceed','proto','repeat','require','return',
        'return-rw','returns','role','rule','state','sub','submethod','subset',
        'succeed','supersede','token','try','unit','unless','until','use',
        'when','while','with','without',
        #Traits
        'export','native','repr','required','rw','symbol',
    )

    PERL6_BUILTINS = (
        'ACCEPTS','abs','abs2rel','absolute','accept','accessed','acos',
        'acosec','acosech','acosh','acotan','acotanh','acquire','act','action',
        'actions','add','add_attribute','add_enum_value','add_fallback',
        'add_method','add_parent','add_private_method','add_role','add_trustee',
        'adverb','after','all','allocate','allof','allowed','alternative-names',
        'annotations','antipair','antipairs','any','anyof','app_lifetime',
        'append','arch','archname','args','arity','Array','asec','asech','asin',
        'asinh','ASSIGN-KEY','ASSIGN-POS','assuming','ast','at','atan','atan2',
        'atanh','AT-KEY','atomic-assign','atomic-dec-fetch','atomic-fetch',
        'atomic-fetch-add','atomic-fetch-dec','atomic-fetch-inc',
        'atomic-fetch-sub','atomic-inc-fetch','AT-POS','attributes','auth',
        'await','backtrace','Bag','BagHash','bail-out','base','basename',
        'base-repeating','batch','BIND-KEY','BIND-POS','bind-stderr',
        'bind-stdin','bind-stdout','bind-udp','bits','bless','block','Bool',
        'bool-only','bounds','break','Bridge','broken','BUILD','build-date',
        'bytes','cache','callframe','calling-package','CALL-ME','callsame',
        'callwith','can','cancel','candidates','cando','can-ok','canonpath',
        'caps','caption','Capture','cas','catdir','categorize','categorize-list',
        'catfile','catpath','cause','ceiling','cglobal','changed','Channel',
        'chars','chdir','child','child-name','child-typename','chmod','chomp',
        'chop','chr','chrs','chunks','cis','classify','classify-list','cleanup',
        'clone','close','closed','close-stdin','cmp-ok','code','codes','collate',
        'column','comb','combinations','command','comment','compiler','Complex',
        'compose','compose_type','composer','condition','config',
        'configure_destroy','configure_type_checking','conj','connect',
        'constraints','construct','contains','contents','copy','cos','cosec',
        'cosech','cosh','cotan','cotanh','count','count-only','cpu-cores',
        'cpu-usage','CREATE','create_type','cross','cue','curdir','curupdir','d',
        'Date','DateTime','day','daycount','day-of-month','day-of-week',
        'day-of-year','days-in-month','declaration','decode','decoder','deepmap',
        'default','defined','DEFINITE','delayed','DELETE-KEY','DELETE-POS',
        'denominator','desc','DESTROY','destroyers','devnull','diag',
        'did-you-mean','die','dies-ok','dir','dirname','dir-sep','DISTROnames',
        'do','does','does-ok','done','done-testing','duckmap','dynamic','e',
        'eager','earlier','elems','emit','enclosing','encode','encoder',
        'encoding','end','ends-with','enum_from_value','enum_value_list',
        'enum_values','enums','eof','EVAL','eval-dies-ok','EVALFILE',
        'eval-lives-ok','exception','excludes-max','excludes-min','EXISTS-KEY',
        'EXISTS-POS','exit','exitcode','exp','expected','explicitly-manage',
        'expmod','extension','f','fail','fails-like','fc','feature','file',
        'filename','find_method','find_method_qualified','finish','first','flat',
        'flatmap','flip','floor','flunk','flush','fmt','format','formatter',
        'freeze','from','from-list','from-loop','from-posix','full',
        'full-barrier','get','get_value','getc','gist','got','grab','grabpairs',
        'grep','handle','handled','handles','hardware','has_accessor','Hash',
        'head','headers','hh-mm-ss','hidden','hides','hour','how','hyper','id',
        'illegal','im','in','indent','index','indices','indir','infinite',
        'infix','infix:<+>','infix:<->','install_method_cache','Instant',
        'instead','Int','int-bounds','interval','in-timezone','invalid-str',
        'invert','invocant','IO','IO::Notification.watch-path','is_trusted',
        'is_type','isa','is-absolute','isa-ok','is-approx','is-deeply',
        'is-hidden','is-initial-thread','is-int','is-lazy','is-leap-year',
        'isNaN','isnt','is-prime','is-relative','is-routine','is-setting',
        'is-win','item','iterator','join','keep','kept','KERNELnames','key',
        'keyof','keys','kill','kv','kxxv','l','lang','last','lastcall','later',
        'lazy','lc','leading','level','like','line','lines','link','List',
        'listen','live','lives-ok','local','lock','log','log10','lookup','lsb',
        'made','MAIN','make','Map','match','max','maxpairs','merge','message',
        'method','method_table','methods','migrate','min','minmax','minpairs',
        'minute','misplaced','Mix','MixHash','mkdir','mode','modified','month',
        'move','mro','msb','multi','multiness','my','name','named','named_names',
        'narrow','nativecast','native-descriptor','nativesizeof','new','new_type',
        'new-from-daycount','new-from-pairs','next','nextcallee','next-handle',
        'nextsame','nextwith','NFC','NFD','NFKC','NFKD','nl-in','nl-out',
        'nodemap','nok','none','norm','not','note','now','nude','Num',
        'numerator','Numeric','of','offset','offset-in-hours','offset-in-minutes',
        'ok','old','on-close','one','on-switch','open','opened','operation',
        'optional','ord','ords','orig','os-error','osname','out-buffer','pack',
        'package','package-kind','package-name','packages','pair','pairs',
        'pairup','parameter','params','parent','parent-name','parents','parse',
        'parse-base','parsefile','parse-names','parts','pass','path','path-sep',
        'payload','peer-host','peer-port','periods','perl','permutations','phaser',
        'pick','pickpairs','pid','placeholder','plan','plus','polar','poll',
        'polymod','pop','pos','positional','posix','postfix','postmatch',
        'precomp-ext','precomp-target','pred','prefix','prematch','prepend',
        'print','printf','print-nl','print-to','private','private_method_table',
        'proc','produce','Promise','prompt','protect','pull-one','push',
        'push-all','push-at-least','push-exactly','push-until-lazy','put',
        'qualifier-type','quit','r','race','radix','rand','range','Rat','raw',
        're','read','readchars','readonly','ready','Real','reallocate','reals',
        'reason','rebless','receive','recv','redispatcher','redo','reduce',
        'rel2abs','relative','release','rename','repeated','replacement',
        'report','reserved','resolve','restore','result','resume','rethrow',
        'reverse','right','rindex','rmdir','role','roles_to_compose','rolish',
        'roll','rootdir','roots','rotate','rotor','round','roundrobin',
        'routine-type','run','rwx','s','samecase','samemark','samewith','say',
        'schedule-on','scheduler','scope','sec','sech','second','seek','self',
        'send','Set','set_hidden','set_name','set_package','set_rw','set_value',
        'SetHash','set-instruments','setup_finalization','shape','share','shell',
        'shift','sibling','sigil','sign','signal','signals','signature','sin',
        'sinh','sink','sink-all','skip','skip-at-least','skip-at-least-pull-one',
        'skip-one','skip-rest','sleep','sleep-timer','sleep-until','Slip','slurp',
        'slurp-rest','slurpy','snap','snapper','so','socket-host','socket-port',
        'sort','source','source-package','spawn','SPEC','splice','split',
        'splitdir','splitpath','sprintf','spurt','sqrt','squish','srand','stable',
        'start','started','starts-with','status','stderr','stdout','Str',
        'sub_signature','subbuf','subbuf-rw','subname','subparse','subst',
        'subst-mutate','substr','substr-eq','substr-rw','subtest','succ','sum',
        'Supply','symlink','t','tail','take','take-rw','tan','tanh','tap',
        'target','target-name','tc','tclc','tell','then','throttle','throw',
        'throws-like','timezone','tmpdir','to','today','todo','toggle','to-posix',
        'total','trailing','trans','tree','trim','trim-leading','trim-trailing',
        'truncate','truncated-to','trusts','try_acquire','trying','twigil','type',
        'type_captures','typename','uc','udp','uncaught_handler','unimatch',
        'uniname','uninames','uniparse','uniprop','uniprops','unique','unival',
        'univals','unlike','unlink','unlock','unpack','unpolar','unshift',
        'unwrap','updir','USAGE','use-ok','utc','val','value','values','VAR',
        'variable','verbose-config','version','VMnames','volume','vow','w','wait',
        'warn','watch','watch-path','week','weekday-of-month','week-number',
        'week-year','WHAT','when','WHERE','WHEREFORE','WHICH','WHO',
        'whole-second','WHY','wordcase','words','workaround','wrap','write',
        'write-to','x','yada','year','yield','yyyy-mm-dd','z','zip','zip-latest',

    )

    PERL6_BUILTIN_CLASSES = (
        #Booleans
        'False','True',
        #Classes
        'Any','Array','Associative','AST','atomicint','Attribute','Backtrace',
        'Backtrace::Frame','Bag','Baggy','BagHash','Blob','Block','Bool','Buf',
        'Callable','CallFrame','Cancellation','Capture','CArray','Channel','Code',
        'compiler','Complex','ComplexStr','Cool','CurrentThreadScheduler',
        'Cursor','Date','Dateish','DateTime','Distro','Duration','Encoding',
        'Exception','Failure','FatRat','Grammar','Hash','HyperWhatever','Instant',
        'Int','int16','int32','int64','int8','IntStr','IO','IO::ArgFiles',
        'IO::CatHandle','IO::Handle','IO::Notification','IO::Path',
        'IO::Path::Cygwin','IO::Path::QNX','IO::Path::Unix','IO::Path::Win32',
        'IO::Pipe','IO::Socket','IO::Socket::Async','IO::Socket::INET','IO::Spec',
        'IO::Spec::Cygwin','IO::Spec::QNX','IO::Spec::Unix','IO::Spec::Win32',
        'IO::Special','Iterable','Iterator','Junction','Kernel','Label','List',
        'Lock','Lock::Async','long','longlong','Macro','Map','Match',
        'Metamodel::AttributeContainer','Metamodel::C3MRO','Metamodel::ClassHOW',
        'Metamodel::EnumHOW','Metamodel::Finalization','Metamodel::MethodContainer',
        'Metamodel::MROBasedMethodDispatch','Metamodel::MultipleInheritance',
        'Metamodel::Naming','Metamodel::Primitives','Metamodel::PrivateMethodContainer',
        'Metamodel::RoleContainer','Metamodel::Trusting','Method','Mix','MixHash',
        'Mixy','Mu','NFC','NFD','NFKC','NFKD','Nil','Num','num32','num64',
        'Numeric','NumStr','ObjAt','Order','Pair','Parameter','Perl','Pod::Block',
        'Pod::Block::Code','Pod::Block::Comment','Pod::Block::Declarator',
        'Pod::Block::Named','Pod::Block::Para','Pod::Block::Table','Pod::Heading',
        'Pod::Item','Pointer','Positional','PositionalBindFailover','Proc',
        'Proc::Async','Promise','Proxy','PseudoStash','QuantHash','Range','Rat',
        'Rational','RatStr','Real','Regex','Routine','Scalar','Scheduler',
        'Semaphore','Seq','Set','SetHash','Setty','Signature','size_t','Slip',
        'Stash','Str','StrDistance','Stringy','Sub','Submethod','Supplier',
        'Supplier::Preserving','Supply','Systemic','Tap','Telemetry',
        'Telemetry::Instrument::Thread','Telemetry::Instrument::Usage',
        'Telemetry::Period','Telemetry::Sampler','Thread','ThreadPoolScheduler',
        'UInt','uint16','uint32','uint64','uint8','Uni','utf8','Variable',
        'Version','VM','Whatever','WhateverCode','WrapHandle'
    )

    PERL6_OPERATORS = (
        'X', 'Z', 'after', 'also', 'and', 'andthen', 'before', 'cmp', 'div',
        'eq', 'eqv', 'extra', 'ff', 'fff', 'ge', 'gt', 'le', 'leg', 'lt', 'm',
        'mm', 'mod', 'ne', 'or', 'orelse', 'rx', 's', 'tr', 'x', 'xor', 'xx',
        '++', '--', '**', '!', '+', '-', '~', '?', '|', '||', '+^', '~^', '?^',
        '^', '*', '/', '%', '%%', '+&', '+<', '+>', '~&', '~<', '~>', '?&',
        'gcd', 'lcm', '+', '-', '+|', '+^', '~|', '~^', '?|', '?^',
        '~', '&', '^', 'but', 'does', '<=>', '..', '..^', '^..', '^..^',
        '!=', '==', '<', '<=', '>', '>=', '~~', '===', '!eqv',
        '&&', '||', '^^', '//', 'min', 'max', '??', '!!', 'ff', 'fff', 'so',
        'not', '<==', '==>', '<<==', '==>>','unicmp',
    )

    # Perl 6 has a *lot* of possible bracketing characters
    # this list was lifted from STD.pm6 (https://github.com/perl6/std)
    PERL6_BRACKETS = {
        '\u0028': '\u0029', '\u003c': '\u003e', '\u005b': '\u005d',
        '\u007b': '\u007d', '\u00ab': '\u00bb', '\u0f3a': '\u0f3b',
        '\u0f3c': '\u0f3d', '\u169b': '\u169c', '\u2018': '\u2019',
        '\u201a': '\u2019', '\u201b': '\u2019', '\u201c': '\u201d',
        '\u201e': '\u201d', '\u201f': '\u201d', '\u2039': '\u203a',
        '\u2045': '\u2046', '\u207d': '\u207e', '\u208d': '\u208e',
        '\u2208': '\u220b', '\u2209': '\u220c', '\u220a': '\u220d',
        '\u2215': '\u29f5', '\u223c': '\u223d', '\u2243': '\u22cd',
        '\u2252': '\u2253', '\u2254': '\u2255', '\u2264': '\u2265',
        '\u2266': '\u2267', '\u2268': '\u2269', '\u226a': '\u226b',
        '\u226e': '\u226f', '\u2270': '\u2271', '\u2272': '\u2273',
        '\u2274': '\u2275', '\u2276': '\u2277', '\u2278': '\u2279',
        '\u227a': '\u227b', '\u227c': '\u227d', '\u227e': '\u227f',
        '\u2280': '\u2281', '\u2282': '\u2283', '\u2284': '\u2285',
        '\u2286': '\u2287', '\u2288': '\u2289', '\u228a': '\u228b',
        '\u228f': '\u2290', '\u2291': '\u2292', '\u2298': '\u29b8',
        '\u22a2': '\u22a3', '\u22a6': '\u2ade', '\u22a8': '\u2ae4',
        '\u22a9': '\u2ae3', '\u22ab': '\u2ae5', '\u22b0': '\u22b1',
        '\u22b2': '\u22b3', '\u22b4': '\u22b5', '\u22b6': '\u22b7',
        '\u22c9': '\u22ca', '\u22cb': '\u22cc', '\u22d0': '\u22d1',
        '\u22d6': '\u22d7', '\u22d8': '\u22d9', '\u22da': '\u22db',
        '\u22dc': '\u22dd', '\u22de': '\u22df', '\u22e0': '\u22e1',
        '\u22e2': '\u22e3', '\u22e4': '\u22e5', '\u22e6': '\u22e7',
        '\u22e8': '\u22e9', '\u22ea': '\u22eb', '\u22ec': '\u22ed',
        '\u22f0': '\u22f1', '\u22f2': '\u22fa', '\u22f3': '\u22fb',
        '\u22f4': '\u22fc', '\u22f6': '\u22fd', '\u22f7': '\u22fe',
        '\u2308': '\u2309', '\u230a': '\u230b', '\u2329': '\u232a',
        '\u23b4': '\u23b5', '\u2768': '\u2769', '\u276a': '\u276b',
        '\u276c': '\u276d', '\u276e': '\u276f', '\u2770': '\u2771',
        '\u2772': '\u2773', '\u2774': '\u2775', '\u27c3': '\u27c4',
        '\u27c5': '\u27c6', '\u27d5': '\u27d6', '\u27dd': '\u27de',
        '\u27e2': '\u27e3', '\u27e4': '\u27e5', '\u27e6': '\u27e7',
        '\u27e8': '\u27e9', '\u27ea': '\u27eb', '\u2983': '\u2984',
        '\u2985': '\u2986', '\u2987': '\u2988', '\u2989': '\u298a',
        '\u298b': '\u298c', '\u298d': '\u298e', '\u298f': '\u2990',
        '\u2991': '\u2992', '\u2993': '\u2994', '\u2995': '\u2996',
        '\u2997': '\u2998', '\u29c0': '\u29c1', '\u29c4': '\u29c5',
        '\u29cf': '\u29d0', '\u29d1': '\u29d2', '\u29d4': '\u29d5',
        '\u29d8': '\u29d9', '\u29da': '\u29db', '\u29f8': '\u29f9',
        '\u29fc': '\u29fd', '\u2a2b': '\u2a2c', '\u2a2d': '\u2a2e',
        '\u2a34': '\u2a35', '\u2a3c': '\u2a3d', '\u2a64': '\u2a65',
        '\u2a79': '\u2a7a', '\u2a7d': '\u2a7e', '\u2a7f': '\u2a80',
        '\u2a81': '\u2a82', '\u2a83': '\u2a84', '\u2a8b': '\u2a8c',
        '\u2a91': '\u2a92', '\u2a93': '\u2a94', '\u2a95': '\u2a96',
        '\u2a97': '\u2a98', '\u2a99': '\u2a9a', '\u2a9b': '\u2a9c',
        '\u2aa1': '\u2aa2', '\u2aa6': '\u2aa7', '\u2aa8': '\u2aa9',
        '\u2aaa': '\u2aab', '\u2aac': '\u2aad', '\u2aaf': '\u2ab0',
        '\u2ab3': '\u2ab4', '\u2abb': '\u2abc', '\u2abd': '\u2abe',
        '\u2abf': '\u2ac0', '\u2ac1': '\u2ac2', '\u2ac3': '\u2ac4',
        '\u2ac5': '\u2ac6', '\u2acd': '\u2ace', '\u2acf': '\u2ad0',
        '\u2ad1': '\u2ad2', '\u2ad3': '\u2ad4', '\u2ad5': '\u2ad6',
        '\u2aec': '\u2aed', '\u2af7': '\u2af8', '\u2af9': '\u2afa',
        '\u2e02': '\u2e03', '\u2e04': '\u2e05', '\u2e09': '\u2e0a',
        '\u2e0c': '\u2e0d', '\u2e1c': '\u2e1d', '\u2e20': '\u2e21',
        '\u3008': '\u3009', '\u300a': '\u300b', '\u300c': '\u300d',
        '\u300e': '\u300f', '\u3010': '\u3011', '\u3014': '\u3015',
        '\u3016': '\u3017', '\u3018': '\u3019', '\u301a': '\u301b',
        '\u301d': '\u301e', '\ufd3e': '\ufd3f', '\ufe17': '\ufe18',
        '\ufe35': '\ufe36', '\ufe37': '\ufe38', '\ufe39': '\ufe3a',
        '\ufe3b': '\ufe3c', '\ufe3d': '\ufe3e', '\ufe3f': '\ufe40',
        '\ufe41': '\ufe42', '\ufe43': '\ufe44', '\ufe47': '\ufe48',
        '\ufe59': '\ufe5a', '\ufe5b': '\ufe5c', '\ufe5d': '\ufe5e',
        '\uff08': '\uff09', '\uff1c': '\uff1e', '\uff3b': '\uff3d',
        '\uff5b': '\uff5d', '\uff5f': '\uff60', '\uff62': '\uff63',
    }

    def _build_word_match(words, boundary_regex_fragment=None, prefix='', suffix=''):
        if boundary_regex_fragment is None:
            return r'\b(' + prefix + r'|'.join(re.escape(x) for x in words) + \
                suffix + r')\b'
        else:
            return r'(?<!' + boundary_regex_fragment + r')' + prefix + r'(' + \
                r'|'.join(re.escape(x) for x in words) + r')' + suffix + r'(?!' + \
                boundary_regex_fragment + r')'

    def brackets_callback(token_class):
        def callback(lexer, match, context):
            groups = match.groupdict()
            opening_chars = groups['delimiter']
            n_chars = len(opening_chars)
            adverbs = groups.get('adverbs')

            closer = Perl6Lexer.PERL6_BRACKETS.get(opening_chars[0])
            text = context.text

            if closer is None:  # it's not a mirrored character, which means we
                                # just need to look for the next occurrence

                end_pos = text.find(opening_chars, match.start('delimiter') + n_chars)
            else:   # we need to look for the corresponding closing character,
                    # keep nesting in mind
                closing_chars = closer * n_chars
                nesting_level = 1

                search_pos = match.start('delimiter')

                while nesting_level > 0:
                    next_open_pos = text.find(opening_chars, search_pos + n_chars)
                    next_close_pos = text.find(closing_chars, search_pos + n_chars)

                    if next_close_pos == -1:
                        next_close_pos = len(text)
                        nesting_level = 0
                    elif next_open_pos != -1 and next_open_pos < next_close_pos:
                        nesting_level += 1
                        search_pos = next_open_pos
                    else:  # next_close_pos < next_open_pos
                        nesting_level -= 1
                        search_pos = next_close_pos

                end_pos = next_close_pos

            if end_pos < 0:     # if we didn't find a closer, just highlight the
                                # rest of the text in this class
                end_pos = len(text)

            if adverbs is not None and re.search(r':to\b', adverbs):
                heredoc_terminator = text[match.start('delimiter') + n_chars:end_pos]
                end_heredoc = re.search(r'^\s*' + re.escape(heredoc_terminator) +
                                        r'\s*$', text[end_pos:], re.MULTILINE)

                if end_heredoc:
                    end_pos += end_heredoc.end()
                else:
                    end_pos = len(text)

            yield match.start(), token_class, text[match.start():end_pos + n_chars]
            context.pos = end_pos + n_chars

        return callback

    def opening_brace_callback(lexer, match, context):
        stack = context.stack

        yield match.start(), Text, context.text[match.start():match.end()]
        context.pos = match.end()

        # if we encounter an opening brace and we're one level
        # below a token state, it means we need to increment
        # the nesting level for braces so we know later when
        # we should return to the token rules.
        if len(stack) > 2 and stack[-2] == 'token':
            context.perl6_token_nesting_level += 1

    def closing_brace_callback(lexer, match, context):
        stack = context.stack

        yield match.start(), Text, context.text[match.start():match.end()]
        context.pos = match.end()

        # if we encounter a free closing brace and we're one level
        # below a token state, it means we need to check the nesting
        # level to see if we need to return to the token state.
        if len(stack) > 2 and stack[-2] == 'token':
            context.perl6_token_nesting_level -= 1
            if context.perl6_token_nesting_level == 0:
                stack.pop()

    def embedded_perl6_callback(lexer, match, context):
        context.perl6_token_nesting_level = 1
        yield match.start(), Text, context.text[match.start():match.end()]
        context.pos = match.end()
        context.stack.append('root')

    # If you're modifying these rules, be careful if you need to process '{' or '}'
    # characters. We have special logic for processing these characters (due to the fact
    # that you can nest Perl 6 code in regex blocks), so if you need to process one of
    # them, make sure you also process the corresponding one!
    tokens = {
        'common': [
            (r'#[`|=](?P<delimiter>(?P<first_char>[' + ''.join(PERL6_BRACKETS) + r'])(?P=first_char)*)',
             brackets_callback(Comment.Multiline)),
            (r'#[^\n]*$', Comment.Single),
            (r'^(\s*)=begin\s+(\w+)\b.*?^\1=end\s+\2', Comment.Multiline),
            (r'^(\s*)=for.*?\n\s*?\n', Comment.Multiline),
            (r'^=.*?\n\s*?\n', Comment.Multiline),
            (r'(regex|token|rule)(\s*' + PERL6_IDENTIFIER_RANGE + '+:sym)',
             bygroups(Keyword, Name), 'token-sym-brackets'),
            (r'(regex|token|rule)(?!' + PERL6_IDENTIFIER_RANGE + r')(\s*' + PERL6_IDENTIFIER_RANGE + '+)?',
             bygroups(Keyword, Name), 'pre-token'),
            # deal with a special case in the Perl 6 grammar (role q { ... })
            (r'(role)(\s+)(q)(\s*)', bygroups(Keyword, Whitespace, Name, Whitespace)),
            (_build_word_match(PERL6_KEYWORDS, PERL6_IDENTIFIER_RANGE), Keyword),
            (_build_word_match(PERL6_BUILTIN_CLASSES, PERL6_IDENTIFIER_RANGE, suffix='(?::[UD])?'),
             Name.Builtin),
            (_build_word_match(PERL6_BUILTINS, PERL6_IDENTIFIER_RANGE), Name.Builtin),
            # copied from PerlLexer
            (r'[$@%&][.^:?=!~]?' + PERL6_IDENTIFIER_RANGE + '+(?:<<.*?>>|<.*?>|«.*?»)*',
             Name.Variable),
            (r'\$[!/](?:<<.*?>>|<.*?>|«.*?»)*', Name.Variable.Global),
            (r'::\?\w+', Name.Variable.Global),
            (r'[$@%&]\*' + PERL6_IDENTIFIER_RANGE + '+(?:<<.*?>>|<.*?>|«.*?»)*',
             Name.Variable.Global),
            (r'\$(?:<.*?>)+', Name.Variable),
            (r'(?:q|qq|Q)[a-zA-Z]?\s*(?P<adverbs>:[\w\s:]+)?\s*(?P<delimiter>(?P<first_char>[^0-9a-zA-Z:\s])'
             r'(?P=first_char)*)', brackets_callback(String)),
            # copied from PerlLexer
            (r'0_?[0-7]+(_[0-7]+)*', Number.Oct),
            (r'0x[0-9A-Fa-f]+(_[0-9A-Fa-f]+)*', Number.Hex),
            (r'0b[01]+(_[01]+)*', Number.Bin),
            (r'(?i)(\d*(_\d*)*\.\d+(_\d*)*|\d+(_\d*)*\.\d+(_\d*)*)(e[+-]?\d+)?',
             Number.Float),
            (r'(?i)\d+(_\d*)*e[+-]?\d+(_\d*)*', Number.Float),
            (r'\d+(_\d+)*', Number.Integer),
            (r'(?<=~~)\s*/(?:\\\\|\\/|.)*?/', String.Regex),
            (r'(?<=[=(,])\s*/(?:\\\\|\\/|.)*?/', String.Regex),
            (r'm\w+(?=\()', Name),
            (r'(?:m|ms|rx)\s*(?P<adverbs>:[\w\s:]+)?\s*(?P<delimiter>(?P<first_char>[^\w:\s])'
             r'(?P=first_char)*)', brackets_callback(String.Regex)),
            (r'(?:s|ss|tr)\s*(?::[\w\s:]+)?\s*/(?:\\\\|\\/|.)*?/(?:\\\\|\\/|.)*?/',
             String.Regex),
            (r'<[^\s=].*?\S>', String),
            (_build_word_match(PERL6_OPERATORS), Operator),
            (r'\w' + PERL6_IDENTIFIER_RANGE + '*', Name),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),
        ],
        'root': [
            include('common'),
            (r'\{', opening_brace_callback),
            (r'\}', closing_brace_callback),
            (r'.+?', Text),
        ],
        'pre-token': [
            include('common'),
            (r'\{', Text, ('#pop', 'token')),
            (r'.+?', Text),
        ],
        'token-sym-brackets': [
            (r'(?P<delimiter>(?P<first_char>[' + ''.join(PERL6_BRACKETS) + '])(?P=first_char)*)',
             brackets_callback(Name), ('#pop', 'pre-token')),
            default(('#pop', 'pre-token')),
        ],
        'token': [
            (r'\}', Text, '#pop'),
            (r'(?<=:)(?:my|our|state|constant|temp|let).*?;', using(this)),
            # make sure that quotes in character classes aren't treated as strings
            (r'<(?:[-!?+.]\s*)?\[.*?\]>', String.Regex),
            # make sure that '#' characters in quotes aren't treated as comments
            (r"(?<!\\)'(\\\\|\\[^\\]|[^'\\])*'", String.Regex),
            (r'(?<!\\)"(\\\\|\\[^\\]|[^"\\])*"', String.Regex),
            (r'#.*?$', Comment.Single),
            (r'\{', embedded_perl6_callback),
            ('.+?', String.Regex),
        ],
    }

    def analyse_text(text):
        def strip_pod(lines):
            in_pod = False
            stripped_lines = []

            for line in lines:
                if re.match(r'^=(?:end|cut)', line):
                    in_pod = False
                elif re.match(r'^=\w+', line):
                    in_pod = True
                elif not in_pod:
                    stripped_lines.append(line)

            return stripped_lines

        # XXX handle block comments
        lines = text.splitlines()
        lines = strip_pod(lines)
        text = '\n'.join(lines)

        if shebang_matches(text, r'perl6|rakudo|niecza|pugs'):
            return True

        saw_perl_decl = False
        rating = False

        # check for my/our/has declarations
        if re.search(r"(?:my|our|has)\s+(?:" + Perl6Lexer.PERL6_IDENTIFIER_RANGE +
                     r"+\s+)?[$@%&(]", text):
            rating = 0.8
            saw_perl_decl = True

        for line in lines:
            line = re.sub('#.*', '', line)
            if re.match(r'^\s*$', line):
                continue

            # match v6; use v6; use v6.0; use v6.0.0;
            if re.match(r'^\s*(?:use\s+)?v6(?:\.\d(?:\.\d)?)?;', line):
                return True
            # match class, module, role, enum, grammar declarations
            class_decl = re.match(r'^\s*(?:(?P<scope>my|our)\s+)?(?:module|class|role|enum|grammar)', line)
            if class_decl:
                if saw_perl_decl or class_decl.group('scope') is not None:
                    return True
                rating = 0.05
                continue
            break

        if ':=' in text:
            # Same logic as above for PerlLexer
            rating /= 2

        return rating

    def __init__(self, **options):
        super().__init__(**options)
        self.encoding = options.get('encoding', 'utf-8')

# === NexusCore/openenv\Lib\site-packages\win32\scripts\pywin32_postinstall.py ===
# postinstall script for pywin32
#
# copies pywintypesXX.dll and pythoncomXX.dll into the system directory,
# and creates a pth file
import argparse
import glob
import os
import shutil
import sys
import sysconfig
import tempfile
import winreg

tee_f = open(
    os.path.join(
        tempfile.gettempdir(),  # Send output somewhere so it can be found if necessary...
        "pywin32_postinstall.log",
    ),
    "w",
)


class Tee:
    def __init__(self, file):
        self.f = file

    def write(self, what):
        if self.f is not None:
            try:
                self.f.write(what.replace("\n", "\r\n"))
            except OSError:
                pass
        tee_f.write(what)

    def flush(self):
        if self.f is not None:
            try:
                self.f.flush()
            except OSError:
                pass
        tee_f.flush()


sys.stderr = Tee(sys.stderr)
sys.stdout = Tee(sys.stdout)

com_modules = [
    # module_name,                      class_names
    ("win32com.servers.interp", "Interpreter"),
    ("win32com.servers.dictionary", "DictionaryPolicy"),
    ("win32com.axscript.client.pyscript", "PyScript"),
]

# Is this a 'silent' install - ie, avoid all dialogs.
# Different than 'verbose'
silent = 0

# Verbosity of output messages.
verbose = 1

root_key_name = "Software\\Python\\PythonCore\\" + sys.winver


def get_root_hkey():
    try:
        winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, root_key_name, 0, winreg.KEY_CREATE_SUB_KEY
        )
        return winreg.HKEY_LOCAL_MACHINE
    except OSError:
        # Either not exist, or no permissions to create subkey means
        # must be HKCU
        return winreg.HKEY_CURRENT_USER


# Create a function with the same signature as create_shortcut
# previously provided by bdist_wininst
def create_shortcut(
    path, description, filename, arguments="", workdir="", iconpath="", iconindex=0
):
    import pythoncom
    from win32com.shell import shell

    ilink = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink,
        None,
        pythoncom.CLSCTX_INPROC_SERVER,
        shell.IID_IShellLink,
    )
    ilink.SetPath(path)
    ilink.SetDescription(description)
    if arguments:
        ilink.SetArguments(arguments)
    if workdir:
        ilink.SetWorkingDirectory(workdir)
    if iconpath or iconindex:
        ilink.SetIconLocation(iconpath, iconindex)
    # now save it.
    ipf = ilink.QueryInterface(pythoncom.IID_IPersistFile)
    ipf.Save(filename, 0)


# Support the same list of "path names" as bdist_wininst used to
def get_special_folder_path(path_name):
    from win32com.shell import shell, shellcon

    for maybe in """
        CSIDL_COMMON_STARTMENU CSIDL_STARTMENU CSIDL_COMMON_APPDATA
        CSIDL_LOCAL_APPDATA CSIDL_APPDATA CSIDL_COMMON_DESKTOPDIRECTORY
        CSIDL_DESKTOPDIRECTORY CSIDL_COMMON_STARTUP CSIDL_STARTUP
        CSIDL_COMMON_PROGRAMS CSIDL_PROGRAMS CSIDL_PROGRAM_FILES_COMMON
        CSIDL_PROGRAM_FILES CSIDL_FONTS""".split():
        if maybe == path_name:
            csidl = getattr(shellcon, maybe)
            return shell.SHGetSpecialFolderPath(0, csidl, False)
    raise ValueError(f"{path_name} is an unknown path ID")


def CopyTo(desc, src, dest):
    import win32api
    import win32con

    while 1:
        try:
            win32api.CopyFile(src, dest, 0)
            return
        except win32api.error as details:
            if details.winerror == 5:  # access denied - user not admin.
                raise
            if silent:
                # Running silent mode - just re-raise the error.
                raise
            full_desc = (
                f"Error {desc}\n\n"
                "If you have any Python applications running, "
                f"please close them now\nand select 'Retry'\n\n{details.strerror}"
            )
            rc = win32api.MessageBox(
                0, full_desc, "Installation Error", win32con.MB_ABORTRETRYIGNORE
            )
            if rc == win32con.IDABORT:
                raise
            elif rc == win32con.IDIGNORE:
                return
            # else retry - around we go again.


# We need to import win32api to determine the Windows system directory,
# so we can copy our system files there - but importing win32api will
# load the pywintypes.dll already in the system directory preventing us
# from updating them!
# So, we pull the same trick pywintypes.py does, but it loads from
# our pywintypes_system32 directory.
def LoadSystemModule(lib_dir, modname):
    # See if this is a debug build.
    import importlib.machinery
    import importlib.util

    suffix = "_d" if "_d.pyd" in importlib.machinery.EXTENSION_SUFFIXES else ""
    filename = "%s%d%d%s.dll" % (
        modname,
        sys.version_info.major,
        sys.version_info.minor,
        suffix,
    )
    filename = os.path.join(lib_dir, "pywin32_system32", filename)
    loader = importlib.machinery.ExtensionFileLoader(modname, filename)
    spec = importlib.machinery.ModuleSpec(name=modname, loader=loader, origin=filename)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)


def SetPyKeyVal(key_name, value_name, value):
    root_hkey = get_root_hkey()
    root_key = winreg.OpenKey(root_hkey, root_key_name)
    try:
        my_key = winreg.CreateKey(root_key, key_name)
        try:
            winreg.SetValueEx(my_key, value_name, 0, winreg.REG_SZ, value)
            if verbose:
                print(f"-> {root_key_name}\\{key_name}[{value_name}]={value!r}")
        finally:
            my_key.Close()
    finally:
        root_key.Close()


def UnsetPyKeyVal(key_name, value_name, delete_key=False):
    root_hkey = get_root_hkey()
    root_key = winreg.OpenKey(root_hkey, root_key_name)
    try:
        my_key = winreg.OpenKey(root_key, key_name, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(my_key, value_name)
            if verbose:
                print(f"-> DELETE {root_key_name}\\{key_name}[{value_name}]")
        finally:
            my_key.Close()
        if delete_key:
            winreg.DeleteKey(root_key, key_name)
            if verbose:
                print(f"-> DELETE {root_key_name}\\{key_name}")
    except OSError as why:
        winerror = getattr(why, "winerror", why.errno)
        if winerror != 2:  # file not found
            raise
    finally:
        root_key.Close()


def RegisterCOMObjects(register=True):
    import win32com.server.register

    if register:
        func = win32com.server.register.RegisterClasses
    else:
        func = win32com.server.register.UnregisterClasses
    flags = {}
    if not verbose:
        flags["quiet"] = 1
    for module, klass_name in com_modules:
        __import__(module)
        mod = sys.modules[module]
        flags["finalize_register"] = getattr(mod, "DllRegisterServer", None)
        flags["finalize_unregister"] = getattr(mod, "DllUnregisterServer", None)
        klass = getattr(mod, klass_name)
        func(klass, **flags)


def RegisterHelpFile(register=True, lib_dir=None):
    if lib_dir is None:
        lib_dir = sysconfig.get_paths()["platlib"]
    if register:
        # Register the .chm help file.
        chm_file = os.path.join(lib_dir, "PyWin32.chm")
        if os.path.isfile(chm_file):
            # This isn't recursive, so if 'Help' doesn't exist, we croak
            SetPyKeyVal("Help", None, None)
            SetPyKeyVal("Help\\Pythonwin Reference", None, chm_file)
            return chm_file
        else:
            print("NOTE: PyWin32.chm can not be located, so has not been registered")
    else:
        UnsetPyKeyVal("Help\\Pythonwin Reference", None, delete_key=True)
    return None


def RegisterPythonwin(register=True, lib_dir=None):
    """Add (or remove) Pythonwin to context menu for python scripts.
    ??? Should probably also add Edit command for pys files also.
    Also need to remove these keys on uninstall, but there's no function
    to add registry entries to uninstall log ???
    """
    import os

    if lib_dir is None:
        lib_dir = sysconfig.get_paths()["platlib"]
    classes_root = get_root_hkey()
    ## Installer executable doesn't seem to pass anything to postinstall script indicating if it's a debug build
    pythonwin_exe = os.path.join(lib_dir, "Pythonwin", "Pythonwin.exe")
    pythonwin_edit_command = pythonwin_exe + ' -edit "%1"'

    keys_vals = [
        (
            "Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\Pythonwin.exe",
            "",
            pythonwin_exe,
        ),
        (
            "Software\\Classes\\Python.File\\shell\\Edit with Pythonwin",
            "command",
            pythonwin_edit_command,
        ),
        (
            "Software\\Classes\\Python.NoConFile\\shell\\Edit with Pythonwin",
            "command",
            pythonwin_edit_command,
        ),
    ]

    try:
        if register:
            for key, sub_key, val in keys_vals:
                ## Since winreg only uses the character Api functions, this can fail if Python
                ##  is installed to a path containing non-ascii characters
                hkey = winreg.CreateKey(classes_root, key)
                if sub_key:
                    hkey = winreg.CreateKey(hkey, sub_key)
                winreg.SetValueEx(hkey, None, 0, winreg.REG_SZ, val)
                hkey.Close()
        else:
            for key, sub_key, val in keys_vals:
                try:
                    if sub_key:
                        hkey = winreg.OpenKey(classes_root, key)
                        winreg.DeleteKey(hkey, sub_key)
                        hkey.Close()
                    winreg.DeleteKey(classes_root, key)
                except OSError as why:
                    winerror = getattr(why, "winerror", why.errno)
                    if winerror != 2:  # file not found
                        raise
    finally:
        # tell windows about the change
        from win32com.shell import shell, shellcon

        shell.SHChangeNotify(
            shellcon.SHCNE_ASSOCCHANGED, shellcon.SHCNF_IDLIST, None, None
        )


def get_shortcuts_folder():
    if get_root_hkey() == winreg.HKEY_LOCAL_MACHINE:
        try:
            fldr = get_special_folder_path("CSIDL_COMMON_PROGRAMS")
        except OSError:
            # No CSIDL_COMMON_PROGRAMS on this platform
            fldr = get_special_folder_path("CSIDL_PROGRAMS")
    else:
        # non-admin install - always goes in this user's start menu.
        fldr = get_special_folder_path("CSIDL_PROGRAMS")

    try:
        install_group = winreg.QueryValue(
            get_root_hkey(), root_key_name + "\\InstallPath\\InstallGroup"
        )
    except OSError:
        install_group = "Python %d.%d" % (
            sys.version_info.major,
            sys.version_info.minor,
        )
    return os.path.join(fldr, install_group)


# Get the system directory, which may be the Wow64 directory if we are a 32bit
# python on a 64bit OS.
def get_system_dir():
    import win32api  # we assume this exists.

    try:
        import pythoncom
        import win32process
        from win32com.shell import shell, shellcon

        try:
            if win32process.IsWow64Process():
                return shell.SHGetSpecialFolderPath(0, shellcon.CSIDL_SYSTEMX86)
            return shell.SHGetSpecialFolderPath(0, shellcon.CSIDL_SYSTEM)
        except (pythoncom.com_error, win32process.error):
            return win32api.GetSystemDirectory()
    except ImportError:
        return win32api.GetSystemDirectory()


def fixup_dbi():
    # We used to have a dbi.pyd with our .pyd files, but now have a .py file.
    # If the user didn't uninstall, they will find the .pyd which will cause
    # problems - so handle that.
    import win32api
    import win32con

    pyd_name = os.path.join(os.path.dirname(win32api.__file__), "dbi.pyd")
    pyd_d_name = os.path.join(os.path.dirname(win32api.__file__), "dbi_d.pyd")
    py_name = os.path.join(os.path.dirname(win32con.__file__), "dbi.py")
    for this_pyd in (pyd_name, pyd_d_name):
        this_dest = this_pyd + ".old"
        if os.path.isfile(this_pyd) and os.path.isfile(py_name):
            try:
                if os.path.isfile(this_dest):
                    print(
                        f"Old dbi '{this_dest}' already exists - deleting '{this_pyd}'"
                    )
                    os.remove(this_pyd)
                else:
                    os.rename(this_pyd, this_dest)
                    print(f"renamed '{this_pyd}'->'{this_pyd}.old'")
            except OSError as exc:
                print(f"FAILED to rename '{this_pyd}': {exc}")


def install(lib_dir):
    import traceback

    # The .pth file is now installed as a regular file.
    # Create the .pth file in the site-packages dir, and use only relative paths
    # We used to write a .pth directly to sys.prefix - clobber it.
    if os.path.isfile(os.path.join(sys.prefix, "pywin32.pth")):
        os.unlink(os.path.join(sys.prefix, "pywin32.pth"))
    # The .pth may be new and therefore not loaded in this session.
    # Setup the paths just in case.
    for name in "win32 win32\\lib Pythonwin".split():
        sys.path.append(os.path.join(lib_dir, name))
    # It is possible people with old versions installed with still have
    # pywintypes and pythoncom registered.  We no longer need this, and stale
    # entries hurt us.
    for name in "pythoncom pywintypes".split():
        keyname = "Software\\Python\\PythonCore\\" + sys.winver + "\\Modules\\" + name
        for root in winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER:
            try:
                winreg.DeleteKey(root, keyname + "\\Debug")
            except OSError:
                pass
            try:
                winreg.DeleteKey(root, keyname)
            except OSError:
                pass
    LoadSystemModule(lib_dir, "pywintypes")
    LoadSystemModule(lib_dir, "pythoncom")
    import win32api

    # and now we can get the system directory:
    files = glob.glob(os.path.join(lib_dir, "pywin32_system32\\*.*"))
    if not files:
        raise RuntimeError("No system files to copy!!")
    # Try the system32 directory first - if that fails due to "access denied",
    # it implies a non-admin user, and we use sys.prefix
    for dest_dir in [get_system_dir(), sys.prefix]:
        # and copy some files over there
        worked = 0
        try:
            for fname in files:
                base = os.path.basename(fname)
                dst = os.path.join(dest_dir, base)
                CopyTo("installing %s" % base, fname, dst)
                if verbose:
                    print(f"Copied {base} to {dst}")
                worked = 1
                # Nuke any other versions that may exist - having
                # duplicates causes major headaches.
                bad_dest_dirs = [
                    os.path.join(sys.prefix, "Library\\bin"),
                    os.path.join(sys.prefix, "Lib\\site-packages\\win32"),
                ]
                if dest_dir != sys.prefix:
                    bad_dest_dirs.append(sys.prefix)
                for bad_dest_dir in bad_dest_dirs:
                    bad_fname = os.path.join(bad_dest_dir, base)
                    if os.path.exists(bad_fname):
                        # let exceptions go here - delete must succeed
                        os.unlink(bad_fname)
            if worked:
                break
        except win32api.error as details:
            if details.winerror == 5:
                # access denied - user not admin - try sys.prefix dir,
                # but first check that a version doesn't already exist
                # in that place - otherwise that one will still get used!
                if os.path.exists(dst):
                    msg = (
                        "The file '%s' exists, but can not be replaced "
                        "due to insufficient permissions.  You must "
                        "reinstall this software as an Administrator" % dst
                    )
                    print(msg)
                    raise RuntimeError(msg)
                continue
            raise
    else:
        raise RuntimeError(
            "You don't have enough permissions to install the system files"
        )

    # Register our demo COM objects.
    try:
        try:
            RegisterCOMObjects()
        except win32api.error as details:
            if details.winerror != 5:  # ERROR_ACCESS_DENIED
                raise
            print("You do not have the permissions to install COM objects.")
            print("The sample COM objects were not registered.")
    except Exception:
        print("FAILED to register the Python COM objects")
        traceback.print_exc()

    # There may be no main Python key in HKCU if, eg, an admin installed
    # python itself.
    winreg.CreateKey(get_root_hkey(), root_key_name)

    chm_file = None
    try:
        chm_file = RegisterHelpFile(True, lib_dir)
    except Exception:
        print("Failed to register help file")
        traceback.print_exc()
    else:
        if verbose:
            print("Registered help file")

    # misc other fixups.
    fixup_dbi()

    # Register Pythonwin in context menu
    try:
        RegisterPythonwin(True, lib_dir)
    except Exception:
        print("Failed to register pythonwin as editor")
        traceback.print_exc()
    else:
        if verbose:
            print("Pythonwin has been registered in context menu")

    # Create the win32com\gen_py directory.
    make_dir = os.path.join(lib_dir, "win32com", "gen_py")
    if not os.path.isdir(make_dir):
        if verbose:
            print(f"Creating directory {make_dir}")
        os.mkdir(make_dir)

    try:
        # create shortcuts
        # CSIDL_COMMON_PROGRAMS only available works on NT/2000/XP, and
        # will fail there if the user has no admin rights.
        fldr = get_shortcuts_folder()
        # If the group doesn't exist, then we don't make shortcuts - its
        # possible that this isn't a "normal" install.
        if os.path.isdir(fldr):
            dst = os.path.join(fldr, "PythonWin.lnk")
            create_shortcut(
                os.path.join(lib_dir, "Pythonwin\\Pythonwin.exe"),
                "The Pythonwin IDE",
                dst,
                "",
                sys.prefix,
            )
            if verbose:
                print("Shortcut for Pythonwin created")
            # And the docs.
            if chm_file:
                dst = os.path.join(fldr, "Python for Windows Documentation.lnk")
                doc = "Documentation for the PyWin32 extensions"
                create_shortcut(chm_file, doc, dst)
                if verbose:
                    print("Shortcut to documentation created")
        else:
            if verbose:
                print(f"Can't install shortcuts - {fldr!r} is not a folder")
    except Exception as details:
        print(details)

    # importing win32com.client ensures the gen_py dir created - not strictly
    # necessary to do now, but this makes the installation "complete"
    try:
        import win32com.client  # noqa
    except ImportError:
        # Don't let this error sound fatal
        pass
    print("The pywin32 extensions were successfully installed.")


def uninstall(lib_dir):
    # First ensure our system modules are loaded from pywin32_system, so
    # we can remove the ones we copied...
    LoadSystemModule(lib_dir, "pywintypes")
    LoadSystemModule(lib_dir, "pythoncom")

    try:
        RegisterCOMObjects(False)
    except Exception as why:
        print(f"Failed to unregister COM objects: {why}")

    try:
        RegisterHelpFile(False, lib_dir)
    except Exception as why:
        print(f"Failed to unregister help file: {why}")
    else:
        if verbose:
            print("Unregistered help file")

    try:
        RegisterPythonwin(False, lib_dir)
    except Exception as why:
        print(f"Failed to unregister Pythonwin: {why}")
    else:
        if verbose:
            print("Unregistered Pythonwin")

    try:
        # remove gen_py directory.
        gen_dir = os.path.join(lib_dir, "win32com", "gen_py")
        if os.path.isdir(gen_dir):
            shutil.rmtree(gen_dir)
            if verbose:
                print(f"Removed directory {gen_dir}")

        # Remove pythonwin compiled "config" files.
        pywin_dir = os.path.join(lib_dir, "Pythonwin", "pywin")
        for fname in glob.glob(os.path.join(pywin_dir, "*.cfc")):
            os.remove(fname)

        # The dbi.pyd.old files we may have created.
        try:
            os.remove(os.path.join(lib_dir, "win32", "dbi.pyd.old"))
        except OSError:
            pass
        try:
            os.remove(os.path.join(lib_dir, "win32", "dbi_d.pyd.old"))
        except OSError:
            pass

    except Exception as why:
        print(f"Failed to remove misc files: {why}")

    try:
        fldr = get_shortcuts_folder()
        for link in ("PythonWin.lnk", "Python for Windows Documentation.lnk"):
            fqlink = os.path.join(fldr, link)
            if os.path.isfile(fqlink):
                os.remove(fqlink)
                if verbose:
                    print(f"Removed {link}")
    except Exception as why:
        print(f"Failed to remove shortcuts: {why}")
    # Now remove the system32 files.
    files = glob.glob(os.path.join(lib_dir, "pywin32_system32\\*.*"))
    # Try the system32 directory first - if that fails due to "access denied",
    # it implies a non-admin user, and we use sys.prefix
    try:
        for dest_dir in [get_system_dir(), sys.prefix]:
            # and copy some files over there
            worked = 0
            for fname in files:
                base = os.path.basename(fname)
                dst = os.path.join(dest_dir, base)
                if os.path.isfile(dst):
                    try:
                        os.remove(dst)
                        worked = 1
                        if verbose:
                            print("Removed file %s" % (dst))
                    except Exception:
                        print(f"FAILED to remove {dst}")
            if worked:
                break
    except Exception as why:
        print(f"FAILED to remove system files: {why}")


# NOTE: This used to be run from inside the bdist_wininst created binary un/installer.
# From inside the binary installer this script HAD to NOT
# call sys.exit() or raise SystemExit, otherwise the installer would also terminate!
# Out of principle, we're still not using system exits.


def verify_destination(location: str) -> str:
    location = os.path.abspath(location)
    if not os.path.isdir(location):
        raise argparse.ArgumentTypeError(
            f'Path "{location}" is not an existing directory!'
        )
    return location


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""A post-install script for the pywin32 extensions.

    * Typical usage:

    > python -m pywin32_postinstall -install

    * or (shorter but you don't have control over which python environment is used)

    > pywin32_postinstall -install

    You need to execute this script, with a '-install' parameter,
    to ensure the environment is setup correctly to install COM objects, services, etc.
    """,
    )
    parser.add_argument(
        "-install",
        default=False,
        action="store_true",
        help="Configure the Python environment correctly for pywin32.",
    )
    parser.add_argument(
        "-remove",
        default=False,
        action="store_true",
        help="Try and remove everything that was installed or copied.",
    )
    parser.add_argument(
        "-wait",
        type=int,
        help="Wait for the specified process to terminate before starting.",
    )
    parser.add_argument(
        "-silent",
        default=False,
        action="store_true",
        help='Don\'t display the "Abort/Retry/Ignore" dialog for files in use.',
    )
    parser.add_argument(
        "-quiet",
        default=False,
        action="store_true",
        help="Don't display progress messages.",
    )
    parser.add_argument(
        "-destination",
        default=sysconfig.get_paths()["platlib"],
        type=verify_destination,
        help="Location of the PyWin32 installation",
    )

    args = parser.parse_args()

    if not args.quiet:
        print(f"Parsed arguments are: {args}")

    if not args.install ^ args.remove:
        parser.error("You need to either choose to -install or -remove!")

    if args.wait is not None:
        try:
            os.waitpid(args.wait, 0)
        except OSError:
            # child already dead
            pass

    silent = args.silent
    verbose = not args.quiet

    if args.install:
        install(args.destination)

    if args.remove:
        uninstall(args.destination)


if __name__ == "__main__":
    main()

# === NexusCore/myenv\Lib\site-packages\pip\_internal\operations\prepare.py ===
"""Prepares a distribution for installation
"""

# The following comment should be removed at some point in the future.
# mypy: strict-optional=False

import mimetypes
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.distributions import make_distribution_for_install_requirement
from pip._internal.distributions.installed import InstalledDistribution
from pip._internal.exceptions import (
    DirectoryUrlHashUnsupported,
    HashMismatch,
    HashUnpinned,
    InstallationError,
    MetadataInconsistent,
    NetworkConnectionError,
    VcsHashUnsupported,
)
from pip._internal.index.package_finder import PackageFinder
from pip._internal.metadata import BaseDistribution, get_metadata_distribution
from pip._internal.models.direct_url import ArchiveInfo
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.network.download import BatchDownloader, Downloader
from pip._internal.network.lazy_wheel import (
    HTTPRangeRequestUnsupported,
    dist_from_wheel_url,
)
from pip._internal.network.session import PipSession
from pip._internal.operations.build.build_tracker import BuildTracker
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils._log import getLogger
from pip._internal.utils.direct_url_helpers import (
    direct_url_for_editable,
    direct_url_from_link,
)
from pip._internal.utils.hashes import Hashes, MissingHashes
from pip._internal.utils.logging import indent_log
from pip._internal.utils.misc import (
    display_path,
    hash_file,
    hide_url,
    redact_auth_from_requirement,
)
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.unpacking import unpack_file
from pip._internal.vcs import vcs

logger = getLogger(__name__)


def _get_prepared_distribution(
    req: InstallRequirement,
    build_tracker: BuildTracker,
    finder: PackageFinder,
    build_isolation: bool,
    check_build_deps: bool,
) -> BaseDistribution:
    """Prepare a distribution for installation."""
    abstract_dist = make_distribution_for_install_requirement(req)
    tracker_id = abstract_dist.build_tracker_id
    if tracker_id is not None:
        with build_tracker.track(req, tracker_id):
            abstract_dist.prepare_distribution_metadata(
                finder, build_isolation, check_build_deps
            )
    return abstract_dist.get_metadata_distribution()


def unpack_vcs_link(link: Link, location: str, verbosity: int) -> None:
    vcs_backend = vcs.get_backend_for_scheme(link.scheme)
    assert vcs_backend is not None
    vcs_backend.unpack(location, url=hide_url(link.url), verbosity=verbosity)


@dataclass
class File:
    path: str
    content_type: Optional[str] = None

    def __post_init__(self) -> None:
        if self.content_type is None:
            self.content_type = mimetypes.guess_type(self.path)[0]


def get_http_url(
    link: Link,
    download: Downloader,
    download_dir: Optional[str] = None,
    hashes: Optional[Hashes] = None,
) -> File:
    temp_dir = TempDirectory(kind="unpack", globally_managed=True)
    # If a download dir is specified, is the file already downloaded there?
    already_downloaded_path = None
    if download_dir:
        already_downloaded_path = _check_download_dir(link, download_dir, hashes)

    if already_downloaded_path:
        from_path = already_downloaded_path
        content_type = None
    else:
        # let's download to a tmp dir
        from_path, content_type = download(link, temp_dir.path)
        if hashes:
            hashes.check_against_path(from_path)

    return File(from_path, content_type)


def get_file_url(
    link: Link, download_dir: Optional[str] = None, hashes: Optional[Hashes] = None
) -> File:
    """Get file and optionally check its hash."""
    # If a download dir is specified, is the file already there and valid?
    already_downloaded_path = None
    if download_dir:
        already_downloaded_path = _check_download_dir(link, download_dir, hashes)

    if already_downloaded_path:
        from_path = already_downloaded_path
    else:
        from_path = link.file_path

    # If --require-hashes is off, `hashes` is either empty, the
    # link's embedded hash, or MissingHashes; it is required to
    # match. If --require-hashes is on, we are satisfied by any
    # hash in `hashes` matching: a URL-based or an option-based
    # one; no internet-sourced hash will be in `hashes`.
    if hashes:
        hashes.check_against_path(from_path)
    return File(from_path, None)


def unpack_url(
    link: Link,
    location: str,
    download: Downloader,
    verbosity: int,
    download_dir: Optional[str] = None,
    hashes: Optional[Hashes] = None,
) -> Optional[File]:
    """Unpack link into location, downloading if required.

    :param hashes: A Hashes object, one of whose embedded hashes must match,
        or HashMismatch will be raised. If the Hashes is empty, no matches are
        required, and unhashable types of requirements (like VCS ones, which
        would ordinarily raise HashUnsupported) are allowed.
    """
    # non-editable vcs urls
    if link.is_vcs:
        unpack_vcs_link(link, location, verbosity=verbosity)
        return None

    assert not link.is_existing_dir()

    # file urls
    if link.is_file:
        file = get_file_url(link, download_dir, hashes=hashes)

    # http urls
    else:
        file = get_http_url(
            link,
            download,
            download_dir,
            hashes=hashes,
        )

    # unpack the archive to the build dir location. even when only downloading
    # archives, they have to be unpacked to parse dependencies, except wheels
    if not link.is_wheel:
        unpack_file(file.path, location, file.content_type)

    return file


def _check_download_dir(
    link: Link,
    download_dir: str,
    hashes: Optional[Hashes],
    warn_on_hash_mismatch: bool = True,
) -> Optional[str]:
    """Check download_dir for previously downloaded file with correct hash
    If a correct file is found return its path else None
    """
    download_path = os.path.join(download_dir, link.filename)

    if not os.path.exists(download_path):
        return None

    # If already downloaded, does its hash match?
    logger.info("File was already downloaded %s", download_path)
    if hashes:
        try:
            hashes.check_against_path(download_path)
        except HashMismatch:
            if warn_on_hash_mismatch:
                logger.warning(
                    "Previously-downloaded file %s has bad hash. Re-downloading.",
                    download_path,
                )
            os.unlink(download_path)
            return None
    return download_path


class RequirementPreparer:
    """Prepares a Requirement"""

    def __init__(
        self,
        build_dir: str,
        download_dir: Optional[str],
        src_dir: str,
        build_isolation: bool,
        check_build_deps: bool,
        build_tracker: BuildTracker,
        session: PipSession,
        progress_bar: str,
        finder: PackageFinder,
        require_hashes: bool,
        use_user_site: bool,
        lazy_wheel: bool,
        verbosity: int,
        legacy_resolver: bool,
    ) -> None:
        super().__init__()

        self.src_dir = src_dir
        self.build_dir = build_dir
        self.build_tracker = build_tracker
        self._session = session
        self._download = Downloader(session, progress_bar)
        self._batch_download = BatchDownloader(session, progress_bar)
        self.finder = finder

        # Where still-packed archives should be written to. If None, they are
        # not saved, and are deleted immediately after unpacking.
        self.download_dir = download_dir

        # Is build isolation allowed?
        self.build_isolation = build_isolation

        # Should check build dependencies?
        self.check_build_deps = check_build_deps

        # Should hash-checking be required?
        self.require_hashes = require_hashes

        # Should install in user site-packages?
        self.use_user_site = use_user_site

        # Should wheels be downloaded lazily?
        self.use_lazy_wheel = lazy_wheel

        # How verbose should underlying tooling be?
        self.verbosity = verbosity

        # Are we using the legacy resolver?
        self.legacy_resolver = legacy_resolver

        # Memoized downloaded files, as mapping of url: path.
        self._downloaded: Dict[str, str] = {}

        # Previous "header" printed for a link-based InstallRequirement
        self._previous_requirement_header = ("", "")

    def _log_preparing_link(self, req: InstallRequirement) -> None:
        """Provide context for the requirement being prepared."""
        if req.link.is_file and not req.is_wheel_from_cache:
            message = "Processing %s"
            information = str(display_path(req.link.file_path))
        else:
            message = "Collecting %s"
            information = redact_auth_from_requirement(req.req) if req.req else str(req)

        # If we used req.req, inject requirement source if available (this
        # would already be included if we used req directly)
        if req.req and req.comes_from:
            if isinstance(req.comes_from, str):
                comes_from: Optional[str] = req.comes_from
            else:
                comes_from = req.comes_from.from_path()
            if comes_from:
                information += f" (from {comes_from})"

        if (message, information) != self._previous_requirement_header:
            self._previous_requirement_header = (message, information)
            logger.info(message, information)

        if req.is_wheel_from_cache:
            with indent_log():
                logger.info("Using cached %s", req.link.filename)

    def _ensure_link_req_src_dir(
        self, req: InstallRequirement, parallel_builds: bool
    ) -> None:
        """Ensure source_dir of a linked InstallRequirement."""
        # Since source_dir is only set for editable requirements.
        if req.link.is_wheel:
            # We don't need to unpack wheels, so no need for a source
            # directory.
            return
        assert req.source_dir is None
        if req.link.is_existing_dir():
            # build local directories in-tree
            req.source_dir = req.link.file_path
            return

        # We always delete unpacked sdists after pip runs.
        req.ensure_has_source_dir(
            self.build_dir,
            autodelete=True,
            parallel_builds=parallel_builds,
        )
        req.ensure_pristine_source_checkout()

    def _get_linked_req_hashes(self, req: InstallRequirement) -> Hashes:
        # By the time this is called, the requirement's link should have
        # been checked so we can tell what kind of requirements req is
        # and raise some more informative errors than otherwise.
        # (For example, we can raise VcsHashUnsupported for a VCS URL
        # rather than HashMissing.)
        if not self.require_hashes:
            return req.hashes(trust_internet=True)

        # We could check these first 2 conditions inside unpack_url
        # and save repetition of conditions, but then we would
        # report less-useful error messages for unhashable
        # requirements, complaining that there's no hash provided.
        if req.link.is_vcs:
            raise VcsHashUnsupported()
        if req.link.is_existing_dir():
            raise DirectoryUrlHashUnsupported()

        # Unpinned packages are asking for trouble when a new version
        # is uploaded.  This isn't a security check, but it saves users
        # a surprising hash mismatch in the future.
        # file:/// URLs aren't pinnable, so don't complain about them
        # not being pinned.
        if not req.is_direct and not req.is_pinned:
            raise HashUnpinned()

        # If known-good hashes are missing for this requirement,
        # shim it with a facade object that will provoke hash
        # computation and then raise a HashMissing exception
        # showing the user what the hash should be.
        return req.hashes(trust_internet=False) or MissingHashes()

    def _fetch_metadata_only(
        self,
        req: InstallRequirement,
    ) -> Optional[BaseDistribution]:
        if self.legacy_resolver:
            logger.debug(
                "Metadata-only fetching is not used in the legacy resolver",
            )
            return None
        if self.require_hashes:
            logger.debug(
                "Metadata-only fetching is not used as hash checking is required",
            )
            return None
        # Try PEP 658 metadata first, then fall back to lazy wheel if unavailable.
        return self._fetch_metadata_using_link_data_attr(
            req
        ) or self._fetch_metadata_using_lazy_wheel(req.link)

    def _fetch_metadata_using_link_data_attr(
        self,
        req: InstallRequirement,
    ) -> Optional[BaseDistribution]:
        """Fetch metadata from the data-dist-info-metadata attribute, if possible."""
        # (1) Get the link to the metadata file, if provided by the backend.
        metadata_link = req.link.metadata_link()
        if metadata_link is None:
            return None
        assert req.req is not None
        logger.verbose(
            "Obtaining dependency information for %s from %s",
            req.req,
            metadata_link,
        )
        # (2) Download the contents of the METADATA file, separate from the dist itself.
        metadata_file = get_http_url(
            metadata_link,
            self._download,
            hashes=metadata_link.as_hashes(),
        )
        with open(metadata_file.path, "rb") as f:
            metadata_contents = f.read()
        # (3) Generate a dist just from those file contents.
        metadata_dist = get_metadata_distribution(
            metadata_contents,
            req.link.filename,
            req.req.name,
        )
        # (4) Ensure the Name: field from the METADATA file matches the name from the
        #     install requirement.
        #
        #     NB: raw_name will fall back to the name from the install requirement if
        #     the Name: field is not present, but it's noted in the raw_name docstring
        #     that that should NEVER happen anyway.
        if canonicalize_name(metadata_dist.raw_name) != canonicalize_name(req.req.name):
            raise MetadataInconsistent(
                req, "Name", req.req.name, metadata_dist.raw_name
            )
        return metadata_dist

    def _fetch_metadata_using_lazy_wheel(
        self,
        link: Link,
    ) -> Optional[BaseDistribution]:
        """Fetch metadata using lazy wheel, if possible."""
        # --use-feature=fast-deps must be provided.
        if not self.use_lazy_wheel:
            return None
        if link.is_file or not link.is_wheel:
            logger.debug(
                "Lazy wheel is not used as %r does not point to a remote wheel",
                link,
            )
            return None

        wheel = Wheel(link.filename)
        name = canonicalize_name(wheel.name)
        logger.info(
            "Obtaining dependency information from %s %s",
            name,
            wheel.version,
        )
        url = link.url.split("#", 1)[0]
        try:
            return dist_from_wheel_url(name, url, self._session)
        except HTTPRangeRequestUnsupported:
            logger.debug("%s does not support range requests", url)
            return None

    def _complete_partial_requirements(
        self,
        partially_downloaded_reqs: Iterable[InstallRequirement],
        parallel_builds: bool = False,
    ) -> None:
        """Download any requirements which were only fetched by metadata."""
        # Download to a temporary directory. These will be copied over as
        # needed for downstream 'download', 'wheel', and 'install' commands.
        temp_dir = TempDirectory(kind="unpack", globally_managed=True).path

        # Map each link to the requirement that owns it. This allows us to set
        # `req.local_file_path` on the appropriate requirement after passing
        # all the links at once into BatchDownloader.
        links_to_fully_download: Dict[Link, InstallRequirement] = {}
        for req in partially_downloaded_reqs:
            assert req.link
            links_to_fully_download[req.link] = req

        batch_download = self._batch_download(
            links_to_fully_download.keys(),
            temp_dir,
        )
        for link, (filepath, _) in batch_download:
            logger.debug("Downloading link %s to %s", link, filepath)
            req = links_to_fully_download[link]
            # Record the downloaded file path so wheel reqs can extract a Distribution
            # in .get_dist().
            req.local_file_path = filepath
            # Record that the file is downloaded so we don't do it again in
            # _prepare_linked_requirement().
            self._downloaded[req.link.url] = filepath

            # If this is an sdist, we need to unpack it after downloading, but the
            # .source_dir won't be set up until we are in _prepare_linked_requirement().
            # Add the downloaded archive to the install requirement to unpack after
            # preparing the source dir.
            if not req.is_wheel:
                req.needs_unpacked_archive(Path(filepath))

        # This step is necessary to ensure all lazy wheels are processed
        # successfully by the 'download', 'wheel', and 'install' commands.
        for req in partially_downloaded_reqs:
            self._prepare_linked_requirement(req, parallel_builds)

    def prepare_linked_requirement(
        self, req: InstallRequirement, parallel_builds: bool = False
    ) -> BaseDistribution:
        """Prepare a requirement to be obtained from req.link."""
        assert req.link
        self._log_preparing_link(req)
        with indent_log():
            # Check if the relevant file is already available
            # in the download directory
            file_path = None
            if self.download_dir is not None and req.link.is_wheel:
                hashes = self._get_linked_req_hashes(req)
                file_path = _check_download_dir(
                    req.link,
                    self.download_dir,
                    hashes,
                    # When a locally built wheel has been found in cache, we don't warn
                    # about re-downloading when the already downloaded wheel hash does
                    # not match. This is because the hash must be checked against the
                    # original link, not the cached link. It that case the already
                    # downloaded file will be removed and re-fetched from cache (which
                    # implies a hash check against the cache entry's origin.json).
                    warn_on_hash_mismatch=not req.is_wheel_from_cache,
                )

            if file_path is not None:
                # The file is already available, so mark it as downloaded
                self._downloaded[req.link.url] = file_path
            else:
                # The file is not available, attempt to fetch only metadata
                metadata_dist = self._fetch_metadata_only(req)
                if metadata_dist is not None:
                    req.needs_more_preparation = True
                    return metadata_dist

            # None of the optimizations worked, fully prepare the requirement
            return self._prepare_linked_requirement(req, parallel_builds)

    def prepare_linked_requirements_more(
        self, reqs: Iterable[InstallRequirement], parallel_builds: bool = False
    ) -> None:
        """Prepare linked requirements more, if needed."""
        reqs = [req for req in reqs if req.needs_more_preparation]
        for req in reqs:
            # Determine if any of these requirements were already downloaded.
            if self.download_dir is not None and req.link.is_wheel:
                hashes = self._get_linked_req_hashes(req)
                file_path = _check_download_dir(req.link, self.download_dir, hashes)
                if file_path is not None:
                    self._downloaded[req.link.url] = file_path
                    req.needs_more_preparation = False

        # Prepare requirements we found were already downloaded for some
        # reason. The other downloads will be completed separately.
        partially_downloaded_reqs: List[InstallRequirement] = []
        for req in reqs:
            if req.needs_more_preparation:
                partially_downloaded_reqs.append(req)
            else:
                self._prepare_linked_requirement(req, parallel_builds)

        # TODO: separate this part out from RequirementPreparer when the v1
        # resolver can be removed!
        self._complete_partial_requirements(
            partially_downloaded_reqs,
            parallel_builds=parallel_builds,
        )

    def _prepare_linked_requirement(
        self, req: InstallRequirement, parallel_builds: bool
    ) -> BaseDistribution:
        assert req.link
        link = req.link

        hashes = self._get_linked_req_hashes(req)

        if hashes and req.is_wheel_from_cache:
            assert req.download_info is not None
            assert link.is_wheel
            assert link.is_file
            # We need to verify hashes, and we have found the requirement in the cache
            # of locally built wheels.
            if (
                isinstance(req.download_info.info, ArchiveInfo)
                and req.download_info.info.hashes
                and hashes.has_one_of(req.download_info.info.hashes)
            ):
                # At this point we know the requirement was built from a hashable source
                # artifact, and we verified that the cache entry's hash of the original
                # artifact matches one of the hashes we expect. We don't verify hashes
                # against the cached wheel, because the wheel is not the original.
                hashes = None
            else:
                logger.warning(
                    "The hashes of the source archive found in cache entry "
                    "don't match, ignoring cached built wheel "
                    "and re-downloading source."
                )
                req.link = req.cached_wheel_source_link
                link = req.link

        self._ensure_link_req_src_dir(req, parallel_builds)

        if link.is_existing_dir():
            local_file = None
        elif link.url not in self._downloaded:
            try:
                local_file = unpack_url(
                    link,
                    req.source_dir,
                    self._download,
                    self.verbosity,
                    self.download_dir,
                    hashes,
                )
            except NetworkConnectionError as exc:
                raise InstallationError(
                    f"Could not install requirement {req} because of HTTP "
                    f"error {exc} for URL {link}"
                )
        else:
            file_path = self._downloaded[link.url]
            if hashes:
                hashes.check_against_path(file_path)
            local_file = File(file_path, content_type=None)

        # If download_info is set, we got it from the wheel cache.
        if req.download_info is None:
            # Editables don't go through this function (see
            # prepare_editable_requirement).
            assert not req.editable
            req.download_info = direct_url_from_link(link, req.source_dir)
            # Make sure we have a hash in download_info. If we got it as part of the
            # URL, it will have been verified and we can rely on it. Otherwise we
            # compute it from the downloaded file.
            # FIXME: https://github.com/pypa/pip/issues/11943
            if (
                isinstance(req.download_info.info, ArchiveInfo)
                and not req.download_info.info.hashes
                and local_file
            ):
                hash = hash_file(local_file.path)[0].hexdigest()
                # We populate info.hash for backward compatibility.
                # This will automatically populate info.hashes.
                req.download_info.info.hash = f"sha256={hash}"

        # For use in later processing,
        # preserve the file path on the requirement.
        if local_file:
            req.local_file_path = local_file.path

        dist = _get_prepared_distribution(
            req,
            self.build_tracker,
            self.finder,
            self.build_isolation,
            self.check_build_deps,
        )
        return dist

    def save_linked_requirement(self, req: InstallRequirement) -> None:
        assert self.download_dir is not None
        assert req.link is not None
        link = req.link
        if link.is_vcs or (link.is_existing_dir() and req.editable):
            # Make a .zip of the source_dir we already created.
            req.archive(self.download_dir)
            return

        if link.is_existing_dir():
            logger.debug(
                "Not copying link to destination directory "
                "since it is a directory: %s",
                link,
            )
            return
        if req.local_file_path is None:
            # No distribution was downloaded for this requirement.
            return

        download_location = os.path.join(self.download_dir, link.filename)
        if not os.path.exists(download_location):
            shutil.copy(req.local_file_path, download_location)
            download_path = display_path(download_location)
            logger.info("Saved %s", download_path)

    def prepare_editable_requirement(
        self,
        req: InstallRequirement,
    ) -> BaseDistribution:
        """Prepare an editable requirement."""
        assert req.editable, "cannot prepare a non-editable req as editable"

        logger.info("Obtaining %s", req)

        with indent_log():
            if self.require_hashes:
                raise InstallationError(
                    f"The editable requirement {req} cannot be installed when "
                    "requiring hashes, because there is no single file to "
                    "hash."
                )
            req.ensure_has_source_dir(self.src_dir)
            req.update_editable()
            assert req.source_dir
            req.download_info = direct_url_for_editable(req.unpacked_source_directory)

            dist = _get_prepared_distribution(
                req,
                self.build_tracker,
                self.finder,
                self.build_isolation,
                self.check_build_deps,
            )

            req.check_if_exists(self.use_user_site)

        return dist

    def prepare_installed_requirement(
        self,
        req: InstallRequirement,
        skip_reason: str,
    ) -> BaseDistribution:
        """Prepare an already-installed requirement."""
        assert req.satisfied_by, "req should have been satisfied but isn't"
        assert skip_reason is not None, (
            "did not get skip reason skipped but req.satisfied_by "
            f"is set to {req.satisfied_by}"
        )
        logger.info(
            "Requirement %s: %s (%s)", skip_reason, req, req.satisfied_by.version
        )
        with indent_log():
            if self.require_hashes:
                logger.debug(
                    "Since it is already installed, we are trusting this "
                    "package without checking its hash. To ensure a "
                    "completely repeatable environment, install into an "
                    "empty virtualenv."
                )
            return InstalledDistribution(req).get_metadata_distribution()

# === NexusCore/openenv\Lib\site-packages\anyio\_core\_synchronization.py ===
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from types import TracebackType

from sniffio import AsyncLibraryNotFoundError

from ..lowlevel import checkpoint
from ._eventloop import get_async_backend
from ._exceptions import BusyResourceError
from ._tasks import CancelScope
from ._testing import TaskInfo, get_current_task


@dataclass(frozen=True)
class EventStatistics:
    """
    :ivar int tasks_waiting: number of tasks waiting on :meth:`~.Event.wait`
    """

    tasks_waiting: int


@dataclass(frozen=True)
class CapacityLimiterStatistics:
    """
    :ivar int borrowed_tokens: number of tokens currently borrowed by tasks
    :ivar float total_tokens: total number of available tokens
    :ivar tuple borrowers: tasks or other objects currently holding tokens borrowed from
        this limiter
    :ivar int tasks_waiting: number of tasks waiting on
        :meth:`~.CapacityLimiter.acquire` or
        :meth:`~.CapacityLimiter.acquire_on_behalf_of`
    """

    borrowed_tokens: int
    total_tokens: float
    borrowers: tuple[object, ...]
    tasks_waiting: int


@dataclass(frozen=True)
class LockStatistics:
    """
    :ivar bool locked: flag indicating if this lock is locked or not
    :ivar ~anyio.TaskInfo owner: task currently holding the lock (or ``None`` if the
        lock is not held by any task)
    :ivar int tasks_waiting: number of tasks waiting on :meth:`~.Lock.acquire`
    """

    locked: bool
    owner: TaskInfo | None
    tasks_waiting: int


@dataclass(frozen=True)
class ConditionStatistics:
    """
    :ivar int tasks_waiting: number of tasks blocked on :meth:`~.Condition.wait`
    :ivar ~anyio.LockStatistics lock_statistics: statistics of the underlying
        :class:`~.Lock`
    """

    tasks_waiting: int
    lock_statistics: LockStatistics


@dataclass(frozen=True)
class SemaphoreStatistics:
    """
    :ivar int tasks_waiting: number of tasks waiting on :meth:`~.Semaphore.acquire`

    """

    tasks_waiting: int


class Event:
    def __new__(cls) -> Event:
        try:
            return get_async_backend().create_event()
        except AsyncLibraryNotFoundError:
            return EventAdapter()

    def set(self) -> None:
        """Set the flag, notifying all listeners."""
        raise NotImplementedError

    def is_set(self) -> bool:
        """Return ``True`` if the flag is set, ``False`` if not."""
        raise NotImplementedError

    async def wait(self) -> None:
        """
        Wait until the flag has been set.

        If the flag has already been set when this method is called, it returns
        immediately.

        """
        raise NotImplementedError

    def statistics(self) -> EventStatistics:
        """Return statistics about the current state of this event."""
        raise NotImplementedError


class EventAdapter(Event):
    _internal_event: Event | None = None
    _is_set: bool = False

    def __new__(cls) -> EventAdapter:
        return object.__new__(cls)

    @property
    def _event(self) -> Event:
        if self._internal_event is None:
            self._internal_event = get_async_backend().create_event()
            if self._is_set:
                self._internal_event.set()

        return self._internal_event

    def set(self) -> None:
        if self._internal_event is None:
            self._is_set = True
        else:
            self._event.set()

    def is_set(self) -> bool:
        if self._internal_event is None:
            return self._is_set

        return self._internal_event.is_set()

    async def wait(self) -> None:
        await self._event.wait()

    def statistics(self) -> EventStatistics:
        if self._internal_event is None:
            return EventStatistics(tasks_waiting=0)

        return self._internal_event.statistics()


class Lock:
    def __new__(cls, *, fast_acquire: bool = False) -> Lock:
        try:
            return get_async_backend().create_lock(fast_acquire=fast_acquire)
        except AsyncLibraryNotFoundError:
            return LockAdapter(fast_acquire=fast_acquire)

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.release()

    async def acquire(self) -> None:
        """Acquire the lock."""
        raise NotImplementedError

    def acquire_nowait(self) -> None:
        """
        Acquire the lock, without blocking.

        :raises ~anyio.WouldBlock: if the operation would block

        """
        raise NotImplementedError

    def release(self) -> None:
        """Release the lock."""
        raise NotImplementedError

    def locked(self) -> bool:
        """Return True if the lock is currently held."""
        raise NotImplementedError

    def statistics(self) -> LockStatistics:
        """
        Return statistics about the current state of this lock.

        .. versionadded:: 3.0
        """
        raise NotImplementedError


class LockAdapter(Lock):
    _internal_lock: Lock | None = None

    def __new__(cls, *, fast_acquire: bool = False) -> LockAdapter:
        return object.__new__(cls)

    def __init__(self, *, fast_acquire: bool = False):
        self._fast_acquire = fast_acquire

    @property
    def _lock(self) -> Lock:
        if self._internal_lock is None:
            self._internal_lock = get_async_backend().create_lock(
                fast_acquire=self._fast_acquire
            )

        return self._internal_lock

    async def __aenter__(self) -> None:
        await self._lock.acquire()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._internal_lock is not None:
            self._internal_lock.release()

    async def acquire(self) -> None:
        """Acquire the lock."""
        await self._lock.acquire()

    def acquire_nowait(self) -> None:
        """
        Acquire the lock, without blocking.

        :raises ~anyio.WouldBlock: if the operation would block

        """
        self._lock.acquire_nowait()

    def release(self) -> None:
        """Release the lock."""
        self._lock.release()

    def locked(self) -> bool:
        """Return True if the lock is currently held."""
        return self._lock.locked()

    def statistics(self) -> LockStatistics:
        """
        Return statistics about the current state of this lock.

        .. versionadded:: 3.0

        """
        if self._internal_lock is None:
            return LockStatistics(False, None, 0)

        return self._internal_lock.statistics()


class Condition:
    _owner_task: TaskInfo | None = None

    def __init__(self, lock: Lock | None = None):
        self._lock = lock or Lock()
        self._waiters: deque[Event] = deque()

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.release()

    def _check_acquired(self) -> None:
        if self._owner_task != get_current_task():
            raise RuntimeError("The current task is not holding the underlying lock")

    async def acquire(self) -> None:
        """Acquire the underlying lock."""
        await self._lock.acquire()
        self._owner_task = get_current_task()

    def acquire_nowait(self) -> None:
        """
        Acquire the underlying lock, without blocking.

        :raises ~anyio.WouldBlock: if the operation would block

        """
        self._lock.acquire_nowait()
        self._owner_task = get_current_task()

    def release(self) -> None:
        """Release the underlying lock."""
        self._lock.release()

    def locked(self) -> bool:
        """Return True if the lock is set."""
        return self._lock.locked()

    def notify(self, n: int = 1) -> None:
        """Notify exactly n listeners."""
        self._check_acquired()
        for _ in range(n):
            try:
                event = self._waiters.popleft()
            except IndexError:
                break

            event.set()

    def notify_all(self) -> None:
        """Notify all the listeners."""
        self._check_acquired()
        for event in self._waiters:
            event.set()

        self._waiters.clear()

    async def wait(self) -> None:
        """Wait for a notification."""
        await checkpoint()
        event = Event()
        self._waiters.append(event)
        self.release()
        try:
            await event.wait()
        except BaseException:
            if not event.is_set():
                self._waiters.remove(event)

            raise
        finally:
            with CancelScope(shield=True):
                await self.acquire()

    def statistics(self) -> ConditionStatistics:
        """
        Return statistics about the current state of this condition.

        .. versionadded:: 3.0
        """
        return ConditionStatistics(len(self._waiters), self._lock.statistics())


class Semaphore:
    def __new__(
        cls,
        initial_value: int,
        *,
        max_value: int | None = None,
        fast_acquire: bool = False,
    ) -> Semaphore:
        try:
            return get_async_backend().create_semaphore(
                initial_value, max_value=max_value, fast_acquire=fast_acquire
            )
        except AsyncLibraryNotFoundError:
            return SemaphoreAdapter(initial_value, max_value=max_value)

    def __init__(
        self,
        initial_value: int,
        *,
        max_value: int | None = None,
        fast_acquire: bool = False,
    ):
        if not isinstance(initial_value, int):
            raise TypeError("initial_value must be an integer")
        if initial_value < 0:
            raise ValueError("initial_value must be >= 0")
        if max_value is not None:
            if not isinstance(max_value, int):
                raise TypeError("max_value must be an integer or None")
            if max_value < initial_value:
                raise ValueError(
                    "max_value must be equal to or higher than initial_value"
                )

        self._fast_acquire = fast_acquire

    async def __aenter__(self) -> Semaphore:
        await self.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.release()

    async def acquire(self) -> None:
        """Decrement the semaphore value, blocking if necessary."""
        raise NotImplementedError

    def acquire_nowait(self) -> None:
        """
        Acquire the underlying lock, without blocking.

        :raises ~anyio.WouldBlock: if the operation would block

        """
        raise NotImplementedError

    def release(self) -> None:
        """Increment the semaphore value."""
        raise NotImplementedError

    @property
    def value(self) -> int:
        """The current value of the semaphore."""
        raise NotImplementedError

    @property
    def max_value(self) -> int | None:
        """The maximum value of the semaphore."""
        raise NotImplementedError

    def statistics(self) -> SemaphoreStatistics:
        """
        Return statistics about the current state of this semaphore.

        .. versionadded:: 3.0
        """
        raise NotImplementedError


class SemaphoreAdapter(Semaphore):
    _internal_semaphore: Semaphore | None = None

    def __new__(
        cls,
        initial_value: int,
        *,
        max_value: int | None = None,
        fast_acquire: bool = False,
    ) -> SemaphoreAdapter:
        return object.__new__(cls)

    def __init__(
        self,
        initial_value: int,
        *,
        max_value: int | None = None,
        fast_acquire: bool = False,
    ) -> None:
        super().__init__(initial_value, max_value=max_value, fast_acquire=fast_acquire)
        self._initial_value = initial_value
        self._max_value = max_value

    @property
    def _semaphore(self) -> Semaphore:
        if self._internal_semaphore is None:
            self._internal_semaphore = get_async_backend().create_semaphore(
                self._initial_value, max_value=self._max_value
            )

        return self._internal_semaphore

    async def acquire(self) -> None:
        await self._semaphore.acquire()

    def acquire_nowait(self) -> None:
        self._semaphore.acquire_nowait()

    def release(self) -> None:
        self._semaphore.release()

    @property
    def value(self) -> int:
        if self._internal_semaphore is None:
            return self._initial_value

        return self._semaphore.value

    @property
    def max_value(self) -> int | None:
        return self._max_value

    def statistics(self) -> SemaphoreStatistics:
        if self._internal_semaphore is None:
            return SemaphoreStatistics(tasks_waiting=0)

        return self._semaphore.statistics()


class CapacityLimiter:
    def __new__(cls, total_tokens: float) -> CapacityLimiter:
        try:
            return get_async_backend().create_capacity_limiter(total_tokens)
        except AsyncLibraryNotFoundError:
            return CapacityLimiterAdapter(total_tokens)

    async def __aenter__(self) -> None:
        raise NotImplementedError

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        raise NotImplementedError

    @property
    def total_tokens(self) -> float:
        """
        The total number of tokens available for borrowing.

        This is a read-write property. If the total number of tokens is increased, the
        proportionate number of tasks waiting on this limiter will be granted their
        tokens.

        .. versionchanged:: 3.0
            The property is now writable.

        """
        raise NotImplementedError

    @total_tokens.setter
    def total_tokens(self, value: float) -> None:
        raise NotImplementedError

    @property
    def borrowed_tokens(self) -> int:
        """The number of tokens that have currently been borrowed."""
        raise NotImplementedError

    @property
    def available_tokens(self) -> float:
        """The number of tokens currently available to be borrowed"""
        raise NotImplementedError

    def acquire_nowait(self) -> None:
        """
        Acquire a token for the current task without waiting for one to become
        available.

        :raises ~anyio.WouldBlock: if there are no tokens available for borrowing

        """
        raise NotImplementedError

    def acquire_on_behalf_of_nowait(self, borrower: object) -> None:
        """
        Acquire a token without waiting for one to become available.

        :param borrower: the entity borrowing a token
        :raises ~anyio.WouldBlock: if there are no tokens available for borrowing

        """
        raise NotImplementedError

    async def acquire(self) -> None:
        """
        Acquire a token for the current task, waiting if necessary for one to become
        available.

        """
        raise NotImplementedError

    async def acquire_on_behalf_of(self, borrower: object) -> None:
        """
        Acquire a token, waiting if necessary for one to become available.

        :param borrower: the entity borrowing a token

        """
        raise NotImplementedError

    def release(self) -> None:
        """
        Release the token held by the current task.

        :raises RuntimeError: if the current task has not borrowed a token from this
            limiter.

        """
        raise NotImplementedError

    def release_on_behalf_of(self, borrower: object) -> None:
        """
        Release the token held by the given borrower.

        :raises RuntimeError: if the borrower has not borrowed a token from this
            limiter.

        """
        raise NotImplementedError

    def statistics(self) -> CapacityLimiterStatistics:
        """
        Return statistics about the current state of this limiter.

        .. versionadded:: 3.0

        """
        raise NotImplementedError


class CapacityLimiterAdapter(CapacityLimiter):
    _internal_limiter: CapacityLimiter | None = None

    def __new__(cls, total_tokens: float) -> CapacityLimiterAdapter:
        return object.__new__(cls)

    def __init__(self, total_tokens: float) -> None:
        self.total_tokens = total_tokens

    @property
    def _limiter(self) -> CapacityLimiter:
        if self._internal_limiter is None:
            self._internal_limiter = get_async_backend().create_capacity_limiter(
                self._total_tokens
            )

        return self._internal_limiter

    async def __aenter__(self) -> None:
        await self._limiter.__aenter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        return await self._limiter.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def total_tokens(self) -> float:
        if self._internal_limiter is None:
            return self._total_tokens

        return self._internal_limiter.total_tokens

    @total_tokens.setter
    def total_tokens(self, value: float) -> None:
        if not isinstance(value, int) and value is not math.inf:
            raise TypeError("total_tokens must be an int or math.inf")
        elif value < 1:
            raise ValueError("total_tokens must be >= 1")

        if self._internal_limiter is None:
            self._total_tokens = value
            return

        self._limiter.total_tokens = value

    @property
    def borrowed_tokens(self) -> int:
        if self._internal_limiter is None:
            return 0

        return self._internal_limiter.borrowed_tokens

    @property
    def available_tokens(self) -> float:
        if self._internal_limiter is None:
            return self._total_tokens

        return self._internal_limiter.available_tokens

    def acquire_nowait(self) -> None:
        self._limiter.acquire_nowait()

    def acquire_on_behalf_of_nowait(self, borrower: object) -> None:
        self._limiter.acquire_on_behalf_of_nowait(borrower)

    async def acquire(self) -> None:
        await self._limiter.acquire()

    async def acquire_on_behalf_of(self, borrower: object) -> None:
        await self._limiter.acquire_on_behalf_of(borrower)

    def release(self) -> None:
        self._limiter.release()

    def release_on_behalf_of(self, borrower: object) -> None:
        self._limiter.release_on_behalf_of(borrower)

    def statistics(self) -> CapacityLimiterStatistics:
        if self._internal_limiter is None:
            return CapacityLimiterStatistics(
                borrowed_tokens=0,
                total_tokens=self.total_tokens,
                borrowers=(),
                tasks_waiting=0,
            )

        return self._internal_limiter.statistics()


class ResourceGuard:
    """
    A context manager for ensuring that a resource is only used by a single task at a
    time.

    Entering this context manager while the previous has not exited it yet will trigger
    :exc:`BusyResourceError`.

    :param action: the action to guard against (visible in the :exc:`BusyResourceError`
        when triggered, e.g. "Another task is already {action} this resource")

    .. versionadded:: 4.1
    """

    __slots__ = "action", "_guarded"

    def __init__(self, action: str = "using"):
        self.action: str = action
        self._guarded = False

    def __enter__(self) -> None:
        if self._guarded:
            raise BusyResourceError(self.action)

        self._guarded = True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._guarded = False

# === NexusCore/openenv\Lib\site-packages\litellm\types\router.py ===
"""
litellm.Router Types - includes RouterConfig, UpdateRouterConfig, ModelInfo etc
"""

import datetime
import enum
import uuid
from typing import Any, Dict, List, Literal, Optional, Tuple, Union, get_type_hints

import httpx
from httpx import AsyncClient, Client
from openai import AsyncAzureOpenAI, AsyncOpenAI, AzureOpenAI, OpenAI
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Required, TypedDict

from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler, HTTPHandler

from ..exceptions import RateLimitError
from .completion import CompletionRequest
from .embedding import EmbeddingRequest
from .llms.openai import OpenAIFileObject
from .llms.vertex_ai import VERTEX_CREDENTIALS_TYPES
from .utils import ModelResponse, ProviderSpecificModelInfo


class ConfigurableClientsideParamsCustomAuth(TypedDict):
    api_base: str


CONFIGURABLE_CLIENTSIDE_AUTH_PARAMS = Optional[
    List[Union[str, ConfigurableClientsideParamsCustomAuth]]
]


class ModelConfig(BaseModel):
    model_name: str
    litellm_params: Union[CompletionRequest, EmbeddingRequest]
    tpm: int
    rpm: int

    model_config = ConfigDict(protected_namespaces=())


class RouterConfig(BaseModel):
    model_list: List[ModelConfig]

    redis_url: Optional[str] = None
    redis_host: Optional[str] = None
    redis_port: Optional[int] = None
    redis_password: Optional[str] = None

    cache_responses: Optional[bool] = False
    cache_kwargs: Optional[Dict] = {}
    caching_groups: Optional[List[Tuple[str, List[str]]]] = None
    client_ttl: Optional[int] = 3600
    num_retries: Optional[int] = 0
    timeout: Optional[float] = None
    default_litellm_params: Optional[Dict[str, str]] = {}
    set_verbose: Optional[bool] = False
    fallbacks: Optional[List] = []
    allowed_fails: Optional[int] = None
    context_window_fallbacks: Optional[List] = []
    model_group_alias: Optional[Dict[str, List[str]]] = {}
    retry_after: Optional[int] = 0
    routing_strategy: Literal[
        "simple-shuffle",
        "least-busy",
        "usage-based-routing",
        "latency-based-routing",
    ] = "simple-shuffle"

    model_config = ConfigDict(protected_namespaces=())


class UpdateRouterConfig(BaseModel):
    """
    Set of params that you can modify via `router.update_settings()`.
    """

    routing_strategy_args: Optional[dict] = None
    routing_strategy: Optional[str] = None
    model_group_retry_policy: Optional[dict] = None
    allowed_fails: Optional[int] = None
    cooldown_time: Optional[float] = None
    num_retries: Optional[int] = None
    timeout: Optional[float] = None
    max_retries: Optional[int] = None
    retry_after: Optional[float] = None
    fallbacks: Optional[List[dict]] = None
    context_window_fallbacks: Optional[List[dict]] = None

    model_config = ConfigDict(protected_namespaces=())


class ModelInfo(BaseModel):
    id: Optional[
        str
    ]  # Allow id to be optional on input, but it will always be present as a str in the model instance
    db_model: bool = False  # used for proxy - to separate models which are stored in the db vs. config.
    updated_at: Optional[datetime.datetime] = None
    updated_by: Optional[str] = None

    created_at: Optional[datetime.datetime] = None
    created_by: Optional[str] = None

    base_model: Optional[
        str
    ] = None  # specify if the base model is azure/gpt-3.5-turbo etc for accurate cost tracking
    tier: Optional[Literal["free", "paid"]] = None

    """
    Team Model Specific Fields
    """
    # the team id that this model belongs to
    team_id: Optional[str] = None

    # the model_name that can be used by the team when making LLM calls
    team_public_model_name: Optional[str] = None

    def __init__(self, id: Optional[Union[str, int]] = None, **params):
        if id is None:
            id = str(uuid.uuid4())  # Generate a UUID if id is None or not provided
        elif isinstance(id, int):
            id = str(id)
        super().__init__(id=id, **params)

    model_config = ConfigDict(extra="allow")

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)


class CredentialLiteLLMParams(BaseModel):
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    ## VERTEX AI ##
    vertex_project: Optional[str] = None
    vertex_location: Optional[str] = None
    vertex_credentials: Optional[Union[str, dict]] = None
    ## UNIFIED PROJECT/REGION ##
    region_name: Optional[str] = None

    ## AWS BEDROCK / SAGEMAKER ##
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region_name: Optional[str] = None
    ## IBM WATSONX ##
    watsonx_region_name: Optional[str] = None


class CustomPricingLiteLLMParams(BaseModel):
    ## CUSTOM PRICING ##
    input_cost_per_token: Optional[float] = None
    output_cost_per_token: Optional[float] = None
    input_cost_per_second: Optional[float] = None
    output_cost_per_second: Optional[float] = None
    input_cost_per_pixel: Optional[float] = None
    output_cost_per_pixel: Optional[float] = None


class GenericLiteLLMParams(CredentialLiteLLMParams, CustomPricingLiteLLMParams):
    """
    LiteLLM Params without 'model' arg (used across completion / assistants api)
    """

    custom_llm_provider: Optional[str] = None
    tpm: Optional[int] = None
    rpm: Optional[int] = None
    timeout: Optional[
        Union[float, str, httpx.Timeout]
    ] = None  # if str, pass in as os.environ/
    stream_timeout: Optional[
        Union[float, str]
    ] = None  # timeout when making stream=True calls, if str, pass in as os.environ/
    max_retries: Optional[int] = None
    organization: Optional[str] = None  # for openai orgs
    configurable_clientside_auth_params: CONFIGURABLE_CLIENTSIDE_AUTH_PARAMS = None
    litellm_credential_name: Optional[str] = None

    ## LOGGING PARAMS ##
    litellm_trace_id: Optional[str] = None

    max_file_size_mb: Optional[float] = None

    # Deployment budgets
    max_budget: Optional[float] = None
    budget_duration: Optional[str] = None
    use_in_pass_through: Optional[bool] = False
    use_litellm_proxy: Optional[bool] = False
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    merge_reasoning_content_in_choices: Optional[bool] = False
    model_info: Optional[Dict] = None
    mock_response: Optional[Union[str, ModelResponse, Exception, Any]] = None

    def __init__(
        self,
        custom_llm_provider: Optional[str] = None,
        max_retries: Optional[Union[int, str]] = None,
        tpm: Optional[int] = None,
        rpm: Optional[int] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        api_version: Optional[str] = None,
        timeout: Optional[Union[float, str]] = None,  # if str, pass in as os.environ/
        stream_timeout: Optional[Union[float, str]] = (
            None  # timeout when making stream=True calls, if str, pass in as os.environ/
        ),
        organization: Optional[str] = None,  # for openai orgs
        ## LOGGING PARAMS ##
        litellm_trace_id: Optional[str] = None,
        ## UNIFIED PROJECT/REGION ##
        region_name: Optional[str] = None,
        ## VERTEX AI ##
        vertex_project: Optional[str] = None,
        vertex_location: Optional[str] = None,
        vertex_credentials: Optional[VERTEX_CREDENTIALS_TYPES] = None,
        ## AWS BEDROCK / SAGEMAKER ##
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region_name: Optional[str] = None,
        ## IBM WATSONX ##
        watsonx_region_name: Optional[str] = None,
        input_cost_per_token: Optional[float] = None,
        output_cost_per_token: Optional[float] = None,
        input_cost_per_second: Optional[float] = None,
        output_cost_per_second: Optional[float] = None,
        max_file_size_mb: Optional[float] = None,
        # Deployment budgets
        max_budget: Optional[float] = None,
        budget_duration: Optional[str] = None,
        # Pass through params
        use_in_pass_through: Optional[bool] = False,
        # Dynamic param to force using litellm proxy
        use_litellm_proxy: Optional[bool] = False,
        # This will merge the reasoning content in the choices
        merge_reasoning_content_in_choices: Optional[bool] = False,
        model_info: Optional[Dict] = None,
        mock_response: Optional[Union[str, ModelResponse, Exception, Any]] = None,
        **params,
    ):
        args = locals()
        args.pop("max_retries", None)
        args.pop("self", None)
        args.pop("params", None)
        args.pop("__class__", None)
        if max_retries is not None and isinstance(max_retries, str):
            max_retries = int(max_retries)  # cast to int
        # We need to keep max_retries in args since it's a parameter of GenericLiteLLMParams
        args[
            "max_retries"
        ] = max_retries  # Put max_retries back in args after popping it
        super().__init__(**args, **params)

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)


class LiteLLM_Params(GenericLiteLLMParams):
    """
    LiteLLM Params with 'model' requirement - used for completions
    """

    model: str
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def __init__(
        self,
        model: str,
        custom_llm_provider: Optional[str] = None,
        max_retries: Optional[Union[int, str]] = None,
        tpm: Optional[int] = None,
        rpm: Optional[int] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        api_version: Optional[str] = None,
        timeout: Optional[Union[float, str]] = None,  # if str, pass in as os.environ/
        stream_timeout: Optional[Union[float, str]] = (
            None  # timeout when making stream=True calls, if str, pass in as os.environ/
        ),
        organization: Optional[str] = None,  # for openai orgs
        ## VERTEX AI ##
        vertex_project: Optional[str] = None,
        vertex_location: Optional[str] = None,
        ## AWS BEDROCK / SAGEMAKER ##
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region_name: Optional[str] = None,
        # OpenAI / Azure Whisper
        # set a max-size of file that can be passed to litellm proxy
        max_file_size_mb: Optional[float] = None,
        # will use deployment on pass-through endpoints if True
        use_in_pass_through: Optional[bool] = False,
        use_litellm_proxy: Optional[bool] = False,
        **params,
    ):
        args = locals()
        args.pop("max_retries", None)
        args.pop("self", None)
        args.pop("params", None)
        args.pop("__class__", None)
        if max_retries is not None and isinstance(max_retries, str):
            max_retries = int(max_retries)  # cast to int
        super().__init__(max_retries=max_retries, **args, **params)

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)


class updateLiteLLMParams(GenericLiteLLMParams):
    # This class is used to update the LiteLLM_Params
    # only differece is model is optional
    model: Optional[str] = None


class updateDeployment(BaseModel):
    model_name: Optional[str] = None
    litellm_params: Optional[updateLiteLLMParams] = None
    model_info: Optional[ModelInfo] = None

    model_config = ConfigDict(protected_namespaces=())


class LiteLLMParamsTypedDict(TypedDict, total=False):
    model: str
    custom_llm_provider: Optional[str]
    tpm: Optional[int]
    rpm: Optional[int]
    order: Optional[int]
    weight: Optional[int]
    max_parallel_requests: Optional[int]
    api_key: Optional[str]
    api_base: Optional[str]
    api_version: Optional[str]
    timeout: Optional[Union[float, str, httpx.Timeout]]
    stream_timeout: Optional[Union[float, str]]
    max_retries: Optional[int]
    organization: Optional[Union[List, str]]  # for openai orgs
    configurable_clientside_auth_params: CONFIGURABLE_CLIENTSIDE_AUTH_PARAMS  # for allowing api base switching on finetuned models
    ## DROP PARAMS ##
    drop_params: Optional[bool]
    ## UNIFIED PROJECT/REGION ##
    region_name: Optional[str]
    ## VERTEX AI ##
    vertex_project: Optional[str]
    vertex_location: Optional[str]
    ## AWS BEDROCK / SAGEMAKER ##
    aws_access_key_id: Optional[str]
    aws_secret_access_key: Optional[str]
    aws_region_name: Optional[str]
    ## IBM WATSONX ##
    watsonx_region_name: Optional[str]
    ## CUSTOM PRICING ##
    input_cost_per_token: Optional[float]
    output_cost_per_token: Optional[float]
    input_cost_per_second: Optional[float]
    output_cost_per_second: Optional[float]
    num_retries: Optional[int]
    ## MOCK RESPONSES ##
    mock_response: Optional[Union[str, ModelResponse, Exception]]

    # routing params
    # use this for tag-based routing
    tags: Optional[List[str]]

    # deployment budgets
    max_budget: Optional[float]
    budget_duration: Optional[str]


class DeploymentTypedDict(TypedDict, total=False):
    model_name: Required[str]
    litellm_params: Required[LiteLLMParamsTypedDict]
    model_info: dict


SPECIAL_MODEL_INFO_PARAMS = [
    "input_cost_per_token",
    "output_cost_per_token",
    "input_cost_per_character",
    "output_cost_per_character",
]


class Deployment(BaseModel):
    model_name: str
    litellm_params: LiteLLM_Params
    model_info: ModelInfo

    model_config = ConfigDict(extra="allow", protected_namespaces=())

    def __init__(
        self,
        model_name: str,
        litellm_params: LiteLLM_Params,
        model_info: Optional[Union[ModelInfo, dict]] = None,
        **params,
    ):
        if model_info is None:
            model_info = ModelInfo()
        elif isinstance(model_info, dict):
            model_info = ModelInfo(**model_info)

        for (
            key
        ) in (
            SPECIAL_MODEL_INFO_PARAMS
        ):  # ensures custom pricing info is consistently in 'model_info'
            field = getattr(litellm_params, key, None)
            if field is not None:
                setattr(model_info, key, field)

        super().__init__(
            model_info=model_info,
            model_name=model_name,
            litellm_params=litellm_params,
            **params,
        )

    def to_json(self, **kwargs):
        try:
            return self.model_dump(**kwargs)  # noqa
        except Exception as e:
            # if using pydantic v1
            return self.dict(**kwargs)

    def __contains__(self, key):
        # Define custom behavior for the 'in' operator
        return hasattr(self, key)

    def get(self, key, default=None):
        # Custom .get() method to access attributes with a default value if the attribute doesn't exist
        return getattr(self, key, default)

    def __getitem__(self, key):
        # Allow dictionary-style access to attributes
        return getattr(self, key)

    def __setitem__(self, key, value):
        # Allow dictionary-style assignment of attributes
        setattr(self, key, value)


class RouterErrors(enum.Enum):
    """
    Enum for router specific errors with common codes
    """

    user_defined_ratelimit_error = "Deployment over user-defined ratelimit."
    no_deployments_available = "No deployments available for selected model"
    no_deployments_with_tag_routing = (
        "Not allowed to access model due to tags configuration"
    )
    no_deployments_with_provider_budget_routing = (
        "No deployments available - crossed budget"
    )


class AllowedFailsPolicy(BaseModel):
    """
    Use this to set a custom number of allowed fails/minute before cooling down a deployment
    If `AuthenticationErrorAllowedFails = 1000`, then 1000 AuthenticationError will be allowed before cooling down a deployment

    Mapping of Exception type to allowed_fails for each exception
    https://docs.litellm.ai/docs/exception_mapping
    """

    BadRequestErrorAllowedFails: Optional[int] = None
    AuthenticationErrorAllowedFails: Optional[int] = None
    TimeoutErrorAllowedFails: Optional[int] = None
    RateLimitErrorAllowedFails: Optional[int] = None
    ContentPolicyViolationErrorAllowedFails: Optional[int] = None
    InternalServerErrorAllowedFails: Optional[int] = None


class RetryPolicy(BaseModel):
    """
    Use this to set a custom number of retries per exception type
    If RateLimitErrorRetries = 3, then 3 retries will be made for RateLimitError
    Mapping of Exception type to number of retries
    https://docs.litellm.ai/docs/exception_mapping
    """

    BadRequestErrorRetries: Optional[int] = None
    AuthenticationErrorRetries: Optional[int] = None
    TimeoutErrorRetries: Optional[int] = None
    RateLimitErrorRetries: Optional[int] = None
    ContentPolicyViolationErrorRetries: Optional[int] = None
    InternalServerErrorRetries: Optional[int] = None


class AlertingConfig(BaseModel):
    """
    Use this configure alerting for the router. Receive alerts on the following events
    - LLM API Exceptions
    - LLM Responses Too Slow
    - LLM Requests Hanging

    Args:
        webhook_url: str            - webhook url for alerting, slack provides a webhook url to send alerts to
        alerting_threshold: Optional[float] = None - threshold for slow / hanging llm responses (in seconds)
    """

    webhook_url: str
    alerting_threshold: Optional[float] = 300


class ModelGroupInfo(BaseModel):
    model_group: str
    providers: List[str]
    max_input_tokens: Optional[float] = None
    max_output_tokens: Optional[float] = None
    input_cost_per_token: Optional[float] = None
    output_cost_per_token: Optional[float] = None
    mode: Optional[
        Union[
            str,
            Literal[
                "chat",
                "embedding",
                "completion",
                "image_generation",
                "audio_transcription",
                "rerank",
                "moderations",
            ],
        ]
    ] = Field(default="chat")
    tpm: Optional[int] = None
    rpm: Optional[int] = None
    supports_parallel_function_calling: bool = Field(default=False)
    supports_vision: bool = Field(default=False)
    supports_web_search: bool = Field(default=False)
    supports_url_context: bool = Field(default=False)
    supports_reasoning: bool = Field(default=False)
    supports_function_calling: bool = Field(default=False)
    supported_openai_params: Optional[List[str]] = Field(default=[])
    configurable_clientside_auth_params: CONFIGURABLE_CLIENTSIDE_AUTH_PARAMS = None

    def __init__(self, **data):
        for field_name, field_type in get_type_hints(self.__class__).items():
            if field_type == bool and data.get(field_name) is None:
                data[field_name] = False
        super().__init__(**data)


class AssistantsTypedDict(TypedDict):
    custom_llm_provider: Literal["azure", "openai"]
    litellm_params: LiteLLMParamsTypedDict


class FineTuningConfig(BaseModel):
    custom_llm_provider: Literal["azure", "openai"]


class CustomRoutingStrategyBase:
    async def async_get_available_deployment(
        self,
        model: str,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List]] = None,
        specific_deployment: Optional[bool] = False,
        request_kwargs: Optional[Dict] = None,
    ):
        """
        Asynchronously retrieves the available deployment based on the given parameters.

        Args:
            model (str): The name of the model.
            messages (Optional[List[Dict[str, str]]], optional): The list of messages for a given request. Defaults to None.
            input (Optional[Union[str, List]], optional): The input for a given embedding request. Defaults to None.
            specific_deployment (Optional[bool], optional): Whether to retrieve a specific deployment. Defaults to False.
            request_kwargs (Optional[Dict], optional): Additional request keyword arguments. Defaults to None.

        Returns:
            Returns an element from litellm.router.model_list

        """
        pass

    def get_available_deployment(
        self,
        model: str,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List]] = None,
        specific_deployment: Optional[bool] = False,
        request_kwargs: Optional[Dict] = None,
    ):
        """
        Synchronously retrieves the available deployment based on the given parameters.

        Args:
            model (str): The name of the model.
            messages (Optional[List[Dict[str, str]]], optional): The list of messages for a given request. Defaults to None.
            input (Optional[Union[str, List]], optional): The input for a given embedding request. Defaults to None.
            specific_deployment (Optional[bool], optional): Whether to retrieve a specific deployment. Defaults to False.
            request_kwargs (Optional[Dict], optional): Additional request keyword arguments. Defaults to None.

        Returns:
            Returns an element from litellm.router.model_list

        """
        pass


class RouterGeneralSettings(BaseModel):
    async_only_mode: bool = Field(
        default=False
    )  # this will only initialize async clients. Good for memory utils
    pass_through_all_models: bool = Field(
        default=False
    )  # if passed a model not llm_router model list, pass through the request to litellm.acompletion/embedding


class RouterRateLimitErrorBasic(ValueError):
    """
    Raise a basic error inside helper functions.
    """

    def __init__(
        self,
        model: str,
    ):
        self.model = model
        _message = f"{RouterErrors.no_deployments_available.value}."
        super().__init__(_message)


class RouterRateLimitError(ValueError):
    def __init__(
        self,
        model: str,
        cooldown_time: float,
        enable_pre_call_checks: bool,
        cooldown_list: List,
    ):
        self.model = model
        self.cooldown_time = cooldown_time
        self.enable_pre_call_checks = enable_pre_call_checks
        self.cooldown_list = cooldown_list
        _message = f"{RouterErrors.no_deployments_available.value}, Try again in {cooldown_time} seconds. Passed model={model}. pre-call-checks={enable_pre_call_checks}, cooldown_list={cooldown_list}"
        super().__init__(_message)


class RouterModelGroupAliasItem(TypedDict):
    model: str
    hidden: bool  # if 'True', don't return on `.get_model_list`


VALID_LITELLM_ENVIRONMENTS = [
    "development",
    "staging",
    "production",
]


class RoutingStrategy(enum.Enum):
    LEAST_BUSY = "least-busy"
    LATENCY_BASED = "latency-based-routing"
    COST_BASED = "cost-based-routing"
    USAGE_BASED_ROUTING_V2 = "usage-based-routing-v2"
    USAGE_BASED_ROUTING = "usage-based-routing"
    PROVIDER_BUDGET_LIMITING = "provider-budget-routing"


class RouterCacheEnum(enum.Enum):
    TPM = "global_router:{id}:{model}:tpm:{current_minute}"
    RPM = "global_router:{id}:{model}:rpm:{current_minute}"


class GenericBudgetWindowDetails(BaseModel):
    """Details about a provider's budget window"""

    budget_start: float
    spend_key: str
    start_time_key: str
    ttl_seconds: int


OptionalPreCallChecks = List[
    Literal[
        "prompt_caching", "router_budget_limiting", "responses_api_deployment_check"
    ]
]


class LiteLLM_RouterFileObject(TypedDict, total=False):
    """
    Tracking the litellm params hash, used for mapping the file id to the right model
    """

    litellm_params_sensitive_credential_hash: str
    file_object: OpenAIFileObject

# === NexusCore/openenv\Lib\site-packages\pip\_internal\operations\prepare.py ===
"""Prepares a distribution for installation
"""

# The following comment should be removed at some point in the future.
# mypy: strict-optional=False

import mimetypes
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from pip._vendor.packaging.utils import canonicalize_name

from pip._internal.distributions import make_distribution_for_install_requirement
from pip._internal.distributions.installed import InstalledDistribution
from pip._internal.exceptions import (
    DirectoryUrlHashUnsupported,
    HashMismatch,
    HashUnpinned,
    InstallationError,
    MetadataInconsistent,
    NetworkConnectionError,
    VcsHashUnsupported,
)
from pip._internal.index.package_finder import PackageFinder
from pip._internal.metadata import BaseDistribution, get_metadata_distribution
from pip._internal.models.direct_url import ArchiveInfo
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.network.download import BatchDownloader, Downloader
from pip._internal.network.lazy_wheel import (
    HTTPRangeRequestUnsupported,
    dist_from_wheel_url,
)
from pip._internal.network.session import PipSession
from pip._internal.operations.build.build_tracker import BuildTracker
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils._log import getLogger
from pip._internal.utils.direct_url_helpers import (
    direct_url_for_editable,
    direct_url_from_link,
)
from pip._internal.utils.hashes import Hashes, MissingHashes
from pip._internal.utils.logging import indent_log
from pip._internal.utils.misc import (
    display_path,
    hash_file,
    hide_url,
    redact_auth_from_requirement,
)
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.unpacking import unpack_file
from pip._internal.vcs import vcs

logger = getLogger(__name__)


def _get_prepared_distribution(
    req: InstallRequirement,
    build_tracker: BuildTracker,
    finder: PackageFinder,
    build_isolation: bool,
    check_build_deps: bool,
) -> BaseDistribution:
    """Prepare a distribution for installation."""
    abstract_dist = make_distribution_for_install_requirement(req)
    tracker_id = abstract_dist.build_tracker_id
    if tracker_id is not None:
        with build_tracker.track(req, tracker_id):
            abstract_dist.prepare_distribution_metadata(
                finder, build_isolation, check_build_deps
            )
    return abstract_dist.get_metadata_distribution()


def unpack_vcs_link(link: Link, location: str, verbosity: int) -> None:
    vcs_backend = vcs.get_backend_for_scheme(link.scheme)
    assert vcs_backend is not None
    vcs_backend.unpack(location, url=hide_url(link.url), verbosity=verbosity)


@dataclass
class File:
    path: str
    content_type: Optional[str] = None

    def __post_init__(self) -> None:
        if self.content_type is None:
            self.content_type = mimetypes.guess_type(self.path)[0]


def get_http_url(
    link: Link,
    download: Downloader,
    download_dir: Optional[str] = None,
    hashes: Optional[Hashes] = None,
) -> File:
    temp_dir = TempDirectory(kind="unpack", globally_managed=True)
    # If a download dir is specified, is the file already downloaded there?
    already_downloaded_path = None
    if download_dir:
        already_downloaded_path = _check_download_dir(link, download_dir, hashes)

    if already_downloaded_path:
        from_path = already_downloaded_path
        content_type = None
    else:
        # let's download to a tmp dir
        from_path, content_type = download(link, temp_dir.path)
        if hashes:
            hashes.check_against_path(from_path)

    return File(from_path, content_type)


def get_file_url(
    link: Link, download_dir: Optional[str] = None, hashes: Optional[Hashes] = None
) -> File:
    """Get file and optionally check its hash."""
    # If a download dir is specified, is the file already there and valid?
    already_downloaded_path = None
    if download_dir:
        already_downloaded_path = _check_download_dir(link, download_dir, hashes)

    if already_downloaded_path:
        from_path = already_downloaded_path
    else:
        from_path = link.file_path

    # If --require-hashes is off, `hashes` is either empty, the
    # link's embedded hash, or MissingHashes; it is required to
    # match. If --require-hashes is on, we are satisfied by any
    # hash in `hashes` matching: a URL-based or an option-based
    # one; no internet-sourced hash will be in `hashes`.
    if hashes:
        hashes.check_against_path(from_path)
    return File(from_path, None)


def unpack_url(
    link: Link,
    location: str,
    download: Downloader,
    verbosity: int,
    download_dir: Optional[str] = None,
    hashes: Optional[Hashes] = None,
) -> Optional[File]:
    """Unpack link into location, downloading if required.

    :param hashes: A Hashes object, one of whose embedded hashes must match,
        or HashMismatch will be raised. If the Hashes is empty, no matches are
        required, and unhashable types of requirements (like VCS ones, which
        would ordinarily raise HashUnsupported) are allowed.
    """
    # non-editable vcs urls
    if link.is_vcs:
        unpack_vcs_link(link, location, verbosity=verbosity)
        return None

    assert not link.is_existing_dir()

    # file urls
    if link.is_file:
        file = get_file_url(link, download_dir, hashes=hashes)

    # http urls
    else:
        file = get_http_url(
            link,
            download,
            download_dir,
            hashes=hashes,
        )

    # unpack the archive to the build dir location. even when only downloading
    # archives, they have to be unpacked to parse dependencies, except wheels
    if not link.is_wheel:
        unpack_file(file.path, location, file.content_type)

    return file


def _check_download_dir(
    link: Link,
    download_dir: str,
    hashes: Optional[Hashes],
    warn_on_hash_mismatch: bool = True,
) -> Optional[str]:
    """Check download_dir for previously downloaded file with correct hash
    If a correct file is found return its path else None
    """
    download_path = os.path.join(download_dir, link.filename)

    if not os.path.exists(download_path):
        return None

    # If already downloaded, does its hash match?
    logger.info("File was already downloaded %s", download_path)
    if hashes:
        try:
            hashes.check_against_path(download_path)
        except HashMismatch:
            if warn_on_hash_mismatch:
                logger.warning(
                    "Previously-downloaded file %s has bad hash. Re-downloading.",
                    download_path,
                )
            os.unlink(download_path)
            return None
    return download_path


class RequirementPreparer:
    """Prepares a Requirement"""

    def __init__(
        self,
        build_dir: str,
        download_dir: Optional[str],
        src_dir: str,
        build_isolation: bool,
        check_build_deps: bool,
        build_tracker: BuildTracker,
        session: PipSession,
        progress_bar: str,
        finder: PackageFinder,
        require_hashes: bool,
        use_user_site: bool,
        lazy_wheel: bool,
        verbosity: int,
        legacy_resolver: bool,
    ) -> None:
        super().__init__()

        self.src_dir = src_dir
        self.build_dir = build_dir
        self.build_tracker = build_tracker
        self._session = session
        self._download = Downloader(session, progress_bar)
        self._batch_download = BatchDownloader(session, progress_bar)
        self.finder = finder

        # Where still-packed archives should be written to. If None, they are
        # not saved, and are deleted immediately after unpacking.
        self.download_dir = download_dir

        # Is build isolation allowed?
        self.build_isolation = build_isolation

        # Should check build dependencies?
        self.check_build_deps = check_build_deps

        # Should hash-checking be required?
        self.require_hashes = require_hashes

        # Should install in user site-packages?
        self.use_user_site = use_user_site

        # Should wheels be downloaded lazily?
        self.use_lazy_wheel = lazy_wheel

        # How verbose should underlying tooling be?
        self.verbosity = verbosity

        # Are we using the legacy resolver?
        self.legacy_resolver = legacy_resolver

        # Memoized downloaded files, as mapping of url: path.
        self._downloaded: Dict[str, str] = {}

        # Previous "header" printed for a link-based InstallRequirement
        self._previous_requirement_header = ("", "")

    def _log_preparing_link(self, req: InstallRequirement) -> None:
        """Provide context for the requirement being prepared."""
        if req.link.is_file and not req.is_wheel_from_cache:
            message = "Processing %s"
            information = str(display_path(req.link.file_path))
        else:
            message = "Collecting %s"
            information = redact_auth_from_requirement(req.req) if req.req else str(req)

        # If we used req.req, inject requirement source if available (this
        # would already be included if we used req directly)
        if req.req and req.comes_from:
            if isinstance(req.comes_from, str):
                comes_from: Optional[str] = req.comes_from
            else:
                comes_from = req.comes_from.from_path()
            if comes_from:
                information += f" (from {comes_from})"

        if (message, information) != self._previous_requirement_header:
            self._previous_requirement_header = (message, information)
            logger.info(message, information)

        if req.is_wheel_from_cache:
            with indent_log():
                logger.info("Using cached %s", req.link.filename)

    def _ensure_link_req_src_dir(
        self, req: InstallRequirement, parallel_builds: bool
    ) -> None:
        """Ensure source_dir of a linked InstallRequirement."""
        # Since source_dir is only set for editable requirements.
        if req.link.is_wheel:
            # We don't need to unpack wheels, so no need for a source
            # directory.
            return
        assert req.source_dir is None
        if req.link.is_existing_dir():
            # build local directories in-tree
            req.source_dir = req.link.file_path
            return

        # We always delete unpacked sdists after pip runs.
        req.ensure_has_source_dir(
            self.build_dir,
            autodelete=True,
            parallel_builds=parallel_builds,
        )
        req.ensure_pristine_source_checkout()

    def _get_linked_req_hashes(self, req: InstallRequirement) -> Hashes:
        # By the time this is called, the requirement's link should have
        # been checked so we can tell what kind of requirements req is
        # and raise some more informative errors than otherwise.
        # (For example, we can raise VcsHashUnsupported for a VCS URL
        # rather than HashMissing.)
        if not self.require_hashes:
            return req.hashes(trust_internet=True)

        # We could check these first 2 conditions inside unpack_url
        # and save repetition of conditions, but then we would
        # report less-useful error messages for unhashable
        # requirements, complaining that there's no hash provided.
        if req.link.is_vcs:
            raise VcsHashUnsupported()
        if req.link.is_existing_dir():
            raise DirectoryUrlHashUnsupported()

        # Unpinned packages are asking for trouble when a new version
        # is uploaded.  This isn't a security check, but it saves users
        # a surprising hash mismatch in the future.
        # file:/// URLs aren't pinnable, so don't complain about them
        # not being pinned.
        if not req.is_direct and not req.is_pinned:
            raise HashUnpinned()

        # If known-good hashes are missing for this requirement,
        # shim it with a facade object that will provoke hash
        # computation and then raise a HashMissing exception
        # showing the user what the hash should be.
        return req.hashes(trust_internet=False) or MissingHashes()

    def _fetch_metadata_only(
        self,
        req: InstallRequirement,
    ) -> Optional[BaseDistribution]:
        if self.legacy_resolver:
            logger.debug(
                "Metadata-only fetching is not used in the legacy resolver",
            )
            return None
        if self.require_hashes:
            logger.debug(
                "Metadata-only fetching is not used as hash checking is required",
            )
            return None
        # Try PEP 658 metadata first, then fall back to lazy wheel if unavailable.
        return self._fetch_metadata_using_link_data_attr(
            req
        ) or self._fetch_metadata_using_lazy_wheel(req.link)

    def _fetch_metadata_using_link_data_attr(
        self,
        req: InstallRequirement,
    ) -> Optional[BaseDistribution]:
        """Fetch metadata from the data-dist-info-metadata attribute, if possible."""
        # (1) Get the link to the metadata file, if provided by the backend.
        metadata_link = req.link.metadata_link()
        if metadata_link is None:
            return None
        assert req.req is not None
        logger.verbose(
            "Obtaining dependency information for %s from %s",
            req.req,
            metadata_link,
        )
        # (2) Download the contents of the METADATA file, separate from the dist itself.
        metadata_file = get_http_url(
            metadata_link,
            self._download,
            hashes=metadata_link.as_hashes(),
        )
        with open(metadata_file.path, "rb") as f:
            metadata_contents = f.read()
        # (3) Generate a dist just from those file contents.
        metadata_dist = get_metadata_distribution(
            metadata_contents,
            req.link.filename,
            req.req.name,
        )
        # (4) Ensure the Name: field from the METADATA file matches the name from the
        #     install requirement.
        #
        #     NB: raw_name will fall back to the name from the install requirement if
        #     the Name: field is not present, but it's noted in the raw_name docstring
        #     that that should NEVER happen anyway.
        if canonicalize_name(metadata_dist.raw_name) != canonicalize_name(req.req.name):
            raise MetadataInconsistent(
                req, "Name", req.req.name, metadata_dist.raw_name
            )
        return metadata_dist

    def _fetch_metadata_using_lazy_wheel(
        self,
        link: Link,
    ) -> Optional[BaseDistribution]:
        """Fetch metadata using lazy wheel, if possible."""
        # --use-feature=fast-deps must be provided.
        if not self.use_lazy_wheel:
            return None
        if link.is_file or not link.is_wheel:
            logger.debug(
                "Lazy wheel is not used as %r does not point to a remote wheel",
                link,
            )
            return None

        wheel = Wheel(link.filename)
        name = canonicalize_name(wheel.name)
        logger.info(
            "Obtaining dependency information from %s %s",
            name,
            wheel.version,
        )
        url = link.url.split("#", 1)[0]
        try:
            return dist_from_wheel_url(name, url, self._session)
        except HTTPRangeRequestUnsupported:
            logger.debug("%s does not support range requests", url)
            return None

    def _complete_partial_requirements(
        self,
        partially_downloaded_reqs: Iterable[InstallRequirement],
        parallel_builds: bool = False,
    ) -> None:
        """Download any requirements which were only fetched by metadata."""
        # Download to a temporary directory. These will be copied over as
        # needed for downstream 'download', 'wheel', and 'install' commands.
        temp_dir = TempDirectory(kind="unpack", globally_managed=True).path

        # Map each link to the requirement that owns it. This allows us to set
        # `req.local_file_path` on the appropriate requirement after passing
        # all the links at once into BatchDownloader.
        links_to_fully_download: Dict[Link, InstallRequirement] = {}
        for req in partially_downloaded_reqs:
            assert req.link
            links_to_fully_download[req.link] = req

        batch_download = self._batch_download(
            links_to_fully_download.keys(),
            temp_dir,
        )
        for link, (filepath, _) in batch_download:
            logger.debug("Downloading link %s to %s", link, filepath)
            req = links_to_fully_download[link]
            # Record the downloaded file path so wheel reqs can extract a Distribution
            # in .get_dist().
            req.local_file_path = filepath
            # Record that the file is downloaded so we don't do it again in
            # _prepare_linked_requirement().
            self._downloaded[req.link.url] = filepath

            # If this is an sdist, we need to unpack it after downloading, but the
            # .source_dir won't be set up until we are in _prepare_linked_requirement().
            # Add the downloaded archive to the install requirement to unpack after
            # preparing the source dir.
            if not req.is_wheel:
                req.needs_unpacked_archive(Path(filepath))

        # This step is necessary to ensure all lazy wheels are processed
        # successfully by the 'download', 'wheel', and 'install' commands.
        for req in partially_downloaded_reqs:
            self._prepare_linked_requirement(req, parallel_builds)

    def prepare_linked_requirement(
        self, req: InstallRequirement, parallel_builds: bool = False
    ) -> BaseDistribution:
        """Prepare a requirement to be obtained from req.link."""
        assert req.link
        self._log_preparing_link(req)
        with indent_log():
            # Check if the relevant file is already available
            # in the download directory
            file_path = None
            if self.download_dir is not None and req.link.is_wheel:
                hashes = self._get_linked_req_hashes(req)
                file_path = _check_download_dir(
                    req.link,
                    self.download_dir,
                    hashes,
                    # When a locally built wheel has been found in cache, we don't warn
                    # about re-downloading when the already downloaded wheel hash does
                    # not match. This is because the hash must be checked against the
                    # original link, not the cached link. It that case the already
                    # downloaded file will be removed and re-fetched from cache (which
                    # implies a hash check against the cache entry's origin.json).
                    warn_on_hash_mismatch=not req.is_wheel_from_cache,
                )

            if file_path is not None:
                # The file is already available, so mark it as downloaded
                self._downloaded[req.link.url] = file_path
            else:
                # The file is not available, attempt to fetch only metadata
                metadata_dist = self._fetch_metadata_only(req)
                if metadata_dist is not None:
                    req.needs_more_preparation = True
                    return metadata_dist

            # None of the optimizations worked, fully prepare the requirement
            return self._prepare_linked_requirement(req, parallel_builds)

    def prepare_linked_requirements_more(
        self, reqs: Iterable[InstallRequirement], parallel_builds: bool = False
    ) -> None:
        """Prepare linked requirements more, if needed."""
        reqs = [req for req in reqs if req.needs_more_preparation]
        for req in reqs:
            # Determine if any of these requirements were already downloaded.
            if self.download_dir is not None and req.link.is_wheel:
                hashes = self._get_linked_req_hashes(req)
                file_path = _check_download_dir(req.link, self.download_dir, hashes)
                if file_path is not None:
                    self._downloaded[req.link.url] = file_path
                    req.needs_more_preparation = False

        # Prepare requirements we found were already downloaded for some
        # reason. The other downloads will be completed separately.
        partially_downloaded_reqs: List[InstallRequirement] = []
        for req in reqs:
            if req.needs_more_preparation:
                partially_downloaded_reqs.append(req)
            else:
                self._prepare_linked_requirement(req, parallel_builds)

        # TODO: separate this part out from RequirementPreparer when the v1
        # resolver can be removed!
        self._complete_partial_requirements(
            partially_downloaded_reqs,
            parallel_builds=parallel_builds,
        )

    def _prepare_linked_requirement(
        self, req: InstallRequirement, parallel_builds: bool
    ) -> BaseDistribution:
        assert req.link
        link = req.link

        hashes = self._get_linked_req_hashes(req)

        if hashes and req.is_wheel_from_cache:
            assert req.download_info is not None
            assert link.is_wheel
            assert link.is_file
            # We need to verify hashes, and we have found the requirement in the cache
            # of locally built wheels.
            if (
                isinstance(req.download_info.info, ArchiveInfo)
                and req.download_info.info.hashes
                and hashes.has_one_of(req.download_info.info.hashes)
            ):
                # At this point we know the requirement was built from a hashable source
                # artifact, and we verified that the cache entry's hash of the original
                # artifact matches one of the hashes we expect. We don't verify hashes
                # against the cached wheel, because the wheel is not the original.
                hashes = None
            else:
                logger.warning(
                    "The hashes of the source archive found in cache entry "
                    "don't match, ignoring cached built wheel "
                    "and re-downloading source."
                )
                req.link = req.cached_wheel_source_link
                link = req.link

        self._ensure_link_req_src_dir(req, parallel_builds)

        if link.is_existing_dir():
            local_file = None
        elif link.url not in self._downloaded:
            try:
                local_file = unpack_url(
                    link,
                    req.source_dir,
                    self._download,
                    self.verbosity,
                    self.download_dir,
                    hashes,
                )
            except NetworkConnectionError as exc:
                raise InstallationError(
                    f"Could not install requirement {req} because of HTTP "
                    f"error {exc} for URL {link}"
                )
        else:
            file_path = self._downloaded[link.url]
            if hashes:
                hashes.check_against_path(file_path)
            local_file = File(file_path, content_type=None)

        # If download_info is set, we got it from the wheel cache.
        if req.download_info is None:
            # Editables don't go through this function (see
            # prepare_editable_requirement).
            assert not req.editable
            req.download_info = direct_url_from_link(link, req.source_dir)
            # Make sure we have a hash in download_info. If we got it as part of the
            # URL, it will have been verified and we can rely on it. Otherwise we
            # compute it from the downloaded file.
            # FIXME: https://github.com/pypa/pip/issues/11943
            if (
                isinstance(req.download_info.info, ArchiveInfo)
                and not req.download_info.info.hashes
                and local_file
            ):
                hash = hash_file(local_file.path)[0].hexdigest()
                # We populate info.hash for backward compatibility.
                # This will automatically populate info.hashes.
                req.download_info.info.hash = f"sha256={hash}"

        # For use in later processing,
        # preserve the file path on the requirement.
        if local_file:
            req.local_file_path = local_file.path

        dist = _get_prepared_distribution(
            req,
            self.build_tracker,
            self.finder,
            self.build_isolation,
            self.check_build_deps,
        )
        return dist

    def save_linked_requirement(self, req: InstallRequirement) -> None:
        assert self.download_dir is not None
        assert req.link is not None
        link = req.link
        if link.is_vcs or (link.is_existing_dir() and req.editable):
            # Make a .zip of the source_dir we already created.
            req.archive(self.download_dir)
            return

        if link.is_existing_dir():
            logger.debug(
                "Not copying link to destination directory "
                "since it is a directory: %s",
                link,
            )
            return
        if req.local_file_path is None:
            # No distribution was downloaded for this requirement.
            return

        download_location = os.path.join(self.download_dir, link.filename)
        if not os.path.exists(download_location):
            shutil.copy(req.local_file_path, download_location)
            download_path = display_path(download_location)
            logger.info("Saved %s", download_path)

    def prepare_editable_requirement(
        self,
        req: InstallRequirement,
    ) -> BaseDistribution:
        """Prepare an editable requirement."""
        assert req.editable, "cannot prepare a non-editable req as editable"

        logger.info("Obtaining %s", req)

        with indent_log():
            if self.require_hashes:
                raise InstallationError(
                    f"The editable requirement {req} cannot be installed when "
                    "requiring hashes, because there is no single file to "
                    "hash."
                )
            req.ensure_has_source_dir(self.src_dir)
            req.update_editable()
            assert req.source_dir
            req.download_info = direct_url_for_editable(req.unpacked_source_directory)

            dist = _get_prepared_distribution(
                req,
                self.build_tracker,
                self.finder,
                self.build_isolation,
                self.check_build_deps,
            )

            req.check_if_exists(self.use_user_site)

        return dist

    def prepare_installed_requirement(
        self,
        req: InstallRequirement,
        skip_reason: str,
    ) -> BaseDistribution:
        """Prepare an already-installed requirement."""
        assert req.satisfied_by, "req should have been satisfied but isn't"
        assert skip_reason is not None, (
            "did not get skip reason skipped but req.satisfied_by "
            f"is set to {req.satisfied_by}"
        )
        logger.info(
            "Requirement %s: %s (%s)", skip_reason, req, req.satisfied_by.version
        )
        with indent_log():
            if self.require_hashes:
                logger.debug(
                    "Since it is already installed, we are trusting this "
                    "package without checking its hash. To ensure a "
                    "completely repeatable environment, install into an "
                    "empty virtualenv."
                )
            return InstalledDistribution(req).get_metadata_distribution()

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\bidi\browsing_context.py ===
# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from typing import Dict, List, Optional, Union

from selenium.webdriver.common.bidi.common import command_builder

from .session import Session


class ReadinessState:
    """Represents the stage of document loading at which a navigation command will return."""

    NONE = "none"
    INTERACTIVE = "interactive"
    COMPLETE = "complete"


class UserPromptType:
    """Represents the possible user prompt types."""

    ALERT = "alert"
    BEFORE_UNLOAD = "beforeunload"
    CONFIRM = "confirm"
    PROMPT = "prompt"


class NavigationInfo:
    """Provides details of an ongoing navigation."""

    def __init__(
        self,
        context: str,
        navigation: Optional[str],
        timestamp: int,
        url: str,
    ):
        self.context = context
        self.navigation = navigation
        self.timestamp = timestamp
        self.url = url

    @classmethod
    def from_json(cls, json: Dict) -> "NavigationInfo":
        """Creates a NavigationInfo instance from a dictionary.

        Parameters:
        -----------
            json: A dictionary containing the navigation information.

        Returns:
        -------
            NavigationInfo: A new instance of NavigationInfo.
        """
        return cls(
            context=json.get("context"),
            navigation=json.get("navigation"),
            timestamp=json.get("timestamp"),
            url=json.get("url"),
        )


class BrowsingContextInfo:
    """Represents the properties of a navigable."""

    def __init__(
        self,
        context: str,
        url: str,
        children: Optional[List["BrowsingContextInfo"]],
        parent: Optional[str] = None,
        user_context: Optional[str] = None,
        original_opener: Optional[str] = None,
        client_window: Optional[str] = None,
    ):
        self.context = context
        self.url = url
        self.children = children
        self.parent = parent
        self.user_context = user_context
        self.original_opener = original_opener
        self.client_window = client_window

    @classmethod
    def from_json(cls, json: Dict) -> "BrowsingContextInfo":
        """Creates a BrowsingContextInfo instance from a dictionary.

        Parameters:
        -----------
            json: A dictionary containing the browsing context information.

        Returns:
        -------
            BrowsingContextInfo: A new instance of BrowsingContextInfo.
        """
        children = None
        if json.get("children") is not None:
            children = [BrowsingContextInfo.from_json(child) for child in json.get("children")]

        return cls(
            context=json.get("context"),
            url=json.get("url"),
            children=children,
            parent=json.get("parent"),
            user_context=json.get("userContext"),
            original_opener=json.get("originalOpener"),
            client_window=json.get("clientWindow"),
        )


class DownloadWillBeginParams(NavigationInfo):
    """Parameters for the downloadWillBegin event."""

    def __init__(
        self,
        context: str,
        navigation: Optional[str],
        timestamp: int,
        url: str,
        suggested_filename: str,
    ):
        super().__init__(context, navigation, timestamp, url)
        self.suggested_filename = suggested_filename

    @classmethod
    def from_json(cls, json: Dict) -> "DownloadWillBeginParams":
        """Creates a DownloadWillBeginParams instance from a dictionary.

        Parameters:
        -----------
            json: A dictionary containing the download parameters.

        Returns:
        -------
            DownloadWillBeginParams: A new instance of DownloadWillBeginParams.
        """
        return cls(
            context=json.get("context"),
            navigation=json.get("navigation"),
            timestamp=json.get("timestamp"),
            url=json.get("url"),
            suggested_filename=json.get("suggestedFilename"),
        )


class UserPromptOpenedParams:
    """Parameters for the userPromptOpened event."""

    def __init__(
        self,
        context: str,
        handler: str,
        message: str,
        type: str,
        default_value: Optional[str] = None,
    ):
        self.context = context
        self.handler = handler
        self.message = message
        self.type = type
        self.default_value = default_value

    @classmethod
    def from_json(cls, json: Dict) -> "UserPromptOpenedParams":
        """Creates a UserPromptOpenedParams instance from a dictionary.

        Parameters:
        -----------
            json: A dictionary containing the user prompt parameters.

        Returns:
        -------
            UserPromptOpenedParams: A new instance of UserPromptOpenedParams.
        """
        return cls(
            context=json.get("context"),
            handler=json.get("handler"),
            message=json.get("message"),
            type=json.get("type"),
            default_value=json.get("defaultValue"),
        )


class UserPromptClosedParams:
    """Parameters for the userPromptClosed event."""

    def __init__(
        self,
        context: str,
        accepted: bool,
        type: str,
        user_text: Optional[str] = None,
    ):
        self.context = context
        self.accepted = accepted
        self.type = type
        self.user_text = user_text

    @classmethod
    def from_json(cls, json: Dict) -> "UserPromptClosedParams":
        """Creates a UserPromptClosedParams instance from a dictionary.

        Parameters:
        -----------
            json: A dictionary containing the user prompt closed parameters.

        Returns:
        -------
            UserPromptClosedParams: A new instance of UserPromptClosedParams.
        """
        return cls(
            context=json.get("context"),
            accepted=json.get("accepted"),
            type=json.get("type"),
            user_text=json.get("userText"),
        )


class HistoryUpdatedParams:
    """Parameters for the historyUpdated event."""

    def __init__(
        self,
        context: str,
        url: str,
    ):
        self.context = context
        self.url = url

    @classmethod
    def from_json(cls, json: Dict) -> "HistoryUpdatedParams":
        """Creates a HistoryUpdatedParams instance from a dictionary.

        Parameters:
        -----------
            json: A dictionary containing the history updated parameters.

        Returns:
        -------
            HistoryUpdatedParams: A new instance of HistoryUpdatedParams.
        """
        return cls(
            context=json.get("context"),
            url=json.get("url"),
        )


class BrowsingContextEvent:
    """Base class for browsing context events."""

    def __init__(self, event_class: str, **kwargs):
        self.event_class = event_class
        self.params = kwargs

    @classmethod
    def from_json(cls, json: Dict) -> "BrowsingContextEvent":
        """Creates a BrowsingContextEvent instance from a dictionary.

        Parameters:
        -----------
            json: A dictionary containing the event information.

        Returns:
        -------
            BrowsingContextEvent: A new instance of BrowsingContextEvent.
        """
        return cls(event_class=json.get("event_class"), **json)


class BrowsingContext:
    """BiDi implementation of the browsingContext module."""

    EVENTS = {
        "context_created": "browsingContext.contextCreated",
        "context_destroyed": "browsingContext.contextDestroyed",
        "dom_content_loaded": "browsingContext.domContentLoaded",
        "download_will_begin": "browsingContext.downloadWillBegin",
        "fragment_navigated": "browsingContext.fragmentNavigated",
        "history_updated": "browsingContext.historyUpdated",
        "load": "browsingContext.load",
        "navigation_aborted": "browsingContext.navigationAborted",
        "navigation_committed": "browsingContext.navigationCommitted",
        "navigation_failed": "browsingContext.navigationFailed",
        "navigation_started": "browsingContext.navigationStarted",
        "user_prompt_closed": "browsingContext.userPromptClosed",
        "user_prompt_opened": "browsingContext.userPromptOpened",
    }

    def __init__(self, conn):
        self.conn = conn
        self.subscriptions = {}
        self.callbacks = {}

    def activate(self, context: str) -> None:
        """Activates and focuses the given top-level traversable.

        Parameters:
        -----------
            context: The browsing context ID to activate.

        Raises:
        ------
            Exception: If the browsing context is not a top-level traversable.
        """
        params = {"context": context}
        self.conn.execute(command_builder("browsingContext.activate", params))

    def capture_screenshot(
        self,
        context: str,
        origin: str = "viewport",
        format: Optional[Dict] = None,
        clip: Optional[Dict] = None,
    ) -> str:
        """Captures an image of the given navigable, and returns it as a Base64-encoded string.

        Parameters:
        -----------
            context: The browsing context ID to capture.
            origin: The origin of the screenshot, either "viewport" or "document".
            format: The format of the screenshot.
            clip: The clip rectangle of the screenshot.

        Returns:
        -------
            str: The Base64-encoded screenshot.
        """
        params = {"context": context, "origin": origin}
        if format is not None:
            params["format"] = format
        if clip is not None:
            params["clip"] = clip

        result = self.conn.execute(command_builder("browsingContext.captureScreenshot", params))
        return result["data"]

    def close(self, context: str, prompt_unload: bool = False) -> None:
        """Closes a top-level traversable.

        Parameters:
        -----------
            context: The browsing context ID to close.
            prompt_unload: Whether to prompt to unload.

        Raises:
        ------
            Exception: If the browsing context is not a top-level traversable.
        """
        params = {"context": context, "promptUnload": prompt_unload}
        self.conn.execute(command_builder("browsingContext.close", params))

    def create(
        self,
        type: str,
        reference_context: Optional[str] = None,
        background: bool = False,
        user_context: Optional[str] = None,
    ) -> str:
        """Creates a new navigable, either in a new tab or in a new window, and returns its navigable id.

        Parameters:
        -----------
            type: The type of the new navigable, either "tab" or "window".
            reference_context: The reference browsing context ID.
            background: Whether to create the new navigable in the background.
            user_context: The user context ID.

        Returns:
        -------
            str: The browsing context ID of the created navigable.
        """
        params = {"type": type}
        if reference_context is not None:
            params["referenceContext"] = reference_context
        if background is not None:
            params["background"] = background
        if user_context is not None:
            params["userContext"] = user_context

        result = self.conn.execute(command_builder("browsingContext.create", params))
        return result["context"]

    def get_tree(
        self,
        max_depth: Optional[int] = None,
        root: Optional[str] = None,
    ) -> List[BrowsingContextInfo]:
        """Returns a tree of all descendent navigables including the given parent itself, or all top-level contexts
        when no parent is provided.

        Parameters:
        -----------
            max_depth: The maximum depth of the tree.
            root: The root browsing context ID.

        Returns:
        -------
            List[BrowsingContextInfo]: A list of browsing context information.
        """
        params = {}
        if max_depth is not None:
            params["maxDepth"] = max_depth
        if root is not None:
            params["root"] = root

        result = self.conn.execute(command_builder("browsingContext.getTree", params))
        return [BrowsingContextInfo.from_json(context) for context in result["contexts"]]

    def handle_user_prompt(
        self,
        context: str,
        accept: Optional[bool] = None,
        user_text: Optional[str] = None,
    ) -> None:
        """Allows closing an open prompt.

        Parameters:
        -----------
            context: The browsing context ID.
            accept: Whether to accept the prompt.
            user_text: The text to enter in the prompt.
        """
        params = {"context": context}
        if accept is not None:
            params["accept"] = accept
        if user_text is not None:
            params["userText"] = user_text

        self.conn.execute(command_builder("browsingContext.handleUserPrompt", params))

    def locate_nodes(
        self,
        context: str,
        locator: Dict,
        max_node_count: Optional[int] = None,
        serialization_options: Optional[Dict] = None,
        start_nodes: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """Returns a list of all nodes matching the specified locator.

        Parameters:
        -----------
            context: The browsing context ID.
            locator: The locator to use.
            max_node_count: The maximum number of nodes to return.
            serialization_options: The serialization options.
            start_nodes: The start nodes.

        Returns:
        -------
            List[Dict]: A list of nodes.
        """
        params = {"context": context, "locator": locator}
        if max_node_count is not None:
            params["maxNodeCount"] = max_node_count
        if serialization_options is not None:
            params["serializationOptions"] = serialization_options
        if start_nodes is not None:
            params["startNodes"] = start_nodes

        result = self.conn.execute(command_builder("browsingContext.locateNodes", params))
        return result["nodes"]

    def navigate(
        self,
        context: str,
        url: str,
        wait: Optional[str] = None,
    ) -> Dict:
        """Navigates a navigable to the given URL.

        Parameters:
        -----------
            context: The browsing context ID.
            url: The URL to navigate to.
            wait: The readiness state to wait for.

        Returns:
        -------
            Dict: A dictionary containing the navigation result.
        """
        params = {"context": context, "url": url}
        if wait is not None:
            params["wait"] = wait

        result = self.conn.execute(command_builder("browsingContext.navigate", params))
        return result

    def print(
        self,
        context: str,
        background: bool = False,
        margin: Optional[Dict] = None,
        orientation: str = "portrait",
        page: Optional[Dict] = None,
        page_ranges: Optional[List[Union[int, str]]] = None,
        scale: float = 1.0,
        shrink_to_fit: bool = True,
    ) -> str:
        """Creates a paginated representation of a document, and returns it as a PDF document represented as a
        Base64-encoded string.

        Parameters:
        -----------
            context: The browsing context ID.
            background: Whether to include the background.
            margin: The margin parameters.
            orientation: The orientation, either "portrait" or "landscape".
            page: The page parameters.
            page_ranges: The page ranges.
            scale: The scale.
            shrink_to_fit: Whether to shrink to fit.

        Returns:
        -------
            str: The Base64-encoded PDF document.
        """
        params = {
            "context": context,
            "background": background,
            "orientation": orientation,
            "scale": scale,
            "shrinkToFit": shrink_to_fit,
        }
        if margin is not None:
            params["margin"] = margin
        if page is not None:
            params["page"] = page
        if page_ranges is not None:
            params["pageRanges"] = page_ranges

        result = self.conn.execute(command_builder("browsingContext.print", params))
        return result["data"]

    def reload(
        self,
        context: str,
        ignore_cache: Optional[bool] = None,
        wait: Optional[str] = None,
    ) -> Dict:
        """Reloads a navigable.

        Parameters:
        -----------
            context: The browsing context ID.
            ignore_cache: Whether to ignore the cache.
            wait: The readiness state to wait for.

        Returns:
        -------
            Dict: A dictionary containing the navigation result.
        """
        params = {"context": context}
        if ignore_cache is not None:
            params["ignoreCache"] = ignore_cache
        if wait is not None:
            params["wait"] = wait

        result = self.conn.execute(command_builder("browsingContext.reload", params))
        return result

    def set_viewport(
        self,
        context: Optional[str] = None,
        viewport: Optional[Dict] = None,
        device_pixel_ratio: Optional[float] = None,
        user_contexts: Optional[List[str]] = None,
    ) -> None:
        """Modifies specific viewport characteristics on the given top-level traversable.

        Parameters:
        -----------
            context: The browsing context ID.
            viewport: The viewport parameters.
            device_pixel_ratio: The device pixel ratio.
            user_contexts: The user context IDs.

        Raises:
        ------
            Exception: If the browsing context is not a top-level traversable.
        """
        params = {}
        if context is not None:
            params["context"] = context
        if viewport is not None:
            params["viewport"] = viewport
        if device_pixel_ratio is not None:
            params["devicePixelRatio"] = device_pixel_ratio
        if user_contexts is not None:
            params["userContexts"] = user_contexts

        self.conn.execute(command_builder("browsingContext.setViewport", params))

    def traverse_history(self, context: str, delta: int) -> Dict:
        """Traverses the history of a given navigable by a delta.

        Parameters:
        -----------
            context: The browsing context ID.
            delta: The delta to traverse by.

        Returns:
        -------
            Dict: A dictionary containing the traverse history result.
        """
        params = {"context": context, "delta": delta}
        result = self.conn.execute(command_builder("browsingContext.traverseHistory", params))
        return result

    def _on_event(self, event_name: str, callback: callable) -> int:
        """Set a callback function to subscribe to a browsing context event.

        Parameters:
        ----------
            event_name: The event to subscribe to.
            callback: The callback function to execute on event.

        Returns:
        -------
            int: callback id
        """
        event = BrowsingContextEvent(event_name)

        def _callback(event_data):
            if event_name == self.EVENTS["context_created"] or event_name == self.EVENTS["context_destroyed"]:
                info = BrowsingContextInfo.from_json(event_data.params)
                callback(info)
            elif event_name == self.EVENTS["download_will_begin"]:
                params = DownloadWillBeginParams.from_json(event_data.params)
                callback(params)
            elif event_name == self.EVENTS["user_prompt_opened"]:
                params = UserPromptOpenedParams.from_json(event_data.params)
                callback(params)
            elif event_name == self.EVENTS["user_prompt_closed"]:
                params = UserPromptClosedParams.from_json(event_data.params)
                callback(params)
            elif event_name == self.EVENTS["history_updated"]:
                params = HistoryUpdatedParams.from_json(event_data.params)
                callback(params)
            else:
                # For navigation events
                info = NavigationInfo.from_json(event_data.params)
                callback(info)

        callback_id = self.conn.add_callback(event, _callback)

        if event_name in self.callbacks:
            self.callbacks[event_name].append(callback_id)
        else:
            self.callbacks[event_name] = [callback_id]

        return callback_id

    def add_event_handler(self, event: str, callback: callable, contexts: Optional[List[str]] = None) -> int:
        """Add an event handler to the browsing context.

        Parameters:
        ----------
            event: The event to subscribe to.
            callback: The callback function to execute on event.
            contexts: The browsing context IDs to subscribe to.

        Returns:
        -------
            int: callback id
        """
        try:
            event_name = self.EVENTS[event]
        except KeyError:
            raise Exception(f"Event {event} not found")

        callback_id = self._on_event(event_name, callback)

        if event_name in self.subscriptions:
            self.subscriptions[event_name].append(callback_id)
        else:
            params = {"events": [event_name]}
            if contexts is not None:
                params["browsingContexts"] = contexts
            session = Session(self.conn)
            self.conn.execute(session.subscribe(**params))
            self.subscriptions[event_name] = [callback_id]

        return callback_id

    def remove_event_handler(self, event: str, callback_id: int) -> None:
        """Remove an event handler from the browsing context.

        Parameters:
        ----------
            event: The event to unsubscribe from.
            callback_id: The callback id to remove.
        """
        try:
            event_name = self.EVENTS[event]
        except KeyError:
            raise Exception(f"Event {event} not found")

        event = BrowsingContextEvent(event_name)

        self.conn.remove_callback(event, callback_id)
        self.subscriptions[event_name].remove(callback_id)
        if len(self.subscriptions[event_name]) == 0:
            params = {"events": [event_name]}
            session = Session(self.conn)
            self.conn.execute(session.unsubscribe(**params))
            del self.subscriptions[event_name]

    def clear_event_handlers(self) -> None:
        """Clear all event handlers from the browsing context."""
        for event_name in self.subscriptions:
            event = BrowsingContextEvent(event_name)
            for callback_id in self.subscriptions[event_name]:
                self.conn.remove_callback(event, callback_id)
            params = {"events": [event_name]}
            session = Session(self.conn)
            self.conn.execute(session.unsubscribe(**params))
        self.subscriptions = {}

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\browser.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Browser
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import page
from . import target


class BrowserContextID(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> BrowserContextID:
        return cls(json)

    def __repr__(self):
        return 'BrowserContextID({})'.format(super().__repr__())


class WindowID(int):
    def to_json(self) -> int:
        return self

    @classmethod
    def from_json(cls, json: int) -> WindowID:
        return cls(json)

    def __repr__(self):
        return 'WindowID({})'.format(super().__repr__())


class WindowState(enum.Enum):
    '''
    The state of the browser window.
    '''
    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class Bounds:
    '''
    Browser window bounds information
    '''
    #: The offset from the left edge of the screen to the window in pixels.
    left: typing.Optional[int] = None

    #: The offset from the top edge of the screen to the window in pixels.
    top: typing.Optional[int] = None

    #: The window width in pixels.
    width: typing.Optional[int] = None

    #: The window height in pixels.
    height: typing.Optional[int] = None

    #: The window state. Default to normal.
    window_state: typing.Optional[WindowState] = None

    def to_json(self):
        json = dict()
        if self.left is not None:
            json['left'] = self.left
        if self.top is not None:
            json['top'] = self.top
        if self.width is not None:
            json['width'] = self.width
        if self.height is not None:
            json['height'] = self.height
        if self.window_state is not None:
            json['windowState'] = self.window_state.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            left=int(json['left']) if 'left' in json else None,
            top=int(json['top']) if 'top' in json else None,
            width=int(json['width']) if 'width' in json else None,
            height=int(json['height']) if 'height' in json else None,
            window_state=WindowState.from_json(json['windowState']) if 'windowState' in json else None,
        )


class PermissionType(enum.Enum):
    AR = "ar"
    AUDIO_CAPTURE = "audioCapture"
    AUTOMATIC_FULLSCREEN = "automaticFullscreen"
    BACKGROUND_FETCH = "backgroundFetch"
    BACKGROUND_SYNC = "backgroundSync"
    CAMERA_PAN_TILT_ZOOM = "cameraPanTiltZoom"
    CAPTURED_SURFACE_CONTROL = "capturedSurfaceControl"
    CLIPBOARD_READ_WRITE = "clipboardReadWrite"
    CLIPBOARD_SANITIZED_WRITE = "clipboardSanitizedWrite"
    DISPLAY_CAPTURE = "displayCapture"
    DURABLE_STORAGE = "durableStorage"
    GEOLOCATION = "geolocation"
    HAND_TRACKING = "handTracking"
    IDLE_DETECTION = "idleDetection"
    KEYBOARD_LOCK = "keyboardLock"
    LOCAL_FONTS = "localFonts"
    MIDI = "midi"
    MIDI_SYSEX = "midiSysex"
    NFC = "nfc"
    NOTIFICATIONS = "notifications"
    PAYMENT_HANDLER = "paymentHandler"
    PERIODIC_BACKGROUND_SYNC = "periodicBackgroundSync"
    POINTER_LOCK = "pointerLock"
    PROTECTED_MEDIA_IDENTIFIER = "protectedMediaIdentifier"
    SENSORS = "sensors"
    SMART_CARD = "smartCard"
    SPEAKER_SELECTION = "speakerSelection"
    STORAGE_ACCESS = "storageAccess"
    TOP_LEVEL_STORAGE_ACCESS = "topLevelStorageAccess"
    VIDEO_CAPTURE = "videoCapture"
    VR = "vr"
    WAKE_LOCK_SCREEN = "wakeLockScreen"
    WAKE_LOCK_SYSTEM = "wakeLockSystem"
    WEB_APP_INSTALLATION = "webAppInstallation"
    WEB_PRINTING = "webPrinting"
    WINDOW_MANAGEMENT = "windowManagement"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class PermissionSetting(enum.Enum):
    GRANTED = "granted"
    DENIED = "denied"
    PROMPT = "prompt"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PermissionDescriptor:
    '''
    Definition of PermissionDescriptor defined in the Permissions API:
    https://w3c.github.io/permissions/#dom-permissiondescriptor.
    '''
    #: Name of permission.
    #: See https://cs.chromium.org/chromium/src/third_party/blink/renderer/modules/permissions/permission_descriptor.idl for valid permission names.
    name: str

    #: For "midi" permission, may also specify sysex control.
    sysex: typing.Optional[bool] = None

    #: For "push" permission, may specify userVisibleOnly.
    #: Note that userVisibleOnly = true is the only currently supported type.
    user_visible_only: typing.Optional[bool] = None

    #: For "clipboard" permission, may specify allowWithoutSanitization.
    allow_without_sanitization: typing.Optional[bool] = None

    #: For "fullscreen" permission, must specify allowWithoutGesture:true.
    allow_without_gesture: typing.Optional[bool] = None

    #: For "camera" permission, may specify panTiltZoom.
    pan_tilt_zoom: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['name'] = self.name
        if self.sysex is not None:
            json['sysex'] = self.sysex
        if self.user_visible_only is not None:
            json['userVisibleOnly'] = self.user_visible_only
        if self.allow_without_sanitization is not None:
            json['allowWithoutSanitization'] = self.allow_without_sanitization
        if self.allow_without_gesture is not None:
            json['allowWithoutGesture'] = self.allow_without_gesture
        if self.pan_tilt_zoom is not None:
            json['panTiltZoom'] = self.pan_tilt_zoom
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            sysex=bool(json['sysex']) if 'sysex' in json else None,
            user_visible_only=bool(json['userVisibleOnly']) if 'userVisibleOnly' in json else None,
            allow_without_sanitization=bool(json['allowWithoutSanitization']) if 'allowWithoutSanitization' in json else None,
            allow_without_gesture=bool(json['allowWithoutGesture']) if 'allowWithoutGesture' in json else None,
            pan_tilt_zoom=bool(json['panTiltZoom']) if 'panTiltZoom' in json else None,
        )


class BrowserCommandId(enum.Enum):
    '''
    Browser command ids used by executeBrowserCommand.
    '''
    OPEN_TAB_SEARCH = "openTabSearch"
    CLOSE_TAB_SEARCH = "closeTabSearch"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class Bucket:
    '''
    Chrome histogram bucket.
    '''
    #: Minimum value (inclusive).
    low: int

    #: Maximum value (exclusive).
    high: int

    #: Number of samples.
    count: int

    def to_json(self):
        json = dict()
        json['low'] = self.low
        json['high'] = self.high
        json['count'] = self.count
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            low=int(json['low']),
            high=int(json['high']),
            count=int(json['count']),
        )


@dataclass
class Histogram:
    '''
    Chrome histogram.
    '''
    #: Name.
    name: str

    #: Sum of sample values.
    sum_: int

    #: Total number of samples.
    count: int

    #: Buckets.
    buckets: typing.List[Bucket]

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['sum'] = self.sum_
        json['count'] = self.count
        json['buckets'] = [i.to_json() for i in self.buckets]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            sum_=int(json['sum']),
            count=int(json['count']),
            buckets=[Bucket.from_json(i) for i in json['buckets']],
        )


def set_permission(
        permission: PermissionDescriptor,
        setting: PermissionSetting,
        origin: typing.Optional[str] = None,
        browser_context_id: typing.Optional[BrowserContextID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set permission settings for given origin.

    **EXPERIMENTAL**

    :param permission: Descriptor of permission to override.
    :param setting: Setting of the permission.
    :param origin: *(Optional)* Origin the permission applies to, all origins if not specified.
    :param browser_context_id: *(Optional)* Context to override. When omitted, default browser context is used.
    '''
    params: T_JSON_DICT = dict()
    params['permission'] = permission.to_json()
    params['setting'] = setting.to_json()
    if origin is not None:
        params['origin'] = origin
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.setPermission',
        'params': params,
    }
    json = yield cmd_dict


def grant_permissions(
        permissions: typing.List[PermissionType],
        origin: typing.Optional[str] = None,
        browser_context_id: typing.Optional[BrowserContextID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Grant specific permissions to the given origin and reject all others.

    **EXPERIMENTAL**

    :param permissions:
    :param origin: *(Optional)* Origin the permission applies to, all origins if not specified.
    :param browser_context_id: *(Optional)* BrowserContext to override permissions. When omitted, default browser context is used.
    '''
    params: T_JSON_DICT = dict()
    params['permissions'] = [i.to_json() for i in permissions]
    if origin is not None:
        params['origin'] = origin
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.grantPermissions',
        'params': params,
    }
    json = yield cmd_dict


def reset_permissions(
        browser_context_id: typing.Optional[BrowserContextID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Reset all permission management for all origins.

    :param browser_context_id: *(Optional)* BrowserContext to reset permissions. When omitted, default browser context is used.
    '''
    params: T_JSON_DICT = dict()
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.resetPermissions',
        'params': params,
    }
    json = yield cmd_dict


def set_download_behavior(
        behavior: str,
        browser_context_id: typing.Optional[BrowserContextID] = None,
        download_path: typing.Optional[str] = None,
        events_enabled: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set the behavior when downloading a file.

    **EXPERIMENTAL**

    :param behavior: Whether to allow all or deny all download requests, or use default Chrome behavior if available (otherwise deny). ``allowAndName`` allows download and names files according to their download guids.
    :param browser_context_id: *(Optional)* BrowserContext to set download behavior. When omitted, default browser context is used.
    :param download_path: *(Optional)* The default path to save downloaded files to. This is required if behavior is set to 'allow' or 'allowAndName'.
    :param events_enabled: *(Optional)* Whether to emit download events (defaults to false).
    '''
    params: T_JSON_DICT = dict()
    params['behavior'] = behavior
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    if download_path is not None:
        params['downloadPath'] = download_path
    if events_enabled is not None:
        params['eventsEnabled'] = events_enabled
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.setDownloadBehavior',
        'params': params,
    }
    json = yield cmd_dict


def cancel_download(
        guid: str,
        browser_context_id: typing.Optional[BrowserContextID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Cancel a download if in progress

    **EXPERIMENTAL**

    :param guid: Global unique identifier of the download.
    :param browser_context_id: *(Optional)* BrowserContext to perform the action in. When omitted, default browser context is used.
    '''
    params: T_JSON_DICT = dict()
    params['guid'] = guid
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.cancelDownload',
        'params': params,
    }
    json = yield cmd_dict


def close() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Close browser gracefully.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.close',
    }
    json = yield cmd_dict


def crash() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Crashes browser on the main thread.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.crash',
    }
    json = yield cmd_dict


def crash_gpu_process() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Crashes GPU process.

    **EXPERIMENTAL**
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.crashGpuProcess',
    }
    json = yield cmd_dict


def get_version() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, str, str, str, str]]:
    '''
    Returns version information.

    :returns: A tuple with the following items:

        0. **protocolVersion** - Protocol version.
        1. **product** - Product name.
        2. **revision** - Product revision.
        3. **userAgent** - User-Agent.
        4. **jsVersion** - V8 version.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.getVersion',
    }
    json = yield cmd_dict
    return (
        str(json['protocolVersion']),
        str(json['product']),
        str(json['revision']),
        str(json['userAgent']),
        str(json['jsVersion'])
    )


def get_browser_command_line() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Returns the command line switches for the browser process if, and only if
    --enable-automation is on the commandline.

    **EXPERIMENTAL**

    :returns: Commandline parameters
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.getBrowserCommandLine',
    }
    json = yield cmd_dict
    return [str(i) for i in json['arguments']]


def get_histograms(
        query: typing.Optional[str] = None,
        delta: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[Histogram]]:
    '''
    Get Chrome histograms.

    **EXPERIMENTAL**

    :param query: *(Optional)* Requested substring in name. Only histograms which have query as a substring in their name are extracted. An empty or absent query returns all histograms.
    :param delta: *(Optional)* If true, retrieve delta since last delta call.
    :returns: Histograms.
    '''
    params: T_JSON_DICT = dict()
    if query is not None:
        params['query'] = query
    if delta is not None:
        params['delta'] = delta
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.getHistograms',
        'params': params,
    }
    json = yield cmd_dict
    return [Histogram.from_json(i) for i in json['histograms']]


def get_histogram(
        name: str,
        delta: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,Histogram]:
    '''
    Get a Chrome histogram by name.

    **EXPERIMENTAL**

    :param name: Requested histogram name.
    :param delta: *(Optional)* If true, retrieve delta since last delta call.
    :returns: Histogram.
    '''
    params: T_JSON_DICT = dict()
    params['name'] = name
    if delta is not None:
        params['delta'] = delta
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.getHistogram',
        'params': params,
    }
    json = yield cmd_dict
    return Histogram.from_json(json['histogram'])


def get_window_bounds(
        window_id: WindowID
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,Bounds]:
    '''
    Get position and size of the browser window.

    **EXPERIMENTAL**

    :param window_id: Browser window id.
    :returns: Bounds information of the window. When window state is 'minimized', the restored window position and size are returned.
    '''
    params: T_JSON_DICT = dict()
    params['windowId'] = window_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.getWindowBounds',
        'params': params,
    }
    json = yield cmd_dict
    return Bounds.from_json(json['bounds'])


def get_window_for_target(
        target_id: typing.Optional[target.TargetID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[WindowID, Bounds]]:
    '''
    Get the browser window that contains the devtools target.

    **EXPERIMENTAL**

    :param target_id: *(Optional)* Devtools agent host id. If called as a part of the session, associated targetId is used.
    :returns: A tuple with the following items:

        0. **windowId** - Browser window id.
        1. **bounds** - Bounds information of the window. When window state is 'minimized', the restored window position and size are returned.
    '''
    params: T_JSON_DICT = dict()
    if target_id is not None:
        params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.getWindowForTarget',
        'params': params,
    }
    json = yield cmd_dict
    return (
        WindowID.from_json(json['windowId']),
        Bounds.from_json(json['bounds'])
    )


def set_window_bounds(
        window_id: WindowID,
        bounds: Bounds
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set position and/or size of the browser window.

    **EXPERIMENTAL**

    :param window_id: Browser window id.
    :param bounds: New window bounds. The 'minimized', 'maximized' and 'fullscreen' states cannot be combined with 'left', 'top', 'width' or 'height'. Leaves unspecified fields unchanged.
    '''
    params: T_JSON_DICT = dict()
    params['windowId'] = window_id.to_json()
    params['bounds'] = bounds.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.setWindowBounds',
        'params': params,
    }
    json = yield cmd_dict


def set_dock_tile(
        badge_label: typing.Optional[str] = None,
        image: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set dock tile details, platform-specific.

    **EXPERIMENTAL**

    :param badge_label: *(Optional)*
    :param image: *(Optional)* Png encoded image.
    '''
    params: T_JSON_DICT = dict()
    if badge_label is not None:
        params['badgeLabel'] = badge_label
    if image is not None:
        params['image'] = image
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.setDockTile',
        'params': params,
    }
    json = yield cmd_dict


def execute_browser_command(
        command_id: BrowserCommandId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Invoke custom browser commands used by telemetry.

    **EXPERIMENTAL**

    :param command_id:
    '''
    params: T_JSON_DICT = dict()
    params['commandId'] = command_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.executeBrowserCommand',
        'params': params,
    }
    json = yield cmd_dict


def add_privacy_sandbox_enrollment_override(
        url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Allows a site to use privacy sandbox features that require enrollment
    without the site actually being enrolled. Only supported on page targets.

    :param url:
    '''
    params: T_JSON_DICT = dict()
    params['url'] = url
    cmd_dict: T_JSON_DICT = {
        'method': 'Browser.addPrivacySandboxEnrollmentOverride',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Browser.downloadWillBegin')
@dataclass
class DownloadWillBegin:
    '''
    **EXPERIMENTAL**

    Fired when page is about to start a download.
    '''
    #: Id of the frame that caused the download to begin.
    frame_id: page.FrameId
    #: Global unique identifier of the download.
    guid: str
    #: URL of the resource being downloaded.
    url: str
    #: Suggested file name of the resource (the actual name of the file saved on disk may differ).
    suggested_filename: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DownloadWillBegin:
        return cls(
            frame_id=page.FrameId.from_json(json['frameId']),
            guid=str(json['guid']),
            url=str(json['url']),
            suggested_filename=str(json['suggestedFilename'])
        )


@event_class('Browser.downloadProgress')
@dataclass
class DownloadProgress:
    '''
    **EXPERIMENTAL**

    Fired when download makes progress. Last call has ``done`` == true.
    '''
    #: Global unique identifier of the download.
    guid: str
    #: Total expected bytes to download.
    total_bytes: float
    #: Total bytes received.
    received_bytes: float
    #: Download status.
    state: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DownloadProgress:
        return cls(
            guid=str(json['guid']),
            total_bytes=float(json['totalBytes']),
            received_bytes=float(json['receivedBytes']),
            state=str(json['state'])
        )