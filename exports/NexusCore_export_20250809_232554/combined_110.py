
# === NexusCore/openenv\Lib\site-packages\anthropic\lib\bedrock\_client.py ===
from __future__ import annotations

import os
from typing import Any, Union, Mapping, TypeVar
from typing_extensions import Self, override

import httpx

from ... import _exceptions
from ._beta import Beta, AsyncBeta
from ..._types import NOT_GIVEN, Timeout, NotGiven
from ..._utils import is_dict, is_given
from ..._compat import model_copy
from ..._version import __version__
from ..._streaming import Stream, AsyncStream
from ..._exceptions import APIStatusError
from ..._base_client import (
    DEFAULT_MAX_RETRIES,
    BaseClient,
    SyncAPIClient,
    AsyncAPIClient,
    FinalRequestOptions,
)
from ._stream_decoder import AWSEventStreamDecoder
from ...resources.messages import Messages, AsyncMessages
from ...resources.completions import Completions, AsyncCompletions

DEFAULT_VERSION = "bedrock-2023-05-31"

_HttpxClientT = TypeVar("_HttpxClientT", bound=Union[httpx.Client, httpx.AsyncClient])
_DefaultStreamT = TypeVar("_DefaultStreamT", bound=Union[Stream[Any], AsyncStream[Any]])


def _prepare_options(input_options: FinalRequestOptions) -> FinalRequestOptions:
    options = model_copy(input_options, deep=True)

    if is_dict(options.json_data):
        options.json_data.setdefault("anthropic_version", DEFAULT_VERSION)

        if is_given(options.headers):
            betas = options.headers.get("anthropic-beta")
            if betas:
                options.json_data.setdefault("anthropic_beta", betas.split(","))

    if options.url in {"/v1/complete", "/v1/messages", "/v1/messages?beta=true"} and options.method == "post":
        if not is_dict(options.json_data):
            raise RuntimeError("Expected dictionary json_data for post /completions endpoint")

        model = options.json_data.pop("model", None)
        stream = options.json_data.pop("stream", False)
        if stream:
            options.url = f"/model/{model}/invoke-with-response-stream"
        else:
            options.url = f"/model/{model}/invoke"

    return options


class BaseBedrockClient(BaseClient[_HttpxClientT, _DefaultStreamT]):
    @override
    def _make_status_error(
        self,
        err_msg: str,
        *,
        body: object,
        response: httpx.Response,
    ) -> APIStatusError:
        if response.status_code == 400:
            return _exceptions.BadRequestError(err_msg, response=response, body=body)

        if response.status_code == 401:
            return _exceptions.AuthenticationError(err_msg, response=response, body=body)

        if response.status_code == 403:
            return _exceptions.PermissionDeniedError(err_msg, response=response, body=body)

        if response.status_code == 404:
            return _exceptions.NotFoundError(err_msg, response=response, body=body)

        if response.status_code == 409:
            return _exceptions.ConflictError(err_msg, response=response, body=body)

        if response.status_code == 422:
            return _exceptions.UnprocessableEntityError(err_msg, response=response, body=body)

        if response.status_code == 429:
            return _exceptions.RateLimitError(err_msg, response=response, body=body)

        if response.status_code >= 500:
            return _exceptions.InternalServerError(err_msg, response=response, body=body)
        return APIStatusError(err_msg, response=response, body=body)


class AnthropicBedrock(BaseBedrockClient[httpx.Client, Stream[Any]], SyncAPIClient):
    messages: Messages
    completions: Completions
    beta: Beta

    def __init__(
        self,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_profile: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client. See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.Client | None = None,
        # Enable or disable schema validation for data returned by the API.
        # When enabled an error APIResponseValidationError is raised
        # if the API responds with invalid data for the expected schema.
        #
        # This parameter may be removed or changed in the future.
        # If you rely on this feature, please open a GitHub issue
        # outlining your use-case to help us decide if it should be
        # part of our public interface in the future.
        _strict_response_validation: bool = False,
    ) -> None:
        self.aws_secret_key = aws_secret_key

        self.aws_access_key = aws_access_key

        if aws_region is None:
            aws_region = os.environ.get("AWS_REGION") or "us-east-1"
        self.aws_region = aws_region
        self.aws_profile = aws_profile

        self.aws_session_token = aws_session_token

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_BEDROCK_BASE_URL")
        if base_url is None:
            base_url = f"https://bedrock-runtime.{self.aws_region}.amazonaws.com"

        super().__init__(
            version=__version__,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            custom_headers=default_headers,
            custom_query=default_query,
            http_client=http_client,
            _strict_response_validation=_strict_response_validation,
        )

        self.beta = Beta(self)
        self.messages = Messages(self)
        self.completions = Completions(self)

    @override
    def _make_sse_decoder(self) -> AWSEventStreamDecoder:
        return AWSEventStreamDecoder()

    @override
    def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        return _prepare_options(options)

    @override
    def _prepare_request(self, request: httpx.Request) -> None:
        from ._auth import get_auth_headers

        data = request.read().decode()

        headers = get_auth_headers(
            method=request.method,
            url=str(request.url),
            headers=request.headers,
            aws_access_key=self.aws_access_key,
            aws_secret_key=self.aws_secret_key,
            aws_session_token=self.aws_session_token,
            region=self.aws_region or "us-east-1",
            profile=self.aws_profile,
            data=data,
        )
        request.headers.update(headers)

    def copy(
        self,
        *,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.Client | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        return self.__class__(
            aws_secret_key=aws_secret_key or self.aws_secret_key,
            aws_access_key=aws_access_key or self.aws_access_key,
            aws_region=aws_region or self.aws_region,
            aws_session_token=aws_session_token or self.aws_session_token,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy


class AsyncAnthropicBedrock(BaseBedrockClient[httpx.AsyncClient, AsyncStream[Any]], AsyncAPIClient):
    messages: AsyncMessages
    completions: AsyncCompletions
    beta: AsyncBeta

    def __init__(
        self,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_profile: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client. See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.AsyncClient | None = None,
        # Enable or disable schema validation for data returned by the API.
        # When enabled an error APIResponseValidationError is raised
        # if the API responds with invalid data for the expected schema.
        #
        # This parameter may be removed or changed in the future.
        # If you rely on this feature, please open a GitHub issue
        # outlining your use-case to help us decide if it should be
        # part of our public interface in the future.
        _strict_response_validation: bool = False,
    ) -> None:
        self.aws_secret_key = aws_secret_key

        self.aws_access_key = aws_access_key

        if aws_region is None:
            aws_region = os.environ.get("AWS_REGION") or "us-east-1"
        self.aws_region = aws_region
        self.aws_profile = aws_profile

        self.aws_session_token = aws_session_token

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_BEDROCK_BASE_URL")
        if base_url is None:
            base_url = f"https://bedrock-runtime.{self.aws_region}.amazonaws.com"

        super().__init__(
            version=__version__,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            custom_headers=default_headers,
            custom_query=default_query,
            http_client=http_client,
            _strict_response_validation=_strict_response_validation,
        )

        self.messages = AsyncMessages(self)
        self.completions = AsyncCompletions(self)
        self.beta = AsyncBeta(self)

    @override
    def _make_sse_decoder(self) -> AWSEventStreamDecoder:
        return AWSEventStreamDecoder()

    @override
    async def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        return _prepare_options(options)

    @override
    async def _prepare_request(self, request: httpx.Request) -> None:
        from ._auth import get_auth_headers

        data = request.read().decode()

        headers = get_auth_headers(
            method=request.method,
            url=str(request.url),
            headers=request.headers,
            aws_access_key=self.aws_access_key,
            aws_secret_key=self.aws_secret_key,
            aws_session_token=self.aws_session_token,
            region=self.aws_region or "us-east-1",
            profile=self.aws_profile,
            data=data,
        )
        request.headers.update(headers)

    def copy(
        self,
        *,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.AsyncClient | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        return self.__class__(
            aws_secret_key=aws_secret_key or self.aws_secret_key,
            aws_access_key=aws_access_key or self.aws_access_key,
            aws_region=aws_region or self.aws_region,
            aws_session_token=aws_session_token or self.aws_session_token,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\anthropic\lib\bedrock\_client.py ===
from __future__ import annotations

import os
from typing import Any, Union, Mapping, TypeVar
from typing_extensions import Self, override

import httpx

from ... import _exceptions
from ._beta import Beta, AsyncBeta
from ..._types import NOT_GIVEN, Timeout, NotGiven
from ..._utils import is_dict, is_given
from ..._compat import model_copy
from ..._version import __version__
from ..._streaming import Stream, AsyncStream
from ..._exceptions import APIStatusError
from ..._base_client import (
    DEFAULT_MAX_RETRIES,
    BaseClient,
    SyncAPIClient,
    AsyncAPIClient,
    FinalRequestOptions,
)
from ._stream_decoder import AWSEventStreamDecoder
from ...resources.messages import Messages, AsyncMessages
from ...resources.completions import Completions, AsyncCompletions

DEFAULT_VERSION = "bedrock-2023-05-31"

_HttpxClientT = TypeVar("_HttpxClientT", bound=Union[httpx.Client, httpx.AsyncClient])
_DefaultStreamT = TypeVar("_DefaultStreamT", bound=Union[Stream[Any], AsyncStream[Any]])


def _prepare_options(input_options: FinalRequestOptions) -> FinalRequestOptions:
    options = model_copy(input_options, deep=True)

    if is_dict(options.json_data):
        options.json_data.setdefault("anthropic_version", DEFAULT_VERSION)

        if is_given(options.headers):
            betas = options.headers.get("anthropic-beta")
            if betas:
                options.json_data.setdefault("anthropic_beta", betas.split(","))

    if options.url in {"/v1/complete", "/v1/messages", "/v1/messages?beta=true"} and options.method == "post":
        if not is_dict(options.json_data):
            raise RuntimeError("Expected dictionary json_data for post /completions endpoint")

        model = options.json_data.pop("model", None)
        stream = options.json_data.pop("stream", False)
        if stream:
            options.url = f"/model/{model}/invoke-with-response-stream"
        else:
            options.url = f"/model/{model}/invoke"

    return options


class BaseBedrockClient(BaseClient[_HttpxClientT, _DefaultStreamT]):
    @override
    def _make_status_error(
        self,
        err_msg: str,
        *,
        body: object,
        response: httpx.Response,
    ) -> APIStatusError:
        if response.status_code == 400:
            return _exceptions.BadRequestError(err_msg, response=response, body=body)

        if response.status_code == 401:
            return _exceptions.AuthenticationError(err_msg, response=response, body=body)

        if response.status_code == 403:
            return _exceptions.PermissionDeniedError(err_msg, response=response, body=body)

        if response.status_code == 404:
            return _exceptions.NotFoundError(err_msg, response=response, body=body)

        if response.status_code == 409:
            return _exceptions.ConflictError(err_msg, response=response, body=body)

        if response.status_code == 422:
            return _exceptions.UnprocessableEntityError(err_msg, response=response, body=body)

        if response.status_code == 429:
            return _exceptions.RateLimitError(err_msg, response=response, body=body)

        if response.status_code >= 500:
            return _exceptions.InternalServerError(err_msg, response=response, body=body)
        return APIStatusError(err_msg, response=response, body=body)


class AnthropicBedrock(BaseBedrockClient[httpx.Client, Stream[Any]], SyncAPIClient):
    messages: Messages
    completions: Completions
    beta: Beta

    def __init__(
        self,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_profile: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client. See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.Client | None = None,
        # Enable or disable schema validation for data returned by the API.
        # When enabled an error APIResponseValidationError is raised
        # if the API responds with invalid data for the expected schema.
        #
        # This parameter may be removed or changed in the future.
        # If you rely on this feature, please open a GitHub issue
        # outlining your use-case to help us decide if it should be
        # part of our public interface in the future.
        _strict_response_validation: bool = False,
    ) -> None:
        self.aws_secret_key = aws_secret_key

        self.aws_access_key = aws_access_key

        if aws_region is None:
            aws_region = os.environ.get("AWS_REGION") or "us-east-1"
        self.aws_region = aws_region
        self.aws_profile = aws_profile

        self.aws_session_token = aws_session_token

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_BEDROCK_BASE_URL")
        if base_url is None:
            base_url = f"https://bedrock-runtime.{self.aws_region}.amazonaws.com"

        super().__init__(
            version=__version__,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            custom_headers=default_headers,
            custom_query=default_query,
            http_client=http_client,
            _strict_response_validation=_strict_response_validation,
        )

        self.beta = Beta(self)
        self.messages = Messages(self)
        self.completions = Completions(self)

    @override
    def _make_sse_decoder(self) -> AWSEventStreamDecoder:
        return AWSEventStreamDecoder()

    @override
    def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        return _prepare_options(options)

    @override
    def _prepare_request(self, request: httpx.Request) -> None:
        from ._auth import get_auth_headers

        data = request.read().decode()

        headers = get_auth_headers(
            method=request.method,
            url=str(request.url),
            headers=request.headers,
            aws_access_key=self.aws_access_key,
            aws_secret_key=self.aws_secret_key,
            aws_session_token=self.aws_session_token,
            region=self.aws_region or "us-east-1",
            profile=self.aws_profile,
            data=data,
        )
        request.headers.update(headers)

    def copy(
        self,
        *,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.Client | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        return self.__class__(
            aws_secret_key=aws_secret_key or self.aws_secret_key,
            aws_access_key=aws_access_key or self.aws_access_key,
            aws_region=aws_region or self.aws_region,
            aws_session_token=aws_session_token or self.aws_session_token,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy


class AsyncAnthropicBedrock(BaseBedrockClient[httpx.AsyncClient, AsyncStream[Any]], AsyncAPIClient):
    messages: AsyncMessages
    completions: AsyncCompletions
    beta: AsyncBeta

    def __init__(
        self,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_profile: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client. See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.AsyncClient | None = None,
        # Enable or disable schema validation for data returned by the API.
        # When enabled an error APIResponseValidationError is raised
        # if the API responds with invalid data for the expected schema.
        #
        # This parameter may be removed or changed in the future.
        # If you rely on this feature, please open a GitHub issue
        # outlining your use-case to help us decide if it should be
        # part of our public interface in the future.
        _strict_response_validation: bool = False,
    ) -> None:
        self.aws_secret_key = aws_secret_key

        self.aws_access_key = aws_access_key

        if aws_region is None:
            aws_region = os.environ.get("AWS_REGION") or "us-east-1"
        self.aws_region = aws_region
        self.aws_profile = aws_profile

        self.aws_session_token = aws_session_token

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_BEDROCK_BASE_URL")
        if base_url is None:
            base_url = f"https://bedrock-runtime.{self.aws_region}.amazonaws.com"

        super().__init__(
            version=__version__,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            custom_headers=default_headers,
            custom_query=default_query,
            http_client=http_client,
            _strict_response_validation=_strict_response_validation,
        )

        self.messages = AsyncMessages(self)
        self.completions = AsyncCompletions(self)
        self.beta = AsyncBeta(self)

    @override
    def _make_sse_decoder(self) -> AWSEventStreamDecoder:
        return AWSEventStreamDecoder()

    @override
    async def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        return _prepare_options(options)

    @override
    async def _prepare_request(self, request: httpx.Request) -> None:
        from ._auth import get_auth_headers

        data = request.read().decode()

        headers = get_auth_headers(
            method=request.method,
            url=str(request.url),
            headers=request.headers,
            aws_access_key=self.aws_access_key,
            aws_secret_key=self.aws_secret_key,
            aws_session_token=self.aws_session_token,
            region=self.aws_region or "us-east-1",
            profile=self.aws_profile,
            data=data,
        )
        request.headers.update(headers)

    def copy(
        self,
        *,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.AsyncClient | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        return self.__class__(
            aws_secret_key=aws_secret_key or self.aws_secret_key,
            aws_access_key=aws_access_key or self.aws_access_key,
            aws_region=aws_region or self.aws_region,
            aws_session_token=aws_session_token or self.aws_session_token,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\anthropic\lib\bedrock\_client.py ===
from __future__ import annotations

import os
from typing import Any, Union, Mapping, TypeVar
from typing_extensions import Self, override

import httpx

from ... import _exceptions
from ._beta import Beta, AsyncBeta
from ..._types import NOT_GIVEN, Timeout, NotGiven
from ..._utils import is_dict, is_given
from ..._compat import model_copy
from ..._version import __version__
from ..._streaming import Stream, AsyncStream
from ..._exceptions import APIStatusError
from ..._base_client import (
    DEFAULT_MAX_RETRIES,
    BaseClient,
    SyncAPIClient,
    AsyncAPIClient,
    FinalRequestOptions,
)
from ._stream_decoder import AWSEventStreamDecoder
from ...resources.messages import Messages, AsyncMessages
from ...resources.completions import Completions, AsyncCompletions

DEFAULT_VERSION = "bedrock-2023-05-31"

_HttpxClientT = TypeVar("_HttpxClientT", bound=Union[httpx.Client, httpx.AsyncClient])
_DefaultStreamT = TypeVar("_DefaultStreamT", bound=Union[Stream[Any], AsyncStream[Any]])


def _prepare_options(input_options: FinalRequestOptions) -> FinalRequestOptions:
    options = model_copy(input_options, deep=True)

    if is_dict(options.json_data):
        options.json_data.setdefault("anthropic_version", DEFAULT_VERSION)

        if is_given(options.headers):
            betas = options.headers.get("anthropic-beta")
            if betas:
                options.json_data.setdefault("anthropic_beta", betas.split(","))

    if options.url in {"/v1/complete", "/v1/messages", "/v1/messages?beta=true"} and options.method == "post":
        if not is_dict(options.json_data):
            raise RuntimeError("Expected dictionary json_data for post /completions endpoint")

        model = options.json_data.pop("model", None)
        stream = options.json_data.pop("stream", False)
        if stream:
            options.url = f"/model/{model}/invoke-with-response-stream"
        else:
            options.url = f"/model/{model}/invoke"

    return options


class BaseBedrockClient(BaseClient[_HttpxClientT, _DefaultStreamT]):
    @override
    def _make_status_error(
        self,
        err_msg: str,
        *,
        body: object,
        response: httpx.Response,
    ) -> APIStatusError:
        if response.status_code == 400:
            return _exceptions.BadRequestError(err_msg, response=response, body=body)

        if response.status_code == 401:
            return _exceptions.AuthenticationError(err_msg, response=response, body=body)

        if response.status_code == 403:
            return _exceptions.PermissionDeniedError(err_msg, response=response, body=body)

        if response.status_code == 404:
            return _exceptions.NotFoundError(err_msg, response=response, body=body)

        if response.status_code == 409:
            return _exceptions.ConflictError(err_msg, response=response, body=body)

        if response.status_code == 422:
            return _exceptions.UnprocessableEntityError(err_msg, response=response, body=body)

        if response.status_code == 429:
            return _exceptions.RateLimitError(err_msg, response=response, body=body)

        if response.status_code >= 500:
            return _exceptions.InternalServerError(err_msg, response=response, body=body)
        return APIStatusError(err_msg, response=response, body=body)


class AnthropicBedrock(BaseBedrockClient[httpx.Client, Stream[Any]], SyncAPIClient):
    messages: Messages
    completions: Completions
    beta: Beta

    def __init__(
        self,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_profile: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client. See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.Client | None = None,
        # Enable or disable schema validation for data returned by the API.
        # When enabled an error APIResponseValidationError is raised
        # if the API responds with invalid data for the expected schema.
        #
        # This parameter may be removed or changed in the future.
        # If you rely on this feature, please open a GitHub issue
        # outlining your use-case to help us decide if it should be
        # part of our public interface in the future.
        _strict_response_validation: bool = False,
    ) -> None:
        self.aws_secret_key = aws_secret_key

        self.aws_access_key = aws_access_key

        if aws_region is None:
            aws_region = os.environ.get("AWS_REGION") or "us-east-1"
        self.aws_region = aws_region
        self.aws_profile = aws_profile

        self.aws_session_token = aws_session_token

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_BEDROCK_BASE_URL")
        if base_url is None:
            base_url = f"https://bedrock-runtime.{self.aws_region}.amazonaws.com"

        super().__init__(
            version=__version__,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            custom_headers=default_headers,
            custom_query=default_query,
            http_client=http_client,
            _strict_response_validation=_strict_response_validation,
        )

        self.beta = Beta(self)
        self.messages = Messages(self)
        self.completions = Completions(self)

    @override
    def _make_sse_decoder(self) -> AWSEventStreamDecoder:
        return AWSEventStreamDecoder()

    @override
    def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        return _prepare_options(options)

    @override
    def _prepare_request(self, request: httpx.Request) -> None:
        from ._auth import get_auth_headers

        data = request.read().decode()

        headers = get_auth_headers(
            method=request.method,
            url=str(request.url),
            headers=request.headers,
            aws_access_key=self.aws_access_key,
            aws_secret_key=self.aws_secret_key,
            aws_session_token=self.aws_session_token,
            region=self.aws_region or "us-east-1",
            profile=self.aws_profile,
            data=data,
        )
        request.headers.update(headers)

    def copy(
        self,
        *,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.Client | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        return self.__class__(
            aws_secret_key=aws_secret_key or self.aws_secret_key,
            aws_access_key=aws_access_key or self.aws_access_key,
            aws_region=aws_region or self.aws_region,
            aws_session_token=aws_session_token or self.aws_session_token,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy


class AsyncAnthropicBedrock(BaseBedrockClient[httpx.AsyncClient, AsyncStream[Any]], AsyncAPIClient):
    messages: AsyncMessages
    completions: AsyncCompletions
    beta: AsyncBeta

    def __init__(
        self,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_profile: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client. See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.AsyncClient | None = None,
        # Enable or disable schema validation for data returned by the API.
        # When enabled an error APIResponseValidationError is raised
        # if the API responds with invalid data for the expected schema.
        #
        # This parameter may be removed or changed in the future.
        # If you rely on this feature, please open a GitHub issue
        # outlining your use-case to help us decide if it should be
        # part of our public interface in the future.
        _strict_response_validation: bool = False,
    ) -> None:
        self.aws_secret_key = aws_secret_key

        self.aws_access_key = aws_access_key

        if aws_region is None:
            aws_region = os.environ.get("AWS_REGION") or "us-east-1"
        self.aws_region = aws_region
        self.aws_profile = aws_profile

        self.aws_session_token = aws_session_token

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_BEDROCK_BASE_URL")
        if base_url is None:
            base_url = f"https://bedrock-runtime.{self.aws_region}.amazonaws.com"

        super().__init__(
            version=__version__,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            custom_headers=default_headers,
            custom_query=default_query,
            http_client=http_client,
            _strict_response_validation=_strict_response_validation,
        )

        self.messages = AsyncMessages(self)
        self.completions = AsyncCompletions(self)
        self.beta = AsyncBeta(self)

    @override
    def _make_sse_decoder(self) -> AWSEventStreamDecoder:
        return AWSEventStreamDecoder()

    @override
    async def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        return _prepare_options(options)

    @override
    async def _prepare_request(self, request: httpx.Request) -> None:
        from ._auth import get_auth_headers

        data = request.read().decode()

        headers = get_auth_headers(
            method=request.method,
            url=str(request.url),
            headers=request.headers,
            aws_access_key=self.aws_access_key,
            aws_secret_key=self.aws_secret_key,
            aws_session_token=self.aws_session_token,
            region=self.aws_region or "us-east-1",
            profile=self.aws_profile,
            data=data,
        )
        request.headers.update(headers)

    def copy(
        self,
        *,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.AsyncClient | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        return self.__class__(
            aws_secret_key=aws_secret_key or self.aws_secret_key,
            aws_access_key=aws_access_key or self.aws_access_key,
            aws_region=aws_region or self.aws_region,
            aws_session_token=aws_session_token or self.aws_session_token,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\combined_7.py ===

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\numpy\lib\tests\test_function_base.py ===
import decimal
import math
import operator
import sys
import warnings
from fractions import Fraction
from functools import partial

import hypothesis
import hypothesis.strategies as st
import pytest
from hypothesis.extra.numpy import arrays

import numpy as np
import numpy.lib._function_base_impl as nfb
from numpy import (
    angle,
    average,
    bartlett,
    blackman,
    corrcoef,
    cov,
    delete,
    diff,
    digitize,
    extract,
    flipud,
    gradient,
    hamming,
    hanning,
    i0,
    insert,
    interp,
    kaiser,
    ma,
    meshgrid,
    piecewise,
    place,
    rot90,
    select,
    setxor1d,
    sinc,
    trapezoid,
    trim_zeros,
    unique,
    unwrap,
    vectorize,
)
from numpy._core.numeric import normalize_axis_tuple
from numpy.exceptions import AxisError
from numpy.random import rand
from numpy.testing import (
    HAS_REFCOUNT,
    IS_WASM,
    NOGIL_BUILD,
    assert_,
    assert_allclose,
    assert_almost_equal,
    assert_array_almost_equal,
    assert_array_equal,
    assert_equal,
    assert_raises,
    assert_raises_regex,
    assert_warns,
    suppress_warnings,
)


def get_mat(n):
    data = np.arange(n)
    data = np.add.outer(data, data)
    return data


def _make_complex(real, imag):
    """
    Like real + 1j * imag, but behaves as expected when imag contains non-finite
    values
    """
    ret = np.zeros(np.broadcast(real, imag).shape, np.complex128)
    ret.real = real
    ret.imag = imag
    return ret


class TestRot90:
    def test_basic(self):
        assert_raises(ValueError, rot90, np.ones(4))
        assert_raises(ValueError, rot90, np.ones((2, 2, 2)), axes=(0, 1, 2))
        assert_raises(ValueError, rot90, np.ones((2, 2)), axes=(0, 2))
        assert_raises(ValueError, rot90, np.ones((2, 2)), axes=(1, 1))
        assert_raises(ValueError, rot90, np.ones((2, 2, 2)), axes=(-2, 1))

        a = [[0, 1, 2],
             [3, 4, 5]]
        b1 = [[2, 5],
              [1, 4],
              [0, 3]]
        b2 = [[5, 4, 3],
              [2, 1, 0]]
        b3 = [[3, 0],
              [4, 1],
              [5, 2]]
        b4 = [[0, 1, 2],
              [3, 4, 5]]

        for k in range(-3, 13, 4):
            assert_equal(rot90(a, k=k), b1)
        for k in range(-2, 13, 4):
            assert_equal(rot90(a, k=k), b2)
        for k in range(-1, 13, 4):
            assert_equal(rot90(a, k=k), b3)
        for k in range(0, 13, 4):
            assert_equal(rot90(a, k=k), b4)

        assert_equal(rot90(rot90(a, axes=(0, 1)), axes=(1, 0)), a)
        assert_equal(rot90(a, k=1, axes=(1, 0)), rot90(a, k=-1, axes=(0, 1)))

    def test_axes(self):
        a = np.ones((50, 40, 3))
        assert_equal(rot90(a).shape, (40, 50, 3))
        assert_equal(rot90(a, axes=(0, 2)), rot90(a, axes=(0, -1)))
        assert_equal(rot90(a, axes=(1, 2)), rot90(a, axes=(-2, -1)))

    def test_rotation_axes(self):
        a = np.arange(8).reshape((2, 2, 2))

        a_rot90_01 = [[[2, 3],
                       [6, 7]],
                      [[0, 1],
                       [4, 5]]]
        a_rot90_12 = [[[1, 3],
                       [0, 2]],
                      [[5, 7],
                       [4, 6]]]
        a_rot90_20 = [[[4, 0],
                       [6, 2]],
                      [[5, 1],
                       [7, 3]]]
        a_rot90_10 = [[[4, 5],
                       [0, 1]],
                      [[6, 7],
                       [2, 3]]]

        assert_equal(rot90(a, axes=(0, 1)), a_rot90_01)
        assert_equal(rot90(a, axes=(1, 0)), a_rot90_10)
        assert_equal(rot90(a, axes=(1, 2)), a_rot90_12)

        for k in range(1, 5):
            assert_equal(rot90(a, k=k, axes=(2, 0)),
                         rot90(a_rot90_20, k=k - 1, axes=(2, 0)))


class TestFlip:

    def test_axes(self):
        assert_raises(AxisError, np.flip, np.ones(4), axis=1)
        assert_raises(AxisError, np.flip, np.ones((4, 4)), axis=2)
        assert_raises(AxisError, np.flip, np.ones((4, 4)), axis=-3)
        assert_raises(AxisError, np.flip, np.ones((4, 4)), axis=(0, 3))

    def test_basic_lr(self):
        a = get_mat(4)
        b = a[:, ::-1]
        assert_equal(np.flip(a, 1), b)
        a = [[0, 1, 2],
             [3, 4, 5]]
        b = [[2, 1, 0],
             [5, 4, 3]]
        assert_equal(np.flip(a, 1), b)

    def test_basic_ud(self):
        a = get_mat(4)
        b = a[::-1, :]
        assert_equal(np.flip(a, 0), b)
        a = [[0, 1, 2],
             [3, 4, 5]]
        b = [[3, 4, 5],
             [0, 1, 2]]
        assert_equal(np.flip(a, 0), b)

    def test_3d_swap_axis0(self):
        a = np.array([[[0, 1],
                       [2, 3]],
                      [[4, 5],
                       [6, 7]]])

        b = np.array([[[4, 5],
                       [6, 7]],
                      [[0, 1],
                       [2, 3]]])

        assert_equal(np.flip(a, 0), b)

    def test_3d_swap_axis1(self):
        a = np.array([[[0, 1],
                       [2, 3]],
                      [[4, 5],
                       [6, 7]]])

        b = np.array([[[2, 3],
                       [0, 1]],
                      [[6, 7],
                       [4, 5]]])

        assert_equal(np.flip(a, 1), b)

    def test_3d_swap_axis2(self):
        a = np.array([[[0, 1],
                       [2, 3]],
                      [[4, 5],
                       [6, 7]]])

        b = np.array([[[1, 0],
                       [3, 2]],
                      [[5, 4],
                       [7, 6]]])

        assert_equal(np.flip(a, 2), b)

    def test_4d(self):
        a = np.arange(2 * 3 * 4 * 5).reshape(2, 3, 4, 5)
        for i in range(a.ndim):
            assert_equal(np.flip(a, i),
                         np.flipud(a.swapaxes(0, i)).swapaxes(i, 0))

    def test_default_axis(self):
        a = np.array([[1, 2, 3],
                      [4, 5, 6]])
        b = np.array([[6, 5, 4],
                      [3, 2, 1]])
        assert_equal(np.flip(a), b)

    def test_multiple_axes(self):
        a = np.array([[[0, 1],
                       [2, 3]],
                      [[4, 5],
                       [6, 7]]])

        assert_equal(np.flip(a, axis=()), a)

        b = np.array([[[5, 4],
                       [7, 6]],
                      [[1, 0],
                       [3, 2]]])

        assert_equal(np.flip(a, axis=(0, 2)), b)

        c = np.array([[[3, 2],
                       [1, 0]],
                      [[7, 6],
                       [5, 4]]])

        assert_equal(np.flip(a, axis=(1, 2)), c)


class TestAny:

    def test_basic(self):
        y1 = [0, 0, 1, 0]
        y2 = [0, 0, 0, 0]
        y3 = [1, 0, 1, 0]
        assert_(np.any(y1))
        assert_(np.any(y3))
        assert_(not np.any(y2))

    def test_nd(self):
        y1 = [[0, 0, 0], [0, 1, 0], [1, 1, 0]]
        assert_(np.any(y1))
        assert_array_equal(np.any(y1, axis=0), [1, 1, 0])
        assert_array_equal(np.any(y1, axis=1), [0, 1, 1])


class TestAll:

    def test_basic(self):
        y1 = [0, 1, 1, 0]
        y2 = [0, 0, 0, 0]
        y3 = [1, 1, 1, 1]
        assert_(not np.all(y1))
        assert_(np.all(y3))
        assert_(not np.all(y2))
        assert_(np.all(~np.array(y2)))

    def test_nd(self):
        y1 = [[0, 0, 1], [0, 1, 1], [1, 1, 1]]
        assert_(not np.all(y1))
        assert_array_equal(np.all(y1, axis=0), [0, 0, 1])
        assert_array_equal(np.all(y1, axis=1), [0, 0, 1])


@pytest.mark.parametrize("dtype", ["i8", "U10", "object", "datetime64[ms]"])
def test_any_and_all_result_dtype(dtype):
    arr = np.ones(3, dtype=dtype)
    assert np.any(arr).dtype == np.bool
    assert np.all(arr).dtype == np.bool


class TestCopy:

    def test_basic(self):
        a = np.array([[1, 2], [3, 4]])
        a_copy = np.copy(a)
        assert_array_equal(a, a_copy)
        a_copy[0, 0] = 10
        assert_equal(a[0, 0], 1)
        assert_equal(a_copy[0, 0], 10)

    def test_order(self):
        # It turns out that people rely on np.copy() preserving order by
        # default; changing this broke scikit-learn:
        # github.com/scikit-learn/scikit-learn/commit/7842748cf777412c506a8c0ed28090711d3a3783
        a = np.array([[1, 2], [3, 4]])
        assert_(a.flags.c_contiguous)
        assert_(not a.flags.f_contiguous)
        a_fort = np.array([[1, 2], [3, 4]], order="F")
        assert_(not a_fort.flags.c_contiguous)
        assert_(a_fort.flags.f_contiguous)
        a_copy = np.copy(a)
        assert_(a_copy.flags.c_contiguous)
        assert_(not a_copy.flags.f_contiguous)
        a_fort_copy = np.copy(a_fort)
        assert_(not a_fort_copy.flags.c_contiguous)
        assert_(a_fort_copy.flags.f_contiguous)

    def test_subok(self):
        mx = ma.ones(5)
        assert_(not ma.isMaskedArray(np.copy(mx, subok=False)))
        assert_(ma.isMaskedArray(np.copy(mx, subok=True)))
        # Default behavior
        assert_(not ma.isMaskedArray(np.copy(mx)))


class TestAverage:

    def test_basic(self):
        y1 = np.array([1, 2, 3])
        assert_(average(y1, axis=0) == 2.)
        y2 = np.array([1., 2., 3.])
        assert_(average(y2, axis=0) == 2.)
        y3 = [0., 0., 0.]
        assert_(average(y3, axis=0) == 0.)

        y4 = np.ones((4, 4))
        y4[0, 1] = 0
        y4[1, 0] = 2
        assert_almost_equal(y4.mean(0), average(y4, 0))
        assert_almost_equal(y4.mean(1), average(y4, 1))

        y5 = rand(5, 5)
        assert_almost_equal(y5.mean(0), average(y5, 0))
        assert_almost_equal(y5.mean(1), average(y5, 1))

    @pytest.mark.parametrize(
        'x, axis, expected_avg, weights, expected_wavg, expected_wsum',
        [([1, 2, 3], None, [2.0], [3, 4, 1], [1.75], [8.0]),
         ([[1, 2, 5], [1, 6, 11]], 0, [[1.0, 4.0, 8.0]],
          [1, 3], [[1.0, 5.0, 9.5]], [[4, 4, 4]])],
    )
    def test_basic_keepdims(self, x, axis, expected_avg,
                            weights, expected_wavg, expected_wsum):
        avg = np.average(x, axis=axis, keepdims=True)
        assert avg.shape == np.shape(expected_avg)
        assert_array_equal(avg, expected_avg)

        wavg = np.average(x, axis=axis, weights=weights, keepdims=True)
        assert wavg.shape == np.shape(expected_wavg)
        assert_array_equal(wavg, expected_wavg)

        wavg, wsum = np.average(x, axis=axis, weights=weights, returned=True,
                                keepdims=True)
        assert wavg.shape == np.shape(expected_wavg)
        assert_array_equal(wavg, expected_wavg)
        assert wsum.shape == np.shape(expected_wsum)
        assert_array_equal(wsum, expected_wsum)

    def test_weights(self):
        y = np.arange(10)
        w = np.arange(10)
        actual = average(y, weights=w)
        desired = (np.arange(10) ** 2).sum() * 1. / np.arange(10).sum()
        assert_almost_equal(actual, desired)

        y1 = np.array([[1, 2, 3], [4, 5, 6]])
        w0 = [1, 2]
        actual = average(y1, weights=w0, axis=0)
        desired = np.array([3., 4., 5.])
        assert_almost_equal(actual, desired)

        w1 = [0, 0, 1]
        actual = average(y1, weights=w1, axis=1)
        desired = np.array([3., 6.])
        assert_almost_equal(actual, desired)

        # weights and input have different shapes but no axis is specified
        with pytest.raises(
                TypeError,
                match="Axis must be specified when shapes of a "
                      "and weights differ"):
            average(y1, weights=w1)

        # 2D Case
        w2 = [[0, 0, 1], [0, 0, 2]]
        desired = np.array([3., 6.])
        assert_array_equal(average(y1, weights=w2, axis=1), desired)
        assert_equal(average(y1, weights=w2), 5.)

        y3 = rand(5).astype(np.float32)
        w3 = rand(5).astype(np.float64)

        assert_(np.average(y3, weights=w3).dtype == np.result_type(y3, w3))

        # test weights with `keepdims=False` and `keepdims=True`
        x = np.array([2, 3, 4]).reshape(3, 1)
        w = np.array([4, 5, 6]).reshape(3, 1)

        actual = np.average(x, weights=w, axis=1, keepdims=False)
        desired = np.array([2., 3., 4.])
        assert_array_equal(actual, desired)

        actual = np.average(x, weights=w, axis=1, keepdims=True)
        desired = np.array([[2.], [3.], [4.]])
        assert_array_equal(actual, desired)

    def test_weight_and_input_dims_different(self):
        y = np.arange(12).reshape(2, 2, 3)
        w = np.array([0., 0., 1., .5, .5, 0., 0., .5, .5, 1., 0., 0.])\
            .reshape(2, 2, 3)

        subw0 = w[:, :, 0]
        actual = average(y, axis=(0, 1), weights=subw0)
        desired = np.array([7., 8., 9.])
        assert_almost_equal(actual, desired)

        subw1 = w[1, :, :]
        actual = average(y, axis=(1, 2), weights=subw1)
        desired = np.array([2.25, 8.25])
        assert_almost_equal(actual, desired)

        subw2 = w[:, 0, :]
        actual = average(y, axis=(0, 2), weights=subw2)
        desired = np.array([4.75, 7.75])
        assert_almost_equal(actual, desired)

        # here the weights have the wrong shape for the specified axes
        with pytest.raises(
                ValueError,
                match="Shape of weights must be consistent with "
                      "shape of a along specified axis"):
            average(y, axis=(0, 1, 2), weights=subw0)

        with pytest.raises(
                ValueError,
                match="Shape of weights must be consistent with "
                      "shape of a along specified axis"):
            average(y, axis=(0, 1), weights=subw1)

        # swapping the axes should be same as transposing weights
        actual = average(y, axis=(1, 0), weights=subw0)
        desired = average(y, axis=(0, 1), weights=subw0.T)
        assert_almost_equal(actual, desired)

        # if average over all axes, should have float output
        actual = average(y, axis=(0, 1, 2), weights=w)
        assert_(actual.ndim == 0)

    def test_returned(self):
        y = np.array([[1, 2, 3], [4, 5, 6]])

        # No weights
        avg, scl = average(y, returned=True)
        assert_equal(scl, 6.)

        avg, scl = average(y, 0, returned=True)
        assert_array_equal(scl, np.array([2., 2., 2.]))

        avg, scl = average(y, 1, returned=True)
        assert_array_equal(scl, np.array([3., 3.]))

        # With weights
        w0 = [1, 2]
        avg, scl = average(y, weights=w0, axis=0, returned=True)
        assert_array_equal(scl, np.array([3., 3., 3.]))

        w1 = [1, 2, 3]
        avg, scl = average(y, weights=w1, axis=1, returned=True)
        assert_array_equal(scl, np.array([6., 6.]))

        w2 = [[0, 0, 1], [1, 2, 3]]
        avg, scl = average(y, weights=w2, axis=1, returned=True)
        assert_array_equal(scl, np.array([1., 6.]))

    def test_subclasses(self):
        class subclass(np.ndarray):
            pass
        a = np.array([[1, 2], [3, 4]]).view(subclass)
        w = np.array([[1, 2], [3, 4]]).view(subclass)

        assert_equal(type(np.average(a)), subclass)
        assert_equal(type(np.average(a, weights=w)), subclass)

    def test_upcasting(self):
        typs = [('i4', 'i4', 'f8'), ('i4', 'f4', 'f8'), ('f4', 'i4', 'f8'),
                 ('f4', 'f4', 'f4'), ('f4', 'f8', 'f8')]
        for at, wt, rt in typs:
            a = np.array([[1, 2], [3, 4]], dtype=at)
            w = np.array([[1, 2], [3, 4]], dtype=wt)
            assert_equal(np.average(a, weights=w).dtype, np.dtype(rt))

    def test_object_dtype(self):
        a = np.array([decimal.Decimal(x) for x in range(10)])
        w = np.array([decimal.Decimal(1) for _ in range(10)])
        w /= w.sum()
        assert_almost_equal(a.mean(0), average(a, weights=w))

    def test_object_no_weights(self):
        a = np.array([decimal.Decimal(x) for x in range(10)])
        m = average(a)
        assert m == decimal.Decimal('4.5')

    def test_average_class_without_dtype(self):
        # see gh-21988
        a = np.array([Fraction(1, 5), Fraction(3, 5)])
        assert_equal(np.average(a), Fraction(2, 5))


class TestSelect:
    choices = [np.array([1, 2, 3]),
               np.array([4, 5, 6]),
               np.array([7, 8, 9])]
    conditions = [np.array([False, False, False]),
                  np.array([False, True, False]),
                  np.array([False, False, True])]

    def _select(self, cond, values, default=0):
        output = []
        for m in range(len(cond)):
            output += [V[m] for V, C in zip(values, cond) if C[m]] or [default]
        return output

    def test_basic(self):
        choices = self.choices
        conditions = self.conditions
        assert_array_equal(select(conditions, choices, default=15),
                           self._select(conditions, choices, default=15))

        assert_equal(len(choices), 3)
        assert_equal(len(conditions), 3)

    def test_broadcasting(self):
        conditions = [np.array(True), np.array([False, True, False])]
        choices = [1, np.arange(12).reshape(4, 3)]
        assert_array_equal(select(conditions, choices), np.ones((4, 3)))
        # default can broadcast too:
        assert_equal(select([True], [0], default=[0]).shape, (1,))

    def test_return_dtype(self):
        assert_equal(select(self.conditions, self.choices, 1j).dtype,
                     np.complex128)
        # But the conditions need to be stronger then the scalar default
        # if it is scalar.
        choices = [choice.astype(np.int8) for choice in self.choices]
        assert_equal(select(self.conditions, choices).dtype, np.int8)

        d = np.array([1, 2, 3, np.nan, 5, 7])
        m = np.isnan(d)
        assert_equal(select([m], [d]), [0, 0, 0, np.nan, 0, 0])

    def test_deprecated_empty(self):
        assert_raises(ValueError, select, [], [], 3j)
        assert_raises(ValueError, select, [], [])

    def test_non_bool_deprecation(self):
        choices = self.choices
        conditions = self.conditions[:]
        conditions[0] = conditions[0].astype(np.int_)
        assert_raises(TypeError, select, conditions, choices)
        conditions[0] = conditions[0].astype(np.uint8)
        assert_raises(TypeError, select, conditions, choices)
        assert_raises(TypeError, select, conditions, choices)

    def test_many_arguments(self):
        # This used to be limited by NPY_MAXARGS == 32
        conditions = [np.array([False])] * 100
        choices = [np.array([1])] * 100
        select(conditions, choices)


class TestInsert:

    def test_basic(self):
        a = [1, 2, 3]
        assert_equal(insert(a, 0, 1), [1, 1, 2, 3])
        assert_equal(insert(a, 3, 1), [1, 2, 3, 1])
        assert_equal(insert(a, [1, 1, 1], [1, 2, 3]), [1, 1, 2, 3, 2, 3])
        assert_equal(insert(a, 1, [1, 2, 3]), [1, 1, 2, 3, 2, 3])
        assert_equal(insert(a, [1, -1, 3], 9), [1, 9, 2, 9, 3, 9])
        assert_equal(insert(a, slice(-1, None, -1), 9), [9, 1, 9, 2, 9, 3])
        assert_equal(insert(a, [-1, 1, 3], [7, 8, 9]), [1, 8, 2, 7, 3, 9])
        b = np.array([0, 1], dtype=np.float64)
        assert_equal(insert(b, 0, b[0]), [0., 0., 1.])
        assert_equal(insert(b, [], []), b)
        assert_equal(insert(a, np.array([True] * 4), 9), [9, 1, 9, 2, 9, 3, 9])
        assert_equal(insert(a, np.array([True, False, True, False]), 9),
                     [9, 1, 2, 9, 3])

    def test_multidim(self):
        a = [[1, 1, 1]]
        r = [[2, 2, 2],
             [1, 1, 1]]
        assert_equal(insert(a, 0, [1]), [1, 1, 1, 1])
        assert_equal(insert(a, 0, [2, 2, 2], axis=0), r)
        assert_equal(insert(a, 0, 2, axis=0), r)
        assert_equal(insert(a, 2, 2, axis=1), [[1, 1, 2, 1]])

        a = np.array([[1, 1], [2, 2], [3, 3]])
        b = np.arange(1, 4).repeat(3).reshape(3, 3)
        c = np.concatenate(
            (a[:, 0:1], np.arange(1, 4).repeat(3).reshape(3, 3).T,
             a[:, 1:2]), axis=1)
        assert_equal(insert(a, [1], [[1], [2], [3]], axis=1), b)
        assert_equal(insert(a, [1], [1, 2, 3], axis=1), c)
        # scalars behave differently, in this case exactly opposite:
        assert_equal(insert(a, 1, [1, 2, 3], axis=1), b)
        assert_equal(insert(a, 1, [[1], [2], [3]], axis=1), c)

        a = np.arange(4).reshape(2, 2)
        assert_equal(insert(a[:, :1], 1, a[:, 1], axis=1), a)
        assert_equal(insert(a[:1, :], 1, a[1, :], axis=0), a)

        # negative axis value
        a = np.arange(24).reshape((2, 3, 4))
        assert_equal(insert(a, 1, a[:, :, 3], axis=-1),
                     insert(a, 1, a[:, :, 3], axis=2))
        assert_equal(insert(a, 1, a[:, 2, :], axis=-2),
                     insert(a, 1, a[:, 2, :], axis=1))

        # invalid axis value
        assert_raises(AxisError, insert, a, 1, a[:, 2, :], axis=3)
        assert_raises(AxisError, insert, a, 1, a[:, 2, :], axis=-4)

        # negative axis value
        a = np.arange(24).reshape((2, 3, 4))
        assert_equal(insert(a, 1, a[:, :, 3], axis=-1),
                     insert(a, 1, a[:, :, 3], axis=2))
        assert_equal(insert(a, 1, a[:, 2, :], axis=-2),
                     insert(a, 1, a[:, 2, :], axis=1))

    def test_0d(self):
        a = np.array(1)
        with pytest.raises(AxisError):
            insert(a, [], 2, axis=0)
        with pytest.raises(TypeError):
            insert(a, [], 2, axis="nonsense")

    def test_subclass(self):
        class SubClass(np.ndarray):
            pass
        a = np.arange(10).view(SubClass)
        assert_(isinstance(np.insert(a, 0, [0]), SubClass))
        assert_(isinstance(np.insert(a, [], []), SubClass))
        assert_(isinstance(np.insert(a, [0, 1], [1, 2]), SubClass))
        assert_(isinstance(np.insert(a, slice(1, 2), [1, 2]), SubClass))
        assert_(isinstance(np.insert(a, slice(1, -2, -1), []), SubClass))
        # This is an error in the future:
        a = np.array(1).view(SubClass)
        assert_(isinstance(np.insert(a, 0, [0]), SubClass))

    def test_index_array_copied(self):
        x = np.array([1, 1, 1])
        np.insert([0, 1, 2], x, [3, 4, 5])
        assert_equal(x, np.array([1, 1, 1]))

    def test_structured_array(self):
        a = np.array([(1, 'a'), (2, 'b'), (3, 'c')],
                     dtype=[('foo', 'i'), ('bar', 'S1')])
        val = (4, 'd')
        b = np.insert(a, 0, val)
        assert_array_equal(b[0], np.array(val, dtype=b.dtype))
        val = [(4, 'd')] * 2
        b = np.insert(a, [0, 2], val)
        assert_array_equal(b[[0, 3]], np.array(val, dtype=b.dtype))

    def test_index_floats(self):
        with pytest.raises(IndexError):
            np.insert([0, 1, 2], np.array([1.0, 2.0]), [10, 20])
        with pytest.raises(IndexError):
            np.insert([0, 1, 2], np.array([], dtype=float), [])

    @pytest.mark.parametrize('idx', [4, -4])
    def test_index_out_of_bounds(self, idx):
        with pytest.raises(IndexError, match='out of bounds'):
            np.insert([0, 1, 2], [idx], [3, 4])


class TestAmax:

    def test_basic(self):
        a = [3, 4, 5, 10, -3, -5, 6.0]
        assert_equal(np.amax(a), 10.0)
        b = [[3, 6.0, 9.0],
             [4, 10.0, 5.0],
             [8, 3.0, 2.0]]
        assert_equal(np.amax(b, axis=0), [8.0, 10.0, 9.0])
        assert_equal(np.amax(b, axis=1), [9.0, 10.0, 8.0])


class TestAmin:

    def test_basic(self):
        a = [3, 4, 5, 10, -3, -5, 6.0]
        assert_equal(np.amin(a), -5.0)
        b = [[3, 6.0, 9.0],
             [4, 10.0, 5.0],
             [8, 3.0, 2.0]]
        assert_equal(np.amin(b, axis=0), [3.0, 3.0, 2.0])
        assert_equal(np.amin(b, axis=1), [3.0, 4.0, 2.0])


class TestPtp:

    def test_basic(self):
        a = np.array([3, 4, 5, 10, -3, -5, 6.0])
        assert_equal(np.ptp(a, axis=0), 15.0)
        b = np.array([[3, 6.0, 9.0],
                      [4, 10.0, 5.0],
                      [8, 3.0, 2.0]])
        assert_equal(np.ptp(b, axis=0), [5.0, 7.0, 7.0])
        assert_equal(np.ptp(b, axis=-1), [6.0, 6.0, 6.0])

        assert_equal(np.ptp(b, axis=0, keepdims=True), [[5.0, 7.0, 7.0]])
        assert_equal(np.ptp(b, axis=(0, 1), keepdims=True), [[8.0]])


class TestCumsum:

    @pytest.mark.parametrize("cumsum", [np.cumsum, np.cumulative_sum])
    def test_basic(self, cumsum):
        ba = [1, 2, 10, 11, 6, 5, 4]
        ba2 = [[1, 2, 3, 4], [5, 6, 7, 9], [10, 3, 4, 5]]
        for ctype in [np.int8, np.uint8, np.int16, np.uint16, np.int32,
                      np.uint32, np.float32, np.float64, np.complex64,
                      np.complex128]:
            a = np.array(ba, ctype)
            a2 = np.array(ba2, ctype)

            tgt = np.array([1, 3, 13, 24, 30, 35, 39], ctype)
            assert_array_equal(cumsum(a, axis=0), tgt)

            tgt = np.array(
                [[1, 2, 3, 4], [6, 8, 10, 13], [16, 11, 14, 18]], ctype)
            assert_array_equal(cumsum(a2, axis=0), tgt)

            tgt = np.array(
                [[1, 3, 6, 10], [5, 11, 18, 27], [10, 13, 17, 22]], ctype)
            assert_array_equal(cumsum(a2, axis=1), tgt)


class TestProd:

    def test_basic(self):
        ba = [1, 2, 10, 11, 6, 5, 4]
        ba2 = [[1, 2, 3, 4], [5, 6, 7, 9], [10, 3, 4, 5]]
        for ctype in [np.int16, np.uint16, np.int32, np.uint32,
                      np.float32, np.float64, np.complex64, np.complex128]:
            a = np.array(ba, ctype)
            a2 = np.array(ba2, ctype)
            if ctype in ['1', 'b']:
                assert_raises(ArithmeticError, np.prod, a)
                assert_raises(ArithmeticError, np.prod, a2, 1)
            else:
                assert_equal(a.prod(axis=0), 26400)
                assert_array_equal(a2.prod(axis=0),
                                   np.array([50, 36, 84, 180], ctype))
                assert_array_equal(a2.prod(axis=-1),
                                   np.array([24, 1890, 600], ctype))


class TestCumprod:

    @pytest.mark.parametrize("cumprod", [np.cumprod, np.cumulative_prod])
    def test_basic(self, cumprod):
        ba = [1, 2, 10, 11, 6, 5, 4]
        ba2 = [[1, 2, 3, 4], [5, 6, 7, 9], [10, 3, 4, 5]]
        for ctype in [np.int16, np.uint16, np.int32, np.uint32,
                      np.float32, np.float64, np.complex64, np.complex128]:
            a = np.array(ba, ctype)
            a2 = np.array(ba2, ctype)
            if ctype in ['1', 'b']:
                assert_raises(ArithmeticError, cumprod, a)
                assert_raises(ArithmeticError, cumprod, a2, 1)
                assert_raises(ArithmeticError, cumprod, a)
            else:
                assert_array_equal(cumprod(a, axis=-1),
                                   np.array([1, 2, 20, 220,
                                             1320, 6600, 26400], ctype))
                assert_array_equal(cumprod(a2, axis=0),
                                   np.array([[1, 2, 3, 4],
                                             [5, 12, 21, 36],
                                             [50, 36, 84, 180]], ctype))
                assert_array_equal(cumprod(a2, axis=-1),
                                   np.array([[1, 2, 6, 24],
                                             [5, 30, 210, 1890],
                                             [10, 30, 120, 600]], ctype))


def test_cumulative_include_initial():
    arr = np.arange(8).reshape((2, 2, 2))

    expected = np.array([
        [[0, 0], [0, 1], [2, 4]], [[0, 0], [4, 5], [10, 12]]
    ])
    assert_array_equal(
        np.cumulative_sum(arr, axis=1, include_initial=True), expected
    )

    expected = np.array([
        [[1, 0, 0], [1, 2, 6]], [[1, 4, 20], [1, 6, 42]]
    ])
    assert_array_equal(
        np.cumulative_prod(arr, axis=2, include_initial=True), expected
    )

    out = np.zeros((3, 2), dtype=np.float64)
    expected = np.array([[0, 0], [1, 2], [4, 6]], dtype=np.float64)
    arr = np.arange(1, 5).reshape((2, 2))
    np.cumulative_sum(arr, axis=0, out=out, include_initial=True)
    assert_array_equal(out, expected)

    expected = np.array([1, 2, 4])
    assert_array_equal(
        np.cumulative_prod(np.array([2, 2]), include_initial=True), expected
    )


class TestDiff:

    def test_basic(self):
        x = [1, 4, 6, 7, 12]
        out = np.array([3, 2, 1, 5])
        out2 = np.array([-1, -1, 4])
        out3 = np.array([0, 5])
        assert_array_equal(diff(x), out)
        assert_array_equal(diff(x, n=2), out2)
        assert_array_equal(diff(x, n=3), out3)

        x = [1.1, 2.2, 3.0, -0.2, -0.1]
        out = np.array([1.1, 0.8, -3.2, 0.1])
        assert_almost_equal(diff(x), out)

        x = [True, True, False, False]
        out = np.array([False, True, False])
        out2 = np.array([True, True])
        assert_array_equal(diff(x), out)
        assert_array_equal(diff(x, n=2), out2)

    def test_axis(self):
        x = np.zeros((10, 20, 30))
        x[:, 1::2, :] = 1
        exp = np.ones((10, 19, 30))
        exp[:, 1::2, :] = -1
        assert_array_equal(diff(x), np.zeros((10, 20, 29)))
        assert_array_equal(diff(x, axis=-1), np.zeros((10, 20, 29)))
        assert_array_equal(diff(x, axis=0), np.zeros((9, 20, 30)))
        assert_array_equal(diff(x, axis=1), exp)
        assert_array_equal(diff(x, axis=-2), exp)
        assert_raises(AxisError, diff, x, axis=3)
        assert_raises(AxisError, diff, x, axis=-4)

        x = np.array(1.11111111111, np.float64)
        assert_raises(ValueError, diff, x)

    def test_nd(self):
        x = 20 * rand(10, 20, 30)
        out1 = x[:, :, 1:] - x[:, :, :-1]
        out2 = out1[:, :, 1:] - out1[:, :, :-1]
        out3 = x[1:, :, :] - x[:-1, :, :]
        out4 = out3[1:, :, :] - out3[:-1, :, :]
        assert_array_equal(diff(x), out1)
        assert_array_equal(diff(x, n=2), out2)
        assert_array_equal(diff(x, axis=0), out3)
        assert_array_equal(diff(x, n=2, axis=0), out4)

    def test_n(self):
        x = list(range(3))
        assert_raises(ValueError, diff, x, n=-1)
        output = [diff(x, n=n) for n in range(1, 5)]
        expected = [[1, 1], [0], [], []]
        assert_(diff(x, n=0) is x)
        for n, (expected_n, output_n) in enumerate(zip(expected, output), start=1):
            assert_(type(output_n) is np.ndarray)
            assert_array_equal(output_n, expected_n)
            assert_equal(output_n.dtype, np.int_)
            assert_equal(len(output_n), max(0, len(x) - n))

    def test_times(self):
        x = np.arange('1066-10-13', '1066-10-16', dtype=np.datetime64)
        expected = [
            np.array([1, 1], dtype='timedelta64[D]'),
            np.array([0], dtype='timedelta64[D]'),
        ]
        expected.extend([np.array([], dtype='timedelta64[D]')] * 3)
        for n, exp in enumerate(expected, start=1):
            out = diff(x, n=n)
            assert_array_equal(out, exp)
            assert_equal(out.dtype, exp.dtype)

    def test_subclass(self):
        x = ma.array([[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]],
                     mask=[[False, False], [True, False],
                           [False, True], [True, True], [False, False]])
        out = diff(x)
        assert_array_equal(out.data, [[1], [1], [1], [1], [1]])
        assert_array_equal(out.mask, [[False], [True],
                                      [True], [True], [False]])
        assert_(type(out) is type(x))

        out3 = diff(x, n=3)
        assert_array_equal(out3.data, [[], [], [], [], []])
        assert_array_equal(out3.mask, [[], [], [], [], []])
        assert_(type(out3) is type(x))

    def test_prepend(self):
        x = np.arange(5) + 1
        assert_array_equal(diff(x, prepend=0), np.ones(5))
        assert_array_equal(diff(x, prepend=[0]), np.ones(5))
        assert_array_equal(np.cumsum(np.diff(x, prepend=0)), x)
        assert_array_equal(diff(x, prepend=[-1, 0]), np.ones(6))

        x = np.arange(4).reshape(2, 2)
        result = np.diff(x, axis=1, prepend=0)
        expected = [[0, 1], [2, 1]]
        assert_array_equal(result, expected)
        result = np.diff(x, axis=1, prepend=[[0], [0]])
        assert_array_equal(result, expected)

        result = np.diff(x, axis=0, prepend=0)
        expected = [[0, 1], [2, 2]]
        assert_array_equal(result, expected)
        result = np.diff(x, axis=0, prepend=[[0, 0]])
        assert_array_equal(result, expected)

        assert_raises(ValueError, np.diff, x, prepend=np.zeros((3, 3)))

        assert_raises(AxisError, diff, x, prepend=0, axis=3)

    def test_append(self):
        x = np.arange(5)
        result = diff(x, append=0)
        expected = [1, 1, 1, 1, -4]
        assert_array_equal(result, expected)
        result = diff(x, append=[0])
        assert_array_equal(result, expected)
        result = diff(x, append=[0, 2])
        expected = expected + [2]
        assert_array_equal(result, expected)

        x = np.arange(4).reshape(2, 2)
        result = np.diff(x, axis=1, append=0)
        expected = [[1, -1], [1, -3]]
        assert_array_equal(result, expected)
        result = np.diff(x, axis=1, append=[[0], [0]])
        assert_array_equal(result, expected)

        result = np.diff(x, axis=0, append=0)
        expected = [[2, 2], [-2, -3]]
        assert_array_equal(result, expected)
        result = np.diff(x, axis=0, append=[[0, 0]])
        assert_array_equal(result, expected)

        assert_raises(ValueError, np.diff, x, append=np.zeros((3, 3)))

        assert_raises(AxisError, diff, x, append=0, axis=3)


class TestDelete:

    def setup_method(self):
        self.a = np.arange(5)
        self.nd_a = np.arange(5).repeat(2).reshape(1, 5, 2)

    def _check_inverse_of_slicing(self, indices):
        a_del = delete(self.a, indices)
        nd_a_del = delete(self.nd_a, indices, axis=1)
        msg = f'Delete failed for obj: {indices!r}'
        assert_array_equal(setxor1d(a_del, self.a[indices, ]), self.a,
                           err_msg=msg)
        xor = setxor1d(nd_a_del[0, :, 0], self.nd_a[0, indices, 0])
        assert_array_equal(xor, self.nd_a[0, :, 0], err_msg=msg)

    def test_slices(self):
        lims = [-6, -2, 0, 1, 2, 4, 5]
        steps = [-3, -1, 1, 3]
        for start in lims:
            for stop in lims:
                for step in steps:
                    s = slice(start, stop, step)
                    self._check_inverse_of_slicing(s)

    def test_fancy(self):
        self._check_inverse_of_slicing(np.array([[0, 1], [2, 1]]))
        with pytest.raises(IndexError):
            delete(self.a, [100])
        with pytest.raises(IndexError):
            delete(self.a, [-100])

        self._check_inverse_of_slicing([0, -1, 2, 2])

        self._check_inverse_of_slicing([True, False, False, True, False])

        # not legal, indexing with these would change the dimension
        with pytest.raises(ValueError):
            delete(self.a, True)
        with pytest.raises(ValueError):
            delete(self.a, False)

        # not enough items
        with pytest.raises(ValueError):
            delete(self.a, [False] * 4)

    def test_single(self):
        self._check_inverse_of_slicing(0)
        self._check_inverse_of_slicing(-4)

    def test_0d(self):
        a = np.array(1)
        with pytest.raises(AxisError):
            delete(a, [], axis=0)
        with pytest.raises(TypeError):
            delete(a, [], axis="nonsense")

    def test_subclass(self):
        class SubClass(np.ndarray):
            pass
        a = self.a.view(SubClass)
        assert_(isinstance(delete(a, 0), SubClass))
        assert_(isinstance(delete(a, []), SubClass))
        assert_(isinstance(delete(a, [0, 1]), SubClass))
        assert_(isinstance(delete(a, slice(1, 2)), SubClass))
        assert_(isinstance(delete(a, slice(1, -2)), SubClass))

    def test_array_order_preserve(self):
        # See gh-7113
        k = np.arange(10).reshape(2, 5, order='F')
        m = delete(k, slice(60, None), axis=1)

        # 'k' is Fortran ordered, and 'm' should have the
        # same ordering as 'k' and NOT become C ordered
        assert_equal(m.flags.c_contiguous, k.flags.c_contiguous)
        assert_equal(m.flags.f_contiguous, k.flags.f_contiguous)

    def test_index_floats(self):
        with pytest.raises(IndexError):
            np.delete([0, 1, 2], np.array([1.0, 2.0]))
        with pytest.raises(IndexError):
            np.delete([0, 1, 2], np.array([], dtype=float))

    @pytest.mark.parametrize("indexer", [np.array([1]), [1]])
    def test_single_item_array(self, indexer):
        a_del_int = delete(self.a, 1)
        a_del = delete(self.a, indexer)
        assert_equal(a_del_int, a_del)

        nd_a_del_int = delete(self.nd_a, 1, axis=1)
        nd_a_del = delete(self.nd_a, np.array([1]), axis=1)
        assert_equal(nd_a_del_int, nd_a_del)

    def test_single_item_array_non_int(self):
        # Special handling for integer arrays must not affect non-integer ones.
        # If `False` was cast to `0` it would delete the element:
        res = delete(np.ones(1), np.array([False]))
        assert_array_equal(res, np.ones(1))

        # Test the more complicated (with axis) case from gh-21840
        x = np.ones((3, 1))
        false_mask = np.array([False], dtype=bool)
        true_mask = np.array([True], dtype=bool)

        res = delete(x, false_mask, axis=-1)
        assert_array_equal(res, x)
        res = delete(x, true_mask, axis=-1)
        assert_array_equal(res, x[:, :0])

        # Object or e.g. timedeltas should *not* be allowed
        with pytest.raises(IndexError):
            delete(np.ones(2), np.array([0], dtype=object))

        with pytest.raises(IndexError):
            # timedeltas are sometimes "integral, but clearly not allowed:
            delete(np.ones(2), np.array([0], dtype="m8[ns]"))


class TestGradient:

    def test_basic(self):
        v = [[1, 1], [3, 4]]
        x = np.array(v)
        dx = [np.array([[2., 3.], [2., 3.]]),
              np.array([[0., 0.], [1., 1.]])]
        assert_array_equal(gradient(x), dx)
        assert_array_equal(gradient(v), dx)

    def test_args(self):
        dx = np.cumsum(np.ones(5))
        dx_uneven = [1., 2., 5., 9., 11.]
        f_2d = np.arange(25).reshape(5, 5)

        # distances must be scalars or have size equal to gradient[axis]
        gradient(np.arange(5), 3.)
        gradient(np.arange(5), np.array(3.))
        gradient(np.arange(5), dx)
        # dy is set equal to dx because scalar
        gradient(f_2d, 1.5)
        gradient(f_2d, np.array(1.5))

        gradient(f_2d, dx_uneven, dx_uneven)
        # mix between even and uneven spaces and
        # mix between scalar and vector
        gradient(f_2d, dx, 2)

        # 2D but axis specified
        gradient(f_2d, dx, axis=1)

        # 2d coordinate arguments are not yet allowed
        assert_raises_regex(ValueError, '.*scalars or 1d',
            gradient, f_2d, np.stack([dx] * 2, axis=-1), 1)

    def test_badargs(self):
        f_2d = np.arange(25).reshape(5, 5)
        x = np.cumsum(np.ones(5))

        # wrong sizes
        assert_raises(ValueError, gradient, f_2d, x, np.ones(2))
        assert_raises(ValueError, gradient, f_2d, 1, np.ones(2))
        assert_raises(ValueError, gradient, f_2d, np.ones(2), np.ones(2))
        # wrong number of arguments
        assert_raises(TypeError, gradient, f_2d, x)
        assert_raises(TypeError, gradient, f_2d, x, axis=(0, 1))
        assert_raises(TypeError, gradient, f_2d, x, x, x)
        assert_raises(TypeError, gradient, f_2d, 1, 1, 1)
        assert_raises(TypeError, gradient, f_2d, x, x, axis=1)
        assert_raises(TypeError, gradient, f_2d, 1, 1, axis=1)

    def test_datetime64(self):
        # Make sure gradient() can handle special types like datetime64
        x = np.array(
            ['1910-08-16', '1910-08-11', '1910-08-10', '1910-08-12',
             '1910-10-12', '1910-12-12', '1912-12-12'],
            dtype='datetime64[D]')
        dx = np.array(
            [-5, -3, 0, 31, 61, 396, 731],
            dtype='timedelta64[D]')
        assert_array_equal(gradient(x), dx)
        assert_(dx.dtype == np.dtype('timedelta64[D]'))

    def test_masked(self):
        # Make sure that gradient supports subclasses like masked arrays
        x = np.ma.array([[1, 1], [3, 4]],
                        mask=[[False, False], [False, False]])
        out = gradient(x)[0]
        assert_equal(type(out), type(x))
        # And make sure that the output and input don't have aliased mask
        # arrays
        assert_(x._mask is not out._mask)
        # Also check that edge_order=2 doesn't alter the original mask
        x2 = np.ma.arange(5)
        x2[2] = np.ma.masked
        np.gradient(x2, edge_order=2)
        assert_array_equal(x2.mask, [False, False, True, False, False])

    def test_second_order_accurate(self):
        # Testing that the relative numerical error is less that 3% for
        # this example problem. This corresponds to second order
        # accurate finite differences for all interior and boundary
        # points.
        x = np.linspace(0, 1, 10)
        dx = x[1] - x[0]
        y = 2 * x ** 3 + 4 * x ** 2 + 2 * x
        analytical = 6 * x ** 2 + 8 * x + 2
        num_error = np.abs((np.gradient(y, dx, edge_order=2) / analytical) - 1)
        assert_(np.all(num_error < 0.03) == True)

        # test with unevenly spaced
        np.random.seed(0)
        x = np.sort(np.random.random(10))
        y = 2 * x ** 3 + 4 * x ** 2 + 2 * x
        analytical = 6 * x ** 2 + 8 * x + 2
        num_error = np.abs((np.gradient(y, x, edge_order=2) / analytical) - 1)
        assert_(np.all(num_error < 0.03) == True)

    def test_spacing(self):
        f = np.array([0, 2., 3., 4., 5., 5.])
        f = np.tile(f, (6, 1)) + f.reshape(-1, 1)
        x_uneven = np.array([0., 0.5, 1., 3., 5., 7.])
        x_even = np.arange(6.)

        fdx_even_ord1 = np.tile([2., 1.5, 1., 1., 0.5, 0.], (6, 1))
        fdx_even_ord2 = np.tile([2.5, 1.5, 1., 1., 0.5, -0.5], (6, 1))
        fdx_uneven_ord1 = np.tile([4., 3., 1.7, 0.5, 0.25, 0.], (6, 1))
        fdx_uneven_ord2 = np.tile([5., 3., 1.7, 0.5, 0.25, -0.25], (6, 1))

        # evenly spaced
        for edge_order, exp_res in [(1, fdx_even_ord1), (2, fdx_even_ord2)]:
            res1 = gradient(f, 1., axis=(0, 1), edge_order=edge_order)
            res2 = gradient(f, x_even, x_even,
                            axis=(0, 1), edge_order=edge_order)
            res3 = gradient(f, x_even, x_even,
                            axis=None, edge_order=edge_order)
            assert_array_equal(res1, res2)
            assert_array_equal(res2, res3)
            assert_almost_equal(res1[0], exp_res.T)
            assert_almost_equal(res1[1], exp_res)

            res1 = gradient(f, 1., axis=0, edge_order=edge_order)
            res2 = gradient(f, x_even, axis=0, edge_order=edge_order)
            assert_(res1.shape == res2.shape)
            assert_almost_equal(res2, exp_res.T)

            res1 = gradient(f, 1., axis=1, edge_order=edge_order)
            res2 = gradient(f, x_even, axis=1, edge_order=edge_order)
            assert_(res1.shape == res2.shape)
            assert_array_equal(res2, exp_res)

        # unevenly spaced
        for edge_order, exp_res in [(1, fdx_uneven_ord1), (2, fdx_uneven_ord2)]:
            res1 = gradient(f, x_uneven, x_uneven,
                            axis=(0, 1), edge_order=edge_order)
            res2 = gradient(f, x_uneven, x_uneven,
                            axis=None, edge_order=edge_order)
            assert_array_equal(res1, res2)
            assert_almost_equal(res1[0], exp_res.T)
            assert_almost_equal(res1[1], exp_res)

            res1 = gradient(f, x_uneven, axis=0, edge_order=edge_order)
            assert_almost_equal(res1, exp_res.T)

            res1 = gradient(f, x_uneven, axis=1, edge_order=edge_order)
            assert_almost_equal(res1, exp_res)

        # mixed
        res1 = gradient(f, x_even, x_uneven, axis=(0, 1), edge_order=1)
        res2 = gradient(f, x_uneven, x_even, axis=(1, 0), edge_order=1)
        assert_array_equal(res1[0], res2[1])
        assert_array_equal(res1[1], res2[0])
        assert_almost_equal(res1[0], fdx_even_ord1.T)
        assert_almost_equal(res1[1], fdx_uneven_ord1)

        res1 = gradient(f, x_even, x_uneven, axis=(0, 1), edge_order=2)
        res2 = gradient(f, x_uneven, x_even, axis=(1, 0), edge_order=2)
        assert_array_equal(res1[0], res2[1])
        assert_array_equal(res1[1], res2[0])
        assert_almost_equal(res1[0], fdx_even_ord2.T)
        assert_almost_equal(res1[1], fdx_uneven_ord2)

    def test_specific_axes(self):
        # Testing that gradient can work on a given axis only
        v = [[1, 1], [3, 4]]
        x = np.array(v)
        dx = [np.array([[2., 3.], [2., 3.]]),
              np.array([[0., 0.], [1., 1.]])]
        assert_array_equal(gradient(x, axis=0), dx[0])
        assert_array_equal(gradient(x, axis=1), dx[1])
        assert_array_equal(gradient(x, axis=-1), dx[1])
        assert_array_equal(gradient(x, axis=(1, 0)), [dx[1], dx[0]])

        # test axis=None which means all axes
        assert_almost_equal(gradient(x, axis=None), [dx[0], dx[1]])
        # and is the same as no axis keyword given
        assert_almost_equal(gradient(x, axis=None), gradient(x))

        # test vararg order
        assert_array_equal(gradient(x, 2, 3, axis=(1, 0)),
                           [dx[1] / 2.0, dx[0] / 3.0])
        # test maximal number of varargs
        assert_raises(TypeError, gradient, x, 1, 2, axis=1)

        assert_raises(AxisError, gradient, x, axis=3)
        assert_raises(AxisError, gradient, x, axis=-3)
        # assert_raises(TypeError, gradient, x, axis=[1,])

    def test_timedelta64(self):
        # Make sure gradient() can handle special types like timedelta64
        x = np.array(
            [-5, -3, 10, 12, 61, 321, 300],
            dtype='timedelta64[D]')
        dx = np.array(
            [2, 7, 7, 25, 154, 119, -21],
            dtype='timedelta64[D]')
        assert_array_equal(gradient(x), dx)
        assert_(dx.dtype == np.dtype('timedelta64[D]'))

    def test_inexact_dtypes(self):
        for dt in [np.float16, np.float32, np.float64]:
            # dtypes should not be promoted in a different way to what diff does
            x = np.array([1, 2, 3], dtype=dt)
            assert_equal(gradient(x).dtype, np.diff(x).dtype)

    def test_values(self):
        # needs at least 2 points for edge_order ==1
        gradient(np.arange(2), edge_order=1)
        # needs at least 3 points for edge_order ==1
        gradient(np.arange(3), edge_order=2)

        assert_raises(ValueError, gradient, np.arange(0), edge_order=1)
        assert_raises(ValueError, gradient, np.arange(0), edge_order=2)
        assert_raises(ValueError, gradient, np.arange(1), edge_order=1)
        assert_raises(ValueError, gradient, np.arange(1), edge_order=2)
        assert_raises(ValueError, gradient, np.arange(2), edge_order=2)

    @pytest.mark.parametrize('f_dtype', [np.uint8, np.uint16,
                                         np.uint32, np.uint64])
    def test_f_decreasing_unsigned_int(self, f_dtype):
        f = np.array([5, 4, 3, 2, 1], dtype=f_dtype)
        g = gradient(f)
        assert_array_equal(g, [-1] * len(f))

    @pytest.mark.parametrize('f_dtype', [np.int8, np.int16,
                                         np.int32, np.int64])
    def test_f_signed_int_big_jump(self, f_dtype):
        maxint = np.iinfo(f_dtype).max
        x = np.array([1, 3])
        f = np.array([-1, maxint], dtype=f_dtype)
        dfdx = gradient(f, x)
        assert_array_equal(dfdx, [(maxint + 1) // 2] * 2)

    @pytest.mark.parametrize('x_dtype', [np.uint8, np.uint16,
                                         np.uint32, np.uint64])
    def test_x_decreasing_unsigned(self, x_dtype):
        x = np.array([3, 2, 1], dtype=x_dtype)
        f = np.array([0, 2, 4])
        dfdx = gradient(f, x)
        assert_array_equal(dfdx, [-2] * len(x))

    @pytest.mark.parametrize('x_dtype', [np.int8, np.int16,
                                         np.int32, np.int64])
    def test_x_signed_int_big_jump(self, x_dtype):
        minint = np.iinfo(x_dtype).min
        maxint = np.iinfo(x_dtype).max
        x = np.array([-1, maxint], dtype=x_dtype)
        f = np.array([minint // 2, 0])
        dfdx = gradient(f, x)
        assert_array_equal(dfdx, [0.5, 0.5])

    def test_return_type(self):
        res = np.gradient(([1, 2], [2, 3]))
        assert type(res) is tuple


class TestAngle:

    def test_basic(self):
        x = [1 + 3j, np.sqrt(2) / 2.0 + 1j * np.sqrt(2) / 2,
             1, 1j, -1, -1j, 1 - 3j, -1 + 3j]
        y = angle(x)
        yo = [
            np.arctan(3.0 / 1.0),
            np.arctan(1.0), 0, np.pi / 2, np.pi, -np.pi / 2.0,
            -np.arctan(3.0 / 1.0), np.pi - np.arctan(3.0 / 1.0)]
        z = angle(x, deg=True)
        zo = np.array(yo) * 180 / np.pi
        assert_array_almost_equal(y, yo, 11)
        assert_array_almost_equal(z, zo, 11)

    def test_subclass(self):
        x = np.ma.array([1 + 3j, 1, np.sqrt(2) / 2 * (1 + 1j)])
        x[1] = np.ma.masked
        expected = np.ma.array([np.arctan(3.0 / 1.0), 0, np.arctan(1.0)])
        expected[1] = np.ma.masked
        actual = angle(x)
        assert_equal(type(actual), type(expected))
        assert_equal(actual.mask, expected.mask)
        assert_equal(actual, expected)


class TestTrimZeros:

    a = np.array([0, 0, 1, 0, 2, 3, 4, 0])
    b = a.astype(float)
    c = a.astype(complex)
    d = a.astype(object)

    def values(self):
        attr_names = ('a', 'b', 'c', 'd')
        return (getattr(self, name) for name in attr_names)

    def test_basic(self):
        slc = np.s_[2:-1]
        for arr in self.values():
            res = trim_zeros(arr)
            assert_array_equal(res, arr[slc])

    def test_leading_skip(self):
        slc = np.s_[:-1]
        for arr in self.values():
            res = trim_zeros(arr, trim='b')
            assert_array_equal(res, arr[slc])

    def test_trailing_skip(self):
        slc = np.s_[2:]
        for arr in self.values():
            res = trim_zeros(arr, trim='F')
            assert_array_equal(res, arr[slc])

    def test_all_zero(self):
        for _arr in self.values():
            arr = np.zeros_like(_arr, dtype=_arr.dtype)

            res1 = trim_zeros(arr, trim='B')
            assert len(res1) == 0

            res2 = trim_zeros(arr, trim='f')
            assert len(res2) == 0

    def test_size_zero(self):
        arr = np.zeros(0)
        res = trim_zeros(arr)
        assert_array_equal(arr, res)

    @pytest.mark.parametrize(
        'arr',
        [np.array([0, 2**62, 0]),
         np.array([0, 2**63, 0]),
         np.array([0, 2**64, 0])]
    )
    def test_overflow(self, arr):
        slc = np.s_[1:2]
        res = trim_zeros(arr)
        assert_array_equal(res, arr[slc])

    def test_no_trim(self):
        arr = np.array([None, 1, None])
        res = trim_zeros(arr)
        assert_array_equal(arr, res)

    def test_list_to_list(self):
        res = trim_zeros(self.a.tolist())
        assert isinstance(res, list)

    @pytest.mark.parametrize("ndim", (0, 1, 2, 3, 10))
    def test_nd_basic(self, ndim):
        a = np.ones((2,) * ndim)
        b = np.pad(a, (2, 1), mode="constant", constant_values=0)
        res = trim_zeros(b, axis=None)
        assert_array_equal(a, res)

    @pytest.mark.parametrize("ndim", (0, 1, 2, 3))
    def test_allzero(self, ndim):
        a = np.zeros((3,) * ndim)
        res = trim_zeros(a, axis=None)
        assert_array_equal(res, np.zeros((0,) * ndim))

    def test_trim_arg(self):
        a = np.array([0, 1, 2, 0])

        res = trim_zeros(a, trim='f')
        assert_array_equal(res, [1, 2, 0])

        res = trim_zeros(a, trim='b')
        assert_array_equal(res, [0, 1, 2])

    @pytest.mark.parametrize("trim", ("front", ""))
    def test_unexpected_trim_value(self, trim):
        arr = self.a
        with pytest.raises(ValueError, match=r"unexpected character\(s\) in `trim`"):
            trim_zeros(arr, trim=trim)


class TestExtins:

    def test_basic(self):
        a = np.array([1, 3, 2, 1, 2, 3, 3])
        b = extract(a > 1, a)
        assert_array_equal(b, [3, 2, 2, 3, 3])

    def test_place(self):
        # Make sure that non-np.ndarray objects
        # raise an error instead of doing nothing
        assert_raises(TypeError, place, [1, 2, 3], [True, False], [0, 1])

        a = np.array([1, 4, 3, 2, 5, 8, 7])
        place(a, [0, 1, 0, 1, 0, 1, 0], [2, 4, 6])
        assert_array_equal(a, [1, 2, 3, 4, 5, 6, 7])

        place(a, np.zeros(7), [])
        assert_array_equal(a, np.arange(1, 8))

        place(a, [1, 0, 1, 0, 1, 0, 1], [8, 9])
        assert_array_equal(a, [8, 2, 9, 4, 8, 6, 9])
        assert_raises_regex(ValueError, "Cannot insert from an empty array",
                            lambda: place(a, [0, 0, 0, 0, 0, 1, 0], []))

        # See Issue #6974
        a = np.array(['12', '34'])
        place(a, [0, 1], '9')
        assert_array_equal(a, ['12', '9'])

    def test_both(self):
        a = rand(10)
        mask = a > 0.5
        ac = a.copy()
        c = extract(mask, a)
        place(a, mask, 0)
        place(a, mask, c)
        assert_array_equal(a, ac)


# _foo1 and _foo2 are used in some tests in TestVectorize.

def _foo1(x, y=1.0):
    return y * math.floor(x)


def _foo2(x, y=1.0, z=0.0):
    return y * math.floor(x) + z


class TestVectorize:

    def test_simple(self):
        def addsubtract(a, b):
            if a > b:
                return a - b
            else:
                return a + b

        f = vectorize(addsubtract)
        r = f([0, 3, 6, 9], [1, 3, 5, 7])
        assert_array_equal(r, [1, 6, 1, 2])

    def test_scalar(self):
        def addsubtract(a, b):
            if a > b:
                return a - b
            else:
                return a + b

        f = vectorize(addsubtract)
        r = f([0, 3, 6, 9], 5)
        assert_array_equal(r, [5, 8, 1, 4])

    def test_large(self):
        x = np.linspace(-3, 2, 10000)
        f = vectorize(lambda x: x)
        y = f(x)
        assert_array_equal(y, x)

    def test_ufunc(self):
        f = vectorize(math.cos)
        args = np.array([0, 0.5 * np.pi, np.pi, 1.5 * np.pi, 2 * np.pi])
        r1 = f(args)
        r2 = np.cos(args)
        assert_array_almost_equal(r1, r2)

    def test_keywords(self):

        def foo(a, b=1):
            return a + b

        f = vectorize(foo)
        args = np.array([1, 2, 3])
        r1 = f(args)
        r2 = np.array([2, 3, 4])
        assert_array_equal(r1, r2)
        r1 = f(args, 2)
        r2 = np.array([3, 4, 5])
        assert_array_equal(r1, r2)

    def test_keywords_with_otypes_order1(self):
        # gh-1620: The second call of f would crash with
        # `ValueError: invalid number of arguments`.
        f = vectorize(_foo1, otypes=[float])
        # We're testing the caching of ufuncs by vectorize, so the order
        # of these function calls is an important part of the test.
        r1 = f(np.arange(3.0), 1.0)
        r2 = f(np.arange(3.0))
        assert_array_equal(r1, r2)

    def test_keywords_with_otypes_order2(self):
        # gh-1620: The second call of f would crash with
        # `ValueError: non-broadcastable output operand with shape ()
        # doesn't match the broadcast shape (3,)`.
        f = vectorize(_foo1, otypes=[float])
        # We're testing the caching of ufuncs by vectorize, so the order
        # of these function calls is an important part of the test.
        r1 = f(np.arange(3.0))
        r2 = f(np.arange(3.0), 1.0)
        assert_array_equal(r1, r2)

    def test_keywords_with_otypes_order3(self):
        # gh-1620: The third call of f would crash with
        # `ValueError: invalid number of arguments`.
        f = vectorize(_foo1, otypes=[float])
        # We're testing the caching of ufuncs by vectorize, so the order
        # of these function calls is an important part of the test.
        r1 = f(np.arange(3.0))
        r2 = f(np.arange(3.0), y=1.0)
        r3 = f(np.arange(3.0))
        assert_array_equal(r1, r2)
        assert_array_equal(r1, r3)

    def test_keywords_with_otypes_several_kwd_args1(self):
        # gh-1620 Make sure different uses of keyword arguments
        # don't break the vectorized function.
        f = vectorize(_foo2, otypes=[float])
        # We're testing the caching of ufuncs by vectorize, so the order
        # of these function calls is an important part of the test.
        r1 = f(10.4, z=100)
        r2 = f(10.4, y=-1)
        r3 = f(10.4)
        assert_equal(r1, _foo2(10.4, z=100))
        assert_equal(r2, _foo2(10.4, y=-1))
        assert_equal(r3, _foo2(10.4))

    def test_keywords_with_otypes_several_kwd_args2(self):
        # gh-1620 Make sure different uses of keyword arguments
        # don't break the vectorized function.
        f = vectorize(_foo2, otypes=[float])
        # We're testing the caching of ufuncs by vectorize, so the order
        # of these function calls is an important part of the test.
        r1 = f(z=100, x=10.4, y=-1)
        r2 = f(1, 2, 3)
        assert_equal(r1, _foo2(z=100, x=10.4, y=-1))
        assert_equal(r2, _foo2(1, 2, 3))

    def test_keywords_no_func_code(self):
        # This needs to test a function that has keywords but
        # no func_code attribute, since otherwise vectorize will
        # inspect the func_code.
        import random
        try:
            vectorize(random.randrange)  # Should succeed
        except Exception:
            raise AssertionError

    def test_keywords2_ticket_2100(self):
        # Test kwarg support: enhancement ticket 2100

        def foo(a, b=1):
            return a + b

        f = vectorize(foo)
        args = np.array([1, 2, 3])
        r1 = f(a=args)
        r2 = np.array([2, 3, 4])
        assert_array_equal(r1, r2)
        r1 = f(b=1, a=args)
        assert_array_equal(r1, r2)
        r1 = f(args, b=2)
        r2 = np.array([3, 4, 5])
        assert_array_equal(r1, r2)

    def test_keywords3_ticket_2100(self):
        # Test excluded with mixed positional and kwargs: ticket 2100
        def mypolyval(x, p):
            _p = list(p)
            res = _p.pop(0)
            while _p:
                res = res * x + _p.pop(0)
            return res

        vpolyval = np.vectorize(mypolyval, excluded=['p', 1])
        ans = [3, 6]
        assert_array_equal(ans, vpolyval(x=[0, 1], p=[1, 2, 3]))
        assert_array_equal(ans, vpolyval([0, 1], p=[1, 2, 3]))
        assert_array_equal(ans, vpolyval([0, 1], [1, 2, 3]))

    def test_keywords4_ticket_2100(self):
        # Test vectorizing function with no positional args.
        @vectorize
        def f(**kw):
            res = 1.0
            for _k in kw:
                res *= kw[_k]
            return res

        assert_array_equal(f(a=[1, 2], b=[3, 4]), [3, 8])

    def test_keywords5_ticket_2100(self):
        # Test vectorizing function with no kwargs args.
        @vectorize
        def f(*v):
            return np.prod(v)

        assert_array_equal(f([1, 2], [3, 4]), [3, 8])

    def test_coverage1_ticket_2100(self):
        def foo():
            return 1

        f = vectorize(foo)
        assert_array_equal(f(), 1)

    def test_assigning_docstring(self):
        def foo(x):
            """Original documentation"""
            return x

        f = vectorize(foo)
        assert_equal(f.__doc__, foo.__doc__)

        doc = "Provided documentation"
        f = vectorize(foo, doc=doc)
        assert_equal(f.__doc__, doc)

    def test_UnboundMethod_ticket_1156(self):
        # Regression test for issue 1156
        class Foo:
            b = 2

            def bar(self, a):
                return a ** self.b

        assert_array_equal(vectorize(Foo().bar)(np.arange(9)),
                           np.arange(9) ** 2)
        assert_array_equal(vectorize(Foo.bar)(Foo(), np.arange(9)),
                           np.arange(9) ** 2)

    def test_execution_order_ticket_1487(self):
        # Regression test for dependence on execution order: issue 1487
        f1 = vectorize(lambda x: x)
        res1a = f1(np.arange(3))
        res1b = f1(np.arange(0.1, 3))
        f2 = vectorize(lambda x: x)
        res2b = f2(np.arange(0.1, 3))
        res2a = f2(np.arange(3))
        assert_equal(res1a, res2a)
        assert_equal(res1b, res2b)

    def test_string_ticket_1892(self):
        # Test vectorization over strings: issue 1892.
        f = np.vectorize(lambda x: x)
        s = '0123456789' * 10
        assert_equal(s, f(s))

    def test_dtype_promotion_gh_29189(self):
        # dtype should not be silently promoted (int32 -> int64)
        dtypes = [np.int16, np.int32, np.int64, np.float16, np.float32, np.float64]

        for dtype in dtypes:
            x = np.asarray([1, 2, 3], dtype=dtype)
            y = np.vectorize(lambda x: x + x)(x)
            assert x.dtype == y.dtype

    def test_cache(self):
        # Ensure that vectorized func called exactly once per argument.
        _calls = [0]

        @vectorize
        def f(x):
            _calls[0] += 1
            return x ** 2

        f.cache = True
        x = np.arange(5)
        assert_array_equal(f(x), x * x)
        assert_equal(_calls[0], len(x))

    def test_otypes(self):
        f = np.vectorize(lambda x: x)
        f.otypes = 'i'
        x = np.arange(5)
        assert_array_equal(f(x), x)

    def test_otypes_object_28624(self):
        # with object otype, the vectorized function should return y
        # wrapped into an object array
        y = np.arange(3)
        f = vectorize(lambda x: y, otypes=[object])

        assert f(None).item() is y
        assert f([None]).item() is y

        y = [1, 2, 3]
        f = vectorize(lambda x: y, otypes=[object])

        assert f(None).item() is y
        assert f([None]).item() is y

    def test_parse_gufunc_signature(self):
        assert_equal(nfb._parse_gufunc_signature('(x)->()'), ([('x',)], [()]))
        assert_equal(nfb._parse_gufunc_signature('(x,y)->()'),
                     ([('x', 'y')], [()]))
        assert_equal(nfb._parse_gufunc_signature('(x),(y)->()'),
                     ([('x',), ('y',)], [()]))
        assert_equal(nfb._parse_gufunc_signature('(x)->(y)'),
                     ([('x',)], [('y',)]))
        assert_equal(nfb._parse_gufunc_signature('(x)->(y),()'),
                     ([('x',)], [('y',), ()]))
        assert_equal(nfb._parse_gufunc_signature('(),(a,b,c),(d)->(d,e)'),
                     ([(), ('a', 'b', 'c'), ('d',)], [('d', 'e')]))

        # Tests to check if whitespaces are ignored
        assert_equal(nfb._parse_gufunc_signature('(x )->()'), ([('x',)], [()]))
        assert_equal(nfb._parse_gufunc_signature('( x , y )->(  )'),
                     ([('x', 'y')], [()]))
        assert_equal(nfb._parse_gufunc_signature('(x),( y) ->()'),
                     ([('x',), ('y',)], [()]))
        assert_equal(nfb._parse_gufunc_signature('(  x)-> (y )  '),
                     ([('x',)], [('y',)]))
        assert_equal(nfb._parse_gufunc_signature(' (x)->( y),( )'),
                     ([('x',)], [('y',), ()]))
        assert_equal(nfb._parse_gufunc_signature(
                     '(  ), ( a,  b,c )  ,(  d)   ->   (d  ,  e)'),
                     ([(), ('a', 'b', 'c'), ('d',)], [('d', 'e')]))

        with assert_raises(ValueError):
            nfb._parse_gufunc_signature('(x)(y)->()')
        with assert_raises(ValueError):
            nfb._parse_gufunc_signature('(x),(y)->')
        with assert_raises(ValueError):
            nfb._parse_gufunc_signature('((x))->(x)')

    def test_signature_simple(self):
        def addsubtract(a, b):
            if a > b:
                return a - b
            else:
                return a + b

        f = vectorize(addsubtract, signature='(),()->()')
        r = f([0, 3, 6, 9], [1, 3, 5, 7])
        assert_array_equal(r, [1, 6, 1, 2])

    def test_signature_mean_last(self):
        def mean(a):
            return a.mean()

        f = vectorize(mean, signature='(n)->()')
        r = f([[1, 3], [2, 4]])
        assert_array_equal(r, [2, 3])

    def test_signature_center(self):
        def center(a):
            return a - a.mean()

        f = vectorize(center, signature='(n)->(n)')
        r = f([[1, 3], [2, 4]])
        assert_array_equal(r, [[-1, 1], [-1, 1]])

    def test_signature_two_outputs(self):
        f = vectorize(lambda x: (x, x), signature='()->(),()')
        r = f([1, 2, 3])
        assert_(isinstance(r, tuple) and len(r) == 2)
        assert_array_equal(r[0], [1, 2, 3])
        assert_array_equal(r[1], [1, 2, 3])

    def test_signature_outer(self):
        f = vectorize(np.outer, signature='(a),(b)->(a,b)')
        r = f([1, 2], [1, 2, 3])
        assert_array_equal(r, [[1, 2, 3], [2, 4, 6]])

        r = f([[[1, 2]]], [1, 2, 3])
        assert_array_equal(r, [[[[1, 2, 3], [2, 4, 6]]]])

        r = f([[1, 0], [2, 0]], [1, 2, 3])
        assert_array_equal(r, [[[1, 2, 3], [0, 0, 0]],
                               [[2, 4, 6], [0, 0, 0]]])

        r = f([1, 2], [[1, 2, 3], [0, 0, 0]])
        assert_array_equal(r, [[[1, 2, 3], [2, 4, 6]],
                               [[0, 0, 0], [0, 0, 0]]])

    def test_signature_computed_size(self):
        f = vectorize(lambda x: x[:-1], signature='(n)->(m)')
        r = f([1, 2, 3])
        assert_array_equal(r, [1, 2])

        r = f([[1, 2, 3], [2, 3, 4]])
        assert_array_equal(r, [[1, 2], [2, 3]])

    def test_signature_excluded(self):

        def foo(a, b=1):
            return a + b

        f = vectorize(foo, signature='()->()', excluded={'b'})
        assert_array_equal(f([1, 2, 3]), [2, 3, 4])
        assert_array_equal(f([1, 2, 3], b=0), [1, 2, 3])

    def test_signature_otypes(self):
        f = vectorize(lambda x: x, signature='(n)->(n)', otypes=['float64'])
        r = f([1, 2, 3])
        assert_equal(r.dtype, np.dtype('float64'))
        assert_array_equal(r, [1, 2, 3])

    def test_signature_invalid_inputs(self):
        f = vectorize(operator.add, signature='(n),(n)->(n)')
        with assert_raises_regex(TypeError, 'wrong number of positional'):
            f([1, 2])
        with assert_raises_regex(
                ValueError, 'does not have enough dimensions'):
            f(1, 2)
        with assert_raises_regex(
                ValueError, 'inconsistent size for core dimension'):
            f([1, 2], [1, 2, 3])

        f = vectorize(operator.add, signature='()->()')
        with assert_raises_regex(TypeError, 'wrong number of positional'):
            f(1, 2)

    def test_signature_invalid_outputs(self):

        f = vectorize(lambda x: x[:-1], signature='(n)->(n)')
        with assert_raises_regex(
                ValueError, 'inconsistent size for core dimension'):
            f([1, 2, 3])

        f = vectorize(lambda x: x, signature='()->(),()')
        with assert_raises_regex(ValueError, 'wrong number of outputs'):
            f(1)

        f = vectorize(lambda x: (x, x), signature='()->()')
        with assert_raises_regex(ValueError, 'wrong number of outputs'):
            f([1, 2])

    def test_size_zero_output(self):
        # see issue 5868
        f = np.vectorize(lambda x: x)
        x = np.zeros([0, 5], dtype=int)
        with assert_raises_regex(ValueError, 'otypes'):
            f(x)

        f.otypes = 'i'
        assert_array_equal(f(x), x)

        f = np.vectorize(lambda x: x, signature='()->()')
        with assert_raises_regex(ValueError, 'otypes'):
            f(x)

        f = np.vectorize(lambda x: x, signature='()->()', otypes='i')
        assert_array_equal(f(x), x)

        f = np.vectorize(lambda x: x, signature='(n)->(n)', otypes='i')
        assert_array_equal(f(x), x)

        f = np.vectorize(lambda x: x, signature='(n)->(n)')
        assert_array_equal(f(x.T), x.T)

        f = np.vectorize(lambda x: [x], signature='()->(n)', otypes='i')
        with assert_raises_regex(ValueError, 'new output dimensions'):
            f(x)

    def test_subclasses(self):
        class subclass(np.ndarray):
            pass

        m = np.array([[1., 0., 0.],
                      [0., 0., 1.],
                      [0., 1., 0.]]).view(subclass)
        v = np.array([[1., 2., 3.], [4., 5., 6.], [7., 8., 9.]]).view(subclass)
        # generalized (gufunc)
        matvec = np.vectorize(np.matmul, signature='(m,m),(m)->(m)')
        r = matvec(m, v)
        assert_equal(type(r), subclass)
        assert_equal(r, [[1., 3., 2.], [4., 6., 5.], [7., 9., 8.]])

        # element-wise (ufunc)
        mult = np.vectorize(lambda x, y: x * y)
        r = mult(m, v)
        assert_equal(type(r), subclass)
        assert_equal(r, m * v)

    def test_name(self):
        # gh-23021
        @np.vectorize
        def f2(a, b):
            return a + b

        assert f2.__name__ == 'f2'

    def test_decorator(self):
        @vectorize
        def addsubtract(a, b):
            if a > b:
                return a - b
            else:
                return a + b

        r = addsubtract([0, 3, 6, 9], [1, 3, 5, 7])
        assert_array_equal(r, [1, 6, 1, 2])

    def test_docstring(self):
        @vectorize
        def f(x):
            """Docstring"""
            return x

        if sys.flags.optimize < 2:
            assert f.__doc__ == "Docstring"

    def test_partial(self):
        def foo(x, y):
            return x + y

        bar = partial(foo, 3)
        vbar = np.vectorize(bar)
        assert vbar(1) == 4

    def test_signature_otypes_decorator(self):
        @vectorize(signature='(n)->(n)', otypes=['float64'])
        def f(x):
            return x

        r = f([1, 2, 3])
        assert_equal(r.dtype, np.dtype('float64'))
        assert_array_equal(r, [1, 2, 3])
        assert f.__name__ == 'f'

    def test_bad_input(self):
        with assert_raises(TypeError):
            A = np.vectorize(pyfunc=3)

    def test_no_keywords(self):
        with assert_raises(TypeError):
            @np.vectorize("string")
            def foo():
                return "bar"

    def test_positional_regression_9477(self):
        # This supplies the first keyword argument as a positional,
        # to ensure that they are still properly forwarded after the
        # enhancement for #9477
        f = vectorize((lambda x: x), ['float64'])
        r = f([2])
        assert_equal(r.dtype, np.dtype('float64'))

    def test_datetime_conversion(self):
        otype = "datetime64[ns]"
        arr = np.array(['2024-01-01', '2024-01-02', '2024-01-03'],
                       dtype='datetime64[ns]')
        assert_array_equal(np.vectorize(lambda x: x, signature="(i)->(j)",
                                        otypes=[otype])(arr), arr)


class TestLeaks:
    class A:
        iters = 20

        def bound(self, *args):
            return 0

        @staticmethod
        def unbound(*args):
            return 0

    @pytest.mark.skipif(not HAS_REFCOUNT, reason="Python lacks refcounts")
    @pytest.mark.skipif(NOGIL_BUILD,
                        reason=("Functions are immortalized if a thread is "
                                "launched, making this test flaky"))
    @pytest.mark.parametrize('name, incr', [
            ('bound', A.iters),
            ('unbound', 0),
            ])
    def test_frompyfunc_leaks(self, name, incr):
        # exposed in gh-11867 as np.vectorized, but the problem stems from
        # frompyfunc.
        # class.attribute = np.frompyfunc(<method>) creates a
        # reference cycle if <method> is a bound class method.
        # It requires a gc collection cycle to break the cycle.
        import gc
        A_func = getattr(self.A, name)
        gc.disable()
        try:
            refcount = sys.getrefcount(A_func)
            for i in range(self.A.iters):
                a = self.A()
                a.f = np.frompyfunc(getattr(a, name), 1, 1)
                out = a.f(np.arange(10))
            a = None
            # A.func is part of a reference cycle if incr is non-zero
            assert_equal(sys.getrefcount(A_func), refcount + incr)
            for i in range(5):
                gc.collect()
            assert_equal(sys.getrefcount(A_func), refcount)
        finally:
            gc.enable()


class TestDigitize:

    def test_forward(self):
        x = np.arange(-6, 5)
        bins = np.arange(-5, 5)
        assert_array_equal(digitize(x, bins), np.arange(11))

    def test_reverse(self):
        x = np.arange(5, -6, -1)
        bins = np.arange(5, -5, -1)
        assert_array_equal(digitize(x, bins), np.arange(11))

    def test_random(self):
        x = rand(10)
        bin = np.linspace(x.min(), x.max(), 10)
        assert_(np.all(digitize(x, bin) != 0))

    def test_right_basic(self):
        x = [1, 5, 4, 10, 8, 11, 0]
        bins = [1, 5, 10]
        default_answer = [1, 2, 1, 3, 2, 3, 0]
        assert_array_equal(digitize(x, bins), default_answer)
        right_answer = [0, 1, 1, 2, 2, 3, 0]
        assert_array_equal(digitize(x, bins, True), right_answer)

    def test_right_open(self):
        x = np.arange(-6, 5)
        bins = np.arange(-6, 4)
        assert_array_equal(digitize(x, bins, True), np.arange(11))

    def test_right_open_reverse(self):
        x = np.arange(5, -6, -1)
        bins = np.arange(4, -6, -1)
        assert_array_equal(digitize(x, bins, True), np.arange(11))

    def test_right_open_random(self):
        x = rand(10)
        bins = np.linspace(x.min(), x.max(), 10)
        assert_(np.all(digitize(x, bins, True) != 10))

    def test_monotonic(self):
        x = [-1, 0, 1, 2]
        bins = [0, 0, 1]
        assert_array_equal(digitize(x, bins, False), [0, 2, 3, 3])
        assert_array_equal(digitize(x, bins, True), [0, 0, 2, 3])
        bins = [1, 1, 0]
        assert_array_equal(digitize(x, bins, False), [3, 2, 0, 0])
        assert_array_equal(digitize(x, bins, True), [3, 3, 2, 0])
        bins = [1, 1, 1, 1]
        assert_array_equal(digitize(x, bins, False), [0, 0, 4, 4])
        assert_array_equal(digitize(x, bins, True), [0, 0, 0, 4])
        bins = [0, 0, 1, 0]
        assert_raises(ValueError, digitize, x, bins)
        bins = [1, 1, 0, 1]
        assert_raises(ValueError, digitize, x, bins)

    def test_casting_error(self):
        x = [1, 2, 3 + 1.j]
        bins = [1, 2, 3]
        assert_raises(TypeError, digitize, x, bins)
        x, bins = bins, x
        assert_raises(TypeError, digitize, x, bins)

    def test_return_type(self):
        # Functions returning indices should always return base ndarrays
        class A(np.ndarray):
            pass
        a = np.arange(5).view(A)
        b = np.arange(1, 3).view(A)
        assert_(not isinstance(digitize(b, a, False), A))
        assert_(not isinstance(digitize(b, a, True), A))

    def test_large_integers_increasing(self):
        # gh-11022
        x = 2**54  # loses precision in a float
        assert_equal(np.digitize(x, [x - 1, x + 1]), 1)

    @pytest.mark.xfail(
        reason="gh-11022: np._core.multiarray._monoticity loses precision")
    def test_large_integers_decreasing(self):
        # gh-11022
        x = 2**54  # loses precision in a float
        assert_equal(np.digitize(x, [x + 1, x - 1]), 1)


class TestUnwrap:

    def test_simple(self):
        # check that unwrap removes jumps greater that 2*pi
        assert_array_equal(unwrap([1, 1 + 2 * np.pi]), [1, 1])
        # check that unwrap maintains continuity
        assert_(np.all(diff(unwrap(rand(10) * 100)) < np.pi))

    def test_period(self):
        # check that unwrap removes jumps greater that 255
        assert_array_equal(unwrap([1, 1 + 256], period=255), [1, 2])
        # check that unwrap maintains continuity
        assert_(np.all(diff(unwrap(rand(10) * 1000, period=255)) < 255))
        # check simple case
        simple_seq = np.array([0, 75, 150, 225, 300])
        wrap_seq = np.mod(simple_seq, 255)
        assert_array_equal(unwrap(wrap_seq, period=255), simple_seq)
        # check custom discont value
        uneven_seq = np.array([0, 75, 150, 225, 300, 430])
        wrap_uneven = np.mod(uneven_seq, 250)
        no_discont = unwrap(wrap_uneven, period=250)
        assert_array_equal(no_discont, [0, 75, 150, 225, 300, 180])
        sm_discont = unwrap(wrap_uneven, period=250, discont=140)
        assert_array_equal(sm_discont, [0, 75, 150, 225, 300, 430])
        assert sm_discont.dtype == wrap_uneven.dtype


@pytest.mark.parametrize(
    "dtype", "O" + np.typecodes["AllInteger"] + np.typecodes["Float"]
)
@pytest.mark.parametrize("M", [0, 1, 10])
class TestFilterwindows:

    def test_hanning(self, dtype: str, M: int) -> None:
        scalar = np.array(M, dtype=dtype)[()]

        w = hanning(scalar)
        if dtype == "O":
            ref_dtype = np.float64
        else:
            ref_dtype = np.result_type(scalar.dtype, np.float64)
        assert w.dtype == ref_dtype

        # check symmetry
        assert_equal(w, flipud(w))

        # check known value
        if scalar < 1:
            assert_array_equal(w, np.array([]))
        elif scalar == 1:
            assert_array_equal(w, np.ones(1))
        else:
            assert_almost_equal(np.sum(w, axis=0), 4.500, 4)

    def test_hamming(self, dtype: str, M: int) -> None:
        scalar = np.array(M, dtype=dtype)[()]

        w = hamming(scalar)
        if dtype == "O":
            ref_dtype = np.float64
        else:
            ref_dtype = np.result_type(scalar.dtype, np.float64)
        assert w.dtype == ref_dtype

        # check symmetry
        assert_equal(w, flipud(w))

        # check known value
        if scalar < 1:
            assert_array_equal(w, np.array([]))
        elif scalar == 1:
            assert_array_equal(w, np.ones(1))
        else:
            assert_almost_equal(np.sum(w, axis=0), 4.9400, 4)

    def test_bartlett(self, dtype: str, M: int) -> None:
        scalar = np.array(M, dtype=dtype)[()]

        w = bartlett(scalar)
        if dtype == "O":
            ref_dtype = np.float64
        else:
            ref_dtype = np.result_type(scalar.dtype, np.float64)
        assert w.dtype == ref_dtype

        # check symmetry
        assert_equal(w, flipud(w))

        # check known value
        if scalar < 1:
            assert_array_equal(w, np.array([]))
        elif scalar == 1:
            assert_array_equal(w, np.ones(1))
        else:
            assert_almost_equal(np.sum(w, axis=0), 4.4444, 4)

    def test_blackman(self, dtype: str, M: int) -> None:
        scalar = np.array(M, dtype=dtype)[()]

        w = blackman(scalar)
        if dtype == "O":
            ref_dtype = np.float64
        else:
            ref_dtype = np.result_type(scalar.dtype, np.float64)
        assert w.dtype == ref_dtype

        # check symmetry
        assert_equal(w, flipud(w))

        # check known value
        if scalar < 1:
            assert_array_equal(w, np.array([]))
        elif scalar == 1:
            assert_array_equal(w, np.ones(1))
        else:
            assert_almost_equal(np.sum(w, axis=0), 3.7800, 4)

    def test_kaiser(self, dtype: str, M: int) -> None:
        scalar = np.array(M, dtype=dtype)[()]

        w = kaiser(scalar, 0)
        if dtype == "O":
            ref_dtype = np.float64
        else:
            ref_dtype = np.result_type(scalar.dtype, np.float64)
        assert w.dtype == ref_dtype

        # check symmetry
        assert_equal(w, flipud(w))

        # check known value
        if scalar < 1:
            assert_array_equal(w, np.array([]))
        elif scalar == 1:
            assert_array_equal(w, np.ones(1))
        else:
            assert_almost_equal(np.sum(w, axis=0), 10, 15)


class TestTrapezoid:

    def test_simple(self):
        x = np.arange(-10, 10, .1)
        r = trapezoid(np.exp(-.5 * x ** 2) / np.sqrt(2 * np.pi), dx=0.1)
        # check integral of normal equals 1
        assert_almost_equal(r, 1, 7)

    def test_ndim(self):
        x = np.linspace(0, 1, 3)
        y = np.linspace(0, 2, 8)
        z = np.linspace(0, 3, 13)

        wx = np.ones_like(x) * (x[1] - x[0])
        wx[0] /= 2
        wx[-1] /= 2
        wy = np.ones_like(y) * (y[1] - y[0])
        wy[0] /= 2
        wy[-1] /= 2
        wz = np.ones_like(z) * (z[1] - z[0])
        wz[0] /= 2
        wz[-1] /= 2

        q = x[:, None, None] + y[None, :, None] + z[None, None, :]

        qx = (q * wx[:, None, None]).sum(axis=0)
        qy = (q * wy[None, :, None]).sum(axis=1)
        qz = (q * wz[None, None, :]).sum(axis=2)

        # n-d `x`
        r = trapezoid(q, x=x[:, None, None], axis=0)
        assert_almost_equal(r, qx)
        r = trapezoid(q, x=y[None, :, None], axis=1)
        assert_almost_equal(r, qy)
        r = trapezoid(q, x=z[None, None, :], axis=2)
        assert_almost_equal(r, qz)

        # 1-d `x`
        r = trapezoid(q, x=x, axis=0)
        assert_almost_equal(r, qx)
        r = trapezoid(q, x=y, axis=1)
        assert_almost_equal(r, qy)
        r = trapezoid(q, x=z, axis=2)
        assert_almost_equal(r, qz)

    def test_masked(self):
        # Testing that masked arrays behave as if the function is 0 where
        # masked
        x = np.arange(5)
        y = x * x
        mask = x == 2
        ym = np.ma.array(y, mask=mask)
        r = 13.0  # sum(0.5 * (0 + 1) * 1.0 + 0.5 * (9 + 16))
        assert_almost_equal(trapezoid(ym, x), r)

        xm = np.ma.array(x, mask=mask)
        assert_almost_equal(trapezoid(ym, xm), r)

        xm = np.ma.array(x, mask=mask)
        assert_almost_equal(trapezoid(y, xm), r)


class TestSinc:

    def test_simple(self):
        assert_(sinc(0) == 1)
        w = sinc(np.linspace(-1, 1, 100))
        # check symmetry
        assert_array_almost_equal(w, flipud(w), 7)

    def test_array_like(self):
        x = [0, 0.5]
        y1 = sinc(np.array(x))
        y2 = sinc(list(x))
        y3 = sinc(tuple(x))
        assert_array_equal(y1, y2)
        assert_array_equal(y1, y3)

    def test_bool_dtype(self):
        x = (np.arange(4, dtype=np.uint8) % 2 == 1)
        actual = sinc(x)
        expected = sinc(x.astype(np.float64))
        assert_allclose(actual, expected)
        assert actual.dtype == np.float64

    @pytest.mark.parametrize('dtype', [np.uint8, np.int16, np.uint64])
    def test_int_dtypes(self, dtype):
        x = np.arange(4, dtype=dtype)
        actual = sinc(x)
        expected = sinc(x.astype(np.float64))
        assert_allclose(actual, expected)
        assert actual.dtype == np.float64

    @pytest.mark.parametrize(
            'dtype',
            [np.float16, np.float32, np.longdouble, np.complex64, np.complex128]
    )
    def test_float_dtypes(self, dtype):
        x = np.arange(4, dtype=dtype)
        assert sinc(x).dtype == x.dtype

    def test_float16_underflow(self):
        x = np.float16(0)
        # before gh-27784, fill value for 0 in input would underflow float16,
        # resulting in nan
        assert_array_equal(sinc(x), np.asarray(1.0))

class TestUnique:

    def test_simple(self):
        x = np.array([4, 3, 2, 1, 1, 2, 3, 4, 0])
        assert_(np.all(unique(x) == [0, 1, 2, 3, 4]))
        assert_(unique(np.array([1, 1, 1, 1, 1])) == np.array([1]))
        x = ['widget', 'ham', 'foo', 'bar', 'foo', 'ham']
        assert_(np.all(unique(x) == ['bar', 'foo', 'ham', 'widget']))
        x = np.array([5 + 6j, 1 + 1j, 1 + 10j, 10, 5 + 6j])
        assert_(np.all(unique(x) == [1 + 1j, 1 + 10j, 5 + 6j, 10]))


class TestCheckFinite:

    def test_simple(self):
        a = [1, 2, 3]
        b = [1, 2, np.inf]
        c = [1, 2, np.nan]
        np.asarray_chkfinite(a)
        assert_raises(ValueError, np.asarray_chkfinite, b)
        assert_raises(ValueError, np.asarray_chkfinite, c)

    def test_dtype_order(self):
        # Regression test for missing dtype and order arguments
        a = [1, 2, 3]
        a = np.asarray_chkfinite(a, order='F', dtype=np.float64)
        assert_(a.dtype == np.float64)


class TestCorrCoef:
    A = np.array(
        [[0.15391142, 0.18045767, 0.14197213],
         [0.70461506, 0.96474128, 0.27906989],
         [0.9297531, 0.32296769, 0.19267156]])
    B = np.array(
        [[0.10377691, 0.5417086, 0.49807457],
         [0.82872117, 0.77801674, 0.39226705],
         [0.9314666, 0.66800209, 0.03538394]])
    res1 = np.array(
        [[1., 0.9379533, -0.04931983],
         [0.9379533, 1., 0.30007991],
         [-0.04931983, 0.30007991, 1.]])
    res2 = np.array(
        [[1., 0.9379533, -0.04931983, 0.30151751, 0.66318558, 0.51532523],
         [0.9379533, 1., 0.30007991, -0.04781421, 0.88157256, 0.78052386],
         [-0.04931983, 0.30007991, 1., -0.96717111, 0.71483595, 0.83053601],
         [0.30151751, -0.04781421, -0.96717111, 1., -0.51366032, -0.66173113],
         [0.66318558, 0.88157256, 0.71483595, -0.51366032, 1., 0.98317823],
         [0.51532523, 0.78052386, 0.83053601, -0.66173113, 0.98317823, 1.]])

    def test_non_array(self):
        assert_almost_equal(np.corrcoef([0, 1, 0], [1, 0, 1]),
                            [[1., -1.], [-1., 1.]])

    def test_simple(self):
        tgt1 = corrcoef(self.A)
        assert_almost_equal(tgt1, self.res1)
        assert_(np.all(np.abs(tgt1) <= 1.0))

        tgt2 = corrcoef(self.A, self.B)
        assert_almost_equal(tgt2, self.res2)
        assert_(np.all(np.abs(tgt2) <= 1.0))

    def test_ddof(self):
        # ddof raises DeprecationWarning
        with suppress_warnings() as sup:
            warnings.simplefilter("always")
            assert_warns(DeprecationWarning, corrcoef, self.A, ddof=-1)
            sup.filter(DeprecationWarning)
            # ddof has no or negligible effect on the function
            assert_almost_equal(corrcoef(self.A, ddof=-1), self.res1)
            assert_almost_equal(corrcoef(self.A, self.B, ddof=-1), self.res2)
            assert_almost_equal(corrcoef(self.A, ddof=3), self.res1)
            assert_almost_equal(corrcoef(self.A, self.B, ddof=3), self.res2)

    def test_bias(self):
        # bias raises DeprecationWarning
        with suppress_warnings() as sup:
            warnings.simplefilter("always")
            assert_warns(DeprecationWarning, corrcoef, self.A, self.B, 1, 0)
            assert_warns(DeprecationWarning, corrcoef, self.A, bias=0)
            sup.filter(DeprecationWarning)
            # bias has no or negligible effect on the function
            assert_almost_equal(corrcoef(self.A, bias=1), self.res1)

    def test_complex(self):
        x = np.array([[1, 2, 3], [1j, 2j, 3j]])
        res = corrcoef(x)
        tgt = np.array([[1., -1.j], [1.j, 1.]])
        assert_allclose(res, tgt)
        assert_(np.all(np.abs(res) <= 1.0))

    def test_xy(self):
        x = np.array([[1, 2, 3]])
        y = np.array([[1j, 2j, 3j]])
        assert_allclose(np.corrcoef(x, y), np.array([[1., -1.j], [1.j, 1.]]))

    def test_empty(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always', RuntimeWarning)
            assert_array_equal(corrcoef(np.array([])), np.nan)
            assert_array_equal(corrcoef(np.array([]).reshape(0, 2)),
                               np.array([]).reshape(0, 0))
            assert_array_equal(corrcoef(np.array([]).reshape(2, 0)),
                               np.array([[np.nan, np.nan], [np.nan, np.nan]]))

    def test_extreme(self):
        x = [[1e-100, 1e100], [1e100, 1e-100]]
        with np.errstate(all='raise'):
            c = corrcoef(x)
        assert_array_almost_equal(c, np.array([[1., -1.], [-1., 1.]]))
        assert_(np.all(np.abs(c) <= 1.0))

    @pytest.mark.parametrize("test_type", [np.half, np.single, np.double, np.longdouble])
    def test_corrcoef_dtype(self, test_type):
        cast_A = self.A.astype(test_type)
        res = corrcoef(cast_A, dtype=test_type)
        assert test_type == res.dtype


class TestCov:
    x1 = np.array([[0, 2], [1, 1], [2, 0]]).T
    res1 = np.array([[1., -1.], [-1., 1.]])
    x2 = np.array([0.0, 1.0, 2.0], ndmin=2)
    frequencies = np.array([1, 4, 1])
    x2_repeats = np.array([[0.0], [1.0], [1.0], [1.0], [1.0], [2.0]]).T
    res2 = np.array([[0.4, -0.4], [-0.4, 0.4]])
    unit_frequencies = np.ones(3, dtype=np.int_)
    weights = np.array([1.0, 4.0, 1.0])
    res3 = np.array([[2. / 3., -2. / 3.], [-2. / 3., 2. / 3.]])
    unit_weights = np.ones(3)
    x3 = np.array([0.3942, 0.5969, 0.7730, 0.9918, 0.7964])

    def test_basic(self):
        assert_allclose(cov(self.x1), self.res1)

    def test_complex(self):
        x = np.array([[1, 2, 3], [1j, 2j, 3j]])
        res = np.array([[1., -1.j], [1.j, 1.]])
        assert_allclose(cov(x), res)
        assert_allclose(cov(x, aweights=np.ones(3)), res)

    def test_xy(self):
        x = np.array([[1, 2, 3]])
        y = np.array([[1j, 2j, 3j]])
        assert_allclose(cov(x, y), np.array([[1., -1.j], [1.j, 1.]]))

    def test_empty(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always', RuntimeWarning)
            assert_array_equal(cov(np.array([])), np.nan)
            assert_array_equal(cov(np.array([]).reshape(0, 2)),
                               np.array([]).reshape(0, 0))
            assert_array_equal(cov(np.array([]).reshape(2, 0)),
                               np.array([[np.nan, np.nan], [np.nan, np.nan]]))

    def test_wrong_ddof(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always', RuntimeWarning)
            assert_array_equal(cov(self.x1, ddof=5),
                               np.array([[np.inf, -np.inf],
                                         [-np.inf, np.inf]]))

    def test_1D_rowvar(self):
        assert_allclose(cov(self.x3), cov(self.x3, rowvar=False))
        y = np.array([0.0780, 0.3107, 0.2111, 0.0334, 0.8501])
        assert_allclose(cov(self.x3, y), cov(self.x3, y, rowvar=False))

    def test_1D_variance(self):
        assert_allclose(cov(self.x3, ddof=1), np.var(self.x3, ddof=1))

    def test_fweights(self):
        assert_allclose(cov(self.x2, fweights=self.frequencies),
                        cov(self.x2_repeats))
        assert_allclose(cov(self.x1, fweights=self.frequencies),
                        self.res2)
        assert_allclose(cov(self.x1, fweights=self.unit_frequencies),
                        self.res1)
        nonint = self.frequencies + 0.5
        assert_raises(TypeError, cov, self.x1, fweights=nonint)
        f = np.ones((2, 3), dtype=np.int_)
        assert_raises(RuntimeError, cov, self.x1, fweights=f)
        f = np.ones(2, dtype=np.int_)
        assert_raises(RuntimeError, cov, self.x1, fweights=f)
        f = -1 * np.ones(3, dtype=np.int_)
        assert_raises(ValueError, cov, self.x1, fweights=f)

    def test_aweights(self):
        assert_allclose(cov(self.x1, aweights=self.weights), self.res3)
        assert_allclose(cov(self.x1, aweights=3.0 * self.weights),
                        cov(self.x1, aweights=self.weights))
        assert_allclose(cov(self.x1, aweights=self.unit_weights), self.res1)
        w = np.ones((2, 3))
        assert_raises(RuntimeError, cov, self.x1, aweights=w)
        w = np.ones(2)
        assert_raises(RuntimeError, cov, self.x1, aweights=w)
        w = -1.0 * np.ones(3)
        assert_raises(ValueError, cov, self.x1, aweights=w)

    def test_unit_fweights_and_aweights(self):
        assert_allclose(cov(self.x2, fweights=self.frequencies,
                            aweights=self.unit_weights),
                        cov(self.x2_repeats))
        assert_allclose(cov(self.x1, fweights=self.frequencies,
                            aweights=self.unit_weights),
                        self.res2)
        assert_allclose(cov(self.x1, fweights=self.unit_frequencies,
                            aweights=self.unit_weights),
                        self.res1)
        assert_allclose(cov(self.x1, fweights=self.unit_frequencies,
                            aweights=self.weights),
                        self.res3)
        assert_allclose(cov(self.x1, fweights=self.unit_frequencies,
                            aweights=3.0 * self.weights),
                        cov(self.x1, aweights=self.weights))
        assert_allclose(cov(self.x1, fweights=self.unit_frequencies,
                            aweights=self.unit_weights),
                        self.res1)

    @pytest.mark.parametrize("test_type", [np.half, np.single, np.double, np.longdouble])
    def test_cov_dtype(self, test_type):
        cast_x1 = self.x1.astype(test_type)
        res = cov(cast_x1, dtype=test_type)
        assert test_type == res.dtype

    def test_gh_27658(self):
        x = np.ones((3, 1))
        expected = np.cov(x, ddof=0, rowvar=True)
        actual = np.cov(x.T, ddof=0, rowvar=False)
        assert_allclose(actual, expected, strict=True)


class Test_I0:

    def test_simple(self):
        assert_almost_equal(
            i0(0.5),
            np.array(1.0634833707413234))

        # need at least one test above 8, as the implementation is piecewise
        A = np.array([0.49842636, 0.6969809, 0.22011976, 0.0155549, 10.0])
        expected = np.array([1.06307822, 1.12518299, 1.01214991, 1.00006049, 2815.71662847])
        assert_almost_equal(i0(A), expected)
        assert_almost_equal(i0(-A), expected)

        B = np.array([[0.827002, 0.99959078],
                      [0.89694769, 0.39298162],
                      [0.37954418, 0.05206293],
                      [0.36465447, 0.72446427],
                      [0.48164949, 0.50324519]])
        assert_almost_equal(
            i0(B),
            np.array([[1.17843223, 1.26583466],
                      [1.21147086, 1.03898290],
                      [1.03633899, 1.00067775],
                      [1.03352052, 1.13557954],
                      [1.05884290, 1.06432317]]))
        # Regression test for gh-11205
        i0_0 = np.i0([0.])
        assert_equal(i0_0.shape, (1,))
        assert_array_equal(np.i0([0.]), np.array([1.]))

    def test_non_array(self):
        a = np.arange(4)

        class array_like:
            __array_interface__ = a.__array_interface__

            def __array_wrap__(self, arr, context, return_scalar):
                return self

        # E.g. pandas series survive ufunc calls through array-wrap:
        assert isinstance(np.abs(array_like()), array_like)
        exp = np.i0(a)
        res = np.i0(array_like())

        assert_array_equal(exp, res)

    def test_complex(self):
        a = np.array([0, 1 + 2j])
        with pytest.raises(TypeError, match="i0 not supported for complex values"):
            res = i0(a)


class TestKaiser:

    def test_simple(self):
        assert_(np.isfinite(kaiser(1, 1.0)))
        assert_almost_equal(kaiser(0, 1.0),
                            np.array([]))
        assert_almost_equal(kaiser(2, 1.0),
                            np.array([0.78984831, 0.78984831]))
        assert_almost_equal(kaiser(5, 1.0),
                            np.array([0.78984831, 0.94503323, 1.,
                                      0.94503323, 0.78984831]))
        assert_almost_equal(kaiser(5, 1.56789),
                            np.array([0.58285404, 0.88409679, 1.,
                                      0.88409679, 0.58285404]))

    def test_int_beta(self):
        kaiser(3, 4)


class TestMeshgrid:

    def test_simple(self):
        [X, Y] = meshgrid([1, 2, 3], [4, 5, 6, 7])
        assert_array_equal(X, np.array([[1, 2, 3],
                                        [1, 2, 3],
                                        [1, 2, 3],
                                        [1, 2, 3]]))
        assert_array_equal(Y, np.array([[4, 4, 4],
                                        [5, 5, 5],
                                        [6, 6, 6],
                                        [7, 7, 7]]))

    def test_single_input(self):
        [X] = meshgrid([1, 2, 3, 4])
        assert_array_equal(X, np.array([1, 2, 3, 4]))

    def test_no_input(self):
        args = []
        assert_array_equal([], meshgrid(*args))
        assert_array_equal([], meshgrid(*args, copy=False))

    def test_indexing(self):
        x = [1, 2, 3]
        y = [4, 5, 6, 7]
        [X, Y] = meshgrid(x, y, indexing='ij')
        assert_array_equal(X, np.array([[1, 1, 1, 1],
                                        [2, 2, 2, 2],
                                        [3, 3, 3, 3]]))
        assert_array_equal(Y, np.array([[4, 5, 6, 7],
                                        [4, 5, 6, 7],
                                        [4, 5, 6, 7]]))

        # Test expected shapes:
        z = [8, 9]
        assert_(meshgrid(x, y)[0].shape == (4, 3))
        assert_(meshgrid(x, y, indexing='ij')[0].shape == (3, 4))
        assert_(meshgrid(x, y, z)[0].shape == (4, 3, 2))
        assert_(meshgrid(x, y, z, indexing='ij')[0].shape == (3, 4, 2))

        assert_raises(ValueError, meshgrid, x, y, indexing='notvalid')

    def test_sparse(self):
        [X, Y] = meshgrid([1, 2, 3], [4, 5, 6, 7], sparse=True)
        assert_array_equal(X, np.array([[1, 2, 3]]))
        assert_array_equal(Y, np.array([[4], [5], [6], [7]]))

    def test_invalid_arguments(self):
        # Test that meshgrid complains about invalid arguments
        # Regression test for issue #4755:
        # https://github.com/numpy/numpy/issues/4755
        assert_raises(TypeError, meshgrid,
                      [1, 2, 3], [4, 5, 6, 7], indices='ij')

    def test_return_type(self):
        # Test for appropriate dtype in returned arrays.
        # Regression test for issue #5297
        # https://github.com/numpy/numpy/issues/5297
        x = np.arange(0, 10, dtype=np.float32)
        y = np.arange(10, 20, dtype=np.float64)

        X, Y = np.meshgrid(x, y)

        assert_(X.dtype == x.dtype)
        assert_(Y.dtype == y.dtype)

        # copy
        X, Y = np.meshgrid(x, y, copy=True)

        assert_(X.dtype == x.dtype)
        assert_(Y.dtype == y.dtype)

        # sparse
        X, Y = np.meshgrid(x, y, sparse=True)

        assert_(X.dtype == x.dtype)
        assert_(Y.dtype == y.dtype)

    def test_writeback(self):
        # Issue 8561
        X = np.array([1.1, 2.2])
        Y = np.array([3.3, 4.4])
        x, y = np.meshgrid(X, Y, sparse=False, copy=True)

        x[0, :] = 0
        assert_equal(x[0, :], 0)
        assert_equal(x[1, :], X)

    def test_nd_shape(self):
        a, b, c, d, e = np.meshgrid(*([0] * i for i in range(1, 6)))
        expected_shape = (2, 1, 3, 4, 5)
        assert_equal(a.shape, expected_shape)
        assert_equal(b.shape, expected_shape)
        assert_equal(c.shape, expected_shape)
        assert_equal(d.shape, expected_shape)
        assert_equal(e.shape, expected_shape)

    def test_nd_values(self):
        a, b, c = np.meshgrid([0], [1, 2], [3, 4, 5])
        assert_equal(a, [[[0, 0, 0]], [[0, 0, 0]]])
        assert_equal(b, [[[1, 1, 1]], [[2, 2, 2]]])
        assert_equal(c, [[[3, 4, 5]], [[3, 4, 5]]])

    def test_nd_indexing(self):
        a, b, c = np.meshgrid([0], [1, 2], [3, 4, 5], indexing='ij')
        assert_equal(a, [[[0, 0, 0], [0, 0, 0]]])
        assert_equal(b, [[[1, 1, 1], [2, 2, 2]]])
        assert_equal(c, [[[3, 4, 5], [3, 4, 5]]])


class TestPiecewise:

    def test_simple(self):
        # Condition is single bool list
        x = piecewise([0, 0], [True, False], [1])
        assert_array_equal(x, [1, 0])

        # List of conditions: single bool list
        x = piecewise([0, 0], [[True, False]], [1])
        assert_array_equal(x, [1, 0])

        # Conditions is single bool array
        x = piecewise([0, 0], np.array([True, False]), [1])
        assert_array_equal(x, [1, 0])

        # Condition is single int array
        x = piecewise([0, 0], np.array([1, 0]), [1])
        assert_array_equal(x, [1, 0])

        # List of conditions: int array
        x = piecewise([0, 0], [np.array([1, 0])], [1])
        assert_array_equal(x, [1, 0])

        x = piecewise([0, 0], [[False, True]], [lambda x:-1])
        assert_array_equal(x, [0, -1])

        assert_raises_regex(ValueError, '1 or 2 functions are expected',
            piecewise, [0, 0], [[False, True]], [])
        assert_raises_regex(ValueError, '1 or 2 functions are expected',
            piecewise, [0, 0], [[False, True]], [1, 2, 3])

    def test_two_conditions(self):
        x = piecewise([1, 2], [[True, False], [False, True]], [3, 4])
        assert_array_equal(x, [3, 4])

    def test_scalar_domains_three_conditions(self):
        x = piecewise(3, [True, False, False], [4, 2, 0])
        assert_equal(x, 4)

    def test_default(self):
        # No value specified for x[1], should be 0
        x = piecewise([1, 2], [True, False], [2])
        assert_array_equal(x, [2, 0])

        # Should set x[1] to 3
        x = piecewise([1, 2], [True, False], [2, 3])
        assert_array_equal(x, [2, 3])

    def test_0d(self):
        x = np.array(3)
        y = piecewise(x, x > 3, [4, 0])
        assert_(y.ndim == 0)
        assert_(y == 0)

        x = 5
        y = piecewise(x, [True, False], [1, 0])
        assert_(y.ndim == 0)
        assert_(y == 1)

        # With 3 ranges (It was failing, before)
        y = piecewise(x, [False, False, True], [1, 2, 3])
        assert_array_equal(y, 3)

    def test_0d_comparison(self):
        x = 3
        y = piecewise(x, [x <= 3, x > 3], [4, 0])  # Should succeed.
        assert_equal(y, 4)

        # With 3 ranges (It was failing, before)
        x = 4
        y = piecewise(x, [x <= 3, (x > 3) * (x <= 5), x > 5], [1, 2, 3])
        assert_array_equal(y, 2)

        assert_raises_regex(ValueError, '2 or 3 functions are expected',
            piecewise, x, [x <= 3, x > 3], [1])
        assert_raises_regex(ValueError, '2 or 3 functions are expected',
            piecewise, x, [x <= 3, x > 3], [1, 1, 1, 1])

    def test_0d_0d_condition(self):
        x = np.array(3)
        c = np.array(x > 3)
        y = piecewise(x, [c], [1, 2])
        assert_equal(y, 2)

    def test_multidimensional_extrafunc(self):
        x = np.array([[-2.5, -1.5, -0.5],
                      [0.5, 1.5, 2.5]])
        y = piecewise(x, [x < 0, x >= 2], [-1, 1, 3])
        assert_array_equal(y, np.array([[-1., -1., -1.],
                                        [3., 3., 1.]]))

    def test_subclasses(self):
        class subclass(np.ndarray):
            pass
        x = np.arange(5.).view(subclass)
        r = piecewise(x, [x < 2., x >= 4], [-1., 1., 0.])
        assert_equal(type(r), subclass)
        assert_equal(r, [-1., -1., 0., 0., 1.])


class TestBincount:

    def test_simple(self):
        y = np.bincount(np.arange(4))
        assert_array_equal(y, np.ones(4))

    def test_simple2(self):
        y = np.bincount(np.array([1, 5, 2, 4, 1]))
        assert_array_equal(y, np.array([0, 2, 1, 0, 1, 1]))

    def test_simple_weight(self):
        x = np.arange(4)
        w = np.array([0.2, 0.3, 0.5, 0.1])
        y = np.bincount(x, w)
        assert_array_equal(y, w)

    def test_simple_weight2(self):
        x = np.array([1, 2, 4, 5, 2])
        w = np.array([0.2, 0.3, 0.5, 0.1, 0.2])
        y = np.bincount(x, w)
        assert_array_equal(y, np.array([0, 0.2, 0.5, 0, 0.5, 0.1]))

    def test_with_minlength(self):
        x = np.array([0, 1, 0, 1, 1])
        y = np.bincount(x, minlength=3)
        assert_array_equal(y, np.array([2, 3, 0]))
        x = []
        y = np.bincount(x, minlength=0)
        assert_array_equal(y, np.array([]))

    def test_with_minlength_smaller_than_maxvalue(self):
        x = np.array([0, 1, 1, 2, 2, 3, 3])
        y = np.bincount(x, minlength=2)
        assert_array_equal(y, np.array([1, 2, 2, 2]))
        y = np.bincount(x, minlength=0)
        assert_array_equal(y, np.array([1, 2, 2, 2]))

    def test_with_minlength_and_weights(self):
        x = np.array([1, 2, 4, 5, 2])
        w = np.array([0.2, 0.3, 0.5, 0.1, 0.2])
        y = np.bincount(x, w, 8)
        assert_array_equal(y, np.array([0, 0.2, 0.5, 0, 0.5, 0.1, 0, 0]))

    def test_empty(self):
        x = np.array([], dtype=int)
        y = np.bincount(x)
        assert_array_equal(x, y)

    def test_empty_with_minlength(self):
        x = np.array([], dtype=int)
        y = np.bincount(x, minlength=5)
        assert_array_equal(y, np.zeros(5, dtype=int))

    @pytest.mark.parametrize('minlength', [0, 3])
    def test_empty_list(self, minlength):
        assert_array_equal(np.bincount([], minlength=minlength),
                           np.zeros(minlength, dtype=int))

    def test_with_incorrect_minlength(self):
        x = np.array([], dtype=int)
        assert_raises_regex(TypeError,
                            "'str' object cannot be interpreted",
                            lambda: np.bincount(x, minlength="foobar"))
        assert_raises_regex(ValueError,
                            "must not be negative",
                            lambda: np.bincount(x, minlength=-1))

        x = np.arange(5)
        assert_raises_regex(TypeError,
                            "'str' object cannot be interpreted",
                            lambda: np.bincount(x, minlength="foobar"))
        assert_raises_regex(ValueError,
                            "must not be negative",
                            lambda: np.bincount(x, minlength=-1))

    @pytest.mark.skipif(not HAS_REFCOUNT, reason="Python lacks refcounts")
    def test_dtype_reference_leaks(self):
        # gh-6805
        intp_refcount = sys.getrefcount(np.dtype(np.intp))
        double_refcount = sys.getrefcount(np.dtype(np.double))

        for j in range(10):
            np.bincount([1, 2, 3])
        assert_equal(sys.getrefcount(np.dtype(np.intp)), intp_refcount)
        assert_equal(sys.getrefcount(np.dtype(np.double)), double_refcount)

        for j in range(10):
            np.bincount([1, 2, 3], [4, 5, 6])
        assert_equal(sys.getrefcount(np.dtype(np.intp)), intp_refcount)
        assert_equal(sys.getrefcount(np.dtype(np.double)), double_refcount)

    @pytest.mark.parametrize("vals", [[[2, 2]], 2])
    def test_error_not_1d(self, vals):
        # Test that values has to be 1-D (both as array and nested list)
        vals_arr = np.asarray(vals)
        with assert_raises(ValueError):
            np.bincount(vals_arr)
        with assert_raises(ValueError):
            np.bincount(vals)

    @pytest.mark.parametrize("dt", np.typecodes["AllInteger"])
    def test_gh_28354(self, dt):
        a = np.array([0, 1, 1, 3, 2, 1, 7], dtype=dt)
        actual = np.bincount(a)
        expected = [1, 3, 1, 1, 0, 0, 0, 1]
        assert_array_equal(actual, expected)

    def test_contiguous_handling(self):
        # check for absence of hard crash
        np.bincount(np.arange(10000)[::2])

    def test_gh_28354_array_like(self):
        class A:
            def __array__(self):
                return np.array([0, 1, 1, 3, 2, 1, 7], dtype=np.uint64)

        a = A()
        actual = np.bincount(a)
        expected = [1, 3, 1, 1, 0, 0, 0, 1]
        assert_array_equal(actual, expected)


class TestInterp:

    def test_exceptions(self):
        assert_raises(ValueError, interp, 0, [], [])
        assert_raises(ValueError, interp, 0, [0], [1, 2])
        assert_raises(ValueError, interp, 0, [0, 1], [1, 2], period=0)
        assert_raises(ValueError, interp, 0, [], [], period=360)
        assert_raises(ValueError, interp, 0, [0], [1, 2], period=360)

    def test_basic(self):
        x = np.linspace(0, 1, 5)
        y = np.linspace(0, 1, 5)
        x0 = np.linspace(0, 1, 50)
        assert_almost_equal(np.interp(x0, x, y), x0)

    def test_right_left_behavior(self):
        # Needs range of sizes to test different code paths.
        # size ==1 is special cased, 1 < size < 5 is linear search, and
        # size >= 5 goes through local search and possibly binary search.
        for size in range(1, 10):
            xp = np.arange(size, dtype=np.double)
            yp = np.ones(size, dtype=np.double)
            incpts = np.array([-1, 0, size - 1, size], dtype=np.double)
            decpts = incpts[::-1]

            incres = interp(incpts, xp, yp)
            decres = interp(decpts, xp, yp)
            inctgt = np.array([1, 1, 1, 1], dtype=float)
            dectgt = inctgt[::-1]
            assert_equal(incres, inctgt)
            assert_equal(decres, dectgt)

            incres = interp(incpts, xp, yp, left=0)
            decres = interp(decpts, xp, yp, left=0)
            inctgt = np.array([0, 1, 1, 1], dtype=float)
            dectgt = inctgt[::-1]
            assert_equal(incres, inctgt)
            assert_equal(decres, dectgt)

            incres = interp(incpts, xp, yp, right=2)
            decres = interp(decpts, xp, yp, right=2)
            inctgt = np.array([1, 1, 1, 2], dtype=float)
            dectgt = inctgt[::-1]
            assert_equal(incres, inctgt)
            assert_equal(decres, dectgt)

            incres = interp(incpts, xp, yp, left=0, right=2)
            decres = interp(decpts, xp, yp, left=0, right=2)
            inctgt = np.array([0, 1, 1, 2], dtype=float)
            dectgt = inctgt[::-1]
            assert_equal(incres, inctgt)
            assert_equal(decres, dectgt)

    def test_scalar_interpolation_point(self):
        x = np.linspace(0, 1, 5)
        y = np.linspace(0, 1, 5)
        x0 = 0
        assert_almost_equal(np.interp(x0, x, y), x0)
        x0 = .3
        assert_almost_equal(np.interp(x0, x, y), x0)
        x0 = np.float32(.3)
        assert_almost_equal(np.interp(x0, x, y), x0)
        x0 = np.float64(.3)
        assert_almost_equal(np.interp(x0, x, y), x0)
        x0 = np.nan
        assert_almost_equal(np.interp(x0, x, y), x0)

    def test_non_finite_behavior_exact_x(self):
        x = [1, 2, 2.5, 3, 4]
        xp = [1, 2, 3, 4]
        fp = [1, 2, np.inf, 4]
        assert_almost_equal(np.interp(x, xp, fp), [1, 2, np.inf, np.inf, 4])
        fp = [1, 2, np.nan, 4]
        assert_almost_equal(np.interp(x, xp, fp), [1, 2, np.nan, np.nan, 4])

    @pytest.fixture(params=[
        np.float64,
        lambda x: _make_complex(x, 0),
        lambda x: _make_complex(0, x),
        lambda x: _make_complex(x, np.multiply(x, -2))
    ], ids=[
        'real',
        'complex-real',
        'complex-imag',
        'complex-both'
    ])
    def sc(self, request):
        """ scale function used by the below tests """
        return request.param

    def test_non_finite_any_nan(self, sc):
        """ test that nans are propagated """
        assert_equal(np.interp(0.5, [np.nan,      1], sc([     0,     10])), sc(np.nan))
        assert_equal(np.interp(0.5, [     0, np.nan], sc([     0,     10])), sc(np.nan))
        assert_equal(np.interp(0.5, [     0,      1], sc([np.nan,     10])), sc(np.nan))
        assert_equal(np.interp(0.5, [     0,      1], sc([     0, np.nan])), sc(np.nan))

    def test_non_finite_inf(self, sc):
        """ Test that interp between opposite infs gives nan """
        assert_equal(np.interp(0.5, [-np.inf, +np.inf], sc([      0,      10])), sc(np.nan))
        assert_equal(np.interp(0.5, [      0,       1], sc([-np.inf, +np.inf])), sc(np.nan))
        assert_equal(np.interp(0.5, [      0,       1], sc([+np.inf, -np.inf])), sc(np.nan))

        # unless the y values are equal
        assert_equal(np.interp(0.5, [-np.inf, +np.inf], sc([     10,      10])), sc(10))

    def test_non_finite_half_inf_xf(self, sc):
        """ Test that interp where both axes have a bound at inf gives nan """
        assert_equal(np.interp(0.5, [-np.inf,       1], sc([-np.inf,      10])), sc(np.nan))
        assert_equal(np.interp(0.5, [-np.inf,       1], sc([+np.inf,      10])), sc(np.nan))
        assert_equal(np.interp(0.5, [-np.inf,       1], sc([      0, -np.inf])), sc(np.nan))
        assert_equal(np.interp(0.5, [-np.inf,       1], sc([      0, +np.inf])), sc(np.nan))
        assert_equal(np.interp(0.5, [      0, +np.inf], sc([-np.inf,      10])), sc(np.nan))
        assert_equal(np.interp(0.5, [      0, +np.inf], sc([+np.inf,      10])), sc(np.nan))
        assert_equal(np.interp(0.5, [      0, +np.inf], sc([      0, -np.inf])), sc(np.nan))
        assert_equal(np.interp(0.5, [      0, +np.inf], sc([      0, +np.inf])), sc(np.nan))

    def test_non_finite_half_inf_x(self, sc):
        """ Test interp where the x axis has a bound at inf """
        assert_equal(np.interp(0.5, [-np.inf, -np.inf], sc([0, 10])), sc(10))
        assert_equal(np.interp(0.5, [-np.inf, 1      ], sc([0, 10])), sc(10))  # noqa: E202
        assert_equal(np.interp(0.5, [      0, +np.inf], sc([0, 10])), sc(0))
        assert_equal(np.interp(0.5, [+np.inf, +np.inf], sc([0, 10])), sc(0))

    def test_non_finite_half_inf_f(self, sc):
        """ Test interp where the f axis has a bound at inf """
        assert_equal(np.interp(0.5, [0, 1], sc([      0, -np.inf])), sc(-np.inf))
        assert_equal(np.interp(0.5, [0, 1], sc([      0, +np.inf])), sc(+np.inf))
        assert_equal(np.interp(0.5, [0, 1], sc([-np.inf,      10])), sc(-np.inf))
        assert_equal(np.interp(0.5, [0, 1], sc([+np.inf,      10])), sc(+np.inf))
        assert_equal(np.interp(0.5, [0, 1], sc([-np.inf, -np.inf])), sc(-np.inf))
        assert_equal(np.interp(0.5, [0, 1], sc([+np.inf, +np.inf])), sc(+np.inf))

    def test_complex_interp(self):
        # test complex interpolation
        x = np.linspace(0, 1, 5)
        y = np.linspace(0, 1, 5) + (1 + np.linspace(0, 1, 5)) * 1.0j
        x0 = 0.3
        y0 = x0 + (1 + x0) * 1.0j
        assert_almost_equal(np.interp(x0, x, y), y0)
        # test complex left and right
        x0 = -1
        left = 2 + 3.0j
        assert_almost_equal(np.interp(x0, x, y, left=left), left)
        x0 = 2.0
        right = 2 + 3.0j
        assert_almost_equal(np.interp(x0, x, y, right=right), right)
        # test complex non finite
        x = [1, 2, 2.5, 3, 4]
        xp = [1, 2, 3, 4]
        fp = [1, 2 + 1j, np.inf, 4]
        y = [1, 2 + 1j, np.inf + 0.5j, np.inf, 4]
        assert_almost_equal(np.interp(x, xp, fp), y)
        # test complex periodic
        x = [-180, -170, -185, 185, -10, -5, 0, 365]
        xp = [190, -190, 350, -350]
        fp = [5 + 1.0j, 10 + 2j, 3 + 3j, 4 + 4j]
        y = [7.5 + 1.5j, 5. + 1.0j, 8.75 + 1.75j, 6.25 + 1.25j, 3. + 3j, 3.25 + 3.25j,
             3.5 + 3.5j, 3.75 + 3.75j]
        assert_almost_equal(np.interp(x, xp, fp, period=360), y)

    def test_zero_dimensional_interpolation_point(self):
        x = np.linspace(0, 1, 5)
        y = np.linspace(0, 1, 5)
        x0 = np.array(.3)
        assert_almost_equal(np.interp(x0, x, y), x0)

        xp = np.array([0, 2, 4])
        fp = np.array([1, -1, 1])

        actual = np.interp(np.array(1), xp, fp)
        assert_equal(actual, 0)
        assert_(isinstance(actual, np.float64))

        actual = np.interp(np.array(4.5), xp, fp, period=4)
        assert_equal(actual, 0.5)
        assert_(isinstance(actual, np.float64))

    def test_if_len_x_is_small(self):
        xp = np.arange(0, 10, 0.0001)
        fp = np.sin(xp)
        assert_almost_equal(np.interp(np.pi, xp, fp), 0.0)

    def test_period(self):
        x = [-180, -170, -185, 185, -10, -5, 0, 365]
        xp = [190, -190, 350, -350]
        fp = [5, 10, 3, 4]
        y = [7.5, 5., 8.75, 6.25, 3., 3.25, 3.5, 3.75]
        assert_almost_equal(np.interp(x, xp, fp, period=360), y)
        x = np.array(x, order='F').reshape(2, -1)
        y = np.array(y, order='C').reshape(2, -1)
        assert_almost_equal(np.interp(x, xp, fp, period=360), y)


class TestPercentile:

    def test_basic(self):
        x = np.arange(8) * 0.5
        assert_equal(np.percentile(x, 0), 0.)
        assert_equal(np.percentile(x, 100), 3.5)
        assert_equal(np.percentile(x, 50), 1.75)
        x[1] = np.nan
        assert_equal(np.percentile(x, 0), np.nan)
        assert_equal(np.percentile(x, 0, method='nearest'), np.nan)
        assert_equal(np.percentile(x, 0, method='inverted_cdf'), np.nan)
        assert_equal(
            np.percentile(x, 0, method='inverted_cdf',
                          weights=np.ones_like(x)),
            np.nan,
        )

    def test_fraction(self):
        x = [Fraction(i, 2) for i in range(8)]

        p = np.percentile(x, Fraction(0))
        assert_equal(p, Fraction(0))
        assert_equal(type(p), Fraction)

        p = np.percentile(x, Fraction(100))
        assert_equal(p, Fraction(7, 2))
        assert_equal(type(p), Fraction)

        p = np.percentile(x, Fraction(50))
        assert_equal(p, Fraction(7, 4))
        assert_equal(type(p), Fraction)

        p = np.percentile(x, [Fraction(50)])
        assert_equal(p, np.array([Fraction(7, 4)]))
        assert_equal(type(p), np.ndarray)

    def test_api(self):
        d = np.ones(5)
        np.percentile(d, 5, None, None, False)
        np.percentile(d, 5, None, None, False, 'linear')
        o = np.ones((1,))
        np.percentile(d, 5, None, o, False, 'linear')

    def test_complex(self):
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='G')
        assert_raises(TypeError, np.percentile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='D')
        assert_raises(TypeError, np.percentile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='F')
        assert_raises(TypeError, np.percentile, arr_c, 0.5)

    def test_2D(self):
        x = np.array([[1, 1, 1],
                      [1, 1, 1],
                      [4, 4, 3],
                      [1, 1, 1],
                      [1, 1, 1]])
        assert_array_equal(np.percentile(x, 50, axis=0), [1, 1, 1])

    @pytest.mark.parametrize("dtype", np.typecodes["Float"])
    def test_linear_nan_1D(self, dtype):
        # METHOD 1 of H&F
        arr = np.asarray([15.0, np.nan, 35.0, 40.0, 50.0], dtype=dtype)
        res = np.percentile(
            arr,
            40.0,
            method="linear")
        np.testing.assert_equal(res, np.nan)
        np.testing.assert_equal(res.dtype, arr.dtype)

    H_F_TYPE_CODES = [(int_type, np.float64)
                      for int_type in np.typecodes["AllInteger"]
                      ] + [(np.float16, np.float16),
                           (np.float32, np.float32),
                           (np.float64, np.float64),
                           (np.longdouble, np.longdouble),
                           (np.dtype("O"), np.float64)]

    @pytest.mark.parametrize(["function", "quantile"],
                             [(np.quantile, 0.4),
                              (np.percentile, 40.0)])
    @pytest.mark.parametrize(["input_dtype", "expected_dtype"], H_F_TYPE_CODES)
    @pytest.mark.parametrize(["method", "weighted", "expected"],
                              [("inverted_cdf", False, 20),
                              ("inverted_cdf", True, 20),
                              ("averaged_inverted_cdf", False, 27.5),
                              ("closest_observation", False, 20),
                              ("interpolated_inverted_cdf", False, 20),
                              ("hazen", False, 27.5),
                              ("weibull", False, 26),
                              ("linear", False, 29),
                              ("median_unbiased", False, 27),
                              ("normal_unbiased", False, 27.125),
                               ])
    def test_linear_interpolation(self,
                                  function,
                                  quantile,
                                  method,
                                  weighted,
                                  expected,
                                  input_dtype,
                                  expected_dtype):
        expected_dtype = np.dtype(expected_dtype)

        arr = np.asarray([15.0, 20.0, 35.0, 40.0, 50.0], dtype=input_dtype)
        weights = np.ones_like(arr) if weighted else None
        if input_dtype is np.longdouble:
            if function is np.quantile:
                # 0.4 is not exactly representable and it matters
                # for "averaged_inverted_cdf", so we need to cheat.
                quantile = input_dtype("0.4")
            # We want to use nulp, but that does not work for longdouble
            test_function = np.testing.assert_almost_equal
        else:
            test_function = np.testing.assert_array_almost_equal_nulp

        actual = function(arr, quantile, method=method, weights=weights)

        test_function(actual, expected_dtype.type(expected))

        if method in ["inverted_cdf", "closest_observation"]:
            if input_dtype == "O":
                np.testing.assert_equal(np.asarray(actual).dtype, np.float64)
            else:
                np.testing.assert_equal(np.asarray(actual).dtype,
                                        np.dtype(input_dtype))
        else:
            np.testing.assert_equal(np.asarray(actual).dtype,
                                    np.dtype(expected_dtype))

    TYPE_CODES = np.typecodes["AllInteger"] + np.typecodes["Float"] + "O"

    @pytest.mark.parametrize("dtype", TYPE_CODES)
    def test_lower_higher(self, dtype):
        assert_equal(np.percentile(np.arange(10, dtype=dtype), 50,
                                   method='lower'), 4)
        assert_equal(np.percentile(np.arange(10, dtype=dtype), 50,
                                   method='higher'), 5)

    @pytest.mark.parametrize("dtype", TYPE_CODES)
    def test_midpoint(self, dtype):
        assert_equal(np.percentile(np.arange(10, dtype=dtype), 51,
                                   method='midpoint'), 4.5)
        assert_equal(np.percentile(np.arange(9, dtype=dtype) + 1, 50,
                                   method='midpoint'), 5)
        assert_equal(np.percentile(np.arange(11, dtype=dtype), 51,
                                   method='midpoint'), 5.5)
        assert_equal(np.percentile(np.arange(11, dtype=dtype), 50,
                                   method='midpoint'), 5)

    @pytest.mark.parametrize("dtype", TYPE_CODES)
    def test_nearest(self, dtype):
        assert_equal(np.percentile(np.arange(10, dtype=dtype), 51,
                                   method='nearest'), 5)
        assert_equal(np.percentile(np.arange(10, dtype=dtype), 49,
                                   method='nearest'), 4)

    def test_linear_interpolation_extrapolation(self):
        arr = np.random.rand(5)

        actual = np.percentile(arr, 100)
        np.testing.assert_equal(actual, arr.max())

        actual = np.percentile(arr, 0)
        np.testing.assert_equal(actual, arr.min())

    def test_sequence(self):
        x = np.arange(8) * 0.5
        assert_equal(np.percentile(x, [0, 100, 50]), [0, 3.5, 1.75])

    def test_axis(self):
        x = np.arange(12).reshape(3, 4)

        assert_equal(np.percentile(x, (25, 50, 100)), [2.75, 5.5, 11.0])

        r0 = [[2, 3, 4, 5], [4, 5, 6, 7], [8, 9, 10, 11]]
        assert_equal(np.percentile(x, (25, 50, 100), axis=0), r0)

        r1 = [[0.75, 1.5, 3], [4.75, 5.5, 7], [8.75, 9.5, 11]]
        assert_equal(np.percentile(x, (25, 50, 100), axis=1), np.array(r1).T)

        # ensure qth axis is always first as with np.array(old_percentile(..))
        x = np.arange(3 * 4 * 5 * 6).reshape(3, 4, 5, 6)
        assert_equal(np.percentile(x, (25, 50)).shape, (2,))
        assert_equal(np.percentile(x, (25, 50, 75)).shape, (3,))
        assert_equal(np.percentile(x, (25, 50), axis=0).shape, (2, 4, 5, 6))
        assert_equal(np.percentile(x, (25, 50), axis=1).shape, (2, 3, 5, 6))
        assert_equal(np.percentile(x, (25, 50), axis=2).shape, (2, 3, 4, 6))
        assert_equal(np.percentile(x, (25, 50), axis=3).shape, (2, 3, 4, 5))
        assert_equal(
            np.percentile(x, (25, 50, 75), axis=1).shape, (3, 3, 5, 6))
        assert_equal(np.percentile(x, (25, 50),
                                   method="higher").shape, (2,))
        assert_equal(np.percentile(x, (25, 50, 75),
                                   method="higher").shape, (3,))
        assert_equal(np.percentile(x, (25, 50), axis=0,
                                   method="higher").shape, (2, 4, 5, 6))
        assert_equal(np.percentile(x, (25, 50), axis=1,
                                   method="higher").shape, (2, 3, 5, 6))
        assert_equal(np.percentile(x, (25, 50), axis=2,
                                   method="higher").shape, (2, 3, 4, 6))
        assert_equal(np.percentile(x, (25, 50), axis=3,
                                   method="higher").shape, (2, 3, 4, 5))
        assert_equal(np.percentile(x, (25, 50, 75), axis=1,
                                   method="higher").shape, (3, 3, 5, 6))

    def test_scalar_q(self):
        # test for no empty dimensions for compatibility with old percentile
        x = np.arange(12).reshape(3, 4)
        assert_equal(np.percentile(x, 50), 5.5)
        assert_(np.isscalar(np.percentile(x, 50)))
        r0 = np.array([4., 5., 6., 7.])
        assert_equal(np.percentile(x, 50, axis=0), r0)
        assert_equal(np.percentile(x, 50, axis=0).shape, r0.shape)
        r1 = np.array([1.5, 5.5, 9.5])
        assert_almost_equal(np.percentile(x, 50, axis=1), r1)
        assert_equal(np.percentile(x, 50, axis=1).shape, r1.shape)

        out = np.empty(1)
        assert_equal(np.percentile(x, 50, out=out), 5.5)
        assert_equal(out, 5.5)
        out = np.empty(4)
        assert_equal(np.percentile(x, 50, axis=0, out=out), r0)
        assert_equal(out, r0)
        out = np.empty(3)
        assert_equal(np.percentile(x, 50, axis=1, out=out), r1)
        assert_equal(out, r1)

        # test for no empty dimensions for compatibility with old percentile
        x = np.arange(12).reshape(3, 4)
        assert_equal(np.percentile(x, 50, method='lower'), 5.)
        assert_(np.isscalar(np.percentile(x, 50)))
        r0 = np.array([4., 5., 6., 7.])
        c0 = np.percentile(x, 50, method='lower', axis=0)
        assert_equal(c0, r0)
        assert_equal(c0.shape, r0.shape)
        r1 = np.array([1., 5., 9.])
        c1 = np.percentile(x, 50, method='lower', axis=1)
        assert_almost_equal(c1, r1)
        assert_equal(c1.shape, r1.shape)

        out = np.empty((), dtype=x.dtype)
        c = np.percentile(x, 50, method='lower', out=out)
        assert_equal(c, 5)
        assert_equal(out, 5)
        out = np.empty(4, dtype=x.dtype)
        c = np.percentile(x, 50, method='lower', axis=0, out=out)
        assert_equal(c, r0)
        assert_equal(out, r0)
        out = np.empty(3, dtype=x.dtype)
        c = np.percentile(x, 50, method='lower', axis=1, out=out)
        assert_equal(c, r1)
        assert_equal(out, r1)

    def test_exception(self):
        assert_raises(ValueError, np.percentile, [1, 2], 56,
                      method='foobar')
        assert_raises(ValueError, np.percentile, [1], 101)
        assert_raises(ValueError, np.percentile, [1], -1)
        assert_raises(ValueError, np.percentile, [1], list(range(50)) + [101])
        assert_raises(ValueError, np.percentile, [1], list(range(50)) + [-0.1])

    def test_percentile_list(self):
        assert_equal(np.percentile([1, 2, 3], 0), 1)

    @pytest.mark.parametrize(
        "percentile, with_weights",
        [
            (np.percentile, False),
            (partial(np.percentile, method="inverted_cdf"), True),
        ]
    )
    def test_percentile_out(self, percentile, with_weights):
        out_dtype = int if with_weights else float
        x = np.array([1, 2, 3])
        y = np.zeros((3,), dtype=out_dtype)
        p = (1, 2, 3)
        weights = np.ones_like(x) if with_weights else None
        r = percentile(x, p, out=y, weights=weights)
        assert r is y
        assert_equal(percentile(x, p, weights=weights), y)

        x = np.array([[1, 2, 3],
                      [4, 5, 6]])
        y = np.zeros((3, 3), dtype=out_dtype)
        weights = np.ones_like(x) if with_weights else None
        r = percentile(x, p, axis=0, out=y, weights=weights)
        assert r is y
        assert_equal(percentile(x, p, weights=weights, axis=0), y)

        y = np.zeros((3, 2), dtype=out_dtype)
        percentile(x, p, axis=1, out=y, weights=weights)
        assert_equal(percentile(x, p, weights=weights, axis=1), y)

        x = np.arange(12).reshape(3, 4)
        # q.dim > 1, float
        if with_weights:
            r0 = np.array([[0, 1, 2, 3], [4, 5, 6, 7]])
        else:
            r0 = np.array([[2., 3., 4., 5.], [4., 5., 6., 7.]])
        out = np.empty((2, 4), dtype=out_dtype)
        weights = np.ones_like(x) if with_weights else None
        assert_equal(
            percentile(x, (25, 50), axis=0, out=out, weights=weights), r0
        )
        assert_equal(out, r0)
        r1 = np.array([[0.75, 4.75, 8.75], [1.5, 5.5, 9.5]])
        out = np.empty((2, 3))
        assert_equal(np.percentile(x, (25, 50), axis=1, out=out), r1)
        assert_equal(out, r1)

        # q.dim > 1, int
        r0 = np.array([[0, 1, 2, 3], [4, 5, 6, 7]])
        out = np.empty((2, 4), dtype=x.dtype)
        c = np.percentile(x, (25, 50), method='lower', axis=0, out=out)
        assert_equal(c, r0)
        assert_equal(out, r0)
        r1 = np.array([[0, 4, 8], [1, 5, 9]])
        out = np.empty((2, 3), dtype=x.dtype)
        c = np.percentile(x, (25, 50), method='lower', axis=1, out=out)
        assert_equal(c, r1)
        assert_equal(out, r1)

    def test_percentile_empty_dim(self):
        # empty dims are preserved
        d = np.arange(11 * 2).reshape(11, 1, 2, 1)
        assert_array_equal(np.percentile(d, 50, axis=0).shape, (1, 2, 1))
        assert_array_equal(np.percentile(d, 50, axis=1).shape, (11, 2, 1))
        assert_array_equal(np.percentile(d, 50, axis=2).shape, (11, 1, 1))
        assert_array_equal(np.percentile(d, 50, axis=3).shape, (11, 1, 2))
        assert_array_equal(np.percentile(d, 50, axis=-1).shape, (11, 1, 2))
        assert_array_equal(np.percentile(d, 50, axis=-2).shape, (11, 1, 1))
        assert_array_equal(np.percentile(d, 50, axis=-3).shape, (11, 2, 1))
        assert_array_equal(np.percentile(d, 50, axis=-4).shape, (1, 2, 1))

        assert_array_equal(np.percentile(d, 50, axis=2,
                                         method='midpoint').shape,
                           (11, 1, 1))
        assert_array_equal(np.percentile(d, 50, axis=-2,
                                         method='midpoint').shape,
                           (11, 1, 1))

        assert_array_equal(np.array(np.percentile(d, [10, 50], axis=0)).shape,
                           (2, 1, 2, 1))
        assert_array_equal(np.array(np.percentile(d, [10, 50], axis=1)).shape,
                           (2, 11, 2, 1))
        assert_array_equal(np.array(np.percentile(d, [10, 50], axis=2)).shape,
                           (2, 11, 1, 1))
        assert_array_equal(np.array(np.percentile(d, [10, 50], axis=3)).shape,
                           (2, 11, 1, 2))

    def test_percentile_no_overwrite(self):
        a = np.array([2, 3, 4, 1])
        np.percentile(a, [50], overwrite_input=False)
        assert_equal(a, np.array([2, 3, 4, 1]))

        a = np.array([2, 3, 4, 1])
        np.percentile(a, [50])
        assert_equal(a, np.array([2, 3, 4, 1]))

    def test_no_p_overwrite(self):
        p = np.linspace(0., 100., num=5)
        np.percentile(np.arange(100.), p, method="midpoint")
        assert_array_equal(p, np.linspace(0., 100., num=5))
        p = np.linspace(0., 100., num=5).tolist()
        np.percentile(np.arange(100.), p, method="midpoint")
        assert_array_equal(p, np.linspace(0., 100., num=5).tolist())

    def test_percentile_overwrite(self):
        a = np.array([2, 3, 4, 1])
        b = np.percentile(a, [50], overwrite_input=True)
        assert_equal(b, np.array([2.5]))

        b = np.percentile([2, 3, 4, 1], [50], overwrite_input=True)
        assert_equal(b, np.array([2.5]))

    def test_extended_axis(self):
        o = np.random.normal(size=(71, 23))
        x = np.dstack([o] * 10)
        assert_equal(np.percentile(x, 30, axis=(0, 1)), np.percentile(o, 30))
        x = np.moveaxis(x, -1, 0)
        assert_equal(np.percentile(x, 30, axis=(-2, -1)), np.percentile(o, 30))
        x = x.swapaxes(0, 1).copy()
        assert_equal(np.percentile(x, 30, axis=(0, -1)), np.percentile(o, 30))
        x = x.swapaxes(0, 1).copy()

        assert_equal(np.percentile(x, [25, 60], axis=(0, 1, 2)),
                     np.percentile(x, [25, 60], axis=None))
        assert_equal(np.percentile(x, [25, 60], axis=(0,)),
                     np.percentile(x, [25, 60], axis=0))

        d = np.arange(3 * 5 * 7 * 11).reshape((3, 5, 7, 11))
        np.random.shuffle(d.ravel())
        assert_equal(np.percentile(d, 25, axis=(0, 1, 2))[0],
                     np.percentile(d[:, :, :, 0].flatten(), 25))
        assert_equal(np.percentile(d, [10, 90], axis=(0, 1, 3))[:, 1],
                     np.percentile(d[:, :, 1, :].flatten(), [10, 90]))
        assert_equal(np.percentile(d, 25, axis=(3, 1, -4))[2],
                     np.percentile(d[:, :, 2, :].flatten(), 25))
        assert_equal(np.percentile(d, 25, axis=(3, 1, 2))[2],
                     np.percentile(d[2, :, :, :].flatten(), 25))
        assert_equal(np.percentile(d, 25, axis=(3, 2))[2, 1],
                     np.percentile(d[2, 1, :, :].flatten(), 25))
        assert_equal(np.percentile(d, 25, axis=(1, -2))[2, 1],
                     np.percentile(d[2, :, :, 1].flatten(), 25))
        assert_equal(np.percentile(d, 25, axis=(1, 3))[2, 2],
                     np.percentile(d[2, :, 2, :].flatten(), 25))

    def test_extended_axis_invalid(self):
        d = np.ones((3, 5, 7, 11))
        assert_raises(AxisError, np.percentile, d, axis=-5, q=25)
        assert_raises(AxisError, np.percentile, d, axis=(0, -5), q=25)
        assert_raises(AxisError, np.percentile, d, axis=4, q=25)
        assert_raises(AxisError, np.percentile, d, axis=(0, 4), q=25)
        # each of these refers to the same axis twice
        assert_raises(ValueError, np.percentile, d, axis=(1, 1), q=25)
        assert_raises(ValueError, np.percentile, d, axis=(-1, -1), q=25)
        assert_raises(ValueError, np.percentile, d, axis=(3, -1), q=25)

    def test_keepdims(self):
        d = np.ones((3, 5, 7, 11))
        assert_equal(np.percentile(d, 7, axis=None, keepdims=True).shape,
                     (1, 1, 1, 1))
        assert_equal(np.percentile(d, 7, axis=(0, 1), keepdims=True).shape,
                     (1, 1, 7, 11))
        assert_equal(np.percentile(d, 7, axis=(0, 3), keepdims=True).shape,
                     (1, 5, 7, 1))
        assert_equal(np.percentile(d, 7, axis=(1,), keepdims=True).shape,
                     (3, 1, 7, 11))
        assert_equal(np.percentile(d, 7, (0, 1, 2, 3), keepdims=True).shape,
                     (1, 1, 1, 1))
        assert_equal(np.percentile(d, 7, axis=(0, 1, 3), keepdims=True).shape,
                     (1, 1, 7, 1))

        assert_equal(np.percentile(d, [1, 7], axis=(0, 1, 3),
                                   keepdims=True).shape, (2, 1, 1, 7, 1))
        assert_equal(np.percentile(d, [1, 7], axis=(0, 3),
                                   keepdims=True).shape, (2, 1, 5, 7, 1))

    @pytest.mark.parametrize('q', [7, [1, 7]])
    @pytest.mark.parametrize(
        argnames='axis',
        argvalues=[
            None,
            1,
            (1,),
            (0, 1),
            (-3, -1),
        ]
    )
    def test_keepdims_out(self, q, axis):
        d = np.ones((3, 5, 7, 11))
        if axis is None:
            shape_out = (1,) * d.ndim
        else:
            axis_norm = normalize_axis_tuple(axis, d.ndim)
            shape_out = tuple(
                1 if i in axis_norm else d.shape[i] for i in range(d.ndim))
        shape_out = np.shape(q) + shape_out

        out = np.empty(shape_out)
        result = np.percentile(d, q, axis=axis, keepdims=True, out=out)
        assert result is out
        assert_equal(result.shape, shape_out)

    def test_out(self):
        o = np.zeros((4,))
        d = np.ones((3, 4))
        assert_equal(np.percentile(d, 0, 0, out=o), o)
        assert_equal(np.percentile(d, 0, 0, method='nearest', out=o), o)
        o = np.zeros((3,))
        assert_equal(np.percentile(d, 1, 1, out=o), o)
        assert_equal(np.percentile(d, 1, 1, method='nearest', out=o), o)

        o = np.zeros(())
        assert_equal(np.percentile(d, 2, out=o), o)
        assert_equal(np.percentile(d, 2, method='nearest', out=o), o)

    @pytest.mark.parametrize("method, weighted", [
        ("linear", False),
        ("nearest", False),
        ("inverted_cdf", False),
        ("inverted_cdf", True),
    ])
    def test_out_nan(self, method, weighted):
        if weighted:
            kwargs = {"weights": np.ones((3, 4)), "method": method}
        else:
            kwargs = {"method": method}
        with warnings.catch_warnings(record=True):
            warnings.filterwarnings('always', '', RuntimeWarning)
            o = np.zeros((4,))
            d = np.ones((3, 4))
            d[2, 1] = np.nan
            assert_equal(np.percentile(d, 0, 0, out=o, **kwargs), o)

            o = np.zeros((3,))
            assert_equal(np.percentile(d, 1, 1, out=o, **kwargs), o)

            o = np.zeros(())
            assert_equal(np.percentile(d, 1, out=o, **kwargs), o)

    def test_nan_behavior(self):
        a = np.arange(24, dtype=float)
        a[2] = np.nan
        assert_equal(np.percentile(a, 0.3), np.nan)
        assert_equal(np.percentile(a, 0.3, axis=0), np.nan)
        assert_equal(np.percentile(a, [0.3, 0.6], axis=0),
                     np.array([np.nan] * 2))

        a = np.arange(24, dtype=float).reshape(2, 3, 4)
        a[1, 2, 3] = np.nan
        a[1, 1, 2] = np.nan

        # no axis
        assert_equal(np.percentile(a, 0.3), np.nan)
        assert_equal(np.percentile(a, 0.3).ndim, 0)

        # axis0 zerod
        b = np.percentile(np.arange(24, dtype=float).reshape(2, 3, 4), 0.3, 0)
        b[2, 3] = np.nan
        b[1, 2] = np.nan
        assert_equal(np.percentile(a, 0.3, 0), b)

        # axis0 not zerod
        b = np.percentile(np.arange(24, dtype=float).reshape(2, 3, 4),
                          [0.3, 0.6], 0)
        b[:, 2, 3] = np.nan
        b[:, 1, 2] = np.nan
        assert_equal(np.percentile(a, [0.3, 0.6], 0), b)

        # axis1 zerod
        b = np.percentile(np.arange(24, dtype=float).reshape(2, 3, 4), 0.3, 1)
        b[1, 3] = np.nan
        b[1, 2] = np.nan
        assert_equal(np.percentile(a, 0.3, 1), b)
        # axis1 not zerod
        b = np.percentile(
            np.arange(24, dtype=float).reshape(2, 3, 4), [0.3, 0.6], 1)
        b[:, 1, 3] = np.nan
        b[:, 1, 2] = np.nan
        assert_equal(np.percentile(a, [0.3, 0.6], 1), b)

        # axis02 zerod
        b = np.percentile(
            np.arange(24, dtype=float).reshape(2, 3, 4), 0.3, (0, 2))
        b[1] = np.nan
        b[2] = np.nan
        assert_equal(np.percentile(a, 0.3, (0, 2)), b)
        # axis02 not zerod
        b = np.percentile(np.arange(24, dtype=float).reshape(2, 3, 4),
                          [0.3, 0.6], (0, 2))
        b[:, 1] = np.nan
        b[:, 2] = np.nan
        assert_equal(np.percentile(a, [0.3, 0.6], (0, 2)), b)
        # axis02 not zerod with method='nearest'
        b = np.percentile(np.arange(24, dtype=float).reshape(2, 3, 4),
                          [0.3, 0.6], (0, 2), method='nearest')
        b[:, 1] = np.nan
        b[:, 2] = np.nan
        assert_equal(np.percentile(
            a, [0.3, 0.6], (0, 2), method='nearest'), b)

    def test_nan_q(self):
        # GH18830
        with pytest.raises(ValueError, match="Percentiles must be in"):
            np.percentile([1, 2, 3, 4.0], np.nan)
        with pytest.raises(ValueError, match="Percentiles must be in"):
            np.percentile([1, 2, 3, 4.0], [np.nan])
        q = np.linspace(1.0, 99.0, 16)
        q[0] = np.nan
        with pytest.raises(ValueError, match="Percentiles must be in"):
            np.percentile([1, 2, 3, 4.0], q)

    @pytest.mark.parametrize("dtype", ["m8[D]", "M8[s]"])
    @pytest.mark.parametrize("pos", [0, 23, 10])
    def test_nat_basic(self, dtype, pos):
        # TODO: Note that times have dubious rounding as of fixing NaTs!
        # NaT and NaN should behave the same, do basic tests for NaT:
        a = np.arange(0, 24, dtype=dtype)
        a[pos] = "NaT"
        res = np.percentile(a, 30)
        assert res.dtype == dtype
        assert np.isnat(res)
        res = np.percentile(a, [30, 60])
        assert res.dtype == dtype
        assert np.isnat(res).all()

        a = np.arange(0, 24 * 3, dtype=dtype).reshape(-1, 3)
        a[pos, 1] = "NaT"
        res = np.percentile(a, 30, axis=0)
        assert_array_equal(np.isnat(res), [False, True, False])


quantile_methods = [
    'inverted_cdf', 'averaged_inverted_cdf', 'closest_observation',
    'interpolated_inverted_cdf', 'hazen', 'weibull', 'linear',
    'median_unbiased', 'normal_unbiased', 'nearest', 'lower', 'higher',
    'midpoint']


methods_supporting_weights = ["inverted_cdf"]


class TestQuantile:
    # most of this is already tested by TestPercentile

    def V(self, x, y, alpha):
        # Identification function used in several tests.
        return (x >= y) - alpha

    def test_max_ulp(self):
        x = [0.0, 0.2, 0.4]
        a = np.quantile(x, 0.45)
        # The default linear method would result in 0 + 0.2 * (0.45/2) = 0.18.
        # 0.18 is not exactly representable and the formula leads to a 1 ULP
        # different result. Ensure it is this exact within 1 ULP, see gh-20331.
        np.testing.assert_array_max_ulp(a, 0.18, maxulp=1)

    def test_basic(self):
        x = np.arange(8) * 0.5
        assert_equal(np.quantile(x, 0), 0.)
        assert_equal(np.quantile(x, 1), 3.5)
        assert_equal(np.quantile(x, 0.5), 1.75)

    def test_correct_quantile_value(self):
        a = np.array([True])
        tf_quant = np.quantile(True, False)
        assert_equal(tf_quant, a[0])
        assert_equal(type(tf_quant), a.dtype)
        a = np.array([False, True, True])
        quant_res = np.quantile(a, a)
        assert_array_equal(quant_res, a)
        assert_equal(quant_res.dtype, a.dtype)

    def test_fraction(self):
        # fractional input, integral quantile
        x = [Fraction(i, 2) for i in range(8)]
        q = np.quantile(x, 0)
        assert_equal(q, 0)
        assert_equal(type(q), Fraction)

        q = np.quantile(x, 1)
        assert_equal(q, Fraction(7, 2))
        assert_equal(type(q), Fraction)

        q = np.quantile(x, .5)
        assert_equal(q, 1.75)
        assert_equal(type(q), np.float64)

        q = np.quantile(x, Fraction(1, 2))
        assert_equal(q, Fraction(7, 4))
        assert_equal(type(q), Fraction)

        q = np.quantile(x, [Fraction(1, 2)])
        assert_equal(q, np.array([Fraction(7, 4)]))
        assert_equal(type(q), np.ndarray)

        q = np.quantile(x, [[Fraction(1, 2)]])
        assert_equal(q, np.array([[Fraction(7, 4)]]))
        assert_equal(type(q), np.ndarray)

        # repeat with integral input but fractional quantile
        x = np.arange(8)
        assert_equal(np.quantile(x, Fraction(1, 2)), Fraction(7, 2))

    def test_complex(self):
        # gh-22652
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='G')
        assert_raises(TypeError, np.quantile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='D')
        assert_raises(TypeError, np.quantile, arr_c, 0.5)
        arr_c = np.array([0.5 + 3.0j, 2.1 + 0.5j, 1.6 + 2.3j], dtype='F')
        assert_raises(TypeError, np.quantile, arr_c, 0.5)

    def test_no_p_overwrite(self):
        # this is worth retesting, because quantile does not make a copy
        p0 = np.array([0, 0.75, 0.25, 0.5, 1.0])
        p = p0.copy()
        np.quantile(np.arange(100.), p, method="midpoint")
        assert_array_equal(p, p0)

        p0 = p0.tolist()
        p = p.tolist()
        np.quantile(np.arange(100.), p, method="midpoint")
        assert_array_equal(p, p0)

    @pytest.mark.parametrize("dtype", np.typecodes["AllInteger"])
    def test_quantile_preserve_int_type(self, dtype):
        res = np.quantile(np.array([1, 2], dtype=dtype), [0.5],
                          method="nearest")
        assert res.dtype == dtype

    @pytest.mark.parametrize("method", quantile_methods)
    def test_q_zero_one(self, method):
        # gh-24710
        arr = [10, 11, 12]
        quantile = np.quantile(arr, q=[0, 1], method=method)
        assert_equal(quantile, np.array([10, 12]))

    @pytest.mark.parametrize("method", quantile_methods)
    def test_quantile_monotonic(self, method):
        # GH 14685
        # test that the return value of quantile is monotonic if p0 is ordered
        # Also tests that the boundary values are not mishandled.
        p0 = np.linspace(0, 1, 101)
        quantile = np.quantile(np.array([0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 1, 1, 9, 9, 9,
                                         8, 8, 7]) * 0.1, p0, method=method)
        assert_equal(np.sort(quantile), quantile)

        # Also test one where the number of data points is clearly divisible:
        quantile = np.quantile([0., 1., 2., 3.], p0, method=method)
        assert_equal(np.sort(quantile), quantile)

    @hypothesis.given(
            arr=arrays(dtype=np.float64,
                       shape=st.integers(min_value=3, max_value=1000),
                       elements=st.floats(allow_infinity=False, allow_nan=False,
                                          min_value=-1e300, max_value=1e300)))
    def test_quantile_monotonic_hypo(self, arr):
        p0 = np.arange(0, 1, 0.01)
        quantile = np.quantile(arr, p0)
        assert_equal(np.sort(quantile), quantile)

    def test_quantile_scalar_nan(self):
        a = np.array([[10., 7., 4.], [3., 2., 1.]])
        a[0][1] = np.nan
        actual = np.quantile(a, 0.5)
        assert np.isscalar(actual)
        assert_equal(np.quantile(a, 0.5), np.nan)

    @pytest.mark.parametrize("weights", [False, True])
    @pytest.mark.parametrize("method", quantile_methods)
    @pytest.mark.parametrize("alpha", [0.2, 0.5, 0.9])
    def test_quantile_identification_equation(self, weights, method, alpha):
        # Test that the identification equation holds for the empirical
        # CDF:
        #   E[V(x, Y)] = 0  <=>  x is quantile
        # with Y the random variable for which we have observed values and
        # V(x, y) the canonical identification function for the quantile (at
        # level alpha), see
        # https://doi.org/10.48550/arXiv.0912.0902
        if weights and method not in methods_supporting_weights:
            pytest.skip("Weights not supported by method.")
        rng = np.random.default_rng(4321)
        # We choose n and alpha such that we cover 3 cases:
        #  - n * alpha is an integer
        #  - n * alpha is a float that gets rounded down
        #  - n * alpha is a float that gest rounded up
        n = 102  # n * alpha = 20.4, 51. , 91.8
        y = rng.random(n)
        w = rng.integers(low=0, high=10, size=n) if weights else None
        x = np.quantile(y, alpha, method=method, weights=w)

        if method in ("higher",):
            # These methods do not fulfill the identification equation.
            assert np.abs(np.mean(self.V(x, y, alpha))) > 0.1 / n
        elif int(n * alpha) == n * alpha and not weights:
            # We can expect exact results, up to machine precision.
            assert_allclose(
                np.average(self.V(x, y, alpha), weights=w), 0, atol=1e-14,
            )
        else:
            # V = (x >= y) - alpha cannot sum to zero exactly but within
            # "sample precision".
            assert_allclose(np.average(self.V(x, y, alpha), weights=w), 0,
                atol=1 / n / np.amin([alpha, 1 - alpha]))

    @pytest.mark.parametrize("weights", [False, True])
    @pytest.mark.parametrize("method", quantile_methods)
    @pytest.mark.parametrize("alpha", [0.2, 0.5, 0.9])
    def test_quantile_add_and_multiply_constant(self, weights, method, alpha):
        # Test that
        #  1. quantile(c + x) = c + quantile(x)
        #  2. quantile(c * x) = c * quantile(x)
        #  3. quantile(-x) = -quantile(x, 1 - alpha)
        #     On empirical quantiles, this equation does not hold exactly.
        # Koenker (2005) "Quantile Regression" Chapter 2.2.3 calls these
        # properties equivariance.
        if weights and method not in methods_supporting_weights:
            pytest.skip("Weights not supported by method.")
        rng = np.random.default_rng(4321)
        # We choose n and alpha such that we have cases for
        #  - n * alpha is an integer
        #  - n * alpha is a float that gets rounded down
        #  - n * alpha is a float that gest rounded up
        n = 102  # n * alpha = 20.4, 51. , 91.8
        y = rng.random(n)
        w = rng.integers(low=0, high=10, size=n) if weights else None
        q = np.quantile(y, alpha, method=method, weights=w)
        c = 13.5

        # 1
        assert_allclose(np.quantile(c + y, alpha, method=method, weights=w),
                        c + q)
        # 2
        assert_allclose(np.quantile(c * y, alpha, method=method, weights=w),
                        c * q)
        # 3
        if weights:
            # From here on, we would need more methods to support weights.
            return
        q = -np.quantile(-y, 1 - alpha, method=method)
        if method == "inverted_cdf":
            if (
                n * alpha == int(n * alpha)
                or np.round(n * alpha) == int(n * alpha) + 1
            ):
                assert_allclose(q, np.quantile(y, alpha, method="higher"))
            else:
                assert_allclose(q, np.quantile(y, alpha, method="lower"))
        elif method == "closest_observation":
            if n * alpha == int(n * alpha):
                assert_allclose(q, np.quantile(y, alpha, method="higher"))
            elif np.round(n * alpha) == int(n * alpha) + 1:
                assert_allclose(
                    q, np.quantile(y, alpha + 1 / n, method="higher"))
            else:
                assert_allclose(q, np.quantile(y, alpha, method="lower"))
        elif method == "interpolated_inverted_cdf":
            assert_allclose(q, np.quantile(y, alpha + 1 / n, method=method))
        elif method == "nearest":
            if n * alpha == int(n * alpha):
                assert_allclose(q, np.quantile(y, alpha + 1 / n, method=method))
            else:
                assert_allclose(q, np.quantile(y, alpha, method=method))
        elif method == "lower":
            assert_allclose(q, np.quantile(y, alpha, method="higher"))
        elif method == "higher":
            assert_allclose(q, np.quantile(y, alpha, method="lower"))
        else:
            # "averaged_inverted_cdf", "hazen", "weibull", "linear",
            # "median_unbiased", "normal_unbiased", "midpoint"
            assert_allclose(q, np.quantile(y, alpha, method=method))

    @pytest.mark.parametrize("method", methods_supporting_weights)
    @pytest.mark.parametrize("alpha", [0.2, 0.5, 0.9])
    def test_quantile_constant_weights(self, method, alpha):
        rng = np.random.default_rng(4321)
        # We choose n and alpha such that we have cases for
        #  - n * alpha is an integer
        #  - n * alpha is a float that gets rounded down
        #  - n * alpha is a float that gest rounded up
        n = 102  # n * alpha = 20.4, 51. , 91.8
        y = rng.random(n)
        q = np.quantile(y, alpha, method=method)

        w = np.ones_like(y)
        qw = np.quantile(y, alpha, method=method, weights=w)
        assert_allclose(qw, q)

        w = 8.125 * np.ones_like(y)
        qw = np.quantile(y, alpha, method=method, weights=w)
        assert_allclose(qw, q)

    @pytest.mark.parametrize("method", methods_supporting_weights)
    @pytest.mark.parametrize("alpha", [0, 0.2, 0.5, 0.9, 1])
    def test_quantile_with_integer_weights(self, method, alpha):
        # Integer weights can be interpreted as repeated observations.
        rng = np.random.default_rng(4321)
        # We choose n and alpha such that we have cases for
        #  - n * alpha is an integer
        #  - n * alpha is a float that gets rounded down
        #  - n * alpha is a float that gest rounded up
        n = 102  # n * alpha = 20.4, 51. , 91.8
        y = rng.random(n)
        w = rng.integers(low=0, high=10, size=n, dtype=np.int32)

        qw = np.quantile(y, alpha, method=method, weights=w)
        q = np.quantile(np.repeat(y, w), alpha, method=method)
        assert_allclose(qw, q)

    @pytest.mark.parametrize("method", methods_supporting_weights)
    def test_quantile_with_weights_and_axis(self, method):
        rng = np.random.default_rng(4321)

        # 1d weight and single alpha
        y = rng.random((2, 10, 3))
        w = np.abs(rng.random(10))
        alpha = 0.5
        q = np.quantile(y, alpha, weights=w, method=method, axis=1)
        q_res = np.zeros(shape=(2, 3))
        for i in range(2):
            for j in range(3):
                q_res[i, j] = np.quantile(
                    y[i, :, j], alpha, method=method, weights=w
                )
        assert_allclose(q, q_res)

        # 1d weight and 1d alpha
        alpha = [0, 0.2, 0.4, 0.6, 0.8, 1]  # shape (6,)
        q = np.quantile(y, alpha, weights=w, method=method, axis=1)
        q_res = np.zeros(shape=(6, 2, 3))
        for i in range(2):
            for j in range(3):
                q_res[:, i, j] = np.quantile(
                    y[i, :, j], alpha, method=method, weights=w
                )
        assert_allclose(q, q_res)

        # 1d weight and 2d alpha
        alpha = [[0, 0.2], [0.4, 0.6], [0.8, 1]]  # shape (3, 2)
        q = np.quantile(y, alpha, weights=w, method=method, axis=1)
        q_res = q_res.reshape((3, 2, 2, 3))
        assert_allclose(q, q_res)

        # shape of weights equals shape of y
        w = np.abs(rng.random((2, 10, 3)))
        alpha = 0.5
        q = np.quantile(y, alpha, weights=w, method=method, axis=1)
        q_res = np.zeros(shape=(2, 3))
        for i in range(2):
            for j in range(3):
                q_res[i, j] = np.quantile(
                    y[i, :, j], alpha, method=method, weights=w[i, :, j]
                )
        assert_allclose(q, q_res)

    @pytest.mark.parametrize("method", methods_supporting_weights)
    def test_quantile_weights_min_max(self, method):
        # Test weighted quantile at 0 and 1 with leading and trailing zero
        # weights.
        w = [0, 0, 1, 2, 3, 0]
        y = np.arange(6)
        y_min = np.quantile(y, 0, weights=w, method="inverted_cdf")
        y_max = np.quantile(y, 1, weights=w, method="inverted_cdf")
        assert y_min == y[2]  # == 2
        assert y_max == y[4]  # == 4

    def test_quantile_weights_raises_negative_weights(self):
        y = [1, 2]
        w = [-0.5, 1]
        with pytest.raises(ValueError, match="Weights must be non-negative"):
            np.quantile(y, 0.5, weights=w, method="inverted_cdf")

    @pytest.mark.parametrize(
            "method",
            sorted(set(quantile_methods) - set(methods_supporting_weights)),
    )
    def test_quantile_weights_raises_unsupported_methods(self, method):
        y = [1, 2]
        w = [0.5, 1]
        msg = "Only method 'inverted_cdf' supports weights"
        with pytest.raises(ValueError, match=msg):
            np.quantile(y, 0.5, weights=w, method=method)

    def test_weibull_fraction(self):
        arr = [Fraction(0, 1), Fraction(1, 10)]
        quantile = np.quantile(arr, [0, ], method='weibull')
        assert_equal(quantile, np.array(Fraction(0, 1)))
        quantile = np.quantile(arr, [Fraction(1, 2)], method='weibull')
        assert_equal(quantile, np.array(Fraction(1, 20)))

    def test_closest_observation(self):
        # Round ties to nearest even order statistic (see #26656)
        m = 'closest_observation'
        q = 0.5
        arr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        assert_equal(2, np.quantile(arr[0:3], q, method=m))
        assert_equal(2, np.quantile(arr[0:4], q, method=m))
        assert_equal(2, np.quantile(arr[0:5], q, method=m))
        assert_equal(3, np.quantile(arr[0:6], q, method=m))
        assert_equal(4, np.quantile(arr[0:7], q, method=m))
        assert_equal(4, np.quantile(arr[0:8], q, method=m))
        assert_equal(4, np.quantile(arr[0:9], q, method=m))
        assert_equal(5, np.quantile(arr, q, method=m))


class TestLerp:
    @hypothesis.given(t0=st.floats(allow_nan=False, allow_infinity=False,
                                   min_value=0, max_value=1),
                      t1=st.floats(allow_nan=False, allow_infinity=False,
                                   min_value=0, max_value=1),
                      a=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=-1e300, max_value=1e300),
                      b=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=-1e300, max_value=1e300))
    def test_linear_interpolation_formula_monotonic(self, t0, t1, a, b):
        l0 = nfb._lerp(a, b, t0)
        l1 = nfb._lerp(a, b, t1)
        if t0 == t1 or a == b:
            assert l0 == l1  # uninteresting
        elif (t0 < t1) == (a < b):
            assert l0 <= l1
        else:
            assert l0 >= l1

    @hypothesis.given(t=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=0, max_value=1),
                      a=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=-1e300, max_value=1e300),
                      b=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=-1e300, max_value=1e300))
    def test_linear_interpolation_formula_bounded(self, t, a, b):
        if a <= b:
            assert a <= nfb._lerp(a, b, t) <= b
        else:
            assert b <= nfb._lerp(a, b, t) <= a

    @hypothesis.given(t=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=0, max_value=1),
                      a=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=-1e300, max_value=1e300),
                      b=st.floats(allow_nan=False, allow_infinity=False,
                                  min_value=-1e300, max_value=1e300))
    def test_linear_interpolation_formula_symmetric(self, t, a, b):
        # double subtraction is needed to remove the extra precision of t < 0.5
        left = nfb._lerp(a, b, 1 - (1 - t))
        right = nfb._lerp(b, a, 1 - t)
        assert_allclose(left, right)

    def test_linear_interpolation_formula_0d_inputs(self):
        a = np.array(2)
        b = np.array(5)
        t = np.array(0.2)
        assert nfb._lerp(a, b, t) == 2.6


class TestMedian:

    def test_basic(self):
        a0 = np.array(1)
        a1 = np.arange(2)
        a2 = np.arange(6).reshape(2, 3)
        assert_equal(np.median(a0), 1)
        assert_allclose(np.median(a1), 0.5)
        assert_allclose(np.median(a2), 2.5)
        assert_allclose(np.median(a2, axis=0), [1.5, 2.5, 3.5])
        assert_equal(np.median(a2, axis=1), [1, 4])
        assert_allclose(np.median(a2, axis=None), 2.5)

        a = np.array([0.0444502, 0.0463301, 0.141249, 0.0606775])
        assert_almost_equal((a[1] + a[3]) / 2., np.median(a))
        a = np.array([0.0463301, 0.0444502, 0.141249])
        assert_equal(a[0], np.median(a))
        a = np.array([0.0444502, 0.141249, 0.0463301])
        assert_equal(a[-1], np.median(a))
        # check array scalar result
        assert_equal(np.median(a).ndim, 0)
        a[1] = np.nan
        assert_equal(np.median(a).ndim, 0)

    def test_axis_keyword(self):
        a3 = np.array([[2, 3],
                       [0, 1],
                       [6, 7],
                       [4, 5]])
        for a in [a3, np.random.randint(0, 100, size=(2, 3, 4))]:
            orig = a.copy()
            np.median(a, axis=None)
            for ax in range(a.ndim):
                np.median(a, axis=ax)
            assert_array_equal(a, orig)

        assert_allclose(np.median(a3, axis=0), [3, 4])
        assert_allclose(np.median(a3.T, axis=1), [3, 4])
        assert_allclose(np.median(a3), 3.5)
        assert_allclose(np.median(a3, axis=None), 3.5)
        assert_allclose(np.median(a3.T), 3.5)

    def test_overwrite_keyword(self):
        a3 = np.array([[2, 3],
                       [0, 1],
                       [6, 7],
                       [4, 5]])
        a0 = np.array(1)
        a1 = np.arange(2)
        a2 = np.arange(6).reshape(2, 3)
        assert_allclose(np.median(a0.copy(), overwrite_input=True), 1)
        assert_allclose(np.median(a1.copy(), overwrite_input=True), 0.5)
        assert_allclose(np.median(a2.copy(), overwrite_input=True), 2.5)
        assert_allclose(
            np.median(a2.copy(), overwrite_input=True, axis=0), [1.5, 2.5, 3.5])
        assert_allclose(
            np.median(a2.copy(), overwrite_input=True, axis=1), [1, 4])
        assert_allclose(
            np.median(a2.copy(), overwrite_input=True, axis=None), 2.5)
        assert_allclose(
            np.median(a3.copy(), overwrite_input=True, axis=0), [3, 4])
        assert_allclose(
            np.median(a3.T.copy(), overwrite_input=True, axis=1), [3, 4])

        a4 = np.arange(3 * 4 * 5, dtype=np.float32).reshape((3, 4, 5))
        np.random.shuffle(a4.ravel())
        assert_allclose(np.median(a4, axis=None),
                        np.median(a4.copy(), axis=None, overwrite_input=True))
        assert_allclose(np.median(a4, axis=0),
                        np.median(a4.copy(), axis=0, overwrite_input=True))
        assert_allclose(np.median(a4, axis=1),
                        np.median(a4.copy(), axis=1, overwrite_input=True))
        assert_allclose(np.median(a4, axis=2),
                        np.median(a4.copy(), axis=2, overwrite_input=True))

    def test_array_like(self):
        x = [1, 2, 3]
        assert_almost_equal(np.median(x), 2)
        x2 = [x]
        assert_almost_equal(np.median(x2), 2)
        assert_allclose(np.median(x2, axis=0), x)

    def test_subclass(self):
        # gh-3846
        class MySubClass(np.ndarray):

            def __new__(cls, input_array, info=None):
                obj = np.asarray(input_array).view(cls)
                obj.info = info
                return obj

            def mean(self, axis=None, dtype=None, out=None):
                return -7

        a = MySubClass([1, 2, 3])
        assert_equal(np.median(a), -7)

    @pytest.mark.parametrize('arr',
                             ([1., 2., 3.], [1., np.nan, 3.], np.nan, 0.))
    def test_subclass2(self, arr):
        """Check that we return subclasses, even if a NaN scalar."""
        class MySubclass(np.ndarray):
            pass

        m = np.median(np.array(arr).view(MySubclass))
        assert isinstance(m, MySubclass)

    def test_out(self):
        o = np.zeros((4,))
        d = np.ones((3, 4))
        assert_equal(np.median(d, 0, out=o), o)
        o = np.zeros((3,))
        assert_equal(np.median(d, 1, out=o), o)
        o = np.zeros(())
        assert_equal(np.median(d, out=o), o)

    def test_out_nan(self):
        with warnings.catch_warnings(record=True):
            warnings.filterwarnings('always', '', RuntimeWarning)
            o = np.zeros((4,))
            d = np.ones((3, 4))
            d[2, 1] = np.nan
            assert_equal(np.median(d, 0, out=o), o)
            o = np.zeros((3,))
            assert_equal(np.median(d, 1, out=o), o)
            o = np.zeros(())
            assert_equal(np.median(d, out=o), o)

    def test_nan_behavior(self):
        a = np.arange(24, dtype=float)
        a[2] = np.nan
        assert_equal(np.median(a), np.nan)
        assert_equal(np.median(a, axis=0), np.nan)

        a = np.arange(24, dtype=float).reshape(2, 3, 4)
        a[1, 2, 3] = np.nan
        a[1, 1, 2] = np.nan

        # no axis
        assert_equal(np.median(a), np.nan)
        assert_equal(np.median(a).ndim, 0)

        # axis0
        b = np.median(np.arange(24, dtype=float).reshape(2, 3, 4), 0)
        b[2, 3] = np.nan
        b[1, 2] = np.nan
        assert_equal(np.median(a, 0), b)

        # axis1
        b = np.median(np.arange(24, dtype=float).reshape(2, 3, 4), 1)
        b[1, 3] = np.nan
        b[1, 2] = np.nan
        assert_equal(np.median(a, 1), b)

        # axis02
        b = np.median(np.arange(24, dtype=float).reshape(2, 3, 4), (0, 2))
        b[1] = np.nan
        b[2] = np.nan
        assert_equal(np.median(a, (0, 2)), b)

    @pytest.mark.skipif(IS_WASM, reason="fp errors don't work correctly")
    def test_empty(self):
        # mean(empty array) emits two warnings: empty slice and divide by 0
        a = np.array([], dtype=float)
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', RuntimeWarning)
            assert_equal(np.median(a), np.nan)
            assert_(w[0].category is RuntimeWarning)
            assert_equal(len(w), 2)

        # multiple dimensions
        a = np.array([], dtype=float, ndmin=3)
        # no axis
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', RuntimeWarning)
            assert_equal(np.median(a), np.nan)
            assert_(w[0].category is RuntimeWarning)

        # axis 0 and 1
        b = np.array([], dtype=float, ndmin=2)
        assert_equal(np.median(a, axis=0), b)
        assert_equal(np.median(a, axis=1), b)

        # axis 2
        b = np.array(np.nan, dtype=float, ndmin=2)
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', RuntimeWarning)
            assert_equal(np.median(a, axis=2), b)
            assert_(w[0].category is RuntimeWarning)

    def test_object(self):
        o = np.arange(7.)
        assert_(type(np.median(o.astype(object))), float)
        o[2] = np.nan
        assert_(type(np.median(o.astype(object))), float)

    def test_extended_axis(self):
        o = np.random.normal(size=(71, 23))
        x = np.dstack([o] * 10)
        assert_equal(np.median(x, axis=(0, 1)), np.median(o))
        x = np.moveaxis(x, -1, 0)
        assert_equal(np.median(x, axis=(-2, -1)), np.median(o))
        x = x.swapaxes(0, 1).copy()
        assert_equal(np.median(x, axis=(0, -1)), np.median(o))

        assert_equal(np.median(x, axis=(0, 1, 2)), np.median(x, axis=None))
        assert_equal(np.median(x, axis=(0, )), np.median(x, axis=0))
        assert_equal(np.median(x, axis=(-1, )), np.median(x, axis=-1))

        d = np.arange(3 * 5 * 7 * 11).reshape((3, 5, 7, 11))
        np.random.shuffle(d.ravel())
        assert_equal(np.median(d, axis=(0, 1, 2))[0],
                     np.median(d[:, :, :, 0].flatten()))
        assert_equal(np.median(d, axis=(0, 1, 3))[1],
                     np.median(d[:, :, 1, :].flatten()))
        assert_equal(np.median(d, axis=(3, 1, -4))[2],
                     np.median(d[:, :, 2, :].flatten()))
        assert_equal(np.median(d, axis=(3, 1, 2))[2],
                     np.median(d[2, :, :, :].flatten()))
        assert_equal(np.median(d, axis=(3, 2))[2, 1],
                     np.median(d[2, 1, :, :].flatten()))
        assert_equal(np.median(d, axis=(1, -2))[2, 1],
                     np.median(d[2, :, :, 1].flatten()))
        assert_equal(np.median(d, axis=(1, 3))[2, 2],
                     np.median(d[2, :, 2, :].flatten()))

    def test_extended_axis_invalid(self):
        d = np.ones((3, 5, 7, 11))
        assert_raises(AxisError, np.median, d, axis=-5)
        assert_raises(AxisError, np.median, d, axis=(0, -5))
        assert_raises(AxisError, np.median, d, axis=4)
        assert_raises(AxisError, np.median, d, axis=(0, 4))
        assert_raises(ValueError, np.median, d, axis=(1, 1))

    def test_keepdims(self):
        d = np.ones((3, 5, 7, 11))
        assert_equal(np.median(d, axis=None, keepdims=True).shape,
                     (1, 1, 1, 1))
        assert_equal(np.median(d, axis=(0, 1), keepdims=True).shape,
                     (1, 1, 7, 11))
        assert_equal(np.median(d, axis=(0, 3), keepdims=True).shape,
                     (1, 5, 7, 1))
        assert_equal(np.median(d, axis=(1,), keepdims=True).shape,
                     (3, 1, 7, 11))
        assert_equal(np.median(d, axis=(0, 1, 2, 3), keepdims=True).shape,
                     (1, 1, 1, 1))
        assert_equal(np.median(d, axis=(0, 1, 3), keepdims=True).shape,
                     (1, 1, 7, 1))

    @pytest.mark.parametrize(
        argnames='axis',
        argvalues=[
            None,
            1,
            (1, ),
            (0, 1),
            (-3, -1),
        ]
    )
    def test_keepdims_out(self, axis):
        d = np.ones((3, 5, 7, 11))
        if axis is None:
            shape_out = (1,) * d.ndim
        else:
            axis_norm = normalize_axis_tuple(axis, d.ndim)
            shape_out = tuple(
                1 if i in axis_norm else d.shape[i] for i in range(d.ndim))
        out = np.empty(shape_out)
        result = np.median(d, axis=axis, keepdims=True, out=out)
        assert result is out
        assert_equal(result.shape, shape_out)

    @pytest.mark.parametrize("dtype", ["m8[s]"])
    @pytest.mark.parametrize("pos", [0, 23, 10])
    def test_nat_behavior(self, dtype, pos):
        # TODO: Median does not support Datetime, due to `mean`.
        # NaT and NaN should behave the same, do basic tests for NaT.
        a = np.arange(0, 24, dtype=dtype)
        a[pos] = "NaT"
        res = np.median(a)
        assert res.dtype == dtype
        assert np.isnat(res)
        res = np.percentile(a, [30, 60])
        assert res.dtype == dtype
        assert np.isnat(res).all()

        a = np.arange(0, 24 * 3, dtype=dtype).reshape(-1, 3)
        a[pos, 1] = "NaT"
        res = np.median(a, axis=0)
        assert_array_equal(np.isnat(res), [False, True, False])


class TestSortComplex:

    @pytest.mark.parametrize("type_in, type_out", [
        ('l', 'D'),
        ('h', 'F'),
        ('H', 'F'),
        ('b', 'F'),
        ('B', 'F'),
        ('g', 'G'),
        ])
    def test_sort_real(self, type_in, type_out):
        # sort_complex() type casting for real input types
        a = np.array([5, 3, 6, 2, 1], dtype=type_in)
        actual = np.sort_complex(a)
        expected = np.sort(a).astype(type_out)
        assert_equal(actual, expected)
        assert_equal(actual.dtype, expected.dtype)

    def test_sort_complex(self):
        # sort_complex() handling of complex input
        a = np.array([2 + 3j, 1 - 2j, 1 - 3j, 2 + 1j], dtype='D')
        expected = np.array([1 - 3j, 1 - 2j, 2 + 1j, 2 + 3j], dtype='D')
        actual = np.sort_complex(a)
        assert_equal(actual, expected)
        assert_equal(actual.dtype, expected.dtype)

# === NexusCore/app\routes.py ===
# app/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, Response
from app import db
from app.models import Product                      # ← models.py で定義した ORM クラス[1]
from app.forms  import ProductForm                  # ← WTForms フォーム
import csv, io
from datetime import datetime

bp = Blueprint('main', __name__)                    # ① Blueprint 宣言

# --------------------------------------------------
# ② 一覧＋新規登録
# --------------------------------------------------
@bp.route('/products', methods=['GET', 'POST'])
def manage_products():
    form = ProductForm()
    if form.validate_on_submit():                   # 追加ボタンが押されたとき
        product = Product(
            name= form.name.data,
            brand=form.brand.data,
            purchase_price=form.purchase_price.data,
            selling_price =form.selling_price.data,
            supplier_url  =form.supplier_url.data,
            image_url     =form.image_url.data,
            stock_status  =form.stock_status.data,
            transaction_fee=form.transaction_fee.data,
            shipping_cost   =form.shipping_cost.data,
            customs_duty    =form.customs_duty.data,
            procurement_fee =form.procurement_fee.data,
        )
        # 利益をその場で計算して保存
        product.profit = product.calculate_profit()      # [1]
        db.session.add(product)
        db.session.commit()
        flash('商品を登録しました', 'success')
        return redirect(url_for('main.manage_products'))

    products = Product.query.all()
    return render_template('products/manage.html',
                           form=form, products=products)

# --------------------------------------------------
# ③ CSV 取込
# --------------------------------------------------
@bp.route('/products/import', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        flash('CSV ファイルがありません', 'error')
        return redirect(url_for('main.manage_products'))

    f = request.files['file']
    if not f.filename.endswith('.csv'):
        flash('CSV だけアップロードできます', 'error')
        return redirect(url_for('main.manage_products'))

    stream  = io.StringIO(f.stream.read().decode('utf-8-sig'))
    reader  = csv.DictReader(stream)
    created = 0
    for row in reader:
        # 必須カラムチェック
        if not all(k in row for k in ('name', 'purchaseprice', 'sellingprice')):
            flash('必須列が不足しています', 'error')
            return redirect(url_for('main.manage_products'))

        p = Product(
            name = row['name'],
            brand= row.get('brand', ''),
            purchase_price=float(row['purchaseprice']),
            selling_price =float(row['sellingprice']),
            supplier_url  =row.get('supplierurl', ''),
            image_url     =row.get('imageurl', ''),
            stock_status  =row.get('stockstatus', 'true').lower() in ('true','1','yes'),
            transaction_fee=float(row.get('transactionfee',0)),
            shipping_cost   =float(row.get('shippingcost',0)),
            customs_duty    =float(row.get('customsduty',0)),
            procurement_fee =float(row.get('procurementfee',0)),
        )
        p.profit = p.calculate_profit()                 # [1]
        db.session.add(p)
        created += 1
    db.session.commit()
    flash(f'{created} 件取り込みました', 'success')
    return redirect(url_for('main.manage_products'))

# --------------------------------------------------
# ③ CSV 書出し
# --------------------------------------------------
@bp.route('/products/export')
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'name','brand','purchaseprice','sellingprice',
        'transactionfee','shippingcost','customsduty','procurementfee',
        'supplierurl','imageurl','stockstatus'
    ])
    for p in Product.query.all():
        writer.writerow([
            p.name, p.brand, p.purchase_price, p.selling_price,
            p.transaction_fee, p.shipping_cost, p.customs_duty, p.procurement_fee,
            p.supplier_url, p.image_url, 'true' if p.stock_status else 'false'
        ])
    output.seek(0)
    data = '\ufeff' + output.getvalue()                  # UTF-8 BOM 付き[1]
    dt   = datetime.now().strftime('%Y%m%d%H%M%S')
    return Response(
        data, mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=products_{dt}.csv'}
    )

# --------------------------------------------------
# ④ 編集・削除
# --------------------------------------------------
@bp.route('/products/<int:pid>/edit', methods=['GET','POST'])
def edit_product(pid):
    product = Product.query.get_or_404(pid)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        product.profit = product.calculate_profit()
        db.session.commit()
        flash('更新しました', 'success')
        return redirect(url_for('main.manage_products'))
    return render_template('products/edit.html', form=form, product=product)

@bp.route('/products/<int:pid>/delete', methods=['POST'])
def delete_product(pid):
    product = Product.query.get_or_404(pid)
    db.session.delete(product)
    db.session.commit()
    flash('削除しました', 'success')
    return redirect(url_for('main.manage_products'))

# --------------------------------------------------
# ⑤ ルートリダイレクト
# --------------------------------------------------
@bp.route('/')
def index():
    return redirect(url_for('main.manage_products'))

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\app\routes.py ===
# app/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, Response
from app import db
from app.models import Product                      # ← models.py で定義した ORM クラス[1]
from app.forms  import ProductForm                  # ← WTForms フォーム
import csv, io
from datetime import datetime

bp = Blueprint('main', __name__)                    # ① Blueprint 宣言

# --------------------------------------------------
# ② 一覧＋新規登録
# --------------------------------------------------
@bp.route('/products', methods=['GET', 'POST'])
def manage_products():
    form = ProductForm()
    if form.validate_on_submit():                   # 追加ボタンが押されたとき
        product = Product(
            name= form.name.data,
            brand=form.brand.data,
            purchase_price=form.purchase_price.data,
            selling_price =form.selling_price.data,
            supplier_url  =form.supplier_url.data,
            image_url     =form.image_url.data,
            stock_status  =form.stock_status.data,
            transaction_fee=form.transaction_fee.data,
            shipping_cost   =form.shipping_cost.data,
            customs_duty    =form.customs_duty.data,
            procurement_fee =form.procurement_fee.data,
        )
        # 利益をその場で計算して保存
        product.profit = product.calculate_profit()      # [1]
        db.session.add(product)
        db.session.commit()
        flash('商品を登録しました', 'success')
        return redirect(url_for('main.manage_products'))

    products = Product.query.all()
    return render_template('products/manage.html',
                           form=form, products=products)

# --------------------------------------------------
# ③ CSV 取込
# --------------------------------------------------
@bp.route('/products/import', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        flash('CSV ファイルがありません', 'error')
        return redirect(url_for('main.manage_products'))

    f = request.files['file']
    if not f.filename.endswith('.csv'):
        flash('CSV だけアップロードできます', 'error')
        return redirect(url_for('main.manage_products'))

    stream  = io.StringIO(f.stream.read().decode('utf-8-sig'))
    reader  = csv.DictReader(stream)
    created = 0
    for row in reader:
        # 必須カラムチェック
        if not all(k in row for k in ('name', 'purchaseprice', 'sellingprice')):
            flash('必須列が不足しています', 'error')
            return redirect(url_for('main.manage_products'))

        p = Product(
            name = row['name'],
            brand= row.get('brand', ''),
            purchase_price=float(row['purchaseprice']),
            selling_price =float(row['sellingprice']),
            supplier_url  =row.get('supplierurl', ''),
            image_url     =row.get('imageurl', ''),
            stock_status  =row.get('stockstatus', 'true').lower() in ('true','1','yes'),
            transaction_fee=float(row.get('transactionfee',0)),
            shipping_cost   =float(row.get('shippingcost',0)),
            customs_duty    =float(row.get('customsduty',0)),
            procurement_fee =float(row.get('procurementfee',0)),
        )
        p.profit = p.calculate_profit()                 # [1]
        db.session.add(p)
        created += 1
    db.session.commit()
    flash(f'{created} 件取り込みました', 'success')
    return redirect(url_for('main.manage_products'))

# --------------------------------------------------
# ③ CSV 書出し
# --------------------------------------------------
@bp.route('/products/export')
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'name','brand','purchaseprice','sellingprice',
        'transactionfee','shippingcost','customsduty','procurementfee',
        'supplierurl','imageurl','stockstatus'
    ])
    for p in Product.query.all():
        writer.writerow([
            p.name, p.brand, p.purchase_price, p.selling_price,
            p.transaction_fee, p.shipping_cost, p.customs_duty, p.procurement_fee,
            p.supplier_url, p.image_url, 'true' if p.stock_status else 'false'
        ])
    output.seek(0)
    data = '\ufeff' + output.getvalue()                  # UTF-8 BOM 付き[1]
    dt   = datetime.now().strftime('%Y%m%d%H%M%S')
    return Response(
        data, mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=products_{dt}.csv'}
    )

# --------------------------------------------------
# ④ 編集・削除
# --------------------------------------------------
@bp.route('/products/<int:pid>/edit', methods=['GET','POST'])
def edit_product(pid):
    product = Product.query.get_or_404(pid)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        product.profit = product.calculate_profit()
        db.session.commit()
        flash('更新しました', 'success')
        return redirect(url_for('main.manage_products'))
    return render_template('products/edit.html', form=form, product=product)

@bp.route('/products/<int:pid>/delete', methods=['POST'])
def delete_product(pid):
    product = Product.query.get_or_404(pid)
    db.session.delete(product)
    db.session.commit()
    flash('削除しました', 'success')
    return redirect(url_for('main.manage_products'))

# --------------------------------------------------
# ⑤ ルートリダイレクト
# --------------------------------------------------
@bp.route('/')
def index():
    return redirect(url_for('main.manage_products'))

# === NexusCore/exported_projects\app_20250703_223016\app\utils\generate_descriptions.py ===
import os
import requests
import csv
import time
import random
from dotenv import load_dotenv
from datetime import datetime

# 環境変数の読み込み
load_dotenv()

class BUYMADescriptionGenerator:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.endpoint = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BUYMA-Auto-Desc/3.0"
        }
        self.model = "sonar-pro"  # 最新有効モデル名

    def _create_log(self, message, log_type="error"):
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{log_type}_{timestamp}.log"
        with open(os.path.join(log_dir, filename), "w", encoding="utf-8") as f:
            f.write(message)

    def _call_api(self, payload):
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e.response.status_code}\n{e.response.text}"
            self._create_log(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request Failed: {str(e)}"
            self._create_log(error_msg)
        except Exception as e:
            error_msg = f"Unexpected Error: {str(e)}"
            self._create_log(error_msg)
        return None

    def generate_description(self, product_info):
        prompt = f"""
        あなたはBUYMA専門のプロコピーライターです。
        以下の条件で商品説明文を日本語で作成してください。

        [要件]
        1. 300-500文字
        2. ブランド名とカテゴリを自然に配置
        3. 商品の特徴を3点箇条書き
        4. 感情に訴える表現（例: 「上質なレザーの風合い」）
        5. 急かし表現や「今すぐ」などの強い勧誘は避ける
        6. 重複表現を避け、情報を簡潔に整理
        7. 生活シーンや使用イメージを盛り込む
        8. 読み手に自然に提案する口調で仕上げる

        [商品情報]
        ブランド: {product_info.get('brand', '')}
        商品名: {product_info.get('name', '')}
        カテゴリ: {product_info.get('category', '')}
        特徴: {product_info.get('features', '')}
        素材: {product_info.get('materials', '')}
        サイズ: {product_info.get('size', '')}
        カラー: {product_info.get('color', '')}
        対象層: {product_info.get('target', '')}
        価格帯: {product_info.get('price_range', '')}
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "あなたは高級ファッション専門のコピーライターです。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        result = self._call_api(payload)
        return result['choices'][0]['message']['content'].strip() if result else None

    def batch_process(self, products, retry=3):
        results = []
        for idx, product in enumerate(products):
            attempt = 0
            while attempt < retry:
                try:
                    print(f"処理中 ({idx+1}/{len(products)})")
                    desc = self.generate_description(product)
                    if desc:
                        results.append({**product, "description": desc})
                        break
                    else:
                        attempt += 1
                        time.sleep(2 ** attempt)
                except Exception as e:
                    print(f"エラー: {str(e)}")
                    attempt += 1
            time.sleep(random.uniform(1, 3))
        return results

if __name__ == "__main__":
    generator = BUYMADescriptionGenerator()
    sample_products = [
        {
            "brand": "PRADA",
            "name": "シンフォニー トートバッグ",
            "category": "トートバッグ",
            "features": "軽量ナイロン素材、大容量収納",
            "materials": "ナイロン",
            "size": "W35cm x H25cm x D15cm",
            "color": "ブラック",
            "target": "20-30代女性",
            "price_range": "15-20万円"
        }
    ]
    processed_data = generator.batch_process(sample_products)
    if processed_data:
        output_path = os.path.join(os.path.dirname(__file__), 'output.csv')
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=processed_data[0].keys())
            writer.writeheader()
            writer.writerows(processed_data)
        print(f"CSVファイルを正常に出力しました: {output_path}")
    else:
        print("処理に失敗しました。ログを確認してください。")

# === NexusCore/exported_projects\project_export_m73owrzi\app\utils\generate_descriptions.py ===
import os
import requests
import csv
import time
import random
from dotenv import load_dotenv
from datetime import datetime

# 環境変数の読み込み
load_dotenv()

class BUYMADescriptionGenerator:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.endpoint = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BUYMA-Auto-Desc/3.0"
        }
        self.model = "sonar-pro"  # 最新有効モデル名

    def _create_log(self, message, log_type="error"):
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{log_type}_{timestamp}.log"
        with open(os.path.join(log_dir, filename), "w", encoding="utf-8") as f:
            f.write(message)

    def _call_api(self, payload):
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e.response.status_code}\n{e.response.text}"
            self._create_log(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request Failed: {str(e)}"
            self._create_log(error_msg)
        except Exception as e:
            error_msg = f"Unexpected Error: {str(e)}"
            self._create_log(error_msg)
        return None

    def generate_description(self, product_info):
        prompt = f"""
        あなたはBUYMA専門のプロコピーライターです。
        以下の条件で商品説明文を日本語で作成してください。

        [要件]
        1. 300-500文字
        2. ブランド名とカテゴリを自然に配置
        3. 商品の特徴を3点箇条書き
        4. 感情に訴える表現（例: 「上質なレザーの風合い」）
        5. 急かし表現や「今すぐ」などの強い勧誘は避ける
        6. 重複表現を避け、情報を簡潔に整理
        7. 生活シーンや使用イメージを盛り込む
        8. 読み手に自然に提案する口調で仕上げる

        [商品情報]
        ブランド: {product_info.get('brand', '')}
        商品名: {product_info.get('name', '')}
        カテゴリ: {product_info.get('category', '')}
        特徴: {product_info.get('features', '')}
        素材: {product_info.get('materials', '')}
        サイズ: {product_info.get('size', '')}
        カラー: {product_info.get('color', '')}
        対象層: {product_info.get('target', '')}
        価格帯: {product_info.get('price_range', '')}
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "あなたは高級ファッション専門のコピーライターです。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        result = self._call_api(payload)
        return result['choices'][0]['message']['content'].strip() if result else None

    def batch_process(self, products, retry=3):
        results = []
        for idx, product in enumerate(products):
            attempt = 0
            while attempt < retry:
                try:
                    print(f"処理中 ({idx+1}/{len(products)})")
                    desc = self.generate_description(product)
                    if desc:
                        results.append({**product, "description": desc})
                        break
                    else:
                        attempt += 1
                        time.sleep(2 ** attempt)
                except Exception as e:
                    print(f"エラー: {str(e)}")
                    attempt += 1
            time.sleep(random.uniform(1, 3))
        return results

if __name__ == "__main__":
    generator = BUYMADescriptionGenerator()
    sample_products = [
        {
            "brand": "PRADA",
            "name": "シンフォニー トートバッグ",
            "category": "トートバッグ",
            "features": "軽量ナイロン素材、大容量収納",
            "materials": "ナイロン",
            "size": "W35cm x H25cm x D15cm",
            "color": "ブラック",
            "target": "20-30代女性",
            "price_range": "15-20万円"
        }
    ]
    processed_data = generator.batch_process(sample_products)
    if processed_data:
        output_path = os.path.join(os.path.dirname(__file__), 'output.csv')
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=processed_data[0].keys())
            writer.writeheader()
            writer.writerows(processed_data)
        print(f"CSVファイルを正常に出力しました: {output_path}")
    else:
        print("処理に失敗しました。ログを確認してください。")

# === NexusCore/exported_projects\project_export_xb_l70t8\app\utils\generate_descriptions.py ===
import os
import requests
import csv
import time
import random
from dotenv import load_dotenv
from datetime import datetime

# 環境変数の読み込み
load_dotenv()

class BUYMADescriptionGenerator:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.endpoint = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BUYMA-Auto-Desc/3.0"
        }
        self.model = "sonar-pro"  # 最新有効モデル名

    def _create_log(self, message, log_type="error"):
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{log_type}_{timestamp}.log"
        with open(os.path.join(log_dir, filename), "w", encoding="utf-8") as f:
            f.write(message)

    def _call_api(self, payload):
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e.response.status_code}\n{e.response.text}"
            self._create_log(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request Failed: {str(e)}"
            self._create_log(error_msg)
        except Exception as e:
            error_msg = f"Unexpected Error: {str(e)}"
            self._create_log(error_msg)
        return None

    def generate_description(self, product_info):
        prompt = f"""
        あなたはBUYMA専門のプロコピーライターです。
        以下の条件で商品説明文を日本語で作成してください。

        [要件]
        1. 300-500文字
        2. ブランド名とカテゴリを自然に配置
        3. 商品の特徴を3点箇条書き
        4. 感情に訴える表現（例: 「上質なレザーの風合い」）
        5. 急かし表現や「今すぐ」などの強い勧誘は避ける
        6. 重複表現を避け、情報を簡潔に整理
        7. 生活シーンや使用イメージを盛り込む
        8. 読み手に自然に提案する口調で仕上げる

        [商品情報]
        ブランド: {product_info.get('brand', '')}
        商品名: {product_info.get('name', '')}
        カテゴリ: {product_info.get('category', '')}
        特徴: {product_info.get('features', '')}
        素材: {product_info.get('materials', '')}
        サイズ: {product_info.get('size', '')}
        カラー: {product_info.get('color', '')}
        対象層: {product_info.get('target', '')}
        価格帯: {product_info.get('price_range', '')}
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "あなたは高級ファッション専門のコピーライターです。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        result = self._call_api(payload)
        return result['choices'][0]['message']['content'].strip() if result else None

    def batch_process(self, products, retry=3):
        results = []
        for idx, product in enumerate(products):
            attempt = 0
            while attempt < retry:
                try:
                    print(f"処理中 ({idx+1}/{len(products)})")
                    desc = self.generate_description(product)
                    if desc:
                        results.append({**product, "description": desc})
                        break
                    else:
                        attempt += 1
                        time.sleep(2 ** attempt)
                except Exception as e:
                    print(f"エラー: {str(e)}")
                    attempt += 1
            time.sleep(random.uniform(1, 3))
        return results

if __name__ == "__main__":
    generator = BUYMADescriptionGenerator()
    sample_products = [
        {
            "brand": "PRADA",
            "name": "シンフォニー トートバッグ",
            "category": "トートバッグ",
            "features": "軽量ナイロン素材、大容量収納",
            "materials": "ナイロン",
            "size": "W35cm x H25cm x D15cm",
            "color": "ブラック",
            "target": "20-30代女性",
            "price_range": "15-20万円"
        }
    ]
    processed_data = generator.batch_process(sample_products)
    if processed_data:
        output_path = os.path.join(os.path.dirname(__file__), 'output.csv')
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=processed_data[0].keys())
            writer.writeheader()
            writer.writerows(processed_data)
        print(f"CSVファイルを正常に出力しました: {output_path}")
    else:
        print("処理に失敗しました。ログを確認してください。")

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\utils\generate_descriptions.py ===
import os
import requests
import csv
import time
import random
from dotenv import load_dotenv
from datetime import datetime

# 環境変数の読み込み
load_dotenv()

class BUYMADescriptionGenerator:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.endpoint = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BUYMA-Auto-Desc/3.0"
        }
        self.model = "sonar-pro"  # 最新有効モデル名

    def _create_log(self, message, log_type="error"):
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{log_type}_{timestamp}.log"
        with open(os.path.join(log_dir, filename), "w", encoding="utf-8") as f:
            f.write(message)

    def _call_api(self, payload):
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e.response.status_code}\n{e.response.text}"
            self._create_log(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request Failed: {str(e)}"
            self._create_log(error_msg)
        except Exception as e:
            error_msg = f"Unexpected Error: {str(e)}"
            self._create_log(error_msg)
        return None

    def generate_description(self, product_info):
        prompt = f"""
        あなたはBUYMA専門のプロコピーライターです。
        以下の条件で商品説明文を日本語で作成してください。

        [要件]
        1. 300-500文字
        2. ブランド名とカテゴリを自然に配置
        3. 商品の特徴を3点箇条書き
        4. 感情に訴える表現（例: 「上質なレザーの風合い」）
        5. 急かし表現や「今すぐ」などの強い勧誘は避ける
        6. 重複表現を避け、情報を簡潔に整理
        7. 生活シーンや使用イメージを盛り込む
        8. 読み手に自然に提案する口調で仕上げる

        [商品情報]
        ブランド: {product_info.get('brand', '')}
        商品名: {product_info.get('name', '')}
        カテゴリ: {product_info.get('category', '')}
        特徴: {product_info.get('features', '')}
        素材: {product_info.get('materials', '')}
        サイズ: {product_info.get('size', '')}
        カラー: {product_info.get('color', '')}
        対象層: {product_info.get('target', '')}
        価格帯: {product_info.get('price_range', '')}
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "あなたは高級ファッション専門のコピーライターです。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        result = self._call_api(payload)
        return result['choices'][0]['message']['content'].strip() if result else None

    def batch_process(self, products, retry=3):
        results = []
        for idx, product in enumerate(products):
            attempt = 0
            while attempt < retry:
                try:
                    print(f"処理中 ({idx+1}/{len(products)})")
                    desc = self.generate_description(product)
                    if desc:
                        results.append({**product, "description": desc})
                        break
                    else:
                        attempt += 1
                        time.sleep(2 ** attempt)
                except Exception as e:
                    print(f"エラー: {str(e)}")
                    attempt += 1
            time.sleep(random.uniform(1, 3))
        return results

if __name__ == "__main__":
    generator = BUYMADescriptionGenerator()
    sample_products = [
        {
            "brand": "PRADA",
            "name": "シンフォニー トートバッグ",
            "category": "トートバッグ",
            "features": "軽量ナイロン素材、大容量収納",
            "materials": "ナイロン",
            "size": "W35cm x H25cm x D15cm",
            "color": "ブラック",
            "target": "20-30代女性",
            "price_range": "15-20万円"
        }
    ]
    processed_data = generator.batch_process(sample_products)
    if processed_data:
        output_path = os.path.join(os.path.dirname(__file__), 'output.csv')
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=processed_data[0].keys())
            writer.writeheader()
            writer.writerows(processed_data)
        print(f"CSVファイルを正常に出力しました: {output_path}")
    else:
        print("処理に失敗しました。ログを確認してください。")

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\app_20250703_223016\app\utils\generate_descriptions.py ===
import os
import requests
import csv
import time
import random
from dotenv import load_dotenv
from datetime import datetime

# 環境変数の読み込み
load_dotenv()

class BUYMADescriptionGenerator:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.endpoint = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BUYMA-Auto-Desc/3.0"
        }
        self.model = "sonar-pro"  # 最新有効モデル名

    def _create_log(self, message, log_type="error"):
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{log_type}_{timestamp}.log"
        with open(os.path.join(log_dir, filename), "w", encoding="utf-8") as f:
            f.write(message)

    def _call_api(self, payload):
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e.response.status_code}\n{e.response.text}"
            self._create_log(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request Failed: {str(e)}"
            self._create_log(error_msg)
        except Exception as e:
            error_msg = f"Unexpected Error: {str(e)}"
            self._create_log(error_msg)
        return None

    def generate_description(self, product_info):
        prompt = f"""
        あなたはBUYMA専門のプロコピーライターです。
        以下の条件で商品説明文を日本語で作成してください。

        [要件]
        1. 300-500文字
        2. ブランド名とカテゴリを自然に配置
        3. 商品の特徴を3点箇条書き
        4. 感情に訴える表現（例: 「上質なレザーの風合い」）
        5. 急かし表現や「今すぐ」などの強い勧誘は避ける
        6. 重複表現を避け、情報を簡潔に整理
        7. 生活シーンや使用イメージを盛り込む
        8. 読み手に自然に提案する口調で仕上げる

        [商品情報]
        ブランド: {product_info.get('brand', '')}
        商品名: {product_info.get('name', '')}
        カテゴリ: {product_info.get('category', '')}
        特徴: {product_info.get('features', '')}
        素材: {product_info.get('materials', '')}
        サイズ: {product_info.get('size', '')}
        カラー: {product_info.get('color', '')}
        対象層: {product_info.get('target', '')}
        価格帯: {product_info.get('price_range', '')}
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "あなたは高級ファッション専門のコピーライターです。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        result = self._call_api(payload)
        return result['choices'][0]['message']['content'].strip() if result else None

    def batch_process(self, products, retry=3):
        results = []
        for idx, product in enumerate(products):
            attempt = 0
            while attempt < retry:
                try:
                    print(f"処理中 ({idx+1}/{len(products)})")
                    desc = self.generate_description(product)
                    if desc:
                        results.append({**product, "description": desc})
                        break
                    else:
                        attempt += 1
                        time.sleep(2 ** attempt)
                except Exception as e:
                    print(f"エラー: {str(e)}")
                    attempt += 1
            time.sleep(random.uniform(1, 3))
        return results

if __name__ == "__main__":
    generator = BUYMADescriptionGenerator()
    sample_products = [
        {
            "brand": "PRADA",
            "name": "シンフォニー トートバッグ",
            "category": "トートバッグ",
            "features": "軽量ナイロン素材、大容量収納",
            "materials": "ナイロン",
            "size": "W35cm x H25cm x D15cm",
            "color": "ブラック",
            "target": "20-30代女性",
            "price_range": "15-20万円"
        }
    ]
    processed_data = generator.batch_process(sample_products)
    if processed_data:
        output_path = os.path.join(os.path.dirname(__file__), 'output.csv')
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=processed_data[0].keys())
            writer.writeheader()
            writer.writerows(processed_data)
        print(f"CSVファイルを正常に出力しました: {output_path}")
    else:
        print("処理に失敗しました。ログを確認してください。")

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_m73owrzi\app\utils\generate_descriptions.py ===
import os
import requests
import csv
import time
import random
from dotenv import load_dotenv
from datetime import datetime

# 環境変数の読み込み
load_dotenv()

class BUYMADescriptionGenerator:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.endpoint = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BUYMA-Auto-Desc/3.0"
        }
        self.model = "sonar-pro"  # 最新有効モデル名

    def _create_log(self, message, log_type="error"):
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{log_type}_{timestamp}.log"
        with open(os.path.join(log_dir, filename), "w", encoding="utf-8") as f:
            f.write(message)

    def _call_api(self, payload):
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e.response.status_code}\n{e.response.text}"
            self._create_log(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request Failed: {str(e)}"
            self._create_log(error_msg)
        except Exception as e:
            error_msg = f"Unexpected Error: {str(e)}"
            self._create_log(error_msg)
        return None

    def generate_description(self, product_info):
        prompt = f"""
        あなたはBUYMA専門のプロコピーライターです。
        以下の条件で商品説明文を日本語で作成してください。

        [要件]
        1. 300-500文字
        2. ブランド名とカテゴリを自然に配置
        3. 商品の特徴を3点箇条書き
        4. 感情に訴える表現（例: 「上質なレザーの風合い」）
        5. 急かし表現や「今すぐ」などの強い勧誘は避ける
        6. 重複表現を避け、情報を簡潔に整理
        7. 生活シーンや使用イメージを盛り込む
        8. 読み手に自然に提案する口調で仕上げる

        [商品情報]
        ブランド: {product_info.get('brand', '')}
        商品名: {product_info.get('name', '')}
        カテゴリ: {product_info.get('category', '')}
        特徴: {product_info.get('features', '')}
        素材: {product_info.get('materials', '')}
        サイズ: {product_info.get('size', '')}
        カラー: {product_info.get('color', '')}
        対象層: {product_info.get('target', '')}
        価格帯: {product_info.get('price_range', '')}
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "あなたは高級ファッション専門のコピーライターです。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        result = self._call_api(payload)
        return result['choices'][0]['message']['content'].strip() if result else None

    def batch_process(self, products, retry=3):
        results = []
        for idx, product in enumerate(products):
            attempt = 0
            while attempt < retry:
                try:
                    print(f"処理中 ({idx+1}/{len(products)})")
                    desc = self.generate_description(product)
                    if desc:
                        results.append({**product, "description": desc})
                        break
                    else:
                        attempt += 1
                        time.sleep(2 ** attempt)
                except Exception as e:
                    print(f"エラー: {str(e)}")
                    attempt += 1
            time.sleep(random.uniform(1, 3))
        return results

if __name__ == "__main__":
    generator = BUYMADescriptionGenerator()
    sample_products = [
        {
            "brand": "PRADA",
            "name": "シンフォニー トートバッグ",
            "category": "トートバッグ",
            "features": "軽量ナイロン素材、大容量収納",
            "materials": "ナイロン",
            "size": "W35cm x H25cm x D15cm",
            "color": "ブラック",
            "target": "20-30代女性",
            "price_range": "15-20万円"
        }
    ]
    processed_data = generator.batch_process(sample_products)
    if processed_data:
        output_path = os.path.join(os.path.dirname(__file__), 'output.csv')
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=processed_data[0].keys())
            writer.writeheader()
            writer.writerows(processed_data)
        print(f"CSVファイルを正常に出力しました: {output_path}")
    else:
        print("処理に失敗しました。ログを確認してください。")

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_xb_l70t8\app\utils\generate_descriptions.py ===
import os
import requests
import csv
import time
import random
from dotenv import load_dotenv
from datetime import datetime

# 環境変数の読み込み
load_dotenv()

class BUYMADescriptionGenerator:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.endpoint = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BUYMA-Auto-Desc/3.0"
        }
        self.model = "sonar-pro"  # 最新有効モデル名

    def _create_log(self, message, log_type="error"):
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{log_type}_{timestamp}.log"
        with open(os.path.join(log_dir, filename), "w", encoding="utf-8") as f:
            f.write(message)

    def _call_api(self, payload):
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e.response.status_code}\n{e.response.text}"
            self._create_log(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request Failed: {str(e)}"
            self._create_log(error_msg)
        except Exception as e:
            error_msg = f"Unexpected Error: {str(e)}"
            self._create_log(error_msg)
        return None

    def generate_description(self, product_info):
        prompt = f"""
        あなたはBUYMA専門のプロコピーライターです。
        以下の条件で商品説明文を日本語で作成してください。

        [要件]
        1. 300-500文字
        2. ブランド名とカテゴリを自然に配置
        3. 商品の特徴を3点箇条書き
        4. 感情に訴える表現（例: 「上質なレザーの風合い」）
        5. 急かし表現や「今すぐ」などの強い勧誘は避ける
        6. 重複表現を避け、情報を簡潔に整理
        7. 生活シーンや使用イメージを盛り込む
        8. 読み手に自然に提案する口調で仕上げる

        [商品情報]
        ブランド: {product_info.get('brand', '')}
        商品名: {product_info.get('name', '')}
        カテゴリ: {product_info.get('category', '')}
        特徴: {product_info.get('features', '')}
        素材: {product_info.get('materials', '')}
        サイズ: {product_info.get('size', '')}
        カラー: {product_info.get('color', '')}
        対象層: {product_info.get('target', '')}
        価格帯: {product_info.get('price_range', '')}
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "あなたは高級ファッション専門のコピーライターです。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        result = self._call_api(payload)
        return result['choices'][0]['message']['content'].strip() if result else None

    def batch_process(self, products, retry=3):
        results = []
        for idx, product in enumerate(products):
            attempt = 0
            while attempt < retry:
                try:
                    print(f"処理中 ({idx+1}/{len(products)})")
                    desc = self.generate_description(product)
                    if desc:
                        results.append({**product, "description": desc})
                        break
                    else:
                        attempt += 1
                        time.sleep(2 ** attempt)
                except Exception as e:
                    print(f"エラー: {str(e)}")
                    attempt += 1
            time.sleep(random.uniform(1, 3))
        return results

if __name__ == "__main__":
    generator = BUYMADescriptionGenerator()
    sample_products = [
        {
            "brand": "PRADA",
            "name": "シンフォニー トートバッグ",
            "category": "トートバッグ",
            "features": "軽量ナイロン素材、大容量収納",
            "materials": "ナイロン",
            "size": "W35cm x H25cm x D15cm",
            "color": "ブラック",
            "target": "20-30代女性",
            "price_range": "15-20万円"
        }
    ]
    processed_data = generator.batch_process(sample_products)
    if processed_data:
        output_path = os.path.join(os.path.dirname(__file__), 'output.csv')
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=processed_data[0].keys())
            writer.writeheader()
            writer.writerows(processed_data)
        print(f"CSVファイルを正常に出力しました: {output_path}")
    else:
        print("処理に失敗しました。ログを確認してください。")

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\exported_projects\project_export_y7xxp1v8\app\utils\generate_descriptions.py ===
import os
import requests
import csv
import time
import random
from dotenv import load_dotenv
from datetime import datetime

# 環境変数の読み込み
load_dotenv()

class BUYMADescriptionGenerator:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.endpoint = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BUYMA-Auto-Desc/3.0"
        }
        self.model = "sonar-pro"  # 最新有効モデル名

    def _create_log(self, message, log_type="error"):
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{log_type}_{timestamp}.log"
        with open(os.path.join(log_dir, filename), "w", encoding="utf-8") as f:
            f.write(message)

    def _call_api(self, payload):
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e.response.status_code}\n{e.response.text}"
            self._create_log(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request Failed: {str(e)}"
            self._create_log(error_msg)
        except Exception as e:
            error_msg = f"Unexpected Error: {str(e)}"
            self._create_log(error_msg)
        return None

    def generate_description(self, product_info):
        prompt = f"""
        あなたはBUYMA専門のプロコピーライターです。
        以下の条件で商品説明文を日本語で作成してください。

        [要件]
        1. 300-500文字
        2. ブランド名とカテゴリを自然に配置
        3. 商品の特徴を3点箇条書き
        4. 感情に訴える表現（例: 「上質なレザーの風合い」）
        5. 急かし表現や「今すぐ」などの強い勧誘は避ける
        6. 重複表現を避け、情報を簡潔に整理
        7. 生活シーンや使用イメージを盛り込む
        8. 読み手に自然に提案する口調で仕上げる

        [商品情報]
        ブランド: {product_info.get('brand', '')}
        商品名: {product_info.get('name', '')}
        カテゴリ: {product_info.get('category', '')}
        特徴: {product_info.get('features', '')}
        素材: {product_info.get('materials', '')}
        サイズ: {product_info.get('size', '')}
        カラー: {product_info.get('color', '')}
        対象層: {product_info.get('target', '')}
        価格帯: {product_info.get('price_range', '')}
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "あなたは高級ファッション専門のコピーライターです。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        result = self._call_api(payload)
        return result['choices'][0]['message']['content'].strip() if result else None

    def batch_process(self, products, retry=3):
        results = []
        for idx, product in enumerate(products):
            attempt = 0
            while attempt < retry:
                try:
                    print(f"処理中 ({idx+1}/{len(products)})")
                    desc = self.generate_description(product)
                    if desc:
                        results.append({**product, "description": desc})
                        break
                    else:
                        attempt += 1
                        time.sleep(2 ** attempt)
                except Exception as e:
                    print(f"エラー: {str(e)}")
                    attempt += 1
            time.sleep(random.uniform(1, 3))
        return results

if __name__ == "__main__":
    generator = BUYMADescriptionGenerator()
    sample_products = [
        {
            "brand": "PRADA",
            "name": "シンフォニー トートバッグ",
            "category": "トートバッグ",
            "features": "軽量ナイロン素材、大容量収納",
            "materials": "ナイロン",
            "size": "W35cm x H25cm x D15cm",
            "color": "ブラック",
            "target": "20-30代女性",
            "price_range": "15-20万円"
        }
    ]
    processed_data = generator.batch_process(sample_products)
    if processed_data:
        output_path = os.path.join(os.path.dirname(__file__), 'output.csv')
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=processed_data[0].keys())
            writer.writeheader()
            writer.writerows(processed_data)
        print(f"CSVファイルを正常に出力しました: {output_path}")
    else:
        print("処理に失敗しました。ログを確認してください。")

# === NexusCore/healing_sandbox\src\agents\debugger_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: debugger_agent.py
# メモ: FKBの'target'ヒントを解釈し、「修正計画」を返す分析官にアップグレード。
#      エラーログとファイルコンテキストを受け取り、修正対象とパッチを特定します。
# ==============================================================================
import os
import json
import re
import difflib
import logging
from .base_agent import BaseAgent

class DebuggerAgent(BaseAgent):
    """
    エラーログを分析し、FKBの知識に基づいて、どのファイルにどのような修正を
    適用すべきかという「修正計画」を立案する分析官エージェント。
    """
    def __init__(self, api_key: str, model: str, knowledge_base_path: str = "fkb_local.json"):
        super().__init__(api_key, model)
        self.knowledge_base_path = knowledge_base_path
        self.fkb = self._load_fkb()
        
        if self.fkb:
            print(f"[OK] DebuggerAgent initialized. {len(self.fkb)} known issues loaded from: {self.knowledge_base_path}")
        else:
            print(f"[WARNING] DebuggerAgent initialized with an EMPTY knowledge base. File not found or empty at: {self.knowledge_base_path}")

    def _load_fkb(self) -> list:
        """
        Failure Knowledge Base (FKB)をロードします。
        サンドボックス実行を考慮し、カレントディレクトリからの相対パスで検索します。
        """
        try:
            path = self.knowledge_base_path
            if not os.path.isabs(path):
                path = os.path.join(os.getcwd(), self.knowledge_base_path)
            if not os.path.exists(path): return []
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Failed to load FKB: {e}")
            return []

    def debug(self, error_log: str, files_context: dict) -> dict | None:
        """
        エラーログを分析し、パッチとターゲットファイルを含む「修正計画」を返します。

        Args:
            error_log (str): pytestなどから出力されたエラーログ。
            files_context (dict): 修正対象となりうるファイルのパスを格納した辞書。
                                  例: {"source_file": "/path/to/app.py", "test_file": "/path/to/test_app.py"}

        Returns:
            dict | None: 修正計画の辞書、または解決策が見つからない場合はNone。
                         例: {"patch": "...", "target": "test_file", "entry": {...}}
        """
        logging.info(f"Debugging error... (log size: {len(error_log)} chars)")

        for entry in self.fkb:
            if re.search(entry["error_signature"], error_log, re.DOTALL | re.IGNORECASE):
                logging.info(f"Found known issue: {entry['cause']}")
                
                # FKBから修正対象のヒント（"source_file" or "test_file"）を取得
                target_hint = entry.get("target", "source_file") # デフォルトはソースファイル
                
                file_to_read_path = files_context.get(target_hint)
                if not file_to_read_path or not os.path.exists(file_to_read_path):
                    logging.error(f"Target file for reading not found in context: {target_hint}")
                    continue

                try:
                    with open(file_to_read_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    modified_code = self._apply_solution_pattern(original_code, entry["solution_pattern"])

                    if modified_code and original_code != modified_code:
                        diff = self._create_diff(original_code, modified_code, file_to_read_path)
                        logging.info(f"Generated patch for '{target_hint}':\n{diff}")
                        # 「修正計画」を辞書として返す
                        return {"patch": diff, "target": target_hint, "entry": entry}
                    else:
                        logging.warning(f"Solution pattern did not result in code changes for file: {file_to_read_path}")
                
                except Exception as e:
                    logging.error(f"Error applying solution for '{entry['cause']}': {e}", exc_info=True)
                
                # 1つのルールに一致したら、その結果（成功でも失敗でも）を返して終了
                return None

        logging.warning("No known solution found in FKB for this error.")
        return None

    def _apply_solution_pattern(self, code: str, solution: dict) -> str | None:
        """FKBの解決策パターンに基づき、コードを修正します。"""
        solution_type = solution.get("type")
        if solution_type == "regex_replace":
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            # FKBの$1, $2... を re.subが解釈できる \\1, \\2... に変換
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, code, flags=re.DOTALL)
        elif solution_type == "add_import":
            import_statement = solution["import"]
            if import_statement not in code:
                return f"{import_statement}\n{code}"
            return code
        return None

    def _create_diff(self, original_code: str, modified_code: str, filename: str) -> str:
        """2つのコード文字列からunified diff形式のパッチを生成します。"""
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename,
            tofile=filename,
        )
        return "".join(diff)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\healing_sandbox\src\agents\debugger_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: debugger_agent.py
# メモ: FKBの'target'ヒントを解釈し、「修正計画」を返す分析官にアップグレード。
#      エラーログとファイルコンテキストを受け取り、修正対象とパッチを特定します。
# ==============================================================================
import os
import json
import re
import difflib
import logging
from .base_agent import BaseAgent

class DebuggerAgent(BaseAgent):
    """
    エラーログを分析し、FKBの知識に基づいて、どのファイルにどのような修正を
    適用すべきかという「修正計画」を立案する分析官エージェント。
    """
    def __init__(self, api_key: str, model: str, knowledge_base_path: str = "fkb_local.json"):
        super().__init__(api_key, model)
        self.knowledge_base_path = knowledge_base_path
        self.fkb = self._load_fkb()
        
        if self.fkb:
            print(f"[OK] DebuggerAgent initialized. {len(self.fkb)} known issues loaded from: {self.knowledge_base_path}")
        else:
            print(f"[WARNING] DebuggerAgent initialized with an EMPTY knowledge base. File not found or empty at: {self.knowledge_base_path}")

    def _load_fkb(self) -> list:
        """
        Failure Knowledge Base (FKB)をロードします。
        サンドボックス実行を考慮し、カレントディレクトリからの相対パスで検索します。
        """
        try:
            path = self.knowledge_base_path
            if not os.path.isabs(path):
                path = os.path.join(os.getcwd(), self.knowledge_base_path)
            if not os.path.exists(path): return []
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Failed to load FKB: {e}")
            return []

    def debug(self, error_log: str, files_context: dict) -> dict | None:
        """
        エラーログを分析し、パッチとターゲットファイルを含む「修正計画」を返します。

        Args:
            error_log (str): pytestなどから出力されたエラーログ。
            files_context (dict): 修正対象となりうるファイルのパスを格納した辞書。
                                  例: {"source_file": "/path/to/app.py", "test_file": "/path/to/test_app.py"}

        Returns:
            dict | None: 修正計画の辞書、または解決策が見つからない場合はNone。
                         例: {"patch": "...", "target": "test_file", "entry": {...}}
        """
        logging.info(f"Debugging error... (log size: {len(error_log)} chars)")

        for entry in self.fkb:
            if re.search(entry["error_signature"], error_log, re.DOTALL | re.IGNORECASE):
                logging.info(f"Found known issue: {entry['cause']}")
                
                # FKBから修正対象のヒント（"source_file" or "test_file"）を取得
                target_hint = entry.get("target", "source_file") # デフォルトはソースファイル
                
                file_to_read_path = files_context.get(target_hint)
                if not file_to_read_path or not os.path.exists(file_to_read_path):
                    logging.error(f"Target file for reading not found in context: {target_hint}")
                    continue

                try:
                    with open(file_to_read_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    modified_code = self._apply_solution_pattern(original_code, entry["solution_pattern"])

                    if modified_code and original_code != modified_code:
                        diff = self._create_diff(original_code, modified_code, file_to_read_path)
                        logging.info(f"Generated patch for '{target_hint}':\n{diff}")
                        # 「修正計画」を辞書として返す
                        return {"patch": diff, "target": target_hint, "entry": entry}
                    else:
                        logging.warning(f"Solution pattern did not result in code changes for file: {file_to_read_path}")
                
                except Exception as e:
                    logging.error(f"Error applying solution for '{entry['cause']}': {e}", exc_info=True)
                
                # 1つのルールに一致したら、その結果（成功でも失敗でも）を返して終了
                return None

        logging.warning("No known solution found in FKB for this error.")
        return None

    def _apply_solution_pattern(self, code: str, solution: dict) -> str | None:
        """FKBの解決策パターンに基づき、コードを修正します。"""
        solution_type = solution.get("type")
        if solution_type == "regex_replace":
            search_pattern = solution["search"]
            replace_template = solution["replace"]
            # FKBの$1, $2... を re.subが解釈できる \\1, \\2... に変換
            replace_template = re.sub(r'\$(\d)', r'\\\1', replace_template)
            return re.sub(search_pattern, replace_template, code, flags=re.DOTALL)
        elif solution_type == "add_import":
            import_statement = solution["import"]
            if import_statement not in code:
                return f"{import_statement}\n{code}"
            return code
        return None

    def _create_diff(self, original_code: str, modified_code: str, filename: str) -> str:
        """2つのコード文字列からunified diff形式のパッチを生成します。"""
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            modified_code.splitlines(keepends=True),
            fromfile=filename,
            tofile=filename,
        )
        return "".join(diff)

# === NexusCore/src\agents\postmortem_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: postmortem_agent.py
# メモ: 【思考プロセス強化版】生成するFKBのsolution_patternが、
#      テストを完全にパスさせるための、より包括的で完全な解決策になるよう、
#      プロンプトの思考プロセスを大幅に強化。
# ==============================================================================
import json
import re
import logging
from .base_agent import BaseAgent

class PostmortemAgent(BaseAgent):
    SYSTEM_PROMPT = """
あなたは、非常に経験豊富なソフトウェア開発者であり、根本原因分析（RCA）の専門家です。
あなたの仕事は、他のAIエージェントが解決に失敗したテストエラーの完全なコンテキストを分析し、
そのエラーを将来解決するための「知識」をJSON形式で生成することです。
"""

    def analyze_failure_and_suggest_fkb_entry(
        self,
        error_log: str,
        source_code: str,
        test_code: str,
        source_file_path: str,
        test_file_path: str
    ) -> dict | None:
        """
        未知のエラーを分析し、fkb_local.jsonに追加すべき新しいエントリを提案する。
        成功した場合は辞書を、失敗した場合はNoneを返す。
        """
        self.logger.info(f"Analyzing failed test to generate new FKB entry (source={source_file_path}, test={test_file_path})")

        # ▼▼▼▼▼ ここからが最重要修正点 ▼▼▼▼▼
        prompt = f"""
# 状況
我々のAI開発システムが、以下のテストエラーの自己修復に失敗しました。
原因は、故障知識ベース（FKB）に、このエラーを解決するためのルールが存在しなかったことです。
あなたの任務は、この失敗事例を分析し、FKBに追加すべき新しい知識エントリを1つ生成することです。

# 分析対象データ
---
## 1. 失敗したテストのエラーログ
```
{error_log}
```
---
## 2. エラーが発生したソースコード (`{source_file_path}`)
```python
{source_code}
```
---
## 3. 失敗したテストコード (`{test_file_path}`)
```python
{test_code}
```
---

# あなたへの厳格な指示
上記の情報に基づき、以下の思考プロセスに従って、FKBエントリを生成してください。

## 思考プロセス
1.  **根本原因の特定**: エラーログとコードを注意深く読み、バグの根本原因を特定せよ。（例：「テストコードが、ネストされた関数を直接インポートしようとしている」）
2.  **エラーシグネチャの一般化**: エラーログから、この種のエラーを将来確実に捕捉できる、汎用的な正規表現（regex）を `error_signature` として考案せよ。
3.  **完全な解決策の考案**: このバグを修正し、**テストを完全にパスさせる**には、どのファイルをどのように変更する必要があるかを具体的に考えよ。
    -   例えば、`ImportError`を修正する場合、`import`文の修正だけでなく、そのインポートを利用している箇所の**関数名**も修正する必要があるかもしれない。
    -   例えば、ソースコードの関数名を変更する場合、テストコードの呼び出し箇所も変更する必要がある。
    -   この具体的な修正を、`llm_diagnose_and_fix`の`instruction`として記述せよ。
4.  **最終的なJSONの構築**: 上記の分析結果を基に、`id`, `error_signature`, `cause`, `target`, `solution_pattern`, `description` を持つ、単一のJSONオブジェクトを生成せよ。

## `solution_pattern` の詳細なルール
- `solution_pattern` は、必ず "type" キーを持つ **JSONオブジェクト（辞書）**でなければならない。
- `type` が `"llm_diagnose_and_fix"` の場合: `"instruction"` キーに、**テストを完全にパスさせるための、包括的な修正指示**を記述せよ。

## JSON出力例
```json
{{
  "id": "FKB-SUGGESTION-0001",
  "error_signature": "ImportError: cannot import name 'add'",
  "cause": "テストコードが、ネストされた関数や、誤った名前の関数を直接インポートしようとしている。",
  "target": "test_file",
  "solution_pattern": {{
    "type": "llm_diagnose_and_fix",
    "instruction": "The test failed with an ImportError. Analyze the source code to find the correct way to access the intended function. Modify the test code to import the parent function and then call it to get the nested function, or fix the imported function name if it's a simple typo. The goal is to make the test pass."
  }},
  "description": "ネストされた関数やタイポによる不正なインポートが原因のエラーを、テストコード側を修正することで解決する知識。"
}}
```

# 絶対的な出力ルール
- **生成したJSONオブジェクトのみ**を出力すること。
- 説明、前置き、その他のテキストは一切含めてはならない。
- `id` は `"FKB-SUGGESTION-XXXX"` の形式とせよ。
- `cause` と `description` は、日本語で簡潔に記述すること。
- JSONは必ず `{{` で始まり、 `}}` で終わる単一のオブジェクトであること。
"""
        # ▲▲▲▲▲ ここまでが最重要修正点 ▲▲▲▲▲
        try:
            response_str = self._call_llm(prompt, self.SYSTEM_PROMPT, temperature=0.3, as_json=True)
            match = re.search(r'\{.*\}', response_str, re.DOTALL)
            if not match:
                self.logger.error(f"LLM response does not contain a JSON object. Raw response:\n{response_str}")
                return None
            
            json_str = match.group(0)
            suggestion = json.loads(json_str)
            self.logger.info("Successfully generated a new FKB suggestion.")
            return suggestion

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON generated by LLM: {e}. Raw response:\n{response_str}")
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in PostmortemAgent: {e}", exc_info=True)
            return None

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\postmortem_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: postmortem_agent.py
# メモ: 【思考プロセス強化版】生成するFKBのsolution_patternが、
#      テストを完全にパスさせるための、より包括的で完全な解決策になるよう、
#      プロンプトの思考プロセスを大幅に強化。
# ==============================================================================
import json
import re
import logging
from .base_agent import BaseAgent

class PostmortemAgent(BaseAgent):
    SYSTEM_PROMPT = """
あなたは、非常に経験豊富なソフトウェア開発者であり、根本原因分析（RCA）の専門家です。
あなたの仕事は、他のAIエージェントが解決に失敗したテストエラーの完全なコンテキストを分析し、
そのエラーを将来解決するための「知識」をJSON形式で生成することです。
"""

    def analyze_failure_and_suggest_fkb_entry(
        self,
        error_log: str,
        source_code: str,
        test_code: str,
        source_file_path: str,
        test_file_path: str
    ) -> dict | None:
        """
        未知のエラーを分析し、fkb_local.jsonに追加すべき新しいエントリを提案する。
        成功した場合は辞書を、失敗した場合はNoneを返す。
        """
        self.logger.info(f"Analyzing failed test to generate new FKB entry (source={source_file_path}, test={test_file_path})")

        # ▼▼▼▼▼ ここからが最重要修正点 ▼▼▼▼▼
        prompt = f"""
# 状況
我々のAI開発システムが、以下のテストエラーの自己修復に失敗しました。
原因は、故障知識ベース（FKB）に、このエラーを解決するためのルールが存在しなかったことです。
あなたの任務は、この失敗事例を分析し、FKBに追加すべき新しい知識エントリを1つ生成することです。

# 分析対象データ
---
## 1. 失敗したテストのエラーログ
```
{error_log}
```
---
## 2. エラーが発生したソースコード (`{source_file_path}`)
```python
{source_code}
```
---
## 3. 失敗したテストコード (`{test_file_path}`)
```python
{test_code}
```
---

# あなたへの厳格な指示
上記の情報に基づき、以下の思考プロセスに従って、FKBエントリを生成してください。

## 思考プロセス
1.  **根本原因の特定**: エラーログとコードを注意深く読み、バグの根本原因を特定せよ。（例：「テストコードが、ネストされた関数を直接インポートしようとしている」）
2.  **エラーシグネチャの一般化**: エラーログから、この種のエラーを将来確実に捕捉できる、汎用的な正規表現（regex）を `error_signature` として考案せよ。
3.  **完全な解決策の考案**: このバグを修正し、**テストを完全にパスさせる**には、どのファイルをどのように変更する必要があるかを具体的に考えよ。
    -   例えば、`ImportError`を修正する場合、`import`文の修正だけでなく、そのインポートを利用している箇所の**関数名**も修正する必要があるかもしれない。
    -   例えば、ソースコードの関数名を変更する場合、テストコードの呼び出し箇所も変更する必要がある。
    -   この具体的な修正を、`llm_diagnose_and_fix`の`instruction`として記述せよ。
4.  **最終的なJSONの構築**: 上記の分析結果を基に、`id`, `error_signature`, `cause`, `target`, `solution_pattern`, `description` を持つ、単一のJSONオブジェクトを生成せよ。

## `solution_pattern` の詳細なルール
- `solution_pattern` は、必ず "type" キーを持つ **JSONオブジェクト（辞書）**でなければならない。
- `type` が `"llm_diagnose_and_fix"` の場合: `"instruction"` キーに、**テストを完全にパスさせるための、包括的な修正指示**を記述せよ。

## JSON出力例
```json
{{
  "id": "FKB-SUGGESTION-0001",
  "error_signature": "ImportError: cannot import name 'add'",
  "cause": "テストコードが、ネストされた関数や、誤った名前の関数を直接インポートしようとしている。",
  "target": "test_file",
  "solution_pattern": {{
    "type": "llm_diagnose_and_fix",
    "instruction": "The test failed with an ImportError. Analyze the source code to find the correct way to access the intended function. Modify the test code to import the parent function and then call it to get the nested function, or fix the imported function name if it's a simple typo. The goal is to make the test pass."
  }},
  "description": "ネストされた関数やタイポによる不正なインポートが原因のエラーを、テストコード側を修正することで解決する知識。"
}}
```

# 絶対的な出力ルール
- **生成したJSONオブジェクトのみ**を出力すること。
- 説明、前置き、その他のテキストは一切含めてはならない。
- `id` は `"FKB-SUGGESTION-XXXX"` の形式とせよ。
- `cause` と `description` は、日本語で簡潔に記述すること。
- JSONは必ず `{{` で始まり、 `}}` で終わる単一のオブジェクトであること。
"""
        # ▲▲▲▲▲ ここまでが最重要修正点 ▲▲▲▲▲
        try:
            response_str = self._call_llm(prompt, self.SYSTEM_PROMPT, temperature=0.3, as_json=True)
            match = re.search(r'\{.*\}', response_str, re.DOTALL)
            if not match:
                self.logger.error(f"LLM response does not contain a JSON object. Raw response:\n{response_str}")
                return None
            
            json_str = match.group(0)
            suggestion = json.loads(json_str)
            self.logger.info("Successfully generated a new FKB suggestion.")
            return suggestion

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON generated by LLM: {e}. Raw response:\n{response_str}")
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in PostmortemAgent: {e}", exc_info=True)
            return None

# === NexusCore/src\gradio_app\app_ui.py ===
# src/gradio_app/app_ui.py

import gradio as gr
import os
import subprocess
from openai import OpenAI
from dotenv import load_dotenv
import re

# .env から OPENAI_API_KEY を読み込み
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ファイル保存先
SAMPLE_FILE = "./sandbox_output/sample.py"
TEST_FILE = "./sandbox_output/test_sample.py"

def save_sample_code(code: str):
    os.makedirs(os.path.dirname(SAMPLE_FILE), exist_ok=True)
    with open(SAMPLE_FILE, "w", encoding="utf-8") as f:
        f.write(code)

def extract_code(full_response: str) -> str:
    match = re.search(r"```python\n(.*?)```", full_response, re.DOTALL)
    if match:
        return match.group(1).strip()
    code = full_response
    code = re.sub(r'^(Sure.*?pytest-style unit test.*?`is_prime\(n\)`:?\s*\n)?', '', code, flags=re.MULTILINE | re.IGNORECASE)
    code = re.sub(r'(\n?This test.*$|\n?Please note.*$)', '', code, flags=re.DOTALL)
    return code.strip()

def generate_unit_test(code: str) -> str:
    prompt = f"""
以下のPython関数に対するpytestスタイルのユニットテストを生成してください。

{code}

テストコードのみを返してください。test_sample.pyというファイルに直接書き込めるような、完全に有効なPythonコードのみが必要です。
前置きや結びの言葉、説明文は一切含めないでください。
**生成するすべてのコードを単一の「```python」と「```」ブロックで必ず囲んでください。**
**`sample.py`から`is_prime`関数をインポートする行を含めてください。**
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return extract_code(response.choices[0].message.content.strip())

def save_test_code(code: str):
    os.makedirs(os.path.dirname(TEST_FILE), exist_ok=True)
    with open(TEST_FILE, "w", encoding="utf-8") as f:
        f.write(code)

def run_pytest() -> str:
    try:
        result = subprocess.run(
            ["pytest", TEST_FILE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        return output
    except FileNotFoundError:
        return "⚠️ エラー: pytestが見つかりません。\n`pip install pytest` を実行してください。"
    except Exception as e:
        return f"⚠️ pytest実行中に予期せぬエラーが発生しました: {e}"

def process_code(code: str):
    if not code.strip():
        return "", "💡 Python関数を入力してください。"
    save_sample_code(code)
    try:
        test_code = generate_unit_test(code)
        save_test_code(test_code)
        test_result = run_pytest()
        return test_code, test_result
    except Exception as e:
        return "", f"❌ エラー: {e}\nAPIキー、ネットワーク、または生成コードに問題がある可能性があります。"

# GradioタブUIを構築
def launch_app_ui():
    with gr.Column():
        gr.Markdown("## ✅ Python関数入力 → ユニットテスト生成 → 自動実行")
        gr.Markdown("ChatGPTがpytest形式のテストコードを生成し、自動実行します。")

        code_input = gr.Code(
            label="📝 Python関数を入力", 
            language="python", 
            lines=10, 
            value="""def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True"""
        )
        generate_button = gr.Button("🔁 テスト生成＆実行")

        test_output = gr.Code(label="✅ 生成されたユニットテスト", language="python", lines=10, interactive=False)
        result_output = gr.Textbox(label="🧪 pytest実行結果", lines=15, interactive=False)

        generate_button.click(
            fn=process_code,
            inputs=code_input,
            outputs=[test_output, result_output]
        )

# === NexusCore/src\utils\file_utils.py ===
# ==============================================================================
# フォルダ: src/utils
# ファイル名: file_utils.py
# メモ: ArchitectAgentが生成した詳細な設計図（ファイルとフォルダのリスト）を
#      解釈し、プロジェクト構造を再帰的に作成できるようにアップグレード。
# ==============================================================================
import os
import zipfile
import json
from datetime import datetime
import tempfile
import logging
from pathlib import Path # pathlibをインポート

# 既存の関数の定義 (変更なし)
MAX_FILE_SIZE_MB = 5
MAX_TOTAL_SIZE_MB = 20
FRONTEND_PREVIEW_CHARS = 100

def extract_file_content(file):
    # ... (既存の関数の実装はそのまま) ...
    logging.info("DEBUG: extract_file_content - start")
    logging.info("DEBUG: file type: %s", type(file))
    logging.info("DEBUG: file attributes: %s", dir(file))
    logging.info("DEBUG: file __dict__: %s", getattr(file, '__dict__', 'no __dict__'))
    try:
        if hasattr(file, "name") and os.path.exists(file.name):
            try:
                with open(file.name, "r", encoding="utf-8") as f:
                    content = f.read()
                    logging.info("DEBUG: open utf-8 (preview): %s", content[:100])
                    return content
            except Exception:
                with open(file.name, "r", encoding="cp932", errors="ignore") as f:
                    content = f.read()
                    logging.info("DEBUG: open cp932 (preview): %s", content[:100])
                    return content
        # ... (以下、既存の関数の実装が続く) ...
    except Exception as e:
        logging.error(f"Error in extract_file_content: {e}")
        return ""

def file_list_display(files):
    # ... (既存の関数の実装はそのまま) ...
    if not files:
        return "（ファイル未選択）"
    if not isinstance(files, list):
        files = [files]
    names = []
    for file in files:
        if hasattr(file, "name"):
            names.append(file.name)
        else:
            names.append(str(file))
    return "\\n".join(names)

def download_history(history):
    # ... (既存の関数の実装はそのまま) ...
    fn = f"history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    return fn

# --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
# 古いcreate_project_structure関数を、新しいインテリジェントなバージョンに置き換えます。
def create_project_structure(root_path: str, files: list):
    """
    指定されたルートパスに、設計データに基づいたファイルとフォルダの構造を再帰的に作成します。

    Args:
        root_path (str): プロジェクトが作成されるベースディレクトリ。
        files (list): ファイル/フォルダ情報を格納した辞書のリスト。
                      各辞書は 'name', 'type', 'content' (ファイルの場合) のキーを持つ。
    """
    logger = logging.getLogger(__name__)
    root = Path(root_path)
    logger.info(f"Creating project structure at: {root}")

    # ルートディレクトリが存在することを確認
    root.mkdir(parents=True, exist_ok=True)

    if not isinstance(files, list):
        logger.error(f"Invalid 'files' format. Expected a list, but got {type(files)}")
        return

    for item in files:
        item_path_str = item.get("name")
        item_type = item.get("type")
        
        if not item_path_str or not item_type:
            logger.warning(f"Skipping invalid item in design data: {item}")
            continue

        # item_path_str内のバックスラッシュをスラッシュに統一し、先頭のスラッシュを削除
        normalized_path = item_path_str.replace("\\\\", "/").lstrip("/")
        full_path = root / normalized_path
        
        try:
            if item_type == 'folder':
                full_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created directory: {full_path}")
            elif item_type == 'file':
                # ファイルを書き込む前に、親ディレクトリが存在することを確認
                full_path.parent.mkdir(parents=True, exist_ok=True)
                content = item.get("content", "")
                full_path.write_text(content, encoding='utf-8')
                logger.debug(f"Created file: {full_path}")
        except Exception as e:
            logger.error(f"Failed to create {item_type} at {full_path}: {e}")

# --- ★★★★★ ここまで ★★★★★ ---


# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\gradio_app\app_ui.py ===
# src/gradio_app/app_ui.py

import gradio as gr
import os
import subprocess
from openai import OpenAI
from dotenv import load_dotenv
import re

# .env から OPENAI_API_KEY を読み込み
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ファイル保存先
SAMPLE_FILE = "./sandbox_output/sample.py"
TEST_FILE = "./sandbox_output/test_sample.py"

def save_sample_code(code: str):
    os.makedirs(os.path.dirname(SAMPLE_FILE), exist_ok=True)
    with open(SAMPLE_FILE, "w", encoding="utf-8") as f:
        f.write(code)

def extract_code(full_response: str) -> str:
    match = re.search(r"```python\n(.*?)```", full_response, re.DOTALL)
    if match:
        return match.group(1).strip()
    code = full_response
    code = re.sub(r'^(Sure.*?pytest-style unit test.*?`is_prime\(n\)`:?\s*\n)?', '', code, flags=re.MULTILINE | re.IGNORECASE)
    code = re.sub(r'(\n?This test.*$|\n?Please note.*$)', '', code, flags=re.DOTALL)
    return code.strip()

def generate_unit_test(code: str) -> str:
    prompt = f"""
以下のPython関数に対するpytestスタイルのユニットテストを生成してください。

{code}

テストコードのみを返してください。test_sample.pyというファイルに直接書き込めるような、完全に有効なPythonコードのみが必要です。
前置きや結びの言葉、説明文は一切含めないでください。
**生成するすべてのコードを単一の「```python」と「```」ブロックで必ず囲んでください。**
**`sample.py`から`is_prime`関数をインポートする行を含めてください。**
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return extract_code(response.choices[0].message.content.strip())

def save_test_code(code: str):
    os.makedirs(os.path.dirname(TEST_FILE), exist_ok=True)
    with open(TEST_FILE, "w", encoding="utf-8") as f:
        f.write(code)

def run_pytest() -> str:
    try:
        result = subprocess.run(
            ["pytest", TEST_FILE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        return output
    except FileNotFoundError:
        return "⚠️ エラー: pytestが見つかりません。\n`pip install pytest` を実行してください。"
    except Exception as e:
        return f"⚠️ pytest実行中に予期せぬエラーが発生しました: {e}"

def process_code(code: str):
    if not code.strip():
        return "", "💡 Python関数を入力してください。"
    save_sample_code(code)
    try:
        test_code = generate_unit_test(code)
        save_test_code(test_code)
        test_result = run_pytest()
        return test_code, test_result
    except Exception as e:
        return "", f"❌ エラー: {e}\nAPIキー、ネットワーク、または生成コードに問題がある可能性があります。"

# GradioタブUIを構築
def launch_app_ui():
    with gr.Column():
        gr.Markdown("## ✅ Python関数入力 → ユニットテスト生成 → 自動実行")
        gr.Markdown("ChatGPTがpytest形式のテストコードを生成し、自動実行します。")

        code_input = gr.Code(
            label="📝 Python関数を入力", 
            language="python", 
            lines=10, 
            value="""def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True"""
        )
        generate_button = gr.Button("🔁 テスト生成＆実行")

        test_output = gr.Code(label="✅ 生成されたユニットテスト", language="python", lines=10, interactive=False)
        result_output = gr.Textbox(label="🧪 pytest実行結果", lines=15, interactive=False)

        generate_button.click(
            fn=process_code,
            inputs=code_input,
            outputs=[test_output, result_output]
        )

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\file_utils.py ===
# ==============================================================================
# フォルダ: src/utils
# ファイル名: file_utils.py
# メモ: ArchitectAgentが生成した詳細な設計図（ファイルとフォルダのリスト）を
#      解釈し、プロジェクト構造を再帰的に作成できるようにアップグレード。
# ==============================================================================
import os
import zipfile
import json
from datetime import datetime
import tempfile
import logging
from pathlib import Path # pathlibをインポート

# 既存の関数の定義 (変更なし)
MAX_FILE_SIZE_MB = 5
MAX_TOTAL_SIZE_MB = 20
FRONTEND_PREVIEW_CHARS = 100

def extract_file_content(file):
    # ... (既存の関数の実装はそのまま) ...
    logging.info("DEBUG: extract_file_content - start")
    logging.info("DEBUG: file type: %s", type(file))
    logging.info("DEBUG: file attributes: %s", dir(file))
    logging.info("DEBUG: file __dict__: %s", getattr(file, '__dict__', 'no __dict__'))
    try:
        if hasattr(file, "name") and os.path.exists(file.name):
            try:
                with open(file.name, "r", encoding="utf-8") as f:
                    content = f.read()
                    logging.info("DEBUG: open utf-8 (preview): %s", content[:100])
                    return content
            except Exception:
                with open(file.name, "r", encoding="cp932", errors="ignore") as f:
                    content = f.read()
                    logging.info("DEBUG: open cp932 (preview): %s", content[:100])
                    return content
        # ... (以下、既存の関数の実装が続く) ...
    except Exception as e:
        logging.error(f"Error in extract_file_content: {e}")
        return ""

def file_list_display(files):
    # ... (既存の関数の実装はそのまま) ...
    if not files:
        return "（ファイル未選択）"
    if not isinstance(files, list):
        files = [files]
    names = []
    for file in files:
        if hasattr(file, "name"):
            names.append(file.name)
        else:
            names.append(str(file))
    return "\\n".join(names)

def download_history(history):
    # ... (既存の関数の実装はそのまま) ...
    fn = f"history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    return fn

# --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
# 古いcreate_project_structure関数を、新しいインテリジェントなバージョンに置き換えます。
def create_project_structure(root_path: str, files: list):
    """
    指定されたルートパスに、設計データに基づいたファイルとフォルダの構造を再帰的に作成します。

    Args:
        root_path (str): プロジェクトが作成されるベースディレクトリ。
        files (list): ファイル/フォルダ情報を格納した辞書のリスト。
                      各辞書は 'name', 'type', 'content' (ファイルの場合) のキーを持つ。
    """
    logger = logging.getLogger(__name__)
    root = Path(root_path)
    logger.info(f"Creating project structure at: {root}")

    # ルートディレクトリが存在することを確認
    root.mkdir(parents=True, exist_ok=True)

    if not isinstance(files, list):
        logger.error(f"Invalid 'files' format. Expected a list, but got {type(files)}")
        return

    for item in files:
        item_path_str = item.get("name")
        item_type = item.get("type")
        
        if not item_path_str or not item_type:
            logger.warning(f"Skipping invalid item in design data: {item}")
            continue

        # item_path_str内のバックスラッシュをスラッシュに統一し、先頭のスラッシュを削除
        normalized_path = item_path_str.replace("\\\\", "/").lstrip("/")
        full_path = root / normalized_path
        
        try:
            if item_type == 'folder':
                full_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created directory: {full_path}")
            elif item_type == 'file':
                # ファイルを書き込む前に、親ディレクトリが存在することを確認
                full_path.parent.mkdir(parents=True, exist_ok=True)
                content = item.get("content", "")
                full_path.write_text(content, encoding='utf-8')
                logger.debug(f"Created file: {full_path}")
        except Exception as e:
            logger.error(f"Failed to create {item_type} at {full_path}: {e}")

# --- ★★★★★ ここまで ★★★★★ ---


# === NexusCore/src\agents\guardian_agent.py ===
import json
import git
from .base_agent import BaseAgent
from src.utils.vcs import GitController

class GuardianAgent(BaseAgent):
    """
    コードの品質、セキュリティ、憲法への準拠をレビューし、
    承認された変更をGitに記録するCTOエージェント。
    """
    # ★★★★★ 修正点1: 他のエージェントと共通のSYSTEM_PROMPTを定義 ★★★★★
    SYSTEM_PROMPT = """
あなたはCTO（最高技術責任者）です。
開発チームから提出されたコード、テスト結果、その他の情報を総合的にレビューし、
その変更を承認（APPROVE）するか、修正のために差し戻す（REJECT）かを判断してください。
判断は、プロジェクトの憲法と、提示された技術的証拠に厳密に基づいてください。
"""

    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        try:
            self.vcs = GitController()
        except git.InvalidGitRepositoryError:
            self.vcs = None
            print("⚠️ GuardianAgent: Gitリポジトリが見つからないため、コミット機能は無効です。")

    def review_and_commit(self, code_draft: str, test_code: str, test_result: str, testimony: str, constitution: str, task_description: str, changed_files: list, debug_info: dict = None):
        """
        コードをレビューし、承認された場合にのみコミットを実行する。
        """
        print("\n--- GuardianAgent (CTO): 最終レビューとコミット判断を開始 ---")

        # ★★★★★ 修正点2: プロンプトの構造をSYSTEM_PROMPTと分離 ★★★★★
        prompt = f"""
# レビュー対象の情報
- **プロジェクト憲法**: {constitution}
- **元のタスク**: {task_description}
- **提出コード**:
```python
{code_draft}
```
- **テストコード**:
```python
{test_code}
```
- **テスト結果**:
```
{test_result}
```
- **開発者の証言**: {testimony}

# あなたへの指示
上記の情報に基づき、このコード変更を承認するかを判断してください。

# 出力要件
- 必ず `decision` (`APPROVE`または`REJECT`) と `reason` (判断理由) を含むJSON形式で出力してください。
- REJECTする場合、`feedback_for_coder` キーに具体的な修正指示を含めてください。
"""
        # ★★★★★ 修正点3: 'invoke' を正しい '_call_llm' に修正し、JSON出力を指定 ★★★★★
        review_result_json = self._call_llm(prompt, self.SYSTEM_PROMPT, as_json=True)
        
        try:
            review_data = json.loads(review_result_json)
        except json.JSONDecodeError:
            print("❌ GuardianAgentのレビュー出力が不正なJSONでした。")
            return {"decision": "REJECT", "reason": "Invalid JSON response from Guardian."}

        decision = review_data.get("decision", "REJECT")
        reason = review_data.get("reason", "理由不明。")
        print(f"判断: {decision}")
        print(f"理由: {reason}")
        
        if decision == "REJECT":
            review_data["feedback_for_coder"] = review_data.get("feedback_for_coder", reason)
            return review_data

        if self.vcs:
            commit_message = self._generate_commit_message(review_data, changed_files, debug_info)
            commit_hash = self.vcs.commit_changes(changed_files, commit_message)
            
            if commit_hash:
                review_data["commit"] = commit_hash
            else:
                review_data["commit"] = "Commit failed or no changes detected."
        else:
            review_data["commit"] = "Git repository not available."
            
        return review_data


    def _generate_commit_message(self, review_data: dict, changed_files: list, debug_info: dict = None) -> str:
        """
        Conventional Commits形式に準拠したコミットメッセージを生成する。
        """
        scope = "auto"
        body = f"Reviewed by: GuardianAgent (Model: {self.model})\n"
        body += f"Reason for approval: {review_data.get('reason', 'N/A')}\n"

        if debug_info:
            commit_type = "fix"
            header = f"{commit_type}({scope}): Self-healed by DebuggerAgent"
            body += f"\n[DEBUGGER ACTIVITY]\n"
            body += f"Error Signature: {debug_info.get('error_signature', 'N/A')}\n"
            solution_type = debug_info.get('solution_pattern', {}).get('type', 'N/A')
            body += f"Applied Solution Type: {solution_type}\n"
        else:
            commit_type = "feat"
            header = f"{commit_type}({scope}): Implemented new functionality via CoderAgent"
        
        return f"{header}\n\n{body}"

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\guardian_agent.py ===
import json
import git
from .base_agent import BaseAgent
from src.utils.vcs import GitController

class GuardianAgent(BaseAgent):
    """
    コードの品質、セキュリティ、憲法への準拠をレビューし、
    承認された変更をGitに記録するCTOエージェント。
    """
    # ★★★★★ 修正点1: 他のエージェントと共通のSYSTEM_PROMPTを定義 ★★★★★
    SYSTEM_PROMPT = """
あなたはCTO（最高技術責任者）です。
開発チームから提出されたコード、テスト結果、その他の情報を総合的にレビューし、
その変更を承認（APPROVE）するか、修正のために差し戻す（REJECT）かを判断してください。
判断は、プロジェクトの憲法と、提示された技術的証拠に厳密に基づいてください。
"""

    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        try:
            self.vcs = GitController()
        except git.InvalidGitRepositoryError:
            self.vcs = None
            print("⚠️ GuardianAgent: Gitリポジトリが見つからないため、コミット機能は無効です。")

    def review_and_commit(self, code_draft: str, test_code: str, test_result: str, testimony: str, constitution: str, task_description: str, changed_files: list, debug_info: dict = None):
        """
        コードをレビューし、承認された場合にのみコミットを実行する。
        """
        print("\n--- GuardianAgent (CTO): 最終レビューとコミット判断を開始 ---")

        # ★★★★★ 修正点2: プロンプトの構造をSYSTEM_PROMPTと分離 ★★★★★
        prompt = f"""
# レビュー対象の情報
- **プロジェクト憲法**: {constitution}
- **元のタスク**: {task_description}
- **提出コード**:
```python
{code_draft}
```
- **テストコード**:
```python
{test_code}
```
- **テスト結果**:
```
{test_result}
```
- **開発者の証言**: {testimony}

# あなたへの指示
上記の情報に基づき、このコード変更を承認するかを判断してください。

# 出力要件
- 必ず `decision` (`APPROVE`または`REJECT`) と `reason` (判断理由) を含むJSON形式で出力してください。
- REJECTする場合、`feedback_for_coder` キーに具体的な修正指示を含めてください。
"""
        # ★★★★★ 修正点3: 'invoke' を正しい '_call_llm' に修正し、JSON出力を指定 ★★★★★
        review_result_json = self._call_llm(prompt, self.SYSTEM_PROMPT, as_json=True)
        
        try:
            review_data = json.loads(review_result_json)
        except json.JSONDecodeError:
            print("❌ GuardianAgentのレビュー出力が不正なJSONでした。")
            return {"decision": "REJECT", "reason": "Invalid JSON response from Guardian."}

        decision = review_data.get("decision", "REJECT")
        reason = review_data.get("reason", "理由不明。")
        print(f"判断: {decision}")
        print(f"理由: {reason}")
        
        if decision == "REJECT":
            review_data["feedback_for_coder"] = review_data.get("feedback_for_coder", reason)
            return review_data

        if self.vcs:
            commit_message = self._generate_commit_message(review_data, changed_files, debug_info)
            commit_hash = self.vcs.commit_changes(changed_files, commit_message)
            
            if commit_hash:
                review_data["commit"] = commit_hash
            else:
                review_data["commit"] = "Commit failed or no changes detected."
        else:
            review_data["commit"] = "Git repository not available."
            
        return review_data


    def _generate_commit_message(self, review_data: dict, changed_files: list, debug_info: dict = None) -> str:
        """
        Conventional Commits形式に準拠したコミットメッセージを生成する。
        """
        scope = "auto"
        body = f"Reviewed by: GuardianAgent (Model: {self.model})\n"
        body += f"Reason for approval: {review_data.get('reason', 'N/A')}\n"

        if debug_info:
            commit_type = "fix"
            header = f"{commit_type}({scope}): Self-healed by DebuggerAgent"
            body += f"\n[DEBUGGER ACTIVITY]\n"
            body += f"Error Signature: {debug_info.get('error_signature', 'N/A')}\n"
            solution_type = debug_info.get('solution_pattern', {}).get('type', 'N/A')
            body += f"Applied Solution Type: {solution_type}\n"
        else:
            commit_type = "feat"
            header = f"{commit_type}({scope}): Implemented new functionality via CoderAgent"
        
        return f"{header}\n\n{body}"

# === NexusCore/data_collection\Local-Code-Interpreter\src\cli.py ===
from response_parser import *
import copy
import json
from tqdm import tqdm
import logging
import argparse
import os

def initialization(state_dict: Dict) -> None:
    if not os.path.exists('cache'):
        os.mkdir('cache')
    if state_dict["bot_backend"] is None:
        state_dict["bot_backend"] = BotBackend()
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']

def get_bot_backend(state_dict: Dict) -> BotBackend:
    return state_dict["bot_backend"]

def switch_to_gpt4(state_dict: Dict, whether_switch: bool) -> None:
    bot_backend = get_bot_backend(state_dict)
    if whether_switch:
        bot_backend.update_gpt_model_choice("GPT-4")
    else:
        bot_backend.update_gpt_model_choice("GPT-3.5")

def add_text(state_dict, history, text):
    bot_backend = get_bot_backend(state_dict)
    bot_backend.add_text_message(user_text=text)
    history = history + [[text, None]]
    return history, state_dict

def bot(state_dict, history):
    bot_backend = get_bot_backend(state_dict)
    while bot_backend.finish_reason in ('new_input', 'function_call'):
        if history[-1][1]:
            history.append([None, ""])
        else:
            history[-1][1] = ""
        logging.info("Start chat completion")
        response = chat_completion(bot_backend=bot_backend)
        logging.info(f"End chat completion, response: {response}")

        logging.info("Start parse response")
        history, _ = parse_response(
            chunk=response,
            history=history,
            bot_backend=bot_backend
        )
        logging.info("End parse response")
    return history

def main(state, history, user_input):
    history, state = add_text(state, history, user_input)
    last_history = copy.deepcopy(history)
    first_turn_flag = False
    while True:
        if first_turn_flag:
            switch_to_gpt4(state, False)
            first_turn_flag = False
        else:
            switch_to_gpt4(state, True)
        logging.info("Start bot")
        history = bot(state, history)
        logging.info("End bot")
        print(state["bot_backend"].conversation)
        if last_history == copy.deepcopy(history):
            logging.info("No new response, end conversation")
            conversation = [item for item in state["bot_backend"].conversation if item["content"]]
            return conversation
        else:
            logging.info("New response, continue conversation")
            last_history = copy.deepcopy(history)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_path', type=str)
    parser.add_argument('--output_path', type=str)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logging.info("Initialization")

    state = {"bot_backend": None}
    history = []

    initialization(state)
    switch_to_gpt4(state_dict=state, whether_switch=True)

    logging.info("Start")
    with open(args.input_path, "r") as f:
        instructions = [json.loads(line)["query"] for line in f.readlines()]
    all_history = []
    logging.info(f"{len(instructions)} remaining instructions for {args.input_path}")

    for user_input_index, user_input in enumerate(tqdm(instructions)):
        logging.info(f"Start conversation {user_input_index}")
        conversation = main(state, history, user_input)
        all_history.append(
            {
                "instruction": user_input,
                "conversation": conversation
            }
        )
        with open(f"{args.output_path}", "w") as f:
            json.dump(all_history, f, indent=4, ensure_ascii=False)
        state["bot_backend"].restart()
        

# === NexusCore/data_collection\Local-Code-Interpreter\src\jupyter_backend.py ===
import jupyter_client
import re


def delete_color_control_char(string):
    ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
    return ansi_escape.sub('', string)


class JupyterKernel:
    def __init__(self, work_dir):
        self.kernel_manager, self.kernel_client = jupyter_client.manager.start_new_kernel(kernel_name='python3')
        self.work_dir = work_dir
        self.interrupt_signal = False
        self._create_work_dir()
        self.available_functions = {
            'execute_code': self.execute_code,
            'python': self.execute_code
        }

    def execute_code_(self, code):
        msg_id = self.kernel_client.execute(code)

        # Get the output of the code
        msg_list = []
        while True:
            try:
                iopub_msg = self.kernel_client.get_iopub_msg(timeout=1)
                msg_list.append(iopub_msg)
                if iopub_msg['msg_type'] == 'status' and iopub_msg['content'].get('execution_state') == 'idle':
                    break
            except:
                if self.interrupt_signal:
                    self.kernel_manager.interrupt_kernel()
                    self.interrupt_signal = False
                continue

        all_output = []
        for iopub_msg in msg_list:
            if iopub_msg['msg_type'] == 'stream':
                if iopub_msg['content'].get('name') == 'stdout':
                    output = iopub_msg['content']['text']
                    all_output.append(('stdout', output))
            elif iopub_msg['msg_type'] == 'execute_result':
                if 'data' in iopub_msg['content']:
                    if 'text/plain' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['text/plain']
                        all_output.append(('execute_result_text', output))
                    if 'text/html' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['text/html']
                        all_output.append(('execute_result_html', output))
                    if 'image/png' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['image/png']
                        all_output.append(('execute_result_png', output))
                    if 'image/jpeg' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['image/jpeg']
                        all_output.append(('execute_result_jpeg', output))
            elif iopub_msg['msg_type'] == 'display_data':
                if 'data' in iopub_msg['content']:
                    if 'text/plain' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['text/plain']
                        all_output.append(('display_text', output))
                    if 'text/html' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['text/html']
                        all_output.append(('display_html', output))
                    if 'image/png' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['image/png']
                        all_output.append(('display_png', output))
                    if 'image/jpeg' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['image/jpeg']
                        all_output.append(('display_jpeg', output))
            elif iopub_msg['msg_type'] == 'error':
                if 'traceback' in iopub_msg['content']:
                    output = '\n'.join(iopub_msg['content']['traceback'])
                    all_output.append(('error', output))

        return all_output

    def execute_code(self, code):
        text_to_gpt = []
        content_to_display = self.execute_code_(code)
        for mark, out_str in content_to_display:
            if mark in ('stdout', 'execute_result_text', 'display_text'):
                text_to_gpt.append(out_str)
            elif mark in ('execute_result_png', 'execute_result_jpeg', 'display_png', 'display_jpeg'):
                text_to_gpt.append('[image]')
            elif mark == 'error':
                text_to_gpt.append(delete_color_control_char(out_str))

        return '\n'.join(text_to_gpt), content_to_display

    def _create_work_dir(self):
        # set work dir in jupyter environment
        init_code = f"import os\n" \
                    f"if not os.path.exists('{self.work_dir}'):\n" \
                    f"    os.mkdir('{self.work_dir}')\n" \
                    f"os.chdir('{self.work_dir}')\n" \
                    f"del os"
        self.execute_code_(init_code)

    def send_interrupt_signal(self):
        self.interrupt_signal = True

    def restart_jupyter_kernel(self):
        self.kernel_client.shutdown()
        self.kernel_manager, self.kernel_client = jupyter_client.manager.start_new_kernel(kernel_name='python3')
        self.interrupt_signal = False
        self._create_work_dir()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\data_collection\Local-Code-Interpreter\src\cli.py ===
from response_parser import *
import copy
import json
from tqdm import tqdm
import logging
import argparse
import os

def initialization(state_dict: Dict) -> None:
    if not os.path.exists('cache'):
        os.mkdir('cache')
    if state_dict["bot_backend"] is None:
        state_dict["bot_backend"] = BotBackend()
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']

def get_bot_backend(state_dict: Dict) -> BotBackend:
    return state_dict["bot_backend"]

def switch_to_gpt4(state_dict: Dict, whether_switch: bool) -> None:
    bot_backend = get_bot_backend(state_dict)
    if whether_switch:
        bot_backend.update_gpt_model_choice("GPT-4")
    else:
        bot_backend.update_gpt_model_choice("GPT-3.5")

def add_text(state_dict, history, text):
    bot_backend = get_bot_backend(state_dict)
    bot_backend.add_text_message(user_text=text)
    history = history + [[text, None]]
    return history, state_dict

def bot(state_dict, history):
    bot_backend = get_bot_backend(state_dict)
    while bot_backend.finish_reason in ('new_input', 'function_call'):
        if history[-1][1]:
            history.append([None, ""])
        else:
            history[-1][1] = ""
        logging.info("Start chat completion")
        response = chat_completion(bot_backend=bot_backend)
        logging.info(f"End chat completion, response: {response}")

        logging.info("Start parse response")
        history, _ = parse_response(
            chunk=response,
            history=history,
            bot_backend=bot_backend
        )
        logging.info("End parse response")
    return history

def main(state, history, user_input):
    history, state = add_text(state, history, user_input)
    last_history = copy.deepcopy(history)
    first_turn_flag = False
    while True:
        if first_turn_flag:
            switch_to_gpt4(state, False)
            first_turn_flag = False
        else:
            switch_to_gpt4(state, True)
        logging.info("Start bot")
        history = bot(state, history)
        logging.info("End bot")
        print(state["bot_backend"].conversation)
        if last_history == copy.deepcopy(history):
            logging.info("No new response, end conversation")
            conversation = [item for item in state["bot_backend"].conversation if item["content"]]
            return conversation
        else:
            logging.info("New response, continue conversation")
            last_history = copy.deepcopy(history)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_path', type=str)
    parser.add_argument('--output_path', type=str)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logging.info("Initialization")

    state = {"bot_backend": None}
    history = []

    initialization(state)
    switch_to_gpt4(state_dict=state, whether_switch=True)

    logging.info("Start")
    with open(args.input_path, "r") as f:
        instructions = [json.loads(line)["query"] for line in f.readlines()]
    all_history = []
    logging.info(f"{len(instructions)} remaining instructions for {args.input_path}")

    for user_input_index, user_input in enumerate(tqdm(instructions)):
        logging.info(f"Start conversation {user_input_index}")
        conversation = main(state, history, user_input)
        all_history.append(
            {
                "instruction": user_input,
                "conversation": conversation
            }
        )
        with open(f"{args.output_path}", "w") as f:
            json.dump(all_history, f, indent=4, ensure_ascii=False)
        state["bot_backend"].restart()
        

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\data_collection\Local-Code-Interpreter\src\jupyter_backend.py ===
import jupyter_client
import re


def delete_color_control_char(string):
    ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
    return ansi_escape.sub('', string)


class JupyterKernel:
    def __init__(self, work_dir):
        self.kernel_manager, self.kernel_client = jupyter_client.manager.start_new_kernel(kernel_name='python3')
        self.work_dir = work_dir
        self.interrupt_signal = False
        self._create_work_dir()
        self.available_functions = {
            'execute_code': self.execute_code,
            'python': self.execute_code
        }

    def execute_code_(self, code):
        msg_id = self.kernel_client.execute(code)

        # Get the output of the code
        msg_list = []
        while True:
            try:
                iopub_msg = self.kernel_client.get_iopub_msg(timeout=1)
                msg_list.append(iopub_msg)
                if iopub_msg['msg_type'] == 'status' and iopub_msg['content'].get('execution_state') == 'idle':
                    break
            except:
                if self.interrupt_signal:
                    self.kernel_manager.interrupt_kernel()
                    self.interrupt_signal = False
                continue

        all_output = []
        for iopub_msg in msg_list:
            if iopub_msg['msg_type'] == 'stream':
                if iopub_msg['content'].get('name') == 'stdout':
                    output = iopub_msg['content']['text']
                    all_output.append(('stdout', output))
            elif iopub_msg['msg_type'] == 'execute_result':
                if 'data' in iopub_msg['content']:
                    if 'text/plain' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['text/plain']
                        all_output.append(('execute_result_text', output))
                    if 'text/html' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['text/html']
                        all_output.append(('execute_result_html', output))
                    if 'image/png' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['image/png']
                        all_output.append(('execute_result_png', output))
                    if 'image/jpeg' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['image/jpeg']
                        all_output.append(('execute_result_jpeg', output))
            elif iopub_msg['msg_type'] == 'display_data':
                if 'data' in iopub_msg['content']:
                    if 'text/plain' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['text/plain']
                        all_output.append(('display_text', output))
                    if 'text/html' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['text/html']
                        all_output.append(('display_html', output))
                    if 'image/png' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['image/png']
                        all_output.append(('display_png', output))
                    if 'image/jpeg' in iopub_msg['content']['data']:
                        output = iopub_msg['content']['data']['image/jpeg']
                        all_output.append(('display_jpeg', output))
            elif iopub_msg['msg_type'] == 'error':
                if 'traceback' in iopub_msg['content']:
                    output = '\n'.join(iopub_msg['content']['traceback'])
                    all_output.append(('error', output))

        return all_output

    def execute_code(self, code):
        text_to_gpt = []
        content_to_display = self.execute_code_(code)
        for mark, out_str in content_to_display:
            if mark in ('stdout', 'execute_result_text', 'display_text'):
                text_to_gpt.append(out_str)
            elif mark in ('execute_result_png', 'execute_result_jpeg', 'display_png', 'display_jpeg'):
                text_to_gpt.append('[image]')
            elif mark == 'error':
                text_to_gpt.append(delete_color_control_char(out_str))

        return '\n'.join(text_to_gpt), content_to_display

    def _create_work_dir(self):
        # set work dir in jupyter environment
        init_code = f"import os\n" \
                    f"if not os.path.exists('{self.work_dir}'):\n" \
                    f"    os.mkdir('{self.work_dir}')\n" \
                    f"os.chdir('{self.work_dir}')\n" \
                    f"del os"
        self.execute_code_(init_code)

    def send_interrupt_signal(self):
        self.interrupt_signal = True

    def restart_jupyter_kernel(self):
        self.kernel_client.shutdown()
        self.kernel_manager, self.kernel_client = jupyter_client.manager.start_new_kernel(kernel_name='python3')
        self.interrupt_signal = False
        self._create_work_dir()

# === NexusCore/src\agents\knowledge_curator_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: knowledge_curator_agent.py
# メモ: 【情報伝達修正版】検証プロセスにおいて、PostmortemAgentが分析した
#      のと同一の「生のエラーログ」をDebuggerAgentに引き継ぐように修正。
# ==============================================================================
import os
import shutil
import tempfile
import logging
import json
import subprocess
import sys
from pathlib import Path

from .debugger_agent import DebuggerAgent
from .patch_applier import PatchApplier

class KnowledgeCuratorAgent:
    def __init__(self, api_key: str, model: str):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.api_key = api_key
        self.model = model

    def validate_fkb_suggestion(
        self,
        suggestion: dict,
        original_project_path: str,
        failed_test_path: str,
        related_source_path: str,
        # ▼▼▼▼▼ 【最重要修正点】生のテスト失敗ログを追加 ▼▼▼▼▼
        original_test_output: str
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
    ) -> bool:
        """
        提案されたFKBエントリを一時的なサンドボックス環境で検証する。
        """
        self.logger.info(f"Starting validation for FKB suggestion: {suggestion.get('id', 'N/A')}")
        
        with tempfile.TemporaryDirectory(prefix="k_curator_") as sandbox_path:
            try:
                # 1. プロジェクトの関連ファイルのみをサンドボックスにコピー
                self.logger.debug(f"Creating minimal sandbox at: {sandbox_path}")
                
                # 必要なディレクトリ構造を作成
                Path(sandbox_path, os.path.dirname(os.path.relpath(related_source_path, original_project_path))).mkdir(parents=True, exist_ok=True)
                Path(sandbox_path, os.path.dirname(os.path.relpath(failed_test_path, original_project_path))).mkdir(parents=True, exist_ok=True)

                # 関連ファイルのみをコピー
                shutil.copy(related_source_path, os.path.join(sandbox_path, os.path.relpath(related_source_path, original_project_path)))
                shutil.copy(failed_test_path, os.path.join(sandbox_path, os.path.relpath(failed_test_path, original_project_path)))
                
                # __init__.pyを作成
                for dirpath, _, _ in os.walk(sandbox_path):
                    Path(dirpath, "__init__.py").touch()

                # 2. 一時的なFKBを作成
                temp_fkb_path = os.path.join(sandbox_path, "temp_fkb.json")
                with open(temp_fkb_path, 'w', encoding='utf-8') as f:
                    json.dump([suggestion], f, ensure_ascii=False, indent=2)
                self.logger.debug("Created temporary FKB with new suggestion.")

                # 3. サンドボックス内でDebuggerAgentを初期化
                debugger = DebuggerAgent(self.api_key, self.model, knowledge_base_path=temp_fkb_path, project_path=sandbox_path)
                patcher = PatchApplier()

                # 4. 自己修復を試行
                # ▼▼▼▼▼ 【最重要修正点】サンドボックス内でテストを再実行するのではなく、元のエラーログを使用 ▼▼▼▼▼
                files_context = {
                    "source_file": os.path.join(sandbox_path, os.path.relpath(related_source_path, original_project_path)),
                    "test_file": os.path.join(sandbox_path, os.path.relpath(failed_test_path, original_project_path))
                }
                debug_result = debugger.debug(original_test_output, files_context)
                # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

                if not (debug_result and debug_result.get("patch")):
                    self.logger.warning("Validation failed: Debugger did not generate a patch with the new knowledge.")
                    return False

                # 5. パッチを適用し、テストが成功するか確認
                was_applied = patcher.apply(debug_result["patch"], sandbox_path)
                if not was_applied:
                    self.logger.warning("Validation failed: Generated patch could not be applied.")
                    return False

                tests_passed, _ = self._run_tests_in_sandbox(sandbox_path, os.path.relpath(failed_test_path, original_project_path))
                if tests_passed:
                    self.logger.info("✅ Validation successful! The new knowledge correctly fixed the bug.")
                    return True
                else:
                    self.logger.warning("Validation failed: Tests still fail after applying the patch.")
                    return False

            except Exception as e:
                self.logger.error(f"An error occurred during validation: {e}", exc_info=True)
                return False

    def _run_tests_in_sandbox(self, sandbox_path: str, test_file_rel_path: str) -> tuple[bool, str]:
        """サンドボックス内でpytestを実行する"""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file_rel_path],
            cwd=sandbox_path,
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        output = result.stdout + "\n" + result.stderr
        return result.returncode == 0, output

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\knowledge_curator_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: knowledge_curator_agent.py
# メモ: 【情報伝達修正版】検証プロセスにおいて、PostmortemAgentが分析した
#      のと同一の「生のエラーログ」をDebuggerAgentに引き継ぐように修正。
# ==============================================================================
import os
import shutil
import tempfile
import logging
import json
import subprocess
import sys
from pathlib import Path

from .debugger_agent import DebuggerAgent
from .patch_applier import PatchApplier

class KnowledgeCuratorAgent:
    def __init__(self, api_key: str, model: str):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.api_key = api_key
        self.model = model

    def validate_fkb_suggestion(
        self,
        suggestion: dict,
        original_project_path: str,
        failed_test_path: str,
        related_source_path: str,
        # ▼▼▼▼▼ 【最重要修正点】生のテスト失敗ログを追加 ▼▼▼▼▼
        original_test_output: str
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
    ) -> bool:
        """
        提案されたFKBエントリを一時的なサンドボックス環境で検証する。
        """
        self.logger.info(f"Starting validation for FKB suggestion: {suggestion.get('id', 'N/A')}")
        
        with tempfile.TemporaryDirectory(prefix="k_curator_") as sandbox_path:
            try:
                # 1. プロジェクトの関連ファイルのみをサンドボックスにコピー
                self.logger.debug(f"Creating minimal sandbox at: {sandbox_path}")
                
                # 必要なディレクトリ構造を作成
                Path(sandbox_path, os.path.dirname(os.path.relpath(related_source_path, original_project_path))).mkdir(parents=True, exist_ok=True)
                Path(sandbox_path, os.path.dirname(os.path.relpath(failed_test_path, original_project_path))).mkdir(parents=True, exist_ok=True)

                # 関連ファイルのみをコピー
                shutil.copy(related_source_path, os.path.join(sandbox_path, os.path.relpath(related_source_path, original_project_path)))
                shutil.copy(failed_test_path, os.path.join(sandbox_path, os.path.relpath(failed_test_path, original_project_path)))
                
                # __init__.pyを作成
                for dirpath, _, _ in os.walk(sandbox_path):
                    Path(dirpath, "__init__.py").touch()

                # 2. 一時的なFKBを作成
                temp_fkb_path = os.path.join(sandbox_path, "temp_fkb.json")
                with open(temp_fkb_path, 'w', encoding='utf-8') as f:
                    json.dump([suggestion], f, ensure_ascii=False, indent=2)
                self.logger.debug("Created temporary FKB with new suggestion.")

                # 3. サンドボックス内でDebuggerAgentを初期化
                debugger = DebuggerAgent(self.api_key, self.model, knowledge_base_path=temp_fkb_path, project_path=sandbox_path)
                patcher = PatchApplier()

                # 4. 自己修復を試行
                # ▼▼▼▼▼ 【最重要修正点】サンドボックス内でテストを再実行するのではなく、元のエラーログを使用 ▼▼▼▼▼
                files_context = {
                    "source_file": os.path.join(sandbox_path, os.path.relpath(related_source_path, original_project_path)),
                    "test_file": os.path.join(sandbox_path, os.path.relpath(failed_test_path, original_project_path))
                }
                debug_result = debugger.debug(original_test_output, files_context)
                # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

                if not (debug_result and debug_result.get("patch")):
                    self.logger.warning("Validation failed: Debugger did not generate a patch with the new knowledge.")
                    return False

                # 5. パッチを適用し、テストが成功するか確認
                was_applied = patcher.apply(debug_result["patch"], sandbox_path)
                if not was_applied:
                    self.logger.warning("Validation failed: Generated patch could not be applied.")
                    return False

                tests_passed, _ = self._run_tests_in_sandbox(sandbox_path, os.path.relpath(failed_test_path, original_project_path))
                if tests_passed:
                    self.logger.info("✅ Validation successful! The new knowledge correctly fixed the bug.")
                    return True
                else:
                    self.logger.warning("Validation failed: Tests still fail after applying the patch.")
                    return False

            except Exception as e:
                self.logger.error(f"An error occurred during validation: {e}", exc_info=True)
                return False

    def _run_tests_in_sandbox(self, sandbox_path: str, test_file_rel_path: str) -> tuple[bool, str]:
        """サンドボックス内でpytestを実行する"""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file_rel_path],
            cwd=sandbox_path,
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        output = result.stdout + "\n" + result.stderr
        return result.returncode == 0, output

# === NexusCore/src\realtime_whisper.py ===
# ファイル名例: realtime_whisper.py
# 必要なライブラリ: sounddevice, numpy, noisereduce, librosa, soundfile, openai, scipy
# インストール例:
# pip install sounddevice numpy noisereduce librosa soundfile openai scipy

import sounddevice as sd
import numpy as np
import threading
import time
import noisereduce as nr
import librosa
import soundfile as sf
import tempfile
import openai
from scipy.io.wavfile import write
import os

# Whisper APIキーは環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- メモ ---
# 1. エンターキーで録音終了、最大60秒まで録音
# 2. 録音後、ノイズリダクション＋音量正規化を自動実行
# 3. Whisper APIで日本語文字起こし
# 4. 一時ファイルは自動削除

def record_and_process_audio(max_duration=60, sample_rate=16000):
    print(f"録音開始: 最大{max_duration}秒、エンターキーで終了")
    recording = []
    event = threading.Event()
    start_time = time.time()

    def callback(indata, frames, t, status):
        if time.time() - start_time > max_duration:
            event.set()
            raise sd.CallbackAbort
        recording.append(indata.copy())

    def record_thread():
        with sd.InputStream(samplerate=sample_rate, channels=1, callback=callback):
            event.wait()

    def key_thread():
        input()  # エンターキー待ち
        event.set()

    t1 = threading.Thread(target=record_thread)
    t2 = threading.Thread(target=key_thread)
    t1.start()
    t2.start()
    t2.join(timeout=max_duration)
    t1.join(timeout=1)

    if not recording:
        return None

    audio_np = np.concatenate(recording, axis=0).flatten()

    # 一時ファイルに保存
    temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    write(temp_wav.name, sample_rate, audio_np)

    # ノイズ除去・音量正規化処理
    y, sr = librosa.load(temp_wav.name, sr=sample_rate)
    noise_sample = y[:int(sr*0.5)]  # 最初の0.5秒をノイズと仮定
    y_denoised = nr.reduce_noise(y=y, y_noise=noise_sample, sr=sr, stationary=False)
    y_normalized = librosa.util.normalize(y_denoised)

    # 処理後の音声を別ファイルに保存
    processed_wav = tempfile.NamedTemporaryFile(suffix='_processed.wav', delete=False)
    sf.write(processed_wav.name, y_normalized, sr)

    # 元の録音ファイルは削除
    temp_wav.close()
    os.unlink(temp_wav.name)

    return processed_wav.name

def transcribe_with_whisper(audio_path):
    with open(audio_path, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ja",
            response_format="text"
        )
    return transcript

if __name__ == '__main__':
    wav_path = record_and_process_audio(max_duration=60)
    if wav_path:
        print("録音・前処理完了、Whisperで文字起こし中...")
        text = transcribe_with_whisper(wav_path)
        print("認識結果:")
        print(text)
        os.unlink(wav_path)  # 処理後ファイル削除
    else:
        print("録音がキャンセルされました、または音声がありませんでした。")

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\realtime_whisper.py ===
# ファイル名例: realtime_whisper.py
# 必要なライブラリ: sounddevice, numpy, noisereduce, librosa, soundfile, openai, scipy
# インストール例:
# pip install sounddevice numpy noisereduce librosa soundfile openai scipy

import sounddevice as sd
import numpy as np
import threading
import time
import noisereduce as nr
import librosa
import soundfile as sf
import tempfile
import openai
from scipy.io.wavfile import write
import os

# Whisper APIキーは環境変数から取得
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- メモ ---
# 1. エンターキーで録音終了、最大60秒まで録音
# 2. 録音後、ノイズリダクション＋音量正規化を自動実行
# 3. Whisper APIで日本語文字起こし
# 4. 一時ファイルは自動削除

def record_and_process_audio(max_duration=60, sample_rate=16000):
    print(f"録音開始: 最大{max_duration}秒、エンターキーで終了")
    recording = []
    event = threading.Event()
    start_time = time.time()

    def callback(indata, frames, t, status):
        if time.time() - start_time > max_duration:
            event.set()
            raise sd.CallbackAbort
        recording.append(indata.copy())

    def record_thread():
        with sd.InputStream(samplerate=sample_rate, channels=1, callback=callback):
            event.wait()

    def key_thread():
        input()  # エンターキー待ち
        event.set()

    t1 = threading.Thread(target=record_thread)
    t2 = threading.Thread(target=key_thread)
    t1.start()
    t2.start()
    t2.join(timeout=max_duration)
    t1.join(timeout=1)

    if not recording:
        return None

    audio_np = np.concatenate(recording, axis=0).flatten()

    # 一時ファイルに保存
    temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    write(temp_wav.name, sample_rate, audio_np)

    # ノイズ除去・音量正規化処理
    y, sr = librosa.load(temp_wav.name, sr=sample_rate)
    noise_sample = y[:int(sr*0.5)]  # 最初の0.5秒をノイズと仮定
    y_denoised = nr.reduce_noise(y=y, y_noise=noise_sample, sr=sr, stationary=False)
    y_normalized = librosa.util.normalize(y_denoised)

    # 処理後の音声を別ファイルに保存
    processed_wav = tempfile.NamedTemporaryFile(suffix='_processed.wav', delete=False)
    sf.write(processed_wav.name, y_normalized, sr)

    # 元の録音ファイルは削除
    temp_wav.close()
    os.unlink(temp_wav.name)

    return processed_wav.name

def transcribe_with_whisper(audio_path):
    with open(audio_path, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ja",
            response_format="text"
        )
    return transcript

if __name__ == '__main__':
    wav_path = record_and_process_audio(max_duration=60)
    if wav_path:
        print("録音・前処理完了、Whisperで文字起こし中...")
        text = transcribe_with_whisper(wav_path)
        print("認識結果:")
        print(text)
        os.unlink(wav_path)  # 処理後ファイル削除
    else:
        print("録音がキャンセルされました、または音声がありませんでした。")

# === NexusCore/src\utils\code_analyzer.py ===
# src/utils/code_analyzer.py

import subprocess
import re
import json

def run_pylint(file_path: str) -> float:
    """指定されたファイルに対してPylintを実行し、スコアを返す"""
    print(f"🔬 Running Pylint on {file_path}...")
    command = ["pylint", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout
        match = re.search(r"Your code has been rated at (\d+\.\d+)/10", output)
        if match:
            score = float(match.group(1))
            print(f"✅ Pylint score: {score}/10")
            return score
        print(f"⚠️ Pylint score not found in output.")
        return 0.0
    except Exception as e:
        print(f"🚨 An error occurred while running Pylint: {e}")
        return 0.0

def run_mypy(file_path: str) -> tuple[bool, str]:
    """指定されたファイルに対してMyPyを実行し、(成功フラグ, 結果メッセージ)を返す"""
    print(f"🔬 Running MyPy on {file_path}...")
    command = ["mypy", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        if "Success: no issues found" in output:
            print("✅ MyPy found no issues.")
            return True, "Passed"
        else:
            error_summary = "\n".join(line for line in output.splitlines() if "error:" in line)
            print(f"❌ MyPy found issues.")
            return False, error_summary
    except Exception as e:
        print(f"🚨 An error occurred while running MyPy: {e}")
        return False, str(e)

def run_bandit(target_path: str) -> tuple[bool, str]:
    """指定されたパスに対してBanditを実行し、(成功フラグ, 結果メッセージ)を返す"""
    print(f"🔬 Running Bandit security scan on {target_path}...")
    command = ["bandit", "-r", target_path, "-f", "json"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        report = json.loads(result.stdout)
        high_medium_issues = [
            f"- {res['issue_text']} (Severity: {res['issue_severity']}, File: {res['filename']}:{res['line_number']})"
            for res in report["results"]
            if res["issue_severity"] in ["HIGH", "MEDIUM"]
        ]
        if not high_medium_issues:
            print("✅ Bandit: No high or medium severity issues found.")
            return True, "Passed"
        else:
            issue_summary = "\n".join(high_medium_issues)
            print("❌ Bandit found security issues.")
            return False, issue_summary
    except json.JSONDecodeError:
        print("✅ Bandit: No security issues reported.")
        return True, "Passed"
    except Exception as e:
        print(f"🚨 An error occurred while running Bandit: {e}")
        return False, str(e)

def run_pytest_cov(project_path: str) -> float:
    """
    指定されたプロジェクトパスを基準にテストとカバレッジ計測を実行する。
    設定はpyproject.tomlから読み込まれる。
    """
    print(f"🔬 Running pytest-cov on {project_path}...")
    # 設定ファイルがあるので、コマンドはシンプルに 'pytest' だけで良い
    command = ["pytest"]
    try:
        # cwdを指定して、対象プロジェクトのルートでコマンドを実行する
        result = subprocess.run(
            command,
            cwd=project_path,  # これが重要！
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        output = result.stdout
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if match:
            coverage = float(match.group(1))
            print(f"✅ Pytest-cov coverage: {coverage}%")
            return coverage
        print(f"⚠️ Pytest-cov coverage not found. Output:\n{output}")
        return 0.0
    except Exception as e:
        print(f"🚨 An error occurred while running pytest-cov: {e}")
        return 0.0

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\code_analyzer.py ===
# src/utils/code_analyzer.py

import subprocess
import re
import json

def run_pylint(file_path: str) -> float:
    """指定されたファイルに対してPylintを実行し、スコアを返す"""
    print(f"🔬 Running Pylint on {file_path}...")
    command = ["pylint", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout
        match = re.search(r"Your code has been rated at (\d+\.\d+)/10", output)
        if match:
            score = float(match.group(1))
            print(f"✅ Pylint score: {score}/10")
            return score
        print(f"⚠️ Pylint score not found in output.")
        return 0.0
    except Exception as e:
        print(f"🚨 An error occurred while running Pylint: {e}")
        return 0.0

def run_mypy(file_path: str) -> tuple[bool, str]:
    """指定されたファイルに対してMyPyを実行し、(成功フラグ, 結果メッセージ)を返す"""
    print(f"🔬 Running MyPy on {file_path}...")
    command = ["mypy", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        if "Success: no issues found" in output:
            print("✅ MyPy found no issues.")
            return True, "Passed"
        else:
            error_summary = "\n".join(line for line in output.splitlines() if "error:" in line)
            print(f"❌ MyPy found issues.")
            return False, error_summary
    except Exception as e:
        print(f"🚨 An error occurred while running MyPy: {e}")
        return False, str(e)

def run_bandit(target_path: str) -> tuple[bool, str]:
    """指定されたパスに対してBanditを実行し、(成功フラグ, 結果メッセージ)を返す"""
    print(f"🔬 Running Bandit security scan on {target_path}...")
    command = ["bandit", "-r", target_path, "-f", "json"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        report = json.loads(result.stdout)
        high_medium_issues = [
            f"- {res['issue_text']} (Severity: {res['issue_severity']}, File: {res['filename']}:{res['line_number']})"
            for res in report["results"]
            if res["issue_severity"] in ["HIGH", "MEDIUM"]
        ]
        if not high_medium_issues:
            print("✅ Bandit: No high or medium severity issues found.")
            return True, "Passed"
        else:
            issue_summary = "\n".join(high_medium_issues)
            print("❌ Bandit found security issues.")
            return False, issue_summary
    except json.JSONDecodeError:
        print("✅ Bandit: No security issues reported.")
        return True, "Passed"
    except Exception as e:
        print(f"🚨 An error occurred while running Bandit: {e}")
        return False, str(e)

def run_pytest_cov(project_path: str) -> float:
    """
    指定されたプロジェクトパスを基準にテストとカバレッジ計測を実行する。
    設定はpyproject.tomlから読み込まれる。
    """
    print(f"🔬 Running pytest-cov on {project_path}...")
    # 設定ファイルがあるので、コマンドはシンプルに 'pytest' だけで良い
    command = ["pytest"]
    try:
        # cwdを指定して、対象プロジェクトのルートでコマンドを実行する
        result = subprocess.run(
            command,
            cwd=project_path,  # これが重要！
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        output = result.stdout
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if match:
            coverage = float(match.group(1))
            print(f"✅ Pytest-cov coverage: {coverage}%")
            return coverage
        print(f"⚠️ Pytest-cov coverage not found. Output:\n{output}")
        return 0.0
    except Exception as e:
        print(f"🚨 An error occurred while running pytest-cov: {e}")
        return 0.0

# === NexusCore/src\utils\config.py ===
# フォルダ: src/utils
# ファイル名: config.py
# メモ: プロジェクト全体の設定値（APIキー、秘密鍵、データベース接続情報など）を
#      一元管理するためのファイルです。すべての設定はここから読み込みます。

import os
from dotenv import load_dotenv

# プロジェクトのルートにある.envファイルを読み込む
# このファイルの場所から2階層上のディレクトリをルートと仮定
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """
    環境変数から設定を読み込むための設定クラス。
    アプリケーション全体でこのクラスのインスタンスをインポートして使用します。
    """
    # --- OpenAI API ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")# フォルダ: src/utils
# ファイル名: config.py
# メモ: プロジェクト全体の設定値（APIキー、秘密鍵、データベース接続情報など）を
#      一元管理するためのファイルです。すべての設定はここから読み込みます。

import os
from dotenv import load_dotenv

# プロジェクトのルートにある.envファイルを読み込む
# このファイルの場所から2階層上のディレクトリをルートと仮定
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """
    環境変数から設定を読み込むための設定クラス。
    アプリケーション全体でこのクラスのインスタンスをインポートして使用します。
    """
    # --- OpenAI API ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # --- Gemini API (Multi-Agent System) ---
    # ◀️ マルチエージェントシステム用のAPIキーを追加
    # エージェントA（生成役）用のキー
    GEMINI_API_KEY_AGENT_A = os.getenv("GEMINI_API_KEY_AGENT_A")
    # エージェントB（批評・改善役）用のキー
    GEMINI_API_KEY_AGENT_B = os.getenv("GEMINI_API_KEY_AGENT_B")


    # --- Flask Application ---
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # --- Database ---
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")
    
    # --- Celery (for background tasks) ---
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# アプリケーション全体で共有するためのConfigクラスのインスタンス
config = Config()

# APIキーが設定されていない場合に警告を表示
if not config.OPENAI_API_KEY:
    print("⚠️ 警告: OPENAI_API_KEYが.envファイルに設定されていません。")

# ◀️ Gemini APIキーの警告を追加
if not config.GEMINI_API_KEY_AGENT_A or not config.GEMINI_API_KEY_AGENT_B:
    print("⚠️ 警告: マルチエージェント用のGEMINI_API_KEYが設定されていません。")



    # --- Flask Application ---
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # --- Database ---
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")
    
    # --- Celery (for background tasks) ---
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# アプリケーション全体で共有するためのConfigクラスのインスタンス
config = Config()

# APIキーが設定されていない場合に警告を表示
if not config.OPENAI_API_KEY:
    print("⚠️ 警告: OPENAI_API_KEYが.envファイルに設定されていません。")


# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\config.py ===
# フォルダ: src/utils
# ファイル名: config.py
# メモ: プロジェクト全体の設定値（APIキー、秘密鍵、データベース接続情報など）を
#      一元管理するためのファイルです。すべての設定はここから読み込みます。

import os
from dotenv import load_dotenv

# プロジェクトのルートにある.envファイルを読み込む
# このファイルの場所から2階層上のディレクトリをルートと仮定
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """
    環境変数から設定を読み込むための設定クラス。
    アプリケーション全体でこのクラスのインスタンスをインポートして使用します。
    """
    # --- OpenAI API ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")# フォルダ: src/utils
# ファイル名: config.py
# メモ: プロジェクト全体の設定値（APIキー、秘密鍵、データベース接続情報など）を
#      一元管理するためのファイルです。すべての設定はここから読み込みます。

import os
from dotenv import load_dotenv

# プロジェクトのルートにある.envファイルを読み込む
# このファイルの場所から2階層上のディレクトリをルートと仮定
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """
    環境変数から設定を読み込むための設定クラス。
    アプリケーション全体でこのクラスのインスタンスをインポートして使用します。
    """
    # --- OpenAI API ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # --- Gemini API (Multi-Agent System) ---
    # ◀️ マルチエージェントシステム用のAPIキーを追加
    # エージェントA（生成役）用のキー
    GEMINI_API_KEY_AGENT_A = os.getenv("GEMINI_API_KEY_AGENT_A")
    # エージェントB（批評・改善役）用のキー
    GEMINI_API_KEY_AGENT_B = os.getenv("GEMINI_API_KEY_AGENT_B")


    # --- Flask Application ---
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # --- Database ---
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")
    
    # --- Celery (for background tasks) ---
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# アプリケーション全体で共有するためのConfigクラスのインスタンス
config = Config()

# APIキーが設定されていない場合に警告を表示
if not config.OPENAI_API_KEY:
    print("⚠️ 警告: OPENAI_API_KEYが.envファイルに設定されていません。")

# ◀️ Gemini APIキーの警告を追加
if not config.GEMINI_API_KEY_AGENT_A or not config.GEMINI_API_KEY_AGENT_B:
    print("⚠️ 警告: マルチエージェント用のGEMINI_API_KEYが設定されていません。")



    # --- Flask Application ---
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # --- Database ---
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")
    
    # --- Celery (for background tasks) ---
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# アプリケーション全体で共有するためのConfigクラスのインスタンス
config = Config()

# APIキーが設定されていない場合に警告を表示
if not config.OPENAI_API_KEY:
    print("⚠️ 警告: OPENAI_API_KEYが.envファイルに設定されていません。")


# === NexusCore/src\streamlit_legacy.py ===
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import io

# 音声録音用
from streamlit_mic_recorder import mic_recorder

# .envファイルからAPIキーを読み込む
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

st.title("ChatGPT風チャット＋音声入力＋ファイルアップロード")

# セッションステートでチャット履歴を管理
if "messages" not in st.session_state:
    st.session_state.messages = []

# ファイルアップロード
uploaded_files = st.file_uploader("ファイルをアップロード（複数可）", accept_multiple_files=True)
if uploaded_files:
    for file in uploaded_files:
        st.write(f"アップロード: {file.name}")
        # テキストファイルは内容表示
        if file.type.startswith("text"):
            content = file.read().decode("utf-8", errors="ignore")
            st.text_area(f"{file.name}の内容", content, height=100)
        # バイナリの場合はファイル名のみ表示

# 音声入力（録音）
st.subheader("音声入力（録音→Whisperで文字起こし）")
audio_data = mic_recorder(
    start_prompt="録音開始",
    stop_prompt="録音停止",
    format="webm",
    key="mic"
)

if audio_data:
    st.audio(audio_data["bytes"], format="audio/webm")
    audio_bytes_io = io.BytesIO(audio_data["bytes"])
    audio_bytes_io.name = "audio.webm"
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_bytes_io,
            language="ja"
        )
        st.success("文字起こし結果:")
        st.write(transcript.text)
        # 文字起こし結果をチャット履歴に追加
        st.session_state.messages.append({"role": "user", "content": transcript.text})
    except Exception as e:
        st.error(f"文字起こしエラー: {e}")

# チャット履歴の表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ユーザーからの入力受付
if prompt := st.chat_input("メッセージを入力してください"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # OpenAI APIでAI応答をストリーミング生成
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたは有能なアシスタントです。"},
            *st.session_state.messages
        ],
        stream=True
    )

    with st.chat_message("assistant"):
        full_response = ""
        placeholder = st.empty()
        for chunk in response:
            content = getattr(chunk.choices[0].delta, "content", None)
            if content:
                full_response += content
                placeholder.markdown(full_response + "▌")
        placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})

# === NexusCore/healing_sandbox\src\agents\base_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: base_agent.py
# メモ: すべてのエージェントが自身のクラス名を冠した専用ロガーを持つように
#      アーキテクチャをアップグレード。
# ==============================================================================
import json
import logging # ロギングをインポート
from openai import OpenAI
import google.generativeai as genai

class BaseAgent:
    def __init__(self, api_key: str, model: str):
        # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
        # 自分自身のクラス名をロガー名として、専用のロガーインスタンスを取得
        self.logger = logging.getLogger(self.__class__.__name__)
        # --- ★★★★★ ここまで ★★★★★ ---

        self.model = model
        self.client = None
        self.provider = None

        if "gpt" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("GPTモデルを使用するには、有効なOpenAI APIキーが必要です。")
            self.client = OpenAI(api_key=api_key)
            self.provider = "openai"
            self.logger.info(f"OpenAI client initialized for model: {self.model}")

        elif "gemini" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("Geminiモデルを使用するには、有効なGoogle APIキーが必要です。")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            self.provider = "google"
            self.logger.info(f"Google Gemini client initialized for model: {self.model}")

        elif "dummy" in model.lower():
            self.provider = "dummy"
            self.logger.info("BaseAgent initialized in DUMMY mode for testing. No API client will be used.")
        
        else:
            raise ValueError(f"Unsupported or unknown model specified: {self.model}. Must contain 'gpt', 'gemini', or 'dummy'.")

    def _call_llm(self, prompt: str, system_prompt: str, temperature: float = 0.1, as_json: bool = False) -> str:
        """
        プロバイダーに応じて適切なLLM呼び出しメソッドを振り分ける。
        """
        self.logger.debug(f"Calling LLM. Provider: {self.provider}, JSON mode: {as_json}")
        if self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temperature, as_json)
        elif self.provider == "google":
            return self._call_gemini(prompt, system_prompt, temperature, as_json)
        elif self.provider == "dummy":
            self.logger.warning("LLM call attempted in DUMMY mode. Returning empty string.")
            return json.dumps({"response": "dummy response"}) if as_json else "dummy response"
        else:
            self.logger.error(f"LLM provider '{self.provider}' is not implemented.")
            raise NotImplementedError(f"LLM provider '{self.provider}' is not implemented.")

    def _call_openai(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        response_format = {"type": "json_object"} if as_json else {"type": "text"}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format=response_format
        )
        return response.choices[0].message.content.strip()

    def _call_gemini(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json" if as_json else "text/plain"
        )
        full_prompt = f"{system_prompt}\\n\\n---\\n\\n{prompt}"
        
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        return response.text.strip()

# === NexusCore/src\agents\base_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: base_agent.py
# メモ: すべてのエージェントが自身のクラス名を冠した専用ロガーを持つように
#      アーキテクチャをアップグレード。
# ==============================================================================
import json
import logging # ロギングをインポート
from openai import OpenAI
import google.generativeai as genai

class BaseAgent:
    def __init__(self, api_key: str, model: str):
        # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
        # 自分自身のクラス名をロガー名として、専用のロガーインスタンスを取得
        self.logger = logging.getLogger(self.__class__.__name__)
        # --- ★★★★★ ここまで ★★★★★ ---

        self.model = model
        self.client = None
        self.provider = None

        if "gpt" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("GPTモデルを使用するには、有効なOpenAI APIキーが必要です。")
            self.client = OpenAI(api_key=api_key)
            self.provider = "openai"
            self.logger.info(f"OpenAI client initialized for model: {self.model}")

        elif "gemini" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("Geminiモデルを使用するには、有効なGoogle APIキーが必要です。")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            self.provider = "google"
            self.logger.info(f"Google Gemini client initialized for model: {self.model}")

        elif "dummy" in model.lower():
            self.provider = "dummy"
            self.logger.info("BaseAgent initialized in DUMMY mode for testing. No API client will be used.")
        
        else:
            raise ValueError(f"Unsupported or unknown model specified: {self.model}. Must contain 'gpt', 'gemini', or 'dummy'.")

    def _call_llm(self, prompt: str, system_prompt: str, temperature: float = 0.1, as_json: bool = False) -> str:
        """
        プロバイダーに応じて適切なLLM呼び出しメソッドを振り分ける。
        """
        self.logger.debug(f"Calling LLM. Provider: {self.provider}, JSON mode: {as_json}")
        if self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temperature, as_json)
        elif self.provider == "google":
            return self._call_gemini(prompt, system_prompt, temperature, as_json)
        elif self.provider == "dummy":
            self.logger.warning("LLM call attempted in DUMMY mode. Returning empty string.")
            return json.dumps({"response": "dummy response"}) if as_json else "dummy response"
        else:
            self.logger.error(f"LLM provider '{self.provider}' is not implemented.")
            raise NotImplementedError(f"LLM provider '{self.provider}' is not implemented.")

    def _call_openai(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        response_format = {"type": "json_object"} if as_json else {"type": "text"}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format=response_format
        )
        return response.choices[0].message.content.strip()

    def _call_gemini(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json" if as_json else "text/plain"
        )
        full_prompt = f"{system_prompt}\\n\\n---\\n\\n{prompt}"
        
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        return response.text.strip()

# === NexusCore/src\agents\policy_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: policy_agent.py
# メモ: テスト成功後、Guardianのレビュー前に介入する品質ゲート。
#      BaseAgentを継承し、既存アーキテクチャに準拠。
# ==============================================================================

import json
import re
from .base_agent import BaseAgent

class PolicyAgent(BaseAgent):
    """
    コードが事前に定義されたポリシー（規約）に準拠しているかを監査するエージェント。
    LLMを呼び出さず、設定ファイルに基づいて機械的にチェックを行う。
    """
    def __init__(self, api_key: str, model: str, policy_rules_path: str = "config/policy_rules.json"):
        """
        PolicyAgentを初期化する。
        LLMは使用しないが、BaseAgentのインターフェースに合わせるため引数を受け取る。
        """
        # BaseAgentの初期化を呼び出し、主にロガーをセットアップ
        super().__init__(api_key, model)
        
        try:
            with open(policy_rules_path, 'r', encoding='utf-8') as f:
                self.policies = json.load(f)
            self.logger.info(f"Loaded {len(self.policies)} policies from {policy_rules_path}")
        except FileNotFoundError:
            self.logger.error(f"Policy rules file not found at: {policy_rules_path}. No policies will be enforced.")
            self.policies = []
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON from {policy_rules_path}. Check for syntax errors.")
            self.policies = []


    def audit(self, files_to_check: list) -> dict:
        """
        与えられたファイル群を監査し、監査結果を返す。

        Args:
            files_to_check (list): ファイルパスとコンテンツを含む辞書のリスト。
                                  例: [{"path": "app/main.py", "content": "..."}]

        Returns:
            dict: 監査結果。'result'キーに'APPROVED'または'REJECTED'、
                  'violations'キーに違反リストが含まれる。
        """
        all_violations = []
        self.logger.info(f"Starting policy audit for {len(files_to_check)} file(s)...")

        if not self.policies:
            self.logger.warning("No policies loaded. Skipping audit and approving by default.")
            return {"result": "APPROVED", "violations": []}

        for file_info in files_to_check:
            file_path = file_info.get("path")
            content = file_info.get("content")
            if not file_path or content is None:
                continue

            for policy in self.policies:
                # ポリシーに必要なキーが存在するかチェック
                if not all(k in policy for k in ["policy_id", "detection_pattern", "severity", "description"]):
                    self.logger.warning(f"Skipping malformed policy: {policy.get('policy_id', 'N/A')}")
                    continue

                # ターゲットファイルパターンに一致するかチェック
                if re.search(policy.get("target_file_pattern", ".*"), file_path):
                    for i, line in enumerate(content.splitlines()):
                        if re.search(policy["detection_pattern"], line):
                            violation = {
                                "file_path": file_path,
                                "line_number": i + 1,
                                "policy_id": policy["policy_id"],
                                "severity": policy["severity"],
                                "description": policy["description"],
                                "suggestion": policy.get("suggestion", "No specific suggestion.")
                            }
                            all_violations.append(violation)
                            self.logger.warning(f"Policy violation found: {violation}")

        result = "APPROVED" if not all_violations else "REJECTED"
        self.logger.info(f"Policy audit finished. Result: {result}, Violations: {len(all_violations)}")
        
        return {
            "result": result,
            "violations": all_violations
        }

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\streamlit_legacy.py ===
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import io

# 音声録音用
from streamlit_mic_recorder import mic_recorder

# .envファイルからAPIキーを読み込む
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

st.title("ChatGPT風チャット＋音声入力＋ファイルアップロード")

# セッションステートでチャット履歴を管理
if "messages" not in st.session_state:
    st.session_state.messages = []

# ファイルアップロード
uploaded_files = st.file_uploader("ファイルをアップロード（複数可）", accept_multiple_files=True)
if uploaded_files:
    for file in uploaded_files:
        st.write(f"アップロード: {file.name}")
        # テキストファイルは内容表示
        if file.type.startswith("text"):
            content = file.read().decode("utf-8", errors="ignore")
            st.text_area(f"{file.name}の内容", content, height=100)
        # バイナリの場合はファイル名のみ表示

# 音声入力（録音）
st.subheader("音声入力（録音→Whisperで文字起こし）")
audio_data = mic_recorder(
    start_prompt="録音開始",
    stop_prompt="録音停止",
    format="webm",
    key="mic"
)

if audio_data:
    st.audio(audio_data["bytes"], format="audio/webm")
    audio_bytes_io = io.BytesIO(audio_data["bytes"])
    audio_bytes_io.name = "audio.webm"
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_bytes_io,
            language="ja"
        )
        st.success("文字起こし結果:")
        st.write(transcript.text)
        # 文字起こし結果をチャット履歴に追加
        st.session_state.messages.append({"role": "user", "content": transcript.text})
    except Exception as e:
        st.error(f"文字起こしエラー: {e}")

# チャット履歴の表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ユーザーからの入力受付
if prompt := st.chat_input("メッセージを入力してください"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # OpenAI APIでAI応答をストリーミング生成
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたは有能なアシスタントです。"},
            *st.session_state.messages
        ],
        stream=True
    )

    with st.chat_message("assistant"):
        full_response = ""
        placeholder = st.empty()
        for chunk in response:
            content = getattr(chunk.choices[0].delta, "content", None)
            if content:
                full_response += content
                placeholder.markdown(full_response + "▌")
        placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\healing_sandbox\src\agents\base_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: base_agent.py
# メモ: すべてのエージェントが自身のクラス名を冠した専用ロガーを持つように
#      アーキテクチャをアップグレード。
# ==============================================================================
import json
import logging # ロギングをインポート
from openai import OpenAI
import google.generativeai as genai

class BaseAgent:
    def __init__(self, api_key: str, model: str):
        # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
        # 自分自身のクラス名をロガー名として、専用のロガーインスタンスを取得
        self.logger = logging.getLogger(self.__class__.__name__)
        # --- ★★★★★ ここまで ★★★★★ ---

        self.model = model
        self.client = None
        self.provider = None

        if "gpt" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("GPTモデルを使用するには、有効なOpenAI APIキーが必要です。")
            self.client = OpenAI(api_key=api_key)
            self.provider = "openai"
            self.logger.info(f"OpenAI client initialized for model: {self.model}")

        elif "gemini" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("Geminiモデルを使用するには、有効なGoogle APIキーが必要です。")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            self.provider = "google"
            self.logger.info(f"Google Gemini client initialized for model: {self.model}")

        elif "dummy" in model.lower():
            self.provider = "dummy"
            self.logger.info("BaseAgent initialized in DUMMY mode for testing. No API client will be used.")
        
        else:
            raise ValueError(f"Unsupported or unknown model specified: {self.model}. Must contain 'gpt', 'gemini', or 'dummy'.")

    def _call_llm(self, prompt: str, system_prompt: str, temperature: float = 0.1, as_json: bool = False) -> str:
        """
        プロバイダーに応じて適切なLLM呼び出しメソッドを振り分ける。
        """
        self.logger.debug(f"Calling LLM. Provider: {self.provider}, JSON mode: {as_json}")
        if self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temperature, as_json)
        elif self.provider == "google":
            return self._call_gemini(prompt, system_prompt, temperature, as_json)
        elif self.provider == "dummy":
            self.logger.warning("LLM call attempted in DUMMY mode. Returning empty string.")
            return json.dumps({"response": "dummy response"}) if as_json else "dummy response"
        else:
            self.logger.error(f"LLM provider '{self.provider}' is not implemented.")
            raise NotImplementedError(f"LLM provider '{self.provider}' is not implemented.")

    def _call_openai(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        response_format = {"type": "json_object"} if as_json else {"type": "text"}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format=response_format
        )
        return response.choices[0].message.content.strip()

    def _call_gemini(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json" if as_json else "text/plain"
        )
        full_prompt = f"{system_prompt}\\n\\n---\\n\\n{prompt}"
        
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        return response.text.strip()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\base_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: base_agent.py
# メモ: すべてのエージェントが自身のクラス名を冠した専用ロガーを持つように
#      アーキテクチャをアップグレード。
# ==============================================================================
import json
import logging # ロギングをインポート
from openai import OpenAI
import google.generativeai as genai

class BaseAgent:
    def __init__(self, api_key: str, model: str):
        # --- ★★★★★ ここからが最重要修正点 ★★★★★ ---
        # 自分自身のクラス名をロガー名として、専用のロガーインスタンスを取得
        self.logger = logging.getLogger(self.__class__.__name__)
        # --- ★★★★★ ここまで ★★★★★ ---

        self.model = model
        self.client = None
        self.provider = None

        if "gpt" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("GPTモデルを使用するには、有効なOpenAI APIキーが必要です。")
            self.client = OpenAI(api_key=api_key)
            self.provider = "openai"
            self.logger.info(f"OpenAI client initialized for model: {self.model}")

        elif "gemini" in model.lower():
            if not api_key or api_key == "dummy_key":
                raise ValueError("Geminiモデルを使用するには、有効なGoogle APIキーが必要です。")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            self.provider = "google"
            self.logger.info(f"Google Gemini client initialized for model: {self.model}")

        elif "dummy" in model.lower():
            self.provider = "dummy"
            self.logger.info("BaseAgent initialized in DUMMY mode for testing. No API client will be used.")
        
        else:
            raise ValueError(f"Unsupported or unknown model specified: {self.model}. Must contain 'gpt', 'gemini', or 'dummy'.")

    def _call_llm(self, prompt: str, system_prompt: str, temperature: float = 0.1, as_json: bool = False) -> str:
        """
        プロバイダーに応じて適切なLLM呼び出しメソッドを振り分ける。
        """
        self.logger.debug(f"Calling LLM. Provider: {self.provider}, JSON mode: {as_json}")
        if self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temperature, as_json)
        elif self.provider == "google":
            return self._call_gemini(prompt, system_prompt, temperature, as_json)
        elif self.provider == "dummy":
            self.logger.warning("LLM call attempted in DUMMY mode. Returning empty string.")
            return json.dumps({"response": "dummy response"}) if as_json else "dummy response"
        else:
            self.logger.error(f"LLM provider '{self.provider}' is not implemented.")
            raise NotImplementedError(f"LLM provider '{self.provider}' is not implemented.")

    def _call_openai(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        response_format = {"type": "json_object"} if as_json else {"type": "text"}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format=response_format
        )
        return response.choices[0].message.content.strip()

    def _call_gemini(self, prompt: str, system_prompt: str, temperature: float, as_json: bool) -> str:
        # (実装は変更なし)
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json" if as_json else "text/plain"
        )
        full_prompt = f"{system_prompt}\\n\\n---\\n\\n{prompt}"
        
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        return response.text.strip()

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\agents\policy_agent.py ===
# ==============================================================================
# フォルダ: src/agents
# ファイル名: policy_agent.py
# メモ: テスト成功後、Guardianのレビュー前に介入する品質ゲート。
#      BaseAgentを継承し、既存アーキテクチャに準拠。
# ==============================================================================

import json
import re
from .base_agent import BaseAgent

class PolicyAgent(BaseAgent):
    """
    コードが事前に定義されたポリシー（規約）に準拠しているかを監査するエージェント。
    LLMを呼び出さず、設定ファイルに基づいて機械的にチェックを行う。
    """
    def __init__(self, api_key: str, model: str, policy_rules_path: str = "config/policy_rules.json"):
        """
        PolicyAgentを初期化する。
        LLMは使用しないが、BaseAgentのインターフェースに合わせるため引数を受け取る。
        """
        # BaseAgentの初期化を呼び出し、主にロガーをセットアップ
        super().__init__(api_key, model)
        
        try:
            with open(policy_rules_path, 'r', encoding='utf-8') as f:
                self.policies = json.load(f)
            self.logger.info(f"Loaded {len(self.policies)} policies from {policy_rules_path}")
        except FileNotFoundError:
            self.logger.error(f"Policy rules file not found at: {policy_rules_path}. No policies will be enforced.")
            self.policies = []
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON from {policy_rules_path}. Check for syntax errors.")
            self.policies = []


    def audit(self, files_to_check: list) -> dict:
        """
        与えられたファイル群を監査し、監査結果を返す。

        Args:
            files_to_check (list): ファイルパスとコンテンツを含む辞書のリスト。
                                  例: [{"path": "app/main.py", "content": "..."}]

        Returns:
            dict: 監査結果。'result'キーに'APPROVED'または'REJECTED'、
                  'violations'キーに違反リストが含まれる。
        """
        all_violations = []
        self.logger.info(f"Starting policy audit for {len(files_to_check)} file(s)...")

        if not self.policies:
            self.logger.warning("No policies loaded. Skipping audit and approving by default.")
            return {"result": "APPROVED", "violations": []}

        for file_info in files_to_check:
            file_path = file_info.get("path")
            content = file_info.get("content")
            if not file_path or content is None:
                continue

            for policy in self.policies:
                # ポリシーに必要なキーが存在するかチェック
                if not all(k in policy for k in ["policy_id", "detection_pattern", "severity", "description"]):
                    self.logger.warning(f"Skipping malformed policy: {policy.get('policy_id', 'N/A')}")
                    continue

                # ターゲットファイルパターンに一致するかチェック
                if re.search(policy.get("target_file_pattern", ".*"), file_path):
                    for i, line in enumerate(content.splitlines()):
                        if re.search(policy["detection_pattern"], line):
                            violation = {
                                "file_path": file_path,
                                "line_number": i + 1,
                                "policy_id": policy["policy_id"],
                                "severity": policy["severity"],
                                "description": policy["description"],
                                "suggestion": policy.get("suggestion", "No specific suggestion.")
                            }
                            all_violations.append(violation)
                            self.logger.warning(f"Policy violation found: {violation}")

        result = "APPROVED" if not all_violations else "REJECTED"
        self.logger.info(f"Policy audit finished. Result: {result}, Violations: {len(all_violations)}")
        
        return {
            "result": result,
            "violations": all_violations
        }

# === NexusCore/src\utils\const.py ===
TOOLS_CODE = """
import numpy as np
import pandas as pd 
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import os,sys
import re
from datetime import datetime
from sympy import symbols, Eq, solve
import torch 
import requests
from bs4 import BeautifulSoup
import json
import math
import yfinance
import time
"""

write_denial_function = 'lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("Writing to disk operation is not permitted due to safety reasons. Please do not try again!"))'
read_denial_function = 'lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("Reading from disk operation is not permitted due to safety reasons. Please do not try again!"))'
class_denial = """Class Denial:
    def __getattr__(self, name):
        def method(*args, **kwargs):
            return "Using this class is not permitted due to safety reasons. Please do not try again!"
        return method
"""

GUARD_CODE = f"""
import os

os.kill = {write_denial_function}
os.system = {write_denial_function}
os.putenv = {write_denial_function}
os.remove = {write_denial_function}
os.removedirs = {write_denial_function}
os.rmdir = {write_denial_function}
os.fchdir = {write_denial_function}
os.setuid = {write_denial_function}
os.fork = {write_denial_function}
os.forkpty = {write_denial_function}
os.killpg = {write_denial_function}
os.rename = {write_denial_function}
os.renames = {write_denial_function}
os.truncate = {write_denial_function}
os.replace = {write_denial_function}
os.unlink = {write_denial_function}
os.fchmod = {write_denial_function}
os.fchown = {write_denial_function}
os.chmod = {write_denial_function}
os.chown = {write_denial_function}
os.chroot = {write_denial_function}
os.fchdir = {write_denial_function}
os.lchflags = {write_denial_function}
os.lchmod = {write_denial_function}
os.lchown = {write_denial_function}
os.getcwd = {write_denial_function}
os.chdir = {write_denial_function}
os.popen = {write_denial_function}

import shutil

shutil.rmtree = {write_denial_function}
shutil.move = {write_denial_function}
shutil.chown = {write_denial_function}

import subprocess

subprocess.Popen = {write_denial_function}  # type: ignore

import sys

sys.modules["ipdb"] = {write_denial_function}
sys.modules["joblib"] = {write_denial_function}
sys.modules["resource"] = {write_denial_function}
sys.modules["psutil"] = {write_denial_function}
sys.modules["tkinter"] = {write_denial_function}
"""

CODE_INTERPRETER_SYSTEM_PROMPT = """You are an AI code interpreter.
Your goal is to help users do a variety of jobs by executing Python code.

You should:
1. Comprehend the user's requirements carefully & to the letter.
2. Give a brief description for what you plan to do & call the provided function to run code.
3. Provide results analysis based on the execution output.
4. If error occurred, try to fix it.
5. Response in the same language as the user."""

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\utils\const.py ===
TOOLS_CODE = """
import numpy as np
import pandas as pd 
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import os,sys
import re
from datetime import datetime
from sympy import symbols, Eq, solve
import torch 
import requests
from bs4 import BeautifulSoup
import json
import math
import yfinance
import time
"""

write_denial_function = 'lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("Writing to disk operation is not permitted due to safety reasons. Please do not try again!"))'
read_denial_function = 'lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("Reading from disk operation is not permitted due to safety reasons. Please do not try again!"))'
class_denial = """Class Denial:
    def __getattr__(self, name):
        def method(*args, **kwargs):
            return "Using this class is not permitted due to safety reasons. Please do not try again!"
        return method
"""

GUARD_CODE = f"""
import os

os.kill = {write_denial_function}
os.system = {write_denial_function}
os.putenv = {write_denial_function}
os.remove = {write_denial_function}
os.removedirs = {write_denial_function}
os.rmdir = {write_denial_function}
os.fchdir = {write_denial_function}
os.setuid = {write_denial_function}
os.fork = {write_denial_function}
os.forkpty = {write_denial_function}
os.killpg = {write_denial_function}
os.rename = {write_denial_function}
os.renames = {write_denial_function}
os.truncate = {write_denial_function}
os.replace = {write_denial_function}
os.unlink = {write_denial_function}
os.fchmod = {write_denial_function}
os.fchown = {write_denial_function}
os.chmod = {write_denial_function}
os.chown = {write_denial_function}
os.chroot = {write_denial_function}
os.fchdir = {write_denial_function}
os.lchflags = {write_denial_function}
os.lchmod = {write_denial_function}
os.lchown = {write_denial_function}
os.getcwd = {write_denial_function}
os.chdir = {write_denial_function}
os.popen = {write_denial_function}

import shutil

shutil.rmtree = {write_denial_function}
shutil.move = {write_denial_function}
shutil.chown = {write_denial_function}

import subprocess

subprocess.Popen = {write_denial_function}  # type: ignore

import sys

sys.modules["ipdb"] = {write_denial_function}
sys.modules["joblib"] = {write_denial_function}
sys.modules["resource"] = {write_denial_function}
sys.modules["psutil"] = {write_denial_function}
sys.modules["tkinter"] = {write_denial_function}
"""

CODE_INTERPRETER_SYSTEM_PROMPT = """You are an AI code interpreter.
Your goal is to help users do a variety of jobs by executing Python code.

You should:
1. Comprehend the user's requirements carefully & to the letter.
2. Give a brief description for what you plan to do & call the provided function to run code.
3. Provide results analysis based on the execution output.
4. If error occurred, try to fix it.
5. Response in the same language as the user."""

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_io.py ===
import gc
import gzip
import locale
import os
import re
import sys
import threading
import time
import warnings
from ctypes import c_bool
from datetime import datetime
from io import BytesIO, StringIO
from multiprocessing import Value, get_context
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

import numpy as np
import numpy.ma as ma
from numpy._utils import asbytes
from numpy.exceptions import VisibleDeprecationWarning
from numpy.lib import _npyio_impl
from numpy.lib._iotools import ConversionWarning, ConverterError
from numpy.lib._npyio_impl import recfromcsv, recfromtxt
from numpy.ma.testutils import assert_equal
from numpy.testing import (
    HAS_REFCOUNT,
    IS_PYPY,
    IS_WASM,
    assert_,
    assert_allclose,
    assert_array_equal,
    assert_no_gc_cycles,
    assert_no_warnings,
    assert_raises,
    assert_raises_regex,
    assert_warns,
    break_cycles,
    suppress_warnings,
    tempdir,
    temppath,
)
from numpy.testing._private.utils import requires_memory


class TextIO(BytesIO):
    """Helper IO class.

    Writes encode strings to bytes if needed, reads return bytes.
    This makes it easier to emulate files opened in binary mode
    without needing to explicitly convert strings to bytes in
    setting up the test data.

    """
    def __init__(self, s=""):
        BytesIO.__init__(self, asbytes(s))

    def write(self, s):
        BytesIO.write(self, asbytes(s))

    def writelines(self, lines):
        BytesIO.writelines(self, [asbytes(s) for s in lines])


IS_64BIT = sys.maxsize > 2**32
try:
    import bz2
    HAS_BZ2 = True
except ImportError:
    HAS_BZ2 = False
try:
    import lzma
    HAS_LZMA = True
except ImportError:
    HAS_LZMA = False


def strptime(s, fmt=None):
    """
    This function is available in the datetime module only from Python >=
    2.5.

    """
    if isinstance(s, bytes):
        s = s.decode("latin1")
    return datetime(*time.strptime(s, fmt)[:3])


class RoundtripTest:
    def roundtrip(self, save_func, *args, **kwargs):
        """
        save_func : callable
            Function used to save arrays to file.
        file_on_disk : bool
            If true, store the file on disk, instead of in a
            string buffer.
        save_kwds : dict
            Parameters passed to `save_func`.
        load_kwds : dict
            Parameters passed to `numpy.load`.
        args : tuple of arrays
            Arrays stored to file.

        """
        save_kwds = kwargs.get('save_kwds', {})
        load_kwds = kwargs.get('load_kwds', {"allow_pickle": True})
        file_on_disk = kwargs.get('file_on_disk', False)

        if file_on_disk:
            target_file = NamedTemporaryFile(delete=False)
            load_file = target_file.name
        else:
            target_file = BytesIO()
            load_file = target_file

        try:
            arr = args

            save_func(target_file, *arr, **save_kwds)
            target_file.flush()
            target_file.seek(0)

            if sys.platform == 'win32' and not isinstance(target_file, BytesIO):
                target_file.close()

            arr_reloaded = np.load(load_file, **load_kwds)

            self.arr = arr
            self.arr_reloaded = arr_reloaded
        finally:
            if not isinstance(target_file, BytesIO):
                target_file.close()
                # holds an open file descriptor so it can't be deleted on win
                if 'arr_reloaded' in locals():
                    if not isinstance(arr_reloaded, np.lib.npyio.NpzFile):
                        os.remove(target_file.name)

    def check_roundtrips(self, a):
        self.roundtrip(a)
        self.roundtrip(a, file_on_disk=True)
        self.roundtrip(np.asfortranarray(a))
        self.roundtrip(np.asfortranarray(a), file_on_disk=True)
        if a.shape[0] > 1:
            # neither C nor Fortran contiguous for 2D arrays or more
            self.roundtrip(np.asfortranarray(a)[1:])
            self.roundtrip(np.asfortranarray(a)[1:], file_on_disk=True)

    def test_array(self):
        a = np.array([], float)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], float)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], int)
        self.check_roundtrips(a)

        a = np.array([[1 + 5j, 2 + 6j], [3 + 7j, 4 + 8j]], dtype=np.csingle)
        self.check_roundtrips(a)

        a = np.array([[1 + 5j, 2 + 6j], [3 + 7j, 4 + 8j]], dtype=np.cdouble)
        self.check_roundtrips(a)

    def test_array_object(self):
        a = np.array([], object)
        self.check_roundtrips(a)

        a = np.array([[1, 2], [3, 4]], object)
        self.check_roundtrips(a)

    def test_1D(self):
        a = np.array([1, 2, 3, 4], int)
        self.roundtrip(a)

    @pytest.mark.skipif(sys.platform == 'win32', reason="Fails on Win32")
    def test_mmap(self):
        a = np.array([[1, 2.5], [4, 7.3]])
        self.roundtrip(a, file_on_disk=True, load_kwds={'mmap_mode': 'r'})

        a = np.asfortranarray([[1, 2.5], [4, 7.3]])
        self.roundtrip(a, file_on_disk=True, load_kwds={'mmap_mode': 'r'})

    def test_record(self):
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        self.check_roundtrips(a)

    @pytest.mark.slow
    def test_format_2_0(self):
        dt = [(("%d" % i) * 100, float) for i in range(500)]
        a = np.ones(1000, dtype=dt)
        with warnings.catch_warnings(record=True):
            warnings.filterwarnings('always', '', UserWarning)
            self.check_roundtrips(a)


class TestSaveLoad(RoundtripTest):
    def roundtrip(self, *args, **kwargs):
        RoundtripTest.roundtrip(self, np.save, *args, **kwargs)
        assert_equal(self.arr[0], self.arr_reloaded)
        assert_equal(self.arr[0].dtype, self.arr_reloaded.dtype)
        assert_equal(self.arr[0].flags.fnc, self.arr_reloaded.flags.fnc)


class TestSavezLoad(RoundtripTest):
    def roundtrip(self, *args, **kwargs):
        RoundtripTest.roundtrip(self, np.savez, *args, **kwargs)
        try:
            for n, arr in enumerate(self.arr):
                reloaded = self.arr_reloaded['arr_%d' % n]
                assert_equal(arr, reloaded)
                assert_equal(arr.dtype, reloaded.dtype)
                assert_equal(arr.flags.fnc, reloaded.flags.fnc)
        finally:
            # delete tempfile, must be done here on windows
            if self.arr_reloaded.fid:
                self.arr_reloaded.fid.close()
                os.remove(self.arr_reloaded.fid.name)

    @pytest.mark.skipif(IS_PYPY, reason="Hangs on PyPy")
    @pytest.mark.skipif(not IS_64BIT, reason="Needs 64bit platform")
    @pytest.mark.slow
    def test_big_arrays(self):
        L = (1 << 31) + 100000
        a = np.empty(L, dtype=np.uint8)
        with temppath(prefix="numpy_test_big_arrays_", suffix=".npz") as tmp:
            np.savez(tmp, a=a)
            del a
            npfile = np.load(tmp)
            a = npfile['a']  # Should succeed
            npfile.close()

    def test_multiple_arrays(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        self.roundtrip(a, b)

    def test_named_arrays(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        c = BytesIO()
        np.savez(c, file_a=a, file_b=b)
        c.seek(0)
        l = np.load(c)
        assert_equal(a, l['file_a'])
        assert_equal(b, l['file_b'])

    def test_tuple_getitem_raises(self):
        # gh-23748
        a = np.array([1, 2, 3])
        f = BytesIO()
        np.savez(f, a=a)
        f.seek(0)
        l = np.load(f)
        with pytest.raises(KeyError, match="(1, 2)"):
            l[1, 2]

    def test_BagObj(self):
        a = np.array([[1, 2], [3, 4]], float)
        b = np.array([[1 + 2j, 2 + 7j], [3 - 6j, 4 + 12j]], complex)
        c = BytesIO()
        np.savez(c, file_a=a, file_b=b)
        c.seek(0)
        l = np.load(c)
        assert_equal(sorted(dir(l.f)), ['file_a', 'file_b'])
        assert_equal(a, l.f.file_a)
        assert_equal(b, l.f.file_b)

    @pytest.mark.skipif(IS_WASM, reason="Cannot start thread")
    def test_savez_filename_clashes(self):
        # Test that issue #852 is fixed
        # and savez functions in multithreaded environment

        def writer(error_list):
            with temppath(suffix='.npz') as tmp:
                arr = np.random.randn(500, 500)
                try:
                    np.savez(tmp, arr=arr)
                except OSError as err:
                    error_list.append(err)

        errors = []
        threads = [threading.Thread(target=writer, args=(errors,))
                   for j in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if errors:
            raise AssertionError(errors)

    def test_not_closing_opened_fid(self):
        # Test that issue #2178 is fixed:
        # verify could seek on 'loaded' file
        with temppath(suffix='.npz') as tmp:
            with open(tmp, 'wb') as fp:
                np.savez(fp, data='LOVELY LOAD')
            with open(tmp, 'rb', 10000) as fp:
                fp.seek(0)
                assert_(not fp.closed)
                np.load(fp)['data']
                # fp must not get closed by .load
                assert_(not fp.closed)
                fp.seek(0)
                assert_(not fp.closed)

    @pytest.mark.slow_pypy
    def test_closing_fid(self):
        # Test that issue #1517 (too many opened files) remains closed
        # It might be a "weak" test since failed to get triggered on
        # e.g. Debian sid of 2012 Jul 05 but was reported to
        # trigger the failure on Ubuntu 10.04:
        # http://projects.scipy.org/numpy/ticket/1517#comment:2
        with temppath(suffix='.npz') as tmp:
            np.savez(tmp, data='LOVELY LOAD')
            # We need to check if the garbage collector can properly close
            # numpy npz file returned by np.load when their reference count
            # goes to zero.  Python running in debug mode raises a
            # ResourceWarning when file closing is left to the garbage
            # collector, so we catch the warnings.
            with suppress_warnings() as sup:
                sup.filter(ResourceWarning)  # TODO: specify exact message
                for i in range(1, 1025):
                    try:
                        np.load(tmp)["data"]
                    except Exception as e:
                        msg = f"Failed to load data from a file: {e}"
                        raise AssertionError(msg)
                    finally:
                        if IS_PYPY:
                            gc.collect()

    def test_closing_zipfile_after_load(self):
        # Check that zipfile owns file and can close it.  This needs to
        # pass a file name to load for the test. On windows failure will
        # cause a second error will be raised when the attempt to remove
        # the open file is made.
        prefix = 'numpy_test_closing_zipfile_after_load_'
        with temppath(suffix='.npz', prefix=prefix) as tmp:
            np.savez(tmp, lab='place holder')
            data = np.load(tmp)
            fp = data.zip.fp
            data.close()
            assert_(fp.closed)

    @pytest.mark.parametrize("count, expected_repr", [
        (1, "NpzFile {fname!r} with keys: arr_0"),
        (5, "NpzFile {fname!r} with keys: arr_0, arr_1, arr_2, arr_3, arr_4"),
        # _MAX_REPR_ARRAY_COUNT is 5, so files with more than 5 keys are
        # expected to end in '...'
        (6, "NpzFile {fname!r} with keys: arr_0, arr_1, arr_2, arr_3, arr_4..."),
    ])
    def test_repr_lists_keys(self, count, expected_repr):
        a = np.array([[1, 2], [3, 4]], float)
        with temppath(suffix='.npz') as tmp:
            np.savez(tmp, *[a] * count)
            l = np.load(tmp)
            assert repr(l) == expected_repr.format(fname=tmp)
            l.close()


class TestSaveTxt:
    def test_array(self):
        a = np.array([[1, 2], [3, 4]], float)
        fmt = "%.18e"
        c = BytesIO()
        np.savetxt(c, a, fmt=fmt)
        c.seek(0)
        assert_equal(c.readlines(),
                     [asbytes((fmt + ' ' + fmt + '\n') % (1, 2)),
                      asbytes((fmt + ' ' + fmt + '\n') % (3, 4))])

        a = np.array([[1, 2], [3, 4]], int)
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 2\n', b'3 4\n'])

    def test_1D(self):
        a = np.array([1, 2, 3, 4], int)
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'1\n', b'2\n', b'3\n', b'4\n'])

    def test_0D_3D(self):
        c = BytesIO()
        assert_raises(ValueError, np.savetxt, c, np.array(1))
        assert_raises(ValueError, np.savetxt, c, np.array([[[1], [2]]]))

    def test_structured(self):
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        c = BytesIO()
        np.savetxt(c, a, fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 2\n', b'3 4\n'])

    def test_structured_padded(self):
        # gh-13297
        a = np.array([(1, 2, 3), (4, 5, 6)], dtype=[
            ('foo', 'i4'), ('bar', 'i4'), ('baz', 'i4')
        ])
        c = BytesIO()
        np.savetxt(c, a[['foo', 'baz']], fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1 3\n', b'4 6\n'])

    def test_multifield_view(self):
        a = np.ones(1, dtype=[('x', 'i4'), ('y', 'i4'), ('z', 'f4')])
        v = a[['x', 'z']]
        with temppath(suffix='.npy') as path:
            path = Path(path)
            np.save(path, v)
            data = np.load(path)
            assert_array_equal(data, v)

    def test_delimiter(self):
        a = np.array([[1., 2.], [3., 4.]])
        c = BytesIO()
        np.savetxt(c, a, delimiter=',', fmt='%d')
        c.seek(0)
        assert_equal(c.readlines(), [b'1,2\n', b'3,4\n'])

    def test_format(self):
        a = np.array([(1, 2), (3, 4)])
        c = BytesIO()
        # Sequence of formats
        np.savetxt(c, a, fmt=['%02d', '%3.1f'])
        c.seek(0)
        assert_equal(c.readlines(), [b'01 2.0\n', b'03 4.0\n'])

        # A single multiformat string
        c = BytesIO()
        np.savetxt(c, a, fmt='%02d : %3.1f')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'01 : 2.0\n', b'03 : 4.0\n'])

        # Specify delimiter, should be overridden
        c = BytesIO()
        np.savetxt(c, a, fmt='%02d : %3.1f', delimiter=',')
        c.seek(0)
        lines = c.readlines()
        assert_equal(lines, [b'01 : 2.0\n', b'03 : 4.0\n'])

        # Bad fmt, should raise a ValueError
        c = BytesIO()
        assert_raises(ValueError, np.savetxt, c, a, fmt=99)

    def test_header_footer(self):
        # Test the functionality of the header and footer keyword argument.

        c = BytesIO()
        a = np.array([(1, 2), (3, 4)], dtype=int)
        test_header_footer = 'Test header / footer'
        # Test the header keyword argument
        np.savetxt(c, a, fmt='%1d', header=test_header_footer)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('# ' + test_header_footer + '\n1 2\n3 4\n'))
        # Test the footer keyword argument
        c = BytesIO()
        np.savetxt(c, a, fmt='%1d', footer=test_header_footer)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('1 2\n3 4\n# ' + test_header_footer + '\n'))
        # Test the commentstr keyword argument used on the header
        c = BytesIO()
        commentstr = '% '
        np.savetxt(c, a, fmt='%1d',
                   header=test_header_footer, comments=commentstr)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes(commentstr + test_header_footer + '\n' + '1 2\n3 4\n'))
        # Test the commentstr keyword argument used on the footer
        c = BytesIO()
        commentstr = '% '
        np.savetxt(c, a, fmt='%1d',
                   footer=test_header_footer, comments=commentstr)
        c.seek(0)
        assert_equal(c.read(),
                     asbytes('1 2\n3 4\n' + commentstr + test_header_footer + '\n'))

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_file_roundtrip(self, filename_type):
        with temppath() as name:
            a = np.array([(1, 2), (3, 4)])
            np.savetxt(filename_type(name), a)
            b = np.loadtxt(filename_type(name))
            assert_array_equal(a, b)

    def test_complex_arrays(self):
        ncols = 2
        nrows = 2
        a = np.zeros((ncols, nrows), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re + 1.0j * im

        # One format only
        c = BytesIO()
        np.savetxt(c, a, fmt=' %+.3e')
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b' ( +3.142e+00+ +2.718e+00j)  ( +3.142e+00+ +2.718e+00j)\n',
             b' ( +3.142e+00+ +2.718e+00j)  ( +3.142e+00+ +2.718e+00j)\n'])

        # One format for each real and imaginary part
        c = BytesIO()
        np.savetxt(c, a, fmt='  %+.3e' * 2 * ncols)
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b'  +3.142e+00  +2.718e+00  +3.142e+00  +2.718e+00\n',
             b'  +3.142e+00  +2.718e+00  +3.142e+00  +2.718e+00\n'])

        # One format for each complex number
        c = BytesIO()
        np.savetxt(c, a, fmt=['(%.3e%+.3ej)'] * ncols)
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b'(3.142e+00+2.718e+00j) (3.142e+00+2.718e+00j)\n',
             b'(3.142e+00+2.718e+00j) (3.142e+00+2.718e+00j)\n'])

    def test_complex_negative_exponent(self):
        # Previous to 1.15, some formats generated x+-yj, gh 7895
        ncols = 2
        nrows = 2
        a = np.zeros((ncols, nrows), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re - 1.0j * im
        c = BytesIO()
        np.savetxt(c, a, fmt='%.3e')
        c.seek(0)
        lines = c.readlines()
        assert_equal(
            lines,
            [b' (3.142e+00-2.718e+00j)  (3.142e+00-2.718e+00j)\n',
             b' (3.142e+00-2.718e+00j)  (3.142e+00-2.718e+00j)\n'])

    def test_custom_writer(self):

        class CustomWriter(list):
            def write(self, text):
                self.extend(text.split(b'\n'))

        w = CustomWriter()
        a = np.array([(1, 2), (3, 4)])
        np.savetxt(w, a)
        b = np.loadtxt(w)
        assert_array_equal(a, b)

    def test_unicode(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        with tempdir() as tmpdir:
            # set encoding as on windows it may not be unicode even on py3
            np.savetxt(os.path.join(tmpdir, 'test.csv'), a, fmt=['%s'],
                       encoding='UTF-8')

    def test_unicode_roundtrip(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        # our gz wrapper support encoding
        suffixes = ['', '.gz']
        if HAS_BZ2:
            suffixes.append('.bz2')
        if HAS_LZMA:
            suffixes.extend(['.xz', '.lzma'])
        with tempdir() as tmpdir:
            for suffix in suffixes:
                np.savetxt(os.path.join(tmpdir, 'test.csv' + suffix), a,
                           fmt=['%s'], encoding='UTF-16-LE')
                b = np.loadtxt(os.path.join(tmpdir, 'test.csv' + suffix),
                               encoding='UTF-16-LE', dtype=np.str_)
                assert_array_equal(a, b)

    def test_unicode_bytestream(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        s = BytesIO()
        np.savetxt(s, a, fmt=['%s'], encoding='UTF-8')
        s.seek(0)
        assert_equal(s.read().decode('UTF-8'), utf8 + '\n')

    def test_unicode_stringstream(self):
        utf8 = b'\xcf\x96'.decode('UTF-8')
        a = np.array([utf8], dtype=np.str_)
        s = StringIO()
        np.savetxt(s, a, fmt=['%s'], encoding='UTF-8')
        s.seek(0)
        assert_equal(s.read(), utf8 + '\n')

    @pytest.mark.parametrize("iotype", [StringIO, BytesIO])
    def test_unicode_and_bytes_fmt(self, iotype):
        # string type of fmt should not matter, see also gh-4053
        a = np.array([1.])
        s = iotype()
        np.savetxt(s, a, fmt="%f")
        s.seek(0)
        if iotype is StringIO:
            assert_equal(s.read(), "%f\n" % 1.)
        else:
            assert_equal(s.read(), b"%f\n" % 1.)

    @pytest.mark.skipif(sys.platform == 'win32', reason="files>4GB may not work")
    @pytest.mark.slow
    @requires_memory(free_bytes=7e9)
    def test_large_zip(self):
        def check_large_zip(memoryerror_raised):
            memoryerror_raised.value = False
            try:
                # The test takes at least 6GB of memory, writes a file larger
                # than 4GB. This tests the ``allowZip64`` kwarg to ``zipfile``
                test_data = np.asarray([np.random.rand(
                                        np.random.randint(50, 100), 4)
                                        for i in range(800000)], dtype=object)
                with tempdir() as tmpdir:
                    np.savez(os.path.join(tmpdir, 'test.npz'),
                             test_data=test_data)
            except MemoryError:
                memoryerror_raised.value = True
                raise
        # run in a subprocess to ensure memory is released on PyPy, see gh-15775
        # Use an object in shared memory to re-raise the MemoryError exception
        # in our process if needed, see gh-16889
        memoryerror_raised = Value(c_bool)

        # Since Python 3.8, the default start method for multiprocessing has
        # been changed from 'fork' to 'spawn' on macOS, causing inconsistency
        # on memory sharing model, leading to failed test for check_large_zip
        ctx = get_context('fork')
        p = ctx.Process(target=check_large_zip, args=(memoryerror_raised,))
        p.start()
        p.join()
        if memoryerror_raised.value:
            raise MemoryError("Child process raised a MemoryError exception")
        # -9 indicates a SIGKILL, probably an OOM.
        if p.exitcode == -9:
            pytest.xfail("subprocess got a SIGKILL, apparently free memory was not sufficient")
        assert p.exitcode == 0

class LoadTxtBase:
    def check_compressed(self, fopen, suffixes):
        # Test that we can load data from a compressed file
        wanted = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')
        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            for suffix in suffixes:
                with temppath(suffix=suffix) as name:
                    with fopen(name, mode='wt', encoding='UTF-32-LE') as f:
                        f.write(data)
                    res = self.loadfunc(name, encoding='UTF-32-LE')
                    assert_array_equal(res, wanted)
                    with fopen(name, "rt",  encoding='UTF-32-LE') as f:
                        res = self.loadfunc(f)
                    assert_array_equal(res, wanted)

    def test_compressed_gzip(self):
        self.check_compressed(gzip.open, ('.gz',))

    @pytest.mark.skipif(not HAS_BZ2, reason="Needs bz2")
    def test_compressed_bz2(self):
        self.check_compressed(bz2.open, ('.bz2',))

    @pytest.mark.skipif(not HAS_LZMA, reason="Needs lzma")
    def test_compressed_lzma(self):
        self.check_compressed(lzma.open, ('.xz', '.lzma'))

    def test_encoding(self):
        with temppath() as path:
            with open(path, "wb") as f:
                f.write('0.\n1.\n2.'.encode("UTF-16"))
            x = self.loadfunc(path, encoding="UTF-16")
            assert_array_equal(x, [0., 1., 2.])

    def test_stringload(self):
        # umlaute
        nonascii = b'\xc3\xb6\xc3\xbc\xc3\xb6'.decode("UTF-8")
        with temppath() as path:
            with open(path, "wb") as f:
                f.write(nonascii.encode("UTF-16"))
            x = self.loadfunc(path, encoding="UTF-16", dtype=np.str_)
            assert_array_equal(x, nonascii)

    def test_binary_decode(self):
        utf16 = b'\xff\xfeh\x04 \x00i\x04 \x00j\x04'
        v = self.loadfunc(BytesIO(utf16), dtype=np.str_, encoding='UTF-16')
        assert_array_equal(v, np.array(utf16.decode('UTF-16').split()))

    def test_converters_decode(self):
        # test converters that decode strings
        c = TextIO()
        c.write(b'\xcf\x96')
        c.seek(0)
        x = self.loadfunc(c, dtype=np.str_, encoding="bytes",
                          converters={0: lambda x: x.decode('UTF-8')})
        a = np.array([b'\xcf\x96'.decode('UTF-8')])
        assert_array_equal(x, a)

    def test_converters_nodecode(self):
        # test native string converters enabled by setting an encoding
        utf8 = b'\xcf\x96'.decode('UTF-8')
        with temppath() as path:
            with open(path, 'wt', encoding='UTF-8') as f:
                f.write(utf8)
            x = self.loadfunc(path, dtype=np.str_,
                              converters={0: lambda x: x + 't'},
                              encoding='UTF-8')
            a = np.array([utf8 + 't'])
            assert_array_equal(x, a)


class TestLoadTxt(LoadTxtBase):
    loadfunc = staticmethod(np.loadtxt)

    def setup_method(self):
        # lower chunksize for testing
        self.orig_chunk = _npyio_impl._loadtxt_chunksize
        _npyio_impl._loadtxt_chunksize = 1

    def teardown_method(self):
        _npyio_impl._loadtxt_chunksize = self.orig_chunk

    def test_record(self):
        c = TextIO()
        c.write('1 2\n3 4')
        c.seek(0)
        x = np.loadtxt(c, dtype=[('x', np.int32), ('y', np.int32)])
        a = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        assert_array_equal(x, a)

        d = TextIO()
        d.write('M 64 75.0\nF 25 60.0')
        d.seek(0)
        mydescriptor = {'names': ('gender', 'age', 'weight'),
                        'formats': ('S1', 'i4', 'f4')}
        b = np.array([('M', 64.0, 75.0),
                      ('F', 25.0, 60.0)], dtype=mydescriptor)
        y = np.loadtxt(d, dtype=mydescriptor)
        assert_array_equal(y, b)

    def test_array(self):
        c = TextIO()
        c.write('1 2\n3 4')

        c.seek(0)
        x = np.loadtxt(c, dtype=int)
        a = np.array([[1, 2], [3, 4]], int)
        assert_array_equal(x, a)

        c.seek(0)
        x = np.loadtxt(c, dtype=float)
        a = np.array([[1, 2], [3, 4]], float)
        assert_array_equal(x, a)

    def test_1D(self):
        c = TextIO()
        c.write('1\n2\n3\n4\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int)
        a = np.array([1, 2, 3, 4], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('1,2,3,4\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',')
        a = np.array([1, 2, 3, 4], int)
        assert_array_equal(x, a)

    def test_missing(self):
        c = TextIO()
        c.write('1,2,3,,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       converters={3: lambda s: int(s or - 999)})
        a = np.array([1, 2, 3, -999, 5], int)
        assert_array_equal(x, a)

    def test_converters_with_usecols(self):
        c = TextIO()
        c.write('1,2,3,,5\n6,7,8,9,10\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       converters={3: lambda s: int(s or - 999)},
                       usecols=(1, 3,))
        a = np.array([[2, -999], [7, 9]], int)
        assert_array_equal(x, a)

    def test_comments_unicode(self):
        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments='#')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_comments_byte(self):
        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments=b'#')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_comments_multiple(self):
        c = TextIO()
        c.write('# comment\n1,2,3\n@ comment2\n4,5,6 // comment3')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments=['#', '@', '//'])
        a = np.array([[1, 2, 3], [4, 5, 6]], int)
        assert_array_equal(x, a)

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_comments_multi_chars(self):
        c = TextIO()
        c.write('/* comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       comments='/*')
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        # Check that '/*' is not transformed to ['/', '*']
        c = TextIO()
        c.write('*/ comment\n1,2,3,5\n')
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, dtype=int, delimiter=',',
                      comments='/*')

    def test_skiprows(self):
        c = TextIO()
        c.write('comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('# comment\n1,2,3,5\n')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_usecols(self):
        a = np.array([[1, 2], [3, 4]], float)
        c = BytesIO()
        np.savetxt(c, a)
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(1,))
        assert_array_equal(x, a[:, 1])

        a = np.array([[1, 2, 3], [3, 4, 5]], float)
        c = BytesIO()
        np.savetxt(c, a)
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(1, 2))
        assert_array_equal(x, a[:, 1:])

        # Testing with arrays instead of tuples.
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=np.array([1, 2]))
        assert_array_equal(x, a[:, 1:])

        # Testing with an integer instead of a sequence
        for int_type in [int, np.int8, np.int16,
                         np.int32, np.int64, np.uint8, np.uint16,
                         np.uint32, np.uint64]:
            to_read = int_type(1)
            c.seek(0)
            x = np.loadtxt(c, dtype=float, usecols=to_read)
            assert_array_equal(x, a[:, 1])

        # Testing with some crazy custom integer type
        class CrazyInt:
            def __index__(self):
                return 1

        crazy_int = CrazyInt()
        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=crazy_int)
        assert_array_equal(x, a[:, 1])

        c.seek(0)
        x = np.loadtxt(c, dtype=float, usecols=(crazy_int,))
        assert_array_equal(x, a[:, 1])

        # Checking with dtypes defined converters.
        data = '''JOE 70.1 25.3
                BOB 60.5 27.9
                '''
        c = TextIO(data)
        names = ['stid', 'temp']
        dtypes = ['S4', 'f8']
        arr = np.loadtxt(c, usecols=(0, 2), dtype=list(zip(names, dtypes)))
        assert_equal(arr['stid'], [b"JOE", b"BOB"])
        assert_equal(arr['temp'], [25.3, 27.9])

        # Testing non-ints in usecols
        c.seek(0)
        bogus_idx = 1.5
        assert_raises_regex(
            TypeError,
            f'^usecols must be.*{type(bogus_idx).__name__}',
            np.loadtxt, c, usecols=bogus_idx
            )

        assert_raises_regex(
            TypeError,
            f'^usecols must be.*{type(bogus_idx).__name__}',
            np.loadtxt, c, usecols=[0, bogus_idx, 0]
            )

    def test_bad_usecols(self):
        with pytest.raises(OverflowError):
            np.loadtxt(["1\n"], usecols=[2**64], delimiter=",")
        with pytest.raises((ValueError, OverflowError)):
            # Overflow error on 32bit platforms
            np.loadtxt(["1\n"], usecols=[2**62], delimiter=",")
        with pytest.raises(TypeError,
                match="If a structured dtype .*. But 1 usecols were given and "
                      "the number of fields is 3."):
            np.loadtxt(["1,1\n"], dtype="i,2i", usecols=[0], delimiter=",")

    def test_fancy_dtype(self):
        c = TextIO()
        c.write('1,2,3.0\n4,5,6.0\n')
        c.seek(0)
        dt = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        x = np.loadtxt(c, dtype=dt, delimiter=',')
        a = np.array([(1, (2, 3.0)), (4, (5, 6.0))], dt)
        assert_array_equal(x, a)

    def test_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 3))])
        x = np.loadtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0, [[1, 2, 3], [4, 5, 6]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_3d_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6 7 8 9 10 11 12")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 2, 3))])
        x = np.loadtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0,
                       [[[1, 2, 3], [4, 5, 6]], [[7, 8, 9], [10, 11, 12]]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_str_dtype(self):
        # see gh-8033
        c = ["str1", "str2"]

        for dt in (str, np.bytes_):
            a = np.array(["str1", "str2"], dtype=dt)
            x = np.loadtxt(c, dtype=dt)
            assert_array_equal(x, a)

    def test_empty_file(self):
        with pytest.warns(UserWarning, match="input contained no data"):
            c = TextIO()
            x = np.loadtxt(c)
            assert_equal(x.shape, (0,))
            x = np.loadtxt(c, dtype=np.int64)
            assert_equal(x.shape, (0,))
            assert_(x.dtype == np.int64)

    def test_unused_converter(self):
        c = TextIO()
        c.writelines(['1 21\n', '3 42\n'])
        c.seek(0)
        data = np.loadtxt(c, usecols=(1,),
                          converters={0: lambda s: int(s, 16)})
        assert_array_equal(data, [21, 42])

        c.seek(0)
        data = np.loadtxt(c, usecols=(1,),
                          converters={1: lambda s: int(s, 16)})
        assert_array_equal(data, [33, 66])

    def test_dtype_with_object(self):
        # Test using an explicit dtype with an object
        data = """ 1; 2001-01-01
                   2; 2002-01-31 """
        ndtype = [('idx', int), ('code', object)]
        func = lambda s: strptime(s.strip(), "%Y-%m-%d")
        converters = {1: func}
        test = np.loadtxt(TextIO(data), delimiter=";", dtype=ndtype,
                          converters=converters)
        control = np.array(
            [(1, datetime(2001, 1, 1)), (2, datetime(2002, 1, 31))],
            dtype=ndtype)
        assert_equal(test, control)

    def test_uint64_type(self):
        tgt = (9223372043271415339, 9223372043271415853)
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=np.uint64)
        assert_equal(res, tgt)

    def test_int64_type(self):
        tgt = (-9223372036854775807, 9223372036854775807)
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=np.int64)
        assert_equal(res, tgt)

    def test_from_float_hex(self):
        # IEEE doubles and floats only, otherwise the float32
        # conversion may fail.
        tgt = np.logspace(-10, 10, 5).astype(np.float32)
        tgt = np.hstack((tgt, -tgt)).astype(float)
        inp = '\n'.join(map(float.hex, tgt))
        c = TextIO()
        c.write(inp)
        for dt in [float, np.float32]:
            c.seek(0)
            res = np.loadtxt(
                c, dtype=dt, converters=float.fromhex, encoding="latin1")
            assert_equal(res, tgt, err_msg=f"{dt}")

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_default_float_converter_no_default_hex_conversion(self):
        """
        Ensure that fromhex is only used for values with the correct prefix and
        is not called by default. Regression test related to gh-19598.
        """
        c = TextIO("a b c")
        with pytest.raises(ValueError,
                match=".*convert string 'a' to float64 at row 0, column 1"):
            np.loadtxt(c)

    @pytest.mark.skipif(IS_PYPY and sys.implementation.version <= (7, 3, 8),
                        reason="PyPy bug in error formatting")
    def test_default_float_converter_exception(self):
        """
        Ensure that the exception message raised during failed floating point
        conversion is correct. Regression test related to gh-19598.
        """
        c = TextIO("qrs tuv")  # Invalid values for default float converter
        with pytest.raises(ValueError,
                match="could not convert string 'qrs' to float64"):
            np.loadtxt(c)

    def test_from_complex(self):
        tgt = (complex(1, 1), complex(1, -1))
        c = TextIO()
        c.write("%s %s" % tgt)
        c.seek(0)
        res = np.loadtxt(c, dtype=complex)
        assert_equal(res, tgt)

    def test_complex_misformatted(self):
        # test for backward compatibility
        # some complex formats used to generate x+-yj
        a = np.zeros((2, 2), dtype=np.complex128)
        re = np.pi
        im = np.e
        a[:] = re - 1.0j * im
        c = BytesIO()
        np.savetxt(c, a, fmt='%.16e')
        c.seek(0)
        txt = c.read()
        c.seek(0)
        # misformat the sign on the imaginary part, gh 7895
        txt_bad = txt.replace(b'e+00-', b'e00+-')
        assert_(txt_bad != txt)
        c.write(txt_bad)
        c.seek(0)
        res = np.loadtxt(c, dtype=complex)
        assert_equal(res, a)

    def test_universal_newline(self):
        with temppath() as name:
            with open(name, 'w') as f:
                f.write('1 21\r3 42\r')
            data = np.loadtxt(name)
        assert_array_equal(data, [[1, 21], [3, 42]])

    def test_empty_field_after_tab(self):
        c = TextIO()
        c.write('1 \t2 \t3\tstart \n4\t5\t6\t  \n7\t8\t9.5\t')
        c.seek(0)
        dt = {'names': ('x', 'y', 'z', 'comment'),
              'formats': ('<i4', '<i4', '<f4', '|S8')}
        x = np.loadtxt(c, dtype=dt, delimiter='\t')
        a = np.array([b'start ', b'  ', b''])
        assert_array_equal(x['comment'], a)

    def test_unpack_structured(self):
        txt = TextIO("M 21 72\nF 35 58")
        dt = {'names': ('a', 'b', 'c'), 'formats': ('|S1', '<i4', '<f4')}
        a, b, c = np.loadtxt(txt, dtype=dt, unpack=True)
        assert_(a.dtype.str == '|S1')
        assert_(b.dtype.str == '<i4')
        assert_(c.dtype.str == '<f4')
        assert_array_equal(a, np.array([b'M', b'F']))
        assert_array_equal(b, np.array([21, 35]))
        assert_array_equal(c, np.array([72.,  58.]))

    def test_ndmin_keyword(self):
        c = TextIO()
        c.write('1,2,3\n4,5,6')
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, ndmin=3)
        c.seek(0)
        assert_raises(ValueError, np.loadtxt, c, ndmin=1.5)
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',', ndmin=1)
        a = np.array([[1, 2, 3], [4, 5, 6]])
        assert_array_equal(x, a)

        d = TextIO()
        d.write('0,1,2')
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=2)
        assert_(x.shape == (1, 3))
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=1)
        assert_(x.shape == (3,))
        d.seek(0)
        x = np.loadtxt(d, dtype=int, delimiter=',', ndmin=0)
        assert_(x.shape == (3,))

        e = TextIO()
        e.write('0\n1\n2')
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=2)
        assert_(x.shape == (3, 1))
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=1)
        assert_(x.shape == (3,))
        e.seek(0)
        x = np.loadtxt(e, dtype=int, delimiter=',', ndmin=0)
        assert_(x.shape == (3,))

        # Test ndmin kw with empty file.
        with pytest.warns(UserWarning, match="input contained no data"):
            f = TextIO()
            assert_(np.loadtxt(f, ndmin=2).shape == (0, 1,))
            assert_(np.loadtxt(f, ndmin=1).shape == (0,))

    def test_generator_source(self):
        def count():
            for i in range(10):
                yield "%d" % i

        res = np.loadtxt(count())
        assert_array_equal(res, np.arange(10))

    def test_bad_line(self):
        c = TextIO()
        c.write('1 2 3\n4 5 6\n2 3')
        c.seek(0)

        # Check for exception and that exception contains line number
        assert_raises_regex(ValueError, "3", np.loadtxt, c)

    def test_none_as_string(self):
        # gh-5155, None should work as string when format demands it
        c = TextIO()
        c.write('100,foo,200\n300,None,400')
        c.seek(0)
        dt = np.dtype([('x', int), ('a', 'S10'), ('y', int)])
        np.loadtxt(c, delimiter=',', dtype=dt, comments=None)  # Should succeed

    @pytest.mark.skipif(locale.getpreferredencoding() == 'ANSI_X3.4-1968',
                        reason="Wrong preferred encoding")
    def test_binary_load(self):
        butf8 = b"5,6,7,\xc3\x95scarscar\r\n15,2,3,hello\r\n"\
                b"20,2,3,\xc3\x95scar\r\n"
        sutf8 = butf8.decode("UTF-8").replace("\r", "").splitlines()
        with temppath() as path:
            with open(path, "wb") as f:
                f.write(butf8)
            with open(path, "rb") as f:
                x = np.loadtxt(f, encoding="UTF-8", dtype=np.str_)
            assert_array_equal(x, sutf8)
            # test broken latin1 conversion people now rely on
            with open(path, "rb") as f:
                x = np.loadtxt(f, encoding="UTF-8", dtype="S")
            x = [b'5,6,7,\xc3\x95scarscar', b'15,2,3,hello', b'20,2,3,\xc3\x95scar']
            assert_array_equal(x, np.array(x, dtype="S"))

    def test_max_rows(self):
        c = TextIO()
        c.write('1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       max_rows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

    def test_max_rows_with_skiprows(self):
        c = TextIO()
        c.write('comments\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=1)
        a = np.array([1, 2, 3, 5], int)
        assert_array_equal(x, a)

        c = TextIO()
        c.write('comment\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=2)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8]], int)
        assert_array_equal(x, a)

    def test_max_rows_with_read_continuation(self):
        c = TextIO()
        c.write('1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       max_rows=2)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8]], int)
        assert_array_equal(x, a)
        # test continuation
        x = np.loadtxt(c, dtype=int, delimiter=',')
        a = np.array([2, 1, 4, 5], int)
        assert_array_equal(x, a)

    def test_max_rows_larger(self):
        #test max_rows > num rows
        c = TextIO()
        c.write('comment\n1,2,3,5\n4,5,7,8\n2,1,4,5')
        c.seek(0)
        x = np.loadtxt(c, dtype=int, delimiter=',',
                       skiprows=1, max_rows=6)
        a = np.array([[1, 2, 3, 5], [4, 5, 7, 8], [2, 1, 4, 5]], int)
        assert_array_equal(x, a)

    @pytest.mark.parametrize(["skip", "data"], [
            (1, ["ignored\n", "1,2\n", "\n", "3,4\n"]),
            # "Bad" lines that do not end in newlines:
            (1, ["ignored", "1,2", "", "3,4"]),
            (1, StringIO("ignored\n1,2\n\n3,4")),
            # Same as above, but do not skip any lines:
            (0, ["-1,0\n", "1,2\n", "\n", "3,4\n"]),
            (0, ["-1,0", "1,2", "", "3,4"]),
            (0, StringIO("-1,0\n1,2\n\n3,4"))])
    def test_max_rows_empty_lines(self, skip, data):
        with pytest.warns(UserWarning,
                    match=f"Input line 3.*max_rows={3 - skip}"):
            res = np.loadtxt(data, dtype=int, skiprows=skip, delimiter=",",
                             max_rows=3 - skip)
            assert_array_equal(res, [[-1, 0], [1, 2], [3, 4]][skip:])

        if isinstance(data, StringIO):
            data.seek(0)

        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            with pytest.raises(UserWarning):
                np.loadtxt(data, dtype=int, skiprows=skip, delimiter=",",
                           max_rows=3 - skip)

class Testfromregex:
    def test_record(self):
        c = TextIO()
        c.write('1.312 foo\n1.534 bar\n4.444 qux')
        c.seek(0)

        dt = [('num', np.float64), ('val', 'S3')]
        x = np.fromregex(c, r"([0-9.]+)\s+(...)", dt)
        a = np.array([(1.312, 'foo'), (1.534, 'bar'), (4.444, 'qux')],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_record_2(self):
        c = TextIO()
        c.write('1312 foo\n1534 bar\n4444 qux')
        c.seek(0)

        dt = [('num', np.int32), ('val', 'S3')]
        x = np.fromregex(c, r"(\d+)\s+(...)", dt)
        a = np.array([(1312, 'foo'), (1534, 'bar'), (4444, 'qux')],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_record_3(self):
        c = TextIO()
        c.write('1312 foo\n1534 bar\n4444 qux')
        c.seek(0)

        dt = [('num', np.float64)]
        x = np.fromregex(c, r"(\d+)\s+...", dt)
        a = np.array([(1312,), (1534,), (4444,)], dtype=dt)
        assert_array_equal(x, a)

    @pytest.mark.parametrize("path_type", [str, Path])
    def test_record_unicode(self, path_type):
        utf8 = b'\xcf\x96'
        with temppath() as str_path:
            path = path_type(str_path)
            with open(path, 'wb') as f:
                f.write(b'1.312 foo' + utf8 + b' \n1.534 bar\n4.444 qux')

            dt = [('num', np.float64), ('val', 'U4')]
            x = np.fromregex(path, r"(?u)([0-9.]+)\s+(\w+)", dt, encoding='UTF-8')
            a = np.array([(1.312, 'foo' + utf8.decode('UTF-8')), (1.534, 'bar'),
                           (4.444, 'qux')], dtype=dt)
            assert_array_equal(x, a)

            regexp = re.compile(r"([0-9.]+)\s+(\w+)", re.UNICODE)
            x = np.fromregex(path, regexp, dt, encoding='UTF-8')
            assert_array_equal(x, a)

    def test_compiled_bytes(self):
        regexp = re.compile(br'(\d)')
        c = BytesIO(b'123')
        dt = [('num', np.float64)]
        a = np.array([1, 2, 3], dtype=dt)
        x = np.fromregex(c, regexp, dt)
        assert_array_equal(x, a)

    def test_bad_dtype_not_structured(self):
        regexp = re.compile(br'(\d)')
        c = BytesIO(b'123')
        with pytest.raises(TypeError, match='structured datatype'):
            np.fromregex(c, regexp, dtype=np.float64)


#####--------------------------------------------------------------------------


class TestFromTxt(LoadTxtBase):
    loadfunc = staticmethod(np.genfromtxt)

    def test_record(self):
        # Test w/ explicit dtype
        data = TextIO('1 2\n3 4')
        test = np.genfromtxt(data, dtype=[('x', np.int32), ('y', np.int32)])
        control = np.array([(1, 2), (3, 4)], dtype=[('x', 'i4'), ('y', 'i4')])
        assert_equal(test, control)
        #
        data = TextIO('M 64.0 75.0\nF 25.0 60.0')
        descriptor = {'names': ('gender', 'age', 'weight'),
                      'formats': ('S1', 'i4', 'f4')}
        control = np.array([('M', 64.0, 75.0), ('F', 25.0, 60.0)],
                           dtype=descriptor)
        test = np.genfromtxt(data, dtype=descriptor)
        assert_equal(test, control)

    def test_array(self):
        # Test outputting a standard ndarray
        data = TextIO('1 2\n3 4')
        control = np.array([[1, 2], [3, 4]], dtype=int)
        test = np.genfromtxt(data, dtype=int)
        assert_array_equal(test, control)
        #
        data.seek(0)
        control = np.array([[1, 2], [3, 4]], dtype=float)
        test = np.loadtxt(data, dtype=float)
        assert_array_equal(test, control)

    def test_1D(self):
        # Test squeezing to 1D
        control = np.array([1, 2, 3, 4], int)
        #
        data = TextIO('1\n2\n3\n4\n')
        test = np.genfromtxt(data, dtype=int)
        assert_array_equal(test, control)
        #
        data = TextIO('1,2,3,4\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',')
        assert_array_equal(test, control)

    def test_comments(self):
        # Test the stripping of comments
        control = np.array([1, 2, 3, 5], int)
        # Comment on its own line
        data = TextIO('# comment\n1,2,3,5\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',', comments='#')
        assert_equal(test, control)
        # Comment at the end of a line
        data = TextIO('1,2,3,5# comment\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',', comments='#')
        assert_equal(test, control)

    def test_skiprows(self):
        # Test row skipping
        control = np.array([1, 2, 3, 5], int)
        kwargs = {"dtype": int, "delimiter": ','}
        #
        data = TextIO('comment\n1,2,3,5\n')
        test = np.genfromtxt(data, skip_header=1, **kwargs)
        assert_equal(test, control)
        #
        data = TextIO('# comment\n1,2,3,5\n')
        test = np.loadtxt(data, skiprows=1, **kwargs)
        assert_equal(test, control)

    def test_skip_footer(self):
        data = [f"# {i}" for i in range(1, 6)]
        data.append("A, B, C")
        data.extend([f"{i},{i:3.1f},{i:03d}" for i in range(51)])
        data[-1] = "99,99"
        kwargs = {"delimiter": ",", "names": True, "skip_header": 5, "skip_footer": 10}
        test = np.genfromtxt(TextIO("\n".join(data)), **kwargs)
        ctrl = np.array([(f"{i:f}", f"{i:f}", f"{i:f}") for i in range(41)],
                        dtype=[(_, float) for _ in "ABC"])
        assert_equal(test, ctrl)

    def test_skip_footer_with_invalid(self):
        with suppress_warnings() as sup:
            sup.filter(ConversionWarning)
            basestr = '1 1\n2 2\n3 3\n4 4\n5  \n6  \n7  \n'
            # Footer too small to get rid of all invalid values
            assert_raises(ValueError, np.genfromtxt,
                          TextIO(basestr), skip_footer=1)
    #        except ValueError:
    #            pass
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=1, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]]))
            #
            a = np.genfromtxt(TextIO(basestr), skip_footer=3)
            assert_equal(a, np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]]))
            #
            basestr = '1 1\n2  \n3 3\n4 4\n5  \n6 6\n7 7\n'
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=1, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [3., 3.], [4., 4.], [6., 6.]]))
            a = np.genfromtxt(
                TextIO(basestr), skip_footer=3, invalid_raise=False)
            assert_equal(a, np.array([[1., 1.], [3., 3.], [4., 4.]]))

    def test_header(self):
        # Test retrieving a header
        data = TextIO('gender age weight\nM 64.0 75.0\nF 25.0 60.0')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, dtype=None, names=True,
                                 encoding='bytes')
            assert_(w[0].category is VisibleDeprecationWarning)
        control = {'gender': np.array([b'M', b'F']),
                   'age': np.array([64.0, 25.0]),
                   'weight': np.array([75.0, 60.0])}
        assert_equal(test['gender'], control['gender'])
        assert_equal(test['age'], control['age'])
        assert_equal(test['weight'], control['weight'])

    def test_auto_dtype(self):
        # Test the automatic definition of the output dtype
        data = TextIO('A 64 75.0 3+4j True\nBCD 25 60.0 5+6j False')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, dtype=None, encoding='bytes')
            assert_(w[0].category is VisibleDeprecationWarning)
        control = [np.array([b'A', b'BCD']),
                   np.array([64, 25]),
                   np.array([75.0, 60.0]),
                   np.array([3 + 4j, 5 + 6j]),
                   np.array([True, False]), ]
        assert_equal(test.dtype.names, ['f0', 'f1', 'f2', 'f3', 'f4'])
        for (i, ctrl) in enumerate(control):
            assert_equal(test[f'f{i}'], ctrl)

    def test_auto_dtype_uniform(self):
        # Tests whether the output dtype can be uniformized
        data = TextIO('1 2 3 4\n5 6 7 8\n')
        test = np.genfromtxt(data, dtype=None)
        control = np.array([[1, 2, 3, 4], [5, 6, 7, 8]])
        assert_equal(test, control)

    def test_fancy_dtype(self):
        # Check that a nested dtype isn't MIA
        data = TextIO('1,2,3.0\n4,5,6.0\n')
        fancydtype = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        test = np.genfromtxt(data, dtype=fancydtype, delimiter=',')
        control = np.array([(1, (2, 3.0)), (4, (5, 6.0))], dtype=fancydtype)
        assert_equal(test, control)

    def test_names_overwrite(self):
        # Test overwriting the names of the dtype
        descriptor = {'names': ('g', 'a', 'w'),
                      'formats': ('S1', 'i4', 'f4')}
        data = TextIO(b'M 64.0 75.0\nF 25.0 60.0')
        names = ('gender', 'age', 'weight')
        test = np.genfromtxt(data, dtype=descriptor, names=names)
        descriptor['names'] = names
        control = np.array([('M', 64.0, 75.0),
                            ('F', 25.0, 60.0)], dtype=descriptor)
        assert_equal(test, control)

    def test_bad_fname(self):
        with pytest.raises(TypeError, match='fname must be a string,'):
            np.genfromtxt(123)

    def test_commented_header(self):
        # Check that names can be retrieved even if the line is commented out.
        data = TextIO("""
#gender age weight
M   21  72.100000
F   35  58.330000
M   33  21.99
        """)
        # The # is part of the first name and should be deleted automatically.
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, names=True, dtype=None,
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('M', 21, 72.1), ('F', 35, 58.33), ('M', 33, 21.99)],
                        dtype=[('gender', '|S1'), ('age', int), ('weight', float)])
        assert_equal(test, ctrl)
        # Ditto, but we should get rid of the first element
        data = TextIO(b"""
# gender age weight
M   21  72.100000
F   35  58.330000
M   33  21.99
        """)
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, names=True, dtype=None,
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test, ctrl)

    def test_names_and_comments_none(self):
        # Tests case when names is true but comments is None (gh-10780)
        data = TextIO('col1 col2\n 1 2\n 3 4')
        test = np.genfromtxt(data, dtype=(int, int), comments=None, names=True)
        control = np.array([(1, 2), (3, 4)], dtype=[('col1', int), ('col2', int)])
        assert_equal(test, control)

    def test_file_is_closed_on_error(self):
        # gh-13200
        with tempdir() as tmpdir:
            fpath = os.path.join(tmpdir, "test.csv")
            with open(fpath, "wb") as f:
                f.write('\N{GREEK PI SYMBOL}'.encode())

            # ResourceWarnings are emitted from a destructor, so won't be
            # detected by regular propagation to errors.
            with assert_no_warnings():
                with pytest.raises(UnicodeDecodeError):
                    np.genfromtxt(fpath, encoding="ascii")

    def test_autonames_and_usecols(self):
        # Tests names and usecols
        data = TextIO('A B C D\n aaaa 121 45 9.1')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, usecols=('A', 'C', 'D'),
                                names=True, dtype=None, encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        control = np.array(('aaaa', 45, 9.1),
                           dtype=[('A', '|S4'), ('C', int), ('D', float)])
        assert_equal(test, control)

    def test_converters_with_usecols(self):
        # Test the combination user-defined converters and usecol
        data = TextIO('1,2,3,,5\n6,7,8,9,10\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',',
                            converters={3: lambda s: int(s or - 999)},
                            usecols=(1, 3,))
        control = np.array([[2, -999], [7, 9]], int)
        assert_equal(test, control)

    def test_converters_with_usecols_and_names(self):
        # Tests names and usecols
        data = TextIO('A B C D\n aaaa 121 45 9.1')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(data, usecols=('A', 'C', 'D'), names=True,
                                dtype=None, encoding="bytes",
                                converters={'C': lambda s: 2 * int(s)})
            assert_(w[0].category is VisibleDeprecationWarning)
        control = np.array(('aaaa', 90, 9.1),
                           dtype=[('A', '|S4'), ('C', int), ('D', float)])
        assert_equal(test, control)

    def test_converters_cornercases(self):
        # Test the conversion to datetime.
        converter = {
            'date': lambda s: strptime(s, '%Y-%m-%d %H:%M:%SZ')}
        data = TextIO('2009-02-03 12:00:00Z, 72214.0')
        test = np.genfromtxt(data, delimiter=',', dtype=None,
                            names=['date', 'stid'], converters=converter)
        control = np.array((datetime(2009, 2, 3), 72214.),
                           dtype=[('date', np.object_), ('stid', float)])
        assert_equal(test, control)

    def test_converters_cornercases2(self):
        # Test the conversion to datetime64.
        converter = {
            'date': lambda s: np.datetime64(strptime(s, '%Y-%m-%d %H:%M:%SZ'))}
        data = TextIO('2009-02-03 12:00:00Z, 72214.0')
        test = np.genfromtxt(data, delimiter=',', dtype=None,
                            names=['date', 'stid'], converters=converter)
        control = np.array((datetime(2009, 2, 3), 72214.),
                           dtype=[('date', 'datetime64[us]'), ('stid', float)])
        assert_equal(test, control)

    def test_unused_converter(self):
        # Test whether unused converters are forgotten
        data = TextIO("1 21\n  3 42\n")
        test = np.genfromtxt(data, usecols=(1,),
                            converters={0: lambda s: int(s, 16)})
        assert_equal(test, [21, 42])
        #
        data.seek(0)
        test = np.genfromtxt(data, usecols=(1,),
                            converters={1: lambda s: int(s, 16)})
        assert_equal(test, [33, 66])

    def test_invalid_converter(self):
        strip_rand = lambda x: float((b'r' in x.lower() and x.split()[-1]) or
                                     ((b'r' not in x.lower() and x.strip()) or 0.0))
        strip_per = lambda x: float((b'%' in x.lower() and x.split()[0]) or
                                    ((b'%' not in x.lower() and x.strip()) or 0.0))
        s = TextIO("D01N01,10/1/2003 ,1 %,R 75,400,600\r\n"
                   "L24U05,12/5/2003, 2 %,1,300, 150.5\r\n"
                   "D02N03,10/10/2004,R 1,,7,145.55")
        kwargs = {
            "converters": {2: strip_per, 3: strip_rand}, "delimiter": ",",
            "dtype": None, "encoding": "bytes"}
        assert_raises(ConverterError, np.genfromtxt, s, **kwargs)

    def test_tricky_converter_bug1666(self):
        # Test some corner cases
        s = TextIO('q1,2\nq3,4')
        cnv = lambda s: float(s[1:])
        test = np.genfromtxt(s, delimiter=',', converters={0: cnv})
        control = np.array([[1., 2.], [3., 4.]])
        assert_equal(test, control)

    def test_dtype_with_converters(self):
        dstr = "2009; 23; 46"
        test = np.genfromtxt(TextIO(dstr,),
                            delimiter=";", dtype=float, converters={0: bytes})
        control = np.array([('2009', 23., 46)],
                           dtype=[('f0', '|S4'), ('f1', float), ('f2', float)])
        assert_equal(test, control)
        test = np.genfromtxt(TextIO(dstr,),
                            delimiter=";", dtype=float, converters={0: float})
        control = np.array([2009., 23., 46],)
        assert_equal(test, control)

    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_dtype_with_converters_and_usecols(self):
        dstr = "1,5,-1,1:1\n2,8,-1,1:n\n3,3,-2,m:n\n"
        dmap = {'1:1': 0, '1:n': 1, 'm:1': 2, 'm:n': 3}
        dtyp = [('e1', 'i4'), ('e2', 'i4'), ('e3', 'i2'), ('n', 'i1')]
        conv = {0: int, 1: int, 2: int, 3: lambda r: dmap[r.decode()]}
        test = recfromcsv(TextIO(dstr,), dtype=dtyp, delimiter=',',
                          names=None, converters=conv, encoding="bytes")
        control = np.rec.array([(1, 5, -1, 0), (2, 8, -1, 1), (3, 3, -2, 3)], dtype=dtyp)
        assert_equal(test, control)
        dtyp = [('e1', 'i4'), ('e2', 'i4'), ('n', 'i1')]
        test = recfromcsv(TextIO(dstr,), dtype=dtyp, delimiter=',',
                          usecols=(0, 1, 3), names=None, converters=conv,
                          encoding="bytes")
        control = np.rec.array([(1, 5, 0), (2, 8, 1), (3, 3, 3)], dtype=dtyp)
        assert_equal(test, control)

    def test_dtype_with_object(self):
        # Test using an explicit dtype with an object
        data = """ 1; 2001-01-01
                   2; 2002-01-31 """
        ndtype = [('idx', int), ('code', object)]
        func = lambda s: strptime(s.strip(), "%Y-%m-%d")
        converters = {1: func}
        test = np.genfromtxt(TextIO(data), delimiter=";", dtype=ndtype,
                             converters=converters)
        control = np.array(
            [(1, datetime(2001, 1, 1)), (2, datetime(2002, 1, 31))],
            dtype=ndtype)
        assert_equal(test, control)

        ndtype = [('nest', [('idx', int), ('code', object)])]
        with assert_raises_regex(NotImplementedError,
                                 'Nested fields.* not supported.*'):
            test = np.genfromtxt(TextIO(data), delimiter=";",
                                 dtype=ndtype, converters=converters)

        # nested but empty fields also aren't supported
        ndtype = [('idx', int), ('code', object), ('nest', [])]
        with assert_raises_regex(NotImplementedError,
                                 'Nested fields.* not supported.*'):
            test = np.genfromtxt(TextIO(data), delimiter=";",
                                 dtype=ndtype, converters=converters)

    def test_dtype_with_object_no_converter(self):
        # Object without a converter uses bytes:
        parsed = np.genfromtxt(TextIO("1"), dtype=object)
        assert parsed[()] == b"1"
        parsed = np.genfromtxt(TextIO("string"), dtype=object)
        assert parsed[()] == b"string"

    def test_userconverters_with_explicit_dtype(self):
        # Test user_converters w/ explicit (standard) dtype
        data = TextIO('skip,skip,2001-01-01,1.0,skip')
        test = np.genfromtxt(data, delimiter=",", names=None, dtype=float,
                             usecols=(2, 3), converters={2: bytes})
        control = np.array([('2001-01-01', 1.)],
                           dtype=[('', '|S10'), ('', float)])
        assert_equal(test, control)

    def test_utf8_userconverters_with_explicit_dtype(self):
        utf8 = b'\xcf\x96'
        with temppath() as path:
            with open(path, 'wb') as f:
                f.write(b'skip,skip,2001-01-01' + utf8 + b',1.0,skip')
            test = np.genfromtxt(path, delimiter=",", names=None, dtype=float,
                                 usecols=(2, 3), converters={2: str},
                                 encoding='UTF-8')
        control = np.array([('2001-01-01' + utf8.decode('UTF-8'), 1.)],
                           dtype=[('', '|U11'), ('', float)])
        assert_equal(test, control)

    def test_spacedelimiter(self):
        # Test space delimiter
        data = TextIO("1  2  3  4   5\n6  7  8  9  10")
        test = np.genfromtxt(data)
        control = np.array([[1., 2., 3., 4., 5.],
                            [6., 7., 8., 9., 10.]])
        assert_equal(test, control)

    def test_integer_delimiter(self):
        # Test using an integer for delimiter
        data = "  1  2  3\n  4  5 67\n890123  4"
        test = np.genfromtxt(TextIO(data), delimiter=3)
        control = np.array([[1, 2, 3], [4, 5, 67], [890, 123, 4]])
        assert_equal(test, control)

    def test_missing(self):
        data = TextIO('1,2,3,,5\n')
        test = np.genfromtxt(data, dtype=int, delimiter=',',
                            converters={3: lambda s: int(s or - 999)})
        control = np.array([1, 2, 3, -999, 5], int)
        assert_equal(test, control)

    def test_missing_with_tabs(self):
        # Test w/ a delimiter tab
        txt = "1\t2\t3\n\t2\t\n1\t\t3"
        test = np.genfromtxt(TextIO(txt), delimiter="\t",
                             usemask=True,)
        ctrl_d = np.array([(1, 2, 3), (np.nan, 2, np.nan), (1, np.nan, 3)],)
        ctrl_m = np.array([(0, 0, 0), (1, 0, 1), (0, 1, 0)], dtype=bool)
        assert_equal(test.data, ctrl_d)
        assert_equal(test.mask, ctrl_m)

    def test_usecols(self):
        # Test the selection of columns
        # Select 1 column
        control = np.array([[1, 2], [3, 4]], float)
        data = TextIO()
        np.savetxt(data, control)
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=(1,))
        assert_equal(test, control[:, 1])
        #
        control = np.array([[1, 2, 3], [3, 4, 5]], float)
        data = TextIO()
        np.savetxt(data, control)
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=(1, 2))
        assert_equal(test, control[:, 1:])
        # Testing with arrays instead of tuples.
        data.seek(0)
        test = np.genfromtxt(data, dtype=float, usecols=np.array([1, 2]))
        assert_equal(test, control[:, 1:])

    def test_usecols_as_css(self):
        # Test giving usecols with a comma-separated string
        data = "1 2 3\n4 5 6"
        test = np.genfromtxt(TextIO(data),
                             names="a, b, c", usecols="a, c")
        ctrl = np.array([(1, 3), (4, 6)], dtype=[(_, float) for _ in "ac"])
        assert_equal(test, ctrl)

    def test_usecols_with_structured_dtype(self):
        # Test usecols with an explicit structured dtype
        data = TextIO("JOE 70.1 25.3\nBOB 60.5 27.9")
        names = ['stid', 'temp']
        dtypes = ['S4', 'f8']
        test = np.genfromtxt(
            data, usecols=(0, 2), dtype=list(zip(names, dtypes)))
        assert_equal(test['stid'], [b"JOE", b"BOB"])
        assert_equal(test['temp'], [25.3, 27.9])

    def test_usecols_with_integer(self):
        # Test usecols with an integer
        test = np.genfromtxt(TextIO(b"1 2 3\n4 5 6"), usecols=0)
        assert_equal(test, np.array([1., 4.]))

    def test_usecols_with_named_columns(self):
        # Test usecols with named columns
        ctrl = np.array([(1, 3), (4, 6)], dtype=[('a', float), ('c', float)])
        data = "1 2 3\n4 5 6"
        kwargs = {"names": "a, b, c"}
        test = np.genfromtxt(TextIO(data), usecols=(0, -1), **kwargs)
        assert_equal(test, ctrl)
        test = np.genfromtxt(TextIO(data),
                             usecols=('a', 'c'), **kwargs)
        assert_equal(test, ctrl)

    def test_empty_file(self):
        # Test that an empty file raises the proper warning.
        with suppress_warnings() as sup:
            sup.filter(message="genfromtxt: Empty input file:")
            data = TextIO()
            test = np.genfromtxt(data)
            assert_equal(test, np.array([]))

            # when skip_header > 0
            test = np.genfromtxt(data, skip_header=1)
            assert_equal(test, np.array([]))

    def test_fancy_dtype_alt(self):
        # Check that a nested dtype isn't MIA
        data = TextIO('1,2,3.0\n4,5,6.0\n')
        fancydtype = np.dtype([('x', int), ('y', [('t', int), ('s', float)])])
        test = np.genfromtxt(data, dtype=fancydtype, delimiter=',', usemask=True)
        control = ma.array([(1, (2, 3.0)), (4, (5, 6.0))], dtype=fancydtype)
        assert_equal(test, control)

    def test_shaped_dtype(self):
        c = TextIO("aaaa  1.0  8.0  1 2 3 4 5 6")
        dt = np.dtype([('name', 'S4'), ('x', float), ('y', float),
                       ('block', int, (2, 3))])
        x = np.genfromtxt(c, dtype=dt)
        a = np.array([('aaaa', 1.0, 8.0, [[1, 2, 3], [4, 5, 6]])],
                     dtype=dt)
        assert_array_equal(x, a)

    def test_withmissing(self):
        data = TextIO('A,B\n0,1\n2,N/A')
        kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
        test = np.genfromtxt(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        #
        data.seek(0)
        test = np.genfromtxt(data, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', float), ('B', float)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_user_missing_values(self):
        data = "A, B, C\n0, 0., 0j\n1, N/A, 1j\n-9, 2.2, N/A\n3, -99, 3j"
        basekwargs = {"dtype": None, "delimiter": ",", "names": True}
        mdtype = [('A', int), ('B', float), ('C', complex)]
        #
        test = np.genfromtxt(TextIO(data), missing_values="N/A",
                            **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0)],
                           dtype=mdtype)
        assert_equal(test, control)
        #
        basekwargs['dtype'] = mdtype
        test = np.genfromtxt(TextIO(data),
                            missing_values={0: -9, 1: -99, 2: -999j}, usemask=True, **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (1, 0, 1), (0, 1, 0)],
                           dtype=mdtype)
        assert_equal(test, control)
        #
        test = np.genfromtxt(TextIO(data),
                            missing_values={0: -9, 'B': -99, 'C': -999j},
                            usemask=True,
                            **basekwargs)
        control = ma.array([(0, 0.0, 0j), (1, -999, 1j),
                            (-9, 2.2, -999j), (3, -99, 3j)],
                           mask=[(0, 0, 0), (0, 1, 0), (1, 0, 1), (0, 1, 0)],
                           dtype=mdtype)
        assert_equal(test, control)

    def test_user_filling_values(self):
        # Test with missing and filling values
        ctrl = np.array([(0, 3), (4, -999)], dtype=[('a', int), ('b', int)])
        data = "N/A, 2, 3\n4, ,???"
        kwargs = {"delimiter": ",",
                      "dtype": int,
                      "names": "a,b,c",
                      "missing_values": {0: "N/A", 'b': " ", 2: "???"},
                      "filling_values": {0: 0, 'b': 0, 2: -999}}
        test = np.genfromtxt(TextIO(data), **kwargs)
        ctrl = np.array([(0, 2, 3), (4, 0, -999)],
                        dtype=[(_, int) for _ in "abc"])
        assert_equal(test, ctrl)
        #
        test = np.genfromtxt(TextIO(data), usecols=(0, -1), **kwargs)
        ctrl = np.array([(0, 3), (4, -999)], dtype=[(_, int) for _ in "ac"])
        assert_equal(test, ctrl)

        data2 = "1,2,*,4\n5,*,7,8\n"
        test = np.genfromtxt(TextIO(data2), delimiter=',', dtype=int,
                             missing_values="*", filling_values=0)
        ctrl = np.array([[1, 2, 0, 4], [5, 0, 7, 8]])
        assert_equal(test, ctrl)
        test = np.genfromtxt(TextIO(data2), delimiter=',', dtype=int,
                             missing_values="*", filling_values=-1)
        ctrl = np.array([[1, 2, -1, 4], [5, -1, 7, 8]])
        assert_equal(test, ctrl)

    def test_withmissing_float(self):
        data = TextIO('A,B\n0,1.5\n2,-999.00')
        test = np.genfromtxt(data, dtype=None, delimiter=',',
                            missing_values='-999.0', names=True, usemask=True)
        control = ma.array([(0, 1.5), (2, -1.)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', float)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)

    def test_with_masked_column_uniform(self):
        # Test masked column
        data = TextIO('1 2 3\n4 5 6\n')
        test = np.genfromtxt(data, dtype=None,
                             missing_values='2,5', usemask=True)
        control = ma.array([[1, 2, 3], [4, 5, 6]], mask=[[0, 1, 0], [0, 1, 0]])
        assert_equal(test, control)

    def test_with_masked_column_various(self):
        # Test masked column
        data = TextIO('True 2 3\nFalse 5 6\n')
        test = np.genfromtxt(data, dtype=None,
                             missing_values='2,5', usemask=True)
        control = ma.array([(1, 2, 3), (0, 5, 6)],
                           mask=[(0, 1, 0), (0, 1, 0)],
                           dtype=[('f0', bool), ('f1', bool), ('f2', int)])
        assert_equal(test, control)

    def test_invalid_raise(self):
        # Test invalid raise
        data = ["1, 1, 1, 1, 1"] * 50
        for i in range(5):
            data[10 * i] = "2, 2, 2, 2 2"
        data.insert(0, "a, b, c, d, e")
        mdata = TextIO("\n".join(data))

        kwargs = {"delimiter": ",", "dtype": None, "names": True}

        def f():
            return np.genfromtxt(mdata, invalid_raise=False, **kwargs)
        mtest = assert_warns(ConversionWarning, f)
        assert_equal(len(mtest), 45)
        assert_equal(mtest, np.ones(45, dtype=[(_, int) for _ in 'abcde']))
        #
        mdata.seek(0)
        assert_raises(ValueError, np.genfromtxt, mdata,
                      delimiter=",", names=True)

    def test_invalid_raise_with_usecols(self):
        # Test invalid_raise with usecols
        data = ["1, 1, 1, 1, 1"] * 50
        for i in range(5):
            data[10 * i] = "2, 2, 2, 2 2"
        data.insert(0, "a, b, c, d, e")
        mdata = TextIO("\n".join(data))

        kwargs = {"delimiter": ",", "dtype": None, "names": True,
                      "invalid_raise": False}

        def f():
            return np.genfromtxt(mdata, usecols=(0, 4), **kwargs)
        mtest = assert_warns(ConversionWarning, f)
        assert_equal(len(mtest), 45)
        assert_equal(mtest, np.ones(45, dtype=[(_, int) for _ in 'ae']))
        #
        mdata.seek(0)
        mtest = np.genfromtxt(mdata, usecols=(0, 1), **kwargs)
        assert_equal(len(mtest), 50)
        control = np.ones(50, dtype=[(_, int) for _ in 'ab'])
        control[[10 * _ for _ in range(5)]] = (2, 2)
        assert_equal(mtest, control)

    def test_inconsistent_dtype(self):
        # Test inconsistent dtype
        data = ["1, 1, 1, 1, -1.1"] * 50
        mdata = TextIO("\n".join(data))

        converters = {4: lambda x: f"({x.decode()})"}
        kwargs = {"delimiter": ",", "converters": converters,
                      "dtype": [(_, int) for _ in 'abcde'], "encoding": "bytes"}
        assert_raises(ValueError, np.genfromtxt, mdata, **kwargs)

    def test_default_field_format(self):
        # Test default format
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=None, defaultfmt="f%02i")
        ctrl = np.array([(0, 1, 2.3), (4, 5, 6.7)],
                        dtype=[("f00", int), ("f01", int), ("f02", float)])
        assert_equal(mtest, ctrl)

    def test_single_dtype_wo_names(self):
        # Test single dtype w/o names
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, defaultfmt="f%02i")
        ctrl = np.array([[0., 1., 2.3], [4., 5., 6.7]], dtype=float)
        assert_equal(mtest, ctrl)

    def test_single_dtype_w_explicit_names(self):
        # Test single dtype w explicit names
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, names="a, b, c")
        ctrl = np.array([(0., 1., 2.3), (4., 5., 6.7)],
                        dtype=[(_, float) for _ in "abc"])
        assert_equal(mtest, ctrl)

    def test_single_dtype_w_implicit_names(self):
        # Test single dtype w implicit names
        data = "a, b, c\n0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data),
                             delimiter=",", dtype=float, names=True)
        ctrl = np.array([(0., 1., 2.3), (4., 5., 6.7)],
                        dtype=[(_, float) for _ in "abc"])
        assert_equal(mtest, ctrl)

    def test_easy_structured_dtype(self):
        # Test easy structured dtype
        data = "0, 1, 2.3\n4, 5, 6.7"
        mtest = np.genfromtxt(TextIO(data), delimiter=",",
                             dtype=(int, float, float), defaultfmt="f_%02i")
        ctrl = np.array([(0, 1., 2.3), (4, 5., 6.7)],
                        dtype=[("f_00", int), ("f_01", float), ("f_02", float)])
        assert_equal(mtest, ctrl)

    def test_autostrip(self):
        # Test autostrip
        data = "01/01/2003  , 1.3,   abcde"
        kwargs = {"delimiter": ",", "dtype": None, "encoding": "bytes"}
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            mtest = np.genfromtxt(TextIO(data), **kwargs)
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('01/01/2003  ', 1.3, '   abcde')],
                        dtype=[('f0', '|S12'), ('f1', float), ('f2', '|S8')])
        assert_equal(mtest, ctrl)
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            mtest = np.genfromtxt(TextIO(data), autostrip=True, **kwargs)
            assert_(w[0].category is VisibleDeprecationWarning)
        ctrl = np.array([('01/01/2003', 1.3, 'abcde')],
                        dtype=[('f0', '|S10'), ('f1', float), ('f2', '|S5')])
        assert_equal(mtest, ctrl)

    def test_replace_space(self):
        # Test the 'replace_space' option
        txt = "A.A, B (B), C:C\n1, 2, 3.14"
        # Test default: replace ' ' by '_' and delete non-alphanum chars
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None)
        ctrl_dtype = [("AA", int), ("B_B", int), ("CC", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no replace, no delete
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None,
                             replace_space='', deletechars='')
        ctrl_dtype = [("A.A", int), ("B (B)", int), ("C:C", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no delete (spaces are replaced by _)
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=None,
                             deletechars='')
        ctrl_dtype = [("A.A", int), ("B_(B)", int), ("C:C", float)]
        ctrl = np.array((1, 2, 3.14), dtype=ctrl_dtype)
        assert_equal(test, ctrl)

    def test_replace_space_known_dtype(self):
        # Test the 'replace_space' (and related) options when dtype != None
        txt = "A.A, B (B), C:C\n1, 2, 3"
        # Test default: replace ' ' by '_' and delete non-alphanum chars
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int)
        ctrl_dtype = [("AA", int), ("B_B", int), ("CC", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no replace, no delete
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int,
                             replace_space='', deletechars='')
        ctrl_dtype = [("A.A", int), ("B (B)", int), ("C:C", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)
        # Test: no delete (spaces are replaced by _)
        test = np.genfromtxt(TextIO(txt),
                             delimiter=",", names=True, dtype=int,
                             deletechars='')
        ctrl_dtype = [("A.A", int), ("B_(B)", int), ("C:C", int)]
        ctrl = np.array((1, 2, 3), dtype=ctrl_dtype)
        assert_equal(test, ctrl)

    def test_incomplete_names(self):
        # Test w/ incomplete names
        data = "A,,C\n0,1,2\n3,4,5"
        kwargs = {"delimiter": ",", "names": True}
        # w/ dtype=None
        ctrl = np.array([(0, 1, 2), (3, 4, 5)],
                        dtype=[(_, int) for _ in ('A', 'f0', 'C')])
        test = np.genfromtxt(TextIO(data), dtype=None, **kwargs)
        assert_equal(test, ctrl)
        # w/ default dtype
        ctrl = np.array([(0, 1, 2), (3, 4, 5)],
                        dtype=[(_, float) for _ in ('A', 'f0', 'C')])
        test = np.genfromtxt(TextIO(data), **kwargs)

    def test_names_auto_completion(self):
        # Make sure that names are properly completed
        data = "1 2 3\n 4 5 6"
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, float, int), names="a")
        ctrl = np.array([(1, 2, 3), (4, 5, 6)],
                        dtype=[('a', int), ('f0', float), ('f1', int)])
        assert_equal(test, ctrl)

    def test_names_with_usecols_bug1636(self):
        # Make sure we pick up the right names w/ usecols
        data = "A,B,C,D,E\n0,1,2,3,4\n0,1,2,3,4\n0,1,2,3,4"
        ctrl_names = ("A", "C", "E")
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, int, int), delimiter=",",
                             usecols=(0, 2, 4), names=True)
        assert_equal(test.dtype.names, ctrl_names)
        #
        test = np.genfromtxt(TextIO(data),
                             dtype=(int, int, int), delimiter=",",
                             usecols=("A", "C", "E"), names=True)
        assert_equal(test.dtype.names, ctrl_names)
        #
        test = np.genfromtxt(TextIO(data),
                             dtype=int, delimiter=",",
                             usecols=("A", "C", "E"), names=True)
        assert_equal(test.dtype.names, ctrl_names)

    def test_fixed_width_names(self):
        # Test fix-width w/ names
        data = "    A    B   C\n    0    1 2.3\n   45   67   9."
        kwargs = {"delimiter": (5, 5, 4), "names": True, "dtype": None}
        ctrl = np.array([(0, 1, 2.3), (45, 67, 9.)],
                        dtype=[('A', int), ('B', int), ('C', float)])
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)
        #
        kwargs = {"delimiter": 5, "names": True, "dtype": None}
        ctrl = np.array([(0, 1, 2.3), (45, 67, 9.)],
                        dtype=[('A', int), ('B', int), ('C', float)])
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)

    def test_filling_values(self):
        # Test missing values
        data = b"1, 2, 3\n1, , 5\n0, 6, \n"
        kwargs = {"delimiter": ",", "dtype": None, "filling_values": -999}
        ctrl = np.array([[1, 2, 3], [1, -999, 5], [0, 6, -999]], dtype=int)
        test = np.genfromtxt(TextIO(data), **kwargs)
        assert_equal(test, ctrl)

    def test_comments_is_none(self):
        # Github issue 329 (None was previously being converted to 'None').
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO("test1,testNonetherestofthedata"),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1], b'testNonetherestofthedata')
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO("test1, testNonetherestofthedata"),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1], b' testNonetherestofthedata')

    def test_latin1(self):
        latin1 = b'\xf6\xfc\xf6'
        norm = b"norm1,norm2,norm3\n"
        enc = b"test1,testNonethe" + latin1 + b",test3\n"
        s = norm + enc + norm
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(s),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test[1, 0], b"test1")
        assert_equal(test[1, 1], b"testNonethe" + latin1)
        assert_equal(test[1, 2], b"test3")
        test = np.genfromtxt(TextIO(s),
                             dtype=None, comments=None, delimiter=',',
                             encoding='latin1')
        assert_equal(test[1, 0], "test1")
        assert_equal(test[1, 1], "testNonethe" + latin1.decode('latin1'))
        assert_equal(test[1, 2], "test3")

        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(b"0,testNonethe" + latin1),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        assert_equal(test['f0'], 0)
        assert_equal(test['f1'], b"testNonethe" + latin1)

    def test_binary_decode_autodtype(self):
        utf16 = b'\xff\xfeh\x04 \x00i\x04 \x00j\x04'
        v = self.loadfunc(BytesIO(utf16), dtype=None, encoding='UTF-16')
        assert_array_equal(v, np.array(utf16.decode('UTF-16').split()))

    def test_utf8_byte_encoding(self):
        utf8 = b"\xcf\x96"
        norm = b"norm1,norm2,norm3\n"
        enc = b"test1,testNonethe" + utf8 + b",test3\n"
        s = norm + enc + norm
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', '', VisibleDeprecationWarning)
            test = np.genfromtxt(TextIO(s),
                                 dtype=None, comments=None, delimiter=',',
                                 encoding="bytes")
            assert_(w[0].category is VisibleDeprecationWarning)
        ctl = np.array([
                 [b'norm1', b'norm2', b'norm3'],
                 [b'test1', b'testNonethe' + utf8, b'test3'],
                 [b'norm1', b'norm2', b'norm3']])
        assert_array_equal(test, ctl)

    def test_utf8_file(self):
        utf8 = b"\xcf\x96"
        with temppath() as path:
            with open(path, "wb") as f:
                f.write((b"test1,testNonethe" + utf8 + b",test3\n") * 2)
            test = np.genfromtxt(path, dtype=None, comments=None,
                                 delimiter=',', encoding="UTF-8")
            ctl = np.array([
                     ["test1", "testNonethe" + utf8.decode("UTF-8"), "test3"],
                     ["test1", "testNonethe" + utf8.decode("UTF-8"), "test3"]],
                     dtype=np.str_)
            assert_array_equal(test, ctl)

            # test a mixed dtype
            with open(path, "wb") as f:
                f.write(b"0,testNonethe" + utf8)
            test = np.genfromtxt(path, dtype=None, comments=None,
                                 delimiter=',', encoding="UTF-8")
            assert_equal(test['f0'], 0)
            assert_equal(test['f1'], "testNonethe" + utf8.decode("UTF-8"))

    def test_utf8_file_nodtype_unicode(self):
        # bytes encoding with non-latin1 -> unicode upcast
        utf8 = '\u03d6'
        latin1 = '\xf6\xfc\xf6'

        # skip test if cannot encode utf8 test string with preferred
        # encoding. The preferred encoding is assumed to be the default
        # encoding of open. Will need to change this for PyTest, maybe
        # using pytest.mark.xfail(raises=***).
        try:
            encoding = locale.getpreferredencoding()
            utf8.encode(encoding)
        except (UnicodeError, ImportError):
            pytest.skip('Skipping test_utf8_file_nodtype_unicode, '
                        'unable to encode utf8 in preferred encoding')

        with temppath() as path:
            with open(path, "wt") as f:
                f.write("norm1,norm2,norm3\n")
                f.write("norm1," + latin1 + ",norm3\n")
                f.write("test1,testNonethe" + utf8 + ",test3\n")
            with warnings.catch_warnings(record=True) as w:
                warnings.filterwarnings('always', '',
                                        VisibleDeprecationWarning)
                test = np.genfromtxt(path, dtype=None, comments=None,
                                     delimiter=',', encoding="bytes")
                # Check for warning when encoding not specified.
                assert_(w[0].category is VisibleDeprecationWarning)
            ctl = np.array([
                     ["norm1", "norm2", "norm3"],
                     ["norm1", latin1, "norm3"],
                     ["test1", "testNonethe" + utf8, "test3"]],
                     dtype=np.str_)
            assert_array_equal(test, ctl)

    @pytest.mark.filterwarnings("ignore:.*recfromtxt.*:DeprecationWarning")
    def test_recfromtxt(self):
        #
        data = TextIO('A,B\n0,1\n2,3')
        kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
        test = recfromtxt(data, **kwargs)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('A', int), ('B', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,N/A')
        test = recfromtxt(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        assert_equal(test.A, [0, 2])

    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_recfromcsv(self):
        #
        data = TextIO('A,B\n0,1\n2,3')
        kwargs = {"missing_values": "N/A", "names": True, "case_sensitive": True,
                      "encoding": "bytes"}
        test = recfromcsv(data, dtype=None, **kwargs)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('A', int), ('B', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,N/A')
        test = recfromcsv(data, dtype=None, usemask=True, **kwargs)
        control = ma.array([(0, 1), (2, -1)],
                           mask=[(False, False), (False, True)],
                           dtype=[('A', int), ('B', int)])
        assert_equal(test, control)
        assert_equal(test.mask, control.mask)
        assert_equal(test.A, [0, 2])
        #
        data = TextIO('A,B\n0,1\n2,3')
        test = recfromcsv(data, missing_values='N/A',)
        control = np.array([(0, 1), (2, 3)],
                           dtype=[('a', int), ('b', int)])
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)
        #
        data = TextIO('A,B\n0,1\n2,3')
        dtype = [('a', int), ('b', float)]
        test = recfromcsv(data, missing_values='N/A', dtype=dtype)
        control = np.array([(0, 1), (2, 3)],
                           dtype=dtype)
        assert_(isinstance(test, np.recarray))
        assert_equal(test, control)

        # gh-10394
        data = TextIO('color\n"red"\n"blue"')
        test = recfromcsv(data, converters={0: lambda x: x.strip('\"')})
        control = np.array([('red',), ('blue',)], dtype=[('color', (str, 4))])
        assert_equal(test.dtype, control.dtype)
        assert_equal(test, control)

    def test_max_rows(self):
        # Test the `max_rows` keyword argument.
        data = '1 2\n3 4\n5 6\n7 8\n9 10\n'
        txt = TextIO(data)
        a1 = np.genfromtxt(txt, max_rows=3)
        a2 = np.genfromtxt(txt)
        assert_equal(a1, [[1, 2], [3, 4], [5, 6]])
        assert_equal(a2, [[7, 8], [9, 10]])

        # max_rows must be at least 1.
        assert_raises(ValueError, np.genfromtxt, TextIO(data), max_rows=0)

        # An input with several invalid rows.
        data = '1 1\n2 2\n0 \n3 3\n4 4\n5  \n6  \n7  \n'

        test = np.genfromtxt(TextIO(data), max_rows=2)
        control = np.array([[1., 1.], [2., 2.]])
        assert_equal(test, control)

        # Test keywords conflict
        assert_raises(ValueError, np.genfromtxt, TextIO(data), skip_footer=1,
                      max_rows=4)

        # Test with invalid value
        assert_raises(ValueError, np.genfromtxt, TextIO(data), max_rows=4)

        # Test with invalid not raise
        with suppress_warnings() as sup:
            sup.filter(ConversionWarning)

            test = np.genfromtxt(TextIO(data), max_rows=4, invalid_raise=False)
            control = np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]])
            assert_equal(test, control)

            test = np.genfromtxt(TextIO(data), max_rows=5, invalid_raise=False)
            control = np.array([[1., 1.], [2., 2.], [3., 3.], [4., 4.]])
            assert_equal(test, control)

        # Structured array with field names.
        data = 'a b\n#c d\n1 1\n2 2\n#0 \n3 3\n4 4\n5  5\n'

        # Test with header, names and comments
        txt = TextIO(data)
        test = np.genfromtxt(txt, skip_header=1, max_rows=3, names=True)
        control = np.array([(1.0, 1.0), (2.0, 2.0), (3.0, 3.0)],
                      dtype=[('c', '<f8'), ('d', '<f8')])
        assert_equal(test, control)
        # To continue reading the same "file", don't use skip_header or
        # names, and use the previously determined dtype.
        test = np.genfromtxt(txt, max_rows=None, dtype=test.dtype)
        control = np.array([(4.0, 4.0), (5.0, 5.0)],
                      dtype=[('c', '<f8'), ('d', '<f8')])
        assert_equal(test, control)

    def test_gft_using_filename(self):
        # Test that we can load data from a filename as well as a file
        # object
        tgt = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')

        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            with temppath() as name:
                with open(name, 'w') as f:
                    f.write(data)
                res = np.genfromtxt(name)
            assert_array_equal(res, tgt)

    def test_gft_from_gzip(self):
        # Test that we can load data from a gzipped file
        wanted = np.arange(6).reshape((2, 3))
        linesep = ('\n', '\r\n', '\r')

        for sep in linesep:
            data = '0 1 2' + sep + '3 4 5'
            s = BytesIO()
            with gzip.GzipFile(fileobj=s, mode='w') as g:
                g.write(asbytes(data))

            with temppath(suffix='.gz2') as name:
                with open(name, 'w') as f:
                    f.write(data)
                assert_array_equal(np.genfromtxt(name), wanted)

    def test_gft_using_generator(self):
        # gft doesn't work with unicode.
        def count():
            for i in range(10):
                yield asbytes("%d" % i)

        res = np.genfromtxt(count())
        assert_array_equal(res, np.arange(10))

    def test_auto_dtype_largeint(self):
        # Regression test for numpy/numpy#5635 whereby large integers could
        # cause OverflowErrors.

        # Test the automatic definition of the output dtype
        #
        # 2**66 = 73786976294838206464 => should convert to float
        # 2**34 = 17179869184 => should convert to int64
        # 2**10 = 1024 => should convert to int (int32 on 32-bit systems,
        #                 int64 on 64-bit systems)

        data = TextIO('73786976294838206464 17179869184 1024')

        test = np.genfromtxt(data, dtype=None)

        assert_equal(test.dtype.names, ['f0', 'f1', 'f2'])

        assert_(test.dtype['f0'] == float)
        assert_(test.dtype['f1'] == np.int64)
        assert_(test.dtype['f2'] == np.int_)

        assert_allclose(test['f0'], 73786976294838206464.)
        assert_equal(test['f1'], 17179869184)
        assert_equal(test['f2'], 1024)

    def test_unpack_float_data(self):
        txt = TextIO("1,2,3\n4,5,6\n7,8,9\n0.0,1.0,2.0")
        a, b, c = np.loadtxt(txt, delimiter=",", unpack=True)
        assert_array_equal(a, np.array([1.0, 4.0, 7.0, 0.0]))
        assert_array_equal(b, np.array([2.0, 5.0, 8.0, 1.0]))
        assert_array_equal(c, np.array([3.0, 6.0, 9.0, 2.0]))

    def test_unpack_structured(self):
        # Regression test for gh-4341
        # Unpacking should work on structured arrays
        txt = TextIO("M 21 72\nF 35 58")
        dt = {'names': ('a', 'b', 'c'), 'formats': ('S1', 'i4', 'f4')}
        a, b, c = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_equal(a.dtype, np.dtype('S1'))
        assert_equal(b.dtype, np.dtype('i4'))
        assert_equal(c.dtype, np.dtype('f4'))
        assert_array_equal(a, np.array([b'M', b'F']))
        assert_array_equal(b, np.array([21, 35]))
        assert_array_equal(c, np.array([72.,  58.]))

    def test_unpack_auto_dtype(self):
        # Regression test for gh-4341
        # Unpacking should work when dtype=None
        txt = TextIO("M 21 72.\nF 35 58.")
        expected = (np.array(["M", "F"]), np.array([21, 35]), np.array([72., 58.]))
        test = np.genfromtxt(txt, dtype=None, unpack=True, encoding="utf-8")
        for arr, result in zip(expected, test):
            assert_array_equal(arr, result)
            assert_equal(arr.dtype, result.dtype)

    def test_unpack_single_name(self):
        # Regression test for gh-4341
        # Unpacking should work when structured dtype has only one field
        txt = TextIO("21\n35")
        dt = {'names': ('a',), 'formats': ('i4',)}
        expected = np.array([21, 35], dtype=np.int32)
        test = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_array_equal(expected, test)
        assert_equal(expected.dtype, test.dtype)

    def test_squeeze_scalar(self):
        # Regression test for gh-4341
        # Unpacking a scalar should give zero-dim output,
        # even if dtype is structured
        txt = TextIO("1")
        dt = {'names': ('a',), 'formats': ('i4',)}
        expected = np.array((1,), dtype=np.int32)
        test = np.genfromtxt(txt, dtype=dt, unpack=True)
        assert_array_equal(expected, test)
        assert_equal((), test.shape)
        assert_equal(expected.dtype, test.dtype)

    @pytest.mark.parametrize("ndim", [0, 1, 2])
    def test_ndmin_keyword(self, ndim: int):
        # lets have the same behaviour of ndmin as loadtxt
        # as they should be the same for non-missing values
        txt = "42"

        a = np.loadtxt(StringIO(txt), ndmin=ndim)
        b = np.genfromtxt(StringIO(txt), ndmin=ndim)

        assert_array_equal(a, b)


class TestPathUsage:
    # Test that pathlib.Path can be used
    def test_loadtxt(self):
        with temppath(suffix='.txt') as path:
            path = Path(path)
            a = np.array([[1.1, 2], [3, 4]])
            np.savetxt(path, a)
            x = np.loadtxt(path)
            assert_array_equal(x, a)

    def test_save_load(self):
        # Test that pathlib.Path instances can be used with save.
        with temppath(suffix='.npy') as path:
            path = Path(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            data = np.load(path)
            assert_array_equal(data, a)

    def test_save_load_memmap(self):
        # Test that pathlib.Path instances can be loaded mem-mapped.
        with temppath(suffix='.npy') as path:
            path = Path(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            data = np.load(path, mmap_mode='r')
            assert_array_equal(data, a)
            # close the mem-mapped file
            del data
            if IS_PYPY:
                break_cycles()
                break_cycles()

    @pytest.mark.xfail(IS_WASM, reason="memmap doesn't work correctly")
    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_save_load_memmap_readwrite(self, filename_type):
        with temppath(suffix='.npy') as path:
            path = filename_type(path)
            a = np.array([[1, 2], [3, 4]], int)
            np.save(path, a)
            b = np.load(path, mmap_mode='r+')
            a[0][0] = 5
            b[0][0] = 5
            del b  # closes the file
            if IS_PYPY:
                break_cycles()
                break_cycles()
            data = np.load(path)
            assert_array_equal(data, a)

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_savez_load(self, filename_type):
        with temppath(suffix='.npz') as path:
            path = filename_type(path)
            np.savez(path, lab='place holder')
            with np.load(path) as data:
                assert_array_equal(data['lab'], 'place holder')

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_savez_compressed_load(self, filename_type):
        with temppath(suffix='.npz') as path:
            path = filename_type(path)
            np.savez_compressed(path, lab='place holder')
            data = np.load(path)
            assert_array_equal(data['lab'], 'place holder')
            data.close()

    @pytest.mark.parametrize("filename_type", [Path, str])
    def test_genfromtxt(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            a = np.array([(1, 2), (3, 4)])
            np.savetxt(path, a)
            data = np.genfromtxt(path)
            assert_array_equal(a, data)

    @pytest.mark.parametrize("filename_type", [Path, str])
    @pytest.mark.filterwarnings("ignore:.*recfromtxt.*:DeprecationWarning")
    def test_recfromtxt(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            with open(path, 'w') as f:
                f.write('A,B\n0,1\n2,3')

            kwargs = {"delimiter": ",", "missing_values": "N/A", "names": True}
            test = recfromtxt(path, **kwargs)
            control = np.array([(0, 1), (2, 3)],
                               dtype=[('A', int), ('B', int)])
            assert_(isinstance(test, np.recarray))
            assert_equal(test, control)

    @pytest.mark.parametrize("filename_type", [Path, str])
    @pytest.mark.filterwarnings("ignore:.*recfromcsv.*:DeprecationWarning")
    def test_recfromcsv(self, filename_type):
        with temppath(suffix='.txt') as path:
            path = filename_type(path)
            with open(path, 'w') as f:
                f.write('A,B\n0,1\n2,3')

            kwargs = {
                "missing_values": "N/A", "names": True, "case_sensitive": True
            }
            test = recfromcsv(path, dtype=None, **kwargs)
            control = np.array([(0, 1), (2, 3)],
                               dtype=[('A', int), ('B', int)])
            assert_(isinstance(test, np.recarray))
            assert_equal(test, control)


def test_gzip_load():
    a = np.random.random((5, 5))

    s = BytesIO()
    f = gzip.GzipFile(fileobj=s, mode="w")

    np.save(f, a)
    f.close()
    s.seek(0)

    f = gzip.GzipFile(fileobj=s, mode="r")
    assert_array_equal(np.load(f), a)


# These next two classes encode the minimal API needed to save()/load() arrays.
# The `test_ducktyping` ensures they work correctly
class JustWriter:
    def __init__(self, base):
        self.base = base

    def write(self, s):
        return self.base.write(s)

    def flush(self):
        return self.base.flush()

class JustReader:
    def __init__(self, base):
        self.base = base

    def read(self, n):
        return self.base.read(n)

    def seek(self, off, whence=0):
        return self.base.seek(off, whence)


def test_ducktyping():
    a = np.random.random((5, 5))

    s = BytesIO()
    f = JustWriter(s)

    np.save(f, a)
    f.flush()
    s.seek(0)

    f = JustReader(s)
    assert_array_equal(np.load(f), a)


def test_gzip_loadtxt():
    # Thanks to another windows brokenness, we can't use
    # NamedTemporaryFile: a file created from this function cannot be
    # reopened by another open call. So we first put the gzipped string
    # of the test reference array, write it to a securely opened file,
    # which is then read from by the loadtxt function
    s = BytesIO()
    g = gzip.GzipFile(fileobj=s, mode='w')
    g.write(b'1 2 3\n')
    g.close()

    s.seek(0)
    with temppath(suffix='.gz') as name:
        with open(name, 'wb') as f:
            f.write(s.read())
        res = np.loadtxt(name)
    s.close()

    assert_array_equal(res, [1, 2, 3])


def test_gzip_loadtxt_from_string():
    s = BytesIO()
    f = gzip.GzipFile(fileobj=s, mode="w")
    f.write(b'1 2 3\n')
    f.close()
    s.seek(0)

    f = gzip.GzipFile(fileobj=s, mode="r")
    assert_array_equal(np.loadtxt(f), [1, 2, 3])


def test_npzfile_dict():
    s = BytesIO()
    x = np.zeros((3, 3))
    y = np.zeros((3, 3))

    np.savez(s, x=x, y=y)
    s.seek(0)

    z = np.load(s)

    assert_('x' in z)
    assert_('y' in z)
    assert_('x' in z.keys())
    assert_('y' in z.keys())

    for f, a in z.items():
        assert_(f in ['x', 'y'])
        assert_equal(a.shape, (3, 3))

    for a in z.values():
        assert_equal(a.shape, (3, 3))

    assert_(len(z.items()) == 2)

    for f in z:
        assert_(f in ['x', 'y'])

    assert_('x' in z.keys())
    assert (z.get('x') == z['x']).all()


@pytest.mark.skipif(not HAS_REFCOUNT, reason="Python lacks refcounts")
def test_load_refcount():
    # Check that objects returned by np.load are directly freed based on
    # their refcount, rather than needing the gc to collect them.

    f = BytesIO()
    np.savez(f, [1, 2, 3])
    f.seek(0)

    with assert_no_gc_cycles():
        np.load(f)

    f.seek(0)
    dt = [("a", 'u1', 2), ("b", 'u1', 2)]
    with assert_no_gc_cycles():
        x = np.loadtxt(TextIO("0 1 2 3"), dtype=dt)
        assert_equal(x, np.array([((0, 1), (2, 3))], dtype=dt))


def test_load_multiple_arrays_until_eof():
    f = BytesIO()
    np.save(f, 1)
    np.save(f, 2)
    f.seek(0)
    out1 = np.load(f)
    assert out1 == 1
    out2 = np.load(f)
    assert out2 == 2
    with pytest.raises(EOFError):
        np.load(f)


def test_savez_nopickle():
    obj_array = np.array([1, 'hello'], dtype=object)
    with temppath(suffix='.npz') as tmp:
        np.savez(tmp, obj_array)

    with temppath(suffix='.npz') as tmp:
        with pytest.raises(ValueError, match="Object arrays cannot be saved when.*"):
            np.savez(tmp, obj_array, allow_pickle=False)

    with temppath(suffix='.npz') as tmp:
        np.savez_compressed(tmp, obj_array)

    with temppath(suffix='.npz') as tmp:
        with pytest.raises(ValueError, match="Object arrays cannot be saved when.*"):
            np.savez_compressed(tmp, obj_array, allow_pickle=False)