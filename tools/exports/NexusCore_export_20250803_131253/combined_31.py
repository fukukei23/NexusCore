
# === NexusCore/app\extensions.py ===
from celery import Celery, Task

def celery_init_app(app):
    class ContextTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery = Celery(app.import_name)
    celery.config_from_object(app.config["CELERY"])
    celery.Task = ContextTask
    app.celery = celery            # ← 外部から参照できるよう保持
    return celery

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\vertex\_client.py ===
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Union, Mapping, TypeVar
from typing_extensions import Self, override

import httpx

from ... import _exceptions
from ._auth import load_auth, refresh_auth
from ._beta import Beta, AsyncBeta
from ..._types import NOT_GIVEN, NotGiven, Transport, ProxiesTypes, AsyncTransport
from ..._utils import is_dict, asyncify, is_given
from ..._compat import model_copy, typed_cached_property
from ..._models import FinalRequestOptions
from ..._version import __version__
from ..._streaming import Stream, AsyncStream
from ..._exceptions import APIStatusError
from ..._base_client import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_CONNECTION_LIMITS,
    BaseClient,
    SyncAPIClient,
    AsyncAPIClient,
    SyncHttpxClientWrapper,
    AsyncHttpxClientWrapper,
)
from ...resources.messages import Messages, AsyncMessages

if TYPE_CHECKING:
    from google.auth.credentials import Credentials as GoogleCredentials  # type: ignore


DEFAULT_VERSION = "vertex-2023-10-16"

_HttpxClientT = TypeVar("_HttpxClientT", bound=Union[httpx.Client, httpx.AsyncClient])
_DefaultStreamT = TypeVar("_DefaultStreamT", bound=Union[Stream[Any], AsyncStream[Any]])


class BaseVertexClient(BaseClient[_HttpxClientT, _DefaultStreamT]):
    @typed_cached_property
    def region(self) -> str:
        raise RuntimeError("region not set")

    @typed_cached_property
    def project_id(self) -> str | None:
        project_id = os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID")
        if project_id:
            return project_id

        return None

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


class AnthropicVertex(BaseVertexClient[httpx.Client, Stream[Any]], SyncAPIClient):
    messages: Messages
    beta: Beta

    def __init__(
        self,
        *,
        region: str | NotGiven = NOT_GIVEN,
        project_id: str | NotGiven = NOT_GIVEN,
        access_token: str | None = None,
        credentials: GoogleCredentials | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client. See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.Client | None = None,
        # See httpx documentation for [custom transports](https://www.python-httpx.org/advanced/#custom-transports)
        transport: Transport | None = None,
        # See httpx documentation for [proxies](https://www.python-httpx.org/advanced/#http-proxying)
        proxies: ProxiesTypes | None = None,
        # See httpx documentation for [limits](https://www.python-httpx.org/advanced/#pool-limit-configuration)
        connection_pool_limits: httpx.Limits | None = None,
        _strict_response_validation: bool = False,
    ) -> None:
        if not is_given(region):
            region = os.environ.get("CLOUD_ML_REGION", NOT_GIVEN)
        if not is_given(region):
            raise ValueError(
                "No region was given. The client should be instantiated with the `region` argument or the `CLOUD_ML_REGION` environment variable should be set."
            )

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_VERTEX_BASE_URL")
            if base_url is None:
                base_url = f"https://{region}-aiplatform.googleapis.com/v1"

        super().__init__(
            version=__version__,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            custom_headers=default_headers,
            custom_query=default_query,
            http_client=http_client,
            transport=transport,
            proxies=proxies,
            limits=connection_pool_limits,
            _strict_response_validation=_strict_response_validation,
        )

        if is_given(project_id):
            self.project_id = project_id

        self.region = region
        self.access_token = access_token
        self.credentials = credentials

        self.messages = Messages(self)
        self.beta = Beta(self)

    @override
    def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        return _prepare_options(options, project_id=self.project_id, region=self.region)

    @override
    def _prepare_request(self, request: httpx.Request) -> None:
        if request.headers.get("Authorization"):
            # already authenticated, nothing for us to do
            return

        request.headers["Authorization"] = f"Bearer {self._ensure_access_token()}"

    def _ensure_access_token(self) -> str:
        if self.access_token is not None:
            return self.access_token

        if not self.credentials:
            self.credentials, project_id = load_auth(project_id=self.project_id)
            if not self.project_id:
                self.project_id = project_id

        if self.credentials.expired or not self.credentials.token:
            refresh_auth(self.credentials)

        if not self.credentials.token:
            raise RuntimeError("Could not resolve API token from the environment")

        assert isinstance(self.credentials.token, str)
        return self.credentials.token

    def copy(
        self,
        *,
        region: str | NotGiven = NOT_GIVEN,
        project_id: str | NotGiven = NOT_GIVEN,
        access_token: str | None = None,
        credentials: GoogleCredentials | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.Client | None = None,
        connection_pool_limits: httpx.Limits | None = None,
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

        if connection_pool_limits is not None:
            if http_client is not None:
                raise ValueError("The 'http_client' argument is mutually exclusive with 'connection_pool_limits'")

            if not isinstance(self._client, SyncHttpxClientWrapper):
                raise ValueError(
                    "A custom HTTP client has been set and is mutually exclusive with the 'connection_pool_limits' argument"
                )

            http_client = None
        else:
            if self._limits is not DEFAULT_CONNECTION_LIMITS:
                connection_pool_limits = self._limits
            else:
                connection_pool_limits = None

            http_client = http_client or self._client

        return self.__class__(
            region=region if is_given(region) else self.region,
            project_id=project_id if is_given(project_id) else self.project_id or NOT_GIVEN,
            access_token=access_token or self.access_token,
            credentials=credentials or self.credentials,
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


class AsyncAnthropicVertex(BaseVertexClient[httpx.AsyncClient, AsyncStream[Any]], AsyncAPIClient):
    messages: AsyncMessages
    beta: AsyncBeta

    def __init__(
        self,
        *,
        region: str | NotGiven = NOT_GIVEN,
        project_id: str | NotGiven = NOT_GIVEN,
        access_token: str | None = None,
        credentials: GoogleCredentials | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client. See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.AsyncClient | None = None,
        # See httpx documentation for [custom transports](https://www.python-httpx.org/advanced/#custom-transports)
        transport: AsyncTransport | None = None,
        # See httpx documentation for [proxies](https://www.python-httpx.org/advanced/#http-proxying)
        proxies: ProxiesTypes | None = None,
        # See httpx documentation for [limits](https://www.python-httpx.org/advanced/#pool-limit-configuration)
        connection_pool_limits: httpx.Limits | None = None,
        _strict_response_validation: bool = False,
    ) -> None:
        if not is_given(region):
            region = os.environ.get("CLOUD_ML_REGION", NOT_GIVEN)
        if not is_given(region):
            raise ValueError(
                "No region was given. The client should be instantiated with the `region` argument or the `CLOUD_ML_REGION` environment variable should be set."
            )

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_VERTEX_BASE_URL")
            if base_url is None:
                base_url = f"https://{region}-aiplatform.googleapis.com/v1"

        super().__init__(
            version=__version__,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            custom_headers=default_headers,
            custom_query=default_query,
            http_client=http_client,
            transport=transport,
            proxies=proxies,
            limits=connection_pool_limits,
            _strict_response_validation=_strict_response_validation,
        )

        if is_given(project_id):
            self.project_id = project_id

        self.region = region
        self.access_token = access_token
        self.credentials = credentials

        self.messages = AsyncMessages(self)
        self.beta = AsyncBeta(self)

    @override
    async def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        return _prepare_options(options, project_id=self.project_id, region=self.region)

    @override
    async def _prepare_request(self, request: httpx.Request) -> None:
        if request.headers.get("Authorization"):
            # already authenticated, nothing for us to do
            return

        request.headers["Authorization"] = f"Bearer {await self._ensure_access_token()}"

    async def _ensure_access_token(self) -> str:
        if self.access_token is not None:
            return self.access_token

        if not self.credentials:
            self.credentials, project_id = await asyncify(load_auth)(project_id=self.project_id)
            if not self.project_id:
                self.project_id = project_id

        if self.credentials.expired or not self.credentials.token:
            await asyncify(refresh_auth)(self.credentials)

        if not self.credentials.token:
            raise RuntimeError("Could not resolve API token from the environment")

        assert isinstance(self.credentials.token, str)
        return self.credentials.token

    def copy(
        self,
        *,
        region: str | NotGiven = NOT_GIVEN,
        project_id: str | NotGiven = NOT_GIVEN,
        access_token: str | None = None,
        credentials: GoogleCredentials | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.AsyncClient | None = None,
        connection_pool_limits: httpx.Limits | None = None,
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

        if connection_pool_limits is not None:
            if http_client is not None:
                raise ValueError("The 'http_client' argument is mutually exclusive with 'connection_pool_limits'")

            if not isinstance(self._client, AsyncHttpxClientWrapper):
                raise ValueError(
                    "A custom HTTP client has been set and is mutually exclusive with the 'connection_pool_limits' argument"
                )

            http_client = None
        else:
            if self._limits is not DEFAULT_CONNECTION_LIMITS:
                connection_pool_limits = self._limits
            else:
                connection_pool_limits = None

            http_client = http_client or self._client

        return self.__class__(
            region=region if is_given(region) else self.region,
            project_id=project_id if is_given(project_id) else self.project_id or NOT_GIVEN,
            access_token=access_token or self.access_token,
            credentials=credentials or self.credentials,
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


def _prepare_options(input_options: FinalRequestOptions, *, project_id: str | None, region: str) -> FinalRequestOptions:
    options = model_copy(input_options, deep=True)

    if is_dict(options.json_data):
        options.json_data.setdefault("anthropic_version", DEFAULT_VERSION)

    if options.url in {"/v1/messages", "/v1/messages?beta=true"} and options.method == "post":
        if project_id is None:
            raise RuntimeError(
                "No project_id was given and it could not be resolved from credentials. The client should be instantiated with the `project_id` argument or the `ANTHROPIC_VERTEX_PROJECT_ID` environment variable should be set."
            )

        if not is_dict(options.json_data):
            raise RuntimeError("Expected json data to be a dictionary for post /v1/messages")

        model = options.json_data.pop("model")
        stream = options.json_data.get("stream", False)
        specifier = "streamRawPredict" if stream else "rawPredict"

        options.url = f"/projects/{project_id}/locations/{region}/publishers/anthropic/models/{model}:{specifier}"

        if is_dict(options.json_data):
            options.json_data.pop("model", None)

    return options

# === NexusCore/src\modules\diff_viewer.py ===
# modules/diff_viewer.py

import difflib

def generate_diff(old_code: str, new_code: str) -> str:
    diff = difflib.unified_diff(
        old_code.splitlines(),
        new_code.splitlines(),
        fromfile='Before',
        tofile='After',
        lineterm=''
    )
    return "\n".join(diff)

# === NexusCore/src\tests\test_sample.py ===
import pytest
from sample import add_two_integers

def test_add_two_integers():
    assert add_two_integers(1, 2) == 3
    assert add_two_integers(-1, -2) == -3
    assert add_two_integers(0, 0) == 0

    with pytest.raises(TypeError):
        add_two_integers("1", 2)

    with pytest.raises(TypeError):
        add_two_integers(1, "2")

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\app\extensions.py ===
from celery import Celery, Task

def celery_init_app(app):
    class ContextTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery = Celery(app.import_name)
    celery.config_from_object(app.config["CELERY"])
    celery.Task = ContextTask
    app.celery = celery            # ← 外部から参照できるよう保持
    return celery

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\anthropic\lib\vertex\_client.py ===
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Union, Mapping, TypeVar
from typing_extensions import Self, override

import httpx

from ... import _exceptions
from ._auth import load_auth, refresh_auth
from ._beta import Beta, AsyncBeta
from ..._types import NOT_GIVEN, NotGiven, Transport, ProxiesTypes, AsyncTransport
from ..._utils import is_dict, asyncify, is_given
from ..._compat import model_copy, typed_cached_property
from ..._models import FinalRequestOptions
from ..._version import __version__
from ..._streaming import Stream, AsyncStream
from ..._exceptions import APIStatusError
from ..._base_client import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_CONNECTION_LIMITS,
    BaseClient,
    SyncAPIClient,
    AsyncAPIClient,
    SyncHttpxClientWrapper,
    AsyncHttpxClientWrapper,
)
from ...resources.messages import Messages, AsyncMessages

if TYPE_CHECKING:
    from google.auth.credentials import Credentials as GoogleCredentials  # type: ignore


DEFAULT_VERSION = "vertex-2023-10-16"

_HttpxClientT = TypeVar("_HttpxClientT", bound=Union[httpx.Client, httpx.AsyncClient])
_DefaultStreamT = TypeVar("_DefaultStreamT", bound=Union[Stream[Any], AsyncStream[Any]])


class BaseVertexClient(BaseClient[_HttpxClientT, _DefaultStreamT]):
    @typed_cached_property
    def region(self) -> str:
        raise RuntimeError("region not set")

    @typed_cached_property
    def project_id(self) -> str | None:
        project_id = os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID")
        if project_id:
            return project_id

        return None

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


class AnthropicVertex(BaseVertexClient[httpx.Client, Stream[Any]], SyncAPIClient):
    messages: Messages
    beta: Beta

    def __init__(
        self,
        *,
        region: str | NotGiven = NOT_GIVEN,
        project_id: str | NotGiven = NOT_GIVEN,
        access_token: str | None = None,
        credentials: GoogleCredentials | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client. See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.Client | None = None,
        # See httpx documentation for [custom transports](https://www.python-httpx.org/advanced/#custom-transports)
        transport: Transport | None = None,
        # See httpx documentation for [proxies](https://www.python-httpx.org/advanced/#http-proxying)
        proxies: ProxiesTypes | None = None,
        # See httpx documentation for [limits](https://www.python-httpx.org/advanced/#pool-limit-configuration)
        connection_pool_limits: httpx.Limits | None = None,
        _strict_response_validation: bool = False,
    ) -> None:
        if not is_given(region):
            region = os.environ.get("CLOUD_ML_REGION", NOT_GIVEN)
        if not is_given(region):
            raise ValueError(
                "No region was given. The client should be instantiated with the `region` argument or the `CLOUD_ML_REGION` environment variable should be set."
            )

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_VERTEX_BASE_URL")
            if base_url is None:
                base_url = f"https://{region}-aiplatform.googleapis.com/v1"

        super().__init__(
            version=__version__,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            custom_headers=default_headers,
            custom_query=default_query,
            http_client=http_client,
            transport=transport,
            proxies=proxies,
            limits=connection_pool_limits,
            _strict_response_validation=_strict_response_validation,
        )

        if is_given(project_id):
            self.project_id = project_id

        self.region = region
        self.access_token = access_token
        self.credentials = credentials

        self.messages = Messages(self)
        self.beta = Beta(self)

    @override
    def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        return _prepare_options(options, project_id=self.project_id, region=self.region)

    @override
    def _prepare_request(self, request: httpx.Request) -> None:
        if request.headers.get("Authorization"):
            # already authenticated, nothing for us to do
            return

        request.headers["Authorization"] = f"Bearer {self._ensure_access_token()}"

    def _ensure_access_token(self) -> str:
        if self.access_token is not None:
            return self.access_token

        if not self.credentials:
            self.credentials, project_id = load_auth(project_id=self.project_id)
            if not self.project_id:
                self.project_id = project_id

        if self.credentials.expired or not self.credentials.token:
            refresh_auth(self.credentials)

        if not self.credentials.token:
            raise RuntimeError("Could not resolve API token from the environment")

        assert isinstance(self.credentials.token, str)
        return self.credentials.token

    def copy(
        self,
        *,
        region: str | NotGiven = NOT_GIVEN,
        project_id: str | NotGiven = NOT_GIVEN,
        access_token: str | None = None,
        credentials: GoogleCredentials | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.Client | None = None,
        connection_pool_limits: httpx.Limits | None = None,
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

        if connection_pool_limits is not None:
            if http_client is not None:
                raise ValueError("The 'http_client' argument is mutually exclusive with 'connection_pool_limits'")

            if not isinstance(self._client, SyncHttpxClientWrapper):
                raise ValueError(
                    "A custom HTTP client has been set and is mutually exclusive with the 'connection_pool_limits' argument"
                )

            http_client = None
        else:
            if self._limits is not DEFAULT_CONNECTION_LIMITS:
                connection_pool_limits = self._limits
            else:
                connection_pool_limits = None

            http_client = http_client or self._client

        return self.__class__(
            region=region if is_given(region) else self.region,
            project_id=project_id if is_given(project_id) else self.project_id or NOT_GIVEN,
            access_token=access_token or self.access_token,
            credentials=credentials or self.credentials,
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


class AsyncAnthropicVertex(BaseVertexClient[httpx.AsyncClient, AsyncStream[Any]], AsyncAPIClient):
    messages: AsyncMessages
    beta: AsyncBeta

    def __init__(
        self,
        *,
        region: str | NotGiven = NOT_GIVEN,
        project_id: str | NotGiven = NOT_GIVEN,
        access_token: str | None = None,
        credentials: GoogleCredentials | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client. See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.AsyncClient | None = None,
        # See httpx documentation for [custom transports](https://www.python-httpx.org/advanced/#custom-transports)
        transport: AsyncTransport | None = None,
        # See httpx documentation for [proxies](https://www.python-httpx.org/advanced/#http-proxying)
        proxies: ProxiesTypes | None = None,
        # See httpx documentation for [limits](https://www.python-httpx.org/advanced/#pool-limit-configuration)
        connection_pool_limits: httpx.Limits | None = None,
        _strict_response_validation: bool = False,
    ) -> None:
        if not is_given(region):
            region = os.environ.get("CLOUD_ML_REGION", NOT_GIVEN)
        if not is_given(region):
            raise ValueError(
                "No region was given. The client should be instantiated with the `region` argument or the `CLOUD_ML_REGION` environment variable should be set."
            )

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_VERTEX_BASE_URL")
            if base_url is None:
                base_url = f"https://{region}-aiplatform.googleapis.com/v1"

        super().__init__(
            version=__version__,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            custom_headers=default_headers,
            custom_query=default_query,
            http_client=http_client,
            transport=transport,
            proxies=proxies,
            limits=connection_pool_limits,
            _strict_response_validation=_strict_response_validation,
        )

        if is_given(project_id):
            self.project_id = project_id

        self.region = region
        self.access_token = access_token
        self.credentials = credentials

        self.messages = AsyncMessages(self)
        self.beta = AsyncBeta(self)

    @override
    async def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        return _prepare_options(options, project_id=self.project_id, region=self.region)

    @override
    async def _prepare_request(self, request: httpx.Request) -> None:
        if request.headers.get("Authorization"):
            # already authenticated, nothing for us to do
            return

        request.headers["Authorization"] = f"Bearer {await self._ensure_access_token()}"

    async def _ensure_access_token(self) -> str:
        if self.access_token is not None:
            return self.access_token

        if not self.credentials:
            self.credentials, project_id = await asyncify(load_auth)(project_id=self.project_id)
            if not self.project_id:
                self.project_id = project_id

        if self.credentials.expired or not self.credentials.token:
            await asyncify(refresh_auth)(self.credentials)

        if not self.credentials.token:
            raise RuntimeError("Could not resolve API token from the environment")

        assert isinstance(self.credentials.token, str)
        return self.credentials.token

    def copy(
        self,
        *,
        region: str | NotGiven = NOT_GIVEN,
        project_id: str | NotGiven = NOT_GIVEN,
        access_token: str | None = None,
        credentials: GoogleCredentials | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.AsyncClient | None = None,
        connection_pool_limits: httpx.Limits | None = None,
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

        if connection_pool_limits is not None:
            if http_client is not None:
                raise ValueError("The 'http_client' argument is mutually exclusive with 'connection_pool_limits'")

            if not isinstance(self._client, AsyncHttpxClientWrapper):
                raise ValueError(
                    "A custom HTTP client has been set and is mutually exclusive with the 'connection_pool_limits' argument"
                )

            http_client = None
        else:
            if self._limits is not DEFAULT_CONNECTION_LIMITS:
                connection_pool_limits = self._limits
            else:
                connection_pool_limits = None

            http_client = http_client or self._client

        return self.__class__(
            region=region if is_given(region) else self.region,
            project_id=project_id if is_given(project_id) else self.project_id or NOT_GIVEN,
            access_token=access_token or self.access_token,
            credentials=credentials or self.credentials,
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


def _prepare_options(input_options: FinalRequestOptions, *, project_id: str | None, region: str) -> FinalRequestOptions:
    options = model_copy(input_options, deep=True)

    if is_dict(options.json_data):
        options.json_data.setdefault("anthropic_version", DEFAULT_VERSION)

    if options.url in {"/v1/messages", "/v1/messages?beta=true"} and options.method == "post":
        if project_id is None:
            raise RuntimeError(
                "No project_id was given and it could not be resolved from credentials. The client should be instantiated with the `project_id` argument or the `ANTHROPIC_VERTEX_PROJECT_ID` environment variable should be set."
            )

        if not is_dict(options.json_data):
            raise RuntimeError("Expected json data to be a dictionary for post /v1/messages")

        model = options.json_data.pop("model")
        stream = options.json_data.get("stream", False)
        specifier = "streamRawPredict" if stream else "rawPredict"

        options.url = f"/projects/{project_id}/locations/{region}/publishers/anthropic/models/{model}:{specifier}"

        if is_dict(options.json_data):
            options.json_data.pop("model", None)

    return options

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\modules\diff_viewer.py ===
# modules/diff_viewer.py

import difflib

def generate_diff(old_code: str, new_code: str) -> str:
    diff = difflib.unified_diff(
        old_code.splitlines(),
        new_code.splitlines(),
        fromfile='Before',
        tofile='After',
        lineterm=''
    )
    return "\n".join(diff)

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\src\tests\test_sample.py ===
import pytest
from sample import add_two_integers

def test_add_two_integers():
    assert add_two_integers(1, 2) == 3
    assert add_two_integers(-1, -2) == -3
    assert add_two_integers(0, 0) == 0

    with pytest.raises(TypeError):
        add_two_integers("1", 2)

    with pytest.raises(TypeError):
        add_two_integers(1, "2")

# === NexusCore/tools\exports\export_20250803_114325\combined_24.py ===

# === NexusCore/openenv\Lib\site-packages\openai\lib\streaming\responses\_events.py ===
from __future__ import annotations

from typing import Optional
from typing_extensions import Union, Generic, TypeVar, Annotated, TypeAlias

from ...._utils import PropertyInfo
from ...._compat import GenericModel
from ....types.responses import (
    ParsedResponse,
    ResponseErrorEvent,
    ResponseFailedEvent,
    ResponseQueuedEvent,
    ResponseCreatedEvent,
    ResponseTextDoneEvent as RawResponseTextDoneEvent,
    ResponseAudioDoneEvent,
    ResponseCompletedEvent as RawResponseCompletedEvent,
    ResponseTextDeltaEvent as RawResponseTextDeltaEvent,
    ResponseAudioDeltaEvent,
    ResponseIncompleteEvent,
    ResponseInProgressEvent,
    ResponseRefusalDoneEvent,
    ResponseRefusalDeltaEvent,
    ResponseMcpCallFailedEvent,
    ResponseReasoningDoneEvent,
    ResponseOutputItemDoneEvent,
    ResponseReasoningDeltaEvent,
    ResponseContentPartDoneEvent,
    ResponseOutputItemAddedEvent,
    ResponseContentPartAddedEvent,
    ResponseMcpCallCompletedEvent,
    ResponseMcpCallInProgressEvent,
    ResponseMcpListToolsFailedEvent,
    ResponseAudioTranscriptDoneEvent,
    ResponseAudioTranscriptDeltaEvent,
    ResponseMcpCallArgumentsDoneEvent,
    ResponseReasoningSummaryDoneEvent,
    ResponseImageGenCallCompletedEvent,
    ResponseMcpCallArgumentsDeltaEvent,
    ResponseMcpListToolsCompletedEvent,
    ResponseReasoningSummaryDeltaEvent,
    ResponseImageGenCallGeneratingEvent,
    ResponseImageGenCallInProgressEvent,
    ResponseMcpListToolsInProgressEvent,
    ResponseWebSearchCallCompletedEvent,
    ResponseWebSearchCallSearchingEvent,
    ResponseFileSearchCallCompletedEvent,
    ResponseFileSearchCallSearchingEvent,
    ResponseWebSearchCallInProgressEvent,
    ResponseFileSearchCallInProgressEvent,
    ResponseImageGenCallPartialImageEvent,
    ResponseReasoningSummaryPartDoneEvent,
    ResponseReasoningSummaryTextDoneEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseOutputTextAnnotationAddedEvent,
    ResponseReasoningSummaryPartAddedEvent,
    ResponseReasoningSummaryTextDeltaEvent,
    ResponseFunctionCallArgumentsDeltaEvent as RawResponseFunctionCallArgumentsDeltaEvent,
    ResponseCodeInterpreterCallCodeDoneEvent,
    ResponseCodeInterpreterCallCodeDeltaEvent,
    ResponseCodeInterpreterCallCompletedEvent,
    ResponseCodeInterpreterCallInProgressEvent,
    ResponseCodeInterpreterCallInterpretingEvent,
)

TextFormatT = TypeVar(
    "TextFormatT",
    # if it isn't given then we don't do any parsing
    default=None,
)


class ResponseTextDeltaEvent(RawResponseTextDeltaEvent):
    snapshot: str


class ResponseTextDoneEvent(RawResponseTextDoneEvent, GenericModel, Generic[TextFormatT]):
    parsed: Optional[TextFormatT] = None


class ResponseFunctionCallArgumentsDeltaEvent(RawResponseFunctionCallArgumentsDeltaEvent):
    snapshot: str


class ResponseCompletedEvent(RawResponseCompletedEvent, GenericModel, Generic[TextFormatT]):
    response: ParsedResponse[TextFormatT]  # type: ignore[assignment]


ResponseStreamEvent: TypeAlias = Annotated[
    Union[
        # wrappers with snapshots added on
        ResponseTextDeltaEvent,
        ResponseTextDoneEvent[TextFormatT],
        ResponseFunctionCallArgumentsDeltaEvent,
        ResponseCompletedEvent[TextFormatT],
        # the same as the non-accumulated API
        ResponseAudioDeltaEvent,
        ResponseAudioDoneEvent,
        ResponseAudioTranscriptDeltaEvent,
        ResponseAudioTranscriptDoneEvent,
        ResponseCodeInterpreterCallCodeDeltaEvent,
        ResponseCodeInterpreterCallCodeDoneEvent,
        ResponseCodeInterpreterCallCompletedEvent,
        ResponseCodeInterpreterCallInProgressEvent,
        ResponseCodeInterpreterCallInterpretingEvent,
        ResponseContentPartAddedEvent,
        ResponseContentPartDoneEvent,
        ResponseCreatedEvent,
        ResponseErrorEvent,
        ResponseFileSearchCallCompletedEvent,
        ResponseFileSearchCallInProgressEvent,
        ResponseFileSearchCallSearchingEvent,
        ResponseFunctionCallArgumentsDoneEvent,
        ResponseInProgressEvent,
        ResponseFailedEvent,
        ResponseIncompleteEvent,
        ResponseOutputItemAddedEvent,
        ResponseOutputItemDoneEvent,
        ResponseRefusalDeltaEvent,
        ResponseRefusalDoneEvent,
        ResponseTextDoneEvent,
        ResponseWebSearchCallCompletedEvent,
        ResponseWebSearchCallInProgressEvent,
        ResponseWebSearchCallSearchingEvent,
        ResponseReasoningSummaryPartAddedEvent,
        ResponseReasoningSummaryPartDoneEvent,
        ResponseReasoningSummaryTextDeltaEvent,
        ResponseReasoningSummaryTextDoneEvent,
        ResponseImageGenCallCompletedEvent,
        ResponseImageGenCallInProgressEvent,
        ResponseImageGenCallGeneratingEvent,
        ResponseImageGenCallPartialImageEvent,
        ResponseMcpCallCompletedEvent,
        ResponseMcpCallArgumentsDeltaEvent,
        ResponseMcpCallArgumentsDoneEvent,
        ResponseMcpCallFailedEvent,
        ResponseMcpCallInProgressEvent,
        ResponseMcpListToolsCompletedEvent,
        ResponseMcpListToolsFailedEvent,
        ResponseMcpListToolsInProgressEvent,
        ResponseOutputTextAnnotationAddedEvent,
        ResponseQueuedEvent,
        ResponseReasoningDeltaEvent,
        ResponseReasoningSummaryDeltaEvent,
        ResponseReasoningSummaryDoneEvent,
        ResponseReasoningDoneEvent,
    ],
    PropertyInfo(discriminator="type"),
]

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\breakpoint.py ===
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
Breakpoints.

@group Breakpoints:
    Breakpoint, CodeBreakpoint, PageBreakpoint, HardwareBreakpoint,
    BufferWatch, Hook, ApiHook

@group Warnings:
    BreakpointWarning, BreakpointCallbackWarning
"""

__revision__ = "$Id$"

__all__ = [
    # Base class for breakpoints
    "Breakpoint",
    # Breakpoint implementations
    "CodeBreakpoint",
    "PageBreakpoint",
    "HardwareBreakpoint",
    # Hooks and watches
    "Hook",
    "ApiHook",
    "BufferWatch",
    # Warnings
    "BreakpointWarning",
    "BreakpointCallbackWarning",
]

from winappdbg import win32
from winappdbg import compat
import sys
from winappdbg.process import Process, Thread
from winappdbg.util import DebugRegister, MemoryAddresses
from winappdbg.textio import HexDump

import ctypes
import warnings
import traceback

# ==============================================================================


class BreakpointWarning(UserWarning):
    """
    This warning is issued when a non-fatal error occurs that's related to
    breakpoints.
    """


class BreakpointCallbackWarning(RuntimeWarning):
    """
    This warning is issued when an uncaught exception was raised by a
    breakpoint's user-defined callback.
    """


# ==============================================================================


class Breakpoint(object):
    """
    Base class for breakpoints.
    Here's the breakpoints state machine.

    @see: L{CodeBreakpoint}, L{PageBreakpoint}, L{HardwareBreakpoint}

    @group Breakpoint states:
        DISABLED, ENABLED, ONESHOT, RUNNING
    @group State machine:
        hit, disable, enable, one_shot, running,
        is_disabled, is_enabled, is_one_shot, is_running,
        get_state, get_state_name
    @group Information:
        get_address, get_size, get_span, is_here
    @group Conditional breakpoints:
        is_conditional, is_unconditional,
        get_condition, set_condition, eval_condition
    @group Automatic breakpoints:
        is_automatic, is_interactive,
        get_action, set_action, run_action

    @cvar DISABLED: I{Disabled} S{->} Enabled, OneShot
    @cvar ENABLED:  I{Enabled}  S{->} I{Running}, Disabled
    @cvar ONESHOT:  I{OneShot}  S{->} I{Disabled}
    @cvar RUNNING:  I{Running}  S{->} I{Enabled}, Disabled

    @type DISABLED: int
    @type ENABLED:  int
    @type ONESHOT:  int
    @type RUNNING:  int

    @type stateNames: dict E{lb} int S{->} str E{rb}
    @cvar stateNames: User-friendly names for each breakpoint state.

    @type typeName: str
    @cvar typeName: User friendly breakpoint type string.
    """

    # I don't think transitions Enabled <-> OneShot should be allowed... plus
    #  it would require special handling to avoid setting the same bp twice

    DISABLED = 0
    ENABLED = 1
    ONESHOT = 2
    RUNNING = 3

    typeName = "breakpoint"

    stateNames = {
        DISABLED: "disabled",
        ENABLED: "enabled",
        ONESHOT: "one shot",
        RUNNING: "running",
    }

    def __init__(self, address, size=1, condition=True, action=None):
        """
        Breakpoint object.

        @type  address: int
        @param address: Memory address for breakpoint.

        @type  size: int
        @param size: Size of breakpoint in bytes (defaults to 1).

        @type  condition: function
        @param condition: (Optional) Condition callback function.

            The callback signature is::

                def condition_callback(event):
                    return True     # returns True or False

            Where B{event} is an L{Event} object,
            and the return value is a boolean
            (C{True} to dispatch the event, C{False} otherwise).

        @type  action: function
        @param action: (Optional) Action callback function.
            If specified, the event is handled by this callback instead of
            being dispatched normally.

            The callback signature is::

                def action_callback(event):
                    pass        # no return value

            Where B{event} is an L{Event} object.
        """
        self.__address = address
        self.__size = size
        self.__state = self.DISABLED

        self.set_condition(condition)
        self.set_action(action)

    def __repr__(self):
        if self.is_disabled():
            state = "Disabled"
        else:
            state = "Active (%s)" % self.get_state_name()
        if self.is_conditional():
            condition = "conditional"
        else:
            condition = "unconditional"
        name = self.typeName
        size = self.get_size()
        if size == 1:
            address = HexDump.address(self.get_address())
        else:
            begin = self.get_address()
            end = begin + size
            begin = HexDump.address(begin)
            end = HexDump.address(end)
            address = "range %s-%s" % (begin, end)
        msg = "<%s %s %s at remote address %s>"
        msg = msg % (state, condition, name, address)
        return msg

    # ------------------------------------------------------------------------------

    def is_disabled(self):
        """
        @rtype:  bool
        @return: C{True} if the breakpoint is in L{DISABLED} state.
        """
        return self.get_state() == self.DISABLED

    def is_enabled(self):
        """
        @rtype:  bool
        @return: C{True} if the breakpoint is in L{ENABLED} state.
        """
        return self.get_state() == self.ENABLED

    def is_one_shot(self):
        """
        @rtype:  bool
        @return: C{True} if the breakpoint is in L{ONESHOT} state.
        """
        return self.get_state() == self.ONESHOT

    def is_running(self):
        """
        @rtype:  bool
        @return: C{True} if the breakpoint is in L{RUNNING} state.
        """
        return self.get_state() == self.RUNNING

    def is_here(self, address):
        """
        @rtype:  bool
        @return: C{True} if the address is within the range of the breakpoint.
        """
        begin = self.get_address()
        end = begin + self.get_size()
        return begin <= address < end

    def get_address(self):
        """
        @rtype:  int
        @return: The target memory address for the breakpoint.
        """
        return self.__address

    def get_size(self):
        """
        @rtype:  int
        @return: The size in bytes of the breakpoint.
        """
        return self.__size

    def get_span(self):
        """
        @rtype:  tuple( int, int )
        @return:
            Starting and ending address of the memory range
            covered by the breakpoint.
        """
        address = self.get_address()
        size = self.get_size()
        return (address, address + size)

    def get_state(self):
        """
        @rtype:  int
        @return: The current state of the breakpoint
            (L{DISABLED}, L{ENABLED}, L{ONESHOT}, L{RUNNING}).
        """
        return self.__state

    def get_state_name(self):
        """
        @rtype:  str
        @return: The name of the current state of the breakpoint.
        """
        return self.stateNames[self.get_state()]

    # ------------------------------------------------------------------------------

    def is_conditional(self):
        """
        @see: L{__init__}
        @rtype:  bool
        @return: C{True} if the breakpoint has a condition callback defined.
        """
        # Do not evaluate as boolean! Test for identity with True instead.
        return self.__condition is not True

    def is_unconditional(self):
        """
        @rtype:  bool
        @return: C{True} if the breakpoint doesn't have a condition callback defined.
        """
        # Do not evaluate as boolean! Test for identity with True instead.
        return self.__condition is True

    def get_condition(self):
        """
        @rtype:  bool, function
        @return: Returns the condition callback for conditional breakpoints.
            Returns C{True} for unconditional breakpoints.
        """
        return self.__condition

    def set_condition(self, condition=True):
        """
        Sets a new condition callback for the breakpoint.

        @see: L{__init__}

        @type  condition: function
        @param condition: (Optional) Condition callback function.
        """
        if condition is None:
            self.__condition = True
        else:
            self.__condition = condition

    def eval_condition(self, event):
        """
        Evaluates the breakpoint condition, if any was set.

        @type  event: L{Event}
        @param event: Debug event triggered by the breakpoint.

        @rtype:  bool
        @return: C{True} to dispatch the event, C{False} otherwise.
        """
        condition = self.get_condition()
        if condition is True:  # shortcut for unconditional breakpoints
            return True
        if callable(condition):
            try:
                return bool(condition(event))
            except Exception:
                e = sys.exc_info()[1]
                msg = "Breakpoint condition callback %r" " raised an exception: %s"
                msg = msg % (condition, traceback.format_exc(e))
                warnings.warn(msg, BreakpointCallbackWarning)
                return False
        return bool(condition)  # force evaluation now

    # ------------------------------------------------------------------------------

    def is_automatic(self):
        """
        @rtype:  bool
        @return: C{True} if the breakpoint has an action callback defined.
        """
        return self.__action is not None

    def is_interactive(self):
        """
        @rtype:  bool
        @return:
            C{True} if the breakpoint doesn't have an action callback defined.
        """
        return self.__action is None

    def get_action(self):
        """
        @rtype:  bool, function
        @return: Returns the action callback for automatic breakpoints.
            Returns C{None} for interactive breakpoints.
        """
        return self.__action

    def set_action(self, action=None):
        """
        Sets a new action callback for the breakpoint.

        @type  action: function
        @param action: (Optional) Action callback function.
        """
        self.__action = action

    def run_action(self, event):
        """
        Executes the breakpoint action callback, if any was set.

        @type  event: L{Event}
        @param event: Debug event triggered by the breakpoint.
        """
        action = self.get_action()
        if action is not None:
            try:
                return bool(action(event))
            except Exception:
                e = sys.exc_info()[1]
                msg = "Breakpoint action callback %r" " raised an exception: %s"
                msg = msg % (action, traceback.format_exc(e))
                warnings.warn(msg, BreakpointCallbackWarning)
                return False
        return True

    # ------------------------------------------------------------------------------

    def __bad_transition(self, state):
        """
        Raises an C{AssertionError} exception for an invalid state transition.

        @see: L{stateNames}

        @type  state: int
        @param state: Intended breakpoint state.

        @raise Exception: Always.
        """
        statemsg = ""
        oldState = self.stateNames[self.get_state()]
        newState = self.stateNames[state]
        msg = "Invalid state transition (%s -> %s)" " for breakpoint at address %s"
        msg = msg % (oldState, newState, HexDump.address(self.get_address()))
        raise AssertionError(msg)

    def disable(self, aProcess, aThread):
        """
        Transition to L{DISABLED} state.
          - When hit: OneShot S{->} Disabled
          - Forced by user: Enabled, OneShot, Running S{->} Disabled
          - Transition from running state may require special handling
            by the breakpoint implementation class.

        @type  aProcess: L{Process}
        @param aProcess: Process object.

        @type  aThread: L{Thread}
        @param aThread: Thread object.
        """
        ##        if self.__state not in (self.ENABLED, self.ONESHOT, self.RUNNING):
        ##            self.__bad_transition(self.DISABLED)
        self.__state = self.DISABLED

    def enable(self, aProcess, aThread):
        """
        Transition to L{ENABLED} state.
          - When hit: Running S{->} Enabled
          - Forced by user: Disabled, Running S{->} Enabled
          - Transition from running state may require special handling
            by the breakpoint implementation class.

        @type  aProcess: L{Process}
        @param aProcess: Process object.

        @type  aThread: L{Thread}
        @param aThread: Thread object.
        """
        ##        if self.__state not in (self.DISABLED, self.RUNNING):
        ##            self.__bad_transition(self.ENABLED)
        self.__state = self.ENABLED

    def one_shot(self, aProcess, aThread):
        """
        Transition to L{ONESHOT} state.
          - Forced by user: Disabled S{->} OneShot

        @type  aProcess: L{Process}
        @param aProcess: Process object.

        @type  aThread: L{Thread}
        @param aThread: Thread object.
        """
        ##        if self.__state != self.DISABLED:
        ##            self.__bad_transition(self.ONESHOT)
        self.__state = self.ONESHOT

    def running(self, aProcess, aThread):
        """
        Transition to L{RUNNING} state.
          - When hit: Enabled S{->} Running

        @type  aProcess: L{Process}
        @param aProcess: Process object.

        @type  aThread: L{Thread}
        @param aThread: Thread object.
        """
        if self.__state != self.ENABLED:
            self.__bad_transition(self.RUNNING)
        self.__state = self.RUNNING

    def hit(self, event):
        """
        Notify a breakpoint that it's been hit.

        This triggers the corresponding state transition and sets the
        C{breakpoint} property of the given L{Event} object.

        @see: L{disable}, L{enable}, L{one_shot}, L{running}

        @type  event: L{Event}
        @param event: Debug event to handle (depends on the breakpoint type).

        @raise AssertionError: Disabled breakpoints can't be hit.
        """
        aProcess = event.get_process()
        aThread = event.get_thread()
        state = self.get_state()

        event.breakpoint = self

        if state == self.ENABLED:
            self.running(aProcess, aThread)

        elif state == self.RUNNING:
            self.enable(aProcess, aThread)

        elif state == self.ONESHOT:
            self.disable(aProcess, aThread)

        elif state == self.DISABLED:
            # this should not happen
            msg = "Hit a disabled breakpoint at address %s"
            msg = msg % HexDump.address(self.get_address())
            warnings.warn(msg, BreakpointWarning)


# ==============================================================================

# XXX TODO
# Check if the user is trying to set a code breakpoint on a memory mapped file,
# so we don't end up writing the int3 instruction in the file by accident.


class CodeBreakpoint(Breakpoint):
    """
    Code execution breakpoints (using an int3 opcode).

    @see: L{Debug.break_at}

    @type bpInstruction: str
    @cvar bpInstruction: Breakpoint instruction for the current processor.
    """

    typeName = "code breakpoint"

    if win32.arch in (win32.ARCH_I386, win32.ARCH_AMD64):
        bpInstruction = "\xCC"  # int 3

    def __init__(self, address, condition=True, action=None):
        """
        Code breakpoint object.

        @see: L{Breakpoint.__init__}

        @type  address: int
        @param address: Memory address for breakpoint.

        @type  condition: function
        @param condition: (Optional) Condition callback function.

        @type  action: function
        @param action: (Optional) Action callback function.
        """
        if win32.arch not in (win32.ARCH_I386, win32.ARCH_AMD64):
            msg = "Code breakpoints not supported for %s" % win32.arch
            raise NotImplementedError(msg)
        Breakpoint.__init__(self, address, len(self.bpInstruction), condition, action)
        self.__previousValue = self.bpInstruction

    def __set_bp(self, aProcess):
        """
        Writes a breakpoint instruction at the target address.

        @type  aProcess: L{Process}
        @param aProcess: Process object.
        """
        address = self.get_address()
        self.__previousValue = aProcess.read(address, len(self.bpInstruction))
        if self.__previousValue == self.bpInstruction:
            msg = "Possible overlapping code breakpoints at %s"
            msg = msg % HexDump.address(address)
            warnings.warn(msg, BreakpointWarning)
        aProcess.write(address, self.bpInstruction)

    def __clear_bp(self, aProcess):
        """
        Restores the original byte at the target address.

        @type  aProcess: L{Process}
        @param aProcess: Process object.
        """
        address = self.get_address()
        currentValue = aProcess.read(address, len(self.bpInstruction))
        if currentValue == self.bpInstruction:
            # Only restore the previous value if the int3 is still there.
            aProcess.write(self.get_address(), self.__previousValue)
        else:
            self.__previousValue = currentValue
            msg = "Overwritten code breakpoint at %s"
            msg = msg % HexDump.address(address)
            warnings.warn(msg, BreakpointWarning)

    def disable(self, aProcess, aThread):
        if not self.is_disabled() and not self.is_running():
            self.__clear_bp(aProcess)
        super(CodeBreakpoint, self).disable(aProcess, aThread)

    def enable(self, aProcess, aThread):
        if not self.is_enabled() and not self.is_one_shot():
            self.__set_bp(aProcess)
        super(CodeBreakpoint, self).enable(aProcess, aThread)

    def one_shot(self, aProcess, aThread):
        if not self.is_enabled() and not self.is_one_shot():
            self.__set_bp(aProcess)
        super(CodeBreakpoint, self).one_shot(aProcess, aThread)

    # FIXME race condition here (however unlikely)
    # If another thread runs on over the target address while
    # the breakpoint is in RUNNING state, we'll miss it. There
    # is a solution to this but it's somewhat complicated, so
    # I'm leaving it for another version of the debugger. :(
    def running(self, aProcess, aThread):
        if self.is_enabled():
            self.__clear_bp(aProcess)
            aThread.set_tf()
        super(CodeBreakpoint, self).running(aProcess, aThread)


# ==============================================================================

# TODO:
# * If the original page was already a guard page, the exception should be
#   passed to the debugee instead of being handled by the debugger.
# * If the original page was already a guard page, it should NOT be converted
#   to a no-access page when disabling the breakpoint.
# * If the page permissions were modified after the breakpoint was enabled,
#   no change should be done on them when disabling the breakpoint. For this
#   we need to remember the original page permissions instead of blindly
#   setting and clearing the guard page bit on them.
# * Some pages seem to be "magic" and resist all attempts at changing their
#   protect bits (for example the pages where the PEB and TEB reside). Maybe
#   a more descriptive error message could be shown in this case.


class PageBreakpoint(Breakpoint):
    """
    Page access breakpoint (using guard pages).

    @see: L{Debug.watch_buffer}

    @group Information:
        get_size_in_pages
    """

    typeName = "page breakpoint"

    # ------------------------------------------------------------------------------

    def __init__(self, address, pages=1, condition=True, action=None):
        """
        Page breakpoint object.

        @see: L{Breakpoint.__init__}

        @type  address: int
        @param address: Memory address for breakpoint.

        @type  pages: int
        @param address: Size of breakpoint in pages.

        @type  condition: function
        @param condition: (Optional) Condition callback function.

        @type  action: function
        @param action: (Optional) Action callback function.
        """
        Breakpoint.__init__(self, address, pages * MemoryAddresses.pageSize, condition, action)
        ##        if (address & 0x00000FFF) != 0:
        floordiv_align = long(address) // long(MemoryAddresses.pageSize)
        truediv_align = float(address) / float(MemoryAddresses.pageSize)
        if floordiv_align != truediv_align:
            msg = "Address of page breakpoint " "must be aligned to a page size boundary " "(value %s received)" % HexDump.address(address)
            raise ValueError(msg)

    def get_size_in_pages(self):
        """
        @rtype:  int
        @return: The size in pages of the breakpoint.
        """
        # The size is always a multiple of the page size.
        return self.get_size() // MemoryAddresses.pageSize

    def __set_bp(self, aProcess):
        """
        Sets the target pages as guard pages.

        @type  aProcess: L{Process}
        @param aProcess: Process object.
        """
        lpAddress = self.get_address()
        dwSize = self.get_size()
        flNewProtect = aProcess.mquery(lpAddress).Protect
        flNewProtect = flNewProtect | win32.PAGE_GUARD
        aProcess.mprotect(lpAddress, dwSize, flNewProtect)

    def __clear_bp(self, aProcess):
        """
        Restores the original permissions of the target pages.

        @type  aProcess: L{Process}
        @param aProcess: Process object.
        """
        lpAddress = self.get_address()
        flNewProtect = aProcess.mquery(lpAddress).Protect
        flNewProtect = flNewProtect & (0xFFFFFFFF ^ win32.PAGE_GUARD)  # DWORD
        aProcess.mprotect(lpAddress, self.get_size(), flNewProtect)

    def disable(self, aProcess, aThread):
        if not self.is_disabled():
            self.__clear_bp(aProcess)
        super(PageBreakpoint, self).disable(aProcess, aThread)

    def enable(self, aProcess, aThread):
        if win32.arch not in (win32.ARCH_I386, win32.ARCH_AMD64):
            msg = "Only one-shot page breakpoints are supported for %s"
            raise NotImplementedError(msg % win32.arch)
        if not self.is_enabled() and not self.is_one_shot():
            self.__set_bp(aProcess)
        super(PageBreakpoint, self).enable(aProcess, aThread)

    def one_shot(self, aProcess, aThread):
        if not self.is_enabled() and not self.is_one_shot():
            self.__set_bp(aProcess)
        super(PageBreakpoint, self).one_shot(aProcess, aThread)

    def running(self, aProcess, aThread):
        aThread.set_tf()
        super(PageBreakpoint, self).running(aProcess, aThread)


# ==============================================================================


class HardwareBreakpoint(Breakpoint):
    """
    Hardware breakpoint (using debug registers).

    @see: L{Debug.watch_variable}

    @group Information:
        get_slot, get_trigger, get_watch

    @group Trigger flags:
        BREAK_ON_EXECUTION, BREAK_ON_WRITE, BREAK_ON_ACCESS

    @group Watch size flags:
        WATCH_BYTE, WATCH_WORD, WATCH_DWORD, WATCH_QWORD

    @type BREAK_ON_EXECUTION: int
    @cvar BREAK_ON_EXECUTION: Break on execution.

    @type BREAK_ON_WRITE: int
    @cvar BREAK_ON_WRITE: Break on write.

    @type BREAK_ON_ACCESS: int
    @cvar BREAK_ON_ACCESS: Break on read or write.

    @type WATCH_BYTE: int
    @cvar WATCH_BYTE: Watch a byte.

    @type WATCH_WORD: int
    @cvar WATCH_WORD: Watch a word (2 bytes).

    @type WATCH_DWORD: int
    @cvar WATCH_DWORD: Watch a double word (4 bytes).

    @type WATCH_QWORD: int
    @cvar WATCH_QWORD: Watch one quad word (8 bytes).

    @type validTriggers: tuple
    @cvar validTriggers: Valid trigger flag values.

    @type validWatchSizes: tuple
    @cvar validWatchSizes: Valid watch flag values.
    """

    typeName = "hardware breakpoint"

    BREAK_ON_EXECUTION = DebugRegister.BREAK_ON_EXECUTION
    BREAK_ON_WRITE = DebugRegister.BREAK_ON_WRITE
    BREAK_ON_ACCESS = DebugRegister.BREAK_ON_ACCESS

    WATCH_BYTE = DebugRegister.WATCH_BYTE
    WATCH_WORD = DebugRegister.WATCH_WORD
    WATCH_DWORD = DebugRegister.WATCH_DWORD
    WATCH_QWORD = DebugRegister.WATCH_QWORD

    validTriggers = (
        BREAK_ON_EXECUTION,
        BREAK_ON_WRITE,
        BREAK_ON_ACCESS,
    )

    validWatchSizes = (
        WATCH_BYTE,
        WATCH_WORD,
        WATCH_DWORD,
        WATCH_QWORD,
    )

    def __init__(self, address, triggerFlag=BREAK_ON_ACCESS, sizeFlag=WATCH_DWORD, condition=True, action=None):
        """
        Hardware breakpoint object.

        @see: L{Breakpoint.__init__}

        @type  address: int
        @param address: Memory address for breakpoint.

        @type  triggerFlag: int
        @param triggerFlag: Trigger of breakpoint. Must be one of the following:

             - L{BREAK_ON_EXECUTION}

               Break on code execution.

             - L{BREAK_ON_WRITE}

               Break on memory read or write.

             - L{BREAK_ON_ACCESS}

               Break on memory write.

        @type  sizeFlag: int
        @param sizeFlag: Size of breakpoint. Must be one of the following:

             - L{WATCH_BYTE}

               One (1) byte in size.

             - L{WATCH_WORD}

               Two (2) bytes in size.

             - L{WATCH_DWORD}

               Four (4) bytes in size.

             - L{WATCH_QWORD}

               Eight (8) bytes in size.

        @type  condition: function
        @param condition: (Optional) Condition callback function.

        @type  action: function
        @param action: (Optional) Action callback function.
        """
        if win32.arch not in (win32.ARCH_I386, win32.ARCH_AMD64):
            msg = "Hardware breakpoints not supported for %s" % win32.arch
            raise NotImplementedError(msg)
        if sizeFlag == self.WATCH_BYTE:
            size = 1
        elif sizeFlag == self.WATCH_WORD:
            size = 2
        elif sizeFlag == self.WATCH_DWORD:
            size = 4
        elif sizeFlag == self.WATCH_QWORD:
            size = 8
        else:
            msg = "Invalid size flag for hardware breakpoint (%s)"
            msg = msg % repr(sizeFlag)
            raise ValueError(msg)

        if triggerFlag not in self.validTriggers:
            msg = "Invalid trigger flag for hardware breakpoint (%s)"
            msg = msg % repr(triggerFlag)
            raise ValueError(msg)

        Breakpoint.__init__(self, address, size, condition, action)
        self.__trigger = triggerFlag
        self.__watch = sizeFlag
        self.__slot = None

    def __clear_bp(self, aThread):
        """
        Clears this breakpoint from the debug registers.

        @type  aThread: L{Thread}
        @param aThread: Thread object.
        """
        if self.__slot is not None:
            aThread.suspend()
            try:
                ctx = aThread.get_context(win32.CONTEXT_DEBUG_REGISTERS)
                DebugRegister.clear_bp(ctx, self.__slot)
                aThread.set_context(ctx)
                self.__slot = None
            finally:
                aThread.resume()

    def __set_bp(self, aThread):
        """
        Sets this breakpoint in the debug registers.

        @type  aThread: L{Thread}
        @param aThread: Thread object.
        """
        if self.__slot is None:
            aThread.suspend()
            try:
                ctx = aThread.get_context(win32.CONTEXT_DEBUG_REGISTERS)
                self.__slot = DebugRegister.find_slot(ctx)
                if self.__slot is None:
                    msg = "No available hardware breakpoint slots for thread ID %d"
                    msg = msg % aThread.get_tid()
                    raise RuntimeError(msg)
                DebugRegister.set_bp(ctx, self.__slot, self.get_address(), self.__trigger, self.__watch)
                aThread.set_context(ctx)
            finally:
                aThread.resume()

    def get_slot(self):
        """
        @rtype:  int
        @return: The debug register number used by this breakpoint,
            or C{None} if the breakpoint is not active.
        """
        return self.__slot

    def get_trigger(self):
        """
        @see: L{validTriggers}
        @rtype:  int
        @return: The breakpoint trigger flag.
        """
        return self.__trigger

    def get_watch(self):
        """
        @see: L{validWatchSizes}
        @rtype:  int
        @return: The breakpoint watch flag.
        """
        return self.__watch

    def disable(self, aProcess, aThread):
        if not self.is_disabled():
            self.__clear_bp(aThread)
        super(HardwareBreakpoint, self).disable(aProcess, aThread)

    def enable(self, aProcess, aThread):
        if not self.is_enabled() and not self.is_one_shot():
            self.__set_bp(aThread)
        super(HardwareBreakpoint, self).enable(aProcess, aThread)

    def one_shot(self, aProcess, aThread):
        if not self.is_enabled() and not self.is_one_shot():
            self.__set_bp(aThread)
        super(HardwareBreakpoint, self).one_shot(aProcess, aThread)

    def running(self, aProcess, aThread):
        self.__clear_bp(aThread)
        super(HardwareBreakpoint, self).running(aProcess, aThread)
        aThread.set_tf()


# ==============================================================================

# XXX FIXME
#
# The implementation of function hooks is very simple. A breakpoint is set at
# the entry point. Each time it's hit the "pre" callback is executed. If a
# "post" callback was defined, a one-shot breakpoint is set at the return
# address - and when that breakpoint hits, the "post" callback is executed.
#
# Functions hooks, as they are implemented now, don't work correctly for
# recursive functions. The problem is we don't know when to remove the
# breakpoint at the return address. Also there could be more than one return
# address.
#
# One possible solution would involve a dictionary of lists, where the key
# would be the thread ID and the value a stack of return addresses. But we
# still don't know what to do if the "wrong" return address is hit for some
# reason (maybe check the stack pointer?). Or if both a code and a hardware
# breakpoint are hit simultaneously.
#
# For now, the workaround for the user is to set only the "pre" callback for
# functions that are known to be recursive.
#
# If an exception is thrown by a hooked function and caught by one of it's
# parent functions, the "post" callback won't be called and weird stuff may
# happen. A possible solution is to put a breakpoint in the system call that
# unwinds the stack, to detect this case and remove the "post" breakpoint.
#
# Hooks may also behave oddly if the return address is overwritten by a buffer
# overflow bug (this is similar to the exception problem). But it's probably a
# minor issue since when you're fuzzing a function for overflows you're usually
# not interested in the return value anyway.

# TODO: an API to modify the hooked function's arguments


class Hook(object):
    """
    Factory class to produce hook objects. Used by L{Debug.hook_function} and
    L{Debug.stalk_function}.

    When you try to instance this class, one of the architecture specific
    implementations is returned instead.

    Instances act as an action callback for code breakpoints set at the
    beginning of a function. It automatically retrieves the parameters from
    the stack, sets a breakpoint at the return address and retrieves the
    return value from the function call.

    @see: L{_Hook_i386}, L{_Hook_amd64}

    @type useHardwareBreakpoints: bool
    @cvar useHardwareBreakpoints: C{True} to try to use hardware breakpoints,
        C{False} otherwise.
    """

    # This is a factory class that returns
    # the architecture specific implementation.
    def __new__(cls, *argv, **argd):
        try:
            arch = argd["arch"]
            del argd["arch"]
        except KeyError:
            try:
                arch = argv[4]
                argv = argv[:4] + argv[5:]
            except IndexError:
                raise TypeError("Missing 'arch' argument!")
        if arch is None:
            arch = win32.arch
        if arch == win32.ARCH_I386:
            return _Hook_i386(*argv, **argd)
        if arch == win32.ARCH_AMD64:
            return _Hook_amd64(*argv, **argd)
        return object.__new__(cls, *argv, **argd)

    # XXX FIXME
    #
    # Hardware breakpoints don't work correctly (or al all) in old VirtualBox
    # versions (3.0 and below).
    #
    # Maybe there should be a way to autodetect the buggy VirtualBox versions
    # and tell Hook objects not to use hardware breakpoints?
    #
    # For now the workaround is to manually set this variable to True when
    # WinAppDbg is installed on a physical machine.
    #
    useHardwareBreakpoints = False

    def __init__(self, preCB=None, postCB=None, paramCount=None, signature=None, arch=None):
        """
        @type  preCB: function
        @param preCB: (Optional) Callback triggered on function entry.

            The signature for the callback should be something like this::

                def pre_LoadLibraryEx(event, ra, lpFilename, hFile, dwFlags):

                    # return address
                    ra = params[0]

                    # function arguments start from here...
                    szFilename = event.get_process().peek_string(lpFilename)

                    # (...)

            Note that all pointer types are treated like void pointers, so your
            callback won't get the string or structure pointed to by it, but
            the remote memory address instead. This is so to prevent the ctypes
            library from being "too helpful" and trying to dereference the
            pointer. To get the actual data being pointed to, use one of the
            L{Process.read} methods.

        @type  postCB: function
        @param postCB: (Optional) Callback triggered on function exit.

            The signature for the callback should be something like this::

                def post_LoadLibraryEx(event, return_value):

                    # (...)

        @type  paramCount: int
        @param paramCount:
            (Optional) Number of parameters for the C{preCB} callback,
            not counting the return address. Parameters are read from
            the stack and assumed to be DWORDs in 32 bits and QWORDs in 64.

            This is a faster way to pull stack parameters in 32 bits, but in 64
            bits (or with some odd APIs in 32 bits) it won't be useful, since
            not all arguments to the hooked function will be of the same size.

            For a more reliable and cross-platform way of hooking use the
            C{signature} argument instead.

        @type  signature: tuple
        @param signature:
            (Optional) Tuple of C{ctypes} data types that constitute the
            hooked function signature. When the function is called, this will
            be used to parse the arguments from the stack. Overrides the
            C{paramCount} argument.

        @type  arch: str
        @param arch: (Optional) Target architecture. Defaults to the current
            architecture. See: L{win32.arch}
        """
        self.__preCB = preCB
        self.__postCB = postCB
        self.__paramStack = dict()  # tid -> list of tuple( arg, arg, arg... )

        self._paramCount = paramCount

        if win32.arch != win32.ARCH_I386:
            self.useHardwareBreakpoints = False

        if win32.bits == 64 and paramCount and not signature:
            signature = (win32.QWORD,) * paramCount

        if signature:
            self._signature = self._calc_signature(signature)
        else:
            self._signature = None

    def _cast_signature_pointers_to_void(self, signature):
        c_void_p = ctypes.c_void_p
        c_char_p = ctypes.c_char_p
        c_wchar_p = ctypes.c_wchar_p
        _Pointer = ctypes._Pointer
        cast = ctypes.cast
        for i in compat.xrange(len(signature)):
            t = signature[i]
            if t is not c_void_p and (issubclass(t, _Pointer) or t in [c_char_p, c_wchar_p]):
                signature[i] = cast(t, c_void_p)

    def _calc_signature(self, signature):
        raise NotImplementedError("Hook signatures are not supported for architecture: %s" % win32.arch)

    def _get_return_address(self, aProcess, aThread):
        return None

    def _get_function_arguments(self, aProcess, aThread):
        if self._signature or self._paramCount:
            raise NotImplementedError("Hook signatures are not supported for architecture: %s" % win32.arch)
        return ()

    def _get_return_value(self, aThread):
        return None

    # By using break_at() to set a process-wide breakpoint on the function's
    # return address, we might hit a race condition when more than one thread
    # is being debugged.
    #
    # Hardware breakpoints should be used instead. But since a thread can run
    # out of those, we need to fall back to this method when needed.

    def __call__(self, event):
        """
        Handles the breakpoint event on entry of the function.

        @type  event: L{ExceptionEvent}
        @param event: Breakpoint hit event.

        @raise WindowsError: An error occured.
        """
        debug = event.debug

        dwProcessId = event.get_pid()
        dwThreadId = event.get_tid()
        aProcess = event.get_process()
        aThread = event.get_thread()

        # Get the return address and function arguments.
        ra = self._get_return_address(aProcess, aThread)
        params = self._get_function_arguments(aProcess, aThread)

        # Keep the function arguments for later use.
        self.__push_params(dwThreadId, params)

        # If we need to hook the return from the function...
        bHookedReturn = False
        if ra is not None and self.__postCB is not None:
            # Try to set a one shot hardware breakpoint at the return address.
            useHardwareBreakpoints = self.useHardwareBreakpoints
            if useHardwareBreakpoints:
                try:
                    debug.define_hardware_breakpoint(
                        dwThreadId, ra, event.debug.BP_BREAK_ON_EXECUTION, event.debug.BP_WATCH_BYTE, True, self.__postCallAction_hwbp
                    )
                    debug.enable_one_shot_hardware_breakpoint(dwThreadId, ra)
                    bHookedReturn = True
                except Exception:
                    e = sys.exc_info()[1]
                    useHardwareBreakpoints = False
                    msg = "Failed to set hardware breakpoint" " at address %s for thread ID %d"
                    msg = msg % (HexDump.address(ra), dwThreadId)
                    warnings.warn(msg, BreakpointWarning)

            # If not possible, set a code breakpoint instead.
            if not useHardwareBreakpoints:
                try:
                    debug.break_at(dwProcessId, ra, self.__postCallAction_codebp)
                    bHookedReturn = True
                except Exception:
                    e = sys.exc_info()[1]
                    msg = "Failed to set code breakpoint" " at address %s for process ID %d"
                    msg = msg % (HexDump.address(ra), dwProcessId)
                    warnings.warn(msg, BreakpointWarning)

        # Call the "pre" callback.
        try:
            self.__callHandler(self.__preCB, event, ra, *params)

        # If no "post" callback is defined, forget the function arguments.
        finally:
            if not bHookedReturn:
                self.__pop_params(dwThreadId)

    def __postCallAction_hwbp(self, event):
        """
        Handles hardware breakpoint events on return from the function.

        @type  event: L{ExceptionEvent}
        @param event: Single step event.
        """

        # Remove the one shot hardware breakpoint
        # at the return address location in the stack.
        tid = event.get_tid()
        address = event.breakpoint.get_address()
        event.debug.erase_hardware_breakpoint(tid, address)

        # Call the "post" callback.
        try:
            self.__postCallAction(event)

        # Forget the parameters.
        finally:
            self.__pop_params(tid)

    def __postCallAction_codebp(self, event):
        """
        Handles code breakpoint events on return from the function.

        @type  event: L{ExceptionEvent}
        @param event: Breakpoint hit event.
        """

        # If the breakpoint was accidentally hit by another thread,
        # pass it to the debugger instead of calling the "post" callback.
        #
        # XXX FIXME:
        # I suppose this check will fail under some weird conditions...
        #
        tid = event.get_tid()
        if tid not in self.__paramStack:
            return True

        # Remove the code breakpoint at the return address.
        pid = event.get_pid()
        address = event.breakpoint.get_address()
        event.debug.dont_break_at(pid, address)

        # Call the "post" callback.
        try:
            self.__postCallAction(event)

        # Forget the parameters.
        finally:
            self.__pop_params(tid)

    def __postCallAction(self, event):
        """
        Calls the "post" callback.

        @type  event: L{ExceptionEvent}
        @param event: Breakpoint hit event.
        """
        aThread = event.get_thread()
        retval = self._get_return_value(aThread)
        self.__callHandler(self.__postCB, event, retval)

    def __callHandler(self, callback, event, *params):
        """
        Calls a "pre" or "post" handler, if set.

        @type  callback: function
        @param callback: Callback function to call.

        @type  event: L{ExceptionEvent}
        @param event: Breakpoint hit event.

        @type  params: tuple
        @param params: Parameters for the callback function.
        """
        if callback is not None:
            event.hook = self
            callback(event, *params)

    def __push_params(self, tid, params):
        """
        Remembers the arguments tuple for the last call to the hooked function
        from this thread.

        @type  tid: int
        @param tid: Thread global ID.

        @type  params: tuple( arg, arg, arg... )
        @param params: Tuple of arguments.
        """
        stack = self.__paramStack.get(tid, [])
        stack.append(params)
        self.__paramStack[tid] = stack

    def __pop_params(self, tid):
        """
        Forgets the arguments tuple for the last call to the hooked function
        from this thread.

        @type  tid: int
        @param tid: Thread global ID.
        """
        stack = self.__paramStack[tid]
        stack.pop()
        if not stack:
            del self.__paramStack[tid]

    def get_params(self, tid):
        """
        Returns the parameters found in the stack when the hooked function
        was last called by this thread.

        @type  tid: int
        @param tid: Thread global ID.

        @rtype:  tuple( arg, arg, arg... )
        @return: Tuple of arguments.
        """
        try:
            params = self.get_params_stack(tid)[-1]
        except IndexError:
            msg = "Hooked function called from thread %d already returned"
            raise IndexError(msg % tid)
        return params

    def get_params_stack(self, tid):
        """
        Returns the parameters found in the stack each time the hooked function
        was called by this thread and hasn't returned yet.

        @type  tid: int
        @param tid: Thread global ID.

        @rtype:  list of tuple( arg, arg, arg... )
        @return: List of argument tuples.
        """
        try:
            stack = self.__paramStack[tid]
        except KeyError:
            msg = "Hooked function was not called from thread %d"
            raise KeyError(msg % tid)
        return stack

    def hook(self, debug, pid, address):
        """
        Installs the function hook at a given process and address.

        @see: L{unhook}

        @warning: Do not call from an function hook callback.

        @type  debug: L{Debug}
        @param debug: Debug object.

        @type  pid: int
        @param pid: Process ID.

        @type  address: int
        @param address: Function address.
        """
        return debug.break_at(pid, address, self)

    def unhook(self, debug, pid, address):
        """
        Removes the function hook at a given process and address.

        @see: L{hook}

        @warning: Do not call from an function hook callback.

        @type  debug: L{Debug}
        @param debug: Debug object.

        @type  pid: int
        @param pid: Process ID.

        @type  address: int
        @param address: Function address.
        """
        return debug.dont_break_at(pid, address)


class _Hook_i386(Hook):
    """
    Implementation details for L{Hook} on the L{win32.ARCH_I386} architecture.
    """

    # We don't want to inherit the parent class __new__ method.
    __new__ = object.__new__

    def _calc_signature(self, signature):
        self._cast_signature_pointers_to_void(signature)

        class Arguments(ctypes.Structure):
            _fields_ = [("arg_%s" % i, signature[i]) for i in compat.xrange(len(signature) - 1, -1, -1)]

        return Arguments

    def _get_return_address(self, aProcess, aThread):
        return aProcess.read_pointer(aThread.get_sp())

    def _get_function_arguments(self, aProcess, aThread):
        if self._signature:
            params = aThread.read_stack_structure(self._signature, offset=win32.sizeof(win32.LPVOID))
        elif self._paramCount:
            params = aThread.read_stack_dwords(self._paramCount, offset=win32.sizeof(win32.LPVOID))
        else:
            params = ()
        return params

    def _get_return_value(self, aThread):
        ctx = aThread.get_context(win32.CONTEXT_INTEGER)
        return ctx["Eax"]


class _Hook_amd64(Hook):
    """
    Implementation details for L{Hook} on the L{win32.ARCH_AMD64} architecture.
    """

    # We don't want to inherit the parent class __new__ method.
    __new__ = object.__new__

    # Make a list of floating point types.
    __float_types = (
        ctypes.c_double,
        ctypes.c_float,
    )
    # Long doubles are not supported in old versions of ctypes!
    try:
        __float_types += (ctypes.c_longdouble,)
    except AttributeError:
        pass

    def _calc_signature(self, signature):
        self._cast_signature_pointers_to_void(signature)

        float_types = self.__float_types
        c_sizeof = ctypes.sizeof
        reg_size = c_sizeof(ctypes.c_size_t)

        reg_int_sig = []
        reg_float_sig = []
        stack_sig = []

        for i in compat.xrange(len(signature)):
            arg = signature[i]
            name = "arg_%d" % i
            stack_sig.insert(0, (name, arg))
            if i < 4:
                if type(arg) in float_types:
                    reg_float_sig.append((name, arg))
                elif c_sizeof(arg) <= reg_size:
                    reg_int_sig.append((name, arg))
                else:
                    msg = (
                        "Hook signatures don't support structures" " within the first 4 arguments of a function" " for the %s architecture"
                    ) % win32.arch
                    raise NotImplementedError(msg)

        if reg_int_sig:

            class RegisterArguments(ctypes.Structure):
                _fields_ = reg_int_sig
        else:
            RegisterArguments = None
        if reg_float_sig:

            class FloatArguments(ctypes.Structure):
                _fields_ = reg_float_sig
        else:
            FloatArguments = None
        if stack_sig:

            class StackArguments(ctypes.Structure):
                _fields_ = stack_sig
        else:
            StackArguments = None

        return (len(signature), RegisterArguments, FloatArguments, StackArguments)

    def _get_return_address(self, aProcess, aThread):
        return aProcess.read_pointer(aThread.get_sp())

    def _get_function_arguments(self, aProcess, aThread):
        if self._signature:
            (args_count, RegisterArguments, FloatArguments, StackArguments) = self._signature
            arguments = {}
            if StackArguments:
                address = aThread.get_sp() + win32.sizeof(win32.LPVOID)
                stack_struct = aProcess.read_structure(address, StackArguments)
                stack_args = dict([(name, stack_struct.__getattribute__(name)) for (name, type) in stack_struct._fields_])
                arguments.update(stack_args)
            flags = 0
            if RegisterArguments:
                flags = flags | win32.CONTEXT_INTEGER
            if FloatArguments:
                flags = flags | win32.CONTEXT_MMX_REGISTERS
            if flags:
                ctx = aThread.get_context(flags)
                if RegisterArguments:
                    buffer = (win32.QWORD * 4)(ctx["Rcx"], ctx["Rdx"], ctx["R8"], ctx["R9"])
                    reg_args = self._get_arguments_from_buffer(buffer, RegisterArguments)
                    arguments.update(reg_args)
                if FloatArguments:
                    buffer = (win32.M128A * 4)(ctx["XMM0"], ctx["XMM1"], ctx["XMM2"], ctx["XMM3"])
                    float_args = self._get_arguments_from_buffer(buffer, FloatArguments)
                    arguments.update(float_args)
            params = tuple([arguments["arg_%d" % i] for i in compat.xrange(args_count)])
        else:
            params = ()
        return params

    def _get_arguments_from_buffer(self, buffer, structure):
        b_ptr = ctypes.pointer(buffer)
        v_ptr = ctypes.cast(b_ptr, ctypes.c_void_p)
        s_ptr = ctypes.cast(v_ptr, ctypes.POINTER(structure))
        struct = s_ptr.contents
        return dict([(name, struct.__getattribute__(name)) for (name, type) in struct._fields_])

    def _get_return_value(self, aThread):
        ctx = aThread.get_context(win32.CONTEXT_INTEGER)
        return ctx["Rax"]


# ------------------------------------------------------------------------------

# This class acts as a factory of Hook objects, one per target process.
# Said objects are deleted by the unhook() method.


class ApiHook(object):
    """
    Used by L{EventHandler}.

    This class acts as an action callback for code breakpoints set at the
    beginning of a function. It automatically retrieves the parameters from
    the stack, sets a breakpoint at the return address and retrieves the
    return value from the function call.

    @see: L{EventHandler.apiHooks}

    @type modName: str
    @ivar modName: Module name.

    @type procName: str
    @ivar procName: Procedure name.
    """

    def __init__(self, eventHandler, modName, procName, paramCount=None, signature=None):
        """
        @type  eventHandler: L{EventHandler}
        @param eventHandler: Event handler instance. This is where the hook
            callbacks are to be defined (see below).

        @type  modName: str
        @param modName: Module name.

        @type  procName: str
        @param procName: Procedure name.
            The pre and post callbacks will be deduced from it.

            For example, if the procedure is "LoadLibraryEx" the callback
            routines will be "pre_LoadLibraryEx" and "post_LoadLibraryEx".

            The signature for the callbacks should be something like this::

                def pre_LoadLibraryEx(self, event, ra, lpFilename, hFile, dwFlags):

                    # return address
                    ra = params[0]

                    # function arguments start from here...
                    szFilename = event.get_process().peek_string(lpFilename)

                    # (...)

                def post_LoadLibraryEx(self, event, return_value):

                    # (...)

            Note that all pointer types are treated like void pointers, so your
            callback won't get the string or structure pointed to by it, but
            the remote memory address instead. This is so to prevent the ctypes
            library from being "too helpful" and trying to dereference the
            pointer. To get the actual data being pointed to, use one of the
            L{Process.read} methods.

        @type  paramCount: int
        @param paramCount:
            (Optional) Number of parameters for the C{preCB} callback,
            not counting the return address. Parameters are read from
            the stack and assumed to be DWORDs in 32 bits and QWORDs in 64.

            This is a faster way to pull stack parameters in 32 bits, but in 64
            bits (or with some odd APIs in 32 bits) it won't be useful, since
            not all arguments to the hooked function will be of the same size.

            For a more reliable and cross-platform way of hooking use the
            C{signature} argument instead.

        @type  signature: tuple
        @param signature:
            (Optional) Tuple of C{ctypes} data types that constitute the
            hooked function signature. When the function is called, this will
            be used to parse the arguments from the stack. Overrides the
            C{paramCount} argument.
        """
        self.__modName = modName
        self.__procName = procName
        self.__paramCount = paramCount
        self.__signature = signature
        self.__preCB = getattr(eventHandler, "pre_%s" % procName, None)
        self.__postCB = getattr(eventHandler, "post_%s" % procName, None)
        self.__hook = dict()

    def __call__(self, event):
        """
        Handles the breakpoint event on entry of the function.

        @type  event: L{ExceptionEvent}
        @param event: Breakpoint hit event.

        @raise WindowsError: An error occured.
        """
        pid = event.get_pid()
        try:
            hook = self.__hook[pid]
        except KeyError:
            hook = Hook(self.__preCB, self.__postCB, self.__paramCount, self.__signature, event.get_process().get_arch())
            self.__hook[pid] = hook
        return hook(event)

    @property
    def modName(self):
        return self.__modName

    @property
    def procName(self):
        return self.__procName

    def hook(self, debug, pid):
        """
        Installs the API hook on a given process and module.

        @warning: Do not call from an API hook callback.

        @type  debug: L{Debug}
        @param debug: Debug object.

        @type  pid: int
        @param pid: Process ID.
        """
        label = "%s!%s" % (self.__modName, self.__procName)
        try:
            hook = self.__hook[pid]
        except KeyError:
            try:
                aProcess = debug.system.get_process(pid)
            except KeyError:
                aProcess = Process(pid)
            hook = Hook(self.__preCB, self.__postCB, self.__paramCount, self.__signature, aProcess.get_arch())
            self.__hook[pid] = hook
        hook.hook(debug, pid, label)

    def unhook(self, debug, pid):
        """
        Removes the API hook from the given process and module.

        @warning: Do not call from an API hook callback.

        @type  debug: L{Debug}
        @param debug: Debug object.

        @type  pid: int
        @param pid: Process ID.
        """
        try:
            hook = self.__hook[pid]
        except KeyError:
            return
        label = "%s!%s" % (self.__modName, self.__procName)
        hook.unhook(debug, pid, label)
        del self.__hook[pid]


# ==============================================================================


class BufferWatch(object):
    """
    Returned by L{Debug.watch_buffer}.

    This object uniquely references a buffer being watched, even if there are
    multiple watches set on the exact memory region.

    @type pid: int
    @ivar pid: Process ID.

    @type start: int
    @ivar start: Memory address of the start of the buffer.

    @type end: int
    @ivar end: Memory address of the end of the buffer.

    @type action: callable
    @ivar action: Action callback.

    @type oneshot: bool
    @ivar oneshot: C{True} for one shot breakpoints, C{False} otherwise.
    """

    def __init__(self, pid, start, end, action=None, oneshot=False):
        self.__pid = pid
        self.__start = start
        self.__end = end
        self.__action = action
        self.__oneshot = oneshot

    @property
    def pid(self):
        return self.__pid

    @property
    def start(self):
        return self.__start

    @property
    def end(self):
        return self.__end

    @property
    def action(self):
        return self.__action

    @property
    def oneshot(self):
        return self.__oneshot

    def match(self, address):
        """
        Determine if the given memory address lies within the watched buffer.

        @rtype: bool
        @return: C{True} if the given memory address lies within the watched
            buffer, C{False} otherwise.
        """
        return self.__start <= address < self.__end


# ==============================================================================


class _BufferWatchCondition(object):
    """
    Used by L{Debug.watch_buffer}.

    This class acts as a condition callback for page breakpoints.
    It emulates page breakpoints that can overlap and/or take up less
    than a page's size.
    """

    def __init__(self):
        self.__ranges = list()  # list of BufferWatch in definition order

    def add(self, bw):
        """
        Adds a buffer watch identifier.

        @type  bw: L{BufferWatch}
        @param bw:
            Buffer watch identifier.
        """
        self.__ranges.append(bw)

    def remove(self, bw):
        """
        Removes a buffer watch identifier.

        @type  bw: L{BufferWatch}
        @param bw:
            Buffer watch identifier.

        @raise KeyError: The buffer watch identifier was already removed.
        """
        try:
            self.__ranges.remove(bw)
        except KeyError:
            if not bw.oneshot:
                raise

    def remove_last_match(self, address, size):
        """
        Removes the last buffer from the watch object
        to match the given address and size.

        @type  address: int
        @param address: Memory address of buffer to stop watching.

        @type  size: int
        @param size: Size in bytes of buffer to stop watching.

        @rtype:  int
        @return: Number of matching elements found. Only the last one to be
            added is actually deleted upon calling this method.

            This counter allows you to know if there are more matching elements
            and how many.
        """
        count = 0
        start = address
        end = address + size - 1
        matched = None
        for item in self.__ranges:
            if item.match(start) and item.match(end):
                matched = item
                count += 1
        self.__ranges.remove(matched)
        return count

    def count(self):
        """
        @rtype:  int
        @return: Number of buffers being watched.
        """
        return len(self.__ranges)

    def __call__(self, event):
        """
        Breakpoint condition callback.

        This method will also call the action callbacks for each
        buffer being watched.

        @type  event: L{ExceptionEvent}
        @param event: Guard page exception event.

        @rtype:  bool
        @return: C{True} if the address being accessed belongs
            to at least one of the buffers that was being watched
            and had no action callback.
        """
        address = event.get_exception_information(1)
        bCondition = False
        for bw in self.__ranges:
            bMatched = bw.match(address)
            try:
                action = bw.action
                if bMatched and action is not None:
                    try:
                        action(event)
                    except Exception:
                        e = sys.exc_info()[1]
                        msg = "Breakpoint action callback %r" " raised an exception: %s"
                        msg = msg % (action, traceback.format_exc(e))
                        warnings.warn(msg, BreakpointCallbackWarning)
                else:
                    bCondition = bCondition or bMatched
            finally:
                if bMatched and bw.oneshot:
                    event.debug.dont_watch_buffer(bw)
        return bCondition


# ==============================================================================


class _BreakpointContainer(object):
    """
    Encapsulates the capability to contain Breakpoint objects.

    @group Breakpoints:
        break_at, watch_variable, watch_buffer, hook_function,
        dont_break_at, dont_watch_variable, dont_watch_buffer,
        dont_hook_function, unhook_function,
        break_on_error, dont_break_on_error

    @group Stalking:
        stalk_at, stalk_variable, stalk_buffer, stalk_function,
        dont_stalk_at, dont_stalk_variable, dont_stalk_buffer,
        dont_stalk_function

    @group Tracing:
        is_tracing, get_traced_tids,
        start_tracing, stop_tracing,
        start_tracing_process, stop_tracing_process,
        start_tracing_all, stop_tracing_all

    @group Symbols:
        resolve_label, resolve_exported_function

    @group Advanced breakpoint use:
        define_code_breakpoint,
        define_page_breakpoint,
        define_hardware_breakpoint,
        has_code_breakpoint,
        has_page_breakpoint,
        has_hardware_breakpoint,
        get_code_breakpoint,
        get_page_breakpoint,
        get_hardware_breakpoint,
        erase_code_breakpoint,
        erase_page_breakpoint,
        erase_hardware_breakpoint,
        enable_code_breakpoint,
        enable_page_breakpoint,
        enable_hardware_breakpoint,
        enable_one_shot_code_breakpoint,
        enable_one_shot_page_breakpoint,
        enable_one_shot_hardware_breakpoint,
        disable_code_breakpoint,
        disable_page_breakpoint,
        disable_hardware_breakpoint

    @group Listing breakpoints:
        get_all_breakpoints,
        get_all_code_breakpoints,
        get_all_page_breakpoints,
        get_all_hardware_breakpoints,
        get_process_breakpoints,
        get_process_code_breakpoints,
        get_process_page_breakpoints,
        get_process_hardware_breakpoints,
        get_thread_hardware_breakpoints,
        get_all_deferred_code_breakpoints,
        get_process_deferred_code_breakpoints

    @group Batch operations on breakpoints:
        enable_all_breakpoints,
        enable_one_shot_all_breakpoints,
        disable_all_breakpoints,
        erase_all_breakpoints,
        enable_process_breakpoints,
        enable_one_shot_process_breakpoints,
        disable_process_breakpoints,
        erase_process_breakpoints

    @group Breakpoint types:
        BP_TYPE_ANY, BP_TYPE_CODE, BP_TYPE_PAGE, BP_TYPE_HARDWARE
    @group Breakpoint states:
        BP_STATE_DISABLED, BP_STATE_ENABLED, BP_STATE_ONESHOT, BP_STATE_RUNNING
    @group Memory breakpoint trigger flags:
        BP_BREAK_ON_EXECUTION, BP_BREAK_ON_WRITE, BP_BREAK_ON_ACCESS
    @group Memory breakpoint size flags:
        BP_WATCH_BYTE, BP_WATCH_WORD, BP_WATCH_DWORD, BP_WATCH_QWORD

    @type BP_TYPE_ANY: int
    @cvar BP_TYPE_ANY: To get all breakpoints
    @type BP_TYPE_CODE: int
    @cvar BP_TYPE_CODE: To get code breakpoints only
    @type BP_TYPE_PAGE: int
    @cvar BP_TYPE_PAGE: To get page breakpoints only
    @type BP_TYPE_HARDWARE: int
    @cvar BP_TYPE_HARDWARE: To get hardware breakpoints only

    @type BP_STATE_DISABLED: int
    @cvar BP_STATE_DISABLED: Breakpoint is disabled.
    @type BP_STATE_ENABLED: int
    @cvar BP_STATE_ENABLED: Breakpoint is enabled.
    @type BP_STATE_ONESHOT: int
    @cvar BP_STATE_ONESHOT: Breakpoint is enabled for one shot.
    @type BP_STATE_RUNNING: int
    @cvar BP_STATE_RUNNING: Breakpoint is running (recently hit).

    @type BP_BREAK_ON_EXECUTION: int
    @cvar BP_BREAK_ON_EXECUTION: Break on code execution.
    @type BP_BREAK_ON_WRITE: int
    @cvar BP_BREAK_ON_WRITE: Break on memory write.
    @type BP_BREAK_ON_ACCESS: int
    @cvar BP_BREAK_ON_ACCESS: Break on memory read or write.
    """

    # Breakpoint types
    BP_TYPE_ANY = 0  # to get all breakpoints
    BP_TYPE_CODE = 1
    BP_TYPE_PAGE = 2
    BP_TYPE_HARDWARE = 3

    # Breakpoint states
    BP_STATE_DISABLED = Breakpoint.DISABLED
    BP_STATE_ENABLED = Breakpoint.ENABLED
    BP_STATE_ONESHOT = Breakpoint.ONESHOT
    BP_STATE_RUNNING = Breakpoint.RUNNING

    # Memory breakpoint trigger flags
    BP_BREAK_ON_EXECUTION = HardwareBreakpoint.BREAK_ON_EXECUTION
    BP_BREAK_ON_WRITE = HardwareBreakpoint.BREAK_ON_WRITE
    BP_BREAK_ON_ACCESS = HardwareBreakpoint.BREAK_ON_ACCESS

    # Memory breakpoint size flags
    BP_WATCH_BYTE = HardwareBreakpoint.WATCH_BYTE
    BP_WATCH_WORD = HardwareBreakpoint.WATCH_WORD
    BP_WATCH_QWORD = HardwareBreakpoint.WATCH_QWORD
    BP_WATCH_DWORD = HardwareBreakpoint.WATCH_DWORD

    def __init__(self):
        self.__codeBP = dict()  # (pid, address) -> CodeBreakpoint
        self.__pageBP = dict()  # (pid, address) -> PageBreakpoint
        self.__hardwareBP = dict()  # tid -> [ HardwareBreakpoint ]
        self.__runningBP = dict()  # tid -> set( Breakpoint )
        self.__tracing = set()  # set( tid )
        self.__deferredBP = dict()  # pid -> label -> (action, oneshot)

    # ------------------------------------------------------------------------------

    # This operates on the dictionary of running breakpoints.
    # Since the bps are meant to stay alive no cleanup is done here.

    def __get_running_bp_set(self, tid):
        "Auxiliary method."
        return self.__runningBP.get(tid, ())

    def __add_running_bp(self, tid, bp):
        "Auxiliary method."
        if tid not in self.__runningBP:
            self.__runningBP[tid] = set()
        self.__runningBP[tid].add(bp)

    def __del_running_bp(self, tid, bp):
        "Auxiliary method."
        self.__runningBP[tid].remove(bp)
        if not self.__runningBP[tid]:
            del self.__runningBP[tid]

    def __del_running_bp_from_all_threads(self, bp):
        "Auxiliary method."
        for tid, bpset in compat.iteritems(self.__runningBP):
            if bp in bpset:
                bpset.remove(bp)
                self.system.get_thread(tid).clear_tf()

    # ------------------------------------------------------------------------------

    # This is the cleanup code. Mostly called on response to exit/unload debug
    # events. If possible it shouldn't raise exceptions on runtime errors.
    # The main goal here is to avoid memory or handle leaks.

    def __cleanup_breakpoint(self, event, bp):
        "Auxiliary method."
        try:
            process = event.get_process()
            thread = event.get_thread()
            bp.disable(process, thread)  # clear the debug regs / trap flag
        except Exception:
            pass
        bp.set_condition(True)  # break possible circular reference
        bp.set_action(None)  # break possible circular reference

    def __cleanup_thread(self, event):
        """
        Auxiliary method for L{_notify_exit_thread}
        and L{_notify_exit_process}.
        """
        tid = event.get_tid()

        # Cleanup running breakpoints
        try:
            for bp in self.__runningBP[tid]:
                self.__cleanup_breakpoint(event, bp)
            del self.__runningBP[tid]
        except KeyError:
            pass

        # Cleanup hardware breakpoints
        try:
            for bp in self.__hardwareBP[tid]:
                self.__cleanup_breakpoint(event, bp)
            del self.__hardwareBP[tid]
        except KeyError:
            pass

        # Cleanup set of threads being traced
        if tid in self.__tracing:
            self.__tracing.remove(tid)

    def __cleanup_process(self, event):
        """
        Auxiliary method for L{_notify_exit_process}.
        """
        pid = event.get_pid()
        process = event.get_process()

        # Cleanup code breakpoints
        for bp_pid, bp_address in compat.keys(self.__codeBP):
            if bp_pid == pid:
                bp = self.__codeBP[(bp_pid, bp_address)]
                self.__cleanup_breakpoint(event, bp)
                del self.__codeBP[(bp_pid, bp_address)]

        # Cleanup page breakpoints
        for bp_pid, bp_address in compat.keys(self.__pageBP):
            if bp_pid == pid:
                bp = self.__pageBP[(bp_pid, bp_address)]
                self.__cleanup_breakpoint(event, bp)
                del self.__pageBP[(bp_pid, bp_address)]

        # Cleanup deferred code breakpoints
        try:
            del self.__deferredBP[pid]
        except KeyError:
            pass

    def __cleanup_module(self, event):
        """
        Auxiliary method for L{_notify_unload_dll}.
        """
        pid = event.get_pid()
        process = event.get_process()
        module = event.get_module()

        # Cleanup thread breakpoints on this module
        for tid in process.iter_thread_ids():
            thread = process.get_thread(tid)

            # Running breakpoints
            if tid in self.__runningBP:
                bplist = list(self.__runningBP[tid])
                for bp in bplist:
                    bp_address = bp.get_address()
                    if process.get_module_at_address(bp_address) == module:
                        self.__cleanup_breakpoint(event, bp)
                        self.__runningBP[tid].remove(bp)

            # Hardware breakpoints
            if tid in self.__hardwareBP:
                bplist = list(self.__hardwareBP[tid])
                for bp in bplist:
                    bp_address = bp.get_address()
                    if process.get_module_at_address(bp_address) == module:
                        self.__cleanup_breakpoint(event, bp)
                        self.__hardwareBP[tid].remove(bp)

        # Cleanup code breakpoints on this module
        for bp_pid, bp_address in compat.keys(self.__codeBP):
            if bp_pid == pid:
                if process.get_module_at_address(bp_address) == module:
                    bp = self.__codeBP[(bp_pid, bp_address)]
                    self.__cleanup_breakpoint(event, bp)
                    del self.__codeBP[(bp_pid, bp_address)]

        # Cleanup page breakpoints on this module
        for bp_pid, bp_address in compat.keys(self.__pageBP):
            if bp_pid == pid:
                if process.get_module_at_address(bp_address) == module:
                    bp = self.__pageBP[(bp_pid, bp_address)]
                    self.__cleanup_breakpoint(event, bp)
                    del self.__pageBP[(bp_pid, bp_address)]

    # ------------------------------------------------------------------------------

    # Defining breakpoints.

    # Code breakpoints.
    def define_code_breakpoint(self, dwProcessId, address, condition=True, action=None):
        """
        Creates a disabled code breakpoint at the given address.

        @see:
            L{has_code_breakpoint},
            L{get_code_breakpoint},
            L{enable_code_breakpoint},
            L{enable_one_shot_code_breakpoint},
            L{disable_code_breakpoint},
            L{erase_code_breakpoint}

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @type  address: int
        @param address: Memory address of the code instruction to break at.

        @type  condition: function
        @param condition: (Optional) Condition callback function.

            The callback signature is::

                def condition_callback(event):
                    return True     # returns True or False

            Where B{event} is an L{Event} object,
            and the return value is a boolean
            (C{True} to dispatch the event, C{False} otherwise).

        @type  action: function
        @param action: (Optional) Action callback function.
            If specified, the event is handled by this callback instead of
            being dispatched normally.

            The callback signature is::

                def action_callback(event):
                    pass        # no return value

            Where B{event} is an L{Event} object,
            and the return value is a boolean
            (C{True} to dispatch the event, C{False} otherwise).

        @rtype:  L{CodeBreakpoint}
        @return: The code breakpoint object.
        """
        process = self.system.get_process(dwProcessId)
        bp = CodeBreakpoint(address, condition, action)

        key = (dwProcessId, bp.get_address())
        if key in self.__codeBP:
            msg = "Already exists (PID %d) : %r"
            raise KeyError(msg % (dwProcessId, self.__codeBP[key]))
        self.__codeBP[key] = bp
        return bp

    # Page breakpoints.
    def define_page_breakpoint(self, dwProcessId, address, pages=1, condition=True, action=None):
        """
        Creates a disabled page breakpoint at the given address.

        @see:
            L{has_page_breakpoint},
            L{get_page_breakpoint},
            L{enable_page_breakpoint},
            L{enable_one_shot_page_breakpoint},
            L{disable_page_breakpoint},
            L{erase_page_breakpoint}

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @type  address: int
        @param address: Memory address of the first page to watch.

        @type  pages: int
        @param pages: Number of pages to watch.

        @type  condition: function
        @param condition: (Optional) Condition callback function.

            The callback signature is::

                def condition_callback(event):
                    return True     # returns True or False

            Where B{event} is an L{Event} object,
            and the return value is a boolean
            (C{True} to dispatch the event, C{False} otherwise).

        @type  action: function
        @param action: (Optional) Action callback function.
            If specified, the event is handled by this callback instead of
            being dispatched normally.

            The callback signature is::

                def action_callback(event):
                    pass        # no return value

            Where B{event} is an L{Event} object,
            and the return value is a boolean
            (C{True} to dispatch the event, C{False} otherwise).

        @rtype:  L{PageBreakpoint}
        @return: The page breakpoint object.
        """
        process = self.system.get_process(dwProcessId)
        bp = PageBreakpoint(address, pages, condition, action)
        begin = bp.get_address()
        end = begin + bp.get_size()

        address = begin
        pageSize = MemoryAddresses.pageSize
        while address < end:
            key = (dwProcessId, address)
            if key in self.__pageBP:
                msg = "Already exists (PID %d) : %r"
                msg = msg % (dwProcessId, self.__pageBP[key])
                raise KeyError(msg)
            address = address + pageSize

        address = begin
        while address < end:
            key = (dwProcessId, address)
            self.__pageBP[key] = bp
            address = address + pageSize
        return bp

    # Hardware breakpoints.
    def define_hardware_breakpoint(
        self, dwThreadId, address, triggerFlag=BP_BREAK_ON_ACCESS, sizeFlag=BP_WATCH_DWORD, condition=True, action=None
    ):
        """
        Creates a disabled hardware breakpoint at the given address.

        @see:
            L{has_hardware_breakpoint},
            L{get_hardware_breakpoint},
            L{enable_hardware_breakpoint},
            L{enable_one_shot_hardware_breakpoint},
            L{disable_hardware_breakpoint},
            L{erase_hardware_breakpoint}

        @note:
            Hardware breakpoints do not seem to work properly on VirtualBox.
            See U{http://www.virtualbox.org/ticket/477}.

        @type  dwThreadId: int
        @param dwThreadId: Thread global ID.

        @type  address: int
        @param address: Memory address to watch.

        @type  triggerFlag: int
        @param triggerFlag: Trigger of breakpoint. Must be one of the following:

             - L{BP_BREAK_ON_EXECUTION}

               Break on code execution.

             - L{BP_BREAK_ON_WRITE}

               Break on memory read or write.

             - L{BP_BREAK_ON_ACCESS}

               Break on memory write.

        @type  sizeFlag: int
        @param sizeFlag: Size of breakpoint. Must be one of the following:

             - L{BP_WATCH_BYTE}

               One (1) byte in size.

             - L{BP_WATCH_WORD}

               Two (2) bytes in size.

             - L{BP_WATCH_DWORD}

               Four (4) bytes in size.

             - L{BP_WATCH_QWORD}

               Eight (8) bytes in size.

        @type  condition: function
        @param condition: (Optional) Condition callback function.

            The callback signature is::

                def condition_callback(event):
                    return True     # returns True or False

            Where B{event} is an L{Event} object,
            and the return value is a boolean
            (C{True} to dispatch the event, C{False} otherwise).

        @type  action: function
        @param action: (Optional) Action callback function.
            If specified, the event is handled by this callback instead of
            being dispatched normally.

            The callback signature is::

                def action_callback(event):
                    pass        # no return value

            Where B{event} is an L{Event} object,
            and the return value is a boolean
            (C{True} to dispatch the event, C{False} otherwise).

        @rtype:  L{HardwareBreakpoint}
        @return: The hardware breakpoint object.
        """
        thread = self.system.get_thread(dwThreadId)
        bp = HardwareBreakpoint(address, triggerFlag, sizeFlag, condition, action)
        begin = bp.get_address()
        end = begin + bp.get_size()

        if dwThreadId in self.__hardwareBP:
            bpSet = self.__hardwareBP[dwThreadId]
            for oldbp in bpSet:
                old_begin = oldbp.get_address()
                old_end = old_begin + oldbp.get_size()
                if MemoryAddresses.do_ranges_intersect(begin, end, old_begin, old_end):
                    msg = "Already exists (TID %d) : %r" % (dwThreadId, oldbp)
                    raise KeyError(msg)
        else:
            bpSet = set()
            self.__hardwareBP[dwThreadId] = bpSet
        bpSet.add(bp)
        return bp

    # ------------------------------------------------------------------------------

    # Checking breakpoint definitions.

    def has_code_breakpoint(self, dwProcessId, address):
        """
        Checks if a code breakpoint is defined at the given address.

        @see:
            L{define_code_breakpoint},
            L{get_code_breakpoint},
            L{erase_code_breakpoint},
            L{enable_code_breakpoint},
            L{enable_one_shot_code_breakpoint},
            L{disable_code_breakpoint}

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @type  address: int
        @param address: Memory address of breakpoint.

        @rtype:  bool
        @return: C{True} if the breakpoint is defined, C{False} otherwise.
        """
        return (dwProcessId, address) in self.__codeBP

    def has_page_breakpoint(self, dwProcessId, address):
        """
        Checks if a page breakpoint is defined at the given address.

        @see:
            L{define_page_breakpoint},
            L{get_page_breakpoint},
            L{erase_page_breakpoint},
            L{enable_page_breakpoint},
            L{enable_one_shot_page_breakpoint},
            L{disable_page_breakpoint}

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @type  address: int
        @param address: Memory address of breakpoint.

        @rtype:  bool
        @return: C{True} if the breakpoint is defined, C{False} otherwise.
        """
        return (dwProcessId, address) in self.__pageBP

    def has_hardware_breakpoint(self, dwThreadId, address):
        """
        Checks if a hardware breakpoint is defined at the given address.

        @see:
            L{define_hardware_breakpoint},
            L{get_hardware_breakpoint},
            L{erase_hardware_breakpoint},
            L{enable_hardware_breakpoint},
            L{enable_one_shot_hardware_breakpoint},
            L{disable_hardware_breakpoint}

        @type  dwThreadId: int
        @param dwThreadId: Thread global ID.

        @type  address: int
        @param address: Memory address of breakpoint.

        @rtype:  bool
        @return: C{True} if the breakpoint is defined, C{False} otherwise.
        """
        if dwThreadId in self.__hardwareBP:
            bpSet = self.__hardwareBP[dwThreadId]
            for bp in bpSet:
                if bp.get_address() == address:
                    return True
        return False

    # ------------------------------------------------------------------------------

    # Getting breakpoints.

    def get_code_breakpoint(self, dwProcessId, address):
        """
        Returns the internally used breakpoint object,
        for the code breakpoint defined at the given address.

        @warning: It's usually best to call the L{Debug} methods
            instead of accessing the breakpoint objects directly.

        @see:
            L{define_code_breakpoint},
            L{has_code_breakpoint},
            L{enable_code_breakpoint},
            L{enable_one_shot_code_breakpoint},
            L{disable_code_breakpoint},
            L{erase_code_breakpoint}

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @type  address: int
        @param address: Memory address where the breakpoint is defined.

        @rtype:  L{CodeBreakpoint}
        @return: The code breakpoint object.
        """
        key = (dwProcessId, address)
        if key not in self.__codeBP:
            msg = "No breakpoint at process %d, address %s"
            address = HexDump.address(address)
            raise KeyError(msg % (dwProcessId, address))
        return self.__codeBP[key]

    def get_page_breakpoint(self, dwProcessId, address):
        """
        Returns the internally used breakpoint object,
        for the page breakpoint defined at the given address.

        @warning: It's usually best to call the L{Debug} methods
            instead of accessing the breakpoint objects directly.

        @see:
            L{define_page_breakpoint},
            L{has_page_breakpoint},
            L{enable_page_breakpoint},
            L{enable_one_shot_page_breakpoint},
            L{disable_page_breakpoint},
            L{erase_page_breakpoint}

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @type  address: int
        @param address: Memory address where the breakpoint is defined.

        @rtype:  L{PageBreakpoint}
        @return: The page breakpoint object.
        """
        key = (dwProcessId, address)
        if key not in self.__pageBP:
            msg = "No breakpoint at process %d, address %s"
            address = HexDump.addresS(address)
            raise KeyError(msg % (dwProcessId, address))
        return self.__pageBP[key]

    def get_hardware_breakpoint(self, dwThreadId, address):
        """
        Returns the internally used breakpoint object,
        for the code breakpoint defined at the given address.

        @warning: It's usually best to call the L{Debug} methods
            instead of accessing the breakpoint objects directly.

        @see:
            L{define_hardware_breakpoint},
            L{has_hardware_breakpoint},
            L{get_code_breakpoint},
            L{enable_hardware_breakpoint},
            L{enable_one_shot_hardware_breakpoint},
            L{disable_hardware_breakpoint},
            L{erase_hardware_breakpoint}

        @type  dwThreadId: int
        @param dwThreadId: Thread global ID.

        @type  address: int
        @param address: Memory address where the breakpoint is defined.

        @rtype:  L{HardwareBreakpoint}
        @return: The hardware breakpoint object.
        """
        if dwThreadId not in self.__hardwareBP:
            msg = "No hardware breakpoints set for thread %d"
            raise KeyError(msg % dwThreadId)
        for bp in self.__hardwareBP[dwThreadId]:
            if bp.is_here(address):
                return bp
        msg = "No hardware breakpoint at thread %d, address %s"
        raise KeyError(msg % (dwThreadId, HexDump.address(address)))

    # ------------------------------------------------------------------------------

    # Enabling and disabling breakpoints.

    def enable_code_breakpoint(self, dwProcessId, address):
        """
        Enables the code breakpoint at the given address.

        @see:
            L{define_code_breakpoint},
            L{has_code_breakpoint},
            L{enable_one_shot_code_breakpoint},
            L{disable_code_breakpoint}
            L{erase_code_breakpoint},

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @type  address: int
        @param address: Memory address of breakpoint.
        """
        p = self.system.get_process(dwProcessId)
        bp = self.get_code_breakpoint(dwProcessId, address)
        if bp.is_running():
            self.__del_running_bp_from_all_threads(bp)
        bp.enable(p, None)  # XXX HACK thread is not used

    def enable_page_breakpoint(self, dwProcessId, address):
        """
        Enables the page breakpoint at the given address.

        @see:
            L{define_page_breakpoint},
            L{has_page_breakpoint},
            L{get_page_breakpoint},
            L{enable_one_shot_page_breakpoint},
            L{disable_page_breakpoint}
            L{erase_page_breakpoint},

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @type  address: int
        @param address: Memory address of breakpoint.
        """
        p = self.system.get_process(dwProcessId)
        bp = self.get_page_breakpoint(dwProcessId, address)
        if bp.is_running():
            self.__del_running_bp_from_all_threads(bp)
        bp.enable(p, None)  # XXX HACK thread is not used

    def enable_hardware_breakpoint(self, dwThreadId, address):
        """
        Enables the hardware breakpoint at the given address.

        @see:
            L{define_hardware_breakpoint},
            L{has_hardware_breakpoint},
            L{get_hardware_breakpoint},
            L{enable_one_shot_hardware_breakpoint},
            L{disable_hardware_breakpoint}
            L{erase_hardware_breakpoint},

        @note: Do not set hardware breakpoints while processing the system
            breakpoint event.

        @type  dwThreadId: int
        @param dwThreadId: Thread global ID.

        @type  address: int
        @param address: Memory address of breakpoint.
        """
        t = self.system.get_thread(dwThreadId)
        bp = self.get_hardware_breakpoint(dwThreadId, address)
        if bp.is_running():
            self.__del_running_bp_from_all_threads(bp)
        bp.enable(None, t)  # XXX HACK process is not used

    def enable_one_shot_code_breakpoint(self, dwProcessId, address):
        """
        Enables the code breakpoint at the given address for only one shot.

        @see:
            L{define_code_breakpoint},
            L{has_code_breakpoint},
            L{get_code_breakpoint},
            L{enable_code_breakpoint},
            L{disable_code_breakpoint}
            L{erase_code_breakpoint},

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @type  address: int
        @param address: Memory address of breakpoint.
        """
        p = self.system.get_process(dwProcessId)
        bp = self.get_code_breakpoint(dwProcessId, address)
        if bp.is_running():
            self.__del_running_bp_from_all_threads(bp)
        bp.one_shot(p, None)  # XXX HACK thread is not used

    def enable_one_shot_page_breakpoint(self, dwProcessId, address):
        """
        Enables the page breakpoint at the given address for only one shot.

        @see:
            L{define_page_breakpoint},
            L{has_page_breakpoint},
            L{get_page_breakpoint},
            L{enable_page_breakpoint},
            L{disable_page_breakpoint}
            L{erase_page_breakpoint},

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @type  address: int
        @param address: Memory address of breakpoint.
        """
        p = self.system.get_process(dwProcessId)
        bp = self.get_page_breakpoint(dwProcessId, address)
        if bp.is_running():
            self.__del_running_bp_from_all_threads(bp)
        bp.one_shot(p, None)  # XXX HACK thread is not used

    def enable_one_shot_hardware_breakpoint(self, dwThreadId, address):
        """
        Enables the hardware breakpoint at the given address for only one shot.

        @see:
            L{define_hardware_breakpoint},
            L{has_hardware_breakpoint},
            L{get_hardware_breakpoint},
            L{enable_hardware_breakpoint},
            L{disable_hardware_breakpoint}
            L{erase_hardware_breakpoint},

        @type  dwThreadId: int
        @param dwThreadId: Thread global ID.

        @type  address: int
        @param address: Memory address of breakpoint.
        """
        t = self.system.get_thread(dwThreadId)
        bp = self.get_hardware_breakpoint(dwThreadId, address)
        if bp.is_running():
            self.__del_running_bp_from_all_threads(bp)
        bp.one_shot(None, t)  # XXX HACK process is not used

    def disable_code_breakpoint(self, dwProcessId, address):
        """
        Disables the code breakpoint at the given address.

        @see:
            L{define_code_breakpoint},
            L{has_code_breakpoint},
            L{get_code_breakpoint},
            L{enable_code_breakpoint}
            L{enable_one_shot_code_breakpoint},
            L{erase_code_breakpoint},

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @type  address: int
        @param address: Memory address of breakpoint.
        """
        p = self.system.get_process(dwProcessId)
        bp = self.get_code_breakpoint(dwProcessId, address)
        if bp.is_running():
            self.__del_running_bp_from_all_threads(bp)
        bp.disable(p, None)  # XXX HACK thread is not used

    def disable_page_breakpoint(self, dwProcessId, address):
        """
        Disables the page breakpoint at the given address.

        @see:
            L{define_page_breakpoint},
            L{has_page_breakpoint},
            L{get_page_breakpoint},
            L{enable_page_breakpoint}
            L{enable_one_shot_page_breakpoint},
            L{erase_page_breakpoint},

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @type  address: int
        @param address: Memory address of breakpoint.
        """
        p = self.system.get_process(dwProcessId)
        bp = self.get_page_breakpoint(dwProcessId, address)
        if bp.is_running():
            self.__del_running_bp_from_all_threads(bp)
        bp.disable(p, None)  # XXX HACK thread is not used

    def disable_hardware_breakpoint(self, dwThreadId, address):
        """
        Disables the hardware breakpoint at the given address.

        @see:
            L{define_hardware_breakpoint},
            L{has_hardware_breakpoint},
            L{get_hardware_breakpoint},
            L{enable_hardware_breakpoint}
            L{enable_one_shot_hardware_breakpoint},
            L{erase_hardware_breakpoint},

        @type  dwThreadId: int
        @param dwThreadId: Thread global ID.

        @type  address: int
        @param address: Memory address of breakpoint.
        """
        t = self.system.get_thread(dwThreadId)
        p = t.get_process()
        bp = self.get_hardware_breakpoint(dwThreadId, address)
        if bp.is_running():
            self.__del_running_bp(dwThreadId, bp)
        bp.disable(p, t)

    # ------------------------------------------------------------------------------

    # Undefining (erasing) breakpoints.

    def erase_code_breakpoint(self, dwProcessId, address):
        """
        Erases the code breakpoint at the given address.

        @see:
            L{define_code_breakpoint},
            L{has_code_breakpoint},
            L{get_code_breakpoint},
            L{enable_code_breakpoint},
            L{enable_one_shot_code_breakpoint},
            L{disable_code_breakpoint}

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @type  address: int
        @param address: Memory address of breakpoint.
        """
        bp = self.get_code_breakpoint(dwProcessId, address)
        if not bp.is_disabled():
            self.disable_code_breakpoint(dwProcessId, address)
        del self.__codeBP[(dwProcessId, address)]

    def erase_page_breakpoint(self, dwProcessId, address):
        """
        Erases the page breakpoint at the given address.

        @see:
            L{define_page_breakpoint},
            L{has_page_breakpoint},
            L{get_page_breakpoint},
            L{enable_page_breakpoint},
            L{enable_one_shot_page_breakpoint},
            L{disable_page_breakpoint}

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @type  address: int
        @param address: Memory address of breakpoint.
        """
        bp = self.get_page_breakpoint(dwProcessId, address)
        begin = bp.get_address()
        end = begin + bp.get_size()
        if not bp.is_disabled():
            self.disable_page_breakpoint(dwProcessId, address)
        address = begin
        pageSize = MemoryAddresses.pageSize
        while address < end:
            del self.__pageBP[(dwProcessId, address)]
            address = address + pageSize

    def erase_hardware_breakpoint(self, dwThreadId, address):
        """
        Erases the hardware breakpoint at the given address.

        @see:
            L{define_hardware_breakpoint},
            L{has_hardware_breakpoint},
            L{get_hardware_breakpoint},
            L{enable_hardware_breakpoint},
            L{enable_one_shot_hardware_breakpoint},
            L{disable_hardware_breakpoint}

        @type  dwThreadId: int
        @param dwThreadId: Thread global ID.

        @type  address: int
        @param address: Memory address of breakpoint.
        """
        bp = self.get_hardware_breakpoint(dwThreadId, address)
        if not bp.is_disabled():
            self.disable_hardware_breakpoint(dwThreadId, address)
        bpSet = self.__hardwareBP[dwThreadId]
        bpSet.remove(bp)
        if not bpSet:
            del self.__hardwareBP[dwThreadId]

    # ------------------------------------------------------------------------------

    # Listing breakpoints.

    def get_all_breakpoints(self):
        """
        Returns all breakpoint objects as a list of tuples.

        Each tuple contains:
         - Process global ID to which the breakpoint applies.
         - Thread global ID to which the breakpoint applies, or C{None}.
         - The L{Breakpoint} object itself.

        @note: If you're only interested in a specific breakpoint type, or in
            breakpoints for a specific process or thread, it's probably faster
            to call one of the following methods:
             - L{get_all_code_breakpoints}
             - L{get_all_page_breakpoints}
             - L{get_all_hardware_breakpoints}
             - L{get_process_code_breakpoints}
             - L{get_process_page_breakpoints}
             - L{get_process_hardware_breakpoints}
             - L{get_thread_hardware_breakpoints}

        @rtype:  list of tuple( pid, tid, bp )
        @return: List of all breakpoints.
        """
        bplist = list()

        # Get the code breakpoints.
        for pid, bp in self.get_all_code_breakpoints():
            bplist.append((pid, None, bp))

        # Get the page breakpoints.
        for pid, bp in self.get_all_page_breakpoints():
            bplist.append((pid, None, bp))

        # Get the hardware breakpoints.
        for tid, bp in self.get_all_hardware_breakpoints():
            pid = self.system.get_thread(tid).get_pid()
            bplist.append((pid, tid, bp))

        # Return the list of breakpoints.
        return bplist

    def get_all_code_breakpoints(self):
        """
        @rtype:  list of tuple( int, L{CodeBreakpoint} )
        @return: All code breakpoints as a list of tuples (pid, bp).
        """
        return [(pid, bp) for ((pid, address), bp) in compat.iteritems(self.__codeBP)]

    def get_all_page_breakpoints(self):
        """
        @rtype:  list of tuple( int, L{PageBreakpoint} )
        @return: All page breakpoints as a list of tuples (pid, bp).
        """
        ##        return list( set( [ (pid, bp) for ((pid, address), bp) in compat.iteritems(self.__pageBP) ] ) )
        result = set()
        for (pid, address), bp in compat.iteritems(self.__pageBP):
            result.add((pid, bp))
        return list(result)

    def get_all_hardware_breakpoints(self):
        """
        @rtype:  list of tuple( int, L{HardwareBreakpoint} )
        @return: All hardware breakpoints as a list of tuples (tid, bp).
        """
        result = list()
        for tid, bplist in compat.iteritems(self.__hardwareBP):
            for bp in bplist:
                result.append((tid, bp))
        return result

    def get_process_breakpoints(self, dwProcessId):
        """
        Returns all breakpoint objects for the given process as a list of tuples.

        Each tuple contains:
         - Process global ID to which the breakpoint applies.
         - Thread global ID to which the breakpoint applies, or C{None}.
         - The L{Breakpoint} object itself.

        @note: If you're only interested in a specific breakpoint type, or in
            breakpoints for a specific process or thread, it's probably faster
            to call one of the following methods:
             - L{get_all_code_breakpoints}
             - L{get_all_page_breakpoints}
             - L{get_all_hardware_breakpoints}
             - L{get_process_code_breakpoints}
             - L{get_process_page_breakpoints}
             - L{get_process_hardware_breakpoints}
             - L{get_thread_hardware_breakpoints}

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @rtype:  list of tuple( pid, tid, bp )
        @return: List of all breakpoints for the given process.
        """
        bplist = list()

        # Get the code breakpoints.
        for bp in self.get_process_code_breakpoints(dwProcessId):
            bplist.append((dwProcessId, None, bp))

        # Get the page breakpoints.
        for bp in self.get_process_page_breakpoints(dwProcessId):
            bplist.append((dwProcessId, None, bp))

        # Get the hardware breakpoints.
        for tid, bp in self.get_process_hardware_breakpoints(dwProcessId):
            pid = self.system.get_thread(tid).get_pid()
            bplist.append((dwProcessId, tid, bp))

        # Return the list of breakpoints.
        return bplist

    def get_process_code_breakpoints(self, dwProcessId):
        """
        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @rtype:  list of L{CodeBreakpoint}
        @return: All code breakpoints for the given process.
        """
        return [bp for ((pid, address), bp) in compat.iteritems(self.__codeBP) if pid == dwProcessId]

    def get_process_page_breakpoints(self, dwProcessId):
        """
        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @rtype:  list of L{PageBreakpoint}
        @return: All page breakpoints for the given process.
        """
        return [bp for ((pid, address), bp) in compat.iteritems(self.__pageBP) if pid == dwProcessId]

    def get_thread_hardware_breakpoints(self, dwThreadId):
        """
        @see: L{get_process_hardware_breakpoints}

        @type  dwThreadId: int
        @param dwThreadId: Thread global ID.

        @rtype:  list of L{HardwareBreakpoint}
        @return: All hardware breakpoints for the given thread.
        """
        result = list()
        for tid, bplist in compat.iteritems(self.__hardwareBP):
            if tid == dwThreadId:
                for bp in bplist:
                    result.append(bp)
        return result

    def get_process_hardware_breakpoints(self, dwProcessId):
        """
        @see: L{get_thread_hardware_breakpoints}

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.

        @rtype:  list of tuple( int, L{HardwareBreakpoint} )
        @return: All hardware breakpoints for each thread in the given process
            as a list of tuples (tid, bp).
        """
        result = list()
        aProcess = self.system.get_process(dwProcessId)
        for dwThreadId in aProcess.iter_thread_ids():
            if dwThreadId in self.__hardwareBP:
                bplist = self.__hardwareBP[dwThreadId]
                for bp in bplist:
                    result.append((dwThreadId, bp))
        return result

    ##    def get_all_hooks(self):
    ##        """
    ##        @see: L{get_process_hooks}
    ##
    ##        @rtype:  list of tuple( int, int, L{Hook} )
    ##        @return: All defined hooks as a list of tuples (pid, address, hook).
    ##        """
    ##        return [ (pid, address, hook) \
    ##            for ((pid, address), hook) in self.__hook_objects ]
    ##
    ##    def get_process_hooks(self, dwProcessId):
    ##        """
    ##        @see: L{get_all_hooks}
    ##
    ##        @type  dwProcessId: int
    ##        @param dwProcessId: Process global ID.
    ##
    ##        @rtype:  list of tuple( int, int, L{Hook} )
    ##        @return: All hooks for the given process as a list of tuples
    ##            (pid, address, hook).
    ##        """
    ##        return [ (pid, address, hook) \
    ##            for ((pid, address), hook) in self.__hook_objects \
    ##            if pid == dwProcessId ]

    # ------------------------------------------------------------------------------

    # Batch operations on all breakpoints.

    def enable_all_breakpoints(self):
        """
        Enables all disabled breakpoints in all processes.

        @see:
            enable_code_breakpoint,
            enable_page_breakpoint,
            enable_hardware_breakpoint
        """

        # disable code breakpoints
        for pid, bp in self.get_all_code_breakpoints():
            if bp.is_disabled():
                self.enable_code_breakpoint(pid, bp.get_address())

        # disable page breakpoints
        for pid, bp in self.get_all_page_breakpoints():
            if bp.is_disabled():
                self.enable_page_breakpoint(pid, bp.get_address())

        # disable hardware breakpoints
        for tid, bp in self.get_all_hardware_breakpoints():
            if bp.is_disabled():
                self.enable_hardware_breakpoint(tid, bp.get_address())

    def enable_one_shot_all_breakpoints(self):
        """
        Enables for one shot all disabled breakpoints in all processes.

        @see:
            enable_one_shot_code_breakpoint,
            enable_one_shot_page_breakpoint,
            enable_one_shot_hardware_breakpoint
        """

        # disable code breakpoints for one shot
        for pid, bp in self.get_all_code_breakpoints():
            if bp.is_disabled():
                self.enable_one_shot_code_breakpoint(pid, bp.get_address())

        # disable page breakpoints for one shot
        for pid, bp in self.get_all_page_breakpoints():
            if bp.is_disabled():
                self.enable_one_shot_page_breakpoint(pid, bp.get_address())

        # disable hardware breakpoints for one shot
        for tid, bp in self.get_all_hardware_breakpoints():
            if bp.is_disabled():
                self.enable_one_shot_hardware_breakpoint(tid, bp.get_address())

    def disable_all_breakpoints(self):
        """
        Disables all breakpoints in all processes.

        @see:
            disable_code_breakpoint,
            disable_page_breakpoint,
            disable_hardware_breakpoint
        """

        # disable code breakpoints
        for pid, bp in self.get_all_code_breakpoints():
            self.disable_code_breakpoint(pid, bp.get_address())

        # disable page breakpoints
        for pid, bp in self.get_all_page_breakpoints():
            self.disable_page_breakpoint(pid, bp.get_address())

        # disable hardware breakpoints
        for tid, bp in self.get_all_hardware_breakpoints():
            self.disable_hardware_breakpoint(tid, bp.get_address())

    def erase_all_breakpoints(self):
        """
        Erases all breakpoints in all processes.

        @see:
            erase_code_breakpoint,
            erase_page_breakpoint,
            erase_hardware_breakpoint
        """

        # This should be faster but let's not trust the GC so much :P
        # self.disable_all_breakpoints()
        # self.__codeBP       = dict()
        # self.__pageBP       = dict()
        # self.__hardwareBP   = dict()
        # self.__runningBP    = dict()
        # self.__hook_objects = dict()

        ##        # erase hooks
        ##        for (pid, address, hook) in self.get_all_hooks():
        ##            self.dont_hook_function(pid, address)

        # erase code breakpoints
        for pid, bp in self.get_all_code_breakpoints():
            self.erase_code_breakpoint(pid, bp.get_address())

        # erase page breakpoints
        for pid, bp in self.get_all_page_breakpoints():
            self.erase_page_breakpoint(pid, bp.get_address())

        # erase hardware breakpoints
        for tid, bp in self.get_all_hardware_breakpoints():
            self.erase_hardware_breakpoint(tid, bp.get_address())

    # ------------------------------------------------------------------------------

    # Batch operations on breakpoints per process.

    def enable_process_breakpoints(self, dwProcessId):
        """
        Enables all disabled breakpoints for the given process.

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.
        """

        # enable code breakpoints
        for bp in self.get_process_code_breakpoints(dwProcessId):
            if bp.is_disabled():
                self.enable_code_breakpoint(dwProcessId, bp.get_address())

        # enable page breakpoints
        for bp in self.get_process_page_breakpoints(dwProcessId):
            if bp.is_disabled():
                self.enable_page_breakpoint(dwProcessId, bp.get_address())

        # enable hardware breakpoints
        if self.system.has_process(dwProcessId):
            aProcess = self.system.get_process(dwProcessId)
        else:
            aProcess = Process(dwProcessId)
            aProcess.scan_threads()
        for aThread in aProcess.iter_threads():
            dwThreadId = aThread.get_tid()
            for bp in self.get_thread_hardware_breakpoints(dwThreadId):
                if bp.is_disabled():
                    self.enable_hardware_breakpoint(dwThreadId, bp.get_address())

    def enable_one_shot_process_breakpoints(self, dwProcessId):
        """
        Enables for one shot all disabled breakpoints for the given process.

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.
        """

        # enable code breakpoints for one shot
        for bp in self.get_process_code_breakpoints(dwProcessId):
            if bp.is_disabled():
                self.enable_one_shot_code_breakpoint(dwProcessId, bp.get_address())

        # enable page breakpoints for one shot
        for bp in self.get_process_page_breakpoints(dwProcessId):
            if bp.is_disabled():
                self.enable_one_shot_page_breakpoint(dwProcessId, bp.get_address())

        # enable hardware breakpoints for one shot
        if self.system.has_process(dwProcessId):
            aProcess = self.system.get_process(dwProcessId)
        else:
            aProcess = Process(dwProcessId)
            aProcess.scan_threads()
        for aThread in aProcess.iter_threads():
            dwThreadId = aThread.get_tid()
            for bp in self.get_thread_hardware_breakpoints(dwThreadId):
                if bp.is_disabled():
                    self.enable_one_shot_hardware_breakpoint(dwThreadId, bp.get_address())

    def disable_process_breakpoints(self, dwProcessId):
        """
        Disables all breakpoints for the given process.

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.
        """

        # disable code breakpoints
        for bp in self.get_process_code_breakpoints(dwProcessId):
            self.disable_code_breakpoint(dwProcessId, bp.get_address())

        # disable page breakpoints
        for bp in self.get_process_page_breakpoints(dwProcessId):
            self.disable_page_breakpoint(dwProcessId, bp.get_address())

        # disable hardware breakpoints
        if self.system.has_process(dwProcessId):
            aProcess = self.system.get_process(dwProcessId)
        else:
            aProcess = Process(dwProcessId)
            aProcess.scan_threads()
        for aThread in aProcess.iter_threads():
            dwThreadId = aThread.get_tid()
            for bp in self.get_thread_hardware_breakpoints(dwThreadId):
                self.disable_hardware_breakpoint(dwThreadId, bp.get_address())

    def erase_process_breakpoints(self, dwProcessId):
        """
        Erases all breakpoints for the given process.

        @type  dwProcessId: int
        @param dwProcessId: Process global ID.
        """

        # disable breakpoints first
        # if an error occurs, no breakpoint is erased
        self.disable_process_breakpoints(dwProcessId)

        ##        # erase hooks
        ##        for address, hook in self.get_process_hooks(dwProcessId):
        ##            self.dont_hook_function(dwProcessId, address)

        # erase code breakpoints
        for bp in self.get_process_code_breakpoints(dwProcessId):
            self.erase_code_breakpoint(dwProcessId, bp.get_address())

        # erase page breakpoints
        for bp in self.get_process_page_breakpoints(dwProcessId):
            self.erase_page_breakpoint(dwProcessId, bp.get_address())

        # erase hardware breakpoints
        if self.system.has_process(dwProcessId):
            aProcess = self.system.get_process(dwProcessId)
        else:
            aProcess = Process(dwProcessId)
            aProcess.scan_threads()
        for aThread in aProcess.iter_threads():
            dwThreadId = aThread.get_tid()
            for bp in self.get_thread_hardware_breakpoints(dwThreadId):
                self.erase_hardware_breakpoint(dwThreadId, bp.get_address())

    # ------------------------------------------------------------------------------

    # Internal handlers of debug events.

    def _notify_guard_page(self, event):
        """
        Notify breakpoints of a guard page exception event.

        @type  event: L{ExceptionEvent}
        @param event: Guard page exception event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """
        address = event.get_fault_address()
        pid = event.get_pid()
        bCallHandler = True

        # Align address to page boundary.
        mask = ~(MemoryAddresses.pageSize - 1)
        address = address & mask

        # Do we have an active page breakpoint there?
        key = (pid, address)
        if key in self.__pageBP:
            bp = self.__pageBP[key]
            if bp.is_enabled() or bp.is_one_shot():
                # Breakpoint is ours.
                event.continueStatus = win32.DBG_CONTINUE
                ##                event.continueStatus = win32.DBG_EXCEPTION_HANDLED

                # Hit the breakpoint.
                bp.hit(event)

                # Remember breakpoints in RUNNING state.
                if bp.is_running():
                    tid = event.get_tid()
                    self.__add_running_bp(tid, bp)

                # Evaluate the breakpoint condition.
                bCondition = bp.eval_condition(event)

                # If the breakpoint is automatic, run the action.
                # If not, notify the user.
                if bCondition and bp.is_automatic():
                    bp.run_action(event)
                    bCallHandler = False
                else:
                    bCallHandler = bCondition

        # If we don't have a breakpoint here pass the exception to the debugee.
        # This is a normally occurring exception so we shouldn't swallow it.
        else:
            event.continueStatus = win32.DBG_EXCEPTION_NOT_HANDLED

        return bCallHandler

    def _notify_breakpoint(self, event):
        """
        Notify breakpoints of a breakpoint exception event.

        @type  event: L{ExceptionEvent}
        @param event: Breakpoint exception event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """
        address = event.get_exception_address()
        pid = event.get_pid()
        bCallHandler = True

        # Do we have an active code breakpoint there?
        key = (pid, address)
        if key in self.__codeBP:
            bp = self.__codeBP[key]
            if not bp.is_disabled():
                # Change the program counter (PC) to the exception address.
                # This accounts for the change in PC caused by
                # executing the breakpoint instruction, no matter
                # the size of it.
                aThread = event.get_thread()
                aThread.set_pc(address)

                # Swallow the exception.
                event.continueStatus = win32.DBG_CONTINUE

                # Hit the breakpoint.
                bp.hit(event)

                # Remember breakpoints in RUNNING state.
                if bp.is_running():
                    tid = event.get_tid()
                    self.__add_running_bp(tid, bp)

                # Evaluate the breakpoint condition.
                bCondition = bp.eval_condition(event)

                # If the breakpoint is automatic, run the action.
                # If not, notify the user.
                if bCondition and bp.is_automatic():
                    bCallHandler = bp.run_action(event)
                else:
                    bCallHandler = bCondition

        # Handle the system breakpoint.
        # TODO: examine the stack trace to figure out if it's really a
        # system breakpoint or an antidebug trick. The caller should be
        # inside ntdll if it's legit.
        elif event.get_process().is_system_defined_breakpoint(address):
            event.continueStatus = win32.DBG_CONTINUE

        # In hostile mode, if we don't have a breakpoint here pass the
        # exception to the debugee. In normal mode assume all breakpoint
        # exceptions are to be handled by the debugger.
        else:
            if self.in_hostile_mode():
                event.continueStatus = win32.DBG_EXCEPTION_NOT_HANDLED
            else:
                event.continueStatus = win32.DBG_CONTINUE

        return bCallHandler

    def _notify_single_step(self, event):
        """
        Notify breakpoints of a single step exception event.

        @type  event: L{ExceptionEvent}
        @param event: Single step exception event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """
        pid = event.get_pid()
        tid = event.get_tid()
        aThread = event.get_thread()
        aProcess = event.get_process()
        bCallHandler = True
        bIsOurs = False

        # In hostile mode set the default to pass the exception to the debugee.
        # If we later determine the exception is ours, hide it instead.
        old_continueStatus = event.continueStatus
        try:
            if self.in_hostile_mode():
                event.continueStatus = win32.DBG_EXCEPTION_NOT_HANDLED

            # Single step support is implemented on x86/x64 architectures only.
            if self.system.arch not in (win32.ARCH_I386, win32.ARCH_AMD64):
                return bCallHandler

            # In hostile mode, read the last executed bytes to try to detect
            # some antidebug tricks. Skip this check in normal mode because
            # it'd slow things down.
            #
            # FIXME: weird opcode encodings may bypass this check!
            #
            # bFakeSingleStep: Ice Breakpoint undocumented instruction.
            # bHideTrapFlag: Don't let pushf instructions get the real value of
            #                the trap flag.
            # bNextIsPopFlags: Don't let popf instructions clear the trap flag.
            #
            bFakeSingleStep = False
            bLastIsPushFlags = False
            bNextIsPopFlags = False
            if self.in_hostile_mode():
                pc = aThread.get_pc()
                c = aProcess.read_char(pc - 1)
                if c == 0xF1:  # int1
                    bFakeSingleStep = True
                elif c == 0x9C:  # pushf
                    bLastIsPushFlags = True
                c = aProcess.peek_char(pc)
                if c == 0x66:  # the only valid prefix for popf
                    c = aProcess.peek_char(pc + 1)
                if c == 0x9D:  # popf
                    if bLastIsPushFlags:
                        bLastIsPushFlags = False  # they cancel each other out
                    else:
                        bNextIsPopFlags = True

            # When the thread is in tracing mode,
            # don't pass the exception to the debugee
            # and set the trap flag again.
            if self.is_tracing(tid):
                bIsOurs = True
                if not bFakeSingleStep:
                    event.continueStatus = win32.DBG_CONTINUE
                aThread.set_tf()

                # Don't let the debugee read or write the trap flag.
                # This code works in 32 and 64 bits thanks to the endianness.
                if bLastIsPushFlags or bNextIsPopFlags:
                    sp = aThread.get_sp()
                    flags = aProcess.read_dword(sp)
                    if bLastIsPushFlags:
                        flags &= ~Thread.Flags.Trap
                    else:  # if bNextIsPopFlags:
                        flags |= Thread.Flags.Trap
                    aProcess.write_dword(sp, flags)

            # Handle breakpoints in RUNNING state.
            running = self.__get_running_bp_set(tid)
            if running:
                bIsOurs = True
                if not bFakeSingleStep:
                    event.continueStatus = win32.DBG_CONTINUE
                bCallHandler = False
                while running:
                    try:
                        running.pop().hit(event)
                    except Exception:
                        e = sys.exc_info()[1]
                        warnings.warn(str(e), BreakpointWarning)

            # Handle hardware breakpoints.
            if tid in self.__hardwareBP:
                ctx = aThread.get_context(win32.CONTEXT_DEBUG_REGISTERS)
                Dr6 = ctx["Dr6"]
                ctx["Dr6"] = Dr6 & DebugRegister.clearHitMask
                aThread.set_context(ctx)
                bFoundBreakpoint = False
                bCondition = False
                hwbpList = [bp for bp in self.__hardwareBP[tid]]
                for bp in hwbpList:
                    if not bp in self.__hardwareBP[tid]:
                        continue  # it was removed by a user-defined callback
                    slot = bp.get_slot()
                    if (slot is not None) and (Dr6 & DebugRegister.hitMask[slot]):
                        if not bFoundBreakpoint:  # set before actions are called
                            if not bFakeSingleStep:
                                event.continueStatus = win32.DBG_CONTINUE
                        bFoundBreakpoint = True
                        bIsOurs = True
                        bp.hit(event)
                        if bp.is_running():
                            self.__add_running_bp(tid, bp)
                        bThisCondition = bp.eval_condition(event)
                        if bThisCondition and bp.is_automatic():
                            bp.run_action(event)
                            bThisCondition = False
                        bCondition = bCondition or bThisCondition
                if bFoundBreakpoint:
                    bCallHandler = bCondition

            # Always call the user-defined handler
            # when the thread is in tracing mode.
            if self.is_tracing(tid):
                bCallHandler = True

            # If we're not in hostile mode, by default we assume all single
            # step exceptions are caused by the debugger.
            if not bIsOurs and not self.in_hostile_mode():
                aThread.clear_tf()

        # If the user hit Control-C while we were inside the try block,
        # set the default continueStatus back.
        except:
            event.continueStatus = old_continueStatus
            raise

        return bCallHandler

    def _notify_load_dll(self, event):
        """
        Notify the loading of a DLL.

        @type  event: L{LoadDLLEvent}
        @param event: Load DLL event.

        @rtype:  bool
        @return: C{True} to call the user-defined handler, C{False} otherwise.
        """
        self.__set_deferred_breakpoints(event)
        return True

    def _notify_unload_dll(self, event):
        """
        Notify the unloading of a DLL.

        @type  event: L{UnloadDLLEvent}
        @param event: Unload DLL event.

        @rtype:  bool
        @return: C{True} to call the user-defined handler, C{False} otherwise.
        """
        self.__cleanup_module(event)
        return True

    def _notify_exit_thread(self, event):
        """
        Notify the termination of a thread.

        @type  event: L{ExitThreadEvent}
        @param event: Exit thread event.

        @rtype:  bool
        @return: C{True} to call the user-defined handler, C{False} otherwise.
        """
        self.__cleanup_thread(event)
        return True

    def _notify_exit_process(self, event):
        """
        Notify the termination of a process.

        @type  event: L{ExitProcessEvent}
        @param event: Exit process event.

        @rtype:  bool
        @return: C{True} to call the user-defined handler, C{False} otherwise.
        """
        self.__cleanup_process(event)
        self.__cleanup_thread(event)
        return True

    # ------------------------------------------------------------------------------

    # This is the high level breakpoint interface. Here we don't have to care
    # about defining or enabling breakpoints, and many errors are ignored
    # (like for example setting the same breakpoint twice, here the second
    # breakpoint replaces the first, much like in WinDBG). It should be easier
    # and more intuitive, if less detailed. It also allows the use of deferred
    # breakpoints.

    # ------------------------------------------------------------------------------

    # Code breakpoints

    def __set_break(self, pid, address, action, oneshot):
        """
        Used by L{break_at} and L{stalk_at}.

        @type  pid: int
        @param pid: Process global ID.

        @type  address: int or str
        @param address:
            Memory address of code instruction to break at. It can be an
            integer value for the actual address or a string with a label
            to be resolved.

        @type  action: function
        @param action: (Optional) Action callback function.

            See L{define_code_breakpoint} for more details.

        @type  oneshot: bool
        @param oneshot: C{True} for one-shot breakpoints, C{False} otherwise.

        @rtype:  L{Breakpoint}
        @return: Returns the new L{Breakpoint} object, or C{None} if the label
            couldn't be resolved and the breakpoint was deferred. Deferred
            breakpoints are set when the DLL they point to is loaded.
        """
        if type(address) not in (int, long):
            label = address
            try:
                address = self.system.get_process(pid).resolve_label(address)
                if not address:
                    raise Exception()
            except Exception:
                try:
                    deferred = self.__deferredBP[pid]
                except KeyError:
                    deferred = dict()
                    self.__deferredBP[pid] = deferred
                if label in deferred:
                    msg = "Redefined deferred code breakpoint at %s in process ID %d"
                    msg = msg % (label, pid)
                    warnings.warn(msg, BreakpointWarning)
                deferred[label] = (action, oneshot)
                return None
        if self.has_code_breakpoint(pid, address):
            bp = self.get_code_breakpoint(pid, address)
            if bp.get_action() != action:  # can't use "is not", fails for bound methods
                bp.set_action(action)
                msg = "Redefined code breakpoint at %s in process ID %d"
                msg = msg % (label, pid)
                warnings.warn(msg, BreakpointWarning)
        else:
            self.define_code_breakpoint(pid, address, True, action)
            bp = self.get_code_breakpoint(pid, address)
        if oneshot:
            if not bp.is_one_shot():
                self.enable_one_shot_code_breakpoint(pid, address)
        else:
            if not bp.is_enabled():
                self.enable_code_breakpoint(pid, address)
        return bp

    def __clear_break(self, pid, address):
        """
        Used by L{dont_break_at} and L{dont_stalk_at}.

        @type  pid: int
        @param pid: Process global ID.

        @type  address: int or str
        @param address:
            Memory address of code instruction to break at. It can be an
            integer value for the actual address or a string with a label
            to be resolved.
        """
        if type(address) not in (int, long):
            unknown = True
            label = address
            try:
                deferred = self.__deferredBP[pid]
                del deferred[label]
                unknown = False
            except KeyError:
                ##                traceback.print_last()      # XXX DEBUG
                pass
            aProcess = self.system.get_process(pid)
            try:
                address = aProcess.resolve_label(label)
                if not address:
                    raise Exception()
            except Exception:
                ##                traceback.print_last()      # XXX DEBUG
                if unknown:
                    msg = "Can't clear unknown code breakpoint" " at %s in process ID %d"
                    msg = msg % (label, pid)
                    warnings.warn(msg, BreakpointWarning)
                return
        if self.has_code_breakpoint(pid, address):
            self.erase_code_breakpoint(pid, address)

    def __set_deferred_breakpoints(self, event):
        """
        Used internally. Sets all deferred breakpoints for a DLL when it's
        loaded.

        @type  event: L{LoadDLLEvent}
        @param event: Load DLL event.
        """
        pid = event.get_pid()
        try:
            deferred = self.__deferredBP[pid]
        except KeyError:
            return
        aProcess = event.get_process()
        for label, (action, oneshot) in deferred.items():
            try:
                address = aProcess.resolve_label(label)
            except Exception:
                continue
            del deferred[label]
            try:
                self.__set_break(pid, address, action, oneshot)
            except Exception:
                msg = "Can't set deferred breakpoint %s at process ID %d"
                msg = msg % (label, pid)
                warnings.warn(msg, BreakpointWarning)

    def get_all_deferred_code_breakpoints(self):
        """
        Returns a list of deferred code breakpoints.

        @rtype:  tuple of (int, str, callable, bool)
        @return: Tuple containing the following elements:
             - Process ID where to set the breakpoint.
             - Label pointing to the address where to set the breakpoint.
             - Action callback for the breakpoint.
             - C{True} of the breakpoint is one-shot, C{False} otherwise.
        """
        result = []
        for pid, deferred in compat.iteritems(self.__deferredBP):
            for label, (action, oneshot) in compat.iteritems(deferred):
                result.add((pid, label, action, oneshot))
        return result

    def get_process_deferred_code_breakpoints(self, dwProcessId):
        """
        Returns a list of deferred code breakpoints.

        @type  dwProcessId: int
        @param dwProcessId: Process ID.

        @rtype:  tuple of (int, str, callable, bool)
        @return: Tuple containing the following elements:
             - Label pointing to the address where to set the breakpoint.
             - Action callback for the breakpoint.
             - C{True} of the breakpoint is one-shot, C{False} otherwise.
        """
        return [(label, action, oneshot) for (label, (action, oneshot)) in compat.iteritems(self.__deferredBP.get(dwProcessId, {}))]

    def stalk_at(self, pid, address, action=None):
        """
        Sets a one shot code breakpoint at the given process and address.

        If instead of an address you pass a label, the breakpoint may be
        deferred until the DLL it points to is loaded.

        @see: L{break_at}, L{dont_stalk_at}

        @type  pid: int
        @param pid: Process global ID.

        @type  address: int or str
        @param address:
            Memory address of code instruction to break at. It can be an
            integer value for the actual address or a string with a label
            to be resolved.

        @type  action: function
        @param action: (Optional) Action callback function.

            See L{define_code_breakpoint} for more details.

        @rtype:  bool
        @return: C{True} if the breakpoint was set immediately, or C{False} if
            it was deferred.
        """
        bp = self.__set_break(pid, address, action, oneshot=True)
        return bp is not None

    def break_at(self, pid, address, action=None):
        """
        Sets a code breakpoint at the given process and address.

        If instead of an address you pass a label, the breakpoint may be
        deferred until the DLL it points to is loaded.

        @see: L{stalk_at}, L{dont_break_at}

        @type  pid: int
        @param pid: Process global ID.

        @type  address: int or str
        @param address:
            Memory address of code instruction to break at. It can be an
            integer value for the actual address or a string with a label
            to be resolved.

        @type  action: function
        @param action: (Optional) Action callback function.

            See L{define_code_breakpoint} for more details.

        @rtype:  bool
        @return: C{True} if the breakpoint was set immediately, or C{False} if
            it was deferred.
        """
        bp = self.__set_break(pid, address, action, oneshot=False)
        return bp is not None

    def dont_break_at(self, pid, address):
        """
        Clears a code breakpoint set by L{break_at}.

        @type  pid: int
        @param pid: Process global ID.

        @type  address: int or str
        @param address:
            Memory address of code instruction to break at. It can be an
            integer value for the actual address or a string with a label
            to be resolved.
        """
        self.__clear_break(pid, address)

    def dont_stalk_at(self, pid, address):
        """
        Clears a code breakpoint set by L{stalk_at}.

        @type  pid: int
        @param pid: Process global ID.

        @type  address: int or str
        @param address:
            Memory address of code instruction to break at. It can be an
            integer value for the actual address or a string with a label
            to be resolved.
        """
        self.__clear_break(pid, address)

    # ------------------------------------------------------------------------------

    # Function hooks

    def hook_function(self, pid, address, preCB=None, postCB=None, paramCount=None, signature=None):
        """
        Sets a function hook at the given address.

        If instead of an address you pass a label, the hook may be
        deferred until the DLL it points to is loaded.

        @type  pid: int
        @param pid: Process global ID.

        @type  address: int or str
        @param address:
            Memory address of code instruction to break at. It can be an
            integer value for the actual address or a string with a label
            to be resolved.

        @type  preCB: function
        @param preCB: (Optional) Callback triggered on function entry.

            The signature for the callback should be something like this::

                def pre_LoadLibraryEx(event, ra, lpFilename, hFile, dwFlags):

                    # return address
                    ra = params[0]

                    # function arguments start from here...
                    szFilename = event.get_process().peek_string(lpFilename)

                    # (...)

            Note that all pointer types are treated like void pointers, so your
            callback won't get the string or structure pointed to by it, but
            the remote memory address instead. This is so to prevent the ctypes
            library from being "too helpful" and trying to dereference the
            pointer. To get the actual data being pointed to, use one of the
            L{Process.read} methods.

        @type  postCB: function
        @param postCB: (Optional) Callback triggered on function exit.

            The signature for the callback should be something like this::

                def post_LoadLibraryEx(event, return_value):

                    # (...)

        @type  paramCount: int
        @param paramCount:
            (Optional) Number of parameters for the C{preCB} callback,
            not counting the return address. Parameters are read from
            the stack and assumed to be DWORDs in 32 bits and QWORDs in 64.

            This is a faster way to pull stack parameters in 32 bits, but in 64
            bits (or with some odd APIs in 32 bits) it won't be useful, since
            not all arguments to the hooked function will be of the same size.

            For a more reliable and cross-platform way of hooking use the
            C{signature} argument instead.

        @type  signature: tuple
        @param signature:
            (Optional) Tuple of C{ctypes} data types that constitute the
            hooked function signature. When the function is called, this will
            be used to parse the arguments from the stack. Overrides the
            C{paramCount} argument.

        @rtype:  bool
        @return: C{True} if the hook was set immediately, or C{False} if
            it was deferred.
        """
        try:
            aProcess = self.system.get_process(pid)
        except KeyError:
            aProcess = Process(pid)
        arch = aProcess.get_arch()
        hookObj = Hook(preCB, postCB, paramCount, signature, arch)
        bp = self.break_at(pid, address, hookObj)
        return bp is not None

    def stalk_function(self, pid, address, preCB=None, postCB=None, paramCount=None, signature=None):
        """
        Sets a one-shot function hook at the given address.

        If instead of an address you pass a label, the hook may be
        deferred until the DLL it points to is loaded.

        @type  pid: int
        @param pid: Process global ID.

        @type  address: int or str
        @param address:
            Memory address of code instruction to break at. It can be an
            integer value for the actual address or a string with a label
            to be resolved.

        @type  preCB: function
        @param preCB: (Optional) Callback triggered on function entry.

            The signature for the callback should be something like this::

                def pre_LoadLibraryEx(event, ra, lpFilename, hFile, dwFlags):

                    # return address
                    ra = params[0]

                    # function arguments start from here...
                    szFilename = event.get_process().peek_string(lpFilename)

                    # (...)

            Note that all pointer types are treated like void pointers, so your
            callback won't get the string or structure pointed to by it, but
            the remote memory address instead. This is so to prevent the ctypes
            library from being "too helpful" and trying to dereference the
            pointer. To get the actual data being pointed to, use one of the
            L{Process.read} methods.

        @type  postCB: function
        @param postCB: (Optional) Callback triggered on function exit.

            The signature for the callback should be something like this::

                def post_LoadLibraryEx(event, return_value):

                    # (...)

        @type  paramCount: int
        @param paramCount:
            (Optional) Number of parameters for the C{preCB} callback,
            not counting the return address. Parameters are read from
            the stack and assumed to be DWORDs in 32 bits and QWORDs in 64.

            This is a faster way to pull stack parameters in 32 bits, but in 64
            bits (or with some odd APIs in 32 bits) it won't be useful, since
            not all arguments to the hooked function will be of the same size.

            For a more reliable and cross-platform way of hooking use the
            C{signature} argument instead.

        @type  signature: tuple
        @param signature:
            (Optional) Tuple of C{ctypes} data types that constitute the
            hooked function signature. When the function is called, this will
            be used to parse the arguments from the stack. Overrides the
            C{paramCount} argument.

        @rtype:  bool
        @return: C{True} if the breakpoint was set immediately, or C{False} if
            it was deferred.
        """
        try:
            aProcess = self.system.get_process(pid)
        except KeyError:
            aProcess = Process(pid)
        arch = aProcess.get_arch()
        hookObj = Hook(preCB, postCB, paramCount, signature, arch)
        bp = self.stalk_at(pid, address, hookObj)
        return bp is not None

    def dont_hook_function(self, pid, address):
        """
        Removes a function hook set by L{hook_function}.

        @type  pid: int
        @param pid: Process global ID.

        @type  address: int or str
        @param address:
            Memory address of code instruction to break at. It can be an
            integer value for the actual address or a string with a label
            to be resolved.
        """
        self.dont_break_at(pid, address)

    # alias
    unhook_function = dont_hook_function

    def dont_stalk_function(self, pid, address):
        """
        Removes a function hook set by L{stalk_function}.

        @type  pid: int
        @param pid: Process global ID.

        @type  address: int or str
        @param address:
            Memory address of code instruction to break at. It can be an
            integer value for the actual address or a string with a label
            to be resolved.
        """
        self.dont_stalk_at(pid, address)

    # ------------------------------------------------------------------------------

    # Variable watches

    def __set_variable_watch(self, tid, address, size, action):
        """
        Used by L{watch_variable} and L{stalk_variable}.

        @type  tid: int
        @param tid: Thread global ID.

        @type  address: int
        @param address: Memory address of variable to watch.

        @type  size: int
        @param size: Size of variable to watch. The only supported sizes are:
            byte (1), word (2), dword (4) and qword (8).

        @type  action: function
        @param action: (Optional) Action callback function.

            See L{define_hardware_breakpoint} for more details.

        @rtype:  L{HardwareBreakpoint}
        @return: Hardware breakpoint at the requested address.
        """

        # TODO
        # We should merge the breakpoints instead of overwriting them.
        # We'll have the same problem as watch_buffer and we'll need to change
        # the API again.

        if size == 1:
            sizeFlag = self.BP_WATCH_BYTE
        elif size == 2:
            sizeFlag = self.BP_WATCH_WORD
        elif size == 4:
            sizeFlag = self.BP_WATCH_DWORD
        elif size == 8:
            sizeFlag = self.BP_WATCH_QWORD
        else:
            raise ValueError("Bad size for variable watch: %r" % size)

        if self.has_hardware_breakpoint(tid, address):
            warnings.warn(
                "Hardware breakpoint in thread %d at address %s was overwritten!"
                % (tid, HexDump.address(address, self.system.get_thread(tid).get_bits())),
                BreakpointWarning,
            )

            bp = self.get_hardware_breakpoint(tid, address)
            if bp.get_trigger() != self.BP_BREAK_ON_ACCESS or bp.get_watch() != sizeFlag:
                self.erase_hardware_breakpoint(tid, address)
                self.define_hardware_breakpoint(tid, address, self.BP_BREAK_ON_ACCESS, sizeFlag, True, action)
                bp = self.get_hardware_breakpoint(tid, address)

        else:
            self.define_hardware_breakpoint(tid, address, self.BP_BREAK_ON_ACCESS, sizeFlag, True, action)
            bp = self.get_hardware_breakpoint(tid, address)

        return bp

    def __clear_variable_watch(self, tid, address):
        """
        Used by L{dont_watch_variable} and L{dont_stalk_variable}.

        @type  tid: int
        @param tid: Thread global ID.

        @type  address: int
        @param address: Memory address of variable to stop watching.
        """
        if self.has_hardware_breakpoint(tid, address):
            self.erase_hardware_breakpoint(tid, address)

    def watch_variable(self, tid, address, size, action=None):
        """
        Sets a hardware breakpoint at the given thread, address and size.

        @see: L{dont_watch_variable}

        @type  tid: int
        @param tid: Thread global ID.

        @type  address: int
        @param address: Memory address of variable to watch.

        @type  size: int
        @param size: Size of variable to watch. The only supported sizes are:
            byte (1), word (2), dword (4) and qword (8).

        @type  action: function
        @param action: (Optional) Action callback function.

            See L{define_hardware_breakpoint} for more details.
        """
        bp = self.__set_variable_watch(tid, address, size, action)
        if not bp.is_enabled():
            self.enable_hardware_breakpoint(tid, address)

    def stalk_variable(self, tid, address, size, action=None):
        """
        Sets a one-shot hardware breakpoint at the given thread,
        address and size.

        @see: L{dont_watch_variable}

        @type  tid: int
        @param tid: Thread global ID.

        @type  address: int
        @param address: Memory address of variable to watch.

        @type  size: int
        @param size: Size of variable to watch. The only supported sizes are:
            byte (1), word (2), dword (4) and qword (8).

        @type  action: function
        @param action: (Optional) Action callback function.

            See L{define_hardware_breakpoint} for more details.
        """
        bp = self.__set_variable_watch(tid, address, size, action)
        if not bp.is_one_shot():
            self.enable_one_shot_hardware_breakpoint(tid, address)

    def dont_watch_variable(self, tid, address):
        """
        Clears a hardware breakpoint set by L{watch_variable}.

        @type  tid: int
        @param tid: Thread global ID.

        @type  address: int
        @param address: Memory address of variable to stop watching.
        """
        self.__clear_variable_watch(tid, address)

    def dont_stalk_variable(self, tid, address):
        """
        Clears a hardware breakpoint set by L{stalk_variable}.

        @type  tid: int
        @param tid: Thread global ID.

        @type  address: int
        @param address: Memory address of variable to stop watching.
        """
        self.__clear_variable_watch(tid, address)

    # ------------------------------------------------------------------------------

    # Buffer watches

    def __set_buffer_watch(self, pid, address, size, action, bOneShot):
        """
        Used by L{watch_buffer} and L{stalk_buffer}.

        @type  pid: int
        @param pid: Process global ID.

        @type  address: int
        @param address: Memory address of buffer to watch.

        @type  size: int
        @param size: Size in bytes of buffer to watch.

        @type  action: function
        @param action: (Optional) Action callback function.

            See L{define_page_breakpoint} for more details.

        @type  bOneShot: bool
        @param bOneShot:
            C{True} to set a one-shot breakpoint,
            C{False} to set a normal breakpoint.
        """

        # Check the size isn't zero or negative.
        if size < 1:
            raise ValueError("Bad size for buffer watch: %r" % size)

        # Create the buffer watch identifier.
        bw = BufferWatch(pid, address, address + size, action, bOneShot)

        # Get the base address and size in pages required for this buffer.
        base = MemoryAddresses.align_address_to_page_start(address)
        limit = MemoryAddresses.align_address_to_page_end(address + size)
        pages = MemoryAddresses.get_buffer_size_in_pages(address, size)

        try:
            # For each page:
            #  + if a page breakpoint exists reuse it
            #  + if it doesn't exist define it

            bset = set()  # all breakpoints used
            nset = set()  # newly defined breakpoints
            cset = set()  # condition objects

            page_addr = base
            pageSize = MemoryAddresses.pageSize
            while page_addr < limit:
                # If a breakpoints exists, reuse it.
                if self.has_page_breakpoint(pid, page_addr):
                    bp = self.get_page_breakpoint(pid, page_addr)
                    if bp not in bset:
                        condition = bp.get_condition()
                        if not condition in cset:
                            if not isinstance(condition, _BufferWatchCondition):
                                # this shouldn't happen unless you tinkered
                                # with it or defined your own page breakpoints
                                # manually.
                                msg = "Can't watch buffer at page %s"
                                msg = msg % HexDump.address(page_addr)
                                raise RuntimeError(msg)
                            cset.add(condition)
                        bset.add(bp)

                # If it doesn't, define it.
                else:
                    condition = _BufferWatchCondition()
                    bp = self.define_page_breakpoint(pid, page_addr, 1, condition=condition)
                    bset.add(bp)
                    nset.add(bp)
                    cset.add(condition)

                # Next page.
                page_addr = page_addr + pageSize

            # For each breakpoint, enable it if needed.
            aProcess = self.system.get_process(pid)
            for bp in bset:
                if bp.is_disabled() or bp.is_one_shot():
                    bp.enable(aProcess, None)

        # On error...
        except:
            # Erase the newly defined breakpoints.
            for bp in nset:
                try:
                    self.erase_page_breakpoint(pid, bp.get_address())
                except:
                    pass

            # Pass the exception to the caller
            raise

        # For each condition object, add the new buffer.
        for condition in cset:
            condition.add(bw)

    def __clear_buffer_watch_old_method(self, pid, address, size):
        """
        Used by L{dont_watch_buffer} and L{dont_stalk_buffer}.

        @warn: Deprecated since WinAppDbg 1.5.

        @type  pid: int
        @param pid: Process global ID.

        @type  address: int
        @param address: Memory address of buffer to stop watching.

        @type  size: int
        @param size: Size in bytes of buffer to stop watching.
        """
        warnings.warn("Deprecated since WinAppDbg 1.5", DeprecationWarning)

        # Check the size isn't zero or negative.
        if size < 1:
            raise ValueError("Bad size for buffer watch: %r" % size)

        # Get the base address and size in pages required for this buffer.
        base = MemoryAddresses.align_address_to_page_start(address)
        limit = MemoryAddresses.align_address_to_page_end(address + size)
        pages = MemoryAddresses.get_buffer_size_in_pages(address, size)

        # For each page, get the breakpoint and it's condition object.
        # For each condition, remove the buffer.
        # For each breakpoint, if no buffers are on watch, erase it.
        cset = set()  # condition objects
        page_addr = base
        pageSize = MemoryAddresses.pageSize
        while page_addr < limit:
            if self.has_page_breakpoint(pid, page_addr):
                bp = self.get_page_breakpoint(pid, page_addr)
                condition = bp.get_condition()
                if condition not in cset:
                    if not isinstance(condition, _BufferWatchCondition):
                        # this shouldn't happen unless you tinkered with it
                        # or defined your own page breakpoints manually.
                        continue
                    cset.add(condition)
                    condition.remove_last_match(address, size)
                    if condition.count() == 0:
                        try:
                            self.erase_page_breakpoint(pid, bp.get_address())
                        except WindowsError:
                            pass
            page_addr = page_addr + pageSize

    def __clear_buffer_watch(self, bw):
        """
        Used by L{dont_watch_buffer} and L{dont_stalk_buffer}.

        @type  bw: L{BufferWatch}
        @param bw: Buffer watch identifier.
        """

        # Get the PID and the start and end addresses of the buffer.
        pid = bw.pid
        start = bw.start
        end = bw.end

        # Get the base address and size in pages required for the buffer.
        base = MemoryAddresses.align_address_to_page_start(start)
        limit = MemoryAddresses.align_address_to_page_end(end)
        pages = MemoryAddresses.get_buffer_size_in_pages(start, end - start)

        # For each page, get the breakpoint and it's condition object.
        # For each condition, remove the buffer.
        # For each breakpoint, if no buffers are on watch, erase it.
        cset = set()  # condition objects
        page_addr = base
        pageSize = MemoryAddresses.pageSize
        while page_addr < limit:
            if self.has_page_breakpoint(pid, page_addr):
                bp = self.get_page_breakpoint(pid, page_addr)
                condition = bp.get_condition()
                if condition not in cset:
                    if not isinstance(condition, _BufferWatchCondition):
                        # this shouldn't happen unless you tinkered with it
                        # or defined your own page breakpoints manually.
                        continue
                    cset.add(condition)
                    condition.remove(bw)
                    if condition.count() == 0:
                        try:
                            self.erase_page_breakpoint(pid, bp.get_address())
                        except WindowsError:
                            msg = "Cannot remove page breakpoint at address %s"
                            msg = msg % HexDump.address(bp.get_address())
                            warnings.warn(msg, BreakpointWarning)
            page_addr = page_addr + pageSize

    def watch_buffer(self, pid, address, size, action=None):
        """
        Sets a page breakpoint and notifies when the given buffer is accessed.

        @see: L{dont_watch_variable}

        @type  pid: int
        @param pid: Process global ID.

        @type  address: int
        @param address: Memory address of buffer to watch.

        @type  size: int
        @param size: Size in bytes of buffer to watch.

        @type  action: function
        @param action: (Optional) Action callback function.

            See L{define_page_breakpoint} for more details.

        @rtype:  L{BufferWatch}
        @return: Buffer watch identifier.
        """
        self.__set_buffer_watch(pid, address, size, action, False)

    def stalk_buffer(self, pid, address, size, action=None):
        """
        Sets a one-shot page breakpoint and notifies
        when the given buffer is accessed.

        @see: L{dont_watch_variable}

        @type  pid: int
        @param pid: Process global ID.

        @type  address: int
        @param address: Memory address of buffer to watch.

        @type  size: int
        @param size: Size in bytes of buffer to watch.

        @type  action: function
        @param action: (Optional) Action callback function.

            See L{define_page_breakpoint} for more details.

        @rtype:  L{BufferWatch}
        @return: Buffer watch identifier.
        """
        self.__set_buffer_watch(pid, address, size, action, True)

    def dont_watch_buffer(self, bw, *argv, **argd):
        """
        Clears a page breakpoint set by L{watch_buffer}.

        @type  bw: L{BufferWatch}
        @param bw:
            Buffer watch identifier returned by L{watch_buffer}.
        """

        # The sane way to do it.
        if not (argv or argd):
            self.__clear_buffer_watch(bw)

        # Backwards compatibility with WinAppDbg 1.4.
        else:
            argv = list(argv)
            argv.insert(0, bw)
            if "pid" in argd:
                argv.insert(0, argd.pop("pid"))
            if "address" in argd:
                argv.insert(1, argd.pop("address"))
            if "size" in argd:
                argv.insert(2, argd.pop("size"))
            if argd:
                raise TypeError("Wrong arguments for dont_watch_buffer()")
            try:
                pid, address, size = argv
            except ValueError:
                raise TypeError("Wrong arguments for dont_watch_buffer()")
            self.__clear_buffer_watch_old_method(pid, address, size)

    def dont_stalk_buffer(self, bw, *argv, **argd):
        """
        Clears a page breakpoint set by L{stalk_buffer}.

        @type  bw: L{BufferWatch}
        @param bw:
            Buffer watch identifier returned by L{stalk_buffer}.
        """
        self.dont_watch_buffer(bw, *argv, **argd)

    # ------------------------------------------------------------------------------

    # Tracing

    # XXX TODO
    # Add "action" parameter to tracing mode

    def __start_tracing(self, thread):
        """
        @type  thread: L{Thread}
        @param thread: Thread to start tracing.
        """
        tid = thread.get_tid()
        if not tid in self.__tracing:
            thread.set_tf()
            self.__tracing.add(tid)

    def __stop_tracing(self, thread):
        """
        @type  thread: L{Thread}
        @param thread: Thread to stop tracing.
        """
        tid = thread.get_tid()
        if tid in self.__tracing:
            self.__tracing.remove(tid)
            if thread.is_alive():
                thread.clear_tf()

    def is_tracing(self, tid):
        """
        @type  tid: int
        @param tid: Thread global ID.

        @rtype:  bool
        @return: C{True} if the thread is being traced, C{False} otherwise.
        """
        return tid in self.__tracing

    def get_traced_tids(self):
        """
        Retrieves the list of global IDs of all threads being traced.

        @rtype:  list( int... )
        @return: List of thread global IDs.
        """
        tids = list(self.__tracing)
        tids.sort()
        return tids

    def start_tracing(self, tid):
        """
        Start tracing mode in the given thread.

        @type  tid: int
        @param tid: Global ID of thread to start tracing.
        """
        if not self.is_tracing(tid):
            thread = self.system.get_thread(tid)
            self.__start_tracing(thread)

    def stop_tracing(self, tid):
        """
        Stop tracing mode in the given thread.

        @type  tid: int
        @param tid: Global ID of thread to stop tracing.
        """
        if self.is_tracing(tid):
            thread = self.system.get_thread(tid)
            self.__stop_tracing(thread)

    def start_tracing_process(self, pid):
        """
        Start tracing mode for all threads in the given process.

        @type  pid: int
        @param pid: Global ID of process to start tracing.
        """
        for thread in self.system.get_process(pid).iter_threads():
            self.__start_tracing(thread)

    def stop_tracing_process(self, pid):
        """
        Stop tracing mode for all threads in the given process.

        @type  pid: int
        @param pid: Global ID of process to stop tracing.
        """
        for thread in self.system.get_process(pid).iter_threads():
            self.__stop_tracing(thread)

    def start_tracing_all(self):
        """
        Start tracing mode for all threads in all debugees.
        """
        for pid in self.get_debugee_pids():
            self.start_tracing_process(pid)

    def stop_tracing_all(self):
        """
        Stop tracing mode for all threads in all debugees.
        """
        for pid in self.get_debugee_pids():
            self.stop_tracing_process(pid)

    # ------------------------------------------------------------------------------

    # Break on LastError values (only available since Windows Server 2003)

    def break_on_error(self, pid, errorCode):
        """
        Sets or clears the system breakpoint for a given Win32 error code.

        Use L{Process.is_system_defined_breakpoint} to tell if a breakpoint
        exception was caused by a system breakpoint or by the application
        itself (for example because of a failed assertion in the code).

        @note: This functionality is only available since Windows Server 2003.
            In 2003 it only breaks on error values set externally to the
            kernel32.dll library, but this was fixed in Windows Vista.

        @warn: This method will fail if the debug symbols for ntdll (kernel32
            in Windows 2003) are not present. For more information see:
            L{System.fix_symbol_store_path}.

        @see: U{http://www.nynaeve.net/?p=147}

        @type  pid: int
        @param pid: Process ID.

        @type  errorCode: int
        @param errorCode: Win32 error code to stop on. Set to C{0} or
            C{ERROR_SUCCESS} to clear the breakpoint instead.

        @raise NotImplementedError:
            The functionality is not supported in this system.

        @raise WindowsError:
            An error occurred while processing this request.
        """
        aProcess = self.system.get_process(pid)
        address = aProcess.get_break_on_error_ptr()
        if not address:
            raise NotImplementedError("The functionality is not supported in this system.")
        aProcess.write_dword(address, errorCode)

    def dont_break_on_error(self, pid):
        """
        Alias to L{break_on_error}C{(pid, ERROR_SUCCESS)}.

        @type  pid: int
        @param pid: Process ID.

        @raise NotImplementedError:
            The functionality is not supported in this system.

        @raise WindowsError:
            An error occurred while processing this request.
        """
        self.break_on_error(pid, 0)

    # ------------------------------------------------------------------------------

    # Simplified symbol resolving, useful for hooking functions

    def resolve_exported_function(self, pid, modName, procName):
        """
        Resolves the exported DLL function for the given process.

        @type  pid: int
        @param pid: Process global ID.

        @type  modName: str
        @param modName: Name of the module that exports the function.

        @type  procName: str
        @param procName: Name of the exported function to resolve.

        @rtype:  int, None
        @return: On success, the address of the exported function.
            On failure, returns C{None}.
        """
        aProcess = self.system.get_process(pid)
        aModule = aProcess.get_module_by_name(modName)
        if not aModule:
            aProcess.scan_modules()
            aModule = aProcess.get_module_by_name(modName)
        if aModule:
            address = aModule.resolve(procName)
            return address
        return None

    def resolve_label(self, pid, label):
        """
        Resolves a label for the given process.

        @type  pid: int
        @param pid: Process global ID.

        @type  label: str
        @param label: Label to resolve.

        @rtype:  int
        @return: Memory address pointed to by the label.

        @raise ValueError: The label is malformed or impossible to resolve.
        @raise RuntimeError: Cannot resolve the module or function.
        """
        return self.get_process(pid).resolve_label(label)

# === NexusCore/openenv\Lib\site-packages\matplotlib\patches.py ===
r"""
Patches are `.Artist`\s with a face color and an edge color.
"""

import functools
import inspect
import math
from numbers import Number, Real
import textwrap
from types import SimpleNamespace
from collections import namedtuple
from matplotlib.transforms import Affine2D

import numpy as np

import matplotlib as mpl
from . import (_api, artist, cbook, colors, _docstring, hatch as mhatch,
               lines as mlines, transforms)
from .bezier import (
    NonIntersectingPathException, get_cos_sin, get_intersection,
    get_parallels, inside_circle, make_wedged_bezier2,
    split_bezier_intersecting_with_closedpath, split_path_inout)
from .path import Path
from ._enums import JoinStyle, CapStyle


@_docstring.interpd
@_api.define_aliases({
    "antialiased": ["aa"],
    "edgecolor": ["ec"],
    "facecolor": ["fc"],
    "linestyle": ["ls"],
    "linewidth": ["lw"],
})
class Patch(artist.Artist):
    """
    A patch is a 2D artist with a face color and an edge color.

    If any of *edgecolor*, *facecolor*, *linewidth*, or *antialiased*
    are *None*, they default to their rc params setting.
    """
    zorder = 1

    # Whether to draw an edge by default.  Set on a
    # subclass-by-subclass basis.
    _edge_default = False

    def __init__(self, *,
                 edgecolor=None,
                 facecolor=None,
                 color=None,
                 linewidth=None,
                 linestyle=None,
                 antialiased=None,
                 hatch=None,
                 fill=True,
                 capstyle=None,
                 joinstyle=None,
                 **kwargs):
        """
        The following kwarg properties are supported

        %(Patch:kwdoc)s
        """
        super().__init__()

        if linestyle is None:
            linestyle = "solid"
        if capstyle is None:
            capstyle = CapStyle.butt
        if joinstyle is None:
            joinstyle = JoinStyle.miter

        self._hatch_color = colors.to_rgba(mpl.rcParams['hatch.color'])
        self._hatch_linewidth = mpl.rcParams['hatch.linewidth']
        self._fill = bool(fill)  # needed for set_facecolor call
        if color is not None:
            if edgecolor is not None or facecolor is not None:
                _api.warn_external(
                    "Setting the 'color' property will override "
                    "the edgecolor or facecolor properties.")
            self.set_color(color)
        else:
            self.set_edgecolor(edgecolor)
            self.set_facecolor(facecolor)

        self._linewidth = 0
        self._unscaled_dash_pattern = (0, None)  # offset, dash
        self._dash_pattern = (0, None)  # offset, dash (scaled by linewidth)

        self.set_linestyle(linestyle)
        self.set_linewidth(linewidth)
        self.set_antialiased(antialiased)
        self.set_hatch(hatch)
        self.set_capstyle(capstyle)
        self.set_joinstyle(joinstyle)

        if len(kwargs):
            self._internal_update(kwargs)

    def get_verts(self):
        """
        Return a copy of the vertices used in this patch.

        If the patch contains Bézier curves, the curves will be interpolated by
        line segments.  To access the curves as curves, use `get_path`.
        """
        trans = self.get_transform()
        path = self.get_path()
        polygons = path.to_polygons(trans)
        if len(polygons):
            return polygons[0]
        return []

    def _process_radius(self, radius):
        if radius is not None:
            return radius
        if isinstance(self._picker, Number):
            _radius = self._picker
        else:
            if self.get_edgecolor()[3] == 0:
                _radius = 0
            else:
                _radius = self.get_linewidth()
        return _radius

    def contains(self, mouseevent, radius=None):
        """
        Test whether the mouse event occurred in the patch.

        Parameters
        ----------
        mouseevent : `~matplotlib.backend_bases.MouseEvent`
            Where the user clicked.

        radius : float, optional
            Additional margin on the patch in target coordinates of
            `.Patch.get_transform`. See `.Path.contains_point` for further
            details.

            If `None`, the default value depends on the state of the object:

            - If `.Artist.get_picker` is a number, the default
              is that value.  This is so that picking works as expected.
            - Otherwise if the edge color has a non-zero alpha, the default
              is half of the linewidth.  This is so that all the colored
              pixels are "in" the patch.
            - Finally, if the edge has 0 alpha, the default is 0.  This is
              so that patches without a stroked edge do not have points
              outside of the filled region report as "in" due to an
              invisible edge.


        Returns
        -------
        (bool, empty dict)
        """
        if self._different_canvas(mouseevent):
            return False, {}
        radius = self._process_radius(radius)
        codes = self.get_path().codes
        if codes is not None:
            vertices = self.get_path().vertices
            # if the current path is concatenated by multiple sub paths.
            # get the indexes of the starting code(MOVETO) of all sub paths
            idxs, = np.where(codes == Path.MOVETO)
            # Don't split before the first MOVETO.
            idxs = idxs[1:]
            subpaths = map(
                Path, np.split(vertices, idxs), np.split(codes, idxs))
        else:
            subpaths = [self.get_path()]
        inside = any(
            subpath.contains_point(
                (mouseevent.x, mouseevent.y), self.get_transform(), radius)
            for subpath in subpaths)
        return inside, {}

    def contains_point(self, point, radius=None):
        """
        Return whether the given point is inside the patch.

        Parameters
        ----------
        point : (float, float)
            The point (x, y) to check, in target coordinates of
            ``.Patch.get_transform()``. These are display coordinates for patches
            that are added to a figure or Axes.
        radius : float, optional
            Additional margin on the patch in target coordinates of
            `.Patch.get_transform`. See `.Path.contains_point` for further
            details.

            If `None`, the default value depends on the state of the object:

            - If `.Artist.get_picker` is a number, the default
              is that value.  This is so that picking works as expected.
            - Otherwise if the edge color has a non-zero alpha, the default
              is half of the linewidth.  This is so that all the colored
              pixels are "in" the patch.
            - Finally, if the edge has 0 alpha, the default is 0.  This is
              so that patches without a stroked edge do not have points
              outside of the filled region report as "in" due to an
              invisible edge.

        Returns
        -------
        bool

        Notes
        -----
        The proper use of this method depends on the transform of the patch.
        Isolated patches do not have a transform. In this case, the patch
        creation coordinates and the point coordinates match. The following
        example checks that the center of a circle is within the circle

        >>> center = 0, 0
        >>> c = Circle(center, radius=1)
        >>> c.contains_point(center)
        True

        The convention of checking against the transformed patch stems from
        the fact that this method is predominantly used to check if display
        coordinates (e.g. from mouse events) are within the patch. If you want
        to do the above check with data coordinates, you have to properly
        transform them first:

        >>> center = 0, 0
        >>> c = Circle(center, radius=3)
        >>> plt.gca().add_patch(c)
        >>> transformed_interior_point = c.get_data_transform().transform((0, 2))
        >>> c.contains_point(transformed_interior_point)
        True

        """
        radius = self._process_radius(radius)
        return self.get_path().contains_point(point,
                                              self.get_transform(),
                                              radius)

    def contains_points(self, points, radius=None):
        """
        Return whether the given points are inside the patch.

        Parameters
        ----------
        points : (N, 2) array
            The points to check, in target coordinates of
            ``self.get_transform()``. These are display coordinates for patches
            that are added to a figure or Axes. Columns contain x and y values.
        radius : float, optional
            Additional margin on the patch in target coordinates of
            `.Patch.get_transform`. See `.Path.contains_point` for further
            details.

            If `None`, the default value depends on the state of the object:

            - If `.Artist.get_picker` is a number, the default
              is that value.  This is so that picking works as expected.
            - Otherwise if the edge color has a non-zero alpha, the default
              is half of the linewidth.  This is so that all the colored
              pixels are "in" the patch.
            - Finally, if the edge has 0 alpha, the default is 0.  This is
              so that patches without a stroked edge do not have points
              outside of the filled region report as "in" due to an
              invisible edge.

        Returns
        -------
        length-N bool array

        Notes
        -----
        The proper use of this method depends on the transform of the patch.
        See the notes on `.Patch.contains_point`.
        """
        radius = self._process_radius(radius)
        return self.get_path().contains_points(points,
                                               self.get_transform(),
                                               radius)

    def update_from(self, other):
        # docstring inherited.
        super().update_from(other)
        # For some properties we don't need or don't want to go through the
        # getters/setters, so we just copy them directly.
        self._edgecolor = other._edgecolor
        self._facecolor = other._facecolor
        self._original_edgecolor = other._original_edgecolor
        self._original_facecolor = other._original_facecolor
        self._fill = other._fill
        self._hatch = other._hatch
        self._hatch_color = other._hatch_color
        self._unscaled_dash_pattern = other._unscaled_dash_pattern
        self.set_linewidth(other._linewidth)  # also sets scaled dashes
        self.set_transform(other.get_data_transform())
        # If the transform of other needs further initialization, then it will
        # be the case for this artist too.
        self._transformSet = other.is_transform_set()

    def get_extents(self):
        """
        Return the `Patch`'s axis-aligned extents as a `~.transforms.Bbox`.
        """
        return self.get_path().get_extents(self.get_transform())

    def get_transform(self):
        """Return the `~.transforms.Transform` applied to the `Patch`."""
        return self.get_patch_transform() + artist.Artist.get_transform(self)

    def get_data_transform(self):
        """
        Return the `~.transforms.Transform` mapping data coordinates to
        physical coordinates.
        """
        return artist.Artist.get_transform(self)

    def get_patch_transform(self):
        """
        Return the `~.transforms.Transform` instance mapping patch coordinates
        to data coordinates.

        For example, one may define a patch of a circle which represents a
        radius of 5 by providing coordinates for a unit circle, and a
        transform which scales the coordinates (the patch coordinate) by 5.
        """
        return transforms.IdentityTransform()

    def get_antialiased(self):
        """Return whether antialiasing is used for drawing."""
        return self._antialiased

    def get_edgecolor(self):
        """Return the edge color."""
        return self._edgecolor

    def get_facecolor(self):
        """Return the face color."""
        return self._facecolor

    def get_linewidth(self):
        """Return the line width in points."""
        return self._linewidth

    def get_linestyle(self):
        """Return the linestyle."""
        return self._linestyle

    def set_antialiased(self, aa):
        """
        Set whether to use antialiased rendering.

        Parameters
        ----------
        aa : bool or None
        """
        if aa is None:
            aa = mpl.rcParams['patch.antialiased']
        self._antialiased = aa
        self.stale = True

    def _set_edgecolor(self, color):
        set_hatch_color = True
        if color is None:
            if (mpl.rcParams['patch.force_edgecolor'] or
                    not self._fill or self._edge_default):
                color = mpl.rcParams['patch.edgecolor']
            else:
                color = 'none'
                set_hatch_color = False

        self._edgecolor = colors.to_rgba(color, self._alpha)
        if set_hatch_color:
            self._hatch_color = self._edgecolor
        self.stale = True

    def set_edgecolor(self, color):
        """
        Set the patch edge color.

        Parameters
        ----------
        color : :mpltype:`color` or None
        """
        self._original_edgecolor = color
        self._set_edgecolor(color)

    def _set_facecolor(self, color):
        if color is None:
            color = mpl.rcParams['patch.facecolor']
        alpha = self._alpha if self._fill else 0
        self._facecolor = colors.to_rgba(color, alpha)
        self.stale = True

    def set_facecolor(self, color):
        """
        Set the patch face color.

        Parameters
        ----------
        color : :mpltype:`color` or None
        """
        self._original_facecolor = color
        self._set_facecolor(color)

    def set_color(self, c):
        """
        Set both the edgecolor and the facecolor.

        Parameters
        ----------
        c : :mpltype:`color`

        See Also
        --------
        Patch.set_facecolor, Patch.set_edgecolor
            For setting the edge or face color individually.
        """
        self.set_facecolor(c)
        self.set_edgecolor(c)

    def set_alpha(self, alpha):
        # docstring inherited
        super().set_alpha(alpha)
        self._set_facecolor(self._original_facecolor)
        self._set_edgecolor(self._original_edgecolor)
        # stale is already True

    def set_linewidth(self, w):
        """
        Set the patch linewidth in points.

        Parameters
        ----------
        w : float or None
        """
        if w is None:
            w = mpl.rcParams['patch.linewidth']
        self._linewidth = float(w)
        self._dash_pattern = mlines._scale_dashes(
            *self._unscaled_dash_pattern, w)
        self.stale = True

    def set_linestyle(self, ls):
        """
        Set the patch linestyle.

        ==========================================  =================
        linestyle                                   description
        ==========================================  =================
        ``'-'`` or ``'solid'``                      solid line
        ``'--'`` or  ``'dashed'``                   dashed line
        ``'-.'`` or  ``'dashdot'``                  dash-dotted line
        ``':'`` or ``'dotted'``                     dotted line
        ``'none'``, ``'None'``, ``' '``, or ``''``  draw nothing
        ==========================================  =================

        Alternatively a dash tuple of the following form can be provided::

            (offset, onoffseq)

        where ``onoffseq`` is an even length tuple of on and off ink in points.

        Parameters
        ----------
        ls : {'-', '--', '-.', ':', '', (offset, on-off-seq), ...}
            The line style.
        """
        if ls is None:
            ls = "solid"
        if ls in [' ', '', 'none']:
            ls = 'None'
        self._linestyle = ls
        self._unscaled_dash_pattern = mlines._get_dash_pattern(ls)
        self._dash_pattern = mlines._scale_dashes(
            *self._unscaled_dash_pattern, self._linewidth)
        self.stale = True

    def set_fill(self, b):
        """
        Set whether to fill the patch.

        Parameters
        ----------
        b : bool
        """
        self._fill = bool(b)
        self._set_facecolor(self._original_facecolor)
        self._set_edgecolor(self._original_edgecolor)
        self.stale = True

    def get_fill(self):
        """Return whether the patch is filled."""
        return self._fill

    # Make fill a property so as to preserve the long-standing
    # but somewhat inconsistent behavior in which fill was an
    # attribute.
    fill = property(get_fill, set_fill)

    @_docstring.interpd
    def set_capstyle(self, s):
        """
        Set the `.CapStyle`.

        The default capstyle is 'round' for `.FancyArrowPatch` and 'butt' for
        all other patches.

        Parameters
        ----------
        s : `.CapStyle` or %(CapStyle)s
        """
        cs = CapStyle(s)
        self._capstyle = cs
        self.stale = True

    def get_capstyle(self):
        """Return the capstyle."""
        return self._capstyle.name

    @_docstring.interpd
    def set_joinstyle(self, s):
        """
        Set the `.JoinStyle`.

        The default joinstyle is 'round' for `.FancyArrowPatch` and 'miter' for
        all other patches.

        Parameters
        ----------
        s : `.JoinStyle` or %(JoinStyle)s
        """
        js = JoinStyle(s)
        self._joinstyle = js
        self.stale = True

    def get_joinstyle(self):
        """Return the joinstyle."""
        return self._joinstyle.name

    def set_hatch(self, hatch):
        r"""
        Set the hatching pattern.

        *hatch* can be one of::

          /   - diagonal hatching
          \   - back diagonal
          |   - vertical
          -   - horizontal
          +   - crossed
          x   - crossed diagonal
          o   - small circle
          O   - large circle
          .   - dots
          *   - stars

        Letters can be combined, in which case all the specified
        hatchings are done.  If same letter repeats, it increases the
        density of hatching of that pattern.

        Parameters
        ----------
        hatch : {'/', '\\', '|', '-', '+', 'x', 'o', 'O', '.', '*'}
        """
        # Use validate_hatch(list) after deprecation.
        mhatch._validate_hatch_pattern(hatch)
        self._hatch = hatch
        self.stale = True

    def get_hatch(self):
        """Return the hatching pattern."""
        return self._hatch

    def set_hatch_linewidth(self, lw):
        """Set the hatch linewidth."""
        self._hatch_linewidth = lw

    def get_hatch_linewidth(self):
        """Return the hatch linewidth."""
        return self._hatch_linewidth

    def _draw_paths_with_artist_properties(
            self, renderer, draw_path_args_list):
        """
        ``draw()`` helper factored out for sharing with `FancyArrowPatch`.

        Configure *renderer* and the associated graphics context *gc*
        from the artist properties, then repeatedly call
        ``renderer.draw_path(gc, *draw_path_args)`` for each tuple
        *draw_path_args* in *draw_path_args_list*.
        """

        renderer.open_group('patch', self.get_gid())
        gc = renderer.new_gc()

        gc.set_foreground(self._edgecolor, isRGBA=True)

        lw = self._linewidth
        if self._edgecolor[3] == 0 or self._linestyle == 'None':
            lw = 0
        gc.set_linewidth(lw)
        gc.set_dashes(*self._dash_pattern)
        gc.set_capstyle(self._capstyle)
        gc.set_joinstyle(self._joinstyle)

        gc.set_antialiased(self._antialiased)
        self._set_gc_clip(gc)
        gc.set_url(self._url)
        gc.set_snap(self.get_snap())

        gc.set_alpha(self._alpha)

        if self._hatch:
            gc.set_hatch(self._hatch)
            gc.set_hatch_color(self._hatch_color)
            gc.set_hatch_linewidth(self._hatch_linewidth)

        if self.get_sketch_params() is not None:
            gc.set_sketch_params(*self.get_sketch_params())

        if self.get_path_effects():
            from matplotlib.patheffects import PathEffectRenderer
            renderer = PathEffectRenderer(self.get_path_effects(), renderer)

        for draw_path_args in draw_path_args_list:
            renderer.draw_path(gc, *draw_path_args)

        gc.restore()
        renderer.close_group('patch')
        self.stale = False

    @artist.allow_rasterization
    def draw(self, renderer):
        # docstring inherited
        if not self.get_visible():
            return
        path = self.get_path()
        transform = self.get_transform()
        tpath = transform.transform_path_non_affine(path)
        affine = transform.get_affine()
        self._draw_paths_with_artist_properties(
            renderer,
            [(tpath, affine,
              # Work around a bug in the PDF and SVG renderers, which
              # do not draw the hatches if the facecolor is fully
              # transparent, but do if it is None.
              self._facecolor if self._facecolor[3] else None)])

    def get_path(self):
        """Return the path of this patch."""
        raise NotImplementedError('Derived must override')

    def get_window_extent(self, renderer=None):
        return self.get_path().get_extents(self.get_transform())

    def _convert_xy_units(self, xy):
        """Convert x and y units for a tuple (x, y)."""
        x = self.convert_xunits(xy[0])
        y = self.convert_yunits(xy[1])
        return x, y


class Shadow(Patch):
    def __str__(self):
        return f"Shadow({self.patch})"

    @_docstring.interpd
    def __init__(self, patch, ox, oy, *, shade=0.7, **kwargs):
        """
        Create a shadow of the given *patch*.

        By default, the shadow will have the same face color as the *patch*,
        but darkened. The darkness can be controlled by *shade*.

        Parameters
        ----------
        patch : `~matplotlib.patches.Patch`
            The patch to create the shadow for.
        ox, oy : float
            The shift of the shadow in data coordinates, scaled by a factor
            of dpi/72.
        shade : float, default: 0.7
            How the darkness of the shadow relates to the original color. If 1, the
            shadow is black, if 0, the shadow has the same color as the *patch*.

            .. versionadded:: 3.8

        **kwargs
            Properties of the shadow patch. Supported keys are:

            %(Patch:kwdoc)s
        """
        super().__init__()
        self.patch = patch
        self._ox, self._oy = ox, oy
        self._shadow_transform = transforms.Affine2D()

        self.update_from(self.patch)
        if not 0 <= shade <= 1:
            raise ValueError("shade must be between 0 and 1.")
        color = (1 - shade) * np.asarray(colors.to_rgb(self.patch.get_facecolor()))
        self.update({'facecolor': color, 'edgecolor': color, 'alpha': 0.5,
                     # Place shadow patch directly behind the inherited patch.
                     'zorder': np.nextafter(self.patch.zorder, -np.inf),
                     **kwargs})

    def _update_transform(self, renderer):
        ox = renderer.points_to_pixels(self._ox)
        oy = renderer.points_to_pixels(self._oy)
        self._shadow_transform.clear().translate(ox, oy)

    def get_path(self):
        return self.patch.get_path()

    def get_patch_transform(self):
        return self.patch.get_patch_transform() + self._shadow_transform

    def draw(self, renderer):
        self._update_transform(renderer)
        super().draw(renderer)


class Rectangle(Patch):
    """
    A rectangle defined via an anchor point *xy* and its *width* and *height*.

    The rectangle extends from ``xy[0]`` to ``xy[0] + width`` in x-direction
    and from ``xy[1]`` to ``xy[1] + height`` in y-direction. ::

      :                +------------------+
      :                |                  |
      :              height               |
      :                |                  |
      :               (xy)---- width -----+

    One may picture *xy* as the bottom left corner, but which corner *xy* is
    actually depends on the direction of the axis and the sign of *width*
    and *height*; e.g. *xy* would be the bottom right corner if the x-axis
    was inverted or if *width* was negative.
    """

    def __str__(self):
        pars = self._x0, self._y0, self._width, self._height, self.angle
        fmt = "Rectangle(xy=(%g, %g), width=%g, height=%g, angle=%g)"
        return fmt % pars

    @_docstring.interpd
    def __init__(self, xy, width, height, *,
                 angle=0.0, rotation_point='xy', **kwargs):
        """
        Parameters
        ----------
        xy : (float, float)
            The anchor point.
        width : float
            Rectangle width.
        height : float
            Rectangle height.
        angle : float, default: 0
            Rotation in degrees anti-clockwise about the rotation point.
        rotation_point : {'xy', 'center', (number, number)}, default: 'xy'
            If ``'xy'``, rotate around the anchor point. If ``'center'`` rotate
            around the center. If 2-tuple of number, rotate around this
            coordinate.

        Other Parameters
        ----------------
        **kwargs : `~matplotlib.patches.Patch` properties
            %(Patch:kwdoc)s
        """
        super().__init__(**kwargs)
        self._x0 = xy[0]
        self._y0 = xy[1]
        self._width = width
        self._height = height
        self.angle = float(angle)
        self.rotation_point = rotation_point
        # Required for RectangleSelector with axes aspect ratio != 1
        # The patch is defined in data coordinates and when changing the
        # selector with square modifier and not in data coordinates, we need
        # to correct for the aspect ratio difference between the data and
        # display coordinate systems. Its value is typically provide by
        # Axes._get_aspect_ratio()
        self._aspect_ratio_correction = 1.0
        self._convert_units()  # Validate the inputs.

    def get_path(self):
        """Return the vertices of the rectangle."""
        return Path.unit_rectangle()

    def _convert_units(self):
        """Convert bounds of the rectangle."""
        x0 = self.convert_xunits(self._x0)
        y0 = self.convert_yunits(self._y0)
        x1 = self.convert_xunits(self._x0 + self._width)
        y1 = self.convert_yunits(self._y0 + self._height)
        return x0, y0, x1, y1

    def get_patch_transform(self):
        # Note: This cannot be called until after this has been added to
        # an Axes, otherwise unit conversion will fail. This makes it very
        # important to call the accessor method and not directly access the
        # transformation member variable.
        bbox = self.get_bbox()
        if self.rotation_point == 'center':
            width, height = bbox.x1 - bbox.x0, bbox.y1 - bbox.y0
            rotation_point = bbox.x0 + width / 2., bbox.y0 + height / 2.
        elif self.rotation_point == 'xy':
            rotation_point = bbox.x0, bbox.y0
        else:
            rotation_point = self.rotation_point
        return transforms.BboxTransformTo(bbox) \
                + transforms.Affine2D() \
                .translate(-rotation_point[0], -rotation_point[1]) \
                .scale(1, self._aspect_ratio_correction) \
                .rotate_deg(self.angle) \
                .scale(1, 1 / self._aspect_ratio_correction) \
                .translate(*rotation_point)

    @property
    def rotation_point(self):
        """The rotation point of the patch."""
        return self._rotation_point

    @rotation_point.setter
    def rotation_point(self, value):
        if value in ['center', 'xy'] or (
                isinstance(value, tuple) and len(value) == 2 and
                isinstance(value[0], Real) and isinstance(value[1], Real)
                ):
            self._rotation_point = value
        else:
            raise ValueError("`rotation_point` must be one of "
                             "{'xy', 'center', (number, number)}.")

    def get_x(self):
        """Return the left coordinate of the rectangle."""
        return self._x0

    def get_y(self):
        """Return the bottom coordinate of the rectangle."""
        return self._y0

    def get_xy(self):
        """Return the left and bottom coords of the rectangle as a tuple."""
        return self._x0, self._y0

    def get_corners(self):
        """
        Return the corners of the rectangle, moving anti-clockwise from
        (x0, y0).
        """
        return self.get_patch_transform().transform(
            [(0, 0), (1, 0), (1, 1), (0, 1)])

    def get_center(self):
        """Return the centre of the rectangle."""
        return self.get_patch_transform().transform((0.5, 0.5))

    def get_width(self):
        """Return the width of the rectangle."""
        return self._width

    def get_height(self):
        """Return the height of the rectangle."""
        return self._height

    def get_angle(self):
        """Get the rotation angle in degrees."""
        return self.angle

    def set_x(self, x):
        """Set the left coordinate of the rectangle."""
        self._x0 = x
        self.stale = True

    def set_y(self, y):
        """Set the bottom coordinate of the rectangle."""
        self._y0 = y
        self.stale = True

    def set_angle(self, angle):
        """
        Set the rotation angle in degrees.

        The rotation is performed anti-clockwise around *xy*.
        """
        self.angle = angle
        self.stale = True

    def set_xy(self, xy):
        """
        Set the left and bottom coordinates of the rectangle.

        Parameters
        ----------
        xy : (float, float)
        """
        self._x0, self._y0 = xy
        self.stale = True

    def set_width(self, w):
        """Set the width of the rectangle."""
        self._width = w
        self.stale = True

    def set_height(self, h):
        """Set the height of the rectangle."""
        self._height = h
        self.stale = True

    def set_bounds(self, *args):
        """
        Set the bounds of the rectangle as *left*, *bottom*, *width*, *height*.

        The values may be passed as separate parameters or as a tuple::

            set_bounds(left, bottom, width, height)
            set_bounds((left, bottom, width, height))

        .. ACCEPTS: (left, bottom, width, height)
        """
        if len(args) == 1:
            l, b, w, h = args[0]
        else:
            l, b, w, h = args
        self._x0 = l
        self._y0 = b
        self._width = w
        self._height = h
        self.stale = True

    def get_bbox(self):
        """Return the `.Bbox`."""
        return transforms.Bbox.from_extents(*self._convert_units())

    xy = property(get_xy, set_xy)


class RegularPolygon(Patch):
    """A regular polygon patch."""

    def __str__(self):
        s = "RegularPolygon((%g, %g), %d, radius=%g, orientation=%g)"
        return s % (self.xy[0], self.xy[1], self.numvertices, self.radius,
                    self.orientation)

    @_docstring.interpd
    def __init__(self, xy, numVertices, *,
                 radius=5, orientation=0, **kwargs):
        """
        Parameters
        ----------
        xy : (float, float)
            The center position.

        numVertices : int
            The number of vertices.

        radius : float
            The distance from the center to each of the vertices.

        orientation : float
            The polygon rotation angle (in radians).

        **kwargs
            `Patch` properties:

            %(Patch:kwdoc)s
        """
        self.xy = xy
        self.numvertices = numVertices
        self.orientation = orientation
        self.radius = radius
        self._path = Path.unit_regular_polygon(numVertices)
        self._patch_transform = transforms.Affine2D()
        super().__init__(**kwargs)

    def get_path(self):
        return self._path

    def get_patch_transform(self):
        return self._patch_transform.clear() \
            .scale(self.radius) \
            .rotate(self.orientation) \
            .translate(*self.xy)


class PathPatch(Patch):
    """A general polycurve path patch."""

    _edge_default = True

    def __str__(self):
        s = "PathPatch%d((%g, %g) ...)"
        return s % (len(self._path.vertices), *tuple(self._path.vertices[0]))

    @_docstring.interpd
    def __init__(self, path, **kwargs):
        """
        *path* is a `.Path` object.

        Valid keyword arguments are:

        %(Patch:kwdoc)s
        """
        super().__init__(**kwargs)
        self._path = path

    def get_path(self):
        return self._path

    def set_path(self, path):
        self._path = path


class StepPatch(PathPatch):
    """
    A path patch describing a stepwise constant function.

    By default, the path is not closed and starts and stops at
    baseline value.
    """

    _edge_default = False

    @_docstring.interpd
    def __init__(self, values, edges, *,
                 orientation='vertical', baseline=0, **kwargs):
        """
        Parameters
        ----------
        values : array-like
            The step heights.

        edges : array-like
            The edge positions, with ``len(edges) == len(vals) + 1``,
            between which the curve takes on vals values.

        orientation : {'vertical', 'horizontal'}, default: 'vertical'
            The direction of the steps. Vertical means that *values* are
            along the y-axis, and edges are along the x-axis.

        baseline : float, array-like or None, default: 0
            The bottom value of the bounding edges or when
            ``fill=True``, position of lower edge. If *fill* is
            True or an array is passed to *baseline*, a closed
            path is drawn.

        **kwargs
            `Patch` properties:

            %(Patch:kwdoc)s
        """
        self.orientation = orientation
        self._edges = np.asarray(edges)
        self._values = np.asarray(values)
        self._baseline = np.asarray(baseline) if baseline is not None else None
        self._update_path()
        super().__init__(self._path, **kwargs)

    def _update_path(self):
        if np.isnan(np.sum(self._edges)):
            raise ValueError('Nan values in "edges" are disallowed')
        if self._edges.size - 1 != self._values.size:
            raise ValueError('Size mismatch between "values" and "edges". '
                             "Expected `len(values) + 1 == len(edges)`, but "
                             f"`len(values) = {self._values.size}` and "
                             f"`len(edges) = {self._edges.size}`.")
        # Initializing with empty arrays allows supporting empty stairs.
        verts, codes = [np.empty((0, 2))], [np.empty(0, dtype=Path.code_type)]

        _nan_mask = np.isnan(self._values)
        if self._baseline is not None:
            _nan_mask |= np.isnan(self._baseline)
        for idx0, idx1 in cbook.contiguous_regions(~_nan_mask):
            x = np.repeat(self._edges[idx0:idx1+1], 2)
            y = np.repeat(self._values[idx0:idx1], 2)
            if self._baseline is None:
                y = np.concatenate([y[:1], y, y[-1:]])
            elif self._baseline.ndim == 0:  # single baseline value
                y = np.concatenate([[self._baseline], y, [self._baseline]])
            elif self._baseline.ndim == 1:  # baseline array
                base = np.repeat(self._baseline[idx0:idx1], 2)[::-1]
                x = np.concatenate([x, x[::-1]])
                y = np.concatenate([base[-1:], y, base[:1],
                                    base[:1], base, base[-1:]])
            else:  # no baseline
                raise ValueError('Invalid `baseline` specified')
            if self.orientation == 'vertical':
                xy = np.column_stack([x, y])
            else:
                xy = np.column_stack([y, x])
            verts.append(xy)
            codes.append([Path.MOVETO] + [Path.LINETO]*(len(xy)-1))
        self._path = Path(np.concatenate(verts), np.concatenate(codes))

    def get_data(self):
        """Get `.StepPatch` values, edges and baseline as namedtuple."""
        StairData = namedtuple('StairData', 'values edges baseline')
        return StairData(self._values, self._edges, self._baseline)

    def set_data(self, values=None, edges=None, baseline=None):
        """
        Set `.StepPatch` values, edges and baseline.

        Parameters
        ----------
        values : 1D array-like or None
            Will not update values, if passing None
        edges : 1D array-like, optional
        baseline : float, 1D array-like or None
        """
        if values is None and edges is None and baseline is None:
            raise ValueError("Must set *values*, *edges* or *baseline*.")
        if values is not None:
            self._values = np.asarray(values)
        if edges is not None:
            self._edges = np.asarray(edges)
        if baseline is not None:
            self._baseline = np.asarray(baseline)
        self._update_path()
        self.stale = True


class Polygon(Patch):
    """A general polygon patch."""

    def __str__(self):
        if len(self._path.vertices):
            s = "Polygon%d((%g, %g) ...)"
            return s % (len(self._path.vertices), *self._path.vertices[0])
        else:
            return "Polygon0()"

    @_docstring.interpd
    def __init__(self, xy, *, closed=True, **kwargs):
        """
        Parameters
        ----------
        xy : (N, 2) array

        closed : bool, default: True
            Whether the polygon is closed (i.e., has identical start and end
            points).

        **kwargs
            %(Patch:kwdoc)s
        """
        super().__init__(**kwargs)
        self._closed = closed
        self.set_xy(xy)

    def get_path(self):
        """Get the `.Path` of the polygon."""
        return self._path

    def get_closed(self):
        """Return whether the polygon is closed."""
        return self._closed

    def set_closed(self, closed):
        """
        Set whether the polygon is closed.

        Parameters
        ----------
        closed : bool
            True if the polygon is closed
        """
        if self._closed == bool(closed):
            return
        self._closed = bool(closed)
        self.set_xy(self.get_xy())
        self.stale = True

    def get_xy(self):
        """
        Get the vertices of the path.

        Returns
        -------
        (N, 2) array
            The coordinates of the vertices.
        """
        return self._path.vertices

    def set_xy(self, xy):
        """
        Set the vertices of the polygon.

        Parameters
        ----------
        xy : (N, 2) array-like
            The coordinates of the vertices.

        Notes
        -----
        Unlike `.Path`, we do not ignore the last input vertex. If the
        polygon is meant to be closed, and the last point of the polygon is not
        equal to the first, we assume that the user has not explicitly passed a
        ``CLOSEPOLY`` vertex, and add it ourselves.
        """
        xy = np.asarray(xy)
        nverts, _ = xy.shape
        if self._closed:
            # if the first and last vertex are the "same", then we assume that
            # the user explicitly passed the CLOSEPOLY vertex. Otherwise, we
            # have to append one since the last vertex will be "ignored" by
            # Path
            if nverts == 1 or nverts > 1 and (xy[0] != xy[-1]).any():
                xy = np.concatenate([xy, [xy[0]]])
        else:
            # if we aren't closed, and the last vertex matches the first, then
            # we assume we have an unnecessary CLOSEPOLY vertex and remove it
            if nverts > 2 and (xy[0] == xy[-1]).all():
                xy = xy[:-1]
        self._path = Path(xy, closed=self._closed)
        self.stale = True

    xy = property(get_xy, set_xy,
                  doc='The vertices of the path as a (N, 2) array.')


class Wedge(Patch):
    """Wedge shaped patch."""

    def __str__(self):
        pars = (self.center[0], self.center[1], self.r,
                self.theta1, self.theta2, self.width)
        fmt = "Wedge(center=(%g, %g), r=%g, theta1=%g, theta2=%g, width=%s)"
        return fmt % pars

    @_docstring.interpd
    def __init__(self, center, r, theta1, theta2, *, width=None, **kwargs):
        """
        A wedge centered at *x*, *y* center with radius *r* that
        sweeps *theta1* to *theta2* (in degrees).  If *width* is given,
        then a partial wedge is drawn from inner radius *r* - *width*
        to outer radius *r*.

        Valid keyword arguments are:

        %(Patch:kwdoc)s
        """
        super().__init__(**kwargs)
        self.center = center
        self.r, self.width = r, width
        self.theta1, self.theta2 = theta1, theta2
        self._patch_transform = transforms.IdentityTransform()
        self._recompute_path()

    def _recompute_path(self):
        # Inner and outer rings are connected unless the annulus is complete
        if abs((self.theta2 - self.theta1) - 360) <= 1e-12:
            theta1, theta2 = 0, 360
            connector = Path.MOVETO
        else:
            theta1, theta2 = self.theta1, self.theta2
            connector = Path.LINETO

        # Form the outer ring
        arc = Path.arc(theta1, theta2)

        if self.width is not None:
            # Partial annulus needs to draw the outer ring
            # followed by a reversed and scaled inner ring
            v1 = arc.vertices
            v2 = arc.vertices[::-1] * (self.r - self.width) / self.r
            v = np.concatenate([v1, v2, [(0, 0)]])
            c = [*arc.codes, connector, *arc.codes[1:], Path.CLOSEPOLY]
        else:
            # Wedge doesn't need an inner ring
            v = np.concatenate([arc.vertices, [(0, 0), (0, 0)]])
            c = [*arc.codes, connector, Path.CLOSEPOLY]

        # Shift and scale the wedge to the final location.
        self._path = Path(v * self.r + self.center, c)

    def set_center(self, center):
        self._path = None
        self.center = center
        self.stale = True

    def set_radius(self, radius):
        self._path = None
        self.r = radius
        self.stale = True

    def set_theta1(self, theta1):
        self._path = None
        self.theta1 = theta1
        self.stale = True

    def set_theta2(self, theta2):
        self._path = None
        self.theta2 = theta2
        self.stale = True

    def set_width(self, width):
        self._path = None
        self.width = width
        self.stale = True

    def get_path(self):
        if self._path is None:
            self._recompute_path()
        return self._path


# COVERAGE NOTE: Not used internally or from examples
class Arrow(Patch):
    """An arrow patch."""

    def __str__(self):
        return "Arrow()"

    _path = Path._create_closed([
        [0.0, 0.1], [0.0, -0.1], [0.8, -0.1], [0.8, -0.3], [1.0, 0.0],
        [0.8, 0.3], [0.8, 0.1]])

    @_docstring.interpd
    def __init__(self, x, y, dx, dy, *, width=1.0, **kwargs):
        """
        Draws an arrow from (*x*, *y*) to (*x* + *dx*, *y* + *dy*).
        The width of the arrow is scaled by *width*.

        Parameters
        ----------
        x : float
            x coordinate of the arrow tail.
        y : float
            y coordinate of the arrow tail.
        dx : float
            Arrow length in the x direction.
        dy : float
            Arrow length in the y direction.
        width : float, default: 1
            Scale factor for the width of the arrow. With a default value of 1,
            the tail width is 0.2 and head width is 0.6.
        **kwargs
            Keyword arguments control the `Patch` properties:

            %(Patch:kwdoc)s

        See Also
        --------
        FancyArrow
            Patch that allows independent control of the head and tail
            properties.
        """
        super().__init__(**kwargs)
        self.set_data(x, y, dx, dy, width)

    def get_path(self):
        return self._path

    def get_patch_transform(self):
        return self._patch_transform

    def set_data(self, x=None, y=None, dx=None, dy=None, width=None):
        """
        Set `.Arrow` x, y, dx, dy and width.
        Values left as None will not be updated.

        Parameters
        ----------
        x, y : float or None, default: None
            The x and y coordinates of the arrow base.

        dx, dy : float or None, default: None
            The length of the arrow along x and y direction.

        width : float or None, default: None
            Width of full arrow tail.
        """
        if x is not None:
            self._x = x
        if y is not None:
            self._y = y
        if dx is not None:
            self._dx = dx
        if dy is not None:
            self._dy = dy
        if width is not None:
            self._width = width
        self._patch_transform = (
            transforms.Affine2D()
            .scale(np.hypot(self._dx, self._dy), self._width)
            .rotate(np.arctan2(self._dy, self._dx))
            .translate(self._x, self._y)
            .frozen())


class FancyArrow(Polygon):
    """
    Like Arrow, but lets you set head width and head height independently.
    """

    _edge_default = True

    def __str__(self):
        return "FancyArrow()"

    @_docstring.interpd
    def __init__(self, x, y, dx, dy, *,
                 width=0.001, length_includes_head=False, head_width=None,
                 head_length=None, shape='full', overhang=0,
                 head_starts_at_zero=False, **kwargs):
        """
        Parameters
        ----------
        x, y : float
            The x and y coordinates of the arrow base.

        dx, dy : float
            The length of the arrow along x and y direction.

        width : float, default: 0.001
            Width of full arrow tail.

        length_includes_head : bool, default: False
            True if head is to be counted in calculating the length.

        head_width : float or None, default: 3*width
            Total width of the full arrow head.

        head_length : float or None, default: 1.5*head_width
            Length of arrow head.

        shape : {'full', 'left', 'right'}, default: 'full'
            Draw the left-half, right-half, or full arrow.

        overhang : float, default: 0
            Fraction that the arrow is swept back (0 overhang means
            triangular shape). Can be negative or greater than one.

        head_starts_at_zero : bool, default: False
            If True, the head starts being drawn at coordinate 0
            instead of ending at coordinate 0.

        **kwargs
            `.Patch` properties:

            %(Patch:kwdoc)s
        """
        self._x = x
        self._y = y
        self._dx = dx
        self._dy = dy
        self._width = width
        self._length_includes_head = length_includes_head
        self._head_width = head_width
        self._head_length = head_length
        self._shape = shape
        self._overhang = overhang
        self._head_starts_at_zero = head_starts_at_zero
        self._make_verts()
        super().__init__(self.verts, closed=True, **kwargs)

    def set_data(self, *, x=None, y=None, dx=None, dy=None, width=None,
                 head_width=None, head_length=None):
        """
        Set `.FancyArrow` x, y, dx, dy, width, head_with, and head_length.
        Values left as None will not be updated.

        Parameters
        ----------
        x, y : float or None, default: None
            The x and y coordinates of the arrow base.

        dx, dy : float or None, default: None
            The length of the arrow along x and y direction.

        width : float or None, default: None
            Width of full arrow tail.

        head_width : float or None, default: None
            Total width of the full arrow head.

        head_length : float or None, default: None
            Length of arrow head.
        """
        if x is not None:
            self._x = x
        if y is not None:
            self._y = y
        if dx is not None:
            self._dx = dx
        if dy is not None:
            self._dy = dy
        if width is not None:
            self._width = width
        if head_width is not None:
            self._head_width = head_width
        if head_length is not None:
            self._head_length = head_length
        self._make_verts()
        self.set_xy(self.verts)

    def _make_verts(self):
        if self._head_width is None:
            head_width = 3 * self._width
        else:
            head_width = self._head_width
        if self._head_length is None:
            head_length = 1.5 * head_width
        else:
            head_length = self._head_length

        distance = np.hypot(self._dx, self._dy)

        if self._length_includes_head:
            length = distance
        else:
            length = distance + head_length
        if not length:
            self.verts = np.empty([0, 2])  # display nothing if empty
        else:
            # start by drawing horizontal arrow, point at (0, 0)
            hw, hl = head_width, head_length
            hs, lw = self._overhang, self._width
            left_half_arrow = np.array([
                [0.0, 0.0],                 # tip
                [-hl, -hw / 2],             # leftmost
                [-hl * (1 - hs), -lw / 2],  # meets stem
                [-length, -lw / 2],         # bottom left
                [-length, 0],
            ])
            # if we're not including the head, shift up by head length
            if not self._length_includes_head:
                left_half_arrow += [head_length, 0]
            # if the head starts at 0, shift up by another head length
            if self._head_starts_at_zero:
                left_half_arrow += [head_length / 2, 0]
            # figure out the shape, and complete accordingly
            if self._shape == 'left':
                coords = left_half_arrow
            else:
                right_half_arrow = left_half_arrow * [1, -1]
                if self._shape == 'right':
                    coords = right_half_arrow
                elif self._shape == 'full':
                    # The half-arrows contain the midpoint of the stem,
                    # which we can omit from the full arrow. Including it
                    # twice caused a problem with xpdf.
                    coords = np.concatenate([left_half_arrow[:-1],
                                             right_half_arrow[-2::-1]])
                else:
                    raise ValueError(f"Got unknown shape: {self._shape!r}")
            if distance != 0:
                cx = self._dx / distance
                sx = self._dy / distance
            else:
                # Account for division by zero
                cx, sx = 0, 1
            M = [[cx, sx], [-sx, cx]]
            self.verts = np.dot(coords, M) + [
                self._x + self._dx,
                self._y + self._dy,
            ]


_docstring.interpd.register(
    FancyArrow="\n".join(
        (inspect.getdoc(FancyArrow.__init__) or "").splitlines()[2:]))


class CirclePolygon(RegularPolygon):
    """A polygon-approximation of a circle patch."""

    def __str__(self):
        s = "CirclePolygon((%g, %g), radius=%g, resolution=%d)"
        return s % (self.xy[0], self.xy[1], self.radius, self.numvertices)

    @_docstring.interpd
    def __init__(self, xy, radius=5, *,
                 resolution=20,  # the number of vertices
                 ** kwargs):
        """
        Create a circle at *xy* = (*x*, *y*) with given *radius*.

        This circle is approximated by a regular polygon with *resolution*
        sides.  For a smoother circle drawn with splines, see `Circle`.

        Valid keyword arguments are:

        %(Patch:kwdoc)s
        """
        super().__init__(
            xy, resolution, radius=radius, orientation=0, **kwargs)


class Ellipse(Patch):
    """A scale-free ellipse."""

    def __str__(self):
        pars = (self._center[0], self._center[1],
                self.width, self.height, self.angle)
        fmt = "Ellipse(xy=(%s, %s), width=%s, height=%s, angle=%s)"
        return fmt % pars

    @_docstring.interpd
    def __init__(self, xy, width, height, *, angle=0, **kwargs):
        """
        Parameters
        ----------
        xy : (float, float)
            xy coordinates of ellipse centre.
        width : float
            Total length (diameter) of horizontal axis.
        height : float
            Total length (diameter) of vertical axis.
        angle : float, default: 0
            Rotation in degrees anti-clockwise.

        Notes
        -----
        Valid keyword arguments are:

        %(Patch:kwdoc)s
        """
        super().__init__(**kwargs)

        self._center = xy
        self._width, self._height = width, height
        self._angle = angle
        self._path = Path.unit_circle()
        # Required for EllipseSelector with axes aspect ratio != 1
        # The patch is defined in data coordinates and when changing the
        # selector with square modifier and not in data coordinates, we need
        # to correct for the aspect ratio difference between the data and
        # display coordinate systems.
        self._aspect_ratio_correction = 1.0
        # Note: This cannot be calculated until this is added to an Axes
        self._patch_transform = transforms.IdentityTransform()

    def _recompute_transform(self):
        """
        Notes
        -----
        This cannot be called until after this has been added to an Axes,
        otherwise unit conversion will fail. This makes it very important to
        call the accessor method and not directly access the transformation
        member variable.
        """
        center = (self.convert_xunits(self._center[0]),
                  self.convert_yunits(self._center[1]))
        width = self.convert_xunits(self._width)
        height = self.convert_yunits(self._height)
        self._patch_transform = transforms.Affine2D() \
            .scale(width * 0.5, height * 0.5 * self._aspect_ratio_correction) \
            .rotate_deg(self.angle) \
            .scale(1, 1 / self._aspect_ratio_correction) \
            .translate(*center)

    def get_path(self):
        """Return the path of the ellipse."""
        return self._path

    def get_patch_transform(self):
        self._recompute_transform()
        return self._patch_transform

    def set_center(self, xy):
        """
        Set the center of the ellipse.

        Parameters
        ----------
        xy : (float, float)
        """
        self._center = xy
        self.stale = True

    def get_center(self):
        """Return the center of the ellipse."""
        return self._center

    center = property(get_center, set_center)

    def set_width(self, width):
        """
        Set the width of the ellipse.

        Parameters
        ----------
        width : float
        """
        self._width = width
        self.stale = True

    def get_width(self):
        """
        Return the width of the ellipse.
        """
        return self._width

    width = property(get_width, set_width)

    def set_height(self, height):
        """
        Set the height of the ellipse.

        Parameters
        ----------
        height : float
        """
        self._height = height
        self.stale = True

    def get_height(self):
        """Return the height of the ellipse."""
        return self._height

    height = property(get_height, set_height)

    def set_angle(self, angle):
        """
        Set the angle of the ellipse.

        Parameters
        ----------
        angle : float
        """
        self._angle = angle
        self.stale = True

    def get_angle(self):
        """Return the angle of the ellipse."""
        return self._angle

    angle = property(get_angle, set_angle)

    def get_corners(self):
        """
        Return the corners of the ellipse bounding box.

        The bounding box orientation is moving anti-clockwise from the
        lower left corner defined before rotation.
        """
        return self.get_patch_transform().transform(
            [(-1, -1), (1, -1), (1, 1), (-1, 1)])

    def get_vertices(self):
        """
        Return the vertices coordinates of the ellipse.

        The definition can be found `here <https://en.wikipedia.org/wiki/Ellipse>`_

        .. versionadded:: 3.8
        """
        if self.width < self.height:
            ret = self.get_patch_transform().transform([(0, 1), (0, -1)])
        else:
            ret = self.get_patch_transform().transform([(1, 0), (-1, 0)])
        return [tuple(x) for x in ret]

    def get_co_vertices(self):
        """
        Return the co-vertices coordinates of the ellipse.

        The definition can be found `here <https://en.wikipedia.org/wiki/Ellipse>`_

        .. versionadded:: 3.8
        """
        if self.width < self.height:
            ret = self.get_patch_transform().transform([(1, 0), (-1, 0)])
        else:
            ret = self.get_patch_transform().transform([(0, 1), (0, -1)])
        return [tuple(x) for x in ret]


class Annulus(Patch):
    """
    An elliptical annulus.
    """

    @_docstring.interpd
    def __init__(self, xy, r, width, angle=0.0, **kwargs):
        """
        Parameters
        ----------
        xy : (float, float)
            xy coordinates of annulus centre.
        r : float or (float, float)
            The radius, or semi-axes:

            - If float: radius of the outer circle.
            - If two floats: semi-major and -minor axes of outer ellipse.
        width : float
            Width (thickness) of the annular ring. The width is measured inward
            from the outer ellipse so that for the inner ellipse the semi-axes
            are given by ``r - width``. *width* must be less than or equal to
            the semi-minor axis.
        angle : float, default: 0
            Rotation angle in degrees (anti-clockwise from the positive
            x-axis). Ignored for circular annuli (i.e., if *r* is a scalar).
        **kwargs
            Keyword arguments control the `Patch` properties:

            %(Patch:kwdoc)s
        """
        super().__init__(**kwargs)

        self.set_radii(r)
        self.center = xy
        self.width = width
        self.angle = angle
        self._path = None

    def __str__(self):
        if self.a == self.b:
            r = self.a
        else:
            r = (self.a, self.b)

        return "Annulus(xy=(%s, %s), r=%s, width=%s, angle=%s)" % \
                (*self.center, r, self.width, self.angle)

    def set_center(self, xy):
        """
        Set the center of the annulus.

        Parameters
        ----------
        xy : (float, float)
        """
        self._center = xy
        self._path = None
        self.stale = True

    def get_center(self):
        """Return the center of the annulus."""
        return self._center

    center = property(get_center, set_center)

    def set_width(self, width):
        """
        Set the width (thickness) of the annulus ring.

        The width is measured inwards from the outer ellipse.

        Parameters
        ----------
        width : float
        """
        if width > min(self.a, self.b):
            raise ValueError(
                'Width of annulus must be less than or equal to semi-minor axis')

        self._width = width
        self._path = None
        self.stale = True

    def get_width(self):
        """Return the width (thickness) of the annulus ring."""
        return self._width

    width = property(get_width, set_width)

    def set_angle(self, angle):
        """
        Set the tilt angle of the annulus.

        Parameters
        ----------
        angle : float
        """
        self._angle = angle
        self._path = None
        self.stale = True

    def get_angle(self):
        """Return the angle of the annulus."""
        return self._angle

    angle = property(get_angle, set_angle)

    def set_semimajor(self, a):
        """
        Set the semi-major axis *a* of the annulus.

        Parameters
        ----------
        a : float
        """
        self.a = float(a)
        self._path = None
        self.stale = True

    def set_semiminor(self, b):
        """
        Set the semi-minor axis *b* of the annulus.

        Parameters
        ----------
        b : float
        """
        self.b = float(b)
        self._path = None
        self.stale = True

    def set_radii(self, r):
        """
        Set the semi-major (*a*) and semi-minor radii (*b*) of the annulus.

        Parameters
        ----------
        r : float or (float, float)
            The radius, or semi-axes:

            - If float: radius of the outer circle.
            - If two floats: semi-major and -minor axes of outer ellipse.
        """
        if np.shape(r) == (2,):
            self.a, self.b = r
        elif np.shape(r) == ():
            self.a = self.b = float(r)
        else:
            raise ValueError("Parameter 'r' must be one or two floats.")

        self._path = None
        self.stale = True

    def get_radii(self):
        """Return the semi-major and semi-minor radii of the annulus."""
        return self.a, self.b

    radii = property(get_radii, set_radii)

    def _transform_verts(self, verts, a, b):
        return transforms.Affine2D() \
            .scale(*self._convert_xy_units((a, b))) \
            .rotate_deg(self.angle) \
            .translate(*self._convert_xy_units(self.center)) \
            .transform(verts)

    def _recompute_path(self):
        # circular arc
        arc = Path.arc(0, 360)

        # annulus needs to draw an outer ring
        # followed by a reversed and scaled inner ring
        a, b, w = self.a, self.b, self.width
        v1 = self._transform_verts(arc.vertices, a, b)
        v2 = self._transform_verts(arc.vertices[::-1], a - w, b - w)
        v = np.vstack([v1, v2, v1[0, :], (0, 0)])
        c = np.hstack([arc.codes, Path.MOVETO,
                       arc.codes[1:], Path.MOVETO,
                       Path.CLOSEPOLY])
        self._path = Path(v, c)

    def get_path(self):
        if self._path is None:
            self._recompute_path()
        return self._path


class Circle(Ellipse):
    """
    A circle patch.
    """
    def __str__(self):
        pars = self.center[0], self.center[1], self.radius
        fmt = "Circle(xy=(%g, %g), radius=%g)"
        return fmt % pars

    @_docstring.interpd
    def __init__(self, xy, radius=5, **kwargs):
        """
        Create a true circle at center *xy* = (*x*, *y*) with given *radius*.

        Unlike `CirclePolygon` which is a polygonal approximation, this uses
        Bezier splines and is much closer to a scale-free circle.

        Valid keyword arguments are:

        %(Patch:kwdoc)s
        """
        super().__init__(xy, radius * 2, radius * 2, **kwargs)
        self.radius = radius

    def set_radius(self, radius):
        """
        Set the radius of the circle.

        Parameters
        ----------
        radius : float
        """
        self.width = self.height = 2 * radius
        self.stale = True

    def get_radius(self):
        """Return the radius of the circle."""
        return self.width / 2.

    radius = property(get_radius, set_radius)


class Arc(Ellipse):
    """
    An elliptical arc, i.e. a segment of an ellipse.

    Due to internal optimizations, the arc cannot be filled.
    """

    def __str__(self):
        pars = (self.center[0], self.center[1], self.width,
                self.height, self.angle, self.theta1, self.theta2)
        fmt = ("Arc(xy=(%g, %g), width=%g, "
               "height=%g, angle=%g, theta1=%g, theta2=%g)")
        return fmt % pars

    @_docstring.interpd
    def __init__(self, xy, width, height, *,
                 angle=0.0, theta1=0.0, theta2=360.0, **kwargs):
        """
        Parameters
        ----------
        xy : (float, float)
            The center of the ellipse.

        width : float
            The length of the horizontal axis.

        height : float
            The length of the vertical axis.

        angle : float
            Rotation of the ellipse in degrees (counterclockwise).

        theta1, theta2 : float, default: 0, 360
            Starting and ending angles of the arc in degrees. These values
            are relative to *angle*, e.g. if *angle* = 45 and *theta1* = 90
            the absolute starting angle is 135.
            Default *theta1* = 0, *theta2* = 360, i.e. a complete ellipse.
            The arc is drawn in the counterclockwise direction.
            Angles greater than or equal to 360, or smaller than 0, are
            represented by an equivalent angle in the range [0, 360), by
            taking the input value mod 360.

        Other Parameters
        ----------------
        **kwargs : `~matplotlib.patches.Patch` properties
            Most `.Patch` properties are supported as keyword arguments,
            except *fill* and *facecolor* because filling is not supported.

        %(Patch:kwdoc)s
        """
        fill = kwargs.setdefault('fill', False)
        if fill:
            raise ValueError("Arc objects cannot be filled")

        super().__init__(xy, width, height, angle=angle, **kwargs)

        self.theta1 = theta1
        self.theta2 = theta2
        (self._theta1, self._theta2, self._stretched_width,
         self._stretched_height) = self._theta_stretch()
        self._path = Path.arc(self._theta1, self._theta2)

    @artist.allow_rasterization
    def draw(self, renderer):
        """
        Draw the arc to the given *renderer*.

        Notes
        -----
        Ellipses are normally drawn using an approximation that uses
        eight cubic Bezier splines.  The error of this approximation
        is 1.89818e-6, according to this unverified source:

          Lancaster, Don.  *Approximating a Circle or an Ellipse Using
          Four Bezier Cubic Splines.*

          https://www.tinaja.com/glib/ellipse4.pdf

        There is a use case where very large ellipses must be drawn
        with very high accuracy, and it is too expensive to render the
        entire ellipse with enough segments (either splines or line
        segments).  Therefore, in the case where either radius of the
        ellipse is large enough that the error of the spline
        approximation will be visible (greater than one pixel offset
        from the ideal), a different technique is used.

        In that case, only the visible parts of the ellipse are drawn,
        with each visible arc using a fixed number of spline segments
        (8).  The algorithm proceeds as follows:

        1. The points where the ellipse intersects the axes (or figure)
           bounding box are located.  (This is done by performing an inverse
           transformation on the bbox such that it is relative to the unit
           circle -- this makes the intersection calculation much easier than
           doing rotated ellipse intersection directly.)

           This uses the "line intersecting a circle" algorithm from:

               Vince, John.  *Geometry for Computer Graphics: Formulae,
               Examples & Proofs.*  London: Springer-Verlag, 2005.

        2. The angles of each of the intersection points are calculated.

        3. Proceeding counterclockwise starting in the positive
           x-direction, each of the visible arc-segments between the
           pairs of vertices are drawn using the Bezier arc
           approximation technique implemented in `.Path.arc`.
        """
        if not self.get_visible():
            return

        self._recompute_transform()

        self._update_path()
        # Get width and height in pixels we need to use
        # `self.get_data_transform` rather than `self.get_transform`
        # because we want the transform from dataspace to the
        # screen space to estimate how big the arc will be in physical
        # units when rendered (the transform that we get via
        # `self.get_transform()` goes from an idealized unit-radius
        # space to screen space).
        data_to_screen_trans = self.get_data_transform()
        pwidth, pheight = (
            data_to_screen_trans.transform((self._stretched_width,
                                            self._stretched_height)) -
            data_to_screen_trans.transform((0, 0)))
        inv_error = (1.0 / 1.89818e-6) * 0.5

        if pwidth < inv_error and pheight < inv_error:
            return Patch.draw(self, renderer)

        def line_circle_intersect(x0, y0, x1, y1):
            dx = x1 - x0
            dy = y1 - y0
            dr2 = dx * dx + dy * dy
            D = x0 * y1 - x1 * y0
            D2 = D * D
            discrim = dr2 - D2
            if discrim >= 0.0:
                sign_dy = np.copysign(1, dy)  # +/-1, never 0.
                sqrt_discrim = np.sqrt(discrim)
                return np.array(
                    [[(D * dy + sign_dy * dx * sqrt_discrim) / dr2,
                      (-D * dx + abs(dy) * sqrt_discrim) / dr2],
                     [(D * dy - sign_dy * dx * sqrt_discrim) / dr2,
                      (-D * dx - abs(dy) * sqrt_discrim) / dr2]])
            else:
                return np.empty((0, 2))

        def segment_circle_intersect(x0, y0, x1, y1):
            epsilon = 1e-9
            if x1 < x0:
                x0e, x1e = x1, x0
            else:
                x0e, x1e = x0, x1
            if y1 < y0:
                y0e, y1e = y1, y0
            else:
                y0e, y1e = y0, y1
            xys = line_circle_intersect(x0, y0, x1, y1)
            xs, ys = xys.T
            return xys[
                (x0e - epsilon < xs) & (xs < x1e + epsilon)
                & (y0e - epsilon < ys) & (ys < y1e + epsilon)
            ]

        # Transform the Axes (or figure) box_path so that it is relative to
        # the unit circle in the same way that it is relative to the desired
        # ellipse.
        box_path_transform = (
            transforms.BboxTransformTo((self.axes or self.get_figure(root=False)).bbox)
            - self.get_transform())
        box_path = Path.unit_rectangle().transformed(box_path_transform)

        thetas = set()
        # For each of the point pairs, there is a line segment
        for p0, p1 in zip(box_path.vertices[:-1], box_path.vertices[1:]):
            xy = segment_circle_intersect(*p0, *p1)
            x, y = xy.T
            # arctan2 return [-pi, pi), the rest of our angles are in
            # [0, 360], adjust as needed.
            theta = (np.rad2deg(np.arctan2(y, x)) + 360) % 360
            thetas.update(
                theta[(self._theta1 < theta) & (theta < self._theta2)])
        thetas = sorted(thetas) + [self._theta2]
        last_theta = self._theta1
        theta1_rad = np.deg2rad(self._theta1)
        inside = box_path.contains_point(
            (np.cos(theta1_rad), np.sin(theta1_rad))
        )

        # save original path
        path_original = self._path
        for theta in thetas:
            if inside:
                self._path = Path.arc(last_theta, theta, 8)
                Patch.draw(self, renderer)
                inside = False
            else:
                inside = True
            last_theta = theta

        # restore original path
        self._path = path_original

    def _update_path(self):
        # Compute new values and update and set new _path if any value changed
        stretched = self._theta_stretch()
        if any(a != b for a, b in zip(
                stretched, (self._theta1, self._theta2, self._stretched_width,
                            self._stretched_height))):
            (self._theta1, self._theta2, self._stretched_width,
             self._stretched_height) = stretched
            self._path = Path.arc(self._theta1, self._theta2)

    def _theta_stretch(self):
        # If the width and height of ellipse are not equal, take into account
        # stretching when calculating angles to draw between
        def theta_stretch(theta, scale):
            theta = np.deg2rad(theta)
            x = np.cos(theta)
            y = np.sin(theta)
            stheta = np.rad2deg(np.arctan2(scale * y, x))
            # arctan2 has the range [-pi, pi], we expect [0, 2*pi]
            return (stheta + 360) % 360

        width = self.convert_xunits(self.width)
        height = self.convert_yunits(self.height)
        if (
            # if we need to stretch the angles because we are distorted
            width != height
            # and we are not doing a full circle.
            #
            # 0 and 360 do not exactly round-trip through the angle
            # stretching (due to both float precision limitations and
            # the difference between the range of arctan2 [-pi, pi] and
            # this method [0, 360]) so avoid doing it if we don't have to.
            and not (self.theta1 != self.theta2 and
                     self.theta1 % 360 == self.theta2 % 360)
        ):
            theta1 = theta_stretch(self.theta1, width / height)
            theta2 = theta_stretch(self.theta2, width / height)
            return theta1, theta2, width, height
        return self.theta1, self.theta2, width, height


def bbox_artist(artist, renderer, props=None, fill=True):
    """
    A debug function to draw a rectangle around the bounding
    box returned by an artist's `.Artist.get_window_extent`
    to test whether the artist is returning the correct bbox.

    *props* is a dict of rectangle props with the additional property
    'pad' that sets the padding around the bbox in points.
    """
    if props is None:
        props = {}
    props = props.copy()  # don't want to alter the pad externally
    pad = props.pop('pad', 4)
    pad = renderer.points_to_pixels(pad)
    bbox = artist.get_window_extent(renderer)
    r = Rectangle(
        xy=(bbox.x0 - pad / 2, bbox.y0 - pad / 2),
        width=bbox.width + pad, height=bbox.height + pad,
        fill=fill, transform=transforms.IdentityTransform(), clip_on=False)
    r.update(props)
    r.draw(renderer)


def draw_bbox(bbox, renderer, color='k', trans=None):
    """
    A debug function to draw a rectangle around the bounding
    box returned by an artist's `.Artist.get_window_extent`
    to test whether the artist is returning the correct bbox.
    """
    r = Rectangle(xy=bbox.p0, width=bbox.width, height=bbox.height,
                  edgecolor=color, fill=False, clip_on=False)
    if trans is not None:
        r.set_transform(trans)
    r.draw(renderer)


class _Style:
    """
    A base class for the Styles. It is meant to be a container class,
    where actual styles are declared as subclass of it, and it
    provides some helper functions.
    """

    def __init_subclass__(cls):
        # Automatically perform docstring interpolation on the subclasses:
        # This allows listing the supported styles via
        # - %(BoxStyle:table)s
        # - %(ConnectionStyle:table)s
        # - %(ArrowStyle:table)s
        # and additionally adding .. ACCEPTS: blocks via
        # - %(BoxStyle:table_and_accepts)s
        # - %(ConnectionStyle:table_and_accepts)s
        # - %(ArrowStyle:table_and_accepts)s
        _docstring.interpd.register(**{
            f"{cls.__name__}:table": cls.pprint_styles(),
            f"{cls.__name__}:table_and_accepts": (
                cls.pprint_styles()
                + "\n\n    .. ACCEPTS: ["
                + "|".join(map(" '{}' ".format, cls._style_list))
                + "]")
        })

    def __new__(cls, stylename, **kwargs):
        """Return the instance of the subclass with the given style name."""
        # The "class" should have the _style_list attribute, which is a mapping
        # of style names to style classes.
        _list = stylename.replace(" ", "").split(",")
        _name = _list[0].lower()
        try:
            _cls = cls._style_list[_name]
        except KeyError as err:
            raise ValueError(f"Unknown style: {stylename!r}") from err
        try:
            _args_pair = [cs.split("=") for cs in _list[1:]]
            _args = {k: float(v) for k, v in _args_pair}
        except ValueError as err:
            raise ValueError(
                f"Incorrect style argument: {stylename!r}") from err
        return _cls(**{**_args, **kwargs})

    @classmethod
    def get_styles(cls):
        """Return a dictionary of available styles."""
        return cls._style_list

    @classmethod
    def pprint_styles(cls):
        """Return the available styles as pretty-printed string."""
        table = [('Class', 'Name', 'Parameters'),
                 *[(cls.__name__,
                    # Add backquotes, as - and | have special meaning in reST.
                    f'``{name}``',
                    # [1:-1] drops the surrounding parentheses.
                    str(inspect.signature(cls))[1:-1] or 'None')
                   for name, cls in cls._style_list.items()]]
        # Convert to rst table.
        col_len = [max(len(cell) for cell in column) for column in zip(*table)]
        table_formatstr = '  '.join('=' * cl for cl in col_len)
        rst_table = '\n'.join([
            '',
            table_formatstr,
            '  '.join(cell.ljust(cl) for cell, cl in zip(table[0], col_len)),
            table_formatstr,
            *['  '.join(cell.ljust(cl) for cell, cl in zip(row, col_len))
              for row in table[1:]],
            table_formatstr,
        ])
        return textwrap.indent(rst_table, prefix=' ' * 4)

    @classmethod
    @_api.deprecated(
        '3.10.0',
        message="This method is never used internally.",
        alternative="No replacement.  Please open an issue if you use this."
    )
    def register(cls, name, style):
        """Register a new style."""
        if not issubclass(style, cls._Base):
            raise ValueError(f"{style} must be a subclass of {cls._Base}")
        cls._style_list[name] = style


def _register_style(style_list, cls=None, *, name=None):
    """Class decorator that stashes a class in a (style) dictionary."""
    if cls is None:
        return functools.partial(_register_style, style_list, name=name)
    style_list[name or cls.__name__.lower()] = cls
    return cls


@_docstring.interpd
class BoxStyle(_Style):
    """
    `BoxStyle` is a container class which defines several
    boxstyle classes, which are used for `FancyBboxPatch`.

    A style object can be created as::

           BoxStyle.Round(pad=0.2)

    or::

           BoxStyle("Round", pad=0.2)

    or::

           BoxStyle("Round, pad=0.2")

    The following boxstyle classes are defined.

    %(BoxStyle:table)s

    An instance of a boxstyle class is a callable object, with the signature ::

       __call__(self, x0, y0, width, height, mutation_size) -> Path

    *x0*, *y0*, *width* and *height* specify the location and size of the box
    to be drawn; *mutation_size* scales the outline properties such as padding.
    """

    _style_list = {}

    @_register_style(_style_list)
    class Square:
        """A square box."""

        def __init__(self, pad=0.3):
            """
            Parameters
            ----------
            pad : float, default: 0.3
                The amount of padding around the original box.
            """
            self.pad = pad

        def __call__(self, x0, y0, width, height, mutation_size):
            pad = mutation_size * self.pad
            # width and height with padding added.
            width, height = width + 2 * pad, height + 2 * pad
            # boundary of the padded box
            x0, y0 = x0 - pad, y0 - pad
            x1, y1 = x0 + width, y0 + height
            return Path._create_closed(
                [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])

    @_register_style(_style_list)
    class Circle:
        """A circular box."""

        def __init__(self, pad=0.3):
            """
            Parameters
            ----------
            pad : float, default: 0.3
                The amount of padding around the original box.
            """
            self.pad = pad

        def __call__(self, x0, y0, width, height, mutation_size):
            pad = mutation_size * self.pad
            width, height = width + 2 * pad, height + 2 * pad
            # boundary of the padded box
            x0, y0 = x0 - pad, y0 - pad
            return Path.circle((x0 + width / 2, y0 + height / 2),
                                max(width, height) / 2)

    @_register_style(_style_list)
    class Ellipse:
        """
        An elliptical box.

        .. versionadded:: 3.7
        """

        def __init__(self, pad=0.3):
            """
            Parameters
            ----------
            pad : float, default: 0.3
                The amount of padding around the original box.
            """
            self.pad = pad

        def __call__(self, x0, y0, width, height, mutation_size):
            pad = mutation_size * self.pad
            width, height = width + 2 * pad, height + 2 * pad
            # boundary of the padded box
            x0, y0 = x0 - pad, y0 - pad
            a = width / math.sqrt(2)
            b = height / math.sqrt(2)
            trans = Affine2D().scale(a, b).translate(x0 + width / 2,
                                                     y0 + height / 2)
            return trans.transform_path(Path.unit_circle())

    @_register_style(_style_list)
    class LArrow:
        """A box in the shape of a left-pointing arrow."""

        def __init__(self, pad=0.3):
            """
            Parameters
            ----------
            pad : float, default: 0.3
                The amount of padding around the original box.
            """
            self.pad = pad

        def __call__(self, x0, y0, width, height, mutation_size):
            # padding
            pad = mutation_size * self.pad
            # width and height with padding added.
            width, height = width + 2 * pad, height + 2 * pad
            # boundary of the padded box
            x0, y0 = x0 - pad, y0 - pad,
            x1, y1 = x0 + width, y0 + height

            dx = (y1 - y0) / 2
            dxx = dx / 2
            x0 = x0 + pad / 1.4  # adjust by ~sqrt(2)

            return Path._create_closed(
                [(x0 + dxx, y0), (x1, y0), (x1, y1), (x0 + dxx, y1),
                 (x0 + dxx, y1 + dxx), (x0 - dx, y0 + dx),
                 (x0 + dxx, y0 - dxx),  # arrow
                 (x0 + dxx, y0)])

    @_register_style(_style_list)
    class RArrow(LArrow):
        """A box in the shape of a right-pointing arrow."""

        def __call__(self, x0, y0, width, height, mutation_size):
            p = BoxStyle.LArrow.__call__(
                self, x0, y0, width, height, mutation_size)
            p.vertices[:, 0] = 2 * x0 + width - p.vertices[:, 0]
            return p

    @_register_style(_style_list)
    class DArrow:
        """A box in the shape of a two-way arrow."""
        # Modified from LArrow to add a right arrow to the bbox.

        def __init__(self, pad=0.3):
            """
            Parameters
            ----------
            pad : float, default: 0.3
                The amount of padding around the original box.
            """
            self.pad = pad

        def __call__(self, x0, y0, width, height, mutation_size):
            # padding
            pad = mutation_size * self.pad
            # width and height with padding added.
            # The width is padded by the arrows, so we don't need to pad it.
            height = height + 2 * pad
            # boundary of the padded box
            x0, y0 = x0 - pad, y0 - pad
            x1, y1 = x0 + width, y0 + height

            dx = (y1 - y0) / 2
            dxx = dx / 2
            x0 = x0 + pad / 1.4  # adjust by ~sqrt(2)

            return Path._create_closed([
                (x0 + dxx, y0), (x1, y0),  # bot-segment
                (x1, y0 - dxx), (x1 + dx + dxx, y0 + dx),
                (x1, y1 + dxx),  # right-arrow
                (x1, y1), (x0 + dxx, y1),  # top-segment
                (x0 + dxx, y1 + dxx), (x0 - dx, y0 + dx),
                (x0 + dxx, y0 - dxx),  # left-arrow
                (x0 + dxx, y0)])

    @_register_style(_style_list)
    class Round:
        """A box with round corners."""

        def __init__(self, pad=0.3, rounding_size=None):
            """
            Parameters
            ----------
            pad : float, default: 0.3
                The amount of padding around the original box.
            rounding_size : float, default: *pad*
                Radius of the corners.
            """
            self.pad = pad
            self.rounding_size = rounding_size

        def __call__(self, x0, y0, width, height, mutation_size):

            # padding
            pad = mutation_size * self.pad

            # size of the rounding corner
            if self.rounding_size:
                dr = mutation_size * self.rounding_size
            else:
                dr = pad

            width, height = width + 2 * pad, height + 2 * pad

            x0, y0 = x0 - pad, y0 - pad,
            x1, y1 = x0 + width, y0 + height

            # Round corners are implemented as quadratic Bezier, e.g.,
            # [(x0, y0-dr), (x0, y0), (x0+dr, y0)] for lower left corner.
            cp = [(x0 + dr, y0),
                  (x1 - dr, y0),
                  (x1, y0), (x1, y0 + dr),
                  (x1, y1 - dr),
                  (x1, y1), (x1 - dr, y1),
                  (x0 + dr, y1),
                  (x0, y1), (x0, y1 - dr),
                  (x0, y0 + dr),
                  (x0, y0), (x0 + dr, y0),
                  (x0 + dr, y0)]

            com = [Path.MOVETO,
                   Path.LINETO,
                   Path.CURVE3, Path.CURVE3,
                   Path.LINETO,
                   Path.CURVE3, Path.CURVE3,
                   Path.LINETO,
                   Path.CURVE3, Path.CURVE3,
                   Path.LINETO,
                   Path.CURVE3, Path.CURVE3,
                   Path.CLOSEPOLY]

            return Path(cp, com)

    @_register_style(_style_list)
    class Round4:
        """A box with rounded edges."""

        def __init__(self, pad=0.3, rounding_size=None):
            """
            Parameters
            ----------
            pad : float, default: 0.3
                The amount of padding around the original box.
            rounding_size : float, default: *pad*/2
                Rounding of edges.
            """
            self.pad = pad
            self.rounding_size = rounding_size

        def __call__(self, x0, y0, width, height, mutation_size):

            # padding
            pad = mutation_size * self.pad

            # Rounding size; defaults to half of the padding.
            if self.rounding_size:
                dr = mutation_size * self.rounding_size
            else:
                dr = pad / 2.

            width = width + 2 * pad - 2 * dr
            height = height + 2 * pad - 2 * dr

            x0, y0 = x0 - pad + dr, y0 - pad + dr,
            x1, y1 = x0 + width, y0 + height

            cp = [(x0, y0),
                  (x0 + dr, y0 - dr), (x1 - dr, y0 - dr), (x1, y0),
                  (x1 + dr, y0 + dr), (x1 + dr, y1 - dr), (x1, y1),
                  (x1 - dr, y1 + dr), (x0 + dr, y1 + dr), (x0, y1),
                  (x0 - dr, y1 - dr), (x0 - dr, y0 + dr), (x0, y0),
                  (x0, y0)]

            com = [Path.MOVETO,
                   Path.CURVE4, Path.CURVE4, Path.CURVE4,
                   Path.CURVE4, Path.CURVE4, Path.CURVE4,
                   Path.CURVE4, Path.CURVE4, Path.CURVE4,
                   Path.CURVE4, Path.CURVE4, Path.CURVE4,
                   Path.CLOSEPOLY]

            return Path(cp, com)

    @_register_style(_style_list)
    class Sawtooth:
        """A box with a sawtooth outline."""

        def __init__(self, pad=0.3, tooth_size=None):
            """
            Parameters
            ----------
            pad : float, default: 0.3
                The amount of padding around the original box.
            tooth_size : float, default: *pad*/2
                Size of the sawtooth.
            """
            self.pad = pad
            self.tooth_size = tooth_size

        def _get_sawtooth_vertices(self, x0, y0, width, height, mutation_size):

            # padding
            pad = mutation_size * self.pad

            # size of sawtooth
            if self.tooth_size is None:
                tooth_size = self.pad * .5 * mutation_size
            else:
                tooth_size = self.tooth_size * mutation_size

            hsz = tooth_size / 2
            width = width + 2 * pad - tooth_size
            height = height + 2 * pad - tooth_size

            # the sizes of the vertical and horizontal sawtooth are
            # separately adjusted to fit the given box size.
            dsx_n = round((width - tooth_size) / (tooth_size * 2)) * 2
            dsy_n = round((height - tooth_size) / (tooth_size * 2)) * 2

            x0, y0 = x0 - pad + hsz, y0 - pad + hsz
            x1, y1 = x0 + width, y0 + height

            xs = [
                x0, *np.linspace(x0 + hsz, x1 - hsz, 2 * dsx_n + 1),  # bottom
                *([x1, x1 + hsz, x1, x1 - hsz] * dsy_n)[:2*dsy_n+2],  # right
                x1, *np.linspace(x1 - hsz, x0 + hsz, 2 * dsx_n + 1),  # top
                *([x0, x0 - hsz, x0, x0 + hsz] * dsy_n)[:2*dsy_n+2],  # left
            ]
            ys = [
                *([y0, y0 - hsz, y0, y0 + hsz] * dsx_n)[:2*dsx_n+2],  # bottom
                y0, *np.linspace(y0 + hsz, y1 - hsz, 2 * dsy_n + 1),  # right
                *([y1, y1 + hsz, y1, y1 - hsz] * dsx_n)[:2*dsx_n+2],  # top
                y1, *np.linspace(y1 - hsz, y0 + hsz, 2 * dsy_n + 1),  # left
            ]

            return [*zip(xs, ys), (xs[0], ys[0])]

        def __call__(self, x0, y0, width, height, mutation_size):
            saw_vertices = self._get_sawtooth_vertices(x0, y0, width,
                                                       height, mutation_size)
            return Path(saw_vertices, closed=True)

    @_register_style(_style_list)
    class Roundtooth(Sawtooth):
        """A box with a rounded sawtooth outline."""

        def __call__(self, x0, y0, width, height, mutation_size):
            saw_vertices = self._get_sawtooth_vertices(x0, y0,
                                                       width, height,
                                                       mutation_size)
            # Add a trailing vertex to allow us to close the polygon correctly
            saw_vertices = np.concatenate([saw_vertices, [saw_vertices[0]]])
            codes = ([Path.MOVETO] +
                     [Path.CURVE3, Path.CURVE3] * ((len(saw_vertices)-1)//2) +
                     [Path.CLOSEPOLY])
            return Path(saw_vertices, codes)


@_docstring.interpd
class ConnectionStyle(_Style):
    """
    `ConnectionStyle` is a container class which defines
    several connectionstyle classes, which is used to create a path
    between two points.  These are mainly used with `FancyArrowPatch`.

    A connectionstyle object can be either created as::

           ConnectionStyle.Arc3(rad=0.2)

    or::

           ConnectionStyle("Arc3", rad=0.2)

    or::

           ConnectionStyle("Arc3, rad=0.2")

    The following classes are defined

    %(ConnectionStyle:table)s

    An instance of any connection style class is a callable object,
    whose call signature is::

        __call__(self, posA, posB,
                 patchA=None, patchB=None,
                 shrinkA=2., shrinkB=2.)

    and it returns a `.Path` instance. *posA* and *posB* are
    tuples of (x, y) coordinates of the two points to be
    connected. *patchA* (or *patchB*) is given, the returned path is
    clipped so that it start (or end) from the boundary of the
    patch. The path is further shrunk by *shrinkA* (or *shrinkB*)
    which is given in points.
    """

    _style_list = {}

    class _Base:
        """
        A base class for connectionstyle classes. The subclass needs
        to implement a *connect* method whose call signature is::

          connect(posA, posB)

        where posA and posB are tuples of x, y coordinates to be
        connected.  The method needs to return a path connecting two
        points. This base class defines a __call__ method, and a few
        helper methods.
        """
        def _in_patch(self, patch):
            """
            Return a predicate function testing whether a point *xy* is
            contained in *patch*.
            """
            return lambda xy: patch.contains(
                SimpleNamespace(x=xy[0], y=xy[1]))[0]

        def _clip(self, path, in_start, in_stop):
            """
            Clip *path* at its start by the region where *in_start* returns
            True, and at its stop by the region where *in_stop* returns True.

            The original path is assumed to start in the *in_start* region and
            to stop in the *in_stop* region.
            """
            if in_start:
                try:
                    _, path = split_path_inout(path, in_start)
                except ValueError:
                    pass
            if in_stop:
                try:
                    path, _ = split_path_inout(path, in_stop)
                except ValueError:
                    pass
            return path

        def __call__(self, posA, posB,
                     shrinkA=2., shrinkB=2., patchA=None, patchB=None):
            """
            Call the *connect* method to create a path between *posA* and
            *posB*; then clip and shrink the path.
            """
            path = self.connect(posA, posB)
            path = self._clip(
                path,
                self._in_patch(patchA) if patchA else None,
                self._in_patch(patchB) if patchB else None,
            )
            path = self._clip(
                path,
                inside_circle(*path.vertices[0], shrinkA) if shrinkA else None,
                inside_circle(*path.vertices[-1], shrinkB) if shrinkB else None
            )
            return path

    @_register_style(_style_list)
    class Arc3(_Base):
        """
        Creates a simple quadratic Bézier curve between two
        points. The curve is created so that the middle control point
        (C1) is located at the same distance from the start (C0) and
        end points(C2) and the distance of the C1 to the line
        connecting C0-C2 is *rad* times the distance of C0-C2.
        """

        def __init__(self, rad=0.):
            """
            Parameters
            ----------
            rad : float
              Curvature of the curve.
            """
            self.rad = rad

        def connect(self, posA, posB):
            x1, y1 = posA
            x2, y2 = posB
            x12, y12 = (x1 + x2) / 2., (y1 + y2) / 2.
            dx, dy = x2 - x1, y2 - y1

            f = self.rad

            cx, cy = x12 + f * dy, y12 - f * dx

            vertices = [(x1, y1),
                        (cx, cy),
                        (x2, y2)]
            codes = [Path.MOVETO,
                     Path.CURVE3,
                     Path.CURVE3]

            return Path(vertices, codes)

    @_register_style(_style_list)
    class Angle3(_Base):
        """
        Creates a simple quadratic Bézier curve between two points. The middle
        control point is placed at the intersecting point of two lines which
        cross the start and end point, and have a slope of *angleA* and
        *angleB*, respectively.
        """

        def __init__(self, angleA=90, angleB=0):
            """
            Parameters
            ----------
            angleA : float
              Starting angle of the path.

            angleB : float
              Ending angle of the path.
            """

            self.angleA = angleA
            self.angleB = angleB

        def connect(self, posA, posB):
            x1, y1 = posA
            x2, y2 = posB

            cosA = math.cos(math.radians(self.angleA))
            sinA = math.sin(math.radians(self.angleA))
            cosB = math.cos(math.radians(self.angleB))
            sinB = math.sin(math.radians(self.angleB))

            cx, cy = get_intersection(x1, y1, cosA, sinA,
                                      x2, y2, cosB, sinB)

            vertices = [(x1, y1), (cx, cy), (x2, y2)]
            codes = [Path.MOVETO, Path.CURVE3, Path.CURVE3]

            return Path(vertices, codes)

    @_register_style(_style_list)
    class Angle(_Base):
        """
        Creates a piecewise continuous quadratic Bézier path between two
        points. The path has a one passing-through point placed at the
        intersecting point of two lines which cross the start and end point,
        and have a slope of *angleA* and *angleB*, respectively.
        The connecting edges are rounded with *rad*.
        """

        def __init__(self, angleA=90, angleB=0, rad=0.):
            """
            Parameters
            ----------
            angleA : float
              Starting angle of the path.

            angleB : float
              Ending angle of the path.

            rad : float
              Rounding radius of the edge.
            """

            self.angleA = angleA
            self.angleB = angleB

            self.rad = rad

        def connect(self, posA, posB):
            x1, y1 = posA
            x2, y2 = posB

            cosA = math.cos(math.radians(self.angleA))
            sinA = math.sin(math.radians(self.angleA))
            cosB = math.cos(math.radians(self.angleB))
            sinB = math.sin(math.radians(self.angleB))

            cx, cy = get_intersection(x1, y1, cosA, sinA,
                                      x2, y2, cosB, sinB)

            vertices = [(x1, y1)]
            codes = [Path.MOVETO]

            if self.rad == 0.:
                vertices.append((cx, cy))
                codes.append(Path.LINETO)
            else:
                dx1, dy1 = x1 - cx, y1 - cy
                d1 = np.hypot(dx1, dy1)
                f1 = self.rad / d1
                dx2, dy2 = x2 - cx, y2 - cy
                d2 = np.hypot(dx2, dy2)
                f2 = self.rad / d2
                vertices.extend([(cx + dx1 * f1, cy + dy1 * f1),
                                 (cx, cy),
                                 (cx + dx2 * f2, cy + dy2 * f2)])
                codes.extend([Path.LINETO, Path.CURVE3, Path.CURVE3])

            vertices.append((x2, y2))
            codes.append(Path.LINETO)

            return Path(vertices, codes)

    @_register_style(_style_list)
    class Arc(_Base):
        """
        Creates a piecewise continuous quadratic Bézier path between two
        points. The path can have two passing-through points, a
        point placed at the distance of *armA* and angle of *angleA* from
        point A, another point with respect to point B. The edges are
        rounded with *rad*.
        """

        def __init__(self, angleA=0, angleB=0, armA=None, armB=None, rad=0.):
            """
            Parameters
            ----------
            angleA : float
              Starting angle of the path.

            angleB : float
              Ending angle of the path.

            armA : float or None
              Length of the starting arm.

            armB : float or None
              Length of the ending arm.

            rad : float
              Rounding radius of the edges.
            """

            self.angleA = angleA
            self.angleB = angleB
            self.armA = armA
            self.armB = armB

            self.rad = rad

        def connect(self, posA, posB):
            x1, y1 = posA
            x2, y2 = posB

            vertices = [(x1, y1)]
            rounded = []
            codes = [Path.MOVETO]

            if self.armA:
                cosA = math.cos(math.radians(self.angleA))
                sinA = math.sin(math.radians(self.angleA))
                # x_armA, y_armB
                d = self.armA - self.rad
                rounded.append((x1 + d * cosA, y1 + d * sinA))
                d = self.armA
                rounded.append((x1 + d * cosA, y1 + d * sinA))

            if self.armB:
                cosB = math.cos(math.radians(self.angleB))
                sinB = math.sin(math.radians(self.angleB))
                x_armB, y_armB = x2 + self.armB * cosB, y2 + self.armB * sinB

                if rounded:
                    xp, yp = rounded[-1]
                    dx, dy = x_armB - xp, y_armB - yp
                    dd = (dx * dx + dy * dy) ** .5

                    rounded.append((xp + self.rad * dx / dd,
                                    yp + self.rad * dy / dd))
                    vertices.extend(rounded)
                    codes.extend([Path.LINETO,
                                  Path.CURVE3,
                                  Path.CURVE3])
                else:
                    xp, yp = vertices[-1]
                    dx, dy = x_armB - xp, y_armB - yp
                    dd = (dx * dx + dy * dy) ** .5

                d = dd - self.rad
                rounded = [(xp + d * dx / dd, yp + d * dy / dd),
                           (x_armB, y_armB)]

            if rounded:
                xp, yp = rounded[-1]
                dx, dy = x2 - xp, y2 - yp
                dd = (dx * dx + dy * dy) ** .5

                rounded.append((xp + self.rad * dx / dd,
                                yp + self.rad * dy / dd))
                vertices.extend(rounded)
                codes.extend([Path.LINETO,
                              Path.CURVE3,
                              Path.CURVE3])

            vertices.append((x2, y2))
            codes.append(Path.LINETO)

            return Path(vertices, codes)

    @_register_style(_style_list)
    class Bar(_Base):
        """
        A line with *angle* between A and B with *armA* and *armB*. One of the
        arms is extended so that they are connected in a right angle. The
        length of *armA* is determined by (*armA* + *fraction* x AB distance).
        Same for *armB*.
        """

        def __init__(self, armA=0., armB=0., fraction=0.3, angle=None):
            """
            Parameters
            ----------
            armA : float
                Minimum length of armA.

            armB : float
                Minimum length of armB.

            fraction : float
                A fraction of the distance between two points that will be
                added to armA and armB.

            angle : float or None
                Angle of the connecting line (if None, parallel to A and B).
            """
            self.armA = armA
            self.armB = armB
            self.fraction = fraction
            self.angle = angle

        def connect(self, posA, posB):
            x1, y1 = posA
            x20, y20 = x2, y2 = posB

            theta1 = math.atan2(y2 - y1, x2 - x1)
            dx, dy = x2 - x1, y2 - y1
            dd = (dx * dx + dy * dy) ** .5
            ddx, ddy = dx / dd, dy / dd

            armA, armB = self.armA, self.armB

            if self.angle is not None:
                theta0 = np.deg2rad(self.angle)
                dtheta = theta1 - theta0
                dl = dd * math.sin(dtheta)
                dL = dd * math.cos(dtheta)
                x2, y2 = x1 + dL * math.cos(theta0), y1 + dL * math.sin(theta0)
                armB = armB - dl

                # update
                dx, dy = x2 - x1, y2 - y1
                dd2 = (dx * dx + dy * dy) ** .5
                ddx, ddy = dx / dd2, dy / dd2

            arm = max(armA, armB)
            f = self.fraction * dd + arm

            cx1, cy1 = x1 + f * ddy, y1 - f * ddx
            cx2, cy2 = x2 + f * ddy, y2 - f * ddx

            vertices = [(x1, y1),
                        (cx1, cy1),
                        (cx2, cy2),
                        (x20, y20)]
            codes = [Path.MOVETO,
                     Path.LINETO,
                     Path.LINETO,
                     Path.LINETO]

            return Path(vertices, codes)


def _point_along_a_line(x0, y0, x1, y1, d):
    """
    Return the point on the line connecting (*x0*, *y0*) -- (*x1*, *y1*) whose
    distance from (*x0*, *y0*) is *d*.
    """
    dx, dy = x0 - x1, y0 - y1
    ff = d / (dx * dx + dy * dy) ** .5
    x2, y2 = x0 - ff * dx, y0 - ff * dy

    return x2, y2


@_docstring.interpd
class ArrowStyle(_Style):
    """
    `ArrowStyle` is a container class which defines several
    arrowstyle classes, which is used to create an arrow path along a
    given path.  These are mainly used with `FancyArrowPatch`.

    An arrowstyle object can be either created as::

           ArrowStyle.Fancy(head_length=.4, head_width=.4, tail_width=.4)

    or::

           ArrowStyle("Fancy", head_length=.4, head_width=.4, tail_width=.4)

    or::

           ArrowStyle("Fancy, head_length=.4, head_width=.4, tail_width=.4")

    The following classes are defined

    %(ArrowStyle:table)s

    For an overview of the visual appearance, see
    :doc:`/gallery/text_labels_and_annotations/fancyarrow_demo`.

    An instance of any arrow style class is a callable object,
    whose call signature is::

        __call__(self, path, mutation_size, linewidth, aspect_ratio=1.)

    and it returns a tuple of a `.Path` instance and a boolean
    value. *path* is a `.Path` instance along which the arrow
    will be drawn. *mutation_size* and *aspect_ratio* have the same
    meaning as in `BoxStyle`. *linewidth* is a line width to be
    stroked. This is meant to be used to correct the location of the
    head so that it does not overshoot the destination point, but not all
    classes support it.

    Notes
    -----
    *angleA* and *angleB* specify the orientation of the bracket, as either a
    clockwise or counterclockwise angle depending on the arrow type. 0 degrees
    means perpendicular to the line connecting the arrow's head and tail.

    .. plot:: gallery/text_labels_and_annotations/angles_on_bracket_arrows.py
    """

    _style_list = {}

    class _Base:
        """
        Arrow Transmuter Base class

        ArrowTransmuterBase and its derivatives are used to make a fancy
        arrow around a given path. The __call__ method returns a path
        (which will be used to create a PathPatch instance) and a boolean
        value indicating the path is open therefore is not fillable.  This
        class is not an artist and actual drawing of the fancy arrow is
        done by the FancyArrowPatch class.
        """

        # The derived classes are required to be able to be initialized
        # w/o arguments, i.e., all its argument (except self) must have
        # the default values.

        @staticmethod
        def ensure_quadratic_bezier(path):
            """
            Some ArrowStyle classes only works with a simple quadratic
            Bézier curve (created with `.ConnectionStyle.Arc3` or
            `.ConnectionStyle.Angle3`). This static method checks if the
            provided path is a simple quadratic Bézier curve and returns its
            control points if true.
            """
            segments = list(path.iter_segments())
            if (len(segments) != 2 or segments[0][1] != Path.MOVETO or
                    segments[1][1] != Path.CURVE3):
                raise ValueError(
                    "'path' is not a valid quadratic Bezier curve")
            return [*segments[0][0], *segments[1][0]]

        def transmute(self, path, mutation_size, linewidth):
            """
            The transmute method is the very core of the ArrowStyle class and
            must be overridden in the subclasses. It receives the *path*
            object along which the arrow will be drawn, and the
            *mutation_size*, with which the arrow head etc. will be scaled.
            The *linewidth* may be used to adjust the path so that it does not
            pass beyond the given points. It returns a tuple of a `.Path`
            instance and a boolean. The boolean value indicate whether the
            path can be filled or not. The return value can also be a list of
            paths and list of booleans of the same length.
            """
            raise NotImplementedError('Derived must override')

        def __call__(self, path, mutation_size, linewidth,
                     aspect_ratio=1.):
            """
            The __call__ method is a thin wrapper around the transmute method
            and takes care of the aspect ratio.
            """

            if aspect_ratio is not None:
                # Squeeze the given height by the aspect_ratio
                vertices = path.vertices / [1, aspect_ratio]
                path_shrunk = Path(vertices, path.codes)
                # call transmute method with squeezed height.
                path_mutated, fillable = self.transmute(path_shrunk,
                                                        mutation_size,
                                                        linewidth)
                if np.iterable(fillable):
                    # Restore the height
                    path_list = [Path(p.vertices * [1, aspect_ratio], p.codes)
                                 for p in path_mutated]
                    return path_list, fillable
                else:
                    return path_mutated, fillable
            else:
                return self.transmute(path, mutation_size, linewidth)

    class _Curve(_Base):
        """
        A simple arrow which will work with any path instance. The
        returned path is the concatenation of the original path, and at
        most two paths representing the arrow head or bracket at the start
        point and at the end point. The arrow heads can be either open
        or closed.
        """

        arrow = "-"
        fillbegin = fillend = False  # Whether arrows are filled.

        def __init__(self, head_length=.4, head_width=.2, widthA=1., widthB=1.,
                     lengthA=0.2, lengthB=0.2, angleA=0, angleB=0, scaleA=None,
                     scaleB=None):
            """
            Parameters
            ----------
            head_length : float, default: 0.4
                Length of the arrow head, relative to *mutation_size*.
            head_width : float, default: 0.2
                Width of the arrow head, relative to *mutation_size*.
            widthA, widthB : float, default: 1.0
                Width of the bracket.
            lengthA, lengthB : float, default: 0.2
                Length of the bracket.
            angleA, angleB : float, default: 0
                Orientation of the bracket, as a counterclockwise angle.
                0 degrees means perpendicular to the line.
            scaleA, scaleB : float, default: *mutation_size*
                The scale of the brackets.
            """

            self.head_length, self.head_width = head_length, head_width
            self.widthA, self.widthB = widthA, widthB
            self.lengthA, self.lengthB = lengthA, lengthB
            self.angleA, self.angleB = angleA, angleB
            self.scaleA, self.scaleB = scaleA, scaleB

            self._beginarrow_head = False
            self._beginarrow_bracket = False
            self._endarrow_head = False
            self._endarrow_bracket = False

            if "-" not in self.arrow:
                raise ValueError("arrow must have the '-' between "
                                 "the two heads")

            beginarrow, endarrow = self.arrow.split("-", 1)

            if beginarrow == "<":
                self._beginarrow_head = True
                self._beginarrow_bracket = False
            elif beginarrow == "<|":
                self._beginarrow_head = True
                self._beginarrow_bracket = False
                self.fillbegin = True
            elif beginarrow in ("]", "|"):
                self._beginarrow_head = False
                self._beginarrow_bracket = True

            if endarrow == ">":
                self._endarrow_head = True
                self._endarrow_bracket = False
            elif endarrow == "|>":
                self._endarrow_head = True
                self._endarrow_bracket = False
                self.fillend = True
            elif endarrow in ("[", "|"):
                self._endarrow_head = False
                self._endarrow_bracket = True

            super().__init__()

        def _get_arrow_wedge(self, x0, y0, x1, y1,
                             head_dist, cos_t, sin_t, linewidth):
            """
            Return the paths for arrow heads. Since arrow lines are
            drawn with capstyle=projected, The arrow goes beyond the
            desired point. This method also returns the amount of the path
            to be shrunken so that it does not overshoot.
            """

            # arrow from x0, y0 to x1, y1
            dx, dy = x0 - x1, y0 - y1

            cp_distance = np.hypot(dx, dy)

            # pad_projected : amount of pad to account the
            # overshooting of the projection of the wedge
            pad_projected = (.5 * linewidth / sin_t)

            # Account for division by zero
            if cp_distance == 0:
                cp_distance = 1

            # apply pad for projected edge
            ddx = pad_projected * dx / cp_distance
            ddy = pad_projected * dy / cp_distance

            # offset for arrow wedge
            dx = dx / cp_distance * head_dist
            dy = dy / cp_distance * head_dist

            dx1, dy1 = cos_t * dx + sin_t * dy, -sin_t * dx + cos_t * dy
            dx2, dy2 = cos_t * dx - sin_t * dy, sin_t * dx + cos_t * dy

            vertices_arrow = [(x1 + ddx + dx1, y1 + ddy + dy1),
                              (x1 + ddx, y1 + ddy),
                              (x1 + ddx + dx2, y1 + ddy + dy2)]
            codes_arrow = [Path.MOVETO,
                           Path.LINETO,
                           Path.LINETO]

            return vertices_arrow, codes_arrow, ddx, ddy

        def _get_bracket(self, x0, y0,
                         x1, y1, width, length, angle):

            cos_t, sin_t = get_cos_sin(x1, y1, x0, y0)

            # arrow from x0, y0 to x1, y1
            from matplotlib.bezier import get_normal_points
            x1, y1, x2, y2 = get_normal_points(x0, y0, cos_t, sin_t, width)

            dx, dy = length * cos_t, length * sin_t

            vertices_arrow = [(x1 + dx, y1 + dy),
                              (x1, y1),
                              (x2, y2),
                              (x2 + dx, y2 + dy)]
            codes_arrow = [Path.MOVETO,
                           Path.LINETO,
                           Path.LINETO,
                           Path.LINETO]

            if angle:
                trans = transforms.Affine2D().rotate_deg_around(x0, y0, angle)
                vertices_arrow = trans.transform(vertices_arrow)

            return vertices_arrow, codes_arrow

        def transmute(self, path, mutation_size, linewidth):
            # docstring inherited
            if self._beginarrow_head or self._endarrow_head:
                head_length = self.head_length * mutation_size
                head_width = self.head_width * mutation_size
                head_dist = np.hypot(head_length, head_width)
                cos_t, sin_t = head_length / head_dist, head_width / head_dist

            scaleA = mutation_size if self.scaleA is None else self.scaleA
            scaleB = mutation_size if self.scaleB is None else self.scaleB

            # begin arrow
            x0, y0 = path.vertices[0]
            x1, y1 = path.vertices[1]

            # If there is no room for an arrow and a line, then skip the arrow
            has_begin_arrow = self._beginarrow_head and (x0, y0) != (x1, y1)
            verticesA, codesA, ddxA, ddyA = (
                self._get_arrow_wedge(x1, y1, x0, y0,
                                      head_dist, cos_t, sin_t, linewidth)
                if has_begin_arrow
                else ([], [], 0, 0)
            )

            # end arrow
            x2, y2 = path.vertices[-2]
            x3, y3 = path.vertices[-1]

            # If there is no room for an arrow and a line, then skip the arrow
            has_end_arrow = self._endarrow_head and (x2, y2) != (x3, y3)
            verticesB, codesB, ddxB, ddyB = (
                self._get_arrow_wedge(x2, y2, x3, y3,
                                      head_dist, cos_t, sin_t, linewidth)
                if has_end_arrow
                else ([], [], 0, 0)
            )

            # This simple code will not work if ddx, ddy is greater than the
            # separation between vertices.
            paths = [Path(np.concatenate([[(x0 + ddxA, y0 + ddyA)],
                                          path.vertices[1:-1],
                                          [(x3 + ddxB, y3 + ddyB)]]),
                          path.codes)]
            fills = [False]

            if has_begin_arrow:
                if self.fillbegin:
                    paths.append(
                        Path([*verticesA, (0, 0)], [*codesA, Path.CLOSEPOLY]))
                    fills.append(True)
                else:
                    paths.append(Path(verticesA, codesA))
                    fills.append(False)
            elif self._beginarrow_bracket:
                x0, y0 = path.vertices[0]
                x1, y1 = path.vertices[1]
                verticesA, codesA = self._get_bracket(x0, y0, x1, y1,
                                                      self.widthA * scaleA,
                                                      self.lengthA * scaleA,
                                                      self.angleA)

                paths.append(Path(verticesA, codesA))
                fills.append(False)

            if has_end_arrow:
                if self.fillend:
                    fills.append(True)
                    paths.append(
                        Path([*verticesB, (0, 0)], [*codesB, Path.CLOSEPOLY]))
                else:
                    fills.append(False)
                    paths.append(Path(verticesB, codesB))
            elif self._endarrow_bracket:
                x0, y0 = path.vertices[-1]
                x1, y1 = path.vertices[-2]
                verticesB, codesB = self._get_bracket(x0, y0, x1, y1,
                                                      self.widthB * scaleB,
                                                      self.lengthB * scaleB,
                                                      self.angleB)

                paths.append(Path(verticesB, codesB))
                fills.append(False)

            return paths, fills

    @_register_style(_style_list, name="-")
    class Curve(_Curve):
        """A simple curve without any arrow head."""

        def __init__(self):  # hide head_length, head_width
            # These attributes (whose values come from backcompat) only matter
            # if someone modifies beginarrow/etc. on an ArrowStyle instance.
            super().__init__(head_length=.2, head_width=.1)

    @_register_style(_style_list, name="<-")
    class CurveA(_Curve):
        """An arrow with a head at its start point."""
        arrow = "<-"

    @_register_style(_style_list, name="->")
    class CurveB(_Curve):
        """An arrow with a head at its end point."""
        arrow = "->"

    @_register_style(_style_list, name="<->")
    class CurveAB(_Curve):
        """An arrow with heads both at the start and the end point."""
        arrow = "<->"

    @_register_style(_style_list, name="<|-")
    class CurveFilledA(_Curve):
        """An arrow with filled triangle head at the start."""
        arrow = "<|-"

    @_register_style(_style_list, name="-|>")
    class CurveFilledB(_Curve):
        """An arrow with filled triangle head at the end."""
        arrow = "-|>"

    @_register_style(_style_list, name="<|-|>")
    class CurveFilledAB(_Curve):
        """An arrow with filled triangle heads at both ends."""
        arrow = "<|-|>"

    @_register_style(_style_list, name="]-")
    class BracketA(_Curve):
        """An arrow with an outward square bracket at its start."""
        arrow = "]-"

        def __init__(self, widthA=1., lengthA=0.2, angleA=0):
            """
            Parameters
            ----------
            widthA : float, default: 1.0
                Width of the bracket.
            lengthA : float, default: 0.2
                Length of the bracket.
            angleA : float, default: 0 degrees
                Orientation of the bracket, as a counterclockwise angle.
                0 degrees means perpendicular to the line.
            """
            super().__init__(widthA=widthA, lengthA=lengthA, angleA=angleA)

    @_register_style(_style_list, name="-[")
    class BracketB(_Curve):
        """An arrow with an outward square bracket at its end."""
        arrow = "-["

        def __init__(self, widthB=1., lengthB=0.2, angleB=0):
            """
            Parameters
            ----------
            widthB : float, default: 1.0
                Width of the bracket.
            lengthB : float, default: 0.2
                Length of the bracket.
            angleB : float, default: 0 degrees
                Orientation of the bracket, as a counterclockwise angle.
                0 degrees means perpendicular to the line.
            """
            super().__init__(widthB=widthB, lengthB=lengthB, angleB=angleB)

    @_register_style(_style_list, name="]-[")
    class BracketAB(_Curve):
        """An arrow with outward square brackets at both ends."""
        arrow = "]-["

        def __init__(self,
                     widthA=1., lengthA=0.2, angleA=0,
                     widthB=1., lengthB=0.2, angleB=0):
            """
            Parameters
            ----------
            widthA, widthB : float, default: 1.0
                Width of the bracket.
            lengthA, lengthB : float, default: 0.2
                Length of the bracket.
            angleA, angleB : float, default: 0 degrees
                Orientation of the bracket, as a counterclockwise angle.
                0 degrees means perpendicular to the line.
            """
            super().__init__(widthA=widthA, lengthA=lengthA, angleA=angleA,
                             widthB=widthB, lengthB=lengthB, angleB=angleB)

    @_register_style(_style_list, name="|-|")
    class BarAB(_Curve):
        """An arrow with vertical bars ``|`` at both ends."""
        arrow = "|-|"

        def __init__(self, widthA=1., angleA=0, widthB=1., angleB=0):
            """
            Parameters
            ----------
            widthA, widthB : float, default: 1.0
                Width of the bracket.
            angleA, angleB : float, default: 0 degrees
                Orientation of the bracket, as a counterclockwise angle.
                0 degrees means perpendicular to the line.
            """
            super().__init__(widthA=widthA, lengthA=0, angleA=angleA,
                             widthB=widthB, lengthB=0, angleB=angleB)

    @_register_style(_style_list, name=']->')
    class BracketCurve(_Curve):
        """
        An arrow with an outward square bracket at its start and a head at
        the end.
        """
        arrow = "]->"

        def __init__(self, widthA=1., lengthA=0.2, angleA=None):
            """
            Parameters
            ----------
            widthA : float, default: 1.0
                Width of the bracket.
            lengthA : float, default: 0.2
                Length of the bracket.
            angleA : float, default: 0 degrees
                Orientation of the bracket, as a counterclockwise angle.
                0 degrees means perpendicular to the line.
            """
            super().__init__(widthA=widthA, lengthA=lengthA, angleA=angleA)

    @_register_style(_style_list, name='<-[')
    class CurveBracket(_Curve):
        """
        An arrow with an outward square bracket at its end and a head at
        the start.
        """
        arrow = "<-["

        def __init__(self, widthB=1., lengthB=0.2, angleB=None):
            """
            Parameters
            ----------
            widthB : float, default: 1.0
                Width of the bracket.
            lengthB : float, default: 0.2
                Length of the bracket.
            angleB : float, default: 0 degrees
                Orientation of the bracket, as a counterclockwise angle.
                0 degrees means perpendicular to the line.
            """
            super().__init__(widthB=widthB, lengthB=lengthB, angleB=angleB)

    @_register_style(_style_list)
    class Simple(_Base):
        """A simple arrow. Only works with a quadratic Bézier curve."""

        def __init__(self, head_length=.5, head_width=.5, tail_width=.2):
            """
            Parameters
            ----------
            head_length : float, default: 0.5
                Length of the arrow head.

            head_width : float, default: 0.5
                Width of the arrow head.

            tail_width : float, default: 0.2
                Width of the arrow tail.
            """
            self.head_length, self.head_width, self.tail_width = \
                head_length, head_width, tail_width
            super().__init__()

        def transmute(self, path, mutation_size, linewidth):
            # docstring inherited
            x0, y0, x1, y1, x2, y2 = self.ensure_quadratic_bezier(path)

            # divide the path into a head and a tail
            head_length = self.head_length * mutation_size
            in_f = inside_circle(x2, y2, head_length)
            arrow_path = [(x0, y0), (x1, y1), (x2, y2)]

            try:
                arrow_out, arrow_in = \
                    split_bezier_intersecting_with_closedpath(arrow_path, in_f)
            except NonIntersectingPathException:
                # if this happens, make a straight line of the head_length
                # long.
                x0, y0 = _point_along_a_line(x2, y2, x1, y1, head_length)
                x1n, y1n = 0.5 * (x0 + x2), 0.5 * (y0 + y2)
                arrow_in = [(x0, y0), (x1n, y1n), (x2, y2)]
                arrow_out = None

            # head
            head_width = self.head_width * mutation_size
            head_left, head_right = make_wedged_bezier2(arrow_in,
                                                        head_width / 2., wm=.5)

            # tail
            if arrow_out is not None:
                tail_width = self.tail_width * mutation_size
                tail_left, tail_right = get_parallels(arrow_out,
                                                      tail_width / 2.)

                patch_path = [(Path.MOVETO, tail_right[0]),
                              (Path.CURVE3, tail_right[1]),
                              (Path.CURVE3, tail_right[2]),
                              (Path.LINETO, head_right[0]),
                              (Path.CURVE3, head_right[1]),
                              (Path.CURVE3, head_right[2]),
                              (Path.CURVE3, head_left[1]),
                              (Path.CURVE3, head_left[0]),
                              (Path.LINETO, tail_left[2]),
                              (Path.CURVE3, tail_left[1]),
                              (Path.CURVE3, tail_left[0]),
                              (Path.LINETO, tail_right[0]),
                              (Path.CLOSEPOLY, tail_right[0]),
                              ]
            else:
                patch_path = [(Path.MOVETO, head_right[0]),
                              (Path.CURVE3, head_right[1]),
                              (Path.CURVE3, head_right[2]),
                              (Path.CURVE3, head_left[1]),
                              (Path.CURVE3, head_left[0]),
                              (Path.CLOSEPOLY, head_left[0]),
                              ]

            path = Path([p for c, p in patch_path], [c for c, p in patch_path])

            return path, True

    @_register_style(_style_list)
    class Fancy(_Base):
        """A fancy arrow. Only works with a quadratic Bézier curve."""

        def __init__(self, head_length=.4, head_width=.4, tail_width=.4):
            """
            Parameters
            ----------
            head_length : float, default: 0.4
                Length of the arrow head.

            head_width : float, default: 0.4
                Width of the arrow head.

            tail_width : float, default: 0.4
                Width of the arrow tail.
            """
            self.head_length, self.head_width, self.tail_width = \
                head_length, head_width, tail_width
            super().__init__()

        def transmute(self, path, mutation_size, linewidth):
            # docstring inherited
            x0, y0, x1, y1, x2, y2 = self.ensure_quadratic_bezier(path)

            # divide the path into a head and a tail
            head_length = self.head_length * mutation_size
            arrow_path = [(x0, y0), (x1, y1), (x2, y2)]

            # path for head
            in_f = inside_circle(x2, y2, head_length)
            try:
                path_out, path_in = split_bezier_intersecting_with_closedpath(
                    arrow_path, in_f)
            except NonIntersectingPathException:
                # if this happens, make a straight line of the head_length
                # long.
                x0, y0 = _point_along_a_line(x2, y2, x1, y1, head_length)
                x1n, y1n = 0.5 * (x0 + x2), 0.5 * (y0 + y2)
                arrow_path = [(x0, y0), (x1n, y1n), (x2, y2)]
                path_head = arrow_path
            else:
                path_head = path_in

            # path for head
            in_f = inside_circle(x2, y2, head_length * .8)
            path_out, path_in = split_bezier_intersecting_with_closedpath(
                arrow_path, in_f)
            path_tail = path_out

            # head
            head_width = self.head_width * mutation_size
            head_l, head_r = make_wedged_bezier2(path_head,
                                                 head_width / 2.,
                                                 wm=.6)

            # tail
            tail_width = self.tail_width * mutation_size
            tail_left, tail_right = make_wedged_bezier2(path_tail,
                                                        tail_width * .5,
                                                        w1=1., wm=0.6, w2=0.3)

            # path for head
            in_f = inside_circle(x0, y0, tail_width * .3)
            path_in, path_out = split_bezier_intersecting_with_closedpath(
                arrow_path, in_f)
            tail_start = path_in[-1]

            head_right, head_left = head_r, head_l
            patch_path = [(Path.MOVETO, tail_start),
                          (Path.LINETO, tail_right[0]),
                          (Path.CURVE3, tail_right[1]),
                          (Path.CURVE3, tail_right[2]),
                          (Path.LINETO, head_right[0]),
                          (Path.CURVE3, head_right[1]),
                          (Path.CURVE3, head_right[2]),
                          (Path.CURVE3, head_left[1]),
                          (Path.CURVE3, head_left[0]),
                          (Path.LINETO, tail_left[2]),
                          (Path.CURVE3, tail_left[1]),
                          (Path.CURVE3, tail_left[0]),
                          (Path.LINETO, tail_start),
                          (Path.CLOSEPOLY, tail_start),
                          ]
            path = Path([p for c, p in patch_path], [c for c, p in patch_path])

            return path, True

    @_register_style(_style_list)
    class Wedge(_Base):
        """
        Wedge(?) shape. Only works with a quadratic Bézier curve.  The
        start point has a width of the *tail_width* and the end point has a
        width of 0. At the middle, the width is *shrink_factor*x*tail_width*.
        """

        def __init__(self, tail_width=.3, shrink_factor=0.5):
            """
            Parameters
            ----------
            tail_width : float, default: 0.3
                Width of the tail.

            shrink_factor : float, default: 0.5
                Fraction of the arrow width at the middle point.
            """
            self.tail_width = tail_width
            self.shrink_factor = shrink_factor
            super().__init__()

        def transmute(self, path, mutation_size, linewidth):
            # docstring inherited
            x0, y0, x1, y1, x2, y2 = self.ensure_quadratic_bezier(path)

            arrow_path = [(x0, y0), (x1, y1), (x2, y2)]
            b_plus, b_minus = make_wedged_bezier2(
                                    arrow_path,
                                    self.tail_width * mutation_size / 2.,
                                    wm=self.shrink_factor)

            patch_path = [(Path.MOVETO, b_plus[0]),
                          (Path.CURVE3, b_plus[1]),
                          (Path.CURVE3, b_plus[2]),
                          (Path.LINETO, b_minus[2]),
                          (Path.CURVE3, b_minus[1]),
                          (Path.CURVE3, b_minus[0]),
                          (Path.CLOSEPOLY, b_minus[0]),
                          ]
            path = Path([p for c, p in patch_path], [c for c, p in patch_path])

            return path, True


class FancyBboxPatch(Patch):
    """
    A fancy box around a rectangle with lower left at *xy* = (*x*, *y*)
    with specified width and height.

    `.FancyBboxPatch` is similar to `.Rectangle`, but it draws a fancy box
    around the rectangle. The transformation of the rectangle box to the
    fancy box is delegated to the style classes defined in `.BoxStyle`.
    """

    _edge_default = True

    def __str__(self):
        s = self.__class__.__name__ + "((%g, %g), width=%g, height=%g)"
        return s % (self._x, self._y, self._width, self._height)

    @_docstring.interpd
    def __init__(self, xy, width, height, boxstyle="round", *,
                 mutation_scale=1, mutation_aspect=1, **kwargs):
        """
        Parameters
        ----------
        xy : (float, float)
          The lower left corner of the box.

        width : float
            The width of the box.

        height : float
            The height of the box.

        boxstyle : str or `~matplotlib.patches.BoxStyle`
            The style of the fancy box. This can either be a `.BoxStyle`
            instance or a string of the style name and optionally comma
            separated attributes (e.g. "Round, pad=0.2"). This string is
            passed to `.BoxStyle` to construct a `.BoxStyle` object. See
            there for a full documentation.

            The following box styles are available:

            %(BoxStyle:table)s

        mutation_scale : float, default: 1
            Scaling factor applied to the attributes of the box style
            (e.g. pad or rounding_size).

        mutation_aspect : float, default: 1
            The height of the rectangle will be squeezed by this value before
            the mutation and the mutated box will be stretched by the inverse
            of it. For example, this allows different horizontal and vertical
            padding.

        Other Parameters
        ----------------
        **kwargs : `~matplotlib.patches.Patch` properties

        %(Patch:kwdoc)s
        """

        super().__init__(**kwargs)
        self._x, self._y = xy
        self._width = width
        self._height = height
        self.set_boxstyle(boxstyle)
        self._mutation_scale = mutation_scale
        self._mutation_aspect = mutation_aspect
        self.stale = True

    @_docstring.interpd
    def set_boxstyle(self, boxstyle=None, **kwargs):
        """
        Set the box style, possibly with further attributes.

        Attributes from the previous box style are not reused.

        Without argument (or with ``boxstyle=None``), the available box styles
        are returned as a human-readable string.

        Parameters
        ----------
        boxstyle : str or `~matplotlib.patches.BoxStyle`
            The style of the box: either a `.BoxStyle` instance, or a string,
            which is the style name and optionally comma separated attributes
            (e.g. "Round,pad=0.2"). Such a string is used to construct a
            `.BoxStyle` object, as documented in that class.

            The following box styles are available:

            %(BoxStyle:table_and_accepts)s

        **kwargs
            Additional attributes for the box style. See the table above for
            supported parameters.

        Examples
        --------
        ::

            set_boxstyle("Round,pad=0.2")
            set_boxstyle("round", pad=0.2)
        """
        if boxstyle is None:
            return BoxStyle.pprint_styles()
        self._bbox_transmuter = (
            BoxStyle(boxstyle, **kwargs)
            if isinstance(boxstyle, str) else boxstyle)
        self.stale = True

    def get_boxstyle(self):
        """Return the boxstyle object."""
        return self._bbox_transmuter

    def set_mutation_scale(self, scale):
        """
        Set the mutation scale.

        Parameters
        ----------
        scale : float
        """
        self._mutation_scale = scale
        self.stale = True

    def get_mutation_scale(self):
        """Return the mutation scale."""
        return self._mutation_scale

    def set_mutation_aspect(self, aspect):
        """
        Set the aspect ratio of the bbox mutation.

        Parameters
        ----------
        aspect : float
        """
        self._mutation_aspect = aspect
        self.stale = True

    def get_mutation_aspect(self):
        """Return the aspect ratio of the bbox mutation."""
        return (self._mutation_aspect if self._mutation_aspect is not None
                else 1)  # backcompat.

    def get_path(self):
        """Return the mutated path of the rectangle."""
        boxstyle = self.get_boxstyle()
        m_aspect = self.get_mutation_aspect()
        # Call boxstyle with y, height squeezed by aspect_ratio.
        path = boxstyle(self._x, self._y / m_aspect,
                        self._width, self._height / m_aspect,
                        self.get_mutation_scale())
        return Path(path.vertices * [1, m_aspect], path.codes)  # Unsqueeze y.

    # Following methods are borrowed from the Rectangle class.

    def get_x(self):
        """Return the left coord of the rectangle."""
        return self._x

    def get_y(self):
        """Return the bottom coord of the rectangle."""
        return self._y

    def get_width(self):
        """Return the width of the rectangle."""
        return self._width

    def get_height(self):
        """Return the height of the rectangle."""
        return self._height

    def set_x(self, x):
        """
        Set the left coord of the rectangle.

        Parameters
        ----------
        x : float
        """
        self._x = x
        self.stale = True

    def set_y(self, y):
        """
        Set the bottom coord of the rectangle.

        Parameters
        ----------
        y : float
        """
        self._y = y
        self.stale = True

    def set_width(self, w):
        """
        Set the rectangle width.

        Parameters
        ----------
        w : float
        """
        self._width = w
        self.stale = True

    def set_height(self, h):
        """
        Set the rectangle height.

        Parameters
        ----------
        h : float
        """
        self._height = h
        self.stale = True

    def set_bounds(self, *args):
        """
        Set the bounds of the rectangle.

        Call signatures::

            set_bounds(left, bottom, width, height)
            set_bounds((left, bottom, width, height))

        Parameters
        ----------
        left, bottom : float
            The coordinates of the bottom left corner of the rectangle.
        width, height : float
            The width/height of the rectangle.
        """
        if len(args) == 1:
            l, b, w, h = args[0]
        else:
            l, b, w, h = args
        self._x = l
        self._y = b
        self._width = w
        self._height = h
        self.stale = True

    def get_bbox(self):
        """Return the `.Bbox`."""
        return transforms.Bbox.from_bounds(self._x, self._y,
                                           self._width, self._height)


class FancyArrowPatch(Patch):
    """
    A fancy arrow patch.

    It draws an arrow using the `ArrowStyle`. It is primarily used by the
    `~.axes.Axes.annotate` method.  For most purposes, use the annotate method for
    drawing arrows.

    The head and tail positions are fixed at the specified start and end points
    of the arrow, but the size and shape (in display coordinates) of the arrow
    does not change when the axis is moved or zoomed.
    """
    _edge_default = True

    def __str__(self):
        if self._posA_posB is not None:
            (x1, y1), (x2, y2) = self._posA_posB
            return f"{type(self).__name__}(({x1:g}, {y1:g})->({x2:g}, {y2:g}))"
        else:
            return f"{type(self).__name__}({self._path_original})"

    @_docstring.interpd
    def __init__(self, posA=None, posB=None, *,
                 path=None, arrowstyle="simple", connectionstyle="arc3",
                 patchA=None, patchB=None, shrinkA=2, shrinkB=2,
                 mutation_scale=1, mutation_aspect=1, **kwargs):
        """
        **Defining the arrow position and path**

        There are two ways to define the arrow position and path:

        - **Start, end and connection**:
          The typical approach is to define the start and end points of the
          arrow using *posA* and *posB*. The curve between these two can
          further be configured using *connectionstyle*.

          If given, the arrow curve is clipped by *patchA* and *patchB*,
          allowing it to start/end at the border of these patches.
          Additionally, the arrow curve can be shortened by *shrinkA* and *shrinkB*
          to create a margin between start/end (after possible clipping) and the
          drawn arrow.

        - **path**: Alternatively if *path* is provided, an arrow is drawn along
          this Path. In this case, *connectionstyle*, *patchA*, *patchB*,
          *shrinkA*, and *shrinkB* are ignored.

        **Styling**

        The *arrowstyle* defines the styling of the arrow head, tail and shaft.
        The resulting arrows can be styled further by setting the `.Patch`
        properties such as *linewidth*, *color*, *facecolor*, *edgecolor*
        etc. via keyword arguments.

        Parameters
        ----------
        posA, posB : (float, float), optional
            (x, y) coordinates of start and end point of the arrow.
            The actually drawn start and end positions may be modified
            through *patchA*, *patchB*, *shrinkA*, and *shrinkB*.

            *posA*, *posB* are exclusive of *path*.

        path : `~matplotlib.path.Path`, optional
            If provided, an arrow is drawn along this path and *patchA*,
            *patchB*, *shrinkA*, and *shrinkB* are ignored.

            *path* is exclusive of *posA*, *posB*.

        arrowstyle : str or `.ArrowStyle`, default: 'simple'
            The styling of arrow head, tail and shaft. This can be

            - `.ArrowStyle` or one of its subclasses
            - The shorthand string name (e.g. "->") as given in the table below,
              optionally containing a comma-separated list of style parameters,
              e.g. "->, head_length=10, head_width=5".

            The style parameters are scaled by *mutation_scale*.

            The following arrow styles are available. See also
            :doc:`/gallery/text_labels_and_annotations/fancyarrow_demo`.

            %(ArrowStyle:table)s

            Only the styles ``<|-``, ``-|>``, ``<|-|>`` ``simple``, ``fancy``
            and ``wedge`` contain closed paths and can be filled.

        connectionstyle : str or `.ConnectionStyle` or None, optional, \
default: 'arc3'
            `.ConnectionStyle` with which *posA* and *posB* are connected.
            This can be

            - `.ConnectionStyle` or one of its subclasses
            - The shorthand string name as given in the table below, e.g. "arc3".

            %(ConnectionStyle:table)s

            Ignored if *path* is provided.

        patchA, patchB : `~matplotlib.patches.Patch`, default: None
            Optional Patches at *posA* and *posB*, respectively. If given,
            the arrow path is clipped by these patches such that head and tail
            are at the border of the patches.

            Ignored if *path* is provided.

        shrinkA, shrinkB : float, default: 2
            Shorten the arrow path at *posA* and *posB* by this amount in points.
            This allows to add a margin between the intended start/end points and
            the arrow.

            Ignored if *path* is provided.

        mutation_scale : float, default: 1
            Value with which attributes of *arrowstyle* (e.g., *head_length*)
            will be scaled.

        mutation_aspect : None or float, default: None
            The height of the rectangle will be squeezed by this value before
            the mutation and the mutated box will be stretched by the inverse
            of it.

        Other Parameters
        ----------------
        **kwargs : `~matplotlib.patches.Patch` properties, optional
            Here is a list of available `.Patch` properties:

        %(Patch:kwdoc)s

            In contrast to other patches, the default ``capstyle`` and
            ``joinstyle`` for `FancyArrowPatch` are set to ``"round"``.
        """
        # Traditionally, the cap- and joinstyle for FancyArrowPatch are round
        kwargs.setdefault("joinstyle", JoinStyle.round)
        kwargs.setdefault("capstyle", CapStyle.round)

        super().__init__(**kwargs)

        if posA is not None and posB is not None and path is None:
            self._posA_posB = [posA, posB]

            if connectionstyle is None:
                connectionstyle = "arc3"
            self.set_connectionstyle(connectionstyle)

        elif posA is None and posB is None and path is not None:
            self._posA_posB = None
        else:
            raise ValueError("Either posA and posB, or path need to provided")

        self.patchA = patchA
        self.patchB = patchB
        self.shrinkA = shrinkA
        self.shrinkB = shrinkB

        self._path_original = path

        self.set_arrowstyle(arrowstyle)

        self._mutation_scale = mutation_scale
        self._mutation_aspect = mutation_aspect

        self._dpi_cor = 1.0

    def set_positions(self, posA, posB):
        """
        Set the start and end positions of the connecting path.

        Parameters
        ----------
        posA, posB : None, tuple
            (x, y) coordinates of arrow tail and arrow head respectively. If
            `None` use current value.
        """
        if posA is not None:
            self._posA_posB[0] = posA
        if posB is not None:
            self._posA_posB[1] = posB
        self.stale = True

    def set_patchA(self, patchA):
        """
        Set the tail patch.

        Parameters
        ----------
        patchA : `.patches.Patch`
        """
        self.patchA = patchA
        self.stale = True

    def set_patchB(self, patchB):
        """
        Set the head patch.

        Parameters
        ----------
        patchB : `.patches.Patch`
        """
        self.patchB = patchB
        self.stale = True

    @_docstring.interpd
    def set_connectionstyle(self, connectionstyle=None, **kwargs):
        """
        Set the connection style, possibly with further attributes.

        Attributes from the previous connection style are not reused.

        Without argument (or with ``connectionstyle=None``), the available box
        styles are returned as a human-readable string.

        Parameters
        ----------
        connectionstyle : str or `~matplotlib.patches.ConnectionStyle`
            The style of the connection: either a `.ConnectionStyle` instance,
            or a string, which is the style name and optionally comma separated
            attributes (e.g. "Arc,armA=30,rad=10"). Such a string is used to
            construct a `.ConnectionStyle` object, as documented in that class.

            The following connection styles are available:

            %(ConnectionStyle:table_and_accepts)s

        **kwargs
            Additional attributes for the connection style. See the table above
            for supported parameters.

        Examples
        --------
        ::

            set_connectionstyle("Arc,armA=30,rad=10")
            set_connectionstyle("arc", armA=30, rad=10)
        """
        if connectionstyle is None:
            return ConnectionStyle.pprint_styles()
        self._connector = (
            ConnectionStyle(connectionstyle, **kwargs)
            if isinstance(connectionstyle, str) else connectionstyle)
        self.stale = True

    def get_connectionstyle(self):
        """Return the `ConnectionStyle` used."""
        return self._connector

    @_docstring.interpd
    def set_arrowstyle(self, arrowstyle=None, **kwargs):
        """
        Set the arrow style, possibly with further attributes.

        Attributes from the previous arrow style are not reused.

        Without argument (or with ``arrowstyle=None``), the available box
        styles are returned as a human-readable string.

        Parameters
        ----------
        arrowstyle : str or `~matplotlib.patches.ArrowStyle`
            The style of the arrow: either a `.ArrowStyle` instance, or a
            string, which is the style name and optionally comma separated
            attributes (e.g. "Fancy,head_length=0.2"). Such a string is used to
            construct a `.ArrowStyle` object, as documented in that class.

            The following arrow styles are available:

            %(ArrowStyle:table_and_accepts)s

        **kwargs
            Additional attributes for the arrow style. See the table above for
            supported parameters.

        Examples
        --------
        ::

            set_arrowstyle("Fancy,head_length=0.2")
            set_arrowstyle("fancy", head_length=0.2)
        """
        if arrowstyle is None:
            return ArrowStyle.pprint_styles()
        self._arrow_transmuter = (
            ArrowStyle(arrowstyle, **kwargs)
            if isinstance(arrowstyle, str) else arrowstyle)
        self.stale = True

    def get_arrowstyle(self):
        """Return the arrowstyle object."""
        return self._arrow_transmuter

    def set_mutation_scale(self, scale):
        """
        Set the mutation scale.

        Parameters
        ----------
        scale : float
        """
        self._mutation_scale = scale
        self.stale = True

    def get_mutation_scale(self):
        """
        Return the mutation scale.

        Returns
        -------
        scalar
        """
        return self._mutation_scale

    def set_mutation_aspect(self, aspect):
        """
        Set the aspect ratio of the bbox mutation.

        Parameters
        ----------
        aspect : float
        """
        self._mutation_aspect = aspect
        self.stale = True

    def get_mutation_aspect(self):
        """Return the aspect ratio of the bbox mutation."""
        return (self._mutation_aspect if self._mutation_aspect is not None
                else 1)  # backcompat.

    def get_path(self):
        """Return the path of the arrow in the data coordinates."""
        # The path is generated in display coordinates, then converted back to
        # data coordinates.
        _path, fillable = self._get_path_in_displaycoord()
        if np.iterable(fillable):
            _path = Path.make_compound_path(*_path)
        return self.get_transform().inverted().transform_path(_path)

    def _get_path_in_displaycoord(self):
        """Return the mutated path of the arrow in display coordinates."""
        dpi_cor = self._dpi_cor

        if self._posA_posB is not None:
            posA = self._convert_xy_units(self._posA_posB[0])
            posB = self._convert_xy_units(self._posA_posB[1])
            (posA, posB) = self.get_transform().transform((posA, posB))
            _path = self.get_connectionstyle()(posA, posB,
                                               patchA=self.patchA,
                                               patchB=self.patchB,
                                               shrinkA=self.shrinkA * dpi_cor,
                                               shrinkB=self.shrinkB * dpi_cor
                                               )
        else:
            _path = self.get_transform().transform_path(self._path_original)

        _path, fillable = self.get_arrowstyle()(
            _path,
            self.get_mutation_scale() * dpi_cor,
            self.get_linewidth() * dpi_cor,
            self.get_mutation_aspect())

        return _path, fillable

    def draw(self, renderer):
        if not self.get_visible():
            return

        # FIXME: dpi_cor is for the dpi-dependency of the linewidth.  There
        # could be room for improvement.  Maybe _get_path_in_displaycoord could
        # take a renderer argument, but get_path should be adapted too.
        self._dpi_cor = renderer.points_to_pixels(1.)
        path, fillable = self._get_path_in_displaycoord()

        if not np.iterable(fillable):
            path = [path]
            fillable = [fillable]

        affine = transforms.IdentityTransform()

        self._draw_paths_with_artist_properties(
            renderer,
            [(p, affine, self._facecolor if f and self._facecolor[3] else None)
             for p, f in zip(path, fillable)])


class ConnectionPatch(FancyArrowPatch):
    """A patch that connects two points (possibly in different Axes)."""

    def __str__(self):
        return "ConnectionPatch((%g, %g), (%g, %g))" % \
               (self.xy1[0], self.xy1[1], self.xy2[0], self.xy2[1])

    @_docstring.interpd
    def __init__(self, xyA, xyB, coordsA, coordsB=None, *,
                 axesA=None, axesB=None,
                 arrowstyle="-",
                 connectionstyle="arc3",
                 patchA=None,
                 patchB=None,
                 shrinkA=0.,
                 shrinkB=0.,
                 mutation_scale=10.,
                 mutation_aspect=None,
                 clip_on=False,
                 **kwargs):
        """
        Connect point *xyA* in *coordsA* with point *xyB* in *coordsB*.

        Valid keys are

        ===============  ======================================================
        Key              Description
        ===============  ======================================================
        arrowstyle       the arrow style
        connectionstyle  the connection style
        relpos           default is (0.5, 0.5)
        patchA           default is bounding box of the text
        patchB           default is None
        shrinkA          default is 2 points
        shrinkB          default is 2 points
        mutation_scale   default is text size (in points)
        mutation_aspect  default is 1.
        ?                any key for `matplotlib.patches.PathPatch`
        ===============  ======================================================

        *coordsA* and *coordsB* are strings that indicate the
        coordinates of *xyA* and *xyB*.

        ==================== ==================================================
        Property             Description
        ==================== ==================================================
        'figure points'      points from the lower left corner of the figure
        'figure pixels'      pixels from the lower left corner of the figure
        'figure fraction'    0, 0 is lower left of figure and 1, 1 is upper
                             right
        'subfigure points'   points from the lower left corner of the subfigure
        'subfigure pixels'   pixels from the lower left corner of the subfigure
        'subfigure fraction' fraction of the subfigure, 0, 0 is lower left.
        'axes points'        points from lower left corner of the Axes
        'axes pixels'        pixels from lower left corner of the Axes
        'axes fraction'      0, 0 is lower left of Axes and 1, 1 is upper right
        'data'               use the coordinate system of the object being
                             annotated (default)
        'offset points'      offset (in points) from the *xy* value
        'polar'              you can specify *theta*, *r* for the annotation,
                             even in cartesian plots.  Note that if you are
                             using a polar Axes, you do not need to specify
                             polar for the coordinate system since that is the
                             native "data" coordinate system.
        ==================== ==================================================

        Alternatively they can be set to any valid
        `~matplotlib.transforms.Transform`.

        Note that 'subfigure pixels' and 'figure pixels' are the same
        for the parent figure, so users who want code that is usable in
        a subfigure can use 'subfigure pixels'.

        .. note::

           Using `ConnectionPatch` across two `~.axes.Axes` instances
           is not directly compatible with :ref:`constrained layout
           <constrainedlayout_guide>`. Add the artist
           directly to the `.Figure` instead of adding it to a specific Axes,
           or exclude it from the layout using ``con.set_in_layout(False)``.

           .. code-block:: default

              fig, ax = plt.subplots(1, 2, constrained_layout=True)
              con = ConnectionPatch(..., axesA=ax[0], axesB=ax[1])
              fig.add_artist(con)

        """
        if coordsB is None:
            coordsB = coordsA
        # we'll draw ourself after the artist we annotate by default
        self.xy1 = xyA
        self.xy2 = xyB
        self.coords1 = coordsA
        self.coords2 = coordsB

        self.axesA = axesA
        self.axesB = axesB

        super().__init__(posA=(0, 0), posB=(1, 1),
                         arrowstyle=arrowstyle,
                         connectionstyle=connectionstyle,
                         patchA=patchA, patchB=patchB,
                         shrinkA=shrinkA, shrinkB=shrinkB,
                         mutation_scale=mutation_scale,
                         mutation_aspect=mutation_aspect,
                         clip_on=clip_on,
                         **kwargs)
        # if True, draw annotation only if self.xy is inside the Axes
        self._annotation_clip = None

    def _get_xy(self, xy, s, axes=None):
        """Calculate the pixel position of given point."""
        s0 = s  # For the error message, if needed.
        if axes is None:
            axes = self.axes

        # preserve mixed type input (such as str, int)
        x = np.array(xy[0])
        y = np.array(xy[1])

        fig = self.get_figure(root=False)
        if s in ["figure points", "axes points"]:
            x = x * fig.dpi / 72
            y = y * fig.dpi / 72
            s = s.replace("points", "pixels")
        elif s == "figure fraction":
            s = fig.transFigure
        elif s == "subfigure fraction":
            s = fig.transSubfigure
        elif s == "axes fraction":
            s = axes.transAxes

        if s == 'data':
            trans = axes.transData
            x = cbook._to_unmasked_float_array(axes.xaxis.convert_units(x))
            y = cbook._to_unmasked_float_array(axes.yaxis.convert_units(y))
            return trans.transform((x, y))
        elif s == 'offset points':
            if self.xycoords == 'offset points':  # prevent recursion
                return self._get_xy(self.xy, 'data')
            return (
                self._get_xy(self.xy, self.xycoords)  # converted data point
                + xy * self.get_figure(root=True).dpi / 72)  # converted offset
        elif s == 'polar':
            theta, r = x, y
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            trans = axes.transData
            return trans.transform((x, y))
        elif s == 'figure pixels':
            # pixels from the lower left corner of the figure
            bb = self.get_figure(root=False).figbbox
            x = bb.x0 + x if x >= 0 else bb.x1 + x
            y = bb.y0 + y if y >= 0 else bb.y1 + y
            return x, y
        elif s == 'subfigure pixels':
            # pixels from the lower left corner of the figure
            bb = self.get_figure(root=False).bbox
            x = bb.x0 + x if x >= 0 else bb.x1 + x
            y = bb.y0 + y if y >= 0 else bb.y1 + y
            return x, y
        elif s == 'axes pixels':
            # pixels from the lower left corner of the Axes
            bb = axes.bbox
            x = bb.x0 + x if x >= 0 else bb.x1 + x
            y = bb.y0 + y if y >= 0 else bb.y1 + y
            return x, y
        elif isinstance(s, transforms.Transform):
            return s.transform(xy)
        else:
            raise ValueError(f"{s0} is not a valid coordinate transformation")

    def set_annotation_clip(self, b):
        """
        Set the annotation's clipping behavior.

        Parameters
        ----------
        b : bool or None
            - True: The annotation will be clipped when ``self.xy`` is
              outside the Axes.
            - False: The annotation will always be drawn.
            - None: The annotation will be clipped when ``self.xy`` is
              outside the Axes and ``self.xycoords == "data"``.
        """
        self._annotation_clip = b
        self.stale = True

    def get_annotation_clip(self):
        """
        Return the clipping behavior.

        See `.set_annotation_clip` for the meaning of the return value.
        """
        return self._annotation_clip

    def _get_path_in_displaycoord(self):
        """Return the mutated path of the arrow in display coordinates."""
        dpi_cor = self._dpi_cor
        posA = self._get_xy(self.xy1, self.coords1, self.axesA)
        posB = self._get_xy(self.xy2, self.coords2, self.axesB)
        path = self.get_connectionstyle()(
            posA, posB,
            patchA=self.patchA, patchB=self.patchB,
            shrinkA=self.shrinkA * dpi_cor, shrinkB=self.shrinkB * dpi_cor,
        )
        path, fillable = self.get_arrowstyle()(
            path,
            self.get_mutation_scale() * dpi_cor,
            self.get_linewidth() * dpi_cor,
            self.get_mutation_aspect()
        )
        return path, fillable

    def _check_xy(self, renderer):
        """Check whether the annotation needs to be drawn."""

        b = self.get_annotation_clip()

        if b or (b is None and self.coords1 == "data"):
            xy_pixel = self._get_xy(self.xy1, self.coords1, self.axesA)
            if self.axesA is None:
                axes = self.axes
            else:
                axes = self.axesA
            if not axes.contains_point(xy_pixel):
                return False

        if b or (b is None and self.coords2 == "data"):
            xy_pixel = self._get_xy(self.xy2, self.coords2, self.axesB)
            if self.axesB is None:
                axes = self.axes
            else:
                axes = self.axesB
            if not axes.contains_point(xy_pixel):
                return False

        return True

    def draw(self, renderer):
        if not self.get_visible() or not self._check_xy(renderer):
            return
        super().draw(renderer)

# === NexusCore/openenv\Lib\site-packages\matplotlib\pyplot.py ===
# Note: The first part of this file can be modified in place, but the latter
# part is autogenerated by the boilerplate.py script.

"""
`matplotlib.pyplot` is a state-based interface to matplotlib. It provides
an implicit,  MATLAB-like, way of plotting.  It also opens figures on your
screen, and acts as the figure GUI manager.

pyplot is mainly intended for interactive plots and simple cases of
programmatic plot generation::

    import numpy as np
    import matplotlib.pyplot as plt

    x = np.arange(0, 5, 0.1)
    y = np.sin(x)
    plt.plot(x, y)
    plt.show()

The explicit object-oriented API is recommended for complex plots, though
pyplot is still usually used to create the figure and often the Axes in the
figure. See `.pyplot.figure`, `.pyplot.subplots`, and
`.pyplot.subplot_mosaic` to create figures, and
:doc:`Axes API </api/axes_api>` for the plotting methods on an Axes::

    import numpy as np
    import matplotlib.pyplot as plt

    x = np.arange(0, 5, 0.1)
    y = np.sin(x)
    fig, ax = plt.subplots()
    ax.plot(x, y)
    plt.show()


See :ref:`api_interfaces` for an explanation of the tradeoffs between the
implicit and explicit interfaces.
"""

# fmt: off

from __future__ import annotations

from contextlib import AbstractContextManager, ExitStack
from enum import Enum
import functools
import importlib
import inspect
import logging
import sys
import threading
import time
from typing import TYPE_CHECKING, cast, overload

from cycler import cycler  # noqa: F401
import matplotlib
import matplotlib.colorbar
import matplotlib.image
from matplotlib import _api
# Re-exported (import x as x) for typing.
from matplotlib import get_backend as get_backend, rcParams as rcParams
from matplotlib import cm as cm  # noqa: F401
from matplotlib import style as style  # noqa: F401
from matplotlib import _pylab_helpers
from matplotlib import interactive  # noqa: F401
from matplotlib import cbook
from matplotlib import _docstring
from matplotlib.backend_bases import (
    FigureCanvasBase, FigureManagerBase, MouseButton)
from matplotlib.figure import Figure, FigureBase, figaspect
from matplotlib.gridspec import GridSpec, SubplotSpec
from matplotlib import rcsetup, rcParamsDefault, rcParamsOrig
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.axes import Subplot  # noqa: F401
from matplotlib.backends import BackendFilter, backend_registry
from matplotlib.projections import PolarAxes
from matplotlib.colorizer import _ColorizerInterface, ColorizingArtist, Colorizer
from matplotlib import mlab  # for detrend_none, window_hanning
from matplotlib.scale import get_scale_names  # noqa: F401

from matplotlib.cm import _colormaps
from matplotlib.colors import _color_sequences, Colormap

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable, Iterable, Sequence
    import datetime
    import pathlib
    import os
    from typing import Any, BinaryIO, Literal, TypeVar
    from typing_extensions import ParamSpec

    import PIL.Image
    from numpy.typing import ArrayLike

    import matplotlib.axes
    import matplotlib.artist
    import matplotlib.backend_bases
    from matplotlib.axis import Tick
    from matplotlib.axes._base import _AxesBase
    from matplotlib.backend_bases import Event
    from matplotlib.cm import ScalarMappable
    from matplotlib.contour import ContourSet, QuadContourSet
    from matplotlib.collections import (
        Collection,
        FillBetweenPolyCollection,
        LineCollection,
        PolyCollection,
        PathCollection,
        EventCollection,
        QuadMesh,
    )
    from matplotlib.colorbar import Colorbar
    from matplotlib.container import (
        BarContainer,
        ErrorbarContainer,
        StemContainer,
    )
    from matplotlib.figure import SubFigure
    from matplotlib.legend import Legend
    from matplotlib.mlab import GaussianKDE
    from matplotlib.image import AxesImage, FigureImage
    from matplotlib.patches import FancyArrow, StepPatch, Wedge
    from matplotlib.quiver import Barbs, Quiver, QuiverKey
    from matplotlib.scale import ScaleBase
    from matplotlib.typing import (
        ColorType,
        CoordsType,
        HashableList,
        LineStyleType,
        MarkerType,
    )
    from matplotlib.widgets import SubplotTool

    _P = ParamSpec('_P')
    _R = TypeVar('_R')
    _T = TypeVar('_T')


# We may not need the following imports here:
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D, AxLine
from matplotlib.text import Text, Annotation
from matplotlib.patches import Arrow, Circle, Rectangle  # noqa: F401
from matplotlib.patches import Polygon
from matplotlib.widgets import Button, Slider, Widget  # noqa: F401

from .ticker import (  # noqa: F401
    TickHelper, Formatter, FixedFormatter, NullFormatter, FuncFormatter,
    FormatStrFormatter, ScalarFormatter, LogFormatter, LogFormatterExponent,
    LogFormatterMathtext, Locator, IndexLocator, FixedLocator, NullLocator,
    LinearLocator, LogLocator, AutoLocator, MultipleLocator, MaxNLocator)

_log = logging.getLogger(__name__)


# Explicit rename instead of import-as for typing's sake.
colormaps = _colormaps
color_sequences = _color_sequences


@overload
def _copy_docstring_and_deprecators(
    method: Any,
    func: Literal[None] = None
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]: ...


@overload
def _copy_docstring_and_deprecators(
    method: Any, func: Callable[_P, _R]) -> Callable[_P, _R]: ...


def _copy_docstring_and_deprecators(
    method: Any,
    func: Callable[_P, _R] | None = None
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]] | Callable[_P, _R]:
    if func is None:
        return cast('Callable[[Callable[_P, _R]], Callable[_P, _R]]',
                    functools.partial(_copy_docstring_and_deprecators, method))
    decorators: list[Callable[[Callable[_P, _R]], Callable[_P, _R]]] = [
        _docstring.copy(method)
    ]
    # Check whether the definition of *method* includes @_api.rename_parameter
    # or @_api.make_keyword_only decorators; if so, propagate them to the
    # pyplot wrapper as well.
    while hasattr(method, "__wrapped__"):
        potential_decorator = _api.deprecation.DECORATORS.get(method)
        if potential_decorator:
            decorators.append(potential_decorator)
        method = method.__wrapped__
    for decorator in decorators[::-1]:
        func = decorator(func)
    _add_pyplot_note(func, method)
    return func


_NO_PYPLOT_NOTE = [
    'FigureBase._gci',  # wrapped_func is private
    '_AxesBase._sci',  # wrapped_func is private
    'Artist.findobj',  # not a standard pyplot wrapper because it does not operate
                       # on the current Figure / Axes. Explanation of relation would
                       # be more complex and is not too important.
]


def _add_pyplot_note(func, wrapped_func):
    """
    Add a note to the docstring of *func* that it is a pyplot wrapper.

    The note is added to the "Notes" section of the docstring. If that does
    not exist, a "Notes" section is created. In numpydoc, the "Notes"
    section is the third last possible section, only potentially followed by
    "References" and "Examples".
    """
    if not func.__doc__:
        return  # nothing to do

    qualname = wrapped_func.__qualname__
    if qualname in _NO_PYPLOT_NOTE:
        return

    wrapped_func_is_method = True
    if "." not in qualname:
        # method qualnames are prefixed by the class and ".", e.g. "Axes.plot"
        wrapped_func_is_method = False
        link = f"{wrapped_func.__module__}.{qualname}"
    elif qualname.startswith("Axes."):  # e.g. "Axes.plot"
        link = ".axes." + qualname
    elif qualname.startswith("_AxesBase."):  # e.g. "_AxesBase.set_xlabel"
        link = ".axes.Axes" + qualname[9:]
    elif qualname.startswith("Figure."):  # e.g. "Figure.figimage"
        link = "." + qualname
    elif qualname.startswith("FigureBase."):  # e.g. "FigureBase.gca"
        link = ".Figure" + qualname[10:]
    elif qualname.startswith("FigureCanvasBase."):  # "FigureBaseCanvas.mpl_connect"
        link = "." + qualname
    else:
        raise RuntimeError(f"Wrapped method from unexpected class: {qualname}")

    if wrapped_func_is_method:
        message = f"This is the :ref:`pyplot wrapper <pyplot_interface>` for `{link}`."
    else:
        message = f"This is equivalent to `{link}`."

    # Find the correct insert position:
    # - either we already have a "Notes" section into which we can insert
    # - or we create one before the next present section. Note that in numpydoc, the
    #   "Notes" section is the third last possible section, only potentially followed
    #   by "References" and "Examples".
    # - or we append a new "Notes" section at the end.
    doc = inspect.cleandoc(func.__doc__)
    if "\nNotes\n-----" in doc:
        before, after = doc.split("\nNotes\n-----", 1)
    elif (index := doc.find("\nReferences\n----------")) != -1:
        before, after = doc[:index], doc[index:]
    elif (index := doc.find("\nExamples\n--------")) != -1:
        before, after = doc[:index], doc[index:]
    else:
        # No "Notes", "References", or "Examples" --> append to the end.
        before = doc + "\n"
        after = ""

    func.__doc__ = f"{before}\nNotes\n-----\n\n.. note::\n\n    {message}\n{after}"


## Global ##


# The state controlled by {,un}install_repl_displayhook().
_ReplDisplayHook = Enum("_ReplDisplayHook", ["NONE", "PLAIN", "IPYTHON"])
_REPL_DISPLAYHOOK = _ReplDisplayHook.NONE


def _draw_all_if_interactive() -> None:
    if matplotlib.is_interactive():
        draw_all()


def install_repl_displayhook() -> None:
    """
    Connect to the display hook of the current shell.

    The display hook gets called when the read-evaluate-print-loop (REPL) of
    the shell has finished the execution of a command. We use this callback
    to be able to automatically update a figure in interactive mode.

    This works both with IPython and with vanilla python shells.
    """
    global _REPL_DISPLAYHOOK

    if _REPL_DISPLAYHOOK is _ReplDisplayHook.IPYTHON:
        return

    # See if we have IPython hooks around, if so use them.
    # Use ``sys.modules.get(name)`` rather than ``name in sys.modules`` as
    # entries can also have been explicitly set to None.
    mod_ipython = sys.modules.get("IPython")
    if not mod_ipython:
        _REPL_DISPLAYHOOK = _ReplDisplayHook.PLAIN
        return
    ip = mod_ipython.get_ipython()
    if not ip:
        _REPL_DISPLAYHOOK = _ReplDisplayHook.PLAIN
        return

    ip.events.register("post_execute", _draw_all_if_interactive)
    _REPL_DISPLAYHOOK = _ReplDisplayHook.IPYTHON

    if mod_ipython.version_info[:2] < (8, 24):
        # Use of backend2gui is not needed for IPython >= 8.24 as that functionality
        # has been moved to Matplotlib.
        # This code can be removed when Python 3.12, the latest version supported by
        # IPython < 8.24, reaches end-of-life in late 2028.
        from IPython.core.pylabtools import backend2gui
        ipython_gui_name = backend2gui.get(get_backend())
    else:
        _, ipython_gui_name = backend_registry.resolve_backend(get_backend())
    # trigger IPython's eventloop integration, if available
    if ipython_gui_name:
        ip.enable_gui(ipython_gui_name)


def uninstall_repl_displayhook() -> None:
    """Disconnect from the display hook of the current shell."""
    global _REPL_DISPLAYHOOK
    if _REPL_DISPLAYHOOK is _ReplDisplayHook.IPYTHON:
        from IPython import get_ipython
        ip = get_ipython()
        ip.events.unregister("post_execute", _draw_all_if_interactive)
    _REPL_DISPLAYHOOK = _ReplDisplayHook.NONE


draw_all = _pylab_helpers.Gcf.draw_all


# Ensure this appears in the pyplot docs.
@_copy_docstring_and_deprecators(matplotlib.set_loglevel)
def set_loglevel(*args, **kwargs) -> None:
    return matplotlib.set_loglevel(*args, **kwargs)


@_copy_docstring_and_deprecators(Artist.findobj)
def findobj(
    o: Artist | None = None,
    match: Callable[[Artist], bool] | type[Artist] | None = None,
    include_self: bool = True
) -> list[Artist]:
    if o is None:
        o = gcf()
    return o.findobj(match, include_self=include_self)


_backend_mod: type[matplotlib.backend_bases._Backend] | None = None


def _get_backend_mod() -> type[matplotlib.backend_bases._Backend]:
    """
    Ensure that a backend is selected and return it.

    This is currently private, but may be made public in the future.
    """
    if _backend_mod is None:
        # Use rcParams._get("backend") to avoid going through the fallback
        # logic (which will (re)import pyplot and then call switch_backend if
        # we need to resolve the auto sentinel)
        switch_backend(rcParams._get("backend"))
    return cast(type[matplotlib.backend_bases._Backend], _backend_mod)


def switch_backend(newbackend: str) -> None:
    """
    Set the pyplot backend.

    Switching to an interactive backend is possible only if no event loop for
    another interactive backend has started.  Switching to and from
    non-interactive backends is always possible.

    If the new backend is different than the current backend then all open
    Figures will be closed via ``plt.close('all')``.

    Parameters
    ----------
    newbackend : str
        The case-insensitive name of the backend to use.

    """
    global _backend_mod
    # make sure the init is pulled up so we can assign to it later
    import matplotlib.backends

    if newbackend is rcsetup._auto_backend_sentinel:
        current_framework = cbook._get_running_interactive_framework()

        if (current_framework and
                (backend := backend_registry.backend_for_gui_framework(
                    current_framework))):
            candidates = [backend]
        else:
            candidates = []
        candidates += [
            "macosx", "qtagg", "gtk4agg", "gtk3agg", "tkagg", "wxagg"]

        # Don't try to fallback on the cairo-based backends as they each have
        # an additional dependency (pycairo) over the agg-based backend, and
        # are of worse quality.
        for candidate in candidates:
            try:
                switch_backend(candidate)
            except ImportError:
                continue
            else:
                rcParamsOrig['backend'] = candidate
                return
        else:
            # Switching to Agg should always succeed; if it doesn't, let the
            # exception propagate out.
            switch_backend("agg")
            rcParamsOrig["backend"] = "agg"
            return
    old_backend = rcParams._get('backend')  # get without triggering backend resolution

    module = backend_registry.load_backend_module(newbackend)
    canvas_class = module.FigureCanvas

    required_framework = canvas_class.required_interactive_framework
    if required_framework is not None:
        current_framework = cbook._get_running_interactive_framework()
        if (current_framework and required_framework
                and current_framework != required_framework):
            raise ImportError(
                "Cannot load backend {!r} which requires the {!r} interactive "
                "framework, as {!r} is currently running".format(
                    newbackend, required_framework, current_framework))

    # Load the new_figure_manager() and show() functions from the backend.

    # Classically, backends can directly export these functions.  This should
    # keep working for backcompat.
    new_figure_manager = getattr(module, "new_figure_manager", None)
    show = getattr(module, "show", None)

    # In that classical approach, backends are implemented as modules, but
    # "inherit" default method implementations from backend_bases._Backend.
    # This is achieved by creating a "class" that inherits from
    # backend_bases._Backend and whose body is filled with the module globals.
    class backend_mod(matplotlib.backend_bases._Backend):
        locals().update(vars(module))

    # However, the newer approach for defining new_figure_manager and
    # show is to derive them from canvas methods.  In that case, also
    # update backend_mod accordingly; also, per-backend customization of
    # draw_if_interactive is disabled.
    if new_figure_manager is None:

        def new_figure_manager_given_figure(num, figure):
            return canvas_class.new_manager(figure, num)

        def new_figure_manager(num, *args, FigureClass=Figure, **kwargs):
            fig = FigureClass(*args, **kwargs)
            return new_figure_manager_given_figure(num, fig)

        def draw_if_interactive() -> None:
            if matplotlib.is_interactive():
                manager = _pylab_helpers.Gcf.get_active()
                if manager:
                    manager.canvas.draw_idle()

        backend_mod.new_figure_manager_given_figure = (  # type: ignore[method-assign]
            new_figure_manager_given_figure)
        backend_mod.new_figure_manager = (  # type: ignore[method-assign]
            new_figure_manager)
        backend_mod.draw_if_interactive = (  # type: ignore[method-assign]
            draw_if_interactive)

    # If the manager explicitly overrides pyplot_show, use it even if a global
    # show is already present, as the latter may be here for backcompat.
    manager_class = getattr(canvas_class, "manager_class", None)
    # We can't compare directly manager_class.pyplot_show and FMB.pyplot_show because
    # pyplot_show is a classmethod so the above constructs are bound classmethods, and
    # thus always different (being bound to different classes).  We also have to use
    # getattr_static instead of vars as manager_class could have no __dict__.
    manager_pyplot_show = inspect.getattr_static(manager_class, "pyplot_show", None)
    base_pyplot_show = inspect.getattr_static(FigureManagerBase, "pyplot_show", None)
    if (show is None
            or (manager_pyplot_show is not None
                and manager_pyplot_show != base_pyplot_show)):
        if not manager_pyplot_show:
            raise ValueError(
                f"Backend {newbackend} defines neither FigureCanvas.manager_class nor "
                f"a toplevel show function")
        _pyplot_show = cast('Any', manager_class).pyplot_show
        backend_mod.show = _pyplot_show  # type: ignore[method-assign]

    _log.debug("Loaded backend %s version %s.",
               newbackend, backend_mod.backend_version)

    if newbackend in ("ipympl", "widget"):
        # ipympl < 0.9.4 expects rcParams["backend"] to be the fully-qualified backend
        # name "module://ipympl.backend_nbagg" not short names "ipympl" or "widget".
        import importlib.metadata as im
        from matplotlib import _parse_to_version_info  # type: ignore[attr-defined]
        try:
            module_version = im.version("ipympl")
            if _parse_to_version_info(module_version) < (0, 9, 4):
                newbackend = "module://ipympl.backend_nbagg"
        except im.PackageNotFoundError:
            pass

    rcParams['backend'] = rcParamsDefault['backend'] = newbackend
    _backend_mod = backend_mod
    for func_name in ["new_figure_manager", "draw_if_interactive", "show"]:
        globals()[func_name].__signature__ = inspect.signature(
            getattr(backend_mod, func_name))

    # Need to keep a global reference to the backend for compatibility reasons.
    # See https://github.com/matplotlib/matplotlib/issues/6092
    matplotlib.backends.backend = newbackend  # type: ignore[attr-defined]

    # Make sure the repl display hook is installed in case we become interactive.
    install_repl_displayhook()


def _warn_if_gui_out_of_main_thread() -> None:
    warn = False
    canvas_class = cast(type[FigureCanvasBase], _get_backend_mod().FigureCanvas)
    if canvas_class.required_interactive_framework:
        if hasattr(threading, 'get_native_id'):
            # This compares native thread ids because even if Python-level
            # Thread objects match, the underlying OS thread (which is what
            # really matters) may be different on Python implementations with
            # green threads.
            if threading.get_native_id() != threading.main_thread().native_id:
                warn = True
        else:
            # Fall back to Python-level Thread if native IDs are unavailable,
            # mainly for PyPy.
            if threading.current_thread() is not threading.main_thread():
                warn = True
    if warn:
        _api.warn_external(
            "Starting a Matplotlib GUI outside of the main thread will likely "
            "fail.")


# This function's signature is rewritten upon backend-load by switch_backend.
def new_figure_manager(*args, **kwargs):
    """Create a new figure manager instance."""
    _warn_if_gui_out_of_main_thread()
    return _get_backend_mod().new_figure_manager(*args, **kwargs)


# This function's signature is rewritten upon backend-load by switch_backend.
def draw_if_interactive(*args, **kwargs):
    """
    Redraw the current figure if in interactive mode.

    .. warning::

        End users will typically not have to call this function because the
        the interactive mode takes care of this.
    """
    return _get_backend_mod().draw_if_interactive(*args, **kwargs)


# This function's signature is rewritten upon backend-load by switch_backend.
def show(*args, **kwargs) -> None:
    """
    Display all open figures.

    Parameters
    ----------
    block : bool, optional
        Whether to wait for all figures to be closed before returning.

        If `True` block and run the GUI main loop until all figure windows
        are closed.

        If `False` ensure that all figure windows are displayed and return
        immediately.  In this case, you are responsible for ensuring
        that the event loop is running to have responsive figures.

        Defaults to True in non-interactive mode and to False in interactive
        mode (see `.pyplot.isinteractive`).

    See Also
    --------
    ion : Enable interactive mode, which shows / updates the figure after
          every plotting command, so that calling ``show()`` is not necessary.
    ioff : Disable interactive mode.
    savefig : Save the figure to an image file instead of showing it on screen.

    Notes
    -----
    **Saving figures to file and showing a window at the same time**

    If you want an image file as well as a user interface window, use
    `.pyplot.savefig` before `.pyplot.show`. At the end of (a blocking)
    ``show()`` the figure is closed and thus unregistered from pyplot. Calling
    `.pyplot.savefig` afterwards would save a new and thus empty figure. This
    limitation of command order does not apply if the show is non-blocking or
    if you keep a reference to the figure and use `.Figure.savefig`.

    **Auto-show in jupyter notebooks**

    The jupyter backends (activated via ``%matplotlib inline``,
    ``%matplotlib notebook``, or ``%matplotlib widget``), call ``show()`` at
    the end of every cell by default. Thus, you usually don't have to call it
    explicitly there.
    """
    _warn_if_gui_out_of_main_thread()
    return _get_backend_mod().show(*args, **kwargs)


def isinteractive() -> bool:
    """
    Return whether plots are updated after every plotting command.

    The interactive mode is mainly useful if you build plots from the command
    line and want to see the effect of each command while you are building the
    figure.

    In interactive mode:

    - newly created figures will be shown immediately;
    - figures will automatically redraw on change;
    - `.pyplot.show` will not block by default.

    In non-interactive mode:

    - newly created figures and changes to figures will not be reflected until
      explicitly asked to be;
    - `.pyplot.show` will block by default.

    See Also
    --------
    ion : Enable interactive mode.
    ioff : Disable interactive mode.
    show : Show all figures (and maybe block).
    pause : Show all figures, and block for a time.
    """
    return matplotlib.is_interactive()


# Note: The return type of ioff being AbstractContextManager
# instead of ExitStack is deliberate.
# See https://github.com/matplotlib/matplotlib/issues/27659
# and https://github.com/matplotlib/matplotlib/pull/27667 for more info.
def ioff() -> AbstractContextManager:
    """
    Disable interactive mode.

    See `.pyplot.isinteractive` for more details.

    See Also
    --------
    ion : Enable interactive mode.
    isinteractive : Whether interactive mode is enabled.
    show : Show all figures (and maybe block).
    pause : Show all figures, and block for a time.

    Notes
    -----
    For a temporary change, this can be used as a context manager::

        # if interactive mode is on
        # then figures will be shown on creation
        plt.ion()
        # This figure will be shown immediately
        fig = plt.figure()

        with plt.ioff():
            # interactive mode will be off
            # figures will not automatically be shown
            fig2 = plt.figure()
            # ...

    To enable optional usage as a context manager, this function returns a
    context manager object, which is not intended to be stored or
    accessed by the user.
    """
    stack = ExitStack()
    stack.callback(ion if isinteractive() else ioff)
    matplotlib.interactive(False)
    uninstall_repl_displayhook()
    return stack


# Note: The return type of ion being AbstractContextManager
# instead of ExitStack is deliberate.
# See https://github.com/matplotlib/matplotlib/issues/27659
# and https://github.com/matplotlib/matplotlib/pull/27667 for more info.
def ion() -> AbstractContextManager:
    """
    Enable interactive mode.

    See `.pyplot.isinteractive` for more details.

    See Also
    --------
    ioff : Disable interactive mode.
    isinteractive : Whether interactive mode is enabled.
    show : Show all figures (and maybe block).
    pause : Show all figures, and block for a time.

    Notes
    -----
    For a temporary change, this can be used as a context manager::

        # if interactive mode is off
        # then figures will not be shown on creation
        plt.ioff()
        # This figure will not be shown immediately
        fig = plt.figure()

        with plt.ion():
            # interactive mode will be on
            # figures will automatically be shown
            fig2 = plt.figure()
            # ...

    To enable optional usage as a context manager, this function returns a
    context manager object, which is not intended to be stored or
    accessed by the user.
    """
    stack = ExitStack()
    stack.callback(ion if isinteractive() else ioff)
    matplotlib.interactive(True)
    install_repl_displayhook()
    return stack


def pause(interval: float) -> None:
    """
    Run the GUI event loop for *interval* seconds.

    If there is an active figure, it will be updated and displayed before the
    pause, and the GUI event loop (if any) will run during the pause.

    This can be used for crude animation.  For more complex animation use
    :mod:`matplotlib.animation`.

    If there is no active figure, sleep for *interval* seconds instead.

    See Also
    --------
    matplotlib.animation : Proper animations
    show : Show all figures and optional block until all figures are closed.
    """
    manager = _pylab_helpers.Gcf.get_active()
    if manager is not None:
        canvas = manager.canvas
        if canvas.figure.stale:
            canvas.draw_idle()
        show(block=False)
        canvas.start_event_loop(interval)
    else:
        time.sleep(interval)


@_copy_docstring_and_deprecators(matplotlib.rc)
def rc(group: str, **kwargs) -> None:
    matplotlib.rc(group, **kwargs)


@_copy_docstring_and_deprecators(matplotlib.rc_context)
def rc_context(
    rc: dict[str, Any] | None = None,
    fname: str | pathlib.Path | os.PathLike | None = None,
) -> AbstractContextManager[None]:
    return matplotlib.rc_context(rc, fname)


@_copy_docstring_and_deprecators(matplotlib.rcdefaults)
def rcdefaults() -> None:
    matplotlib.rcdefaults()
    if matplotlib.is_interactive():
        draw_all()


# getp/get/setp are explicitly reexported so that they show up in pyplot docs.


@_copy_docstring_and_deprecators(matplotlib.artist.getp)
def getp(obj, *args, **kwargs):
    return matplotlib.artist.getp(obj, *args, **kwargs)


@_copy_docstring_and_deprecators(matplotlib.artist.get)
def get(obj, *args, **kwargs):
    return matplotlib.artist.get(obj, *args, **kwargs)


@_copy_docstring_and_deprecators(matplotlib.artist.setp)
def setp(obj, *args, **kwargs):
    return matplotlib.artist.setp(obj, *args, **kwargs)


def xkcd(
    scale: float = 1, length: float = 100, randomness: float = 2
) -> ExitStack:
    """
    Turn on `xkcd <https://xkcd.com/>`_ sketch-style drawing mode.

    This will only have an effect on things drawn after this function is called.

    For best results, install the `xkcd script <https://github.com/ipython/xkcd-font/>`_
    font; xkcd fonts are not packaged with Matplotlib.

    Parameters
    ----------
    scale : float, optional
        The amplitude of the wiggle perpendicular to the source line.
    length : float, optional
        The length of the wiggle along the line.
    randomness : float, optional
        The scale factor by which the length is shrunken or expanded.

    Notes
    -----
    This function works by a number of rcParams, so it will probably
    override others you have set before.

    If you want the effects of this function to be temporary, it can
    be used as a context manager, for example::

        with plt.xkcd():
            # This figure will be in XKCD-style
            fig1 = plt.figure()
            # ...

        # This figure will be in regular style
        fig2 = plt.figure()
    """
    # This cannot be implemented in terms of contextmanager() or rc_context()
    # because this needs to work as a non-contextmanager too.

    if rcParams['text.usetex']:
        raise RuntimeError(
            "xkcd mode is not compatible with text.usetex = True")

    stack = ExitStack()
    stack.callback(rcParams._update_raw, rcParams.copy())  # type: ignore[arg-type]

    from matplotlib import patheffects
    rcParams.update({
        'font.family': ['xkcd', 'xkcd Script', 'Comic Neue', 'Comic Sans MS'],
        'font.size': 14.0,
        'path.sketch': (scale, length, randomness),
        'path.effects': [
            patheffects.withStroke(linewidth=4, foreground="w")],
        'axes.linewidth': 1.5,
        'lines.linewidth': 2.0,
        'figure.facecolor': 'white',
        'grid.linewidth': 0.0,
        'axes.grid': False,
        'axes.unicode_minus': False,
        'axes.edgecolor': 'black',
        'xtick.major.size': 8,
        'xtick.major.width': 3,
        'ytick.major.size': 8,
        'ytick.major.width': 3,
    })

    return stack


## Figures ##

def figure(
    # autoincrement if None, else integer from 1-N
    num: int | str | Figure | SubFigure | None = None,
    # defaults to rc figure.figsize
    figsize: ArrayLike | None = None,
    # defaults to rc figure.dpi
    dpi: float | None = None,
    *,
    # defaults to rc figure.facecolor
    facecolor: ColorType | None = None,
    # defaults to rc figure.edgecolor
    edgecolor: ColorType | None = None,
    frameon: bool = True,
    FigureClass: type[Figure] = Figure,
    clear: bool = False,
    **kwargs
) -> Figure:
    """
    Create a new figure, or activate an existing figure.

    Parameters
    ----------
    num : int or str or `.Figure` or `.SubFigure`, optional
        A unique identifier for the figure.

        If a figure with that identifier already exists, this figure is made
        active and returned. An integer refers to the ``Figure.number``
        attribute, a string refers to the figure label.

        If there is no figure with the identifier or *num* is not given, a new
        figure is created, made active and returned.  If *num* is an int, it
        will be used for the ``Figure.number`` attribute, otherwise, an
        auto-generated integer value is used (starting at 1 and incremented
        for each new figure). If *num* is a string, the figure label and the
        window title is set to this value.  If num is a ``SubFigure``, its
        parent ``Figure`` is activated.

    figsize : (float, float), default: :rc:`figure.figsize`
        Width, height in inches.

    dpi : float, default: :rc:`figure.dpi`
        The resolution of the figure in dots-per-inch.

    facecolor : :mpltype:`color`, default: :rc:`figure.facecolor`
        The background color.

    edgecolor : :mpltype:`color`, default: :rc:`figure.edgecolor`
        The border color.

    frameon : bool, default: True
        If False, suppress drawing the figure frame.

    FigureClass : subclass of `~matplotlib.figure.Figure`
        If set, an instance of this subclass will be created, rather than a
        plain `.Figure`.

    clear : bool, default: False
        If True and the figure already exists, then it is cleared.

    layout : {'constrained', 'compressed', 'tight', 'none', `.LayoutEngine`, None}, \
default: None
        The layout mechanism for positioning of plot elements to avoid
        overlapping Axes decorations (labels, ticks, etc). Note that layout
        managers can measurably slow down figure display.

        - 'constrained': The constrained layout solver adjusts Axes sizes
          to avoid overlapping Axes decorations.  Can handle complex plot
          layouts and colorbars, and is thus recommended.

          See :ref:`constrainedlayout_guide`
          for examples.

        - 'compressed': uses the same algorithm as 'constrained', but
          removes extra space between fixed-aspect-ratio Axes.  Best for
          simple grids of Axes.

        - 'tight': Use the tight layout mechanism. This is a relatively
          simple algorithm that adjusts the subplot parameters so that
          decorations do not overlap. See `.Figure.set_tight_layout` for
          further details.

        - 'none': Do not use a layout engine.

        - A `.LayoutEngine` instance. Builtin layout classes are
          `.ConstrainedLayoutEngine` and `.TightLayoutEngine`, more easily
          accessible by 'constrained' and 'tight'.  Passing an instance
          allows third parties to provide their own layout engine.

        If not given, fall back to using the parameters *tight_layout* and
        *constrained_layout*, including their config defaults
        :rc:`figure.autolayout` and :rc:`figure.constrained_layout.use`.

    **kwargs
        Additional keyword arguments are passed to the `.Figure` constructor.

    Returns
    -------
    `~matplotlib.figure.Figure`

    Notes
    -----
    A newly created figure is passed to the `~.FigureCanvasBase.new_manager`
    method or the `new_figure_manager` function provided by the current
    backend, which install a canvas and a manager on the figure.

    Once this is done, :rc:`figure.hooks` are called, one at a time, on the
    figure; these hooks allow arbitrary customization of the figure (e.g.,
    attaching callbacks) or of associated elements (e.g., modifying the
    toolbar).  See :doc:`/gallery/user_interfaces/mplcvd` for an example of
    toolbar customization.

    If you are creating many figures, make sure you explicitly call
    `.pyplot.close` on the figures you are not using, because this will
    enable pyplot to properly clean up the memory.

    `~matplotlib.rcParams` defines the default values, which can be modified
    in the matplotlibrc file.
    """
    allnums = get_fignums()

    if isinstance(num, FigureBase):
        # type narrowed to `Figure | SubFigure` by combination of input and isinstance
        root_fig = num.get_figure(root=True)
        if root_fig.canvas.manager is None:
            raise ValueError("The passed figure is not managed by pyplot")
        elif (any(param is not None for param in [figsize, dpi, facecolor, edgecolor])
              or not frameon or kwargs) and root_fig.canvas.manager.num in allnums:
            _api.warn_external(
                "Ignoring specified arguments in this call because figure "
                f"with num: {root_fig.canvas.manager.num} already exists")
        _pylab_helpers.Gcf.set_active(root_fig.canvas.manager)
        return root_fig

    next_num = max(allnums) + 1 if allnums else 1
    fig_label = ''
    if num is None:
        num = next_num
    else:
        if (any(param is not None for param in [figsize, dpi, facecolor, edgecolor])
              or not frameon or kwargs) and num in allnums:
            _api.warn_external(
                "Ignoring specified arguments in this call "
                f"because figure with num: {num} already exists")
        if isinstance(num, str):
            fig_label = num
            all_labels = get_figlabels()
            if fig_label not in all_labels:
                if fig_label == 'all':
                    _api.warn_external("close('all') closes all existing figures.")
                num = next_num
            else:
                inum = all_labels.index(fig_label)
                num = allnums[inum]
        else:
            num = int(num)  # crude validation of num argument

    # Type of "num" has narrowed to int, but mypy can't quite see it
    manager = _pylab_helpers.Gcf.get_fig_manager(num)  # type: ignore[arg-type]
    if manager is None:
        max_open_warning = rcParams['figure.max_open_warning']
        if len(allnums) == max_open_warning >= 1:
            _api.warn_external(
                f"More than {max_open_warning} figures have been opened. "
                f"Figures created through the pyplot interface "
                f"(`matplotlib.pyplot.figure`) are retained until explicitly "
                f"closed and may consume too much memory. (To control this "
                f"warning, see the rcParam `figure.max_open_warning`). "
                f"Consider using `matplotlib.pyplot.close()`.",
                RuntimeWarning)

        manager = new_figure_manager(
            num, figsize=figsize, dpi=dpi,
            facecolor=facecolor, edgecolor=edgecolor, frameon=frameon,
            FigureClass=FigureClass, **kwargs)
        fig = manager.canvas.figure
        if fig_label:
            fig.set_label(fig_label)

        for hookspecs in rcParams["figure.hooks"]:
            module_name, dotted_name = hookspecs.split(":")
            obj: Any = importlib.import_module(module_name)
            for part in dotted_name.split("."):
                obj = getattr(obj, part)
            obj(fig)

        _pylab_helpers.Gcf._set_new_active_manager(manager)

        # make sure backends (inline) that we don't ship that expect this
        # to be called in plotting commands to make the figure call show
        # still work.  There is probably a better way to do this in the
        # FigureManager base class.
        draw_if_interactive()

        if _REPL_DISPLAYHOOK is _ReplDisplayHook.PLAIN:
            fig.stale_callback = _auto_draw_if_interactive

    if clear:
        manager.canvas.figure.clear()

    return manager.canvas.figure


def _auto_draw_if_interactive(fig, val):
    """
    An internal helper function for making sure that auto-redrawing
    works as intended in the plain python repl.

    Parameters
    ----------
    fig : Figure
        A figure object which is assumed to be associated with a canvas
    """
    if (val and matplotlib.is_interactive()
            and not fig.canvas.is_saving()
            and not fig.canvas._is_idle_drawing):
        # Some artists can mark themselves as stale in the middle of drawing
        # (e.g. axes position & tick labels being computed at draw time), but
        # this shouldn't trigger a redraw because the current redraw will
        # already take them into account.
        with fig.canvas._idle_draw_cntx():
            fig.canvas.draw_idle()


def gcf() -> Figure:
    """
    Get the current figure.

    If there is currently no figure on the pyplot figure stack, a new one is
    created using `~.pyplot.figure()`.  (To test whether there is currently a
    figure on the pyplot figure stack, check whether `~.pyplot.get_fignums()`
    is empty.)
    """
    manager = _pylab_helpers.Gcf.get_active()
    if manager is not None:
        return manager.canvas.figure
    else:
        return figure()


def fignum_exists(num: int | str) -> bool:
    """
    Return whether the figure with the given id exists.

    Parameters
    ----------
    num : int or str
        A figure identifier.

    Returns
    -------
    bool
        Whether or not a figure with id *num* exists.
    """
    return (
        _pylab_helpers.Gcf.has_fignum(num)
        if isinstance(num, int)
        else num in get_figlabels()
    )


def get_fignums() -> list[int]:
    """Return a list of existing figure numbers."""
    return sorted(_pylab_helpers.Gcf.figs)


def get_figlabels() -> list[Any]:
    """Return a list of existing figure labels."""
    managers = _pylab_helpers.Gcf.get_all_fig_managers()
    managers.sort(key=lambda m: m.num)
    return [m.canvas.figure.get_label() for m in managers]


def get_current_fig_manager() -> FigureManagerBase | None:
    """
    Return the figure manager of the current figure.

    The figure manager is a container for the actual backend-depended window
    that displays the figure on screen.

    If no current figure exists, a new one is created, and its figure
    manager is returned.

    Returns
    -------
    `.FigureManagerBase` or backend-dependent subclass thereof
    """
    return gcf().canvas.manager


@_copy_docstring_and_deprecators(FigureCanvasBase.mpl_connect)
def connect(s: str, func: Callable[[Event], Any]) -> int:
    return gcf().canvas.mpl_connect(s, func)


@_copy_docstring_and_deprecators(FigureCanvasBase.mpl_disconnect)
def disconnect(cid: int) -> None:
    gcf().canvas.mpl_disconnect(cid)


def close(fig: None | int | str | Figure | Literal["all"] = None) -> None:
    """
    Close a figure window, and unregister it from pyplot.

    Parameters
    ----------
    fig : None or int or str or `.Figure`
        The figure to close. There are a number of ways to specify this:

        - *None*: the current figure
        - `.Figure`: the given `.Figure` instance
        - ``int``: a figure number
        - ``str``: a figure name
        - 'all': all figures

    Notes
    -----
    pyplot maintains a reference to figures created with `figure()`. When
    work on the figure is completed, it should be closed, i.e. deregistered
    from pyplot, to free its memory (see also :rc:figure.max_open_warning).
    Closing a figure window created by `show()` automatically deregisters the
    figure. For all other use cases, most prominently `savefig()` without
    `show()`, the figure must be deregistered explicitly using `close()`.
    """
    if fig is None:
        manager = _pylab_helpers.Gcf.get_active()
        if manager is None:
            return
        else:
            _pylab_helpers.Gcf.destroy(manager)
    elif fig == 'all':
        _pylab_helpers.Gcf.destroy_all()
    elif isinstance(fig, int):
        _pylab_helpers.Gcf.destroy(fig)
    elif hasattr(fig, 'int'):
        # if we are dealing with a type UUID, we
        # can use its integer representation
        _pylab_helpers.Gcf.destroy(fig.int)
    elif isinstance(fig, str):
        all_labels = get_figlabels()
        if fig in all_labels:
            num = get_fignums()[all_labels.index(fig)]
            _pylab_helpers.Gcf.destroy(num)
    elif isinstance(fig, Figure):
        _pylab_helpers.Gcf.destroy_fig(fig)
    else:
        raise TypeError("close() argument must be a Figure, an int, a string, "
                        "or None, not %s" % type(fig))


def clf() -> None:
    """Clear the current figure."""
    gcf().clear()


def draw() -> None:
    """
    Redraw the current figure.

    This is used to update a figure that has been altered, but not
    automatically re-drawn.  If interactive mode is on (via `.ion()`), this
    should be only rarely needed, but there may be ways to modify the state of
    a figure without marking it as "stale".  Please report these cases as bugs.

    This is equivalent to calling ``fig.canvas.draw_idle()``, where ``fig`` is
    the current figure.

    See Also
    --------
    .FigureCanvasBase.draw_idle
    .FigureCanvasBase.draw
    """
    gcf().canvas.draw_idle()


@_copy_docstring_and_deprecators(Figure.savefig)
def savefig(*args, **kwargs) -> None:
    fig = gcf()
    # savefig default implementation has no return, so mypy is unhappy
    # presumably this is here because subclasses can return?
    res = fig.savefig(*args, **kwargs)  # type: ignore[func-returns-value]
    fig.canvas.draw_idle()  # Need this if 'transparent=True', to reset colors.
    return res


## Putting things in figures ##


def figlegend(*args, **kwargs) -> Legend:
    return gcf().legend(*args, **kwargs)
if Figure.legend.__doc__:
    figlegend.__doc__ = Figure.legend.__doc__ \
        .replace(" legend(", " figlegend(") \
        .replace("fig.legend(", "plt.figlegend(") \
        .replace("ax.plot(", "plt.plot(")


## Axes ##

@_docstring.interpd
def axes(
    arg: None | tuple[float, float, float, float] = None,
    **kwargs
) -> matplotlib.axes.Axes:
    """
    Add an Axes to the current figure and make it the current Axes.

    Call signatures::

        plt.axes()
        plt.axes(rect, projection=None, polar=False, **kwargs)
        plt.axes(ax)

    Parameters
    ----------
    arg : None or 4-tuple
        The exact behavior of this function depends on the type:

        - *None*: A new full window Axes is added using
          ``subplot(**kwargs)``.
        - 4-tuple of floats *rect* = ``(left, bottom, width, height)``.
          A new Axes is added with dimensions *rect* in normalized
          (0, 1) units using `~.Figure.add_axes` on the current figure.

    projection : {None, 'aitoff', 'hammer', 'lambert', 'mollweide', \
'polar', 'rectilinear', str}, optional
        The projection type of the `~.axes.Axes`. *str* is the name of
        a custom projection, see `~matplotlib.projections`. The default
        None results in a 'rectilinear' projection.

    polar : bool, default: False
        If True, equivalent to projection='polar'.

    sharex, sharey : `~matplotlib.axes.Axes`, optional
        Share the x or y `~matplotlib.axis` with sharex and/or sharey.
        The axis will have the same limits, ticks, and scale as the axis
        of the shared Axes.

    label : str
        A label for the returned Axes.

    Returns
    -------
    `~.axes.Axes`, or a subclass of `~.axes.Axes`
        The returned Axes class depends on the projection used. It is
        `~.axes.Axes` if rectilinear projection is used and
        `.projections.polar.PolarAxes` if polar projection is used.

    Other Parameters
    ----------------
    **kwargs
        This method also takes the keyword arguments for
        the returned Axes class. The keyword arguments for the
        rectilinear Axes class `~.axes.Axes` can be found in
        the following table but there might also be other keyword
        arguments if another projection is used, see the actual Axes
        class.

        %(Axes:kwdoc)s

    See Also
    --------
    .Figure.add_axes
    .pyplot.subplot
    .Figure.add_subplot
    .Figure.subplots
    .pyplot.subplots

    Examples
    --------
    ::

        # Creating a new full window Axes
        plt.axes()

        # Creating a new Axes with specified dimensions and a grey background
        plt.axes((left, bottom, width, height), facecolor='grey')
    """
    fig = gcf()
    pos = kwargs.pop('position', None)
    if arg is None:
        if pos is None:
            return fig.add_subplot(**kwargs)
        else:
            return fig.add_axes(pos, **kwargs)
    else:
        return fig.add_axes(arg, **kwargs)


def delaxes(ax: matplotlib.axes.Axes | None = None) -> None:
    """
    Remove an `~.axes.Axes` (defaulting to the current Axes) from its figure.
    """
    if ax is None:
        ax = gca()
    ax.remove()


def sca(ax: Axes) -> None:
    """
    Set the current Axes to *ax* and the current Figure to the parent of *ax*.
    """
    # Mypy sees ax.figure as potentially None,
    # but if you are calling this, it won't be None
    # Additionally the slight difference between `Figure` and `FigureBase` mypy catches
    fig = ax.get_figure(root=False)
    figure(fig)  # type: ignore[arg-type]
    fig.sca(ax)  # type: ignore[union-attr]


def cla() -> None:
    """Clear the current Axes."""
    # Not generated via boilerplate.py to allow a different docstring.
    return gca().cla()


## More ways of creating Axes ##

@_docstring.interpd
def subplot(*args, **kwargs) -> Axes:
    """
    Add an Axes to the current figure or retrieve an existing Axes.

    This is a wrapper of `.Figure.add_subplot` which provides additional
    behavior when working with the implicit API (see the notes section).

    Call signatures::

       subplot(nrows, ncols, index, **kwargs)
       subplot(pos, **kwargs)
       subplot(**kwargs)
       subplot(ax)

    Parameters
    ----------
    *args : int, (int, int, *index*), or `.SubplotSpec`, default: (1, 1, 1)
        The position of the subplot described by one of

        - Three integers (*nrows*, *ncols*, *index*). The subplot will take the
          *index* position on a grid with *nrows* rows and *ncols* columns.
          *index* starts at 1 in the upper left corner and increases to the
          right. *index* can also be a two-tuple specifying the (*first*,
          *last*) indices (1-based, and including *last*) of the subplot, e.g.,
          ``fig.add_subplot(3, 1, (1, 2))`` makes a subplot that spans the
          upper 2/3 of the figure.
        - A 3-digit integer. The digits are interpreted as if given separately
          as three single-digit integers, i.e. ``fig.add_subplot(235)`` is the
          same as ``fig.add_subplot(2, 3, 5)``. Note that this can only be used
          if there are no more than 9 subplots.
        - A `.SubplotSpec`.

    projection : {None, 'aitoff', 'hammer', 'lambert', 'mollweide', \
'polar', 'rectilinear', str}, optional
        The projection type of the subplot (`~.axes.Axes`). *str* is the name
        of a custom projection, see `~matplotlib.projections`. The default
        None results in a 'rectilinear' projection.

    polar : bool, default: False
        If True, equivalent to projection='polar'.

    sharex, sharey : `~matplotlib.axes.Axes`, optional
        Share the x or y `~matplotlib.axis` with sharex and/or sharey. The
        axis will have the same limits, ticks, and scale as the axis of the
        shared Axes.

    label : str
        A label for the returned Axes.

    Returns
    -------
    `~.axes.Axes`

        The Axes of the subplot. The returned Axes can actually be an instance
        of a subclass, such as `.projections.polar.PolarAxes` for polar
        projections.

    Other Parameters
    ----------------
    **kwargs
        This method also takes the keyword arguments for the returned Axes
        base class; except for the *figure* argument. The keyword arguments
        for the rectilinear base class `~.axes.Axes` can be found in
        the following table but there might also be other keyword
        arguments if another projection is used.

        %(Axes:kwdoc)s

    Notes
    -----
    .. versionchanged:: 3.8
        In versions prior to 3.8, any preexisting Axes that overlap with the new Axes
        beyond sharing a boundary was deleted. Deletion does not happen in more
        recent versions anymore. Use `.Axes.remove` explicitly if needed.

    If you do not want this behavior, use the `.Figure.add_subplot` method
    or the `.pyplot.axes` function instead.

    If no *kwargs* are passed and there exists an Axes in the location
    specified by *args* then that Axes will be returned rather than a new
    Axes being created.

    If *kwargs* are passed and there exists an Axes in the location
    specified by *args*, the projection type is the same, and the
    *kwargs* match with the existing Axes, then the existing Axes is
    returned.  Otherwise a new Axes is created with the specified
    parameters.  We save a reference to the *kwargs* which we use
    for this comparison.  If any of the values in *kwargs* are
    mutable we will not detect the case where they are mutated.
    In these cases we suggest using `.Figure.add_subplot` and the
    explicit Axes API rather than the implicit pyplot API.

    See Also
    --------
    .Figure.add_subplot
    .pyplot.subplots
    .pyplot.axes
    .Figure.subplots

    Examples
    --------
    ::

        plt.subplot(221)

        # equivalent but more general
        ax1 = plt.subplot(2, 2, 1)

        # add a subplot with no frame
        ax2 = plt.subplot(222, frameon=False)

        # add a polar subplot
        plt.subplot(223, projection='polar')

        # add a red subplot that shares the x-axis with ax1
        plt.subplot(224, sharex=ax1, facecolor='red')

        # delete ax2 from the figure
        plt.delaxes(ax2)

        # add ax2 to the figure again
        plt.subplot(ax2)

        # make the first Axes "current" again
        plt.subplot(221)

    """
    # Here we will only normalize `polar=True` vs `projection='polar'` and let
    # downstream code deal with the rest.
    unset = object()
    projection = kwargs.get('projection', unset)
    polar = kwargs.pop('polar', unset)
    if polar is not unset and polar:
        # if we got mixed messages from the user, raise
        if projection is not unset and projection != 'polar':
            raise ValueError(
                f"polar={polar}, yet projection={projection!r}. "
                "Only one of these arguments should be supplied."
            )
        kwargs['projection'] = projection = 'polar'

    # if subplot called without arguments, create subplot(1, 1, 1)
    if len(args) == 0:
        args = (1, 1, 1)

    # This check was added because it is very easy to type subplot(1, 2, False)
    # when subplots(1, 2, False) was intended (sharex=False, that is). In most
    # cases, no error will ever occur, but mysterious behavior can result
    # because what was intended to be the sharex argument is instead treated as
    # a subplot index for subplot()
    if len(args) >= 3 and isinstance(args[2], bool):
        _api.warn_external("The subplot index argument to subplot() appears "
                           "to be a boolean. Did you intend to use "
                           "subplots()?")
    # Check for nrows and ncols, which are not valid subplot args:
    if 'nrows' in kwargs or 'ncols' in kwargs:
        raise TypeError("subplot() got an unexpected keyword argument 'ncols' "
                        "and/or 'nrows'.  Did you intend to call subplots()?")

    fig = gcf()

    # First, search for an existing subplot with a matching spec.
    key = SubplotSpec._from_subplot_args(fig, args)

    for ax in fig.axes:
        # If we found an Axes at the position, we can reuse it if the user passed no
        # kwargs or if the Axes class and kwargs are identical.
        if (ax.get_subplotspec() == key
            and (kwargs == {}
                 or (ax._projection_init
                     == fig._process_projection_requirements(**kwargs)))):
            break
    else:
        # we have exhausted the known Axes and none match, make a new one!
        ax = fig.add_subplot(*args, **kwargs)

    fig.sca(ax)

    return ax


@overload
def subplots(
    nrows: Literal[1] = ...,
    ncols: Literal[1] = ...,
    *,
    sharex: bool | Literal["none", "all", "row", "col"] = ...,
    sharey: bool | Literal["none", "all", "row", "col"] = ...,
    squeeze: Literal[True] = ...,
    width_ratios: Sequence[float] | None = ...,
    height_ratios: Sequence[float] | None = ...,
    subplot_kw: dict[str, Any] | None = ...,
    gridspec_kw: dict[str, Any] | None = ...,
    **fig_kw
) -> tuple[Figure, Axes]:
    ...


@overload
def subplots(
    nrows: int = ...,
    ncols: int = ...,
    *,
    sharex: bool | Literal["none", "all", "row", "col"] = ...,
    sharey: bool | Literal["none", "all", "row", "col"] = ...,
    squeeze: Literal[False],
    width_ratios: Sequence[float] | None = ...,
    height_ratios: Sequence[float] | None = ...,
    subplot_kw: dict[str, Any] | None = ...,
    gridspec_kw: dict[str, Any] | None = ...,
    **fig_kw
) -> tuple[Figure, np.ndarray]:  # TODO numpy/numpy#24738
    ...


@overload
def subplots(
    nrows: int = ...,
    ncols: int = ...,
    *,
    sharex: bool | Literal["none", "all", "row", "col"] = ...,
    sharey: bool | Literal["none", "all", "row", "col"] = ...,
    squeeze: bool = ...,
    width_ratios: Sequence[float] | None = ...,
    height_ratios: Sequence[float] | None = ...,
    subplot_kw: dict[str, Any] | None = ...,
    gridspec_kw: dict[str, Any] | None = ...,
    **fig_kw
) -> tuple[Figure, Any]:
    ...


def subplots(
    nrows: int = 1, ncols: int = 1, *,
    sharex: bool | Literal["none", "all", "row", "col"] = False,
    sharey: bool | Literal["none", "all", "row", "col"] = False,
    squeeze: bool = True,
    width_ratios: Sequence[float] | None = None,
    height_ratios: Sequence[float] | None = None,
    subplot_kw: dict[str, Any] | None = None,
    gridspec_kw: dict[str, Any] | None = None,
    **fig_kw
) -> tuple[Figure, Any]:
    """
    Create a figure and a set of subplots.

    This utility wrapper makes it convenient to create common layouts of
    subplots, including the enclosing figure object, in a single call.

    Parameters
    ----------
    nrows, ncols : int, default: 1
        Number of rows/columns of the subplot grid.

    sharex, sharey : bool or {'none', 'all', 'row', 'col'}, default: False
        Controls sharing of properties among x (*sharex*) or y (*sharey*)
        axes:

        - True or 'all': x- or y-axis will be shared among all subplots.
        - False or 'none': each subplot x- or y-axis will be independent.
        - 'row': each subplot row will share an x- or y-axis.
        - 'col': each subplot column will share an x- or y-axis.

        When subplots have a shared x-axis along a column, only the x tick
        labels of the bottom subplot are created. Similarly, when subplots
        have a shared y-axis along a row, only the y tick labels of the first
        column subplot are created. To later turn other subplots' ticklabels
        on, use `~matplotlib.axes.Axes.tick_params`.

        When subplots have a shared axis that has units, calling
        `.Axis.set_units` will update each axis with the new units.

        Note that it is not possible to unshare axes.

    squeeze : bool, default: True
        - If True, extra dimensions are squeezed out from the returned
          array of `~matplotlib.axes.Axes`:

          - if only one subplot is constructed (nrows=ncols=1), the
            resulting single Axes object is returned as a scalar.
          - for Nx1 or 1xM subplots, the returned object is a 1D numpy
            object array of Axes objects.
          - for NxM, subplots with N>1 and M>1 are returned as a 2D array.

        - If False, no squeezing at all is done: the returned Axes object is
          always a 2D array containing Axes instances, even if it ends up
          being 1x1.

    width_ratios : array-like of length *ncols*, optional
        Defines the relative widths of the columns. Each column gets a
        relative width of ``width_ratios[i] / sum(width_ratios)``.
        If not given, all columns will have the same width.  Equivalent
        to ``gridspec_kw={'width_ratios': [...]}``.

    height_ratios : array-like of length *nrows*, optional
        Defines the relative heights of the rows. Each row gets a
        relative height of ``height_ratios[i] / sum(height_ratios)``.
        If not given, all rows will have the same height. Convenience
        for ``gridspec_kw={'height_ratios': [...]}``.

    subplot_kw : dict, optional
        Dict with keywords passed to the
        `~matplotlib.figure.Figure.add_subplot` call used to create each
        subplot.

    gridspec_kw : dict, optional
        Dict with keywords passed to the `~matplotlib.gridspec.GridSpec`
        constructor used to create the grid the subplots are placed on.

    **fig_kw
        All additional keyword arguments are passed to the
        `.pyplot.figure` call.

    Returns
    -------
    fig : `.Figure`

    ax : `~matplotlib.axes.Axes` or array of Axes
        *ax* can be either a single `~.axes.Axes` object, or an array of Axes
        objects if more than one subplot was created.  The dimensions of the
        resulting array can be controlled with the squeeze keyword, see above.

        Typical idioms for handling the return value are::

            # using the variable ax for single a Axes
            fig, ax = plt.subplots()

            # using the variable axs for multiple Axes
            fig, axs = plt.subplots(2, 2)

            # using tuple unpacking for multiple Axes
            fig, (ax1, ax2) = plt.subplots(1, 2)
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2)

        The names ``ax`` and pluralized ``axs`` are preferred over ``axes``
        because for the latter it's not clear if it refers to a single
        `~.axes.Axes` instance or a collection of these.

    See Also
    --------
    .pyplot.figure
    .pyplot.subplot
    .pyplot.axes
    .Figure.subplots
    .Figure.add_subplot

    Examples
    --------
    ::

        # First create some toy data:
        x = np.linspace(0, 2*np.pi, 400)
        y = np.sin(x**2)

        # Create just a figure and only one subplot
        fig, ax = plt.subplots()
        ax.plot(x, y)
        ax.set_title('Simple plot')

        # Create two subplots and unpack the output array immediately
        f, (ax1, ax2) = plt.subplots(1, 2, sharey=True)
        ax1.plot(x, y)
        ax1.set_title('Sharing Y axis')
        ax2.scatter(x, y)

        # Create four polar Axes and access them through the returned array
        fig, axs = plt.subplots(2, 2, subplot_kw=dict(projection="polar"))
        axs[0, 0].plot(x, y)
        axs[1, 1].scatter(x, y)

        # Share a X axis with each column of subplots
        plt.subplots(2, 2, sharex='col')

        # Share a Y axis with each row of subplots
        plt.subplots(2, 2, sharey='row')

        # Share both X and Y axes with all subplots
        plt.subplots(2, 2, sharex='all', sharey='all')

        # Note that this is the same as
        plt.subplots(2, 2, sharex=True, sharey=True)

        # Create figure number 10 with a single subplot
        # and clears it if it already exists.
        fig, ax = plt.subplots(num=10, clear=True)

    """
    fig = figure(**fig_kw)
    axs = fig.subplots(nrows=nrows, ncols=ncols, sharex=sharex, sharey=sharey,
                       squeeze=squeeze, subplot_kw=subplot_kw,
                       gridspec_kw=gridspec_kw, height_ratios=height_ratios,
                       width_ratios=width_ratios)
    return fig, axs


@overload
def subplot_mosaic(
    mosaic: str,
    *,
    sharex: bool = ...,
    sharey: bool = ...,
    width_ratios: ArrayLike | None = ...,
    height_ratios: ArrayLike | None = ...,
    empty_sentinel: str = ...,
    subplot_kw: dict[str, Any] | None = ...,
    gridspec_kw: dict[str, Any] | None = ...,
    per_subplot_kw: dict[str | tuple[str, ...], dict[str, Any]] | None = ...,
    **fig_kw: Any
) -> tuple[Figure, dict[str, matplotlib.axes.Axes]]: ...


@overload
def subplot_mosaic(
    mosaic: list[HashableList[_T]],
    *,
    sharex: bool = ...,
    sharey: bool = ...,
    width_ratios: ArrayLike | None = ...,
    height_ratios: ArrayLike | None = ...,
    empty_sentinel: _T = ...,
    subplot_kw: dict[str, Any] | None = ...,
    gridspec_kw: dict[str, Any] | None = ...,
    per_subplot_kw: dict[_T | tuple[_T, ...], dict[str, Any]] | None = ...,
    **fig_kw: Any
) -> tuple[Figure, dict[_T, matplotlib.axes.Axes]]: ...


@overload
def subplot_mosaic(
    mosaic: list[HashableList[Hashable]],
    *,
    sharex: bool = ...,
    sharey: bool = ...,
    width_ratios: ArrayLike | None = ...,
    height_ratios: ArrayLike | None = ...,
    empty_sentinel: Any = ...,
    subplot_kw: dict[str, Any] | None = ...,
    gridspec_kw: dict[str, Any] | None = ...,
    per_subplot_kw: dict[Hashable | tuple[Hashable, ...], dict[str, Any]] | None = ...,
    **fig_kw: Any
) -> tuple[Figure, dict[Hashable, matplotlib.axes.Axes]]: ...


def subplot_mosaic(
    mosaic: str | list[HashableList[_T]] | list[HashableList[Hashable]],
    *,
    sharex: bool = False,
    sharey: bool = False,
    width_ratios: ArrayLike | None = None,
    height_ratios: ArrayLike | None = None,
    empty_sentinel: Any = '.',
    subplot_kw: dict[str, Any] | None = None,
    gridspec_kw: dict[str, Any] | None = None,
    per_subplot_kw: dict[str | tuple[str, ...], dict[str, Any]] |
                    dict[_T | tuple[_T, ...], dict[str, Any]] |
                    dict[Hashable | tuple[Hashable, ...], dict[str, Any]] | None = None,
    **fig_kw: Any
) -> tuple[Figure, dict[str, matplotlib.axes.Axes]] | \
     tuple[Figure, dict[_T, matplotlib.axes.Axes]] | \
     tuple[Figure, dict[Hashable, matplotlib.axes.Axes]]:
    """
    Build a layout of Axes based on ASCII art or nested lists.

    This is a helper function to build complex GridSpec layouts visually.

    See :ref:`mosaic`
    for an example and full API documentation

    Parameters
    ----------
    mosaic : list of list of {hashable or nested} or str

        A visual layout of how you want your Axes to be arranged
        labeled as strings.  For example ::

           x = [['A panel', 'A panel', 'edge'],
                ['C panel', '.',       'edge']]

        produces 4 Axes:

        - 'A panel' which is 1 row high and spans the first two columns
        - 'edge' which is 2 rows high and is on the right edge
        - 'C panel' which in 1 row and 1 column wide in the bottom left
        - a blank space 1 row and 1 column wide in the bottom center

        Any of the entries in the layout can be a list of lists
        of the same form to create nested layouts.

        If input is a str, then it must be of the form ::

          '''
          AAE
          C.E
          '''

        where each character is a column and each line is a row.
        This only allows only single character Axes labels and does
        not allow nesting but is very terse.

    sharex, sharey : bool, default: False
        If True, the x-axis (*sharex*) or y-axis (*sharey*) will be shared
        among all subplots.  In that case, tick label visibility and axis units
        behave as for `subplots`.  If False, each subplot's x- or y-axis will
        be independent.

    width_ratios : array-like of length *ncols*, optional
        Defines the relative widths of the columns. Each column gets a
        relative width of ``width_ratios[i] / sum(width_ratios)``.
        If not given, all columns will have the same width.  Convenience
        for ``gridspec_kw={'width_ratios': [...]}``.

    height_ratios : array-like of length *nrows*, optional
        Defines the relative heights of the rows. Each row gets a
        relative height of ``height_ratios[i] / sum(height_ratios)``.
        If not given, all rows will have the same height. Convenience
        for ``gridspec_kw={'height_ratios': [...]}``.

    empty_sentinel : object, optional
        Entry in the layout to mean "leave this space empty".  Defaults
        to ``'.'``. Note, if *layout* is a string, it is processed via
        `inspect.cleandoc` to remove leading white space, which may
        interfere with using white-space as the empty sentinel.

    subplot_kw : dict, optional
        Dictionary with keywords passed to the `.Figure.add_subplot` call
        used to create each subplot.  These values may be overridden by
        values in *per_subplot_kw*.

    per_subplot_kw : dict, optional
        A dictionary mapping the Axes identifiers or tuples of identifiers
        to a dictionary of keyword arguments to be passed to the
        `.Figure.add_subplot` call used to create each subplot.  The values
        in these dictionaries have precedence over the values in
        *subplot_kw*.

        If *mosaic* is a string, and thus all keys are single characters,
        it is possible to use a single string instead of a tuple as keys;
        i.e. ``"AB"`` is equivalent to ``("A", "B")``.

        .. versionadded:: 3.7

    gridspec_kw : dict, optional
        Dictionary with keywords passed to the `.GridSpec` constructor used
        to create the grid the subplots are placed on.

    **fig_kw
        All additional keyword arguments are passed to the
        `.pyplot.figure` call.

    Returns
    -------
    fig : `.Figure`
       The new figure

    dict[label, Axes]
       A dictionary mapping the labels to the Axes objects.  The order of
       the Axes is left-to-right and top-to-bottom of their position in the
       total layout.

    """
    fig = figure(**fig_kw)
    ax_dict = fig.subplot_mosaic(  # type: ignore[misc]
        mosaic,  # type: ignore[arg-type]
        sharex=sharex, sharey=sharey,
        height_ratios=height_ratios, width_ratios=width_ratios,
        subplot_kw=subplot_kw, gridspec_kw=gridspec_kw,
        empty_sentinel=empty_sentinel,
        per_subplot_kw=per_subplot_kw,  # type: ignore[arg-type]
    )
    return fig, ax_dict


def subplot2grid(
    shape: tuple[int, int], loc: tuple[int, int],
    rowspan: int = 1, colspan: int = 1,
    fig: Figure | None = None,
    **kwargs
) -> matplotlib.axes.Axes:
    """
    Create a subplot at a specific location inside a regular grid.

    Parameters
    ----------
    shape : (int, int)
        Number of rows and of columns of the grid in which to place axis.
    loc : (int, int)
        Row number and column number of the axis location within the grid.
    rowspan : int, default: 1
        Number of rows for the axis to span downwards.
    colspan : int, default: 1
        Number of columns for the axis to span to the right.
    fig : `.Figure`, optional
        Figure to place the subplot in. Defaults to the current figure.
    **kwargs
        Additional keyword arguments are handed to `~.Figure.add_subplot`.

    Returns
    -------
    `~.axes.Axes`

        The Axes of the subplot. The returned Axes can actually be an instance
        of a subclass, such as `.projections.polar.PolarAxes` for polar
        projections.

    Notes
    -----
    The following call ::

        ax = subplot2grid((nrows, ncols), (row, col), rowspan, colspan)

    is identical to ::

        fig = gcf()
        gs = fig.add_gridspec(nrows, ncols)
        ax = fig.add_subplot(gs[row:row+rowspan, col:col+colspan])
    """
    if fig is None:
        fig = gcf()
    rows, cols = shape
    gs = GridSpec._check_gridspec_exists(fig, rows, cols)
    subplotspec = gs.new_subplotspec(loc, rowspan=rowspan, colspan=colspan)
    return fig.add_subplot(subplotspec, **kwargs)


def twinx(ax: matplotlib.axes.Axes | None = None) -> _AxesBase:
    """
    Make and return a second Axes that shares the *x*-axis.  The new Axes will
    overlay *ax* (or the current Axes if *ax* is *None*), and its ticks will be
    on the right.

    Examples
    --------
    :doc:`/gallery/subplots_axes_and_figures/two_scales`
    """
    if ax is None:
        ax = gca()
    ax1 = ax.twinx()
    return ax1


def twiny(ax: matplotlib.axes.Axes | None = None) -> _AxesBase:
    """
    Make and return a second Axes that shares the *y*-axis.  The new Axes will
    overlay *ax* (or the current Axes if *ax* is *None*), and its ticks will be
    on the top.

    Examples
    --------
    :doc:`/gallery/subplots_axes_and_figures/two_scales`
    """
    if ax is None:
        ax = gca()
    ax1 = ax.twiny()
    return ax1


def subplot_tool(targetfig: Figure | None = None) -> SubplotTool | None:
    """
    Launch a subplot tool window for a figure.

    Returns
    -------
    `matplotlib.widgets.SubplotTool`
    """
    if targetfig is None:
        targetfig = gcf()
    tb = targetfig.canvas.manager.toolbar  # type: ignore[union-attr]
    if hasattr(tb, "configure_subplots"):  # toolbar2
        from matplotlib.backend_bases import NavigationToolbar2
        return cast(NavigationToolbar2, tb).configure_subplots()
    elif hasattr(tb, "trigger_tool"):  # toolmanager
        from matplotlib.backend_bases import ToolContainerBase
        cast(ToolContainerBase, tb).trigger_tool("subplots")
        return None
    else:
        raise ValueError("subplot_tool can only be launched for figures with "
                         "an associated toolbar")


def box(on: bool | None = None) -> None:
    """
    Turn the Axes box on or off on the current Axes.

    Parameters
    ----------
    on : bool or None
        The new `~matplotlib.axes.Axes` box state. If ``None``, toggle
        the state.

    See Also
    --------
    :meth:`matplotlib.axes.Axes.set_frame_on`
    :meth:`matplotlib.axes.Axes.get_frame_on`
    """
    ax = gca()
    if on is None:
        on = not ax.get_frame_on()
    ax.set_frame_on(on)

## Axis ##


def xlim(*args, **kwargs) -> tuple[float, float]:
    """
    Get or set the x limits of the current Axes.

    Call signatures::

        left, right = xlim()  # return the current xlim
        xlim((left, right))   # set the xlim to left, right
        xlim(left, right)     # set the xlim to left, right

    If you do not specify args, you can pass *left* or *right* as kwargs,
    i.e.::

        xlim(right=3)  # adjust the right leaving left unchanged
        xlim(left=1)  # adjust the left leaving right unchanged

    Setting limits turns autoscaling off for the x-axis.

    Returns
    -------
    left, right
        A tuple of the new x-axis limits.

    Notes
    -----
    Calling this function with no arguments (e.g. ``xlim()``) is the pyplot
    equivalent of calling `~.Axes.get_xlim` on the current Axes.
    Calling this function with arguments is the pyplot equivalent of calling
    `~.Axes.set_xlim` on the current Axes. All arguments are passed though.
    """
    ax = gca()
    if not args and not kwargs:
        return ax.get_xlim()
    ret = ax.set_xlim(*args, **kwargs)
    return ret


def ylim(*args, **kwargs) -> tuple[float, float]:
    """
    Get or set the y-limits of the current Axes.

    Call signatures::

        bottom, top = ylim()  # return the current ylim
        ylim((bottom, top))   # set the ylim to bottom, top
        ylim(bottom, top)     # set the ylim to bottom, top

    If you do not specify args, you can alternatively pass *bottom* or
    *top* as kwargs, i.e.::

        ylim(top=3)  # adjust the top leaving bottom unchanged
        ylim(bottom=1)  # adjust the bottom leaving top unchanged

    Setting limits turns autoscaling off for the y-axis.

    Returns
    -------
    bottom, top
        A tuple of the new y-axis limits.

    Notes
    -----
    Calling this function with no arguments (e.g. ``ylim()``) is the pyplot
    equivalent of calling `~.Axes.get_ylim` on the current Axes.
    Calling this function with arguments is the pyplot equivalent of calling
    `~.Axes.set_ylim` on the current Axes. All arguments are passed though.
    """
    ax = gca()
    if not args and not kwargs:
        return ax.get_ylim()
    ret = ax.set_ylim(*args, **kwargs)
    return ret


def xticks(
    ticks: ArrayLike | None = None,
    labels: Sequence[str] | None = None,
    *,
    minor: bool = False,
    **kwargs
) -> tuple[list[Tick] | np.ndarray, list[Text]]:
    """
    Get or set the current tick locations and labels of the x-axis.

    Pass no arguments to return the current values without modifying them.

    Parameters
    ----------
    ticks : array-like, optional
        The list of xtick locations.  Passing an empty list removes all xticks.
    labels : array-like, optional
        The labels to place at the given *ticks* locations.  This argument can
        only be passed if *ticks* is passed as well.
    minor : bool, default: False
        If ``False``, get/set the major ticks/labels; if ``True``, the minor
        ticks/labels.
    **kwargs
        `.Text` properties can be used to control the appearance of the labels.

        .. warning::

            This only sets the properties of the current ticks, which is
            only sufficient if you either pass *ticks*, resulting in a
            fixed list of ticks, or if the plot is static.

            Ticks are not guaranteed to be persistent. Various operations
            can create, delete and modify the Tick instances. There is an
            imminent risk that these settings can get lost if you work on
            the figure further (including also panning/zooming on a
            displayed figure).

            Use `~.pyplot.tick_params` instead if possible.


    Returns
    -------
    locs
        The list of xtick locations.
    labels
        The list of xlabel `.Text` objects.

    Notes
    -----
    Calling this function with no arguments (e.g. ``xticks()``) is the pyplot
    equivalent of calling `~.Axes.get_xticks` and `~.Axes.get_xticklabels` on
    the current Axes.
    Calling this function with arguments is the pyplot equivalent of calling
    `~.Axes.set_xticks` and `~.Axes.set_xticklabels` on the current Axes.

    Examples
    --------
    >>> locs, labels = xticks()  # Get the current locations and labels.
    >>> xticks(np.arange(0, 1, step=0.2))  # Set label locations.
    >>> xticks(np.arange(3), ['Tom', 'Dick', 'Sue'])  # Set text labels.
    >>> xticks([0, 1, 2], ['January', 'February', 'March'],
    ...        rotation=20)  # Set text labels and properties.
    >>> xticks([])  # Disable xticks.
    """
    ax = gca()

    locs: list[Tick] | np.ndarray
    if ticks is None:
        locs = ax.get_xticks(minor=minor)
        if labels is not None:
            raise TypeError("xticks(): Parameter 'labels' can't be set "
                            "without setting 'ticks'")
    else:
        locs = ax.set_xticks(ticks, minor=minor)

    labels_out: list[Text] = []
    if labels is None:
        labels_out = ax.get_xticklabels(minor=minor)
        for l in labels_out:
            l._internal_update(kwargs)
    else:
        labels_out = ax.set_xticklabels(labels, minor=minor, **kwargs)

    return locs, labels_out


def yticks(
    ticks: ArrayLike | None = None,
    labels: Sequence[str] | None = None,
    *,
    minor: bool = False,
    **kwargs
) -> tuple[list[Tick] | np.ndarray, list[Text]]:
    """
    Get or set the current tick locations and labels of the y-axis.

    Pass no arguments to return the current values without modifying them.

    Parameters
    ----------
    ticks : array-like, optional
        The list of ytick locations.  Passing an empty list removes all yticks.
    labels : array-like, optional
        The labels to place at the given *ticks* locations.  This argument can
        only be passed if *ticks* is passed as well.
    minor : bool, default: False
        If ``False``, get/set the major ticks/labels; if ``True``, the minor
        ticks/labels.
    **kwargs
        `.Text` properties can be used to control the appearance of the labels.

        .. warning::

            This only sets the properties of the current ticks, which is
            only sufficient if you either pass *ticks*, resulting in a
            fixed list of ticks, or if the plot is static.

            Ticks are not guaranteed to be persistent. Various operations
            can create, delete and modify the Tick instances. There is an
            imminent risk that these settings can get lost if you work on
            the figure further (including also panning/zooming on a
            displayed figure).

            Use `~.pyplot.tick_params` instead if possible.

    Returns
    -------
    locs
        The list of ytick locations.
    labels
        The list of ylabel `.Text` objects.

    Notes
    -----
    Calling this function with no arguments (e.g. ``yticks()``) is the pyplot
    equivalent of calling `~.Axes.get_yticks` and `~.Axes.get_yticklabels` on
    the current Axes.
    Calling this function with arguments is the pyplot equivalent of calling
    `~.Axes.set_yticks` and `~.Axes.set_yticklabels` on the current Axes.

    Examples
    --------
    >>> locs, labels = yticks()  # Get the current locations and labels.
    >>> yticks(np.arange(0, 1, step=0.2))  # Set label locations.
    >>> yticks(np.arange(3), ['Tom', 'Dick', 'Sue'])  # Set text labels.
    >>> yticks([0, 1, 2], ['January', 'February', 'March'],
    ...        rotation=45)  # Set text labels and properties.
    >>> yticks([])  # Disable yticks.
    """
    ax = gca()

    locs: list[Tick] | np.ndarray
    if ticks is None:
        locs = ax.get_yticks(minor=minor)
        if labels is not None:
            raise TypeError("yticks(): Parameter 'labels' can't be set "
                            "without setting 'ticks'")
    else:
        locs = ax.set_yticks(ticks, minor=minor)

    labels_out: list[Text] = []
    if labels is None:
        labels_out = ax.get_yticklabels(minor=minor)
        for l in labels_out:
            l._internal_update(kwargs)
    else:
        labels_out = ax.set_yticklabels(labels, minor=minor, **kwargs)

    return locs, labels_out


def rgrids(
    radii: ArrayLike | None = None,
    labels: Sequence[str | Text] | None = None,
    angle: float | None = None,
    fmt: str | None = None,
    **kwargs
) -> tuple[list[Line2D], list[Text]]:
    """
    Get or set the radial gridlines on the current polar plot.

    Call signatures::

     lines, labels = rgrids()
     lines, labels = rgrids(radii, labels=None, angle=22.5, fmt=None, **kwargs)

    When called with no arguments, `.rgrids` simply returns the tuple
    (*lines*, *labels*). When called with arguments, the labels will
    appear at the specified radial distances and angle.

    Parameters
    ----------
    radii : tuple with floats
        The radii for the radial gridlines

    labels : tuple with strings or None
        The labels to use at each radial gridline. The
        `matplotlib.ticker.ScalarFormatter` will be used if None.

    angle : float
        The angular position of the radius labels in degrees.

    fmt : str or None
        Format string used in `matplotlib.ticker.FormatStrFormatter`.
        For example '%f'.

    Returns
    -------
    lines : list of `.lines.Line2D`
        The radial gridlines.

    labels : list of `.text.Text`
        The tick labels.

    Other Parameters
    ----------------
    **kwargs
        *kwargs* are optional `.Text` properties for the labels.

    See Also
    --------
    .pyplot.thetagrids
    .projections.polar.PolarAxes.set_rgrids
    .Axis.get_gridlines
    .Axis.get_ticklabels

    Examples
    --------
    ::

      # set the locations of the radial gridlines
      lines, labels = rgrids( (0.25, 0.5, 1.0) )

      # set the locations and labels of the radial gridlines
      lines, labels = rgrids( (0.25, 0.5, 1.0), ('Tom', 'Dick', 'Harry' ))
    """
    ax = gca()
    if not isinstance(ax, PolarAxes):
        raise RuntimeError('rgrids only defined for polar Axes')
    if all(p is None for p in [radii, labels, angle, fmt]) and not kwargs:
        lines_out: list[Line2D] = ax.yaxis.get_gridlines()
        labels_out: list[Text] = ax.yaxis.get_ticklabels()
    elif radii is None:
        raise TypeError("'radii' cannot be None when other parameters are passed")
    else:
        lines_out, labels_out = ax.set_rgrids(
            radii, labels=labels, angle=angle, fmt=fmt, **kwargs)
    return lines_out, labels_out


def thetagrids(
    angles: ArrayLike | None = None,
    labels: Sequence[str | Text] | None = None,
    fmt: str | None = None,
    **kwargs
) -> tuple[list[Line2D], list[Text]]:
    """
    Get or set the theta gridlines on the current polar plot.

    Call signatures::

     lines, labels = thetagrids()
     lines, labels = thetagrids(angles, labels=None, fmt=None, **kwargs)

    When called with no arguments, `.thetagrids` simply returns the tuple
    (*lines*, *labels*). When called with arguments, the labels will
    appear at the specified angles.

    Parameters
    ----------
    angles : tuple with floats, degrees
        The angles of the theta gridlines.

    labels : tuple with strings or None
        The labels to use at each radial gridline. The
        `.projections.polar.ThetaFormatter` will be used if None.

    fmt : str or None
        Format string used in `matplotlib.ticker.FormatStrFormatter`.
        For example '%f'. Note that the angle in radians will be used.

    Returns
    -------
    lines : list of `.lines.Line2D`
        The theta gridlines.

    labels : list of `.text.Text`
        The tick labels.

    Other Parameters
    ----------------
    **kwargs
        *kwargs* are optional `.Text` properties for the labels.

    See Also
    --------
    .pyplot.rgrids
    .projections.polar.PolarAxes.set_thetagrids
    .Axis.get_gridlines
    .Axis.get_ticklabels

    Examples
    --------
    ::

      # set the locations of the angular gridlines
      lines, labels = thetagrids(range(45, 360, 90))

      # set the locations and labels of the angular gridlines
      lines, labels = thetagrids(range(45, 360, 90), ('NE', 'NW', 'SW', 'SE'))
    """
    ax = gca()
    if not isinstance(ax, PolarAxes):
        raise RuntimeError('thetagrids only defined for polar Axes')
    if all(param is None for param in [angles, labels, fmt]) and not kwargs:
        lines_out: list[Line2D] = ax.xaxis.get_ticklines()
        labels_out: list[Text] = ax.xaxis.get_ticklabels()
    elif angles is None:
        raise TypeError("'angles' cannot be None when other parameters are passed")
    else:
        lines_out, labels_out = ax.set_thetagrids(angles,
                                                  labels=labels, fmt=fmt,
                                                  **kwargs)
    return lines_out, labels_out


@_api.deprecated("3.7", pending=True)
def get_plot_commands() -> list[str]:
    """
    Get a sorted list of all of the plotting commands.
    """
    NON_PLOT_COMMANDS = {
        'connect', 'disconnect', 'get_current_fig_manager', 'ginput',
        'new_figure_manager', 'waitforbuttonpress'}
    return [name for name in _get_pyplot_commands()
            if name not in NON_PLOT_COMMANDS]


def _get_pyplot_commands() -> list[str]:
    # This works by searching for all functions in this module and removing
    # a few hard-coded exclusions, as well as all of the colormap-setting
    # functions, and anything marked as private with a preceding underscore.
    exclude = {'colormaps', 'colors', 'get_plot_commands', *colormaps}
    this_module = inspect.getmodule(get_plot_commands)
    return sorted(
        name for name, obj in globals().items()
        if not name.startswith('_') and name not in exclude
           and inspect.isfunction(obj)
           and inspect.getmodule(obj) is this_module)


## Plotting part 1: manually generated functions and wrappers ##


@_copy_docstring_and_deprecators(Figure.colorbar)
def colorbar(
    mappable: ScalarMappable | ColorizingArtist | None = None,
    cax: matplotlib.axes.Axes | None = None,
    ax: matplotlib.axes.Axes | Iterable[matplotlib.axes.Axes] | None = None,
    **kwargs
) -> Colorbar:
    if mappable is None:
        mappable = gci()
        if mappable is None:
            raise RuntimeError('No mappable was found to use for colorbar '
                               'creation. First define a mappable such as '
                               'an image (with imshow) or a contour set ('
                               'with contourf).')
    ret = gcf().colorbar(mappable, cax=cax, ax=ax, **kwargs)
    return ret


def clim(vmin: float | None = None, vmax: float | None = None) -> None:
    """
    Set the color limits of the current image.

    If either *vmin* or *vmax* is None, the image min/max respectively
    will be used for color scaling.

    If you want to set the clim of multiple images, use
    `~.ScalarMappable.set_clim` on every image, for example::

      for im in gca().get_images():
          im.set_clim(0, 0.5)

    """
    im = gci()
    if im is None:
        raise RuntimeError('You must first define an image, e.g., with imshow')

    im.set_clim(vmin, vmax)


def get_cmap(name: Colormap | str | None = None, lut: int | None = None) -> Colormap:
    """
    Get a colormap instance, defaulting to rc values if *name* is None.

    Parameters
    ----------
    name : `~matplotlib.colors.Colormap` or str or None, default: None
        If a `.Colormap` instance, it will be returned. Otherwise, the name of
        a colormap known to Matplotlib, which will be resampled by *lut*. The
        default, None, means :rc:`image.cmap`.
    lut : int or None, default: None
        If *name* is not already a Colormap instance and *lut* is not None, the
        colormap will be resampled to have *lut* entries in the lookup table.

    Returns
    -------
    Colormap
    """
    if name is None:
        name = rcParams['image.cmap']
    if isinstance(name, Colormap):
        return name
    _api.check_in_list(sorted(_colormaps), name=name)
    if lut is None:
        return _colormaps[name]
    else:
        return _colormaps[name].resampled(lut)


def set_cmap(cmap: Colormap | str) -> None:
    """
    Set the default colormap, and applies it to the current image if any.

    Parameters
    ----------
    cmap : `~matplotlib.colors.Colormap` or str
        A colormap instance or the name of a registered colormap.

    See Also
    --------
    colormaps
    get_cmap
    """
    cmap = get_cmap(cmap)

    rc('image', cmap=cmap.name)
    im = gci()

    if im is not None:
        im.set_cmap(cmap)


@_copy_docstring_and_deprecators(matplotlib.image.imread)
def imread(
        fname: str | pathlib.Path | BinaryIO, format: str | None = None
) -> np.ndarray:
    return matplotlib.image.imread(fname, format)


@_copy_docstring_and_deprecators(matplotlib.image.imsave)
def imsave(
    fname: str | os.PathLike | BinaryIO, arr: ArrayLike, **kwargs
) -> None:
    matplotlib.image.imsave(fname, arr, **kwargs)


def matshow(A: ArrayLike, fignum: None | int = None, **kwargs) -> AxesImage:
    """
    Display a 2D array as a matrix in a new figure window.

    The origin is set at the upper left hand corner.
    The indexing is ``(row, column)`` so that the first index runs vertically
    and the second index runs horizontally in the figure:

    .. code-block:: none

        A[0, 0]   ⋯ A[0, M-1]
           ⋮             ⋮
        A[N-1, 0] ⋯ A[N-1, M-1]

    The aspect ratio of the figure window is that of the array,
    unless this would make an excessively short or narrow figure.

    Tick labels for the xaxis are placed on top.

    Parameters
    ----------
    A : 2D array-like
        The matrix to be displayed.

    fignum : None or int
        If *None*, create a new, appropriately sized figure window.

        If 0, use the current Axes (creating one if there is none, without ever
        adjusting the figure size).

        Otherwise, create a new Axes on the figure with the given number
        (creating it at the appropriate size if it does not exist, but not
        adjusting the figure size otherwise).  Note that this will be drawn on
        top of any preexisting Axes on the figure.

    Returns
    -------
    `~matplotlib.image.AxesImage`

    Other Parameters
    ----------------
    **kwargs : `~matplotlib.axes.Axes.imshow` arguments

    """
    A = np.asanyarray(A)
    if fignum == 0:
        ax = gca()
    else:
        if fignum is not None and fignum_exists(fignum):
            # Do not try to set a figure size.
            figsize = None
        else:
            # Extract actual aspect ratio of array and make appropriately sized figure.
            figsize = figaspect(A)
        fig = figure(fignum, figsize=figsize)
        ax = fig.add_axes((0.15, 0.09, 0.775, 0.775))
    im = ax.matshow(A, **kwargs)
    sci(im)
    return im


def polar(*args, **kwargs) -> list[Line2D]:
    """
    Make a polar plot.

    call signature::

      polar(theta, r, [fmt], **kwargs)

    This is a convenience wrapper around `.pyplot.plot`. It ensures that the
    current Axes is polar (or creates one if needed) and then passes all parameters
    to ``.pyplot.plot``.

    .. note::
        When making polar plots using the :ref:`pyplot API <pyplot_interface>`,
        ``polar()`` should typically be the first command because that makes sure
        a polar Axes is created. Using other commands such as ``plt.title()``
        before this can lead to the implicit creation of a rectangular Axes, in which
        case a subsequent ``polar()`` call will fail.
    """
    # If an axis already exists, check if it has a polar projection
    if gcf().get_axes():
        ax = gca()
        if not isinstance(ax, PolarAxes):
            _api.warn_deprecated(
                "3.10",
                message="There exists a non-polar current Axes. Therefore, the "
                        "resulting plot from 'polar()' is non-polar. You likely "
                        "should call 'polar()' before any other pyplot plotting "
                        "commands. "
                        "Support for this scenario is deprecated in %(since)s and "
                        "will raise an error in %(removal)s"
            )
    else:
        ax = axes(projection="polar")
    return ax.plot(*args, **kwargs)


# If rcParams['backend_fallback'] is true, and an interactive backend is
# requested, ignore rcParams['backend'] and force selection of a backend that
# is compatible with the current running interactive framework.
if rcParams["backend_fallback"]:
    requested_backend = rcParams._get_backend_or_none()  # type: ignore[attr-defined]
    requested_backend = None if requested_backend is None else requested_backend.lower()
    available_backends = backend_registry.list_builtin(BackendFilter.INTERACTIVE)
    if (
        requested_backend in (set(available_backends) - {'webagg', 'nbagg'})
        and cbook._get_running_interactive_framework()
    ):
        rcParams._set("backend", rcsetup._auto_backend_sentinel)

# fmt: on

################# REMAINING CONTENT GENERATED BY boilerplate.py ##############


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Figure.figimage)
def figimage(
    X: ArrayLike,
    xo: int = 0,
    yo: int = 0,
    alpha: float | None = None,
    norm: str | Normalize | None = None,
    cmap: str | Colormap | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    origin: Literal["upper", "lower"] | None = None,
    resize: bool = False,
    *,
    colorizer: Colorizer | None = None,
    **kwargs,
) -> FigureImage:
    return gcf().figimage(
        X,
        xo=xo,
        yo=yo,
        alpha=alpha,
        norm=norm,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        origin=origin,
        resize=resize,
        colorizer=colorizer,
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Figure.text)
def figtext(
    x: float, y: float, s: str, fontdict: dict[str, Any] | None = None, **kwargs
) -> Text:
    return gcf().text(x, y, s, fontdict=fontdict, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Figure.gca)
def gca() -> Axes:
    return gcf().gca()


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Figure._gci)
def gci() -> ColorizingArtist | None:
    return gcf()._gci()


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Figure.ginput)
def ginput(
    n: int = 1,
    timeout: float = 30,
    show_clicks: bool = True,
    mouse_add: MouseButton = MouseButton.LEFT,
    mouse_pop: MouseButton = MouseButton.RIGHT,
    mouse_stop: MouseButton = MouseButton.MIDDLE,
) -> list[tuple[int, int]]:
    return gcf().ginput(
        n=n,
        timeout=timeout,
        show_clicks=show_clicks,
        mouse_add=mouse_add,
        mouse_pop=mouse_pop,
        mouse_stop=mouse_stop,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Figure.subplots_adjust)
def subplots_adjust(
    left: float | None = None,
    bottom: float | None = None,
    right: float | None = None,
    top: float | None = None,
    wspace: float | None = None,
    hspace: float | None = None,
) -> None:
    gcf().subplots_adjust(
        left=left, bottom=bottom, right=right, top=top, wspace=wspace, hspace=hspace
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Figure.suptitle)
def suptitle(t: str, **kwargs) -> Text:
    return gcf().suptitle(t, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Figure.tight_layout)
def tight_layout(
    *,
    pad: float = 1.08,
    h_pad: float | None = None,
    w_pad: float | None = None,
    rect: tuple[float, float, float, float] | None = None,
) -> None:
    gcf().tight_layout(pad=pad, h_pad=h_pad, w_pad=w_pad, rect=rect)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Figure.waitforbuttonpress)
def waitforbuttonpress(timeout: float = -1) -> None | bool:
    return gcf().waitforbuttonpress(timeout=timeout)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.acorr)
def acorr(
    x: ArrayLike, *, data=None, **kwargs
) -> tuple[np.ndarray, np.ndarray, LineCollection | Line2D, Line2D | None]:
    return gca().acorr(x, **({"data": data} if data is not None else {}), **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.angle_spectrum)
def angle_spectrum(
    x: ArrayLike,
    Fs: float | None = None,
    Fc: int | None = None,
    window: Callable[[ArrayLike], ArrayLike] | ArrayLike | None = None,
    pad_to: int | None = None,
    sides: Literal["default", "onesided", "twosided"] | None = None,
    *,
    data=None,
    **kwargs,
) -> tuple[np.ndarray, np.ndarray, Line2D]:
    return gca().angle_spectrum(
        x,
        Fs=Fs,
        Fc=Fc,
        window=window,
        pad_to=pad_to,
        sides=sides,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.annotate)
def annotate(
    text: str,
    xy: tuple[float, float],
    xytext: tuple[float, float] | None = None,
    xycoords: CoordsType = "data",
    textcoords: CoordsType | None = None,
    arrowprops: dict[str, Any] | None = None,
    annotation_clip: bool | None = None,
    **kwargs,
) -> Annotation:
    return gca().annotate(
        text,
        xy,
        xytext=xytext,
        xycoords=xycoords,
        textcoords=textcoords,
        arrowprops=arrowprops,
        annotation_clip=annotation_clip,
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.arrow)
def arrow(x: float, y: float, dx: float, dy: float, **kwargs) -> FancyArrow:
    return gca().arrow(x, y, dx, dy, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.autoscale)
def autoscale(
    enable: bool = True,
    axis: Literal["both", "x", "y"] = "both",
    tight: bool | None = None,
) -> None:
    gca().autoscale(enable=enable, axis=axis, tight=tight)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.axhline)
def axhline(y: float = 0, xmin: float = 0, xmax: float = 1, **kwargs) -> Line2D:
    return gca().axhline(y=y, xmin=xmin, xmax=xmax, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.axhspan)
def axhspan(
    ymin: float, ymax: float, xmin: float = 0, xmax: float = 1, **kwargs
) -> Rectangle:
    return gca().axhspan(ymin, ymax, xmin=xmin, xmax=xmax, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.axis)
def axis(
    arg: tuple[float, float, float, float] | bool | str | None = None,
    /,
    *,
    emit: bool = True,
    **kwargs,
) -> tuple[float, float, float, float]:
    return gca().axis(arg, emit=emit, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.axline)
def axline(
    xy1: tuple[float, float],
    xy2: tuple[float, float] | None = None,
    *,
    slope: float | None = None,
    **kwargs,
) -> AxLine:
    return gca().axline(xy1, xy2=xy2, slope=slope, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.axvline)
def axvline(x: float = 0, ymin: float = 0, ymax: float = 1, **kwargs) -> Line2D:
    return gca().axvline(x=x, ymin=ymin, ymax=ymax, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.axvspan)
def axvspan(
    xmin: float, xmax: float, ymin: float = 0, ymax: float = 1, **kwargs
) -> Rectangle:
    return gca().axvspan(xmin, xmax, ymin=ymin, ymax=ymax, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.bar)
def bar(
    x: float | ArrayLike,
    height: float | ArrayLike,
    width: float | ArrayLike = 0.8,
    bottom: float | ArrayLike | None = None,
    *,
    align: Literal["center", "edge"] = "center",
    data=None,
    **kwargs,
) -> BarContainer:
    return gca().bar(
        x,
        height,
        width=width,
        bottom=bottom,
        align=align,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.barbs)
def barbs(*args, data=None, **kwargs) -> Barbs:
    return gca().barbs(*args, **({"data": data} if data is not None else {}), **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.barh)
def barh(
    y: float | ArrayLike,
    width: float | ArrayLike,
    height: float | ArrayLike = 0.8,
    left: float | ArrayLike | None = None,
    *,
    align: Literal["center", "edge"] = "center",
    data=None,
    **kwargs,
) -> BarContainer:
    return gca().barh(
        y,
        width,
        height=height,
        left=left,
        align=align,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.bar_label)
def bar_label(
    container: BarContainer,
    labels: ArrayLike | None = None,
    *,
    fmt: str | Callable[[float], str] = "%g",
    label_type: Literal["center", "edge"] = "edge",
    padding: float = 0,
    **kwargs,
) -> list[Annotation]:
    return gca().bar_label(
        container,
        labels=labels,
        fmt=fmt,
        label_type=label_type,
        padding=padding,
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.boxplot)
def boxplot(
    x: ArrayLike | Sequence[ArrayLike],
    notch: bool | None = None,
    sym: str | None = None,
    vert: bool | None = None,
    orientation: Literal["vertical", "horizontal"] = "vertical",
    whis: float | tuple[float, float] | None = None,
    positions: ArrayLike | None = None,
    widths: float | ArrayLike | None = None,
    patch_artist: bool | None = None,
    bootstrap: int | None = None,
    usermedians: ArrayLike | None = None,
    conf_intervals: ArrayLike | None = None,
    meanline: bool | None = None,
    showmeans: bool | None = None,
    showcaps: bool | None = None,
    showbox: bool | None = None,
    showfliers: bool | None = None,
    boxprops: dict[str, Any] | None = None,
    tick_labels: Sequence[str] | None = None,
    flierprops: dict[str, Any] | None = None,
    medianprops: dict[str, Any] | None = None,
    meanprops: dict[str, Any] | None = None,
    capprops: dict[str, Any] | None = None,
    whiskerprops: dict[str, Any] | None = None,
    manage_ticks: bool = True,
    autorange: bool = False,
    zorder: float | None = None,
    capwidths: float | ArrayLike | None = None,
    label: Sequence[str] | None = None,
    *,
    data=None,
) -> dict[str, Any]:
    return gca().boxplot(
        x,
        notch=notch,
        sym=sym,
        vert=vert,
        orientation=orientation,
        whis=whis,
        positions=positions,
        widths=widths,
        patch_artist=patch_artist,
        bootstrap=bootstrap,
        usermedians=usermedians,
        conf_intervals=conf_intervals,
        meanline=meanline,
        showmeans=showmeans,
        showcaps=showcaps,
        showbox=showbox,
        showfliers=showfliers,
        boxprops=boxprops,
        tick_labels=tick_labels,
        flierprops=flierprops,
        medianprops=medianprops,
        meanprops=meanprops,
        capprops=capprops,
        whiskerprops=whiskerprops,
        manage_ticks=manage_ticks,
        autorange=autorange,
        zorder=zorder,
        capwidths=capwidths,
        label=label,
        **({"data": data} if data is not None else {}),
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.broken_barh)
def broken_barh(
    xranges: Sequence[tuple[float, float]],
    yrange: tuple[float, float],
    *,
    data=None,
    **kwargs,
) -> PolyCollection:
    return gca().broken_barh(
        xranges, yrange, **({"data": data} if data is not None else {}), **kwargs
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.clabel)
def clabel(CS: ContourSet, levels: ArrayLike | None = None, **kwargs) -> list[Text]:
    return gca().clabel(CS, levels=levels, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.cohere)
def cohere(
    x: ArrayLike,
    y: ArrayLike,
    NFFT: int = 256,
    Fs: float = 2,
    Fc: int = 0,
    detrend: Literal["none", "mean", "linear"]
    | Callable[[ArrayLike], ArrayLike] = mlab.detrend_none,
    window: Callable[[ArrayLike], ArrayLike] | ArrayLike = mlab.window_hanning,
    noverlap: int = 0,
    pad_to: int | None = None,
    sides: Literal["default", "onesided", "twosided"] = "default",
    scale_by_freq: bool | None = None,
    *,
    data=None,
    **kwargs,
) -> tuple[np.ndarray, np.ndarray]:
    return gca().cohere(
        x,
        y,
        NFFT=NFFT,
        Fs=Fs,
        Fc=Fc,
        detrend=detrend,
        window=window,
        noverlap=noverlap,
        pad_to=pad_to,
        sides=sides,
        scale_by_freq=scale_by_freq,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.contour)
def contour(*args, data=None, **kwargs) -> QuadContourSet:
    __ret = gca().contour(
        *args, **({"data": data} if data is not None else {}), **kwargs
    )
    if __ret._A is not None:  # type: ignore[attr-defined]
        sci(__ret)
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.contourf)
def contourf(*args, data=None, **kwargs) -> QuadContourSet:
    __ret = gca().contourf(
        *args, **({"data": data} if data is not None else {}), **kwargs
    )
    if __ret._A is not None:  # type: ignore[attr-defined]
        sci(__ret)
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.csd)
def csd(
    x: ArrayLike,
    y: ArrayLike,
    NFFT: int | None = None,
    Fs: float | None = None,
    Fc: int | None = None,
    detrend: Literal["none", "mean", "linear"]
    | Callable[[ArrayLike], ArrayLike]
    | None = None,
    window: Callable[[ArrayLike], ArrayLike] | ArrayLike | None = None,
    noverlap: int | None = None,
    pad_to: int | None = None,
    sides: Literal["default", "onesided", "twosided"] | None = None,
    scale_by_freq: bool | None = None,
    return_line: bool | None = None,
    *,
    data=None,
    **kwargs,
) -> tuple[np.ndarray, np.ndarray] | tuple[np.ndarray, np.ndarray, Line2D]:
    return gca().csd(
        x,
        y,
        NFFT=NFFT,
        Fs=Fs,
        Fc=Fc,
        detrend=detrend,
        window=window,
        noverlap=noverlap,
        pad_to=pad_to,
        sides=sides,
        scale_by_freq=scale_by_freq,
        return_line=return_line,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.ecdf)
def ecdf(
    x: ArrayLike,
    weights: ArrayLike | None = None,
    *,
    complementary: bool = False,
    orientation: Literal["vertical", "horizontal"] = "vertical",
    compress: bool = False,
    data=None,
    **kwargs,
) -> Line2D:
    return gca().ecdf(
        x,
        weights=weights,
        complementary=complementary,
        orientation=orientation,
        compress=compress,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.errorbar)
def errorbar(
    x: float | ArrayLike,
    y: float | ArrayLike,
    yerr: float | ArrayLike | None = None,
    xerr: float | ArrayLike | None = None,
    fmt: str = "",
    ecolor: ColorType | None = None,
    elinewidth: float | None = None,
    capsize: float | None = None,
    barsabove: bool = False,
    lolims: bool | ArrayLike = False,
    uplims: bool | ArrayLike = False,
    xlolims: bool | ArrayLike = False,
    xuplims: bool | ArrayLike = False,
    errorevery: int | tuple[int, int] = 1,
    capthick: float | None = None,
    *,
    data=None,
    **kwargs,
) -> ErrorbarContainer:
    return gca().errorbar(
        x,
        y,
        yerr=yerr,
        xerr=xerr,
        fmt=fmt,
        ecolor=ecolor,
        elinewidth=elinewidth,
        capsize=capsize,
        barsabove=barsabove,
        lolims=lolims,
        uplims=uplims,
        xlolims=xlolims,
        xuplims=xuplims,
        errorevery=errorevery,
        capthick=capthick,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.eventplot)
def eventplot(
    positions: ArrayLike | Sequence[ArrayLike],
    orientation: Literal["horizontal", "vertical"] = "horizontal",
    lineoffsets: float | Sequence[float] = 1,
    linelengths: float | Sequence[float] = 1,
    linewidths: float | Sequence[float] | None = None,
    colors: ColorType | Sequence[ColorType] | None = None,
    alpha: float | Sequence[float] | None = None,
    linestyles: LineStyleType | Sequence[LineStyleType] = "solid",
    *,
    data=None,
    **kwargs,
) -> EventCollection:
    return gca().eventplot(
        positions,
        orientation=orientation,
        lineoffsets=lineoffsets,
        linelengths=linelengths,
        linewidths=linewidths,
        colors=colors,
        alpha=alpha,
        linestyles=linestyles,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.fill)
def fill(*args, data=None, **kwargs) -> list[Polygon]:
    return gca().fill(*args, **({"data": data} if data is not None else {}), **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.fill_between)
def fill_between(
    x: ArrayLike,
    y1: ArrayLike | float,
    y2: ArrayLike | float = 0,
    where: Sequence[bool] | None = None,
    interpolate: bool = False,
    step: Literal["pre", "post", "mid"] | None = None,
    *,
    data=None,
    **kwargs,
) -> FillBetweenPolyCollection:
    return gca().fill_between(
        x,
        y1,
        y2=y2,
        where=where,
        interpolate=interpolate,
        step=step,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.fill_betweenx)
def fill_betweenx(
    y: ArrayLike,
    x1: ArrayLike | float,
    x2: ArrayLike | float = 0,
    where: Sequence[bool] | None = None,
    step: Literal["pre", "post", "mid"] | None = None,
    interpolate: bool = False,
    *,
    data=None,
    **kwargs,
) -> FillBetweenPolyCollection:
    return gca().fill_betweenx(
        y,
        x1,
        x2=x2,
        where=where,
        step=step,
        interpolate=interpolate,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.grid)
def grid(
    visible: bool | None = None,
    which: Literal["major", "minor", "both"] = "major",
    axis: Literal["both", "x", "y"] = "both",
    **kwargs,
) -> None:
    gca().grid(visible=visible, which=which, axis=axis, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.hexbin)
def hexbin(
    x: ArrayLike,
    y: ArrayLike,
    C: ArrayLike | None = None,
    gridsize: int | tuple[int, int] = 100,
    bins: Literal["log"] | int | Sequence[float] | None = None,
    xscale: Literal["linear", "log"] = "linear",
    yscale: Literal["linear", "log"] = "linear",
    extent: tuple[float, float, float, float] | None = None,
    cmap: str | Colormap | None = None,
    norm: str | Normalize | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    alpha: float | None = None,
    linewidths: float | None = None,
    edgecolors: Literal["face", "none"] | ColorType = "face",
    reduce_C_function: Callable[[np.ndarray | list[float]], float] = np.mean,
    mincnt: int | None = None,
    marginals: bool = False,
    colorizer: Colorizer | None = None,
    *,
    data=None,
    **kwargs,
) -> PolyCollection:
    __ret = gca().hexbin(
        x,
        y,
        C=C,
        gridsize=gridsize,
        bins=bins,
        xscale=xscale,
        yscale=yscale,
        extent=extent,
        cmap=cmap,
        norm=norm,
        vmin=vmin,
        vmax=vmax,
        alpha=alpha,
        linewidths=linewidths,
        edgecolors=edgecolors,
        reduce_C_function=reduce_C_function,
        mincnt=mincnt,
        marginals=marginals,
        colorizer=colorizer,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )
    sci(__ret)
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.hist)
def hist(
    x: ArrayLike | Sequence[ArrayLike],
    bins: int | Sequence[float] | str | None = None,
    range: tuple[float, float] | None = None,
    density: bool = False,
    weights: ArrayLike | None = None,
    cumulative: bool | float = False,
    bottom: ArrayLike | float | None = None,
    histtype: Literal["bar", "barstacked", "step", "stepfilled"] = "bar",
    align: Literal["left", "mid", "right"] = "mid",
    orientation: Literal["vertical", "horizontal"] = "vertical",
    rwidth: float | None = None,
    log: bool = False,
    color: ColorType | Sequence[ColorType] | None = None,
    label: str | Sequence[str] | None = None,
    stacked: bool = False,
    *,
    data=None,
    **kwargs,
) -> tuple[
    np.ndarray | list[np.ndarray],
    np.ndarray,
    BarContainer | Polygon | list[BarContainer | Polygon],
]:
    return gca().hist(
        x,
        bins=bins,
        range=range,
        density=density,
        weights=weights,
        cumulative=cumulative,
        bottom=bottom,
        histtype=histtype,
        align=align,
        orientation=orientation,
        rwidth=rwidth,
        log=log,
        color=color,
        label=label,
        stacked=stacked,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.stairs)
def stairs(
    values: ArrayLike,
    edges: ArrayLike | None = None,
    *,
    orientation: Literal["vertical", "horizontal"] = "vertical",
    baseline: float | ArrayLike | None = 0,
    fill: bool = False,
    data=None,
    **kwargs,
) -> StepPatch:
    return gca().stairs(
        values,
        edges=edges,
        orientation=orientation,
        baseline=baseline,
        fill=fill,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.hist2d)
def hist2d(
    x: ArrayLike,
    y: ArrayLike,
    bins: None | int | tuple[int, int] | ArrayLike | tuple[ArrayLike, ArrayLike] = 10,
    range: ArrayLike | None = None,
    density: bool = False,
    weights: ArrayLike | None = None,
    cmin: float | None = None,
    cmax: float | None = None,
    *,
    data=None,
    **kwargs,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, QuadMesh]:
    __ret = gca().hist2d(
        x,
        y,
        bins=bins,
        range=range,
        density=density,
        weights=weights,
        cmin=cmin,
        cmax=cmax,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )
    sci(__ret[-1])
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.hlines)
def hlines(
    y: float | ArrayLike,
    xmin: float | ArrayLike,
    xmax: float | ArrayLike,
    colors: ColorType | Sequence[ColorType] | None = None,
    linestyles: LineStyleType = "solid",
    label: str = "",
    *,
    data=None,
    **kwargs,
) -> LineCollection:
    return gca().hlines(
        y,
        xmin,
        xmax,
        colors=colors,
        linestyles=linestyles,
        label=label,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.imshow)
def imshow(
    X: ArrayLike | PIL.Image.Image,
    cmap: str | Colormap | None = None,
    norm: str | Normalize | None = None,
    *,
    aspect: Literal["equal", "auto"] | float | None = None,
    interpolation: str | None = None,
    alpha: float | ArrayLike | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    colorizer: Colorizer | None = None,
    origin: Literal["upper", "lower"] | None = None,
    extent: tuple[float, float, float, float] | None = None,
    interpolation_stage: Literal["data", "rgba", "auto"] | None = None,
    filternorm: bool = True,
    filterrad: float = 4.0,
    resample: bool | None = None,
    url: str | None = None,
    data=None,
    **kwargs,
) -> AxesImage:
    __ret = gca().imshow(
        X,
        cmap=cmap,
        norm=norm,
        aspect=aspect,
        interpolation=interpolation,
        alpha=alpha,
        vmin=vmin,
        vmax=vmax,
        colorizer=colorizer,
        origin=origin,
        extent=extent,
        interpolation_stage=interpolation_stage,
        filternorm=filternorm,
        filterrad=filterrad,
        resample=resample,
        url=url,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )
    sci(__ret)
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.legend)
def legend(*args, **kwargs) -> Legend:
    return gca().legend(*args, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.locator_params)
def locator_params(
    axis: Literal["both", "x", "y"] = "both", tight: bool | None = None, **kwargs
) -> None:
    gca().locator_params(axis=axis, tight=tight, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.loglog)
def loglog(*args, **kwargs) -> list[Line2D]:
    return gca().loglog(*args, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.magnitude_spectrum)
def magnitude_spectrum(
    x: ArrayLike,
    Fs: float | None = None,
    Fc: int | None = None,
    window: Callable[[ArrayLike], ArrayLike] | ArrayLike | None = None,
    pad_to: int | None = None,
    sides: Literal["default", "onesided", "twosided"] | None = None,
    scale: Literal["default", "linear", "dB"] | None = None,
    *,
    data=None,
    **kwargs,
) -> tuple[np.ndarray, np.ndarray, Line2D]:
    return gca().magnitude_spectrum(
        x,
        Fs=Fs,
        Fc=Fc,
        window=window,
        pad_to=pad_to,
        sides=sides,
        scale=scale,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.margins)
def margins(
    *margins: float,
    x: float | None = None,
    y: float | None = None,
    tight: bool | None = True,
) -> tuple[float, float] | None:
    return gca().margins(*margins, x=x, y=y, tight=tight)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.minorticks_off)
def minorticks_off() -> None:
    gca().minorticks_off()


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.minorticks_on)
def minorticks_on() -> None:
    gca().minorticks_on()


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.pcolor)
def pcolor(
    *args: ArrayLike,
    shading: Literal["flat", "nearest", "auto"] | None = None,
    alpha: float | None = None,
    norm: str | Normalize | None = None,
    cmap: str | Colormap | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    colorizer: Colorizer | None = None,
    data=None,
    **kwargs,
) -> Collection:
    __ret = gca().pcolor(
        *args,
        shading=shading,
        alpha=alpha,
        norm=norm,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        colorizer=colorizer,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )
    sci(__ret)
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.pcolormesh)
def pcolormesh(
    *args: ArrayLike,
    alpha: float | None = None,
    norm: str | Normalize | None = None,
    cmap: str | Colormap | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    colorizer: Colorizer | None = None,
    shading: Literal["flat", "nearest", "gouraud", "auto"] | None = None,
    antialiased: bool = False,
    data=None,
    **kwargs,
) -> QuadMesh:
    __ret = gca().pcolormesh(
        *args,
        alpha=alpha,
        norm=norm,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        colorizer=colorizer,
        shading=shading,
        antialiased=antialiased,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )
    sci(__ret)
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.phase_spectrum)
def phase_spectrum(
    x: ArrayLike,
    Fs: float | None = None,
    Fc: int | None = None,
    window: Callable[[ArrayLike], ArrayLike] | ArrayLike | None = None,
    pad_to: int | None = None,
    sides: Literal["default", "onesided", "twosided"] | None = None,
    *,
    data=None,
    **kwargs,
) -> tuple[np.ndarray, np.ndarray, Line2D]:
    return gca().phase_spectrum(
        x,
        Fs=Fs,
        Fc=Fc,
        window=window,
        pad_to=pad_to,
        sides=sides,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.pie)
def pie(
    x: ArrayLike,
    explode: ArrayLike | None = None,
    labels: Sequence[str] | None = None,
    colors: ColorType | Sequence[ColorType] | None = None,
    autopct: str | Callable[[float], str] | None = None,
    pctdistance: float = 0.6,
    shadow: bool = False,
    labeldistance: float | None = 1.1,
    startangle: float = 0,
    radius: float = 1,
    counterclock: bool = True,
    wedgeprops: dict[str, Any] | None = None,
    textprops: dict[str, Any] | None = None,
    center: tuple[float, float] = (0, 0),
    frame: bool = False,
    rotatelabels: bool = False,
    *,
    normalize: bool = True,
    hatch: str | Sequence[str] | None = None,
    data=None,
) -> tuple[list[Wedge], list[Text]] | tuple[list[Wedge], list[Text], list[Text]]:
    return gca().pie(
        x,
        explode=explode,
        labels=labels,
        colors=colors,
        autopct=autopct,
        pctdistance=pctdistance,
        shadow=shadow,
        labeldistance=labeldistance,
        startangle=startangle,
        radius=radius,
        counterclock=counterclock,
        wedgeprops=wedgeprops,
        textprops=textprops,
        center=center,
        frame=frame,
        rotatelabels=rotatelabels,
        normalize=normalize,
        hatch=hatch,
        **({"data": data} if data is not None else {}),
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.plot)
def plot(
    *args: float | ArrayLike | str,
    scalex: bool = True,
    scaley: bool = True,
    data=None,
    **kwargs,
) -> list[Line2D]:
    return gca().plot(
        *args,
        scalex=scalex,
        scaley=scaley,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.plot_date)
def plot_date(
    x: ArrayLike,
    y: ArrayLike,
    fmt: str = "o",
    tz: str | datetime.tzinfo | None = None,
    xdate: bool = True,
    ydate: bool = False,
    *,
    data=None,
    **kwargs,
) -> list[Line2D]:
    return gca().plot_date(
        x,
        y,
        fmt=fmt,
        tz=tz,
        xdate=xdate,
        ydate=ydate,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.psd)
def psd(
    x: ArrayLike,
    NFFT: int | None = None,
    Fs: float | None = None,
    Fc: int | None = None,
    detrend: Literal["none", "mean", "linear"]
    | Callable[[ArrayLike], ArrayLike]
    | None = None,
    window: Callable[[ArrayLike], ArrayLike] | ArrayLike | None = None,
    noverlap: int | None = None,
    pad_to: int | None = None,
    sides: Literal["default", "onesided", "twosided"] | None = None,
    scale_by_freq: bool | None = None,
    return_line: bool | None = None,
    *,
    data=None,
    **kwargs,
) -> tuple[np.ndarray, np.ndarray] | tuple[np.ndarray, np.ndarray, Line2D]:
    return gca().psd(
        x,
        NFFT=NFFT,
        Fs=Fs,
        Fc=Fc,
        detrend=detrend,
        window=window,
        noverlap=noverlap,
        pad_to=pad_to,
        sides=sides,
        scale_by_freq=scale_by_freq,
        return_line=return_line,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.quiver)
def quiver(*args, data=None, **kwargs) -> Quiver:
    __ret = gca().quiver(
        *args, **({"data": data} if data is not None else {}), **kwargs
    )
    sci(__ret)
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.quiverkey)
def quiverkey(
    Q: Quiver, X: float, Y: float, U: float, label: str, **kwargs
) -> QuiverKey:
    return gca().quiverkey(Q, X, Y, U, label, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.scatter)
def scatter(
    x: float | ArrayLike,
    y: float | ArrayLike,
    s: float | ArrayLike | None = None,
    c: ArrayLike | Sequence[ColorType] | ColorType | None = None,
    marker: MarkerType | None = None,
    cmap: str | Colormap | None = None,
    norm: str | Normalize | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    alpha: float | None = None,
    linewidths: float | Sequence[float] | None = None,
    *,
    edgecolors: Literal["face", "none"] | ColorType | Sequence[ColorType] | None = None,
    colorizer: Colorizer | None = None,
    plotnonfinite: bool = False,
    data=None,
    **kwargs,
) -> PathCollection:
    __ret = gca().scatter(
        x,
        y,
        s=s,
        c=c,
        marker=marker,
        cmap=cmap,
        norm=norm,
        vmin=vmin,
        vmax=vmax,
        alpha=alpha,
        linewidths=linewidths,
        edgecolors=edgecolors,
        colorizer=colorizer,
        plotnonfinite=plotnonfinite,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )
    sci(__ret)
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.semilogx)
def semilogx(*args, **kwargs) -> list[Line2D]:
    return gca().semilogx(*args, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.semilogy)
def semilogy(*args, **kwargs) -> list[Line2D]:
    return gca().semilogy(*args, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.specgram)
def specgram(
    x: ArrayLike,
    NFFT: int | None = None,
    Fs: float | None = None,
    Fc: int | None = None,
    detrend: Literal["none", "mean", "linear"]
    | Callable[[ArrayLike], ArrayLike]
    | None = None,
    window: Callable[[ArrayLike], ArrayLike] | ArrayLike | None = None,
    noverlap: int | None = None,
    cmap: str | Colormap | None = None,
    xextent: tuple[float, float] | None = None,
    pad_to: int | None = None,
    sides: Literal["default", "onesided", "twosided"] | None = None,
    scale_by_freq: bool | None = None,
    mode: Literal["default", "psd", "magnitude", "angle", "phase"] | None = None,
    scale: Literal["default", "linear", "dB"] | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    *,
    data=None,
    **kwargs,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, AxesImage]:
    __ret = gca().specgram(
        x,
        NFFT=NFFT,
        Fs=Fs,
        Fc=Fc,
        detrend=detrend,
        window=window,
        noverlap=noverlap,
        cmap=cmap,
        xextent=xextent,
        pad_to=pad_to,
        sides=sides,
        scale_by_freq=scale_by_freq,
        mode=mode,
        scale=scale,
        vmin=vmin,
        vmax=vmax,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )
    sci(__ret[-1])
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.spy)
def spy(
    Z: ArrayLike,
    precision: float | Literal["present"] = 0,
    marker: str | None = None,
    markersize: float | None = None,
    aspect: Literal["equal", "auto"] | float | None = "equal",
    origin: Literal["upper", "lower"] = "upper",
    **kwargs,
) -> AxesImage:
    __ret = gca().spy(
        Z,
        precision=precision,
        marker=marker,
        markersize=markersize,
        aspect=aspect,
        origin=origin,
        **kwargs,
    )
    if isinstance(__ret, _ColorizerInterface):
        sci(__ret)
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.stackplot)
def stackplot(
    x, *args, labels=(), colors=None, hatch=None, baseline="zero", data=None, **kwargs
):
    return gca().stackplot(
        x,
        *args,
        labels=labels,
        colors=colors,
        hatch=hatch,
        baseline=baseline,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.stem)
def stem(
    *args: ArrayLike | str,
    linefmt: str | None = None,
    markerfmt: str | None = None,
    basefmt: str | None = None,
    bottom: float = 0,
    label: str | None = None,
    orientation: Literal["vertical", "horizontal"] = "vertical",
    data=None,
) -> StemContainer:
    return gca().stem(
        *args,
        linefmt=linefmt,
        markerfmt=markerfmt,
        basefmt=basefmt,
        bottom=bottom,
        label=label,
        orientation=orientation,
        **({"data": data} if data is not None else {}),
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.step)
def step(
    x: ArrayLike,
    y: ArrayLike,
    *args,
    where: Literal["pre", "post", "mid"] = "pre",
    data=None,
    **kwargs,
) -> list[Line2D]:
    return gca().step(
        x,
        y,
        *args,
        where=where,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.streamplot)
def streamplot(
    x,
    y,
    u,
    v,
    density=1,
    linewidth=None,
    color=None,
    cmap=None,
    norm=None,
    arrowsize=1,
    arrowstyle="-|>",
    minlength=0.1,
    transform=None,
    zorder=None,
    start_points=None,
    maxlength=4.0,
    integration_direction="both",
    broken_streamlines=True,
    *,
    data=None,
):
    __ret = gca().streamplot(
        x,
        y,
        u,
        v,
        density=density,
        linewidth=linewidth,
        color=color,
        cmap=cmap,
        norm=norm,
        arrowsize=arrowsize,
        arrowstyle=arrowstyle,
        minlength=minlength,
        transform=transform,
        zorder=zorder,
        start_points=start_points,
        maxlength=maxlength,
        integration_direction=integration_direction,
        broken_streamlines=broken_streamlines,
        **({"data": data} if data is not None else {}),
    )
    sci(__ret.lines)
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.table)
def table(
    cellText=None,
    cellColours=None,
    cellLoc="right",
    colWidths=None,
    rowLabels=None,
    rowColours=None,
    rowLoc="left",
    colLabels=None,
    colColours=None,
    colLoc="center",
    loc="bottom",
    bbox=None,
    edges="closed",
    **kwargs,
):
    return gca().table(
        cellText=cellText,
        cellColours=cellColours,
        cellLoc=cellLoc,
        colWidths=colWidths,
        rowLabels=rowLabels,
        rowColours=rowColours,
        rowLoc=rowLoc,
        colLabels=colLabels,
        colColours=colColours,
        colLoc=colLoc,
        loc=loc,
        bbox=bbox,
        edges=edges,
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.text)
def text(
    x: float, y: float, s: str, fontdict: dict[str, Any] | None = None, **kwargs
) -> Text:
    return gca().text(x, y, s, fontdict=fontdict, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.tick_params)
def tick_params(axis: Literal["both", "x", "y"] = "both", **kwargs) -> None:
    gca().tick_params(axis=axis, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.ticklabel_format)
def ticklabel_format(
    *,
    axis: Literal["both", "x", "y"] = "both",
    style: Literal["", "sci", "scientific", "plain"] | None = None,
    scilimits: tuple[int, int] | None = None,
    useOffset: bool | float | None = None,
    useLocale: bool | None = None,
    useMathText: bool | None = None,
) -> None:
    gca().ticklabel_format(
        axis=axis,
        style=style,
        scilimits=scilimits,
        useOffset=useOffset,
        useLocale=useLocale,
        useMathText=useMathText,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.tricontour)
def tricontour(*args, **kwargs):
    __ret = gca().tricontour(*args, **kwargs)
    if __ret._A is not None:  # type: ignore[attr-defined]
        sci(__ret)
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.tricontourf)
def tricontourf(*args, **kwargs):
    __ret = gca().tricontourf(*args, **kwargs)
    if __ret._A is not None:  # type: ignore[attr-defined]
        sci(__ret)
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.tripcolor)
def tripcolor(
    *args,
    alpha=1.0,
    norm=None,
    cmap=None,
    vmin=None,
    vmax=None,
    shading="flat",
    facecolors=None,
    **kwargs,
):
    __ret = gca().tripcolor(
        *args,
        alpha=alpha,
        norm=norm,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        shading=shading,
        facecolors=facecolors,
        **kwargs,
    )
    sci(__ret)
    return __ret


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.triplot)
def triplot(*args, **kwargs):
    return gca().triplot(*args, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.violinplot)
def violinplot(
    dataset: ArrayLike | Sequence[ArrayLike],
    positions: ArrayLike | None = None,
    vert: bool | None = None,
    orientation: Literal["vertical", "horizontal"] = "vertical",
    widths: float | ArrayLike = 0.5,
    showmeans: bool = False,
    showextrema: bool = True,
    showmedians: bool = False,
    quantiles: Sequence[float | Sequence[float]] | None = None,
    points: int = 100,
    bw_method: Literal["scott", "silverman"]
    | float
    | Callable[[GaussianKDE], float]
    | None = None,
    side: Literal["both", "low", "high"] = "both",
    *,
    data=None,
) -> dict[str, Collection]:
    return gca().violinplot(
        dataset,
        positions=positions,
        vert=vert,
        orientation=orientation,
        widths=widths,
        showmeans=showmeans,
        showextrema=showextrema,
        showmedians=showmedians,
        quantiles=quantiles,
        points=points,
        bw_method=bw_method,
        side=side,
        **({"data": data} if data is not None else {}),
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.vlines)
def vlines(
    x: float | ArrayLike,
    ymin: float | ArrayLike,
    ymax: float | ArrayLike,
    colors: ColorType | Sequence[ColorType] | None = None,
    linestyles: LineStyleType = "solid",
    label: str = "",
    *,
    data=None,
    **kwargs,
) -> LineCollection:
    return gca().vlines(
        x,
        ymin,
        ymax,
        colors=colors,
        linestyles=linestyles,
        label=label,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.xcorr)
def xcorr(
    x: ArrayLike,
    y: ArrayLike,
    normed: bool = True,
    detrend: Callable[[ArrayLike], ArrayLike] = mlab.detrend_none,
    usevlines: bool = True,
    maxlags: int = 10,
    *,
    data=None,
    **kwargs,
) -> tuple[np.ndarray, np.ndarray, LineCollection | Line2D, Line2D | None]:
    return gca().xcorr(
        x,
        y,
        normed=normed,
        detrend=detrend,
        usevlines=usevlines,
        maxlags=maxlags,
        **({"data": data} if data is not None else {}),
        **kwargs,
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes._sci)
def sci(im: ColorizingArtist) -> None:
    gca()._sci(im)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.set_title)
def title(
    label: str,
    fontdict: dict[str, Any] | None = None,
    loc: Literal["left", "center", "right"] | None = None,
    pad: float | None = None,
    *,
    y: float | None = None,
    **kwargs,
) -> Text:
    return gca().set_title(label, fontdict=fontdict, loc=loc, pad=pad, y=y, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.set_xlabel)
def xlabel(
    xlabel: str,
    fontdict: dict[str, Any] | None = None,
    labelpad: float | None = None,
    *,
    loc: Literal["left", "center", "right"] | None = None,
    **kwargs,
) -> Text:
    return gca().set_xlabel(
        xlabel, fontdict=fontdict, labelpad=labelpad, loc=loc, **kwargs
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.set_ylabel)
def ylabel(
    ylabel: str,
    fontdict: dict[str, Any] | None = None,
    labelpad: float | None = None,
    *,
    loc: Literal["bottom", "center", "top"] | None = None,
    **kwargs,
) -> Text:
    return gca().set_ylabel(
        ylabel, fontdict=fontdict, labelpad=labelpad, loc=loc, **kwargs
    )


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.set_xscale)
def xscale(value: str | ScaleBase, **kwargs) -> None:
    gca().set_xscale(value, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
@_copy_docstring_and_deprecators(Axes.set_yscale)
def yscale(value: str | ScaleBase, **kwargs) -> None:
    gca().set_yscale(value, **kwargs)


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def autumn() -> None:
    """
    Set the colormap to 'autumn'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("autumn")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def bone() -> None:
    """
    Set the colormap to 'bone'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("bone")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def cool() -> None:
    """
    Set the colormap to 'cool'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("cool")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def copper() -> None:
    """
    Set the colormap to 'copper'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("copper")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def flag() -> None:
    """
    Set the colormap to 'flag'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("flag")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def gray() -> None:
    """
    Set the colormap to 'gray'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("gray")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def hot() -> None:
    """
    Set the colormap to 'hot'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("hot")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def hsv() -> None:
    """
    Set the colormap to 'hsv'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("hsv")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def jet() -> None:
    """
    Set the colormap to 'jet'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("jet")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def pink() -> None:
    """
    Set the colormap to 'pink'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("pink")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def prism() -> None:
    """
    Set the colormap to 'prism'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("prism")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def spring() -> None:
    """
    Set the colormap to 'spring'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("spring")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def summer() -> None:
    """
    Set the colormap to 'summer'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("summer")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def winter() -> None:
    """
    Set the colormap to 'winter'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("winter")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def magma() -> None:
    """
    Set the colormap to 'magma'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("magma")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def inferno() -> None:
    """
    Set the colormap to 'inferno'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("inferno")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def plasma() -> None:
    """
    Set the colormap to 'plasma'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("plasma")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def viridis() -> None:
    """
    Set the colormap to 'viridis'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("viridis")


# Autogenerated by boilerplate.py.  Do not edit as changes will be lost.
def nipy_spectral() -> None:
    """
    Set the colormap to 'nipy_spectral'.

    This changes the default colormap as well as the colormap of the current
    image if there is one. See ``help(colormaps)`` for more information.
    """
    set_cmap("nipy_spectral")