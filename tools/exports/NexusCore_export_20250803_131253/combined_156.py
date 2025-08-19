
# === NexusCore/tools\exports\export_20250803_114325\combined_84.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\assistants\main.py ===
# What is this?
## Main file for assistants API logic
import asyncio
import contextvars
import os
from functools import partial
from typing import Any, Coroutine, Dict, Iterable, List, Literal, Optional, Union

import httpx
from openai import AsyncOpenAI, OpenAI
from openai.types.beta.assistant import Assistant
from openai.types.beta.assistant_deleted import AssistantDeleted

import litellm
from litellm.types.router import GenericLiteLLMParams
from litellm.utils import (
    exception_type,
    get_litellm_params,
    get_llm_provider,
    get_secret,
    supports_httpx_timeout,
)

from ..llms.azure.assistants import AzureAssistantsAPI
from ..llms.openai.openai import OpenAIAssistantsAPI
from ..types.llms.openai import *
from ..types.router import *
from .utils import get_optional_params_add_message

####### ENVIRONMENT VARIABLES ###################
openai_assistants_api = OpenAIAssistantsAPI()
azure_assistants_api = AzureAssistantsAPI()

### ASSISTANTS ###


async def aget_assistants(
    custom_llm_provider: Literal["openai", "azure"],
    client: Optional[AsyncOpenAI] = None,
    **kwargs,
) -> AsyncCursorPage[Assistant]:
    loop = asyncio.get_event_loop()
    ### PASS ARGS TO GET ASSISTANTS ###
    kwargs["aget_assistants"] = True
    try:
        # Use a partial function to pass your keyword arguments
        func = partial(get_assistants, custom_llm_provider, client, **kwargs)

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        _, custom_llm_provider, _, _ = get_llm_provider(  # type: ignore
            model="", custom_llm_provider=custom_llm_provider
        )  # type: ignore

        # Await normally
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response
        return response  # type: ignore
    except Exception as e:
        raise exception_type(
            model="",
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs={},
            extra_kwargs=kwargs,
        )


def get_assistants(
    custom_llm_provider: Literal["openai", "azure"],
    client: Optional[Any] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    api_version: Optional[str] = None,
    **kwargs,
) -> SyncCursorPage[Assistant]:
    aget_assistants: Optional[bool] = kwargs.pop("aget_assistants", None)
    if aget_assistants is not None and not isinstance(aget_assistants, bool):
        raise Exception(
            "Invalid value passed in for aget_assistants. Only bool or None allowed"
        )
    optional_params = GenericLiteLLMParams(
        api_key=api_key, api_base=api_base, api_version=api_version, **kwargs
    )
    litellm_params_dict = get_litellm_params(**kwargs)

    ### TIMEOUT LOGIC ###
    timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
    # set timeout for 10 minutes by default

    if (
        timeout is not None
        and isinstance(timeout, httpx.Timeout)
        and supports_httpx_timeout(custom_llm_provider) is False
    ):
        read_timeout = timeout.read or 600
        timeout = read_timeout  # default 10 min timeout
    elif timeout is not None and not isinstance(timeout, httpx.Timeout):
        timeout = float(timeout)  # type: ignore
    elif timeout is None:
        timeout = 600.0

    response: Optional[SyncCursorPage[Assistant]] = None
    if custom_llm_provider == "openai":
        api_base = (
            optional_params.api_base  # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            or litellm.api_base
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        )
        organization = (
            optional_params.organization
            or litellm.organization
            or os.getenv("OPENAI_ORGANIZATION", None)
            or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
        )
        # set API KEY
        api_key = (
            optional_params.api_key
            or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
            or litellm.openai_key
            or os.getenv("OPENAI_API_KEY")
        )

        response = openai_assistants_api.get_assistants(
            api_base=api_base,
            api_key=api_key,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            organization=organization,
            client=client,
            aget_assistants=aget_assistants,  # type: ignore
        )  # type: ignore
    elif custom_llm_provider == "azure":
        api_base = (
            optional_params.api_base or litellm.api_base or get_secret("AZURE_API_BASE")
        )  # type: ignore

        api_version = (
            optional_params.api_version
            or litellm.api_version
            or get_secret("AZURE_API_VERSION")
        )  # type: ignore

        api_key = (
            optional_params.api_key
            or litellm.api_key
            or litellm.azure_key
            or get_secret("AZURE_OPENAI_API_KEY")
            or get_secret("AZURE_API_KEY")
        )  # type: ignore

        extra_body = optional_params.get("extra_body", {})
        azure_ad_token: Optional[str] = None
        if extra_body is not None:
            azure_ad_token = extra_body.pop("azure_ad_token", None)
        else:
            azure_ad_token = get_secret("AZURE_AD_TOKEN")  # type: ignore

        response = azure_assistants_api.get_assistants(
            api_base=api_base,
            api_key=api_key,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            client=client,
            aget_assistants=aget_assistants,  # type: ignore
            litellm_params=litellm_params_dict,
        )
    else:
        raise litellm.exceptions.BadRequestError(
            message="LiteLLM doesn't support {} for 'get_assistants'. Only 'openai' is supported.".format(
                custom_llm_provider
            ),
            model="n/a",
            llm_provider=custom_llm_provider,
            response=httpx.Response(
                status_code=400,
                content="Unsupported provider",
                request=httpx.Request(method="create_thread", url="https://github.com/BerriAI/litellm"),  # type: ignore
            ),
        )

    if response is None:
        raise litellm.exceptions.BadRequestError(
            message="LiteLLM doesn't support {} for 'get_assistants'. Only 'openai' is supported.".format(
                custom_llm_provider
            ),
            model="n/a",
            llm_provider=custom_llm_provider,
            response=httpx.Response(
                status_code=400,
                content="Unsupported provider",
                request=httpx.Request(method="create_thread", url="https://github.com/BerriAI/litellm"),  # type: ignore
            ),
        )

    return response


async def acreate_assistants(
    custom_llm_provider: Literal["openai", "azure"],
    client: Optional[AsyncOpenAI] = None,
    **kwargs,
) -> Assistant:
    loop = asyncio.get_event_loop()
    ### PASS ARGS TO GET ASSISTANTS ###
    kwargs["async_create_assistants"] = True
    model = kwargs.pop("model", None)
    try:
        kwargs["client"] = client
        # Use a partial function to pass your keyword arguments
        func = partial(create_assistants, custom_llm_provider, model, **kwargs)

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        _, custom_llm_provider, _, _ = get_llm_provider(  # type: ignore
            model=model, custom_llm_provider=custom_llm_provider
        )  # type: ignore

        # Await normally
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response
        return response  # type: ignore
    except Exception as e:
        raise exception_type(
            model=model,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs={},
            extra_kwargs=kwargs,
        )


def create_assistants(
    custom_llm_provider: Literal["openai", "azure"],
    model: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    instructions: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_resources: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, str]] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    response_format: Optional[Union[str, Dict[str, str]]] = None,
    client: Optional[Any] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    api_version: Optional[str] = None,
    **kwargs,
) -> Union[Assistant, Coroutine[Any, Any, Assistant]]:
    async_create_assistants: Optional[bool] = kwargs.pop(
        "async_create_assistants", None
    )
    if async_create_assistants is not None and not isinstance(
        async_create_assistants, bool
    ):
        raise ValueError(
            "Invalid value passed in for async_create_assistants. Only bool or None allowed"
        )
    optional_params = GenericLiteLLMParams(
        api_key=api_key, api_base=api_base, api_version=api_version, **kwargs
    )
    litellm_params_dict = get_litellm_params(**kwargs)

    ### TIMEOUT LOGIC ###
    timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
    # set timeout for 10 minutes by default

    if (
        timeout is not None
        and isinstance(timeout, httpx.Timeout)
        and supports_httpx_timeout(custom_llm_provider) is False
    ):
        read_timeout = timeout.read or 600
        timeout = read_timeout  # default 10 min timeout
    elif timeout is not None and not isinstance(timeout, httpx.Timeout):
        timeout = float(timeout)  # type: ignore
    elif timeout is None:
        timeout = 600.0

    create_assistant_data = {
        "model": model,
        "name": name,
        "description": description,
        "instructions": instructions,
        "tools": tools,
        "tool_resources": tool_resources,
        "metadata": metadata,
        "temperature": temperature,
        "top_p": top_p,
        "response_format": response_format,
    }

    # only send params that are not None
    create_assistant_data = {
        k: v for k, v in create_assistant_data.items() if v is not None
    }

    response: Optional[Union[Coroutine[Any, Any, Assistant], Assistant]] = None
    if custom_llm_provider == "openai":
        api_base = (
            optional_params.api_base  # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            or litellm.api_base
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        )
        organization = (
            optional_params.organization
            or litellm.organization
            or os.getenv("OPENAI_ORGANIZATION", None)
            or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
        )
        # set API KEY
        api_key = (
            optional_params.api_key
            or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
            or litellm.openai_key
            or os.getenv("OPENAI_API_KEY")
        )

        response = openai_assistants_api.create_assistants(
            api_base=api_base,
            api_key=api_key,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            organization=organization,
            create_assistant_data=create_assistant_data,
            client=client,
            async_create_assistants=async_create_assistants,  # type: ignore
        )  # type: ignore
    elif custom_llm_provider == "azure":
        api_base = (
            optional_params.api_base or litellm.api_base or get_secret("AZURE_API_BASE")
        )  # type: ignore

        api_version = (
            optional_params.api_version
            or litellm.api_version
            or get_secret("AZURE_API_VERSION")
        )  # type: ignore

        api_key = (
            optional_params.api_key
            or litellm.api_key
            or litellm.azure_key
            or get_secret("AZURE_OPENAI_API_KEY")
            or get_secret("AZURE_API_KEY")
        )  # type: ignore

        extra_body = optional_params.get("extra_body", {})
        azure_ad_token: Optional[str] = None
        if extra_body is not None:
            azure_ad_token = extra_body.pop("azure_ad_token", None)
        else:
            azure_ad_token = get_secret("AZURE_AD_TOKEN")  # type: ignore

        if isinstance(client, OpenAI):
            client = None  # only pass client if it's AzureOpenAI

        response = azure_assistants_api.create_assistants(
            api_base=api_base,
            api_key=api_key,
            azure_ad_token=azure_ad_token,
            api_version=api_version,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            client=client,
            async_create_assistants=async_create_assistants,
            create_assistant_data=create_assistant_data,
            litellm_params=litellm_params_dict,
        )
    else:
        raise litellm.exceptions.BadRequestError(
            message="LiteLLM doesn't support {} for 'create_assistants'. Only 'openai' is supported.".format(
                custom_llm_provider
            ),
            model="n/a",
            llm_provider=custom_llm_provider,
            response=httpx.Response(
                status_code=400,
                content="Unsupported provider",
                request=httpx.Request(method="create_thread", url="https://github.com/BerriAI/litellm"),  # type: ignore
            ),
        )
    if response is None:
        raise litellm.exceptions.InternalServerError(
            message="No response returned from 'create_assistants'",
            model=model,
            llm_provider=custom_llm_provider,
        )
    return response


async def adelete_assistant(
    custom_llm_provider: Literal["openai", "azure"],
    client: Optional[AsyncOpenAI] = None,
    **kwargs,
) -> AssistantDeleted:
    loop = asyncio.get_event_loop()
    ### PASS ARGS TO GET ASSISTANTS ###
    kwargs["async_delete_assistants"] = True
    try:
        kwargs["client"] = client
        # Use a partial function to pass your keyword arguments
        func = partial(delete_assistant, custom_llm_provider, **kwargs)

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        _, custom_llm_provider, _, _ = get_llm_provider(  # type: ignore
            model="", custom_llm_provider=custom_llm_provider
        )  # type: ignore

        # Await normally
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response
        return response  # type: ignore
    except Exception as e:
        raise exception_type(
            model="",
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs={},
            extra_kwargs=kwargs,
        )


def delete_assistant(
    custom_llm_provider: Literal["openai", "azure"],
    assistant_id: str,
    client: Optional[Any] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    api_version: Optional[str] = None,
    **kwargs,
) -> Union[AssistantDeleted, Coroutine[Any, Any, AssistantDeleted]]:
    optional_params = GenericLiteLLMParams(
        api_key=api_key, api_base=api_base, api_version=api_version, **kwargs
    )

    litellm_params_dict = get_litellm_params(**kwargs)

    async_delete_assistants: Optional[bool] = kwargs.pop(
        "async_delete_assistants", None
    )
    if async_delete_assistants is not None and not isinstance(
        async_delete_assistants, bool
    ):
        raise ValueError(
            "Invalid value passed in for async_delete_assistants. Only bool or None allowed"
        )

    ### TIMEOUT LOGIC ###
    timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
    # set timeout for 10 minutes by default

    if (
        timeout is not None
        and isinstance(timeout, httpx.Timeout)
        and supports_httpx_timeout(custom_llm_provider) is False
    ):
        read_timeout = timeout.read or 600
        timeout = read_timeout  # default 10 min timeout
    elif timeout is not None and not isinstance(timeout, httpx.Timeout):
        timeout = float(timeout)  # type: ignore
    elif timeout is None:
        timeout = 600.0

    response: Optional[
        Union[AssistantDeleted, Coroutine[Any, Any, AssistantDeleted]]
    ] = None
    if custom_llm_provider == "openai":
        api_base = (
            optional_params.api_base
            or litellm.api_base
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        )
        organization = (
            optional_params.organization
            or litellm.organization
            or os.getenv("OPENAI_ORGANIZATION", None)
            or None
        )
        # set API KEY
        api_key = (
            optional_params.api_key
            or litellm.api_key
            or litellm.openai_key
            or os.getenv("OPENAI_API_KEY")
        )

        response = openai_assistants_api.delete_assistant(
            api_base=api_base,
            api_key=api_key,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            organization=organization,
            assistant_id=assistant_id,
            client=client,
            async_delete_assistants=async_delete_assistants,
        )
    elif custom_llm_provider == "azure":
        api_base = (
            optional_params.api_base or litellm.api_base or get_secret("AZURE_API_BASE")
        )  # type: ignore

        api_version = (
            optional_params.api_version
            or litellm.api_version
            or get_secret("AZURE_API_VERSION")
        )  # type: ignore

        api_key = (
            optional_params.api_key
            or litellm.api_key
            or litellm.azure_key
            or get_secret("AZURE_OPENAI_API_KEY")
            or get_secret("AZURE_API_KEY")
        )  # type: ignore

        extra_body = optional_params.get("extra_body", {})
        azure_ad_token: Optional[str] = None
        if extra_body is not None:
            azure_ad_token = extra_body.pop("azure_ad_token", None)
        else:
            azure_ad_token = get_secret("AZURE_AD_TOKEN")  # type: ignore

        if isinstance(client, OpenAI):
            client = None  # only pass client if it's AzureOpenAI

        response = azure_assistants_api.delete_assistant(
            assistant_id=assistant_id,
            api_base=api_base,
            api_key=api_key,
            azure_ad_token=azure_ad_token,
            api_version=api_version,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            client=client,
            async_delete_assistants=async_delete_assistants,
            litellm_params=litellm_params_dict,
        )
    else:
        raise litellm.exceptions.BadRequestError(
            message="LiteLLM doesn't support {} for 'delete_assistant'. Only 'openai' is supported.".format(
                custom_llm_provider
            ),
            model="n/a",
            llm_provider=custom_llm_provider,
            response=httpx.Response(
                status_code=400,
                content="Unsupported provider",
                request=httpx.Request(
                    method="delete_assistant", url="https://github.com/BerriAI/litellm"
                ),
            ),
        )
    if response is None:
        raise litellm.exceptions.InternalServerError(
            message="No response returned from 'delete_assistant'",
            model="n/a",
            llm_provider=custom_llm_provider,
        )
    return response


### THREADS ###


async def acreate_thread(
    custom_llm_provider: Literal["openai", "azure"], **kwargs
) -> Thread:
    loop = asyncio.get_event_loop()
    ### PASS ARGS TO GET ASSISTANTS ###
    kwargs["acreate_thread"] = True
    try:
        # Use a partial function to pass your keyword arguments
        func = partial(create_thread, custom_llm_provider, **kwargs)

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        _, custom_llm_provider, _, _ = get_llm_provider(  # type: ignore
            model="", custom_llm_provider=custom_llm_provider
        )  # type: ignore

        # Await normally
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response
        return response  # type: ignore
    except Exception as e:
        raise exception_type(
            model="",
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs={},
            extra_kwargs=kwargs,
        )


def create_thread(
    custom_llm_provider: Literal["openai", "azure"],
    messages: Optional[Iterable[OpenAICreateThreadParamsMessage]] = None,
    metadata: Optional[dict] = None,
    tool_resources: Optional[OpenAICreateThreadParamsToolResources] = None,
    client: Optional[OpenAI] = None,
    **kwargs,
) -> Thread:
    """
    - get the llm provider
    - if openai - route it there
    - pass through relevant params

    ```
    from litellm import create_thread

    create_thread(
        custom_llm_provider="openai",
        ### OPTIONAL ###
        messages =  {
            "role": "user",
            "content": "Hello, what is AI?"
            },
            {
            "role": "user",
            "content": "How does AI work? Explain it in simple terms."
        }]
    )
    ```
    """
    acreate_thread = kwargs.get("acreate_thread", None)
    optional_params = GenericLiteLLMParams(**kwargs)
    litellm_params_dict = get_litellm_params(**kwargs)

    ### TIMEOUT LOGIC ###
    timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
    # set timeout for 10 minutes by default

    if (
        timeout is not None
        and isinstance(timeout, httpx.Timeout)
        and supports_httpx_timeout(custom_llm_provider) is False
    ):
        read_timeout = timeout.read or 600
        timeout = read_timeout  # default 10 min timeout
    elif timeout is not None and not isinstance(timeout, httpx.Timeout):
        timeout = float(timeout)  # type: ignore
    elif timeout is None:
        timeout = 600.0

    api_base: Optional[str] = None
    api_key: Optional[str] = None

    response: Optional[Thread] = None
    if custom_llm_provider == "openai":
        api_base = (
            optional_params.api_base  # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            or litellm.api_base
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        )
        organization = (
            optional_params.organization
            or litellm.organization
            or os.getenv("OPENAI_ORGANIZATION", None)
            or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
        )
        # set API KEY
        api_key = (
            optional_params.api_key
            or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
            or litellm.openai_key
            or os.getenv("OPENAI_API_KEY")
        )
        response = openai_assistants_api.create_thread(
            messages=messages,
            metadata=metadata,
            api_base=api_base,
            api_key=api_key,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            organization=organization,
            client=client,
            acreate_thread=acreate_thread,
        )
    elif custom_llm_provider == "azure":
        api_base = (
            optional_params.api_base or litellm.api_base or get_secret("AZURE_API_BASE")
        )  # type: ignore

        api_key = (
            optional_params.api_key
            or litellm.api_key
            or litellm.azure_key
            or get_secret("AZURE_OPENAI_API_KEY")
            or get_secret("AZURE_API_KEY")
        )  # type: ignore

        api_version: Optional[str] = (
            optional_params.api_version
            or litellm.api_version
            or get_secret("AZURE_API_VERSION")
        )  # type: ignore

        extra_body = optional_params.get("extra_body", {})
        azure_ad_token: Optional[str] = None
        if extra_body is not None:
            azure_ad_token = extra_body.pop("azure_ad_token", None)
        else:
            azure_ad_token = get_secret("AZURE_AD_TOKEN")  # type: ignore

        if isinstance(client, OpenAI):
            client = None  # only pass client if it's AzureOpenAI

        response = azure_assistants_api.create_thread(
            messages=messages,
            metadata=metadata,
            api_base=api_base,
            api_key=api_key,
            azure_ad_token=azure_ad_token,
            api_version=api_version,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            client=client,
            acreate_thread=acreate_thread,
            litellm_params=litellm_params_dict,
        )
    else:
        raise litellm.exceptions.BadRequestError(
            message="LiteLLM doesn't support {} for 'create_thread'. Only 'openai' is supported.".format(
                custom_llm_provider
            ),
            model="n/a",
            llm_provider=custom_llm_provider,
            response=httpx.Response(
                status_code=400,
                content="Unsupported provider",
                request=httpx.Request(method="create_thread", url="https://github.com/BerriAI/litellm"),  # type: ignore
            ),
        )
    return response  # type: ignore


async def aget_thread(
    custom_llm_provider: Literal["openai", "azure"],
    thread_id: str,
    client: Optional[AsyncOpenAI] = None,
    **kwargs,
) -> Thread:
    loop = asyncio.get_event_loop()
    ### PASS ARGS TO GET ASSISTANTS ###
    kwargs["aget_thread"] = True
    try:
        # Use a partial function to pass your keyword arguments
        func = partial(get_thread, custom_llm_provider, thread_id, client, **kwargs)

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        _, custom_llm_provider, _, _ = get_llm_provider(  # type: ignore
            model="", custom_llm_provider=custom_llm_provider
        )  # type: ignore

        # Await normally
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response
        return response  # type: ignore
    except Exception as e:
        raise exception_type(
            model="",
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs={},
            extra_kwargs=kwargs,
        )


def get_thread(
    custom_llm_provider: Literal["openai", "azure"],
    thread_id: str,
    client=None,
    **kwargs,
) -> Thread:
    """Get the thread object, given a thread_id"""
    aget_thread = kwargs.pop("aget_thread", None)
    optional_params = GenericLiteLLMParams(**kwargs)
    litellm_params_dict = get_litellm_params(**kwargs)
    ### TIMEOUT LOGIC ###
    timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
    # set timeout for 10 minutes by default

    if (
        timeout is not None
        and isinstance(timeout, httpx.Timeout)
        and supports_httpx_timeout(custom_llm_provider) is False
    ):
        read_timeout = timeout.read or 600
        timeout = read_timeout  # default 10 min timeout
    elif timeout is not None and not isinstance(timeout, httpx.Timeout):
        timeout = float(timeout)  # type: ignore
    elif timeout is None:
        timeout = 600.0
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    response: Optional[Thread] = None
    if custom_llm_provider == "openai":
        api_base = (
            optional_params.api_base  # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            or litellm.api_base
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        )
        organization = (
            optional_params.organization
            or litellm.organization
            or os.getenv("OPENAI_ORGANIZATION", None)
            or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
        )
        # set API KEY
        api_key = (
            optional_params.api_key
            or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
            or litellm.openai_key
            or os.getenv("OPENAI_API_KEY")
        )

        response = openai_assistants_api.get_thread(
            thread_id=thread_id,
            api_base=api_base,
            api_key=api_key,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            organization=organization,
            client=client,
            aget_thread=aget_thread,
        )
    elif custom_llm_provider == "azure":
        api_base = (
            optional_params.api_base or litellm.api_base or get_secret("AZURE_API_BASE")
        )  # type: ignore

        api_version: Optional[str] = (
            optional_params.api_version
            or litellm.api_version
            or get_secret("AZURE_API_VERSION")
        )  # type: ignore

        api_key = (
            optional_params.api_key
            or litellm.api_key
            or litellm.azure_key
            or get_secret("AZURE_OPENAI_API_KEY")
            or get_secret("AZURE_API_KEY")
        )  # type: ignore

        extra_body = optional_params.get("extra_body", {})
        azure_ad_token: Optional[str] = None
        if extra_body is not None:
            azure_ad_token = extra_body.pop("azure_ad_token", None)
        else:
            azure_ad_token = get_secret("AZURE_AD_TOKEN")  # type: ignore

        if isinstance(client, OpenAI):
            client = None  # only pass client if it's AzureOpenAI

        response = azure_assistants_api.get_thread(
            thread_id=thread_id,
            api_base=api_base,
            api_key=api_key,
            azure_ad_token=azure_ad_token,
            api_version=api_version,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            client=client,
            aget_thread=aget_thread,
            litellm_params=litellm_params_dict,
        )
    else:
        raise litellm.exceptions.BadRequestError(
            message="LiteLLM doesn't support {} for 'get_thread'. Only 'openai' is supported.".format(
                custom_llm_provider
            ),
            model="n/a",
            llm_provider=custom_llm_provider,
            response=httpx.Response(
                status_code=400,
                content="Unsupported provider",
                request=httpx.Request(method="create_thread", url="https://github.com/BerriAI/litellm"),  # type: ignore
            ),
        )
    return response  # type: ignore


### MESSAGES ###


async def a_add_message(
    custom_llm_provider: Literal["openai", "azure"],
    thread_id: str,
    role: Literal["user", "assistant"],
    content: str,
    attachments: Optional[List[Attachment]] = None,
    metadata: Optional[dict] = None,
    client=None,
    **kwargs,
) -> OpenAIMessage:
    loop = asyncio.get_event_loop()
    ### PASS ARGS TO GET ASSISTANTS ###
    kwargs["a_add_message"] = True
    try:
        # Use a partial function to pass your keyword arguments
        func = partial(
            add_message,
            custom_llm_provider,
            thread_id,
            role,
            content,
            attachments,
            metadata,
            client,
            **kwargs,
        )

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        _, custom_llm_provider, _, _ = get_llm_provider(  # type: ignore
            model="", custom_llm_provider=custom_llm_provider
        )  # type: ignore

        # Await normally
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            # Call the synchronous function using run_in_executor
            response = init_response
        return response  # type: ignore
    except Exception as e:
        raise exception_type(
            model="",
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs={},
            extra_kwargs=kwargs,
        )


def add_message(
    custom_llm_provider: Literal["openai", "azure"],
    thread_id: str,
    role: Literal["user", "assistant"],
    content: str,
    attachments: Optional[List[Attachment]] = None,
    metadata: Optional[dict] = None,
    client=None,
    **kwargs,
) -> OpenAIMessage:
    ### COMMON OBJECTS ###
    a_add_message = kwargs.pop("a_add_message", None)
    _message_data = MessageData(
        role=role, content=content, attachments=attachments, metadata=metadata
    )
    litellm_params_dict = get_litellm_params(**kwargs)
    optional_params = GenericLiteLLMParams(**kwargs)

    message_data = get_optional_params_add_message(
        role=_message_data["role"],
        content=_message_data["content"],
        attachments=_message_data["attachments"],
        metadata=_message_data["metadata"],
        custom_llm_provider=custom_llm_provider,
    )

    ### TIMEOUT LOGIC ###
    timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
    # set timeout for 10 minutes by default

    if (
        timeout is not None
        and isinstance(timeout, httpx.Timeout)
        and supports_httpx_timeout(custom_llm_provider) is False
    ):
        read_timeout = timeout.read or 600
        timeout = read_timeout  # default 10 min timeout
    elif timeout is not None and not isinstance(timeout, httpx.Timeout):
        timeout = float(timeout)  # type: ignore
    elif timeout is None:
        timeout = 600.0
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    response: Optional[OpenAIMessage] = None
    if custom_llm_provider == "openai":
        api_base = (
            optional_params.api_base  # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            or litellm.api_base
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        )
        organization = (
            optional_params.organization
            or litellm.organization
            or os.getenv("OPENAI_ORGANIZATION", None)
            or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
        )
        # set API KEY
        api_key = (
            optional_params.api_key
            or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
            or litellm.openai_key
            or os.getenv("OPENAI_API_KEY")
        )
        response = openai_assistants_api.add_message(
            thread_id=thread_id,
            message_data=message_data,
            api_base=api_base,
            api_key=api_key,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            organization=organization,
            client=client,
            a_add_message=a_add_message,
        )
    elif custom_llm_provider == "azure":
        api_base = (
            optional_params.api_base or litellm.api_base or get_secret("AZURE_API_BASE")
        )  # type: ignore

        api_version: Optional[str] = (
            optional_params.api_version
            or litellm.api_version
            or get_secret("AZURE_API_VERSION")
        )  # type: ignore

        api_key = (
            optional_params.api_key
            or litellm.api_key
            or litellm.azure_key
            or get_secret("AZURE_OPENAI_API_KEY")
            or get_secret("AZURE_API_KEY")
        )  # type: ignore

        extra_body = optional_params.get("extra_body", {})
        azure_ad_token: Optional[str] = None
        if extra_body is not None:
            azure_ad_token = extra_body.pop("azure_ad_token", None)
        else:
            azure_ad_token = get_secret("AZURE_AD_TOKEN")  # type: ignore

        response = azure_assistants_api.add_message(
            thread_id=thread_id,
            message_data=message_data,
            api_base=api_base,
            api_key=api_key,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            client=client,
            a_add_message=a_add_message,
            litellm_params=litellm_params_dict,
        )
    else:
        raise litellm.exceptions.BadRequestError(
            message="LiteLLM doesn't support {} for 'create_thread'. Only 'openai' is supported.".format(
                custom_llm_provider
            ),
            model="n/a",
            llm_provider=custom_llm_provider,
            response=httpx.Response(
                status_code=400,
                content="Unsupported provider",
                request=httpx.Request(method="create_thread", url="https://github.com/BerriAI/litellm"),  # type: ignore
            ),
        )

    return response  # type: ignore


async def aget_messages(
    custom_llm_provider: Literal["openai", "azure"],
    thread_id: str,
    client: Optional[AsyncOpenAI] = None,
    **kwargs,
) -> AsyncCursorPage[OpenAIMessage]:
    loop = asyncio.get_event_loop()
    ### PASS ARGS TO GET ASSISTANTS ###
    kwargs["aget_messages"] = True
    try:
        # Use a partial function to pass your keyword arguments
        func = partial(
            get_messages,
            custom_llm_provider,
            thread_id,
            client,
            **kwargs,
        )

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        _, custom_llm_provider, _, _ = get_llm_provider(  # type: ignore
            model="", custom_llm_provider=custom_llm_provider
        )  # type: ignore

        # Await normally
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            # Call the synchronous function using run_in_executor
            response = init_response
        return response  # type: ignore
    except Exception as e:
        raise exception_type(
            model="",
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs={},
            extra_kwargs=kwargs,
        )


def get_messages(
    custom_llm_provider: Literal["openai", "azure"],
    thread_id: str,
    client: Optional[Any] = None,
    **kwargs,
) -> SyncCursorPage[OpenAIMessage]:
    aget_messages = kwargs.pop("aget_messages", None)
    optional_params = GenericLiteLLMParams(**kwargs)
    litellm_params_dict = get_litellm_params(**kwargs)

    ### TIMEOUT LOGIC ###
    timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
    # set timeout for 10 minutes by default

    if (
        timeout is not None
        and isinstance(timeout, httpx.Timeout)
        and supports_httpx_timeout(custom_llm_provider) is False
    ):
        read_timeout = timeout.read or 600
        timeout = read_timeout  # default 10 min timeout
    elif timeout is not None and not isinstance(timeout, httpx.Timeout):
        timeout = float(timeout)  # type: ignore
    elif timeout is None:
        timeout = 600.0

    response: Optional[SyncCursorPage[OpenAIMessage]] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    if custom_llm_provider == "openai":
        api_base = (
            optional_params.api_base  # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            or litellm.api_base
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        )
        organization = (
            optional_params.organization
            or litellm.organization
            or os.getenv("OPENAI_ORGANIZATION", None)
            or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
        )
        # set API KEY
        api_key = (
            optional_params.api_key
            or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
            or litellm.openai_key
            or os.getenv("OPENAI_API_KEY")
        )
        response = openai_assistants_api.get_messages(
            thread_id=thread_id,
            api_base=api_base,
            api_key=api_key,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            organization=organization,
            client=client,
            aget_messages=aget_messages,
        )
    elif custom_llm_provider == "azure":
        api_base = (
            optional_params.api_base or litellm.api_base or get_secret("AZURE_API_BASE")
        )  # type: ignore

        api_version: Optional[str] = (
            optional_params.api_version
            or litellm.api_version
            or get_secret("AZURE_API_VERSION")
        )  # type: ignore

        api_key = (
            optional_params.api_key
            or litellm.api_key
            or litellm.azure_key
            or get_secret("AZURE_OPENAI_API_KEY")
            or get_secret("AZURE_API_KEY")
        )  # type: ignore

        extra_body = optional_params.get("extra_body", {})
        azure_ad_token: Optional[str] = None
        if extra_body is not None:
            azure_ad_token = extra_body.pop("azure_ad_token", None)
        else:
            azure_ad_token = get_secret("AZURE_AD_TOKEN")  # type: ignore

        response = azure_assistants_api.get_messages(
            thread_id=thread_id,
            api_base=api_base,
            api_key=api_key,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            client=client,
            aget_messages=aget_messages,
            litellm_params=litellm_params_dict,
        )
    else:
        raise litellm.exceptions.BadRequestError(
            message="LiteLLM doesn't support {} for 'get_messages'. Only 'openai' is supported.".format(
                custom_llm_provider
            ),
            model="n/a",
            llm_provider=custom_llm_provider,
            response=httpx.Response(
                status_code=400,
                content="Unsupported provider",
                request=httpx.Request(method="create_thread", url="https://github.com/BerriAI/litellm"),  # type: ignore
            ),
        )

    return response  # type: ignore


### RUNS ###
def arun_thread_stream(
    *,
    event_handler: Optional[AssistantEventHandler] = None,
    **kwargs,
) -> AsyncAssistantStreamManager[AsyncAssistantEventHandler]:
    kwargs["arun_thread"] = True
    return run_thread(stream=True, event_handler=event_handler, **kwargs)  # type: ignore


async def arun_thread(
    custom_llm_provider: Literal["openai", "azure"],
    thread_id: str,
    assistant_id: str,
    additional_instructions: Optional[str] = None,
    instructions: Optional[str] = None,
    metadata: Optional[dict] = None,
    model: Optional[str] = None,
    stream: Optional[bool] = None,
    tools: Optional[Iterable[AssistantToolParam]] = None,
    client: Optional[Any] = None,
    **kwargs,
) -> Run:
    loop = asyncio.get_event_loop()
    ### PASS ARGS TO GET ASSISTANTS ###
    kwargs["arun_thread"] = True
    try:
        # Use a partial function to pass your keyword arguments
        func = partial(
            run_thread,
            custom_llm_provider,
            thread_id,
            assistant_id,
            additional_instructions,
            instructions,
            metadata,
            model,
            stream,
            tools,
            client,
            **kwargs,
        )

        # Add the context to the function
        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)

        _, custom_llm_provider, _, _ = get_llm_provider(  # type: ignore
            model="", custom_llm_provider=custom_llm_provider
        )  # type: ignore

        # Await normally
        init_response = await loop.run_in_executor(None, func_with_context)
        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            # Call the synchronous function using run_in_executor
            response = init_response
        return response  # type: ignore
    except Exception as e:
        raise exception_type(
            model="",
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs={},
            extra_kwargs=kwargs,
        )


def run_thread_stream(
    *,
    event_handler: Optional[AssistantEventHandler] = None,
    **kwargs,
) -> AssistantStreamManager[AssistantEventHandler]:
    return run_thread(stream=True, event_handler=event_handler, **kwargs)  # type: ignore


def run_thread(
    custom_llm_provider: Literal["openai", "azure"],
    thread_id: str,
    assistant_id: str,
    additional_instructions: Optional[str] = None,
    instructions: Optional[str] = None,
    metadata: Optional[dict] = None,
    model: Optional[str] = None,
    stream: Optional[bool] = None,
    tools: Optional[Iterable[AssistantToolParam]] = None,
    client: Optional[Any] = None,
    event_handler: Optional[AssistantEventHandler] = None,  # for stream=True calls
    **kwargs,
) -> Run:
    """Run a given thread + assistant."""
    arun_thread = kwargs.pop("arun_thread", None)
    optional_params = GenericLiteLLMParams(**kwargs)
    litellm_params_dict = get_litellm_params(**kwargs)

    ### TIMEOUT LOGIC ###
    timeout = optional_params.timeout or kwargs.get("request_timeout", 600) or 600
    # set timeout for 10 minutes by default

    if (
        timeout is not None
        and isinstance(timeout, httpx.Timeout)
        and supports_httpx_timeout(custom_llm_provider) is False
    ):
        read_timeout = timeout.read or 600
        timeout = read_timeout  # default 10 min timeout
    elif timeout is not None and not isinstance(timeout, httpx.Timeout):
        timeout = float(timeout)  # type: ignore
    elif timeout is None:
        timeout = 600.0

    response: Optional[Run] = None
    if custom_llm_provider == "openai":
        api_base = (
            optional_params.api_base  # for deepinfra/perplexity/anyscale/groq we check in get_llm_provider and pass in the api base from there
            or litellm.api_base
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        )
        organization = (
            optional_params.organization
            or litellm.organization
            or os.getenv("OPENAI_ORGANIZATION", None)
            or None  # default - https://github.com/openai/openai-python/blob/284c1799070c723c6a553337134148a7ab088dd8/openai/util.py#L105
        )
        # set API KEY
        api_key = (
            optional_params.api_key
            or litellm.api_key  # for deepinfra/perplexity/anyscale we check in get_llm_provider and pass in the api key from there
            or litellm.openai_key
            or os.getenv("OPENAI_API_KEY")
        )

        response = openai_assistants_api.run_thread(
            thread_id=thread_id,
            assistant_id=assistant_id,
            additional_instructions=additional_instructions,
            instructions=instructions,
            metadata=metadata,
            model=model,
            stream=stream,
            tools=tools,
            api_base=api_base,
            api_key=api_key,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            organization=organization,
            client=client,
            arun_thread=arun_thread,
            event_handler=event_handler,
        )
    elif custom_llm_provider == "azure":
        api_base = (
            optional_params.api_base or litellm.api_base or get_secret("AZURE_API_BASE")
        )  # type: ignore

        api_version = (
            optional_params.api_version
            or litellm.api_version
            or get_secret("AZURE_API_VERSION")
        )  # type: ignore

        api_key = (
            optional_params.api_key
            or litellm.api_key
            or litellm.azure_key
            or get_secret("AZURE_OPENAI_API_KEY")
            or get_secret("AZURE_API_KEY")
        )  # type: ignore

        extra_body = optional_params.get("extra_body", {})
        azure_ad_token = None
        if extra_body is not None:
            azure_ad_token = extra_body.pop("azure_ad_token", None)
        else:
            azure_ad_token = get_secret("AZURE_AD_TOKEN")  # type: ignore

        response = azure_assistants_api.run_thread(
            thread_id=thread_id,
            assistant_id=assistant_id,
            additional_instructions=additional_instructions,
            instructions=instructions,
            metadata=metadata,
            model=model,
            stream=stream,
            tools=tools,
            api_base=str(api_base) if api_base is not None else None,
            api_key=str(api_key) if api_key is not None else None,
            api_version=str(api_version) if api_version is not None else None,
            azure_ad_token=str(azure_ad_token) if azure_ad_token is not None else None,
            timeout=timeout,
            max_retries=optional_params.max_retries,
            client=client,
            arun_thread=arun_thread,
            litellm_params=litellm_params_dict,
        )  # type: ignore
    else:
        raise litellm.exceptions.BadRequestError(
            message="LiteLLM doesn't support {} for 'run_thread'. Only 'openai' is supported.".format(
                custom_llm_provider
            ),
            model="n/a",
            llm_provider=custom_llm_provider,
            response=httpx.Response(
                status_code=400,
                content="Unsupported provider",
                request=httpx.Request(method="create_thread", url="https://github.com/BerriAI/litellm"),  # type: ignore
            ),
        )
    return response  # type: ignore

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\backend_ps.py ===
"""
A PostScript backend, which can produce both PostScript .ps and .eps.
"""

import bisect
import codecs
import datetime
from enum import Enum
import functools
from io import StringIO
import itertools
import logging
import math
import os
import pathlib
import shutil
import struct
from tempfile import TemporaryDirectory
import textwrap
import time

import fontTools
import numpy as np

import matplotlib as mpl
from matplotlib import _api, cbook, _path, _text_helpers
from matplotlib._afm import AFM
from matplotlib.backend_bases import (
    _Backend, FigureCanvasBase, FigureManagerBase, RendererBase)
from matplotlib.cbook import is_writable_file_like, file_requires_unicode
from matplotlib.font_manager import get_font
from matplotlib.ft2font import LoadFlags
from matplotlib._mathtext_data import uni2type1
from matplotlib.path import Path
from matplotlib.texmanager import TexManager
from matplotlib.transforms import Affine2D
from matplotlib.backends.backend_mixed import MixedModeRenderer
from . import _backend_pdf_ps


_log = logging.getLogger(__name__)
debugPS = False


papersize = {'letter': (8.5, 11),
             'legal': (8.5, 14),
             'ledger': (11, 17),
             'a0': (33.11, 46.81),
             'a1': (23.39, 33.11),
             'a2': (16.54, 23.39),
             'a3': (11.69, 16.54),
             'a4': (8.27, 11.69),
             'a5': (5.83, 8.27),
             'a6': (4.13, 5.83),
             'a7': (2.91, 4.13),
             'a8': (2.05, 2.91),
             'a9': (1.46, 2.05),
             'a10': (1.02, 1.46),
             'b0': (40.55, 57.32),
             'b1': (28.66, 40.55),
             'b2': (20.27, 28.66),
             'b3': (14.33, 20.27),
             'b4': (10.11, 14.33),
             'b5': (7.16, 10.11),
             'b6': (5.04, 7.16),
             'b7': (3.58, 5.04),
             'b8': (2.51, 3.58),
             'b9': (1.76, 2.51),
             'b10': (1.26, 1.76)}


def _nums_to_str(*args, sep=" "):
    return sep.join(f"{arg:1.3f}".rstrip("0").rstrip(".") for arg in args)


def _move_path_to_path_or_stream(src, dst):
    """
    Move the contents of file at *src* to path-or-filelike *dst*.

    If *dst* is a path, the metadata of *src* are *not* copied.
    """
    if is_writable_file_like(dst):
        fh = (open(src, encoding='latin-1')
              if file_requires_unicode(dst)
              else open(src, 'rb'))
        with fh:
            shutil.copyfileobj(fh, dst)
    else:
        shutil.move(src, dst, copy_function=shutil.copyfile)


def _font_to_ps_type3(font_path, chars):
    """
    Subset *chars* from the font at *font_path* into a Type 3 font.

    Parameters
    ----------
    font_path : path-like
        Path to the font to be subsetted.
    chars : str
        The characters to include in the subsetted font.

    Returns
    -------
    str
        The string representation of a Type 3 font, which can be included
        verbatim into a PostScript file.
    """
    font = get_font(font_path, hinting_factor=1)
    glyph_ids = [font.get_char_index(c) for c in chars]

    preamble = """\
%!PS-Adobe-3.0 Resource-Font
%%Creator: Converted from TrueType to Type 3 by Matplotlib.
10 dict begin
/FontName /{font_name} def
/PaintType 0 def
/FontMatrix [{inv_units_per_em} 0 0 {inv_units_per_em} 0 0] def
/FontBBox [{bbox}] def
/FontType 3 def
/Encoding [{encoding}] def
/CharStrings {num_glyphs} dict dup begin
/.notdef 0 def
""".format(font_name=font.postscript_name,
           inv_units_per_em=1 / font.units_per_EM,
           bbox=" ".join(map(str, font.bbox)),
           encoding=" ".join(f"/{font.get_glyph_name(glyph_id)}"
                             for glyph_id in glyph_ids),
           num_glyphs=len(glyph_ids) + 1)
    postamble = """
end readonly def

/BuildGlyph {
 exch begin
 CharStrings exch
 2 copy known not {pop /.notdef} if
 true 3 1 roll get exec
 end
} _d

/BuildChar {
 1 index /Encoding get exch get
 1 index /BuildGlyph get exec
} _d

FontName currentdict end definefont pop
"""

    entries = []
    for glyph_id in glyph_ids:
        g = font.load_glyph(glyph_id, LoadFlags.NO_SCALE)
        v, c = font.get_path()
        entries.append(
            "/%(name)s{%(bbox)s sc\n" % {
                "name": font.get_glyph_name(glyph_id),
                "bbox": " ".join(map(str, [g.horiAdvance, 0, *g.bbox])),
            }
            + _path.convert_to_string(
                # Convert back to TrueType's internal units (1/64's).
                # (Other dimensions are already in these units.)
                Path(v * 64, c), None, None, False, None, 0,
                # No code for quad Beziers triggers auto-conversion to cubics.
                # Drop intermediate closepolys (relying on the outline
                # decomposer always explicitly moving to the closing point
                # first).
                [b"m", b"l", b"", b"c", b""], True).decode("ascii")
            + "ce} _d"
        )

    return preamble + "\n".join(entries) + postamble


def _font_to_ps_type42(font_path, chars, fh):
    """
    Subset *chars* from the font at *font_path* into a Type 42 font at *fh*.

    Parameters
    ----------
    font_path : path-like
        Path to the font to be subsetted.
    chars : str
        The characters to include in the subsetted font.
    fh : file-like
        Where to write the font.
    """
    subset_str = ''.join(chr(c) for c in chars)
    _log.debug("SUBSET %s characters: %s", font_path, subset_str)
    try:
        kw = {}
        # fix this once we support loading more fonts from a collection
        # https://github.com/matplotlib/matplotlib/issues/3135#issuecomment-571085541
        if font_path.endswith('.ttc'):
            kw['fontNumber'] = 0
        with (fontTools.ttLib.TTFont(font_path, **kw) as font,
              _backend_pdf_ps.get_glyphs_subset(font_path, subset_str) as subset):
            fontdata = _backend_pdf_ps.font_as_file(subset).getvalue()
            _log.debug(
                "SUBSET %s %d -> %d", font_path, os.stat(font_path).st_size,
                len(fontdata)
            )
            fh.write(_serialize_type42(font, subset, fontdata))
    except RuntimeError:
        _log.warning(
            "The PostScript backend does not currently support the selected font (%s).",
            font_path)
        raise


def _serialize_type42(font, subset, fontdata):
    """
    Output a PostScript Type-42 format representation of font

    Parameters
    ----------
    font : fontTools.ttLib.ttFont.TTFont
        The original font object
    subset : fontTools.ttLib.ttFont.TTFont
        The subset font object
    fontdata : bytes
        The raw font data in TTF format

    Returns
    -------
    str
        The Type-42 formatted font
    """
    version, breakpoints = _version_and_breakpoints(font.get('loca'), fontdata)
    post = font['post']
    name = font['name']
    chars = _generate_charstrings(subset)
    sfnts = _generate_sfnts(fontdata, subset, breakpoints)
    return textwrap.dedent(f"""
        %%!PS-TrueTypeFont-{version[0]}.{version[1]}-{font['head'].fontRevision:.7f}
        10 dict begin
        /FontType 42 def
        /FontMatrix [1 0 0 1 0 0] def
        /FontName /{name.getDebugName(6)} def
        /FontInfo 7 dict dup begin
        /FullName ({name.getDebugName(4)}) def
        /FamilyName ({name.getDebugName(1)}) def
        /Version ({name.getDebugName(5)}) def
        /ItalicAngle {post.italicAngle} def
        /isFixedPitch {'true' if post.isFixedPitch else 'false'} def
        /UnderlinePosition {post.underlinePosition} def
        /UnderlineThickness {post.underlineThickness} def
        end readonly def
        /Encoding StandardEncoding def
        /FontBBox [{_nums_to_str(*_bounds(font))}] def
        /PaintType 0 def
        /CIDMap 0 def
        {chars}
        {sfnts}
        FontName currentdict end definefont pop
        """)


def _version_and_breakpoints(loca, fontdata):
    """
    Read the version number of the font and determine sfnts breakpoints.

    When a TrueType font file is written as a Type 42 font, it has to be
    broken into substrings of at most 65535 bytes. These substrings must
    begin at font table boundaries or glyph boundaries in the glyf table.
    This function determines all possible breakpoints and it is the caller's
    responsibility to do the splitting.

    Helper function for _font_to_ps_type42.

    Parameters
    ----------
    loca : fontTools.ttLib._l_o_c_a.table__l_o_c_a or None
        The loca table of the font if available
    fontdata : bytes
        The raw data of the font

    Returns
    -------
    version : tuple[int, int]
        A 2-tuple of the major version number and minor version number.
    breakpoints : list[int]
        The breakpoints is a sorted list of offsets into fontdata; if loca is not
        available, just the table boundaries.
    """
    v1, v2, numTables = struct.unpack('>3h', fontdata[:6])
    version = (v1, v2)

    tables = {}
    for i in range(numTables):
        tag, _, offset, _ = struct.unpack('>4sIII', fontdata[12 + i*16:12 + (i+1)*16])
        tables[tag.decode('ascii')] = offset
    if loca is not None:
        glyf_breakpoints = {tables['glyf'] + offset for offset in loca.locations[:-1]}
    else:
        glyf_breakpoints = set()
    breakpoints = sorted({*tables.values(), *glyf_breakpoints, len(fontdata)})

    return version, breakpoints


def _bounds(font):
    """
    Compute the font bounding box, as if all glyphs were written
    at the same start position.

    Helper function for _font_to_ps_type42.

    Parameters
    ----------
    font : fontTools.ttLib.ttFont.TTFont
        The font

    Returns
    -------
    tuple
        (xMin, yMin, xMax, yMax) of the combined bounding box
        of all the glyphs in the font
    """
    gs = font.getGlyphSet(False)
    pen = fontTools.pens.boundsPen.BoundsPen(gs)
    for name in gs.keys():
        gs[name].draw(pen)
    return pen.bounds or (0, 0, 0, 0)


def _generate_charstrings(font):
    """
    Transform font glyphs into CharStrings

    Helper function for _font_to_ps_type42.

    Parameters
    ----------
    font : fontTools.ttLib.ttFont.TTFont
        The font

    Returns
    -------
    str
        A definition of the CharStrings dictionary in PostScript
    """
    go = font.getGlyphOrder()
    s = f'/CharStrings {len(go)} dict dup begin\n'
    for i, name in enumerate(go):
        s += f'/{name} {i} def\n'
    s += 'end readonly def'
    return s


def _generate_sfnts(fontdata, font, breakpoints):
    """
    Transform font data into PostScript sfnts format.

    Helper function for _font_to_ps_type42.

    Parameters
    ----------
    fontdata : bytes
        The raw data of the font
    font : fontTools.ttLib.ttFont.TTFont
        The fontTools font object
    breakpoints : list
        Sorted offsets of possible breakpoints

    Returns
    -------
    str
        The sfnts array for the font definition, consisting
        of hex-encoded strings in PostScript format
    """
    s = '/sfnts['
    pos = 0
    while pos < len(fontdata):
        i = bisect.bisect_left(breakpoints, pos + 65534)
        newpos = breakpoints[i-1]
        if newpos <= pos:
            # have to accept a larger string
            newpos = breakpoints[-1]
        s += f'<{fontdata[pos:newpos].hex()}00>'  # Always NUL terminate.
        pos = newpos
    s += ']def'
    return '\n'.join(s[i:i+100] for i in range(0, len(s), 100))


def _log_if_debug_on(meth):
    """
    Wrap `RendererPS` method *meth* to emit a PS comment with the method name,
    if the global flag `debugPS` is set.
    """
    @functools.wraps(meth)
    def wrapper(self, *args, **kwargs):
        if debugPS:
            self._pswriter.write(f"% {meth.__name__}\n")
        return meth(self, *args, **kwargs)

    return wrapper


class RendererPS(_backend_pdf_ps.RendererPDFPSBase):
    """
    The renderer handles all the drawing primitives using a graphics
    context instance that controls the colors/styles.
    """

    _afm_font_dir = cbook._get_data_path("fonts/afm")
    _use_afm_rc_name = "ps.useafm"

    def __init__(self, width, height, pswriter, imagedpi=72):
        # Although postscript itself is dpi independent, we need to inform the
        # image code about a requested dpi to generate high resolution images
        # and them scale them before embedding them.
        super().__init__(width, height)
        self._pswriter = pswriter
        if mpl.rcParams['text.usetex']:
            self.textcnt = 0
            self.psfrag = []
        self.imagedpi = imagedpi

        # current renderer state (None=uninitialised)
        self.color = None
        self.linewidth = None
        self.linejoin = None
        self.linecap = None
        self.linedash = None
        self.fontname = None
        self.fontsize = None
        self._hatches = {}
        self.image_magnification = imagedpi / 72
        self._clip_paths = {}
        self._path_collection_id = 0

        self._character_tracker = _backend_pdf_ps.CharacterTracker()
        self._logwarn_once = functools.cache(_log.warning)

    def _is_transparent(self, rgb_or_rgba):
        if rgb_or_rgba is None:
            return True  # Consistent with rgbFace semantics.
        elif len(rgb_or_rgba) == 4:
            if rgb_or_rgba[3] == 0:
                return True
            if rgb_or_rgba[3] != 1:
                self._logwarn_once(
                    "The PostScript backend does not support transparency; "
                    "partially transparent artists will be rendered opaque.")
            return False
        else:  # len() == 3.
            return False

    def set_color(self, r, g, b, store=True):
        if (r, g, b) != self.color:
            self._pswriter.write(f"{_nums_to_str(r)} setgray\n"
                                 if r == g == b else
                                 f"{_nums_to_str(r, g, b)} setrgbcolor\n")
            if store:
                self.color = (r, g, b)

    def set_linewidth(self, linewidth, store=True):
        linewidth = float(linewidth)
        if linewidth != self.linewidth:
            self._pswriter.write(f"{_nums_to_str(linewidth)} setlinewidth\n")
            if store:
                self.linewidth = linewidth

    @staticmethod
    def _linejoin_cmd(linejoin):
        # Support for directly passing integer values is for backcompat.
        linejoin = {'miter': 0, 'round': 1, 'bevel': 2, 0: 0, 1: 1, 2: 2}[
            linejoin]
        return f"{linejoin:d} setlinejoin\n"

    def set_linejoin(self, linejoin, store=True):
        if linejoin != self.linejoin:
            self._pswriter.write(self._linejoin_cmd(linejoin))
            if store:
                self.linejoin = linejoin

    @staticmethod
    def _linecap_cmd(linecap):
        # Support for directly passing integer values is for backcompat.
        linecap = {'butt': 0, 'round': 1, 'projecting': 2, 0: 0, 1: 1, 2: 2}[
            linecap]
        return f"{linecap:d} setlinecap\n"

    def set_linecap(self, linecap, store=True):
        if linecap != self.linecap:
            self._pswriter.write(self._linecap_cmd(linecap))
            if store:
                self.linecap = linecap

    def set_linedash(self, offset, seq, store=True):
        if self.linedash is not None:
            oldo, oldseq = self.linedash
            if np.array_equal(seq, oldseq) and oldo == offset:
                return

        self._pswriter.write(f"[{_nums_to_str(*seq)}] {_nums_to_str(offset)} setdash\n"
                             if seq is not None and len(seq) else
                             "[] 0 setdash\n")
        if store:
            self.linedash = (offset, seq)

    def set_font(self, fontname, fontsize, store=True):
        if (fontname, fontsize) != (self.fontname, self.fontsize):
            self._pswriter.write(f"/{fontname} {fontsize:1.3f} selectfont\n")
            if store:
                self.fontname = fontname
                self.fontsize = fontsize

    def create_hatch(self, hatch, linewidth):
        sidelen = 72
        if hatch in self._hatches:
            return self._hatches[hatch]
        name = 'H%d' % len(self._hatches)
        pageheight = self.height * 72
        self._pswriter.write(f"""\
  << /PatternType 1
     /PaintType 2
     /TilingType 2
     /BBox[0 0 {sidelen:d} {sidelen:d}]
     /XStep {sidelen:d}
     /YStep {sidelen:d}

     /PaintProc {{
        pop
        {linewidth:g} setlinewidth
{self._convert_path(Path.hatch(hatch), Affine2D().scale(sidelen), simplify=False)}
        gsave
        fill
        grestore
        stroke
     }} bind
   >>
   matrix
   0 {pageheight:g} translate
   makepattern
   /{name} exch def
""")
        self._hatches[hatch] = name
        return name

    def get_image_magnification(self):
        """
        Get the factor by which to magnify images passed to draw_image.
        Allows a backend to have images at a different resolution to other
        artists.
        """
        return self.image_magnification

    def _convert_path(self, path, transform, clip=False, simplify=None):
        if clip:
            clip = (0.0, 0.0, self.width * 72.0, self.height * 72.0)
        else:
            clip = None
        return _path.convert_to_string(
            path, transform, clip, simplify, None,
            6, [b"m", b"l", b"", b"c", b"cl"], True).decode("ascii")

    def _get_clip_cmd(self, gc):
        clip = []
        rect = gc.get_clip_rectangle()
        if rect is not None:
            clip.append(f"{_nums_to_str(*rect.p0, *rect.size)} rectclip\n")
        path, trf = gc.get_clip_path()
        if path is not None:
            key = (path, id(trf))
            custom_clip_cmd = self._clip_paths.get(key)
            if custom_clip_cmd is None:
                custom_clip_cmd = "c%d" % len(self._clip_paths)
                self._pswriter.write(f"""\
/{custom_clip_cmd} {{
{self._convert_path(path, trf, simplify=False)}
clip
newpath
}} bind def
""")
                self._clip_paths[key] = custom_clip_cmd
            clip.append(f"{custom_clip_cmd}\n")
        return "".join(clip)

    @_log_if_debug_on
    def draw_image(self, gc, x, y, im, transform=None):
        # docstring inherited

        h, w = im.shape[:2]
        imagecmd = "false 3 colorimage"
        data = im[::-1, :, :3]  # Vertically flipped rgb values.
        hexdata = data.tobytes().hex("\n", -64)  # Linewrap to 128 chars.

        if transform is None:
            matrix = "1 0 0 1 0 0"
            xscale = w / self.image_magnification
            yscale = h / self.image_magnification
        else:
            matrix = " ".join(map(str, transform.frozen().to_values()))
            xscale = 1.0
            yscale = 1.0

        self._pswriter.write(f"""\
gsave
{self._get_clip_cmd(gc)}
{x:g} {y:g} translate
[{matrix}] concat
{xscale:g} {yscale:g} scale
/DataString {w:d} string def
{w:d} {h:d} 8 [ {w:d} 0 0 -{h:d} 0 {h:d} ]
{{
currentfile DataString readhexstring pop
}} bind {imagecmd}
{hexdata}
grestore
""")

    @_log_if_debug_on
    def draw_path(self, gc, path, transform, rgbFace=None):
        # docstring inherited
        clip = rgbFace is None and gc.get_hatch_path() is None
        simplify = path.should_simplify and clip
        ps = self._convert_path(path, transform, clip=clip, simplify=simplify)
        self._draw_ps(ps, gc, rgbFace)

    @_log_if_debug_on
    def draw_markers(
            self, gc, marker_path, marker_trans, path, trans, rgbFace=None):
        # docstring inherited

        ps_color = (
            None
            if self._is_transparent(rgbFace)
            else f'{_nums_to_str(rgbFace[0])} setgray'
            if rgbFace[0] == rgbFace[1] == rgbFace[2]
            else f'{_nums_to_str(*rgbFace[:3])} setrgbcolor')

        # construct the generic marker command:

        # don't want the translate to be global
        ps_cmd = ['/o {', 'gsave', 'newpath', 'translate']

        lw = gc.get_linewidth()
        alpha = (gc.get_alpha()
                 if gc.get_forced_alpha() or len(gc.get_rgb()) == 3
                 else gc.get_rgb()[3])
        stroke = lw > 0 and alpha > 0
        if stroke:
            ps_cmd.append('%.1f setlinewidth' % lw)
            ps_cmd.append(self._linejoin_cmd(gc.get_joinstyle()))
            ps_cmd.append(self._linecap_cmd(gc.get_capstyle()))

        ps_cmd.append(self._convert_path(marker_path, marker_trans,
                                         simplify=False))

        if rgbFace:
            if stroke:
                ps_cmd.append('gsave')
            if ps_color:
                ps_cmd.extend([ps_color, 'fill'])
            if stroke:
                ps_cmd.append('grestore')

        if stroke:
            ps_cmd.append('stroke')
        ps_cmd.extend(['grestore', '} bind def'])

        for vertices, code in path.iter_segments(
                trans,
                clip=(0, 0, self.width*72, self.height*72),
                simplify=False):
            if len(vertices):
                x, y = vertices[-2:]
                ps_cmd.append(f"{x:g} {y:g} o")

        ps = '\n'.join(ps_cmd)
        self._draw_ps(ps, gc, rgbFace, fill=False, stroke=False)

    @_log_if_debug_on
    def draw_path_collection(self, gc, master_transform, paths, all_transforms,
                             offsets, offset_trans, facecolors, edgecolors,
                             linewidths, linestyles, antialiaseds, urls,
                             offset_position):
        # Is the optimization worth it? Rough calculation:
        # cost of emitting a path in-line is
        #     (len_path + 2) * uses_per_path
        # cost of definition+use is
        #     (len_path + 3) + 3 * uses_per_path
        len_path = len(paths[0].vertices) if len(paths) > 0 else 0
        uses_per_path = self._iter_collection_uses_per_path(
            paths, all_transforms, offsets, facecolors, edgecolors)
        should_do_optimization = \
            len_path + 3 * uses_per_path + 3 < (len_path + 2) * uses_per_path
        if not should_do_optimization:
            return RendererBase.draw_path_collection(
                self, gc, master_transform, paths, all_transforms,
                offsets, offset_trans, facecolors, edgecolors,
                linewidths, linestyles, antialiaseds, urls,
                offset_position)

        path_codes = []
        for i, (path, transform) in enumerate(self._iter_collection_raw_paths(
                master_transform, paths, all_transforms)):
            name = 'p%d_%d' % (self._path_collection_id, i)
            path_bytes = self._convert_path(path, transform, simplify=False)
            self._pswriter.write(f"""\
/{name} {{
newpath
translate
{path_bytes}
}} bind def
""")
            path_codes.append(name)

        for xo, yo, path_id, gc0, rgbFace in self._iter_collection(
                gc, path_codes, offsets, offset_trans,
                facecolors, edgecolors, linewidths, linestyles,
                antialiaseds, urls, offset_position):
            ps = f"{xo:g} {yo:g} {path_id}"
            self._draw_ps(ps, gc0, rgbFace)

        self._path_collection_id += 1

    @_log_if_debug_on
    def draw_tex(self, gc, x, y, s, prop, angle, *, mtext=None):
        # docstring inherited
        if self._is_transparent(gc.get_rgb()):
            return  # Special handling for fully transparent.

        if not hasattr(self, "psfrag"):
            self._logwarn_once(
                "The PS backend determines usetex status solely based on "
                "rcParams['text.usetex'] and does not support having "
                "usetex=True only for some elements; this element will thus "
                "be rendered as if usetex=False.")
            self.draw_text(gc, x, y, s, prop, angle, False, mtext)
            return

        w, h, bl = self.get_text_width_height_descent(s, prop, ismath="TeX")
        fontsize = prop.get_size_in_points()
        thetext = 'psmarker%d' % self.textcnt
        color = _nums_to_str(*gc.get_rgb()[:3], sep=',')
        fontcmd = {'sans-serif': r'{\sffamily %s}',
                   'monospace': r'{\ttfamily %s}'}.get(
                       mpl.rcParams['font.family'][0], r'{\rmfamily %s}')
        s = fontcmd % s
        tex = r'\color[rgb]{%s} %s' % (color, s)

        # Stick to bottom-left alignment, so subtract descent from the text-normal
        # direction since text is normally positioned by its baseline.
        rangle = np.radians(angle + 90)
        pos = _nums_to_str(x - bl * np.cos(rangle), y - bl * np.sin(rangle))
        self.psfrag.append(
            r'\psfrag{%s}[bl][bl][1][%f]{\fontsize{%f}{%f}%s}' % (
                thetext, angle, fontsize, fontsize*1.25, tex))

        self._pswriter.write(f"""\
gsave
{pos} moveto
({thetext})
show
grestore
""")
        self.textcnt += 1

    @_log_if_debug_on
    def draw_text(self, gc, x, y, s, prop, angle, ismath=False, mtext=None):
        # docstring inherited

        if self._is_transparent(gc.get_rgb()):
            return  # Special handling for fully transparent.

        if ismath == 'TeX':
            return self.draw_tex(gc, x, y, s, prop, angle)

        if ismath:
            return self.draw_mathtext(gc, x, y, s, prop, angle)

        stream = []  # list of (ps_name, x, char_name)

        if mpl.rcParams['ps.useafm']:
            font = self._get_font_afm(prop)
            ps_name = (font.postscript_name.encode("ascii", "replace")
                        .decode("ascii"))
            scale = 0.001 * prop.get_size_in_points()
            thisx = 0
            last_name = None  # kerns returns 0 for None.
            for c in s:
                name = uni2type1.get(ord(c), f"uni{ord(c):04X}")
                try:
                    width = font.get_width_from_char_name(name)
                except KeyError:
                    name = 'question'
                    width = font.get_width_char('?')
                kern = font.get_kern_dist_from_name(last_name, name)
                last_name = name
                thisx += kern * scale
                stream.append((ps_name, thisx, name))
                thisx += width * scale

        else:
            font = self._get_font_ttf(prop)
            self._character_tracker.track(font, s)
            for item in _text_helpers.layout(s, font):
                ps_name = (item.ft_object.postscript_name
                           .encode("ascii", "replace").decode("ascii"))
                glyph_name = item.ft_object.get_glyph_name(item.glyph_idx)
                stream.append((ps_name, item.x, glyph_name))
        self.set_color(*gc.get_rgb())

        for ps_name, group in itertools. \
                groupby(stream, lambda entry: entry[0]):
            self.set_font(ps_name, prop.get_size_in_points(), False)
            thetext = "\n".join(f"{x:g} 0 m /{name:s} glyphshow"
                                for _, x, name in group)
            self._pswriter.write(f"""\
gsave
{self._get_clip_cmd(gc)}
{x:g} {y:g} translate
{angle:g} rotate
{thetext}
grestore
""")

    @_log_if_debug_on
    def draw_mathtext(self, gc, x, y, s, prop, angle):
        """Draw the math text using matplotlib.mathtext."""
        width, height, descent, glyphs, rects = \
            self._text2path.mathtext_parser.parse(s, 72, prop)
        self.set_color(*gc.get_rgb())
        self._pswriter.write(
            f"gsave\n"
            f"{x:g} {y:g} translate\n"
            f"{angle:g} rotate\n")
        lastfont = None
        for font, fontsize, num, ox, oy in glyphs:
            self._character_tracker.track_glyph(font, num)
            if (font.postscript_name, fontsize) != lastfont:
                lastfont = font.postscript_name, fontsize
                self._pswriter.write(
                    f"/{font.postscript_name} {fontsize} selectfont\n")
            glyph_name = (
                font.get_name_char(chr(num)) if isinstance(font, AFM) else
                font.get_glyph_name(font.get_char_index(num)))
            self._pswriter.write(
                f"{ox:g} {oy:g} moveto\n"
                f"/{glyph_name} glyphshow\n")
        for ox, oy, w, h in rects:
            self._pswriter.write(f"{ox} {oy} {w} {h} rectfill\n")
        self._pswriter.write("grestore\n")

    @_log_if_debug_on
    def draw_gouraud_triangles(self, gc, points, colors, trans):
        assert len(points) == len(colors)
        if len(points) == 0:
            return
        assert points.ndim == 3
        assert points.shape[1] == 3
        assert points.shape[2] == 2
        assert colors.ndim == 3
        assert colors.shape[1] == 3
        assert colors.shape[2] == 4

        shape = points.shape
        flat_points = points.reshape((shape[0] * shape[1], 2))
        flat_points = trans.transform(flat_points)
        flat_colors = colors.reshape((shape[0] * shape[1], 4))
        points_min = np.min(flat_points, axis=0) - (1 << 12)
        points_max = np.max(flat_points, axis=0) + (1 << 12)
        factor = np.ceil((2 ** 32 - 1) / (points_max - points_min))

        xmin, ymin = points_min
        xmax, ymax = points_max

        data = np.empty(
            shape[0] * shape[1],
            dtype=[('flags', 'u1'), ('points', '2>u4'), ('colors', '3u1')])
        data['flags'] = 0
        data['points'] = (flat_points - points_min) * factor
        data['colors'] = flat_colors[:, :3] * 255.0
        hexdata = data.tobytes().hex("\n", -64)  # Linewrap to 128 chars.

        self._pswriter.write(f"""\
gsave
<< /ShadingType 4
   /ColorSpace [/DeviceRGB]
   /BitsPerCoordinate 32
   /BitsPerComponent 8
   /BitsPerFlag 8
   /AntiAlias true
   /Decode [ {xmin:g} {xmax:g} {ymin:g} {ymax:g} 0 1 0 1 0 1 ]
   /DataSource <
{hexdata}
>
>>
shfill
grestore
""")

    def _draw_ps(self, ps, gc, rgbFace, *, fill=True, stroke=True):
        """
        Emit the PostScript snippet *ps* with all the attributes from *gc*
        applied.  *ps* must consist of PostScript commands to construct a path.

        The *fill* and/or *stroke* kwargs can be set to False if the *ps*
        string already includes filling and/or stroking, in which case
        `_draw_ps` is just supplying properties and clipping.
        """
        write = self._pswriter.write
        mightstroke = (gc.get_linewidth() > 0
                       and not self._is_transparent(gc.get_rgb()))
        if not mightstroke:
            stroke = False
        if self._is_transparent(rgbFace):
            fill = False
        hatch = gc.get_hatch()

        if mightstroke:
            self.set_linewidth(gc.get_linewidth())
            self.set_linejoin(gc.get_joinstyle())
            self.set_linecap(gc.get_capstyle())
            self.set_linedash(*gc.get_dashes())
        if mightstroke or hatch:
            self.set_color(*gc.get_rgb()[:3])
        write('gsave\n')

        write(self._get_clip_cmd(gc))

        write(ps.strip())
        write("\n")

        if fill:
            if stroke or hatch:
                write("gsave\n")
            self.set_color(*rgbFace[:3], store=False)
            write("fill\n")
            if stroke or hatch:
                write("grestore\n")

        if hatch:
            hatch_name = self.create_hatch(hatch, gc.get_hatch_linewidth())
            write("gsave\n")
            write(_nums_to_str(*gc.get_hatch_color()[:3]))
            write(f" {hatch_name} setpattern fill grestore\n")

        if stroke:
            write("stroke\n")

        write("grestore\n")


class _Orientation(Enum):
    portrait, landscape = range(2)

    def swap_if_landscape(self, shape):
        return shape[::-1] if self.name == "landscape" else shape


class FigureCanvasPS(FigureCanvasBase):
    fixed_dpi = 72
    filetypes = {'ps': 'Postscript',
                 'eps': 'Encapsulated Postscript'}

    def get_default_filetype(self):
        return 'ps'

    def _print_ps(
            self, fmt, outfile, *,
            metadata=None, papertype=None, orientation='portrait',
            bbox_inches_restore=None, **kwargs):

        dpi = self.figure.dpi
        self.figure.dpi = 72  # Override the dpi kwarg

        dsc_comments = {}
        if isinstance(outfile, (str, os.PathLike)):
            filename = pathlib.Path(outfile).name
            dsc_comments["Title"] = \
                filename.encode("ascii", "replace").decode("ascii")
        dsc_comments["Creator"] = (metadata or {}).get(
            "Creator",
            f"Matplotlib v{mpl.__version__}, https://matplotlib.org/")
        # See https://reproducible-builds.org/specs/source-date-epoch/
        source_date_epoch = os.getenv("SOURCE_DATE_EPOCH")
        dsc_comments["CreationDate"] = (
            datetime.datetime.fromtimestamp(
                int(source_date_epoch),
                datetime.timezone.utc).strftime("%a %b %d %H:%M:%S %Y")
            if source_date_epoch
            else time.ctime())
        dsc_comments = "\n".join(
            f"%%{k}: {v}" for k, v in dsc_comments.items())

        if papertype is None:
            papertype = mpl.rcParams['ps.papersize']
        papertype = papertype.lower()
        _api.check_in_list(['figure', *papersize], papertype=papertype)

        orientation = _api.check_getitem(
            _Orientation, orientation=orientation.lower())

        printer = (self._print_figure_tex
                   if mpl.rcParams['text.usetex'] else
                   self._print_figure)
        printer(fmt, outfile, dpi=dpi, dsc_comments=dsc_comments,
                orientation=orientation, papertype=papertype,
                bbox_inches_restore=bbox_inches_restore, **kwargs)

    def _print_figure(
            self, fmt, outfile, *,
            dpi, dsc_comments, orientation, papertype,
            bbox_inches_restore=None):
        """
        Render the figure to a filesystem path or a file-like object.

        Parameters are as for `.print_figure`, except that *dsc_comments* is a
        string containing Document Structuring Convention comments,
        generated from the *metadata* parameter to `.print_figure`.
        """
        is_eps = fmt == 'eps'
        if not (isinstance(outfile, (str, os.PathLike))
                or is_writable_file_like(outfile)):
            raise ValueError("outfile must be a path or a file-like object")

        # find the appropriate papertype
        width, height = self.figure.get_size_inches()
        if is_eps or papertype == 'figure':
            paper_width, paper_height = width, height
        else:
            paper_width, paper_height = orientation.swap_if_landscape(
                papersize[papertype])

        # center the figure on the paper
        xo = 72 * 0.5 * (paper_width - width)
        yo = 72 * 0.5 * (paper_height - height)

        llx = xo
        lly = yo
        urx = llx + self.figure.bbox.width
        ury = lly + self.figure.bbox.height
        rotation = 0
        if orientation is _Orientation.landscape:
            llx, lly, urx, ury = lly, llx, ury, urx
            xo, yo = 72 * paper_height - yo, xo
            rotation = 90
        bbox = (llx, lly, urx, ury)

        self._pswriter = StringIO()

        # mixed mode rendering
        ps_renderer = RendererPS(width, height, self._pswriter, imagedpi=dpi)
        renderer = MixedModeRenderer(
            self.figure, width, height, dpi, ps_renderer,
            bbox_inches_restore=bbox_inches_restore)

        self.figure.draw(renderer)

        def print_figure_impl(fh):
            # write the PostScript headers
            if is_eps:
                print("%!PS-Adobe-3.0 EPSF-3.0", file=fh)
            else:
                print("%!PS-Adobe-3.0", file=fh)
                if papertype != 'figure':
                    print(f"%%DocumentPaperSizes: {papertype}", file=fh)
                print("%%Pages: 1", file=fh)
            print(f"%%LanguageLevel: 3\n"
                  f"{dsc_comments}\n"
                  f"%%Orientation: {orientation.name}\n"
                  f"{_get_bbox_header(bbox)}\n"
                  f"%%EndComments\n",
                  end="", file=fh)

            Ndict = len(_psDefs)
            print("%%BeginProlog", file=fh)
            if not mpl.rcParams['ps.useafm']:
                Ndict += len(ps_renderer._character_tracker.used)
            print("/mpldict %d dict def" % Ndict, file=fh)
            print("mpldict begin", file=fh)
            print("\n".join(_psDefs), file=fh)
            if not mpl.rcParams['ps.useafm']:
                for font_path, chars \
                        in ps_renderer._character_tracker.used.items():
                    if not chars:
                        continue
                    fonttype = mpl.rcParams['ps.fonttype']
                    # Can't use more than 255 chars from a single Type 3 font.
                    if len(chars) > 255:
                        fonttype = 42
                    fh.flush()
                    if fonttype == 3:
                        fh.write(_font_to_ps_type3(font_path, chars))
                    else:  # Type 42 only.
                        _font_to_ps_type42(font_path, chars, fh)
            print("end", file=fh)
            print("%%EndProlog", file=fh)

            if not is_eps:
                print("%%Page: 1 1", file=fh)
            print("mpldict begin", file=fh)

            print("%s translate" % _nums_to_str(xo, yo), file=fh)
            if rotation:
                print("%d rotate" % rotation, file=fh)
            print(f"0 0 {_nums_to_str(width*72, height*72)} rectclip", file=fh)

            # write the figure
            print(self._pswriter.getvalue(), file=fh)

            # write the trailer
            print("end", file=fh)
            print("showpage", file=fh)
            if not is_eps:
                print("%%EOF", file=fh)
            fh.flush()

        if mpl.rcParams['ps.usedistiller']:
            # We are going to use an external program to process the output.
            # Write to a temporary file.
            with TemporaryDirectory() as tmpdir:
                tmpfile = os.path.join(tmpdir, "tmp.ps")
                with open(tmpfile, 'w', encoding='latin-1') as fh:
                    print_figure_impl(fh)
                if mpl.rcParams['ps.usedistiller'] == 'ghostscript':
                    _try_distill(gs_distill,
                                 tmpfile, is_eps, ptype=papertype, bbox=bbox)
                elif mpl.rcParams['ps.usedistiller'] == 'xpdf':
                    _try_distill(xpdf_distill,
                                 tmpfile, is_eps, ptype=papertype, bbox=bbox)
                _move_path_to_path_or_stream(tmpfile, outfile)

        else:  # Write directly to outfile.
            with cbook.open_file_cm(outfile, "w", encoding="latin-1") as file:
                if not file_requires_unicode(file):
                    file = codecs.getwriter("latin-1")(file)
                print_figure_impl(file)

    def _print_figure_tex(
            self, fmt, outfile, *,
            dpi, dsc_comments, orientation, papertype,
            bbox_inches_restore=None):
        """
        If :rc:`text.usetex` is True, a temporary pair of tex/eps files
        are created to allow tex to manage the text layout via the PSFrags
        package. These files are processed to yield the final ps or eps file.

        The rest of the behavior is as for `._print_figure`.
        """
        is_eps = fmt == 'eps'

        width, height = self.figure.get_size_inches()
        xo = 0
        yo = 0

        llx = xo
        lly = yo
        urx = llx + self.figure.bbox.width
        ury = lly + self.figure.bbox.height
        bbox = (llx, lly, urx, ury)

        self._pswriter = StringIO()

        # mixed mode rendering
        ps_renderer = RendererPS(width, height, self._pswriter, imagedpi=dpi)
        renderer = MixedModeRenderer(self.figure,
                                     width, height, dpi, ps_renderer,
                                     bbox_inches_restore=bbox_inches_restore)

        self.figure.draw(renderer)

        # write to a temp file, we'll move it to outfile when done
        with TemporaryDirectory() as tmpdir:
            tmppath = pathlib.Path(tmpdir, "tmp.ps")
            tmppath.write_text(
                f"""\
%!PS-Adobe-3.0 EPSF-3.0
%%LanguageLevel: 3
{dsc_comments}
{_get_bbox_header(bbox)}
%%EndComments
%%BeginProlog
/mpldict {len(_psDefs)} dict def
mpldict begin
{"".join(_psDefs)}
end
%%EndProlog
mpldict begin
{_nums_to_str(xo, yo)} translate
0 0 {_nums_to_str(width*72, height*72)} rectclip
{self._pswriter.getvalue()}
end
showpage
""",
                encoding="latin-1")

            if orientation is _Orientation.landscape:  # now, ready to rotate
                width, height = height, width
                bbox = (lly, llx, ury, urx)

            # set the paper size to the figure size if is_eps. The
            # resulting ps file has the given size with correct bounding
            # box so that there is no need to call 'pstoeps'
            if is_eps or papertype == 'figure':
                paper_width, paper_height = orientation.swap_if_landscape(
                    self.figure.get_size_inches())
            else:
                paper_width, paper_height = papersize[papertype]

            psfrag_rotated = _convert_psfrags(
                tmppath, ps_renderer.psfrag, paper_width, paper_height,
                orientation.name)

            if (mpl.rcParams['ps.usedistiller'] == 'ghostscript'
                    or mpl.rcParams['text.usetex']):
                _try_distill(gs_distill,
                             tmppath, is_eps, ptype=papertype, bbox=bbox,
                             rotated=psfrag_rotated)
            elif mpl.rcParams['ps.usedistiller'] == 'xpdf':
                _try_distill(xpdf_distill,
                             tmppath, is_eps, ptype=papertype, bbox=bbox,
                             rotated=psfrag_rotated)

            _move_path_to_path_or_stream(tmppath, outfile)

    print_ps = functools.partialmethod(_print_ps, "ps")
    print_eps = functools.partialmethod(_print_ps, "eps")

    def draw(self):
        self.figure.draw_without_rendering()
        return super().draw()


def _convert_psfrags(tmppath, psfrags, paper_width, paper_height, orientation):
    """
    When we want to use the LaTeX backend with postscript, we write PSFrag tags
    to a temporary postscript file, each one marking a position for LaTeX to
    render some text. convert_psfrags generates a LaTeX document containing the
    commands to convert those tags to text. LaTeX/dvips produces the postscript
    file that includes the actual text.
    """
    with mpl.rc_context({
            "text.latex.preamble":
            mpl.rcParams["text.latex.preamble"] +
            mpl.texmanager._usepackage_if_not_loaded("color") +
            mpl.texmanager._usepackage_if_not_loaded("graphicx") +
            mpl.texmanager._usepackage_if_not_loaded("psfrag") +
            r"\geometry{papersize={%(width)sin,%(height)sin},margin=0in}"
            % {"width": paper_width, "height": paper_height}
    }):
        dvifile = TexManager().make_dvi(
            "\n"
            r"\begin{figure}""\n"
            r"  \centering\leavevmode""\n"
            r"  %(psfrags)s""\n"
            r"  \includegraphics*[angle=%(angle)s]{%(epsfile)s}""\n"
            r"\end{figure}"
            % {
                "psfrags": "\n".join(psfrags),
                "angle": 90 if orientation == 'landscape' else 0,
                "epsfile": tmppath.resolve().as_posix(),
            },
            fontsize=10)  # tex's default fontsize.

    with TemporaryDirectory() as tmpdir:
        psfile = os.path.join(tmpdir, "tmp.ps")
        cbook._check_and_log_subprocess(
            ['dvips', '-q', '-R0', '-o', psfile, dvifile], _log)
        shutil.move(psfile, tmppath)

    # check if the dvips created a ps in landscape paper.  Somehow,
    # above latex+dvips results in a ps file in a landscape mode for a
    # certain figure sizes (e.g., 8.3in, 5.8in which is a5). And the
    # bounding box of the final output got messed up. We check see if
    # the generated ps file is in landscape and return this
    # information. The return value is used in pstoeps step to recover
    # the correct bounding box. 2010-06-05 JJL
    with open(tmppath) as fh:
        psfrag_rotated = "Landscape" in fh.read(1000)
    return psfrag_rotated


def _try_distill(func, tmppath, *args, **kwargs):
    try:
        func(str(tmppath), *args, **kwargs)
    except mpl.ExecutableNotFoundError as exc:
        _log.warning("%s.  Distillation step skipped.", exc)


def gs_distill(tmpfile, eps=False, ptype='letter', bbox=None, rotated=False):
    """
    Use ghostscript's pswrite or epswrite device to distill a file.
    This yields smaller files without illegal encapsulated postscript
    operators. The output is low-level, converting text to outlines.
    """

    if eps:
        paper_option = ["-dEPSCrop"]
    elif ptype == "figure":
        # The bbox will have its lower-left corner at (0, 0), so upper-right
        # corner corresponds with paper size.
        paper_option = [f"-dDEVICEWIDTHPOINTS={bbox[2]}",
                        f"-dDEVICEHEIGHTPOINTS={bbox[3]}"]
    else:
        paper_option = [f"-sPAPERSIZE={ptype}"]

    psfile = tmpfile + '.ps'
    dpi = mpl.rcParams['ps.distiller.res']

    cbook._check_and_log_subprocess(
        [mpl._get_executable_info("gs").executable,
         "-dBATCH", "-dNOPAUSE", "-r%d" % dpi, "-sDEVICE=ps2write",
         *paper_option, f"-sOutputFile={psfile}", tmpfile],
        _log)

    os.remove(tmpfile)
    shutil.move(psfile, tmpfile)

    # While it is best if above steps preserve the original bounding
    # box, there seem to be cases when it is not. For those cases,
    # the original bbox can be restored during the pstoeps step.

    if eps:
        # For some versions of gs, above steps result in a ps file where the
        # original bbox is no more correct. Do not adjust bbox for now.
        pstoeps(tmpfile, bbox, rotated=rotated)


def xpdf_distill(tmpfile, eps=False, ptype='letter', bbox=None, rotated=False):
    """
    Use ghostscript's ps2pdf and xpdf's/poppler's pdftops to distill a file.
    This yields smaller files without illegal encapsulated postscript
    operators. This distiller is preferred, generating high-level postscript
    output that treats text as text.
    """
    mpl._get_executable_info("gs")  # Effectively checks for ps2pdf.
    mpl._get_executable_info("pdftops")

    if eps:
        paper_option = ["-dEPSCrop"]
    elif ptype == "figure":
        # The bbox will have its lower-left corner at (0, 0), so upper-right
        # corner corresponds with paper size.
        paper_option = [f"-dDEVICEWIDTHPOINTS#{bbox[2]}",
                        f"-dDEVICEHEIGHTPOINTS#{bbox[3]}"]
    else:
        paper_option = [f"-sPAPERSIZE#{ptype}"]

    with TemporaryDirectory() as tmpdir:
        tmppdf = pathlib.Path(tmpdir, "tmp.pdf")
        tmpps = pathlib.Path(tmpdir, "tmp.ps")
        # Pass options as `-foo#bar` instead of `-foo=bar` to keep Windows
        # happy (https://ghostscript.com/doc/9.56.1/Use.htm#MS_Windows).
        cbook._check_and_log_subprocess(
            ["ps2pdf",
             "-dAutoFilterColorImages#false",
             "-dAutoFilterGrayImages#false",
             "-sAutoRotatePages#None",
             "-sGrayImageFilter#FlateEncode",
             "-sColorImageFilter#FlateEncode",
             *paper_option,
             tmpfile, tmppdf], _log)
        cbook._check_and_log_subprocess(
            ["pdftops", "-paper", "match", "-level3", tmppdf, tmpps], _log)
        shutil.move(tmpps, tmpfile)
    if eps:
        pstoeps(tmpfile)


@_api.deprecated("3.9")
def get_bbox_header(lbrt, rotated=False):
    """
    Return a postscript header string for the given bbox lbrt=(l, b, r, t).
    Optionally, return rotate command.
    """
    return _get_bbox_header(lbrt), (_get_rotate_command(lbrt) if rotated else "")


def _get_bbox_header(lbrt):
    """Return a PostScript header string for bounding box *lbrt*=(l, b, r, t)."""
    l, b, r, t = lbrt
    return (f"%%BoundingBox: {int(l)} {int(b)} {math.ceil(r)} {math.ceil(t)}\n"
            f"%%HiResBoundingBox: {l:.6f} {b:.6f} {r:.6f} {t:.6f}")


def _get_rotate_command(lbrt):
    """Return a PostScript 90° rotation command for bounding box *lbrt*=(l, b, r, t)."""
    l, b, r, t = lbrt
    return f"{l+r:.2f} {0:.2f} translate\n90 rotate"


def pstoeps(tmpfile, bbox=None, rotated=False):
    """
    Convert the postscript to encapsulated postscript.  The bbox of
    the eps file will be replaced with the given *bbox* argument. If
    None, original bbox will be used.
    """

    epsfile = tmpfile + '.eps'
    with open(epsfile, 'wb') as epsh, open(tmpfile, 'rb') as tmph:
        write = epsh.write
        # Modify the header:
        for line in tmph:
            if line.startswith(b'%!PS'):
                write(b"%!PS-Adobe-3.0 EPSF-3.0\n")
                if bbox:
                    write(_get_bbox_header(bbox).encode('ascii') + b'\n')
            elif line.startswith(b'%%EndComments'):
                write(line)
                write(b'%%BeginProlog\n'
                      b'save\n'
                      b'countdictstack\n'
                      b'mark\n'
                      b'newpath\n'
                      b'/showpage {} def\n'
                      b'/setpagedevice {pop} def\n'
                      b'%%EndProlog\n'
                      b'%%Page 1 1\n')
                if rotated:  # The output eps file need to be rotated.
                    write(_get_rotate_command(bbox).encode('ascii') + b'\n')
                break
            elif bbox and line.startswith((b'%%Bound', b'%%HiResBound',
                                           b'%%DocumentMedia', b'%%Pages')):
                pass
            else:
                write(line)
        # Now rewrite the rest of the file, and modify the trailer.
        # This is done in a second loop such that the header of the embedded
        # eps file is not modified.
        for line in tmph:
            if line.startswith(b'%%EOF'):
                write(b'cleartomark\n'
                      b'countdictstack\n'
                      b'exch sub { end } repeat\n'
                      b'restore\n'
                      b'showpage\n'
                      b'%%EOF\n')
            elif line.startswith(b'%%PageBoundingBox'):
                pass
            else:
                write(line)

    os.remove(tmpfile)
    shutil.move(epsfile, tmpfile)


FigureManagerPS = FigureManagerBase


# The following Python dictionary psDefs contains the entries for the
# PostScript dictionary mpldict.  This dictionary implements most of
# the matplotlib primitives and some abbreviations.
#
# References:
# https://www.adobe.com/content/dam/acom/en/devnet/actionscript/articles/PLRM.pdf
# http://preserve.mactech.com/articles/mactech/Vol.09/09.04/PostscriptTutorial
# http://www.math.ubc.ca/people/faculty/cass/graphics/text/www/
#

# The usage comments use the notation of the operator summary
# in the PostScript Language reference manual.
_psDefs = [
    # name proc  *_d*  -
    # Note that this cannot be bound to /d, because when embedding a Type3 font
    # we may want to define a "d" glyph using "/d{...} d" which would locally
    # overwrite the definition.
    "/_d { bind def } bind def",
    # x y  *m*  -
    "/m { moveto } _d",
    # x y  *l*  -
    "/l { lineto } _d",
    # x y  *r*  -
    "/r { rlineto } _d",
    # x1 y1 x2 y2 x y *c*  -
    "/c { curveto } _d",
    # *cl*  -
    "/cl { closepath } _d",
    # *ce*  -
    "/ce { closepath eofill } _d",
    # wx wy llx lly urx ury  *setcachedevice*  -
    "/sc { setcachedevice } _d",
]


@_Backend.export
class _BackendPS(_Backend):
    backend_version = 'Level II'
    FigureCanvas = FigureCanvasPS

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\repository.py ===
import atexit
import os
import re
import subprocess
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Tuple, TypedDict, Union
from urllib.parse import urlparse

from huggingface_hub import constants
from huggingface_hub.repocard import metadata_load, metadata_save

from .hf_api import HfApi, repo_type_and_id_from_hf_id
from .lfs import LFS_MULTIPART_UPLOAD_COMMAND
from .utils import (
    SoftTemporaryDirectory,
    get_token,
    logging,
    run_subprocess,
    tqdm,
    validate_hf_hub_args,
)
from .utils._deprecation import _deprecate_method


logger = logging.get_logger(__name__)


class CommandInProgress:
    """
    Utility to follow commands launched asynchronously.
    """

    def __init__(
        self,
        title: str,
        is_done_method: Callable,
        status_method: Callable,
        process: subprocess.Popen,
        post_method: Optional[Callable] = None,
    ):
        self.title = title
        self._is_done = is_done_method
        self._status = status_method
        self._process = process
        self._stderr = ""
        self._stdout = ""
        self._post_method = post_method

    @property
    def is_done(self) -> bool:
        """
        Whether the process is done.
        """
        result = self._is_done()

        if result and self._post_method is not None:
            self._post_method()
            self._post_method = None

        return result

    @property
    def status(self) -> int:
        """
        The exit code/status of the current action. Will return `0` if the
        command has completed successfully, and a number between 1 and 255 if
        the process errored-out.

        Will return -1 if the command is still ongoing.
        """
        return self._status()

    @property
    def failed(self) -> bool:
        """
        Whether the process errored-out.
        """
        return self.status > 0

    @property
    def stderr(self) -> str:
        """
        The current output message on the standard error.
        """
        if self._process.stderr is not None:
            self._stderr += self._process.stderr.read()
        return self._stderr

    @property
    def stdout(self) -> str:
        """
        The current output message on the standard output.
        """
        if self._process.stdout is not None:
            self._stdout += self._process.stdout.read()
        return self._stdout

    def __repr__(self):
        status = self.status

        if status == -1:
            status = "running"

        return (
            f"[{self.title} command, status code: {status},"
            f" {'in progress.' if not self.is_done else 'finished.'} PID:"
            f" {self._process.pid}]"
        )


def is_git_repo(folder: Union[str, Path]) -> bool:
    """
    Check if the folder is the root or part of a git repository

    Args:
        folder (`str`):
            The folder in which to run the command.

    Returns:
        `bool`: `True` if the repository is part of a repository, `False`
        otherwise.
    """
    folder_exists = os.path.exists(os.path.join(folder, ".git"))
    git_branch = subprocess.run("git branch".split(), cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return folder_exists and git_branch.returncode == 0


def is_local_clone(folder: Union[str, Path], remote_url: str) -> bool:
    """
    Check if the folder is a local clone of the remote_url

    Args:
        folder (`str` or `Path`):
            The folder in which to run the command.
        remote_url (`str`):
            The url of a git repository.

    Returns:
        `bool`: `True` if the repository is a local clone of the remote
        repository specified, `False` otherwise.
    """
    if not is_git_repo(folder):
        return False

    remotes = run_subprocess("git remote -v", folder).stdout

    # Remove token for the test with remotes.
    remote_url = re.sub(r"https://.*@", "https://", remote_url)
    remotes = [re.sub(r"https://.*@", "https://", remote) for remote in remotes.split()]
    return remote_url in remotes


def is_tracked_with_lfs(filename: Union[str, Path]) -> bool:
    """
    Check if the file passed is tracked with git-lfs.

    Args:
        filename (`str` or `Path`):
            The filename to check.

    Returns:
        `bool`: `True` if the file passed is tracked with git-lfs, `False`
        otherwise.
    """
    folder = Path(filename).parent
    filename = Path(filename).name

    try:
        p = run_subprocess("git check-attr -a".split() + [filename], folder)
        attributes = p.stdout.strip()
    except subprocess.CalledProcessError as exc:
        if not is_git_repo(folder):
            return False
        else:
            raise OSError(exc.stderr)

    if len(attributes) == 0:
        return False

    found_lfs_tag = {"diff": False, "merge": False, "filter": False}

    for attribute in attributes.split("\n"):
        for tag in found_lfs_tag.keys():
            if tag in attribute and "lfs" in attribute:
                found_lfs_tag[tag] = True

    return all(found_lfs_tag.values())


def is_git_ignored(filename: Union[str, Path]) -> bool:
    """
    Check if file is git-ignored. Supports nested .gitignore files.

    Args:
        filename (`str` or `Path`):
            The filename to check.

    Returns:
        `bool`: `True` if the file passed is ignored by `git`, `False`
        otherwise.
    """
    folder = Path(filename).parent
    filename = Path(filename).name

    try:
        p = run_subprocess("git check-ignore".split() + [filename], folder, check=False)
        # Will return exit code 1 if not gitignored
        is_ignored = not bool(p.returncode)
    except subprocess.CalledProcessError as exc:
        raise OSError(exc.stderr)

    return is_ignored


def is_binary_file(filename: Union[str, Path]) -> bool:
    """
    Check if file is a binary file.

    Args:
        filename (`str` or `Path`):
            The filename to check.

    Returns:
        `bool`: `True` if the file passed is a binary file, `False` otherwise.
    """
    try:
        with open(filename, "rb") as f:
            content = f.read(10 * (1024**2))  # Read a maximum of 10MB

        # Code sample taken from the following stack overflow thread
        # https://stackoverflow.com/questions/898669/how-can-i-detect-if-a-file-is-binary-non-text-in-python/7392391#7392391
        text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F})
        return bool(content.translate(None, text_chars))
    except UnicodeDecodeError:
        return True


def files_to_be_staged(pattern: str = ".", folder: Union[str, Path, None] = None) -> List[str]:
    """
    Returns a list of filenames that are to be staged.

    Args:
        pattern (`str` or `Path`):
            The pattern of filenames to check. Put `.` to get all files.
        folder (`str` or `Path`):
            The folder in which to run the command.

    Returns:
        `List[str]`: List of files that are to be staged.
    """
    try:
        p = run_subprocess("git ls-files --exclude-standard -mo".split() + [pattern], folder)
        if len(p.stdout.strip()):
            files = p.stdout.strip().split("\n")
        else:
            files = []
    except subprocess.CalledProcessError as exc:
        raise EnvironmentError(exc.stderr)

    return files


def is_tracked_upstream(folder: Union[str, Path]) -> bool:
    """
    Check if the current checked-out branch is tracked upstream.

    Args:
        folder (`str` or `Path`):
            The folder in which to run the command.

    Returns:
        `bool`: `True` if the current checked-out branch is tracked upstream,
        `False` otherwise.
    """
    try:
        run_subprocess("git rev-parse --symbolic-full-name --abbrev-ref @{u}", folder)
        return True
    except subprocess.CalledProcessError as exc:
        if "HEAD" in exc.stderr:
            raise OSError("No branch checked out")

        return False


def commits_to_push(folder: Union[str, Path], upstream: Optional[str] = None) -> int:
    """
        Check the number of commits that would be pushed upstream

        Args:
            folder (`str` or `Path`):
                The folder in which to run the command.
            upstream (`str`, *optional*):
    The name of the upstream repository with which the comparison should be
    made.

        Returns:
            `int`: Number of commits that would be pushed upstream were a `git
            push` to proceed.
    """
    try:
        result = run_subprocess(f"git cherry -v {upstream or ''}", folder)
        return len(result.stdout.split("\n")) - 1
    except subprocess.CalledProcessError as exc:
        raise EnvironmentError(exc.stderr)


class PbarT(TypedDict):
    # Used to store an opened progress bar in `_lfs_log_progress`
    bar: tqdm
    past_bytes: int


@contextmanager
def _lfs_log_progress():
    """
    This is a context manager that will log the Git LFS progress of cleaning,
    smudging, pulling and pushing.
    """

    if logger.getEffectiveLevel() >= logging.ERROR:
        try:
            yield
        except Exception:
            pass
        return

    def output_progress(stopping_event: threading.Event):
        """
        To be launched as a separate thread with an event meaning it should stop
        the tail.
        """
        # Key is tuple(state, filename), value is a dict(tqdm bar and a previous value)
        pbars: Dict[Tuple[str, str], PbarT] = {}

        def close_pbars():
            for pbar in pbars.values():
                pbar["bar"].update(pbar["bar"].total - pbar["past_bytes"])
                pbar["bar"].refresh()
                pbar["bar"].close()

        def tail_file(filename) -> Iterator[str]:
            """
            Creates a generator to be iterated through, which will return each
            line one by one. Will stop tailing the file if the stopping_event is
            set.
            """
            with open(filename, "r") as file:
                current_line = ""
                while True:
                    if stopping_event.is_set():
                        close_pbars()
                        break

                    line_bit = file.readline()
                    if line_bit is not None and not len(line_bit.strip()) == 0:
                        current_line += line_bit
                        if current_line.endswith("\n"):
                            yield current_line
                            current_line = ""
                    else:
                        time.sleep(1)

        # If the file isn't created yet, wait for a few seconds before trying again.
        # Can be interrupted with the stopping_event.
        while not os.path.exists(os.environ["GIT_LFS_PROGRESS"]):
            if stopping_event.is_set():
                close_pbars()
                return

            time.sleep(2)

        for line in tail_file(os.environ["GIT_LFS_PROGRESS"]):
            try:
                state, file_progress, byte_progress, filename = line.split()
            except ValueError as error:
                # Try/except to ease debugging. See https://github.com/huggingface/huggingface_hub/issues/1373.
                raise ValueError(f"Cannot unpack LFS progress line:\n{line}") from error
            description = f"{state.capitalize()} file {filename}"

            current_bytes, total_bytes = byte_progress.split("/")
            current_bytes_int = int(current_bytes)
            total_bytes_int = int(total_bytes)

            pbar = pbars.get((state, filename))
            if pbar is None:
                # Initialize progress bar
                pbars[(state, filename)] = {
                    "bar": tqdm(
                        desc=description,
                        initial=current_bytes_int,
                        total=total_bytes_int,
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                        name="huggingface_hub.lfs_upload",
                    ),
                    "past_bytes": int(current_bytes),
                }
            else:
                # Update progress bar
                pbar["bar"].update(current_bytes_int - pbar["past_bytes"])
                pbar["past_bytes"] = current_bytes_int

    current_lfs_progress_value = os.environ.get("GIT_LFS_PROGRESS", "")

    with SoftTemporaryDirectory() as tmpdir:
        os.environ["GIT_LFS_PROGRESS"] = os.path.join(tmpdir, "lfs_progress")
        logger.debug(f"Following progress in {os.environ['GIT_LFS_PROGRESS']}")

        exit_event = threading.Event()
        x = threading.Thread(target=output_progress, args=(exit_event,), daemon=True)
        x.start()

        try:
            yield
        finally:
            exit_event.set()
            x.join()

            os.environ["GIT_LFS_PROGRESS"] = current_lfs_progress_value


class Repository:
    """
    Helper class to wrap the git and git-lfs commands.

    The aim is to facilitate interacting with huggingface.co hosted model or
    dataset repos, though not a lot here (if any) is actually specific to
    huggingface.co.

    <Tip warning={true}>

    [`Repository`] is deprecated in favor of the http-based alternatives implemented in
    [`HfApi`]. Given its large adoption in legacy code, the complete removal of
    [`Repository`] will only happen in release `v1.0`. For more details, please read
    https://huggingface.co/docs/huggingface_hub/concepts/git_vs_http.

    </Tip>
    """

    command_queue: List[CommandInProgress]

    @validate_hf_hub_args
    @_deprecate_method(
        version="1.0",
        message=(
            "Please prefer the http-based alternatives instead. Given its large adoption in legacy code, the complete"
            " removal is only planned on next major release.\nFor more details, please read"
            " https://huggingface.co/docs/huggingface_hub/concepts/git_vs_http."
        ),
    )
    def __init__(
        self,
        local_dir: Union[str, Path],
        clone_from: Optional[str] = None,
        repo_type: Optional[str] = None,
        token: Union[bool, str] = True,
        git_user: Optional[str] = None,
        git_email: Optional[str] = None,
        revision: Optional[str] = None,
        skip_lfs_files: bool = False,
        client: Optional[HfApi] = None,
    ):
        """
        Instantiate a local clone of a git repo.

        If `clone_from` is set, the repo will be cloned from an existing remote repository.
        If the remote repo does not exist, a `EnvironmentError` exception will be thrown.
        Please create the remote repo first using [`create_repo`].

        `Repository` uses the local git credentials by default. If explicitly set, the `token`
        or the `git_user`/`git_email` pair will be used instead.

        Args:
            local_dir (`str` or `Path`):
                path (e.g. `'my_trained_model/'`) to the local directory, where
                the `Repository` will be initialized.
            clone_from (`str`, *optional*):
                Either a repository url or `repo_id`.
                Example:
                - `"https://huggingface.co/philschmid/playground-tests"`
                - `"philschmid/playground-tests"`
            repo_type (`str`, *optional*):
                To set when cloning a repo from a repo_id. Default is model.
            token (`bool` or `str`, *optional*):
                A valid authentication token (see https://huggingface.co/settings/token).
                If `None` or `True` and machine is logged in (through `huggingface-cli login`
                or [`~huggingface_hub.login`]), token will be retrieved from the cache.
                If `False`, token is not sent in the request header.
            git_user (`str`, *optional*):
                will override the `git config user.name` for committing and
                pushing files to the hub.
            git_email (`str`, *optional*):
                will override the `git config user.email` for committing and
                pushing files to the hub.
            revision (`str`, *optional*):
                Revision to checkout after initializing the repository. If the
                revision doesn't exist, a branch will be created with that
                revision name from the default branch's current HEAD.
            skip_lfs_files (`bool`, *optional*, defaults to `False`):
                whether to skip git-LFS files or not.
            client (`HfApi`, *optional*):
                Instance of [`HfApi`] to use when calling the HF Hub API. A new
                instance will be created if this is left to `None`.

        Raises:
            [`EnvironmentError`](https://docs.python.org/3/library/exceptions.html#EnvironmentError)
                If the remote repository set in `clone_from` does not exist.
        """
        if isinstance(local_dir, Path):
            local_dir = str(local_dir)
        os.makedirs(local_dir, exist_ok=True)
        self.local_dir = os.path.join(os.getcwd(), local_dir)
        self._repo_type = repo_type
        self.command_queue = []
        self.skip_lfs_files = skip_lfs_files
        self.client = client if client is not None else HfApi()

        self.check_git_versions()

        if isinstance(token, str):
            self.huggingface_token: Optional[str] = token
        elif token is False:
            self.huggingface_token = None
        else:
            # if `True` -> explicit use of the cached token
            # if `None` -> implicit use of the cached token
            self.huggingface_token = get_token()

        if clone_from is not None:
            self.clone_from(repo_url=clone_from)
        else:
            if is_git_repo(self.local_dir):
                logger.debug("[Repository] is a valid git repo")
            else:
                raise ValueError("If not specifying `clone_from`, you need to pass Repository a valid git clone.")

        if self.huggingface_token is not None and (git_email is None or git_user is None):
            user = self.client.whoami(self.huggingface_token)

            if git_email is None:
                git_email = user.get("email")

            if git_user is None:
                git_user = user.get("fullname")

        if git_user is not None or git_email is not None:
            self.git_config_username_and_email(git_user, git_email)

        self.lfs_enable_largefiles()
        self.git_credential_helper_store()

        if revision is not None:
            self.git_checkout(revision, create_branch_ok=True)

        # This ensures that all commands exit before exiting the Python runtime.
        # This will ensure all pushes register on the hub, even if other errors happen in subsequent operations.
        atexit.register(self.wait_for_commands)

    @property
    def current_branch(self) -> str:
        """
        Returns the current checked out branch.

        Returns:
            `str`: Current checked out branch.
        """
        try:
            result = run_subprocess("git rev-parse --abbrev-ref HEAD", self.local_dir).stdout.strip()
        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

        return result

    def check_git_versions(self):
        """
        Checks that `git` and `git-lfs` can be run.

        Raises:
            [`EnvironmentError`](https://docs.python.org/3/library/exceptions.html#EnvironmentError)
                If `git` or `git-lfs` are not installed.
        """
        try:
            git_version = run_subprocess("git --version", self.local_dir).stdout.strip()
        except FileNotFoundError:
            raise EnvironmentError("Looks like you do not have git installed, please install.")

        try:
            lfs_version = run_subprocess("git-lfs --version", self.local_dir).stdout.strip()
        except FileNotFoundError:
            raise EnvironmentError(
                "Looks like you do not have git-lfs installed, please install."
                " You can install from https://git-lfs.github.com/."
                " Then run `git lfs install` (you only have to do this once)."
            )
        logger.info(git_version + "\n" + lfs_version)

    @validate_hf_hub_args
    def clone_from(self, repo_url: str, token: Union[bool, str, None] = None):
        """
        Clone from a remote. If the folder already exists, will try to clone the
        repository within it.

        If this folder is a git repository with linked history, will try to
        update the repository.

        Args:
            repo_url (`str`):
                The URL from which to clone the repository
            token (`Union[str, bool]`, *optional*):
                Whether to use the authentication token. It can be:
                 - a string which is the token itself
                 - `False`, which would not use the authentication token
                 - `True`, which would fetch the authentication token from the
                   local folder and use it (you should be logged in for this to
                   work).
                - `None`, which would retrieve the value of
                  `self.huggingface_token`.

        <Tip>

        Raises the following error:

            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              if an organization token (starts with "api_org") is passed. Use must use
              your own personal access token (see https://hf.co/settings/tokens).

            - [`EnvironmentError`](https://docs.python.org/3/library/exceptions.html#EnvironmentError)
              if you are trying to clone the repository in a non-empty folder, or if the
              `git` operations raise errors.

        </Tip>
        """
        token = (
            token  # str -> use it
            if isinstance(token, str)
            else (
                None  # `False` -> explicit no token
                if token is False
                else self.huggingface_token  # `None` or `True` -> use default
            )
        )
        if token is not None and token.startswith("api_org"):
            raise ValueError(
                "You must use your personal access token, not an Organization token"
                " (see https://hf.co/settings/tokens)."
            )

        hub_url = self.client.endpoint
        if hub_url in repo_url or ("http" not in repo_url and len(repo_url.split("/")) <= 2):
            repo_type, namespace, repo_name = repo_type_and_id_from_hf_id(repo_url, hub_url=hub_url)
            repo_id = f"{namespace}/{repo_name}" if namespace is not None else repo_name

            if repo_type is not None:
                self._repo_type = repo_type

            repo_url = hub_url + "/"

            if self._repo_type in constants.REPO_TYPES_URL_PREFIXES:
                repo_url += constants.REPO_TYPES_URL_PREFIXES[self._repo_type]

            if token is not None:
                # Add token in git url when provided
                scheme = urlparse(repo_url).scheme
                repo_url = repo_url.replace(f"{scheme}://", f"{scheme}://user:{token}@")

            repo_url += repo_id

        # For error messages, it's cleaner to show the repo url without the token.
        clean_repo_url = re.sub(r"(https?)://.*@", r"\1://", repo_url)
        try:
            run_subprocess("git lfs install", self.local_dir)

            # checks if repository is initialized in a empty repository or in one with files
            if len(os.listdir(self.local_dir)) == 0:
                logger.warning(f"Cloning {clean_repo_url} into local empty directory.")

                with _lfs_log_progress():
                    env = os.environ.copy()

                    if self.skip_lfs_files:
                        env.update({"GIT_LFS_SKIP_SMUDGE": "1"})

                    run_subprocess(
                        # 'git lfs clone' is deprecated (will display a warning in the terminal)
                        # but we still use it as it provides a nicer UX when downloading large
                        # files (shows progress).
                        f"{'git clone' if self.skip_lfs_files else 'git lfs clone'} {repo_url} .",
                        self.local_dir,
                        env=env,
                    )
            else:
                # Check if the folder is the root of a git repository
                if not is_git_repo(self.local_dir):
                    raise EnvironmentError(
                        "Tried to clone a repository in a non-empty folder that isn't"
                        f" a git repository ('{self.local_dir}'). If you really want to"
                        f" do this, do it manually:\n cd {self.local_dir} && git init"
                        " && git remote add origin && git pull origin main\n or clone"
                        " repo to a new folder and move your existing files there"
                        " afterwards."
                    )

                if is_local_clone(self.local_dir, repo_url):
                    logger.warning(
                        f"{self.local_dir} is already a clone of {clean_repo_url}."
                        " Make sure you pull the latest changes with"
                        " `repo.git_pull()`."
                    )
                else:
                    output = run_subprocess("git remote get-url origin", self.local_dir, check=False)

                    error_msg = (
                        f"Tried to clone {clean_repo_url} in an unrelated git"
                        " repository.\nIf you believe this is an error, please add"
                        f" a remote with the following URL: {clean_repo_url}."
                    )
                    if output.returncode == 0:
                        clean_local_remote_url = re.sub(r"https://.*@", "https://", output.stdout)
                        error_msg += f"\nLocal path has its origin defined as: {clean_local_remote_url}"
                    raise EnvironmentError(error_msg)

        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

    def git_config_username_and_email(self, git_user: Optional[str] = None, git_email: Optional[str] = None):
        """
        Sets git username and email (only in the current repo).

        Args:
            git_user (`str`, *optional*):
                The username to register through `git`.
            git_email (`str`, *optional*):
                The email to register through `git`.
        """
        try:
            if git_user is not None:
                run_subprocess("git config user.name".split() + [git_user], self.local_dir)

            if git_email is not None:
                run_subprocess(f"git config user.email {git_email}".split(), self.local_dir)
        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

    def git_credential_helper_store(self):
        """
        Sets the git credential helper to `store`
        """
        try:
            run_subprocess("git config credential.helper store", self.local_dir)
        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

    def git_head_hash(self) -> str:
        """
        Get commit sha on top of HEAD.

        Returns:
            `str`: The current checked out commit SHA.
        """
        try:
            p = run_subprocess("git rev-parse HEAD", self.local_dir)
            return p.stdout.strip()
        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

    def git_remote_url(self) -> str:
        """
        Get URL to origin remote.

        Returns:
            `str`: The URL of the `origin` remote.
        """
        try:
            p = run_subprocess("git config --get remote.origin.url", self.local_dir)
            url = p.stdout.strip()
            # Strip basic auth info.
            return re.sub(r"https://.*@", "https://", url)
        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

    def git_head_commit_url(self) -> str:
        """
        Get URL to last commit on HEAD. We assume it's been pushed, and the url
        scheme is the same one as for GitHub or HuggingFace.

        Returns:
            `str`: The URL to the current checked-out commit.
        """
        sha = self.git_head_hash()
        url = self.git_remote_url()
        if url.endswith("/"):
            url = url[:-1]
        return f"{url}/commit/{sha}"

    def list_deleted_files(self) -> List[str]:
        """
        Returns a list of the files that are deleted in the working directory or
        index.

        Returns:
            `List[str]`: A list of files that have been deleted in the working
            directory or index.
        """
        try:
            git_status = run_subprocess("git status -s", self.local_dir).stdout.strip()
        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

        if len(git_status) == 0:
            return []

        # Receives a status like the following
        #  D .gitignore
        #  D new_file.json
        # AD new_file1.json
        # ?? new_file2.json
        # ?? new_file4.json

        # Strip each line of whitespaces
        modified_files_statuses = [status.strip() for status in git_status.split("\n")]

        # Only keep files that are deleted using the D prefix
        deleted_files_statuses = [status for status in modified_files_statuses if "D" in status.split()[0]]

        # Remove the D prefix and strip to keep only the relevant filename
        deleted_files = [status.split()[-1].strip() for status in deleted_files_statuses]

        return deleted_files

    def lfs_track(self, patterns: Union[str, List[str]], filename: bool = False):
        """
        Tell git-lfs to track files according to a pattern.

        Setting the `filename` argument to `True` will treat the arguments as
        literal filenames, not as patterns. Any special glob characters in the
        filename will be escaped when writing to the `.gitattributes` file.

        Args:
            patterns (`Union[str, List[str]]`):
                The pattern, or list of patterns, to track with git-lfs.
            filename (`bool`, *optional*, defaults to `False`):
                Whether to use the patterns as literal filenames.
        """
        if isinstance(patterns, str):
            patterns = [patterns]
        try:
            for pattern in patterns:
                run_subprocess(
                    f"git lfs track {'--filename' if filename else ''} {pattern}",
                    self.local_dir,
                )
        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

    def lfs_untrack(self, patterns: Union[str, List[str]]):
        """
        Tell git-lfs to untrack those files.

        Args:
            patterns (`Union[str, List[str]]`):
                The pattern, or list of patterns, to untrack with git-lfs.
        """
        if isinstance(patterns, str):
            patterns = [patterns]
        try:
            for pattern in patterns:
                run_subprocess("git lfs untrack".split() + [pattern], self.local_dir)
        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

    def lfs_enable_largefiles(self):
        """
        HF-specific. This enables upload support of files >5GB.
        """
        try:
            lfs_config = "git config lfs.customtransfer.multipart"
            run_subprocess(f"{lfs_config}.path huggingface-cli", self.local_dir)
            run_subprocess(
                f"{lfs_config}.args {LFS_MULTIPART_UPLOAD_COMMAND}",
                self.local_dir,
            )
        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

    def auto_track_binary_files(self, pattern: str = ".") -> List[str]:
        """
        Automatically track binary files with git-lfs.

        Args:
            pattern (`str`, *optional*, defaults to "."):
                The pattern with which to track files that are binary.

        Returns:
            `List[str]`: List of filenames that are now tracked due to being
            binary files
        """
        files_to_be_tracked_with_lfs = []

        deleted_files = self.list_deleted_files()

        for filename in files_to_be_staged(pattern, folder=self.local_dir):
            if filename in deleted_files:
                continue

            path_to_file = os.path.join(os.getcwd(), self.local_dir, filename)

            if not (is_tracked_with_lfs(path_to_file) or is_git_ignored(path_to_file)):
                size_in_mb = os.path.getsize(path_to_file) / (1024 * 1024)

                if size_in_mb >= 10:
                    logger.warning(
                        "Parsing a large file to check if binary or not. Tracking large"
                        " files using `repository.auto_track_large_files` is"
                        " recommended so as to not load the full file in memory."
                    )

                is_binary = is_binary_file(path_to_file)

                if is_binary:
                    self.lfs_track(filename)
                    files_to_be_tracked_with_lfs.append(filename)

        # Cleanup the .gitattributes if files were deleted
        self.lfs_untrack(deleted_files)

        return files_to_be_tracked_with_lfs

    def auto_track_large_files(self, pattern: str = ".") -> List[str]:
        """
        Automatically track large files (files that weigh more than 10MBs) with
        git-lfs.

        Args:
            pattern (`str`, *optional*, defaults to "."):
                The pattern with which to track files that are above 10MBs.

        Returns:
            `List[str]`: List of filenames that are now tracked due to their
            size.
        """
        files_to_be_tracked_with_lfs = []

        deleted_files = self.list_deleted_files()

        for filename in files_to_be_staged(pattern, folder=self.local_dir):
            if filename in deleted_files:
                continue

            path_to_file = os.path.join(os.getcwd(), self.local_dir, filename)
            size_in_mb = os.path.getsize(path_to_file) / (1024 * 1024)

            if size_in_mb >= 10 and not is_tracked_with_lfs(path_to_file) and not is_git_ignored(path_to_file):
                self.lfs_track(filename)
                files_to_be_tracked_with_lfs.append(filename)

        # Cleanup the .gitattributes if files were deleted
        self.lfs_untrack(deleted_files)

        return files_to_be_tracked_with_lfs

    def lfs_prune(self, recent=False):
        """
        git lfs prune

        Args:
            recent (`bool`, *optional*, defaults to `False`):
                Whether to prune files even if they were referenced by recent
                commits. See the following
                [link](https://github.com/git-lfs/git-lfs/blob/f3d43f0428a84fc4f1e5405b76b5a73ec2437e65/docs/man/git-lfs-prune.1.ronn#recent-files)
                for more information.
        """
        try:
            with _lfs_log_progress():
                result = run_subprocess(f"git lfs prune {'--recent' if recent else ''}", self.local_dir)
                logger.info(result.stdout)
        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

    def git_pull(self, rebase: bool = False, lfs: bool = False):
        """
        git pull

        Args:
            rebase (`bool`, *optional*, defaults to `False`):
                Whether to rebase the current branch on top of the upstream
                branch after fetching.
            lfs (`bool`, *optional*, defaults to `False`):
                Whether to fetch the LFS files too. This option only changes the
                behavior when a repository was cloned without fetching the LFS
                files; calling `repo.git_pull(lfs=True)` will then fetch the LFS
                file from the remote repository.
        """
        command = "git pull" if not lfs else "git lfs pull"
        if rebase:
            command += " --rebase"
        try:
            with _lfs_log_progress():
                result = run_subprocess(command, self.local_dir)
                logger.info(result.stdout)
        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

    def git_add(self, pattern: str = ".", auto_lfs_track: bool = False):
        """
        git add

        Setting the `auto_lfs_track` parameter to `True` will automatically
        track files that are larger than 10MB with `git-lfs`.

        Args:
            pattern (`str`, *optional*, defaults to "."):
                The pattern with which to add files to staging.
            auto_lfs_track (`bool`, *optional*, defaults to `False`):
                Whether to automatically track large and binary files with
                git-lfs. Any file over 10MB in size, or in binary format, will
                be automatically tracked.
        """
        if auto_lfs_track:
            # Track files according to their size (>=10MB)
            tracked_files = self.auto_track_large_files(pattern)

            # Read the remaining files and track them if they're binary
            tracked_files.extend(self.auto_track_binary_files(pattern))

            if tracked_files:
                logger.warning(
                    f"Adding files tracked by Git LFS: {tracked_files}. This may take a"
                    " bit of time if the files are large."
                )

        try:
            result = run_subprocess("git add -v".split() + [pattern], self.local_dir)
            logger.info(f"Adding to index:\n{result.stdout}\n")
        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

    def git_commit(self, commit_message: str = "commit files to HF hub"):
        """
        git commit

        Args:
            commit_message (`str`, *optional*, defaults to "commit files to HF hub"):
                The message attributed to the commit.
        """
        try:
            result = run_subprocess("git commit -v -m".split() + [commit_message], self.local_dir)
            logger.info(f"Committed:\n{result.stdout}\n")
        except subprocess.CalledProcessError as exc:
            if len(exc.stderr) > 0:
                raise EnvironmentError(exc.stderr)
            else:
                raise EnvironmentError(exc.stdout)

    def git_push(
        self,
        upstream: Optional[str] = None,
        blocking: bool = True,
        auto_lfs_prune: bool = False,
    ) -> Union[str, Tuple[str, CommandInProgress]]:
        """
        git push

        If used without setting `blocking`, will return url to commit on remote
        repo. If used with `blocking=True`, will return a tuple containing the
        url to commit and the command object to follow for information about the
        process.

        Args:
            upstream (`str`, *optional*):
                Upstream to which this should push. If not specified, will push
                to the lastly defined upstream or to the default one (`origin
                main`).
            blocking (`bool`, *optional*, defaults to `True`):
                Whether the function should return only when the push has
                finished. Setting this to `False` will return an
                `CommandInProgress` object which has an `is_done` property. This
                property will be set to `True` when the push is finished.
            auto_lfs_prune (`bool`, *optional*, defaults to `False`):
                Whether to automatically prune files once they have been pushed
                to the remote.
        """
        command = "git push"

        if upstream:
            command += f" --set-upstream {upstream}"

        number_of_commits = commits_to_push(self.local_dir, upstream)

        if number_of_commits > 1:
            logger.warning(f"Several commits ({number_of_commits}) will be pushed upstream.")
            if blocking:
                logger.warning("The progress bars may be unreliable.")

        try:
            with _lfs_log_progress():
                process = subprocess.Popen(
                    command.split(),
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    encoding="utf-8",
                    cwd=self.local_dir,
                )

                if blocking:
                    stdout, stderr = process.communicate()
                    return_code = process.poll()
                    process.kill()

                    if len(stderr):
                        logger.warning(stderr)

                    if return_code:
                        raise subprocess.CalledProcessError(return_code, process.args, output=stdout, stderr=stderr)

        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

        if not blocking:

            def status_method():
                status = process.poll()
                if status is None:
                    return -1
                else:
                    return status

            command_in_progress = CommandInProgress(
                "push",
                is_done_method=lambda: process.poll() is not None,
                status_method=status_method,
                process=process,
                post_method=self.lfs_prune if auto_lfs_prune else None,
            )

            self.command_queue.append(command_in_progress)

            return self.git_head_commit_url(), command_in_progress

        if auto_lfs_prune:
            self.lfs_prune()

        return self.git_head_commit_url()

    def git_checkout(self, revision: str, create_branch_ok: bool = False):
        """
        git checkout a given revision

        Specifying `create_branch_ok` to `True` will create the branch to the
        given revision if that revision doesn't exist.

        Args:
            revision (`str`):
                The revision to checkout.
            create_branch_ok (`str`, *optional*, defaults to `False`):
                Whether creating a branch named with the `revision` passed at
                the current checked-out reference if `revision` isn't an
                existing revision is allowed.
        """
        try:
            result = run_subprocess(f"git checkout {revision}", self.local_dir)
            logger.warning(f"Checked out {revision} from {self.current_branch}.")
            logger.warning(result.stdout)
        except subprocess.CalledProcessError as exc:
            if not create_branch_ok:
                raise EnvironmentError(exc.stderr)
            else:
                try:
                    result = run_subprocess(f"git checkout -b {revision}", self.local_dir)
                    logger.warning(
                        f"Revision `{revision}` does not exist. Created and checked out branch `{revision}`."
                    )
                    logger.warning(result.stdout)
                except subprocess.CalledProcessError as exc:
                    raise EnvironmentError(exc.stderr)

    def tag_exists(self, tag_name: str, remote: Optional[str] = None) -> bool:
        """
        Check if a tag exists or not.

        Args:
            tag_name (`str`):
                The name of the tag to check.
            remote (`str`, *optional*):
                Whether to check if the tag exists on a remote. This parameter
                should be the identifier of the remote.

        Returns:
            `bool`: Whether the tag exists.
        """
        if remote:
            try:
                result = run_subprocess(f"git ls-remote origin refs/tags/{tag_name}", self.local_dir).stdout.strip()
            except subprocess.CalledProcessError as exc:
                raise EnvironmentError(exc.stderr)

            return len(result) != 0
        else:
            try:
                git_tags = run_subprocess("git tag", self.local_dir).stdout.strip()
            except subprocess.CalledProcessError as exc:
                raise EnvironmentError(exc.stderr)

            git_tags = git_tags.split("\n")
            return tag_name in git_tags

    def delete_tag(self, tag_name: str, remote: Optional[str] = None) -> bool:
        """
        Delete a tag, both local and remote, if it exists

        Args:
            tag_name (`str`):
                The tag name to delete.
            remote (`str`, *optional*):
                The remote on which to delete the tag.

        Returns:
             `bool`: `True` if deleted, `False` if the tag didn't exist.
                If remote is not passed, will just be updated locally
        """
        delete_locally = True
        delete_remotely = True

        if not self.tag_exists(tag_name):
            delete_locally = False

        if not self.tag_exists(tag_name, remote=remote):
            delete_remotely = False

        if delete_locally:
            try:
                run_subprocess(["git", "tag", "-d", tag_name], self.local_dir).stdout.strip()
            except subprocess.CalledProcessError as exc:
                raise EnvironmentError(exc.stderr)

        if remote and delete_remotely:
            try:
                run_subprocess(f"git push {remote} --delete {tag_name}", self.local_dir).stdout.strip()
            except subprocess.CalledProcessError as exc:
                raise EnvironmentError(exc.stderr)

        return True

    def add_tag(self, tag_name: str, message: Optional[str] = None, remote: Optional[str] = None):
        """
        Add a tag at the current head and push it

        If remote is None, will just be updated locally

        If no message is provided, the tag will be lightweight. if a message is
        provided, the tag will be annotated.

        Args:
            tag_name (`str`):
                The name of the tag to be added.
            message (`str`, *optional*):
                The message that accompanies the tag. The tag will turn into an
                annotated tag if a message is passed.
            remote (`str`, *optional*):
                The remote on which to add the tag.
        """
        if message:
            tag_args = ["git", "tag", "-a", tag_name, "-m", message]
        else:
            tag_args = ["git", "tag", tag_name]

        try:
            run_subprocess(tag_args, self.local_dir).stdout.strip()
        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

        if remote:
            try:
                run_subprocess(f"git push {remote} {tag_name}", self.local_dir).stdout.strip()
            except subprocess.CalledProcessError as exc:
                raise EnvironmentError(exc.stderr)

    def is_repo_clean(self) -> bool:
        """
        Return whether or not the git status is clean or not

        Returns:
            `bool`: `True` if the git status is clean, `False` otherwise.
        """
        try:
            git_status = run_subprocess("git status --porcelain", self.local_dir).stdout.strip()
        except subprocess.CalledProcessError as exc:
            raise EnvironmentError(exc.stderr)

        return len(git_status) == 0

    def push_to_hub(
        self,
        commit_message: str = "commit files to HF hub",
        blocking: bool = True,
        clean_ok: bool = True,
        auto_lfs_prune: bool = False,
    ) -> Union[None, str, Tuple[str, CommandInProgress]]:
        """
        Helper to add, commit, and push files to remote repository on the
        HuggingFace Hub. Will automatically track large files (>10MB).

        Args:
            commit_message (`str`):
                Message to use for the commit.
            blocking (`bool`, *optional*, defaults to `True`):
                Whether the function should return only when the `git push` has
                finished.
            clean_ok (`bool`, *optional*, defaults to `True`):
                If True, this function will return None if the repo is
                untouched. Default behavior is to fail because the git command
                fails.
            auto_lfs_prune (`bool`, *optional*, defaults to `False`):
                Whether to automatically prune files once they have been pushed
                to the remote.
        """
        if clean_ok and self.is_repo_clean():
            logger.info("Repo currently clean. Ignoring push_to_hub")
            return None
        self.git_add(auto_lfs_track=True)
        self.git_commit(commit_message)
        return self.git_push(
            upstream=f"origin {self.current_branch}",
            blocking=blocking,
            auto_lfs_prune=auto_lfs_prune,
        )

    @contextmanager
    def commit(
        self,
        commit_message: str,
        branch: Optional[str] = None,
        track_large_files: bool = True,
        blocking: bool = True,
        auto_lfs_prune: bool = False,
    ):
        """
        Context manager utility to handle committing to a repository. This
        automatically tracks large files (>10Mb) with git-lfs. Set the
        `track_large_files` argument to `False` if you wish to ignore that
        behavior.

        Args:
            commit_message (`str`):
                Message to use for the commit.
            branch (`str`, *optional*):
                The branch on which the commit will appear. This branch will be
                checked-out before any operation.
            track_large_files (`bool`, *optional*, defaults to `True`):
                Whether to automatically track large files or not. Will do so by
                default.
            blocking (`bool`, *optional*, defaults to `True`):
                Whether the function should return only when the `git push` has
                finished.
            auto_lfs_prune (`bool`, defaults to `True`):
                Whether to automatically prune files once they have been pushed
                to the remote.

        Examples:

        ```python
        >>> with Repository(
        ...     "text-files",
        ...     clone_from="<user>/text-files",
        ...     token=True,
        >>> ).commit("My first file :)"):
        ...     with open("file.txt", "w+") as f:
        ...         f.write(json.dumps({"hey": 8}))

        >>> import torch

        >>> model = torch.nn.Transformer()
        >>> with Repository(
        ...     "torch-model",
        ...     clone_from="<user>/torch-model",
        ...     token=True,
        >>> ).commit("My cool model :)"):
        ...     torch.save(model.state_dict(), "model.pt")
        ```

        """

        files_to_stage = files_to_be_staged(".", folder=self.local_dir)

        if len(files_to_stage):
            files_in_msg = str(files_to_stage[:5])[:-1] + ", ...]" if len(files_to_stage) > 5 else str(files_to_stage)
            logger.error(
                "There exists some updated files in the local repository that are not"
                f" committed: {files_in_msg}. This may lead to errors if checking out"
                " a branch. These files and their modifications will be added to the"
                " current commit."
            )

        if branch is not None:
            self.git_checkout(branch, create_branch_ok=True)

        if is_tracked_upstream(self.local_dir):
            logger.warning("Pulling changes ...")
            self.git_pull(rebase=True)
        else:
            logger.warning(f"The current branch has no upstream branch. Will push to 'origin {self.current_branch}'")

        current_working_directory = os.getcwd()
        os.chdir(os.path.join(current_working_directory, self.local_dir))

        try:
            yield self
        finally:
            self.git_add(auto_lfs_track=track_large_files)

            try:
                self.git_commit(commit_message)
            except OSError as e:
                # If no changes are detected, there is nothing to commit.
                if "nothing to commit" not in str(e):
                    raise e

            try:
                self.git_push(
                    upstream=f"origin {self.current_branch}",
                    blocking=blocking,
                    auto_lfs_prune=auto_lfs_prune,
                )
            except OSError as e:
                # If no changes are detected, there is nothing to commit.
                if "could not read Username" in str(e):
                    raise OSError("Couldn't authenticate user for push. Did you set `token` to `True`?") from e
                else:
                    raise e

            os.chdir(current_working_directory)

    def repocard_metadata_load(self) -> Optional[Dict]:
        filepath = os.path.join(self.local_dir, constants.REPOCARD_NAME)
        if os.path.isfile(filepath):
            return metadata_load(filepath)
        return None

    def repocard_metadata_save(self, data: Dict) -> None:
        return metadata_save(os.path.join(self.local_dir, constants.REPOCARD_NAME), data)

    @property
    def commands_failed(self):
        """
        Returns the asynchronous commands that failed.
        """
        return [c for c in self.command_queue if c.status > 0]

    @property
    def commands_in_progress(self):
        """
        Returns the asynchronous commands that are currently in progress.
        """
        return [c for c in self.command_queue if not c.is_done]

    def wait_for_commands(self):
        """
        Blocking method: blocks all subsequent execution until all commands have
        been processed.
        """
        index = 0
        for command_failed in self.commands_failed:
            logger.error(f"The {command_failed.title} command with PID {command_failed._process.pid} failed.")
            logger.error(command_failed.stderr)

        while self.commands_in_progress:
            if index % 10 == 0:
                logger.warning(
                    f"Waiting for the following commands to finish before shutting down: {self.commands_in_progress}."
                )

            index += 1

            time.sleep(1)

# === NexusCore/openenv\Lib\site-packages\nltk\chunk\regexp.py ===
# Natural Language Toolkit: Regular Expression Chunkers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com> (minor additions)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import re

import regex

from nltk.chunk.api import ChunkParserI
from nltk.tree import Tree

# //////////////////////////////////////////////////////
# ChunkString
# //////////////////////////////////////////////////////


class ChunkString:
    """
    A string-based encoding of a particular chunking of a text.
    Internally, the ``ChunkString`` class uses a single string to
    encode the chunking of the input text.  This string contains a
    sequence of angle-bracket delimited tags, with chunking indicated
    by braces.  An example of this encoding is::

        {<DT><JJ><NN>}<VBN><IN>{<DT><NN>}<.>{<DT><NN>}<VBD><.>

    ``ChunkString`` are created from tagged texts (i.e., lists of
    ``tokens`` whose type is ``TaggedType``).  Initially, nothing is
    chunked.

    The chunking of a ``ChunkString`` can be modified with the ``xform()``
    method, which uses a regular expression to transform the string
    representation.  These transformations should only add and remove
    braces; they should *not* modify the sequence of angle-bracket
    delimited tags.

    :type _str: str
    :ivar _str: The internal string representation of the text's
        encoding.  This string representation contains a sequence of
        angle-bracket delimited tags, with chunking indicated by
        braces.  An example of this encoding is::

            {<DT><JJ><NN>}<VBN><IN>{<DT><NN>}<.>{<DT><NN>}<VBD><.>

    :type _pieces: list(tagged tokens and chunks)
    :ivar _pieces: The tagged tokens and chunks encoded by this ``ChunkString``.
    :ivar _debug: The debug level.  See the constructor docs.

    :cvar IN_CHUNK_PATTERN: A zero-width regexp pattern string that
        will only match positions that are in chunks.
    :cvar IN_STRIP_PATTERN: A zero-width regexp pattern string that
        will only match positions that are in strips.
    """

    CHUNK_TAG_CHAR = r"[^\{\}<>]"
    CHUNK_TAG = r"(<%s+?>)" % CHUNK_TAG_CHAR

    IN_CHUNK_PATTERN = r"(?=[^\{]*\})"
    IN_STRIP_PATTERN = r"(?=[^\}]*(\{|$))"

    # These are used by _verify
    _CHUNK = r"(\{%s+?\})+?" % CHUNK_TAG
    _STRIP = r"(%s+?)+?" % CHUNK_TAG
    _VALID = re.compile(r"^(\{?%s\}?)*?$" % CHUNK_TAG)
    _BRACKETS = re.compile(r"[^\{\}]+")
    _BALANCED_BRACKETS = re.compile(r"(\{\})*$")

    def __init__(self, chunk_struct, debug_level=1):
        """
        Construct a new ``ChunkString`` that encodes the chunking of
        the text ``tagged_tokens``.

        :type chunk_struct: Tree
        :param chunk_struct: The chunk structure to be further chunked.
        :type debug_level: int
        :param debug_level: The level of debugging which should be
            applied to transformations on the ``ChunkString``.  The
            valid levels are:

                - 0: no checks
                - 1: full check on to_chunkstruct
                - 2: full check on to_chunkstruct and cursory check after
                  each transformation.
                - 3: full check on to_chunkstruct and full check after
                  each transformation.

            We recommend you use at least level 1.  You should
            probably use level 3 if you use any non-standard
            subclasses of ``RegexpChunkRule``.
        """
        self._root_label = chunk_struct.label()
        self._pieces = chunk_struct[:]
        tags = [self._tag(tok) for tok in self._pieces]
        self._str = "<" + "><".join(tags) + ">"
        self._debug = debug_level

    def _tag(self, tok):
        if isinstance(tok, tuple):
            return tok[1]
        elif isinstance(tok, Tree):
            return tok.label()
        else:
            raise ValueError("chunk structures must contain tagged " "tokens or trees")

    def _verify(self, s, verify_tags):
        """
        Check to make sure that ``s`` still corresponds to some chunked
        version of ``_pieces``.

        :type verify_tags: bool
        :param verify_tags: Whether the individual tags should be
            checked.  If this is false, ``_verify`` will check to make
            sure that ``_str`` encodes a chunked version of *some*
            list of tokens.  If this is true, then ``_verify`` will
            check to make sure that the tags in ``_str`` match those in
            ``_pieces``.

        :raise ValueError: if the internal string representation of
            this ``ChunkString`` is invalid or not consistent with _pieces.
        """
        # Check overall form
        if not ChunkString._VALID.match(s):
            raise ValueError(
                "Transformation generated invalid " "chunkstring:\n  %s" % s
            )

        # Check that parens are balanced.  If the string is long, we
        # have to do this in pieces, to avoid a maximum recursion
        # depth limit for regular expressions.
        brackets = ChunkString._BRACKETS.sub("", s)
        for i in range(1 + len(brackets) // 5000):
            substr = brackets[i * 5000 : i * 5000 + 5000]
            if not ChunkString._BALANCED_BRACKETS.match(substr):
                raise ValueError(
                    "Transformation generated invalid " "chunkstring:\n  %s" % s
                )

        if verify_tags <= 0:
            return

        tags1 = (re.split(r"[\{\}<>]+", s))[1:-1]
        tags2 = [self._tag(piece) for piece in self._pieces]
        if tags1 != tags2:
            raise ValueError(
                "Transformation generated invalid " "chunkstring: tag changed"
            )

    def to_chunkstruct(self, chunk_label="CHUNK"):
        """
        Return the chunk structure encoded by this ``ChunkString``.

        :rtype: Tree
        :raise ValueError: If a transformation has generated an
            invalid chunkstring.
        """
        if self._debug > 0:
            self._verify(self._str, 1)

        # Use this alternating list to create the chunkstruct.
        pieces = []
        index = 0
        piece_in_chunk = 0
        for piece in re.split("[{}]", self._str):
            # Find the list of tokens contained in this piece.
            length = piece.count("<")
            subsequence = self._pieces[index : index + length]

            # Add this list of tokens to our pieces.
            if piece_in_chunk:
                pieces.append(Tree(chunk_label, subsequence))
            else:
                pieces += subsequence

            # Update index, piece_in_chunk
            index += length
            piece_in_chunk = not piece_in_chunk

        return Tree(self._root_label, pieces)

    def xform(self, regexp, repl):
        """
        Apply the given transformation to the string encoding of this
        ``ChunkString``.  In particular, find all occurrences that match
        ``regexp``, and replace them using ``repl`` (as done by
        ``re.sub``).

        This transformation should only add and remove braces; it
        should *not* modify the sequence of angle-bracket delimited
        tags.  Furthermore, this transformation may not result in
        improper bracketing.  Note, in particular, that bracketing may
        not be nested.

        :type regexp: str or regexp
        :param regexp: A regular expression matching the substring
            that should be replaced.  This will typically include a
            named group, which can be used by ``repl``.
        :type repl: str
        :param repl: An expression specifying what should replace the
            matched substring.  Typically, this will include a named
            replacement group, specified by ``regexp``.
        :rtype: None
        :raise ValueError: If this transformation generated an
            invalid chunkstring.
        """
        # Do the actual substitution
        s = re.sub(regexp, repl, self._str)

        # The substitution might have generated "empty chunks"
        # (substrings of the form "{}").  Remove them, so they don't
        # interfere with other transformations.
        s = re.sub(r"\{\}", "", s)

        # Make sure that the transformation was legal.
        if self._debug > 1:
            self._verify(s, self._debug - 2)

        # Commit the transformation.
        self._str = s

    def __repr__(self):
        """
        Return a string representation of this ``ChunkString``.
        It has the form::

            <ChunkString: '{<DT><JJ><NN>}<VBN><IN>{<DT><NN>}'>

        :rtype: str
        """
        return "<ChunkString: %s>" % repr(self._str)

    def __str__(self):
        """
        Return a formatted representation of this ``ChunkString``.
        This representation will include extra spaces to ensure that
        tags will line up with the representation of other
        ``ChunkStrings`` for the same text, regardless of the chunking.

        :rtype: str
        """
        # Add spaces to make everything line up.
        str = re.sub(r">(?!\})", r"> ", self._str)
        str = re.sub(r"([^\{])<", r"\1 <", str)
        if str[0] == "<":
            str = " " + str
        return str


# //////////////////////////////////////////////////////
# Chunking Rules
# //////////////////////////////////////////////////////


class RegexpChunkRule:
    """
    A rule specifying how to modify the chunking in a ``ChunkString``,
    using a transformational regular expression.  The
    ``RegexpChunkRule`` class itself can be used to implement any
    transformational rule based on regular expressions.  There are
    also a number of subclasses, which can be used to implement
    simpler types of rules, based on matching regular expressions.

    Each ``RegexpChunkRule`` has a regular expression and a
    replacement expression.  When a ``RegexpChunkRule`` is "applied"
    to a ``ChunkString``, it searches the ``ChunkString`` for any
    substring that matches the regular expression, and replaces it
    using the replacement expression.  This search/replace operation
    has the same semantics as ``re.sub``.

    Each ``RegexpChunkRule`` also has a description string, which
    gives a short (typically less than 75 characters) description of
    the purpose of the rule.

    This transformation defined by this ``RegexpChunkRule`` should
    only add and remove braces; it should *not* modify the sequence
    of angle-bracket delimited tags.  Furthermore, this transformation
    may not result in nested or mismatched bracketing.
    """

    def __init__(self, regexp, repl, descr):
        """
        Construct a new RegexpChunkRule.

        :type regexp: regexp or str
        :param regexp: The regular expression for this ``RegexpChunkRule``.
            When this rule is applied to a ``ChunkString``, any
            substring that matches ``regexp`` will be replaced using
            the replacement string ``repl``.  Note that this must be a
            normal regular expression, not a tag pattern.
        :type repl: str
        :param repl: The replacement expression for this ``RegexpChunkRule``.
            When this rule is applied to a ``ChunkString``, any substring
            that matches ``regexp`` will be replaced using ``repl``.
        :type descr: str
        :param descr: A short description of the purpose and/or effect
            of this rule.
        """
        if isinstance(regexp, str):
            regexp = re.compile(regexp)
        self._repl = repl
        self._descr = descr
        self._regexp = regexp

    def apply(self, chunkstr):
        # Keep docstring generic so we can inherit it.
        """
        Apply this rule to the given ``ChunkString``.  See the
        class reference documentation for a description of what it
        means to apply a rule.

        :type chunkstr: ChunkString
        :param chunkstr: The chunkstring to which this rule is applied.
        :rtype: None
        :raise ValueError: If this transformation generated an
            invalid chunkstring.
        """
        chunkstr.xform(self._regexp, self._repl)

    def descr(self):
        """
        Return a short description of the purpose and/or effect of
        this rule.

        :rtype: str
        """
        return self._descr

    def __repr__(self):
        """
        Return a string representation of this rule.  It has the form::

            <RegexpChunkRule: '{<IN|VB.*>}'->'<IN>'>

        Note that this representation does not include the
        description string; that string can be accessed
        separately with the ``descr()`` method.

        :rtype: str
        """
        return (
            "<RegexpChunkRule: "
            + repr(self._regexp.pattern)
            + "->"
            + repr(self._repl)
            + ">"
        )

    @staticmethod
    def fromstring(s):
        """
        Create a RegexpChunkRule from a string description.
        Currently, the following formats are supported::

          {regexp}         # chunk rule
          }regexp{         # strip rule
          regexp}{regexp   # split rule
          regexp{}regexp   # merge rule

        Where ``regexp`` is a regular expression for the rule.  Any
        text following the comment marker (``#``) will be used as
        the rule's description:

        >>> from nltk.chunk.regexp import RegexpChunkRule
        >>> RegexpChunkRule.fromstring('{<DT>?<NN.*>+}')
        <ChunkRule: '<DT>?<NN.*>+'>
        """
        # Split off the comment (but don't split on '\#')
        m = re.match(r"(?P<rule>(\\.|[^#])*)(?P<comment>#.*)?", s)
        rule = m.group("rule").strip()
        comment = (m.group("comment") or "")[1:].strip()

        # Pattern bodies: chunk, strip, split, merge
        try:
            if not rule:
                raise ValueError("Empty chunk pattern")
            if rule[0] == "{" and rule[-1] == "}":
                return ChunkRule(rule[1:-1], comment)
            elif rule[0] == "}" and rule[-1] == "{":
                return StripRule(rule[1:-1], comment)
            elif "}{" in rule:
                left, right = rule.split("}{")
                return SplitRule(left, right, comment)
            elif "{}" in rule:
                left, right = rule.split("{}")
                return MergeRule(left, right, comment)
            elif re.match("[^{}]*{[^{}]*}[^{}]*", rule):
                left, chunk, right = re.split("[{}]", rule)
                return ChunkRuleWithContext(left, chunk, right, comment)
            else:
                raise ValueError("Illegal chunk pattern: %s" % rule)
        except (ValueError, re.error) as e:
            raise ValueError("Illegal chunk pattern: %s" % rule) from e


class ChunkRule(RegexpChunkRule):
    """
    A rule specifying how to add chunks to a ``ChunkString``, using a
    matching tag pattern.  When applied to a ``ChunkString``, it will
    find any substring that matches this tag pattern and that is not
    already part of a chunk, and create a new chunk containing that
    substring.
    """

    def __init__(self, tag_pattern, descr):
        """
        Construct a new ``ChunkRule``.

        :type tag_pattern: str
        :param tag_pattern: This rule's tag pattern.  When
            applied to a ``ChunkString``, this rule will
            chunk any substring that matches this tag pattern and that
            is not already part of a chunk.
        :type descr: str
        :param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._pattern = tag_pattern
        regexp = re.compile(
            "(?P<chunk>%s)%s"
            % (tag_pattern2re_pattern(tag_pattern), ChunkString.IN_STRIP_PATTERN)
        )
        RegexpChunkRule.__init__(self, regexp, r"{\g<chunk>}", descr)

    def __repr__(self):
        """
        Return a string representation of this rule.  It has the form::

            <ChunkRule: '<IN|VB.*>'>

        Note that this representation does not include the
        description string; that string can be accessed
        separately with the ``descr()`` method.

        :rtype: str
        """
        return "<ChunkRule: " + repr(self._pattern) + ">"


class StripRule(RegexpChunkRule):
    """
    A rule specifying how to remove strips to a ``ChunkString``,
    using a matching tag pattern.  When applied to a
    ``ChunkString``, it will find any substring that matches this
    tag pattern and that is contained in a chunk, and remove it
    from that chunk, thus creating two new chunks.
    """

    def __init__(self, tag_pattern, descr):
        """
        Construct a new ``StripRule``.

        :type tag_pattern: str
        :param tag_pattern: This rule's tag pattern.  When
            applied to a ``ChunkString``, this rule will
            find any substring that matches this tag pattern and that
            is contained in a chunk, and remove it from that chunk,
            thus creating two new chunks.
        :type descr: str
        :param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._pattern = tag_pattern
        regexp = re.compile(
            "(?P<strip>%s)%s"
            % (tag_pattern2re_pattern(tag_pattern), ChunkString.IN_CHUNK_PATTERN)
        )
        RegexpChunkRule.__init__(self, regexp, r"}\g<strip>{", descr)

    def __repr__(self):
        """
        Return a string representation of this rule.  It has the form::

            <StripRule: '<IN|VB.*>'>

        Note that this representation does not include the
        description string; that string can be accessed
        separately with the ``descr()`` method.

        :rtype: str
        """
        return "<StripRule: " + repr(self._pattern) + ">"


class UnChunkRule(RegexpChunkRule):
    """
    A rule specifying how to remove chunks to a ``ChunkString``,
    using a matching tag pattern.  When applied to a
    ``ChunkString``, it will find any complete chunk that matches this
    tag pattern, and un-chunk it.
    """

    def __init__(self, tag_pattern, descr):
        """
        Construct a new ``UnChunkRule``.

        :type tag_pattern: str
        :param tag_pattern: This rule's tag pattern.  When
            applied to a ``ChunkString``, this rule will
            find any complete chunk that matches this tag pattern,
            and un-chunk it.
        :type descr: str
        :param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._pattern = tag_pattern
        regexp = re.compile(r"\{(?P<chunk>%s)\}" % tag_pattern2re_pattern(tag_pattern))
        RegexpChunkRule.__init__(self, regexp, r"\g<chunk>", descr)

    def __repr__(self):
        """
        Return a string representation of this rule.  It has the form::

            <UnChunkRule: '<IN|VB.*>'>

        Note that this representation does not include the
        description string; that string can be accessed
        separately with the ``descr()`` method.

        :rtype: str
        """
        return "<UnChunkRule: " + repr(self._pattern) + ">"


class MergeRule(RegexpChunkRule):
    """
    A rule specifying how to merge chunks in a ``ChunkString``, using
    two matching tag patterns: a left pattern, and a right pattern.
    When applied to a ``ChunkString``, it will find any chunk whose end
    matches left pattern, and immediately followed by a chunk whose
    beginning matches right pattern.  It will then merge those two
    chunks into a single chunk.
    """

    def __init__(self, left_tag_pattern, right_tag_pattern, descr):
        """
        Construct a new ``MergeRule``.

        :type right_tag_pattern: str
        :param right_tag_pattern: This rule's right tag
            pattern.  When applied to a ``ChunkString``, this
            rule will find any chunk whose end matches
            ``left_tag_pattern``, and immediately followed by a chunk
            whose beginning matches this pattern.  It will
            then merge those two chunks into a single chunk.
        :type left_tag_pattern: str
        :param left_tag_pattern: This rule's left tag
            pattern.  When applied to a ``ChunkString``, this
            rule will find any chunk whose end matches
            this pattern, and immediately followed by a chunk
            whose beginning matches ``right_tag_pattern``.  It will
            then merge those two chunks into a single chunk.

        :type descr: str
        :param descr: A short description of the purpose and/or effect
            of this rule.
        """
        # Ensure that the individual patterns are coherent.  E.g., if
        # left='(' and right=')', then this will raise an exception:
        re.compile(tag_pattern2re_pattern(left_tag_pattern))
        re.compile(tag_pattern2re_pattern(right_tag_pattern))

        self._left_tag_pattern = left_tag_pattern
        self._right_tag_pattern = right_tag_pattern
        regexp = re.compile(
            "(?P<left>%s)}{(?=%s)"
            % (
                tag_pattern2re_pattern(left_tag_pattern),
                tag_pattern2re_pattern(right_tag_pattern),
            )
        )
        RegexpChunkRule.__init__(self, regexp, r"\g<left>", descr)

    def __repr__(self):
        """
        Return a string representation of this rule.  It has the form::

            <MergeRule: '<NN|DT|JJ>', '<NN|JJ>'>

        Note that this representation does not include the
        description string; that string can be accessed
        separately with the ``descr()`` method.

        :rtype: str
        """
        return (
            "<MergeRule: "
            + repr(self._left_tag_pattern)
            + ", "
            + repr(self._right_tag_pattern)
            + ">"
        )


class SplitRule(RegexpChunkRule):
    """
    A rule specifying how to split chunks in a ``ChunkString``, using
    two matching tag patterns: a left pattern, and a right pattern.
    When applied to a ``ChunkString``, it will find any chunk that
    matches the left pattern followed by the right pattern.  It will
    then split the chunk into two new chunks, at the point between the
    two pattern matches.
    """

    def __init__(self, left_tag_pattern, right_tag_pattern, descr):
        """
        Construct a new ``SplitRule``.

        :type right_tag_pattern: str
        :param right_tag_pattern: This rule's right tag
            pattern.  When applied to a ``ChunkString``, this rule will
            find any chunk containing a substring that matches
            ``left_tag_pattern`` followed by this pattern.  It will
            then split the chunk into two new chunks at the point
            between these two matching patterns.
        :type left_tag_pattern: str
        :param left_tag_pattern: This rule's left tag
            pattern.  When applied to a ``ChunkString``, this rule will
            find any chunk containing a substring that matches this
            pattern followed by ``right_tag_pattern``.  It will then
            split the chunk into two new chunks at the point between
            these two matching patterns.
        :type descr: str
        :param descr: A short description of the purpose and/or effect
            of this rule.
        """
        # Ensure that the individual patterns are coherent.  E.g., if
        # left='(' and right=')', then this will raise an exception:
        re.compile(tag_pattern2re_pattern(left_tag_pattern))
        re.compile(tag_pattern2re_pattern(right_tag_pattern))

        self._left_tag_pattern = left_tag_pattern
        self._right_tag_pattern = right_tag_pattern
        regexp = re.compile(
            "(?P<left>%s)(?=%s)"
            % (
                tag_pattern2re_pattern(left_tag_pattern),
                tag_pattern2re_pattern(right_tag_pattern),
            )
        )
        RegexpChunkRule.__init__(self, regexp, r"\g<left>}{", descr)

    def __repr__(self):
        """
        Return a string representation of this rule.  It has the form::

            <SplitRule: '<NN>', '<DT>'>

        Note that this representation does not include the
        description string; that string can be accessed
        separately with the ``descr()`` method.

        :rtype: str
        """
        return (
            "<SplitRule: "
            + repr(self._left_tag_pattern)
            + ", "
            + repr(self._right_tag_pattern)
            + ">"
        )


class ExpandLeftRule(RegexpChunkRule):
    """
    A rule specifying how to expand chunks in a ``ChunkString`` to the left,
    using two matching tag patterns: a left pattern, and a right pattern.
    When applied to a ``ChunkString``, it will find any chunk whose beginning
    matches right pattern, and immediately preceded by a strip whose
    end matches left pattern.  It will then expand the chunk to incorporate
    the new material on the left.
    """

    def __init__(self, left_tag_pattern, right_tag_pattern, descr):
        """
        Construct a new ``ExpandRightRule``.

        :type right_tag_pattern: str
        :param right_tag_pattern: This rule's right tag
            pattern.  When applied to a ``ChunkString``, this
            rule will find any chunk whose beginning matches
            ``right_tag_pattern``, and immediately preceded by a strip
            whose end matches this pattern.  It will
            then merge those two chunks into a single chunk.
        :type left_tag_pattern: str
        :param left_tag_pattern: This rule's left tag
            pattern.  When applied to a ``ChunkString``, this
            rule will find any chunk whose beginning matches
            this pattern, and immediately preceded by a strip
            whose end matches ``left_tag_pattern``.  It will
            then expand the chunk to incorporate the new material on the left.

        :type descr: str
        :param descr: A short description of the purpose and/or effect
            of this rule.
        """
        # Ensure that the individual patterns are coherent.  E.g., if
        # left='(' and right=')', then this will raise an exception:
        re.compile(tag_pattern2re_pattern(left_tag_pattern))
        re.compile(tag_pattern2re_pattern(right_tag_pattern))

        self._left_tag_pattern = left_tag_pattern
        self._right_tag_pattern = right_tag_pattern
        regexp = re.compile(
            r"(?P<left>%s)\{(?P<right>%s)"
            % (
                tag_pattern2re_pattern(left_tag_pattern),
                tag_pattern2re_pattern(right_tag_pattern),
            )
        )
        RegexpChunkRule.__init__(self, regexp, r"{\g<left>\g<right>", descr)

    def __repr__(self):
        """
        Return a string representation of this rule.  It has the form::

            <ExpandLeftRule: '<NN|DT|JJ>', '<NN|JJ>'>

        Note that this representation does not include the
        description string; that string can be accessed
        separately with the ``descr()`` method.

        :rtype: str
        """
        return (
            "<ExpandLeftRule: "
            + repr(self._left_tag_pattern)
            + ", "
            + repr(self._right_tag_pattern)
            + ">"
        )


class ExpandRightRule(RegexpChunkRule):
    """
    A rule specifying how to expand chunks in a ``ChunkString`` to the
    right, using two matching tag patterns: a left pattern, and a
    right pattern.  When applied to a ``ChunkString``, it will find any
    chunk whose end matches left pattern, and immediately followed by
    a strip whose beginning matches right pattern.  It will then
    expand the chunk to incorporate the new material on the right.
    """

    def __init__(self, left_tag_pattern, right_tag_pattern, descr):
        """
        Construct a new ``ExpandRightRule``.

        :type right_tag_pattern: str
        :param right_tag_pattern: This rule's right tag
            pattern.  When applied to a ``ChunkString``, this
            rule will find any chunk whose end matches
            ``left_tag_pattern``, and immediately followed by a strip
            whose beginning matches this pattern.  It will
            then merge those two chunks into a single chunk.
        :type left_tag_pattern: str
        :param left_tag_pattern: This rule's left tag
            pattern.  When applied to a ``ChunkString``, this
            rule will find any chunk whose end matches
            this pattern, and immediately followed by a strip
            whose beginning matches ``right_tag_pattern``.  It will
            then expand the chunk to incorporate the new material on the right.

        :type descr: str
        :param descr: A short description of the purpose and/or effect
            of this rule.
        """
        # Ensure that the individual patterns are coherent.  E.g., if
        # left='(' and right=')', then this will raise an exception:
        re.compile(tag_pattern2re_pattern(left_tag_pattern))
        re.compile(tag_pattern2re_pattern(right_tag_pattern))

        self._left_tag_pattern = left_tag_pattern
        self._right_tag_pattern = right_tag_pattern
        regexp = re.compile(
            r"(?P<left>%s)\}(?P<right>%s)"
            % (
                tag_pattern2re_pattern(left_tag_pattern),
                tag_pattern2re_pattern(right_tag_pattern),
            )
        )
        RegexpChunkRule.__init__(self, regexp, r"\g<left>\g<right>}", descr)

    def __repr__(self):
        """
        Return a string representation of this rule.  It has the form::

            <ExpandRightRule: '<NN|DT|JJ>', '<NN|JJ>'>

        Note that this representation does not include the
        description string; that string can be accessed
        separately with the ``descr()`` method.

        :rtype: str
        """
        return (
            "<ExpandRightRule: "
            + repr(self._left_tag_pattern)
            + ", "
            + repr(self._right_tag_pattern)
            + ">"
        )


class ChunkRuleWithContext(RegexpChunkRule):
    """
    A rule specifying how to add chunks to a ``ChunkString``, using
    three matching tag patterns: one for the left context, one for the
    chunk, and one for the right context.  When applied to a
    ``ChunkString``, it will find any substring that matches the chunk
    tag pattern, is surrounded by substrings that match the two
    context patterns, and is not already part of a chunk; and create a
    new chunk containing the substring that matched the chunk tag
    pattern.

    Caveat: Both the left and right context are consumed when this
    rule matches; therefore, if you need to find overlapping matches,
    you will need to apply your rule more than once.
    """

    def __init__(
        self,
        left_context_tag_pattern,
        chunk_tag_pattern,
        right_context_tag_pattern,
        descr,
    ):
        """
        Construct a new ``ChunkRuleWithContext``.

        :type left_context_tag_pattern: str
        :param left_context_tag_pattern: A tag pattern that must match
            the left context of ``chunk_tag_pattern`` for this rule to
            apply.
        :type chunk_tag_pattern: str
        :param chunk_tag_pattern: A tag pattern that must match for this
            rule to apply.  If the rule does apply, then this pattern
            also identifies the substring that will be made into a chunk.
        :type right_context_tag_pattern: str
        :param right_context_tag_pattern: A tag pattern that must match
            the right context of ``chunk_tag_pattern`` for this rule to
            apply.
        :type descr: str
        :param descr: A short description of the purpose and/or effect
            of this rule.
        """
        # Ensure that the individual patterns are coherent.  E.g., if
        # left='(' and right=')', then this will raise an exception:
        re.compile(tag_pattern2re_pattern(left_context_tag_pattern))
        re.compile(tag_pattern2re_pattern(chunk_tag_pattern))
        re.compile(tag_pattern2re_pattern(right_context_tag_pattern))

        self._left_context_tag_pattern = left_context_tag_pattern
        self._chunk_tag_pattern = chunk_tag_pattern
        self._right_context_tag_pattern = right_context_tag_pattern
        regexp = re.compile(
            "(?P<left>%s)(?P<chunk>%s)(?P<right>%s)%s"
            % (
                tag_pattern2re_pattern(left_context_tag_pattern),
                tag_pattern2re_pattern(chunk_tag_pattern),
                tag_pattern2re_pattern(right_context_tag_pattern),
                ChunkString.IN_STRIP_PATTERN,
            )
        )
        replacement = r"\g<left>{\g<chunk>}\g<right>"
        RegexpChunkRule.__init__(self, regexp, replacement, descr)

    def __repr__(self):
        """
        Return a string representation of this rule.  It has the form::

            <ChunkRuleWithContext: '<IN>', '<NN>', '<DT>'>

        Note that this representation does not include the
        description string; that string can be accessed
        separately with the ``descr()`` method.

        :rtype: str
        """
        return "<ChunkRuleWithContext:  {!r}, {!r}, {!r}>".format(
            self._left_context_tag_pattern,
            self._chunk_tag_pattern,
            self._right_context_tag_pattern,
        )


# //////////////////////////////////////////////////////
# Tag Pattern Format Conversion
# //////////////////////////////////////////////////////

# this should probably be made more strict than it is -- e.g., it
# currently accepts 'foo'.
CHUNK_TAG_PATTERN = re.compile(
    r"^(({}|<{}>)*)$".format(r"([^\{\}<>]|\{\d+,?\}|\{\d*,\d+\})+", r"[^\{\}<>]+")
)


def tag_pattern2re_pattern(tag_pattern):
    """
    Convert a tag pattern to a regular expression pattern.  A "tag
    pattern" is a modified version of a regular expression, designed
    for matching sequences of tags.  The differences between regular
    expression patterns and tag patterns are:

        - In tag patterns, ``'<'`` and ``'>'`` act as parentheses; so
          ``'<NN>+'`` matches one or more repetitions of ``'<NN>'``, not
          ``'<NN'`` followed by one or more repetitions of ``'>'``.
        - Whitespace in tag patterns is ignored.  So
          ``'<DT> | <NN>'`` is equivalent to ``'<DT>|<NN>'``
        - In tag patterns, ``'.'`` is equivalent to ``'[^{}<>]'``; so
          ``'<NN.*>'`` matches any single tag starting with ``'NN'``.

    In particular, ``tag_pattern2re_pattern`` performs the following
    transformations on the given pattern:

        - Replace '.' with '[^<>{}]'
        - Remove any whitespace
        - Add extra parens around '<' and '>', to make '<' and '>' act
          like parentheses.  E.g., so that in '<NN>+', the '+' has scope
          over the entire '<NN>'; and so that in '<NN|IN>', the '|' has
          scope over 'NN' and 'IN', but not '<' or '>'.
        - Check to make sure the resulting pattern is valid.

    :type tag_pattern: str
    :param tag_pattern: The tag pattern to convert to a regular
        expression pattern.
    :raise ValueError: If ``tag_pattern`` is not a valid tag pattern.
        In particular, ``tag_pattern`` should not include braces; and it
        should not contain nested or mismatched angle-brackets.
    :rtype: str
    :return: A regular expression pattern corresponding to
        ``tag_pattern``.
    """
    # Clean up the regular expression
    tag_pattern = re.sub(r"\s", "", tag_pattern)
    tag_pattern = re.sub(r"<", "(<(", tag_pattern)
    tag_pattern = re.sub(r">", ")>)", tag_pattern)

    # Check the regular expression
    if not CHUNK_TAG_PATTERN.match(tag_pattern):
        raise ValueError("Bad tag pattern: %r" % tag_pattern)

    # Replace "." with CHUNK_TAG_CHAR.
    # We have to do this after, since it adds {}[]<>s, which would
    # confuse CHUNK_TAG_PATTERN.
    # PRE doesn't have lookback assertions, so reverse twice, and do
    # the pattern backwards (with lookahead assertions).  This can be
    # made much cleaner once we can switch back to SRE.
    def reverse_str(str):
        lst = list(str)
        lst.reverse()
        return "".join(lst)

    tc_rev = reverse_str(ChunkString.CHUNK_TAG_CHAR)
    reversed = reverse_str(tag_pattern)
    reversed = re.sub(r"\.(?!\\(\\\\)*($|[^\\]))", tc_rev, reversed)
    tag_pattern = reverse_str(reversed)

    return tag_pattern


# //////////////////////////////////////////////////////
# RegexpChunkParser
# //////////////////////////////////////////////////////


class RegexpChunkParser(ChunkParserI):
    """
    A regular expression based chunk parser.  ``RegexpChunkParser`` uses a
    sequence of "rules" to find chunks of a single type within a
    text.  The chunking of the text is encoded using a ``ChunkString``,
    and each rule acts by modifying the chunking in the
    ``ChunkString``.  The rules are all implemented using regular
    expression matching and substitution.

    The ``RegexpChunkRule`` class and its subclasses (``ChunkRule``,
    ``StripRule``, ``UnChunkRule``, ``MergeRule``, and ``SplitRule``)
    define the rules that are used by ``RegexpChunkParser``.  Each rule
    defines an ``apply()`` method, which modifies the chunking encoded
    by a given ``ChunkString``.

    :type _rules: list(RegexpChunkRule)
    :ivar _rules: The list of rules that should be applied to a text.
    :type _trace: int
    :ivar _trace: The default level of tracing.

    """

    def __init__(self, rules, chunk_label="NP", root_label="S", trace=0):
        """
        Construct a new ``RegexpChunkParser``.

        :type rules: list(RegexpChunkRule)
        :param rules: The sequence of rules that should be used to
            generate the chunking for a tagged text.
        :type chunk_label: str
        :param chunk_label: The node value that should be used for
            chunk subtrees.  This is typically a short string
            describing the type of information contained by the chunk,
            such as ``"NP"`` for base noun phrases.
        :type root_label: str
        :param root_label: The node value that should be used for the
            top node of the chunk structure.
        :type trace: int
        :param trace: The level of tracing that should be used when
            parsing a text.  ``0`` will generate no tracing output;
            ``1`` will generate normal tracing output; and ``2`` or
            higher will generate verbose tracing output.
        """
        self._rules = rules
        self._trace = trace
        self._chunk_label = chunk_label
        self._root_label = root_label

    def _trace_apply(self, chunkstr, verbose):
        """
        Apply each rule of this ``RegexpChunkParser`` to ``chunkstr``, in
        turn.  Generate trace output between each rule.  If ``verbose``
        is true, then generate verbose output.

        :type chunkstr: ChunkString
        :param chunkstr: The chunk string to which each rule should be
            applied.
        :type verbose: bool
        :param verbose: Whether output should be verbose.
        :rtype: None
        """
        print("# Input:")
        print(chunkstr)
        for rule in self._rules:
            rule.apply(chunkstr)
            if verbose:
                print("#", rule.descr() + " (" + repr(rule) + "):")
            else:
                print("#", rule.descr() + ":")
            print(chunkstr)

    def _notrace_apply(self, chunkstr):
        """
        Apply each rule of this ``RegexpChunkParser`` to ``chunkstr``, in
        turn.

        :param chunkstr: The chunk string to which each rule should be
            applied.
        :type chunkstr: ChunkString
        :rtype: None
        """

        for rule in self._rules:
            rule.apply(chunkstr)

    def parse(self, chunk_struct, trace=None):
        """
        :type chunk_struct: Tree
        :param chunk_struct: the chunk structure to be (further) chunked
        :type trace: int
        :param trace: The level of tracing that should be used when
            parsing a text.  ``0`` will generate no tracing output;
            ``1`` will generate normal tracing output; and ``2`` or
            higher will generate verbose tracing output.  This value
            overrides the trace level value that was given to the
            constructor.
        :rtype: Tree
        :return: a chunk structure that encodes the chunks in a given
            tagged sentence.  A chunk is a non-overlapping linguistic
            group, such as a noun phrase.  The set of chunks
            identified in the chunk structure depends on the rules
            used to define this ``RegexpChunkParser``.
        """
        if len(chunk_struct) == 0:
            print("Warning: parsing empty text")
            return Tree(self._root_label, [])

        try:
            chunk_struct.label()
        except AttributeError:
            chunk_struct = Tree(self._root_label, chunk_struct)

        # Use the default trace value?
        if trace is None:
            trace = self._trace

        chunkstr = ChunkString(chunk_struct)

        # Apply the sequence of rules to the chunkstring.
        if trace:
            verbose = trace > 1
            self._trace_apply(chunkstr, verbose)
        else:
            self._notrace_apply(chunkstr)

        # Use the chunkstring to create a chunk structure.
        return chunkstr.to_chunkstruct(self._chunk_label)

    def rules(self):
        """
        :return: the sequence of rules used by ``RegexpChunkParser``.
        :rtype: list(RegexpChunkRule)
        """
        return self._rules

    def __repr__(self):
        """
        :return: a concise string representation of this
            ``RegexpChunkParser``.
        :rtype: str
        """
        return "<RegexpChunkParser with %d rules>" % len(self._rules)

    def __str__(self):
        """
        :return: a verbose string representation of this ``RegexpChunkParser``.
        :rtype: str
        """
        s = "RegexpChunkParser with %d rules:\n" % len(self._rules)
        margin = 0
        for rule in self._rules:
            margin = max(margin, len(rule.descr()))
        if margin < 35:
            format = "    %" + repr(-(margin + 3)) + "s%s\n"
        else:
            format = "    %s\n      %s\n"
        for rule in self._rules:
            s += format % (rule.descr(), repr(rule))
        return s[:-1]


# //////////////////////////////////////////////////////
# Chunk Grammar
# //////////////////////////////////////////////////////


class RegexpParser(ChunkParserI):
    r"""
    A grammar based chunk parser.  ``chunk.RegexpParser`` uses a set of
    regular expression patterns to specify the behavior of the parser.
    The chunking of the text is encoded using a ``ChunkString``, and
    each rule acts by modifying the chunking in the ``ChunkString``.
    The rules are all implemented using regular expression matching
    and substitution.

    A grammar contains one or more clauses in the following form::

     NP:
       {<DT|JJ>}          # chunk determiners and adjectives
       }<[\.VI].*>+{      # strip any tag beginning with V, I, or .
       <.*>}{<DT>         # split a chunk at a determiner
       <DT|JJ>{}<NN.*>    # merge chunk ending with det/adj
                          # with one starting with a noun

    The patterns of a clause are executed in order.  An earlier
    pattern may introduce a chunk boundary that prevents a later
    pattern from executing.  Sometimes an individual pattern will
    match on multiple, overlapping extents of the input.  As with
    regular expression substitution more generally, the chunker will
    identify the first match possible, then continue looking for matches
    after this one has ended.

    The clauses of a grammar are also executed in order.  A cascaded
    chunk parser is one having more than one clause.  The maximum depth
    of a parse tree created by this chunk parser is the same as the
    number of clauses in the grammar.

    When tracing is turned on, the comment portion of a line is displayed
    each time the corresponding pattern is applied.

    :type _start: str
    :ivar _start: The start symbol of the grammar (the root node of
        resulting trees)
    :type _stages: int
    :ivar _stages: The list of parsing stages corresponding to the grammar

    """

    def __init__(self, grammar, root_label="S", loop=1, trace=0):
        """
        Create a new chunk parser, from the given start state
        and set of chunk patterns.

        :param grammar: The grammar, or a list of RegexpChunkParser objects
        :type grammar: str or list(RegexpChunkParser)
        :param root_label: The top node of the tree being created
        :type root_label: str or Nonterminal
        :param loop: The number of times to run through the patterns
        :type loop: int
        :type trace: int
        :param trace: The level of tracing that should be used when
            parsing a text.  ``0`` will generate no tracing output;
            ``1`` will generate normal tracing output; and ``2`` or
            higher will generate verbose tracing output.
        """
        self._trace = trace
        self._stages = []
        self._grammar = grammar
        self._loop = loop

        if isinstance(grammar, str):
            self._read_grammar(grammar, root_label, trace)
        else:
            # Make sur the grammar looks like it has the right type:
            type_err = (
                "Expected string or list of RegexpChunkParsers " "for the grammar."
            )
            try:
                grammar = list(grammar)
            except BaseException as e:
                raise TypeError(type_err) from e
            for elt in grammar:
                if not isinstance(elt, RegexpChunkParser):
                    raise TypeError(type_err)
            self._stages = grammar

    def _read_grammar(self, grammar, root_label, trace):
        """
        Helper function for __init__: read the grammar if it is a
        string.
        """
        rules = []
        lhs = None
        pattern = regex.compile("(?P<nonterminal>(\\.|[^:])*)(:(?P<rule>.*))")
        for line in grammar.split("\n"):
            line = line.strip()

            # New stage begins if there's an unescaped ':'
            m = pattern.match(line)
            if m:
                # Record the stage that we just completed.
                self._add_stage(rules, lhs, root_label, trace)
                # Start a new stage.
                lhs = m.group("nonterminal").strip()
                rules = []
                line = m.group("rule").strip()

            # Skip blank & comment-only lines
            if line == "" or line.startswith("#"):
                continue

            # Add the rule
            rules.append(RegexpChunkRule.fromstring(line))

        # Record the final stage
        self._add_stage(rules, lhs, root_label, trace)

    def _add_stage(self, rules, lhs, root_label, trace):
        """
        Helper function for __init__: add a new stage to the parser.
        """
        if rules != []:
            if not lhs:
                raise ValueError("Expected stage marker (eg NP:)")
            parser = RegexpChunkParser(
                rules, chunk_label=lhs, root_label=root_label, trace=trace
            )
            self._stages.append(parser)

    def parse(self, chunk_struct, trace=None):
        """
        Apply the chunk parser to this input.

        :type chunk_struct: Tree
        :param chunk_struct: the chunk structure to be (further) chunked
            (this tree is modified, and is also returned)
        :type trace: int
        :param trace: The level of tracing that should be used when
            parsing a text.  ``0`` will generate no tracing output;
            ``1`` will generate normal tracing output; and ``2`` or
            higher will generate verbose tracing output.  This value
            overrides the trace level value that was given to the
            constructor.
        :return: the chunked output.
        :rtype: Tree
        """
        if trace is None:
            trace = self._trace
        for i in range(self._loop):
            for parser in self._stages:
                chunk_struct = parser.parse(chunk_struct, trace=trace)
        return chunk_struct

    def __repr__(self):
        """
        :return: a concise string representation of this ``chunk.RegexpParser``.
        :rtype: str
        """
        return "<chunk.RegexpParser with %d stages>" % len(self._stages)

    def __str__(self):
        """
        :return: a verbose string representation of this
            ``RegexpParser``.
        :rtype: str
        """
        s = "chunk.RegexpParser with %d stages:\n" % len(self._stages)
        margin = 0
        for parser in self._stages:
            s += "%s\n" % parser
        return s[:-1]


# //////////////////////////////////////////////////////
# Demonstration code
# //////////////////////////////////////////////////////


def demo_eval(chunkparser, text):
    """
    Demonstration code for evaluating a chunk parser, using a
    ``ChunkScore``.  This function assumes that ``text`` contains one
    sentence per line, and that each sentence has the form expected by
    ``tree.chunk``.  It runs the given chunk parser on each sentence in
    the text, and scores the result.  It prints the final score
    (precision, recall, and f-measure); and reports the set of chunks
    that were missed and the set of chunks that were incorrect.  (At
    most 10 missing chunks and 10 incorrect chunks are reported).

    :param chunkparser: The chunkparser to be tested
    :type chunkparser: ChunkParserI
    :param text: The chunked tagged text that should be used for
        evaluation.
    :type text: str
    """
    from nltk import chunk
    from nltk.tree import Tree

    # Evaluate our chunk parser.
    chunkscore = chunk.ChunkScore()

    for sentence in text.split("\n"):
        print(sentence)
        sentence = sentence.strip()
        if not sentence:
            continue
        gold = chunk.tagstr2tree(sentence)
        tokens = gold.leaves()
        test = chunkparser.parse(Tree("S", tokens), trace=1)
        chunkscore.score(gold, test)
        print()

    print("/" + ("=" * 75) + "\\")
    print("Scoring", chunkparser)
    print("-" * 77)
    print("Precision: %5.1f%%" % (chunkscore.precision() * 100), " " * 4, end=" ")
    print("Recall: %5.1f%%" % (chunkscore.recall() * 100), " " * 6, end=" ")
    print("F-Measure: %5.1f%%" % (chunkscore.f_measure() * 100))

    # Missed chunks.
    if chunkscore.missed():
        print("Missed:")
        missed = chunkscore.missed()
        for chunk in missed[:10]:
            print("  ", " ".join(map(str, chunk)))
        if len(chunkscore.missed()) > 10:
            print("  ...")

    # Incorrect chunks.
    if chunkscore.incorrect():
        print("Incorrect:")
        incorrect = chunkscore.incorrect()
        for chunk in incorrect[:10]:
            print("  ", " ".join(map(str, chunk)))
        if len(chunkscore.incorrect()) > 10:
            print("  ...")

    print("\\" + ("=" * 75) + "/")
    print()


def demo():
    """
    A demonstration for the ``RegexpChunkParser`` class.  A single text is
    parsed with four different chunk parsers, using a variety of rules
    and strategies.
    """

    from nltk import Tree, chunk

    text = """\
    [ the/DT little/JJ cat/NN ] sat/VBD on/IN [ the/DT mat/NN ] ./.
    [ John/NNP ] saw/VBD [the/DT cats/NNS] [the/DT dog/NN] chased/VBD ./.
    [ John/NNP ] thinks/VBZ [ Mary/NN ] saw/VBD [ the/DT cat/NN ] sit/VB on/IN [ the/DT mat/NN ]./.
    """

    print("*" * 75)
    print("Evaluation text:")
    print(text)
    print("*" * 75)
    print()

    grammar = r"""
    NP:                   # NP stage
      {<DT>?<JJ>*<NN>}    # chunk determiners, adjectives and nouns
      {<NNP>+}            # chunk proper nouns
    """
    cp = chunk.RegexpParser(grammar)
    demo_eval(cp, text)

    grammar = r"""
    NP:
      {<.*>}              # start by chunking each tag
      }<[\.VI].*>+{       # unchunk any verbs, prepositions or periods
      <DT|JJ>{}<NN.*>     # merge det/adj with nouns
    """
    cp = chunk.RegexpParser(grammar)
    demo_eval(cp, text)

    grammar = r"""
    NP: {<DT>?<JJ>*<NN>}    # chunk determiners, adjectives and nouns
    VP: {<TO>?<VB.*>}       # VP = verb words
    """
    cp = chunk.RegexpParser(grammar)
    demo_eval(cp, text)

    grammar = r"""
    NP: {<.*>*}             # start by chunking everything
        }<[\.VI].*>+{       # strip any verbs, prepositions or periods
        <.*>}{<DT>          # separate on determiners
    PP: {<IN><NP>}          # PP = preposition + noun phrase
    VP: {<VB.*><NP|PP>*}    # VP = verb words + NPs and PPs
    """
    cp = chunk.RegexpParser(grammar)
    demo_eval(cp, text)

    # Evaluation

    from nltk.corpus import conll2000

    print()
    print("Demonstration of empty grammar:")

    cp = chunk.RegexpParser("")
    print(chunk.accuracy(cp, conll2000.chunked_sents("test.txt", chunk_types=("NP",))))

    print()
    print("Demonstration of accuracy evaluation using CoNLL tags:")

    grammar = r"""
    NP:
      {<.*>}              # start by chunking each tag
      }<[\.VI].*>+{       # unchunk any verbs, prepositions or periods
      <DT|JJ>{}<NN.*>     # merge det/adj with nouns
    """
    cp = chunk.RegexpParser(grammar)
    print(chunk.accuracy(cp, conll2000.chunked_sents("test.txt")[:5]))

    print()
    print("Demonstration of tagged token input")

    grammar = r"""
    NP: {<.*>*}             # start by chunking everything
        }<[\.VI].*>+{       # strip any verbs, prepositions or periods
        <.*>}{<DT>          # separate on determiners
    PP: {<IN><NP>}          # PP = preposition + noun phrase
    VP: {<VB.*><NP|PP>*}    # VP = verb words + NPs and PPs
    """
    cp = chunk.RegexpParser(grammar)
    print(
        cp.parse(
            [
                ("the", "DT"),
                ("little", "JJ"),
                ("cat", "NN"),
                ("sat", "VBD"),
                ("on", "IN"),
                ("the", "DT"),
                ("mat", "NN"),
                (".", "."),
            ]
        )
    )


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\otBase.py ===
from fontTools.config import OPTIONS
from fontTools.misc.textTools import Tag, bytesjoin
from .DefaultTable import DefaultTable
from enum import IntEnum
import sys
import array
import struct
import logging
from functools import lru_cache
from typing import Iterator, NamedTuple, Optional, Tuple

log = logging.getLogger(__name__)

have_uharfbuzz = False
try:
    import uharfbuzz as hb

    # repack method added in uharfbuzz >= 0.23; if uharfbuzz *can* be
    # imported but repack method is missing, behave as if uharfbuzz
    # is not available (fallback to the slower Python implementation)
    have_uharfbuzz = callable(getattr(hb, "repack", None))
except ImportError:
    pass

USE_HARFBUZZ_REPACKER = OPTIONS[f"{__name__}:USE_HARFBUZZ_REPACKER"]


class OverflowErrorRecord(object):
    def __init__(self, overflowTuple):
        self.tableType = overflowTuple[0]
        self.LookupListIndex = overflowTuple[1]
        self.SubTableIndex = overflowTuple[2]
        self.itemName = overflowTuple[3]
        self.itemIndex = overflowTuple[4]

    def __repr__(self):
        return str(
            (
                self.tableType,
                "LookupIndex:",
                self.LookupListIndex,
                "SubTableIndex:",
                self.SubTableIndex,
                "ItemName:",
                self.itemName,
                "ItemIndex:",
                self.itemIndex,
            )
        )


class OTLOffsetOverflowError(Exception):
    def __init__(self, overflowErrorRecord):
        self.value = overflowErrorRecord

    def __str__(self):
        return repr(self.value)


class RepackerState(IntEnum):
    # Repacking control flow is implemnted using a state machine. The state machine table:
    #
    # State       | Packing Success | Packing Failed | Exception Raised |
    # ------------+-----------------+----------------+------------------+
    # PURE_FT     | Return result   | PURE_FT        | Return failure   |
    # HB_FT       | Return result   | HB_FT          | FT_FALLBACK      |
    # FT_FALLBACK | HB_FT           | FT_FALLBACK    | Return failure   |

    # Pack only with fontTools, don't allow sharing between extensions.
    PURE_FT = 1

    # Attempt to pack with harfbuzz (allowing sharing between extensions)
    # use fontTools to attempt overflow resolution.
    HB_FT = 2

    # Fallback if HB/FT packing gets stuck. Pack only with fontTools, don't allow sharing between
    # extensions.
    FT_FALLBACK = 3


class BaseTTXConverter(DefaultTable):
    """Generic base class for TTX table converters. It functions as an
    adapter between the TTX (ttLib actually) table model and the model
    we use for OpenType tables, which is necessarily subtly different.
    """

    def decompile(self, data, font):
        """Create an object from the binary data. Called automatically on access."""
        from . import otTables

        reader = OTTableReader(data, tableTag=self.tableTag)
        tableClass = getattr(otTables, self.tableTag)
        self.table = tableClass()
        self.table.decompile(reader, font)

    def compile(self, font):
        """Compiles the table into binary. Called automatically on save."""

        # General outline:
        # Create a top-level OTTableWriter for the GPOS/GSUB table.
        # 	Call the compile method for the the table
        # 		for each 'converter' record in the table converter list
        # 			call converter's write method for each item in the value.
        # 				- For simple items, the write method adds a string to the
        # 				writer's self.items list.
        # 				- For Struct/Table/Subtable items, it add first adds new writer to the
        # 				to the writer's self.items, then calls the item's compile method.
        # 				This creates a tree of writers, rooted at the GUSB/GPOS writer, with
        # 				each writer representing a table, and the writer.items list containing
        # 				the child data strings and writers.
        # 	call the getAllData method
        # 		call _doneWriting, which removes duplicates
        # 		call _gatherTables. This traverses the tables, adding unique occurences to a flat list of tables
        # 		Traverse the flat list of tables, calling getDataLength on each to update their position
        # 		Traverse the flat list of tables again, calling getData each get the data in the table, now that
        # 		pos's and offset are known.

        # 		If a lookup subtable overflows an offset, we have to start all over.
        overflowRecord = None
        # this is 3-state option: default (None) means automatically use hb.repack or
        # silently fall back if it fails; True, use it and raise error if not possible
        # or it errors out; False, don't use it, even if you can.
        use_hb_repack = font.cfg[USE_HARFBUZZ_REPACKER]
        if self.tableTag in ("GSUB", "GPOS"):
            if use_hb_repack is False:
                log.debug(
                    "hb.repack disabled, compiling '%s' with pure-python serializer",
                    self.tableTag,
                )
            elif not have_uharfbuzz:
                if use_hb_repack is True:
                    raise ImportError("No module named 'uharfbuzz'")
                else:
                    assert use_hb_repack is None
                    log.debug(
                        "uharfbuzz not found, compiling '%s' with pure-python serializer",
                        self.tableTag,
                    )

        if (
            use_hb_repack in (None, True)
            and have_uharfbuzz
            and self.tableTag in ("GSUB", "GPOS")
        ):
            state = RepackerState.HB_FT
        else:
            state = RepackerState.PURE_FT

        hb_first_error_logged = False
        lastOverflowRecord = None
        while True:
            try:
                writer = OTTableWriter(tableTag=self.tableTag)
                self.table.compile(writer, font)
                if state == RepackerState.HB_FT:
                    return self.tryPackingHarfbuzz(writer, hb_first_error_logged)
                elif state == RepackerState.PURE_FT:
                    return self.tryPackingFontTools(writer)
                elif state == RepackerState.FT_FALLBACK:
                    # Run packing with FontTools only, but don't return the result as it will
                    # not be optimally packed. Once a successful packing has been found, state is
                    # changed back to harfbuzz packing to produce the final, optimal, packing.
                    self.tryPackingFontTools(writer)
                    log.debug(
                        "Re-enabling sharing between extensions and switching back to "
                        "harfbuzz+fontTools packing."
                    )
                    state = RepackerState.HB_FT

            except OTLOffsetOverflowError as e:
                hb_first_error_logged = True
                ok = self.tryResolveOverflow(font, e, lastOverflowRecord)
                lastOverflowRecord = e.value

                if ok:
                    continue

                if state is RepackerState.HB_FT:
                    log.debug(
                        "Harfbuzz packing out of resolutions, disabling sharing between extensions and "
                        "switching to fontTools only packing."
                    )
                    state = RepackerState.FT_FALLBACK
                else:
                    raise

    def tryPackingHarfbuzz(self, writer, hb_first_error_logged):
        try:
            log.debug("serializing '%s' with hb.repack", self.tableTag)
            return writer.getAllDataUsingHarfbuzz(self.tableTag)
        except (ValueError, MemoryError, hb.RepackerError) as e:
            # Only log hb repacker errors the first time they occur in
            # the offset-overflow resolution loop, they are just noisy.
            # Maybe we can revisit this if/when uharfbuzz actually gives
            # us more info as to why hb.repack failed...
            if not hb_first_error_logged:
                error_msg = f"{type(e).__name__}"
                if str(e) != "":
                    error_msg += f": {e}"
                log.warning(
                    "hb.repack failed to serialize '%s', attempting fonttools resolutions "
                    "; the error message was: %s",
                    self.tableTag,
                    error_msg,
                )
                hb_first_error_logged = True
            return writer.getAllData(remove_duplicate=False)

    def tryPackingFontTools(self, writer):
        return writer.getAllData()

    def tryResolveOverflow(self, font, e, lastOverflowRecord):
        ok = 0
        if lastOverflowRecord == e.value:
            # Oh well...
            return ok

        overflowRecord = e.value
        log.info("Attempting to fix OTLOffsetOverflowError %s", e)

        if overflowRecord.itemName is None:
            from .otTables import fixLookupOverFlows

            ok = fixLookupOverFlows(font, overflowRecord)
        else:
            from .otTables import fixSubTableOverFlows

            ok = fixSubTableOverFlows(font, overflowRecord)

        if ok:
            return ok

        # Try upgrading lookup to Extension and hope
        # that cross-lookup sharing not happening would
        # fix overflow...
        from .otTables import fixLookupOverFlows

        return fixLookupOverFlows(font, overflowRecord)

    def toXML(self, writer, font):
        self.table.toXML2(writer, font)

    def fromXML(self, name, attrs, content, font):
        from . import otTables

        if not hasattr(self, "table"):
            tableClass = getattr(otTables, self.tableTag)
            self.table = tableClass()
        self.table.fromXML(name, attrs, content, font)
        self.table.populateDefaults()

    def ensureDecompiled(self, recurse=True):
        self.table.ensureDecompiled(recurse=recurse)


# https://github.com/fonttools/fonttools/pull/2285#issuecomment-834652928
assert len(struct.pack("i", 0)) == 4
assert array.array("i").itemsize == 4, "Oops, file a bug against fonttools."


class OTTableReader(object):
    """Helper class to retrieve data from an OpenType table."""

    __slots__ = ("data", "offset", "pos", "localState", "tableTag")

    def __init__(self, data, localState=None, offset=0, tableTag=None):
        self.data = data
        self.offset = offset
        self.pos = offset
        self.localState = localState
        self.tableTag = tableTag

    def advance(self, count):
        self.pos += count

    def seek(self, pos):
        self.pos = pos

    def copy(self):
        other = self.__class__(self.data, self.localState, self.offset, self.tableTag)
        other.pos = self.pos
        return other

    def getSubReader(self, offset):
        offset = self.offset + offset
        return self.__class__(self.data, self.localState, offset, self.tableTag)

    def readValue(self, typecode, staticSize):
        pos = self.pos
        newpos = pos + staticSize
        (value,) = struct.unpack(f">{typecode}", self.data[pos:newpos])
        self.pos = newpos
        return value

    def readArray(self, typecode, staticSize, count):
        pos = self.pos
        newpos = pos + count * staticSize
        value = array.array(typecode, self.data[pos:newpos])
        if sys.byteorder != "big":
            value.byteswap()
        self.pos = newpos
        return value.tolist()

    def readInt8(self):
        return self.readValue("b", staticSize=1)

    def readInt8Array(self, count):
        return self.readArray("b", staticSize=1, count=count)

    def readShort(self):
        return self.readValue("h", staticSize=2)

    def readShortArray(self, count):
        return self.readArray("h", staticSize=2, count=count)

    def readLong(self):
        return self.readValue("i", staticSize=4)

    def readLongArray(self, count):
        return self.readArray("i", staticSize=4, count=count)

    def readUInt8(self):
        return self.readValue("B", staticSize=1)

    def readUInt8Array(self, count):
        return self.readArray("B", staticSize=1, count=count)

    def readUShort(self):
        return self.readValue("H", staticSize=2)

    def readUShortArray(self, count):
        return self.readArray("H", staticSize=2, count=count)

    def readULong(self):
        return self.readValue("I", staticSize=4)

    def readULongArray(self, count):
        return self.readArray("I", staticSize=4, count=count)

    def readUInt24(self):
        pos = self.pos
        newpos = pos + 3
        (value,) = struct.unpack(">l", b"\0" + self.data[pos:newpos])
        self.pos = newpos
        return value

    def readUInt24Array(self, count):
        return [self.readUInt24() for _ in range(count)]

    def readTag(self):
        pos = self.pos
        newpos = pos + 4
        value = Tag(self.data[pos:newpos])
        assert len(value) == 4, value
        self.pos = newpos
        return value

    def readData(self, count):
        pos = self.pos
        newpos = pos + count
        value = self.data[pos:newpos]
        self.pos = newpos
        return value

    def __setitem__(self, name, value):
        state = self.localState.copy() if self.localState else dict()
        state[name] = value
        self.localState = state

    def __getitem__(self, name):
        return self.localState and self.localState[name]

    def __contains__(self, name):
        return self.localState and name in self.localState


class OffsetToWriter(object):
    def __init__(self, subWriter, offsetSize):
        self.subWriter = subWriter
        self.offsetSize = offsetSize

    def __eq__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return self.subWriter == other.subWriter and self.offsetSize == other.offsetSize

    def __hash__(self):
        # only works after self._doneWriting() has been called
        return hash((self.subWriter, self.offsetSize))


class OTTableWriter(object):
    """Helper class to gather and assemble data for OpenType tables."""

    def __init__(self, localState=None, tableTag=None):
        self.items = []
        self.pos = None
        self.localState = localState
        self.tableTag = tableTag
        self.parent = None
        self.name = "<none>"

    def __setitem__(self, name, value):
        state = self.localState.copy() if self.localState else dict()
        state[name] = value
        self.localState = state

    def __getitem__(self, name):
        return self.localState[name]

    def __delitem__(self, name):
        del self.localState[name]

    # assembler interface

    def getDataLength(self):
        """Return the length of this table in bytes, without subtables."""
        l = 0
        for item in self.items:
            if hasattr(item, "getCountData"):
                l += item.size
            elif hasattr(item, "subWriter"):
                l += item.offsetSize
            else:
                l = l + len(item)
        return l

    def getData(self):
        """Assemble the data for this writer/table, without subtables."""
        items = list(self.items)  # make a shallow copy
        pos = self.pos
        numItems = len(items)
        for i in range(numItems):
            item = items[i]

            if hasattr(item, "subWriter"):
                if item.offsetSize == 4:
                    items[i] = packULong(item.subWriter.pos - pos)
                elif item.offsetSize == 2:
                    try:
                        items[i] = packUShort(item.subWriter.pos - pos)
                    except struct.error:
                        # provide data to fix overflow problem.
                        overflowErrorRecord = self.getOverflowErrorRecord(
                            item.subWriter
                        )

                        raise OTLOffsetOverflowError(overflowErrorRecord)
                elif item.offsetSize == 3:
                    items[i] = packUInt24(item.subWriter.pos - pos)
                else:
                    raise ValueError(item.offsetSize)

        return bytesjoin(items)

    def getDataForHarfbuzz(self):
        """Assemble the data for this writer/table with all offset field set to 0"""
        items = list(self.items)
        packFuncs = {2: packUShort, 3: packUInt24, 4: packULong}
        for i, item in enumerate(items):
            if hasattr(item, "subWriter"):
                # Offset value is not needed in harfbuzz repacker, so setting offset to 0 to avoid overflow here
                if item.offsetSize in packFuncs:
                    items[i] = packFuncs[item.offsetSize](0)
                else:
                    raise ValueError(item.offsetSize)

        return bytesjoin(items)

    def __hash__(self):
        # only works after self._doneWriting() has been called
        return hash(self.items)

    def __ne__(self, other):
        result = self.__eq__(other)
        return result if result is NotImplemented else not result

    def __eq__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return self.items == other.items

    def _doneWriting(self, internedTables, shareExtension=False):
        # Convert CountData references to data string items
        # collapse duplicate table references to a unique entry
        # "tables" are OTTableWriter objects.

        # For Extension Lookup types, we can
        # eliminate duplicates only within the tree under the Extension Lookup,
        # as offsets may exceed 64K even between Extension LookupTable subtables.
        isExtension = hasattr(self, "Extension")

        # Certain versions of Uniscribe reject the font if the GSUB/GPOS top-level
        # arrays (ScriptList, FeatureList, LookupList) point to the same, possibly
        # empty, array.  So, we don't share those.
        # See: https://github.com/fonttools/fonttools/issues/518
        dontShare = hasattr(self, "DontShare")

        if isExtension and not shareExtension:
            internedTables = {}

        items = self.items
        for i in range(len(items)):
            item = items[i]
            if hasattr(item, "getCountData"):
                items[i] = item.getCountData()
            elif hasattr(item, "subWriter"):
                item.subWriter._doneWriting(
                    internedTables, shareExtension=shareExtension
                )
                # At this point, all subwriters are hashable based on their items.
                # (See hash and comparison magic methods above.) So the ``setdefault``
                # call here will return the first writer object we've seen with
                # equal content, or store it in the dictionary if it's not been
                # seen yet. We therefore replace the subwriter object with an equivalent
                # object, which deduplicates the tree.
                if not dontShare:
                    items[i].subWriter = internedTables.setdefault(
                        item.subWriter, item.subWriter
                    )
        self.items = tuple(items)

    def _gatherTables(self, tables, extTables, done):
        # Convert table references in self.items tree to a flat
        # list of tables in depth-first traversal order.
        # "tables" are OTTableWriter objects.
        # We do the traversal in reverse order at each level, in order to
        # resolve duplicate references to be the last reference in the list of tables.
        # For extension lookups, duplicate references can be merged only within the
        # writer tree under the  extension lookup.

        done[id(self)] = True

        numItems = len(self.items)
        iRange = list(range(numItems))
        iRange.reverse()

        isExtension = hasattr(self, "Extension")

        selfTables = tables

        if isExtension:
            assert (
                extTables is not None
            ), "Program or XML editing error. Extension subtables cannot contain extensions subtables"
            tables, extTables, done = extTables, None, {}

        # add Coverage table if it is sorted last.
        sortCoverageLast = False
        if hasattr(self, "sortCoverageLast"):
            # Find coverage table
            for i in range(numItems):
                item = self.items[i]
                if (
                    hasattr(item, "subWriter")
                    and getattr(item.subWriter, "name", None) == "Coverage"
                ):
                    sortCoverageLast = True
                    break
            if id(item.subWriter) not in done:
                item.subWriter._gatherTables(tables, extTables, done)
            else:
                # We're a new parent of item
                pass

        for i in iRange:
            item = self.items[i]
            if not hasattr(item, "subWriter"):
                continue

            if (
                sortCoverageLast
                and (i == 1)
                and getattr(item.subWriter, "name", None) == "Coverage"
            ):
                # we've already 'gathered' it above
                continue

            if id(item.subWriter) not in done:
                item.subWriter._gatherTables(tables, extTables, done)
            else:
                # Item is already written out by other parent
                pass

        selfTables.append(self)

    def _gatherGraphForHarfbuzz(self, tables, obj_list, done, objidx, virtual_edges):
        real_links = []
        virtual_links = []
        item_idx = objidx

        # Merge virtual_links from parent
        for idx in virtual_edges:
            virtual_links.append((0, 0, idx))

        sortCoverageLast = False
        coverage_idx = 0
        if hasattr(self, "sortCoverageLast"):
            # Find coverage table
            for i, item in enumerate(self.items):
                if getattr(item, "name", None) == "Coverage":
                    sortCoverageLast = True
                    if id(item) not in done:
                        coverage_idx = item_idx = item._gatherGraphForHarfbuzz(
                            tables, obj_list, done, item_idx, virtual_edges
                        )
                    else:
                        coverage_idx = done[id(item)]
                    virtual_edges.append(coverage_idx)
                    break

        child_idx = 0
        offset_pos = 0
        for i, item in enumerate(self.items):
            if hasattr(item, "subWriter"):
                pos = offset_pos
            elif hasattr(item, "getCountData"):
                offset_pos += item.size
                continue
            else:
                offset_pos = offset_pos + len(item)
                continue

            if id(item.subWriter) not in done:
                child_idx = item_idx = item.subWriter._gatherGraphForHarfbuzz(
                    tables, obj_list, done, item_idx, virtual_edges
                )
            else:
                child_idx = done[id(item.subWriter)]

            real_edge = (pos, item.offsetSize, child_idx)
            real_links.append(real_edge)
            offset_pos += item.offsetSize

        tables.append(self)
        obj_list.append((real_links, virtual_links))
        item_idx += 1
        done[id(self)] = item_idx
        if sortCoverageLast:
            virtual_edges.pop()

        return item_idx

    def getAllDataUsingHarfbuzz(self, tableTag):
        """The Whole table is represented as a Graph.
        Assemble graph data and call Harfbuzz repacker to pack the table.
        Harfbuzz repacker is faster and retain as much sub-table sharing as possible, see also:
        https://github.com/harfbuzz/harfbuzz/blob/main/docs/repacker.md
        The input format for hb.repack() method is explained here:
        https://github.com/harfbuzz/uharfbuzz/blob/main/src/uharfbuzz/_harfbuzz.pyx#L1149
        """
        internedTables = {}
        self._doneWriting(internedTables, shareExtension=True)
        tables = []
        obj_list = []
        done = {}
        objidx = 0
        virtual_edges = []
        self._gatherGraphForHarfbuzz(tables, obj_list, done, objidx, virtual_edges)
        # Gather all data in two passes: the absolute positions of all
        # subtable are needed before the actual data can be assembled.
        pos = 0
        for table in tables:
            table.pos = pos
            pos = pos + table.getDataLength()

        data = []
        for table in tables:
            tableData = table.getDataForHarfbuzz()
            data.append(tableData)

        if hasattr(hb, "repack_with_tag"):
            return hb.repack_with_tag(str(tableTag), data, obj_list)
        else:
            return hb.repack(data, obj_list)

    def getAllData(self, remove_duplicate=True):
        """Assemble all data, including all subtables."""
        if remove_duplicate:
            internedTables = {}
            self._doneWriting(internedTables)
        tables = []
        extTables = []
        done = {}
        self._gatherTables(tables, extTables, done)
        tables.reverse()
        extTables.reverse()
        # Gather all data in two passes: the absolute positions of all
        # subtable are needed before the actual data can be assembled.
        pos = 0
        for table in tables:
            table.pos = pos
            pos = pos + table.getDataLength()

        for table in extTables:
            table.pos = pos
            pos = pos + table.getDataLength()

        data = []
        for table in tables:
            tableData = table.getData()
            data.append(tableData)

        for table in extTables:
            tableData = table.getData()
            data.append(tableData)

        return bytesjoin(data)

    # interface for gathering data, as used by table.compile()

    def getSubWriter(self):
        subwriter = self.__class__(self.localState, self.tableTag)
        subwriter.parent = (
            self  # because some subtables have idential values, we discard
        )
        # the duplicates under the getAllData method. Hence some
        # subtable writers can have more than one parent writer.
        # But we just care about first one right now.
        return subwriter

    def writeValue(self, typecode, value):
        self.items.append(struct.pack(f">{typecode}", value))

    def writeArray(self, typecode, values):
        a = array.array(typecode, values)
        if sys.byteorder != "big":
            a.byteswap()
        self.items.append(a.tobytes())

    def writeInt8(self, value):
        assert -128 <= value < 128, value
        self.items.append(struct.pack(">b", value))

    def writeInt8Array(self, values):
        self.writeArray("b", values)

    def writeShort(self, value):
        assert -32768 <= value < 32768, value
        self.items.append(struct.pack(">h", value))

    def writeShortArray(self, values):
        self.writeArray("h", values)

    def writeLong(self, value):
        self.items.append(struct.pack(">i", value))

    def writeLongArray(self, values):
        self.writeArray("i", values)

    def writeUInt8(self, value):
        assert 0 <= value < 256, value
        self.items.append(struct.pack(">B", value))

    def writeUInt8Array(self, values):
        self.writeArray("B", values)

    def writeUShort(self, value):
        assert 0 <= value < 0x10000, value
        self.items.append(struct.pack(">H", value))

    def writeUShortArray(self, values):
        self.writeArray("H", values)

    def writeULong(self, value):
        self.items.append(struct.pack(">I", value))

    def writeULongArray(self, values):
        self.writeArray("I", values)

    def writeUInt24(self, value):
        assert 0 <= value < 0x1000000, value
        b = struct.pack(">L", value)
        self.items.append(b[1:])

    def writeUInt24Array(self, values):
        for value in values:
            self.writeUInt24(value)

    def writeTag(self, tag):
        tag = Tag(tag).tobytes()
        assert len(tag) == 4, tag
        self.items.append(tag)

    def writeSubTable(self, subWriter, offsetSize):
        self.items.append(OffsetToWriter(subWriter, offsetSize))

    def writeCountReference(self, table, name, size=2, value=None):
        ref = CountReference(table, name, size=size, value=value)
        self.items.append(ref)
        return ref

    def writeStruct(self, format, values):
        data = struct.pack(*(format,) + values)
        self.items.append(data)

    def writeData(self, data):
        self.items.append(data)

    def getOverflowErrorRecord(self, item):
        LookupListIndex = SubTableIndex = itemName = itemIndex = None
        if self.name == "LookupList":
            LookupListIndex = item.repeatIndex
        elif self.name == "Lookup":
            LookupListIndex = self.repeatIndex
            SubTableIndex = item.repeatIndex
        else:
            itemName = getattr(item, "name", "<none>")
            if hasattr(item, "repeatIndex"):
                itemIndex = item.repeatIndex
            if self.name == "SubTable":
                LookupListIndex = self.parent.repeatIndex
                SubTableIndex = self.repeatIndex
            elif self.name == "ExtSubTable":
                LookupListIndex = self.parent.parent.repeatIndex
                SubTableIndex = self.parent.repeatIndex
            else:  # who knows how far below the SubTable level we are! Climb back up to the nearest subtable.
                itemName = ".".join([self.name, itemName])
                p1 = self.parent
                while p1 and p1.name not in ["ExtSubTable", "SubTable"]:
                    itemName = ".".join([p1.name, itemName])
                    p1 = p1.parent
                if p1:
                    if p1.name == "ExtSubTable":
                        LookupListIndex = p1.parent.parent.repeatIndex
                        SubTableIndex = p1.parent.repeatIndex
                    else:
                        LookupListIndex = p1.parent.repeatIndex
                        SubTableIndex = p1.repeatIndex

        return OverflowErrorRecord(
            (self.tableTag, LookupListIndex, SubTableIndex, itemName, itemIndex)
        )


class CountReference(object):
    """A reference to a Count value, not a count of references."""

    def __init__(self, table, name, size=None, value=None):
        self.table = table
        self.name = name
        self.size = size
        if value is not None:
            self.setValue(value)

    def setValue(self, value):
        table = self.table
        name = self.name
        if table[name] is None:
            table[name] = value
        else:
            assert table[name] == value, (name, table[name], value)

    def getValue(self):
        return self.table[self.name]

    def getCountData(self):
        v = self.table[self.name]
        if v is None:
            v = 0
        return {1: packUInt8, 2: packUShort, 4: packULong}[self.size](v)


def packUInt8(value):
    return struct.pack(">B", value)


def packUShort(value):
    return struct.pack(">H", value)


def packULong(value):
    assert 0 <= value < 0x100000000, value
    return struct.pack(">I", value)


def packUInt24(value):
    assert 0 <= value < 0x1000000, value
    return struct.pack(">I", value)[1:]


class BaseTable(object):
    """Generic base class for all OpenType (sub)tables."""

    def __getattr__(self, attr):
        reader = self.__dict__.get("reader")
        if reader:
            del self.reader
            font = self.font
            del self.font
            self.decompile(reader, font)
            return getattr(self, attr)

        raise AttributeError(attr)

    def ensureDecompiled(self, recurse=False):
        reader = self.__dict__.get("reader")
        if reader:
            del self.reader
            font = self.font
            del self.font
            self.decompile(reader, font)
        if recurse:
            for subtable in self.iterSubTables():
                subtable.value.ensureDecompiled(recurse)

    def __getstate__(self):
        # before copying/pickling 'lazy' objects, make a shallow copy of OTTableReader
        # https://github.com/fonttools/fonttools/issues/2965
        if "reader" in self.__dict__:
            state = self.__dict__.copy()
            state["reader"] = self.__dict__["reader"].copy()
            return state
        return self.__dict__

    @classmethod
    def getRecordSize(cls, reader):
        totalSize = 0
        for conv in cls.converters:
            size = conv.getRecordSize(reader)
            if size is NotImplemented:
                return NotImplemented
            countValue = 1
            if conv.repeat:
                if conv.repeat in reader:
                    countValue = reader[conv.repeat] + conv.aux
                else:
                    return NotImplemented
            totalSize += size * countValue
        return totalSize

    def getConverters(self):
        return self.converters

    def getConverterByName(self, name):
        return self.convertersByName[name]

    def populateDefaults(self, propagator=None):
        for conv in self.getConverters():
            if conv.repeat:
                if not hasattr(self, conv.name):
                    setattr(self, conv.name, [])
                countValue = len(getattr(self, conv.name)) - conv.aux
                try:
                    count_conv = self.getConverterByName(conv.repeat)
                    setattr(self, conv.repeat, countValue)
                except KeyError:
                    # conv.repeat is a propagated count
                    if propagator and conv.repeat in propagator:
                        propagator[conv.repeat].setValue(countValue)
            else:
                if conv.aux and not eval(conv.aux, None, self.__dict__):
                    continue
                if hasattr(self, conv.name):
                    continue  # Warn if it should NOT be present?!
                if hasattr(conv, "writeNullOffset"):
                    setattr(self, conv.name, None)  # Warn?
                # elif not conv.isCount:
                # 	# Warn?
                # 	pass
                if hasattr(conv, "DEFAULT"):
                    # OptionalValue converters (e.g. VarIndex)
                    setattr(self, conv.name, conv.DEFAULT)

    def decompile(self, reader, font):
        self.readFormat(reader)
        table = {}
        self.__rawTable = table  # for debugging
        for conv in self.getConverters():
            if conv.name == "SubTable":
                conv = conv.getConverter(reader.tableTag, table["LookupType"])
            if conv.name == "ExtSubTable":
                conv = conv.getConverter(reader.tableTag, table["ExtensionLookupType"])
            if conv.name == "FeatureParams":
                conv = conv.getConverter(reader["FeatureTag"])
            if conv.name == "SubStruct":
                conv = conv.getConverter(reader.tableTag, table["MorphType"])
            try:
                if conv.repeat:
                    if isinstance(conv.repeat, int):
                        countValue = conv.repeat
                    elif conv.repeat in table:
                        countValue = table[conv.repeat]
                    else:
                        # conv.repeat is a propagated count
                        countValue = reader[conv.repeat]
                    countValue += conv.aux
                    table[conv.name] = conv.readArray(reader, font, table, countValue)
                else:
                    if conv.aux and not eval(conv.aux, None, table):
                        continue
                    table[conv.name] = conv.read(reader, font, table)
                    if conv.isPropagated:
                        reader[conv.name] = table[conv.name]
            except Exception as e:
                name = conv.name
                e.args = e.args + (name,)
                raise

        if hasattr(self, "postRead"):
            self.postRead(table, font)
        else:
            self.__dict__.update(table)

        del self.__rawTable  # succeeded, get rid of debugging info

    def compile(self, writer, font):
        self.ensureDecompiled()
        # TODO Following hack to be removed by rewriting how FormatSwitching tables
        # are handled.
        # https://github.com/fonttools/fonttools/pull/2238#issuecomment-805192631
        if hasattr(self, "preWrite"):
            deleteFormat = not hasattr(self, "Format")
            table = self.preWrite(font)
            deleteFormat = deleteFormat and hasattr(self, "Format")
        else:
            deleteFormat = False
            table = self.__dict__.copy()

        # some count references may have been initialized in a custom preWrite; we set
        # these in the writer's state beforehand (instead of sequentially) so they will
        # be propagated to all nested subtables even if the count appears in the current
        # table only *after* the offset to the subtable that it is counting.
        for conv in self.getConverters():
            if conv.isCount and conv.isPropagated:
                value = table.get(conv.name)
                if isinstance(value, CountReference):
                    writer[conv.name] = value

        if hasattr(self, "sortCoverageLast"):
            writer.sortCoverageLast = 1

        if hasattr(self, "DontShare"):
            writer.DontShare = True

        if hasattr(self.__class__, "LookupType"):
            writer["LookupType"].setValue(self.__class__.LookupType)

        self.writeFormat(writer)
        for conv in self.getConverters():
            value = table.get(
                conv.name
            )  # TODO Handle defaults instead of defaulting to None!
            if conv.repeat:
                if value is None:
                    value = []
                countValue = len(value) - conv.aux
                if isinstance(conv.repeat, int):
                    assert len(value) == conv.repeat, "expected %d values, got %d" % (
                        conv.repeat,
                        len(value),
                    )
                elif conv.repeat in table:
                    CountReference(table, conv.repeat, value=countValue)
                else:
                    # conv.repeat is a propagated count
                    writer[conv.repeat].setValue(countValue)
                try:
                    conv.writeArray(writer, font, table, value)
                except Exception as e:
                    e.args = e.args + (conv.name + "[]",)
                    raise
            elif conv.isCount:
                # Special-case Count values.
                # Assumption: a Count field will *always* precede
                # the actual array(s).
                # We need a default value, as it may be set later by a nested
                # table. We will later store it here.
                # We add a reference: by the time the data is assembled
                # the Count value will be filled in.
                # We ignore the current count value since it will be recomputed,
                # unless it's a CountReference that was already initialized in a custom preWrite.
                if isinstance(value, CountReference):
                    ref = value
                    ref.size = conv.staticSize
                    writer.writeData(ref)
                    table[conv.name] = ref.getValue()
                else:
                    ref = writer.writeCountReference(table, conv.name, conv.staticSize)
                    table[conv.name] = None
                if conv.isPropagated:
                    writer[conv.name] = ref
            elif conv.isLookupType:
                # We make sure that subtables have the same lookup type,
                # and that the type is the same as the one set on the
                # Lookup object, if any is set.
                if conv.name not in table:
                    table[conv.name] = None
                ref = writer.writeCountReference(
                    table, conv.name, conv.staticSize, table[conv.name]
                )
                writer["LookupType"] = ref
            else:
                if conv.aux and not eval(conv.aux, None, table):
                    continue
                try:
                    conv.write(writer, font, table, value)
                except Exception as e:
                    name = value.__class__.__name__ if value is not None else conv.name
                    e.args = e.args + (name,)
                    raise
                if conv.isPropagated:
                    writer[conv.name] = value

        if deleteFormat:
            del self.Format

    def readFormat(self, reader):
        pass

    def writeFormat(self, writer):
        pass

    def toXML(self, xmlWriter, font, attrs=None, name=None):
        tableName = name if name else self.__class__.__name__
        if attrs is None:
            attrs = []
        if hasattr(self, "Format"):
            attrs = attrs + [("Format", self.Format)]
        xmlWriter.begintag(tableName, attrs)
        xmlWriter.newline()
        self.toXML2(xmlWriter, font)
        xmlWriter.endtag(tableName)
        xmlWriter.newline()

    def toXML2(self, xmlWriter, font):
        # Simpler variant of toXML, *only* for the top level tables (like GPOS, GSUB).
        # This is because in TTX our parent writes our main tag, and in otBase.py we
        # do it ourselves. I think I'm getting schizophrenic...
        for conv in self.getConverters():
            if conv.repeat:
                value = getattr(self, conv.name, [])
                for i in range(len(value)):
                    item = value[i]
                    conv.xmlWrite(xmlWriter, font, item, conv.name, [("index", i)])
            else:
                if conv.aux and not eval(conv.aux, None, vars(self)):
                    continue
                value = getattr(
                    self, conv.name, None
                )  # TODO Handle defaults instead of defaulting to None!
                conv.xmlWrite(xmlWriter, font, value, conv.name, [])

    def fromXML(self, name, attrs, content, font):
        try:
            conv = self.getConverterByName(name)
        except KeyError:
            raise  # XXX on KeyError, raise nice error
        value = conv.xmlRead(attrs, content, font)
        # Some manually-written tables have a conv.repeat of ""
        # to represent lists. Hence comparing to None here to
        # allow those lists to be read correctly from XML.
        if conv.repeat is not None:
            seq = getattr(self, conv.name, None)
            if seq is None:
                seq = []
                setattr(self, conv.name, seq)
            seq.append(value)
        else:
            setattr(self, conv.name, value)

    def __ne__(self, other):
        result = self.__eq__(other)
        return result if result is NotImplemented else not result

    def __eq__(self, other):
        if type(self) != type(other):
            return NotImplemented

        self.ensureDecompiled()
        other.ensureDecompiled()

        return self.__dict__ == other.__dict__

    class SubTableEntry(NamedTuple):
        """See BaseTable.iterSubTables()"""

        name: str
        value: "BaseTable"
        index: Optional[int] = None  # index into given array, None for single values

    def iterSubTables(self) -> Iterator[SubTableEntry]:
        """Yield (name, value, index) namedtuples for all subtables of current table.

        A sub-table is an instance of BaseTable (or subclass thereof) that is a child
        of self, the current parent table.
        The tuples also contain the attribute name (str) of the of parent table to get
        a subtable, and optionally, for lists of subtables (i.e. attributes associated
        with a converter that has a 'repeat'), an index into the list containing the
        given subtable value.
        This method can be useful to traverse trees of otTables.
        """
        for conv in self.getConverters():
            name = conv.name
            value = getattr(self, name, None)
            if value is None:
                continue
            if isinstance(value, BaseTable):
                yield self.SubTableEntry(name, value)
            elif isinstance(value, list):
                yield from (
                    self.SubTableEntry(name, v, index=i)
                    for i, v in enumerate(value)
                    if isinstance(v, BaseTable)
                )

    # instance (not @class)method for consistency with FormatSwitchingBaseTable
    def getVariableAttrs(self):
        return getVariableAttrs(self.__class__)


class FormatSwitchingBaseTable(BaseTable):
    """Minor specialization of BaseTable, for tables that have multiple
    formats, eg. CoverageFormat1 vs. CoverageFormat2."""

    @classmethod
    def getRecordSize(cls, reader):
        return NotImplemented

    def getConverters(self):
        try:
            fmt = self.Format
        except AttributeError:
            # some FormatSwitchingBaseTables (e.g. Coverage) no longer have 'Format'
            # attribute after fully decompiled, only gain one in preWrite before being
            # recompiled. In the decompiled state, these hand-coded classes defined in
            # otTables.py lose their format-specific nature and gain more high-level
            # attributes that are not tied to converters.
            return []
        return self.converters.get(self.Format, [])

    def getConverterByName(self, name):
        return self.convertersByName[self.Format][name]

    def readFormat(self, reader):
        self.Format = reader.readUShort()

    def writeFormat(self, writer):
        writer.writeUShort(self.Format)

    def toXML(self, xmlWriter, font, attrs=None, name=None):
        BaseTable.toXML(self, xmlWriter, font, attrs, name)

    def getVariableAttrs(self):
        return getVariableAttrs(self.__class__, self.Format)


class UInt8FormatSwitchingBaseTable(FormatSwitchingBaseTable):
    def readFormat(self, reader):
        self.Format = reader.readUInt8()

    def writeFormat(self, writer):
        writer.writeUInt8(self.Format)


formatSwitchingBaseTables = {
    "uint16": FormatSwitchingBaseTable,
    "uint8": UInt8FormatSwitchingBaseTable,
}


def getFormatSwitchingBaseTableClass(formatType):
    try:
        return formatSwitchingBaseTables[formatType]
    except KeyError:
        raise TypeError(f"Unsupported format type: {formatType!r}")


# memoize since these are parsed from otData.py, thus stay constant
@lru_cache()
def getVariableAttrs(cls: BaseTable, fmt: Optional[int] = None) -> Tuple[str]:
    """Return sequence of variable table field names (can be empty).

    Attributes are deemed "variable" when their otData.py's description contain
    'VarIndexBase + {offset}', e.g. COLRv1 PaintVar* tables.
    """
    if not issubclass(cls, BaseTable):
        raise TypeError(cls)
    if issubclass(cls, FormatSwitchingBaseTable):
        if fmt is None:
            raise TypeError(f"'fmt' is required for format-switching {cls.__name__}")
        converters = cls.convertersByName[fmt]
    else:
        converters = cls.convertersByName
    # assume if no 'VarIndexBase' field is present, table has no variable fields
    if "VarIndexBase" not in converters:
        return ()
    varAttrs = {}
    for name, conv in converters.items():
        offset = conv.getVarIndexOffset()
        if offset is not None:
            varAttrs[name] = offset
    return tuple(sorted(varAttrs, key=varAttrs.__getitem__))


#
# Support for ValueRecords
#
# This data type is so different from all other OpenType data types that
# it requires quite a bit of code for itself. It even has special support
# in OTTableReader and OTTableWriter...
#

valueRecordFormat = [
    # 	Mask	 Name		isDevice signed
    (0x0001, "XPlacement", 0, 1),
    (0x0002, "YPlacement", 0, 1),
    (0x0004, "XAdvance", 0, 1),
    (0x0008, "YAdvance", 0, 1),
    (0x0010, "XPlaDevice", 1, 0),
    (0x0020, "YPlaDevice", 1, 0),
    (0x0040, "XAdvDevice", 1, 0),
    (0x0080, "YAdvDevice", 1, 0),
    # 	reserved:
    (0x0100, "Reserved1", 0, 0),
    (0x0200, "Reserved2", 0, 0),
    (0x0400, "Reserved3", 0, 0),
    (0x0800, "Reserved4", 0, 0),
    (0x1000, "Reserved5", 0, 0),
    (0x2000, "Reserved6", 0, 0),
    (0x4000, "Reserved7", 0, 0),
    (0x8000, "Reserved8", 0, 0),
]


def _buildDict():
    d = {}
    for mask, name, isDevice, signed in valueRecordFormat:
        d[name] = mask, isDevice, signed
    return d


valueRecordFormatDict = _buildDict()


class ValueRecordFactory(object):
    """Given a format code, this object convert ValueRecords."""

    def __init__(self, valueFormat):
        format = []
        for mask, name, isDevice, signed in valueRecordFormat:
            if valueFormat & mask:
                format.append((name, isDevice, signed))
        self.format = format

    def __len__(self):
        return len(self.format)

    def readValueRecord(self, reader, font):
        format = self.format
        if not format:
            return None
        valueRecord = ValueRecord()
        for name, isDevice, signed in format:
            if signed:
                value = reader.readShort()
            else:
                value = reader.readUShort()
            if isDevice:
                if value:
                    from . import otTables

                    subReader = reader.getSubReader(value)
                    value = getattr(otTables, name)()
                    value.decompile(subReader, font)
                else:
                    value = None
            setattr(valueRecord, name, value)
        return valueRecord

    def writeValueRecord(self, writer, font, valueRecord):
        for name, isDevice, signed in self.format:
            value = getattr(valueRecord, name, 0)
            if isDevice:
                if value:
                    subWriter = writer.getSubWriter()
                    writer.writeSubTable(subWriter, offsetSize=2)
                    value.compile(subWriter, font)
                else:
                    writer.writeUShort(0)
            elif signed:
                writer.writeShort(value)
            else:
                writer.writeUShort(value)


class ValueRecord(object):
    # see ValueRecordFactory

    def __init__(self, valueFormat=None, src=None):
        if valueFormat is not None:
            for mask, name, isDevice, signed in valueRecordFormat:
                if valueFormat & mask:
                    setattr(self, name, None if isDevice else 0)
            if src is not None:
                for key, val in src.__dict__.items():
                    if not hasattr(self, key):
                        continue
                    setattr(self, key, val)
        elif src is not None:
            self.__dict__ = src.__dict__.copy()

    def getFormat(self):
        format = 0
        for name in self.__dict__.keys():
            format = format | valueRecordFormatDict[name][0]
        return format

    def getEffectiveFormat(self):
        format = 0
        for name, value in self.__dict__.items():
            if value:
                format = format | valueRecordFormatDict[name][0]
        return format

    def toXML(self, xmlWriter, font, valueName, attrs=None):
        if attrs is None:
            simpleItems = []
        else:
            simpleItems = list(attrs)
        for mask, name, isDevice, format in valueRecordFormat[:4]:  # "simple" values
            if hasattr(self, name):
                simpleItems.append((name, getattr(self, name)))
        deviceItems = []
        for mask, name, isDevice, format in valueRecordFormat[4:8]:  # device records
            if hasattr(self, name):
                device = getattr(self, name)
                if device is not None:
                    deviceItems.append((name, device))
        if deviceItems:
            xmlWriter.begintag(valueName, simpleItems)
            xmlWriter.newline()
            for name, deviceRecord in deviceItems:
                if deviceRecord is not None:
                    deviceRecord.toXML(xmlWriter, font, name=name)
            xmlWriter.endtag(valueName)
            xmlWriter.newline()
        else:
            xmlWriter.simpletag(valueName, simpleItems)
            xmlWriter.newline()

    def fromXML(self, name, attrs, content, font):
        from . import otTables

        for k, v in attrs.items():
            setattr(self, k, int(v))
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            value = getattr(otTables, name)()
            for elem2 in content:
                if not isinstance(elem2, tuple):
                    continue
                name2, attrs2, content2 = elem2
                value.fromXML(name2, attrs2, content2, font)
            setattr(self, name, value)

    def __ne__(self, other):
        result = self.__eq__(other)
        return result if result is NotImplemented else not result

    def __eq__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

# === NexusCore/openenv\Lib\site-packages\matplotlib\_cm.py ===
"""
Nothing here but dictionaries for generating LinearSegmentedColormaps,
and a dictionary of these dictionaries.

Documentation for each is in pyplot.colormaps().  Please update this
with the purpose and type of your colormap if you add data for one here.
"""

from functools import partial

import numpy as np

_binary_data = {
    'red':    ((0., 1., 1.), (1., 0., 0.)),
    'green':  ((0., 1., 1.), (1., 0., 0.)),
    'blue':   ((0., 1., 1.), (1., 0., 0.))
    }

_autumn_data = {'red':   ((0., 1.0, 1.0), (1.0, 1.0, 1.0)),
                'green': ((0., 0., 0.), (1.0, 1.0, 1.0)),
                'blue':  ((0., 0., 0.), (1.0, 0., 0.))}

_bone_data = {'red':   ((0., 0., 0.),
                        (0.746032, 0.652778, 0.652778),
                        (1.0, 1.0, 1.0)),
              'green': ((0., 0., 0.),
                        (0.365079, 0.319444, 0.319444),
                        (0.746032, 0.777778, 0.777778),
                        (1.0, 1.0, 1.0)),
              'blue':  ((0., 0., 0.),
                        (0.365079, 0.444444, 0.444444),
                        (1.0, 1.0, 1.0))}

_cool_data = {'red':   ((0., 0., 0.), (1.0, 1.0, 1.0)),
              'green': ((0., 1., 1.), (1.0, 0.,  0.)),
              'blue':  ((0., 1., 1.), (1.0, 1.,  1.))}

_copper_data = {'red':   ((0., 0., 0.),
                          (0.809524, 1.000000, 1.000000),
                          (1.0, 1.0, 1.0)),
                'green': ((0., 0., 0.),
                          (1.0, 0.7812, 0.7812)),
                'blue':  ((0., 0., 0.),
                          (1.0, 0.4975, 0.4975))}

def _flag_red(x): return 0.75 * np.sin((x * 31.5 + 0.25) * np.pi) + 0.5
def _flag_green(x): return np.sin(x * 31.5 * np.pi)
def _flag_blue(x): return 0.75 * np.sin((x * 31.5 - 0.25) * np.pi) + 0.5
_flag_data = {'red': _flag_red, 'green': _flag_green, 'blue': _flag_blue}

def _prism_red(x): return 0.75 * np.sin((x * 20.9 + 0.25) * np.pi) + 0.67
def _prism_green(x): return 0.75 * np.sin((x * 20.9 - 0.25) * np.pi) + 0.33
def _prism_blue(x): return -1.1 * np.sin((x * 20.9) * np.pi)
_prism_data = {'red': _prism_red, 'green': _prism_green, 'blue': _prism_blue}

def _ch_helper(gamma, s, r, h, p0, p1, x):
    """Helper function for generating picklable cubehelix colormaps."""
    # Apply gamma factor to emphasise low or high intensity values
    xg = x ** gamma
    # Calculate amplitude and angle of deviation from the black to white
    # diagonal in the plane of constant perceived intensity.
    a = h * xg * (1 - xg) / 2
    phi = 2 * np.pi * (s / 3 + r * x)
    return xg + a * (p0 * np.cos(phi) + p1 * np.sin(phi))

def cubehelix(gamma=1.0, s=0.5, r=-1.5, h=1.0):
    """
    Return custom data dictionary of (r, g, b) conversion functions, which can
    be used with `.ColormapRegistry.register`, for the cubehelix color scheme.

    Unlike most other color schemes cubehelix was designed by D.A. Green to
    be monotonically increasing in terms of perceived brightness.
    Also, when printed on a black and white postscript printer, the scheme
    results in a greyscale with monotonically increasing brightness.
    This color scheme is named cubehelix because the (r, g, b) values produced
    can be visualised as a squashed helix around the diagonal in the
    (r, g, b) color cube.

    For a unit color cube (i.e. 3D coordinates for (r, g, b) each in the
    range 0 to 1) the color scheme starts at (r, g, b) = (0, 0, 0), i.e. black,
    and finishes at (r, g, b) = (1, 1, 1), i.e. white. For some fraction *x*,
    between 0 and 1, the color is the corresponding grey value at that
    fraction along the black to white diagonal (x, x, x) plus a color
    element. This color element is calculated in a plane of constant
    perceived intensity and controlled by the following parameters.

    Parameters
    ----------
    gamma : float, default: 1
        Gamma factor emphasizing either low intensity values (gamma < 1), or
        high intensity values (gamma > 1).
    s : float, default: 0.5 (purple)
        The starting color.
    r : float, default: -1.5
        The number of r, g, b rotations in color that are made from the start
        to the end of the color scheme.  The default of -1.5 corresponds to ->
        B -> G -> R -> B.
    h : float, default: 1
        The hue, i.e. how saturated the colors are. If this parameter is zero
        then the color scheme is purely a greyscale.
    """
    return {'red': partial(_ch_helper, gamma, s, r, h, -0.14861, 1.78277),
            'green': partial(_ch_helper, gamma, s, r, h, -0.29227, -0.90649),
            'blue': partial(_ch_helper, gamma, s, r, h, 1.97294, 0.0)}

_cubehelix_data = cubehelix()

_bwr_data = ((0.0, 0.0, 1.0), (1.0, 1.0, 1.0), (1.0, 0.0, 0.0))
_brg_data = ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))

# Gnuplot palette functions
def _g0(x): return 0
def _g1(x): return 0.5
def _g2(x): return 1
def _g3(x): return x
def _g4(x): return x ** 2
def _g5(x): return x ** 3
def _g6(x): return x ** 4
def _g7(x): return np.sqrt(x)
def _g8(x): return np.sqrt(np.sqrt(x))
def _g9(x): return np.sin(x * np.pi / 2)
def _g10(x): return np.cos(x * np.pi / 2)
def _g11(x): return np.abs(x - 0.5)
def _g12(x): return (2 * x - 1) ** 2
def _g13(x): return np.sin(x * np.pi)
def _g14(x): return np.abs(np.cos(x * np.pi))
def _g15(x): return np.sin(x * 2 * np.pi)
def _g16(x): return np.cos(x * 2 * np.pi)
def _g17(x): return np.abs(np.sin(x * 2 * np.pi))
def _g18(x): return np.abs(np.cos(x * 2 * np.pi))
def _g19(x): return np.abs(np.sin(x * 4 * np.pi))
def _g20(x): return np.abs(np.cos(x * 4 * np.pi))
def _g21(x): return 3 * x
def _g22(x): return 3 * x - 1
def _g23(x): return 3 * x - 2
def _g24(x): return np.abs(3 * x - 1)
def _g25(x): return np.abs(3 * x - 2)
def _g26(x): return (3 * x - 1) / 2
def _g27(x): return (3 * x - 2) / 2
def _g28(x): return np.abs((3 * x - 1) / 2)
def _g29(x): return np.abs((3 * x - 2) / 2)
def _g30(x): return x / 0.32 - 0.78125
def _g31(x): return 2 * x - 0.84
def _g32(x):
    ret = np.zeros(len(x))
    m = (x < 0.25)
    ret[m] = 4 * x[m]
    m = (x >= 0.25) & (x < 0.92)
    ret[m] = -2 * x[m] + 1.84
    m = (x >= 0.92)
    ret[m] = x[m] / 0.08 - 11.5
    return ret
def _g33(x): return np.abs(2 * x - 0.5)
def _g34(x): return 2 * x
def _g35(x): return 2 * x - 0.5
def _g36(x): return 2 * x - 1

gfunc = {i: globals()[f"_g{i}"] for i in range(37)}

_gnuplot_data = {
        'red': gfunc[7],
        'green': gfunc[5],
        'blue': gfunc[15],
}

_gnuplot2_data = {
        'red': gfunc[30],
        'green': gfunc[31],
        'blue': gfunc[32],
}

_ocean_data = {
        'red': gfunc[23],
        'green': gfunc[28],
        'blue': gfunc[3],
}

_afmhot_data = {
        'red': gfunc[34],
        'green': gfunc[35],
        'blue': gfunc[36],
}

_rainbow_data = {
        'red': gfunc[33],
        'green': gfunc[13],
        'blue': gfunc[10],
}

_seismic_data = (
        (0.0, 0.0, 0.3), (0.0, 0.0, 1.0),
        (1.0, 1.0, 1.0), (1.0, 0.0, 0.0),
        (0.5, 0.0, 0.0))

_terrain_data = (
        (0.00, (0.2, 0.2, 0.6)),
        (0.15, (0.0, 0.6, 1.0)),
        (0.25, (0.0, 0.8, 0.4)),
        (0.50, (1.0, 1.0, 0.6)),
        (0.75, (0.5, 0.36, 0.33)),
        (1.00, (1.0, 1.0, 1.0)))

_gray_data = {'red':   ((0., 0, 0), (1., 1, 1)),
              'green': ((0., 0, 0), (1., 1, 1)),
              'blue':  ((0., 0, 0), (1., 1, 1))}

_hot_data = {'red':   ((0., 0.0416, 0.0416),
                       (0.365079, 1.000000, 1.000000),
                       (1.0, 1.0, 1.0)),
             'green': ((0., 0., 0.),
                       (0.365079, 0.000000, 0.000000),
                       (0.746032, 1.000000, 1.000000),
                       (1.0, 1.0, 1.0)),
             'blue':  ((0., 0., 0.),
                       (0.746032, 0.000000, 0.000000),
                       (1.0, 1.0, 1.0))}

_hsv_data = {'red':   ((0., 1., 1.),
                       (0.158730, 1.000000, 1.000000),
                       (0.174603, 0.968750, 0.968750),
                       (0.333333, 0.031250, 0.031250),
                       (0.349206, 0.000000, 0.000000),
                       (0.666667, 0.000000, 0.000000),
                       (0.682540, 0.031250, 0.031250),
                       (0.841270, 0.968750, 0.968750),
                       (0.857143, 1.000000, 1.000000),
                       (1.0, 1.0, 1.0)),
             'green': ((0., 0., 0.),
                       (0.158730, 0.937500, 0.937500),
                       (0.174603, 1.000000, 1.000000),
                       (0.507937, 1.000000, 1.000000),
                       (0.666667, 0.062500, 0.062500),
                       (0.682540, 0.000000, 0.000000),
                       (1.0, 0., 0.)),
             'blue':  ((0., 0., 0.),
                       (0.333333, 0.000000, 0.000000),
                       (0.349206, 0.062500, 0.062500),
                       (0.507937, 1.000000, 1.000000),
                       (0.841270, 1.000000, 1.000000),
                       (0.857143, 0.937500, 0.937500),
                       (1.0, 0.09375, 0.09375))}

_jet_data = {'red':   ((0.00, 0, 0),
                       (0.35, 0, 0),
                       (0.66, 1, 1),
                       (0.89, 1, 1),
                       (1.00, 0.5, 0.5)),
             'green': ((0.000, 0, 0),
                       (0.125, 0, 0),
                       (0.375, 1, 1),
                       (0.640, 1, 1),
                       (0.910, 0, 0),
                       (1.000, 0, 0)),
             'blue':  ((0.00, 0.5, 0.5),
                       (0.11, 1, 1),
                       (0.34, 1, 1),
                       (0.65, 0, 0),
                       (1.00, 0, 0))}

_pink_data = {'red':   ((0., 0.1178, 0.1178), (0.015873, 0.195857, 0.195857),
                        (0.031746, 0.250661, 0.250661),
                        (0.047619, 0.295468, 0.295468),
                        (0.063492, 0.334324, 0.334324),
                        (0.079365, 0.369112, 0.369112),
                        (0.095238, 0.400892, 0.400892),
                        (0.111111, 0.430331, 0.430331),
                        (0.126984, 0.457882, 0.457882),
                        (0.142857, 0.483867, 0.483867),
                        (0.158730, 0.508525, 0.508525),
                        (0.174603, 0.532042, 0.532042),
                        (0.190476, 0.554563, 0.554563),
                        (0.206349, 0.576204, 0.576204),
                        (0.222222, 0.597061, 0.597061),
                        (0.238095, 0.617213, 0.617213),
                        (0.253968, 0.636729, 0.636729),
                        (0.269841, 0.655663, 0.655663),
                        (0.285714, 0.674066, 0.674066),
                        (0.301587, 0.691980, 0.691980),
                        (0.317460, 0.709441, 0.709441),
                        (0.333333, 0.726483, 0.726483),
                        (0.349206, 0.743134, 0.743134),
                        (0.365079, 0.759421, 0.759421),
                        (0.380952, 0.766356, 0.766356),
                        (0.396825, 0.773229, 0.773229),
                        (0.412698, 0.780042, 0.780042),
                        (0.428571, 0.786796, 0.786796),
                        (0.444444, 0.793492, 0.793492),
                        (0.460317, 0.800132, 0.800132),
                        (0.476190, 0.806718, 0.806718),
                        (0.492063, 0.813250, 0.813250),
                        (0.507937, 0.819730, 0.819730),
                        (0.523810, 0.826160, 0.826160),
                        (0.539683, 0.832539, 0.832539),
                        (0.555556, 0.838870, 0.838870),
                        (0.571429, 0.845154, 0.845154),
                        (0.587302, 0.851392, 0.851392),
                        (0.603175, 0.857584, 0.857584),
                        (0.619048, 0.863731, 0.863731),
                        (0.634921, 0.869835, 0.869835),
                        (0.650794, 0.875897, 0.875897),
                        (0.666667, 0.881917, 0.881917),
                        (0.682540, 0.887896, 0.887896),
                        (0.698413, 0.893835, 0.893835),
                        (0.714286, 0.899735, 0.899735),
                        (0.730159, 0.905597, 0.905597),
                        (0.746032, 0.911421, 0.911421),
                        (0.761905, 0.917208, 0.917208),
                        (0.777778, 0.922958, 0.922958),
                        (0.793651, 0.928673, 0.928673),
                        (0.809524, 0.934353, 0.934353),
                        (0.825397, 0.939999, 0.939999),
                        (0.841270, 0.945611, 0.945611),
                        (0.857143, 0.951190, 0.951190),
                        (0.873016, 0.956736, 0.956736),
                        (0.888889, 0.962250, 0.962250),
                        (0.904762, 0.967733, 0.967733),
                        (0.920635, 0.973185, 0.973185),
                        (0.936508, 0.978607, 0.978607),
                        (0.952381, 0.983999, 0.983999),
                        (0.968254, 0.989361, 0.989361),
                        (0.984127, 0.994695, 0.994695), (1.0, 1.0, 1.0)),
              'green': ((0., 0., 0.), (0.015873, 0.102869, 0.102869),
                        (0.031746, 0.145479, 0.145479),
                        (0.047619, 0.178174, 0.178174),
                        (0.063492, 0.205738, 0.205738),
                        (0.079365, 0.230022, 0.230022),
                        (0.095238, 0.251976, 0.251976),
                        (0.111111, 0.272166, 0.272166),
                        (0.126984, 0.290957, 0.290957),
                        (0.142857, 0.308607, 0.308607),
                        (0.158730, 0.325300, 0.325300),
                        (0.174603, 0.341178, 0.341178),
                        (0.190476, 0.356348, 0.356348),
                        (0.206349, 0.370899, 0.370899),
                        (0.222222, 0.384900, 0.384900),
                        (0.238095, 0.398410, 0.398410),
                        (0.253968, 0.411476, 0.411476),
                        (0.269841, 0.424139, 0.424139),
                        (0.285714, 0.436436, 0.436436),
                        (0.301587, 0.448395, 0.448395),
                        (0.317460, 0.460044, 0.460044),
                        (0.333333, 0.471405, 0.471405),
                        (0.349206, 0.482498, 0.482498),
                        (0.365079, 0.493342, 0.493342),
                        (0.380952, 0.517549, 0.517549),
                        (0.396825, 0.540674, 0.540674),
                        (0.412698, 0.562849, 0.562849),
                        (0.428571, 0.584183, 0.584183),
                        (0.444444, 0.604765, 0.604765),
                        (0.460317, 0.624669, 0.624669),
                        (0.476190, 0.643958, 0.643958),
                        (0.492063, 0.662687, 0.662687),
                        (0.507937, 0.680900, 0.680900),
                        (0.523810, 0.698638, 0.698638),
                        (0.539683, 0.715937, 0.715937),
                        (0.555556, 0.732828, 0.732828),
                        (0.571429, 0.749338, 0.749338),
                        (0.587302, 0.765493, 0.765493),
                        (0.603175, 0.781313, 0.781313),
                        (0.619048, 0.796819, 0.796819),
                        (0.634921, 0.812029, 0.812029),
                        (0.650794, 0.826960, 0.826960),
                        (0.666667, 0.841625, 0.841625),
                        (0.682540, 0.856040, 0.856040),
                        (0.698413, 0.870216, 0.870216),
                        (0.714286, 0.884164, 0.884164),
                        (0.730159, 0.897896, 0.897896),
                        (0.746032, 0.911421, 0.911421),
                        (0.761905, 0.917208, 0.917208),
                        (0.777778, 0.922958, 0.922958),
                        (0.793651, 0.928673, 0.928673),
                        (0.809524, 0.934353, 0.934353),
                        (0.825397, 0.939999, 0.939999),
                        (0.841270, 0.945611, 0.945611),
                        (0.857143, 0.951190, 0.951190),
                        (0.873016, 0.956736, 0.956736),
                        (0.888889, 0.962250, 0.962250),
                        (0.904762, 0.967733, 0.967733),
                        (0.920635, 0.973185, 0.973185),
                        (0.936508, 0.978607, 0.978607),
                        (0.952381, 0.983999, 0.983999),
                        (0.968254, 0.989361, 0.989361),
                        (0.984127, 0.994695, 0.994695), (1.0, 1.0, 1.0)),
              'blue':  ((0., 0., 0.), (0.015873, 0.102869, 0.102869),
                        (0.031746, 0.145479, 0.145479),
                        (0.047619, 0.178174, 0.178174),
                        (0.063492, 0.205738, 0.205738),
                        (0.079365, 0.230022, 0.230022),
                        (0.095238, 0.251976, 0.251976),
                        (0.111111, 0.272166, 0.272166),
                        (0.126984, 0.290957, 0.290957),
                        (0.142857, 0.308607, 0.308607),
                        (0.158730, 0.325300, 0.325300),
                        (0.174603, 0.341178, 0.341178),
                        (0.190476, 0.356348, 0.356348),
                        (0.206349, 0.370899, 0.370899),
                        (0.222222, 0.384900, 0.384900),
                        (0.238095, 0.398410, 0.398410),
                        (0.253968, 0.411476, 0.411476),
                        (0.269841, 0.424139, 0.424139),
                        (0.285714, 0.436436, 0.436436),
                        (0.301587, 0.448395, 0.448395),
                        (0.317460, 0.460044, 0.460044),
                        (0.333333, 0.471405, 0.471405),
                        (0.349206, 0.482498, 0.482498),
                        (0.365079, 0.493342, 0.493342),
                        (0.380952, 0.503953, 0.503953),
                        (0.396825, 0.514344, 0.514344),
                        (0.412698, 0.524531, 0.524531),
                        (0.428571, 0.534522, 0.534522),
                        (0.444444, 0.544331, 0.544331),
                        (0.460317, 0.553966, 0.553966),
                        (0.476190, 0.563436, 0.563436),
                        (0.492063, 0.572750, 0.572750),
                        (0.507937, 0.581914, 0.581914),
                        (0.523810, 0.590937, 0.590937),
                        (0.539683, 0.599824, 0.599824),
                        (0.555556, 0.608581, 0.608581),
                        (0.571429, 0.617213, 0.617213),
                        (0.587302, 0.625727, 0.625727),
                        (0.603175, 0.634126, 0.634126),
                        (0.619048, 0.642416, 0.642416),
                        (0.634921, 0.650600, 0.650600),
                        (0.650794, 0.658682, 0.658682),
                        (0.666667, 0.666667, 0.666667),
                        (0.682540, 0.674556, 0.674556),
                        (0.698413, 0.682355, 0.682355),
                        (0.714286, 0.690066, 0.690066),
                        (0.730159, 0.697691, 0.697691),
                        (0.746032, 0.705234, 0.705234),
                        (0.761905, 0.727166, 0.727166),
                        (0.777778, 0.748455, 0.748455),
                        (0.793651, 0.769156, 0.769156),
                        (0.809524, 0.789314, 0.789314),
                        (0.825397, 0.808969, 0.808969),
                        (0.841270, 0.828159, 0.828159),
                        (0.857143, 0.846913, 0.846913),
                        (0.873016, 0.865261, 0.865261),
                        (0.888889, 0.883229, 0.883229),
                        (0.904762, 0.900837, 0.900837),
                        (0.920635, 0.918109, 0.918109),
                        (0.936508, 0.935061, 0.935061),
                        (0.952381, 0.951711, 0.951711),
                        (0.968254, 0.968075, 0.968075),
                        (0.984127, 0.984167, 0.984167), (1.0, 1.0, 1.0))}

_spring_data = {'red':   ((0., 1., 1.), (1.0, 1.0, 1.0)),
                'green': ((0., 0., 0.), (1.0, 1.0, 1.0)),
                'blue':  ((0., 1., 1.), (1.0, 0.0, 0.0))}


_summer_data = {'red':   ((0., 0., 0.), (1.0, 1.0, 1.0)),
                'green': ((0., 0.5, 0.5), (1.0, 1.0, 1.0)),
                'blue':  ((0., 0.4, 0.4), (1.0, 0.4, 0.4))}


_winter_data = {'red':   ((0., 0., 0.), (1.0, 0.0, 0.0)),
                'green': ((0., 0., 0.), (1.0, 1.0, 1.0)),
                'blue':  ((0., 1., 1.), (1.0, 0.5, 0.5))}

_nipy_spectral_data = {
    'red': [
        (0.0, 0.0, 0.0), (0.05, 0.4667, 0.4667),
        (0.10, 0.5333, 0.5333), (0.15, 0.0, 0.0),
        (0.20, 0.0, 0.0), (0.25, 0.0, 0.0),
        (0.30, 0.0, 0.0), (0.35, 0.0, 0.0),
        (0.40, 0.0, 0.0), (0.45, 0.0, 0.0),
        (0.50, 0.0, 0.0), (0.55, 0.0, 0.0),
        (0.60, 0.0, 0.0), (0.65, 0.7333, 0.7333),
        (0.70, 0.9333, 0.9333), (0.75, 1.0, 1.0),
        (0.80, 1.0, 1.0), (0.85, 1.0, 1.0),
        (0.90, 0.8667, 0.8667), (0.95, 0.80, 0.80),
        (1.0, 0.80, 0.80),
    ],
    'green': [
        (0.0, 0.0, 0.0), (0.05, 0.0, 0.0),
        (0.10, 0.0, 0.0), (0.15, 0.0, 0.0),
        (0.20, 0.0, 0.0), (0.25, 0.4667, 0.4667),
        (0.30, 0.6000, 0.6000), (0.35, 0.6667, 0.6667),
        (0.40, 0.6667, 0.6667), (0.45, 0.6000, 0.6000),
        (0.50, 0.7333, 0.7333), (0.55, 0.8667, 0.8667),
        (0.60, 1.0, 1.0), (0.65, 1.0, 1.0),
        (0.70, 0.9333, 0.9333), (0.75, 0.8000, 0.8000),
        (0.80, 0.6000, 0.6000), (0.85, 0.0, 0.0),
        (0.90, 0.0, 0.0), (0.95, 0.0, 0.0),
        (1.0, 0.80, 0.80),
    ],
    'blue': [
        (0.0, 0.0, 0.0), (0.05, 0.5333, 0.5333),
        (0.10, 0.6000, 0.6000), (0.15, 0.6667, 0.6667),
        (0.20, 0.8667, 0.8667), (0.25, 0.8667, 0.8667),
        (0.30, 0.8667, 0.8667), (0.35, 0.6667, 0.6667),
        (0.40, 0.5333, 0.5333), (0.45, 0.0, 0.0),
        (0.5, 0.0, 0.0), (0.55, 0.0, 0.0),
        (0.60, 0.0, 0.0), (0.65, 0.0, 0.0),
        (0.70, 0.0, 0.0), (0.75, 0.0, 0.0),
        (0.80, 0.0, 0.0), (0.85, 0.0, 0.0),
        (0.90, 0.0, 0.0), (0.95, 0.0, 0.0),
        (1.0, 0.80, 0.80),
    ],
}


# 34 colormaps based on color specifications and designs
# developed by Cynthia Brewer (https://colorbrewer2.org/).
# The ColorBrewer palettes have been included under the terms
# of an Apache-stype license (for details, see the file
# LICENSE_COLORBREWER in the license directory of the matplotlib
# source distribution).

# RGB values taken from Brewer's Excel sheet, divided by 255

_Blues_data = (
    (0.96862745098039216,  0.98431372549019602,  1.0                ),
    (0.87058823529411766,  0.92156862745098034,  0.96862745098039216),
    (0.77647058823529413,  0.85882352941176465,  0.93725490196078431),
    (0.61960784313725492,  0.792156862745098  ,  0.88235294117647056),
    (0.41960784313725491,  0.68235294117647061,  0.83921568627450982),
    (0.25882352941176473,  0.5725490196078431 ,  0.77647058823529413),
    (0.12941176470588237,  0.44313725490196076,  0.70980392156862748),
    (0.03137254901960784,  0.31764705882352939,  0.61176470588235299),
    (0.03137254901960784,  0.18823529411764706,  0.41960784313725491)
    )

_BrBG_data = (
    (0.32941176470588235,  0.18823529411764706,  0.0196078431372549 ),
    (0.5490196078431373 ,  0.31764705882352939,  0.0392156862745098 ),
    (0.74901960784313726,  0.50588235294117645,  0.17647058823529413),
    (0.87450980392156863,  0.76078431372549016,  0.49019607843137253),
    (0.96470588235294119,  0.90980392156862744,  0.76470588235294112),
    (0.96078431372549022,  0.96078431372549022,  0.96078431372549022),
    (0.7803921568627451 ,  0.91764705882352937,  0.89803921568627454),
    (0.50196078431372548,  0.80392156862745101,  0.75686274509803919),
    (0.20784313725490197,  0.59215686274509804,  0.5607843137254902 ),
    (0.00392156862745098,  0.4                ,  0.36862745098039218),
    (0.0                ,  0.23529411764705882,  0.18823529411764706)
    )

_BuGn_data = (
    (0.96862745098039216,  0.9882352941176471 ,  0.99215686274509807),
    (0.89803921568627454,  0.96078431372549022,  0.97647058823529409),
    (0.8                ,  0.92549019607843142,  0.90196078431372551),
    (0.6                ,  0.84705882352941175,  0.78823529411764703),
    (0.4                ,  0.76078431372549016,  0.64313725490196083),
    (0.25490196078431371,  0.68235294117647061,  0.46274509803921571),
    (0.13725490196078433,  0.54509803921568623,  0.27058823529411763),
    (0.0                ,  0.42745098039215684,  0.17254901960784313),
    (0.0                ,  0.26666666666666666,  0.10588235294117647)
    )

_BuPu_data = (
    (0.96862745098039216,  0.9882352941176471 ,  0.99215686274509807),
    (0.8784313725490196 ,  0.92549019607843142,  0.95686274509803926),
    (0.74901960784313726,  0.82745098039215681,  0.90196078431372551),
    (0.61960784313725492,  0.73725490196078436,  0.85490196078431369),
    (0.5490196078431373 ,  0.58823529411764708,  0.77647058823529413),
    (0.5490196078431373 ,  0.41960784313725491,  0.69411764705882351),
    (0.53333333333333333,  0.25490196078431371,  0.61568627450980395),
    (0.50588235294117645,  0.05882352941176471,  0.48627450980392156),
    (0.30196078431372547,  0.0                ,  0.29411764705882354)
    )

_GnBu_data = (
    (0.96862745098039216,  0.9882352941176471 ,  0.94117647058823528),
    (0.8784313725490196 ,  0.95294117647058818,  0.85882352941176465),
    (0.8                ,  0.92156862745098034,  0.77254901960784317),
    (0.6588235294117647 ,  0.8666666666666667 ,  0.70980392156862748),
    (0.4823529411764706 ,  0.8                ,  0.7686274509803922 ),
    (0.30588235294117649,  0.70196078431372544,  0.82745098039215681),
    (0.16862745098039217,  0.5490196078431373 ,  0.74509803921568629),
    (0.03137254901960784,  0.40784313725490196,  0.67450980392156867),
    (0.03137254901960784,  0.25098039215686274,  0.50588235294117645)
    )

_Greens_data = (
    (0.96862745098039216,  0.9882352941176471 ,  0.96078431372549022),
    (0.89803921568627454,  0.96078431372549022,  0.8784313725490196 ),
    (0.7803921568627451 ,  0.9137254901960784 ,  0.75294117647058822),
    (0.63137254901960782,  0.85098039215686272,  0.60784313725490191),
    (0.45490196078431372,  0.7686274509803922 ,  0.46274509803921571),
    (0.25490196078431371,  0.6705882352941176 ,  0.36470588235294116),
    (0.13725490196078433,  0.54509803921568623,  0.27058823529411763),
    (0.0                ,  0.42745098039215684,  0.17254901960784313),
    (0.0                ,  0.26666666666666666,  0.10588235294117647)
    )

_Greys_data = (
    (1.0                ,  1.0                ,  1.0                ),
    (0.94117647058823528,  0.94117647058823528,  0.94117647058823528),
    (0.85098039215686272,  0.85098039215686272,  0.85098039215686272),
    (0.74117647058823533,  0.74117647058823533,  0.74117647058823533),
    (0.58823529411764708,  0.58823529411764708,  0.58823529411764708),
    (0.45098039215686275,  0.45098039215686275,  0.45098039215686275),
    (0.32156862745098042,  0.32156862745098042,  0.32156862745098042),
    (0.14509803921568629,  0.14509803921568629,  0.14509803921568629),
    (0.0                ,  0.0                ,  0.0                )
    )

_Oranges_data = (
    (1.0                ,  0.96078431372549022,  0.92156862745098034),
    (0.99607843137254903,  0.90196078431372551,  0.80784313725490198),
    (0.99215686274509807,  0.81568627450980391,  0.63529411764705879),
    (0.99215686274509807,  0.68235294117647061,  0.41960784313725491),
    (0.99215686274509807,  0.55294117647058827,  0.23529411764705882),
    (0.94509803921568625,  0.41176470588235292,  0.07450980392156863),
    (0.85098039215686272,  0.28235294117647058,  0.00392156862745098),
    (0.65098039215686276,  0.21176470588235294,  0.01176470588235294),
    (0.49803921568627452,  0.15294117647058825,  0.01568627450980392)
    )

_OrRd_data = (
    (1.0                ,  0.96862745098039216,  0.92549019607843142),
    (0.99607843137254903,  0.90980392156862744,  0.78431372549019607),
    (0.99215686274509807,  0.83137254901960789,  0.61960784313725492),
    (0.99215686274509807,  0.73333333333333328,  0.51764705882352946),
    (0.9882352941176471 ,  0.55294117647058827,  0.34901960784313724),
    (0.93725490196078431,  0.396078431372549  ,  0.28235294117647058),
    (0.84313725490196079,  0.18823529411764706,  0.12156862745098039),
    (0.70196078431372544,  0.0                ,  0.0                ),
    (0.49803921568627452,  0.0                ,  0.0                )
    )

_PiYG_data = (
    (0.55686274509803924,  0.00392156862745098,  0.32156862745098042),
    (0.77254901960784317,  0.10588235294117647,  0.49019607843137253),
    (0.87058823529411766,  0.46666666666666667,  0.68235294117647061),
    (0.94509803921568625,  0.71372549019607845,  0.85490196078431369),
    (0.99215686274509807,  0.8784313725490196 ,  0.93725490196078431),
    (0.96862745098039216,  0.96862745098039216,  0.96862745098039216),
    (0.90196078431372551,  0.96078431372549022,  0.81568627450980391),
    (0.72156862745098038,  0.88235294117647056,  0.52549019607843139),
    (0.49803921568627452,  0.73725490196078436,  0.25490196078431371),
    (0.30196078431372547,  0.5725490196078431 ,  0.12941176470588237),
    (0.15294117647058825,  0.39215686274509803,  0.09803921568627451)
    )

_PRGn_data = (
    (0.25098039215686274,  0.0                ,  0.29411764705882354),
    (0.46274509803921571,  0.16470588235294117,  0.51372549019607838),
    (0.6                ,  0.4392156862745098 ,  0.6705882352941176 ),
    (0.76078431372549016,  0.6470588235294118 ,  0.81176470588235294),
    (0.90588235294117647,  0.83137254901960789,  0.90980392156862744),
    (0.96862745098039216,  0.96862745098039216,  0.96862745098039216),
    (0.85098039215686272,  0.94117647058823528,  0.82745098039215681),
    (0.65098039215686276,  0.85882352941176465,  0.62745098039215685),
    (0.35294117647058826,  0.68235294117647061,  0.38039215686274508),
    (0.10588235294117647,  0.47058823529411764,  0.21568627450980393),
    (0.0                ,  0.26666666666666666,  0.10588235294117647)
    )

_PuBu_data = (
    (1.0                ,  0.96862745098039216,  0.98431372549019602),
    (0.92549019607843142,  0.90588235294117647,  0.94901960784313721),
    (0.81568627450980391,  0.81960784313725488,  0.90196078431372551),
    (0.65098039215686276,  0.74117647058823533,  0.85882352941176465),
    (0.45490196078431372,  0.66274509803921566,  0.81176470588235294),
    (0.21176470588235294,  0.56470588235294117,  0.75294117647058822),
    (0.0196078431372549 ,  0.4392156862745098 ,  0.69019607843137254),
    (0.01568627450980392,  0.35294117647058826,  0.55294117647058827),
    (0.00784313725490196,  0.2196078431372549 ,  0.34509803921568627)
    )

_PuBuGn_data = (
    (1.0                ,  0.96862745098039216,  0.98431372549019602),
    (0.92549019607843142,  0.88627450980392153,  0.94117647058823528),
    (0.81568627450980391,  0.81960784313725488,  0.90196078431372551),
    (0.65098039215686276,  0.74117647058823533,  0.85882352941176465),
    (0.40392156862745099,  0.66274509803921566,  0.81176470588235294),
    (0.21176470588235294,  0.56470588235294117,  0.75294117647058822),
    (0.00784313725490196,  0.50588235294117645,  0.54117647058823526),
    (0.00392156862745098,  0.42352941176470588,  0.34901960784313724),
    (0.00392156862745098,  0.27450980392156865,  0.21176470588235294)
    )

_PuOr_data = (
    (0.49803921568627452,  0.23137254901960785,  0.03137254901960784),
    (0.70196078431372544,  0.34509803921568627,  0.02352941176470588),
    (0.8784313725490196 ,  0.50980392156862742,  0.07843137254901961),
    (0.99215686274509807,  0.72156862745098038,  0.38823529411764707),
    (0.99607843137254903,  0.8784313725490196 ,  0.71372549019607845),
    (0.96862745098039216,  0.96862745098039216,  0.96862745098039216),
    (0.84705882352941175,  0.85490196078431369,  0.92156862745098034),
    (0.69803921568627447,  0.6705882352941176 ,  0.82352941176470584),
    (0.50196078431372548,  0.45098039215686275,  0.67450980392156867),
    (0.32941176470588235,  0.15294117647058825,  0.53333333333333333),
    (0.17647058823529413,  0.0                ,  0.29411764705882354)
    )

_PuRd_data = (
    (0.96862745098039216,  0.95686274509803926,  0.97647058823529409),
    (0.90588235294117647,  0.88235294117647056,  0.93725490196078431),
    (0.83137254901960789,  0.72549019607843135,  0.85490196078431369),
    (0.78823529411764703,  0.58039215686274515,  0.7803921568627451 ),
    (0.87450980392156863,  0.396078431372549  ,  0.69019607843137254),
    (0.90588235294117647,  0.16078431372549021,  0.54117647058823526),
    (0.80784313725490198,  0.07058823529411765,  0.33725490196078434),
    (0.59607843137254901,  0.0                ,  0.2627450980392157 ),
    (0.40392156862745099,  0.0                ,  0.12156862745098039)
    )

_Purples_data = (
    (0.9882352941176471 ,  0.98431372549019602,  0.99215686274509807),
    (0.93725490196078431,  0.92941176470588238,  0.96078431372549022),
    (0.85490196078431369,  0.85490196078431369,  0.92156862745098034),
    (0.73725490196078436,  0.74117647058823533,  0.86274509803921573),
    (0.61960784313725492,  0.60392156862745094,  0.78431372549019607),
    (0.50196078431372548,  0.49019607843137253,  0.72941176470588232),
    (0.41568627450980394,  0.31764705882352939,  0.63921568627450975),
    (0.32941176470588235,  0.15294117647058825,  0.5607843137254902 ),
    (0.24705882352941178,  0.0                ,  0.49019607843137253)
    )

_RdBu_data = (
    (0.40392156862745099,  0.0                ,  0.12156862745098039),
    (0.69803921568627447,  0.09411764705882353,  0.16862745098039217),
    (0.83921568627450982,  0.37647058823529411,  0.30196078431372547),
    (0.95686274509803926,  0.6470588235294118 ,  0.50980392156862742),
    (0.99215686274509807,  0.85882352941176465,  0.7803921568627451 ),
    (0.96862745098039216,  0.96862745098039216,  0.96862745098039216),
    (0.81960784313725488,  0.89803921568627454,  0.94117647058823528),
    (0.5725490196078431 ,  0.77254901960784317,  0.87058823529411766),
    (0.2627450980392157 ,  0.57647058823529407,  0.76470588235294112),
    (0.12941176470588237,  0.4                ,  0.67450980392156867),
    (0.0196078431372549 ,  0.18823529411764706,  0.38039215686274508)
    )

_RdGy_data = (
    (0.40392156862745099,  0.0                ,  0.12156862745098039),
    (0.69803921568627447,  0.09411764705882353,  0.16862745098039217),
    (0.83921568627450982,  0.37647058823529411,  0.30196078431372547),
    (0.95686274509803926,  0.6470588235294118 ,  0.50980392156862742),
    (0.99215686274509807,  0.85882352941176465,  0.7803921568627451 ),
    (1.0                ,  1.0                ,  1.0                ),
    (0.8784313725490196 ,  0.8784313725490196 ,  0.8784313725490196 ),
    (0.72941176470588232,  0.72941176470588232,  0.72941176470588232),
    (0.52941176470588236,  0.52941176470588236,  0.52941176470588236),
    (0.30196078431372547,  0.30196078431372547,  0.30196078431372547),
    (0.10196078431372549,  0.10196078431372549,  0.10196078431372549)
    )

_RdPu_data = (
    (1.0                ,  0.96862745098039216,  0.95294117647058818),
    (0.99215686274509807,  0.8784313725490196 ,  0.86666666666666667),
    (0.9882352941176471 ,  0.77254901960784317,  0.75294117647058822),
    (0.98039215686274506,  0.62352941176470589,  0.70980392156862748),
    (0.96862745098039216,  0.40784313725490196,  0.63137254901960782),
    (0.86666666666666667,  0.20392156862745098,  0.59215686274509804),
    (0.68235294117647061,  0.00392156862745098,  0.49411764705882355),
    (0.47843137254901963,  0.00392156862745098,  0.46666666666666667),
    (0.28627450980392155,  0.0                ,  0.41568627450980394)
    )

_RdYlBu_data = (
    (0.6470588235294118 , 0.0                 , 0.14901960784313725),
    (0.84313725490196079, 0.18823529411764706 , 0.15294117647058825),
    (0.95686274509803926, 0.42745098039215684 , 0.2627450980392157 ),
    (0.99215686274509807, 0.68235294117647061 , 0.38039215686274508),
    (0.99607843137254903, 0.8784313725490196  , 0.56470588235294117),
    (1.0                , 1.0                 , 0.74901960784313726),
    (0.8784313725490196 , 0.95294117647058818 , 0.97254901960784312),
    (0.6705882352941176 , 0.85098039215686272 , 0.9137254901960784 ),
    (0.45490196078431372, 0.67843137254901964 , 0.81960784313725488),
    (0.27058823529411763, 0.45882352941176469 , 0.70588235294117652),
    (0.19215686274509805, 0.21176470588235294 , 0.58431372549019611)
    )

_RdYlGn_data = (
    (0.6470588235294118 , 0.0                 , 0.14901960784313725),
    (0.84313725490196079, 0.18823529411764706 , 0.15294117647058825),
    (0.95686274509803926, 0.42745098039215684 , 0.2627450980392157 ),
    (0.99215686274509807, 0.68235294117647061 , 0.38039215686274508),
    (0.99607843137254903, 0.8784313725490196  , 0.54509803921568623),
    (1.0                , 1.0                 , 0.74901960784313726),
    (0.85098039215686272, 0.93725490196078431 , 0.54509803921568623),
    (0.65098039215686276, 0.85098039215686272 , 0.41568627450980394),
    (0.4                , 0.74117647058823533 , 0.38823529411764707),
    (0.10196078431372549, 0.59607843137254901 , 0.31372549019607843),
    (0.0                , 0.40784313725490196 , 0.21568627450980393)
    )

_Reds_data = (
    (1.0                , 0.96078431372549022 , 0.94117647058823528),
    (0.99607843137254903, 0.8784313725490196  , 0.82352941176470584),
    (0.9882352941176471 , 0.73333333333333328 , 0.63137254901960782),
    (0.9882352941176471 , 0.5725490196078431  , 0.44705882352941179),
    (0.98431372549019602, 0.41568627450980394 , 0.29019607843137257),
    (0.93725490196078431, 0.23137254901960785 , 0.17254901960784313),
    (0.79607843137254897, 0.094117647058823528, 0.11372549019607843),
    (0.6470588235294118 , 0.058823529411764705, 0.08235294117647058),
    (0.40392156862745099, 0.0                 , 0.05098039215686274)
    )

_Spectral_data = (
    (0.61960784313725492, 0.003921568627450980, 0.25882352941176473),
    (0.83529411764705885, 0.24313725490196078 , 0.30980392156862746),
    (0.95686274509803926, 0.42745098039215684 , 0.2627450980392157 ),
    (0.99215686274509807, 0.68235294117647061 , 0.38039215686274508),
    (0.99607843137254903, 0.8784313725490196  , 0.54509803921568623),
    (1.0                , 1.0                 , 0.74901960784313726),
    (0.90196078431372551, 0.96078431372549022 , 0.59607843137254901),
    (0.6705882352941176 , 0.8666666666666667  , 0.64313725490196083),
    (0.4                , 0.76078431372549016 , 0.6470588235294118 ),
    (0.19607843137254902, 0.53333333333333333 , 0.74117647058823533),
    (0.36862745098039218, 0.30980392156862746 , 0.63529411764705879)
    )

_YlGn_data = (
    (1.0                , 1.0                 , 0.89803921568627454),
    (0.96862745098039216, 0.9882352941176471  , 0.72549019607843135),
    (0.85098039215686272, 0.94117647058823528 , 0.63921568627450975),
    (0.67843137254901964, 0.8666666666666667  , 0.55686274509803924),
    (0.47058823529411764, 0.77647058823529413 , 0.47450980392156861),
    (0.25490196078431371, 0.6705882352941176  , 0.36470588235294116),
    (0.13725490196078433, 0.51764705882352946 , 0.2627450980392157 ),
    (0.0                , 0.40784313725490196 , 0.21568627450980393),
    (0.0                , 0.27058823529411763 , 0.16078431372549021)
    )

_YlGnBu_data = (
    (1.0                , 1.0                 , 0.85098039215686272),
    (0.92941176470588238, 0.97254901960784312 , 0.69411764705882351),
    (0.7803921568627451 , 0.9137254901960784  , 0.70588235294117652),
    (0.49803921568627452, 0.80392156862745101 , 0.73333333333333328),
    (0.25490196078431371, 0.71372549019607845 , 0.7686274509803922 ),
    (0.11372549019607843, 0.56862745098039214 , 0.75294117647058822),
    (0.13333333333333333, 0.36862745098039218 , 0.6588235294117647 ),
    (0.14509803921568629, 0.20392156862745098 , 0.58039215686274515),
    (0.03137254901960784, 0.11372549019607843 , 0.34509803921568627)
    )

_YlOrBr_data = (
    (1.0                , 1.0                 , 0.89803921568627454),
    (1.0                , 0.96862745098039216 , 0.73725490196078436),
    (0.99607843137254903, 0.8901960784313725  , 0.56862745098039214),
    (0.99607843137254903, 0.7686274509803922  , 0.30980392156862746),
    (0.99607843137254903, 0.6                 , 0.16078431372549021),
    (0.92549019607843142, 0.4392156862745098  , 0.07843137254901961),
    (0.8                , 0.29803921568627451 , 0.00784313725490196),
    (0.6                , 0.20392156862745098 , 0.01568627450980392),
    (0.4                , 0.14509803921568629 , 0.02352941176470588)
    )

_YlOrRd_data = (
    (1.0                , 1.0                 , 0.8                ),
    (1.0                , 0.92941176470588238 , 0.62745098039215685),
    (0.99607843137254903, 0.85098039215686272 , 0.46274509803921571),
    (0.99607843137254903, 0.69803921568627447 , 0.29803921568627451),
    (0.99215686274509807, 0.55294117647058827 , 0.23529411764705882),
    (0.9882352941176471 , 0.30588235294117649 , 0.16470588235294117),
    (0.8901960784313725 , 0.10196078431372549 , 0.10980392156862745),
    (0.74117647058823533, 0.0                 , 0.14901960784313725),
    (0.50196078431372548, 0.0                 , 0.14901960784313725)
    )


# ColorBrewer's qualitative maps, implemented using ListedColormap
# for use with mpl.colors.NoNorm

_Accent_data = (
    (0.49803921568627452, 0.78823529411764703, 0.49803921568627452),
    (0.74509803921568629, 0.68235294117647061, 0.83137254901960789),
    (0.99215686274509807, 0.75294117647058822, 0.52549019607843139),
    (1.0,                 1.0,                 0.6                ),
    (0.2196078431372549,  0.42352941176470588, 0.69019607843137254),
    (0.94117647058823528, 0.00784313725490196, 0.49803921568627452),
    (0.74901960784313726, 0.35686274509803922, 0.09019607843137254),
    (0.4,                 0.4,                 0.4                ),
    )

_Dark2_data = (
    (0.10588235294117647, 0.61960784313725492, 0.46666666666666667),
    (0.85098039215686272, 0.37254901960784315, 0.00784313725490196),
    (0.45882352941176469, 0.4392156862745098,  0.70196078431372544),
    (0.90588235294117647, 0.16078431372549021, 0.54117647058823526),
    (0.4,                 0.65098039215686276, 0.11764705882352941),
    (0.90196078431372551, 0.6705882352941176,  0.00784313725490196),
    (0.65098039215686276, 0.46274509803921571, 0.11372549019607843),
    (0.4,                 0.4,                 0.4                ),
    )

_Paired_data = (
    (0.65098039215686276, 0.80784313725490198, 0.8901960784313725 ),
    (0.12156862745098039, 0.47058823529411764, 0.70588235294117652),
    (0.69803921568627447, 0.87450980392156863, 0.54117647058823526),
    (0.2,                 0.62745098039215685, 0.17254901960784313),
    (0.98431372549019602, 0.60392156862745094, 0.6                ),
    (0.8901960784313725,  0.10196078431372549, 0.10980392156862745),
    (0.99215686274509807, 0.74901960784313726, 0.43529411764705883),
    (1.0,                 0.49803921568627452, 0.0                ),
    (0.792156862745098,   0.69803921568627447, 0.83921568627450982),
    (0.41568627450980394, 0.23921568627450981, 0.60392156862745094),
    (1.0,                 1.0,                 0.6                ),
    (0.69411764705882351, 0.34901960784313724, 0.15686274509803921),
    )

_Pastel1_data = (
    (0.98431372549019602, 0.70588235294117652, 0.68235294117647061),
    (0.70196078431372544, 0.80392156862745101, 0.8901960784313725 ),
    (0.8,                 0.92156862745098034, 0.77254901960784317),
    (0.87058823529411766, 0.79607843137254897, 0.89411764705882357),
    (0.99607843137254903, 0.85098039215686272, 0.65098039215686276),
    (1.0,                 1.0,                 0.8                ),
    (0.89803921568627454, 0.84705882352941175, 0.74117647058823533),
    (0.99215686274509807, 0.85490196078431369, 0.92549019607843142),
    (0.94901960784313721, 0.94901960784313721, 0.94901960784313721),
    )

_Pastel2_data = (
    (0.70196078431372544, 0.88627450980392153, 0.80392156862745101),
    (0.99215686274509807, 0.80392156862745101, 0.67450980392156867),
    (0.79607843137254897, 0.83529411764705885, 0.90980392156862744),
    (0.95686274509803926, 0.792156862745098,   0.89411764705882357),
    (0.90196078431372551, 0.96078431372549022, 0.78823529411764703),
    (1.0,                 0.94901960784313721, 0.68235294117647061),
    (0.94509803921568625, 0.88627450980392153, 0.8                ),
    (0.8,                 0.8,                 0.8                ),
    )

_Set1_data = (
    (0.89411764705882357, 0.10196078431372549, 0.10980392156862745),
    (0.21568627450980393, 0.49411764705882355, 0.72156862745098038),
    (0.30196078431372547, 0.68627450980392157, 0.29019607843137257),
    (0.59607843137254901, 0.30588235294117649, 0.63921568627450975),
    (1.0,                 0.49803921568627452, 0.0                ),
    (1.0,                 1.0,                 0.2                ),
    (0.65098039215686276, 0.33725490196078434, 0.15686274509803921),
    (0.96862745098039216, 0.50588235294117645, 0.74901960784313726),
    (0.6,                 0.6,                 0.6),
    )

_Set2_data = (
    (0.4,                 0.76078431372549016, 0.6470588235294118 ),
    (0.9882352941176471,  0.55294117647058827, 0.3843137254901961 ),
    (0.55294117647058827, 0.62745098039215685, 0.79607843137254897),
    (0.90588235294117647, 0.54117647058823526, 0.76470588235294112),
    (0.65098039215686276, 0.84705882352941175, 0.32941176470588235),
    (1.0,                 0.85098039215686272, 0.18431372549019609),
    (0.89803921568627454, 0.7686274509803922,  0.58039215686274515),
    (0.70196078431372544, 0.70196078431372544, 0.70196078431372544),
    )

_Set3_data = (
    (0.55294117647058827, 0.82745098039215681, 0.7803921568627451 ),
    (1.0,                 1.0,                 0.70196078431372544),
    (0.74509803921568629, 0.72941176470588232, 0.85490196078431369),
    (0.98431372549019602, 0.50196078431372548, 0.44705882352941179),
    (0.50196078431372548, 0.69411764705882351, 0.82745098039215681),
    (0.99215686274509807, 0.70588235294117652, 0.3843137254901961 ),
    (0.70196078431372544, 0.87058823529411766, 0.41176470588235292),
    (0.9882352941176471,  0.80392156862745101, 0.89803921568627454),
    (0.85098039215686272, 0.85098039215686272, 0.85098039215686272),
    (0.73725490196078436, 0.50196078431372548, 0.74117647058823533),
    (0.8,                 0.92156862745098034, 0.77254901960784317),
    (1.0,                 0.92941176470588238, 0.43529411764705883),
    )


# The next 7 palettes are from the Yorick scientific visualization package,
# an evolution of the GIST package, both by David H. Munro.
# They are released under a BSD-like license (see LICENSE_YORICK in
# the license directory of the matplotlib source distribution).
#
# Most palette functions have been reduced to simple function descriptions
# by Reinier Heeres, since the rgb components were mostly straight lines.
# gist_earth_data and gist_ncar_data were simplified by a script and some
# manual effort.

_gist_earth_data = {
    'red': (
        (0.0, 0.0, 0.0000),
        (0.2824, 0.1882, 0.1882),
        (0.4588, 0.2714, 0.2714),
        (0.5490, 0.4719, 0.4719),
        (0.6980, 0.7176, 0.7176),
        (0.7882, 0.7553, 0.7553),
        (1.0000, 0.9922, 0.9922),
    ),
    'green': (
        (0.0, 0.0, 0.0000),
        (0.0275, 0.0000, 0.0000),
        (0.1098, 0.1893, 0.1893),
        (0.1647, 0.3035, 0.3035),
        (0.2078, 0.3841, 0.3841),
        (0.2824, 0.5020, 0.5020),
        (0.5216, 0.6397, 0.6397),
        (0.6980, 0.7171, 0.7171),
        (0.7882, 0.6392, 0.6392),
        (0.7922, 0.6413, 0.6413),
        (0.8000, 0.6447, 0.6447),
        (0.8078, 0.6481, 0.6481),
        (0.8157, 0.6549, 0.6549),
        (0.8667, 0.6991, 0.6991),
        (0.8745, 0.7103, 0.7103),
        (0.8824, 0.7216, 0.7216),
        (0.8902, 0.7323, 0.7323),
        (0.8980, 0.7430, 0.7430),
        (0.9412, 0.8275, 0.8275),
        (0.9569, 0.8635, 0.8635),
        (0.9647, 0.8816, 0.8816),
        (0.9961, 0.9733, 0.9733),
        (1.0000, 0.9843, 0.9843),
    ),
    'blue': (
        (0.0, 0.0, 0.0000),
        (0.0039, 0.1684, 0.1684),
        (0.0078, 0.2212, 0.2212),
        (0.0275, 0.4329, 0.4329),
        (0.0314, 0.4549, 0.4549),
        (0.2824, 0.5004, 0.5004),
        (0.4667, 0.2748, 0.2748),
        (0.5451, 0.3205, 0.3205),
        (0.7843, 0.3961, 0.3961),
        (0.8941, 0.6651, 0.6651),
        (1.0000, 0.9843, 0.9843),
    )
}

_gist_gray_data = {
        'red': gfunc[3],
        'green': gfunc[3],
        'blue': gfunc[3],
}

def _gist_heat_red(x): return 1.5 * x
def _gist_heat_green(x): return 2 * x - 1
def _gist_heat_blue(x): return 4 * x - 3
_gist_heat_data = {
    'red': _gist_heat_red, 'green': _gist_heat_green, 'blue': _gist_heat_blue}

_gist_ncar_data = {
    'red': (
        (0.0, 0.0, 0.0000),
        (0.3098, 0.0000, 0.0000),
        (0.3725, 0.3993, 0.3993),
        (0.4235, 0.5003, 0.5003),
        (0.5333, 1.0000, 1.0000),
        (0.7922, 1.0000, 1.0000),
        (0.8471, 0.6218, 0.6218),
        (0.8980, 0.9235, 0.9235),
        (1.0000, 0.9961, 0.9961),
    ),
    'green': (
        (0.0, 0.0, 0.0000),
        (0.0510, 0.3722, 0.3722),
        (0.1059, 0.0000, 0.0000),
        (0.1569, 0.7202, 0.7202),
        (0.1608, 0.7537, 0.7537),
        (0.1647, 0.7752, 0.7752),
        (0.2157, 1.0000, 1.0000),
        (0.2588, 0.9804, 0.9804),
        (0.2706, 0.9804, 0.9804),
        (0.3176, 1.0000, 1.0000),
        (0.3686, 0.8081, 0.8081),
        (0.4275, 1.0000, 1.0000),
        (0.5216, 1.0000, 1.0000),
        (0.6314, 0.7292, 0.7292),
        (0.6863, 0.2796, 0.2796),
        (0.7451, 0.0000, 0.0000),
        (0.7922, 0.0000, 0.0000),
        (0.8431, 0.1753, 0.1753),
        (0.8980, 0.5000, 0.5000),
        (1.0000, 0.9725, 0.9725),
    ),
    'blue': (
        (0.0, 0.5020, 0.5020),
        (0.0510, 0.0222, 0.0222),
        (0.1098, 1.0000, 1.0000),
        (0.2039, 1.0000, 1.0000),
        (0.2627, 0.6145, 0.6145),
        (0.3216, 0.0000, 0.0000),
        (0.4157, 0.0000, 0.0000),
        (0.4745, 0.2342, 0.2342),
        (0.5333, 0.0000, 0.0000),
        (0.5804, 0.0000, 0.0000),
        (0.6314, 0.0549, 0.0549),
        (0.6902, 0.0000, 0.0000),
        (0.7373, 0.0000, 0.0000),
        (0.7922, 0.9738, 0.9738),
        (0.8000, 1.0000, 1.0000),
        (0.8431, 1.0000, 1.0000),
        (0.8980, 0.9341, 0.9341),
        (1.0000, 0.9961, 0.9961),
    )
}

_gist_rainbow_data = (
        (0.000, (1.00, 0.00, 0.16)),
        (0.030, (1.00, 0.00, 0.00)),
        (0.215, (1.00, 1.00, 0.00)),
        (0.400, (0.00, 1.00, 0.00)),
        (0.586, (0.00, 1.00, 1.00)),
        (0.770, (0.00, 0.00, 1.00)),
        (0.954, (1.00, 0.00, 1.00)),
        (1.000, (1.00, 0.00, 0.75))
)

_gist_stern_data = {
        'red': (
            (0.000, 0.000, 0.000), (0.0547, 1.000, 1.000),
            (0.250, 0.027, 0.250),  # (0.2500, 0.250, 0.250),
            (1.000, 1.000, 1.000)),
        'green': ((0, 0, 0), (1, 1, 1)),
        'blue': (
            (0.000, 0.000, 0.000), (0.500, 1.000, 1.000),
            (0.735, 0.000, 0.000), (1.000, 1.000, 1.000))
}

def _gist_yarg(x): return 1 - x
_gist_yarg_data = {'red': _gist_yarg, 'green': _gist_yarg, 'blue': _gist_yarg}

# This bipolar colormap was generated from CoolWarmFloat33.csv of
# "Diverging Color Maps for Scientific Visualization" by Kenneth Moreland.
# <http://www.kennethmoreland.com/color-maps/>
_coolwarm_data = {
    'red': [
        (0.0, 0.2298057, 0.2298057),
        (0.03125, 0.26623388, 0.26623388),
        (0.0625, 0.30386891, 0.30386891),
        (0.09375, 0.342804478, 0.342804478),
        (0.125, 0.38301334, 0.38301334),
        (0.15625, 0.424369608, 0.424369608),
        (0.1875, 0.46666708, 0.46666708),
        (0.21875, 0.509635204, 0.509635204),
        (0.25, 0.552953156, 0.552953156),
        (0.28125, 0.596262162, 0.596262162),
        (0.3125, 0.639176211, 0.639176211),
        (0.34375, 0.681291281, 0.681291281),
        (0.375, 0.722193294, 0.722193294),
        (0.40625, 0.761464949, 0.761464949),
        (0.4375, 0.798691636, 0.798691636),
        (0.46875, 0.833466556, 0.833466556),
        (0.5, 0.865395197, 0.865395197),
        (0.53125, 0.897787179, 0.897787179),
        (0.5625, 0.924127593, 0.924127593),
        (0.59375, 0.944468518, 0.944468518),
        (0.625, 0.958852946, 0.958852946),
        (0.65625, 0.96732803, 0.96732803),
        (0.6875, 0.969954137, 0.969954137),
        (0.71875, 0.966811177, 0.966811177),
        (0.75, 0.958003065, 0.958003065),
        (0.78125, 0.943660866, 0.943660866),
        (0.8125, 0.923944917, 0.923944917),
        (0.84375, 0.89904617, 0.89904617),
        (0.875, 0.869186849, 0.869186849),
        (0.90625, 0.834620542, 0.834620542),
        (0.9375, 0.795631745, 0.795631745),
        (0.96875, 0.752534934, 0.752534934),
        (1.0, 0.705673158, 0.705673158)],
    'green': [
        (0.0, 0.298717966, 0.298717966),
        (0.03125, 0.353094838, 0.353094838),
        (0.0625, 0.406535296, 0.406535296),
        (0.09375, 0.458757618, 0.458757618),
        (0.125, 0.50941904, 0.50941904),
        (0.15625, 0.558148092, 0.558148092),
        (0.1875, 0.604562568, 0.604562568),
        (0.21875, 0.648280772, 0.648280772),
        (0.25, 0.688929332, 0.688929332),
        (0.28125, 0.726149107, 0.726149107),
        (0.3125, 0.759599947, 0.759599947),
        (0.34375, 0.788964712, 0.788964712),
        (0.375, 0.813952739, 0.813952739),
        (0.40625, 0.834302879, 0.834302879),
        (0.4375, 0.849786142, 0.849786142),
        (0.46875, 0.860207984, 0.860207984),
        (0.5, 0.86541021, 0.86541021),
        (0.53125, 0.848937047, 0.848937047),
        (0.5625, 0.827384882, 0.827384882),
        (0.59375, 0.800927443, 0.800927443),
        (0.625, 0.769767752, 0.769767752),
        (0.65625, 0.734132809, 0.734132809),
        (0.6875, 0.694266682, 0.694266682),
        (0.71875, 0.650421156, 0.650421156),
        (0.75, 0.602842431, 0.602842431),
        (0.78125, 0.551750968, 0.551750968),
        (0.8125, 0.49730856, 0.49730856),
        (0.84375, 0.439559467, 0.439559467),
        (0.875, 0.378313092, 0.378313092),
        (0.90625, 0.312874446, 0.312874446),
        (0.9375, 0.24128379, 0.24128379),
        (0.96875, 0.157246067, 0.157246067),
        (1.0, 0.01555616, 0.01555616)],
    'blue': [
        (0.0, 0.753683153, 0.753683153),
        (0.03125, 0.801466763, 0.801466763),
        (0.0625, 0.84495867, 0.84495867),
        (0.09375, 0.883725899, 0.883725899),
        (0.125, 0.917387822, 0.917387822),
        (0.15625, 0.945619588, 0.945619588),
        (0.1875, 0.968154911, 0.968154911),
        (0.21875, 0.98478814, 0.98478814),
        (0.25, 0.995375608, 0.995375608),
        (0.28125, 0.999836203, 0.999836203),
        (0.3125, 0.998151185, 0.998151185),
        (0.34375, 0.990363227, 0.990363227),
        (0.375, 0.976574709, 0.976574709),
        (0.40625, 0.956945269, 0.956945269),
        (0.4375, 0.931688648, 0.931688648),
        (0.46875, 0.901068838, 0.901068838),
        (0.5, 0.865395561, 0.865395561),
        (0.53125, 0.820880546, 0.820880546),
        (0.5625, 0.774508472, 0.774508472),
        (0.59375, 0.726736146, 0.726736146),
        (0.625, 0.678007945, 0.678007945),
        (0.65625, 0.628751763, 0.628751763),
        (0.6875, 0.579375448, 0.579375448),
        (0.71875, 0.530263762, 0.530263762),
        (0.75, 0.481775914, 0.481775914),
        (0.78125, 0.434243684, 0.434243684),
        (0.8125, 0.387970225, 0.387970225),
        (0.84375, 0.343229596, 0.343229596),
        (0.875, 0.300267182, 0.300267182),
        (0.90625, 0.259301199, 0.259301199),
        (0.9375, 0.220525627, 0.220525627),
        (0.96875, 0.184115123, 0.184115123),
        (1.0, 0.150232812, 0.150232812)]
    }

# Implementation of Carey Rappaport's CMRmap.
# See `A Color Map for Effective Black-and-White Rendering of Color-Scale
# Images' by Carey Rappaport
# https://www.mathworks.com/matlabcentral/fileexchange/2662-cmrmap-m
_CMRmap_data = {'red':    ((0.000, 0.00, 0.00),
                           (0.125, 0.15, 0.15),
                           (0.250, 0.30, 0.30),
                           (0.375, 0.60, 0.60),
                           (0.500, 1.00, 1.00),
                           (0.625, 0.90, 0.90),
                           (0.750, 0.90, 0.90),
                           (0.875, 0.90, 0.90),
                           (1.000, 1.00, 1.00)),
                'green':  ((0.000, 0.00, 0.00),
                           (0.125, 0.15, 0.15),
                           (0.250, 0.15, 0.15),
                           (0.375, 0.20, 0.20),
                           (0.500, 0.25, 0.25),
                           (0.625, 0.50, 0.50),
                           (0.750, 0.75, 0.75),
                           (0.875, 0.90, 0.90),
                           (1.000, 1.00, 1.00)),
                'blue':   ((0.000, 0.00, 0.00),
                           (0.125, 0.50, 0.50),
                           (0.250, 0.75, 0.75),
                           (0.375, 0.50, 0.50),
                           (0.500, 0.15, 0.15),
                           (0.625, 0.00, 0.00),
                           (0.750, 0.10, 0.10),
                           (0.875, 0.50, 0.50),
                           (1.000, 1.00, 1.00))}


# An MIT licensed, colorblind-friendly heatmap from Wistia:
#   https://github.com/wistia/heatmap-palette
#   https://wistia.com/learn/culture/heatmaps-for-colorblindness
#
# >>> import matplotlib.colors as c
# >>> colors = ["#e4ff7a", "#ffe81a", "#ffbd00", "#ffa000", "#fc7f00"]
# >>> cm = c.LinearSegmentedColormap.from_list('wistia', colors)
# >>> _wistia_data = cm._segmentdata
# >>> del _wistia_data['alpha']
#
_wistia_data = {
    'red': [(0.0, 0.8941176470588236, 0.8941176470588236),
            (0.25, 1.0, 1.0),
            (0.5, 1.0, 1.0),
            (0.75, 1.0, 1.0),
            (1.0, 0.9882352941176471, 0.9882352941176471)],
    'green': [(0.0, 1.0, 1.0),
              (0.25, 0.9098039215686274, 0.9098039215686274),
              (0.5, 0.7411764705882353, 0.7411764705882353),
              (0.75, 0.6274509803921569, 0.6274509803921569),
              (1.0, 0.4980392156862745, 0.4980392156862745)],
    'blue': [(0.0, 0.47843137254901963, 0.47843137254901963),
             (0.25, 0.10196078431372549, 0.10196078431372549),
             (0.5, 0.0, 0.0),
             (0.75, 0.0, 0.0),
             (1.0, 0.0, 0.0)],
}


# Categorical palettes from Vega:
# https://github.com/vega/vega/wiki/Scales
# (divided by 255)
#

_tab10_data = (
    (0.12156862745098039, 0.4666666666666667,  0.7058823529411765  ),  # 1f77b4
    (1.0,                 0.4980392156862745,  0.054901960784313725),  # ff7f0e
    (0.17254901960784313, 0.6274509803921569,  0.17254901960784313 ),  # 2ca02c
    (0.8392156862745098,  0.15294117647058825, 0.1568627450980392  ),  # d62728
    (0.5803921568627451,  0.403921568627451,   0.7411764705882353  ),  # 9467bd
    (0.5490196078431373,  0.33725490196078434, 0.29411764705882354 ),  # 8c564b
    (0.8901960784313725,  0.4666666666666667,  0.7607843137254902  ),  # e377c2
    (0.4980392156862745,  0.4980392156862745,  0.4980392156862745  ),  # 7f7f7f
    (0.7372549019607844,  0.7411764705882353,  0.13333333333333333 ),  # bcbd22
    (0.09019607843137255, 0.7450980392156863,  0.8117647058823529),    # 17becf
)

_tab20_data = (
    (0.12156862745098039, 0.4666666666666667,  0.7058823529411765  ),  # 1f77b4
    (0.6823529411764706,  0.7803921568627451,  0.9098039215686274  ),  # aec7e8
    (1.0,                 0.4980392156862745,  0.054901960784313725),  # ff7f0e
    (1.0,                 0.7333333333333333,  0.47058823529411764 ),  # ffbb78
    (0.17254901960784313, 0.6274509803921569,  0.17254901960784313 ),  # 2ca02c
    (0.596078431372549,   0.8745098039215686,  0.5411764705882353  ),  # 98df8a
    (0.8392156862745098,  0.15294117647058825, 0.1568627450980392  ),  # d62728
    (1.0,                 0.596078431372549,   0.5882352941176471  ),  # ff9896
    (0.5803921568627451,  0.403921568627451,   0.7411764705882353  ),  # 9467bd
    (0.7725490196078432,  0.6901960784313725,  0.8352941176470589  ),  # c5b0d5
    (0.5490196078431373,  0.33725490196078434, 0.29411764705882354 ),  # 8c564b
    (0.7686274509803922,  0.611764705882353,   0.5803921568627451  ),  # c49c94
    (0.8901960784313725,  0.4666666666666667,  0.7607843137254902  ),  # e377c2
    (0.9686274509803922,  0.7137254901960784,  0.8235294117647058  ),  # f7b6d2
    (0.4980392156862745,  0.4980392156862745,  0.4980392156862745  ),  # 7f7f7f
    (0.7803921568627451,  0.7803921568627451,  0.7803921568627451  ),  # c7c7c7
    (0.7372549019607844,  0.7411764705882353,  0.13333333333333333 ),  # bcbd22
    (0.8588235294117647,  0.8588235294117647,  0.5529411764705883  ),  # dbdb8d
    (0.09019607843137255, 0.7450980392156863,  0.8117647058823529  ),  # 17becf
    (0.6196078431372549,  0.8549019607843137,  0.8980392156862745),    # 9edae5
)

_tab20b_data = (
    (0.2235294117647059,  0.23137254901960785, 0.4745098039215686 ),  # 393b79
    (0.3215686274509804,  0.32941176470588235, 0.6392156862745098 ),  # 5254a3
    (0.4196078431372549,  0.43137254901960786, 0.8117647058823529 ),  # 6b6ecf
    (0.611764705882353,   0.6196078431372549,  0.8705882352941177 ),  # 9c9ede
    (0.38823529411764707, 0.4745098039215686,  0.2235294117647059 ),  # 637939
    (0.5490196078431373,  0.6352941176470588,  0.3215686274509804 ),  # 8ca252
    (0.7098039215686275,  0.8117647058823529,  0.4196078431372549 ),  # b5cf6b
    (0.807843137254902,   0.8588235294117647,  0.611764705882353  ),  # cedb9c
    (0.5490196078431373,  0.42745098039215684, 0.19215686274509805),  # 8c6d31
    (0.7411764705882353,  0.6196078431372549,  0.2235294117647059 ),  # bd9e39
    (0.9058823529411765,  0.7294117647058823,  0.3215686274509804 ),  # e7ba52
    (0.9058823529411765,  0.796078431372549,   0.5803921568627451 ),  # e7cb94
    (0.5176470588235295,  0.23529411764705882, 0.2235294117647059 ),  # 843c39
    (0.6784313725490196,  0.28627450980392155, 0.2901960784313726 ),  # ad494a
    (0.8392156862745098,  0.3803921568627451,  0.4196078431372549 ),  # d6616b
    (0.9058823529411765,  0.5882352941176471,  0.611764705882353  ),  # e7969c
    (0.4823529411764706,  0.2549019607843137,  0.45098039215686275),  # 7b4173
    (0.6470588235294118,  0.3176470588235294,  0.5803921568627451 ),  # a55194
    (0.807843137254902,   0.42745098039215684, 0.7411764705882353 ),  # ce6dbd
    (0.8705882352941177,  0.6196078431372549,  0.8392156862745098 ),  # de9ed6
)

_tab20c_data = (
    (0.19215686274509805, 0.5098039215686274,  0.7411764705882353  ),  # 3182bd
    (0.4196078431372549,  0.6823529411764706,  0.8392156862745098  ),  # 6baed6
    (0.6196078431372549,  0.792156862745098,   0.8823529411764706  ),  # 9ecae1
    (0.7764705882352941,  0.8588235294117647,  0.9372549019607843  ),  # c6dbef
    (0.9019607843137255,  0.3333333333333333,  0.050980392156862744),  # e6550d
    (0.9921568627450981,  0.5529411764705883,  0.23529411764705882 ),  # fd8d3c
    (0.9921568627450981,  0.6823529411764706,  0.4196078431372549  ),  # fdae6b
    (0.9921568627450981,  0.8156862745098039,  0.6352941176470588  ),  # fdd0a2
    (0.19215686274509805, 0.6392156862745098,  0.32941176470588235 ),  # 31a354
    (0.4549019607843137,  0.7686274509803922,  0.4627450980392157  ),  # 74c476
    (0.6313725490196078,  0.8509803921568627,  0.6078431372549019  ),  # a1d99b
    (0.7803921568627451,  0.9137254901960784,  0.7529411764705882  ),  # c7e9c0
    (0.4588235294117647,  0.4196078431372549,  0.6941176470588235  ),  # 756bb1
    (0.6196078431372549,  0.6039215686274509,  0.7843137254901961  ),  # 9e9ac8
    (0.7372549019607844,  0.7411764705882353,  0.8627450980392157  ),  # bcbddc
    (0.8549019607843137,  0.8549019607843137,  0.9215686274509803  ),  # dadaeb
    (0.38823529411764707, 0.38823529411764707, 0.38823529411764707 ),  # 636363
    (0.5882352941176471,  0.5882352941176471,  0.5882352941176471  ),  # 969696
    (0.7411764705882353,  0.7411764705882353,  0.7411764705882353  ),  # bdbdbd
    (0.8509803921568627,  0.8509803921568627,  0.8509803921568627  ),  # d9d9d9
)


_petroff10_data = (
    (0.24705882352941178, 0.5647058823529412,  0.8549019607843137),    # 3f90da
    (1.0,                 0.6627450980392157,  0.054901960784313725),  # ffa90e
    (0.7411764705882353,  0.12156862745098039, 0.00392156862745098),   # bd1f01
    (0.5803921568627451,  0.6431372549019608,  0.6352941176470588),    # 94a4a2
    (0.5137254901960784,  0.17647058823529413, 0.7137254901960784),    # 832db6
    (0.6627450980392157,  0.4196078431372549,  0.34901960784313724),   # a96b59
    (0.9058823529411765,  0.38823529411764707, 0.0),                   # e76300
    (0.7254901960784313,  0.6745098039215687,  0.4392156862745098),    # b9ac70
    (0.44313725490196076, 0.4588235294117647,  0.5058823529411764),    # 717581
    (0.5725490196078431,  0.8549019607843137,  0.8666666666666667),    # 92dadd
)


datad = {
    'Blues': _Blues_data,
    'BrBG': _BrBG_data,
    'BuGn': _BuGn_data,
    'BuPu': _BuPu_data,
    'CMRmap': _CMRmap_data,
    'GnBu': _GnBu_data,
    'Greens': _Greens_data,
    'Greys': _Greys_data,
    'OrRd': _OrRd_data,
    'Oranges': _Oranges_data,
    'PRGn': _PRGn_data,
    'PiYG': _PiYG_data,
    'PuBu': _PuBu_data,
    'PuBuGn': _PuBuGn_data,
    'PuOr': _PuOr_data,
    'PuRd': _PuRd_data,
    'Purples': _Purples_data,
    'RdBu': _RdBu_data,
    'RdGy': _RdGy_data,
    'RdPu': _RdPu_data,
    'RdYlBu': _RdYlBu_data,
    'RdYlGn': _RdYlGn_data,
    'Reds': _Reds_data,
    'Spectral': _Spectral_data,
    'Wistia': _wistia_data,
    'YlGn': _YlGn_data,
    'YlGnBu': _YlGnBu_data,
    'YlOrBr': _YlOrBr_data,
    'YlOrRd': _YlOrRd_data,
    'afmhot': _afmhot_data,
    'autumn': _autumn_data,
    'binary': _binary_data,
    'bone': _bone_data,
    'brg': _brg_data,
    'bwr': _bwr_data,
    'cool': _cool_data,
    'coolwarm': _coolwarm_data,
    'copper': _copper_data,
    'cubehelix': _cubehelix_data,
    'flag': _flag_data,
    'gist_earth': _gist_earth_data,
    'gist_gray': _gist_gray_data,
    'gist_heat': _gist_heat_data,
    'gist_ncar': _gist_ncar_data,
    'gist_rainbow': _gist_rainbow_data,
    'gist_stern': _gist_stern_data,
    'gist_yarg': _gist_yarg_data,
    'gnuplot': _gnuplot_data,
    'gnuplot2': _gnuplot2_data,
    'gray': _gray_data,
    'hot': _hot_data,
    'hsv': _hsv_data,
    'jet': _jet_data,
    'nipy_spectral': _nipy_spectral_data,
    'ocean': _ocean_data,
    'pink': _pink_data,
    'prism': _prism_data,
    'rainbow': _rainbow_data,
    'seismic': _seismic_data,
    'spring': _spring_data,
    'summer': _summer_data,
    'terrain': _terrain_data,
    'winter': _winter_data,
    # Qualitative
    'Accent': {'listed': _Accent_data},
    'Dark2': {'listed': _Dark2_data},
    'Paired': {'listed': _Paired_data},
    'Pastel1': {'listed': _Pastel1_data},
    'Pastel2': {'listed': _Pastel2_data},
    'Set1': {'listed': _Set1_data},
    'Set2': {'listed': _Set2_data},
    'Set3': {'listed': _Set3_data},
    'tab10': {'listed': _tab10_data},
    'tab20': {'listed': _tab20_data},
    'tab20b': {'listed': _tab20b_data},
    'tab20c': {'listed': _tab20c_data},
}

# === NexusCore/openenv\Lib\site-packages\nltk\sem\drt.py ===
# Natural Language Toolkit: Discourse Representation Theory (DRT)
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import operator
from functools import reduce
from itertools import chain

from nltk.sem.logic import (
    APP,
    AbstractVariableExpression,
    AllExpression,
    AndExpression,
    ApplicationExpression,
    BinaryExpression,
    BooleanExpression,
    ConstantExpression,
    EqualityExpression,
    EventVariableExpression,
    ExistsExpression,
    Expression,
    FunctionVariableExpression,
    ImpExpression,
    IndividualVariableExpression,
    LambdaExpression,
    LogicParser,
    NegatedExpression,
    OrExpression,
    Tokens,
    Variable,
    is_eventvar,
    is_funcvar,
    is_indvar,
    unique_variable,
)

# Import Tkinter-based modules if they are available
try:
    from tkinter import Canvas, Tk
    from tkinter.font import Font

    from nltk.util import in_idle

except ImportError:
    # No need to print a warning here, nltk.draw has already printed one.
    pass


class DrtTokens(Tokens):
    DRS = "DRS"
    DRS_CONC = "+"
    PRONOUN = "PRO"
    OPEN_BRACKET = "["
    CLOSE_BRACKET = "]"
    COLON = ":"

    PUNCT = [DRS_CONC, OPEN_BRACKET, CLOSE_BRACKET, COLON]

    SYMBOLS = Tokens.SYMBOLS + PUNCT

    TOKENS = Tokens.TOKENS + [DRS] + PUNCT


class DrtParser(LogicParser):
    """A lambda calculus expression parser."""

    def __init__(self):
        LogicParser.__init__(self)

        self.operator_precedence = dict(
            [(x, 1) for x in DrtTokens.LAMBDA_LIST]
            + [(x, 2) for x in DrtTokens.NOT_LIST]
            + [(APP, 3)]
            + [(x, 4) for x in DrtTokens.EQ_LIST + Tokens.NEQ_LIST]
            + [(DrtTokens.COLON, 5)]
            + [(DrtTokens.DRS_CONC, 6)]
            + [(x, 7) for x in DrtTokens.OR_LIST]
            + [(x, 8) for x in DrtTokens.IMP_LIST]
            + [(None, 9)]
        )

    def get_all_symbols(self):
        """This method exists to be overridden"""
        return DrtTokens.SYMBOLS

    def isvariable(self, tok):
        return tok not in DrtTokens.TOKENS

    def handle(self, tok, context):
        """This method is intended to be overridden for logics that
        use different operators or expressions"""
        if tok in DrtTokens.NOT_LIST:
            return self.handle_negation(tok, context)

        elif tok in DrtTokens.LAMBDA_LIST:
            return self.handle_lambda(tok, context)

        elif tok == DrtTokens.OPEN:
            if self.inRange(0) and self.token(0) == DrtTokens.OPEN_BRACKET:
                return self.handle_DRS(tok, context)
            else:
                return self.handle_open(tok, context)

        elif tok.upper() == DrtTokens.DRS:
            self.assertNextToken(DrtTokens.OPEN)
            return self.handle_DRS(tok, context)

        elif self.isvariable(tok):
            if self.inRange(0) and self.token(0) == DrtTokens.COLON:
                return self.handle_prop(tok, context)
            else:
                return self.handle_variable(tok, context)

    def make_NegatedExpression(self, expression):
        return DrtNegatedExpression(expression)

    def handle_DRS(self, tok, context):
        # a DRS
        refs = self.handle_refs()
        if (
            self.inRange(0) and self.token(0) == DrtTokens.COMMA
        ):  # if there is a comma (it's optional)
            self.token()  # swallow the comma
        conds = self.handle_conds(context)
        self.assertNextToken(DrtTokens.CLOSE)
        return DRS(refs, conds, None)

    def handle_refs(self):
        self.assertNextToken(DrtTokens.OPEN_BRACKET)
        refs = []
        while self.inRange(0) and self.token(0) != DrtTokens.CLOSE_BRACKET:
            # Support expressions like: DRS([x y],C) == DRS([x,y],C)
            if refs and self.token(0) == DrtTokens.COMMA:
                self.token()  # swallow the comma
            refs.append(self.get_next_token_variable("quantified"))
        self.assertNextToken(DrtTokens.CLOSE_BRACKET)
        return refs

    def handle_conds(self, context):
        self.assertNextToken(DrtTokens.OPEN_BRACKET)
        conds = []
        while self.inRange(0) and self.token(0) != DrtTokens.CLOSE_BRACKET:
            # Support expressions like: DRS([x y],C) == DRS([x, y],C)
            if conds and self.token(0) == DrtTokens.COMMA:
                self.token()  # swallow the comma
            conds.append(self.process_next_expression(context))
        self.assertNextToken(DrtTokens.CLOSE_BRACKET)
        return conds

    def handle_prop(self, tok, context):
        variable = self.make_VariableExpression(tok)
        self.assertNextToken(":")
        drs = self.process_next_expression(DrtTokens.COLON)
        return DrtProposition(variable, drs)

    def make_EqualityExpression(self, first, second):
        """This method serves as a hook for other logic parsers that
        have different equality expression classes"""
        return DrtEqualityExpression(first, second)

    def get_BooleanExpression_factory(self, tok):
        """This method serves as a hook for other logic parsers that
        have different boolean operators"""
        if tok == DrtTokens.DRS_CONC:
            return lambda first, second: DrtConcatenation(first, second, None)
        elif tok in DrtTokens.OR_LIST:
            return DrtOrExpression
        elif tok in DrtTokens.IMP_LIST:

            def make_imp_expression(first, second):
                if isinstance(first, DRS):
                    return DRS(first.refs, first.conds, second)
                if isinstance(first, DrtConcatenation):
                    return DrtConcatenation(first.first, first.second, second)
                raise Exception("Antecedent of implication must be a DRS")

            return make_imp_expression
        else:
            return None

    def make_BooleanExpression(self, factory, first, second):
        return factory(first, second)

    def make_ApplicationExpression(self, function, argument):
        return DrtApplicationExpression(function, argument)

    def make_VariableExpression(self, name):
        return DrtVariableExpression(Variable(name))

    def make_LambdaExpression(self, variables, term):
        return DrtLambdaExpression(variables, term)


class DrtExpression:
    """
    This is the base abstract DRT Expression from which every DRT
    Expression extends.
    """

    _drt_parser = DrtParser()

    @classmethod
    def fromstring(cls, s):
        return cls._drt_parser.parse(s)

    def applyto(self, other):
        return DrtApplicationExpression(self, other)

    def __neg__(self):
        return DrtNegatedExpression(self)

    def __and__(self, other):
        return NotImplemented

    def __or__(self, other):
        assert isinstance(other, DrtExpression)
        return DrtOrExpression(self, other)

    def __gt__(self, other):
        assert isinstance(other, DrtExpression)
        if isinstance(self, DRS):
            return DRS(self.refs, self.conds, other)
        if isinstance(self, DrtConcatenation):
            return DrtConcatenation(self.first, self.second, other)
        raise Exception("Antecedent of implication must be a DRS")

    def equiv(self, other, prover=None):
        """
        Check for logical equivalence.
        Pass the expression (self <-> other) to the theorem prover.
        If the prover says it is valid, then the self and other are equal.

        :param other: an ``DrtExpression`` to check equality against
        :param prover: a ``nltk.inference.api.Prover``
        """
        assert isinstance(other, DrtExpression)

        f1 = self.simplify().fol()
        f2 = other.simplify().fol()
        return f1.equiv(f2, prover)

    @property
    def type(self):
        raise AttributeError(
            "'%s' object has no attribute 'type'" % self.__class__.__name__
        )

    def typecheck(self, signature=None):
        raise NotImplementedError()

    def __add__(self, other):
        return DrtConcatenation(self, other, None)

    def get_refs(self, recursive=False):
        """
        Return the set of discourse referents in this DRS.
        :param recursive: bool Also find discourse referents in subterms?
        :return: list of ``Variable`` objects
        """
        raise NotImplementedError()

    def is_pronoun_function(self):
        """Is self of the form "PRO(x)"?"""
        return (
            isinstance(self, DrtApplicationExpression)
            and isinstance(self.function, DrtAbstractVariableExpression)
            and self.function.variable.name == DrtTokens.PRONOUN
            and isinstance(self.argument, DrtIndividualVariableExpression)
        )

    def make_EqualityExpression(self, first, second):
        return DrtEqualityExpression(first, second)

    def make_VariableExpression(self, variable):
        return DrtVariableExpression(variable)

    def resolve_anaphora(self):
        return resolve_anaphora(self)

    def eliminate_equality(self):
        return self.visit_structured(lambda e: e.eliminate_equality(), self.__class__)

    def pretty_format(self):
        """
        Draw the DRS
        :return: the pretty print string
        """
        return "\n".join(self._pretty())

    def pretty_print(self):
        print(self.pretty_format())

    def draw(self):
        DrsDrawer(self).draw()


class DRS(DrtExpression, Expression):
    """A Discourse Representation Structure."""

    def __init__(self, refs, conds, consequent=None):
        """
        :param refs: list of ``DrtIndividualVariableExpression`` for the
            discourse referents
        :param conds: list of ``Expression`` for the conditions
        """
        self.refs = refs
        self.conds = conds
        self.consequent = consequent

    def replace(self, variable, expression, replace_bound=False, alpha_convert=True):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        if variable in self.refs:
            # if a bound variable is the thing being replaced
            if not replace_bound:
                return self
            else:
                i = self.refs.index(variable)
                if self.consequent:
                    consequent = self.consequent.replace(
                        variable, expression, True, alpha_convert
                    )
                else:
                    consequent = None
                return DRS(
                    self.refs[:i] + [expression.variable] + self.refs[i + 1 :],
                    [
                        cond.replace(variable, expression, True, alpha_convert)
                        for cond in self.conds
                    ],
                    consequent,
                )
        else:
            if alpha_convert:
                # any bound variable that appears in the expression must
                # be alpha converted to avoid a conflict
                for ref in set(self.refs) & expression.free():
                    newvar = unique_variable(ref)
                    newvarex = DrtVariableExpression(newvar)
                    i = self.refs.index(ref)
                    if self.consequent:
                        consequent = self.consequent.replace(
                            ref, newvarex, True, alpha_convert
                        )
                    else:
                        consequent = None
                    self = DRS(
                        self.refs[:i] + [newvar] + self.refs[i + 1 :],
                        [
                            cond.replace(ref, newvarex, True, alpha_convert)
                            for cond in self.conds
                        ],
                        consequent,
                    )

            # replace in the conditions
            if self.consequent:
                consequent = self.consequent.replace(
                    variable, expression, replace_bound, alpha_convert
                )
            else:
                consequent = None
            return DRS(
                self.refs,
                [
                    cond.replace(variable, expression, replace_bound, alpha_convert)
                    for cond in self.conds
                ],
                consequent,
            )

    def free(self):
        """:see: Expression.free()"""
        conds_free = reduce(operator.or_, [c.free() for c in self.conds], set())
        if self.consequent:
            conds_free.update(self.consequent.free())
        return conds_free - set(self.refs)

    def get_refs(self, recursive=False):
        """:see: AbstractExpression.get_refs()"""
        if recursive:
            conds_refs = self.refs + list(
                chain.from_iterable(c.get_refs(True) for c in self.conds)
            )
            if self.consequent:
                conds_refs.extend(self.consequent.get_refs(True))
            return conds_refs
        else:
            return self.refs

    def visit(self, function, combinator):
        """:see: Expression.visit()"""
        parts = list(map(function, self.conds))
        if self.consequent:
            parts.append(function(self.consequent))
        return combinator(parts)

    def visit_structured(self, function, combinator):
        """:see: Expression.visit_structured()"""
        consequent = function(self.consequent) if self.consequent else None
        return combinator(self.refs, list(map(function, self.conds)), consequent)

    def eliminate_equality(self):
        drs = self
        i = 0
        while i < len(drs.conds):
            cond = drs.conds[i]
            if (
                isinstance(cond, EqualityExpression)
                and isinstance(cond.first, AbstractVariableExpression)
                and isinstance(cond.second, AbstractVariableExpression)
            ):
                drs = DRS(
                    list(set(drs.refs) - {cond.second.variable}),
                    drs.conds[:i] + drs.conds[i + 1 :],
                    drs.consequent,
                )
                if cond.second.variable != cond.first.variable:
                    drs = drs.replace(cond.second.variable, cond.first, False, False)
                    i = 0
                i -= 1
            i += 1

        conds = []
        for cond in drs.conds:
            new_cond = cond.eliminate_equality()
            new_cond_simp = new_cond.simplify()
            if (
                not isinstance(new_cond_simp, DRS)
                or new_cond_simp.refs
                or new_cond_simp.conds
                or new_cond_simp.consequent
            ):
                conds.append(new_cond)

        consequent = drs.consequent.eliminate_equality() if drs.consequent else None
        return DRS(drs.refs, conds, consequent)

    def fol(self):
        if self.consequent:
            accum = None
            if self.conds:
                accum = reduce(AndExpression, [c.fol() for c in self.conds])

            if accum:
                accum = ImpExpression(accum, self.consequent.fol())
            else:
                accum = self.consequent.fol()

            for ref in self.refs[::-1]:
                accum = AllExpression(ref, accum)

            return accum

        else:
            if not self.conds:
                raise Exception("Cannot convert DRS with no conditions to FOL.")
            accum = reduce(AndExpression, [c.fol() for c in self.conds])
            for ref in map(Variable, self._order_ref_strings(self.refs)[::-1]):
                accum = ExistsExpression(ref, accum)
            return accum

    def _pretty(self):
        refs_line = " ".join(self._order_ref_strings(self.refs))

        cond_lines = [
            cond
            for cond_line in [
                filter(lambda s: s.strip(), cond._pretty()) for cond in self.conds
            ]
            for cond in cond_line
        ]
        length = max([len(refs_line)] + list(map(len, cond_lines)))
        drs = (
            [
                " _" + "_" * length + "_ ",
                "| " + refs_line.ljust(length) + " |",
                "|-" + "-" * length + "-|",
            ]
            + ["| " + line.ljust(length) + " |" for line in cond_lines]
            + ["|_" + "_" * length + "_|"]
        )
        if self.consequent:
            return DrtBinaryExpression._assemble_pretty(
                drs, DrtTokens.IMP, self.consequent._pretty()
            )
        return drs

    def _order_ref_strings(self, refs):
        strings = ["%s" % ref for ref in refs]
        ind_vars = []
        func_vars = []
        event_vars = []
        other_vars = []
        for s in strings:
            if is_indvar(s):
                ind_vars.append(s)
            elif is_funcvar(s):
                func_vars.append(s)
            elif is_eventvar(s):
                event_vars.append(s)
            else:
                other_vars.append(s)
        return (
            sorted(other_vars)
            + sorted(event_vars, key=lambda v: int([v[2:], -1][len(v[2:]) == 0]))
            + sorted(func_vars, key=lambda v: (v[0], int([v[1:], -1][len(v[1:]) == 0])))
            + sorted(ind_vars, key=lambda v: (v[0], int([v[1:], -1][len(v[1:]) == 0])))
        )

    def __eq__(self, other):
        r"""Defines equality modulo alphabetic variance.
        If we are comparing \x.M  and \y.N, then check equality of M and N[x/y]."""
        if isinstance(other, DRS):
            if len(self.refs) == len(other.refs):
                converted_other = other
                for r1, r2 in zip(self.refs, converted_other.refs):
                    varex = self.make_VariableExpression(r1)
                    converted_other = converted_other.replace(r2, varex, True)
                if self.consequent == converted_other.consequent and len(
                    self.conds
                ) == len(converted_other.conds):
                    for c1, c2 in zip(self.conds, converted_other.conds):
                        if not (c1 == c2):
                            return False
                    return True
        return False

    def __ne__(self, other):
        return not self == other

    __hash__ = Expression.__hash__

    def __str__(self):
        drs = "([{}],[{}])".format(
            ",".join(self._order_ref_strings(self.refs)),
            ", ".join("%s" % cond for cond in self.conds),
        )  # map(str, self.conds)))
        if self.consequent:
            return (
                DrtTokens.OPEN
                + drs
                + " "
                + DrtTokens.IMP
                + " "
                + "%s" % self.consequent
                + DrtTokens.CLOSE
            )
        return drs


def DrtVariableExpression(variable):
    """
    This is a factory method that instantiates and returns a subtype of
    ``DrtAbstractVariableExpression`` appropriate for the given variable.
    """
    if is_indvar(variable.name):
        return DrtIndividualVariableExpression(variable)
    elif is_funcvar(variable.name):
        return DrtFunctionVariableExpression(variable)
    elif is_eventvar(variable.name):
        return DrtEventVariableExpression(variable)
    else:
        return DrtConstantExpression(variable)


class DrtAbstractVariableExpression(DrtExpression, AbstractVariableExpression):
    def fol(self):
        return self

    def get_refs(self, recursive=False):
        """:see: AbstractExpression.get_refs()"""
        return []

    def _pretty(self):
        s = "%s" % self
        blank = " " * len(s)
        return [blank, blank, s, blank]

    def eliminate_equality(self):
        return self


class DrtIndividualVariableExpression(
    DrtAbstractVariableExpression, IndividualVariableExpression
):
    pass


class DrtFunctionVariableExpression(
    DrtAbstractVariableExpression, FunctionVariableExpression
):
    pass


class DrtEventVariableExpression(
    DrtIndividualVariableExpression, EventVariableExpression
):
    pass


class DrtConstantExpression(DrtAbstractVariableExpression, ConstantExpression):
    pass


class DrtProposition(DrtExpression, Expression):
    def __init__(self, variable, drs):
        self.variable = variable
        self.drs = drs

    def replace(self, variable, expression, replace_bound=False, alpha_convert=True):
        if self.variable == variable:
            assert isinstance(
                expression, DrtAbstractVariableExpression
            ), "Can only replace a proposition label with a variable"
            return DrtProposition(
                expression.variable,
                self.drs.replace(variable, expression, replace_bound, alpha_convert),
            )
        else:
            return DrtProposition(
                self.variable,
                self.drs.replace(variable, expression, replace_bound, alpha_convert),
            )

    def eliminate_equality(self):
        return DrtProposition(self.variable, self.drs.eliminate_equality())

    def get_refs(self, recursive=False):
        return self.drs.get_refs(True) if recursive else []

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__
            and self.variable == other.variable
            and self.drs == other.drs
        )

    def __ne__(self, other):
        return not self == other

    __hash__ = Expression.__hash__

    def fol(self):
        return self.drs.fol()

    def _pretty(self):
        drs_s = self.drs._pretty()
        blank = " " * len("%s" % self.variable)
        return (
            [blank + " " + line for line in drs_s[:1]]
            + ["%s" % self.variable + ":" + line for line in drs_s[1:2]]
            + [blank + " " + line for line in drs_s[2:]]
        )

    def visit(self, function, combinator):
        """:see: Expression.visit()"""
        return combinator([function(self.drs)])

    def visit_structured(self, function, combinator):
        """:see: Expression.visit_structured()"""
        return combinator(self.variable, function(self.drs))

    def __str__(self):
        return f"prop({self.variable}, {self.drs})"


class DrtNegatedExpression(DrtExpression, NegatedExpression):
    def fol(self):
        return NegatedExpression(self.term.fol())

    def get_refs(self, recursive=False):
        """:see: AbstractExpression.get_refs()"""
        return self.term.get_refs(recursive)

    def _pretty(self):
        term_lines = self.term._pretty()
        return (
            ["    " + line for line in term_lines[:2]]
            + ["__  " + line for line in term_lines[2:3]]
            + ["  | " + line for line in term_lines[3:4]]
            + ["    " + line for line in term_lines[4:]]
        )


class DrtLambdaExpression(DrtExpression, LambdaExpression):
    def alpha_convert(self, newvar):
        """Rename all occurrences of the variable introduced by this variable
        binder in the expression to ``newvar``.
        :param newvar: ``Variable``, for the new variable
        """
        return self.__class__(
            newvar,
            self.term.replace(self.variable, DrtVariableExpression(newvar), True),
        )

    def fol(self):
        return LambdaExpression(self.variable, self.term.fol())

    def _pretty(self):
        variables = [self.variable]
        term = self.term
        while term.__class__ == self.__class__:
            variables.append(term.variable)
            term = term.term
        var_string = " ".join("%s" % v for v in variables) + DrtTokens.DOT
        term_lines = term._pretty()
        blank = " " * len(var_string)
        return (
            ["    " + blank + line for line in term_lines[:1]]
            + [r" \  " + blank + line for line in term_lines[1:2]]
            + [r" /\ " + var_string + line for line in term_lines[2:3]]
            + ["    " + blank + line for line in term_lines[3:]]
        )

    def get_refs(self, recursive=False):
        """:see: AbstractExpression.get_refs()"""
        return (
            [self.variable] + self.term.get_refs(True) if recursive else [self.variable]
        )


class DrtBinaryExpression(DrtExpression, BinaryExpression):
    def get_refs(self, recursive=False):
        """:see: AbstractExpression.get_refs()"""
        return (
            self.first.get_refs(True) + self.second.get_refs(True) if recursive else []
        )

    def _pretty(self):
        return DrtBinaryExpression._assemble_pretty(
            self._pretty_subex(self.first),
            self.getOp(),
            self._pretty_subex(self.second),
        )

    @staticmethod
    def _assemble_pretty(first_lines, op, second_lines):
        max_lines = max(len(first_lines), len(second_lines))
        first_lines = _pad_vertically(first_lines, max_lines)
        second_lines = _pad_vertically(second_lines, max_lines)
        blank = " " * len(op)
        first_second_lines = list(zip(first_lines, second_lines))
        return (
            [
                " " + first_line + " " + blank + " " + second_line + " "
                for first_line, second_line in first_second_lines[:2]
            ]
            + [
                "(" + first_line + " " + op + " " + second_line + ")"
                for first_line, second_line in first_second_lines[2:3]
            ]
            + [
                " " + first_line + " " + blank + " " + second_line + " "
                for first_line, second_line in first_second_lines[3:]
            ]
        )

    def _pretty_subex(self, subex):
        return subex._pretty()


class DrtBooleanExpression(DrtBinaryExpression, BooleanExpression):
    pass


class DrtOrExpression(DrtBooleanExpression, OrExpression):
    def fol(self):
        return OrExpression(self.first.fol(), self.second.fol())

    def _pretty_subex(self, subex):
        if isinstance(subex, DrtOrExpression):
            return [line[1:-1] for line in subex._pretty()]
        return DrtBooleanExpression._pretty_subex(self, subex)


class DrtEqualityExpression(DrtBinaryExpression, EqualityExpression):
    def fol(self):
        return EqualityExpression(self.first.fol(), self.second.fol())


class DrtConcatenation(DrtBooleanExpression):
    """DRS of the form '(DRS + DRS)'"""

    def __init__(self, first, second, consequent=None):
        DrtBooleanExpression.__init__(self, first, second)
        self.consequent = consequent

    def replace(self, variable, expression, replace_bound=False, alpha_convert=True):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        first = self.first
        second = self.second
        consequent = self.consequent

        # If variable is bound
        if variable in self.get_refs():
            if replace_bound:
                first = first.replace(
                    variable, expression, replace_bound, alpha_convert
                )
                second = second.replace(
                    variable, expression, replace_bound, alpha_convert
                )
                if consequent:
                    consequent = consequent.replace(
                        variable, expression, replace_bound, alpha_convert
                    )
        else:
            if alpha_convert:
                # alpha convert every ref that is free in 'expression'
                for ref in set(self.get_refs(True)) & expression.free():
                    v = DrtVariableExpression(unique_variable(ref))
                    first = first.replace(ref, v, True, alpha_convert)
                    second = second.replace(ref, v, True, alpha_convert)
                    if consequent:
                        consequent = consequent.replace(ref, v, True, alpha_convert)

            first = first.replace(variable, expression, replace_bound, alpha_convert)
            second = second.replace(variable, expression, replace_bound, alpha_convert)
            if consequent:
                consequent = consequent.replace(
                    variable, expression, replace_bound, alpha_convert
                )

        return self.__class__(first, second, consequent)

    def eliminate_equality(self):
        # TODO: at some point.  for now, simplify.
        drs = self.simplify()
        assert not isinstance(drs, DrtConcatenation)
        return drs.eliminate_equality()

    def simplify(self):
        first = self.first.simplify()
        second = self.second.simplify()
        consequent = self.consequent.simplify() if self.consequent else None

        if isinstance(first, DRS) and isinstance(second, DRS):
            # For any ref that is in both 'first' and 'second'
            for ref in set(first.get_refs(True)) & set(second.get_refs(True)):
                # alpha convert the ref in 'second' to prevent collision
                newvar = DrtVariableExpression(unique_variable(ref))
                second = second.replace(ref, newvar, True)

            return DRS(first.refs + second.refs, first.conds + second.conds, consequent)
        else:
            return self.__class__(first, second, consequent)

    def get_refs(self, recursive=False):
        """:see: AbstractExpression.get_refs()"""
        refs = self.first.get_refs(recursive) + self.second.get_refs(recursive)
        if self.consequent and recursive:
            refs.extend(self.consequent.get_refs(True))
        return refs

    def getOp(self):
        return DrtTokens.DRS_CONC

    def __eq__(self, other):
        r"""Defines equality modulo alphabetic variance.
        If we are comparing \x.M  and \y.N, then check equality of M and N[x/y]."""
        if isinstance(other, DrtConcatenation):
            self_refs = self.get_refs()
            other_refs = other.get_refs()
            if len(self_refs) == len(other_refs):
                converted_other = other
                for r1, r2 in zip(self_refs, other_refs):
                    varex = self.make_VariableExpression(r1)
                    converted_other = converted_other.replace(r2, varex, True)
                return (
                    self.first == converted_other.first
                    and self.second == converted_other.second
                    and self.consequent == converted_other.consequent
                )
        return False

    def __ne__(self, other):
        return not self == other

    __hash__ = DrtBooleanExpression.__hash__

    def fol(self):
        e = AndExpression(self.first.fol(), self.second.fol())
        if self.consequent:
            e = ImpExpression(e, self.consequent.fol())
        return e

    def _pretty(self):
        drs = DrtBinaryExpression._assemble_pretty(
            self._pretty_subex(self.first),
            self.getOp(),
            self._pretty_subex(self.second),
        )
        if self.consequent:
            drs = DrtBinaryExpression._assemble_pretty(
                drs, DrtTokens.IMP, self.consequent._pretty()
            )
        return drs

    def _pretty_subex(self, subex):
        if isinstance(subex, DrtConcatenation):
            return [line[1:-1] for line in subex._pretty()]
        return DrtBooleanExpression._pretty_subex(self, subex)

    def visit(self, function, combinator):
        """:see: Expression.visit()"""
        if self.consequent:
            return combinator(
                [function(self.first), function(self.second), function(self.consequent)]
            )
        else:
            return combinator([function(self.first), function(self.second)])

    def __str__(self):
        first = self._str_subex(self.first)
        second = self._str_subex(self.second)
        drs = Tokens.OPEN + first + " " + self.getOp() + " " + second + Tokens.CLOSE
        if self.consequent:
            return (
                DrtTokens.OPEN
                + drs
                + " "
                + DrtTokens.IMP
                + " "
                + "%s" % self.consequent
                + DrtTokens.CLOSE
            )
        return drs

    def _str_subex(self, subex):
        s = "%s" % subex
        if isinstance(subex, DrtConcatenation) and subex.consequent is None:
            return s[1:-1]
        return s


class DrtApplicationExpression(DrtExpression, ApplicationExpression):
    def fol(self):
        return ApplicationExpression(self.function.fol(), self.argument.fol())

    def get_refs(self, recursive=False):
        """:see: AbstractExpression.get_refs()"""
        return (
            self.function.get_refs(True) + self.argument.get_refs(True)
            if recursive
            else []
        )

    def _pretty(self):
        function, args = self.uncurry()
        function_lines = function._pretty()
        args_lines = [arg._pretty() for arg in args]
        max_lines = max(map(len, [function_lines] + args_lines))
        function_lines = _pad_vertically(function_lines, max_lines)
        args_lines = [_pad_vertically(arg_lines, max_lines) for arg_lines in args_lines]
        func_args_lines = list(zip(function_lines, list(zip(*args_lines))))
        return (
            [
                func_line + " " + " ".join(args_line) + " "
                for func_line, args_line in func_args_lines[:2]
            ]
            + [
                func_line + "(" + ",".join(args_line) + ")"
                for func_line, args_line in func_args_lines[2:3]
            ]
            + [
                func_line + " " + " ".join(args_line) + " "
                for func_line, args_line in func_args_lines[3:]
            ]
        )


def _pad_vertically(lines, max_lines):
    pad_line = [" " * len(lines[0])]
    return lines + pad_line * (max_lines - len(lines))


class PossibleAntecedents(list, DrtExpression, Expression):
    def free(self):
        """Set of free variables."""
        return set(self)

    def replace(self, variable, expression, replace_bound=False, alpha_convert=True):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        result = PossibleAntecedents()
        for item in self:
            if item == variable:
                self.append(expression)
            else:
                self.append(item)
        return result

    def _pretty(self):
        s = "%s" % self
        blank = " " * len(s)
        return [blank, blank, s]

    def __str__(self):
        return "[" + ",".join("%s" % it for it in self) + "]"


class AnaphoraResolutionException(Exception):
    pass


def resolve_anaphora(expression, trail=[]):
    if isinstance(expression, ApplicationExpression):
        if expression.is_pronoun_function():
            possible_antecedents = PossibleAntecedents()
            for ancestor in trail:
                for ref in ancestor.get_refs():
                    refex = expression.make_VariableExpression(ref)

                    # ==========================================================
                    # Don't allow resolution to itself or other types
                    # ==========================================================
                    if refex.__class__ == expression.argument.__class__ and not (
                        refex == expression.argument
                    ):
                        possible_antecedents.append(refex)

            if len(possible_antecedents) == 1:
                resolution = possible_antecedents[0]
            else:
                resolution = possible_antecedents
            return expression.make_EqualityExpression(expression.argument, resolution)
        else:
            r_function = resolve_anaphora(expression.function, trail + [expression])
            r_argument = resolve_anaphora(expression.argument, trail + [expression])
            return expression.__class__(r_function, r_argument)

    elif isinstance(expression, DRS):
        r_conds = []
        for cond in expression.conds:
            r_cond = resolve_anaphora(cond, trail + [expression])

            # if the condition is of the form '(x = [])' then raise exception
            if isinstance(r_cond, EqualityExpression):
                if isinstance(r_cond.first, PossibleAntecedents):
                    # Reverse the order so that the variable is on the left
                    temp = r_cond.first
                    r_cond.first = r_cond.second
                    r_cond.second = temp
                if isinstance(r_cond.second, PossibleAntecedents):
                    if not r_cond.second:
                        raise AnaphoraResolutionException(
                            "Variable '%s' does not "
                            "resolve to anything." % r_cond.first
                        )

            r_conds.append(r_cond)
        if expression.consequent:
            consequent = resolve_anaphora(expression.consequent, trail + [expression])
        else:
            consequent = None
        return expression.__class__(expression.refs, r_conds, consequent)

    elif isinstance(expression, AbstractVariableExpression):
        return expression

    elif isinstance(expression, NegatedExpression):
        return expression.__class__(
            resolve_anaphora(expression.term, trail + [expression])
        )

    elif isinstance(expression, DrtConcatenation):
        if expression.consequent:
            consequent = resolve_anaphora(expression.consequent, trail + [expression])
        else:
            consequent = None
        return expression.__class__(
            resolve_anaphora(expression.first, trail + [expression]),
            resolve_anaphora(expression.second, trail + [expression]),
            consequent,
        )

    elif isinstance(expression, BinaryExpression):
        return expression.__class__(
            resolve_anaphora(expression.first, trail + [expression]),
            resolve_anaphora(expression.second, trail + [expression]),
        )

    elif isinstance(expression, LambdaExpression):
        return expression.__class__(
            expression.variable, resolve_anaphora(expression.term, trail + [expression])
        )


class DrsDrawer:
    BUFFER = 3  # Space between elements
    TOPSPACE = 10  # Space above whole DRS
    OUTERSPACE = 6  # Space to the left, right, and bottom of the while DRS

    def __init__(self, drs, size_canvas=True, canvas=None):
        """
        :param drs: ``DrtExpression``, The DRS to be drawn
        :param size_canvas: bool, True if the canvas size should be the exact size of the DRS
        :param canvas: ``Canvas`` The canvas on which to draw the DRS.  If none is given, create a new canvas.
        """
        master = None
        if not canvas:
            master = Tk()
            master.title("DRT")

            font = Font(family="helvetica", size=12)

            if size_canvas:
                canvas = Canvas(master, width=0, height=0)
                canvas.font = font
                self.canvas = canvas
                (right, bottom) = self._visit(drs, self.OUTERSPACE, self.TOPSPACE)

                width = max(right + self.OUTERSPACE, 100)
                height = bottom + self.OUTERSPACE
                canvas = Canvas(master, width=width, height=height)  # , bg='white')
            else:
                canvas = Canvas(master, width=300, height=300)

            canvas.pack()
            canvas.font = font

        self.canvas = canvas
        self.drs = drs
        self.master = master

    def _get_text_height(self):
        """Get the height of a line of text"""
        return self.canvas.font.metrics("linespace")

    def draw(self, x=OUTERSPACE, y=TOPSPACE):
        """Draw the DRS"""
        self._handle(self.drs, self._draw_command, x, y)

        if self.master and not in_idle():
            self.master.mainloop()
        else:
            return self._visit(self.drs, x, y)

    def _visit(self, expression, x, y):
        """
        Return the bottom-rightmost point without actually drawing the item

        :param expression: the item to visit
        :param x: the top of the current drawing area
        :param y: the left side of the current drawing area
        :return: the bottom-rightmost point
        """
        return self._handle(expression, self._visit_command, x, y)

    def _draw_command(self, item, x, y):
        """
        Draw the given item at the given location

        :param item: the item to draw
        :param x: the top of the current drawing area
        :param y: the left side of the current drawing area
        :return: the bottom-rightmost point
        """
        if isinstance(item, str):
            self.canvas.create_text(x, y, anchor="nw", font=self.canvas.font, text=item)
        elif isinstance(item, tuple):
            # item is the lower-right of a box
            (right, bottom) = item
            self.canvas.create_rectangle(x, y, right, bottom)
            horiz_line_y = (
                y + self._get_text_height() + (self.BUFFER * 2)
            )  # the line separating refs from conds
            self.canvas.create_line(x, horiz_line_y, right, horiz_line_y)

        return self._visit_command(item, x, y)

    def _visit_command(self, item, x, y):
        """
        Return the bottom-rightmost point without actually drawing the item

        :param item: the item to visit
        :param x: the top of the current drawing area
        :param y: the left side of the current drawing area
        :return: the bottom-rightmost point
        """
        if isinstance(item, str):
            return (x + self.canvas.font.measure(item), y + self._get_text_height())
        elif isinstance(item, tuple):
            return item

    def _handle(self, expression, command, x=0, y=0):
        """
        :param expression: the expression to handle
        :param command: the function to apply, either _draw_command or _visit_command
        :param x: the top of the current drawing area
        :param y: the left side of the current drawing area
        :return: the bottom-rightmost point
        """
        if command == self._visit_command:
            # if we don't need to draw the item, then we can use the cached values
            try:
                # attempt to retrieve cached values
                right = expression._drawing_width + x
                bottom = expression._drawing_height + y
                return (right, bottom)
            except AttributeError:
                # the values have not been cached yet, so compute them
                pass

        if isinstance(expression, DrtAbstractVariableExpression):
            factory = self._handle_VariableExpression
        elif isinstance(expression, DRS):
            factory = self._handle_DRS
        elif isinstance(expression, DrtNegatedExpression):
            factory = self._handle_NegatedExpression
        elif isinstance(expression, DrtLambdaExpression):
            factory = self._handle_LambdaExpression
        elif isinstance(expression, BinaryExpression):
            factory = self._handle_BinaryExpression
        elif isinstance(expression, DrtApplicationExpression):
            factory = self._handle_ApplicationExpression
        elif isinstance(expression, PossibleAntecedents):
            factory = self._handle_VariableExpression
        elif isinstance(expression, DrtProposition):
            factory = self._handle_DrtProposition
        else:
            raise Exception(expression.__class__.__name__)

        (right, bottom) = factory(expression, command, x, y)

        # cache the values
        expression._drawing_width = right - x
        expression._drawing_height = bottom - y

        return (right, bottom)

    def _handle_VariableExpression(self, expression, command, x, y):
        return command("%s" % expression, x, y)

    def _handle_NegatedExpression(self, expression, command, x, y):
        # Find the width of the negation symbol
        right = self._visit_command(DrtTokens.NOT, x, y)[0]

        # Handle term
        (right, bottom) = self._handle(expression.term, command, right, y)

        # Handle variables now that we know the y-coordinate
        command(
            DrtTokens.NOT,
            x,
            self._get_centered_top(y, bottom - y, self._get_text_height()),
        )

        return (right, bottom)

    def _handle_DRS(self, expression, command, x, y):
        left = x + self.BUFFER  # indent the left side
        bottom = y + self.BUFFER  # indent the top

        # Handle Discourse Referents
        if expression.refs:
            refs = " ".join("%s" % r for r in expression.refs)
        else:
            refs = "     "
        (max_right, bottom) = command(refs, left, bottom)
        bottom += self.BUFFER * 2

        # Handle Conditions
        if expression.conds:
            for cond in expression.conds:
                (right, bottom) = self._handle(cond, command, left, bottom)
                max_right = max(max_right, right)
                bottom += self.BUFFER
        else:
            bottom += self._get_text_height() + self.BUFFER

        # Handle Box
        max_right += self.BUFFER
        return command((max_right, bottom), x, y)

    def _handle_ApplicationExpression(self, expression, command, x, y):
        function, args = expression.uncurry()
        if not isinstance(function, DrtAbstractVariableExpression):
            # It's not a predicate expression ("P(x,y)"), so leave arguments curried
            function = expression.function
            args = [expression.argument]

        # Get the max bottom of any element on the line
        function_bottom = self._visit(function, x, y)[1]
        max_bottom = max(
            [function_bottom] + [self._visit(arg, x, y)[1] for arg in args]
        )

        line_height = max_bottom - y

        # Handle 'function'
        function_drawing_top = self._get_centered_top(
            y, line_height, function._drawing_height
        )
        right = self._handle(function, command, x, function_drawing_top)[0]

        # Handle open paren
        centred_string_top = self._get_centered_top(
            y, line_height, self._get_text_height()
        )
        right = command(DrtTokens.OPEN, right, centred_string_top)[0]

        # Handle each arg
        for i, arg in enumerate(args):
            arg_drawing_top = self._get_centered_top(
                y, line_height, arg._drawing_height
            )
            right = self._handle(arg, command, right, arg_drawing_top)[0]

            if i + 1 < len(args):
                # since it's not the last arg, add a comma
                right = command(DrtTokens.COMMA + " ", right, centred_string_top)[0]

        # Handle close paren
        right = command(DrtTokens.CLOSE, right, centred_string_top)[0]

        return (right, max_bottom)

    def _handle_LambdaExpression(self, expression, command, x, y):
        # Find the width of the lambda symbol and abstracted variables
        variables = DrtTokens.LAMBDA + "%s" % expression.variable + DrtTokens.DOT
        right = self._visit_command(variables, x, y)[0]

        # Handle term
        (right, bottom) = self._handle(expression.term, command, right, y)

        # Handle variables now that we know the y-coordinate
        command(
            variables, x, self._get_centered_top(y, bottom - y, self._get_text_height())
        )

        return (right, bottom)

    def _handle_BinaryExpression(self, expression, command, x, y):
        # Get the full height of the line, based on the operands
        first_height = self._visit(expression.first, 0, 0)[1]
        second_height = self._visit(expression.second, 0, 0)[1]
        line_height = max(first_height, second_height)

        # Handle open paren
        centred_string_top = self._get_centered_top(
            y, line_height, self._get_text_height()
        )
        right = command(DrtTokens.OPEN, x, centred_string_top)[0]

        # Handle the first operand
        first_height = expression.first._drawing_height
        (right, first_bottom) = self._handle(
            expression.first,
            command,
            right,
            self._get_centered_top(y, line_height, first_height),
        )

        # Handle the operator
        right = command(" %s " % expression.getOp(), right, centred_string_top)[0]

        # Handle the second operand
        second_height = expression.second._drawing_height
        (right, second_bottom) = self._handle(
            expression.second,
            command,
            right,
            self._get_centered_top(y, line_height, second_height),
        )

        # Handle close paren
        right = command(DrtTokens.CLOSE, right, centred_string_top)[0]

        return (right, max(first_bottom, second_bottom))

    def _handle_DrtProposition(self, expression, command, x, y):
        # Find the width of the negation symbol
        right = command(expression.variable, x, y)[0]

        # Handle term
        (right, bottom) = self._handle(expression.term, command, right, y)

        return (right, bottom)

    def _get_centered_top(self, top, full_height, item_height):
        """Get the y-coordinate of the point that a figure should start at if
        its height is 'item_height' and it needs to be centered in an area that
        starts at 'top' and is 'full_height' tall."""
        return top + (full_height - item_height) / 2


def demo():
    print("=" * 20 + "TEST PARSE" + "=" * 20)
    dexpr = DrtExpression.fromstring
    print(dexpr(r"([x,y],[sees(x,y)])"))
    print(dexpr(r"([x],[man(x), walks(x)])"))
    print(dexpr(r"\x.\y.([],[sees(x,y)])"))
    print(dexpr(r"\x.([],[walks(x)])(john)"))
    print(dexpr(r"(([x],[walks(x)]) + ([y],[runs(y)]))"))
    print(dexpr(r"(([],[walks(x)]) -> ([],[runs(x)]))"))
    print(dexpr(r"([x],[PRO(x), sees(John,x)])"))
    print(dexpr(r"([x],[man(x), -([],[walks(x)])])"))
    print(dexpr(r"([],[(([x],[man(x)]) -> ([],[walks(x)]))])"))

    print("=" * 20 + "Test fol()" + "=" * 20)
    print(dexpr(r"([x,y],[sees(x,y)])").fol())

    print("=" * 20 + "Test alpha conversion and lambda expression equality" + "=" * 20)
    e1 = dexpr(r"\x.([],[P(x)])")
    print(e1)
    e2 = e1.alpha_convert(Variable("z"))
    print(e2)
    print(e1 == e2)

    print("=" * 20 + "Test resolve_anaphora()" + "=" * 20)
    print(resolve_anaphora(dexpr(r"([x,y,z],[dog(x), cat(y), walks(z), PRO(z)])")))
    print(
        resolve_anaphora(dexpr(r"([],[(([x],[dog(x)]) -> ([y],[walks(y), PRO(y)]))])"))
    )
    print(resolve_anaphora(dexpr(r"(([x,y],[]) + ([],[PRO(x)]))")))

    print("=" * 20 + "Test pretty_print()" + "=" * 20)
    dexpr(r"([],[])").pretty_print()
    dexpr(
        r"([],[([x],[big(x), dog(x)]) -> ([],[bark(x)]) -([x],[walk(x)])])"
    ).pretty_print()
    dexpr(r"([x,y],[x=y]) + ([z],[dog(z), walk(z)])").pretty_print()
    dexpr(r"([],[([x],[]) | ([y],[]) | ([z],[dog(z), walk(z)])])").pretty_print()
    dexpr(r"\P.\Q.(([x],[]) + P(x) + Q(x))(\x.([],[dog(x)]))").pretty_print()


def test_draw():
    try:
        from tkinter import Tk
    except ImportError as e:
        raise ValueError("tkinter is required, but it's not available.")

    expressions = [
        r"x",
        r"([],[])",
        r"([x],[])",
        r"([x],[man(x)])",
        r"([x,y],[sees(x,y)])",
        r"([x],[man(x), walks(x)])",
        r"\x.([],[man(x), walks(x)])",
        r"\x y.([],[sees(x,y)])",
        r"([],[(([],[walks(x)]) + ([],[runs(x)]))])",
        r"([x],[man(x), -([],[walks(x)])])",
        r"([],[(([x],[man(x)]) -> ([],[walks(x)]))])",
    ]

    for e in expressions:
        d = DrtExpression.fromstring(e)
        d.draw()


if __name__ == "__main__":
    demo()